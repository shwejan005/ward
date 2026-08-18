# ADR 0001: LangGraph StateGraph Orchestration

## Status
Accepted

## Context
A production PR review agent requires parallel fan-out across multiple specialist reasoners (Security, Quality, Tests, Docs), state checkpointing, human-in-the-loop (HITL) resumption, and structured aggregation. We evaluated Temporal and LangGraph.

## Decision
We choose **LangGraph StateGraph** as the primary orchestration engine, encapsulated behind an abstract `WorkflowEngine` protocol.

## Consequences
- **Pros**: Native multi-agent abstractions, lower operational complexity than a distributed Temporal cluster, easy fan-out via parallel execution, checkpoint support for pause/resume.
- **Cons**: Requires custom persistence adapters for complex long-running durable executions exceeding multiple days.
- **Mitigation**: The `WorkflowEngine` protocol in `backend/core/` ensures zero orchestrator lock-in; Temporal can be swapped in without modifying any domain or specialist agent code.
