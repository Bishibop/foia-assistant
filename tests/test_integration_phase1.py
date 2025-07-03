"""
Integration tests for Phase 1: Multi-Request Management
"""

import pytest
from pathlib import Path

from src.processing.request_manager import RequestManager
from src.processing.document_store import DocumentStore
from src.models.document import Document
from src.models.request import FOIARequest


class TestMultiRequestIntegration:
    """Integration tests for multi-request functionality"""
    
    @pytest.fixture
    def setup(self):
        """Setup managers and test data"""
        request_manager = RequestManager()
        document_store = DocumentStore()
        
        # Create sample documents
        docs = [
            Document(filename="doc1.txt", content="Content 1", classification="responsive"),
            Document(filename="doc2.txt", content="Content 2", classification="non-responsive"),
            Document(filename="doc3.txt", content="Content 3", classification="uncertain"),
        ]
        
        return request_manager, document_store, docs
        
    def test_request_creation_flow(self, setup):
        """Test complete request creation flow"""
        request_manager, document_store, docs = setup
        
        # Create requests
        request1 = request_manager.create_request("FOIA Request 1", "First test request")
        request2 = request_manager.create_request("FOIA Request 2", "Second test request")
        
        # Verify requests were created
        assert request_manager.get_request_count() == 2
        assert request1.name == "FOIA Request 1"
        assert request2.name == "FOIA Request 2"
        
        # Verify first request is active
        assert request_manager.get_active_request() == request1
        
        # Add documents to request 1
        document_store.add_documents(request1.id, docs[:2])
        
        # Switch to request 2
        assert request_manager.set_active_request(request2.id) is True
        assert request_manager.get_active_request() == request2
        
        # Add different documents to request 2
        document_store.add_documents(request2.id, [docs[2]])
        
        # Verify data isolation
        assert document_store.get_document_count(request1.id) == 2
        assert document_store.get_document_count(request2.id) == 1
        
        # Verify documents are isolated
        assert document_store.get_document(request1.id, "doc1.txt") is not None
        assert document_store.get_document(request1.id, "doc3.txt") is None
        assert document_store.get_document(request2.id, "doc3.txt") is not None
        assert document_store.get_document(request2.id, "doc1.txt") is None
        
    def test_request_deletion_and_data_cleanup(self, setup):
        """Test that deleting a request cleans up associated data"""
        request_manager, document_store, docs = setup
        
        # Create requests and add documents
        request1 = request_manager.create_request("Request 1")
        request2 = request_manager.create_request("Request 2")
        
        document_store.add_documents(request1.id, docs)
        document_store.add_documents(request2.id, docs)
        
        # Delete request 1
        request_manager.delete_request(request1.id)
        
        # Clear request 1 data from document store
        document_store.clear_request(request1.id)
        
        # Verify request 1 is gone
        assert request_manager.get_request(request1.id) is None
        assert document_store.get_document_count(request1.id) == 0
        
        # Verify request 2 is unaffected
        assert request_manager.get_request(request2.id) is not None
        assert document_store.get_document_count(request2.id) == 3
        
    def test_request_statistics_integration(self, setup):
        """Test integration between request statistics and document store"""
        request_manager, document_store, docs = setup
        
        # Create request
        request = request_manager.create_request("Stats Test Request")
        
        # Add documents
        document_store.add_documents(request.id, docs)
        
        # Update some documents as reviewed
        document_store.update_document(
            request.id, 
            "doc1.txt", 
            human_decision="responsive",
            human_feedback="Confirmed"
        )
        document_store.update_document(
            request.id, 
            "doc2.txt", 
            human_decision="non-responsive",
            human_feedback="Not relevant"
        )
        
        # Get statistics from document store
        stats = document_store.get_statistics(request.id)
        
        # Update request with statistics
        request_manager.update_request(
            request.id,
            status="review"
        )
        request.total_documents = stats['total']
        request.processed_documents = stats['total']
        request.responsive_count = stats['responsive']
        request.non_responsive_count = stats['non_responsive']
        request.uncertain_count = stats['uncertain']
        request.reviewed_document_ids = {
            doc.filename for doc in document_store.get_reviewed_documents(request.id)
        }
        
        # Get summary
        summary = request.get_summary()
        
        # Verify statistics
        assert summary['total_documents'] == 3
        assert summary['reviewed'] == 2
        assert summary['responsive'] == 1
        assert summary['non_responsive'] == 1
        assert summary['uncertain'] == 1
        assert summary['progress'] == pytest.approx(66.67, rel=0.01)
        
    def test_multiple_active_request_switches(self, setup):
        """Test switching between multiple requests"""
        request_manager, document_store, docs = setup
        
        # Create multiple requests
        requests = []
        for i in range(5):
            request = request_manager.create_request(f"Request {i+1}")
            requests.append(request)
            
        # Switch between requests and add documents
        for i, request in enumerate(requests):
            request_manager.set_active_request(request.id)
            # Add a unique document to each request
            doc = Document(
                filename=f"unique_{i}.txt",
                content=f"Content for request {i+1}",
                classification="responsive"
            )
            document_store.add_document(request.id, doc)
            
        # Verify each request has its unique document
        for i, request in enumerate(requests):
            assert document_store.get_document_count(request.id) == 1
            unique_doc = document_store.get_document(request.id, f"unique_{i}.txt")
            assert unique_doc is not None
            assert f"request {i+1}" in unique_doc.content
            
    def test_request_workflow_states(self, setup):
        """Test request state transitions through workflow"""
        request_manager, document_store, docs = setup
        
        # Create request in draft state
        request = request_manager.create_request("Workflow Test")
        assert request.status == "draft"
        
        # Move to processing when documents added
        document_store.add_documents(request.id, docs)
        request_manager.update_request(request.id, status="processing")
        
        # Simulate processing completion
        for doc in docs:
            doc.confidence = 0.9
            
        # Move to review
        request_manager.update_request(request.id, status="review")
        
        # Simulate reviews
        document_store.update_document(
            request.id, "doc1.txt", human_decision="responsive"
        )
        document_store.update_document(
            request.id, "doc2.txt", human_decision="non-responsive"
        )
        document_store.update_document(
            request.id, "doc3.txt", human_decision="uncertain"
        )
        
        # Move to complete
        request_manager.update_request(request.id, status="complete")
        
        # Verify final state
        final_request = request_manager.get_request(request.id)
        assert final_request.status == "complete"
        
        # Verify all documents reviewed
        unreviewed = document_store.get_unreviewed_documents(request.id)
        assert len(unreviewed) == 0