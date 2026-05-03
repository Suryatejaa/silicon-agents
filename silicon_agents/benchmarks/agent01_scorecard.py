"""Benchmark scorecard logic for Agent 01."""

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
    """Definition for one benchmark artifact."""

    id: str
    title: str
    workflow: str
    artifact_name: str
    manual_review_minutes: int
    findings: tuple[BenchmarkFinding, ...] = field(default_factory=tuple)


def _normalize(text: str) -> str:
    lowered = text.strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")


AGENT01_BENCHMARKS: dict[str, BenchmarkDefinition] = {
    "coverage_vcs_sample.log": BenchmarkDefinition(
        id="coverage_vcs_sample.log",
        title="USB Controller Benchmark · VCS Coverage",
        workflow="Coverage closure",
        artifact_name="coverage_vcs_sample.log",
        manual_review_minutes=95,
        findings=(
            BenchmarkFinding(
                id="isochronous_transfer",
                label="isochronous_transfer",
                aliases=("isochronous_transfer",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="control_transfer_error",
                label="control_transfer_error",
                aliases=("control_transfer_error",),
                expected_priority="HIGH",
            ),
            BenchmarkFinding(
                id="concurrent_dma_conflict",
                label="concurrent_dma_conflict",
                aliases=("concurrent_dma_conflict",),
                expected_priority="HIGH",
            ),
            BenchmarkFinding(
                id="dma_during_interrupt",
                label="dma_during_interrupt",
                aliases=("dma_during_interrupt",),
                expected_priority="MEDIUM",
            ),
        ),
    ),
    "coverage_xcelium_sample.log": BenchmarkDefinition(
        id="coverage_xcelium_sample.log",
        title="Power Mode Benchmark · Xcelium Coverage",
        workflow="Coverage closure",
        artifact_name="coverage_xcelium_sample.log",
        manual_review_minutes=65,
        findings=(
            BenchmarkFinding(
                id="brownout_recovery",
                label="brownout_recovery",
                aliases=("brownout_recovery",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="low_voltage_interrupt",
                label="low_voltage_interrupt",
                aliases=("low_voltage_interrupt",),
                expected_priority="MEDIUM",
            ),
        ),
    ),
    "coverage_pcie_dma_sample.log": BenchmarkDefinition(
        id="coverage_pcie_dma_sample.log",
        title="PCIe DMA Benchmark · VCS Coverage",
        workflow="Coverage closure",
        artifact_name="coverage_pcie_dma_sample.log",
        manual_review_minutes=105,
        findings=(
            BenchmarkFinding(
                id="posted_write_boundary",
                label="posted_write_boundary",
                aliases=("posted_write_boundary",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="completion_timeout_recovery",
                label="completion_timeout_recovery",
                aliases=("completion_timeout_recovery",),
                expected_priority="HIGH",
            ),
            BenchmarkFinding(
                id="concurrent_tag_reuse",
                label="concurrent_tag_reuse",
                aliases=("concurrent_tag_reuse",),
                expected_priority="HIGH",
            ),
            BenchmarkFinding(
                id="msi_backpressure",
                label="msi_backpressure",
                aliases=("msi_backpressure",),
                expected_priority="MEDIUM",
            ),
        ),
    ),
    "coverage_lpddr_refresh_sample.log": BenchmarkDefinition(
        id="coverage_lpddr_refresh_sample.log",
        title="LPDDR Controller Benchmark · Xcelium Coverage",
        workflow="Coverage closure",
        artifact_name="coverage_lpddr_refresh_sample.log",
        manual_review_minutes=88,
        findings=(
            BenchmarkFinding(
                id="self_refresh_exit",
                label="self_refresh_exit",
                aliases=("self_refresh_exit",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="bank_conflict_recovery",
                label="bank_conflict_recovery",
                aliases=("bank_conflict_recovery",),
                expected_priority="HIGH",
            ),
            BenchmarkFinding(
                id="refresh_during_throttle",
                label="refresh_during_throttle",
                aliases=("refresh_during_throttle",),
                expected_priority="MEDIUM",
            ),
        ),
    ),
    "coverage_noc_qos_sample.log": BenchmarkDefinition(
        id="coverage_noc_qos_sample.log",
        title="NoC QoS Benchmark · VCS Coverage",
        workflow="Coverage closure",
        artifact_name="coverage_noc_qos_sample.log",
        manual_review_minutes=92,
        findings=(
            BenchmarkFinding(
                id="starvation_prevention",
                label="starvation_prevention",
                aliases=("starvation_prevention",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="credit_exhaustion_backoff",
                label="credit_exhaustion_backoff",
                aliases=("credit_exhaustion_backoff",),
                expected_priority="HIGH",
            ),
            BenchmarkFinding(
                id="qos_boost_demotion",
                label="qos_boost_demotion",
                aliases=("qos_boost_demotion",),
                expected_priority="MEDIUM",
            ),
        ),
    ),
    "coverage_secure_boot_sample.log": BenchmarkDefinition(
        id="coverage_secure_boot_sample.log",
        title="Secure Boot Benchmark · VCS Coverage",
        workflow="Coverage closure",
        artifact_name="coverage_secure_boot_sample.log",
        manual_review_minutes=96,
        findings=(
            BenchmarkFinding(
                id="rollback_protection_fault",
                label="rollback_protection_fault",
                aliases=("rollback_protection_fault",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="key_revocation_path",
                label="key_revocation_path",
                aliases=("key_revocation_path",),
                expected_priority="HIGH",
            ),
            BenchmarkFinding(
                id="debug_unlock_denied",
                label="debug_unlock_denied",
                aliases=("debug_unlock_denied",),
                expected_priority="MEDIUM",
            ),
        ),
    ),
    "regression_sample.log": BenchmarkDefinition(
        id="regression_sample.log",
        title="Nightly Regression Benchmark",
        workflow="Regression triage",
        artifact_name="regression_sample.log",
        manual_review_minutes=120,
        findings=(
            BenchmarkFinding(
                id="timeout_cluster",
                label="timeout",
                aliases=("timeout", "usb_bulk_transfer", "usb_bulk_transfer_timeout"),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="assertion_cluster",
                label="assertion",
                aliases=("assertion", "arb_grant", "dma_single_channel"),
                expected_priority="MEDIUM",
            ),
        ),
    ),
    "regression_pcie_dma_sample.log": BenchmarkDefinition(
        id="regression_pcie_dma_sample.log",
        title="PCIe DMA Regression Benchmark",
        workflow="Regression triage",
        artifact_name="regression_pcie_dma_sample.log",
        manual_review_minutes=135,
        findings=(
            BenchmarkFinding(
                id="completion_replay",
                label="completion_replay",
                aliases=("completion_replay",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="tag_credit",
                label="tag_credit",
                aliases=("tag_credit",),
                expected_priority="MEDIUM",
            ),
        ),
    ),
    "regression_audio_dsp_sample.log": BenchmarkDefinition(
        id="regression_audio_dsp_sample.log",
        title="Audio DSP Regression Benchmark",
        workflow="Regression triage",
        artifact_name="regression_audio_dsp_sample.log",
        manual_review_minutes=118,
        findings=(
            BenchmarkFinding(
                id="frame_overrun",
                label="frame_overrun",
                aliases=("frame_overrun",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="coeff_update",
                label="coeff_update",
                aliases=("coeff_update",),
                expected_priority="MEDIUM",
            ),
        ),
    ),
    "regression_secure_boot_sample.log": BenchmarkDefinition(
        id="regression_secure_boot_sample.log",
        title="Secure Boot Regression Benchmark",
        workflow="Regression triage",
        artifact_name="regression_secure_boot_sample.log",
        manual_review_minutes=126,
        findings=(
            BenchmarkFinding(
                id="secure_boot_hash",
                label="secure_boot_hash",
                aliases=("secure_boot_hash",),
                expected_priority="HIGH",
                recommended_first=True,
            ),
            BenchmarkFinding(
                id="rollback_counter",
                label="rollback_counter",
                aliases=("rollback_counter",),
                expected_priority="MEDIUM",
            ),
        ),
    ),
}


def list_agent01_benchmarks() -> list[dict[str, object]]:
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
        for benchmark in AGENT01_BENCHMARKS.values()
    ]


def get_agent01_benchmark(benchmark_id: str) -> BenchmarkDefinition | None:
    """Look up one benchmark definition."""

    return AGENT01_BENCHMARKS.get(benchmark_id)


def evaluate_agent01_benchmark(benchmark_id: str, decisions: list[Decision]) -> dict[str, object]:
    """Evaluate an Agent 01 run against a benchmark artifact."""

    benchmark = get_agent01_benchmark(benchmark_id)
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

    evidence_supported = sum(1 for decision in decisions if str(decision.metadata.get("evidence", "")).strip())
    evidence_coverage = evidence_supported / len(decisions) if decisions else 0.0

    review_minutes = max(8, 12 + len(decisions) * 6)
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
        notes.append("Some decisions were missing explicit artifact evidence.")
    if not notes:
        notes.append("Run aligned well with the benchmark expectations and included visible supporting evidence.")

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
                "evidence": str(decision.metadata.get("evidence", "")),
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
