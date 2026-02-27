"""Text chunking utilities for legal documents.

Implements legal-aware chunking that preserves document structure
while creating retrievable chunks with anchor information.
"""

import re
from typing import NamedTuple


class TextChunk(NamedTuple):
    """A chunk of text with anchor information."""

    chunk_index: int
    chunk_text: str
    anchor_start: str
    anchor_end: str


class ChunkingResult(NamedTuple):
    """Result of chunking a document."""

    chunks: list[TextChunk]


def chunk_by_tokens(
    text: str,
    anchor_value: str,
    chunk_size: int = 500,
    overlap: int = 50,
    start_index: int = 0,
) -> list[TextChunk]:
    """Chunk text by approximate token count with overlap.

    Args:
        text: Text content to chunk.
        anchor_value: Anchor identifier (e.g., page number, paragraph ID).
        chunk_size: Target size in characters (rough token approximation).
        overlap: Number of characters to overlap between chunks.
        start_index: Starting chunk index.

    Returns:
        List of TextChunk objects.
    """
    chunks = []
    text_length = len(text)
    current_pos = 0
    chunk_idx = start_index

    while current_pos < text_length:
        end_pos = min(current_pos + chunk_size, text_length)

        if end_pos < text_length:
            chunk_end = text.rfind(" ", current_pos, end_pos)
            if chunk_end == -1 or chunk_end <= current_pos:
                chunk_end = end_pos
        else:
            chunk_end = text_length

        chunk_text = text[current_pos:chunk_end].strip()

        if chunk_text:
            chunks.append(
                TextChunk(
                    chunk_index=chunk_idx,
                    chunk_text=chunk_text,
                    anchor_start=anchor_value,
                    anchor_end=anchor_value,
                )
            )
            chunk_idx += 1

        current_pos = chunk_end - overlap if chunk_end < text_length else text_length

        if current_pos >= text_length:
            break

    return chunks


def chunk_by_sentences(
    text: str,
    anchor_value: str,
    sentences_per_chunk: int = 5,
    start_index: int = 0,
) -> list[TextChunk]:
    """Chunk text by sentences, preserving sentence boundaries.

    Args:
        text: Text content to chunk.
        anchor_value: Anchor identifier.
        sentences_per_chunk: Number of sentences per chunk.
        start_index: Starting chunk index.

    Returns:
        List of TextChunk objects.
    """
    sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(sentence_pattern, text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    chunk_idx = start_index

    for i in range(0, len(sentences), sentences_per_chunk):
        chunk_sentences = sentences[i : i + sentences_per_chunk]
        chunk_text = " ".join(chunk_sentences)

        chunks.append(
            TextChunk(
                chunk_index=chunk_idx,
                chunk_text=chunk_text,
                anchor_start=anchor_value,
                anchor_end=anchor_value,
            )
        )
        chunk_idx += 1

    return chunks


def chunk_document(
    extracted_texts: list[tuple[str, str]],
    strategy: str = "tokens",
    chunk_size: int = 500,
    overlap: int = 50,
) -> ChunkingResult:
    """Chunk a document from extracted text anchors.

    Args:
        extracted_texts: List of (anchor_value, text_content) tuples.
        strategy: Chunking strategy ("tokens" or "sentences").
        chunk_size: Target chunk size (for token strategy).
        overlap: Overlap size (for token strategy).

    Returns:
        ChunkingResult with all chunks from the document.
    """
    all_chunks = []
    chunk_idx = 0

    for anchor_value, text_content in extracted_texts:
        if not text_content.strip():
            continue

        if strategy == "sentences":
            chunks = chunk_by_sentences(
                text_content, anchor_value, sentences_per_chunk=5, start_index=chunk_idx
            )
        else:
            chunks = chunk_by_tokens(
                text_content, anchor_value, chunk_size, overlap, start_index=chunk_idx
            )

        all_chunks.extend(chunks)
        chunk_idx += len(chunks)

    return ChunkingResult(chunks=all_chunks)


def chunk_legal_document(
    extracted_texts: list[tuple[str, str, str]],
    chunk_size: int = 500,
    overlap: int = 50,
) -> ChunkingResult:
    """Chunk a legal document with structure awareness.

    Attempts to identify legal structure (headings, clauses, definitions)
    and create chunks that respect these boundaries when possible.

    Args:
        extracted_texts: List of (anchor_type, anchor_value, text_content) tuples.
        chunk_size: Target chunk size in characters.
        overlap: Overlap size in characters.

    Returns:
        ChunkingResult with all chunks.
    """
    all_chunks = []
    chunk_idx = 0

    heading_pattern = r'^(?:\d+\.)+\s+[A-Z]|^[A-Z][A-Z\s]+:|\b(?:ARTICLE|SECTION|CLAUSE)\s+\d+'

    for anchor_type, anchor_value, text_content in extracted_texts:
        if not text_content.strip():
            continue

        lines = text_content.split("\n")
        current_section = []
        current_anchor_start = anchor_value

        for line in lines:
            line = line.strip()
            if not line:
                continue

            is_heading = bool(re.match(heading_pattern, line, re.IGNORECASE))

            if is_heading and current_section:
                section_text = " ".join(current_section)
                chunks = chunk_by_tokens(
                    section_text,
                    current_anchor_start,
                    chunk_size,
                    overlap,
                    start_index=chunk_idx,
                )
                all_chunks.extend(chunks)
                chunk_idx += len(chunks)
                current_section = []
                current_anchor_start = anchor_value

            current_section.append(line)

        if current_section:
            section_text = " ".join(current_section)
            chunks = chunk_by_tokens(
                section_text, current_anchor_start, chunk_size, overlap, start_index=chunk_idx
            )
            all_chunks.extend(chunks)
            chunk_idx += len(chunks)

    return ChunkingResult(chunks=all_chunks)
