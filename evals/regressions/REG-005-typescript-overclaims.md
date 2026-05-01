# REG-005: TypeScript overclaim prevention

## Prompt

```text
Should I use TypeScript or JavaScript for a new web project starting today?
```

## Purpose

Catch broad technology-choice overclaims that survived some runs.

## Required final-answer elements

- Recommend TypeScript by default for serious/maintained web apps.
- Clearly state TypeScript does not validate runtime API/form/user input.
- Mention runtime validation for boundaries: Zod, Valibot, io-ts, JSON Schema/AJV, generated clients.
- Do not claim TypeScript catches wrong argument order generally; include same-type counterexample if discussing it.
- Do not claim TypeScript eliminates null/undefined runtime crashes.
- Mention linting for floating promises if discussing forgotten `await`.
- Mention JS + JSDoc/checkJs as a middle path.

## Failure conditions

- “TS eliminates most null/undefined crashes.”
- “TS catches wrong argument order” without caveat.
- “Native TS execution means type checking.”
- “The ecosystem assumes TS” as a universal claim.

## Recommended mode

`normal_trialogue_plus_overclaim_check`.
