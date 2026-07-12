"""Debug routes for local pilot diagnostics."""

from __future__ import annotations

from fastapi import APIRouter

from silicon_agents.core.config import get_settings
from silicon_agents.core.llm import LLMProvider


router = APIRouter(prefix="/api/v1/debug", tags=["debug"])


@router.get("/llm")
async def llm_debug_config() -> dict[str, object]:
    settings = get_settings()
    llm = LLMProvider()
    return {
        "llm_primary": settings.llm_primary,
        "gemini_api_key_present": bool(settings.gemini_api_key),
        "gemini_model": settings.gemini_model,
        "gemini_fallback_model": settings.gemini_fallback_model,
        "gemini_models_in_order": llm._gemini_models(),
        "openai_api_key_present": bool(settings.openai_api_key),
        "openai_model": settings.openai_model,
        "sarvam_api_key_present": bool(settings.sarvam_api_key),
        "sarvam_model": settings.sarvam_model,
        "sarvam_base_url": settings.sarvam_base_url,
        "provider_order": llm._provider_order(),
        "rag_embedding_provider": settings.rag_embedding_provider,
        "gemini_embedding_model": settings.gemini_embedding_model,
        "rag_vector_backend": settings.rag_vector_backend,
    }


@router.post("/llm/smoke")
async def llm_smoke() -> dict[str, object]:
    llm = LLMProvider()
    raw = ""
    async for chunk in llm.stream(
        "Return JSON only.",
        'Return {"ok": true, "source": "live"}.',
        '{"ok": false, "source": "mock"}',
        response_mime_type="application/json",
    ):
        raw += chunk
    return {
        "provider": llm.last_provider,
        "model": llm.last_model,
        "fallback_reason": llm.fallback_reason,
        "attempts": llm.provider_attempts,
        "raw_response": raw[:1000],
    }
