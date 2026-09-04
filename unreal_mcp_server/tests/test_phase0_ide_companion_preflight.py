"""Offline coverage for the IDE companion no-mutation preflight."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_ide_companion_readiness.py"
CHAT_START_SCRIPT_PATH = REPO_ROOT / "scripts" / "start_chat_cockpit_server.ps1"
DIRTY_REVIEW_SCRIPT_PATH = REPO_ROOT / "scripts" / "write_dirty_promotion_review.py"
BRIDGE_PING_SCRIPT_PATH = REPO_ROOT / "scripts" / "bridge_ping.py"
PROVIDER_REVIEW_SCRIPT_PATH = REPO_ROOT / "scripts" / "write_provider_config_review.py"
PAID_GENERATION_REVIEW_SCRIPT_PATH = REPO_ROOT / "scripts" / "write_paid_generation_evidence_review.py"
BLUEPRINT_MUTATION_REVIEW_SCRIPT_PATH = REPO_ROOT / "scripts" / "write_blueprint_mutation_evidence_review.py"
PLATFORM_STABILITY_REVIEW_SCRIPT_PATH = REPO_ROOT / "scripts" / "write_platform_stability_review.py"
COUNT_PATH = SERVER_ROOT / "tests" / "last_tool_count.txt"


@contextmanager
def _temporary_untracked_git_change():
    """Make dirty-worktree tests deterministic without touching tracked files."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=SERVER_ROOT / "tests",
        prefix=".git-status-test-",
        suffix=".tmp",
        delete=False,
    ) as stream:
        marker_path = Path(stream.name)
        stream.write("synthetic dirty-worktree fixture\n")
    try:
        yield
    finally:
        marker_path.unlink(missing_ok=True)


def _load_preflight_module():
    spec = importlib.util.spec_from_file_location("audit_ide_companion_readiness", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_paid_generation_review_module():
    spec = importlib.util.spec_from_file_location("write_paid_generation_evidence_review", PAID_GENERATION_REVIEW_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_blueprint_mutation_review_module():
    spec = importlib.util.spec_from_file_location("write_blueprint_mutation_evidence_review", BLUEPRINT_MUTATION_REVIEW_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_dirty_review_module():
    spec = importlib.util.spec_from_file_location("write_dirty_promotion_review", DIRTY_REVIEW_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class TestPhase0IdeCompanionPreflight(unittest.TestCase):
    def test_report_is_structured_and_no_spend(self):
        module = _load_preflight_module()

        before = COUNT_PATH.read_text(encoding="utf-8")
        with _temporary_untracked_git_change():
            report = module.build_report(
                bridge_host="127.0.0.1",
                bridge_port=9,
                chat_url="http://127.0.0.1:9",
                timeout_s=0.1,
            )
        after = COUNT_PATH.read_text(encoding="utf-8")

        self.assertEqual(before, after)
        self.assertEqual(report["schema"], "unreal_mcp_ide_companion_preflight.v1")
        self.assertIn("tool_inventory", report)
        self.assertEqual(report["tool_count"], report["tool_inventory"]["tool_count"])
        self.assertEqual(report["recorded_tool_count"], report["tool_inventory"]["recorded_count"])
        self.assertEqual(report["partial_tool_count"], report["tool_inventory"]["partial_tools"])
        self.assertEqual(
            report["tool_registry_reproducible"],
            report["tool_inventory"]["matches_recorded_count"] and not report["tool_inventory"]["missing_category_modules"],
        )
        self.assertIn("runtime", report)
        self.assertIn("bridge", report)
        self.assertIn("chat", report)
        self.assertIn("provider_config", report)
        self.assertIn("test_lanes", report)
        self.assertEqual(report["test_lanes"]["schema"], "unreal_mcp_test_lane_audit.v1")
        self.assertTrue(report["test_lanes"]["ok"])
        self.assertEqual(report["test_lanes"]["violation_count"], 0)
        self.assertGreaterEqual(report["test_lanes"]["offline_count"], 1)
        self.assertGreaterEqual(report["test_lanes"]["paid_provider_count"], 1)
        self.assertTrue(report["test_lanes"]["paid_provider_contract_ok"])
        self.assertFalse(report["test_lanes"]["paid_provider_default_ci_network_required"])
        self.assertTrue(report["test_lanes"]["paid_provider_manual_network_required"])
        self.assertFalse(report["test_lanes"]["paid_provider_manual_spend_required"])
        self.assertIn("RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE", report["test_lanes"]["paid_provider_required_env_vars"])
        self.assertIn("UNREAL_MCP_PROVIDER_NETWORK_APPROVED", report["test_lanes"]["paid_provider_required_env_vars"])
        self.assertIn("UNREAL_MCP_CONFIRM_NO_SPEND_PROVIDER_CHECKS", report["test_lanes"]["paid_provider_required_env_vars"])
        self.assertIn("gen_tripo_get_credit_balance", report["test_lanes"]["paid_provider_no_spend_tools"])
        self.assertIn("gen_uthana_get_account", report["test_lanes"]["paid_provider_no_spend_tools"])
        self.assertIn("gen_uthana_get_job", report["test_lanes"]["paid_provider_no_spend_tools"])
        self.assertEqual(report["test_lanes"]["paid_provider_forbidden_tokens_present"], [])
        self.assertIn("paid_provider_generative_smoke", report["test_lanes"]["paid_provider_manual_command"])
        self.assertIn("no_mutation_tests", report)
        self.assertEqual(report["no_mutation_tests"]["schema"], "unreal_mcp_no_mutation_unittest_receipt.v1")
        self.assertIn(report["no_mutation_tests"]["state"], {"ok", "missing", "blocked"})
        self.assertEqual(report["no_mutation_tests"]["required_command"], "python scripts\\run_no_mutation_unittest.py")
        self.assertEqual(report["no_mutation_tests"]["operator_command_handoff_count"], 1)
        self.assertEqual(report["no_mutation_tests"]["operator_command_handoff_ids"], ["run_no_mutation_unittest"])
        self.assertEqual(
            report["no_mutation_tests"]["operator_command_handoff"][0]["command"],
            "python scripts\\run_no_mutation_unittest.py",
        )
        self.assertFalse(report["no_mutation_tests"]["operator_command_handoff"][0]["requires_bridge"])
        self.assertTrue(report["no_mutation_tests"]["operator_command_handoff"][0]["no_editor_mutation"])
        self.assertTrue(report["no_mutation_tests"]["operator_command_handoff"][0]["no_git_mutation"])
        self.assertFalse(report["no_mutation_tests"]["network_required"])
        self.assertFalse(report["no_mutation_tests"]["spend_required"])
        self.assertFalse(report["no_mutation_tests"]["unreal_editor_required"])
        self.assertEqual(report["provider_config"]["animation_provider"], "uthana")
        self.assertIn("uthana_api_key_configured", report["provider_config"])
        self.assertIn("animation_output_folder", report["provider_config"])
        self.assertIn("repair_contract", report["provider_config"])
        self.assertIn("secret_contract", report["provider_config"])
        self.assertIn("review_receipt", report["provider_config"])
        self.assertIn(report["provider_config"]["review_receipt_state"], {"missing", "ready", "missing_keys", "blocked"})
        self.assertEqual(report["provider_config"]["review_receipt_path"], "Saved\\ProviderConfigReview\\last_review_receipt.json")
        self.assertEqual(report["provider_config"]["review_receipt_required_command"], "python scripts\\write_provider_config_review.py")
        self.assertEqual(report["provider_config"]["operator_command_handoff_count"], 1)
        self.assertEqual(report["provider_config"]["operator_command_handoff_ids"], ["write_provider_config_review_receipt"])
        provider_handoff = report["provider_config"]["operator_command_handoff"][0]
        self.assertEqual(provider_handoff["command"], "python scripts\\write_provider_config_review.py")
        self.assertFalse(provider_handoff["requires_bridge"])
        self.assertFalse(provider_handoff["requires_provider_network"])
        self.assertFalse(provider_handoff["requires_spend"])
        self.assertTrue(provider_handoff["no_provider_call"])
        self.assertTrue(provider_handoff["no_task_submission"])
        self.assertTrue(provider_handoff["no_editor_mutation"])
        self.assertFalse(report["provider_config"]["repair_contract"]["network_required"])
        self.assertFalse(report["provider_config"]["repair_contract"]["spend_required"])
        self.assertFalse(report["provider_config"]["secret_contract"]["raw_key_returned"])
        self.assertTrue(report["provider_config"]["secret_contract"]["masked_status_only"])
        self.assertIn("<TRIPO_API_KEY>", report["provider_config"]["repair_contract"]["tripo_store_command_template"])
        self.assertIn("<UTHANA_API_KEY>", report["provider_config"]["repair_contract"]["uthana_store_command_template"])
        self.assertIn("readiness_policy", report)
        self.assertEqual(report["readiness_policy"]["schema"], "unreal_mcp_readiness_policy.v1")
        self.assertIn("ready_for_blueprint_mutation", report)
        self.assertFalse(report["ready_for_blueprint_mutation"])
        self.assertIn("platform_stability_review", report)
        self.assertIn(report["platform_stability_review_receipt_state"], {"missing", "ready", "review_required", "blocked"})
        self.assertEqual(report["platform_stability_review_receipt_path"], "Saved\\PlatformStabilityReview\\last_review_receipt.json")
        self.assertEqual(report["platform_stability_review_receipt_required_command"], "python scripts\\write_platform_stability_review.py")
        self.assertFalse(report["platform_stability_review"]["network_required"])
        self.assertFalse(report["platform_stability_review"]["spend_required"])
        self.assertFalse(report["platform_stability_review"]["unreal_editor_required"])
        self.assertIn("unreal_bridge_reachable", report["readiness_policy"]["editor_mutation"]["missing_gates"])
        self.assertIn("receipt", report["bridge"])
        self.assertIn(report["bridge"]["bridge_ping_receipt_state"], {"missing", "ok", "blocked"})
        self.assertEqual(report["bridge"]["bridge_ping_receipt_path"], "Saved\\BridgePing\\last_ping_receipt.json")
        self.assertEqual(report["bridge"]["bridge_ping_required_command"], "python scripts\\bridge_ping.py")
        self.assertEqual(report["bridge"]["bridge_ping_operator_command_handoff_count"], 1)
        self.assertEqual(report["bridge"]["bridge_ping_operator_command_handoff_ids"], ["verify_unreal_bridge_ping"])
        self.assertEqual(report["bridge"]["bridge_ping_operator_command_handoff"][0]["command"], "python scripts\\bridge_ping.py")
        self.assertTrue(report["bridge"]["bridge_ping_operator_command_handoff"][0]["requires_bridge"])
        self.assertTrue(report["bridge"]["bridge_ping_operator_command_handoff"][0]["requires_unreal_editor"])
        self.assertTrue(report["bridge"]["bridge_ping_operator_command_handoff"][0]["no_editor_mutation"])
        self.assertIn("chat_server_reachable", report["blocking_gates"])
        self.assertIn("chat_server_reachable", report["readiness_policy"]["chat_cockpit"]["missing_gates"])
        self.assertIn("chat_history_endpoint_ready", report["readiness_policy"]["chat_cockpit"]["evidence_required"])
        self.assertEqual(report["chat"]["health_endpoint"], "/chat/history?limit=1")
        self.assertIn("scripts\\start_chat_cockpit_server.ps1", report["chat"]["startup_command"])
        self.assertIn("--transport sse", report["chat"]["manual_startup_command"])
        self.assertEqual(report["chat"]["startup_receipt_path"], "Saved\\ChatCockpit\\last_start_receipt.json")
        self.assertIn("npm run chat:agent", report["chat"]["agent_command"])
        self.assertIn("tcp_ready", report["chat"])
        self.assertIn("tcp", report["chat"])
        self.assertIn("chat_cockpit_repair_contract", report)
        chat_repair = report["chat_cockpit_repair_contract"]
        self.assertEqual(chat_repair["schema"], "unreal_mcp_chat_cockpit_repair_contract.v1")
        self.assertEqual(chat_repair["health_endpoint"], "/chat/history?limit=1")
        self.assertIn("scripts\\start_chat_cockpit_server.ps1", chat_repair["startup_command"])
        self.assertIn("--transport sse", chat_repair["manual_startup_command"])
        self.assertEqual(chat_repair["startup_receipt_path"], "Saved\\ChatCockpit\\last_start_receipt.json")
        self.assertIn("messages list", chat_repair["proof_expected"])
        self.assertIn("chat_cockpit_start_receipt_success", chat_repair["required_evidence"])
        self.assertIn("chat_history_http_200", chat_repair["required_evidence"])
        self.assertTrue(chat_repair["no_process_start"])
        self.assertTrue(chat_repair["no_port_kill"])
        self.assertFalse(chat_repair["network_required"])
        self.assertFalse(chat_repair["spend_required"])
        self.assertFalse(chat_repair["unreal_editor_required"])
        self.assertFalse(report["chat"]["network_required"])
        self.assertFalse(report["chat"]["spend_required"])
        self.assertIn("wallet_evidence_recorded", report["blocking_gates"])
        self.assertIn("spend_confirmation_recorded", report["blocking_gates"])
        self.assertIn("wallet_evidence_recorded", report["readiness_policy"]["paid_generation"]["missing_gates"])
        self.assertIn("spend_confirmation_recorded", report["readiness_policy"]["paid_generation"]["missing_gates"])
        self.assertIn("paid_animation_generation", report["readiness_policy"])
        self.assertIn(
            "animation_provider_api_key_configured",
            report["readiness_policy"]["paid_animation_generation"]["required_gates"],
        )
        self.assertIn("wallet_evidence_recorded", report["readiness_policy"]["paid_animation_generation"]["missing_gates"])
        self.assertIn("spend_confirmation_recorded", report["readiness_policy"]["paid_animation_generation"]["missing_gates"])
        self.assertIn("ready_for_paid_animation_generation", report)
        self.assertIn("paid_generation_evidence", report)
        paid_evidence = report["paid_generation_evidence"]
        self.assertEqual(paid_evidence["schema"], "unreal_mcp_paid_generation_evidence_contract.v1")
        self.assertFalse(paid_evidence["wallet_evidence_recorded"])
        self.assertFalse(paid_evidence["mesh_wallet_evidence_recorded"])
        self.assertFalse(paid_evidence["animation_allowance_evidence_recorded"])
        self.assertFalse(paid_evidence["spend_confirmation_recorded"])
        self.assertFalse(paid_evidence["explicit_spend_approval_recorded"])
        self.assertFalse(paid_evidence["explicit_usage_approval_recorded"])
        self.assertFalse(paid_evidence["network_required_now"])
        self.assertFalse(paid_evidence["spend_required_now"])
        self.assertTrue(paid_evidence["future_network_required"])
        self.assertTrue(paid_evidence["future_spend_required"])
        self.assertEqual(paid_evidence["mesh_wallet_tool"], "gen_tripo_get_credit_balance")
        self.assertIn("gen_uthana_get_account", paid_evidence["animation_allowance_tools"])
        self.assertIn("gen_uthana_check_download_allowed", paid_evidence["animation_allowance_tools"])
        self.assertIn("masked_tripo_wallet_evidence", paid_evidence["evidence_required"])
        self.assertIn("masked_uthana_allowance_evidence", paid_evidence["evidence_required"])
        self.assertIn("explicit_uthana_usage_approval", paid_evidence["evidence_required"])
        self.assertEqual(paid_evidence["ledger_tool"], "skill_record_ide_companion_evidence")
        self.assertIn("confirm_usage=True", paid_evidence["spend_approval_field"])
        self.assertIn("gen_tripo_get_credit_balance(include_raw=False)", " ".join(paid_evidence["wallet_evidence_review_steps"]))
        self.assertIn("gen_uthana_get_account(include_user=False)", " ".join(paid_evidence["wallet_evidence_review_steps"]))
        self.assertIn("--mesh-wallet-evidence-recorded", paid_evidence["wallet_evidence_receipt_command_template"])
        self.assertIn("--animation-allowance-evidence-recorded", paid_evidence["wallet_evidence_receipt_command_template"])
        self.assertIn("--record-masked-tripo-wallet-evidence", paid_evidence["mesh_wallet_evidence_receipt_command_template"])
        self.assertNotIn("--animation-allowance-evidence-recorded", paid_evidence["mesh_wallet_evidence_receipt_command_template"])
        self.assertIn("--record-masked-uthana-allowance-evidence", paid_evidence["animation_allowance_receipt_command_template"])
        self.assertNotIn("--mesh-wallet-evidence-recorded", paid_evidence["animation_allowance_receipt_command_template"])
        self.assertIn("--record-explicit-spend-and-usage-approval", paid_evidence["spend_confirmation_receipt_command_template"])
        self.assertIn("operator_command_handoff", paid_evidence)
        self.assertEqual(len(paid_evidence["operator_command_handoff"]), 3)
        self.assertEqual(paid_evidence["operator_command_handoff"][0]["id"], "record_masked_tripo_wallet_evidence")
        self.assertEqual(paid_evidence["operator_command_handoff"][1]["id"], "record_masked_uthana_allowance_evidence")
        self.assertEqual(paid_evidence["operator_command_handoff"][2]["id"], "record_explicit_spend_and_usage_approval")
        self.assertEqual(paid_evidence["operator_command_handoff"][0]["provider"], "tripo")
        self.assertEqual(paid_evidence["operator_command_handoff"][1]["provider"], "uthana")
        self.assertFalse(paid_evidence["operator_command_handoff"][0]["approval_flags_included"])
        self.assertFalse(paid_evidence["operator_command_handoff"][1]["approval_flags_included"])
        self.assertTrue(paid_evidence["operator_command_handoff"][0]["requires_provider_network_approval"])
        self.assertTrue(paid_evidence["operator_command_handoff"][1]["requires_provider_network_approval"])
        self.assertTrue(paid_evidence["operator_command_handoff"][0]["no_provider_call"])
        self.assertTrue(paid_evidence["operator_command_handoff"][0]["no_task_submission"])
        self.assertTrue(paid_evidence["operator_command_handoff"][1]["no_task_submission"])
        self.assertTrue(paid_evidence["operator_command_handoff"][2]["approval_flags_included"])
        self.assertTrue(paid_evidence["operator_command_handoff"][2]["requires_human_spend_or_usage_approval"])
        self.assertIn("--record-masked-tripo-wallet-evidence", paid_evidence["operator_command_handoff"][0]["command"])
        self.assertIn("--record-masked-uthana-allowance-evidence", paid_evidence["operator_command_handoff"][1]["command"])
        self.assertNotIn("--spend-confirmation-recorded", paid_evidence["operator_command_handoff"][0]["command"])
        self.assertNotIn("--spend-confirmation-recorded", paid_evidence["operator_command_handoff"][1]["command"])
        self.assertIn("--record-explicit-spend-and-usage-approval", paid_evidence["operator_command_handoff"][2]["command"])
        self.assertEqual(paid_evidence["review_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
        self.assertEqual(paid_evidence["review_receipt_required_command"], "python scripts\\write_paid_generation_evidence_review.py")
        self.assertIn(paid_evidence["review_receipt_state"], {"missing", "missing_evidence", "ready"})
        self.assertTrue(paid_evidence["no_provider_call"])
        self.assertTrue(paid_evidence["no_credit_reservation"])
        self.assertTrue(paid_evidence["no_task_submission"])
        self.assertTrue(paid_evidence["no_ledger_write"])
        self.assertIn("blueprint_mutation_evidence", report)
        blueprint_evidence = report["blueprint_mutation_evidence"]
        self.assertEqual(blueprint_evidence["schema"], "unreal_mcp_blueprint_mutation_evidence_review_receipt.v1")
        self.assertIn(blueprint_evidence["state"], {"missing", "missing_evidence", "ready", "blocked"})
        self.assertEqual(blueprint_evidence["path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
        self.assertEqual(blueprint_evidence["required_command"], "python scripts\\write_blueprint_mutation_evidence_review.py")
        self.assertIn("pre_read_evidence_recorded", blueprint_evidence)
        self.assertIn("compile_plan_recorded", blueprint_evidence)
        self.assertIn("readback_plan_recorded", blueprint_evidence)
        self.assertTrue(blueprint_evidence["no_editor_mutation"])
        self.assertTrue(blueprint_evidence["no_blueprint_mutation"])
        self.assertTrue(blueprint_evidence["no_compile"])
        self.assertTrue(blueprint_evidence["no_save"])
        self.assertTrue(blueprint_evidence["no_pie"])
        self.assertTrue(blueprint_evidence["no_provider_call"])
        self.assertTrue(blueprint_evidence["no_git_mutation"])
        self.assertEqual(report["blueprint_mutation_evidence_receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
        self.assertEqual(
            report["blueprint_mutation_evidence_receipt_required_command"],
            "python scripts\\write_blueprint_mutation_evidence_review.py",
        )
        self.assertIn("readiness_repair_queue", report)
        repair_queue = report["readiness_repair_queue"]
        self.assertEqual(repair_queue["schema"], "unreal_mcp_readiness_repair_queue.v1")
        self.assertEqual(repair_queue["state"], "blocked")
        self.assertGreaterEqual(repair_queue["action_count"], 1)
        self.assertTrue(repair_queue["no_auto_execute"])
        self.assertTrue(repair_queue["no_secret_echo"])
        self.assertTrue(repair_queue["no_git_mutation"])
        self.assertTrue(repair_queue["no_editor_mutation"])
        self.assertIn(
            repair_queue["recommended_next"],
            {
                "repair_chat_server_reachability",
                "refresh_chat_cockpit_after_server_ready",
                "review_dirty_groups_for_promotion",
                "verify_unreal_bridge_reachability",
                "configure_tripo_provider_secret",
                "configure_uthana_provider_secret",
                "record_wallet_or_allowance_evidence",
            },
        )
        self.assertEqual(
            repair_queue["priority_policy"],
            "chat_health_then_wip_promotion_safety_then_bridge_proof_then_paid_provider_gates",
        )
        if repair_queue["recommended_next"] == "record_wallet_or_allowance_evidence":
            self.assertTrue(repair_queue["network_required_for_next_action"])
        else:
            self.assertFalse(repair_queue["network_required_for_next_action"])
        self.assertFalse(repair_queue["spend_required_for_next_action"])
        repair_actions = {item["gate"]: item for item in repair_queue["action_preview"]}
        self.assertIn("wallet_evidence_recorded", repair_actions)
        self.assertIn("dirty_state_grouped_for_promotion", repair_actions)
        self.assertIn("unreal_bridge_reachable", repair_actions)
        if "chat_server_reachable" in repair_actions:
            self.assertEqual(repair_actions["chat_server_reachable"]["recommended_contract"], "chat_cockpit_repair_contract")
            self.assertTrue(repair_actions["chat_server_reachable"]["no_process_start"])
        if report["provider_config"]["api_key_configured"]:
            self.assertNotIn("provider_api_key_configured", repair_actions)
        else:
            self.assertIn("provider_api_key_configured", repair_actions)
            self.assertEqual(repair_actions["provider_api_key_configured"]["secret_placeholder"], "<TRIPO_API_KEY>")
            self.assertEqual(repair_actions["provider_api_key_configured"]["review_receipt_path"], "Saved\\ProviderConfigReview\\last_review_receipt.json")
            self.assertTrue(repair_actions["provider_api_key_configured"]["no_provider_call"])
        if report["provider_config"].get("uthana_api_key_configured", False):
            self.assertNotIn("animation_provider_api_key_configured", repair_actions)
        else:
            self.assertIn("animation_provider_api_key_configured", repair_actions)
            self.assertEqual(repair_actions["animation_provider_api_key_configured"]["secret_placeholder"], "<UTHANA_API_KEY>")
            self.assertEqual(repair_actions["animation_provider_api_key_configured"]["review_receipt_path"], "Saved\\ProviderConfigReview\\last_review_receipt.json")
        self.assertTrue(repair_actions["wallet_evidence_recorded"]["requires_network"])
        self.assertTrue(repair_actions["wallet_evidence_recorded"]["no_credit_reservation"])
        self.assertTrue(repair_actions["wallet_evidence_recorded"]["no_task_submission"])
        self.assertTrue(repair_actions["wallet_evidence_recorded"]["no_download"])
        self.assertIn("gen_uthana_get_account(include_user=False)", " ".join(repair_actions["wallet_evidence_recorded"]["review_steps"]))
        self.assertIn("--mesh-wallet-evidence-recorded", repair_actions["wallet_evidence_recorded"]["receipt_command_template"])
        self.assertIn("--animation-allowance-evidence-recorded", repair_actions["wallet_evidence_recorded"]["receipt_command_template"])
        self.assertEqual(len(repair_actions["wallet_evidence_recorded"]["operator_command_handoff"]), 2)
        self.assertEqual(
            repair_actions["wallet_evidence_recorded"]["operator_command_handoff"][0]["id"],
            "record_masked_tripo_wallet_evidence",
        )
        self.assertEqual(
            repair_actions["wallet_evidence_recorded"]["operator_command_handoff"][1]["id"],
            "record_masked_uthana_allowance_evidence",
        )
        self.assertFalse(repair_actions["wallet_evidence_recorded"]["operator_command_handoff"][0]["approval_flags_included"])
        self.assertFalse(repair_actions["wallet_evidence_recorded"]["operator_command_handoff"][1]["approval_flags_included"])
        self.assertEqual(len(repair_actions["spend_confirmation_recorded"]["operator_command_handoff"]), 1)
        self.assertEqual(
            repair_actions["spend_confirmation_recorded"]["operator_command_handoff"][0]["id"],
            "record_explicit_spend_and_usage_approval",
        )
        self.assertTrue(repair_actions["spend_confirmation_recorded"]["operator_command_handoff"][0]["approval_flags_included"])
        self.assertEqual(repair_actions["dirty_state_grouped_for_promotion"]["recommended_tool"], "scripts/write_dirty_promotion_review.py")
        self.assertEqual(repair_actions["dirty_state_grouped_for_promotion"]["receipt_path"], "Saved\\DirtyPromotionReview\\last_review_receipt.json")
        self.assertEqual(repair_actions["dirty_state_grouped_for_promotion"]["required_command"], "python scripts\\write_dirty_promotion_review.py")
        self.assertIn("receipt_current", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("receipt_stale", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("receipt_dirty_signature_match", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("current_dirty_signature", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("receipt_dirty_signature", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("evidence_review_matrix_count", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("evidence_unresolved_count", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("evidence_review_matrix_preview", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_group", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_missing_evidence_preview", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_decision_prompt_preview", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_status", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_recorded_evidence_preview", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_human_approval_recorded", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_merge_policy", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_previous_evidence_merged", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_reset_evidence", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertEqual(
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_merge_policy"],
            "preserve_existing_evidence_when_dirty_signature_and_target_match",
        )
        self.assertIn("target_review_receipt_command_template", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_approval_receipt_command_template", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_receipt_command_policy", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_operator_command_handoff", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertEqual(len(repair_actions["dirty_state_grouped_for_promotion"]["target_review_operator_command_handoff"]), 2)
        self.assertEqual(
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_operator_command_handoff"][0]["id"],
            "record_dirty_target_evidence",
        )
        self.assertFalse(
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_operator_command_handoff"][0]["requires_human_approval"]
        )
        self.assertFalse(
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_operator_command_handoff"][0]["approval_flag_included"]
        )
        self.assertTrue(
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_operator_command_handoff"][0]["no_git_mutation"]
        )
        self.assertTrue(
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_operator_command_handoff"][1]["requires_human_approval"]
        )
        self.assertTrue(
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_operator_command_handoff"][1]["approval_flag_included"]
        )
        self.assertIn("--target-owner-or-source", repair_actions["dirty_state_grouped_for_promotion"]["target_review_receipt_command_template"])
        self.assertIn("--target-focused-test-results", repair_actions["dirty_state_grouped_for_promotion"]["target_review_receipt_command_template"])
        self.assertNotIn(
            "--target-human-approval-recorded",
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_receipt_command_template"],
        )
        self.assertIn(
            "--target-human-approval-recorded",
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_approval_receipt_command_template"],
        )
        self.assertIn("explicit human approval", repair_actions["dirty_state_grouped_for_promotion"]["target_review_receipt_command_policy"])
        self.assertIn("target_review_focused_test_command_preview", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertIn("target_review_focused_test_command_handoff", repair_actions["dirty_state_grouped_for_promotion"])
        self.assertGreaterEqual(len(repair_actions["dirty_state_grouped_for_promotion"]["target_review_focused_test_command_handoff"]), 1)
        self.assertEqual(
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_focused_test_command_handoff"][0]["command_kind"],
            "local_validation",
        )
        self.assertTrue(
            repair_actions["dirty_state_grouped_for_promotion"]["target_review_focused_test_command_handoff"][0]["no_git_mutation"]
        )
        self.assertIn("target_review_sample_preview", repair_actions["dirty_state_grouped_for_promotion"])
        if repair_actions["dirty_state_grouped_for_promotion"]["evidence_review_matrix_preview"]:
            self.assertIn("missing_evidence_count", repair_actions["dirty_state_grouped_for_promotion"]["evidence_review_matrix_preview"][0])
            self.assertFalse(repair_actions["dirty_state_grouped_for_promotion"]["evidence_review_matrix_preview"][0]["promotion_allowed"])
            self.assertEqual(
                repair_actions["dirty_state_grouped_for_promotion"]["target_review_group"],
                repair_actions["dirty_state_grouped_for_promotion"]["evidence_review_matrix_preview"][0]["group"],
            )
            self.assertGreaterEqual(repair_actions["dirty_state_grouped_for_promotion"]["target_review_missing_evidence_count"], 1)
            self.assertIn(
                "human_approval_before_stage_commit_merge",
                repair_actions["dirty_state_grouped_for_promotion"]["target_review_missing_evidence_preview"],
            )
            self.assertTrue(any(
                "owner_or_source" in prompt
                for prompt in repair_actions["dirty_state_grouped_for_promotion"]["target_review_decision_prompt_preview"]
            ))
            self.assertFalse(repair_actions["dirty_state_grouped_for_promotion"]["target_review_promotion_allowed_after_receipt"])
        if repair_actions["dirty_state_grouped_for_promotion"]["target_review_focused_test_command_count"]:
            self.assertIn(
                "python",
                " ".join(repair_actions["dirty_state_grouped_for_promotion"]["target_review_focused_test_command_preview"]).lower(),
            )
        if repair_queue["recommended_next"] == "review_dirty_groups_for_promotion":
            self.assertEqual(repair_queue["next_gate"], "dirty_state_grouped_for_promotion")
            self.assertEqual(repair_queue["next_policy_area"], "wip_promotion")
            self.assertEqual(repair_queue["next_tool"], "scripts/write_dirty_promotion_review.py")
            self.assertEqual(
                repair_queue["next_target_review_group"],
                repair_actions["dirty_state_grouped_for_promotion"]["target_review_group"],
            )
            self.assertEqual(
                repair_queue["next_target_review_missing_evidence_count"],
                repair_actions["dirty_state_grouped_for_promotion"]["target_review_missing_evidence_count"],
            )
            self.assertIn(
                "human_approval_before_stage_commit_merge",
                repair_queue["next_target_review_missing_evidence_preview"],
            )
            self.assertIn("next_target_review_status", repair_queue)
            self.assertIn("next_target_review_recorded_evidence_preview", repair_queue)
            self.assertFalse(repair_queue["next_target_review_human_approval_recorded"])
            self.assertEqual(
                repair_queue["next_target_review_merge_policy"],
                repair_actions["dirty_state_grouped_for_promotion"]["target_review_merge_policy"],
            )
            self.assertFalse(repair_queue["next_target_review_reset_evidence"])
            self.assertEqual(
                repair_queue["next_target_review_receipt_command_template"],
                repair_actions["dirty_state_grouped_for_promotion"]["target_review_receipt_command_template"],
            )
            self.assertEqual(
                repair_queue["next_target_review_approval_receipt_command_template"],
                repair_actions["dirty_state_grouped_for_promotion"]["target_review_approval_receipt_command_template"],
            )
            self.assertIn("explicit human approval", repair_queue["next_target_review_receipt_command_policy"])
            self.assertEqual(
                repair_queue["next_target_review_operator_command_handoff"],
                repair_actions["dirty_state_grouped_for_promotion"]["target_review_operator_command_handoff"],
            )
            self.assertIn("next_target_review_pending_human_approval_only", repair_queue)
            self.assertIn("next_target_review_human_approval_command_handoff", repair_queue)
            if repair_queue["next_target_review_pending_human_approval_only"]:
                self.assertEqual(repair_queue["next_target_review_human_approval_gate"], "human_approval_before_stage_commit_merge")
                self.assertEqual(len(repair_queue["next_target_review_human_approval_command_handoff"]), 1)
                self.assertEqual(
                    repair_queue["next_operator_command_handoff"],
                    repair_queue["next_target_review_human_approval_command_handoff"],
                )
            else:
                self.assertEqual(
                    repair_queue["next_operator_command_handoff"],
                    repair_actions["dirty_state_grouped_for_promotion"]["target_review_operator_command_handoff"],
                )
            self.assertEqual(
                repair_queue["next_target_review_focused_test_command_handoff"],
                repair_actions["dirty_state_grouped_for_promotion"]["target_review_focused_test_command_handoff"],
            )
            self.assertGreaterEqual(repair_queue["next_target_review_focused_test_command_count"], 1)
            self.assertTrue(any(
                "promotion_intent" in prompt
                for prompt in repair_queue["next_target_review_decision_prompt_preview"]
            ))
            self.assertIn("python", " ".join(repair_queue["next_target_review_focused_test_command_preview"]).lower())
            self.assertFalse(repair_queue["next_target_review_promotion_allowed_after_receipt"])
        self.assertTrue(repair_actions["dirty_state_grouped_for_promotion"]["no_stage"])
        self.assertTrue(repair_actions["unreal_bridge_reachable"]["requires_unreal_editor"])
        self.assertEqual(repair_actions["unreal_bridge_reachable"]["receipt_path"], "Saved\\BridgePing\\last_ping_receipt.json")
        self.assertEqual(repair_actions["unreal_bridge_reachable"]["required_command"], "python scripts\\bridge_ping.py")
        self.assertIn("bridge_ping_receipt_success", repair_actions["unreal_bridge_reachable"]["evidence_required_preview"])
        action_order = {item["gate"]: item["order"] for item in repair_queue["action_preview"]}
        if "dirty_state_grouped_for_promotion" in action_order and "unreal_bridge_reachable" in action_order:
            self.assertLess(action_order["dirty_state_grouped_for_promotion"], action_order["unreal_bridge_reachable"])
        if "unreal_bridge_reachable" in action_order and "wallet_evidence_recorded" in action_order:
            self.assertLess(action_order["unreal_bridge_reachable"], action_order["wallet_evidence_recorded"])
        self.assertNotIn("api_key_masked", json.dumps(repair_queue))
        self.assertIn("blueprint_pre_read_evidence", report["readiness_policy"]["blueprint_mutation"]["missing_gates"])
        self.assertIn("compile_check_after_mutation", report["readiness_policy"]["blueprint_mutation"]["evidence_required"])
        self.assertFalse(report["readiness_policy"]["blueprint_mutation"]["allowed"])
        self.assertIn("blueprint_pre_read_evidence", report["blocking_gates"])
        self.assertIn("blueprint_compile_plan", report["blocking_gates"])
        self.assertIn("blueprint_readback_plan", report["blocking_gates"])
        self.assertEqual(repair_actions["blueprint_pre_read_evidence"]["policy_area"], "blueprint_mutation")
        self.assertTrue(repair_actions["blueprint_pre_read_evidence"]["requires_bridge"])
        self.assertTrue(repair_actions["blueprint_pre_read_evidence"]["requires_unreal_editor"])
        self.assertTrue(repair_actions["blueprint_pre_read_evidence"]["no_blueprint_mutation"])
        self.assertEqual(repair_actions["blueprint_pre_read_evidence"]["receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
        self.assertEqual(
            repair_actions["blueprint_pre_read_evidence"]["required_command"],
            "python scripts\\write_blueprint_mutation_evidence_review.py",
        )
        self.assertIn("--pre-read-evidence-recorded", repair_actions["blueprint_pre_read_evidence"]["receipt_command_template"])
        self.assertIn("--target-blueprint-path", repair_actions["blueprint_pre_read_evidence"]["receipt_command_template"])
        self.assertEqual(
            repair_actions["blueprint_pre_read_evidence"]["pre_read_evidence_recorded"],
            blueprint_evidence["pre_read_evidence_recorded"],
        )
        self.assertEqual(
            repair_actions["blueprint_pre_read_evidence"]["compile_plan_recorded"],
            blueprint_evidence["compile_plan_recorded"],
        )
        self.assertEqual(
            repair_actions["blueprint_pre_read_evidence"]["readback_plan_recorded"],
            blueprint_evidence["readback_plan_recorded"],
        )
        self.assertIn("blueprint_pre_read", repair_actions["blueprint_pre_read_evidence"]["evidence_required_preview"])
        self.assertEqual(repair_actions["blueprint_compile_plan"]["policy_area"], "blueprint_mutation")
        self.assertFalse(repair_actions["blueprint_compile_plan"]["requires_bridge"])
        self.assertTrue(repair_actions["blueprint_compile_plan"]["no_blueprint_mutation"])
        self.assertEqual(repair_actions["blueprint_compile_plan"]["receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
        self.assertIn("--compile-plan-recorded", repair_actions["blueprint_compile_plan"]["receipt_command_template"])
        self.assertIn("compile_check_after_mutation", repair_actions["blueprint_compile_plan"]["evidence_required_preview"])
        self.assertEqual(repair_actions["blueprint_readback_plan"]["policy_area"], "blueprint_mutation")
        self.assertFalse(repair_actions["blueprint_readback_plan"]["requires_bridge"])
        self.assertTrue(repair_actions["blueprint_readback_plan"]["no_blueprint_mutation"])
        self.assertEqual(repair_actions["blueprint_readback_plan"]["receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
        self.assertIn("--readback-plan-recorded", repair_actions["blueprint_readback_plan"]["receipt_command_template"])
        self.assertIn("graph_or_component_readback_after_mutation", repair_actions["blueprint_readback_plan"]["evidence_required_preview"])
        self.assertLess(action_order["unreal_bridge_reachable"], action_order["blueprint_pre_read_evidence"])
        self.assertLess(action_order["blueprint_pre_read_evidence"], action_order["blueprint_compile_plan"])
        self.assertLess(action_order["blueprint_compile_plan"], action_order["blueprint_readback_plan"])
        self.assertIn("platform_stability", report["readiness_policy"])
        self.assertIn("build_wrapper_references_ready", report["readiness_policy"]["platform_stability"]["required_gates"])
        self.assertIn("test_lane_separation", report["readiness_policy"]["platform_stability"]["required_gates"])
        self.assertIn("high_value_bridge_wrappers_covered", report["readiness_policy"]["platform_stability"]["required_gates"])
        self.assertIn(
            "offline_live_paid_test_lane_audit",
            report["readiness_policy"]["platform_stability"]["evidence_required"],
        )
        self.assertIn(
            "last_no_mutation_unittest_receipt",
            report["readiness_policy"]["wip_promotion"]["evidence_required"],
        )
        self.assertIn(
            "high_value_wrapper_coverage_audit",
            report["readiness_policy"]["platform_stability"]["evidence_required"],
        )
        self.assertIn("high_value_wrapper_coverage", report)
        self.assertEqual(report["high_value_wrapper_coverage"]["schema"], "unreal_mcp_high_value_wrapper_coverage.v1")
        self.assertEqual(report["high_value_wrapper_coverage"]["state"], "ok")
        self.assertEqual(report["high_value_wrapper_coverage"]["status"], "OK")
        self.assertTrue(report["high_value_wrapper_coverage"]["ok"])
        self.assertEqual(report["high_value_wrapper_coverage"]["capability_count"], 10)
        self.assertEqual(report["high_value_wrapper_coverage"]["covered_capability_count"], 10)
        self.assertEqual(report["high_value_wrapper_coverage"]["failing_capability_count"], 0)
        self.assertGreaterEqual(report["high_value_wrapper_coverage"]["command_count"], 14)
        self.assertEqual(report["high_value_wrapper_coverage"]["roadmap_priority_count"], 10)
        self.assertEqual(report["high_value_wrapper_coverage"]["roadmap_priority_covered_count"], 10)
        self.assertEqual(report["high_value_wrapper_coverage"]["roadmap_priority_missing_count"], 0)
        self.assertIn(
            "behavior_tree_blackboard_assignment",
            report["high_value_wrapper_coverage"]["roadmap_priority_preview"],
        )
        self.assertIn(
            "behavior_tree_task_graph_primitives",
            report["high_value_wrapper_coverage"]["roadmap_priority_preview"],
        )
        self.assertEqual(report["high_value_wrapper_coverage"]["roadmap_priority_missing_preview"], [])
        self.assertEqual(
            report["high_value_wrapper_coverage"]["schema_command_count"],
            report["high_value_wrapper_coverage"]["schema_covered_command_count"],
        )
        self.assertIn("set_behavior_tree_blackboard", report["high_value_wrapper_coverage"]["command_preview"])
        self.assertEqual(report["high_value_wrapper_coverage"]["audit_tool"], "scripts/audit_high_value_wrapper_coverage.py")
        self.assertEqual(report["high_value_wrapper_coverage"]["bridge_registry_tool"], "scripts/bridge_command_audit.py")
        self.assertEqual(report["high_value_wrapper_coverage"]["operator_command_handoff_count"], 2)
        self.assertEqual(
            report["high_value_wrapper_coverage"]["operator_command_handoff_ids"],
            ["run_high_value_wrapper_coverage_audit", "run_high_value_wrapper_offline_tests"],
        )
        self.assertEqual(
            report["high_value_wrapper_coverage"]["operator_command_handoff"][0]["command_kind"],
            "local_validation",
        )
        self.assertFalse(report["high_value_wrapper_coverage"]["operator_command_handoff"][0]["requires_bridge"])
        self.assertTrue(report["high_value_wrapper_coverage"]["operator_command_handoff"][0]["no_editor_mutation"])
        self.assertTrue(report["high_value_wrapper_coverage"]["operator_command_handoff"][0]["no_provider_call"])
        self.assertFalse(report["high_value_wrapper_coverage"]["requires_bridge"])
        self.assertTrue(report["high_value_wrapper_coverage"]["no_editor_mutation"])
        self.assertTrue(report["high_value_wrapper_coverage"]["no_provider_call"])
        self.assertTrue(report["high_value_wrapper_coverage"]["no_git_mutation"])
        self.assertIn("add_get_random_reachable_point_node", report["high_value_wrapper_coverage"]["command_preview"])
        self.assertFalse(report["high_value_wrapper_coverage"]["network_required"])
        self.assertFalse(report["high_value_wrapper_coverage"]["spend_required"])
        self.assertFalse(report["high_value_wrapper_coverage"]["unreal_editor_required"])
        self.assertIn("working_branch_is_wip", report["readiness_policy"]["platform_stability"]["required_gates"])
        self.assertIn("wip_promotion", report["readiness_policy"])
        self.assertIn("high_value_bridge_wrappers_covered", report["readiness_policy"]["wip_promotion"]["required_gates"])
        self.assertIn("dirty_state_grouped_for_promotion", report["readiness_policy"]["wip_promotion"]["required_gates"])
        self.assertIn("plugin_build_successful", report["readiness_policy"]["wip_promotion"]["required_gates"])
        self.assertIn("chat_cockpit_reachable", report["readiness_policy"]["wip_promotion"]["required_gates"])
        self.assertIn("dirty_state_grouped_or_clean", report["readiness_policy"]["wip_promotion"]["evidence_required"])
        self.assertIn("ready_for_wip_promotion", report)
        self.assertIn("branch_policy", report["readiness_policy"])
        self.assertIn("branch", report["git"])
        self.assertEqual(report["git"]["branch"]["development_branch"], "wip")
        self.assertEqual(report["git"]["branch"]["stable_branch"], "main")
        self.assertIn("ready_for_platform_stability", report)
        self.assertIn("last_plugin_build_status", report["build"])
        self.assertIn(report["build"]["last_plugin_build_status"], {"success", "failed", "unknown"})
        self.assertIn(report["build"]["build_wrapper_status"], {"ready", "missing_reference", "missing_wrapper"})
        self.assertIn("build_wrapper_project_ready", report["build"])
        self.assertIn("build_wrapper_plugin_ready", report["build"])
        self.assertIn("build_wrapper_tool_ready", report["build"])
        self.assertIn("build_health", report["build"])
        self.assertIn(report["build"]["build_health"], {"ok", "blocked", "unknown"})
        self.assertIn("last_plugin_build_warning_count", report["build"])
        self.assertIn("last_plugin_build_warning_categories", report["build"])
        self.assertIn(report["build"]["last_plugin_build_warning_severity"], {"none", "toolchain", "repo", "mixed", "unknown"})
        self.assertIn("local_build_receipt_exists", report["build"])
        self.assertIn("local_build_receipt_path", report["build"])
        self.assertIn("last_plugin_build_source", report["build"])
        self.assertIn(report["build"]["last_plugin_build_source"], {"local_receipt", "automation_log", "none"})
        self.assertIn("dirty_risk", report["git"])
        self.assertIn(report["git"]["dirty_risk"], {"clean", "moderate", "elevated", "high", "unknown"})
        self.assertIn("tracked_change_count", report["git"])
        self.assertIn("untracked_count", report["git"])
        self.assertIn("dirty_group_count", report["git"])
        self.assertIn("dirty_group_preview", report["git"])
        self.assertIn("primary_dirty_group", report["git"])
        self.assertIn("dirty_grouping_required", report["git"])
        self.assertIn("dirty_promotion_contract", report)
        dirty_promotion = report["dirty_promotion_contract"]
        self.assertEqual(dirty_promotion["schema"], "unreal_mcp_dirty_promotion_contract.v1")
        self.assertIn(dirty_promotion["state"], {"ready", "needs_grouping"})
        self.assertEqual(dirty_promotion["dirty_group_count"], report["git"]["dirty_group_count"])
        self.assertEqual(dirty_promotion["tracked_change_count"], report["git"]["tracked_change_count"])
        self.assertEqual(dirty_promotion["untracked_count"], report["git"]["untracked_count"])
        self.assertEqual(dirty_promotion["primary_dirty_group"], report["git"]["primary_dirty_group"])
        self.assertEqual(dirty_promotion["dirty_signature"], report["git"]["dirty_signature"])
        self.assertEqual(dirty_promotion["dirty_signature_algorithm"], "sha256(git_status_porcelain_v1_sorted_lines)")
        self.assertIn("dirty_promotion_receipt_matches_current_worktree", dirty_promotion["required_evidence"])
        self.assertIn("rerun_dirty_promotion_review_if_receipt_stale", dirty_promotion["safe_promotion_next_steps"])
        self.assertIn("review_receipt", dirty_promotion)
        self.assertIn(dirty_promotion["review_receipt_state"], {"missing", "review_required", "ready", "blocked", "stale"})
        self.assertIn("review_receipt_current", dirty_promotion)
        self.assertIn("review_receipt_stale", dirty_promotion)
        self.assertIn("review_receipt_dirty_signature_match", dirty_promotion)
        self.assertEqual(dirty_promotion["review_receipt_path"], "Saved\\DirtyPromotionReview\\last_review_receipt.json")
        self.assertEqual(dirty_promotion["review_receipt_required_command"], "python scripts\\write_dirty_promotion_review.py")
        self.assertIn("target_review_group", dirty_promotion)
        self.assertIn("target_review_order", dirty_promotion)
        self.assertIn("target_review_scope", dirty_promotion)
        self.assertIn("target_review_missing_evidence_preview", dirty_promotion)
        self.assertIn("target_review_decision_prompt_preview", dirty_promotion)
        self.assertIn("target_review_status", dirty_promotion)
        self.assertIn("target_review_recorded_evidence_preview", dirty_promotion)
        self.assertIn("target_review_human_approval_recorded", dirty_promotion)
        self.assertIn("target_review_merge_policy", dirty_promotion)
        self.assertIn("target_review_previous_evidence_merged", dirty_promotion)
        self.assertIn("target_review_reset_evidence", dirty_promotion)
        self.assertEqual(
            dirty_promotion["target_review_merge_policy"],
            "preserve_existing_evidence_when_dirty_signature_and_target_match",
        )
        self.assertIn("target_review_receipt_command_template", dirty_promotion)
        self.assertIn("target_review_approval_receipt_command_template", dirty_promotion)
        self.assertIn("target_review_receipt_command_policy", dirty_promotion)
        self.assertIn("target_review_operator_command_handoff", dirty_promotion)
        self.assertEqual(len(dirty_promotion["target_review_operator_command_handoff"]), 2)
        self.assertEqual(dirty_promotion["target_review_operator_command_handoff"][0]["command_kind"], "local_receipt")
        self.assertTrue(dirty_promotion["target_review_operator_command_handoff"][0]["records_evidence_only"])
        self.assertFalse(dirty_promotion["target_review_operator_command_handoff"][0]["approval_flag_included"])
        self.assertTrue(dirty_promotion["target_review_operator_command_handoff"][1]["approval_flag_included"])
        self.assertIn("target_review_focused_test_command_handoff", dirty_promotion)
        self.assertGreaterEqual(len(dirty_promotion["target_review_focused_test_command_handoff"]), 1)
        self.assertEqual(dirty_promotion["target_review_focused_test_command_handoff"][0]["command_kind"], "local_validation")
        self.assertTrue(dirty_promotion["target_review_focused_test_command_handoff"][0]["no_git_mutation"])
        self.assertIn("target_review_pending_human_approval_only", dirty_promotion)
        self.assertIn("target_review_human_approval_gate", dirty_promotion)
        self.assertIn("target_review_human_approval_command_handoff", dirty_promotion)
        self.assertIn("--target-owner-or-source", dirty_promotion["target_review_receipt_command_template"])
        self.assertNotIn("--target-human-approval-recorded", dirty_promotion["target_review_receipt_command_template"])
        self.assertIn("--target-human-approval-recorded", dirty_promotion["target_review_approval_receipt_command_template"])
        self.assertIn("target_review_focused_test_command_preview", dirty_promotion)
        self.assertIn("target_review_sample_preview", dirty_promotion)
        self.assertIn("target_review_source", dirty_promotion)
        self.assertIn(dirty_promotion["target_review_source"], {"current_review_receipt", "current_dirty_worktree"})
        self.assertFalse(dirty_promotion["target_review_promotion_allowed_after_receipt"])
        if dirty_promotion["review_receipt_current"] and dirty_promotion["review_receipt"].get("target_review_group"):
            self.assertEqual(dirty_promotion["target_review_source"], "current_review_receipt")
            self.assertEqual(
                dirty_promotion["target_review_group"],
                dirty_promotion["review_receipt"]["target_review_group"],
            )
            self.assertEqual(
                dirty_promotion["target_review_missing_evidence_count"],
                dirty_promotion["review_receipt"]["target_review_missing_evidence_count"],
            )
        self.assertIn("dirty_promotion_review_receipt", dirty_promotion["required_evidence"])
        self.assertIn("human_review_before_stage_commit_or_merge", dirty_promotion["required_evidence"])
        self.assertIn("one coherent dirty group", dirty_promotion["promotion_batch_policy"])
        self.assertIn("generated/local artifacts", dirty_promotion["artifact_policy"])
        self.assertIn("run_focused_tests_for_each_candidate_batch", dirty_promotion["safe_promotion_next_steps"])
        self.assertIn("candidate_batch_review_policy", dirty_promotion)
        self.assertIn("evidence_review_matrix", dirty_promotion)
        self.assertIn("evidence_review_matrix_count", dirty_promotion)
        self.assertIn("evidence_unresolved_count", dirty_promotion)
        self.assertIn("evidence_review_policy", dirty_promotion)
        self.assertIn("promotion_evidence_matrix_for_each_candidate_batch", dirty_promotion["required_evidence"])
        self.assertIn("focused_test_command_count", dirty_promotion)
        self.assertIn("focused_test_command_preview", dirty_promotion)
        self.assertIn("explicit human approval", dirty_promotion["candidate_batch_review_policy"])
        self.assertIn("receipt records the review target only", dirty_promotion["evidence_review_policy"])
        self.assertTrue(dirty_promotion["no_git_mutation"])
        self.assertTrue(dirty_promotion["no_stage"])
        self.assertTrue(dirty_promotion["no_commit"])
        self.assertTrue(dirty_promotion["no_clean"])
        self.assertTrue(dirty_promotion["no_delete"])
        self.assertTrue(dirty_promotion["no_branch_or_merge"])
        self.assertTrue(dirty_promotion["no_provider_call"])
        self.assertTrue(dirty_promotion["no_editor_mutation"])
        self.assertFalse(dirty_promotion["network_required"])
        self.assertFalse(dirty_promotion["spend_required"])
        self.assertFalse(dirty_promotion["unreal_editor_required"])
        if report["git"]["dirty_grouping_required"]:
            self.assertEqual(dirty_promotion["state"], "needs_grouping")
            self.assertGreaterEqual(dirty_promotion["review_batch_count"], 1)
            self.assertIn("group", dirty_promotion["review_batches"][0])
            self.assertIn("promotion_batch", dirty_promotion["review_batches"][0])
            self.assertIn("recommended_review", dirty_promotion["review_batches"][0])
            self.assertIn("focused_test_commands", dirty_promotion["review_batches"][0])
            self.assertIn("approval_evidence_required", dirty_promotion["review_batches"][0])
            self.assertFalse(dirty_promotion["review_batches"][0]["promotion_allowed_after_receipt"])
            self.assertGreaterEqual(dirty_promotion["evidence_review_matrix_count"], 1)
            self.assertEqual(dirty_promotion["evidence_review_matrix_count"], dirty_promotion["review_batch_count"])
            self.assertIn("missing_evidence", dirty_promotion["evidence_review_matrix"][0])
            self.assertIn("human_approval_before_stage_commit_merge", dirty_promotion["evidence_review_matrix"][0]["missing_evidence"])
            self.assertFalse(dirty_promotion["evidence_review_matrix"][0]["promotion_allowed"])
            self.assertTrue(dirty_promotion["target_review_group"])
            self.assertGreaterEqual(dirty_promotion["target_review_missing_evidence_count"], 1)
            self.assertIn(
                "human_approval_before_stage_commit_merge",
                dirty_promotion["target_review_missing_evidence_preview"],
            )
            self.assertTrue(any("owner_or_source" in prompt for prompt in dirty_promotion["target_review_decision_prompt_preview"]))
            self.assertGreaterEqual(dirty_promotion["target_review_focused_test_command_count"], 1)
        self.assertEqual(report["runtime"]["python_version_info"]["major"], sys.version_info.major)
        self.assertEqual(report["runtime"]["python_version_info"]["minor"], sys.version_info.minor)
        self.assertTrue(report["runtime"]["python_executable"])
        self.assertTrue(report["runtime"]["platform"])
        self.assertFalse(report["network_required"])
        self.assertFalse(report["spend_required"])
        self.assertFalse(report["unreal_editor_required"])
        self.assertEqual(report["tool_inventory"]["tool_count"], report["tool_inventory"]["recorded_count"])

    def test_readiness_policy_keeps_paid_and_blueprint_mutation_gated(self):
        module = _load_preflight_module()

        policy = module._build_readiness_policy(
            tool_inventory={
                "matches_recorded_count": True,
                "missing_category_modules": [],
            },
            bridge={"ready": True},
            chat={"ready": True},
            provider={"api_key_configured": True, "uthana_api_key_configured": True},
            git={"branch": {"current": "wip", "working_branch_ok": True}, "dirty_risk": "clean", "tracked_change_count": 0},
            build={"build_wrapper_status": "ready", "build_wrapper_existing_count": 1, "build_health": "ok", "last_plugin_build_status": "success"},
            test_lanes={"ok": True, "violation_count": 0},
        )

        self.assertTrue(policy["editor_mutation"]["allowed"])
        self.assertTrue(policy["chat_cockpit"]["allowed"])
        self.assertFalse(policy["paid_generation"]["allowed"])
        self.assertEqual(
            policy["paid_generation"]["missing_gates"],
            ["wallet_evidence_recorded", "spend_confirmation_recorded"],
        )
        self.assertFalse(policy["paid_animation_generation"]["allowed"])
        self.assertEqual(
            policy["paid_animation_generation"]["missing_gates"],
            ["wallet_evidence_recorded", "spend_confirmation_recorded"],
        )
        self.assertFalse(policy["blueprint_mutation"]["allowed"])
        self.assertIn("blueprint_readback_plan", policy["blueprint_mutation"]["missing_gates"])
        self.assertTrue(policy["platform_stability"]["allowed"])
        self.assertTrue(policy["wip_promotion"]["allowed"])
        self.assertTrue(policy["branch_policy"]["allowed"])

        lane_blocked_policy = module._build_readiness_policy(
            tool_inventory={
                "matches_recorded_count": True,
                "missing_category_modules": [],
            },
            bridge={"ready": True},
            chat={"ready": True},
            provider={"api_key_configured": True, "uthana_api_key_configured": True},
            git={"branch": {"current": "wip", "working_branch_ok": True}},
            build={"build_wrapper_status": "ready", "build_wrapper_existing_count": 1, "build_health": "ok"},
            test_lanes={"ok": False, "violation_count": 1},
        )

        self.assertFalse(lane_blocked_policy["platform_stability"]["allowed"])
        self.assertIn("test_lane_separation", lane_blocked_policy["platform_stability"]["missing_gates"])
        self.assertFalse(lane_blocked_policy["wip_promotion"]["allowed"])
        self.assertIn("no_mutation_test_lane_safe", lane_blocked_policy["wip_promotion"]["missing_gates"])

        no_mutation_blocked_policy = module._build_readiness_policy(
            tool_inventory={
                "matches_recorded_count": True,
                "missing_category_modules": [],
            },
            bridge={"ready": True},
            chat={"ready": True},
            provider={"api_key_configured": True, "uthana_api_key_configured": True},
            git={"branch": {"current": "wip", "working_branch_ok": True}, "dirty_risk": "clean", "tracked_change_count": 0},
            build={"build_wrapper_status": "ready", "build_wrapper_existing_count": 1, "build_health": "ok", "last_plugin_build_status": "success"},
            test_lanes={"ok": True, "violation_count": 0},
            no_mutation_tests={"ok": False, "mutation_count": 1},
        )

        self.assertTrue(no_mutation_blocked_policy["platform_stability"]["allowed"])
        self.assertFalse(no_mutation_blocked_policy["wip_promotion"]["allowed"])
        self.assertIn("no_mutation_test_lane_safe", no_mutation_blocked_policy["wip_promotion"]["missing_gates"])

        dirty_blocked_policy = module._build_readiness_policy(
            tool_inventory={
                "matches_recorded_count": True,
                "missing_category_modules": [],
            },
            bridge={"ready": True},
            chat={"ready": True},
            provider={"api_key_configured": True, "uthana_api_key_configured": True},
            git={"branch": {"current": "wip", "working_branch_ok": True}, "dirty_risk": "high", "tracked_change_count": 2},
            build={"build_wrapper_status": "ready", "build_wrapper_existing_count": 1, "build_health": "ok", "last_plugin_build_status": "success"},
            test_lanes={"ok": True, "violation_count": 0},
        )

        self.assertTrue(dirty_blocked_policy["platform_stability"]["allowed"])
        self.assertFalse(dirty_blocked_policy["wip_promotion"]["allowed"])
        self.assertIn("dirty_state_grouped_for_promotion", dirty_blocked_policy["wip_promotion"]["missing_gates"])

        wrapper_blocked_policy = module._build_readiness_policy(
            tool_inventory={
                "matches_recorded_count": True,
                "missing_category_modules": [],
            },
            bridge={"ready": True},
            chat={"ready": True},
            provider={"api_key_configured": True, "uthana_api_key_configured": True},
            git={"branch": {"current": "wip", "working_branch_ok": True}, "dirty_risk": "clean", "tracked_change_count": 0},
            build={"build_wrapper_status": "ready", "build_wrapper_existing_count": 1, "build_health": "ok", "last_plugin_build_status": "success"},
            test_lanes={"ok": True, "violation_count": 0},
            high_value_wrapper_coverage={"ok": False, "failing_capability_count": 1},
        )

        self.assertFalse(wrapper_blocked_policy["platform_stability"]["allowed"])
        self.assertIn("high_value_bridge_wrappers_covered", wrapper_blocked_policy["platform_stability"]["missing_gates"])
        self.assertFalse(wrapper_blocked_policy["wip_promotion"]["allowed"])
        self.assertIn("high_value_bridge_wrappers_covered", wrapper_blocked_policy["wip_promotion"]["missing_gates"])

        plugin_build_blocked_policy = module._build_readiness_policy(
            tool_inventory={
                "matches_recorded_count": True,
                "missing_category_modules": [],
            },
            bridge={"ready": True},
            chat={"ready": True},
            provider={"api_key_configured": True, "uthana_api_key_configured": True},
            git={"branch": {"current": "wip", "working_branch_ok": True}, "dirty_risk": "clean", "tracked_change_count": 0},
            build={"build_wrapper_status": "ready", "build_wrapper_existing_count": 1, "build_health": "ok", "last_plugin_build_status": "unknown"},
            test_lanes={"ok": True, "violation_count": 0},
        )

        self.assertFalse(plugin_build_blocked_policy["wip_promotion"]["allowed"])
        self.assertIn("plugin_build_successful", plugin_build_blocked_policy["wip_promotion"]["missing_gates"])

        animation_blocked_policy = module._build_readiness_policy(
            tool_inventory={
                "matches_recorded_count": True,
                "missing_category_modules": [],
            },
            bridge={"ready": True},
            chat={"ready": True},
            provider={"api_key_configured": True, "uthana_api_key_configured": False},
            git={"branch": {"current": "wip", "working_branch_ok": True}},
            build={"build_wrapper_status": "ready", "build_wrapper_existing_count": 1, "build_health": "ok"},
        )

        self.assertFalse(animation_blocked_policy["paid_animation_generation"]["allowed"])
        self.assertEqual(
            animation_blocked_policy["paid_animation_generation"]["missing_gates"][0],
            "animation_provider_api_key_configured",
        )

        blocked_policy = module._build_readiness_policy(
            tool_inventory={
                "matches_recorded_count": True,
                "missing_category_modules": [],
            },
            bridge={"ready": True},
            chat={"ready": True},
            provider={"api_key_configured": True, "uthana_api_key_configured": True},
            git={"branch": {"current": "wip", "working_branch_ok": True}},
            build={"build_wrapper_status": "missing_reference", "build_wrapper_existing_count": 1, "build_health": "blocked"},
        )

        self.assertFalse(blocked_policy["platform_stability"]["allowed"])
        self.assertEqual(blocked_policy["platform_stability"]["missing_gates"], ["build_wrapper_references_ready"])

        branch_blocked_policy = module._build_readiness_policy(
            tool_inventory={
                "matches_recorded_count": True,
                "missing_category_modules": [],
            },
            bridge={"ready": True},
            chat={"ready": True},
            provider={"api_key_configured": True, "uthana_api_key_configured": True},
            git={"branch": {"current": "main", "working_branch_ok": False}},
            build={"build_wrapper_status": "ready", "build_wrapper_existing_count": 1, "build_health": "ok"},
        )

        self.assertFalse(branch_blocked_policy["branch_policy"]["allowed"])
        self.assertIn("working_branch_is_wip", branch_blocked_policy["platform_stability"]["missing_gates"])

    def test_git_porcelain_parser_reports_dirty_risk(self):
        module = _load_preflight_module()

        clean = module._parse_git_porcelain([])
        moderate = module._parse_git_porcelain([" M README.md", "?? .mcp_artifacts/session.json"])
        high = module._parse_git_porcelain([f" M file_{index}.py" for index in range(55)])
        conflicted = module._parse_git_porcelain(["UU unreal_mcp_server/tools/example.py"])

        self.assertEqual(clean["dirty_risk"], "clean")
        self.assertEqual(clean["dirty_count"], 0)
        self.assertEqual(moderate["dirty_risk"], "moderate")
        self.assertEqual(moderate["tracked_change_count"], 1)
        self.assertEqual(moderate["untracked_count"], 1)
        self.assertEqual(moderate["generated_or_local_count"], 1)
        self.assertEqual(moderate["dirty_group_count"], 2)
        self.assertEqual(moderate["dirty_group_preview"][0]["group"], "local_artifacts")
        self.assertEqual(moderate["dirty_group_preview"][0]["untracked_count"], 1)
        self.assertIn("repo_docs", {group["group"] for group in moderate["dirty_groups"]})
        self.assertTrue(moderate["dirty_grouping_required"])
        self.assertEqual(high["dirty_risk"], "high")
        self.assertEqual(conflicted["dirty_risk"], "high")
        self.assertEqual(conflicted["status_counts"]["conflicted"], 1)

        grouped = module._parse_git_porcelain([
            " M unreal_mcp_server/chat/cockpit.py",
            " M unreal_mcp_server/tests/test_chat.py",
            "?? scripts/audit_ide_companion_readiness.py",
            " M unreal_plugin/Source/UnrealMCP/Private/UnrealMCPBridge.cpp",
        ])
        self.assertEqual(
            [row["group"] for row in grouped["dirty_group_preview"]],
            ["chat_cockpit", "scripts", "server_tests", "unreal_plugin"],
        )
        self.assertEqual(grouped["primary_dirty_group"], "chat_cockpit")

    def test_chat_status_reports_repair_contract_without_network_spend_or_editor(self):
        module = _load_preflight_module()

        status = module._chat_status("http://127.0.0.1:9", timeout_s=0.1)

        self.assertFalse(status["ready"])
        self.assertEqual(status["base_url"], "http://127.0.0.1:9")
        self.assertEqual(status["health_endpoint"], "/chat/history?limit=1")
        self.assertEqual(status["expected_transport"], "sse")
        self.assertIn("/sse", status["expected_mcp_endpoint"])
        self.assertIn("scripts\\start_chat_cockpit_server.ps1", status["startup_command"])
        self.assertIn("--transport sse", status["manual_startup_command"])
        self.assertEqual(status["startup_script"], "scripts\\start_chat_cockpit_server.ps1")
        self.assertEqual(status["startup_receipt_path"], "Saved\\ChatCockpit\\last_start_receipt.json")
        self.assertEqual(status["agent_command"], "npm run chat:agent")
        self.assertFalse(status["network_required"])
        self.assertFalse(status["spend_required"])
        self.assertFalse(status["unreal_editor_required"])
        self.assertIn("tcp_ready", status)
        self.assertIn("tcp", status)
        self.assertIn("failure_mode", status)
        repair = module._chat_cockpit_repair_contract(status)
        self.assertEqual(repair["schema"], "unreal_mcp_chat_cockpit_repair_contract.v1")
        self.assertEqual(repair["state"], "needs_startup")
        self.assertEqual(repair["health_endpoint"], "/chat/history?limit=1")
        self.assertIn("scripts\\start_chat_cockpit_server.ps1", repair["startup_command"])
        self.assertIn("--transport sse", repair["manual_startup_command"])
        self.assertEqual(repair["startup_script"], "scripts\\start_chat_cockpit_server.ps1")
        self.assertEqual(repair["startup_receipt_path"], "Saved\\ChatCockpit\\last_start_receipt.json")
        self.assertIn("Invoke-WebRequest", repair["proof_command"])
        self.assertIn("messages list", repair["proof_expected"])
        self.assertIn("chat_cockpit_start_receipt_success", repair["required_evidence"])
        self.assertIn("chat_history_http_200", repair["required_evidence"])
        self.assertTrue(repair["no_process_start"])
        self.assertTrue(repair["no_port_kill"])
        self.assertFalse(repair["network_required"])
        self.assertFalse(repair["spend_required"])
        self.assertFalse(repair["unreal_editor_required"])

    def test_dirty_promotion_review_receipt_parser_reports_missing_ready_and_review_required(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing = module._dirty_promotion_review_receipt_status(tmp_path / "missing.json")
            ready_path = tmp_path / "ready.json"
            review_path = tmp_path / "review.json"
            stale_path = tmp_path / "stale.json"
            ready_path.write_text(json.dumps({
                "schema": "unreal_mcp_dirty_promotion_review_receipt.v1",
                "status": "ready",
                "dirty_group_count": 0,
                "dirty_signature": "clean-signature",
                "dirty_signature_algorithm": "sha256(git_status_porcelain_v1_sorted_lines)",
                "dirty_signature_entry_count": 0,
                "tracked_change_count": 0,
                "review_batch_count": 0,
                "ready_for_promotion": True,
            }), encoding="utf-8")
            review_path.write_text(json.dumps({
                "schema": "unreal_mcp_dirty_promotion_review_receipt.v1",
                "status": "review_required",
                "dirty_group_count": 2,
                "dirty_signature": "current-signature",
                "dirty_signature_algorithm": "sha256(git_status_porcelain_v1_sorted_lines)",
                "dirty_signature_entry_count": 7,
                "tracked_change_count": 3,
                "untracked_count": 4,
                "review_batch_count": 2,
                "primary_dirty_group": "server_tests",
                "promotion_batch_policy": "Review one coherent dirty group at a time.",
                "artifact_policy": "Keep generated/local artifacts ignored.",
                "safe_promotion_next_steps": ["write_dirty_promotion_review_receipt", "run_focused_tests_for_each_candidate_batch"],
                "evidence_review_matrix": [
                    {
                        "group": "server_tests",
                        "order": 1,
                        "candidate_batch_scope": "tracked_review",
                        "missing_evidence": ["owner_or_source", "human_approval_before_stage_commit_merge"],
                        "required_evidence": ["owner_or_source", "human_approval_before_stage_commit_merge"],
                        "missing_evidence_count": 2,
                        "promotion_allowed": False,
                        "tracked_count": 3,
                        "untracked_count": 4,
                    }
                ],
                "evidence_review_matrix_count": 1,
                "evidence_unresolved_count": 2,
                "evidence_review_policy": "A dirty-promotion receipt records the review target only.",
                "target_review_group": "server_tests",
                "target_review_order": 1,
                "target_review_scope": "tracked_review",
                "target_review_tracked_count": 3,
                "target_review_untracked_count": 4,
                "target_review_missing_evidence_count": 2,
                "target_review_missing_evidence_preview": ["owner_or_source", "human_approval_before_stage_commit_merge"],
                "target_review_required_evidence_preview": ["owner_or_source", "human_approval_before_stage_commit_merge"],
                "target_review_decision_prompt_preview": ["owner_or_source: identify test owner"],
                "target_review_focused_test_command_handoff": [
                    {
                        "id": "run_dirty_target_focused_test_1",
                        "command": "python -m unittest unreal_mcp_server.tests.test_chat",
                        "command_kind": "local_validation",
                        "no_git_mutation": True,
                    }
                ],
                "target_review_focused_test_command_count": 1,
                "target_review_focused_test_command_preview": ["python -m unittest unreal_mcp_server.tests.test_chat"],
                "target_review_sample_preview": [" M unreal_mcp_server/tests/test_chat.py"],
                "target_review_promotion_allowed_after_receipt": False,
                "ready_for_promotion": False,
            }), encoding="utf-8")
            stale_path.write_text(json.dumps({
                "schema": "unreal_mcp_dirty_promotion_review_receipt.v1",
                "status": "review_required",
                "dirty_group_count": 1,
                "dirty_signature": "old-signature",
                "dirty_signature_algorithm": "sha256(git_status_porcelain_v1_sorted_lines)",
                "dirty_signature_entry_count": 1,
                "tracked_change_count": 1,
                "review_batch_count": 1,
                "ready_for_promotion": False,
            }), encoding="utf-8")

            ready = module._dirty_promotion_review_receipt_status(ready_path)
            review = module._dirty_promotion_review_receipt_status(
                review_path,
                current_git={"dirty_signature": "current-signature"},
            )
            stale = module._dirty_promotion_review_receipt_status(
                stale_path,
                current_git={"dirty_signature": "new-signature"},
            )

        self.assertFalse(missing["receipt_exists"])
        self.assertEqual(missing["state"], "missing")
        self.assertEqual(missing["required_command"], "python scripts\\write_dirty_promotion_review.py")
        self.assertTrue(ready["receipt_exists"])
        self.assertEqual(ready["state"], "ready")
        self.assertEqual(ready["tracked_change_count"], 0)
        self.assertEqual(review["state"], "review_required")
        self.assertEqual(review["dirty_signature"], "current-signature")
        self.assertEqual(review["dirty_signature_check"], "match")
        self.assertTrue(review["dirty_signature_match"])
        self.assertEqual(review["dirty_group_count"], 2)
        self.assertEqual(review["primary_dirty_group"], "server_tests")
        self.assertIn("one coherent dirty group", review["promotion_batch_policy"])
        self.assertIn("generated/local artifacts", review["artifact_policy"])
        self.assertIn("run_focused_tests_for_each_candidate_batch", review["safe_promotion_next_steps"])
        self.assertEqual(review["evidence_review_matrix_count"], 1)
        self.assertEqual(review["evidence_unresolved_count"], 2)
        self.assertIn("owner_or_source", review["evidence_review_matrix"][0]["missing_evidence"])
        self.assertIn("review target only", review["evidence_review_policy"])
        self.assertEqual(review["target_review_group"], "server_tests")
        self.assertEqual(review["target_review_order"], 1)
        self.assertEqual(review["target_review_scope"], "tracked_review")
        self.assertEqual(review["target_review_tracked_count"], 3)
        self.assertEqual(review["target_review_untracked_count"], 4)
        self.assertEqual(review["target_review_missing_evidence_count"], 2)
        self.assertIn("human_approval_before_stage_commit_merge", review["target_review_missing_evidence_preview"])
        self.assertIn("owner_or_source", review["target_review_required_evidence_preview"])
        self.assertIn("owner_or_source", review["target_review_decision_prompt_preview"][0])
        self.assertEqual(len(review["target_review_focused_test_command_handoff"]), 1)
        self.assertEqual(review["target_review_focused_test_command_handoff"][0]["id"], "run_dirty_target_focused_test_1")
        self.assertEqual(review["target_review_focused_test_command_handoff"][0]["command_kind"], "local_validation")
        self.assertTrue(review["target_review_focused_test_command_handoff"][0]["no_git_mutation"])
        self.assertEqual(review["target_review_focused_test_command_count"], 1)
        self.assertIn("test_chat", review["target_review_focused_test_command_preview"][0])
        self.assertIn("test_chat.py", review["target_review_sample_preview"][0])
        self.assertFalse(review["target_review_promotion_allowed_after_receipt"])
        self.assertFalse(review["network_required"])
        self.assertFalse(review["spend_required"])
        self.assertFalse(review["unreal_editor_required"])
        self.assertTrue(review["no_git_mutation"])
        self.assertTrue(review["no_stage"])
        self.assertTrue(review["no_commit"])
        self.assertTrue(review["no_provider_call"])
        self.assertTrue(review["no_editor_mutation"])
        self.assertEqual(stale["state"], "stale")
        self.assertEqual(stale["dirty_signature_check"], "mismatch")
        self.assertFalse(stale["dirty_signature_match"])
        self.assertEqual(stale["current_dirty_signature"], "new-signature")

    def test_platform_stability_review_receipt_parser_reports_missing_ready_and_review_required(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing = module._platform_stability_review_receipt_status(tmp_path / "missing.json")
            ready_path = tmp_path / "ready.json"
            review_path = tmp_path / "review.json"
            ready_path.write_text(json.dumps({
                "schema": "unreal_mcp_platform_stability_review_receipt.v1",
                "status": "ready",
                "ready_for_platform_stability": True,
                "ready_for_wip_promotion": True,
                "tool_registry_reproducible": True,
                "tool_count": 667,
                "recorded_tool_count": 667,
                "partial_tool_count": 128,
                "blocking_gate_count": 0,
                "blocking_gate_preview": [],
                "readiness_repair_action_count": 0,
                "readiness_repair_recommended_next": "none",
                "readiness_repair_action_preview": [],
                "test_lane_ok": True,
                "paid_provider_smoke_contract_ok": True,
                "paid_provider_smoke_manual_command": "python -m unittest unreal_mcp_server.tests.paid_provider_generative_smoke",
                "paid_provider_smoke_required_env_vars": ["RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE"],
                "paid_provider_smoke_no_spend_tools": ["gen_tripo_get_credit_balance", "gen_uthana_get_account"],
                "paid_provider_smoke_forbidden_tokens_present": [],
                "paid_provider_smoke_manual_spend_required": False,
                "paid_provider_smoke_no_task_submission": True,
                "paid_provider_smoke_no_download": True,
                "paid_provider_smoke_no_import": True,
                "blueprint_mutation_evidence_receipt_state": "ready",
                "blueprint_mutation_evidence_receipt_status": "ready",
                "blueprint_mutation_evidence_receipt_path": "Saved\\BlueprintMutationEvidence\\last_review_receipt.json",
                "blueprint_mutation_evidence_required_command": "python scripts\\write_blueprint_mutation_evidence_review.py",
                "blueprint_mutation_pre_read_evidence_recorded": True,
                "blueprint_mutation_compile_plan_recorded": True,
                "blueprint_mutation_readback_plan_recorded": True,
                "blueprint_mutation_target_blueprint_path": "/Game/Test/BP_Test",
                "blueprint_mutation_intended_summary": "add interaction event",
                "blueprint_mutation_evidence_required_preview": ["blueprint_pre_read", "compile_check_after_mutation"],
                "blueprint_mutation_evidence_no_blueprint_mutation": True,
                "blueprint_mutation_evidence_no_compile": True,
                "no_mutation_test_ok": True,
                "no_mutation_test_operator_command_handoff": [
                    {
                        "id": "run_no_mutation_unittest",
                        "command": "python scripts\\run_no_mutation_unittest.py",
                        "no_editor_mutation": True,
                    }
                ],
                "no_mutation_test_operator_command_handoff_ids": ["run_no_mutation_unittest"],
                "no_mutation_test_operator_command_handoff_count": 1,
                "provider_config_operator_command_handoff": [
                    {
                        "id": "write_provider_config_review_receipt",
                        "command": "python scripts\\write_provider_config_review.py",
                        "no_provider_call": True,
                        "no_editor_mutation": True,
                    }
                ],
                "provider_config_operator_command_handoff_ids": ["write_provider_config_review_receipt"],
                "provider_config_operator_command_handoff_count": 1,
                "high_value_wrappers_covered": True,
                "build_wrapper_status": "ready",
                "build_health": "ready",
                "last_plugin_build_status": "success",
            }), encoding="utf-8")
            review_path.write_text(json.dumps({
                "schema": "unreal_mcp_platform_stability_review_receipt.v1",
                "status": "review_required",
                "ready_for_platform_stability": False,
                "ready_for_wip_promotion": False,
                "tool_registry_reproducible": True,
                "tool_count": 667,
                "recorded_count": 667,
                "partial_tool_count": 128,
                "blocking_gate_count": 3,
                "blocking_gate_preview": [
                    "unreal_bridge_reachable",
                    "blueprint_pre_read_evidence",
                    "blueprint_compile_plan",
                ],
                "readiness_repair_action_count": 3,
                "readiness_repair_recommended_next": "review_dirty_groups_for_promotion",
                "readiness_repair_next_gate": "dirty_state_grouped_for_promotion",
                "readiness_repair_next_policy_area": "wip_promotion",
                "readiness_repair_next_tool": "scripts/write_dirty_promotion_review.py",
                "readiness_repair_next_requires_bridge": False,
                "readiness_repair_next_requires_network": False,
                "readiness_repair_next_requires_spend": False,
                "readiness_repair_action_preview": [
                    {
                        "gate": "dirty_state_grouped_for_promotion",
                        "action_id": "review_dirty_groups_for_promotion",
                        "policy_area": "wip_promotion",
                        "recommended_tool": "scripts/write_dirty_promotion_review.py",
                    },
                    {
                        "gate": "unreal_bridge_reachable",
                        "action_id": "verify_unreal_bridge_reachability",
                        "policy_area": "editor_mutation",
                        "recommended_tool": "scripts/bridge_ping.py",
                    },
                ],
                "blueprint_mutation_evidence_receipt_state": "missing_evidence",
                "blueprint_mutation_evidence_receipt_status": "missing_evidence",
                "blueprint_mutation_evidence_receipt_path": "Saved\\BlueprintMutationEvidence\\last_review_receipt.json",
                "blueprint_mutation_evidence_required_command": "python scripts\\write_blueprint_mutation_evidence_review.py",
                "blueprint_mutation_pre_read_evidence_recorded": False,
                "blueprint_mutation_compile_plan_recorded": False,
                "blueprint_mutation_readback_plan_recorded": False,
                "blueprint_mutation_evidence_required_preview": ["blueprint_pre_read", "compile_check_after_mutation"],
                "blueprint_mutation_evidence_no_editor_mutation": True,
                "blueprint_mutation_evidence_no_blueprint_mutation": True,
                "blueprint_mutation_evidence_no_compile": True,
                "blueprint_mutation_evidence_no_save": True,
                "blueprint_mutation_evidence_no_pie": True,
                "test_lane_ok": True,
                "no_mutation_test_ok": False,
                "no_mutation_test_operator_command_handoff": [
                    {
                        "id": "run_no_mutation_unittest",
                        "command": "python scripts\\run_no_mutation_unittest.py",
                        "no_editor_mutation": True,
                    }
                ],
                "no_mutation_test_operator_command_handoff_ids": ["run_no_mutation_unittest"],
                "no_mutation_test_operator_command_handoff_count": 1,
                "provider_config_operator_command_handoff": [
                    {
                        "id": "write_provider_config_review_receipt",
                        "command": "python scripts\\write_provider_config_review.py",
                        "no_provider_call": True,
                        "no_editor_mutation": True,
                    }
                ],
                "provider_config_operator_command_handoff_ids": ["write_provider_config_review_receipt"],
                "provider_config_operator_command_handoff_count": 1,
                "high_value_wrappers_covered": True,
                "dirty_promotion_review_receipt_state": "review_required",
                "dirty_promotion_review_receipt_current": True,
                "dirty_promotion_review_receipt_stale": False,
                "dirty_promotion_review_receipt_signature_match": True,
                "dirty_signature_algorithm": "sha256(git_status_porcelain_v1_sorted_lines)",
                "dirty_signature_entry_count": 222,
                "dirty_promotion_review_batch_count": 8,
                "dirty_promotion_evidence_unresolved_count": 47,
                "dirty_target_review_group": "project_knowledge",
                "dirty_target_review_order": 1,
                "dirty_target_review_scope": "tracked_review",
                "dirty_target_review_tracked_count": 2,
                "dirty_target_review_untracked_count": 64,
                "dirty_target_review_missing_evidence_count": 6,
                "dirty_target_review_missing_evidence_preview": ["owner_or_source", "tracked_diff_review"],
                "dirty_target_review_focused_test_command_count": 2,
                "dirty_target_review_focused_test_command_preview": ["python scripts\\audit_ide_companion_readiness.py --json"],
                "dirty_target_review_sample_preview": [" M knowledge_base/Projects/Insanitii/INDEX.md"],
                "dirty_target_review_promotion_allowed_after_receipt": False,
                "platform_missing_gate_count": 1,
                "wip_promotion_missing_gate_count": 2,
            }), encoding="utf-8")

            ready = module._platform_stability_review_receipt_status(ready_path)
            review = module._platform_stability_review_receipt_status(review_path)

        self.assertFalse(missing["receipt_exists"])
        self.assertEqual(missing["state"], "missing")
        self.assertEqual(missing["required_command"], "python scripts\\write_platform_stability_review.py")
        self.assertEqual(missing["tool_count"], 0)
        self.assertEqual(missing["recorded_tool_count"], 0)
        self.assertEqual(missing["partial_tool_count"], 0)
        self.assertEqual(missing["blocking_gate_count"], 0)
        self.assertEqual(missing["blocking_gate_preview"], [])
        self.assertEqual(missing["readiness_repair_action_count"], 0)
        self.assertEqual(missing["readiness_repair_recommended_next"], "none")
        self.assertEqual(missing["readiness_repair_action_preview"], [])
        self.assertEqual(missing["blueprint_mutation_evidence_receipt_state"], "missing")
        self.assertEqual(missing["blueprint_mutation_evidence_receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
        self.assertEqual(missing["blueprint_mutation_evidence_required_command"], "python scripts\\write_blueprint_mutation_evidence_review.py")
        self.assertFalse(missing["blueprint_mutation_pre_read_evidence_recorded"])
        self.assertFalse(missing["blueprint_mutation_compile_plan_recorded"])
        self.assertFalse(missing["blueprint_mutation_readback_plan_recorded"])
        self.assertTrue(missing["blueprint_mutation_evidence_no_blueprint_mutation"])
        self.assertTrue(missing["blueprint_mutation_evidence_no_compile"])
        self.assertEqual(missing["provider_config_operator_command_handoff_count"], 0)
        self.assertEqual(missing["provider_config_operator_command_handoff_ids"], [])
        self.assertEqual(missing["provider_config_operator_command_handoff"], [])
        self.assertTrue(ready["receipt_exists"])
        self.assertEqual(ready["state"], "ready")
        self.assertTrue(ready["ready_for_platform_stability"])
        self.assertEqual(ready["tool_count"], 667)
        self.assertEqual(ready["recorded_tool_count"], 667)
        self.assertEqual(ready["partial_tool_count"], 128)
        self.assertEqual(ready["blocking_gate_count"], 0)
        self.assertEqual(ready["blocking_gate_preview"], [])
        self.assertEqual(ready["readiness_repair_action_count"], 0)
        self.assertEqual(ready["readiness_repair_recommended_next"], "none")
        self.assertEqual(ready["readiness_repair_action_preview"], [])
        self.assertTrue(ready["paid_provider_smoke_contract_ok"])
        self.assertIn("paid_provider_generative_smoke", ready["paid_provider_smoke_manual_command"])
        self.assertIn("RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE", ready["paid_provider_smoke_required_env_vars"])
        self.assertIn("gen_uthana_get_account", ready["paid_provider_smoke_no_spend_tools"])
        self.assertEqual(ready["paid_provider_smoke_forbidden_tokens_present"], [])
        self.assertFalse(ready["paid_provider_smoke_manual_spend_required"])
        self.assertTrue(ready["paid_provider_smoke_no_task_submission"])
        self.assertTrue(ready["paid_provider_smoke_no_download"])
        self.assertTrue(ready["paid_provider_smoke_no_import"])
        self.assertEqual(ready["blueprint_mutation_evidence_receipt_state"], "ready")
        self.assertEqual(ready["blueprint_mutation_evidence_receipt_status"], "ready")
        self.assertEqual(ready["blueprint_mutation_evidence_receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
        self.assertTrue(ready["blueprint_mutation_pre_read_evidence_recorded"])
        self.assertTrue(ready["blueprint_mutation_compile_plan_recorded"])
        self.assertTrue(ready["blueprint_mutation_readback_plan_recorded"])
        self.assertEqual(ready["blueprint_mutation_target_blueprint_path"], "/Game/Test/BP_Test")
        self.assertIn("blueprint_pre_read", ready["blueprint_mutation_evidence_required_preview"])
        self.assertTrue(ready["blueprint_mutation_evidence_no_blueprint_mutation"])
        self.assertEqual(ready["no_mutation_test_operator_command_handoff_count"], 1)
        self.assertEqual(ready["no_mutation_test_operator_command_handoff_ids"], ["run_no_mutation_unittest"])
        self.assertEqual(ready["no_mutation_test_operator_command_handoff"][0]["command"], "python scripts\\run_no_mutation_unittest.py")
        self.assertEqual(ready["provider_config_operator_command_handoff_count"], 1)
        self.assertEqual(ready["provider_config_operator_command_handoff_ids"], ["write_provider_config_review_receipt"])
        self.assertEqual(ready["provider_config_operator_command_handoff"][0]["command"], "python scripts\\write_provider_config_review.py")
        self.assertTrue(ready["provider_config_operator_command_handoff"][0]["no_provider_call"])
        self.assertTrue(ready["provider_config_operator_command_handoff"][0]["no_editor_mutation"])
        self.assertEqual(review["state"], "review_required")
        self.assertFalse(review["ready_for_platform_stability"])
        self.assertEqual(review["tool_count"], 667)
        self.assertEqual(review["recorded_tool_count"], 667)
        self.assertEqual(review["partial_tool_count"], 128)
        self.assertEqual(review["blocking_gate_count"], 3)
        self.assertIn("blueprint_pre_read_evidence", review["blocking_gate_preview"])
        self.assertIn("blueprint_compile_plan", review["blocking_gate_preview"])
        self.assertEqual(review["readiness_repair_action_count"], 3)
        self.assertEqual(review["readiness_repair_recommended_next"], "review_dirty_groups_for_promotion")
        self.assertEqual(review["readiness_repair_next_gate"], "dirty_state_grouped_for_promotion")
        self.assertEqual(review["readiness_repair_next_policy_area"], "wip_promotion")
        self.assertEqual(review["readiness_repair_next_tool"], "scripts/write_dirty_promotion_review.py")
        self.assertFalse(review["readiness_repair_next_requires_bridge"])
        self.assertFalse(review["readiness_repair_next_requires_network"])
        self.assertFalse(review["readiness_repair_next_requires_spend"])
        self.assertEqual(review["blueprint_mutation_evidence_receipt_state"], "missing_evidence")
        self.assertFalse(review["blueprint_mutation_pre_read_evidence_recorded"])
        self.assertFalse(review["blueprint_mutation_compile_plan_recorded"])
        self.assertFalse(review["blueprint_mutation_readback_plan_recorded"])
        self.assertIn("compile_check_after_mutation", review["blueprint_mutation_evidence_required_preview"])
        self.assertTrue(review["blueprint_mutation_evidence_no_editor_mutation"])
        self.assertTrue(review["blueprint_mutation_evidence_no_save"])
        self.assertEqual(review["no_mutation_test_operator_command_handoff_count"], 1)
        self.assertEqual(review["no_mutation_test_operator_command_handoff_ids"], ["run_no_mutation_unittest"])
        self.assertEqual(review["provider_config_operator_command_handoff_count"], 1)
        self.assertEqual(review["provider_config_operator_command_handoff_ids"], ["write_provider_config_review_receipt"])
        self.assertEqual(review["readiness_repair_action_preview"][0]["gate"], "dirty_state_grouped_for_promotion")
        self.assertEqual(review["readiness_repair_action_preview"][1]["recommended_tool"], "scripts/bridge_ping.py")
        self.assertEqual(review["dirty_promotion_review_receipt_state"], "review_required")
        self.assertTrue(review["dirty_promotion_review_receipt_current"])
        self.assertFalse(review["dirty_promotion_review_receipt_stale"])
        self.assertTrue(review["dirty_promotion_review_receipt_signature_match"])
        self.assertEqual(review["dirty_signature_algorithm"], "sha256(git_status_porcelain_v1_sorted_lines)")
        self.assertEqual(review["dirty_signature_entry_count"], 222)
        self.assertEqual(review["dirty_promotion_review_batch_count"], 8)
        self.assertEqual(review["dirty_promotion_evidence_unresolved_count"], 47)
        self.assertEqual(review["dirty_target_review_group"], "project_knowledge")
        self.assertEqual(review["dirty_target_review_order"], 1)
        self.assertEqual(review["dirty_target_review_scope"], "tracked_review")
        self.assertEqual(review["dirty_target_review_tracked_count"], 2)
        self.assertEqual(review["dirty_target_review_untracked_count"], 64)
        self.assertEqual(review["dirty_target_review_missing_evidence_count"], 6)
        self.assertIn("tracked_diff_review", review["dirty_target_review_missing_evidence_preview"])
        self.assertEqual(review["dirty_target_review_focused_test_command_count"], 2)
        self.assertIn("audit_ide_companion_readiness", review["dirty_target_review_focused_test_command_preview"][0])
        self.assertIn("Insanitii/INDEX.md", review["dirty_target_review_sample_preview"][0])
        self.assertFalse(review["dirty_target_review_promotion_allowed_after_receipt"])
        self.assertEqual(review["platform_missing_gate_count"], 1)
        self.assertFalse(review["network_required"])
        self.assertFalse(review["spend_required"])
        self.assertFalse(review["unreal_editor_required"])
        self.assertTrue(review["no_provider_call"])
        self.assertTrue(review["no_editor_mutation"])
        self.assertTrue(review["no_git_mutation"])

    def test_bridge_ping_receipt_parser_reports_missing_success_and_failure(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing = module._bridge_ping_receipt_status(tmp_path / "missing.json")
            success_path = tmp_path / "success.json"
            failed_path = tmp_path / "failed.json"
            success_path.write_text(json.dumps({
                "schema": "unreal_mcp_bridge_ping_receipt.v1",
                "status": "success",
                "exit_code": 0,
                "successful_bridge_ping": True,
                "command_status": "success",
                "actor_count": 3,
                "host": "127.0.0.1",
                "port": 55655,
            }), encoding="utf-8")
            failed_path.write_text(json.dumps({
                "schema": "unreal_mcp_bridge_ping_receipt.v1",
                "status": "failed",
                "exit_code": 1,
                "successful_bridge_ping": False,
                "error": "ConnectionRefusedError",
            }), encoding="utf-8")

            success = module._bridge_ping_receipt_status(success_path)
            failed = module._bridge_ping_receipt_status(failed_path)

        self.assertFalse(missing["receipt_exists"])
        self.assertEqual(missing["state"], "missing")
        self.assertEqual(missing["required_command"], "python scripts\\bridge_ping.py")
        self.assertEqual(missing["operator_command_handoff_count"], 1)
        self.assertEqual(missing["operator_command_handoff_ids"], ["verify_unreal_bridge_ping"])
        self.assertEqual(missing["operator_command_handoff"][0]["receipt_path"], "Saved\\BridgePing\\last_ping_receipt.json")
        self.assertTrue(missing["operator_command_handoff"][0]["requires_bridge"])
        self.assertTrue(success["receipt_exists"])
        self.assertEqual(success["state"], "ok")
        self.assertTrue(success["successful_bridge_ping"])
        self.assertEqual(success["actor_count"], 3)
        self.assertEqual(success["operator_command_handoff"][0]["id"], "verify_unreal_bridge_ping")
        self.assertEqual(failed["state"], "blocked")
        self.assertFalse(failed["successful_bridge_ping"])
        self.assertTrue(failed["unreal_editor_required"])
        self.assertFalse(failed["spend_required"])
        self.assertTrue(failed["no_editor_mutation"])
        self.assertTrue(failed["no_git_mutation"])

    def test_dirty_promotion_review_script_is_receipt_based_and_non_destructive(self):
        text = DIRTY_REVIEW_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("unreal_mcp_dirty_promotion_review_receipt.v1", text)
        self.assertIn("Saved", text)
        self.assertIn("DirtyPromotionReview", text)
        self.assertIn("DIRTY_PROMOTION_RECEIPT=", text)
        self.assertIn("DIRTY_PROMOTION_REVIEW_BATCHES=", text)
        self.assertIn("DIRTY_PROMOTION_FOCUSED_TEST_COMMANDS=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_REVIEW=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_SCOPE=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_TRACKED=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_UNTRACKED=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_SAMPLE=", text)
        self.assertIn("--target-owner-or-source", text)
        self.assertIn("--target-human-approval-recorded", text)
        self.assertIn("--reset-target-evidence", text)
        self.assertIn("preserve_existing_evidence_when_dirty_signature_and_target_match", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_STATUS=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_RECORDED_EVIDENCE=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_MISSING_EVIDENCE=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_REQUIRED_EVIDENCE=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_DECISION_PROMPTS=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_EVIDENCE_COMMAND_TEMPLATE=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_APPROVAL_COMMAND_TEMPLATE=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_HUMAN_APPROVAL_RECORDED=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_PROMOTION_ALLOWED=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_FOCUSED_TEST_COMMANDS=", text)
        self.assertIn("DIRTY_PROMOTION_TARGET_FOCUSED_TEST_PREVIEW=", text)
        self.assertIn("DIRTY_PROMOTION_NEXT_STEP=", text)
        self.assertIn("\"no_git_mutation\": True", text)
        self.assertIn("\"no_stage\": True", text)
        self.assertIn("\"no_commit\": True", text)
        self.assertIn("\"no_clean\": True", text)
        self.assertIn("\"no_delete\": True", text)
        self.assertIn("\"no_branch_or_merge\": True", text)
        self.assertIn("\"no_provider_call\": True", text)
        self.assertIn("\"no_editor_mutation\": True", text)
        self.assertIn("promotion_batch_policy", text)
        self.assertIn("artifact_policy", text)
        self.assertIn("safe_promotion_next_steps", text)
        self.assertIn("candidate_batch_review_policy", text)
        self.assertIn("evidence_review_matrix", text)
        self.assertIn("evidence_unresolved_count", text)
        self.assertIn("DIRTY_PROMOTION_EVIDENCE_UNRESOLVED=", text)
        self.assertIn("focused_test_command_preview", text)
        self.assertIn("target_review_group", text)
        self.assertIn("target_review_missing_evidence_preview", text)
        self.assertIn("target_review_focused_test_command_preview", text)
        self.assertIn("target_review_sample_preview", text)
        self.assertNotIn("git add", text)
        self.assertNotIn("git commit", text)
        self.assertNotIn("git clean", text)

    def test_dirty_promotion_review_writer_merges_same_signature_target_evidence(self):
        module = _load_dirty_review_module()

        with _temporary_untracked_git_change():
            owner_only = module.build_receipt({
                "target_review_owner_or_source": "codex local WIP review",
                "target_review_promotion_intent": "keep_wip",
            }, reset_target_evidence=True)
            merged = module.build_receipt({
                "target_review_focused_test_results": "audit and no-mutation tests passed",
                "target_review_artifact_policy_decision": "keep generated artifacts ignored unless explicitly promoted",
                "target_review_tracked_diff_review": "tracked docs and tests reviewed as one server_tests batch",
            }, previous_receipt=owner_only)
            reset = module.build_receipt({
                "target_review_focused_test_results": "fresh focused test note only",
            }, previous_receipt=owner_only, reset_target_evidence=True)
            stale_previous = dict(owner_only)
            stale_previous["dirty_signature"] = "0" * 64
            stale = module.build_receipt({
                "target_review_focused_test_results": "fresh focused test note only",
            }, previous_receipt=stale_previous)

        self.assertFalse(owner_only["target_review_previous_evidence_merged"])
        self.assertEqual(owner_only["target_review_recorded_evidence_count"], 2)
        self.assertGreaterEqual(len(owner_only["target_review_focused_test_command_handoff"]), 1)
        self.assertEqual(owner_only["target_review_focused_test_command_handoff"][0]["command_kind"], "local_validation")
        self.assertTrue(owner_only["target_review_focused_test_command_handoff"][0]["requires_human_review"])
        self.assertTrue(owner_only["target_review_focused_test_command_handoff"][0]["no_git_mutation"])
        self.assertTrue(merged["target_review_previous_evidence_merged"])
        self.assertFalse(merged["target_review_reset_evidence"])
        self.assertIn("owner_or_source", merged["target_review_recorded_evidence_preview"])
        self.assertIn("promotion_intent", merged["target_review_recorded_evidence_preview"])
        self.assertIn("focused_test_results", merged["target_review_recorded_evidence_preview"])
        self.assertIn("artifact_policy_decision", merged["target_review_recorded_evidence_preview"])
        self.assertIn("tracked_diff_review", merged["target_review_recorded_evidence_preview"])
        self.assertTrue(merged["target_review_pending_human_approval_only"])
        self.assertEqual(merged["target_review_human_approval_gate"], "human_approval_before_stage_commit_merge")
        self.assertEqual(len(merged["target_review_human_approval_command_handoff"]), 1)
        self.assertEqual(merged["target_review_human_approval_command_handoff"][0]["id"], "record_dirty_target_human_approval")
        self.assertTrue(merged["target_review_human_approval_command_handoff"][0]["approval_flag_included"])
        self.assertFalse(merged["target_review_promotion_allowed_after_receipt"])
        self.assertEqual(
            merged["target_review_merge_policy"],
            "preserve_existing_evidence_when_dirty_signature_and_target_match",
        )
        self.assertFalse(reset["target_review_previous_evidence_merged"])
        self.assertTrue(reset["target_review_reset_evidence"])
        self.assertNotIn("owner_or_source", reset["target_review_recorded_evidence_preview"])
        self.assertFalse(stale["target_review_previous_evidence_merged"])
        self.assertNotIn("owner_or_source", stale["target_review_recorded_evidence_preview"])
        with self.assertRaises(ValueError):
            module.build_receipt({
                "target_review_owner_or_source": "a" * 32,
            }, reset_target_evidence=True)

    def test_platform_stability_review_script_is_receipt_based_and_non_destructive(self):
        text = PLATFORM_STABILITY_REVIEW_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("unreal_mcp_platform_stability_review_receipt.v1", text)
        self.assertIn("Saved", text)
        self.assertIn("PlatformStabilityReview", text)
        self.assertIn("PLATFORM_STABILITY_RECEIPT=", text)
        self.assertIn("PLATFORM_STABILITY_DIRTY_TARGET_REVIEW=", text)
        self.assertIn("\"no_raw_key\": True", text)
        self.assertIn("\"no_provider_call\": True", text)
        self.assertIn("\"no_wallet_check\": True", text)
        self.assertIn("\"no_credit_reservation\": True", text)
        self.assertIn("\"no_spend_confirmation\": True", text)
        self.assertIn("\"no_editor_mutation\": True", text)
        self.assertIn("\"no_git_mutation\": True", text)
        self.assertIn("\"paid_provider_smoke_contract_ok\"", text)
        self.assertIn("\"paid_provider_smoke_no_task_submission\"", text)
        self.assertIn("\"paid_provider_smoke_no_download\"", text)
        self.assertIn("\"paid_provider_smoke_no_import\"", text)
        self.assertIn("paid_provider_smoke_contract_static_no_spend", text)
        self.assertIn("\"blueprint_mutation_evidence_receipt_state\"", text)
        self.assertIn("\"blueprint_mutation_pre_read_evidence_recorded\"", text)
        self.assertIn("\"blueprint_mutation_compile_plan_recorded\"", text)
        self.assertIn("\"blueprint_mutation_readback_plan_recorded\"", text)
        self.assertIn("blueprint_mutation_pre_read_compile_readback_gate_state", text)
        self.assertIn("python scripts\\\\write_blueprint_mutation_evidence_review.py", text)
        self.assertIn("\"dirty_target_review_group\"", text)
        self.assertIn("\"dirty_target_review_missing_evidence_preview\"", text)
        self.assertIn("\"dirty_target_review_focused_test_command_preview\"", text)
        self.assertIn("\"no_stage\": True", text)
        self.assertIn("\"no_commit\": True", text)
        self.assertNotIn("confirm_spend=True", text)
        self.assertNotIn("confirm_usage=True", text)
        self.assertNotIn("gen_tripo_create", text)
        self.assertNotIn("gen_uthana_create", text)
        self.assertNotIn("git add", text)
        self.assertNotIn("git commit", text)
        self.assertNotIn("git clean", text)

    def test_bridge_ping_script_writes_receipt_and_remains_read_only(self):
        text = BRIDGE_PING_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("unreal_mcp_bridge_ping_receipt.v1", text)
        self.assertIn("Saved", text)
        self.assertIn("BridgePing", text)
        self.assertIn("BRIDGE_PING_RECEIPT=", text)
        self.assertIn("\"successful_bridge_ping\"", text)
        self.assertIn("\"no_editor_mutation\": True", text)
        self.assertIn("\"no_provider_call\": True", text)
        self.assertIn("\"no_git_mutation\": True", text)
        self.assertIn("\"unreal_editor_required\": True", text)
        self.assertNotIn("confirm_spend=True", text)
        self.assertNotIn("git add", text)
        self.assertNotIn("git commit", text)

    def test_chat_start_script_is_receipt_based_and_non_destructive(self):
        text = CHAT_START_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("Start-Process", text)
        self.assertIn("-WindowStyle Hidden", text)
        self.assertIn("Saved\\ChatCockpit\\last_start_receipt.json", text)
        self.assertIn("unreal_mcp_chat_cockpit_start_receipt.v1", text)
        self.assertIn("CHAT_COCKPIT_RECEIPT=", text)
        self.assertIn("no_port_kill", text)
        self.assertIn("no_editor_mutation", text)
        self.assertIn("no_provider_call", text)
        self.assertIn("no_git_mutation", text)
        self.assertIn('[string]$BindHost = "127.0.0.1"', text)
        self.assertIn("[int]$TimeoutSeconds = 180", text)
        self.assertIn("Stop-Process -Id $Process.Id", text)
        self.assertNotIn("taskkill", text.lower())

    def test_chat_cockpit_start_receipt_parser_reports_missing_ready_and_blocked(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing = module._chat_cockpit_start_receipt_status(tmp_path / "missing.json")
            ready_path = tmp_path / "ready.json"
            failed_path = tmp_path / "failed.json"
            ready_path.write_text(json.dumps({
                "schema": "unreal_mcp_chat_cockpit_start_receipt.v1",
                "status": "already_running",
                "base_url": "http://127.0.0.1:8000",
                "health_url": "http://127.0.0.1:8000/chat/history?limit=1",
                "mcp_endpoint": "http://127.0.0.1:8000/sse",
                "process_started": False,
                "no_port_kill": True,
                "no_editor_mutation": True,
                "no_provider_call": True,
                "no_git_mutation": True,
            }), encoding="utf-8")
            failed_path.write_text(json.dumps({
                "schema": "unreal_mcp_chat_cockpit_start_receipt.v1",
                "status": "failed",
                "failure_mode": "health_timeout",
            }), encoding="utf-8")

            ready = module._chat_cockpit_start_receipt_status(ready_path)
            failed = module._chat_cockpit_start_receipt_status(failed_path)

        self.assertFalse(missing["receipt_exists"])
        self.assertEqual(missing["state"], "missing")
        self.assertEqual(
            missing["required_command"],
            "powershell -ExecutionPolicy Bypass -File scripts\\start_chat_cockpit_server.ps1",
        )
        self.assertEqual(ready["state"], "ready")
        self.assertEqual(ready["status"], "already_running")
        self.assertFalse(ready["process_started"])
        self.assertTrue(ready["no_port_kill"])
        self.assertTrue(ready["no_editor_mutation"])
        self.assertEqual(failed["state"], "blocked")
        self.assertEqual(failed["failure_mode"], "health_timeout")
        self.assertFalse(failed["network_required"])
        self.assertFalse(failed["spend_required"])
        self.assertFalse(failed["unreal_editor_required"])

    def test_provider_config_status_reports_no_leak_repair_contract(self):
        module = _load_preflight_module()

        status = module._provider_config_status()
        repair = status["repair_contract"]
        secret_contract = status["secret_contract"]

        self.assertEqual(repair["schema"], "unreal_mcp_provider_config_repair.v1")
        self.assertEqual(repair["config_tool"], "gen_get_provider_config")
        self.assertEqual(repair["save_tool"], "gen_save_provider_config")
        self.assertIn("TRIPO_API_KEY", repair["tripo_env_var"])
        self.assertIn("UTHANA_API_KEY", repair["uthana_env_var"])
        self.assertIn("<TRIPO_API_KEY>", repair["tripo_store_command_template"])
        self.assertIn("<UTHANA_API_KEY>", repair["uthana_store_command_template"])
        self.assertIn("raw provider keys", repair["no_leak_policy"])
        self.assertFalse(repair["network_required"])
        self.assertFalse(repair["spend_required"])
        self.assertFalse(repair["unreal_editor_required"])
        self.assertFalse(secret_contract["raw_key_returned"])
        self.assertTrue(secret_contract["masked_status_only"])
        self.assertTrue(secret_contract["secrets_gitignored"])
        self.assertTrue(secret_contract["settings_gitignored"])
        self.assertIn(status["review_receipt_state"], {"missing", "ready", "missing_keys", "blocked"})
        self.assertEqual(status["review_receipt_path"], "Saved\\ProviderConfigReview\\last_review_receipt.json")
        self.assertEqual(status["review_receipt_required_command"], "python scripts\\write_provider_config_review.py")
        self.assertEqual(status["operator_command_handoff_count"], 1)
        self.assertEqual(status["operator_command_handoff_ids"], ["write_provider_config_review_receipt"])
        self.assertTrue(status["operator_command_handoff"][0]["no_raw_key"])
        self.assertTrue(status["operator_command_handoff"][0]["no_provider_call"])
        self.assertTrue(status["operator_command_handoff"][0]["no_git_mutation"])

    def test_provider_config_review_receipt_parser_reports_missing_ready_and_missing_keys(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing = module._provider_config_review_receipt_status(tmp_path / "missing.json")
            ready_path = tmp_path / "ready.json"
            missing_keys_path = tmp_path / "missing_keys.json"
            ready_path.write_text(json.dumps({
                "schema": "unreal_mcp_provider_config_review_receipt.v1",
                "status": "ready",
                "api_key_configured": True,
                "api_key_source": "env",
                "uthana_api_key_configured": True,
                "uthana_api_key_source": "secrets",
                "secrets_gitignored": True,
                "settings_gitignored": True,
            }), encoding="utf-8")
            missing_keys_path.write_text(json.dumps({
                "schema": "unreal_mcp_provider_config_review_receipt.v1",
                "status": "missing_keys",
                "api_key_configured": False,
                "api_key_source": "missing",
                "uthana_api_key_configured": False,
                "uthana_api_key_source": "missing",
            }), encoding="utf-8")

            ready = module._provider_config_review_receipt_status(ready_path)
            missing_keys = module._provider_config_review_receipt_status(missing_keys_path)

        self.assertFalse(missing["receipt_exists"])
        self.assertEqual(missing["state"], "missing")
        self.assertEqual(missing["required_command"], "python scripts\\write_provider_config_review.py")
        self.assertEqual(ready["state"], "ready")
        self.assertTrue(ready["api_key_configured"])
        self.assertTrue(ready["uthana_api_key_configured"])
        self.assertEqual(missing_keys["state"], "missing_keys")
        self.assertFalse(missing_keys["api_key_configured"])
        self.assertFalse(missing_keys["uthana_api_key_configured"])
        self.assertFalse(missing_keys["network_required"])
        self.assertFalse(missing_keys["spend_required"])
        self.assertTrue(missing_keys["no_raw_key"])
        self.assertTrue(missing_keys["no_provider_call"])

    def test_provider_config_review_script_is_no_leak_and_no_spend(self):
        text = PROVIDER_REVIEW_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("unreal_mcp_provider_config_review_receipt.v1", text)
        self.assertIn("Saved", text)
        self.assertIn("ProviderConfigReview", text)
        self.assertIn("PROVIDER_CONFIG_RECEIPT=", text)
        self.assertIn("\"no_raw_key\": True", text)
        self.assertIn("\"no_provider_call\": True", text)
        self.assertIn("\"no_wallet_check\": True", text)
        self.assertIn("\"no_credit_reservation\": True", text)
        self.assertIn("\"no_spend_confirmation\": True", text)
        self.assertNotIn("TRIPO_API_KEY\"]", text)
        self.assertNotIn("UTHANA_API_KEY\"]", text)

    def test_paid_generation_evidence_review_receipt_parser_reports_missing_ready_and_missing_evidence(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing = module._paid_generation_evidence_review_receipt_status(tmp_path / "missing.json")
            ready_path = tmp_path / "ready.json"
            missing_evidence_path = tmp_path / "missing_evidence.json"
            ready_path.write_text(json.dumps({
                "schema": "unreal_mcp_paid_generation_evidence_review_receipt.v1",
                "status": "ready",
                "mesh_wallet_evidence_recorded": True,
                "animation_allowance_evidence_recorded": True,
                "explicit_spend_approval_recorded": True,
                "explicit_usage_approval_recorded": True,
                "estimated_spend_reviewed": True,
                "estimated_motion_seconds_reviewed": True,
                "mesh_wallet_evidence_summary": "masked balance reviewed",
                "animation_allowance_summary": "masked allowance reviewed",
                "explicit_spend_approval_summary": "developer approved one mesh task",
                "usage_approval_summary": "developer approved one motion task",
            }), encoding="utf-8")
            missing_evidence_path.write_text(json.dumps({
                "schema": "unreal_mcp_paid_generation_evidence_review_receipt.v1",
                "status": "missing_evidence",
                "wallet_evidence_recorded": False,
                "spend_confirmation_recorded": False,
            }), encoding="utf-8")

            ready = module._paid_generation_evidence_review_receipt_status(ready_path)
            missing_evidence = module._paid_generation_evidence_review_receipt_status(missing_evidence_path)

        self.assertFalse(missing["receipt_exists"])
        self.assertEqual(missing["state"], "missing")
        self.assertEqual(missing["required_command"], "python scripts\\write_paid_generation_evidence_review.py")
        self.assertEqual(ready["state"], "ready")
        self.assertTrue(ready["wallet_evidence_recorded"])
        self.assertTrue(ready["mesh_wallet_evidence_recorded"])
        self.assertTrue(ready["animation_allowance_evidence_recorded"])
        self.assertTrue(ready["spend_confirmation_recorded"])
        self.assertTrue(ready["explicit_spend_approval_recorded"])
        self.assertTrue(ready["explicit_usage_approval_recorded"])
        self.assertTrue(ready["estimated_spend_reviewed"])
        self.assertTrue(ready["estimated_motion_seconds_reviewed"])
        self.assertEqual(missing_evidence["state"], "missing_evidence")
        self.assertFalse(missing_evidence["wallet_evidence_recorded"])
        self.assertFalse(missing_evidence["spend_confirmation_recorded"])
        self.assertFalse(missing_evidence["network_required"])
        self.assertFalse(missing_evidence["spend_required"])
        self.assertTrue(missing_evidence["no_provider_call"])
        self.assertTrue(missing_evidence["no_wallet_check"])
        self.assertTrue(missing_evidence["no_task_submission"])

    def test_paid_generation_evidence_writer_merges_provider_specific_handoffs(self):
        module = _load_paid_generation_review_module()

        tripo_only = module.build_receipt(
            reset_evidence=True,
            mesh_wallet_evidence_recorded=True,
            mesh_wallet_evidence_summary="masked Tripo credits reviewed",
        )
        merged = module.build_receipt(
            previous_receipt=tripo_only,
            animation_allowance_evidence_recorded=True,
            animation_allowance_summary="masked Uthana allowance reviewed",
        )
        ready = module.build_receipt(
            previous_receipt=merged,
            spend_confirmation_recorded=True,
            explicit_usage_approval_recorded=True,
            estimated_spend_reviewed=True,
            estimated_motion_seconds_reviewed=True,
            spend_confirmation_summary="developer approved one Tripo mesh task",
            usage_approval_summary="developer approved one Uthana motion task",
        )

        self.assertEqual(tripo_only["status"], "missing_evidence")
        self.assertTrue(tripo_only["mesh_wallet_evidence_recorded"])
        self.assertFalse(tripo_only["animation_allowance_evidence_recorded"])
        self.assertTrue(merged["mesh_wallet_evidence_recorded"])
        self.assertTrue(merged["animation_allowance_evidence_recorded"])
        self.assertTrue(merged["wallet_evidence_recorded"])
        self.assertIn("masked Tripo credits reviewed", merged["wallet_evidence_summary"])
        self.assertIn("masked Uthana allowance reviewed", merged["wallet_evidence_summary"])
        self.assertEqual(merged["merge_policy"], "preserve_existing_evidence_unless_reset")
        self.assertEqual(ready["status"], "ready")
        self.assertTrue(ready["explicit_spend_approval_recorded"])
        self.assertTrue(ready["explicit_usage_approval_recorded"])
        self.assertTrue(ready["estimated_spend_reviewed"])
        self.assertTrue(ready["estimated_motion_seconds_reviewed"])
        with self.assertRaises(ValueError):
            module.build_receipt(
                reset_evidence=True,
                animation_allowance_evidence_recorded=True,
                animation_allowance_summary="a" * 32,
            )

    def test_paid_generation_evidence_review_script_is_no_provider_and_no_spend(self):
        text = PAID_GENERATION_REVIEW_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("unreal_mcp_paid_generation_evidence_review_receipt.v1", text)
        self.assertIn("Saved", text)
        self.assertIn("PaidGenerationEvidence", text)
        self.assertIn("PAID_GENERATION_EVIDENCE_RECEIPT=", text)
        self.assertIn("--mesh-wallet-evidence-recorded", text)
        self.assertIn("--animation-allowance-evidence-recorded", text)
        self.assertIn("--record-masked-tripo-wallet-evidence", text)
        self.assertIn("--record-masked-uthana-allowance-evidence", text)
        self.assertIn("--record-explicit-spend-and-usage-approval", text)
        self.assertIn("--reset-evidence", text)
        self.assertIn("--explicit-usage-approval-recorded", text)
        self.assertIn("ANIMATION_ALLOWANCE_EVIDENCE_RECORDED=", text)
        self.assertIn("\"no_provider_call\": True", text)
        self.assertIn("\"no_wallet_check\": True", text)
        self.assertIn("\"no_credit_reservation\": True", text)
        self.assertIn("\"no_task_submission\": True", text)
        self.assertIn("\"no_editor_mutation\": True", text)
        self.assertNotIn("gen_tripo_get_credit_balance(", text)
        self.assertNotIn("gen_uthana_get_account(", text)

    def test_blueprint_mutation_evidence_review_receipt_parser_reports_missing_ready_and_missing_evidence(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing = module._blueprint_mutation_evidence_review_receipt_status(tmp_path / "missing.json")
            ready_path = tmp_path / "ready.json"
            missing_evidence_path = tmp_path / "missing_evidence.json"
            ready_path.write_text(json.dumps({
                "schema": "unreal_mcp_blueprint_mutation_evidence_review_receipt.v1",
                "status": "ready",
                "pre_read_evidence_recorded": True,
                "compile_plan_recorded": True,
                "readback_plan_recorded": True,
                "target_blueprint_path": "/Game/Test/BP_Test",
                "intended_mutation_summary": "add interaction event",
                "pre_read_summary": "existing graph inspected",
                "compile_plan_summary": "compile target Blueprint after mutation",
                "readback_plan_summary": "read back event node after compile",
            }), encoding="utf-8")
            missing_evidence_path.write_text(json.dumps({
                "schema": "unreal_mcp_blueprint_mutation_evidence_review_receipt.v1",
                "status": "missing_evidence",
                "pre_read_evidence_recorded": True,
                "compile_plan_recorded": False,
                "readback_plan_recorded": False,
            }), encoding="utf-8")

            ready = module._blueprint_mutation_evidence_review_receipt_status(ready_path)
            missing_evidence = module._blueprint_mutation_evidence_review_receipt_status(missing_evidence_path)

        self.assertFalse(missing["receipt_exists"])
        self.assertEqual(missing["state"], "missing")
        self.assertEqual(missing["required_command"], "python scripts\\write_blueprint_mutation_evidence_review.py")
        self.assertEqual(len(missing["operator_command_handoff"]), 3)
        self.assertEqual(missing["operator_command_handoff"][0]["id"], "record_blueprint_pre_read_evidence")
        self.assertEqual(missing["operator_command_handoff"][1]["id"], "record_blueprint_compile_plan")
        self.assertEqual(missing["operator_command_handoff"][2]["id"], "record_blueprint_readback_plan")
        self.assertTrue(missing["operator_command_handoff"][0]["records_evidence_only"])
        self.assertTrue(missing["operator_command_handoff"][0]["no_blueprint_mutation"])
        self.assertEqual(ready["state"], "ready")
        self.assertTrue(ready["pre_read_evidence_recorded"])
        self.assertTrue(ready["compile_plan_recorded"])
        self.assertTrue(ready["readback_plan_recorded"])
        self.assertEqual(ready["target_blueprint_path"], "/Game/Test/BP_Test")
        self.assertEqual(missing_evidence["state"], "missing_evidence")
        self.assertTrue(missing_evidence["pre_read_evidence_recorded"])
        self.assertFalse(missing_evidence["compile_plan_recorded"])
        self.assertFalse(missing_evidence["readback_plan_recorded"])
        self.assertFalse(missing_evidence["network_required"])
        self.assertFalse(missing_evidence["spend_required"])
        self.assertFalse(missing_evidence["unreal_editor_required"])
        self.assertTrue(missing_evidence["no_editor_mutation"])
        self.assertTrue(missing_evidence["no_blueprint_mutation"])
        self.assertTrue(missing_evidence["no_compile"])
        self.assertTrue(missing_evidence["no_save"])
        self.assertTrue(missing_evidence["no_pie"])

    def test_blueprint_mutation_evidence_writer_merges_passive_evidence_steps(self):
        module = _load_blueprint_mutation_review_module()

        pre_read = module.build_receipt(
            reset_evidence=True,
            pre_read_evidence_recorded=True,
            target_blueprint_path="/Game/Test/BP_Test",
            intended_mutation_summary="add interaction event",
            pre_read_summary="existing graph inspected",
        )
        compile_plan = module.build_receipt(
            previous_receipt=pre_read,
            compile_plan_recorded=True,
            compile_plan_summary="compile target Blueprint after mutation",
        )
        ready = module.build_receipt(
            previous_receipt=compile_plan,
            readback_plan_recorded=True,
            readback_plan_summary="read back event node after compile",
        )

        self.assertEqual(pre_read["status"], "missing_evidence")
        self.assertTrue(pre_read["pre_read_evidence_recorded"])
        self.assertFalse(pre_read["compile_plan_recorded"])
        self.assertTrue(compile_plan["pre_read_evidence_recorded"])
        self.assertTrue(compile_plan["compile_plan_recorded"])
        self.assertEqual(compile_plan["target_blueprint_path"], "/Game/Test/BP_Test")
        self.assertEqual(compile_plan["merge_policy"], "preserve_existing_evidence_unless_reset")
        self.assertEqual(ready["status"], "ready")
        self.assertTrue(ready["pre_read_evidence_recorded"])
        self.assertTrue(ready["compile_plan_recorded"])
        self.assertTrue(ready["readback_plan_recorded"])
        self.assertTrue(ready["human_approval_required_before_blueprint_mutation"])
        self.assertTrue(ready["no_editor_mutation"])
        self.assertTrue(ready["no_blueprint_mutation"])
        self.assertTrue(ready["no_compile"])
        self.assertTrue(ready["no_save"])
        self.assertTrue(ready["no_pie"])
        self.assertTrue(ready["no_provider_call"])
        self.assertEqual(len(ready["operator_command_handoff"]), 3)
        self.assertIn("--pre-read-evidence-recorded", ready["operator_command_handoff"][0]["command"])
        self.assertIn("--compile-plan-recorded", ready["operator_command_handoff"][1]["command"])
        self.assertIn("--readback-plan-recorded", ready["operator_command_handoff"][2]["command"])
        with self.assertRaises(ValueError):
            module.build_receipt(
                reset_evidence=True,
                pre_read_evidence_recorded=True,
                pre_read_summary="tsk_" + ("A" * 25),
            )

    def test_blueprint_mutation_evidence_review_script_is_no_editor_mutation(self):
        text = BLUEPRINT_MUTATION_REVIEW_SCRIPT_PATH.read_text(encoding="utf-8")

        self.assertIn("unreal_mcp_blueprint_mutation_evidence_review_receipt.v1", text)
        self.assertIn("Saved", text)
        self.assertIn("BlueprintMutationEvidence", text)
        self.assertIn("BLUEPRINT_MUTATION_EVIDENCE_RECEIPT=", text)
        self.assertIn("--pre-read-evidence-recorded", text)
        self.assertIn("--compile-plan-recorded", text)
        self.assertIn("--readback-plan-recorded", text)
        self.assertIn("record_blueprint_pre_read_evidence", text)
        self.assertIn("record_blueprint_compile_plan", text)
        self.assertIn("record_blueprint_readback_plan", text)
        self.assertIn("--reset-evidence", text)
        self.assertIn("BLUEPRINT_PRE_READ_EVIDENCE_RECORDED=", text)
        self.assertIn("\"no_bridge_ping\": True", text)
        self.assertIn("\"no_editor_mutation\": True", text)
        self.assertIn("\"no_blueprint_mutation\": True", text)
        self.assertIn("\"no_compile\": True", text)
        self.assertIn("\"no_save\": True", text)
        self.assertIn("\"no_pie\": True", text)
        self.assertIn("\"no_provider_call\": True", text)
        self.assertNotIn("bridge_ping(", text)
        self.assertNotIn("compile_blueprint(", text)

    def test_automation_log_parser_reports_success_and_failure(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            success_log = Path(tmp) / "success.txt"
            success_log.write_text(
                "Building plugin for target platforms: Win64\n"
                "Visual Studio 2022 compiler version 14.44.35225 is not a preferred version. Please use the latest preferred version 14.38.33130\n"
                "Warning: Visual Studio 2022 compiler is not a preferred version\n"
                "BUILD SUCCESSFUL\n"
                "AutomationTool exiting with ExitCode=0 (Success)\n",
                encoding="utf-8",
            )
            failure_log = Path(tmp) / "failure.txt"
            failure_log.write_text(
                "Building plugin for target platforms: Win64\n"
                "Plugin 'UnrealMCP' depends on plugin 'StructUtils' which was deprecated in 5.5 and will soon be removed. Please update your dependencies.\n"
                "C:\\Engine\\Source\\Runtime\\Json\\Public\\Json.h(10): warning: Monolithic headers should not be used by this module.\n"
                "BUILD FAILED\n"
                "AutomationTool exiting with ExitCode=6\n",
                encoding="utf-8",
            )

            success = module._parse_automation_log(success_log)
            failure = module._parse_automation_log(failure_log)

        self.assertEqual(success["last_plugin_build_status"], "success")
        self.assertEqual(success["last_plugin_build_exit_code"], 0)
        self.assertEqual(success["last_plugin_build_warning_severity"], "toolchain")
        self.assertEqual(success["last_plugin_build_warning_categories"], ["toolchain_preference"])
        self.assertEqual(success["last_plugin_build_warning_count"], 2)
        self.assertEqual(failure["last_plugin_build_status"], "failed")
        self.assertEqual(failure["last_plugin_build_exit_code"], 6)
        self.assertEqual(failure["last_plugin_build_warning_severity"], "repo")
        self.assertIn("deprecated_plugin", failure["last_plugin_build_warning_categories"])
        self.assertIn("monolithic_header", failure["last_plugin_build_warning_categories"])

    def test_plugin_build_receipt_parser_prefers_local_receipt_log(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_path = tmp_path / "last_build.log"
            receipt_path = tmp_path / "last_build_receipt.json"
            log_path.write_text(
                "Building plugin for target platforms: Win64\n"
                "Warning: Visual Studio 2022 compiler is not a preferred version\n"
                "BUILD SUCCESSFUL\n"
                "AutomationTool exiting with ExitCode=0 (Success)\n",
                encoding="utf-8",
            )
            receipt_path.write_text(json.dumps({
                "schema": "unreal_mcp_plugin_build_receipt.v1",
                "generated_at_utc": "2026-06-15T23:59:00Z",
                "plugin_path": "C:/repo/unreal_plugin/UnrealMCP.uplugin",
                "package_dir": "C:/repo/Saved/PluginBuildSmoke/Package",
                "log_path": str(log_path),
                "run_uat": "C:/UE/RunUAT.bat",
                "exit_code": 0,
                "status": "success",
                "target_platforms": ["Win64"],
            }), encoding="utf-8")

            status = module._parse_plugin_build_receipt(receipt_path)

        self.assertIsNotNone(status)
        self.assertEqual(status["last_plugin_build_status"], "success")
        self.assertEqual(status["last_plugin_build_exit_code"], 0)
        self.assertEqual(status["last_plugin_build_receipt_schema"], "unreal_mcp_plugin_build_receipt.v1")
        self.assertEqual(status["last_plugin_build_receipt_generated_at_utc"], "2026-06-15T23:59:00Z")
        self.assertEqual(status["last_plugin_build_warning_severity"], "toolchain")
        self.assertIn("toolchain_preference", status["last_plugin_build_warning_categories"])

    def test_no_mutation_receipt_parser_reports_missing_clean_and_blocked(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing = module._no_mutation_test_status(tmp_path / "missing.json")
            clean_path = tmp_path / "clean.json"
            dirty_path = tmp_path / "dirty.json"
            clean_path.write_text(json.dumps({
                "schema": "unreal_mcp_no_mutation_unittest_receipt.v1",
                "generated_at_utc": "2026-06-16T00:00:00Z",
                "command": ["python", "scripts\\run_no_mutation_unittest.py"],
                "start_directory": "unreal_mcp_server/tests",
                "pattern": "test_*.py",
                "test_exit_code": 0,
                "mutation_count": 0,
                "mutated_paths": [],
                "status": "success",
                "duration_ms": 10,
                "tracked_file_count": 42,
                "snapshot_hash_algorithm": "sha256(path\\0content_sha256_or_missing\\0)",
                "snapshot_digest_match": True,
                "snapshot_scope": "git_tracked_worktree",
            }), encoding="utf-8")
            dirty_path.write_text(json.dumps({
                "schema": "unreal_mcp_no_mutation_unittest_receipt.v1",
                "test_exit_code": 0,
                "mutation_count": 1,
                "mutated_paths": ["unreal_mcp_server/tests/last_tool_count.txt"],
                "status": "failed",
            }), encoding="utf-8")

            clean = module._no_mutation_test_status(clean_path)
            dirty = module._no_mutation_test_status(dirty_path)

        self.assertFalse(missing["ok"])
        self.assertEqual(missing["state"], "missing")
        self.assertTrue(clean["ok"])
        self.assertEqual(clean["state"], "ok")
        self.assertEqual(clean["mutation_count"], 0)
        self.assertEqual(clean["tracked_file_count"], 42)
        self.assertTrue(clean["snapshot_digest_match"])
        self.assertEqual(clean["snapshot_scope"], "git_tracked_worktree")
        self.assertEqual(clean["snapshot_hash_algorithm"], "sha256(path\\0content_sha256_or_missing\\0)")
        self.assertFalse(clean["network_required"])
        self.assertFalse(clean["spend_required"])
        self.assertFalse(clean["unreal_editor_required"])
        self.assertFalse(dirty["ok"])
        self.assertEqual(dirty["state"], "blocked")
        self.assertEqual(dirty["mutation_count"], 1)
        self.assertIn("unreal_mcp_server/tests/last_tool_count.txt", dirty["mutated_paths"])

    def test_build_wrapper_status_validates_project_and_build_tool_paths(self):
        module = _load_preflight_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            project_path = tmp_path / "PlayableSlice.uproject"
            batch_project_path = tmp_path / "HostProject.uproject"
            plugin_path = tmp_path / "UnrealMCP.uplugin"
            build_bat = tmp_path / "Build.bat"
            run_uat = tmp_path / "RunUAT.bat"
            project_path.write_text("{}", encoding="utf-8")
            batch_project_path.write_text("{}", encoding="utf-8")
            plugin_path.write_text("{}", encoding="utf-8")
            build_bat.write_text("@echo off\n", encoding="utf-8")
            run_uat.write_text("@echo off\n", encoding="utf-8")
            ready_wrapper = tmp_path / "ready.ps1"
            ready_wrapper.write_text(
                f'$ProjectPath = "{project_path}"\n'
                f'$BuildBat = "{build_bat}"\n'
                '& $BuildBat SliceEditor Win64 Development "-Project=$ProjectPath" -WaitMutex\n',
                encoding="utf-8",
            )
            ready_batch_wrapper = tmp_path / "ready.bat"
            ready_batch_wrapper.write_text(
                '@echo off\n'
                'set "PLUGIN_PATH=%~dp0UnrealMCP.uplugin"\n'
                f'set "RUN_UAT={run_uat}"\n'
                '"%RUN_UAT%" BuildPlugin -Plugin="%PLUGIN_PATH%" -Package="%~dp0Package" -TargetPlatforms=Win64\n',
                encoding="utf-8",
            )
            missing_wrapper = tmp_path / "missing.bat"
            missing_wrapper.write_text(
                f'"{build_bat}" MissingEditor Win64 Development -Project="{tmp_path / "Missing.uproject"}" -WaitMutex\n',
                encoding="utf-8",
            )

            ready = module._build_wrapper_status(paths=[ready_wrapper])
            ready_batch = module._build_wrapper_status(paths=[ready_batch_wrapper])
            missing = module._build_wrapper_status(paths=[missing_wrapper])

        self.assertEqual(ready["status"], "ready")
        self.assertTrue(ready["project_ready"])
        self.assertTrue(ready["tool_ready"])
        self.assertEqual(ready["missing_reference_count"], 0)
        self.assertEqual(ready_batch["status"], "ready")
        self.assertTrue(ready_batch["project_ready"])
        self.assertTrue(ready_batch["plugin_ready"])
        self.assertTrue(ready_batch["tool_ready"])
        self.assertEqual(ready_batch["plugin_paths"], [str(plugin_path.resolve())])
        self.assertEqual(missing["status"], "missing_reference")
        self.assertFalse(missing["project_ready"])
        self.assertTrue(missing["plugin_ready"])
        self.assertTrue(missing["tool_ready"])
        self.assertEqual(missing["missing_reference_count"], 1)
        self.assertTrue(missing["missing_references"][0].endswith("Missing.uproject"))

    def test_cli_json_output(self):
        before = COUNT_PATH.read_text(encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--json",
                "--bridge-port",
                "9",
                "--chat-url",
                "http://127.0.0.1:9",
                "--timeout",
                "0.1",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=45,
            check=False,
        )
        after = COUNT_PATH.read_text(encoding="utf-8")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(before, after)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["schema"], "unreal_mcp_ide_companion_preflight.v1")
        self.assertIn("runtime", payload)
        self.assertEqual(payload["runtime"]["python_version_info"]["major"], sys.version_info.major)
        self.assertIn("unreal_bridge_reachable", payload["blocking_gates"])
        self.assertIn("chat_server_reachable", payload["blocking_gates"])
        self.assertIn("chat_server_reachable", payload["readiness_policy"]["chat_cockpit"]["missing_gates"])
        self.assertEqual(payload["chat"]["health_endpoint"], "/chat/history?limit=1")
        self.assertIn("scripts\\start_chat_cockpit_server.ps1", payload["chat"]["startup_command"])
        self.assertIn("--transport sse", payload["chat"]["manual_startup_command"])
        self.assertEqual(payload["chat"]["startup_receipt_path"], "Saved\\ChatCockpit\\last_start_receipt.json")
        self.assertIn(payload["chat"]["startup_receipt_state"], {"missing", "ready", "blocked"})
        self.assertEqual(
            payload["chat"]["startup_receipt_required_command"],
            "powershell -ExecutionPolicy Bypass -File scripts\\start_chat_cockpit_server.ps1",
        )
        self.assertIn("tcp_ready", payload["chat"])
        self.assertIn("chat_cockpit_repair_contract", payload)
        self.assertEqual(payload["chat_cockpit_repair_contract"]["schema"], "unreal_mcp_chat_cockpit_repair_contract.v1")
        self.assertEqual(payload["chat_cockpit_repair_contract"]["health_endpoint"], "/chat/history?limit=1")
        self.assertIn("scripts\\start_chat_cockpit_server.ps1", payload["chat_cockpit_repair_contract"]["startup_command"])
        self.assertIn("--transport sse", payload["chat_cockpit_repair_contract"]["manual_startup_command"])
        self.assertEqual(payload["chat_cockpit_repair_contract"]["startup_receipt_path"], "Saved\\ChatCockpit\\last_start_receipt.json")
        self.assertTrue(payload["chat_cockpit_repair_contract"]["no_process_start"])
        self.assertTrue(payload["chat_cockpit_repair_contract"]["no_port_kill"])
        self.assertFalse(payload["chat_cockpit_repair_contract"]["network_required"])
        self.assertEqual(payload["readiness_policy"]["schema"], "unreal_mcp_readiness_policy.v1")
        self.assertIn("wallet_evidence_recorded", payload["blocking_gates"])
        self.assertIn("spend_confirmation_recorded", payload["blocking_gates"])
        self.assertIn("spend_confirmation_recorded", payload["readiness_policy"]["paid_generation"]["missing_gates"])
        self.assertIn("paid_animation_generation", payload["readiness_policy"])
        self.assertIn("ready_for_paid_animation_generation", payload)
        self.assertIn("ready_for_blueprint_mutation", payload)
        self.assertFalse(payload["ready_for_blueprint_mutation"])
        self.assertIn("blueprint_pre_read_evidence", payload["blocking_gates"])
        self.assertIn("blueprint_compile_plan", payload["blocking_gates"])
        self.assertIn("blueprint_readback_plan", payload["blocking_gates"])
        self.assertIn("dirty_promotion_contract", payload)
        self.assertEqual(payload["dirty_promotion_contract"]["schema"], "unreal_mcp_dirty_promotion_contract.v1")
        self.assertTrue(payload["dirty_promotion_contract"]["no_git_mutation"])
        self.assertTrue(payload["dirty_promotion_contract"]["no_stage"])
        self.assertIn("human_review_before_stage_commit_or_merge", payload["dirty_promotion_contract"]["required_evidence"])
        self.assertIn("high_value_wrapper_coverage", payload)
        self.assertTrue(payload["high_value_wrapper_coverage"]["ok"])
        self.assertEqual(payload["high_value_wrapper_coverage"]["failing_capability_count"], 0)
        self.assertEqual(payload["high_value_wrapper_coverage"]["roadmap_priority_count"], 10)
        self.assertEqual(payload["high_value_wrapper_coverage"]["roadmap_priority_covered_count"], 10)
        self.assertEqual(payload["high_value_wrapper_coverage"]["roadmap_priority_missing_count"], 0)
        self.assertIn("high_value_bridge_wrappers_covered", payload["readiness_policy"]["platform_stability"]["required_gates"])
        self.assertIn("high_value_wrapper_coverage_audit", payload["readiness_policy"]["platform_stability"]["evidence_required"])
        self.assertIn("paid_generation_evidence", payload)
        self.assertEqual(payload["paid_generation_evidence"]["schema"], "unreal_mcp_paid_generation_evidence_contract.v1")
        self.assertFalse(payload["paid_generation_evidence"]["network_required_now"])
        self.assertFalse(payload["paid_generation_evidence"]["spend_required_now"])
        self.assertTrue(payload["paid_generation_evidence"]["no_provider_call"])
        self.assertTrue(payload["paid_generation_evidence"]["no_credit_reservation"])
        self.assertIn("gen_uthana_get_account", payload["paid_generation_evidence"]["animation_allowance_tools"])
        self.assertIn("gen_tripo_get_credit_balance(include_raw=False)", " ".join(payload["paid_generation_evidence"]["wallet_evidence_review_steps"]))
        self.assertIn("--mesh-wallet-evidence-recorded", payload["paid_generation_evidence"]["wallet_evidence_receipt_command_template"])
        self.assertIn("--animation-allowance-evidence-recorded", payload["paid_generation_evidence"]["wallet_evidence_receipt_command_template"])
        self.assertIn("--record-masked-tripo-wallet-evidence", payload["paid_generation_evidence"]["mesh_wallet_evidence_receipt_command_template"])
        self.assertIn("--record-masked-uthana-allowance-evidence", payload["paid_generation_evidence"]["animation_allowance_receipt_command_template"])
        self.assertIn("--record-explicit-spend-and-usage-approval", payload["paid_generation_evidence"]["spend_confirmation_receipt_command_template"])
        self.assertEqual(len(payload["paid_generation_evidence"]["operator_command_handoff"]), 3)
        self.assertEqual(payload["paid_generation_evidence"]["operator_command_handoff"][0]["id"], "record_masked_tripo_wallet_evidence")
        self.assertEqual(payload["paid_generation_evidence"]["operator_command_handoff"][1]["id"], "record_masked_uthana_allowance_evidence")
        self.assertEqual(payload["paid_generation_evidence"]["operator_command_handoff"][2]["id"], "record_explicit_spend_and_usage_approval")
        self.assertFalse(payload["paid_generation_evidence"]["operator_command_handoff"][0]["approval_flags_included"])
        self.assertFalse(payload["paid_generation_evidence"]["operator_command_handoff"][1]["approval_flags_included"])
        self.assertTrue(payload["paid_generation_evidence"]["operator_command_handoff"][2]["approval_flags_included"])
        self.assertIn("readiness_repair_queue", payload)
        self.assertEqual(payload["readiness_repair_queue"]["schema"], "unreal_mcp_readiness_repair_queue.v1")
        self.assertTrue(payload["readiness_repair_queue"]["no_auto_execute"])
        self.assertTrue(payload["readiness_repair_queue"]["no_secret_echo"])
        repair_actions = {
            action["gate"]: action
            for action in payload["readiness_repair_queue"]["action_preview"]
            if isinstance(action, dict) and "gate" in action
        }
        self.assertEqual(repair_actions["blueprint_pre_read_evidence"]["policy_area"], "blueprint_mutation")
        self.assertTrue(repair_actions["blueprint_pre_read_evidence"]["no_blueprint_mutation"])
        self.assertIn("blueprint_pre_read", repair_actions["blueprint_pre_read_evidence"]["evidence_required_preview"])
        self.assertEqual(repair_actions["blueprint_compile_plan"]["policy_area"], "blueprint_mutation")
        self.assertTrue(repair_actions["blueprint_compile_plan"]["no_blueprint_mutation"])
        self.assertEqual(repair_actions["blueprint_readback_plan"]["policy_area"], "blueprint_mutation")
        self.assertTrue(repair_actions["blueprint_readback_plan"]["no_blueprint_mutation"])
        if payload["provider_config"]["api_key_configured"]:
            self.assertNotIn("provider_api_key_configured", payload["readiness_repair_queue"]["blocking_gate_preview"])
        else:
            self.assertIn("provider_api_key_configured", payload["readiness_repair_queue"]["blocking_gate_preview"])
        if payload["provider_config"].get("uthana_api_key_configured", False):
            self.assertNotIn("animation_provider_api_key_configured", payload["readiness_repair_queue"]["blocking_gate_preview"])
        else:
            self.assertIn("animation_provider_api_key_configured", payload["readiness_repair_queue"]["blocking_gate_preview"])
        self.assertEqual(payload["readiness_repair_queue"]["next_action"]["gate"], "chat_server_reachable")
        self.assertNotIn("api_key_masked", json.dumps(payload["readiness_repair_queue"]))
        self.assertIn("repair_contract", payload["provider_config"])
        self.assertIn("<UTHANA_API_KEY>", payload["provider_config"]["repair_contract"]["uthana_store_command_template"])
        self.assertIn("platform_stability", payload["readiness_policy"])
        self.assertIn("branch_policy", payload["readiness_policy"])
        self.assertIn("branch", payload["git"])
        self.assertIn("ready_for_platform_stability", payload)
        self.assertIn("wip_promotion", payload["readiness_policy"])
        self.assertIn("ready_for_wip_promotion", payload)
        self.assertIn("dirty_state_grouped_for_promotion", payload["readiness_policy"]["wip_promotion"]["required_gates"])
        self.assertIn("last_plugin_build_status", payload["build"])
        self.assertIn("last_plugin_build_warning_count", payload["build"])
        self.assertIn("last_plugin_build_warning_severity", payload["build"])
        self.assertIn("build_wrapper_status", payload["build"])
        self.assertIn("build_wrapper_missing_references", payload["build"])
        self.assertIn("build_wrapper_plugin_ready", payload["build"])
        self.assertIn("dirty_risk", payload["git"])
        self.assertIn("dirty_group_preview", payload["git"])
        self.assertIn("dirty_grouping_required", payload["git"])

    def test_text_summary_surfaces_local_receipt_states(self):
        module = _load_preflight_module()
        with _temporary_untracked_git_change():
            report = module.build_report(
                bridge_host="127.0.0.1",
                bridge_port=9,
                chat_url="http://127.0.0.1:9",
                timeout_s=0.1,
            )
        dirty_action = next(
            item
            for item in report["readiness_repair_queue"]["action_preview"]
            if item["gate"] == "dirty_state_grouped_for_promotion"
        )
        report["readiness_repair_queue"]["next_action"] = dirty_action
        report["readiness_repair_queue"]["recommended_next"] = dirty_action["action_id"]
        text = module.format_text(report)

        self.assertIn("Bridge ping receipt:", text)
        self.assertIn("Saved\\BridgePing\\last_ping_receipt.json", text)
        self.assertIn("Chat cockpit startup receipt:", text)
        self.assertIn("Saved\\ChatCockpit\\last_start_receipt.json", text)
        self.assertIn("Provider config review receipt:", text)
        self.assertIn("Saved\\ProviderConfigReview\\last_review_receipt.json", text)
        self.assertIn("Paid generation evidence receipt:", text)
        self.assertIn("Saved\\PaidGenerationEvidence\\last_review_receipt.json", text)
        self.assertIn("Dirty promotion review receipt:", text)
        self.assertIn("Saved\\DirtyPromotionReview\\last_review_receipt.json", text)
        self.assertIn("No-mutation test receipt:", text)
        self.assertIn("Saved\\NoMutationTest\\last_run_receipt.json", text)
        self.assertIn("Plugin build receipt:", text)
        self.assertIn("Saved\\PluginBuildSmoke\\last_build_receipt.json", text)
        self.assertIn("Platform stability review receipt:", text)
        self.assertIn("Saved\\PlatformStabilityReview\\last_review_receipt.json", text)
        self.assertIn("Blocking gates:", text)
        self.assertIn("Next repair:", text)
        self.assertIn(report["readiness_repair_queue"]["recommended_next"], text)
        self.assertIn(report["readiness_repair_queue"]["next_action"]["gate"], text)
        self.assertIn("Next repair evidence:", text)
        self.assertIn("unresolved item(s)", text)
        self.assertIn("batch(es)", text)
        target_group = report["readiness_repair_queue"]["next_action"].get("target_review_group")
        if target_group:
            self.assertIn("Next repair target:", text)
            self.assertIn(target_group, text)
            self.assertIn("missing evidence", text)
            self.assertIn("focused tests", text)
            self.assertIn("sample paths", text)
        self.assertIn("Repair priority:", text)
        self.assertIn("chat_health_then_wip_promotion_safety_then_bridge_proof_then_paid_provider_gates", text)

    def test_text_summary_shortens_repo_local_receipt_paths(self):
        module = _load_preflight_module()
        report = module.build_report(
            bridge_host="127.0.0.1",
            bridge_port=9,
            chat_url="http://127.0.0.1:9",
            timeout_s=0.1,
        )
        report["no_mutation_tests"]["receipt_path"] = str(REPO_ROOT / "Saved" / "NoMutationTest" / "last_run_receipt.json")
        report["build"]["local_build_receipt_path"] = str(REPO_ROOT / "Saved" / "PluginBuildSmoke" / "last_build_receipt.json")

        text = module.format_text(report)

        self.assertIn("No-mutation test receipt:", text)
        self.assertIn("(Saved\\NoMutationTest\\last_run_receipt.json)", text)
        self.assertIn("Plugin build receipt:", text)
        self.assertIn("(Saved\\PluginBuildSmoke\\last_build_receipt.json)", text)
        self.assertNotIn(str(REPO_ROOT / "Saved" / "NoMutationTest" / "last_run_receipt.json"), text)
        self.assertNotIn(str(REPO_ROOT / "Saved" / "PluginBuildSmoke" / "last_build_receipt.json"), text)


if __name__ == "__main__":
    unittest.main()
