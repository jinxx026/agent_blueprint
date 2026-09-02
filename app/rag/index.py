"""Tenant-aware hybrid semantic and lexical candidate retrieval."""

import math
from collections import Counter
from threading import RLock

from langchain_core.embeddings import Embeddings

from app.rag.models import ContextualChunk, IndexedChunk, ScoredChunk
from app.rag.text import terms


class MemoryHybridIndex:
    def __init__(self, embeddings: Embeddings) -> None:
        self._embeddings = embeddings
        self._items: dict[str, IndexedChunk] = {}
        self._lock = RLock()

    def replace_document(
        self, tenant_id: str, document_id: str, chunks: tuple[ContextualChunk, ...]
    ) -> None:
        vectors = self._embeddings.embed_documents([chunk.contextual_content for chunk in chunks])
        indexed = [
            IndexedChunk(chunk=chunk, embedding=tuple(vector))
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        with self._lock:
            stale_ids = [
                chunk_id
                for chunk_id, item in self._items.items()
                if item.chunk.tenant_id == tenant_id and item.chunk.document_id == document_id
            ]
            for chunk_id in stale_ids:
                del self._items[chunk_id]
            for item in indexed:
                self._items[item.chunk.chunk_id] = item

    def search(
        self,
        query: str,
        *,
        tenant_id: str,
        roles: frozenset[str],
        source_ids: frozenset[str],
        limit: int,
    ) -> tuple[ScoredChunk, ...]:
        query_vector = self._embeddings.embed_query(query)
        query_terms = Counter(terms(query))
        scored = []
        with self._lock:
            items = tuple(self._items.values())
        for item in items:
            chunk = item.chunk
            if chunk.tenant_id != tenant_id or chunk.source_id not in source_ids:
                continue
            if not roles.intersection(chunk.allowed_roles):
                continue
            semantic = sum(a * b for a, b in zip(query_vector, item.embedding, strict=True))
            document_terms = Counter(terms(chunk.contextual_content))
            overlap = sum(min(count, document_terms[token]) for token, count in query_terms.items())
            lexical = overlap / math.sqrt(
                max(1, sum(query_terms.values())) * max(1, sum(document_terms.values()))
            )
            score = 0.65 * semantic + 0.35 * lexical
            scored.append(ScoredChunk(chunk=chunk, retrieval_score=score))
        return tuple(
            sorted(scored, key=lambda item: (-item.retrieval_score, item.chunk.chunk_id))[:limit]
        )
