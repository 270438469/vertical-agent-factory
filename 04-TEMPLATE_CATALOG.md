# 通用模板库

## 1. Domain Requirement

```yaml
domain:
  id:
  name:
  description:

users: []

scope:
  include: []
  exclude: []

tasks: []
entities: []
sources: []
external_systems: []
write_actions: []

risk:
  prohibited: []
  approval_required: []

outputs: []
```

## 2. Domain Definition

```yaml
id:
version:
name:
description:

scope:
  include: []
  exclude: []

autonomy:
  read:
  analyze:
  recommend:
  execute:

risk:
  default:

owners: []
```

## 3. Ontology

```yaml
entities:
  EntityName:
    identifiers: []
    aliases: []
    properties: []

relations:
  - from:
    relation:
    to:

invariants: []
```

## 4. Task

```yaml
tasks:
  - id:
    class:
    description:
    required_entities: []
    required_capabilities: []

    evidence:
      required:

    side_effect:
    risk:
    completion: []
```

## 5. Agent

```yaml
id:
version:

domain:
  id:
  version:

task_types:
  allow: []

skills:
  allow: []

capabilities:
  allow: []
  deny: []

policies: []

runtime:
  max_steps:
  max_tool_calls:
```

## 6. Capability

```yaml
id:
description:

risk:
  class:
  level:

side_effect:
required_scopes: []
input_schema_ref:
output_schema_ref:
```

## 7. MCP Binding

```yaml
capability:

implementation:
  protocol: mcp
  server:
  tool:

priority:

conditions:
```

## 8. Skill

```markdown
---
id:
name:
version:

domain:
  id:

task_types: []
preconditions: []

inputs:
  required: []

outputs:
  required: []

requires:
  capabilities: []

policy:
  side_effect:

runtime:
  max_steps:
  max_tool_calls:
---

# Objective
# Procedure
# Validation
# Failure Handling
# Completion Criteria
```

## 9. Workflow

```yaml
id:
version:
initial_state:

states:
  STATE_NAME:
    action:
    next:
    on_failure:

terminal: []
```

## 10. Policy

```yaml
rules:
  - id:
    when: {}
    require: {}
    decision:
```

## 11. Domain Result

```json
{
  "status": "",
  "summary": "",
  "facts": [],
  "inferences": [],
  "evidence": [],
  "actions": [],
  "warnings": [],
  "uncertainties": [],
  "metadata": {}
}
```

## 12. Eval

```yaml
id:
task_type:

input:
  user:

fixtures: {}

expect:
  entities: []

  capabilities:
    must_use: []
    must_not_use: []

  skills: []
  policy: {}
  evidence: {}
  output: {}
```

## 13. Change Request

```yaml
change_request:

  domain:

  type:
    - add_task
    - add_skill
    - add_provider
    - change_policy
    - change_schema
    - refactor

  description:

  expected_behavior:

  compatibility:
    required: true

  rollout:
    strategy:
```

## 14. Release Note

```markdown
# Domain Package Release

Version:

## Added
## Changed
## Deprecated
## Removed
## Policy Changes
## Provider Changes
## Eval Result
## Migration Notes
```
