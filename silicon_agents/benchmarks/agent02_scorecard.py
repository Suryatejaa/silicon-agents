"""Benchmark scorecard logic for Agent 02."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from silicon_agents.core.schemas import Decision


@dataclass(frozen=True)
class BenchmarkFinding:
    """Expected finding for a benchmark artifact."""

    id: str
    label: str
    aliases: tuple[str, ...]
    expected_priority: str
    recommended_first: bool = False


@dataclass(frozen=True)
class BenchmarkDefinition:
    """Definition for one Agent 02 benchmark artifact."""

    id: str
    title: str
    workflow: str
    artifact_name: str
    manual_review_minutes: int
    findings: tuple[BenchmarkFinding, ...] = field(default_factory=tuple)


def _normalize(text: str) -> str:
    lowered = text.strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")


AGENT02_BENCHMARKS: dict[str, BenchmarkDefinition] = {
    "ate_parametric_sample.csv": BenchmarkDefinition(
        id="ate_parametric_sample.csv",
        title="Mobile SoC Yield Benchmark · ATE Parametric Review",
        workflow="ATE anomaly and binning review",
        artifact_name="ate_parametric_sample.csv",
        manual_review_minutes=85,
        findings=(
            BenchmarkFinding(
                id="c005",
                label="C005",
                aliases=("c005",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="c008",
                label="C008",
                aliases=("c008",),
                expected_priority="HIGH",
            ),
        ),
    ),
    "spc_trend_sample.csv": BenchmarkDefinition(
        id="spc_trend_sample.csv",
        title="PMIC SPC Benchmark · Leakage Drift Review",
        workflow="SPC drift monitoring",
        artifact_name="spc_trend_sample.csv",
        manual_review_minutes=70,
        findings=(
            BenchmarkFinding(
                id="avg_leakage_ua",
                label="avg_leakage_ua",
                aliases=("avg_leakage_ua", "average_leakage", "leakage_drift"),
                expected_priority="HIGH",
                recommended_first=True,
            ),
        ),
    ),
}


def list_agent02_benchmarks() -> list[dict[str, object]]:
    """Return benchmark metadata for the frontend."""

    return [
        {
            "id": benchmark.id,
            "title": benchmark.title,
            "workflow": benchmark.workflow,
            "artifact_name": benchmark.artifact_name,
            "manual_review_minutes": benchmark.manual_review_minutes,
            "expected_findings": len(benchmark.findings),
        }
        for benchmark in AGENT02_BENCHMARKS.values()
    ]


def get_agent02_benchmark(benchmark_id: str) -> BenchmarkDefinition | None:
    """Look up one benchmark definition."""

    return AGENT02_BENCHMARKS.get(benchmark_id)


def evaluate_agent02_benchmark(benchmark_id: str, decisions: list[Decision]) -> dict[str, object]:
    """Evaluate an Agent 02 run against a benchmark artifact."""

    benchmark = get_agent02_benchmark(benchmark_id)
    if benchmark is None:
        raise KeyError(f"Unknown benchmark: {benchmark_id}")

    matched_by_finding: dict[str, Decision] = {}
    for decision in decisions:
        target = _normalize(decision.target)
        for finding in benchmark.findings:
            aliases = {_normalize(alias) for alias in finding.aliases}
            aliases.add(_normalize(finding.label))
            if target in aliases and finding.id not in matched_by_finding:
                matched_by_finding[finding.id] = decision

    matched_ids = set(matched_by_finding)
    expected_ids = {finding.id for finding in benchmark.findings}
    missed = [finding.label for finding in benchmark.findings if finding.id not in matched_ids]

    recall = len(matched_ids) / len(expected_ids) if expected_ids else 1.0

    expected_high = [finding for finding in benchmark.findings if finding.expected_priority == "HIGH"]
    matched_high = [
        finding.id
        for finding in expected_high
        if finding.id in matched_by_finding and matched_by_finding[finding.id].priority == "HIGH"
    ]
    high_priority_alignment = len(matched_high) / len(expected_high) if expected_high else 1.0

    first_candidates = {finding.id for finding in benchmark.findings if finding.recommended_first}
    first_action_alignment = 0.0
    if decisions:
        first_target = _normalize(decisions[0].target)
        for finding in benchmark.findings:
            aliases = {_normalize(alias) for alias in finding.aliases}
            aliases.add(_normalize(finding.label))
            if finding.id in first_candidates and first_target in aliases:
                first_action_alignment = 1.0
                break

    evidence_supported = sum(1 for decision in decisions if str(decision.metadata.get("evidence", "")).strip() or str(decision.rationale).strip())
    evidence_coverage = evidence_supported / len(decisions) if decisions else 0.0

    review_minutes = max(8, 10 + len(decisions) * 7)
    review_time_saved_minutes = max(0, benchmark.manual_review_minutes - review_minutes)

    overall_score = round(
        (
            recall * 0.4
            + high_priority_alignment * 0.25
            + first_action_alignment * 0.15
            + evidence_coverage * 0.2
        )
        * 100
    )

    notes: list[str] = []
    if missed:
        notes.append(f"Missed benchmark findings: {', '.join(missed)}.")
    if first_action_alignment < 1.0:
        notes.append("Top-ranked action did not align with the benchmark's preferred first investigation.")
    if evidence_coverage < 1.0:
        notes.append("Some decisions were missing explicit supporting context or rationale.")
    if not notes:
        notes.append("Run aligned well with the benchmark expectations and included visible supporting rationale.")

    return {
        "benchmark_id": benchmark.id,
        "title": benchmark.title,
        "workflow": benchmark.workflow,
        "artifact_name": benchmark.artifact_name,
        "manual_review_minutes": benchmark.manual_review_minutes,
        "assisted_review_minutes": review_minutes,
        "review_time_saved_minutes": review_time_saved_minutes,
        "matched_findings": [
            {
                "expected": next(finding.label for finding in benchmark.findings if finding.id == finding_id),
                "observed_target": decision.target,
                "priority": decision.priority,
                "evidence": str(decision.metadata.get("evidence", decision.rationale)),
            }
            for finding_id, decision in matched_by_finding.items()
        ],
        "missed_findings": missed,
        "metrics": {
            "overall_score": overall_score,
            "findings_recall": round(recall, 2),
            "high_priority_alignment": round(high_priority_alignment, 2),
            "first_action_alignment": round(first_action_alignment, 2),
            "evidence_coverage": round(evidence_coverage, 2),
            "matched_expected_findings": len(matched_ids),
            "expected_findings": len(expected_ids),
        },
        "notes": notes,
    }
