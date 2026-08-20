# Ward — Autonomous Multi-Agent PR Review System

> **WARD** is not a linter with an LLM bolted on. It is a parallel fan-out of grounded specialist reasoners over a Git diff, backed by a unified Postgres-compatible data spine with full auditability, cost control, and confidence-weighted human-in-the-loop gating.

## Architecture

WARD implements a **Modular Monolith** (ADR-002) with strict inward-only dependency rules:

```
GitHub PR → Webhook Ingress → Redis/ARQ Queue → LangGraph Orchestrator
    ↓
┌───────────┬───────────┬───────────┬───────────┐
│ Security  │ Quality   │  Tests    │   Docs    │  ← 4 Specialist Agents (parallel)
│  Agent    │  Agent    │  Agent    │  Agent    │
└─────┬─────┴─────┬─────┴─────┬─────┴─────┬─────┘
      └───────────┴───────────┴───────────┘
                      ↓
              Aggregator (merge, dedup, consensus)
                      ↓
              Confidence-Weighted HITL Gate
              ↓                         ↓
    Auto-post to GitHub PR      Route to Human Queue
```

### Data Spine (Tiger Cloud / TimescaleDB — ADR-003)

One Postgres-compatible database, three internal lanes:

| Lane | Table | Index / Feature |
|------|-------|-----------------|
| **Memory** | `code_chunks` | pgvectorscale DiskANN + GIN FTS |
| **Time** | `agent_events` | TimescaleDB Hypertable (1-day) |
| **Rollups** | `agent_health_1m`, `pr_cost_hourly` | Continuous Aggregates |
| **Truth** | `pr_review_records`, `finding_records`, `hitl_*` | Standard relational |

### Key Technologies

- **Backend**: Python 3.10+, FastAPI, Pydantic v2
- **Orchestration**: LangGraph StateGraph with parallel Send API
- **Queue**: Redis + ARQ
- **Database**: Tiger Cloud (TimescaleDB + pgvector + pgvectorscale)
- **Frontend**: Next.js (App Router)
- **Embeddings**: OpenAI text-embedding-3-large (256-dim)

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env
# Fill in TIGER_DATABASE_URL, OPENAI_API_KEY, GITHUB_* credentials

# 2. Start infrastructure
docker compose up -d

# 3. Run database migrations
psql $TIGER_DATABASE_URL -f scripts/migrations/001_tiger_init.sql

# 4. Start the API server
cd backend && uvicorn api.main:app --reload --port 8000

# 5. Start the ARQ worker
cd backend && python -m job_queue.arq_worker

# 6. Start the frontend
cd frontend && npm run dev
```

## Project Structure

```
ward/
├── backend/
│   ├── agents/           # 4 specialist agents + base + contracts
│   ├── api/              # FastAPI routes (reviews, economics, HITL)
│   ├── auth/             # RBAC & webhook auth dependencies
│   ├── core/             # Abstract workflow engine, exceptions (0 deps)
│   ├── data/             # Code chunking & embedding ingestion
│   ├── database/         # Async Postgres, ORM models, repositories
│   ├── economics/        # BudgetGuard, cost queries, routing advisor
│   ├── evaluation/       # Golden datasets, LLM-as-judge, regression gate
│   ├── hitl/             # Approval queue, escalation, disputes, feedback
│   ├── integrations/     # GitHub REST client & models
│   ├── job_queue/        # ARQ worker & task definitions
│   ├── memory/           # Hybrid RAG (DiskANN + FTS), embedder
│   ├── models/           # Pydantic domain models (Finding, Review, etc.)
│   ├── observability/    # Events spine, tracing, audit, alerts
│   ├── orchestrator/     # LangGraph graph, nodes, state, engine
│   ├── prompts/          # Versioned prompt registry & templates
│   ├── reliability/      # Retry, circuit breaker, idempotency, timeout
│   ├── security/         # Threat model, injection guard, RBAC, masking
│   ├── tools/            # LLM client, model router, tool registry
│   └── webhook_receiver/ # HMAC validation, payload parsing, routing
├── scripts/migrations/   # Idempotent DDL (Tiger Cloud schema)
├── tests/                # Unit, integration, evaluation tests
├── frontend/             # Next.js review dashboard
├── docker-compose.yml    # Redis + TimescaleDB + API + Worker
└── .env.example          # Environment variable template
```

## Architecture Decision Records

| ADR | Decision | Rationale |
|-----|----------|-----------|
| ADR-001 | LangGraph over Temporal | Lower operational cost for current scale; swappable via `WorkflowEngine` interface |
| ADR-002 | Modular Monolith | Inward-only deps; any outer module deletable without breaking inner |
| ADR-003 | Tiger Cloud single data spine | Memory + Truth + Time in one Postgres; fewer connection pools, one backup story |
| ADR-004 | Continuous Aggregate BudgetGuard | Pre-aggregated cost data; BudgetGuard reads summary, not raw events |

## License

MIT
