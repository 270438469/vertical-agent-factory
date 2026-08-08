# Vertical Agent Factory

> 通用垂直领域 Agent / Harness / MCP / Skill 生成与维护框架

目标：以后只需要提供领域要求，即可按统一规范批量生成、更新和治理垂直领域 Agent 系统。

## 核心模型

```text
Agent        = 谁负责
Skill        = 怎么做
Capability   = 需要什么语义能力
MCP Tool     = 具体由什么实现
Harness      = 如何可靠、安全执行
Domain Pack  = 某一垂直领域的全部业务资产
Policy       = 允许做到什么程度
Eval         = 如何判断系统是否正确
```

核心原则：

> 垂直领域不是复制一套 Agent Runtime，而是在统一 Harness 上安装一个 Domain Package。

## 通用平台层

以下组件保持通用：

```text
Core Harness
MCP Gateway
Agent Runtime
Model Adapter
State / Checkpoint
Memory Infrastructure
Approval Infrastructure
Secrets
Tracing
Evaluation Runtime
Capability Resolver
Policy Engine
```

领域变化集中在：

```text
Domain Ontology
Task Taxonomy
Domain Skills
Domain Capabilities
Domain Knowledge
Domain Policy
Domain Workflows
Domain Output Schemas
Domain Evals
```

## 文件

- `SKILL.md`：Vertical Agent Factory 主 Skill。
- `01-VERTICAL_AGENT_FRAMEWORK.md`：总体架构规范。
- `02-DOMAIN_PACKAGE_SPEC.md`：Domain Package 标准。
- `03-GENERATION_AND_MAINTENANCE_WORKFLOW.md`：生成、批量搭建和维护流程。
- `04-TEMPLATE_CATALOG.md`：核心模板库。
- `05-CHECKLIST_AND_EVALS.md`：验收、回归和 Eval 规范。

## 后续输入示例

```yaml
domain:
  id: finance
  name: Financial Intelligence

scope:
  include:
    - US equities
    - China A-shares
    - global macro

tasks:
  - market snapshot
  - filing analysis
  - stock move explanation
  - macro analysis

data_sources:
  - SEC
  - SSE
  - SZSE
  - FRED
  - market data
  - news

autonomy:
  read: autonomous
  analyze: autonomous
  write: deny
```

将上述需求交给 `vertical-agent-factory` Skill，即可按统一规范生成完整 Domain Package。
