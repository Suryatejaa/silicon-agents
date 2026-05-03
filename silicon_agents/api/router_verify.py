"""Routes for Agent 01 verification."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from silicon_agents.agents.agent01_verify import VerificationAgent
from silicon_agents.benchmarks.run_scorecard import evaluate_run_scorecard
from silicon_agents.core.config import get_settings
from silicon_agents.core.schemas import Decision, RunHistoryRecord, VerificationBriefRequest, VerifyRequest
from silicon_agents.core.streaming import sse_event
from silicon_agents.output.report_html import render_verification_brief
from silicon_agents.storage.feedback_store import FeedbackStore


router = APIRouter(prefix="/api/v1", tags=["verification"])
logger = logging.getLogger(__name__)


@router.post("/verify")
async def verify(request: VerifyRequest) -> StreamingResponse:
    settings = get_settings()
    if len(request.report_text) > settings.max_report_chars:
        raise HTTPException(status_code=400, detail="Report exceeds configured size limit.")

    agent = VerificationAgent()
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
        try:
            async for event_type, payload in agent.stream(request):
                if event_type == "decision":
                    decisions.append(Decision(**payload))
                elif event_type == "chunk":
                    text = str(payload.get("text", "")).strip()
                    if text:
                        analysis_log.append(text)
                elif event_type == "orchestration":
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
            scorecard = evaluate_run_scorecard("agent01", request.artifact_name, decisions)
            record = RunHistoryRecord(
                run_id=run_id,
                project_id=request.project_id,
                agent="agent01",
                mode=request.mode,
                status=status,
                provider=provider,
                model=model,
                artifact_name=request.artifact_name,
                runtime_label=request.design_name,
                run_profile_id=request.run_profile_id,
                run_profile_name=request.run_profile_name,
                chip_type=request.chip_type,
                client_profile=request.client_profile,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                total_decisions=total_decisions,
                high=high,
                medium=medium,
                low=low,
                request_payload=_verification_request_snapshot(request),
                orchestration=orchestration,
                analysis_log=analysis_log,
                decisions=decisions,
                observability={
                    "artifact_chars": len(request.report_text),
                    "analysis_events": len(analysis_log),
                    "decision_count": len(decisions),
                    "provider_family": provider.split("/")[0] if provider else "mock",
                    "runtime_label": request.design_name,
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
                "agent01",
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


@router.post("/verify/export/html")
async def export_verification_brief(request: VerificationBriefRequest) -> HTMLResponse:
    html = render_verification_brief(request)
    headers = {
        "Content-Disposition": f'attachment; filename="{request.project_id}-verification-brief.html"'
    }
    return HTMLResponse(content=html, headers=headers)


def _verification_request_snapshot(request: VerifyRequest) -> dict[str, object]:
    payload = request.model_dump()
    report_text = payload.pop("report_text", "")
    payload["report_text_excerpt"] = str(report_text)[:4000]
    payload["report_text_chars"] = len(str(report_text))
    return payload
