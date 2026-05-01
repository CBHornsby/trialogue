# Scorecards

`manual_eval_2026_05.jsonl` and `.csv` contain one row per eval run. The rows are intentionally concise: they are meant to support product decisions, regression selection, routing rules, and future automated scoring.

## Count

This scorecard has **30 scored runs across 29 exact unique prompts**. It includes reruns/regression-style tests, so it should not be described externally as 30 independent scenarios.

## Important fields

- `outcome`: qualitative eval result.
- `critic_real_issues`: count of useful critic findings.
- `critic_manufactured_issues`: count of obvious manufactured critic findings observed during manual review.
- `critic_missed_critical_issue`: normalized boolean.
- `critic_missed_critical_issue_detail`: nuance from manual notes, if any.
- `judge_introduced_error`: normalized boolean.
- `judge_introduced_error_detail`: description of the judge-introduced issue, if any.
- `judge_preserved_error`: normalized boolean.
- `judge_preserved_error_detail`: description of the preserved error, if any.
- `final_better_than_proposer`: normalized boolean.
- `final_better_than_proposer_detail`: nuance such as `minor`, `slight`, or `secondary_only`.
- `worth_full_trialogue`: normalized boolean for normal product use.
- `worth_full_trialogue_detail`: nuance such as `moderate`, `modest`, or `regression_only`.
- `needs_source_or_verifier`: normalized boolean.
- `needs_source_or_verifier_detail`: nuance such as `example_verifier`, `calculator_verifier`, or `lightweight_source_verifier`.
- `recommended_mode`: one of the five canonical routing modes.
- `recommended_mode_detail`: the original more specific routing recommendation.
- `notes`: concise qualitative finding.

## Canonical routing modes

- `single_model_quick`
- `normal_trialogue`
- `trialogue_plus_verifier`
- `source_required_trialogue`
- `professional_boundary`
