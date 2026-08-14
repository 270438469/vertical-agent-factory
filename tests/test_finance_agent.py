import math
from collections import Counter

import pytest

from vertical_agent_factory import AgentRuntime, ApprovalRequired, load_domain_package
from vertical_agent_factory.evals import run_evals
from vertical_agent_factory.finance_data import (
    DISCLAIMER,
    FinanceDataGateway,
    normalize_a_share_symbol,
    normalize_us_symbol,
)
from vertical_agent_factory.validation import validate_package


def test_finance_domain_package_and_golden_evals_are_complete(monkeypatch):
    monkeypatch.setenv("VAF_FINANCE_DATA_MODE", "fixture")
    package = load_domain_package(".", "finance")
    report = validate_package(package)
    assert report.passed, report.format()
    categories = Counter(case["category"] for case in package.evals)
    assert categories == {
        "happy_path": 5,
        "edge_case": 5,
        "ambiguous": 5,
        "tool_failure": 5,
        "policy_boundary": 5,
        "adversarial": 5,
    }
    results = run_evals(".", "finance")
    assert len(results) == 30
    assert all(item["passed"] for item in results)


@pytest.mark.parametrize(
    "task,payload",
    [
        ("finance.macro.analyze", {"region": "global"}),
        ("finance.a_share.analyze", {"symbol": "600000"}),
        ("finance.us_stock.analyze", {"symbol": "AAPL"}),
    ],
)
def test_finance_analysis_is_dated_evidenced_and_disclaimed(tmp_path, monkeypatch, task, payload):
    monkeypatch.setenv("VAF_FINANCE_DATA_MODE", "fixture")
    result = AgentRuntime(".", "finance", trace_dir=tmp_path).run(task, payload)
    assert result["status"] == "SUCCESS"
    assert result["evidence"]
    assert result["metadata"]["as_of"]
    assert result["metadata"]["validated"] is True
    assert DISCLAIMER in result["warnings"]


def test_equity_analysis_returns_transparent_risk_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("VAF_FINANCE_DATA_MODE", "fixture")
    result = AgentRuntime(".", "finance", trace_dir=tmp_path).run(
        "finance.us_stock.analyze", {"symbol": "MSFT"}
    )
    metrics = result["metadata"]["metrics"]
    assert set(metrics) == {
        "period_return_pct",
        "annualized_volatility_pct",
        "max_drawdown_pct",
    }
    assert math.isfinite(metrics["annualized_volatility_pct"])
    assert result["actions"] == []


def test_unknown_symbol_withholds_financial_analysis(tmp_path, monkeypatch):
    monkeypatch.setenv("VAF_FINANCE_DATA_MODE", "fixture")
    result = AgentRuntime(".", "finance", trace_dir=tmp_path).run(
        "finance.us_stock.analyze", {"symbol": "UNKNOWN"}
    )
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["facts"] == []
    assert DISCLAIMER in result["warnings"]


def test_finance_publication_requires_explicit_approval(tmp_path):
    runtime = AgentRuntime(".", "finance", trace_dir=tmp_path)
    with pytest.raises(ApprovalRequired):
        runtime.run("finance.briefing.publish", {"channel": "wechat"})


def test_symbol_normalization_is_bounded():
    assert normalize_a_share_symbol("600000") == "600000.SH"
    assert normalize_a_share_symbol("000001") == "000001.SZ"
    assert normalize_a_share_symbol("830001") == "830001.BJ"
    assert normalize_a_share_symbol("../../.env") == ""
    assert normalize_us_symbol("aapl") == "AAPL"
    assert normalize_us_symbol("AAPL&apikey=x") == ""


class FakeFinanceTransport(object):
    def post_json(self, url, payload):
        assert url == "https://api.tushare.pro"
        assert payload["api_name"] == "daily"
        assert payload["token"] == "tushare-test-token"
        return {
            "code": 0,
            "msg": None,
            "data": {
                "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount"],
                "items": [
                    ["600000.SH", "20260814", 10.0, 10.4, 9.9, 10.3, 1000, 10000],
                    ["600000.SH", "20260813", 9.9, 10.1, 9.8, 10.0, 900, 9000],
                ],
            },
        }

    def get_json(self, url, params):
        assert url == "https://www.alphavantage.co/query"
        assert params["function"] == "TIME_SERIES_DAILY"
        assert params["apikey"] == "alpha-test-key"
        return {
            "Time Series (Daily)": {
                "2026-08-14": {"1. open": "230", "2. high": "235", "3. low": "229", "4. close": "234", "5. volume": "100000"},
                "2026-08-13": {"1. open": "228", "2. high": "232", "3. low": "227", "4. close": "231", "5. volume": "90000"},
            }
        }


def test_live_finance_adapters_use_official_bounded_endpoints(monkeypatch):
    transport = FakeFinanceTransport()
    monkeypatch.setenv("TUSHARE_TOKEN", "tushare-test-token")
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "alpha-test-key")
    gateway = FinanceDataGateway(mode="live", transport=transport)
    a_share = gateway.a_share({"symbol": "600000", "lookback_days": 30})
    us_stock = gateway.us_stock({"symbol": "AAPL"})
    assert a_share["as_of"] == "2026-08-14"
    assert us_stock["as_of"] == "2026-08-14"
    assert a_share["points"][-1]["close"] == 10.3
    assert us_stock["points"][-1]["close"] == 234.0
