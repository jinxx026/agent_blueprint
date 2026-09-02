# ADR 0007: Contextual RAG, reranking, and compression

## Status

Accepted.

## Decision

RAG ingestion preserves document structure and enriches each raw chunk with title,
section, document overview, and neighboring text before embedding. Query-time retrieval
uses semantic plus lexical scores to create a broad candidate set, applies tenant,
role, and source filters before scoring, reranks query/chunk pairs, and compresses the
winning chunks to relevant sentences while retaining citations.

Embedding, index, reranker, and compressor are replaceable interfaces. The local
implementations are deterministic and API-key free; production adapters can use a
vector database, provider embeddings, and a cross-encoder without changing agents.

## Consequences

- Chunks remain understandable when retrieved outside their original page.
- Retrieval favors recall first and precision second.
- Irrelevant tenants and unauthorized roles never reach model context.
- Compressed context lowers token use without losing source traceability.
- In-memory indexing is a development adapter, not durable production storage.
