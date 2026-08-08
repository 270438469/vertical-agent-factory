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

## 可执行系统

仓库现已包含共享 Harness 和一个完整的 `research` 示例 Domain Pack：

```text
vertical_agent_factory/  运行时、策略、解析、Trace、Eval 与 CLI
domains/research/        Domain、Ontology、Tasks、Knowledge、Schemas、Workflows
agents/research/         Agent Manifest 与系统约束
skills/research/         可执行 Skill 契约与 Codex Skill 指令
capabilities/            语义能力注册表
mcp/bindings/            Provider Binding（示例使用本地 Provider）
policies/                Domain Policy
evals/                   30 个 Golden Cases
```

快速验证：

```powershell
python -m vertical_agent_factory.cli --root . validate --domain research
python -m vertical_agent_factory.cli --root . run --domain research `
  --task research.answer.query --input "query=shared Harness"
python -m vertical_agent_factory.cli --root . eval --domain research
```

写操作默认要求审批。示例发布任务可用以下命令验证审批门：

```powershell
python -m vertical_agent_factory.cli --root . run --domain research `
  --task research.report.publish --input "target=demo"

python -m vertical_agent_factory.cli --root . run --domain research `
  --task research.report.publish --input "target=demo" `
  --approve research.report.publish
```

运行 Trace 写入 `.runs/<run-id>.jsonl`，可关联 Agent、Skill、Capability、Policy、Binding 和 Workflow 状态。

## 可视化 Web UI

`web/` 提供交互式系统地图，用于讲解运行链、Domain Pack 搭建流程、策略审批、
Provider 故障以及完整自测试结果。

```powershell
cd web
pnpm install
pnpm run dev
```

页面包含五种可执行 Trace 演示：证据查询、无足够证据、Provider 故障、审批拦截和已批准写入。
