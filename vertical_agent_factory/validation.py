from pathlib import Path


class ValidationReport(object):
    def __init__(self):
        self.errors = []
        self.warnings = []

    @property
    def passed(self):
        return not self.errors

    def error(self, message):
        self.errors.append(message)

    def warn(self, message):
        self.warnings.append(message)

    def format(self):
        lines = ["PASS" if self.passed else "FAIL"]
        lines.extend("ERROR: {}".format(item) for item in self.errors)
        lines.extend("WARN: {}".format(item) for item in self.warnings)
        return "\n".join(lines)


def validate_package(package):
    report = ValidationReport()
    if package.domain.get("id") != package.domain_id:
        report.error("domain.yaml id does not match directory")
    if not package.domain.get("version"):
        report.error("domain version is required")
    task_ids = {item.get("id") for item in package.tasks}
    skill_ids = {item.get("id") for item in package.skills}
    capability_ids = {item.get("id") for item in package.capabilities}
    workflow_ids = {item.get("id") for item in package.workflows}
    binding_capabilities = {item.get("capability") for item in package.bindings}
    agent_skills = set(package.agent.get("skills", {}).get("allow", []))
    agent_capabilities = set(package.agent.get("capabilities", {}).get("allow", []))
    policy_rules = []
    for policy in package.policies:
        policy_rules.extend(policy.get("rules", []))

    for skill_id in agent_skills:
        if skill_id not in skill_ids and not skill_id.startswith("core."):
            report.error("Agent references unknown skill {}".format(skill_id))
    for task in package.tasks:
        task_id = task.get("id")
        if not task_id:
            report.error("Task without id")
            continue
        if task.get("workflow") not in workflow_ids:
            report.error("Task {} references unknown workflow".format(task_id))
        for capability_id in task.get("required_capabilities", []):
            if capability_id not in capability_ids:
                report.error(
                    "Task {} references unknown capability {}".format(task_id, capability_id)
                )
            elif capability_id not in agent_capabilities:
                report.error(
                    "Task {} requires capability {} not allowed by Agent".format(
                        task_id, capability_id
                    )
                )
        if task.get("side_effect") and not task.get("risk"):
            report.error("Write task {} has no risk classification".format(task_id))
    for skill in package.skills:
        skill_id = skill.get("id")
        skill_path = Path(skill.get("_path", ""))
        if not (skill_path / "SKILL.md").exists():
            report.error("Skill {} has no SKILL.md".format(skill_id))
        if not skill.get("version"):
            report.error("Skill {} has no version".format(skill_id))
        for task_id in skill.get("task_types", []):
            if task_id not in task_ids:
                report.error("Skill {} references unknown task {}".format(skill_id, task_id))
        for capability_id in skill.get("requires", {}).get("capabilities", []):
            if capability_id not in capability_ids:
                report.error(
                    "Skill {} references unknown capability {}".format(
                        skill_id, capability_id
                    )
                )
            elif capability_id not in binding_capabilities:
                report.error("Capability {} has no binding".format(capability_id))
    for workflow in package.workflows:
        states = workflow.get("states", {})
        initial = workflow.get("initial_state")
        terminal = set(workflow.get("terminal", []))
        if initial not in states and initial not in terminal:
            report.error("Workflow {} has invalid initial state".format(workflow.get("id")))
        if not terminal:
            report.error("Workflow {} has no terminal state".format(workflow.get("id")))
        for state_name, state in states.items():
            skill_id = (state.get("action") or {}).get("skill")
            if skill_id and skill_id not in skill_ids:
                report.error(
                    "Workflow {} state {} references unknown skill {}".format(
                        workflow.get("id"), state_name, skill_id
                    )
                )
            if state.get("next") not in states and state.get("next") not in terminal:
                report.error(
                    "Workflow {} state {} has invalid next state".format(
                        workflow.get("id"), state_name
                    )
                )
            if not state.get("on_failure"):
                report.warn(
                    "Workflow {} state {} has no explicit failure target".format(
                        workflow.get("id"), state_name
                    )
                )
    for capability in package.capabilities:
        if capability.get("side_effect") and capability.get("risk", {}).get("level") == "high":
            risk_class = capability.get("risk", {}).get("class")
            protected = any(
                rule.get("when", {}).get("risk_class") == risk_class
                and rule.get("decision") in ("approval_required", "deny")
                for rule in policy_rules
            )
            if not protected:
                report.error(
                    "High-risk capability {} has no approval or deny policy".format(
                        capability.get("id")
                    )
                )
    schema = package.domain_root / "schemas" / "result.json"
    if not schema.exists():
        report.error("Missing result schema")
    if len(package.evals) < 30:
        report.warn("Fewer than 30 eval cases")
    return report
