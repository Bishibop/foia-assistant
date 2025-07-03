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

        # Embedding Progress section (for duplicate detection) - shown first since it happens first
        embedding_group = QGroupBox("Duplicate Detection")
        embedding_layout = QVBoxLayout()

        # Embedding progress bar
        self.embedding_progress_bar = QProgressBar()
        self.embedding_progress_bar.setTextVisible(True)
        self.embedding_progress_bar.setFormat("Generating embeddings: %v / %m (%p%)")
        embedding_layout.addWidget(self.embedding_progress_bar)

        # Embedding stats
        embedding_stats_layout = QHBoxLayout()

        # Embeddings generated label
        self.embeddings_label = QLabel("Embeddings Generated: 0")
        self.embeddings_label.setStyleSheet("color: #0066cc;")
        embedding_stats_layout.addWidget(self.embeddings_label)

        # Add stretch to push duplicates label to the right
        embedding_stats_layout.addStretch()

        # Duplicates found label
        self.duplicates_label = QLabel("Duplicates Found: 0")
        self.duplicates_label.setStyleSheet("color: #ff6600; font-weight: bold;")
        embedding_stats_layout.addWidget(self.duplicates_label)

        embedding_layout.addLayout(embedding_stats_layout)

        # Parallel embedding info (initially hidden)
        self.embedding_parallel_widget = QWidget()
        embedding_parallel_layout = QHBoxLayout()
        embedding_parallel_layout.setContentsMargins(0, 5, 0, 0)

        # Worker count for embeddings
        self.embedding_worker_label = QLabel("Workers: -")
        self.embedding_worker_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        embedding_parallel_layout.addWidget(self.embedding_worker_label)

        # Processing rate for embeddings
        self.embedding_rate_label = QLabel("Rate: - docs/min")
        self.embedding_rate_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        embedding_parallel_layout.addWidget(self.embedding_rate_label)

        embedding_parallel_layout.addStretch()
        self.embedding_parallel_widget.setLayout(embedding_parallel_layout)
        self.embedding_parallel_widget.setVisible(False)
        embedding_layout.addWidget(self.embedding_parallel_widget)

        embedding_group.setLayout(embedding_layout)
        # Always visible now
        self.embedding_group = embedding_group
        layout.addWidget(embedding_group)

        # Progress section (document classification)
        progress_group = QGroupBox("Document Classification")
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

        # Parallel processing info (initially hidden)
        self.parallel_info_widget = QWidget()
        parallel_layout = QHBoxLayout()
        parallel_layout.setContentsMargins(0, 5, 0, 0)

        # Worker count
        self.worker_label = QLabel("Workers: -")
        self.worker_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        parallel_layout.addWidget(self.worker_label)

        # Processing rate
        self.rate_label = QLabel("Rate: - docs/min")
        self.rate_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        parallel_layout.addWidget(self.rate_label)

        parallel_layout.addStretch()
        self.parallel_info_widget.setLayout(parallel_layout)
        self.parallel_info_widget.setVisible(False)
        progress_layout.addWidget(self.parallel_info_widget)

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
            "duplicates": self._create_stat_widget(
                "Duplicates", "0", stats_layout, "#666666"
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

    def update_worker_count(self, count: int) -> None:
        """Update the worker count display.

        Args:
            count: Number of active workers

        """
        self.worker_label.setText(f"Workers: {count}")
        self.parallel_info_widget.setVisible(True)

    def update_processing_rate(self, rate: float) -> None:
        """Update the processing rate display.

        Args:
            rate: Processing rate in documents per minute

        """
        self.rate_label.setText(f"Rate: {rate:.1f} docs/min")
        self.parallel_info_widget.setVisible(True)

    def update_embedding_progress(self, current: int, total: int) -> None:
        """Update embedding generation progress.
        
        Args:
            current: Current number of embeddings generated
            total: Total number of documents to process
        
        """
        self.embedding_progress_bar.setMaximum(total)
        self.embedding_progress_bar.setValue(current)
        self.embeddings_label.setText(f"Embeddings Generated: {current}")

    def update_duplicate_count(self, count: int) -> None:
        """Update duplicate count display.
        
        Args:
            count: Number of duplicates found
        
        """
        self.duplicates_label.setText(f"Duplicates Found: {count}")
    
    def update_embedding_worker_count(self, count: int) -> None:
        """Update the embedding worker count display.
        
        Args:
            count: Number of active embedding workers
        
        """
        self.embedding_worker_label.setText(f"Workers: {count}")
        self.embedding_parallel_widget.setVisible(True)
    
    def update_embedding_processing_rate(self, rate: float) -> None:
        """Update the embedding processing rate display.
        
        Args:
            rate: Processing rate in documents per minute
        
        """
        self.embedding_rate_label.setText(f"Rate: {rate:.1f} docs/min")
        self.embedding_parallel_widget.setVisible(True)

    def reset(self) -> None:
        """Reset all displays to initial state."""
        self.progress_bar.setValue(0)
        self.current_doc_label.setText("Ready to process")
        self.activity_log.clear()

        # Hide parallel processing info
        self.parallel_info_widget.setVisible(False)
        self.worker_label.setText("Workers: -")
        self.rate_label.setText("Rate: - docs/min")

        # Reset embedding displays (keep visible)
        self.embedding_progress_bar.setValue(0)
        self.embeddings_label.setText("Embeddings Generated: 0")
        self.duplicates_label.setText("Duplicates Found: 0")
        
        # Hide embedding parallel processing info
        self.embedding_parallel_widget.setVisible(False)
        self.embedding_worker_label.setText("Workers: -")
        self.embedding_rate_label.setText("Rate: - docs/min")

        # Reset all statistics
        for label in self.stats_labels.values():
            label.setText("0")
