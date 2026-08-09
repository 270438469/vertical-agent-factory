# 全面自测试报告

测试日期：2026-08-09  
测试分支：`bussiness_type`  
测试基线：`42a2c1c Add no-code agent setup center`

## 发布结论

**PASS（所有当前环境可执行的发布门均通过）**。

Python、商业 API、无代码配置后台、Agent Domain Pack、Golden Evals、Web UI、生产构建、服务端渲染、Python 3.7 语法兼容、Git 空白检查、密钥模式扫描和运行时忽略规则全部通过。

Docker 镜像构建未执行：本机已安装 Docker CLI 29.1.3，但 Docker Desktop Linux daemon 未启动。该项记录为环境不可用，不属于代码测试失败；启用 Docker Desktop 后可执行 `docker build -t vertical-agent-factory:self-test .` 补验。

## 测试结果

| 测试门 | 结果 | 证据 |
|---|---:|---|
| Git 远端同步 | PASS | 本地与 `origin/bussiness_type` 的 ahead/behind 为 `0/0`，`git pull --rebase` 返回最新 |
| Python 全量测试 | PASS | `60 passed` |
| Domain Pack 校验 | PASS | `research` 返回 `PASS` |
| Golden Evals | PASS | `30 passed, 0 failed` |
| Web ESLint | PASS | 无错误、无警告 |
| Web 生产构建 | PASS | `/` 与 `/setup` 路由构建成功 |
| Web SSR HTML | PASS | `3 passed, 0 failed` |
| Python 3.7 语法 | PASS | 商业 API 与无代码配置模块通过 `py_compile` |
| Git 空白检查 | PASS | `git diff --check` 无错误 |
| 已跟踪文件密钥模式扫描 | PASS | 未发现常见 OpenAI、GitHub 或 Sites Token 模式 |
| 运行时私密文件忽略 | PASS | `.env` 与 `config/commercial.yaml` 均被 Git 忽略 |
| Docker 镜像构建 | NOT RUN | Docker Desktop Linux daemon 未启动 |

## 覆盖的关键路径

### Agent 运行时

- Domain、Agent、Skill、Capability、Policy、Binding 和 Workflow 契约加载；
- 成功查询、证据不足、工具失败、对抗输入和策略边界；
- 写操作审批门、Trace 和结果验证；
- 30 个 Golden Cases 的终态一致性。

### 商业 API

- 客户 Bearer API Key 认证；
- Domain、Task、Provider 和 Model 白名单；
- 每分钟限流、月额度、用量计量与幂等重放；
- 请求体大小限制、未知字段拒绝和标准化错误；
- 中国模型厂商与国际厂商 Provider 请求/响应契约；
- Base URL 官方域名白名单和不安全 URL 拒绝。

### 无代码配置中心

- 厂商目录、模型档位和表单到 YAML 的自动转换；
- YAML 与真实密钥分离；
- 占位模型、重复模型、未知厂商、短密钥和非法 Base URL 拒绝；
- 一次性管理员密钥、仅本机访问和 CORS 来源白名单；
- 配置预览不回显真实密钥；
- `commercial.yaml` 与 `.env` 安全写入；
- 配置完成后加载 `.env` 并重启为正常商业 API。

### Web UI

- 系统地图首页正常服务端渲染；
- `/setup` 五步无代码配置向导正常服务端渲染；
- 核心可访问性标签和交互控件存在；
- 生产构建未包含脚手架占位内容或硬编码真实密钥。

## 复现命令

```powershell
python -m pytest -q
python -m vertical_agent_factory.cli --root . validate --domain research
python -m vertical_agent_factory.cli --root . eval --domain research

cd web
pnpm run lint
pnpm test
```

Docker Desktop 启动后补验：

```powershell
docker build --pull=false -t vertical-agent-factory:self-test .
```

## 发布建议

当前提交可进入代码评审。正式商业环境仍应在 CI 或有 Docker daemon 的构建机上补跑镜像构建，并使用外部 Secret Manager、共享限流/计量存储和生产反向代理完成部署验收。
