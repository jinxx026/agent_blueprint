"""Immutable data contracts for the RAG pipeline."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RagDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str
    source_id: str
    document_id: str
    title: str
    content: str
    allowed_roles: tuple[str, ...]
    citation_base: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ContextualChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    tenant_id: str
    source_id: str
    document_id: str
    title: str
    section: str
    raw_content: str
    contextual_content: str
    allowed_roles: tuple[str, ...]
    citation: str
    start_index: int


class IndexedChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk: ContextualChunk
    embedding: tuple[float, ...]


class ScoredChunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk: ContextualChunk
    retrieval_score: float
    rerank_score: float = 0.0


class RetrievedContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    content: str
    citation: str
    source_id: str
    retrieval_score: float
    rerank_score: float
    original_characters: int
    compressed_characters: int
