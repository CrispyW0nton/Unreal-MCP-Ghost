"""Offline tests for test lane filename separation."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_test_lanes.py"


def _load_lane_module():
    spec = importlib.util.spec_from_file_location("audit_test_lanes", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class TestLaneAudit(unittest.TestCase):
    def test_report_classifies_offline_live_and_paid_lanes(self) -> None:
        module = _load_lane_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir)
            for name in (
                "test_offline_contract.py",
                "live_bridge_smoke.py",
                "demo_a_live.py",
                "paid_provider_wallet.py",
                "manual_probe.py",
            ):
                (test_root / name).write_text("# fixture\n", encoding="utf-8")

            report = module.build_lane_report(test_root)

        self.assertTrue(report["ok"])
        self.assertEqual(report["counts"]["offline"], 1)
        self.assertEqual(report["counts"]["live_bridge"], 1)
        self.assertEqual(report["counts"]["live_bridge_manual"], 1)
        self.assertEqual(report["counts"]["paid_provider"], 1)
        self.assertEqual(report["counts"]["manual"], 1)
        self.assertIn("paid_provider_contract", report)
        self.assertFalse(report["paid_provider_contract"]["smoke_exists"])

    def test_report_flags_live_or_paid_tests_in_default_discovery(self) -> None:
        module = _load_lane_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_root = Path(tmpdir)
            for name in ("test_live_bridge_smoke.py", "test_paid_provider_wallet.py"):
                (test_root / name).write_text("# fixture\n", encoding="utf-8")

            report = module.build_lane_report(test_root)

        self.assertFalse(report["ok"])
        self.assertEqual(
            [violation["file"] for violation in report["violations"]],
            ["test_live_bridge_smoke.py", "test_paid_provider_wallet.py"],
        )

    def test_repo_has_guarded_paid_provider_lane_artifact(self) -> None:
        module = _load_lane_module()
        report = module.build_lane_report()

        self.assertTrue(report["ok"])
        self.assertIn("paid_provider_generative_smoke.py", report["lanes"]["paid_provider"])
        self.assertGreaterEqual(report["counts"]["paid_provider"], 1)
        contract = report["paid_provider_contract"]
        self.assertEqual(contract["schema"], "unreal_mcp_paid_provider_smoke_contract.v1")
        self.assertTrue(contract["contract_ok"])
        self.assertTrue(contract["smoke_exists"])
        self.assertTrue(contract["in_paid_provider_lane"])
        self.assertFalse(contract["default_discovered"])
        self.assertFalse(contract["default_ci_network_required"])
        self.assertTrue(contract["manual_network_required"])
        self.assertFalse(contract["manual_spend_required"])
        self.assertTrue(contract["no_task_submission"])
        self.assertTrue(contract["no_download"])
        self.assertTrue(contract["no_import"])
        self.assertEqual(contract["missing_required_tokens"], [])
        self.assertEqual(contract["forbidden_tokens_present"], [])
        self.assertIn("RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE", contract["required_env_vars"])
        self.assertIn("UNREAL_MCP_PROVIDER_NETWORK_APPROVED", contract["required_env_vars"])
        self.assertIn("UNREAL_MCP_CONFIRM_NO_SPEND_PROVIDER_CHECKS", contract["required_env_vars"])
        self.assertIn("UTHANA_SMOKE_JOB_ID", contract["optional_env_vars"])
        self.assertIn("UTHANA_SMOKE_MOTION_ID", contract["optional_env_vars"])
        self.assertIn("gen_tripo_get_credit_balance", contract["no_spend_tools"])
        self.assertIn("gen_uthana_get_account", contract["no_spend_tools"])
        self.assertIn("gen_uthana_get_job", contract["no_spend_tools"])
        self.assertIn("gen_uthana_check_download_allowed", contract["no_spend_tools"])
        self.assertIn("python -m unittest unreal_mcp_server.tests.paid_provider_generative_smoke", contract["manual_command"])

        smoke_path = REPO_ROOT / "unreal_mcp_server" / "tests" / "paid_provider_generative_smoke.py"
        smoke_text = smoke_path.read_text(encoding="utf-8")
        self.assertIn("RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE", smoke_text)
        self.assertIn("UNREAL_MCP_PROVIDER_NETWORK_APPROVED", smoke_text)
        self.assertIn("UNREAL_MCP_CONFIRM_NO_SPEND_PROVIDER_CHECKS", smoke_text)
        self.assertIn("gen_tripo_get_credit_balance", smoke_text)
        self.assertIn("gen_uthana_get_account", smoke_text)
        self.assertIn("gen_uthana_get_job", smoke_text)
        self.assertIn("gen_uthana_check_download_allowed", smoke_text)
        self.assertIn("UTHANA_SMOKE_JOB_ID", smoke_text)
        self.assertIn("UTHANA_SMOKE_MOTION_ID", smoke_text)
        self.assertNotIn("gen_uthana_download_motion", smoke_text)
        self.assertNotIn("confirm_spend=True", smoke_text)
        self.assertNotIn("confirm_usage=True", smoke_text)


if __name__ == "__main__":
    unittest.main()
