from pathlib import Path

from .errors import ApprovalRequired, AgentFactoryError, PolicyDenied, RuntimeExecutionError
from .loader import load_domain_package
from .policy import PolicyEngine
from .providers import DEFAULT_HANDLERS
from .resolver import CapabilityResolver
from .trace import TraceRecorder
from .validation import validate_package


class AgentRuntime(object):
    def __init__(self, project_root, domain_id, handlers=None, approvals=None, trace_dir=None):
        self.package = load_domain_package(project_root, domain_id)
        report = validate_package(self.package)
        if report.errors:
            raise RuntimeExecutionError(report.format())
        configured_handlers = dict(DEFAULT_HANDLERS)
        configured_handlers.update(handlers or {})
        self.resolver = CapabilityResolver(self.package, configured_handlers)
        self.policy = PolicyEngine(self.package.policies, approvals=approvals)
        self.trace_dir = Path(trace_dir or Path(project_root) / ".runs")

    def run(self, task_id, inputs=None):
        inputs = dict(inputs or {})
        task = self.package.task(task_id)
        workflow = self.package.workflow(task.get("workflow"))
        trace = TraceRecorder(
            self.trace_dir, self.package.domain_id, self.package.agent.get("id")
        )
        state_data = dict(inputs)
        trace.emit("run.started", task_type=task_id)
        trace.emit("domain.loaded", version=self.package.domain.get("version"))
        try:
            current = workflow.get("initial_state")
            terminal = set(workflow.get("terminal", []))
            steps = 0
            while current not in terminal:
                steps += 1
                if steps > self.package.agent.get("runtime", {}).get("max_steps", 20):
                    raise RuntimeExecutionError("Workflow exceeded max_steps")
                state = workflow.get("states", {}).get(current)
                if state is None:
                    raise RuntimeExecutionError("Unknown workflow state: {}".format(current))
                action = state.get("action") or {}
                try:
                    if action.get("skill"):
                        self._execute_skill(action["skill"], task, state_data, trace)
                    next_state = state.get("next")
                    if not next_state:
                        raise RuntimeExecutionError(
                            "State {} has no next transition".format(current)
                        )
                    trace.emit(
                        "workflow.transitioned", from_state=current, to_state=next_state
                    )
                    current = next_state
                except AgentFactoryError:
                    failure = state.get("on_failure")
                    if failure:
                        trace.emit(
                            "workflow.transitioned",
                            status="failed",
                            from_state=current,
                            to_state=failure,
                        )
                    raise
            result = state_data.get("result") or {
                "status": "SUCCESS",
                "summary": "Workflow completed.",
                "facts": [],
                "inferences": [],
                "evidence": [],
                "actions": [],
                "warnings": [],
                "uncertainties": [],
                "metadata": {},
            }
            result.setdefault("metadata", {}).update(
                {
                    "run_id": trace.run_id,
                    "trace_id": trace.trace_id,
                    "domain_version": self.package.domain.get("version"),
                    "agent_version": self.package.agent.get("version"),
                }
            )
            trace.emit("run.completed", result_status=result.get("status"))
            return result
        except Exception as exc:
            trace.emit("run.failed", status="failed", error=type(exc).__name__)
            raise

    def _execute_skill(self, skill_id, task, state_data, trace):
        skill = self.package.skill(skill_id)
        if task.get("id") not in skill.get("task_types", []):
            raise RuntimeExecutionError(
                "Skill {} does not allow task {}".format(skill_id, task.get("id"))
            )
        trace.emit("skill.selected", skill_id=skill_id, version=skill.get("version"))
        capabilities = skill.get("requires", {}).get("capabilities", [])
        for capability_id in capabilities:
            capability = self.package.capability(capability_id)
            policy_context = {
                "capability": capability_id,
                "risk_class": capability.get("risk", {}).get("class"),
                "side_effect": bool(capability.get("side_effect")),
            }
            try:
                decision = self.policy.decide(policy_context)
            except ApprovalRequired:
                trace.emit(
                    "approval.requested",
                    status="pending",
                    capability=capability_id,
                )
                raise
            except PolicyDenied:
                trace.emit(
                    "policy.denied",
                    status="denied",
                    capability=capability_id,
                )
                raise
            trace.emit(
                "policy.allowed",
                capability=capability_id,
                decision=decision.get("decision"),
                rule=decision.get("rule"),
            )
            binding, handler = self.resolver.resolve(capability_id)
            trace.emit(
                "capability.resolved",
                capability=capability_id,
                binding=binding.get("implementation", {}).get("handler"),
            )
            trace.emit("tool.started", capability=capability_id)
            output = handler(dict(state_data), self.package) or {}
            state_data.update(output)
            trace.emit("tool.completed", capability=capability_id)
