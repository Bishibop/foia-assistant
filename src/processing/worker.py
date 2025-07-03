"""Background worker thread for LangGraph document processing."""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from ..constants import SUPPORTED_FILE_EXTENSION
from ..langgraph.workflow import get_compiled_workflow
from ..models.document import Document
from .parallel_worker import ParallelDocumentProcessor


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
    processing_rate_updated = pyqtSignal(float)  # docs per minute
    worker_count_updated = pyqtSignal(int)  # number of active workers

    def __init__(
        self, folder_path: Path, foia_request: str, use_parallel: bool = True
    ) -> None:
        """Initialize the processing worker.

        Args:
            folder_path: Path to folder containing documents to process
            foia_request: The FOIA request text to process documents against
            use_parallel: Whether to use parallel processing (default: True)

        """
        super().__init__()
        self.folder_path = folder_path
        self.foia_request = foia_request
        self.workflow = get_compiled_workflow()
        self._is_cancelled = False
        self.use_parallel = use_parallel

        # Track statistics
        self.stats = {
            "total": 0,
            "processed": 0,
            "responsive": 0,
            "non_responsive": 0,
            "uncertain": 0,
            "errors": 0,
        }

        # Parallel processor (created when needed)
        self._parallel_processor: ParallelDocumentProcessor | None = None

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

            if self.use_parallel and len(txt_files) > 3:
                # Use parallel processing for 4+ documents
                self._process_parallel(txt_files)
            else:
                # Use sequential processing for small batches
                self._process_sequential(txt_files)

            # Final progress update
            self.progress_updated.emit(len(txt_files), len(txt_files))
            self.processing_complete.emit()

        except Exception as e:
            self.error_occurred.emit(f"Processing failed: {e!s}")

    def _process_sequential(self, txt_files: list[Path]) -> None:
        """Process documents sequentially (original implementation)."""
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
                self.error_occurred.emit(f"Error processing {file_path.name}: {e!s}")

    def _process_parallel(self, txt_files: list[Path]) -> None:
        """Process documents in parallel using multiple workers."""
        # Create parallel processor (workflow created in each worker)
        self._parallel_processor = ParallelDocumentProcessor()

        # Emit worker count
        self.worker_count_updated.emit(self._parallel_processor.num_workers)

        # Set up callbacks
        def update_progress(current: int, total: int) -> None:
            """Update progress and statistics."""
            self.progress_updated.emit(current, total)
            self.stats["processed"] = current
            self.stats_updated.emit(self.stats.copy())

            # Update processing rate
            rate = self._parallel_processor.get_processing_rate()
            if rate > 0:
                self.processing_rate_updated.emit(rate)

        def handle_error(error: str) -> None:
            """Handle processing errors."""
            self.stats["errors"] += 1
            self.error_occurred.emit(error)
        
        def handle_document(document: Document) -> None:
            """Handle completed document."""
            # Update statistics
            if document.classification == "responsive":
                self.stats["responsive"] += 1
            elif document.classification == "non_responsive":
                self.stats["non_responsive"] += 1
            else:
                self.stats["uncertain"] += 1
            
            # Emit document and updated stats
            self.document_processed.emit(document)
            self.stats_updated.emit(self.stats.copy())

        self._parallel_processor.set_progress_callback(update_progress)
        self._parallel_processor.set_error_callback(handle_error)
        self._parallel_processor.set_document_callback(handle_document)

        # Process documents
        documents = self._parallel_processor.process_documents(
            txt_files, self.foia_request
        )
        
        # Documents are already emitted via callback as they complete
        # Just do a final stats update to ensure everything is synced
        self.stats_updated.emit(self.stats.copy())

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
