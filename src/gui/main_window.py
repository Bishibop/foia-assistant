from datetime import timezone
from pathlib import Path

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from ..constants import (
    TAB_AUDIT,
    TAB_FINALIZE,
    TAB_INTAKE,
    TAB_REQUESTS,
    TAB_REVIEW,
    WINDOW_INITIAL_POSITION,
    WINDOW_INITIAL_SIZE,
    WINDOW_TITLE,
)
from ..processing.audit_manager import AuditManager
from ..processing.document_store import DocumentStore
from ..processing.feedback_manager import FeedbackManager
from ..processing.request_manager import RequestManager
from ..services.embedding_store import EmbeddingStore
from .styles import MAIN_WINDOW_STYLE
from .tabs.audit_tab import AuditTab
from .tabs.finalize_tab import FinalizeTab
from .tabs.intake_tab import IntakeTab
from .tabs.requests_tab import RequestsTab
from .tabs.review_tab import ReviewTab


class MainWindow(QMainWindow):
    """Main application window with tabbed interface.

    Provides the primary UI structure for the FOIA Response Assistant,
    organizing functionality into Processing, Review, and Processed tabs.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(
            WINDOW_INITIAL_POSITION[0],
            WINDOW_INITIAL_POSITION[1],
            WINDOW_INITIAL_SIZE[0],
            WINDOW_INITIAL_SIZE[1],
        )

        # Initialize managers
        self.request_manager = RequestManager()
        self.document_store = DocumentStore()
        self.feedback_manager = FeedbackManager()
        self.embedding_store = EmbeddingStore()
        self.audit_manager = AuditManager()

        # Store source folder path
        self.source_folder = None

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs with manager references
        self.requests_tab = RequestsTab(self.request_manager)
        self.intake_tab = IntakeTab(self.request_manager, self.document_store, self.feedback_manager, self.embedding_store, self.audit_manager)
        self.review_tab = ReviewTab(self.request_manager, self.document_store, self.feedback_manager, self.audit_manager)
        self.finalize_tab = FinalizeTab(self.request_manager, self.document_store, self.audit_manager)
        self.audit_tab = AuditTab(self.audit_manager, self.request_manager, self.document_store)

        # Add tabs to widget (Requests tab first)
        self.tab_widget.addTab(self.requests_tab, TAB_REQUESTS)
        self.tab_widget.addTab(self.intake_tab, TAB_INTAKE)
        self.tab_widget.addTab(self.review_tab, TAB_REVIEW)
        self.tab_widget.addTab(self.finalize_tab, TAB_FINALIZE)
        self.tab_widget.addTab(self.audit_tab, TAB_AUDIT)

        # Connect signals between tabs
        self._connect_signals()

        # Apply styling
        self._apply_styling()

        # Create default requests if none exist
        if self.request_manager.get_request_count() == 0:
            # Create multiple default requests
            default_requests = [
                {
                    "name": "F-2024-00123",
                    "description": "Blue Sky Project",
                    "foia_text": "All emails, documents, and communications related to the Blue Sky Project between January 2023 and September 2024.",
                    "deadline": "2025-07-04",
                },
                {
                    "name": "F-2024-00124",
                    "description": "Climate Research Grants",
                    "foia_text": "All grant applications, funding decisions, and correspondence related to climate change research funding awarded by the agency between October 2022 and December 2024.",
                },
                {
                    "name": "F-2024-00125",
                    "description": "Public Health Initiative",
                    "foia_text": "All records, reports, and communications regarding the Public Health Preparedness Initiative, including budget allocations and program evaluations from January 2023 to present.",
                },
                {
                    "name": "F-2024-00126",
                    "description": "Infrastructure Assessment",
                    "foia_text": "All engineering reports, safety assessments, and maintenance records for bridges and tunnels in Region 5, covering the period from July 2023 to October 2024.",
                },
                {
                    "name": "F-2024-00127",
                    "description": "Environmental Impact Study",
                    "foia_text": "All environmental impact assessments, public comments, and agency responses related to the proposed Riverside Development Project, from initial proposal in March 2023 through current date.",
                },
            ]

            # Create each request
            for req_data in default_requests:
                request = self.request_manager.create_request(
                    req_data["name"], req_data["description"]
                )
                # Build update kwargs
                update_kwargs = {"foia_request_text": req_data["foia_text"]}

                # Add deadline if specified
                if "deadline" in req_data:
                    from datetime import datetime

                    deadline = datetime.strptime(req_data["deadline"], "%Y-%m-%d")
                    deadline = deadline.replace(tzinfo=timezone.utc)
                    update_kwargs["deadline"] = deadline

                self.request_manager.update_request(request.id, **update_kwargs)

            # Clear active request so none are automatically selected
            self.request_manager._active_request_id = None
            self._update_window_title()
            # Refresh requests tab to show all default requests
            self.requests_tab._refresh_table()

        # Initial refresh of all tabs
        self.intake_tab.refresh_request_context()
        self.review_tab.refresh_request_context()
        self.finalize_tab.refresh_request_context()

    def _connect_signals(self) -> None:
        """Connect signals between tabs."""
        # Connect request tab signals
        self.requests_tab.request_created.connect(self._on_request_created)
        self.requests_tab.request_selected.connect(self._on_request_selected)
        self.requests_tab.request_deleted.connect(self._on_request_deleted)

        # When folder is selected, store it
        self.intake_tab.folder_selected.connect(self._on_folder_selected)

        # When processing starts, clear all tabs
        self.intake_tab.processing_started.connect(self._clear_all_tabs)

        # When intake completes, send documents to review
        self.intake_tab.documents_processed.connect(self._on_documents_ready)

        # When review completes, send to finalize tab
        self.review_tab.review_completed.connect(
            self.finalize_tab.add_processed_document
        )

        # When all documents are reviewed, enable finalize buttons
        self.review_tab.all_documents_reviewed.connect(
            lambda: self.finalize_tab.set_all_documents_reviewed(True)
        )

        # When reprocess with feedback is requested from review tab
        self.review_tab.reprocess_requested.connect(self._on_reprocess_requested)
        
        # Connect tab change signal to refresh audit tab
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

    def _on_folder_selected(self, folder: Path) -> None:
        """Store the selected source folder."""
        self.source_folder = folder
        self.finalize_tab.set_source_folder(folder)

    def _on_reprocess_requested(self) -> None:
        """Handle reprocess request from review tab."""
        # Switch to intake tab and trigger reprocessing
        self.tab_widget.setCurrentWidget(self.intake_tab)
        self._start_reprocessing_with_feedback()

    def _clear_all_tabs(self) -> None:
        """Clear all documents from review and finalize tabs."""
        self.review_tab.clear_all()
        self.finalize_tab.clear_all()

    def _on_documents_ready(self, documents: list) -> None:
        """Handle documents ready for review."""
        # Add documents to review queue
        self.review_tab.add_documents(documents)

    def _apply_styling(self) -> None:
        self.setStyleSheet(MAIN_WINDOW_STYLE)

    def _on_request_created(self, request_id: str) -> None:
        """Handle new request creation."""
        self._update_window_title()

    def _on_request_selected(self, request_id: str) -> None:
        """Handle request selection."""
        self._update_window_title()
        # Clear review queue when switching requests
        self.review_tab.clear_all()
        # Refresh tabs to show new active request
        self.intake_tab.refresh_request_context()
        self.review_tab.refresh_request_context()
        self.finalize_tab.refresh_request_context()

    def _on_request_deleted(self, request_id: str) -> None:
        """Handle request deletion."""
        # Clear associated documents from document store
        self.document_store.clear_request(request_id)
        # Clear associated feedback
        self.feedback_manager.clear_feedback(request_id)
        self._update_window_title()

    def _update_window_title(self) -> None:
        """Update window title with active request name."""
        active_request = self.request_manager.get_active_request()
        if active_request:
            self.setWindowTitle(f"{WINDOW_TITLE} - {active_request.name}")
        else:
            self.setWindowTitle(WINDOW_TITLE)

    def _start_reprocessing_with_feedback(self) -> None:
        """Start reprocessing unreviewed documents with feedback."""
        # Check if we have the required folder
        if not self.source_folder:
            return

        # Delegate to IntakeTab's reprocessing logic
        # We need to call the intake tab's reprocessing method directly
        self.intake_tab._start_reprocessing_with_feedback_from_main(
            self.source_folder
        )

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change to refresh audit tab when selected."""
        current_widget = self.tab_widget.widget(index)
        if current_widget == self.audit_tab:
            self.audit_tab.refresh()
