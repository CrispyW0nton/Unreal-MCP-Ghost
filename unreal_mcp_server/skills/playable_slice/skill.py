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

    logger.info("Playable slice skill registered: skill_generate_playable_slice")
