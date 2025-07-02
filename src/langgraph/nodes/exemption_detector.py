import logging
from typing import Any

from ...config import EMAIL_PATTERN, GOVERNMENT_DOMAINS, PHONE_PATTERNS, SSN_PATTERN
from ..state import DocumentState

logger = logging.getLogger(__name__)


def detect_exemptions(state: DocumentState) -> dict[str, list[dict[str, Any]]]:
    """Detect potential PII exemptions in the document.
    
    This function scans document content for various types of personally identifiable
    information (PII) that may need to be redacted under FOIA exemptions, including:
    - Social Security Numbers (SSNs)
    - Phone numbers (US formats)
    - Email addresses (excluding government domains)
    
    The function logs warnings for unusually long matches and provides detailed
    logging for debugging purposes.
    
    Args:
        state: Document state containing filename, classification, and content
        
    Returns:
        Dictionary with 'exemptions' key containing a list of detected exemptions.
        Each exemption is a dict with 'type', 'start', 'end', and 'text' keys.
    """
    filename = state.get("filename", "unknown")
    classification = state.get("classification")
    
    # Only process responsive documents
    if classification != "responsive":
        return {"exemptions": []}

    if state.get("error"):
        return {}

    exemptions = []
    content = state.get("content", "")

    # Phone number patterns
    for pattern in PHONE_PATTERNS:
        for match in pattern.finditer(content):
            matched_text = match.group()
            # Log if the match seems unusually long
            if len(matched_text) > 20:
                logger.warning(f"Unusually long phone match in {filename}: '{matched_text}' (length: {len(matched_text)})")
            exemptions.append(
                {
                    "text": matched_text,
                    "type": "phone",
                    "exemption_code": "b6",
                    "start": match.start(),
                    "end": match.end(),
                    "description": "Personal phone number",
                }
            )

    # SSN pattern
    for match in SSN_PATTERN.finditer(content):
        matched_text = match.group()
        if len(matched_text) > 20:
            logger.warning(f"Unusually long SSN match in {filename}: '{matched_text}' (length: {len(matched_text)})")
        exemptions.append(
            {
                "text": matched_text,
                "type": "ssn",
                "exemption_code": "b6",
                "start": match.start(),
                "end": match.end(),
                "description": "Social Security Number",
            }
        )

    # Email pattern
    for match in EMAIL_PATTERN.finditer(content):
        # Only flag personal emails, not government emails
        email = match.group().lower()
        if not any(domain in email for domain in GOVERNMENT_DOMAINS):
            if len(email) > 50:
                logger.warning(f"Unusually long email match in {filename}: '{email}' (length: {len(email)})")
            exemptions.append(
                {
                    "text": match.group(),
                    "type": "email",
                    "exemption_code": "b6",
                    "start": match.start(),
                    "end": match.end(),
                    "description": "Personal email address",
                }
            )

    # Remove duplicates
    unique_exemptions = []
    seen = set()
    for ex in exemptions:
        key = (ex["text"], ex["start"])
        if key not in seen:
            seen.add(key)
            unique_exemptions.append(ex)

    # Check for overlapping exemptions that might cause highlighting issues
    if unique_exemptions:
        sorted_exemptions = sorted(unique_exemptions, key=lambda x: x["start"])
        for i in range(1, len(sorted_exemptions)):
            prev = sorted_exemptions[i-1]
            curr = sorted_exemptions[i]
            if prev["end"] >= curr["start"]:
                logger.warning(f"Overlapping exemptions in {filename}: {prev['type']} at {prev['start']}-{prev['end']} overlaps with {curr['type']} at {curr['start']}-{curr['end']}")

    return {"exemptions": unique_exemptions}
