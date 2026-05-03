"""Coverage report parsing for VCS and Xcelium-like logs."""

from __future__ import annotations

import re

from silicon_agents.core.schemas import ParsedItem, ParsedReport, ParsedSummary


COVERGROUP_PATTERNS = [
    re.compile(
        r"Cover\s*Group\s*:\s*(?P<name>.+?)(?:\s*\[(?:Coverage|Covered)\s*[:=]\s*(?P<pct>\d+(?:\.\d+)?)\s*%?\])?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"Covergroup\s+(?P<name>.+?)(?:\s+(?:Coverage|Covered)\s*[:=]\s*(?P<pct>\d+(?:\.\d+)?)\s*%?)?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:CG|Covergroup)\s*[:=]?\s*(?P<name>.+?)(?:\s*[-|]\s*(?:Coverage|Covered)\s*[:=]?\s*(?P<pct>\d+(?:\.\d+)?)\s*%?)?$",
        re.IGNORECASE,
    ),
]
BIN_PATTERNS = [
    re.compile(
        r"(?:bins?\s+)?(?P<name>[\w./:-]+)\s*[:=]\s*(?P<hits>\d+)\s*hits?(?:\s+(?P<status>[A-Z_ ]+))?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:bin\s+)?(?P<name>[\w./:-]+)\s*-\s*(?P<hits>\d+)\s*hits?(?:\s+(?P<status>[A-Z_ ]+))?",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:bins?\s+)?(?P<name>[\w./:-]+)\s*[:=]\s*(?P<hits>\d+)(?:\s+(?P<status>PASS|FAIL|GAP|MISS|BELOW THRESHOLD|UNCOVERED|UNDERCOVERED)[A-Z_ ]*)?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<name>[\w./:-]+)\s+\((?P<hits>\d+)\)(?:\s+(?P<status>PASS|FAIL|GAP|MISS|BELOW THRESHOLD|UNCOVERED|UNDERCOVERED)[A-Z_ ]*)?$",
        re.IGNORECASE,
    ),
]
PCT_RE = re.compile(r"(?:Coverage|Covered)\s*[:=]\s*(?P<pct>\d+(?:\.\d+)?)\s*%?", re.IGNORECASE)


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
    warnings: list[str] = []
    matched_groups = 0
    matched_bins = 0

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        group_match = next((pattern.search(stripped) for pattern in COVERGROUP_PATTERNS if pattern.search(stripped)), None)
        if group_match:
            current_group = group_match.group("name").strip()
            pct = group_match.group("pct")
            if pct is None:
                pct_match = PCT_RE.search(stripped)
                pct = pct_match.group("pct") if pct_match else None
            if pct is not None:
                groups[current_group] = float(pct)
            matched_groups += 1
            continue
        if current_group not in groups:
            pct_match = PCT_RE.search(stripped)
            if pct_match:
                groups[current_group] = float(pct_match.group("pct"))
                continue
        bin_match = next((pattern.search(stripped) for pattern in BIN_PATTERNS if pattern.search(stripped)), None)
        if bin_match:
            hits = int(bin_match.group("hits"))
            lowered = stripped.lower()
            status = "covered" if hits > 0 else "uncovered"
            if any(token in lowered for token in {"below threshold", "undercovered"}):
                status = "undercovered"
            elif hits == 0 and any(token in lowered for token in {"fail", "gap", "miss", "uncovered"}):
                status = "uncovered"
            item_name = bin_match.group("name").strip()
            matched_bins += 1
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
    if matched_groups == 0:
        warnings.append("No explicit covergroup headers were recognized. Group names may be inferred or incomplete.")
    if matched_bins == 0:
        warnings.append("No bin rows were recognized. Review the artifact format before trusting the output.")
    elif matched_bins < 3:
        warnings.append("Only a small number of bin rows were recognized. Validate that the report format matches the parser assumptions.")

    confidence = _estimate_coverage_confidence(tool, matched_groups, matched_bins, warnings)

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
        metadata={
            "tool": tool,
            "groups": list(groups.keys()),
            "parser_format": tool,
            "parser_confidence": confidence,
            "parser_warnings": warnings,
            "matched_groups": matched_groups,
            "matched_bins": matched_bins,
        },
        raw_excerpt=raw[:1000],
    )


def _estimate_coverage_confidence(tool: str, matched_groups: int, matched_bins: int, warnings: list[str]) -> float:
    confidence = 0.35
    if tool != "unknown":
        confidence += 0.15
    if matched_groups >= 1:
        confidence += 0.2
    if matched_groups >= 2:
        confidence += 0.05
    if matched_bins >= 3:
        confidence += 0.15
    if matched_bins >= 8:
        confidence += 0.05
    confidence -= min(0.2, 0.08 * len(warnings))
    return max(0.05, min(0.99, round(confidence, 2)))
