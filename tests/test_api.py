import importlib
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from silicon_agents.core.config import get_settings


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["SA_DB_PATH"] = os.path.join(cls.temp_dir.name, "test.db")
        os.environ["SA_RAG_EMBEDDING_PROVIDER"] = "local"
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("PILOT_ACCESS_TOKEN", None)
        get_settings.cache_clear()
        import main

        importlib.reload(main)
        cls.client = TestClient(main.create_app())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()
        os.environ.pop("SA_DB_PATH", None)
        os.environ.pop("SA_RAG_EMBEDDING_PROVIDER", None)
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("PILOT_ACCESS_TOKEN", None)
        get_settings.cache_clear()

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_pitch_page_route(self) -> None:
        response = self.client.get("/pitch")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Silicon Agents", response.text)
        self.assertIn("Pitch Deck", response.text)

    def test_pilot_and_docs_routes(self) -> None:
        pilot = self.client.get("/pilot")
        self.assertEqual(pilot.status_code, 200)
        self.assertIn("Pilot Dashboard", pilot.text)

        docs = self.client.get("/product-docs")
        self.assertEqual(docs.status_code, 200)
        self.assertIn("Silicon Agents documentation", docs.text)

        rag = self.client.get("/rag")
        self.assertEqual(rag.status_code, 200)
        self.assertIn("Retrieval Evidence Workbench", rag.text)

    def test_enterprise_config_defaults_and_update(self) -> None:
        default_agent01 = self.client.get("/api/v1/config/agent01")
        self.assertEqual(default_agent01.status_code, 200)
        self.assertEqual(default_agent01.json()["agent"], "agent01")
        self.assertIn("org_name", default_agent01.json()["config"])

        updated = self.client.put(
            "/api/v1/config/agent01",
            json={
                "org_name": "InSemi Delivery Unit",
                "review_board": "Verification Governance Board",
                "output_style": "Audit-friendly signoff format",
                "escalation_policy": "Escalate only with hard evidence.",
                "evidence_policy": "Every action must cite report evidence.",
                "instruction_addendum": "Keep recommendations concise.",
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["config"]["org_name"], "InSemi Delivery Unit")

        fetched_again = self.client.get("/api/v1/config/agent01")
        self.assertEqual(fetched_again.status_code, 200)
        self.assertEqual(fetched_again.json()["config"]["review_board"], "Verification Governance Board")

    def test_verify_endpoint_streams(self) -> None:
        response = self.client.post(
            "/api/v1/verify",
            json={
                "report_text": "Cover Group: demo [Coverage: 50.0%]\nbins gap_case: 0 hits FAIL gap",
                "mode": "coverage",
                "project_id": "api-test",
                "artifact_name": "demo_coverage.log",
                "artifact_source": "pasted_text",
                "run_profile_id": "usb_dv_coverage",
                "run_profile_name": "USB Controller Benchmark",
                "chip_type": "USB controller",
                "client_profile": "Enterprise DV team",
                "custom_instructions": "Prefer protocol escape review.",
                "reference_data": "Previous notes mention repeated gap_case misses.",
                "reference_data_label": "historical notes",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "decision"', response.text)
        self.assertIn('"run_id": "run-', response.text)

        history = self.client.get("/api/v1/runs", params={"project_id": "api-test", "agent": "agent01"})
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["runs"]), 1)
        run_id = history.json()["runs"][0]["run_id"]
        detail = self.client.get(f"/api/v1/runs/{run_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["artifact_name"], "demo_coverage.log")
        self.assertEqual(detail.json()["artifact_source"], "pasted_text")
        self.assertEqual(
            detail.json()["raw_artifact"],
            "Cover Group: demo [Coverage: 50.0%]\nbins gap_case: 0 hits FAIL gap",
        )
        self.assertEqual(detail.json()["run_profile_id"], "usb_dv_coverage")
        self.assertGreaterEqual(detail.json()["duration_ms"], 0)
        self.assertIn("decision_count", detail.json()["observability"])
        self.assertTrue(detail.json()["benchmark_score"])
        self.assertIn(detail.json()["parser_format"], {"vcs", "xcelium", "unknown"})
        self.assertGreater(detail.json()["parser_confidence"], 0)
        self.assertIsInstance(detail.json()["parser_warnings"], list)

        rag_search = self.client.post(
            "/api/v1/rag/search",
            json={
                "project_id": "api-test",
                "agent": "agent01",
                "mode": "coverage",
                "run_profile_id": "usb_dv_coverage",
                "query": "gap_case protocol escape review",
                "limit": 5,
            },
        )
        self.assertEqual(rag_search.status_code, 200)
        self.assertGreaterEqual(len(rag_search.json()["documents"]), 1)
        self.assertEqual(rag_search.json()["documents"][0]["project_id"], "api-test")

        second_response = self.client.post(
            "/api/v1/verify",
            json={
                "report_text": "Cover Group: demo [Coverage: 50.0%]\nbins gap_case: 0 hits FAIL gap",
                "mode": "coverage",
                "project_id": "api-test",
                "artifact_name": "demo_coverage_second.log",
                "artifact_source": "pasted_text",
                "run_profile_id": "usb_dv_coverage",
                "run_profile_name": "USB Controller Benchmark",
            },
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertIn("retrieved_sources", second_response.text)
        self.assertIn("content_excerpt", second_response.text)

        jira_export = self.client.get(f"/api/v1/runs/{run_id}/export/jira")
        self.assertEqual(jira_export.status_code, 200)
        self.assertEqual(jira_export.json()["format"], "jira")
        self.assertIn("summary", jira_export.json()["payload"])

        email_export = self.client.get(f"/api/v1/runs/{run_id}/export/email")
        self.assertEqual(email_export.status_code, 200)
        self.assertEqual(email_export.json()["format"], "email")
        self.assertIn("subject", email_export.json()["payload"])

        detail_after_exports = self.client.get(f"/api/v1/runs/{run_id}")
        self.assertEqual(detail_after_exports.status_code, 200)
        self.assertEqual(len(detail_after_exports.json()["export_history"]), 2)

    def test_rag_manual_note_ingest_and_search(self) -> None:
        ingest = self.client.post(
            "/api/v1/rag/ingest-note",
            json={
                "project_id": "rag-note-api",
                "agent": "agent01",
                "mode": "coverage",
                "source_id": "note-api-001",
                "title": "Secure boot waiver guidance",
                "content": (
                    "Lifecycle lockdown coverage gaps require security review before waiver. "
                    "Image authentication negative-path bins should cite prior escape risk."
                ),
                "run_profile_id": "secure_boot_coverage",
                "run_profile_name": "Secure Boot Coverage",
                "chip_type": "Secure Boot ROM",
                "client_profile": "Security DV team",
                "tags": ["waiver", "security"],
            },
        )
        self.assertEqual(ingest.status_code, 200)
        self.assertEqual(ingest.json()["source_id"], "note-api-001")
        self.assertGreaterEqual(ingest.json()["document_count"], 1)

        search = self.client.post(
            "/api/v1/rag/search",
            json={
                "project_id": "rag-note-api",
                "agent": "agent01",
                "mode": "coverage",
                "run_profile_id": "secure_boot_coverage",
                "source_type": "manual_note",
                "query": "lifecycle lockdown waiver security review",
                "limit": 5,
            },
        )
        self.assertEqual(search.status_code, 200)
        self.assertEqual(len(search.json()["documents"]), 1)
        self.assertEqual(search.json()["documents"][0]["source_type"], "manual_note")
        self.assertEqual(search.json()["documents"][0]["source_id"], "note-api-001")
        self.assertGreater(len(search.json()["documents"][0]["embedding"]), 0)
        self.assertEqual(search.json()["documents"][0]["metadata"]["embedding_provider"], "local")
        self.assertIn("embedding_score", search.json()["documents"][0]["metadata"])

        reindex = self.client.post(
            "/api/v1/rag/reindex",
            json={
                "project_id": "rag-note-api",
                "agent": "agent01",
                "mode": "coverage",
                "source_type": "manual_note",
                "source_id": "note-api-001",
                "limit": 10,
            },
        )
        self.assertEqual(reindex.status_code, 200)
        self.assertEqual(reindex.json()["document_count"], 1)
        self.assertEqual(reindex.json()["embedding_provider"], "local")
        self.assertEqual(reindex.json()["documents"][0]["metadata"]["embedding_model"], "local-hashing-v1")

    def test_yield_endpoint_accepts_enterprise_fields(self) -> None:
        response = self.client.post(
            "/api/v1/yield",
            json={
                "csv_data": "chip_id,max_freq_ghz,leakage_ua,vmin_mv,bin,pass\nC001,3.82,142,780,1,PASS\nC005,3.80,143,779,2,PASS\nC008,1.90,720,1010,3,FAIL\n",
                "lot_id": "LOT_004",
                "mode": "ate",
                "project_id": "yield-api-test",
                "artifact_name": "ate_parametric_sample.csv",
                "artifact_source": "bundled_sample",
                "run_profile_id": "mobile_soc_yield",
                "run_profile_name": "Mobile SoC Yield Review",
                "chip_type": "Mobile SoC",
                "client_profile": "Enterprise yield team",
                "custom_instructions": "Prioritize premium-bin recovery.",
                "reference_data": "Historical note: premium-bin reclaim candidates matter most.",
                "reference_data_label": "historical yield notes",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('"type": "decision"', response.text)
        self.assertIn('"run_id": "run-', response.text)

        history = self.client.get("/api/v1/runs", params={"project_id": "yield-api-test", "agent": "agent02"})
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["runs"]), 1)
        run_id = history.json()["runs"][0]["run_id"]
        detail = self.client.get(f"/api/v1/runs/{run_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["artifact_name"], "ate_parametric_sample.csv")
        self.assertEqual(detail.json()["artifact_source"], "bundled_sample")
        self.assertIn("chip_id,max_freq_ghz", detail.json()["raw_artifact"])
        self.assertEqual(detail.json()["run_profile_name"], "Mobile SoC Yield Review")
        self.assertIn("analysis_events", detail.json()["observability"])
        self.assertEqual(detail.json()["parser_format"], "ate_csv")
        self.assertGreater(detail.json()["parser_confidence"], 0)

        second_response = self.client.post(
            "/api/v1/yield",
            json={
                "csv_data": "chip_id,max_freq_ghz,leakage_ua,vmin_mv,bin,pass\nC001,3.82,142,780,1,PASS\nC005,3.80,143,779,2,PASS\nC008,1.90,720,1010,3,FAIL\n",
                "lot_id": "LOT_004_RERUN",
                "mode": "ate",
                "project_id": "yield-api-test",
                "artifact_name": "ate_parametric_rerun.csv",
                "artifact_source": "pasted_text",
                "run_profile_id": "mobile_soc_yield",
                "run_profile_name": "Mobile SoC Yield Review",
                "chip_type": "Mobile SoC",
                "client_profile": "Enterprise yield team",
                "custom_instructions": "Prioritize premium-bin recovery.",
            },
        )
        self.assertEqual(second_response.status_code, 200)
        self.assertIn("retrieved_sources", second_response.text)
        self.assertIn("content_excerpt", second_response.text)

        second_runs = self.client.get("/api/v1/runs", params={"project_id": "yield-api-test", "agent": "agent02"})
        second_run_id = second_runs.json()["runs"][0]["run_id"]
        second_detail = self.client.get(f"/api/v1/runs/{second_run_id}")
        self.assertGreaterEqual(second_detail.json()["observability"]["retrieval_document_count"], 1)
        self.assertIn("content_excerpt", second_detail.json()["orchestration"]["retrieval"]["sources"][0])

    def test_feedback_round_trip(self) -> None:
        self.client.post(
            "/api/v1/verify",
            json={
                "report_text": "Cover Group: demo [Coverage: 50.0%]\nbins gap_case: 0 hits FAIL gap",
                "mode": "coverage",
                "project_id": "feedback-test",
                "artifact_name": "feedback_demo.log",
                "run_profile_id": "feedback_profile",
                "run_profile_name": "Feedback Profile",
            },
        )
        runs = self.client.get("/api/v1/runs", params={"project_id": "feedback-test", "agent": "agent01"})
        run_id = runs.json()["runs"][0]["run_id"]
        save = self.client.post(
            "/api/v1/feedback",
            json={
                "decision_id": "D001",
                "accepted": True,
                "notes": "Confirmed in unit test",
                "project_id": "feedback-test",
                "engineer_id": "test-user",
                "run_id": run_id,
            },
        )
        self.assertEqual(save.status_code, 200)
        history = self.client.get("/api/v1/feedback/feedback-test")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(history.json()["feedback"][0]["decision_id"], "D001")
        run_detail = self.client.get(f"/api/v1/runs/{run_id}")
        self.assertEqual(run_detail.status_code, 200)
        self.assertEqual(run_detail.json()["feedback_summary"]["accepted"], 1)

    def test_pilot_metrics_endpoint(self) -> None:
        self.client.post(
            "/api/v1/verify",
            json={
                "report_text": "Cover Group: demo [Coverage: 50.0%]\nbins gap_case: 0 hits FAIL gap",
                "mode": "coverage",
                "project_id": "pilot-metrics-test",
                "artifact_name": "pilot_metrics.log",
                "artifact_source": "uploaded_file",
                "run_profile_id": "pilot_profile",
                "run_profile_name": "Pilot Profile",
            },
        )
        runs = self.client.get("/api/v1/runs", params={"project_id": "pilot-metrics-test", "agent": "agent01"})
        run_id = runs.json()["runs"][0]["run_id"]
        self.client.post(
            "/api/v1/feedback",
            json={
                "decision_id": "D001",
                "accepted": True,
                "project_id": "pilot-metrics-test",
                "engineer_id": "pilot-reviewer",
                "run_id": run_id,
            },
        )
        self.client.get(f"/api/v1/runs/{run_id}/export/jira")
        metrics = self.client.get("/api/v1/pilot/metrics")
        self.assertEqual(metrics.status_code, 200)
        payload = metrics.json()
        self.assertGreaterEqual(payload["total_runs"], 1)
        self.assertGreaterEqual(payload["completed_runs"], 1)
        self.assertGreaterEqual(payload["accepted_decisions"], 1)
        self.assertGreaterEqual(payload["total_exports"], 1)
        self.assertTrue(any(item["label"] == "agent01" for item in payload["agent_breakdown"]))
        self.assertTrue(any(item["label"] == "uploaded_file" for item in payload["artifact_source_breakdown"]))

    def test_agent01_benchmark_evaluation_endpoint(self) -> None:
        response = self.client.post(
            "/api/v1/benchmarks/agent01/evaluate",
            json={
                "benchmark_id": "coverage_vcs_sample.log",
                "decisions": [
                    {
                        "id": "D001",
                        "project_id": "bench-api",
                        "type": "coverage_gap",
                        "target": "isochronous_transfer",
                        "action": "Force isochronous traffic in a directed sequence.",
                        "rationale": "Gap remains at zero hits.",
                        "priority": "HIGH",
                        "confidence": 0.91,
                        "effort": "2hrs",
                        "metadata": {"evidence": "bins isochronous_transfer: 0 hits FAIL gap"},
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["benchmark_id"], "coverage_vcs_sample.log")
        self.assertEqual(response.json()["metrics"]["matched_expected_findings"], 1)

    def test_agent01_benchmark_catalog_is_expanded(self) -> None:
        response = self.client.get("/api/v1/benchmarks/agent01")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload), 10)
        benchmark_ids = {item["id"] for item in payload}
        self.assertIn("coverage_pcie_dma_sample.log", benchmark_ids)
        self.assertIn("regression_secure_boot_sample.log", benchmark_ids)

    def test_verification_brief_export_endpoint(self) -> None:
        response = self.client.post(
            "/api/v1/verify/export/html",
            json={
                "project_id": "brief-test",
                "design_name": "USB Controller v2.3",
                "mode": "coverage",
                "context": "USB verification review",
                "provider": "mock/local",
                "artifact_name": "coverage_vcs_sample.log",
                "workflow_label": "Coverage report",
                "review_time_saved": "~58 min of first-pass review effort",
                "benchmark_title": "USB Controller Benchmark · VCS Coverage",
                "benchmark_score": "92/100",
                "benchmark_notes": ["Matched findings: isochronous_transfer, control_transfer_error."],
                "analysis_log": ["Step 1 · Parsing report: Parsed 4 coverpoints."],
                "decisions": [
                    {
                        "id": "D001",
                        "project_id": "brief-test",
                        "type": "coverage_gap",
                        "target": "isochronous_transfer",
                        "action": "Force directed isochronous traffic.",
                        "rationale": "Gap remains at zero hits.",
                        "priority": "HIGH",
                        "confidence": 0.91,
                        "effort": "2hrs",
                        "metadata": {
                            "evidence": "bins isochronous_transfer: 0 hits FAIL gap",
                            "rank_basis": "Zero-hit functional gap on a protocol mode."
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Silicon Agents", response.text)
        self.assertIn("isochronous_transfer", response.text)
        self.assertIn("Executive summary", response.text)
        self.assertIn("Recommended next pilot step", response.text)

    def test_agent02_benchmark_evaluation_endpoint(self) -> None:
        response = self.client.post(
            "/api/v1/benchmarks/agent02/evaluate",
            json={
                "benchmark_id": "ate_parametric_sample.csv",
                "decisions": [
                    {
                        "id": "Y001",
                        "project_id": "bench-api",
                        "type": "bin_mismatch",
                        "target": "C005",
                        "action": "Review bin thresholds and reclassify this die as a premium candidate.",
                        "rationale": "C005 meets Bin 1 guardrails but is currently assigned to Bin 2.",
                        "priority": "HIGH",
                        "confidence": 0.94,
                        "effort": "30min",
                        "metadata": {"evidence": "3.80GHz, 143uA leakage, currently assigned to Bin 2"},
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["benchmark_id"], "ate_parametric_sample.csv")
        self.assertEqual(response.json()["metrics"]["matched_expected_findings"], 1)

    def test_yield_brief_export_endpoint(self) -> None:
        response = self.client.post(
            "/api/v1/yield/export/html",
            json={
                "project_id": "yield-brief-test",
                "lot_id": "LOT_004",
                "mode": "ate",
                "context": "Mobile SoC yield review",
                "provider": "mock/local",
                "artifact_name": "ate_parametric_sample.csv",
                "workflow_label": "ATE anomaly and binning review",
                "review_time_saved": "~54 min of first-pass review effort",
                "benchmark_title": "Mobile SoC Yield Benchmark · ATE Parametric Review",
                "benchmark_score": "91/100",
                "benchmark_notes": ["Matched findings: C005, C008."],
                "analysis_log": ["Step 1 · Parsing parametric data: Parsed 8 chips."],
                "decisions": [
                    {
                        "id": "Y001",
                        "project_id": "yield-brief-test",
                        "type": "bin_mismatch",
                        "target": "C005",
                        "action": "Review bin thresholds and reclassify this die as a premium candidate.",
                        "rationale": "C005 meets Bin 1 guardrails but is currently assigned to Bin 2.",
                        "priority": "HIGH",
                        "confidence": 0.94,
                        "effort": "30min",
                        "metadata": {
                            "evidence": "3.80GHz, 143uA leakage, currently assigned to Bin 2",
                            "rank_basis": "Revenue upside from premium-bin recovery."
                        },
                    }
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Silicon Agents", response.text)
        self.assertIn("Yield brief", response.text)
        self.assertIn("Executive summary", response.text)
        self.assertIn("Recommended next pilot step", response.text)


class PilotAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        os.environ["SA_DB_PATH"] = os.path.join(cls.temp_dir.name, "pilot_test.db")
        os.environ.pop("DATABASE_URL", None)
        os.environ["PILOT_ACCESS_TOKEN"] = "pilot-secret"
        get_settings.cache_clear()
        import main

        importlib.reload(main)
        cls.client = TestClient(main.create_app())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()
        os.environ.pop("SA_DB_PATH", None)
        os.environ.pop("PILOT_ACCESS_TOKEN", None)
        get_settings.cache_clear()

    def test_health_is_not_protected(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_api_requires_token(self) -> None:
        response = self.client.get("/api/v1/runs")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Pilot access token required.")

    def test_browser_redirects_to_pilot_login(self) -> None:
        response = self.client.get("/", follow_redirects=False, headers={"accept": "text/html"})
        self.assertEqual(response.status_code, 307)
        self.assertIn("/pilot-login", response.headers["location"])

    def test_unlock_flow_sets_cookie_and_grants_access(self) -> None:
        unlock = self.client.post("/pilot/unlock", headers={"X-Pilot-Access-Token": "pilot-secret"})
        self.assertEqual(unlock.status_code, 200)
        self.assertTrue(unlock.json()["unlocked"])

        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Silicon Agents", page.text)

    def test_pilot_access_code_generation_requires_and_accepts_token(self) -> None:
        unauthorized = self.client.post("/api/v1/pilot/access-code/generate")
        self.assertEqual(unauthorized.status_code, 401)

        authorized = self.client.post(
            "/api/v1/pilot/access-code/generate",
            headers={"X-Pilot-Access-Token": "pilot-secret"},
        )
        self.assertEqual(authorized.status_code, 200)
        payload = authorized.json()
        self.assertIn("code", payload)
        self.assertIn("X-Pilot-Access-Token", payload["bearer_example"])
