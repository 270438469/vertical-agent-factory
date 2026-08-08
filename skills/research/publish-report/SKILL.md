---
name: publish-report
description: Publish a prepared research report through an approved capability. Use only for explicit report publication requests after Harness policy approval.
---

# Publish Report

## Procedure

1. Confirm the destination and prepared report are present.
2. Request `research.report.publish` through the Harness.
3. Stop when approval is absent or policy denies the action.
4. Record the provider result as an action, not as inferred success.

## Validation

Require an approval decision before invoking the write provider.

## Failure handling

Do not retry an ambiguous write result automatically.

## Completion criteria

Return a structured action record or an explicit approval requirement.
