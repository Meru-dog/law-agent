"""Embedding generation for text chunks.

Uses sentence-transformers to generate vector embeddings for semantic search.
"""

from functools import lru_cache
from typing import Any

from sentence_transformers import SentenceTransformer

from app.config import Settings


@lru_cache(maxsize=1)
def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    """Get cached embedding model.

    Uses a lightweight sentence transformer model suitable for semantic search.
    The model produces 384-dimensional embeddings.

    Args:
        model_name: Name of the sentence-transformers model to use.

    Returns:
        Loaded SentenceTransformer model.
    """
    return SentenceTransformer(model_name)


def generate_embedding(text: str, model_name: str = "all-MiniLM-L6-v2") -> list[float]:
    """Generate embedding vector for a text string.

    Args:
        text: Text to embed.
        model_name: Name of the embedding model to use.

    Returns:
        Embedding vector as a list of floats.
    """
    model = get_embedding_model(model_name)
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def generate_embeddings_batch(
    texts: list[str], model_name: str = "all-MiniLM-L6-v2"
) -> list[list[float]]:
    """Generate embeddings for multiple texts in batch (more efficient).

    Args:
        texts: List of text strings to embed.
        model_name: Name of the embedding model to use.

    Returns:
        List of embedding vectors.
    """
    if not texts:
        return []

    model = get_embedding_model(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


def get_embedding_dimension(model_name: str = "all-MiniLM-L6-v2") -> int:
    """Get the dimensionality of embeddings from a model.

    Args:
        model_name: Name of the embedding model.

    Returns:
        Embedding dimension.
    """
    model = get_embedding_model(model_name)
    return model.get_sentence_embedding_dimension()
