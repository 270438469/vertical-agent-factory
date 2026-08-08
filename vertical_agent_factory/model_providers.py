"""Official model API adapters used by the commercial gateway.

The adapters intentionally use the vendors' documented HTTPS APIs directly. This
keeps the core runtime independent from vendor SDK release cycles and makes the
HTTP boundary straightforward to fake in tests.
"""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote
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


PROVIDER_TYPES = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}


class ModelGateway(object):
    def __init__(self, api_keys, transport=None):
        self.api_keys = dict(api_keys or {})
        self.transport = transport

    def generate(self, provider, model, prompt, instructions=None, maximum_output_tokens=800):
        provider_type = PROVIDER_TYPES.get(provider)
        if provider_type is None:
            raise ModelProviderError("Unsupported model provider: {}".format(provider))
        client = provider_type(self.api_keys.get(provider), transport=self.transport)
        return client.generate(
            model,
            prompt,
            instructions=instructions,
            maximum_output_tokens=maximum_output_tokens,
        )
