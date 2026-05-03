import asyncio
import unittest

from silicon_agents.core.schemas import VerifyRequest
from silicon_agents.orchestration.prompt_orchestrator import PromptOrchestrator


class PromptOrchestratorTests(unittest.TestCase):
    def test_orchestrator_builds_fallback_plan(self) -> None:
        async def build():
            orchestrator = PromptOrchestrator()
            return await orchestrator.build_plan(
                domain_label="verification coverage closure",
                task_label="ranking coverage gap closure actions",
                runtime_label="USB Controller v2.3",
                chip_type="USB 3.0 controller",
                client_profile="Fabless client with protocol-heavy review style",
                custom_instructions="Prefer protocol corner cases over low-value closure.",
                reference_data="Historical log: isochronous_transfer was previously missed due to constrained-random bias.",
                reference_data_label="historical closure notes",
                context="Focus on transfer modes and arbitration.",
                parsed_summary={"summary": {"failed": 2}, "type": "coverage"},
            )

        plan = asyncio.run(build())
        self.assertIn("USB Controller v2.3", plan["chip_focus"])
        self.assertTrue(plan["instruction_overrides"])
        self.assertTrue(plan["prompt_addendum"])


class EnterpriseRequestSchemaTests(unittest.TestCase):
    def test_verify_request_accepts_enterprise_fields(self) -> None:
        request = VerifyRequest(
            report_text="Cover Group: demo [Coverage: 50.0%]\nbins gap_case: 0 hits FAIL gap",
            chip_type="PCIe controller",
            client_profile="Custom DV methodology",
            custom_instructions="Bias actions toward directed sequence generation.",
            reference_data="Prior log shows timeout cluster around LTSSM recovery.",
            reference_data_label="historical triage log",
        )
        self.assertEqual(request.chip_type, "PCIe controller")
        self.assertEqual(request.reference_data_label, "historical triage log")
