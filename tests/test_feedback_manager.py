"""Tests for the FeedbackManager class."""

import pytest

from src.models.document import Document
from src.models.feedback import FeedbackEntry
from src.processing.feedback_manager import FeedbackManager


@pytest.fixture
def feedback_manager():
    """Create a FeedbackManager instance for testing."""
    return FeedbackManager()


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    return Document(
        filename="test_doc.txt",
        content="This is a test document about the FOIA request topic.",
        classification="responsive",
        confidence=0.8,
        justification="Document relates to the request",
        exemptions=[]
    )


class TestFeedbackManager:
    """Test suite for FeedbackManager."""
    
    def test_initialization(self, feedback_manager):
        """Test that FeedbackManager initializes correctly."""
        assert feedback_manager._feedback == {}
        assert feedback_manager.has_feedback("test_request") is False
    
    def test_add_feedback_no_change(self, feedback_manager, sample_document):
        """Test that no feedback is recorded when human agrees with AI."""
        result = feedback_manager.add_feedback(
            sample_document, 
            "request_1", 
            "responsive"  # Same as AI classification
        )
        
        assert result is None
        assert not feedback_manager.has_feedback("request_1")
    
    def test_add_feedback_with_correction(self, feedback_manager, sample_document):
        """Test that feedback is recorded when human corrects AI."""
        result = feedback_manager.add_feedback(
            sample_document,
            "request_1",
            "non_responsive"  # Different from AI classification
        )
        
        assert result is not None
        assert isinstance(result, FeedbackEntry)
        assert result.document_id == "test_doc.txt"
        assert result.original_classification == "responsive"
        assert result.human_decision == "non_responsive"
        assert result.original_confidence == 0.8
        assert feedback_manager.has_feedback("request_1")
    
    def test_get_all_feedback_empty(self, feedback_manager):
        """Test getting feedback when none exists."""
        feedback = feedback_manager.get_all_feedback("request_1")
        assert feedback == []
    
    def test_get_all_feedback_with_entries(self, feedback_manager):
        """Test getting all feedback for a request."""
        # Add multiple feedback entries
        doc1 = Document(
            filename="doc1.txt",
            content="First document content",
            classification="responsive",
            confidence=0.9
        )
        doc2 = Document(
            filename="doc2.txt",
            content="Second document content",
            classification="non_responsive",
            confidence=0.7
        )
        
        feedback_manager.add_feedback(doc1, "request_1", "non_responsive")
        feedback_manager.add_feedback(doc2, "request_1", "responsive")
        
        feedback = feedback_manager.get_all_feedback("request_1")
        
        assert len(feedback) == 2
        assert feedback[0]["ai_classification"] == "responsive"
        assert feedback[0]["human_correction"] == "non_responsive"
        assert feedback[1]["ai_classification"] == "non_responsive"
        assert feedback[1]["human_correction"] == "responsive"
    
    def test_feedback_isolation_between_requests(self, feedback_manager, sample_document):
        """Test that feedback is isolated between different requests."""
        # Add feedback for different requests
        feedback_manager.add_feedback(sample_document, "request_1", "non_responsive")
        feedback_manager.add_feedback(sample_document, "request_2", "uncertain")
        
        feedback1 = feedback_manager.get_all_feedback("request_1")
        feedback2 = feedback_manager.get_all_feedback("request_2")
        
        assert len(feedback1) == 1
        assert len(feedback2) == 1
        assert feedback1[0]["human_correction"] == "non_responsive"
        assert feedback2[0]["human_correction"] == "uncertain"
    
    def test_get_statistics_empty(self, feedback_manager):
        """Test statistics when no feedback exists."""
        stats = feedback_manager.get_statistics("request_1")
        
        assert stats["total_corrections"] == 0
        assert stats["most_corrected_type"] == "N/A"
    
    def test_get_statistics_with_feedback(self, feedback_manager):
        """Test statistics calculation with feedback."""
        # Create documents with different classifications
        docs = [
            Document(filename=f"doc{i}.txt", content=f"Content {i}", 
                    classification="responsive", confidence=0.8)
            for i in range(3)
        ]
        docs.extend([
            Document(filename=f"doc{i}.txt", content=f"Content {i}", 
                    classification="non_responsive", confidence=0.7)
            for i in range(3, 5)
        ])
        
        # Add corrections
        for doc in docs[:3]:
            feedback_manager.add_feedback(doc, "request_1", "non_responsive")
        for doc in docs[3:]:
            feedback_manager.add_feedback(doc, "request_1", "responsive")
        
        stats = feedback_manager.get_statistics("request_1")
        
        assert stats["total_corrections"] == 5
        assert stats["most_corrected_type"] == "responsive → non_responsive"
        assert "responsive → non_responsive" in stats["correction_counts"]
        assert stats["correction_counts"]["responsive → non_responsive"] == 3
    
    def test_clear_feedback(self, feedback_manager, sample_document):
        """Test clearing feedback for a request."""
        # Add feedback
        feedback_manager.add_feedback(sample_document, "request_1", "non_responsive")
        assert feedback_manager.has_feedback("request_1")
        
        # Clear feedback
        feedback_manager.clear_feedback("request_1")
        assert not feedback_manager.has_feedback("request_1")
        assert feedback_manager.get_all_feedback("request_1") == []
    
    def test_document_snippet_truncation(self, feedback_manager):
        """Test that long document content is truncated in snippets."""
        long_content = "A" * 300  # Longer than 200 chars
        doc = Document(
            filename="long_doc.txt",
            content=long_content,
            classification="responsive",
            confidence=0.8
        )
        
        result = feedback_manager.add_feedback(doc, "request_1", "non_responsive")
        
        assert result is not None
        assert len(result.document_snippet) == 203  # 200 chars + "..."
        assert result.document_snippet.endswith("...")
    
    def test_feedback_prompt_format(self, feedback_manager, sample_document):
        """Test that feedback is formatted correctly for prompts."""
        feedback_manager.add_feedback(sample_document, "request_1", "non_responsive")
        
        feedback = feedback_manager.get_all_feedback("request_1")
        
        assert len(feedback) == 1
        example = feedback[0]
        assert "document_snippet" in example
        assert "ai_classification" in example
        assert "human_correction" in example
        assert "confidence" in example
        assert example["confidence"] == 0.8