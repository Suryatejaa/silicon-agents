import unittest

from silicon_agents.benchmarks.agent01_scorecard import evaluate_agent01_benchmark
from silicon_agents.benchmarks.agent02_scorecard import evaluate_agent02_benchmark
from silicon_agents.core.schemas import Decision


class Agent01BenchmarkTests(unittest.TestCase):
    def test_coverage_benchmark_scores_expected_findings(self) -> None:
        decisions = [
            Decision(
                id="D001",
                project_id="bench-test",
                type="coverage_gap",
                target="isochronous_transfer",
                action="Force isochronous traffic in a directed sequence.",
                rationale="Gap remains at zero hits.",
                priority="HIGH",
                confidence=0.91,
                effort="2hrs",
                metadata={"evidence": "bins isochronous_transfer: 0 hits FAIL gap"},
            ),
            Decision(
                id="D002",
                project_id="bench-test",
                type="coverage_gap",
                target="control_transfer_error",
                action="Inject negative-path control transfer errors.",
                rationale="Recovery path is uncovered.",
                priority="HIGH",
                confidence=0.88,
                effort="2hrs",
                metadata={"evidence": "bins control_transfer_error: 0 hits FAIL gap"},
            ),
            Decision(
                id="D003",
                project_id="bench-test",
                type="coverage_gap",
                target="concurrent_dma_conflict",
                action="Enable multi-channel contention stimulus.",
                rationale="Concurrency scenario is missing.",
                priority="HIGH",
                confidence=0.85,
                effort="2hrs",
                metadata={"evidence": "bins concurrent_dma_conflict: 0 hits FAIL gap"},
            ),
            Decision(
                id="D004",
                project_id="bench-test",
                type="coverage_gap",
                target="dma_during_interrupt",
                action="Overlap interrupt windows with DMA arbitration.",
                rationale="Threshold is still low.",
                priority="MEDIUM",
                confidence=0.78,
                effort="30min",
                metadata={"evidence": "bins dma_during_interrupt: 3 hits FAIL below threshold"},
            ),
        ]

        result = evaluate_agent01_benchmark("coverage_vcs_sample.log", decisions)

        self.assertEqual(result["metrics"]["overall_score"], 100)
        self.assertEqual(result["metrics"]["matched_expected_findings"], 4)
        self.assertEqual(result["review_time_saved_minutes"], 59)

    def test_regression_benchmark_accepts_cluster_aliases(self) -> None:
        decisions = [
            Decision(
                id="T001",
                project_id="bench-test",
                type="regression_failure",
                target="usb_bulk_transfer",
                action="Inspect timeout path first.",
                rationale="Multiple tests fail at the same cycle.",
                priority="HIGH",
                confidence=0.9,
                effort="2hrs",
                metadata={"evidence": "usb_bulk_transfer_test_001 FAIL timeout at cycle 4820"},
            ),
            Decision(
                id="T002",
                project_id="bench-test",
                type="regression_failure",
                target="arb_grant",
                action="Check DMA arbitration assertion changes.",
                rationale="Assertion failures point to arbitration logic.",
                priority="MEDIUM",
                confidence=0.8,
                effort="30min",
                metadata={"evidence": "dma_single_channel_test_003 FAIL assertion: arb_grant"},
            ),
        ]

        result = evaluate_agent01_benchmark("regression_sample.log", decisions)

        self.assertEqual(result["metrics"]["matched_expected_findings"], 2)
        self.assertEqual(result["metrics"]["first_action_alignment"], 1.0)
        self.assertEqual(result["metrics"]["overall_score"], 100)


class Agent02BenchmarkTests(unittest.TestCase):
    def test_ate_benchmark_scores_expected_findings(self) -> None:
        decisions = [
            Decision(
                id="Y001",
                project_id="bench-test",
                type="bin_mismatch",
                target="C005",
                action="Review bin thresholds and reclassify this die as a premium candidate.",
                rationale="C005 meets Bin 1 guardrails on frequency and leakage but is currently assigned to Bin 2.",
                priority="HIGH",
                confidence=0.94,
                effort="30min",
                metadata={"evidence": "3.80GHz, 143uA leakage, currently assigned to Bin 2"},
            ),
            Decision(
                id="Y002",
                project_id="bench-test",
                type="yield_anomaly",
                target="C008",
                action="Escalate this chip for deeper parametric review.",
                rationale="C008 shows unusually high leakage compared with the lot baseline.",
                priority="HIGH",
                confidence=0.89,
                effort="2hrs",
                metadata={"evidence": "720uA leakage vs lot baseline"},
            ),
        ]

        result = evaluate_agent02_benchmark("ate_parametric_sample.csv", decisions)

        self.assertEqual(result["metrics"]["overall_score"], 100)
        self.assertEqual(result["metrics"]["matched_expected_findings"], 2)
        self.assertEqual(result["review_time_saved_minutes"], 61)

    def test_spc_benchmark_accepts_drift_aliases(self) -> None:
        decisions = [
            Decision(
                id="S001",
                project_id="bench-test",
                type="spc_drift",
                target="avg_leakage_ua",
                action="Inspect the process step that most strongly correlates with leakage drift.",
                rationale="Leakage increased monotonically across the reviewed lots.",
                priority="HIGH",
                confidence=0.91,
                effort="2hrs",
                metadata={"evidence": "LOT_005 ends well above recent baseline leakage"},
            ),
        ]

        result = evaluate_agent02_benchmark("spc_trend_sample.csv", decisions)

        self.assertEqual(result["metrics"]["matched_expected_findings"], 1)
        self.assertEqual(result["metrics"]["first_action_alignment"], 1.0)
        self.assertEqual(result["metrics"]["overall_score"], 100)
