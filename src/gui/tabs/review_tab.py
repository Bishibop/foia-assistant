from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QShowEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.constants import MAIN_LAYOUT_MARGINS, STATUS_MESSAGE_MAX_HEIGHT, STATUS_MESSAGE_TIMEOUT_MS
from src.gui.styles import create_secondary_button
from src.gui.widgets.decision_panel import DecisionPanel
from src.gui.widgets.document_viewer import DocumentViewer
from src.models.document import Document


class ReviewTab(QWidget):
    """Tab for reviewing document classifications."""

    review_completed = pyqtSignal(
        Document
    )  # Emitted when a document review is completed
    all_documents_reviewed = pyqtSignal()  # Emitted when queue is empty

    def __init__(self) -> None:
        super().__init__()
        self._document_queue: list[Document] = []
        self._current_document: Document | None = None
        self._current_index = 0
        self._init_ui()
        self._update_queue_display()
        self._update_navigation()
        self._decision_panel.clear()  # Initially disable all decision buttons

    def _init_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(*MAIN_LAYOUT_MARGINS)

        # Header section
        header_layout = self._create_header_section()
        layout.addLayout(header_layout)

        # Navigation controls
        nav_layout = self._create_navigation_controls()
        layout.addLayout(nav_layout)

        # Main content area with splitter
        splitter = self._create_content_splitter()
        layout.addWidget(splitter, 1)  # Give splitter stretch factor to fill space

        # Status message
        self._status_message = self._create_status_message()
        layout.addWidget(self._status_message)

        self.setLayout(layout)

        # Set focus policy for keyboard shortcuts
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _create_header_section(self) -> QHBoxLayout:
        """Create the header with title and queue status."""
        header_layout = QHBoxLayout()

        from ..styles import create_title_label
        title = create_title_label("Document Review")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self._queue_status = QLabel("Queue: 0 documents")
        self._queue_status.setStyleSheet("font-size: 14px; color: #666;")
        header_layout.addWidget(self._queue_status)

        return header_layout

    def _create_navigation_controls(self) -> QHBoxLayout:
        """Create the navigation control buttons."""
        nav_layout = QHBoxLayout()

        self._prev_button = create_secondary_button("← Previous")
        self._prev_button.clicked.connect(self._previous_document)
        nav_layout.addWidget(self._prev_button)

        self._document_counter = QLabel("0 / 0")
        self._document_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self._document_counter)

        self._next_button = create_secondary_button("Next →")
        self._next_button.clicked.connect(self._next_document)
        nav_layout.addWidget(self._next_button)
        
        # Add stretch to keep buttons left-aligned
        nav_layout.addStretch()

        return nav_layout

    def _create_content_splitter(self) -> QSplitter:
        """Create the main content splitter with document viewer and decision panel."""
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Document viewer (left side)
        self._document_viewer = DocumentViewer()
        self._document_viewer.setMinimumWidth(200)  # Allow it to be resized smaller
        splitter.addWidget(self._document_viewer)

        # Decision panel (right side)
        self._decision_panel = DecisionPanel()
        self._decision_panel.decision_made.connect(self._on_decision_made)
        self._decision_panel.setMinimumWidth(200)  # Allow it to be resized smaller
        splitter.addWidget(self._decision_panel)

        # Set initial splitter with stretch factors for 40/60 split
        splitter.setStretchFactor(0, 2)  # Document viewer (40%)
        splitter.setStretchFactor(1, 3)  # Decision panel (60%)
        
        # Ensure splitter handle is visible and draggable
        splitter.setChildrenCollapsible(False)
        
        # Store splitter reference for later sizing
        self._splitter = splitter

        return splitter

    def _create_status_message(self) -> QLabel:
        """Create the status message label."""
        status_message = QLabel("")
        status_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_message.setStyleSheet("color: green; font-weight: bold;")
        status_message.setMaximumHeight(STATUS_MESSAGE_MAX_HEIGHT)
        return status_message

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the review queue."""
        # Only add documents that haven't been reviewed
        for doc in documents:
            if doc.human_decision is None and doc not in self._document_queue:
                self._document_queue.append(doc)

        self._update_queue_display()

        # Display first document if we don't have one showing
        if self._current_document is None and self._document_queue:
            self._display_document(0)

    def _display_document(self, index: int) -> None:
        """Display document at given index."""
        if 0 <= index < len(self._document_queue):
            self._current_index = index
            self._current_document = self._document_queue[index]

            # Update viewer
            self._document_viewer.display_document(
                self._current_document.filename,
                self._current_document.content,
                self._current_document.exemptions,
            )

            # Update decision panel
            self._decision_panel.display_classification(
                self._current_document.classification,
                self._current_document.confidence,
                self._current_document.justification,
                self._current_document.exemptions,
            )

            # Update navigation
            self._update_navigation()

    def _update_navigation(self) -> None:
        """Update navigation buttons and counter."""
        total = len(self._document_queue)
        current = self._current_index + 1 if total > 0 else 0

        self._document_counter.setText(f"{current} / {total}")
        
        # Disable all navigation buttons if no documents
        if total == 0:
            self._prev_button.setEnabled(False)
            self._next_button.setEnabled(False)
        else:
            self._prev_button.setEnabled(self._current_index > 0)
            self._next_button.setEnabled(self._current_index < total - 1)

    def _update_queue_display(self) -> None:
        """Update queue status display."""
        count = len(self._document_queue)
        self._queue_status.setText(
            f"Queue: {count} document{'s' if count != 1 else ''}"
        )

    def _on_decision_made(self, decision: str, feedback: str) -> None:
        """Handle decision from decision panel."""
        if self._current_document is None:
            return

        # Update document with decision
        if decision == "approved":
            self._current_document.human_decision = (
                self._current_document.classification
            )
        else:
            self._current_document.human_decision = decision

        self._current_document.human_feedback = feedback if feedback else None

        # Emit signal
        self.review_completed.emit(self._current_document)

        # Show status message
        self._show_status_message("Decision recorded!")

        # Remove from queue
        self._document_queue.pop(self._current_index)
        self._update_queue_display()

        # Move to next document
        if self._document_queue:
            # Stay at same index unless we're at the end
            if self._current_index >= len(self._document_queue):
                self._current_index = len(self._document_queue) - 1
            self._display_document(self._current_index)
        else:
            # No more documents
            self._current_document = None
            self._document_viewer.clear()
            self._decision_panel.clear()
            self._update_navigation()
            self._show_status_message("All documents reviewed!")
            self.all_documents_reviewed.emit()

    def _previous_document(self) -> None:
        """Navigate to previous document."""
        if self._current_index > 0:
            self._display_document(self._current_index - 1)

    def _next_document(self) -> None:
        """Navigate to next document."""
        if self._current_index < len(self._document_queue) - 1:
            self._display_document(self._current_index + 1)


    def _show_status_message(self, message: str) -> None:
        """Show temporary status message."""
        self._status_message.setText(message)
        QTimer.singleShot(STATUS_MESSAGE_TIMEOUT_MS, lambda: self._status_message.setText(""))

    def keyPressEvent(self, event: QKeyEvent | None) -> None:  # noqa: N802
        """Handle keyboard shortcuts."""
        if event is None or self._current_document is None:
            return

        key = event.key()

        if key == Qt.Key.Key_Space:
            # Spacebar = Approve
            self._decision_panel._make_decision("approved")
        elif key == Qt.Key.Key_R:
            # R = Responsive
            self._decision_panel._make_decision("responsive")
        elif key == Qt.Key.Key_N:
            # N = Non-responsive
            self._decision_panel._make_decision("non_responsive")
        elif key == Qt.Key.Key_U:
            # U = Uncertain
            self._decision_panel._make_decision("uncertain")
        elif key == Qt.Key.Key_Left:
            # Left arrow = Previous
            self._previous_document()
        elif key == Qt.Key.Key_Right:
            # Right arrow = Next
            self._next_document()
        else:
            super().keyPressEvent(event)

    def get_queue_count(self) -> int:
        """Get number of documents in queue."""
        return len(self._document_queue)
    
    def clear_all(self) -> None:
        """Clear all documents from the review queue."""
        self._document_queue.clear()
        self._current_document = None
        self._current_index = 0
        self._document_viewer.clear()
        self._decision_panel.clear()
        self._update_queue_display()
        self._update_navigation()
        self._status_message.clear()

    def showEvent(self, event: QShowEvent | None) -> None:  # noqa: N802
        """Handle widget show event to properly set splitter sizes."""
        super().showEvent(event)
        
        # Set proper splitter sizes for 40/60 split when widget is shown
        if hasattr(self, '_splitter') and self._splitter.width() > 0:
            total_width = self._splitter.width() - self._splitter.handleWidth()
            if total_width > 0:
                doc_viewer_width = int(total_width * 0.4)
                decision_panel_width = int(total_width * 0.6)
                self._splitter.setSizes([doc_viewer_width, decision_panel_width])
