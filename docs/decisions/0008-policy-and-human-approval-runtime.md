# ADR 0008: Deterministic policy and human approval runtime

## Status

Accepted.

## Decision

Compiled policies are evaluated by deterministic code immediately before tool
execution. Runtime facts and validated tool arguments are compared using the compiler's
restricted operators; no model and no `eval` participates in authorization. Missing
facts fail closed. Decisions use the precedence transfer, deny, require approval, allow.

Approval-bound actions call LangGraph `interrupt()` before any connector side effect.
The request is persisted by the checkpointer and execution resumes with
`Command(resume=...)` on the same thread. Approval ID, role, reason, and expiry are
validated again before the connector runs. Connector idempotency protects node replay.

## Consequences

- The model cannot approve its own action or bypass a policy.
- User roles must intersect the tool's allowed roles.
- Missing identity or amount facts deny rather than guess.
- Approval and connector decisions have separate audit trails.
- In-memory persistence is a local adapter; production must use durable storage and
  roles derived from verified identity.
