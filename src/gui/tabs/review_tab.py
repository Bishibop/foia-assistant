from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QShowEvent
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.constants import (
    BUTTON_STYLE_SECONDARY,
    MAIN_LAYOUT_MARGINS,
    STATUS_MESSAGE_MAX_HEIGHT,
    STATUS_MESSAGE_TIMEOUT_MS,
)
from src.gui.styles import create_secondary_button
from src.gui.widgets.decision_panel import DecisionPanel
from src.gui.widgets.document_viewer import DocumentViewer
from src.models.document import Document
from src.processing.document_store import DocumentStore
from src.processing.feedback_manager import FeedbackManager
from src.processing.request_manager import RequestManager


class ReviewTab(QWidget):
    """Tab for reviewing document classifications."""

    review_completed = pyqtSignal(
        Document
    )  # Emitted when a document review is completed
    all_documents_reviewed = pyqtSignal()  # Emitted when queue is empty
    reprocess_requested = pyqtSignal()  # Emitted when user wants to reprocess with feedback

    def __init__(
        self,
        request_manager: RequestManager | None = None,
        document_store: DocumentStore | None = None,
        feedback_manager: FeedbackManager | None = None,
    ) -> None:
        super().__init__()
        self.request_manager = request_manager
        self.document_store = document_store
        self.feedback_manager = feedback_manager
        self._document_queue: list[Document] = []
        self._current_document: Document | None = None
        self._current_index = 0
        self._init_ui()
        self._update_queue_display()
        self._update_navigation()
        self._decision_panel.clear()  # Initially disable all decision buttons
        self._update_feedback_panel()  # Initialize feedback panel

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

        # Reprocess button (feedback panel)
        feedback_layout = self._create_feedback_panel()
        layout.addLayout(feedback_layout)

        self.setLayout(layout)

        # Set focus policy for keyboard shortcuts
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _create_header_section(self) -> QHBoxLayout:
        """Create the header with title and active request."""
        header_layout = QHBoxLayout()

        from ..styles import create_title_label

        title = create_title_label("Document Review")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Active request label (top-right)
        if self.request_manager:
            self._active_request_label = QLabel("No active request")
            self._active_request_label.setStyleSheet(
                "font-size: 14px; color: #0066cc; font-weight: bold;"
            )
            header_layout.addWidget(self._active_request_label)
            self._update_active_request_display()

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

    def _create_feedback_panel(self) -> QHBoxLayout:
        """Create the feedback panel with reprocess button."""
        feedback_layout = QHBoxLayout()

        # Feedback info label
        self._feedback_info_label = QLabel("")
        self._feedback_info_label.setStyleSheet("color: #666; font-size: 12px; font-style: italic;")
        feedback_layout.addWidget(self._feedback_info_label)

        feedback_layout.addStretch()

        # Reprocess button
        self._reprocess_btn = QPushButton("Reprocess Unreviewed with Feedback")
        self._reprocess_btn.setEnabled(False)
        self._reprocess_btn.clicked.connect(self._request_reprocess_with_feedback)
        self._reprocess_btn.setStyleSheet(BUTTON_STYLE_SECONDARY)
        self._reprocess_btn.setToolTip("Reprocess remaining unreviewed documents using learned patterns from corrections")
        feedback_layout.addWidget(self._reprocess_btn)

        return feedback_layout

    def add_documents(self, documents: list[Document]) -> None:
        """Add documents to the review queue."""
        # If we have a document store and request manager, load from active request
        if self.document_store and self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                # Load unreviewed documents from the document store for this request
                self._document_queue = self.document_store.get_unreviewed_documents(
                    active_request.id
                )
        else:
            # Fall back to the provided documents
            # Only add documents that haven't been reviewed
            for doc in documents:
                if doc.human_decision is None and doc not in self._document_queue:
                    self._document_queue.append(doc)

        self._update_queue_display()

        # Display first document if we don't have one showing
        if self._current_document is None and self._document_queue:
            self._display_document(0)

        # Update feedback panel when documents are added
        self._update_feedback_panel()

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
        # Queue count is now shown in the navigation counter
        pass

    def _on_decision_made(self, decision: str, feedback: str) -> None:
        """Handle decision from decision panel."""
        if self._current_document is None:
            return

        # Handle override non-duplicate decision
        if decision == "override_non_duplicate":
            self._handle_override_non_duplicate()
            return

        # Update document with decision
        if decision == "approved":
            self._current_document.human_decision = (
                self._current_document.classification
            )
        else:
            self._current_document.human_decision = decision

        self._current_document.human_feedback = feedback if feedback else None

        # Update in document store if available
        if self.document_store and self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                self.document_store.update_document(
                    active_request.id,
                    self._current_document.filename,
                    human_decision=self._current_document.human_decision,
                    human_feedback=self._current_document.human_feedback,
                )

                # Capture feedback if human corrected the AI
                if self.feedback_manager and decision != "approved" and self._current_document.human_decision:
                    self.feedback_manager.add_feedback(
                        self._current_document,
                        active_request.id,
                        self._current_document.human_decision
                    )

        # Emit signal
        self.review_completed.emit(self._current_document)

        # Show appropriate status message and update feedback panel
        if (self.feedback_manager and self.request_manager and
            decision != "approved" and
            self._current_document.classification != self._current_document.human_decision):
            self._show_status_message("Decision recorded and feedback captured!")
            self._update_feedback_panel()  # Update feedback panel after capturing feedback
        else:
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
        QTimer.singleShot(
            STATUS_MESSAGE_TIMEOUT_MS, lambda: self._status_message.setText("")
        )

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
        elif key == Qt.Key.Key_D:
            # D = Override Non-Duplicate (only for duplicates)
            if self._current_document.classification == "duplicate":
                self._decision_panel._make_decision("override_non_duplicate")
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
        if hasattr(self, "_splitter") and self._splitter.width() > 0:
            total_width = self._splitter.width() - self._splitter.handleWidth()
            if total_width > 0:
                doc_viewer_width = int(total_width * 0.4)
                decision_panel_width = int(total_width * 0.6)
                self._splitter.setSizes([doc_viewer_width, decision_panel_width])

    def _update_active_request_display(self) -> None:
        """Update the active request display."""
        if hasattr(self, "_active_request_label") and self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                self._active_request_label.setText(f"Request: {active_request.name}")
            else:
                self._active_request_label.setText("No active request")

    def refresh_request_context(self) -> None:
        """Refresh the review queue for the active request."""
        self._update_active_request_display()
        # Reload documents from document store for active request
        if self.document_store and self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                self._document_queue = self.document_store.get_unreviewed_documents(
                    active_request.id
                )
                self._update_queue_display()
                # Display first document if available
                if self._document_queue and not self._current_document:
                    self._display_document(0)

        # Update feedback panel for new request
        self._update_feedback_panel()

    def _update_feedback_panel(self) -> None:
        """Update the feedback panel based on current feedback and document state."""
        if not self.feedback_manager or not self.request_manager:
            self._feedback_info_label.setText("")
            self._reprocess_btn.setEnabled(False)
            return

        active_request = self.request_manager.get_active_request()
        if not active_request:
            self._feedback_info_label.setText("")
            self._reprocess_btn.setEnabled(False)
            return

        # Get feedback statistics
        stats = self.feedback_manager.get_statistics(active_request.id)

        if stats["total_corrections"] == 0:
            self._feedback_info_label.setText("No feedback captured yet")
            self._reprocess_btn.setEnabled(False)
        else:
            # Check if there are unreviewed documents to reprocess
            has_unreviewed = False
            if self.document_store:
                unreviewed_docs = self.document_store.get_unreviewed_documents(active_request.id)
                has_unreviewed = len(unreviewed_docs) > 0

            if has_unreviewed:
                self._feedback_info_label.setText(
                    f"Feedback available: {stats['total_corrections']} corrections (most common: {stats['most_corrected_type']})"
                )
                self._reprocess_btn.setEnabled(True)
            else:
                self._feedback_info_label.setText(
                    f"Feedback available: {stats['total_corrections']} corrections (no unreviewed documents)"
                )
                self._reprocess_btn.setEnabled(False)

    def _request_reprocess_with_feedback(self) -> None:
        """Request reprocessing with feedback from the main application."""
        if not self.feedback_manager or not self.request_manager or not self.document_store:
            return

        active_request = self.request_manager.get_active_request()
        if not active_request:
            return

        # Get feedback and unreviewed document counts
        feedback_stats = self.feedback_manager.get_statistics(active_request.id)
        unreviewed_docs = self.document_store.get_unreviewed_documents(active_request.id)

        if feedback_stats["total_corrections"] == 0:
            return

        if not unreviewed_docs:
            return

        # Emit signal to request reprocessing immediately
        self.reprocess_requested.emit()

    def _handle_override_non_duplicate(self) -> None:
        """Handle override non-duplicate decision by reclassifying the document."""
        if self._current_document is None:
            return
            
        # Create progress dialog
        progress = QProgressDialog(
            "Reclassifying document as non-duplicate...", 
            None,  # No cancel button
            0, 
            0,  # Indeterminate progress
            self
        )
        progress.setWindowTitle("Processing")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)  # Show immediately
        progress.setAutoClose(True)
        progress.setAutoReset(True)
        
        # Disable the cancel button
        progress.setCancelButton(None)
        
        # Show the progress dialog
        progress.show()
        QApplication.processEvents()  # Ensure the dialog is displayed
        
        # Import what we need for classification
        from ...langgraph.workflow import create_initial_state, get_compiled_workflow
        
        # Get active request for FOIA request text
        if not self.request_manager:
            progress.close()
            return
            
        active_request = self.request_manager.get_active_request()
        if not active_request:
            progress.close()
            return
        
        try:
            # Create workflow and state
            workflow = get_compiled_workflow()
            initial_state = create_initial_state(
                self._current_document.filename,
                active_request.foia_request_text
            )
            
            # Add document content
            initial_state["content"] = self._current_document.content
            
            # Override duplicate flags to force classification
            initial_state["is_duplicate"] = False
            initial_state["duplicate_of"] = None
            initial_state["similarity_score"] = None
            
            # Run the workflow
            QApplication.processEvents()  # Keep UI responsive
            final_state = workflow.invoke(initial_state)
            
            # Update the current document with new classification
            self._current_document.classification = final_state["classification"]
            self._current_document.confidence = final_state["confidence"]
            self._current_document.justification = final_state["justification"]
            self._current_document.exemptions = final_state.get("exemptions", [])
            
            # Clear duplicate metadata
            self._current_document.is_duplicate = False
            self._current_document.duplicate_of = None
            self._current_document.similarity_score = None
            
            # Update the UI to show new classification
            self._decision_panel.display_classification(
                self._current_document.classification,
                self._current_document.confidence,
                self._current_document.justification,
                self._current_document.exemptions,
            )
            
            # Update in document store if available
            if self.document_store:
                self.document_store.update_document(
                    active_request.id,
                    self._current_document.filename,
                    classification=self._current_document.classification,
                    confidence=self._current_document.confidence,
                    justification=self._current_document.justification,
                    exemptions=self._current_document.exemptions,
                    is_duplicate=False,
                    duplicate_of=None,
                    similarity_score=None,
                )
            
            # Close progress dialog
            progress.close()
            
            self._show_status_message("Document reclassified successfully!")
            
        except Exception as e:
            # Close progress dialog on error
            progress.close()
            
            self._show_status_message(f"Error reclassifying document: {str(e)}")
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error reclassifying document: {e}", exc_info=True)
