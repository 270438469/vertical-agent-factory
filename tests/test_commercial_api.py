from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vertical_agent_factory.commercial.app import create_app
from vertical_agent_factory.commercial.config import (
    CommercialConfig,
    CommercialConfigError,
    TenantConfig,
    load_commercial_config,
)
from vertical_agent_factory.commercial.service import CommercialService
from vertical_agent_factory.commercial.setup import (
    SetupValidationError,
    convert_setup,
    load_local_environment,
)
from vertical_agent_factory.model_providers import ModelResult


API_KEY = "test-key-that-is-longer-than-thirty-two-bytes"


class FakeModelGateway(object):
    def __init__(self):
        self.calls = []

    def generate(self, provider, model, prompt, instructions=None, maximum_output_tokens=800):
        self.calls.append((provider, model, prompt, instructions))
        return ModelResult(
            text="Externally generated but evidence-backed.",
            provider=provider,
            model=model,
            input_tokens=20,
            output_tokens=6,
            total_tokens=26,
            vendor_request_id="vendor-1",
        )


def make_service(tmp_path, monkeypatch, rate_limit=60, quota=100):
    monkeypatch.setenv("TEST_CUSTOMER_API_KEY", API_KEY)
    tenant = TenantConfig(
        tenant_id="customer-a",
        api_key_env="TEST_CUSTOMER_API_KEY",
        allowed_domains=["research"],
        allowed_tasks=["research.answer.query", "research.report.publish"],
        allowed_providers=["local", "openai"],
        default_provider="local",
        allowed_models={"openai": ["approved-model"]},
        default_models={"openai": "approved-model"},
        rate_limit_per_minute=rate_limit,
        monthly_request_quota=quota,
    )
    config = CommercialConfig(
        project_root=Path(".").resolve(),
        database_path=tmp_path / "usage.sqlite3",
        provider_key_envs={"openai": "OPENAI_API_KEY"},
        tenants=[tenant],
    )
    gateway = FakeModelGateway()
    return CommercialService(config, model_gateway=gateway), gateway


def auth_headers(**extra):
    headers = {"Authorization": "Bearer {}".format(API_KEY)}
    headers.update(extra)
    return headers


def test_health_is_public_but_models_require_auth(tmp_path, monkeypatch):
    service, _ = make_service(tmp_path, monkeypatch)
    client = TestClient(create_app(service=service))
    assert client.get("/v1/health").status_code == 200
    response = client.get("/v1/models")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_local_agent_run_is_authenticated_and_metered(tmp_path, monkeypatch):
    service, _ = make_service(tmp_path, monkeypatch)
    client = TestClient(create_app(service=service))
    response = client.post(
        "/v1/agent/runs",
        headers=auth_headers(),
        json={
            "domain": "research",
            "task": "research.answer.query",
            "input": {"query": "shared Harness"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "local"
    assert body["result"]["status"] == "SUCCESS"
    assert response.headers["x-request-id"] == body["request_id"]
    usage = client.get("/v1/usage", headers=auth_headers()).json()
    assert usage["requests"] == 1
    assert usage["requests_remaining"] == 99


def test_external_provider_is_allowlisted_and_usage_is_reported(tmp_path, monkeypatch):
    service, gateway = make_service(tmp_path, monkeypatch)
    client = TestClient(create_app(service=service))
    response = client.post(
        "/v1/agent/runs",
        headers=auth_headers(),
        json={
            "domain": "research",
            "task": "research.answer.query",
            "input": {"query": "shared Harness"},
            "provider": "openai",
            "model": "approved-model",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["usage"]["total_tokens"] == 26
    assert body["result"]["metadata"]["model_provider"] == "openai"
    assert gateway.calls[0][0:2] == ("openai", "approved-model")


def test_unapproved_model_and_task_are_forbidden(tmp_path, monkeypatch):
    service, _ = make_service(tmp_path, monkeypatch)
    client = TestClient(create_app(service=service))
    model_response = client.post(
        "/v1/agent/runs",
        headers=auth_headers(),
        json={
            "domain": "research",
            "task": "research.answer.query",
            "input": {"query": "Harness"},
            "provider": "openai",
            "model": "expensive-unapproved-model",
        },
    )
    assert model_response.status_code == 403
    assert model_response.json()["error"]["code"] == "model_forbidden"
    task_response = client.post(
        "/v1/agent/runs",
        headers=auth_headers(),
        json={"domain": "research", "task": "admin.delete", "input": {}},
    )
    assert task_response.status_code == 403
    assert task_response.json()["error"]["code"] == "task_forbidden"


def test_idempotency_replays_only_the_same_payload(tmp_path, monkeypatch):
    service, _ = make_service(tmp_path, monkeypatch, rate_limit=1)
    client = TestClient(create_app(service=service))
    payload = {
        "domain": "research",
        "task": "research.answer.query",
        "input": {"query": "Harness"},
    }
    headers = auth_headers(**{"Idempotency-Key": "customer-operation-1"})
    first = client.post("/v1/agent/runs", headers=headers, json=payload)
    replay = client.post("/v1/agent/runs", headers=headers, json=payload)
    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["request_id"] == first.json()["request_id"]
    assert replay.json()["idempotent_replay"] is True
    conflict = client.post(
        "/v1/agent/runs",
        headers=headers,
        json=dict(payload, input={"query": "different"}),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_conflict"


def test_rate_limit_and_write_approval_fail_closed(tmp_path, monkeypatch):
    rate_service, _ = make_service(tmp_path / "rate", monkeypatch, rate_limit=1)
    rate_client = TestClient(create_app(service=rate_service))
    payload = {
        "domain": "research",
        "task": "research.answer.query",
        "input": {"query": "Harness"},
    }
    assert rate_client.post("/v1/agent/runs", headers=auth_headers(), json=payload).status_code == 200
    limited = rate_client.post("/v1/agent/runs", headers=auth_headers(), json=payload)
    assert limited.status_code == 429
    assert limited.headers["retry-after"]

    approval_service, _ = make_service(tmp_path / "approval", monkeypatch)
    approval_client = TestClient(create_app(service=approval_service))
    blocked = approval_client.post(
        "/v1/agent/runs",
        headers=auth_headers(),
        json={
            "domain": "research",
            "task": "research.report.publish",
            "input": {"target": "external"},
        },
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "approval_required"


def test_monthly_quota_is_enforced(tmp_path, monkeypatch):
    service, _ = make_service(tmp_path, monkeypatch, quota=1)
    client = TestClient(create_app(service=service))
    payload = {
        "domain": "research",
        "task": "research.answer.query",
        "input": {"query": "Harness"},
    }
    assert client.post("/v1/agent/runs", headers=auth_headers(), json=payload).status_code == 200
    exceeded = client.post("/v1/agent/runs", headers=auth_headers(), json=payload)
    assert exceeded.status_code == 429
    assert exceeded.json()["error"]["code"] == "quota_exceeded"


def test_request_schema_rejects_unknown_fields(tmp_path, monkeypatch):
    service, _ = make_service(tmp_path, monkeypatch)
    client = TestClient(create_app(service=service))
    response = client.post(
        "/v1/agent/runs",
        headers=auth_headers(),
        json={
            "domain": "research",
            "task": "research.answer.query",
            "input": {},
            "approvals": ["research.report.publish"],
        },
    )
    assert response.status_code == 422


def test_request_body_limit_is_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv("VAF_MAX_REQUEST_BYTES", "128")
    service, _ = make_service(tmp_path, monkeypatch)
    client = TestClient(create_app(service=service))
    response = client.post(
        "/v1/agent/runs",
        headers=auth_headers(),
        json={
            "domain": "research",
            "task": "research.answer.query",
            "input": {"query": "x" * 256},
        },
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_config_loader_resolves_paths_and_rejects_unknown_provider(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    valid = config_dir / "commercial.yaml"
    valid.write_text(
        """
project_root: ..
database_path: state/usage.sqlite3
providers:
  openai:
    api_key_env: OPENAI_API_KEY
  qwen:
    api_key_env: DASHSCOPE_API_KEY
    base_url_env: DASHSCOPE_BASE_URL
tenants:
  - id: customer-a
    api_key_env: CUSTOMER_KEY
    allowed_domains: [research]
    allowed_tasks: [research.answer.query]
    allowed_providers: [local, openai]
    allowed_models:
      openai: [tier-1, tier-2, tier-3]
    default_models:
      openai: tier-1
""",
        encoding="utf-8",
    )
    loaded = load_commercial_config(valid)
    assert loaded.project_root == tmp_path.resolve()
    assert loaded.database_path == (tmp_path / "state" / "usage.sqlite3").resolve()
    assert loaded.provider_base_url_envs == {"qwen": "DASHSCOPE_BASE_URL"}

    invalid = config_dir / "invalid.yaml"
    invalid.write_text(
        valid.read_text(encoding="utf-8").replace(
            "allowed_providers: [local, openai]",
            "allowed_providers: [local, unknown-vendor]",
        ),
        encoding="utf-8",
    )
    with pytest.raises(CommercialConfigError):
        load_commercial_config(invalid)


def test_commercial_example_uses_at_most_three_ordered_model_tiers():
    config_path = Path(__file__).parents[1] / "config" / "commercial.example.yaml"
    loaded = load_commercial_config(config_path)
    tenant = loaded.tenants[0]

    for provider in tenant.allowed_providers:
        if provider == "local":
            continue
        models = tenant.allowed_models[provider]
        assert 1 <= len(models) <= 3
        assert len(models) == len(set(models))
        assert tenant.default_models[provider] == models[0]


@pytest.mark.parametrize(
    "models, default_model, error",
    [
        (["one", "two", "three", "four"], "one", "at most three"),
        (["one", "one"], "one", "duplicate"),
        (["one", "two"], "two", "first tier"),
    ],
)
def test_config_rejects_invalid_model_tiers(
    tmp_path, models, default_model, error
):
    config_path = tmp_path / "commercial.yaml"
    rendered_models = ", ".join(models)
    config_path.write_text(
        """
providers:
  openai:
    api_key_env: OPENAI_API_KEY
tenants:
  - id: customer-a
    api_key_env: CUSTOMER_KEY
    allowed_domains: [research]
    allowed_tasks: [research.answer.query]
    allowed_providers: [openai]
    default_provider: openai
    allowed_models:
      openai: [{models}]
    default_models:
      openai: {default_model}
""".format(models=rendered_models, default_model=default_model),
        encoding="utf-8",
    )

    with pytest.raises(CommercialConfigError, match=error):
        load_commercial_config(config_path)


def test_service_rejects_short_customer_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_CUSTOMER_API_KEY", "too-short")
    tenant = TenantConfig(
        tenant_id="customer-a",
        api_key_env="TEST_CUSTOMER_API_KEY",
        allowed_domains=["research"],
        allowed_tasks=["research.answer.query"],
        allowed_providers=["local"],
    )
    config = CommercialConfig(
        project_root=Path(".").resolve(),
        database_path=tmp_path / "usage.sqlite3",
        provider_key_envs={},
        tenants=[tenant],
    )
    with pytest.raises(ValueError, match="at least 32"):
        CommercialService(config)


def setup_payload():
    return {
        "tenant_id": "demo-customer",
        "customer_api_key": "customer-key-that-is-longer-than-32-bytes",
        "allowed_tasks": ["research.answer.query"],
        "providers": [
            {
                "id": "deepseek",
                "api_key": "provider-secret-value",
                "base_url": "",
                "models": ["deepseek-v4-pro", "deepseek-v4-flash"],
            }
        ],
        "default_provider": "deepseek",
        "rate_limit_per_minute": 45,
        "monthly_request_quota": 9000,
    }


def test_setup_converter_separates_yaml_from_secrets():
    converted = convert_setup(setup_payload(), require_secrets=True)
    assert "provider-secret-value" not in converted["yaml"]
    assert "customer-key-that-is-longer-than-32-bytes" not in converted["yaml"]
    assert converted["config"]["providers"]["deepseek"]["api_key_env"] == "DEEPSEEK_API_KEY"
    assert converted["config"]["tenants"][0]["default_models"]["deepseek"] == "deepseek-v4-pro"
    assert converted["secrets"]["DEEPSEEK_API_KEY"] == "provider-secret-value"


def test_setup_converter_rejects_placeholder_models():
    payload = setup_payload()
    payload["providers"][0] = {
        "id": "siliconflow",
        "api_key": "provider-secret-value",
        "models": ["replace-with-siliconflow-top1-model-id"],
    }
    with pytest.raises(SetupValidationError, match="占位模型"):
        convert_setup(payload, require_secrets=True)


def test_no_code_setup_api_previews_and_applies_local_files(tmp_path, monkeypatch):
    setup_key = "setup-administrator-key-longer-than-32-bytes"
    config_path = tmp_path / "config" / "commercial.yaml"
    environment_path = tmp_path / ".env"
    monkeypatch.setenv("VAF_SETUP_ADMIN_KEY", setup_key)
    monkeypatch.setenv("VAF_SETUP_ENV_FILE", str(environment_path))
    client = TestClient(create_app(config_path=config_path))
    headers = {"Authorization": "Bearer {}".format(setup_key)}

    assert client.get("/v1/health").json()["status"] == "setup_required"
    assert client.get("/v1/setup/catalog").status_code == 200
    assert client.get("/v1/setup/status", headers=headers).status_code == 200

    preview = client.post("/v1/setup/preview", headers=headers, json=setup_payload())
    assert preview.status_code == 200
    assert "provider-secret-value" not in preview.text
    assert "api_key_env: DEEPSEEK_API_KEY" in preview.json()["yaml"]

    applied = client.post("/v1/setup/apply", headers=headers, json=setup_payload())
    assert applied.status_code == 200
    assert applied.json()["restart_required"] is True
    assert "provider-secret-value" not in config_path.read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=provider-secret-value" in environment_path.read_text(encoding="utf-8")
    loaded = load_commercial_config(config_path)
    assert loaded.tenants[0].tenant_id == "demo-customer"

    monkeypatch.delenv("VAF_API_KEY_DEMO_CUSTOMER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("VAF_SETUP_ADMIN_KEY", raising=False)
    load_local_environment(environment_path)
    restarted = TestClient(create_app(config_path=config_path))
    assert restarted.get("/v1/health").json()["status"] == "ok"


def test_setup_api_is_hidden_without_an_admin_key(tmp_path, monkeypatch):
    monkeypatch.delenv("VAF_SETUP_ADMIN_KEY", raising=False)
    service, _ = make_service(tmp_path, monkeypatch)
    client = TestClient(create_app(service=service))
    response = client.get("/v1/setup/status")
    assert response.status_code == 404
