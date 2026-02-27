"""Entity extraction from legal documents using LLM.

Extracts defined terms, parties, and obligations from legal text chunks.
"""

import json
from dataclasses import dataclass

from google import genai
from google.genai import types

from app.config import Settings
from app.logging import get_logger


@dataclass
class EntityExtractionResult:
    """Result from entity extraction."""

    terms: list[dict]  # [{"term": str, "definition": str}, ...]
    parties: list[dict]  # [{"name": str, "role": str}, ...]
    obligations: list[dict]  # [{"description": str, "party": str}, ...]
    doc_id: str
    anchor: str


ENTITY_EXTRACTION_PROMPT = """Extract legal entities from the following text. Return a JSON object with three arrays:

1. "terms": Defined terms with their definitions. Format: [{{"term": "...", "definition": "..."}}]
2. "parties": Named parties mentioned. Format: [{{"name": "...", "role": "..."}}]
3. "obligations": Obligations or requirements. Format: [{{"description": "...", "party": "..."}}]

Rules:
- Only extract explicit, clear entities
- Do not infer or assume information not present in the text
- Return empty arrays if no entities of that type are found
- Keep definitions concise (max 200 chars)
- For parties, "role" can be: "buyer", "seller", "provider", "client", "other"

Text to analyze:
{text}

Return ONLY valid JSON, no additional text or explanation."""


def extract_entities_from_text(
    text: str, anchor: str, doc_id: str, settings: Settings
) -> EntityExtractionResult:
    """Extract entities from a single text chunk using LLM.

    Args:
        text: Text content to extract entities from.
        anchor: Source anchor (page/paragraph reference).
        doc_id: Source document identifier.
        settings: Application settings with Gemini API configuration.

    Returns:
        EntityExtractionResult with extracted entities and provenance.

    Raises:
        ValueError: If API key not configured or response invalid.
    """
    logger = get_logger(__name__)

    if not settings.gemini_api_key:
        logger.error("gemini_api_key_missing")
        raise ValueError("Gemini API key not configured")

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = ENTITY_EXTRACTION_PROMPT.format(text=text[:2000])  # Limit input length

    try:
        logger.debug("entity_extraction_start", doc_id=doc_id, anchor=anchor)

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=1024,
                thinking_config=types.ThinkingConfig(thinking_budget=1024),
            )
        )

        if not response.text:
            logger.warning("entity_extraction_empty_response", doc_id=doc_id)
            return EntityExtractionResult(
                terms=[], parties=[], obligations=[], doc_id=doc_id, anchor=anchor
            )

        # Parse JSON response
        try:
            # Clean response text (remove markdown code blocks if present)
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            entities = json.loads(response_text)

            terms = entities.get("terms", [])
            parties = entities.get("parties", [])
            obligations = entities.get("obligations", [])

            logger.info(
                "entities_extracted",
                doc_id=doc_id,
                anchor=anchor,
                terms_count=len(terms),
                parties_count=len(parties),
                obligations_count=len(obligations),
            )

            return EntityExtractionResult(
                terms=terms,
                parties=parties,
                obligations=obligations,
                doc_id=doc_id,
                anchor=anchor,
            )

        except json.JSONDecodeError as e:
            logger.error(
                "entity_extraction_json_parse_failed",
                doc_id=doc_id,
                error=str(e),
                response_text=response_text[:200],
            )
            # Return empty result rather than failing
            return EntityExtractionResult(
                terms=[], parties=[], obligations=[], doc_id=doc_id, anchor=anchor
            )

    except Exception as e:
        error_str = str(e).lower()
        if "quota" in error_str or "resource" in error_str:
            logger.error("gemini_quota_exceeded", error=str(e))
            raise ValueError("API quota exceeded. Please try again later.") from e
        elif "timeout" in error_str or "deadline" in error_str:
            logger.error("gemini_timeout", error=str(e))
            raise ValueError("Request timed out. Please try again.") from e
        else:
            logger.error("entity_extraction_failed", doc_id=doc_id, error=str(e))
            # Return empty result for graceful degradation
            return EntityExtractionResult(
                terms=[], parties=[], obligations=[], doc_id=doc_id, anchor=anchor
            )


def extract_entities_from_chunks(
    chunks: list[tuple[str, str]], doc_id: str, settings: Settings
) -> list[EntityExtractionResult]:
    """Extract entities from multiple text chunks.

    Args:
        chunks: List of (anchor, text) tuples.
        doc_id: Source document identifier.
        settings: Application settings.

    Returns:
        List of EntityExtractionResult objects, one per chunk.
    """
    logger = get_logger(__name__)
    results = []

    # Process chunks sequentially for MVP (can be parallelized later)
    for anchor, text in chunks:
        try:
            result = extract_entities_from_text(text, anchor, doc_id, settings)
            results.append(result)
        except Exception as e:
            logger.error(
                "chunk_entity_extraction_failed",
                doc_id=doc_id,
                anchor=anchor,
                error=str(e),
            )
            # Continue processing other chunks
            results.append(
                EntityExtractionResult(
                    terms=[], parties=[], obligations=[], doc_id=doc_id, anchor=anchor
                )
            )

    logger.info(
        "batch_entity_extraction_complete",
        doc_id=doc_id,
        chunk_count=len(chunks),
        results_count=len(results),
    )

    return results


def merge_entity_results(results: list[EntityExtractionResult]) -> dict:
    """Merge entity extraction results from multiple chunks.

    Deduplicates entities based on name/term.

    Args:
        results: List of EntityExtractionResult objects.

    Returns:
        Dict with merged terms, parties, obligations arrays.
    """
    merged = {"terms": [], "parties": [], "obligations": []}

    # Use sets to track seen entities (simple deduplication)
    seen_terms = set()
    seen_parties = set()
    seen_obligations = set()

    for result in results:
        # Merge terms
        for term in result.terms:
            term_key = term.get("term", "").lower()
            if term_key and term_key not in seen_terms:
                seen_terms.add(term_key)
                merged["terms"].append(term)

        # Merge parties
        for party in result.parties:
            party_key = party.get("name", "").lower()
            if party_key and party_key not in seen_parties:
                seen_parties.add(party_key)
                merged["parties"].append(party)

        # Merge obligations
        for obligation in result.obligations:
            obligation_key = obligation.get("description", "").lower()[:100]
            if obligation_key and obligation_key not in seen_obligations:
                seen_obligations.add(obligation_key)
                merged["obligations"].append(obligation)

    return merged
