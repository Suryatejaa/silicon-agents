"""Coverage report parsing for VCS and Xcelium-like logs."""

from __future__ import annotations

import re

from silicon_agents.core.schemas import ParsedItem, ParsedReport, ParsedSummary


COVERGROUP_RE = re.compile(r"Cover Group:\s*(?P<name>.+?)(?:\s*\[Coverage:\s*(?P<pct>\d+(?:\.\d+)?)%\])?$", re.IGNORECASE)
BIN_RE = re.compile(r"(?:bins?\s+)?(?P<name>[\w./:-]+)\s*:\s*(?P<hits>\d+)\s*hits?(?:\s+(?P<status>[A-Z_ ]+))?", re.IGNORECASE)


def detect_coverage_format(raw: str) -> str:
    lowered = raw.lower()
    if "xrun" in lowered or "xcelium" in lowered:
        return "xcelium"
    if "vcs" in lowered or "cover group" in lowered:
        return "vcs"
    return "unknown"


def parse_coverage_report(raw: str, fmt: str = "auto") -> ParsedReport:
    tool = detect_coverage_format(raw) if fmt == "auto" else fmt
    current_group = "ungrouped"
    items: list[ParsedItem] = []
    groups: dict[str, float] = {}

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        group_match = COVERGROUP_RE.search(stripped)
        if group_match:
            current_group = group_match.group("name").strip()
            pct = group_match.group("pct")
            if pct is not None:
                groups[current_group] = float(pct)
            continue
        bin_match = BIN_RE.search(stripped)
        if bin_match:
            hits = int(bin_match.group("hits"))
            status = "covered" if hits > 0 else "uncovered"
            if "below threshold" in stripped.lower():
                status = "undercovered"
            item_name = bin_match.group("name").strip()
            items.append(
                ParsedItem(
                    id=f"{current_group}:{item_name}",
                    name=item_name,
                    hits=hits,
                    value=hits,
                    status=status,
                    context={"group": current_group, "line": stripped},
                )
            )

    covered = sum(1 for item in items if item.status == "covered")
    uncovered = sum(1 for item in items if item.status != "covered")
    coverage_pct = round((covered / len(items)) * 100, 1) if items else 0.0
    if groups:
        coverage_pct = round(sum(groups.values()) / len(groups), 1)

    return ParsedReport(
        type="coverage",
        agent="verification",
        summary=ParsedSummary(
            total=len(items),
            covered=covered,
            uncovered=uncovered,
            coverage_pct=coverage_pct,
        ),
        items=items,
        metadata={"tool": tool, "groups": list(groups.keys())},
        raw_excerpt=raw[:1000],
    )

