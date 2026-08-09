# 无代码 Agent 配置中心使用手册

本文面向不编写代码的运营、交付和项目管理员。配置中心会把页面中填写的业务选择自动转换为 `commercial.yaml`，把真实密钥单独写入 `.env`，并在写入前由本地后台再次校验。

在线入口：<https://vertical-agent-factory-lab.xuchong1999.chatgpt.site/setup>

## 配置前需要准备什么

请先确认电脑上已有项目目录和 Python 3.7 或更高版本。然后准备：

1. 一个客户或项目标识，例如 `acme-research`；
2. 要开放的 Agent 任务；
3. 如果要调用大模型，准备相应厂商账号、API Key 和已开通模型；
4. 豆包、SiliconFlow、SenseNova 等账号相关平台，还要准备控制台中的真实 Endpoint ID 或模型 ID；
5. 期望的每分钟调用上限和每月请求额度。

厂商密钥和客户调用密钥是两类不同凭据：厂商密钥由服务器调用模型时使用；客户调用密钥由你的外部客户访问统一 Agent API 时使用。不要把两者混用。

## 第 1 步：填写业务用途

打开配置中心后，在“业务用途”中填写客户/项目标识。该标识用于租户隔离，只能包含字母、数字、短横线和下划线。

随后选择 Agent 可以执行的任务：

- “查询并生成答案”对应 `research.answer.query`，是只读任务；
- “发布研究报告”对应 `research.report.publish`，是写操作，默认必须经过审批。

当前仓库已经安装 `research` Domain Pack。UI 配置的是该领域中现有 Agent 的租户、模型和调用策略；如果需要法务、客服或其他领域，应先安装对应 Domain Pack。

## 第 2 步：选择模型厂商

不选择任何厂商时，系统使用本地确定性流程，不会产生模型 API 费用。需要大模型生成答案时，选择已经开户的厂商。

每张厂商卡片都列出需要准备的内容，并提供官方申请入口。可同时选择多家厂商；调用方只能在这里生成的白名单范围内选择 Provider 和 Model。

选择原则：

- 先接入一家已经完成实名、计费和配额设置的厂商；
- 试运行通过后再增加备用厂商；
- 不要因为页面列出某厂商就认为账号自动拥有相应模型权限，最终权限以厂商控制台为准。

## 第 3 步：填写密钥和模型

对每个已选厂商，完成以下字段：

1. 把厂商控制台生成的 API Key 粘贴到密码框；
2. 只有页面显示 Base URL 字段时才填写；不确定时留空，系统使用官方默认地址；
3. 检查一到三档模型，第一项是默认高能力档；
4. 出现 `replace-with-...` 时，必须替换为当前账号中的真实模型 ID；
5. 豆包账号如果要求 Endpoint ID，应把预填模型别名替换为同地域的 Endpoint ID。

配置中心不会把密码框内容保存到浏览器存储。刷新或关闭页面会清空密钥。后台还会拒绝非官方 HTTPS Base URL、未知厂商、重复模型、空模型和超过三档的模型列表。

## 第 4 步：设置权限与额度

页面会自动生成一个不少于 32 字符的客户 API Key。可以点击“重新生成”，也可以粘贴由企业密钥管理系统生成的随机值。

然后填写：

- 每分钟最多请求数：保护服务和预算免受突发流量影响；
- 每月最多请求数：达到后统一 API 自动拒绝新请求；
- 默认生成方式：调用方未指定 Provider 时使用本地流程或某家已选厂商。

高风险写能力不会在配置 UI 中预批准。生成的 `approved_capabilities` 固定为空，外部请求也不能自行携带审批结果。

## 第 5 步：检查并应用

页面会展示客户、任务、厂商和默认方式摘要，并生成高级 YAML 预览。预览不包含任何真实密钥。

### 推荐方式：一键应用到本机

1. 保持配置页面打开；
2. 在项目根目录打开 PowerShell；
3. 点击“复制本地配置服务启动命令”；
4. 把命令粘贴到 PowerShell 并按 Enter；
5. 等待终端显示 API 已启动；
6. 回到页面点击“后台检查”；
7. 检查通过后点击“应用到本机”；
8. 看到成功路径后，在 PowerShell 按 `Ctrl+C` 停止服务；
9. 再运行 `python -m vertical_agent_factory.commercial.app`。

复制命令会完成 API 依赖安装，设置一次性管理员密钥，允许当前配置页面访问 `127.0.0.1`，并启动本地配置服务。管理员密钥只存在于当前 PowerShell 进程中，重启后配置接口默认关闭。

应用成功后，后台固定写入：

- `config/commercial.yaml`：租户、任务、Provider、模型、额度；不含真实密钥；
- `.env`：客户密钥、厂商密钥和必要的 Base URL；该文件已被 Git 忽略。

服务启动入口会读取 `.env` 中尚未由系统环境设置的变量；生产环境已有环境变量时，进程变量优先，不会被 `.env` 覆盖。

### 备用方式：下载配置包

如果浏览器策略、企业代理或防火墙阻止在线页面访问本机，可以点击：

- “下载 YAML”，保存为 `config/commercial.yaml`；
- “下载私密 .env”，保存到项目根目录的 `.env`。

`.env` 包含真实凭据，不要提交 Git、发送到聊天群或工单。下载文件后重新启动 API 服务即可加载。

## 后台自动转换接口

配置中心调用以下本地接口：

| 接口 | 作用 | 是否需要一次性管理员密钥 |
|---|---|---:|
| `GET /v1/setup/catalog` | 返回厂商、模型档位和准备说明 | 否 |
| `GET /v1/setup/status` | 检查配置服务状态和目标路径 | 是 |
| `POST /v1/setup/preview` | 校验表单并返回无密钥 YAML | 是 |
| `POST /v1/setup/apply` | 原子写入 YAML 和 `.env` | 是 |

安全默认值：

- 未设置 `VAF_SETUP_ADMIN_KEY` 时，管理接口返回 404；
- 管理密钥必须不少于 32 字符；
- 默认只接受来自本机回环地址的请求；
- 跨域来源必须明确列入 `VAF_SETUP_ALLOWED_ORIGINS`；
- 响应只返回密钥是否已配置，不回显密钥值；
- 配置采用临时文件加原子替换，避免写入一半留下损坏文件。

## 常见问题

### 页面提示“无法连接”

确认 PowerShell 中的服务仍在运行，页面地址与命令中的 `VAF_SETUP_ALLOWED_ORIGINS` 完全一致，并检查本地地址仍是 `http://127.0.0.1:8000`。

### 后台返回 401

页面中的“一次性管理员密钥”必须与启动命令中的 `VAF_SETUP_ADMIN_KEY` 相同。最简单的处理方式是重新点击复制命令，停止旧服务后重新粘贴启动。

### 后台返回模型占位符错误

SiliconFlow 和 SenseNova 的公共示例不能假定每个账号都启用相同模型。登录厂商控制台，把 `replace-with-...` 替换为账号中实际可调用的模型 ID。

### 应用成功但统一 API 仍不可用

配置应用后必须重启一次。重启时不要继续设置临时 `VAF_SETUP_ADMIN_KEY`；直接执行：

```powershell
python -m vertical_agent_factory.commercial.app
```

然后访问 `http://127.0.0.1:8000/v1/health`。返回 `status: ok` 表示商业 API 已读取新配置；返回 `setup_required` 表示仍有配置或密钥缺失，可重新进入向导检查。

## 配置完成后的验证

先用客户 API Key 查询模型白名单：

```powershell
$headers = @{ Authorization = "Bearer <客户 API Key>" }
Invoke-RestMethod -Uri http://127.0.0.1:8000/v1/models -Headers $headers
```

再执行只读查询：

```powershell
$headers = @{
  Authorization = "Bearer <客户 API Key>"
  "Content-Type" = "application/json"
}
$body = @{
  domain = "research"
  task = "research.answer.query"
  input = @{ query = "shared Harness" }
} | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/agent/runs -Headers $headers -Body $body
```

完整生产部署、反向代理、计量和密钥轮换要求见[商业 API 接入与部署](COMMERCIAL_API.md)，各厂商模型档位见[模型前三档配置](MODEL_TIERS.md)。
