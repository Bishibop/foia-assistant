from typing import TypedDict


class DocumentState(TypedDict):
    """State that flows through the LangGraph workflow."""

    # Input fields
    filename: str
    content: str
    foia_request: str

    # Classification results
    classification: str | None  # "responsive", "non_responsive", "uncertain"
    confidence: float | None
    justification: str | None

    # Exemptions
    exemptions: list[dict] | None

    # Human feedback (for learning)
    human_decision: str | None
    human_feedback: str | None

    # Learning
    patterns_learned: list[str] | None

    # Workflow control
    error: str | None
