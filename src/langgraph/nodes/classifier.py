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

        # Log feedback summary once per batch
        current_filename = state.get('filename', 'unknown')
        if feedback_examples and not hasattr(classify_document, '_feedback_logged'):
            logger.info(f"Classifier using {len(feedback_examples)} feedback examples")
            classify_document._feedback_logged = True

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
1. FIRST check filename patterns - if ALL files with a prefix were corrected the same way, apply that pattern
2. THEN check content patterns - if content matches corrections, follow the human correction
3. Filename patterns are STRONG indicators - humans often organize files by type

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

            # Analyze filename patterns in feedback
            filename_prefix_patterns = {}
            for example in feedback_examples:
                filename = example.get('document_filename', '')
                if filename:
                    # Extract prefix (e.g., 'email', 'memo', 'report')
                    prefix = filename.split('_')[0] if '_' in filename else filename.split('.')[0]
                    human_class = example.get('human_correction', 'unknown')

                    if prefix not in filename_prefix_patterns:
                        filename_prefix_patterns[prefix] = {}
                    if human_class not in filename_prefix_patterns[prefix]:
                        filename_prefix_patterns[prefix][human_class] = 0
                    filename_prefix_patterns[prefix][human_class] += 1

            # Count correction patterns
            correction_patterns = {}
            for example in feedback_examples:
                pattern = f"{example.get('ai_classification', 'unknown')} → {example.get('human_correction', 'unknown')}"
                correction_patterns[pattern] = correction_patterns.get(pattern, 0) + 1

            # Show filename patterns FIRST
            if filename_prefix_patterns:
                system_prompt += "\n📁 FILENAME PATTERN ANALYSIS:\n"
                for prefix, classifications in filename_prefix_patterns.items():
                    total = sum(classifications.values())
                    system_prompt += f"\nFilenames starting with '{prefix}_' or '{prefix}.':\n"
                    for classification, count in classifications.items():
                        percentage = (count / total) * 100
                        system_prompt += f"  - {count}/{total} ({percentage:.0f}%) corrected to: {classification}\n"
                    # Add rule if pattern is unanimous
                    if len(classifications) == 1:
                        only_class = list(classifications.keys())[0]
                        system_prompt += f"  ⚠️ RULE: ALL '{prefix}' files were corrected to {only_class}\n"

            # Show patterns after filename analysis
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

🎯 FILENAME-AWARE CLASSIFICATION RULES:
1. ALWAYS check filename prefix patterns FIRST
2. If ALL corrections for a filename prefix go the same way → APPLY THAT PATTERN
3. Then check content for additional patterns
4. Filename patterns + content patterns = VERY STRONG signal

⚡ CLASSIFICATION PRIORITY ORDER:
1. IF filename prefix has unanimous correction pattern (100% same classification):
    → APPLY that classification immediately
2. ELSE IF document mentions the SAME specific topics/projects as corrections:
    → Apply the correction classification
3. ELSE IF filename prefix has a strong pattern (>80% same classification):
    → Strongly consider that classification
4. ELSE:
    → Use standard FOIA classification

❌ FORBIDDEN: Ignoring patterns because you think you know better
✅ REQUIRED: Following human correction patterns exactly

Remember: The human already reviewed documents JUST LIKE THIS ONE and corrected your mistakes. Don't make the same mistake again!"""


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

            🔍 CURRENT DOCUMENT FILENAME: {filename}
            
            📄 FILENAME ANALYSIS:
            - Prefix: {filename_prefix}
            - Check the FILENAME PATTERN ANALYSIS above for rules about '{filename_prefix}' files
            - If a unanimous pattern exists for '{filename_prefix}' files, YOU MUST FOLLOW IT

            Document Content:
            {content}

            Classify this document and explain your reasoning. Remember to check filename patterns FIRST.""",
                ),
            ]
        )

        # Create the chain with JSON output parser
        parser = JsonOutputParser(pydantic_object=ClassificationResult)
        chain = prompt | llm | parser

        # Extract filename prefix for the prompt
        current_filename = state.get("filename", "")
        filename_prefix = current_filename.split('_')[0] if '_' in current_filename else current_filename.split('.')[0]

        # Get the classification
        result = chain.invoke({
            "foia_request": state["foia_request"],
            "filename": state["filename"],
            "filename_prefix": filename_prefix,
            "content": state["content"]
        })

        # Log the AI's response to see if it's considering feedback (only for key documents)
        if current_filename.endswith('_001.txt') or 'email_blue_sky' in current_filename:
            logger.debug(f"AI response for {current_filename}: "
                        f"classification={result['classification']}, "
                        f"confidence={result['confidence']:.1%}")

        # Log to audit trail if audit_manager is available
        audit_manager = state.get("audit_manager")
        filename = state.get("filename", "unknown")
        request_id = state.get("request_id", "unknown")
        
        logger.info(f"🔍 CLASSIFIER: About to log classification for {filename}")
        logger.info(f"🔍 CLASSIFIER: audit_manager type: {type(audit_manager)}")
        logger.info(f"🔍 CLASSIFIER: request_id: {request_id}")
        
        if audit_manager:
            logger.info(f"🔍 CLASSIFIER: Calling log_classification for {filename}: {result['classification']} ({result['confidence']:.2f})")
            audit_manager.log_classification(
                filename=filename,
                result=result["classification"],
                confidence=result["confidence"],
                request_id=request_id
            )
            logger.info(f"🔍 CLASSIFIER: log_classification call completed")
        else:
            logger.warning(f"🔍 CLASSIFIER: No audit_manager in state!")

        # Result is already parsed by JsonOutputParser (returns dict)
        return {
            "classification": result["classification"],
            "confidence": result["confidence"],
            "justification": result["justification"],
        }

    except Exception as e:
        # Log error to audit trail if audit_manager is available
        audit_manager = state.get("audit_manager")
        if audit_manager:
            audit_manager.log_error(
                filename=state.get("filename"),
                error_message=str(e),
                request_id=state.get("request_id", "unknown")
            )
        return create_error_response(e)
