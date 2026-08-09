"""Official model API adapters used by the commercial gateway.

The adapters intentionally use the vendors' documented HTTPS APIs directly. This
keeps the core runtime independent from vendor SDK release cycles and makes the
HTTP boundary straightforward to fake in tests.
"""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .errors import RuntimeExecutionError


class ModelProviderError(RuntimeExecutionError):
    """A configured model provider rejected or failed a request."""


@dataclass
class ModelResult:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    vendor_request_id: str = ""

    def usage(self):
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


class JsonHttpTransport(object):
    """Small JSON transport with bounded response reads and sanitized errors."""

    def __init__(self, timeout_seconds=60, maximum_response_bytes=5 * 1024 * 1024):
        self.timeout_seconds = timeout_seconds
        self.maximum_response_bytes = maximum_response_bytes

    def post(self, url, headers, payload):
        body = json.dumps(payload).encode("utf-8")
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read(self.maximum_response_bytes + 1)
                if len(raw) > self.maximum_response_bytes:
                    raise ModelProviderError("Provider response exceeded size limit")
                return json.loads(raw.decode("utf-8")), {
                    key.lower(): value for key, value in response.headers.items()
                }
        except HTTPError as exc:
            # Do not surface response bodies: vendors may echo submitted content.
            raise ModelProviderError("Provider returned HTTP {}".format(exc.code))
        except URLError as exc:
            raise ModelProviderError("Provider connection failed: {}".format(exc.reason))
        except (ValueError, UnicodeDecodeError):
            raise ModelProviderError("Provider returned invalid JSON")


class BaseModelProvider(object):
    provider_id = None

    def __init__(self, api_key, transport=None):
        if not api_key:
            raise ModelProviderError("{} API key is not configured".format(self.provider_id))
        self.api_key = api_key
        self.transport = transport or JsonHttpTransport()

    def generate(self, model, prompt, instructions=None, maximum_output_tokens=800):
        raise NotImplementedError


class OpenAIProvider(BaseModelProvider):
    provider_id = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def generate(self, model, prompt, instructions=None, maximum_output_tokens=800):
        payload = {
            "model": model,
            "input": prompt,
            "max_output_tokens": maximum_output_tokens,
        }
        if instructions:
            payload["instructions"] = instructions
        data, headers = self.transport.post(
            self.endpoint,
            {
                "Authorization": "Bearer {}".format(self.api_key),
                "Content-Type": "application/json",
            },
            payload,
        )
        text = data.get("output_text") or self._output_text(data.get("output", []))
        if not text:
            raise ModelProviderError("OpenAI response did not contain output text")
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        return ModelResult(
            text=text,
            provider=self.provider_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=int(usage.get("total_tokens") or input_tokens + output_tokens),
            vendor_request_id=data.get("id") or headers.get("x-request-id", ""),
        )

    @staticmethod
    def _output_text(output):
        parts = []
        for item in output:
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(content["text"])
        return "\n".join(parts)


class AnthropicProvider(BaseModelProvider):
    provider_id = "anthropic"
    endpoint = "https://api.anthropic.com/v1/messages"

    def generate(self, model, prompt, instructions=None, maximum_output_tokens=800):
        payload = {
            "model": model,
            "max_tokens": maximum_output_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if instructions:
            payload["system"] = instructions
        data, headers = self.transport.post(
            self.endpoint,
            {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            payload,
        )
        text = "\n".join(
            item.get("text", "")
            for item in data.get("content", [])
            if item.get("type") == "text" and item.get("text")
        )
        if not text:
            raise ModelProviderError("Anthropic response did not contain output text")
        usage = data.get("usage") or {}
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
        return ModelResult(
            text=text,
            provider=self.provider_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            vendor_request_id=data.get("id") or headers.get("request-id", ""),
        )


class GeminiProvider(BaseModelProvider):
    provider_id = "gemini"
    endpoint_template = (
        "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
    )

    def generate(self, model, prompt, instructions=None, maximum_output_tokens=800):
        combined = prompt
        if instructions:
            combined = "{}\n\n{}".format(instructions, prompt)
        payload = {
            "contents": [{"role": "user", "parts": [{"text": combined}]}],
            "generationConfig": {"maxOutputTokens": maximum_output_tokens},
        }
        url = self.endpoint_template.format(quote(model, safe=""))
        data, headers = self.transport.post(
            url,
            {"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            payload,
        )
        parts = []
        for candidate in data.get("candidates", []):
            for item in candidate.get("content", {}).get("parts", []):
                if item.get("text"):
                    parts.append(item["text"])
        text = "\n".join(parts)
        if not text:
            raise ModelProviderError("Gemini response did not contain output text")
        usage = data.get("usageMetadata") or {}
        input_tokens = int(usage.get("promptTokenCount") or 0)
        output_tokens = int(usage.get("candidatesTokenCount") or 0)
        return ModelResult(
            text=text,
            provider=self.provider_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=int(usage.get("totalTokenCount") or input_tokens + output_tokens),
            vendor_request_id=headers.get("x-request-id", ""),
        )


CHINA_OPENAI_COMPATIBLE_PROVIDERS = {
    "qwen": {
        "name": "Alibaba Cloud Model Studio (Qwen)",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "allowed_hosts": (
            "dashscope.aliyuncs.com",
            "dashscope-intl.aliyuncs.com",
            "dashscope-us.aliyuncs.com",
            ".maas.aliyuncs.com",
        ),
    },
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "allowed_hosts": ("api.deepseek.com",),
    },
    "zhipu": {
        "name": "Zhipu BigModel (GLM)",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "allowed_hosts": ("open.bigmodel.cn",),
    },
    "moonshot": {
        "name": "Moonshot AI (Kimi)",
        "base_url": "https://api.moonshot.cn/v1",
        "allowed_hosts": ("api.moonshot.cn", "api.moonshot.ai"),
    },
    "minimax": {
        "name": "MiniMax",
        "base_url": "https://api.minimaxi.com/v1",
        "allowed_hosts": ("api.minimaxi.com", "api.minimax.io"),
    },
    "doubao": {
        "name": "Volcengine Ark (Doubao)",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "allowed_hosts": ("ark.cn-beijing.volces.com", ".volces.com"),
    },
    "hunyuan": {
        "name": "Tencent Hunyuan",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "allowed_hosts": ("api.hunyuan.cloud.tencent.com",),
    },
    "qianfan": {
        "name": "Baidu Qianfan",
        "base_url": "https://qianfan.baidubce.com/v2",
        "allowed_hosts": ("qianfan.baidubce.com", ".qianfan.baidubce.com"),
    },
    "stepfun": {
        "name": "StepFun",
        "base_url": "https://api.stepfun.ai/v1",
        "allowed_hosts": ("api.stepfun.ai",),
    },
    "yi": {
        "name": "01.AI (Yi)",
        "base_url": "https://api.lingyiwanwu.com/v1",
        "allowed_hosts": ("api.lingyiwanwu.com",),
    },
    "baichuan": {
        "name": "Baichuan AI",
        "base_url": "https://api.baichuan-ai.com/v1",
        "allowed_hosts": ("api.baichuan-ai.com",),
    },
    "spark": {
        "name": "iFLYTEK Spark",
        "base_url": "https://spark-api-open.xf-yun.com/v1",
        "allowed_hosts": ("spark-api-open.xf-yun.com",),
    },
    "siliconflow": {
        "name": "SiliconFlow",
        "base_url": "https://api.siliconflow.cn/v1",
        "allowed_hosts": ("api.siliconflow.cn",),
    },
    "sensenova": {
        "name": "SenseNova",
        "base_url": "https://api.sensenova.cn/compatible-mode/v1",
        "allowed_hosts": ("api.sensenova.cn", ".sensenova.cn"),
    },
    "mimo": {
        "name": "Xiaomi MiMo",
        "base_url": "https://api.xiaomimimo.com/v1",
        "allowed_hosts": ("api.xiaomimimo.com",),
    },
    "longcat": {
        "name": "Meituan LongCat",
        "base_url": "https://api.longcat.chat/openai/v1",
        "allowed_hosts": ("api.longcat.chat",),
    },
}


def _host_allowed(host, allowed_hosts):
    host = (host or "").lower().rstrip(".")
    for allowed in allowed_hosts:
        allowed = allowed.lower().rstrip(".")
        if allowed.startswith("."):
            if host.endswith(allowed) and host != allowed[1:]:
                return True
        elif host == allowed:
            return True
    return False


class OpenAICompatibleProvider(BaseModelProvider):
    """Chat Completions adapter for allowlisted Chinese provider endpoints."""

    def __init__(self, provider_id, api_key, base_url=None, transport=None):
        definition = CHINA_OPENAI_COMPATIBLE_PROVIDERS.get(provider_id)
        if definition is None:
            raise ModelProviderError("Unsupported compatible provider: {}".format(provider_id))
        self.provider_id = provider_id
        selected_base_url = (base_url or definition["base_url"]).rstrip("/")
        parsed = urlparse(selected_base_url)
        try:
            parsed_port = parsed.port
        except ValueError:
            raise ModelProviderError("Provider base URL contains an invalid port")
        if parsed.scheme != "https" or not _host_allowed(
            parsed.hostname, definition["allowed_hosts"]
        ):
            raise ModelProviderError(
                "Provider base URL is outside the official host allowlist"
            )
        if (
            parsed.query
            or parsed.fragment
            or parsed.username
            or parsed.password
            or parsed_port not in (None, 443)
        ):
            raise ModelProviderError("Provider base URL contains unsupported components")
        self.endpoint = (
            selected_base_url
            if selected_base_url.endswith("/chat/completions")
            else selected_base_url + "/chat/completions"
        )
        super().__init__(api_key, transport=transport)

    def generate(self, model, prompt, instructions=None, maximum_output_tokens=800):
        messages = []
        if instructions:
            messages.append({"role": "system", "content": instructions})
        messages.append({"role": "user", "content": prompt})
        data, headers = self.transport.post(
            self.endpoint,
            {
                "Authorization": "Bearer {}".format(self.api_key),
                "Content-Type": "application/json",
            },
            {
                "model": model,
                "messages": messages,
                "max_tokens": maximum_output_tokens,
                "stream": False,
            },
        )
        choices = data.get("choices") or []
        content = (choices[0].get("message") or {}).get("content") if choices else None
        if isinstance(content, list):
            text = "\n".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("text")
            )
        else:
            text = content or ""
        if not text:
            raise ModelProviderError(
                "{} response did not contain output text".format(self.provider_id)
            )
        usage = data.get("usage") or {}
        input_tokens = int(
            usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        )
        output_tokens = int(
            usage.get("completion_tokens") or usage.get("output_tokens") or 0
        )
        return ModelResult(
            text=text,
            provider=self.provider_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=int(usage.get("total_tokens") or input_tokens + output_tokens),
            vendor_request_id=data.get("id") or headers.get("x-request-id", ""),
        )


PROVIDER_TYPES = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}


class ModelGateway(object):
    def __init__(self, api_keys, base_urls=None, transport=None):
        self.api_keys = dict(api_keys or {})
        self.base_urls = dict(base_urls or {})
        self.transport = transport

    def generate(self, provider, model, prompt, instructions=None, maximum_output_tokens=800):
        provider_type = PROVIDER_TYPES.get(provider)
        if provider_type is not None:
            client = provider_type(self.api_keys.get(provider), transport=self.transport)
        elif provider in CHINA_OPENAI_COMPATIBLE_PROVIDERS:
            client = OpenAICompatibleProvider(
                provider,
                self.api_keys.get(provider),
                base_url=self.base_urls.get(provider),
                transport=self.transport,
            )
        else:
            raise ModelProviderError("Unsupported model provider: {}".format(provider))
        return client.generate(
            model,
            prompt,
            instructions=instructions,
            maximum_output_tokens=maximum_output_tokens,
        )
