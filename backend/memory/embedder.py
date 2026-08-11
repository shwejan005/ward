"""Embedding client wrapping OpenAI text-embedding-3-large (256-dim)."""

from __future__ import annotations

import structlog
from openai import AsyncOpenAI

from backend.settings import settings

logger = structlog.get_logger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the configured embedding model.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each is a list of floats).
    """
    if not texts:
        return []

    client = _get_client()

    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
        dimensions=settings.embedding_dimensions,
    )

    # Sort by index to maintain order
    sorted_data = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in sorted_data]


async def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    results = await embed_texts([text])
    return results[0]
