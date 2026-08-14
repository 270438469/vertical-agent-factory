import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from vertical_agent_factory.channels.wechat import (
    DISCLAIMER,
    parse_wechat_message,
    route_finance_text,
    verify_wechat_signature,
)
from vertical_agent_factory.commercial.app import create_app
from vertical_agent_factory.commercial.config import CommercialConfig, TenantConfig
from vertical_agent_factory.commercial.service import CommercialService


TOKEN = "wechat-callback-token-long-enough"
CUSTOMER_KEY = "customer-api-key-longer-than-thirty-two-bytes"


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("WECHAT_OFFICIAL_ACCOUNT_TOKEN", TOKEN)
    monkeypatch.setenv("VAF_WECHAT_TENANT_ID", "finance-customer")
    monkeypatch.setenv("VAF_WECHAT_FINANCE_DATA_MODE", "fixture")
    monkeypatch.setenv("FINANCE_CUSTOMER_KEY", CUSTOMER_KEY)
    tenant = TenantConfig(
        tenant_id="finance-customer",
        api_key_env="FINANCE_CUSTOMER_KEY",
        allowed_domains=["finance"],
        allowed_tasks=[
            "finance.macro.analyze",
            "finance.a_share.analyze",
            "finance.us_stock.analyze",
        ],
        allowed_providers=["local"],
        default_provider="local",
    )
    config = CommercialConfig(
        project_root=Path(".").resolve(),
        database_path=tmp_path / "usage.sqlite3",
        provider_key_envs={},
        tenants=[tenant],
    )
    return TestClient(create_app(service=CommercialService(config)))


def signed_query(timestamp="1723600000", nonce="nonce-1"):
    signature = hashlib.sha1("".join(sorted([TOKEN, timestamp, nonce])).encode("utf-8")).hexdigest()
    return "signature={}&timestamp={}&nonce={}".format(signature, timestamp, nonce)


def text_message(content="A股 600000", msg_id="123456789"):
    return (
        "<xml>"
        "<ToUserName>official-account</ToUserName>"
        "<FromUserName>openid-user</FromUserName>"
        "<CreateTime>1723600000</CreateTime>"
        "<MsgType>text</MsgType>"
        "<Content>{}</Content>"
        "<MsgId>{}</MsgId>"
        "</xml>"
    ).format(content, msg_id)


def test_wechat_signature_and_intent_routing():
    assert verify_wechat_signature(TOKEN, signed_query().split("&")[0].split("=")[1], "1723600000", "nonce-1")
    assert route_finance_text("宏观 中国")["input"]["region"] == "china"
    assert route_finance_text("A股 600000")["task"] == "finance.a_share.analyze"
    assert route_finance_text("美股 aapl")["input"]["symbol"] == "AAPL"
    assert route_finance_text("帮助") is None


def test_wechat_server_verification_returns_echostr(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.get("/v1/channels/wechat/official-account?{}&echostr=verified".format(signed_query()))
    assert response.status_code == 200
    assert response.text == "verified"


def test_wechat_text_message_runs_finance_agent_and_returns_xml(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    response = client.post(
        "/v1/channels/wechat/official-account?{}".format(signed_query()),
        content=text_message().encode("utf-8"),
        headers={"Content-Type": "application/xml"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    parsed = parse_wechat_message(response.content)
    assert parsed["ToUserName"] == "openid-user"
    assert parsed["FromUserName"] == "official-account"
    assert "600000.SH" in parsed["Content"]
    assert DISCLAIMER in parsed["Content"]


def test_wechat_duplicate_message_is_idempotent(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    url = "/v1/channels/wechat/official-account?{}".format(signed_query())
    first = client.post(url, content=text_message(msg_id="same-id"))
    second = client.post(url, content=text_message(msg_id="same-id"))
    assert first.status_code == second.status_code == 200
    assert "600000.SH" in second.text


def test_wechat_rejects_invalid_signature_and_dtd(tmp_path, monkeypatch):
    client = make_client(tmp_path, monkeypatch)
    invalid = client.post(
        "/v1/channels/wechat/official-account?signature=bad&timestamp=1&nonce=2",
        content=text_message(),
    )
    assert invalid.status_code == 403
    malicious = "<!DOCTYPE xml [<!ENTITY x 'boom'>]>" + text_message("&x;")
    rejected = client.post(
        "/v1/channels/wechat/official-account?{}".format(signed_query()),
        content=malicious,
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "invalid_wechat_message"
