"""Executable shared harness for Vertical Agent Factory domain packages."""

from .errors import ApprovalRequired, PackageValidationError, RuntimeExecutionError
from .loader import DomainPackage, load_domain_package
from .runtime import AgentRuntime
from .validation import ValidationReport, validate_package

__all__ = [
    "AgentRuntime",
    "ApprovalRequired",
    "DomainPackage",
    "PackageValidationError",
    "RuntimeExecutionError",
    "ValidationReport",
    "load_domain_package",
    "validate_package",
]

__version__ = "0.1.0"
