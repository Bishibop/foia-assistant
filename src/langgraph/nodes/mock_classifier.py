"""Mock classifier for testing without OpenAI API key.

This simulates realistic classification based on document content.
"""

from ..state import DocumentState


def mock_classify_document(state: DocumentState) -> dict:
    """Mock classify document for testing."""
    if state.get("error"):
        return {}

    content = state.get("content", "").lower()
    foia_request = state.get("foia_request", "").lower()

    # Extract key terms from FOIA request
    # For "All emails about Project Blue Sky"
    key_terms = []
    if "blue sky" in foia_request:
        key_terms = ["blue sky", "project blue sky"]

    # Check for key terms
    has_key_terms = any(term in content for term in key_terms)

    # Check if it's an email
    is_email = "from:" in content and "to:" in content

    # Classify based on content
    if has_key_terms and is_email:
        classification = "responsive"
        confidence = 0.95
        justification = "This email directly discusses Project Blue Sky. It contains the key terms and is in email format as requested."
    elif has_key_terms and not is_email:
        classification = "responsive"
        confidence = 0.85
        justification = "This document mentions Project Blue Sky but is not an email. Still marking as responsive since it discusses the project."
    elif "sky" in content or "blue" in content:
        classification = "uncertain"
        confidence = 0.60
        justification = "This document mentions 'sky' or 'blue' but doesn't clearly reference 'Project Blue Sky'. Requires human review to determine if it's related."
    else:
        classification = "non_responsive"
        confidence = 0.90
        justification = "This document does not mention Project Blue Sky or related terms. It appears to be about other topics."

    return {
        "classification": classification,
        "confidence": confidence,
        "justification": justification,
    }
