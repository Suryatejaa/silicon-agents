"""Routes for retrieval-ready RAG context."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from silicon_agents.core.config import get_settings
from silicon_agents.core.schemas import (
    ManualNoteIngestRequest,
    ManualNoteIngestResponse,
    RetrievalReindexRequest,
    RetrievalReindexResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from silicon_agents.rag.documents import build_manual_note_documents
from silicon_agents.rag.embeddings import EmbeddingProvider
from silicon_agents.storage.feedback_store import FeedbackStore


router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


@router.post("/search", response_model=RetrievalSearchResponse)
async def search_retrieval_documents(request: RetrievalSearchRequest) -> RetrievalSearchResponse:
    settings = get_settings()
    store = FeedbackStore(settings.db_path)
    await store.init()
    documents = await store.search_retrieval_documents(
        project_id=request.project_id,
        query=request.query,
        agent=request.agent,
        mode=request.mode,
        run_profile_id=request.run_profile_id,
        source_type=request.source_type,
        limit=request.limit,
    )
    return RetrievalSearchResponse(documents=documents)


@router.post("/ingest-note", response_model=ManualNoteIngestResponse)
async def ingest_manual_note(request: ManualNoteIngestRequest) -> ManualNoteIngestResponse:
    settings = get_settings()
    store = FeedbackStore(settings.db_path)
    await store.init()
    source_id = request.source_id or f"note-{uuid4().hex[:12]}"
    documents = build_manual_note_documents(
        request=request,
        source_id=source_id,
        created_at=datetime.now(timezone.utc),
    )
    embedder = EmbeddingProvider()
    documents = [await embedder.embed_document(document) for document in documents]
    await store.save_retrieval_documents(documents)
    return ManualNoteIngestResponse(
        source_id=source_id,
        document_count=len(documents),
        documents=documents,
    )


@router.post("/reindex", response_model=RetrievalReindexResponse)
async def reindex_retrieval_documents(request: RetrievalReindexRequest) -> RetrievalReindexResponse:
    settings = get_settings()
    store = FeedbackStore(settings.db_path)
    await store.init()
    documents = await store.get_retrieval_documents(
        project_id=request.project_id,
        agent=request.agent,
        mode=request.mode,
        source_type=request.source_type,
        source_id=request.source_id,
        limit=request.limit,
    )
    embedder = EmbeddingProvider()
    reindexed = [await embedder.embed_document(document) for document in documents]
    await store.save_retrieval_documents(reindexed)
    return RetrievalReindexResponse(
        document_count=len(reindexed),
        embedding_provider=embedder.last_provider,
        embedding_model=embedder.last_model,
        documents=reindexed,
    )
