"""
Debate Tool - Backend
FastAPI server that orchestrates a three-model debate via Server-Sent Events.

Each debate is persisted to ~/.debate-tool/debates/{id}.json so that
errors don't lose work and the user can retry from a specific role.
"""
import asyncio
import json
from typing import AsyncIterator, Optional, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import load_settings, save_settings, Settings
from models import stream_model, list_available_models, ProviderError
from persistence import (
    Debate, RoleResult, new_debate, save_debate, load_debate,
    list_recent_debates, delete_debate,
)

app = FastAPI(title="Debate Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# ROLE PROMPTS - calibrated to reduce critic anchoring and
# put final answer first in judge output
# ============================================================
PROPOSER_SYSTEM = """You are answering a user's question carefully and substantively.
Give your best answer with reasoning. Be specific and concrete.
Don't hedge unnecessarily, but flag genuine uncertainty where it exists.
Aim for the answer a thoughtful expert would give a peer, not a generic explanation."""


CRITIC_CRITERIA_SYSTEM = """You are establishing what a correct, complete answer to a user's question
should account for, BEFORE you see anyone's attempt to answer it.

You will only see the question. Your job is to list the key correctness criteria,
edge cases, or considerations that a good answer should cover. This list will
later be used to evaluate a separately-generated answer, so it must come purely
from your own analysis of the question, not from anyone else's framing.

Output a concise list of criteria. No preamble, no review, no answer. Just the
criteria.

Format:

CRITERIA FOR A GOOD ANSWER:
- [criterion 1]
- [criterion 2]
- [criterion 3]
- ...

Aim for 5-10 criteria. Be specific where possible (e.g., "must distinguish X
from Y" rather than "should be accurate"). For technical questions, include
relevant edge cases. For architecture questions, include scalability/security/
reliability considerations. For factual questions, include the kinds of claims
that must be verified."""


CRITIC_SYSTEM = """You are an adversarial but calibrated reviewer of an answer to a user's question.

You have been given a set of criteria (generated independently from the question
alone, before anyone saw the proposer's answer) plus the proposer's actual answer.
Your job is to review the answer against those criteria.

For each substantive issue you find, provide:
- Severity: critical | major | minor
- Exact claim or omission (quote it)
- Why it matters
- Suggested correction
- Confidence: high | medium | low

Important constraints:
- If the answer is substantially correct, say so explicitly. "No significant issues
  found, the answer addresses the criteria well" is a valid and valuable output.
- Do NOT manufacture issues to seem useful. Better to say nothing than to invent
  problems that waste the judge's effort.
- Distinguish real errors and missed considerations from style preferences. Don't
  flag the latter.
- The criteria you were given are guidance, not a checklist to enforce mechanically.
  If the answer addresses something important not in the criteria, that's fine. If
  it omits something in the criteria that doesn't actually matter for this question,
  that's also fine.
- For technical/code questions: propose at least one test case or failure mode if
  issues are found.
- For architecture questions: identify scalability, security, reliability, or
  maintainability risks if any are missing.

Format your response as:

ISSUES FOUND:
[Numbered list with severity/quote/why/correction/confidence, or "No substantive issues" if genuine]

OVERALL ASSESSMENT:
[One short paragraph: is the answer solid, partially correct, or significantly flawed?]"""


JUDGE_SYSTEM = """You are an evidence-aware adjudicator, not a polished synthesizer.
You are reviewing a question, a proposed answer, and a critique of that answer.
Your job is to produce the best final answer for the user — but the critic is NOT
automatically correct. Critics sometimes manufacture issues, overcorrect, or miss
context. Your job is to weigh each critique on its merits.

Important behaviors:

ADJUDICATE EACH CRITIC POINT, DON'T JUST ABSORB IT:
For every issue the critic raised, decide explicitly whether to accept, reject,
modify, or mark uncertain. Don't assume the critic is right. If a critique looks
plausible but you can't verify it, mark it uncertain rather than silently
accepting it.

PRESERVE CORRECT EXAMPLES:
If the critic provided a correct counterexample or code snippet, preserve it
exactly. Do not casually rewrite working examples while integrating them — that
introduces new bugs. If you do rewrite an example, re-verify the rewrite for
correctness before including it.

VERIFY ANY NEW CLAIMS YOU ADD:
If you add an example, claim, or detail that wasn't in the proposer or critic
response, audit it before finalizing. If you can't verify it, remove it or mark
it as uncertain. Do not invent specifics to sound more thorough.

DO NOT OVERCLAIM CERTAINTY:
"None significant" for remaining uncertainty should be reserved for genuinely
deterministic questions (e.g., "what does this operator do," "what's the syntax
for X"). For questions involving tradeoffs, context-dependence, version-dependent
specifics, or contested expert opinion, surface that uncertainty honestly.

Structure your output in this order:

FINAL ANSWER:
[The best answer to the user's original question. Lead with this. The user is
reading this panel to get an answer, so put it first. Write naturally and
substantively, not as a summary.]

CRITIC POINT ADJUDICATION:
[For each substantive issue the critic raised, briefly state: ACCEPTED / REJECTED
/ MODIFIED / UNCERTAIN, with one sentence of reasoning. Skip this section only if
the critic found no substantive issues.]

WHAT CHANGED FROM THE PROPOSER'S DRAFT:
- Corrected: [factual fixes incorporated, if any]
- Added: [new content beyond the proposer's draft, if any]
- Removed: [proposer claims dropped as wrong/unsupported, if any]
- Preserved: [valid proposer claims the critic challenged but you kept]

REMAINING UNCERTAINTY:
[Use this structure. If a category doesn't apply, say "none" for that category.
Do not write a single bare "None significant" — at minimum address each line.]
- Context gaps: [aspects where the right answer depends on context not provided]
- Version/release dependencies: [specifics that may be release-dependent]
- Definitions to confirm: [terms or assumptions that need verification]
- Claims to verify before production use: [things worth checking against primary
  sources before relying on them]"""


# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================
ProviderName = Literal["claude", "openai", "gemini"]
RoleName = Literal["proposer", "critic", "judge"]


class Message(BaseModel):
    role: str
    content: str


class DebateRequest(BaseModel):
    messages: list[Message]


class ResumeRequest(BaseModel):
    """Resume a debate from a specific role onward, reusing prior outputs."""
    debate_id: str
    from_role: RoleName  # which role to (re)start from


class SettingsUpdate(BaseModel):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    proposer_provider: ProviderName = "claude"
    proposer_model: str = "claude-opus-4-7"
    critic_provider: ProviderName = "openai"
    critic_model: str = "gpt-5.5"
    judge_provider: ProviderName = "gemini"
    judge_model: str = "gemini-3.1-pro-preview"


# ============================================================
# SSE HELPER
# ============================================================
def sse(event: dict) -> str:
    """Format a dict as a Server-Sent Event line."""
    return f"data: {json.dumps(event)}\n\n"


# ============================================================
# ROLE EXECUTION - runs a single role and updates the debate
# ============================================================
ROLE_ORDER: list[RoleName] = ["proposer", "critic", "judge"]


def _build_role_input(debate: Debate, role: RoleName) -> tuple[str, str]:
    """Return (system_prompt, user_input) for a given role."""
    if role == "proposer":
        return PROPOSER_SYSTEM, debate.question

    elif role == "critic":
        criteria_text = debate.critic.criteria or "(No criteria available - proceed with general review.)"
        user = (
            f"USER'S QUESTION:\n{debate.question}\n\n"
            f"CRITERIA FOR A GOOD ANSWER (generated independently from the question alone):\n{criteria_text}\n\n"
            f"PROPOSED ANSWER:\n{debate.proposer.text}\n\n"
            f"Review this answer following the structure in your instructions."
        )
        return CRITIC_SYSTEM, user

    elif role == "judge":
        user = (
            f"USER'S ORIGINAL QUESTION:\n{debate.question}\n\n"
            f"PROPOSED ANSWER:\n{debate.proposer.text}\n\n"
            f"CRITIQUE OF PROPOSED ANSWER:\n{debate.critic.text}\n\n"
            f"Produce your final answer following the structure in your instructions."
        )
        return JUDGE_SYSTEM, user

    raise ValueError(f"Unknown role: {role}")


def _role_settings(settings: Settings, role: RoleName) -> tuple[str, str]:
    """Return (provider, model) for a given role from settings."""
    if role == "proposer":
        return settings.proposer_provider, settings.proposer_model
    elif role == "critic":
        return settings.critic_provider, settings.critic_model
    elif role == "judge":
        return settings.judge_provider, settings.judge_model
    raise ValueError(f"Unknown role: {role}")


async def _execute_role(
    debate: Debate, role: RoleName, settings: Settings,
) -> AsyncIterator[str]:
    """Run a single role, streaming SSE events. Updates and persists debate state."""
    provider, model = _role_settings(settings, role)
    system, user_input = _build_role_input(debate, role)

    # Reset role state and mark active
    role_result = RoleResult(
        text="",
        provider=provider,
        model=model,
        status="active",
    )
    debate.set_role(role, role_result)
    save_debate(debate)

    yield sse({
        "type": "role_start",
        "role": role,
        "provider": provider,
        "model": model,
    })

    try:
        async for event in stream_model(
            provider=provider,
            model=model,
            api_key=settings.api_key_for(provider),
            system=system,
            user=user_input,
        ):
            if event["type"] == "text":
                role_result.text += event["content"]
                yield sse({"type": "token", "role": role, "content": event["content"]})
            elif event["type"] == "usage":
                role_result.input_tokens = event["input"]
                role_result.output_tokens = event["output"]
                yield sse({
                    "type": "usage",
                    "role": role,
                    "input": event["input"],
                    "output": event["output"],
                })
    except ProviderError as e:
        role_result.status = "error"
        role_result.error_message = str(e)
        debate.status = "error"
        save_debate(debate)
        yield sse({"type": "error", "role": role, "message": str(e), "debate_id": debate.id})
        return
    except asyncio.CancelledError:
        role_result.status = "error"
        role_result.error_message = "Cancelled by user"
        debate.status = "stopped"
        save_debate(debate)
        yield sse({"type": "stopped", "role": role, "debate_id": debate.id})
        raise

    role_result.status = "complete"
    save_debate(debate)
    yield sse({"type": "role_complete", "role": role})


async def _execute_criteria_step(
    debate: Debate, settings: Settings,
) -> AsyncIterator[str]:
    """Generate the critic's criteria from the question alone, before the critic sees the answer.

    Runs as a non-streaming background call - we don't show tokens as they arrive
    because the criteria step is internal plumbing, not a user-facing role.
    Saves criteria to debate.critic.criteria when complete.
    """
    provider, model = _role_settings(settings, "critic")
    api_key = settings.api_key_for(provider)

    # Ensure the critic role result exists with provider/model set, so the UI
    # has the right metadata when the critic role itself starts.
    if debate.critic.provider == "":
        debate.critic.provider = provider
        debate.critic.model = model

    criteria_text = ""
    input_tokens = 0
    output_tokens = 0

    try:
        async for event in stream_model(
            provider=provider,
            model=model,
            api_key=api_key,
            system=CRITIC_CRITERIA_SYSTEM,
            user=debate.question,
        ):
            if event["type"] == "text":
                criteria_text += event["content"]
            elif event["type"] == "usage":
                input_tokens = event["input"]
                output_tokens = event["output"]
    except ProviderError as e:
        # If criteria generation fails, we proceed without criteria.
        # The critic will still run, just without independent guidance.
        debate.critic.criteria = ""
        save_debate(debate)
        yield sse({
            "type": "criteria_error",
            "message": f"Criteria step failed (proceeding without): {e}",
        })
        return
    except asyncio.CancelledError:
        debate.status = "stopped"
        save_debate(debate)
        raise

    debate.critic.criteria = criteria_text
    debate.critic.criteria_input_tokens = input_tokens
    debate.critic.criteria_output_tokens = output_tokens
    save_debate(debate)
    yield sse({
        "type": "criteria_complete",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    })


async def _drain_to_queue(
    gen: AsyncIterator[str],
    queue: asyncio.Queue,
) -> None:
    """Helper: forward all events from an async generator to a queue, then signal done."""
    try:
        async for event in gen:
            await queue.put(event)
    finally:
        await queue.put(None)  # sentinel: this generator is done


async def _run_proposer_and_criteria_in_parallel(
    debate: Debate, settings: Settings,
) -> AsyncIterator[str]:
    """Run the proposer (streaming, user-visible) and criteria (silent, background) concurrently.

    Both depend only on the question, so they have no data dependency on each other.
    Yields proposer events as they arrive; criteria events are mostly silent (just a
    completion ping at the end).
    """
    queue: asyncio.Queue = asyncio.Queue()

    proposer_task = asyncio.create_task(
        _drain_to_queue(_execute_role(debate, "proposer", settings), queue)
    )
    criteria_task = asyncio.create_task(
        _drain_to_queue(_execute_criteria_step(debate, settings), queue)
    )

    finished = 0
    try:
        while finished < 2:
            event = await queue.get()
            if event is None:
                finished += 1
                continue
            yield event
    except asyncio.CancelledError:
        proposer_task.cancel()
        criteria_task.cancel()
        # Wait briefly for cancellation to propagate
        await asyncio.gather(proposer_task, criteria_task, return_exceptions=True)
        raise

    # Surface any exceptions from the tasks
    for task in (proposer_task, criteria_task):
        if task.done() and not task.cancelled():
            exc = task.exception()
            if exc:
                # Errors should already have been yielded as SSE events by _execute_role
                # or _execute_criteria_step; we just don't want to swallow them silently.
                pass


async def run_debate_stream(
    debate: Debate, settings: Settings, start_from: RoleName = "proposer",
) -> AsyncIterator[str]:
    """Run a debate from `start_from` through to the judge, yielding SSE events.

    When starting from the proposer, runs the proposer and criteria-generation
    in parallel (both depend only on the question). The critic then runs with
    independent criteria as input.

    When resuming from critic or judge, prior outputs are reused as-is. Note
    that resuming from critic uses whatever criteria were stored on the original
    run; we don't regenerate criteria for retries.
    """
    # Emit the debate ID early so frontend can track it for retries
    yield sse({"type": "debate_started", "debate_id": debate.id})

    debate.status = "running"
    save_debate(debate)

    if start_from == "proposer":
        # Parallel: proposer + criteria
        async for event in _run_proposer_and_criteria_in_parallel(debate, settings):
            yield event
        # Stop if proposer errored
        if debate.proposer.status == "error":
            return
        # Then critic and judge sequentially
        for role in ["critic", "judge"]:
            async for event in _execute_role(debate, role, settings):
                yield event
            if debate.get_role(role).status == "error":
                return

    else:
        # Resuming from critic or judge: prior outputs already exist, no parallel needed
        start_idx = ROLE_ORDER.index(start_from)
        for role in ROLE_ORDER[start_idx:]:
            async for event in _execute_role(debate, role, settings):
                yield event
            if debate.get_role(role).status == "error":
                return

    debate.status = "complete"
    save_debate(debate)
    yield sse({"type": "done", "debate_id": debate.id})


# ============================================================
# ROUTES
# ============================================================
@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/settings")
def get_settings():
    s = load_settings()
    return {
        "anthropic_api_key_set": bool(s.anthropic_api_key),
        "openai_api_key_set": bool(s.openai_api_key),
        "google_api_key_set": bool(s.google_api_key),
        "proposer_provider": s.proposer_provider,
        "proposer_model": s.proposer_model,
        "critic_provider": s.critic_provider,
        "critic_model": s.critic_model,
        "judge_provider": s.judge_provider,
        "judge_model": s.judge_model,
    }


@app.post("/api/settings")
def update_settings(update: SettingsUpdate):
    s = load_settings()
    if update.anthropic_api_key:
        s.anthropic_api_key = update.anthropic_api_key
    if update.openai_api_key:
        s.openai_api_key = update.openai_api_key
    if update.google_api_key:
        s.google_api_key = update.google_api_key
    s.proposer_provider = update.proposer_provider
    s.proposer_model = update.proposer_model
    s.critic_provider = update.critic_provider
    s.critic_model = update.critic_model
    s.judge_provider = update.judge_provider
    s.judge_model = update.judge_model
    save_settings(s)
    return {"ok": True}


@app.post("/api/settings/clear-key/{provider}")
def clear_key(provider: str):
    """Explicitly clear a saved API key."""
    if provider not in ("anthropic", "openai", "google"):
        raise HTTPException(400, f"Unknown provider: {provider}")
    s = load_settings()
    if provider == "anthropic":
        s.anthropic_api_key = ""
    elif provider == "openai":
        s.openai_api_key = ""
    elif provider == "google":
        s.google_api_key = ""
    save_settings(s)
    return {"ok": True}


@app.post("/api/debate")
async def debate(request: DebateRequest):
    settings = load_settings()

    needed_providers = {settings.proposer_provider, settings.critic_provider, settings.judge_provider}
    for p in needed_providers:
        if not settings.api_key_for(p):
            raise HTTPException(400, f"API key not configured for provider: {p}")

    question = request.messages[-1].content if request.messages else ""
    if not question.strip():
        raise HTTPException(400, "Empty question")

    new_d = new_debate(question)
    save_debate(new_d)

    return StreamingResponse(
        run_debate_stream(new_d, settings, start_from="proposer"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/debate/resume")
async def resume_debate(request: ResumeRequest):
    """Resume an existing debate from a given role, reusing prior role outputs."""
    settings = load_settings()
    debate_obj = load_debate(request.debate_id)
    if debate_obj is None:
        raise HTTPException(404, f"Debate {request.debate_id} not found")

    needed_providers = {settings.proposer_provider, settings.critic_provider, settings.judge_provider}
    for p in needed_providers:
        if not settings.api_key_for(p):
            raise HTTPException(400, f"API key not configured for provider: {p}")

    # Validate that prior roles have content
    start_idx = ROLE_ORDER.index(request.from_role)
    for prior_role in ROLE_ORDER[:start_idx]:
        prior = debate_obj.get_role(prior_role)
        if not prior.text or prior.status != "complete":
            raise HTTPException(
                400,
                f"Cannot resume from {request.from_role}: prior role {prior_role} has no completed output",
            )

    return StreamingResponse(
        run_debate_stream(debate_obj, settings, start_from=request.from_role),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/debate/{debate_id}")
def get_debate(debate_id: str):
    """Load a saved debate's full state."""
    d = load_debate(debate_id)
    if d is None:
        raise HTTPException(404, f"Debate {debate_id} not found")
    return d.to_dict()


@app.get("/api/debates")
def list_debates(limit: int = 50):
    """List recent debates (metadata only)."""
    return {"debates": list_recent_debates(limit)}


@app.delete("/api/debate/{debate_id}")
def delete_debate_route(debate_id: str):
    """Delete a saved debate."""
    if delete_debate(debate_id):
        return {"ok": True}
    raise HTTPException(404, f"Debate {debate_id} not found")


@app.get("/api/list-models/{provider}")
def list_models(provider: str):
    """Return available models for a provider, using the saved API key."""
    if provider not in ("claude", "openai", "gemini"):
        raise HTTPException(400, f"Unknown provider: {provider}")

    settings = load_settings()
    api_key = settings.api_key_for(provider)
    if not api_key:
        raise HTTPException(400, f"No API key configured for {provider}")

    try:
        models = list_available_models(provider, api_key)
        return {"provider": provider, "models": models}
    except ProviderError as e:
        raise HTTPException(502, str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
