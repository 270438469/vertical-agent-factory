import pytest

from vertical_agent_factory.model_providers import (
    AnthropicProvider,
    GeminiProvider,
    ModelProviderError,
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
