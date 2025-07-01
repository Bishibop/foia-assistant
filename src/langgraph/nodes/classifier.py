from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...config import MODEL_CONFIG
from ...utils.error_handling import create_error_response
from ..state import DocumentState


class ClassificationResult(BaseModel):
    """Schema for document classification result."""

    classification: str = Field(
        description="One of: responsive, non_responsive, or uncertain"
    )
    confidence: float = Field(description="Confidence score between 0 and 1")
    justification: str = Field(
        description="Brief explanation of the classification decision"
    )


def classify_document(state: DocumentState) -> dict:
    """Classify document using OpenAI."""
    if state.get("error"):
        return {}

    # Check for API key
    import os

    if not os.getenv("OPENAI_API_KEY"):
        return create_error_response("OPENAI_API_KEY environment variable not set")

    try:
        # Initialize the model with JSON mode
        llm = ChatOpenAI(
            model=str(MODEL_CONFIG["classification_model"]),
            temperature=float(MODEL_CONFIG["temperature"]),
            model_kwargs={"response_format": {"type": "json_object"}},
        )

        # Create the classification prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a FOIA (Freedom of Information Act) response analyst.
            Your job is to classify documents based on whether they are responsive to a FOIA request.

            Classify documents as:
            - "responsive": The document directly relates to or discusses the topic in the FOIA request
            - "non_responsive": The document is clearly unrelated to the FOIA request
            - "uncertain": You're not sure if the document is responsive (ambiguous cases)

            You must respond with valid JSON containing these exact fields:
            {{
                "classification": "responsive" or "non_responsive" or "uncertain",
                "confidence": 0.0 to 1.0,
                "justification": "your explanation here"
            }}""",
                ),
                (
                    "user",
                    """FOIA Request: {foia_request}

            Document Content:
            {content}

            Classify this document and explain your reasoning.""",
                ),
            ]
        )

        # Create the chain with JSON output parser
        parser = JsonOutputParser(pydantic_object=ClassificationResult)
        chain = prompt | llm | parser

        # Get the classification
        result = chain.invoke(
            {"foia_request": state["foia_request"], "content": state["content"]}
        )

        # Result is already parsed by JsonOutputParser (returns dict)
        return {
            "classification": result["classification"],
            "confidence": result["confidence"],
            "justification": result["justification"],
        }

    except Exception as e:
        return create_error_response(e)
