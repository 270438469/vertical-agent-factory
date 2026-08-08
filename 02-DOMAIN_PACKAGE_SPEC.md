# Domain Package 标准

## 1. 标准目录

```text
domains/<domain>/
├── domain.yaml
├── ontology.yaml
├── task-taxonomy.yaml
├── knowledge.yaml
├── schemas/
│   ├── query.json
│   ├── result.json
│   └── entities/
└── workflows/
    └── *.yaml

agents/<domain>/
├── agent.yaml
└── SYSTEM.md

skills/<domain>/
└── <skill-id>/
    ├── SKILL.md
    ├── skill.yaml
    └── tests/

capabilities/
└── <domain>.yaml

mcp/bindings/
└── <domain>.yaml

policies/<domain>/
└── *.yaml

evals/<domain>/
└── *.yaml
```

## 2. domain.yaml

```yaml
id: example-domain
version: 1.0.0
name: Example Domain
description: >

scope:
  include: []
  exclude: []

users: []

autonomy:
  read: autonomous
  analyze: autonomous
  recommend: autonomous
  write: approval_required

risk:
  default: medium

owners: []
```

## 3. ontology.yaml

```yaml
version: 1.0.0

entities:
  ExampleEntity:
    identifiers:
      - id
    aliases: []
    properties:
      - name
      - status

relations:
  - from: ExampleEntity
    relation: related_to
    to: ExampleEntity

invariants: []
```

## 4. task-taxonomy.yaml

```yaml
tasks:
  - id: domain.entity.read
    class: QUERY
    description: >

    required_entities:
      - ExampleEntity

    capabilities:
      - domain.entity.read

    evidence:
      required: true

    side_effect: false

    completion:
      - entity returned
```

## 5. agent.yaml

```yaml
id: example-domain-agent
version: 1.0.0

domain:
  id: example-domain
  version: 1.0.0

task_types:
  allow: []

skills:
  allow:
    - core.task-planning
    - core.mcp-tool-orchestration
    - core.result-validation

capabilities:
  allow: []
  deny: []

policies:
  - global
  - example-domain

runtime:
  max_steps: 20
  max_tool_calls: 30
```

## 6. Domain Skill

`SKILL.md` 的 frontmatter 只保存 Codex 用于触发的 `name` 和 `description`；
Harness 所需的版本、任务、输入输出、Capability 和 Policy 契约存放在相邻的
`skill.yaml`，避免产品元数据和运行时契约互相耦合。

```markdown
---
name: example-skill
description: Perform the example domain workflow. Use for domain.task requests.
---

# Objective

# Procedure

1. ...
2. ...

# Validation

# Failure Handling

# Completion Criteria
```

```yaml
# skill.yaml
id: example-domain.example-skill
version: 1.0.0
task_types: [domain.task]
preconditions: []
inputs:
  required: []
outputs:
  required: []
requires:
  capabilities: []
policy:
  side_effect: none
runtime:
  max_steps: 8
  max_tool_calls: 10
```

## 7. capabilities.yaml

```yaml
capabilities:
  - id: domain.entity.read
    description: >

    risk:
      class: READ
      level: low

    side_effect: false

    input_schema_ref:
    output_schema_ref:
```

## 8. bindings.yaml

```yaml
bindings:
  - capability: domain.entity.read

    implementation:
      protocol: mcp
      server: example-server
      tool: entity_read

    priority: 100
```

## 9. workflow.yaml

```yaml
id: domain.example-workflow
version: 1.0.0

states:
  RECEIVED:
    next: NORMALIZED

  NORMALIZED:
    action:
      skill: domain.normalize
    next: ANALYZED

  ANALYZED:
    action:
      skill: domain.analyze
    next: VALIDATED

  VALIDATED:
    action:
      skill: core.result-validation
    success: COMPLETED
    failure: FAILED

terminal:
  - COMPLETED
  - FAILED
```

## 10. policy.yaml

```yaml
rules:
  - id: allow-read
    when:
      risk_class: READ
    decision: allow

  - id: write-needs-approval
    when:
      side_effect: true
    decision: approval_required
```

## 11. Result Schema

```json
{
  "status": "SUCCESS",
  "summary": "",
  "facts": [],
  "inferences": [],
  "evidence": [],
  "actions": [],
  "uncertainties": [],
  "metadata": {}
}
```

## 12. Eval Case

```yaml
id: domain-case-001

task_type: domain.task

input:
  user: >

fixtures: {}

expect:
  entities: []

  capabilities:
    must_use: []
    must_not_use: []

  policy:
    allowed: true

  output:
    required_fields: []

  evidence:
    minimum: 1
```
