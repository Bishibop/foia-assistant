from dataclasses import dataclass
from typing import Any


@dataclass
class Document:
    """Represents a document being processed for FOIA review."""

    filename: str
    content: str
    classification: str | None = None  # "responsive", "non_responsive", "uncertain", "duplicate"
    confidence: float | None = None
    justification: str | None = None
    exemptions: list[dict[str, Any]] | None = None
    human_decision: str | None = None
    human_feedback: str | None = None

    # Duplicate detection fields
    is_duplicate: bool = False
    duplicate_of: str | None = None
    similarity_score: float | None = None
    content_hash: str | None = None
    embedding_generated: bool = False

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
            "is_duplicate": self.is_duplicate,
            "duplicate_of": self.duplicate_of,
            "similarity_score": self.similarity_score,
            "content_hash": self.content_hash,
            "embedding_generated": self.embedding_generated,
        }
