"""D.7 playable-slice generation skill."""

from __future__ import annotations

import json
import logging
import re
import time
import importlib.util
from argparse import Namespace
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP.skills.playable_slice")

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _REPO_ROOT / "knowledge_base" / "v5" / "PLAYABLE_SLICE_SCHEMA.json"
_PREFLIGHT_SCRIPT_PATH = _REPO_ROOT / "scripts" / "playable_slice_live_preflight.py"
_ASSET_ROLES = ("hero", "prop", "prop", "enemy")
_VALID_MODES = {"preflight", "plan", "submit_assets", "orchestrate"}


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


def _split_user_list(value: str) -> List[str]:
    parts = re.split(r"[,;\n]+", value or "")
    return [part.strip() for part in parts if part.strip()]


def _pick_requested_roles(asset_roles: str, enemy: str) -> Dict[str, Any]:
    requested = _split_user_list(asset_roles)
    hero = next((item for item in requested if re.search(r"\b(hero|player|character|protagonist|avatar)\b", item, re.I)), "")
    enemy_role = next((item for item in requested if re.search(r"\b(enemy|boss|npc|ai|slime|skeleton|robot|drone|creature)\b", item, re.I)), "")
    props = [
        item for item in requested
        if item != hero and item != enemy_role
    ]
    while len(props) < 2:
        props.append(("cover prop", "objective pickup")[len(props)])
    return {
        "requested": requested,
        "hero": hero or "third-person hero character",
        "enemy": enemy_role or enemy,
        "props": props[:2],
    }


def _asset_prompt(theme: str, role: str, index: int, enemy: str, descriptor: str = "") -> str:
    requested = descriptor.strip()
    if role == "hero":
        subject = requested or "third-person hero character"
        return f"game-ready {subject} for a {theme} playable slice, clean silhouette, readable proportions"
    if role == "enemy":
        subject = requested or enemy
        return f"game-ready {subject} enemy for a {theme} encounter, simple patrol/chase readable silhouette"
    prop_names = ("cover prop", "objective pickup")
    subject = requested or prop_names[index - 1]
    return f"game-ready {theme} {subject}, low-poly vertical-slice style, clear collision shape"


def build_playable_slice_plan(
    brief: str,
    content_path: str = "/Game/Generated/PlayableSlice",
    asset_roles: str = "",
    gameplay_loop: str = "",
    acceptance_criteria: str = "",
    required_evidence: str = "",
) -> Dict[str, Any]:
    """Build a deterministic D.7 plan from a one-sentence game brief."""

    theme = _theme_from_brief(brief)
    enemy = _enemy_from_brief(brief)
    requested_roles = _pick_requested_roles(asset_roles, enemy)
    slug = _safe_name(brief[:48], "PlayableSlice")
    base_path = _normalize_content_folder(content_path)
    assets: List[Dict[str, Any]] = []
    prop_index = 0
    for index, role in enumerate(_ASSET_ROLES, start=1):
        if role == "prop":
            prop_index += 1
            descriptor = requested_roles["props"][prop_index - 1]
            name = f"{slug}_{_safe_name(descriptor, f'Prop{prop_index}')}"
            prompt = _asset_prompt(theme, role, prop_index, enemy, descriptor)
        else:
            descriptor = requested_roles[role]
            name = f"{slug}_{_safe_name(descriptor, role.title())}"
            prompt = _asset_prompt(theme, role, index, enemy, descriptor)
        assets.append({
            "role": role,
            "description": descriptor,
            "name": name,
            "prompt": prompt,
            "provider": "tripo",
            "task_type": "text_to_model",
            "content_path": f"{base_path}/Assets",
            "texture": True,
            "pbr": True,
            "texture_quality": "standard",
            "face_limit": 12000,
            "smart_low_poly": True,
        })

    return {
        "schema": "unreal_mcp_playable_slice_plan.v1",
        "brief": brief,
        "theme": theme,
        "content_path": base_path,
        "requested_asset_roles": requested_roles["requested"],
        "assets": assets,
        "gameplay": {
            "player_blueprint": f"{base_path}/Blueprints/BP_{slug}_Player",
            "enemy_blueprint": f"{base_path}/Blueprints/BP_{slug}_{_safe_name(enemy, 'Enemy').title()}Enemy",
            "behavior_tree": f"{base_path}/AI/BT_{slug}_Enemy",
            "blackboard": f"{base_path}/AI/BB_{slug}_Enemy",
            "hud_widget": f"{base_path}/UI/WBP_{slug}_HUD",
            "requested_loop": gameplay_loop.strip(),
            "level_goal": gameplay_loop.strip() or "small third-person arena with hero start, two props, one patrol/chase enemy, health HUD, and exit objective",
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
            "acceptance_criteria": acceptance_criteria.strip(),
            "required_runtime_evidence": _split_user_list(required_evidence) or ["PIE >= 60 seconds", "viewport screenshot", "compile reports"],
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
            for key in ("name", "description", "prompt", "provider", "task_type", "content_path"):
                if not str(asset.get(key, "")).strip():
                    errors.append(f"asset {asset.get('role', '?')} missing {key}")
            if asset.get("smart_low_poly") is not True:
                errors.append(f"asset {asset.get('role', '?')} must set smart_low_poly true")
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


def _load_preflight_module() -> Any:
    spec = importlib.util.spec_from_file_location("playable_slice_live_preflight", _PREFLIGHT_SCRIPT_PATH)
    if not spec or not spec.loader:
        raise RuntimeError(f"Unable to load playable-slice preflight script: {_PREFLIGHT_SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_live_preflight(session_name: str, estimated_credits: int = 120) -> Dict[str, Any]:
    module = _load_preflight_module()
    args = Namespace(
        repo_root=str(_REPO_ROOT),
        engine_root="",
        package_root=r"C:\uebuild",
        bridge_host="127.0.0.1",
        bridge_port=55557,
        bridge_timeout_s=1.0,
        session_name=session_name or "playable-slice",
        estimated_credits=estimated_credits,
    )
    return module.build_preflight(args)


def _parse_json_list(value: str, field_name: str) -> tuple[List[Dict[str, Any]], List[str]]:
    if not str(value or "").strip():
        return [], []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        return [], [f"{field_name} must be JSON: {exc}"]
    if not isinstance(parsed, list):
        return [], [f"{field_name} must be a JSON array"]
    normalized: List[Dict[str, Any]] = []
    errors: List[str] = []
    for index, item in enumerate(parsed):
        if isinstance(item, dict):
            normalized.append(item)
        else:
            errors.append(f"{field_name}[{index}] must be an object")
    return normalized, errors


def _parse_json_object(value: str, field_name: str) -> tuple[Dict[str, Any], List[str]]:
    if not str(value or "").strip():
        return {}, []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        return {}, [f"{field_name} must be JSON: {exc}"]
    if not isinstance(parsed, dict):
        return {}, [f"{field_name} must be a JSON object"]
    return parsed, []


def _asset_payload(asset: Dict[str, Any], model_version: str) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "type": "text_to_model",
        "prompt": asset["prompt"],
        "texture": bool(asset.get("texture", True)),
        "pbr": bool(asset.get("pbr", True)),
        "texture_quality": asset.get("texture_quality", "standard"),
        "face_limit": int(asset.get("face_limit", 12000)),
        "smart_low_poly": bool(asset.get("smart_low_poly", True)),
    }
    if model_version:
        payload["model_version"] = model_version
    return payload


def _find_role_record(records: List[Dict[str, Any]], role: str, asset_name: str) -> Dict[str, Any]:
    for record in records:
        if str(record.get("asset_name", "")).lower() == asset_name.lower():
            return record
    for record in records:
        if str(record.get("asset_role", record.get("role", ""))).lower() == role.lower():
            return record
    return {}


def _match_asset_records(assets: List[Dict[str, Any]], records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    used: set[int] = set()
    for asset in assets:
        match_index = -1
        asset_name = str(asset.get("name", "")).lower()
        role = str(asset.get("role", "")).lower()
        for index, record in enumerate(records):
            if index in used:
                continue
            if str(record.get("asset_name", "")).lower() == asset_name:
                match_index = index
                break
        if match_index == -1:
            for index, record in enumerate(records):
                if index in used:
                    continue
                if str(record.get("asset_role", record.get("role", ""))).lower() == role:
                    match_index = index
                    break
        if match_index == -1:
            matches.append({})
            continue
        used.add(match_index)
        matches.append(records[match_index])
    return matches


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, "", {}):
        return []
    return [value]


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        stripped = value.strip()
        return bool(stripped) and not stripped.startswith("<")
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _compile_reports_clean(reports: List[Any], explicit_clean: Any) -> bool:
    if explicit_clean is True:
        return True
    if not reports:
        return False
    for report in reports:
        if isinstance(report, dict):
            if report.get("success") is False or report.get("compiled") is False or report.get("errors"):
                return False
            status = str(report.get("status", "")).strip().lower()
            if (
                report.get("success") is not True
                and report.get("compiled") is not True
                and status not in {"ok", "clean", "passed", "success", "compiled"}
            ):
                return False
            continue
        if not _is_present(report):
            return False
    return True


def _gate_status(observed: List[Any], missing: List[str]) -> str:
    if not missing:
        return "proven"
    if observed:
        return "partial"
    return "missing"


def _build_evidence_readiness(
    plan: Dict[str, Any],
    task_submissions: List[Dict[str, Any]],
    imported_assets: List[Dict[str, Any]],
    execution_evidence: Dict[str, Any],
) -> Dict[str, Any]:
    assets = plan["assets"]
    submission_matches = _match_asset_records(assets, task_submissions)
    import_matches = _match_asset_records(assets, imported_assets)
    asset_rows: List[Dict[str, Any]] = []
    missing_tasks: List[str] = []
    missing_imports: List[str] = []
    observed_tasks: List[str] = []
    observed_imports: List[str] = []
    for asset, submission, imported in zip(assets, submission_matches, import_matches):
        task_id = str(submission.get("task_id", "")).strip()
        imported_path = imported.get("asset_path", imported.get("imported_asset_path", ""))
        if _is_present(task_id):
            observed_tasks.append(task_id)
        else:
            missing_tasks.append(asset["name"])
        if _is_present(imported_path):
            observed_imports.append(str(imported_path))
        else:
            missing_imports.append(asset["name"])
        asset_rows.append({
            "asset_role": asset["role"],
            "asset_name": asset["name"],
            "task_id": task_id,
            "imported_asset_path": imported_path,
            "task_proven": _is_present(task_id),
            "import_proven": _is_present(imported_path),
        })

    credit_observed = []
    if _is_present(execution_evidence.get("credit_guard")):
        credit_observed.append("credit_guard")
    if _is_present(execution_evidence.get("credit_usage")):
        credit_observed.append("credit_usage")
    credit_missing = [] if credit_observed else ["credit guard or usage summary"]
    if not credit_observed and observed_tasks:
        credit_observed.append("task submissions without credit summary")

    gameplay_assets = execution_evidence.get("gameplay_assets", {})
    if not isinstance(gameplay_assets, dict):
        gameplay_assets = {}
    required_gameplay = {
        "player_blueprint": plan["gameplay"]["player_blueprint"],
        "enemy_blueprint": plan["gameplay"]["enemy_blueprint"],
        "hud_widget": plan["gameplay"]["hud_widget"],
        "level_or_map": f"{plan['content_path']}/Level",
    }
    changed_assets = _as_list(execution_evidence.get("changed_assets") or execution_evidence.get("touched_assets"))
    gameplay_observed = [f"{key}: {value}" for key, value in gameplay_assets.items() if _is_present(value)]
    if changed_assets:
        gameplay_observed.append("changed_assets")
    gameplay_missing = [key for key in required_gameplay if not _is_present(gameplay_assets.get(key))]

    compile_reports = _as_list(execution_evidence.get("compile_reports"))
    compile_clean = _compile_reports_clean(compile_reports, execution_evidence.get("compile_clean"))
    compile_observed = compile_reports or (["compile_clean"] if execution_evidence.get("compile_clean") is True else [])
    compile_missing = [] if compile_clean else ["clean compile reports for touched Blueprints/widgets"]

    pie_log_path = execution_evidence.get("pie_log_path", execution_evidence.get("pie_log"))
    pie_duration = execution_evidence.get("pie_duration_s", execution_evidence.get("pie_seconds"))
    pie_observed = []
    if _is_present(pie_log_path):
        pie_observed.append(str(pie_log_path))
    if isinstance(pie_duration, (int, float)) and pie_duration > 0:
        pie_observed.append(f"{pie_duration}s")
    pie_missing = []
    if not _is_present(pie_log_path):
        pie_missing.append("PIE log path or captured log")
    if not isinstance(pie_duration, (int, float)) or pie_duration < 60:
        pie_missing.append("PIE duration >= 60 seconds or explicit smoke exception")

    screenshot_path = execution_evidence.get(
        "viewport_screenshot_path",
        execution_evidence.get("screenshot_path", execution_evidence.get("viewport_screenshot")),
    )
    screenshot_observed = [str(screenshot_path)] if _is_present(screenshot_path) else []
    screenshot_missing = [] if screenshot_observed else ["viewport screenshot path"]

    report_path = execution_evidence.get(
        "vertical_slice_report_path",
        execution_evidence.get("report_path", execution_evidence.get("final_report_path")),
    )
    report_observed = [str(report_path)] if _is_present(report_path) else []
    report_missing = [] if report_observed else ["skill_package_vertical_slice_report output path"]

    gates = [
        {
            "id": "tripo_asset_tasks",
            "label": "Tripo Smart Mesh task ids for all planned assets",
            "status": _gate_status(observed_tasks, missing_tasks),
            "observed": observed_tasks,
            "missing": missing_tasks,
            "proof_tools": ["skill_generate_playable_slice(mode='submit_assets')", "gen_tripo_text_to_model"],
        },
        {
            "id": "tripo_credit_record",
            "label": "Confirmed Tripo credit guard or usage summary",
            "status": _gate_status(credit_observed, credit_missing),
            "observed": credit_observed,
            "missing": credit_missing,
            "proof_tools": ["gen_check_credit_budget", "skill_generate_playable_slice(mode='submit_assets')"],
        },
        {
            "id": "imported_generated_assets",
            "label": "Imported generated asset paths for all planned assets",
            "status": _gate_status(observed_imports, missing_imports),
            "observed": observed_imports,
            "missing": missing_imports,
            "proof_tools": ["gen_tripo_wait_for_task", "gen_tripo_import_to_project"],
        },
        {
            "id": "gameplay_assets_built",
            "label": "Player, enemy, HUD, and level/map assets built or updated",
            "status": _gate_status(gameplay_observed, gameplay_missing),
            "observed": gameplay_observed,
            "missing": gameplay_missing,
            "proof_tools": ["create_blueprint", "build_behavior_tree", "create_widget_blueprint", "spawn_actor"],
        },
        {
            "id": "compile_reports_clean",
            "label": "Touched Blueprint/widget compile reports are clean",
            "status": _gate_status(compile_observed, compile_missing),
            "observed": compile_observed,
            "missing": compile_missing,
            "proof_tools": ["compile_blueprint_and_report"],
        },
        {
            "id": "pie_runtime_log",
            "label": "PIE runtime evidence captured",
            "status": _gate_status(pie_observed, pie_missing),
            "observed": pie_observed,
            "missing": pie_missing,
            "proof_tools": ["pie_launch_session", "pie_capture_log"],
        },
        {
            "id": "viewport_screenshot",
            "label": "Viewport screenshot evidence captured",
            "status": _gate_status(screenshot_observed, screenshot_missing),
            "observed": screenshot_observed,
            "missing": screenshot_missing,
            "proof_tools": ["viewport_capture_screenshot"],
        },
        {
            "id": "final_vertical_slice_report",
            "label": "Final vertical-slice evidence report packaged",
            "status": _gate_status(report_observed, report_missing),
            "observed": report_observed,
            "missing": report_missing,
            "proof_tools": ["execution_journal_finish", "skill_package_vertical_slice_report"],
        },
    ]
    live_proven = all(gate["status"] == "proven" for gate in gates)
    next_steps = [
        f"{gate['id']}: {', '.join(gate['missing'])}"
        for gate in gates
        if gate["status"] != "proven"
    ]
    return {
        "schema": "unreal_mcp_playable_slice_evidence_readiness.v1",
        "live_playable_slice_proven": live_proven,
        "summary": "Live playable slice is proven." if live_proven else "Orchestration is ready, but live playable-slice proof is incomplete.",
        "asset_evidence": asset_rows,
        "gates": gates,
        "next_proof_steps": next_steps,
        "provided_evidence_keys": sorted(execution_evidence.keys()),
    }


def _build_playable_slice_orchestration(
    plan: Dict[str, Any],
    task_submissions: List[Dict[str, Any]],
    imported_assets: List[Dict[str, Any]],
    execution_evidence: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    wait_and_import: List[Dict[str, Any]] = []
    submission_matches = _match_asset_records(plan["assets"], task_submissions)
    import_matches = _match_asset_records(plan["assets"], imported_assets)
    for asset, submission, imported in zip(plan["assets"], submission_matches, import_matches):
        task_id = str(submission.get("task_id", "<task_id_from_submit_assets>"))
        wait_and_import.append({
            "asset_role": asset["role"],
            "asset_name": asset["name"],
            "task_id": task_id,
            "expected_content_path": asset["content_path"],
            "imported_asset_path": imported.get("asset_path", imported.get("imported_asset_path", "")),
            "tool_calls": [
                {
                    "tool": "gen_tripo_wait_for_task",
                    "args": {"task_id": task_id, "timeout_s": 900, "poll_s": 10},
                    "evidence": ["final task status", "progress", "downloadable output"],
                },
                {
                    "tool": "gen_tripo_import_to_project",
                    "args": {
                        "task_id": task_id,
                        "content_path": asset["content_path"],
                        "asset_name": asset["name"],
                        "create_material_instance": True,
                        "create_blueprint": False,
                    },
                    "evidence": ["static mesh path", "material paths", "import warnings"],
                },
            ],
        })

    gameplay = plan["gameplay"]
    base_path = plan["content_path"]
    blueprint_phase = {
        "phase": "assemble_playable_loop",
        "goal": gameplay["level_goal"],
        "tool_domains": [
            "gameplay_framework",
            "blueprint_asset",
            "blueprint_graph",
            "editor_actor_viewport",
            "ui_umg",
            "ai_behavior_tree",
            "diagnostics",
        ],
        "target_assets": {
            "player_blueprint": gameplay["player_blueprint"],
            "enemy_blueprint": gameplay["enemy_blueprint"],
            "behavior_tree": gameplay["behavior_tree"],
            "blackboard": gameplay["blackboard"],
            "hud_widget": gameplay["hud_widget"],
            "level_folder": f"{base_path}/Level",
        },
        "required_actions": [
            "Create or reuse a player pawn/controller and wire movement, camera, health, and interaction state.",
            "Create pickup/goal actors that use generated meshes, collision, and readable feedback.",
            "Create one enemy shell with patrol/chase behavior and assign Behavior Tree/Blackboard assets when AI is in scope.",
            "Place player start, imported meshes, enemy, lighting, nav bounds, collision volumes, and objective trigger in a compact arena.",
            "Create a compact HUD widget for objective, health, and completion feedback.",
        ],
        "compile_tools": ["compile_blueprint_and_report"],
        "readback_tools": ["scan_project_assets", "get_blueprint_nodes", "get_project_context"],
    }
    verification_phase = {
        "phase": "verify_and_report",
        "acceptance_criteria": plan["validation"].get("acceptance_criteria", ""),
        "required_evidence": plan["validation"].get("required_runtime_evidence", []),
        "tool_calls": [
            {"tool": "compile_blueprint_and_report", "args": {"blueprint_path": "<each_touched_blueprint_or_widget>"}},
            {"tool": "pie_launch_session", "args": {"map": "<current_or_created_level>"}},
            {"tool": "pie_capture_log", "args": {"max_lines": 200}},
            {"tool": "viewport_capture_screenshot", "args": {"label": "playable_slice_evidence"}},
            {"tool": "pie_stop_session", "args": {}},
            {
                "tool": "execution_journal_finish",
                "args": {
                    "journal_path": "<journal_path_from_execution_journal_start>",
                    "status": "<completed|completed_with_warnings|failed>",
                    "summary": "Summarize generated assets, gameplay assembly, compile results, PIE evidence, warnings, and follow-ups.",
                    "artifacts": ["<changed_asset_paths>", "<pie_log_path>", "<viewport_screenshot_path>"],
                    "verification": {
                        "compile": "<compile summary>",
                        "pie": "<PIE summary>",
                        "screenshot": "<screenshot path>",
                        "acceptance_criteria": plan["validation"].get("acceptance_criteria", ""),
                        "required_evidence": plan["validation"].get("required_runtime_evidence", []),
                    },
                },
            },
            {
                "tool": "skill_package_vertical_slice_report",
                "args": {
                    "title": f"Playable Slice Report - {_safe_name(plan['brief'], 'PlayableSlice')}",
                    "summary": "Summarize the completed playable loop, generated Tripo assets, Blueprint/UMG/AI/level changes, verification status, and remaining design-review work.",
                    "journal_path": "<journal_path_from_execution_journal_start_or_empty>",
                    "report_dir": "knowledge_base/Reports",
                    "project_name": "<project_or_map_name>",
                    "artifacts": [
                        "<changed_asset_paths>",
                        "<imported_generated_asset_paths>",
                        "<pie_log_path>",
                        "<viewport_screenshot_path>",
                    ],
                    "verification": {
                        "brief": plan["brief"],
                        "plan_schema": plan["schema"],
                        "acceptance_criteria": plan["validation"].get("acceptance_criteria", ""),
                        "required_evidence": plan["validation"].get("required_runtime_evidence", []),
                        "compile": "<compile_blueprint_and_report summaries>",
                        "pie": "<pie_launch_session and pie_capture_log summary>",
                        "screenshot": "<viewport_capture_screenshot path>",
                        "credit_usage": "<Tripo credit guard and usage summary>",
                        "warnings": "<unresolved warnings or empty list>",
                    },
                    "include_journal_entries": True,
                    "max_entries": 30,
                },
            },
        ],
        "green_report_requires": [
            "all touched Blueprints/widgets compile",
            "generated assets imported under the planned /Game path",
            "PIE launches without blocking runtime errors",
            "viewport screenshot shows the playable level",
            "final report lists warnings and human design-review follow-ups",
        ],
    }
    return {
        "schema": "unreal_mcp_playable_slice_orchestration.v1",
        "plan_schema": plan["schema"],
        "brief": plan["brief"],
        "content_path": plan["content_path"],
        "phases": [
            {
                "phase": "context",
                "tool_calls": [
                    {"tool": "get_project_context", "args": {}},
                    {"tool": "scan_project_assets", "args": {"path": "/Game", "depth": 3}},
                    {"tool": "list_available_tools", "args": {"domain": "all"}},
                    {"tool": "get_onboarding_context", "args": {"task": "blueprints"}},
                    {"tool": "get_onboarding_context", "args": {"task": "world_building"}},
                    {"tool": "get_onboarding_context", "args": {"task": "umg"}},
                    {
                        "tool": "execution_journal_start",
                        "args": {
                            "title": f"Playable Slice - {_safe_name(plan['brief'], 'PlayableSlice')}",
                            "goal": plan["brief"],
                            "project_name": "<project_or_map_name>",
                            "tags": ["playable_slice", "generative", "tripo"],
                        },
                    },
                ],
            },
            {"phase": "wait_and_import_generated_assets", "assets": wait_and_import},
            blueprint_phase,
            verification_phase,
        ],
        "evidence_contract": {
            "schema": "unreal_mcp_playable_slice_evidence_contract.v1",
            "asset_generation": ["task_id", "credit_guard", "provider output", "import result"],
            "gameplay": ["changed Blueprint/widget/map assets", "compile reports", "readback checks"],
            "runtime": ["PIE log", "PIE duration", "viewport screenshot", "warnings/errors"],
            "report": ["execution journal finish", "vertical slice report path"],
        },
        "evidence_readiness": _build_evidence_readiness(plan, task_submissions, imported_assets, execution_evidence or {}),
    }


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
    task_submissions_json: str = "",
    imported_assets_json: str = "",
    execution_evidence_json: str = "",
    asset_roles: str = "",
    gameplay_loop: str = "",
    acceptance_criteria: str = "",
    required_evidence: str = "",
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
        "asset_roles": asset_roles,
        "gameplay_loop": gameplay_loop,
        "acceptance_criteria": acceptance_criteria,
        "required_evidence": required_evidence,
        "task_submissions_json": task_submissions_json,
        "imported_assets_json": imported_assets_json,
        "execution_evidence_json": execution_evidence_json,
    }
    if safe_mode not in _VALID_MODES:
        return _structured(
            success=False,
            stage="invalid_mode",
            message="mode must be one of: preflight, plan, submit_assets, orchestrate",
            inputs=inputs,
            errors=["mode must be one of: preflight, plan, submit_assets, orchestrate"],
            t0=t0,
        )
    if safe_mode == "preflight":
        preflight = _run_live_preflight(session_name=session_name, estimated_credits=120)
        return _structured(
            success=bool(preflight.get("ready_for_live_spend")),
            stage="preflight_ready" if preflight.get("ready_for_live_spend") else "preflight_missing_gates",
            message=(
                "Playable-slice live preflight is ready for confirmed spend"
                if preflight.get("ready_for_live_spend")
                else "Playable-slice live preflight found missing readiness gates"
            ),
            inputs=inputs,
            outputs={
                "preflight": preflight,
                "network_required": False,
                "unreal_mutation_required": False,
                "spend_required": False,
                "execution_modes": sorted(_VALID_MODES),
            },
            warnings=[] if preflight.get("ready_for_live_spend") else list(preflight.get("next_actions", [])),
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

    plan = build_playable_slice_plan(
        brief,
        content_path,
        asset_roles=asset_roles,
        gameplay_loop=gameplay_loop,
        acceptance_criteria=acceptance_criteria,
        required_evidence=required_evidence,
    )
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
    if safe_mode == "orchestrate":
        task_submissions, task_errors = _parse_json_list(task_submissions_json, "task_submissions_json")
        imported_assets, import_errors = _parse_json_list(imported_assets_json, "imported_assets_json")
        execution_evidence, evidence_errors = _parse_json_object(execution_evidence_json, "execution_evidence_json")
        parse_errors = task_errors + import_errors + evidence_errors
        if parse_errors:
            return _structured(
                success=False,
                stage="orchestration_input_invalid",
                message="Playable-slice orchestration inputs were invalid",
                inputs=inputs,
                outputs={"plan": plan},
                errors=parse_errors,
                t0=t0,
            )
        orchestration = _build_playable_slice_orchestration(plan, task_submissions, imported_assets, execution_evidence)
        return _structured(
            success=True,
            stage="orchestration_ready",
            message="Playable-slice orchestration package is ready for import, gameplay assembly, PIE, and report phases",
            inputs=inputs,
            outputs={
                "plan": plan,
                "orchestration": orchestration,
                "network_required": False,
                "unreal_mutation_required": False,
                "execution_modes": sorted(_VALID_MODES),
            },
            warnings=[
                "This mode does not mutate Unreal; execute the returned tool calls in order and stop on destructive overwrite or failed compile.",
            ],
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
        task_submissions_json: str = "",
        imported_assets_json: str = "",
        execution_evidence_json: str = "",
        asset_roles: str = "",
        gameplay_loop: str = "",
        acceptance_criteria: str = "",
        required_evidence: str = "",
    ) -> str:
        """Plan or start a generated playable slice from one brief.

        Mode `preflight` runs a no-spend live-readiness check for Tripo auth,
        credit budget, packaged plugin build evidence, and bridge reachability.
        Mode `plan` validates the schema and returns the end-to-end tool
        sequence without network calls. Mode `submit_assets` requires
        TRIPO_API_KEY and confirm_spend=True before submitting paid Tripo tasks.
        Mode `orchestrate` returns a no-spend import/gameplay/PIE/report package
        from the plan plus optional submitted-task, imported-asset, and execution
        evidence JSON. Execution evidence is used only to mark proof gates as
        satisfied; orchestration itself never mutates Unreal.
        Optional asset_roles, gameplay_loop, acceptance_criteria, and
        required_evidence inputs let the Unreal Playable Slice UI steer the
        generated plan instead of relying on brief-only inference.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d7-playable-slice-skill
        Example:
            skill_generate_playable_slice(brief="third-person dungeon demo with a slime and a boss", mode="preflight", asset_roles="hero, key, boss")"""
        result = _impl(
            brief=brief,
            mode=mode,
            content_path=content_path,
            session_name=session_name,
            confirm_spend=confirm_spend,
            asset_roles=asset_roles,
            gameplay_loop=gameplay_loop,
            acceptance_criteria=acceptance_criteria,
            required_evidence=required_evidence,
            task_submissions_json=task_submissions_json,
            imported_assets_json=imported_assets_json,
            execution_evidence_json=execution_evidence_json,
        )
        return json.dumps(result)

    logger.info("Playable slice skill registered: skill_generate_playable_slice")
