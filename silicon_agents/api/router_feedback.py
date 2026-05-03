"""Routes for feedback, stored decisions, and run history."""

from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException

from silicon_agents.core.config import get_settings
from silicon_agents.core.schemas import (
    DecisionListResponse,
    FeedbackListResponse,
    FeedbackRequest,
    PilotAccessCodeResponse,
    PilotMetricsResponse,
    RunHistoryListResponse,
    RunHistoryRecord,
    StructuredExportResponse,
)
from silicon_agents.output.report_structured import build_email_export, build_jira_export
from silicon_agents.storage.feedback_store import FeedbackStore


router = APIRouter(prefix="/api/v1", tags=["feedback"])


@router.post("/feedback")
async def save_feedback(request: FeedbackRequest) -> dict[str, object]:
    store = FeedbackStore(get_settings().db_path)
    await store.init()
    await store.record_feedback(
        decision_id=request.decision_id,
        project_id=request.project_id,
        accepted=request.accepted,
        notes=request.notes,
        engineer_id=request.engineer_id,
        run_id=request.run_id or "",
    )
    return {"saved": True, "decision_id": request.decision_id}


@router.get("/feedback/{project_id}", response_model=FeedbackListResponse)
async def get_feedback(project_id: str) -> FeedbackListResponse:
    store = FeedbackStore(get_settings().db_path)
    await store.init()
    return FeedbackListResponse(project_id=project_id, feedback=await store.get_feedback(project_id))


@router.get("/decisions/{project_id}", response_model=DecisionListResponse)
async def get_decisions(project_id: str) -> DecisionListResponse:
    store = FeedbackStore(get_settings().db_path)
    await store.init()
    return DecisionListResponse(project_id=project_id, decisions=await store.get_decisions(project_id))


@router.get("/runs", response_model=RunHistoryListResponse)
async def get_run_history(
    project_id: Optional[str] = None,
    agent: Optional[str] = None,
    limit: int = 25,
) -> RunHistoryListResponse:
    store = FeedbackStore(get_settings().db_path)
    await store.init()
    clamped_limit = max(1, min(limit, 200))
    runs = await store.get_run_history(project_id=project_id, agent=agent, limit=clamped_limit)
    return RunHistoryListResponse(runs=runs)


@router.get("/runs/{run_id}", response_model=RunHistoryRecord)
async def get_run(run_id: str) -> RunHistoryRecord:
    store = FeedbackStore(get_settings().db_path)
    await store.init()
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return run


@router.get("/pilot/metrics", response_model=PilotMetricsResponse)
async def get_pilot_metrics() -> PilotMetricsResponse:
    settings = get_settings()
    store = FeedbackStore(settings.db_path)
    await store.init()
    return await store.get_pilot_metrics(access_enabled=bool(settings.pilot_access_token))


@router.post("/pilot/access-code/generate", response_model=PilotAccessCodeResponse)
async def generate_pilot_access_code() -> PilotAccessCodeResponse:
    code = secrets.token_urlsafe(18)
    return PilotAccessCodeResponse(
        code=code,
        bearer_example=f"X-Pilot-Access-Token: {code}",
        curl_example=f"curl -H 'X-Pilot-Access-Token: {code}' http://127.0.0.1:8000/api/v1/pilot/metrics",
        note="Generated codes are suggestions for pilot sharing. Set PILOT_ACCESS_TOKEN in the deployment environment to activate one.",
    )


@router.get("/runs/{run_id}/export/{target}", response_model=StructuredExportResponse)
async def export_run(run_id: str, target: str) -> StructuredExportResponse:
    store = FeedbackStore(get_settings().db_path)
    await store.init()
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    if target == "jira":
        export = build_jira_export(run)
        await store.record_export(run_id, "jira", export.title, export.filename)
        return export
    if target == "email":
        export = build_email_export(run)
        await store.record_export(run_id, "email", export.title, export.filename)
        return export
    raise HTTPException(status_code=400, detail="Unsupported export target.")
