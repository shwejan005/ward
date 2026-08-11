"""Hybrid retrieval client: DiskANN vector + FTS with Reciprocal Rank Fusion (§2.2, §3.5).

The single retrieval interface that queries both the DiskANN vector index and
the GIN full-text search index on code_chunks, then merges results using RRF.
"""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

from backend.settings import settings

logger = structlog.get_logger(__name__)

# RRF constant (standard value from Cormack et al.)
_RRF_K = 60


class TigerMemoryClient:
    """Hybrid retrieval over the code_chunks table in Tiger Cloud.

    Combines:
    - DiskANN approximate nearest-neighbor search on embeddings
    - PostgreSQL tsvector full-text search on content

    Results merged with Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, pool: asyncpg.Pool | None = None) -> None:
        self._pool = pool

    async def _get_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                settings.tiger_database_url, min_size=2, max_size=10,
            )
        return self._pool

    async def hybrid_search(
        self,
        query_embedding: list[float],
        query_text: str,
        repo: str,
        *,
        top_k: int = 10,
        vector_weight: float = 0.6,
    ) -> list[dict[str, Any]]:
        """Run hybrid vector + FTS search with RRF merge.

        Args:
            query_embedding: The embedding vector for semantic search.
            query_text: The text query for keyword search.
            repo: Filter to chunks from this repository.
            top_k: Number of results to return.
            vector_weight: Weight for vector results in RRF (FTS gets 1 - this).

        Returns:
            List of dicts with: id, repo, path, symbol, content, score
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            # 1. DiskANN vector similarity search
            vector_results = await conn.fetch(
                """
                SELECT id, repo, path, symbol, content,
                       1 - (embedding <=> $1::vector) AS similarity
                FROM code_chunks
                WHERE repo = $2
                ORDER BY embedding <=> $1::vector
                LIMIT $3
                """,
                str(query_embedding),
                repo,
                top_k * 2,  # fetch more for RRF merge
            )

            # 2. Full-text search (catches exact names, error codes, config keys)
            fts_results = await conn.fetch(
                """
                SELECT id, repo, path, symbol, content,
                       ts_rank_cd(content_tsv, plainto_tsquery('english', $1)) AS rank
                FROM code_chunks
                WHERE repo = $2
                  AND content_tsv @@ plainto_tsquery('english', $1)
                ORDER BY rank DESC
                LIMIT $3
                """,
                query_text,
                repo,
                top_k * 2,
            )

        # 3. Reciprocal Rank Fusion
        rrf_scores: dict[str, float] = {}
        chunk_data: dict[str, dict[str, Any]] = {}

        for rank, row in enumerate(vector_results):
            chunk_id = str(row["id"])
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + vector_weight / (rank + _RRF_K)
            chunk_data[chunk_id] = dict(row)

        fts_weight = 1.0 - vector_weight
        for rank, row in enumerate(fts_results):
            chunk_id = str(row["id"])
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + fts_weight / (rank + _RRF_K)
            if chunk_id not in chunk_data:
                chunk_data[chunk_id] = dict(row)

        # Sort by RRF score descending
        sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)[:top_k]

        results = []
        for cid in sorted_ids:
            data = chunk_data[cid]
            results.append({
                "id": cid,
                "repo": data["repo"],
                "path": data["path"],
                "symbol": data.get("symbol"),
                "content": data["content"],
                "score": rrf_scores[cid],
            })

        return results

    async def search_by_path(
        self, repo: str, path: str, *, limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Fetch all chunks for a specific file path."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, repo, path, symbol, content, chunk_index
                FROM code_chunks
                WHERE repo = $1 AND path = $2
                ORDER BY chunk_index
                LIMIT $3
                """,
                repo,
                path,
                limit,
            )
        return [dict(r) for r in rows]
