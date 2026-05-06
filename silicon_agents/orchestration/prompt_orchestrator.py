"""Enterprise prompt orchestration for multi-stage agent runs."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from silicon_agents.core.llm import LLMProvider


ORCHESTRATOR_SYSTEM_PROMPT = """
You are the Silicon Agents orchestration layer for enterprise semiconductor workflows.
Your job is to transform client-specific chip context, historical data, and operating instructions into a compact prompt plan for a downstream analysis agent.

Rules:
- preserve the user's intent and domain constraints
- prioritize only instructions and reference data that materially affect analysis
- never invent client processes, thresholds, or design context
- output valid JSON only
""".strip()
logger = logging.getLogger(__name__)


class PromptOrchestrator:
    """Build run-specific prompt plans before the analysis call."""

    def __init__(self) -> None:
        self.llm = LLMProvider()
        self.last_provider = "mock"
        self.last_diagnostics: dict[str, Any] = {}

    async def build_plan(
        self,
        *,
        domain_label: str,
        task_label: str,
        runtime_label: str | None,
        chip_type: str | None,
        client_profile: str | None,
        custom_instructions: str | None,
        reference_data: str | None,
        reference_data_label: str | None,
        context: str | None,
        parsed_summary: dict[str, Any],
    ) -> dict[str, Any]:
        fallback = self._fallback_plan(
            domain_label=domain_label,
            task_label=task_label,
            runtime_label=runtime_label,
            chip_type=chip_type,
            client_profile=client_profile,
            custom_instructions=custom_instructions,
            reference_data=reference_data,
            reference_data_label=reference_data_label,
            context=context,
        )
        prompt = (
            "Return a JSON object with keys chip_focus, instruction_overrides, reference_priorities, analysis_directives, output_emphasis, prompt_addendum.\n"
            "chip_focus and output_emphasis are strings.\n"
            "instruction_overrides, reference_priorities, and analysis_directives are arrays of 2 to 5 short strings.\n"
            "prompt_addendum is a compact paragraph the downstream analysis LLM should obey.\n"
            f"Domain: {domain_label}\n"
            f"Task: {task_label}\n"
            f"Runtime focus label: {runtime_label or 'Not provided'}\n"
            f"Chip type: {chip_type or 'Unknown'}\n"
            f"Client profile: {client_profile or 'Not provided'}\n"
            f"Custom instructions: {custom_instructions or 'Not provided'}\n"
            f"Reference data label: {reference_data_label or 'Not provided'}\n"
            f"Reference data excerpt: {(reference_data or 'Not provided')[:5000]}\n"
            f"Run context: {context or 'Not provided'}\n"
            f"Parsed summary: {json.dumps(parsed_summary)}\n"
            "If runtime focus conflicts with saved chip profile naming, prefer the current artifact/runtime label while preserving workflow style.\n"
        )
        raw = ""
        try:
            async for chunk in self.llm.stream(
                ORCHESTRATOR_SYSTEM_PROMPT,
                prompt,
                json.dumps(fallback),
                response_mime_type="application/json",
            ):
                raw += chunk
            if self.llm.last_provider == "mock":
                self.last_provider = "mock"
                self.last_diagnostics = self._llm_diagnostics("provider_fallback", raw)
                fallback["llm_diagnostics"] = self.last_diagnostics
                return fallback
            plan = self._extract_json(raw)
            self.last_provider = self.llm.last_provider
            self.last_diagnostics = self._llm_diagnostics("live_json", raw)
            return {
                "chip_focus": str(plan.get("chip_focus", fallback["chip_focus"])),
                "instruction_overrides": self._as_list(plan.get("instruction_overrides"), fallback["instruction_overrides"]),
                "reference_priorities": self._as_list(plan.get("reference_priorities"), fallback["reference_priorities"]),
                "analysis_directives": self._as_list(plan.get("analysis_directives"), fallback["analysis_directives"]),
                "output_emphasis": str(plan.get("output_emphasis", fallback["output_emphasis"])),
                "prompt_addendum": str(plan.get("prompt_addendum", fallback["prompt_addendum"])),
                "llm_diagnostics": self.last_diagnostics,
            }
        except Exception as exc:
            logger.warning(
                "Orchestration LLM fell back provider=%s model=%s error=%s raw_head=%r attempts=%s",
                self.llm.last_provider,
                self.llm.last_model,
                exc,
                raw[:500],
                self.llm.provider_attempts,
            )
            self.last_provider = "mock"
            self.last_diagnostics = self._llm_diagnostics(f"parse_or_provider_fallback: {exc}", raw)
            fallback["llm_diagnostics"] = self.last_diagnostics
            return fallback

    def _llm_diagnostics(self, reason: str, raw: str = "") -> dict[str, Any]:
        return {
            "provider": self.llm.last_provider,
            "model": self.llm.last_model,
            "attempts": list(self.llm.provider_attempts),
            "fallback_reason": self.llm.fallback_reason or reason,
            "raw_response_chars": len(raw or ""),
            "raw_response_excerpt": (raw or "")[:500],
        }

    def _fallback_plan(
        self,
        *,
        domain_label: str,
        task_label: str,
        runtime_label: str | None,
        chip_type: str | None,
        client_profile: str | None,
        custom_instructions: str | None,
        reference_data: str | None,
        reference_data_label: str | None,
        context: str | None,
    ) -> dict[str, Any]:
        instruction_overrides = [
            "Ground every finding in the parsed artifact before using historical hints.",
            "Respect client review style and keep recommendations human-approvable.",
        ]
        if custom_instructions:
            instruction_overrides.append(custom_instructions[:180])
        reference_priorities = [
            f"Use {reference_data_label or 'reference data'} only to shape hypotheses, not to replace current-run evidence.",
            "Prefer repeat patterns from historical logs when they clearly match the current artifact.",
        ]
        if reference_data:
            reference_priorities.append(f"Historical data available with {min(len(reference_data.splitlines()), 25)} lines of context.")
        analysis_directives = [
            f"Optimize for {task_label.lower()} within {domain_label.lower()}.",
            f"Adapt recommendations to {chip_type or 'the current chip program'} and its likely workflow constraints.",
        ]
        if context:
            analysis_directives.append(context[:180])
        chip_focus = self._chip_focus(runtime_label, chip_type)
        return {
            "chip_focus": chip_focus,
            "instruction_overrides": instruction_overrides[:5],
            "reference_priorities": reference_priorities[:5],
            "analysis_directives": analysis_directives[:5],
            "output_emphasis": f"Ranked, evidence-grounded actions tailored to the current run focus and the client's workflow style.",
            "prompt_addendum": (
                f"Client profile: {client_profile or 'standard enterprise workflow'}. "
                f"Chip focus: {chip_focus}. "
                f"Honor these instructions: {' | '.join(instruction_overrides[:3])}. "
                f"Use historical context carefully: {' | '.join(reference_priorities[:2])}."
            ),
        }

    def _chip_focus(self, runtime_label: str | None, chip_type: str | None) -> str:
        runtime = str(runtime_label or "").strip()
        chip = str(chip_type or "").strip()
        if runtime and chip and runtime.lower() not in chip.lower() and chip.lower() not in runtime.lower():
            return f"{runtime} · {chip}"
        if runtime:
            return runtime
        if chip:
            return chip
        return "general semiconductor workflow"

    def _extract_json(self, raw: str) -> dict[str, Any]:
        stripped = raw.strip()
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in orchestrator response.")
        return json.loads(match.group(0))

    def _as_list(self, value: Any, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            built = [str(item) for item in value if str(item).strip()]
            if built:
                return built[:5]
        return fallback
