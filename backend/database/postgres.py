"""Async PostgreSQL connection management.

Provides a shared asyncpg pool for hot-path queries (events, retrieval)
and SQLAlchemy async sessions for ORM operations on truth tables.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import asyncpg
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.settings import settings

# ── asyncpg pool (hot path: events, vector search) ──────────────────────────

_pool: asyncpg.Pool | None = None


async def get_asyncpg_pool() -> asyncpg.Pool:
    """Get or create the shared asyncpg connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.tiger_database_url,
            min_size=5,
            max_size=20,
        )
    return _pool


async def close_asyncpg_pool() -> None:
    """Close the asyncpg pool on shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


# ── SQLAlchemy async engine (ORM: truth tables) ─────────────────────────────

def _sa_url() -> str:
    """Convert postgres:// to postgresql+asyncpg:// for SQLAlchemy."""
    url = settings.tiger_database_url
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


_engine = create_async_engine(
    _sa_url(),
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=True,
)

_session_factory = async_sessionmaker(
    _engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Get a SQLAlchemy async session. Automatically commits or rolls back."""
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
