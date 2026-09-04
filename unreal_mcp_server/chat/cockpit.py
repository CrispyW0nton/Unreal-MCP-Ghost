"""Read-only helpers for MCP Chat cockpit session and ledger context."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .storage import get_recent_messages, list_sessions

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
DEFAULT_IDE_COMPANION_SESSION_DIR = _REPO_ROOT / ".mcp_artifacts" / "ide_companion_sessions"


def safe_artifact_name(name: str) -> str:
    text = str(name or "ide-companion").strip() or "ide-companion"
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)
    return safe.strip("_") or "ide-companion"


def relative_repo_path(path: Path) -> str:
    try:
        return str(path.relative_to(_REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def classify_artifact(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("kb://"):
        return "knowledge_base"
    if text.startswith("/Game/"):
        return "unreal_asset"
    if "://" in text:
        return "uri"
    if "/" in text or "\\" in text:
        return "path"
    return "note"


def read_ledger_payload(path: Path) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("schema") != "unreal_mcp_ide_companion_ledger.v1":
        return None
    return payload


def bounded_string_preview(value: Any, limit: int = 3) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value[: max(0, int(limit or 0))]]


def editor_operation_preview_rows(rows: Any, limit: int = 3) -> List[str]:
    if not isinstance(rows, list):
        return []
    preview: List[str] = []
    for row in rows[: max(0, int(limit or 0))]:
        if not isinstance(row, dict):
            preview.append(str(row))
            continue
        operation_id = str(row.get("id", "")).strip()
        operation_type = str(row.get("operation_type", "")).strip()
        summary = str(row.get("summary", "")).strip()
        tool_candidates = row.get("tool_candidates") if isinstance(row.get("tool_candidates"), list) else []
        tool_preview = ", ".join(str(tool) for tool in tool_candidates[:2])
        parts = [part for part in (operation_id, operation_type, summary) if part]
        text = " | ".join(parts)
        if tool_preview:
            text = f"{text} -> {tool_preview}" if text else tool_preview
        preview.append(text)
    return preview


def generated_animation_prompt_preview_rows(prompts: Any, asset_list: Any, limit: int = 5) -> List[str]:
    rows: List[str] = []
    if isinstance(prompts, list):
        for prompt in prompts:
            if not isinstance(prompt, dict):
                continue
            name = str(prompt.get("name", "")).strip()
            role = str(prompt.get("role", "")).strip()
            provider = str(prompt.get("provider", "")).strip()
            task_type = str(prompt.get("task_type", "")).strip()
            target_skeleton = str(prompt.get("target_skeleton", "")).strip()
            parts = [part for part in (name, role, provider, task_type, target_skeleton) if part]
            if parts:
                rows.append(" | ".join(parts))
    if not rows and isinstance(asset_list, list):
        for asset in asset_list:
            if not isinstance(asset, dict):
                continue
            if str(asset.get("kind", "")).strip() != "generated_animation_or_placeholder":
                continue
            name = str(asset.get("name", "")).strip()
            role = str(asset.get("role", "")).strip()
            path = str(asset.get("path", "")).strip()
            parts = [part for part in (name, role, path) if part]
            if parts:
                rows.append(" | ".join(parts))
    return rows[: max(0, int(limit or 0))]


def work_order_template_summary(work_order: Dict[str, Any]) -> Dict[str, Any]:
    template = work_order.get("feature_template_work") if isinstance(work_order.get("feature_template_work"), dict) else {}
    if template.get("schema") != "unreal_mcp_gameplay_feature_template.v1":
        return {}

    asset_list = template.get("asset_list") if isinstance(template.get("asset_list"), list) else []
    operations = template.get("graph_component_operations") if isinstance(template.get("graph_component_operations"), list) else []
    editor_operations = template.get("editor_operation_checklist") if isinstance(template.get("editor_operation_checklist"), list) else []
    compile_checks = template.get("compile_readback_checks") if isinstance(template.get("compile_readback_checks"), list) else []
    pie_validation = template.get("pie_validation") if isinstance(template.get("pie_validation"), list) else []
    repair_instructions = template.get("repair_instructions") if isinstance(template.get("repair_instructions"), list) else []
    evidence_requirements = template.get("evidence_requirements") if isinstance(template.get("evidence_requirements"), list) else []
    stop_conditions = template.get("stop_conditions") if isinstance(template.get("stop_conditions"), list) else []
    ownership_split = template.get("ownership_split") if isinstance(template.get("ownership_split"), dict) else {}
    completion_contract = template.get("completion_contract") if isinstance(template.get("completion_contract"), dict) else {}
    runtime_proof_contract = template.get("runtime_proof_contract") if isinstance(template.get("runtime_proof_contract"), dict) else {}
    runtime_proof_required = runtime_proof_contract.get("required_evidence") if isinstance(runtime_proof_contract.get("required_evidence"), list) else []
    runtime_proof_tools = runtime_proof_contract.get("tool_candidates") if isinstance(runtime_proof_contract.get("tool_candidates"), list) else []
    runtime_proof_stop = runtime_proof_contract.get("stop_if_missing") if isinstance(runtime_proof_contract.get("stop_if_missing"), list) else []
    runtime_proof_before = runtime_proof_contract.get("required_before") if isinstance(runtime_proof_contract.get("required_before"), list) else []
    generated_animation_prompts = template.get("generated_animation_prompts") if isinstance(template.get("generated_animation_prompts"), list) else []
    animation_system_hook = template.get("animation_system_hook") if isinstance(template.get("animation_system_hook"), dict) else {}
    generated_animation_assets = [
        asset
        for asset in asset_list
        if isinstance(asset, dict) and str(asset.get("kind", "")).strip() == "generated_animation_or_placeholder"
    ]
    generated_animation_count = len(generated_animation_prompts) or len(generated_animation_assets)
    generated_animation_providers = sorted({
        str(prompt.get("provider", "")).strip()
        for prompt in generated_animation_prompts
        if isinstance(prompt, dict) and str(prompt.get("provider", "")).strip()
    })
    generated_animation_skeletons = sorted({
        str(prompt.get("target_skeleton", "")).strip()
        for prompt in generated_animation_prompts
        if isinstance(prompt, dict) and str(prompt.get("target_skeleton", "")).strip()
    })
    generated_animation_tools = [
        str(tool).strip()
        for tool in (animation_system_hook.get("tools") if isinstance(animation_system_hook.get("tools"), list) else [])
        if str(tool).strip()
    ]
    generated_animation_proof = [
        str(item).strip()
        for item in (animation_system_hook.get("proof_required") if isinstance(animation_system_hook.get("proof_required"), list) else [])
        if str(item).strip()
    ]
    completion_proof_gates = completion_contract.get("proof_gates") if isinstance(completion_contract.get("proof_gates"), list) else []
    completion_required_evidence = completion_contract.get("required_evidence") if isinstance(completion_contract.get("required_evidence"), list) else []
    completion_stop_before_complete = completion_contract.get("stop_before_complete") if isinstance(completion_contract.get("stop_before_complete"), list) else []
    operation_proof_contracts = [
        row.get("operation_proof_contract")
        for row in editor_operations
        if isinstance(row, dict) and isinstance(row.get("operation_proof_contract"), dict)
    ]
    operation_required_after = sorted({
        str(item).strip()
        for contract in operation_proof_contracts
        for item in (contract.get("required_after") if isinstance(contract.get("required_after"), list) else [])
        if str(item).strip()
    })
    operation_types = sorted({
        str(row.get("operation_type", "")).strip()
        for row in editor_operations
        if isinstance(row, dict) and str(row.get("operation_type", "")).strip()
    })
    tool_candidates = sorted({
        str(tool).strip()
        for row in editor_operations
        if isinstance(row, dict)
        for tool in (row.get("tool_candidates") if isinstance(row.get("tool_candidates"), list) else [])
        if str(tool).strip()
    })
    generated_asset_operations = [
        row
        for row in editor_operations
        if isinstance(row, dict) and str(row.get("operation_type", "")).strip() == "generated_asset_replacement"
    ]
    generated_asset_operation_tools = sorted({
        str(tool).strip()
        for row in generated_asset_operations
        for tool in (row.get("tool_candidates") if isinstance(row.get("tool_candidates"), list) else [])
        if str(tool).strip()
    })
    generated_asset_operation_proofs = [
        row.get("operation_proof_contract")
        for row in generated_asset_operations
        if isinstance(row.get("operation_proof_contract"), dict)
    ]
    next_editor_operation = next((row for row in editor_operations if isinstance(row, dict)), {})
    next_operation_proof = (
        next_editor_operation.get("operation_proof_contract")
        if isinstance(next_editor_operation.get("operation_proof_contract"), dict)
        else {}
    )
    next_operation_tools = (
        next_editor_operation.get("tool_candidates")
        if isinstance(next_editor_operation.get("tool_candidates"), list)
        else []
    )
    return {
        "target_phase": str(work_order.get("target_phase", "")),
        "template_name": str(template.get("template_name", "")),
        "display_name": str(template.get("display_name", "")),
        "asset_count": len(asset_list),
        "operation_count": len(operations),
        "editor_operation_count": len(editor_operations),
        "editor_operation_type_preview": operation_types[:6],
        "editor_operation_tool_preview": tool_candidates[:8],
        "editor_operation_preview": editor_operation_preview_rows(editor_operations),
        "next_editor_operation_id": str(next_editor_operation.get("id", "")),
        "next_editor_operation_type": str(next_editor_operation.get("operation_type", "")),
        "next_editor_operation_summary": str(next_editor_operation.get("summary", "")),
        "next_editor_operation_tool_preview": bounded_string_preview(next_operation_tools, 5),
        "next_editor_operation_requires_bridge": bool(next_editor_operation.get("requires_bridge", False)),
        "next_editor_operation_requires_compile_after": bool(next_editor_operation.get("requires_compile_after", False)),
        "next_editor_operation_requires_readback_after": bool(next_editor_operation.get("requires_readback_after", False)),
        "next_editor_operation_required_before_preview": bounded_string_preview(
            next_operation_proof.get("required_before", []),
            5,
        ),
        "next_editor_operation_required_after_preview": bounded_string_preview(
            next_operation_proof.get("required_after", []),
            5,
        ),
        "next_editor_operation_stop_if_missing_preview": bounded_string_preview(
            next_operation_proof.get("stop_if_missing", []),
            5,
        ),
        "generated_asset_replacement_operation_count": len(generated_asset_operations),
        "generated_asset_replacement_operation_preview": editor_operation_preview_rows(generated_asset_operations)[:5],
        "generated_asset_replacement_tool_preview": generated_asset_operation_tools[:8],
        "generated_asset_replacement_proof_contract_count": len(generated_asset_operation_proofs),
        "generated_animation_prompt_count": generated_animation_count,
        "generated_animation_prompt_preview": generated_animation_prompt_preview_rows(generated_animation_prompts, asset_list, 5),
        "generated_animation_provider_preview": generated_animation_providers[:5],
        "generated_animation_target_skeleton_preview": generated_animation_skeletons[:5],
        "generated_animation_tool_preview": generated_animation_tools[:8],
        "generated_animation_proof_required_preview": generated_animation_proof[:8],
        "estimated_uthana_motion_seconds": int(template.get("estimated_uthana_motion_seconds", 0) or 0),
        "operation_proof_contract_count": len(operation_proof_contracts),
        "operation_proof_required_after_preview": operation_required_after[:8],
        "bridge_required_operation_count": sum(1 for row in editor_operations if isinstance(row, dict) and row.get("requires_bridge", False)),
        "compile_after_operation_count": sum(1 for row in editor_operations if isinstance(row, dict) and row.get("requires_compile_after", False)),
        "readback_after_operation_count": sum(1 for row in editor_operations if isinstance(row, dict) and row.get("requires_readback_after", False)),
        "compile_check_count": len(compile_checks),
        "pie_validation_count": len(pie_validation),
        "runtime_proof_contract_schema": str(runtime_proof_contract.get("schema", "")),
        "runtime_proof_mode": str(runtime_proof_contract.get("mode", "")),
        "runtime_proof_required_count": len(runtime_proof_required),
        "runtime_proof_required_before_count": len(runtime_proof_before),
        "runtime_proof_required_before_preview": bounded_string_preview(runtime_proof_before, 8),
        "runtime_proof_tool_preview": bounded_string_preview(runtime_proof_tools, 8),
        "runtime_proof_required_preview": bounded_string_preview(runtime_proof_required, 8),
        "runtime_proof_stop_preview": bounded_string_preview(runtime_proof_stop, 8),
        "repair_instruction_count": len(repair_instructions),
        "evidence_requirement_count": len(evidence_requirements),
        "stop_condition_count": len(stop_conditions),
        "completion_contract_schema": str(completion_contract.get("schema", "")),
        "completion_proof_gate_count": len(completion_proof_gates),
        "completion_required_evidence_count": len(completion_required_evidence),
        "completion_stop_condition_count": len(completion_stop_before_complete),
        "ownership_domains": sorted(str(key) for key in ownership_split.keys())[:8],
        "asset_preview": bounded_string_preview(asset_list),
        "operation_preview": bounded_string_preview(operations),
        "compile_check_preview": bounded_string_preview(compile_checks),
        "pie_validation_preview": bounded_string_preview(pie_validation),
        "repair_preview": bounded_string_preview(repair_instructions),
        "evidence_preview": bounded_string_preview(evidence_requirements),
        "completion_proof_gate_preview": bounded_string_preview(completion_proof_gates, 8),
        "completion_required_evidence_preview": bounded_string_preview(completion_required_evidence, 8),
        "completion_stop_before_complete_preview": bounded_string_preview(completion_stop_before_complete, 8),
    }


def generated_asset_replacement_operation_gate_context(work_order_template: Dict[str, Any]) -> Dict[str, Any]:
    operation_count = int(work_order_template.get("generated_asset_replacement_operation_count", 0) or 0)
    if operation_count <= 0:
        return {
            "generated_asset_replacement_operation_count": 0,
            "generated_asset_replacement_operation_preview": [],
            "generated_asset_replacement_tool_preview": [],
            "generated_asset_replacement_proof_contract_count": 0,
            "generated_asset_replacement_gate_policy": [],
        }
    return {
        "generated_asset_replacement_operation_count": operation_count,
        "generated_asset_replacement_operation_preview": bounded_string_preview(
            work_order_template.get("generated_asset_replacement_operation_preview", []),
            5,
        ),
        "generated_asset_replacement_tool_preview": bounded_string_preview(
            work_order_template.get("generated_asset_replacement_tool_preview", []),
            8,
        ),
        "generated_asset_replacement_proof_contract_count": int(
            work_order_template.get("generated_asset_replacement_proof_contract_count", 0) or 0
        ),
        "generated_asset_replacement_gate_policy": [
            "Review generated asset lifecycle and quality proof before placeholder replacement.",
            "Do not execute replacement operations while import, proof, or ledger evidence is missing.",
            "Keep placeholder assets active until generated replacements pass compile/readback evidence gates.",
        ],
    }


def generated_animation_prompt_gate_context(work_order_template: Dict[str, Any]) -> Dict[str, Any]:
    prompt_count = int(work_order_template.get("generated_animation_prompt_count", 0) or 0)
    if prompt_count <= 0:
        return {
            "generated_animation_prompt_count": 0,
            "generated_animation_prompt_preview": [],
            "generated_animation_provider_preview": [],
            "generated_animation_target_skeleton_preview": [],
            "generated_animation_tool_preview": [],
            "generated_animation_proof_required_preview": [],
            "generated_animation_prompt_gate_policy": [],
            "estimated_uthana_motion_seconds": 0,
        }
    return {
        "generated_animation_prompt_count": prompt_count,
        "generated_animation_prompt_preview": bounded_string_preview(
            work_order_template.get("generated_animation_prompt_preview", []),
            5,
        ),
        "generated_animation_provider_preview": bounded_string_preview(
            work_order_template.get("generated_animation_provider_preview", []),
            5,
        ),
        "generated_animation_target_skeleton_preview": bounded_string_preview(
            work_order_template.get("generated_animation_target_skeleton_preview", []),
            5,
        ),
        "generated_animation_tool_preview": bounded_string_preview(
            work_order_template.get("generated_animation_tool_preview", []),
            8,
        ),
        "generated_animation_proof_required_preview": bounded_string_preview(
            work_order_template.get("generated_animation_proof_required_preview", []),
            8,
        ),
        "generated_animation_prompt_gate_policy": [
            "Review Uthana motion prompts and lifecycle manifest before text-to-motion or animation replacement work.",
            "Do not call Uthana, download, import, retarget, edit AnimGraph, or run PIE until auth, usage, bridge, proof, and ledger gates are clear.",
            "Keep fallback animation active until generated motion retarget/readback, AnimGraph, PIE, and ledger proof pass.",
        ],
        "estimated_uthana_motion_seconds": int(work_order_template.get("estimated_uthana_motion_seconds", 0) or 0),
    }


def build_clean_hud_summary(
    *,
    selected_session: str,
    ledger: Dict[str, Any],
    blocking_gates: List[str],
    readiness_policy: Dict[str, Any],
    readiness_repair_queue: Dict[str, Any],
    work_order_template: Dict[str, Any],
    next_safe_step: Dict[str, Any],
    execution_review: Dict[str, Any],
    generated_asset_quality_gate: Dict[str, Any],
    generated_animation_lifecycle_gate: Dict[str, Any],
    evidence_recording: Dict[str, Any],
    platform_preflight: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a bounded top-level packet for the native HUD strip."""
    blocker_preview = bounded_string_preview(blocking_gates, 3)
    hidden_blocker_count = max(0, len(blocking_gates) - len(blocker_preview))
    feature_title = str(work_order_template.get("display_name") or work_order_template.get("template_name") or "")
    next_operation_summary = str(work_order_template.get("next_editor_operation_summary", ""))
    next_action_tool = str(next_safe_step.get("next_action_tool") or execution_review.get("target_action", {}).get("tool", ""))
    next_operator_handoff = {}
    raw_handoffs = (
        readiness_repair_queue.get("next_operator_command_handoff")
        if isinstance(readiness_repair_queue.get("next_operator_command_handoff"), list)
        else []
    )
    if raw_handoffs and isinstance(raw_handoffs[0], dict):
        next_operator_handoff = raw_handoffs[0]
    if not next_operator_handoff:
        for item in evidence_recording.get("items", []) if isinstance(evidence_recording.get("items"), list) else []:
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            target_handoffs = (
                metadata.get("target_review_operator_command_handoff")
                if isinstance(metadata.get("target_review_operator_command_handoff"), list)
                else []
            )
            if target_handoffs and isinstance(target_handoffs[0], dict):
                next_operator_handoff = target_handoffs[0]
                break
        if not next_operator_handoff:
            for item in evidence_recording.get("items", []) if isinstance(evidence_recording.get("items"), list) else []:
                if not isinstance(item, dict):
                    continue
                metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                metadata_handoffs = (
                    metadata.get("operator_command_handoff")
                    if isinstance(metadata.get("operator_command_handoff"), list)
                    else []
                )
                if metadata_handoffs and isinstance(metadata_handoffs[0], dict):
                    next_operator_handoff = metadata_handoffs[0]
                    break
    next_handoff_id = str(next_operator_handoff.get("id", ""))
    next_handoff_label = str(next_operator_handoff.get("label") or next_handoff_id)
    next_handoff_command = str(next_operator_handoff.get("command", ""))
    next_handoff_receipt_path = str(next_operator_handoff.get("receipt_path", ""))
    next_handoff_command_kind = str(next_operator_handoff.get("command_kind", ""))
    next_handoff_records_evidence_only = bool(next_operator_handoff.get("records_evidence_only", False))
    next_handoff_requires_bridge = bool(next_operator_handoff.get("requires_bridge", False))
    next_handoff_requires_spend = bool(next_operator_handoff.get("requires_spend", False))
    next_handoff_requires_human_approval = bool(next_operator_handoff.get("requires_human_approval", False))
    next_handoff_no_provider_call = bool(next_operator_handoff.get("no_provider_call", True))
    next_handoff_no_spend = bool(next_operator_handoff.get("no_spend", not next_handoff_requires_spend))
    next_handoff_no_task_submission = bool(next_operator_handoff.get("no_task_submission", True))
    next_handoff_no_download = bool(next_operator_handoff.get("no_download", True))
    next_handoff_no_import = bool(next_operator_handoff.get("no_import", True))
    next_handoff_no_stage = bool(next_operator_handoff.get("no_stage", True))
    next_handoff_no_commit = bool(next_operator_handoff.get("no_commit", True))
    next_handoff_no_branch_or_merge = bool(next_operator_handoff.get("no_branch_or_merge", True))
    next_handoff_no_editor_mutation = bool(next_operator_handoff.get("no_editor_mutation", True))
    next_handoff_no_git_mutation = bool(next_operator_handoff.get("no_git_mutation", True))
    if next_handoff_records_evidence_only and next_handoff_no_provider_call and next_handoff_no_editor_mutation and next_handoff_no_git_mutation:
        next_handoff_safety_label = "local evidence only"
    elif next_handoff_requires_bridge:
        next_handoff_safety_label = "live bridge evidence"
    elif next_handoff_no_provider_call and next_handoff_no_editor_mutation and next_handoff_no_git_mutation:
        next_handoff_safety_label = "local validation"
    else:
        next_handoff_safety_label = "review before executing"
    can_execute_next_action = bool(next_safe_step.get("can_execute_now", False))
    next_step_primary = (
        next_action_tool
        if can_execute_next_action and next_action_tool
        else (next_handoff_label or next_action_tool or "No queued editor action")
    )
    next_step_secondary = str(next_safe_step.get("next_action_label") or next_safe_step.get("next_action_id") or "")
    if (not can_execute_next_action or not next_step_secondary) and next_handoff_id:
        next_step_secondary = str(next_handoff_safety_label or next_handoff_command_kind or next_handoff_receipt_path or next_handoff_command)
    generated_asset_count = int(generated_asset_quality_gate.get("asset_count", 0) or 0)
    generated_animation_count = int(generated_animation_lifecycle_gate.get("animation_asset_count", 0) or 0)
    provider_review_state = str(platform_preflight.get("provider_config_review_receipt_state", "missing"))
    bridge_state = str(platform_preflight.get("bridge_ping_receipt_state", "missing"))
    generated_animation_target = (
        generated_animation_lifecycle_gate.get("target_animation")
        if isinstance(generated_animation_lifecycle_gate.get("target_animation"), dict)
        else {}
    )
    generated_animation_next_action = (
        generated_animation_lifecycle_gate.get("next_safe_action")
        if isinstance(generated_animation_lifecycle_gate.get("next_safe_action"), dict)
        else {}
    )
    generated_animation_provider = str(
        generated_animation_lifecycle_gate.get("animation_provider")
        or generated_animation_target.get("provider")
        or ""
    )
    generated_animation_target_name = str(
        generated_animation_target.get("name")
        or generated_animation_next_action.get("target_animation_name")
        or ""
    )
    generated_animation_next_action_id = str(generated_animation_next_action.get("action_id", ""))
    generated_animation_usage_handoff = (
        generated_animation_lifecycle_gate.get("uthana_usage_next_operator_command_handoff")
        if isinstance(generated_animation_lifecycle_gate.get("uthana_usage_next_operator_command_handoff"), dict)
        else {}
    )
    generated_animation_usage_handoff_id = str(generated_animation_usage_handoff.get("id", ""))
    generated_animation_primary = f"{generated_asset_count} asset(s), {generated_animation_count} animation(s)"
    generated_animation_secondary = f"provider review: {provider_review_state}"
    if generated_animation_count:
        animation_label_parts = [
            part
            for part in (
                generated_animation_provider,
                generated_animation_target_name,
            )
            if part
        ]
        if animation_label_parts:
            generated_animation_secondary = ": ".join(animation_label_parts)
        elif generated_animation_next_action_id:
            generated_animation_secondary = generated_animation_next_action_id
        if generated_animation_next_action_id:
            generated_animation_secondary = (
                f"{generated_animation_secondary} -> {generated_animation_next_action_id}"
                if generated_animation_secondary
                else generated_animation_next_action_id
            )
    blueprint_evidence_contract = (
        platform_preflight.get("blueprint_mutation_evidence_contract")
        if isinstance(platform_preflight.get("blueprint_mutation_evidence_contract"), dict)
        else {}
    )
    blueprint_pre_read_recorded = bool(blueprint_evidence_contract.get("pre_read_evidence_recorded", False))
    blueprint_compile_plan_recorded = bool(blueprint_evidence_contract.get("compile_plan_recorded", False))
    blueprint_readback_plan_recorded = bool(blueprint_evidence_contract.get("readback_plan_recorded", False))
    blueprint_evidence_state = str(blueprint_evidence_contract.get("state", "missing"))
    if blueprint_evidence_state in {"", "missing"}:
        blueprint_evidence_state = "missing_evidence"
    blueprint_missing_gate_order = [
        ("blueprint_pre_read_evidence", blueprint_pre_read_recorded),
        ("blueprint_compile_plan", blueprint_compile_plan_recorded),
        ("blueprint_readback_plan", blueprint_readback_plan_recorded),
    ]
    blueprint_missing_gates = [gate for gate, recorded in blueprint_missing_gate_order if not recorded]
    blueprint_handoffs = (
        blueprint_evidence_contract.get("operator_command_handoff")
        if isinstance(blueprint_evidence_contract.get("operator_command_handoff"), list)
        else []
    )
    blueprint_next_handoff = {}
    for missing_gate in blueprint_missing_gates:
        for handoff in blueprint_handoffs:
            if isinstance(handoff, dict) and str(handoff.get("evidence_gate", "")) == missing_gate:
                blueprint_next_handoff = handoff
                break
        if blueprint_next_handoff:
            break
    if not blueprint_next_handoff:
        blueprint_next_handoff = next((handoff for handoff in blueprint_handoffs if isinstance(handoff, dict)), {})
    blueprint_next_handoff_id = str(blueprint_next_handoff.get("id", ""))
    blueprint_next_handoff_label = str(blueprint_next_handoff.get("label") or blueprint_next_handoff_id)
    blueprint_next_gate = str(blueprint_next_handoff.get("evidence_gate") or (blueprint_missing_gates[0] if blueprint_missing_gates else ""))
    blueprint_receipt_path = str(
        blueprint_evidence_contract.get("receipt_path")
        or blueprint_evidence_contract.get("path")
        or blueprint_next_handoff.get("receipt_path", "")
    )
    blueprint_recorded_count = 3 - len(blueprint_missing_gates)
    blueprint_summary = (
        f"{blueprint_recorded_count}/3 recorded"
        if blueprint_missing_gates
        else "pre-read/compile/readback recorded"
    )
    blueprint_safety_label = "blueprint evidence only"
    blueprint_no_mutation = bool(blueprint_evidence_contract.get("no_blueprint_mutation", True))
    blueprint_no_editor_mutation = bool(blueprint_evidence_contract.get("no_editor_mutation", True))
    blueprint_no_compile = bool(blueprint_evidence_contract.get("no_compile", True))
    blueprint_no_save = bool(blueprint_evidence_contract.get("no_save", True))
    blueprint_no_pie = bool(blueprint_evidence_contract.get("no_pie", True))
    overall_state = "blocked" if blocking_gates else ("ready" if ledger else "missing")

    compact_cards = [
        {
            "id": "session",
            "title": "Session",
            "state": "ready" if ledger else "missing",
            "primary": selected_session,
            "secondary": str(ledger.get("work_order_phase") or ledger.get("next_phase") or ledger.get("latest_phase") or ""),
        },
        {
            "id": "readiness",
            "title": "Readiness",
            "state": str(readiness_policy.get("state", overall_state)),
            "primary": (
                "All local gates clear"
                if not blocking_gates
                else f"{len(blocking_gates)} gate(s) need attention"
            ),
            "secondary": ", ".join(blocker_preview),
            "overflow_count": hidden_blocker_count,
        },
        {
            "id": "feature",
            "title": "Feature",
            "state": "ready" if work_order_template else "missing",
            "primary": feature_title,
            "secondary": next_operation_summary,
        },
        {
            "id": "next_safe_step",
            "title": "Next Step",
            "state": str(next_safe_step.get("state") or execution_review.get("state") or "empty"),
            "primary": next_step_primary,
            "secondary": next_step_secondary,
            "can_execute_now": bool(next_safe_step.get("can_execute_now", False)),
            "next_operator_handoff_id": next_handoff_id,
        },
        {
            "id": "generation",
            "title": "Generation",
            "state": str(generated_asset_quality_gate.get("state") or generated_animation_lifecycle_gate.get("state") or "missing"),
            "primary": generated_animation_primary,
            "secondary": generated_animation_secondary,
            "animation_provider": generated_animation_provider,
            "animation_target_name": generated_animation_target_name,
            "animation_next_safe_action_id": generated_animation_next_action_id,
            "animation_usage_next_operator_handoff_id": generated_animation_usage_handoff_id,
        },
        {
            "id": "evidence",
            "title": "Evidence",
            "state": "blocked" if evidence_recording.get("blocked_count", 0) else ("ready" if evidence_recording.get("item_count", 0) else "empty"),
            "primary": f"{int(evidence_recording.get('pending_count', 0) or 0)} pending, {int(evidence_recording.get('recorded_count', 0) or 0)} recorded",
            "secondary": str(evidence_recording.get("record_tool", "")),
        },
    ]
    return {
        "schema": "unreal_mcp_chat_cockpit_hud_summary.v1",
        "state": overall_state,
        "selected_session": selected_session,
        "visible_card_count": len(compact_cards),
        "max_visible_cards": 6,
        "compact_cards": compact_cards,
        "primary_blocker_preview": blocker_preview,
        "primary_blocker_overflow_count": hidden_blocker_count,
        "next_safe_action_tool": next_action_tool,
        "next_safe_action_id": str(next_safe_step.get("next_action_id", "")),
        "can_execute_next_safe_action": bool(next_safe_step.get("can_execute_now", False)),
        "next_operator_handoff_id": next_handoff_id,
        "next_operator_handoff_label": next_handoff_label,
        "next_operator_handoff_command": next_handoff_command,
        "next_operator_handoff_command_kind": next_handoff_command_kind,
        "next_operator_handoff_receipt_path": next_handoff_receipt_path,
        "next_operator_handoff_safety_label": next_handoff_safety_label,
        "next_operator_handoff_records_evidence_only": next_handoff_records_evidence_only,
        "next_operator_handoff_requires_bridge": next_handoff_requires_bridge,
        "next_operator_handoff_requires_spend": next_handoff_requires_spend,
        "next_operator_handoff_requires_human_approval": next_handoff_requires_human_approval,
        "next_operator_handoff_no_provider_call": next_handoff_no_provider_call,
        "next_operator_handoff_no_spend": next_handoff_no_spend,
        "next_operator_handoff_no_task_submission": next_handoff_no_task_submission,
        "next_operator_handoff_no_download": next_handoff_no_download,
        "next_operator_handoff_no_import": next_handoff_no_import,
        "next_operator_handoff_no_stage": next_handoff_no_stage,
        "next_operator_handoff_no_commit": next_handoff_no_commit,
        "next_operator_handoff_no_branch_or_merge": next_handoff_no_branch_or_merge,
        "next_operator_handoff_no_editor_mutation": next_handoff_no_editor_mutation,
        "next_operator_handoff_no_git_mutation": next_handoff_no_git_mutation,
        "bridge_ping_receipt_state": bridge_state,
        "provider_config_review_receipt_state": provider_review_state,
        "feature_template_name": str(work_order_template.get("template_name", "")),
        "feature_template_display_name": feature_title,
        "next_editor_operation_id": str(work_order_template.get("next_editor_operation_id", "")),
        "next_editor_operation_summary": next_operation_summary,
        "generated_asset_count": generated_asset_count,
        "generated_animation_count": generated_animation_count,
        "generated_animation_provider": generated_animation_provider,
        "generated_animation_target_name": generated_animation_target_name,
        "generated_animation_next_safe_action_id": generated_animation_next_action_id,
        "generated_animation_next_safe_tool": str(generated_animation_next_action.get("tool", "")),
        "generated_animation_usage_next_operator_handoff_id": generated_animation_usage_handoff_id,
        "generated_animation_usage_receipt_path": str(generated_animation_lifecycle_gate.get("uthana_usage_receipt_path", "")),
        "blueprint_mutation_evidence_state": blueprint_evidence_state,
        "blueprint_mutation_evidence_summary": blueprint_summary,
        "blueprint_mutation_evidence_recorded_count": blueprint_recorded_count,
        "blueprint_mutation_evidence_missing_count": len(blueprint_missing_gates),
        "blueprint_mutation_missing_gate_preview": blueprint_missing_gates,
        "blueprint_mutation_next_gate": blueprint_next_gate,
        "blueprint_mutation_next_operator_handoff_id": blueprint_next_handoff_id,
        "blueprint_mutation_next_operator_handoff_label": blueprint_next_handoff_label,
        "blueprint_mutation_evidence_receipt_path": blueprint_receipt_path,
        "blueprint_mutation_safety_label": blueprint_safety_label,
        "blueprint_mutation_pre_read_evidence_recorded": blueprint_pre_read_recorded,
        "blueprint_mutation_compile_plan_recorded": blueprint_compile_plan_recorded,
        "blueprint_mutation_readback_plan_recorded": blueprint_readback_plan_recorded,
        "blueprint_mutation_no_blueprint_mutation": blueprint_no_mutation,
        "blueprint_mutation_no_editor_mutation": blueprint_no_editor_mutation,
        "blueprint_mutation_no_compile": blueprint_no_compile,
        "blueprint_mutation_no_save": blueprint_no_save,
        "blueprint_mutation_no_pie": blueprint_no_pie,
        "evidence_pending_count": int(evidence_recording.get("pending_count", 0) or 0),
        "evidence_blocked_count": int(evidence_recording.get("blocked_count", 0) or 0),
        "layout_policy": [
            "Render compact_cards first; keep detailed cards and workflow_actions behind drill-down controls.",
            "Show at most max_visible_cards in the primary HUD strip.",
            "Use primary_blocker_overflow_count instead of listing every blocker in the visible HUD.",
            "Show next_operator_handoff_* as the copyable local receipt/test action only in drill-down UI.",
            "Use next_operator_handoff_safety_label in visible native UI; keep command text behind drill-down/copy affordances.",
            "Show Blueprint mutation evidence as compact inspect/compile/readback proof state, not as permission to mutate.",
        ],
        "detail_sources": ["cards", "workflow_actions", "readiness_policy", "evidence_recording"],
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
    }


def build_queue_target_context(
    *,
    target_phase: str,
    work_order_template: Dict[str, Any],
    ledger_path: str,
    generated_animation_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if not target_phase:
        return {}
    return {
        "target_phase": target_phase,
        "template_name": str(work_order_template.get("template_name", "")),
        "display_name": str(work_order_template.get("display_name", "")),
        "operation_count": int(work_order_template.get("operation_count", 0) or 0),
        "editor_operation_count": int(work_order_template.get("editor_operation_count", 0) or 0),
        "bridge_required_operation_count": int(work_order_template.get("bridge_required_operation_count", 0) or 0),
        "compile_after_operation_count": int(work_order_template.get("compile_after_operation_count", 0) or 0),
        "readback_after_operation_count": int(work_order_template.get("readback_after_operation_count", 0) or 0),
        "compile_check_count": int(work_order_template.get("compile_check_count", 0) or 0),
        "evidence_requirement_count": int(work_order_template.get("evidence_requirement_count", 0) or 0),
        "operation_proof_contract_count": int(work_order_template.get("operation_proof_contract_count", 0) or 0),
        "operation_proof_required_after_preview": bounded_string_preview(
            work_order_template.get("operation_proof_required_after_preview", []),
            8,
        ),
        "editor_operation_type_preview": bounded_string_preview(work_order_template.get("editor_operation_type_preview", []), 6),
        "editor_operation_tool_preview": bounded_string_preview(work_order_template.get("editor_operation_tool_preview", []), 8),
        "editor_operation_preview": bounded_string_preview(work_order_template.get("editor_operation_preview", []), 5),
        "next_editor_operation_id": str(work_order_template.get("next_editor_operation_id", "")),
        "next_editor_operation_type": str(work_order_template.get("next_editor_operation_type", "")),
        "next_editor_operation_summary": str(work_order_template.get("next_editor_operation_summary", "")),
        "next_editor_operation_tool_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_tool_preview", []),
            5,
        ),
        "next_editor_operation_requires_bridge": bool(work_order_template.get("next_editor_operation_requires_bridge", False)),
        "next_editor_operation_requires_compile_after": bool(work_order_template.get("next_editor_operation_requires_compile_after", False)),
        "next_editor_operation_requires_readback_after": bool(work_order_template.get("next_editor_operation_requires_readback_after", False)),
        "next_editor_operation_required_before_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_required_before_preview", []),
            5,
        ),
        "next_editor_operation_required_after_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_required_after_preview", []),
            5,
        ),
        "next_editor_operation_stop_if_missing_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_stop_if_missing_preview", []),
            5,
        ),
        **generated_asset_replacement_operation_gate_context(work_order_template),
        **generated_animation_prompt_gate_context(work_order_template),
        **generated_animation_operation_gate_context(generated_animation_context or {}),
        "ledger_path": ledger_path,
    }


def generated_animation_operation_gate_context(generated_animation_context: Dict[str, Any]) -> Dict[str, Any]:
    target_animation = (
        generated_animation_context.get("target_animation")
        if isinstance(generated_animation_context.get("target_animation"), dict)
        else {}
    )
    next_safe_action = (
        generated_animation_context.get("next_safe_action")
        if isinstance(generated_animation_context.get("next_safe_action"), dict)
        else {}
    )
    usage_contract = (
        generated_animation_context.get("uthana_usage_contract")
        if isinstance(generated_animation_context.get("uthana_usage_contract"), dict)
        else {}
    )
    usage_handoff = usage_contract.get("operator_command_handoff") if isinstance(usage_contract.get("operator_command_handoff"), list) else []
    next_usage_handoff = (
        generated_animation_context.get("uthana_usage_next_operator_command_handoff")
        if isinstance(generated_animation_context.get("uthana_usage_next_operator_command_handoff"), dict)
        else {}
    )
    animation_asset_count = int(generated_animation_context.get("animation_asset_count", 0) or 0)
    if animation_asset_count <= 0:
        return {
            "generated_animation_asset_count": 0,
            "generated_animation_pending_count": 0,
            "generated_animation_quality_evidence_missing_count": 0,
            "generated_animation_missing_stage_preview": [],
            "generated_animation_gate_policy": [],
        }
    return {
        "generated_animation_asset_count": animation_asset_count,
        "generated_animation_pending_count": int(generated_animation_context.get("animation_pending_count", 0) or 0),
        "generated_animation_target_name": str(target_animation.get("name", "")),
        "generated_animation_target_provider": str(target_animation.get("provider", "")),
        "generated_animation_target_task_status": str(target_animation.get("task_status", "")),
        "generated_animation_target_motion_id": str(target_animation.get("motion_id", "")),
        "generated_animation_target_skeleton": str(target_animation.get("target_skeleton", "")),
        "generated_animation_quality_proof_contract_schema": str(generated_animation_context.get("quality_proof_contract_schema", "")),
        "generated_animation_quality_evidence_missing_count": int(
            generated_animation_context.get("quality_evidence_missing_count", 0) or 0
        ),
        "generated_animation_missing_stage_preview": bounded_string_preview(
            generated_animation_context.get("missing_stage_preview", []),
            8,
        ),
        "generated_animation_next_safe_action_id": str(next_safe_action.get("action_id", "")),
        "generated_animation_next_safe_tool": str(next_safe_action.get("tool", "")),
        "generated_animation_usage_contract_schema": str(usage_contract.get("schema", "")),
        "generated_animation_usage_receipt_path": str(usage_contract.get("review_receipt_path", "")),
        "generated_animation_usage_confirmation_field": str(usage_contract.get("usage_confirmation_field", "")),
        "generated_animation_allowance_tool_preview": bounded_string_preview(usage_contract.get("allowance_tools", []), 4),
        "generated_animation_allowance_review_steps": bounded_string_preview(usage_contract.get("allowance_review_steps", []), 5),
        "generated_animation_usage_operator_command_handoff_count": len(usage_handoff),
        "generated_animation_usage_operator_command_handoff_ids": bounded_string_preview(
            [str(item.get("id", "")) for item in usage_handoff if isinstance(item, dict)],
            4,
        ),
        "generated_animation_usage_next_operator_command_handoff": dict(next_usage_handoff),
        "generated_animation_usage_next_operator_command_handoff_id": str(next_usage_handoff.get("id", "")),
        "generated_animation_gate_policy": [
            "Review Uthana animation lifecycle and quality proof before import, retarget, AnimGraph, or replacement work.",
            "Do not execute generated animation work while provider, bridge, proof, or ledger evidence is missing.",
            "Keep fallback animation active until retarget/readback, AnimGraph, PIE, and ledger evidence pass.",
        ],
    }


def cockpit_workflow_action(
    *,
    action_id: str,
    label: str,
    tool: str,
    arguments: Dict[str, Any],
    enabled: bool,
    reason: str,
    requires_bridge: bool = False,
    requires_ledger: bool = False,
    records_evidence: bool = False,
    input_source: str = "",
    target_start_context: Dict[str, Any] | None = None,
    target_status_context: Dict[str, Any] | None = None,
    target_work_order_context: Dict[str, Any] | None = None,
    target_gameplay_template_context: Dict[str, Any] | None = None,
    target_placeholder_context: Dict[str, Any] | None = None,
    target_evidence_item: Dict[str, Any] | None = None,
    target_blocker_resolution: Dict[str, Any] | None = None,
    target_queue_context: Dict[str, Any] | None = None,
    target_repair_context: Dict[str, Any] | None = None,
    target_execute_context: Dict[str, Any] | None = None,
    target_resume_context: Dict[str, Any] | None = None,
    target_dashboard_context: Dict[str, Any] | None = None,
    target_readiness_policy_context: Dict[str, Any] | None = None,
    target_blueprint_mutation_context: Dict[str, Any] | None = None,
    target_platform_preflight_context: Dict[str, Any] | None = None,
    target_live_editor_context: Dict[str, Any] | None = None,
    target_wip_promotion_context: Dict[str, Any] | None = None,
    target_bridge_wrapper_context: Dict[str, Any] | None = None,
    target_test_lane_context: Dict[str, Any] | None = None,
    target_generated_asset_context: Dict[str, Any] | None = None,
    target_generated_asset_review_context: Dict[str, Any] | None = None,
    target_asset_lifecycle_compile_context: Dict[str, Any] | None = None,
    target_generated_asset_lifecycle_context: Dict[str, Any] | None = None,
    target_generated_asset_import_context: Dict[str, Any] | None = None,
    target_generated_asset_quality_proof_context: Dict[str, Any] | None = None,
    target_generated_asset_replacement_context: Dict[str, Any] | None = None,
    target_generated_animation_lifecycle_context: Dict[str, Any] | None = None,
    target_generated_asset_provider_task_context: Dict[str, Any] | None = None,
    target_provider_config_context: Dict[str, Any] | None = None,
    target_provider_spend_context: Dict[str, Any] | None = None,
    target_queue_review_context: Dict[str, Any] | None = None,
    target_evidence_review_context: Dict[str, Any] | None = None,
    target_evidence_ledger_context: Dict[str, Any] | None = None,
    target_execution_review_context: Dict[str, Any] | None = None,
    target_repair_review_context: Dict[str, Any] | None = None,
    target_runtime_review_context: Dict[str, Any] | None = None,
    target_readiness_repair_queue_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    action = {
        "id": action_id,
        "label": label,
        "tool": tool,
        "arguments": arguments,
        "enabled": bool(enabled),
        "reason": reason,
        "requires_bridge": bool(requires_bridge),
        "requires_ledger": bool(requires_ledger),
        "records_evidence": bool(records_evidence),
        "input_source": input_source,
    }
    if target_start_context:
        action["target_start_context"] = target_start_context
    if target_status_context:
        action["target_status_context"] = target_status_context
    if target_work_order_context:
        action["target_work_order_context"] = target_work_order_context
    if target_gameplay_template_context:
        action["target_gameplay_template_context"] = target_gameplay_template_context
    if target_placeholder_context:
        action["target_placeholder_context"] = target_placeholder_context
    if target_evidence_item:
        action["target_evidence_item_id"] = target_evidence_item.get("id", "")
        action["target_evidence_item"] = target_evidence_item
        action["target_evidence_context"] = evidence_target_context(target_evidence_item)
    if target_blocker_resolution:
        action["target_blocker_id"] = target_blocker_resolution.get("blocker", "")
        action["target_blocker_resolution"] = target_blocker_resolution
    if target_queue_context:
        action["target_queue_phase"] = target_queue_context.get("target_phase", "")
        action["target_queue_context"] = target_queue_context
    if target_repair_context:
        action["target_repair_id"] = target_repair_context.get("id", "")
        action["target_repair_context"] = target_repair_context
    if target_execute_context:
        action["target_execute_id"] = target_execute_context.get("action_id", "")
        action["target_execute_context"] = target_execute_context
    if target_resume_context:
        action["target_resume_context"] = target_resume_context
    if target_dashboard_context:
        action["target_dashboard_context"] = target_dashboard_context
    if target_readiness_policy_context:
        action["target_readiness_policy_context"] = target_readiness_policy_context
    if target_readiness_repair_queue_context:
        action["target_readiness_repair_queue_context"] = target_readiness_repair_queue_context
    if target_blueprint_mutation_context:
        action["target_blueprint_mutation_context"] = target_blueprint_mutation_context
    if target_platform_preflight_context:
        action["target_platform_preflight_context"] = target_platform_preflight_context
    if target_live_editor_context:
        action["target_live_editor_context"] = target_live_editor_context
    if target_wip_promotion_context:
        action["target_wip_promotion_context"] = target_wip_promotion_context
    if target_bridge_wrapper_context:
        action["target_bridge_wrapper_context"] = target_bridge_wrapper_context
    if target_test_lane_context:
        action["target_test_lane_context"] = target_test_lane_context
    if target_execution_review_context:
        action["target_execution_review_context"] = target_execution_review_context
    if target_repair_review_context:
        action["target_repair_review_context"] = target_repair_review_context
    if target_runtime_review_context:
        action["target_runtime_review_context"] = target_runtime_review_context
    if target_generated_asset_context:
        action["target_generated_asset_id"] = target_generated_asset_context.get("id", "")
        action["target_generated_asset_context"] = target_generated_asset_context
    if target_generated_asset_review_context:
        action["target_generated_asset_review_context"] = target_generated_asset_review_context
    if target_asset_lifecycle_compile_context:
        action["target_asset_lifecycle_compile_context"] = target_asset_lifecycle_compile_context
    if target_generated_asset_lifecycle_context:
        action["target_generated_asset_lifecycle_context"] = target_generated_asset_lifecycle_context
    if target_generated_asset_import_context:
        action["target_generated_asset_import_context"] = target_generated_asset_import_context
    if target_generated_asset_quality_proof_context:
        action["target_generated_asset_quality_proof_context"] = target_generated_asset_quality_proof_context
    if target_generated_asset_replacement_context:
        action["target_generated_asset_replacement_context"] = target_generated_asset_replacement_context
    if target_generated_animation_lifecycle_context:
        action["target_generated_animation_lifecycle_context"] = target_generated_animation_lifecycle_context
    if target_generated_asset_provider_task_context:
        action["target_generated_asset_provider_task_context"] = target_generated_asset_provider_task_context
    if target_provider_config_context:
        action["target_provider_config_context"] = target_provider_config_context
    if target_provider_spend_context:
        action["target_provider_spend_context"] = target_provider_spend_context
    if target_queue_review_context:
        action["target_queue_review_context"] = target_queue_review_context
    if target_evidence_review_context:
        action["target_evidence_review_context"] = target_evidence_review_context
    if target_evidence_ledger_context:
        action["target_evidence_event_count"] = target_evidence_ledger_context.get("event_count", 0)
        action["target_evidence_ledger_context"] = target_evidence_ledger_context
    return action


def evidence_ledger_context(ledger: Dict[str, Any]) -> Dict[str, Any]:
    preview_events = ledger.get("preview_events") if isinstance(ledger.get("preview_events"), list) else []
    events = [event for event in preview_events if isinstance(event, dict)]
    latest_event = events[-1] if events else {}
    artifact_total = 0
    for event in events:
        if isinstance(event.get("artifact_count"), int):
            artifact_total += int(event.get("artifact_count", 0) or 0)
        else:
            artifacts = event.get("artifact_preview") if isinstance(event.get("artifact_preview"), list) else []
            artifact_total += len(artifacts)
    return {
        "ledger_path": str(ledger.get("ledger_path", "")),
        "session_name": str(ledger.get("session_name", "")),
        "event_count": int(ledger.get("event_count", len(events)) or 0),
        "preview_event_count": len(events),
        "artifact_count": artifact_total,
        "latest_phase": str(latest_event.get("phase_name", ledger.get("latest_phase", ""))),
        "latest_evidence_type": str(latest_event.get("evidence_type", "")),
        "latest_summary": str(latest_event.get("summary", "")),
        "latest_artifact_preview": bounded_string_preview(latest_event.get("artifact_preview", []), 5),
        "timeline_preview": [
            {
                "phase_name": str(event.get("phase_name", "")),
                "evidence_type": str(event.get("evidence_type", "")),
                "summary": str(event.get("summary", "")),
                "artifact_count": int(event.get("artifact_count", 0) or 0),
                "artifact_preview": bounded_string_preview(event.get("artifact_preview", []), 3),
            }
            for event in events[:5]
        ],
    }


def evidence_target_context(target_evidence_item: Dict[str, Any]) -> Dict[str, Any]:
    artifacts = target_evidence_item.get("required_artifacts") if isinstance(target_evidence_item.get("required_artifacts"), list) else []
    metadata = target_evidence_item.get("metadata") if isinstance(target_evidence_item.get("metadata"), dict) else {}
    context: Dict[str, Any] = {
        "id": str(target_evidence_item.get("id", "")),
        "source": str(target_evidence_item.get("source", "")),
        "phase_name": str(target_evidence_item.get("phase_name", "")),
        "evidence_type": str(target_evidence_item.get("evidence_type", "")),
        "label": str(target_evidence_item.get("label", "")),
        "state": str(target_evidence_item.get("state", "")),
        "requires_bridge": bool(target_evidence_item.get("requires_bridge", False)),
        "artifact_count": int(target_evidence_item.get("required_artifact_count", len(artifacts)) or 0),
        "artifact_preview": bounded_string_preview(artifacts, 5),
        "suggested_summary": str(target_evidence_item.get("suggested_summary", "")),
    }
    if metadata:
        evidence_type = str(target_evidence_item.get("evidence_type", ""))
        context["metadata_keys"] = sorted(str(key) for key in metadata.keys() if isinstance(key, str))[:12]
        readiness_policy = {
            "schema": metadata.get("schema", ""),
            "state": metadata.get("state", ""),
            "blocked_policy_count": int(metadata.get("blocked_policy_count", 0) or 0),
            "blocked_policy_preview": bounded_string_preview(metadata.get("blocked_policy_preview", []), 8),
            "editor_mutation_allowed": bool(metadata.get("editor_mutation_allowed", False)),
            "editor_mutation_missing_gate_count": int(metadata.get("editor_mutation_missing_gate_count", 0) or 0),
            "editor_mutation_missing_gate_preview": bounded_string_preview(metadata.get("editor_mutation_missing_gate_preview", []), 8),
            "editor_mutation_evidence_required_count": int(metadata.get("editor_mutation_evidence_required_count", 0) or 0),
            "editor_mutation_evidence_required_preview": bounded_string_preview(metadata.get("editor_mutation_evidence_required_preview", []), 8),
            "paid_generation_allowed": bool(metadata.get("paid_generation_allowed", False)),
            "paid_generation_missing_gate_count": int(metadata.get("paid_generation_missing_gate_count", 0) or 0),
            "paid_generation_missing_gate_preview": bounded_string_preview(metadata.get("paid_generation_missing_gate_preview", []), 8),
            "paid_generation_evidence_required_count": int(metadata.get("paid_generation_evidence_required_count", 0) or 0),
            "paid_generation_evidence_required_preview": bounded_string_preview(metadata.get("paid_generation_evidence_required_preview", []), 8),
            "paid_animation_generation_allowed": bool(metadata.get("paid_animation_generation_allowed", False)),
            "paid_animation_generation_missing_gate_count": int(metadata.get("paid_animation_generation_missing_gate_count", 0) or 0),
            "paid_animation_generation_missing_gate_preview": bounded_string_preview(metadata.get("paid_animation_generation_missing_gate_preview", []), 8),
            "paid_animation_generation_evidence_required_count": int(metadata.get("paid_animation_generation_evidence_required_count", 0) or 0),
            "paid_animation_generation_evidence_required_preview": bounded_string_preview(metadata.get("paid_animation_generation_evidence_required_preview", []), 8),
            "blueprint_mutation_allowed": bool(metadata.get("blueprint_mutation_allowed", False)),
            "blueprint_mutation_missing_gate_count": int(metadata.get("blueprint_mutation_missing_gate_count", 0) or 0),
            "blueprint_mutation_missing_gate_preview": bounded_string_preview(metadata.get("blueprint_mutation_missing_gate_preview", []), 8),
            "blueprint_mutation_evidence_required_count": int(metadata.get("blueprint_mutation_evidence_required_count", 0) or 0),
            "blueprint_mutation_evidence_required_preview": bounded_string_preview(metadata.get("blueprint_mutation_evidence_required_preview", []), 8),
            "wip_promotion_allowed": bool(metadata.get("wip_promotion_allowed", False)),
            "wip_promotion_missing_gate_count": int(metadata.get("wip_promotion_missing_gate_count", 0) or 0),
            "wip_promotion_missing_gate_preview": bounded_string_preview(metadata.get("wip_promotion_missing_gate_preview", []), 8),
            "wip_promotion_evidence_required_count": int(metadata.get("wip_promotion_evidence_required_count", 0) or 0),
            "wip_promotion_evidence_required_preview": bounded_string_preview(metadata.get("wip_promotion_evidence_required_preview", []), 10),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
        }
        filtered_readiness_policy = {
            str(key): value
            for key, value in readiness_policy.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "readiness_policy" and filtered_readiness_policy:
            context["readiness_policy"] = filtered_readiness_policy
        readiness_repair_queue = {
            "schema": metadata.get("schema", ""),
            "state": metadata.get("state", ""),
            "action_count": int(metadata.get("action_count", 0) or 0),
            "blocking_gate_count": int(metadata.get("blocking_gate_count", 0) or 0),
            "blocking_gate_preview": bounded_string_preview(metadata.get("blocking_gate_preview", []), 8),
            "recommended_next": metadata.get("recommended_next", ""),
            "next_action_id": metadata.get("next_action_id", ""),
            "next_gate": metadata.get("next_gate", ""),
            "next_policy_area": metadata.get("next_policy_area", ""),
            "next_recommended_contract": metadata.get("next_recommended_contract", ""),
            "next_recommended_tool": metadata.get("next_recommended_tool", ""),
            "next_evidence_required_preview": bounded_string_preview(metadata.get("next_evidence_required_preview", []), 8),
            "next_requires_manual_operator": bool(metadata.get("next_requires_manual_operator", False)),
            "next_requires_bridge": bool(metadata.get("next_requires_bridge", False)),
            "next_requires_network": bool(metadata.get("next_requires_network", False)),
            "next_requires_spend": bool(metadata.get("next_requires_spend", False)),
            "next_requires_unreal_editor": bool(metadata.get("next_requires_unreal_editor", False)),
            "next_receipt_command_template": metadata.get("next_receipt_command_template", ""),
            "next_operator_command_handoff": (
                list(metadata.get("next_operator_command_handoff", []))[:2]
                if isinstance(metadata.get("next_operator_command_handoff"), list)
                else []
            ),
            "no_auto_execute": bool(metadata.get("no_auto_execute", True)),
            "no_secret_echo": bool(metadata.get("no_secret_echo", True)),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
        }
        filtered_readiness_repair_queue = {
            str(key): value
            for key, value in readiness_repair_queue.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "readiness_repair_queue":
            context["readiness_repair_queue"] = filtered_readiness_repair_queue
        dirty_promotion_review = {
            "schema": metadata.get("schema", ""),
            "state": metadata.get("state", ""),
            "receipt_state": metadata.get("receipt_state", ""),
            "receipt_path": metadata.get("receipt_path", ""),
            "required_command": metadata.get("required_command", ""),
            "ready_for_promotion": bool(metadata.get("ready_for_promotion", False)),
            "dirty_risk": metadata.get("dirty_risk", ""),
            "dirty_group_count": int(metadata.get("dirty_group_count", 0) or 0),
            "evidence_unresolved_count": int(metadata.get("evidence_unresolved_count", 0) or 0),
            "target_review_group": metadata.get("target_review_group", ""),
            "target_review_order": int(metadata.get("target_review_order", 0) or 0),
            "target_review_scope": metadata.get("target_review_scope", ""),
            "target_review_tracked_count": int(metadata.get("target_review_tracked_count", 0) or 0),
            "target_review_untracked_count": int(metadata.get("target_review_untracked_count", 0) or 0),
            "target_review_status": metadata.get("target_review_status") or "missing_evidence",
            "target_review_evidence_complete": bool(metadata.get("target_review_evidence_complete", False)),
            "target_review_recorded_evidence_count": int(metadata.get("target_review_recorded_evidence_count", 0) or 0),
            "target_review_recorded_evidence_preview": bounded_string_preview(metadata.get("target_review_recorded_evidence_preview", []), 8),
            "target_review_human_approval_recorded": bool(metadata.get("target_review_human_approval_recorded", False)),
            "target_review_missing_evidence_count": int(metadata.get("target_review_missing_evidence_count", 0) or 0),
            "target_review_missing_evidence_preview": bounded_string_preview(metadata.get("target_review_missing_evidence_preview", []), 8),
            "target_review_required_evidence_preview": bounded_string_preview(metadata.get("target_review_required_evidence_preview", []), 8),
            "target_review_decision_prompt_preview": bounded_string_preview(metadata.get("target_review_decision_prompt_preview", []), 8),
            "target_review_receipt_command_template": metadata.get("target_review_receipt_command_template", ""),
            "target_review_approval_receipt_command_template": metadata.get("target_review_approval_receipt_command_template", ""),
            "target_review_receipt_command_policy": metadata.get("target_review_receipt_command_policy", ""),
            "target_review_operator_command_handoff": (
                list(metadata.get("target_review_operator_command_handoff", []))[:2]
                if isinstance(metadata.get("target_review_operator_command_handoff"), list)
                else []
            ),
            "target_review_pending_human_approval_only": bool(metadata.get("target_review_pending_human_approval_only", False)),
            "target_review_human_approval_gate": str(metadata.get("target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
            "target_review_human_approval_command_handoff": (
                list(metadata.get("target_review_human_approval_command_handoff", []))[:1]
                if isinstance(metadata.get("target_review_human_approval_command_handoff"), list)
                else []
            ),
            "target_review_focused_test_command_handoff": (
                list(metadata.get("target_review_focused_test_command_handoff", []))[:5]
                if isinstance(metadata.get("target_review_focused_test_command_handoff"), list)
                else []
            ),
            "target_review_focused_test_command_count": int(metadata.get("target_review_focused_test_command_count", 0) or 0),
            "target_review_focused_test_command_preview": bounded_string_preview(metadata.get("target_review_focused_test_command_preview", []), 5),
            "target_review_sample_preview": bounded_string_preview(metadata.get("target_review_sample_preview", []), 5),
            "target_review_promotion_allowed_after_receipt": bool(metadata.get("target_review_promotion_allowed_after_receipt", False)),
            "target_review_merge_policy": str(metadata.get("target_review_merge_policy", "")),
            "target_review_previous_evidence_merged": bool(metadata.get("target_review_previous_evidence_merged", False)),
            "target_review_reset_evidence": bool(metadata.get("target_review_reset_evidence", False)),
            "promotion_batch_policy": metadata.get("promotion_batch_policy", ""),
            "artifact_policy": metadata.get("artifact_policy", ""),
            "safe_promotion_next_steps": bounded_string_preview(metadata.get("safe_promotion_next_steps", []), 8),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
            "no_stage": bool(metadata.get("no_stage", True)),
            "no_commit": bool(metadata.get("no_commit", True)),
            "no_branch_or_merge": bool(metadata.get("no_branch_or_merge", True)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
        }
        filtered_dirty_promotion_review = {
            str(key): value
            for key, value in dirty_promotion_review.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "dirty_promotion_review":
            context["dirty_promotion_review"] = filtered_dirty_promotion_review
        generated_asset = {
            "asset_id": metadata.get("asset_id", ""),
            "asset_name": metadata.get("asset_name", ""),
            "asset_role": metadata.get("asset_role", ""),
            "provider": metadata.get("provider", ""),
            "state": metadata.get("state", ""),
            "task_status": metadata.get("task_status", ""),
            "next_gate": metadata.get("next_gate", ""),
            "manifest_path": metadata.get("manifest_path", ""),
            "expected_import_path": metadata.get("expected_import_path", ""),
            "imported_asset_path": metadata.get("imported_asset_path", ""),
            "has_placeholder": bool(metadata.get("has_placeholder", False)),
            "quality_gate_count": int(metadata.get("quality_gate_count", 0) or 0),
            "quality_evidence_count": int(metadata.get("quality_evidence_count", 0) or 0),
            "quality_gate_preview": bounded_string_preview(metadata.get("quality_gate_preview", []), 5),
            "import_or_quality_pass_allowed": bool(metadata.get("import_or_quality_pass_allowed", False)),
            "requires_successful_bridge_ping_before_import_or_quality": bool(metadata.get("requires_successful_bridge_ping_before_import_or_quality", True)),
            "requires_quality_evidence_before_replacement": bool(metadata.get("requires_quality_evidence_before_replacement", True)),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
            "no_task_submission": bool(metadata.get("no_task_submission", True)),
            "no_download": bool(metadata.get("no_download", True)),
            "no_import": bool(metadata.get("no_import", True)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
        }
        filtered_asset = {
            str(key): value
            for key, value in generated_asset.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "generated_asset_quality_gate" and filtered_asset:
            context["generated_asset"] = filtered_asset
        generated_animation = {
            "animation_id": metadata.get("animation_id", ""),
            "animation_name": metadata.get("animation_name", ""),
            "animation_role": metadata.get("animation_role", ""),
            "provider": metadata.get("provider", ""),
            "task_type": metadata.get("task_type", ""),
            "task_status": metadata.get("task_status", ""),
            "motion_id": metadata.get("motion_id", ""),
            "manifest_path": metadata.get("manifest_path", ""),
            "expected_import_path": metadata.get("expected_import_path", ""),
            "target_skeleton": metadata.get("target_skeleton", ""),
            "format": metadata.get("format", ""),
            "estimated_seconds": int(metadata.get("estimated_seconds", 0) or 0),
            "default_character_id": metadata.get("default_character_id", ""),
            "quality_gate_count": int(metadata.get("quality_gate_count", 0) or 0),
            "quality_evidence_count": int(metadata.get("quality_evidence_count", 0) or 0),
            "quality_evidence_missing_count": int(metadata.get("quality_evidence_missing_count", 0) or 0),
            "quality_proof_contract_schema": metadata.get("quality_proof_contract_schema", ""),
            "quality_proof_required_count": int(metadata.get("quality_proof_required_count", 0) or 0),
            "quality_proof_required_preview": bounded_string_preview(metadata.get("quality_proof_required_preview", []), 8),
            "missing_stage_preview": bounded_string_preview(metadata.get("missing_stage_preview", []), 5),
            "quality_gate_preview": bounded_string_preview(metadata.get("quality_gate_preview", []), 5),
            "compile_tool": metadata.get("compile_tool", ""),
            "submit_tool": metadata.get("submit_tool", ""),
            "download_tool": metadata.get("download_tool", ""),
            "import_tool": metadata.get("import_tool", ""),
            "uthana_usage_contract_schema": metadata.get("uthana_usage_contract_schema", ""),
            "uthana_usage_receipt_path": metadata.get("uthana_usage_receipt_path", ""),
            "uthana_usage_receipt_required_command": metadata.get("uthana_usage_receipt_required_command", ""),
            "uthana_allowance_tools": bounded_string_preview(metadata.get("uthana_allowance_tools", []), 4),
            "uthana_allowance_review_steps": bounded_string_preview(metadata.get("uthana_allowance_review_steps", []), 5),
            "uthana_usage_confirmation_field": metadata.get("uthana_usage_confirmation_field", ""),
            "uthana_usage_operator_command_handoff": (
                list(metadata.get("uthana_usage_operator_command_handoff", []))[:2]
                if isinstance(metadata.get("uthana_usage_operator_command_handoff"), list)
                else []
            ),
            "uthana_usage_next_operator_command_handoff": (
                dict(metadata.get("uthana_usage_next_operator_command_handoff", {}))
                if isinstance(metadata.get("uthana_usage_next_operator_command_handoff"), dict)
                else {}
            ),
            "no_provider_call": bool(metadata.get("no_provider_call", False)),
            "no_task_submission": bool(metadata.get("no_task_submission", False)),
            "no_download": bool(metadata.get("no_download", False)),
            "no_import": bool(metadata.get("no_import", False)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", False)),
        }
        filtered_animation = {
            str(key): value
            for key, value in generated_animation.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "generated_animation_evidence" and filtered_animation:
            context["generated_animation"] = filtered_animation
        paid_generation_evidence = {
            "schema": metadata.get("schema", ""),
            "state": metadata.get("state", ""),
            "provider": metadata.get("provider", ""),
            "missing_gate_count": int(metadata.get("missing_gate_count", 0) or 0),
            "missing_gate_preview": bounded_string_preview(metadata.get("missing_gate_preview", []), 8),
            "wallet_evidence_recorded": bool(metadata.get("wallet_evidence_recorded", False)),
            "mesh_wallet_evidence_recorded": bool(metadata.get("mesh_wallet_evidence_recorded", False)),
            "animation_allowance_evidence_recorded": bool(metadata.get("animation_allowance_evidence_recorded", False)),
            "spend_confirmation_recorded": bool(metadata.get("spend_confirmation_recorded", False)),
            "explicit_spend_approval_recorded": bool(metadata.get("explicit_spend_approval_recorded", False)),
            "explicit_usage_approval_recorded": bool(metadata.get("explicit_usage_approval_recorded", False)),
            "estimated_spend_reviewed": bool(metadata.get("estimated_spend_reviewed", False)),
            "estimated_motion_seconds_reviewed": bool(metadata.get("estimated_motion_seconds_reviewed", False)),
            "mesh_provider": metadata.get("mesh_provider", ""),
            "animation_provider": metadata.get("animation_provider", ""),
            "review_receipt_exists": bool(metadata.get("review_receipt_exists", False)),
            "review_receipt_state": metadata.get("review_receipt_state", ""),
            "review_receipt_path": metadata.get("review_receipt_path", ""),
            "review_receipt_required_command": metadata.get("review_receipt_required_command", ""),
            "mesh_wallet_tool": metadata.get("mesh_wallet_tool", ""),
            "animation_allowance_tools": bounded_string_preview(metadata.get("animation_allowance_tools", []), 3),
            "ledger_tool": metadata.get("ledger_tool", ""),
            "spend_approval_field": metadata.get("spend_approval_field", ""),
            "wallet_evidence_review_steps": bounded_string_preview(metadata.get("wallet_evidence_review_steps", []), 5),
            "wallet_evidence_receipt_command_template": metadata.get("wallet_evidence_receipt_command_template", ""),
            "mesh_wallet_evidence_receipt_command_template": metadata.get("mesh_wallet_evidence_receipt_command_template", ""),
            "animation_allowance_receipt_command_template": metadata.get("animation_allowance_receipt_command_template", ""),
            "spend_confirmation_receipt_command_template": metadata.get("spend_confirmation_receipt_command_template", ""),
            "operator_command_handoff": (
                list(metadata.get("operator_command_handoff", []))[:3]
                if isinstance(metadata.get("operator_command_handoff"), list)
                else []
            ),
            "no_spend_checks": bounded_string_preview(metadata.get("no_spend_checks", []), 5),
            "evidence_required_preview": bounded_string_preview(metadata.get("evidence_required_preview", []), 8),
            "fallback_tool": metadata.get("fallback_tool", ""),
            "fallback_reason": metadata.get("fallback_reason", ""),
            "network_required_now": bool(metadata.get("network_required_now", False)),
            "spend_required_now": bool(metadata.get("spend_required_now", False)),
            "future_network_required": bool(metadata.get("future_network_required", False)),
            "future_spend_required": bool(metadata.get("future_spend_required", False)),
            "unreal_editor_required_now": bool(metadata.get("unreal_editor_required_now", False)),
            "no_provider_call": bool(metadata.get("no_provider_call", False)),
            "no_credit_reservation": bool(metadata.get("no_credit_reservation", False)),
            "no_task_submission": bool(metadata.get("no_task_submission", False)),
            "no_ledger_write": bool(metadata.get("no_ledger_write", False)),
            "review_contract_no_ledger_write": bool(metadata.get("review_contract_no_ledger_write", False)),
        }
        filtered_paid_generation_evidence = {
            str(key): value
            for key, value in paid_generation_evidence.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "paid_generation_evidence" and filtered_paid_generation_evidence:
            context["paid_generation_evidence"] = filtered_paid_generation_evidence
        bridge_ping_receipt = {
            "schema": metadata.get("schema", ""),
            "receipt_state": metadata.get("receipt_state", ""),
            "receipt_exists": bool(metadata.get("receipt_exists", False)),
            "receipt_path": metadata.get("receipt_path", ""),
            "required_command": metadata.get("required_command", ""),
            "successful_bridge_ping": bool(metadata.get("successful_bridge_ping", False)),
            "bridge_ready": bool(metadata.get("bridge_ready", False)),
            "bridge_tcp_ready": bool(metadata.get("bridge_tcp_ready", False)),
            "bridge_host": metadata.get("bridge_host", ""),
            "bridge_port": int(metadata.get("bridge_port", 0) or 0),
            "editor_mutation_allowed": bool(metadata.get("editor_mutation_allowed", False)),
            "blueprint_missing_gate_count": int(metadata.get("blueprint_missing_gate_count", 0) or 0),
            "operator_command_handoff": (
                list(metadata.get("operator_command_handoff", []))[:1]
                if isinstance(metadata.get("operator_command_handoff"), list)
                else []
            ),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
            "no_pie_run": bool(metadata.get("no_pie_run", True)),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
            "stop_before_editor_or_pie": bool(metadata.get("stop_before_editor_or_pie", True)),
        }
        filtered_bridge_ping_receipt = {
            str(key): value
            for key, value in bridge_ping_receipt.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "bridge_ping_receipt" and filtered_bridge_ping_receipt:
            context["bridge_ping_receipt"] = filtered_bridge_ping_receipt
        provider_config_review = {
            "schema": metadata.get("schema", ""),
            "receipt_state": metadata.get("receipt_state", ""),
            "receipt_exists": bool(metadata.get("receipt_exists", False)),
            "receipt_path": metadata.get("receipt_path", ""),
            "required_command": metadata.get("required_command", ""),
            "operator_command_handoff": (
                list(metadata.get("operator_command_handoff", []))[:1]
                if isinstance(metadata.get("operator_command_handoff"), list)
                else []
            ),
            "provider": metadata.get("provider", ""),
            "animation_provider": metadata.get("animation_provider", ""),
            "provider_api_key_configured": bool(metadata.get("provider_api_key_configured", False)),
            "animation_provider_api_key_configured": bool(metadata.get("animation_provider_api_key_configured", False)),
            "provider_api_key_source": metadata.get("provider_api_key_source", ""),
            "animation_provider_api_key_source": metadata.get("animation_provider_api_key_source", ""),
            "provider_secrets_gitignored": bool(metadata.get("provider_secrets_gitignored", False)),
            "provider_settings_gitignored": bool(metadata.get("provider_settings_gitignored", False)),
            "secret_contract_schema": metadata.get("secret_contract_schema", ""),
            "masked_status_only": bool(metadata.get("masked_status_only", True)),
            "raw_key_returned": bool(metadata.get("raw_key_returned", False)),
            "save_tool": metadata.get("save_tool", ""),
            "proof_tool": metadata.get("proof_tool", ""),
            "no_raw_key": bool(metadata.get("no_raw_key", True)),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
            "no_wallet_check": bool(metadata.get("no_wallet_check", True)),
            "no_credit_reservation": bool(metadata.get("no_credit_reservation", True)),
            "no_spend_confirmation": bool(metadata.get("no_spend_confirmation", True)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
        }
        filtered_provider_config_review = {
            str(key): value
            for key, value in provider_config_review.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "provider_config_review" and filtered_provider_config_review:
            context["provider_config_review"] = filtered_provider_config_review
        chat_cockpit_start_receipt = {
            "schema": metadata.get("schema", ""),
            "chat_ready": bool(metadata.get("chat_ready", False)),
            "chat_tcp_ready": bool(metadata.get("chat_tcp_ready", False)),
            "chat_base_url": metadata.get("chat_base_url", ""),
            "chat_health_endpoint": metadata.get("chat_health_endpoint", ""),
            "startup_script": metadata.get("startup_script", ""),
            "startup_receipt_path": metadata.get("startup_receipt_path", ""),
            "startup_command": metadata.get("startup_command", ""),
            "manual_startup_command": metadata.get("manual_startup_command", ""),
            "proof_command": metadata.get("proof_command", ""),
            "proof_expected": metadata.get("proof_expected", ""),
            "repair_state": metadata.get("repair_state", ""),
            "no_process_start": bool(metadata.get("no_process_start", True)),
            "no_port_kill": bool(metadata.get("no_port_kill", True)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
        }
        filtered_chat_cockpit_start_receipt = {
            str(key): value
            for key, value in chat_cockpit_start_receipt.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "chat_cockpit_start_receipt" and filtered_chat_cockpit_start_receipt:
            context["chat_cockpit_start_receipt"] = filtered_chat_cockpit_start_receipt
        platform_stability_review = {
            "schema": metadata.get("schema", ""),
            "receipt_state": metadata.get("receipt_state", ""),
            "receipt_exists": bool(metadata.get("receipt_exists", False)),
            "receipt_path": metadata.get("receipt_path", ""),
            "required_command": metadata.get("required_command", ""),
            "ready_for_platform_stability": bool(metadata.get("ready_for_platform_stability", False)),
            "ready_for_wip_promotion": bool(metadata.get("ready_for_wip_promotion", False)),
            "platform_missing_gate_count": int(metadata.get("platform_missing_gate_count", 0) or 0),
            "wip_promotion_missing_gate_count": int(metadata.get("wip_promotion_missing_gate_count", 0) or 0),
            "blocking_gate_count": int(metadata.get("blocking_gate_count", 0) or 0),
            "blocking_gate_preview": bounded_string_preview(metadata.get("blocking_gate_preview", []), 12),
            "readiness_repair_action_count": int(metadata.get("readiness_repair_action_count", 0) or 0),
            "readiness_repair_recommended_next": metadata.get("readiness_repair_recommended_next", ""),
            "readiness_repair_next_gate": metadata.get("readiness_repair_next_gate", ""),
            "readiness_repair_next_policy_area": metadata.get("readiness_repair_next_policy_area", ""),
            "readiness_repair_next_tool": metadata.get("readiness_repair_next_tool", ""),
            "readiness_repair_next_requires_bridge": bool(metadata.get("readiness_repair_next_requires_bridge", False)),
            "readiness_repair_next_requires_network": bool(metadata.get("readiness_repair_next_requires_network", False)),
            "readiness_repair_next_requires_spend": bool(metadata.get("readiness_repair_next_requires_spend", False)),
            "readiness_repair_action_preview": [
                item for item in metadata.get("readiness_repair_action_preview", [])[:8] if isinstance(item, dict)
            ] if isinstance(metadata.get("readiness_repair_action_preview"), list) else [],
            "dirty_promotion_review_receipt_state": metadata.get("dirty_promotion_review_receipt_state", ""),
            "dirty_promotion_review_receipt_current": bool(metadata.get("dirty_promotion_review_receipt_current", False)),
            "dirty_promotion_review_receipt_stale": bool(metadata.get("dirty_promotion_review_receipt_stale", False)),
            "dirty_promotion_review_receipt_signature_match": bool(metadata.get("dirty_promotion_review_receipt_signature_match", False)),
            "dirty_signature_algorithm": metadata.get("dirty_signature_algorithm", ""),
            "dirty_signature_entry_count": int(metadata.get("dirty_signature_entry_count", 0) or 0),
            "dirty_promotion_review_batch_count": int(metadata.get("dirty_promotion_review_batch_count", 0) or 0),
            "dirty_promotion_evidence_unresolved_count": int(metadata.get("dirty_promotion_evidence_unresolved_count", 0) or 0),
            "dirty_target_review_group": metadata.get("dirty_target_review_group", ""),
            "dirty_target_review_order": int(metadata.get("dirty_target_review_order", 0) or 0),
            "dirty_target_review_scope": metadata.get("dirty_target_review_scope", ""),
            "dirty_target_review_tracked_count": int(metadata.get("dirty_target_review_tracked_count", 0) or 0),
            "dirty_target_review_untracked_count": int(metadata.get("dirty_target_review_untracked_count", 0) or 0),
            "dirty_target_review_status": metadata.get("dirty_target_review_status") or "missing_evidence",
            "dirty_target_review_evidence_complete": bool(metadata.get("dirty_target_review_evidence_complete", False)),
            "dirty_target_review_recorded_evidence_count": int(metadata.get("dirty_target_review_recorded_evidence_count", 0) or 0),
            "dirty_target_review_recorded_evidence_preview": bounded_string_preview(metadata.get("dirty_target_review_recorded_evidence_preview", []), 8),
            "dirty_target_review_human_approval_recorded": bool(metadata.get("dirty_target_review_human_approval_recorded", False)),
            "dirty_target_review_missing_evidence_count": int(metadata.get("dirty_target_review_missing_evidence_count", 0) or 0),
            "dirty_target_review_missing_evidence_preview": bounded_string_preview(metadata.get("dirty_target_review_missing_evidence_preview", []), 8),
            "dirty_target_review_required_evidence_preview": bounded_string_preview(metadata.get("dirty_target_review_required_evidence_preview", []), 8),
            "dirty_target_review_decision_prompt_preview": bounded_string_preview(metadata.get("dirty_target_review_decision_prompt_preview", []), 8),
            "dirty_target_review_receipt_command_template": metadata.get("dirty_target_review_receipt_command_template", ""),
            "dirty_target_review_approval_receipt_command_template": metadata.get("dirty_target_review_approval_receipt_command_template", ""),
            "dirty_target_review_receipt_command_policy": metadata.get("dirty_target_review_receipt_command_policy", ""),
            "dirty_target_review_operator_command_handoff": (
                list(metadata.get("dirty_target_review_operator_command_handoff", []))[:2]
                if isinstance(metadata.get("dirty_target_review_operator_command_handoff"), list)
                else []
            ),
            "dirty_target_review_focused_test_command_count": int(metadata.get("dirty_target_review_focused_test_command_count", 0) or 0),
            "dirty_target_review_focused_test_command_preview": bounded_string_preview(metadata.get("dirty_target_review_focused_test_command_preview", []), 5),
            "dirty_target_review_sample_preview": bounded_string_preview(metadata.get("dirty_target_review_sample_preview", []), 5),
            "dirty_target_review_promotion_allowed_after_receipt": bool(metadata.get("dirty_target_review_promotion_allowed_after_receipt", False)),
            "dirty_target_review_merge_policy": str(metadata.get("dirty_target_review_merge_policy", "")),
            "dirty_target_review_previous_evidence_merged": bool(metadata.get("dirty_target_review_previous_evidence_merged", False)),
            "dirty_target_review_reset_evidence": bool(metadata.get("dirty_target_review_reset_evidence", False)),
            "tool_registry_reproducible": bool(metadata.get("tool_registry_reproducible", False)),
            "tool_count": int(metadata.get("tool_count", 0) or 0),
            "recorded_tool_count": int(metadata.get("recorded_tool_count", 0) or 0),
            "partial_tool_count": int(metadata.get("partial_tool_count", 0) or 0),
            "test_lane_state": metadata.get("test_lane_state", ""),
            "paid_provider_smoke_contract_ok": bool(metadata.get("paid_provider_smoke_contract_ok", False)),
            "paid_provider_smoke_manual_command": metadata.get("paid_provider_smoke_manual_command", ""),
            "paid_provider_smoke_required_env_vars": bounded_string_preview(metadata.get("paid_provider_smoke_required_env_vars", []), 5),
            "paid_provider_smoke_no_spend_tools": bounded_string_preview(metadata.get("paid_provider_smoke_no_spend_tools", []), 5),
            "paid_provider_smoke_manual_spend_required": bool(metadata.get("paid_provider_smoke_manual_spend_required", False)),
            "paid_provider_smoke_no_task_submission": bool(metadata.get("paid_provider_smoke_no_task_submission", True)),
            "paid_provider_smoke_no_download": bool(metadata.get("paid_provider_smoke_no_download", True)),
            "paid_provider_smoke_no_import": bool(metadata.get("paid_provider_smoke_no_import", True)),
            "paid_generation_evidence_receipt_state": metadata.get("paid_generation_evidence_receipt_state", ""),
            "paid_generation_evidence_receipt_path": metadata.get("paid_generation_evidence_receipt_path", ""),
            "paid_generation_evidence_required_command": metadata.get("paid_generation_evidence_required_command", ""),
            "paid_generation_wallet_evidence_recorded": bool(metadata.get("paid_generation_wallet_evidence_recorded", False)),
            "paid_generation_mesh_wallet_evidence_recorded": bool(metadata.get("paid_generation_mesh_wallet_evidence_recorded", False)),
            "paid_generation_animation_allowance_evidence_recorded": bool(metadata.get("paid_generation_animation_allowance_evidence_recorded", False)),
            "paid_generation_spend_confirmation_recorded": bool(metadata.get("paid_generation_spend_confirmation_recorded", False)),
            "paid_generation_explicit_spend_approval_recorded": bool(metadata.get("paid_generation_explicit_spend_approval_recorded", False)),
            "paid_generation_explicit_usage_approval_recorded": bool(metadata.get("paid_generation_explicit_usage_approval_recorded", False)),
            "paid_generation_estimated_spend_reviewed": bool(metadata.get("paid_generation_estimated_spend_reviewed", False)),
            "paid_generation_estimated_motion_seconds_reviewed": bool(metadata.get("paid_generation_estimated_motion_seconds_reviewed", False)),
            "paid_generation_mesh_provider": metadata.get("paid_generation_mesh_provider", ""),
            "paid_generation_animation_provider": metadata.get("paid_generation_animation_provider", ""),
            "paid_generation_operator_command_handoff": (
                list(metadata.get("paid_generation_operator_command_handoff", []))[:3]
                if isinstance(metadata.get("paid_generation_operator_command_handoff"), list)
                else []
            ),
            "blueprint_mutation_evidence_receipt_state": metadata.get("blueprint_mutation_evidence_receipt_state", ""),
            "blueprint_mutation_evidence_receipt_status": metadata.get("blueprint_mutation_evidence_receipt_status", ""),
            "blueprint_mutation_evidence_receipt_path": metadata.get("blueprint_mutation_evidence_receipt_path", ""),
            "blueprint_mutation_evidence_required_command": metadata.get("blueprint_mutation_evidence_required_command", ""),
            "blueprint_mutation_operator_command_handoff": (
                list(metadata.get("blueprint_mutation_operator_command_handoff", []))[:3]
                if isinstance(metadata.get("blueprint_mutation_operator_command_handoff"), list)
                else []
            ),
            "blueprint_mutation_pre_read_evidence_recorded": bool(metadata.get("blueprint_mutation_pre_read_evidence_recorded", False)),
            "blueprint_mutation_compile_plan_recorded": bool(metadata.get("blueprint_mutation_compile_plan_recorded", False)),
            "blueprint_mutation_readback_plan_recorded": bool(metadata.get("blueprint_mutation_readback_plan_recorded", False)),
            "blueprint_mutation_target_blueprint_path": metadata.get("blueprint_mutation_target_blueprint_path", ""),
            "blueprint_mutation_intended_summary": metadata.get("blueprint_mutation_intended_summary", ""),
            "blueprint_mutation_evidence_required_preview": bounded_string_preview(metadata.get("blueprint_mutation_evidence_required_preview", []), 8),
            "blueprint_mutation_evidence_merge_policy": metadata.get("blueprint_mutation_evidence_merge_policy", ""),
            "blueprint_mutation_human_approval_required": bool(metadata.get("blueprint_mutation_human_approval_required", True)),
            "blueprint_mutation_evidence_no_editor_mutation": bool(metadata.get("blueprint_mutation_evidence_no_editor_mutation", True)),
            "blueprint_mutation_evidence_no_blueprint_mutation": bool(metadata.get("blueprint_mutation_evidence_no_blueprint_mutation", True)),
            "blueprint_mutation_evidence_no_compile": bool(metadata.get("blueprint_mutation_evidence_no_compile", True)),
            "blueprint_mutation_evidence_no_save": bool(metadata.get("blueprint_mutation_evidence_no_save", True)),
            "blueprint_mutation_evidence_no_pie": bool(metadata.get("blueprint_mutation_evidence_no_pie", True)),
            "no_mutation_test_ok": bool(metadata.get("no_mutation_test_ok", False)),
            "no_mutation_test_status": metadata.get("no_mutation_test_status", ""),
            "no_mutation_test_mutation_count": int(metadata.get("no_mutation_test_mutation_count", 0) or 0),
            "no_mutation_test_exit_code": int(metadata.get("no_mutation_test_exit_code", 0) or 0),
            "no_mutation_test_tracked_file_count": int(metadata.get("no_mutation_test_tracked_file_count", 0) or 0),
            "no_mutation_test_snapshot_digest_match": bool(metadata.get("no_mutation_test_snapshot_digest_match", False)),
            "no_mutation_test_snapshot_scope": metadata.get("no_mutation_test_snapshot_scope", ""),
            "no_mutation_test_snapshot_hash_algorithm": metadata.get("no_mutation_test_snapshot_hash_algorithm", ""),
            "no_mutation_test_operator_command_handoff": (
                list(metadata.get("no_mutation_test_operator_command_handoff", []))[:1]
                if isinstance(metadata.get("no_mutation_test_operator_command_handoff"), list)
                else []
            ),
            "high_value_wrapper_ok": bool(metadata.get("high_value_wrapper_ok", False)),
            "build_wrapper_status": metadata.get("build_wrapper_status", ""),
            "last_plugin_build_status": metadata.get("last_plugin_build_status", ""),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
        }
        filtered_platform_stability_review = {
            str(key): value
            for key, value in platform_stability_review.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "platform_stability_review" and filtered_platform_stability_review:
            context["platform_stability_review"] = filtered_platform_stability_review
        runtime_verification = {
            "target_phase": metadata.get("target_phase", ""),
            "state": metadata.get("state", ""),
            "can_verify_now": bool(metadata.get("can_verify_now", False)),
            "bridge_blocked": bool(metadata.get("bridge_blocked", False)),
            "pie_validation_count": int(metadata.get("pie_validation_count", 0) or 0),
            "compile_check_count": int(metadata.get("compile_check_count", 0) or 0),
            "evidence_requirement_count": int(metadata.get("evidence_requirement_count", 0) or 0),
            "runtime_evidence_event_count": int(metadata.get("runtime_evidence_event_count", 0) or 0),
            "runtime_proof_contract_schema": metadata.get("runtime_proof_contract_schema", ""),
            "runtime_proof_mode": metadata.get("runtime_proof_mode", ""),
            "runtime_proof_required_count": int(metadata.get("runtime_proof_required_count", 0) or 0),
            "runtime_proof_required_before_count": int(metadata.get("runtime_proof_required_before_count", 0) or 0),
            "runtime_proof_required_before_preview": bounded_string_preview(metadata.get("runtime_proof_required_before_preview", []), 8),
            "runtime_proof_required_preview": bounded_string_preview(metadata.get("runtime_proof_required_preview", []), 8),
            "runtime_proof_tool_preview": bounded_string_preview(metadata.get("runtime_proof_tool_preview", []), 8),
            "runtime_proof_stop_preview": bounded_string_preview(metadata.get("runtime_proof_stop_preview", []), 5),
            "runtime_probe_allowed": bool(metadata.get("runtime_probe_allowed", False)),
            "requires_successful_bridge_ping_before_runtime_probe": bool(metadata.get("requires_successful_bridge_ping_before_runtime_probe", True)),
            "blocked_item_count": int(metadata.get("blocked_item_count", 0) or 0),
            "pending_item_count": int(metadata.get("pending_item_count", 0) or 0),
            "recorded_item_count": int(metadata.get("recorded_item_count", 0) or 0),
            "runtime_proof_preview": bounded_string_preview(metadata.get("runtime_proof_preview", []), 5),
            "compile_check_preview": bounded_string_preview(metadata.get("compile_check_preview", []), 4),
            "no_pie_run": bool(metadata.get("no_pie_run", True)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
        }
        filtered_runtime = {
            str(key): value
            for key, value in runtime_verification.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "runtime_verification" and filtered_runtime:
            context["runtime_verification"] = filtered_runtime
        queued_action = {
            "queue_path": metadata.get("queue_path", ""),
            "queue_name": metadata.get("queue_name", ""),
            "target_phase": metadata.get("target_phase", ""),
            "next_action_id": metadata.get("next_action_id", ""),
            "next_action_tool": metadata.get("next_action_tool", ""),
            "next_action_label": metadata.get("next_action_label", ""),
            "feature_template_schema": metadata.get("feature_template_schema", ""),
            "feature_template_name": metadata.get("feature_template_name", ""),
            "feature_template_display_name": metadata.get("feature_template_display_name", ""),
            "feature_template_operation_count": int(metadata.get("feature_template_operation_count", 0) or 0),
            "feature_template_next_operation_id": metadata.get("feature_template_next_operation_id", ""),
            "feature_template_next_operation_type": metadata.get("feature_template_next_operation_type", ""),
            "feature_template_next_operation_summary": metadata.get("feature_template_next_operation_summary", ""),
            "feature_template_next_operation_tool_preview": bounded_string_preview(
                metadata.get("feature_template_next_operation_tool_preview", []),
                8,
            ),
            "feature_template_next_operation_required_before_preview": bounded_string_preview(
                metadata.get("feature_template_next_operation_required_before_preview", []),
                8,
            ),
            "feature_template_next_operation_required_after_preview": bounded_string_preview(
                metadata.get("feature_template_next_operation_required_after_preview", []),
                8,
            ),
            "feature_template_next_operation_stop_if_missing_preview": bounded_string_preview(
                metadata.get("feature_template_next_operation_stop_if_missing_preview", []),
                8,
            ),
            "action_count": int(metadata.get("action_count", 0) or 0),
            "preview_action_count": int(metadata.get("preview_action_count", 0) or 0),
            "argument_keys": bounded_string_preview(metadata.get("argument_keys", []), 8),
            "bridge_blocked": bool(metadata.get("bridge_blocked", False)),
            "can_execute_now": bool(metadata.get("can_execute_now", False)),
            "requires_successful_bridge_ping_before_execution": bool(metadata.get("requires_successful_bridge_ping_before_execution", True)),
            "no_auto_execute": bool(metadata.get("no_auto_execute", True)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
            "no_pie_run": bool(metadata.get("no_pie_run", True)),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
            "evidence_preview": bounded_string_preview(metadata.get("evidence_preview", []), 5),
        }
        filtered_queue = {
            str(key): value
            for key, value in queued_action.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "editor_queue" and filtered_queue:
            context["queued_action"] = filtered_queue
        feature_completion_contract = {
            "schema": metadata.get("completion_contract_schema", ""),
            "template_name": metadata.get("template_name", ""),
            "display_name": metadata.get("display_name", ""),
            "proof_gate_count": int(metadata.get("completion_proof_gate_count", 0) or 0),
            "required_evidence_count": int(metadata.get("completion_required_evidence_count", 0) or 0),
            "stop_condition_count": int(metadata.get("completion_stop_condition_count", 0) or 0),
            "proof_gate_preview": bounded_string_preview(metadata.get("completion_proof_gate_preview", []), 8),
            "required_evidence_preview": bounded_string_preview(metadata.get("completion_required_evidence_preview", []), 8),
            "stop_before_complete_preview": bounded_string_preview(metadata.get("completion_stop_before_complete_preview", []), 8),
            "record_tool": metadata.get("record_tool", ""),
            "completion_allowed": bool(metadata.get("completion_allowed", False)),
            "requires_all_proof_gates_before_complete": bool(metadata.get("requires_all_proof_gates_before_complete", True)),
            "requires_all_required_evidence_before_complete": bool(metadata.get("requires_all_required_evidence_before_complete", True)),
            "stop_before_complete_required": bool(metadata.get("stop_before_complete_required", True)),
            "no_auto_complete": bool(metadata.get("no_auto_complete", True)),
            "no_editor_mutation": bool(metadata.get("no_editor_mutation", True)),
            "no_pie_run": bool(metadata.get("no_pie_run", True)),
            "no_provider_call": bool(metadata.get("no_provider_call", True)),
            "no_git_mutation": bool(metadata.get("no_git_mutation", True)),
        }
        filtered_completion_contract = {
            str(key): value
            for key, value in feature_completion_contract.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
        if evidence_type == "feature_completion_contract" and filtered_completion_contract:
            context["feature_completion_contract"] = filtered_completion_contract
    return context


def evidence_review_context(
    evidence_recording: Dict[str, Any],
    target_evidence_item: Dict[str, Any],
) -> Dict[str, Any]:
    item_count = int(evidence_recording.get("item_count", 0) or 0)
    if not item_count:
        return {}
    target_context = evidence_target_context(target_evidence_item) if target_evidence_item else {}
    return {
        "state": "blocked" if int(evidence_recording.get("blocked_count", 0) or 0) else "ready",
        "session_name": str(evidence_recording.get("session_name", "")),
        "target_phase": str(evidence_recording.get("target_phase", "")),
        "item_count": item_count,
        "pending_count": int(evidence_recording.get("pending_count", 0) or 0),
        "blocked_count": int(evidence_recording.get("blocked_count", 0) or 0),
        "recorded_count": int(evidence_recording.get("recorded_count", 0) or 0),
        "record_tool": str(evidence_recording.get("record_tool", "skill_record_ide_companion_evidence")),
        "target_evidence": target_context,
        "target_evidence_id": str(target_evidence_item.get("id", "")) if target_evidence_item else "",
        "target_evidence_type": str(target_evidence_item.get("evidence_type", "")) if target_evidence_item else "",
        "target_artifact_count": int(target_context.get("artifact_count", 0) or 0),
        "target_artifact_preview": target_context.get("artifact_preview", []) if isinstance(target_context.get("artifact_preview"), list) else [],
        "requires_bridge": bool(evidence_recording.get("unreal_editor_required", False)),
        "network_required": bool(evidence_recording.get("network_required", False)),
        "spend_required": bool(evidence_recording.get("spend_required", False)),
        "review_tool": "chat_get_cockpit_overview",
        "stop_before_ledger_write": True,
    }


def select_execute_context(next_queue: Dict[str, Any]) -> Dict[str, Any]:
    preview_actions = next_queue.get("preview_actions") if isinstance(next_queue.get("preview_actions"), list) else []
    next_action = preview_actions[0] if preview_actions and isinstance(preview_actions[0], dict) else {}
    action_id = str(next_queue.get("next_action_id") or next_action.get("id", ""))
    action_tool = str(next_queue.get("next_action_tool") or next_action.get("tool", ""))
    if not action_id and not action_tool:
        return {}
    return {
        "action_id": action_id,
        "tool": action_tool,
        "label": str(next_action.get("label") or action_id or action_tool),
        "queue_path": str(next_queue.get("queue_path", "")),
        "queue_name": str(next_queue.get("queue_name", "")),
        "target_phase": str(next_queue.get("target_phase", "")),
        "argument_keys": next_action.get("argument_keys", []) if isinstance(next_action.get("argument_keys"), list) else [],
        "requires_bridge": bool(next_queue.get("bridge_required", True)),
        "can_execute_now": bool(next_queue.get("can_execute_now", False)),
        "bridge_blocked": bool(next_queue.get("bridge_blocked", False)),
    }


def queue_review_context(
    queues: List[Dict[str, Any]],
    next_queue: Dict[str, Any],
    *,
    work_order_template: Dict[str, Any] | None = None,
    generated_animation_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if not queues:
        return {}
    selected = next_queue if next_queue else queues[0]
    preview_actions = selected.get("preview_actions") if isinstance(selected.get("preview_actions"), list) else []
    next_action = preview_actions[0] if preview_actions and isinstance(preview_actions[0], dict) else {}
    blocking_gates = selected.get("blocking_gates") if isinstance(selected.get("blocking_gates"), list) else []
    return {
        "state": "ready" if any(queue.get("can_execute_now") for queue in queues) else "blocked",
        "queue_count": len(queues),
        "queued_action_count": sum(int(queue.get("action_count", 0) or 0) for queue in queues),
        "executable_queue_count": sum(1 for queue in queues if queue.get("can_execute_now")),
        "blocked_queue_count": sum(1 for queue in queues if not queue.get("can_execute_now")),
        "bridge_blocked_count": sum(1 for queue in queues if queue.get("bridge_blocked")),
        "queue_name": str(selected.get("queue_name", "")),
        "queue_path": str(selected.get("queue_path", "")),
        "target_phase": str(selected.get("target_phase", "")),
        "action_count": int(selected.get("action_count", 0) or 0),
        "preview_action_count": len(preview_actions),
        "evidence_count": int(selected.get("evidence_count", 0) or 0),
        "next_action_id": str(selected.get("next_action_id") or next_action.get("id", "")),
        "next_action_tool": str(selected.get("next_action_tool") or next_action.get("tool", "")),
        "next_action_label": str(next_action.get("label") or selected.get("next_action_id", "")),
        "blocking_gate_count": len(blocking_gates),
        "blocking_gate_preview": bounded_string_preview(blocking_gates, 6),
        "requires_bridge": bool(selected.get("bridge_required", False)),
        "bridge_blocked": bool(selected.get("bridge_blocked", False)),
        "can_execute_now": bool(selected.get("can_execute_now", False)),
        **generated_asset_replacement_operation_gate_context(work_order_template or {}),
        **generated_animation_operation_gate_context(generated_animation_context or {}),
        "review_tool": "chat_get_cockpit_overview",
        "execute_tool": str(selected.get("next_action_tool", "")),
        "stop_before_editor_mutation": True,
    }


def execution_review_context(execution_review: Dict[str, Any]) -> Dict[str, Any]:
    target_action = execution_review.get("target_action") if isinstance(execution_review.get("target_action"), dict) else {}
    return {
        "state": str(execution_review.get("state", "")),
        "can_execute_now": bool(execution_review.get("can_execute_now", False)),
        "action_id": str(target_action.get("action_id", "")),
        "tool": str(target_action.get("tool", "")),
        "label": str(target_action.get("label", "")),
        "queue_path": str(target_action.get("queue_path", "")),
        "queue_name": str(target_action.get("queue_name", "")),
        "target_phase": str(target_action.get("target_phase", "")),
        "requires_bridge": bool(execution_review.get("requires_bridge", False)),
        "missing_gate_count": int(execution_review.get("missing_gate_count", 0) or 0),
        "missing_gates": bounded_string_preview(execution_review.get("missing_gates", []), 6),
        "after_execution_evidence_count": int(execution_review.get("after_execution_evidence_count", 0) or 0),
        "after_execution_evidence_preview": bounded_string_preview(execution_review.get("after_execution_evidence_preview", []), 5),
        "policy_preview": bounded_string_preview(execution_review.get("policy_preview", []), 5),
        "pre_execution_checklist": bounded_string_preview(execution_review.get("pre_execution_checklist", []), 5),
        "post_execution_evidence_required": bounded_string_preview(execution_review.get("post_execution_evidence_required", []), 5),
        "generated_asset_replacement_operation_count": int(execution_review.get("generated_asset_replacement_operation_count", 0) or 0),
        "generated_asset_replacement_operation_preview": bounded_string_preview(execution_review.get("generated_asset_replacement_operation_preview", []), 5),
        "generated_asset_replacement_tool_preview": bounded_string_preview(execution_review.get("generated_asset_replacement_tool_preview", []), 8),
        "generated_asset_replacement_proof_contract_count": int(execution_review.get("generated_asset_replacement_proof_contract_count", 0) or 0),
        "generated_asset_replacement_gate_policy": bounded_string_preview(execution_review.get("generated_asset_replacement_gate_policy", []), 5),
        "generated_animation_prompt_count": int(execution_review.get("generated_animation_prompt_count", 0) or 0),
        "generated_animation_prompt_preview": bounded_string_preview(execution_review.get("generated_animation_prompt_preview", []), 5),
        "generated_animation_provider_preview": bounded_string_preview(execution_review.get("generated_animation_provider_preview", []), 5),
        "generated_animation_target_skeleton_preview": bounded_string_preview(execution_review.get("generated_animation_target_skeleton_preview", []), 5),
        "generated_animation_tool_preview": bounded_string_preview(execution_review.get("generated_animation_tool_preview", []), 8),
        "generated_animation_proof_required_preview": bounded_string_preview(execution_review.get("generated_animation_proof_required_preview", []), 8),
        "generated_animation_prompt_gate_policy": bounded_string_preview(execution_review.get("generated_animation_prompt_gate_policy", []), 5),
        "estimated_uthana_motion_seconds": int(execution_review.get("estimated_uthana_motion_seconds", 0) or 0),
        "generated_animation_asset_count": int(execution_review.get("generated_animation_asset_count", 0) or 0),
        "generated_animation_pending_count": int(execution_review.get("generated_animation_pending_count", 0) or 0),
        "generated_animation_target_name": str(execution_review.get("generated_animation_target_name", "")),
        "generated_animation_target_provider": str(execution_review.get("generated_animation_target_provider", "")),
        "generated_animation_target_task_status": str(execution_review.get("generated_animation_target_task_status", "")),
        "generated_animation_target_motion_id": str(execution_review.get("generated_animation_target_motion_id", "")),
        "generated_animation_target_skeleton": str(execution_review.get("generated_animation_target_skeleton", "")),
        "generated_animation_quality_proof_contract_schema": str(execution_review.get("generated_animation_quality_proof_contract_schema", "")),
        "generated_animation_quality_evidence_missing_count": int(execution_review.get("generated_animation_quality_evidence_missing_count", 0) or 0),
        "generated_animation_missing_stage_preview": bounded_string_preview(execution_review.get("generated_animation_missing_stage_preview", []), 8),
        "generated_animation_next_safe_action_id": str(execution_review.get("generated_animation_next_safe_action_id", "")),
        "generated_animation_next_safe_tool": str(execution_review.get("generated_animation_next_safe_tool", "")),
        "generated_animation_usage_contract_schema": str(execution_review.get("generated_animation_usage_contract_schema", "")),
        "generated_animation_usage_receipt_path": str(execution_review.get("generated_animation_usage_receipt_path", "")),
        "generated_animation_usage_confirmation_field": str(execution_review.get("generated_animation_usage_confirmation_field", "")),
        "generated_animation_allowance_tool_preview": bounded_string_preview(execution_review.get("generated_animation_allowance_tool_preview", []), 4),
        "generated_animation_allowance_review_steps": bounded_string_preview(execution_review.get("generated_animation_allowance_review_steps", []), 5),
        "generated_animation_gate_policy": bounded_string_preview(execution_review.get("generated_animation_gate_policy", []), 5),
        "executor_contract": bounded_string_preview(execution_review.get("executor_contract", []), 5),
        "stop_after_action": bool(execution_review.get("stop_after_action", True)),
    }


def repair_review_context(repair_review: Dict[str, Any]) -> Dict[str, Any]:
    target_repair = repair_review.get("target_repair") if isinstance(repair_review.get("target_repair"), dict) else {}
    repair_readiness = (
        repair_review.get("repair_execution_readiness")
        if isinstance(repair_review.get("repair_execution_readiness"), dict)
        else {}
    )
    return {
        "state": str(repair_review.get("state", "")),
        "target_repair_id": str(target_repair.get("id", "")),
        "label": str(target_repair.get("label", "")),
        "target_phase": str(target_repair.get("target_phase", "")),
        "requires_bridge": bool(repair_review.get("requires_bridge", False)),
        "bridge_blocked": bool(repair_review.get("bridge_blocked", False)),
        "failure_signal_count": int(repair_review.get("failure_signal_count", 0) or 0),
        "blocked_count": int(repair_review.get("blocked_count", 0) or 0),
        "needs_repair_count": int(repair_review.get("needs_repair_count", 0) or 0),
        "repair_instruction_count": int(repair_review.get("repair_instruction_count", 0) or 0),
        "stop_condition_count": int(repair_review.get("stop_condition_count", 0) or 0),
        "compile_check_preview": bounded_string_preview(repair_review.get("compile_check_preview", []), 4),
        "evidence_preview": bounded_string_preview(repair_review.get("evidence_preview", []), 5),
        "policy_preview": bounded_string_preview(repair_review.get("policy_preview", []), 5),
        "repair_execution_readiness": {
            "schema": str(repair_readiness.get("schema", "unreal_mcp_chat_repair_execution_readiness.v1")),
            "state": str(repair_readiness.get("state", "")),
            "can_compile_repair_work_order": bool(repair_readiness.get("can_compile_repair_work_order", False)),
            "can_apply_repair_now": bool(repair_readiness.get("can_apply_repair_now", False)),
            "can_record_repair_evidence": bool(repair_readiness.get("can_record_repair_evidence", False)),
            "target_repair_id": str(repair_readiness.get("target_repair_id", "")),
            "target_phase": str(repair_readiness.get("target_phase", "")),
            "requires_bridge_before_apply": bool(repair_readiness.get("requires_bridge_before_apply", False)),
            "bridge_blocked": bool(repair_readiness.get("bridge_blocked", False)),
            "missing_gate_preview": bounded_string_preview(repair_readiness.get("missing_gate_preview", []), 5),
            "required_before_plan_preview": bounded_string_preview(repair_readiness.get("required_before_plan_preview", []), 5),
            "required_before_apply_preview": bounded_string_preview(repair_readiness.get("required_before_apply_preview", []), 5),
            "required_after_apply_preview": bounded_string_preview(repair_readiness.get("required_after_apply_preview", []), 5),
            "stop_if_missing_preview": bounded_string_preview(repair_readiness.get("stop_if_missing_preview", []), 5),
            "recommended_next": str(repair_readiness.get("recommended_next", "")),
            "planning_tool": str(repair_readiness.get("planning_tool", "")),
            "evidence_tool": str(repair_readiness.get("evidence_tool", "")),
            "no_editor_mutation": bool(repair_readiness.get("no_editor_mutation", True)),
            "stop_before_editor_mutation": bool(repair_readiness.get("stop_before_editor_mutation", True)),
        },
        "repair_execution_readiness_state": str(repair_review.get("repair_execution_readiness_state", "")),
        "can_compile_repair_work_order": bool(repair_review.get("can_compile_repair_work_order", False)),
        "can_apply_repair_now": bool(repair_review.get("can_apply_repair_now", False)),
        "repair_recommended_next": str(repair_review.get("repair_recommended_next", "")),
        "recommended_tool": str(repair_review.get("recommended_tool", "")),
        "evidence_tool": str(repair_review.get("evidence_tool", "")),
        "stop_after_repair_attempt": bool(repair_review.get("stop_after_repair_attempt", True)),
    }


def runtime_review_context(runtime_review: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "state": str(runtime_review.get("state", "")),
        "target_phase": str(runtime_review.get("target_phase", "")),
        "can_verify_now": bool(runtime_review.get("can_verify_now", False)),
        "requires_bridge": bool(runtime_review.get("requires_bridge", False)),
        "bridge_blocked": bool(runtime_review.get("bridge_blocked", False)),
        "pie_validation_count": int(runtime_review.get("pie_validation_count", 0) or 0),
        "compile_check_count": int(runtime_review.get("compile_check_count", 0) or 0),
        "evidence_requirement_count": int(runtime_review.get("evidence_requirement_count", 0) or 0),
        "runtime_proof_contract_schema": str(runtime_review.get("runtime_proof_contract_schema", "")),
        "runtime_proof_mode": str(runtime_review.get("runtime_proof_mode", "")),
        "runtime_proof_required_count": int(runtime_review.get("runtime_proof_required_count", 0) or 0),
        "runtime_proof_required_before_count": int(runtime_review.get("runtime_proof_required_before_count", 0) or 0),
        "runtime_proof_required_before_preview": bounded_string_preview(runtime_review.get("runtime_proof_required_before_preview", []), 8),
        "runtime_proof_required_preview": bounded_string_preview(runtime_review.get("runtime_proof_required_preview", []), 8),
        "runtime_proof_tool_preview": bounded_string_preview(runtime_review.get("runtime_proof_tool_preview", []), 8),
        "runtime_proof_stop_preview": bounded_string_preview(runtime_review.get("runtime_proof_stop_preview", []), 5),
        "runtime_evidence_event_count": int(runtime_review.get("runtime_evidence_event_count", 0) or 0),
        "blocked_item_count": int(runtime_review.get("blocked_item_count", 0) or 0),
        "pending_item_count": int(runtime_review.get("pending_item_count", 0) or 0),
        "recorded_item_count": int(runtime_review.get("recorded_item_count", 0) or 0),
        "compile_check_preview": bounded_string_preview(runtime_review.get("compile_check_preview", []), 4),
        "runtime_proof_preview": bounded_string_preview(runtime_review.get("runtime_proof_preview", []), 5),
        "policy_preview": bounded_string_preview(runtime_review.get("policy_preview", []), 5),
        "review_tool": str(runtime_review.get("review_tool", "chat_get_cockpit_overview")),
        "evidence_tool": str(runtime_review.get("evidence_tool", "skill_record_ide_companion_evidence")),
        "stop_after_runtime_probe": bool(runtime_review.get("stop_after_runtime_probe", True)),
    }


def select_repair_context(repair_loop: Dict[str, Any], target_phase: str) -> Dict[str, Any]:
    items = repair_loop.get("items") if isinstance(repair_loop.get("items"), list) else []
    candidates = [item for item in items if isinstance(item, dict) and str(item.get("label", "")).strip()]
    if not candidates:
        return {}
    selected = candidates[0]
    return {
        "id": str(selected.get("id", "")),
        "kind": str(selected.get("kind", "")),
        "label": str(selected.get("label", "")),
        "state": str(selected.get("state", repair_loop.get("state", ""))),
        "target_phase": target_phase,
        "requires_bridge": bool(selected.get("requires_bridge", True)),
        "recommended_tool": str(repair_loop.get("recommended_tool", "skill_compile_ide_companion_work_order")),
        "evidence_tool": str(repair_loop.get("evidence_tool", "skill_record_ide_companion_evidence")),
        "follow_up": str(selected.get("follow_up", "")),
        "evidence_preview": bounded_string_preview(repair_loop.get("evidence_preview", []), 5),
        "compile_check_preview": bounded_string_preview(repair_loop.get("compile_check_preview", []), 3),
    }


def select_recordable_evidence_item(evidence_recording: Dict[str, Any]) -> Dict[str, Any]:
    items = evidence_recording.get("items") if isinstance(evidence_recording.get("items"), list) else []
    candidates = [item for item in items if isinstance(item, dict)]
    if not candidates:
        return {}

    def evidence_priority(item: Dict[str, Any]) -> tuple[int, str]:
        item_id = str(item.get("id", ""))
        state = str(item.get("state", ""))
        requires_bridge = bool(item.get("requires_bridge", False))
        if state == "pending" and item_id == "record_readiness_repair_queue":
            return (0, item_id)
        if state == "pending" and item_id == "record_dirty_promotion_review":
            return (1, item_id)
        if state == "pending" and item_id == "record_paid_generation_evidence":
            return (2, item_id)
        if state == "pending" and item_id == "record_readiness_policy":
            return (3, item_id)
        if state == "pending" and not requires_bridge:
            return (4, item_id)
        if state == "pending":
            return (5, item_id)
        if state == "blocked" and item_id == "record_readiness_repair_queue":
            return (6, item_id)
        if state == "blocked" and item_id == "record_dirty_promotion_review":
            return (7, item_id)
        if state == "blocked" and item_id == "record_paid_generation_evidence":
            return (8, item_id)
        if state == "blocked" and item_id == "record_readiness_policy":
            return (9, item_id)
        if state == "blocked":
            return (10, item_id)
        return (11, item_id)

    selected = sorted(candidates, key=evidence_priority)[0]
    artifacts = selected.get("required_artifacts") if isinstance(selected.get("required_artifacts"), list) else []
    target = {
        "id": str(selected.get("id", "")),
        "source": str(selected.get("source", "")),
        "phase_name": str(selected.get("phase_name", "")),
        "evidence_type": str(selected.get("evidence_type", "")),
        "label": str(selected.get("label", "")),
        "state": str(selected.get("state", "")),
        "requires_bridge": bool(selected.get("requires_bridge", False)),
        "required_artifacts": bounded_string_preview(artifacts, 5),
        "required_artifact_count": int(selected.get("required_artifact_count", len(artifacts)) or 0),
        "suggested_summary": str(selected.get("suggested_summary", "")),
    }
    metadata = selected.get("metadata") if isinstance(selected.get("metadata"), dict) else {}
    if metadata:
        target["metadata"] = {
            str(key): value
            for key, value in metadata.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
    return target


def select_evidence_item_by_id(evidence_recording: Dict[str, Any], item_id: str) -> Dict[str, Any]:
    items = evidence_recording.get("items") if isinstance(evidence_recording.get("items"), list) else []
    for item in items:
        if isinstance(item, dict) and str(item.get("id", "")) == item_id:
            artifacts = item.get("required_artifacts") if isinstance(item.get("required_artifacts"), list) else []
            target = {
                "id": str(item.get("id", "")),
                "source": str(item.get("source", "")),
                "phase_name": str(item.get("phase_name", "")),
                "evidence_type": str(item.get("evidence_type", "")),
                "label": str(item.get("label", "")),
                "state": str(item.get("state", "")),
                "requires_bridge": bool(item.get("requires_bridge", False)),
                "required_artifacts": bounded_string_preview(artifacts, 10),
                "required_artifact_count": int(item.get("required_artifact_count", len(artifacts)) or 0),
                "suggested_summary": str(item.get("suggested_summary", "")),
            }
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            if metadata:
                target["metadata"] = {
                    str(key): value
                    for key, value in metadata.items()
                    if isinstance(key, str) and value not in ("", None, [], {})
                }
            return target
    return {}


def select_generated_asset_context(generated_asset_quality_gate: Dict[str, Any]) -> Dict[str, Any]:
    items = generated_asset_quality_gate.get("items") if isinstance(generated_asset_quality_gate.get("items"), list) else []
    candidates = [item for item in items if isinstance(item, dict) and str(item.get("id", "")).strip()]
    if not candidates:
        return {}

    def asset_priority(item: Dict[str, Any]) -> tuple[int, str]:
        state = str(item.get("state", ""))
        if state == "provider_pending":
            return (0, str(item.get("id", "")))
        if state == "import_pending":
            return (1, str(item.get("id", "")))
        if state == "quality_pending":
            return (2, str(item.get("id", "")))
        if state == "ready":
            return (3, str(item.get("id", "")))
        return (4, str(item.get("id", "")))

    selected = sorted(candidates, key=asset_priority)[0]
    return {
        "id": str(selected.get("id", "")),
        "name": str(selected.get("name", "")),
        "role": str(selected.get("role", "")),
        "provider": str(selected.get("provider", "")),
        "state": str(selected.get("state", "")),
        "task_status": str(selected.get("task_status", "")),
        "next_gate": str(selected.get("next_gate", "")),
        "manifest_path": str(selected.get("manifest_path", "")),
        "expected_import_path": str(selected.get("expected_import_path", "")),
        "imported_asset_path": str(selected.get("imported_asset_path", "")),
        "has_placeholder": bool(selected.get("has_placeholder", False)),
        "quality_gate_count": int(selected.get("quality_gate_count", 0) or 0),
        "quality_evidence_count": int(selected.get("quality_evidence_count", 0) or 0),
        "quality_gate_preview": bounded_string_preview(selected.get("quality_gate_preview", []), 5),
    }


def generated_asset_review_context(
    generated_asset_quality_gate: Dict[str, Any],
    target_generated_asset_context: Dict[str, Any],
) -> Dict[str, Any]:
    asset_count = int(generated_asset_quality_gate.get("asset_count", 0) or 0)
    if not asset_count:
        return {}
    return {
        "state": str(generated_asset_quality_gate.get("state", "")),
        "asset_count": asset_count,
        "provider_pending_count": int(generated_asset_quality_gate.get("provider_pending_count", 0) or 0),
        "import_pending_count": int(generated_asset_quality_gate.get("import_pending_count", 0) or 0),
        "quality_pending_count": int(generated_asset_quality_gate.get("quality_pending_count", 0) or 0),
        "ready_count": int(generated_asset_quality_gate.get("ready_count", 0) or 0),
        "placeholder_count": int(generated_asset_quality_gate.get("placeholder_count", 0) or 0),
        "target_asset": target_generated_asset_context,
        "review_tool": "chat_get_cockpit_overview",
        "resolve_tool": "skill_compile_ide_companion_asset_lifecycle_manifest",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "stop_before_provider_or_import": True,
    }


def generated_asset_lifecycle_context(
    asset_lifecycles: List[Dict[str, Any]],
    generated_asset_quality_gate: Dict[str, Any],
    target_generated_asset_context: Dict[str, Any],
) -> Dict[str, Any]:
    asset_count = int(generated_asset_quality_gate.get("asset_count", 0) or 0)
    if not asset_lifecycles and not asset_count:
        return {}

    provider_pending_count = int(generated_asset_quality_gate.get("provider_pending_count", 0) or 0)
    import_pending_count = int(generated_asset_quality_gate.get("import_pending_count", 0) or 0)
    quality_pending_count = int(generated_asset_quality_gate.get("quality_pending_count", 0) or 0)
    ready_count = int(generated_asset_quality_gate.get("ready_count", 0) or 0)
    placeholder_count = int(generated_asset_quality_gate.get("placeholder_count", 0) or 0)
    preferred_providers: List[str] = []
    lifecycle_paths: List[str] = []
    manifest_asset_count = 0
    manifest_animation_asset_count = 0
    manifest_animation_pending_count = 0
    manifest_placeholder_count = 0
    manifest_blocked_count = 0
    stop_condition_count = 0
    future_network_required = False
    future_spend_required = False
    for lifecycle in asset_lifecycles:
        if not isinstance(lifecycle, dict):
            continue
        provider = str(lifecycle.get("preferred_provider", "")).strip()
        if provider and provider not in preferred_providers:
            preferred_providers.append(provider)
        manifest_path = str(lifecycle.get("manifest_path", "")).strip()
        if manifest_path:
            lifecycle_paths.append(manifest_path)
        manifest_asset_count += int(lifecycle.get("asset_count", 0) or 0)
        manifest_animation_asset_count += int(lifecycle.get("animation_asset_count", 0) or 0)
        manifest_animation_pending_count += int(lifecycle.get("animation_pending_count", 0) or 0)
        manifest_placeholder_count += int(lifecycle.get("placeholder_count", 0) or 0)
        manifest_blocked_count += int(lifecycle.get("blocked_or_pending_count", 0) or 0)
        stop_condition_count += int(lifecycle.get("stop_condition_count", 0) or 0)
        future_network_required = future_network_required or bool(lifecycle.get("future_provider_network_required", False))
        future_spend_required = future_spend_required or bool(lifecycle.get("future_spend_required", False))

    missing_stages: List[str] = []
    if not asset_lifecycles:
        missing_stages.append("lifecycle_manifest")
    if provider_pending_count:
        missing_stages.append("provider_task_completion")
    if import_pending_count:
        missing_stages.append("download_or_import_result")
    if quality_pending_count:
        missing_stages.append("quality_proof")
    if manifest_animation_pending_count:
        missing_stages.append("animation_motion_generation_or_retarget")
    if placeholder_count or manifest_placeholder_count:
        missing_stages.append("placeholder_mapping")
    if stop_condition_count:
        missing_stages.append("stop_condition_review")

    lifecycle_asset_count = asset_count or manifest_asset_count
    blocked_or_pending_count = provider_pending_count + import_pending_count + quality_pending_count
    if not blocked_or_pending_count and manifest_blocked_count:
        blocked_or_pending_count = manifest_blocked_count
    state = "missing" if not asset_lifecycles else ("ready" if lifecycle_asset_count and ready_count == lifecycle_asset_count else "blocked")
    lifecycle_complete = bool(asset_lifecycles and lifecycle_asset_count and blocked_or_pending_count == 0 and ready_count == lifecycle_asset_count)
    return {
        "schema": "unreal_mcp_chat_generated_asset_lifecycle_gate.v1",
        "state": state,
        "manifest_count": len(asset_lifecycles),
        "asset_count": lifecycle_asset_count,
        "animation_asset_count": manifest_animation_asset_count,
        "animation_pending_count": manifest_animation_pending_count,
        "provider_pending_count": provider_pending_count,
        "import_pending_count": import_pending_count,
        "quality_pending_count": quality_pending_count,
        "ready_count": ready_count,
        "placeholder_count": max(placeholder_count, manifest_placeholder_count),
        "blocked_or_pending_count": blocked_or_pending_count,
        "stop_condition_count": stop_condition_count,
        "preferred_provider_preview": preferred_providers[:5],
        "manifest_path_preview": bounded_string_preview(lifecycle_paths, 5),
        "missing_stage_count": len(missing_stages),
        "missing_stage_preview": missing_stages[:8],
        "target_asset": target_generated_asset_context,
        "lifecycle_complete": lifecycle_complete,
        "future_network_required": future_network_required or bool(generated_asset_quality_gate.get("network_required", False)),
        "future_spend_required": future_spend_required or bool(generated_asset_quality_gate.get("spend_required", False)),
        "animation_provider": "uthana" if manifest_animation_asset_count else "",
        "animation_review_tool": "review_generated_animation_lifecycle_gate",
        "review_tool": "chat_get_cockpit_overview",
        "lifecycle_tool": "skill_compile_ide_companion_asset_lifecycle_manifest",
        "placeholder_tool": "skill_compile_ide_companion_placeholder_manifest",
        "provider_review_tool": "review_provider_spend_gate",
        "import_review_tool": "review_generated_asset_import_gate",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "no_provider_call": True,
        "no_editor_mutation": True,
        "no_import": True,
        "no_ledger_write": True,
        "stop_before_lifecycle_mutation": True,
    }


def _generated_animation_next_safe_action(
    *,
    target: Dict[str, Any],
    status: str,
    success_statuses: set[str],
    paid_missing: List[Any],
    editor_missing: List[Any],
    quality_gate_count: int,
    quality_evidence_count: int,
) -> Dict[str, Any]:
    animation_name = str(target.get("name") or target.get("id") or "generated animation")
    motion_id = str(target.get("motion_id", ""))
    submit_tool = str(target.get("submit_tool", "gen_uthana_text_to_motion") or "")
    planned_submit_tool = str(target.get("planned_submit_tool") or submit_tool or "gen_uthana_text_to_motion")
    status_tool = str(target.get("status_tool", "") or ("gen_uthana_get_job" if str(target.get("task_type", "")) == "video_to_motion" else "gen_uthana_get_motion"))
    task_type = str(target.get("task_type", "text_to_motion") or "text_to_motion")
    source_video_file = str(
        target.get("video_file")
        or target.get("reference_video_file")
        or target.get("source_video_file")
        or ""
    )
    public_mcp_tool_available = bool(target.get("public_mcp_tool_available", True)) and bool(submit_tool)
    unsupported_reason = str(target.get("unsupported_reason", ""))
    base: Dict[str, Any] = {
        "schema": "unreal_mcp_chat_generated_animation_next_safe_action.v1",
        "target_animation_id": str(target.get("id", "")),
        "target_animation_name": animation_name,
        "provider": str(target.get("provider", "uthana") or "uthana"),
        "task_type": task_type,
        "submit_tool": submit_tool,
        "planned_submit_tool": planned_submit_tool,
        "status_tool": status_tool,
        "source_video_file": source_video_file,
        "video_reference_required": task_type == "video_to_motion",
        "video_reference_provided": bool(source_video_file),
        "public_mcp_tool_available": public_mcp_tool_available,
        "unsupported_reason": unsupported_reason,
        "no_provider_call": True,
        "no_download": True,
        "no_import": True,
        "no_editor_mutation": True,
        "no_ledger_write": True,
        "stop_before_provider_download_import_or_editor": True,
    }

    if not public_mcp_tool_available:
        return {
            **base,
            "state": "blocked",
            "action_id": "implement_uthana_submit_tool_wrapper",
            "label": "Implement Uthana submit tool wrapper",
            "tool": "chat_get_cockpit_overview",
            "action_type": "provider_wrapper_gap",
            "can_execute_now": False,
            "reason": unsupported_reason or f"{planned_submit_tool} is planned but no public MCP submit tool is registered yet.",
            "blocking_gate_count": 1,
            "blocking_gate_preview": ["public_mcp_submit_tool_missing", planned_submit_tool],
            "candidate_tool_after_unblocked": planned_submit_tool,
            "requires_provider_network": False,
            "requires_usage_confirmation": False,
            "requires_bridge": False,
        }

    if task_type == "video_to_motion" and status not in success_statuses and not source_video_file:
        return {
            **base,
            "state": "blocked",
            "action_id": "attach_uthana_video_reference",
            "label": "Attach Uthana video reference",
            "tool": "chat_get_cockpit_overview",
            "action_type": "input_evidence",
            "can_execute_now": False,
            "reason": "Uthana video-to-motion needs a local .mp4, .mov, or .avi reference file before upload can be confirmed.",
            "blocking_gate_count": 1,
            "blocking_gate_preview": ["uthana_video_reference_file"],
            "candidate_tool_after_unblocked": submit_tool,
            "requires_provider_network": False,
            "requires_usage_confirmation": False,
            "requires_bridge": False,
        }

    if paid_missing:
        return {
            **base,
            "state": "blocked",
            "action_id": "resolve_uthana_usage_gates",
            "label": "Resolve Uthana usage gates",
            "tool": "gen_compile_ide_companion_readiness",
            "action_type": "readiness_review",
            "can_execute_now": False,
            "reason": "Uthana motion generation is blocked until animation provider auth, quota evidence, and explicit usage approval are recorded.",
            "blocking_gate_count": len(paid_missing),
            "blocking_gate_preview": bounded_string_preview(paid_missing, 8),
            "candidate_tool_after_unblocked": submit_tool or planned_submit_tool,
            "requires_provider_network": False,
            "requires_usage_confirmation": False,
            "requires_bridge": False,
        }

    if status not in success_statuses:
        if task_type == "video_to_motion":
            return {
                **base,
                "state": "ready_to_confirm",
                "action_id": "submit_uthana_video_to_motion",
                "label": "Submit Uthana video-to-motion",
                "tool": submit_tool,
                "action_type": "provider_generation",
                "can_execute_now": False,
                "reason": "Uploading the reference clip is the next lifecycle step and still requires explicit per-call confirmation.",
                "blocking_gate_count": 0,
                "blocking_gate_preview": [],
                "requires_provider_network": True,
                "requires_usage_confirmation": True,
                "requires_bridge": False,
                "confirmation_field": "confirm_usage",
                "expected_followup_tool": status_tool or "gen_uthana_get_job",
                "argument_preview": {
                    "video_file": source_video_file,
                    "motion_name": animation_name,
                    "model": str(target.get("model", "") or "video-to-motion-v2"),
                    "character_id": str(target.get("default_character_id", "")),
                    "estimated_seconds": int(target.get("estimated_seconds", 0) or 0),
                },
            }
        return {
            **base,
            "state": "ready_to_confirm",
            "action_id": "submit_uthana_text_to_motion",
            "label": "Submit Uthana text-to-motion",
            "tool": submit_tool,
            "action_type": "provider_generation",
            "can_execute_now": False,
            "reason": "A provider call is the next lifecycle step and still requires an explicit per-call confirmation.",
            "blocking_gate_count": 0,
            "blocking_gate_preview": [],
            "requires_provider_network": True,
            "requires_usage_confirmation": True,
            "requires_bridge": False,
            "confirmation_field": "confirm_usage",
            "argument_preview": {
                "prompt": animation_name,
                "character_id": str(target.get("default_character_id", "")),
                "estimated_seconds": int(target.get("estimated_seconds", 0) or 0),
                "foot_ik": True,
            },
        }

    if not motion_id:
        return {
            **base,
            "state": "blocked",
            "action_id": "attach_uthana_motion_id",
            "label": "Attach Uthana motion id",
            "tool": "chat_get_cockpit_overview",
            "action_type": "evidence_reconciliation",
            "can_execute_now": False,
            "reason": "The motion result is marked complete but no Uthana motion id is available for download, import, or evidence compilation.",
            "blocking_gate_count": 1,
            "blocking_gate_preview": ["uthana_motion_id"],
            "requires_provider_network": False,
            "requires_usage_confirmation": False,
            "requires_bridge": False,
        }

    if editor_missing:
        return {
            **base,
            "state": "blocked",
            "action_id": "unblock_animation_import_gates",
            "label": "Unblock animation import gates",
            "tool": "gen_compile_ide_companion_readiness",
            "action_type": "editor_readiness_review",
            "can_execute_now": False,
            "reason": "Uthana motion import and retarget work must wait for editor mutation readiness and a live bridge.",
            "blocking_gate_count": len(editor_missing),
            "blocking_gate_preview": bounded_string_preview(editor_missing, 8),
            "candidate_tool_after_unblocked": "gen_uthana_import_animation_to_project",
            "requires_provider_network": False,
            "requires_usage_confirmation": False,
            "requires_bridge": True,
        }

    if quality_gate_count and quality_evidence_count < quality_gate_count:
        return {
            **base,
            "state": "needs_evidence",
            "action_id": "compile_generated_animation_evidence",
            "label": "Compile generated animation evidence",
            "tool": "gen_compile_generated_animation_evidence",
            "action_type": "evidence_compile",
            "can_execute_now": False,
            "reason": "Motion exists, but retarget/readback, AnimGraph or state-machine, PIE, ledger, and approval proof are not complete.",
            "blocking_gate_count": max(0, quality_gate_count - quality_evidence_count),
            "blocking_gate_preview": ["animation_retarget_animgraph_pie_ledger_proof"],
            "requires_provider_network": False,
            "requires_usage_confirmation": False,
            "requires_bridge": False,
        }

    return {
        **base,
        "state": "ready_to_record",
        "action_id": "record_generated_animation_evidence",
        "label": "Record generated animation evidence",
        "tool": "skill_record_ide_companion_evidence",
        "action_type": "ledger_record",
        "can_execute_now": True,
        "reason": "All generated animation quality proof gates are satisfied and ready to be recorded in the evidence ledger.",
        "blocking_gate_count": 0,
        "blocking_gate_preview": [],
        "requires_provider_network": False,
        "requires_usage_confirmation": False,
        "requires_bridge": False,
        "no_ledger_write": False,
        "stop_before_provider_download_import_or_editor": True,
    }


def _uthana_animation_usage_contract(
    *,
    target: Dict[str, Any],
    paid_generation: Dict[str, Any],
) -> Dict[str, Any]:
    missing_gates = paid_generation.get("missing_gates") if isinstance(paid_generation.get("missing_gates"), list) else []
    evidence_required = paid_generation.get("evidence_required") if isinstance(paid_generation.get("evidence_required"), list) else []
    allowance_receipt_command = (
        'python scripts\\write_paid_generation_evidence_review.py --record-masked-uthana-allowance-evidence '
        '--animation-allowance-summary "<masked Uthana allowance evidence>"'
    )
    usage_receipt_command = (
        'python scripts\\write_paid_generation_evidence_review.py --record-masked-uthana-allowance-evidence '
        '--record-explicit-spend-and-usage-approval --animation-allowance-summary "<masked Uthana allowance evidence>" '
        '--usage-approval-summary "<explicit human Uthana usage approval>"'
    )
    operator_command_handoff = [
        {
            "id": "record_masked_uthana_allowance_evidence",
            "label": "Record masked Uthana allowance evidence",
            "provider": "uthana",
            "command": allowance_receipt_command,
            "command_kind": "local_receipt",
            "receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
            "evidence_field": "animation_allowance_evidence_recorded",
            "summary_field": "animation_allowance_summary",
            "requires_provider_network_approval": True,
            "requires_human_spend_or_usage_approval": False,
            "approval_flags_included": False,
            "records_evidence_only": True,
            "no_provider_call": True,
            "no_task_submission": True,
            "no_download": True,
            "no_import": True,
            "no_editor_mutation": True,
            "no_git_mutation": True,
        },
        {
            "id": "record_explicit_uthana_usage_approval",
            "label": "Record explicit Uthana usage approval",
            "provider": "uthana",
            "command": usage_receipt_command,
            "command_kind": "local_receipt",
            "receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
            "evidence_field": "explicit_usage_approval_recorded",
            "summary_field": "usage_approval_summary",
            "requires_provider_network_approval": False,
            "requires_human_spend_or_usage_approval": True,
            "approval_flags_included": True,
            "records_evidence_only": True,
            "no_provider_call": True,
            "no_task_submission": True,
            "no_download": True,
            "no_import": True,
            "no_editor_mutation": True,
            "no_git_mutation": True,
        },
    ]
    return {
        "schema": "unreal_mcp_uthana_animation_usage_contract.v1",
        "provider": str(target.get("provider", "uthana") or "uthana"),
        "task_type": str(target.get("task_type", "text_to_motion") or "text_to_motion"),
        "source_video_file": str(target.get("video_file") or target.get("reference_video_file") or target.get("source_video_file") or ""),
        "video_reference_required": str(target.get("task_type", "")) == "video_to_motion",
        "target_animation_id": str(target.get("id", "")),
        "target_animation_name": str(target.get("name", "")),
        "target_skeleton": str(target.get("target_skeleton", "")),
        "estimated_seconds": int(target.get("estimated_seconds", 0) or 0),
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": bounded_string_preview(missing_gates, 8),
        "evidence_required_preview": bounded_string_preview(evidence_required, 8),
        "allowance_tools": [
            "gen_uthana_get_account",
            "gen_uthana_check_download_allowed",
        ],
        "allowance_review_steps": [
            "Confirm provider-network approval and no-spend intent before allowance checks.",
            "Run gen_uthana_get_account(include_user=False) for masked Uthana org allowance evidence.",
            "Run gen_uthana_check_download_allowed only for an existing motion id before any file fetch.",
            "Write Saved\\PaidGenerationEvidence\\last_review_receipt.json with masked allowance evidence and explicit usage approval.",
        ],
        "review_receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
        "review_receipt_required_command": "python scripts\\write_paid_generation_evidence_review.py",
        "wallet_evidence_receipt_command_template": allowance_receipt_command,
        "usage_confirmation_receipt_command_template": usage_receipt_command,
        "operator_command_handoff": operator_command_handoff,
        "operator_command_handoff_ids": [item["id"] for item in operator_command_handoff],
        "usage_confirmation_field": "confirm_usage=True for gen_uthana_text_to_motion, gen_uthana_video_to_motion, and gen_uthana_download_motion",
        "fallback_tool": "skill_compile_ide_companion_placeholder_manifest",
        "fallback_policy": "Keep fallback animation active until Uthana allowance, usage approval, motion/import proof, and ledger evidence are recorded.",
        "network_required_now": False,
        "spend_required_now": False,
        "future_network_required": True,
        "future_usage_confirmation_required": True,
        "no_provider_call": True,
        "no_task_submission": True,
        "no_download": True,
        "no_import": True,
        "no_editor_mutation": True,
        "no_credit_reservation": True,
        "no_ledger_write": True,
    }


def generated_animation_lifecycle_context(
    *,
    asset_lifecycles: List[Dict[str, Any]],
    readiness_policy: Dict[str, Any],
) -> Dict[str, Any]:
    animation_assets: List[Dict[str, Any]] = []
    for lifecycle in asset_lifecycles:
        if not isinstance(lifecycle, dict):
            continue
        manifest_path = str(lifecycle.get("manifest_path", ""))
        preview_assets = lifecycle.get("preview_animation_assets") if isinstance(lifecycle.get("preview_animation_assets"), list) else []
        for asset in preview_assets:
            if isinstance(asset, dict):
                row = dict(asset)
                row["manifest_path"] = manifest_path
                animation_assets.append(row)
    if not animation_assets:
        return {}

    success_statuses = {"success", "final", "complete", "completed"}

    def animation_priority(asset: Dict[str, Any]) -> tuple[int, str]:
        public_mcp_tool_available = bool(asset.get("public_mcp_tool_available", True)) and bool(
            str(asset.get("submit_tool", "gen_uthana_text_to_motion") or "")
        )
        if not public_mcp_tool_available:
            return (0, str(asset.get("id", "")))
        status = str(asset.get("task_status", ""))
        quality_gate_count = int(asset.get("quality_gate_count", 0) or 0)
        quality_evidence_count = int(asset.get("quality_evidence_count", 0) or 0)
        if status not in success_statuses:
            return (1, str(asset.get("id", "")))
        if quality_gate_count and quality_evidence_count < quality_gate_count:
            return (2, str(asset.get("id", "")))
        return (3, str(asset.get("id", "")))

    target = sorted(animation_assets, key=animation_priority)[0]
    unsupported_animation_assets = [
        asset for asset in animation_assets
        if not (bool(asset.get("public_mcp_tool_available", True)) and bool(str(asset.get("submit_tool", "gen_uthana_text_to_motion") or "")))
    ]
    paid_generation = readiness_policy.get("paid_animation_generation") if isinstance(readiness_policy.get("paid_animation_generation"), dict) else {}
    editor_mutation = readiness_policy.get("editor_mutation") if isinstance(readiness_policy.get("editor_mutation"), dict) else {}
    paid_missing = paid_generation.get("missing_gates") if isinstance(paid_generation.get("missing_gates"), list) else []
    editor_missing = editor_mutation.get("missing_gates") if isinstance(editor_mutation.get("missing_gates"), list) else []
    status = str(target.get("task_status", "not_submitted"))
    quality_gate_count = int(target.get("quality_gate_count", 0) or 0)
    quality_evidence_count = int(target.get("quality_evidence_count", 0) or 0)
    target_submit_tool = str(target.get("submit_tool", "gen_uthana_text_to_motion") or "")
    target_planned_submit_tool = str(target.get("planned_submit_tool") or target_submit_tool or "gen_uthana_text_to_motion")
    target_public_mcp_tool_available = bool(target.get("public_mcp_tool_available", True)) and bool(target_submit_tool)
    target_unsupported_reason = str(target.get("unsupported_reason", ""))
    missing_stages: List[str] = []
    if not target_public_mcp_tool_available:
        missing_stages.append("provider_submit_tool_missing")
    if (
        str(target.get("task_type", "")) == "video_to_motion"
        and status not in success_statuses
        and not str(target.get("video_file") or target.get("reference_video_file") or target.get("source_video_file") or "")
    ):
        missing_stages.append("uthana_video_reference_file")
    if status not in success_statuses:
        missing_stages.append("uthana_motion_generation")
    if not str(target.get("motion_id", "")):
        missing_stages.append("uthana_motion_id")
    if paid_missing:
        missing_stages.append("provider_usage_readiness")
    if editor_missing:
        missing_stages.append("editor_import_readiness")
    if quality_gate_count and quality_evidence_count < quality_gate_count:
        missing_stages.append("animation_retarget_animgraph_pie_ledger_proof")
    animation_ready = bool(
        status in success_statuses
        and quality_gate_count
        and quality_evidence_count >= quality_gate_count
        and not editor_missing
    )
    next_safe_action = _generated_animation_next_safe_action(
        target=target,
        status=status,
        success_statuses=success_statuses,
        paid_missing=paid_missing,
        editor_missing=editor_missing,
        quality_gate_count=quality_gate_count,
        quality_evidence_count=quality_evidence_count,
    )
    usage_contract = _uthana_animation_usage_contract(
        target=target,
        paid_generation=paid_generation,
    )
    usage_handoff = usage_contract.get("operator_command_handoff") if isinstance(usage_contract.get("operator_command_handoff"), list) else []
    if "wallet_evidence_recorded" in paid_missing:
        next_usage_handoff = dict(usage_handoff[0]) if usage_handoff else {}
    elif "spend_confirmation_recorded" in paid_missing:
        next_usage_handoff = dict(usage_handoff[1]) if len(usage_handoff) > 1 else {}
    else:
        next_usage_handoff = {}
    return {
        "schema": "unreal_mcp_chat_generated_animation_lifecycle_gate.v1",
        "state": "ready" if animation_ready else "blocked",
        "readiness_state": str(readiness_policy.get("state", "")),
        "animation_provider": "uthana",
        "animation_asset_count": len(animation_assets),
        "animation_pending_count": sum(1 for asset in animation_assets if str(asset.get("task_status", "")) not in success_statuses),
        "target_animation": {
            "id": str(target.get("id", "")),
            "name": str(target.get("name", "")),
            "role": str(target.get("role", "")),
            "provider": str(target.get("provider", "")),
            "task_type": str(target.get("task_type", "")),
            "source_video_file": str(target.get("video_file") or target.get("reference_video_file") or target.get("source_video_file") or ""),
            "video_reference_required": str(target.get("task_type", "")) == "video_to_motion",
            "video_reference_provided": bool(str(target.get("video_file") or target.get("reference_video_file") or target.get("source_video_file") or "")),
            "task_status": status,
            "motion_id": str(target.get("motion_id", "")),
            "submit_tool": target_submit_tool,
            "planned_submit_tool": target_planned_submit_tool,
            "public_mcp_tool_available": target_public_mcp_tool_available,
            "unsupported_reason": target_unsupported_reason,
            "manifest_path": str(target.get("manifest_path", "")),
            "expected_import_path": str(target.get("expected_import_path", "")),
            "target_skeleton": str(target.get("target_skeleton", "")),
            "format": str(target.get("format", "")),
            "estimated_seconds": int(target.get("estimated_seconds", 0) or 0),
            "default_character_id": str(target.get("default_character_id", "")),
            "quality_gate_preview": bounded_string_preview(target.get("quality_gate_preview", []), 8),
            "quality_proof_contract_schema": str(target.get("quality_proof_contract_schema", "")),
            "quality_proof_required_preview": bounded_string_preview(target.get("quality_proof_required_preview", []), 8),
        },
        "quality_gate_count": quality_gate_count,
        "quality_evidence_count": quality_evidence_count,
        "quality_evidence_missing_count": max(0, quality_gate_count - quality_evidence_count),
        "quality_proof_contract_schema": str(target.get("quality_proof_contract_schema", "")),
        "quality_proof_required_count": int(target.get("quality_proof_required_count", 0) or 0),
        "quality_proof_required_preview": bounded_string_preview(target.get("quality_proof_required_preview", []), 8),
        "unsupported_provider_task_count": len(unsupported_animation_assets),
        "unsupported_provider_task_preview": [
            {
                "id": str(asset.get("id", "")),
                "name": str(asset.get("name", "")),
                "provider": str(asset.get("provider", "")),
                "task_type": str(asset.get("task_type", "")),
                "planned_submit_tool": str(asset.get("planned_submit_tool") or asset.get("submit_tool", "")),
                "unsupported_reason": str(asset.get("unsupported_reason", "")),
            }
            for asset in unsupported_animation_assets[:5]
        ],
        "missing_stage_count": len(missing_stages),
        "missing_stage_preview": missing_stages[:8],
        "missing_paid_gate_count": len(paid_missing),
        "missing_paid_gate_preview": bounded_string_preview(paid_missing, 8),
        "missing_editor_gate_count": len(editor_missing),
        "missing_editor_gate_preview": bounded_string_preview(editor_missing, 8),
        "next_safe_action": next_safe_action,
        "uthana_usage_contract": usage_contract,
        "uthana_usage_receipt_path": usage_contract["review_receipt_path"],
        "uthana_usage_receipt_required_command": usage_contract["review_receipt_required_command"],
        "uthana_allowance_tool_preview": usage_contract["allowance_tools"],
        "uthana_allowance_review_steps": usage_contract["allowance_review_steps"],
        "uthana_usage_confirmation_field": usage_contract["usage_confirmation_field"],
        "uthana_usage_operator_command_handoff": usage_handoff,
        "uthana_usage_next_operator_command_handoff": next_usage_handoff,
        "submit_tool": target_submit_tool or ("gen_uthana_text_to_motion" if target_public_mcp_tool_available else ""),
        "planned_submit_tool": target_planned_submit_tool,
        "public_mcp_tool_available": target_public_mcp_tool_available,
        "unsupported_reason": target_unsupported_reason,
        "download_tool": "gen_uthana_download_motion",
        "import_tool": "gen_uthana_import_animation_to_project",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "requires_provider_key": True,
        "requires_usage_confirmation": True,
        "requires_bridge": True,
        "no_provider_call": True,
        "no_download": True,
        "no_import": True,
        "no_editor_mutation": True,
        "no_ledger_write": True,
        "stop_before_animation_generation_or_import": True,
    }


def generated_asset_import_context(
    *,
    generated_asset_quality_gate: Dict[str, Any],
    readiness_policy: Dict[str, Any],
) -> Dict[str, Any]:
    items = generated_asset_quality_gate.get("items") if isinstance(generated_asset_quality_gate.get("items"), list) else []
    candidates = [
        item for item in items
        if isinstance(item, dict) and str(item.get("state", "")) in {"import_pending", "quality_pending"}
    ]
    if not candidates:
        return {}

    def asset_priority(item: Dict[str, Any]) -> tuple[int, str]:
        state = str(item.get("state", ""))
        if state == "import_pending":
            return (0, str(item.get("id", "")))
        if state == "quality_pending":
            return (1, str(item.get("id", "")))
        return (2, str(item.get("id", "")))

    target = sorted(candidates, key=asset_priority)[0]
    editor_mutation = readiness_policy.get("editor_mutation") if isinstance(readiness_policy.get("editor_mutation"), dict) else {}
    missing_gates = editor_mutation.get("missing_gates") if isinstance(editor_mutation.get("missing_gates"), list) else []
    quality_gate_count = int(target.get("quality_gate_count", 0) or 0)
    quality_evidence_count = int(target.get("quality_evidence_count", 0) or 0)
    state = "ready" if editor_mutation.get("allowed", False) else "blocked"
    return {
        "state": state,
        "readiness_state": str(readiness_policy.get("state", "")),
        "editor_mutation_allowed": bool(editor_mutation.get("allowed", False)),
        "asset_count": int(generated_asset_quality_gate.get("asset_count", 0) or 0),
        "import_pending_count": int(generated_asset_quality_gate.get("import_pending_count", 0) or 0),
        "quality_pending_count": int(generated_asset_quality_gate.get("quality_pending_count", 0) or 0),
        "target_asset": {
            "id": str(target.get("id", "")),
            "name": str(target.get("name", "")),
            "role": str(target.get("role", "")),
            "provider": str(target.get("provider", "")),
            "state": str(target.get("state", "")),
            "task_status": str(target.get("task_status", "")),
            "next_gate": str(target.get("next_gate", "")),
            "manifest_path": str(target.get("manifest_path", "")),
            "expected_import_path": str(target.get("expected_import_path", "")),
            "imported_asset_path": str(target.get("imported_asset_path", "")),
            "has_placeholder": bool(target.get("has_placeholder", False)),
            "quality_gate_count": quality_gate_count,
            "quality_evidence_count": quality_evidence_count,
            "quality_gate_preview": bounded_string_preview(target.get("quality_gate_preview", []), 5),
        },
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": bounded_string_preview(missing_gates, 8),
        "quality_gate_count": quality_gate_count,
        "quality_evidence_count": quality_evidence_count,
        "quality_evidence_missing_count": max(0, quality_gate_count - quality_evidence_count),
        "import_readback_required": True,
        "quality_proof_required": True,
        "placeholder_replacement_required": bool(target.get("has_placeholder", False)),
        "review_tool": "chat_get_cockpit_overview",
        "lifecycle_tool": "skill_compile_ide_companion_asset_lifecycle_manifest",
        "queue_tool": "skill_compile_ide_companion_editor_queue",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "requires_bridge": True,
        "stop_before_import_or_quality_work": True,
    }


def generated_asset_quality_proof_context(
    *,
    generated_asset_quality_gate: Dict[str, Any],
    readiness_policy: Dict[str, Any],
) -> Dict[str, Any]:
    items = generated_asset_quality_gate.get("items") if isinstance(generated_asset_quality_gate.get("items"), list) else []
    candidates = [
        item for item in items
        if isinstance(item, dict) and int(item.get("quality_gate_count", 0) or 0) > int(item.get("quality_evidence_count", 0) or 0)
    ]
    if not candidates:
        return {}

    def asset_priority(item: Dict[str, Any]) -> tuple[int, str]:
        state = str(item.get("state", ""))
        if state == "quality_pending":
            return (0, str(item.get("id", "")))
        if state == "import_pending":
            return (1, str(item.get("id", "")))
        if state == "provider_pending":
            return (2, str(item.get("id", "")))
        return (3, str(item.get("id", "")))

    target = sorted(candidates, key=asset_priority)[0]
    editor_mutation = readiness_policy.get("editor_mutation") if isinstance(readiness_policy.get("editor_mutation"), dict) else {}
    missing_gates = editor_mutation.get("missing_gates") if isinstance(editor_mutation.get("missing_gates"), list) else []
    imported_path = str(target.get("imported_asset_path", ""))
    quality_gate_count = int(target.get("quality_gate_count", 0) or 0)
    quality_evidence_count = int(target.get("quality_evidence_count", 0) or 0)
    missing_evidence_count = max(0, quality_gate_count - quality_evidence_count)
    quality_gate_preview = bounded_string_preview(target.get("quality_gate_preview", []), 8)
    quality_text = " ".join(str(item).lower() for item in quality_gate_preview)
    missing_stages: List[str] = []
    if not imported_path:
        missing_stages.append("import_result")
    if missing_gates:
        missing_stages.append("editor_mutation_readiness")
    if missing_evidence_count:
        missing_stages.append("material_collision_viewport_ledger_proof")
    missing_stages.append("ledger_quality_evidence")
    proof_ready = bool(editor_mutation.get("allowed", False) and imported_path and missing_evidence_count == 0)
    return {
        "schema": "unreal_mcp_chat_generated_asset_quality_proof_gate.v1",
        "state": "ready" if proof_ready else "blocked",
        "readiness_state": str(readiness_policy.get("state", "")),
        "editor_mutation_allowed": bool(editor_mutation.get("allowed", False)),
        "asset_count": int(generated_asset_quality_gate.get("asset_count", 0) or 0),
        "quality_pending_count": int(generated_asset_quality_gate.get("quality_pending_count", 0) or 0),
        "quality_candidate_count": len(candidates),
        "target_asset": {
            "id": str(target.get("id", "")),
            "name": str(target.get("name", "")),
            "role": str(target.get("role", "")),
            "provider": str(target.get("provider", "")),
            "state": str(target.get("state", "")),
            "task_status": str(target.get("task_status", "")),
            "manifest_path": str(target.get("manifest_path", "")),
            "expected_import_path": str(target.get("expected_import_path", "")),
            "imported_asset_path": imported_path,
            "has_placeholder": bool(target.get("has_placeholder", False)),
            "quality_gate_preview": quality_gate_preview,
            "quality_proof_contract_schema": str(target.get("quality_proof_contract_schema", "")),
            "quality_proof_required_preview": bounded_string_preview(target.get("quality_proof_required_preview", []), 8),
        },
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": bounded_string_preview(missing_gates, 8),
        "missing_stage_count": len(missing_stages),
        "missing_stage_preview": missing_stages[:8],
        "quality_gate_count": quality_gate_count,
        "quality_evidence_count": quality_evidence_count,
        "quality_evidence_missing_count": missing_evidence_count,
        "quality_proof_contract_schema": str(target.get("quality_proof_contract_schema", "")),
        "quality_proof_required_count": int(target.get("quality_proof_required_count", 0) or 0),
        "quality_proof_required_preview": bounded_string_preview(target.get("quality_proof_required_preview", []), 8),
        "requires_imported_asset": not bool(imported_path),
        "requires_material_proof": "material" in quality_text,
        "requires_collision_proof": "collision" in quality_text,
        "requires_viewport_proof": "viewport" in quality_text or "thumbnail" in quality_text or "screenshot" in quality_text,
        "requires_ledger_proof": True,
        "quality_proof_ready": proof_ready,
        "review_tool": "chat_get_cockpit_overview",
        "import_review_tool": "review_generated_asset_import_gate",
        "replacement_review_tool": "review_generated_asset_replacement_gate",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "requires_bridge": True,
        "no_provider_call": True,
        "no_import": True,
        "no_editor_mutation": True,
        "no_viewport_capture": True,
        "no_ledger_write": True,
        "stop_before_quality_proof_work": True,
    }


def generated_asset_replacement_context(
    *,
    asset_lifecycles: List[Dict[str, Any]],
    readiness_policy: Dict[str, Any],
) -> Dict[str, Any]:
    placeholder_assets: List[Dict[str, Any]] = []
    for lifecycle in asset_lifecycles:
        if not isinstance(lifecycle, dict):
            continue
        manifest_path = str(lifecycle.get("manifest_path", ""))
        preview_assets = lifecycle.get("preview_assets") if isinstance(lifecycle.get("preview_assets"), list) else []
        for asset in preview_assets:
            if isinstance(asset, dict) and asset.get("has_placeholder"):
                row = dict(asset)
                row["manifest_path"] = manifest_path
                placeholder_assets.append(row)
    if not placeholder_assets:
        return {}

    def replacement_priority(asset: Dict[str, Any]) -> tuple[int, str]:
        imported_path = str(asset.get("imported_asset_path", ""))
        quality_gate_count = int(asset.get("quality_gate_count", 0) or 0)
        quality_evidence_count = int(asset.get("quality_evidence_count", 0) or 0)
        task_status = str(asset.get("task_status", ""))
        if not imported_path:
            return (0, str(asset.get("id", "")))
        if quality_gate_count and quality_evidence_count < quality_gate_count:
            return (1, str(asset.get("id", "")))
        if task_status not in {"success", "final", "complete", "completed"}:
            return (2, str(asset.get("id", "")))
        return (3, str(asset.get("id", "")))

    target = sorted(placeholder_assets, key=replacement_priority)[0]
    editor_mutation = readiness_policy.get("editor_mutation") if isinstance(readiness_policy.get("editor_mutation"), dict) else {}
    missing_gates = editor_mutation.get("missing_gates") if isinstance(editor_mutation.get("missing_gates"), list) else []
    imported_path = str(target.get("imported_asset_path", ""))
    task_status = str(target.get("task_status") or "not_submitted")
    quality_gate_count = int(target.get("quality_gate_count", 0) or 0)
    quality_evidence_count = int(target.get("quality_evidence_count", 0) or 0)
    missing_stages: List[str] = []
    if task_status not in {"success", "final", "complete", "completed"}:
        missing_stages.append("provider_task_completion")
    if not imported_path:
        missing_stages.append("generated_asset_import")
    if quality_gate_count and quality_evidence_count < quality_gate_count:
        missing_stages.append("quality_proof")
    if missing_gates:
        missing_stages.append("editor_mutation_readiness")
    missing_stages.append("ledger_replacement_evidence")
    replacement_ready = bool(
        editor_mutation.get("allowed", False)
        and imported_path
        and (not quality_gate_count or quality_evidence_count >= quality_gate_count)
        and task_status in {"success", "final", "complete", "completed"}
    )
    return {
        "schema": "unreal_mcp_chat_generated_asset_replacement_gate.v1",
        "state": "ready" if replacement_ready else "blocked",
        "readiness_state": str(readiness_policy.get("state", "")),
        "editor_mutation_allowed": bool(editor_mutation.get("allowed", False)),
        "asset_count": sum(int(lifecycle.get("asset_count", 0) or 0) for lifecycle in asset_lifecycles if isinstance(lifecycle, dict)),
        "placeholder_count": len(placeholder_assets),
        "replacement_pending_count": sum(1 for asset in placeholder_assets if not str(asset.get("imported_asset_path", ""))),
        "quality_gate_count": quality_gate_count,
        "quality_evidence_count": quality_evidence_count,
        "quality_evidence_missing_count": max(0, quality_gate_count - quality_evidence_count),
        "target_asset": {
            "id": str(target.get("id", "")),
            "name": str(target.get("name", "")),
            "role": str(target.get("role", "")),
            "provider": str(target.get("provider", "")),
            "task_status": task_status,
            "manifest_path": str(target.get("manifest_path", "")),
            "expected_import_path": str(target.get("expected_import_path", "")),
            "imported_asset_path": imported_path,
            "placeholder_asset_path": str(target.get("placeholder_asset_path", "")),
            "replacement_policy_preview": bounded_string_preview(target.get("replacement_policy_preview", []), 5),
        },
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": bounded_string_preview(missing_gates, 8),
        "missing_stage_count": len(missing_stages),
        "missing_stage_preview": missing_stages[:8],
        "replacement_ready": replacement_ready,
        "import_required_before_replacement": not bool(imported_path),
        "quality_proof_required": bool(quality_gate_count and quality_evidence_count < quality_gate_count),
        "ledger_evidence_required": True,
        "review_tool": "chat_get_cockpit_overview",
        "lifecycle_tool": "skill_compile_ide_companion_asset_lifecycle_manifest",
        "queue_tool": "skill_compile_ide_companion_editor_queue",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "requires_bridge": True,
        "no_provider_call": True,
        "no_import": True,
        "no_editor_mutation": True,
        "no_ledger_write": True,
        "stop_before_placeholder_replacement": True,
    }


def generated_asset_provider_task_context(
    *,
    asset_lifecycles: List[Dict[str, Any]],
    readiness_policy: Dict[str, Any],
) -> Dict[str, Any]:
    assets: List[Dict[str, Any]] = []
    for lifecycle in asset_lifecycles:
        if not isinstance(lifecycle, dict):
            continue
        manifest_path = str(lifecycle.get("manifest_path", ""))
        preview_assets = lifecycle.get("preview_assets") if isinstance(lifecycle.get("preview_assets"), list) else []
        for asset in preview_assets:
            if isinstance(asset, dict):
                row = dict(asset)
                row["manifest_path"] = manifest_path
                assets.append(row)
    if not assets:
        return {}

    success_statuses = {"success", "final", "complete", "completed"}
    failed_statuses = {"blocked", "failed", "error", "cancelled", "canceled"}
    submitted_statuses = {"submitted", "queued", "running", "processing", "in_progress"}

    def status_for(asset: Dict[str, Any]) -> str:
        return str(asset.get("task_status") or "not_submitted")

    def has_download(asset: Dict[str, Any]) -> bool:
        return bool(str(asset.get("downloaded_asset_path", "")) or str(asset.get("download_path", "")) or str(asset.get("imported_asset_path", "")))

    def task_priority(asset: Dict[str, Any]) -> tuple[int, str]:
        status = status_for(asset)
        imported_path = str(asset.get("imported_asset_path", ""))
        if status in failed_statuses:
            return (0, str(asset.get("id", "")))
        if status in success_statuses and (not has_download(asset) or not imported_path):
            return (1, str(asset.get("id", "")))
        if status in submitted_statuses:
            return (2, str(asset.get("id", "")))
        if status == "not_submitted":
            return (3, str(asset.get("id", "")))
        return (4, str(asset.get("id", "")))

    target = sorted(assets, key=task_priority)[0]
    paid_generation = readiness_policy.get("paid_generation") if isinstance(readiness_policy.get("paid_generation"), dict) else {}
    missing_paid_gates = paid_generation.get("missing_gates") if isinstance(paid_generation.get("missing_gates"), list) else []
    target_status = status_for(target)
    target_task_id = str(target.get("task_id", ""))
    target_imported_path = str(target.get("imported_asset_path", ""))
    target_has_download = has_download(target)
    provider_pending_count = sum(1 for asset in assets if status_for(asset) in {"not_submitted", "blocked"})
    provider_failed_count = sum(1 for asset in assets if status_for(asset) in failed_statuses)
    provider_success_count = sum(1 for asset in assets if status_for(asset) in success_statuses)
    submitted_count = sum(1 for asset in assets if status_for(asset) in submitted_statuses or bool(str(asset.get("task_id", ""))))
    task_id_missing_count = sum(1 for asset in assets if status_for(asset) != "not_submitted" and not str(asset.get("task_id", "")))
    download_pending_count = sum(1 for asset in assets if status_for(asset) in success_statuses and not has_download(asset))
    import_pending_count = sum(1 for asset in assets if status_for(asset) in success_statuses and not str(asset.get("imported_asset_path", "")))
    missing_stages: List[str] = []
    if missing_paid_gates and target_status == "not_submitted":
        missing_stages.append("provider_spend_readiness")
    if target_status == "not_submitted":
        missing_stages.append("provider_task_submission")
    if target_status in submitted_statuses:
        missing_stages.append("provider_task_status_wait")
    if target_status in failed_statuses:
        missing_stages.append("provider_task_repair")
    if target_status in success_statuses and not target_has_download:
        missing_stages.append("download_result")
    if target_status in success_statuses and not target_imported_path:
        missing_stages.append("import_result")
    if target_status != "not_submitted" and not target_task_id:
        missing_stages.append("provider_task_id")
    missing_stages.append("ledger_provider_task_evidence")
    provider_task_ready = bool(
        target_status in success_statuses
        and target_task_id
        and target_has_download
        and not missing_paid_gates
    )
    return {
        "schema": "unreal_mcp_chat_generated_asset_provider_task_gate.v1",
        "state": "ready" if provider_task_ready else "blocked",
        "readiness_state": str(readiness_policy.get("state", "")),
        "paid_generation_allowed": bool(paid_generation.get("allowed", False)),
        "asset_count": len(assets),
        "provider_pending_count": provider_pending_count,
        "provider_failed_count": provider_failed_count,
        "provider_success_count": provider_success_count,
        "submitted_count": submitted_count,
        "task_id_missing_count": task_id_missing_count,
        "download_pending_count": download_pending_count,
        "import_pending_count": import_pending_count,
        "target_asset": {
            "id": str(target.get("id", "")),
            "name": str(target.get("name", "")),
            "role": str(target.get("role", "")),
            "provider": str(target.get("provider", "")),
            "task_status": target_status,
            "task_id": target_task_id,
            "submit_tool": str(target.get("submit_tool", "")),
            "status_tool": str(target.get("status_tool", "")),
            "download_tool": str(target.get("download_tool", "")),
            "import_tool": str(target.get("import_tool", "")),
            "manifest_path": str(target.get("manifest_path", "")),
            "expected_import_path": str(target.get("expected_import_path", "")),
            "downloaded_asset_path": str(target.get("downloaded_asset_path", "")),
            "download_path": str(target.get("download_path", "")),
            "imported_asset_path": target_imported_path,
        },
        "missing_gate_count": len(missing_paid_gates),
        "missing_gate_preview": bounded_string_preview(missing_paid_gates, 8),
        "missing_stage_count": len(missing_stages),
        "missing_stage_preview": missing_stages[:8],
        "provider_task_ready": provider_task_ready,
        "status_poll_required": target_status in submitted_statuses,
        "download_required": target_status in success_statuses and not target_has_download,
        "import_required_after_download": target_status in success_statuses and not target_imported_path,
        "ledger_evidence_required": True,
        "review_tool": "chat_get_cockpit_overview",
        "spend_review_tool": "review_provider_spend_gate",
        "lifecycle_tool": "skill_compile_ide_companion_asset_lifecycle_manifest",
        "import_review_tool": "review_generated_asset_import_gate",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "requires_network": True,
        "requires_bridge_for_import": True,
        "no_provider_call": True,
        "no_status_poll": True,
        "no_download": True,
        "no_import": True,
        "no_editor_mutation": True,
        "no_ledger_write": True,
        "stop_before_provider_task_or_download": True,
    }


def readiness_policy_context(readiness_policy: Dict[str, Any]) -> Dict[str, Any]:
    if not readiness_policy:
        return {}
    policy_names = [
        "editor_mutation",
        "paid_generation",
        "paid_animation_generation",
        "blueprint_mutation",
        "wip_promotion",
    ]
    missing_gates: List[str] = []
    blocked_policies: List[str] = []
    evidence_required: List[str] = []
    for policy_name in policy_names:
        row = readiness_policy.get(policy_name)
        if not isinstance(row, dict):
            continue
        if not row.get("allowed", False):
            blocked_policies.append(policy_name)
        row_missing = row.get("missing_gates") if isinstance(row.get("missing_gates"), list) else []
        for gate in row_missing:
            gate_text = str(gate)
            if gate_text and gate_text not in missing_gates:
                missing_gates.append(gate_text)
        row_evidence = row.get("evidence_required") if isinstance(row.get("evidence_required"), list) else []
        for evidence in row_evidence:
            evidence_text = str(evidence)
            if evidence_text and evidence_text not in evidence_required:
                evidence_required.append(evidence_text)
    wip_promotion = readiness_policy.get("wip_promotion") if isinstance(readiness_policy.get("wip_promotion"), dict) else {}
    wip_evidence_required = wip_promotion.get("evidence_required") if isinstance(wip_promotion.get("evidence_required"), list) else []
    return {
        "state": str(readiness_policy.get("state", "")),
        "blocked_policy_count": int(readiness_policy.get("blocked_policy_count", len(blocked_policies)) or 0),
        "blocked_policies": blocked_policies,
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": missing_gates[:8],
        "evidence_required_count": len(evidence_required),
        "evidence_required_preview": bounded_string_preview(evidence_required, 8),
        "wip_promotion_evidence_required_count": len(wip_evidence_required),
        "wip_promotion_evidence_required_preview": bounded_string_preview(wip_evidence_required, 10),
        "recommended_tools": bounded_string_preview(readiness_policy.get("recommended_tools", []), 5),
        "network_required": bool(readiness_policy.get("network_required", False)),
        "unreal_editor_required": bool(readiness_policy.get("unreal_editor_required", False)),
        "spend_required": bool(readiness_policy.get("spend_required", False)),
        "review_tool": "chat_get_cockpit_overview",
        "readiness_tool": "gen_compile_ide_companion_readiness",
        "stop_before_editor_or_provider": True,
    }


def readiness_repair_queue_context(readiness_repair_queue: Dict[str, Any]) -> Dict[str, Any]:
    if not readiness_repair_queue:
        return {}
    next_action = readiness_repair_queue.get("next_action") if isinstance(readiness_repair_queue.get("next_action"), dict) else {}
    action_preview = readiness_repair_queue.get("action_preview") if isinstance(readiness_repair_queue.get("action_preview"), list) else []
    blocking_gates = readiness_repair_queue.get("blocking_gate_preview") if isinstance(readiness_repair_queue.get("blocking_gate_preview"), list) else []
    return {
        "schema": str(readiness_repair_queue.get("schema", "unreal_mcp_readiness_repair_queue.v1")),
        "state": str(readiness_repair_queue.get("state", "")),
        "recommended_next": str(readiness_repair_queue.get("recommended_next", "none")),
        "priority_policy": str(readiness_repair_queue.get("priority_policy", "chat_health_then_wip_promotion_safety_then_bridge_proof_then_paid_provider_gates")),
        "action_count": int(readiness_repair_queue.get("action_count", 0) or 0),
        "blocking_gate_count": int(readiness_repair_queue.get("blocking_gate_count", len(blocking_gates)) or 0),
        "blocking_gate_preview": bounded_string_preview(blocking_gates, 8),
        "action_preview": action_preview[:6],
        "next_action": next_action,
        "next_action_id": str(next_action.get("action_id", "")),
        "next_gate": str(next_action.get("gate", "")),
        "next_policy_area": str(next_action.get("policy_area", "")),
        "next_title": str(next_action.get("title", "")),
        "next_tool": str(next_action.get("recommended_tool", "")),
        "next_contract": str(next_action.get("recommended_contract", "")),
        "next_required_command": str(next_action.get("required_command") or next_action.get("proof_command") or next_action.get("receipt_command_template") or ""),
        "next_operator_command_handoff": (
            (
                list(next_action.get("target_review_human_approval_command_handoff", []))[:1]
                if (
                    next_action.get("target_review_pending_human_approval_only")
                    and isinstance(next_action.get("target_review_human_approval_command_handoff"), list)
                )
                else []
            )
            or (
                list(next_action.get("operator_command_handoff", []))[:2]
                if isinstance(next_action.get("operator_command_handoff"), list)
                else []
            )
            or (
                list(next_action.get("target_review_operator_command_handoff", []))[:2]
                if isinstance(next_action.get("target_review_operator_command_handoff"), list)
                else []
            )
        ),
        "next_evidence_preview": bounded_string_preview(next_action.get("evidence_required_preview", []), 6),
        "next_evidence_review_matrix_count": int(next_action.get("evidence_review_matrix_count", 0) or 0),
        "next_evidence_unresolved_count": int(next_action.get("evidence_unresolved_count", 0) or 0),
        "next_evidence_review_matrix_preview": (
            list(next_action.get("evidence_review_matrix_preview", []))[:3]
            if isinstance(next_action.get("evidence_review_matrix_preview"), list)
            else []
        ),
        "next_target_review_group": str(next_action.get("target_review_group", "")),
        "next_target_review_order": int(next_action.get("target_review_order", 0) or 0),
        "next_target_review_scope": str(next_action.get("target_review_scope", "")),
        "next_target_review_tracked_count": int(next_action.get("target_review_tracked_count", 0) or 0),
        "next_target_review_untracked_count": int(next_action.get("target_review_untracked_count", 0) or 0),
        "next_target_review_status": str(next_action.get("target_review_status", "")),
        "next_target_review_evidence_complete": bool(next_action.get("target_review_evidence_complete", False)),
        "next_target_review_recorded_evidence_count": int(next_action.get("target_review_recorded_evidence_count", 0) or 0),
        "next_target_review_recorded_evidence_preview": bounded_string_preview(next_action.get("target_review_recorded_evidence_preview", []), 8),
        "next_target_review_human_approval_recorded": bool(next_action.get("target_review_human_approval_recorded", False)),
        "next_target_review_missing_evidence_count": int(next_action.get("target_review_missing_evidence_count", 0) or 0),
        "next_target_review_missing_evidence_preview": bounded_string_preview(next_action.get("target_review_missing_evidence_preview", []), 8),
        "next_target_review_required_evidence_preview": bounded_string_preview(next_action.get("target_review_required_evidence_preview", []), 8),
        "next_target_review_decision_prompt_preview": bounded_string_preview(next_action.get("target_review_decision_prompt_preview", []), 8),
        "next_target_review_receipt_command_template": str(next_action.get("target_review_receipt_command_template", "")),
        "next_target_review_approval_receipt_command_template": str(next_action.get("target_review_approval_receipt_command_template", "")),
        "next_target_review_receipt_command_policy": str(next_action.get("target_review_receipt_command_policy", "")),
        "next_target_review_operator_command_handoff": (
            list(next_action.get("target_review_operator_command_handoff", []))[:2]
            if isinstance(next_action.get("target_review_operator_command_handoff"), list)
            else []
        ),
        "next_target_review_pending_human_approval_only": bool(next_action.get("target_review_pending_human_approval_only", False)),
        "next_target_review_human_approval_gate": str(next_action.get("target_review_human_approval_gate", "")),
        "next_target_review_human_approval_command_handoff": (
            list(next_action.get("target_review_human_approval_command_handoff", []))[:1]
            if isinstance(next_action.get("target_review_human_approval_command_handoff"), list)
            else []
        ),
        "next_target_review_focused_test_command_handoff": (
            list(next_action.get("target_review_focused_test_command_handoff", []))[:5]
            if isinstance(next_action.get("target_review_focused_test_command_handoff"), list)
            else []
        ),
        "next_target_review_focused_test_command_count": int(next_action.get("target_review_focused_test_command_count", 0) or 0),
        "next_target_review_focused_test_command_preview": bounded_string_preview(next_action.get("target_review_focused_test_command_preview", []), 5),
        "next_target_review_sample_preview": bounded_string_preview(next_action.get("target_review_sample_preview", []), 5),
        "next_target_review_promotion_allowed_after_receipt": bool(next_action.get("target_review_promotion_allowed_after_receipt", False)),
        "next_target_review_merge_policy": str(next_action.get("target_review_merge_policy", "")),
        "next_target_review_previous_evidence_merged": bool(next_action.get("target_review_previous_evidence_merged", False)),
        "next_target_review_reset_evidence": bool(next_action.get("target_review_reset_evidence", False)),
        "requires_bridge": bool(next_action.get("requires_bridge", False)),
        "requires_network": bool(next_action.get("requires_network", False)),
        "requires_spend": bool(next_action.get("requires_spend", False)),
        "requires_unreal_editor": bool(next_action.get("requires_unreal_editor", False)),
        "no_auto_execute": bool(readiness_repair_queue.get("no_auto_execute", True)),
        "no_secret_echo": bool(readiness_repair_queue.get("no_secret_echo", True)),
        "no_git_mutation": bool(readiness_repair_queue.get("no_git_mutation", True)),
        "no_editor_mutation": bool(readiness_repair_queue.get("no_editor_mutation", True)),
        "review_tool": "chat_get_cockpit_overview",
        "record_tool": "skill_record_ide_companion_evidence",
        "stop_before_running_repair": True,
    }


def blueprint_mutation_context(
    *,
    readiness_policy: Dict[str, Any],
    work_order_template: Dict[str, Any],
    queues: List[Dict[str, Any]],
    target_phase: str,
    readiness_repair_queue: Dict[str, Any] | None = None,
    blueprint_evidence: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    blueprint_policy = readiness_policy.get("blueprint_mutation") if isinstance(readiness_policy.get("blueprint_mutation"), dict) else {}
    if not blueprint_policy:
        return {}
    evidence_receipt = blueprint_evidence if isinstance(blueprint_evidence, dict) else {}
    missing_gates = blueprint_policy.get("missing_gates") if isinstance(blueprint_policy.get("missing_gates"), list) else []
    evidence_required = blueprint_policy.get("evidence_required") if isinstance(blueprint_policy.get("evidence_required"), list) else []
    required_gates = blueprint_policy.get("required_gates") if isinstance(blueprint_policy.get("required_gates"), list) else []
    queued_action_count = sum(int(queue.get("action_count", 0) or 0) for queue in queues)
    bridge_blocked_count = sum(1 for queue in queues if queue.get("bridge_blocked"))
    missing_gate_set = {str(gate) for gate in missing_gates}
    required_gate_set = {str(gate) for gate in required_gates}
    evidence_required_set = {str(item) for item in evidence_required}
    repair_queue = readiness_repair_queue if isinstance(readiness_repair_queue, dict) else {}
    repair_actions = repair_queue.get("action_preview") if isinstance(repair_queue.get("action_preview"), list) else []
    blueprint_repair_actions = [
        {
            "gate": str(action.get("gate", "")),
            "action_id": str(action.get("action_id", "")),
            "title": str(action.get("title", "")),
            "recommended_tool": str(action.get("recommended_tool", "")),
            "receipt_path": str(action.get("receipt_path", "")),
            "receipt_state": str(action.get("receipt_state", "")),
            "required_command": str(action.get("required_command", "")),
            "receipt_command_template": str(action.get("receipt_command_template", "")),
            "operator_command_handoff": (
                list(action.get("operator_command_handoff", []))[:1]
                if isinstance(action.get("operator_command_handoff"), list)
                else []
            ),
            "requires_bridge": bool(action.get("requires_bridge", False)),
            "requires_unreal_editor": bool(action.get("requires_unreal_editor", False)),
            "evidence_required_preview": bounded_string_preview(action.get("evidence_required_preview", []), 5),
            "review_steps_preview": bounded_string_preview(action.get("review_steps", []), 4),
            "pre_read_evidence_recorded": bool(action.get("pre_read_evidence_recorded", False)),
            "compile_plan_recorded": bool(action.get("compile_plan_recorded", False)),
            "readback_plan_recorded": bool(action.get("readback_plan_recorded", False)),
            "no_blueprint_mutation": bool(action.get("no_blueprint_mutation", True)),
        }
        for action in repair_actions
        if isinstance(action, dict) and action.get("policy_area") == "blueprint_mutation"
    ]
    return {
        "state": "ready" if blueprint_policy.get("allowed", False) else "blocked",
        "readiness_state": str(readiness_policy.get("state", "")),
        "blueprint_mutation_allowed": bool(blueprint_policy.get("allowed", False)),
        "target_phase": str(target_phase or work_order_template.get("target_phase", "")),
        "template_name": str(work_order_template.get("template_name", "")),
        "display_name": str(work_order_template.get("display_name", "")),
        "operation_count": int(work_order_template.get("operation_count", 0) or 0),
        "editor_operation_count": int(work_order_template.get("editor_operation_count", 0) or 0),
        "bridge_required_operation_count": int(work_order_template.get("bridge_required_operation_count", 0) or 0),
        "compile_after_operation_count": int(work_order_template.get("compile_after_operation_count", 0) or 0),
        "readback_after_operation_count": int(work_order_template.get("readback_after_operation_count", 0) or 0),
        "compile_check_count": int(work_order_template.get("compile_check_count", 0) or 0),
        "pie_validation_count": int(work_order_template.get("pie_validation_count", 0) or 0),
        "runtime_proof_required_count": int(work_order_template.get("runtime_proof_required_count", 0) or 0),
        "runtime_proof_mode": str(work_order_template.get("runtime_proof_mode", "")),
        "runtime_proof_required_preview": bounded_string_preview(work_order_template.get("runtime_proof_required_preview", []), 8),
        "runtime_proof_tool_preview": bounded_string_preview(work_order_template.get("runtime_proof_tool_preview", []), 8),
        "evidence_requirement_count": int(work_order_template.get("evidence_requirement_count", 0) or 0),
        "operation_proof_contract_count": int(work_order_template.get("operation_proof_contract_count", 0) or 0),
        "operation_proof_required_after_preview": bounded_string_preview(work_order_template.get("operation_proof_required_after_preview", []), 8),
        "editor_operation_type_preview": bounded_string_preview(work_order_template.get("editor_operation_type_preview", []), 6),
        "editor_operation_tool_preview": bounded_string_preview(work_order_template.get("editor_operation_tool_preview", []), 8),
        "editor_operation_preview": bounded_string_preview(work_order_template.get("editor_operation_preview", []), 5),
        "queue_count": len(queues),
        "queued_action_count": queued_action_count,
        "bridge_blocked_count": bridge_blocked_count,
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": bounded_string_preview(missing_gates, 8),
        "required_gate_count": len(required_gates),
        "required_gate_preview": bounded_string_preview(required_gates, 8),
        "evidence_required_count": len(evidence_required),
        "evidence_required_preview": bounded_string_preview(evidence_required, 8),
        "repair_queue_state": str(repair_queue.get("state", "")),
        "repair_queue_recommended_next": str(repair_queue.get("recommended_next", "none")),
        "evidence_receipt_state": str(evidence_receipt.get("state", evidence_receipt.get("status", "missing"))),
        "evidence_receipt_status": str(evidence_receipt.get("status", evidence_receipt.get("state", "missing"))),
        "evidence_receipt_exists": bool(evidence_receipt.get("receipt_exists", False)),
        "evidence_receipt_path": str(
            evidence_receipt.get("receipt_path", evidence_receipt.get("path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json"))
        ),
        "evidence_receipt_required_command": str(
            evidence_receipt.get("receipt_required_command", evidence_receipt.get("required_command", "python scripts\\write_blueprint_mutation_evidence_review.py"))
        ),
        "operator_command_handoff": (
            list(evidence_receipt.get("operator_command_handoff", []))[:3]
            if isinstance(evidence_receipt.get("operator_command_handoff"), list)
            else []
        ),
        "pre_read_evidence_recorded": bool(evidence_receipt.get("pre_read_evidence_recorded", False)),
        "compile_plan_recorded": bool(evidence_receipt.get("compile_plan_recorded", False)),
        "readback_plan_recorded": bool(evidence_receipt.get("readback_plan_recorded", False)),
        "target_blueprint_path": str(evidence_receipt.get("target_blueprint_path", "")),
        "intended_mutation_summary": str(evidence_receipt.get("intended_mutation_summary", "")),
        "pre_read_summary": str(evidence_receipt.get("pre_read_summary", "")),
        "compile_plan_summary": str(evidence_receipt.get("compile_plan_summary", "")),
        "readback_plan_summary": str(evidence_receipt.get("readback_plan_summary", "")),
        "evidence_merge_policy": str(evidence_receipt.get("merge_policy", "preserve_existing_evidence_unless_reset")),
        "reset_evidence": bool(evidence_receipt.get("reset_evidence", False)),
        "human_approval_required_before_blueprint_mutation": bool(
            evidence_receipt.get("human_approval_required_before_blueprint_mutation", True)
        ),
        "receipt_no_editor_mutation": bool(evidence_receipt.get("no_editor_mutation", True)),
        "receipt_no_blueprint_mutation": bool(evidence_receipt.get("no_blueprint_mutation", True)),
        "receipt_no_compile": bool(evidence_receipt.get("no_compile", True)),
        "receipt_no_save": bool(evidence_receipt.get("no_save", True)),
        "receipt_no_provider_call": bool(evidence_receipt.get("no_provider_call", True)),
        "receipt_no_git_mutation": bool(evidence_receipt.get("no_git_mutation", True)),
        "blueprint_repair_action_count": len(blueprint_repair_actions),
        "blueprint_repair_action_preview": blueprint_repair_actions[:4],
        "blueprint_repair_gate_preview": bounded_string_preview([action["gate"] for action in blueprint_repair_actions], 5),
        "blueprint_next_repair_action_id": str(blueprint_repair_actions[0]["action_id"] if blueprint_repair_actions else ""),
        "blueprint_next_repair_gate": str(blueprint_repair_actions[0]["gate"] if blueprint_repair_actions else ""),
        "blueprint_next_repair_tool": str(blueprint_repair_actions[0]["recommended_tool"] if blueprint_repair_actions else ""),
        "blueprint_next_repair_review_steps_preview": (
            bounded_string_preview(blueprint_repair_actions[0].get("review_steps_preview", []), 4)
            if blueprint_repair_actions
            else []
        ),
        "pre_read_required": "blueprint_pre_read_evidence" in missing_gate_set or "blueprint_pre_read_evidence" in required_gate_set or "blueprint_pre_read" in evidence_required_set,
        "compile_plan_required": "blueprint_compile_plan" in missing_gate_set or "blueprint_compile_plan" in required_gate_set or "compile_check_after_mutation" in evidence_required_set,
        "readback_plan_required": "blueprint_readback_plan" in missing_gate_set or "blueprint_readback_plan" in required_gate_set or "graph_or_component_readback_after_mutation" in evidence_required_set,
        "bridge_required": "unreal_bridge_reachable" in missing_gate_set or "unreal_bridge_reachable" in required_gate_set,
        "readiness_tool": "gen_compile_ide_companion_readiness",
        "work_order_tool": "skill_compile_ide_companion_work_order",
        "queue_tool": "skill_compile_ide_companion_editor_queue",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "review_tool": "chat_get_cockpit_overview",
        "requires_bridge": True,
        "requires_compile_readback": True,
        "stop_before_blueprint_mutation": True,
    }


def bridge_wrapper_coverage_context() -> Dict[str, Any]:
    audit_path = _REPO_ROOT / "scripts" / "audit_high_value_wrapper_coverage.py"
    if not audit_path.exists():
        return {
            "state": "missing",
            "status": "MISSING",
            "schema": "unreal_mcp_high_value_wrapper_coverage.v1",
            "audit_tool": relative_repo_path(audit_path),
            "missing_preview": ["scripts/audit_high_value_wrapper_coverage.py"],
            "roadmap_priority_count": 0,
            "roadmap_priority_covered_count": 0,
            "roadmap_priority_missing_count": 1,
            "roadmap_priority_preview": [],
            "roadmap_priority_missing_preview": ["scripts/audit_high_value_wrapper_coverage.py"],
            "operator_command_handoff": [],
            "operator_command_handoff_ids": [],
            "operator_command_handoff_count": 0,
            "review_tool": "chat_get_cockpit_overview",
            "requires_bridge": False,
            "no_editor_mutation": True,
        }

    try:
        module_name = "_unreal_mcp_high_value_wrapper_coverage"
        spec = importlib.util.spec_from_file_location(module_name, audit_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load high-value wrapper coverage audit")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        report = module.build_report()
    except Exception as exc:  # pragma: no cover - defensive cockpit fallback
        return {
            "state": "error",
            "status": "ERROR",
            "schema": "unreal_mcp_high_value_wrapper_coverage.v1",
            "audit_tool": relative_repo_path(audit_path),
            "error": str(exc),
            "roadmap_priority_count": 0,
            "roadmap_priority_covered_count": 0,
            "roadmap_priority_missing_count": 1,
            "roadmap_priority_preview": [],
            "roadmap_priority_missing_preview": ["scripts/audit_high_value_wrapper_coverage.py"],
            "operator_command_handoff": [],
            "operator_command_handoff_ids": [],
            "operator_command_handoff_count": 0,
            "review_tool": "chat_get_cockpit_overview",
            "requires_bridge": False,
            "no_editor_mutation": True,
        }

    capabilities = report.get("capabilities") if isinstance(report.get("capabilities"), list) else []
    failing = [entry for entry in capabilities if isinstance(entry, dict) and not entry.get("ok")]
    commands: List[str] = []
    for capability in capabilities:
        if not isinstance(capability, dict):
            continue
        rows = capability.get("commands") if isinstance(capability.get("commands"), list) else []
        for row in rows:
            if isinstance(row, dict):
                command = str(row.get("command", ""))
                if command and command not in commands:
                    commands.append(command)
    roadmap_priority_preview = (
        report.get("roadmap_priority_preview")
        if isinstance(report.get("roadmap_priority_preview"), list)
        else [entry.get("name", "") for entry in capabilities if isinstance(entry, dict)]
    )
    roadmap_priority_missing_preview = (
        report.get("roadmap_priority_missing_preview")
        if isinstance(report.get("roadmap_priority_missing_preview"), list)
        else [entry.get("name", "") for entry in failing if isinstance(entry, dict)]
    )
    operator_command_handoff = (
        [item for item in report.get("operator_command_handoff", [])[:3] if isinstance(item, dict)]
        if isinstance(report.get("operator_command_handoff"), list)
        else []
    )

    return {
        "state": "ok" if report.get("ok") else "attention",
        "status": "OK" if report.get("ok") else "FAIL",
        "schema": str(report.get("schema", "unreal_mcp_high_value_wrapper_coverage.v1")),
        "source_scope": str(report.get("source_scope", "")),
        "capability_count": len(capabilities),
        "covered_capability_count": max(0, len(capabilities) - len(failing)),
        "failing_capability_count": len(failing),
        "command_count": len(commands),
        "schema_command_count": int(report.get("schema_command_count", 0) or 0),
        "schema_covered_command_count": int(report.get("schema_covered_command_count", 0) or 0),
        "command_preview": sorted(commands)[:12],
        "failing_capability_preview": bounded_string_preview([entry.get("name", "") for entry in failing], 8),
        "roadmap_priority_count": int(report.get("roadmap_priority_count", len(capabilities)) or 0),
        "roadmap_priority_covered_count": int(
            report.get("roadmap_priority_covered_count", max(0, len(capabilities) - len(failing))) or 0
        ),
        "roadmap_priority_missing_count": int(report.get("roadmap_priority_missing_count", len(failing)) or 0),
        "roadmap_priority_preview": bounded_string_preview(roadmap_priority_preview, 12),
        "roadmap_priority_missing_preview": bounded_string_preview(roadmap_priority_missing_preview, 8),
        "operator_command_handoff": operator_command_handoff,
        "operator_command_handoff_ids": bounded_string_preview([str(item.get("id", "")) for item in operator_command_handoff], 3),
        "operator_command_handoff_count": len(operator_command_handoff),
        "audit_tool": relative_repo_path(audit_path),
        "bridge_registry_tool": "scripts/bridge_command_audit.py",
        "review_tool": "chat_get_cockpit_overview",
        "requires_bridge": False,
        "no_editor_mutation": True,
    }


def test_lane_context() -> Dict[str, Any]:
    audit_path = _REPO_ROOT / "scripts" / "audit_test_lanes.py"
    no_mutation_receipt_path = _REPO_ROOT / "Saved" / "NoMutationTest" / "last_run_receipt.json"
    no_mutation_operator_command_handoff = [
        {
            "id": "run_no_mutation_unittest",
            "label": "Run no-mutation unittest lane",
            "command": "python scripts\\run_no_mutation_unittest.py",
            "command_kind": "local_validation_receipt",
            "receipt_path": "Saved\\NoMutationTest\\last_run_receipt.json",
            "produces_evidence_for": "no_mutation_test_lane_safe",
            "records_evidence_only": False,
            "requires_bridge": False,
            "requires_provider_network": False,
            "requires_spend": False,
            "no_editor_mutation": True,
            "no_provider_call": True,
            "no_git_mutation": True,
            "no_task_submission": True,
        }
    ]
    if not audit_path.exists():
        return {
            "state": "missing",
            "status": "MISSING",
            "schema": "unreal_mcp_test_lane_audit.v1",
            "audit_tool": relative_repo_path(audit_path),
            "missing_preview": ["scripts/audit_test_lanes.py"],
            "no_mutation_operator_command_handoff": no_mutation_operator_command_handoff,
            "no_mutation_operator_command_handoff_ids": [item["id"] for item in no_mutation_operator_command_handoff],
            "no_mutation_operator_command_handoff_count": len(no_mutation_operator_command_handoff),
            "review_tool": "chat_get_cockpit_overview",
            "requires_bridge": False,
            "no_editor_mutation": True,
        }

    try:
        module_name = "_unreal_mcp_test_lane_audit"
        spec = importlib.util.spec_from_file_location(module_name, audit_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load test lane audit")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        report = module.build_lane_report()
    except Exception as exc:  # pragma: no cover - defensive cockpit fallback
        return {
            "state": "error",
            "status": "ERROR",
            "schema": "unreal_mcp_test_lane_audit.v1",
            "audit_tool": relative_repo_path(audit_path),
            "error": str(exc),
            "no_mutation_operator_command_handoff": no_mutation_operator_command_handoff,
            "no_mutation_operator_command_handoff_ids": [item["id"] for item in no_mutation_operator_command_handoff],
            "no_mutation_operator_command_handoff_count": len(no_mutation_operator_command_handoff),
            "review_tool": "chat_get_cockpit_overview",
            "requires_bridge": False,
            "no_editor_mutation": True,
        }

    counts = report.get("counts") if isinstance(report.get("counts"), dict) else {}
    lanes = report.get("lanes") if isinstance(report.get("lanes"), dict) else {}
    violations = report.get("violations") if isinstance(report.get("violations"), list) else []
    paid_provider_contract = report.get("paid_provider_contract") if isinstance(report.get("paid_provider_contract"), dict) else {}
    try:
        no_mutation_receipt = json.loads(no_mutation_receipt_path.read_text(encoding="utf-8-sig")) if no_mutation_receipt_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        no_mutation_receipt = {}
    no_mutation_status = str(no_mutation_receipt.get("status", "missing") or "missing")
    no_mutation_exit_code = no_mutation_receipt.get("test_exit_code")
    no_mutation_mutation_count = no_mutation_receipt.get("mutation_count")
    no_mutation_tracked_file_count = no_mutation_receipt.get("tracked_file_count")
    try:
        no_mutation_exit_code = int(no_mutation_exit_code) if no_mutation_exit_code is not None else None
    except (TypeError, ValueError):
        no_mutation_exit_code = None
    try:
        no_mutation_mutation_count = int(no_mutation_mutation_count) if no_mutation_mutation_count is not None else None
    except (TypeError, ValueError):
        no_mutation_mutation_count = None
    try:
        no_mutation_tracked_file_count = int(no_mutation_tracked_file_count) if no_mutation_tracked_file_count is not None else None
    except (TypeError, ValueError):
        no_mutation_tracked_file_count = None
    no_mutation_ok = no_mutation_status == "success" and no_mutation_exit_code == 0 and no_mutation_mutation_count == 0
    violation_preview = [
        f"{violation.get('file', '')}: {violation.get('reason', '')}"
        for violation in violations
        if isinstance(violation, dict)
    ]
    return {
        "state": "ok" if report.get("ok") else "attention",
        "status": "OK" if report.get("ok") else "FAIL",
        "schema": str(report.get("schema", "unreal_mcp_test_lane_audit.v1")),
        "test_root": str(report.get("test_root", "")),
        "default_discovery_pattern": str(report.get("default_discovery_pattern", "test_*.py")),
        "offline_count": int(counts.get("offline", 0) or 0),
        "live_bridge_count": int(counts.get("live_bridge", 0) or 0),
        "live_bridge_manual_count": int(counts.get("live_bridge_manual", 0) or 0),
        "paid_provider_count": int(counts.get("paid_provider", 0) or 0),
        "manual_count": int(counts.get("manual", 0) or 0),
        "violation_count": len(violations),
        "violation_preview": bounded_string_preview(violation_preview, 5),
        "offline_preview": bounded_string_preview(lanes.get("offline", []), 5),
        "live_bridge_preview": bounded_string_preview(lanes.get("live_bridge", []), 5),
        "live_bridge_manual_preview": bounded_string_preview(lanes.get("live_bridge_manual", []), 5),
        "paid_provider_preview": bounded_string_preview(lanes.get("paid_provider", []), 5),
        "paid_provider_contract": paid_provider_contract,
        "paid_provider_contract_ok": bool(paid_provider_contract.get("contract_ok", False)) if paid_provider_contract else False,
        "paid_provider_manual_command": str(paid_provider_contract.get("manual_command", "")) if paid_provider_contract else "",
        "paid_provider_required_env_vars": bounded_string_preview(paid_provider_contract.get("required_env_vars", []), 5) if isinstance(paid_provider_contract.get("required_env_vars"), list) else [],
        "paid_provider_optional_env_vars": bounded_string_preview(paid_provider_contract.get("optional_env_vars", []), 3) if isinstance(paid_provider_contract.get("optional_env_vars"), list) else [],
        "paid_provider_no_spend_tools": bounded_string_preview(paid_provider_contract.get("no_spend_tools", []), 5) if isinstance(paid_provider_contract.get("no_spend_tools"), list) else [],
        "paid_provider_forbidden_tokens_present": bounded_string_preview(paid_provider_contract.get("forbidden_tokens_present", []), 5) if isinstance(paid_provider_contract.get("forbidden_tokens_present"), list) else [],
        "paid_provider_default_ci_network_required": bool(paid_provider_contract.get("default_ci_network_required", False)) if paid_provider_contract else False,
        "paid_provider_manual_network_required": bool(paid_provider_contract.get("manual_network_required", False)) if paid_provider_contract else False,
        "paid_provider_manual_spend_required": bool(paid_provider_contract.get("manual_spend_required", False)) if paid_provider_contract else False,
        "paid_provider_no_task_submission": bool(paid_provider_contract.get("no_task_submission", True)) if paid_provider_contract else True,
        "paid_provider_no_download": bool(paid_provider_contract.get("no_download", True)) if paid_provider_contract else True,
        "paid_provider_no_import": bool(paid_provider_contract.get("no_import", True)) if paid_provider_contract else True,
        "audit_tool": relative_repo_path(audit_path),
        "ci_doc": "docs/ci-smoke.md",
        "default_ci_safe": bool(report.get("ok")),
        "no_mutation_receipt_schema": str(no_mutation_receipt.get("schema", "unreal_mcp_no_mutation_unittest_receipt.v1")),
        "no_mutation_receipt_exists": no_mutation_receipt_path.exists(),
        "no_mutation_receipt_path": relative_repo_path(no_mutation_receipt_path),
        "no_mutation_state": "ok" if no_mutation_ok else ("missing" if not no_mutation_receipt else "blocked"),
        "no_mutation_status": no_mutation_status,
        "no_mutation_ok": no_mutation_ok,
        "no_mutation_exit_code": no_mutation_exit_code,
        "no_mutation_mutation_count": no_mutation_mutation_count,
        "no_mutation_tracked_file_count": no_mutation_tracked_file_count,
        "no_mutation_snapshot_digest_match": bool(no_mutation_receipt.get("snapshot_digest_match", False)),
        "no_mutation_snapshot_scope": str(no_mutation_receipt.get("snapshot_scope", "")),
        "no_mutation_snapshot_hash_algorithm": str(no_mutation_receipt.get("snapshot_hash_algorithm", "")),
        "no_mutation_required_command": "python scripts\\run_no_mutation_unittest.py",
        "no_mutation_operator_command_handoff": no_mutation_operator_command_handoff,
        "no_mutation_operator_command_handoff_ids": [item["id"] for item in no_mutation_operator_command_handoff],
        "no_mutation_operator_command_handoff_count": len(no_mutation_operator_command_handoff),
        "requires_bridge": False,
        "future_bridge_required": True,
        "future_spend_required": True,
        "review_tool": "chat_get_cockpit_overview",
        "no_editor_mutation": True,
    }


def platform_preflight_context() -> Dict[str, Any]:
    audit_path = _REPO_ROOT / "scripts" / "audit_ide_companion_readiness.py"
    if not audit_path.exists():
        return {
            "state": "missing",
            "status": "MISSING",
            "schema": "unreal_mcp_ide_companion_preflight.v1",
            "audit_tool": relative_repo_path(audit_path),
            "missing_preview": ["scripts/audit_ide_companion_readiness.py"],
            "review_tool": "chat_get_cockpit_overview",
            "requires_bridge": False,
            "no_editor_mutation": True,
        }

    try:
        module_name = "_unreal_mcp_ide_companion_readiness"
        spec = importlib.util.spec_from_file_location(module_name, audit_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load IDE companion readiness audit")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        report = module.build_report(timeout_s=0.1)
    except Exception as exc:  # pragma: no cover - defensive cockpit fallback
        return {
            "state": "error",
            "status": "ERROR",
            "schema": "unreal_mcp_ide_companion_preflight.v1",
            "audit_tool": relative_repo_path(audit_path),
            "error": str(exc),
            "review_tool": "chat_get_cockpit_overview",
            "requires_bridge": False,
            "no_editor_mutation": True,
        }

    tool_inventory = report.get("tool_inventory") if isinstance(report.get("tool_inventory"), dict) else {}
    git = report.get("git") if isinstance(report.get("git"), dict) else {}
    bridge = report.get("bridge") if isinstance(report.get("bridge"), dict) else {}
    chat = report.get("chat") if isinstance(report.get("chat"), dict) else {}
    chat_repair = report.get("chat_cockpit_repair_contract") if isinstance(report.get("chat_cockpit_repair_contract"), dict) else {}
    repair_queue = report.get("readiness_repair_queue") if isinstance(report.get("readiness_repair_queue"), dict) else {}
    provider = report.get("provider_config") if isinstance(report.get("provider_config"), dict) else {}
    test_lanes = report.get("test_lanes") if isinstance(report.get("test_lanes"), dict) else {}
    no_mutation_tests = report.get("no_mutation_tests") if isinstance(report.get("no_mutation_tests"), dict) else {}
    high_value_wrapper_coverage = report.get("high_value_wrapper_coverage") if isinstance(report.get("high_value_wrapper_coverage"), dict) else {}
    dirty_promotion = report.get("dirty_promotion_contract") if isinstance(report.get("dirty_promotion_contract"), dict) else {}
    platform_stability_review = report.get("platform_stability_review") if isinstance(report.get("platform_stability_review"), dict) else {}
    build = report.get("build") if isinstance(report.get("build"), dict) else {}
    readiness_policy = report.get("readiness_policy") if isinstance(report.get("readiness_policy"), dict) else {}
    paid_generation_evidence = report.get("paid_generation_evidence") if isinstance(report.get("paid_generation_evidence"), dict) else {}
    blueprint_mutation_evidence = report.get("blueprint_mutation_evidence") if isinstance(report.get("blueprint_mutation_evidence"), dict) else {}
    branch = git.get("branch") if isinstance(git.get("branch"), dict) else {}
    paid_generation = readiness_policy.get("paid_generation") if isinstance(readiness_policy.get("paid_generation"), dict) else {}
    paid_animation_generation = readiness_policy.get("paid_animation_generation") if isinstance(readiness_policy.get("paid_animation_generation"), dict) else {}
    blueprint_mutation = readiness_policy.get("blueprint_mutation") if isinstance(readiness_policy.get("blueprint_mutation"), dict) else {}
    platform_stability = readiness_policy.get("platform_stability") if isinstance(readiness_policy.get("platform_stability"), dict) else {}
    wip_promotion = readiness_policy.get("wip_promotion") if isinstance(readiness_policy.get("wip_promotion"), dict) else {}
    provider_repair = provider.get("repair_contract") if isinstance(provider.get("repair_contract"), dict) else {}
    provider_secret_contract = provider.get("secret_contract") if isinstance(provider.get("secret_contract"), dict) else {}
    blocking_gates = report.get("blocking_gates") if isinstance(report.get("blocking_gates"), list) else []
    blueprint_blocking_gates = (
        blueprint_mutation.get("missing_gates")
        if isinstance(blueprint_mutation.get("missing_gates"), list)
        else []
    )
    combined_blocking_gates = list(dict.fromkeys(
        str(gate).strip()
        for gate in [*blocking_gates, *blueprint_blocking_gates]
        if str(gate).strip()
    ))
    state = "ready" if report.get("ready_for_editor_mutation") and report.get("ready_for_chat_cockpit") and report.get("ready_for_platform_stability", True) else "blocked"
    repair_next_action = repair_queue.get("next_action") if isinstance(repair_queue.get("next_action"), dict) else {}
    repair_next_operator_command_handoff = (
        list(repair_queue.get("next_operator_command_handoff", []))[:2]
        if isinstance(repair_queue.get("next_operator_command_handoff"), list)
        else []
    ) or (
        list(repair_next_action.get("operator_command_handoff", []))[:2]
        if isinstance(repair_next_action.get("operator_command_handoff"), list)
        else []
    ) or (
        list(repair_next_action.get("target_review_human_approval_command_handoff", []))[:1]
        if (
            repair_next_action.get("target_review_pending_human_approval_only")
            and isinstance(repair_next_action.get("target_review_human_approval_command_handoff"), list)
        )
        else []
    ) or (
        list(repair_next_action.get("target_review_operator_command_handoff", []))[:2]
        if isinstance(repair_next_action.get("target_review_operator_command_handoff"), list)
        else []
    )
    queue_repair_preview = repair_queue.get("action_preview")
    receipt_repair_preview = platform_stability_review.get("readiness_repair_action_preview")
    repair_action_preview = (
        queue_repair_preview
        if isinstance(queue_repair_preview, list)
        else (receipt_repair_preview if isinstance(receipt_repair_preview, list) else [])
    )
    return {
        "state": state,
        "status": "READY" if state == "ready" else "BLOCKED",
        "schema": str(report.get("schema", "unreal_mcp_ide_companion_preflight.v1")),
        "ready_for_editor_mutation": bool(report.get("ready_for_editor_mutation", False)),
        "ready_for_paid_generation": bool(report.get("ready_for_paid_generation", False)),
        "ready_for_paid_animation_generation": bool(report.get("ready_for_paid_animation_generation", False)),
        "ready_for_blueprint_mutation": bool(report.get("ready_for_blueprint_mutation", False)),
        "ready_for_chat_cockpit": bool(report.get("ready_for_chat_cockpit", False)),
        "ready_for_platform_stability": bool(report.get("ready_for_platform_stability", False)),
        "ready_for_wip_promotion": bool(report.get("ready_for_wip_promotion", False)),
        "blocking_gate_count": len(combined_blocking_gates),
        "blocking_gate_preview": bounded_string_preview(combined_blocking_gates, 12),
        "readiness_repair_action_count": int(
            repair_queue.get("action_count")
            or platform_stability_review.get("readiness_repair_action_count", 0)
            or 0
        ),
        "readiness_repair_recommended_next": str(
            repair_queue.get("recommended_next")
            or platform_stability_review.get("readiness_repair_recommended_next", "none")
        ),
        "readiness_repair_next_gate": str(
            repair_next_action.get("gate")
            or platform_stability_review.get("readiness_repair_next_gate", "")
        ),
        "readiness_repair_next_policy_area": str(
            repair_next_action.get("policy_area")
            or platform_stability_review.get("readiness_repair_next_policy_area", "")
        ),
        "readiness_repair_next_tool": str(
            repair_next_action.get("recommended_tool")
            or platform_stability_review.get("readiness_repair_next_tool", "")
        ),
        "readiness_repair_next_requires_bridge": bool(
            repair_next_action.get("requires_bridge", False)
            or platform_stability_review.get("readiness_repair_next_requires_bridge", False)
        ),
        "readiness_repair_next_requires_network": bool(
            repair_next_action.get("requires_network", False)
            or platform_stability_review.get("readiness_repair_next_requires_network", False)
        ),
        "readiness_repair_next_requires_spend": bool(
            repair_next_action.get("requires_spend", False)
            or platform_stability_review.get("readiness_repair_next_requires_spend", False)
        ),
        "readiness_repair_action_preview": [
            item for item in repair_action_preview[:8] if isinstance(item, dict)
        ],
        "readiness_repair_queue": {
            "schema": str(repair_queue.get("schema", "unreal_mcp_readiness_repair_queue.v1")),
            "state": str(repair_queue.get("state", "")),
            "action_count": int(repair_queue.get("action_count", 0) or 0),
            "blocking_gate_count": int(repair_queue.get("blocking_gate_count", 0) or 0),
            "blocking_gate_preview": bounded_string_preview(repair_queue.get("blocking_gate_preview", []), 8),
            "recommended_next": str(repair_queue.get("recommended_next", "none")),
            "next_action": repair_queue.get("next_action") if isinstance(repair_queue.get("next_action"), dict) else {},
            "next_operator_command_handoff": repair_next_operator_command_handoff,
            "action_preview": list(repair_queue.get("action_preview", []))[:8] if isinstance(repair_queue.get("action_preview"), list) else [],
            "no_auto_execute": bool(repair_queue.get("no_auto_execute", True)),
            "no_secret_echo": bool(repair_queue.get("no_secret_echo", True)),
            "no_git_mutation": bool(repair_queue.get("no_git_mutation", True)),
            "no_editor_mutation": bool(repair_queue.get("no_editor_mutation", True)),
            "network_required_for_next_action": bool(repair_queue.get("network_required_for_next_action", False)),
            "spend_required_for_next_action": bool(repair_queue.get("spend_required_for_next_action", False)),
            "unreal_editor_required_for_next_action": bool(repair_queue.get("unreal_editor_required_for_next_action", False)),
            "priority_policy": str(repair_queue.get("priority_policy", "chat_health_then_wip_promotion_safety_then_bridge_proof_then_paid_provider_gates")),
        },
        "tool_count": int(tool_inventory.get("tool_count", 0) or 0),
        "recorded_count": int(tool_inventory.get("recorded_count", 0) or 0),
        "tool_registry_reproducible": bool(tool_inventory.get("matches_recorded_count", False)) and not bool(tool_inventory.get("missing_category_modules", [])),
        "partial_tool_count": int(tool_inventory.get("partial_tools", 0) or 0),
        "module_count": int(tool_inventory.get("module_count", 0) or 0),
        "dirty_risk": str(git.get("dirty_risk", "unknown")),
        "dirty_count": int(git.get("dirty_count", 0) or 0) if git.get("dirty_count") is not None else 0,
        "tracked_change_count": int(git.get("tracked_change_count", 0) or 0),
        "untracked_count": int(git.get("untracked_count", 0) or 0),
        "dirty_group_count": int(git.get("dirty_group_count", 0) or 0),
        "dirty_group_preview": list(git.get("dirty_group_preview", []))[:6] if isinstance(git.get("dirty_group_preview"), list) else [],
        "primary_dirty_group": str(git.get("primary_dirty_group", "")),
        "dirty_grouping_required": bool(git.get("dirty_grouping_required", False)),
        "dirty_promotion_contract": {
            "schema": str(dirty_promotion.get("schema", "unreal_mcp_dirty_promotion_contract.v1")),
            "state": str(dirty_promotion.get("state", "")),
            "ready_for_promotion": bool(dirty_promotion.get("ready_for_promotion", False)),
            "dirty_risk": str(dirty_promotion.get("dirty_risk", "")),
            "dirty_group_count": int(dirty_promotion.get("dirty_group_count", 0) or 0),
            "dirty_signature": str(dirty_promotion.get("dirty_signature", "")),
            "dirty_signature_algorithm": str(dirty_promotion.get("dirty_signature_algorithm", "")),
            "dirty_signature_entry_count": int(dirty_promotion.get("dirty_signature_entry_count", 0) or 0),
            "tracked_change_count": int(dirty_promotion.get("tracked_change_count", 0) or 0),
            "untracked_count": int(dirty_promotion.get("untracked_count", 0) or 0),
            "primary_dirty_group": str(dirty_promotion.get("primary_dirty_group", "")),
            "review_batch_count": int(dirty_promotion.get("review_batch_count", 0) or 0),
            "review_batch_preview": list(dirty_promotion.get("review_batches", []))[:5] if isinstance(dirty_promotion.get("review_batches"), list) else [],
            "evidence_review_matrix_count": int(dirty_promotion.get("evidence_review_matrix_count", 0) or 0),
            "evidence_review_matrix_preview": list(dirty_promotion.get("evidence_review_matrix", []))[:5] if isinstance(dirty_promotion.get("evidence_review_matrix"), list) else [],
            "evidence_unresolved_count": int(dirty_promotion.get("evidence_unresolved_count", 0) or 0),
            "evidence_review_policy": str(dirty_promotion.get("evidence_review_policy", "")),
            "focused_test_command_count": int(dirty_promotion.get("focused_test_command_count", 0) or 0),
            "focused_test_command_preview": bounded_string_preview(dirty_promotion.get("focused_test_command_preview", []), 8),
            "target_review_group": str(dirty_promotion.get("target_review_group", "")),
            "target_review_order": int(dirty_promotion.get("target_review_order", 0) or 0),
            "target_review_scope": str(dirty_promotion.get("target_review_scope", "")),
            "target_review_tracked_count": int(dirty_promotion.get("target_review_tracked_count", 0) or 0),
            "target_review_untracked_count": int(dirty_promotion.get("target_review_untracked_count", 0) or 0),
            "target_review_missing_evidence_count": int(dirty_promotion.get("target_review_missing_evidence_count", 0) or 0),
            "target_review_status": str(dirty_promotion.get("target_review_status") or "missing_evidence"),
            "target_review_evidence_complete": bool(dirty_promotion.get("target_review_evidence_complete", False)),
            "target_review_recorded_evidence_count": int(dirty_promotion.get("target_review_recorded_evidence_count", 0) or 0),
            "target_review_recorded_evidence_preview": bounded_string_preview(dirty_promotion.get("target_review_recorded_evidence_preview", []), 8),
            "target_review_human_approval_recorded": bool(dirty_promotion.get("target_review_human_approval_recorded", False)),
            "target_review_missing_evidence_preview": bounded_string_preview(dirty_promotion.get("target_review_missing_evidence_preview", []), 8),
            "target_review_required_evidence_preview": bounded_string_preview(dirty_promotion.get("target_review_required_evidence_preview", []), 8),
            "target_review_decision_prompt_preview": bounded_string_preview(dirty_promotion.get("target_review_decision_prompt_preview", []), 8),
            "target_review_receipt_command_template": str(dirty_promotion.get("target_review_receipt_command_template", "")),
            "target_review_approval_receipt_command_template": str(
                dirty_promotion.get("target_review_approval_receipt_command_template", "")
            ),
            "target_review_receipt_command_policy": str(dirty_promotion.get("target_review_receipt_command_policy", "")),
            "target_review_operator_command_handoff": (
                list(dirty_promotion.get("target_review_operator_command_handoff", []))[:2]
                if isinstance(dirty_promotion.get("target_review_operator_command_handoff"), list)
                else []
            ),
            "target_review_pending_human_approval_only": bool(dirty_promotion.get("target_review_pending_human_approval_only", False)),
            "target_review_human_approval_gate": str(dirty_promotion.get("target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
            "target_review_human_approval_command_handoff": (
                list(dirty_promotion.get("target_review_human_approval_command_handoff", []))[:1]
                if isinstance(dirty_promotion.get("target_review_human_approval_command_handoff"), list)
                else []
            ),
            "target_review_focused_test_command_handoff": (
                list(dirty_promotion.get("target_review_focused_test_command_handoff", []))[:5]
                if isinstance(dirty_promotion.get("target_review_focused_test_command_handoff"), list)
                else []
            ),
            "target_review_focused_test_command_count": int(dirty_promotion.get("target_review_focused_test_command_count", 0) or 0),
            "target_review_focused_test_command_preview": bounded_string_preview(dirty_promotion.get("target_review_focused_test_command_preview", []), 5),
            "target_review_sample_preview": bounded_string_preview(dirty_promotion.get("target_review_sample_preview", []), 5),
            "target_review_promotion_allowed_after_receipt": bool(dirty_promotion.get("target_review_promotion_allowed_after_receipt", False)),
            "target_review_merge_policy": str(dirty_promotion.get("target_review_merge_policy", "")),
            "target_review_previous_evidence_merged": bool(dirty_promotion.get("target_review_previous_evidence_merged", False)),
            "target_review_reset_evidence": bool(dirty_promotion.get("target_review_reset_evidence", False)),
            "target_review_source": str(dirty_promotion.get("target_review_source", "")),
            "candidate_batch_review_policy": str(dirty_promotion.get("candidate_batch_review_policy", "")),
            "review_receipt_exists": bool(dirty_promotion.get("review_receipt_exists", False)),
            "review_receipt_state": str(dirty_promotion.get("review_receipt_state", "missing")),
            "review_receipt_current": bool(dirty_promotion.get("review_receipt_current", False)),
            "review_receipt_stale": bool(dirty_promotion.get("review_receipt_stale", False)),
            "review_receipt_dirty_signature_match": bool(dirty_promotion.get("review_receipt_dirty_signature_match", False)),
            "review_receipt_path": str(dirty_promotion.get("review_receipt_path", "Saved\\DirtyPromotionReview\\last_review_receipt.json")),
            "review_receipt_required_command": str(dirty_promotion.get("review_receipt_required_command", "python scripts\\write_dirty_promotion_review.py")),
            "required_evidence_preview": bounded_string_preview(dirty_promotion.get("required_evidence", []), 8),
            "promotion_batch_policy": str(dirty_promotion.get("promotion_batch_policy", "")),
            "artifact_policy": str(dirty_promotion.get("artifact_policy", "")),
            "safe_promotion_next_steps": bounded_string_preview(dirty_promotion.get("safe_promotion_next_steps", []), 8),
            "recommended_next": str(dirty_promotion.get("recommended_next", "")),
            "no_git_mutation": bool(dirty_promotion.get("no_git_mutation", True)),
            "no_stage": bool(dirty_promotion.get("no_stage", True)),
            "no_commit": bool(dirty_promotion.get("no_commit", True)),
            "no_clean": bool(dirty_promotion.get("no_clean", True)),
            "no_delete": bool(dirty_promotion.get("no_delete", True)),
            "no_branch_or_merge": bool(dirty_promotion.get("no_branch_or_merge", True)),
            "no_provider_call": bool(dirty_promotion.get("no_provider_call", True)),
            "no_editor_mutation": bool(dirty_promotion.get("no_editor_mutation", True)),
        },
        "platform_stability_review": {
            "schema": str(platform_stability_review.get("schema", "unreal_mcp_platform_stability_review_receipt.v1")),
            "state": str(platform_stability_review.get("state", "missing")),
            "status": str(platform_stability_review.get("status", "missing")),
            "receipt_exists": bool(platform_stability_review.get("receipt_exists", False)),
            "path": str(platform_stability_review.get("path", "Saved\\PlatformStabilityReview\\last_review_receipt.json")),
            "required_command": str(platform_stability_review.get("required_command", "python scripts\\write_platform_stability_review.py")),
            "ready_for_platform_stability": bool(platform_stability_review.get("ready_for_platform_stability", False)),
            "ready_for_wip_promotion": bool(platform_stability_review.get("ready_for_wip_promotion", False)),
            "platform_missing_gate_count": platform_stability_review.get("platform_missing_gate_count"),
            "wip_promotion_missing_gate_count": platform_stability_review.get("wip_promotion_missing_gate_count"),
            "blocking_gate_count": len(combined_blocking_gates),
            "blocking_gate_preview": bounded_string_preview(
                combined_blocking_gates or platform_stability_review.get("blocking_gate_preview", []),
                12,
            ),
            "readiness_repair_action_count": int(repair_queue.get("action_count", 0) or 0),
            "readiness_repair_recommended_next": str(repair_queue.get("recommended_next", "")),
            "readiness_repair_next_gate": str(repair_next_action.get("gate", "")),
            "readiness_repair_next_policy_area": str(repair_next_action.get("policy_area", "")),
            "readiness_repair_next_tool": str(repair_next_action.get("recommended_tool", "")),
            "readiness_repair_next_requires_bridge": bool(repair_next_action.get("requires_bridge", False)),
            "readiness_repair_next_requires_network": bool(repair_next_action.get("requires_network", False)),
            "readiness_repair_next_requires_spend": bool(repair_next_action.get("requires_spend", False)),
            "readiness_repair_action_preview": [
                item for item in repair_action_preview[:8] if isinstance(item, dict)
            ],
            "dirty_promotion_review_receipt_state": str(platform_stability_review.get("dirty_promotion_review_receipt_state", "missing")),
            "dirty_promotion_review_receipt_current": bool(platform_stability_review.get("dirty_promotion_review_receipt_current", False)),
            "dirty_promotion_review_receipt_stale": bool(platform_stability_review.get("dirty_promotion_review_receipt_stale", False)),
            "dirty_promotion_review_receipt_signature_match": bool(platform_stability_review.get("dirty_promotion_review_receipt_signature_match", False)),
            "dirty_signature_algorithm": str(platform_stability_review.get("dirty_signature_algorithm", "")),
            "dirty_signature_entry_count": int(platform_stability_review.get("dirty_signature_entry_count", 0) or 0),
            "dirty_promotion_review_batch_count": int(platform_stability_review.get("dirty_promotion_review_batch_count", 0) or 0),
            "dirty_promotion_evidence_unresolved_count": int(platform_stability_review.get("dirty_promotion_evidence_unresolved_count", 0) or 0),
            "dirty_target_review_group": str(platform_stability_review.get("dirty_target_review_group", "")),
            "dirty_target_review_order": int(platform_stability_review.get("dirty_target_review_order", 0) or 0),
            "dirty_target_review_scope": str(platform_stability_review.get("dirty_target_review_scope", "")),
            "dirty_target_review_tracked_count": int(platform_stability_review.get("dirty_target_review_tracked_count", 0) or 0),
            "dirty_target_review_untracked_count": int(platform_stability_review.get("dirty_target_review_untracked_count", 0) or 0),
            "dirty_target_review_status": str(platform_stability_review.get("dirty_target_review_status") or "missing_evidence"),
            "dirty_target_review_evidence_complete": bool(platform_stability_review.get("dirty_target_review_evidence_complete", False)),
            "dirty_target_review_recorded_evidence_count": int(platform_stability_review.get("dirty_target_review_recorded_evidence_count", 0) or 0),
            "dirty_target_review_recorded_evidence_preview": bounded_string_preview(platform_stability_review.get("dirty_target_review_recorded_evidence_preview", []), 8),
            "dirty_target_review_human_approval_recorded": bool(platform_stability_review.get("dirty_target_review_human_approval_recorded", False)),
            "dirty_target_review_missing_evidence_count": int(platform_stability_review.get("dirty_target_review_missing_evidence_count", 0) or 0),
            "dirty_target_review_missing_evidence_preview": bounded_string_preview(platform_stability_review.get("dirty_target_review_missing_evidence_preview", []), 8),
            "dirty_target_review_required_evidence_preview": bounded_string_preview(platform_stability_review.get("dirty_target_review_required_evidence_preview", []), 8),
            "dirty_target_review_decision_prompt_preview": bounded_string_preview(platform_stability_review.get("dirty_target_review_decision_prompt_preview", []), 8),
            "dirty_target_review_receipt_command_template": str(platform_stability_review.get("dirty_target_review_receipt_command_template", "")),
            "dirty_target_review_approval_receipt_command_template": str(platform_stability_review.get("dirty_target_review_approval_receipt_command_template", "")),
            "dirty_target_review_receipt_command_policy": str(platform_stability_review.get("dirty_target_review_receipt_command_policy", "")),
            "dirty_target_review_operator_command_handoff": (
                list(platform_stability_review.get("dirty_target_review_operator_command_handoff", []))[:2]
                if isinstance(platform_stability_review.get("dirty_target_review_operator_command_handoff"), list)
                else []
            ),
            "dirty_target_review_pending_human_approval_only": bool(platform_stability_review.get("dirty_target_review_pending_human_approval_only", False)),
            "dirty_target_review_human_approval_gate": str(platform_stability_review.get("dirty_target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
            "dirty_target_review_human_approval_command_handoff": (
                list(platform_stability_review.get("dirty_target_review_human_approval_command_handoff", []))[:1]
                if isinstance(platform_stability_review.get("dirty_target_review_human_approval_command_handoff"), list)
                else []
            ),
            "dirty_target_review_focused_test_command_handoff": (
                list(platform_stability_review.get("dirty_target_review_focused_test_command_handoff", []))[:5]
                if isinstance(platform_stability_review.get("dirty_target_review_focused_test_command_handoff"), list)
                else []
            ),
            "dirty_target_review_focused_test_command_count": int(platform_stability_review.get("dirty_target_review_focused_test_command_count", 0) or 0),
            "dirty_target_review_focused_test_command_preview": bounded_string_preview(platform_stability_review.get("dirty_target_review_focused_test_command_preview", []), 5),
            "dirty_target_review_sample_preview": bounded_string_preview(platform_stability_review.get("dirty_target_review_sample_preview", []), 5),
            "dirty_target_review_promotion_allowed_after_receipt": bool(platform_stability_review.get("dirty_target_review_promotion_allowed_after_receipt", False)),
            "dirty_target_review_merge_policy": str(platform_stability_review.get("dirty_target_review_merge_policy", "")),
            "dirty_target_review_previous_evidence_merged": bool(platform_stability_review.get("dirty_target_review_previous_evidence_merged", False)),
            "dirty_target_review_reset_evidence": bool(platform_stability_review.get("dirty_target_review_reset_evidence", False)),
            "tool_registry_reproducible": bool(
                platform_stability_review.get("tool_registry_reproducible", False)
                or (tool_inventory.get("matches_recorded_count", False) and not tool_inventory.get("missing_category_modules", []))
            ),
            "tool_count": int(platform_stability_review.get("tool_count", 0) or tool_inventory.get("tool_count", 0) or 0),
            "recorded_tool_count": int(platform_stability_review.get("recorded_tool_count", 0) or tool_inventory.get("recorded_count", 0) or 0),
            "partial_tool_count": int(platform_stability_review.get("partial_tool_count", 0) or tool_inventory.get("partial_tools", 0) or 0),
            "paid_provider_smoke_contract_ok": bool(platform_stability_review.get("paid_provider_smoke_contract_ok", False)),
            "paid_provider_smoke_manual_command": str(platform_stability_review.get("paid_provider_smoke_manual_command", "")),
            "paid_provider_smoke_required_env_vars": bounded_string_preview(platform_stability_review.get("paid_provider_smoke_required_env_vars", []), 5),
            "paid_provider_smoke_no_spend_tools": bounded_string_preview(platform_stability_review.get("paid_provider_smoke_no_spend_tools", []), 5),
            "paid_provider_smoke_forbidden_tokens_present": bounded_string_preview(platform_stability_review.get("paid_provider_smoke_forbidden_tokens_present", []), 8),
            "paid_provider_smoke_manual_spend_required": bool(platform_stability_review.get("paid_provider_smoke_manual_spend_required", False)),
            "paid_provider_smoke_no_task_submission": bool(platform_stability_review.get("paid_provider_smoke_no_task_submission", True)),
            "paid_provider_smoke_no_download": bool(platform_stability_review.get("paid_provider_smoke_no_download", True)),
            "paid_provider_smoke_no_import": bool(platform_stability_review.get("paid_provider_smoke_no_import", True)),
            "paid_generation_evidence_receipt_state": str(
                platform_stability_review.get("paid_generation_evidence_receipt_state")
                or paid_generation_evidence.get("review_receipt_state", "missing")
            ),
            "paid_generation_evidence_receipt_path": str(
                platform_stability_review.get("paid_generation_evidence_receipt_path")
                or paid_generation_evidence.get("review_receipt_path", "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
            ),
            "paid_generation_evidence_required_command": str(
                platform_stability_review.get("paid_generation_evidence_required_command")
                or paid_generation_evidence.get("review_receipt_required_command", "python scripts\\write_paid_generation_evidence_review.py")
            ),
            "paid_generation_wallet_evidence_recorded": bool(
                platform_stability_review.get("paid_generation_wallet_evidence_recorded", False)
                or paid_generation_evidence.get("wallet_evidence_recorded", False)
            ),
            "paid_generation_mesh_wallet_evidence_recorded": bool(
                platform_stability_review.get("paid_generation_mesh_wallet_evidence_recorded", False)
                or paid_generation_evidence.get("mesh_wallet_evidence_recorded", False)
            ),
            "paid_generation_animation_allowance_evidence_recorded": bool(
                platform_stability_review.get("paid_generation_animation_allowance_evidence_recorded", False)
                or paid_generation_evidence.get("animation_allowance_evidence_recorded", False)
            ),
            "paid_generation_spend_confirmation_recorded": bool(
                platform_stability_review.get("paid_generation_spend_confirmation_recorded", False)
                or paid_generation_evidence.get("spend_confirmation_recorded", False)
            ),
            "paid_generation_explicit_spend_approval_recorded": bool(
                platform_stability_review.get("paid_generation_explicit_spend_approval_recorded", False)
                or paid_generation_evidence.get("explicit_spend_approval_recorded", False)
            ),
            "paid_generation_explicit_usage_approval_recorded": bool(
                platform_stability_review.get("paid_generation_explicit_usage_approval_recorded", False)
                or paid_generation_evidence.get("explicit_usage_approval_recorded", False)
            ),
            "paid_generation_estimated_spend_reviewed": bool(
                platform_stability_review.get("paid_generation_estimated_spend_reviewed", False)
                or paid_generation_evidence.get("estimated_spend_reviewed", False)
            ),
            "paid_generation_estimated_motion_seconds_reviewed": bool(
                platform_stability_review.get("paid_generation_estimated_motion_seconds_reviewed", False)
                or paid_generation_evidence.get("estimated_motion_seconds_reviewed", False)
            ),
            "paid_generation_mesh_provider": str(
                platform_stability_review.get("paid_generation_mesh_provider")
                or paid_generation_evidence.get("mesh_provider", "tripo")
            ),
            "paid_generation_animation_provider": str(
                platform_stability_review.get("paid_generation_animation_provider")
                or paid_generation_evidence.get("animation_provider", "uthana")
            ),
            "paid_generation_operator_command_handoff": (
                list(platform_stability_review.get("paid_generation_operator_command_handoff") or paid_generation_evidence.get("operator_command_handoff", []))[:3]
                if isinstance(platform_stability_review.get("paid_generation_operator_command_handoff") or paid_generation_evidence.get("operator_command_handoff", []), list)
                else []
            ),
            "provider_config_operator_command_handoff": (
                list(platform_stability_review.get("provider_config_operator_command_handoff") or provider.get("operator_command_handoff", []))[:1]
                if isinstance(platform_stability_review.get("provider_config_operator_command_handoff") or provider.get("operator_command_handoff", []), list)
                else []
            ),
            "provider_config_operator_command_handoff_ids": bounded_string_preview(
                platform_stability_review.get("provider_config_operator_command_handoff_ids") or provider.get("operator_command_handoff_ids", []),
                1,
            ),
            "provider_config_operator_command_handoff_count": int(
                platform_stability_review.get("provider_config_operator_command_handoff_count", 0)
                or provider.get("operator_command_handoff_count", 0)
                or 0
            ),
            "blueprint_mutation_evidence_receipt_state": str(platform_stability_review.get("blueprint_mutation_evidence_receipt_state", "missing")),
            "blueprint_mutation_evidence_receipt_status": str(platform_stability_review.get("blueprint_mutation_evidence_receipt_status", "missing")),
            "blueprint_mutation_evidence_receipt_path": str(platform_stability_review.get("blueprint_mutation_evidence_receipt_path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")),
            "blueprint_mutation_evidence_required_command": str(platform_stability_review.get("blueprint_mutation_evidence_required_command", "python scripts\\write_blueprint_mutation_evidence_review.py")),
            "blueprint_mutation_operator_command_handoff": (
                list(platform_stability_review.get("blueprint_mutation_operator_command_handoff") or report.get("blueprint_mutation_operator_command_handoff", []))[:3]
                if isinstance(platform_stability_review.get("blueprint_mutation_operator_command_handoff") or report.get("blueprint_mutation_operator_command_handoff", []), list)
                else []
            ),
            "blueprint_mutation_pre_read_evidence_recorded": bool(platform_stability_review.get("blueprint_mutation_pre_read_evidence_recorded", False)),
            "blueprint_mutation_compile_plan_recorded": bool(platform_stability_review.get("blueprint_mutation_compile_plan_recorded", False)),
            "blueprint_mutation_readback_plan_recorded": bool(platform_stability_review.get("blueprint_mutation_readback_plan_recorded", False)),
            "blueprint_mutation_target_blueprint_path": str(platform_stability_review.get("blueprint_mutation_target_blueprint_path", "")),
            "blueprint_mutation_intended_summary": str(platform_stability_review.get("blueprint_mutation_intended_summary", "")),
            "blueprint_mutation_evidence_required_preview": bounded_string_preview(platform_stability_review.get("blueprint_mutation_evidence_required_preview", []), 8),
            "blueprint_mutation_evidence_merge_policy": str(platform_stability_review.get("blueprint_mutation_evidence_merge_policy", "preserve_existing_evidence_unless_reset")),
            "blueprint_mutation_human_approval_required": bool(platform_stability_review.get("blueprint_mutation_human_approval_required", True)),
            "blueprint_mutation_evidence_no_editor_mutation": bool(platform_stability_review.get("blueprint_mutation_evidence_no_editor_mutation", True)),
            "blueprint_mutation_evidence_no_blueprint_mutation": bool(platform_stability_review.get("blueprint_mutation_evidence_no_blueprint_mutation", True)),
            "blueprint_mutation_evidence_no_compile": bool(platform_stability_review.get("blueprint_mutation_evidence_no_compile", True)),
            "blueprint_mutation_evidence_no_save": bool(platform_stability_review.get("blueprint_mutation_evidence_no_save", True)),
            "blueprint_mutation_evidence_no_pie": bool(platform_stability_review.get("blueprint_mutation_evidence_no_pie", True)),
            "no_provider_call": bool(platform_stability_review.get("no_provider_call", True)),
            "no_editor_mutation": bool(platform_stability_review.get("no_editor_mutation", True)),
            "no_git_mutation": bool(platform_stability_review.get("no_git_mutation", True)),
        },
        "platform_stability_review_receipt_exists": bool(report.get("platform_stability_review_receipt_exists", False)),
        "platform_stability_review_receipt_state": str(report.get("platform_stability_review_receipt_state", "missing")),
        "platform_stability_review_receipt_path": str(report.get("platform_stability_review_receipt_path", "Saved\\PlatformStabilityReview\\last_review_receipt.json")),
        "platform_stability_review_receipt_required_command": str(report.get("platform_stability_review_receipt_required_command", "python scripts\\write_platform_stability_review.py")),
        "current_branch": str(branch.get("current", "")),
        "branch_role": str(branch.get("role", "unknown")),
        "working_branch_ok": bool(branch.get("working_branch_ok", False)),
        "source_branch_policy": str(branch.get("development_branch", "wip")),
        "stable_branch_policy": str(branch.get("stable_branch", "main")),
        "promotion_target_branch": str(branch.get("promotion_target", "main")),
        "bridge_ready": bool(bridge.get("ready", False)),
        "bridge_tcp_ready": bool(bridge.get("tcp_ready", bridge.get("ready", False))),
        "bridge_host": str(bridge.get("host", "")),
        "bridge_port": int(bridge.get("port", 0) or 0),
        "bridge_ping_receipt_exists": bool(bridge.get("bridge_ping_receipt_exists", False)),
        "bridge_ping_receipt_state": str(bridge.get("bridge_ping_receipt_state", "missing")),
        "bridge_ping_receipt_path": str(bridge.get("bridge_ping_receipt_path", "Saved\\BridgePing\\last_ping_receipt.json")),
        "bridge_ping_required_command": str(bridge.get("bridge_ping_required_command", "python scripts\\bridge_ping.py")),
        "bridge_ping_operator_command_handoff": (
            list(bridge.get("bridge_ping_operator_command_handoff", []))[:1]
            if isinstance(bridge.get("bridge_ping_operator_command_handoff"), list)
            else []
        ),
        "bridge_ping_operator_command_handoff_ids": bounded_string_preview(
            bridge.get("bridge_ping_operator_command_handoff_ids", []),
            1,
        ),
        "bridge_ping_operator_command_handoff_count": int(bridge.get("bridge_ping_operator_command_handoff_count", 0) or 0),
        "successful_bridge_ping": bool(bridge.get("successful_bridge_ping", False)),
        "chat_ready": bool(chat.get("ready", False)),
        "chat_url": str(chat.get("url", "")),
        "chat_base_url": str(chat.get("base_url", "")),
        "chat_health_endpoint": str(chat.get("health_endpoint", "")),
        "chat_tcp_ready": bool(chat.get("tcp_ready", False)),
        "chat_failure_mode": str(chat.get("failure_mode", "")),
        "chat_startup_script": str(chat.get("startup_script", "")),
        "chat_startup_receipt_path": str(chat.get("startup_receipt_path", "")),
        "chat_startup_command": str(chat.get("startup_command", "")),
        "chat_manual_startup_command": str(chat.get("manual_startup_command", "")),
        "chat_agent_command": str(chat.get("agent_command", "")),
        "chat_troubleshooting_preview": bounded_string_preview(chat.get("troubleshooting", []), 3),
        "chat_cockpit_repair_contract": {
            "schema": str(chat_repair.get("schema", "unreal_mcp_chat_cockpit_repair_contract.v1")),
            "state": str(chat_repair.get("state", "")),
            "ready": bool(chat_repair.get("ready", False)),
            "base_url": str(chat_repair.get("base_url", chat.get("base_url", ""))),
            "health_endpoint": str(chat_repair.get("health_endpoint", chat.get("health_endpoint", ""))),
            "health_url": str(chat_repair.get("health_url", chat.get("url", ""))),
            "expected_transport": str(chat_repair.get("expected_transport", chat.get("expected_transport", "sse"))),
            "expected_mcp_endpoint": str(chat_repair.get("expected_mcp_endpoint", chat.get("expected_mcp_endpoint", ""))),
            "tcp_ready": bool(chat_repair.get("tcp_ready", chat.get("tcp_ready", False))),
            "failure_mode": str(chat_repair.get("failure_mode", chat.get("failure_mode", ""))),
            "startup_script": str(chat_repair.get("startup_script", chat.get("startup_script", ""))),
            "startup_receipt_path": str(chat_repair.get("startup_receipt_path", chat.get("startup_receipt_path", ""))),
            "startup_command": str(chat_repair.get("startup_command", chat.get("startup_command", ""))),
            "manual_startup_command": str(chat_repair.get("manual_startup_command", chat.get("manual_startup_command", ""))),
            "agent_command": str(chat_repair.get("agent_command", chat.get("agent_command", ""))),
            "proof_command": str(chat_repair.get("proof_command", "")),
            "proof_expected": str(chat_repair.get("proof_expected", "")),
            "startup_step_preview": bounded_string_preview(chat_repair.get("startup_steps", []), 4),
            "required_evidence_preview": bounded_string_preview(chat_repair.get("required_evidence", []), 5),
            "no_process_start": bool(chat_repair.get("no_process_start", True)),
            "no_port_kill": bool(chat_repair.get("no_port_kill", True)),
            "no_editor_mutation": bool(chat_repair.get("no_editor_mutation", True)),
            "no_provider_call": bool(chat_repair.get("no_provider_call", True)),
            "no_git_mutation": bool(chat_repair.get("no_git_mutation", True)),
            "network_required": bool(chat_repair.get("network_required", False)),
            "spend_required": bool(chat_repair.get("spend_required", False)),
            "unreal_editor_required": bool(chat_repair.get("unreal_editor_required", False)),
        },
        "provider": str(provider.get("provider", "")),
        "animation_provider": str(provider.get("animation_provider", "")),
        "provider_api_key_configured": bool(provider.get("api_key_configured", False)),
        "provider_api_key_source": str(provider.get("api_key_source", "missing")),
        "animation_provider_api_key_configured": bool(provider.get("uthana_api_key_configured", False)),
        "animation_provider_api_key_source": str(provider.get("uthana_api_key_source", "missing")),
        "provider_secrets_gitignored": bool(provider.get("secrets_gitignored", False)),
        "provider_settings_gitignored": bool(provider.get("settings_gitignored", False)),
        "provider_config_review_receipt_exists": bool(provider.get("review_receipt_exists", False)),
        "provider_config_review_receipt_state": str(provider.get("review_receipt_state", "missing")),
        "provider_config_review_receipt_path": str(provider.get("review_receipt_path", "Saved\\ProviderConfigReview\\last_review_receipt.json")),
        "provider_config_review_receipt_required_command": str(provider.get("review_receipt_required_command", "python scripts\\write_provider_config_review.py")),
        "provider_config_operator_command_handoff": (
            list(provider.get("operator_command_handoff", []))[:1]
            if isinstance(provider.get("operator_command_handoff"), list)
            else []
        ),
        "provider_config_operator_command_handoff_ids": bounded_string_preview(
            provider.get("operator_command_handoff_ids", []),
            1,
        ),
        "provider_config_operator_command_handoff_count": int(provider.get("operator_command_handoff_count", 0) or 0),
        "provider_secret_contract": {
            "secrets_gitignored": bool(provider_secret_contract.get("secrets_gitignored", False)),
            "settings_gitignored": bool(provider_secret_contract.get("settings_gitignored", False)),
            "raw_key_returned": bool(provider_secret_contract.get("raw_key_returned", False)),
            "masked_status_only": bool(provider_secret_contract.get("masked_status_only", False)),
            "secret_storage": str(provider_secret_contract.get("secret_storage", "")),
        },
        "provider_repair_contract": {
            "schema": str(provider_repair.get("schema", "unreal_mcp_provider_config_repair.v1")),
            "config_tool": str(provider_repair.get("config_tool", "gen_get_provider_config")),
            "save_tool": str(provider_repair.get("save_tool", "gen_save_provider_config")),
            "native_settings_surface": str(provider_repair.get("native_settings_surface", "MCP Chat Generate Settings")),
            "tripo_missing": bool(provider_repair.get("tripo_missing", False)),
            "uthana_missing": bool(provider_repair.get("uthana_missing", False)),
            "tripo_store_command_template": str(provider_repair.get("tripo_store_command_template", "")),
            "uthana_store_command_template": str(provider_repair.get("uthana_store_command_template", "")),
            "proof_tool": str(provider_repair.get("proof_tool", "gen_get_provider_config(include_paths=True)")),
            "proof_required_preview": bounded_string_preview(provider_repair.get("proof_required", []), 4),
            "no_leak_policy": str(provider_repair.get("no_leak_policy", "")),
        },
        "paid_generation_evidence_contract": {
            "schema": str(paid_generation_evidence.get("schema", "unreal_mcp_paid_generation_evidence_contract.v1")),
            "wallet_evidence_recorded": bool(paid_generation_evidence.get("wallet_evidence_recorded", False)),
            "mesh_wallet_evidence_recorded": bool(paid_generation_evidence.get("mesh_wallet_evidence_recorded", False)),
            "animation_allowance_evidence_recorded": bool(paid_generation_evidence.get("animation_allowance_evidence_recorded", False)),
            "spend_confirmation_recorded": bool(paid_generation_evidence.get("spend_confirmation_recorded", False)),
            "explicit_spend_approval_recorded": bool(paid_generation_evidence.get("explicit_spend_approval_recorded", False)),
            "explicit_usage_approval_recorded": bool(paid_generation_evidence.get("explicit_usage_approval_recorded", False)),
            "estimated_spend_reviewed": bool(paid_generation_evidence.get("estimated_spend_reviewed", False)),
            "estimated_motion_seconds_reviewed": bool(paid_generation_evidence.get("estimated_motion_seconds_reviewed", False)),
            "mesh_provider": str(paid_generation_evidence.get("mesh_provider", "tripo")),
            "animation_provider": str(paid_generation_evidence.get("animation_provider", "uthana")),
            "mesh_wallet_tool": str(paid_generation_evidence.get("mesh_wallet_tool", "gen_tripo_get_credit_balance")),
            "animation_allowance_tools": bounded_string_preview(paid_generation_evidence.get("animation_allowance_tools", []), 3),
            "ledger_tool": str(paid_generation_evidence.get("ledger_tool", "skill_record_ide_companion_evidence")),
            "spend_approval_field": str(paid_generation_evidence.get("spend_approval_field", "")),
            "wallet_evidence_review_steps": bounded_string_preview(paid_generation_evidence.get("wallet_evidence_review_steps", []), 5),
            "wallet_evidence_receipt_command_template": str(paid_generation_evidence.get("wallet_evidence_receipt_command_template", "")),
            "mesh_wallet_evidence_receipt_command_template": str(paid_generation_evidence.get("mesh_wallet_evidence_receipt_command_template", "")),
            "animation_allowance_receipt_command_template": str(paid_generation_evidence.get("animation_allowance_receipt_command_template", "")),
            "spend_confirmation_receipt_command_template": str(paid_generation_evidence.get("spend_confirmation_receipt_command_template", "")),
            "operator_command_handoff": (
                list(paid_generation_evidence.get("operator_command_handoff", []))[:3]
                if isinstance(paid_generation_evidence.get("operator_command_handoff"), list)
                else []
            ),
            "no_spend_checks": bounded_string_preview(paid_generation_evidence.get("no_spend_checks", []), 5),
            "review_receipt_exists": bool(paid_generation_evidence.get("review_receipt_exists", False)),
            "review_receipt_state": str(paid_generation_evidence.get("review_receipt_state", "missing")),
            "review_receipt_path": str(paid_generation_evidence.get("review_receipt_path", "Saved\\PaidGenerationEvidence\\last_review_receipt.json")),
            "review_receipt_required_command": str(paid_generation_evidence.get("review_receipt_required_command", "python scripts\\write_paid_generation_evidence_review.py")),
            "evidence_required_preview": bounded_string_preview(paid_generation_evidence.get("evidence_required", []), 8),
            "fallback_tool": str(paid_generation_evidence.get("fallback_tool", "skill_compile_ide_companion_placeholder_manifest")),
            "fallback_reason": str(paid_generation_evidence.get("fallback_reason", "")),
            "network_required_now": bool(paid_generation_evidence.get("network_required_now", False)),
            "spend_required_now": bool(paid_generation_evidence.get("spend_required_now", False)),
            "future_network_required": bool(paid_generation_evidence.get("future_network_required", True)),
            "future_spend_required": bool(paid_generation_evidence.get("future_spend_required", True)),
            "unreal_editor_required_now": bool(paid_generation_evidence.get("unreal_editor_required_now", False)),
            "no_provider_call": bool(paid_generation_evidence.get("no_provider_call", True)),
            "no_credit_reservation": bool(paid_generation_evidence.get("no_credit_reservation", True)),
            "no_ledger_write": bool(paid_generation_evidence.get("no_ledger_write", True)),
            "no_task_submission": bool(paid_generation_evidence.get("no_task_submission", True)),
        },
        "blueprint_mutation_evidence_contract": {
            "schema": str(blueprint_mutation_evidence.get("schema", "unreal_mcp_blueprint_mutation_evidence_review_receipt.v1")),
            "state": str(blueprint_mutation_evidence.get("state", "missing")),
            "status": str(blueprint_mutation_evidence.get("status", "missing")),
            "receipt_exists": bool(blueprint_mutation_evidence.get("receipt_exists", False)),
            "receipt_path": str(blueprint_mutation_evidence.get("path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")),
            "receipt_required_command": str(blueprint_mutation_evidence.get("required_command", "python scripts\\write_blueprint_mutation_evidence_review.py")),
            "pre_read_receipt_command_template": str(blueprint_mutation_evidence.get("pre_read_receipt_command_template", "")),
            "compile_plan_receipt_command_template": str(blueprint_mutation_evidence.get("compile_plan_receipt_command_template", "")),
            "readback_plan_receipt_command_template": str(blueprint_mutation_evidence.get("readback_plan_receipt_command_template", "")),
            "operator_command_handoff": (
                list(blueprint_mutation_evidence.get("operator_command_handoff", []))[:3]
                if isinstance(blueprint_mutation_evidence.get("operator_command_handoff"), list)
                else []
            ),
            "pre_read_evidence_recorded": bool(blueprint_mutation_evidence.get("pre_read_evidence_recorded", False)),
            "compile_plan_recorded": bool(blueprint_mutation_evidence.get("compile_plan_recorded", False)),
            "readback_plan_recorded": bool(blueprint_mutation_evidence.get("readback_plan_recorded", False)),
            "target_blueprint_path": str(blueprint_mutation_evidence.get("target_blueprint_path", "")),
            "intended_mutation_summary": str(blueprint_mutation_evidence.get("intended_mutation_summary", "")),
            "pre_read_summary": str(blueprint_mutation_evidence.get("pre_read_summary", "")),
            "compile_plan_summary": str(blueprint_mutation_evidence.get("compile_plan_summary", "")),
            "readback_plan_summary": str(blueprint_mutation_evidence.get("readback_plan_summary", "")),
            "required_evidence_preview": bounded_string_preview(blueprint_mutation_evidence.get("required_evidence", []), 8),
            "merge_policy": str(blueprint_mutation_evidence.get("merge_policy", "preserve_existing_evidence_unless_reset")),
            "reset_evidence": bool(blueprint_mutation_evidence.get("reset_evidence", False)),
            "human_approval_required_before_blueprint_mutation": bool(
                blueprint_mutation_evidence.get("human_approval_required_before_blueprint_mutation", True)
            ),
            "no_bridge_ping": bool(blueprint_mutation_evidence.get("no_bridge_ping", True)),
            "no_editor_mutation": bool(blueprint_mutation_evidence.get("no_editor_mutation", True)),
            "no_blueprint_mutation": bool(blueprint_mutation_evidence.get("no_blueprint_mutation", True)),
            "no_compile": bool(blueprint_mutation_evidence.get("no_compile", True)),
            "no_save": bool(blueprint_mutation_evidence.get("no_save", True)),
            "no_pie": bool(blueprint_mutation_evidence.get("no_pie", True)),
            "no_provider_call": bool(blueprint_mutation_evidence.get("no_provider_call", True)),
            "no_git_mutation": bool(blueprint_mutation_evidence.get("no_git_mutation", True)),
        },
        "paid_missing_gate_count": len(paid_generation.get("missing_gates", [])) if isinstance(paid_generation.get("missing_gates"), list) else 0,
        "paid_missing_gate_preview": bounded_string_preview(paid_generation.get("missing_gates", []), 8),
        "paid_animation_missing_gate_count": len(paid_animation_generation.get("missing_gates", [])) if isinstance(paid_animation_generation.get("missing_gates"), list) else 0,
        "paid_animation_missing_gate_preview": bounded_string_preview(paid_animation_generation.get("missing_gates", []), 8),
        "blueprint_mutation_evidence_receipt_state": str(blueprint_mutation_evidence.get("state", "missing")),
        "blueprint_mutation_evidence_receipt_path": str(blueprint_mutation_evidence.get("path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")),
        "blueprint_mutation_evidence_receipt_required_command": str(
            blueprint_mutation_evidence.get("required_command", "python scripts\\write_blueprint_mutation_evidence_review.py")
        ),
        "blueprint_mutation_operator_command_handoff": (
            list(blueprint_mutation_evidence.get("operator_command_handoff", []))[:3]
            if isinstance(blueprint_mutation_evidence.get("operator_command_handoff"), list)
            else []
        ),
        "blueprint_pre_read_evidence_recorded": bool(blueprint_mutation_evidence.get("pre_read_evidence_recorded", False)),
        "blueprint_compile_plan_recorded": bool(blueprint_mutation_evidence.get("compile_plan_recorded", False)),
        "blueprint_readback_plan_recorded": bool(blueprint_mutation_evidence.get("readback_plan_recorded", False)),
        "blueprint_mutation_target_blueprint_path": str(blueprint_mutation_evidence.get("target_blueprint_path", "")),
        "blueprint_mutation_intended_summary": str(blueprint_mutation_evidence.get("intended_mutation_summary", "")),
        "blueprint_missing_gate_count": len(blueprint_mutation.get("missing_gates", [])) if isinstance(blueprint_mutation.get("missing_gates"), list) else 0,
        "blueprint_missing_gate_preview": bounded_string_preview(blueprint_mutation.get("missing_gates", []), 8),
        "platform_missing_gate_count": len(platform_stability.get("missing_gates", [])) if isinstance(platform_stability.get("missing_gates"), list) else 0,
        "platform_missing_gate_preview": bounded_string_preview(platform_stability.get("missing_gates", []), 8),
        "wip_promotion_missing_gate_count": len(wip_promotion.get("missing_gates", [])) if isinstance(wip_promotion.get("missing_gates"), list) else 0,
        "wip_promotion_missing_gate_preview": bounded_string_preview(wip_promotion.get("missing_gates", []), 8),
        "test_lane_state": "ok" if test_lanes.get("ok", False) else "attention",
        "test_lane_default_ci_safe": bool(test_lanes.get("default_ci_safe", test_lanes.get("ok", False))),
        "test_lane_offline_count": int(test_lanes.get("offline_count", 0) or 0),
        "test_lane_live_bridge_count": int(test_lanes.get("live_bridge_count", 0) or 0),
        "test_lane_live_bridge_manual_count": int(test_lanes.get("live_bridge_manual_count", 0) or 0),
        "test_lane_paid_provider_count": int(test_lanes.get("paid_provider_count", 0) or 0),
        "test_lane_violation_count": int(test_lanes.get("violation_count", 0) or 0),
        "paid_provider_smoke_contract_ok": bool(test_lanes.get("paid_provider_contract_ok", False)),
        "paid_provider_smoke_manual_command": str(test_lanes.get("paid_provider_manual_command", "")),
        "paid_provider_smoke_required_env_vars": bounded_string_preview(test_lanes.get("paid_provider_required_env_vars", []), 5),
        "paid_provider_smoke_no_spend_tools": bounded_string_preview(test_lanes.get("paid_provider_no_spend_tools", []), 5),
        "paid_provider_smoke_default_ci_network_required": bool(test_lanes.get("paid_provider_default_ci_network_required", False)),
        "paid_provider_smoke_manual_network_required": bool(test_lanes.get("paid_provider_manual_network_required", False)),
        "paid_provider_smoke_manual_spend_required": bool(test_lanes.get("paid_provider_manual_spend_required", False)),
        "no_mutation_test_state": str(no_mutation_tests.get("state", "missing")),
        "no_mutation_test_ok": bool(no_mutation_tests.get("ok", False)),
        "no_mutation_test_status": str(no_mutation_tests.get("status", "missing")),
        "no_mutation_test_exit_code": no_mutation_tests.get("test_exit_code"),
        "no_mutation_test_mutation_count": (
            int(no_mutation_tests.get("mutation_count", 0) or 0)
            if no_mutation_tests.get("mutation_count") is not None
            else None
        ),
        "no_mutation_test_receipt_exists": bool(no_mutation_tests.get("receipt_exists", False)),
        "no_mutation_test_receipt_path": str(no_mutation_tests.get("receipt_path", "")),
        "no_mutation_test_tracked_file_count": (
            int(no_mutation_tests.get("tracked_file_count", 0) or 0)
            if no_mutation_tests.get("tracked_file_count") is not None
            else None
        ),
        "no_mutation_test_snapshot_digest_match": bool(no_mutation_tests.get("snapshot_digest_match", False)),
        "no_mutation_test_snapshot_scope": str(no_mutation_tests.get("snapshot_scope", "")),
        "no_mutation_test_snapshot_hash_algorithm": str(no_mutation_tests.get("snapshot_hash_algorithm", "")),
        "no_mutation_test_required_command": str(no_mutation_tests.get("required_command", "python scripts\\run_no_mutation_unittest.py")),
        "no_mutation_test_operator_command_handoff": (
            list(no_mutation_tests.get("operator_command_handoff", []))[:1]
            if isinstance(no_mutation_tests.get("operator_command_handoff"), list)
            else []
        ),
        "no_mutation_test_operator_command_handoff_ids": bounded_string_preview(
            no_mutation_tests.get("operator_command_handoff_ids", []),
            1,
        ),
        "no_mutation_test_operator_command_handoff_count": int(no_mutation_tests.get("operator_command_handoff_count", 0) or 0),
        "high_value_wrapper_state": str(high_value_wrapper_coverage.get("state", "")),
        "high_value_wrapper_ok": bool(high_value_wrapper_coverage.get("ok", False)),
        "high_value_wrapper_capability_count": int(high_value_wrapper_coverage.get("capability_count", 0) or 0),
        "high_value_wrapper_covered_capability_count": int(high_value_wrapper_coverage.get("covered_capability_count", 0) or 0),
        "high_value_wrapper_failing_capability_count": int(high_value_wrapper_coverage.get("failing_capability_count", 0) or 0),
        "high_value_wrapper_command_count": int(high_value_wrapper_coverage.get("command_count", 0) or 0),
        "high_value_wrapper_schema_command_count": int(high_value_wrapper_coverage.get("schema_command_count", 0) or 0),
        "high_value_wrapper_schema_covered_command_count": int(high_value_wrapper_coverage.get("schema_covered_command_count", 0) or 0),
        "high_value_wrapper_command_preview": bounded_string_preview(high_value_wrapper_coverage.get("command_preview", []), 12),
        "high_value_wrapper_failing_capability_preview": bounded_string_preview(high_value_wrapper_coverage.get("failing_capability_preview", []), 5),
        "high_value_wrapper_roadmap_priority_count": int(high_value_wrapper_coverage.get("roadmap_priority_count", 0) or 0),
        "high_value_wrapper_roadmap_priority_covered_count": int(high_value_wrapper_coverage.get("roadmap_priority_covered_count", 0) or 0),
        "high_value_wrapper_roadmap_priority_missing_count": int(high_value_wrapper_coverage.get("roadmap_priority_missing_count", 0) or 0),
        "high_value_wrapper_roadmap_priority_preview": bounded_string_preview(high_value_wrapper_coverage.get("roadmap_priority_preview", []), 12),
        "high_value_wrapper_roadmap_priority_missing_preview": bounded_string_preview(high_value_wrapper_coverage.get("roadmap_priority_missing_preview", []), 5),
        "high_value_wrapper_operator_command_handoff": (
            list(high_value_wrapper_coverage.get("operator_command_handoff", []))[:3]
            if isinstance(high_value_wrapper_coverage.get("operator_command_handoff"), list)
            else []
        ),
        "high_value_wrapper_operator_command_handoff_ids": bounded_string_preview(
            high_value_wrapper_coverage.get("operator_command_handoff_ids", []),
            3,
        ),
        "high_value_wrapper_operator_command_handoff_count": int(high_value_wrapper_coverage.get("operator_command_handoff_count", 0) or 0),
        "high_value_wrapper_audit_tool": str(high_value_wrapper_coverage.get("audit_tool", "scripts/audit_high_value_wrapper_coverage.py")),
        "build_wrapper_exists": bool(build.get("build_wrapper_exists", False)),
        "build_wrapper_status": str(build.get("build_wrapper_status", "unknown")),
        "build_wrapper_project_ready": bool(build.get("build_wrapper_project_ready", False)),
        "build_wrapper_tool_ready": bool(build.get("build_wrapper_tool_ready", False)),
        "build_wrapper_missing_reference_count": len(build.get("build_wrapper_missing_references", [])) if isinstance(build.get("build_wrapper_missing_references"), list) else 0,
        "build_wrapper_missing_reference_preview": bounded_string_preview(build.get("build_wrapper_missing_references", []), 3),
        "build_health": str(build.get("build_health", "unknown")),
        "last_plugin_build_status": str(build.get("last_plugin_build_status", "unknown")),
        "last_plugin_build_exit_code": build.get("last_plugin_build_exit_code"),
        "last_plugin_build_warning_count": int(build.get("last_plugin_build_warning_count", 0) or 0),
        "last_plugin_build_warning_categories": bounded_string_preview(build.get("last_plugin_build_warning_categories", []), 6),
        "last_plugin_build_warning_preview": bounded_string_preview(build.get("last_plugin_build_warning_preview", []), 3),
        "last_plugin_build_warning_severity": str(build.get("last_plugin_build_warning_severity", "unknown")),
        "audit_tool": relative_repo_path(audit_path),
        "readiness_tool": "gen_compile_ide_companion_readiness",
        "review_tool": "chat_get_cockpit_overview",
        "requires_bridge": False,
        "no_editor_mutation": True,
        "no_provider_spend": True,
        "stop_before_editor_provider_or_blueprint": True,
    }


def wip_promotion_context(
    *,
    platform_preflight: Dict[str, Any],
    bridge_wrapper_coverage: Dict[str, Any],
    test_lanes: Dict[str, Any],
    readiness_policy: Dict[str, Any],
) -> Dict[str, Any]:
    if not platform_preflight:
        return {}

    gate_rows = [
        {
            "gate": "working_branch_is_wip",
            "ready": bool(platform_preflight.get("working_branch_ok", False)),
            "evidence": f"{platform_preflight.get('current_branch', '') or 'unknown'} ({platform_preflight.get('branch_role', 'unknown')})",
        },
        {
            "gate": "tool_registry_reproducible",
            "ready": bool(platform_preflight.get("tool_registry_reproducible", False)),
            "evidence": f"{platform_preflight.get('tool_count', 0)}/{platform_preflight.get('recorded_count', 0)} tools",
        },
        {
            "gate": "no_mutation_test_lane_safe",
            "ready": (
                bool(test_lanes.get("default_ci_safe", False))
                and int(test_lanes.get("violation_count", 0) or 0) == 0
                and bool(platform_preflight.get("no_mutation_test_ok", False))
            ),
            "evidence": (
                f"{test_lanes.get('offline_count', 0)} offline, "
                f"{test_lanes.get('violation_count', 0)} violation(s), "
                f"mutations {platform_preflight.get('no_mutation_test_mutation_count', 'unknown')}, "
                f"exit {platform_preflight.get('no_mutation_test_exit_code', 'unknown')}"
            ),
        },
        {
            "gate": "high_value_bridge_wrappers_covered",
            "ready": str(bridge_wrapper_coverage.get("state", "")) == "ok" and int(bridge_wrapper_coverage.get("failing_capability_count", 0) or 0) == 0,
            "evidence": f"{bridge_wrapper_coverage.get('covered_capability_count', 0)}/{bridge_wrapper_coverage.get('capability_count', 0)} capability",
        },
        {
            "gate": "build_wrapper_references_ready",
            "ready": str(platform_preflight.get("build_wrapper_status", "")) == "ready" and str(platform_preflight.get("build_health", "")) != "blocked",
            "evidence": f"{platform_preflight.get('build_wrapper_status', 'unknown')}; {platform_preflight.get('build_health', 'unknown')}; missing {platform_preflight.get('build_wrapper_missing_reference_count', 0)}",
        },
        {
            "gate": "plugin_build_successful",
            "ready": str(platform_preflight.get("last_plugin_build_status", "")) == "success" and str(platform_preflight.get("build_health", "")) != "blocked",
            "evidence": f"{platform_preflight.get('last_plugin_build_status', 'unknown')}; {platform_preflight.get('build_health', 'unknown')}",
        },
        {
            "gate": "dirty_state_grouped_for_promotion",
            "ready": str(platform_preflight.get("dirty_risk", "")) in {"clean", "low"} and int(platform_preflight.get("tracked_change_count", 0) or 0) == 0,
            "evidence": f"{platform_preflight.get('dirty_risk', 'unknown')}; tracked {platform_preflight.get('tracked_change_count', 0)}, untracked {platform_preflight.get('untracked_count', 0)}, groups {platform_preflight.get('dirty_group_count', 0)}",
        },
    ]

    chat_cockpit = readiness_policy.get("chat_cockpit") if isinstance(readiness_policy.get("chat_cockpit"), dict) else {}
    if chat_cockpit:
        gate_rows.append({
            "gate": "chat_cockpit_reachable",
            "ready": bool(chat_cockpit.get("allowed", False)),
            "evidence": (
                "ready"
                if chat_cockpit.get("allowed", False)
                else f"{', '.join(bounded_string_preview(chat_cockpit.get('missing_gates', []), 3))}; tcp {platform_preflight.get('chat_tcp_ready', False)}"
            ),
        })

    missing_gates = [row["gate"] for row in gate_rows if not row["ready"]]
    state = "ready" if not missing_gates else "blocked"
    dirty_promotion_contract = platform_preflight.get("dirty_promotion_contract") if isinstance(platform_preflight.get("dirty_promotion_contract"), dict) else {}
    dirty_review_batches = dirty_promotion_contract.get("review_batch_preview") if isinstance(dirty_promotion_contract.get("review_batch_preview"), list) else []
    dirty_evidence_matrix = dirty_promotion_contract.get("evidence_review_matrix_preview") if isinstance(dirty_promotion_contract.get("evidence_review_matrix_preview"), list) else []
    target_dirty_batch = next((item for item in dirty_review_batches if isinstance(item, dict)), {})
    target_dirty_gap = next((item for item in dirty_evidence_matrix if isinstance(item, dict)), {})
    target_dirty_missing = (
        target_dirty_gap.get("missing_evidence")
        if isinstance(target_dirty_gap.get("missing_evidence"), list)
        else []
    )
    platform_stability_review = platform_preflight.get("platform_stability_review") if isinstance(platform_preflight.get("platform_stability_review"), dict) else {}
    chat_repair_contract = platform_preflight.get("chat_cockpit_repair_contract") if isinstance(platform_preflight.get("chat_cockpit_repair_contract"), dict) else {}
    readiness_repair_queue = platform_preflight.get("readiness_repair_queue") if isinstance(platform_preflight.get("readiness_repair_queue"), dict) else {}
    promotion_resolutions = [blocker_resolution_for_gate(gate) for gate in missing_gates]
    promotion_resolution_preview = [
        {
            "blocker": str(item.get("blocker", "")),
            "severity": str(item.get("severity", "")),
            "recommended_strategy": str(item.get("recommended_strategy", "")),
            "recommended_tool": str(item.get("recommended_tool", "")),
        }
        for item in promotion_resolutions[:5]
        if isinstance(item, dict)
    ]
    target_promotion_blocker_resolution = select_blocker_resolution_target({"resolutions": promotion_resolutions}) if promotion_resolutions else {}
    return {
        "state": state,
        "status": "READY" if state == "ready" else "BLOCKED",
        "current_branch": str(platform_preflight.get("current_branch", "")),
        "branch_role": str(platform_preflight.get("branch_role", "unknown")),
        "working_branch_ok": bool(platform_preflight.get("working_branch_ok", False)),
        "source_branch_policy": str(platform_preflight.get("source_branch_policy", "wip")),
        "stable_branch_policy": str(platform_preflight.get("stable_branch_policy", "main")),
        "promotion_target_branch": str(platform_preflight.get("promotion_target_branch", "main")),
        "gate_count": len(gate_rows),
        "ready_gate_count": len(gate_rows) - len(missing_gates),
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": bounded_string_preview(missing_gates, 8),
        "gate_preview": gate_rows[:8],
        "promotion_resolution_preview": promotion_resolution_preview,
        "target_promotion_blocker_resolution": target_promotion_blocker_resolution,
        "readiness_repair_queue": readiness_repair_queue,
        "readiness_repair_recommended_next": str(readiness_repair_queue.get("recommended_next", "none")),
        "readiness_repair_action_count": int(readiness_repair_queue.get("action_count", 0) or 0),
        "readiness_repair_action_preview": list(readiness_repair_queue.get("action_preview", []))[:6] if isinstance(readiness_repair_queue.get("action_preview"), list) else [],
        "tool_count": int(platform_preflight.get("tool_count", 0) or 0),
        "recorded_count": int(platform_preflight.get("recorded_count", 0) or 0),
        "dirty_risk": str(platform_preflight.get("dirty_risk", "unknown")),
        "tracked_change_count": int(platform_preflight.get("tracked_change_count", 0) or 0),
        "untracked_count": int(platform_preflight.get("untracked_count", 0) or 0),
        "dirty_group_count": int(platform_preflight.get("dirty_group_count", 0) or 0),
        "dirty_group_preview": list(platform_preflight.get("dirty_group_preview", []))[:6] if isinstance(platform_preflight.get("dirty_group_preview"), list) else [],
        "primary_dirty_group": str(platform_preflight.get("primary_dirty_group", "")),
        "dirty_grouping_required": bool(platform_preflight.get("dirty_grouping_required", False)),
        "dirty_promotion_contract": dirty_promotion_contract,
        "dirty_promotion_review_batch_count": int(dirty_promotion_contract.get("review_batch_count", 0) or 0),
        "dirty_promotion_review_batch_preview": list(dirty_promotion_contract.get("review_batch_preview", []))[:5] if isinstance(dirty_promotion_contract.get("review_batch_preview"), list) else [],
        "dirty_promotion_evidence_review_matrix_count": int(dirty_promotion_contract.get("evidence_review_matrix_count", 0) or 0),
        "dirty_promotion_evidence_review_matrix_preview": list(dirty_promotion_contract.get("evidence_review_matrix_preview", []))[:5] if isinstance(dirty_promotion_contract.get("evidence_review_matrix_preview"), list) else [],
        "dirty_promotion_evidence_unresolved_count": int(dirty_promotion_contract.get("evidence_unresolved_count", 0) or 0),
        "dirty_promotion_evidence_review_policy": str(dirty_promotion_contract.get("evidence_review_policy", "")),
        "dirty_promotion_focused_test_command_count": int(dirty_promotion_contract.get("focused_test_command_count", 0) or 0),
        "dirty_promotion_focused_test_command_preview": bounded_string_preview(dirty_promotion_contract.get("focused_test_command_preview", []), 8),
        "target_review_group": str(dirty_promotion_contract.get("target_review_group") or target_dirty_batch.get("group") or target_dirty_gap.get("group") or ""),
        "target_review_order": int(dirty_promotion_contract.get("target_review_order", target_dirty_batch.get("order", target_dirty_gap.get("order", 0))) or 0),
        "target_review_scope": str(dirty_promotion_contract.get("target_review_scope") or target_dirty_batch.get("candidate_batch_scope") or target_dirty_gap.get("candidate_batch_scope") or ""),
        "target_review_missing_evidence_count": int(
            dirty_promotion_contract.get("target_review_missing_evidence_count", target_dirty_gap.get("missing_evidence_count", len(target_dirty_missing))) or 0
        ),
        "target_review_status": str(dirty_promotion_contract.get("target_review_status") or "missing_evidence"),
        "target_review_evidence_complete": bool(dirty_promotion_contract.get("target_review_evidence_complete", False)),
        "target_review_recorded_evidence_count": int(dirty_promotion_contract.get("target_review_recorded_evidence_count", 0) or 0),
        "target_review_recorded_evidence_preview": bounded_string_preview(
            dirty_promotion_contract.get("target_review_recorded_evidence_preview", []),
            8,
        ),
        "target_review_human_approval_recorded": bool(dirty_promotion_contract.get("target_review_human_approval_recorded", False)),
        "target_review_missing_evidence_preview": bounded_string_preview(
            dirty_promotion_contract.get("target_review_missing_evidence_preview", target_dirty_missing),
            8,
        ),
        "target_review_required_evidence_preview": bounded_string_preview(
            dirty_promotion_contract.get("target_review_required_evidence_preview", target_dirty_gap.get("required_evidence", [])),
            8,
        ),
        "target_review_decision_prompt_preview": bounded_string_preview(
            dirty_promotion_contract.get("target_review_decision_prompt_preview", target_dirty_batch.get("decision_prompts", [])),
            8,
        ),
        "target_review_receipt_command_template": str(dirty_promotion_contract.get("target_review_receipt_command_template", "")),
        "target_review_approval_receipt_command_template": str(
            dirty_promotion_contract.get("target_review_approval_receipt_command_template", "")
        ),
        "target_review_receipt_command_policy": str(dirty_promotion_contract.get("target_review_receipt_command_policy", "")),
        "target_review_operator_command_handoff": (
            list(dirty_promotion_contract.get("target_review_operator_command_handoff", []))[:2]
            if isinstance(dirty_promotion_contract.get("target_review_operator_command_handoff"), list)
            else []
        ),
        "target_review_pending_human_approval_only": bool(dirty_promotion_contract.get("target_review_pending_human_approval_only", False)),
        "target_review_human_approval_gate": str(dirty_promotion_contract.get("target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
        "target_review_human_approval_command_handoff": (
            list(dirty_promotion_contract.get("target_review_human_approval_command_handoff", []))[:1]
            if isinstance(dirty_promotion_contract.get("target_review_human_approval_command_handoff"), list)
            else []
        ),
        "target_review_focused_test_command_handoff": (
            list(dirty_promotion_contract.get("target_review_focused_test_command_handoff", []))[:5]
            if isinstance(dirty_promotion_contract.get("target_review_focused_test_command_handoff"), list)
            else []
        ),
        "target_review_focused_test_command_count": int(
            dirty_promotion_contract.get("target_review_focused_test_command_count", target_dirty_batch.get("focused_test_command_count", 0)) or 0
        ),
        "target_review_focused_test_command_preview": bounded_string_preview(
            dirty_promotion_contract.get("target_review_focused_test_command_preview", target_dirty_batch.get("focused_test_commands", [])),
            5,
        ),
        "target_review_sample_preview": bounded_string_preview(
            dirty_promotion_contract.get("target_review_sample_preview", target_dirty_batch.get("sample", [])),
            5,
        ),
        "target_review_promotion_allowed_after_receipt": bool(
            dirty_promotion_contract.get("target_review_promotion_allowed_after_receipt", target_dirty_batch.get("promotion_allowed_after_receipt", False))
        ),
        "target_review_merge_policy": str(dirty_promotion_contract.get("target_review_merge_policy", "")),
        "target_review_previous_evidence_merged": bool(dirty_promotion_contract.get("target_review_previous_evidence_merged", False)),
        "target_review_reset_evidence": bool(dirty_promotion_contract.get("target_review_reset_evidence", False)),
        "target_review_source": str(dirty_promotion_contract.get("target_review_source", "")),
        "dirty_promotion_candidate_batch_review_policy": str(dirty_promotion_contract.get("candidate_batch_review_policy", "")),
        "dirty_promotion_review_receipt_exists": bool(dirty_promotion_contract.get("review_receipt_exists", False)),
        "dirty_promotion_review_receipt_state": str(dirty_promotion_contract.get("review_receipt_state", "missing")),
        "dirty_promotion_review_receipt_current": bool(dirty_promotion_contract.get("review_receipt_current", False)),
        "dirty_promotion_review_receipt_stale": bool(dirty_promotion_contract.get("review_receipt_stale", False)),
        "dirty_promotion_review_receipt_signature_match": bool(dirty_promotion_contract.get("review_receipt_dirty_signature_match", False)),
        "dirty_promotion_review_receipt_path": str(dirty_promotion_contract.get("review_receipt_path", "Saved\\DirtyPromotionReview\\last_review_receipt.json")),
        "dirty_promotion_review_receipt_required_command": str(dirty_promotion_contract.get("review_receipt_required_command", "python scripts\\write_dirty_promotion_review.py")),
        "dirty_promotion_required_evidence_preview": bounded_string_preview(dirty_promotion_contract.get("required_evidence_preview", []), 8),
        "dirty_promotion_batch_policy": str(dirty_promotion_contract.get("promotion_batch_policy", "")),
        "dirty_promotion_artifact_policy": str(dirty_promotion_contract.get("artifact_policy", "")),
        "dirty_promotion_safe_next_steps": bounded_string_preview(dirty_promotion_contract.get("safe_promotion_next_steps", []), 8),
        "dirty_promotion_recommended_next": str(dirty_promotion_contract.get("recommended_next", "")),
        "platform_stability_review": platform_stability_review,
        "platform_stability_review_receipt_exists": bool(platform_stability_review.get("receipt_exists", False)),
        "platform_stability_review_receipt_state": str(platform_stability_review.get("state", "missing")),
        "platform_stability_review_receipt_path": str(platform_stability_review.get("path", "Saved\\PlatformStabilityReview\\last_review_receipt.json")),
        "platform_stability_review_receipt_required_command": str(platform_stability_review.get("required_command", "python scripts\\write_platform_stability_review.py")),
        "last_plugin_build_status": str(platform_preflight.get("last_plugin_build_status", "unknown")),
        "build_wrapper_status": str(platform_preflight.get("build_wrapper_status", "unknown")),
        "build_health": str(platform_preflight.get("build_health", "unknown")),
        "build_wrapper_missing_reference_count": int(platform_preflight.get("build_wrapper_missing_reference_count", 0) or 0),
        "last_plugin_build_warning_count": int(platform_preflight.get("last_plugin_build_warning_count", 0) or 0),
        "last_plugin_build_warning_categories": bounded_string_preview(platform_preflight.get("last_plugin_build_warning_categories", []), 6),
        "last_plugin_build_warning_severity": str(platform_preflight.get("last_plugin_build_warning_severity", "unknown")),
        "test_lane_state": str(test_lanes.get("state", "")),
        "test_lane_violation_count": int(test_lanes.get("violation_count", 0) or 0),
        "no_mutation_test_state": str(platform_preflight.get("no_mutation_test_state", "missing")),
        "no_mutation_test_ok": bool(platform_preflight.get("no_mutation_test_ok", False)),
        "no_mutation_test_status": str(platform_preflight.get("no_mutation_test_status", "missing")),
        "no_mutation_test_mutation_count": platform_preflight.get("no_mutation_test_mutation_count"),
        "no_mutation_test_exit_code": platform_preflight.get("no_mutation_test_exit_code"),
        "no_mutation_test_receipt_path": str(platform_preflight.get("no_mutation_test_receipt_path", "")),
        "no_mutation_test_tracked_file_count": platform_preflight.get("no_mutation_test_tracked_file_count"),
        "no_mutation_test_snapshot_digest_match": bool(platform_preflight.get("no_mutation_test_snapshot_digest_match", False)),
        "no_mutation_test_snapshot_scope": str(platform_preflight.get("no_mutation_test_snapshot_scope", "")),
        "no_mutation_test_snapshot_hash_algorithm": str(platform_preflight.get("no_mutation_test_snapshot_hash_algorithm", "")),
        "no_mutation_test_required_command": str(platform_preflight.get("no_mutation_test_required_command", "python scripts\\run_no_mutation_unittest.py")),
        "no_mutation_test_operator_command_handoff": (
            list(platform_preflight.get("no_mutation_test_operator_command_handoff", []))[:1]
            if isinstance(platform_preflight.get("no_mutation_test_operator_command_handoff"), list)
            else []
        ),
        "no_mutation_test_operator_command_handoff_ids": bounded_string_preview(
            platform_preflight.get("no_mutation_test_operator_command_handoff_ids", []),
            1,
        ),
        "no_mutation_test_operator_command_handoff_count": int(platform_preflight.get("no_mutation_test_operator_command_handoff_count", 0) or 0),
        "chat_base_url": str(platform_preflight.get("chat_base_url", "")),
        "chat_health_endpoint": str(platform_preflight.get("chat_health_endpoint", "")),
        "chat_tcp_ready": bool(platform_preflight.get("chat_tcp_ready", False)),
        "chat_failure_mode": str(platform_preflight.get("chat_failure_mode", "")),
        "chat_startup_command": str(platform_preflight.get("chat_startup_command", "")),
        "chat_agent_command": str(platform_preflight.get("chat_agent_command", "")),
        "chat_troubleshooting_preview": bounded_string_preview(platform_preflight.get("chat_troubleshooting_preview", []), 3),
        "chat_cockpit_repair_contract": chat_repair_contract,
        "chat_cockpit_repair_state": str(chat_repair_contract.get("state", "")),
        "chat_cockpit_required_evidence_preview": bounded_string_preview(chat_repair_contract.get("required_evidence_preview", []), 5),
        "chat_cockpit_startup_step_preview": bounded_string_preview(chat_repair_contract.get("startup_step_preview", []), 4),
        "chat_cockpit_proof_command": str(chat_repair_contract.get("proof_command", "")),
        "bridge_wrapper_state": str(bridge_wrapper_coverage.get("state", "")),
        "failing_wrapper_count": int(bridge_wrapper_coverage.get("failing_capability_count", 0) or 0),
        "wrapper_roadmap_priority_count": int(bridge_wrapper_coverage.get("roadmap_priority_count", 0) or 0),
        "wrapper_roadmap_priority_covered_count": int(bridge_wrapper_coverage.get("roadmap_priority_covered_count", 0) or 0),
        "wrapper_roadmap_priority_missing_count": int(bridge_wrapper_coverage.get("roadmap_priority_missing_count", 0) or 0),
        "readiness_state": str(readiness_policy.get("state", "")),
        "promotion_policy": "Keep experimental work on wip; move to main only after evidence proves the gates are stable.",
        "review_tool": "chat_get_cockpit_overview",
        "preflight_tool": "scripts/audit_ide_companion_readiness.py",
        "test_lane_tool": "scripts/audit_test_lanes.py",
        "wrapper_audit_tool": "scripts/audit_high_value_wrapper_coverage.py",
        "requires_bridge": False,
        "no_editor_mutation": True,
        "no_provider_spend": True,
        "no_git_mutation": True,
        "stop_before_branch_stage_commit_or_merge": True,
    }


def live_editor_bridge_context(
    *,
    platform_preflight: Dict[str, Any],
    readiness_policy: Dict[str, Any],
    queues: List[Dict[str, Any]],
    next_safe_step: Dict[str, Any],
    execution_review: Dict[str, Any],
    runtime_review: Dict[str, Any],
) -> Dict[str, Any]:
    if not platform_preflight and not queues and not next_safe_step and not runtime_review:
        return {}

    editor_mutation = readiness_policy.get("editor_mutation") if isinstance(readiness_policy.get("editor_mutation"), dict) else {}
    next_queue = queues[0] if queues else {}
    queued_action_count = sum(int(queue.get("action_count", 0) or 0) for queue in queues)
    executable_queue_count = sum(1 for queue in queues if queue.get("can_execute_now"))
    bridge_blocked_count = sum(1 for queue in queues if queue.get("bridge_blocked"))
    missing_gates: List[str] = []
    for source in (
        editor_mutation.get("missing_gates", []),
        next_safe_step.get("blocking_gates", []),
        execution_review.get("missing_gates", []),
    ):
        if not isinstance(source, list):
            continue
        for gate in source:
            gate_text = str(gate)
            if gate_text and gate_text not in missing_gates:
                missing_gates.append(gate_text)
    if not bool(platform_preflight.get("bridge_ready", False)) and "unreal_bridge_reachable" not in missing_gates:
        missing_gates.insert(0, "unreal_bridge_reachable")

    bridge_ready = bool(platform_preflight.get("bridge_ready", False))
    can_execute_now = bool(next_safe_step.get("can_execute_now", False)) and bridge_ready
    can_verify_now = bool(runtime_review.get("can_verify_now", False)) and bridge_ready
    state = "ready" if bridge_ready and bool(editor_mutation.get("allowed", False)) and (can_execute_now or can_verify_now) else "blocked"
    return {
        "state": state,
        "status": "READY" if state == "ready" else "BLOCKED",
        "bridge_ready": bridge_ready,
        "bridge_tcp_ready": bool(platform_preflight.get("bridge_tcp_ready", bridge_ready)),
        "bridge_host": str(platform_preflight.get("bridge_host", "")),
        "bridge_port": int(platform_preflight.get("bridge_port", 0) or 0),
        "bridge_ping_receipt_exists": bool(platform_preflight.get("bridge_ping_receipt_exists", False)),
        "bridge_ping_receipt_state": str(platform_preflight.get("bridge_ping_receipt_state", "missing")),
        "bridge_ping_receipt_path": str(platform_preflight.get("bridge_ping_receipt_path", "Saved\\BridgePing\\last_ping_receipt.json")),
        "bridge_ping_required_command": str(platform_preflight.get("bridge_ping_required_command", "python scripts\\bridge_ping.py")),
        "bridge_ping_operator_command_handoff": (
            list(platform_preflight.get("bridge_ping_operator_command_handoff", []))[:1]
            if isinstance(platform_preflight.get("bridge_ping_operator_command_handoff"), list)
            else []
        ),
        "bridge_ping_operator_command_handoff_ids": bounded_string_preview(
            platform_preflight.get("bridge_ping_operator_command_handoff_ids", []),
            1,
        ),
        "bridge_ping_operator_command_handoff_count": int(platform_preflight.get("bridge_ping_operator_command_handoff_count", 0) or 0),
        "successful_bridge_ping": bool(platform_preflight.get("successful_bridge_ping", False)),
        "editor_mutation_allowed": bool(editor_mutation.get("allowed", False)),
        "readiness_state": str(readiness_policy.get("state", "")),
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": bounded_string_preview(missing_gates, 8),
        "queue_count": len(queues),
        "queued_action_count": queued_action_count,
        "executable_queue_count": executable_queue_count,
        "bridge_blocked_count": bridge_blocked_count,
        "next_queue_name": str(next_queue.get("queue_name", "")),
        "next_action_id": str(next_queue.get("next_action_id", next_safe_step.get("next_action_id", ""))),
        "next_action_tool": str(next_queue.get("next_action_tool", next_safe_step.get("next_action_tool", ""))),
        "next_safe_step_state": str(next_safe_step.get("state", "")),
        "can_execute_now": can_execute_now,
        "execution_review_state": str(execution_review.get("state", "")),
        "after_execution_evidence_count": int(execution_review.get("after_execution_evidence_count", 0) or 0),
        "runtime_review_state": str(runtime_review.get("state", "")),
        "can_verify_now": can_verify_now,
        "runtime_proof_count": int(runtime_review.get("evidence_requirement_count", 0) or 0),
        "runtime_recorded_count": int(runtime_review.get("runtime_evidence_event_count", 0) or 0),
        "preflight_tool": "scripts/audit_ide_companion_readiness.py",
        "queue_review_tool": "chat_get_cockpit_overview",
        "queue_tool": "skill_compile_ide_companion_editor_queue",
        "runtime_review_tool": "chat_get_cockpit_overview",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "requires_bridge": False,
        "future_editor_mutation_requires_bridge": True,
        "no_editor_mutation": True,
        "no_pie_run": True,
        "stop_before_editor_or_pie": True,
    }


def provider_config_context(
    *,
    platform_preflight: Dict[str, Any],
    readiness_policy: Dict[str, Any],
) -> Dict[str, Any]:
    if not platform_preflight:
        return {}

    paid_generation = readiness_policy.get("paid_generation") if isinstance(readiness_policy.get("paid_generation"), dict) else {}
    paid_animation = (
        readiness_policy.get("paid_animation_generation")
        if isinstance(readiness_policy.get("paid_animation_generation"), dict)
        else {}
    )
    provider_repair = (
        platform_preflight.get("provider_repair_contract")
        if isinstance(platform_preflight.get("provider_repair_contract"), dict)
        else {}
    )
    provider_secret = (
        platform_preflight.get("provider_secret_contract")
        if isinstance(platform_preflight.get("provider_secret_contract"), dict)
        else {}
    )
    paid_evidence = (
        platform_preflight.get("paid_generation_evidence_contract")
        if isinstance(platform_preflight.get("paid_generation_evidence_contract"), dict)
        else {}
    )

    tripo_ready = bool(platform_preflight.get("provider_api_key_configured", False))
    uthana_ready = bool(platform_preflight.get("animation_provider_api_key_configured", False))
    receipt_state = str(platform_preflight.get("provider_config_review_receipt_state", "missing"))
    operator_command_handoff = (
        list(platform_preflight.get("provider_config_operator_command_handoff", []))[:1]
        if isinstance(platform_preflight.get("provider_config_operator_command_handoff"), list)
        else []
    )
    missing_gates: List[str] = []
    for source in (
        paid_generation.get("missing_gates", []),
        paid_animation.get("missing_gates", []),
    ):
        if not isinstance(source, list):
            continue
        for gate in source:
            gate_text = str(gate)
            if gate_text in {
                "provider_api_key_configured",
                "animation_provider_api_key_configured",
                "wallet_evidence_recorded",
                "spend_confirmation_recorded",
            } and gate_text not in missing_gates:
                missing_gates.append(gate_text)

    if not tripo_ready and "provider_api_key_configured" not in missing_gates:
        missing_gates.insert(0, "provider_api_key_configured")
    if not uthana_ready and "animation_provider_api_key_configured" not in missing_gates:
        missing_gates.append("animation_provider_api_key_configured")

    if not tripo_ready:
        recommended_next = "configure_tripo_provider_secret"
    elif not uthana_ready:
        recommended_next = "configure_uthana_provider_secret"
    elif receipt_state != "ready":
        recommended_next = "write_provider_config_review_receipt"
    else:
        recommended_next = "record_wallet_or_allowance_evidence"

    state = "ready" if tripo_ready and uthana_ready and receipt_state == "ready" else "blocked"
    return {
        "schema": "unreal_mcp_provider_config_gate_context.v1",
        "state": state,
        "status": "READY" if state == "ready" else "BLOCKED",
        "provider": str(platform_preflight.get("provider", "tripo")),
        "animation_provider": str(platform_preflight.get("animation_provider", "uthana")),
        "provider_api_key_configured": tripo_ready,
        "provider_api_key_source": str(platform_preflight.get("provider_api_key_source", "missing")),
        "animation_provider_api_key_configured": uthana_ready,
        "animation_provider_api_key_source": str(platform_preflight.get("animation_provider_api_key_source", "missing")),
        "provider_config_review_receipt_exists": bool(platform_preflight.get("provider_config_review_receipt_exists", False)),
        "provider_config_review_receipt_state": receipt_state,
        "provider_config_review_receipt_path": str(platform_preflight.get("provider_config_review_receipt_path", "Saved\\ProviderConfigReview\\last_review_receipt.json")),
        "provider_config_review_receipt_required_command": str(platform_preflight.get("provider_config_review_receipt_required_command", "python scripts\\write_provider_config_review.py")),
        "provider_config_operator_command_handoff": operator_command_handoff,
        "provider_config_operator_command_handoff_ids": bounded_string_preview(
            platform_preflight.get("provider_config_operator_command_handoff_ids", []),
            1,
        ),
        "provider_config_operator_command_handoff_count": int(platform_preflight.get("provider_config_operator_command_handoff_count", 0) or 0),
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": bounded_string_preview(missing_gates, 8),
        "recommended_next": recommended_next,
        "native_settings_surface": str(provider_repair.get("native_settings_surface", "MCP Chat Generate Settings")),
        "config_tool": str(provider_repair.get("config_tool", "gen_get_provider_config")),
        "save_tool": str(provider_repair.get("save_tool", "gen_save_provider_config")),
        "proof_tool": str(provider_repair.get("proof_tool", "gen_get_provider_config(include_paths=True)")),
        "tripo_store_command_template": str(provider_repair.get("tripo_store_command_template", "")),
        "uthana_store_command_template": str(provider_repair.get("uthana_store_command_template", "")),
        "secret_storage": str(provider_secret.get("secret_storage", "env vars or ignored Saved/MCPChat/secrets.json")),
        "secrets_gitignored": bool(provider_secret.get("secrets_gitignored", False)),
        "settings_gitignored": bool(provider_secret.get("settings_gitignored", False)),
        "raw_key_returned": bool(provider_secret.get("raw_key_returned", False)),
        "masked_status_only": bool(provider_secret.get("masked_status_only", True)),
        "mesh_wallet_tool": str(paid_evidence.get("mesh_wallet_tool", "gen_tripo_get_credit_balance")),
        "animation_allowance_tools": bounded_string_preview(
            paid_evidence.get("animation_allowance_tools", ["gen_uthana_get_account", "gen_uthana_check_download_allowed"]),
            4,
        ),
        "evidence_required_preview": bounded_string_preview([
            "masked_provider_auth_source",
            "masked_animation_provider_auth_source",
            "raw_key_absent_from_outputs",
            "provider_config_review_receipt",
            "wallet_or_allowance_evidence_recorded_separately",
            "explicit_spend_or_usage_confirmation_recorded_separately",
        ], 6),
        "review_tool": "chat_get_cockpit_overview",
        "readiness_tool": "gen_compile_ide_companion_readiness",
        "receipt_tool": "scripts/write_provider_config_review.py",
        "requires_bridge": False,
        "network_required_now": False,
        "spend_required_now": False,
        "unreal_editor_required_now": False,
        "future_network_required": True,
        "future_spend_required": True,
        "no_raw_key": True,
        "no_provider_call": True,
        "no_wallet_check": True,
        "no_credit_reservation": True,
        "no_spend_confirmation": True,
        "no_editor_mutation": True,
        "stop_before_provider_call": True,
    }


def provider_spend_context(
    *,
    readiness_policy: Dict[str, Any],
    generated_asset_quality_gate: Dict[str, Any],
    target_generated_asset_context: Dict[str, Any],
    platform_preflight: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    provider_pending_count = int(generated_asset_quality_gate.get("provider_pending_count", 0) or 0)
    if not provider_pending_count:
        return {}
    paid_generation = readiness_policy.get("paid_generation") if isinstance(readiness_policy.get("paid_generation"), dict) else {}
    missing_gates = paid_generation.get("missing_gates") if isinstance(paid_generation.get("missing_gates"), list) else []
    evidence_required = paid_generation.get("evidence_required") if isinstance(paid_generation.get("evidence_required"), list) else []
    target_asset = target_generated_asset_context if str(target_generated_asset_context.get("state", "")) == "provider_pending" else {}
    placeholder_count = int(generated_asset_quality_gate.get("placeholder_count", 0) or 0)
    fallback_available = bool(not paid_generation.get("allowed", False) and placeholder_count > 0)
    target_provider = str(target_asset.get("provider") or target_generated_asset_context.get("provider", ""))
    preflight = platform_preflight if isinstance(platform_preflight, dict) else {}
    preflight_paid_contract = (
        preflight.get("paid_generation_evidence_contract")
        if isinstance(preflight.get("paid_generation_evidence_contract"), dict)
        else {}
    )
    evidence_contract = {
        "schema": "unreal_mcp_paid_generation_evidence_contract.v1",
        "wallet_evidence_recorded": bool(preflight_paid_contract.get("wallet_evidence_recorded", False)),
        "mesh_wallet_evidence_recorded": bool(preflight_paid_contract.get("mesh_wallet_evidence_recorded", False)),
        "animation_allowance_evidence_recorded": bool(preflight_paid_contract.get("animation_allowance_evidence_recorded", False)),
        "spend_confirmation_recorded": bool(preflight_paid_contract.get("spend_confirmation_recorded", False)),
        "explicit_spend_approval_recorded": bool(preflight_paid_contract.get("explicit_spend_approval_recorded", False)),
        "explicit_usage_approval_recorded": bool(preflight_paid_contract.get("explicit_usage_approval_recorded", False)),
        "estimated_spend_reviewed": bool(preflight_paid_contract.get("estimated_spend_reviewed", False)),
        "estimated_motion_seconds_reviewed": bool(preflight_paid_contract.get("estimated_motion_seconds_reviewed", False)),
        "mesh_provider": target_provider or "tripo",
        "animation_provider": "uthana",
        "review_receipt_exists": bool(preflight_paid_contract.get("review_receipt_exists", False)),
        "review_receipt_state": str(preflight_paid_contract.get("review_receipt_state", "missing")),
        "review_receipt_path": str(preflight_paid_contract.get("review_receipt_path", "Saved\\PaidGenerationEvidence\\last_review_receipt.json")),
        "review_receipt_required_command": str(preflight_paid_contract.get("review_receipt_required_command", "python scripts\\write_paid_generation_evidence_review.py")),
        "mesh_wallet_tool": "gen_tripo_get_credit_balance",
        "animation_allowance_tools": [
            "gen_uthana_get_account",
            "gen_uthana_get_job",
            "gen_uthana_check_download_allowed",
        ],
        "ledger_tool": "skill_record_ide_companion_evidence",
        "spend_approval_field": "confirm_spend=True for Tripo; confirm_usage=True for Uthana task/download",
        "no_spend_checks": bounded_string_preview(preflight_paid_contract.get("no_spend_checks", [
            "gen_get_provider_config(include_paths=True)",
            "gen_tripo_get_credit_balance after provider-network approval and no-spend intent",
            "gen_uthana_get_account / gen_uthana_get_job / gen_uthana_check_download_allowed after provider-network approval and no-spend intent",
        ]), 5),
        "wallet_evidence_review_steps": bounded_string_preview(preflight_paid_contract.get("wallet_evidence_review_steps", [
            "Confirm provider-network approval and no-spend intent in the cockpit.",
            "Run gen_tripo_get_credit_balance(include_raw=False) for masked Tripo wallet balance evidence.",
            "Run gen_uthana_get_account(include_user=False) for masked Uthana org allowance evidence.",
            "Write the ignored local paid-generation evidence receipt with a short non-secret summary.",
        ]), 5),
        "wallet_evidence_receipt_command_template": str(
            preflight_paid_contract.get(
                "wallet_evidence_receipt_command_template",
                'python scripts\\write_paid_generation_evidence_review.py --mesh-wallet-evidence-recorded --animation-allowance-evidence-recorded --mesh-wallet-evidence-summary "<masked Tripo wallet evidence>" --animation-allowance-summary "<masked Uthana allowance evidence>"',
            )
        ),
        "mesh_wallet_evidence_receipt_command_template": str(
            preflight_paid_contract.get(
                "mesh_wallet_evidence_receipt_command_template",
                'python scripts\\write_paid_generation_evidence_review.py --mesh-wallet-evidence-recorded --mesh-wallet-evidence-summary "<masked Tripo wallet evidence>"',
            )
        ),
        "animation_allowance_receipt_command_template": str(
            preflight_paid_contract.get(
                "animation_allowance_receipt_command_template",
                'python scripts\\write_paid_generation_evidence_review.py --animation-allowance-evidence-recorded --animation-allowance-summary "<masked Uthana allowance evidence>"',
            )
        ),
        "spend_confirmation_receipt_command_template": str(
            preflight_paid_contract.get(
                "spend_confirmation_receipt_command_template",
                'python scripts\\write_paid_generation_evidence_review.py --mesh-wallet-evidence-recorded --animation-allowance-evidence-recorded --spend-confirmation-recorded --explicit-usage-approval-recorded --estimated-spend-reviewed --estimated-motion-seconds-reviewed --mesh-wallet-evidence-summary "<masked Tripo wallet evidence>" --animation-allowance-summary "<masked Uthana allowance evidence>" --spend-confirmation-summary "<explicit human Tripo spend approval>" --usage-approval-summary "<explicit human Uthana usage approval>"',
            )
        ),
        "evidence_required_preview": bounded_string_preview([
            "masked_provider_auth_source",
            "wallet_or_allowance_evidence",
            "masked_tripo_wallet_evidence",
            "masked_uthana_allowance_evidence",
            "explicit_human_spend_or_usage_approval",
            "explicit_uthana_usage_approval",
            "estimated_credits_or_motion_seconds_reviewed",
            "ledger_evidence_row_before_paid_task_submission",
        ], 6),
        "fallback_tool": "skill_compile_ide_companion_placeholder_manifest",
        "fallback_reason": str(preflight_paid_contract.get(
            "fallback_reason",
            "Use placeholders and lifecycle manifests until wallet/allowance and explicit spend/usage approval are recorded.",
        )),
        "network_required_now": False,
        "spend_required_now": False,
        "future_network_required": True,
        "future_spend_required": True,
        "unreal_editor_required_now": False,
        "no_provider_call": True,
        "no_credit_reservation": True,
        "no_task_submission": True,
        "no_ledger_write": True,
    }
    operator_handoff = (
        list(preflight_paid_contract.get("operator_command_handoff", []))[:3]
        if isinstance(preflight_paid_contract.get("operator_command_handoff"), list)
        else []
    )
    if not operator_handoff:
        operator_handoff = [
            {
                "id": "record_masked_tripo_wallet_evidence",
                "label": "Record masked Tripo wallet evidence",
                "provider": "tripo",
                "command": evidence_contract["mesh_wallet_evidence_receipt_command_template"],
                "command_kind": "local_receipt",
                "receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
                "requires_provider_network_approval": True,
                "requires_human_spend_or_usage_approval": False,
                "approval_flags_included": False,
                "records_evidence_only": True,
                "no_provider_call": True,
                "no_credit_reservation": True,
                "no_task_submission": True,
                "no_download": True,
                "no_import": True,
                "no_editor_mutation": True,
                "no_git_mutation": True,
            },
            {
                "id": "record_masked_uthana_allowance_evidence",
                "label": "Record masked Uthana allowance evidence",
                "provider": "uthana",
                "command": evidence_contract["animation_allowance_receipt_command_template"],
                "command_kind": "local_receipt",
                "receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
                "requires_provider_network_approval": True,
                "requires_human_spend_or_usage_approval": False,
                "approval_flags_included": False,
                "records_evidence_only": True,
                "no_provider_call": True,
                "no_credit_reservation": True,
                "no_task_submission": True,
                "no_download": True,
                "no_import": True,
                "no_editor_mutation": True,
                "no_git_mutation": True,
            },
            {
                "id": "record_explicit_spend_and_usage_approval",
                "label": "Record explicit Tripo spend and Uthana usage approval",
                "provider": "tripo+uthana",
                "command": evidence_contract["spend_confirmation_receipt_command_template"],
                "command_kind": "local_receipt",
                "receipt_path": "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
                "requires_provider_network_approval": False,
                "requires_human_spend_or_usage_approval": True,
                "approval_flags_included": True,
                "records_evidence_only": True,
                "no_provider_call": True,
                "no_credit_reservation": True,
                "no_task_submission": True,
                "no_download": True,
                "no_import": True,
                "no_editor_mutation": True,
                "no_git_mutation": True,
            },
        ]
    evidence_contract["operator_command_handoff"] = operator_handoff
    return {
        "state": "ready" if paid_generation.get("allowed", False) else "blocked",
        "readiness_state": str(readiness_policy.get("state", "")),
        "paid_generation_allowed": bool(paid_generation.get("allowed", False)),
        "provider_pending_count": provider_pending_count,
        "asset_count": int(generated_asset_quality_gate.get("asset_count", 0) or 0),
        "placeholder_count": placeholder_count,
        "missing_gate_count": len(missing_gates),
        "missing_gate_preview": bounded_string_preview(missing_gates, 8),
        "evidence_required_count": len(evidence_required),
        "evidence_required_preview": bounded_string_preview(evidence_required, 8),
        "paid_generation_evidence_contract": evidence_contract,
        "target_asset": target_asset,
        "provider": target_provider,
        "provider_config_review_receipt_exists": bool(preflight.get("provider_config_review_receipt_exists", False)),
        "provider_config_review_receipt_state": str(preflight.get("provider_config_review_receipt_state", "missing")),
        "provider_config_review_receipt_path": str(preflight.get("provider_config_review_receipt_path", "Saved\\ProviderConfigReview\\last_review_receipt.json")),
        "provider_config_review_receipt_required_command": str(preflight.get("provider_config_review_receipt_required_command", "python scripts\\write_provider_config_review.py")),
        "next_gate": str(target_asset.get("next_gate") or target_generated_asset_context.get("next_gate", "")),
        "readiness_tool": "gen_compile_ide_companion_readiness",
        "placeholder_tool": "skill_compile_ide_companion_placeholder_manifest",
        "lifecycle_tool": "skill_compile_ide_companion_asset_lifecycle_manifest",
        "fallback_placeholder_available": fallback_available,
        "fallback_action_id": "compile_placeholder_manifest" if fallback_available else "",
        "fallback_action_label": "Compile Placeholder Manifest" if fallback_available else "",
        "fallback_tool": "skill_compile_ide_companion_placeholder_manifest" if fallback_available else "",
        "fallback_queue_tool": "skill_compile_ide_companion_editor_queue" if fallback_available else "",
        "fallback_reason": (
            "Paid provider gates are blocked; compile no-spend placeholders and queue safe editor actions instead of submitting provider work."
            if fallback_available else ""
        ),
        "review_tool": "chat_get_cockpit_overview",
        "future_network_required": True,
        "future_spend_required": True,
        "network_required_now": False,
        "spend_required_now": False,
        "unreal_editor_required_now": False,
        "no_provider_call": True,
        "stop_before_provider_call": True,
    }


def start_session_context(
    *,
    session_name: str,
    ledger: Dict[str, Any],
    queues: List[Dict[str, Any]],
    readiness_policy: Dict[str, Any],
    generated_asset_quality_gate: Dict[str, Any],
) -> Dict[str, Any]:
    has_existing_ledger = bool(ledger)
    return {
        "session_name": str(session_name or "ide-companion"),
        "has_existing_ledger": has_existing_ledger,
        "ledger_path": str(ledger.get("ledger_path", "")),
        "event_count": int(ledger.get("event_count", 0) or 0),
        "completed_phase_count": int(ledger.get("completed_phase_count", 0) or 0),
        "latest_phase": str(ledger.get("latest_phase", "")),
        "readiness_state": str(readiness_policy.get("state", "")),
        "blocked_policy_count": int(readiness_policy.get("blocked_policy_count", 0) or 0),
        "queue_count": len(queues),
        "generated_asset_count": int(generated_asset_quality_gate.get("asset_count", 0) or 0),
        "session_tool": "skill_compile_ide_companion_session",
        "readiness_tool": "gen_compile_ide_companion_readiness",
        "resume_tool": "skill_resume_ide_companion_session",
        "review_tool": "chat_get_cockpit_overview",
        "recommended_next": "resume_existing_session" if has_existing_ledger else "create_session_plan",
        "stop_before_editor_or_provider": True,
    }


def status_refresh_context(
    *,
    ledger: Dict[str, Any],
    queues: List[Dict[str, Any]],
    readiness_policy: Dict[str, Any],
    evidence_recording: Dict[str, Any],
    blocker_resolutions: Dict[str, Any],
    generated_asset_quality_gate: Dict[str, Any],
    runtime_review: Dict[str, Any],
) -> Dict[str, Any]:
    if not ledger:
        return {}
    evidence_items = evidence_recording.get("items") if isinstance(evidence_recording.get("items"), list) else []
    blocking_gates = ledger.get("blocking_gates") if isinstance(ledger.get("blocking_gates"), list) else []
    return {
        "session_name": str(ledger.get("session_name", "")),
        "ledger_path": str(ledger.get("ledger_path", "")),
        "has_session_plan": bool(ledger.get("has_session_plan", False)),
        "session_plan_phase_count": int(ledger.get("session_plan_phase_count", 0) or 0),
        "event_count": int(ledger.get("event_count", 0) or 0),
        "completed_phase_count": int(ledger.get("completed_phase_count", 0) or 0),
        "latest_phase": str(ledger.get("latest_phase", "")),
        "next_phase": str(ledger.get("next_phase", "")),
        "next_tool": str(ledger.get("next_tool", "")),
        "readiness_state": str(readiness_policy.get("state", "")),
        "blocked_policy_count": int(readiness_policy.get("blocked_policy_count", 0) or 0),
        "blocking_gate_count": int(blocker_resolutions.get("blocking_gate_count", len(blocking_gates)) or 0),
        "queue_count": len(queues),
        "evidence_item_count": len(evidence_items),
        "generated_asset_count": int(generated_asset_quality_gate.get("asset_count", 0) or 0),
        "runtime_review_state": str(runtime_review.get("state", "")),
        "status_tool": "skill_compile_ide_companion_status",
        "resume_tool": "skill_resume_ide_companion_session",
        "readiness_tool": "gen_compile_ide_companion_readiness",
        "review_tool": "chat_get_cockpit_overview",
        "requires_session_plan": True,
        "stop_before_editor_or_provider": True,
    }


def work_order_context(
    *,
    ledger: Dict[str, Any],
    readiness_policy: Dict[str, Any],
    blocker_resolutions: Dict[str, Any],
    work_order_template: Dict[str, Any],
    status_context: Dict[str, Any],
) -> Dict[str, Any]:
    if not ledger:
        return {}
    target_phase = str(ledger.get("work_order_phase") or ledger.get("next_phase") or "")
    blocking_gates = ledger.get("blocking_gates") if isinstance(ledger.get("blocking_gates"), list) else []
    return {
        "session_name": str(ledger.get("session_name", "")),
        "ledger_path": str(ledger.get("ledger_path", "")),
        "has_session_plan": bool(ledger.get("has_session_plan", False)),
        "has_status_receipt": bool(ledger.get("has_status_receipt", False)),
        "target_phase": target_phase,
        "latest_phase": str(ledger.get("latest_phase", "")),
        "next_phase": str(ledger.get("next_phase", "")),
        "next_tool": str(ledger.get("next_tool", "")),
        "readiness_state": str(readiness_policy.get("state", "")),
        "blocked_policy_count": int(readiness_policy.get("blocked_policy_count", 0) or 0),
        "blocking_gate_count": int(blocker_resolutions.get("blocking_gate_count", len(blocking_gates)) or 0),
        "status_completed_phase_count": int(status_context.get("completed_phase_count", 0) or 0),
        "template_name": str(work_order_template.get("template_name", "")),
        "display_name": str(work_order_template.get("display_name", "")),
        "operation_count": int(work_order_template.get("operation_count", 0) or 0),
        "editor_operation_count": int(work_order_template.get("editor_operation_count", 0) or 0),
        "bridge_required_operation_count": int(work_order_template.get("bridge_required_operation_count", 0) or 0),
        "compile_after_operation_count": int(work_order_template.get("compile_after_operation_count", 0) or 0),
        "readback_after_operation_count": int(work_order_template.get("readback_after_operation_count", 0) or 0),
        "compile_check_count": int(work_order_template.get("compile_check_count", 0) or 0),
        "pie_validation_count": int(work_order_template.get("pie_validation_count", 0) or 0),
        "runtime_proof_required_count": int(work_order_template.get("runtime_proof_required_count", 0) or 0),
        "runtime_proof_mode": str(work_order_template.get("runtime_proof_mode", "")),
        "runtime_proof_required_preview": bounded_string_preview(work_order_template.get("runtime_proof_required_preview", []), 8),
        "runtime_proof_tool_preview": bounded_string_preview(work_order_template.get("runtime_proof_tool_preview", []), 8),
        "evidence_requirement_count": int(work_order_template.get("evidence_requirement_count", 0) or 0),
        "editor_operation_type_preview": bounded_string_preview(work_order_template.get("editor_operation_type_preview", []), 6),
        "editor_operation_tool_preview": bounded_string_preview(work_order_template.get("editor_operation_tool_preview", []), 8),
        "editor_operation_preview": bounded_string_preview(work_order_template.get("editor_operation_preview", []), 5),
        **generated_animation_prompt_gate_context(work_order_template),
        "work_order_tool": "skill_compile_ide_companion_work_order",
        "status_tool": "skill_compile_ide_companion_status",
        "resume_tool": "skill_resume_ide_companion_session",
        "review_tool": "chat_get_cockpit_overview",
        "requires_session_plan": True,
        "prefers_status_receipt": True,
        "stop_before_editor_mutation": True,
    }


def gameplay_template_context(
    *,
    ledger: Dict[str, Any],
    readiness_policy: Dict[str, Any],
    work_order_template: Dict[str, Any],
) -> Dict[str, Any]:
    if not work_order_template:
        return {}
    editor_mutation = readiness_policy.get("editor_mutation") if isinstance(readiness_policy.get("editor_mutation"), dict) else {}
    paid_animation = (
        readiness_policy.get("paid_animation_generation")
        if isinstance(readiness_policy.get("paid_animation_generation"), dict)
        else {}
    )
    generated_animation_prompt_count = int(work_order_template.get("generated_animation_prompt_count", 0) or 0)
    paid_animation_missing_gates = (
        paid_animation.get("missing_gates") if isinstance(paid_animation.get("missing_gates"), list) else []
    )
    paid_animation_evidence = (
        paid_animation.get("evidence_required") if isinstance(paid_animation.get("evidence_required"), list) else []
    )
    editor_missing_gates = editor_mutation.get("missing_gates") if isinstance(editor_mutation.get("missing_gates"), list) else []
    bridge_required_count = int(work_order_template.get("bridge_required_operation_count", 0) or 0)
    compile_count = int(work_order_template.get("compile_after_operation_count", 0) or 0)
    readback_count = int(work_order_template.get("readback_after_operation_count", 0) or 0)
    runtime_required_count = int(work_order_template.get("runtime_proof_required_count", 0) or 0)
    completion_required_count = int(work_order_template.get("completion_required_evidence_count", 0) or 0)
    operation_proof_count = int(work_order_template.get("operation_proof_contract_count", 0) or 0)
    requires_runtime_proof = bool(runtime_required_count > 0 or completion_required_count > 0)
    can_queue_editor_work = bool(
        work_order_template.get("template_name")
        and bool(editor_mutation.get("allowed", False))
        and bridge_required_count > 0
        and compile_count > 0
        and readback_count > 0
    )
    can_mark_feature_complete = bool(
        can_queue_editor_work
        and runtime_required_count > 0
        and completion_required_count > 0
        and not editor_missing_gates
    )
    execution_readiness = {
        "schema": "unreal_mcp_gameplay_template_execution_readiness.v1",
        "state": "ready_to_queue" if can_queue_editor_work else "blocked",
        "can_queue_editor_work": can_queue_editor_work,
        "can_mark_feature_complete": can_mark_feature_complete,
        "editor_mutation_allowed": bool(editor_mutation.get("allowed", False)),
        "bridge_required_operation_count": bridge_required_count,
        "compile_after_operation_count": compile_count,
        "readback_after_operation_count": readback_count,
        "operation_proof_contract_count": operation_proof_count,
        "runtime_proof_required_count": runtime_required_count,
        "completion_required_evidence_count": completion_required_count,
        "missing_gate_count": len(editor_missing_gates),
        "missing_gate_preview": bounded_string_preview(editor_missing_gates, 6),
        "required_before_preview": bounded_string_preview(
            [
                "unreal_bridge_reachable",
                "blueprint_pre_read_evidence",
                "operation_proof_contract_reviewed",
            ],
            6,
        ),
        "required_after_preview": bounded_string_preview(
            [
                "blueprint_compile_report",
                "graph_or_component_readback",
                "runtime_proof_contract_evidence",
                "ide_companion_ledger_event",
            ],
            6,
        ),
        "stop_if_missing_preview": bounded_string_preview(
            [
                "bridge ping failed",
                "compile report missing or failed",
                "readback does not show the expected operation",
                "runtime proof contract evidence is incomplete",
                "IDE companion ledger evidence is missing",
            ],
            6,
        ),
        "recommended_next": "queue_editor_actions" if can_queue_editor_work else "resolve_blueprint_mutation_gates",
        "next_editor_operation_id": str(work_order_template.get("next_editor_operation_id", "")),
        "next_editor_operation_type": str(work_order_template.get("next_editor_operation_type", "")),
        "next_editor_operation_summary": str(work_order_template.get("next_editor_operation_summary", "")),
        "next_editor_operation_tool_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_tool_preview", []),
            5,
        ),
        "next_editor_operation_ready": bool(can_queue_editor_work and work_order_template.get("next_editor_operation_id")),
        "next_editor_operation_blocking_gate_preview": (
            [] if can_queue_editor_work else bounded_string_preview(editor_missing_gates, 5)
        ),
        "next_editor_operation_required_before_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_required_before_preview", []),
            5,
        ),
        "next_editor_operation_required_after_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_required_after_preview", []),
            5,
        ),
        "next_editor_operation_stop_if_missing_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_stop_if_missing_preview", []),
            5,
        ),
        "queue_tool": "skill_compile_ide_companion_editor_queue",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "review_tool": "chat_get_cockpit_overview",
        "requires_bridge_before_execution": bool(bridge_required_count > 0),
        "requires_compile_readback": bool(compile_count > 0 or readback_count > 0),
        "requires_runtime_proof": requires_runtime_proof,
        "requires_ledger_evidence": True,
        "no_editor_mutation": True,
        "stop_before_editor_mutation": True,
        "stop_before_feature_complete": True,
    }
    return {
        "state": "ready_to_review" if work_order_template.get("template_name") else "missing_template",
        "session_name": str(ledger.get("session_name", "")),
        "ledger_path": str(ledger.get("ledger_path", "")),
        "target_phase": str(work_order_template.get("target_phase") or ledger.get("work_order_phase") or ledger.get("next_phase") or ""),
        "template_name": str(work_order_template.get("template_name", "")),
        "display_name": str(work_order_template.get("display_name", "")),
        "asset_count": int(work_order_template.get("asset_count", 0) or 0),
        "operation_count": int(work_order_template.get("operation_count", 0) or 0),
        "editor_operation_count": int(work_order_template.get("editor_operation_count", 0) or 0),
        "bridge_required_operation_count": int(work_order_template.get("bridge_required_operation_count", 0) or 0),
        "compile_after_operation_count": int(work_order_template.get("compile_after_operation_count", 0) or 0),
        "readback_after_operation_count": int(work_order_template.get("readback_after_operation_count", 0) or 0),
        "compile_check_count": int(work_order_template.get("compile_check_count", 0) or 0),
        "pie_validation_count": int(work_order_template.get("pie_validation_count", 0) or 0),
        "runtime_proof_contract_schema": str(work_order_template.get("runtime_proof_contract_schema", "")),
        "runtime_proof_mode": str(work_order_template.get("runtime_proof_mode", "")),
        "runtime_proof_required_count": int(work_order_template.get("runtime_proof_required_count", 0) or 0),
        "runtime_proof_required_before_count": int(work_order_template.get("runtime_proof_required_before_count", 0) or 0),
        "runtime_proof_required_preview": bounded_string_preview(work_order_template.get("runtime_proof_required_preview", []), 8),
        "runtime_proof_tool_preview": bounded_string_preview(work_order_template.get("runtime_proof_tool_preview", []), 8),
        "runtime_proof_stop_preview": bounded_string_preview(work_order_template.get("runtime_proof_stop_preview", []), 8),
        "repair_instruction_count": int(work_order_template.get("repair_instruction_count", 0) or 0),
        "evidence_requirement_count": int(work_order_template.get("evidence_requirement_count", 0) or 0),
        "stop_condition_count": int(work_order_template.get("stop_condition_count", 0) or 0),
        "completion_proof_gate_count": int(work_order_template.get("completion_proof_gate_count", 0) or 0),
        "completion_required_evidence_count": int(work_order_template.get("completion_required_evidence_count", 0) or 0),
        "completion_stop_condition_count": int(work_order_template.get("completion_stop_condition_count", 0) or 0),
        "operation_proof_contract_count": int(work_order_template.get("operation_proof_contract_count", 0) or 0),
        "ownership_domains": bounded_string_preview(work_order_template.get("ownership_domains", []), 8),
        "asset_preview": bounded_string_preview(work_order_template.get("asset_preview", []), 5),
        "operation_preview": bounded_string_preview(work_order_template.get("operation_preview", []), 5),
        "editor_operation_type_preview": bounded_string_preview(work_order_template.get("editor_operation_type_preview", []), 6),
        "editor_operation_tool_preview": bounded_string_preview(work_order_template.get("editor_operation_tool_preview", []), 8),
        "editor_operation_preview": bounded_string_preview(work_order_template.get("editor_operation_preview", []), 5),
        "next_editor_operation_id": str(work_order_template.get("next_editor_operation_id", "")),
        "next_editor_operation_type": str(work_order_template.get("next_editor_operation_type", "")),
        "next_editor_operation_summary": str(work_order_template.get("next_editor_operation_summary", "")),
        "next_editor_operation_tool_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_tool_preview", []),
            5,
        ),
        "next_editor_operation_requires_bridge": bool(work_order_template.get("next_editor_operation_requires_bridge", False)),
        "next_editor_operation_requires_compile_after": bool(work_order_template.get("next_editor_operation_requires_compile_after", False)),
        "next_editor_operation_requires_readback_after": bool(work_order_template.get("next_editor_operation_requires_readback_after", False)),
        "next_editor_operation_required_before_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_required_before_preview", []),
            5,
        ),
        "next_editor_operation_required_after_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_required_after_preview", []),
            5,
        ),
        "next_editor_operation_stop_if_missing_preview": bounded_string_preview(
            work_order_template.get("next_editor_operation_stop_if_missing_preview", []),
            5,
        ),
        "generated_asset_replacement_operation_count": int(work_order_template.get("generated_asset_replacement_operation_count", 0) or 0),
        "generated_asset_replacement_operation_preview": bounded_string_preview(work_order_template.get("generated_asset_replacement_operation_preview", []), 5),
        "generated_asset_replacement_tool_preview": bounded_string_preview(work_order_template.get("generated_asset_replacement_tool_preview", []), 8),
        "generated_asset_replacement_proof_contract_count": int(work_order_template.get("generated_asset_replacement_proof_contract_count", 0) or 0),
        **generated_animation_prompt_gate_context(work_order_template),
        "generated_animation_paid_generation_allowed": bool(paid_animation.get("allowed", False)),
        "generated_animation_paid_missing_gate_count": len(paid_animation_missing_gates) if generated_animation_prompt_count > 0 else 0,
        "generated_animation_paid_missing_gate_preview": (
            bounded_string_preview(paid_animation_missing_gates, 5) if generated_animation_prompt_count > 0 else []
        ),
        "generated_animation_paid_evidence_required_preview": (
            bounded_string_preview(paid_animation_evidence, 5) if generated_animation_prompt_count > 0 else []
        ),
        "generated_animation_safe_unblock_tool_preview": (
            [
                "gen_save_provider_config",
                "gen_uthana_get_account",
                "skill_record_ide_companion_evidence",
            ]
            if generated_animation_prompt_count > 0
            else []
        ),
        "generated_animation_stop_before_provider": bool(
            generated_animation_prompt_count > 0 and (paid_animation_missing_gates or not paid_animation.get("allowed", False))
        ),
        "execution_readiness": execution_readiness,
        "execution_readiness_state": execution_readiness["state"],
        "can_queue_editor_work": execution_readiness["can_queue_editor_work"],
        "can_mark_feature_complete": execution_readiness["can_mark_feature_complete"],
        "execution_recommended_next": execution_readiness["recommended_next"],
        "operation_proof_required_after_preview": bounded_string_preview(work_order_template.get("operation_proof_required_after_preview", []), 8),
        "compile_check_preview": bounded_string_preview(work_order_template.get("compile_check_preview", []), 5),
        "pie_validation_preview": bounded_string_preview(work_order_template.get("pie_validation_preview", []), 5),
        "repair_preview": bounded_string_preview(work_order_template.get("repair_preview", []), 5),
        "evidence_preview": bounded_string_preview(work_order_template.get("evidence_preview", []), 5),
        "completion_proof_gate_preview": bounded_string_preview(work_order_template.get("completion_proof_gate_preview", []), 5),
        "completion_required_evidence_preview": bounded_string_preview(work_order_template.get("completion_required_evidence_preview", []), 5),
        "completion_stop_before_complete_preview": bounded_string_preview(work_order_template.get("completion_stop_before_complete_preview", []), 5),
        "readiness_state": str(readiness_policy.get("state", "")),
        "editor_mutation_allowed": bool(editor_mutation.get("allowed", False)),
        "missing_gate_preview": bounded_string_preview(editor_missing_gates, 5),
        "plan_tool": "skill_plan_gameplay_mechanic",
        "work_order_tool": "skill_compile_ide_companion_work_order",
        "queue_tool": "skill_compile_ide_companion_editor_queue",
        "review_tool": "chat_get_cockpit_overview",
        "requires_ledger": True,
        "stop_before_editor_mutation": True,
    }


def placeholder_manifest_context(
    *,
    ledger: Dict[str, Any],
    readiness_policy: Dict[str, Any],
    blocker_resolutions: Dict[str, Any],
    generated_asset_quality_gate: Dict[str, Any],
    target_generated_asset_context: Dict[str, Any],
) -> Dict[str, Any]:
    asset_count = int(generated_asset_quality_gate.get("asset_count", 0) or 0)
    if not ledger or not asset_count:
        return {}
    blocking_gates = ledger.get("blocking_gates") if isinstance(ledger.get("blocking_gates"), list) else []
    return {
        "session_name": str(ledger.get("session_name", "")),
        "ledger_path": str(ledger.get("ledger_path", "")),
        "has_session_plan": bool(ledger.get("has_session_plan", False)),
        "readiness_state": str(readiness_policy.get("state", "")),
        "blocked_policy_count": int(readiness_policy.get("blocked_policy_count", 0) or 0),
        "blocking_gate_count": int(blocker_resolutions.get("blocking_gate_count", len(blocking_gates)) or 0),
        "generated_asset_state": str(generated_asset_quality_gate.get("state", "")),
        "asset_count": asset_count,
        "provider_pending_count": int(generated_asset_quality_gate.get("provider_pending_count", 0) or 0),
        "import_pending_count": int(generated_asset_quality_gate.get("import_pending_count", 0) or 0),
        "quality_pending_count": int(generated_asset_quality_gate.get("quality_pending_count", 0) or 0),
        "placeholder_count": int(generated_asset_quality_gate.get("placeholder_count", 0) or 0),
        "ready_count": int(generated_asset_quality_gate.get("ready_count", 0) or 0),
        "target_asset": target_generated_asset_context,
        "placeholder_root": "/Game/Generated/Placeholders",
        "placeholder_tool": "skill_compile_ide_companion_placeholder_manifest",
        "blocker_tool": "skill_compile_ide_companion_blocker_resolution",
        "lifecycle_tool": "skill_compile_ide_companion_asset_lifecycle_manifest",
        "review_tool": "chat_get_cockpit_overview",
        "requires_session_plan": True,
        "stop_before_editor_or_provider": True,
    }


def asset_lifecycle_manifest_compile_context(
    *,
    ledger: Dict[str, Any],
    work_order_template: Dict[str, Any],
    asset_lifecycles: List[Dict[str, Any]],
    generated_asset_quality_gate: Dict[str, Any],
    readiness_policy: Dict[str, Any],
) -> Dict[str, Any]:
    if not ledger:
        return {}
    session_asset_prompt_count = int(ledger.get("generated_asset_prompt_count", 0) or 0)
    session_animation_prompt_count = int(ledger.get("generated_animation_prompt_count", 0) or 0)
    template_asset_count = int(work_order_template.get("asset_count", 0) or 0)
    template_animation_prompt_count = int(work_order_template.get("generated_animation_prompt_count", 0) or 0)
    planned_asset_count = max(session_asset_prompt_count, template_asset_count)
    planned_animation_count = max(session_animation_prompt_count, template_animation_prompt_count)
    planned_count = planned_asset_count + planned_animation_count
    if planned_count <= 0 and not asset_lifecycles:
        return {}
    paid_generation = readiness_policy.get("paid_generation") if isinstance(readiness_policy.get("paid_generation"), dict) else {}
    paid_animation = readiness_policy.get("paid_animation_generation") if isinstance(readiness_policy.get("paid_animation_generation"), dict) else {}
    missing_gates = []
    missing_gates.extend(str(gate) for gate in paid_generation.get("missing_gates", []) if str(gate).strip())
    missing_gates.extend(str(gate) for gate in paid_animation.get("missing_gates", []) if str(gate).strip())
    lifecycle_asset_count = sum(int(lifecycle.get("asset_count", 0) or 0) for lifecycle in asset_lifecycles if isinstance(lifecycle, dict))
    lifecycle_animation_count = sum(int(lifecycle.get("animation_asset_count", 0) or 0) for lifecycle in asset_lifecycles if isinstance(lifecycle, dict))
    lifecycle_pending_count = sum(int(lifecycle.get("blocked_or_pending_count", 0) or 0) for lifecycle in asset_lifecycles if isinstance(lifecycle, dict))
    lifecycle_animation_pending_count = sum(int(lifecycle.get("animation_pending_count", 0) or 0) for lifecycle in asset_lifecycles if isinstance(lifecycle, dict))
    has_session_plan = bool(ledger.get("has_session_plan", False))
    if not has_session_plan:
        state = "blocked"
    elif not asset_lifecycles:
        state = "ready_to_compile"
    elif lifecycle_pending_count or lifecycle_animation_pending_count:
        state = "refresh_recommended"
    else:
        state = "manifest_present"
    return {
        "schema": "unreal_mcp_chat_asset_lifecycle_manifest_compile_context.v1",
        "state": state,
        "session_name": str(ledger.get("session_name", "")),
        "ledger_path": str(ledger.get("ledger_path", "")),
        "has_session_plan": has_session_plan,
        "session_plan_phase_count": int(ledger.get("session_plan_phase_count", 0) or 0),
        "target_phase": str(work_order_template.get("target_phase") or ledger.get("work_order_phase") or ledger.get("next_phase") or ""),
        "template_name": str(work_order_template.get("template_name", "")),
        "display_name": str(work_order_template.get("display_name", "")),
        "planned_asset_prompt_count": planned_asset_count,
        "planned_animation_prompt_count": planned_animation_count,
        "generated_animation_prompt_preview": bounded_string_preview(work_order_template.get("generated_animation_prompt_preview", []), 5),
        "generated_animation_tool_preview": bounded_string_preview(work_order_template.get("generated_animation_tool_preview", []), 8),
        "generated_animation_proof_required_preview": bounded_string_preview(work_order_template.get("generated_animation_proof_required_preview", []), 8),
        "estimated_uthana_motion_seconds": max(
            int(ledger.get("estimated_uthana_motion_seconds", 0) or 0),
            int(work_order_template.get("estimated_uthana_motion_seconds", 0) or 0),
        ),
        "manifest_count": len(asset_lifecycles),
        "manifest_asset_count": lifecycle_asset_count,
        "manifest_animation_asset_count": lifecycle_animation_count,
        "manifest_pending_count": lifecycle_pending_count + lifecycle_animation_pending_count,
        "generated_asset_quality_state": str(generated_asset_quality_gate.get("state", "")),
        "missing_future_gate_preview": bounded_string_preview(sorted(set(missing_gates)), 8),
        "compile_tool": "skill_compile_ide_companion_asset_lifecycle_manifest",
        "placeholder_tool": "skill_compile_ide_companion_placeholder_manifest",
        "review_tool": "chat_get_cockpit_overview",
        "requires_session_plan": True,
        "write_manifest_recommended": True,
        "future_network_required": planned_count > 0,
        "future_spend_required": planned_count > 0,
        "network_required_now": False,
        "spend_required_now": False,
        "unreal_editor_required_now": False,
        "stop_before_provider_or_editor": True,
        "no_provider_call": True,
    }


def resume_session_context(ledger: Dict[str, Any]) -> Dict[str, Any]:
    if not ledger:
        return {}
    blocking_gates = ledger.get("blocking_gates") if isinstance(ledger.get("blocking_gates"), list) else []
    preview_events = ledger.get("preview_events") if isinstance(ledger.get("preview_events"), list) else []
    return {
        "session_name": str(ledger.get("session_name", "")),
        "ledger_path": str(ledger.get("ledger_path", "")),
        "event_count": int(ledger.get("event_count", 0) or 0),
        "completed_phase_count": int(ledger.get("completed_phase_count", 0) or 0),
        "latest_phase": str(ledger.get("latest_phase", "")),
        "latest_summary": str(ledger.get("latest_summary", "")),
        "next_phase": str(ledger.get("next_phase", "")),
        "next_tool": str(ledger.get("next_tool", "")),
        "work_order_phase": str(ledger.get("work_order_phase", "")),
        "blocking_gate_count": len(blocking_gates),
        "blocking_gate_preview": bounded_string_preview(blocking_gates, 5),
        "preview_event_count": len(preview_events),
        "resume_tool": "skill_resume_ide_companion_session",
        "dashboard_tool": "skill_compile_ide_companion_dashboard",
        "stop_before_editor_mutation": True,
    }


def dashboard_context(
    *,
    ledger: Dict[str, Any],
    queues: List[Dict[str, Any]],
    readiness_policy: Dict[str, Any],
    evidence_recording: Dict[str, Any],
    blocker_resolutions: Dict[str, Any],
    repair_loop: Dict[str, Any],
    generated_asset_quality_gate: Dict[str, Any],
    runtime_review: Dict[str, Any],
) -> Dict[str, Any]:
    if not ledger:
        return {}
    evidence_items = evidence_recording.get("items") if isinstance(evidence_recording.get("items"), list) else []
    queued_action_count = sum(int(queue.get("action_count", 0) or 0) for queue in queues)
    executable_queue_count = sum(1 for queue in queues if queue.get("can_execute_now"))
    return {
        "session_name": str(ledger.get("session_name", "")),
        "ledger_path": str(ledger.get("ledger_path", "")),
        "event_count": int(ledger.get("event_count", 0) or 0),
        "completed_phase_count": int(ledger.get("completed_phase_count", 0) or 0),
        "latest_phase": str(ledger.get("latest_phase", "")),
        "next_phase": str(ledger.get("next_phase", "")),
        "work_order_phase": str(ledger.get("work_order_phase", "")),
        "readiness_state": str(readiness_policy.get("state", "")),
        "blocked_policy_count": int(readiness_policy.get("blocked_policy_count", 0) or 0),
        "blocking_gate_count": int(blocker_resolutions.get("blocking_gate_count", 0) or 0),
        "queue_count": len(queues),
        "queued_action_count": queued_action_count,
        "executable_queue_count": executable_queue_count,
        "evidence_item_count": len(evidence_items),
        "generated_asset_state": str(generated_asset_quality_gate.get("state", "")),
        "generated_asset_count": int(generated_asset_quality_gate.get("asset_count", 0) or 0),
        "runtime_review_state": str(runtime_review.get("state", "")),
        "repair_loop_state": str(repair_loop.get("state", "")),
        "dashboard_tool": "skill_compile_ide_companion_dashboard",
        "review_tool": "chat_get_cockpit_overview",
        "stop_before_editor_mutation": True,
    }


def cockpit_workflow_actions(
    *,
    session_name: str,
    ledger: Dict[str, Any],
    queues: List[Dict[str, Any]],
    blocking_gates: List[str],
    readiness_policy: Dict[str, Any],
    work_order_template: Dict[str, Any],
    evidence_recording: Dict[str, Any],
    blocker_resolutions: Dict[str, Any],
    repair_loop: Dict[str, Any],
    asset_lifecycles: List[Dict[str, Any]],
    generated_asset_quality_gate: Dict[str, Any],
    next_safe_step: Dict[str, Any],
    execution_review: Dict[str, Any],
    repair_review: Dict[str, Any],
    runtime_review: Dict[str, Any],
    platform_preflight: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    ledger_path = str(ledger.get("ledger_path", ""))
    target_phase = str(ledger.get("work_order_phase") or ledger.get("next_phase") or "")
    next_queue = queues[0] if queues else {}
    has_ledger = bool(ledger)
    has_queue = bool(queues)
    can_execute_queue = bool(next_queue.get("can_execute_now", False))
    bridge_blocked = "unreal_bridge_reachable" in set(blocking_gates) or any(queue.get("bridge_blocked") for queue in queues)
    session_args = {"session_name": session_name}
    ledger_args = {"ledger_path": ledger_path} if ledger_path else session_args
    target_evidence_item = select_recordable_evidence_item(evidence_recording)
    target_runtime_evidence_item = select_evidence_item_by_id(evidence_recording, "record_runtime_verification")
    target_queued_evidence_item = select_evidence_item_by_id(evidence_recording, "record_editor_queue_1")
    target_paid_generation_evidence_item = select_evidence_item_by_id(evidence_recording, "record_paid_generation_evidence")
    target_generated_asset_evidence_item = select_evidence_item_by_id(evidence_recording, "record_generated_asset_quality_gate")
    target_generated_animation_evidence_item = select_evidence_item_by_id(evidence_recording, "record_generated_animation_evidence")
    target_feature_completion_contract_item = select_evidence_item_by_id(evidence_recording, "record_feature_completion_contract")
    target_platform_stability_evidence_item = select_evidence_item_by_id(evidence_recording, "record_platform_stability_review")
    target_dirty_promotion_evidence_item = select_evidence_item_by_id(evidence_recording, "record_dirty_promotion_review")
    target_provider_config_evidence_item = select_evidence_item_by_id(evidence_recording, "record_provider_config_review")
    target_bridge_ping_evidence_item = select_evidence_item_by_id(evidence_recording, "record_bridge_ping_receipt")
    target_chat_cockpit_start_evidence_item = select_evidence_item_by_id(evidence_recording, "record_chat_cockpit_start_receipt")
    evidence_phase = str(target_evidence_item.get("phase_name") or target_phase)
    evidence_type = str(target_evidence_item.get("evidence_type") or "note")
    evidence_summary = str(target_evidence_item.get("suggested_summary") or "Record cockpit-observed evidence for the current phase.")
    evidence_artifacts = target_evidence_item.get("required_artifacts") if isinstance(target_evidence_item.get("required_artifacts"), list) else []
    queued_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_queued_evidence_item.get("phase_name") or target_phase or "editor_implementation"),
        "evidence_type": str(target_queued_evidence_item.get("evidence_type") or "editor_queue"),
        "summary": str(target_queued_evidence_item.get("suggested_summary") or "Record queued editor action compile/readback evidence."),
        "artifacts": target_queued_evidence_item.get("required_artifacts") if isinstance(target_queued_evidence_item.get("required_artifacts"), list) else [],
    }
    runtime_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_runtime_evidence_item.get("phase_name") or target_phase or "runtime_verification"),
        "evidence_type": str(target_runtime_evidence_item.get("evidence_type") or "runtime_verification"),
        "summary": str(target_runtime_evidence_item.get("suggested_summary") or "Record runtime verification evidence for the current work order."),
        "artifacts": target_runtime_evidence_item.get("required_artifacts") if isinstance(target_runtime_evidence_item.get("required_artifacts"), list) else [],
    }
    generated_asset_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_generated_asset_evidence_item.get("phase_name") or target_phase or "asset_generation"),
        "evidence_type": str(target_generated_asset_evidence_item.get("evidence_type") or "generated_asset_quality_gate"),
        "summary": str(target_generated_asset_evidence_item.get("suggested_summary") or "Record generated asset quality-gate evidence."),
        "artifacts": target_generated_asset_evidence_item.get("required_artifacts") if isinstance(target_generated_asset_evidence_item.get("required_artifacts"), list) else [],
    }
    paid_generation_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_paid_generation_evidence_item.get("phase_name") or target_phase or "asset_generation"),
        "evidence_type": str(target_paid_generation_evidence_item.get("evidence_type") or "paid_generation_evidence"),
        "summary": str(target_paid_generation_evidence_item.get("suggested_summary") or "Record wallet, allowance, and spend/usage approval evidence before paid provider work."),
        "artifacts": target_paid_generation_evidence_item.get("required_artifacts") if isinstance(target_paid_generation_evidence_item.get("required_artifacts"), list) else [],
    }
    generated_animation_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_generated_animation_evidence_item.get("phase_name") or target_phase or "animation_generation"),
        "evidence_type": str(target_generated_animation_evidence_item.get("evidence_type") or "generated_animation_evidence"),
        "summary": str(target_generated_animation_evidence_item.get("suggested_summary") or "Record generated animation evidence gates."),
        "artifacts": target_generated_animation_evidence_item.get("required_artifacts") if isinstance(target_generated_animation_evidence_item.get("required_artifacts"), list) else [],
    }
    feature_completion_contract_arguments = {
        "session_name": session_name,
        "phase_name": str(target_feature_completion_contract_item.get("phase_name") or target_phase or "runtime_verification"),
        "evidence_type": str(target_feature_completion_contract_item.get("evidence_type") or "feature_completion_contract"),
        "summary": str(target_feature_completion_contract_item.get("suggested_summary") or "Record gameplay feature completion-contract proof gates."),
        "artifacts": target_feature_completion_contract_item.get("required_artifacts") if isinstance(target_feature_completion_contract_item.get("required_artifacts"), list) else [],
    }
    platform_stability_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_platform_stability_evidence_item.get("phase_name") or "session_preflight"),
        "evidence_type": str(target_platform_stability_evidence_item.get("evidence_type") or "platform_stability_review"),
        "summary": str(target_platform_stability_evidence_item.get("suggested_summary") or "Record the local platform-stability review receipt."),
        "artifacts": target_platform_stability_evidence_item.get("required_artifacts") if isinstance(target_platform_stability_evidence_item.get("required_artifacts"), list) else [],
    }
    dirty_promotion_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_dirty_promotion_evidence_item.get("phase_name") or "session_preflight"),
        "evidence_type": str(target_dirty_promotion_evidence_item.get("evidence_type") or "dirty_promotion_review"),
        "summary": str(target_dirty_promotion_evidence_item.get("suggested_summary") or "Record the local dirty-promotion review receipt."),
        "artifacts": target_dirty_promotion_evidence_item.get("required_artifacts") if isinstance(target_dirty_promotion_evidence_item.get("required_artifacts"), list) else [],
    }
    provider_config_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_provider_config_evidence_item.get("phase_name") or "session_preflight"),
        "evidence_type": str(target_provider_config_evidence_item.get("evidence_type") or "provider_config_review"),
        "summary": str(target_provider_config_evidence_item.get("suggested_summary") or "Record the masked provider config review receipt."),
        "artifacts": target_provider_config_evidence_item.get("required_artifacts") if isinstance(target_provider_config_evidence_item.get("required_artifacts"), list) else [],
    }
    bridge_ping_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_bridge_ping_evidence_item.get("phase_name") or "session_preflight"),
        "evidence_type": str(target_bridge_ping_evidence_item.get("evidence_type") or "bridge_ping_receipt"),
        "summary": str(target_bridge_ping_evidence_item.get("suggested_summary") or "Record the bridge ping receipt state."),
        "artifacts": target_bridge_ping_evidence_item.get("required_artifacts") if isinstance(target_bridge_ping_evidence_item.get("required_artifacts"), list) else [],
    }
    chat_cockpit_start_evidence_arguments = {
        "session_name": session_name,
        "phase_name": str(target_chat_cockpit_start_evidence_item.get("phase_name") or "session_preflight"),
        "evidence_type": str(target_chat_cockpit_start_evidence_item.get("evidence_type") or "chat_cockpit_start_receipt"),
        "summary": str(target_chat_cockpit_start_evidence_item.get("suggested_summary") or "Record the chat cockpit startup receipt."),
        "artifacts": target_chat_cockpit_start_evidence_item.get("required_artifacts") if isinstance(target_chat_cockpit_start_evidence_item.get("required_artifacts"), list) else [],
    }
    target_blocker_resolution = select_blocker_resolution_target(blocker_resolutions)
    blocker_arguments = {**ledger_args, "current_blockers": blocking_gates}
    if target_blocker_resolution:
        blocker_arguments["target_blocker"] = target_blocker_resolution.get("blocker", "")
        blocker_arguments["preferred_strategy"] = target_blocker_resolution.get("recommended_strategy", "")
    target_generated_animation_lifecycle_context = generated_animation_lifecycle_context(
        asset_lifecycles=asset_lifecycles,
        readiness_policy=readiness_policy,
    )
    queue_target_context = build_queue_target_context(
        target_phase=target_phase,
        work_order_template=work_order_template,
        ledger_path=ledger_path,
        generated_animation_context=target_generated_animation_lifecycle_context,
    )
    queue_arguments = {"queue_name": "editor_queue"}
    if target_phase:
        queue_arguments["target_phase"] = target_phase
    if ledger_path:
        queue_arguments["ledger_path"] = ledger_path
    target_repair_context = select_repair_context(repair_loop, target_phase or "repair")
    repair_arguments = {**ledger_args, "target_phase": target_phase or "repair"}
    if target_repair_context:
        repair_arguments["target_repair_id"] = target_repair_context.get("id", "")
        repair_arguments["recommended_tool"] = target_repair_context.get("recommended_tool", "")
    target_execute_context = select_execute_context(next_queue)
    target_queue_review_context = queue_review_context(
        queues,
        next_queue,
        work_order_template=work_order_template,
        generated_animation_context=target_generated_animation_lifecycle_context,
    )
    target_evidence_review_context = evidence_review_context(evidence_recording, target_evidence_item)
    target_execution_review_context = execution_review_context(execution_review) if execution_review else {}
    target_repair_review_context = repair_review_context(repair_review) if repair_review else {}
    target_runtime_review_context = runtime_review_context(runtime_review) if runtime_review else {}
    target_generated_asset_context = select_generated_asset_context(generated_asset_quality_gate)
    target_generated_asset_review_context = generated_asset_review_context(generated_asset_quality_gate, target_generated_asset_context)
    target_generated_asset_lifecycle_context = generated_asset_lifecycle_context(
        asset_lifecycles,
        generated_asset_quality_gate,
        target_generated_asset_context,
    )
    target_asset_lifecycle_compile_context = asset_lifecycle_manifest_compile_context(
        ledger=ledger,
        work_order_template=work_order_template,
        asset_lifecycles=asset_lifecycles,
        generated_asset_quality_gate=generated_asset_quality_gate,
        readiness_policy=readiness_policy,
    )
    target_generated_asset_import_context = generated_asset_import_context(
        generated_asset_quality_gate=generated_asset_quality_gate,
        readiness_policy=readiness_policy,
    )
    target_generated_asset_quality_proof_context = generated_asset_quality_proof_context(
        generated_asset_quality_gate=generated_asset_quality_gate,
        readiness_policy=readiness_policy,
    )
    target_generated_asset_replacement_context = generated_asset_replacement_context(
        asset_lifecycles=asset_lifecycles,
        readiness_policy=readiness_policy,
    )
    target_platform_preflight_context = platform_preflight if isinstance(platform_preflight, dict) and platform_preflight else platform_preflight_context()
    target_provider_spend_context = provider_spend_context(
        readiness_policy=readiness_policy,
        generated_asset_quality_gate=generated_asset_quality_gate,
        target_generated_asset_context=target_generated_asset_context,
        platform_preflight=target_platform_preflight_context,
    )
    target_provider_config_context = provider_config_context(
        platform_preflight=target_platform_preflight_context,
        readiness_policy=readiness_policy,
    )
    target_generated_asset_provider_task_context = generated_asset_provider_task_context(
        asset_lifecycles=asset_lifecycles,
        readiness_policy=readiness_policy,
    )
    target_bridge_wrapper_context = bridge_wrapper_coverage_context()
    target_test_lane_context = test_lane_context()
    target_live_editor_context = live_editor_bridge_context(
        platform_preflight=target_platform_preflight_context,
        readiness_policy=readiness_policy,
        queues=queues,
        next_safe_step=next_safe_step,
        execution_review=execution_review,
        runtime_review=runtime_review,
    )
    target_wip_promotion_context = wip_promotion_context(
        platform_preflight=target_platform_preflight_context,
        bridge_wrapper_coverage=target_bridge_wrapper_context,
        test_lanes=target_test_lane_context,
        readiness_policy=readiness_policy,
    )
    target_placeholder_context = placeholder_manifest_context(
        ledger=ledger,
        readiness_policy=readiness_policy,
        blocker_resolutions=blocker_resolutions,
        generated_asset_quality_gate=generated_asset_quality_gate,
        target_generated_asset_context=target_generated_asset_context,
    )
    target_readiness_policy_context = readiness_policy_context(readiness_policy)
    target_readiness_repair_queue_context = readiness_repair_queue_context(
        target_platform_preflight_context.get("readiness_repair_queue", {})
        if isinstance(target_platform_preflight_context, dict)
        else {}
    )
    target_blueprint_mutation_context = blueprint_mutation_context(
        readiness_policy=readiness_policy,
        work_order_template=work_order_template,
        queues=queues,
        target_phase=target_phase,
        readiness_repair_queue=(
            target_platform_preflight_context.get("readiness_repair_queue", {})
            if isinstance(target_platform_preflight_context, dict)
            else {}
        ),
        blueprint_evidence=(
            target_platform_preflight_context.get("blueprint_mutation_evidence_contract", {})
            if isinstance(target_platform_preflight_context, dict)
            else {}
        ),
    )
    target_start_context = start_session_context(
        session_name=session_name,
        ledger=ledger,
        queues=queues,
        readiness_policy=readiness_policy,
        generated_asset_quality_gate=generated_asset_quality_gate,
    )
    target_status_context = status_refresh_context(
        ledger=ledger,
        queues=queues,
        readiness_policy=readiness_policy,
        evidence_recording=evidence_recording,
        blocker_resolutions=blocker_resolutions,
        generated_asset_quality_gate=generated_asset_quality_gate,
        runtime_review=runtime_review,
    )
    target_work_order_context = work_order_context(
        ledger=ledger,
        readiness_policy=readiness_policy,
        blocker_resolutions=blocker_resolutions,
        work_order_template=work_order_template,
        status_context=target_status_context,
    )
    target_gameplay_template_context = gameplay_template_context(
        ledger=ledger,
        readiness_policy=readiness_policy,
        work_order_template=work_order_template,
    )
    target_resume_context = resume_session_context(ledger)
    target_dashboard_context = dashboard_context(
        ledger=ledger,
        queues=queues,
        readiness_policy=readiness_policy,
        evidence_recording=evidence_recording,
        blocker_resolutions=blocker_resolutions,
        repair_loop=repair_loop,
        generated_asset_quality_gate=generated_asset_quality_gate,
        runtime_review=runtime_review,
    )
    asset_arguments = {**ledger_args}
    if target_generated_asset_context:
        asset_arguments.update({
            "manifest_path": target_generated_asset_context.get("manifest_path", ""),
            "target_asset_id": target_generated_asset_context.get("id", ""),
            "target_asset_state": target_generated_asset_context.get("state", ""),
            "next_gate": target_generated_asset_context.get("next_gate", ""),
        })
    lifecycle_manifest_arguments = {
        "session_plan": "<latest session_plan from ledger, dashboard, or resume output>",
        "placeholder_manifest": "<optional latest unreal_mcp_ide_companion_placeholder_manifest.v1 packet>",
        "preferred_provider": "tripo",
        "write_manifest": True,
        "manifest_name": "asset_lifecycle",
    }
    ledger_detail_arguments = {**ledger_args, "limit": 50}
    target_evidence_ledger_context = evidence_ledger_context(ledger) if has_ledger else {}
    return [
        cockpit_workflow_action(
            action_id="start_companion_session",
            label="Start Companion Session",
            tool="skill_compile_ide_companion_session",
            arguments=session_args,
            enabled=True,
            reason="Create or refresh an IDE companion plan for this session.",
            input_source="session_name plus cockpit readiness, ledger, queue, and generated-asset state",
            target_start_context=target_start_context,
        ),
        cockpit_workflow_action(
            action_id="check_readiness",
            label="Check Readiness",
            tool="gen_compile_ide_companion_readiness",
            arguments=session_args,
            enabled=True,
            reason="Refresh local preflight, bridge, chat, provider, and build gates before execution.",
            input_source="outputs.readiness_policy plus local preflight gates",
            target_readiness_policy_context=target_readiness_policy_context,
        ),
        cockpit_workflow_action(
            action_id="review_readiness_repair_queue",
            label="Review Readiness Repair Queue",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=bool(target_readiness_repair_queue_context),
            reason="Review the prioritized blocker repair queue before running receipt scripts, bridge checks, provider checks, or evidence recording.",
            input_source="outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context.readiness_repair_queue",
            target_readiness_repair_queue_context=target_readiness_repair_queue_context,
        ),
        cockpit_workflow_action(
            action_id="review_platform_preflight_gate",
            label="Review Platform Preflight Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=bool(target_platform_preflight_context),
            reason="Review tool-count reproducibility, dirty-state risk, bridge, chat, provider, build, and readiness gates before risky work.",
            input_source="scripts/audit_ide_companion_readiness.py plus outputs.readiness_policy",
            target_platform_preflight_context=target_platform_preflight_context,
        ),
        cockpit_workflow_action(
            action_id="review_live_editor_bridge_gate",
            label="Review Live Editor Bridge Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=bool(target_live_editor_context),
            reason="Review bridge reachability, queued editor actions, runtime/PIE state, and evidence gates before any live editor work.",
            input_source="outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context plus outputs.next_safe_step, execution_review, and runtime_review",
            target_live_editor_context=target_live_editor_context,
        ),
        cockpit_workflow_action(
            action_id="review_wip_promotion_gate",
            label="Review WIP Promotion Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=bool(target_wip_promotion_context),
            reason="Review whether WIP is stable enough to promote toward main based on registry, CI lane, wrapper, build, dirty-state, and cockpit gates.",
            input_source="outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context plus wrapper and test-lane audits",
            target_wip_promotion_context=target_wip_promotion_context,
        ),
        cockpit_workflow_action(
            action_id="review_blueprint_mutation_gate",
            label="Review Blueprint Mutation Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=bool(target_blueprint_mutation_context),
            reason="Review bridge, pre-read, compile, and readback gates before any Blueprint graph or component mutation.",
            input_source="outputs.readiness_policy.blueprint_mutation plus outputs.work_order_template and outputs.editor_queues",
            target_blueprint_mutation_context=target_blueprint_mutation_context,
        ),
        cockpit_workflow_action(
            action_id="review_bridge_wrapper_coverage",
            label="Review Bridge Wrapper Coverage",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=bool(target_bridge_wrapper_context),
            reason="Review high-value C++ bridge wrapper coverage, Python reachability, tests, and docs before planning more wrapper work.",
            input_source="scripts/audit_high_value_wrapper_coverage.py plus scripts/bridge_command_audit.py",
            target_bridge_wrapper_context=target_bridge_wrapper_context,
        ),
        cockpit_workflow_action(
            action_id="review_test_lane_gates",
            label="Review Test Lane Gates",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=bool(target_test_lane_context),
            reason="Review offline, live-bridge, and paid-provider test lane separation before running checks that could mutate Unreal or spend credits.",
            input_source="scripts/audit_test_lanes.py plus docs/ci-smoke.md",
            target_test_lane_context=target_test_lane_context,
        ),
        cockpit_workflow_action(
            action_id="review_provider_config_gate",
            label="Review Provider Config Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=bool(target_provider_config_context),
            reason="Review masked Tripo/Uthana credential configuration and receipt evidence before wallet checks, spend approval, or provider task submission.",
            input_source="outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context plus provider repair and secret contracts",
            target_provider_config_context=target_provider_config_context,
        ),
        cockpit_workflow_action(
            action_id="refresh_companion_status",
            label="Refresh Companion Status",
            tool="skill_compile_ide_companion_status",
            arguments={
                "session_plan": "<latest session_plan from ledger, dashboard, or resume output>",
                "readiness_report": "outputs.readiness_policy",
                "completed_phases": "<completed phase names from current session plan/status>",
                "evidence": "outputs.evidence_recording plus ledger evidence",
                "current_blockers": blocking_gates,
            },
            enabled=has_ledger,
            reason="Compile a fresh no-spend status receipt from the current plan, readiness, blockers, and evidence.",
            requires_ledger=True,
            input_source="matching_ide_companion_ledger plus outputs.readiness_policy and outputs.evidence_recording",
            target_status_context=target_status_context,
        ),
        cockpit_workflow_action(
            action_id="generate_work_order",
            label="Generate Work Order",
            tool="skill_compile_ide_companion_work_order",
            arguments={
                "session_plan": "<latest session_plan from ledger, dashboard, or resume output>",
                "companion_status": "<latest status receipt from ledger or refresh_companion_status>",
                "target_phase": target_phase,
                "readiness_report": "outputs.readiness_policy",
            },
            enabled=has_ledger,
            reason="Compile the next no-spend executable work order from the current session plan, status, and readiness gates.",
            requires_ledger=True,
            input_source="matching_ide_companion_ledger plus outputs.workflow_actions.refresh_companion_status.target_status_context",
            target_work_order_context=target_work_order_context,
        ),
        cockpit_workflow_action(
            action_id="review_gameplay_template_plan",
            label="Review Gameplay Template Plan",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_gameplay_template_context),
            reason="Review the selected gameplay feature template assets, graph operations, compile/PIE gates, evidence, and repair expectations before queueing editor work.",
            requires_ledger=True,
            input_source="matching_ide_companion_ledger.latest_work_order.feature_template_work plus outputs.work_order_template",
            target_gameplay_template_context=target_gameplay_template_context,
        ),
        cockpit_workflow_action(
            action_id="queue_gameplay_template_next_operation",
            label="Queue Gameplay Template Operation",
            tool="skill_compile_ide_companion_editor_queue",
            arguments={
                "session_plan": "<latest session_plan from ledger, dashboard, or resume output>",
                "companion_status": "<latest status receipt from ledger or refresh_companion_status>",
                "work_order": "<latest work_order with feature_template_work>",
                "queue_name": "gameplay_template_queue",
            },
            enabled=has_ledger and bool(work_order_template.get("next_editor_operation_id")),
            reason="Compile a local bridge-gated editor queue that preserves the selected gameplay template operation and its proof contract.",
            requires_ledger=True,
            input_source="outputs.workflow_actions.review_gameplay_template_plan.target_gameplay_template_context plus matching_ide_companion_ledger.latest_work_order",
            target_gameplay_template_context=target_gameplay_template_context,
            target_queue_context=queue_target_context,
        ),
        cockpit_workflow_action(
            action_id="resume_companion_session",
            label="Resume Companion Session",
            tool="skill_resume_ide_companion_session",
            arguments=ledger_args,
            enabled=has_ledger,
            reason="Resume the local companion ledger and compile the next safe work context.",
            requires_ledger=True,
            input_source="matching_ide_companion_ledger.ledger_path",
            target_resume_context=target_resume_context,
        ),
        cockpit_workflow_action(
            action_id="show_companion_dashboard",
            label="Show Companion Dashboard",
            tool="skill_compile_ide_companion_dashboard",
            arguments=ledger_args,
            enabled=has_ledger,
            reason="Compile the display-ready companion dashboard from the current ledger state.",
            requires_ledger=True,
            input_source="matching_ide_companion_ledger.ledger_path",
            target_dashboard_context=target_dashboard_context,
        ),
        cockpit_workflow_action(
            action_id="show_evidence_ledger",
            label="Show Evidence Ledger",
            tool="chat_get_cockpit_ledger_detail",
            arguments=ledger_detail_arguments,
            enabled=has_ledger,
            reason="Open the bounded evidence ledger detail for timeline, artifact, status, and work-order proof.",
            requires_ledger=True,
            input_source="matching_ide_companion_ledger.ledger_path plus outputs.evidence_timeline",
            target_evidence_ledger_context=target_evidence_ledger_context,
        ),
        cockpit_workflow_action(
            action_id="resolve_blockers",
            label="Resolve Blockers",
            tool="skill_compile_ide_companion_blocker_resolution",
            arguments=blocker_arguments,
            enabled=has_ledger and bool(blocker_resolutions.get("blocking_gate_count", 0)),
            reason="Choose unblock, placeholder, fallback, or stop paths for the current cockpit gates.",
            requires_ledger=True,
            input_source="outputs.blocker_resolutions",
            target_blocker_resolution=target_blocker_resolution,
        ),
        cockpit_workflow_action(
            action_id="review_generated_asset_gate",
            label="Review Generated Asset Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_generated_asset_review_context),
            reason="Review generated-asset provider, placeholder, import, quality, and evidence gates before any provider submission or editor import.",
            requires_ledger=True,
            input_source="outputs.generated_asset_quality_gate",
            target_generated_asset_review_context=target_generated_asset_review_context,
        ),
        cockpit_workflow_action(
            action_id="review_generated_asset_lifecycle_gate",
            label="Review Generated Asset Lifecycle Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_generated_asset_lifecycle_context),
            reason="Review generated-asset prompt, provider, task, placeholder, import, quality, evidence, and stop-condition lifecycle completeness before provider, import, or ledger work.",
            requires_ledger=True,
            input_source="outputs.generated_asset_lifecycles plus outputs.generated_asset_quality_gate",
            target_generated_asset_lifecycle_context=target_generated_asset_lifecycle_context,
        ),
        cockpit_workflow_action(
            action_id="compile_asset_lifecycle_manifest",
            label="Compile Generated Asset Lifecycle",
            tool="skill_compile_ide_companion_asset_lifecycle_manifest",
            arguments=lifecycle_manifest_arguments,
            enabled=has_ledger
            and bool(target_asset_lifecycle_compile_context)
            and bool(target_asset_lifecycle_compile_context.get("has_session_plan", False))
            and (
                int(target_asset_lifecycle_compile_context.get("planned_asset_prompt_count", 0) or 0)
                + int(target_asset_lifecycle_compile_context.get("planned_animation_prompt_count", 0) or 0)
                > 0
            ),
            reason="Compile or refresh the provider-neutral generated mesh and Uthana animation lifecycle manifest from the current companion session plan.",
            requires_ledger=True,
            input_source="matching_ide_companion_ledger.session_plan plus outputs.work_order_template generated prompt counts",
            target_asset_lifecycle_compile_context=target_asset_lifecycle_compile_context,
        ),
        cockpit_workflow_action(
            action_id="review_generated_animation_lifecycle_gate",
            label="Review Generated Animation Lifecycle Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_generated_animation_lifecycle_context),
            reason="Review Uthana motion generation, download, import, retarget, AnimGraph, PIE, and ledger gates before animation provider or editor work.",
            requires_ledger=True,
            input_source="outputs.generated_asset_lifecycles.preview_animation_assets plus outputs.readiness_policy",
            target_generated_animation_lifecycle_context=target_generated_animation_lifecycle_context,
        ),
        cockpit_workflow_action(
            action_id="compile_generated_animation_evidence",
            label="Compile Generated Animation Evidence",
            tool="gen_compile_generated_animation_evidence",
            arguments={
                "session_name": session_name,
                "motion_prompt": target_generated_animation_lifecycle_context.get("target_animation", {}).get("name", "") if target_generated_animation_lifecycle_context else "",
                "motion_id": target_generated_animation_lifecycle_context.get("target_animation", {}).get("motion_id", "") if target_generated_animation_lifecycle_context else "",
                "character_id": target_generated_animation_lifecycle_context.get("target_animation", {}).get("default_character_id", "") if target_generated_animation_lifecycle_context else "",
                "provider_task_result_tool": target_generated_animation_lifecycle_context.get("next_safe_action", {}).get("expected_followup_tool", "") or target_generated_animation_lifecycle_context.get("next_safe_action", {}).get("tool", "") if target_generated_animation_lifecycle_context else "",
                "text_motion_result_json": "<captured gen_uthana_text_to_motion output when task_type=text_to_motion>",
                "job_result_json": "<captured gen_uthana_get_job output when task_type=video_to_motion>",
                "motion_result_json": "<captured gen_uthana_get_motion output when available>",
                "download_allowed_json": "<captured gen_uthana_check_download_allowed output>",
                "download_result_json": "<captured gen_uthana_download_motion output>",
                "import_result_json": "<captured gen_uthana_import_animation_to_project output>",
                "retarget_evidence_json": "<captured retarget/readback proof JSON>",
                "animgraph_evidence_json": "<captured AnimGraph or state-machine proof JSON>",
                "pie_evidence_json": "<captured PIE/runtime proof JSON>",
                "ledger_evidence_json": "<captured ledger evidence JSON>",
                "approval_note": "<human approval after visual/runtime inspection>",
            },
            enabled=has_ledger and bool(target_generated_animation_lifecycle_context),
            reason="Compile a no-spend generated-animation evidence receipt from current Uthana, download, import, retarget, AnimGraph, PIE, ledger, and approval proof.",
            requires_ledger=True,
            input_source="outputs.workflow_actions.review_generated_animation_lifecycle_gate.target_generated_animation_lifecycle_context plus captured provider/editor/runtime/ledger proof JSON",
            target_generated_animation_lifecycle_context=target_generated_animation_lifecycle_context,
        ),
        cockpit_workflow_action(
            action_id="review_generated_asset_import_gate",
            label="Review Generated Asset Import Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_generated_asset_import_context),
            reason="Review import path, placeholder replacement, material/collision/viewport proof, and bridge gates before generated asset import or quality work.",
            requires_ledger=True,
            input_source="outputs.generated_asset_quality_gate.items plus outputs.readiness_policy.editor_mutation",
            target_generated_asset_import_context=target_generated_asset_import_context,
        ),
        cockpit_workflow_action(
            action_id="review_generated_asset_quality_proof_gate",
            label="Review Generated Asset Quality Proof Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_generated_asset_quality_proof_context),
            reason="Review material, collision, viewport, and ledger proof requirements before generated asset quality work or evidence recording.",
            requires_ledger=True,
            input_source="outputs.generated_asset_quality_gate.items plus outputs.readiness_policy.editor_mutation",
            target_generated_asset_quality_proof_context=target_generated_asset_quality_proof_context,
        ),
        cockpit_workflow_action(
            action_id="review_generated_asset_replacement_gate",
            label="Review Generated Asset Replacement Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_generated_asset_replacement_context),
            reason="Review placeholder-to-generated asset mapping, imported asset path, quality proof, bridge gates, and ledger requirements before placeholder replacement.",
            requires_ledger=True,
            input_source="outputs.generated_asset_lifecycles.preview_assets plus outputs.readiness_policy.editor_mutation",
            target_generated_asset_replacement_context=target_generated_asset_replacement_context,
        ),
        cockpit_workflow_action(
            action_id="review_provider_spend_gate",
            label="Review Provider Spend Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_provider_spend_context),
            reason="Review provider credentials, wallet evidence, spend confirmation, and selected provider-pending asset before any paid provider task.",
            requires_ledger=True,
            input_source="outputs.readiness_policy.paid_generation plus outputs.generated_asset_quality_gate",
            target_provider_spend_context=target_provider_spend_context,
        ),
        cockpit_workflow_action(
            action_id="continue_with_placeholder_fallback",
            label="Continue With Placeholder Fallback",
            tool="skill_compile_ide_companion_placeholder_manifest",
            arguments={
                "session_plan": "<latest session_plan from ledger, dashboard, or resume output>",
                "placeholder_root": target_placeholder_context.get("placeholder_root", "/Game/Generated/Placeholders"),
                "blocker_resolution": "<optional latest unreal_mcp_ide_companion_blocker_resolution.v1 packet>",
            },
            enabled=has_ledger
            and bool(target_provider_spend_context.get("fallback_placeholder_available", False))
            and bool(target_placeholder_context),
            reason="Compile the no-spend placeholder manifest when paid provider spend is blocked but playable proof can continue with placeholders.",
            requires_ledger=True,
            input_source="outputs.workflow_actions.review_provider_spend_gate.target_provider_spend_context plus outputs.workflow_actions.compile_placeholder_manifest.target_placeholder_context",
            target_provider_spend_context=target_provider_spend_context,
            target_placeholder_context=target_placeholder_context,
        ),
        cockpit_workflow_action(
            action_id="review_generated_asset_provider_task_gate",
            label="Review Generated Asset Provider Task Gate",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_generated_asset_provider_task_context),
            reason="Review provider task status, task id, download/import readiness, and missing evidence before any provider status poll, download, import, or ledger work.",
            requires_ledger=True,
            input_source="outputs.generated_asset_lifecycles.preview_assets plus outputs.readiness_policy.paid_generation",
            target_generated_asset_provider_task_context=target_generated_asset_provider_task_context,
        ),
        cockpit_workflow_action(
            action_id="resolve_generated_asset",
            label="Resolve Generated Asset",
            tool="skill_compile_ide_companion_asset_lifecycle_manifest",
            arguments=asset_arguments,
            enabled=has_ledger and bool(target_generated_asset_context) and str(target_generated_asset_context.get("state", "")) != "ready",
            reason="Plan the next provider, placeholder, import, quality, or evidence step for the selected generated asset.",
            requires_ledger=True,
            input_source="outputs.generated_asset_quality_gate.items",
            target_generated_asset_context=target_generated_asset_context,
        ),
        cockpit_workflow_action(
            action_id="compile_placeholder_manifest",
            label="Compile Placeholder Manifest",
            tool="skill_compile_ide_companion_placeholder_manifest",
            arguments={
                "session_plan": "<latest session_plan from ledger, dashboard, or resume output>",
                "placeholder_root": target_placeholder_context.get("placeholder_root", "/Game/Generated/Placeholders"),
                "blocker_resolution": "<optional outputs.blocker_resolutions or resolve_blockers result>",
            },
            enabled=has_ledger and bool(target_placeholder_context),
            reason="Compile no-spend placeholder assets for blocked generated assets before provider spend or editor import.",
            requires_ledger=True,
            input_source="outputs.generated_asset_quality_gate plus outputs.workflow_actions.resolve_blockers",
            target_placeholder_context=target_placeholder_context,
        ),
        cockpit_workflow_action(
            action_id="review_editor_queue",
            label="Review Editor Queue",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_queue,
            reason="Review queued editor actions, bridge blockers, evidence requirements, and the next action before execution or queue recompilation.",
            input_source="outputs.editor_queues plus outputs.next_safe_step",
            target_queue_review_context=target_queue_review_context,
        ),
        cockpit_workflow_action(
            action_id="queue_editor_actions",
            label="Queue Editor Actions",
            tool="skill_compile_ide_companion_editor_queue",
            arguments=queue_arguments,
            enabled=has_ledger and bool(target_phase),
            reason="Compile the next bridge-gated editor action queue from the ledger session plan, status, and work order.",
            requires_ledger=True,
            input_source="chat_get_cockpit_ledger_detail.latest_status/latest_work_order plus ledger session_plan",
            target_queue_context=queue_target_context,
        ),
        cockpit_workflow_action(
            action_id="execute_next_safe_step",
            label="Execute Next Safe Step",
            tool=str(next_queue.get("next_action_tool", "")),
            arguments={"queue_path": next_queue.get("queue_path", ""), "action_id": next_queue.get("next_action_id", "")},
            enabled=has_queue and can_execute_queue and not bridge_blocked,
            reason="Run only the next queued editor action after bridge/readiness gates pass.",
            requires_bridge=True,
            requires_ledger=True,
            input_source="outputs.next_safe_step",
            target_execute_context=target_execute_context,
            target_execution_review_context=target_execution_review_context,
        ),
        cockpit_workflow_action(
            action_id="review_evidence_requirements",
            label="Review Evidence Requirements",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(target_evidence_review_context),
            reason="Review pending, blocked, and recorded evidence requirements before writing any ledger evidence.",
            requires_ledger=True,
            input_source="outputs.evidence_recording plus outputs.workflow_actions.record_evidence.target_evidence_context",
            target_evidence_review_context=target_evidence_review_context,
        ),
        cockpit_workflow_action(
            action_id="record_evidence",
            label="Record Evidence",
            tool="skill_record_ide_companion_evidence",
            arguments={
                "session_name": session_name,
                "phase_name": evidence_phase,
                "evidence_type": evidence_type,
                "summary": evidence_summary,
                "artifacts": evidence_artifacts,
            },
            enabled=has_ledger and bool(evidence_phase),
            reason="Append the cockpit-selected evidence row to the ledger.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items",
            target_evidence_item=target_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_platform_stability_review",
            label="Record Platform Stability Review",
            tool="skill_record_ide_companion_evidence",
            arguments=platform_stability_evidence_arguments,
            enabled=has_ledger and bool(target_platform_stability_evidence_item),
            reason="Record the local platform-stability review receipt before claiming WIP is promotion-ready.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_platform_stability_review plus outputs.workflow_actions.review_platform_preflight_gate",
            target_evidence_item=target_platform_stability_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_dirty_promotion_review",
            label="Record Dirty Promotion Review",
            tool="skill_record_ide_companion_evidence",
            arguments=dirty_promotion_evidence_arguments,
            enabled=has_ledger and bool(target_dirty_promotion_evidence_item),
            reason="Record dirty-state grouping and promotion review evidence before staging, cleaning, merging, or promoting WIP.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_dirty_promotion_review plus outputs.workflow_actions.review_wip_promotion_gate",
            target_evidence_item=target_dirty_promotion_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_provider_config_review",
            label="Record Provider Config Review",
            tool="skill_record_ide_companion_evidence",
            arguments=provider_config_evidence_arguments,
            enabled=has_ledger and bool(target_provider_config_evidence_item),
            reason="Record masked Tripo/Uthana provider configuration review before wallet checks, allowance checks, spend approval, or provider task submission.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_provider_config_review plus outputs.workflow_actions.review_provider_config_gate",
            target_evidence_item=target_provider_config_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_bridge_ping_receipt",
            label="Record Bridge Ping Receipt",
            tool="skill_record_ide_companion_evidence",
            arguments=bridge_ping_evidence_arguments,
            enabled=has_ledger and bool(target_bridge_ping_evidence_item),
            reason="Record bridge ping receipt state before any editor mutation, queued action execution, Blueprint change, or PIE run.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_bridge_ping_receipt plus outputs.workflow_actions.review_live_editor_bridge_gate",
            target_evidence_item=target_bridge_ping_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_chat_cockpit_start_receipt",
            label="Record Chat Cockpit Start Receipt",
            tool="skill_record_ide_companion_evidence",
            arguments=chat_cockpit_start_evidence_arguments,
            enabled=has_ledger and bool(target_chat_cockpit_start_evidence_item),
            reason="Record MCP Chat startup and /chat/history health proof without starting processes or killing ports.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_chat_cockpit_start_receipt plus outputs.workflow_actions.review_platform_preflight_gate",
            target_evidence_item=target_chat_cockpit_start_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_queued_action_evidence",
            label="Record Queued Action Evidence",
            tool="skill_record_ide_companion_evidence",
            arguments=queued_evidence_arguments,
            enabled=has_ledger and bool(target_queued_evidence_item),
            reason="Record compile/readback proof for the cockpit-selected queued editor action after execution or explain the blocking gate.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_editor_queue_1 plus outputs.next_safe_step",
            target_evidence_item=target_queued_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_generated_asset_evidence",
            label="Record Generated Asset Evidence",
            tool="skill_record_ide_companion_evidence",
            arguments=generated_asset_evidence_arguments,
            enabled=has_ledger and bool(target_generated_asset_evidence_item),
            reason="Record provider, placeholder, import-path, and quality-gate proof for the cockpit-selected generated asset without submitting provider work or importing assets.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_generated_asset_quality_gate",
            target_evidence_item=target_generated_asset_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_paid_generation_evidence",
            label="Record Paid Generation Evidence",
            tool="skill_record_ide_companion_evidence",
            arguments=paid_generation_evidence_arguments,
            enabled=has_ledger and bool(target_paid_generation_evidence_item),
            reason="Record Tripo wallet, Uthana allowance, and explicit spend/usage approval evidence before paid provider work.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_paid_generation_evidence plus outputs.workflow_actions.review_provider_spend_gate",
            target_evidence_item=target_paid_generation_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_generated_animation_evidence",
            label="Record Generated Animation Evidence",
            tool="skill_record_ide_companion_evidence",
            arguments=generated_animation_evidence_arguments,
            enabled=has_ledger and bool(target_generated_animation_evidence_item),
            reason="Record Uthana motion, download, import, retarget, AnimGraph, PIE, ledger, and approval proof needs without submitting provider work or mutating Unreal.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_generated_animation_evidence plus outputs.workflow_actions.compile_generated_animation_evidence",
            target_evidence_item=target_generated_animation_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="record_feature_completion_contract",
            label="Record Feature Completion Contract",
            tool="skill_record_ide_companion_evidence",
            arguments=feature_completion_contract_arguments,
            enabled=has_ledger and bool(target_feature_completion_contract_item),
            reason="Record the gameplay feature completion contract after required evidence, proof gates, and stop-before-complete checks are reviewed.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_feature_completion_contract plus outputs.work_order_template",
            target_evidence_item=target_feature_completion_contract_item,
        ),
        cockpit_workflow_action(
            action_id="review_runtime_verification",
            label="Review Runtime Verification",
            tool="chat_get_cockpit_overview",
            arguments={**session_args, "message_limit": 20, "limit": 50},
            enabled=has_ledger and bool(runtime_review.get("available")),
            reason="Review compile, readback, PIE, screenshot, and runtime-state proof before verification.",
            requires_ledger=True,
            input_source="outputs.runtime_review plus outputs.runtime_verification",
            target_runtime_review_context=target_runtime_review_context,
        ),
        cockpit_workflow_action(
            action_id="record_runtime_evidence",
            label="Record Runtime Evidence",
            tool="skill_record_ide_companion_evidence",
            arguments=runtime_evidence_arguments,
            enabled=has_ledger and bool(target_runtime_evidence_item),
            reason="Record the cockpit-selected runtime verification proof row after PIE, screenshot, actor-state, compile, and readback evidence is available.",
            requires_ledger=True,
            records_evidence=True,
            input_source="outputs.evidence_recording.items.record_runtime_verification",
            target_evidence_item=target_runtime_evidence_item,
        ),
        cockpit_workflow_action(
            action_id="repair_failed_step",
            label="Repair Failed Step",
            tool="skill_compile_ide_companion_work_order",
            arguments=repair_arguments,
            enabled=has_ledger and bool(work_order_template.get("repair_instruction_count", 0)),
            reason="Use the latest work-order repair hints to compile a bounded repair pass.",
            requires_ledger=True,
            input_source="outputs.repair_loop.items",
            target_repair_context=target_repair_context,
            target_repair_review_context=target_repair_review_context,
        ),
    ]


def blocker_resolution_for_gate(gate: str) -> Dict[str, Any]:
    blocker = str(gate or "").strip()
    if blocker == "unreal_bridge_reachable":
        return {
            "blocker": blocker,
            "severity": "hard_for_editor_mutation",
            "summary": "Unreal bridge is required before Blueprint, actor, PIE, viewport, or queued editor actions.",
            "recommended_strategy": "unblock_first",
            "recommended_tool": "scripts/bridge_ping.py",
            "unblock_action": "Start Unreal Editor with the UnrealMCP plugin loaded, then run python scripts\\bridge_ping.py and confirm Saved\\BridgePing\\last_ping_receipt.json records a successful bridge ping.",
            "fallback_action": "Continue offline planning, work-order compilation, and evidence recording without editor mutation.",
            "evidence_required": "bridge_ping_receipt_success plus readiness gate unreal_bridge_reachable is ready",
            "can_continue_offline": True,
        }
    if blocker == "chat_server_reachable":
        return {
            "blocker": blocker,
            "severity": "hard_for_native_cockpit",
            "summary": "MCP Chat must be reachable before the native editor cockpit can refresh history, actions, or dashboards.",
            "recommended_strategy": "unblock_cockpit_surface",
            "recommended_tool": "gen_compile_ide_companion_readiness",
            "unblock_action": "Start the MCP Chat server with scripts\\start_chat_cockpit_server.ps1, confirm /chat/history?limit=1 returns 200 and Saved\\ChatCockpit\\last_start_receipt.json records success, then rerun readiness.",
            "fallback_action": "Continue offline audits and source-side tests, but do not rely on the native cockpit action rail until chat is reachable.",
            "evidence_required": "readiness gate chat_server_reachable is ready and chat_history_endpoint_ready evidence exists",
            "can_continue_offline": True,
        }
    if blocker == "provider_api_key_configured":
        return {
            "blocker": blocker,
            "severity": "hard_for_paid_generation",
            "summary": "Tripo mesh generation must wait until the mesh provider credential source is configured without exposing the raw key.",
            "recommended_strategy": "configure_provider_secret",
            "recommended_tool": "gen_save_provider_config",
            "unblock_action": "Configure Tripo through the native Generate Settings masked TRIPO_API_KEY field, env TRIPO_API_KEY, or ignored local secrets via gen_save_provider_config, then refresh provider config and wallet evidence before any paid task.",
            "fallback_action": "Continue with prompt manifests, placeholder assets, and no-spend gameplay proof.",
            "evidence_required": "TRIPO_API_KEY auth source plus masked provider config evidence; raw key must not appear in chat, docs, or ledger entries",
            "can_continue_offline": True,
        }
    if blocker == "animation_provider_api_key_configured":
        return {
            "blocker": blocker,
            "severity": "hard_for_paid_animation_generation",
            "summary": "Uthana motion generation must wait until the animation provider credential source is configured without exposing the raw key.",
            "recommended_strategy": "configure_uthana_key_in_native_generate_settings",
            "recommended_tool": "gen_save_provider_config",
            "unblock_action": "Configure Uthana through the native Generate Settings masked UTHANA_API_KEY field, env UTHANA_API_KEY, or ignored local secrets via gen_save_provider_config with store_uthana_api_key=True, then refresh provider config and account allowance before text-to-motion.",
            "fallback_action": "Continue with animation prompt manifests, retarget plans, placeholders, and no-spend proof planning.",
            "evidence_required": "UTHANA_API_KEY auth source plus masked provider config evidence such as gen_get_provider_config uthana_api_key_configured=true; raw key must not appear in chat, docs, or ledger entries",
            "can_continue_offline": True,
        }
    if blocker == "tool_registry_reproducible":
        return {
            "blocker": blocker,
            "severity": "hard_for_platform_stability",
            "summary": "The MCP tool registry must match the recorded baseline before CI, promotion, or editor mutation is trusted.",
            "recommended_strategy": "refresh_tool_registry_evidence",
            "recommended_tool": "scripts/tool_inventory.py",
            "unblock_action": "Run the tool inventory and focused registration tests, then update the recorded baseline only when the intentional tool count change is documented.",
            "fallback_action": "Continue source review only; do not promote WIP or mutate Unreal from an unreproducible registry state.",
            "evidence_required": "tool_inventory.py output plus matching unreal_mcp_server/tests/last_tool_count.txt evidence",
            "can_continue_offline": True,
        }
    if blocker == "test_lane_separation":
        return {
            "blocker": blocker,
            "severity": "hard_for_platform_stability",
            "summary": "Offline, live-bridge, and paid-provider tests must remain separated so default discovery stays no-mutation and no-spend.",
            "recommended_strategy": "repair_test_lane_naming",
            "recommended_tool": "scripts/audit_test_lanes.py",
            "unblock_action": "Rename or move any live-bridge or paid-provider tests out of default test_*.py discovery, then rerun the lane audit and no-mutation suite.",
            "fallback_action": "Do not run broad default CI or promote WIP until lane violations are repaired.",
            "evidence_required": "audit_test_lanes.py ok=true and violation_count=0",
            "can_continue_offline": True,
        }
    if blocker == "build_wrapper_present":
        return {
            "blocker": blocker,
            "severity": "hard_for_platform_stability",
            "summary": "Build wrapper evidence is required before treating the plugin build path as stable.",
            "recommended_strategy": "restore_build_wrapper",
            "recommended_tool": "scripts/audit_ide_companion_readiness.py",
            "unblock_action": "Restore the expected build wrapper or update the preflight wrapper list with a documented replacement, then rerun preflight.",
            "fallback_action": "Continue source-side tests only; do not claim BuildPlugin readiness.",
            "evidence_required": "preflight build_wrapper_exists=true and build_wrapper_status=ready",
            "can_continue_offline": True,
        }
    if blocker == "build_wrapper_references_ready":
        return {
            "blocker": blocker,
            "severity": "hard_for_platform_stability",
            "summary": "Build wrappers must reference existing project, plugin, and Unreal build-tool paths before plugin build health is trusted.",
            "recommended_strategy": "repair_build_wrapper_references",
            "recommended_tool": "scripts/audit_ide_companion_readiness.py",
            "unblock_action": "Fix stale project/plugin/tool paths in the build wrapper or local environment, then rerun preflight until missing reference count is zero.",
            "fallback_action": "Keep WIP source work local and do not promote or run build-dependent live work.",
            "evidence_required": "preflight build_wrapper_status=ready, build_wrapper_missing_reference_count=0, and build_health not blocked",
            "can_continue_offline": True,
        }
    if blocker == "working_branch_is_wip":
        return {
            "blocker": blocker,
            "severity": "hard_for_platform_stability",
            "summary": "Experimental development should happen on wip; main remains the stable promotion target.",
            "recommended_strategy": "return_to_wip",
            "recommended_tool": "git status",
            "unblock_action": "Switch back to the existing wip branch or record a deliberate promotion plan before continuing experimental changes.",
            "fallback_action": "Do not stage, commit, merge, or mutate Unreal from the wrong branch role.",
            "evidence_required": "preflight branch policy shows current=wip and working_branch_ok=true",
            "can_continue_offline": True,
        }
    if blocker == "no_mutation_test_lane_safe":
        return {
            "blocker": blocker,
            "severity": "hard_for_wip_promotion",
            "summary": "WIP cannot move toward main until default offline tests are proven separated from live-bridge and paid-provider lanes.",
            "recommended_strategy": "prove_no_mutation_lane_safe",
            "recommended_tool": "scripts/audit_test_lanes.py",
            "unblock_action": "Run the test-lane audit and no-mutation suite, then repair any default-discovery lane violations before promotion.",
            "fallback_action": "Keep the work on wip and avoid broad release or promotion steps until offline CI is no-mutation.",
            "evidence_required": "audit_test_lanes.py ok=true, violation_count=0, run_no_mutation_unittest.py TRACKED_FILE_MUTATIONS=0, tracked_file_count>0, snapshot_digest_match=true, and snapshot_scope=git_tracked_worktree",
            "can_continue_offline": True,
        }
    if blocker == "high_value_bridge_wrappers_covered":
        return {
            "blocker": blocker,
            "severity": "hard_for_wip_promotion",
            "summary": "WIP promotion must wait until the roadmap's high-value bridge wrappers remain covered by C++, Python, schema, tests, and docs evidence.",
            "recommended_strategy": "repair_wrapper_coverage",
            "recommended_tool": "scripts/audit_high_value_wrapper_coverage.py",
            "unblock_action": "Run the wrapper audit, repair any failing capability with route/schema/test/doc evidence, then rerun focused wrapper tests.",
            "fallback_action": "Continue feature work on wip without claiming the bridge-wrapper roadmap is promotion-ready.",
            "evidence_required": "high-value wrapper audit ok=true with failing_capability_count=0",
            "can_continue_offline": True,
        }
    if blocker == "plugin_build_successful":
        return {
            "blocker": blocker,
            "severity": "hard_for_wip_promotion",
            "summary": "WIP promotion needs recent plugin build success evidence before main can be treated as stable.",
            "recommended_strategy": "refresh_plugin_build_evidence",
            "recommended_tool": "scripts/audit_ide_companion_readiness.py",
            "unblock_action": "Run the documented BuildPlugin wrapper when appropriate, then rerun preflight so last_plugin_build_status and build_health reflect the result.",
            "fallback_action": "Keep source work on wip and do not promote build-dependent changes to main.",
            "evidence_required": "preflight last_plugin_build_status=success and build_health not blocked",
            "can_continue_offline": True,
        }
    if blocker == "dirty_state_grouped_for_promotion":
        return {
            "blocker": blocker,
            "severity": "hard_for_wip_promotion",
            "summary": "WIP promotion must wait until dirty tracked changes are deliberately grouped, reviewed, and proven instead of mixed with unrelated work.",
            "recommended_strategy": "group_dirty_state_for_promotion",
            "recommended_tool": "scripts/write_dirty_promotion_review.py",
            "unblock_action": "Run python scripts\\write_dirty_promotion_review.py to write Saved\\DirtyPromotionReview\\last_review_receipt.json, review each dirty group, keep generated/local artifacts ignored, and only stage or promote an intentional evidence-backed set later.",
            "fallback_action": "Continue implementation and verification on wip; do not stage, commit, merge, or move to main from a high-risk dirty state.",
            "evidence_required": "dirty_promotion_review_receipt plus preflight dirty_risk clean/low with tracked_change_count=0, or a documented human promotion plan for grouped tracked changes",
            "can_continue_offline": True,
        }
    if blocker == "chat_cockpit_reachable":
        return {
            "blocker": blocker,
            "severity": "hard_for_wip_promotion",
            "summary": "The native MCP Chat cockpit should be reachable before promotion so the IDE surface can review dashboards, blockers, queues, and evidence.",
            "recommended_strategy": "restore_chat_cockpit_before_promotion",
            "recommended_tool": "scripts/audit_ide_companion_readiness.py",
            "unblock_action": "Start or repair the SSE MCP Chat server on port 8000, verify /chat/history?limit=1 returns 200, then rerun preflight until chat readiness is restored.",
            "fallback_action": "Continue offline source tests, but do not treat the editor cockpit as promotion-ready.",
            "evidence_required": "preflight ready_for_chat_cockpit=true or chat_cockpit allowed=true with chat_history_endpoint_ready evidence",
            "can_continue_offline": True,
        }
    if blocker in {"api_wallet_has_credits", "wallet_evidence_recorded"}:
        return {
            "blocker": blocker,
            "severity": "hard_for_paid_generation",
            "summary": "Paid mesh or motion generation must wait until wallet, credit, or allowance evidence is recorded.",
            "recommended_strategy": "record_wallet_evidence",
            "recommended_tool": "skill_record_ide_companion_evidence",
            "unblock_action": "Run only approved no-spend provider checks, then record masked wallet or allowance evidence in the companion ledger.",
            "fallback_action": "Continue with prompt manifests, placeholder assets, and no-spend gameplay proof.",
            "evidence_required": "wallet_or_credit_evidence ledger entry",
            "can_continue_offline": True,
        }
    if blocker in {"spend_confirmed", "spend_confirmation_recorded"}:
        return {
            "blocker": blocker,
            "severity": "approval_required",
            "summary": "Paid provider tasks require explicit human spend approval.",
            "recommended_strategy": "stop_and_record",
            "recommended_tool": "skill_record_ide_companion_evidence",
            "unblock_action": "Review prompts, provider, estimated credits or motion seconds with the developer; proceed only after explicit spend/usage confirmation is recorded.",
            "fallback_action": "Keep work in prompt manifests and placeholders until approval is recorded.",
            "evidence_required": "explicit spend or usage approval ledger entry",
            "can_continue_offline": True,
        }
    if blocker == "blueprint_pre_read_evidence":
        return {
            "blocker": blocker,
            "severity": "hard_for_blueprint_mutation",
            "summary": "Blueprint mutation must wait until the target Blueprint or graph has been inspected and recorded.",
            "recommended_strategy": "inspect_before_mutation",
            "recommended_tool": "chat_get_cockpit_overview",
            "unblock_action": "Use the work order to identify the target Blueprint, inspect its graph/component state, and record pre-read evidence before queuing mutation.",
            "fallback_action": "Continue planning and queue review without executing Blueprint mutation.",
            "evidence_required": "blueprint_pre_read ledger evidence",
            "can_continue_offline": True,
        }
    if blocker == "blueprint_compile_plan":
        return {
            "blocker": blocker,
            "severity": "hard_for_blueprint_mutation",
            "summary": "Blueprint mutation must include an explicit compile check after the queued edit.",
            "recommended_strategy": "add_compile_gate",
            "recommended_tool": "skill_compile_ide_companion_work_order",
            "unblock_action": "Regenerate or revise the work order so each Blueprint edit includes a compile check and failure repair path.",
            "fallback_action": "Keep the edit queued but do not execute until compile proof is planned.",
            "evidence_required": "compile_check_after_mutation plan",
            "can_continue_offline": True,
        }
    if blocker == "blueprint_readback_plan":
        return {
            "blocker": blocker,
            "severity": "hard_for_blueprint_mutation",
            "summary": "Blueprint mutation must include graph or component readback after the queued edit.",
            "recommended_strategy": "add_readback_gate",
            "recommended_tool": "skill_compile_ide_companion_work_order",
            "unblock_action": "Regenerate or revise the work order so each Blueprint edit includes readback evidence for the changed graph or component.",
            "fallback_action": "Keep the edit queued but do not execute until readback proof is planned.",
            "evidence_required": "graph_or_component_readback_after_mutation plan",
            "can_continue_offline": True,
        }
    return {
        "blocker": blocker,
        "severity": "unknown",
        "summary": "Unknown blocker should be inspected before execution continues.",
        "recommended_strategy": "refresh_status",
        "recommended_tool": "skill_compile_ide_companion_status",
        "unblock_action": "Refresh readiness/status and inspect the blocker detail.",
        "fallback_action": "Record the blocker and stop this phase cleanly.",
        "evidence_required": "updated readiness/status report",
        "can_continue_offline": False,
    }


def build_blocker_resolution_summary(blocking_gates: List[str]) -> Dict[str, Any]:
    gates = [str(gate) for gate in blocking_gates if str(gate).strip()]
    resolutions = [blocker_resolution_for_gate(gate) for gate in gates]
    hard_count = sum(1 for item in resolutions if str(item.get("severity", "")).startswith("hard_"))
    offline_count = sum(1 for item in resolutions if item.get("can_continue_offline"))
    recommended_tools = []
    for item in resolutions:
        tool = str(item.get("recommended_tool", ""))
        if tool and tool not in recommended_tools:
            recommended_tools.append(tool)
    return {
        "schema": "unreal_mcp_chat_blocker_resolution_summary.v1",
        "blocking_gate_count": len(gates),
        "hard_blocker_count": hard_count,
        "offline_continuation_count": offline_count,
        "recommended_tools": recommended_tools,
        "resolutions": resolutions,
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
    }


def select_blocker_resolution_target(blocker_resolutions: Dict[str, Any]) -> Dict[str, Any]:
    resolutions = blocker_resolutions.get("resolutions") if isinstance(blocker_resolutions.get("resolutions"), list) else []
    candidates = [item for item in resolutions if isinstance(item, dict) and str(item.get("blocker", "")).strip()]
    if not candidates:
        return {}

    def blocker_priority(item: Dict[str, Any]) -> tuple:
        blocker = str(item.get("blocker", ""))
        severity = str(item.get("severity", ""))
        strategy = str(item.get("recommended_strategy", ""))
        if blocker == "unreal_bridge_reachable":
            return (0, blocker)
        if blocker == "chat_server_reachable":
            return (1, blocker)
        if severity == "hard_for_editor_mutation":
            return (2, blocker)
        if severity == "hard_for_blueprint_mutation":
            return (3, blocker)
        if severity == "hard_for_platform_stability":
            return (4, blocker)
        if severity == "hard_for_wip_promotion":
            promotion_order = {
                "dirty_state_grouped_for_promotion": 0,
                "plugin_build_successful": 1,
                "no_mutation_test_lane_safe": 2,
                "high_value_bridge_wrappers_covered": 3,
                "chat_cockpit_reachable": 4,
            }
            return (5, promotion_order.get(blocker, 99), blocker)
        if strategy in {
            "configure_provider_secret",
            "configure_animation_provider_secret",
            "configure_uthana_key_in_native_generate_settings",
        }:
            return (6, blocker)
        if strategy == "record_wallet_evidence":
            return (7, blocker)
        if strategy == "continue_with_placeholders":
            return (8, blocker)
        if severity in {"hard_for_paid_generation", "hard_for_paid_animation_generation"}:
            return (9, blocker)
        if strategy == "stop_and_record":
            return (10, blocker)
        if severity == "approval_required":
            return (11, blocker)
        if severity == "unknown":
            return (12, blocker)
        return (13, blocker)

    selected = sorted(candidates, key=blocker_priority)[0]
    return {
        "blocker": str(selected.get("blocker", "")),
        "severity": str(selected.get("severity", "")),
        "summary": str(selected.get("summary", "")),
        "recommended_strategy": str(selected.get("recommended_strategy", "")),
        "recommended_tool": str(selected.get("recommended_tool", "")),
        "unblock_action": str(selected.get("unblock_action", "")),
        "fallback_action": str(selected.get("fallback_action", "")),
        "evidence_required": str(selected.get("evidence_required", "")),
        "can_continue_offline": bool(selected.get("can_continue_offline", False)),
    }


def cockpit_policy_row(
    *,
    allowed: bool,
    required_gates: List[str],
    missing_gates: List[str],
    evidence_required: List[str],
) -> Dict[str, Any]:
    return {
        "allowed": bool(allowed),
        "required_gates": required_gates,
        "missing_gates": missing_gates,
        "evidence_required": evidence_required,
    }


def build_readiness_policy_summary(
    *,
    blocking_gates: List[str],
    queues: List[Dict[str, Any]],
    work_order_template: Dict[str, Any],
) -> Dict[str, Any]:
    gate_set = {str(gate) for gate in blocking_gates if str(gate).strip()}
    bridge_blocked = "unreal_bridge_reachable" in gate_set or any(queue.get("bridge_blocked") for queue in queues)
    tool_registry_blocked = "tool_registry_reproducible" in gate_set
    provider_blocked = "provider_api_key_configured" in gate_set
    animation_provider_blocked = "animation_provider_api_key_configured" in gate_set
    plugin_build_blocked = "plugin_build_successful" in gate_set
    dirty_state_promotion_blocked = "dirty_state_grouped_for_promotion" in gate_set
    chat_cockpit_blocked = "chat_cockpit_reachable" in gate_set or "chat_server_reachable" in gate_set
    build_wrapper_present_blocked = "build_wrapper_present" in gate_set
    build_wrapper_references_blocked = "build_wrapper_references_ready" in gate_set
    working_branch_blocked = "working_branch_is_wip" in gate_set
    no_mutation_lane_blocked = "no_mutation_test_lane_safe" in gate_set or "test_lane_separation" in gate_set

    editor_missing = []
    if tool_registry_blocked:
        editor_missing.append("tool_registry_reproducible")
    if bridge_blocked:
        editor_missing.append("unreal_bridge_reachable")

    paid_missing = []
    if provider_blocked:
        paid_missing.append("provider_api_key_configured")
    paid_missing.extend(["wallet_evidence_recorded", "spend_confirmation_recorded"])

    animation_paid_missing = []
    if animation_provider_blocked:
        animation_paid_missing.append("animation_provider_api_key_configured")
    animation_paid_missing.extend(["wallet_evidence_recorded", "spend_confirmation_recorded"])

    compile_checks = int(work_order_template.get("compile_check_count", 0) or 0)
    blueprint_missing = list(editor_missing)
    blueprint_missing.append("blueprint_pre_read_evidence")
    if compile_checks <= 0:
        blueprint_missing.append("blueprint_compile_plan")
    blueprint_missing.append("blueprint_readback_plan")
    blueprint_missing = sorted(dict.fromkeys(blueprint_missing))

    wip_promotion_missing = []
    if working_branch_blocked:
        wip_promotion_missing.append("working_branch_is_wip")
    if tool_registry_blocked:
        wip_promotion_missing.append("tool_registry_reproducible")
    if no_mutation_lane_blocked:
        wip_promotion_missing.append("no_mutation_test_lane_safe")
    if build_wrapper_present_blocked:
        wip_promotion_missing.append("build_wrapper_present")
    if build_wrapper_references_blocked:
        wip_promotion_missing.append("build_wrapper_references_ready")
    if plugin_build_blocked:
        wip_promotion_missing.append("plugin_build_successful")
    if dirty_state_promotion_blocked:
        wip_promotion_missing.append("dirty_state_grouped_for_promotion")
    if chat_cockpit_blocked:
        wip_promotion_missing.append("chat_cockpit_reachable")

    policy_rows = {
        "editor_mutation": cockpit_policy_row(
            allowed=not editor_missing,
            required_gates=["tool_registry_reproducible", "unreal_bridge_reachable"],
            missing_gates=editor_missing,
            evidence_required=["successful_bridge_ping"],
        ),
        "paid_generation": cockpit_policy_row(
            allowed=False,
            required_gates=[
                "provider_api_key_configured",
                "wallet_evidence_recorded",
                "spend_confirmation_recorded",
            ],
            missing_gates=paid_missing,
            evidence_required=["provider_key_presence", "wallet_or_credit_evidence", "explicit_spend_confirmation"],
        ),
        "paid_animation_generation": cockpit_policy_row(
            allowed=False,
            required_gates=[
                "animation_provider_api_key_configured",
                "wallet_evidence_recorded",
                "spend_confirmation_recorded",
            ],
            missing_gates=animation_paid_missing,
            evidence_required=["animation_provider_key_presence", "wallet_or_credit_evidence", "explicit_spend_confirmation"],
        ),
        "blueprint_mutation": cockpit_policy_row(
            allowed=False,
            required_gates=[
                "tool_registry_reproducible",
                "unreal_bridge_reachable",
                "blueprint_pre_read_evidence",
                "blueprint_compile_plan",
                "blueprint_readback_plan",
            ],
            missing_gates=blueprint_missing,
            evidence_required=[
                "blueprint_pre_read",
                "compile_check_after_mutation",
                "graph_or_component_readback_after_mutation",
            ],
        ),
        "wip_promotion": cockpit_policy_row(
            allowed=not wip_promotion_missing,
            required_gates=[
                "working_branch_is_wip",
                "tool_registry_reproducible",
                "no_mutation_test_lane_safe",
                "build_wrapper_present",
                "build_wrapper_references_ready",
                "plugin_build_successful",
                "dirty_state_grouped_for_promotion",
                "chat_cockpit_reachable",
            ],
            missing_gates=wip_promotion_missing,
            evidence_required=[
                "current_branch_name",
                "tool_count_matches_baseline",
                "offline_live_paid_test_lane_audit",
                "no_mutation_receipt_tracked_file_count",
                "no_mutation_receipt_snapshot_digest_match",
                "no_mutation_receipt_scope_git_tracked_worktree",
                "build_wrapper_project_and_tool_paths_resolve",
                "last_plugin_build_success",
                "dirty_state_grouped_or_clean",
                "chat_history_endpoint_ready",
            ],
        ),
    }
    blocked_policy_count = sum(1 for row in policy_rows.values() if not row["allowed"])
    return {
        "schema": "unreal_mcp_chat_readiness_policy_summary.v1",
        "state": "blocked" if blocked_policy_count else "ready",
        "blocked_policy_count": blocked_policy_count,
        "editor_mutation": policy_rows["editor_mutation"],
        "paid_generation": policy_rows["paid_generation"],
        "paid_animation_generation": policy_rows["paid_animation_generation"],
        "blueprint_mutation": policy_rows["blueprint_mutation"],
        "wip_promotion": policy_rows["wip_promotion"],
        "recommended_tools": ["gen_compile_ide_companion_readiness", "skill_compile_ide_companion_work_order"],
        "notes": [
            "Cockpit policy is read-only and derives from local ledgers and queued action metadata.",
            "Mesh and Uthana animation provider gates are separate so motion spend readiness is explicit.",
            "Blueprint mutation remains action-specific and blocked until a work order supplies pre-read, compile, and readback requirements.",
            "WIP promotion remains stricter than platform stability and includes branch, test lane, build, dirty-state, and chat cockpit proof.",
        ],
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
    }


def build_runtime_verification_checklist(
    *,
    work_order_template: Dict[str, Any],
    ledger: Dict[str, Any],
    queues: List[Dict[str, Any]],
    blocking_gates: List[str],
) -> Dict[str, Any]:
    target_phase = str(work_order_template.get("target_phase") or ledger.get("work_order_phase") or ledger.get("next_phase") or "")
    bridge_blocked = "unreal_bridge_reachable" in set(blocking_gates) or any(queue.get("bridge_blocked") for queue in queues)
    pie_steps = bounded_string_preview(work_order_template.get("pie_validation_preview", []), 5)
    proof_items = bounded_string_preview(work_order_template.get("evidence_preview", []), 5)
    runtime_proof_items = bounded_string_preview(work_order_template.get("runtime_proof_required_preview", []), 8)
    runtime_proof_tools = bounded_string_preview(work_order_template.get("runtime_proof_tool_preview", []), 8)
    runtime_proof_stops = bounded_string_preview(work_order_template.get("runtime_proof_stop_preview", []), 5)
    runtime_proof_before = bounded_string_preview(work_order_template.get("runtime_proof_required_before_preview", []), 8)
    compile_checks = bounded_string_preview(work_order_template.get("compile_check_preview", []), 3)
    runtime_events = [
        event
        for event in ledger.get("preview_events", [])
        if str(event.get("phase_name", "")) == "runtime_verification"
        or str(event.get("evidence_type", "")).lower() in {"pie", "runtime", "screenshot"}
    ] if isinstance(ledger.get("preview_events"), list) else []

    checklist_items = []
    for index, step in enumerate(pie_steps, start=1):
        checklist_items.append({
            "id": f"pie_validation_{index}",
            "kind": "pie_validation",
            "label": step,
            "state": "blocked" if bridge_blocked else "pending",
            "requires_bridge": True,
            "evidence_required": "PIE log, viewport screenshot, and observed runtime state",
        })
    for index, item in enumerate(proof_items, start=1):
        checklist_items.append({
            "id": f"runtime_evidence_{index}",
            "kind": "evidence_requirement",
            "label": item,
            "state": "recorded" if runtime_events else "pending",
            "requires_bridge": "PIE" in item or "screenshot" in item.lower() or "viewport" in item.lower(),
            "evidence_required": item,
        })
    for index, item in enumerate(runtime_proof_items, start=1):
        requires_bridge = item != "ide_companion_ledger_event"
        checklist_items.append({
            "id": f"runtime_contract_evidence_{index}",
            "kind": "runtime_proof_contract",
            "label": item,
            "state": "blocked" if bridge_blocked and requires_bridge else ("recorded" if runtime_events else "pending"),
            "requires_bridge": requires_bridge,
            "evidence_required": item,
        })

    if pie_steps and not proof_items:
        for index, item in enumerate(["PIE log", "viewport screenshot", "actor state/readback"], start=1):
            checklist_items.append({
                "id": f"runtime_default_evidence_{index}",
                "kind": "evidence_requirement",
                "label": item,
                "state": "recorded" if runtime_events else "pending",
                "requires_bridge": True,
                "evidence_required": item,
            })

    available = bool(pie_steps or proof_items or runtime_proof_items or compile_checks)
    return {
        "schema": "unreal_mcp_chat_runtime_verification_checklist.v1",
        "available": available,
        "target_phase": target_phase,
        "state": "blocked" if bridge_blocked and available else ("pending" if available else "missing"),
        "bridge_blocked": bridge_blocked,
        "pie_validation_count": int(work_order_template.get("pie_validation_count", len(pie_steps)) or 0),
        "compile_check_count": int(work_order_template.get("compile_check_count", len(compile_checks)) or 0),
        "evidence_requirement_count": int(work_order_template.get("evidence_requirement_count", len(proof_items)) or 0),
        "runtime_proof_contract_schema": str(work_order_template.get("runtime_proof_contract_schema", "")),
        "runtime_proof_mode": str(work_order_template.get("runtime_proof_mode", "")),
        "runtime_proof_required_count": int(work_order_template.get("runtime_proof_required_count", len(runtime_proof_items)) or 0),
        "runtime_proof_required_before_count": int(work_order_template.get("runtime_proof_required_before_count", len(runtime_proof_before)) or 0),
        "runtime_proof_required_before_preview": runtime_proof_before,
        "runtime_proof_required_preview": runtime_proof_items,
        "runtime_proof_tool_preview": runtime_proof_tools,
        "runtime_proof_stop_preview": runtime_proof_stops,
        "runtime_evidence_event_count": len(runtime_events),
        "compile_check_preview": compile_checks,
        "items": checklist_items,
        "network_required": False,
        "unreal_editor_required": bool(available),
        "spend_required": False,
    }


def build_runtime_review(runtime_verification: Dict[str, Any]) -> Dict[str, Any]:
    runtime_items = runtime_verification.get("items") if isinstance(runtime_verification.get("items"), list) else []
    proof_preview = [
        str(item.get("label") or item.get("evidence_required") or item.get("id", ""))
        for item in runtime_items
        if isinstance(item, dict)
    ]
    blocked_count = sum(1 for item in runtime_items if isinstance(item, dict) and item.get("state") == "blocked")
    pending_count = sum(1 for item in runtime_items if isinstance(item, dict) and item.get("state") == "pending")
    recorded_count = sum(1 for item in runtime_items if isinstance(item, dict) and item.get("state") == "recorded")
    available = bool(runtime_verification.get("available"))
    bridge_blocked = bool(runtime_verification.get("bridge_blocked", False))
    state = str(runtime_verification.get("state", "missing") or "missing")
    return {
        "schema": "unreal_mcp_chat_runtime_review.v1",
        "available": available,
        "state": state,
        "target_phase": str(runtime_verification.get("target_phase", "")),
        "can_verify_now": bool(available and not bridge_blocked),
        "requires_bridge": bool(runtime_verification.get("unreal_editor_required", False)),
        "bridge_blocked": bridge_blocked,
        "pie_validation_count": int(runtime_verification.get("pie_validation_count", 0) or 0),
        "compile_check_count": int(runtime_verification.get("compile_check_count", 0) or 0),
        "evidence_requirement_count": int(runtime_verification.get("evidence_requirement_count", 0) or 0),
        "runtime_proof_contract_schema": str(runtime_verification.get("runtime_proof_contract_schema", "")),
        "runtime_proof_mode": str(runtime_verification.get("runtime_proof_mode", "")),
        "runtime_proof_required_count": int(runtime_verification.get("runtime_proof_required_count", 0) or 0),
        "runtime_proof_required_before_count": int(runtime_verification.get("runtime_proof_required_before_count", 0) or 0),
        "runtime_proof_required_before_preview": bounded_string_preview(runtime_verification.get("runtime_proof_required_before_preview", []), 8),
        "runtime_proof_required_preview": bounded_string_preview(runtime_verification.get("runtime_proof_required_preview", []), 8),
        "runtime_proof_tool_preview": bounded_string_preview(runtime_verification.get("runtime_proof_tool_preview", []), 8),
        "runtime_proof_stop_preview": bounded_string_preview(runtime_verification.get("runtime_proof_stop_preview", []), 5),
        "runtime_evidence_event_count": int(runtime_verification.get("runtime_evidence_event_count", 0) or 0),
        "runtime_item_count": len(runtime_items),
        "blocked_item_count": blocked_count,
        "pending_item_count": pending_count,
        "recorded_item_count": recorded_count,
        "compile_check_preview": bounded_string_preview(runtime_verification.get("compile_check_preview", []), 4),
        "runtime_proof_preview": bounded_string_preview(proof_preview, 5),
        "policy_preview": [
            "Confirm compile and graph/component readback evidence before PIE proof.",
            "Capture only the scoped runtime probe required by the current work order.",
            "Stop if bridge, readiness, or PIE gates are blocked.",
            "Record PIE log, viewport screenshot, and observed actor state before continuing.",
        ],
        "review_tool": "chat_get_cockpit_overview",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "stop_after_runtime_probe": True,
        "network_required": False,
        "unreal_editor_required": bool(runtime_verification.get("unreal_editor_required", False)),
        "spend_required": False,
    }


def build_repair_loop_summary(
    *,
    work_order_template: Dict[str, Any],
    runtime_verification: Dict[str, Any],
    blocking_gates: List[str],
) -> Dict[str, Any]:
    repair_hints = bounded_string_preview(work_order_template.get("repair_preview", []), 5)
    compile_checks = bounded_string_preview(work_order_template.get("compile_check_preview", []), 3)
    evidence_items = bounded_string_preview(work_order_template.get("evidence_preview", []), 5)
    bridge_blocked = "unreal_bridge_reachable" in set(blocking_gates)
    available = bool(repair_hints)
    repair_items = [
        {
            "id": f"repair_hint_{index}",
            "kind": "repair_instruction",
            "label": hint,
            "state": "blocked" if bridge_blocked else "ready",
            "requires_bridge": True,
            "follow_up": "Compile a repair work order, apply one scoped fix, then collect compile/readback/runtime evidence.",
        }
        for index, hint in enumerate(repair_hints, start=1)
    ]
    return {
        "schema": "unreal_mcp_chat_repair_loop_summary.v1",
        "available": available,
        "state": "blocked" if available and bridge_blocked else ("ready" if available else "missing"),
        "bridge_blocked": bridge_blocked,
        "repair_instruction_count": int(work_order_template.get("repair_instruction_count", len(repair_hints)) or 0),
        "stop_condition_count": int(work_order_template.get("stop_condition_count", 0) or 0),
        "runtime_state": runtime_verification.get("state", "missing"),
        "runtime_item_count": len(runtime_verification.get("items", [])) if isinstance(runtime_verification.get("items"), list) else 0,
        "compile_check_preview": compile_checks,
        "evidence_preview": evidence_items,
        "items": repair_items,
        "recommended_tool": "skill_compile_ide_companion_work_order",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "network_required": False,
        "unreal_editor_required": available,
        "spend_required": False,
    }


def evidence_recording_item(
    *,
    item_id: str,
    source: str,
    phase_name: str,
    evidence_type: str,
    label: str,
    required_artifacts: List[str],
    state: str,
    suggested_summary: str,
    requires_bridge: bool = False,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    item = {
        "id": item_id,
        "source": source,
        "phase_name": phase_name,
        "evidence_type": evidence_type,
        "label": label,
        "required_artifacts": required_artifacts,
        "required_artifact_count": len(required_artifacts),
        "state": state,
        "suggested_summary": suggested_summary,
        "requires_bridge": bool(requires_bridge),
    }
    if metadata:
        item["metadata"] = {
            str(key): value
            for key, value in metadata.items()
            if isinstance(key, str) and value not in ("", None, [], {})
        }
    return item


def readiness_policy_evidence_artifacts(readiness_policy: Dict[str, Any]) -> List[str]:
    artifacts: List[str] = []
    for section in ("editor_mutation", "paid_generation", "paid_animation_generation", "blueprint_mutation", "wip_promotion"):
        row = readiness_policy.get(section)
        if not isinstance(row, dict):
            continue
        missing_gates = row.get("missing_gates")
        if isinstance(missing_gates, list):
            for gate in missing_gates:
                gate_text = str(gate).strip()
                if gate_text and gate_text not in artifacts:
                    artifacts.append(gate_text)
        evidence_required = row.get("evidence_required")
        if isinstance(evidence_required, list):
            for evidence in evidence_required:
                evidence_text = str(evidence).strip()
                artifact = f"evidence_required:{evidence_text}" if evidence_text else ""
                if artifact and artifact not in artifacts:
                    artifacts.append(artifact)
    return artifacts[:24]


def readiness_repair_queue_evidence_artifacts(readiness_repair_queue: Dict[str, Any]) -> List[str]:
    artifacts: List[str] = []
    next_action = readiness_repair_queue.get("next_action") if isinstance(readiness_repair_queue.get("next_action"), dict) else {}
    for key in ("action_id", "gate", "recommended_contract", "recommended_tool"):
        value = str(next_action.get(key, "")).strip()
        if value and value not in artifacts:
            artifacts.append(value)
    required = next_action.get("evidence_required_preview") if isinstance(next_action.get("evidence_required_preview"), list) else []
    for item in required:
        value = str(item).strip()
        if value and value not in artifacts:
            artifacts.append(value)
    gates = readiness_repair_queue.get("blocking_gate_preview") if isinstance(readiness_repair_queue.get("blocking_gate_preview"), list) else []
    for gate in gates:
        value = str(gate).strip()
        if value and value not in artifacts:
            artifacts.append(value)
    return artifacts[:8]


def paid_generation_evidence_artifacts(
    provider_spend: Dict[str, Any],
    readiness_policy: Dict[str, Any],
) -> List[str]:
    artifacts: List[str] = []
    if not isinstance(provider_spend, dict):
        provider_spend = {}
    contract = provider_spend.get("paid_generation_evidence_contract") if isinstance(provider_spend.get("paid_generation_evidence_contract"), dict) else {}

    receipt_path = str(contract.get("review_receipt_path", "")).strip()
    if receipt_path:
        receipt_command = str(contract.get("review_receipt_required_command", "python scripts\\write_paid_generation_evidence_review.py"))
        artifacts.append(f"receipt:{receipt_path}")
        artifacts.append(f"receipt_state:{contract.get('review_receipt_state', 'missing')}")
        artifacts.append(f"receipt_command:{receipt_command}")

    for section in ("paid_generation", "paid_animation_generation"):
        row = readiness_policy.get(section) if isinstance(readiness_policy.get(section), dict) else {}
        for gate in row.get("missing_gates", []) if isinstance(row.get("missing_gates"), list) else []:
            gate_name = str(gate).strip()
            if gate_name and gate_name not in artifacts:
                artifacts.append(gate_name)

    value = str(contract.get("mesh_wallet_tool", "")).strip()
    if value:
        artifacts.append(f"mesh_wallet_tool:{value}")
    for item in contract.get("operator_command_handoff", []) if isinstance(contract.get("operator_command_handoff"), list) else []:
        if not isinstance(item, dict):
            continue
        action_id = str(item.get("id", "")).strip()
        if action_id:
            artifacts.append(f"operator_command_handoff:{action_id}")
    for tool in contract.get("animation_allowance_tools", []) if isinstance(contract.get("animation_allowance_tools"), list) else []:
        tool_name = str(tool).strip()
        if tool_name:
            artifacts.append(f"animation_allowance_tool:{tool_name}")
    for step in contract.get("wallet_evidence_review_steps", []) if isinstance(contract.get("wallet_evidence_review_steps"), list) else []:
        step_text = str(step).strip()
        if step_text:
            artifacts.append(f"wallet_evidence_step:{step_text}")
    for field in ("ledger_tool", "spend_approval_field"):
        value = str(contract.get(field, "")).strip()
        if value:
            artifacts.append(f"{field}:{value}")
    for field in (
        "wallet_evidence_receipt_command_template",
        "mesh_wallet_evidence_receipt_command_template",
        "animation_allowance_receipt_command_template",
        "spend_confirmation_receipt_command_template",
    ):
        value = str(contract.get(field, "")).strip()
        if value:
            artifacts.append(f"{field}:{value}")
    for evidence in contract.get("evidence_required_preview", []) if isinstance(contract.get("evidence_required_preview"), list) else []:
        evidence_name = str(evidence).strip()
        if evidence_name and evidence_name not in artifacts:
            artifacts.append(evidence_name)

    if contract:
        artifacts.extend([
            "no_provider_call",
            "no_credit_reservation",
            "ledger_evidence_row_before_paid_task_submission",
        ])

    unique: List[str] = []
    for artifact in artifacts:
        if artifact and artifact not in unique:
            unique.append(artifact)
    return unique[:24]


def platform_stability_evidence_artifacts(platform_preflight: Dict[str, Any]) -> List[str]:
    if not isinstance(platform_preflight, dict) or not platform_preflight:
        return []
    platform_receipt = (
        platform_preflight.get("platform_stability_review")
        if isinstance(platform_preflight.get("platform_stability_review"), dict)
        else {}
    )
    blueprint_contract = (
        platform_preflight.get("blueprint_mutation_evidence_contract")
        if isinstance(platform_preflight.get("blueprint_mutation_evidence_contract"), dict)
        else {}
    )
    paid_evidence_state = str(
        platform_receipt.get(
            "paid_generation_evidence_receipt_state",
            platform_preflight.get("paid_generation_evidence_receipt_state", "missing"),
        )
    )
    if paid_evidence_state in {"", "missing"}:
        paid_evidence_state = "missing_evidence"
    receipt_path = str(platform_preflight.get("platform_stability_review_receipt_path", "Saved\\PlatformStabilityReview\\last_review_receipt.json"))
    artifacts = [
        f"receipt:{receipt_path}",
        f"receipt_state:{platform_preflight.get('platform_stability_review_receipt_state', 'missing')}",
        f"ready_for_platform_stability:{bool(platform_preflight.get('ready_for_platform_stability', False))}",
        f"ready_for_wip_promotion:{bool(platform_preflight.get('ready_for_wip_promotion', False))}",
        f"tool_count:{platform_preflight.get('tool_count', 0)}/{platform_preflight.get('recorded_count', 0)}",
        f"test_lanes:{platform_preflight.get('test_lane_state', 'unknown')}",
        f"paid_provider_smoke_contract:{bool(platform_preflight.get('paid_provider_smoke_contract_ok', False))}",
        f"paid_evidence_receipt:{paid_evidence_state}",
    ]
    paid_handoff = platform_receipt.get("paid_generation_operator_command_handoff", platform_preflight.get("paid_generation_operator_command_handoff", []))
    for item in paid_handoff if isinstance(paid_handoff, list) else []:
        if isinstance(item, dict) and item.get("id"):
            artifacts.append(f"paid_operator_command_handoff:{item.get('id')}")
    blueprint_handoff = (
        platform_receipt.get("blueprint_mutation_operator_command_handoff")
        or platform_preflight.get("blueprint_mutation_operator_command_handoff")
        or blueprint_contract.get("operator_command_handoff", [])
    )
    for item in blueprint_handoff if isinstance(blueprint_handoff, list) else []:
        if isinstance(item, dict) and item.get("id"):
            artifacts.append(f"blueprint_operator_command_handoff:{item.get('id')}")
    artifacts.extend([
        f"blueprint_evidence_receipt:{platform_receipt.get('blueprint_mutation_evidence_receipt_state', platform_preflight.get('blueprint_mutation_evidence_receipt_state', blueprint_contract.get('state', 'missing')))}",
        f"paid_provider_smoke_manual_spend:{bool(platform_preflight.get('paid_provider_smoke_manual_spend_required', False))}",
        f"paid_mesh_wallet_recorded:{bool(platform_receipt.get('paid_generation_mesh_wallet_evidence_recorded', platform_preflight.get('paid_generation_mesh_wallet_evidence_recorded', False)))}",
        f"paid_animation_allowance_recorded:{bool(platform_receipt.get('paid_generation_animation_allowance_evidence_recorded', platform_preflight.get('paid_generation_animation_allowance_evidence_recorded', False)))}",
        f"paid_spend_confirmation_recorded:{bool(platform_receipt.get('paid_generation_spend_confirmation_recorded', platform_preflight.get('paid_generation_spend_confirmation_recorded', False)))}",
        f"blueprint_pre_read_recorded:{bool(platform_receipt.get('blueprint_mutation_pre_read_evidence_recorded', platform_preflight.get('blueprint_pre_read_evidence_recorded', blueprint_contract.get('pre_read_evidence_recorded', False))))}",
        f"blueprint_compile_plan_recorded:{bool(platform_receipt.get('blueprint_mutation_compile_plan_recorded', platform_preflight.get('blueprint_compile_plan_recorded', blueprint_contract.get('compile_plan_recorded', False))))}",
        f"blueprint_readback_plan_recorded:{bool(platform_receipt.get('blueprint_mutation_readback_plan_recorded', platform_preflight.get('blueprint_readback_plan_recorded', blueprint_contract.get('readback_plan_recorded', False))))}",
        f"no_mutation:{platform_preflight.get('no_mutation_test_status', 'missing')}",
        f"no_mutation_tracked:{platform_preflight.get('no_mutation_test_tracked_file_count', 'unknown')}",
        f"no_mutation_snapshot_match:{bool(platform_preflight.get('no_mutation_test_snapshot_digest_match', False))}",
        f"no_mutation_snapshot_scope:{platform_preflight.get('no_mutation_test_snapshot_scope', 'unknown')}",
        f"no_mutation_snapshot_hash:{platform_preflight.get('no_mutation_test_snapshot_hash_algorithm', 'unknown')}",
        f"high_value_wrappers:{platform_preflight.get('high_value_wrapper_state', 'unknown')}",
        f"build:{platform_preflight.get('build_wrapper_status', 'unknown')}/{platform_preflight.get('last_plugin_build_status', 'unknown')}",
    ])
    for gate in platform_preflight.get("platform_missing_gate_preview", []) if isinstance(platform_preflight.get("platform_missing_gate_preview"), list) else []:
        artifacts.append(f"platform_missing:{gate}")
    for gate in platform_preflight.get("wip_promotion_missing_gate_preview", []) if isinstance(platform_preflight.get("wip_promotion_missing_gate_preview"), list) else []:
        artifacts.append(f"wip_missing:{gate}")

    unique: List[str] = []
    for artifact in artifacts:
        value = str(artifact).strip()
        if value and value not in unique:
            unique.append(value)
    return unique[:30]


def dirty_promotion_evidence_artifacts(platform_preflight: Dict[str, Any]) -> List[str]:
    if not isinstance(platform_preflight, dict) or not platform_preflight:
        return []
    contract = platform_preflight.get("dirty_promotion_contract") if isinstance(platform_preflight.get("dirty_promotion_contract"), dict) else {}
    if not contract:
        return []
    receipt_path = str(contract.get("review_receipt_path", "Saved\\DirtyPromotionReview\\last_review_receipt.json"))
    artifacts = [
        f"receipt:{receipt_path}",
        f"receipt_state:{contract.get('review_receipt_state', 'missing')}",
        f"dirty_risk:{contract.get('dirty_risk', platform_preflight.get('dirty_risk', 'unknown'))}",
        f"tracked:{contract.get('tracked_change_count', platform_preflight.get('tracked_change_count', 0))}",
        f"untracked:{contract.get('untracked_count', platform_preflight.get('untracked_count', 0))}",
        f"groups:{contract.get('dirty_group_count', platform_preflight.get('dirty_group_count', 0))}",
        f"batches:{contract.get('review_batch_count', 0)}",
        f"ready_for_promotion:{bool(contract.get('ready_for_promotion', False))}",
        f"recommended_next:{contract.get('recommended_next', 'review_dirty_groups_for_promotion')}",
    ]
    for gate in platform_preflight.get("wip_promotion_missing_gate_preview", []) if isinstance(platform_preflight.get("wip_promotion_missing_gate_preview"), list) else []:
        if str(gate) == "dirty_state_grouped_for_promotion":
            artifacts.append("wip_missing:dirty_state_grouped_for_promotion")
    for evidence in contract.get("required_evidence_preview", []) if isinstance(contract.get("required_evidence_preview"), list) else []:
        artifacts.append(str(evidence))

    unique: List[str] = []
    for artifact in artifacts:
        value = str(artifact).strip()
        if value and value not in unique:
            unique.append(value)
    return unique[:10]


def provider_config_evidence_artifacts(platform_preflight: Dict[str, Any]) -> List[str]:
    if not isinstance(platform_preflight, dict) or not platform_preflight:
        return []
    receipt_path = str(platform_preflight.get("provider_config_review_receipt_path", "Saved\\ProviderConfigReview\\last_review_receipt.json"))
    artifacts = [
        f"receipt:{receipt_path}",
        f"receipt_state:{platform_preflight.get('provider_config_review_receipt_state', 'missing')}",
        f"provider:{platform_preflight.get('provider', 'tripo')}",
        f"animation_provider:{platform_preflight.get('animation_provider', 'uthana')}",
        f"tripo_configured:{bool(platform_preflight.get('provider_api_key_configured', False))}",
        f"uthana_configured:{bool(platform_preflight.get('animation_provider_api_key_configured', False))}",
        f"tripo_source:{platform_preflight.get('provider_api_key_source', 'missing')}",
        f"uthana_source:{platform_preflight.get('animation_provider_api_key_source', 'missing')}",
        "no_raw_key",
        "no_provider_call",
    ]
    for gate in platform_preflight.get("paid_missing_gate_preview", []) if isinstance(platform_preflight.get("paid_missing_gate_preview"), list) else []:
        if str(gate) == "provider_api_key_configured":
            artifacts.append("paid_missing:provider_api_key_configured")
    for gate in platform_preflight.get("paid_animation_missing_gate_preview", []) if isinstance(platform_preflight.get("paid_animation_missing_gate_preview"), list) else []:
        if str(gate) == "animation_provider_api_key_configured":
            artifacts.append("paid_animation_missing:animation_provider_api_key_configured")

    unique: List[str] = []
    for artifact in artifacts:
        value = str(artifact).strip()
        if value and value not in unique:
            unique.append(value)
    return unique[:12]


def bridge_ping_evidence_artifacts(platform_preflight: Dict[str, Any]) -> List[str]:
    if not isinstance(platform_preflight, dict) or not platform_preflight:
        return []
    receipt_path = str(platform_preflight.get("bridge_ping_receipt_path", "Saved\\BridgePing\\last_ping_receipt.json"))
    required_command = str(platform_preflight.get("bridge_ping_required_command", "python scripts\\bridge_ping.py"))
    artifacts = [
        f"receipt:{receipt_path}",
        f"receipt_state:{platform_preflight.get('bridge_ping_receipt_state', 'missing')}",
        f"successful_bridge_ping:{bool(platform_preflight.get('successful_bridge_ping', False))}",
        f"bridge_ready:{bool(platform_preflight.get('bridge_ready', False))}",
        f"bridge_tcp_ready:{bool(platform_preflight.get('bridge_tcp_ready', False))}",
        f"bridge_endpoint:{platform_preflight.get('bridge_host', '127.0.0.1')}:{platform_preflight.get('bridge_port', 0)}",
        f"required_command:{required_command}",
        "no_editor_mutation",
        "no_provider_call",
        "no_git_mutation",
    ]
    for gate in platform_preflight.get("blocking_gate_preview", []) if isinstance(platform_preflight.get("blocking_gate_preview"), list) else []:
        if str(gate) == "unreal_bridge_reachable":
            artifacts.append("blocking_gate:unreal_bridge_reachable")
    for gate in platform_preflight.get("blueprint_missing_gate_preview", []) if isinstance(platform_preflight.get("blueprint_missing_gate_preview"), list) else []:
        if str(gate) == "unreal_bridge_reachable":
            artifacts.append("blueprint_missing:unreal_bridge_reachable")

    unique: List[str] = []
    for artifact in artifacts:
        value = str(artifact).strip()
        if value and value not in unique:
            unique.append(value)
    return unique[:12]


def chat_cockpit_start_evidence_artifacts(platform_preflight: Dict[str, Any]) -> List[str]:
    if not isinstance(platform_preflight, dict) or not platform_preflight:
        return []
    repair = platform_preflight.get("chat_cockpit_repair_contract") if isinstance(platform_preflight.get("chat_cockpit_repair_contract"), dict) else {}
    receipt_path = str(platform_preflight.get("chat_startup_receipt_path") or repair.get("startup_receipt_path") or "Saved\\ChatCockpit\\last_start_receipt.json")
    startup_command = str(platform_preflight.get("chat_startup_command") or repair.get("startup_command") or "")
    proof_command = str(repair.get("proof_command", ""))
    artifacts = [
        f"receipt:{receipt_path}",
        f"chat_ready:{bool(platform_preflight.get('chat_ready', False))}",
        f"chat_tcp_ready:{bool(platform_preflight.get('chat_tcp_ready', False))}",
        f"chat_health:{platform_preflight.get('chat_base_url', '')}{platform_preflight.get('chat_health_endpoint', '')}",
        f"repair_state:{repair.get('state', '')}",
        "chat_history_endpoint_ready",
        "chat_cockpit_start_receipt_success",
    ]
    if startup_command:
        artifacts.append(f"startup_command:{startup_command}")
    if proof_command:
        artifacts.append(f"proof_command:{proof_command}")
    for evidence in repair.get("required_evidence_preview", []) if isinstance(repair.get("required_evidence_preview"), list) else []:
        artifacts.append(str(evidence))

    unique: List[str] = []
    for artifact in artifacts:
        value = str(artifact).strip()
        if value and value not in unique:
            unique.append(value)
    return unique[:12]


def local_readiness_repair_queue(blocking_gates: List[str]) -> Dict[str, Any]:
    gate_order = {
        "chat_server_reachable": 10,
        "chat_cockpit_reachable": 11,
        "dirty_state_grouped_for_promotion": 20,
        "unreal_bridge_reachable": 30,
        "provider_api_key_configured": 40,
        "animation_provider_api_key_configured": 41,
        "wallet_evidence_recorded": 50,
        "spend_confirmation_recorded": 60,
    }
    unique_gates = sorted({str(gate) for gate in blocking_gates if str(gate).strip()}, key=lambda gate: (gate_order.get(gate, 99), gate))
    action_map = {
        "chat_server_reachable": ("repair_chat_server_reachability", "chat_cockpit", "chat_cockpit_repair_contract", "scripts/audit_ide_companion_readiness.py", ["chat_history_http_200", "chat_history_messages_list"]),
        "chat_cockpit_reachable": ("refresh_chat_cockpit_after_server_ready", "wip_promotion", "chat_cockpit_repair_contract", "chat_get_cockpit_overview", ["chat_history_endpoint_ready", "unreal_chat_panel_refresh_after_server_ready"]),
        "provider_api_key_configured": ("configure_tripo_provider_secret", "paid_generation", "provider_config.repair_contract", "gen_save_provider_config", ["masked_provider_auth_source", "api_key_configured_true", "raw_key_absent_from_outputs"]),
        "animation_provider_api_key_configured": ("configure_uthana_provider_secret", "paid_animation_generation", "provider_config.repair_contract", "gen_save_provider_config", ["masked_animation_provider_auth_source", "uthana_api_key_configured_true", "raw_key_absent_from_outputs"]),
        "wallet_evidence_recorded": ("record_wallet_or_allowance_evidence", "paid_generation", "paid_generation_evidence", "gen_tripo_get_credit_balance", ["wallet_or_allowance_evidence", "provider_network_approval", "no_spend_intent_confirmation"]),
        "spend_confirmation_recorded": ("record_explicit_spend_or_usage_confirmation", "paid_generation", "paid_generation_evidence", "skill_record_ide_companion_evidence", ["explicit_human_spend_or_usage_approval", "estimated_credits_or_motion_seconds_reviewed"]),
        "dirty_state_grouped_for_promotion": ("review_dirty_groups_for_promotion", "wip_promotion", "dirty_promotion_contract", "scripts/audit_ide_companion_readiness.py", ["owner_or_source_for_each_dirty_group", "human_review_before_stage_commit_or_merge"]),
        "unreal_bridge_reachable": ("verify_unreal_bridge_reachability", "editor_mutation", "readiness_policy.editor_mutation", "scripts/bridge_ping.py", ["successful_bridge_ping", "bridge_ready_true", "editor_target_project_confirmed"]),
    }
    actions = []
    for index, gate in enumerate(unique_gates, start=1):
        action_id, policy_area, contract, tool, evidence = action_map.get(
            gate,
            (f"resolve_{gate}", "readiness", "readiness_policy", "scripts/audit_ide_companion_readiness.py", [gate]),
        )
        actions.append({
            "order": index,
            "action_id": action_id,
            "gate": gate,
            "policy_area": policy_area,
            "recommended_contract": contract,
            "recommended_tool": tool,
            "evidence_required_preview": evidence,
            "requires_manual_operator": True,
            "requires_bridge": gate == "unreal_bridge_reachable",
            "requires_network": gate == "wallet_evidence_recorded",
            "requires_spend": False,
            "requires_unreal_editor": gate in {"chat_cockpit_reachable", "unreal_bridge_reachable"},
            "no_auto_execute": True,
            "no_secret_echo": True,
            "no_git_mutation": True,
            "no_editor_mutation": True,
        })
        if gate == "wallet_evidence_recorded":
            actions[-1].update({
                "secondary_tools": ["gen_uthana_get_account", "gen_uthana_check_download_allowed"],
                "review_steps": [
                    "Confirm provider-network approval and no-spend intent in the cockpit.",
                    "Run gen_tripo_get_credit_balance(include_raw=False) for masked Tripo wallet balance evidence.",
                    "Run gen_uthana_get_account(include_user=False) for masked Uthana org allowance evidence.",
                    "Write the ignored local paid-generation evidence receipt with a short non-secret summary.",
                ],
                "receipt_command_template": (
                    'python scripts\\write_paid_generation_evidence_review.py --mesh-wallet-evidence-recorded '
                    '--animation-allowance-evidence-recorded --mesh-wallet-evidence-summary "<masked Tripo wallet evidence>" '
                    '--animation-allowance-summary "<masked Uthana allowance evidence>"'
                ),
                "provider_call_required": True,
                "no_credit_reservation": True,
                "no_task_submission": True,
                "no_download": True,
                "no_import": True,
            })
        if gate == "spend_confirmation_recorded":
            actions[-1].update({
                "receipt_command_template": (
                    'python scripts\\write_paid_generation_evidence_review.py --mesh-wallet-evidence-recorded '
                    '--animation-allowance-evidence-recorded --spend-confirmation-recorded '
                    '--explicit-usage-approval-recorded --estimated-spend-reviewed --estimated-motion-seconds-reviewed '
                    '--mesh-wallet-evidence-summary "<masked Tripo wallet evidence>" '
                    '--animation-allowance-summary "<masked Uthana allowance evidence>" '
                    '--spend-confirmation-summary "<explicit human Tripo spend approval>" '
                    '--usage-approval-summary "<explicit human Uthana usage approval>"'
                ),
                "future_spend_required": True,
                "no_provider_call": True,
                "no_credit_reservation": True,
                "no_task_submission": True,
            })
    next_action = actions[0] if actions else {}
    return {
        "schema": "unreal_mcp_readiness_repair_queue.v1",
        "state": "ready" if not actions else "blocked",
        "action_count": len(actions),
        "blocking_gate_count": len(unique_gates),
        "blocking_gate_preview": unique_gates[:8],
        "next_action": next_action,
        "action_preview": actions[:8],
        "recommended_next": str(next_action.get("action_id", "none")) if next_action else "none",
        "priority_policy": "chat_health_then_wip_promotion_safety_then_bridge_proof_then_paid_provider_gates",
        "no_auto_execute": True,
        "no_secret_echo": True,
        "no_git_mutation": True,
        "no_editor_mutation": True,
    }


def build_evidence_recording_checklist(
    *,
    session_name: str,
    ledger: Dict[str, Any],
    queues: List[Dict[str, Any]],
    asset_lifecycles: List[Dict[str, Any]],
    generated_asset_quality_gate: Dict[str, Any],
    work_order_template: Dict[str, Any],
    runtime_verification: Dict[str, Any],
    repair_loop: Dict[str, Any],
    blocker_resolutions: Dict[str, Any],
    readiness_policy: Dict[str, Any],
    readiness_repair_queue: Dict[str, Any] | None = None,
    provider_spend: Dict[str, Any] | None = None,
    platform_preflight: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    target_phase = str(ledger.get("work_order_phase") or ledger.get("next_phase") or ledger.get("latest_phase") or "session_preflight")
    existing_types = {
        str(event.get("evidence_type", "")).lower()
        for event in ledger.get("preview_events", [])
        if isinstance(event, dict)
    } if isinstance(ledger.get("preview_events"), list) else set()
    items: List[Dict[str, Any]] = []

    if blocker_resolutions.get("blocking_gate_count", 0):
        blockers = [str(item.get("blocker", "")) for item in blocker_resolutions.get("resolutions", []) if item.get("blocker")]
        items.append(evidence_recording_item(
            item_id="record_blocker_resolution",
            source="blocker_resolutions",
            phase_name=target_phase,
            evidence_type="blocker_resolution",
            label="Record chosen blocker resolution path",
            required_artifacts=blockers or ["blocking gate list"],
            state="recorded" if "blocker_resolution" in existing_types else "pending",
            suggested_summary="Record the selected blocker-resolution strategy before continuing.",
        ))

    repair_queue = readiness_repair_queue if isinstance(readiness_repair_queue, dict) else {}
    repair_artifacts = readiness_repair_queue_evidence_artifacts(repair_queue)
    if repair_artifacts:
        next_action = repair_queue.get("next_action") if isinstance(repair_queue.get("next_action"), dict) else {}
        items.append(evidence_recording_item(
            item_id="record_readiness_repair_queue",
            source="readiness_repair_queue",
            phase_name=target_phase,
            evidence_type="readiness_repair_queue",
            label="Record ordered readiness repair queue",
            required_artifacts=repair_artifacts,
            state="recorded" if "readiness_repair_queue" in existing_types else "pending",
            suggested_summary="Record the ordered blocker repair queue and next safe manual action before continuing.",
            metadata={
                "schema": repair_queue.get("schema", "unreal_mcp_readiness_repair_queue.v1"),
                "state": repair_queue.get("state", ""),
                "action_count": int(repair_queue.get("action_count", 0) or 0),
                "blocking_gate_count": int(repair_queue.get("blocking_gate_count", 0) or 0),
                "blocking_gate_preview": bounded_string_preview(repair_queue.get("blocking_gate_preview", []), 8),
                "recommended_next": repair_queue.get("recommended_next", ""),
                "next_action_id": next_action.get("action_id", ""),
                "next_gate": next_action.get("gate", ""),
                "next_policy_area": next_action.get("policy_area", ""),
                "next_recommended_contract": next_action.get("recommended_contract", ""),
                "next_recommended_tool": next_action.get("recommended_tool", ""),
                "next_evidence_required_preview": bounded_string_preview(next_action.get("evidence_required_preview", []), 8),
                "next_requires_manual_operator": bool(next_action.get("requires_manual_operator", True)),
                "next_requires_bridge": bool(next_action.get("requires_bridge", False)),
                "next_requires_network": bool(next_action.get("requires_network", False)),
                "next_requires_spend": bool(next_action.get("requires_spend", False)),
                "next_requires_unreal_editor": bool(next_action.get("requires_unreal_editor", False)),
                "next_receipt_command_template": next_action.get("receipt_command_template", ""),
                "next_operator_command_handoff": (
                    (
                        list(next_action.get("operator_command_handoff", []))[:2]
                        if isinstance(next_action.get("operator_command_handoff"), list)
                        else []
                    )
                    or (
                        list(next_action.get("target_review_operator_command_handoff", []))[:2]
                        if isinstance(next_action.get("target_review_operator_command_handoff"), list)
                        else []
                    )
                ),
                "no_auto_execute": bool(repair_queue.get("no_auto_execute", True)),
                "no_secret_echo": bool(repair_queue.get("no_secret_echo", True)),
                "no_git_mutation": bool(repair_queue.get("no_git_mutation", True)),
                "no_editor_mutation": bool(repair_queue.get("no_editor_mutation", True)),
            },
        ))

    platform_context = platform_preflight if isinstance(platform_preflight, dict) else {}
    platform_artifacts = platform_stability_evidence_artifacts(platform_context)
    if platform_artifacts:
        receipt_state = str(platform_context.get("platform_stability_review_receipt_state", "missing"))
        receipt_exists = bool(platform_context.get("platform_stability_review_receipt_exists", False))
        platform_receipt = (
            platform_context.get("platform_stability_review")
            if isinstance(platform_context.get("platform_stability_review"), dict)
            else {}
        )
        dirty_contract = (
            platform_context.get("dirty_promotion_contract")
            if isinstance(platform_context.get("dirty_promotion_contract"), dict)
            else {}
        )
        dirty_context = {
            "dirty_promotion_review_receipt_state": dirty_contract.get("review_receipt_state", "missing"),
            "dirty_promotion_review_receipt_current": dirty_contract.get("review_receipt_current", False),
            "dirty_promotion_review_receipt_stale": dirty_contract.get("review_receipt_stale", False),
            "dirty_promotion_review_receipt_signature_match": dirty_contract.get("review_receipt_dirty_signature_match", False),
            "dirty_signature_algorithm": dirty_contract.get("dirty_signature_algorithm", ""),
            "dirty_signature_entry_count": dirty_contract.get("dirty_signature_entry_count", 0),
            "dirty_promotion_review_batch_count": dirty_contract.get("review_batch_count", 0),
            "dirty_promotion_evidence_unresolved_count": dirty_contract.get("evidence_unresolved_count", 0),
            "dirty_target_review_group": dirty_contract.get("target_review_group", ""),
            "dirty_target_review_order": dirty_contract.get("target_review_order", 0),
            "dirty_target_review_scope": dirty_contract.get("target_review_scope", ""),
            "dirty_target_review_tracked_count": dirty_contract.get("target_review_tracked_count", 0),
            "dirty_target_review_untracked_count": dirty_contract.get("target_review_untracked_count", 0),
            "dirty_target_review_status": dirty_contract.get("target_review_status", "missing_evidence"),
            "dirty_target_review_evidence_complete": dirty_contract.get("target_review_evidence_complete", False),
            "dirty_target_review_recorded_evidence_count": dirty_contract.get("target_review_recorded_evidence_count", 0),
            "dirty_target_review_recorded_evidence_preview": dirty_contract.get("target_review_recorded_evidence_preview", []),
            "dirty_target_review_human_approval_recorded": dirty_contract.get("target_review_human_approval_recorded", False),
            "dirty_target_review_missing_evidence_count": dirty_contract.get("target_review_missing_evidence_count", 0),
            "dirty_target_review_missing_evidence_preview": dirty_contract.get("target_review_missing_evidence_preview", []),
            "dirty_target_review_required_evidence_preview": dirty_contract.get("target_review_required_evidence_preview", []),
            "dirty_target_review_decision_prompt_preview": dirty_contract.get("target_review_decision_prompt_preview", []),
            "dirty_target_review_receipt_command_template": dirty_contract.get("target_review_receipt_command_template", ""),
            "dirty_target_review_approval_receipt_command_template": dirty_contract.get("target_review_approval_receipt_command_template", ""),
            "dirty_target_review_receipt_command_policy": dirty_contract.get("target_review_receipt_command_policy", ""),
            "dirty_target_review_operator_command_handoff": dirty_contract.get("target_review_operator_command_handoff", []),
            "dirty_target_review_pending_human_approval_only": dirty_contract.get("target_review_pending_human_approval_only", False),
            "dirty_target_review_human_approval_gate": dirty_contract.get("target_review_human_approval_gate", "human_approval_before_stage_commit_merge"),
            "dirty_target_review_human_approval_command_handoff": dirty_contract.get("target_review_human_approval_command_handoff", []),
            "dirty_target_review_focused_test_command_handoff": dirty_contract.get("target_review_focused_test_command_handoff", []),
            "dirty_target_review_focused_test_command_count": dirty_contract.get("target_review_focused_test_command_count", 0),
            "dirty_target_review_focused_test_command_preview": dirty_contract.get("target_review_focused_test_command_preview", []),
            "dirty_target_review_sample_preview": dirty_contract.get("target_review_sample_preview", []),
            "dirty_target_review_promotion_allowed_after_receipt": dirty_contract.get("target_review_promotion_allowed_after_receipt", False),
            "dirty_target_review_merge_policy": dirty_contract.get("target_review_merge_policy", ""),
            "dirty_target_review_previous_evidence_merged": dirty_contract.get("target_review_previous_evidence_merged", False),
            "dirty_target_review_reset_evidence": dirty_contract.get("target_review_reset_evidence", False),
        }
        platform_receipt = {
            **platform_context,
            **{
                key: value
                for key, value in platform_receipt.items()
                if value not in ("", None, [], {})
            },
            **dirty_context,
        }
        items.append(evidence_recording_item(
            item_id="record_platform_stability_review",
            source="platform_preflight",
            phase_name="session_preflight",
            evidence_type="platform_stability_review",
            label="Record platform stability review receipt",
            required_artifacts=platform_artifacts,
            state=(
                "recorded"
                if "platform_stability_review" in existing_types
                else ("blocked" if receipt_state == "blocked" else "pending")
            ),
            suggested_summary="Record the local platform-stability review receipt before claiming WIP is promotion-ready.",
            requires_bridge=False,
            metadata={
                "schema": "unreal_mcp_platform_stability_review_receipt.v1",
                "receipt_state": receipt_state,
                "receipt_exists": receipt_exists,
                "receipt_path": platform_context.get("platform_stability_review_receipt_path", "Saved\\PlatformStabilityReview\\last_review_receipt.json"),
                "required_command": platform_context.get("platform_stability_review_receipt_required_command", "python scripts\\write_platform_stability_review.py"),
                "ready_for_platform_stability": bool(platform_context.get("ready_for_platform_stability", False)),
                "ready_for_wip_promotion": bool(platform_context.get("ready_for_wip_promotion", False)),
                "platform_missing_gate_count": int(platform_context.get("platform_missing_gate_count", 0) or 0),
                "wip_promotion_missing_gate_count": int(platform_context.get("wip_promotion_missing_gate_count", 0) or 0),
                "blocking_gate_count": int(platform_context.get("blocking_gate_count", 0) or 0),
                "blocking_gate_preview": bounded_string_preview(platform_context.get("blocking_gate_preview", []), 12),
                "readiness_repair_action_count": int(platform_context.get("readiness_repair_action_count", 0) or 0),
                "readiness_repair_recommended_next": platform_context.get("readiness_repair_recommended_next", ""),
                "readiness_repair_next_gate": platform_context.get("readiness_repair_next_gate", ""),
                "readiness_repair_next_policy_area": platform_context.get("readiness_repair_next_policy_area", ""),
                "readiness_repair_next_tool": platform_context.get("readiness_repair_next_tool", ""),
                "readiness_repair_next_requires_bridge": bool(platform_context.get("readiness_repair_next_requires_bridge", False)),
                "readiness_repair_next_requires_network": bool(platform_context.get("readiness_repair_next_requires_network", False)),
                "readiness_repair_next_requires_spend": bool(platform_context.get("readiness_repair_next_requires_spend", False)),
                "readiness_repair_action_preview": [
                    item for item in platform_context.get("readiness_repair_action_preview", [])[:8] if isinstance(item, dict)
                ] if isinstance(platform_context.get("readiness_repair_action_preview"), list) else [],
                "dirty_promotion_review_receipt_state": platform_receipt.get("dirty_promotion_review_receipt_state", "missing"),
                "dirty_promotion_review_receipt_current": bool(platform_receipt.get("dirty_promotion_review_receipt_current", False)),
                "dirty_promotion_review_receipt_stale": bool(platform_receipt.get("dirty_promotion_review_receipt_stale", False)),
                "dirty_promotion_review_receipt_signature_match": bool(platform_receipt.get("dirty_promotion_review_receipt_signature_match", False)),
                "dirty_signature_algorithm": platform_receipt.get("dirty_signature_algorithm", ""),
                "dirty_signature_entry_count": int(platform_receipt.get("dirty_signature_entry_count", 0) or 0),
                "dirty_promotion_review_batch_count": int(platform_receipt.get("dirty_promotion_review_batch_count", 0) or 0),
                "dirty_promotion_evidence_unresolved_count": int(platform_receipt.get("dirty_promotion_evidence_unresolved_count", 0) or 0),
                "dirty_target_review_group": platform_receipt.get("dirty_target_review_group", ""),
                "dirty_target_review_order": int(platform_receipt.get("dirty_target_review_order", 0) or 0),
                "dirty_target_review_scope": platform_receipt.get("dirty_target_review_scope", ""),
                "dirty_target_review_tracked_count": int(platform_receipt.get("dirty_target_review_tracked_count", 0) or 0),
                "dirty_target_review_untracked_count": int(platform_receipt.get("dirty_target_review_untracked_count", 0) or 0),
                "dirty_target_review_status": str(platform_receipt.get("dirty_target_review_status") or "missing_evidence"),
                "dirty_target_review_evidence_complete": bool(platform_receipt.get("dirty_target_review_evidence_complete", False)),
                "dirty_target_review_recorded_evidence_count": int(platform_receipt.get("dirty_target_review_recorded_evidence_count", 0) or 0),
                "dirty_target_review_recorded_evidence_preview": bounded_string_preview(platform_receipt.get("dirty_target_review_recorded_evidence_preview", []), 8),
                "dirty_target_review_human_approval_recorded": bool(platform_receipt.get("dirty_target_review_human_approval_recorded", False)),
                "dirty_target_review_missing_evidence_count": int(platform_receipt.get("dirty_target_review_missing_evidence_count", 0) or 0),
                "dirty_target_review_missing_evidence_preview": bounded_string_preview(platform_receipt.get("dirty_target_review_missing_evidence_preview", []), 8),
                "dirty_target_review_required_evidence_preview": bounded_string_preview(platform_receipt.get("dirty_target_review_required_evidence_preview", []), 8),
                "dirty_target_review_decision_prompt_preview": bounded_string_preview(platform_receipt.get("dirty_target_review_decision_prompt_preview", []), 8),
                "dirty_target_review_receipt_command_template": str(platform_receipt.get("dirty_target_review_receipt_command_template", "")),
                "dirty_target_review_approval_receipt_command_template": str(
                    platform_receipt.get("dirty_target_review_approval_receipt_command_template", "")
                ),
                "dirty_target_review_receipt_command_policy": str(platform_receipt.get("dirty_target_review_receipt_command_policy", "")),
                "dirty_target_review_operator_command_handoff": (
                    list(platform_receipt.get("dirty_target_review_operator_command_handoff", []))[:2]
                    if isinstance(platform_receipt.get("dirty_target_review_operator_command_handoff"), list)
                    else []
                ),
                "dirty_target_review_pending_human_approval_only": bool(platform_receipt.get("dirty_target_review_pending_human_approval_only", False)),
                "dirty_target_review_human_approval_gate": str(platform_receipt.get("dirty_target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
                "dirty_target_review_human_approval_command_handoff": (
                    list(platform_receipt.get("dirty_target_review_human_approval_command_handoff", []))[:1]
                    if isinstance(platform_receipt.get("dirty_target_review_human_approval_command_handoff"), list)
                    else []
                ),
                "dirty_target_review_focused_test_command_handoff": (
                    list(platform_receipt.get("dirty_target_review_focused_test_command_handoff", []))[:5]
                    if isinstance(platform_receipt.get("dirty_target_review_focused_test_command_handoff"), list)
                    else []
                ),
                "dirty_target_review_focused_test_command_count": int(platform_receipt.get("dirty_target_review_focused_test_command_count", 0) or 0),
                "dirty_target_review_focused_test_command_preview": bounded_string_preview(platform_receipt.get("dirty_target_review_focused_test_command_preview", []), 5),
                "dirty_target_review_sample_preview": bounded_string_preview(platform_receipt.get("dirty_target_review_sample_preview", []), 5),
                "dirty_target_review_promotion_allowed_after_receipt": bool(platform_receipt.get("dirty_target_review_promotion_allowed_after_receipt", False)),
                "dirty_target_review_merge_policy": str(platform_receipt.get("dirty_target_review_merge_policy", "")),
                "dirty_target_review_previous_evidence_merged": bool(platform_receipt.get("dirty_target_review_previous_evidence_merged", False)),
                "dirty_target_review_reset_evidence": bool(platform_receipt.get("dirty_target_review_reset_evidence", False)),
                "tool_registry_reproducible": bool(platform_context.get("tool_registry_reproducible", False)),
                "tool_count": int(platform_context.get("tool_count", 0) or 0),
                "recorded_tool_count": int(platform_context.get("recorded_count", 0) or 0),
                "partial_tool_count": int(platform_context.get("partial_tool_count", 0) or 0),
                "test_lane_state": platform_context.get("test_lane_state", ""),
                "paid_provider_smoke_contract_ok": bool(platform_context.get("paid_provider_smoke_contract_ok", False)),
                "paid_provider_smoke_manual_command": platform_context.get("paid_provider_smoke_manual_command", ""),
                "paid_provider_smoke_required_env_vars": bounded_string_preview(platform_context.get("paid_provider_smoke_required_env_vars", []), 5),
                "paid_provider_smoke_no_spend_tools": bounded_string_preview(platform_context.get("paid_provider_smoke_no_spend_tools", []), 5),
                "paid_provider_smoke_manual_spend_required": bool(platform_context.get("paid_provider_smoke_manual_spend_required", False)),
                "paid_provider_smoke_no_task_submission": bool(platform_context.get("paid_provider_smoke_no_task_submission", True)),
                "paid_provider_smoke_no_download": bool(platform_context.get("paid_provider_smoke_no_download", True)),
                "paid_provider_smoke_no_import": bool(platform_context.get("paid_provider_smoke_no_import", True)),
                "paid_generation_evidence_receipt_state": platform_receipt.get("paid_generation_evidence_receipt_state", platform_context.get("paid_generation_evidence_receipt_state", "missing")),
                "paid_generation_evidence_receipt_path": platform_receipt.get("paid_generation_evidence_receipt_path", platform_context.get("paid_generation_evidence_receipt_path", "Saved\\PaidGenerationEvidence\\last_review_receipt.json")),
                "paid_generation_evidence_required_command": platform_receipt.get("paid_generation_evidence_required_command", platform_context.get("paid_generation_evidence_required_command", "python scripts\\write_paid_generation_evidence_review.py")),
                "paid_generation_wallet_evidence_recorded": bool(platform_receipt.get("paid_generation_wallet_evidence_recorded", platform_context.get("paid_generation_wallet_evidence_recorded", False))),
                "paid_generation_mesh_wallet_evidence_recorded": bool(platform_receipt.get("paid_generation_mesh_wallet_evidence_recorded", platform_context.get("paid_generation_mesh_wallet_evidence_recorded", False))),
                "paid_generation_animation_allowance_evidence_recorded": bool(platform_receipt.get("paid_generation_animation_allowance_evidence_recorded", platform_context.get("paid_generation_animation_allowance_evidence_recorded", False))),
                "paid_generation_spend_confirmation_recorded": bool(platform_receipt.get("paid_generation_spend_confirmation_recorded", platform_context.get("paid_generation_spend_confirmation_recorded", False))),
                "paid_generation_explicit_spend_approval_recorded": bool(platform_receipt.get("paid_generation_explicit_spend_approval_recorded", platform_context.get("paid_generation_explicit_spend_approval_recorded", False))),
                "paid_generation_explicit_usage_approval_recorded": bool(platform_receipt.get("paid_generation_explicit_usage_approval_recorded", platform_context.get("paid_generation_explicit_usage_approval_recorded", False))),
                "paid_generation_estimated_spend_reviewed": bool(platform_receipt.get("paid_generation_estimated_spend_reviewed", platform_context.get("paid_generation_estimated_spend_reviewed", False))),
                "paid_generation_estimated_motion_seconds_reviewed": bool(platform_receipt.get("paid_generation_estimated_motion_seconds_reviewed", platform_context.get("paid_generation_estimated_motion_seconds_reviewed", False))),
                "paid_generation_mesh_provider": platform_receipt.get("paid_generation_mesh_provider", platform_context.get("paid_generation_mesh_provider", "tripo")),
                "paid_generation_animation_provider": platform_receipt.get("paid_generation_animation_provider", platform_context.get("paid_generation_animation_provider", "uthana")),
                "paid_generation_operator_command_handoff": (
                    list(platform_receipt.get("paid_generation_operator_command_handoff", platform_context.get("paid_generation_operator_command_handoff", [])))[:3]
                    if isinstance(platform_receipt.get("paid_generation_operator_command_handoff", platform_context.get("paid_generation_operator_command_handoff", [])), list)
                    else []
                ),
                "blueprint_mutation_evidence_receipt_state": platform_receipt.get(
                    "blueprint_mutation_evidence_receipt_state",
                    platform_context.get("blueprint_mutation_evidence_receipt_state", "missing"),
                ),
                "blueprint_mutation_evidence_receipt_status": platform_receipt.get(
                    "blueprint_mutation_evidence_receipt_status",
                    platform_context.get("blueprint_mutation_evidence_receipt_state", "missing"),
                ),
                "blueprint_mutation_evidence_receipt_path": platform_receipt.get(
                    "blueprint_mutation_evidence_receipt_path",
                    platform_context.get("blueprint_mutation_evidence_receipt_path", "Saved\\BlueprintMutationEvidence\\last_review_receipt.json"),
                ),
                "blueprint_mutation_evidence_required_command": platform_receipt.get(
                    "blueprint_mutation_evidence_required_command",
                    platform_context.get("blueprint_mutation_evidence_receipt_required_command", "python scripts\\write_blueprint_mutation_evidence_review.py"),
                ),
                "blueprint_mutation_operator_command_handoff": (
                    list(platform_receipt.get("blueprint_mutation_operator_command_handoff") or platform_context.get("blueprint_mutation_operator_command_handoff", []))[:3]
                    if isinstance(platform_receipt.get("blueprint_mutation_operator_command_handoff") or platform_context.get("blueprint_mutation_operator_command_handoff", []), list)
                    else []
                ),
                "blueprint_mutation_pre_read_evidence_recorded": bool(platform_receipt.get(
                    "blueprint_mutation_pre_read_evidence_recorded",
                    platform_context.get("blueprint_pre_read_evidence_recorded", False),
                )),
                "blueprint_mutation_compile_plan_recorded": bool(platform_receipt.get(
                    "blueprint_mutation_compile_plan_recorded",
                    platform_context.get("blueprint_compile_plan_recorded", False),
                )),
                "blueprint_mutation_readback_plan_recorded": bool(platform_receipt.get(
                    "blueprint_mutation_readback_plan_recorded",
                    platform_context.get("blueprint_readback_plan_recorded", False),
                )),
                "blueprint_mutation_target_blueprint_path": platform_receipt.get(
                    "blueprint_mutation_target_blueprint_path",
                    platform_context.get("blueprint_mutation_target_blueprint_path", ""),
                ),
                "blueprint_mutation_intended_summary": platform_receipt.get(
                    "blueprint_mutation_intended_summary",
                    platform_context.get("blueprint_mutation_intended_summary", ""),
                ),
                "blueprint_mutation_evidence_required_preview": bounded_string_preview(
                    platform_receipt.get("blueprint_mutation_evidence_required_preview", []),
                    8,
                ),
                "blueprint_mutation_evidence_merge_policy": platform_receipt.get(
                    "blueprint_mutation_evidence_merge_policy",
                    "preserve_existing_evidence_unless_reset",
                ),
                "blueprint_mutation_human_approval_required": bool(platform_receipt.get("blueprint_mutation_human_approval_required", True)),
                "blueprint_mutation_evidence_no_editor_mutation": bool(platform_receipt.get("blueprint_mutation_evidence_no_editor_mutation", True)),
                "blueprint_mutation_evidence_no_blueprint_mutation": bool(platform_receipt.get("blueprint_mutation_evidence_no_blueprint_mutation", True)),
                "blueprint_mutation_evidence_no_compile": bool(platform_receipt.get("blueprint_mutation_evidence_no_compile", True)),
                "blueprint_mutation_evidence_no_save": bool(platform_receipt.get("blueprint_mutation_evidence_no_save", True)),
                "blueprint_mutation_evidence_no_pie": bool(platform_receipt.get("blueprint_mutation_evidence_no_pie", True)),
                "no_mutation_test_ok": bool(platform_context.get("no_mutation_test_ok", False)),
                "no_mutation_test_status": platform_context.get("no_mutation_test_status", ""),
                "no_mutation_test_mutation_count": platform_context.get("no_mutation_test_mutation_count"),
                "no_mutation_test_exit_code": platform_context.get("no_mutation_test_exit_code"),
                "no_mutation_test_tracked_file_count": platform_context.get("no_mutation_test_tracked_file_count"),
                "no_mutation_test_snapshot_digest_match": bool(platform_context.get("no_mutation_test_snapshot_digest_match", False)),
                "no_mutation_test_snapshot_scope": platform_context.get("no_mutation_test_snapshot_scope", ""),
                "no_mutation_test_snapshot_hash_algorithm": platform_context.get("no_mutation_test_snapshot_hash_algorithm", ""),
                "no_mutation_test_operator_command_handoff": (
                    list(platform_context.get("no_mutation_test_operator_command_handoff", []))[:1]
                    if isinstance(platform_context.get("no_mutation_test_operator_command_handoff"), list)
                    else []
                ),
                "high_value_wrapper_ok": bool(platform_context.get("high_value_wrapper_ok", False)),
                "build_wrapper_status": platform_context.get("build_wrapper_status", ""),
                "last_plugin_build_status": platform_context.get("last_plugin_build_status", ""),
                "no_provider_call": True,
                "no_editor_mutation": True,
                "no_git_mutation": True,
            },
        ))

    dirty_artifacts = dirty_promotion_evidence_artifacts(platform_context)
    if dirty_artifacts:
        contract = platform_context.get("dirty_promotion_contract") if isinstance(platform_context.get("dirty_promotion_contract"), dict) else {}
        review_batch_preview = (
            contract.get("review_batch_preview")
            if isinstance(contract.get("review_batch_preview"), list)
            else []
        )
        evidence_review_matrix_preview = (
            contract.get("evidence_review_matrix_preview")
            if isinstance(contract.get("evidence_review_matrix_preview"), list)
            else []
        )
        target_review_batch = next((item for item in review_batch_preview if isinstance(item, dict)), {})
        target_review_gap = next((item for item in evidence_review_matrix_preview if isinstance(item, dict)), {})
        target_missing_evidence = (
            target_review_gap.get("missing_evidence")
            if isinstance(target_review_gap.get("missing_evidence"), list)
            else []
        )
        receipt_state = str(contract.get("review_receipt_state", "missing"))
        receipt_exists = bool(contract.get("review_receipt_exists", False))
        items.append(evidence_recording_item(
            item_id="record_dirty_promotion_review",
            source="dirty_promotion_contract",
            phase_name="session_preflight",
            evidence_type="dirty_promotion_review",
            label="Record dirty promotion review receipt",
            required_artifacts=dirty_artifacts,
            state=(
                "recorded"
                if "dirty_promotion_review" in existing_types
                else ("blocked" if receipt_state == "blocked" else "pending")
            ),
            suggested_summary="Record the dirty-state promotion review before staging, merging, or claiming WIP is promotion-ready.",
            requires_bridge=False,
            metadata={
                "schema": str(contract.get("schema", "unreal_mcp_dirty_promotion_contract.v1")),
                "receipt_state": receipt_state,
                "receipt_exists": receipt_exists,
                "receipt_current": bool(contract.get("review_receipt_current", False)),
                "receipt_stale": bool(contract.get("review_receipt_stale", False)),
                "receipt_dirty_signature_match": bool(contract.get("review_receipt_dirty_signature_match", False)),
                "receipt_path": contract.get("review_receipt_path", "Saved\\DirtyPromotionReview\\last_review_receipt.json"),
                "required_command": contract.get("review_receipt_required_command", "python scripts\\write_dirty_promotion_review.py"),
                "state": contract.get("state", ""),
                "ready_for_promotion": bool(contract.get("ready_for_promotion", False)),
                "dirty_risk": contract.get("dirty_risk", ""),
                "dirty_group_count": int(contract.get("dirty_group_count", 0) or 0),
                "dirty_signature_algorithm": contract.get("dirty_signature_algorithm", ""),
                "dirty_signature_entry_count": int(contract.get("dirty_signature_entry_count", 0) or 0),
                "tracked_change_count": int(contract.get("tracked_change_count", 0) or 0),
                "untracked_count": int(contract.get("untracked_count", 0) or 0),
                "review_batch_count": int(contract.get("review_batch_count", 0) or 0),
                "evidence_review_matrix_count": int(contract.get("evidence_review_matrix_count", 0) or 0),
                "evidence_unresolved_count": int(contract.get("evidence_unresolved_count", 0) or 0),
                "evidence_review_policy": contract.get("evidence_review_policy", ""),
                "target_review_group": str(contract.get("target_review_group") or target_review_batch.get("group") or target_review_gap.get("group") or ""),
                "target_review_order": int(contract.get("target_review_order", target_review_batch.get("order", target_review_gap.get("order", 0))) or 0),
                "target_review_scope": str(contract.get("target_review_scope") or target_review_batch.get("candidate_batch_scope") or target_review_gap.get("candidate_batch_scope") or ""),
                "target_review_tracked_count": int(contract.get("target_review_tracked_count", target_review_batch.get("tracked_count", target_review_gap.get("tracked_count", 0))) or 0),
                "target_review_untracked_count": int(contract.get("target_review_untracked_count", target_review_batch.get("untracked_count", target_review_gap.get("untracked_count", 0))) or 0),
                "target_review_missing_evidence_count": int(
                    contract.get("target_review_missing_evidence_count", target_review_gap.get("missing_evidence_count", len(target_missing_evidence))) or 0
                ),
                "target_review_status": str(contract.get("target_review_status") or "missing_evidence"),
                "target_review_evidence_complete": bool(contract.get("target_review_evidence_complete", False)),
                "target_review_recorded_evidence_count": int(contract.get("target_review_recorded_evidence_count", 0) or 0),
                "target_review_recorded_evidence_preview": bounded_string_preview(
                    contract.get("target_review_recorded_evidence_preview", []),
                    8,
                ),
                "target_review_human_approval_recorded": bool(contract.get("target_review_human_approval_recorded", False)),
                "target_review_missing_evidence_preview": bounded_string_preview(
                    contract.get("target_review_missing_evidence_preview", target_missing_evidence),
                    8,
                ),
                "target_review_required_evidence_preview": bounded_string_preview(
                    contract.get("target_review_required_evidence_preview", target_review_gap.get("required_evidence", [])),
                    8,
                ),
                "target_review_decision_prompt_preview": bounded_string_preview(
                    contract.get("target_review_decision_prompt_preview", target_review_batch.get("decision_prompts", [])),
                    8,
                ),
                "target_review_receipt_command_template": str(contract.get("target_review_receipt_command_template", "")),
                "target_review_approval_receipt_command_template": str(
                    contract.get("target_review_approval_receipt_command_template", "")
                ),
                "target_review_receipt_command_policy": str(contract.get("target_review_receipt_command_policy", "")),
                "target_review_operator_command_handoff": (
                    list(contract.get("target_review_operator_command_handoff", []))[:2]
                    if isinstance(contract.get("target_review_operator_command_handoff"), list)
                    else []
                ),
                "target_review_pending_human_approval_only": bool(contract.get("target_review_pending_human_approval_only", False)),
                "target_review_human_approval_gate": str(contract.get("target_review_human_approval_gate", "human_approval_before_stage_commit_merge")),
                "target_review_human_approval_command_handoff": (
                    list(contract.get("target_review_human_approval_command_handoff", []))[:1]
                    if isinstance(contract.get("target_review_human_approval_command_handoff"), list)
                    else []
                ),
                "target_review_focused_test_command_handoff": (
                    list(contract.get("target_review_focused_test_command_handoff", []))[:5]
                    if isinstance(contract.get("target_review_focused_test_command_handoff"), list)
                    else []
                ),
                "target_review_focused_test_command_count": int(
                    contract.get("target_review_focused_test_command_count", target_review_batch.get("focused_test_command_count", 0)) or 0
                ),
                "target_review_focused_test_command_preview": bounded_string_preview(
                    contract.get("target_review_focused_test_command_preview", target_review_batch.get("focused_test_commands", [])),
                    5,
                ),
                "target_review_sample_preview": bounded_string_preview(
                    contract.get("target_review_sample_preview", target_review_batch.get("sample", [])),
                    5,
                ),
                "target_review_promotion_allowed_after_receipt": bool(
                    contract.get("target_review_promotion_allowed_after_receipt", target_review_batch.get("promotion_allowed_after_receipt", False))
                ),
                "target_review_merge_policy": str(contract.get("target_review_merge_policy", "")),
                "target_review_previous_evidence_merged": bool(contract.get("target_review_previous_evidence_merged", False)),
                "target_review_reset_evidence": bool(contract.get("target_review_reset_evidence", False)),
                "target_review_source": str(contract.get("target_review_source", "")),
                "evidence_review_matrix_preview": [
                    {
                        "group": str(item.get("group", "")),
                        "missing_evidence_count": int(item.get("missing_evidence_count", 0) or 0),
                        "promotion_allowed": bool(item.get("promotion_allowed", False)),
                    }
                    for item in (
                        contract.get("evidence_review_matrix_preview")
                        if isinstance(contract.get("evidence_review_matrix_preview"), list)
                        else []
                    )[:3]
                    if isinstance(item, dict)
                ],
                "promotion_batch_policy": contract.get("promotion_batch_policy", ""),
                "artifact_policy": contract.get("artifact_policy", ""),
                "safe_promotion_next_steps": bounded_string_preview(contract.get("safe_promotion_next_steps", []), 8),
                "recommended_next": contract.get("recommended_next", ""),
                "no_git_mutation": bool(contract.get("no_git_mutation", True)),
                "no_stage": bool(contract.get("no_stage", True)),
                "no_commit": bool(contract.get("no_commit", True)),
                "no_clean": bool(contract.get("no_clean", True)),
                "no_delete": bool(contract.get("no_delete", True)),
                "no_branch_or_merge": bool(contract.get("no_branch_or_merge", True)),
                "no_provider_call": bool(contract.get("no_provider_call", True)),
                "no_editor_mutation": bool(contract.get("no_editor_mutation", True)),
            },
        ))

    provider_artifacts = provider_config_evidence_artifacts(platform_context)
    if provider_artifacts:
        provider_secret_contract = platform_context.get("provider_secret_contract") if isinstance(platform_context.get("provider_secret_contract"), dict) else {}
        provider_repair_contract = platform_context.get("provider_repair_contract") if isinstance(platform_context.get("provider_repair_contract"), dict) else {}
        receipt_state = str(platform_context.get("provider_config_review_receipt_state", "missing"))
        receipt_exists = bool(platform_context.get("provider_config_review_receipt_exists", False))
        items.append(evidence_recording_item(
            item_id="record_provider_config_review",
            source="provider_config",
            phase_name="session_preflight",
            evidence_type="provider_config_review",
            label="Record masked provider config review",
            required_artifacts=provider_artifacts,
            state=(
                "recorded"
                if "provider_config_review" in existing_types
                else ("blocked" if receipt_state == "blocked" else "pending")
            ),
            suggested_summary="Record masked Tripo/Uthana provider configuration review before wallet checks or paid provider work.",
            requires_bridge=False,
            metadata={
                "schema": "unreal_mcp_provider_config_review_receipt.v1",
                "receipt_state": receipt_state,
                "receipt_exists": receipt_exists,
                "receipt_path": platform_context.get("provider_config_review_receipt_path", "Saved\\ProviderConfigReview\\last_review_receipt.json"),
                "required_command": platform_context.get("provider_config_review_receipt_required_command", "python scripts\\write_provider_config_review.py"),
                "operator_command_handoff": (
                    list(platform_context.get("provider_config_operator_command_handoff", []))[:1]
                    if isinstance(platform_context.get("provider_config_operator_command_handoff"), list)
                    else []
                ),
                "provider": platform_context.get("provider", "tripo"),
                "animation_provider": platform_context.get("animation_provider", "uthana"),
                "provider_api_key_configured": bool(platform_context.get("provider_api_key_configured", False)),
                "animation_provider_api_key_configured": bool(platform_context.get("animation_provider_api_key_configured", False)),
                "provider_api_key_source": platform_context.get("provider_api_key_source", "missing"),
                "animation_provider_api_key_source": platform_context.get("animation_provider_api_key_source", "missing"),
                "provider_secrets_gitignored": bool(platform_context.get("provider_secrets_gitignored", False)),
                "provider_settings_gitignored": bool(platform_context.get("provider_settings_gitignored", False)),
                "secret_contract_schema": provider_secret_contract.get("schema", ""),
                "masked_status_only": bool(provider_secret_contract.get("masked_status_only", True)),
                "raw_key_returned": bool(provider_secret_contract.get("raw_key_returned", False)),
                "save_tool": provider_repair_contract.get("save_tool", "gen_save_provider_config"),
                "proof_tool": provider_repair_contract.get("proof_tool", "gen_get_provider_config(include_paths=True)"),
                "no_raw_key": True,
                "no_provider_call": True,
                "no_wallet_check": True,
                "no_credit_reservation": True,
                "no_spend_confirmation": True,
                "no_editor_mutation": True,
            },
        ))

    bridge_artifacts = bridge_ping_evidence_artifacts(platform_context)
    if bridge_artifacts:
        receipt_state = str(platform_context.get("bridge_ping_receipt_state", "missing"))
        receipt_exists = bool(platform_context.get("bridge_ping_receipt_exists", False))
        items.append(evidence_recording_item(
            item_id="record_bridge_ping_receipt",
            source="bridge_ping",
            phase_name="session_preflight",
            evidence_type="bridge_ping_receipt",
            label="Record bridge ping receipt",
            required_artifacts=bridge_artifacts,
            state="recorded" if "bridge_ping_receipt" in existing_types else "pending",
            suggested_summary="Record the bridge ping receipt state before any editor mutation or Blueprint execution.",
            requires_bridge=False,
            metadata={
                "schema": "unreal_mcp_bridge_ping_receipt.v1",
                "receipt_state": receipt_state,
                "receipt_exists": receipt_exists,
                "receipt_path": platform_context.get("bridge_ping_receipt_path", "Saved\\BridgePing\\last_ping_receipt.json"),
                "required_command": platform_context.get("bridge_ping_required_command", "python scripts\\bridge_ping.py"),
                "successful_bridge_ping": bool(platform_context.get("successful_bridge_ping", False)),
                "bridge_ready": bool(platform_context.get("bridge_ready", False)),
                "bridge_tcp_ready": bool(platform_context.get("bridge_tcp_ready", False)),
                "bridge_host": platform_context.get("bridge_host", "127.0.0.1"),
                "bridge_port": int(platform_context.get("bridge_port", 0) or 0),
                "editor_mutation_allowed": bool(platform_context.get("ready_for_editor_mutation", False)),
                "blueprint_missing_gate_count": int(platform_context.get("blueprint_missing_gate_count", 0) or 0),
                "operator_command_handoff": (
                    list(platform_context.get("bridge_ping_operator_command_handoff", []))[:1]
                    if isinstance(platform_context.get("bridge_ping_operator_command_handoff"), list)
                    else []
                ),
                "no_editor_mutation": True,
                "no_pie_run": True,
                "no_provider_call": True,
                "no_git_mutation": True,
                "stop_before_editor_or_pie": True,
            },
        ))

    chat_artifacts = chat_cockpit_start_evidence_artifacts(platform_context)
    if chat_artifacts:
        repair = platform_context.get("chat_cockpit_repair_contract") if isinstance(platform_context.get("chat_cockpit_repair_contract"), dict) else {}
        items.append(evidence_recording_item(
            item_id="record_chat_cockpit_start_receipt",
            source="chat_cockpit_repair_contract",
            phase_name="session_preflight",
            evidence_type="chat_cockpit_start_receipt",
            label="Record chat cockpit startup receipt",
            required_artifacts=chat_artifacts,
            state="recorded" if "chat_cockpit_start_receipt" in existing_types else "pending",
            suggested_summary="Record MCP Chat startup and /chat/history health evidence before relying on cockpit workflow actions.",
            requires_bridge=False,
            metadata={
                "schema": "unreal_mcp_chat_cockpit_start_receipt.v1",
                "chat_ready": bool(platform_context.get("chat_ready", False)),
                "chat_tcp_ready": bool(platform_context.get("chat_tcp_ready", False)),
                "chat_base_url": platform_context.get("chat_base_url", ""),
                "chat_health_endpoint": platform_context.get("chat_health_endpoint", ""),
                "startup_script": platform_context.get("chat_startup_script", "scripts\\start_chat_cockpit_server.ps1"),
                "startup_receipt_path": platform_context.get("chat_startup_receipt_path") or repair.get("startup_receipt_path", "Saved\\ChatCockpit\\last_start_receipt.json"),
                "startup_command": platform_context.get("chat_startup_command") or repair.get("startup_command", ""),
                "manual_startup_command": platform_context.get("chat_manual_startup_command") or repair.get("manual_startup_command", ""),
                "proof_command": repair.get("proof_command", ""),
                "proof_expected": repair.get("proof_expected", ""),
                "repair_state": repair.get("state", ""),
                "no_process_start": bool(repair.get("no_process_start", True)),
                "no_port_kill": bool(repair.get("no_port_kill", True)),
                "no_editor_mutation": bool(repair.get("no_editor_mutation", True)),
                "no_provider_call": bool(repair.get("no_provider_call", True)),
                "no_git_mutation": bool(repair.get("no_git_mutation", True)),
            },
        ))

    spend_context = provider_spend if isinstance(provider_spend, dict) else {}
    paid_artifacts = paid_generation_evidence_artifacts(spend_context, readiness_policy)
    if paid_artifacts:
        contract = spend_context.get("paid_generation_evidence_contract") if isinstance(spend_context.get("paid_generation_evidence_contract"), dict) else {}
        items.append(evidence_recording_item(
            item_id="record_paid_generation_evidence",
            source="provider_spend_context",
            phase_name=target_phase,
            evidence_type="paid_generation_evidence",
            label="Record paid generation wallet and approval evidence",
            required_artifacts=paid_artifacts,
            state="recorded" if "paid_generation_evidence" in existing_types else "pending",
            suggested_summary="Record Tripo wallet or Uthana allowance proof plus explicit human spend/usage approval before paid provider work.",
            metadata={
                "schema": contract.get("schema", "unreal_mcp_paid_generation_evidence_contract.v1"),
                "state": spend_context.get("state", ""),
                "provider": spend_context.get("provider", ""),
                "missing_gate_count": int(spend_context.get("missing_gate_count", 0) or 0),
                "missing_gate_preview": bounded_string_preview(spend_context.get("missing_gate_preview", []), 8),
                "wallet_evidence_recorded": bool(contract.get("wallet_evidence_recorded", False)),
                "mesh_wallet_evidence_recorded": bool(contract.get("mesh_wallet_evidence_recorded", False)),
                "animation_allowance_evidence_recorded": bool(contract.get("animation_allowance_evidence_recorded", False)),
                "spend_confirmation_recorded": bool(contract.get("spend_confirmation_recorded", False)),
                "explicit_spend_approval_recorded": bool(contract.get("explicit_spend_approval_recorded", False)),
                "explicit_usage_approval_recorded": bool(contract.get("explicit_usage_approval_recorded", False)),
                "estimated_spend_reviewed": bool(contract.get("estimated_spend_reviewed", False)),
                "estimated_motion_seconds_reviewed": bool(contract.get("estimated_motion_seconds_reviewed", False)),
                "mesh_provider": contract.get("mesh_provider", "tripo"),
                "animation_provider": contract.get("animation_provider", "uthana"),
                "review_receipt_exists": bool(contract.get("review_receipt_exists", False)),
                "review_receipt_state": contract.get("review_receipt_state", "missing"),
                "review_receipt_path": contract.get("review_receipt_path", "Saved\\PaidGenerationEvidence\\last_review_receipt.json"),
                "review_receipt_required_command": contract.get("review_receipt_required_command", "python scripts\\write_paid_generation_evidence_review.py"),
                "mesh_wallet_tool": contract.get("mesh_wallet_tool", "gen_tripo_get_credit_balance"),
                "animation_allowance_tools": bounded_string_preview(contract.get("animation_allowance_tools", []), 3),
                "ledger_tool": contract.get("ledger_tool", "skill_record_ide_companion_evidence"),
                "spend_approval_field": contract.get("spend_approval_field", ""),
                "wallet_evidence_review_steps": bounded_string_preview(contract.get("wallet_evidence_review_steps", []), 5),
                "wallet_evidence_receipt_command_template": contract.get("wallet_evidence_receipt_command_template", ""),
                "mesh_wallet_evidence_receipt_command_template": contract.get("mesh_wallet_evidence_receipt_command_template", ""),
                "animation_allowance_receipt_command_template": contract.get("animation_allowance_receipt_command_template", ""),
                "spend_confirmation_receipt_command_template": contract.get("spend_confirmation_receipt_command_template", ""),
                "operator_command_handoff": (
                    list(contract.get("operator_command_handoff", []))[:3]
                    if isinstance(contract.get("operator_command_handoff"), list)
                    else []
                ),
                "no_spend_checks": bounded_string_preview(contract.get("no_spend_checks", []), 5),
                "evidence_required_preview": bounded_string_preview(contract.get("evidence_required_preview", []), 8),
                "fallback_tool": contract.get("fallback_tool", "skill_compile_ide_companion_placeholder_manifest"),
                "fallback_reason": contract.get("fallback_reason", ""),
                "network_required_now": bool(contract.get("network_required_now", False)),
                "spend_required_now": bool(contract.get("spend_required_now", False)),
                "future_network_required": bool(contract.get("future_network_required", True)),
                "future_spend_required": bool(contract.get("future_spend_required", True)),
                "unreal_editor_required_now": bool(contract.get("unreal_editor_required_now", False)),
                "no_provider_call": bool(contract.get("no_provider_call", True)),
                "no_credit_reservation": bool(contract.get("no_credit_reservation", True)),
                "no_task_submission": bool(contract.get("no_task_submission", True)),
                "no_ledger_write": bool(contract.get("no_ledger_write", True)),
                "review_contract_no_ledger_write": bool(contract.get("no_ledger_write", True)),
            },
        ))

    policy_artifacts = readiness_policy_evidence_artifacts(readiness_policy)
    if policy_artifacts:
        blocked_policies = [
            name
            for name in ("editor_mutation", "paid_generation", "paid_animation_generation", "blueprint_mutation", "wip_promotion")
            if isinstance(readiness_policy.get(name), dict) and not readiness_policy.get(name, {}).get("allowed", False)
        ]
        editor_mutation_policy = (
            readiness_policy.get("editor_mutation")
            if isinstance(readiness_policy.get("editor_mutation"), dict)
            else {}
        )
        editor_mutation_evidence = (
            editor_mutation_policy.get("evidence_required")
            if isinstance(editor_mutation_policy.get("evidence_required"), list)
            else []
        )
        wip_promotion_policy = readiness_policy.get("wip_promotion") if isinstance(readiness_policy.get("wip_promotion"), dict) else {}
        wip_promotion_evidence = (
            wip_promotion_policy.get("evidence_required")
            if isinstance(wip_promotion_policy.get("evidence_required"), list)
            else []
        )
        blueprint_mutation_policy = (
            readiness_policy.get("blueprint_mutation")
            if isinstance(readiness_policy.get("blueprint_mutation"), dict)
            else {}
        )
        blueprint_mutation_evidence = (
            blueprint_mutation_policy.get("evidence_required")
            if isinstance(blueprint_mutation_policy.get("evidence_required"), list)
            else []
        )
        paid_generation_policy = (
            readiness_policy.get("paid_generation")
            if isinstance(readiness_policy.get("paid_generation"), dict)
            else {}
        )
        paid_generation_evidence = (
            paid_generation_policy.get("evidence_required")
            if isinstance(paid_generation_policy.get("evidence_required"), list)
            else []
        )
        paid_animation_policy = (
            readiness_policy.get("paid_animation_generation")
            if isinstance(readiness_policy.get("paid_animation_generation"), dict)
            else {}
        )
        paid_animation_evidence = (
            paid_animation_policy.get("evidence_required")
            if isinstance(paid_animation_policy.get("evidence_required"), list)
            else []
        )
        items.append(evidence_recording_item(
            item_id="record_readiness_policy",
            source="readiness_policy",
            phase_name=target_phase,
            evidence_type="readiness_policy",
            label="Record readiness policy gate evidence",
            required_artifacts=policy_artifacts,
            state="recorded" if "readiness_policy" in existing_types else "pending",
            suggested_summary="Record missing editor, paid-generation, Blueprint, and WIP-promotion evidence gates before execution or promotion.",
            metadata={
                "schema": readiness_policy.get("schema", "unreal_mcp_chat_readiness_policy_summary.v1"),
                "state": readiness_policy.get("state", ""),
                "blocked_policy_count": int(readiness_policy.get("blocked_policy_count", len(blocked_policies)) or 0),
                "blocked_policy_preview": bounded_string_preview(blocked_policies, 5),
                "editor_mutation_allowed": bool(editor_mutation_policy.get("allowed", False)),
                "editor_mutation_missing_gate_count": (
                    len(editor_mutation_policy.get("missing_gates", []))
                    if isinstance(editor_mutation_policy.get("missing_gates"), list)
                    else 0
                ),
                "editor_mutation_missing_gate_preview": bounded_string_preview(editor_mutation_policy.get("missing_gates", []), 8),
                "editor_mutation_evidence_required_count": len(editor_mutation_evidence),
                "editor_mutation_evidence_required_preview": bounded_string_preview(editor_mutation_evidence, 8),
                "paid_generation_allowed": bool(paid_generation_policy.get("allowed", False)),
                "paid_generation_missing_gate_count": (
                    len(paid_generation_policy.get("missing_gates", []))
                    if isinstance(paid_generation_policy.get("missing_gates"), list)
                    else 0
                ),
                "paid_generation_missing_gate_preview": bounded_string_preview(paid_generation_policy.get("missing_gates", []), 8),
                "paid_generation_evidence_required_count": len(paid_generation_evidence),
                "paid_generation_evidence_required_preview": bounded_string_preview(paid_generation_evidence, 8),
                "paid_animation_generation_allowed": bool(paid_animation_policy.get("allowed", False)),
                "paid_animation_generation_missing_gate_count": (
                    len(paid_animation_policy.get("missing_gates", []))
                    if isinstance(paid_animation_policy.get("missing_gates"), list)
                    else 0
                ),
                "paid_animation_generation_missing_gate_preview": bounded_string_preview(paid_animation_policy.get("missing_gates", []), 8),
                "paid_animation_generation_evidence_required_count": len(paid_animation_evidence),
                "paid_animation_generation_evidence_required_preview": bounded_string_preview(paid_animation_evidence, 8),
                "blueprint_mutation_allowed": bool(blueprint_mutation_policy.get("allowed", False)),
                "blueprint_mutation_missing_gate_count": (
                    len(blueprint_mutation_policy.get("missing_gates", []))
                    if isinstance(blueprint_mutation_policy.get("missing_gates"), list)
                    else 0
                ),
                "blueprint_mutation_missing_gate_preview": bounded_string_preview(blueprint_mutation_policy.get("missing_gates", []), 8),
                "blueprint_mutation_evidence_required_count": len(blueprint_mutation_evidence),
                "blueprint_mutation_evidence_required_preview": bounded_string_preview(blueprint_mutation_evidence, 8),
                "wip_promotion_allowed": bool(wip_promotion_policy.get("allowed", False)),
                "wip_promotion_missing_gate_count": (
                    len(wip_promotion_policy.get("missing_gates", []))
                    if isinstance(wip_promotion_policy.get("missing_gates"), list)
                    else 0
                ),
                "wip_promotion_missing_gate_preview": bounded_string_preview(wip_promotion_policy.get("missing_gates", []), 8),
                "wip_promotion_evidence_required_count": len(wip_promotion_evidence),
                "wip_promotion_evidence_required_preview": bounded_string_preview(wip_promotion_evidence, 10),
                "no_editor_mutation": True,
                "no_provider_call": True,
                "no_git_mutation": True,
            },
        ))

    for index, queue in enumerate(queues[:3], start=1):
        artifacts = bounded_string_preview(queue.get("evidence_preview", []), 5)
        if not artifacts and int(queue.get("evidence_count", 0) or 0):
            artifacts = ["queued action evidence"]
        if artifacts:
            bridge_blocked = bool(queue.get("bridge_blocked", False))
            preview_actions = queue.get("preview_actions") if isinstance(queue.get("preview_actions"), list) else []
            next_action = preview_actions[0] if preview_actions and isinstance(preview_actions[0], dict) else {}
            items.append(evidence_recording_item(
                item_id=f"record_editor_queue_{index}",
                source="editor_queue",
                phase_name=str(queue.get("target_phase") or target_phase),
                evidence_type="editor_queue",
                label=f"Record queued editor action evidence for {queue.get('queue_name', 'editor_queue')}",
                required_artifacts=artifacts,
                state="blocked" if bridge_blocked else "pending",
                suggested_summary="Record compile/readback proof after the queued editor action runs.",
                requires_bridge=bool(queue.get("bridge_required", False)),
                metadata={
                    "queue_path": queue.get("queue_path", ""),
                    "queue_name": queue.get("queue_name", ""),
                    "target_phase": queue.get("target_phase", ""),
                    "next_action_id": queue.get("next_action_id", next_action.get("id", "")),
                    "next_action_tool": queue.get("next_action_tool", next_action.get("tool", "")),
                    "next_action_label": next_action.get("label", "") or queue.get("next_action_id", ""),
                    "feature_template_schema": queue.get("feature_template_schema", ""),
                    "feature_template_name": queue.get("feature_template_name", ""),
                    "feature_template_display_name": queue.get("feature_template_display_name", ""),
                    "feature_template_operation_count": int(queue.get("feature_template_operation_count", 0) or 0),
                    "feature_template_next_operation_id": queue.get("feature_template_next_operation_id", ""),
                    "feature_template_next_operation_type": queue.get("feature_template_next_operation_type", ""),
                    "feature_template_next_operation_summary": queue.get("feature_template_next_operation_summary", ""),
                    "feature_template_next_operation_tool_preview": bounded_string_preview(
                        queue.get("feature_template_next_operation_tool_preview", []),
                        8,
                    ),
                    "feature_template_next_operation_required_before_preview": bounded_string_preview(
                        queue.get("feature_template_next_operation_required_before_preview", []),
                        8,
                    ),
                    "feature_template_next_operation_required_after_preview": bounded_string_preview(
                        queue.get("feature_template_next_operation_required_after_preview", []),
                        8,
                    ),
                    "feature_template_next_operation_stop_if_missing_preview": bounded_string_preview(
                        queue.get("feature_template_next_operation_stop_if_missing_preview", []),
                        8,
                    ),
                    "action_count": int(queue.get("action_count", 0) or 0),
                    "preview_action_count": len(preview_actions),
                    "argument_keys": next_action.get("argument_keys", []) if isinstance(next_action.get("argument_keys"), list) else [],
                    "bridge_blocked": bridge_blocked,
                    "can_execute_now": bool(queue.get("can_execute_now", False)),
                    "requires_successful_bridge_ping_before_execution": True,
                    "no_auto_execute": True,
                    "no_editor_mutation": True,
                    "no_pie_run": True,
                    "no_provider_call": True,
                    "no_git_mutation": True,
                    "evidence_preview": artifacts,
                },
            ))

    runtime_items = runtime_verification.get("items") if isinstance(runtime_verification.get("items"), list) else []
    runtime_artifacts = [
        str(item.get("evidence_required", item.get("label", "")))
        for item in runtime_items[:5]
        if isinstance(item, dict)
    ]
    if runtime_artifacts:
        items.append(evidence_recording_item(
            item_id="record_runtime_verification",
            source="runtime_verification",
            phase_name=str(runtime_verification.get("target_phase") or "runtime_verification"),
            evidence_type="runtime_verification",
            label="Record runtime verification proof",
            required_artifacts=runtime_artifacts,
            state="recorded" if runtime_verification.get("runtime_evidence_event_count", 0) else runtime_verification.get("state", "pending"),
            suggested_summary="Record PIE log, viewport screenshot, and runtime state proof.",
            requires_bridge=True,
            metadata={
                "target_phase": runtime_verification.get("target_phase", ""),
                "state": runtime_verification.get("state", ""),
                "can_verify_now": bool(runtime_verification.get("available") and not runtime_verification.get("bridge_blocked", False)),
                "bridge_blocked": bool(runtime_verification.get("bridge_blocked", False)),
                "pie_validation_count": int(runtime_verification.get("pie_validation_count", 0) or 0),
                "compile_check_count": int(runtime_verification.get("compile_check_count", 0) or 0),
                "evidence_requirement_count": int(runtime_verification.get("evidence_requirement_count", 0) or 0),
                "runtime_proof_contract_schema": runtime_verification.get("runtime_proof_contract_schema", ""),
                "runtime_proof_mode": runtime_verification.get("runtime_proof_mode", ""),
                "runtime_proof_required_count": int(runtime_verification.get("runtime_proof_required_count", 0) or 0),
                "runtime_proof_required_before_count": int(runtime_verification.get("runtime_proof_required_before_count", 0) or 0),
                "runtime_proof_required_before_preview": bounded_string_preview(runtime_verification.get("runtime_proof_required_before_preview", []), 8),
                "runtime_proof_required_preview": bounded_string_preview(runtime_verification.get("runtime_proof_required_preview", []), 8),
                "runtime_proof_tool_preview": bounded_string_preview(runtime_verification.get("runtime_proof_tool_preview", []), 8),
                "runtime_proof_stop_preview": bounded_string_preview(runtime_verification.get("runtime_proof_stop_preview", []), 5),
                "runtime_probe_allowed": bool(runtime_verification.get("available") and not runtime_verification.get("bridge_blocked", False)),
                "requires_successful_bridge_ping_before_runtime_probe": True,
                "runtime_evidence_event_count": int(runtime_verification.get("runtime_evidence_event_count", 0) or 0),
                "blocked_item_count": sum(1 for item in runtime_items if isinstance(item, dict) and item.get("state") == "blocked"),
                "pending_item_count": sum(1 for item in runtime_items if isinstance(item, dict) and item.get("state") == "pending"),
                "recorded_item_count": sum(1 for item in runtime_items if isinstance(item, dict) and item.get("state") == "recorded"),
                "runtime_proof_preview": runtime_artifacts,
                "compile_check_preview": bounded_string_preview(runtime_verification.get("compile_check_preview", []), 4),
                "no_pie_run": True,
                "no_editor_mutation": True,
                "no_provider_call": True,
                "no_git_mutation": True,
            },
        ))

    if repair_loop.get("available"):
        items.append(evidence_recording_item(
            item_id="record_repair_loop",
            source="repair_loop",
            phase_name=target_phase,
            evidence_type="repair",
            label="Record repair attempt outcome",
            required_artifacts=bounded_string_preview(repair_loop.get("evidence_preview", []), 5) or ["repair work order", "compile/readback result"],
            state="blocked" if repair_loop.get("bridge_blocked") else "pending",
            suggested_summary="Record the scoped repair attempt, result, and remaining blockers.",
            requires_bridge=True,
        ))

    if asset_lifecycles:
        required = [
            str(lifecycle.get("manifest_path", ""))
            for lifecycle in asset_lifecycles[:3]
            if lifecycle.get("manifest_path")
        ]
        items.append(evidence_recording_item(
            item_id="record_generated_asset_lifecycle",
            source="generated_asset_lifecycles",
            phase_name=target_phase,
            evidence_type="generated_asset_lifecycle",
            label="Record generated asset lifecycle state",
            required_artifacts=required or ["generated asset lifecycle manifest"],
            state="pending",
            suggested_summary="Record provider, placeholder, import, or quality-gate evidence for generated assets.",
        ))

    target_generated_asset = select_generated_asset_context(generated_asset_quality_gate)
    if target_generated_asset:
        asset_name = target_generated_asset.get("name") or target_generated_asset.get("id") or "generated asset"
        quality_artifacts = bounded_string_preview(target_generated_asset.get("quality_gate_preview", []), 4)
        required = [
            item
            for item in (
                f"asset:{asset_name}",
                f"state:{target_generated_asset.get('state', '')}",
                f"next_gate:{target_generated_asset.get('next_gate', '')}",
                f"manifest:{target_generated_asset.get('manifest_path', '')}",
            )
            if not item.endswith(":")
        ]
        required.extend(quality_artifacts)
        expected_import = str(target_generated_asset.get("expected_import_path", ""))
        if expected_import:
            required.append(f"expected_import:{expected_import}")
        state = str(target_generated_asset.get("state", ""))
        items.append(evidence_recording_item(
            item_id="record_generated_asset_quality_gate",
            source="generated_asset_quality_gate",
            phase_name=target_phase,
            evidence_type="generated_asset_quality_gate",
            label=f"Record generated asset proof for {asset_name}",
            required_artifacts=required[:8],
            state="recorded" if "generated_asset_quality_gate" in existing_types else ("blocked" if state in {"import_pending", "quality_pending"} else "pending"),
            suggested_summary=(
                f"Record generated asset state for {asset_name}: "
                f"{target_generated_asset.get('state', '')}; next gate: {target_generated_asset.get('next_gate', '')}."
            ),
            requires_bridge=state in {"import_pending", "quality_pending"},
            metadata={
                "asset_id": target_generated_asset.get("id", ""),
                "asset_name": asset_name,
                "asset_role": target_generated_asset.get("role", ""),
                "provider": target_generated_asset.get("provider", ""),
                "state": state,
                "task_status": target_generated_asset.get("task_status", ""),
                "next_gate": target_generated_asset.get("next_gate", ""),
                "manifest_path": target_generated_asset.get("manifest_path", ""),
                "expected_import_path": target_generated_asset.get("expected_import_path", ""),
                "imported_asset_path": target_generated_asset.get("imported_asset_path", ""),
                "has_placeholder": bool(target_generated_asset.get("has_placeholder", False)),
                "quality_gate_count": int(target_generated_asset.get("quality_gate_count", 0) or 0),
                "quality_evidence_count": int(target_generated_asset.get("quality_evidence_count", 0) or 0),
                "quality_gate_preview": bounded_string_preview(target_generated_asset.get("quality_gate_preview", []), 5),
                "import_or_quality_pass_allowed": False,
                "requires_successful_bridge_ping_before_import_or_quality": state in {"import_pending", "quality_pending"} or bool(target_generated_asset.get("expected_import_path", "")),
                "requires_quality_evidence_before_replacement": True,
                "no_provider_call": True,
                "no_task_submission": True,
                "no_download": True,
                "no_import": True,
                "no_editor_mutation": True,
                "no_git_mutation": True,
            },
        ))

    target_generated_animation = generated_animation_lifecycle_context(
        asset_lifecycles=asset_lifecycles,
        readiness_policy=readiness_policy,
    )
    if target_generated_animation:
        animation = target_generated_animation.get("target_animation") if isinstance(target_generated_animation.get("target_animation"), dict) else {}
        animation_name = str(animation.get("name") or animation.get("id") or "generated animation")
        missing_stages = bounded_string_preview(target_generated_animation.get("missing_stage_preview", []), 5)
        required = [
            item
            for item in (
                f"animation:{animation_name}",
                f"provider:{target_generated_animation.get('animation_provider', '')}",
                f"status:{animation.get('task_status', '')}",
                f"motion:{animation.get('motion_id', '')}",
                f"skeleton:{animation.get('target_skeleton', '')}",
                f"expected_import:{animation.get('expected_import_path', '')}",
                f"usage_receipt:{target_generated_animation.get('uthana_usage_receipt_path', '')}",
                "compiler:gen_compile_generated_animation_evidence",
            )
            if not item.endswith(":")
        ]
        usage_contract = (
            target_generated_animation.get("uthana_usage_contract")
            if isinstance(target_generated_animation.get("uthana_usage_contract"), dict)
            else {}
        )
        for tool in usage_contract.get("allowance_tools", []) if isinstance(usage_contract.get("allowance_tools"), list) else []:
            tool_name = str(tool).strip()
            if tool_name:
                required.append(f"allowance_tool:{tool_name}")
        required.extend(f"missing:{stage}" for stage in missing_stages)
        quality_gate_count = int(target_generated_animation.get("quality_gate_count", 0) or 0)
        quality_evidence_count = int(target_generated_animation.get("quality_evidence_count", 0) or 0)
        items.append(evidence_recording_item(
            item_id="record_generated_animation_evidence",
            source="generated_animation_lifecycle",
            phase_name=target_phase,
            evidence_type="generated_animation_evidence",
            label=f"Record generated animation proof for {animation_name}",
            required_artifacts=required[:10],
            state="recorded" if "generated_animation_evidence" in existing_types else "pending",
            suggested_summary=(
                f"Record generated animation evidence for {animation_name}: "
                f"{quality_evidence_count}/{quality_gate_count} quality proof gates captured."
            ),
            requires_bridge=False,
            metadata={
                "animation_id": animation.get("id", ""),
                "animation_name": animation_name,
                "animation_role": animation.get("role", ""),
                "provider": target_generated_animation.get("animation_provider", animation.get("provider", "")),
                "task_type": animation.get("task_type", ""),
                "task_status": animation.get("task_status", ""),
                "motion_id": animation.get("motion_id", ""),
                "manifest_path": animation.get("manifest_path", ""),
                "expected_import_path": animation.get("expected_import_path", ""),
                "target_skeleton": animation.get("target_skeleton", ""),
                "format": animation.get("format", ""),
                "estimated_seconds": int(animation.get("estimated_seconds", 0) or 0),
                "default_character_id": animation.get("default_character_id", ""),
                "quality_gate_count": quality_gate_count,
                "quality_evidence_count": quality_evidence_count,
                "quality_evidence_missing_count": int(target_generated_animation.get("quality_evidence_missing_count", 0) or 0),
                "quality_proof_contract_schema": target_generated_animation.get("quality_proof_contract_schema", ""),
                "quality_proof_required_count": int(target_generated_animation.get("quality_proof_required_count", 0) or 0),
                "quality_proof_required_preview": bounded_string_preview(target_generated_animation.get("quality_proof_required_preview", []), 8),
                "missing_stage_preview": missing_stages,
                "quality_gate_preview": bounded_string_preview(animation.get("quality_gate_preview", []), 5),
                "compile_tool": "gen_compile_generated_animation_evidence",
                "submit_tool": target_generated_animation.get("submit_tool", ""),
                "download_tool": target_generated_animation.get("download_tool", ""),
                "import_tool": target_generated_animation.get("import_tool", ""),
                "uthana_usage_contract_schema": usage_contract.get("schema", ""),
                "uthana_usage_receipt_path": usage_contract.get("review_receipt_path", ""),
                "uthana_usage_receipt_required_command": usage_contract.get("review_receipt_required_command", ""),
                "uthana_allowance_tools": bounded_string_preview(usage_contract.get("allowance_tools", []), 4),
                "uthana_allowance_review_steps": bounded_string_preview(usage_contract.get("allowance_review_steps", []), 5),
                "uthana_usage_confirmation_field": usage_contract.get("usage_confirmation_field", ""),
                "uthana_usage_operator_command_handoff": (
                    list(usage_contract.get("operator_command_handoff", []))[:2]
                    if isinstance(usage_contract.get("operator_command_handoff"), list)
                    else []
                ),
                "uthana_usage_next_operator_command_handoff": (
                    dict(target_generated_animation.get("uthana_usage_next_operator_command_handoff", {}))
                    if isinstance(target_generated_animation.get("uthana_usage_next_operator_command_handoff"), dict)
                    else {}
                ),
                "no_provider_call": bool(usage_contract.get("no_provider_call", True)),
                "no_task_submission": bool(usage_contract.get("no_task_submission", True)),
                "no_download": bool(usage_contract.get("no_download", True)),
                "no_import": bool(usage_contract.get("no_import", True)),
                "no_editor_mutation": bool(usage_contract.get("no_editor_mutation", True)),
            },
        ))

    if work_order_template.get("completion_contract_schema"):
        template_name = str(work_order_template.get("display_name") or work_order_template.get("template_name") or "gameplay feature")
        required_evidence = bounded_string_preview(work_order_template.get("completion_required_evidence_preview", []), 8)
        proof_gates = bounded_string_preview(work_order_template.get("completion_proof_gate_preview", []), 8)
        stop_conditions = bounded_string_preview(work_order_template.get("completion_stop_before_complete_preview", []), 8)
        required = []
        required.extend(f"proof_gate:{gate}" for gate in proof_gates)
        required.extend(required_evidence)
        required.extend(f"stop_before_complete:{condition}" for condition in stop_conditions[:2])
        if not required:
            required = ["feature completion contract"]
        items.append(evidence_recording_item(
            item_id="record_feature_completion_contract",
            source="feature_completion_contract",
            phase_name=target_phase,
            evidence_type="feature_completion_contract",
            label=f"Record completion contract for {template_name}",
            required_artifacts=required[:10],
            state="recorded" if "feature_completion_contract" in existing_types else "pending",
            suggested_summary=(
                f"Record completion-contract proof for {template_name}: "
                f"{int(work_order_template.get('completion_proof_gate_count', 0) or 0)} proof gates, "
                f"{int(work_order_template.get('completion_required_evidence_count', 0) or 0)} required evidence artifacts."
            ),
            requires_bridge=False,
            metadata={
                "completion_contract_schema": work_order_template.get("completion_contract_schema", ""),
                "template_name": work_order_template.get("template_name", ""),
                "display_name": work_order_template.get("display_name", ""),
                "completion_proof_gate_count": int(work_order_template.get("completion_proof_gate_count", 0) or 0),
                "completion_required_evidence_count": int(work_order_template.get("completion_required_evidence_count", 0) or 0),
                "completion_stop_condition_count": int(work_order_template.get("completion_stop_condition_count", 0) or 0),
                "completion_proof_gate_preview": proof_gates,
                "completion_required_evidence_preview": required_evidence,
                "completion_stop_before_complete_preview": stop_conditions,
                "record_tool": "skill_record_ide_companion_evidence",
                "completion_allowed": False,
                "requires_all_proof_gates_before_complete": True,
                "requires_all_required_evidence_before_complete": True,
                "stop_before_complete_required": True,
                "no_auto_complete": True,
                "no_editor_mutation": True,
                "no_pie_run": True,
                "no_provider_call": True,
                "no_git_mutation": True,
            },
        ))

    if work_order_template.get("evidence_preview"):
        items.append(evidence_recording_item(
            item_id="record_feature_work_order_evidence",
            source="work_order_template",
            phase_name=target_phase,
            evidence_type="feature_work_order",
            label="Record feature work-order evidence",
            required_artifacts=bounded_string_preview(work_order_template.get("evidence_preview", []), 5),
            state="pending",
            suggested_summary="Record the feature-template compile/readback/runtime proof required by the work order.",
        ))

    pending_count = sum(1 for item in items if item.get("state") == "pending")
    blocked_count = sum(1 for item in items if item.get("state") == "blocked")
    recorded_count = sum(1 for item in items if item.get("state") == "recorded")
    return {
        "schema": "unreal_mcp_chat_evidence_recording_checklist.v1",
        "session_name": session_name,
        "target_phase": target_phase,
        "item_count": len(items),
        "pending_count": pending_count,
        "blocked_count": blocked_count,
        "recorded_count": recorded_count,
        "record_tool": "skill_record_ide_companion_evidence",
        "items": items,
        "network_required": False,
        "unreal_editor_required": any(item.get("requires_bridge") for item in items),
        "spend_required": False,
    }


def build_next_safe_step_gate(
    *,
    queues: List[Dict[str, Any]],
    blocking_gates: List[str],
    evidence_recording: Dict[str, Any],
    work_order_template: Dict[str, Any] | None = None,
    generated_animation_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    next_queue = queues[0] if queues else {}
    preview_actions = next_queue.get("preview_actions") if isinstance(next_queue.get("preview_actions"), list) else []
    next_action = preview_actions[0] if preview_actions and isinstance(preview_actions[0], dict) else {}
    bridge_blocked = "unreal_bridge_reachable" in set(blocking_gates) or bool(next_queue.get("bridge_blocked", False))
    missing_queue = not queues or not next_queue.get("next_action_tool")
    blockers = []
    if missing_queue:
        blockers.append("editor_queue_missing")
    if bridge_blocked:
        blockers.append("unreal_bridge_reachable")
    blockers.extend(str(gate) for gate in blocking_gates if str(gate).strip())
    blocking_gate_list = sorted({gate for gate in blockers if gate})
    can_execute_now = bool(next_queue.get("can_execute_now", False)) and not bridge_blocked and not missing_queue
    if can_execute_now:
        state = "ready"
    elif missing_queue and not blocking_gate_list:
        state = "empty"
    else:
        state = "blocked"

    evidence_items = evidence_recording.get("items") if isinstance(evidence_recording.get("items"), list) else []
    after_execution_evidence = [
        item for item in evidence_items
        if isinstance(item, dict) and item.get("source") in {"editor_queue", "runtime_verification", "repair_loop"}
    ][:3]
    replacement_gate = generated_asset_replacement_operation_gate_context(work_order_template or {})
    animation_prompt_gate = generated_animation_prompt_gate_context(work_order_template or {})
    animation_gate = generated_animation_operation_gate_context(generated_animation_context or {})
    return {
        "schema": "unreal_mcp_chat_next_safe_step_gate.v1",
        "state": state,
        "can_execute_now": can_execute_now,
        "queue_path": str(next_queue.get("queue_path", "")),
        "queue_name": str(next_queue.get("queue_name", "")),
        "target_phase": str(next_queue.get("target_phase", "")),
        "next_action_id": str(next_queue.get("next_action_id", "")),
        "next_action_tool": str(next_queue.get("next_action_tool", "")),
        "next_action_label": str(next_action.get("label", "") or next_action.get("id", "")),
        "argument_keys": next_action.get("argument_keys", []) if isinstance(next_action.get("argument_keys"), list) else [],
        "blocking_gates": blocking_gate_list,
        "requires_bridge": bool(next_queue.get("bridge_required", False)),
        "bridge_blocked": bridge_blocked,
        "after_execution_evidence": after_execution_evidence,
        "after_execution_evidence_count": len(after_execution_evidence),
        "execution_policy": [
            "Run only the next queued editor action.",
            "Stop immediately if bridge or readiness gates change.",
            "Record evidence before executing another queued action.",
            *replacement_gate.get("generated_asset_replacement_gate_policy", []),
            *animation_prompt_gate.get("generated_animation_prompt_gate_policy", []),
            *animation_gate.get("generated_animation_gate_policy", []),
        ],
        "pre_execution_checklist": [
            "Refresh cockpit overview immediately before execution.",
            "Confirm can_execute_now is true and blocking_gates is empty.",
            "Use only next_action_tool for next_action_id from queue_path.",
        ],
        "network_required": False,
        "unreal_editor_required": bool(next_queue.get("bridge_required", False)),
        "spend_required": False,
        **replacement_gate,
        **animation_prompt_gate,
        **animation_gate,
    }


def build_execution_review(
    *,
    next_safe_step: Dict[str, Any],
    evidence_recording: Dict[str, Any],
) -> Dict[str, Any]:
    evidence_items = evidence_recording.get("items") if isinstance(evidence_recording.get("items"), list) else []
    after_execution_rows = [
        item for item in next_safe_step.get("after_execution_evidence", [])
        if isinstance(item, dict)
    ]
    if not after_execution_rows:
        after_execution_rows = [
            item for item in evidence_items
            if isinstance(item, dict) and item.get("source") in {"editor_queue", "runtime_verification", "repair_loop"}
        ][:3]
    evidence_preview = [
        str(item.get("label") or item.get("evidence_type") or item.get("id", ""))
        for item in after_execution_rows
        if isinstance(item, dict)
    ]
    pre_execution_checklist = bounded_string_preview(next_safe_step.get("pre_execution_checklist", []), 5)
    post_execution_evidence_required = bounded_string_preview(evidence_preview, 5)
    target_action = {
        "action_id": str(next_safe_step.get("next_action_id", "")),
        "tool": str(next_safe_step.get("next_action_tool", "")),
        "label": str(next_safe_step.get("next_action_label", "")),
        "queue_path": str(next_safe_step.get("queue_path", "")),
        "queue_name": str(next_safe_step.get("queue_name", "")),
        "target_phase": str(next_safe_step.get("target_phase", "")),
        "argument_keys": next_safe_step.get("argument_keys", []) if isinstance(next_safe_step.get("argument_keys"), list) else [],
    }
    missing_gates = bounded_string_preview(next_safe_step.get("blocking_gates", []), 8)
    can_execute_now = bool(next_safe_step.get("can_execute_now", False))
    state = "ready" if can_execute_now else str(next_safe_step.get("state", "blocked") or "blocked")
    if state == "empty":
        missing_gates = ["editor_queue_missing"]
    return {
        "schema": "unreal_mcp_chat_execution_review.v1",
        "state": state,
        "can_execute_now": can_execute_now,
        "target_action": target_action,
        "requires_bridge": bool(next_safe_step.get("requires_bridge", False)),
        "bridge_blocked": bool(next_safe_step.get("bridge_blocked", False)),
        "missing_gates": missing_gates,
        "missing_gate_count": len(missing_gates),
        "after_execution_evidence_count": int(next_safe_step.get("after_execution_evidence_count", len(after_execution_rows)) or 0),
        "after_execution_evidence_preview": bounded_string_preview(evidence_preview, 5),
        "policy_preview": bounded_string_preview(next_safe_step.get("execution_policy", []), 5),
        "pre_execution_checklist": pre_execution_checklist,
        "post_execution_evidence_required": post_execution_evidence_required,
        "generated_asset_replacement_operation_count": int(
            next_safe_step.get("generated_asset_replacement_operation_count", 0) or 0
        ),
        "generated_asset_replacement_operation_preview": bounded_string_preview(
            next_safe_step.get("generated_asset_replacement_operation_preview", []),
            5,
        ),
        "generated_asset_replacement_tool_preview": bounded_string_preview(
            next_safe_step.get("generated_asset_replacement_tool_preview", []),
            8,
        ),
        "generated_asset_replacement_proof_contract_count": int(
            next_safe_step.get("generated_asset_replacement_proof_contract_count", 0) or 0
        ),
        "generated_asset_replacement_gate_policy": bounded_string_preview(
            next_safe_step.get("generated_asset_replacement_gate_policy", []),
            5,
        ),
        "generated_animation_prompt_count": int(next_safe_step.get("generated_animation_prompt_count", 0) or 0),
        "generated_animation_prompt_preview": bounded_string_preview(
            next_safe_step.get("generated_animation_prompt_preview", []),
            5,
        ),
        "generated_animation_provider_preview": bounded_string_preview(
            next_safe_step.get("generated_animation_provider_preview", []),
            5,
        ),
        "generated_animation_target_skeleton_preview": bounded_string_preview(
            next_safe_step.get("generated_animation_target_skeleton_preview", []),
            5,
        ),
        "generated_animation_tool_preview": bounded_string_preview(
            next_safe_step.get("generated_animation_tool_preview", []),
            8,
        ),
        "generated_animation_proof_required_preview": bounded_string_preview(
            next_safe_step.get("generated_animation_proof_required_preview", []),
            8,
        ),
        "generated_animation_prompt_gate_policy": bounded_string_preview(
            next_safe_step.get("generated_animation_prompt_gate_policy", []),
            5,
        ),
        "estimated_uthana_motion_seconds": int(next_safe_step.get("estimated_uthana_motion_seconds", 0) or 0),
        "generated_animation_asset_count": int(next_safe_step.get("generated_animation_asset_count", 0) or 0),
        "generated_animation_pending_count": int(next_safe_step.get("generated_animation_pending_count", 0) or 0),
        "generated_animation_target_name": str(next_safe_step.get("generated_animation_target_name", "")),
        "generated_animation_target_provider": str(next_safe_step.get("generated_animation_target_provider", "")),
        "generated_animation_target_task_status": str(next_safe_step.get("generated_animation_target_task_status", "")),
        "generated_animation_target_motion_id": str(next_safe_step.get("generated_animation_target_motion_id", "")),
        "generated_animation_target_skeleton": str(next_safe_step.get("generated_animation_target_skeleton", "")),
        "generated_animation_quality_proof_contract_schema": str(
            next_safe_step.get("generated_animation_quality_proof_contract_schema", "")
        ),
        "generated_animation_quality_evidence_missing_count": int(
            next_safe_step.get("generated_animation_quality_evidence_missing_count", 0) or 0
        ),
        "generated_animation_missing_stage_preview": bounded_string_preview(
            next_safe_step.get("generated_animation_missing_stage_preview", []),
            8,
        ),
        "generated_animation_next_safe_action_id": str(next_safe_step.get("generated_animation_next_safe_action_id", "")),
        "generated_animation_next_safe_tool": str(next_safe_step.get("generated_animation_next_safe_tool", "")),
        "generated_animation_usage_contract_schema": str(next_safe_step.get("generated_animation_usage_contract_schema", "")),
        "generated_animation_usage_receipt_path": str(next_safe_step.get("generated_animation_usage_receipt_path", "")),
        "generated_animation_usage_confirmation_field": str(next_safe_step.get("generated_animation_usage_confirmation_field", "")),
        "generated_animation_allowance_tool_preview": bounded_string_preview(
            next_safe_step.get("generated_animation_allowance_tool_preview", []),
            4,
        ),
        "generated_animation_allowance_review_steps": bounded_string_preview(
            next_safe_step.get("generated_animation_allowance_review_steps", []),
            5,
        ),
        "generated_animation_gate_policy": bounded_string_preview(
            next_safe_step.get("generated_animation_gate_policy", []),
            5,
        ),
        "executor_contract": [
            "Execute exactly one queued editor action.",
            "Stop after the action even if more queue entries remain.",
            "Record post-execution evidence before continuing the queue.",
        ],
        "stop_after_action": True,
        "review_tool": "chat_get_cockpit_overview",
        "evidence_tool": "skill_record_ide_companion_evidence",
        "network_required": False,
        "unreal_editor_required": bool(next_safe_step.get("requires_bridge", False)),
        "spend_required": False,
    }


def build_repair_review(
    *,
    repair_loop: Dict[str, Any],
    failure_triage: Dict[str, Any],
    target_phase: str,
) -> Dict[str, Any]:
    repair_items = repair_loop.get("items") if isinstance(repair_loop.get("items"), list) else []
    target_repair = select_repair_context(repair_loop, target_phase or "repair")
    failure_items = failure_triage.get("items") if isinstance(failure_triage.get("items"), list) else []
    failure_preview = [
        str(item.get("label") or item.get("id", ""))
        for item in failure_items
        if isinstance(item, dict)
    ]
    available = bool(repair_loop.get("available")) and bool(repair_items)
    bridge_blocked = bool(repair_loop.get("bridge_blocked", False))
    state = "blocked" if bridge_blocked else ("ready" if available else "missing")
    can_compile_repair_work_order = available
    can_apply_repair_now = bool(available and not bridge_blocked)
    repair_execution_readiness = {
        "schema": "unreal_mcp_chat_repair_execution_readiness.v1",
        "state": "ready_to_apply" if can_apply_repair_now else ("ready_to_plan" if can_compile_repair_work_order else "missing"),
        "can_compile_repair_work_order": can_compile_repair_work_order,
        "can_apply_repair_now": can_apply_repair_now,
        "can_record_repair_evidence": False,
        "target_repair_id": str(target_repair.get("id", "")),
        "target_phase": str(target_repair.get("target_phase") or target_phase or "repair"),
        "requires_bridge_before_apply": bool(target_repair.get("requires_bridge", True)) if target_repair else bool(repair_loop.get("unreal_editor_required", False)),
        "bridge_blocked": bridge_blocked,
        "missing_gate_preview": ["unreal_bridge_reachable"] if bridge_blocked else [],
        "required_before_plan_preview": [
            "target_repair_selected",
            "failure_signal_reviewed",
            "repair_work_order_scope_defined",
        ],
        "required_before_apply_preview": [
            "unreal_bridge_reachable",
            "blueprint_pre_read_evidence",
            "repair_work_order_reviewed",
        ],
        "required_after_apply_preview": [
            "repair_work_order_result",
            "blueprint_compile_report",
            "graph_or_component_readback",
            "ide_companion_ledger_event",
        ],
        "stop_if_missing_preview": [
            "bridge ping failed",
            "repair work order is not scoped",
            "compile report missing or failed",
            "readback still shows the failure",
            "repair evidence is not recorded",
        ],
        "recommended_next": (
            "resolve_bridge_before_apply" if bridge_blocked and available else (
                "compile_repair_work_order" if available else "review_failure_triage"
            )
        ),
        "planning_tool": str(repair_loop.get("recommended_tool", "skill_compile_ide_companion_work_order")),
        "evidence_tool": str(repair_loop.get("evidence_tool", "skill_record_ide_companion_evidence")),
        "review_tool": "chat_get_cockpit_overview",
        "no_editor_mutation": True,
        "stop_before_editor_mutation": True,
        "stop_after_repair_attempt": True,
    }
    return {
        "schema": "unreal_mcp_chat_repair_review.v1",
        "state": state,
        "available": available,
        "target_repair": target_repair,
        "target_phase": str(target_repair.get("target_phase") or target_phase or "repair"),
        "requires_bridge": bool(target_repair.get("requires_bridge", True)) if target_repair else bool(repair_loop.get("unreal_editor_required", False)),
        "bridge_blocked": bridge_blocked,
        "failure_signal_count": int(failure_triage.get("item_count", len(failure_items)) or 0),
        "failure_signal_preview": bounded_string_preview(failure_preview, 5),
        "blocked_count": int(failure_triage.get("blocked_count", 0) or 0),
        "needs_repair_count": int(failure_triage.get("needs_repair_count", 0) or 0),
        "repair_instruction_count": int(repair_loop.get("repair_instruction_count", len(repair_items)) or 0),
        "stop_condition_count": int(repair_loop.get("stop_condition_count", 0) or 0),
        "compile_check_preview": bounded_string_preview(repair_loop.get("compile_check_preview", []), 4),
        "evidence_preview": bounded_string_preview(repair_loop.get("evidence_preview", []), 5),
        "policy_preview": [
            "Compile a scoped repair work order from the selected repair hint.",
            "Apply at most one repair attempt before re-checking compile/readback evidence.",
            "Stop if bridge, readiness, or Blueprint mutation gates are blocked.",
            "Record repair evidence before continuing the queue.",
        ],
        "repair_execution_readiness": repair_execution_readiness,
        "repair_execution_readiness_state": repair_execution_readiness["state"],
        "can_compile_repair_work_order": repair_execution_readiness["can_compile_repair_work_order"],
        "can_apply_repair_now": repair_execution_readiness["can_apply_repair_now"],
        "repair_recommended_next": repair_execution_readiness["recommended_next"],
        "recommended_tool": str(repair_loop.get("recommended_tool", "skill_compile_ide_companion_work_order")),
        "evidence_tool": str(repair_loop.get("evidence_tool", "skill_record_ide_companion_evidence")),
        "stop_after_repair_attempt": True,
        "review_tool": "chat_get_cockpit_overview",
        "network_required": False,
        "unreal_editor_required": bool(repair_loop.get("unreal_editor_required", False)),
        "spend_required": False,
    }


def build_failure_triage_summary(
    *,
    ledger: Dict[str, Any],
    next_safe_step: Dict[str, Any],
    runtime_verification: Dict[str, Any],
    repair_loop: Dict[str, Any],
    blocker_resolutions: Dict[str, Any],
) -> Dict[str, Any]:
    failure_terms = ("failed", "failure", "error", "exception")
    failure_types = {"failure", "error", "compile_error", "tool_error", "repair"}
    items: List[Dict[str, Any]] = []

    preview_events = ledger.get("preview_events") if isinstance(ledger.get("preview_events"), list) else []
    for event in preview_events:
        if not isinstance(event, dict):
            continue
        evidence_type = str(event.get("evidence_type", "")).lower()
        summary = str(event.get("summary", ""))
        summary_lower = summary.lower()
        if evidence_type not in failure_types and not any(term in summary_lower for term in failure_terms):
            continue
        items.append({
            "id": f"ledger_event_{event.get('index', len(items) + 1)}",
            "source": "evidence_timeline",
            "phase_name": str(event.get("phase_name", "")),
            "label": summary or "Failure event recorded in ledger.",
            "state": "needs_repair",
            "recommended_tool": "skill_compile_ide_companion_work_order",
            "evidence_tool": "skill_record_ide_companion_evidence",
            "artifact_preview": bounded_string_preview(event.get("artifact_preview", []), 3),
        })

    if next_safe_step.get("state") == "blocked":
        blocking_gates = bounded_string_preview(next_safe_step.get("blocking_gates", []), 5)
        recommended_tool = (
            "gen_compile_ide_companion_readiness"
            if "unreal_bridge_reachable" in set(blocking_gates)
            else "skill_compile_ide_companion_blocker_resolution"
        )
        items.append({
            "id": "next_safe_step_blocked",
            "source": "next_safe_step",
            "phase_name": str(next_safe_step.get("target_phase", "")),
            "label": "Next queued editor action is blocked before execution.",
            "state": "blocked",
            "recommended_tool": recommended_tool,
            "evidence_tool": "skill_record_ide_companion_evidence",
            "artifact_preview": blocking_gates,
        })

    if runtime_verification.get("available") and runtime_verification.get("state") == "blocked":
        items.append({
            "id": "runtime_verification_blocked",
            "source": "runtime_verification",
            "phase_name": str(runtime_verification.get("target_phase", "")),
            "label": "Runtime verification is blocked before PIE proof can be captured.",
            "state": "blocked",
            "recommended_tool": "gen_compile_ide_companion_readiness",
            "evidence_tool": "skill_record_ide_companion_evidence",
            "artifact_preview": bounded_string_preview(runtime_verification.get("compile_check_preview", []), 3),
        })

    repair_items = repair_loop.get("items") if isinstance(repair_loop.get("items"), list) else []
    if repair_loop.get("available") and repair_items:
        first_repair = repair_items[0] if isinstance(repair_items[0], dict) else {}
        items.append({
            "id": "repair_loop_next_hint",
            "source": "repair_loop",
            "phase_name": str(runtime_verification.get("target_phase", "")),
            "label": str(first_repair.get("label", "Compile a bounded repair work order.")),
            "state": str(first_repair.get("state", repair_loop.get("state", "pending"))),
            "recommended_tool": str(repair_loop.get("recommended_tool", "skill_compile_ide_companion_work_order")),
            "evidence_tool": str(repair_loop.get("evidence_tool", "skill_record_ide_companion_evidence")),
            "artifact_preview": bounded_string_preview(repair_loop.get("evidence_preview", []), 3),
        })

    bounded_items = items[:5]
    blocked_count = sum(1 for item in bounded_items if item.get("state") == "blocked")
    needs_repair_count = sum(1 for item in bounded_items if item.get("state") == "needs_repair")
    recommended_tools = []
    for item in bounded_items:
        tool = str(item.get("recommended_tool", ""))
        if tool and tool not in recommended_tools:
            recommended_tools.append(tool)
    if not recommended_tools and blocker_resolutions.get("recommended_tools"):
        recommended_tools = bounded_string_preview(blocker_resolutions.get("recommended_tools", []), 3)
    return {
        "schema": "unreal_mcp_chat_failure_triage_summary.v1",
        "state": "needs_repair" if needs_repair_count else ("blocked" if blocked_count else ("clear" if not bounded_items else "ready")),
        "item_count": len(bounded_items),
        "blocked_count": blocked_count,
        "needs_repair_count": needs_repair_count,
        "recommended_tools": recommended_tools,
        "evidence_tool": "skill_record_ide_companion_evidence",
        "items": bounded_items,
        "network_required": False,
        "unreal_editor_required": any(item.get("state") in {"blocked", "ready"} for item in bounded_items),
        "spend_required": False,
    }


def build_generated_asset_quality_gate_summary(
    asset_lifecycles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    items: List[Dict[str, Any]] = []
    for lifecycle in asset_lifecycles[:5]:
        if not isinstance(lifecycle, dict):
            continue
        manifest_path = str(lifecycle.get("manifest_path", ""))
        preview_assets = lifecycle.get("preview_assets") if isinstance(lifecycle.get("preview_assets"), list) else []
        for asset in preview_assets:
            if not isinstance(asset, dict) or len(items) >= 8:
                continue
            task_status = str(asset.get("task_status") or "not_submitted")
            imported_path = str(asset.get("imported_asset_path", ""))
            expected_path = str(asset.get("expected_import_path", ""))
            quality_gate_count = int(asset.get("quality_gate_count", 0) or 0)
            quality_evidence_count = int(asset.get("quality_evidence_count", 0) or 0)
            if task_status in {"not_submitted", "blocked", "failed"}:
                state = "provider_pending"
                next_gate = "provider task must complete before import"
            elif not imported_path:
                state = "import_pending"
                next_gate = "download/import result is missing"
            elif quality_gate_count and quality_evidence_count < quality_gate_count:
                state = "quality_pending"
                next_gate = "material/collision/viewport/ledger proof is missing"
            else:
                state = "ready"
                next_gate = "quality gates have recorded evidence"
            items.append({
                "id": str(asset.get("id", "")) or f"asset_quality_{len(items) + 1}",
                "name": str(asset.get("name", "")),
                "role": str(asset.get("role", "")),
                "provider": str(asset.get("provider", "")),
                "state": state,
                "task_status": task_status,
                "expected_import_path": expected_path,
                "imported_asset_path": imported_path,
                "has_placeholder": bool(asset.get("has_placeholder", False)),
                "quality_gate_count": quality_gate_count,
                "quality_gate_preview": bounded_string_preview(asset.get("quality_gate_preview", []), 4),
                "quality_evidence_count": quality_evidence_count,
                "quality_proof_contract_schema": str(asset.get("quality_proof_contract_schema", "")),
                "quality_proof_required_count": int(asset.get("quality_proof_required_count", 0) or 0),
                "quality_proof_required_preview": bounded_string_preview(asset.get("quality_proof_required_preview", []), 8),
                "next_gate": next_gate,
                "manifest_path": manifest_path,
            })

    provider_pending_count = sum(1 for item in items if item.get("state") == "provider_pending")
    import_pending_count = sum(1 for item in items if item.get("state") == "import_pending")
    quality_pending_count = sum(1 for item in items if item.get("state") == "quality_pending")
    ready_count = sum(1 for item in items if item.get("state") == "ready")
    blocked_count = provider_pending_count + import_pending_count + quality_pending_count
    state = "blocked" if blocked_count else ("ready" if ready_count else "missing")
    return {
        "schema": "unreal_mcp_chat_generated_asset_quality_gate.v1",
        "state": state,
        "asset_count": len(items),
        "provider_pending_count": provider_pending_count,
        "import_pending_count": import_pending_count,
        "quality_pending_count": quality_pending_count,
        "ready_count": ready_count,
        "placeholder_count": sum(1 for item in items if item.get("has_placeholder")),
        "items": items[:5],
        "recommended_tools": [
            "skill_compile_ide_companion_asset_lifecycle_manifest",
            "skill_record_ide_companion_evidence",
        ],
        "network_required": any(lifecycle.get("future_provider_network_required") for lifecycle in asset_lifecycles),
        "unreal_editor_required": bool(items),
        "spend_required": any(lifecycle.get("future_spend_required") for lifecycle in asset_lifecycles),
    }


def ledger_summary(path: Path) -> Optional[Dict[str, Any]]:
    payload = read_ledger_payload(path)
    if payload is None:
        return None

    events = payload.get("events") if isinstance(payload.get("events"), list) else []
    latest_event = events[-1] if events and isinstance(events[-1], dict) else {}
    recent_events = []
    recent_start = max(0, len(events) - 5)
    for index, event in enumerate(events[recent_start:], start=recent_start + 1):
        if not isinstance(event, dict):
            continue
        artifacts = event.get("artifacts") if isinstance(event.get("artifacts"), list) else []
        artifact_preview = [str(artifact) for artifact in artifacts[:3]]
        recent_events.append({
            "index": index,
            "phase_name": str(event.get("phase_name", "")),
            "evidence_type": str(event.get("evidence_type", "")),
            "summary": str(event.get("summary", "")),
            "artifact_count": len(artifacts),
            "artifact_preview": artifact_preview,
            "timestamp_unix": event.get("timestamp_unix", 0),
        })
    latest_status = payload.get("latest_status") if isinstance(payload.get("latest_status"), dict) else {}
    latest_work_order = payload.get("latest_work_order") if isinstance(payload.get("latest_work_order"), dict) else {}
    session_plan = payload.get("session_plan") if isinstance(payload.get("session_plan"), dict) else {}
    session_plan_phases = session_plan.get("phases") if isinstance(session_plan.get("phases"), list) else []
    generated_asset_prompts = session_plan.get("generated_asset_prompts") if isinstance(session_plan.get("generated_asset_prompts"), list) else []
    generated_animation_prompts = session_plan.get("generated_animation_prompts") if isinstance(session_plan.get("generated_animation_prompts"), list) else []
    template_summary = work_order_template_summary(latest_work_order)
    return {
        "session_name": str(payload.get("session_name") or path.stem),
        "ledger_path": relative_repo_path(path),
        "event_count": len(events),
        "latest_phase": str(latest_event.get("phase_name", "")),
        "latest_summary": str(latest_event.get("summary", "")),
        "preview_events": recent_events,
        "completed_phase_count": latest_status.get("completed_phase_count", 0),
        "blocking_gates": latest_status.get("blocking_gates", []),
        "next_phase": latest_status.get("next_phase", ""),
        "next_tool": (latest_status.get("next_action") or {}).get("tool", ""),
        "work_order_phase": latest_work_order.get("target_phase", ""),
        "work_order_template": template_summary,
        "has_session_plan": bool(session_plan),
        "session_plan_phase_count": len(session_plan_phases),
        "generated_asset_prompt_count": len(generated_asset_prompts),
        "generated_animation_prompt_count": len(generated_animation_prompts),
        "estimated_uthana_motion_seconds": int(session_plan.get("estimated_uthana_motion_seconds", 0) or 0),
        "has_status_receipt": bool(latest_status),
    }


def editor_queue_summary(path: Path) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("schema") != "unreal_mcp_ide_companion_editor_queue.v1":
        return None

    actions = payload.get("actions") if isinstance(payload.get("actions"), list) else []
    next_action = actions[0] if actions and isinstance(actions[0], dict) else {}
    preview_actions = []
    for index, action in enumerate(actions[:5], start=1):
        if not isinstance(action, dict):
            continue
        arguments = action.get("arguments") if isinstance(action.get("arguments"), dict) else {}
        if not arguments:
            arguments = action.get("params") if isinstance(action.get("params"), dict) else {}
        argument_keys = sorted(str(key) for key in arguments.keys())[:8]
        preview_actions.append({
            "index": index,
            "id": str(action.get("id", "")),
            "tool": str(action.get("tool", "")),
            "label": str(action.get("label", "") or action.get("summary", "")),
            "argument_keys": argument_keys,
        })
    blocking_gates = payload.get("blocking_gates") if isinstance(payload.get("blocking_gates"), list) else []
    evidence_to_collect = payload.get("evidence_to_collect") if isinstance(payload.get("evidence_to_collect"), list) else []
    feature_template = payload.get("feature_template") if isinstance(payload.get("feature_template"), dict) else {}
    return {
        "session_name": str(payload.get("session_name") or path.stem),
        "queue_name": str(payload.get("queue_name") or path.stem),
        "queue_path": relative_repo_path(path),
        "target_phase": str(payload.get("target_phase", "")),
        "source": str(payload.get("source", "")),
        "action_count": len(actions),
        "next_action_id": str(next_action.get("id", "")),
        "next_action_tool": str(next_action.get("tool", "")),
        "feature_template_schema": str(feature_template.get("schema", "")),
        "feature_template_name": str(feature_template.get("template_name", "")),
        "feature_template_display_name": str(feature_template.get("display_name", "")),
        "feature_template_operation_count": int(feature_template.get("editor_operation_count", 0) or 0),
        "feature_template_next_operation_id": str(feature_template.get("next_operation_id", "")),
        "feature_template_next_operation_type": str(feature_template.get("next_operation_type", "")),
        "feature_template_next_operation_summary": str(feature_template.get("next_operation_summary", "")),
        "feature_template_next_operation_tool_preview": bounded_string_preview(
            feature_template.get("next_operation_tool_candidates", []),
            8,
        ),
        "feature_template_next_operation_required_before_preview": bounded_string_preview(
            feature_template.get("next_operation_required_before", []),
            8,
        ),
        "feature_template_next_operation_required_after_preview": bounded_string_preview(
            feature_template.get("next_operation_required_after", []),
            8,
        ),
        "feature_template_next_operation_stop_if_missing_preview": bounded_string_preview(
            feature_template.get("next_operation_stop_if_missing", []),
            8,
        ),
        "preview_actions": preview_actions,
        "blocking_gates": blocking_gates,
        "bridge_required": bool(payload.get("bridge_required", payload.get("unreal_editor_required", False))),
        "bridge_blocked": bool(payload.get("bridge_blocked", False)),
        "can_execute_now": bool(payload.get("can_execute_now", False)),
        "evidence_count": len(evidence_to_collect),
        "evidence_preview": bounded_string_preview(evidence_to_collect),
    }


def asset_lifecycle_summary(path: Path) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("schema") != "unreal_mcp_ide_companion_generated_asset_lifecycle.v1":
        return None

    assets = payload.get("assets") if isinstance(payload.get("assets"), list) else []
    animation_assets = payload.get("animation_assets") if isinstance(payload.get("animation_assets"), list) else []
    preview_assets = []
    preview_animation_assets = []
    blocked_count = 0
    animation_pending_count = 0
    placeholder_count = 0
    for index, asset in enumerate(assets, start=1):
        if not isinstance(asset, dict):
            continue
        provider_task = asset.get("provider_task") if isinstance(asset.get("provider_task"), dict) else {}
        placeholder = asset.get("placeholder_replacement") if isinstance(asset.get("placeholder_replacement"), dict) else {}
        status = str(provider_task.get("status") or "not_submitted")
        quality_gates = asset.get("quality_gates") if isinstance(asset.get("quality_gates"), list) else [
            "mesh loads in Unreal",
            "material slots are reported",
            "collision/readability check is recorded",
            "viewport thumbnail or screenshot proof exists",
            "IDE companion ledger records import and replacement evidence",
        ]
        quality_evidence = asset.get("quality_evidence") if isinstance(asset.get("quality_evidence"), list) else []
        quality_contract = asset.get("quality_proof_contract") if isinstance(asset.get("quality_proof_contract"), dict) else {}
        required_after_import = (
            quality_contract.get("required_after_import")
            if isinstance(quality_contract.get("required_after_import"), list)
            else []
        )
        downloaded_asset_path = str(
            asset.get("downloaded_asset_path")
            or asset.get("download_path")
            or provider_task.get("downloaded_asset_path")
            or provider_task.get("download_path")
            or provider_task.get("downloaded_model_path")
            or ""
        )
        imported_asset_path = str(
            asset.get("imported_asset_path")
            or provider_task.get("imported_asset_path")
            or provider_task.get("import_path")
            or ""
        )
        if status in {"not_submitted", "blocked", "failed"}:
            blocked_count += 1
        if placeholder.get("has_placeholder"):
            placeholder_count += 1
        if index <= 5:
            preview_assets.append({
                "index": index,
                "id": str(asset.get("id", "")),
                "name": str(asset.get("name", "")),
                "role": str(asset.get("role", "")),
                "provider": str(asset.get("provider", "")),
                "task_status": status,
                "task_id": str(provider_task.get("task_id", "")),
                "submit_tool": str(provider_task.get("submit_tool", "")),
                "planned_submit_tool": str(provider_task.get("planned_submit_tool", provider_task.get("submit_tool", ""))),
                "status_tool": str(provider_task.get("status_tool", "")),
                "download_tool": str(provider_task.get("download_tool", "")),
                "import_tool": str(provider_task.get("import_tool", "")),
                "public_mcp_tool_available": bool(provider_task.get("public_mcp_tool_available", True)),
                "unsupported_reason": str(provider_task.get("unsupported_reason", "")),
                "expected_import_path": str(asset.get("expected_import_path", "")),
                "downloaded_asset_path": downloaded_asset_path,
                "imported_asset_path": imported_asset_path,
                "has_placeholder": bool(placeholder.get("has_placeholder", False)),
                "placeholder_asset_path": str(placeholder.get("placeholder_asset_path", "")),
                "replacement_policy_preview": bounded_string_preview(placeholder.get("replacement_policy", []), 5),
                "quality_gate_count": len(quality_gates),
                "quality_gate_preview": bounded_string_preview(quality_gates, 5),
                "quality_evidence_count": len(quality_evidence),
                "quality_proof_contract_schema": str(quality_contract.get("schema", "")),
                "quality_proof_required_count": len(required_after_import),
                "quality_proof_required_preview": bounded_string_preview(required_after_import, 8),
            })

    for index, animation in enumerate(animation_assets, start=1):
        if not isinstance(animation, dict):
            continue
        provider_task = animation.get("provider_task") if isinstance(animation.get("provider_task"), dict) else {}
        status = str(provider_task.get("status") or "not_submitted")
        if status not in {"success", "final", "complete", "completed"}:
            animation_pending_count += 1
        quality_gates = animation.get("quality_gates") if isinstance(animation.get("quality_gates"), list) else []
        quality_evidence = animation.get("quality_evidence") if isinstance(animation.get("quality_evidence"), list) else []
        quality_contract = animation.get("quality_proof_contract") if isinstance(animation.get("quality_proof_contract"), dict) else {}
        required_after_import = (
            quality_contract.get("required_after_import")
            if isinstance(quality_contract.get("required_after_import"), list)
            else []
        )
        if index <= 5:
            preview_animation_assets.append({
                "index": index,
                "id": str(animation.get("id", "")),
                "name": str(animation.get("name", "")),
                "role": str(animation.get("role", "")),
                "provider": str(animation.get("provider", "")),
                "task_type": str(animation.get("task_type", "")),
                "source_video_file": str(animation.get("video_file") or animation.get("reference_video_file") or animation.get("source_video_file") or ""),
                "video_reference_required": str(animation.get("task_type", "")) == "video_to_motion",
                "video_reference_provided": bool(str(animation.get("video_file") or animation.get("reference_video_file") or animation.get("source_video_file") or "")),
                "task_status": status,
                "motion_id": str(provider_task.get("motion_id", "")),
                "submit_tool": str(provider_task.get("submit_tool", "")),
                "planned_submit_tool": str(provider_task.get("planned_submit_tool", provider_task.get("submit_tool", ""))),
                "status_tool": str(provider_task.get("status_tool", "")),
                "download_tool": str(provider_task.get("download_tool", "")),
                "import_tool": str(provider_task.get("import_tool", "")),
                "public_mcp_tool_available": bool(provider_task.get("public_mcp_tool_available", True)),
                "unsupported_reason": str(provider_task.get("unsupported_reason", "")),
                "expected_import_path": str(animation.get("expected_import_path", "")),
                "target_skeleton": str(animation.get("target_skeleton", "")),
                "format": str(animation.get("format", "")),
                "estimated_seconds": int(animation.get("estimated_seconds", 0) or 0),
                "default_character_id": str(animation.get("default_character_id", "")),
                "quality_gate_count": len(quality_gates),
                "quality_gate_preview": bounded_string_preview(quality_gates, 5),
                "quality_evidence_count": len(quality_evidence),
                "quality_proof_contract_schema": str(quality_contract.get("schema", "")),
                "quality_proof_required_count": len(required_after_import),
                "quality_proof_required_preview": bounded_string_preview(required_after_import, 8),
            })

    stop_conditions = payload.get("stop_conditions") if isinstance(payload.get("stop_conditions"), list) else []
    unsupported_provider_tasks = (
        payload.get("unsupported_provider_task_preview")
        if isinstance(payload.get("unsupported_provider_task_preview"), list)
        else []
    )
    return {
        "session_name": str(payload.get("session_name") or path.stem),
        "manifest_path": relative_repo_path(path),
        "preferred_provider": str(payload.get("preferred_provider", "")),
        "asset_count": int(payload.get("asset_count", len(assets)) or 0),
        "preview_assets": preview_assets,
        "preview_asset_count": len(preview_assets),
        "animation_asset_count": int(payload.get("animation_asset_count", len(animation_assets)) or 0),
        "preview_animation_assets": preview_animation_assets,
        "preview_animation_asset_count": len(preview_animation_assets),
        "animation_pending_count": animation_pending_count,
        "placeholder_count": placeholder_count,
        "blocked_or_pending_count": blocked_count,
        "unsupported_provider_task_count": int(payload.get("unsupported_provider_task_count", len(unsupported_provider_tasks)) or 0),
        "unsupported_provider_task_preview": unsupported_provider_tasks[:5],
        "future_provider_network_required": bool(payload.get("future_provider_network_required", False)),
        "future_spend_required": bool(payload.get("future_spend_required", False)),
        "stop_condition_count": len(stop_conditions),
    }


def list_ide_companion_ledgers(
    limit: int = 50,
    *,
    session_dir: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    base = Path(session_dir) if session_dir else DEFAULT_IDE_COMPANION_SESSION_DIR
    if not base.exists():
        return []
    summaries = [
        summary
        for summary in (ledger_summary(path) for path in base.glob("*.json"))
        if summary is not None
    ]
    summaries.sort(key=lambda item: (str(item.get("session_name", "")).lower(), str(item.get("ledger_path", ""))))
    return summaries[: max(1, min(int(limit or 50), 200))]


def list_editor_queues(
    limit: int = 50,
    *,
    session_dir: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    base = Path(session_dir) if session_dir else DEFAULT_IDE_COMPANION_SESSION_DIR
    if not base.exists():
        return []
    summaries = [
        summary
        for summary in (editor_queue_summary(path) for path in base.glob("*.json"))
        if summary is not None
    ]
    summaries.sort(key=lambda item: (str(item.get("session_name", "")).lower(), str(item.get("queue_name", "")).lower()))
    return summaries[: max(1, min(int(limit or 50), 200))]


def list_asset_lifecycle_manifests(
    limit: int = 50,
    *,
    session_dir: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    base = Path(session_dir) if session_dir else DEFAULT_IDE_COMPANION_SESSION_DIR
    if not base.exists():
        return []
    summaries = [
        summary
        for summary in (asset_lifecycle_summary(path) for path in base.glob("*.json"))
        if summary is not None
    ]
    summaries.sort(key=lambda item: (str(item.get("session_name", "")).lower(), str(item.get("manifest_path", ""))))
    return summaries[: max(1, min(int(limit or 50), 200))]


def find_matching_ledger(
    session_name: str,
    *,
    session_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    base = Path(session_dir) if session_dir else DEFAULT_IDE_COMPANION_SESSION_DIR
    safe = safe_artifact_name(session_name)
    candidates = [
        base / f"{safe}.json",
        base / f"{safe}_ledger.json",
        base / f"{safe}_live_ledger.json",
    ]
    for path in candidates:
        summary = ledger_summary(path)
        if summary is not None:
            return summary

    session_lower = str(session_name or "").lower()
    for summary in list_ide_companion_ledgers(limit=200, session_dir=base):
        if str(summary.get("session_name", "")).lower() == session_lower:
            return summary
    return {}


def resolve_ledger_path(
    ledger_path: str = "",
    *,
    session_name: str = "",
    session_dir: Optional[Path | str] = None,
) -> Optional[Path]:
    base = Path(session_dir) if session_dir else DEFAULT_IDE_COMPANION_SESSION_DIR
    candidates: List[Path] = []
    if ledger_path:
        raw_path = Path(ledger_path)
        if raw_path.is_absolute():
            candidates.append(raw_path)
        else:
            candidates.extend([
                base / raw_path,
                base / raw_path.name,
                _REPO_ROOT / raw_path,
            ])
    else:
        safe = safe_artifact_name(session_name)
        candidates.extend([
            base / f"{safe}.json",
            base / f"{safe}_ledger.json",
            base / f"{safe}_live_ledger.json",
        ])

    seen = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if str(resolved) in seen:
            continue
        seen.add(str(resolved))
        if resolved.exists() and resolved.is_relative_to(base.resolve()):
            return resolved
    return None


def find_matching_queues(
    session_name: str,
    *,
    session_dir: Optional[Path | str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    session_lower = str(session_name or "").lower()
    safe = safe_artifact_name(session_name).lower()
    matches = []
    for summary in list_editor_queues(limit=200, session_dir=session_dir):
        summary_session = str(summary.get("session_name", "")).lower()
        queue_path = str(summary.get("queue_path", "")).lower()
        if summary_session == session_lower or summary_session == safe or f"{safe}_" in queue_path:
            matches.append(summary)
    return matches[: max(1, min(int(limit or 20), 100))]


def find_matching_asset_lifecycles(
    session_name: str,
    *,
    session_dir: Optional[Path | str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    session_lower = str(session_name or "").lower()
    safe = safe_artifact_name(session_name).lower()
    matches = []
    for summary in list_asset_lifecycle_manifests(limit=200, session_dir=session_dir):
        summary_session = str(summary.get("session_name", "")).lower()
        manifest_path = str(summary.get("manifest_path", "")).lower()
        if summary_session == session_lower or summary_session == safe or f"{safe}_" in manifest_path:
            matches.append(summary)
    return matches[: max(1, min(int(limit or 20), 100))]


def build_ide_companion_session_picker(
    *,
    selected_session: str = "",
    limit: int = 50,
    session_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    safe_limit = max(1, min(int(limit or 50), 200))
    ledgers = list_ide_companion_ledgers(limit=200, session_dir=session_dir)
    queues = list_editor_queues(limit=200, session_dir=session_dir)
    lifecycles = list_asset_lifecycle_manifests(limit=200, session_dir=session_dir)
    rows: Dict[str, Dict[str, Any]] = {}

    def row_for(name: str) -> Dict[str, Any]:
        session_name = str(name or "ide-companion")
        key = session_name.lower()
        return rows.setdefault(key, {
            "session_name": session_name,
            "selected": False,
            "has_ledger": False,
            "ledger_path": "",
            "latest_phase": "",
            "latest_summary": "",
            "next_phase": "",
            "work_order_phase": "",
            "event_count": 0,
            "completed_phase_count": 0,
            "queue_count": 0,
            "queued_action_count": 0,
            "can_execute_now": False,
            "generated_manifest_count": 0,
            "generated_asset_count": 0,
            "generated_pending_count": 0,
            "placeholder_mapping_count": 0,
            "blocking_gates": [],
        })

    for ledger in ledgers:
        row = row_for(str(ledger.get("session_name", "")))
        row.update({
            "has_ledger": True,
            "ledger_path": str(ledger.get("ledger_path", "")),
            "latest_phase": str(ledger.get("latest_phase", "")),
            "latest_summary": str(ledger.get("latest_summary", "")),
            "next_phase": str(ledger.get("next_phase", "")),
            "work_order_phase": str(ledger.get("work_order_phase", "")),
            "event_count": int(ledger.get("event_count", 0) or 0),
            "completed_phase_count": int(ledger.get("completed_phase_count", 0) or 0),
        })
        gates = set(row.get("blocking_gates", []))
        gates.update(str(gate) for gate in ledger.get("blocking_gates", []) if str(gate).strip())
        row["blocking_gates"] = sorted(gates)

    for queue in queues:
        row = row_for(str(queue.get("session_name", "")))
        row["queue_count"] = int(row.get("queue_count", 0) or 0) + 1
        row["queued_action_count"] = int(row.get("queued_action_count", 0) or 0) + int(queue.get("action_count", 0) or 0)
        row["can_execute_now"] = bool(row.get("can_execute_now", False) or queue.get("can_execute_now", False))
        gates = set(row.get("blocking_gates", []))
        gates.update(str(gate) for gate in queue.get("blocking_gates", []) if str(gate).strip())
        row["blocking_gates"] = sorted(gates)

    for lifecycle in lifecycles:
        row = row_for(str(lifecycle.get("session_name", "")))
        row["generated_manifest_count"] = int(row.get("generated_manifest_count", 0) or 0) + 1
        row["generated_asset_count"] = int(row.get("generated_asset_count", 0) or 0) + int(lifecycle.get("asset_count", 0) or 0)
        row["generated_pending_count"] = int(row.get("generated_pending_count", 0) or 0) + int(lifecycle.get("blocked_or_pending_count", 0) or 0)
        row["placeholder_mapping_count"] = int(row.get("placeholder_mapping_count", 0) or 0) + int(lifecycle.get("placeholder_count", 0) or 0)

    selected_lower = str(selected_session or "").lower()
    entries = list(rows.values())
    for entry in entries:
        entry["selected"] = str(entry.get("session_name", "")).lower() == selected_lower
        entry["state"] = "blocked" if entry.get("blocking_gates") else ("ready" if entry.get("has_ledger") else "partial")
    entries.sort(key=lambda item: (
        not bool(item.get("selected", False)),
        str(item.get("session_name", "")).lower(),
    ))
    entries = entries[:safe_limit]
    return {
        "schema": "unreal_mcp_chat_ide_companion_session_picker.v1",
        "selected_session": selected_session,
        "session_count": len(entries),
        "sessions": entries,
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
    }


def event_detail(event: Dict[str, Any], index: int, artifact_limit: int) -> Dict[str, Any]:
    artifacts = event.get("artifacts") if isinstance(event.get("artifacts"), list) else []
    safe_artifacts = [str(artifact) for artifact in artifacts[:artifact_limit]]
    return {
        "index": index,
        "phase_name": str(event.get("phase_name", "")),
        "evidence_type": str(event.get("evidence_type", "")),
        "summary": str(event.get("summary", "")),
        "timestamp_unix": event.get("timestamp_unix", 0),
        "artifact_count": len(artifacts),
        "artifacts": safe_artifacts,
        "artifact_items": [
            {
                "index": artifact_index,
                "value": artifact,
                "kind": classify_artifact(artifact),
            }
            for artifact_index, artifact in enumerate(safe_artifacts, start=1)
        ],
        "artifact_overflow_count": max(0, len(artifacts) - len(safe_artifacts)),
    }


def phase_index_for_events(events: List[Any]) -> List[Dict[str, Any]]:
    phases: Dict[str, Dict[str, Any]] = {}
    for index, event in enumerate(events, start=1):
        if not isinstance(event, dict):
            continue
        phase_name = str(event.get("phase_name", "") or "unknown")
        entry = phases.setdefault(phase_name, {
            "phase_name": phase_name,
            "event_count": 0,
            "latest_event_index": 0,
        })
        entry["event_count"] += 1
        entry["latest_event_index"] = index
    return list(phases.values())


def build_session_list_payload(
    *,
    include_ide_companion_ledgers: bool = True,
    limit: int = 50,
    chat_session_dir: Optional[Path | str] = None,
    ledger_session_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    safe_limit = max(1, min(int(limit or 50), 200))
    session_payload = list_sessions(session_dir=chat_session_dir)
    sessions = session_payload.get("sessions", [])[:safe_limit]
    ledgers = list_ide_companion_ledgers(safe_limit, session_dir=ledger_session_dir) if include_ide_companion_ledgers else []
    return {
        "sessions": sessions,
        "last_session": session_payload.get("last_session", ""),
        "ide_companion_ledgers": ledgers,
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
    }


def build_session_resume_context(
    *,
    session: str = "",
    message_limit: int = 20,
    chat_session_dir: Optional[Path | str] = None,
    ledger_session_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    session_payload = list_sessions(session_dir=chat_session_dir)
    selected_session = str(session or session_payload.get("last_session") or "default")
    safe_limit = max(1, min(int(message_limit or 20), 100))
    recent = get_recent_messages(limit=safe_limit, session=selected_session, session_dir=chat_session_dir)
    ledger = find_matching_ledger(selected_session, session_dir=ledger_session_dir)
    suggested_actions = [
        {
            "label": "Resume IDE Companion Session",
            "tool": "skill_resume_ide_companion_session",
            "arguments": {"ledger_path": ledger.get("ledger_path", "")} if ledger else {"session_name": selected_session},
            "enabled": bool(ledger),
        },
        {
            "label": "Show IDE Companion Dashboard",
            "tool": "skill_compile_ide_companion_dashboard",
            "arguments": {"ledger_path": ledger.get("ledger_path", "")} if ledger else {"session_name": selected_session},
            "enabled": bool(ledger),
        },
    ]
    return {
        "session": selected_session,
        "recent_messages": recent,
        "matching_ide_companion_ledger": ledger,
        "suggested_actions": suggested_actions,
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
        "warnings": [] if ledger else ["No matching IDE companion ledger was found for this chat session."],
    }


def build_cockpit_overview(
    *,
    session: str = "",
    message_limit: int = 20,
    limit: int = 50,
    chat_session_dir: Optional[Path | str] = None,
    ledger_session_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    session_list = build_session_list_payload(
        include_ide_companion_ledgers=True,
        limit=limit,
        chat_session_dir=chat_session_dir,
        ledger_session_dir=ledger_session_dir,
    )
    resume = build_session_resume_context(
        session=session,
        message_limit=message_limit,
        chat_session_dir=chat_session_dir,
        ledger_session_dir=ledger_session_dir,
    )
    selected_session = str(resume.get("session") or session_list.get("last_session") or "default")
    queues = find_matching_queues(selected_session, session_dir=ledger_session_dir, limit=20)
    asset_lifecycles = find_matching_asset_lifecycles(selected_session, session_dir=ledger_session_dir, limit=20)
    session_picker = build_ide_companion_session_picker(
        selected_session=selected_session,
        limit=limit,
        session_dir=ledger_session_dir,
    )
    ledger = resume.get("matching_ide_companion_ledger") if isinstance(resume.get("matching_ide_companion_ledger"), dict) else {}
    work_order_template = ledger.get("work_order_template") if isinstance(ledger.get("work_order_template"), dict) else {}
    blocking_gates = sorted({
        str(gate)
        for gate in list(ledger.get("blocking_gates", []))
        + [gate for queue in queues for gate in queue.get("blocking_gates", [])]
        if str(gate).strip()
    })
    blocker_resolutions = build_blocker_resolution_summary(blocking_gates)
    runtime_verification = build_runtime_verification_checklist(
        work_order_template=work_order_template,
        ledger=ledger,
        queues=queues,
        blocking_gates=blocking_gates,
    )
    runtime_review = build_runtime_review(runtime_verification)
    repair_loop = build_repair_loop_summary(
        work_order_template=work_order_template,
        runtime_verification=runtime_verification,
        blocking_gates=blocking_gates,
    )
    readiness_policy = build_readiness_policy_summary(
        blocking_gates=blocking_gates,
        queues=queues,
        work_order_template=work_order_template,
    )
    readiness_repair_queue = local_readiness_repair_queue(blocking_gates)
    generated_asset_quality_gate = build_generated_asset_quality_gate_summary(asset_lifecycles)
    target_generated_asset_for_spend = select_generated_asset_context(generated_asset_quality_gate)
    current_platform_preflight = platform_preflight_context()
    provider_spend_review = provider_spend_context(
        readiness_policy=readiness_policy,
        generated_asset_quality_gate=generated_asset_quality_gate,
        target_generated_asset_context=target_generated_asset_for_spend,
        platform_preflight=current_platform_preflight,
    )
    generated_animation_lifecycle_gate = generated_animation_lifecycle_context(
        asset_lifecycles=asset_lifecycles,
        readiness_policy=readiness_policy,
    )
    evidence_recording = build_evidence_recording_checklist(
        session_name=selected_session,
        ledger=ledger,
        queues=queues,
        asset_lifecycles=asset_lifecycles,
        generated_asset_quality_gate=generated_asset_quality_gate,
        work_order_template=work_order_template,
        runtime_verification=runtime_verification,
        repair_loop=repair_loop,
        blocker_resolutions=blocker_resolutions,
        readiness_policy=readiness_policy,
        readiness_repair_queue=readiness_repair_queue,
        provider_spend=provider_spend_review,
        platform_preflight=current_platform_preflight,
    )
    next_safe_step = build_next_safe_step_gate(
        queues=queues,
        blocking_gates=blocking_gates,
        evidence_recording=evidence_recording,
        work_order_template=work_order_template,
        generated_animation_context=generated_animation_lifecycle_gate,
    )
    execution_review = build_execution_review(
        next_safe_step=next_safe_step,
        evidence_recording=evidence_recording,
    )
    failure_triage = build_failure_triage_summary(
        ledger=ledger,
        next_safe_step=next_safe_step,
        runtime_verification=runtime_verification,
        repair_loop=repair_loop,
        blocker_resolutions=blocker_resolutions,
    )
    repair_review = build_repair_review(
        repair_loop=repair_loop,
        failure_triage=failure_triage,
        target_phase=str(ledger.get("work_order_phase") or ledger.get("next_phase") or ""),
    )
    queued_action_count = sum(int(queue.get("action_count", 0) or 0) for queue in queues)
    next_queue = queues[0] if queues else {}
    feature_template_queue = next(
        (
            queue
            for queue in queues
            if isinstance(queue, dict) and queue.get("feature_template_next_operation_id")
        ),
        next_queue,
    )
    lifecycle_asset_count = sum(int(lifecycle.get("asset_count", 0) or 0) for lifecycle in asset_lifecycles)
    lifecycle_pending_count = sum(int(lifecycle.get("blocked_or_pending_count", 0) or 0) for lifecycle in asset_lifecycles)
    lifecycle_animation_count = sum(int(lifecycle.get("animation_asset_count", 0) or 0) for lifecycle in asset_lifecycles)
    lifecycle_animation_pending_count = sum(int(lifecycle.get("animation_pending_count", 0) or 0) for lifecycle in asset_lifecycles)
    lifecycle_placeholder_count = sum(int(lifecycle.get("placeholder_count", 0) or 0) for lifecycle in asset_lifecycles)
    unsupported_provider_task_count = sum(int(lifecycle.get("unsupported_provider_task_count", 0) or 0) for lifecycle in asset_lifecycles)
    unsupported_provider_task_preview = [
        item
        for lifecycle in asset_lifecycles
        for item in (
            lifecycle.get("unsupported_provider_task_preview", [])
            if isinstance(lifecycle.get("unsupported_provider_task_preview"), list)
            else []
        )
    ][:5]
    next_lifecycle = asset_lifecycles[0] if asset_lifecycles else {}
    generated_animation_target = (
        generated_animation_lifecycle_gate.get("target_animation", {})
        if isinstance(generated_animation_lifecycle_gate.get("target_animation"), dict)
        else {}
    )
    generated_animation_next_action = (
        generated_animation_lifecycle_gate.get("next_safe_action", {})
        if isinstance(generated_animation_lifecycle_gate.get("next_safe_action"), dict)
        else {}
    )
    blueprint_mutation_gate = blueprint_mutation_context(
        readiness_policy=readiness_policy,
        work_order_template=work_order_template,
        queues=queues,
        target_phase=str(ledger.get("work_order_phase") or ledger.get("next_phase") or ""),
        blueprint_evidence=(
            current_platform_preflight.get("blueprint_mutation_evidence_contract", {})
            if isinstance(current_platform_preflight, dict)
            else {}
        ),
    )
    cards = [
        {
            "id": "session",
            "title": "Session",
            "state": "ready",
            "summary": selected_session,
            "details": {
                "recent_message_count": len(resume.get("recent_messages", [])),
                "known_session_count": len(session_list.get("sessions", [])),
            },
        },
        {
            "id": "evidence",
            "title": "Evidence",
            "state": "ready" if ledger else "missing",
            "summary": ledger.get("latest_summary", "No matching IDE companion ledger."),
            "details": {
                "ledger_path": ledger.get("ledger_path", ""),
                "event_count": ledger.get("event_count", 0),
                "completed_phase_count": ledger.get("completed_phase_count", 0),
                "latest_phase": ledger.get("latest_phase", ""),
            },
        },
        {
            "id": "blockers",
            "title": "Blockers",
            "state": "blocked" if blocking_gates else "clear",
            "summary": ", ".join(blocking_gates) if blocking_gates else "No local blockers recorded in the selected ledger or queue.",
            "details": {
                "blocking_gates": blocking_gates,
                "hard_blocker_count": blocker_resolutions.get("hard_blocker_count", 0),
                "recommended_tools": blocker_resolutions.get("recommended_tools", []),
                "resolution_preview": [
                    {
                        "blocker": item.get("blocker", ""),
                        "recommended_strategy": item.get("recommended_strategy", ""),
                        "fallback_action": item.get("fallback_action", ""),
                    }
                    for item in blocker_resolutions.get("resolutions", [])[:3]
                ],
            },
        },
        {
            "id": "readiness_policy",
            "title": "Readiness Policy",
            "state": readiness_policy.get("state", "blocked"),
            "summary": f"{readiness_policy.get('blocked_policy_count', 0)} guarded policy area(s) blocked",
            "details": {
                "editor_mutation_missing_gates": readiness_policy.get("editor_mutation", {}).get("missing_gates", []),
                "paid_generation_missing_gates": readiness_policy.get("paid_generation", {}).get("missing_gates", []),
                "paid_animation_generation_missing_gates": readiness_policy.get("paid_animation_generation", {}).get("missing_gates", []),
                "blueprint_mutation_missing_gates": readiness_policy.get("blueprint_mutation", {}).get("missing_gates", []),
                "blueprint_mutation_state": blueprint_mutation_gate.get("state", ""),
                "blueprint_template_name": blueprint_mutation_gate.get("template_name", ""),
                "blueprint_target_phase": blueprint_mutation_gate.get("target_phase", ""),
                "blueprint_editor_operation_count": blueprint_mutation_gate.get("editor_operation_count", 0),
                "blueprint_bridge_required_operation_count": blueprint_mutation_gate.get("bridge_required_operation_count", 0),
                "blueprint_compile_after_operation_count": blueprint_mutation_gate.get("compile_after_operation_count", 0),
                "blueprint_readback_after_operation_count": blueprint_mutation_gate.get("readback_after_operation_count", 0),
                "blueprint_queued_action_count": blueprint_mutation_gate.get("queued_action_count", 0),
                "blueprint_pre_read_required": blueprint_mutation_gate.get("pre_read_required", False),
                "blueprint_compile_plan_required": blueprint_mutation_gate.get("compile_plan_required", False),
                "blueprint_readback_plan_required": blueprint_mutation_gate.get("readback_plan_required", False),
                "blueprint_evidence_required_preview": blueprint_mutation_gate.get("evidence_required_preview", []),
                "blueprint_editor_operation_tool_preview": blueprint_mutation_gate.get("editor_operation_tool_preview", []),
                "blueprint_operation_proof_required_after_preview": blueprint_mutation_gate.get("operation_proof_required_after_preview", []),
                "recommended_tools": readiness_policy.get("recommended_tools", []),
            },
        },
        {
            "id": "editor_queue",
            "title": "Editor Queue",
            "state": "blocked" if any(queue.get("bridge_blocked") for queue in queues) else ("ready" if queues else "empty"),
            "summary": f"{queued_action_count} queued editor action(s)",
            "details": {
                "queue_count": len(queues),
                "queued_action_count": queued_action_count,
                "next_action_id": next_queue.get("next_action_id", ""),
                "next_action_tool": next_queue.get("next_action_tool", ""),
                "can_execute_now": bool(next_queue.get("can_execute_now", False)),
                "feature_template_name": feature_template_queue.get("feature_template_name", ""),
                "feature_template_display_name": feature_template_queue.get("feature_template_display_name", ""),
                "feature_template_operation_count": feature_template_queue.get("feature_template_operation_count", 0),
                "feature_template_next_operation_id": feature_template_queue.get("feature_template_next_operation_id", ""),
                "feature_template_next_operation_type": feature_template_queue.get("feature_template_next_operation_type", ""),
                "feature_template_next_operation_summary": feature_template_queue.get("feature_template_next_operation_summary", ""),
                "feature_template_next_operation_tool_preview": feature_template_queue.get("feature_template_next_operation_tool_preview", []),
                "feature_template_next_operation_required_before_preview": feature_template_queue.get("feature_template_next_operation_required_before_preview", []),
                "feature_template_next_operation_required_after_preview": feature_template_queue.get("feature_template_next_operation_required_after_preview", []),
                "feature_template_next_operation_stop_if_missing_preview": feature_template_queue.get("feature_template_next_operation_stop_if_missing_preview", []),
            },
        },
        {
            "id": "generated_assets",
            "title": "Generated Assets",
            "state": "blocked" if (lifecycle_pending_count or lifecycle_animation_pending_count or unsupported_provider_task_count) else ("ready" if asset_lifecycles else "missing"),
            "summary": f"{lifecycle_asset_count} planned generated asset(s); {lifecycle_animation_count} animation(s); {lifecycle_placeholder_count} placeholder mapping(s)",
            "details": {
                "manifest_count": len(asset_lifecycles),
                "asset_count": lifecycle_asset_count,
                "animation_asset_count": lifecycle_animation_count,
                "blocked_or_pending_count": lifecycle_pending_count,
                "animation_pending_count": lifecycle_animation_pending_count,
                "placeholder_count": lifecycle_placeholder_count,
                "unsupported_provider_task_count": unsupported_provider_task_count,
                "unsupported_provider_task_preview": unsupported_provider_task_preview,
                "next_manifest_path": next_lifecycle.get("manifest_path", ""),
                "preferred_provider": next_lifecycle.get("preferred_provider", ""),
                "animation_gate_state": generated_animation_lifecycle_gate.get("state", ""),
                "animation_provider": generated_animation_lifecycle_gate.get("animation_provider", ""),
                "animation_target_name": generated_animation_target.get("name", ""),
                "animation_target_role": generated_animation_target.get("role", ""),
                "animation_target_task_type": generated_animation_target.get("task_type", ""),
                "animation_target_status": generated_animation_target.get("task_status", ""),
                "animation_target_skeleton": generated_animation_target.get("target_skeleton", ""),
                "animation_next_safe_action_id": generated_animation_next_action.get("action_id", ""),
                "animation_next_safe_action_state": generated_animation_next_action.get("state", ""),
                "animation_next_safe_action_tool": generated_animation_next_action.get("tool", ""),
                "animation_candidate_tool_after_unblocked": generated_animation_next_action.get("candidate_tool_after_unblocked", ""),
                "animation_missing_stage_preview": generated_animation_lifecycle_gate.get("missing_stage_preview", []),
                "animation_missing_paid_gate_preview": generated_animation_lifecycle_gate.get("missing_paid_gate_preview", []),
                "animation_missing_editor_gate_preview": generated_animation_lifecycle_gate.get("missing_editor_gate_preview", []),
                "animation_usage_receipt_path": generated_animation_lifecycle_gate.get("uthana_usage_receipt_path", ""),
                "animation_usage_confirmation_field": generated_animation_lifecycle_gate.get("uthana_usage_confirmation_field", ""),
            },
        },
    ]
    cards.append({
        "id": "generated_asset_quality_gate",
        "title": "Asset Quality",
        "state": generated_asset_quality_gate.get("state", "missing"),
        "summary": (
            f"{generated_asset_quality_gate.get('asset_count', 0)} generated asset gate(s)"
            if generated_asset_quality_gate.get("asset_count", 0)
            else "No generated asset quality gates are available."
        ),
        "details": {
            "provider_pending_count": generated_asset_quality_gate.get("provider_pending_count", 0),
            "import_pending_count": generated_asset_quality_gate.get("import_pending_count", 0),
            "quality_pending_count": generated_asset_quality_gate.get("quality_pending_count", 0),
            "ready_count": generated_asset_quality_gate.get("ready_count", 0),
            "placeholder_count": generated_asset_quality_gate.get("placeholder_count", 0),
            "item_preview": generated_asset_quality_gate.get("items", [])[:3],
        },
    })
    if work_order_template:
        cards.append({
            "id": "feature_work_order",
            "title": "Feature Work",
            "state": "blocked" if blocking_gates else "ready",
            "summary": work_order_template.get("display_name") or work_order_template.get("template_name", ""),
            "details": {
                "target_phase": work_order_template.get("target_phase", ""),
                "template_name": work_order_template.get("template_name", ""),
                "asset_count": work_order_template.get("asset_count", 0),
                "operation_count": work_order_template.get("operation_count", 0),
                "editor_operation_count": work_order_template.get("editor_operation_count", 0),
                "bridge_required_operation_count": work_order_template.get("bridge_required_operation_count", 0),
                "compile_after_operation_count": work_order_template.get("compile_after_operation_count", 0),
                "readback_after_operation_count": work_order_template.get("readback_after_operation_count", 0),
                "compile_check_count": work_order_template.get("compile_check_count", 0),
                "pie_validation_count": work_order_template.get("pie_validation_count", 0),
                "repair_instruction_count": work_order_template.get("repair_instruction_count", 0),
                "evidence_requirement_count": work_order_template.get("evidence_requirement_count", 0),
                "completion_proof_gate_count": work_order_template.get("completion_proof_gate_count", 0),
                "completion_required_evidence_count": work_order_template.get("completion_required_evidence_count", 0),
                "generated_animation_prompt_count": work_order_template.get("generated_animation_prompt_count", 0),
                "generated_animation_prompt_preview": work_order_template.get("generated_animation_prompt_preview", []),
                "generated_animation_provider_preview": work_order_template.get("generated_animation_provider_preview", []),
                "generated_animation_target_skeleton_preview": work_order_template.get("generated_animation_target_skeleton_preview", []),
                "generated_animation_tool_preview": work_order_template.get("generated_animation_tool_preview", []),
                "generated_animation_proof_required_preview": work_order_template.get("generated_animation_proof_required_preview", []),
                "estimated_uthana_motion_seconds": work_order_template.get("estimated_uthana_motion_seconds", 0),
                "operation_preview": work_order_template.get("operation_preview", []),
                "editor_operation_type_preview": work_order_template.get("editor_operation_type_preview", []),
                "editor_operation_tool_preview": work_order_template.get("editor_operation_tool_preview", []),
                "editor_operation_preview": work_order_template.get("editor_operation_preview", []),
                "next_editor_operation_id": work_order_template.get("next_editor_operation_id", ""),
                "next_editor_operation_type": work_order_template.get("next_editor_operation_type", ""),
                "next_editor_operation_summary": work_order_template.get("next_editor_operation_summary", ""),
                "next_editor_operation_tool_preview": work_order_template.get("next_editor_operation_tool_preview", []),
                "next_editor_operation_requires_bridge": work_order_template.get("next_editor_operation_requires_bridge", False),
                "next_editor_operation_requires_compile_after": work_order_template.get("next_editor_operation_requires_compile_after", False),
                "next_editor_operation_requires_readback_after": work_order_template.get("next_editor_operation_requires_readback_after", False),
                "pie_validation_preview": work_order_template.get("pie_validation_preview", []),
                "repair_preview": work_order_template.get("repair_preview", []),
                "completion_proof_gate_preview": work_order_template.get("completion_proof_gate_preview", []),
            },
        })
    cards.append({
        "id": "runtime_verification",
        "title": "Runtime Verification",
        "state": runtime_verification.get("state", "missing"),
        "summary": (
            f"{len(runtime_verification.get('items', []))} runtime proof item(s)"
            if runtime_verification.get("available")
            else "No runtime verification checklist is available for the selected work order."
        ),
        "details": {
            "target_phase": runtime_verification.get("target_phase", ""),
            "bridge_blocked": runtime_verification.get("bridge_blocked", False),
            "pie_validation_count": runtime_verification.get("pie_validation_count", 0),
            "compile_check_count": runtime_verification.get("compile_check_count", 0),
            "evidence_requirement_count": runtime_verification.get("evidence_requirement_count", 0),
            "runtime_evidence_event_count": runtime_verification.get("runtime_evidence_event_count", 0),
            "item_preview": runtime_verification.get("items", [])[:3],
        },
    })
    cards.append({
        "id": "runtime_review",
        "title": "Runtime Review",
        "state": runtime_review.get("state", "missing"),
        "summary": (
            f"{runtime_review.get('pie_validation_count', 0)} PIE step(s); {runtime_review.get('evidence_requirement_count', 0)} proof item(s)"
            if runtime_review.get("available")
            else "No runtime verification review is available."
        ),
        "details": {
            "target_phase": runtime_review.get("target_phase", ""),
            "can_verify_now": runtime_review.get("can_verify_now", False),
            "bridge_blocked": runtime_review.get("bridge_blocked", False),
            "compile_check_count": runtime_review.get("compile_check_count", 0),
            "runtime_evidence_event_count": runtime_review.get("runtime_evidence_event_count", 0),
            "blocked_item_count": runtime_review.get("blocked_item_count", 0),
            "pending_item_count": runtime_review.get("pending_item_count", 0),
            "recorded_item_count": runtime_review.get("recorded_item_count", 0),
            "stop_after_runtime_probe": runtime_review.get("stop_after_runtime_probe", True),
        },
    })
    cards.append({
        "id": "repair_loop",
        "title": "Repair Loop",
        "state": repair_loop.get("state", "missing"),
        "summary": (
            f"{repair_loop.get('repair_instruction_count', 0)} repair instruction(s)"
            if repair_loop.get("available")
            else "No bounded repair instructions are available for the selected work order."
        ),
        "details": {
            "bridge_blocked": repair_loop.get("bridge_blocked", False),
            "repair_instruction_count": repair_loop.get("repair_instruction_count", 0),
            "stop_condition_count": repair_loop.get("stop_condition_count", 0),
            "runtime_state": repair_loop.get("runtime_state", ""),
            "runtime_item_count": repair_loop.get("runtime_item_count", 0),
            "recommended_tool": repair_loop.get("recommended_tool", ""),
            "evidence_tool": repair_loop.get("evidence_tool", ""),
            "item_preview": repair_loop.get("items", [])[:3],
        },
    })
    cards.append({
        "id": "repair_review",
        "title": "Repair Review",
        "state": repair_review.get("state", "missing"),
        "summary": (
            f"{repair_review.get('failure_signal_count', 0)} signal(s); {repair_review.get('repair_instruction_count', 0)} repair instruction(s)"
            if repair_review.get("available")
            else "No selected repair target is available."
        ),
        "details": {
            "target_repair_id": repair_review.get("target_repair", {}).get("id", ""),
            "target_phase": repair_review.get("target_phase", ""),
            "bridge_blocked": repair_review.get("bridge_blocked", False),
            "blocked_count": repair_review.get("blocked_count", 0),
            "needs_repair_count": repair_review.get("needs_repair_count", 0),
            "stop_condition_count": repair_review.get("stop_condition_count", 0),
            "recommended_tool": repair_review.get("recommended_tool", ""),
            "evidence_tool": repair_review.get("evidence_tool", ""),
            "stop_after_repair_attempt": repair_review.get("stop_after_repair_attempt", True),
        },
    })
    cards.append({
        "id": "next_safe_step",
        "title": "Next Safe Step",
        "state": next_safe_step.get("state", "empty"),
        "summary": next_safe_step.get("next_action_tool") or "No queued editor action is ready.",
        "details": {
            "queue_name": next_safe_step.get("queue_name", ""),
            "target_phase": next_safe_step.get("target_phase", ""),
            "next_action_id": next_safe_step.get("next_action_id", ""),
            "next_action_label": next_safe_step.get("next_action_label", ""),
            "can_execute_now": next_safe_step.get("can_execute_now", False),
            "bridge_blocked": next_safe_step.get("bridge_blocked", False),
            "blocking_gates": next_safe_step.get("blocking_gates", []),
            "after_execution_evidence_count": next_safe_step.get("after_execution_evidence_count", 0),
        },
    })
    cards.append({
        "id": "execution_review",
        "title": "Execution Review",
        "state": execution_review.get("state", "blocked"),
        "summary": (
            "Ready to run exactly one queued action"
            if execution_review.get("can_execute_now")
            else f"{execution_review.get('missing_gate_count', 0)} gate(s) block execution"
        ),
        "details": {
            "tool": execution_review.get("target_action", {}).get("tool", ""),
            "action_id": execution_review.get("target_action", {}).get("action_id", ""),
            "target_phase": execution_review.get("target_action", {}).get("target_phase", ""),
            "missing_gates": execution_review.get("missing_gates", []),
            "after_execution_evidence_count": execution_review.get("after_execution_evidence_count", 0),
            "policy_preview": execution_review.get("policy_preview", []),
            "stop_after_action": execution_review.get("stop_after_action", True),
        },
    })
    cards.append({
        "id": "failure_triage",
        "title": "Failure Triage",
        "state": failure_triage.get("state", "clear"),
        "summary": (
            f"{failure_triage.get('item_count', 0)} recovery signal(s)"
            if failure_triage.get("item_count", 0)
            else "No failed or blocked recovery signals are visible."
        ),
        "details": {
            "blocked_count": failure_triage.get("blocked_count", 0),
            "needs_repair_count": failure_triage.get("needs_repair_count", 0),
            "recommended_tools": failure_triage.get("recommended_tools", []),
            "evidence_tool": failure_triage.get("evidence_tool", ""),
            "item_preview": failure_triage.get("items", [])[:3],
        },
    })
    cards.append({
        "id": "evidence_recording",
        "title": "Evidence Recording",
        "state": "blocked" if evidence_recording.get("blocked_count", 0) else ("ready" if evidence_recording.get("item_count", 0) else "empty"),
        "summary": f"{evidence_recording.get('item_count', 0)} evidence item(s) to record",
        "details": {
            "target_phase": evidence_recording.get("target_phase", ""),
            "pending_count": evidence_recording.get("pending_count", 0),
            "blocked_count": evidence_recording.get("blocked_count", 0),
            "recorded_count": evidence_recording.get("recorded_count", 0),
            "record_tool": evidence_recording.get("record_tool", ""),
            "item_preview": evidence_recording.get("items", [])[:3],
        },
    })
    suggested_actions = list(resume.get("suggested_actions", []))
    if queues:
        suggested_actions.append({
            "label": "Execute Next Queued Editor Action",
            "tool": next_queue.get("next_action_tool", ""),
            "arguments": {"queue_path": next_queue.get("queue_path", ""), "action_id": next_queue.get("next_action_id", "")},
            "enabled": bool(next_safe_step.get("can_execute_now", False)),
        })
    workflow_actions = cockpit_workflow_actions(
        session_name=selected_session,
        ledger=ledger,
        queues=queues,
        blocking_gates=blocking_gates,
        readiness_policy=readiness_policy,
        work_order_template=work_order_template,
        evidence_recording=evidence_recording,
        blocker_resolutions=blocker_resolutions,
        repair_loop=repair_loop,
        asset_lifecycles=asset_lifecycles,
        generated_asset_quality_gate=generated_asset_quality_gate,
        next_safe_step=next_safe_step,
        execution_review=execution_review,
        repair_review=repair_review,
        runtime_review=runtime_review,
        platform_preflight=current_platform_preflight,
    )
    warnings = list(resume.get("warnings", []))
    if queues and not any(queue.get("can_execute_now") for queue in queues):
        warnings.append("Queued editor actions are present but not executable until bridge/readiness gates pass.")
    if unsupported_provider_task_count:
        warnings.append(
            f"{unsupported_provider_task_count} generated provider task(s) are planned but do not have registered public MCP submit tools yet."
        )
    hud_summary = build_clean_hud_summary(
        selected_session=selected_session,
        ledger=ledger,
        blocking_gates=blocking_gates,
        readiness_policy=readiness_policy,
        readiness_repair_queue=readiness_repair_queue,
        work_order_template=work_order_template,
        next_safe_step=next_safe_step,
        execution_review=execution_review,
        generated_asset_quality_gate=generated_asset_quality_gate,
        generated_animation_lifecycle_gate=generated_animation_lifecycle_gate,
        evidence_recording=evidence_recording,
        platform_preflight=current_platform_preflight,
    )
    return {
        "schema": "unreal_mcp_chat_cockpit_overview.v1",
        "session": selected_session,
        "session_list": session_list,
        "session_picker": session_picker,
        "resume_context": {key: value for key, value in resume.items() if key != "warnings"},
        "editor_queues": queues,
        "generated_asset_lifecycles": asset_lifecycles,
        "generated_asset_quality_gate": generated_asset_quality_gate,
        "readiness_policy": readiness_policy,
        "readiness_repair_queue": readiness_repair_queue,
        "work_order_template": work_order_template,
        "runtime_verification": runtime_verification,
        "runtime_review": runtime_review,
        "repair_loop": repair_loop,
        "evidence_recording": evidence_recording,
        "next_safe_step": next_safe_step,
        "execution_review": execution_review,
        "repair_review": repair_review,
        "failure_triage": failure_triage,
        "evidence_timeline": ledger.get("preview_events", []),
        "hud_summary": hud_summary,
        "cards": cards,
        "suggested_actions": suggested_actions,
        "workflow_actions": workflow_actions,
        "blocker_resolutions": blocker_resolutions,
        "blocking_gates": blocking_gates,
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
        "warnings": warnings,
    }


def build_ledger_detail(
    *,
    session: str = "",
    ledger_path: str = "",
    event_index: int = 0,
    limit: int = 20,
    artifact_limit: int = 12,
    chat_session_dir: Optional[Path | str] = None,
    ledger_session_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    session_payload = list_sessions(session_dir=chat_session_dir)
    selected_session = str(session or session_payload.get("last_session") or "default")
    warnings: List[str] = []
    resolved_path = resolve_ledger_path(
        ledger_path=ledger_path,
        session_name=selected_session,
        session_dir=ledger_session_dir,
    )
    if resolved_path is None and not ledger_path:
        summary = find_matching_ledger(selected_session, session_dir=ledger_session_dir)
        resolved_path = resolve_ledger_path(
            ledger_path=str(summary.get("ledger_path", "")),
            session_name=selected_session,
            session_dir=ledger_session_dir,
        ) if summary else None

    if resolved_path is None:
        warnings.append("No matching IDE companion ledger was found for this chat session.")
        return {
            "schema": "unreal_mcp_chat_ledger_detail.v1",
            "session": selected_session,
            "ledger_found": False,
            "ledger_path": "",
            "event_count": 0,
            "events": [],
            "phase_index": [],
            "latest_status": {},
            "latest_work_order": {},
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
            "warnings": warnings,
        }

    payload = read_ledger_payload(resolved_path)
    if payload is None:
        warnings.append("The selected file is not a valid IDE companion ledger.")
        return {
            "schema": "unreal_mcp_chat_ledger_detail.v1",
            "session": selected_session,
            "ledger_found": False,
            "ledger_path": relative_repo_path(resolved_path),
            "event_count": 0,
            "events": [],
            "phase_index": [],
            "latest_status": {},
            "latest_work_order": {},
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
            "warnings": warnings,
        }

    events = payload.get("events") if isinstance(payload.get("events"), list) else []
    safe_artifact_limit = max(1, min(int(artifact_limit or 12), 50))
    if int(event_index or 0) > 0:
        selected = int(event_index)
        event_slice = [(selected, events[selected - 1])] if 1 <= selected <= len(events) else []
        if not event_slice:
            warnings.append(f"Event index {selected} is outside the ledger event range.")
    else:
        safe_limit = max(1, min(int(limit or 20), 100))
        start = max(0, len(events) - safe_limit)
        event_slice = list(enumerate(events[start:], start=start + 1))

    detailed_events = [
        event_detail(event, index, safe_artifact_limit)
        for index, event in event_slice
        if isinstance(event, dict)
    ]
    latest_status = payload.get("latest_status") if isinstance(payload.get("latest_status"), dict) else {}
    latest_work_order = payload.get("latest_work_order") if isinstance(payload.get("latest_work_order"), dict) else {}
    return {
        "schema": "unreal_mcp_chat_ledger_detail.v1",
        "session": str(payload.get("session_name") or selected_session),
        "ledger_found": True,
        "ledger_path": relative_repo_path(resolved_path),
        "event_count": len(events),
        "returned_event_count": len(detailed_events),
        "events": detailed_events,
        "phase_index": phase_index_for_events(events),
        "latest_status": latest_status,
        "latest_work_order": latest_work_order,
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
        "warnings": warnings,
    }
