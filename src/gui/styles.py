"""Centralized styling for the FOIA Response Assistant GUI."""

# Main window styling
MAIN_WINDOW_STYLE = """
    QMainWindow {
        background-color: #f5f5f5;
    }
    QTabWidget::pane {
        border: 1px solid #ddd;
        background-color: white;
    }
    QTabBar::tab {
        padding: 8px 16px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: white;
        border-bottom: 2px solid #0066cc;
    }
    QTabBar::tab:!selected {
        background-color: #f0f0f0;
    }
"""

# Placeholder label styling
PLACEHOLDER_LABEL_STYLE = """
    QLabel {
        padding: 40px;
        background-color: #f0f0f0;
        border: 2px dashed #cccccc;
        border-radius: 5px;
        color: #666666;
        font-size: 16px;
    }
"""

# Activity log styling
ACTIVITY_LOG_STYLE = """
    QTextEdit {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        font-family: {font_family};
        font-size: 12px;
    }
"""

# Title label styling
TITLE_LABEL_STYLE = "font-size: 24px; font-weight: bold; margin-bottom: 20px;"


def create_title_label(text: str):
    """Create a standardized title label."""
    from PyQt6.QtWidgets import QLabel

    from src.constants import TITLE_MAX_HEIGHT

    label = QLabel(text)
    label.setStyleSheet(TITLE_LABEL_STYLE)
    label.setMaximumHeight(TITLE_MAX_HEIGHT)
    return label


# Group box styling helpers
def style_folder_label() -> str:
    """Get styling for folder label input."""
    return "padding: 5px; background-color: #f9f9f9;"


def style_current_doc_label() -> str:
    """Get styling for current document label."""
    return "font-style: italic; color: #666;"


def style_stat_label() -> str:
    """Get styling for statistics labels."""
    return "font-size: 12px; color: #666;"


def style_stat_value(bold: bool = True) -> str:
    """Get styling for statistics values."""
    base = "font-size: 20px;"
    if bold:
        base += " font-weight: bold;"
    return base


def create_styled_button(text: str, style_constant: str):
    """Create a button with specified style."""
    from PyQt6.QtWidgets import QPushButton

    button = QPushButton(text)
    button.setStyleSheet(style_constant)
    return button


def create_primary_button(text: str):
    """Create a primary styled button."""
    from src.constants import BUTTON_STYLE_PRIMARY

    return create_styled_button(text, BUTTON_STYLE_PRIMARY)


def create_secondary_button(text: str):
    """Create a secondary styled button."""
    from src.constants import BUTTON_STYLE_SECONDARY

    return create_styled_button(text, BUTTON_STYLE_SECONDARY)


def create_warning_button(text: str):
    """Create a warning styled button (orange)."""
    from src.constants import BUTTON_STYLE_WARNING

    return create_styled_button(text, BUTTON_STYLE_WARNING)
