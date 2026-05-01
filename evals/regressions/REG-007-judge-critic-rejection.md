# REG-007: Judge must be able to reject bad critic points

## Purpose

The manual eval had many accepted critic points and almost no true rejection tests. This regression is a meta-test for adjudication.

## Candidate prompts

```text
Can TypeScript validate API responses at runtime if I define the right interface?
```

Inject or observe whether the critic falsely suggests that interfaces can validate at runtime. The judge must reject that.

```text
Should I always use Kafka for event-driven architecture?
```

If the critic overcorrects toward Kafka as the safest default, the judge must reject that and preserve proportionality.

```text
In JavaScript, are two Symbols with the same description equal? What about Object(s) == s?
```

If the critic makes the old bad claim about boxed fresh Symbols being equal, the judge must reject it.

## Required behavior

The judge should explicitly mark wrong critic points as `REJECTED`, not silently ignore or absorb them.

## Recommended mode

`normal_trialogue` with explicit adjudication metrics.
