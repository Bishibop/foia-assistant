"""Node for checking if a document is a duplicate and handling accordingly."""

import logging

from ..state import DocumentState

logger = logging.getLogger(__name__)


def check_duplicate(state: DocumentState) -> dict:
    """Check if document is a duplicate and set classification accordingly.
    
    If the document is marked as a duplicate, this node will:
    1. Set classification to "duplicate"
    2. Set confidence to 1.0 (certain it's a duplicate)
    3. Set justification explaining it's a duplicate
    4. Skip further processing by not updating other fields
    
    Args:
        state: The document state
        
    Returns:
        Updated state dict with duplicate handling
    """
    # Log what we received
    logger.debug(
        f"Duplicate checker received: filename={state.get('filename')}, "
        f"is_duplicate={state.get('is_duplicate')}, duplicate_of={state.get('duplicate_of')}"
    )
    
    # If there's already an error, don't process
    if state.get("error"):
        return {}
    
    # Check if this document is marked as a duplicate
    if state.get("is_duplicate", False):
        duplicate_of = state.get("duplicate_of", "unknown")
        similarity_score = state.get("similarity_score", 1.0)
        
        # Log the duplicate detection
        logger.info(
            f"Document '{state.get('filename')}' is a duplicate of '{duplicate_of}' "
            f"with similarity score {similarity_score:.2%}. Skipping classification."
        )
        
        # Determine if it's an exact or near duplicate
        if similarity_score >= 0.99:
            duplicate_type = "exact duplicate"
        else:
            duplicate_type = f"near duplicate ({similarity_score:.0%} similar)"
        
        return {
            "classification": "duplicate",
            "confidence": 1.0,  # We're certain it's a duplicate based on embeddings
            "justification": f"This document is a {duplicate_type} of '{duplicate_of}'. "
                           f"Skipping AI classification to save API calls.",
            # Don't set exemptions - duplicates don't need exemption analysis
            "exemptions": []
        }
    
    # Not a duplicate, continue with normal processing
    logger.debug(f"Document '{state.get('filename')}' is not a duplicate, continuing to classification")
    return {}