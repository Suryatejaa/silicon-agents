"""Provider abstraction for streamed reasoning."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator

from silicon_agents.core.config import get_settings


logger = logging.getLogger(__name__)


class LLMProvider:
    """Single interface for all agent callers.

    For this MVP scaffold we support a practical local-first behavior:
    - if live provider keys and SDKs are available, try Gemini then OpenAI
    - otherwise stream deterministic local text so the demo still works
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.last_provider = "mock"
        self.last_model = ""
        self.provider_attempts: list[dict[str, str]] = []
        self.fallback_reason = ""

    async def stream(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_text: str,
        response_mime_type: str = "application/json",
    ) -> AsyncIterator[str]:
        self.provider_attempts = []
        self.fallback_reason = ""
        self.last_provider = "mock"
        self.last_model = ""
        providers = self._provider_order()
        for provider in providers:
            if not self._provider_enabled(provider):
                self.provider_attempts.append({"provider": provider, "status": "disabled", "reason": "missing_api_key_or_unknown_provider"})
                logger.info("LLM provider %s disabled or not configured.", provider)
                continue
            try:
                async for chunk in self._stream_provider(provider, system_prompt, user_prompt, response_mime_type):
                    yield chunk
                return
            except Exception as exc:  # pragma: no cover - best effort live fallback
                self.provider_attempts.append({"provider": provider, "status": "failed", "reason": str(exc)[:1000]})
                logger.exception(
                    "Provider %s failed: type=%s repr=%r",
                    provider,
                    type(exc).__name__,
                    exc,
                )
        self.last_provider = "mock"
        self.fallback_reason = "all_configured_providers_failed_or_disabled"
        logger.error("LLM falling back to mock. Attempts=%s", self.provider_attempts)
        async for chunk in self._stream_mock(fallback_text):
            yield chunk

    def _provider_enabled(self, provider: str) -> bool:
        if provider == "gemini":
            return bool(self.settings.gemini_api_key)
        if provider == "openai":
            return bool(self.settings.openai_api_key)
        if provider == "sarvam":
            return bool(self.settings.sarvam_api_key)
        return False

    def _provider_order(self) -> list[str]:
        providers: list[str] = []
        for provider in [self.settings.llm_primary, "gemini", "sarvam", "openai"]:
            cleaned = str(provider or "").strip().lower()
            if cleaned and cleaned not in providers:
                providers.append(cleaned)
        return providers

    async def _stream_provider(self, provider: str, system_prompt: str, user_prompt: str, response_mime_type: str) -> AsyncIterator[str]:
        if provider == "gemini":
            async for chunk in self._stream_gemini(system_prompt, user_prompt, response_mime_type):
                yield chunk
            return
        if provider == "openai":
            async for chunk in self._stream_openai(system_prompt, user_prompt):
                yield chunk
            return
        if provider == "sarvam":
            async for chunk in self._stream_sarvam(system_prompt, user_prompt):
                yield chunk
            return
        raise RuntimeError(f"Unknown provider: {provider}")

    async def _stream_mock(self, fallback_text: str) -> AsyncIterator[str]:
        parts = [part.strip() for part in fallback_text.split("\n") if part.strip()]
        for part in parts:
            await asyncio.sleep(0)
            yield f"{part}\n"

    async def _stream_gemini(self, system_prompt: str, user_prompt: str, response_mime_type: str) -> AsyncIterator[str]:
        from google import genai  # pragma: no cover
        from google.genai import types  # pragma: no cover

        client = genai.Client(api_key=self.settings.gemini_api_key)
        last_error: Exception | None = None
        for model in self._gemini_models():
            try:
                response = client.models.generate_content_stream(
                    model=model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.2,
                        response_mime_type=response_mime_type,
                    ),
                )
                emitted = False
                for chunk in response:
                    text = getattr(chunk, "text", None)
                    if text:
                        emitted = True
                        self.last_provider = f"gemini/{model}"
                        self.last_model = model
                        yield text
                        await asyncio.sleep(0)
                if emitted:
                    self.provider_attempts.append({"provider": "gemini", "model": model, "status": "success"})
                    logger.info("Gemini model %s succeeded.", model)
                    return
            except Exception as exc:
                last_error = exc
                self.provider_attempts.append({"provider": "gemini", "model": model, "status": "failed", "reason": str(exc)[:1000]})
                logger.warning("Gemini model %s failed: %s", model, exc)
        if last_error:
            raise last_error
        raise RuntimeError("No Gemini models configured.")

    def _gemini_models(self) -> list[str]:
        models: list[str] = []
        for model in [self.settings.gemini_model, self.settings.gemini_fallback_model]:
            cleaned = str(model or "").strip()
            if cleaned and cleaned not in models:
                models.append(cleaned)
        return models

    async def _stream_openai(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        from openai import AsyncOpenAI  # pragma: no cover

        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        stream = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )
        async for event in stream:
            delta = event.choices[0].delta.content if event.choices else None
            if delta:
                self.last_provider = f"openai/{self.settings.openai_model}"
                self.last_model = self.settings.openai_model
                yield delta
        self.provider_attempts.append({"provider": "openai", "model": self.settings.openai_model, "status": "success"})

    async def _stream_sarvam(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        # Use the official Sarvam SDK to handle transport and streaming quirks.
        from sarvamai import SarvamAI  # pragma: no cover

        client = SarvamAI(api_subscription_key=self.settings.sarvam_api_key)

        # Run the SDK call on a thread to avoid blocking the event loop; the SDK
        # returns a synchronous iterator that yields stream events.
        stream = await asyncio.to_thread(
            client.chat.completions,
            model=self.settings.sarvam_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            top_p=1,
            max_tokens=4000,
            reasoning_effort=None,
            stream=True,
        )

        def _next_chunk(iterator):
            try:
                return next(iterator)
            except StopIteration:
                return None

        emitted = False
        while True:
            event = await asyncio.to_thread(_next_chunk, stream)
            if event is None:
                break

            choices = getattr(event, "choices", None) or []
            if not choices:
                continue

            delta = getattr(choices[0], "delta", None)
            text = getattr(delta, "content", None) if delta else None
            if text:
                emitted = True
                self.last_provider = f"sarvam/{self.settings.sarvam_model}"
                self.last_model = self.settings.sarvam_model
                yield str(text)
                await asyncio.sleep(0)

        if emitted:
            self.provider_attempts.append({"provider": "sarvam", "model": self.settings.sarvam_model, "status": "success"})
            logger.info("Sarvam model %s succeeded.", self.settings.sarvam_model)
            return

        raise RuntimeError("Sarvam SDK stream completed without text output.")
