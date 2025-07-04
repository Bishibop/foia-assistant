"""In-memory document storage with request isolation.
"""

from collections import defaultdict
from typing import Any

from src.models.document import Document


class DocumentStore:
    """In-memory document storage with request isolation"""

    def __init__(self) -> None:
        # Store documents by request_id -> filename -> Document
        self._documents: dict[str, dict[str, Document]] = defaultdict(dict)

    def add_document(self, request_id: str, document: Document) -> None:
        """Add document to request-specific store"""
        self._documents[request_id][document.filename] = document

    def add_documents(self, request_id: str, documents: list[Document]) -> None:
        """Add multiple documents to request-specific store"""
        for document in documents:
            self.add_document(request_id, document)

    def get_document(self, request_id: str, filename: str) -> Document | None:
        """Get a specific document by filename"""
        return self._documents[request_id].get(filename)

    def get_documents(self, request_id: str) -> list[Document]:
        """Get all documents for a request"""
        return list(self._documents[request_id].values())

    def get_documents_by_classification(
        self, request_id: str, classification: str
    ) -> list[Document]:
        """Get documents with a specific classification"""
        documents = self.get_documents(request_id)
        return [
            doc
            for doc in documents
            if doc.classification == classification
            or doc.human_decision == classification
        ]

    def get_unreviewed_documents(self, request_id: str) -> list[Document]:
        """Get documents that haven't been reviewed"""
        documents = self.get_documents(request_id)
        return [doc for doc in documents if doc.human_decision is None]

    def get_reviewed_documents(self, request_id: str) -> list[Document]:
        """Get documents that have been reviewed"""
        documents = self.get_documents(request_id)
        return [doc for doc in documents if doc.human_decision is not None]

    def update_document(self, request_id: str, filename: str, **kwargs: Any) -> bool:
        """Update document fields"""
        document = self.get_document(request_id, filename)
        if not document:
            return False

        # Update allowed fields
        allowed_fields = {
            "classification",
            "confidence",
            "justification",
            "exemptions",
            "human_decision",
            "human_feedback",
            "is_duplicate",
            "duplicate_of",
            "similarity_score",
        }

        for field, value in kwargs.items():
            if field in allowed_fields and hasattr(document, field):
                setattr(document, field, value)

        return True

    def get_document_count(self, request_id: str) -> int:
        """Get total number of documents for a request"""
        return len(self._documents[request_id])

    def clear_request(self, request_id: str) -> None:
        """Clear all documents for a request"""
        if request_id in self._documents:
            del self._documents[request_id]

    def clear_all(self) -> None:
        """Clear all documents (for testing purposes)"""
        self._documents.clear()

    def get_statistics(self, request_id: str) -> dict[str, int]:
        """Get classification statistics for a request"""
        documents = self.get_documents(request_id)

        stats = {
            "total": len(documents),
            "reviewed": 0,
            "responsive": 0,
            "non_responsive": 0,
            "uncertain": 0,
            "has_exemptions": 0,
        }

        for doc in documents:
            # Use human decision if available, otherwise AI classification
            classification = doc.human_decision or doc.classification

            if doc.human_decision is not None:
                stats["reviewed"] += 1

            if classification == "responsive":
                stats["responsive"] += 1
            elif classification == "non-responsive":
                stats["non_responsive"] += 1
            elif classification == "uncertain":
                stats["uncertain"] += 1

            if doc.exemptions:
                stats["has_exemptions"] += 1

        return stats

    def has_documents(self, request_id: str) -> bool:
        """Check if a request has any documents"""
        return request_id in self._documents and len(self._documents[request_id]) > 0
