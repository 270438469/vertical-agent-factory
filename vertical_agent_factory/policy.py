from .errors import ApprovalRequired, PolicyDenied


def _matches(conditions, context):
    for key, expected in (conditions or {}).items():
        if context.get(key) != expected:
            return False
    return True


class PolicyEngine(object):
    def __init__(self, policy_documents, approvals=None):
        self.rules = []
        for document in policy_documents:
            self.rules.extend(document.get("rules", []))
        self.approvals = approvals or {}

    def decide(self, context):
        decision = "deny"
        matched_rule = None
        for rule in self.rules:
            if _matches(rule.get("when"), context):
                decision = rule.get("decision", "deny")
                matched_rule = rule.get("id")
        if decision == "deny":
            raise PolicyDenied(
                "Policy denied capability {}".format(context.get("capability"))
            )
        if decision == "approval_required":
            capability = context.get("capability")
            if not self.approvals.get(capability, False):
                raise ApprovalRequired(capability)
        return {"decision": decision, "rule": matched_rule}
