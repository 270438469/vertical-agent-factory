# 模型前三档配置

本文记录商业 API 示例配置中的模型选择。目录锁定日期为 **2026-08-09**；顺序固定为“最高能力 → 均衡 → 高速/低成本”，每个租户、每个 Provider 最多允许三档，列表第一项必须同时是 `default_models`。

“前三档”只比较可用于本系统文本/对话 Agent 的生产模型，不把图像生成、语音、向量、专用代码模型、已弃用模型或仅邀请预览模型混入列表。厂商公开不足三档时只配置实际存在的模型，不用旧模型或虚构 ID 补足数量。

## 当前目录

| Provider | 配置顺序 | 状态与依据 |
| --- | --- | --- |
| `openai` | `gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-5.6-luna` | 官方依次定义为旗舰、能力/成本均衡、高吞吐低成本。[模型目录](https://developers.openai.com/api/docs/models) |
| `anthropic` | `claude-fable-5`、`claude-opus-5`、`claude-sonnet-5` | 按公开能力层级排序。[模型概览](https://platform.claude.com/docs/en/about-claude/models/overview) |
| `gemini` | `gemini-3.5-flash`、`gemini-3.6-flash`、`gemini-3.5-flash-lite` | 均为 GA；覆盖最高持续性能、Agent 均衡和高吞吐。[模型目录](https://ai.google.dev/gemini-api/docs/models) |
| `qwen` | `qwen3.7-max`、`qwen3.7-plus`、`qwen3.6-flash` | 使用稳定版高能力、均衡、轻量三档，未采用仅 Token Plan 可用的 preview。[文本生成目录](https://help.aliyun.com/zh/model-studio/text-generation-model) |
| `deepseek` | `deepseek-v4-pro`、`deepseek-v4-flash` | 官方当前只发布两个生产 Chat 模型，因此不补第三个。[模型与价格](https://api-docs.deepseek.com/quick_start/pricing) |
| `zhipu` | `glm-5.2`、`glm-5.1`、`glm-5` | 当前前三个通用文本旗舰版本。[模型概览](https://docs.bigmodel.cn/cn/guide/start/model-overview) |
| `moonshot` | `kimi-k3`、`kimi-k2.6`、`kimi-k2.5` | 排除 `kimi-k2.7-code` 专用代码模型。[官方完整文档索引](https://platform.kimi.com/docs/llms-full.txt) |
| `minimax` | `MiniMax-M3`、`MiniMax-M2.7`、`MiniMax-M2.7-highspeed` | 通用 Agent 模型与对应高速档。[官方完整文档索引](https://platform.minimaxi.com/docs/llms-full.txt) |
| `doubao` | `doubao-seed-evolving`、`doubao-seed-2.1-pro`、`doubao-seed-2.1-turbo` | 当前产品三档。部分方舟账号必须把三项替换为对应的 Endpoint ID。[豆包模型页](https://www.volcengine.com/product/doubao) |
| `hunyuan` | `hunyuan-a13b`、`hunyuan-turbos-latest`、`hunyuan-lite` | 适用于当前腾讯混元旧平台兼容入口。官方已公告旧平台将在 2026-09-30 停服，生产部署应规划迁移 TokenHub。[产品概述](https://cloud.tencent.com/document/product/1729/104753) |
| `qianfan` | `ernie-5.1`、`ernie-5.0`、`ernie-4.5-turbo-128k` | 文心当前推荐通用层级。[模型列表](https://cloud.baidu.com/doc/qianfan-docs/s/7m95lyy43) |
| `stepfun` | `step-3.5-flash`、`step-3`、`step-2-mini` | 官方推荐的推理/文本、通用多模态推理和高速文本档。[模型能力概览](https://platform.stepfun.ai/docs/en/guides/models/overview) |
| `yi` | `yi-lightning` | 公开目录当前只列一个通用文本模型；`Yi-Vision-V2` 不纳入纯文本前三档。[开放平台](https://platform.lingyiwanwu.com/) |
| `baichuan` | `Baichuan4-Turbo`、`Baichuan4`、`Baichuan4-Air` | 通用模型的增强旗舰、旗舰、低成本档。[开放平台](https://platform.baichuan-ai.com/console/authentication) |
| `spark` | `xsparkx2agent`、`xsparkx2`、`xsparkx2flash` | 使用星辰 Token Plan 的当前 Agent、旗舰、Flash 三档；内置 Base URL 已同步为其 OpenAI 兼容入口。[Token Plan 文档](https://www.xfyun.cn/doc/spark/TokenPlan.html) |
| `siliconflow` | 三个 `replace-with-siliconflow-top*-model-id` 槽位 | SiliconFlow 是聚合平台，模型会持续上下线。部署时从登录后的模型广场选当前前三个已开通文本模型并替换槽位。[快速开始](https://docs.siliconflow.cn/cn/userguide/quickstart) |
| `sensenova` | V6.5 Pro、V6.5 Turbo、V6 Reasoner 的三个账号模型 ID 槽位 | API 要求先查询本账号可用模型 ID，因此示例不伪造公共 ID。[融合模态模型文档](https://platform.sensenova.cn/product/APIService/document) |
| `mimo` | `mimo-v2.5-pro`、`mimo-v2.5` | 官方当前只有两个通用文本模型；ASR/TTS 不纳入。[模型列表](https://mimo.mi.com/docs/zh-CN/quick-start/summary/model) |
| `longcat` | `LongCat-2.0` | 官方当前只有一个生产文本模型。[Chat Completions](https://longcat.chat/platform/docs/api/chat.html) |

## 部署前必须替换的项目

复制 `config/commercial.example.yaml` 后，检查以下配置：

1. `siliconflow`：登录模型广场，从账号实际可见模型中选择三个文本模型，按能力从高到低替换三个槽位。
2. `sensenova`：调用厂商模型列表 API，使用账号返回的 V6.5 Pro、V6.5 Turbo、V6 Reasoner 模型 ID 替换三个槽位。
3. `doubao`：若账号不接受公共模型别名，在方舟控制台创建对应三档推理接入点，并用三个 Endpoint ID 替换别名。
4. 删除租户未购买、未授权或未完成回归测试的模型；不要为了凑满三档而保留不可调用项。

## 更新流程

模型目录具有时效性。建议每月或收到厂商下线公告时执行一次：

1. 只查看上表中的厂商官方模型目录、价格页和下线公告。
2. 排除预览、专用模态和已弃用模型，按“能力 → 均衡 → 成本/速度”选最多三项。
3. 更新 `allowed_models`，并让 `default_models` 等于列表第一项。
4. 执行 `python -m pytest`、Golden Evals、Web 测试和构建。
5. 使用真实测试账号做最小请求；仓库测试只验证配置、协议和解析，不消耗厂商额度，也不能证明账号已获得模型权限。

配置加载器会拒绝超过三项、重复模型，以及默认模型不是第一档的租户配置，从而防止旧配置悄悄漂移。
