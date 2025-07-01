"""Standardized error handling utilities for the FOIA Response Assistant."""

from typing import Any


def create_error_response(
    error: Exception | str,
    classification: str | None = "uncertain",
    confidence: float = 0.0,
) -> dict[str, Any]:
    """Create a standardized error response for LangGraph nodes.

    Args:
        error: The error that occurred
        classification: Default classification for errors
        confidence: Default confidence for errors

    Returns:
        Dictionary with error information and safe defaults

    """
    error_message = str(error) if isinstance(error, Exception) else error

    return {
        "error": error_message,
        "classification": classification,
        "confidence": confidence,
        "justification": f"Error during processing: {error_message}",
    }


def check_state_for_errors(state: dict[str, Any]) -> bool:
    """Check if a state contains errors.

    Args:
        state: The document state to check

    Returns:
        True if state contains errors, False otherwise

    """
    return bool(state.get("error"))
