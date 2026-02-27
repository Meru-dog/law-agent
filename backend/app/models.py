"""SQLAlchemy ORM models for the audit log and document storage.

Stores structured audit entries (IDs and metadata only, never raw document text).
Stores document metadata and extracted text with anchors for retrieval.
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


class AuditEntry(Base):
    """Persistent audit log entry.

    Records every query attempt (success and denial) with identifiers only.
    No raw document text is ever stored (NFR-SEC-3).
    """

    __tablename__ = "audit_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    matter_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Document(Base):
    """Document metadata and storage information.

    Stores metadata for uploaded documents with matter-scoped ACL.
    Original files are stored on disk; this table tracks metadata only.
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(
        String(36), unique=True, index=True, nullable=False
    )
    matter_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    extracted_texts: Mapped[list["ExtractedText"]] = relationship(
        "ExtractedText", back_populates="document", cascade="all, delete-orphan"
    )


class ExtractedText(Base):
    """Extracted text with page/section anchors.

    Stores text extracted from documents with anchor information
    (page numbers for PDF, paragraph IDs for DOCX) for citation.
    """

    __tablename__ = "extracted_texts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.doc_id"), index=True, nullable=False
    )
    anchor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    anchor_value: Mapped[str] = mapped_column(String(255), nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship("Document", back_populates="extracted_texts")


class Chunk(Base):
    """Text chunk with vector embedding for retrieval.

    Chunks are matter-scoped and include anchor information for citation.
    Vector embeddings enable semantic similarity search.
    """

    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_id: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    doc_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.doc_id"), index=True, nullable=False
    )
    matter_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    anchor_start: Mapped[str] = mapped_column(String(255), nullable=False)
    anchor_end: Mapped[str] = mapped_column(String(255), nullable=False)
    embedding: Mapped[Vector] = mapped_column(Vector(384), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WorkflowCheckpoint(Base):
    """Workflow execution checkpoint for debugging and recovery.

    Stores intermediate state at each workflow node for audit and resume capability.
    """

    __tablename__ = "workflow_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    node_name: Mapped[str] = mapped_column(String(50), nullable=False)
    state_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
