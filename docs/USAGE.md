# 使用手册

本文覆盖环境准备、CLI 运行、审批、Trace、自测试、Web UI 和常见问题。若只想快速体验，可先访问[在线可视化实验室](https://vertical-agent-factory-lab.xuchong1999.chatgpt.site)。

## 1. 环境准备

核心运行时需要 Python 3.7+ 和 PyYAML。Web UI 需要 Node.js 22.13+ 与 pnpm 11。

```powershell
git clone https://github.com/270438469/vertical-agent-factory.git
cd vertical-agent-factory
python -m pip install -e .
```

验证安装：

```powershell
vertical-agent --help
```

如果没有安装 editable package，所有命令都可以改写为 `python -m vertical_agent_factory.cli ...`。

## 2. 校验 Domain Pack

```powershell
vertical-agent --root . validate --domain research
```

校验器会检查领域定义、Agent、Task、Skill、Capability、Provider Binding、Policy、Workflow、Schema 和 Eval 之间的引用是否闭合。应先修复校验错误，再运行任务。

## 3. 运行只读研究任务

```powershell
vertical-agent --root . run --domain research `
  --task research.answer.query `
  --input "query=shared Harness"
```

`--input` 使用 `key=value`；多个字段需要重复传入该参数，例如 `--input "query=..." --input "locale=zh-CN"`。运行时依次完成：

1. 加载 `research` Domain Pack。
2. 确认 Agent 允许该 Task。
3. 进入 `research.answer-workflow`。
4. 为每个 Skill 解析所需 Capability 与 Provider Binding。
5. 在工具调用前执行 Policy。
6. 搜索证据、合成答案并校验证据。
7. 输出结构化结果并写入 Trace。

当前示例知识库定义在 `domains/research/knowledge.yaml`。查询超出其证据范围时，系统会返回证据不足，而不是编造答案。

## 4. 验证审批门

先在未批准状态运行写任务：

```powershell
vertical-agent --root . run --domain research `
  --task research.report.publish `
  --input "target=demo"
```

Policy 会在 Provider 执行前返回审批要求。再显式传入批准项：

```powershell
vertical-agent --root . run --domain research `
  --task research.report.publish `
  --input "target=demo" `
  --approve research.report.publish
```

`--approve` 只代表本次运行提供了对应批准。生产环境应将其替换为带身份、时效、范围和审计信息的审批服务。

## 5. 查看 Trace

每次运行都会在仓库根目录的 `.runs/` 生成 `<run-id>.jsonl`。PowerShell 可这样查看最近一次运行：

```powershell
$latestRun = Get-ChildItem .runs\*.jsonl | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Get-Content $latestRun.FullName
```

重点检查：

- 任务和工作流状态是否符合预期。
- Skill 请求的 Capability 被解析到了哪个 Binding。
- Policy 决策发生在 Provider 调用之前。
- 失败是否保留明确错误类型，而不是被吞掉。
- 最终输出是否带有可追溯证据。

## 6. 运行完整自测试

后端与领域包：

```powershell
python -m pip install -e ".[api,api-test]"
python -m pytest -q
vertical-agent --root . validate --domain research
vertical-agent --root . eval --domain research
```

Web UI：

```powershell
cd web
pnpm install
pnpm run lint
pnpm test
```

`pnpm test` 会先执行生产构建，再运行服务端渲染 HTML 测试。当前基线是 60 个 Python 测试、30/30 Golden Evals 和 3 个 HTML 测试。

## 7. 运行 Web UI

```powershell
cd web
pnpm install
pnpm run dev
```

页面提供：

- Runtime：Agent → Skill → Capability → Policy → Binding → Trace 的执行链。
- Builder：Domain Pack 的搭建顺序和资产关系。
- Policies：只读、分析、建议和写入的自治边界。
- Scenarios：5 种可交互执行结果。
- Tests：系统自测覆盖面和当前基线。

在线地址：<https://vertical-agent-factory-lab.xuchong1999.chatgpt.site>

## 8. 常见问题

### 找不到 `vertical-agent`

确认执行过 `python -m pip install -e .`，或改用：

```powershell
python -m vertical_agent_factory.cli --root . validate --domain research
```

### `gh` 安装后仍提示不是命令

安装程序更新 PATH 后，旧终端不会自动刷新。关闭并重新打开 Git Bash / PowerShell，或在当前 PowerShell 直接运行：

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" auth status
```

### Eval 失败

先运行 `validate` 排除引用错误，再查看失败 case 的预期状态和最新 `.runs/*.jsonl`。修改知识、策略、绑定或工作流后，应重新运行全部 Golden Evals。

### Web UI 无法安装依赖

检查 `node --version` 与 `pnpm --version`，确保满足 `web/package.json` 中的版本要求。若没有 pnpm，可先执行 `corepack enable`，再进入 `web/` 安装。
