-- ============================================================================
-- WARD — Unified Data Spine Schema (ADR-003)
-- Tiger Cloud / TimescaleDB + pgvector + pgvectorscale
--
-- Idempotent: safe to run multiple times (IF NOT EXISTS everywhere).
-- Four lanes: Memory, Truth, Time, Rollups — one database.
-- ============================================================================

-- ── Extensions ──────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;          -- pgvector
CREATE EXTENSION IF NOT EXISTS vectorscale;     -- pgvectorscale (DiskANN)
CREATE EXTENSION IF NOT EXISTS timescaledb;     -- TimescaleDB

-- ============================================================================
-- LANE 1 — MEMORY: code_chunks
-- Replaces a separate vector DB (Qdrant). Each row is one chunk of code from
-- a monitored repository, with its embedding and full-text search index.
-- ============================================================================

CREATE TABLE IF NOT EXISTS code_chunks (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    repo         TEXT         NOT NULL,           -- e.g. "org/repo-name"
    path         TEXT         NOT NULL,           -- e.g. "src/auth/session.py"
    symbol       TEXT,                            -- function/class name (nullable)
    chunk_index  INT          NOT NULL DEFAULT 0, -- order within file
    content      TEXT         NOT NULL,           -- raw source code text
    embedding    VECTOR(256)  NOT NULL,           -- text-embedding-3-large, 256 dims
    token_count  INT,                             -- token count of content
    commit_sha   TEXT,                            -- git SHA when this was embedded
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),

    UNIQUE (repo, path, chunk_index)              -- one chunk per position per file
);

-- DiskANN index for fast approximate nearest-neighbor search on embeddings
CREATE INDEX IF NOT EXISTS code_chunks_emb_idx
    ON code_chunks USING diskann (embedding vector_cosine_ops);

-- Auto-generated tsvector column for full-text keyword search
ALTER TABLE code_chunks
    ADD COLUMN IF NOT EXISTS content_tsv TSVECTOR
        GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- GIN index for full-text search (catches exact function names, error codes, config keys)
CREATE INDEX IF NOT EXISTS code_chunks_fts_idx
    ON code_chunks USING GIN (content_tsv);

-- Composite index for repo + path lookups
CREATE INDEX IF NOT EXISTS code_chunks_repo_path_idx
    ON code_chunks (repo, path);

-- ============================================================================
-- LANE 2 — TRUTH: Review records, findings, HITL state
-- Standard relational tables. This is the durable source of truth for every
-- review the system has performed and every human decision made.
-- ============================================================================

-- One row per PR review
CREATE TABLE IF NOT EXISTS pr_review_records (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    repo            TEXT         NOT NULL,
    pr_number       INT          NOT NULL,
    pr_title        TEXT,
    pr_author       TEXT,
    head_sha        TEXT         NOT NULL,
    base_sha        TEXT,
    diff_size_lines INT,
    status          TEXT         NOT NULL DEFAULT 'pending',  -- pending|in_progress|completed|failed
    outcome         TEXT,                                      -- approved|request_changes|critical_block
    overall_confidence  NUMERIC(4,3),
    github_review_id    BIGINT,                               -- GitHub API review ID after posting
    total_cost_usd      NUMERIC(10,6) DEFAULT 0,
    total_tokens        INT DEFAULT 0,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    error_message   TEXT,
    idempotency_key TEXT         UNIQUE,                       -- X-GitHub-Delivery UUID

    UNIQUE (repo, pr_number, head_sha)
);

CREATE INDEX IF NOT EXISTS review_records_repo_idx
    ON pr_review_records (repo, pr_number);

CREATE INDEX IF NOT EXISTS review_records_status_idx
    ON pr_review_records (status);

-- One row per finding raised by a specialist agent
CREATE TABLE IF NOT EXISTS finding_records (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id       UUID         NOT NULL REFERENCES pr_review_records(id) ON DELETE CASCADE,
    agent_type      TEXT         NOT NULL,           -- security|quality|tests|docs
    severity        TEXT         NOT NULL,           -- critical|high|medium|low|info
    category        TEXT         NOT NULL,           -- e.g. "injection", "missing-test"
    file_path       TEXT,
    line_start      INT,
    line_end        INT,
    title           TEXT         NOT NULL,
    description     TEXT         NOT NULL,
    rationale       TEXT,                             -- why the agent flagged this
    suggestion      TEXT,                             -- suggested fix
    confidence      NUMERIC(4,3) NOT NULL DEFAULT 0.5,
    is_duplicate    BOOLEAN      NOT NULL DEFAULT false,
    dedupe_group    TEXT,                             -- aggregator dedup cluster ID
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS findings_review_idx
    ON finding_records (review_id);

CREATE INDEX IF NOT EXISTS findings_severity_idx
    ON finding_records (severity);

-- HITL review queue: when a review needs human approval
CREATE TABLE IF NOT EXISTS hitl_reviews (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id       UUID         NOT NULL REFERENCES pr_review_records(id) ON DELETE CASCADE,
    reason          TEXT         NOT NULL,            -- low_confidence|critical_finding|manual_request
    status          TEXT         NOT NULL DEFAULT 'pending',  -- pending|approved|rejected|expired
    assigned_to     TEXT,                             -- human reviewer username
    decision        TEXT,                             -- approve|reject|modify
    decision_notes  TEXT,
    decided_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ                      -- auto-expire stale reviews
);

CREATE INDEX IF NOT EXISTS hitl_reviews_status_idx
    ON hitl_reviews (status);

CREATE INDEX IF NOT EXISTS hitl_reviews_review_idx
    ON hitl_reviews (review_id);

-- Developer feedback on individual findings (dispute, agreement, etc.)
CREATE TABLE IF NOT EXISTS hitl_feedback (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id      UUID         NOT NULL REFERENCES finding_records(id) ON DELETE CASCADE,
    review_id       UUID         NOT NULL REFERENCES pr_review_records(id) ON DELETE CASCADE,
    feedback_type   TEXT         NOT NULL,            -- agree|disagree|dispute|false_positive
    comment         TEXT,
    submitted_by    TEXT,                             -- GitHub username
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS feedback_finding_idx
    ON hitl_feedback (finding_id);

-- ============================================================================
-- LANE 3 — TIME: agent_events (Hypertable)
-- Every agent action becomes one append-only row. This single table feeds the
-- trace viewer, the audit trail, and the cost ledger.
-- ============================================================================

CREATE TABLE IF NOT EXISTS agent_events (
    ts            TIMESTAMPTZ  NOT NULL,
    review_id     UUID         NOT NULL,
    agent         TEXT         NOT NULL,              -- security|quality|tests|docs|aggregator|orchestrator
    span_id       UUID         NOT NULL DEFAULT gen_random_uuid(),
    parent_span   UUID,
    event_type    TEXT         NOT NULL,              -- span.start|span.end|llm.call|tool.call|decision|escalation
    model         TEXT,                               -- e.g. "gpt-4o", "gpt-4o-mini"
    tokens_in     INT,
    tokens_out    INT,
    cost_usd      NUMERIC(10,6),
    latency_ms    INT,
    outcome       TEXT,                               -- approved|request_changes|critical_block|escalated
    confidence    NUMERIC(4,3),
    payload       JSONB                               -- flexible metadata bag
);

-- Convert to TimescaleDB hypertable with 1-day partitions
SELECT create_hypertable(
    'agent_events',
    by_range('ts', INTERVAL '1 day'),
    if_not_exists => TRUE
);

-- Index for querying events by review
CREATE INDEX IF NOT EXISTS events_review_idx
    ON agent_events (review_id, ts DESC);

-- Index for querying events by agent
CREATE INDEX IF NOT EXISTS events_agent_idx
    ON agent_events (agent, ts DESC);

-- ============================================================================
-- LANE 4 — ROLLUPS: Continuous Aggregates
-- Pre-computed summary tables that Tiger/TimescaleDB keeps updated. The
-- dashboard and BudgetGuard read these instead of scanning raw events.
-- ============================================================================

-- Per-agent health metrics, refreshed every minute
CREATE MATERIALIZED VIEW IF NOT EXISTS agent_health_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts)                          AS bucket,
    agent,
    count(*) FILTER (WHERE event_type = 'llm.call')      AS llm_calls,
    sum(cost_usd)                                        AS cost_usd,
    sum(tokens_in)                                       AS tokens_in,
    sum(tokens_out)                                      AS tokens_out,
    approx_percentile(0.95, percentile_agg(latency_ms))  AS p95_ms,
    count(*) FILTER (WHERE outcome = 'request_changes')::float
        / NULLIF(count(*) FILTER (WHERE outcome IS NOT NULL), 0) AS rejection_rate
FROM agent_events
GROUP BY bucket, agent
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'agent_health_1m',
    start_offset      => INTERVAL '2 hours',
    end_offset        => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists     => TRUE
);

-- Per-PR cost + token rollup, refreshed hourly
CREATE MATERIALIZED VIEW IF NOT EXISTS pr_cost_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', ts)   AS bucket,
    review_id,
    sum(cost_usd)               AS total_cost_usd,
    sum(tokens_in)              AS total_tokens_in,
    sum(tokens_out)             AS total_tokens_out,
    count(DISTINCT agent)       AS agents_used,
    max(confidence)             AS max_confidence
FROM agent_events
GROUP BY bucket, review_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'pr_cost_hourly',
    start_offset      => INTERVAL '4 hours',
    end_offset        => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists     => TRUE
);

-- ============================================================================
-- VERIFICATION QUERIES (run after migration to confirm success)
-- ============================================================================
-- SELECT * FROM timescaledb_information.hypertables;
-- SELECT * FROM timescaledb_information.continuous_aggregates;
-- SELECT extname, extversion FROM pg_extension WHERE extname IN ('vector', 'vectorscale', 'timescaledb');
-- \dt
