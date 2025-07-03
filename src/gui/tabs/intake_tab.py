import logging
from datetime import (
    datetime,
    timezone,
)  # Using timezone.utc for Python 3.10 compatibility (UTC added in 3.11)
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ...constants import (
    BUTTON_STYLE_DANGER,
    BUTTON_STYLE_PRIMARY,
    BUTTON_STYLE_SECONDARY,
    MAIN_LAYOUT_MARGINS,
    SPLITTER_SIZES,
    SUPPORTED_FILE_EXTENSION,
    TIME_FORMAT,
)
from ...models.document import Document
from ...processing.document_store import DocumentStore
from ...processing.feedback_manager import FeedbackManager
from ...processing.request_manager import RequestManager
from ...processing.worker import ProcessingWorker
from ...services.embedding_store import EmbeddingStore
from ..widgets.status_panel import StatusPanel

logger = logging.getLogger(__name__)


class IntakeTab(QWidget):
    """Tab for document intake and AI processing.

    Allows users to select a folder of documents and uses the active FOIA request
    to process documents against. Provides controls to start the AI processing.
    """

    documents_processed = pyqtSignal(
        list
    )  # Emitted when documents are ready for review
    folder_selected = pyqtSignal(Path)  # Emitted when a folder is selected
    processing_started = pyqtSignal()  # Emitted when processing starts

    def __init__(
        self,
        request_manager: RequestManager | None = None,
        document_store: DocumentStore | None = None,
        feedback_manager: FeedbackManager | None = None,
        embedding_store: EmbeddingStore | None = None,
    ) -> None:
        super().__init__()
        self.request_manager = request_manager
        self.document_store = document_store
        self.feedback_manager = feedback_manager
        self.embedding_store = embedding_store
        self.selected_folder: Path | None = None
        self.worker: ProcessingWorker | None = None
        self.processed_documents: list[Document] = []
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = self._create_main_layout()

        # Create splitter for configuration and status
        splitter = self._create_content_splitter()
        main_layout.addWidget(splitter, 1)  # Add stretch factor to fill space

        self.setLayout(main_layout)

        # Update active request display
        if self.request_manager:
            self._update_active_request_display()

    def _create_main_layout(self) -> QVBoxLayout:
        """Create the main layout with title."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(*MAIN_LAYOUT_MARGINS)
        main_layout.setSpacing(10)  # Add consistent spacing

        # Header with title and request info
        header_layout = QHBoxLayout()

        # Title
        from ..styles import create_title_label

        title = create_title_label("Document Processing")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Active request info (top-right)
        if self.request_manager:
            self.active_request_label = QLabel("No active request")
            self.active_request_label.setStyleSheet(
                "font-size: 14px; color: #0066cc; font-weight: bold;"
            )
            header_layout.addWidget(self.active_request_label)

        main_layout.addLayout(header_layout, 0)  # No stretch for header

        return main_layout

    def _create_content_splitter(self) -> QSplitter:
        """Create the splitter with config and status panels."""
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)

        # Left side - Configuration
        config_widget = self._create_config_widget()
        splitter.addWidget(config_widget)

        # Right side - Status panel
        self.status_panel = StatusPanel()
        splitter.addWidget(self.status_panel)

        # Set initial splitter sizes (40% config, 60% status)
        splitter.setSizes(SPLITTER_SIZES)

        return splitter

    def _create_config_widget(self) -> QWidget:
        """Create the configuration widget with folder selection and request input."""
        config_widget = QWidget()
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(0, 0, 10, 0)

        # Folder selection section
        folder_group = self._create_folder_section()
        config_layout.addWidget(folder_group)

        # Active request info section
        request_info_group = self._create_request_info_section()
        config_layout.addWidget(request_info_group)

        # Process buttons
        button_layout = self._create_button_layout()
        config_layout.addLayout(button_layout)

        # Add stretch at bottom to push content up
        config_layout.addStretch()

        config_widget.setLayout(config_layout)
        return config_widget

    def _create_folder_section(self) -> QGroupBox:
        """Create the folder selection section."""
        folder_group = QGroupBox("Select Documents Folder")
        folder_layout = QHBoxLayout()

        self.folder_label = QLineEdit()
        self.folder_label.setPlaceholderText("No folder selected")
        self.folder_label.setReadOnly(True)
        self.folder_label.setStyleSheet("padding: 5px; background-color: #f9f9f9;")

        self.select_folder_btn = QPushButton("Browse...")
        self.select_folder_btn.clicked.connect(self._select_folder)
        self.select_folder_btn.setStyleSheet(BUTTON_STYLE_SECONDARY)

        folder_layout.addWidget(self.folder_label, 1)
        folder_layout.addWidget(self.select_folder_btn)
        folder_group.setLayout(folder_layout)

        return folder_group

    def _create_request_info_section(self) -> QGroupBox:
        """Create the active request info section."""
        request_group = QGroupBox("Active FOIA Request")
        request_layout = QVBoxLayout()
        request_layout.setContentsMargins(10, 10, 10, 10)
        request_layout.setSpacing(5)

        # Create label for active request display
        self.request_info_label = QLabel("No active request selected")
        self.request_info_label.setWordWrap(True)
        self.request_info_label.setStyleSheet(
            "padding: 10px; background-color: #f9f9f9; border: 1px solid #ddd; border-radius: 4px;"
        )
        request_layout.addWidget(self.request_info_label)

        # Note about setting active request
        note_label = QLabel(
            "Note: Set an active request in the Requests tab before processing."
        )
        note_label.setStyleSheet("color: #666; font-size: 12px; font-style: italic;")
        request_layout.addWidget(note_label)

        request_group.setLayout(request_layout)
        return request_group

    def _create_button_layout(self) -> QHBoxLayout:
        """Create the process and cancel buttons layout."""
        button_layout = QHBoxLayout()

        self.process_btn = QPushButton("Start Processing")
        self.process_btn.setEnabled(False)
        self.process_btn.clicked.connect(self._start_processing)
        self.process_btn.setStyleSheet(BUTTON_STYLE_PRIMARY)


        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_processing)
        self.cancel_btn.setStyleSheet(BUTTON_STYLE_DANGER)

        button_layout.addStretch()
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addStretch()

        return button_layout

    def _select_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Documents Folder", "", QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.selected_folder = Path(folder)
            self.folder_label.setText(str(self.selected_folder))

            # Count .txt files and show in status
            txt_files = list(self.selected_folder.glob(SUPPORTED_FILE_EXTENSION))
            self.status_panel.add_log_entry(
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] "  # timezone.utc for Python 3.10 compat
                f"Selected folder: {self.selected_folder} "
                f"(found {len(txt_files)} .txt files)"
            )

            # Emit the folder selection
            self.folder_selected.emit(self.selected_folder)

            self._check_ready_to_process()

    def _check_ready_to_process(self) -> None:
        # Enable process button only if both folder and active request are available
        has_folder = self.selected_folder is not None
        has_active_request = False

        if self.request_manager:
            active_request = self.request_manager.get_active_request()
            has_active_request = active_request is not None

        self.process_btn.setEnabled(has_folder and has_active_request)

    def _start_processing(self) -> None:
        """Start processing documents with LangGraph."""
        if not self._validate_processing_inputs():
            return

        try:
            self._disable_ui_during_processing()
            self._prepare_for_processing()
            self._setup_and_start_worker()

        except Exception as e:
            logger.error(f"Failed to start processing: {e}")
            self._on_error(f"Failed to start processing: {e!s}")
            self._enable_ui_after_processing()

    def _validate_processing_inputs(self) -> bool:
        """Validate that we have necessary inputs for processing."""
        # Check for selected folder
        if not self.selected_folder:
            return False

        # Check for active request
        if not self.request_manager:
            QMessageBox.critical(
                self,
                "No Request Manager",
                "Request manager is not available. Cannot process documents.",
            )
            return False

        active_request = self.request_manager.get_active_request()
        if not active_request:
            QMessageBox.warning(
                self,
                "No Active Request",
                "Please select an active request in the Requests tab before processing documents.",
            )
            return False

        if not active_request.foia_request_text:
            QMessageBox.critical(
                self,
                "Invalid Request",
                "The active request has no FOIA text. Please update the request.",
            )
            return False

        # Validate folder exists
        if not self.selected_folder.exists():
            QMessageBox.critical(
                self,
                "Folder Not Found",
                f"The selected folder no longer exists:\n{self.selected_folder}",
            )
            self.selected_folder = None
            self.folder_label.clear()
            self._check_ready_to_process()
            return False

        return True

    def _disable_ui_during_processing(self) -> None:
        """Disable UI controls during processing."""
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.select_folder_btn.setEnabled(False)
        # No longer need to disable request text since it's not an input field

    def _enable_ui_after_processing(self) -> None:
        """Re-enable UI controls after processing."""
        self.cancel_btn.setEnabled(False)
        self.select_folder_btn.setEnabled(True)
        # Re-check what should be enabled based on current state
        self._check_ready_to_process()

    def _prepare_for_processing(self) -> None:
        """Prepare the UI and emit signals before processing."""
        # Emit signal to clear all tabs
        self.processing_started.emit()

        # Reset status panel and documents list
        self.status_panel.reset()
        self.processed_documents.clear()

        # Log start
        self.status_panel.add_log_entry(
            f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Starting processing of folder: {self.selected_folder}"  # timezone.utc for Python 3.10 compat
        )

    def _setup_and_start_worker(self) -> None:
        """Create, configure and start the processing worker."""
        # Get active request - we've already validated it exists
        active_request = self.request_manager.get_active_request()

        # Create and configure worker with the active request's FOIA text and feedback manager
        self.worker = ProcessingWorker(
            self.selected_folder,
            active_request.foia_request_text,
            request_id=active_request.id,
            feedback_manager=self.feedback_manager,
            embedding_store=self.embedding_store
        )

        # Connect signals
        self._connect_worker_signals()

        # Start processing
        self.worker.start()

    def _connect_worker_signals(self) -> None:
        """Connect all worker signals to their handlers."""
        self.worker.progress_updated.connect(self.status_panel.update_progress)
        self.worker.document_processing.connect(self._on_document_processing)
        self.worker.document_processed.connect(self._on_document_processed)
        self.worker.processing_complete.connect(self._on_processing_complete)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.stats_updated.connect(self.status_panel.update_statistics)

        # Connect new parallel processing signals
        self.worker.processing_rate_updated.connect(self.status_panel.update_processing_rate)
        self.worker.worker_count_updated.connect(self.status_panel.update_worker_count)
        
        # Connect embedding signals for duplicate detection
        self.worker.embedding_progress.connect(self.status_panel.update_embedding_progress)
        self.worker.duplicates_found.connect(self.status_panel.update_duplicate_count)
        self.worker.status_updated.connect(self.status_panel.add_log_entry)
        self.worker.embedding_worker_count.connect(self.status_panel.update_embedding_worker_count)
        self.worker.embedding_rate_updated.connect(self.status_panel.update_embedding_processing_rate)

    def _cancel_processing(self) -> None:
        """Cancel the current processing operation."""
        if self.worker:
            self.worker.cancel()
            self.status_panel.add_log_entry(
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Processing cancelled by user"  # timezone.utc for Python 3.10 compat
            )

    def _on_document_processing(self, filename: str) -> None:
        """Handle document processing signal.

        Args:
            filename: Name of the document being processed

        """
        self.status_panel.set_current_document(filename)
        self.status_panel.add_log_entry(
            f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Processing: {filename}"  # timezone.utc for Python 3.10 compat
        )

    def _on_document_processed(self, document: Document) -> None:
        """Handle document processed signal.

        Args:
            document: The processed document

        """
        self.processed_documents.append(document)

        # Store in document store if available
        if self.document_store and self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                self.document_store.add_document(active_request.id, document)

        # Log with classification
        if document.classification:
            confidence_str = (
                f"{document.confidence:.1%}"
                if document.confidence is not None
                else "N/A"
            )
            log_entry = (
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] "  # timezone.utc for Python 3.10 compat
                f"Classified {document.filename} as {document.classification.upper()} "
                f"(confidence: {confidence_str})"
            )
        else:
            log_entry = (
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] "  # timezone.utc for Python 3.10 compat
                f"Failed to classify {document.filename} - check API key"
            )
        self.status_panel.add_log_entry(log_entry)

    def _on_processing_complete(self) -> None:
        """Handle processing complete signal."""
        # Re-enable controls
        self._enable_ui_after_processing()

        # Log completion
        self.status_panel.add_log_entry(
            f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Processing complete!"  # timezone.utc for Python 3.10 compat
        )

        # Update request statistics if available
        if self.request_manager and self.document_store:
            active_request = self.request_manager.get_active_request()
            if active_request:
                # Update request with processing stats
                stats = self.document_store.get_statistics(active_request.id)
                self.request_manager.update_request(
                    active_request.id,
                    status="review",
                    total_documents=stats["total"],
                    processed_documents=stats["total"],
                    responsive_count=stats["responsive"],
                    non_responsive_count=stats["non_responsive"],
                    uncertain_count=stats["uncertain"],
                )

        # Emit documents for review
        if self.processed_documents:
            self.documents_processed.emit(self.processed_documents.copy())

        # Log completion summary to activity panel instead of showing alert
        stats = self.worker.stats if self.worker else {}
        self.status_panel.add_log_entry(
            f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Processing complete! "  # timezone.utc for Python 3.10 compat
            f"Total: {stats.get('total', 0)}, "
            f"Responsive: {stats.get('responsive', 0)}, "
            f"Non-responsive: {stats.get('non_responsive', 0)}, "
            f"Uncertain: {stats.get('uncertain', 0)}, "
            f"Duplicates: {stats.get('duplicates', 0)}, "
            f"Errors: {stats.get('errors', 0)}"
        )

        # Clean up worker
        if self.worker:
            self.worker.deleteLater()
            self.worker = None

    def _on_error(self, error_message: str) -> None:
        """Handle error signal.

        Args:
            error_message: The error message to display

        """
        self.status_panel.add_log_entry(
            f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] ERROR: {error_message}"  # timezone.utc for Python 3.10 compat
        )

        # Show error dialog
        QMessageBox.critical(
            self,
            "Processing Error",
            f"An error occurred during processing:\n\n{error_message}",
        )

    def _update_active_request_display(self) -> None:
        """Update the active request display."""
        if hasattr(self, "active_request_label") and self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                self.active_request_label.setText(f"Active: {active_request.name}")

                # Update request info in the info section if it exists
                if hasattr(self, "request_info_label"):
                    request_text = active_request.foia_request_text or "No request text"
                    # Truncate if too long
                    if len(request_text) > 200:
                        request_text = request_text[:197] + "..."
                    self.request_info_label.setText(f"Request: {request_text}")
            else:
                self.active_request_label.setText("No active request")
                if hasattr(self, "request_info_label"):
                    self.request_info_label.setText("No active request selected")

        # Check if we can process now
        self._check_ready_to_process()

    def refresh_request_context(self) -> None:
        """Refresh the request context display."""
        self._update_active_request_display()

        # Cancel any ongoing processing when switching requests
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker = None

            # Re-enable the UI
            self.process_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.select_folder_btn.setEnabled(True)

        # Reset the status panel when switching requests
        if hasattr(self, "status_panel"):
            self.status_panel.reset()

        # Clear the list of processed documents for this tab
        self.processed_documents.clear()
        
        # Clear embeddings for the old request if switching
        if self.embedding_store and self.request_manager:
            # Note: We're not clearing here because we might want to keep embeddings
            # across request switches. The embedding store handles request isolation.
            pass

        # Update feedback statistics if available
        if self.feedback_manager and self.request_manager:
            active_request = self.request_manager.get_active_request()
            if active_request:
                stats = self.feedback_manager.get_statistics(active_request.id)
                if stats["total_corrections"] > 0:
                    self.status_panel.add_log_entry(
                        f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] "
                        f"Feedback available: {stats['total_corrections']} corrections"
                    )


    def _start_processing_unreviewed(self, unreviewed_docs: list[Document]) -> None:
        """Start processing only unreviewed documents with feedback."""
        if not self.selected_folder:
            return

        try:
            self._disable_ui_during_processing()

            # Emit signal to clear tabs (but we're only processing unreviewed)
            # This might need adjustment based on desired behavior
            self.processing_started.emit()

            # Reset status panel
            self.status_panel.reset()

            # Get list of unreviewed filenames
            unreviewed_filenames = {doc.filename for doc in unreviewed_docs}

            # Filter txt files to only include unreviewed ones
            all_txt_files = list(self.selected_folder.glob(SUPPORTED_FILE_EXTENSION))
            txt_files_to_process = [
                f for f in all_txt_files
                if f.name in unreviewed_filenames
            ]

            if not txt_files_to_process:
                self._on_error("No unreviewed documents found in folder")
                self._enable_ui_after_processing()
                return

            # Log start
            self.status_panel.add_log_entry(
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] "
                f"Starting reprocessing of {len(txt_files_to_process)} unreviewed documents"
            )

            # Get active request
            active_request = self.request_manager.get_active_request()
            if not active_request:
                self._on_error("No active request")
                self._enable_ui_after_processing()
                return

            # Create worker with specific file list for unreviewed documents
            self.worker = ProcessingWorker(
                self.selected_folder,
                active_request.foia_request_text,
                request_id=active_request.id,
                feedback_manager=self.feedback_manager,
                embedding_store=self.embedding_store,
                file_list=txt_files_to_process  # Pass the filtered file list
            )

            # Connect signals
            self._connect_worker_signals()

            # Start processing
            self.worker.start()

        except Exception as e:
            logger.error(f"Failed to start reprocessing: {e}")
            self._on_error(f"Failed to start reprocessing: {e!s}")
            self._enable_ui_after_processing()

    def _start_reprocessing_with_feedback_from_main(self, folder_path: Path) -> None:
        """Start reprocessing with feedback called from MainWindow."""
        # Set the folder path
        self.selected_folder = folder_path
        self.folder_label.setText(str(self.selected_folder))

        # Get unreviewed documents to reprocess
        if not self.request_manager or not self.document_store:
            return

        active_request = self.request_manager.get_active_request()
        if not active_request:
            return

        unreviewed_docs = self.document_store.get_unreviewed_documents(active_request.id)
        if not unreviewed_docs:
            return

        # Start the reprocessing (dialog already confirmed in ReviewTab)
        self._start_processing_unreviewed(unreviewed_docs)
