# ADR 0006: Managed enterprise connector gateway

## Status

Accepted.

## Decision

Agents never call enterprise APIs directly. Every call passes through a managed tool
executor that validates JSON Schema arguments, resolves an allow-listed connector,
adds an execution-scoped idempotency key, retries only transient failures, normalizes
errors, and writes a credential-free audit event.

Authentication is deployment configuration and is never stored in a Blueprint.
HTTP operations must be explicitly mapped to paths; model-provided URLs are not used.
Approval-bound tools are denied by default until the human approval runtime is added.

## Consequences

- Model output cannot select arbitrary hosts or operations.
- Invalid tool arguments fail before reaching a business system.
- Retried writes do not create duplicate operations within one execution.
- Audit records contain argument names, but not values, tokens, or response bodies.
- The same gateway supports in-memory tests and real HTTP systems.
