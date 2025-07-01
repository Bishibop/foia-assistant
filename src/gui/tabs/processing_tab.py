from datetime import UTC, datetime
from pathlib import Path

from PyQt6.QtCore import Qt
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
    SPLITTER_SIZES,
    SUPPORTED_FILE_EXTENSION,
    TIME_FORMAT,
)
from ...models.document import Document
from ...processing.worker import ProcessingWorker
from ..widgets.status_panel import StatusPanel


class ProcessingTab(QWidget):
    """Tab for document processing setup.

    Allows users to select a folder of documents and enter a FOIA request
    to process documents against. Provides controls to start the AI processing.
    """

    def __init__(self) -> None:
        super().__init__()
        self.selected_folder: Path | None = None
        self.worker: ProcessingWorker | None = None
        self.processed_documents: list[Document] = []
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(*MAIN_LAYOUT_MARGINS)

        # Title
        title = QLabel("Document Processing")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        title.setMaximumHeight(50)  # Fix the height
        main_layout.addWidget(title)

        # Create splitter for configuration and status
        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Horizontal)

        # Left side - Configuration
        config_widget = QWidget()
        config_layout = QVBoxLayout()
        config_layout.setContentsMargins(0, 0, 10, 0)

        # Folder selection section
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
        config_layout.addWidget(folder_group)

        # FOIA request section
        request_group = QGroupBox("FOIA Request")
        request_layout = QVBoxLayout()

        request_label = QLabel("Enter the FOIA request to process documents against:")
        request_layout.addWidget(request_label)

        self.request_text = QTextEdit()
        self.request_text.setPlaceholderText(
            "e.g., All emails and documents related to Project Blue Sky from January 2023 to December 2023"
        )
        self.request_text.setMaximumHeight(REQUEST_TEXT_MAX_HEIGHT)
        request_layout.addWidget(self.request_text)

        request_group.setLayout(request_layout)
        config_layout.addWidget(request_group)

        # Process buttons
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
        config_layout.addLayout(button_layout)

        # Add stretch to push everything to the top
        config_layout.addStretch()

        config_widget.setLayout(config_layout)
        splitter.addWidget(config_widget)

        # Right side - Status panel
        self.status_panel = StatusPanel()
        splitter.addWidget(self.status_panel)

        # Set initial splitter sizes (40% config, 60% status)
        splitter.setSizes(SPLITTER_SIZES)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        # Connect text change to enable/disable process button
        self.request_text.textChanged.connect(self._check_ready_to_process)

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
                f"[{datetime.now(UTC).strftime(TIME_FORMAT)}] "
                f"Selected folder: {self.selected_folder} "
                f"(found {len(txt_files)} .txt files)"
            )

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

        # Disable buttons during processing
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.select_folder_btn.setEnabled(False)
        self.request_text.setReadOnly(True)

        # Reset status panel and documents list
        self.status_panel.reset()
        self.processed_documents.clear()

        # Log start
        self.status_panel.add_log_entry(
            f"[{datetime.now(UTC).strftime(TIME_FORMAT)}] Starting processing of folder: {self.selected_folder}"
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

    def _cancel_processing(self) -> None:
        """Cancel the current processing operation."""
        if self.worker:
            self.worker.cancel()
            self.status_panel.add_log_entry(
                f"[{datetime.now(UTC).strftime(TIME_FORMAT)}] Processing cancelled by user"
            )

    def _on_document_processing(self, filename: str) -> None:
        """Handle document processing signal.

        Args:
            filename: Name of the document being processed

        """
        self.status_panel.set_current_document(filename)
        self.status_panel.add_log_entry(
            f"[{datetime.now(UTC).strftime(TIME_FORMAT)}] Processing: {filename}"
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
                f"[{datetime.now(UTC).strftime(TIME_FORMAT)}] "
                f"Classified {document.filename} as {document.classification.upper()} "
                f"(confidence: {confidence_str})"
            )
        else:
            log_entry = (
                f"[{datetime.now(UTC).strftime(TIME_FORMAT)}] "
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
            f"[{datetime.now(UTC).strftime(TIME_FORMAT)}] Processing complete!"
        )

        # Show summary
        stats = self.worker.stats if self.worker else {}
        QMessageBox.information(
            self,
            "Processing Complete",
            f"Processing complete!\n\n"
            f"Total documents: {stats.get('total', 0)}\n"
            f"Processed: {stats.get('processed', 0)}\n"
            f"Responsive: {stats.get('responsive', 0)}\n"
            f"Non-responsive: {stats.get('non_responsive', 0)}\n"
            f"Uncertain: {stats.get('uncertain', 0)}\n"
            f"Errors: {stats.get('errors', 0)}",
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
            f"[{datetime.now(UTC).strftime(TIME_FORMAT)}] ERROR: {error_message}"
        )

        # Show error dialog
        QMessageBox.critical(
            self,
            "Processing Error",
            f"An error occurred during processing:\n\n{error_message}",
        )
