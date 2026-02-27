"""Tests for embedding generation (T4 part 2).

Covers:
  FR-ING-4 – Embedding computation and storage
  Embedding consistency and dimensionality
"""

import pytest

from app.embeddings import (
    generate_embedding,
    generate_embeddings_batch,
    get_embedding_dimension,
    get_embedding_model,
)


class TestEmbeddingGeneration:
    def test_generates_embedding_vector(self):
        text = "This is a test sentence for embedding."
        embedding = generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    def test_different_texts_produce_different_embeddings(self):
        text1 = "Legal contract clause about payment terms."
        text2 = "Recipe for chocolate cake with frosting."

        emb1 = generate_embedding(text1)
        emb2 = generate_embedding(text2)

        assert emb1 != emb2

    def test_same_text_produces_same_embedding(self):
        text = "Consistent text for embedding test."

        emb1 = generate_embedding(text)
        emb2 = generate_embedding(text)

        assert emb1 == emb2

    def test_handles_empty_string(self):
        embedding = generate_embedding("")

        assert len(embedding) == 384


class TestBatchEmbedding:
    def test_generates_batch_embeddings(self):
        texts = [
            "First legal clause.",
            "Second legal clause.",
            "Third legal clause.",
        ]

        embeddings = generate_embeddings_batch(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)

    def test_batch_consistency_with_single(self):
        text = "Test text for consistency check."

        single_emb = generate_embedding(text)
        batch_embs = generate_embeddings_batch([text])

        assert len(batch_embs) == 1
        assert batch_embs[0] == single_emb

    def test_handles_empty_list(self):
        embeddings = generate_embeddings_batch([])

        assert embeddings == []


class TestEmbeddingModel:
    def test_model_caching(self):
        model1 = get_embedding_model()
        model2 = get_embedding_model()

        assert model1 is model2

    def test_embedding_dimension(self):
        dim = get_embedding_dimension()

        assert dim == 384
        assert isinstance(dim, int)
