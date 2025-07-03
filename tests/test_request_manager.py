"""
Unit tests for the RequestManager class.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from src.processing.request_manager import RequestManager
from src.models.request import FOIARequest


class TestRequestManager:
    """Test cases for RequestManager"""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh RequestManager for each test"""
        return RequestManager()
        
    def test_create_request(self, manager):
        """Test creating a new request"""
        request = manager.create_request("Test Request", "Test description")
        
        assert request is not None
        assert request.name == "Test Request"
        assert request.description == "Test description"
        assert request.id in manager._requests
        assert manager._active_request_id == request.id
        
    def test_first_request_becomes_active(self, manager):
        """Test that the first request automatically becomes active"""
        request1 = manager.create_request("Request 1")
        assert manager.get_active_request() == request1
        
        request2 = manager.create_request("Request 2")
        # First request should still be active
        assert manager.get_active_request() == request1
        
    def test_get_request(self, manager):
        """Test retrieving a specific request"""
        request = manager.create_request("Test Request")
        
        retrieved = manager.get_request(request.id)
        assert retrieved == request
        
        # Test non-existent request
        assert manager.get_request("non-existent-id") is None
        
    def test_get_active_request(self, manager):
        """Test getting the active request"""
        # No active request initially
        assert manager.get_active_request() is None
        
        request = manager.create_request("Test Request")
        assert manager.get_active_request() == request
        
    def test_set_active_request(self, manager):
        """Test setting the active request"""
        request1 = manager.create_request("Request 1")
        request2 = manager.create_request("Request 2")
        
        # Request 1 should be active
        assert manager.get_active_request() == request1
        
        # Switch to request 2
        assert manager.set_active_request(request2.id) is True
        assert manager.get_active_request() == request2
        
        # Try setting non-existent request
        assert manager.set_active_request("non-existent") is False
        # Active request should not change
        assert manager.get_active_request() == request2
        
    def test_list_requests(self, manager):
        """Test listing all requests"""
        # Empty list initially
        assert manager.list_requests() == []
        
        # Create requests with small time delays
        request1 = manager.create_request("Request 1")
        request2 = manager.create_request("Request 2")
        request3 = manager.create_request("Request 3")
        
        # Manually set creation times to ensure order
        request1.created_at = datetime.now() - timedelta(hours=2)
        request2.created_at = datetime.now() - timedelta(hours=1)
        request3.created_at = datetime.now()
        
        requests = manager.list_requests()
        assert len(requests) == 3
        # Should be sorted by creation date, most recent first
        assert requests[0] == request3
        assert requests[1] == request2
        assert requests[2] == request1
        
    def test_delete_request(self, manager):
        """Test deleting a request"""
        request1 = manager.create_request("Request 1")
        request2 = manager.create_request("Request 2")
        
        # Delete request 1 (which is active)
        assert manager.delete_request(request1.id) is True
        assert manager.get_request(request1.id) is None
        # Request 2 should become active
        assert manager.get_active_request() == request2
        
        # Delete request 2
        assert manager.delete_request(request2.id) is True
        assert manager.get_active_request() is None
        
        # Try deleting non-existent request
        assert manager.delete_request("non-existent") is False
        
    def test_delete_non_active_request(self, manager):
        """Test deleting a request that is not active"""
        request1 = manager.create_request("Request 1")
        request2 = manager.create_request("Request 2")
        
        # Request 1 is active, delete request 2
        assert manager.delete_request(request2.id) is True
        # Request 1 should still be active
        assert manager.get_active_request() == request1
        
    def test_update_request(self, manager):
        """Test updating request fields"""
        request = manager.create_request("Original Name")
        request_id = request.id
        
        # Update various fields
        deadline = datetime.now() + timedelta(days=20)
        assert manager.update_request(
            request_id,
            name="Updated Name",
            description="Updated description",
            foia_request_text="Updated FOIA text",
            deadline=deadline,
            status="processing",
            document_folder=Path("/test/path")
        ) is True
        
        # Verify updates
        updated = manager.get_request(request_id)
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"
        assert updated.foia_request_text == "Updated FOIA text"
        assert updated.deadline == deadline
        assert updated.status == "processing"
        assert updated.document_folder == Path("/test/path")
        
        # Try updating non-existent request
        assert manager.update_request("non-existent", name="Test") is False
        
        # Try updating non-allowed field (should be ignored)
        manager.update_request(request_id, id="new-id", processed_documents=999)
        updated = manager.get_request(request_id)
        assert updated.id == request_id  # ID should not change
        assert updated.processed_documents == 0  # Should not be updated
        
    def test_get_request_count(self, manager):
        """Test getting request count"""
        assert manager.get_request_count() == 0
        
        manager.create_request("Request 1")
        assert manager.get_request_count() == 1
        
        manager.create_request("Request 2")
        manager.create_request("Request 3")
        assert manager.get_request_count() == 3
        
        # Delete one
        requests = manager.list_requests()
        manager.delete_request(requests[0].id)
        assert manager.get_request_count() == 2
        
    def test_has_active_request(self, manager):
        """Test checking for active request"""
        assert manager.has_active_request() is False
        
        request = manager.create_request("Test Request")
        assert manager.has_active_request() is True
        
        manager.delete_request(request.id)
        assert manager.has_active_request() is False
        
    def test_clear_all_requests(self, manager):
        """Test clearing all requests"""
        manager.create_request("Request 1")
        manager.create_request("Request 2")
        manager.create_request("Request 3")
        
        assert manager.get_request_count() == 3
        assert manager.has_active_request() is True
        
        manager.clear_all_requests()
        
        assert manager.get_request_count() == 0
        assert manager.has_active_request() is False
        assert manager.get_active_request() is None