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
tenants:
  - id: customer-a
    api_key_env: CUSTOMER_KEY
    allowed_domains: [research]
    allowed_tasks: [research.answer.query]
    allowed_providers: [local, openai]
""",
        encoding="utf-8",
    )
    loaded = load_commercial_config(valid)
    assert loaded.project_root == tmp_path.resolve()
    assert loaded.database_path == (tmp_path / "state" / "usage.sqlite3").resolve()

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
