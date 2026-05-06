"""Verification agent logic."""

from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from typing import AsyncIterator

from silicon_agents.agents.decision_layer import deduplicate_decisions, sort_decisions
from silicon_agents.core.config import get_settings
from silicon_agents.core.llm import LLMProvider
from silicon_agents.core.schemas import Decision, DoneEvent, ParsedItem, VerifyRequest
from silicon_agents.orchestration.prompt_orchestrator import PromptOrchestrator
from silicon_agents.parsers.coverage_parser import parse_coverage_report
from silicon_agents.parsers.regression_parser import parse_regression_log
from silicon_agents.prompts.coverage_prompt import COVERAGE_SYSTEM_PROMPT
from silicon_agents.prompts.regression_prompt import REGRESSION_SYSTEM_PROMPT


logger = logging.getLogger(__name__)


class VerificationAgent:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm = LLMProvider()
        self.orchestrator = PromptOrchestrator()
        self.last_parser_format: str | None = None
        self.last_parser_confidence: float | None = None
        self.last_parser_warnings: list[str] = []

    async def stream(self, request: VerifyRequest) -> AsyncIterator[tuple[str, dict]]:
        self.last_parser_format = None
        self.last_parser_confidence = None
        self.last_parser_warnings = []
        if request.mode == "triage":
            async for event in self._stream_triage(request):
                yield event
            return
        async for event in self._stream_coverage(request):
            yield event

    async def _stream_coverage(self, request: VerifyRequest) -> AsyncIterator[tuple[str, dict]]:
        parsed = parse_coverage_report(request.report_text, request.format)
        self._capture_parser_signals(parsed)
        gaps = [item for item in parsed.items if item.status != "covered"]
        fallback_decisions = self._build_coverage_decisions(gaps, request.project_id)
        llm_result = await self._run_coverage_llm(parsed, request, fallback_decisions)
        decisions = llm_result["decisions"]

        yield "orchestration", llm_result["orchestration"]
        yield "step", {"num": 1, "label": "Parsing report"}
        yield "chunk", {"text": llm_result["steps"]["parse"]}

        yield "step", {"num": 2, "label": "Detecting gaps"}
        yield "chunk", {"text": llm_result["steps"]["detect"]}

        yield "step", {"num": 3, "label": "Analysing root causes"}
        for chunk in llm_result["steps"]["analyse"]:
            yield "chunk", {"text": chunk}

        yield "step", {"num": 4, "label": "Generating stimuli plan"}
        yield "chunk", {"text": self._coverage_recommendation_summary(decisions)}
        for decision in decisions[: min(4, len(decisions))]:
            yield "decision", decision.model_dump()

        yield "step", {"num": 5, "label": "Prioritising actions"}
        yield "chunk", {"text": llm_result["steps"]["prioritise"]}

        done = DoneEvent(
            total_decisions=len(decisions),
            high=sum(1 for d in decisions if d.priority == "HIGH"),
            medium=sum(1 for d in decisions if d.priority == "MEDIUM"),
            low=sum(1 for d in decisions if d.priority == "LOW"),
            provider=llm_result["provider"],
        )
        yield "done", done.model_dump()

    async def _stream_triage(self, request: VerifyRequest) -> AsyncIterator[tuple[str, dict]]:
        parsed = parse_regression_log(request.report_text)
        self._capture_parser_signals(parsed)
        failures = [item for item in parsed.items if item.status == "failed"]
        clusters = self._cluster_failures(failures)
        fallback_decisions = self._build_triage_decisions(clusters, request.project_id)
        llm_result = await self._run_triage_llm(parsed, request, fallback_decisions, clusters)
        decisions = llm_result["decisions"]

        yield "orchestration", llm_result["orchestration"]
        yield "step", {"num": 1, "label": "Parsing regression log"}
        yield "chunk", {"text": llm_result["steps"]["parse"]}

        yield "step", {"num": 2, "label": "Detecting failure clusters"}
        yield "chunk", {"text": llm_result["steps"]["detect"]}

        yield "step", {"num": 3, "label": "Analysing root causes"}
        for chunk in llm_result["steps"]["analyse"]:
            yield "chunk", {"text": chunk}

        yield "step", {"num": 4, "label": "Recommending investigations"}
        yield "chunk", {"text": self._triage_recommendation_summary(decisions)}
        for decision in decisions:
            yield "decision", decision.model_dump()

        yield "step", {"num": 5, "label": "Prioritising actions"}
        yield "chunk", {"text": llm_result["steps"]["prioritise"]}

        done = DoneEvent(
            total_decisions=len(decisions),
            high=sum(1 for d in decisions if d.priority == "HIGH"),
            medium=sum(1 for d in decisions if d.priority == "MEDIUM"),
            low=sum(1 for d in decisions if d.priority == "LOW"),
            provider=llm_result["provider"],
        )
        yield "done", done.model_dump()

    async def _run_coverage_llm(self, parsed, request: VerifyRequest, fallback_decisions: list[Decision]) -> dict:
        fallback = self._fallback_result_for_coverage(parsed, request, fallback_decisions)
        prompt_plan = await self.orchestrator.build_plan(
            domain_label="verification coverage closure",
            task_label="ranking coverage gap closure actions",
            runtime_label=request.design_name,
            chip_type=request.chip_type,
            client_profile=request.client_profile,
            custom_instructions=request.custom_instructions,
            reference_data=request.reference_data,
            reference_data_label=request.reference_data_label,
            context=request.context,
            parsed_summary={
                "design_name": request.design_name,
                "summary": parsed.summary.model_dump(),
                "metadata": parsed.metadata,
                "type": parsed.type,
            },
        )
        prompt = (
            "You must respond with valid JSON only. No markdown fences.\n"
            "Return an object with keys parse, detect, analyse, prioritise, decisions.\n"
            "parse and detect are strings. analyse is an array of 2 to 4 strings. prioritise is a string.\n"
            "decisions is an array of up to 6 objects with keys target, action, rationale, priority, confidence, effort, evidence, rank_basis.\n"
            "Priorities must be HIGH, MEDIUM, or LOW.\n"
            "evidence must cite the relevant covergroup/bin symptom from the parsed input.\n"
            "rank_basis must explain why the action was prioritized now.\n"
            f"Design name: {request.design_name}\n"
            f"Context: {request.context or 'None'}\n"
            f"Chip type: {request.chip_type or 'Unknown'}\n"
            f"Client profile: {request.client_profile or 'Not provided'}\n"
            f"Custom instructions: {request.custom_instructions or 'Not provided'}\n"
            f"Reference data label: {request.reference_data_label or 'Not provided'}\n"
            f"Reference data excerpt: {(request.reference_data or 'Not provided')[:5000]}\n"
            f"Orchestrated prompt plan: {json.dumps(prompt_plan)}\n"
            f"Parsed coverage data: {parsed.model_dump_json()}\n"
        )
        result = await self._run_llm_json(
            system_prompt=COVERAGE_SYSTEM_PROMPT.strip(),
            user_prompt=prompt,
            fallback=fallback,
            decision_type="coverage_gap",
            project_id=request.project_id,
        )
        result["decisions"] = self._enrich_coverage_decisions(result["decisions"], parsed)
        result["orchestration"] = self._orchestration_payload(prompt_plan)
        result["orchestration"]["llm_diagnostics"] = result.get("llm_diagnostics", {})
        return result

    async def _run_triage_llm(self, parsed, request: VerifyRequest, fallback_decisions: list[Decision], clusters: dict) -> dict:
        fallback = self._fallback_result_for_triage(parsed, fallback_decisions, clusters)
        prompt_plan = await self.orchestrator.build_plan(
            domain_label="verification regression triage",
            task_label="ranking regression investigations",
            runtime_label=request.design_name,
            chip_type=request.chip_type,
            client_profile=request.client_profile,
            custom_instructions=request.custom_instructions,
            reference_data=request.reference_data,
            reference_data_label=request.reference_data_label,
            context=request.context,
            parsed_summary={
                "design_name": request.design_name,
                "summary": parsed.summary.model_dump(),
                "metadata": parsed.metadata,
                "type": parsed.type,
                "clusters": {k: [item.name for item in v] for k, v in clusters.items()},
            },
        )
        prompt = (
            "You must respond with valid JSON only. No markdown fences.\n"
            "Return an object with keys parse, detect, analyse, prioritise, decisions.\n"
            "parse and detect are strings. analyse is an array of 2 to 4 strings. prioritise is a string.\n"
            "decisions is an array of up to 6 objects with keys target, action, rationale, priority, confidence, effort, evidence, rank_basis.\n"
            "Priorities must be HIGH, MEDIUM, or LOW.\n"
            "evidence must cite the observed cluster or failure signature from the parsed input.\n"
            "rank_basis must explain why the action should be investigated first.\n"
            f"Design name: {request.design_name}\n"
            f"Context: {request.context or 'None'}\n"
            f"Chip type: {request.chip_type or 'Unknown'}\n"
            f"Client profile: {request.client_profile or 'Not provided'}\n"
            f"Custom instructions: {request.custom_instructions or 'Not provided'}\n"
            f"Reference data label: {request.reference_data_label or 'Not provided'}\n"
            f"Reference data excerpt: {(request.reference_data or 'Not provided')[:5000]}\n"
            f"Orchestrated prompt plan: {json.dumps(prompt_plan)}\n"
            f"Parsed regression data: {parsed.model_dump_json()}\n"
            f"Failure clusters: {json.dumps({k: [item.name for item in v] for k, v in clusters.items()})}\n"
        )
        result = await self._run_llm_json(
            system_prompt=REGRESSION_SYSTEM_PROMPT.strip(),
            user_prompt=prompt,
            fallback=fallback,
            decision_type="regression_failure",
            project_id=request.project_id,
        )
        result["decisions"] = self._enrich_triage_decisions(result["decisions"], clusters)
        result["orchestration"] = self._orchestration_payload(prompt_plan)
        result["orchestration"]["llm_diagnostics"] = result.get("llm_diagnostics", {})
        return result

    async def _run_llm_json(self, system_prompt: str, user_prompt: str, fallback: dict, decision_type: str, project_id: str) -> dict:
        raw = ""
        try:
            async for chunk in self.llm.stream(system_prompt, user_prompt, self._fallback_text(fallback)):
                raw += chunk
            if self.llm.last_provider == "mock":
                fallback["provider"] = "mock"
                fallback["llm_diagnostics"] = self._llm_diagnostics("provider_fallback", raw)
                return fallback
            parsed_json = self._extract_json(raw)
            decisions = self._decisions_from_llm(parsed_json.get("decisions", []), fallback["decisions"], project_id, decision_type)
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
                "llm_diagnostics": self._llm_diagnostics("live_json", raw),
            }
        except Exception as exc:
            logger.warning(
                "Agent 01 live LLM response fell back to deterministic analysis provider=%s model=%s error=%s raw_head=%r attempts=%s",
                self.llm.last_provider,
                self.llm.last_model,
                exc,
                raw[:500],
                self.llm.provider_attempts,
            )
            fallback["provider"] = self.llm.last_provider if self.llm.last_provider != "mock" else "mock"
            fallback["llm_diagnostics"] = self._llm_diagnostics(f"parse_or_decision_fallback: {exc}", raw)
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
        parser_format = metadata.get("parser_format") or metadata.get("tool") or getattr(parsed, "type", None)
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

    def _decisions_from_llm(self, llm_decisions: list[dict], fallback_decisions: list[Decision], project_id: str, decision_type: str) -> list[Decision]:
        built: list[Decision] = []
        for idx, item in enumerate(llm_decisions[: self.settings.max_decisions], start=1):
            try:
                built.append(
                    Decision(
                        id=f"{'D' if decision_type == 'coverage_gap' else 'T'}{idx:03d}",
                        project_id=project_id,
                        type=decision_type,
                        target=str(item["target"]),
                        action=str(item["action"]),
                        rationale=str(item["rationale"]),
                        priority=str(item["priority"]).upper(),
                        confidence=float(item["confidence"]),
                        effort=str(item["effort"]),
                        metadata={
                            "source": "llm",
                            "evidence": str(item.get("evidence", "")),
                            "rank_basis": str(item.get("rank_basis", "")),
                            "orchestration_enabled": True,
                        },
                    )
                )
            except Exception:
                continue
        return sort_decisions(deduplicate_decisions(built)) if built else fallback_decisions

    def _fallback_result_for_coverage(self, parsed, request: VerifyRequest, decisions: list[Decision]) -> dict:
        gaps = [item for item in parsed.items if item.status != "covered"]
        gap_names = ", ".join(item.name for item in gaps[:5]) if gaps else "No material gaps found."
        return {
            "steps": {
                "parse": f"Parsed {parsed.summary.total} coverpoints from {len(parsed.metadata.get('groups', [])) or 1} groups for {request.design_name}.",
                "detect": f"Detected {len(gaps)} uncovered or undercovered points. Top findings: {gap_names}",
                "analyse": [f"{item.name}: {self._coverage_cause(item)}" for item in gaps[: min(3, len(gaps))]],
                "prioritise": f"Prioritised {len(decisions)} actions for the engineer review queue using functional risk, likely bug escape risk, and effort.",
            },
            "decisions": self._enrich_coverage_decisions(decisions, parsed),
            "provider": "mock",
        }

    def _fallback_result_for_triage(self, parsed, decisions: list[Decision], clusters: dict) -> dict:
        return {
            "steps": {
                "parse": f"Parsed {parsed.summary.total} regression results with {parsed.summary.failed} failures.",
                "detect": f"Grouped failures into {len(clusters)} likely root-cause clusters.",
                "analyse": [
                    f"{cluster_name}: {len(items)} failures share a common pattern around {self._cluster_reason(cluster_name)}."
                    for cluster_name, items in list(clusters.items())[:3]
                ],
                "prioritise": "Ranked clusters by blast radius and probability of a single RTL or handshake regression.",
            },
            "decisions": self._enrich_triage_decisions(decisions, clusters),
            "provider": "mock",
        }

    def _build_coverage_decisions(self, gaps: list[ParsedItem], project_id: str) -> list[Decision]:
        decisions: list[Decision] = []
        for idx, gap in enumerate(gaps, start=1):
            priority = "HIGH" if gap.hits in {None, 0} else "MEDIUM"
            confidence = 0.9 if priority == "HIGH" else 0.78
            effort = "2hrs" if priority == "HIGH" else "30min"
            decisions.append(
                Decision(
                    id=f"D{idx:03d}",
                    project_id=project_id,
                    type="coverage_gap",
                    target=gap.name,
                    action=self._coverage_action(gap),
                    rationale=self._coverage_cause(gap),
                    priority=priority,
                    confidence=confidence,
                    effort=effort,
                    metadata={
                        "group": gap.context.get("group"),
                        "prompt": COVERAGE_SYSTEM_PROMPT.strip(),
                        "evidence": gap.context.get("line", ""),
                        "rank_basis": self._coverage_rank_basis(gap),
                        "workflow_stage": "coverage_closure",
                        "orchestration_enabled": True,
                    },
                )
            )
        return self._enrich_coverage_decisions(sort_decisions(deduplicate_decisions(decisions))[: self.settings.max_decisions], None)

    def _build_triage_decisions(self, clusters: dict[str, list[ParsedItem]], project_id: str) -> list[Decision]:
        decisions: list[Decision] = []
        for idx, (cluster_name, items) in enumerate(clusters.items(), start=1):
            size = len(items)
            priority = "HIGH" if size >= 10 else "MEDIUM" if size >= 3 else "LOW"
            decisions.append(
                Decision(
                    id=f"T{idx:03d}",
                    project_id=project_id,
                    type="regression_failure",
                    target=cluster_name,
                    action=f"Inspect the first failing RTL path associated with {cluster_name} and reproduce one representative test locally.",
                    rationale=f"{size} tests share the same failure signature, which suggests a common RTL root cause rather than isolated test noise.",
                    priority=priority,
                    confidence=min(0.95, 0.55 + size * 0.04),
                    effort="30min" if size < 5 else "2hrs",
                    metadata={
                        "sample_tests": [item.name for item in items[:3]],
                        "sample_messages": [item.context.get("message", "") for item in items[:2]],
                        "cluster_size": size,
                        "rank_basis": self._triage_rank_basis(size),
                        "workflow_stage": "regression_triage",
                        "prompt": REGRESSION_SYSTEM_PROMPT.strip(),
                        "orchestration_enabled": True,
                    },
                )
            )
        return self._enrich_triage_decisions(sort_decisions(deduplicate_decisions(decisions))[: self.settings.max_decisions], clusters)

    def _enrich_coverage_decisions(self, decisions: list[Decision], parsed) -> list[Decision]:
        for decision in decisions:
            if decision.metadata.get("evidence"):
                continue
            if parsed is None:
                continue
            match = next((item for item in parsed.items if item.name == decision.target), None)
            if not match:
                continue
            decision.metadata["group"] = match.context.get("group")
            decision.metadata["evidence"] = match.context.get("line", "")
            decision.metadata["rank_basis"] = decision.metadata.get("rank_basis") or self._coverage_rank_basis(match)
            decision.metadata["workflow_stage"] = "coverage_closure"
        return decisions

    def _enrich_triage_decisions(self, decisions: list[Decision], clusters: dict[str, list[ParsedItem]]) -> list[Decision]:
        for decision in decisions:
            items = clusters.get(decision.target, [])
            if not items:
                continue
            decision.metadata["cluster_size"] = len(items)
            decision.metadata["sample_tests"] = [item.name for item in items[:3]]
            decision.metadata["sample_messages"] = [item.context.get("message", "") for item in items[:2]]
            decision.metadata["evidence"] = "; ".join(
                f"{item.name}: {item.context.get('message', '')}" for item in items[:2]
            )
            decision.metadata["rank_basis"] = decision.metadata.get("rank_basis") or self._triage_rank_basis(len(items))
            decision.metadata["workflow_stage"] = "regression_triage"
        return decisions

    def _cluster_failures(self, failures: list[ParsedItem]) -> dict[str, list[ParsedItem]]:
        grouped: dict[str, list[ParsedItem]] = defaultdict(list)
        for item in failures:
            message = item.context.get("message", "")
            signature = "timeout" if "timeout" in message.lower() else "assertion" if "assert" in message.lower() else item.name.split("_test")[0]
            grouped[signature].append(item)
        return dict(sorted(grouped.items(), key=lambda entry: len(entry[1]), reverse=True))

    def _cluster_reason(self, cluster_name: str) -> str:
        if "timeout" in cluster_name:
            return "handshake timing or blocked progress conditions"
        if "assert" in cluster_name:
            return "protocol assertions or signal ordering"
        return "one shared stimulus family or RTL subsystem"

    def _coverage_cause(self, item: ParsedItem) -> str:
        name = item.name.lower()
        if "iso" in name:
            return "The constrained-random space likely never enables isochronous traffic, so the scenario remains unreachable."
        if "interrupt" in name:
            return "Interrupt timing is probably under-constrained, which leaves this corner case lightly exercised."
        if "error" in name:
            return "Negative-path error injection is missing or gated off, so the recovery logic is not being hit."
        if "concurrent" in name or "conflict" in name:
            return "The bench appears to exercise single-channel behavior only, leaving concurrency interactions uncovered."
        return "A meaningful stimulus condition is likely absent from the current scenario matrix."

    def _coverage_action(self, item: ParsedItem) -> str:
        group = item.context.get("group", "this cover group")
        name = item.name.lower()
        if "iso" in name:
            return f"Add a directed UVM sequence that forces isochronous traffic within {group} during an active data path window."
        if "interrupt" in name:
            return f"Relax constraints to overlap interrupt activity with the {group} scenario and run targeted seeds."
        if "error" in name:
            return f"Inject an explicit protocol error path in {group} and capture the expected recovery sequence."
        if "concurrent" in name or "conflict" in name:
            return f"Modify the driver to enable concurrent actors inside {group} and randomise arbitration ordering."
        return f"Create a focused directed test around {item.name} and bias stimulus toward the missing state transition."

    def _coverage_rank_basis(self, item: ParsedItem) -> str:
        if item.hits in {None, 0}:
            return "Zero-hit coverage gaps are prioritized first because they represent completely unexercised functional scenarios."
        return "Undercovered scenarios are prioritized after zero-hit bins because they indicate partial but incomplete stimulus coverage."

    def _coverage_recommendation_summary(self, decisions: list[Decision]) -> str:
        if not decisions:
            return "No material closure actions were generated for this artifact."
        targets = ", ".join(decision.target for decision in decisions[:3])
        return (
            f"Generated {len(decisions)} engineer-reviewable closure actions. "
            f"Top recommendation targets: {targets}."
        )

    def _triage_rank_basis(self, cluster_size: int) -> str:
        if cluster_size >= 10:
            return "Large failure clusters are ranked first because one shared root cause can unblock the biggest portion of the regression."
        if cluster_size >= 3:
            return "Medium-sized clusters are prioritized because they are likely real issues with meaningful blast radius."
        return "Smaller clusters are kept in the queue but ranked below broad-impact regressions."

    def _triage_recommendation_summary(self, decisions: list[Decision]) -> str:
        if not decisions:
            return "No regression investigation actions were generated for this run."
        targets = ", ".join(decision.target for decision in decisions[:3])
        return (
            f"Generated {len(decisions)} recommended investigations and added them to the review queue. "
            f"Top targets: {targets}."
        )
