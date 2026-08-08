# 通用垂直 Agent 架构框架

## 1. 总体结构

```text
                           Product / UX
                               │
                               ▼
                      Vertical Domain Agent
                               │
                     ┌─────────▼─────────┐
                     │    Domain Pack    │
                     │ Domain            │
                     │ Ontology          │
                     │ Tasks             │
                     │ Skills            │
                     │ Workflows         │
                     │ Knowledge         │
                     │ Policies          │
                     │ Schemas           │
                     │ Evals             │
                     └─────────┬─────────┘
                               │
                               ▼
                     ┌───────────────────┐
                     │   Shared Harness  │
                     │ Context           │
                     │ Planner           │
                     │ Skill Resolver    │
                     │ Capability Resolve│
                     │ Policy            │
                     │ Approval          │
                     │ Executor          │
                     │ Checkpoint        │
                     │ Validation        │
                     │ Trace             │
                     └─────────┬─────────┘
                               │
                               ▼
                       Capability Layer
                               │
                               ▼
                         MCP Gateway
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
             MCP Server A  MCP Server B  MCP Server C
```

## 2. 五层模型

```text
L5 Product
Chat / API / Dashboard / Alert / Automation

L4 Domain Package
Ontology / Tasks / Skills / Workflow / Knowledge / Policy / Schema / Eval

L3 Agent Intelligence
Agent / Planning / Skill Selection / Reasoning / Replanning

L2 Harness
Runtime / State / Policy / Approval / Executor / Memory / Validation / Trace

L1 Capability Infrastructure
Capability Registry / MCP Gateway / MCP Servers / Credentials / Storage
```

## 3. 通用与领域边界

只维护一套：

```text
Agent Runtime
Harness Loop
MCP Gateway
Policy Engine
Approval Engine
Tool Executor
State Store
Trace
Evaluation Runtime
Model Adapter
Secrets
```

随领域变化：

```text
domain.yaml
ontology.yaml
task-taxonomy.yaml
agent.yaml
SKILL.md
capabilities.yaml
bindings.yaml
workflows
policies
schemas
evals
knowledge config
```

## 4. 依赖不变量

```text
Agent -> Skill -> Capability -> Binding -> MCP Tool
```

禁止：

```text
Agent -> vendor tool
Skill -> secret
LLM -> policy bypass
```

## 5. Agent 与 Workflow 的分工

Agent-heavy：

```text
分析
研究
信息整合
解释
诊断
假设生成
```

Workflow-heavy：

```text
高风险写操作
审批
固定业务流程
长任务
多阶段验证
金融/生产动作
```

推荐：

```text
Deterministic Workflow
+
LLM Reasoning Nodes
```

## 6. 标准 Context

每轮构造：

```text
System Policy
Domain Definition
Agent Role
Applicable Skills
Current Goal
Structured Entities
Current Workflow State
Relevant Knowledge
Live Evidence
Available Capabilities
Policy Constraints
Output Schema
```

不要默认注入：

```text
全部历史
全部 Skill
全部 MCP Tool
全部知识库
```

## 7. 标准 Trace

```json
{
  "trace_id": "...",
  "run_id": "...",
  "step_id": "...",
  "agent_id": "...",
  "skill_id": "...",
  "domain": "...",
  "event_type": "...",
  "status": "...",
  "timestamp": "..."
}
```

建议事件：

```text
run.started
domain.loaded
agent.selected
skill.selected
plan.created
capability.resolved
policy.allowed
policy.denied
approval.requested
tool.started
tool.completed
workflow.transitioned
validation.completed
run.completed
run.failed
```

## 8. 通用质量目标

每个 Domain 都应验证：

```text
是否选对 Agent？
是否选对 Skill？
是否选对 Capability？
是否选对 Tool？
是否拿到正确 Evidence？
是否违反 Policy？
是否产生正确 Output？
能否 Replay？
能否 Regression Test？
```
