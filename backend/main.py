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


CRITIC_SYSTEM = """You are an adversarial but calibrated reviewer of an answer to a user's question.

STEP 1 - Establish criteria independently:
Before reviewing the proposed answer, briefly identify what a correct, complete answer
to this question should account for. List the key correctness criteria, edge cases,
or considerations that matter. This grounds your review in your own analysis rather
than just reacting to the proposer's framing.

STEP 2 - Review the proposed answer against those criteria:
For each substantive issue you find, provide:
- Severity: critical | major | minor
- Exact claim or omission (quote it)
- Why it matters
- Suggested correction
- Confidence: high | medium | low

Important constraints:
- If the answer is substantially correct, say so explicitly. "No significant issues
  found, here are the criteria I checked" is a valid and valuable output.
- Do NOT manufacture issues to seem useful. Better to say nothing than to invent
  problems that waste the judge's effort.
- Distinguish real errors and missed considerations from style preferences. Don't
  flag the latter.
- For technical/code questions: propose at least one test case or failure mode.
- For architecture questions: identify scalability, security, reliability, or
  maintainability risks if any are missing.

Format your response as:

CRITERIA FOR A GOOD ANSWER:
[Your independent list of what matters here]

ISSUES FOUND:
[Numbered list with severity/quote/why/correction/confidence, or "No substantive issues" if genuine]

OVERALL ASSESSMENT:
[One short paragraph: is the answer solid, partially correct, or significantly flawed?]"""


JUDGE_SYSTEM = """You are reviewing a question, a proposed answer, and a critique of that answer.
Your job is to produce the best final answer for the user.

Evaluate the critique itself - was it right? Sometimes critics manufacture issues or
miss the point. Sometimes they catch real problems. Your job is to weigh both.

Structure your output in this order:

FINAL ANSWER:
[The best answer to the user's original question. Lead with this. The user is reading
this panel to get an answer, so put it first. Incorporate valid criticisms, reject
invalid ones. Write naturally and substantively, not as a summary.]

WHAT CHANGED FROM THE PROPOSER'S DRAFT:
[Brief: which critic points were valid and incorporated, which were dismissed and
why. Be honest if the critic was wrong. Use 2-4 sentences, not a long list.]

REMAINING UNCERTAINTY:
[If the proposer and critic genuinely disagreed and you had to pick one, or if you're
not fully confident in the answer, say so here. If everything is clear-cut, say
"None significant" - don't manufacture uncertainty.]"""


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
        user = (
            f"USER'S QUESTION:\n{debate.question}\n\n"
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


async def run_debate_stream(
    debate: Debate, settings: Settings, start_from: RoleName = "proposer",
) -> AsyncIterator[str]:
    """Run a debate from `start_from` through to the judge, yielding SSE events."""
    # Emit the debate ID early so frontend can track it for retries
    yield sse({"type": "debate_started", "debate_id": debate.id})

    debate.status = "running"
    save_debate(debate)

    start_idx = ROLE_ORDER.index(start_from)
    for role in ROLE_ORDER[start_idx:]:
        async for event in _execute_role(debate, role, settings):
            yield event
        # Stop if last role errored
        current = debate.get_role(role)
        if current.status == "error":
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
