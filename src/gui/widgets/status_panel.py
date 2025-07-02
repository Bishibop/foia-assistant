"""Status panel widget for displaying processing progress and statistics."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...constants import (
    ACTIVITY_LOG_MAX_HEIGHT,
    MONOSPACE_FONT_STACK,
    STAT_COLOR_ERRORS,
    STAT_COLOR_NON_RESPONSIVE,
    STAT_COLOR_RESPONSIVE,
    STAT_COLOR_UNCERTAIN,
)


class StatusPanel(QWidget):
    """Panel for displaying real-time processing status and statistics.

    Shows progress bar, current document, classification statistics,
    and an activity log for processing events.
    """

    def __init__(self) -> None:
        """Initialize the status panel."""
        super().__init__()
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress section
        progress_group = QGroupBox("Processing Progress")
        progress_layout = QVBoxLayout()

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v / %m documents (%p%)")
        progress_layout.addWidget(self.progress_bar)

        # Current document label
        self.current_doc_label = QLabel("Ready to process")
        self.current_doc_label.setStyleSheet("font-style: italic; color: #666;")
        progress_layout.addWidget(self.current_doc_label)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Statistics section
        stats_group = QGroupBox("Classification Statistics")
        stats_layout = QHBoxLayout()

        # Create stat widgets
        self.stats_labels = {
            "total": self._create_stat_widget("Total", "0", stats_layout),
            "processed": self._create_stat_widget("Processed", "0", stats_layout),
            "responsive": self._create_stat_widget(
                "Responsive", "0", stats_layout, STAT_COLOR_RESPONSIVE
            ),
            "non_responsive": self._create_stat_widget(
                "Non-Responsive", "0", stats_layout, STAT_COLOR_NON_RESPONSIVE
            ),
            "uncertain": self._create_stat_widget(
                "Uncertain", "0", stats_layout, STAT_COLOR_UNCERTAIN
            ),
            "errors": self._create_stat_widget(
                "Errors", "0", stats_layout, STAT_COLOR_ERRORS
            ),
        }

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Activity log section
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout()

        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMinimumHeight(ACTIVITY_LOG_MAX_HEIGHT)
        # Use the first font from the stack
        font_family = MONOSPACE_FONT_STACK.split(",")[0].strip("'")
        self.activity_log.setStyleSheet(
            f"""
            QTextEdit {{
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-family: {font_family};
                font-size: 12px;
            }}
        """
        )
        log_layout.addWidget(self.activity_log)

        log_group.setLayout(log_layout)
        # Allow the log group to expand vertically
        layout.addWidget(log_group, 1)  # stretch factor of 1

        self.setLayout(layout)

    def _create_stat_widget(
        self,
        label: str,
        value: str,
        parent_layout: QHBoxLayout,
        color: str | None = None,
    ) -> QLabel:
        """Create a statistics widget.

        Args:
            label: The statistic label
            value: The initial value
            parent_layout: Layout to add the widget to
            color: Optional color for the value

        Returns:
            The value label for updates

        """
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(2)

        # Label
        label_widget = QLabel(label)
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_widget.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(label_widget)

        # Value
        value_widget = QLabel(value)
        value_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        style = "font-size: 20px; font-weight: bold;"
        if color:
            style += f" color: {color};"
        value_widget.setStyleSheet(style)
        layout.addWidget(value_widget)

        container.setLayout(layout)
        parent_layout.addWidget(container)

        return value_widget

    def update_progress(self, current: int, total: int) -> None:
        """Update the progress bar.

        Args:
            current: Current document index
            total: Total number of documents

        """
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def set_current_document(self, filename: str) -> None:
        """Update the current document label.

        Args:
            filename: Name of the document being processed

        """
        self.current_doc_label.setText(f"Processing: {filename}")

    def update_statistics(self, stats: dict[str, int]) -> None:
        """Update all statistics displays.

        Args:
            stats: Dictionary of statistic values

        """
        for key, label in self.stats_labels.items():
            if key in stats:
                label.setText(str(stats[key]))

    def add_log_entry(self, message: str) -> None:
        """Add an entry to the activity log.

        Args:
            message: Message to add to the log

        """
        self.activity_log.append(message)
        # Auto-scroll to bottom
        scrollbar = self.activity_log.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def reset(self) -> None:
        """Reset all displays to initial state."""
        self.progress_bar.setValue(0)
        self.current_doc_label.setText("Ready to process")
        self.activity_log.clear()

        # Reset all statistics
        for label in self.stats_labels.values():
            label.setText("0")
