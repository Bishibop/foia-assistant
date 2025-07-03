from typing import TypedDict


class DocumentState(TypedDict):
    """State that flows through the LangGraph workflow."""

    # Input fields
    filename: str
    content: str
    foia_request: str

    # Duplicate detection fields
    is_duplicate: bool | None
    duplicate_of: str | None
    similarity_score: float | None
    content_hash: str | None
    embedding_generated: bool | None

    # Classification results
    classification: str | None  # "responsive", "non_responsive", "uncertain", "duplicate"
    confidence: float | None
    justification: str | None

    # Exemptions
    exemptions: list[dict] | None

    # Human feedback (for learning)
    human_decision: str | None
    human_feedback: str | None

    # Learning
    patterns_learned: list[str] | None
    feedback_examples: list[dict] | None  # List of previous corrections for few-shot learning

    # Workflow control
    error: str | None
