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

Tool family (2 MCP tools exposed):
  ue_exec_safe      — send any Python snippet using the safe substrate
  ue_exec_transact  — send a Python snippet wrapped in a named transaction

Reference:
  https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python

The tools in this module are THIN wrappers.  The heavy exec_python machinery
already exists in the plugin; these wrappers only inject the correct Unreal
boilerplate around the caller's code before forwarding via exec_python.
"""

from __future__ import annotations

import json
import logging
import textwrap
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

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
    code = _wrap_structured(user_code, stage_name)
    resp = _send("exec_python", {"code": code})
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
