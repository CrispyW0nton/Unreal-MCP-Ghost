"""Static coverage for no-mutation CI smoke documentation."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CI_SMOKE_PATH = REPO_ROOT / "docs" / "ci-smoke.md"


class TestPhase0CiSmokeDocs(unittest.TestCase):
    def test_ci_smoke_documents_no_mutation_full_suite_guard(self):
        text = CI_SMOKE_PATH.read_text(encoding="utf-8")

        self.assertIn("## No-Mutation Full Suite", text)
        self.assertIn("python scripts\\run_no_mutation_unittest.py", text)
        self.assertIn("TRACKED_FILE_MUTATIONS=0", text)
        self.assertIn("NO_MUTATION_RECEIPT=Saved\\NoMutationTest\\last_run_receipt.json", text)
        self.assertIn("unreal_mcp_no_mutation_unittest_receipt.v1", text)
        self.assertIn("mutation_count=0", text)
        self.assertIn("every Git-tracked", text)
        self.assertIn("unreal_mcp_server\\tests\\last_tool_count.txt", text)
        self.assertIn("does not require Unreal Editor", text)
        self.assertIn("Tripo API", text)
        self.assertIn("provider spend approval", text)
        self.assertIn("scripts\\start_chat_cockpit_server.ps1", text)
        self.assertIn("CHAT_COCKPIT_RECEIPT=Saved\\ChatCockpit\\last_start_receipt.json", text)
        self.assertIn("unreal_mcp_chat_cockpit_start_receipt.v1", text)
        self.assertIn("scripts\\write_dirty_promotion_review.py", text)
        self.assertIn("DIRTY_PROMOTION_RECEIPT=Saved\\DirtyPromotionReview\\last_review_receipt.json", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_REVIEW=...", text)
        self.assertIn("unreal_mcp_dirty_promotion_review_receipt.v1", text)
        self.assertIn("not permission to stage, commit, merge, or promote", text)
        self.assertIn("scripts\\write_provider_config_review.py", text)
        self.assertIn("PROVIDER_CONFIG_RECEIPT=Saved\\ProviderConfigReview\\last_review_receipt.json", text)
        self.assertIn("unreal_mcp_provider_config_review_receipt.v1", text)
        self.assertIn("never raw Tripo or Uthana keys", text)
        self.assertIn("scripts\\write_platform_stability_review.py", text)
        self.assertIn("PLATFORM_STABILITY_RECEIPT=Saved\\PlatformStabilityReview\\last_review_receipt.json", text)
        self.assertIn("PLATFORM_STABILITY_DIRTY_TARGET_REVIEW=...", text)
        self.assertIn("unreal_mcp_platform_stability_review_receipt.v1", text)
        self.assertIn("not permission to mutate Unreal, call providers, spend credits, stage, commit, clean, or promote", text)
        self.assertIn("active development on `wip`", text)
        self.assertIn("`main`", text)

    def test_ci_smoke_keeps_focused_phase0_gates_visible(self):
        text = CI_SMOKE_PATH.read_text(encoding="utf-8")

        self.assertIn("python scripts\\tool_inventory.py --markdown", text)
        self.assertIn("python scripts\\audit_ide_companion_readiness.py", text)
        self.assertIn("python scripts\\audit_test_lanes.py", text)
        self.assertIn("python scripts\\bridge_command_audit.py", text)
        self.assertIn("unreal_mcp_server.tests.test_phase0_ide_companion_preflight", text)
        self.assertIn("readiness_policy", text)
        self.assertIn("WIP/main branch policy", text)
        self.assertIn("Blueprint mutation evidence gates", text)

    def test_ci_smoke_separates_offline_live_and_paid_lanes(self):
        text = CI_SMOKE_PATH.read_text(encoding="utf-8")
        normalized_text = " ".join(text.split())

        self.assertIn("## Test Lane Conventions", text)
        self.assertIn("unreal_mcp_server\\tests\\test_*.py", text)
        self.assertIn("unreal_mcp_server\\tests\\live_bridge_*.py", text)
        self.assertIn("unreal_mcp_server\\tests\\paid_provider_*.py", text)
        self.assertIn("No Unreal Editor, no TCP bridge, no provider network, no spend", text)
        self.assertIn("Live bridge tests must be excluded", text)
        self.assertIn("Saved\\BridgePing\\last_ping_receipt.json", text)
        self.assertIn("unreal_mcp_bridge_ping_receipt.v1", text)
        self.assertIn("successful_bridge_ping=true", text)
        self.assertIn("Paid provider tests must also be excluded", text)
        self.assertIn("paid_provider_generative_smoke", text)
        self.assertIn("RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE", text)
        self.assertIn("UNREAL_MCP_PROVIDER_NETWORK_APPROVED", text)
        self.assertIn("UNREAL_MCP_CONFIRM_NO_SPEND_PROVIDER_CHECKS", text)
        self.assertIn("must not submit Tripo tasks", text)
        self.assertIn("audit_test_lanes.py", text)
        self.assertIn("wallet evidence", text)
        self.assertIn("explicit spend or no-spend intent confirmation", normalized_text)


if __name__ == "__main__":
    unittest.main()
