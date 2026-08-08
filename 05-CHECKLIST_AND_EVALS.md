# 验收、回归与质量检查

## 1. 架构检查

- [ ] Domain Scope 明确
- [ ] Include / Exclude 明确
- [ ] Agent 与 Harness 分离
- [ ] Skill 与 Tool 分离
- [ ] Capability 与 Provider 分离
- [ ] MCP Binding 独立
- [ ] Policy 不依赖模型自觉执行
- [ ] 输出有结构化 Schema
- [ ] Evals 已建立

## 2. Skill 检查

- [ ] 有版本
- [ ] 有 Trigger
- [ ] 有 Preconditions
- [ ] 有 Input/Output
- [ ] 只依赖 Capability
- [ ] 有 Validation
- [ ] 有 Failure Handling
- [ ] 有 Completion Criteria
- [ ] 无 Secrets
- [ ] 无无限递归

## 3. Capability 检查

- [ ] 使用稳定业务语义
- [ ] 无供应商名泄漏
- [ ] Risk Classification 完整
- [ ] Side Effect 正确
- [ ] Required Scope 明确
- [ ] Input/Output Schema 存在

## 4. MCP 检查

- [ ] Binding 独立
- [ ] 至少一个实现或标记 unresolved
- [ ] Health Check
- [ ] Timeout
- [ ] Retry 策略
- [ ] Rate Limit 处理
- [ ] Provider 替换不要求改 Skill

## 5. Policy 检查

- [ ] READ 规则明确
- [ ] WRITE 规则明确
- [ ] DESTRUCTIVE 明确
- [ ] PRIVILEGED 明确
- [ ] Approval 规则明确
- [ ] Forbidden Actions 明确
- [ ] Domain Policy 不绕过 Global Policy

## 6. Workflow 检查

- [ ] Initial State
- [ ] Terminal State
- [ ] Failure State
- [ ] Retry Behavior
- [ ] Approval State
- [ ] Long-running State
- [ ] Checkpoint
- [ ] Cancellation
- [ ] Replan Boundary

## 7. Evidence 检查

适用领域：

- [ ] Fact / Inference 区分
- [ ] Source 可追溯
- [ ] Timestamp 存在
- [ ] Trust/Quality 可记录
- [ ] Claim 有 Evidence
- [ ] Counter Evidence 可表达
- [ ] Assumption 可表达

## 8. Eval 最低覆盖

至少：

```text
5 Happy Path
5 Edge Case
5 Ambiguous
5 Tool Failure
5 Policy Boundary
5 Adversarial
```

即至少 30 个基础 Case。

关键领域建议 50-100 个 Golden Cases。

## 9. 通用 Metrics

```text
Task Completion Rate
Entity Resolution Accuracy
Skill Selection Accuracy
Capability Selection Accuracy
Tool Argument Accuracy
Evidence Coverage
Policy Violation Rate
Human Escalation Rate
Tool Error Rate
Replan Rate
Cost per Successful Run
P50 / P95 Latency
```

## 10. Release Gate

```yaml
release_gate:

  schema_validation:
    required: true

  dependency_validation:
    required: true

  policy_violation:
    maximum: 0

  critical_eval:
    minimum_score: 0.95

  unresolved_high_risk_capability:
    maximum: 0

  architecture_drift:
    maximum_critical_findings: 0
```

## 11. Architecture Drift

```text
Agent -> Vendor Tool
    FAIL

Skill -> Secret
    FAIL

Capability without binding
    WARN

High-risk capability without policy
    FAIL

Major task without eval
    FAIL

Workflow without failure path
    FAIL

Output without schema
    FAIL
```

## 12. Definition of Done

- [ ] Domain manifest
- [ ] Ontology
- [ ] Task taxonomy
- [ ] Agent manifest
- [ ] 至少 3 个 Domain Skills
- [ ] Capability registry
- [ ] MCP bindings
- [ ] Domain policies
- [ ] 至少 1 个核心 Workflow
- [ ] Structured output schema
- [ ] 至少 30 个 Eval Cases
- [ ] Trace 可关联 Agent/Skill/Capability/Tool
- [ ] Provider 可在不修改 Skill 的情况下替换
- [ ] Run 可记录完整版本信息
