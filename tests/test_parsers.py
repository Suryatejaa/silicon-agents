import unittest

from silicon_agents.parsers.ate_parser import parse_ate_csv, parse_spc_csv
from silicon_agents.parsers.coverage_parser import detect_coverage_format, parse_coverage_report
from silicon_agents.parsers.regression_parser import parse_regression_log


class CoverageParserTests(unittest.TestCase):
    def test_parse_coverage_report_detects_gaps(self) -> None:
        raw = """
        Cover Group: usb_transfer_type [Coverage: 62.5%]
        bins bulk_transfer: 847 hits PASS
        bins isochronous_transfer: 0 hits FAIL gap
        bins dma_during_interrupt: 3 hits FAIL below threshold
        """
        parsed = parse_coverage_report(raw)
        self.assertEqual(parsed.type, "coverage")
        self.assertEqual(parsed.summary.total, 3)
        self.assertEqual(parsed.summary.uncovered, 2)

    def test_detect_xcelium_format(self) -> None:
        self.assertEqual(detect_coverage_format("Tool: Cadence Xcelium xrun"), "xcelium")


class RegressionParserTests(unittest.TestCase):
    def test_parse_regression_log_counts_failures(self) -> None:
        raw = """
        Total: 10 | PASSED: 6 | FAILED: 4
        usb_test_001 FAIL timeout at cycle 42
        usb_test_002 PASS
        dma_test_003 FAIL assertion: arb_grant
        """
        parsed = parse_regression_log(raw)
        self.assertEqual(parsed.summary.total, 10)
        self.assertEqual(parsed.summary.failed, 4)


class YieldParserTests(unittest.TestCase):
    def test_parse_ate_csv_reads_rows(self) -> None:
        raw = "chip_id,max_freq_ghz,leakage_ua,vmin_mv,bin,pass\nC001,3.8,140,780,1,PASS\nC002,2.1,650,980,3,FAIL\n"
        parsed = parse_ate_csv(raw)
        self.assertEqual(parsed.type, "ate")
        self.assertEqual(parsed.summary.total, 2)
        self.assertEqual(parsed.summary.failed, 1)

    def test_parse_spc_csv_reads_lots(self) -> None:
        raw = "lot_id,date,avg_leakage_ua,yield_pct\nLOT_001,2026-04-01,145,94.2\nLOT_002,2026-04-02,150,93.9\n"
        parsed = parse_spc_csv(raw)
        self.assertEqual(parsed.type, "spc")
        self.assertEqual(parsed.summary.total, 2)

