"""Decision ranking and deduplication."""

from __future__ import annotations

from silicon_agents.core.schemas import Decision


def sort_decisions(decisions: list[Decision]) -> list[Decision]:
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(decisions, key=lambda item: (order[item.priority], -item.confidence, item.target))


def deduplicate_decisions(decisions: list[Decision]) -> list[Decision]:
    deduped: list[Decision] = []
    seen: set[tuple[str, str]] = set()
    for decision in decisions:
        key = (decision.type, decision.target)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(decision)
    return deduped

