"""Routes for Agent 02 yield analysis."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from silicon_agents.agents.agent02_yield import YieldAgent
from silicon_agents.benchmarks.run_scorecard import evaluate_run_scorecard
from silicon_agents.core.config import get_settings
from silicon_agents.core.schemas import Decision, RunHistoryRecord, YieldBriefRequest, YieldRequest
from silicon_agents.core.streaming import sse_event
from silicon_agents.output.report_html import render_yield_brief
from silicon_agents.storage.feedback_store import FeedbackStore


router = APIRouter(prefix="/api/v1", tags=["yield"])
logger = logging.getLogger(__name__)


@router.post("/yield")
async def analyse_yield(request: YieldRequest) -> StreamingResponse:
    settings = get_settings()
    if len(request.csv_data) > settings.max_csv_chars:
        raise HTTPException(status_code=400, detail="CSV input exceeds configured size limit.")

    logger.info(
        "Agent02 yield request accepted project=%s mode=%s artifact=%s chars=%s",
        request.project_id,
        request.mode,
        request.artifact_name or "",
        len(request.csv_data),
    )
    agent = YieldAgent()
    store = FeedbackStore(settings.db_path)
    await store.init()

    async def generator():
        run_id = f"run-{uuid4().hex[:12]}"
        started_at = datetime.now(timezone.utc)
        started_perf = perf_counter()
        decisions = []
        analysis_log: list[str] = []
        orchestration: dict[str, object] = {}
        done_payload: dict[str, object] = {}
        error_message: str | None = None
        status = "completed"
        logger.info("Agent02 stream started run=%s project=%s", run_id, request.project_id)
        retrieval_documents = await store.search_retrieval_documents(
            project_id=request.project_id,
            agent="agent02",
            mode=request.mode,
            run_profile_id=request.run_profile_id,
            query=_retrieval_query(request),
            limit=4,
        )
        enriched_request = _request_with_retrieved_context(request, retrieval_documents)
        try:
            async for event_type, payload in agent.stream(enriched_request):
                if event_type == "decision":
                    if retrieval_documents:
                        payload = _decision_with_retrieval_sources(payload, retrieval_documents)
                    decisions.append(Decision(**payload))
                elif event_type == "chunk":
                    text = str(payload.get("text", "")).strip()
                    if text:
                        analysis_log.append(text)
                elif event_type == "orchestration":
                    payload = {
                        **payload,
                        "retrieval": _retrieval_observability(retrieval_documents),
                    }
                    orchestration = payload
                elif event_type == "done":
                    payload = dict(payload)
                    payload["run_id"] = run_id
                    if agent.llm.last_model:
                        payload["model"] = agent.llm.last_model
                    done_payload = payload
                yield sse_event(event_type, payload)
        except Exception as exc:
            status = "failed"
            error_message = str(exc)
            yield sse_event("error", {"message": error_message, "run_id": run_id})
        finally:
            completed_at = datetime.now(timezone.utc)
            duration_ms = int((perf_counter() - started_perf) * 1000)
            provider = str(done_payload.get("provider") or agent.llm.last_provider or "mock")
            model = agent.llm.last_model or None
            total_decisions = int(done_payload.get("total_decisions", len(decisions)))
            high = int(done_payload.get("high", sum(1 for decision in decisions if decision.priority == "HIGH")))
            medium = int(done_payload.get("medium", sum(1 for decision in decisions if decision.priority == "MEDIUM")))
            low = int(done_payload.get("low", sum(1 for decision in decisions if decision.priority == "LOW")))
            if decisions:
                await store.save_decisions(decisions)
            scorecard = evaluate_run_scorecard("agent02", request.artifact_name, decisions)
            record = RunHistoryRecord(
                run_id=run_id,
                project_id=request.project_id,
                agent="agent02",
                mode=request.mode,
                status=status,
                provider=provider,
                model=model,
                artifact_name=request.artifact_name,
                artifact_source=request.artifact_source,
                raw_artifact=request.csv_data,
                runtime_label=request.lot_id,
                run_profile_id=request.run_profile_id,
                run_profile_name=request.run_profile_name,
                chip_type=request.chip_type,
                client_profile=request.client_profile,
                parser_format=agent.last_parser_format,
                parser_confidence=agent.last_parser_confidence,
                parser_warnings=list(agent.last_parser_warnings),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                total_decisions=total_decisions,
                high=high,
                medium=medium,
                low=low,
                request_payload=_yield_request_snapshot(request),
                orchestration=orchestration,
                analysis_log=analysis_log,
                decisions=decisions,
                observability={
                    "artifact_chars": len(request.csv_data),
                    "analysis_events": len(analysis_log),
                    "decision_count": len(decisions),
                    "provider_family": provider.split("/")[0] if provider else "mock",
                    "runtime_label": request.lot_id,
                    "retrieval_document_count": len(retrieval_documents),
                    "llm": {
                        "provider": agent.llm.last_provider,
                        "model": agent.llm.last_model,
                        "attempts": list(agent.llm.provider_attempts),
                        "fallback_reason": agent.llm.fallback_reason,
                    },
                },
                benchmark_title=str(scorecard["title"]),
                benchmark_score=str(scorecard["score"]),
                benchmark_notes=list(scorecard["notes"]),
                scorecard_mode=str(scorecard["mode"]),
                error_message=error_message,
            )
            await store.save_run_history(record)
            logger.info(
                "Saved run %s agent=%s project=%s mode=%s provider=%s model=%s duration_ms=%s decisions=%s status=%s artifact=%s",
                run_id,
                "agent02",
                request.project_id,
                request.mode,
                provider,
                model or "",
                duration_ms,
                len(decisions),
                status,
                request.artifact_name or "",
            )

    return StreamingResponse(generator(), media_type="text/event-stream")


@router.post("/yield/export/html")
async def export_yield_brief(request: YieldBriefRequest) -> HTMLResponse:
    html = render_yield_brief(request)
    headers = {
        "Content-Disposition": f'attachment; filename="{request.project_id}-yield-brief.html"'
    }
    return HTMLResponse(content=html, headers=headers)


def _yield_request_snapshot(request: YieldRequest) -> dict[str, object]:
    payload = request.model_dump()
    csv_data = payload.pop("csv_data", "")
    payload["csv_data_excerpt"] = str(csv_data)[:4000]
    payload["csv_data_chars"] = len(str(csv_data))
    return payload


def _retrieval_query(request: YieldRequest) -> str:
    return "\n".join(
        part
        for part in [
            request.lot_id,
            request.mode,
            request.chip_type or "",
            request.context or "",
            request.custom_instructions or "",
            request.csv_data[:2500],
        ]
        if part
    )


def _request_with_retrieved_context(request: YieldRequest, documents: list) -> YieldRequest:
    if not documents:
        return request
    retrieved_context = "\n\n".join(
        f"[{index}] {document.title}\n{document.content[:1200]}"
        for index, document in enumerate(documents, start=1)
    )
    existing = request.reference_data or ""
    label = request.reference_data_label or "retrieved yield history"
    return request.model_copy(
        update={
            "reference_data": f"{existing}\n\nRetrieved prior yield evidence:\n{retrieved_context}".strip(),
            "reference_data_label": label,
        }
    )


def _decision_with_retrieval_sources(payload: dict, documents: list) -> dict:
    metadata = dict(payload.get("metadata") or {})
    metadata["retrieved_sources"] = [
        {
            "id": document.id,
            "source_id": document.source_id,
            "title": document.title,
            "score": document.score,
            "document_kind": document.metadata.get("document_kind"),
        }
        for document in documents
    ]
    metadata["retrieval_augmented"] = True
    return {**payload, "metadata": metadata}


def _retrieval_observability(documents: list) -> dict[str, object]:
    return {
        "enabled": True,
        "document_count": len(documents),
        "sources": [
            {
                "id": document.id,
                "source_id": document.source_id,
                "title": document.title,
                "source_type": document.source_type,
                "document_kind": document.metadata.get("document_kind"),
                "score": document.score,
                "content_excerpt": document.content[:700],
            }
            for document in documents
        ],
    }
