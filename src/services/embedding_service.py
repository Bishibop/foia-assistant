"""Embedding service for generating document embeddings using OpenAI API.
"""
import hashlib
import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating document embeddings using OpenAI."""

    def __init__(self) -> None:
        """Initialize the embedding service with OpenAI client."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = OpenAI(api_key=api_key)
        self.model = "text-embedding-3-small"
        self.max_chars = 8000  # ~2000 tokens

    def generate_embedding(self, content: str) -> list[float] | None:
        """Generate embedding for document content.
        
        Args:
            content: The document content to generate embedding for
            
        Returns:
            List of float values representing the embedding, or None on error

        """
        # Truncate content to avoid token limits
        truncated_content = content[:self.max_chars]

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=truncated_content
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation error: {e!s}")
            return None

    def generate_content_hash(self, content: str) -> str:
        """Generate SHA-256 hash of content for exact duplicate detection.
        
        Args:
            content: The document content to hash
            
        Returns:
            Hexadecimal string representation of the content hash

        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
