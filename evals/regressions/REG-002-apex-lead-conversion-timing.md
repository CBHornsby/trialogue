# REG-002: Apex Lead conversion trigger timing

## Prompt

```text
How do I write an Apex trigger that prevents a Lead from being converted if the Account already has an active Contract, but allows it for users with the System Administrator profile?
```

## Purpose

This regression captures the highest-variance Salesforce/Apex case from the manual eval.

## Expected checks

A strong answer should:

- Question or reject `before update` reliance on `ConvertedAccountId` unless source-verified.
- Prefer `after update` for conversion-field availability.
- State that `addError()` in an after trigger can still roll back the conversion transaction.
- Use `without sharing` for the Contract enforcement query.
- Avoid `Map<AccountId, Lead>` if multiple Leads can convert to the same Account in one transaction.
- Prefer Custom Permission over hard-coded `Profile.Name` for production bypass.
- Include a test using `Database.LeadConvert.setAccountId(existingAccount.Id)`.

## Failure conditions

- Final answer confidently uses `before update` while relying on `ConvertedAccountId`.
- Final answer says `ConvertedAccountId` is guaranteed in `before update` without verification.
- Final answer uses `with sharing` for global Contract enforcement.
- Final answer drops multiple Leads converting to the same Account.

## Recommended mode

`source_required_or_platform_verifier`.
