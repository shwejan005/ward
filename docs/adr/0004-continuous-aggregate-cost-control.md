# ADR 0004: Continuous Aggregate BudgetGuard for Pre-Call Cost Control

## Status
Accepted

## Context
Unbounded LLM fan-outs can quickly cause cost spikes if malicious diffs, large files, or recursive loops trigger thousands of model calls. Post-hoc billing alerts are too late to prevent overruns.

## Decision
We implement **BudgetGuard** as a mandatory pre-call barrier reading from TimescaleDB Continuous Aggregates (`agent_health_1m` and `pr_cost_hourly`).

## Mechanism
1. Before every specialist invocation, BudgetGuard queries `agent_health_1m` for current daily spend.
2. If daily spend >= `DAILY_BUDGET_USD` or review spend >= `PER_REVIEW_BUDGET_USD`, a `BudgetExhaustedError` is raised immediately.
3. Reading pre-aggregated materialized views ensures < 2ms latency checks without full table scans on millions of raw event rows.
