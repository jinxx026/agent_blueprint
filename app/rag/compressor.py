"""Query-aware context compression that retains citations and structural context."""

import re

from app.rag.models import RetrievedContext, ScoredChunk
from app.rag.text import terms

SENTENCE_BOUNDARY = re.compile(r"(?<=[。！？!?；;\.])\s*|\n+")


class ContextCompressor:
    def __init__(self, max_characters_per_chunk: int = 350) -> None:
        self._max_characters = max_characters_per_chunk

    def compress(self, query: str, candidate: ScoredChunk) -> RetrievedContext:
        query_terms = set(terms(query))
        sentences = [
            sentence.strip()
            for sentence in SENTENCE_BOUNDARY.split(candidate.chunk.raw_content)
            if sentence.strip()
        ]
        ranked = sorted(
            enumerate(sentences),
            key=lambda item: (
                -len(query_terms.intersection(terms(item[1]))),
                item[0],
            ),
        )
        selected_indexes: list[int] = []
        used = 0
        for index, sentence in ranked:
            relevance = len(query_terms.intersection(terms(sentence)))
            if relevance == 0 and selected_indexes:
                continue
            if used + len(sentence) > self._max_characters and selected_indexes:
                continue
            selected_indexes.append(index)
            used += len(sentence)
        if not selected_indexes and sentences:
            selected_indexes = [0]
        body = "".join(sentences[index] for index in sorted(selected_indexes))
        body = body[: self._max_characters]
        content = f"[文档: {candidate.chunk.title}] [章节: {candidate.chunk.section}]\n{body}"
        return RetrievedContext(
            content=content,
            citation=candidate.chunk.citation,
            source_id=candidate.chunk.source_id,
            retrieval_score=candidate.retrieval_score,
            rerank_score=candidate.rerank_score,
            original_characters=len(candidate.chunk.contextual_content),
            compressed_characters=len(content),
        )
