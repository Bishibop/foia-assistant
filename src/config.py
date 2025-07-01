"""Configuration settings for FOIA Response Assistant."""

import re
from re import Pattern

# Model configuration
MODEL_CONFIG: dict[str, str | float | int] = {
    "classification_model": "gpt-4o-mini",
    "temperature": 0.1,
    "max_tokens": 1000,
}

# FOIA exemption codes and descriptions
EXEMPTION_CODES = {
    "b1": "Classified information",
    "b2": "Internal agency rules",
    "b3": "Information prohibited by other laws",
    "b4": "Trade secrets",
    "b5": "Inter-agency memorandums",
    "b6": "Personal privacy",
    "b7": "Law enforcement",
    "b8": "Financial institutions",
    "b9": "Geological information",
}

# PII detection patterns
PHONE_PATTERNS: list[Pattern] = [
    re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),  # 555-123-4567 or 555.123.4567
    re.compile(r"\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b"),  # (555) 123-4567
]

SSN_PATTERN: Pattern = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

EMAIL_PATTERN: Pattern = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# Government email domains to exclude from PII
GOVERNMENT_DOMAINS = ["@agency.gov", "@state.gov", "@federal.gov", ".gov"]

# Classification thresholds
CONFIDENCE_THRESHOLD = 0.7  # Below this, mark as uncertain

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
