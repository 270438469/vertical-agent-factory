# 商业 API 逐步配置手册

本文从一台新机器开始，逐步完成 Vertical Agent Factory 商业 API 的本地配置、模型厂商接入、租户鉴权、启动验证、Docker 部署和上线检查。示例以 Windows PowerShell 为主，同时给出 Linux/macOS 对应命令。

完成后，外部客户只调用统一的 `/v1/agent/runs`，模型厂商密钥只保存在服务端：

```text
客户系统
  └─ Bearer VAF 客户密钥
      └─ Vertical Agent Factory Commercial API
          ├─ 租户、Domain、Task、Provider、Model allowlist
          ├─ 限流、月配额、幂等、用量记录
          └─ 厂商 API Key → OpenAI / Anthropic / Gemini / 中国模型平台
```

## 0. 先理解四类配置

| 配置 | 保存位置 | 谁使用 | 是否可以发给客户 |
| --- | --- | --- | --- |
| 客户 API Key | 环境变量，例如 `VAF_API_KEY_CUSTOMER_A` | 客户调用本系统 | 只发给对应客户 |
| 厂商 API Key | 环境变量，例如 `OPENAI_API_KEY` | 服务端调用模型厂商 | 不可以 |
| Provider 与模型 allowlist | `config/commercial.yaml` | 服务端授权和路由 | 可以公开模型名，不能写密钥 |
| 用量与幂等数据 | 默认 `.commercial/usage.sqlite3` | 商业 API | 不可以直接公开数据库 |

必须保持以下关系：

1. `providers` 声明服务端支持哪些厂商，以及从哪个环境变量读取密钥。
2. `allowed_providers` 决定某个租户可以选择哪些厂商。
3. 每个外部 Provider 必须在 `allowed_models` 中配置 1–3 个模型。
4. `default_models.<provider>` 必须严格等于 `allowed_models.<provider>` 的第一项。
5. 租户 `default_provider` 必须出现在自己的 `allowed_providers` 中。
6. `approved_capabilities` 默认保持空列表，避免客户绕过写操作审批。

配置加载器会在启动时拒绝错误的模型数量、重复模型和默认档位错位。

## 1. 准备运行环境

生产环境推荐 Python 3.12。项目核心兼容 Python 3.7+，但商业 API 依赖应优先使用当前受支持的 Python 版本。

检查版本：

```powershell
git --version
python --version
node --version
pnpm --version
```

Web UI 自测需要 Node.js 22.13+ 和 pnpm 11.16.0。若只运行商业 API，Node.js 不是必需项。安装 Node.js 后可用 Corepack 准备仓库指定的 pnpm：

```powershell
corepack enable
corepack prepare pnpm@11.16.0 --activate
```

如果 `gh` 刚通过 `winget` 安装但当前窗口找不到，请关闭并重新打开终端，或者直接运行：

```powershell
& "C:\Program Files\GitHub CLI\gh.exe" --version
```

进入项目并同步分支：

```powershell
Set-Location H:\codex\vertical-agent-factory
git switch bussiness_type
git pull --rebase origin bussiness_type
```

创建独立虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[api,api-test]"
```

Linux/macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[api,api-test]'
```

## 2. 创建正式配置文件

不要直接修改示例文件。复制一份未提交到 Git 的运行配置：

```powershell
Copy-Item config/commercial.example.yaml config/commercial.yaml
```

检查 `.gitignore` 已忽略正式配置和运行数据；提交前仍应执行：

```powershell
git status --short
```

确保 `config/commercial.yaml`、`.env`、`.commercial/` 和 `.runs/` 没有被暂存。

配置开头：

```yaml
project_root: ..
database_path: .commercial/usage.sqlite3
```

- `project_root` 相对于配置文件目录。示例配置位于 `config/`，因此 `..` 指向仓库根目录。
- `database_path` 相对于 `project_root`，用于保存请求计量和幂等响应。
- 数据库目录必须可写。Docker 镜像已为 `/app/.commercial` 配置非 root 用户权限。

## 3. 生成客户 API Key

每个租户使用不同的高熵密钥，最少 32 个字符。不要把模型厂商 Key 直接交给客户。

PowerShell 生成 48 字节随机密钥：

```powershell
$randomBytes = New-Object byte[] 48
$randomGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
$randomGenerator.GetBytes($randomBytes)
$customerApiKey = [Convert]::ToBase64String($randomBytes)
$randomGenerator.Dispose()
$customerApiKey
```

只在当前 PowerShell 会话中设置：

```powershell
$env:VAF_API_KEY_DEMO = $customerApiKey
```

Linux/macOS：

```bash
export VAF_API_KEY_DEMO="$(openssl rand -base64 48)"
```

生产环境应把密钥放入云 Secret Manager、Kubernetes Secret、Docker Secret 或 Vault。不要把真实值写进 YAML、README、Trace 或 Git。

## 4. 配置第一个租户

建议先只启用 `local`，确认系统本身可以运行，再逐个添加外部厂商。

最小租户配置：

```yaml
tenants:
  - id: demo-customer
    api_key_env: VAF_API_KEY_DEMO
    allowed_domains:
      - research
    allowed_tasks:
      - research.answer.query
      - research.report.publish
    allowed_providers:
      - local
    default_provider: local
    allowed_models: {}
    default_models: {}
    approved_capabilities: []
    rate_limit_per_minute: 60
    monthly_request_quota: 10000
```

字段说明：

| 字段 | 作用 | 建议 |
| --- | --- | --- |
| `id` | 租户唯一标识，也会进入用量数据库 | 使用稳定、不可复用的业务 ID |
| `api_key_env` | 客户密钥所在环境变量 | 每个租户单独变量 |
| `allowed_domains` | 可访问的 Domain Pack | 从最小集合开始 |
| `allowed_tasks` | 可执行任务 | 不要仅授权 Domain 而放开所有 Task |
| `allowed_providers` | 可选模型平台 | 未购买或未验证的平台不要加入 |
| `default_provider` | 请求未传 `provider` 时使用 | 首次部署使用 `local` |
| `allowed_models` | 各厂商模型白名单 | 每家最多三项 |
| `default_models` | 各厂商默认模型 | 必须等于对应列表第一项 |
| `approved_capabilities` | 服务端预批准能力 | 真实写操作场景保持 `[]` |
| `rate_limit_per_minute` | 当前实例内的分钟请求限制 | 根据租户套餐设置 |
| `monthly_request_quota` | 每月请求次数上限 | 结合计费套餐设置 |

注意：当前分钟限流器保存在进程内存中，SQLite 用量库也面向单实例。部署多个 API 副本前，需要把限流迁移到 Redis、把用量与幂等存储迁移到事务型共享数据库。

## 5. 先启动 Local Provider

设置运行变量：

```powershell
$env:VAF_COMMERCIAL_CONFIG = "config/commercial.yaml"
$env:VAF_API_HOST = "127.0.0.1"
$env:VAF_API_PORT = "8000"
$env:VAF_MAX_REQUEST_BYTES = "262144"
```

重要：项目不会自动读取 `.env`。`.env.example` 只是变量清单。必须像上面一样设置当前进程环境变量，或由进程管理器、容器平台注入。

启动：

```powershell
vertical-agent-api
```

另开一个 PowerShell 窗口验证 Health：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/health
```

预期：

```json
{"status":"ok","service":"vertical-agent-factory"}
```

新终端不会自动继承另一个已打开终端后来设置的环境变量。把第 3 步生成的同一个客户 Key 安全地注入测试终端，然后设置调用头：

```powershell
$env:VAF_API_KEY_DEMO = "粘贴第3步生成的同一个客户Key"
$headers = @{
  Authorization = "Bearer $env:VAF_API_KEY_DEMO"
  "Content-Type" = "application/json"
}
```

查看租户模型：

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/v1/models `
  -Headers $headers
```

调用本地 Agent：

```powershell
$body = @{
  domain = "research"
  task = "research.answer.query"
  input = @{ query = "shared Harness 是什么？" }
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/agent/runs `
  -Headers $headers `
  -Body $body
```

Local Provider 不接受 `model` 字段；传入模型会返回 `400 invalid_model`。

## 6. 添加一个外部 Provider

以下以 DeepSeek 为例。其他厂商遵循同一流程。

### 6.1 获取并注入厂商密钥

在厂商官方控制台开通 API、完成需要的实名或计费配置、创建服务端 Key，然后设置：

```powershell
$env:DEEPSEEK_API_KEY = "替换为真实服务端密钥"
```

### 6.2 在 `providers` 中声明密钥变量

```yaml
providers:
  deepseek:
    api_key_env: DEEPSEEK_API_KEY
```

YAML 中只写环境变量名称，不写真实密钥。

### 6.3 给租户增加 Provider

```yaml
allowed_providers:
  - local
  - deepseek
```

### 6.4 配置最多三个模型档位

```yaml
allowed_models:
  deepseek:
    - deepseek-v4-pro
    - deepseek-v4-flash
default_models:
  deepseek: deepseek-v4-pro
```

DeepSeek 当前官方只公开两个适用的生产 Chat 模型，因此不需要凑满三个。完整的厂商档位及锁定日期见[模型前三档配置](MODEL_TIERS.md)。

### 6.5 重启并验证

修改 YAML 或环境变量后需要重启 API 进程。外部模型测试请求：

```powershell
$body = @{
  domain = "research"
  task = "research.answer.query"
  input = @{ query = "解释 capability-first agent architecture" }
  provider = "deepseek"
  model = "deepseek-v4-pro"
} | ConvertTo-Json -Depth 8

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/v1/agent/runs `
  -Headers $headers `
  -Body $body
```

若省略 `model`，系统使用 `default_models.deepseek`。若指定不在 allowlist 中的模型，会返回 `403 model_forbidden`。

## 7. 各厂商逐项配置

每次只增加一个厂商，并在增加后执行最小真实请求。官方目录会变化，模型名以[模型前三档配置](MODEL_TIERS.md)和厂商控制台实际权限为准。

| Provider | 环境变量 | 官方入口 | 需要完成的厂商侧操作 | 本系统额外配置 |
| --- | --- | --- | --- | --- |
| `openai` | `OPENAI_API_KEY` | [API Key](https://platform.openai.com/api-keys) | 创建 API Project/Key，确认模型和计费权限 | 无 Base URL 配置 |
| `anthropic` | `ANTHROPIC_API_KEY` | [Claude Console](https://console.anthropic.com/settings/keys) | 创建 Claude API Key，确认模型权限 | 无 Base URL 配置 |
| `gemini` | `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | 创建 Gemini API Key，确认项目配额 | 无 Base URL 配置 |
| `qwen` | `DASHSCOPE_API_KEY` | [百炼 Key 配置](https://help.aliyun.com/zh/model-studio/get-api-key) | 开通模型服务并创建 Key | 新工作空间通常还要设置 `DASHSCOPE_BASE_URL` |
| `deepseek` | `DEEPSEEK_API_KEY` | [DeepSeek 平台](https://platform.deepseek.com/api_keys) | 创建 API Key 并充值/授权 | 无 |
| `zhipu` | `ZHIPU_API_KEY` | [BigModel Key](https://open.bigmodel.cn/usercenter/apikeys) | 创建 API Key | 无 |
| `moonshot` | `MOONSHOT_API_KEY` | [Kimi API 文档](https://platform.kimi.com/docs/api/overview) | 在开放平台创建 API Key | 国际账号可设置 `MOONSHOT_BASE_URL=https://api.moonshot.ai/v1` |
| `minimax` | `MINIMAX_API_KEY` | [MiniMax API 文档](https://platform.minimaxi.com/docs/api-reference/api-overview) | 创建 API Key | 国际账号可设置 `MINIMAX_BASE_URL=https://api.minimax.io/v1` |
| `doubao` | `ARK_API_KEY` | [方舟兼容接口](https://www.volcengine.com/docs/82379/1330626) | 创建 API Key；必要时为三档模型创建 Endpoint | 必要时设置 `ARK_BASE_URL`，并把模型别名换为 Endpoint ID |
| `hunyuan` | `HUNYUAN_API_KEY` | [混元兼容接口](https://cloud.tencent.com/document/product/1729/111007) | 获取腾讯混元兼容 API 凭证 | 旧平台迁移前确认账号仍有权限，并规划 TokenHub 迁移 |
| `qianfan` | `QIANFAN_API_KEY` | [千帆文档](https://cloud.baidu.com/doc/Qianfan/index.html) | 创建兼容 API 专用 Key | 不要误用需要 AK/SK 签名的旧接口凭证 |
| `stepfun` | `STEPFUN_API_KEY` | [StepFun 文档](https://platform.stepfun.ai/docs) | 在开放平台创建 Key | 无 |
| `yi` | `YI_API_KEY` | [零一万物文档](https://platform.lingyiwanwu.com/docs) | 在开放平台创建 Key | 当前通用文本目录不足三档 |
| `baichuan` | `BAICHUAN_API_KEY` | [百川文档](https://platform.baichuan-ai.com/docs) | 在开放平台创建 Key | 无 |
| `spark` | `SPARK_API_KEY` | [星辰 Token Plan](https://www.xfyun.cn/doc/spark/TokenPlan.html) | 购买/开通套餐，复制套餐专属 API Key | 使用 Token Plan `/v2` 入口，不是旧版 Spark API Password 入口 |
| `siliconflow` | `SILICONFLOW_API_KEY` | [SiliconFlow 快速开始](https://docs.siliconflow.cn/cn/userguide/quickstart) | 创建 Key，并在模型广场确认实际可用模型 | 必须替换三个 `replace-with-siliconflow-*` 槽位 |
| `sensenova` | `SENSENOVA_API_KEY` | [SenseNova 文档](https://platform.sensenova.cn/product/APIService/document) | 创建凭证并查询当前账号模型列表 | 必须用账号返回的真实模型 ID 替换三个槽位 |
| `mimo` | `MIMO_API_KEY` | [MiMo 文档](https://mimo.mi.com/docs/zh-CN/quick-start/summary/first-api-call) | 在小米 MiMo 平台创建 Key | 当前只有两个通用文本模型 |
| `longcat` | `LONGCAT_API_KEY` | [LongCat 文档](https://longcat.chat/platform/docs/) | 创建 Key 并确认额度 | 当前只有 `LongCat-2.0` 一个生产文本模型 |

### 7.1 Base URL 覆盖

只有示例配置中声明了 `base_url_env` 的 Provider 才会读取覆盖值：

```yaml
providers:
  qwen:
    api_key_env: DASHSCOPE_API_KEY
    base_url_env: DASHSCOPE_BASE_URL
```

PowerShell 示例：

```powershell
$env:DASHSCOPE_BASE_URL = "https://WORKSPACE_ID.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
```

代码只接受 HTTPS、官方允许的主机和标准 443 端口；用户名、密码、查询串、片段以及任意第三方代理地址都会被拒绝。不要通过修改 allowlist 把客户提供的 URL 直接放行。

### 7.2 SiliconFlow 三个槽位

登录模型广场，复制账号实际可见的完整模型 ID（通常带组织前缀），按能力从高到低填写：

```yaml
allowed_models:
  siliconflow:
    - vendor/top-capability-model
    - vendor/balanced-model
    - vendor/fast-model
default_models:
  siliconflow: vendor/top-capability-model
```

只保留已经开通且通过真实请求验证的模型。

### 7.3 SenseNova 账号模型 ID

先按官方文档获取访问令牌并调用模型列表接口，再把返回的真实 ID 填入：

```yaml
allowed_models:
  sensenova:
    - ACCOUNT_MODEL_ID_FOR_V6_5_PRO
    - ACCOUNT_MODEL_ID_FOR_V6_5_TURBO
    - ACCOUNT_MODEL_ID_FOR_V6_REASONER
default_models:
  sensenova: ACCOUNT_MODEL_ID_FOR_V6_5_PRO
```

不要直接把展示名称当作模型 ID。

### 7.4 豆包 Ark Endpoint ID

若公共别名不可调用，在方舟控制台分别创建 Evolving、2.1 Pro、2.1 Turbo 的推理接入点：

```yaml
allowed_models:
  doubao:
    - ep-top-capability
    - ep-balanced
    - ep-fast
default_models:
  doubao: ep-top-capability
```

三个 Endpoint 必须属于当前账号和当前 `ARK_BASE_URL` 地域。

## 8. 删除未启用厂商

生产配置不建议保留所有示例 Provider。禁用某厂商时，从以下三处同时删除：

1. 顶层 `providers.<provider>`。
2. 每个租户的 `allowed_providers`。
3. 每个租户的 `allowed_models.<provider>` 与 `default_models.<provider>`。

例如只启用 Local、OpenAI、DeepSeek：

```yaml
providers:
  openai:
    api_key_env: OPENAI_API_KEY
  deepseek:
    api_key_env: DEEPSEEK_API_KEY

tenants:
  - id: customer-a
    api_key_env: VAF_API_KEY_CUSTOMER_A
    allowed_domains: [research]
    allowed_tasks: [research.answer.query]
    allowed_providers: [local, openai, deepseek]
    default_provider: local
    allowed_models:
      openai: [gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna]
      deepseek: [deepseek-v4-pro, deepseek-v4-flash]
    default_models:
      openai: gpt-5.6-sol
      deepseek: deepseek-v4-pro
    approved_capabilities: []
    rate_limit_per_minute: 60
    monthly_request_quota: 10000
```

## 9. 添加更多租户

每个租户单独创建 API Key、权限和额度：

```yaml
tenants:
  - id: customer-a
    api_key_env: VAF_API_KEY_CUSTOMER_A
    allowed_domains: [research]
    allowed_tasks: [research.answer.query]
    allowed_providers: [local, openai]
    default_provider: openai
    allowed_models:
      openai: [gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna]
    default_models:
      openai: gpt-5.6-sol
    approved_capabilities: []
    rate_limit_per_minute: 120
    monthly_request_quota: 50000

  - id: customer-b
    api_key_env: VAF_API_KEY_CUSTOMER_B
    allowed_domains: [research]
    allowed_tasks: [research.answer.query]
    allowed_providers: [local, deepseek]
    default_provider: local
    allowed_models:
      deepseek: [deepseek-v4-pro, deepseek-v4-flash]
    default_models:
      deepseek: deepseek-v4-pro
    approved_capabilities: []
    rate_limit_per_minute: 30
    monthly_request_quota: 5000
```

对应环境变量：

```powershell
$env:VAF_API_KEY_CUSTOMER_A = "customer-a-random-key-at-least-32-characters"
$env:VAF_API_KEY_CUSTOMER_B = "customer-b-different-random-key-at-least-32"
```

禁止不同租户复用同一客户 Key。

## 10. 配置幂等调用

可能被客户重试的请求应带 `Idempotency-Key`：

```powershell
$idempotentHeaders = @{
  Authorization = "Bearer $env:VAF_API_KEY_DEMO"
  "Content-Type" = "application/json"
  "Idempotency-Key" = "customer-order-20260809-0001"
}
```

同一租户、同一 Idempotency Key、相同请求体会返回第一次结果；同一个 Key 配不同请求体会返回 `409 idempotency_conflict`。Key 最长 128 个字符。

## 11. 查看模型与用量

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/v1/models `
  -Headers $headers

Invoke-RestMethod `
  -Uri http://127.0.0.1:8000/v1/usage `
  -Headers $headers
```

`/v1/models` 只返回当前租户的 Provider 和模型 allowlist，不返回任何厂商密钥。`/v1/usage` 返回请求次数、剩余额度和模型厂商报告的 Token 用量，但不计算货币价格；商业计费系统需要结合版本化价格表另行结算。

## 12. 运行完整自测试

```powershell
python -m pytest -q
python -m vertical_agent_factory.cli --root . validate --domain research
python -m vertical_agent_factory.cli --root . eval --domain research

Set-Location web
pnpm install --frozen-lockfile
pnpm run lint
pnpm test
pnpm run build
Set-Location ..
```

当前仓库基线：

- 60/60 Python 测试。
- 两个领域合计 60/60 Golden Evals。
- 2/2 Web 渲染测试。
- Web lint 和生产构建通过。

这些测试使用模拟传输验证协议和响应解析，不会消耗真实厂商额度。每个启用的厂商仍需用测试账号执行一次最小真实请求，才能确认 Key、模型权限、地域、余额和 Endpoint ID 都正确。

## 13. Docker 部署

先准备：

- `config/commercial.yaml`。
- 不提交到 Git 的 `.env`，包含客户 Key、启用厂商 Key 和运行变量。
- 可持久化的 `.commercial` 数据卷。

`.env` 示例：

```dotenv
VAF_API_KEY_DEMO=替换为至少32字符的随机客户密钥
OPENAI_API_KEY=替换为真实厂商密钥
DEEPSEEK_API_KEY=替换为真实厂商密钥
VAF_MAX_REQUEST_BYTES=262144
```

构建镜像：

```powershell
docker build -f Dockerfile.api -t vertical-agent-api:0.2.0 .
```

运行：

```powershell
$commercialConfig = (Resolve-Path config/commercial.yaml).Path

docker run --rm `
  --name vertical-agent-api `
  -p 127.0.0.1:8000:8000 `
  --env-file .env `
  -v "${commercialConfig}:/app/config/commercial.yaml:ro" `
  -v vaf-commercial-data:/app/.commercial `
  vertical-agent-api:0.2.0
```

说明：

- 只映射到 `127.0.0.1`，由同机反向代理对外提供 HTTPS。
- 配置文件以只读方式挂载。
- `.dockerignore` 会排除本机 `config/commercial.yaml`，正式配置只在运行时挂载，不会烘焙进镜像。
- `.commercial` 使用命名卷，容器重建后用量与幂等数据不会丢失。
- 不要把 `.env` COPY 到镜像。
- 修改配置或环境变量后重建/重启容器。

## 14. 对外上线

应用默认本地监听 `127.0.0.1:8000`。直接暴露到公网前至少完成：

1. 在 Caddy、Nginx、云 API Gateway 或负载均衡器终止 TLS。
2. 只允许反向代理访问后端端口。
3. 配置请求体上限、连接超时、上游超时和日志脱敏。
4. 为客户 API Key 配置安全分发、轮换、吊销和审计流程。
5. 厂商密钥使用 Secret Manager 注入，不放入镜像层或 GitHub Actions 日志。
6. 定期备份 `.commercial/usage.sqlite3`，并验证恢复流程。
7. 接入指标与告警：HTTP 状态、429、502、延迟、厂商错误率、余额和月配额。
8. 多副本部署前替换内存限流和 SQLite 存储。
9. 真实写操作连接独立审批服务；不要长期在 `approved_capabilities` 中预批准。
10. 定期检查厂商模型下线公告，并按[模型前三档配置](MODEL_TIERS.md)更新目录。

## 15. 常见错误与处理

| 状态/错误 | 原因 | 处理 |
| --- | --- | --- |
| 启动时报客户 Key 未设置 | `api_key_env` 对应环境变量为空 | 在启动 API 的同一进程/容器注入变量 |
| 启动时报 Key 少于 32 字符 | 客户 Key 太短 | 重新生成高熵 Key；厂商 Key 不受这个长度检查 |
| `default_provider is not allowed` | 默认 Provider 不在租户列表 | 加入 `allowed_providers` 或修改默认值 |
| `requires allowed_models` | 外部 Provider 没有模型列表 | 配置 1–3 个真实模型 |
| `allows at most three model tiers` | 某厂商超过三项 | 只保留能力、均衡、快速/低成本档 |
| `default_model must be the first tier` | 默认模型不是列表第一项 | 修改 `default_models` 与第一项一致 |
| `401 unauthorized` | 客户 Bearer Key 缺失或错误 | 检查 `Authorization: Bearer ...`，不要填厂商 Key |
| `403 provider_forbidden` | 租户未授权 Provider | 检查 `allowed_providers` |
| `403 model_forbidden` | 模型未在租户 allowlist | 检查完整模型 ID、大小写和组织前缀 |
| `400 model_required` | 外部 Provider 没有请求模型也没有默认模型 | 补全 `default_models` |
| `400 provider_not_supported_for_task` | 外部模型用于当前未适配的 Task | 当前外部模型处理器只接入 `research.answer.query` |
| `409 approval_required` | 写操作未获服务端批准 | 走可信审批流程；不要让客户在请求中自带批准 |
| `409 idempotency_conflict` | 同一幂等 Key 对应不同请求体 | 为新业务操作生成新 Key |
| `413 request_too_large` | 请求体超过 `VAF_MAX_REQUEST_BYTES` | 缩小输入或审慎调整服务端上限 |
| `429 rate_limit_exceeded` | 当前实例分钟限流 | 等待 `Retry-After`，或调整租户套餐 |
| `429 quota_exceeded` | 本月请求次数用尽 | 调整套餐或等待新月份 |
| `502 agent_execution_failed` | Agent 或厂商调用失败 | 用 `X-Request-ID` 查服务端日志和 Trace；不要向客户返回厂商原始密钥信息 |
| 厂商返回 model not found | 模型未开通、已下线或 ID/地域错误 | 查厂商模型列表，更新 allowlist 并重启 |
| Base URL 被拒绝 | 主机不在官方 allowlist 或 URL 包含不安全组件 | 使用文档中的官方 HTTPS 地址 |

## 16. 密钥轮换

客户 Key 轮换建议：

1. 创建新的租户 Key 环境变量，例如 `VAF_API_KEY_CUSTOMER_A_V2`。
2. 在维护窗口修改租户 `api_key_env`。
3. 重启服务并用新 Key 验证 `/v1/models`。
4. 安全通知客户切换。
5. 确认旧 Key 不再调用后，从 Secret Manager 删除旧值。

当前一个租户配置只接受一个客户 Key。若需要无中断双 Key 轮换，应先扩展配置和鉴权层，使其支持主 Key 与过渡 Key，而不是在多个租户中复用同一 `tenant_id`。

厂商 Key 轮换：在厂商控制台创建新 Key → 更新 Secret → 重启服务 → 最小真实请求验证 → 删除旧 Key。

## 17. 上线验收清单

- [ ] `config/commercial.yaml` 未被 Git 跟踪。
- [ ] 每个租户使用不同且至少 32 字符的随机客户 Key。
- [ ] 厂商 Key 仅通过服务端 Secret 注入。
- [ ] 未启用 Provider 已从配置三处删除。
- [ ] 每个启用厂商只有 1–3 个真实可用模型。
- [ ] 每个 `default_models` 等于对应列表第一项。
- [ ] SiliconFlow、SenseNova、豆包账号专属槽位已替换。
- [ ] `approved_capabilities` 默认为空。
- [ ] 76/76 Python 测试、60/60 Golden Evals、Web 测试和构建通过。
- [ ] 每个启用厂商完成最小真实 API 请求。
- [ ] `/v1/models` 只展示当前租户权限。
- [ ] `/v1/usage` 能记录请求和 Token。
- [ ] TLS、日志脱敏、备份、告警和密钥轮换已配置。
- [ ] 多副本前已替换内存限流和 SQLite。

相关资料：

- [商业 API 接入与部署](COMMERCIAL_API.md)
- [模型前三档配置](MODEL_TIERS.md)
- [系统架构](ARCHITECTURE.md)
- [详细使用手册](USAGE.md)
