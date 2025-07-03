"""In-memory storage for document embeddings with duplicate detection capabilities.
"""

import numpy as np


class EmbeddingStore:
    """In-memory storage for document embeddings with duplicate detection."""

    def __init__(self) -> None:
        """Initialize empty embedding store with request isolation."""
        # Store embeddings by request_id -> filename -> embedding
        self._embeddings: dict[str, dict[str, list[float]]] = {}
        # Store content hashes by request_id -> filename -> hash
        self._hashes: dict[str, dict[str, str]] = {}
        # Track processing order by request_id -> list of filenames
        self._processed_order: dict[str, list[str]] = {}

    def add_embedding(self, request_id: str, filename: str,
                     embedding: list[float], content_hash: str) -> None:
        """Store an embedding for a document.
        
        Args:
            request_id: The FOIA request ID
            filename: The document filename
            embedding: The embedding vector
            content_hash: The SHA-256 hash of the document content

        """
        # Initialize request storage if needed
        if request_id not in self._embeddings:
            self._embeddings[request_id] = {}
            self._hashes[request_id] = {}
            self._processed_order[request_id] = []

        # Store the embedding and hash
        self._embeddings[request_id][filename] = embedding
        self._hashes[request_id][filename] = content_hash
        self._processed_order[request_id].append(filename)

    def find_exact(self, request_id: str, content_hash: str) -> str | None:
        """Find exact duplicate by content hash.
        
        Args:
            request_id: The FOIA request ID
            content_hash: The SHA-256 hash to search for
            
        Returns:
            Filename of the first matching document, or None if no match

        """
        request_hashes = self._hashes.get(request_id, {})

        for filename, stored_hash in request_hashes.items():
            if stored_hash == content_hash:
                return filename

        return None

    def find_similar(self, request_id: str, embedding: list[float],
                    threshold: float = 0.85) -> list[tuple[str, float]]:
        """Find similar documents using cosine similarity.
        
        Args:
            request_id: The FOIA request ID
            embedding: The embedding vector to compare against
            threshold: Minimum similarity score (0-1) to be considered similar
            
        Returns:
            List of (filename, similarity_score) tuples sorted by similarity

        """
        similar_docs = []
        request_embeddings = self._embeddings.get(request_id, {})

        for filename, stored_embedding in request_embeddings.items():
            similarity = self._cosine_similarity(embedding, stored_embedding)
            if similarity >= threshold:
                similar_docs.append((filename, similarity))

        # Sort by similarity score (highest first)
        return sorted(similar_docs, key=lambda x: x[1], reverse=True)

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Cosine similarity score between 0 and 1

        """
        # Convert to numpy arrays
        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)

        # Calculate dot product
        dot_product = np.dot(vec1_array, vec2_array)

        # Calculate norms
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)

        # Handle zero vectors
        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Calculate cosine similarity
        return float(dot_product / (norm1 * norm2))

    def clear_request(self, request_id: str) -> None:
        """Clear all embeddings for a specific request.
        
        Args:
            request_id: The FOIA request ID to clear

        """
        self._embeddings.pop(request_id, None)
        self._hashes.pop(request_id, None)
        self._processed_order.pop(request_id, None)

    def get_processed_count(self, request_id: str) -> int:
        """Get the number of processed documents for a request.
        
        Args:
            request_id: The FOIA request ID
            
        Returns:
            Number of documents with stored embeddings

        """
        return len(self._embeddings.get(request_id, {}))
    
    def to_dict(self) -> dict:
        """Convert store to dictionary for serialization.
        
        Returns:
            Dictionary representation of the store
        """
        return {
            "embeddings": self._embeddings,
            "hashes": self._hashes,
            "processed_order": self._processed_order
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EmbeddingStore":
        """Create store from dictionary.
        
        Args:
            data: Dictionary representation of the store
            
        Returns:
            New EmbeddingStore instance
        """
        store = cls()
        store._embeddings = data.get("embeddings", {})
        store._hashes = data.get("hashes", {})
        store._processed_order = data.get("processed_order", {})
        return store
