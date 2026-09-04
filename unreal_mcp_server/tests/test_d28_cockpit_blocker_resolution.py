"""Offline coverage for current cockpit blocker-resolution gates."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from chat.cockpit import (
    blocker_resolution_for_gate,
    build_blocker_resolution_summary,
    select_blocker_resolution_target,
)


class CockpitBlockerResolutionTest(unittest.TestCase):
    def test_current_platform_and_provider_gates_have_specific_resolutions(self) -> None:
        expected = {
            "chat_server_reachable": ("hard_for_native_cockpit", "unblock_cockpit_surface", "gen_compile_ide_companion_readiness"),
            "provider_api_key_configured": ("hard_for_paid_generation", "configure_provider_secret", "gen_save_provider_config"),
            "animation_provider_api_key_configured": ("hard_for_paid_animation_generation", "configure_uthana_key_in_native_generate_settings", "gen_save_provider_config"),
            "wallet_evidence_recorded": ("hard_for_paid_generation", "record_wallet_evidence", "skill_record_ide_companion_evidence"),
            "spend_confirmation_recorded": ("approval_required", "stop_and_record", "skill_record_ide_companion_evidence"),
        }

        for blocker, (severity, strategy, tool) in expected.items():
            with self.subTest(blocker=blocker):
                resolution = blocker_resolution_for_gate(blocker)
                self.assertEqual(resolution["blocker"], blocker)
                self.assertEqual(resolution["severity"], severity)
                self.assertEqual(resolution["recommended_strategy"], strategy)
                self.assertEqual(resolution["recommended_tool"], tool)
                self.assertTrue(resolution["can_continue_offline"])
                self.assertNotEqual(resolution["severity"], "unknown")
        chat = blocker_resolution_for_gate("chat_server_reachable")
        chat_text = " ".join(str(chat[field]) for field in ("unblock_action", "evidence_required"))
        self.assertIn("scripts\\start_chat_cockpit_server.ps1", chat_text)
        self.assertIn("Saved\\ChatCockpit\\last_start_receipt.json", chat_text)
        self.assertIn("/chat/history?limit=1", chat_text)

        bridge = blocker_resolution_for_gate("unreal_bridge_reachable")
        bridge_text = " ".join(str(bridge[field]) for field in ("unblock_action", "evidence_required"))
        self.assertEqual(bridge["recommended_tool"], "scripts/bridge_ping.py")
        self.assertIn("Saved\\BridgePing\\last_ping_receipt.json", bridge_text)
        self.assertIn("bridge_ping_receipt_success", bridge_text)

        dirty = blocker_resolution_for_gate("dirty_state_grouped_for_promotion")
        self.assertEqual(dirty["recommended_tool"], "scripts/write_dirty_promotion_review.py")
        self.assertIn("Saved\\DirtyPromotionReview\\last_review_receipt.json", dirty["unblock_action"])
        self.assertIn("dirty_promotion_review_receipt", dirty["evidence_required"])

    def test_provider_key_resolution_points_to_native_no_leak_setup_paths(self) -> None:
        tripo = blocker_resolution_for_gate("provider_api_key_configured")
        tripo_text = " ".join(str(tripo[field]) for field in ("unblock_action", "evidence_required"))
        self.assertIn("Generate Settings", tripo_text)
        self.assertIn("TRIPO_API_KEY", tripo_text)
        self.assertIn("gen_save_provider_config", tripo_text)
        self.assertIn("raw key must not appear", tripo_text)
        self.assertTrue(tripo["can_continue_offline"])

        uthana = blocker_resolution_for_gate("animation_provider_api_key_configured")
        uthana_text = " ".join(str(uthana[field]) for field in ("unblock_action", "evidence_required"))
        self.assertIn("Generate Settings", uthana_text)
        self.assertIn("UTHANA_API_KEY", uthana_text)
        self.assertIn("store_uthana_api_key=True", uthana_text)
        self.assertIn("uthana_api_key_configured=true", uthana_text)
        self.assertIn("raw key must not appear", uthana_text)
        self.assertTrue(uthana["can_continue_offline"])

    def test_blueprint_mutation_gates_require_pre_read_compile_and_readback(self) -> None:
        expected = {
            "blueprint_pre_read_evidence": ("inspect_before_mutation", "blueprint_pre_read"),
            "blueprint_compile_plan": ("add_compile_gate", "compile_check_after_mutation"),
            "blueprint_readback_plan": ("add_readback_gate", "graph_or_component_readback_after_mutation"),
        }

        for blocker, (strategy, evidence_fragment) in expected.items():
            with self.subTest(blocker=blocker):
                resolution = blocker_resolution_for_gate(blocker)
                self.assertEqual(resolution["severity"], "hard_for_blueprint_mutation")
                self.assertEqual(resolution["recommended_strategy"], strategy)
                self.assertIn(evidence_fragment, resolution["evidence_required"])
                self.assertTrue(resolution["can_continue_offline"])

    def test_platform_stability_gates_have_specific_no_mutation_resolutions(self) -> None:
        expected = {
            "tool_registry_reproducible": ("refresh_tool_registry_evidence", "last_tool_count.txt"),
            "test_lane_separation": ("repair_test_lane_naming", "violation_count=0"),
            "build_wrapper_present": ("restore_build_wrapper", "build_wrapper_exists=true"),
            "build_wrapper_references_ready": ("repair_build_wrapper_references", "build_wrapper_missing_reference_count=0"),
            "working_branch_is_wip": ("return_to_wip", "working_branch_ok=true"),
        }

        for blocker, (strategy, evidence_fragment) in expected.items():
            with self.subTest(blocker=blocker):
                resolution = blocker_resolution_for_gate(blocker)
                self.assertEqual(resolution["blocker"], blocker)
                self.assertEqual(resolution["severity"], "hard_for_platform_stability")
                self.assertEqual(resolution["recommended_strategy"], strategy)
                self.assertIn(evidence_fragment, resolution["evidence_required"])
                self.assertTrue(resolution["can_continue_offline"])
                self.assertNotEqual(resolution["severity"], "unknown")

    def test_wip_promotion_gates_have_specific_no_mutation_resolutions(self) -> None:
        expected = {
            "no_mutation_test_lane_safe": ("prove_no_mutation_lane_safe", "TRACKED_FILE_MUTATIONS=0"),
            "high_value_bridge_wrappers_covered": ("repair_wrapper_coverage", "failing_capability_count=0"),
            "plugin_build_successful": ("refresh_plugin_build_evidence", "last_plugin_build_status=success"),
            "dirty_state_grouped_for_promotion": ("group_dirty_state_for_promotion", "dirty_risk clean/low"),
            "chat_cockpit_reachable": ("restore_chat_cockpit_before_promotion", "ready_for_chat_cockpit=true"),
        }

        for blocker, (strategy, evidence_fragment) in expected.items():
            with self.subTest(blocker=blocker):
                resolution = blocker_resolution_for_gate(blocker)
                self.assertEqual(resolution["blocker"], blocker)
                self.assertEqual(resolution["severity"], "hard_for_wip_promotion")
                self.assertEqual(resolution["recommended_strategy"], strategy)
                self.assertIn(evidence_fragment, resolution["evidence_required"])
                self.assertTrue(resolution["can_continue_offline"])
                self.assertNotEqual(resolution["severity"], "unknown")

    def test_blocker_summary_collects_tools_and_remains_no_mutation(self) -> None:
        summary = build_blocker_resolution_summary([
            "chat_server_reachable",
            "provider_api_key_configured",
            "animation_provider_api_key_configured",
            "wallet_evidence_recorded",
            "spend_confirmation_recorded",
            "blueprint_compile_plan",
        ])

        self.assertEqual(summary["schema"], "unreal_mcp_chat_blocker_resolution_summary.v1")
        self.assertEqual(summary["blocking_gate_count"], 6)
        self.assertEqual(summary["hard_blocker_count"], 5)
        self.assertEqual(summary["offline_continuation_count"], 6)
        self.assertIn("gen_compile_ide_companion_readiness", summary["recommended_tools"])
        self.assertIn("gen_save_provider_config", summary["recommended_tools"])
        self.assertIn("skill_record_ide_companion_evidence", summary["recommended_tools"])
        self.assertIn("skill_compile_ide_companion_work_order", summary["recommended_tools"])
        self.assertFalse(summary["network_required"])
        self.assertFalse(summary["unreal_editor_required"])
        self.assertFalse(summary["spend_required"])

    def test_target_priority_prefers_bridge_then_chat_then_blueprint_then_provider(self) -> None:
        bridge_first = build_blocker_resolution_summary([
            "provider_api_key_configured",
            "chat_server_reachable",
            "unreal_bridge_reachable",
        ])
        self.assertEqual(select_blocker_resolution_target(bridge_first)["blocker"], "unreal_bridge_reachable")

        chat_first = build_blocker_resolution_summary([
            "provider_api_key_configured",
            "chat_server_reachable",
            "blueprint_compile_plan",
        ])
        self.assertEqual(select_blocker_resolution_target(chat_first)["blocker"], "chat_server_reachable")

        blueprint_first = build_blocker_resolution_summary([
            "provider_api_key_configured",
            "wallet_evidence_recorded",
            "blueprint_readback_plan",
        ])
        self.assertEqual(select_blocker_resolution_target(blueprint_first)["blocker"], "blueprint_readback_plan")

        platform_first = build_blocker_resolution_summary([
            "provider_api_key_configured",
            "wallet_evidence_recorded",
            "test_lane_separation",
        ])
        self.assertEqual(select_blocker_resolution_target(platform_first)["blocker"], "test_lane_separation")

        promotion_first = build_blocker_resolution_summary([
            "provider_api_key_configured",
            "chat_cockpit_reachable",
            "dirty_state_grouped_for_promotion",
        ])
        selected_promotion = select_blocker_resolution_target(promotion_first)
        self.assertEqual(selected_promotion["blocker"], "dirty_state_grouped_for_promotion")
        self.assertEqual(selected_promotion["recommended_strategy"], "group_dirty_state_for_promotion")

        animation_key_first = build_blocker_resolution_summary([
            "wallet_evidence_recorded",
            "spend_confirmation_recorded",
            "animation_provider_api_key_configured",
        ])
        selected = select_blocker_resolution_target(animation_key_first)
        self.assertEqual(selected["blocker"], "animation_provider_api_key_configured")
        self.assertEqual(selected["recommended_strategy"], "configure_uthana_key_in_native_generate_settings")


if __name__ == "__main__":
    unittest.main()
