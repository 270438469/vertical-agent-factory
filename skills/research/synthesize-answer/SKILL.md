---
name: synthesize-answer
description: Synthesize a structured research answer from retrieved evidence. Use after evidence collection to separate facts, inferences, and uncertainty.
---

# Synthesize Answer

## Procedure

1. Read only the evidence supplied by the workflow.
2. Separate facts from inferences and assumptions.
3. Attach evidence references to factual output.
4. Withhold a confident answer when evidence is insufficient.

## Validation

Do not emit `SUCCESS` for factual output without evidence.

## Failure handling

Return `INSUFFICIENT_EVIDENCE` when the evidence set is empty.

## Completion criteria

Return a result matching the domain result contract.
