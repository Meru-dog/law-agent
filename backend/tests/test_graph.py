"""Tests for Neo4j graph integration."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from neo4j.exceptions import ServiceUnavailable

from app.config import Settings
from app.graph import (
    Neo4jConnection,
    create_document_node,
    create_entity_nodes,
    create_matter_node,
    get_graph_connection,
    init_graph_schema,
)


@pytest.fixture
def mock_settings():
    """Mock settings with Neo4j configuration."""
    settings = Settings()
    settings.neo4j_uri = "bolt://localhost:7687"
    settings.neo4j_user = "neo4j"
    settings.neo4j_password = "test-password"
    return settings


@pytest.fixture
def mock_driver():
    """Mock Neo4j driver."""
    driver = MagicMock()
    return driver


@pytest.fixture
def mock_session():
    """Mock Neo4j session."""
    session = MagicMock()
    return session


def test_neo4j_connection_success(mock_driver):
    """Test successful Neo4j connection."""
    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")

        assert connection.driver is not None
        mock_graph_driver.assert_called_once_with(
            "bolt://localhost:7687", auth=("neo4j", "password")
        )


def test_neo4j_connection_failure():
    """Test Neo4j connection failure handling."""
    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.side_effect = ServiceUnavailable("Connection failed")

        with pytest.raises(ServiceUnavailable):
            Neo4jConnection("bolt://localhost:7687", "neo4j", "password")


def test_neo4j_connection_context_manager(mock_driver):
    """Test Neo4j connection as context manager."""
    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver

        with Neo4jConnection("bolt://localhost:7687", "neo4j", "password") as conn:
            assert conn.driver is not None

        mock_driver.close.assert_called_once()


def test_neo4j_connection_session(mock_driver, mock_session):
    """Test Neo4j session context manager."""
    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")

        with connection.session() as session:
            assert session is mock_session

        mock_session.close.assert_called_once()


def test_init_graph_schema(mock_driver, mock_session):
    """Test schema initialization."""
    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        init_graph_schema(connection)

        # Verify multiple queries were executed
        assert mock_session.run.call_count >= 7  # At least 7 schema queries


def test_create_matter_node(mock_driver, mock_session):
    """Test matter node creation."""
    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        create_matter_node(connection, "matter-1", "Test Matter")

        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert "matter_id" in call_args[1]
        assert call_args[1]["matter_id"] == "matter-1"


def test_create_document_node(mock_driver, mock_session):
    """Test document node creation."""
    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session
        mock_result = Mock()
        mock_result.single.return_value = {"d": {"doc_id": "doc-123"}}
        mock_session.run.return_value = mock_result

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        create_document_node(connection, "doc-123", "matter-1", "test.pdf", "pdf")

        mock_session.run.assert_called_once()
        call_args = mock_session.run.call_args
        assert call_args[1]["doc_id"] == "doc-123"
        assert call_args[1]["matter_id"] == "matter-1"
        assert call_args[1]["filename"] == "test.pdf"


def test_create_entity_nodes_terms(mock_driver, mock_session):
    """Test entity node creation for terms."""
    entities = {
        "terms": [
            {"term": "Payment Term", "definition": "30 days from invoice"},
            {"term": "Late Fee", "definition": "1.5% per month"},
        ],
        "parties": [],
        "obligations": [],
    }

    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        create_entity_nodes(connection, entities, "doc-123", "page-5")

        # Should create 2 term nodes
        assert mock_session.run.call_count == 2


def test_create_entity_nodes_parties(mock_driver, mock_session):
    """Test entity node creation for parties."""
    entities = {
        "terms": [],
        "parties": [
            {"name": "Acme Corp", "role": "buyer"},
            {"name": "Widget Inc", "role": "seller"},
        ],
        "obligations": [],
    }

    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        create_entity_nodes(connection, entities, "doc-123", "page-5")

        assert mock_session.run.call_count == 2


def test_create_entity_nodes_all_types(mock_driver, mock_session):
    """Test entity node creation for all entity types."""
    entities = {
        "terms": [{"term": "Term1", "definition": "Def1"}],
        "parties": [{"name": "Party1", "role": "buyer"}],
        "obligations": [{"description": "Must pay", "party": "Party1"}],
    }

    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        create_entity_nodes(connection, entities, "doc-123", "page-5")

        # Should create 3 nodes (1 term + 1 party + 1 obligation)
        assert mock_session.run.call_count == 3


def test_create_entity_nodes_empty(mock_driver, mock_session):
    """Test entity node creation with empty entities."""
    entities = {"terms": [], "parties": [], "obligations": []}

    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        create_entity_nodes(connection, entities, "doc-123", "page-5")

        # Should not create any nodes
        mock_session.run.assert_not_called()


def test_get_graph_connection(mock_settings, mock_driver):
    """Test getting graph connection from settings."""
    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver

        connection = get_graph_connection(mock_settings)

        assert connection is not None
        mock_graph_driver.assert_called_once_with(
            mock_settings.neo4j_uri,
            auth=(mock_settings.neo4j_user, mock_settings.neo4j_password),
        )


def test_entity_nodes_have_provenance(mock_driver, mock_session):
    """Test that entity nodes include provenance fields."""
    entities = {
        "terms": [{"term": "Test", "definition": "Test def"}],
        "parties": [],
        "obligations": [],
    }

    with patch("app.graph.GraphDatabase.driver") as mock_graph_driver:
        mock_graph_driver.return_value = mock_driver
        mock_driver.session.return_value = mock_session

        connection = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        create_entity_nodes(connection, entities, "doc-123", "page-5")

        # Check that the query includes provenance fields
        call_args = mock_session.run.call_args
        assert "source_doc_id" in call_args[0][0]
        assert "source_anchor" in call_args[0][0]
        assert call_args[1]["doc_id"] == "doc-123"
        assert call_args[1]["anchor"] == "page-5"
