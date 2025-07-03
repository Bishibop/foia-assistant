"""Background worker thread for LangGraph document processing."""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QThread, pyqtSignal

from ..constants import SUPPORTED_FILE_EXTENSION
from ..langgraph.workflow import get_compiled_workflow
from ..models.document import Document
from ..services.embedding_service import EmbeddingService
from ..services.embedding_store import EmbeddingStore
from .parallel_embeddings import ParallelEmbeddingProcessor
from .parallel_worker import ParallelDocumentProcessor

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .feedback_manager import FeedbackManager


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

    # New signals for embedding progress
    embedding_progress = pyqtSignal(int, int)  # current, total
    duplicates_found = pyqtSignal(int)  # count
    status_updated = pyqtSignal(str)  # status message
    embedding_worker_count = pyqtSignal(int)  # number of embedding workers
    embedding_rate_updated = pyqtSignal(float)  # embedding processing rate

    def __init__(
        self,
        folder_path: Path,
        foia_request: str,
        use_parallel: bool = True,
        request_id: str | None = None,
        feedback_manager: "FeedbackManager | None" = None,
        file_list: list[Path] | None = None,
        embedding_store: EmbeddingStore | None = None
    ) -> None:
        """Initialize the processing worker.

        Args:
            folder_path: Path to folder containing documents to process
            foia_request: The FOIA request text to process documents against
            use_parallel: Whether to use parallel processing (default: True)
            request_id: The FOIA request ID for feedback tracking
            feedback_manager: Manager for handling user feedback/corrections
            file_list: Optional specific list of files to process (overrides folder scan)
            embedding_store: Store for document embeddings and duplicate detection

        """
        super().__init__()
        self.folder_path = folder_path
        self.foia_request = foia_request
        self.workflow = get_compiled_workflow()
        self._is_cancelled = False
        self.use_parallel = use_parallel
        self.request_id = request_id
        self.feedback_manager = feedback_manager
        self.file_list = file_list  # Optional specific file list
        self.embedding_store = embedding_store
        self.embedding_service = EmbeddingService()

        # Document metadata storage for two-phase processing
        self._document_metadata: dict[Path, Document] = {}

        # Track statistics
        self.stats = {
            "total": 0,
            "processed": 0,
            "responsive": 0,
            "non_responsive": 0,
            "uncertain": 0,
            "duplicates": 0,
            "errors": 0,
        }

        # Parallel processor (created when needed)
        self._parallel_processor: ParallelDocumentProcessor | None = None

        # Get feedback examples if available
        self.feedback_examples = []
        if self.feedback_manager and self.request_id:
            self.feedback_examples = self.feedback_manager.get_all_feedback(self.request_id)

    def cancel(self) -> None:
        """Cancel the processing operation."""
        self._is_cancelled = True

    def run(self) -> None:
        """Execute main processing loop in background thread."""
        try:
            # Use provided file list or scan folder
            if self.file_list is not None:
                txt_files = self.file_list
            else:
                # Get all text files in the folder
                txt_files = list(self.folder_path.glob(SUPPORTED_FILE_EXTENSION))

            self.stats["total"] = len(txt_files)

            if not txt_files:
                self.error_occurred.emit(f"No .txt files found in {self.folder_path}")
                return

            # Phase 1: Generate embeddings and detect duplicates (if embedding store provided)
            if self.embedding_store and self.request_id:
                self._generate_embeddings_phase(txt_files)

            # Calculate the number of documents that need classification (total - duplicates)
            non_duplicate_count = len(txt_files) - self.stats.get("duplicates", 0)
            
            # Phase 2: Process documents through classification workflow
            if self.use_parallel and len(txt_files) > 3:
                # Use parallel processing for 4+ documents
                self._process_parallel(txt_files)
            else:
                # Use sequential processing for small batches
                self._process_sequential(txt_files)

            # Final progress update - use non-duplicate count
            self.progress_updated.emit(non_duplicate_count, non_duplicate_count)
            self.processing_complete.emit()

        except Exception as e:
            self.error_occurred.emit(f"Processing failed: {e!s}")

    def _generate_embeddings_phase(self, txt_files: list[Path]) -> None:
        """Generate embeddings for all documents and mark duplicates.
        
        Args:
            txt_files: List of document paths to process

        """
        # Choose between parallel and sequential processing based on file count
        if len(txt_files) > 5:  # Use parallel for more than 5 files
            self._generate_embeddings_parallel(txt_files)
        else:
            self._generate_embeddings_sequential(txt_files)

    def _generate_embeddings_sequential(self, txt_files: list[Path]) -> None:
        """Generate embeddings sequentially (for small file sets)."""
        duplicate_count = 0

        for idx, doc_path in enumerate(txt_files):
            if self._is_cancelled:
                break

            # Update progress
            self.status_updated.emit(f"Generating embeddings... ({idx+1}/{len(txt_files)})")
            self.embedding_progress.emit(idx + 1, len(txt_files))

            try:
                # Load content
                content = doc_path.read_text(encoding='utf-8')
                content_hash = self.embedding_service.generate_content_hash(content)

                # Check for exact duplicate first
                exact_match = self.embedding_store.find_exact(
                    self.request_id, content_hash
                )

                if exact_match:
                    # Mark as exact duplicate
                    doc = Document(
                        filename=doc_path.name,
                        content=content,
                        content_hash=content_hash,
                        is_duplicate=True,
                        duplicate_of=exact_match,
                        similarity_score=1.0
                    )
                    duplicate_count += 1
                    self.stats["duplicates"] = duplicate_count
                    self.stats_updated.emit(self.stats.copy())
                else:
                    # Generate embedding for similarity check
                    embedding = self.embedding_service.generate_embedding(content)

                    if embedding:
                        # Check for near-duplicates
                        similar_docs = self.embedding_store.find_similar(
                            self.request_id, embedding, threshold=0.85
                        )

                        if similar_docs:
                            # Mark as near-duplicate
                            doc = Document(
                                filename=doc_path.name,
                                content=content,
                                content_hash=content_hash,
                                is_duplicate=True,
                                duplicate_of=similar_docs[0][0],
                                similarity_score=similar_docs[0][1],
                                embedding_generated=True
                            )
                            duplicate_count += 1
                            self.stats["duplicates"] = duplicate_count
                            self.stats_updated.emit(self.stats.copy())
                        else:
                            # Original document
                            doc = Document(
                                filename=doc_path.name,
                                content=content,
                                content_hash=content_hash,
                                is_duplicate=False,
                                embedding_generated=True
                            )

                        # Store embedding
                        self.embedding_store.add_embedding(
                            self.request_id, doc_path.name, embedding, content_hash
                        )
                    else:
                        # Failed to generate embedding, treat as original
                        doc = Document(
                            filename=doc_path.name,
                            content=content,
                            content_hash=content_hash,
                            is_duplicate=False,
                            embedding_generated=False
                        )

                # Store document metadata for processing phase
                self._document_metadata[doc_path] = doc

            except Exception as e:
                logger.error(f"Error generating embedding for {doc_path.name}: {e}")
                # Create basic document without embedding
                doc = Document(
                    filename=doc_path.name,
                    content="",
                    is_duplicate=False,
                    embedding_generated=False
                )
                self._document_metadata[doc_path] = doc

        # Emit final duplicate count and stats
        self.duplicates_found.emit(duplicate_count)
        self.stats["duplicates"] = duplicate_count
        self.stats_updated.emit(self.stats.copy())
        self.status_updated.emit(f"Embeddings complete. Duplicates found: {duplicate_count}")

    def _generate_embeddings_parallel(self, txt_files: list[Path]) -> None:
        """Generate embeddings in parallel using multiple workers."""
        self.status_updated.emit("Starting parallel embedding generation...")
        
        # Create parallel processor
        parallel_processor = ParallelEmbeddingProcessor()
        
        # Emit worker count
        self.embedding_worker_count.emit(parallel_processor.num_workers)
        
        # Track duplicate count
        duplicate_count = 0
        
        # Set up callbacks
        def update_progress(current: int, total: int) -> None:
            """Update embedding progress."""
            self.embedding_progress.emit(current, total)
            self.status_updated.emit(f"Generating embeddings... ({current}/{total})")
            
            # Update processing rate
            rate = parallel_processor.get_processing_rate()
            if rate > 0:
                self.embedding_rate_updated.emit(rate)
        
        def handle_error(error: str) -> None:
            """Handle embedding errors."""
            logger.error(f"Embedding error: {error}")
        
        def handle_document(document: Document) -> None:
            """Handle completed embedding."""
            nonlocal duplicate_count
            if document.is_duplicate:
                duplicate_count += 1
                # Update stats and emit in real-time
                self.stats["duplicates"] = duplicate_count
                self.stats_updated.emit(self.stats.copy())
                # Also emit specific duplicate count
                self.duplicates_found.emit(duplicate_count)
        
        parallel_processor.set_progress_callback(update_progress)
        parallel_processor.set_error_callback(handle_error)
        parallel_processor.set_document_callback(handle_document)
        
        # Process embeddings in parallel
        self._document_metadata = parallel_processor.process_embeddings(
            txt_files, self.request_id, self.embedding_store
        )
        
        # Emit final counts
        self.duplicates_found.emit(duplicate_count)
        self.stats["duplicates"] = duplicate_count
        self.stats_updated.emit(self.stats.copy())
        self.status_updated.emit(f"Embeddings complete. Duplicates found: {duplicate_count}")

    def _process_sequential(self, txt_files: list[Path]) -> None:
        """Process documents sequentially (original implementation)."""
        # Calculate adjusted total (excluding duplicates)
        duplicate_count = self.stats.get("duplicates", 0)
        adjusted_total = len(txt_files) - duplicate_count
        non_duplicate_processed = 0
        
        for idx, file_path in enumerate(txt_files):
            if self._is_cancelled:
                break

            # Check if this is a duplicate before processing
            is_duplicate = False
            if file_path in self._document_metadata:
                is_duplicate = self._document_metadata[file_path].is_duplicate
            
            # Emit progress update using adjusted counts
            if not is_duplicate:
                self.progress_updated.emit(non_duplicate_processed, adjusted_total)
            
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
                elif document.classification == "duplicate":
                    # Don't increment duplicates here - already counted during embedding phase
                    pass
                else:
                    self.stats["uncertain"] += 1

                # Increment non-duplicate counter if not a duplicate
                if document.classification != "duplicate":
                    non_duplicate_processed += 1

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

        # Pass embedding metadata if available
        embedding_metadata = self._document_metadata if self._document_metadata else None

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
            elif document.classification == "duplicate":
                # Don't increment duplicates here - already counted during embedding phase
                pass
            else:
                self.stats["uncertain"] += 1

            # Emit document and updated stats
            self.document_processed.emit(document)
            self.stats_updated.emit(self.stats.copy())

        self._parallel_processor.set_progress_callback(update_progress)
        self._parallel_processor.set_error_callback(handle_error)
        self._parallel_processor.set_document_callback(handle_document)

        # Process documents with feedback examples and embedding metadata
        self._parallel_processor.process_documents(
            txt_files, self.foia_request, self.feedback_examples, embedding_metadata
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
        # Check if we have pre-computed metadata from embeddings phase
        if file_path in self._document_metadata:
            doc_metadata = self._document_metadata[file_path]
            content = doc_metadata.content
        else:
            # Read file content if not already loaded
            content = file_path.read_text(encoding="utf-8")
            doc_metadata = None

        # Import the state creation function from workflow
        from ..langgraph.workflow import create_initial_state

        # Create initial state with content
        initial_state = create_initial_state(file_path.name, self.foia_request)
        initial_state["content"] = content  # Add the content we already read
        initial_state["feedback_examples"] = self.feedback_examples  # Add feedback examples
        
        # Add duplicate metadata if available
        if doc_metadata:
            initial_state["is_duplicate"] = doc_metadata.is_duplicate
            initial_state["duplicate_of"] = doc_metadata.duplicate_of
            initial_state["similarity_score"] = doc_metadata.similarity_score
            initial_state["content_hash"] = doc_metadata.content_hash
            initial_state["embedding_generated"] = doc_metadata.embedding_generated

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

        # Add duplicate detection metadata if available
        if doc_metadata:
            document.is_duplicate = doc_metadata.is_duplicate
            document.duplicate_of = doc_metadata.duplicate_of
            document.similarity_score = doc_metadata.similarity_score
            document.content_hash = doc_metadata.content_hash
            document.embedding_generated = doc_metadata.embedding_generated

        return document
