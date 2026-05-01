# REG-006: Stripe webhook livemode and delivery semantics

## Prompt

```text
How should I handle Stripe webhooks safely in production? I’m worried about duplicate events, fake requests, and events arriving out of order.
```

## Purpose

Prevent risky operational guidance around valid-but-irrelevant events and delivery guarantees.

## Required final-answer elements

- Verify signature using raw body and endpoint secret.
- Return `2xx` only after durable capture or durable enqueue.
- Return non-`2xx` if durable capture fails so Stripe retries.
- Deduplicate by event ID and make business handlers idempotent.
- Re-fetch Stripe object when needed for ordering/source-of-truth.
- For valid signed events that are irrelevant/wrong mode/wrong account, prefer safe ignore + `2xx` after logging rather than retry loops, unless provider docs or app design require otherwise.
- Phrase delivery as duplicate/retry/finite-window behavior, not an absolute infinite guarantee.

## Failure conditions

- Returns `400` for valid signed but wrong-mode event without explaining retry consequences.
- Says Stripe guarantees at-least-once delivery without caveat.
- Returns `200` before durable capture.

## Recommended mode

`source_required_trialogue`.
