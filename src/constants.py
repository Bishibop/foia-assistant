"""Constants used throughout the FOIA Response Assistant application."""

# Window configuration
WINDOW_TITLE = "RAPID RESPONSE AI"
WINDOW_INITIAL_SIZE = (1400, 900)
WINDOW_INITIAL_POSITION = (100, 100)

# Application styling
APP_STYLE = "Fusion"

# Tab names
TAB_REQUESTS = "Requests"
TAB_INTAKE = "Intake"
TAB_REVIEW = "Review"
TAB_FINALIZE = "Finalize"
TAB_AUDIT = "Audit"

# GUI Layout constants
SPLITTER_SIZES = [400, 600]  # 40% config, 60% status
ACTIVITY_LOG_MAX_HEIGHT = 150
ACTIVITY_LOG_DEFAULT_HEIGHT = 150
REQUEST_TEXT_MAX_HEIGHT = 100
REQUEST_TEXT_MIN_HEIGHT = 80
REQUEST_TEXT_DEFAULT_HEIGHT = 100

# UI Element sizing
TITLE_MAX_HEIGHT = 50
STATUS_MESSAGE_MAX_HEIGHT = 30
STATUS_MESSAGE_TIMEOUT_MS = 2000
JUSTIFICATION_TEXT_MAX_HEIGHT = 100
FEEDBACK_TEXT_MAX_HEIGHT = 80
DOCUMENT_FONT_SIZE = 10
SEPARATOR_LENGTH = 80

# Time format
TIME_FORMAT = "%H:%M:%S"

# File processing
SUPPORTED_FILE_EXTENSION = "*.txt"

# Button styling
BUTTON_STYLE_PRIMARY = """
    QPushButton {
        padding: 10px 30px;
        background-color: #28a745;
        color: white;
        border: none;
        border-radius: 3px;
        font-size: 16px;
        font-weight: bold;
    }
    QPushButton:hover:enabled {
        background-color: #218838;
    }
    QPushButton:disabled {
        background-color: #cccccc;
    }
"""

BUTTON_STYLE_DANGER = """
    QPushButton {
        padding: 10px 30px;
        background-color: #dc3545;
        color: white;
        border: none;
        border-radius: 3px;
        font-size: 16px;
        font-weight: bold;
    }
    QPushButton:hover:enabled {
        background-color: #c82333;
    }
    QPushButton:disabled {
        background-color: #cccccc;
    }
"""

BUTTON_STYLE_SECONDARY = """
    QPushButton {
        padding: 5px 15px;
        background-color: #0066cc;
        color: white;
        border: none;
        border-radius: 3px;
    }
    QPushButton:hover:enabled {
        background-color: #0052a3;
    }
    QPushButton:disabled {
        background-color: #cccccc;
        color: #666666;
    }
"""

BUTTON_STYLE_WARNING = """
    QPushButton {
        padding: 10px 30px;
        background-color: #ffc107;
        color: #212529;
        border: none;
        border-radius: 3px;
        font-size: 16px;
        font-weight: bold;
    }
    QPushButton:hover:enabled {
        background-color: #e0a800;
    }
    QPushButton:disabled {
        background-color: #cccccc;
        color: #666666;
    }
"""

# Decision button style (taller secondary buttons)
BUTTON_STYLE_DECISION = """
    QPushButton {
        padding: 10px 30px;
        background-color: #0066cc;
        color: white;
        border: none;
        border-radius: 3px;
        font-size: 16px;
        font-weight: bold;
    }
    QPushButton:hover:enabled {
        background-color: #0052a3;
    }
    QPushButton:disabled {
        background-color: #cccccc;
        color: #666666;
    }
"""

# Font settings
MONOSPACE_FONT_STACK = "'Courier New', Courier, Monaco, 'Lucida Console', monospace"

# Layout margins and spacing
MAIN_LAYOUT_MARGINS = (20, 20, 20, 20)
WIDGET_SPACING = 10

# Splitter sizes and ratios
FINALIZE_SPLITTER_SIZES = [600, 400]  # 60/40 ratio for document list/viewer
REVIEW_SPLITTER_STRETCH = (2, 3)  # 40/60 ratio for viewer/decision panel

# Widget dimensions
EXPORT_GROUP_MAX_HEIGHT = 80
DECISION_PANEL_MAX_HEIGHT = 180
SEARCH_INPUT_MAX_WIDTH = 250
STATS_LABEL_MAX_HEIGHT = 30

# Table column widths
TABLE_CHECKBOX_COLUMN_WIDTH = 30
TABLE_FLAG_COLUMN_WIDTH = 50

# Processing defaults
DEFAULT_PROCESSING_TIME = 2.5  # seconds

# UI symbols
FLAG_EMOJI = "🚩"

# Statistics display colors
STAT_COLOR_RESPONSIVE = "#28a745"
STAT_COLOR_NON_RESPONSIVE = "#dc3545"
STAT_COLOR_UNCERTAIN = "#ffc107"
STAT_COLOR_ERRORS = "#6c757d"
