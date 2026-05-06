"""Embedding helpers for retrieval documents."""

from __future__ import annotations

import logging
import hashlib
import math
import re

from silicon_agents.core.config import get_settings
from silicon_agents.core.schemas import RetrievalDocument


EMBEDDING_DIMENSIONS = 64
EMBEDDING_MODEL = "local-hashing-v1"
logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """Provider abstraction for retrieval embeddings.

    Local hashing is deterministic and available everywhere. Hosted providers
    are best-effort and fall back to local embeddings if credentials or SDK
    calls are unavailable.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.last_provider = "local"
        self.last_model = EMBEDDING_MODEL

    async def embed_text(self, text: str) -> tuple[list[float], str, str]:
        provider = str(self.settings.rag_embedding_provider or "local").strip().lower()
        if provider == "gemini" and self.settings.gemini_api_key:
            try:
                embedding = await self._embed_gemini(text)
                self.last_provider = "gemini"
                self.last_model = self.settings.gemini_embedding_model
                return embedding, self.last_provider, self.last_model
            except Exception as exc:  # pragma: no cover - live provider fallback
                logger.warning("Gemini embedding provider failed: %s", exc)
        embedding = embed_retrieval_text(text)
        self.last_provider = "local"
        self.last_model = EMBEDDING_MODEL
        return embedding, self.last_provider, self.last_model

    async def embed_document(self, document: RetrievalDocument) -> RetrievalDocument:
        text = retrieval_embedding_text(document)
        embedding, provider, model = await self.embed_text(text)
        document.embedding = embedding
        document.metadata["embedding_provider"] = provider
        document.metadata["embedding_model"] = model
        document.metadata["embedding_dimensions"] = len(embedding)
        return document

    async def _embed_gemini(self, text: str) -> list[float]:
        from google import genai  # pragma: no cover
        from google.genai import types  # pragma: no cover

        client = genai.Client(api_key=self.settings.gemini_api_key)
        response = client.models.embed_content(
            model=self.settings.gemini_embedding_model,
            contents=text[:8000],
            config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
        )
        if not response.embeddings:
            raise RuntimeError("Gemini embedding response did not include embeddings.")
        return [float(value) for value in response.embeddings[0].values]


def embed_retrieval_text(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    vector = [0.0] * dimensions
    terms = _terms(text)
    if not terms:
        return vector
    for term in terms:
        digest = hashlib.sha256(term.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [round(value / norm, 6) for value in vector]


def ensure_document_embedding(document: RetrievalDocument) -> RetrievalDocument:
    if document.embedding:
        return document
    document.embedding = embed_retrieval_text(retrieval_embedding_text(document))
    document.metadata["embedding_provider"] = document.metadata.get("embedding_provider") or "local"
    document.metadata["embedding_model"] = document.metadata.get("embedding_model") or EMBEDDING_MODEL
    document.metadata["embedding_dimensions"] = document.metadata.get("embedding_dimensions") or EMBEDDING_DIMENSIONS
    return document


def score_embedding_similarity(query: str, document: RetrievalDocument) -> float:
    query_embedding = embed_retrieval_text(query)
    return cosine_similarity(query_embedding, document.embedding)


def score_embedding_vector(query_embedding: list[float], document: RetrievalDocument) -> float:
    return cosine_similarity(query_embedding, document.embedding)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot = sum(left_value * right_value for left_value, right_value in zip(left, right))
    return round(dot / (left_norm * right_norm), 4)


def retrieval_embedding_text(document: RetrievalDocument) -> str:
    return f"{document.title}\n{document.content}\n{_metadata_text(document.metadata)}"


def pgvector_literal(embedding: list[float]) -> str:
    return "[" + ",".join(str(round(float(value), 8)) for value in embedding) + "]"


def _metadata_text(metadata: dict[str, object]) -> str:
    parts: list[str] = []
    for value in metadata.values():
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, dict):
            parts.extend(str(item) for item in value.values())
        else:
            parts.append(str(value))
    return " ".join(parts)


def _terms(text: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9_]+", str(text).lower()) if len(term) > 2]
