import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCharFormat, QTextCursor
from PyQt6.QtWidgets import QTextEdit, QVBoxLayout, QWidget

from src.constants import DOCUMENT_FONT_SIZE, MONOSPACE_FONT_STACK, SEPARATOR_LENGTH

logger = logging.getLogger(__name__)


class DocumentViewer(QWidget):
    """Widget for displaying document content with exemption highlighting."""

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()
        self._exemptions: list[dict] = []

    def _init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self._text_display = QTextEdit()
        self._text_display.setReadOnly(True)
        # Use first font from the stack
        font_family = MONOSPACE_FONT_STACK.split(",")[0].strip("'")
        self._text_display.setFont(QFont(font_family, DOCUMENT_FONT_SIZE))
        layout.addWidget(self._text_display)

        self.setLayout(layout)

    def display_document(
        self, filename: str, content: str, exemptions: list[dict] | None = None
    ) -> None:
        """Display a document with optional exemption highlighting."""
        self._exemptions = exemptions or []

        # Clear and reset formatting
        self._text_display.clear()
        self._text_display.setCurrentCharFormat(
            QTextCharFormat()
        )  # Reset to default format

        # Check if a large portion of the document is being highlighted
        if self._exemptions:
            total_highlighted_chars = sum(
                ex["end"] - ex["start"] for ex in self._exemptions
            )
            if total_highlighted_chars > len(content) * 0.5:
                logger.warning(
                    f"More than 50% of {filename} will be highlighted ({total_highlighted_chars}/{len(content)} chars)"
                )

        # Set document header with default format
        default_format = QTextCharFormat()
        cursor = self._text_display.textCursor()
        cursor.setCharFormat(default_format)
        cursor.insertText(f"File: {filename}\n")
        cursor.insertText("-" * SEPARATOR_LENGTH + "\n")

        # Insert document content with default format
        content_start = cursor.position()
        cursor.insertText(content)

        # Highlight exemptions if any
        if self._exemptions:
            self._highlight_exemptions(content_start)

    def _highlight_exemptions(self, content_start: int) -> None:
        cursor = self._text_display.textCursor()

        # Create highlight format
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(Qt.GlobalColor.yellow)
        highlight_format.setToolTip("PII - Exemption b6")

        for i, exemption in enumerate(self._exemptions):
            try:
                # Validate exemption structure
                if not isinstance(exemption, dict):
                    logger.warning(
                        f"Exemption {i} is not a dictionary: {type(exemption)}"
                    )
                    continue

                if not all(key in exemption for key in ["start", "end", "type"]):
                    logger.warning(
                        f"Exemption {i} missing required keys: {exemption.keys()}"
                    )
                    continue

                # Calculate positions
                start_pos = content_start + exemption["start"]
                end_pos = content_start + exemption["end"]

                # Validate positions
                if exemption["start"] < 0 or exemption["end"] < 0:
                    logger.warning(
                        f"Exemption {i} has negative position: start={exemption['start']}, end={exemption['end']}"
                    )
                    continue

                if exemption["start"] >= exemption["end"]:
                    logger.warning(
                        f"Exemption {i} has invalid range: start={exemption['start']}, end={exemption['end']}"
                    )
                    continue

                # Log unusual positions
                doc_length = self._text_display.document().characterCount()
                if end_pos > doc_length:
                    logger.warning(
                        f"Exemption {i} end position {end_pos} exceeds document length {doc_length}"
                    )
                    continue

                # Move to the exemption position (adjusted for header)
                cursor.setPosition(start_pos)
                cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
                cursor.setCharFormat(highlight_format)

            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Error processing exemption {i}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error highlighting exemption {i}: {e}")

    def clear(self) -> None:
        """Clear the document viewer."""
        self._text_display.clear()
        self._exemptions = []
