"""Workflow orchestration for query processing pipeline.

Orchestrates: query parsing → graph retrieval → vector retrieval → answer synthesis.
Implements checkpointing, fallbacks, and audit logging per node.
"""

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.audit import record_audit
from app.config import Settings
from app.llm import generate_answer, Citation
from app.logging import get_logger
from app.models import WorkflowCheckpoint
from app.retrieval import retrieve_with_graph, ChunkContext


@dataclass
class QueryState:
    """State container for workflow execution."""

    # Input
    query_id: str
    user_id: str
    matter_id: str
    query: str

    # Intermediate artifacts
    retrieved_chunks: Optional[list[ChunkContext]] = None
    graph_candidates: Optional[list[str]] = None
    used_fallback: bool = False

    # Output
    answer: Optional[str] = None
    citations: Optional[list[Citation]] = None
    abstained: bool = False
    confidence: float = 0.0

    # Metadata
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checkpoints: dict[str, Any] = field(default_factory=dict)


def save_checkpoint(
    state: QueryState, node_name: str, session: Session
):
    """Save workflow checkpoint to database.

    Args:
        state: Current workflow state.
        node_name: Name of the node being checkpointed.
        session: Database session.
    """
    logger = get_logger(__name__)

    try:
        # Convert state to JSON-serializable dict
        state_dict = {
            "query_id": state.query_id,
            "user_id": state.user_id,
            "matter_id": state.matter_id,
            "query": state.query,
            "retrieved_chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "doc_id": c.doc_id,
                    "chunk_text": c.chunk_text[:200],  # Truncate for storage
                    "anchor_start": c.anchor_start,
                    "similarity_score": c.similarity_score,
                }
                for c in (state.retrieved_chunks or [])
            ],
            "graph_candidates": state.graph_candidates,
            "used_fallback": state.used_fallback,
            "answer": state.answer,
            "citations": [
                {"context_number": c.context_number, "doc_id": c.doc_id, "anchor": c.anchor}
                for c in (state.citations or [])
            ],
            "abstained": state.abstained,
            "confidence": state.confidence,
            "errors": state.errors,
            "warnings": state.warnings,
        }

        checkpoint = WorkflowCheckpoint(
            query_id=state.query_id,
            node_name=node_name,
            state_snapshot=json.dumps(state_dict),
        )
        session.add(checkpoint)
        session.commit()

        logger.debug("checkpoint_saved", query_id=state.query_id, node_name=node_name)

    except Exception as e:
        logger.error(
            "checkpoint_save_failed",
            query_id=state.query_id,
            node_name=node_name,
            error=str(e),
        )
        # Don't fail workflow on checkpoint error


def retrieval_node(state: QueryState, session: Session, settings: Settings) -> QueryState:
    """Execute GraphRAG retrieval: graph candidates + vector search.

    Args:
        state: Workflow state.
        session: Database session.
        settings: Application settings.

    Returns:
        Updated state with retrieved chunks.
    """
    logger = get_logger(__name__)

    try:
        logger.info("workflow_node_start", node="retrieval", query_id=state.query_id)

        retrieval_result = retrieve_with_graph(
            state.query,
            state.matter_id,
            session,
            settings,
            top_k=settings.max_context_chunks,
        )

        state.retrieved_chunks = retrieval_result.chunks
        state.graph_candidates = retrieval_result.graph_candidates
        state.used_fallback = retrieval_result.used_fallback

        # Audit logging
        audit_step = "graph_retrieval" if retrieval_result.graph_candidates else "vector_retrieval"
        chunk_ids = ",".join([c.chunk_id for c in retrieval_result.chunks])
        record_audit(
            session,
            query_id=state.query_id,
            user_id=state.user_id,
            matter_id=state.matter_id,
            step_name=audit_step,
            artifact_ids=chunk_ids,
        )

        logger.info(
            "workflow_node_complete",
            node="retrieval",
            query_id=state.query_id,
            chunk_count=len(retrieval_result.chunks),
        )

    except Exception as e:
        logger.error("workflow_node_failed", node="retrieval", error=str(e))
        state.errors.append(f"Retrieval failed: {str(e)}")
        # Empty chunks on error
        state.retrieved_chunks = []

    return state


def synthesis_node(state: QueryState, session: Session, settings: Settings) -> QueryState:
    """Generate cited answer using LLM.

    Args:
        state: Workflow state with retrieved chunks.
        session: Database session.
        settings: Application settings.

    Returns:
        Updated state with answer and citations.
    """
    logger = get_logger(__name__)

    try:
        logger.info("workflow_node_start", node="synthesis", query_id=state.query_id)

        # Convert chunks to context format
        contexts = [
            {
                "chunk_text": chunk.chunk_text,
                "doc_id": chunk.doc_id,
                "anchor_start": chunk.anchor_start,
            }
            for chunk in (state.retrieved_chunks or [])
        ]

        # Generate answer
        answer_result = generate_answer(state.query, contexts, settings)

        state.answer = answer_result.answer
        state.citations = answer_result.citations
        state.abstained = answer_result.abstained
        state.confidence = answer_result.confidence

        # Audit logging
        record_audit(
            session,
            query_id=state.query_id,
            user_id=state.user_id,
            matter_id=state.matter_id,
            step_name="answer_synthesis",
        )

        logger.info(
            "workflow_node_complete",
            node="synthesis",
            query_id=state.query_id,
            abstained=state.abstained,
            citation_count=len(state.citations or []),
        )

    except Exception as e:
        logger.error("workflow_node_failed", node="synthesis", error=str(e))
        state.errors.append(f"Answer synthesis failed: {str(e)}")
        # Set error response
        state.answer = "An error occurred while generating the answer."
        state.abstained = True
        state.confidence = 0.0

    return state


def validation_node(state: QueryState, session: Session, settings: Settings) -> QueryState:
    """Validate citations and answer quality.

    Args:
        state: Workflow state with answer and citations.
        session: Database session.
        settings: Application settings.

    Returns:
        Updated state with validation results.
    """
    logger = get_logger(__name__)

    try:
        logger.info("workflow_node_start", node="validation", query_id=state.query_id)

        # Validation 1: Citations present if not abstained
        if not state.abstained and not state.citations:
            state.warnings.append("Answer has no citations")
            state.confidence = max(0.0, state.confidence - 0.3)

        # Validation 2: Citations match context count
        if state.citations and state.retrieved_chunks:
            max_context = len(state.retrieved_chunks)
            for citation in state.citations:
                if citation.context_number > max_context:
                    state.warnings.append(
                        f"Invalid citation number: {citation.context_number}"
                    )
                    state.confidence = max(0.0, state.confidence - 0.1)

        # Validation 3: Answer not empty
        if not state.answer or len(state.answer.strip()) < 10:
            state.warnings.append("Answer is too short or empty")
            state.confidence = 0.0

        logger.info(
            "workflow_node_complete",
            node="validation",
            query_id=state.query_id,
            warnings_count=len(state.warnings),
        )

    except Exception as e:
        logger.error("workflow_node_failed", node="validation", error=str(e))
        state.warnings.append(f"Validation error: {str(e)}")

    return state


def run_workflow(state: QueryState, session: Session, settings: Settings) -> QueryState:
    """Execute the full query processing workflow.

    Workflow: retrieval → synthesis → validation
    Saves checkpoints after each node.

    Args:
        state: Initial workflow state.
        session: Database session.
        settings: Application settings.

    Returns:
        Final workflow state with answer.
    """
    logger = get_logger(__name__)

    logger.info("workflow_start", query_id=state.query_id)

    # Node 1: Retrieval
    state = retrieval_node(state, session, settings)
    save_checkpoint(state, "retrieval", session)

    # Check if we can continue
    if state.errors and not state.retrieved_chunks:
        logger.error(
            "workflow_aborted_after_retrieval",
            query_id=state.query_id,
            errors=state.errors,
        )
        state.answer = "Unable to retrieve relevant documents."
        state.abstained = True
        return state

    # Node 2: Synthesis
    state = synthesis_node(state, session, settings)
    save_checkpoint(state, "synthesis", session)

    # Check if synthesis succeeded
    if state.errors and not state.answer:
        logger.error(
            "workflow_aborted_after_synthesis",
            query_id=state.query_id,
            errors=state.errors,
        )
        return state

    # Node 3: Validation
    state = validation_node(state, session, settings)
    save_checkpoint(state, "validation", session)

    logger.info(
        "workflow_complete",
        query_id=state.query_id,
        abstained=state.abstained,
        confidence=state.confidence,
        errors_count=len(state.errors),
        warnings_count=len(state.warnings),
    )

    return state
