"""Build retrieval-ready documents from saved run history."""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from silicon_agents.core.schemas import Decision, RetrievalDocument, RunHistoryRecord


def build_run_retrieval_documents(record: RunHistoryRecord) -> list[RetrievalDocument]:
    """Convert a completed run into small, filterable retrieval documents."""
    if record.status != "completed":
        return []

    created_at = record.completed_at
    metadata = _base_metadata(record)
    documents = [
        RetrievalDocument(
            id=f"{record.run_id}:summary",
            project_id=record.project_id,
            agent=record.agent,
            mode=record.mode,
            source_type="run_history",
            source_id=record.run_id,
            title=_summary_title(record),
            content=_summary_content(record),
            metadata={**metadata, "document_kind": "run_summary"},
            created_at=created_at,
        )
    ]
    for index, decision in enumerate(record.decisions, start=1):
        documents.append(_decision_document(record, decision, index, created_at, metadata))
    return documents


def score_retrieval_document(query: str, document: RetrievalDocument) -> float:
    query_terms = _terms(query)
    if not query_terms:
        return 0.0
    haystack = _terms(f"{document.title} {document.content} {' '.join(str(v) for v in document.metadata.values())}")
    counts = Counter(haystack)
    if not counts:
        return 0.0
    matches = sum(counts[term] for term in query_terms)
    unique_matches = len(set(query_terms) & set(counts))
    coverage = unique_matches / max(1, len(set(query_terms)))
    density = matches / max(12, len(haystack))
    return round(coverage + density, 4)


def _decision_document(
    record: RunHistoryRecord,
    decision: Decision,
    index: int,
    created_at: datetime,
    base_metadata: dict[str, object],
) -> RetrievalDocument:
    evidence = str(decision.metadata.get("evidence", "")).strip()
    rank_basis = str(decision.metadata.get("rank_basis", "")).strip()
    content_parts = [
        f"Target: {decision.target}",
        f"Action: {decision.action}",
        f"Rationale: {decision.rationale}",
        f"Priority: {decision.priority}",
        f"Confidence: {decision.confidence}",
    ]
    if evidence:
        content_parts.append(f"Current evidence: {evidence}")
    if rank_basis:
        content_parts.append(f"Rank basis: {rank_basis}")
    return RetrievalDocument(
        id=f"{record.run_id}:decision:{decision.id or index}",
        project_id=record.project_id,
        agent=record.agent,
        mode=record.mode,
        source_type="run_history",
        source_id=record.run_id,
        title=f"{record.runtime_label or record.project_id} · {decision.target}",
        content="\n".join(content_parts),
        metadata={
            **base_metadata,
            "document_kind": "decision",
            "decision_id": decision.id,
            "decision_type": decision.type,
            "target": decision.target,
            "priority": decision.priority,
            "evidence": evidence,
        },
        created_at=created_at,
    )


def _summary_title(record: RunHistoryRecord) -> str:
    label = record.runtime_label or record.run_profile_name or record.project_id
    return f"{label} · {record.agent} {record.mode} run summary"


def _summary_content(record: RunHistoryRecord) -> str:
    top_targets = ", ".join(decision.target for decision in record.decisions[:5]) or "No decisions"
    analysis = "\n".join(record.analysis_log[:4])
    return "\n".join(
        [
            f"Run: {record.run_id}",
            f"Workflow: {record.agent} {record.mode}",
            f"Artifact: {record.artifact_name or 'Unknown artifact'}",
            f"Profile: {record.run_profile_name or record.run_profile_id or 'Custom run'}",
            f"Chip type: {record.chip_type or 'Unknown'}",
            f"Decision counts: high={record.high}, medium={record.medium}, low={record.low}",
            f"Top targets: {top_targets}",
            f"Analysis notes: {analysis or 'No analysis log captured.'}",
        ]
    )


def _base_metadata(record: RunHistoryRecord) -> dict[str, object]:
    return {
        "run_id": record.run_id,
        "artifact_name": record.artifact_name or "",
        "artifact_source": record.artifact_source or "unknown",
        "runtime_label": record.runtime_label or "",
        "run_profile_id": record.run_profile_id or "",
        "run_profile_name": record.run_profile_name or "",
        "chip_type": record.chip_type or "",
        "client_profile": record.client_profile or "",
        "parser_format": record.parser_format or "",
        "parser_confidence": record.parser_confidence or 0.0,
        "benchmark_title": record.benchmark_title or "",
        "benchmark_score": record.benchmark_score or "",
    }


def _terms(text: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9_]+", text.lower()) if len(term) > 2]
