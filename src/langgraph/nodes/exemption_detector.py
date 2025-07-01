from ...config import EMAIL_PATTERN, GOVERNMENT_DOMAINS, PHONE_PATTERNS, SSN_PATTERN
from ..state import DocumentState


def detect_exemptions(state: DocumentState) -> dict:
    """Detect potential PII exemptions in the document."""
    # Only process responsive documents
    if state.get("classification") != "responsive":
        return {"exemptions": []}

    if state.get("error"):
        return {}

    exemptions = []
    content = state.get("content", "")

    # Phone number patterns
    for pattern in PHONE_PATTERNS:
        for match in pattern.finditer(content):
            exemptions.append(
                {
                    "text": match.group(),
                    "type": "phone",
                    "exemption_code": "b6",
                    "start": match.start(),
                    "end": match.end(),
                    "description": "Personal phone number",
                }
            )

    # SSN pattern
    for match in SSN_PATTERN.finditer(content):
        exemptions.append(
            {
                "text": match.group(),
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

    return {"exemptions": unique_exemptions}
