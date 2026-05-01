# Evaluation status

This folder is a **manual eval snapshot from May 2026**.

It is intended to preserve product-learning evidence and seed future regression tests. It is not yet an automated CI suite.

## What this is

- A curated record of 30 scored Trialogue runs.
- A set of reusable prompts, rubrics, and regression tests.
- A routing map for deciding when to use:
  - quick/single-model mode,
  - normal Trialogue,
  - Trialogue plus verifier,
  - source-required Trialogue,
  - professional-boundary mode.

## What this is not

- A statistically rigorous benchmark.
- A blinded comparison against all single-model baselines.
- Proof that Trialogue is always better.
- A complete record of every raw token streamed during the eval.

## Next step

Use these evals to build an automated or semi-automated harness:

1. Run the frozen prompts against current Trialogue.
2. Score with the hidden rubrics.
3. Track judge-introduced errors, critic manufactured issues, and source-required routing failures.
4. Rerun the regression tests after every prompt or workflow change.
