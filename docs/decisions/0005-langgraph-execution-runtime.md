# ADR 0005: LangGraph execution runtime

## Status

Accepted.

## Decision

The portable `ExecutionPlan` is converted at runtime into a LangGraph `StateGraph`.
Each compiled agent becomes a LangChain `Runnable`; the outer graph owns delegation,
shared state, tracing, and checkpointing.

Model, knowledge retrieval, and enterprise tools are accessed through small adapter
interfaces. Phase 4 ships deterministic in-memory adapters so the graph is executable
and testable without API keys. Provider models, vector databases, and business-system
connectors can replace those adapters without changing Blueprint files or graph logic.

## Consequences

- The compiler remains deterministic and independent of LangChain.
- An agent receives only its compiled knowledge sources and tool bindings.
- Multi-agent behavior can be tested offline and reproduced exactly.
- The current supervisor executes specialists sequentially; parallel fan-out is a
  later runtime optimization and does not change the portable plan.
- Durable checkpoints, policy enforcement, approval interrupts, and real connectors
  remain separate production hardening stages.
