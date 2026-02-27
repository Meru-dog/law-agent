"""Tests for text chunking (T4 part 1).

Covers:
  FR-ING-3 – Legal-aware chunking with structure preservation
  Chunk anchor tracking
"""

import pytest

from app.chunking import (
    ChunkingResult,
    TextChunk,
    chunk_by_sentences,
    chunk_by_tokens,
    chunk_document,
    chunk_legal_document,
)


class TestChunkByTokens:
    def test_chunks_text_into_segments(self):
        text = "This is a test sentence. " * 50
        chunks = chunk_by_tokens(text, anchor_value="page-1", chunk_size=100, overlap=20)

        assert len(chunks) > 1
        assert all(isinstance(c, TextChunk) for c in chunks)

    def test_chunk_indices_are_sequential(self):
        text = "Word " * 200
        chunks = chunk_by_tokens(text, anchor_value="page-1", chunk_size=100, overlap=20)

        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_chunks_preserve_anchor(self):
        text = "Some text content here."
        chunks = chunk_by_tokens(text, anchor_value="page-42", chunk_size=100, overlap=10)

        assert all(c.anchor_start == "page-42" for c in chunks)
        assert all(c.anchor_end == "page-42" for c in chunks)

    def test_respects_start_index(self):
        text = "Test content."
        chunks = chunk_by_tokens(text, anchor_value="p1", chunk_size=50, start_index=10)

        assert chunks[0].chunk_index == 10

    def test_handles_empty_text(self):
        chunks = chunk_by_tokens("", anchor_value="p1", chunk_size=100, overlap=20)
        assert len(chunks) == 0

    def test_overlap_creates_redundancy(self):
        text = "First sentence here. Second sentence here. Third sentence here."
        chunks = chunk_by_tokens(text, anchor_value="p1", chunk_size=30, overlap=10)

        assert len(chunks) >= 2


class TestChunkBySentences:
    def test_chunks_by_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        chunks = chunk_by_sentences(text, anchor_value="p1", sentences_per_chunk=2)

        assert len(chunks) == 3
        assert "First sentence" in chunks[0].chunk_text
        assert "Second sentence" in chunks[0].chunk_text

    def test_preserves_anchor_information(self):
        text = "Sentence one. Sentence two."
        chunks = chunk_by_sentences(text, anchor_value="para-5", sentences_per_chunk=1)

        assert all(c.anchor_start == "para-5" for c in chunks)

    def test_handles_single_sentence(self):
        text = "Only one sentence here."
        chunks = chunk_by_sentences(text, anchor_value="p1", sentences_per_chunk=3)

        assert len(chunks) == 1


class TestChunkDocument:
    def test_chunks_multiple_anchors(self):
        extracted_texts = [
            ("page-1", "This is page one content. " * 20),
            ("page-2", "This is page two content. " * 20),
        ]

        result = chunk_document(extracted_texts, strategy="tokens", chunk_size=100)

        assert isinstance(result, ChunkingResult)
        assert len(result.chunks) > 2

    def test_chunk_indices_span_entire_document(self):
        extracted_texts = [
            ("page-1", "Content one. " * 10),
            ("page-2", "Content two. " * 10),
        ]

        result = chunk_document(extracted_texts, strategy="tokens", chunk_size=50)

        indices = [c.chunk_index for c in result.chunks]
        assert indices == list(range(len(result.chunks)))

    def test_sentence_strategy(self):
        extracted_texts = [
            ("para-1", "First sentence. Second sentence. Third sentence.")
        ]

        result = chunk_document(extracted_texts, strategy="sentences")

        assert len(result.chunks) >= 1

    def test_skips_empty_content(self):
        extracted_texts = [
            ("page-1", "Content here."),
            ("page-2", "   "),
            ("page-3", "More content."),
        ]

        result = chunk_document(extracted_texts, strategy="tokens", chunk_size=100)

        assert all(c.chunk_text.strip() for c in result.chunks)


class TestChunkLegalDocument:
    def test_identifies_headings(self):
        extracted_texts = [
            (
                "page",
                "1",
                "1. INTRODUCTION\nThis is introductory text.\n2. DEFINITIONS\nDefinition text here.",
            )
        ]

        result = chunk_legal_document(extracted_texts, chunk_size=200)

        assert len(result.chunks) >= 1

    def test_handles_article_sections(self):
        extracted_texts = [
            ("page", "1", "ARTICLE I: PURPOSE\nThe purpose is stated here.\nARTICLE II: SCOPE\nThe scope is defined here.")
        ]

        result = chunk_legal_document(extracted_texts, chunk_size=500)

        assert len(result.chunks) >= 1

    def test_preserves_anchor_references(self):
        extracted_texts = [
            ("page", "5", "Some legal clause text here with sufficient length to create chunks.")
        ]

        result = chunk_legal_document(extracted_texts, chunk_size=100)

        assert all(c.anchor_start == "5" for c in result.chunks)

    def test_handles_clause_pattern(self):
        extracted_texts = [
            ("page", "1", "CLAUSE 1: First clause content.\nCLAUSE 2: Second clause content.")
        ]

        result = chunk_legal_document(extracted_texts, chunk_size=500)

        assert len(result.chunks) >= 1
