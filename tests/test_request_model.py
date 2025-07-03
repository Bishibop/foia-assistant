"""
Unit tests for the FOIARequest model.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from src.models.request import FOIARequest


class TestFOIARequest:
    """Test cases for FOIARequest model"""
    
    def test_request_creation_defaults(self):
        """Test creating a request with default values"""
        request = FOIARequest()
        
        assert request.id is not None
        assert len(request.id) == 36  # UUID length
        assert request.name == ""
        assert request.description == ""
        assert request.foia_request_text == ""
        assert request.status == "draft"
        assert request.total_documents == 0
        assert request.processed_documents == 0
        assert request.responsive_count == 0
        assert request.non_responsive_count == 0
        assert request.uncertain_count == 0
        assert request.document_folder is None
        assert len(request.processed_document_ids) == 0
        assert len(request.reviewed_document_ids) == 0
        
    def test_request_creation_with_values(self):
        """Test creating a request with specific values"""
        deadline = datetime.now() + timedelta(days=20)
        request = FOIARequest(
            name="Test Request",
            description="Test description",
            foia_request_text="Please provide all documents...",
            deadline=deadline,
            status="processing"
        )
        
        assert request.name == "Test Request"
        assert request.description == "Test description"
        assert request.foia_request_text == "Please provide all documents..."
        assert request.deadline == deadline
        assert request.status == "processing"
        
    def test_invalid_status_raises_error(self):
        """Test that invalid status raises ValueError"""
        with pytest.raises(ValueError, match="Invalid status: invalid"):
            FOIARequest(status="invalid")
            
    def test_unique_ids(self):
        """Test that each request gets a unique ID"""
        request1 = FOIARequest()
        request2 = FOIARequest()
        
        assert request1.id != request2.id
        
    def test_update_statistics(self):
        """Test updating request statistics"""
        request = FOIARequest()
        
        # Add some processed documents
        request.processed_document_ids.add("doc1")
        request.processed_document_ids.add("doc2")
        request.processed_document_ids.add("doc3")
        
        request.update_statistics()
        
        assert request.total_documents == 3
        
    def test_progress_percentage(self):
        """Test progress calculation"""
        request = FOIARequest()
        
        # No documents
        assert request.get_progress_percentage() == 0.0
        
        # Add documents
        request.processed_document_ids = {"doc1", "doc2", "doc3", "doc4"}
        request.total_documents = 4
        
        # Review some documents
        request.reviewed_document_ids = {"doc1", "doc2"}
        
        assert request.get_progress_percentage() == 50.0
        
        # Review all documents
        request.reviewed_document_ids = {"doc1", "doc2", "doc3", "doc4"}
        
        assert request.get_progress_percentage() == 100.0
        
    def test_get_summary(self):
        """Test getting request summary"""
        request = FOIARequest(
            name="Test Request",
            status="processing"
        )
        
        # Set up some data
        request.total_documents = 10
        request.processed_documents = 8
        request.reviewed_document_ids = {"doc1", "doc2", "doc3", "doc4", "doc5"}
        request.responsive_count = 3
        request.non_responsive_count = 2
        request.uncertain_count = 0
        
        summary = request.get_summary()
        
        assert summary["id"] == request.id
        assert summary["name"] == "Test Request"
        assert summary["status"] == "processing"
        assert summary["total_documents"] == 10
        assert summary["processed"] == 8
        assert summary["reviewed"] == 5
        assert summary["responsive"] == 3
        assert summary["non_responsive"] == 2
        assert summary["uncertain"] == 0
        assert summary["progress"] == 50.0
        
    def test_document_folder_path(self):
        """Test document folder path handling"""
        request = FOIARequest()
        
        # Set a document folder
        test_path = Path("/test/documents")
        request.document_folder = test_path
        
        assert request.document_folder == test_path
        assert isinstance(request.document_folder, Path)