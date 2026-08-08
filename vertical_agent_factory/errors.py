class AgentFactoryError(Exception):
    """Base error for the shared harness."""


class PackageValidationError(AgentFactoryError):
    """Raised when a domain package is incomplete or inconsistent."""


class ApprovalRequired(AgentFactoryError):
    """Raised before an operation that requires explicit approval."""

    def __init__(self, capability, message=None):
        self.capability = capability
        super().__init__(message or "Approval required for {}".format(capability))


class PolicyDenied(AgentFactoryError):
    """Raised when policy denies an operation."""


class RuntimeExecutionError(AgentFactoryError):
    """Raised when a workflow or capability execution fails."""
