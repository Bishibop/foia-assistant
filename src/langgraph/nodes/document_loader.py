from pathlib import Path

from ...exceptions import DocumentLoadError
from ...utils.error_handling import create_error_response
from ..state import DocumentState


def load_document(state: DocumentState) -> dict:
    """Load document content from file.

    Args:
        state: Document state containing filename

    Returns:
        Dict with content or error

    """
    # If content is already provided, just return empty dict (no update needed)
    if state.get("content"):
        return {}

    try:
        filename = state.get("filename")
        if not filename:
            raise DocumentLoadError("No filename provided")

        filepath = Path(filename)

        if not filepath.exists():
            raise DocumentLoadError(f"File not found: {filepath}")

        if not filepath.is_file():
            raise DocumentLoadError(f"Not a file: {filepath}")

        if filepath.stat().st_size == 0:
            raise DocumentLoadError(f"Empty file: {filepath}")

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            raise DocumentLoadError(f"File contains only whitespace: {filepath}")

        return {"content": content}

    except DocumentLoadError as e:
        return create_error_response(e, classification=None)
    except UnicodeDecodeError:
        return create_error_response(
            f"Unable to decode file (not UTF-8): {filename}", classification=None
        )
    except Exception as e:
        return create_error_response(
            f"Unexpected error loading document: {e!s}", classification=None
        )
