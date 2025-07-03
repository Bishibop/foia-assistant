"""Parallel document processing module for improved performance."""

import multiprocessing as mp
import time
from collections.abc import Callable
from dataclasses import dataclass
from multiprocessing import Queue
from pathlib import Path
from queue import Empty
from typing import Any

from src.models.document import Document


@dataclass
class ProcessingTask:
    """Represents a document processing task."""

    document_path: Path
    foia_request: str
    task_id: int


@dataclass
class ProcessingResult:
    """Represents the result of a document processing task."""

    task_id: int
    document: Document | None = None
    error: str | None = None
    processing_time: float = 0.0


class ParallelDocumentProcessor:
    """Manages parallel processing of documents using multiprocessing."""

    def __init__(
        self,
        num_workers: int | None = None,
        batch_size: int | None = None,
    ) -> None:
        """Initialize the parallel processor.

        Args:
            num_workers: Number of worker processes (defaults to min(4, CPU count - 1))
            batch_size: Maximum documents per batch (defaults to dynamic)

        """
        self.num_workers = num_workers or min(4, max(1, mp.cpu_count() - 1))
        self.batch_size = batch_size
        self._progress_callback: Callable[[int, int], None] | None = None
        self._error_callback: Callable[[str], None] | None = None
        self._document_callback: Callable[[Document], None] | None = None
        self._documents_processed = 0
        self._total_documents = 0
        self._start_time: float | None = None

    def set_progress_callback(self, callback: Callable[[int, int], None]) -> None:
        """Set the progress callback function."""
        self._progress_callback = callback

    def set_error_callback(self, callback: Callable[[str], None]) -> None:
        """Set the error callback function."""
        self._error_callback = callback
    
    def set_document_callback(self, callback: Callable[[Document], None]) -> None:
        """Set the document completion callback function."""
        self._document_callback = callback

    def process_documents(
        self, document_paths: list[Path], foia_request: str
    ) -> list[Document]:
        """Process multiple documents in parallel.

        Args:
            document_paths: List of document paths to process
            foia_request: The FOIA request text for context

        Returns:
            List of processed Document objects

        """
        self._documents_processed = 0
        self._total_documents = len(document_paths)
        self._start_time = time.time()

        # Create processing tasks
        tasks = [
            ProcessingTask(document_path=path, foia_request=foia_request, task_id=idx)
            for idx, path in enumerate(document_paths)
        ]

        # Create batches (batch size will be determined automatically if not set)
        batches = self._create_batches(tasks)

        # Process batches in parallel
        results = self._process_batches(batches)

        # Sort results by original order and extract documents
        results.sort(key=lambda r: r.task_id)
        documents = []
        for result in results:
            if result.document:
                documents.append(result.document)
            elif result.error and self._error_callback:
                self._error_callback(
                    f"Error processing document {result.task_id}: {result.error}"
                )

        return documents

    def _calculate_optimal_batch_size(self, total_tasks: int) -> int:
        """Calculate optimal batch size based on number of tasks and workers."""
        if total_tasks <= self.num_workers:
            return 1
        elif total_tasks <= self.num_workers * 4:
            return 2
        else:
            # Aim for roughly equal distribution with some overhead
            return max(1, total_tasks // (self.num_workers * 4))

    def _create_batches(
        self, tasks: list[ProcessingTask]
    ) -> list[list[ProcessingTask]]:
        """Divide tasks into batches for processing."""
        batch_size = self.batch_size or self._calculate_optimal_batch_size(len(tasks))
        batches = []
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i : i + batch_size]
            batches.append(batch)
        return batches

    def _process_batches(
        self, batches: list[list[ProcessingTask]]
    ) -> list[ProcessingResult]:
        """Process batches of documents using worker pool."""
        # Create queues for communication
        task_queue: Queue = mp.Queue()  # type: ignore
        result_queue: Queue = mp.Queue()  # type: ignore

        # Start worker processes
        workers = []
        for _ in range(self.num_workers):
            worker = mp.Process(
                target=process_document_batch,
                args=(
                    None,
                    task_queue,
                    result_queue,
                ),  # Pass None, workflow created in worker
            )
            worker.start()
            workers.append(worker)

        # Submit batches to queue
        for batch in batches:
            task_queue.put(batch)

        # Signal workers to stop when done
        for _ in range(self.num_workers):
            task_queue.put(None)

        # Collect results
        results = []
        expected_results = sum(len(batch) for batch in batches)

        while len(results) < expected_results:
            try:
                result = result_queue.get(timeout=1.0)
                results.append(result)
                self._documents_processed += 1

                # Update progress
                if self._progress_callback:
                    self._progress_callback(
                        self._documents_processed, self._total_documents
                    )
                
                # Notify about completed document immediately
                if result.document and self._document_callback:
                    self._document_callback(result.document)
            except Empty:
                # Check if any workers died
                for worker in workers:
                    if (
                        not worker.is_alive()
                        and worker.exitcode != 0
                        and self._error_callback
                    ):
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


def process_document_batch(
    workflow_factory: Any,  # This will be None, we'll create workflow in worker
    task_queue: Queue,
    result_queue: Queue,
) -> None:
    """Worker function to process batches of documents.

    Args:
        workflow_factory: Not used, kept for compatibility
        task_queue: Queue to receive processing tasks
        result_queue: Queue to send results

    """
    # Import here to avoid pickling issues
    from src.langgraph.workflow import get_compiled_workflow

    # Create workflow in the worker process
    workflow = get_compiled_workflow()

    # Set process title for monitoring
    try:
        import setproctitle

        setproctitle.setproctitle("foia-worker")
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

                    # Run through workflow
                    state = {
                        "filename": task.document_path.name,
                        "content": content,
                        "foia_request": task.foia_request,
                        "classification": None,
                        "confidence": None,
                        "justification": None,
                        "exemptions": None,
                        "human_decision": None,
                        "human_feedback": None,
                        "patterns_learned": None,
                        "error": None,
                    }

                    # Execute workflow
                    final_state = workflow.invoke(state)

                    # Create document from state
                    document = Document(
                        filename=final_state["filename"],
                        content=final_state["content"],
                        classification=final_state.get("classification"),
                        confidence=final_state.get("confidence"),
                        justification=final_state.get("justification"),
                        exemptions=final_state.get("exemptions", []),
                    )

                    processing_time = time.time() - start_time
                    result = ProcessingResult(
                        task_id=task.task_id,
                        document=document,
                        processing_time=processing_time,
                    )

                except Exception as e:
                    processing_time = time.time() - start_time
                    result = ProcessingResult(
                        task_id=task.task_id,
                        error=str(e),
                        processing_time=processing_time,
                    )

                result_queue.put(result)

        except Empty:
            continue
        except Exception as e:
            # Critical error - log and continue
            print(f"Worker error: {e}")
            continue
