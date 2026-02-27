"""FastAPI application entry point.

MVP deliverable: FastAPI skeleton + health endpoint.
"""

import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Generator

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sqlalchemy import select

from app.audit import record_audit
from app.auth import check_matter_access, get_current_user
from app.chunking import chunk_document
from app.config import Settings, get_settings
from app.database import build_engine, build_session_factory, init_pgvector
from app.embeddings import generate_embedding
from app.embeddings import generate_embeddings_batch
from app.entity_extraction import extract_entities_from_chunks, merge_entity_results
from app.extraction import extract_text
from app.graph import (
    create_document_node,
    create_entity_nodes,
    create_matter_node,
    get_graph_connection,
    init_graph_schema,
)
from app.llm import generate_answer
from app.logging import configure_logging, get_logger
from app.models import Base, Chunk, Document, ExtractedText
from app.retrieval import retrieve_with_graph
from app.workflow import QueryState, run_workflow


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str


class QueryRequest(BaseModel):
    """Body for the /v1/query endpoint."""

    matter_id: str
    query: str


class CitationInfo(BaseModel):
    """Citation reference in the answer."""

    context_number: int
    doc_id: str
    anchor: str


class ChunkResult(BaseModel):
    """A search result chunk with similarity score."""

    chunk_id: str
    doc_id: str
    chunk_text: str
    anchor_start: str
    anchor_end: str
    similarity_score: float


class QueryResponse(BaseModel):
    """Response for /v1/query with cited answer."""

    matter_id: str
    query: str
    answer: str
    query_id: str
    citations: list[CitationInfo]
    abstained: bool
    confidence: float
    retrieval_trace: list[ChunkResult]


class AnchorInfo(BaseModel):
    """Information about a text anchor in a document."""

    anchor_type: str
    anchor_value: str
    text_preview: str


class DocumentUploadResponse(BaseModel):
    """Response for document upload endpoint."""

    doc_id: str
    matter_id: str
    filename: str
    doc_type: str
    anchors: list[AnchorInfo]


class SearchRequest(BaseModel):
    """Request for vector search endpoint."""

    matter_id: str
    query: str
    top_k: int = 5


class SearchResponse(BaseModel):
    """Response for vector search endpoint."""

    matter_id: str
    query: str
    results: list[ChunkResult]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    settings = get_settings()
    configure_logging(settings)

    logger = get_logger(__name__)
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        environment=settings.environment,
        debug=settings.debug,
    )

    engine = build_engine(settings)
    init_pgvector(engine)
    Base.metadata.create_all(bind=engine)
    app.state.session_factory = build_session_factory(engine)

    storage_dir = Path(settings.storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    logger.info("storage_directory_ready", path=str(storage_dir))

    # Initialize Neo4j connection and schema
    try:
        graph_connection = get_graph_connection(settings)
        init_graph_schema(graph_connection)
        app.state.graph_connection = graph_connection
        logger.info("neo4j_initialized")
    except Exception as e:
        logger.warning("neo4j_initialization_failed", error=str(e))
        app.state.graph_connection = None

    yield

    engine.dispose()
    if hasattr(app.state, "graph_connection") and app.state.graph_connection:
        app.state.graph_connection.close()
    logger.info("application_shutdown")


app = FastAPI(
    title="Law RAG API",
    description="Internal law-firm Q&A application with citations",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    session: Session = app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse with status "ok" if the service is running.
    """
    return HealthResponse(status="ok")


@app.post("/v1/query", response_model=QueryResponse, tags=["Query"])
async def query_matter(
    body: QueryRequest,
    user_id: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_db_session),
) -> QueryResponse:
    """Submit a query scoped to a specific matter.

    Requires X-User-Id header and a matter_id the user is authorized for.
    Returns 401 if unauthenticated, 403 if not authorized for the matter.
    """
    logger = get_logger(__name__)
    query_id = str(uuid.uuid4())

    if not check_matter_access(user_id, body.matter_id, settings):
        record_audit(
            session,
            query_id=query_id,
            user_id=user_id,
            matter_id=body.matter_id,
            step_name="access_denied",
        )
        logger.warning(
            "access_denied",
            query_id=query_id,
            user_id=user_id,
            matter_id=body.matter_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: not authorized for this matter",
        )

    record_audit(
        session,
        query_id=query_id,
        user_id=user_id,
        matter_id=body.matter_id,
        step_name="query_received",
    )
    logger.info(
        "query_received",
        query_id=query_id,
        user_id=user_id,
        matter_id=body.matter_id,
    )

    # Execute workflow: retrieval → synthesis → validation
    initial_state = QueryState(
        query_id=query_id,
        user_id=user_id,
        matter_id=body.matter_id,
        query=body.query,
    )

    final_state = run_workflow(initial_state, session, settings)

    # Build retrieval trace from workflow state
    retrieval_trace = []
    if final_state.retrieved_chunks:
        for chunk_ctx in final_state.retrieved_chunks:
            retrieval_trace.append(
                ChunkResult(
                    chunk_id=chunk_ctx.chunk_id,
                    doc_id=chunk_ctx.doc_id,
                    chunk_text=chunk_ctx.chunk_text,
                    anchor_start=chunk_ctx.anchor_start,
                    anchor_end=chunk_ctx.anchor_end,
                    similarity_score=chunk_ctx.similarity_score,
                )
            )

    # Convert citations to response format
    citation_infos = []
    if final_state.citations:
        citation_infos = [
            CitationInfo(
                context_number=cit.context_number,
                doc_id=cit.doc_id,
                anchor=cit.anchor,
            )
            for cit in final_state.citations
        ]

    # Check for workflow errors
    if final_state.errors:
        logger.warning(
            "workflow_completed_with_errors",
            query_id=query_id,
            errors=final_state.errors,
        )

    return QueryResponse(
        matter_id=body.matter_id,
        query=body.query,
        answer=final_state.answer or "Unable to generate answer.",
        query_id=query_id,
        citations=citation_infos,
        abstained=final_state.abstained,
        confidence=final_state.confidence,
        retrieval_trace=retrieval_trace,
    )


@app.post("/v1/documents/upload", response_model=DocumentUploadResponse, tags=["Documents"])
async def upload_document(
    matter_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_db_session),
) -> DocumentUploadResponse:
    """Upload and extract a document for a specific matter.

    Validates file type, enforces matter ACL, stores the file,
    extracts text with anchors, and persists metadata.

    Args:
        matter_id: Matter ID to associate with the document.
        file: Uploaded file (PDF or DOCX).
        user_id: Authenticated user ID.
        settings: Application settings.
        session: Database session.

    Returns:
        DocumentUploadResponse with doc_id and anchor information.

    Raises:
        HTTPException: 403 if user not authorized for matter, 400 if file type invalid.
    """
    logger = get_logger(__name__)

    if not check_matter_access(user_id, matter_id, settings):
        logger.warning(
            "upload_access_denied",
            user_id=user_id,
            matter_id=matter_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: not authorized for this matter",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    file_suffix = Path(file.filename).suffix.lower()
    if file_suffix not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file_suffix}. Supported: .pdf, .docx",
        )

    doc_id = str(uuid.uuid4())
    storage_dir = Path(settings.storage_path) / matter_id
    storage_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{doc_id}{file_suffix}"
    file_path = storage_dir / safe_filename

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error("file_write_failed", doc_id=doc_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file",
        ) from e

    try:
        extraction_result = extract_text(file_path)
    except Exception as e:
        logger.error("extraction_failed", doc_id=doc_id, error=str(e))
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract text: {str(e)}",
        ) from e

    document = Document(
        doc_id=doc_id,
        matter_id=matter_id,
        filename=file.filename,
        doc_type=extraction_result.doc_type,
        file_path=str(file_path),
        uploaded_by=user_id,
    )
    session.add(document)

    anchor_infos = []
    for anchor in extraction_result.anchors:
        extracted_text = ExtractedText(
            doc_id=doc_id,
            anchor_type=anchor.anchor_type,
            anchor_value=anchor.anchor_value,
            text_content=anchor.text_content,
        )
        session.add(extracted_text)

        preview = anchor.text_content[:100]
        if len(anchor.text_content) > 100:
            preview += "..."

        anchor_infos.append(
            AnchorInfo(
                anchor_type=anchor.anchor_type,
                anchor_value=anchor.anchor_value,
                text_preview=preview,
            )
        )

    session.commit()

    extracted_text_tuples = [
        (anchor.anchor_value, anchor.text_content) for anchor in extraction_result.anchors
    ]
    chunking_result = chunk_document(
        extracted_text_tuples,
        strategy="tokens",
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )

    chunk_texts = [chunk.chunk_text for chunk in chunking_result.chunks]
    embeddings = generate_embeddings_batch(chunk_texts, model_name=settings.embedding_model)

    for chunk_data, embedding in zip(chunking_result.chunks, embeddings):
        chunk = Chunk(
            chunk_id=f"{doc_id}-chunk-{chunk_data.chunk_index}",
            doc_id=doc_id,
            matter_id=matter_id,
            chunk_index=chunk_data.chunk_index,
            chunk_text=chunk_data.chunk_text,
            anchor_start=chunk_data.anchor_start,
            anchor_end=chunk_data.anchor_end,
            embedding=embedding,
        )
        session.add(chunk)

    session.commit()

    # Populate knowledge graph with entities (if Neo4j available)
    if hasattr(app.state, "graph_connection") and app.state.graph_connection:
        try:
            # Ensure matter node exists
            create_matter_node(app.state.graph_connection, matter_id, f"Matter {matter_id}")

            # Create document node
            create_document_node(
                app.state.graph_connection,
                doc_id,
                matter_id,
                file.filename,
                extraction_result.doc_type,
            )

            # Extract entities from chunks (sample first 5 chunks to limit API calls)
            chunks_for_extraction = extracted_text_tuples[:5]
            entity_results = extract_entities_from_chunks(
                chunks_for_extraction, doc_id, settings
            )

            # Merge and create entity nodes
            if entity_results:
                merged_entities = merge_entity_results(entity_results)
                # Use first chunk's anchor as representative anchor
                first_anchor = extracted_text_tuples[0][0] if extracted_text_tuples else "unknown"
                create_entity_nodes(
                    app.state.graph_connection,
                    merged_entities,
                    doc_id,
                    first_anchor,
                )

                logger.info(
                    "graph_population_complete",
                    doc_id=doc_id,
                    terms_count=len(merged_entities.get("terms", [])),
                    parties_count=len(merged_entities.get("parties", [])),
                )
        except Exception as e:
            logger.error("graph_population_failed", doc_id=doc_id, error=str(e))
            # Continue despite graph population failure (graceful degradation)
    else:
        logger.warning("graph_population_skipped", doc_id=doc_id, reason="neo4j_unavailable")

    logger.info(
        "document_uploaded",
        doc_id=doc_id,
        matter_id=matter_id,
        user_id=user_id,
        filename=file.filename,
        anchor_count=len(anchor_infos),
        chunk_count=len(chunking_result.chunks),
    )

    return DocumentUploadResponse(
        doc_id=doc_id,
        matter_id=matter_id,
        filename=file.filename,
        doc_type=extraction_result.doc_type,
        anchors=anchor_infos,
    )


@app.post("/v1/search", response_model=SearchResponse, tags=["Search"])
async def search_chunks(
    body: SearchRequest,
    user_id: str = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_db_session),
) -> SearchResponse:
    """Perform matter-scoped vector similarity search.

    Generates an embedding for the query and finds the most similar chunks
    within the authorized matter scope.

    Args:
        body: Search request with matter_id, query, and top_k.
        user_id: Authenticated user ID.
        settings: Application settings.
        session: Database session.

    Returns:
        SearchResponse with top_k most similar chunks.

    Raises:
        HTTPException: 403 if user not authorized for matter.
    """
    logger = get_logger(__name__)

    if not check_matter_access(user_id, body.matter_id, settings):
        logger.warning(
            "search_access_denied",
            user_id=user_id,
            matter_id=body.matter_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: not authorized for this matter",
        )

    query_embedding = generate_embedding(body.query, model_name=settings.embedding_model)

    chunks_with_distance = session.execute(
        select(
            Chunk,
            Chunk.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .where(Chunk.matter_id == body.matter_id)
        .where(Chunk.embedding.isnot(None))
        .order_by(Chunk.embedding.cosine_distance(query_embedding))
        .limit(body.top_k)
    ).all()

    results = []
    for chunk, distance in chunks_with_distance:
        similarity = 1.0 - float(distance)
        results.append(
            ChunkResult(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                chunk_text=chunk.chunk_text,
                anchor_start=chunk.anchor_start,
                anchor_end=chunk.anchor_end,
                similarity_score=similarity,
            )
        )

    logger.info(
        "search_completed",
        user_id=user_id,
        matter_id=body.matter_id,
        result_count=len(results),
    )

    return SearchResponse(matter_id=body.matter_id, query=body.query, results=results)
