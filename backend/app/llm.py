"""LLM integration for cited answer generation using Google Gemini.

Enforces mandatory citations and abstain logic for insufficient evidence.
"""

import re
from dataclasses import dataclass

from google import genai
from google.genai import types

from app.config import Settings
from app.logging import get_logger
from app.prompts import SYSTEM_PROMPT, build_answer_prompt


@dataclass
class Citation:
    """A parsed citation reference."""

    context_number: int
    doc_id: str
    anchor: str


@dataclass
class AnswerResult:
    """Result from LLM answer generation."""

    answer: str
    citations: list[Citation]
    abstained: bool
    confidence: float
    raw_response: str


def generate_answer(
    query: str, contexts: list[dict], settings: Settings
) -> AnswerResult:
    """Generate a cited answer using Gemini API.

    Args:
        query: User's question.
        contexts: List of context dicts with chunk_text, doc_id, anchor_start keys.
        settings: App settings with API key and model config.

    Returns:
        AnswerResult with answer text, parsed citations, and metadata.

    Raises:
        ValueError: If API key not configured.
        Exception: If Gemini API call fails.
    """
    logger = get_logger(__name__)

    if not settings.gemini_api_key:
        logger.error("gemini_api_key_missing")
        raise ValueError("Gemini API key not configured")

    client = genai.Client(api_key=settings.gemini_api_key)

    user_prompt = build_answer_prompt(query, contexts)
    full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

    try:
        logger.info(
            "llm_request_start",
            model=settings.gemini_model,
            context_count=len(contexts),
        )

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,  # Deterministic for citations
                top_p=1.0,
                top_k=1,
                max_output_tokens=2048,
            )
        )

        if not response.text:
            logger.error("gemini_empty_response")
            raise ValueError("Empty response from Gemini API")

        answer_text = response.text
        logger.info("llm_response_received")

    except Exception as e:
        error_str = str(e).lower()
        if "quota" in error_str or "resource" in error_str:
            logger.error("gemini_quota_exceeded", error=str(e))
            raise ValueError("API quota exceeded. Please try again later.") from e
        elif "timeout" in error_str or "deadline" in error_str:
            logger.error("gemini_timeout", error=str(e))
            raise ValueError("Request timed out. Please try again.") from e
        else:
            logger.error("gemini_api_error", error=str(e))
            raise

    # Check if LLM abstained
    abstained = answer_text.strip().startswith("INSUFFICIENT EVIDENCE:")

    # Parse citations from answer
    citations = parse_citations(answer_text, contexts) if not abstained else []

    # Validate citations match provided contexts
    valid_citations = citations
    if citations and not abstained:
        valid_citations = validate_citations(citations, contexts)
        if len(valid_citations) < len(citations):
            logger.warning(
                "invalid_citations_filtered",
                original_count=len(citations),
                valid_count=len(valid_citations),
            )

    # Simple confidence heuristic
    confidence = 0.0
    if abstained:
        confidence = 0.0
    elif valid_citations:
        confidence = min(0.95, 0.7 + (len(valid_citations) * 0.05))
    else:
        confidence = 0.3  # Low confidence if no citations

    return AnswerResult(
        answer=answer_text,
        citations=valid_citations,
        abstained=abstained,
        confidence=confidence,
        raw_response=answer_text,
    )


def parse_citations(answer_text: str, contexts: list[dict]) -> list[Citation]:
    """Extract citation references from answer text.

    Parses patterns like [1], [2], [3] and maps them to document anchors.

    Args:
        answer_text: Generated answer text with citations.
        contexts: List of context dicts to map citation numbers to doc IDs.

    Returns:
        List of Citation objects with context_number, doc_id, anchor.
    """
    citation_pattern = r"\[(\d+)\]"
    matches = re.findall(citation_pattern, answer_text)

    citations = []
    seen = set()

    for match in matches:
        context_num = int(match)
        if context_num in seen:
            continue
        seen.add(context_num)

        # Map citation number to context (1-indexed)
        if 1 <= context_num <= len(contexts):
            ctx = contexts[context_num - 1]
            citations.append(
                Citation(
                    context_number=context_num,
                    doc_id=ctx.get("doc_id", "unknown"),
                    anchor=ctx.get("anchor_start", "unknown"),
                )
            )

    return citations


def validate_citations(
    citations: list[Citation], contexts: list[dict]
) -> list[Citation]:
    """Validate that all citations reference valid context numbers.

    Args:
        citations: List of parsed citations.
        contexts: List of context dicts.

    Returns:
        List of valid citations (those within context bounds).
    """
    valid_citations = []
    max_context_num = len(contexts)

    for citation in citations:
        if 1 <= citation.context_number <= max_context_num:
            valid_citations.append(citation)

    return valid_citations
