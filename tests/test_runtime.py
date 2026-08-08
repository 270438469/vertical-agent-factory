import json

import pytest

from vertical_agent_factory import AgentRuntime, ApprovalRequired, load_domain_package
from vertical_agent_factory.validation import validate_package


def test_research_package_is_valid():
    report = validate_package(load_domain_package(".", "research"))
    assert report.passed, report.format()
    assert len(load_domain_package(".", "research").evals) == 30


def test_query_returns_evidence_backed_result(tmp_path):
    runtime = AgentRuntime(".", "research", trace_dir=tmp_path)
    result = runtime.run("research.answer.query", {"query": "shared Harness"})
    assert result["status"] == "SUCCESS"
    assert result["evidence"]
    assert result["metadata"]["validated"] is True
    trace_path = next(tmp_path.glob("*.jsonl"))
    events = [json.loads(line)["event_type"] for line in trace_path.read_text().splitlines()]
    assert "capability.resolved" in events
    assert events[-1] == "run.completed"


def test_unknown_query_withholds_answer(tmp_path):
    runtime = AgentRuntime(".", "research", trace_dir=tmp_path)
    result = runtime.run("research.answer.query", {"query": "unrelated weather"})
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["facts"] == []


def test_write_requires_approval(tmp_path):
    runtime = AgentRuntime(".", "research", trace_dir=tmp_path)
    with pytest.raises(ApprovalRequired):
        runtime.run("research.report.publish", {"target": "demo"})
    trace_path = next(tmp_path.glob("*.jsonl"))
    events = [json.loads(line)["event_type"] for line in trace_path.read_text().splitlines()]
    assert "approval.requested" in events
    assert events[-1] == "run.failed"


def test_approved_write_uses_demo_provider(tmp_path):
    runtime = AgentRuntime(
        ".",
        "research",
        approvals={"research.report.publish": True},
        trace_dir=tmp_path,
    )
    result = runtime.run("research.report.publish", {"target": "demo"})
    assert result["status"] == "SUCCESS"
    assert result["actions"][0]["type"] == "publish"
    assert result["metadata"]["simulated"] is True
