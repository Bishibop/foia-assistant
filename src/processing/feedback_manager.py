"""Manages user feedback for improving AI classifications."""

import logging
from collections import defaultdict
from typing import Any

from src.models.document import Document
from src.models.feedback import FeedbackEntry

logger = logging.getLogger(__name__)


class FeedbackManager:
    """Manages user feedback for improving classifications."""

    def __init__(self) -> None:
        # Store feedback by request_id
        self._feedback: dict[str, list[FeedbackEntry]] = defaultdict(list)

    def add_feedback(
        self,
        document: Document,
        request_id: str,
        human_decision: str
    ) -> FeedbackEntry | None:
        """Record user feedback on a classification.
        
        Only records feedback when human overrides AI decision.
        
        Args:
            document: The document being reviewed
            request_id: The FOIA request ID
            human_decision: The human's classification decision
            
        Returns:
            FeedbackEntry if feedback was recorded, None if no change

        """
        # Only record if human overrode AI
        if document.classification == human_decision:
            return None

        # Create document snippet (first 200 chars)
        snippet = document.content[:200] if document.content else ""
        if len(document.content) > 200:
            snippet += "..."

        # Don't hardcode any classification rules - let the user's feedback speak for itself
        correction_reason = ""

        entry = FeedbackEntry(
            document_id=document.filename,
            request_id=request_id,
            original_classification=document.classification or "uncertain",
            human_decision=human_decision,
            original_confidence=document.confidence or 0.0,
            document_snippet=snippet,
            correction_reason=correction_reason
        )

        self._feedback[request_id].append(entry)
        logger.info(
            f"Recorded feedback for {document.filename}: "
            f"{entry.original_classification} -> {human_decision}"
        )

        return entry

    def get_all_feedback(self, request_id: str) -> list[dict[str, Any]]:
        """Get all feedback for a request formatted for prompts.
        
        Args:
            request_id: The FOIA request ID
            
        Returns:
            List of feedback examples formatted for inclusion in prompts

        """
        feedback_list = self._feedback.get(request_id, [])

        # Log detailed feedback information for debugging
        if feedback_list:
            logger.info(f"📋 FeedbackManager: Loading {len(feedback_list)} feedback examples for request {request_id}")
            for i, feedback in enumerate(feedback_list[:2]):  # Log first 2 examples
                logger.info(f"📝 Feedback {i+1}: {feedback.document_id} | {feedback.original_classification} → {feedback.human_decision}")
                logger.info(f"   Snippet: '{feedback.document_snippet[:100]}...'")
        else:
            logger.info(f"❌ FeedbackManager: No feedback found for request {request_id}")

        # Convert to format for prompt
        examples = []
        for feedback in feedback_list:
            examples.append({
                "document_filename": feedback.document_id,
                "document_snippet": feedback.document_snippet,
                "ai_classification": feedback.original_classification,
                "human_correction": feedback.human_decision,
                "confidence": feedback.original_confidence,
                "correction_reason": getattr(feedback, 'correction_reason', '')
            })

        # Log the formatted examples that will be sent to the classifier
        if examples:
            logger.info(f"🔄 FeedbackManager: Formatted {len(examples)} examples for classifier")
            for i, example in enumerate(examples[:1]):  # Log first example
                logger.info(f"📤 Example {i+1} to classifier: {example['document_filename']} | {example['ai_classification']} → {example['human_correction']}")

        return examples

    def get_statistics(self, request_id: str) -> dict[str, Any]:
        """Get feedback statistics for a request.
        
        Args:
            request_id: The FOIA request ID
            
        Returns:
            Dictionary with statistics about feedback

        """
        feedback_list = self._feedback.get(request_id, [])

        if not feedback_list:
            return {
                "total_corrections": 0,
                "most_corrected_type": "N/A"
            }

        # Count correction types
        corrections: dict[str, int] = defaultdict(int)
        for f in feedback_list:
            key = f"{f.original_classification} → {f.human_decision}"
            corrections[key] += 1

        most_common = max(corrections.items(), key=lambda x: x[1]) if corrections else ("N/A", 0)

        return {
            "total_corrections": len(feedback_list),
            "most_corrected_type": most_common[0],
            "correction_counts": dict(corrections)
        }

    def clear_feedback(self, request_id: str) -> None:
        """Clear all feedback for a request.
        
        Args:
            request_id: The FOIA request ID

        """
        if request_id in self._feedback:
            count = len(self._feedback[request_id])
            del self._feedback[request_id]
            logger.info(f"Cleared {count} feedback entries for request {request_id}")

    def has_feedback(self, request_id: str) -> bool:
        """Check if a request has any feedback.
        
        Args:
            request_id: The FOIA request ID
            
        Returns:
            True if feedback exists for the request

        """
        return request_id in self._feedback and len(self._feedback[request_id]) > 0
