from .errors import ApprovalRequired, AgentFactoryError
from .runtime import AgentRuntime


def run_evals(project_root, domain_id):
    probe = AgentRuntime(project_root, domain_id)
    cases = probe.package.evals
    results = []
    for case in cases:
        expected = case.get("expect", {}).get("status", "SUCCESS")
        try:
            runtime = AgentRuntime(project_root, domain_id)
            output = runtime.run(case.get("task_type"), case.get("input", {}))
            actual = output.get("status")
        except ApprovalRequired:
            actual = "APPROVAL_REQUIRED"
        except AgentFactoryError:
            actual = "ERROR"
        results.append(
            {
                "id": case.get("id"),
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )
    return results
