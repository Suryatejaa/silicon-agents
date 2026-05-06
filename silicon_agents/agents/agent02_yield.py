"""Yield agent logic."""

from __future__ import annotations

import json
import logging
import re
from statistics import mean, pstdev
from typing import AsyncIterator

from silicon_agents.agents.decision_layer import deduplicate_decisions, sort_decisions
from silicon_agents.core.config import get_settings
from silicon_agents.core.llm import LLMProvider
from silicon_agents.core.schemas import Decision, DoneEvent, ParsedItem, YieldRequest
from silicon_agents.orchestration.prompt_orchestrator import PromptOrchestrator
from silicon_agents.parsers.ate_parser import parse_ate_csv, parse_spc_csv
from silicon_agents.prompts.ate_prompt import ATE_SYSTEM_PROMPT
from silicon_agents.prompts.spc_prompt import SPC_SYSTEM_PROMPT


logger = logging.getLogger(__name__)


class YieldAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = LLMProvider()
        self.orchestrator = PromptOrchestrator()
        self.last_parser_format: str | None = None
        self.last_parser_confidence: float | None = None
        self.last_parser_warnings: list[str] = []

    async def stream(self, request: YieldRequest) -> AsyncIterator[tuple[str, dict]]:
        self.last_parser_format = None
        self.last_parser_confidence = None
        self.last_parser_warnings = []
        if request.mode == "spc":
            async for event in self._stream_spc(request):
                yield event
            return
        async for event in self._stream_ate(request):
            yield event

    async def _stream_ate(self, request: YieldRequest) -> AsyncIterator[tuple[str, dict]]:
        parsed = parse_ate_csv(request.csv_data)
        self._capture_parser_signals(parsed)
        fallback_decisions = self._build_ate_decisions(parsed.items, request.project_id)
        llm_result = await self._run_ate_llm(parsed, request, fallback_decisions)
        decisions = llm_result["decisions"]

        yield "orchestration", llm_result["orchestration"]
        yield "step", {"num": 1, "label": "Parsing parametric data"}
        yield "chunk", {"text": llm_result["steps"]["parse"]}

        yield "step", {"num": 2, "label": "Detecting anomalies"}
        yield "chunk", {"text": llm_result["steps"]["detect"]}

        yield "step", {"num": 3, "label": "Analysing yield risk"}
        for chunk in llm_result["steps"]["analyse"]:
            yield "chunk", {"text": chunk}

        yield "step", {"num": 4, "label": "Recommending actions"}
        yield "chunk", {"text": self._recommendation_summary(decisions, "yield")}
        for decision in decisions:
            yield "decision", decision.model_dump()

        yield "step", {"num": 5, "label": "Prioritising ROI"}
        yield "chunk", {"text": llm_result["steps"]["prioritise"]}

        done = DoneEvent(
            total_decisions=len(decisions),
            high=sum(1 for d in decisions if d.priority == "HIGH"),
            medium=sum(1 for d in decisions if d.priority == "MEDIUM"),
            low=sum(1 for d in decisions if d.priority == "LOW"),
            provider=llm_result["provider"],
        )
        yield "done", done.model_dump()

    async def _stream_spc(self, request: YieldRequest) -> AsyncIterator[tuple[str, dict]]:
        parsed = parse_spc_csv(request.csv_data)
        self._capture_parser_signals(parsed)
        fallback_decisions = self._build_spc_decisions(parsed.items, request.project_id)
        llm_result = await self._run_spc_llm(parsed, request, fallback_decisions)
        decisions = llm_result["decisions"]

        yield "orchestration", llm_result["orchestration"]
        yield "step", {"num": 1, "label": "Parsing lot history"}
        yield "chunk", {"text": llm_result["steps"]["parse"]}

        yield "step", {"num": 2, "label": "Detecting drift"}
        yield "chunk", {"text": llm_result["steps"]["detect"]}

        yield "step", {"num": 3, "label": "Analysing process shift"}
        for chunk in llm_result["steps"]["analyse"]:
            yield "chunk", {"text": chunk}

        yield "step", {"num": 4, "label": "Recommending fab actions"}
        yield "chunk", {"text": self._recommendation_summary(decisions, "spc")}
        for decision in decisions:
            yield "decision", decision.model_dump()

        yield "step", {"num": 5, "label": "Prioritising escalation"}
        yield "chunk", {"text": llm_result["steps"]["prioritise"]}

        done = DoneEvent(
            total_decisions=len(decisions),
            high=sum(1 for d in decisions if d.priority == "HIGH"),
            medium=sum(1 for d in decisions if d.priority == "MEDIUM"),
            low=sum(1 for d in decisions if d.priority == "LOW"),
            provider=llm_result["provider"],
        )
        yield "done", done.model_dump()

    async def _run_ate_llm(self, parsed, request: YieldRequest, fallback_decisions: list[Decision]) -> dict:
        fallback = self._fallback_result_for_ate(parsed, request, fallback_decisions)
        prompt_plan = await self.orchestrator.build_plan(
            domain_label="yield analysis and binning review",
            task_label="ranking yield anomaly and mis-bin actions",
            runtime_label=request.lot_id,
            chip_type=request.chip_type,
            client_profile=request.client_profile,
            custom_instructions=request.custom_instructions,
            reference_data=request.reference_data,
            reference_data_label=request.reference_data_label,
            context=request.context,
            parsed_summary={
                "lot_id": request.lot_id,
                "summary": parsed.summary.model_dump(),
                "metadata": parsed.metadata,
                "type": parsed.type,
            },
        )
        prompt = (
            "You must respond with valid JSON only. No markdown fences.\n"
            "Return an object with keys parse, detect, analyse, prioritise, decisions.\n"
            "parse and detect are strings. analyse is an array of 2 to 4 strings. prioritise is a string.\n"
            "decisions is an array of up to 6 objects with keys target, action, rationale, priority, confidence, effort, type.\n"
            "type must be either bin_mismatch or yield_anomaly.\n"
            "Priorities must be HIGH, MEDIUM, or LOW.\n"
            f"Lot id: {request.lot_id}\n"
            f"Context: {request.context or 'None'}\n"
            f"Chip type: {request.chip_type or 'Unknown'}\n"
            f"Client profile: {request.client_profile or 'Not provided'}\n"
            f"Custom instructions: {request.custom_instructions or 'Not provided'}\n"
            f"Reference data label: {request.reference_data_label or 'Not provided'}\n"
            f"Reference data excerpt: {(request.reference_data or 'Not provided')[:5000]}\n"
            f"Orchestrated prompt plan: {json.dumps(prompt_plan)}\n"
            f"Parsed ATE data: {parsed.model_dump_json()}\n"
        )
        return await self._run_llm_json(
            system_prompt=ATE_SYSTEM_PROMPT.strip(),
            user_prompt=prompt,
            fallback=fallback,
            project_id=request.project_id,
            default_type="yield_anomaly",
            prompt_plan=prompt_plan,
        )

    async def _run_spc_llm(self, parsed, request: YieldRequest, fallback_decisions: list[Decision]) -> dict:
        fallback = self._fallback_result_for_spc(parsed, fallback_decisions)
        prompt_plan = await self.orchestrator.build_plan(
            domain_label="spc drift and process monitoring",
            task_label="ranking process drift actions",
            runtime_label=request.lot_id,
            chip_type=request.chip_type,
            client_profile=request.client_profile,
            custom_instructions=request.custom_instructions,
            reference_data=request.reference_data,
            reference_data_label=request.reference_data_label,
            context=request.context,
            parsed_summary={
                "lot_id": request.lot_id,
                "summary": parsed.summary.model_dump(),
                "metadata": parsed.metadata,
                "type": parsed.type,
            },
        )
        prompt = (
            "You must respond with valid JSON only. No markdown fences.\n"
            "Return an object with keys parse, detect, analyse, prioritise, decisions.\n"
            "parse and detect are strings. analyse is an array of 2 to 4 strings. prioritise is a string.\n"
            "decisions is an array of up to 6 objects with keys target, action, rationale, priority, confidence, effort, type.\n"
            "type must be either spc_drift or spc_alert.\n"
            "Priorities must be HIGH, MEDIUM, or LOW.\n"
            f"Lot id: {request.lot_id}\n"
            f"Context: {request.context or 'None'}\n"
            f"Chip type: {request.chip_type or 'Unknown'}\n"
            f"Client profile: {request.client_profile or 'Not provided'}\n"
            f"Custom instructions: {request.custom_instructions or 'Not provided'}\n"
            f"Reference data label: {request.reference_data_label or 'Not provided'}\n"
            f"Reference data excerpt: {(request.reference_data or 'Not provided')[:5000]}\n"
            f"Orchestrated prompt plan: {json.dumps(prompt_plan)}\n"
            f"Parsed SPC data: {parsed.model_dump_json()}\n"
        )
        return await self._run_llm_json(
            system_prompt=SPC_SYSTEM_PROMPT.strip(),
            user_prompt=prompt,
            fallback=fallback,
            project_id=request.project_id,
            default_type="spc_drift",
            prompt_plan=prompt_plan,
        )

    async def _run_llm_json(self, system_prompt: str, user_prompt: str, fallback: dict, project_id: str, default_type: str, prompt_plan: dict) -> dict:
        raw = ""
        try:
            async for chunk in self.llm.stream(system_prompt, user_prompt, self._fallback_text(fallback)):
                raw += chunk
            if self.llm.last_provider == "mock":
                fallback["orchestration"] = self._orchestration_payload(prompt_plan)
                fallback["provider"] = "mock"
                fallback["llm_diagnostics"] = self._llm_diagnostics("provider_fallback", raw)
                fallback["orchestration"]["llm_diagnostics"] = fallback["llm_diagnostics"]
                return fallback
            parsed_json = self._extract_json(raw)
            decisions = self._decisions_from_llm(parsed_json.get("decisions", []), fallback["decisions"], project_id, default_type)
            if not decisions:
                decisions = fallback["decisions"]
            return {
                "steps": {
                    "parse": parsed_json.get("parse", fallback["steps"]["parse"]),
                    "detect": parsed_json.get("detect", fallback["steps"]["detect"]),
                    "analyse": parsed_json.get("analyse", fallback["steps"]["analyse"]),
                    "prioritise": parsed_json.get("prioritise", fallback["steps"]["prioritise"]),
                },
                "decisions": decisions,
                "provider": self.llm.last_provider,
                "orchestration": {
                    **self._orchestration_payload(prompt_plan),
                    "llm_diagnostics": self._llm_diagnostics("live_json", raw),
                },
                "llm_diagnostics": self._llm_diagnostics("live_json", raw),
            }
        except Exception as exc:
            logger.warning(
                "Agent 02 live LLM response fell back to deterministic analysis provider=%s model=%s error=%s raw_head=%r attempts=%s",
                self.llm.last_provider,
                self.llm.last_model,
                exc,
                raw[:500],
                self.llm.provider_attempts,
            )
            fallback["orchestration"] = self._orchestration_payload(prompt_plan)
            fallback["provider"] = self.llm.last_provider if self.llm.last_provider != "mock" else "mock"
            fallback["llm_diagnostics"] = self._llm_diagnostics(f"parse_or_decision_fallback: {exc}", raw)
            fallback["orchestration"]["llm_diagnostics"] = fallback["llm_diagnostics"]
            return fallback

    def _llm_diagnostics(self, reason: str, raw: str = "") -> dict:
        return {
            "provider": self.llm.last_provider,
            "model": self.llm.last_model,
            "attempts": list(self.llm.provider_attempts),
            "fallback_reason": self.llm.fallback_reason or reason,
            "raw_response_chars": len(raw or ""),
            "raw_response_excerpt": (raw or "")[:500],
        }

    def _fallback_text(self, fallback: dict) -> str:
        analyse = fallback["steps"]["analyse"]
        if isinstance(analyse, list):
            analyse = "\n".join(analyse)
        return "\n".join(
            [
                fallback["steps"]["parse"],
                fallback["steps"]["detect"],
                str(analyse),
                fallback["steps"]["prioritise"],
            ]
        )

    def _orchestration_payload(self, prompt_plan: dict) -> dict:
        return {
            "chip_focus": prompt_plan.get("chip_focus", ""),
            "output_emphasis": prompt_plan.get("output_emphasis", ""),
            "instruction_overrides": prompt_plan.get("instruction_overrides", []),
            "reference_priorities": prompt_plan.get("reference_priorities", []),
            "analysis_directives": prompt_plan.get("analysis_directives", []),
            "prompt_addendum": prompt_plan.get("prompt_addendum", ""),
            "parser_format": self.last_parser_format,
            "parser_confidence": self.last_parser_confidence,
            "parser_warnings": list(self.last_parser_warnings),
            "provider": self.orchestrator.last_provider,
            "orchestration_llm_diagnostics": dict(self.orchestrator.last_diagnostics),
        }

    def _capture_parser_signals(self, parsed) -> None:
        metadata = getattr(parsed, "metadata", {}) or {}
        parser_format = metadata.get("parser_format") or getattr(parsed, "type", None)
        parser_confidence = metadata.get("parser_confidence")
        parser_warnings = metadata.get("parser_warnings") or []
        self.last_parser_format = str(parser_format) if parser_format else None
        self.last_parser_confidence = float(parser_confidence) if parser_confidence is not None else None
        self.last_parser_warnings = [str(item) for item in parser_warnings]

    def _extract_json(self, raw: str) -> dict:
        stripped = raw.strip()
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in LLM response.")
        return json.loads(match.group(0))

    def _decisions_from_llm(self, llm_decisions: list[dict], fallback_decisions: list[Decision], project_id: str, default_type: str) -> list[Decision]:
        built: list[Decision] = []
        for idx, item in enumerate(llm_decisions[: self.settings.max_decisions], start=1):
            try:
                built.append(
                    Decision(
                        id=f"{'S' if str(item.get('type', default_type)).startswith('spc') else 'Y'}{idx:03d}",
                        project_id=project_id,
                        type=str(item.get("type", default_type)),
                        target=str(item["target"]),
                        action=str(item["action"]),
                        rationale=str(item["rationale"]),
                        priority=str(item["priority"]).upper(),
                        confidence=float(item["confidence"]),
                        effort=str(item["effort"]),
                        metadata={"source": "llm", "orchestration_enabled": True},
                    )
                )
            except Exception:
                continue
        return sort_decisions(deduplicate_decisions(built)) if built else fallback_decisions

    def _fallback_result_for_ate(self, parsed, request: YieldRequest, decisions: list[Decision]) -> dict:
        return {
            "steps": {
                "parse": f"Parsed {parsed.summary.total} chips for lot {request.lot_id}.",
                "detect": f"Flagged {sum(1 for d in decisions if d.type == 'yield_anomaly')} anomaly candidates and {sum(1 for d in decisions if d.type == 'bin_mismatch')} likely mis-bins.",
                "analyse": [decision.rationale for decision in decisions[: min(3, len(decisions))]],
                "prioritise": "Ranked actions by mis-bin revenue upside, spec-margin risk, and likely operational effort.",
            },
            "decisions": decisions,
            "provider": "mock",
        }

    def _fallback_result_for_spc(self, parsed, decisions: list[Decision]) -> dict:
        return {
            "steps": {
                "parse": f"Parsed {parsed.summary.total} lots for SPC review.",
                "detect": f"Detected {len(decisions)} drift or escalation candidates.",
                "analyse": [decision.rationale for decision in decisions[: min(3, len(decisions))]],
                "prioritise": "Prioritised actions by drift momentum, control-limit risk, and projected yield loss.",
            },
            "decisions": decisions,
            "provider": "mock",
        }

    def _build_ate_decisions(self, items: list[ParsedItem], project_id: str) -> list[Decision]:
        freq_values = [item.context.get("max_freq_ghz") for item in items if item.context.get("max_freq_ghz") is not None]
        leakage_values = [item.context.get("leakage_ua") for item in items if item.context.get("leakage_ua") is not None]
        leakage_mean = mean(leakage_values) if leakage_values else 0.0
        leakage_std = pstdev(leakage_values) if len(leakage_values) > 1 else 0.0

        decisions: list[Decision] = []
        next_id = 1
        for item in items:
            freq = item.context.get("max_freq_ghz")
            leakage = item.context.get("leakage_ua")
            bin_assignment = int(item.bin_assignment) if str(item.bin_assignment).isdigit() else None

            if freq is not None and leakage is not None and freq >= self.settings.bin1_min_freq_ghz and leakage <= self.settings.bin1_max_leakage_ua and bin_assignment not in {1, None}:
                decisions.append(
                    Decision(
                        id=f"Y{next_id:03d}",
                        project_id=project_id,
                        type="bin_mismatch",
                        target=item.name,
                        action="Review bin thresholds and reclassify this die as a premium candidate.",
                        rationale=f"{item.name} meets Bin 1 guardrails on frequency and leakage but is currently assigned to Bin {bin_assignment}.",
                        priority="HIGH",
                        confidence=0.94,
                        effort="30min",
                        metadata={"freq": freq, "leakage": leakage, "prompt": ATE_SYSTEM_PROMPT.strip(), "orchestration_enabled": True},
                    )
                )
                next_id += 1

            if leakage is not None and leakage_std > 0 and leakage > leakage_mean + 1.5 * leakage_std:
                decisions.append(
                    Decision(
                        id=f"Y{next_id:03d}",
                        project_id=project_id,
                        type="yield_anomaly",
                        target=item.name,
                        action="Escalate this chip for deeper parametric review and correlate with lot-level process conditions.",
                        rationale=f"{item.name} shows unusually high leakage ({leakage}) compared with the lot baseline ({leakage_mean:.1f} +/- {leakage_std:.1f}).",
                        priority="HIGH" if item.status == "failed" else "MEDIUM",
                        confidence=0.89,
                        effort="2hrs",
                        metadata={"freq": freq, "leakage": leakage, "prompt": ATE_SYSTEM_PROMPT.strip(), "orchestration_enabled": True},
                    )
                )
                next_id += 1

        if not decisions and items:
            top = max(items, key=lambda item: item.context.get("leakage_ua") or 0.0)
            decisions.append(
                Decision(
                    id="Y001",
                    project_id=project_id,
                    type="yield_anomaly",
                    target=top.name,
                    action="Use this chip as the first review candidate to validate binning and parametric margins.",
                    rationale="No severe outlier was detected, so the system selected the riskiest visible chip for manual spot-checking.",
                    priority="LOW",
                    confidence=0.62,
                    effort="30min",
                    metadata={"prompt": ATE_SYSTEM_PROMPT.strip(), "orchestration_enabled": True},
                )
            )
        return sort_decisions(deduplicate_decisions(decisions))[: self.settings.max_decisions]

    def _build_spc_decisions(self, items: list[ParsedItem], project_id: str) -> list[Decision]:
        leakage_values = [item.context.get("avg_leakage_ua") for item in items if item.context.get("avg_leakage_ua") is not None]
        if not leakage_values:
            return []
        baseline = mean(leakage_values)
        std = pstdev(leakage_values) if len(leakage_values) > 1 else 0.0
        decisions: list[Decision] = []

        increasing = all(leakage_values[idx] <= leakage_values[idx + 1] for idx in range(len(leakage_values) - 1))
        last = leakage_values[-1]
        if increasing and len(leakage_values) >= 4:
            decisions.append(
                Decision(
                    id="S001",
                    project_id=project_id,
                    type="spc_drift",
                    target="avg_leakage_ua",
                    action="Alert the fab process engineer and inspect the process step that most strongly correlates with leakage drift.",
                    rationale=f"Leakage increased monotonically across {len(leakage_values)} lots, ending at {last:.1f}uA versus a baseline of {baseline:.1f}uA.",
                    priority="HIGH" if std == 0 or last >= baseline + 2 * std else "MEDIUM",
                    confidence=0.91,
                    effort="2hrs",
                    metadata={"prompt": SPC_SYSTEM_PROMPT.strip(), "orchestration_enabled": True},
                )
            )

        if std > 0 and last > baseline + 3 * std:
            decisions.append(
                Decision(
                    id="S002",
                    project_id=project_id,
                    type="spc_alert",
                    target=items[-1].name,
                    action="Treat the latest lot as a control-limit alert and gate further release until reviewed.",
                    rationale=f"The latest lot exceeded the 3-sigma leakage threshold ({last:.1f}uA vs UCL {(baseline + 3 * std):.1f}uA).",
                    priority="HIGH",
                    confidence=0.95,
                    effort="30min",
                    metadata={"prompt": SPC_SYSTEM_PROMPT.strip(), "orchestration_enabled": True},
                )
            )

        return sort_decisions(deduplicate_decisions(decisions))[: self.settings.max_decisions]

    def _recommendation_summary(self, decisions: list[Decision], workflow: str) -> str:
        if not decisions:
            if workflow == "spc":
                return "No fab escalation actions were generated for this SPC review."
            return "No yield review actions were generated for this lot."
        targets = ", ".join(decision.target for decision in decisions[:3])
        if workflow == "spc":
            return (
                f"Generated {len(decisions)} fab or process-control actions for review. "
                f"Top escalation targets: {targets}."
            )
        return (
            f"Generated {len(decisions)} yield actions and placed them in the review queue. "
            f"Top targets: {targets}."
        )
