"""Routes for persisted enterprise configuration."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from silicon_agents.core.config import get_settings
from silicon_agents.core.schemas import Agent01EnterpriseConfig, Agent02EnterpriseConfig, EnterpriseConfigEnvelope
from silicon_agents.storage.feedback_store import FeedbackStore


router = APIRouter(prefix="/api/v1/config", tags=["configuration"])


async def _store() -> FeedbackStore:
    store = FeedbackStore(get_settings().db_path)
    await store.init()
    return store


@router.get("/agent01", response_model=EnterpriseConfigEnvelope)
async def get_agent01_config() -> EnterpriseConfigEnvelope:
    store = await _store()
    payload = await store.get_enterprise_config("agent01")
    return EnterpriseConfigEnvelope(agent="agent01", config=Agent01EnterpriseConfig(**payload))


@router.put("/agent01", response_model=EnterpriseConfigEnvelope)
async def save_agent01_config(request: Agent01EnterpriseConfig) -> EnterpriseConfigEnvelope:
    store = await _store()
    payload = request.model_dump()
    await store.save_enterprise_config("agent01", payload)
    return EnterpriseConfigEnvelope(agent="agent01", config=Agent01EnterpriseConfig(**payload))


@router.get("/agent02", response_model=EnterpriseConfigEnvelope)
async def get_agent02_config() -> EnterpriseConfigEnvelope:
    store = await _store()
    payload = await store.get_enterprise_config("agent02")
    return EnterpriseConfigEnvelope(agent="agent02", config=Agent02EnterpriseConfig(**payload))


@router.put("/agent02", response_model=EnterpriseConfigEnvelope)
async def save_agent02_config(request: Agent02EnterpriseConfig) -> EnterpriseConfigEnvelope:
    store = await _store()
    payload = request.model_dump()
    await store.save_enterprise_config("agent02", payload)
    return EnterpriseConfigEnvelope(agent="agent02", config=Agent02EnterpriseConfig(**payload))


@router.get("/{agent}")
async def get_unknown_agent(agent: str) -> None:
    raise HTTPException(status_code=404, detail=f"Unsupported config agent: {agent}")
