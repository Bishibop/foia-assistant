"""FOIA Response Assistant - AI-powered document classification for FOIA requests."""

from .config import EXEMPTION_CODES, MODEL_CONFIG
from .exceptions import (
    ClassificationError,
    DocumentLoadError,
    ExemptionDetectionError,
    FOIAError,
    ValidationError,
    WorkflowError,
)

__version__ = "0.1.0"
__all__ = [
    "EXEMPTION_CODES",
    "MODEL_CONFIG",
    "ClassificationError",
    "DocumentLoadError",
    "ExemptionDetectionError",
    "FOIAError",
    "ValidationError",
    "WorkflowError",
]
