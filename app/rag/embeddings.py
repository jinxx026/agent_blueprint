"""Deterministic local embeddings implementing LangChain's Embeddings interface."""

import hashlib
import math

from langchain_core.embeddings import Embeddings

from app.rag.text import terms


class HashEmbeddings(Embeddings):
    """Offline feature hashing; replace with provider embeddings in production."""

    def __init__(self, dimensions: int = 256) -> None:
        self._dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in terms(text):
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
