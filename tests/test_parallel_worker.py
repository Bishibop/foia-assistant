"""Tests for the parallel document processing module."""

import multiprocessing as mp
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

import pytest

from src.models.document import Document
from src.processing.parallel_worker import (
    ParallelDocumentProcessor,
    ProcessingResult,
    ProcessingTask,
    process_document_batch,
)


# Note: We no longer need a mock workflow since the real workflow
# is created inside each worker process


@pytest.fixture(autouse=True)
def mock_langgraph_workflow():
    """Mock the LangGraph workflow for all tests."""
    with patch("src.langgraph.workflow.get_compiled_workflow") as mock_get:
        # Create a mock workflow
        mock_workflow = Mock()

        def mock_invoke(state):
            # Simulate processing
            state["classification"] = "responsive"
            state["confidence"] = 0.95
            state["justification"] = "Test classification"
            state["exemptions"] = []
            return state

        mock_workflow.invoke = mock_invoke
        mock_get.return_value = mock_workflow
        yield mock_workflow


class TestParallelDocumentProcessor:
    """Test suite for ParallelDocumentProcessor."""

    @pytest.fixture
    def processor(self):
        """Create a processor."""
        return ParallelDocumentProcessor(num_workers=2)

    def test_initialization(self):
        """Test processor initialization."""
        # Default initialization
        processor = ParallelDocumentProcessor()
        # Should be capped at 4
        assert processor.num_workers == min(4, max(1, mp.cpu_count() - 1))
        assert processor.batch_size is None

        # Custom initialization
        processor = ParallelDocumentProcessor(num_workers=8, batch_size=10)
        assert processor.num_workers == 8  # Custom value overrides the cap
        assert processor.batch_size == 10

    def test_calculate_optimal_batch_size(self, processor):
        """Test batch size calculation."""
        # Small number of tasks
        assert processor._calculate_optimal_batch_size(2) == 1

        # Medium number of tasks
        assert processor._calculate_optimal_batch_size(8) == 2

        # Large number of tasks
        batch_size = processor._calculate_optimal_batch_size(100)
        assert batch_size > 2
        assert batch_size <= 25  # Reasonable upper bound

    def test_create_batches(self, processor):
        """Test batch creation."""
        tasks = [
            ProcessingTask(
                document_path=Path(f"doc{i}.txt"), foia_request="test", task_id=i
            )
            for i in range(10)
        ]

        # Test with batch size 3
        processor.batch_size = 3
        batches = processor._create_batches(tasks)
        assert len(batches) == 4  # 10 tasks / 3 per batch = 4 batches
        assert len(batches[0]) == 3
        assert len(batches[1]) == 3
        assert len(batches[2]) == 3
        assert len(batches[3]) == 1

    def test_process_documents_success(self, processor, tmp_path):
        """Test successful document processing."""
        # Create test documents
        doc_paths = []
        for i in range(5):
            doc_path = tmp_path / f"doc{i}.txt"
            doc_path.write_text(f"This is document {i}")
            doc_paths.append(doc_path)

        # Set up progress tracking
        progress_updates = []

        def track_progress(current, total):
            progress_updates.append((current, total))

        processor.set_progress_callback(track_progress)

        # Process documents
        results = processor.process_documents(doc_paths, "Test FOIA request")

        # Verify results
        assert len(results) == 5
        for i, doc in enumerate(results):
            assert doc.filename == f"doc{i}.txt"
            assert doc.content == f"This is document {i}"
            # Classification could be anything depending on the workflow
            assert doc.classification in ["responsive", "non_responsive", "uncertain"]
            assert doc.confidence is not None

        # Verify progress updates
        assert len(progress_updates) > 0
        assert progress_updates[-1] == (5, 5)

    def test_process_documents_with_errors(self, processor, tmp_path):
        """Test document processing with some errors."""
        # Create test documents (one will fail)
        doc_paths = []
        for i in range(3):
            doc_path = tmp_path / f"doc{i}.txt"
            if i == 1:
                # Don't create this file to simulate error
                doc_paths.append(doc_path)
            else:
                doc_path.write_text(f"This is document {i}")
                doc_paths.append(doc_path)

        # Set up error tracking
        errors = []

        def track_errors(error):
            errors.append(error)

        processor.set_error_callback(track_errors)

        # Process documents
        results = processor.process_documents(doc_paths, "Test FOIA request")

        # Should get results for successful documents
        assert len(results) == 2
        assert results[0].filename == "doc0.txt"
        assert results[1].filename == "doc2.txt"

        # Should have recorded an error
        assert len(errors) == 1
        assert "Error processing document 1" in errors[0]

    def test_processing_rate(self, processor):
        """Test processing rate calculation."""
        # Initial rate should be 0
        assert processor.get_processing_rate() == 0.0

        # Simulate processing
        processor._start_time = time.time() - 60  # 1 minute ago
        processor._documents_processed = 30

        # Should be 30 docs/minute
        rate = processor.get_processing_rate()
        assert 29 <= rate <= 31  # Allow for small timing variations

    def test_worker_function(self, tmp_path):
        """Test the worker process function."""
        # Create queues
        task_queue = mp.Queue()
        result_queue = mp.Queue()

        # Create test task
        doc_path = tmp_path / "test.txt"
        doc_path.write_text("Test content")
        task = ProcessingTask(
            document_path=doc_path, foia_request="Test request", task_id=0
        )

        # Add task and sentinel
        task_queue.put([task])
        task_queue.put(None)

        # Run worker in same process for testing
        process_document_batch(None, task_queue, result_queue)

        # Check result with timeout
        result = result_queue.get(timeout=5.0)
        assert isinstance(result, ProcessingResult)
        assert result.task_id == 0
        assert result.document is not None
        assert result.document.filename == "test.txt"
        assert result.error is None
        assert result.processing_time > 0

    def test_worker_function_error_handling(self, tmp_path):
        """Test worker function error handling."""
        # Create queues
        task_queue = mp.Queue()
        result_queue = mp.Queue()

        # Create task with non-existent file
        task = ProcessingTask(
            document_path=Path("nonexistent.txt"),
            foia_request="Test request",
            task_id=0,
        )

        # Add task and sentinel
        task_queue.put([task])
        task_queue.put(None)

        # Run worker
        process_document_batch(None, task_queue, result_queue)

        # Check error result
        result = result_queue.get()
        assert result.task_id == 0
        assert result.document is None
        assert result.error is not None
        assert "No such file" in result.error or "cannot find" in result.error

    @pytest.mark.parametrize("num_docs,num_workers", [(10, 2), (20, 4), (50, 8)])
    def test_parallel_performance(self, tmp_path, num_docs, num_workers):
        """Test that parallel processing works correctly."""
        # Create test documents
        doc_paths = []
        for i in range(num_docs):
            doc_path = tmp_path / f"doc{i}.txt"
            doc_path.write_text(f"Document {i} content")
            doc_paths.append(doc_path)

        # Time parallel processing
        processor = ParallelDocumentProcessor(num_workers=num_workers)
        start = time.time()
        parallel_results = processor.process_documents(doc_paths, "Test request")
        parallel_time = time.time() - start

        # Verify all documents were processed
        assert len(parallel_results) == num_docs

        # Verify documents are in correct order
        for i, doc in enumerate(parallel_results):
            assert doc.filename == f"doc{i}.txt"
            # Note: classification will be whatever the real workflow returns
            assert doc.classification is not None

        # For large batches, parallel should show improvement
        # (though for small test cases, overhead may dominate)
        print(
            f"Processed {num_docs} docs with {num_workers} workers in {parallel_time:.2f}s"
        )

    def test_batch_distribution(self, processor):
        """Test that batches are evenly distributed."""
        # Test various document counts
        for total_docs in [10, 25, 47, 100]:
            tasks = [
                ProcessingTask(
                    document_path=Path(f"doc{i}.txt"),
                    foia_request="test",
                    task_id=i,
                )
                for i in range(total_docs)
            ]

            batch_size = processor._calculate_optimal_batch_size(total_docs)
            batches = processor._create_batches(tasks)

            # Verify all tasks are included
            task_count = sum(len(batch) for batch in batches)
            assert task_count == total_docs

            # Verify reasonable batch distribution
            if total_docs > processor.num_workers:
                assert len(batches) >= processor.num_workers
                assert (
                    max(len(b) for b in batches) - min(len(b) for b in batches[:-1])
                    <= 1
                )
