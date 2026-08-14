import pytest

from vertical_agent_factory.model_providers import (
    AnthropicProvider,
    CHINA_OPENAI_COMPATIBLE_PROVIDERS,
    GeminiProvider,
    ModelProviderError,
    ModelGateway,
    OpenAICompatibleProvider,
    OpenAIProvider,
)


class FakeTransport(object):
    def __init__(self, response, headers=None):
        self.response = response
        self.headers = headers or {}
        self.calls = []

    def post(self, url, headers, payload):
        self.calls.append((url, headers, payload))
        return self.response, self.headers


def test_openai_responses_api_is_parsed():
    transport = FakeTransport(
        {
            "id": "resp_123",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "grounded answer"}],
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
        }
    )
    result = OpenAIProvider("secret", transport=transport).generate(
        "approved-model", "prompt", instructions="system"
    )
    assert result.text == "grounded answer"
    assert result.total_tokens == 14
    url, headers, payload = transport.calls[0]
    assert url == "https://api.openai.com/v1/responses"
    assert headers["Authorization"] == "Bearer secret"
    assert payload["instructions"] == "system"


def test_anthropic_messages_api_is_parsed():
    transport = FakeTransport(
        {
            "id": "msg_123",
            "content": [{"type": "text", "text": "reviewed answer"}],
            "usage": {"input_tokens": 8, "output_tokens": 3},
        }
    )
    result = AnthropicProvider("secret", transport=transport).generate(
        "approved-model", "prompt"
    )
    assert result.text == "reviewed answer"
    assert result.total_tokens == 11
    _, headers, payload = transport.calls[0]
    assert headers["anthropic-version"] == "2023-06-01"
    assert payload["messages"][0]["role"] == "user"


def test_gemini_generate_content_api_is_parsed():
    transport = FakeTransport(
        {
            "candidates": [{"content": {"parts": [{"text": "verified answer"}]}}],
            "usageMetadata": {
                "promptTokenCount": 7,
                "candidatesTokenCount": 2,
                "totalTokenCount": 9,
            },
        }
    )
    result = GeminiProvider("secret", transport=transport).generate(
        "approved/model", "prompt"
    )
    assert result.text == "verified answer"
    assert result.total_tokens == 9
    url, headers, _ = transport.calls[0]
    assert "approved%2Fmodel" in url
    assert headers["x-goog-api-key"] == "secret"


def test_provider_requires_a_server_side_key():
    with pytest.raises(ModelProviderError):
        OpenAIProvider("")


def test_provider_rejects_empty_model_output():
    with pytest.raises(ModelProviderError):
        OpenAIProvider("secret", transport=FakeTransport({"output": []})).generate(
            "approved-model", "prompt"
        )


@pytest.mark.parametrize("provider_id", sorted(CHINA_OPENAI_COMPATIBLE_PROVIDERS))
def test_china_compatible_provider_contract(provider_id):
    transport = FakeTransport(
        {
            "id": "chatcmpl-cn-1",
            "choices": [
                {"message": {"role": "assistant", "content": "verified result"}}
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 5,
                "total_tokens": 17,
            },
        }
    )
    gateway = ModelGateway({provider_id: "server-secret"}, transport=transport)
    result = gateway.generate(
        provider_id, "tenant-approved-model", "prompt", instructions="system"
    )
    assert result.provider == provider_id
    assert result.text == "verified result"
    assert result.total_tokens == 17
    url, headers, payload = transport.calls[0]
    assert url.endswith("/chat/completions")
    assert headers["Authorization"] == "Bearer server-secret"
    assert payload["messages"][0] == {"role": "system", "content": "system"}
    assert payload["stream"] is False


def test_qwen_workspace_base_url_override_is_allowlisted():
    transport = FakeTransport(
        {
            "choices": [{"message": {"content": "workspace result"}}],
            "usage": {},
        }
    )
    gateway = ModelGateway(
        {"qwen": "secret"},
        base_urls={
            "qwen": "https://workspace-id.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
        },
        transport=transport,
    )
    assert gateway.generate("qwen", "approved-model", "prompt").text == "workspace result"
    assert transport.calls[0][0].startswith(
        "https://workspace-id.cn-beijing.maas.aliyuncs.com/"
    )


@pytest.mark.parametrize(
    "unsafe_url",
    [
        "http://api.deepseek.com",
        "https://api.deepseek.com.attacker.example/v1",
        "https://user:password@api.deepseek.com/v1",
        "https://api.deepseek.com:444/v1",
        "https://attacker.example/v1",
    ],
)
def test_provider_base_url_override_rejects_ssrf(unsafe_url):
    with pytest.raises(ModelProviderError, match="allowlist|unsupported"):
        OpenAICompatibleProvider("deepseek", "secret", base_url=unsafe_url)
