# ADR 0003: Tiger Cloud Unified Data Spine (PostgreSQL + TimescaleDB + DiskANN)

## Status
Accepted

## Context
Traditional AI agent architectures fragment data across three separate databases:
1. Vector DB (e.g. Qdrant / Pinecone) for code chunks.
2. Relational DB (e.g. Postgres) for PR records and HITL state.
3. Time-Series DB or Observability collector (e.g. ClickHouse / Datadog) for execution traces.

This fragmentation triples connection pool overhead, breaks transactional consistency, and complicates backups.

## Decision
We consolidate all storage needs into a **single PostgreSQL-compatible database** (Tiger Cloud / TimescaleDB with pgvector and pgvectorscale):
- **Memory Lane**: `code_chunks` table using DiskANN index (`vector_cosine_ops`) and GIN FTS (`tsvector`).
- **Truth Lane**: Standard relational tables for reviews, findings, and HITL state.
- **Time Lane**: `agent_events` 1-day partitioned Hypertable.
- **Rollup Lane**: Real-time Continuous Aggregates (`agent_health_1m`, `pr_cost_hourly`).

## Consequences
- Single connection pool, atomic schema migrations via SQL.
- Hybrid vector + full-text search executed in a single SQL query via Reciprocal Rank Fusion.
