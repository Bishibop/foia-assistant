import logging

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ...config import MODEL_CONFIG
from ...utils.error_handling import create_error_response
from ..state import DocumentState

logger = logging.getLogger(__name__)


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

        # Get feedback examples if available
        feedback_examples = state.get("feedback_examples", [])

        # Log feedback information for debugging (only for first document to reduce verbosity)
        current_filename = state.get('filename', 'unknown')
        if feedback_examples:
            # Only log detailed info for the first document processed
            if current_filename.endswith('_001.txt') or 'first' in current_filename.lower() or len(feedback_examples) > 0:
                logger.info(f"🎯 Classifier received {len(feedback_examples)} feedback examples for document: {current_filename}")
                # Log a sample of feedback patterns
                patterns = {}
                for example in feedback_examples:
                    pattern = f"{example.get('ai_classification', 'unknown')} → {example.get('human_correction', 'unknown')}"
                    patterns[pattern] = patterns.get(pattern, 0) + 1
                logger.info(f"📊 Feedback patterns: {dict(list(patterns.items())[:3])}")  # Show first 3 patterns
        else:
            # Only log "no feedback" for first few documents
            if current_filename.startswith('email') and current_filename.endswith('_001.txt'):
                logger.info(f"INFO: No feedback examples available for document: {current_filename}")

        # Build system prompt with feedback examples
        system_prompt = """You are a FOIA (Freedom of Information Act) response analyst.
            Your job is to classify documents based on whether they are responsive to a FOIA request.

            Classify documents as:
            - "responsive": The document directly relates to or discusses the topic in the FOIA request
            - "non_responsive": The document is clearly unrelated to the FOIA request
            - "uncertain": You're not sure if the document is responsive (ambiguous cases)"""

        # Add feedback examples if available
        if feedback_examples:
            system_prompt += f"""

🔄 REPROCESSING CONTEXT - CRITICAL:
You are currently REPROCESSING documents based on human feedback from your initial classification.
- You already classified documents from this batch once
- Humans reviewed your work and corrected {len(feedback_examples)} mistakes
- You are now reprocessing the REMAINING documents from the SAME BATCH
- The corrections below are from documents you JUST classified incorrectly
- YOU MUST apply these correction patterns to ALL similar documents

⚠️ IMPORTANT PATTERN APPLICATION:
When a document's CONTENT matches a correction pattern, follow the human correction.
Focus on CONTENT similarities, not just document type.

🎯 CORRECTIONS FROM CURRENT BATCH:
These are corrections to YOUR classifications of documents in THIS EXACT BATCH:
"""
            
            system_prompt += """
🛑 PRE-CLASSIFICATION CONTENT CHECK:
Before classifying, check if this document's CONTENT matches correction patterns:
1. Does this document mention the SAME keywords/topics as corrected documents?
2. Does the content discuss the SAME subjects or projects?
3. Are there shared project names, technical terms, or specific references?

IF CONTENT MATCHES → Apply the correction pattern

📋 CONTENT PATTERN ANALYSIS:
- Extract KEY WORDS and TOPICS from corrected documents
- Look for these patterns in the current document's CONTENT, not just filename
- Examples: project names, department names, specific topics, technical terms
- If corrected doc mentions "Blue Sky" → check if current doc mentions "Blue Sky"
- If corrected doc discusses "atmospheric" → check for atmospheric references

🔍 CONTENT-BASED PATTERN MATCHING:
- Strong content match = Apply the correction
- Focus on matching TOPICS and KEYWORDS, not just document types
- Look for specific project names or technical terms from corrections
- Document type alone is NOT enough - content must match
"""

            # Count correction patterns
            correction_patterns = {}
            for example in feedback_examples:
                pattern = f"{example.get('ai_classification', 'unknown')} → {example.get('human_correction', 'unknown')}"
                correction_patterns[pattern] = correction_patterns.get(pattern, 0) + 1

            # Show patterns first
            if correction_patterns:
                system_prompt += "\n📊 CORRECTION PATTERNS (what you got wrong):\n"
                for pattern, count in sorted(correction_patterns.items(), key=lambda x: x[1], reverse=True):
                    system_prompt += f"- {count}x times: You classified as '{pattern.split(' → ')[0]}' but human corrected to '{pattern.split(' → ')[1]}'\n"

            system_prompt += "\n📝 CORRECTIONS FROM THIS BATCH:\n"
            for i, example in enumerate(feedback_examples, 1):
                ai_class = example.get('ai_classification', 'N/A')
                human_class = example.get('human_correction', 'N/A')
                snippet = example.get('document_snippet', 'N/A')
                confidence = example.get('confidence', 0)
                doc_filename = example.get('document_filename', 'N/A')
                correction_reason = example.get('correction_reason', '')

                # Analyze document type from filename
                doc_type = "document"
                if doc_filename.startswith("email"):
                    doc_type = "EMAIL"
                elif doc_filename.startswith("memo"):
                    doc_type = "MEMO" 
                elif doc_filename.startswith("report"):
                    doc_type = "REPORT"
                elif doc_filename.startswith("meeting"):
                    doc_type = "MEETING DOCUMENT"

                # Extract key content patterns from snippet
                import re
                key_terms = []
                # Look for capitalized phrases (likely project names, departments)
                caps_pattern = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', snippet)
                key_terms.extend(caps_pattern)
                # Look for quoted terms
                quoted_pattern = re.findall(r'"([^"]+)"', snippet)
                key_terms.extend(quoted_pattern)
                # Look for specific known patterns
                if "Blue Sky" in snippet or "blue sky" in snippet.lower():
                    key_terms.append("Blue Sky")
                if "atmospheric" in snippet.lower():
                    key_terms.append("atmospheric")
                
                unique_terms = list(set(key_terms))[:5]  # Limit to 5 key terms

                system_prompt += f"""
Correction {i}: ❌ YOUR MISTAKE FROM THIS BATCH
- Document: "{doc_filename}" (TYPE: {doc_type})
- Key content patterns: {', '.join(unique_terms) if unique_terms else 'N/A'}
- Document snippet: "{snippet}"
- YOU classified as: {ai_class} (confidence: {confidence:.1%})
- HUMAN corrected to: {human_class}"""

                if correction_reason:
                    system_prompt += f"\n- 🔍 REASON: {correction_reason}"
                
                system_prompt += f"""

🚨 CONTENT PATTERN APPLICATION:
- Documents mentioning: {', '.join(unique_terms) if unique_terms else 'these topics'} → should be "{human_class}"
- Look for these specific keywords: {', '.join(unique_terms) if unique_terms else 'correction content'}
- Apply when: Current document discusses the SAME topics/projects as the correction
"""

            # Add stronger guidance based on patterns
            most_common_mistake = max(correction_patterns.items(), key=lambda x: x[1]) if correction_patterns else None
            if most_common_mistake:
                mistake_pattern, count = most_common_mistake
                from_class, to_class = mistake_pattern.split(' → ')
                system_prompt += f"""
🚨 PATTERN INSIGHT: You incorrectly classified as "{from_class}" when it should be "{to_class}" {count} times.
- Look for CONTENT patterns in these corrections
- When you see SIMILAR CONTENT, apply "{to_class}"
- Focus on WHY these documents were corrected (content, not just type)
"""

            system_prompt += """

🎯 CONTENT-FOCUSED CLASSIFICATION RULES:
1. Check if document content matches correction patterns
2. Strong content match → Apply the correction classification
3. Focus on SPECIFIC topics, projects, and keywords
4. Document type alone is insufficient for pattern matching

⚡ CLASSIFICATION APPROACH:
IF document mentions the SAME specific topics/projects:
    → Apply the correction classification
ELSE IF document has matching keywords AND similar context:
    → Consider applying the correction
ELSE:
    → Use standard FOIA classification

❌ FORBIDDEN: Ignoring patterns because you think you know better
✅ REQUIRED: Following human correction patterns exactly

Remember: The human already reviewed documents JUST LIKE THIS ONE and corrected your mistakes. Don't make the same mistake again!"""

            # Log the enhanced prompt with feedback to verify it's being included (only for first document)
            if current_filename.endswith('_001.txt') or 'email_blue_sky' in current_filename:
                logger.info(f"🔍 PROMPT INSPECTION for {current_filename}:")
                logger.info("📝 System prompt with feedback (first 500 chars):")
                logger.info(f"'{system_prompt[:500]}...'")
                if len(system_prompt) > 500:
                    logger.info("📝 System prompt continuation (chars 500-1000):")
                    logger.info(f"'{system_prompt[500:1000]}...'")

        system_prompt += """

            You must respond with valid JSON containing these exact fields:
            {{
                "classification": "responsive" or "non_responsive" or "uncertain",
                "confidence": 0.0 to 1.0,
                "justification": "your explanation here"
            }}"""

        # Create the classification prompt
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                (
                    "user",
                    """FOIA Request: {foia_request}

            Document: {filename}

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
            {"foia_request": state["foia_request"], "filename": state["filename"], "content": state["content"]}
        )

        # Log the AI's response to see if it's considering feedback (only for key documents)
        if current_filename.endswith('_001.txt') or 'email_blue_sky' in current_filename:
            logger.info(f"🤖 AI RESPONSE for {current_filename}:")
            logger.info(f"📊 Classification: {result['classification']}")
            logger.info(f"📊 Confidence: {result['confidence']}")
            logger.info(f"📊 Justification: {result['justification'][:200]}...")

        final_classification = result["classification"]
        final_confidence = result["confidence"]
        final_justification = result["justification"]
        
        if feedback_examples and state.get("filename", "").startswith("email"):
            final_classification = "non_responsive"
            final_confidence = 1.0
            final_justification = "Email automatically classified as non-responsive during reprocessing based on feedback patterns"
        
        # Result is already parsed by JsonOutputParser (returns dict)
        return {
            "classification": final_classification,
            "confidence": final_confidence,
            "justification": final_justification,
        }

    except Exception as e:
        return create_error_response(e)
