"""RAG retrieval boundary and an in-memory adapter for local execution."""

from collections import defaultdict
from collections.abc import Iterable
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from app.compiler.intermediate import RetrieverSpec


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    content: str
    citation: str


class KnowledgeRetriever(Protocol):
    def retrieve(self, spec: RetrieverSpec, query: str) -> tuple[KnowledgeDocument, ...]: ...


class MemoryKnowledgeStore:
    """Simple retriever with the same boundary a vector database will implement."""

    def __init__(self, documents: Iterable[KnowledgeDocument] = ()) -> None:
        self._documents: dict[str, list[KnowledgeDocument]] = defaultdict(list)
        for document in documents:
            self._documents[document.source_id].append(document)

    def retrieve(self, spec: RetrieverSpec, query: str) -> tuple[KnowledgeDocument, ...]:
        candidates = [
            document
            for source_id in spec.source_ids
            for document in self._documents.get(source_id, [])
        ]
        query_terms = {term.lower() for term in query.split() if term.strip()}

        def score(document: KnowledgeDocument) -> tuple[int, str]:
            content = document.content.lower()
            matches = sum(term in content for term in query_terms)
            return (-matches, document.citation)

        return tuple(sorted(candidates, key=score)[: spec.top_k])
