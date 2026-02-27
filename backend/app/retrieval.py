"""GraphRAG retrieval combining graph queries and vector search.

Two-stage retrieval:
1. Graph query finds candidate documents based on entities
2. Vector search restricted to candidates + ACL enforcement
"""

import json
from dataclasses import dataclass
from typing import Optional

from google import genai
from google.genai import types
from neo4j.exceptions import ServiceUnavailable, ClientError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.graph import Neo4jConnection, get_graph_connection
from app.embeddings import generate_embedding
from app.logging import get_logger
from app.models import Chunk


@dataclass
class QueryEntities:
    """Entities extracted from user query."""

    terms: list[str]  # Defined terms to look for
    parties: list[str]  # Party names mentioned
    concepts: list[str]  # General legal concepts


@dataclass
class ChunkContext:
    """Retrieved chunk with context for answer generation."""

    chunk_id: str
    doc_id: str
    chunk_text: str
    anchor_start: str
    anchor_end: str
    similarity_score: float
    source: str  # "graph" or "vector" or "both"


@dataclass
class RetrievalResult:
    """Result from GraphRAG retrieval."""

    chunks: list[ChunkContext]
    graph_candidates: list[str]  # Doc IDs from graph
    used_fallback: bool  # True if fell back to vector-only


QUERY_ENTITY_EXTRACTION_PROMPT = """Extract key entities and concepts from this legal query. Return JSON with three arrays:

1. "terms": Specific defined terms or legal terminology mentioned (e.g., "payment term", "warranty period")
2. "parties": Any party names or roles mentioned (e.g., "buyer", "seller", "Acme Corp")
3. "concepts": General legal concepts or topics (e.g., "payment", "termination", "liability")

Query: {query}

Return ONLY valid JSON, no additional text:
{{"terms": [], "parties": [], "concepts": []}}"""


def extract_query_entities(query: str, settings: Settings) -> QueryEntities:
    """Extract entities from user query using LLM.

    Args:
        query: User's question.
        settings: Application settings with Gemini API key.

    Returns:
        QueryEntities with extracted terms, parties, concepts.
    """
    logger = get_logger(__name__)

    if not settings.gemini_api_key:
        logger.warning("gemini_api_key_missing_for_entity_extraction")
        return QueryEntities(terms=[], parties=[], concepts=[])

    client = genai.Client(api_key=settings.gemini_api_key)

    prompt = QUERY_ENTITY_EXTRACTION_PROMPT.format(query=query)

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=512,
                thinking_config=types.ThinkingConfig(thinking_budget=1024),
            )
        )

        if not response.text:
            logger.warning("query_entity_extraction_empty_response")
            return QueryEntities(terms=[], parties=[], concepts=[])

        # Parse JSON response
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text.replace("```json", "").replace("```", "").strip()
        elif response_text.startswith("```"):
            response_text = response_text.replace("```", "").strip()

        entities = json.loads(response_text)

        return QueryEntities(
            terms=entities.get("terms", []),
            parties=entities.get("parties", []),
            concepts=entities.get("concepts", []),
        )

    except (json.JSONDecodeError, Exception) as e:
        logger.warning("query_entity_extraction_failed", error=str(e))
        return QueryEntities(terms=[], parties=[], concepts=[])


def graph_candidate_search(
    entities: QueryEntities, matter_id: str, connection: Neo4jConnection
) -> list[str]:
    """Search Neo4j for candidate document IDs based on entities.

    Args:
        entities: Extracted query entities.
        matter_id: Matter scope for search.
        connection: Neo4j connection.

    Returns:
        List of candidate document IDs.
    """
    logger = get_logger(__name__)
    candidate_doc_ids = set()

    with connection.session() as session:
        # Query 1: Find documents with matching defined terms
        for term in entities.terms:
            try:
                query = """
                MATCH (m:Matter {matter_id: $matter_id})-[:HAS_DOCUMENT]->(d:Document)
                      -[:DEFINES]->(t:DefinedTerm)
                WHERE toLower(t.term) CONTAINS toLower($term)
                RETURN DISTINCT d.doc_id as doc_id
                LIMIT 10
                """
                result = session.run(query, matter_id=matter_id, term=term)
                for record in result:
                    candidate_doc_ids.add(record["doc_id"])
            except (ServiceUnavailable, ClientError) as e:
                logger.error("graph_query_failed_terms", term=term, error=str(e))

        # Query 2: Find documents mentioning parties
        for party in entities.parties:
            try:
                query = """
                MATCH (m:Matter {matter_id: $matter_id})-[:HAS_DOCUMENT]->(d:Document)
                      -[:MENTIONS_PARTY]->(p:Party)
                WHERE toLower(p.name) CONTAINS toLower($party) OR toLower(p.role) CONTAINS toLower($party)
                RETURN DISTINCT d.doc_id as doc_id
                LIMIT 10
                """
                result = session.run(query, matter_id=matter_id, party=party)
                for record in result:
                    candidate_doc_ids.add(record["doc_id"])
            except (ServiceUnavailable, ClientError) as e:
                logger.error("graph_query_failed_parties", party=party, error=str(e))

        # Query 3: General document search by matter (fallback)
        if not candidate_doc_ids and entities.concepts:
            try:
                query = """
                MATCH (m:Matter {matter_id: $matter_id})-[:HAS_DOCUMENT]->(d:Document)
                RETURN DISTINCT d.doc_id as doc_id
                LIMIT 20
                """
                result = session.run(query, matter_id=matter_id)
                for record in result:
                    candidate_doc_ids.add(record["doc_id"])
            except (ServiceUnavailable, ClientError) as e:
                logger.error("graph_query_failed_general", error=str(e))

    logger.info("graph_candidates_found", count=len(candidate_doc_ids))
    return list(candidate_doc_ids)


def vector_search_with_candidates(
    query: str,
    candidates: Optional[list[str]],
    matter_id: str,
    top_k: int,
    session: Session,
    settings: Settings,
) -> list[ChunkContext]:
    """Vector similarity search restricted to candidate documents.

    Args:
        query: User query string.
        candidates: List of candidate doc_ids from graph (None for unrestricted).
        matter_id: Matter scope for ACL.
        top_k: Number of results to return.
        session: Database session.
        settings: Application settings.

    Returns:
        List of ChunkContext results.
    """
    logger = get_logger(__name__)

    query_embedding = generate_embedding(query, model_name=settings.embedding_model)

    # Build query with optional candidate filter
    base_query = (
        select(
            Chunk,
            Chunk.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .where(Chunk.matter_id == matter_id)
        .where(Chunk.embedding.isnot(None))
    )

    # Add candidate filter if provided
    if candidates:
        base_query = base_query.where(Chunk.doc_id.in_(candidates))

    base_query = base_query.order_by(
        Chunk.embedding.cosine_distance(query_embedding)
    ).limit(top_k)

    chunks_with_distance = session.execute(base_query).all()

    results = []
    for chunk, distance in chunks_with_distance:
        similarity = 1.0 - float(distance)
        source = "graph" if candidates and chunk.doc_id in candidates else "vector"

        results.append(
            ChunkContext(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                chunk_text=chunk.chunk_text,
                anchor_start=chunk.anchor_start,
                anchor_end=chunk.anchor_end,
                similarity_score=similarity,
                source=source,
            )
        )

    logger.info(
        "vector_search_complete",
        result_count=len(results),
        with_candidates=candidates is not None,
    )

    return results


def fuse_results(
    graph_results: list[ChunkContext], vector_results: list[ChunkContext], top_k: int
) -> list[ChunkContext]:
    """Fuse graph and vector results with score boosting.

    Args:
        graph_results: Results from graph-candidate vector search.
        vector_results: Results from full vector search.
        top_k: Number of final results to return.

    Returns:
        Fused and ranked list of ChunkContext.
    """
    logger = get_logger(__name__)

    # Merge results by chunk_id
    result_map = {}

    # Add graph results with boost
    for result in graph_results:
        boosted_score = result.similarity_score * 1.5
        result_map[result.chunk_id] = result
        result.similarity_score = min(1.0, boosted_score)  # Cap at 1.0
        result.source = "graph"

    # Add vector results (may update existing)
    for result in vector_results:
        if result.chunk_id in result_map:
            # Already present from graph - mark as "both"
            result_map[result.chunk_id].source = "both"
        else:
            result_map[result.chunk_id] = result
            result.source = "vector"

    # Sort by score and return top-k
    sorted_results = sorted(
        result_map.values(), key=lambda x: x.similarity_score, reverse=True
    )

    logger.info("results_fused", total_unique=len(sorted_results), top_k=top_k)

    return sorted_results[:top_k]


def retrieve_with_graph(
    query: str, matter_id: str, session: Session, settings: Settings, top_k: int = 10
) -> RetrievalResult:
    """Main retrieval function using GraphRAG approach.

    Combines graph-based candidate selection with vector search.
    Falls back to vector-only if graph unavailable.

    Args:
        query: User query string.
        matter_id: Matter scope for ACL.
        session: Database session.
        settings: Application settings.
        top_k: Number of results to return.

    Returns:
        RetrievalResult with chunks and metadata.
    """
    logger = get_logger(__name__)

    used_fallback = False
    graph_candidates = []

    # Try graph-enhanced retrieval
    try:
        # Extract entities from query
        entities = extract_query_entities(query, settings)
        logger.info(
            "query_entities_extracted",
            terms_count=len(entities.terms),
            parties_count=len(entities.parties),
            concepts_count=len(entities.concepts),
        )

        # Get graph candidates
        if any([entities.terms, entities.parties, entities.concepts]):
            connection = get_graph_connection(settings)
            graph_candidates = graph_candidate_search(entities, matter_id, connection)

            # If no candidates at all, fall back to full vector search
            if len(graph_candidates) < 1:
                logger.info(
                    "graph_candidates_insufficient",
                    count=len(graph_candidates),
                    using_fallback=True,
                )
                graph_candidates = []
                used_fallback = True

    except Exception as e:
        logger.warning("graph_retrieval_failed", error=str(e))
        used_fallback = True

    # Perform vector search
    if graph_candidates:
        # Graph-enhanced: search within candidates
        chunks = vector_search_with_candidates(
            query, graph_candidates, matter_id, top_k, session, settings
        )
    else:
        # Fallback: full vector search
        chunks = vector_search_with_candidates(
            query, None, matter_id, top_k, session, settings
        )
        used_fallback = True

    logger.info(
        "retrieval_complete",
        chunk_count=len(chunks),
        graph_candidates=len(graph_candidates),
        used_fallback=used_fallback,
    )

    return RetrievalResult(
        chunks=chunks, graph_candidates=graph_candidates, used_fallback=used_fallback
    )
