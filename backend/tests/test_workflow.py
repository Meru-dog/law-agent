"""Tests for workflow orchestration."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.config import Settings
from app.llm import AnswerResult, Citation
from app.retrieval import ChunkContext, RetrievalResult
from app.workflow import (
    QueryState,
    retrieval_node,
    run_workflow,
    save_checkpoint,
    synthesis_node,
    validation_node,
)


@pytest.fixture
def mock_settings():
    """Mock settings."""
    settings = Settings()
    settings.gemini_api_key = "test-key"
    settings.gemini_model = "gemini-1.5-pro"
    settings.max_context_chunks = 10
    return settings


@pytest.fixture
def mock_session():
    """Mock database session."""
    session = MagicMock()
    return session


@pytest.fixture
def initial_state():
    """Initial workflow state."""
    return QueryState(
        query_id="query-123",
        user_id="alice",
        matter_id="matter-1",
        query="What is the payment term?",
    )


@pytest.fixture
def sample_chunks():
    """Sample chunk contexts."""
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


def test_save_checkpoint(initial_state, mock_session):
    """Test checkpoint saving."""
    save_checkpoint(initial_state, "test_node", mock_session)

    # Verify checkpoint was added to session
    assert mock_session.add.called
    assert mock_session.commit.called


def test_save_checkpoint_with_data(initial_state, mock_session, sample_chunks):
    """Test checkpoint saves complete state."""
    initial_state.retrieved_chunks = sample_chunks
    initial_state.citations = [
        Citation(context_number=1, doc_id="doc-123", anchor="page-1")
    ]

    save_checkpoint(initial_state, "test_node", mock_session)

    assert mock_session.add.called


def test_save_checkpoint_error_handling(initial_state):
    """Test checkpoint save handles errors gracefully."""
    mock_session = MagicMock()
    mock_session.add.side_effect = Exception("Database error")

    # Should not raise exception
    save_checkpoint(initial_state, "test_node", mock_session)


def test_retrieval_node_success(initial_state, mock_session, mock_settings, sample_chunks):
    """Test successful retrieval node execution."""
    with patch("app.workflow.retrieve_with_graph") as mock_retrieve, \
         patch("app.workflow.record_audit"):

        mock_retrieve.return_value = RetrievalResult(
            chunks=sample_chunks,
            graph_candidates=["doc-123"],
            used_fallback=False,
        )

        state = retrieval_node(initial_state, mock_session, mock_settings)

        assert state.retrieved_chunks is not None
        assert len(state.retrieved_chunks) == 2
        assert state.graph_candidates == ["doc-123"]
        assert not state.used_fallback
        assert len(state.errors) == 0


def test_retrieval_node_fallback(initial_state, mock_session, mock_settings, sample_chunks):
    """Test retrieval node with fallback."""
    with patch("app.workflow.retrieve_with_graph") as mock_retrieve, \
         patch("app.workflow.record_audit"):

        mock_retrieve.return_value = RetrievalResult(
            chunks=sample_chunks,
            graph_candidates=[],
            used_fallback=True,
        )

        state = retrieval_node(initial_state, mock_session, mock_settings)

        assert state.used_fallback
        assert len(state.errors) == 0


def test_retrieval_node_error(initial_state, mock_session, mock_settings):
    """Test retrieval node handles errors."""
    with patch("app.workflow.retrieve_with_graph") as mock_retrieve:
        mock_retrieve.side_effect = Exception("Retrieval failed")

        state = retrieval_node(initial_state, mock_session, mock_settings)

        assert len(state.errors) > 0
        assert "Retrieval failed" in state.errors[0]
        assert state.retrieved_chunks == []


def test_synthesis_node_success(initial_state, mock_session, mock_settings, sample_chunks):
    """Test successful synthesis node execution."""
    initial_state.retrieved_chunks = sample_chunks

    with patch("app.workflow.generate_answer") as mock_generate, \
         patch("app.workflow.record_audit"):

        mock_generate.return_value = AnswerResult(
            answer="The payment term is 30 days [1].",
            citations=[Citation(context_number=1, doc_id="doc-123", anchor="page-1")],
            abstained=False,
            confidence=0.85,
            raw_response="The payment term is 30 days [1].",
        )

        state = synthesis_node(initial_state, mock_session, mock_settings)

        assert state.answer == "The payment term is 30 days [1]."
        assert len(state.citations) == 1
        assert not state.abstained
        assert state.confidence == 0.85
        assert len(state.errors) == 0


def test_synthesis_node_abstain(initial_state, mock_session, mock_settings, sample_chunks):
    """Test synthesis node with abstain response."""
    initial_state.retrieved_chunks = sample_chunks

    with patch("app.workflow.generate_answer") as mock_generate, \
         patch("app.workflow.record_audit"):

        mock_generate.return_value = AnswerResult(
            answer="INSUFFICIENT EVIDENCE: No information found.",
            citations=[],
            abstained=True,
            confidence=0.0,
            raw_response="INSUFFICIENT EVIDENCE: No information found.",
        )

        state = synthesis_node(initial_state, mock_session, mock_settings)

        assert state.abstained
        assert len(state.citations) == 0
        assert state.confidence == 0.0


def test_synthesis_node_error(initial_state, mock_session, mock_settings):
    """Test synthesis node handles errors."""
    initial_state.retrieved_chunks = []

    with patch("app.workflow.generate_answer") as mock_generate:
        mock_generate.side_effect = Exception("LLM failed")

        state = synthesis_node(initial_state, mock_session, mock_settings)

        assert len(state.errors) > 0
        assert "Answer synthesis failed" in state.errors[0]
        assert state.abstained
        assert state.confidence == 0.0


def test_validation_node_success(initial_state, mock_session, mock_settings):
    """Test validation node with valid answer."""
    initial_state.answer = "The payment term is 30 days [1]."
    initial_state.citations = [
        Citation(context_number=1, doc_id="doc-123", anchor="page-1")
    ]
    initial_state.retrieved_chunks = [
        ChunkContext(
            chunk_id="chunk-1",
            doc_id="doc-123",
            chunk_text="Text",
            anchor_start="page-1",
            anchor_end="page-1",
            similarity_score=0.9,
            source="graph",
        )
    ]
    initial_state.abstained = False
    initial_state.confidence = 0.8

    state = validation_node(initial_state, mock_session, mock_settings)

    assert len(state.warnings) == 0
    assert state.confidence == 0.8


def test_validation_node_no_citations(initial_state, mock_session, mock_settings):
    """Test validation warns on missing citations."""
    initial_state.answer = "The payment term is 30 days."
    initial_state.citations = []
    initial_state.abstained = False
    initial_state.confidence = 0.8

    state = validation_node(initial_state, mock_session, mock_settings)

    assert len(state.warnings) > 0
    assert "no citations" in state.warnings[0].lower()
    assert state.confidence < 0.8  # Should be reduced


def test_validation_node_invalid_citation_number(initial_state, mock_session, mock_settings):
    """Test validation detects invalid citation numbers."""
    initial_state.answer = "Answer [5]"
    initial_state.citations = [
        Citation(context_number=5, doc_id="doc-123", anchor="page-1")
    ]
    initial_state.retrieved_chunks = [
        ChunkContext(
            chunk_id="chunk-1",
            doc_id="doc-123",
            chunk_text="Text",
            anchor_start="page-1",
            anchor_end="page-1",
            similarity_score=0.9,
            source="graph",
        )
    ]  # Only 1 chunk, but citation references [5]

    state = validation_node(initial_state, mock_session, mock_settings)

    assert len(state.warnings) > 0
    assert "Invalid citation" in state.warnings[0]


def test_validation_node_empty_answer(initial_state, mock_session, mock_settings):
    """Test validation detects empty answer."""
    initial_state.answer = ""
    initial_state.confidence = 0.5

    state = validation_node(initial_state, mock_session, mock_settings)

    assert len(state.warnings) > 0
    assert state.confidence == 0.0


def test_run_workflow_complete(initial_state, mock_session, mock_settings):
    """Test complete workflow execution."""
    with patch("app.workflow.retrieve_with_graph") as mock_retrieve, \
         patch("app.workflow.generate_answer") as mock_generate, \
         patch("app.workflow.record_audit"), \
         patch("app.workflow.save_checkpoint"):

        # Mock retrieval
        mock_retrieve.return_value = RetrievalResult(
            chunks=[
                ChunkContext(
                    chunk_id="chunk-1",
                    doc_id="doc-123",
                    chunk_text="Payment is 30 days",
                    anchor_start="page-1",
                    anchor_end="page-1",
                    similarity_score=0.9,
                    source="graph",
                )
            ],
            graph_candidates=["doc-123"],
            used_fallback=False,
        )

        # Mock answer generation
        mock_generate.return_value = AnswerResult(
            answer="Payment is 30 days [1].",
            citations=[Citation(context_number=1, doc_id="doc-123", anchor="page-1")],
            abstained=False,
            confidence=0.85,
            raw_response="Payment is 30 days [1].",
        )

        final_state = run_workflow(initial_state, mock_session, mock_settings)

        assert final_state.answer is not None
        assert final_state.retrieved_chunks is not None
        assert len(final_state.citations) > 0
        assert not final_state.abstained
        assert final_state.confidence > 0.5


def test_run_workflow_retrieval_failure(initial_state, mock_session, mock_settings):
    """Test workflow handles retrieval failure."""
    with patch("app.workflow.retrieve_with_graph") as mock_retrieve, \
         patch("app.workflow.save_checkpoint"):

        mock_retrieve.side_effect = Exception("Retrieval failed")

        final_state = run_workflow(initial_state, mock_session, mock_settings)

        assert final_state.abstained
        assert len(final_state.errors) > 0
        assert "Unable to retrieve" in final_state.answer


def test_run_workflow_synthesis_failure(initial_state, mock_session, mock_settings):
    """Test workflow handles synthesis failure."""
    with patch("app.workflow.retrieve_with_graph") as mock_retrieve, \
         patch("app.workflow.generate_answer") as mock_generate, \
         patch("app.workflow.record_audit"), \
         patch("app.workflow.save_checkpoint"):

        # Retrieval succeeds
        mock_retrieve.return_value = RetrievalResult(
            chunks=[
                ChunkContext(
                    chunk_id="chunk-1",
                    doc_id="doc-123",
                    chunk_text="Text",
                    anchor_start="page-1",
                    anchor_end="page-1",
                    similarity_score=0.9,
                    source="graph",
                )
            ],
            graph_candidates=["doc-123"],
            used_fallback=False,
        )

        # Synthesis fails
        mock_generate.side_effect = Exception("LLM failed")

        final_state = run_workflow(initial_state, mock_session, mock_settings)

        assert len(final_state.errors) > 0
        assert final_state.abstained
