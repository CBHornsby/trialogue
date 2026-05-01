# Source-Required Mode v1 Specification

**Status:** Design spec for implementation
**Goal:** Address the most consequential failure mode identified in the May 2026 evaluation — current-facts questions producing confidently-stated claims the system has no way to verify.

## What this fixes

The eval's strongest negative finding came from the OpenAI/Anthropic/Gemini structured output comparison question. The user explicitly asked for current state with citations. The proposer correctly hedged about its knowledge cutoff. The critic flagged the cutoff as inadequate. The judge stripped the hedging and produced confident currency claims the system had no way to verify. The final answer was less reliable than the proposer's draft would have been on its own.

Source-required mode addresses this by adding a retrieval layer that anchors the proposer/critic/judge in fetched source content rather than relying on training data for current facts.

## Architecture overview

```
question
   ↓
[detection layer]
   ↓
[source-needed decision]
   ↓
   ├─→ if normal_trialogue: existing pipeline
   └─→ if source_required:
          ↓
       [retrieval layer]
          ↓
       [source packet]
          ↓
       [proposer | critic | judge with source-aware prompts]
          ↓
       [final answer with citations]
```

Detection gates the proposer. The proposer never starts generation before the source-needed decision is made and (if needed) sources retrieved.

## Components

### 1. Detection layer

**Hard rules first.** Pattern-match obvious cases without invoking an LLM:

- Time-anchored phrases: "as of today", "current", "latest", "today", "recent"
- Citation requests: "with citations", "official docs", "primary sources"
- Currency-sensitive nouns: "pricing", "release notes", "API support", "current limits", "supported models"
- Regulation-sensitive nouns: "laws", "regulations", "policy", "compliance"
- Version-specific: "version X.Y", "in [provider]'s latest"

These should immediately set `requires_sources = true` without any LLM call.

**Cheap LLM classifier for ambiguous cases.** When hard rules don't decide, invoke a fast/cheap model (Haiku 4.5, GPT-4o-mini, or Gemini Flash — pick whichever ecosystem is already configured).

The classifier returns the SourceNeedDecision object. Keep the prompt focused: given a question, decide if it requires current factual lookup, what kind of sources, and what queries to run.

**Output: SourceNeedDecision**

```typescript
interface SourceNeedDecision {
  mode: "normal_trialogue" | "source_required_trialogue";
  requires_sources: boolean;
  confidence: "low" | "medium" | "high";
  reason: string;
  source_policy: "none" | "official_docs_preferred" | "primary_sources_required" | "current_web_required";
  query_plan: string[];
  preferred_domains: string[];
}
```

This is the stable contract. Implementation behind it can evolve (rules → classifier → agentic) without breaking the rest of the system.

**Manual override.** UI must allow users to:
- Override auto-detected source mode → run without sources
- Override auto-detected normal mode → require sources
- Add manual source URLs at any time

Override is a permanent UX feature, not a v1 fallback.

### 2. Retrieval layer

**Search provider interface.** Define an abstract `SearchProvider` so v1 implementation can be swapped later.

```python
class SearchProvider:
    async def search_and_fetch(
        self,
        queries: list[str],
        preferred_domains: list[str],
        max_sources: int = 5,
    ) -> list[Source]:
        ...
```

**v1 implementation: Tavily.** Tavily is purpose-built for LLM agents, returns cleaned content, and minimizes time-to-ship. Use it behind the SearchProvider interface so Brave + Trafilatura can replace it later for cost and control.

**Passage extraction, not first-N-chars.** For each fetched source:
1. Strip boilerplate (nav, scripts, comments, footers).
2. Split into paragraphs.
3. Score paragraphs by query-term overlap with the original question.
4. Keep top 3 passages per source.
5. Preserve surrounding context where relevant.

Do not pass the first 2,000 characters. The relevant evidence is often deeper in the document.

**Source packet structure.**

```typescript
interface Source {
  id: string;          // "S1", "S2", etc.
  title: string;
  url: string;
  publisher: string;   // e.g., "Anthropic", "MDN", "SEC"
  retrieved_at: string;  // ISO timestamp
  published_at?: string; // if extractable
  fetch_status: "success" | "partial" | "failed";
  passages: Passage[];
}

interface Passage {
  text: string;
  score: number;  // relevance score
  position: number;  // approximate location in document
}

interface SourcePacket {
  generated_at: string;
  decision: SourceNeedDecision;
  sources: Source[];
  retrieval_errors: string[];  // any URLs that failed, why
}
```

**Cost ceilings (start values, tune from data):**
- Max sources per query: 5
- Max passages per source: 3
- Max passage tokens: 1,500
- Max source packet tokens: 10,000
- Retrieval timeout: 15 seconds total

**Prompt injection handling.** Retrieved web content is untrusted. Wrap it in clearly-delimited XML tags. Tell models explicitly to treat content within `<source>` tags as data, not instructions. Strip obvious injection patterns where feasible during extraction.

### 3. Failure handling

**Never silently fall back to normal mode** when source-required was triggered but retrieval failed.

Three explicit options at the failure point:

```
Source-required mode was triggered, but sufficient sources could not be retrieved.

Options:
1. Add source URLs manually
2. Continue with an unsourced answer, clearly labeled
3. Cancel
```

The user's choice determines next behavior. If they choose option 2, the final answer must include a prominent disclaimer that no sources were available.

### 4. Prompt updates

**All three roles receive the same source bundle.** Different views create synthesis problems — the judge cannot adjudicate claims it cannot verify against the same evidence the others saw.

**Citation requirement: inline [S1], [S2] format plus source list at the bottom.**

Example output:
```
OpenAI supports schema-constrained structured outputs through the response_format parameter [S1].

...

Sources:
[S1] OpenAI Structured Outputs Guide — https://platform.openai.com/docs/... — retrieved 2026-05-01
[S2] Anthropic Tool Use Guide — https://docs.anthropic.com/... — retrieved 2026-05-01
```

**Role-specific prompt updates.** See `SOURCE_AWARE_PROMPTS_V1.md` for full text.

Key behaviors:
- **Proposer:** Answer only from sources. Every factual claim cites [Sn]. Mark `[UNSOURCED]` when sources don't cover something.
- **Critic:** Verify each cited claim is actually supported. Output structured JSON: `{verified, unsupported, conflicts, gaps}`.
- **Judge:** Preserve hedging. May not upgrade unsourced or contested claims to confident ones. Add explicit "Coverage Gaps" section.

### 5. Persistence

**Embed the source packet in the existing debate JSON.** No separate database for v1.

```json
{
  "id": "...",
  "question": "...",
  "mode": "source_required_trialogue",
  "source_packet": {
    "generated_at": "...",
    "decision": {...},
    "sources": [...],
    "retrieval_errors": [...]
  },
  "proposer": {...},
  "critic": {...},
  "judge": {...}
}
```

This enables debugging, eval reproduction, and future regression testing.

### 6. UI

**Mode visibility:** Show the user what mode is selected and why.

```
[Source mode selected automatically]
Reason: question asks for current provider documentation

[View sources] [Add source] [Run without sources]
```

For normal mode:
```
[Normal mode selected]
[Require sources]
```

**Progress indicators during retrieval.** Source-required mode adds 5-15 seconds of pre-work. Stream status:
- "Detecting whether sources are needed..."
- "Searching official docs..."
- "Fetching source pages..."
- "Extracting relevant passages..."
- "Starting proposer..."

**Source list rendering.** In the final output, render the source list as a structured component, not just text. Each source clickable. Citation links jump to the source they reference.

## v1 Success Criteria

v1 is done when these four gates pass:

1. **Provider comparison regression passes.** The OpenAI/Anthropic/Gemini structured output question (eval case `current_structured_json_providers_001`) routes to source-required mode, cites official docs, marks uncovered claims, and does not strip proposer hedging.

2. **PDF limits regression passes.** A Gemini-PDF-style document analysis question routes to source-required mode and includes coverage gaps when sources are incomplete.

3. **Platform-specific regression passes.** A Salesforce/Apex source-sensitive question either retrieves primary docs or clearly marks unsupported platform claims as unverified.

4. **Retrieval failure protected.** When source-required is triggered but retrieval fails, the system surfaces the three-option fallback UX. It never produces a confident unsourced answer.

**Optional performance target.** Source-required prework starts streaming status within 1 second. Retrieval completes or fails within 15 seconds. Full debate may take longer, but the UI must show progress throughout.

## Implementation order

Build in this sequence to minimize risk:

1. **SourceNeedDecision contract + hard rules.** Stable interface, no LLM dependency. Test with the regression cases.
2. **Source packet schema + persistence.** Structure for storing sources in debate JSON.
3. **Tavily integration behind SearchProvider interface.** Retrieval works end-to-end.
4. **Source-aware prompts for all three roles.** Including prompt injection safeguards.
5. **UI: mode display, progress indicators, source rendering.**
6. **Failure handling UX.**
7. **Cheap classifier for ambiguous cases.** Last because hard rules cover most regression cases without it.
8. **Regression test suite.** Extend existing eval cases' `hidden_rubric` with source-mode assertions.

## What v1 does not include

These are deliberately deferred to v2 or v3:

- Multi-query search planning beyond what the classifier produces
- Reranking via cross-encoder models (e.g., bge-reranker)
- Source quality scoring beyond domain-tier heuristics
- Conflict detection via NLI models
- Source sufficiency checking (does retrieval answer the question?)
- Targeted follow-up retrieval
- Critic having a "search-more" tool
- Claim-level verification
- Multi-hop research
- Separate source database
- Caching of retrieval results

These are real value additions but each requires substantial work. v1 ships the durable contract; v2 and v3 improve the implementations behind it.

## Open questions for implementation

These don't block starting work but should be answered as you build:

- **Latency budget:** What's the actual UX cutoff where users will think the tool froze? Target 1-second feedback, 15-second retrieval, but verify with real testing.
- **Cost ceiling enforcement:** What happens when a query would exceed the source packet token budget? Truncate which sources first?
- **Caching:** When the same question is asked twice within a short window, should retrieval be cached? Probably yes for v2, but v1 can skip this.
- **Domain allowlists:** Should certain question categories have hard preferences (e.g., Salesforce questions → developer.salesforce.com)? Start without this; add if regression tests reveal need.
- **Manual source UX:** When the user adds a source URL manually, does the system fetch and validate it, or trust the URL as-is? For v1, fetch and validate; reject if unfetchable.

## Stable contracts (do not break in v2/v3)

These interfaces must remain stable across versions so tests written against v1 still validate v2 and v3:

- `SourceNeedDecision` object shape
- `Source` and `SourcePacket` object shapes
- Citation format ([Sn] inline + numbered source list)
- Mode names (`normal_trialogue`, `source_required_trialogue`)
- Persistence structure (source packet embedded in debate JSON)
- Failure UX three-option fallback

Implementation details that can change freely:

- Detection internals (rules → classifier → agentic)
- Search provider (Tavily → Brave+Trafilatura → multi-provider fusion)
- Passage extraction algorithm
- Reranking approach
- Specific cost ceilings (numeric tuning)
- Prompt wording (as long as the structural rules are preserved)

## References

- Eval synthesis: see `evals/synthesis/combined_findings.md`
- Eval case for primary regression: `evals/cases/manual_eval_cases.jsonl` — `current_structured_json_providers_001`
- Existing debate persistence: `~/.debate-tool/debates/{id}.json`
- Source-aware prompts: `./v1-prompts.md`
