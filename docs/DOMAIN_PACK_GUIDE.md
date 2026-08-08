# Domain Pack 搭建指南

本指南说明如何以现有 `research` 包为模板，增加一个新垂直领域。建议按契约依赖顺序搭建，每一步都保持 `validate` 可运行。

## 1. 定义领域边界

创建 `domains/<domain-id>/domain.yaml`，先明确：

- include / exclude 范围。
- 目标用户与领域所有者。
- read、analyze、recommend、write 的自治级别。
- 默认风险等级与版本号。

范围必须能排除“不应该由这个 Agent 做”的任务，否则后续 Policy 很难收敛。

## 2. 建立领域语言与任务分类

创建：

- `ontology.yaml`：实体、关系、枚举和关键术语。
- `task-taxonomy.yaml`：每类任务的输入、风险、副作用、证据要求、所需 Capability 和完成条件。

任务 ID 推荐使用 `<domain>.<object>.<action>`，例如 `finance.filing.analyze`。

## 3. 设计 Capability

在 `capabilities/<domain-id>.yaml` 定义稳定的语义能力。粒度应表达业务动作，例如“检索申报文件”，而不是某个供应商的 API 方法名。

每项 Capability 至少明确：

- 输入与输出语义。
- read / write 分类。
- 是否产生副作用。
- 风险与证据要求。
- 超时、重试或幂等约束。

## 4. 编写 Skill

每个 Skill 放在 `skills/<domain-id>/<skill-id>/`，包含：

- `skill.yaml`：机器可读契约、输入输出、所需 Capability。
- `SKILL.md`：执行步骤、边界、失败处理和产出标准。

Skill 不应写死 Provider 名称、凭据或环境地址。它只请求 Capability。

## 5. 绑定 Provider

在 `mcp/bindings/<domain-id>.yaml` 将 Capability 映射到实现。生产接入时建议：

- 凭据由 Secrets / 环境注入，不写入仓库。
- 写操作支持幂等键。
- 明确超时和可重试错误。
- Provider 输出先做 Schema 校验，再交给下一个 Skill。

## 6. 定义 Agent 与 Policy

创建 `agents/<domain-id>/agent.yaml`，显式列出允许的 Task、Skill、Capability 与 Policy；在 `policies/<domain-id>/default.yaml` 定义：

- 哪些读取可自主执行。
- 哪些建议只允许生成草稿。
- 哪些写入需要审批。
- 哪些目标、数据或动作始终拒绝。

不要只依赖自然语言系统提示做权限控制，关键限制必须进入机器可执行 Policy。

## 7. 组合 Workflow 与 Schema

在 `domains/<domain-id>/workflows/` 定义显式状态与失败转移，在 `schemas/` 定义输入输出结构。每个状态只承担一个清晰动作，并为 Provider 故障、证据不足和策略拒绝保留明确路径。

## 8. 建立 Golden Evals

在 `evals/<domain-id>/golden.yaml` 至少覆盖：

- 正常成功路径。
- 无效输入与越界任务。
- 无足够证据。
- Capability 无法解析。
- Provider 故障。
- Policy 拒绝。
- 未批准写入与已批准写入。

## 9. 验收与迭代

```powershell
vertical-agent --root . validate --domain <domain-id>
vertical-agent --root . eval --domain <domain-id>
python -m pytest -q
```

上线前还应人工检查权限边界、凭据管理、真实副作用的幂等性、Trace 中的敏感信息脱敏，以及失败后的补偿策略。

完整字段规范见[Domain Package 标准](../02-DOMAIN_PACKAGE_SPEC.md)，批量生成和维护流程见[生成与维护工作流](../03-GENERATION_AND_MAINTENANCE_WORKFLOW.md)，验收要求见[Checklist 与 Evals](../05-CHECKLIST_AND_EVALS.md)。

