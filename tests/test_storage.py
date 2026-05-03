import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timezone

from silicon_agents.core.schemas import Decision, RunHistoryRecord
from silicon_agents.storage.feedback_store import FeedbackStore


class FeedbackStoreTests(unittest.TestCase):
    def test_decision_and_feedback_round_trip(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as temp_dir:
                db_path = os.path.join(temp_dir, "store.db")
                store = FeedbackStore(db_path)
                await store.init()
                await store.save_decisions(
                    [
                        Decision(
                            id="D001",
                            project_id="storage-test",
                            type="coverage_gap",
                            target="isochronous_transfer",
                            action="Add a directed sequence.",
                            rationale="No ISO traffic was generated.",
                            priority="HIGH",
                            confidence=0.91,
                            effort="2hrs",
                            metadata={},
                        )
                    ]
                )
                await store.record_feedback(
                    decision_id="D001",
                    project_id="storage-test",
                    accepted=True,
                    notes="Validated by test",
                    engineer_id="unit-test",
                )
                decisions = await store.get_decisions("storage-test")
                feedback = await store.get_feedback("storage-test")
                self.assertEqual(len(decisions), 1)
                self.assertEqual(decisions[0].status, "accepted")
                self.assertEqual(len(feedback), 1)
                self.assertTrue(feedback[0].accepted)

        asyncio.run(run())

    def test_enterprise_config_round_trip(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as temp_dir:
                db_path = os.path.join(temp_dir, "store.db")
                store = FeedbackStore(db_path)
                await store.init()
                default_config = await store.get_enterprise_config("agent01")
                self.assertIn("org_name", default_config)
                await store.save_enterprise_config(
                    "agent01",
                    {
                        "org_name": "InSemi Delivery Unit",
                        "review_board": "Verification Governance Board",
                        "output_style": "Audit-friendly signoff format",
                        "escalation_policy": "Escalate only with hard evidence.",
                        "evidence_policy": "Every action must cite report evidence.",
                        "instruction_addendum": "Keep recommendations concise.",
                    },
                )
                persisted = await store.get_enterprise_config("agent01")
                self.assertEqual(persisted["org_name"], "InSemi Delivery Unit")
                self.assertEqual(persisted["review_board"], "Verification Governance Board")

        asyncio.run(run())

    def test_run_history_round_trip(self) -> None:
        async def run() -> None:
            with tempfile.TemporaryDirectory() as temp_dir:
                db_path = os.path.join(temp_dir, "store.db")
                store = FeedbackStore(db_path)
                await store.init()
                record = RunHistoryRecord(
                    run_id="run-001",
                    project_id="history-test",
                    agent="agent01",
                    mode="coverage",
                    status="completed",
                    provider="mock",
                    model=None,
                    artifact_name="coverage_vcs_sample.log",
                    runtime_label="USB Controller v2.3",
                    run_profile_id="usb_dv_coverage",
                    run_profile_name="USB Controller Benchmark",
                    chip_type="USB 3.0 Controller IP",
                    client_profile="Fabless verification team",
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    duration_ms=1250,
                    total_decisions=1,
                    high=1,
                    medium=0,
                    low=0,
                    request_payload={"project_id": "history-test", "report_text_chars": 128},
                    orchestration={"chip_focus": "USB 3.0 Controller IP"},
                    analysis_log=["Parsed covergroup gaps."],
                    decisions=[
                        Decision(
                            id="D001",
                            project_id="history-test",
                            type="coverage_gap",
                            target="isochronous_transfer",
                            action="Add a directed sequence.",
                            rationale="No ISO traffic was generated.",
                            priority="HIGH",
                            confidence=0.91,
                            effort="2hrs",
                            metadata={},
                        )
                    ],
                    observability={"decision_count": 1},
                )
                await store.save_run_history(record)
                await store.record_feedback(
                    decision_id="D001",
                    project_id="history-test",
                    accepted=True,
                    notes="Validated in review",
                    engineer_id="unit-test",
                    run_id="run-001",
                )
                await store.record_export("run-001", "jira", "Agent 01 coverage review", "run-001-jira.json")
                runs = await store.get_run_history(project_id="history-test", agent="agent01", limit=10)
                self.assertEqual(len(runs), 1)
                self.assertEqual(runs[0].run_id, "run-001")
                self.assertEqual(runs[0].feedback_summary.accepted, 1)
                self.assertEqual(runs[0].export_count, 1)
                fetched = await store.get_run("run-001")
                self.assertIsNotNone(fetched)
                assert fetched is not None
                self.assertEqual(fetched.artifact_name, "coverage_vcs_sample.log")
                self.assertEqual(fetched.decisions[0].target, "isochronous_transfer")
                self.assertEqual(len(fetched.feedback), 1)
                self.assertEqual(len(fetched.export_history), 1)

        asyncio.run(run())
