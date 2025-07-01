from dataclasses import dataclass
from typing import Any


@dataclass
class Document:
    """Represents a document being processed for FOIA review."""

    filename: str
    content: str
    classification: str | None = None  # "responsive", "non_responsive", "uncertain"
    confidence: float | None = None
    justification: str | None = None
    exemptions: list[dict[str, Any]] | None = None
    human_decision: str | None = None
    human_feedback: str | None = None

    def __post_init__(self) -> None:
        if self.exemptions is None:
            self.exemptions = []

    def add_exemption(
        self, text: str, exemption_type: str, start: int, end: int
    ) -> None:
        """Add an exemption to the document."""
        if self.exemptions is None:
            self.exemptions = []
        self.exemptions.append(
            {"text": text, "type": exemption_type, "start": start, "end": end}
        )

    def to_dict(self) -> dict:
        """Convert document to dictionary for serialization."""
        return {
            "filename": self.filename,
            "classification": self.classification,
            "confidence": self.confidence,
            "justification": self.justification,
            "exemptions": self.exemptions,
            "human_decision": self.human_decision,
            "human_feedback": self.human_feedback,
        }
