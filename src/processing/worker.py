"""Background worker thread for LangGraph document processing."""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from ..constants import SUPPORTED_FILE_EXTENSION
from ..langgraph.workflow import get_compiled_workflow
from ..models.document import Document


class ProcessingWorker(QThread):
    """Background thread for processing documents with LangGraph.

    Emits signals to update the GUI with processing status and results.
    Handles document loading, classification, and exemption detection.
    """

    # Signals for communicating with GUI
    progress_updated = pyqtSignal(int, int)  # current, total
    document_processing = pyqtSignal(str)  # filename
    document_processed = pyqtSignal(Document)  # completed document
    processing_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)  # error message
    stats_updated = pyqtSignal(dict)  # classification statistics

    def __init__(self, folder_path: Path, foia_request: str) -> None:
        """Initialize the processing worker.

        Args:
            folder_path: Path to folder containing documents to process
            foia_request: The FOIA request text to process documents against

        """
        super().__init__()
        self.folder_path = folder_path
        self.foia_request = foia_request
        self.workflow = get_compiled_workflow()
        self._is_cancelled = False

        # Track statistics
        self.stats = {
            "total": 0,
            "processed": 0,
            "responsive": 0,
            "non_responsive": 0,
            "uncertain": 0,
            "errors": 0,
        }

    def cancel(self) -> None:
        """Cancel the processing operation."""
        self._is_cancelled = True

    def run(self) -> None:
        """Execute main processing loop in background thread."""
        try:
            # Get all text files in the folder
            txt_files = list(self.folder_path.glob(SUPPORTED_FILE_EXTENSION))
            self.stats["total"] = len(txt_files)

            if not txt_files:
                self.error_occurred.emit(f"No .txt files found in {self.folder_path}")
                return

            # Process each document
            for idx, file_path in enumerate(txt_files):
                if self._is_cancelled:
                    break

                # Emit progress update
                self.progress_updated.emit(idx, len(txt_files))
                self.document_processing.emit(file_path.name)

                try:
                    # Process document through LangGraph workflow
                    document = self._process_document(file_path)

                    # Update statistics
                    self.stats["processed"] += 1
                    if document.classification == "responsive":
                        self.stats["responsive"] += 1
                    elif document.classification == "non_responsive":
                        self.stats["non_responsive"] += 1
                    else:
                        self.stats["uncertain"] += 1

                    # Emit results
                    self.document_processed.emit(document)
                    self.stats_updated.emit(self.stats.copy())

                except Exception as e:
                    self.stats["errors"] += 1
                    self.error_occurred.emit(
                        f"Error processing {file_path.name}: {e!s}"
                    )

            # Final progress update
            self.progress_updated.emit(len(txt_files), len(txt_files))
            self.processing_complete.emit()

        except Exception as e:
            self.error_occurred.emit(f"Processing failed: {e!s}")

    def _process_document(self, file_path: Path) -> Document:
        """Process a single document through the LangGraph workflow.

        Args:
            file_path: Path to the document file

        Returns:
            Processed Document object with classification and analysis

        """
        # Read file content
        content = file_path.read_text(encoding="utf-8")

        # Import the state creation function from workflow
        from ..langgraph.workflow import create_initial_state

        # Create initial state with content
        initial_state = create_initial_state(file_path.name, self.foia_request)
        initial_state["content"] = content  # Add the content we already read

        # Run through workflow
        final_state = self.workflow.invoke(initial_state)

        # Create Document object from final state
        document = Document(
            filename=final_state["filename"],
            content=final_state["content"],
            classification=final_state["classification"],
            confidence=final_state["confidence"],
            justification=final_state["justification"],
            exemptions=final_state.get("exemptions", []),
        )

        return document
