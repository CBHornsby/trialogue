# REG-004: S3 presigned upload details must not be dropped

## Prompt

```text
How should I design user file uploads for a web app using S3? Users upload images and PDFs. I want it to be secure and scalable.
```

## Purpose

The judge improved IAM/reliability but dropped some practical proposer details in one run. This regression ensures useful implementation details survive synthesis.

## Required final-answer elements

- Browser never receives AWS credentials.
- Backend signs presigned URL/POST with least-privilege role.
- Prefer presigned POST for user uploads when policy constraints matter.
- Include upload-time policy constraints:
  - `content-length-range`
  - key prefix/exact key
  - declared content type where practical
- Include bucket CORS requirements for browser direct upload.
- Treat S3 events as duplicate/delayed/at-least-once.
- Use idempotent worker, retries, DLQ, reconciliation.
- Quarantine bucket → clean bucket pattern.

## Failure conditions

- Final answer improves architecture but omits CORS and POST policy constraints.
- Final answer trusts client-declared content type.
- Final answer assumes S3 event delivery is exactly-once.

## Recommended mode

`source_required_trialogue_plus_verifier`.
