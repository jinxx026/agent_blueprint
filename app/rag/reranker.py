"""Second-stage query/chunk scoring after broad candidate retrieval."""

from collections import Counter
from typing import Protocol

from app.rag.models import ScoredChunk
from app.rag.text import terms


class Reranker(Protocol):
    def rerank(
        self, query: str, candidates: tuple[ScoredChunk, ...], top_n: int
    ) -> tuple[ScoredChunk, ...]: ...


class LocalCrossEncoderReranker:
    """Offline pair scorer with the same contract as a hosted cross-encoder."""

    def rerank(
        self, query: str, candidates: tuple[ScoredChunk, ...], top_n: int
    ) -> tuple[ScoredChunk, ...]:
        query_terms = Counter(terms(query))
        reranked = []
        for candidate in candidates:
            chunk = candidate.chunk
            body_terms = Counter(terms(chunk.raw_content))
            context_terms = Counter(terms(f"{chunk.title} {chunk.section}"))
            body_overlap = sum(
                min(count, body_terms[token]) for token, count in query_terms.items()
            )
            context_overlap = sum(
                min(count, context_terms[token]) for token, count in query_terms.items()
            )
            denominator = max(1, sum(query_terms.values()))
            pair_score = (body_overlap + 1.5 * context_overlap) / denominator
            exact_boost = 0.25 if query.lower() in chunk.contextual_content.lower() else 0.0
            final_score = 0.35 * candidate.retrieval_score + 0.65 * pair_score + exact_boost
            reranked.append(candidate.model_copy(update={"rerank_score": round(final_score, 8)}))
        return tuple(
            sorted(reranked, key=lambda item: (-item.rerank_score, item.chunk.chunk_id))[:top_n]
        )
