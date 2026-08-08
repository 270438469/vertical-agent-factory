import json
from collections import Counter

import pytest

from vertical_agent_factory.cli import main
from vertical_agent_factory.errors import PolicyDenied, RuntimeExecutionError
from vertical_agent_factory.evals import run_evals
from vertical_agent_factory.loader import load_domain_package
from vertical_agent_factory.policy import PolicyEngine
from vertical_agent_factory.providers import DEFAULT_HANDLERS
from vertical_agent_factory.resolver import CapabilityResolver
from vertical_agent_factory.runtime import AgentRuntime
from vertical_agent_factory.validation import validate_package


def test_golden_eval_taxonomy_is_complete():
    package = load_domain_package(".", "research")
    categories = Counter(case["category"] for case in package.evals)
    assert categories == {
        "happy_path": 5,
        "edge_case": 5,
        "ambiguous": 5,
        "tool_failure": 5,
        "policy_boundary": 5,
        "adversarial": 5,
    }


def test_all_golden_evals_pass():
    results = run_evals(".", "research")
    assert len(results) == 30
    assert all(item["passed"] for item in results)


def test_validation_detects_missing_binding():
    package = load_domain_package(".", "research")
    package.bindings = [
        binding for binding in package.bindings
        if binding["capability"] != "research.evidence.search"
    ]
    report = validate_package(package)
    assert not report.passed
    assert any("has no binding" in error for error in report.errors)


def test_validation_detects_unprotected_high_risk_capability():
    package = load_domain_package(".", "research")
    package.policies = [{"rules": [package.policies[0]["rules"][0]]}]
    report = validate_package(package)
    assert not report.passed
    assert any("High-risk capability" in error for error in report.errors)


def test_resolver_rejects_unhealthy_provider():
    package = load_domain_package(".", "research")
    for binding in package.bindings:
        if binding["capability"] == "research.evidence.search":
            binding["health"] = "unhealthy"
    resolver = CapabilityResolver(package, DEFAULT_HANDLERS)
    with pytest.raises(RuntimeExecutionError):
        resolver.resolve("research.evidence.search")


def test_policy_fails_closed_for_unknown_risk():
    package = load_domain_package(".", "research")
    engine = PolicyEngine(package.policies)
    with pytest.raises(PolicyDenied):
        engine.decide({"capability": "unknown", "risk_class": "PRIVILEGED", "side_effect": True})


def test_provider_failure_is_traced(tmp_path):
    runtime = AgentRuntime(".", "research", trace_dir=tmp_path)
    with pytest.raises(RuntimeExecutionError):
        runtime.run("research.answer.query", {"query": "Harness", "simulate_failure": True})
    trace = [json.loads(line) for line in next(tmp_path.glob("*.jsonl")).read_text().splitlines()]
    assert trace[-1]["event_type"] == "run.failed"
    assert trace[-1]["error"] == "RuntimeExecutionError"


def test_result_matches_declared_contract(tmp_path):
    runtime = AgentRuntime(".", "research", trace_dir=tmp_path)
    result = runtime.run("research.answer.query", {"query": "Capability Binding"})
    schema = json.loads((runtime.package.domain_root / "schemas" / "result.json").read_text())
    assert set(schema["required"]) == set(result)
    assert schema["additionalProperties"] is False


def test_cli_validate_and_approval_boundary(capsys):
    assert main(["--root", ".", "validate", "--domain", "research"]) == 0
    assert main([
        "--root", ".", "run", "--domain", "research",
        "--task", "research.report.publish", "--input", "target=demo",
    ]) == 3
    output = capsys.readouterr().out
    assert "APPROVAL_REQUIRED" in output
