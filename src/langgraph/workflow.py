from typing import Any, cast

from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from .nodes.classifier import classify_document
from .nodes.document_loader import load_document
from .nodes.duplicate_checker import check_duplicate
from .nodes.exemption_detector import detect_exemptions
from .state import DocumentState


def get_compiled_workflow() -> CompiledStateGraph[DocumentState, Any]:
    """Get or create the compiled workflow.

    Returns:
        Compiled LangGraph workflow

    """
    # Create a new graph
    workflow = StateGraph(DocumentState)

    # Add nodes
    workflow.add_node("load_document", load_document)
    workflow.add_node("check_duplicate", check_duplicate)
    workflow.add_node("classify", classify_document)
    workflow.add_node("detect_exemptions", detect_exemptions)

    # Define the flow with conditional routing
    workflow.add_edge("load_document", "check_duplicate")
    
    # Conditional edge from duplicate checker
    def route_after_duplicate_check(state: DocumentState) -> str:
        """Route based on whether document is a duplicate."""
        # Add debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Routing decision for {state.get('filename')}: classification={state.get('classification')}")
        
        # If document was classified as duplicate, skip to end
        if state.get("classification") == "duplicate":
            logger.info(f"Skipping classification for duplicate: {state.get('filename')}")
            return "end"
        # Otherwise continue to classification
        return "classify"
    
    workflow.add_conditional_edges(
        "check_duplicate",
        route_after_duplicate_check,
        {
            "classify": "classify",
            "end": "__end__"
        }
    )
    
    # Normal flow for non-duplicates
    workflow.add_edge("classify", "detect_exemptions")

    # Set the entry point
    workflow.set_entry_point("load_document")

    # Set the finish point (for non-duplicates)
    workflow.set_finish_point("detect_exemptions")

    # Compile and cache the workflow
    return workflow.compile()


def create_initial_state(filename: str, foia_request: str) -> DocumentState:
    """Create initial state for document processing.

    Args:
        filename: Path to document
        foia_request: FOIA request text

    Returns:
        Initial document state

    """
    return {
        "filename": filename,
        "foia_request": foia_request,
        "content": "",
        # Duplicate detection fields
        "is_duplicate": None,
        "duplicate_of": None,
        "similarity_score": None,
        "content_hash": None,
        "embedding_generated": None,
        # Classification fields
        "classification": None,
        "confidence": None,
        "justification": None,
        "exemptions": None,
        "human_decision": None,
        "human_feedback": None,
        "patterns_learned": None,
        "feedback_examples": None,
        "error": None,
    }


def process_document(filename: str, foia_request: str) -> DocumentState:
    """Process a single document through the workflow.

    Args:
        filename: Path to document to process
        foia_request: FOIA request to check against

    Returns:
        Document state after processing

    """
    # Get cached workflow
    app = get_compiled_workflow()

    # Create initial state
    initial_state = create_initial_state(filename, foia_request)

    # Run the workflow
    result = app.invoke(initial_state)

    # Cast result to DocumentState type
    return cast(DocumentState, result)
