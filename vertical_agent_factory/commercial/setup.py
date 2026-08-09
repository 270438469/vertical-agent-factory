"""No-code setup catalog, validation, preview, and local file application."""

import hmac
import os
import tempfile
from pathlib import Path

import yaml

from ..model_providers import OpenAICompatibleProvider
from .config import CommercialConfigError, load_commercial_config


PROVIDER_CATALOG = {
    "openai": {
        "name": "OpenAI",
        "api_key_env": "OPENAI_API_KEY",
        "models": ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"],
        "console_url": "https://platform.openai.com/api-keys",
        "preparation": "创建 API Project 和 API Key，并确认项目已开通计费与模型权限。",
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "api_key_env": "ANTHROPIC_API_KEY",
        "models": ["claude-fable-5", "claude-opus-5", "claude-sonnet-5"],
        "console_url": "https://console.anthropic.com/settings/keys",
        "preparation": "在 Claude Console 创建 API Key，并确认组织的模型权限。",
    },
    "gemini": {
        "name": "Google Gemini",
        "api_key_env": "GEMINI_API_KEY",
        "models": ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"],
        "console_url": "https://aistudio.google.com/app/apikey",
        "preparation": "在 Google AI Studio 创建 API Key，并确认项目配额。",
    },
    "qwen": {
        "name": "阿里云百炼 / 通义千问",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url_env": "DASHSCOPE_BASE_URL",
        "models": ["qwen3.7-max", "qwen3.7-plus", "qwen3.6-flash"],
        "console_url": "https://help.aliyun.com/zh/model-studio/get-api-key",
        "preparation": "开通百炼、创建 API Key；新工作空间还需复制地域/工作空间专属 Base URL。",
    },
    "deepseek": {
        "name": "DeepSeek",
        "api_key_env": "DEEPSEEK_API_KEY",
        "models": ["deepseek-v4-pro", "deepseek-v4-flash"],
        "console_url": "https://platform.deepseek.com/api_keys",
        "preparation": "创建 API Key，并确认账户余额或组织授权。",
    },
    "zhipu": {
        "name": "智谱 BigModel / GLM",
        "api_key_env": "ZHIPU_API_KEY",
        "models": ["glm-5.2", "glm-5.1", "glm-5"],
        "console_url": "https://open.bigmodel.cn/usercenter/apikeys",
        "preparation": "在 BigModel 用户中心创建 API Key。",
    },
    "moonshot": {
        "name": "月之暗面 Kimi",
        "api_key_env": "MOONSHOT_API_KEY",
        "base_url_env": "MOONSHOT_BASE_URL",
        "models": ["kimi-k3", "kimi-k2.6", "kimi-k2.5"],
        "console_url": "https://platform.kimi.com/docs/api/overview",
        "preparation": "在 Kimi 开放平台创建 API Key；国际账号可填写国际 Base URL。",
    },
    "minimax": {
        "name": "MiniMax",
        "api_key_env": "MINIMAX_API_KEY",
        "base_url_env": "MINIMAX_BASE_URL",
        "models": ["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
        "console_url": "https://platform.minimaxi.com/docs/api-reference/api-overview",
        "preparation": "创建 API Key；国际账号可填写国际 Base URL。",
    },
    "doubao": {
        "name": "火山方舟 / 豆包",
        "api_key_env": "ARK_API_KEY",
        "base_url_env": "ARK_BASE_URL",
        "models": ["doubao-seed-evolving", "doubao-seed-2.1-pro", "doubao-seed-2.1-turbo"],
        "console_url": "https://www.volcengine.com/docs/82379/1330626",
        "preparation": "创建方舟 API Key；若账号要求 Endpoint ID，请把三个模型名替换为已创建的 Endpoint ID。",
        "custom_models": True,
    },
    "hunyuan": {
        "name": "腾讯混元",
        "api_key_env": "HUNYUAN_API_KEY",
        "models": ["hunyuan-a13b", "hunyuan-turbos-latest", "hunyuan-lite"],
        "console_url": "https://cloud.tencent.com/document/product/1729/111007",
        "preparation": "获取 OpenAI 兼容接口凭证；旧平台用户同时规划 TokenHub 迁移。",
    },
    "qianfan": {
        "name": "百度千帆 / 文心",
        "api_key_env": "QIANFAN_API_KEY",
        "models": ["ernie-5.1", "ernie-5.0", "ernie-4.5-turbo-128k"],
        "console_url": "https://cloud.baidu.com/doc/Qianfan/index.html",
        "preparation": "创建 OpenAI 兼容 API 专用 Key，不要填写旧 AK/SK 签名凭证。",
    },
    "stepfun": {
        "name": "阶跃星辰 StepFun",
        "api_key_env": "STEPFUN_API_KEY",
        "models": ["step-3.5-flash", "step-3", "step-2-mini"],
        "console_url": "https://platform.stepfun.ai/docs",
        "preparation": "在开放平台创建 API Key 并开通所选模型。",
    },
    "yi": {
        "name": "零一万物 Yi",
        "api_key_env": "YI_API_KEY",
        "models": ["yi-lightning"],
        "console_url": "https://platform.lingyiwanwu.com/",
        "preparation": "在开放平台创建 API Key；当前公开通用文本模型只有一档。",
    },
    "baichuan": {
        "name": "百川智能",
        "api_key_env": "BAICHUAN_API_KEY",
        "models": ["Baichuan4-Turbo", "Baichuan4", "Baichuan4-Air"],
        "console_url": "https://platform.baichuan-ai.com/console/authentication",
        "preparation": "在开放平台完成认证并创建 API Key。",
    },
    "spark": {
        "name": "讯飞星火 / 星辰 Token Plan",
        "api_key_env": "SPARK_API_KEY",
        "models": ["xsparkx2agent", "xsparkx2", "xsparkx2flash"],
        "console_url": "https://www.xfyun.cn/doc/spark/TokenPlan.html",
        "preparation": "购买或开通 Token Plan，复制套餐专属 API Key；不要填写旧版 API Password。",
    },
    "siliconflow": {
        "name": "SiliconFlow 硅基流动",
        "api_key_env": "SILICONFLOW_API_KEY",
        "models": ["replace-with-siliconflow-top1-model-id", "replace-with-siliconflow-top2-model-id", "replace-with-siliconflow-top3-model-id"],
        "console_url": "https://docs.siliconflow.cn/cn/userguide/quickstart",
        "preparation": "创建 API Key，并从登录后的模型广场复制当前账号已开通的前三个文本模型 ID。",
        "custom_models": True,
    },
    "sensenova": {
        "name": "商汤 SenseNova",
        "api_key_env": "SENSENOVA_API_KEY",
        "models": ["replace-with-sensenova-v6.5-pro-model-id", "replace-with-sensenova-v6.5-turbo-model-id", "replace-with-sensenova-v6-reasoner-model-id"],
        "console_url": "https://platform.sensenova.cn/product/APIService/document",
        "preparation": "创建凭证，调用模型列表或在控制台复制本账号真实模型 ID。",
        "custom_models": True,
    },
    "mimo": {
        "name": "小米 MiMo",
        "api_key_env": "MIMO_API_KEY",
        "models": ["mimo-v2.5-pro", "mimo-v2.5"],
        "console_url": "https://mimo.mi.com/docs/zh-CN/quick-start/summary/first-api-call",
        "preparation": "在小米 MiMo 平台创建 API Key；当前通用文本模型只有两档。",
    },
    "longcat": {
        "name": "美团 LongCat",
        "api_key_env": "LONGCAT_API_KEY",
        "models": ["LongCat-2.0"],
        "console_url": "https://longcat.chat/platform/docs/",
        "preparation": "创建 API Key 并确认额度；当前生产文本模型只有一档。",
    },
}


class SetupValidationError(ValueError):
    """The human-friendly setup request cannot be converted safely."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


def public_catalog():
    """Return catalog data without credentials or mutable internal objects."""
    return {
        provider_id: dict(definition)
        for provider_id, definition in PROVIDER_CATALOG.items()
    }


def setup_enabled():
    return len(os.environ.get("VAF_SETUP_ADMIN_KEY", "")) >= 32


def authorize_setup(value):
    expected = os.environ.get("VAF_SETUP_ADMIN_KEY", "")
    supplied = value or ""
    if supplied.startswith("Bearer "):
        supplied = supplied[len("Bearer ") :]
    supplied = supplied.strip()
    return len(expected) >= 32 and hmac.compare_digest(expected, supplied)


def remote_setup_allowed(client_host):
    if os.environ.get("VAF_SETUP_ALLOW_REMOTE", "0").lower() in {"1", "true", "yes"}:
        return True
    return client_host in {"127.0.0.1", "::1", "localhost", "testclient"}


def _safe_identifier(value):
    return bool(value) and len(value) <= 80 and all(
        character.isalnum() or character in "-_" for character in value
    )


def _safe_secret(value):
    return isinstance(value, str) and bool(value) and not any(
        character in value for character in ("\r", "\n", "\0")
    )


def _tenant_env_name(tenant_id):
    normalized = "".join(
        character.upper() if character.isalnum() else "_" for character in tenant_id
    )
    return "VAF_API_KEY_{}".format(normalized)


def convert_setup(payload, require_secrets=False):
    """Convert no-code form data into validated YAML and secret environment data."""
    errors = []
    tenant_id = str(payload.get("tenant_id") or "").strip()
    if not _safe_identifier(tenant_id):
        errors.append("客户标识只能包含字母、数字、短横线或下划线，且不超过 80 个字符")

    tasks = list(dict.fromkeys(payload.get("allowed_tasks") or []))
    supported_tasks = {"research.answer.query", "research.report.publish"}
    if not tasks or any(task not in supported_tasks for task in tasks):
        errors.append("至少选择一个受支持的 Agent 任务")

    provider_inputs = payload.get("providers") or []
    provider_by_id = {}
    for raw in provider_inputs:
        provider_id = str((raw or {}).get("id") or "").strip()
        if provider_id not in PROVIDER_CATALOG:
            errors.append("存在不受支持的模型厂商：{}".format(provider_id or "空值"))
            continue
        if provider_id in provider_by_id:
            errors.append("模型厂商重复：{}".format(provider_id))
            continue
        provider_by_id[provider_id] = raw

    default_provider = str(payload.get("default_provider") or "local")
    allowed_provider_ids = ["local"] + list(provider_by_id)
    if default_provider not in allowed_provider_ids:
        errors.append("默认模型厂商必须先被选中")

    try:
        rate_limit = int(payload.get("rate_limit_per_minute", 60))
        monthly_quota = int(payload.get("monthly_request_quota", 10000))
        if rate_limit < 1 or rate_limit > 100000:
            raise ValueError
        if monthly_quota < 1 or monthly_quota > 1000000000:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("每分钟限流和每月额度必须是合理的正整数")
        rate_limit, monthly_quota = 60, 10000

    providers = {}
    allowed_models = {}
    default_models = {}
    secrets = {}
    warnings = []
    for provider_id, raw in provider_by_id.items():
        definition = PROVIDER_CATALOG[provider_id]
        models = [str(model).strip() for model in (raw.get("models") or [])]
        models = list(dict.fromkeys(model for model in models if model))
        if not 1 <= len(models) <= 3:
            errors.append("{} 必须配置一到三档模型".format(definition["name"]))
        if any(model.startswith("replace-with-") for model in models):
            errors.append("{} 仍有占位模型 ID，请替换为账号中的真实 ID".format(definition["name"]))

        api_key = str(raw.get("api_key") or "")
        if api_key and not _safe_secret(api_key):
            errors.append("{} API Key 包含不允许的换行或空字符".format(definition["name"]))
        if require_secrets and not api_key:
            errors.append("{} 缺少 API Key".format(definition["name"]))
        if api_key:
            secrets[definition["api_key_env"]] = api_key

        provider_config = {"api_key_env": definition["api_key_env"]}
        base_url = str(raw.get("base_url") or "").strip()
        if base_url:
            if not definition.get("base_url_env"):
                errors.append("{} 不支持自定义 Base URL".format(definition["name"]))
            else:
                try:
                    OpenAICompatibleProvider(provider_id, "setup-validation", base_url=base_url)
                except Exception as exc:
                    errors.append("{} Base URL 无效：{}".format(definition["name"], exc))
                secrets[definition["base_url_env"]] = base_url
        if definition.get("base_url_env"):
            provider_config["base_url_env"] = definition["base_url_env"]
        providers[provider_id] = provider_config
        allowed_models[provider_id] = models
        if models:
            default_models[provider_id] = models[0]

    customer_api_key = str(payload.get("customer_api_key") or "")
    if customer_api_key and not _safe_secret(customer_api_key):
        errors.append("客户调用密钥包含不允许的换行或空字符")
    if require_secrets and len(customer_api_key) < 32:
        errors.append("客户调用密钥至少需要 32 个字符")
    elif customer_api_key and len(customer_api_key) < 32:
        warnings.append("客户调用密钥不足 32 个字符，正式应用前必须重新生成")

    if errors:
        raise SetupValidationError(errors)

    tenant_env = _tenant_env_name(tenant_id)
    if customer_api_key:
        secrets[tenant_env] = customer_api_key
    config = {
        "project_root": "..",
        "database_path": ".commercial/usage.sqlite3",
        "providers": providers,
        "tenants": [
            {
                "id": tenant_id,
                "api_key_env": tenant_env,
                "allowed_domains": ["research"],
                "allowed_tasks": tasks,
                "allowed_providers": allowed_provider_ids,
                "default_provider": default_provider,
                "allowed_models": allowed_models,
                "default_models": default_models,
                "approved_capabilities": [],
                "rate_limit_per_minute": rate_limit,
                "monthly_request_quota": monthly_quota,
            }
        ],
    }
    yaml_text = yaml.safe_dump(
        config, allow_unicode=True, sort_keys=False, default_flow_style=False
    )
    env_template = "\n".join(
        "{}={}".format(name, "configured" if name in secrets else "<请填写>")
        for name in [tenant_env]
        + [PROVIDER_CATALOG[item]["api_key_env"] for item in provider_by_id]
        + [
            PROVIDER_CATALOG[item]["base_url_env"]
            for item in provider_by_id
            if PROVIDER_CATALOG[item].get("base_url_env")
        ]
    )
    return {
        "config": config,
        "yaml": yaml_text,
        "environment_template": env_template + "\n",
        "secret_status": {name: bool(value) for name, value in secrets.items()},
        "secrets": secrets,
        "warnings": warnings,
    }


def _atomic_write(path, content):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".{}-".format(path.name), dir=str(path.parent), text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_name, str(path))
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def _merge_environment(path, secrets):
    path = Path(path).resolve()
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    managed = set(secrets)
    output = []
    written = set()
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in managed:
            output.append("{}={}".format(key, secrets[key]))
            written.add(key)
        else:
            output.append(line)
    if output and output[-1]:
        output.append("")
    if managed - written:
        output.append("# Managed by the Vertical Agent Factory setup UI")
        for key in sorted(managed - written):
            output.append("{}={}".format(key, secrets[key]))
    _atomic_write(path, "\n".join(output).rstrip() + "\n")


def load_local_environment(path):
    """Load the setup-managed env file without overriding process variables."""
    environment_path = Path(path).resolve()
    if not environment_path.exists():
        return
    for line in environment_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and all(character.isalnum() or character == "_" for character in key):
            os.environ.setdefault(key, value)


def apply_setup(payload, config_path, environment_path):
    converted = convert_setup(payload, require_secrets=True)
    _atomic_write(config_path, converted["yaml"])
    _merge_environment(environment_path, converted["secrets"])
    try:
        load_commercial_config(config_path)
    except CommercialConfigError:
        raise
    return {
        "status": "applied",
        "config_path": str(Path(config_path).resolve()),
        "environment_path": str(Path(environment_path).resolve()),
        "restart_required": True,
        "configured_secrets": sorted(converted["secrets"]),
        "warnings": converted["warnings"],
    }
