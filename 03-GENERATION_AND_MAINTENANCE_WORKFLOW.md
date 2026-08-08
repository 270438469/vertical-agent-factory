# 生成、批量搭建与维护流程

## 1. 新领域生成流程

```text
Requirement
   ↓
Normalize Domain Request
   ↓
Generate Domain Boundary
   ↓
Generate Ontology
   ↓
Generate Task Taxonomy
   ↓
Generate Capabilities
   ↓
Generate Domain Skills
   ↓
Generate Workflows
   ↓
Generate MCP Bindings
   ↓
Generate Policies
   ↓
Generate Schemas
   ↓
Generate Golden Evals
   ↓
Validate Dependencies
   ↓
Package
```

## 2. 推荐输入模板

```yaml
domain:
  id:
  name:

goal:

users: []

scope:
  include: []
  exclude: []

tasks: []

entities: []

data_sources: []

external_systems: []

write_actions: []

autonomy:
  read:
  analyze:
  recommend:
  write:

risk:
  prohibited: []
  approval_required: []

freshness: []

evidence: []

outputs: []

non_functional:
  latency:
  cost:
  audit:
```

无需一次填满。

## 3. 维护模式

### Bootstrap

新建完整 Domain Package。

### Extend

增加 task / skill / capability / workflow / MCP provider / policy / schema / eval。

### Replace Provider

只替换 Binding/Adapter，不修改 Agent 和 Domain Skill。

### Policy Tightening

```text
allow -> approval -> deny
```

### Refactor

进行 capability rename、ontology merge、skill split、workflow extraction。

## 4. 变更影响分析

```text
                    CHANGE
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
    Ontology        Tasks        Policy
        │             │             │
        ▼             ▼             ▼
      Skills      Capabilities    Workflow
        │             │             │
        └───────┬─────┴───────┬─────┘
                ▼             ▼
             Schemas        MCP Bindings
                │             │
                └──────┬──────┘
                       ▼
                     Evals
```

## 5. Semantic Versioning

PATCH：

```text
修正文案
修复 validation
不改变 contract
```

MINOR：

```text
增加 Skill
增加 Task
增加 MCP Provider
增加可选字段
```

MAJOR：

```text
改变核心实体
改变 Skill 输入输出
改变 Capability 语义
改变 Agent 自治边界
```

## 6. Batch Generation

多个领域：

```text
Shared Core
├── task-planning
├── orchestration
├── validation
├── long-running-task
└── approval

Domain Packs
├── finance
├── web3
├── legal
├── ops
└── sales
```

重复的通用 Capability 应提升到 `capabilities/core.yaml`。

## 7. Provider 维护

绑定应维护：

```text
health
latency
cost
rate limit
permission
region
freshness
quality
```

解析策略：

```text
Capability
  ↓
Policy Filter
  ↓
Tenant Filter
  ↓
Healthy Providers
  ↓
Rank by Quality/Freshness/Latency/Cost
```

## 8. Skill 维护

每次 Skill 修改检查：

```text
Trigger
Input
Output
Capability Dependency
Policy
Completion Criteria
```

修改后运行：

```text
Skill Unit Eval
Domain Golden Eval
Regression
```

## 9. Release Gate

```text
schema validation = PASS
dependency validation = PASS
policy violation = 0
critical task eval >= threshold
no unresolved high-risk capability
no secret in artifacts
version manifest complete
```

## 10. Replay / Rollback

每次 Run 记录：

```text
Domain Package Version
Agent Version
Skill Versions
Capability Version
Policy Version
Binding Version
Model Config Version
```

这样可以 Replay、比较和回滚。
