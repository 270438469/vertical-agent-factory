---
name: search-evidence
description: Search configured research knowledge for traceable evidence. Use for evidence-first research queries before synthesis or reporting.
---

# Search Evidence

## Procedure

1. Normalize the query without changing its meaning.
2. Invoke `research.evidence.search` through the Harness.
3. Preserve source, title, timestamp and trust metadata.
4. Return an empty evidence collection when nothing relevant is found; do not invent material.

## Validation

Require every evidence item to have an identifier and source.

## Failure handling

Propagate provider failures so the workflow can enter its failure path.

## Completion criteria

Return a bounded, ranked evidence collection or an explicit empty collection.
