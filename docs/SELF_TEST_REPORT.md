# 全面自测试报告

测试日期：2026-08-15

测试分支：`bussiness_type`

测试基线：金融 Agent 与微信公众号发布候选版本（提交后对应本分支最新提交）

## 发布结论

**PASS（所有当前环境可执行的发布门均通过）**。

Python、商业 API、无代码配置后台、研究与金融 Domain Pack、微信公众号通道、Golden Evals、Web UI、生产构建、服务端渲染、Python 3.7 语法、Git 空白、密钥模式和忽略规则全部通过。

Docker 镜像构建未执行：本机已安装 Docker CLI 29.1.3，但 Docker Desktop Linux daemon 未启动。该项记录为环境不可用，不属于代码测试失败；启用 Docker Desktop 后可执行 `docker build -t vertical-agent-factory:self-test .` 补验。

## 测试结果

| 测试门 | 结果 | 证据 |
|---|---:|---|
| Git 远端基线同步 | PASS | 提交前 `origin/bussiness_type...HEAD` 为 `0/0` |
| Python 全量测试 | PASS | `76 passed` |
| Domain Pack 校验 | PASS | `research`、`finance` 均返回 `PASS` |
| Golden Evals | PASS | 两个领域合计 `60 passed, 0 failed` |
| Web ESLint | PASS | 无错误、无警告 |
| Web 生产构建 | PASS | `/`、`/finance` 与 `/setup` 路由构建成功 |
| Web SSR HTML | PASS | `4 passed, 0 failed` |
| Python 3.7 语法 | PASS | 金融、微信、商业 API 与配置模块通过 `py_compile` |
| Git 空白检查 | PASS | `git diff --check` 无错误 |
| 已跟踪文件密钥模式扫描 | PASS | 排除公开 Sites 项目标识后，未发现常见 OpenAI、GitHub 或私钥模式 |
| 运行时私密文件忽略 | PASS | `.env` 与 `config/commercial.yaml` 均被 Git 忽略 |
| Docker 镜像构建 | NOT RUN | Docker Desktop Linux daemon 未启动 |

## 覆盖的关键路径

### Agent 运行时

- Domain、Agent、Skill、Capability、Policy、Binding 和 Workflow 契约加载；
- 成功查询、证据不足、工具失败、对抗输入和策略边界；
- 写操作审批门、Trace 和结果验证；
- 两个领域共 60 个 Golden Cases 的终态一致性。

### 金融 Agent 与数据层

- 中国/美国/全球宏观、A 股和美股样例数据分析；
- Tushare、FRED、Alpha Vantage 官方 API 请求契约与失败处理；
- 证券代码规范化、区间收益、历史波动率、最大回撤；
- 事实、推断、证据日期、警告和免责声明分离；
- 无效代码、数据不足、工具故障、提示词注入和投资建议边界；
- 金融简报发布的高风险审批门。

### 微信公众号通道

- GET 服务器签名校验与 `echostr`；
- 明文 XML 文本消息、金融命令路由和被动回复；
- `MsgId` 幂等、错误降级和统一免责声明；
- 错误签名、DTD/Entity 和加密模式拒绝；
- 服务端租户选择，不向微信端暴露客户密钥。

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
- `/finance` 金融研究工作台、风险指标和公众号命令模拟正常渲染；
- 核心可访问性标签和交互控件存在；
- 生产构建未包含脚手架占位内容或硬编码真实密钥。

## 复现命令

```powershell
python -m pytest -q
python -m vertical_agent_factory.cli --root . validate --domain research
python -m vertical_agent_factory.cli --root . eval --domain research
python -m vertical_agent_factory.cli --root . validate --domain finance
python -m vertical_agent_factory.cli --root . eval --domain finance

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
