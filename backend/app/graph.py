"""Neo4j graph database integration for legal entity knowledge graph.

Manages connections, schema initialization, and entity node/edge creation
with mandatory provenance tracking (source_doc_id + source_anchor).
"""

from contextlib import contextmanager
from typing import Generator

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, ClientError

from app.config import Settings
from app.logging import get_logger


class Neo4jConnection:
    """Neo4j connection manager with context manager support."""

    def __init__(self, uri: str, user: str, password: str):
        """Initialize Neo4j connection.

        Args:
            uri: Neo4j bolt URI (e.g., bolt://localhost:7687).
            user: Database username.
            password: Database password.
        """
        self.logger = get_logger(__name__)
        try:
            self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))
            self.logger.info("neo4j_connection_established", uri=uri)
        except ServiceUnavailable as e:
            self.logger.error("neo4j_connection_failed", uri=uri, error=str(e))
            raise

    def close(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            self.logger.info("neo4j_connection_closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Provide a Neo4j session context.

        Yields:
            Neo4j session for executing queries.
        """
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()


def init_graph_schema(connection: Neo4jConnection):
    """Initialize Neo4j schema with constraints and indexes.

    Creates constraints for unique IDs and indexes for efficient lookups.

    Args:
        connection: Active Neo4j connection.
    """
    logger = get_logger(__name__)

    constraints_and_indexes = [
        # Unique constraints
        "CREATE CONSTRAINT matter_id_unique IF NOT EXISTS FOR (m:Matter) REQUIRE m.matter_id IS UNIQUE",
        "CREATE CONSTRAINT doc_id_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
        "CREATE CONSTRAINT section_id_unique IF NOT EXISTS FOR (s:Section) REQUIRE s.section_id IS UNIQUE",
        # Indexes for lookups
        "CREATE INDEX section_doc_idx IF NOT EXISTS FOR (s:Section) ON (s.doc_id)",
        "CREATE INDEX term_text_idx IF NOT EXISTS FOR (t:DefinedTerm) ON (t.term)",
        "CREATE INDEX party_name_idx IF NOT EXISTS FOR (p:Party) ON (p.name)",
        "CREATE INDEX doc_matter_idx IF NOT EXISTS FOR (d:Document) ON (d.matter_id)",
    ]

    with connection.session() as session:
        for query in constraints_and_indexes:
            try:
                session.run(query)
                logger.info("schema_query_executed", query=query[:50])
            except ClientError as e:
                if "EquivalentSchemaRuleAlreadyExists" in str(e):
                    logger.debug("schema_already_exists", query=query[:50])
                else:
                    logger.error("schema_creation_failed", query=query[:50], error=str(e))
                    raise

    logger.info("neo4j_schema_initialized")


def create_matter_node(connection: Neo4jConnection, matter_id: str, name: str):
    """Create a Matter node if it doesn't exist.

    Args:
        connection: Active Neo4j connection.
        matter_id: Unique matter identifier.
        name: Matter display name.
    """
    query = """
    MERGE (m:Matter {matter_id: $matter_id})
    ON CREATE SET m.name = $name, m.created_at = datetime()
    RETURN m
    """
    with connection.session() as session:
        session.run(query, matter_id=matter_id, name=name)


def create_document_node(
    connection: Neo4jConnection,
    doc_id: str,
    matter_id: str,
    filename: str,
    doc_type: str,
):
    """Create a Document node and link it to its Matter.

    Args:
        connection: Active Neo4j connection.
        doc_id: Unique document identifier.
        matter_id: Parent matter identifier.
        filename: Original filename.
        doc_type: Document type (pdf, docx).
    """
    query = """
    MATCH (m:Matter {matter_id: $matter_id})
    MERGE (d:Document {doc_id: $doc_id})
    ON CREATE SET
        d.filename = $filename,
        d.doc_type = $doc_type,
        d.matter_id = $matter_id,
        d.created_at = datetime()
    MERGE (m)-[:HAS_DOCUMENT]->(d)
    RETURN d
    """
    logger = get_logger(__name__)

    with connection.session() as session:
        result = session.run(
            query,
            doc_id=doc_id,
            matter_id=matter_id,
            filename=filename,
            doc_type=doc_type,
        )
        if result.single():
            logger.info("document_node_created", doc_id=doc_id, matter_id=matter_id)


def create_section_node(
    connection: Neo4jConnection,
    section_id: str,
    doc_id: str,
    title: str,
    anchor_start: str,
    anchor_end: str,
    text: str,
):
    """Create a Section node and link it to its Document.

    Args:
        connection: Active Neo4j connection.
        section_id: Unique section identifier.
        doc_id: Parent document identifier.
        title: Section title or heading.
        anchor_start: Starting anchor (page, paragraph).
        anchor_end: Ending anchor.
        text: Section text content (truncated for storage).
    """
    # Truncate text to avoid storing massive content in graph
    max_text_length = 500
    truncated_text = text[:max_text_length] if len(text) > max_text_length else text

    query = """
    MATCH (d:Document {doc_id: $doc_id})
    MERGE (s:Section {section_id: $section_id})
    ON CREATE SET
        s.doc_id = $doc_id,
        s.title = $title,
        s.anchor_start = $anchor_start,
        s.anchor_end = $anchor_end,
        s.text = $text,
        s.source_doc_id = $doc_id,
        s.source_anchor = $anchor_start,
        s.created_at = datetime()
    MERGE (d)-[:CONTAINS]->(s)
    RETURN s
    """

    with connection.session() as session:
        session.run(
            query,
            section_id=section_id,
            doc_id=doc_id,
            title=title,
            anchor_start=anchor_start,
            anchor_end=anchor_end,
            text=truncated_text,
        )


def create_entity_nodes(
    connection: Neo4jConnection,
    entities: dict,
    doc_id: str,
    anchor: str,
):
    """Create entity nodes (terms, parties, obligations) with provenance.

    Args:
        connection: Active Neo4j connection.
        entities: Dict with keys: terms (list), parties (list), obligations (list).
        doc_id: Source document identifier.
        anchor: Source anchor (page/paragraph).
    """
    logger = get_logger(__name__)

    with connection.session() as session:
        # Create DefinedTerm nodes
        for term_data in entities.get("terms", []):
            term = term_data.get("term", "")
            definition = term_data.get("definition", "")

            query = """
            MATCH (d:Document {doc_id: $doc_id})
            MERGE (t:DefinedTerm {term: $term, doc_id: $doc_id})
            ON CREATE SET
                t.definition = $definition,
                t.source_doc_id = $doc_id,
                t.source_anchor = $anchor,
                t.created_at = datetime()
            MERGE (d)-[:DEFINES]->(t)
            RETURN t
            """
            session.run(
                query,
                term=term,
                definition=definition,
                doc_id=doc_id,
                anchor=anchor,
            )

        # Create Party nodes
        for party_data in entities.get("parties", []):
            name = party_data.get("name", "")
            role = party_data.get("role", "")

            query = """
            MATCH (d:Document {doc_id: $doc_id})
            MERGE (p:Party {name: $name, doc_id: $doc_id})
            ON CREATE SET
                p.role = $role,
                p.source_doc_id = $doc_id,
                p.source_anchor = $anchor,
                p.created_at = datetime()
            MERGE (d)-[:MENTIONS_PARTY]->(p)
            RETURN p
            """
            session.run(
                query,
                name=name,
                role=role,
                doc_id=doc_id,
                anchor=anchor,
            )

        # Create Obligation nodes (optional for MVP)
        for obligation_data in entities.get("obligations", []):
            description = obligation_data.get("description", "")
            party = obligation_data.get("party", "")

            query = """
            MATCH (d:Document {doc_id: $doc_id})
            MERGE (o:Obligation {description: $description, doc_id: $doc_id})
            ON CREATE SET
                o.party = $party,
                o.source_doc_id = $doc_id,
                o.source_anchor = $anchor,
                o.created_at = datetime()
            MERGE (d)-[:IMPOSES]->(o)
            RETURN o
            """
            session.run(
                query,
                description=description,
                party=party,
                doc_id=doc_id,
                anchor=anchor,
            )

    logger.info(
        "entities_created",
        doc_id=doc_id,
        terms_count=len(entities.get("terms", [])),
        parties_count=len(entities.get("parties", [])),
        obligations_count=len(entities.get("obligations", [])),
    )


def get_graph_connection(settings: Settings) -> Neo4jConnection:
    """Create a Neo4j connection from settings.

    Args:
        settings: Application settings with Neo4j configuration.

    Returns:
        Neo4jConnection instance.
    """
    return Neo4jConnection(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
    )
