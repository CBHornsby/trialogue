# Documentation

Design docs, specs, and notes for Trialogue.

## Contents

### `source-required-mode/`

Design and implementation spec for source-required mode, addressing the most consequential failure mode identified in the May 2026 evaluation: current-facts questions producing confidently-stated claims the system has no way to verify.

- [`v1-spec.md`](source-required-mode/v1-spec.md) — Architecture, components, success criteria, implementation order
- [`v1-prompts.md`](source-required-mode/v1-prompts.md) — Source-aware prompts for proposer, critic, and judge

## Conventions

Design docs in this folder follow these patterns:

- One subfolder per major feature or area
- Versioned filenames (`v1-spec.md`, `v2-spec.md`) so historical decisions remain inspectable
- Cross-references use relative paths so docs work both on disk and on GitHub

## Related

- [`../evals/`](../evals/) — Evaluation cases, scorecards, regression tests, and synthesis
- [`../README.md`](../README.md) — Project overview
