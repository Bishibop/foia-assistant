import logging
from datetime import datetime, timezone
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ...constants import (
    BUTTON_STYLE_DANGER,
    BUTTON_STYLE_PRIMARY,
    BUTTON_STYLE_SECONDARY,
    MAIN_LAYOUT_MARGINS,
    REQUEST_TEXT_MAX_HEIGHT,
    REQUEST_TEXT_MIN_HEIGHT,
    SPLITTER_SIZES,
    SUPPORTED_FILE_EXTENSION,
    TIME_FORMAT,
)
from ...models.document import Document
from ...processing.worker import ProcessingWorker
from ..widgets.status_panel import StatusPanel

logger = logging.getLogger(__name__)


class IntakeTab(QWidget):
    """Tab for document intake and AI processing.

    Allows users to select a folder of documents and enter a FOIA request
    to process documents against. Provides controls to start the AI processing.
    """

    documents_processed = pyqtSignal(
        list
    )  # Emitted when documents are ready for review
    folder_selected = pyqtSignal(Path)  # Emitted when a folder is selected
    processing_started = pyqtSignal()  # Emitted when processing starts

    def __init__(self) -> None:
        super().__init__()
        self.selected_folder: Path | None = None
        self.worker: ProcessingWorker | None = None
        self.processed_documents: list[Document] = []
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = self._create_main_layout()
        
        # Create splitter for configuration and status
        splitter = self._create_content_splitter()
        main_layout.addWidget(splitter)
        
        self.setLayout(main_layout)

        # Connect text change to enable/disable process button
        self.request_text.textChanged.connect(self._check_ready_to_process)

    def _create_main_layout(self) -> QVBoxLayout:
        """Create the main layout with title."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(*MAIN_LAYOUT_MARGINS)

        # Title
        from ..styles import create_title_label
        title = create_title_label("Document Processing")
        main_layout.addWidget(title)
        
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

        # FOIA request section
        request_group = self._create_request_section()
        config_layout.addWidget(request_group)

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

    def _create_request_section(self) -> QGroupBox:
        """Create the FOIA request input section."""
        request_group = QGroupBox("FOIA Request")
        request_layout = QVBoxLayout()
        request_layout.setContentsMargins(10, 10, 10, 10)
        request_layout.setSpacing(5)

        request_label = QLabel("Enter the FOIA request to process documents against:")
        request_layout.addWidget(request_label)

        self.request_text = QTextEdit()
        self.request_text.setPlaceholderText(
            "e.g., All emails and documents related to Project Blue Sky from January 2023 to December 2023"
        )
        self.request_text.setMinimumHeight(REQUEST_TEXT_MIN_HEIGHT)
        self.request_text.setMaximumHeight(REQUEST_TEXT_MAX_HEIGHT)
        request_layout.addWidget(self.request_text)
        
        # Add stretch to push content up within the group box
        request_layout.addStretch()

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
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] "
                f"Selected folder: {self.selected_folder} "
                f"(found {len(txt_files)} .txt files)"
            )
            
            # Emit the folder selection
            self.folder_selected.emit(self.selected_folder)

            self._check_ready_to_process()

    def _check_ready_to_process(self) -> None:
        # Enable process button only if both folder and request are provided
        has_folder = self.selected_folder is not None
        has_request = len(self.request_text.toPlainText().strip()) > 0
        self.process_btn.setEnabled(has_folder and has_request)

    def _start_processing(self) -> None:
        """Start processing documents with LangGraph."""
        if not self.selected_folder or not self.request_text.toPlainText().strip():
            return

        # Validate folder exists
        if not self.selected_folder.exists():
            QMessageBox.critical(
                self,
                "Folder Not Found",
                f"The selected folder no longer exists:\n{self.selected_folder}"
            )
            self.selected_folder = None
            self.folder_label.clear()
            self._check_ready_to_process()
            return

        try:
            # Disable buttons during processing
            self.process_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
            self.select_folder_btn.setEnabled(False)
            self.request_text.setReadOnly(True)

            # Emit signal to clear all tabs
            self.processing_started.emit()
            
            # Reset status panel and documents list
            self.status_panel.reset()
            self.processed_documents.clear()

            # Log start
            self.status_panel.add_log_entry(
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Starting processing of folder: {self.selected_folder}"
            )

            # Create and configure worker
            self.worker = ProcessingWorker(
                self.selected_folder, self.request_text.toPlainText().strip()
            )

            # Connect signals
            self.worker.progress_updated.connect(self.status_panel.update_progress)
            self.worker.document_processing.connect(self._on_document_processing)
            self.worker.document_processed.connect(self._on_document_processed)
            self.worker.processing_complete.connect(self._on_processing_complete)
            self.worker.error_occurred.connect(self._on_error)
            self.worker.stats_updated.connect(self.status_panel.update_statistics)

            # Start processing
            self.worker.start()
            
        except Exception as e:
            logger.error(f"Failed to start processing: {e}")
            self._on_error(f"Failed to start processing: {str(e)}")
            # Re-enable controls
            self.process_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
            self.select_folder_btn.setEnabled(True)
            self.request_text.setReadOnly(False)

    def _cancel_processing(self) -> None:
        """Cancel the current processing operation."""
        if self.worker:
            self.worker.cancel()
            self.status_panel.add_log_entry(
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Processing cancelled by user"
            )

    def _on_document_processing(self, filename: str) -> None:
        """Handle document processing signal.

        Args:
            filename: Name of the document being processed

        """
        self.status_panel.set_current_document(filename)
        self.status_panel.add_log_entry(
            f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Processing: {filename}"
        )

    def _on_document_processed(self, document: Document) -> None:
        """Handle document processed signal.

        Args:
            document: The processed document

        """
        self.processed_documents.append(document)

        # Log with classification
        if document.classification:
            confidence_str = (
                f"{document.confidence:.1%}"
                if document.confidence is not None
                else "N/A"
            )
            log_entry = (
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] "
                f"Classified {document.filename} as {document.classification.upper()} "
                f"(confidence: {confidence_str})"
            )
        else:
            log_entry = (
                f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] "
                f"Failed to classify {document.filename} - check API key"
            )
        self.status_panel.add_log_entry(log_entry)

    def _on_processing_complete(self) -> None:
        """Handle processing complete signal."""
        # Re-enable controls
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.select_folder_btn.setEnabled(True)
        self.request_text.setReadOnly(False)

        # Log completion
        self.status_panel.add_log_entry(
            f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Processing complete!"
        )

        # Emit documents for review
        if self.processed_documents:
            self.documents_processed.emit(self.processed_documents.copy())

        # Log completion summary to activity panel instead of showing alert
        stats = self.worker.stats if self.worker else {}
        self.status_panel.add_log_entry(
            f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] Processing complete! "
            f"Total: {stats.get('total', 0)}, "
            f"Responsive: {stats.get('responsive', 0)}, "
            f"Non-responsive: {stats.get('non_responsive', 0)}, "
            f"Uncertain: {stats.get('uncertain', 0)}, "
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
            f"[{datetime.now(timezone.utc).strftime(TIME_FORMAT)}] ERROR: {error_message}"
        )

        # Show error dialog
        QMessageBox.critical(
            self,
            "Processing Error",
            f"An error occurred during processing:\n\n{error_message}",
        )
