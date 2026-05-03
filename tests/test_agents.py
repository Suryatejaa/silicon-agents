import asyncio
import unittest

from silicon_agents.agents.agent01_verify import VerificationAgent
from silicon_agents.agents.agent02_yield import YieldAgent
from silicon_agents.core.schemas import VerifyRequest, YieldRequest


class VerificationAgentTests(unittest.TestCase):
    def test_verification_agent_streams_decisions(self) -> None:
        async def collect():
            agent = VerificationAgent()
            request = VerifyRequest(
                report_text="""
                Cover Group: usb_transfer_type [Coverage: 50.0%]
                bins bulk_transfer: 10 hits PASS
                bins isochronous_transfer: 0 hits FAIL gap
                """,
                project_id="test-project",
                chip_type="USB controller",
                client_profile="Enterprise verification workflow",
                custom_instructions="Prefer fastest closure path.",
                reference_data="Previous run showed isochronous gaps.",
            )
            return [event async for event in agent.stream(request)]

        events = asyncio.run(collect())
        orchestration_events = [payload for event_type, payload in events if event_type == "orchestration"]
        decision_events = [payload for event_type, payload in events if event_type == "decision"]
        self.assertTrue(orchestration_events)
        self.assertTrue(decision_events)
        self.assertEqual(decision_events[0]["type"], "coverage_gap")
        self.assertTrue(decision_events[0]["metadata"].get("orchestration_enabled"))


class YieldAgentTests(unittest.TestCase):
    def test_yield_agent_spc_streams_alert(self) -> None:
        async def collect():
            agent = YieldAgent()
            request = YieldRequest(
                csv_data="""
                lot_id,date,avg_leakage_ua,yield_pct
                LOT_001,2026-04-01,145,94.2
                LOT_002,2026-04-02,147,94.0
                LOT_003,2026-04-03,152,93.8
                LOT_004,2026-04-04,161,93.1
                LOT_005,2026-04-05,174,91.4
                """,
                mode="spc",
                project_id="yield-project",
            )
            return [event async for event in agent.stream(request)]

        events = asyncio.run(collect())
        orchestration_events = [payload for event_type, payload in events if event_type == "orchestration"]
        decision_events = [payload for event_type, payload in events if event_type == "decision"]
        self.assertTrue(orchestration_events)
        self.assertTrue(decision_events)
        self.assertIn(decision_events[0]["type"], {"spc_drift", "spc_alert"})
