# Combined findings from the initial Trialogue eval

Manual eval period: May 2026  
Approximate coverage: 30 scored runs across 29 exact unique prompts; includes reruns and regression-style prompts across code/spec, architecture, security/ops, Salesforce/platform configuration, LLM-app engineering, current API/provider facts, ambiguous decisions, creative critique, math/reasoning, simple restraint, and legal/business-risk triage.

## Core conclusion

Trialogue is useful, but not universally. It is best understood as a **structured review workflow for hard prompts**, not a truth oracle and not a general chatbot replacement.

The recurring pattern was:

```text
plausible proposer answer → calibrated critic catches gaps → judge hardens final answer
```

The models often agreed on the headline recommendation. The value was usually in catching operational details, edge cases, unsafe assumptions, or unsupported specificity.

## Highest-confidence findings

### 1. The critic is the most consistently valuable role

Across the manual eval, the critic repeatedly found real issues and showed good restraint. It found no obvious manufactured issues in our manual review, though this should be stated cautiously and not converted into a guarantee.

Examples:

- TypeScript parser: invalid `Date`, Zod trim/min order, `z.coerce.date()` permissiveness.
- React fetch: stale previous-user state when `userId` becomes null.
- Kubernetes probes: incorrect `initialDelaySeconds` explanation.
- Stripe webhooks: durable capture before returning `2xx`.
- Legal C&D: evidence preservation, jurisdiction caveat, public-statement risk, extension request.

### 2. The tool often hardens plausible technical answers

The proposer was often already good. The tool's value was making good answers safer. This was strongest in production code, security/ops, architecture, and LLM-app engineering.

### 3. Simple questions usually do not justify full Trialogue

Python mutable defaults and Symbol equality were clean runs, but mostly proved critic restraint. A single model or quick mode would usually be enough.

### 4. Source-sensitive/current questions require source mode

The structured-output provider comparison was the clearest failure. The user asked for current, cited facts. The critic correctly flagged staleness, but the judge made the answer more authoritative without actual source verification. Normal Trialogue is not sufficient for these prompts.

### 5. The judge is both useful and risky

The judge often integrates critic feedback well. But it can add or preserve errors, especially when generating examples, platform-specific claims, or current provider/API specifics. This supports a post-judge verifier.

### 6. Run-to-run variance is real

Apex Lead conversion was the key variance case. One run caught critical bugs. Later reruns missed the central trigger-timing issue and preserved or introduced Salesforce-specific mistakes. Regression tests should be rerun multiple times.

## Safe external claims

- Early manual evals suggest Trialogue often hardens plausible technical answers.
- The critic role was consistently valuable in this eval.
- The tool is category-dependent, not universally useful.
- Current/source-sensitive questions need source verification.
- Simple questions often do not justify full Trialogue.

## Claims to avoid

- Trialogue eliminates hallucinations.
- Three models are always better than one.
- The critic never fabricates issues.
- It improves answers by a specific percentage.
- It is ready for non-developers.
- It replaces professional advice for legal, medical, or financial decisions.

## Product roadmap implied by the eval

1. Routing/triage before full Trialogue.
2. Source-required mode for current/platform/provider/legal/financial/medical specifics.
3. Post-judge verifier for examples, code, calculations, and platform-specific claims.
4. Eval dashboard / structured scoring table.
5. Bad-critic rejection tests.
6. Final-answer vs audit-trail UI split.
7. Quick/single-model mode.
8. Non-developer packaging only after power-user value is validated.
