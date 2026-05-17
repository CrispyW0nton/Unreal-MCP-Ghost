"""
exec_substrate.py — Safe Execution Substrate for Unreal-MCP-Ghost
==================================================================

Pillar 1 of the Scripting Supremacy architecture.  Every mutating Unreal
automation path should use the wrappers defined here instead of raw
exec_python calls.

Wrappers provided:
  exec_python_transactional   — wraps script in ScopedEditorTransaction
  exec_python_with_progress   — wraps script in ScopedSlowTask
  exec_python_capture_logs    — captures output log lines around a script
  exec_python_structured      — returns a normalised StructuredResult JSON

Tool family (13 MCP tools exposed):
  ue_exec_safe      — send any Python snippet using the safe substrate
  ue_exec_transact  — send a Python snippet wrapped in a named transaction
  ue_exec_progress  — send a Python snippet wrapped in a progress dialog
  execution_journal_* — create, append, and finish repo-local journals
  risk_evaluate_action — score planned mutations before execution
  pie_* / viewport_* — capture PIE/log/screenshot evidence for verification

Reference:
  https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python

The tools in this module are THIN wrappers.  The heavy exec_python machinery
already exists in the plugin; these wrappers only inject the correct Unreal
boilerplate around the caller's code before forwarding via exec_python.
"""

from __future__ import annotations

import json
import logging
import re
import hashlib
import ast
import textwrap
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

_RISK_LEVELS = ("low", "medium", "high", "critical")

# ── Shared result schema ──────────────────────────────────────────────────────
# Every tool in this project should trend toward this shape.

_EMPTY_RESULT: Dict[str, Any] = {
    "success": False,
    "stage": "",
    "message": "",
    "inputs": {},
    "outputs": {},
    "warnings": [],
    "errors": [],
    "log_tail": [],
}


def make_result(
    *,
    success: bool,
    stage: str = "",
    message: str = "",
    inputs: Optional[Dict] = None,
    outputs: Optional[Dict] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    log_tail: Optional[List[str]] = None,
    **extra,
) -> Dict[str, Any]:
    """Build a normalised StructuredResult dict."""
    r = dict(_EMPTY_RESULT)
    r["success"] = success
    r["stage"] = stage
    r["message"] = message
    r["inputs"] = inputs or {}
    r["outputs"] = outputs or {}
    r["warnings"] = warnings or []
    r["errors"] = errors or []
    r["log_tail"] = log_tail or []
    r.update(extra)
    return r


# ── Execution journal helpers ────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_workspace_path(path: str) -> Path:
    root = _workspace_root().resolve()
    candidate = Path(path or ".mcp_journals")
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside workspace root: {root}") from exc
    return resolved


def _slugify(value: str, default: str = "journal") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
    return (slug or default)[:64]


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        if isinstance(value, dict):
            return {str(k): _json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(v) for v in value]
        return str(value)


def _read_journal(path: str) -> Dict[str, Any]:
    journal_path = _resolve_workspace_path(path)
    if not journal_path.exists():
        raise FileNotFoundError(f"Execution journal not found: {journal_path}")
    with journal_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or data.get("schema") != "unreal_mcp_execution_journal.v1":
        raise ValueError(f"Not an Unreal-MCP execution journal: {journal_path}")
    return data


def _write_journal(path: str, data: Dict[str, Any]) -> Path:
    journal_path = _resolve_workspace_path(path)
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    with journal_path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(_json_safe(data), fh, indent=2)
        fh.write("\n")
    return journal_path


def _journal_stats(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_severity: Dict[str, int] = {}
    by_event_type: Dict[str, int] = {}
    failures = 0
    for entry in entries:
        severity = str(entry.get("severity", "info")).lower()
        event_type = str(entry.get("event_type", "event")).lower()
        by_severity[severity] = by_severity.get(severity, 0) + 1
        by_event_type[event_type] = by_event_type.get(event_type, 0) + 1
        if entry.get("success") is False or severity in {"error", "critical"}:
            failures += 1
    return {
        "entry_count": len(entries),
        "failure_count": failures,
        "by_severity": by_severity,
        "by_event_type": by_event_type,
    }


def _artifact_path(kind: str, name: str, extension: str) -> Path:
    stamp = _utc_now().replace(":", "").replace("-", "")
    safe_ext = extension.lstrip(".")
    return _resolve_workspace_path(".mcp_artifacts") / kind / f"{stamp}_{_slugify(name, kind)}.{safe_ext}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _png_dimensions(path: Path) -> Dict[str, int]:
    with path.open("rb") as fh:
        header = fh.read(24)
    if len(header) >= 24 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")
        return {"width": width, "height": height}
    return {"width": 0, "height": 0}


def _file_artifact_info(path: Path) -> Dict[str, Any]:
    resolved = _resolve_workspace_path(str(path))
    if not resolved.exists():
        raise FileNotFoundError(f"Artifact not found: {resolved}")
    info = {
        "path": str(resolved),
        "size_bytes": resolved.stat().st_size,
        "sha256": _sha256_file(resolved),
    }
    if resolved.suffix.lower() == ".png":
        info.update(_png_dimensions(resolved))
    return info


def compare_screenshot_files(
    baseline_path: str,
    candidate_path: str,
    pass_threshold: float = 0.995,
) -> Dict[str, Any]:
    """Compare two workspace-local screenshots with Pillow when available."""
    baseline = _resolve_workspace_path(baseline_path)
    candidate = _resolve_workspace_path(candidate_path)
    baseline_info = _file_artifact_info(baseline)
    candidate_info = _file_artifact_info(candidate)
    byte_equal = baseline_info["sha256"] == candidate_info["sha256"]
    dimensions_match = (
        baseline_info.get("width") == candidate_info.get("width")
        and baseline_info.get("height") == candidate_info.get("height")
    )
    method = "hash_size_dimension"
    similarity = 1.0 if byte_equal and dimensions_match else 0.0
    rms_difference = None

    try:
        from PIL import Image, ImageChops, ImageStat  # type: ignore

        with Image.open(baseline) as base_img, Image.open(candidate) as cand_img:
            if base_img.size == cand_img.size:
                method = "pillow_rms"
                diff = ImageChops.difference(base_img.convert("RGB"), cand_img.convert("RGB"))
                stat = ImageStat.Stat(diff)
                rms_difference = sum((value ** 2 for value in stat.rms)) ** 0.5 / len(stat.rms)
                similarity = max(0.0, 1.0 - (rms_difference / 255.0))
    except Exception:
        pass

    passed = similarity >= float(pass_threshold)
    return make_result(
        success=passed,
        stage="viewport_compare_screenshot",
        message="Screenshots match threshold" if passed else "Screenshots differ beyond threshold",
        inputs={
            "baseline_path": baseline_path,
            "candidate_path": candidate_path,
            "pass_threshold": pass_threshold,
        },
        outputs={
            "comparison_method": method,
            "similarity": similarity,
            "rms_difference": rms_difference,
            "byte_equal": byte_equal,
            "dimensions_match": dimensions_match,
            "baseline": baseline_info,
            "candidate": candidate_info,
        },
    )


def _risk_level_from_score(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _risk_gate(level: str) -> str:
    return {
        "low": "auto_allowed",
        "medium": "journal_required",
        "high": "explicit_confirmation_and_checkpoint",
        "critical": "manual_approval_required",
    }[level]


def evaluate_action_risk(
    *,
    action: str,
    target: str = "",
    operation_type: str = "unknown",
    asset_paths: Optional[List[str]] = None,
    destructive: bool = False,
    requires_compile: bool = False,
    affects_runtime: bool = False,
    touches_source: bool = False,
    estimated_scope: str = "single_asset",
    mitigations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Score an intended editor action before an agent mutates a project."""
    action_l = (action or "").lower()
    operation_l = (operation_type or "unknown").lower()
    scope_l = (estimated_scope or "single_asset").lower()
    assets = asset_paths or []
    mitigations = mitigations or []
    reasons: List[str] = []
    score = 0

    if operation_l in {"inspect", "read", "list", "describe", "capture"}:
        score += 5
        reasons.append("read-only or observational operation")
    elif operation_l in {"create", "add", "edit", "mutate", "configure", "repair"}:
        score += 30
        reasons.append("mutates editor/project state")
    elif operation_l in {"compile", "save", "build", "live_coding"}:
        score += 35
        reasons.append("compile/save/build operation can affect loaded editor state")
    elif operation_l in {"delete", "remove", "overwrite", "reset", "reparent"}:
        score += 65
        reasons.append("destructive or structurally risky operation")
    else:
        score += 20
        reasons.append("unknown operation type")

    destructive_words = ("delete", "remove", "overwrite", "reset", "reparent", "migrate", "rename")
    if destructive or any(word in action_l for word in destructive_words):
        score += 35
        reasons.append("destructive intent or destructive keyword detected")
    if requires_compile:
        score += 15
        reasons.append("requires Blueprint/C++ compile or VM recompile")
    if affects_runtime:
        score += 15
        reasons.append("affects runtime behavior")
    if touches_source:
        score += 25
        reasons.append("touches source code or plugin files")
    if scope_l in {"project", "project_wide", "all_assets", "global"}:
        score += 25
        reasons.append("project-wide scope")
    elif scope_l in {"multi_asset", "folder", "level"}:
        score += 15
        reasons.append("multi-asset or level scope")
    if len(assets) > 10:
        score += 15
        reasons.append("touches more than 10 assets")
    elif len(assets) > 1:
        score += 8
        reasons.append("touches multiple assets")
    if any(str(path).startswith("/") and not str(path).startswith("/Game") for path in assets):
        score += 8
        reasons.append("touches engine/plugin or non-game content")

    mitigation_text = " ".join(mitigations).lower()
    if "backup" in mitigation_text or "checkpoint" in mitigation_text:
        score -= 10
        reasons.append("checkpoint/backup mitigation provided")
    if "journal" in mitigation_text:
        score -= 5
        reasons.append("journal mitigation provided")
    if "dry" in mitigation_text or "preview" in mitigation_text:
        score -= 8
        reasons.append("dry-run or preview mitigation provided")

    score = max(0, min(100, score))
    level = _risk_level_from_score(score)
    gate = _risk_gate(level)
    checklist = [
        "Discover current project state before mutation.",
        "Record the action in an execution journal.",
        "Return verification evidence after the action.",
    ]
    if level in {"high", "critical"}:
        checklist.insert(0, "Create or confirm a checkpoint before proceeding.")
    if destructive or level == "critical":
        checklist.insert(0, "Get explicit human approval before proceeding.")
    if requires_compile:
        checklist.append("Compile or recompile affected assets and capture diagnostics.")

    return make_result(
        success=True,
        stage="risk_evaluation",
        message=f"Risk level: {level}",
        inputs={
            "action": action,
            "target": target,
            "operation_type": operation_type,
            "asset_paths": assets,
            "destructive": destructive,
            "requires_compile": requires_compile,
            "affects_runtime": affects_runtime,
            "touches_source": touches_source,
            "estimated_scope": estimated_scope,
            "mitigations": mitigations,
        },
        outputs={
            "risk_level": level,
            "risk_score": score,
            "recommended_gate": gate,
            "can_autoproceed": level in {"low", "medium"} and not destructive,
            "reasons": reasons,
            "checklist": checklist,
        },
    )


# ── Transport helper ──────────────────────────────────────────────────────────

def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = unreal.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error(f"exec_substrate._send error: {exc}")
        return {"success": False, "message": str(exc)}


def _parse_ue_json(resp: Dict[str, Any]) -> Dict[str, Any]:
    inner = resp.get("result", resp)
    command_result = inner.get("command_result", resp.get("command_result"))
    if command_result not in (None, "", "None"):
        try:
            parsed = ast.literal_eval(command_result) if isinstance(command_result, str) else command_result
            if isinstance(parsed, str):
                return json.loads(parsed)
            if isinstance(parsed, dict):
                return parsed
        except (SyntaxError, ValueError, json.JSONDecodeError):
            pass
    output = inner.get("output", resp.get("output", "")) or ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[Info] "):
            line = line[7:]
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    if not inner.get("success", True):
        return {"success": False, "error": inner.get("message", output or "exec_python failed")}
    return {"success": False, "error": f"Could not parse UE output: {output!r}"}


# ── Python snippet builders ───────────────────────────────────────────────────

def _wrap_transactional(user_code: str, transaction_name: str) -> str:
    """Inject ScopedEditorTransaction around user_code."""
    safe_name = transaction_name.replace('"', '\\"')
    return textwrap.dedent(f"""\
        import unreal, sys, json

        with unreal.ScopedEditorTransaction("{safe_name}") as _trans:
            try:
                _result = {{}}
                _warnings = []
                _errors = []
{textwrap.indent(user_code, '        ')}
                print(json.dumps({{
                    "success": True,
                    "stage": "transaction_complete",
                    "message": "Transaction '{safe_name}' committed",
                    "outputs": _result,
                    "warnings": _warnings,
                    "errors": _errors,
                }}))
            except Exception as _exc:
                _trans.cancel()
                print(json.dumps({{
                    "success": False,
                    "stage": "transaction_rolled_back",
                    "message": str(_exc),
                    "errors": [str(_exc)],
                }}))
        sys.stdout.flush()
    """)


def _wrap_with_progress(user_code: str, task_name: str, total_work: int = 100) -> str:
    """Inject ScopedSlowTask around user_code for progress reporting."""
    safe_name = task_name.replace('"', '\\"')
    return textwrap.dedent(f"""\
        import unreal, sys, json

        with unreal.ScopedSlowTask({total_work}, "{safe_name}") as _task:
            _task.make_dialog(True)  # show cancel button
            try:
                _result = {{}}
                _warnings = []
                _errors = []
{textwrap.indent(user_code, '        ')}
                print(json.dumps({{
                    "success": True,
                    "stage": "progress_complete",
                    "message": "Task '{safe_name}' completed",
                    "outputs": _result,
                    "warnings": _warnings,
                    "errors": _errors,
                }}))
            except Exception as _exc:
                print(json.dumps({{
                    "success": False,
                    "stage": "progress_task_failed",
                    "message": str(_exc),
                    "errors": [str(_exc)],
                }}))
        sys.stdout.flush()
    """)


def _wrap_structured(user_code: str, stage_name: str) -> str:
    """
    Wrap user_code in a try/except that always returns a StructuredResult JSON.

    The user_code is expected to populate _result, _warnings, _errors dicts/lists.
    Example in user_code:
        _result["asset_path"] = "/Game/..."
        _warnings.append("Texture sRGB was reset")
    """
    safe_stage = stage_name.replace('"', '\\"')
    return textwrap.dedent(f"""\
        import unreal, sys, json

        _result = {{}}
        _warnings = []
        _errors = []
        _log_tail = []

        try:
{textwrap.indent(user_code, '    ')}
            print(json.dumps({{
                "success": True,
                "stage": "{safe_stage}",
                "message": "Operation completed",
                "outputs": _result,
                "warnings": _warnings,
                "errors": _errors,
                "log_tail": _log_tail,
            }}))
        except Exception as _exc:
            import traceback as _tb
            print(json.dumps({{
                "success": False,
                "stage": "{safe_stage}",
                "message": str(_exc),
                "outputs": _result,
                "warnings": _warnings,
                "errors": [str(_exc)],
                "log_tail": _tb.format_exc().splitlines()[-10:],
            }}))
        sys.stdout.flush()
    """)


def _wrap_structured_eval_expression(user_code: str, stage_name: str) -> str:
    """Return an evaluate_statement expression that yields a StructuredResult dict."""
    safe_stage = stage_name.replace('"', '\\"')
    script = f"""import unreal, json, traceback

_result = {{}}
_warnings = []
_errors = []
_log_tail = []

try:
{textwrap.indent(user_code, '    ')}
    _mcp_result = {{
        "success": True,
        "stage": "{safe_stage}",
        "message": "Operation completed",
        "outputs": _result,
        "warnings": _warnings,
        "errors": _errors,
        "log_tail": _log_tail,
    }}
except Exception as _exc:
    _mcp_result = {{
        "success": False,
        "stage": "{safe_stage}",
        "message": str(_exc),
        "outputs": _result,
        "warnings": _warnings,
        "errors": [str(_exc)],
        "log_tail": traceback.format_exc().splitlines()[-10:],
    }}
"""
    return f"(lambda ns: (exec({script!r}, ns), ns.get('_mcp_result', {{}}))[1])({{}})"


# ── Public helpers exported to other tool modules ─────────────────────────────

def exec_python_transactional(user_code: str, transaction_name: str) -> Dict[str, Any]:
    """
    Run user_code inside a ScopedEditorTransaction.

    On success: the entire snippet is committed as one undo step.
    On failure: the transaction is cancelled (changes rolled back where possible).

    Returns a StructuredResult dict.
    """
    code = _wrap_transactional(user_code, transaction_name)
    resp = _send("exec_python", {"code": code})
    return _parse_ue_json(resp)


def exec_python_with_progress(
    user_code: str, task_name: str, total_work: int = 100
) -> Dict[str, Any]:
    """
    Run user_code inside a ScopedSlowTask with a cancel button.

    Returns a StructuredResult dict.
    """
    code = _wrap_with_progress(user_code, task_name, total_work)
    resp = _send("exec_python", {"code": code})
    return _parse_ue_json(resp)


def exec_python_structured(user_code: str, stage_name: str = "script") -> Dict[str, Any]:
    """
    Run user_code with automatic try/except and structured JSON output.

    User_code should populate _result{}, _warnings[], _errors[] as needed.
    Returns a StructuredResult dict.
    """
    code = _wrap_structured_eval_expression(user_code, stage_name)
    resp = _send("exec_python", {"code": code, "mode": "evaluate_statement"})
    result = _parse_ue_json(resp)
    # Normalise to ensure all schema keys present
    for key in ("success", "stage", "message", "outputs", "warnings", "errors", "log_tail"):
        if key not in result:
            result[key] = _EMPTY_RESULT[key]
    return result


# ── MCP tools ─────────────────────────────────────────────────────────────────

def register_exec_substrate_tools(mcp: FastMCP):

    @mcp.tool()
    async def ue_exec_safe(
        ctx: Context,
        code: str,
        stage_name: str = "script",
    ) -> str:
        """Run a Python snippet inside Unreal Engine with automatic structured error handling.

        Unlike the raw exec_python, this tool:
        - Wraps code in a try/except that always produces valid JSON
        - Returns a normalised StructuredResult with success, stage, message,
          outputs, warnings, errors, and log_tail
        - Is safe to call from the AI without worrying about parse failures

        Your code should populate these variables:
          _result   : dict   — key/value outputs to return to the caller
          _warnings : list   — non-fatal warnings
          _errors   : list   — error messages (also raised via exception)

        Example code:
            import unreal
            bp = unreal.load_asset('/Game/Blueprints/BP_Player')
            if bp:
                _result['class_name'] = bp.get_class().get_name()
            else:
                _errors.append('Blueprint not found')

        Args:
            code:       Python snippet to execute in Unreal Engine
            stage_name: Descriptive name for the operation (used in result.stage)

        Returns:
            JSON string with StructuredResult:
            {
              "success": true,
              "stage": "script",
              "message": "Operation completed",
              "outputs": {...},
              "warnings": [],
              "errors": [],
              "log_tail": []
            }
        """
        result = exec_python_structured(code, stage_name)
        return json.dumps(result)

    @mcp.tool()
    async def ue_exec_transact(
        ctx: Context,
        code: str,
        transaction_name: str = "MCP Operation",
    ) -> str:
        """Run a Python snippet inside a named ScopedEditorTransaction.

        Wraps the code in an Unreal transaction so that the entire operation
        appears as ONE undo step in the UE5 editor.  If the code raises an
        exception, the transaction is cancelled and the editor state is rolled
        back to its pre-transaction position.

        This is the PREFERRED way to run any mutating Unreal Python:
        - Blueprint modifications
        - Asset property changes
        - Component additions
        - Material edits

        Your code should populate _result{}, _warnings[], _errors[] as needed
        (same contract as ue_exec_safe).

        Args:
            code:             Python snippet to execute inside the transaction
            transaction_name: Name shown in the UE5 Edit menu under Undo History

        Returns:
            JSON string with StructuredResult.
        """
        result = exec_python_transactional(code, transaction_name)
        return json.dumps(result)

    @mcp.tool()
    async def ue_exec_progress(
        ctx: Context,
        code: str,
        task_name: str = "MCP Task",
        total_work: int = 100,
    ) -> str:
        """Run a Python snippet inside a ScopedSlowTask with a progress dialog.

        Use this for long-running operations (bulk imports, retargeting, etc.)
        to keep the UE5 editor responsive and show a cancel button.

        Your code can call:
            _task.enter_progress_frame(N, "Step description")
        to advance the progress bar by N units.

        Args:
            code:       Python snippet to execute with progress reporting
            task_name:  Label shown in the Unreal progress dialog
            total_work: Total work units for the progress bar (default 100)

        Returns:
            JSON string with StructuredResult.
        """
        result = exec_python_with_progress(code, task_name, total_work)
        return json.dumps(result)

    @mcp.tool()
    async def execution_journal_start(
        ctx: Context,
        title: str,
        goal: str = "",
        project_name: str = "",
        journal_dir: str = ".mcp_journals",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Start a repo-local execution journal for an autonomous work session.

        The journal is a JSON file with an immutable id, timestamps, inputs,
        entries, artifacts, and final verification data. Paths are constrained
        to the current workspace root so agents cannot quietly write elsewhere.

        Args:
            title: Human-readable journal title
            goal: What the agent intends to accomplish
            project_name: Optional Unreal project or map name
            journal_dir: Workspace-relative directory for journal files
            tags: Optional labels for later search
            metadata: Optional extra context such as branch, map, or project path

        Returns:
            JSON string with StructuredResult and the created journal path.
        """
        journal_id = uuid.uuid4().hex[:12]
        started_at = _utc_now()
        journal_root = _resolve_workspace_path(journal_dir)
        file_name = f"{started_at.replace(':', '').replace('-', '')}_{_slugify(title)}_{journal_id}.json"
        journal_path = journal_root / file_name
        data = {
            "schema": "unreal_mcp_execution_journal.v1",
            "journal_id": journal_id,
            "title": title,
            "goal": goal,
            "project_name": project_name,
            "status": "in_progress",
            "started_at": started_at,
            "finished_at": "",
            "tags": tags or [],
            "metadata": metadata or {},
            "entries": [],
            "artifacts": [],
            "verification": {},
            "summary": "",
            "stats": _journal_stats([]),
        }
        _write_journal(str(journal_path), data)
        result = make_result(
            success=True,
            stage="execution_journal_start",
            message="Execution journal started",
            inputs={
                "title": title,
                "goal": goal,
                "project_name": project_name,
                "journal_dir": journal_dir,
                "tags": tags or [],
            },
            outputs={
                "journal_id": journal_id,
                "journal_path": str(journal_path),
                "status": "in_progress",
                "started_at": started_at,
            },
        )
        return json.dumps(result)

    @mcp.tool()
    async def execution_journal_log(
        ctx: Context,
        journal_path: str,
        message: str,
        event_type: str = "progress",
        tool_name: str = "",
        success: bool = True,
        severity: str = "info",
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        artifacts: Optional[List[str]] = None,
        risk_level: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Append a structured entry to an execution journal.

        Args:
            journal_path: Path returned by execution_journal_start
            message: Short progress, validation, or failure note
            event_type: progress, tool_call, verification, decision, error, etc.
            tool_name: Optional MCP tool or Unreal command name
            success: Whether this step succeeded
            severity: debug, info, warning, error, or critical
            inputs: Optional summarized inputs for the step
            outputs: Optional summarized outputs or evidence
            artifacts: Optional file or asset paths produced/observed
            risk_level: Optional low/medium/high/critical risk label
            metadata: Optional additional data for later audit

        Returns:
            JSON string with StructuredResult and updated journal stats.
        """
        data = _read_journal(journal_path)
        if data.get("status") == "finished":
            return json.dumps(make_result(
                success=False,
                stage="execution_journal_log",
                message="Cannot log to a finished journal",
                inputs={"journal_path": journal_path},
                errors=["Journal status is finished"],
            ))
        entry = {
            "entry_id": uuid.uuid4().hex[:12],
            "timestamp": _utc_now(),
            "event_type": event_type,
            "severity": severity,
            "success": success,
            "tool_name": tool_name,
            "message": message,
            "risk_level": risk_level if risk_level in _RISK_LEVELS else risk_level,
            "inputs": inputs or {},
            "outputs": outputs or {},
            "artifacts": artifacts or [],
            "metadata": metadata or {},
        }
        data.setdefault("entries", []).append(_json_safe(entry))
        if artifacts:
            existing = set(data.setdefault("artifacts", []))
            for artifact in artifacts:
                if artifact not in existing:
                    data["artifacts"].append(artifact)
                    existing.add(artifact)
        data["stats"] = _journal_stats(data["entries"])
        _write_journal(journal_path, data)
        result = make_result(
            success=True,
            stage="execution_journal_log",
            message="Execution journal entry appended",
            inputs={"journal_path": journal_path, "event_type": event_type, "severity": severity},
            outputs={
                "entry_id": entry["entry_id"],
                "journal_id": data.get("journal_id"),
                "entry_count": data["stats"]["entry_count"],
                "stats": data["stats"],
            },
        )
        return json.dumps(result)

    @mcp.tool()
    async def execution_journal_finish(
        ctx: Context,
        journal_path: str,
        status: str = "completed",
        summary: str = "",
        artifacts: Optional[List[str]] = None,
        verification: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Finish an execution journal and record final evidence.

        Args:
            journal_path: Path returned by execution_journal_start
            status: completed, completed_with_warnings, failed, blocked, or cancelled
            summary: Short human-readable closeout
            artifacts: Optional final file, asset, screenshot, or log paths
            verification: Optional final test/diagnostic evidence

        Returns:
            JSON string with StructuredResult and final journal stats.
        """
        data = _read_journal(journal_path)
        finished_at = _utc_now()
        data["status"] = status
        data["finished_at"] = finished_at
        data["summary"] = summary
        if artifacts:
            existing = set(data.setdefault("artifacts", []))
            for artifact in artifacts:
                if artifact not in existing:
                    data["artifacts"].append(artifact)
                    existing.add(artifact)
        data["verification"] = verification or {}
        data["stats"] = _journal_stats(data.get("entries", []))
        _write_journal(journal_path, data)
        result = make_result(
            success=status not in {"failed", "blocked", "cancelled"},
            stage="execution_journal_finish",
            message="Execution journal finished",
            inputs={"journal_path": journal_path, "status": status},
            outputs={
                "journal_id": data.get("journal_id"),
                "journal_path": str(_resolve_workspace_path(journal_path)),
                "status": status,
                "started_at": data.get("started_at"),
                "finished_at": finished_at,
                "summary": summary,
                "artifacts": data.get("artifacts", []),
                "verification": data.get("verification", {}),
                "stats": data["stats"],
            },
        )
        return json.dumps(result)

    @mcp.tool()
    async def risk_evaluate_action(
        ctx: Context,
        action: str,
        target: str = "",
        operation_type: str = "unknown",
        asset_paths: Optional[List[str]] = None,
        destructive: bool = False,
        requires_compile: bool = False,
        affects_runtime: bool = False,
        touches_source: bool = False,
        estimated_scope: str = "single_asset",
        mitigations: Optional[List[str]] = None,
    ) -> str:
        """Evaluate action risk before an autonomous agent mutates the project.

        Args:
            action: Natural-language action description
            target: Actor, asset, subsystem, file, or feature target
            operation_type: inspect/read/create/edit/delete/compile/save/build/etc.
            asset_paths: Optional affected Unreal asset paths
            destructive: True for deletion, overwrite, reset, or irreversible edits
            requires_compile: True when Blueprint/C++ compile or VM recompile is needed
            affects_runtime: True when gameplay behavior may change
            touches_source: True when C++/Python/plugin source files are involved
            estimated_scope: single_asset, multi_asset, folder, level, or project_wide
            mitigations: Existing safeguards such as checkpoint, journal, dry-run, tests

        Returns:
            JSON string with risk level, score, recommended gate, reasons, and checklist.
        """
        result = evaluate_action_risk(
            action=action,
            target=target,
            operation_type=operation_type,
            asset_paths=asset_paths or [],
            destructive=destructive,
            requires_compile=requires_compile,
            affects_runtime=affects_runtime,
            touches_source=touches_source,
            estimated_scope=estimated_scope,
            mitigations=mitigations or [],
        )
        return json.dumps(result)

    @mcp.tool()
    async def pie_launch_session(
        ctx: Context,
        mode: str = "simulate",
        wait_seconds: float = 0.5,
    ) -> str:
        """Request a PIE or Simulate session from the Unreal Editor.

        Args:
            mode: "simulate" for Simulate In Editor, otherwise requests normal PIE
            wait_seconds: Short post-request delay before reporting session state

        Returns:
            JSON string with requested mode, prior state, current state, and PIE world count.
        """
        code = textwrap.dedent(f"""\
            import time
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            was_in_pie = bool(subsystem.is_in_play_in_editor())
            requested_mode = {mode!r}
            if not was_in_pie:
                if str(requested_mode).lower() in ("simulate", "sie"):
                    subsystem.editor_play_simulate()
                    requested_mode = "simulate"
                else:
                    subsystem.editor_request_begin_play()
                    requested_mode = "play"
                time.sleep(max(0.0, min(float({wait_seconds!r}), 5.0)))
            pie_worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            _result["requested_mode"] = requested_mode
            _result["launch_requested"] = not was_in_pie
            _result["was_in_pie"] = was_in_pie
            _result["is_in_play_in_editor"] = bool(subsystem.is_in_play_in_editor())
            _result["pie_world_count"] = len(pie_worlds)
            _result["pie_world_names"] = [w.get_name() for w in pie_worlds]
            _result["readback_note"] = "PIE/SIE state may update on the next editor tick after the request returns"
        """)
        result = exec_python_structured(code, "pie_launch_session")
        return json.dumps(result)

    @mcp.tool()
    async def pie_stop_session(
        ctx: Context,
        wait_seconds: float = 0.5,
    ) -> str:
        """Request the active PIE/SIE session to stop.

        Args:
            wait_seconds: Short post-request delay before reporting session state

        Returns:
            JSON string with prior and current PIE state.
        """
        code = textwrap.dedent(f"""\
            import time
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            was_in_pie = bool(subsystem.is_in_play_in_editor())
            if was_in_pie:
                subsystem.editor_request_end_play()
                try:
                    unreal.EditorLevelLibrary.editor_end_play()
                except Exception:
                    pass
                time.sleep(max(0.0, min(float({wait_seconds!r}), 5.0)))
            pie_worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
            _result["stop_requested"] = was_in_pie
            _result["was_in_pie"] = was_in_pie
            _result["is_in_play_in_editor"] = bool(subsystem.is_in_play_in_editor())
            _result["pie_world_count"] = len(pie_worlds)
            _result["pie_world_names"] = [w.get_name() for w in pie_worlds]
            _result["readback_note"] = "PIE/SIE state may update on the next editor tick after the request returns"
        """)
        result = exec_python_structured(code, "pie_stop_session")
        return json.dumps(result)

    @mcp.tool()
    async def pie_capture_log(
        ctx: Context,
        max_lines: int = 200,
        contains: str = "",
        save_artifact: bool = False,
        artifact_name: str = "pie_log",
    ) -> str:
        """Capture the tail of the current Unreal project log for verification.

        Args:
            max_lines: Maximum number of log lines to return
            contains: Optional case-insensitive filter
            save_artifact: Save captured lines to `.mcp_artifacts/logs`
            artifact_name: Artifact filename stem when saving

        Returns:
            JSON string with log file path, captured lines, and optional artifact path.
        """
        artifact_path = str(_artifact_path("logs", artifact_name, "log")) if save_artifact else ""
        code = textwrap.dedent(f"""\
            import pathlib
            log_dir = pathlib.Path(unreal.Paths.project_log_dir())
            logs = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
            if not logs:
                raise RuntimeError(f"No Unreal log files found in {{log_dir}}")
            log_file = logs[-1]
            raw_lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            filter_text = {contains!r}.lower()
            if filter_text:
                raw_lines = [line for line in raw_lines if filter_text in line.lower()]
            limit = max(1, min(int({max_lines!r}), 2000))
            captured = raw_lines[-limit:]
            artifact_path = {artifact_path!r}
            if artifact_path:
                out = pathlib.Path(artifact_path)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text("\\n".join(captured) + "\\n", encoding="utf-8")
            _result["log_file"] = str(log_file)
            _result["log_dir"] = str(log_dir)
            _result["line_count"] = len(captured)
            _result["contains"] = {contains!r}
            _result["lines"] = captured
            _result["artifact_path"] = artifact_path
        """)
        result = exec_python_structured(code, "pie_capture_log")
        return json.dumps(result)

    @mcp.tool()
    async def pie_simulate_input(
        ctx: Context,
        console_command: str,
        player_index: int = 0,
        require_pie: bool = True,
    ) -> str:
        """Send a console-command style input to the active PIE world.

        This intentionally starts with console commands because they are stable,
        scriptable, and auditable. Higher-fidelity key/mouse injection can build
        on top after the PIE loop has enough evidence capture.

        Args:
            console_command: Console command to execute, such as `stat fps`
            player_index: Local player controller index
            require_pie: Fail when no PIE/SIE session is active

        Returns:
            JSON string with command dispatch details.
        """
        code = textwrap.dedent(f"""\
            subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
            in_pie = bool(subsystem.is_in_play_in_editor())
            if {bool(require_pie)!r} and not in_pie:
                raise RuntimeError("No active PIE/SIE session; launch PIE before simulating input")
            world = unreal.EditorLevelLibrary.get_game_world()
            if world is None:
                world = unreal.EditorLevelLibrary.get_editor_world()
            controller = None
            try:
                controller = unreal.GameplayStatics.get_player_controller(world, int({player_index!r}))
            except Exception:
                controller = None
            unreal.SystemLibrary.execute_console_command(world, {console_command!r}, controller)
            _result["console_command"] = {console_command!r}
            _result["player_index"] = int({player_index!r})
            _result["required_pie"] = {bool(require_pie)!r}
            _result["was_in_pie"] = in_pie
            _result["world_name"] = world.get_name() if world else ""
            _result["controller_name"] = controller.get_name() if controller else ""
        """)
        result = exec_python_structured(code, "pie_simulate_input")
        return json.dumps(result)

    @mcp.tool()
    async def viewport_capture_screenshot(
        ctx: Context,
        artifact_name: str = "viewport",
        screenshot_dir: str = ".mcp_artifacts/screenshots",
        show_ui: bool = False,
        resolution: Optional[List[int]] = None,
    ) -> str:
        """Capture the active Unreal viewport to a workspace-local PNG artifact.

        Args:
            artifact_name: Screenshot filename stem
            screenshot_dir: Workspace-relative output directory
            show_ui: Forwarded to the native screenshot command when supported
            resolution: Forwarded to the native screenshot command when supported

        Returns:
            JSON string with filepath, dimensions, size, and hash.
        """
        out_dir = _resolve_workspace_path(screenshot_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        filepath = out_dir / f"{_utc_now().replace(':', '').replace('-', '')}_{_slugify(artifact_name, 'viewport')}.png"
        response = _send("take_screenshot", {
            "filepath": str(filepath),
            "show_ui": show_ui,
            "resolution": resolution or [1920, 1080],
        })
        if response.get("status") == "error" or response.get("success") is False:
            result = make_result(
                success=False,
                stage="viewport_capture_screenshot",
                message=response.get("error") or response.get("message", "Screenshot command failed"),
                inputs={"artifact_name": artifact_name, "screenshot_dir": screenshot_dir},
                errors=[response.get("error") or response.get("message", "Screenshot command failed")],
            )
            return json.dumps(result)
        try:
            info = _file_artifact_info(filepath)
            result = make_result(
                success=True,
                stage="viewport_capture_screenshot",
                message="Viewport screenshot captured",
                inputs={"artifact_name": artifact_name, "screenshot_dir": screenshot_dir},
                outputs=info,
            )
        except Exception as exc:
            result = make_result(
                success=False,
                stage="viewport_capture_screenshot",
                message=str(exc),
                inputs={"artifact_name": artifact_name, "screenshot_dir": screenshot_dir},
                errors=[str(exc)],
                outputs={"native_response": response},
            )
        return json.dumps(result)

    @mcp.tool()
    async def viewport_compare_screenshot(
        ctx: Context,
        baseline_path: str,
        candidate_path: str,
        pass_threshold: float = 0.995,
    ) -> str:
        """Compare two workspace-local viewport screenshot artifacts.

        Args:
            baseline_path: Workspace-local baseline PNG path
            candidate_path: Workspace-local candidate PNG path
            pass_threshold: Similarity threshold, 0-1

        Returns:
            JSON string with similarity and artifact metadata.
        """
        try:
            result = compare_screenshot_files(baseline_path, candidate_path, pass_threshold)
        except Exception as exc:
            result = make_result(
                success=False,
                stage="viewport_compare_screenshot",
                message=str(exc),
                inputs={
                    "baseline_path": baseline_path,
                    "candidate_path": candidate_path,
                    "pass_threshold": pass_threshold,
                },
                errors=[str(exc)],
            )
        return json.dumps(result)
