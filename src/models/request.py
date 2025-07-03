"""FOIA Request data model for managing multiple concurrent requests.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4


@dataclass
class FOIARequest:
    """Represents a single FOIA request being processed"""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    foia_request_text: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    deadline: datetime | None = None
    status: str = "draft"  # draft, processing, review, complete

    # Statistics
    total_documents: int = 0
    processed_documents: int = 0
    responsive_count: int = 0
    non_responsive_count: int = 0
    uncertain_count: int = 0

    # Document associations (in-memory only)
    document_folder: Path | None = None
    processed_document_ids: set[str] = field(default_factory=set)
    reviewed_document_ids: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Validate request data after initialization"""
        if self.status not in ["draft", "processing", "review", "complete"]:
            raise ValueError(f"Invalid status: {self.status}")

    def update_statistics(self) -> None:
        """Update derived statistics based on document counts"""
        self.total_documents = len(self.processed_document_ids)

    def get_progress_percentage(self) -> float:
        """Calculate overall progress percentage"""
        if self.total_documents == 0:
            return 0.0

        reviewed = len(self.reviewed_document_ids)
        return (reviewed / self.total_documents) * 100

    def get_summary(self) -> dict:
        """Get summary statistics for the request"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "total_documents": self.total_documents,
            "processed": self.processed_documents,
            "reviewed": len(self.reviewed_document_ids),
            "responsive": self.responsive_count,
            "non_responsive": self.non_responsive_count,
            "uncertain": self.uncertain_count,
            "progress": self.get_progress_percentage(),
        }
