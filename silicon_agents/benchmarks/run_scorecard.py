"""Run-level scorecard helpers for persisted history."""

from __future__ import annotations

from silicon_agents.benchmarks.agent01_scorecard import get_agent01_benchmark, evaluate_agent01_benchmark
from silicon_agents.benchmarks.agent02_scorecard import get_agent02_benchmark, evaluate_agent02_benchmark
from silicon_agents.core.schemas import Decision


def evaluate_run_scorecard(agent: str, artifact_name: str | None, decisions: list[Decision]) -> dict[str, object]:
    artifact_key = str(artifact_name or "").strip()
    if agent == "agent01" and artifact_key and get_agent01_benchmark(artifact_key):
        result = evaluate_agent01_benchmark(artifact_key, decisions)
        return {
            "title": result["title"],
            "score": f'{result["metrics"]["overall_score"]}/100',
            "notes": list(result["notes"]),
            "mode": "benchmark",
        }
    if agent == "agent02" and artifact_key and get_agent02_benchmark(artifact_key):
        result = evaluate_agent02_benchmark(artifact_key, decisions)
        return {
            "title": result["title"],
            "score": f'{result["metrics"]["overall_score"]}/100',
            "notes": list(result["notes"]),
            "mode": "benchmark",
        }
    return _evaluate_live_scorecard(agent, artifact_name, decisions)


def _evaluate_live_scorecard(agent: str, artifact_name: str | None, decisions: list[Decision]) -> dict[str, object]:
    evidence_backed = sum(1 for item in decisions if str(item.metadata.get("evidence", "")).strip())
    actionable = sum(1 for item in decisions if str(item.action).strip() and str(item.rationale).strip())
    high_count = sum(1 for item in decisions if item.priority == "HIGH")
    decision_count = len(decisions)

    evidence_coverage = evidence_backed / decision_count if decision_count else 0.0
    actionability = actionable / decision_count if decision_count else 0.0
    queue_depth = min(1.0, decision_count / 4) if decision_count else 0.0
    priority_signal = min(1.0, (high_count + decision_count) / 6) if decision_count else 0.0

    overall_score = round(
        (
            evidence_coverage * 0.35
            + actionability * 0.3
            + queue_depth * 0.2
            + priority_signal * 0.15
        )
        * 100
    )
    title_prefix = "Live Artifact Scorecard" if agent == "agent01" else "Live Run Scorecard"
    artifact_label = artifact_name or ("Custom verification artifact" if agent == "agent01" else "Custom yield artifact")
    notes = [
        "Live score is computed from actionability, evidence coverage, and queue strength instead of a fixed benchmark."
    ]
    if decision_count:
        notes.append(f"Generated {decision_count} reviewable actions with {high_count} high-priority findings.")
    else:
        notes.append("No reviewable actions were generated from the current artifact shape.")
    return {
        "title": f"{title_prefix} · {artifact_label}",
        "score": f"{overall_score}/100",
        "notes": notes,
        "mode": "live",
    }
