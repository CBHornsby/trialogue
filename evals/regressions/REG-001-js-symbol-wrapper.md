# REG-001: JavaScript Symbol wrapper example

## Prompt

```text
In JavaScript, are two Symbols with the same description equal? What about Object(s) == s?
```

## Purpose

Prevent recurrence of a prior judge bug where a correct Symbol wrapper example was rewritten into a false one.

## Required correct examples

```js
const s = Symbol("x");
Object(s) == s; // true
```

```js
Object(Symbol("x")) == Symbol("x"); // false
```

```js
Symbol("x") == Symbol("x"); // false
```

## Failure condition

The final answer must not claim:

```js
Object(Symbol("x")) == Symbol("x"); // true
```

## Recommended mode

`trialogue_plus_verifier` for broad JS `==` answers; `single_model_quick_or_verifier_regression` for the focused Symbol question.
