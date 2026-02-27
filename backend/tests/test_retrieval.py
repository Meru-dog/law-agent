"""Tests for GraphRAG retrieval."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.config import Settings
from app.retrieval import (
    ChunkContext,
    QueryEntities,
    extract_query_entities,
    fuse_results,
    graph_candidate_search,
    retrieve_with_graph,
    vector_search_with_candidates,
)


@pytest.fixture
def mock_settings():
    """Mock settings with configuration."""
    settings = Settings()
    settings.gemini_api_key = "test-key"
    settings.gemini_model = "gemini-1.5-pro"
    settings.embedding_model = "all-MiniLM-L6-v2"
    settings.max_context_chunks = 10
    settings.neo4j_uri = "bolt://localhost:7687"
    settings.neo4j_user = "neo4j"
    settings.neo4j_password = "test"
    return settings


@pytest.fixture
def sample_chunks():
    """Sample chunk contexts for testing."""
    return [
        ChunkContext(
            chunk_id="chunk-1",
            doc_id="doc-123",
            chunk_text="Payment term is 30 days",
            anchor_start="page-1",
            anchor_end="page-1",
            similarity_score=0.9,
            source="graph",
        ),
        ChunkContext(
            chunk_id="chunk-2",
            doc_id="doc-123",
            chunk_text="Late fees apply",
            anchor_start="page-2",
            anchor_end="page-2",
            similarity_score=0.7,
            source="vector",
        ),
    ]


def test_extract_query_entities_success(mock_settings):
    """Test successful query entity extraction."""
    mock_response = Mock()
    mock_response.text = json.dumps({
        "terms": ["payment term", "warranty"],
        "parties": ["buyer", "seller"],
        "concepts": ["payment", "obligations"],
    })

    with patch("app.retrieval.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        entities = extract_query_entities("What is the payment term?", mock_settings)

        assert len(entities.terms) == 2
        assert len(entities.parties) == 2
        assert len(entities.concepts) == 2
        assert "payment term" in entities.terms


def test_extract_query_entities_no_api_key():
    """Test entity extraction without API key returns empty."""
    settings = Settings()
    settings.gemini_api_key = ""

    entities = extract_query_entities("test query", settings)

    assert len(entities.terms) == 0
    assert len(entities.parties) == 0
    assert len(entities.concepts) == 0


def test_extract_query_entities_json_parse_error(mock_settings):
    """Test entity extraction handles JSON parse errors."""
    mock_response = Mock()
    mock_response.text = "Not valid JSON"

    with patch("app.retrieval.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        entities = extract_query_entities("test query", mock_settings)

        # Should return empty on error
        assert len(entities.terms) == 0


def test_graph_candidate_search_with_terms():
    """Test graph candidate search finds documents by terms."""
    entities = QueryEntities(
        terms=["payment term"], parties=[], concepts=[]
    )

    mock_session = MagicMock()
    mock_record = {"doc_id": "doc-123"}
    mock_session.run.return_value = [mock_record]

    mock_connection = MagicMock()
    mock_connection.session.return_value.__enter__.return_value = mock_session

    candidates = graph_candidate_search(entities, "matter-1", mock_connection)

    assert "doc-123" in candidates
    assert mock_session.run.called


def test_graph_candidate_search_with_parties():
    """Test graph candidate search finds documents by parties."""
    entities = QueryEntities(
        terms=[], parties=["Acme Corp"], concepts=[]
    )

    mock_session = MagicMock()
    mock_record = {"doc_id": "doc-456"}
    mock_session.run.return_value = [mock_record]

    mock_connection = MagicMock()
    mock_connection.session.return_value.__enter__.return_value = mock_session

    candidates = graph_candidate_search(entities, "matter-1", mock_connection)

    assert "doc-456" in candidates


def test_graph_candidate_search_fallback_to_general():
    """Test graph search falls back to general query when no specific entities."""
    entities = QueryEntities(
        terms=[], parties=[], concepts=["general topic"]
    )

    mock_session = MagicMock()
    # First two queries return empty, third returns general results
    mock_session.run.return_value = [{"doc_id": "doc-general"}]

    mock_connection = MagicMock()
    mock_connection.session.return_value.__enter__.return_value = mock_session

    candidates = graph_candidate_search(entities, "matter-1", mock_connection)

    assert "doc-general" in candidates


def test_graph_candidate_search_deduplicates():
    """Test graph search deduplicates document IDs."""
    entities = QueryEntities(
        terms=["term1", "term2"], parties=[], concepts=[]
    )

    mock_session = MagicMock()
    # Both queries return same doc
    mock_session.run.return_value = [{"doc_id": "doc-123"}]

    mock_connection = MagicMock()
    mock_connection.session.return_value.__enter__.return_value = mock_session

    candidates = graph_candidate_search(entities, "matter-1", mock_connection)

    # Should only have one instance of doc-123
    assert candidates.count("doc-123") == 1


def test_vector_search_with_candidates(mock_settings):
    """Test vector search restricted to candidates."""
    mock_session = MagicMock()
    mock_chunk = Mock()
    mock_chunk.chunk_id = "chunk-1"
    mock_chunk.doc_id = "doc-123"
    mock_chunk.chunk_text = "Test text"
    mock_chunk.anchor_start = "page-1"
    mock_chunk.anchor_end = "page-1"

    mock_session.execute.return_value.all.return_value = [(mock_chunk, 0.1)]

    with patch("app.retrieval.generate_embedding") as mock_embed:
        mock_embed.return_value = [0.1] * 384

        results = vector_search_with_candidates(
            "test query",
            ["doc-123"],
            "matter-1",
            5,
            mock_session,
            mock_settings,
        )

        assert len(results) == 1
        assert results[0].doc_id == "doc-123"
        assert results[0].source == "graph"


def test_vector_search_without_candidates(mock_settings):
    """Test unrestricted vector search."""
    mock_session = MagicMock()
    mock_chunk = Mock()
    mock_chunk.chunk_id = "chunk-1"
    mock_chunk.doc_id = "doc-123"
    mock_chunk.chunk_text = "Test text"
    mock_chunk.anchor_start = "page-1"
    mock_chunk.anchor_end = "page-1"

    mock_session.execute.return_value.all.return_value = [(mock_chunk, 0.2)]

    with patch("app.retrieval.generate_embedding") as mock_embed:
        mock_embed.return_value = [0.1] * 384

        results = vector_search_with_candidates(
            "test query",
            None,  # No candidates = unrestricted
            "matter-1",
            5,
            mock_session,
            mock_settings,
        )

        assert len(results) == 1
        assert results[0].source == "vector"


def test_fuse_results_boosts_graph_scores():
    """Test fusion applies score boost to graph results."""
    graph_results = [
        ChunkContext(
            chunk_id="chunk-1",
            doc_id="doc-123",
            chunk_text="Text",
            anchor_start="page-1",
            anchor_end="page-1",
            similarity_score=0.6,  # Should be boosted to 0.9
            source="graph",
        ),
    ]

    vector_results = [
        ChunkContext(
            chunk_id="chunk-2",
            doc_id="doc-456",
            chunk_text="Text",
            anchor_start="page-2",
            anchor_end="page-2",
            similarity_score=0.8,  # No boost
            source="vector",
        ),
    ]

    fused = fuse_results(graph_results, vector_results, top_k=10)

    # Boosted graph result should rank higher
    assert fused[0].chunk_id == "chunk-1"
    assert fused[0].similarity_score == pytest.approx(0.9)


def test_fuse_results_marks_overlaps():
    """Test fusion marks chunks present in both graph and vector results."""
    chunk_both = ChunkContext(
        chunk_id="chunk-1",
        doc_id="doc-123",
        chunk_text="Text",
        anchor_start="page-1",
        anchor_end="page-1",
        similarity_score=0.7,
        source="graph",
    )

    graph_results = [chunk_both]
    vector_results = [chunk_both]

    fused = fuse_results(graph_results, vector_results, top_k=10)

    assert len(fused) == 1
    assert fused[0].source == "both"


def test_fuse_results_respects_top_k():
    """Test fusion respects top_k limit."""
    graph_results = [
        ChunkContext(
            chunk_id=f"chunk-{i}",
            doc_id="doc-123",
            chunk_text="Text",
            anchor_start=f"page-{i}",
            anchor_end=f"page-{i}",
            similarity_score=0.5 + i * 0.1,
            source="graph",
        )
        for i in range(10)
    ]

    fused = fuse_results(graph_results, [], top_k=5)

    assert len(fused) == 5
    # Should be sorted by score descending
    assert fused[0].similarity_score >= fused[1].similarity_score


def test_retrieve_with_graph_uses_graph_candidates(mock_settings):
    """Test retrieve_with_graph uses graph candidates when available."""
    mock_session = MagicMock()
    mock_chunk = Mock()
    mock_chunk.chunk_id = "chunk-1"
    mock_chunk.doc_id = "doc-123"
    mock_chunk.chunk_text = "Test"
    mock_chunk.anchor_start = "page-1"
    mock_chunk.anchor_end = "page-1"

    mock_session.execute.return_value.all.return_value = [(mock_chunk, 0.1)]

    with patch("app.retrieval.extract_query_entities") as mock_extract, \
         patch("app.retrieval.get_graph_connection") as mock_get_conn, \
         patch("app.retrieval.graph_candidate_search") as mock_graph_search, \
         patch("app.retrieval.generate_embedding"):

        mock_extract.return_value = QueryEntities(
            terms=["payment"], parties=[], concepts=[]
        )
        mock_graph_search.return_value = ["doc-123", "doc-456", "doc-789"]  # >= 3 to use graph path

        result = retrieve_with_graph("query", "matter-1", mock_session, mock_settings)

        assert len(result.chunks) > 0
        assert len(result.graph_candidates) > 0
        assert not result.used_fallback


def test_retrieve_with_graph_fallback_on_error(mock_settings):
    """Test retrieve_with_graph falls back to vector-only on graph errors."""
    mock_session = MagicMock()
    mock_chunk = Mock()
    mock_chunk.chunk_id = "chunk-1"
    mock_chunk.doc_id = "doc-123"
    mock_chunk.chunk_text = "Test"
    mock_chunk.anchor_start = "page-1"
    mock_chunk.anchor_end = "page-1"

    mock_session.execute.return_value.all.return_value = [(mock_chunk, 0.1)]

    with patch("app.retrieval.extract_query_entities") as mock_extract, \
         patch("app.retrieval.get_graph_connection") as mock_get_conn, \
         patch("app.retrieval.generate_embedding"):

        mock_extract.side_effect = Exception("Graph error")

        result = retrieve_with_graph("query", "matter-1", mock_session, mock_settings)

        # Should still return results using fallback
        assert len(result.chunks) > 0
        assert result.used_fallback


def test_retrieve_with_graph_fallback_on_few_candidates(mock_settings):
    """Test retrieve_with_graph falls back when no graph candidates found."""
    mock_session = MagicMock()
    mock_chunk = Mock()
    mock_chunk.chunk_id = "chunk-1"
    mock_chunk.doc_id = "doc-123"
    mock_chunk.chunk_text = "Test"
    mock_chunk.anchor_start = "page-1"
    mock_chunk.anchor_end = "page-1"

    mock_session.execute.return_value.all.return_value = [(mock_chunk, 0.1)]

    with patch("app.retrieval.extract_query_entities") as mock_extract, \
         patch("app.retrieval.get_graph_connection") as mock_get_conn, \
         patch("app.retrieval.graph_candidate_search") as mock_graph_search, \
         patch("app.retrieval.generate_embedding"):

        mock_extract.return_value = QueryEntities(
            terms=["payment"], parties=[], concepts=[]
        )
        mock_graph_search.return_value = []  # No candidates → fallback

        result = retrieve_with_graph("query", "matter-1", mock_session, mock_settings)

        assert result.used_fallback
