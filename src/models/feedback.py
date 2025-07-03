"""Feedback data models for learning from user corrections."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FeedbackEntry:
    """Represents a single user correction to an AI classification."""

    document_id: str
    request_id: str
    original_classification: str
    human_decision: str
    original_confidence: float
    timestamp: datetime = field(default_factory=datetime.now)

    # Optional document snippet for context in prompts
    document_snippet: str = ""
    
    # Optional correction reason for better guidance
    correction_reason: str = ""
