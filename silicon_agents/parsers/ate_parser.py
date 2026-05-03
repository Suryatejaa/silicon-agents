"""ATE and SPC parsers."""

from __future__ import annotations

import csv
import io
from typing import Optional

from silicon_agents.core.schemas import ParsedItem, ParsedReport, ParsedSummary


def _to_float(value: Optional[str]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_ate_csv(raw: str) -> ParsedReport:
    reader = csv.DictReader(io.StringIO(raw.strip()))
    items: list[ParsedItem] = []
    anomalies = 0
    passed = 0
    failed = 0
    warnings: list[str] = []
    fieldnames = reader.fieldnames or []

    for idx, row in enumerate(reader):
        chip_id = row.get("chip_id") or row.get("chip") or f"chip_{idx + 1}"
        freq = _to_float(row.get("max_freq_ghz"))
        leakage = _to_float(row.get("leakage_ua"))
        vmin = _to_float(row.get("vmin_mv"))
        bin_assignment = row.get("bin")
        pass_flag = (row.get("pass") or row.get("result") or "").strip().upper()
        status = "passed" if pass_flag in {"PASS", "PASSED", "1", "TRUE"} else "failed"
        if status == "passed":
            passed += 1
        else:
            failed += 1
            anomalies += 1
        items.append(
            ParsedItem(
                id=chip_id,
                name=chip_id,
                status=status,
                value=freq,
                bin_assignment=bin_assignment,
                context={"max_freq_ghz": freq, "leakage_ua": leakage, "vmin_mv": vmin, "row": row},
            )
        )

    if not fieldnames:
        warnings.append("No CSV headers were recognized in the ATE artifact.")
    elif len(fieldnames) < 4:
        warnings.append("Only a partial ATE column set was recognized. Review the uploaded CSV format.")
    if not items:
        warnings.append("No ATE rows were parsed from the artifact.")

    return ParsedReport(
        type="ate",
        agent="yield",
        summary=ParsedSummary(total=len(items), passed=passed, failed=failed, anomalies=anomalies),
        items=items,
        metadata={
            "columns": fieldnames,
            "parser_format": "ate_csv",
            "parser_confidence": _estimate_tabular_confidence(fieldnames, len(items), warnings),
            "parser_warnings": warnings,
        },
        raw_excerpt=raw[:1000],
    )


def parse_spc_csv(raw: str) -> ParsedReport:
    reader = csv.DictReader(io.StringIO(raw.strip()))
    items: list[ParsedItem] = []
    warnings: list[str] = []
    fieldnames = reader.fieldnames or []

    for idx, row in enumerate(reader):
        lot_id = row.get("lot_id") or f"LOT_{idx + 1:03d}"
        leakage = _to_float(row.get("avg_leakage_ua"))
        yield_pct = _to_float(row.get("yield_pct"))
        items.append(
            ParsedItem(
                id=lot_id,
                name=lot_id,
                status="observed",
                value=leakage,
                context={"date": row.get("date"), "avg_leakage_ua": leakage, "yield_pct": yield_pct, "row": row},
            )
        )

    if not fieldnames:
        warnings.append("No CSV headers were recognized in the SPC artifact.")
    elif len(fieldnames) < 3:
        warnings.append("Only a partial SPC column set was recognized. Review the uploaded CSV format.")
    if not items:
        warnings.append("No SPC rows were parsed from the artifact.")

    return ParsedReport(
        type="spc",
        agent="yield",
        summary=ParsedSummary(total=len(items)),
        items=items,
        metadata={
            "columns": fieldnames,
            "parser_format": "spc_csv",
            "parser_confidence": _estimate_tabular_confidence(fieldnames, len(items), warnings),
            "parser_warnings": warnings,
        },
        raw_excerpt=raw[:1000],
    )


def _estimate_tabular_confidence(fieldnames: list[str], item_count: int, warnings: list[str]) -> float:
    confidence = 0.45
    if fieldnames:
        confidence += 0.25
    if len(fieldnames) >= 4:
        confidence += 0.15
    if item_count >= 1:
        confidence += 0.1
    if item_count >= 5:
        confidence += 0.05
    confidence -= min(0.2, 0.08 * len(warnings))
    return max(0.05, min(0.99, round(confidence, 2)))
