"""Document ingestion helpers for retrieval-ready manual notes."""

from __future__ import annotations

import re
from datetime import datetime

from silicon_agents.core.schemas import ManualNoteIngestRequest, RetrievalDocument


MAX_CHUNK_CHARS = 1200
CHUNK_OVERLAP_CHARS = 180


def build_manual_note_documents(
    request: ManualNoteIngestRequest,
    source_id: str,
    created_at: datetime,
) -> list[RetrievalDocument]:
    """Chunk a sanitized engineering note into filterable retrieval documents."""
    chunks = chunk_text(request.content)
    metadata = {
        **request.metadata,
        "document_kind": "manual_note",
        "source_title": request.title,
        "run_profile_id": request.run_profile_id or "",
        "run_profile_name": request.run_profile_name or "",
        "chip_type": request.chip_type or "",
        "client_profile": request.client_profile or "",
        "tags": list(request.tags),
    }
    return [
        RetrievalDocument(
            id=f"{source_id}:chunk:{index:03d}",
            project_id=request.project_id,
            agent=request.agent,
            mode=request.mode,
            source_type="manual_note",
            source_id=source_id,
            title=f"{request.title} · chunk {index}",
            content=chunk,
            metadata={
                **metadata,
                "chunk_index": index,
                "chunk_count": len(chunks),
            },
            created_at=created_at,
        )
        for index, chunk in enumerate(chunks, start=1)
    ]


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS, overlap_chars: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    paragraphs = re.split(r"\n{2,}", normalized)
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            chunks.extend(_split_long_paragraph(paragraph, max_chars, overlap_chars))
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        chunks.append(current.strip())
        overlap = current[-overlap_chars:].strip() if overlap_chars else ""
        current = f"{overlap}\n\n{paragraph}".strip() if overlap else paragraph
    if current:
        chunks.append(current.strip())
    return chunks


def _split_long_paragraph(paragraph: str, max_chars: int, overlap_chars: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    while start < len(paragraph):
        end = min(len(paragraph), start + max_chars)
        if end < len(paragraph):
            split_at = paragraph.rfind(" ", start, end)
            if split_at > start + max_chars // 2:
                end = split_at
        chunks.append(paragraph[start:end].strip())
        if end >= len(paragraph):
            break
        start = max(0, end - overlap_chars)
    return [chunk for chunk in chunks if chunk]


def _normalize_text(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in str(text or "").splitlines()]
    compact = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", compact).strip()
