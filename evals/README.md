# Trialogue evals

This folder contains the initial manual evaluation assets for **Trialogue**, a local proposer → critic → judge multi-model review tool.

The goal of these evals is **not** to prove that three models are always better than one. The goal is to understand when the workflow:

- catches real issues in a plausible first answer,
- avoids manufactured critiques,
- improves the final answer rather than merely lengthening it,
- introduces or preserves new errors,
- is worth the added tokens/latency,
- needs source verification or a post-judge verifier.

## Eval snapshot

- **Date:** May 2026
- **Scope:** 30 scored runs across 29 exact unique prompts.
- **Note on count:** This set includes reruns and regression-style prompts. Do not read “30” as “30 fully independent/distinct product scenarios.”
- **Status:** Manual product-discovery eval, not an active CI suite yet.
- **Raw outputs:** Full transcripts are intentionally not committed. Keep raw debate logs locally in `evals/raw/` if you need to audit public claims later.

## High-level result

The manual eval suggests Trialogue is useful as a **structured review workflow for hard prompts**, especially production code, security/ops, architecture, ambiguous engineering decisions, and high-stakes procedural triage. It is overkill for simple questions and unsafe for current/source-sensitive questions without a source layer.

## Folder layout

```text
evals/
  README.md
  STATUS.md
  .gitignore
  cases/
    manual_eval_cases.jsonl
    README.md
  scorecards/
    manual_eval_2026_05.jsonl
    manual_eval_2026_05.csv
    README.md
  regressions/
    REG-001-js-symbol-wrapper.md
    REG-002-apex-lead-conversion-timing.md
    REG-003-current-provider-json-source-required.md
    REG-004-s3-presigned-post-cors.md
    REG-005-typescript-overclaims.md
    REG-006-stripe-webhook-livemode-and-delivery.md
    REG-007-judge-critic-rejection.md
  synthesis/
    combined_findings.md
    chatgpt_synthesis.md
    claude_synthesis_key_points.md
  schema/
    scorecard.schema.json
    case.schema.json
  scripts/
    summarize_scorecard.py
  raw/
    README.md
    .gitkeep
```

## Canonical routing modes

The scorecard uses **five canonical modes** in `recommended_mode`. More specific recommendations are preserved in `recommended_mode_detail`.

| Canonical mode | Use when |
|---|---|
| `single_model_quick` | Simple, stable, low-stakes prompts where a first answer is likely enough. |
| `normal_trialogue` | Hard technical, architecture, code-review, creative critique, or ambiguous decision prompts where review adds value but sources are not required. |
| `trialogue_plus_verifier` | Code/spec/math/security examples where final examples, calculations, or high-stakes recommendations should be checked after the judge. |
| `source_required_trialogue` | Current facts, APIs, product docs, pricing, platform behavior, provider capabilities, or citation requests. |
| `professional_boundary` | Legal, medical, financial, or other high-stakes professional domains where the answer must stay bounded and may require human expert review. |

## Interpreting the scorecard

The scorecard normalizes boolean fields for analysis. If a field had nuance in the original manual notes, the nuance is stored in a sibling `_detail` field.

Examples:

- `judge_introduced_error`: boolean
- `judge_introduced_error_detail`: text such as `provider_schema_limit_overclaim`
- `worth_full_trialogue`: boolean for normal product use
- `worth_full_trialogue_detail`: text such as `moderate` or `regression_only`

## Public-claim guidance

Safe claims from this eval:

- Early manual evals suggest Trialogue often hardens plausible technical answers.
- The critic role was the most consistently valuable part of the workflow.
- The tool is category-dependent, not universally useful.
- Current/source-sensitive questions need retrieval or verification.
- Simple questions usually do not justify full Trialogue.

Claims to avoid:

- “Trialogue eliminates hallucinations.”
- “Three models are always better than one.”
- “The critic never fabricates issues.”
- “It improves answers by X%.”
- “It is ready for non-developers.”

## Methodological limitations

This was a manual, non-blinded, selected-prompt eval. It did not systematically compare every prompt against single-model baselines. Claude and ChatGPT analyses cross-pollinated during the process. Treat the scorecards as product-discovery evidence, not statistical proof.
