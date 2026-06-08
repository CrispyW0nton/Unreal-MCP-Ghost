"""D.7 playable-slice generation skill."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP.skills.playable_slice")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "knowledge_base" / "v5" / "PLAYABLE_SLICE_SCHEMA.json"
_ASSET_ROLES = ("hero", "prop", "prop", "enemy")
_VALID_MODES = {"plan", "submit_assets"}


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


def skill_generate_playable_slice(
    brief: str,
    mode: str = "plan",
    content_path: str = "/Game/Generated/PlayableSlice",
    session_name: str = "playable-slice",
    confirm_spend: bool = False,
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
    }
    if safe_mode not in _VALID_MODES:
        return _structured(
            success=False,
            stage="invalid_mode",
            message="mode must be one of: plan, submit_assets",
            inputs=inputs,
            errors=["mode must be one of: plan, submit_assets"],
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
            warnings=["Use mode='submit_assets' with confirm_spend=True to start paid Tripo generation."],
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

    @mcp.tool()
    async def skill_generate_playable_slice(
        ctx: Context,
        brief: str,
        mode: str = "plan",
        content_path: str = "/Game/Generated/PlayableSlice",
        session_name: str = "playable-slice",
        confirm_spend: bool = False,
    ) -> str:
        """Plan or start a generated playable slice from one brief.

        Mode `plan` validates the schema and returns the end-to-end tool
        sequence without network calls. Mode `submit_assets` requires
        TRIPO_API_KEY and confirm_spend=True before submitting paid Tripo tasks.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d7-playable-slice-skill
        Example:
            skill_generate_playable_slice(brief="third-person dungeon demo with a slime and a boss", mode="plan")"""
        result = _impl(
            brief=brief,
            mode=mode,
            content_path=content_path,
            session_name=session_name,
            confirm_spend=confirm_spend,
        )
        return json.dumps(result)

    logger.info("Playable slice skill registered: skill_generate_playable_slice")
