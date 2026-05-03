"""Regression log parsing."""

from __future__ import annotations

import re

from silicon_agents.core.schemas import ParsedItem, ParsedReport, ParsedSummary


TOTALS_RE = re.compile(r"Total:\s*(?P<total>\d+)\s*\|\s*PASSED:\s*(?P<passed>\d+)\s*\|\s*FAILED:\s*(?P<failed>\d+)", re.IGNORECASE)
FAIL_RE = re.compile(r"(?P<name>[\w./:-]+)\s+(?P<status>PASS|FAIL)\s*(?P<message>.*)", re.IGNORECASE)


def parse_regression_log(raw: str) -> ParsedReport:
    total = passed = failed = 0
    items: list[ParsedItem] = []

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        totals_match = TOTALS_RE.search(stripped)
        if totals_match:
            total = int(totals_match.group("total"))
            passed = int(totals_match.group("passed"))
            failed = int(totals_match.group("failed"))
            continue
        fail_match = FAIL_RE.search(stripped)
        if fail_match:
            status = fail_match.group("status").upper()
            items.append(
                ParsedItem(
                    id=fail_match.group("name"),
                    name=fail_match.group("name"),
                    status="failed" if status == "FAIL" else "passed",
                    context={"message": fail_match.group("message").strip(), "line": stripped},
                )
            )

    if total == 0:
        total = len(items)
        passed = sum(1 for item in items if item.status == "passed")
        failed = sum(1 for item in items if item.status == "failed")

    return ParsedReport(
        type="regression",
        agent="verification",
        summary=ParsedSummary(total=total, passed=passed, failed=failed),
        items=items,
        metadata={"clusters_candidate_count": failed},
        raw_excerpt=raw[:1000],
    )

