"""Parallel processing for embedding generation and duplicate detection."""

import logging
import multiprocessing as mp
import time
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
from typing import Any

from src.models.document import Document
from src.services.embedding_service import EmbeddingService
from src.services.embedding_store import EmbeddingStore

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingTask:
    """Represents a single embedding generation task."""
    task_id: int
    document_path: Path
    request_id: str


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    task_id: int
    filename: str | None = None
    content: str | None = None
    embedding: list[float] | None = None
    content_hash: str | None = None
    document: Document | None = None  # Added back for the main process to set
    error: str | None = None
    processing_time: float = 0.0


class ParallelEmbeddingProcessor:
    """Handles parallel embedding generation for documents."""

    def __init__(self, num_workers: int | None = None) -> None:
        """Initialize the parallel processor.
        
        Args:
            num_workers: Number of worker processes (defaults to min(4, CPU count - 1))
        """
        self.num_workers = num_workers or min(4, max(1, mp.cpu_count() - 1))
        self._start_time: float | None = None
        self._documents_processed = 0
        self._total_documents = 0
        self._progress_callback: Any = None
        self._error_callback: Any = None
        self._document_callback: Any = None

    def set_progress_callback(self, callback: Any) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback

    def set_error_callback(self, callback: Any) -> None:
        """Set callback for error notifications."""
        self._error_callback = callback

    def set_document_callback(self, callback: Any) -> None:
        """Set callback for completed documents."""
        self._document_callback = callback

    def process_embeddings(
        self, 
        document_paths: list[Path], 
        request_id: str,
        embedding_store: EmbeddingStore
    ) -> dict[Path, Document]:
        """Process embeddings for multiple documents in parallel.
        
        Args:
            document_paths: List of document paths to process
            request_id: The request ID for duplicate detection scope
            embedding_store: The embedding store instance
            
        Returns:
            Dictionary mapping paths to Document objects with embedding metadata
        """
        self._start_time = time.time()
        self._total_documents = len(document_paths)
        self._documents_processed = 0

        # Create tasks
        tasks = [
            EmbeddingTask(
                task_id=idx,
                document_path=path,
                request_id=request_id
            )
            for idx, path in enumerate(document_paths)
        ]

        # Create batches for workers
        batch_size = max(1, len(tasks) // (self.num_workers * 4))
        batches = [
            tasks[i:i + batch_size]
            for i in range(0, len(tasks), batch_size)
        ]

        # Process batches in parallel
        results = self._process_batches(batches, embedding_store)

        # Convert results to document metadata dictionary
        doc_metadata = {}
        
        for result in results:
            if result.document:
                # Map back to original file path using task_id
                doc_path = tasks[result.task_id].document_path
                doc_metadata[doc_path] = result.document

        return doc_metadata

    def _process_batches(
        self, 
        batches: list[list[EmbeddingTask]], 
        embedding_store: EmbeddingStore
    ) -> list[EmbeddingResult]:
        """Process batches of documents using worker pool."""
        # Create queues for communication
        task_queue: Queue = mp.Queue()
        result_queue: Queue = mp.Queue()

        # Start worker processes
        workers = []
        for _ in range(self.num_workers):
            worker = mp.Process(
                target=process_embedding_batch,
                args=(task_queue, result_queue)
            )
            worker.start()
            workers.append(worker)

        # Submit batches to queue (no need to send embedding store anymore)
        for batch in batches:
            task_queue.put(batch)

        # Signal workers to stop when done
        for _ in range(self.num_workers):
            task_queue.put(None)

        # Collect results and perform duplicate detection in real-time
        results = []
        expected_results = sum(len(batch) for batch in batches)
        request_id = batches[0][0].request_id if batches and batches[0] else ""

        while len(results) < expected_results:
            try:
                result = result_queue.get(timeout=1.0)
                
                # Perform duplicate detection in main process
                if not result.error and result.content_hash:
                    # Check for exact duplicate first
                    exact_match = embedding_store.find_exact(request_id, result.content_hash)
                    if exact_match:
                        # Create document as exact duplicate
                        document = Document(
                            filename=result.filename,
                            content=result.content,
                            content_hash=result.content_hash,
                            is_duplicate=True,
                            duplicate_of=exact_match,
                            similarity_score=1.0,
                            embedding_generated=False
                        )
                    elif result.embedding:
                        # Check for similar documents
                        similar_docs = embedding_store.find_similar(
                            request_id, result.embedding, threshold=0.85
                        )
                        
                        if similar_docs:
                            # Near duplicate found
                            document = Document(
                                filename=result.filename,
                                content=result.content,
                                content_hash=result.content_hash,
                                is_duplicate=True,
                                duplicate_of=similar_docs[0][0],
                                similarity_score=similar_docs[0][1],
                                embedding_generated=True
                            )
                        else:
                            # Original document
                            document = Document(
                                filename=result.filename,
                                content=result.content,
                                content_hash=result.content_hash,
                                is_duplicate=False,
                                embedding_generated=True
                            )
                        
                        # Store embedding for future comparisons
                        embedding_store.add_embedding(
                            request_id, result.filename, 
                            result.embedding, result.content_hash
                        )
                    else:
                        # No embedding generated
                        document = Document(
                            filename=result.filename,
                            content=result.content,
                            content_hash=result.content_hash,
                            is_duplicate=False,
                            embedding_generated=False
                        )
                    
                    # Add document to result
                    result.document = document
                    
                    # Notify about completed document
                    if self._document_callback:
                        self._document_callback(document)
                
                results.append(result)
                self._documents_processed += 1

                # Update progress
                if self._progress_callback:
                    self._progress_callback(
                        self._documents_processed, self._total_documents
                    )
                    
            except Empty:
                # Check if any workers died
                for worker in workers:
                    if not worker.is_alive() and worker.exitcode != 0:
                        if self._error_callback:
                            self._error_callback(
                                f"Worker process died with exit code {worker.exitcode}"
                            )

        # Wait for workers to finish
        for worker in workers:
            worker.join(timeout=5.0)
            if worker.is_alive():
                worker.terminate()
                worker.join()

        return results

    def get_processing_rate(self) -> float:
        """Get the current processing rate in documents per minute."""
        if not self._start_time or self._documents_processed == 0:
            return 0.0

        elapsed_time = time.time() - self._start_time
        if elapsed_time == 0:
            return 0.0

        return (self._documents_processed / elapsed_time) * 60


def process_embedding_batch(
    task_queue: Queue,
    result_queue: Queue,
) -> None:
    """Worker function to generate embeddings only.
    
    Args:
        task_queue: Queue to receive processing tasks
        result_queue: Queue to send results
    """
    # Create embedding service in worker process
    embedding_service = EmbeddingService()
    
    # Set process title for monitoring
    try:
        import setproctitle
        setproctitle.setproctitle("foia-embedding-worker")
    except ImportError:
        pass

    while True:
        try:
            # Get next batch
            batch = task_queue.get(timeout=1.0)
            if batch is None:
                # Sentinel value - time to stop
                break

            # Process each document in the batch
            for task in batch:
                start_time = time.time()
                try:
                    # Read document content
                    content = task.document_path.read_text(encoding="utf-8")
                    
                    # Generate content hash
                    content_hash = embedding_service.generate_content_hash(content)
                    
                    # Generate embedding
                    embedding = embedding_service.generate_embedding(content)
                    
                    processing_time = time.time() - start_time
                    result = EmbeddingResult(
                        task_id=task.task_id,
                        filename=task.document_path.name,
                        content=content,
                        embedding=embedding,
                        content_hash=content_hash,
                        processing_time=processing_time
                    )

                except Exception as e:
                    processing_time = time.time() - start_time
                    result = EmbeddingResult(
                        task_id=task.task_id,
                        filename=task.document_path.name,
                        error=str(e),
                        processing_time=processing_time
                    )

                result_queue.put(result)

        except Empty:
            continue
        except Exception as e:
            # Critical error - log and continue
            logger.error(f"Embedding worker error: {e}")
            continue