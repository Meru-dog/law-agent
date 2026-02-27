"""Tests for entity extraction from legal documents."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.config import Settings
from app.entity_extraction import (
    extract_entities_from_chunks,
    extract_entities_from_text,
    merge_entity_results,
    EntityExtractionResult,
)


@pytest.fixture
def mock_settings():
    """Mock settings with API key configured."""
    settings = Settings()
    settings.gemini_api_key = "test-api-key-1234"
    settings.gemini_model = "gemini-1.5-pro"
    return settings


@pytest.fixture
def sample_legal_text():
    """Sample legal text for testing."""
    return """
    This Payment Agreement ("Agreement") is entered into by Acme Corporation ("Buyer")
    and Widget Industries ("Seller"). The Payment Term shall be 30 days from invoice date.
    Late fees of 1.5% per month shall apply to overdue payments.
    """


def test_extract_entities_success(mock_settings, sample_legal_text):
    """Test successful entity extraction."""
    mock_response = Mock()
    mock_response.text = json.dumps({
        "terms": [
            {"term": "Payment Term", "definition": "30 days from invoice date"},
            {"term": "Late fees", "definition": "1.5% per month"},
        ],
        "parties": [
            {"name": "Acme Corporation", "role": "buyer"},
            {"name": "Widget Industries", "role": "seller"},
        ],
        "obligations": [
            {"description": "Pay within 30 days", "party": "Buyer"},
        ],
    })

    with patch("app.entity_extraction.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = extract_entities_from_text(
            sample_legal_text, "page-1", "doc-123", mock_settings
        )

        assert result.doc_id == "doc-123"
        assert result.anchor == "page-1"
        assert len(result.terms) == 2
        assert len(result.parties) == 2
        assert len(result.obligations) == 1
        assert result.terms[0]["term"] == "Payment Term"
        assert result.parties[0]["name"] == "Acme Corporation"


def test_extract_entities_json_with_markdown(mock_settings, sample_legal_text):
    """Test extraction handles JSON wrapped in markdown code blocks."""
    mock_response = Mock()
    mock_response.text = """```json
{
    "terms": [{"term": "Test", "definition": "Test def"}],
    "parties": [],
    "obligations": []
}
```"""

    with patch("app.entity_extraction.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = extract_entities_from_text(
            sample_legal_text, "page-1", "doc-123", mock_settings
        )

        assert len(result.terms) == 1
        assert result.terms[0]["term"] == "Test"


def test_extract_entities_empty_response(mock_settings, sample_legal_text):
    """Test handling of empty response."""
    mock_response = Mock()
    mock_response.text = ""

    with patch("app.entity_extraction.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = extract_entities_from_text(
            sample_legal_text, "page-1", "doc-123", mock_settings
        )

        assert len(result.terms) == 0
        assert len(result.parties) == 0
        assert len(result.obligations) == 0


def test_extract_entities_invalid_json(mock_settings, sample_legal_text):
    """Test handling of invalid JSON response."""
    mock_response = Mock()
    mock_response.text = "This is not valid JSON"

    with patch("app.entity_extraction.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = extract_entities_from_text(
            sample_legal_text, "page-1", "doc-123", mock_settings
        )

        # Should return empty result on parse error
        assert len(result.terms) == 0
        assert len(result.parties) == 0
        assert len(result.obligations) == 0


def test_extract_entities_no_api_key():
    """Test error when API key not configured."""
    settings = Settings()
    settings.gemini_api_key = ""

    with pytest.raises(ValueError, match="API key not configured"):
        extract_entities_from_text("test text", "page-1", "doc-123", settings)


def test_extract_entities_quota_exceeded(mock_settings, sample_legal_text):
    """Test handling of quota exceeded error."""
    with patch("app.entity_extraction.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("quota exceeded")
        mock_client_class.return_value = mock_client

        with pytest.raises(ValueError, match="quota exceeded"):
            extract_entities_from_text(
                sample_legal_text, "page-1", "doc-123", mock_settings
            )


def test_extract_entities_timeout(mock_settings, sample_legal_text):
    """Test handling of timeout error."""
    with patch("app.entity_extraction.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("timeout exceeded")
        mock_client_class.return_value = mock_client

        with pytest.raises(ValueError, match="timed out"):
            extract_entities_from_text(
                sample_legal_text, "page-1", "doc-123", mock_settings
            )


def test_extract_entities_generic_error(mock_settings, sample_legal_text):
    """Test handling of generic errors with graceful degradation."""
    with patch("app.entity_extraction.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("Internal error")
        mock_client_class.return_value = mock_client

        # Should return empty result instead of raising
        result = extract_entities_from_text(
            sample_legal_text, "page-1", "doc-123", mock_settings
        )

        assert len(result.terms) == 0
        assert len(result.parties) == 0


def test_extract_entities_from_chunks(mock_settings):
    """Test batch extraction from multiple chunks."""
    chunks = [
        ("page-1", "Text with terms"),
        ("page-2", "Text with parties"),
    ]

    mock_response = Mock()
    mock_response.text = json.dumps({
        "terms": [{"term": "Test", "definition": "Test def"}],
        "parties": [],
        "obligations": [],
    })

    with patch("app.entity_extraction.genai.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        results = extract_entities_from_chunks(chunks, "doc-123", mock_settings)

        assert len(results) == 2
        assert results[0].anchor == "page-1"
        assert results[1].anchor == "page-2"


def test_extract_entities_from_chunks_with_errors(mock_settings):
    """Test batch extraction handles individual chunk failures."""
    chunks = [
        ("page-1", "Good text"),
        ("page-2", "Bad text"),
    ]

    with patch("app.entity_extraction.genai.Client") as mock_client_class:
        mock_client = MagicMock()

        # First call succeeds, second fails
        mock_response_success = Mock()
        mock_response_success.text = json.dumps({"terms": [], "parties": [], "obligations": []})

        mock_client.models.generate_content.side_effect = [
            mock_response_success,
            Exception("API error"),
        ]
        mock_client_class.return_value = mock_client

        results = extract_entities_from_chunks(chunks, "doc-123", mock_settings)

        # Should still return 2 results (second one empty)
        assert len(results) == 2
        assert results[1].anchor == "page-2"


def test_merge_entity_results():
    """Test merging entity results from multiple chunks."""
    results = [
        EntityExtractionResult(
            terms=[
                {"term": "Payment Term", "definition": "30 days"},
                {"term": "Late Fee", "definition": "1.5%"},
            ],
            parties=[{"name": "Acme Corp", "role": "buyer"}],
            obligations=[{"description": "Pay on time", "party": "Buyer"}],
            doc_id="doc-123",
            anchor="page-1",
        ),
        EntityExtractionResult(
            terms=[
                {"term": "Payment Term", "definition": "30 days"},  # Duplicate
                {"term": "Warranty", "definition": "1 year"},
            ],
            parties=[{"name": "Widget Inc", "role": "seller"}],
            obligations=[],
            doc_id="doc-123",
            anchor="page-2",
        ),
    ]

    merged = merge_entity_results(results)

    # Should deduplicate "Payment Term"
    assert len(merged["terms"]) == 3  # Payment Term, Late Fee, Warranty
    assert len(merged["parties"]) == 2  # Acme Corp, Widget Inc
    assert len(merged["obligations"]) == 1


def test_merge_entity_results_empty():
    """Test merging with empty results."""
    results = [
        EntityExtractionResult(
            terms=[], parties=[], obligations=[], doc_id="doc-123", anchor="page-1"
        ),
    ]

    merged = merge_entity_results(results)

    assert len(merged["terms"]) == 0
    assert len(merged["parties"]) == 0
    assert len(merged["obligations"]) == 0


def test_merge_entity_results_case_insensitive():
    """Test that merging is case-insensitive."""
    results = [
        EntityExtractionResult(
            terms=[{"term": "Payment Term", "definition": "30 days"}],
            parties=[{"name": "Acme Corp", "role": "buyer"}],
            obligations=[],
            doc_id="doc-123",
            anchor="page-1",
        ),
        EntityExtractionResult(
            terms=[{"term": "payment term", "definition": "Different def"}],  # Same term, different case
            parties=[{"name": "ACME CORP", "role": "buyer"}],  # Same party, different case
            obligations=[],
            doc_id="doc-123",
            anchor="page-2",
        ),
    ]

    merged = merge_entity_results(results)

    # Should deduplicate based on case-insensitive comparison
    assert len(merged["terms"]) == 1
    assert len(merged["parties"]) == 1
