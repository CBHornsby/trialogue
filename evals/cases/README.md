# Eval cases

`manual_eval_cases.jsonl` contains reusable prompt records plus hidden rubrics.

Each row contains:

- `id`
- `category`
- `prompt`
- `recommended_mode`
- `recommended_mode_detail`
- `hidden_rubric`
- `expected_failure_modes`

The cases are a mix of:

1. **Regression cases** — known failure modes that should be checked after product/prompt changes.
2. **Routing cases** — prompts that clarify when to use quick mode, normal Trialogue, verifier mode, source-required mode, or professional-boundary mode.
3. **Descriptive eval cases** — prompts that preserve product-learning findings from the manual eval.

All cases now include at least a minimal rubric. The rubrics are intentionally compact; they are seed criteria for future automated or human scoring, not exhaustive domain checklists.

## Notes

- `tool_usefulness_self_eval_001` is intentionally included. It reflects a real Trialogue run on the product-strategy question about whether the tool is useful or overengineered.
- Regression/rerun cases are intentionally included because run-to-run variance was one of the evaluation findings.
