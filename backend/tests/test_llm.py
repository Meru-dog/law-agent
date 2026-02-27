"""Tests for LLM integration with citation parsing and validation."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.config import Settings
from app.llm import (
    Citation,
    generate_answer,
    parse_citations,
    validate_citations,
)


@pytest.fixture
def mock_settings():
    """Mock settings with API key configured."""
    settings = Settings()
    settings.gemini_api_key = "test-key"
    settings.gemini_model = "gemini-1.5-pro"
    settings.max_context_chunks = 10
    return settings


@pytest.fixture
def sample_contexts():
    """Sample context chunks for testing."""
    return [
        {
            "chunk_text": "The payment term is 30 days from invoice date.",
            "doc_id": "doc-123",
            "anchor_start": "page-5",
        },
        {
            "chunk_text": "Late fees of 1.5% per month apply to overdue payments.",
            "doc_id": "doc-123",
            "anchor_start": "page-5",
        },
        {
            "chunk_text": "The contract is governed by California law.",
            "doc_id": "doc-456",
            "anchor_start": "page-12",
        },
    ]


def test_parse_citations_single():
    """Test parsing single citation from answer."""
    answer = "The payment term is 30 days [1]."
    contexts = [{"doc_id": "doc-123", "anchor_start": "page-5"}]

    citations = parse_citations(answer, contexts)

    assert len(citations) == 1
    assert citations[0].context_number == 1
    assert citations[0].doc_id == "doc-123"
    assert citations[0].anchor == "page-5"


def test_parse_citations_multiple():
    """Test parsing multiple citations from answer."""
    answer = "Payment is 30 days [1] with late fees [2] under California law [3]."
    contexts = [
        {"doc_id": "doc-123", "anchor_start": "page-5"},
        {"doc_id": "doc-123", "anchor_start": "page-6"},
        {"doc_id": "doc-456", "anchor_start": "page-12"},
    ]

    citations = parse_citations(answer, contexts)

    assert len(citations) == 3
    assert citations[0].context_number == 1
    assert citations[1].context_number == 2
    assert citations[2].context_number == 3


def test_parse_citations_duplicates():
    """Test that duplicate citations are deduplicated."""
    answer = "Payment terms are clear [1] and explicit [1]."
    contexts = [{"doc_id": "doc-123", "anchor_start": "page-5"}]

    citations = parse_citations(answer, contexts)

    assert len(citations) == 1
    assert citations[0].context_number == 1


def test_parse_citations_out_of_range():
    """Test parsing handles citations beyond context count."""
    answer = "Payment is 30 days [1] with unknown terms [5]."
    contexts = [{"doc_id": "doc-123", "anchor_start": "page-5"}]

    citations = parse_citations(answer, contexts)

    # Should only parse citation [1], ignore [5]
    assert len(citations) == 1
    assert citations[0].context_number == 1


def test_parse_citations_no_citations():
    """Test parsing answer with no citations."""
    answer = "This answer has no citations."
    contexts = [{"doc_id": "doc-123", "anchor_start": "page-5"}]

    citations = parse_citations(answer, contexts)

    assert len(citations) == 0


def test_validate_citations_all_valid():
    """Test validation accepts all valid citations."""
    citations = [
        Citation(context_number=1, doc_id="doc-123", anchor="page-5"),
        Citation(context_number=2, doc_id="doc-456", anchor="page-10"),
    ]
    contexts = [
        {"doc_id": "doc-123", "anchor_start": "page-5"},
        {"doc_id": "doc-456", "anchor_start": "page-10"},
    ]

    valid = validate_citations(citations, contexts)

    assert len(valid) == 2


def test_validate_citations_filters_invalid():
    """Test validation filters out-of-range citations."""
    citations = [
        Citation(context_number=1, doc_id="doc-123", anchor="page-5"),
        Citation(context_number=10, doc_id="doc-999", anchor="page-99"),
    ]
    contexts = [{"doc_id": "doc-123", "anchor_start": "page-5"}]

    valid = validate_citations(citations, contexts)

    assert len(valid) == 1
    assert valid[0].context_number == 1


def test_generate_answer_success(mock_settings, sample_contexts):
    """Test successful answer generation with citations."""
    mock_response = Mock()
    mock_response.text = "The payment term is 30 days [1]."

    with patch("app.llm.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = generate_answer("What is the payment term?", sample_contexts, mock_settings)

        assert result.answer == "The payment term is 30 days [1]."
        assert len(result.citations) == 1
        assert result.citations[0].doc_id == "doc-123"
        assert not result.abstained
        assert result.confidence > 0.5


def test_generate_answer_abstain(mock_settings, sample_contexts):
    """Test LLM abstains when evidence insufficient."""
    mock_response = Mock()
    mock_response.text = "INSUFFICIENT EVIDENCE: No information about refund policy in provided context."

    with patch("app.llm.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = generate_answer("What is the refund policy?", sample_contexts, mock_settings)

        assert result.abstained
        assert len(result.citations) == 0
        assert result.confidence == 0.0
        assert "INSUFFICIENT EVIDENCE" in result.answer


def test_generate_answer_no_api_key():
    """Test error when API key not configured."""
    settings = Settings()
    settings.gemini_api_key = ""

    with pytest.raises(ValueError, match="API key not configured"):
        generate_answer("test query", [], settings)


def test_generate_answer_rate_limit(mock_settings, sample_contexts):
    """Test handling of rate limit errors."""
    with patch("app.llm.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("quota exceeded")
        mock_client_class.return_value = mock_client

        with pytest.raises(ValueError, match="quota exceeded"):
            generate_answer("test query", sample_contexts, mock_settings)


def test_generate_answer_timeout(mock_settings, sample_contexts):
    """Test handling of timeout errors."""
    with patch("app.llm.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("timeout exceeded")
        mock_client_class.return_value = mock_client

        with pytest.raises(ValueError, match="timeout"):
            generate_answer("test query", sample_contexts, mock_settings)


def test_generate_answer_api_error(mock_settings, sample_contexts):
    """Test handling of generic API errors."""
    with patch("app.llm.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("Internal server error")
        mock_client_class.return_value = mock_client

        with pytest.raises(Exception):
            generate_answer("test query", sample_contexts, mock_settings)


def test_generate_answer_empty_contexts(mock_settings):
    """Test answer generation with no context."""
    mock_response = Mock()
    mock_response.text = "INSUFFICIENT EVIDENCE: No relevant documents available."

    with patch("app.llm.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = generate_answer("test query", [], mock_settings)

        assert result.abstained
        assert len(result.citations) == 0


def test_generate_answer_invalid_citations_filtered(mock_settings):
    """Test that invalid citation numbers are filtered out."""
    contexts = [{"doc_id": "doc-123", "anchor_start": "page-5"}]
    mock_response = Mock()
    # Citation [5] is invalid since we only have 1 context
    mock_response.text = "Some answer [1] with invalid ref [5]."

    with patch("app.llm.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = generate_answer("test query", contexts, mock_settings)

        # Should only have 1 valid citation
        assert len(result.citations) == 1
        assert result.citations[0].context_number == 1


def test_generate_answer_multiple_citations(mock_settings, sample_contexts):
    """Test answer with multiple valid citations."""
    mock_response = Mock()
    mock_response.text = "Payment is 30 days [1] with late fees [2] under California law [3]."

    with patch("app.llm.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = generate_answer("What are the payment terms?", sample_contexts, mock_settings)

        assert len(result.citations) == 3
        assert all(cit.context_number in [1, 2, 3] for cit in result.citations)
        assert not result.abstained
