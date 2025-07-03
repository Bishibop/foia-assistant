"""
Unit tests for the DocumentStore class.
"""

import pytest
from src.processing.document_store import DocumentStore
from src.models.document import Document


class TestDocumentStore:
    """Test cases for DocumentStore"""
    
    @pytest.fixture
    def store(self):
        """Create a fresh DocumentStore for each test"""
        return DocumentStore()
        
    @pytest.fixture
    def sample_documents(self):
        """Create sample documents for testing"""
        return [
            Document(
                filename="doc1.txt",
                content="Content 1",
                classification="responsive",
                confidence=0.9,
                justification="Contains requested information"
            ),
            Document(
                filename="doc2.txt",
                content="Content 2",
                classification="non-responsive",
                confidence=0.8,
                justification="Outside scope"
            ),
            Document(
                filename="doc3.txt",
                content="Content 3",
                classification="uncertain",
                confidence=0.5,
                justification="Unclear relevance"
            ),
            Document(
                filename="doc4.txt",
                content="Content 4",
                classification="responsive",
                confidence=0.85,
                justification="Partially responsive",
                exemptions=[{"type": "PII", "start": 10, "end": 20}]
            )
        ]
        
    def test_add_document(self, store):
        """Test adding a single document"""
        doc = Document(filename="test.txt", content="Test content")
        store.add_document("request1", doc)
        
        assert store.get_document_count("request1") == 1
        retrieved = store.get_document("request1", "test.txt")
        assert retrieved == doc
        
    def test_add_documents(self, store, sample_documents):
        """Test adding multiple documents"""
        store.add_documents("request1", sample_documents)
        
        assert store.get_document_count("request1") == 4
        docs = store.get_documents("request1")
        assert len(docs) == 4
        
    def test_get_document(self, store):
        """Test retrieving a specific document"""
        doc = Document(filename="test.txt", content="Test content")
        store.add_document("request1", doc)
        
        retrieved = store.get_document("request1", "test.txt")
        assert retrieved == doc
        
        # Test non-existent document
        assert store.get_document("request1", "non-existent.txt") is None
        
        # Test non-existent request
        assert store.get_document("non-existent", "test.txt") is None
        
    def test_get_documents(self, store, sample_documents):
        """Test retrieving all documents for a request"""
        store.add_documents("request1", sample_documents)
        
        docs = store.get_documents("request1")
        assert len(docs) == 4
        assert all(isinstance(doc, Document) for doc in docs)
        
        # Test empty request
        assert store.get_documents("empty-request") == []
        
    def test_request_isolation(self, store, sample_documents):
        """Test that documents are isolated between requests"""
        # Add documents to different requests
        store.add_documents("request1", sample_documents[:2])
        store.add_documents("request2", sample_documents[2:])
        
        # Verify isolation
        assert store.get_document_count("request1") == 2
        assert store.get_document_count("request2") == 2
        
        # Verify specific documents
        assert store.get_document("request1", "doc1.txt") is not None
        assert store.get_document("request1", "doc3.txt") is None
        assert store.get_document("request2", "doc3.txt") is not None
        assert store.get_document("request2", "doc1.txt") is None
        
    def test_get_documents_by_classification(self, store, sample_documents):
        """Test filtering documents by classification"""
        store.add_documents("request1", sample_documents)
        
        responsive = store.get_documents_by_classification("request1", "responsive")
        assert len(responsive) == 2
        assert all(doc.classification == "responsive" for doc in responsive)
        
        non_responsive = store.get_documents_by_classification("request1", "non-responsive")
        assert len(non_responsive) == 1
        
        uncertain = store.get_documents_by_classification("request1", "uncertain")
        assert len(uncertain) == 1
        
    def test_get_documents_by_human_decision(self, store, sample_documents):
        """Test that human decisions override AI classifications"""
        store.add_documents("request1", sample_documents)
        
        # Update one document with human decision
        store.update_document(
            "request1", 
            "doc2.txt", 
            human_decision="responsive",
            human_feedback="Actually contains relevant info"
        )
        
        # Should now be counted as responsive
        responsive = store.get_documents_by_classification("request1", "responsive")
        assert len(responsive) == 3  # 2 original + 1 human override
        
    def test_get_unreviewed_documents(self, store, sample_documents):
        """Test getting unreviewed documents"""
        store.add_documents("request1", sample_documents)
        
        # Initially all unreviewed
        unreviewed = store.get_unreviewed_documents("request1")
        assert len(unreviewed) == 4
        
        # Review some documents
        store.update_document("request1", "doc1.txt", human_decision="responsive")
        store.update_document("request1", "doc2.txt", human_decision="non-responsive")
        
        unreviewed = store.get_unreviewed_documents("request1")
        assert len(unreviewed) == 2
        assert all(doc.human_decision is None for doc in unreviewed)
        
    def test_get_reviewed_documents(self, store, sample_documents):
        """Test getting reviewed documents"""
        store.add_documents("request1", sample_documents)
        
        # Initially none reviewed
        reviewed = store.get_reviewed_documents("request1")
        assert len(reviewed) == 0
        
        # Review some documents
        store.update_document("request1", "doc1.txt", human_decision="responsive")
        store.update_document("request1", "doc3.txt", human_decision="uncertain")
        
        reviewed = store.get_reviewed_documents("request1")
        assert len(reviewed) == 2
        assert all(doc.human_decision is not None for doc in reviewed)
        
    def test_update_document(self, store):
        """Test updating document fields"""
        doc = Document(filename="test.txt", content="Test content")
        store.add_document("request1", doc)
        
        # Update various fields
        assert store.update_document(
            "request1",
            "test.txt",
            classification="responsive",
            confidence=0.95,
            human_decision="responsive",
            human_feedback="Confirmed responsive"
        ) is True
        
        # Verify updates
        updated = store.get_document("request1", "test.txt")
        assert updated.classification == "responsive"
        assert updated.confidence == 0.95
        assert updated.human_decision == "responsive"
        assert updated.human_feedback == "Confirmed responsive"
        
        # Try updating non-existent document
        assert store.update_document("request1", "non-existent.txt", classification="test") is False
        
        # Try updating non-allowed field (should be ignored)
        store.update_document("request1", "test.txt", id="new-id", content="new content")
        updated = store.get_document("request1", "test.txt")
        assert updated.filename == "test.txt"  # Filename is used as key, not updatable
        assert updated.content == "Test content"  # Should not change
        
    def test_clear_request(self, store, sample_documents):
        """Test clearing documents for a specific request"""
        store.add_documents("request1", sample_documents[:2])
        store.add_documents("request2", sample_documents[2:])
        
        assert store.get_document_count("request1") == 2
        assert store.get_document_count("request2") == 2
        
        store.clear_request("request1")
        
        assert store.get_document_count("request1") == 0
        assert store.get_document_count("request2") == 2  # Should not be affected
        
    def test_clear_all(self, store, sample_documents):
        """Test clearing all documents"""
        store.add_documents("request1", sample_documents[:2])
        store.add_documents("request2", sample_documents[2:])
        
        store.clear_all()
        
        assert store.get_document_count("request1") == 0
        assert store.get_document_count("request2") == 0
        
    def test_get_statistics(self, store, sample_documents):
        """Test getting classification statistics"""
        store.add_documents("request1", sample_documents)
        
        stats = store.get_statistics("request1")
        
        assert stats['total'] == 4
        assert stats['reviewed'] == 0
        assert stats['responsive'] == 2
        assert stats['non_responsive'] == 1
        assert stats['uncertain'] == 1
        assert stats['has_exemptions'] == 1
        
        # Review some documents
        store.update_document("request1", "doc1.txt", human_decision="responsive")
        store.update_document("request1", "doc2.txt", human_decision="responsive")  # Override
        
        stats = store.get_statistics("request1")
        assert stats['reviewed'] == 2
        assert stats['responsive'] == 3  # 2 original + 1 override
        assert stats['non_responsive'] == 0  # Overridden
        
    def test_has_documents(self, store):
        """Test checking if request has documents"""
        assert store.has_documents("request1") is False
        
        doc = Document(filename="test.txt", content="Test")
        store.add_document("request1", doc)
        
        assert store.has_documents("request1") is True
        
        store.clear_request("request1")
        assert store.has_documents("request1") is False