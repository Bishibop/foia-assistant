"""Custom exceptions for FOIA Response Assistant."""


class FOIAError(Exception):
    """Base exception for FOIA Response Assistant."""

    pass


class DocumentLoadError(FOIAError):
    """Raised when a document cannot be loaded."""

    pass


class ClassificationError(FOIAError):
    """Raised when document classification fails."""

    pass


class ExemptionDetectionError(FOIAError):
    """Raised when exemption detection fails."""

    pass


class WorkflowError(FOIAError):
    """Raised when workflow execution fails."""

    pass


class ValidationError(FOIAError):
    """Raised when input validation fails."""

    pass
