# ADR 0002: Modular Monolith Architecture with Inward-Only Dependencies

## Status
Accepted

## Context
Microservice architectures introduce severe operational overhead, distributed transaction failures, network latency penalties between agent hops, and duplicate data schemas.

## Decision
We structure WARD as a **Modular Monolith** with strict inward-only dependency rules:
- `backend/core/` has **0 external dependencies** and defines protocols and exception types.
- Outer modules (`agents`, `api`, `orchestrator`, `hitl`) depend inward on `models` and `core`.
- Observability and event emission are side-effect safe and non-blocking.

## Consequences
- Fast in-process function calls during agent fan-out.
- Single codebase, unified testing suite, atomic migrations.
- Modules can be cleanly extracted into independent microservices later if scaling demands dictate.
