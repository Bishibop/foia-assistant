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
    from .audit_manager import AuditManager
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
        embedding_store: EmbeddingStore | None = None,
        audit_manager: "AuditManager | None" = None
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
            audit_manager: Manager for audit trail logging

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
        self.audit_manager = audit_manager
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

            # Phase 2: Process documents through classification workflow
            if self.use_parallel and len(txt_files) > 3:
                # Use parallel processing for 4+ documents
                logger.info(f"🔍 WORKER: Using PARALLEL processing for {len(txt_files)} documents")
                self._process_parallel(txt_files)
            else:
                # Use sequential processing for small batches
                logger.info(f"🔍 WORKER: Using SEQUENTIAL processing for {len(txt_files)} documents")
                self._process_sequential(txt_files)

            # Calculate the final non-duplicate count AFTER processing
            # (in case duplicate count was updated during processing)
            final_non_duplicate_count = len(txt_files) - self.stats.get("duplicates", 0)
            
            # Final progress update - use correct count
            self.progress_updated.emit(final_non_duplicate_count, final_non_duplicate_count)
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
            logger.info(f"🔍 WORKER: Using PARALLEL embedding generation for {len(txt_files)} documents")
            self._generate_embeddings_parallel(txt_files)
        else:
            logger.info(f"🔍 WORKER: Using SEQUENTIAL embedding generation for {len(txt_files)} documents")
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
                    
                    # Log exact duplicate detection to audit trail
                    if self.audit_manager:
                        self.audit_manager.log_duplicate(
                            filename=doc_path.name,
                            request_id=self.request_id,
                            is_duplicate=True,
                            duplicate_of=exact_match,
                            similarity_score=1.0
                        )
                else:
                    # Generate embedding for similarity check
                    embedding = self.embedding_service.generate_embedding(content)

                    # Log embedding generation to audit trail
                    if self.audit_manager:
                        self.audit_manager.log_embedding(
                            filename=doc_path.name,
                            request_id=self.request_id,
                            success=embedding is not None
                        )

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
                            
                            # Log duplicate detection to audit trail
                            if self.audit_manager:
                                self.audit_manager.log_duplicate(
                                    filename=doc_path.name,
                                    request_id=self.request_id,
                                    is_duplicate=True,
                                    duplicate_of=similar_docs[0][0],
                                    similarity_score=similar_docs[0][1]
                                )
                        else:
                            # Original document
                            doc = Document(
                                filename=doc_path.name,
                                content=content,
                                content_hash=content_hash,
                                is_duplicate=False,
                                embedding_generated=True
                            )
                            
                            # Log as original document
                            if self.audit_manager:
                                self.audit_manager.log_duplicate(
                                    filename=doc_path.name,
                                    request_id=self.request_id,
                                    is_duplicate=False
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
        
        # Log embedding events to audit trail (since parallel processor doesn't have audit support yet)
        if self.audit_manager and self.request_id:
            logger.info(f"🔍 WORKER: Adding audit entries for {len(self._document_metadata)} embedding results")
            for doc_path, document in self._document_metadata.items():
                self.audit_manager.log_embedding(
                    filename=doc_path.name,
                    request_id=self.request_id,
                    success=document.embedding_generated if document.embedding_generated is not None else True
                )
                
                # Also log duplicate detection results
                self.audit_manager.log_duplicate(
                    filename=doc_path.name,
                    request_id=self.request_id,
                    is_duplicate=document.is_duplicate,
                    duplicate_of=document.duplicate_of,
                    similarity_score=document.similarity_score
                )
        
        # Emit final counts
        self.duplicates_found.emit(duplicate_count)
        self.stats["duplicates"] = duplicate_count
        self.stats_updated.emit(self.stats.copy())
        self.status_updated.emit(f"Embeddings complete. Duplicates found: {duplicate_count}")

    def _process_sequential(self, txt_files: list[Path]) -> None:
        """Process documents sequentially (original implementation)."""
        # Reset duplicate count for reprocessing
        if self.feedback_examples:
            self.duplicates_found.emit(0)
            self.stats["duplicates"] = 0
            self.stats_updated.emit(self.stats.copy())
            
        # Calculate adjusted total (excluding duplicates)
        duplicate_count = self.stats.get("duplicates", 0)
        adjusted_total = len(txt_files) - duplicate_count
        non_duplicate_processed = 0
        
        for idx, file_path in enumerate(txt_files):
            if self._is_cancelled:
                break

            # Check if this is a duplicate before processing
            # But skip duplicate checking during reprocessing with feedback
            is_duplicate = False
            if file_path in self._document_metadata and not self.feedback_examples:
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

        # Reset duplicate count for reprocessing
        if self.feedback_examples:
            self.duplicates_found.emit(0)
            self.stats["duplicates"] = 0
            self.stats_updated.emit(self.stats.copy())

        # Emit worker count
        self.worker_count_updated.emit(self._parallel_processor.num_workers)

        # Pass embedding metadata if available, but NOT during reprocessing with feedback
        # When reprocessing, we don't want to carry over old duplicate flags
        if self.feedback_examples:
            # This is reprocessing with feedback - don't use old metadata
            embedding_metadata = None
        else:
            # Normal processing - use metadata if available
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

        def handle_audit_events(audit_events) -> None:
            """Handle audit events from parallel processing."""
            logger.info(f"🔍 WORKER: handle_audit_events called with {len(audit_events)} events")
            if self.audit_manager:
                for event in audit_events:
                    logger.info(f"🔍 WORKER: Processing audit event {event.event_type} for {event.filename}")
                    if event.event_type == "classification":
                        self.audit_manager.log_classification(
                            filename=event.filename,
                            result=event.details["result"],
                            confidence=event.details["confidence"],
                            request_id=event.request_id
                        )
                        logger.info(f"🔍 WORKER: Logged classification to audit manager")
                    elif event.event_type == "error":
                        self.audit_manager.log_error(
                            filename=event.filename,
                            error_message=event.details["error_message"],
                            request_id=event.request_id
                        )
                        logger.info(f"🔍 WORKER: Logged error to audit manager")
            else:
                logger.warning(f"🔍 WORKER: No audit_manager available!")

        self._parallel_processor.set_progress_callback(update_progress)
        self._parallel_processor.set_error_callback(handle_error)
        self._parallel_processor.set_document_callback(handle_document)
        self._parallel_processor.set_audit_callback(handle_audit_events)

        # Process documents with feedback examples and embedding metadata
        self._parallel_processor.process_documents(
            txt_files, self.foia_request, self.feedback_examples, embedding_metadata, self.request_id
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
        # But don't use old metadata during reprocessing with feedback
        if file_path in self._document_metadata and not self.feedback_examples:
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
        initial_state["audit_manager"] = self.audit_manager  # Add audit manager for logging
        initial_state["request_id"] = self.request_id  # Add request ID for audit logging
        
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
