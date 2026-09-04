"""Write an ignored platform-stability review receipt.

The receipt snapshots local readiness evidence for promotion/build-health review
without calling providers, mutating Unreal Editor, or touching Git state.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_ide_companion_readiness.py"
DEFAULT_RECEIPT_PATH = Path("Saved") / "PlatformStabilityReview" / "last_review_receipt.json"


def _load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_ide_companion_readiness", AUDIT_SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {AUDIT_SCRIPT_PATH}")
    spec.loader.exec_module(module)
    return module


def _string_list(value: Any, limit: int) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value[:limit]]


def build_receipt(timeout_s: float = 0.5) -> Dict[str, Any]:
    audit = _load_audit_module()
    report = audit.build_report(timeout_s=timeout_s)
    readiness_policy = report.get("readiness_policy") if isinstance(report.get("readiness_policy"), dict) else {}
    platform = readiness_policy.get("platform_stability") if isinstance(readiness_policy.get("platform_stability"), dict) else {}
    promotion = readiness_policy.get("wip_promotion") if isinstance(readiness_policy.get("wip_promotion"), dict) else {}
    provider = report.get("provider_config") if isinstance(report.get("provider_config"), dict) else {}
    dirty = report.get("dirty_promotion_contract") if isinstance(report.get("dirty_promotion_contract"), dict) else {}
    bridge = report.get("bridge") if isinstance(report.get("bridge"), dict) else {}
    chat = report.get("chat") if isinstance(report.get("chat"), dict) else {}
    build = report.get("build") if isinstance(report.get("build"), dict) else {}
    test_lanes = report.get("test_lanes") if isinstance(report.get("test_lanes"), dict) else {}
    no_mutation = report.get("no_mutation_tests") if isinstance(report.get("no_mutation_tests"), dict) else {}
    wrappers = report.get("high_value_wrapper_coverage") if isinstance(report.get("high_value_wrapper_coverage"), dict) else {}
    paid_evidence = report.get("paid_generation_evidence") if isinstance(report.get("paid_generation_evidence"), dict) else {}
    blueprint_evidence = report.get("blueprint_mutation_evidence") if isinstance(report.get("blueprint_mutation_evidence"), dict) else {}
    tool_inventory = report.get("tool_inventory") if isinstance(report.get("tool_inventory"), dict) else {}
    repair_queue = report.get("readiness_repair_queue") if isinstance(report.get("readiness_repair_queue"), dict) else {}
    next_repair = repair_queue.get("next_action") if isinstance(repair_queue.get("next_action"), dict) else {}
    repair_action_preview = repair_queue.get("action_preview") if isinstance(repair_queue.get("action_preview"), list) else []
    platform_missing = _string_list(platform.get("missing_gates", []), 12)
    promotion_missing = _string_list(promotion.get("missing_gates", []), 12)
    ready_for_platform = bool(report.get("ready_for_platform_stability", False))
    review_batches = dirty.get("review_batches") if isinstance(dirty.get("review_batches"), list) else []
    evidence_matrix = dirty.get("evidence_review_matrix") if isinstance(dirty.get("evidence_review_matrix"), list) else []
    target_review_batch = next((item for item in review_batches if isinstance(item, dict)), {})
    target_review_gap = next((item for item in evidence_matrix if isinstance(item, dict)), {})
    target_missing_evidence = (
        target_review_gap.get("missing_evidence")
        if isinstance(target_review_gap.get("missing_evidence"), list)
        else []
    )

    return {
        "schema": "unreal_mcp_platform_stability_review_receipt.v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "ready" if ready_for_platform else "review_required",
        "ready_for_platform_stability": ready_for_platform,
        "ready_for_wip_promotion": bool(report.get("ready_for_wip_promotion", False)),
        "tool_registry_reproducible": bool(tool_inventory.get("matches_recorded_count", False)) and not bool(tool_inventory.get("missing_category_modules", [])),
        "tool_count": int(tool_inventory.get("tool_count", 0) or 0),
        "recorded_count": int(tool_inventory.get("recorded_count", 0) or 0),
        "recorded_tool_count": int(tool_inventory.get("recorded_count", 0) or 0),
        "partial_tool_count": int(tool_inventory.get("partial_tools", 0) or 0),
        "test_lane_ok": bool(test_lanes.get("ok", False)),
        "test_lane_violation_count": int(test_lanes.get("violation_count", 0) or 0),
        "paid_provider_smoke_contract_ok": bool(test_lanes.get("paid_provider_contract_ok", False)),
        "paid_provider_smoke_manual_command": str(test_lanes.get("paid_provider_manual_command", "")),
        "paid_provider_smoke_required_env_vars": _string_list(test_lanes.get("paid_provider_required_env_vars", []), 5),
        "paid_provider_smoke_no_spend_tools": _string_list(test_lanes.get("paid_provider_no_spend_tools", []), 5),
        "paid_provider_smoke_forbidden_tokens_present": _string_list(test_lanes.get("paid_provider_forbidden_tokens_present", []), 8),
        "paid_provider_smoke_default_ci_network_required": bool(test_lanes.get("paid_provider_default_ci_network_required", False)),
        "paid_provider_smoke_manual_network_required": bool(test_lanes.get("paid_provider_manual_network_required", False)),
        "paid_provider_smoke_manual_spend_required": bool(test_lanes.get("paid_provider_manual_spend_required", False)),
        "paid_provider_smoke_no_task_submission": bool(test_lanes.get("paid_provider_contract", {}).get("no_task_submission", True)) if isinstance(test_lanes.get("paid_provider_contract"), dict) else True,
        "paid_provider_smoke_no_download": bool(test_lanes.get("paid_provider_contract", {}).get("no_download", True)) if isinstance(test_lanes.get("paid_provider_contract"), dict) else True,
        "paid_provider_smoke_no_import": bool(test_lanes.get("paid_provider_contract", {}).get("no_import", True)) if isinstance(test_lanes.get("paid_provider_contract"), dict) else True,
        "paid_generation_evidence_receipt_state": str(paid_evidence.get("review_receipt_state", "missing")),
        "paid_generation_evidence_receipt_path": str(paid_evidence.get("review_receipt_path", "Saved\\PaidGenerationEvidence\\last_review_receipt.json")),
        "paid_generation_evidence_required_command": str(paid_evidence.get("review_receipt_required_command", "python scripts\\write_paid_generation_evidence_review.py")),
        "paid_generation_wallet_evidence_recorded": bool(paid_evidence.get("wallet_evidence_recorded", False)),
        "paid_generation_mesh_wallet_evidence_recorded": bool(paid_evidence.get("mesh_wallet_evidence_recorded", False)),
        "paid_generation_animation_allowance_evidence_recorded": bool(paid_evidence.get("animation_allowance_evidence_recorded", False)),
        "paid_generation_spend_confirmation_recorded": bool(paid_evidence.get("spend_confirmation_recorded", False)),
        "paid_generation_explicit_spend_approval_recorded": bool(paid_evidence.get("explicit_spend_approval_recorded", False)),
        "paid_generation_explicit_usage_approval_recorded": bool(paid_evidence.get("explicit_usage_approval_recorded", False)),
        "paid_generation_estimated_spend_reviewed": bool(paid_evidence.get("estimated_spend_reviewed", False)),
        "paid_generation_estimated_motion_seconds_reviewed": bool(paid_evidence.get("estimated_motion_seconds_reviewed", False)),
        "paid_generation_mesh_provider": str(paid_evidence.get("mesh_provider", "tripo")),
        "paid_generation_animation_provider": str(paid_evidence.get("animation_provider", "uthana")),
        "paid_generation_operator_command_handoff": (
            list(paid_evidence.get("operator_command_handoff", []))[:3]
            if isinstance(paid_evidence.get("operator_command_handoff"), list)
            else []
        ),
        "blueprint_mutation_evidence_receipt_state": str(blueprint_evidence.get("state", "missing")),
        "blueprint_mutation_evidence_receipt_status": str(blueprint_evidence.get("status", "missing")),
        "blueprint_mutation_evidence_receipt_path": str(blueprint_evidence.get("path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")),
        "blueprint_mutation_evidence_required_command": str(blueprint_evidence.get("required_command", "python scripts\\write_blueprint_mutation_evidence_review.py")),
        "blueprint_mutation_operator_command_handoff": (
            list(blueprint_evidence.get("operator_command_handoff", []))[:3]
            if isinstance(blueprint_evidence.get("operator_command_handoff"), list)
            else []
        ),
        "blueprint_mutation_pre_read_evidence_recorded": bool(blueprint_evidence.get("pre_read_evidence_recorded", False)),
        "blueprint_mutation_compile_plan_recorded": bool(blueprint_evidence.get("compile_plan_recorded", False)),
        "blueprint_mutation_readback_plan_recorded": bool(blueprint_evidence.get("readback_plan_recorded", False)),
        "blueprint_mutation_target_blueprint_path": str(blueprint_evidence.get("target_blueprint_path", "")),
        "blueprint_mutation_intended_summary": str(blueprint_evidence.get("intended_mutation_summary", "")),
        "blueprint_mutation_pre_read_summary": str(blueprint_evidence.get("pre_read_summary", "")),
        "blueprint_mutation_compile_plan_summary": str(blueprint_evidence.get("compile_plan_summary", "")),
        "blueprint_mutation_readback_plan_summary": str(blueprint_evidence.get("readback_plan_summary", "")),
        "blueprint_mutation_evidence_required_preview": _string_list(blueprint_evidence.get("required_evidence", []), 8),
        "blueprint_mutation_evidence_merge_policy": str(blueprint_evidence.get("merge_policy", "preserve_existing_evidence_unless_reset")),
        "blueprint_mutation_evidence_reset": bool(blueprint_evidence.get("reset_evidence", False)),
        "blueprint_mutation_human_approval_required": bool(blueprint_evidence.get("human_approval_required_before_blueprint_mutation", True)),
        "blueprint_mutation_evidence_no_bridge_ping": bool(blueprint_evidence.get("no_bridge_ping", True)),
        "blueprint_mutation_evidence_no_editor_mutation": bool(blueprint_evidence.get("no_editor_mutation", True)),
        "blueprint_mutation_evidence_no_blueprint_mutation": bool(blueprint_evidence.get("no_blueprint_mutation", True)),
        "blueprint_mutation_evidence_no_compile": bool(blueprint_evidence.get("no_compile", True)),
        "blueprint_mutation_evidence_no_save": bool(blueprint_evidence.get("no_save", True)),
        "blueprint_mutation_evidence_no_pie": bool(blueprint_evidence.get("no_pie", True)),
        "no_mutation_test_ok": bool(no_mutation.get("ok", False)),
        "no_mutation_test_status": str(no_mutation.get("status", "missing")),
        "no_mutation_test_mutation_count": no_mutation.get("mutation_count"),
        "no_mutation_test_operator_command_handoff": (
            list(no_mutation.get("operator_command_handoff", []))[:1]
            if isinstance(no_mutation.get("operator_command_handoff"), list)
            else []
        ),
        "no_mutation_test_operator_command_handoff_ids": _string_list(no_mutation.get("operator_command_handoff_ids", []), 1),
        "no_mutation_test_operator_command_handoff_count": int(no_mutation.get("operator_command_handoff_count", 0) or 0),
        "high_value_wrappers_covered": bool(wrappers.get("ok", False)) and int(wrappers.get("failing_capability_count", 0) or 0) == 0,
        "high_value_wrapper_capability_count": int(wrappers.get("capability_count", 0) or 0),
        "high_value_wrapper_failing_capability_count": int(wrappers.get("failing_capability_count", 0) or 0),
        "high_value_wrapper_operator_command_handoff": (
            list(wrappers.get("operator_command_handoff", []))[:3]
            if isinstance(wrappers.get("operator_command_handoff"), list)
            else []
        ),
        "high_value_wrapper_operator_command_handoff_ids": _string_list(wrappers.get("operator_command_handoff_ids", []), 3),
        "high_value_wrapper_operator_command_handoff_count": int(wrappers.get("operator_command_handoff_count", 0) or 0),
        "build_wrapper_status": str(build.get("build_wrapper_status", "unknown")),
        "build_health": str(build.get("build_health", "unknown")),
        "last_plugin_build_status": str(build.get("last_plugin_build_status", "unknown")),
        "chat_ready": bool(chat.get("ready", False)),
        "bridge_ping_receipt_state": str(bridge.get("bridge_ping_receipt_state", "missing")),
        "successful_bridge_ping": bool(bridge.get("successful_bridge_ping", False)),
        "bridge_ping_operator_command_handoff": (
            list(bridge.get("bridge_ping_operator_command_handoff", []))[:1]
            if isinstance(bridge.get("bridge_ping_operator_command_handoff"), list)
            else []
        ),
        "bridge_ping_operator_command_handoff_ids": _string_list(bridge.get("bridge_ping_operator_command_handoff_ids", []), 1),
        "bridge_ping_operator_command_handoff_count": int(bridge.get("bridge_ping_operator_command_handoff_count", 0) or 0),
        "provider_config_review_receipt_state": str(provider.get("review_receipt_state", "missing")),
        "provider_config_operator_command_handoff": (
            list(provider.get("operator_command_handoff", []))[:1]
            if isinstance(provider.get("operator_command_handoff"), list)
            else []
        ),
        "provider_config_operator_command_handoff_ids": _string_list(provider.get("operator_command_handoff_ids", []), 1),
        "provider_config_operator_command_handoff_count": int(provider.get("operator_command_handoff_count", 0) or 0),
        "dirty_promotion_review_receipt_state": str(dirty.get("review_receipt_state", "missing")),
        "dirty_promotion_review_receipt_current": bool(dirty.get("review_receipt_current", False)),
        "dirty_promotion_review_receipt_stale": bool(dirty.get("review_receipt_stale", False)),
        "dirty_promotion_review_receipt_signature_match": bool(dirty.get("review_receipt_dirty_signature_match", False)),
        "dirty_signature_algorithm": str(dirty.get("dirty_signature_algorithm", "")),
        "dirty_signature_entry_count": int(dirty.get("dirty_signature_entry_count", 0) or 0),
        "dirty_promotion_review_batch_count": int(dirty.get("review_batch_count", 0) or 0),
        "dirty_promotion_evidence_unresolved_count": int(dirty.get("evidence_unresolved_count", 0) or 0),
        "dirty_target_review_group": str(dirty.get("target_review_group") or target_review_batch.get("group") or target_review_gap.get("group") or ""),
        "dirty_target_review_order": int(dirty.get("target_review_order", target_review_batch.get("order", target_review_gap.get("order", 0))) or 0),
        "dirty_target_review_scope": str(dirty.get("target_review_scope") or target_review_batch.get("candidate_batch_scope") or target_review_gap.get("candidate_batch_scope") or ""),
        "dirty_target_review_tracked_count": int(dirty.get("target_review_tracked_count", target_review_batch.get("tracked_count", target_review_gap.get("tracked_count", 0))) or 0),
        "dirty_target_review_untracked_count": int(dirty.get("target_review_untracked_count", target_review_batch.get("untracked_count", target_review_gap.get("untracked_count", 0))) or 0),
        "dirty_target_review_status": str(dirty.get("target_review_status", "")),
        "dirty_target_review_evidence_complete": bool(dirty.get("target_review_evidence_complete", False)),
        "dirty_target_review_recorded_evidence_count": int(dirty.get("target_review_recorded_evidence_count", 0) or 0),
        "dirty_target_review_recorded_evidence_preview": _string_list(dirty.get("target_review_recorded_evidence_preview", []), 8),
        "dirty_target_review_human_approval_recorded": bool(dirty.get("target_review_human_approval_recorded", False)),
        "dirty_target_review_missing_evidence_count": int(
            dirty.get("target_review_missing_evidence_count", target_review_gap.get("missing_evidence_count", len(target_missing_evidence))) or 0
        ),
        "dirty_target_review_missing_evidence_preview": _string_list(dirty.get("target_review_missing_evidence_preview", target_missing_evidence), 8),
        "dirty_target_review_required_evidence_preview": _string_list(dirty.get("target_review_required_evidence_preview", target_review_gap.get("required_evidence", [])), 8),
        "dirty_target_review_decision_prompt_preview": _string_list(dirty.get("target_review_decision_prompt_preview", target_review_batch.get("decision_prompts", [])), 8),
        "dirty_target_review_receipt_command_template": str(dirty.get("target_review_receipt_command_template", "")),
        "dirty_target_review_approval_receipt_command_template": str(dirty.get("target_review_approval_receipt_command_template", "")),
        "dirty_target_review_receipt_command_policy": str(dirty.get("target_review_receipt_command_policy", "")),
        "dirty_target_review_operator_command_handoff": (
            list(dirty.get("target_review_operator_command_handoff", []))[:2]
            if isinstance(dirty.get("target_review_operator_command_handoff"), list)
            else []
        ),
        "dirty_target_review_pending_human_approval_only": bool(dirty.get("target_review_pending_human_approval_only", False)),
        "dirty_target_review_human_approval_gate": str(dirty.get("target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
        "dirty_target_review_human_approval_command_handoff": (
            list(dirty.get("target_review_human_approval_command_handoff", []))[:1]
            if isinstance(dirty.get("target_review_human_approval_command_handoff"), list)
            else []
        ),
        "dirty_target_review_focused_test_command_handoff": (
            list(dirty.get("target_review_focused_test_command_handoff", []))[:5]
            if isinstance(dirty.get("target_review_focused_test_command_handoff"), list)
            else []
        ),
        "dirty_target_review_focused_test_command_count": int(target_review_batch.get("focused_test_command_count", 0) or 0),
        "dirty_target_review_focused_test_command_preview": (
            _string_list(target_review_batch.get("focused_test_commands", []), 5)
            if isinstance(target_review_batch.get("focused_test_commands"), list)
            else []
        ),
        "dirty_target_review_sample_preview": (
            _string_list(target_review_batch.get("sample", []), 5)
            if isinstance(target_review_batch.get("sample"), list)
            else []
        ),
        "dirty_target_review_promotion_allowed_after_receipt": bool(dirty.get("target_review_promotion_allowed_after_receipt", False)),
        "dirty_target_review_merge_policy": str(dirty.get("target_review_merge_policy", "preserve_existing_evidence_when_dirty_signature_and_target_match")),
        "dirty_target_review_previous_evidence_merged": bool(dirty.get("target_review_previous_evidence_merged", False)),
        "dirty_target_review_reset_evidence": bool(dirty.get("target_review_reset_evidence", False)),
        "platform_missing_gate_count": len(platform_missing),
        "platform_missing_gate_preview": platform_missing,
        "wip_promotion_missing_gate_count": len(promotion_missing),
        "wip_promotion_missing_gate_preview": promotion_missing,
        "blocking_gate_count": len(report.get("blocking_gates", [])) if isinstance(report.get("blocking_gates"), list) else 0,
        "blocking_gate_preview": _string_list(report.get("blocking_gates", []), 12),
        "readiness_repair_action_count": int(repair_queue.get("action_count", 0) or 0),
        "readiness_repair_recommended_next": str(repair_queue.get("recommended_next", "none")),
        "readiness_repair_next_gate": str(next_repair.get("gate", "")),
        "readiness_repair_next_policy_area": str(next_repair.get("policy_area", "")),
        "readiness_repair_next_tool": str(next_repair.get("recommended_tool", "")),
        "readiness_repair_next_requires_bridge": bool(next_repair.get("requires_bridge", False)),
        "readiness_repair_next_requires_network": bool(next_repair.get("requires_network", False)),
        "readiness_repair_next_requires_spend": bool(next_repair.get("requires_spend", False)),
        "readiness_repair_action_preview": [
            {
                "gate": str(item.get("gate", "")),
                "action_id": str(item.get("action_id", "")),
                "policy_area": str(item.get("policy_area", "")),
                "recommended_tool": str(item.get("recommended_tool", "")),
            }
            for item in repair_action_preview[:8]
            if isinstance(item, dict)
        ],
        "required_evidence": [
            "tool_count_matches_baseline",
            "git_branch_policy_evidence",
            "build_wrapper_project_and_tool_paths_resolve",
            "offline_live_paid_test_lane_audit",
            "paid_provider_smoke_contract_static_no_spend",
            "paid_generation_evidence_receipt_state",
            "paid_generation_tripo_wallet_and_uthana_allowance_gate_state",
            "blueprint_mutation_evidence_receipt_state",
            "blueprint_mutation_pre_read_compile_readback_gate_state",
            "last_no_mutation_unittest_receipt",
            "high_value_wrapper_coverage_audit",
            "provider_config_review_receipt_if_paid_generation_is_planned",
            "dirty_promotion_review_receipt_before_wip_promotion",
            "dirty_promotion_review_receipt_current_for_worktree",
        ],
        "followup_commands": [
            "python scripts\\audit_ide_companion_readiness.py",
            "python scripts\\run_no_mutation_unittest.py",
            "python scripts\\audit_high_value_wrapper_coverage.py",
            "python scripts\\write_provider_config_review.py",
            "python scripts\\write_blueprint_mutation_evidence_review.py",
            "python scripts\\write_dirty_promotion_review.py",
        ],
        "no_raw_key": True,
        "no_provider_call": True,
        "no_wallet_check": True,
        "no_credit_reservation": True,
        "no_spend_confirmation": True,
        "no_editor_mutation": True,
        "no_git_mutation": True,
        "no_stage": True,
        "no_commit": True,
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": False,
    }


def write_receipt(path: Path, receipt: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a no-mutation platform-stability review receipt.")
    parser.add_argument("--receipt-path", default=str(DEFAULT_RECEIPT_PATH), help="ignored local JSON receipt path")
    parser.add_argument("--timeout-s", type=float, default=0.5, help="local probe timeout for the underlying readiness audit")
    args = parser.parse_args()

    receipt_path = Path(args.receipt_path)
    if not receipt_path.is_absolute():
        receipt_path = REPO_ROOT / receipt_path
    receipt = build_receipt(timeout_s=args.timeout_s)
    write_receipt(receipt_path, receipt)
    print(f"PLATFORM_STABILITY_RECEIPT={args.receipt_path}")
    print(f"PLATFORM_STABILITY_STATUS={receipt['status']}")
    print(f"READY_FOR_PLATFORM_STABILITY={receipt['ready_for_platform_stability']}")
    print(f"READY_FOR_WIP_PROMOTION={receipt['ready_for_wip_promotion']}")
    print(f"PLATFORM_STABILITY_DIRTY_TARGET_REVIEW={receipt['dirty_target_review_group']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
