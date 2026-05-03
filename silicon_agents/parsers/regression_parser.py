"""Regression log parsing."""

from __future__ import annotations

import re

from silicon_agents.core.schemas import ParsedItem, ParsedReport, ParsedSummary


TOTALS_PATTERNS = [
    re.compile(r"Total:\s*(?P<total>\d+)\s*\|\s*PASSED:\s*(?P<passed>\d+)\s*\|\s*FAILED:\s*(?P<failed>\d+)", re.IGNORECASE),
    re.compile(r"TOTAL\s*[:=]?\s*(?P<total>\d+).+?PASS(?:ED)?\s*[:=]?\s*(?P<passed>\d+).+?FAIL(?:ED)?\s*[:=]?\s*(?P<failed>\d+)", re.IGNORECASE),
    re.compile(r"Summary\s*[:=-]?\s*total\s*[:=]?\s*(?P<total>\d+).+?pass(?:ed)?\s*[:=]?\s*(?P<passed>\d+).+?fail(?:ed)?\s*[:=]?\s*(?P<failed>\d+)", re.IGNORECASE),
]
RESULT_PATTERNS = [
    re.compile(r"(?P<name>[\w./:-]+)\s+(?P<status>PASS|FAIL)\s*(?P<message>.*)", re.IGNORECASE),
    re.compile(r"(?P<status>PASS|FAIL)\s+(?P<name>[\w./:-]+)\s*(?P<message>.*)", re.IGNORECASE),
    re.compile(r"(?:TEST\s*[:=-]?\s*)?(?P<name>[\w./:-]+)\s*[-|:]\s*(?P<status>PASS|FAIL)\s*(?P<message>.*)", re.IGNORECASE),
]


def parse_regression_log(raw: str) -> ParsedReport:
    total = passed = failed = 0
    items: list[ParsedItem] = []
    warnings: list[str] = []
    matched_totals = 0
    matched_tests = 0

    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        totals_match = next((pattern.search(stripped) for pattern in TOTALS_PATTERNS if pattern.search(stripped)), None)
        if totals_match:
            total = int(totals_match.group("total"))
            passed = int(totals_match.group("passed"))
            failed = int(totals_match.group("failed"))
            matched_totals += 1
            continue
        fail_match = next((pattern.search(stripped) for pattern in RESULT_PATTERNS if pattern.search(stripped)), None)
        if fail_match:
            status = fail_match.group("status").upper()
            matched_tests += 1
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
    if matched_totals == 0:
        warnings.append("No regression totals line was recognized. Counts were inferred from individual test rows.")
    if matched_tests == 0:
        warnings.append("No PASS/FAIL test rows were recognized. Review the regression log format before trusting the output.")

    confidence = _estimate_regression_confidence(matched_totals, matched_tests, warnings)

    return ParsedReport(
        type="regression",
        agent="verification",
        summary=ParsedSummary(total=total, passed=passed, failed=failed),
        items=items,
        metadata={
            "clusters_candidate_count": failed,
            "parser_format": "regression_log",
            "parser_confidence": confidence,
            "parser_warnings": warnings,
            "matched_totals": matched_totals,
            "matched_tests": matched_tests,
        },
        raw_excerpt=raw[:1000],
    )


def _estimate_regression_confidence(matched_totals: int, matched_tests: int, warnings: list[str]) -> float:
    confidence = 0.4
    if matched_totals:
        confidence += 0.25
    if matched_tests >= 1:
        confidence += 0.2
    if matched_tests >= 5:
        confidence += 0.1
    confidence -= min(0.2, 0.08 * len(warnings))
    return max(0.05, min(0.99, round(confidence, 2)))
