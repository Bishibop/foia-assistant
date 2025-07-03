"""Audit trail data models for FOIA document processing.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AuditEntry:
    """Represents a single audit log entry."""

    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str = ""
    document_filename: str | None = None
    event_type: str = ""  # "classify", "review", "view", "export", "error"
    details: str = ""
    ai_result: str | None = None
    user_decision: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for CSV export.
        
        Returns:
            Dictionary with all fields formatted for export

        """
        return {
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'request_id': self.request_id,
            'document': self.document_filename or '',
            'event': self.event_type,
            'details': self.details,
            'ai_result': self.ai_result or '',
            'user_decision': self.user_decision or ''
        }
