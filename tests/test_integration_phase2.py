"""
Integration tests for Day 2: Multi-Request Integration with UI Tabs
"""

import pytest
from pathlib import Path
from PyQt6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.models.document import Document
from src.models.request import FOIARequest


class TestMultiRequestUIIntegration:
    """Integration tests for multi-request UI functionality"""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing"""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
        app.quit()
        
    @pytest.fixture
    def main_window(self, app):
        """Create MainWindow instance"""
        window = MainWindow()
        yield window
        window.close()
        
    def test_main_window_initialization(self, main_window):
        """Test that MainWindow initializes with all tabs and managers"""
        # Verify managers are created
        assert main_window.request_manager is not None
        assert main_window.document_store is not None
        
        # Verify tabs are created
        assert main_window.requests_tab is not None
        assert main_window.intake_tab is not None
        assert main_window.review_tab is not None
        assert main_window.finalize_tab is not None
        
        # Verify tabs have manager references
        assert main_window.intake_tab.request_manager == main_window.request_manager
        assert main_window.intake_tab.document_store == main_window.document_store
        assert main_window.review_tab.request_manager == main_window.request_manager
        assert main_window.review_tab.document_store == main_window.document_store
        assert main_window.finalize_tab.request_manager == main_window.request_manager
        assert main_window.finalize_tab.document_store == main_window.document_store
        
        # Verify default request was created
        assert main_window.request_manager.get_request_count() == 1
        default_request = main_window.request_manager.get_active_request()
        assert default_request is not None
        assert default_request.name == "F-2024-00123"
        assert default_request.description == "Blue Sky Project"
        assert "Blue Sky Project" in default_request.foia_request_text
        assert "January 2023" in default_request.foia_request_text
        assert "September 2024" in default_request.foia_request_text
        
    def test_request_switching_updates_all_tabs(self, main_window):
        """Test that switching requests updates all tabs"""
        # Create additional requests
        request2 = main_window.request_manager.create_request("Request 2", "Second request")
        request3 = main_window.request_manager.create_request("Request 3", "Third request")
        
        # Add some test documents to different requests
        doc1 = Document(filename="doc1.txt", content="Content 1", classification="responsive")
        doc2 = Document(filename="doc2.txt", content="Content 2", classification="non-responsive")
        
        main_window.document_store.add_document(request2.id, doc1)
        main_window.document_store.add_document(request3.id, doc2)
        
        # Switch to request 2
        main_window.request_manager.set_active_request(request2.id)
        main_window._on_request_selected(request2.id)
        
        # Verify window title updated
        assert request2.name in main_window.windowTitle()
        
        # Verify intake tab shows correct request
        if hasattr(main_window.intake_tab, 'active_request_label'):
            assert request2.name in main_window.intake_tab.active_request_label.text()
            
    def test_document_flow_through_tabs(self, main_window):
        """Test document flow from intake through review to finalize"""
        # Get active request
        request = main_window.request_manager.get_active_request()
        
        # Simulate document processing in intake
        doc = Document(
            filename="test.txt",
            content="Test content",
            classification="responsive",
            confidence=0.9,
            justification="Contains requested information"
        )
        
        # Add to document store (simulating intake processing)
        main_window.document_store.add_document(request.id, doc)
        
        # Update request stats
        main_window.request_manager.update_request(
            request.id,
            status="review",
            total_documents=1,
            processed_documents=1,
            responsive_count=1
        )
        
        # Refresh review tab
        main_window.review_tab.refresh_request_context()
        
        # Verify document appears in review queue
        assert len(main_window.review_tab._document_queue) == 1
        assert main_window.review_tab._document_queue[0].filename == "test.txt"
        
        # Simulate review decision
        doc.human_decision = "responsive"
        doc.human_feedback = "Confirmed responsive"
        main_window.document_store.update_document(
            request.id,
            doc.filename,
            human_decision=doc.human_decision,
            human_feedback=doc.human_feedback
        )
        
        # Refresh finalize tab
        main_window.finalize_tab.refresh_request_context()
        
        # Verify document appears in finalize tab
        assert len(main_window.finalize_tab.processed_documents) == 1
        assert main_window.finalize_tab.processed_documents[0].document.filename == "test.txt"
        
    def test_request_deletion_clears_data(self, main_window):
        """Test that deleting a request clears associated data"""
        # Create a new request
        request = main_window.request_manager.create_request("Test Request", "To be deleted")
        
        # Add documents
        doc1 = Document(filename="doc1.txt", content="Content 1")
        doc2 = Document(filename="doc2.txt", content="Content 2")
        main_window.document_store.add_documents(request.id, [doc1, doc2])
        
        # Delete request
        main_window._on_request_deleted(request.id)
        
        # Verify documents were cleared
        assert main_window.document_store.get_document_count(request.id) == 0
        
    def test_tab_refresh_on_request_creation(self, main_window):
        """Test that creating a new request refreshes tabs"""
        initial_count = main_window.request_manager.get_request_count()
        
        # Create new request
        new_request = main_window.request_manager.create_request("New Request", "Fresh request")
        main_window._on_request_created(new_request.id)
        
        # Verify request count increased
        assert main_window.request_manager.get_request_count() == initial_count + 1
        
        # Verify window title updated
        assert "RAPID RESPONSE AI" in main_window.windowTitle()
        
    def test_empty_request_handling(self, main_window):
        """Test handling when no documents in request"""
        # Get active request
        request = main_window.request_manager.get_active_request()
        
        # Ensure no documents
        main_window.document_store.clear_request(request.id)
        
        # Refresh all tabs
        main_window.review_tab.refresh_request_context()
        main_window.finalize_tab.refresh_request_context()
        
        # Verify empty states
        assert len(main_window.review_tab._document_queue) == 0
        assert len(main_window.finalize_tab.processed_documents) == 0