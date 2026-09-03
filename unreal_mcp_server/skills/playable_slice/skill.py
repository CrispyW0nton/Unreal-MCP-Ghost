"""D.7 playable-slice generation skill."""

from __future__ import annotations

import json
import logging
import re
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP.skills.playable_slice")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "knowledge_base" / "v5" / "PLAYABLE_SLICE_SCHEMA.json"
_ASSET_ROLES = ("hero", "prop", "prop", "enemy")
_VALID_MODES = {"plan", "submit_assets", "assemble"}


def _structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_generate_playable_slice", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _mechanic_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_plan_gameplay_mechanic", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _session_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_compile_ide_companion_session", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _session_status_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_compile_ide_companion_status", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _work_order_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_compile_ide_companion_work_order", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _ledger_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_record_ide_companion_evidence", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _resume_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_resume_ide_companion_session", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _dashboard_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_compile_ide_companion_dashboard", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _blocker_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_compile_ide_companion_blocker_resolution", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _placeholder_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_compile_ide_companion_placeholder_manifest", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _asset_lifecycle_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_compile_ide_companion_asset_lifecycle_manifest", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _editor_queue_structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_compile_ide_companion_editor_queue", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _safe_name(value: str, default: str = "PlayableSlice") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", (value or "").strip()).strip("_")
    return cleaned[:60] or default


def _normalize_content_folder(value: str) -> str:
    folder = (value or "/Game/Generated/PlayableSlice").strip().replace("\\", "/")
    if not folder.startswith("/Game"):
        folder = "/Game/Generated/PlayableSlice"
    while "//" in folder:
        folder = folder.replace("//", "/")
    return folder.rstrip("/") or "/Game/Generated/PlayableSlice"


def _asset_object_name(asset_path: str) -> str:
    value = (asset_path or "").strip().replace("\\", "/").rstrip("/")
    return value.rsplit("/", 1)[-1] if value else ""


def _ok(raw: Dict[str, Any]) -> bool:
    if not isinstance(raw, dict):
        return False
    result = raw.get("result") if isinstance(raw.get("result"), dict) else {}
    return (
        raw.get("success") is True
        or raw.get("status") == "success"
        or result.get("success") is True
        or (raw.get("success") is not False and raw.get("status") not in {"error", "failed"} and not raw.get("error"))
    )


def _raw_message(raw: Dict[str, Any], fallback: str) -> str:
    if not isinstance(raw, dict):
        return fallback
    result = raw.get("result") if isinstance(raw.get("result"), dict) else {}
    return str(raw.get("message") or raw.get("error") or result.get("message") or result.get("error") or fallback)


def _raw_field(raw: Dict[str, Any], *keys: str) -> str:
    if not isinstance(raw, dict):
        return ""
    result = raw.get("result") if isinstance(raw.get("result"), dict) else {}
    for key in keys:
        value = raw.get(key)
        if value:
            return str(value)
        value = result.get(key)
        if value:
            return str(value)
    return ""


def _send(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection

    try:
        conn = get_unreal_connection()
        if not conn:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        return conn.send_command(command, params) or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error("playable_slice._send error for %s: %s", command, exc)
        return {"success": False, "message": str(exc)}


def _exec_transactional(code: str, transaction_name: str) -> Dict[str, Any]:
    from tools.exec_substrate import exec_python_transactional

    return exec_python_transactional(code, transaction_name)


def _exec_structured(code: str, stage_name: str) -> Dict[str, Any]:
    from tools.exec_substrate import exec_python_structured

    return exec_python_structured(code, stage_name)


def _theme_from_brief(brief: str) -> str:
    text = brief.lower()
    for keyword in ("dungeon", "forest", "sci fi", "sci-fi", "space", "castle", "city", "lab", "desert"):
        if keyword in text:
            return keyword.replace("-", " ")
    return "third person adventure"


def _enemy_from_brief(brief: str) -> str:
    text = brief.lower()
    for keyword in ("slime", "skeleton", "goblin", "robot", "spider", "boss", "zombie", "drone"):
        if keyword in text:
            return keyword
    return "enemy"


def _asset_prompt(theme: str, role: str, index: int, enemy: str) -> str:
    if role == "hero":
        return f"game-ready third-person hero character for a {theme} playable slice, clean silhouette, readable proportions"
    if role == "enemy":
        return f"game-ready {enemy} enemy for a {theme} encounter, simple patrol/chase readable silhouette"
    prop_names = ("cover prop", "objective pickup")
    return f"game-ready {theme} {prop_names[index - 1]}, low-poly vertical-slice style, clear collision shape"


def build_playable_slice_plan(brief: str, content_path: str = "/Game/Generated/PlayableSlice") -> Dict[str, Any]:
    """Build a deterministic D.7 plan from a one-sentence game brief."""

    theme = _theme_from_brief(brief)
    enemy = _enemy_from_brief(brief)
    slug = _safe_name(brief[:48], "PlayableSlice")
    base_path = _normalize_content_folder(content_path)
    assets: List[Dict[str, Any]] = []
    prop_index = 0
    for index, role in enumerate(_ASSET_ROLES, start=1):
        if role == "prop":
            prop_index += 1
            name = f"{slug}_Prop{prop_index}"
            prompt = _asset_prompt(theme, role, prop_index, enemy)
        else:
            name = f"{slug}_{role.title()}"
            prompt = _asset_prompt(theme, role, index, enemy)
        assets.append({
            "role": role,
            "name": name,
            "prompt": prompt,
            "provider": "tripo",
            "task_type": "text_to_model",
            "content_path": f"{base_path}/Assets",
            "texture": True,
            "pbr": True,
            "texture_quality": "standard",
            "face_limit": 12000,
        })

    return {
        "schema": "unreal_mcp_playable_slice_plan.v1",
        "brief": brief,
        "theme": theme,
        "content_path": base_path,
        "assets": assets,
        "gameplay": {
            "player_blueprint": f"{base_path}/Blueprints/BP_{slug}_Player",
            "enemy_blueprint": f"{base_path}/Blueprints/BP_{slug}_{_safe_name(enemy, 'Enemy').title()}Enemy",
            "behavior_tree": f"{base_path}/AI/BT_{slug}_Enemy",
            "blackboard": f"{base_path}/AI/BB_{slug}_Enemy",
            "hud_widget": f"{base_path}/UI/WBP_{slug}_HUD",
            "level_goal": "small third-person arena with hero start, two props, one patrol/chase enemy, health HUD, and exit objective",
        },
        "tool_sequence": [
            {"phase": "context", "tools": ["get_project_context", "list_available_tools", "execution_journal_start"]},
            {"phase": "generate_assets", "tools": ["gen_tripo_text_to_model", "gen_tripo_wait_for_task", "gen_tripo_import_to_project"]},
            {"phase": "player", "tools": ["create_blueprint", "add_component_to_blueprint", "compile_blueprint"]},
            {"phase": "enemy_ai", "tools": ["create_blackboard", "build_behavior_tree", "create_full_enemy_ai", "compile_blueprint"]},
            {"phase": "level", "tools": ["spawn_actor", "focus_viewport", "viewport_capture_screenshot"]},
            {"phase": "hud", "tools": ["create_widget_blueprint", "add_create_widget_node", "compile_blueprint"]},
            {"phase": "verify", "tools": ["compile_blueprint_and_report", "pie_launch_session", "viewport_capture_screenshot"]},
            {"phase": "report", "tools": ["execution_journal_finish", "skill_package_vertical_slice_report"]},
        ],
        "validation": {
            "required_blueprints": ["player_blueprint", "enemy_blueprint", "hud_widget"],
            "required_runtime_evidence": ["PIE >= 60 seconds", "viewport screenshot", "compile reports"],
            "report_tool": "skill_package_vertical_slice_report",
        },
    }


def validate_playable_slice_plan(plan: Dict[str, Any]) -> List[str]:
    """Validate the repo-local D.7 schema subset without external packages."""

    errors: List[str] = []
    if plan.get("schema") != "unreal_mcp_playable_slice_plan.v1":
        errors.append("schema must be unreal_mcp_playable_slice_plan.v1")
    if not str(plan.get("brief", "")).strip():
        errors.append("brief is required")
    assets = plan.get("assets")
    if not isinstance(assets, list) or len(assets) != 4:
        errors.append("assets must include hero, two props, and one enemy")
    else:
        roles = [asset.get("role") for asset in assets if isinstance(asset, dict)]
        if roles.count("hero") != 1 or roles.count("prop") != 2 or roles.count("enemy") != 1:
            errors.append("asset roles must be one hero, two props, and one enemy")
        for asset in assets:
            if not isinstance(asset, dict):
                errors.append("asset entries must be objects")
                continue
            for key in ("name", "prompt", "provider", "task_type", "content_path"):
                if not str(asset.get(key, "")).strip():
                    errors.append(f"asset {asset.get('role', '?')} missing {key}")
    for key in ("gameplay", "tool_sequence", "validation"):
        if key not in plan:
            errors.append(f"{key} is required")
    return errors


def _mechanic_kind(brief: str) -> str:
    text = brief.lower()
    if any(token in text for token in ("bug", "fix", "broken", "repair", "crash", "runtime error", "compile error", "regression", "failed", "failure")):
        return "bug_fix_repair"
    if any(token in text for token in ("optimize", "optimization", "performance", "fps", "frame", "hitch", "profile", "profiling")):
        return "performance_optimization"
    if (
        any(token in text for token in ("vertical slice", "playable slice", "slice"))
        and any(token in text for token in ("ai", "patrol", "enemy", "npc"))
        and any(token in text for token in ("objective", "hud"))
        and any(token in text for token in ("placeholder", "generated", "asset", "swap", "replacement"))
    ):
        return "ai_objective_asset_swap_slice"
    if any(token in text for token in ("ability", "cooldown", "dash", "spell", "power", "gas")):
        return "ability_cooldown"
    if any(token in text for token in ("ai", "patrol", "chase", "perception", "enemy", "npc")):
        return "ai_encounter"
    if any(token in text for token in ("combat", "attack", "damage", "weapon", "melee", "shoot", "boss")):
        return "combat_loop"
    if any(token in text for token in ("save", "load", "checkpoint", "persistent", "persistence")):
        return "save_load_state"
    if any(token in text for token in ("inventory", "item", "resource", "craft")):
        return "inventory_resource"
    if any(token in text for token in ("interact", "pickup", "collect", "use", "objective", "quest", "door", "switch")):
        return "interaction_objective"
    return "core_gameplay_loop"


def _mechanic_blueprint_plan(kind: str, slug: str, content_path: str) -> List[Dict[str, Any]]:
    common_component = {
        "name": f"BP_{slug}_MechanicComponent",
        "parent_class": "ActorComponent",
        "path": f"{content_path}/Blueprints",
        "role": "reusable mechanic state and events",
        "variables": [
            {"name": "bIsActive", "type": "Boolean", "default": True},
            {"name": "Progress", "type": "Float", "default": 0.0},
        ],
        "functions": ["ActivateMechanic", "CompleteMechanic", "ResetMechanic"],
    }
    if kind == "bug_fix_repair":
        return [
            common_component,
            {
                "name": f"BP_{slug}_RepairProbe",
                "parent_class": "Actor",
                "path": f"{content_path}/Blueprints",
                "role": "failure reproduction, scoped repair, and verification evidence marker",
                "variables": [
                    {"name": "FailureSummary", "type": "String", "default": ""},
                    {"name": "LastKnownGoodState", "type": "String", "default": ""},
                    {"name": "bRepairVerified", "type": "Boolean", "default": False},
                ],
                "functions": ["CaptureFailureContext", "ApplyScopedFix", "CaptureVerification", "ReportRepair"],
            },
        ]
    if kind == "performance_optimization":
        return [
            common_component,
            {
                "name": f"BP_{slug}_PerformanceProbe",
                "parent_class": "Actor",
                "path": f"{content_path}/Blueprints",
                "role": "runtime probe and evidence marker for scoped optimization passes",
                "variables": [
                    {"name": "TargetScenario", "type": "String", "default": "PlayableSlice"},
                    {"name": "BaselineFrameMs", "type": "Float", "default": 0.0},
                    {"name": "OptimizedFrameMs", "type": "Float", "default": 0.0},
                ],
                "functions": ["CaptureBaseline", "ApplyScopedOptimization", "CaptureAfter", "ReportDelta"],
            },
        ]
    if kind == "combat_loop":
        return [
            common_component,
            {
                "name": f"BP_{slug}_Damageable",
                "parent_class": "ActorComponent",
                "path": f"{content_path}/Blueprints",
                "role": "health and damage response",
                "variables": [
                    {"name": "Health", "type": "Float", "default": 100.0},
                    {"name": "MaxHealth", "type": "Float", "default": 100.0},
                    {"name": "bIsDead", "type": "Boolean", "default": False},
                ],
                "functions": ["ApplyDamage", "Die", "OnDamageFeedback"],
            },
        ]
    if kind == "ability_cooldown":
        return [
            common_component,
            {
                "name": f"BP_{slug}_Ability",
                "parent_class": "ActorComponent",
                "path": f"{content_path}/Blueprints",
                "role": "ability activation and cooldown state",
                "variables": [
                    {"name": "CooldownSeconds", "type": "Float", "default": 3.0},
                    {"name": "bOnCooldown", "type": "Boolean", "default": False},
                    {"name": "Charges", "type": "Integer", "default": 1},
                ],
                "functions": ["CanActivate", "ActivateAbility", "StartCooldown", "FinishCooldown"],
            },
        ]
    if kind == "ai_encounter":
        return [
            common_component,
            {
                "name": f"BP_{slug}_Enemy",
                "parent_class": "Character",
                "path": f"{content_path}/Blueprints",
                "role": "enemy pawn driven by Blackboard and Behavior Tree",
                "variables": [
                    {"name": "TargetActor", "type": "Object", "default": None},
                    {"name": "PatrolRadius", "type": "Float", "default": 900.0},
                    {"name": "AggroRange", "type": "Float", "default": 1200.0},
                ],
                "functions": ["SetTarget", "ClearTarget", "HandlePlayerSeen"],
            },
        ]
    if kind == "ai_objective_asset_swap_slice":
        return [
            common_component,
            {
                "name": f"BP_{slug}_Enemy",
                "parent_class": "Character",
                "path": f"{content_path}/Blueprints",
                "role": "patrol enemy pawn with generated-or-placeholder visual slot",
                "variables": [
                    {"name": "TargetActor", "type": "Object", "default": None},
                    {"name": "PatrolRadius", "type": "Float", "default": 900.0},
                    {"name": "GeneratedMeshPath", "type": "String", "default": ""},
                ],
                "functions": ["SetTarget", "ClearTarget", "ApplyGeneratedMesh", "UsePlaceholderMesh"],
            },
            {
                "name": f"BP_{slug}_ObjectiveDirector",
                "parent_class": "Actor",
                "path": f"{content_path}/Blueprints",
                "role": "objective state, HUD update, and enemy encounter completion coordinator",
                "variables": [
                    {"name": "ObjectiveText", "type": "Text", "default": "Reach the objective"},
                    {"name": "bObjectiveComplete", "type": "Boolean", "default": False},
                    {"name": "EnemyDefeatedCount", "type": "Integer", "default": 0},
                ],
                "functions": ["StartObjective", "UpdateObjectiveHUD", "HandleEnemyResolved", "CompleteObjective"],
            },
        ]
    if kind == "inventory_resource":
        return [
            common_component,
            {
                "name": f"BP_{slug}_InventoryComponent",
                "parent_class": "ActorComponent",
                "path": f"{content_path}/Blueprints",
                "role": "item/resource collection and persistence handoff",
                "variables": [
                    {"name": "ItemCount", "type": "Integer", "default": 0},
                    {"name": "Capacity", "type": "Integer", "default": 10},
                    {"name": "bPersistToSaveGame", "type": "Boolean", "default": True},
                ],
                "functions": ["CanAddItem", "AddItem", "RemoveItem", "SerializeInventory"],
            },
        ]
    if kind == "save_load_state":
        return [
            common_component,
            {
                "name": f"BP_{slug}_SaveStateComponent",
                "parent_class": "ActorComponent",
                "path": f"{content_path}/Blueprints",
                "role": "save/load state handoff for feature progress",
                "variables": [
                    {"name": "SaveSlotName", "type": "String", "default": "PlayerProgress"},
                    {"name": "bHasSavedState", "type": "Boolean", "default": False},
                    {"name": "SavedProgress", "type": "Float", "default": 0.0},
                ],
                "functions": ["CaptureState", "ApplyLoadedState", "SaveProgress", "LoadProgress"],
            },
        ]
    return [
        common_component,
        {
            "name": f"BP_{slug}_Interactable",
            "parent_class": "Actor",
            "path": f"{content_path}/Blueprints",
            "role": "world actor the player can use to advance the loop",
            "variables": [
                {"name": "PromptText", "type": "Text", "default": "Interact"},
                {"name": "InteractionRadius", "type": "Float", "default": 180.0},
                {"name": "bConsumed", "type": "Boolean", "default": False},
            ],
            "functions": ["CanInteract", "Interact", "ShowPrompt", "HidePrompt"],
        },
    ]


def _mechanic_asset_plan(kind: str, brief: str, slug: str, content_path: str, include_generated_assets: bool) -> List[Dict[str, Any]]:
    if not include_generated_assets:
        return []
    if kind == "bug_fix_repair":
        return []
    role_by_kind = {
        "performance_optimization": ("profiling marker prop", "optimized visual proxy"),
        "combat_loop": ("weapon prop", "impact feedback prop"),
        "ability_cooldown": ("ability pickup", "ability effect marker"),
        "ai_encounter": ("enemy character", "patrol marker prop"),
        "ai_objective_asset_swap_slice": ("patrol enemy character", "objective beacon prop"),
        "inventory_resource": ("collectible item", "storage/cache prop"),
        "save_load_state": ("save station prop", "checkpoint marker prop"),
        "interaction_objective": ("interactable objective prop", "completion reward prop"),
        "core_gameplay_loop": ("mechanic focus prop", "feedback marker prop"),
    }
    roles = role_by_kind.get(kind, role_by_kind["core_gameplay_loop"])
    return [
        {
            "role": role,
            "name": f"{slug}_{index}_{_safe_name(role, 'Asset')}",
            "provider": "tripo",
            "task_type": "text_to_model",
            "content_path": f"{content_path}/Assets",
            "prompt": f"game-ready {role} for {brief}, readable silhouette, low-poly UE5 vertical slice style",
            "texture": True,
            "pbr": True,
            "face_limit": 12000,
            "smart_low_poly": True,
        }
        for index, role in enumerate(roles, start=1)
    ]


def _mechanic_animation_plan(kind: str, brief: str, slug: str, content_path: str, include_generated_assets: bool) -> List[Dict[str, Any]]:
    if not include_generated_assets:
        return []
    if kind in {"bug_fix_repair", "performance_optimization", "save_load_state", "inventory_resource", "interaction_objective", "core_gameplay_loop"}:
        text = brief.lower()
        if not any(token in text for token in ("animation", "motion", "locomotion", "walk", "run", "attack", "ability", "cast", "emote")):
            return []
    role_prompts_by_kind = {
        "ai_encounter": [
            ("enemy_patrol_locomotion", "loopable cautious enemy patrol walk with readable silhouette and clean foot contact"),
            ("enemy_chase_locomotion", "loopable aggressive enemy chase run with forward momentum and game-ready timing"),
        ],
        "ai_objective_asset_swap_slice": [
            ("enemy_patrol_locomotion", "loopable cautious enemy patrol walk for a generated-or-placeholder enemy character"),
            ("enemy_objective_reaction", "short enemy reaction or alert turn toward an objective marker with clear anticipation"),
        ],
        "combat_loop": [
            ("combat_attack_motion", "short readable melee attack motion with anticipation, impact beat, and recovery"),
            ("combat_hit_reaction", "short humanoid hit reaction suitable for gameplay feedback and retargeting"),
        ],
        "ability_cooldown": [
            ("ability_activation_motion", "short ability activation or casting motion with readable startup and recovery"),
            ("ability_cooldown_recovery", "short recovery or return-to-idle motion after an ability use"),
        ],
        "core_gameplay_loop": [
            ("gameplay_feedback_motion", "short humanoid feedback motion for the requested gameplay loop"),
        ],
        "interaction_objective": [
            ("interaction_use_motion", "short humanoid interact or use motion with clear hand/torso action"),
        ],
    }
    roles = role_prompts_by_kind.get(kind, role_prompts_by_kind.get("core_gameplay_loop", []))
    return [
        {
            "role": role,
            "name": f"{slug}_{_safe_name(role, 'Motion')}",
            "provider": "uthana",
            "task_type": "text_to_motion",
            "content_path": f"{content_path}/Animations",
            "prompt": f"{motion_prompt} for {brief}, UE5 gameplay animation, neutral humanoid stance, retarget-friendly",
            "target_skeleton": "UE5 Manny or project humanoid skeleton",
            "format": "fbx",
            "estimated_seconds": 4,
            "default_character_id": "cXi2eAP19XwQ",
            "animation_usage": "generated motion stays placeholder-gated until import, retarget/readback, AnimGraph reference, PIE proof, and ledger evidence pass",
        }
        for role, motion_prompt in roles
    ]


def _feature_operation_type(template_name: str, operation: str) -> str:
    text = f"{template_name} {operation}".lower()
    if any(token in text for token in ("bug", "fix", "broken", "repair", "crash", "runtime error", "compile error", "regression", "failure")):
        return "bug_fix_repair"
    if "blackboard" in text or "behavior tree" in text or "perception" in text:
        return "ai_blackboard_behavior_tree"
    if "placeholder" in text or "generated asset" in text or "replacement" in text or "asset lifecycle" in text:
        return "generated_asset_replacement"
    if "input" in text or "enhanced input" in text or "cooldown" in text:
        return "input_and_cooldown"
    if "savegame" in text or "save" in text or "load" in text or "checkpoint" in text:
        return "save_load_state"
    if "optimiz" in text or "performance" in text or "profil" in text or "fps" in text or "frame" in text or "hitch" in text:
        return "performance_optimization"
    if "replicate" in text or "server" in text or "authoritative" in text:
        return "replication_authority"
    if "hud" in text or "widget" in text or "prompt" in text:
        return "hud_feedback"
    if "collision" in text or "component" in text or "mesh" in text or "overlap" in text:
        return "component_setup"
    return "blueprint_graph_wiring"


def _feature_operation_tools(operation_type: str) -> List[str]:
    tools_by_type = {
        "ai_blackboard_behavior_tree": [
            "create_blackboard",
            "set_behavior_tree_blackboard",
            "build_behavior_tree",
            "bt_get_info",
        ],
        "input_and_cooldown": [
            "project_create_input_action",
            "project_create_input_mapping_context",
            "add_enhanced_input_action_event",
            "add_blueprint_variable",
        ],
        "save_load_state": [
            "create_save_game_blueprint",
            "add_blueprint_variable",
            "add_blueprint_function_with_pins",
            "compile_blueprint_and_report",
        ],
        "performance_optimization": [
            "get_project_context",
            "scan_project_assets",
            "compile_blueprint_and_report",
            "pie_capture_log",
            "viewport_capture_screenshot",
        ],
        "bug_fix_repair": [
            "get_project_context",
            "bp_get_graph_summary",
            "compile_blueprint_and_report",
            "pie_capture_log",
            "viewport_capture_screenshot",
            "skill_compile_ide_companion_work_order",
            "skill_record_ide_companion_evidence",
        ],
        "replication_authority": [
            "net_set_actor_replicates",
            "net_configure_replicated_property",
            "compile_blueprint_and_report",
        ],
        "hud_feedback": [
            "create_umg_widget_blueprint",
            "add_text_block_to_widget",
            "add_create_widget_node",
            "compile_blueprint_and_report",
        ],
        "component_setup": [
            "add_component_to_blueprint",
            "set_component_property",
            "compile_blueprint_and_report",
        ],
        "generated_asset_replacement": [
            "skill_compile_ide_companion_asset_lifecycle_manifest",
            "skill_compile_ide_companion_placeholder_manifest",
            "chat_get_cockpit_overview",
            "compile_blueprint_and_report",
        ],
        "blueprint_graph_wiring": [
            "bp_get_graph_summary",
            "bp_add_node",
            "bp_connect_pins",
            "compile_blueprint_and_report",
        ],
    }
    return tools_by_type.get(operation_type, tools_by_type["blueprint_graph_wiring"])


def _feature_operation_checklist(template_name: str, operations: List[str]) -> List[Dict[str, Any]]:
    checklist: List[Dict[str, Any]] = []
    for index, operation in enumerate(operations, start=1):
        operation_type = _feature_operation_type(template_name, operation)
        operation_id = f"{template_name}_{index:02d}"
        checklist.append({
            "id": operation_id,
            "phase": "editor_implementation",
            "operation_type": operation_type,
            "summary": operation,
            "tool_candidates": _feature_operation_tools(operation_type),
            "requires_bridge": True,
            "requires_compile_after": True,
            "requires_readback_after": True,
            "readback_evidence": "Blueprint graph/component summary confirms the operation before PIE.",
            "ledger_evidence_type": "feature_template_operation",
            "operation_proof_contract": {
                "schema": "unreal_mcp_gameplay_feature_operation_proof.v1",
                "operation_id": operation_id,
                "required_before": [
                    "unreal_bridge_reachable",
                    "blueprint_pre_read_evidence",
                ],
                "required_after": [
                    "blueprint_compile_report",
                    "graph_or_component_readback",
                    "ide_companion_ledger_event",
                ],
                "stop_if_missing": [
                    "bridge ping failed",
                    "compile report missing or failed",
                    "readback does not show the expected operation",
                ],
            },
        })
    return checklist


def _feature_runtime_proof_contract(template_name: str) -> Dict[str, Any]:
    base = {
        "schema": "unreal_mcp_gameplay_feature_runtime_proof.v1",
        "template_name": template_name,
        "mode": "single_player_feature_smoke",
        "required_before": [
            "unreal_bridge_reachable",
            "editor_operations_read_back",
            "blueprint_compile_report",
        ],
        "required_evidence": [
            "pie_log",
            "viewport_or_hud_screenshot",
            "ide_companion_ledger_event",
        ],
        "tool_candidates": [
            "compile_blueprint_and_report",
            "pie_launch_session",
            "pie_capture_log",
            "viewport_capture_screenshot",
        ],
        "stop_if_missing": [
            "PIE was not launched or runtime proof is absent",
            "PIE log contains Blueprint runtime errors",
            "ledger evidence was not recorded",
        ],
        "repair_tools": [
            "skill_compile_ide_companion_work_order",
            "compile_blueprint_and_report",
            "pie_capture_log",
            "skill_record_ide_companion_evidence",
        ],
    }
    if template_name in {"enemy_patrol_chase_attack", "ai_patrol_objective_asset_swap_slice"}:
        base.update({
            "mode": "ai_behavior_tree_navigation_smoke",
            "required_evidence": [
                "bt_get_info_blackboard_assigned",
                "blackboard_key_readback",
                "nav_describe_agent_settings_or_setup_navmesh_result",
                "enemy_capsule_and_movement_component_readback",
                "pie_ai_state_or_log",
                "viewport_or_hud_screenshot",
                "ide_companion_ledger_event",
            ],
            "tool_candidates": [
                "set_behavior_tree_blackboard",
                "bt_get_info",
                "nav_describe_agent_settings",
                "setup_navmesh",
                "compile_blueprint_and_report",
                "pie_launch_session",
                "pie_capture_log",
                "viewport_capture_screenshot",
            ],
            "stop_if_missing": [
                "Behavior Tree has no Blackboard assigned",
                "Blackboard keys TargetActor, PatrolLocation, AggroRange, or AttackRange are missing",
                "nav bounds, nav agent, capsule, or movement component readback is absent",
                "PIE proof does not show patrol, chase, and attack state transitions",
                "ledger evidence was not recorded",
            ],
            "repair_tools": [
                "set_behavior_tree_blackboard",
                "bt_get_info",
                "nav_describe_agent_settings",
                "setup_navmesh",
                "skill_compile_ide_companion_work_order",
                "skill_record_ide_companion_evidence",
            ],
        })
    if template_name == "replicated_combat_sample":
        base.update({
            "mode": "replicated_authority_combat_smoke",
            "required_evidence": [
                "net_describe_blueprint_replication",
                "server_authority_damage_policy_readback",
                "replicated_health_or_death_state_readback",
                "net_validate_common_mistakes",
                "single_player_pie_damage_proof",
                "two_player_pie_or_deferred_rationale",
                "ide_companion_ledger_event",
            ],
            "tool_candidates": [
                "net_set_actor_replicates",
                "net_configure_replicated_property",
                "net_describe_blueprint_replication",
                "net_validate_common_mistakes",
                "network_debug_replication",
                "compile_blueprint_and_report",
                "pie_launch_session",
                "pie_capture_log",
            ],
            "stop_if_missing": [
                "damage path has no server-authority policy or explicit non-networked rationale",
                "health/death state replication readback is absent when networking is requested",
                "net_validate_common_mistakes reports unresolved replication blockers",
                "two-player PIE proof or explicit deferred rationale is missing",
                "ledger evidence was not recorded",
            ],
            "repair_tools": [
                "net_validate_common_mistakes",
                "net_describe_blueprint_replication",
                "skill_compile_ide_companion_work_order",
                "skill_record_ide_companion_evidence",
            ],
        })
    if template_name == "input_cooldown_ability":
        base.update({
            "mode": "input_cooldown_ability_smoke",
            "required_evidence": [
                "enhanced_input_action_mapping_readback",
                "ability_component_cooldown_variable_readback",
                "can_activate_false_while_cooldown_active",
                "hud_cooldown_state_or_widget_readback",
                "pie_input_press_cooldown_log",
                "viewport_or_hud_screenshot",
                "ide_companion_ledger_event",
            ],
            "tool_candidates": [
                "project_create_input_action",
                "project_create_input_mapping_context",
                "add_enhanced_input_action_event",
                "bp_get_graph_summary",
                "compile_blueprint_and_report",
                "pie_launch_session",
                "pie_capture_log",
                "viewport_capture_screenshot",
            ],
            "stop_if_missing": [
                "Enhanced Input action or mapping context readback is absent",
                "cooldown state variable/readback is missing",
                "PIE proof does not show activation followed by blocked repeat input",
                "HUD cooldown feedback proof is missing or stale",
                "ledger evidence was not recorded",
            ],
            "repair_tools": [
                "project_create_input_action",
                "add_enhanced_input_action_event",
                "bp_get_graph_summary",
                "compile_blueprint_and_report",
                "skill_compile_ide_companion_work_order",
                "skill_record_ide_companion_evidence",
            ],
        })
    if template_name == "save_load_state":
        base.update({
            "mode": "save_load_state_restore_smoke",
            "required_evidence": [
                "savegame_blueprint_or_slot_helper_readback",
                "save_slot_name_and_version_key_readback",
                "captured_feature_state_before_save",
                "loaded_feature_state_matches_saved_state",
                "hud_or_objective_state_restored_after_load",
                "pie_save_load_log",
                "viewport_or_hud_screenshot",
                "ide_companion_ledger_event",
            ],
            "tool_candidates": [
                "create_save_game_blueprint",
                "savegame_add_slot_helpers",
                "bp_get_graph_summary",
                "compile_blueprint_and_report",
                "pie_launch_session",
                "pie_capture_log",
                "viewport_capture_screenshot",
            ],
            "stop_if_missing": [
                "SaveGame Blueprint or slot helper readback is absent",
                "saved feature state and loaded feature state are not compared",
                "load path does not apply restored state before HUD/objective feedback resumes",
                "PIE proof does not show save then load or restore",
                "ledger evidence was not recorded",
            ],
            "repair_tools": [
                "create_save_game_blueprint",
                "savegame_add_slot_helpers",
                "bp_get_graph_summary",
                "compile_blueprint_and_report",
                "skill_compile_ide_companion_work_order",
                "skill_record_ide_companion_evidence",
            ],
        })
    return base


def _feature_template_for_kind(
    kind: str,
    slug: str,
    blueprint_assets: List[Dict[str, Any]],
    generated_assets: List[Dict[str, Any]],
    generated_animations: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    template_names = {
        "interaction_objective": "interactable_objective",
        "inventory_resource": "pickup_resource_loop",
        "save_load_state": "save_load_state",
        "performance_optimization": "performance_optimization_pass",
        "bug_fix_repair": "bug_fix_repair_pass",
        "ai_encounter": "enemy_patrol_chase_attack",
        "ai_objective_asset_swap_slice": "ai_patrol_objective_asset_swap_slice",
        "ability_cooldown": "input_cooldown_ability",
        "combat_loop": "replicated_combat_sample",
        "core_gameplay_loop": "objective_hud_update",
    }
    template_name = template_names.get(kind, "objective_hud_update")
    asset_list = [
        {"kind": "blueprint", "name": asset.get("name", ""), "role": asset.get("role", ""), "path": asset.get("path", "")}
        for asset in blueprint_assets
        if isinstance(asset, dict)
    ] + [
        {"kind": "generated_or_placeholder", "name": asset.get("name", ""), "role": asset.get("role", ""), "path": asset.get("content_path", "")}
        for asset in generated_assets
        if isinstance(asset, dict)
    ] + [
        {"kind": "generated_animation_or_placeholder", "name": asset.get("name", ""), "role": asset.get("role", ""), "path": asset.get("content_path", "")}
        for asset in (generated_animations or [])
        if isinstance(asset, dict)
    ]
    common_checks = [
        "compile_blueprint_and_report succeeds for every created Blueprint",
        "bp_get_graph_summary or equivalent readback shows the expected trigger, state mutation, and feedback chain",
        "component readback confirms required collision/mesh/widget/audio components are present",
        "IDE companion ledger records the implementation, compile result, readback, and runtime proof",
    ]
    common_repair = [
        "If a Blueprint compile fails, stop and create a repair work order with the compiler message and graph readback.",
        "If an expected component is missing, re-read the Blueprint components before adding or reconnecting nodes.",
        "If runtime proof is missing, keep the feature marked unproven and rerun PIE/log/screenshot capture after fixing blockers.",
    ]
    templates: Dict[str, Dict[str, Any]] = {
        "interactable_objective": {
            "display_name": "Interactable Objective",
            "ownership_split": {
                "blueprint": ["Interactable Actor", "Mechanic Component", "Prompt Widget"],
                "cpp_candidate": ["Reusable interaction interface only after the Blueprint loop is proven"],
                "data": ["Prompt text", "objective id", "completion reward"],
            },
            "graph_component_operations": [
                "Add collision/interaction volume and visible mesh or placeholder component.",
                "Wire overlap/focus state into ShowPrompt and HidePrompt.",
                "Wire Interact into objective completion, feedback event, and one-shot consumed state.",
                "Update HUD objective text after successful interaction.",
            ],
            "pie_validation": [
                "Player approaches actor and sees prompt.",
                "Interaction fires once, updates objective HUD, and hides or disables completed prompt.",
                "PIE log contains no Blueprint runtime errors.",
            ],
        },
        "pickup_resource_loop": {
            "display_name": "Pickup Resource Loop",
            "ownership_split": {
                "blueprint": ["Pickup Actor", "Inventory/Resource Component", "HUD Counter Widget"],
                "cpp_candidate": ["Inventory serialization or replicated authority if reused across multiple systems"],
                "data": ["Item id", "capacity", "save slot key"],
            },
            "graph_component_operations": [
                "Add overlap/collision component to pickup actor.",
                "Wire pickup overlap or input confirmation into CanAddItem and AddItem.",
                "Destroy or hide pickup only after inventory state changes.",
                "Update HUD counter and optional save-game field.",
            ],
            "pie_validation": [
                "Collecting the pickup increments the HUD/resource count.",
                "Capacity or duplicate rules are respected.",
                "Save/load handoff is recorded or explicitly marked not needed.",
            ],
        },
        "enemy_patrol_chase_attack": {
            "display_name": "Enemy Patrol/Chase/Attack",
            "ownership_split": {
                "blueprint": ["Enemy Character", "AI Controller", "BT tasks/services", "optional perception component"],
                "cpp_candidate": ["Shared combat/damage authority after the behavior tree loop is proven"],
                "data": ["Blackboard keys", "patrol radius", "aggro range", "attack cooldown"],
            },
            "graph_component_operations": [
                "Create or assign Blackboard keys TargetActor, PatrolLocation, AggroRange, and AttackRange.",
                "Create Behavior Tree selector branches for patrol, chase, and attack.",
                "Wire perception or detection into Blackboard TargetActor updates.",
                "Attach movement and attack feedback to thin tasks rather than scattered Blueprint booleans.",
            ],
            "pie_validation": [
                "Enemy patrols when no target is known.",
                "Enemy chases when player is detected and clears target when lost.",
                "Attack feedback triggers only inside range and respects cooldown.",
            ],
        },
        "ai_patrol_objective_asset_swap_slice": {
            "display_name": "AI Patrol Objective Asset-Swap Slice",
            "ownership_split": {
                "blueprint": ["Enemy Character", "AI Controller", "Objective Director", "Objective HUD Widget", "placeholder mesh actor/component"],
                "cpp_candidate": ["Shared enemy state, objective subsystem, or asset replacement subsystem only after the Blueprint slice is proven"],
                "data": ["Blackboard keys", "objective id/text", "placeholder asset path", "generated asset lifecycle manifest", "replacement policy"],
            },
            "graph_component_operations": [
                "Create or assign Blackboard keys TargetActor, PatrolLocation, AggroRange, AttackRange, and ObjectiveActor.",
                "Create Behavior Tree selector branches for patrol, chase, attack, and objective-area arrival.",
                "Wire enemy detection/resolution into ObjectiveDirector objective state updates.",
                "Create Objective HUD text/status update path from ObjectiveDirector.",
                "Add placeholder mesh component and generated asset path variables to the enemy visual slot.",
                "Wire placeholder-to-generated replacement only after lifecycle import, quality proof, and ledger evidence are present.",
            ],
            "pie_validation": [
                "Enemy patrols when no target is known and chases the player when detected.",
                "Objective HUD displays the active objective and updates after the enemy/objective condition is resolved.",
                "Placeholder visual remains active until generated asset quality proof passes.",
                "Generated asset replacement is recorded or explicitly blocked with the placeholder still playable.",
                "PIE log contains no Blueprint runtime errors.",
            ],
        },
        "input_cooldown_ability": {
            "display_name": "Input Cooldown Ability",
            "ownership_split": {
                "blueprint": ["Ability Component", "Enhanced Input Action", "Cooldown HUD Widget"],
                "cpp_candidate": ["Authoritative activation or prediction if the ability becomes replicated"],
                "data": ["Cooldown seconds", "charges", "input mapping context"],
            },
            "graph_component_operations": [
                "Create input action and mapping entry.",
                "Wire input event into CanActivate, ActivateAbility, StartCooldown, and FinishCooldown.",
                "Expose cooldown state to HUD.",
                "Block repeated activation while cooldown is active.",
            ],
            "pie_validation": [
                "Input triggers the ability once.",
                "HUD shows cooldown state.",
                "Repeated input during cooldown is ignored and logged or visually denied.",
            ],
        },
        "replicated_combat_sample": {
            "display_name": "Replicated Combat Sample",
            "ownership_split": {
                "blueprint": ["Damageable Component", "Attack event graph", "Feedback Widget"],
                "cpp_candidate": ["Server-authoritative damage and replicated health should move to C++ before production"],
                "data": ["Damage amount", "health", "death state", "replication policy"],
            },
            "graph_component_operations": [
                "Create health variables and damage application function.",
                "Route attack input or overlap into server-authoritative damage policy.",
                "Replicate health/death state when networking is requested.",
                "Update HUD and impact feedback after damage changes.",
            ],
            "pie_validation": [
                "Damage lowers health and triggers feedback.",
                "Death state fires once.",
                "Replication hooks are implemented or explicitly deferred with rationale.",
            ],
        },
        "save_load_state": {
            "display_name": "Save/Load State",
            "ownership_split": {
                "blueprint": ["Save State Component", "SaveGame Blueprint", "optional checkpoint actor"],
                "cpp_candidate": ["Shared save subsystem once multiple features depend on the same persistence contract"],
                "data": ["Save slot name", "version key", "progress fields", "restore policy"],
            },
            "graph_component_operations": [
                "Create SaveGame object fields for feature progress.",
                "Wire feature completion or checkpoint trigger into CaptureState and SaveProgress.",
                "Wire load path into ApplyLoadedState before player-facing feedback resumes.",
                "Update HUD or objective state after loaded progress is applied.",
            ],
            "pie_validation": [
                "Feature progress is saved after the trigger fires.",
                "Reloading or invoking load restores the expected progress state.",
                "HUD/objective feedback matches the restored state.",
            ],
        },
        "performance_optimization_pass": {
            "display_name": "Performance Optimization Pass",
            "ownership_split": {
                "blueprint": ["Performance Probe Actor", "target feature Blueprint/component readback", "optional optimized proxy component"],
                "cpp_candidate": ["Move repeated tick-heavy or replicated authority code to C++ only after profiling proves the bottleneck"],
                "data": ["baseline scenario", "target frame budget", "suspected hotspot", "before/after evidence paths"],
            },
            "graph_component_operations": [
                "Capture baseline project context, target assets, and current Blueprint/component readback before changing anything.",
                "Add or identify a Performance Probe actor that records the scenario, baseline frame timing, and after-pass timing.",
                "Apply exactly one scoped optimization candidate such as reducing tick work, caching repeated lookups, simplifying collision, or lowering expensive feedback frequency.",
                "Compile and read back the changed Blueprint/component to confirm the optimization did not remove required gameplay feedback.",
                "Capture PIE log, viewport screenshot, and before/after timing evidence for the same scenario.",
            ],
            "pie_validation": [
                "Baseline and after-pass evidence are captured for the same playable scenario.",
                "Gameplay behavior remains equivalent after the optimization.",
                "Frame-time, log-noise, or actor/component count improves or the optimization is reverted and recorded as a failed hypothesis.",
            ],
        },
        "bug_fix_repair_pass": {
            "display_name": "Bug Fix Repair Pass",
            "ownership_split": {
                "blueprint": ["failure target Blueprint/component", "Repair Probe Actor", "verification route"],
                "cpp_candidate": ["Move the fix to C++ only if the failure is shared, authoritative, repeated, or unsafe in Blueprint"],
                "data": ["failure summary", "reproduction steps", "expected behavior", "regression proof"],
            },
            "graph_component_operations": [
                "Capture failure context: target asset, reproduction steps, compile/runtime error, and current graph/component readback.",
                "Reproduce or simulate the failure and record PIE log or viewport evidence before mutating the target.",
                "Apply exactly one scoped fix to the target Blueprint, component, function, or data path.",
                "Compile and read back the changed asset to verify the failure signal is gone and expected behavior remains.",
                "Record regression guard evidence in the IDE companion ledger and create a repair follow-up if the failure persists.",
            ],
            "pie_validation": [
                "Original failure is reproduced or documented as non-reproducible with compile/log/readback evidence.",
                "After the fix, compile/readback/PIE log no longer show the failure.",
                "Core gameplay behavior still works and regression evidence is recorded.",
            ],
        },
        "objective_hud_update": {
            "display_name": "Objective HUD Update",
            "ownership_split": {
                "blueprint": ["Mechanic Component", "Objective Widget", "optional objective actor"],
                "cpp_candidate": ["Objective subsystem only after multiple feature templates share it"],
                "data": ["Objective id", "display text", "completion state"],
            },
            "graph_component_operations": [
                "Create objective state variable and completion event.",
                "Bind widget text or event-driven update to objective state.",
                "Wire mechanic success into objective completion and HUD refresh.",
                "Record readback for widget hierarchy and event path.",
            ],
            "pie_validation": [
                "HUD displays initial objective text.",
                "Gameplay event updates the objective text or completion state.",
                "PIE screenshot captures the final HUD state.",
            ],
        },
    }
    selected = templates[template_name]
    editor_operation_checklist = _feature_operation_checklist(template_name, selected["graph_component_operations"])
    runtime_proof_contract = _feature_runtime_proof_contract(template_name)
    completion_contract = {
        "schema": "unreal_mcp_gameplay_feature_completion_contract.v1",
        "playable_definition": "The feature is only complete after assets exist, editor operations are compiled and read back, PIE validation passes, repair blockers are clear, and the IDE companion ledger records proof.",
        "required_evidence": [
            "feature_template_packet",
            "asset_or_placeholder_manifest",
            "editor_operation_results",
            "blueprint_compile_report",
            "graph_or_component_readback",
            "pie_log",
            "viewport_or_hud_screenshot",
            "runtime_proof_contract_evidence",
            "ide_companion_ledger_event",
        ],
        "proof_gates": [
            {"name": "asset_surface_ready", "source": "asset_list", "required_count": len(asset_list)},
            {"name": "editor_operations_read_back", "source": "editor_operation_checklist", "required_count": len(editor_operation_checklist)},
            {"name": "compile_readback_checks_passed", "source": "compile_readback_checks", "required_count": len(common_checks)},
            {"name": "pie_validation_passed", "source": "pie_validation", "required_count": len(selected["pie_validation"])},
            {"name": "runtime_proof_contract_satisfied", "source": "runtime_proof_contract.required_evidence", "required_count": len(runtime_proof_contract["required_evidence"])},
            {"name": "repair_blockers_clear", "source": "repair_instructions", "required_count": len(common_repair)},
            {"name": "ledger_evidence_recorded", "source": "evidence_requirements", "required_count": 1},
        ],
        "stop_before_complete": [
            "any required asset, placeholder, or generated replacement is missing",
            "any editor operation lacks compile/readback evidence",
            "PIE validation has not been run or contains runtime errors",
            "runtime proof contract evidence is incomplete",
            "repair instructions remain unresolved",
            "IDE companion ledger evidence is missing",
        ],
    }
    return {
        "schema": "unreal_mcp_gameplay_feature_template.v1",
        "template_name": template_name,
        "display_name": selected["display_name"],
        "slug": slug,
        "asset_list": asset_list,
        "ownership_split": selected["ownership_split"],
        "graph_component_operations": selected["graph_component_operations"],
        "editor_operation_checklist": editor_operation_checklist,
        "completion_contract": completion_contract,
        "compile_readback_checks": common_checks,
        "runtime_proof_contract": runtime_proof_contract,
        "pie_validation": selected["pie_validation"],
        "repair_instructions": common_repair,
        "evidence_requirements": [
            "feature template packet",
            "created asset paths or placeholder/generated asset lifecycle manifest",
            "Blueprint compile report",
            "graph/component readback",
            "PIE log and viewport screenshot",
            "IDE companion ledger event for implementation and runtime proof",
        ],
        "stop_conditions": [
            "Unreal bridge is offline for editor mutation",
            "Blueprint compile fails after a structural edit",
            "graph/component readback does not show the expected operation",
            "PIE runtime proof is missing or contains Blueprint runtime errors",
        ],
    }


def build_gameplay_mechanic_plan(
    brief: str,
    content_path: str = "/Game/Generated/Mechanics",
    include_generated_assets: bool = True,
) -> Dict[str, Any]:
    safe_brief = str(brief or "").strip()
    kind = _mechanic_kind(safe_brief)
    slug = _safe_name(safe_brief[:48], "GameplayMechanic")
    base_path = _normalize_content_folder(content_path)
    blueprint_assets = _mechanic_blueprint_plan(kind, slug, base_path)
    generated_assets = _mechanic_asset_plan(kind, safe_brief, slug, base_path, include_generated_assets)
    generated_animation_prompts = _mechanic_animation_plan(kind, safe_brief, slug, base_path, include_generated_assets)
    feature_template = _feature_template_for_kind(kind, slug, blueprint_assets, generated_assets, generated_animation_prompts)
    needs_ai = kind in {"ai_encounter", "ai_objective_asset_swap_slice"}
    needs_damage = kind in {"combat_loop", "ai_encounter", "ai_objective_asset_swap_slice"}
    needs_save = kind in {"inventory_resource", "save_load_state"}
    needs_repair = kind == "bug_fix_repair"
    needs_animation = bool(generated_animation_prompts)
    needs_hud = not needs_repair
    generated_content_tools = ["gen_compile_ide_companion_readiness"]
    if generated_assets:
        generated_content_tools.extend(["gen_tripo_text_to_model", "gen_tripo_import_to_project"])
    if generated_animation_prompts:
        generated_content_tools.extend(["gen_uthana_text_to_motion", "gen_uthana_download_motion", "gen_uthana_import_animation_to_project"])
    tool_sequence = [
        {"phase": "context", "tools": ["get_project_context", "search_knowledge_base", "risk_evaluate_action"]},
        {"phase": "optional_generated_content", "tools": generated_content_tools if (generated_assets or generated_animation_prompts) else []},
        {"phase": "blueprint_scaffold", "tools": ["create_blueprint", "add_blueprint_variable", "add_component_to_blueprint", "compile_blueprint"]},
    ]
    if kind == "performance_optimization":
        tool_sequence.append({"phase": "baseline_profile", "tools": ["get_project_context", "scan_project_assets", "pie_capture_log", "viewport_capture_screenshot"]})
    if needs_repair:
        tool_sequence.append({"phase": "failure_reproduction", "tools": ["get_project_context", "bp_get_graph_summary", "compile_blueprint_and_report", "pie_capture_log", "viewport_capture_screenshot"]})
    if needs_ai:
        tool_sequence.append({"phase": "ai_behavior", "tools": ["create_blackboard", "create_behavior_tree", "build_behavior_tree", "setup_navmesh"]})
    tool_sequence.extend([
        {"phase": "mechanic_logic", "tools": ["bp_get_graph_summary", "bp_add_node", "bp_connect_pins", "bp_compile"]},
        {"phase": "feedback", "tools": ["create_umg_widget_blueprint", "add_text_block_to_widget", "import_sound_asset"]},
        {"phase": "runtime_verification", "tools": ["compile_blueprint_and_report", "pie_launch_session", "pie_capture_log", "viewport_capture_screenshot"]},
        {"phase": "evidence", "tools": ["execution_journal_finish", "skill_package_vertical_slice_report"]},
    ])
    return {
        "schema": "unreal_mcp_gameplay_mechanic_plan.v1",
        "brief": safe_brief,
        "mechanic_kind": kind,
        "content_path": base_path,
        "design_intent": {
            "player_loop": "input or overlap -> mechanic state change -> visible/audio feedback -> objective or system state updates",
            "authoring_style": "small Blueprint/component surface first; move repeated or replicated authority to C++ later",
            "failure_policy": "compile and inspect after each structural phase; keep partial assets usable and reported",
        },
        "supported_feature_templates": [
            "interactable_objective",
            "pickup_resource_loop",
            "enemy_patrol_chase_attack",
            "ai_patrol_objective_asset_swap_slice",
            "objective_hud_update",
            "save_load_state",
            "input_cooldown_ability",
            "replicated_combat_sample",
            "performance_optimization_pass",
            "bug_fix_repair_pass",
        ],
        "feature_template": feature_template,
        "generated_assets": generated_assets,
        "generated_animation_prompts": generated_animation_prompts,
        "estimated_uthana_motion_seconds": sum(int(prompt.get("estimated_seconds", 0) or 0) for prompt in generated_animation_prompts),
        "blueprint_assets": blueprint_assets,
        "system_hooks": {
            "input": {
                "needed": kind in {"interaction_objective", "ability_cooldown", "combat_loop", "core_gameplay_loop"},
                "tools": ["project_create_input_action", "project_create_input_mapping_context", "add_enhanced_input_action_event"],
            },
            "ai": {
                "needed": needs_ai,
                "blackboard_keys": ["TargetActor", "PatrolLocation", "AggroRange"] if needs_ai else [],
                "tools": ["create_blackboard", "create_behavior_tree", "build_behavior_tree"],
            },
            "damage": {
                "needed": needs_damage,
                "tools": ["skill_create_health_system", "apply_point_damage", "add_component_to_blueprint"],
            },
            "hud": {
                "needed": needs_hud,
                "widgets": [f"WBP_{slug}_HUD", f"WBP_{slug}_Prompt"],
                "tools": ["create_umg_widget_blueprint", "add_text_block_to_widget", "compile_blueprint"],
            },
            "savegame": {
                "needed": needs_save,
                "tools": ["create_save_game_blueprint", "savegame_add_slot_helpers"],
            },
            "replication": {
                "needed": kind in {"combat_loop", "inventory_resource", "ability_cooldown"},
                "tools": ["net_set_actor_replicates", "net_configure_replicated_property"],
            },
            "performance": {
                "needed": kind == "performance_optimization",
                "tools": ["get_project_context", "scan_project_assets", "pie_capture_log", "viewport_capture_screenshot"],
            },
            "animation": {
                "needed": needs_animation,
                "provider": "uthana" if needs_animation else "",
                "tools": [
                    "gen_uthana_text_to_motion",
                    "gen_uthana_download_motion",
                    "gen_uthana_import_animation_to_project",
                    "connect_anim_graph_nodes",
                    "add_sequence_player_node",
                    "gen_compile_generated_animation_evidence",
                ] if needs_animation else [],
                "proof_required": [
                    "uthana_api_key_configured",
                    "usage_allowance_and_confirmation",
                    "animation_sequence_load_readback",
                    "target_skeleton_or_retarget_asset",
                    "animgraph_or_state_machine_reference",
                    "pie_motion_playback_or_viewport_proof",
                    "ide_companion_ledger_event",
                ] if needs_animation else [],
            },
            "repair": {
                "needed": needs_repair,
                "tools": [
                    "skill_compile_ide_companion_work_order",
                    "bp_get_graph_summary",
                    "compile_blueprint_and_report",
                    "pie_capture_log",
                    "skill_record_ide_companion_evidence",
                ],
            },
        },
        "tool_sequence": tool_sequence,
        "validation_gates": [
            {"name": "assets_imported_or_stubbed", "evidence": "generated asset paths or explicit placeholder meshes recorded"},
            {"name": "blueprints_compile", "evidence": "compile_blueprint_and_report returns no errors for each Blueprint"},
            {"name": "graph_readback", "evidence": "bp_get_graph_summary shows input/overlap, state mutation, and feedback call chain"},
            {"name": "runtime_feedback", "evidence": "PIE log plus viewport screenshot show prompt/HUD/audio/VFX or state feedback"},
            {"name": "save_or_replication_review", "evidence": "savegame/replication hooks are either implemented or marked not needed"},
        ],
        "next_actions": [
            {"tool": "gen_compile_ide_companion_readiness", "reason": "Check Tripo mesh auth, Uthana motion auth, wallet/usage gates, and editor bridge readiness before generated content work."},
            {"tool": "create_blueprint", "reason": "Create the listed Blueprint/component assets in the target content path."},
            {"tool": "compile_blueprint_and_report", "reason": "Verify each structural phase before wiring additional graph logic."},
            {"tool": "pie_launch_session", "reason": "Prove the mechanic loop in runtime, not only in asset/graph state."},
        ],
    }


def validate_gameplay_mechanic_plan(plan: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if plan.get("schema") != "unreal_mcp_gameplay_mechanic_plan.v1":
        errors.append("schema must be unreal_mcp_gameplay_mechanic_plan.v1")
    if not str(plan.get("brief", "")).strip():
        errors.append("brief is required")
    if not str(plan.get("content_path", "")).startswith("/Game"):
        errors.append("content_path must start with /Game")
    if not isinstance(plan.get("blueprint_assets"), list) or not plan["blueprint_assets"]:
        errors.append("at least one Blueprint asset is required")
    template = plan.get("feature_template")
    if not isinstance(template, dict) or template.get("schema") != "unreal_mcp_gameplay_feature_template.v1":
        errors.append("feature_template must use unreal_mcp_gameplay_feature_template.v1")
    else:
        for key in ("asset_list", "ownership_split", "graph_component_operations", "editor_operation_checklist", "completion_contract", "compile_readback_checks", "pie_validation", "repair_instructions"):
            if not template.get(key):
                errors.append(f"feature_template missing {key}")
    if not isinstance(plan.get("tool_sequence"), list) or len(plan["tool_sequence"]) < 4:
        errors.append("tool_sequence must describe context, scaffold, logic, and verification phases")
    if not isinstance(plan.get("validation_gates"), list) or len(plan["validation_gates"]) < 4:
        errors.append("validation_gates must include editor and runtime proof")
    return errors


def skill_plan_gameplay_mechanic(
    brief: str,
    content_path: str = "/Game/Generated/Mechanics",
    include_generated_assets: bool = True,
) -> Dict[str, Any]:
    """Plan an Unreal-ready gameplay mechanic from a short design brief."""

    t0 = time.monotonic()
    inputs = {
        "brief": brief,
        "content_path": content_path,
        "include_generated_assets": include_generated_assets,
    }
    if not str(brief or "").strip():
        return _mechanic_structured(
            success=False,
            stage="invalid_brief",
            message="brief is required",
            inputs=inputs,
            errors=["brief is required"],
            t0=t0,
        )
    plan = build_gameplay_mechanic_plan(brief, content_path, include_generated_assets)
    errors = validate_gameplay_mechanic_plan(plan)
    if errors:
        return _mechanic_structured(
            success=False,
            stage="plan_validation_failed",
            message="Gameplay mechanic plan failed validation",
            inputs=inputs,
            outputs={"plan": plan},
            errors=errors,
            t0=t0,
        )
    return _mechanic_structured(
        success=True,
        stage="plan_ready",
        message="Gameplay mechanic plan validated; no Unreal mutation or paid provider request was sent",
        inputs=inputs,
        outputs={
            "plan": plan,
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
        },
        warnings=["Use the listed tool_sequence to implement incrementally, compiling and capturing runtime evidence after each structural phase."],
        t0=t0,
    )


def build_ide_companion_session_plan(
    project_brief: str,
    mechanic_brief: str = "",
    content_path: str = "/Game/Generated/PlayableSlice",
    session_name: str = "ide-companion",
    include_generated_assets: bool = True,
) -> Dict[str, Any]:
    safe_project = str(project_brief or "").strip()
    safe_mechanic = str(mechanic_brief or "").strip() or safe_project
    base_path = _normalize_content_folder(content_path)
    safe_session = _safe_name(session_name or "ide-companion", "ide-companion")
    mechanic_path = f"{base_path}/Mechanics"
    mechanic_plan = build_gameplay_mechanic_plan(
        safe_mechanic,
        content_path=mechanic_path,
        include_generated_assets=include_generated_assets,
    )
    slice_asset_prompts = [
        {
            "role": role,
            "name": f"{_safe_name(safe_project[:36], 'CompanionSlice')}_{index}_{role}",
            "provider": "tripo",
            "task_type": "text_to_model",
            "content_path": f"{base_path}/Assets",
            "prompt": f"game-ready {role} asset for {safe_project}, readable silhouette, low-poly UE5 vertical slice style",
            "texture": True,
            "pbr": True,
            "smart_low_poly": True,
            "face_limit": 12000,
        }
        for index, role in enumerate(_ASSET_ROLES, start=1)
    ] if include_generated_assets else []
    generated_asset_prompts = slice_asset_prompts + mechanic_plan.get("generated_assets", [])
    generated_animation_prompts = mechanic_plan.get("generated_animation_prompts", []) if include_generated_assets else []
    estimated_tripo_credits = len(generated_asset_prompts) * 40
    estimated_uthana_motion_seconds = sum(int(prompt.get("estimated_seconds", 0) or 0) for prompt in generated_animation_prompts)
    phases = [
        {
            "name": "orient_to_project",
            "goal": "Load the current project context and relevant knowledge before editing.",
            "tools": ["get_project_context", "search_knowledge_base", "risk_evaluate_action"],
            "gate": "context_loaded",
            "spend_required": False,
            "editor_required": False,
        },
        {
            "name": "session_preflight",
            "goal": "Check Tripo mesh auth, Uthana animation auth, provider wallet/quota gates, local session budget, import handoff, and Unreal bridge reachability.",
            "tools": ["gen_compile_ide_companion_readiness"],
            "request": {
                "brief": safe_project,
                "content_path": base_path,
                "session_name": safe_session,
                "include_api_wallet": True,
                "include_unreal_bridge": True,
            },
            "gate": "readiness_ready_or_blocking_gates_reported",
            "spend_required": False,
            "editor_required": False,
        },
        {
            "name": "mechanic_design",
            "goal": "Turn the gameplay request into Unreal assets, system hooks, and validation gates before mutation.",
            "tools": ["skill_plan_gameplay_mechanic"],
            "request": {
                "brief": safe_mechanic,
                "content_path": mechanic_path,
                "include_generated_assets": include_generated_assets,
            },
            "gate": "mechanic_plan_validated",
            "spend_required": False,
            "editor_required": False,
        },
        {
            "name": "asset_generation",
            "goal": "Generate only the meshes and motions required for the slice, then import and preview them in Unreal.",
            "tools": [
                "gen_tripo_text_to_model",
                "gen_tripo_wait_for_task",
                "gen_tripo_import_to_project",
                "gen_prepare_import_manifest",
                "gen_uthana_text_to_motion",
                "gen_uthana_download_motion",
                "gen_uthana_import_animation_to_project",
            ],
            "asset_prompts": generated_asset_prompts,
            "animation_prompts": generated_animation_prompts,
            "gate": "assets_imported_or_placeholders_recorded",
            "spend_required": bool(generated_asset_prompts or generated_animation_prompts),
            "editor_required": False,
        },
        {
            "name": "editor_implementation",
            "goal": "Create the Blueprint, AI, HUD, input, and level pieces in small compileable passes.",
            "tools": [
                "create_blueprint",
                "add_blueprint_variable",
                "add_component_to_blueprint",
                "bp_add_node",
                "bp_connect_pins",
                "compile_blueprint_and_report",
                "create_umg_widget_blueprint",
                "setup_navmesh",
            ],
            "mechanic_assets": mechanic_plan.get("blueprint_assets", []),
            "system_hooks": mechanic_plan.get("system_hooks", {}),
            "gate": "blueprints_compile_and_graph_readback_matches_plan",
            "spend_required": False,
            "editor_required": True,
        },
        {
            "name": "runtime_verification",
            "goal": "Prove the slice in PIE with logs, screenshots, and clear user-facing feedback.",
            "tools": ["pie_launch_session", "pie_capture_log", "viewport_capture_screenshot", "execution_journal_finish"],
            "gate": "pie_log_and_viewport_evidence_captured",
            "spend_required": False,
            "editor_required": True,
        },
        {
            "name": "developer_handoff",
            "goal": "Package what changed, what is proven, and what remains risky for the solo developer.",
            "tools": ["skill_package_vertical_slice_report", "source_control_status", "diagnostics_summary"],
            "gate": "report_lists_assets_mechanics_evidence_and_open_risks",
            "spend_required": False,
            "editor_required": False,
        },
    ]
    gates = [
        {"name": "api_key_configured", "evidence": "gen_compile_ide_companion_readiness outputs.gates"},
        {"name": "uthana_api_key_configured", "evidence": "gen_get_provider_config outputs.uthana_api_key_configured before generated animation tasks"},
        {"name": "api_wallet_has_credits", "evidence": "outputs.blocking_gates does not include api_wallet_has_credits before paid generation"},
        {"name": "unreal_bridge_reachable", "evidence": "bridge ping/readiness gate is ready before editor mutation"},
        {"name": "spend_confirmed", "evidence": "confirm_spend=True only after explicit user approval for listed asset prompts"},
        {"name": "animation_retarget_readback", "evidence": "generated Uthana motion imports as an Animation Sequence and retarget/readback evidence matches the target skeleton"},
        {"name": "mechanic_plan_validated", "evidence": "skill_plan_gameplay_mechanic returns unreal_mcp_gameplay_mechanic_plan.v1"},
        {"name": "blueprints_compile", "evidence": "compile reports contain no Blueprint errors after each pass"},
        {"name": "runtime_evidence", "evidence": "PIE log plus viewport screenshot show the mechanic feedback loop"},
        {"name": "handoff_report_complete", "evidence": "vertical-slice report lists assets, mechanics, proof, and remaining risks"},
    ]
    return {
        "schema": "unreal_mcp_ide_companion_session_plan.v1",
        "project_brief": safe_project,
        "mechanic_brief": safe_mechanic,
        "content_path": base_path,
        "session_name": safe_session,
        "capabilities": {
            "asset_generation": include_generated_assets,
            "animation_generation": bool(generated_animation_prompts),
            "gameplay_mechanic_guidance": True,
            "editor_mutation": "gated_by_unreal_bridge_reachable",
            "runtime_verification": True,
            "spend_policy": "no paid Tripo or Uthana task until readiness is ready and explicit spend/usage confirmation is recorded",
        },
        "estimated_tripo_credits": estimated_tripo_credits,
        "estimated_uthana_motion_seconds": estimated_uthana_motion_seconds,
        "generated_asset_prompts": generated_asset_prompts,
        "generated_animation_prompts": generated_animation_prompts,
        "mechanic_plan": mechanic_plan,
        "phases": phases,
        "gates": gates,
        "fallbacks": [
            {"condition": "api_wallet_has_credits blocked", "action": "Use placeholder meshes and continue Blueprint/mechanic planning without paid generation."},
            {"condition": "uthana_api_key_configured blocked", "action": "Use marketplace/default locomotion placeholders and continue Animation Blueprint planning without paid motion generation."},
            {"condition": "unreal_bridge_reachable blocked", "action": "Return implementation plan and stop before editor mutation until Unreal Editor is listening."},
            {"condition": "Blueprint compile failure", "action": "Run repair_tools, inspect graph summary, and retry the smallest failed pass."},
            {"condition": "PIE verification failure", "action": "Capture log/screenshot evidence and add a focused repair phase before handoff."},
        ],
        "next_actions": [
            {"tool": "gen_compile_ide_companion_readiness", "reason": "Prove wallet, budget, and bridge gates for this session."},
            {"tool": "skill_plan_gameplay_mechanic", "reason": "Confirm the mechanic plan before generating assets or mutating Unreal."},
            {"tool": "gen_tripo_text_to_model", "reason": "Generate listed Smart Mesh assets only after readiness and spend approval."},
            {"tool": "gen_uthana_text_to_motion", "reason": "Generate listed humanoid motion clips only after Uthana readiness and usage approval."},
            {"tool": "compile_blueprint_and_report", "reason": "Keep each implementation pass small and proven."},
            {"tool": "pie_launch_session", "reason": "Verify the mechanic in runtime before calling the session complete."},
        ],
    }


def validate_ide_companion_session_plan(plan: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        errors.append("schema must be unreal_mcp_ide_companion_session_plan.v1")
    if not str(plan.get("project_brief", "")).strip():
        errors.append("project_brief is required")
    if not str(plan.get("content_path", "")).startswith("/Game"):
        errors.append("content_path must start with /Game")
    if plan.get("mechanic_plan", {}).get("schema") != "unreal_mcp_gameplay_mechanic_plan.v1":
        errors.append("mechanic_plan must use unreal_mcp_gameplay_mechanic_plan.v1")
    if not isinstance(plan.get("phases"), list) or len(plan["phases"]) < 6:
        errors.append("phases must cover preflight, design, assets, editor implementation, runtime verification, and handoff")
    if not isinstance(plan.get("gates"), list) or len(plan["gates"]) < 6:
        errors.append("gates must include wallet, bridge, spend, compile, runtime, and handoff proof")
    return errors


def skill_compile_ide_companion_session(
    project_brief: str,
    mechanic_brief: str = "",
    content_path: str = "/Game/Generated/PlayableSlice",
    session_name: str = "ide-companion",
    include_generated_assets: bool = True,
) -> Dict[str, Any]:
    """Compile the full no-spend IDE companion session plan for one developer."""

    t0 = time.monotonic()
    inputs = {
        "project_brief": project_brief,
        "mechanic_brief": mechanic_brief,
        "content_path": content_path,
        "session_name": session_name,
        "include_generated_assets": include_generated_assets,
    }
    if not str(project_brief or "").strip():
        return _session_structured(
            success=False,
            stage="invalid_project_brief",
            message="project_brief is required",
            inputs=inputs,
            errors=["project_brief is required"],
            t0=t0,
        )
    plan = build_ide_companion_session_plan(
        project_brief=project_brief,
        mechanic_brief=mechanic_brief,
        content_path=content_path,
        session_name=session_name,
        include_generated_assets=include_generated_assets,
    )
    errors = validate_ide_companion_session_plan(plan)
    if errors:
        return _session_structured(
            success=False,
            stage="session_plan_validation_failed",
            message="IDE companion session plan failed validation",
            inputs=inputs,
            outputs={"plan": plan},
            errors=errors,
            t0=t0,
        )
    return _session_structured(
        success=True,
        stage="session_plan_ready",
        message="IDE companion session plan validated; no Unreal mutation, network call, or paid provider request was sent",
        inputs=inputs,
        outputs={
            "plan": plan,
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
            "requires_readiness_before_execution": True,
        },
        warnings=["Run gen_compile_ide_companion_readiness before paid generation or editor mutation, then follow outputs.blocking_gates if readiness is not green."],
        t0=t0,
    )


def _coerce_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _coerce_string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = [part.strip() for part in value.split(",")]
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    return []


def _phase_evidence_present(phase_name: str, evidence: Dict[str, Any]) -> bool:
    value = evidence.get(phase_name)
    if isinstance(value, dict):
        return bool(value.get("complete") or value.get("evidence") or value.get("artifacts"))
    if isinstance(value, list):
        return bool(value)
    return bool(value)


def build_ide_companion_status(
    session_plan: Dict[str, Any],
    readiness_report: Optional[Dict[str, Any]] = None,
    completed_phases: Optional[List[str]] = None,
    evidence: Optional[Dict[str, Any]] = None,
    current_blockers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    plan = _coerce_mapping(session_plan)
    readiness = _coerce_mapping(readiness_report)
    proof = _coerce_mapping(evidence)
    completed = set(_coerce_string_list(completed_phases))
    manual_blockers = _coerce_string_list(current_blockers)
    phases = plan.get("phases", []) if isinstance(plan.get("phases"), list) else []
    readiness_outputs = readiness.get("outputs", readiness)
    readiness_blockers = readiness_outputs.get("blocking_gates", []) if isinstance(readiness_outputs, dict) else []
    blocking_gate_names = [
        str(gate.get("name") or gate.get("id") or gate)
        for gate in readiness_blockers
        if isinstance(gate, dict) or str(gate).strip()
    ]
    blocking_gate_names.extend(manual_blockers)

    readiness_ready = bool(readiness_outputs.get("ready")) if readiness_outputs else False
    wallet_blocked = "api_wallet_has_credits" in blocking_gate_names
    bridge_blocked = "unreal_bridge_reachable" in blocking_gate_names
    spend_blocked = "spend_confirmed" in blocking_gate_names
    phase_status = []
    next_phase = None
    blocked = bool(blocking_gate_names)
    for index, phase in enumerate(phases):
        name = str(phase.get("name", f"phase_{index + 1}"))
        requires_spend = bool(phase.get("spend_required"))
        requires_editor = bool(phase.get("editor_required"))
        evidence_present = _phase_evidence_present(name, proof)
        state = "completed" if name in completed or evidence_present else "waiting"
        if state != "completed":
            if name == "session_preflight":
                state = "available"
            elif requires_spend and (wallet_blocked or spend_blocked or not readiness_ready):
                state = "blocked"
            elif requires_editor and (bridge_blocked or not readiness_ready):
                state = "blocked"
            elif not next_phase and not blocked:
                state = "available"
            elif not next_phase and not requires_spend and not requires_editor:
                state = "available"
            if not next_phase and state in {"available", "blocked"}:
                next_phase = name
        phase_status.append({
            "name": name,
            "state": state,
            "gate": phase.get("gate", ""),
            "tools": phase.get("tools", []),
            "spend_required": requires_spend,
            "editor_required": requires_editor,
            "evidence_present": evidence_present,
        })

    missing_evidence = [
        status["name"]
        for status in phase_status
        if status["state"] == "completed" and not status["evidence_present"]
    ]
    available = [status for status in phase_status if status["state"] == "available"]
    blocked_phases = [status for status in phase_status if status["state"] == "blocked"]
    next_action = None
    if blocking_gate_names:
        next_action = {
            "tool": "gen_compile_ide_companion_readiness",
            "reason": f"Resolve blocking gates before continuing: {', '.join(blocking_gate_names)}",
        }
    elif available:
        next_action = {
            "tool": available[0]["tools"][0] if available[0]["tools"] else "continue_session",
            "reason": f"Continue phase {available[0]['name']}.",
        }
    else:
        next_action = {
            "tool": "skill_package_vertical_slice_report",
            "reason": "All phases are complete or waiting only on final evidence packaging.",
        }

    return {
        "schema": "unreal_mcp_ide_companion_status.v1",
        "session_schema": plan.get("schema", ""),
        "project_brief": plan.get("project_brief", ""),
        "session_name": plan.get("session_name", ""),
        "readiness_ready": readiness_ready,
        "blocking_gates": blocking_gate_names,
        "phase_status": phase_status,
        "completed_phase_count": sum(1 for status in phase_status if status["state"] == "completed"),
        "total_phase_count": len(phase_status),
        "available_phase_count": len(available),
        "blocked_phase_count": len(blocked_phases),
        "next_phase": next_phase or (available[0]["name"] if available else ""),
        "next_action": next_action,
        "ready_for_paid_generation": readiness_ready and not wallet_blocked and not spend_blocked,
        "ready_for_editor_mutation": readiness_ready and not bridge_blocked,
        "ready_for_runtime_verification": readiness_ready and "editor_implementation" in completed,
        "missing_evidence": missing_evidence,
        "evidence_summary": {
            "keys": sorted(proof.keys()),
            "count": len(proof),
        },
    }


def validate_ide_companion_status(status: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if status.get("schema") != "unreal_mcp_ide_companion_status.v1":
        errors.append("schema must be unreal_mcp_ide_companion_status.v1")
    if status.get("session_schema") != "unreal_mcp_ide_companion_session_plan.v1":
        errors.append("session_plan must use unreal_mcp_ide_companion_session_plan.v1")
    if not isinstance(status.get("phase_status"), list) or not status["phase_status"]:
        errors.append("phase_status must describe at least one phase")
    if not isinstance(status.get("next_action"), dict):
        errors.append("next_action is required")
    return errors


def skill_compile_ide_companion_status(
    session_plan: Any,
    readiness_report: Any = None,
    completed_phases: Any = None,
    evidence: Any = None,
    current_blockers: Any = None,
) -> Dict[str, Any]:
    """Compile a no-spend status receipt for an IDE companion session plan."""

    t0 = time.monotonic()
    inputs = {
        "session_plan": session_plan,
        "readiness_report": readiness_report,
        "completed_phases": completed_phases,
        "evidence": evidence,
        "current_blockers": current_blockers,
    }
    plan = _coerce_mapping(session_plan)
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        return _session_status_structured(
            success=False,
            stage="invalid_session_plan",
            message="session_plan must be an unreal_mcp_ide_companion_session_plan.v1 object or JSON string",
            inputs=inputs,
            errors=["session_plan must use unreal_mcp_ide_companion_session_plan.v1"],
            t0=t0,
        )
    status = build_ide_companion_status(
        session_plan=plan,
        readiness_report=_coerce_mapping(readiness_report),
        completed_phases=_coerce_string_list(completed_phases),
        evidence=_coerce_mapping(evidence),
        current_blockers=_coerce_string_list(current_blockers),
    )
    errors = validate_ide_companion_status(status)
    if errors:
        return _session_status_structured(
            success=False,
            stage="status_validation_failed",
            message="IDE companion status failed validation",
            inputs=inputs,
            outputs={"status": status},
            errors=errors,
            t0=t0,
        )
    return _session_status_structured(
        success=True,
        stage="status_ready",
        message="IDE companion status compiled; no Unreal mutation, network call, or paid provider request was sent",
        inputs=inputs,
        outputs={
            "status": status,
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
        },
        warnings=["Use status.next_action and status.blocking_gates to choose the next safe companion step."],
        t0=t0,
    )


def _extract_status_payload(value: Any) -> Dict[str, Any]:
    raw = _coerce_mapping(value)
    if raw.get("schema") == "unreal_mcp_ide_companion_status.v1":
        return raw
    outputs = raw.get("outputs") if isinstance(raw.get("outputs"), dict) else {}
    status = outputs.get("status") if isinstance(outputs.get("status"), dict) else {}
    return status if status.get("schema") == "unreal_mcp_ide_companion_status.v1" else {}


def _find_phase(plan: Dict[str, Any], phase_name: str) -> Dict[str, Any]:
    phases = plan.get("phases", []) if isinstance(plan.get("phases"), list) else []
    for phase in phases:
        if str(phase.get("name", "")) == phase_name:
            return phase
    return phases[0] if phases else {}


def _work_order_tool_steps(phase: Dict[str, Any], plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    phase_name = str(phase.get("name", ""))
    tools = phase.get("tools", []) if isinstance(phase.get("tools"), list) else []
    if phase_name == "asset_generation":
        return [
            {
                "tool": "gen_tripo_text_to_model",
                "arguments": {
                    "prompt": prompt.get("prompt"),
                    "texture": prompt.get("texture", True),
                    "pbr": prompt.get("pbr", True),
                    "smart_low_poly": prompt.get("smart_low_poly", True),
                    "face_limit": prompt.get("face_limit", 12000),
                    "session_name": plan.get("session_name", "ide-companion"),
                    "confirm_spend": True,
                },
                "record_as": prompt.get("name", prompt.get("role", "generated_asset")),
            }
            for prompt in phase.get("asset_prompts", [])
        ]
    if phase_name in {"session_preflight", "mechanic_design"} and isinstance(phase.get("request"), dict) and tools:
        return [{"tool": tools[0], "arguments": phase["request"], "record_as": phase_name}]
    return [{"tool": tool, "arguments": {}, "record_as": f"{phase_name}:{tool}"} for tool in tools]


def _work_order_feature_template(phase_name: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    mechanic_plan = plan.get("mechanic_plan") if isinstance(plan.get("mechanic_plan"), dict) else {}
    template = mechanic_plan.get("feature_template") if isinstance(mechanic_plan.get("feature_template"), dict) else {}
    if template.get("schema") != "unreal_mcp_gameplay_feature_template.v1":
        return {}
    if phase_name not in {"mechanic_design", "editor_implementation", "runtime_verification"}:
        return {}
    if phase_name == "mechanic_design":
        return {
            "schema": template["schema"],
            "template_name": template.get("template_name", ""),
            "display_name": template.get("display_name", ""),
            "asset_list": template.get("asset_list", []),
            "generated_animation_prompts": mechanic_plan.get("generated_animation_prompts", []),
            "estimated_uthana_motion_seconds": mechanic_plan.get("estimated_uthana_motion_seconds", 0),
            "animation_system_hook": mechanic_plan.get("system_hooks", {}).get("animation", {}) if isinstance(mechanic_plan.get("system_hooks"), dict) else {},
            "ownership_split": template.get("ownership_split", {}),
            "editor_operation_checklist": template.get("editor_operation_checklist", []),
            "completion_contract": template.get("completion_contract", {}),
            "evidence_requirements": template.get("evidence_requirements", []),
            "stop_conditions": template.get("stop_conditions", []),
        }
    if phase_name == "editor_implementation":
        return {
            "schema": template["schema"],
            "template_name": template.get("template_name", ""),
            "display_name": template.get("display_name", ""),
            "asset_list": template.get("asset_list", []),
            "generated_animation_prompts": mechanic_plan.get("generated_animation_prompts", []),
            "estimated_uthana_motion_seconds": mechanic_plan.get("estimated_uthana_motion_seconds", 0),
            "animation_system_hook": mechanic_plan.get("system_hooks", {}).get("animation", {}) if isinstance(mechanic_plan.get("system_hooks"), dict) else {},
            "ownership_split": template.get("ownership_split", {}),
            "graph_component_operations": template.get("graph_component_operations", []),
            "editor_operation_checklist": template.get("editor_operation_checklist", []),
            "completion_contract": template.get("completion_contract", {}),
            "compile_readback_checks": template.get("compile_readback_checks", []),
            "repair_instructions": template.get("repair_instructions", []),
            "evidence_requirements": template.get("evidence_requirements", []),
            "stop_conditions": template.get("stop_conditions", []),
        }
    return {
        "schema": template["schema"],
        "template_name": template.get("template_name", ""),
        "display_name": template.get("display_name", ""),
        "asset_list": template.get("asset_list", []),
        "generated_animation_prompts": mechanic_plan.get("generated_animation_prompts", []),
        "estimated_uthana_motion_seconds": mechanic_plan.get("estimated_uthana_motion_seconds", 0),
        "animation_system_hook": mechanic_plan.get("system_hooks", {}).get("animation", {}) if isinstance(mechanic_plan.get("system_hooks"), dict) else {},
        "pie_validation": template.get("pie_validation", []),
        "completion_contract": template.get("completion_contract", {}),
        "repair_instructions": template.get("repair_instructions", []),
        "evidence_requirements": template.get("evidence_requirements", []),
        "stop_conditions": template.get("stop_conditions", []),
    }


def build_ide_companion_work_order(
    session_plan: Dict[str, Any],
    companion_status: Optional[Dict[str, Any]] = None,
    target_phase: str = "",
    readiness_report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    plan = _coerce_mapping(session_plan)
    status = _extract_status_payload(companion_status)
    if not status:
        status = build_ide_companion_status(
            session_plan=plan,
            readiness_report=_coerce_mapping(readiness_report),
        )
    blocking_gates = [str(gate) for gate in status.get("blocking_gates", []) if str(gate).strip()]
    selected_phase_name = str(target_phase or status.get("next_phase") or "").strip()
    phase = _find_phase(plan, selected_phase_name)
    selected_phase_name = str(phase.get("name", selected_phase_name))
    phase_status = next(
        (item for item in status.get("phase_status", []) if item.get("name") == selected_phase_name),
        {},
    )
    requires_spend = bool(phase.get("spend_required"))
    requires_editor = bool(phase.get("editor_required"))
    prerequisites = []
    if blocking_gates:
        prerequisites.append({"name": "resolve_blocking_gates", "detail": ", ".join(blocking_gates)})
    if requires_spend:
        prerequisites.append({"name": "explicit_spend_approval", "detail": "confirm_spend=True only after user approval and funded API wallet"})
    if requires_editor:
        prerequisites.append({"name": "unreal_bridge_reachable", "detail": "Unreal Editor must be listening before mutation"})
    if selected_phase_name == "runtime_verification":
        prerequisites.append({"name": "editor_implementation_complete", "detail": "Blueprint compile reports and graph readback must already be recorded"})

    tool_steps = _work_order_tool_steps(phase, plan)
    stop_conditions = [
        "Stop before any paid Tripo task if api_wallet_has_credits or spend_confirmed is blocked.",
        "Stop before editor mutation if unreal_bridge_reachable is blocked.",
        "Stop on any tool error and compile a new IDE companion status receipt before retrying.",
        "Stop before calling the phase complete unless the evidence_to_collect items are recorded.",
    ]
    evidence_by_phase = {
        "orient_to_project": ["project context summary", "KB search result ids", "risk evaluation"],
        "session_preflight": ["readiness report", "blocking_gates list", "budget and wallet state"],
        "mechanic_design": ["gameplay mechanic plan", "validation gates", "tool sequence"],
        "asset_generation": ["task ids", "wait/status results", "imported asset paths or placeholder decision"],
        "editor_implementation": ["Blueprint compile reports", "graph readback summaries", "created asset paths"],
        "runtime_verification": ["PIE log", "viewport screenshot", "runtime feedback observations"],
        "developer_handoff": ["vertical slice report", "source control status", "open risks"],
    }
    acceptance_by_phase = {
        "orient_to_project": ["Project context and relevant KB guidance are summarized before mutation."],
        "session_preflight": ["Readiness report is current and every blocker has an owner or fallback."],
        "mechanic_design": ["Mechanic plan schema is valid and hooks cover HUD/input/AI/save/replication as needed."],
        "asset_generation": ["Every paid task has explicit approval, task status, and import or placeholder evidence."],
        "editor_implementation": ["Each Blueprint pass compiles and graph readback matches the planned loop."],
        "runtime_verification": ["PIE evidence shows the input-to-feedback loop or records a focused repair item."],
        "developer_handoff": ["Report lists what changed, what is proven, and what remains risky."],
    }
    feature_template_work = _work_order_feature_template(selected_phase_name, plan)
    evidence_to_collect = list(evidence_by_phase.get(selected_phase_name, ["tool result JSON", "human-readable summary"]))
    acceptance_criteria = list(acceptance_by_phase.get(selected_phase_name, ["Phase evidence is recorded and status receipt is updated."]))
    if feature_template_work:
        for item in feature_template_work.get("evidence_requirements", []):
            text = str(item)
            if text and text not in evidence_to_collect:
                evidence_to_collect.append(text)
        for item in feature_template_work.get("stop_conditions", []):
            text = str(item)
            if text and text not in stop_conditions:
                stop_conditions.append(text)
        if selected_phase_name == "editor_implementation":
            acceptance_criteria.append("Feature-template graph/component operations are reflected in compile and readback evidence.")
        elif selected_phase_name == "runtime_verification":
            acceptance_criteria.append("Feature-template PIE validation steps are proven or converted into focused repair instructions.")
        elif selected_phase_name == "mechanic_design":
            acceptance_criteria.append("Feature-template ownership split and asset list are reviewed before editor mutation.")
    return {
        "schema": "unreal_mcp_ide_companion_work_order.v1",
        "session_name": plan.get("session_name", ""),
        "project_brief": plan.get("project_brief", ""),
        "target_phase": selected_phase_name,
        "phase_state": phase_status.get("state", "unknown"),
        "goal": phase.get("goal", ""),
        "gate": phase.get("gate", ""),
        "blocking_gates": blocking_gates,
        "prerequisites": prerequisites,
        "tool_steps": tool_steps,
        "feature_template_work": feature_template_work,
        "evidence_to_collect": evidence_to_collect,
        "acceptance_criteria": acceptance_criteria,
        "stop_conditions": stop_conditions,
        "after_completion": {
            "tool": "skill_compile_ide_companion_status",
            "reason": "Refresh phase state, blockers, and missing evidence after completing or stopping this work order.",
        },
        "safe_to_execute_now": not blocking_gates and phase_status.get("state") != "blocked",
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
    }


def validate_ide_companion_work_order(work_order: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if work_order.get("schema") != "unreal_mcp_ide_companion_work_order.v1":
        errors.append("schema must be unreal_mcp_ide_companion_work_order.v1")
    if not str(work_order.get("target_phase", "")).strip():
        errors.append("target_phase is required")
    if not isinstance(work_order.get("tool_steps"), list):
        errors.append("tool_steps must be a list")
    if not isinstance(work_order.get("stop_conditions"), list) or not work_order["stop_conditions"]:
        errors.append("stop_conditions are required")
    if not isinstance(work_order.get("after_completion"), dict):
        errors.append("after_completion is required")
    return errors


def skill_compile_ide_companion_work_order(
    session_plan: Any,
    companion_status: Any = None,
    target_phase: str = "",
    readiness_report: Any = None,
) -> Dict[str, Any]:
    """Compile the next no-spend executable work order for an IDE companion session."""

    t0 = time.monotonic()
    inputs = {
        "session_plan": session_plan,
        "companion_status": companion_status,
        "target_phase": target_phase,
        "readiness_report": readiness_report,
    }
    plan = _coerce_mapping(session_plan)
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        return _work_order_structured(
            success=False,
            stage="invalid_session_plan",
            message="session_plan must be an unreal_mcp_ide_companion_session_plan.v1 object or JSON string",
            inputs=inputs,
            errors=["session_plan must use unreal_mcp_ide_companion_session_plan.v1"],
            t0=t0,
        )
    work_order = build_ide_companion_work_order(
        session_plan=plan,
        companion_status=companion_status,
        target_phase=target_phase,
        readiness_report=readiness_report,
    )
    errors = validate_ide_companion_work_order(work_order)
    if errors:
        return _work_order_structured(
            success=False,
            stage="work_order_validation_failed",
            message="IDE companion work order failed validation",
            inputs=inputs,
            outputs={"work_order": work_order},
            errors=errors,
            t0=t0,
        )
    return _work_order_structured(
        success=True,
        stage="work_order_ready",
        message="IDE companion work order compiled; no Unreal mutation, network call, or paid provider request was sent",
        inputs=inputs,
        outputs={
            "work_order": work_order,
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
        },
        warnings=["Execute the listed tool_steps only after prerequisites are satisfied; refresh status after stopping or completing the work order."],
        t0=t0,
    )


def _ide_companion_ledger_path(session_name: str) -> Path:
    safe_session = _safe_name(session_name or "ide-companion", "ide-companion")
    return _REPO_ROOT / ".mcp_artifacts" / "ide_companion_sessions" / f"{safe_session}.json"


def _ide_companion_asset_lifecycle_path(session_name: str, manifest_name: str = "asset_lifecycle") -> Path:
    safe_session = _safe_name(session_name or "ide-companion", "ide-companion")
    safe_manifest = _safe_name(manifest_name or "asset_lifecycle", "asset_lifecycle")
    return _REPO_ROOT / ".mcp_artifacts" / "ide_companion_sessions" / f"{safe_session}_{safe_manifest}.json"


def _load_ide_companion_ledger(session_name: str) -> Dict[str, Any]:
    path = _ide_companion_ledger_path(session_name)
    if not path.exists():
        return {
            "schema": "unreal_mcp_ide_companion_ledger.v1",
            "session_name": _safe_name(session_name or "ide-companion", "ide-companion"),
            "events": [],
            "evidence": {},
            "latest_status": {},
            "latest_work_order": {},
            "latest_readiness": {},
        }
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        loaded = {}
    if loaded.get("schema") != "unreal_mcp_ide_companion_ledger.v1":
        loaded["schema"] = "unreal_mcp_ide_companion_ledger.v1"
    loaded.setdefault("session_name", _safe_name(session_name or "ide-companion", "ide-companion"))
    loaded.setdefault("events", [])
    loaded.setdefault("evidence", {})
    loaded.setdefault("latest_status", {})
    loaded.setdefault("latest_work_order", {})
    loaded.setdefault("latest_readiness", {})
    return loaded


def _load_ide_companion_ledger_from_path(ledger_path: str) -> Dict[str, Any]:
    path = Path(str(ledger_path or "")).expanduser()
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if loaded.get("schema") != "unreal_mcp_ide_companion_ledger.v1":
        return {}
    loaded.setdefault("events", [])
    loaded.setdefault("evidence", {})
    loaded.setdefault("latest_status", {})
    loaded.setdefault("latest_work_order", {})
    loaded.setdefault("latest_readiness", {})
    loaded["_ledger_path"] = str(path)
    return loaded


def _save_ide_companion_ledger(ledger: Dict[str, Any]) -> Path:
    path = _ide_companion_ledger_path(str(ledger.get("session_name", "ide-companion")))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _ledger_evidence_map(ledger: Dict[str, Any]) -> Dict[str, Any]:
    evidence: Dict[str, Any] = {}
    for phase_name, records in (ledger.get("evidence") or {}).items():
        if not isinstance(records, list):
            continue
        artifacts: List[str] = []
        summaries: List[str] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            artifacts.extend([str(item) for item in record.get("artifacts", []) if str(item).strip()])
            if str(record.get("summary", "")).strip():
                summaries.append(str(record["summary"]))
        evidence[str(phase_name)] = {
            "complete": bool(records),
            "artifacts": artifacts,
            "evidence": summaries,
        }
    return evidence


def skill_record_ide_companion_evidence(
    session_plan: Any,
    phase_name: str,
    evidence_type: str = "note",
    summary: str = "",
    artifacts: Optional[List[str]] = None,
    readiness_report: Any = None,
    companion_status: Any = None,
    work_order: Any = None,
    current_blockers: Any = None,
) -> Dict[str, Any]:
    """Record phase evidence to a durable local IDE companion ledger."""

    t0 = time.monotonic()
    inputs = {
        "session_plan": session_plan,
        "phase_name": phase_name,
        "evidence_type": evidence_type,
        "summary": summary,
        "artifacts": artifacts,
        "readiness_report": readiness_report,
        "companion_status": companion_status,
        "work_order": work_order,
        "current_blockers": current_blockers,
    }
    plan = _coerce_mapping(session_plan)
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        return _ledger_structured(
            success=False,
            stage="invalid_session_plan",
            message="session_plan must be an unreal_mcp_ide_companion_session_plan.v1 object or JSON string",
            inputs=inputs,
            errors=["session_plan must use unreal_mcp_ide_companion_session_plan.v1"],
            t0=t0,
        )
    safe_phase = str(phase_name or "").strip()
    if not safe_phase:
        return _ledger_structured(
            success=False,
            stage="invalid_phase_name",
            message="phase_name is required",
            inputs=inputs,
            errors=["phase_name is required"],
            t0=t0,
        )
    known_phases = {str(phase.get("name", "")) for phase in plan.get("phases", []) if isinstance(phase, dict)}
    if safe_phase not in known_phases:
        return _ledger_structured(
            success=False,
            stage="unknown_phase",
            message=f"phase_name must match a session phase: {safe_phase}",
            inputs=inputs,
            errors=[f"unknown phase: {safe_phase}"],
            outputs={"known_phases": sorted(known_phases)},
            t0=t0,
        )

    session_name = str(plan.get("session_name", "ide-companion"))
    ledger = _load_ide_companion_ledger(session_name)
    ledger["project_brief"] = plan.get("project_brief", "")
    ledger["session_plan"] = plan
    readiness = _coerce_mapping(readiness_report)
    status = _extract_status_payload(companion_status)
    work = _coerce_mapping(work_order)
    if readiness:
        ledger["latest_readiness"] = readiness
    if status:
        ledger["latest_status"] = status
    if work:
        outputs = work.get("outputs", {}) if isinstance(work.get("outputs"), dict) else {}
        ledger["latest_work_order"] = outputs.get("work_order", work)

    event = {
        "phase_name": safe_phase,
        "evidence_type": str(evidence_type or "note"),
        "summary": str(summary or ""),
        "artifacts": [str(item) for item in (artifacts or []) if str(item).strip()],
        "timestamp_unix": int(time.time()),
    }
    ledger.setdefault("events", []).append(event)
    ledger.setdefault("evidence", {}).setdefault(safe_phase, []).append(event)
    evidence_map = _ledger_evidence_map(ledger)
    completed_phases = sorted(evidence_map.keys())
    updated_status = build_ide_companion_status(
        session_plan=plan,
        readiness_report=ledger.get("latest_readiness", {}),
        completed_phases=completed_phases,
        evidence=evidence_map,
        current_blockers=_coerce_string_list(current_blockers),
    )
    ledger["latest_status"] = updated_status
    ledger_path = _save_ide_companion_ledger(ledger)
    return _ledger_structured(
        success=True,
        stage="evidence_recorded",
        message="IDE companion evidence recorded and status refreshed",
        inputs=inputs,
        outputs={
            "schema": "unreal_mcp_ide_companion_evidence_record.v1",
            "ledger_path": str(ledger_path),
            "ledger": ledger,
            "updated_status": updated_status,
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
        },
        warnings=["Use updated_status.next_action or compile a fresh work order before continuing."],
        t0=t0,
    )


def skill_resume_ide_companion_session(
    session_name: str = "ide-companion",
    ledger_path: str = "",
    readiness_report: Any = None,
    current_blockers: Any = None,
) -> Dict[str, Any]:
    """Resume an IDE companion session from its durable local evidence ledger."""

    t0 = time.monotonic()
    inputs = {
        "session_name": session_name,
        "ledger_path": ledger_path,
        "readiness_report": readiness_report,
        "current_blockers": current_blockers,
    }
    ledger = _load_ide_companion_ledger_from_path(ledger_path) if str(ledger_path or "").strip() else _load_ide_companion_ledger(session_name)
    if not ledger or not ledger.get("events"):
        return _resume_structured(
            success=False,
            stage="ledger_not_found",
            message="No IDE companion ledger was found for the requested session",
            inputs=inputs,
            errors=["ledger not found or empty"],
            outputs={"expected_path": str(_ide_companion_ledger_path(session_name))},
            t0=t0,
        )
    plan = _coerce_mapping(ledger.get("session_plan"))
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        return _resume_structured(
            success=False,
            stage="ledger_missing_session_plan",
            message="Ledger does not contain a valid session plan",
            inputs=inputs,
            errors=["ledger missing unreal_mcp_ide_companion_session_plan.v1"],
            outputs={"ledger_schema": ledger.get("schema", "")},
            t0=t0,
        )
    readiness = _coerce_mapping(readiness_report) or _coerce_mapping(ledger.get("latest_readiness"))
    evidence_map = _ledger_evidence_map(ledger)
    completed_phases = sorted(evidence_map.keys())
    status = build_ide_companion_status(
        session_plan=plan,
        readiness_report=readiness,
        completed_phases=completed_phases,
        evidence=evidence_map,
        current_blockers=_coerce_string_list(current_blockers),
    )
    work_order = build_ide_companion_work_order(
        session_plan=plan,
        companion_status=status,
        readiness_report=readiness,
    )
    ledger["latest_status"] = status
    ledger["latest_work_order"] = work_order
    if readiness:
        ledger["latest_readiness"] = readiness
    saved_path = _save_ide_companion_ledger(ledger)
    return _resume_structured(
        success=True,
        stage="session_resumed",
        message="IDE companion session resumed from local evidence ledger",
        inputs=inputs,
        outputs={
            "schema": "unreal_mcp_ide_companion_resume.v1",
            "ledger_path": str(saved_path),
            "session_name": ledger.get("session_name", plan.get("session_name", "")),
            "event_count": len(ledger.get("events", [])),
            "completed_phases": completed_phases,
            "status": status,
            "work_order": work_order,
            "next_action": status.get("next_action", {}),
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
        },
        warnings=["Use outputs.work_order for the next executable phase, then record new evidence back to the ledger."],
        t0=t0,
    )


def _dashboard_cards(plan: Dict[str, Any], status: Dict[str, Any], work_order: Dict[str, Any], ledger: Dict[str, Any], ledger_path: str) -> List[Dict[str, Any]]:
    mechanic = plan.get("mechanic_plan", {}) if isinstance(plan.get("mechanic_plan"), dict) else {}
    hooks = mechanic.get("system_hooks", {}) if isinstance(mechanic.get("system_hooks"), dict) else {}
    hook_summary = [
        name
        for name, hook in hooks.items()
        if isinstance(hook, dict) and hook.get("needed")
    ]
    return [
        {
            "id": "readiness",
            "title": "Readiness",
            "state": "ready" if status.get("readiness_ready") else "blocked",
            "lines": [
                f"blocking_gates: {', '.join(status.get('blocking_gates', [])) or 'none'}",
                f"paid_generation: {'ready' if status.get('ready_for_paid_generation') else 'not ready'}",
                f"editor_mutation: {'ready' if status.get('ready_for_editor_mutation') else 'not ready'}",
                f"runtime_verification: {'ready' if status.get('ready_for_runtime_verification') else 'not ready'}",
            ],
        },
        {
            "id": "progress",
            "title": "Session Progress",
            "state": "active",
            "lines": [
                f"completed_phases: {status.get('completed_phase_count', 0)}/{status.get('total_phase_count', 0)}",
                f"next_phase: {status.get('next_phase', '') or work_order.get('target_phase', '')}",
                f"ledger_events: {len(ledger.get('events', []))}",
                f"missing_evidence: {', '.join(status.get('missing_evidence', [])) or 'none'}",
            ],
        },
        {
            "id": "next_work",
            "title": "Next Work",
            "state": "ready" if work_order.get("safe_to_execute_now") else "blocked",
            "lines": [
                f"target_phase: {work_order.get('target_phase', '')}",
                f"tool_steps: {len(work_order.get('tool_steps', []))}",
                f"next_action: {status.get('next_action', {}).get('tool', '')}",
                f"stop_conditions: {len(work_order.get('stop_conditions', []))}",
            ],
        },
        {
            "id": "assets",
            "title": "Generated Assets",
            "state": "planned" if plan.get("generated_asset_prompts") else "placeholder",
            "lines": [
                f"prompt_count: {len(plan.get('generated_asset_prompts', []))}",
                f"estimated_tripo_credits: {plan.get('estimated_tripo_credits', 0)}",
                "policy: Smart Mesh, PBR, explicit spend approval",
            ],
        },
        {
            "id": "mechanic",
            "title": "Gameplay Mechanic",
            "state": mechanic.get("mechanic_kind", "planned"),
            "lines": [
                f"kind: {mechanic.get('mechanic_kind', '')}",
                f"blueprint_assets: {len(mechanic.get('blueprint_assets', [])) if isinstance(mechanic.get('blueprint_assets'), list) else 0}",
                f"hooks: {', '.join(hook_summary) or 'none'}",
            ],
        },
        {
            "id": "evidence",
            "title": "Evidence Ledger",
            "state": "recorded" if ledger.get("events") else "empty",
            "lines": [
                f"path: {ledger_path}",
                f"events: {len(ledger.get('events', []))}",
                f"evidence_phases: {', '.join(sorted((ledger.get('evidence') or {}).keys())) or 'none'}",
            ],
        },
    ]


def skill_compile_ide_companion_dashboard(
    session_name: str = "ide-companion",
    ledger_path: str = "",
    session_plan: Any = None,
    readiness_report: Any = None,
    current_blockers: Any = None,
) -> Dict[str, Any]:
    """Compile a no-spend display dashboard packet for the IDE companion."""

    t0 = time.monotonic()
    inputs = {
        "session_name": session_name,
        "ledger_path": ledger_path,
        "session_plan": session_plan,
        "readiness_report": readiness_report,
        "current_blockers": current_blockers,
    }
    ledger = _load_ide_companion_ledger_from_path(ledger_path) if str(ledger_path or "").strip() else _load_ide_companion_ledger(session_name)
    plan = _coerce_mapping(session_plan) or _coerce_mapping(ledger.get("session_plan"))
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        return _dashboard_structured(
            success=False,
            stage="missing_session_plan",
            message="Dashboard requires a session plan or a ledger containing one",
            inputs=inputs,
            errors=["session_plan must use unreal_mcp_ide_companion_session_plan.v1"],
            outputs={"expected_ledger_path": str(_ide_companion_ledger_path(session_name))},
            t0=t0,
        )
    readiness = _coerce_mapping(readiness_report) or _coerce_mapping(ledger.get("latest_readiness"))
    evidence_map = _ledger_evidence_map(ledger)
    completed_phases = sorted(evidence_map.keys())
    status = build_ide_companion_status(
        session_plan=plan,
        readiness_report=readiness,
        completed_phases=completed_phases,
        evidence=evidence_map,
        current_blockers=_coerce_string_list(current_blockers),
    )
    work_order = build_ide_companion_work_order(
        session_plan=plan,
        companion_status=status,
        readiness_report=readiness,
    )
    resolved_ledger_path = str(_ide_companion_ledger_path(str(plan.get("session_name", session_name))))
    if ledger.get("_ledger_path"):
        resolved_ledger_path = str(ledger["_ledger_path"])
    dashboard = {
        "schema": "unreal_mcp_ide_companion_dashboard.v1",
        "session_name": plan.get("session_name", session_name),
        "project_brief": plan.get("project_brief", ""),
        "ledger_path": resolved_ledger_path,
        "status": status,
        "work_order": work_order,
        "cards": _dashboard_cards(plan, status, work_order, ledger, resolved_ledger_path),
        "primary_action": status.get("next_action", {}),
        "command_palette": [
            "Start IDE Companion Session",
            "IDE Companion Readiness",
            "Update IDE Companion Status",
            "Generate IDE Companion Work Order",
            "Record IDE Companion Evidence",
            "Resume IDE Companion Session",
            "Show IDE Companion Dashboard",
            "Queue IDE Companion Editor Actions",
        ],
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
    }
    return _dashboard_structured(
        success=True,
        stage="dashboard_ready",
        message="IDE companion dashboard compiled; no Unreal mutation, network call, or paid provider request was sent",
        inputs=inputs,
        outputs={"dashboard": dashboard},
        warnings=["Render cards in the editor/chat surface, then follow dashboard.primary_action or dashboard.work_order."],
        t0=t0,
    )


def _extract_dashboard_payload(value: Any) -> Dict[str, Any]:
    raw = _coerce_mapping(value)
    if raw.get("schema") == "unreal_mcp_ide_companion_dashboard.v1":
        return raw
    outputs = raw.get("outputs") if isinstance(raw.get("outputs"), dict) else {}
    dashboard = outputs.get("dashboard") if isinstance(outputs.get("dashboard"), dict) else {}
    return dashboard if dashboard.get("schema") == "unreal_mcp_ide_companion_dashboard.v1" else {}


def _resolution_for_blocker(blocker: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    content_path = str(plan.get("content_path", "/Game/Generated/PlayableSlice"))
    if blocker == "api_wallet_has_credits":
        return {
            "blocker": blocker,
            "severity": "hard_for_paid_generation",
            "why_it_matters": "Tripo paid generation cannot start until the API wallet has credits.",
            "unblock_actions": [
                {"action": "Fund the Tripo API wallet", "evidence": "gen_compile_ide_companion_readiness shows api_wallet_has_credits ready"},
                {"action": "Keep confirm_spend=false until wallet is funded and user approves spend", "evidence": "credit guard remains unreserved"},
            ],
            "fallback_actions": [
                {"action": "Continue mechanic design with generated-asset prompts only", "tool": "skill_plan_gameplay_mechanic"},
                {"action": "Use placeholder meshes under the target content path", "tool": "create_blueprint", "content_path": f"{content_path}/Placeholders"},
                {"action": "Record the wallet blocker in the evidence ledger", "tool": "skill_record_ide_companion_evidence"},
            ],
        }
    if blocker == "unreal_bridge_reachable":
        return {
            "blocker": blocker,
            "severity": "hard_for_editor_mutation",
            "why_it_matters": "Blueprint, actor, PIE, and viewport tools require the Unreal MCP bridge.",
            "unblock_actions": [
                {"action": "Start Unreal Editor with the UnrealMCP plugin loaded", "evidence": "scripts/bridge_ping.py succeeds"},
                {"action": "Confirm the bridge is listening on 127.0.0.1:55655", "evidence": "readiness gate unreal_bridge_reachable is ready"},
            ],
            "fallback_actions": [
                {"action": "Continue offline planning and work-order compilation", "tool": "skill_compile_ide_companion_work_order"},
                {"action": "Prepare Blueprint/mechanic instructions without mutation", "tool": "skill_plan_gameplay_mechanic"},
                {"action": "Record bridge blocker in the evidence ledger", "tool": "skill_record_ide_companion_evidence"},
            ],
        }
    if blocker == "spend_confirmed":
        return {
            "blocker": blocker,
            "severity": "approval_required",
            "why_it_matters": "The companion must not submit paid provider tasks without explicit approval.",
            "unblock_actions": [
                {"action": "Review asset prompts and estimated credits with the developer", "evidence": "approved prompt list"},
                {"action": "Run paid task only with confirm_spend=true", "evidence": "task submission result includes task_id"},
            ],
            "fallback_actions": [
                {"action": "Keep working with prompt manifests and placeholders", "tool": "skill_compile_ide_companion_work_order"},
            ],
        }
    return {
        "blocker": blocker,
        "severity": "unknown",
        "why_it_matters": "The companion should stop and ask for a clearer resolution path.",
        "unblock_actions": [{"action": "Refresh readiness/status and inspect the blocker detail", "tool": "skill_compile_ide_companion_status"}],
        "fallback_actions": [{"action": "Record the blocker and stop this phase cleanly", "tool": "skill_record_ide_companion_evidence"}],
    }


def skill_compile_ide_companion_blocker_resolution(
    dashboard: Any = None,
    session_plan: Any = None,
    companion_status: Any = None,
    readiness_report: Any = None,
    preferred_strategy: str = "continue_with_placeholders",
) -> Dict[str, Any]:
    """Compile no-spend blocker resolution choices for an IDE companion session."""

    t0 = time.monotonic()
    inputs = {
        "dashboard": dashboard,
        "session_plan": session_plan,
        "companion_status": companion_status,
        "readiness_report": readiness_report,
        "preferred_strategy": preferred_strategy,
    }
    dash = _extract_dashboard_payload(dashboard)
    plan = _coerce_mapping(session_plan)
    status = _extract_status_payload(companion_status)
    if dash:
        plan = plan or _coerce_mapping(dash.get("session_plan"))
        status = status or _coerce_mapping(dash.get("status"))
    if not plan and dash:
        plan = {
            "schema": "unreal_mcp_ide_companion_session_plan.v1",
            "content_path": "/Game/Generated/PlayableSlice",
            "generated_asset_prompts": [],
            "mechanic_plan": {},
        }
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        return _blocker_structured(
            success=False,
            stage="missing_session_plan",
            message="Blocker resolution requires a session plan or dashboard context",
            inputs=inputs,
            errors=["session_plan must use unreal_mcp_ide_companion_session_plan.v1"],
            t0=t0,
        )
    if not status:
        status = build_ide_companion_status(
            session_plan=plan,
            readiness_report=_coerce_mapping(readiness_report),
        )
    blockers = [str(item) for item in status.get("blocking_gates", []) if str(item).strip()]
    resolutions = [_resolution_for_blocker(blocker, plan) for blocker in blockers]
    strategy = str(preferred_strategy or "continue_with_placeholders").strip().lower()
    if not blockers:
        recommended = {"strategy": "continue", "tool": status.get("next_action", {}).get("tool", "skill_compile_ide_companion_work_order"), "reason": "No blocking gates are present."}
    elif strategy == "stop":
        recommended = {"strategy": "stop_and_record", "tool": "skill_record_ide_companion_evidence", "reason": "Record blockers and stop before unsafe execution."}
    elif strategy == "unblock":
        recommended = {"strategy": "unblock_first", "tool": "gen_compile_ide_companion_readiness", "reason": "Resolve hard readiness gates before continuing."}
    else:
        recommended = {"strategy": "continue_with_placeholders", "tool": "skill_compile_ide_companion_work_order", "reason": "Continue no-spend design/mechanic work while paid generation or editor mutation is blocked."}
    resolution = {
        "schema": "unreal_mcp_ide_companion_blocker_resolution.v1",
        "blocking_gates": blockers,
        "preferred_strategy": strategy,
        "recommended_path": recommended,
        "resolutions": resolutions,
        "placeholder_policy": {
            "enabled_when": "api_wallet_has_credits is blocked or spend is not approved",
            "content_path": f"{plan.get('content_path', '/Game/Generated/PlayableSlice')}/Placeholders",
            "rules": [
                "Do not submit paid Tripo tasks.",
                "Keep generated-asset prompts in the ledger for later execution.",
                "Use placeholder Static Meshes/components only to prove gameplay logic.",
                "Record every placeholder decision as evidence.",
            ],
        },
        "bridge_offline_policy": {
            "enabled_when": "unreal_bridge_reachable is blocked",
            "rules": [
                "Do not call editor mutation tools.",
                "Continue with offline plans, work orders, and implementation instructions.",
                "Resume once scripts/bridge_ping.py succeeds.",
            ],
        },
        "next_actions": [
            recommended,
            {"tool": "skill_record_ide_companion_evidence", "reason": "Persist the chosen blocker resolution path."},
            {"tool": "skill_compile_ide_companion_dashboard", "reason": "Refresh the in-editor dashboard after resolving or recording blockers."},
        ],
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
    }
    return _blocker_structured(
        success=True,
        stage="blocker_resolution_ready",
        message="IDE companion blocker resolution compiled; no Unreal mutation, network call, or paid provider request was sent",
        inputs=inputs,
        outputs={"resolution": resolution},
        warnings=["Follow recommended_path and record the chosen path in the evidence ledger before continuing."],
        t0=t0,
    )


def _placeholder_shape_for_role(role: str) -> str:
    value = str(role or "").lower()
    if "enemy" in value or "character" in value or "hero" in value:
        return "capsule_plus_arrow"
    if "weapon" in value:
        return "elongated_box"
    if "marker" in value or "objective" in value:
        return "emissive_cylinder"
    if "pickup" in value or "collectible" in value or "resource" in value:
        return "small_cube"
    return "simple_cube"


def build_ide_companion_placeholder_manifest(
    session_plan: Dict[str, Any],
    placeholder_root: str = "",
) -> Dict[str, Any]:
    plan = _coerce_mapping(session_plan)
    base_path = str(placeholder_root or f"{plan.get('content_path', '/Game/Generated/PlayableSlice')}/Placeholders").rstrip("/")
    prompts = plan.get("generated_asset_prompts", []) if isinstance(plan.get("generated_asset_prompts"), list) else []
    placeholders = []
    replacement_map = []
    for index, prompt in enumerate(prompts, start=1):
        if not isinstance(prompt, dict):
            continue
        role = str(prompt.get("role") or prompt.get("name") or f"asset_{index}")
        safe_name = _safe_name(str(prompt.get("name") or role), f"Placeholder_{index}")
        asset_path = f"{base_path}/PH_{safe_name}"
        placeholders.append({
            "role": role,
            "placeholder_name": f"PH_{safe_name}",
            "asset_path": asset_path,
            "shape": _placeholder_shape_for_role(role),
            "material": "M_Placeholder_GameplayReadable",
            "label": role.replace("_", " ").title(),
            "purpose": "Prove gameplay silhouette, collision, and feedback before paid generation.",
        })
        replacement_map.append({
            "placeholder_asset_path": asset_path,
            "future_generated_asset_name": prompt.get("name", safe_name),
            "future_content_path": prompt.get("content_path", f"{plan.get('content_path', '/Game/Generated/PlayableSlice')}/Assets"),
            "tripo_prompt": prompt.get("prompt", ""),
            "smart_low_poly": bool(prompt.get("smart_low_poly", True)),
            "face_limit": int(prompt.get("face_limit", 12000) or 12000),
        })
    if not placeholders:
        placeholders.append({
            "role": "mechanic_focus",
            "placeholder_name": "PH_MechanicFocus",
            "asset_path": f"{base_path}/PH_MechanicFocus",
            "shape": "simple_cube",
            "material": "M_Placeholder_GameplayReadable",
            "label": "Mechanic Focus",
            "purpose": "Provide a visible gameplay proxy when no generated asset prompts are planned.",
        })
    return {
        "schema": "unreal_mcp_ide_companion_placeholder_manifest.v1",
        "session_name": plan.get("session_name", "ide-companion"),
        "project_brief": plan.get("project_brief", ""),
        "placeholder_root": base_path,
        "placeholder_assets": placeholders,
        "replacement_map": replacement_map,
        "tool_steps": [
            {"tool": "create_folder", "arguments": {"path": base_path}, "record_as": "placeholder_folder"},
            {"tool": "create_material", "arguments": {"asset_path": f"{base_path}/M_Placeholder_GameplayReadable", "color": [0.1, 0.45, 1.0, 1.0]}, "record_as": "placeholder_material"},
            {"tool": "create_blueprint", "arguments": {"content_path": base_path, "parent_class": "Actor"}, "repeat_for": "placeholder_assets"},
            {"tool": "add_component_to_blueprint", "arguments": {"component_type": "StaticMeshComponent"}, "repeat_for": "placeholder_assets"},
            {"tool": "compile_blueprint_and_report", "arguments": {}, "repeat_for": "placeholder_assets"},
        ],
        "evidence_to_collect": [
            "placeholder asset paths",
            "compile report for every placeholder Blueprint",
            "graph/component readback showing collision/mesh component",
            "ledger evidence that maps each placeholder to a future Tripo prompt",
        ],
        "replacement_policy": [
            "Do not delete placeholder evidence when generated assets arrive.",
            "Replace mesh references only after gen_tripo_import_to_project returns imported asset paths.",
            "Keep placeholder labels until viewport proof confirms generated asset readability.",
            "Record replacement in the IDE companion evidence ledger.",
        ],
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
    }


def skill_compile_ide_companion_placeholder_manifest(
    session_plan: Any,
    placeholder_root: str = "",
    blocker_resolution: Any = None,
) -> Dict[str, Any]:
    """Compile no-spend placeholder asset manifest for blocked generative work."""

    t0 = time.monotonic()
    inputs = {
        "session_plan": session_plan,
        "placeholder_root": placeholder_root,
        "blocker_resolution": blocker_resolution,
    }
    plan = _coerce_mapping(session_plan)
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        return _placeholder_structured(
            success=False,
            stage="invalid_session_plan",
            message="session_plan must be an unreal_mcp_ide_companion_session_plan.v1 object or JSON string",
            inputs=inputs,
            errors=["session_plan must use unreal_mcp_ide_companion_session_plan.v1"],
            t0=t0,
        )
    manifest = build_ide_companion_placeholder_manifest(plan, placeholder_root)
    resolution = _coerce_mapping(blocker_resolution)
    if resolution:
        outputs = resolution.get("outputs", {}) if isinstance(resolution.get("outputs"), dict) else {}
        manifest["blocker_resolution"] = outputs.get("resolution", resolution)
    return _placeholder_structured(
        success=True,
        stage="placeholder_manifest_ready",
        message="IDE companion placeholder manifest compiled; no Unreal mutation, network call, or paid provider request was sent",
        inputs=inputs,
        outputs={"manifest": manifest},
        warnings=["Use this manifest only while paid generation is blocked; record placeholder decisions in the evidence ledger."],
        t0=t0,
    )


def _provider_generation_contract(provider: str, task_type: str) -> Dict[str, Any]:
    normalized_provider = _safe_name(provider or "tripo", "tripo").lower()
    normalized_task_type = _safe_name(task_type or "text_to_model", "text_to_model").lower()
    if normalized_provider == "tripo":
        submit_tool = {
            "text_to_model": "gen_tripo_text_to_model",
            "image_to_model": "gen_tripo_image_to_model",
            "multiview_to_model": "gen_tripo_multiview_to_model",
        }.get(normalized_task_type, "gen_tripo_text_to_model")
        return {
            "provider": "tripo",
            "task_type": normalized_task_type,
            "submit_tool": submit_tool,
            "status_tool": "gen_tripo_wait_for_task",
            "download_tool": "gen_tripo_download_result",
            "import_tool": "gen_tripo_import_to_project",
            "credit_gate": "gen_tripo_get_credit_balance plus explicit confirm_spend=True",
            "public_mcp_tool_available": True,
            "planned_submit_tool": submit_tool,
            "unsupported_reason": "",
        }
    if normalized_provider == "uthana":
        supported_submit_tools = {
            "text_to_motion": "gen_uthana_text_to_motion",
            "video_to_motion": "gen_uthana_video_to_motion",
        }
        planned_submit_tools = {
            "text_to_motion": "gen_uthana_text_to_motion",
            "video_to_motion": "gen_uthana_video_to_motion",
            "retarget_motion": "gen_uthana_retarget_motion",
        }
        submit_tool = supported_submit_tools.get(normalized_task_type, "")
        planned_submit_tool = planned_submit_tools.get(normalized_task_type, f"gen_uthana_{normalized_task_type}")
        public_mcp_tool_available = bool(submit_tool)
        return {
            "provider": "uthana",
            "task_type": normalized_task_type,
            "submit_tool": submit_tool,
            "planned_submit_tool": planned_submit_tool,
            "status_tool": "gen_uthana_get_job" if normalized_task_type == "video_to_motion" else "gen_uthana_get_motion",
            "download_tool": "gen_uthana_download_motion",
            "import_tool": "gen_uthana_import_animation_to_project",
            "credit_gate": "UTHANA_API_KEY plus org motion allowance and explicit usage confirmation",
            "public_mcp_tool_available": public_mcp_tool_available,
            "unsupported_reason": "" if public_mcp_tool_available else f"Uthana {normalized_task_type} is planned provider capability but no public MCP submit tool is registered yet.",
        }
    planned_submit_tool = f"gen_{normalized_provider}_{normalized_task_type}"
    return {
        "provider": normalized_provider,
        "task_type": normalized_task_type,
        "submit_tool": "",
        "planned_submit_tool": planned_submit_tool,
        "status_tool": f"gen_{normalized_provider}_wait_for_task",
        "download_tool": f"gen_{normalized_provider}_download_result",
        "import_tool": f"gen_{normalized_provider}_import_to_project",
        "credit_gate": "provider-specific wallet or quota check plus explicit spend confirmation",
        "public_mcp_tool_available": False,
        "unsupported_reason": f"{normalized_provider} is a provider-neutral slot; register {planned_submit_tool} before execution.",
    }


def _generated_asset_quality_proof_contract(asset_id: str) -> Dict[str, Any]:
    return {
        "schema": "unreal_mcp_generated_asset_quality_proof_contract.v1",
        "asset_id": asset_id,
        "required_after_import": [
            "static_mesh_load_readback",
            "material_slot_count",
            "collision_readability_check",
            "viewport_thumbnail_or_screenshot",
            "ide_companion_ledger_event",
        ],
        "stop_if_missing": [
            "imported asset path is empty",
            "mesh load/readback evidence is missing",
            "material slot count is missing",
            "collision/readability check is missing",
            "viewport or thumbnail proof is missing",
            "IDE companion ledger evidence is missing",
        ],
        "evidence_tool": "skill_record_ide_companion_evidence",
        "review_tool": "chat_get_cockpit_overview",
    }


def _generated_animation_quality_proof_contract(animation_id: str) -> Dict[str, Any]:
    return {
        "schema": "unreal_mcp_generated_animation_quality_proof_contract.v1",
        "animation_id": animation_id,
        "required_after_import": [
            "animation_sequence_load_readback",
            "target_skeleton_or_retarget_asset",
            "animgraph_or_state_machine_reference",
            "pie_motion_playback_or_viewport_proof",
            "ide_companion_ledger_event",
        ],
        "stop_if_missing": [
            "motion id is empty after generation",
            "downloaded motion file path is missing",
            "imported Animation Sequence path is empty",
            "target skeleton or retarget asset evidence is missing",
            "AnimGraph or state machine reference evidence is missing",
            "PIE playback or viewport proof is missing",
            "IDE companion ledger evidence is missing",
        ],
        "evidence_tool": "gen_compile_generated_animation_evidence",
        "review_tool": "chat_get_cockpit_overview",
    }


def build_ide_companion_asset_lifecycle_manifest(
    session_plan: Dict[str, Any],
    placeholder_manifest: Any = None,
    preferred_provider: str = "tripo",
) -> Dict[str, Any]:
    plan = _coerce_mapping(session_plan)
    prompts = plan.get("generated_asset_prompts", []) if isinstance(plan.get("generated_asset_prompts"), list) else []
    animation_prompts = plan.get("generated_animation_prompts", []) if isinstance(plan.get("generated_animation_prompts"), list) else []
    placeholder = _extract_placeholder_manifest(placeholder_manifest)
    replacement_by_name: Dict[str, Dict[str, Any]] = {}
    for replacement in placeholder.get("replacement_map", []):
        if not isinstance(replacement, dict):
            continue
        future_name = str(replacement.get("future_generated_asset_name") or "")
        placeholder_path = str(replacement.get("placeholder_asset_path") or "")
        if future_name:
            replacement_by_name[_safe_name(future_name, future_name).lower()] = replacement
        if placeholder_path:
            replacement_by_name[_asset_object_name(placeholder_path).lower().replace("ph_", "", 1)] = replacement

    asset_records: List[Dict[str, Any]] = []
    for index, prompt in enumerate(prompts, start=1):
        if not isinstance(prompt, dict):
            continue
        name = _safe_name(str(prompt.get("name") or f"GeneratedAsset_{index}"), f"GeneratedAsset_{index}")
        role = str(prompt.get("role") or name)
        provider = str(prompt.get("provider") or preferred_provider or "tripo").lower()
        task_type = str(prompt.get("task_type") or "text_to_model")
        content_path = _normalize_content_folder(str(prompt.get("content_path") or f"{plan.get('content_path', '/Game/Generated/PlayableSlice')}/Assets"))
        contract = _provider_generation_contract(provider, task_type)
        replacement = replacement_by_name.get(name.lower(), {})
        placeholder_path = str(replacement.get("placeholder_asset_path") or "")
        asset_id = f"asset_{index:02d}"
        asset_records.append({
            "id": asset_id,
            "name": name,
            "role": role,
            "provider": contract["provider"],
            "task_type": contract["task_type"],
            "prompt": str(prompt.get("prompt") or ""),
            "target_content_path": content_path,
            "expected_import_path": f"{content_path}/{name}",
            "smart_low_poly": bool(prompt.get("smart_low_poly", True)),
            "face_limit": int(prompt.get("face_limit", 12000) or 12000),
            "provider_task": {
                "status": "not_submitted",
                "task_id": "",
                "submit_tool": contract["submit_tool"],
                "planned_submit_tool": contract.get("planned_submit_tool", contract["submit_tool"]),
                "status_tool": contract["status_tool"],
                "download_tool": contract["download_tool"],
                "import_tool": contract["import_tool"],
                "credit_gate": contract["credit_gate"],
                "requires_confirm_spend": True,
                "public_mcp_tool_available": bool(contract.get("public_mcp_tool_available", True)),
                "unsupported_reason": str(contract.get("unsupported_reason", "")),
            },
            "placeholder_replacement": {
                "has_placeholder": bool(placeholder_path),
                "placeholder_asset_path": placeholder_path,
                "replacement_policy": [
                    "Keep placeholder evidence in the ledger.",
                    "Replace mesh references only after import and viewport proof pass.",
                    "Record the generated asset path and replacement map update.",
                ],
            },
            "quality_gates": [
                "provider task status is success/final",
                "downloaded model file exists",
                "import path exists under /Game",
                "mesh loads in Unreal",
                "material slot count is reported",
                "collision/readability check is recorded",
                "viewport thumbnail or screenshot proof exists",
                "IDE companion ledger records import and replacement evidence",
            ],
            "quality_proof_contract": _generated_asset_quality_proof_contract(asset_id),
        })

    animation_records: List[Dict[str, Any]] = []
    for index, prompt in enumerate(animation_prompts, start=1):
        if not isinstance(prompt, dict):
            continue
        animation_id = f"animation_{index:02d}"
        name = _safe_name(str(prompt.get("name") or f"GeneratedMotion_{index}"), f"GeneratedMotion_{index}")
        role = str(prompt.get("role") or name)
        provider = str(prompt.get("provider") or "uthana").lower()
        task_type = str(prompt.get("task_type") or "text_to_motion")
        content_path = _normalize_content_folder(str(prompt.get("content_path") or f"{plan.get('content_path', '/Game/Generated/PlayableSlice')}/Animations"))
        contract = _provider_generation_contract(provider, task_type)
        video_file = str(
            prompt.get("video_file")
            or prompt.get("reference_video_file")
            or prompt.get("source_video_file")
            or ""
        )
        animation_records.append({
            "id": animation_id,
            "name": name,
            "role": role,
            "provider": contract["provider"],
            "task_type": contract["task_type"],
            "prompt": str(prompt.get("prompt") or ""),
            "video_file": video_file,
            "reference_video_file": video_file,
            "target_content_path": content_path,
            "expected_import_path": f"{content_path}/{name}",
            "target_skeleton": str(prompt.get("target_skeleton") or "UE5 Manny or project humanoid skeleton"),
            "format": str(prompt.get("format") or "fbx").lower(),
            "estimated_seconds": int(prompt.get("estimated_seconds", 0) or 0),
            "default_character_id": str(prompt.get("default_character_id") or "cXi2eAP19XwQ"),
            "animation_usage": str(prompt.get("animation_usage") or "Use only after import, retarget/readback, AnimGraph reference, PIE proof, and ledger evidence pass."),
            "provider_task": {
                "status": "not_submitted" if contract.get("public_mcp_tool_available", True) else "unsupported_task_type",
                "motion_id": "",
                "submit_tool": contract["submit_tool"],
                "planned_submit_tool": contract.get("planned_submit_tool", contract["submit_tool"]),
                "status_tool": contract["status_tool"],
                "download_tool": contract["download_tool"],
                "import_tool": contract["import_tool"],
                "credit_gate": contract["credit_gate"],
                "requires_confirm_spend": True,
                "public_mcp_tool_available": bool(contract.get("public_mcp_tool_available", True)),
                "unsupported_reason": str(contract.get("unsupported_reason", "")),
            },
            "quality_gates": [
                "Uthana motion request has explicit prompt and usage approval",
                "downloaded FBX/GLB/BVH motion file exists",
                "Animation Sequence imports under /Game",
                "target skeleton or retarget asset is recorded",
                "AnimGraph or state machine references the generated motion",
                "PIE log and viewport proof show the motion in gameplay context",
                "IDE companion ledger records animation import, retarget, and runtime evidence",
            ],
            "quality_proof_contract": _generated_animation_quality_proof_contract(animation_id),
        })

    unsupported_provider_tasks = []
    for record in asset_records + animation_records:
        provider_task = record.get("provider_task") if isinstance(record.get("provider_task"), dict) else {}
        if provider_task.get("public_mcp_tool_available", True):
            continue
        unsupported_provider_tasks.append({
            "id": record.get("id", ""),
            "name": record.get("name", ""),
            "provider": record.get("provider", ""),
            "task_type": record.get("task_type", ""),
            "planned_submit_tool": provider_task.get("planned_submit_tool", ""),
            "unsupported_reason": provider_task.get("unsupported_reason", ""),
        })

    return {
        "schema": "unreal_mcp_ide_companion_generated_asset_lifecycle.v1",
        "session_name": plan.get("session_name", "ide-companion"),
        "project_brief": plan.get("project_brief", ""),
        "provider_neutral": True,
        "preferred_provider": (preferred_provider or "tripo").lower(),
        "supported_provider_slots": ["tripo", "uthana", "future_provider"],
        "asset_count": len(asset_records),
        "assets": asset_records,
        "animation_asset_count": len(animation_records),
        "animation_assets": animation_records,
        "estimated_uthana_motion_seconds": sum(int(item.get("estimated_seconds", 0) or 0) for item in animation_records),
        "unsupported_provider_task_count": len(unsupported_provider_tasks),
        "unsupported_provider_task_preview": unsupported_provider_tasks[:5],
        "lifecycle_stages": [
            {"name": "prompt_manifest", "required": True, "evidence": "source prompt, role, target path, provider slot"},
            {"name": "credit_gate", "required": True, "evidence": "provider wallet/quota evidence and explicit spend confirmation"},
            {"name": "task_submission", "required": bool(asset_records), "evidence": "provider task id and request summary"},
            {"name": "status_wait", "required": bool(asset_records), "evidence": "final provider task status"},
            {"name": "download_import", "required": bool(asset_records), "evidence": "download path and imported /Game asset path"},
            {"name": "animation_motion_generation", "required": bool(animation_records), "evidence": "Uthana motion id, prompt, character, and usage approval"},
            {"name": "animation_retarget_import", "required": bool(animation_records), "evidence": "Animation Sequence path, skeleton/retarget readback, AnimGraph reference, and PIE proof"},
            {"name": "placeholder_fallback", "required": False, "evidence": "placeholder manifest or blocker resolution when generation is blocked"},
            {"name": "replacement_mapping", "required": bool(asset_records), "evidence": "placeholder-to-generated asset map"},
            {"name": "material_collision_pass", "required": bool(asset_records), "evidence": "material slots, collision/readability notes"},
            {"name": "viewport_proof", "required": bool(asset_records), "evidence": "thumbnail or viewport screenshot"},
            {"name": "ledger_evidence", "required": True, "evidence": "IDE companion evidence ledger event"},
        ],
        "fallback_policy": [
            "If provider auth, wallet, or spend confirmation is blocked, compile/use the placeholder manifest and continue no-spend gameplay proof.",
            "If Uthana auth or usage allowance is blocked, use existing marketplace/default animation clips and keep generated-motion prompts in the lifecycle manifest.",
            "If import or quality gates fail, keep the placeholder active and emit a repair work order.",
            "Never overwrite placeholder evidence when a generated asset replaces it.",
        ],
        "stop_conditions": [
            "provider key missing",
            "wallet/credit evidence missing",
            "confirm_spend is not explicitly true for paid submission",
            "Uthana key, org motion allowance, or usage confirmation is missing before motion generation",
            "public MCP submit tool is missing for the selected provider task type",
            "downloaded output missing or unsupported",
            "imported asset does not load",
            "viewport proof or ledger evidence is missing",
        ],
        "next_actions": [
            {"tool": "gen_compile_ide_companion_readiness", "reason": "Check provider, wallet, bridge, and session budget gates before generation."},
            {"tool": "skill_compile_ide_companion_placeholder_manifest", "reason": "Prepare no-spend placeholders if generation is blocked."},
            {"tool": "gen_uthana_text_to_motion", "reason": "Generate required humanoid animation clips after Uthana auth, allowance, and usage approval."},
            {"tool": "skill_record_ide_companion_evidence", "reason": "Record prompt, spend, import, replacement, and proof events."},
        ],
        "network_required": False,
        "unreal_editor_required": False,
        "spend_required": False,
        "future_provider_network_required": bool(asset_records or animation_records),
        "future_spend_required": bool(asset_records or animation_records),
    }


def skill_compile_ide_companion_asset_lifecycle_manifest(
    session_plan: Any,
    placeholder_manifest: Any = None,
    preferred_provider: str = "tripo",
    write_manifest: bool = False,
    manifest_name: str = "asset_lifecycle",
) -> Dict[str, Any]:
    """Compile a no-spend provider-neutral generated asset lifecycle manifest."""

    t0 = time.monotonic()
    inputs = {
        "session_plan": session_plan,
        "placeholder_manifest": placeholder_manifest,
        "preferred_provider": preferred_provider,
        "write_manifest": bool(write_manifest),
        "manifest_name": manifest_name,
    }
    plan = _coerce_mapping(session_plan)
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        return _asset_lifecycle_structured(
            success=False,
            stage="invalid_session_plan",
            message="session_plan must be an unreal_mcp_ide_companion_session_plan.v1 object or JSON string",
            inputs=inputs,
            errors=["session_plan must use unreal_mcp_ide_companion_session_plan.v1"],
            t0=t0,
        )

    manifest = build_ide_companion_asset_lifecycle_manifest(
        plan,
        placeholder_manifest=placeholder_manifest,
        preferred_provider=preferred_provider,
    )
    manifest_path = ""
    if write_manifest:
        path = _ide_companion_asset_lifecycle_path(str(manifest.get("session_name") or plan.get("session_name") or "ide-companion"), manifest_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        manifest_path = str(path)
    return _asset_lifecycle_structured(
        success=True,
        stage="asset_lifecycle_manifest_ready",
        message="IDE companion generated asset lifecycle manifest compiled; no Unreal mutation, network call, or paid provider request was sent",
        inputs=inputs,
        outputs={
            "manifest": manifest,
            "manifest_path": manifest_path,
            "manifest_written": bool(manifest_path),
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
        },
        warnings=["This manifest describes future provider/editor work only; run readiness and spend gates before any paid generation."],
        t0=t0,
    )


def _extract_placeholder_manifest(value: Any) -> Dict[str, Any]:
    raw = _coerce_mapping(value)
    if raw.get("schema") == "unreal_mcp_ide_companion_placeholder_manifest.v1":
        return raw
    outputs = raw.get("outputs") if isinstance(raw.get("outputs"), dict) else {}
    manifest = outputs.get("manifest") if isinstance(outputs.get("manifest"), dict) else {}
    return manifest if manifest.get("schema") == "unreal_mcp_ide_companion_placeholder_manifest.v1" else {}


def _extract_work_order_payload(value: Any) -> Dict[str, Any]:
    raw = _coerce_mapping(value)
    if raw.get("schema") == "unreal_mcp_ide_companion_work_order.v1":
        return raw
    outputs = raw.get("outputs") if isinstance(raw.get("outputs"), dict) else {}
    work_order = outputs.get("work_order") if isinstance(outputs.get("work_order"), dict) else {}
    return work_order if work_order.get("schema") == "unreal_mcp_ide_companion_work_order.v1" else {}


def _ide_companion_editor_queue_path(session_name: str, queue_name: str) -> Path:
    safe_session = _safe_name(session_name or "ide-companion", "ide-companion")
    safe_queue = _safe_name(queue_name or "editor_queue", "editor_queue")
    return _REPO_ROOT / ".mcp_artifacts" / "ide_companion_sessions" / f"{safe_session}_{safe_queue}.json"


def _placeholder_editor_actions(manifest: Dict[str, Any]) -> List[Dict[str, Any]]:
    placeholder_root = str(manifest.get("placeholder_root") or "/Game/Generated/PlayableSlice/Placeholders")
    actions: List[Dict[str, Any]] = [
        {
            "id": "create_placeholder_folder",
            "tool": "create_folder",
            "arguments": {"path": placeholder_root},
            "evidence_key": "placeholder_folder",
        },
        {
            "id": "create_placeholder_material",
            "tool": "create_material",
            "arguments": {
                "asset_path": f"{placeholder_root}/M_Placeholder_GameplayReadable",
                "color": [0.1, 0.45, 1.0, 1.0],
            },
            "evidence_key": "placeholder_material",
        },
    ]
    for index, placeholder in enumerate(manifest.get("placeholder_assets", []), start=1):
        if not isinstance(placeholder, dict):
            continue
        name = str(placeholder.get("placeholder_name") or f"PH_Placeholder_{index}")
        asset_path = str(placeholder.get("asset_path") or f"{placeholder_root}/{name}")
        label = str(placeholder.get("label") or name)
        actions.extend([
            {
                "id": f"create_blueprint_{index}",
                "tool": "create_blueprint",
                "arguments": {"content_path": placeholder_root, "blueprint_name": name, "parent_class": "Actor"},
                "evidence_key": asset_path,
            },
            {
                "id": f"add_visual_proxy_{index}",
                "tool": "add_component_to_blueprint",
                "arguments": {
                    "blueprint_path": asset_path,
                    "component_name": "VisualProxy",
                    "component_type": "StaticMeshComponent",
                    "label": label,
                    "placeholder_shape": placeholder.get("shape", "simple_cube"),
                },
                "evidence_key": asset_path,
            },
            {
                "id": f"compile_placeholder_{index}",
                "tool": "compile_blueprint_and_report",
                "arguments": {"blueprint_path": asset_path},
                "evidence_key": asset_path,
            },
        ])
    return actions


def build_ide_companion_editor_queue(
    session_plan: Dict[str, Any],
    companion_status: Any = None,
    work_order: Any = None,
    placeholder_manifest: Any = None,
    queue_name: str = "editor_queue",
) -> Dict[str, Any]:
    plan = _coerce_mapping(session_plan)
    status = _extract_status_payload(companion_status)
    work = _extract_work_order_payload(work_order)
    manifest = _extract_placeholder_manifest(placeholder_manifest)
    feature_template = work.get("feature_template_work") if isinstance(work.get("feature_template_work"), dict) else {}
    feature_operations = (
        feature_template.get("editor_operation_checklist")
        if isinstance(feature_template.get("editor_operation_checklist"), list)
        else []
    )
    next_feature_operation = next((row for row in feature_operations if isinstance(row, dict)), {})
    next_feature_proof = (
        next_feature_operation.get("operation_proof_contract")
        if isinstance(next_feature_operation.get("operation_proof_contract"), dict)
        else {}
    )
    blocking_gates = [str(gate) for gate in status.get("blocking_gates", []) if str(gate).strip()]
    bridge_blocked = "unreal_bridge_reachable" in blocking_gates or status.get("ready_for_editor_mutation") is False
    if manifest:
        actions = _placeholder_editor_actions(manifest)
        source = "placeholder_manifest"
        evidence_to_collect = list(manifest.get("evidence_to_collect", []))
        target_phase = "editor_implementation"
    elif work:
        actions = [
            {
                "id": f"work_order_step_{index}",
                "tool": str(step.get("tool", "")),
                "arguments": step.get("arguments", {}) if isinstance(step, dict) else {},
                "record_as": step.get("record_as", "") if isinstance(step, dict) else "",
            }
            for index, step in enumerate(work.get("tool_steps", []), start=1)
            if isinstance(step, dict) and str(step.get("tool", "")).strip()
        ]
        source = "work_order"
        evidence_to_collect = list(work.get("evidence_to_collect", []))
        target_phase = str(work.get("target_phase") or "editor_implementation")
    else:
        actions = []
        source = "empty"
        evidence_to_collect = ["queued action result JSON", "Blueprint compile report", "graph/component readback"]
        target_phase = "editor_implementation"

    session_name = str(plan.get("session_name", "ide-companion"))
    path = _ide_companion_editor_queue_path(session_name, queue_name)
    prerequisites = [
        {"name": "unreal_bridge_reachable", "detail": "scripts/bridge_ping.py must succeed before executing queued editor actions."},
        {"name": "current_status_receipt", "detail": "Refresh skill_compile_ide_companion_status immediately before execution."},
    ]
    if "api_wallet_has_credits" in blocking_gates:
        prerequisites.append({"name": "placeholder_mode", "detail": "Use placeholders only; do not submit paid Tripo tasks from this queue."})
    queue = {
        "schema": "unreal_mcp_ide_companion_editor_queue.v1",
        "session_name": session_name,
        "project_brief": plan.get("project_brief", ""),
        "queue_name": _safe_name(queue_name or "editor_queue", "editor_queue"),
        "queue_path": str(path),
        "source": source,
        "target_phase": target_phase,
        "can_execute_now": bool(actions) and not bridge_blocked,
        "bridge_required": True,
        "bridge_blocked": bool(bridge_blocked),
        "blocking_gates": blocking_gates,
        "prerequisites": prerequisites,
        "actions": actions,
        "feature_template": {
            "schema": str(feature_template.get("schema", "")),
            "template_name": str(feature_template.get("template_name", "")),
            "display_name": str(feature_template.get("display_name", "")),
            "editor_operation_count": len(feature_operations),
            "next_operation_id": str(next_feature_operation.get("id", "")),
            "next_operation_type": str(next_feature_operation.get("operation_type", "")),
            "next_operation_summary": str(next_feature_operation.get("summary", "")),
            "next_operation_tool_candidates": [
                str(tool)
                for tool in (
                    next_feature_operation.get("tool_candidates")
                    if isinstance(next_feature_operation.get("tool_candidates"), list)
                    else []
                )
                if str(tool).strip()
            ][:8],
            "next_operation_required_before": [
                str(item)
                for item in (
                    next_feature_proof.get("required_before")
                    if isinstance(next_feature_proof.get("required_before"), list)
                    else []
                )
                if str(item).strip()
            ][:8],
            "next_operation_required_after": [
                str(item)
                for item in (
                    next_feature_proof.get("required_after")
                    if isinstance(next_feature_proof.get("required_after"), list)
                    else []
                )
                if str(item).strip()
            ][:8],
            "next_operation_stop_if_missing": [
                str(item)
                for item in (
                    next_feature_proof.get("stop_if_missing")
                    if isinstance(next_feature_proof.get("stop_if_missing"), list)
                    else []
                )
                if str(item).strip()
            ][:8],
        },
        "evidence_to_collect": evidence_to_collect or ["tool result JSON", "compile/readback evidence"],
        "stop_conditions": [
            "Stop before executing any action if scripts/bridge_ping.py fails.",
            "Stop on the first editor tool error and record the queue state as evidence.",
            "Stop before paid Tripo generation; this queue is editor-only and no-spend.",
            "Stop before marking the phase complete unless all evidence_to_collect items are recorded.",
        ],
        "after_execution": [
            {"tool": "skill_record_ide_companion_evidence", "phase_name": target_phase, "reason": "Persist queue execution proof and artifacts."},
            {"tool": "skill_compile_ide_companion_dashboard", "reason": "Refresh the IDE companion dashboard after queue execution or stop."},
        ],
        "network_required": False,
        "unreal_editor_required": True,
        "spend_required": False,
    }
    return queue


def validate_ide_companion_editor_queue(queue: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if queue.get("schema") != "unreal_mcp_ide_companion_editor_queue.v1":
        errors.append("schema must be unreal_mcp_ide_companion_editor_queue.v1")
    if not str(queue.get("session_name", "")).strip():
        errors.append("session_name is required")
    if not isinstance(queue.get("actions"), list):
        errors.append("actions must be a list")
    if not isinstance(queue.get("prerequisites"), list) or not queue["prerequisites"]:
        errors.append("prerequisites are required")
    if not isinstance(queue.get("stop_conditions"), list) or not queue["stop_conditions"]:
        errors.append("stop_conditions are required")
    return errors


def skill_compile_ide_companion_editor_queue(
    session_plan: Any,
    companion_status: Any = None,
    work_order: Any = None,
    placeholder_manifest: Any = None,
    queue_name: str = "editor_queue",
) -> Dict[str, Any]:
    """Compile and persist a bridge-gated editor action queue for an IDE companion session."""

    t0 = time.monotonic()
    inputs = {
        "session_plan": session_plan,
        "companion_status": companion_status,
        "work_order": work_order,
        "placeholder_manifest": placeholder_manifest,
        "queue_name": queue_name,
    }
    plan = _coerce_mapping(session_plan)
    if plan.get("schema") != "unreal_mcp_ide_companion_session_plan.v1":
        return _editor_queue_structured(
            success=False,
            stage="invalid_session_plan",
            message="session_plan must be an unreal_mcp_ide_companion_session_plan.v1 object or JSON string",
            inputs=inputs,
            errors=["session_plan must use unreal_mcp_ide_companion_session_plan.v1"],
            t0=t0,
        )
    queue = build_ide_companion_editor_queue(
        session_plan=plan,
        companion_status=companion_status,
        work_order=work_order,
        placeholder_manifest=placeholder_manifest,
        queue_name=queue_name,
    )
    errors = validate_ide_companion_editor_queue(queue)
    if errors:
        return _editor_queue_structured(
            success=False,
            stage="editor_queue_validation_failed",
            message="IDE companion editor queue failed validation",
            inputs=inputs,
            outputs={"queue": queue},
            errors=errors,
            t0=t0,
        )
    path = Path(queue["queue_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(queue, indent=2, sort_keys=True), encoding="utf-8")
    return _editor_queue_structured(
        success=True,
        stage="editor_queue_ready",
        message="IDE companion editor queue compiled and written; no Unreal mutation, network call, or paid provider request was sent",
        inputs=inputs,
        outputs={
            "queue": queue,
            "queue_path": str(path),
            "network_required": False,
            "unreal_editor_required": False,
            "spend_required": False,
        },
        warnings=["Run scripts/bridge_ping.py and refresh status before executing any queued editor action."],
        t0=t0,
    )


def _load_schema() -> Dict[str, Any]:
    try:
        return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Failed to load playable slice schema: %s", exc)
        return {}


def _asset_payload(asset: Dict[str, Any], model_version: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "type": "text_to_model",
        "prompt": asset["prompt"],
        "texture": bool(asset.get("texture", True)),
        "pbr": bool(asset.get("pbr", True)),
        "texture_quality": asset.get("texture_quality", "standard"),
        "face_limit": int(asset.get("face_limit", 12000)),
    }
    if model_version:
        payload["model_version"] = model_version
    return payload


def _submit_tripo_asset_tasks(plan: Dict[str, Any], session_name: str, confirm_spend: bool) -> Dict[str, Any]:
    from tools import generative_tools as gen

    key_state = gen._resolve_tripo_api_key()
    if not key_state.get("configured"):
        return {
            "success": False,
            "stage": "auth_required",
            "message": "TRIPO_API_KEY is required before playable-slice asset generation",
            "outputs": {"key_state": key_state},
            "warnings": [],
            "errors": ["Configure TRIPO_API_KEY in the environment or Saved/MCPChat/secrets.json."],
        }

    settings = gen._load_generative_settings()
    model_version = gen._clean_model_version(str(settings.get("default_model_version", "")))
    payloads = [_asset_payload(asset, model_version) for asset in plan["assets"]]
    estimated_credits = sum(gen._estimate_tripo_credits("text_to_model", payload) for payload in payloads)
    credit_guard = gen._check_and_reserve_credit_budget(
        estimated_credits=estimated_credits,
        session_name=session_name,
        operation="skill_generate_playable_slice",
        confirm_spend=confirm_spend,
        reserve_credits=True,
    )
    if not credit_guard["approved"]:
        return {
            "success": False,
            "stage": "spend_confirmation_required" if credit_guard["confirm_required"] else "budget_exceeded",
            "message": "Playable-slice Tripo generation requires confirmed credit spend",
            "outputs": {"credit_guard": credit_guard, "estimated_credits": estimated_credits},
            "warnings": ["Call again with confirm_spend=True after user approval."] if credit_guard["confirm_required"] else [],
            "errors": [] if credit_guard["confirm_required"] else ["Estimated credit spend exceeds the session budget."],
        }

    task_submissions: List[Dict[str, Any]] = []
    try:
        for asset, payload in zip(plan["assets"], payloads):
            response = gen._tripo_submit_task(payload)
            task_submissions.append({
                "asset_role": asset["role"],
                "asset_name": asset["name"],
                "task_id": response["task_id"],
                "trace_id": response.get("trace_id", ""),
                "request": payload,
            })
    except Exception as exc:
        gen._release_credit_reservation(credit_guard)
        return {
            "success": False,
            "stage": "asset_submission_failed",
            "message": str(exc),
            "outputs": {"credit_guard": credit_guard, "task_submissions": task_submissions},
            "warnings": [],
            "errors": [str(exc)],
        }

    return {
        "success": True,
        "stage": "asset_tasks_submitted",
        "message": "Submitted playable-slice Tripo asset generation tasks",
        "outputs": {
            "credit_guard": credit_guard,
            "task_submissions": task_submissions,
            "next_steps": [
                "Wait for each task with gen_tripo_wait_for_task.",
                "Import successful outputs with gen_tripo_import_to_project.",
                "Continue player, AI, level, HUD, PIE, screenshot, and report phases from tool_sequence.",
            ],
        },
        "warnings": [],
        "errors": [],
    }


def _import_completed_tripo_tasks(plan: Dict[str, Any], task_ids: List[str]) -> Dict[str, Any]:
    from tools import generative_tools as gen

    if len(task_ids) != len(plan["assets"]):
        return {
            "success": False,
            "stage": "asset_task_count_mismatch",
            "message": "assemble mode requires one Tripo task id per planned asset",
            "outputs": {"expected": len(plan["assets"]), "received": len(task_ids)},
            "warnings": [],
            "errors": ["Provide exactly four task_ids in plan asset order, or pass imported_asset_paths."],
        }

    imports: List[Dict[str, Any]] = []
    asset_paths: List[str] = []
    warnings: List[str] = []
    for asset, task_id in zip(plan["assets"], task_ids):
        try:
            task_result = gen._tripo_get_task(task_id)
            task = task_result["task"]
            if task.get("status") != "success":
                return {
                    "success": False,
                    "stage": "asset_import_pending",
                    "message": f"Tripo task is not successful: {task.get('status')}",
                    "outputs": {"task_id": task_id, "task": task, "imports": imports},
                    "warnings": warnings,
                    "errors": [f"Task {task_id} must reach success before assemble mode can import it."],
                }

            output = task.get("output") if isinstance(task.get("output"), dict) else {}
            download_folder = gen._default_tripo_download_folder(task_id)
            downloads = gen._download_tripo_output_files(
                task_id=task_id,
                output=output,
                target_folder=download_folder,
                output_keys=list(gen._TRIPO_IMPORT_OUTPUT_KEYS),
            )
            primary_model = gen._select_primary_model_download(downloads)
            if not primary_model:
                return {
                    "success": False,
                    "stage": "asset_import_missing_model",
                    "message": "No downloaded Tripo model output was available for import",
                    "outputs": {"task_id": task_id, "downloads": downloads, "imports": imports},
                    "warnings": warnings,
                    "errors": [f"Task {task_id} did not provide a supported model output."],
                }

            import_result = gen._import_generated_static_mesh(
                file_path=str(primary_model["path"]),
                content_path=asset["content_path"],
                asset_name=asset["name"],
                create_material_instance=True,
                create_blueprint=False,
                overwrite_existing=False,
            )
            if not import_result.get("success"):
                return {
                    "success": False,
                    "stage": "asset_import_failed",
                    "message": import_result.get("message") or "Generated mesh import failed",
                    "outputs": {"task_id": task_id, "downloads": downloads, "import_result": import_result, "imports": imports},
                    "warnings": warnings + list(import_result.get("warnings") or []),
                    "errors": import_result.get("errors") or [import_result.get("message") or "Generated mesh import failed"],
                }

            outputs = import_result.get("outputs", {})
            asset_path = outputs.get("asset_path") or f'{asset["content_path"]}/{asset["name"]}'
            asset_paths.append(asset_path)
            warnings.extend(import_result.get("warnings") or [])
            imports.append({
                "task_id": task_id,
                "asset_role": asset["role"],
                "asset_name": asset["name"],
                "asset_path": asset_path,
                "downloads": downloads,
                "import_result": import_result,
            })
        except Exception as exc:
            return {
                "success": False,
                "stage": "asset_import_failed",
                "message": str(exc),
                "outputs": {"task_id": task_id, "imports": imports},
                "warnings": warnings,
                "errors": [str(exc)],
            }

    return {
        "success": True,
        "stage": "assets_imported",
        "message": "Imported completed Tripo task outputs for playable-slice assembly",
        "outputs": {"imports": imports, "asset_paths": asset_paths},
        "warnings": warnings,
        "errors": [],
    }


def _level_assembly_code(plan: Dict[str, Any], imported_asset_paths: List[str]) -> str:
    return textwrap.dedent(f"""
        import unreal

        asset_paths = {json.dumps(imported_asset_paths)}
        content_path = {json.dumps(plan["content_path"])}
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        world = unreal.EditorLevelLibrary.get_editor_world()
        if world is None:
            raise RuntimeError("No editor world is loaded")

        placed = []
        locations = [
            unreal.Vector(-300.0, 0.0, 120.0),
            unreal.Vector(250.0, -220.0, 80.0),
            unreal.Vector(250.0, 220.0, 80.0),
            unreal.Vector(700.0, 0.0, 120.0),
        ]
        for index, asset_path in enumerate(asset_paths):
            mesh = unreal.load_asset(asset_path)
            if mesh is None:
                _warnings.append("Could not load generated mesh: " + str(asset_path))
                continue
            actor = actor_subsystem.spawn_actor_from_class(unreal.StaticMeshActor, locations[index % len(locations)], unreal.Rotator(0.0, 0.0, 0.0))
            actor.set_actor_label("MCP_PlayableSlice_" + str(index + 1))
            component = actor.get_component_by_class(unreal.StaticMeshComponent)
            if component:
                component.set_static_mesh(mesh)
                component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            placed.append(actor.get_actor_label())

        try:
            player_start = actor_subsystem.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-900.0, 0.0, 80.0), unreal.Rotator(0.0, 0.0, 0.0))
            player_start.set_actor_label("MCP_PlayableSlice_PlayerStart")
            placed.append(player_start.get_actor_label())
        except Exception as exc:
            _warnings.append("PlayerStart placement failed: " + str(exc))

        try:
            light = actor_subsystem.spawn_actor_from_class(unreal.PointLight, unreal.Vector(100.0, 0.0, 500.0), unreal.Rotator(0.0, 0.0, 0.0))
            light.set_actor_label("MCP_PlayableSlice_KeyLight")
            component = light.get_component_by_class(unreal.PointLightComponent)
            if component:
                component.set_editor_property("intensity", 5000.0)
            placed.append(light.get_actor_label())
        except Exception as exc:
            _warnings.append("Light placement failed: " + str(exc))

        unreal.EditorLevelLibrary.save_current_level()
        _result["content_path"] = content_path
        _result["placed_actor_labels"] = placed
        _result["placed_actor_count"] = len(placed)
    """)


def _run_pie_smoke(run_pie_seconds: int) -> Dict[str, Any]:
    wait_seconds = max(0, int(run_pie_seconds))
    code = textwrap.dedent(f"""
        import time
        import unreal

        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        was_in_pie = bool(subsystem.is_in_play_in_editor())
        if not was_in_pie:
            subsystem.editor_request_begin_play()
            time.sleep(min({wait_seconds}, 60))
        is_in_pie = bool(subsystem.is_in_play_in_editor())
        if is_in_pie:
            subsystem.editor_request_end_play()
        _result["requested_seconds"] = {wait_seconds}
        _result["entered_pie"] = is_in_pie or was_in_pie
        _result["was_in_pie_before"] = was_in_pie
    """)
    return _exec_structured(code, "playable_slice_pie_smoke")


def _package_slice_report(plan: Dict[str, Any], artifacts: List[str], verification: Dict[str, Any]) -> Dict[str, Any]:
    from skills.health_system import skill_package_vertical_slice_report

    return skill_package_vertical_slice_report(
        title=f"Playable Slice - {_safe_name(plan.get('brief', 'PlayableSlice'), 'PlayableSlice')}",
        summary=f"Generated playable-slice assembly for: {plan.get('brief', '')}",
        project_name="Unreal-MCP-Ghost",
        artifacts=artifacts,
        verification=verification,
        include_journal_entries=False,
    )


def _assemble_playable_slice(
    plan: Dict[str, Any],
    imported_asset_paths: List[str],
    run_pie_seconds: int,
) -> Dict[str, Any]:
    if len(imported_asset_paths) < 4:
        return {
            "success": False,
            "stage": "asset_inputs_required",
            "message": "assemble mode requires four imported generated asset paths",
            "outputs": {"imported_asset_paths": imported_asset_paths},
            "warnings": [],
            "errors": ["Pass imported_asset_paths or completed task_ids before assembling gameplay."],
        }

    gameplay = plan["gameplay"]
    content_path = plan["content_path"]
    ai_path = f"{content_path}/AI"
    steps: List[Dict[str, Any]] = []
    warnings: List[str] = []
    artifacts: List[str] = list(imported_asset_paths)
    created_artifacts: Dict[str, str] = {}

    def call(
        command: str,
        params: Dict[str, Any],
        stage: str,
        required: bool = True,
        artifact_label: str = "",
    ) -> Optional[Dict[str, Any]]:
        raw = _send(command, params)
        step = {"stage": stage, "command": command, "success": _ok(raw), "raw": raw}
        steps.append(step)
        if step["success"]:
            artifact_path = _raw_field(raw, "path", "filepath", "asset_path", "widget_blueprint_path")
            if artifact_label and artifact_path:
                created_artifacts[artifact_label] = artifact_path
                artifacts.append(artifact_path)
        else:
            message = _raw_message(raw, f"{command} failed")
            if required:
                return {
                    "success": False,
                    "stage": stage,
                    "message": message,
                    "outputs": {"steps": steps, "artifacts": artifacts},
                    "warnings": warnings,
                    "errors": [message],
                }
            warnings.append(f"{stage}: {message}")
        return None

    player_name = _asset_object_name(gameplay["player_blueprint"])
    enemy_name = _asset_object_name(gameplay["enemy_blueprint"])
    ai_controller_name = f"{enemy_name}AIController"
    blackboard_name = _asset_object_name(gameplay["blackboard"])
    behavior_tree_name = _asset_object_name(gameplay["behavior_tree"])
    hud_name = _asset_object_name(gameplay["hud_widget"])

    for command, params, stage, artifact_label in (
        ("create_blueprint", {"name": player_name, "parent_class": "Character"}, "create_player_blueprint", "player_blueprint"),
        ("create_blueprint", {"name": enemy_name, "parent_class": "Character"}, "create_enemy_blueprint", "enemy_blueprint"),
        ("create_blueprint", {"name": ai_controller_name, "parent_class": "AIController"}, "create_ai_controller_blueprint", "ai_controller"),
        ("create_blackboard", {"name": blackboard_name, "path": ai_path, "keys": [
            {"name": "TargetActor", "type": "Object"},
            {"name": "PatrolLocation", "type": "Vector"},
            {"name": "ChaseRange", "type": "Float"},
            {"name": "AttackRange", "type": "Float"},
        ]}, "create_blackboard", "blackboard"),
        ("create_behavior_tree", {"name": behavior_tree_name, "path": ai_path}, "create_behavior_tree", "behavior_tree"),
        ("build_behavior_tree", {"behavior_tree_name": behavior_tree_name, "clear_existing": True, "tree": {
            "type": "Selector",
            "children": [
                {"type": "Sequence", "children": [
                    {"type": "MoveTo", "properties": {"BlackboardKey": "TargetActor", "AcceptableRadius": "120.0"}},
                    {"type": "Wait", "properties": {"WaitTime": "0.25"}},
                ]},
                {"type": "Sequence", "children": [
                    {"type": "MoveTo", "properties": {"BlackboardKey": "PatrolLocation", "AcceptableRadius": "80.0"}},
                    {"type": "Wait", "properties": {"WaitTime": "1.0"}},
                ]},
            ],
        }}, "build_behavior_tree", ""),
        ("create_umg_widget_blueprint", {"name": hud_name}, "create_hud_widget", "hud_widget"),
    ):
        failure = call(command, params, stage, artifact_label=artifact_label)
        if failure:
            return failure

    for bp_name, component_name, mesh_path, add_stage, assign_stage in (
        (player_name, "GeneratedHeroMesh", imported_asset_paths[0], "add_player_generated_mesh", "assign_player_generated_mesh"),
        (enemy_name, "GeneratedEnemyMesh", imported_asset_paths[3], "add_enemy_generated_mesh", "assign_enemy_generated_mesh"),
    ):
        failure = call(
            "add_component_to_blueprint",
            {
                "blueprint_name": bp_name,
                "component_type": "StaticMeshComponent",
                "component_name": component_name,
                "location": [0.0, 0.0, -40.0],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0],
            },
            add_stage,
        )
        if failure:
            return failure
        failure = call(
            "set_static_mesh_properties",
            {"blueprint_name": bp_name, "component_name": component_name, "static_mesh": mesh_path},
            assign_stage,
        )
        if failure:
            return failure

    hud_text_failure = call(
        "add_text_block_to_widget",
        {
            "blueprint_name": hud_name,
            "widget_name": "ObjectiveText",
            "text": "Reach the boss room",
            "position": [40.0, 40.0],
            "size": [520.0, 48.0],
            "font_size": 24,
            "color": [1.0, 1.0, 1.0, 1.0],
        },
        "add_hud_objective_text",
        required=False,
    )
    if hud_text_failure:
        return hud_text_failure

    for bp_name, stage in ((player_name, "compile_player_blueprint"), (enemy_name, "compile_enemy_blueprint"), (ai_controller_name, "compile_ai_controller"), (hud_name, "compile_hud_widget")):
        failure = call("compile_blueprint", {"blueprint_name": bp_name}, stage)
        if failure:
            return failure

    failure = call("setup_navmesh", {"extent": [2500.0, 2500.0, 500.0], "location": [0.0, 0.0, 0.0], "rebuild": True}, "setup_navmesh", required=False)
    if failure:
        return failure

    level_result = _exec_transactional(_level_assembly_code(plan, imported_asset_paths), f"playable_slice:assemble:{_safe_name(plan['brief'])}")
    steps.append({"stage": "assemble_level", "command": "ue_exec_transact", "success": bool(level_result.get("success")), "raw": level_result})
    if not level_result.get("success"):
        return {
            "success": False,
            "stage": "assemble_level",
            "message": level_result.get("message", "Level assembly failed"),
            "outputs": {"steps": steps, "artifacts": artifacts},
            "warnings": warnings + list(level_result.get("warnings") or []),
            "errors": level_result.get("errors") or [level_result.get("message", "Level assembly failed")],
        }
    warnings.extend(level_result.get("warnings") or [])

    screenshot_path = _REPO_ROOT / ".mcp_artifacts" / "screenshots" / f"{_safe_name(plan['brief'])}_playable_slice.png"
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    screenshot = _send("take_screenshot", {"filepath": str(screenshot_path), "show_ui": False, "resolution": [1920, 1080]})
    steps.append({"stage": "capture_screenshot", "command": "take_screenshot", "success": _ok(screenshot), "raw": screenshot})
    if _ok(screenshot):
        screenshot_path = screenshot.get("filepath") or screenshot.get("path") or (screenshot.get("result") or {}).get("filepath", "")
        if screenshot_path:
            artifacts.append(str(screenshot_path))
    else:
        warnings.append(f"capture_screenshot: {_raw_message(screenshot, 'screenshot failed')}")

    pie_result = _run_pie_smoke(run_pie_seconds)
    steps.append({"stage": "pie_smoke", "command": "playable_slice_pie_smoke", "success": bool(pie_result.get("success")), "raw": pie_result})
    if not pie_result.get("success"):
        return {
            "success": False,
            "stage": "pie_smoke",
            "message": pie_result.get("message", "PIE smoke failed"),
            "outputs": {"steps": steps, "artifacts": artifacts, "pie_result": pie_result},
            "warnings": warnings + list(pie_result.get("warnings") or []),
            "errors": pie_result.get("errors") or [pie_result.get("message", "PIE smoke failed")],
        }
    warnings.extend(pie_result.get("warnings") or [])

    verification = {
        "brief": plan["brief"],
        "schema": plan["schema"],
        "imported_asset_paths": imported_asset_paths,
        "player_blueprint": gameplay["player_blueprint"],
        "enemy_blueprint": gameplay["enemy_blueprint"],
        "behavior_tree": gameplay["behavior_tree"],
        "blackboard": gameplay["blackboard"],
        "hud_widget": gameplay["hud_widget"],
        "created_artifacts": created_artifacts,
        "generated_mesh_assignments": {
            "player": {"blueprint": player_name, "component": "GeneratedHeroMesh", "static_mesh": imported_asset_paths[0]},
            "enemy": {"blueprint": enemy_name, "component": "GeneratedEnemyMesh", "static_mesh": imported_asset_paths[3]},
        },
        "pie_smoke": pie_result.get("outputs", {}),
        "steps_completed": [step["stage"] for step in steps if step["success"]],
    }
    report = _package_slice_report(plan, artifacts, verification)
    steps.append({"stage": "package_report", "command": "skill_package_vertical_slice_report", "success": bool(report.get("success")), "raw": report})
    if not report.get("success"):
        return {
            "success": False,
            "stage": "package_report",
            "message": report.get("message", "Vertical slice report packaging failed"),
            "outputs": {"steps": steps, "artifacts": artifacts, "verification": verification},
            "warnings": warnings + list(report.get("warnings") or []),
            "errors": report.get("errors") or [report.get("message", "Vertical slice report packaging failed")],
        }

    report_path = report.get("outputs", {}).get("report_path", "")
    if report_path:
        artifacts.append(report_path)
    return {
        "success": True,
        "stage": "assembled",
        "message": "Playable slice assembled, smoke-tested, and packaged",
        "outputs": {
            "steps": steps,
            "artifacts": artifacts,
            "verification": verification,
            "report": report,
        },
        "warnings": warnings + list(report.get("warnings") or []),
        "errors": [],
    }


def skill_generate_playable_slice(
    brief: str,
    mode: str = "plan",
    content_path: str = "/Game/Generated/PlayableSlice",
    session_name: str = "playable-slice",
    confirm_spend: bool = False,
    task_ids: Optional[List[str]] = None,
    imported_asset_paths: Optional[List[str]] = None,
    run_pie_seconds: int = 60,
) -> Dict[str, Any]:
    """Plan or start a generated playable-slice workflow from one brief."""

    t0 = time.monotonic()
    safe_mode = (mode or "plan").strip().lower()
    inputs = {
        "brief": brief,
        "mode": safe_mode,
        "content_path": content_path,
        "session_name": session_name,
        "confirm_spend": confirm_spend,
        "task_ids": task_ids or [],
        "imported_asset_paths": imported_asset_paths or [],
        "run_pie_seconds": run_pie_seconds,
    }
    if safe_mode not in _VALID_MODES:
        return _structured(
            success=False,
            stage="invalid_mode",
            message="mode must be one of: assemble, plan, submit_assets",
            inputs=inputs,
            errors=["mode must be one of: assemble, plan, submit_assets"],
            t0=t0,
        )
    if not str(brief or "").strip():
        return _structured(
            success=False,
            stage="invalid_brief",
            message="brief is required",
            inputs=inputs,
            errors=["brief is required"],
            t0=t0,
        )

    plan = build_playable_slice_plan(brief, content_path)
    validation_errors = validate_playable_slice_plan(plan)
    schema = _load_schema()
    if validation_errors:
        return _structured(
            success=False,
            stage="plan_validation_failed",
            message="Playable-slice plan failed schema validation",
            inputs=inputs,
            outputs={"plan": plan, "schema_path": str(_SCHEMA_PATH), "schema_title": schema.get("title", "")},
            errors=validation_errors,
            t0=t0,
        )
    if safe_mode == "plan":
        return _structured(
            success=True,
            stage="plan_ready",
            message="Playable-slice plan validated; no paid provider request was sent",
            inputs=inputs,
            outputs={
                "plan": plan,
                "schema_path": str(_SCHEMA_PATH),
                "schema_title": schema.get("title", ""),
                "network_required": False,
                "execution_modes": sorted(_VALID_MODES),
            },
            warnings=["Use mode='submit_assets' with confirm_spend=True to start paid Tripo generation; use mode='assemble' after completed task_ids or imported_asset_paths are available."],
            t0=t0,
        )

    if safe_mode == "assemble":
        asset_paths = list(imported_asset_paths or [])
        import_result: Dict[str, Any] = {}
        warnings: List[str] = []
        if not asset_paths and task_ids:
            import_result = _import_completed_tripo_tasks(plan, list(task_ids))
            warnings.extend(import_result.get("warnings", []))
            if not import_result.get("success"):
                return _structured(
                    success=False,
                    stage=import_result["stage"],
                    message=import_result["message"],
                    inputs=inputs,
                    outputs={"plan": plan, **import_result.get("outputs", {})},
                    warnings=warnings,
                    errors=import_result.get("errors", []),
                    t0=t0,
                )
            asset_paths = list(import_result.get("outputs", {}).get("asset_paths", []))

        assembly = _assemble_playable_slice(plan, asset_paths, run_pie_seconds)
        return _structured(
            success=bool(assembly["success"]),
            stage=assembly["stage"],
            message=assembly["message"],
            inputs=inputs,
            outputs={"plan": plan, "asset_import": import_result, **assembly.get("outputs", {})},
            warnings=warnings + assembly.get("warnings", []),
            errors=assembly.get("errors", []),
            t0=t0,
        )

    submission = _submit_tripo_asset_tasks(plan, session_name, confirm_spend)
    return _structured(
        success=bool(submission["success"]),
        stage=submission["stage"],
        message=submission["message"],
        inputs=inputs,
        outputs={"plan": plan, **submission.get("outputs", {})},
        warnings=submission.get("warnings", []),
        errors=submission.get("errors", []),
        t0=t0,
    )


def register_playable_slice_skill(mcp: FastMCP) -> None:
    _impl = globals()["skill_generate_playable_slice"]
    _mechanic_impl = globals()["skill_plan_gameplay_mechanic"]
    _session_impl = globals()["skill_compile_ide_companion_session"]
    _status_impl = globals()["skill_compile_ide_companion_status"]
    _work_order_impl = globals()["skill_compile_ide_companion_work_order"]
    _evidence_impl = globals()["skill_record_ide_companion_evidence"]
    _resume_impl = globals()["skill_resume_ide_companion_session"]
    _dashboard_impl = globals()["skill_compile_ide_companion_dashboard"]
    _blocker_impl = globals()["skill_compile_ide_companion_blocker_resolution"]
    _placeholder_impl = globals()["skill_compile_ide_companion_placeholder_manifest"]
    _asset_lifecycle_impl = globals()["skill_compile_ide_companion_asset_lifecycle_manifest"]
    _editor_queue_impl = globals()["skill_compile_ide_companion_editor_queue"]

    @mcp.tool()
    async def skill_generate_playable_slice(
        ctx: Context,
        brief: str,
        mode: str = "plan",
        content_path: str = "/Game/Generated/PlayableSlice",
        session_name: str = "playable-slice",
        confirm_spend: bool = False,
        task_ids: Optional[List[str]] = None,
        imported_asset_paths: Optional[List[str]] = None,
        run_pie_seconds: int = 60,
    ) -> str:
        """Plan, submit assets for, or assemble a generated playable slice.

        Mode `plan` validates the schema and returns the end-to-end tool
        sequence without network calls. Mode `submit_assets` requires
        TRIPO_API_KEY and confirm_spend=True before submitting paid Tripo tasks.
        Mode `assemble` consumes completed task_ids or imported_asset_paths,
        then creates Blueprint/AI/HUD/level/evidence/report outputs.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d7-playable-slice-skill
        Example:
            skill_generate_playable_slice(brief="third-person dungeon demo with a slime and a boss", mode="plan")"""
        result = _impl(
            brief=brief,
            mode=mode,
            content_path=content_path,
            session_name=session_name,
            confirm_spend=confirm_spend,
            task_ids=task_ids,
            imported_asset_paths=imported_asset_paths,
            run_pie_seconds=run_pie_seconds,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_plan_gameplay_mechanic(
        ctx: Context,
        brief: str,
        content_path: str = "/Game/Generated/Mechanics",
        include_generated_assets: bool = True,
    ) -> str:
        """Plan an Unreal-ready gameplay mechanic implementation from a brief.

        Returns a no-spend, no-editor-mutation plan covering generated asset
        prompts, Blueprint/component structure, AI/HUD/save/replication hooks,
        validation gates, and the ordered MCP tool sequence.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d11-gameplay-mechanic-planner
        Example:
            skill_plan_gameplay_mechanic(brief="player dash ability with cooldown and HUD feedback")"""
        result = _mechanic_impl(
            brief=brief,
            content_path=content_path,
            include_generated_assets=include_generated_assets,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_compile_ide_companion_session(
        ctx: Context,
        project_brief: str,
        mechanic_brief: str = "",
        content_path: str = "/Game/Generated/PlayableSlice",
        session_name: str = "ide-companion",
        include_generated_assets: bool = True,
    ) -> str:
        """Compile a no-spend IDE companion session plan for a solo Unreal developer.

        Returns a full orchestration plan covering readiness, generated assets,
        gameplay mechanic planning, editor implementation, runtime verification,
        fallback paths, gates, and next MCP tool calls.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d12-ide-companion-session-orchestrator
        Example:
            skill_compile_ide_companion_session(project_brief="third-person dungeon slice", mechanic_brief="patrol enemy that updates objective HUD")"""
        result = _session_impl(
            project_brief=project_brief,
            mechanic_brief=mechanic_brief,
            content_path=content_path,
            session_name=session_name,
            include_generated_assets=include_generated_assets,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_compile_ide_companion_status(
        ctx: Context,
        session_plan: Any,
        readiness_report: Any = None,
        completed_phases: Any = None,
        evidence: Any = None,
        current_blockers: Any = None,
    ) -> str:
        """Compile a no-spend progress receipt for an IDE companion session.

        Accepts a session plan plus optional readiness report, completed phase
        names, evidence map, and manual blockers. Returns the current phase
        states, blocking gates, evidence gaps, readiness flags, and next safe
        MCP action.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d13-ide-companion-status-receipt
        Example:
            skill_compile_ide_companion_status(session_plan=plan, readiness_report=readiness, completed_phases=["orient_to_project"])"""
        result = _status_impl(
            session_plan=session_plan,
            readiness_report=readiness_report,
            completed_phases=completed_phases,
            evidence=evidence,
            current_blockers=current_blockers,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_compile_ide_companion_work_order(
        ctx: Context,
        session_plan: Any,
        companion_status: Any = None,
        target_phase: str = "",
        readiness_report: Any = None,
    ) -> str:
        """Compile the next safe work order for an IDE companion session.

        Accepts a session plan plus optional status/readiness context and emits
        the selected phase, prerequisites, blockers, tool steps, evidence to
        collect, acceptance criteria, stop conditions, and after-completion
        status refresh.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d14-ide-companion-work-order
        Example:
            skill_compile_ide_companion_work_order(session_plan=plan, companion_status=status)"""
        result = _work_order_impl(
            session_plan=session_plan,
            companion_status=companion_status,
            target_phase=target_phase,
            readiness_report=readiness_report,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_record_ide_companion_evidence(
        ctx: Context,
        session_plan: Any,
        phase_name: str,
        evidence_type: str = "note",
        summary: str = "",
        artifacts: Optional[List[str]] = None,
        readiness_report: Any = None,
        companion_status: Any = None,
        work_order: Any = None,
        current_blockers: Any = None,
    ) -> str:
        """Record phase evidence to the durable local IDE companion ledger.

        Writes a JSON ledger under `.mcp_artifacts/ide_companion_sessions`,
        refreshes status from the recorded evidence, and returns the ledger path
        plus updated status. This tool does not call Tripo or mutate Unreal.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d15-ide-companion-evidence-ledger
        Example:
            skill_record_ide_companion_evidence(session_plan=plan, phase_name="orient_to_project", summary="Project context loaded")"""
        result = _evidence_impl(
            session_plan=session_plan,
            phase_name=phase_name,
            evidence_type=evidence_type,
            summary=summary,
            artifacts=artifacts,
            readiness_report=readiness_report,
            companion_status=companion_status,
            work_order=work_order,
            current_blockers=current_blockers,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_resume_ide_companion_session(
        ctx: Context,
        session_name: str = "ide-companion",
        ledger_path: str = "",
        readiness_report: Any = None,
        current_blockers: Any = None,
    ) -> str:
        """Resume an IDE companion session from its durable local ledger.

        Loads `.mcp_artifacts/ide_companion_sessions/<session>.json` or an
        explicit ledger path, rebuilds status, compiles the next work order,
        and returns a compact resume packet. This tool does not call Tripo or
        mutate Unreal.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d16-ide-companion-session-resume
        Example:
            skill_resume_ide_companion_session(session_name="ide-companion")"""
        result = _resume_impl(
            session_name=session_name,
            ledger_path=ledger_path,
            readiness_report=readiness_report,
            current_blockers=current_blockers,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_compile_ide_companion_dashboard(
        ctx: Context,
        session_name: str = "ide-companion",
        ledger_path: str = "",
        session_plan: Any = None,
        readiness_report: Any = None,
        current_blockers: Any = None,
    ) -> str:
        """Compile a display-ready dashboard packet for the IDE companion.

        Reads the local ledger or a provided session plan and returns readiness,
        progress, next-work, generated-asset, mechanic, and evidence cards plus
        the current status/work-order payloads. This tool does not call Tripo or
        mutate Unreal.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d17-ide-companion-dashboard
        Example:
            skill_compile_ide_companion_dashboard(session_name="ide-companion")"""
        result = _dashboard_impl(
            session_name=session_name,
            ledger_path=ledger_path,
            session_plan=session_plan,
            readiness_report=readiness_report,
            current_blockers=current_blockers,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_compile_ide_companion_blocker_resolution(
        ctx: Context,
        dashboard: Any = None,
        session_plan: Any = None,
        companion_status: Any = None,
        readiness_report: Any = None,
        preferred_strategy: str = "continue_with_placeholders",
    ) -> str:
        """Compile no-spend resolution choices for IDE companion blockers.

        Converts readiness/status blockers into unblock actions, fallback paths,
        placeholder policy, bridge-offline policy, and next MCP actions. This
        tool does not call Tripo or mutate Unreal.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d18-ide-companion-blocker-resolution
        Example:
            skill_compile_ide_companion_blocker_resolution(session_plan=plan, companion_status=status)"""
        result = _blocker_impl(
            dashboard=dashboard,
            session_plan=session_plan,
            companion_status=companion_status,
            readiness_report=readiness_report,
            preferred_strategy=preferred_strategy,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_compile_ide_companion_placeholder_manifest(
        ctx: Context,
        session_plan: Any,
        placeholder_root: str = "",
        blocker_resolution: Any = None,
    ) -> str:
        """Compile a no-spend placeholder manifest for blocked generated assets.

        Converts planned generated asset prompts into placeholder assets,
        replacement mapping, creation tool steps, and evidence requirements.
        This tool does not call Tripo or mutate Unreal.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d19-ide-companion-placeholder-manifest
        Example:
            skill_compile_ide_companion_placeholder_manifest(session_plan=plan)"""
        result = _placeholder_impl(
            session_plan=session_plan,
            placeholder_root=placeholder_root,
            blocker_resolution=blocker_resolution,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_compile_ide_companion_asset_lifecycle_manifest(
        ctx: Context,
        session_plan: Any,
        placeholder_manifest: Any = None,
        preferred_provider: str = "tripo",
        write_manifest: bool = False,
        manifest_name: str = "asset_lifecycle",
    ) -> str:
        """Compile a provider-neutral generated asset lifecycle manifest.

        Converts planned generated asset prompts into provider task contracts,
        readiness/spend gates, placeholder replacement mapping, quality gates,
        and evidence requirements. This tool does not call Tripo, spend
        credits, or mutate Unreal.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d34-ide-companion-generated-asset-lifecycle-manifest
        Example:
            skill_compile_ide_companion_asset_lifecycle_manifest(session_plan=plan, placeholder_manifest=manifest)"""
        result = _asset_lifecycle_impl(
            session_plan=session_plan,
            placeholder_manifest=placeholder_manifest,
            preferred_provider=preferred_provider,
            write_manifest=write_manifest,
            manifest_name=manifest_name,
        )
        return json.dumps(result)

    @mcp.tool()
    async def skill_compile_ide_companion_editor_queue(
        ctx: Context,
        session_plan: Any,
        companion_status: Any = None,
        work_order: Any = None,
        placeholder_manifest: Any = None,
        queue_name: str = "editor_queue",
    ) -> str:
        """Compile a bridge-gated editor action queue for an IDE companion session.

        Turns a placeholder manifest or work order into durable editor actions
        that can be executed after the Unreal bridge is reachable. This tool
        writes only a local queue file; it does not call Tripo or mutate Unreal.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d20-ide-companion-editor-action-queue
        Example:
            skill_compile_ide_companion_editor_queue(session_plan=plan, companion_status=status, placeholder_manifest=manifest)"""
        result = _editor_queue_impl(
            session_plan=session_plan,
            companion_status=companion_status,
            work_order=work_order,
            placeholder_manifest=placeholder_manifest,
            queue_name=queue_name,
        )
        return json.dumps(result)

    logger.info("Playable slice skills registered: skill_generate_playable_slice, skill_plan_gameplay_mechanic, skill_compile_ide_companion_session, skill_compile_ide_companion_status, skill_compile_ide_companion_work_order, skill_record_ide_companion_evidence, skill_resume_ide_companion_session, skill_compile_ide_companion_dashboard, skill_compile_ide_companion_blocker_resolution, skill_compile_ide_companion_placeholder_manifest, skill_compile_ide_companion_asset_lifecycle_manifest, skill_compile_ide_companion_editor_queue")
