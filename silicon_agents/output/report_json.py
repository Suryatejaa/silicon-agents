"""Machine-readable report formatting."""

from __future__ import annotations

from silicon_agents.core.schemas import Decision, ParsedReport


def render_json_report(parsed: ParsedReport, decisions: list[Decision]) -> dict:
    return {
        "summary": parsed.summary.model_dump(),
        "metadata": parsed.metadata,
        "decisions": [decision.model_dump() for decision in decisions],
    }

