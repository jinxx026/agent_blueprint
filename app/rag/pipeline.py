"""Compose ingestion, broad retrieval, reranking, and compression."""

from app.compiler.intermediate import RetrieverSpec
from app.rag.chunker import ContextualChunker
from app.rag.compressor import ContextCompressor
from app.rag.embeddings import HashEmbeddings
from app.rag.index import MemoryHybridIndex
from app.rag.models import RagDocument, RetrievedContext
from app.rag.reranker import LocalCrossEncoderReranker, Reranker
from app.runtime.retrievers import KnowledgeDocument


class RagPipeline:
    def __init__(
        self,
        chunker: ContextualChunker,
        index: MemoryHybridIndex,
        reranker: Reranker,
        compressor: ContextCompressor,
        candidate_multiplier: int = 4,
    ) -> None:
        self._chunker = chunker
        self._index = index
        self._reranker = reranker
        self._compressor = compressor
        self._candidate_multiplier = candidate_multiplier

    def ingest(self, documents: list[RagDocument]) -> int:
        count = 0
        for document in documents:
            chunks = self._chunker.split(document)
            self._index.replace_document(document.tenant_id, document.document_id, chunks)
            count += len(chunks)
        return count

    def retrieve(
        self,
        query: str,
        *,
        tenant_id: str,
        roles: frozenset[str],
        source_ids: frozenset[str],
        top_k: int,
        rerank: bool = True,
    ) -> tuple[RetrievedContext, ...]:
        candidates = self._index.search(
            query,
            tenant_id=tenant_id,
            roles=roles,
            source_ids=source_ids,
            limit=max(top_k, top_k * self._candidate_multiplier),
        )
        selected = self._reranker.rerank(query, candidates, top_k) if rerank else candidates[:top_k]
        return tuple(self._compressor.compress(query, item) for item in selected)


class RagKnowledgeStore:
    """Adapter exposing the production RAG pipeline to AgentFactory."""

    def __init__(self, pipeline: RagPipeline, tenant_id: str, roles: frozenset[str]) -> None:
        self._pipeline = pipeline
        self._tenant_id = tenant_id
        self._roles = roles

    def retrieve(self, spec: RetrieverSpec, query: str) -> tuple[KnowledgeDocument, ...]:
        results = self._pipeline.retrieve(
            query,
            tenant_id=self._tenant_id,
            roles=self._roles,
            source_ids=frozenset(spec.source_ids),
            top_k=spec.top_k,
            rerank=spec.rerank,
        )
        return tuple(
            KnowledgeDocument(
                source_id=result.source_id,
                content=result.content,
                citation=result.citation,
            )
            for result in results
        )


def create_local_rag_pipeline() -> RagPipeline:
    """Build the API-key-free pipeline used in local development and tests."""

    return RagPipeline(
        ContextualChunker(),
        MemoryHybridIndex(HashEmbeddings()),
        LocalCrossEncoderReranker(),
        ContextCompressor(),
    )
