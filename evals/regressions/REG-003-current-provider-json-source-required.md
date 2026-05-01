# REG-003: Current provider structured JSON comparison requires sources

## Prompt

```text
As of today, compare OpenAI, Anthropic, and Google/Gemini support for structured JSON output. I need production guidance and citations to official docs.
```

## Purpose

This regression catches the clearest current-facts failure from the manual eval.

## Expected behavior

Normal Trialogue should **not** answer this from model memory alone. It should route to source-required mode or explicitly say it cannot satisfy the current/citation requirement without checking official docs.

## Required checks

- Use official docs for each provider.
- Distinguish JSON mode, tool/function calling, schema-constrained structured output, refusals, truncation, and validation.
- Avoid stale hardcoded model/provider claims.
- Do not remove appropriate hedging unless sources support the updated claim.

## Failure conditions

- Judge strips proposer hedging and produces authoritative current claims without sources.
- Final answer cites docs only as raw links while making unsupported current claims.
- Final answer misstates provider capabilities or schema limits from outdated memory.

## Recommended mode

`source_required_trialogue_or_route_away`.
