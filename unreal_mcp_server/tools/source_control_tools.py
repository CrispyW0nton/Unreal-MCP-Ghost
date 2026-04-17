"""
source_control_tools.py — V5 Source Control (read-only)
=========================================================

Read-only source control introspection tools.  These tools NEVER check out,
submit, lock, or modify any file.  They query the active source control
provider (Perforce, SVN, Git, or None) and return the results as structured data.

Graceful degradation: when no provider is configured, every tool returns
success=True with provider="None", available=False — they never raise or
return success=False purely because SC is not set up.

Implementation strategy:
  - Routes the queries through exec_python to the UE5 editor's
    ISourceControlModule (available in the editor Python API).
  - When ISourceControlModule is not available (e.g. running tests offline),
    returns the "None provider" stub.

Tools:
  sc_get_provider_info — identify the active SC provider
  sc_get_status        — per-file state (checked_out, added, unchanged, etc.)
  sc_get_changelist    — files in a named or default changelist
"""

from __future__ import annotations

import json
import logging
import textwrap
import time
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

# ── Error codes ───────────────────────────────────────────────────────────────

ERR_NOT_CONNECTED     = "ERR_UNREAL_NOT_CONNECTED"
ERR_SC_UNAVAILABLE    = "ERR_SC_PROVIDER_UNAVAILABLE"
ERR_INTERNAL          = "ERR_INTERNAL"

# ── Shared helpers ────────────────────────────────────────────────────────────

def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        conn = get_unreal_connection()
        if not conn:
            return {"success": False, "error_code": ERR_NOT_CONNECTED,
                    "message": "Not connected to Unreal Engine"}
        result = conn.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error(f"source_control._send error: {exc}")
        return {"success": False, "message": str(exc)}


def _exec_python(code: str) -> Dict[str, Any]:
    """Run code via exec_python on UE5.  Module-level so tests can patch it."""
    return _send("exec_python", {"code": code})


def _ok(raw: Dict[str, Any]) -> bool:
    return bool(raw and raw.get("success") is not False and raw.get("status") != "error")


def _make_result(
    *,
    success: bool,
    stage: str = "",
    message: str = "",
    outputs: Optional[Dict] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    error_code: Optional[str] = None,
    meta: Optional[Dict] = None,
) -> Dict[str, Any]:
    r: Dict[str, Any] = {
        "success":  success,
        "stage":    stage,
        "message":  message,
        "outputs":  outputs or {},
        "warnings": warnings or [],
        "errors":   errors or [],
        "log_tail": [],
    }
    if error_code:
        r["error_code"] = error_code
    if meta:
        r["meta"] = meta
    return r


def _meta_dict(tool: str, t0: float, **extra) -> Dict[str, Any]:
    m: Dict[str, Any] = {"tool": tool, "duration_ms": int((time.monotonic() - t0) * 1000)}
    m.update(extra)
    return m


# ── SC state normalisation ────────────────────────────────────────────────────

_SC_STATE_MAP = {
    # UE ISourceControlState string → our canonical name
    "checked out":        "checked_out",
    "checkedout":         "checked_out",
    "added":              "added",
    "add":                "added",
    "deleted":            "deleted",
    "delete":             "deleted",
    "conflicted":         "conflicted",
    "conflict":           "conflicted",
    "unchanged":          "unchanged",
    "not in depot":       "not_in_depot",
    "notindepot":         "not_in_depot",
    "ignored":            "ignored",
    "unknown":            "unknown",
}


def _normalise_state(raw_state: str) -> str:
    return _SC_STATE_MAP.get(raw_state.lower().strip(), "unknown")


# ── Registration ──────────────────────────────────────────────────────────────

def register_source_control_tools(mcp: FastMCP):  # noqa: C901

    # ──────────────────────────────────────────────────────────────────────────
    # sc_get_provider_info
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def sc_get_provider_info(ctx: Context) -> str:
        """Get information about the active source control provider.

        Always returns success=True.  When no SC provider is configured,
        returns provider='None', available=False — this is not an error.

        Returns:
            JSON StructuredResult with outputs:
              provider   — 'Perforce' | 'Subversion' | 'Git' | 'None'
              available  — bool
              workspace  — workspace/client name (Perforce only, else '')
              server     — server address (else '')
              user       — SC username (else '')
        """
        t0 = time.monotonic()

        code = textwrap.dedent("""
            import unreal
            _result = {'provider': 'None', 'available': False, 'workspace': '', 'server': '', 'user': ''}
            try:
                sc = unreal.SourceControlHelpers
                provider = sc.get_provider_name()
                _result['provider']  = str(provider) if provider else 'None'
                _result['available'] = sc.is_available()
                # Perforce-specific fields
                try:
                    status = sc.get_provider().get_status_text()
                    _result['status_text'] = str(status) if status else ''
                except Exception:
                    _result['status_text'] = ''
            except AttributeError:
                # SourceControlHelpers not available in this UE version / configuration
                pass
            except Exception as _e:
                _result['error'] = str(_e)
        """)

        raw = _exec_python(code)
        if not _ok(raw):
            # Not connected — return the stub rather than an error
            outputs = {"provider": "None", "available": False, "workspace": "", "server": "", "user": ""}
            return json.dumps(_make_result(
                success=True, stage="sc_get_provider_info",
                message="UE5 not connected — source control unavailable",
                outputs=outputs,
                warnings=["UE5 not reachable; returning stub provider info"],
                meta=_meta_dict("sc_get_provider_info", t0),
            ))

        out = (raw.get("result") or raw.get("outputs") or {})
        if not isinstance(out, dict):
            out = {}

        provider  = out.get("provider", "None")
        available = bool(out.get("available", False))
        outputs = {
            "provider":    provider,
            "available":   available,
            "workspace":   out.get("workspace", ""),
            "server":      out.get("server", ""),
            "user":        out.get("user", ""),
        }
        if "status_text" in out:
            outputs["status_text"] = out["status_text"]
        if "error" in out:
            outputs["error"] = out["error"]

        return json.dumps(_make_result(
            success=True, stage="sc_get_provider_info",
            message=f"SC provider: {provider} (available={available})",
            outputs=outputs,
            meta=_meta_dict("sc_get_provider_info", t0),
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # sc_get_status
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def sc_get_status(
        ctx: Context,
        path: str,
    ) -> str:
        """Get the source control status of a single asset or file path.

        Never raises when the provider is unavailable; returns state='unknown'
        or state='not_in_depot' as appropriate.

        Args:
            path: Package path ('/Game/Blueprints/BP_HealthSystem') or
                  absolute filesystem path to the .uasset file.

        Returns:
            JSON StructuredResult with outputs:
              path      — the queried path
              state     — 'checked_out' | 'added' | 'unchanged' | 'deleted' |
                          'conflicted' | 'not_in_depot' | 'ignored' | 'unknown'
              revision  — revision string (e.g. '#12') or '' if unavailable
        """
        t0 = time.monotonic()

        code = textwrap.dedent(f"""
            import unreal
            _result = {{'path': {path!r}, 'state': 'unknown', 'revision': ''}}
            try:
                sc = unreal.SourceControlHelpers
                if not sc.is_available():
                    _result['state'] = 'unknown'
                else:
                    file_state = sc.query_file_state({path!r})
                    if file_state:
                        _result['state']    = str(file_state.get_state()) if hasattr(file_state, 'get_state') else 'unknown'
                        _result['revision'] = str(file_state.get_revision()) if hasattr(file_state, 'get_revision') else ''
                    else:
                        _result['state'] = 'not_in_depot'
            except AttributeError:
                _result['state'] = 'unknown'
            except Exception as _e:
                _result['state'] = 'unknown'
                _result['error'] = str(_e)
        """)

        raw = _exec_python(code)
        if not _ok(raw):
            outputs = {"path": path, "state": "unknown", "revision": ""}
            return json.dumps(_make_result(
                success=True, stage="sc_get_status",
                message=f"SC status for '{path}': unknown (UE5 not reachable)",
                outputs=outputs,
                warnings=["UE5 not reachable; returning unknown state"],
                meta=_meta_dict("sc_get_status", t0),
            ))

        out = (raw.get("result") or raw.get("outputs") or {})
        if not isinstance(out, dict):
            out = {"path": path, "state": "unknown", "revision": ""}

        raw_state  = out.get("state", "unknown")
        norm_state = _normalise_state(raw_state)
        outputs = {
            "path":     out.get("path", path),
            "state":    norm_state,
            "revision": out.get("revision", ""),
        }
        if "error" in out:
            outputs["error"] = out["error"]

        return json.dumps(_make_result(
            success=True, stage="sc_get_status",
            message=f"SC status for '{path}': {norm_state}",
            outputs=outputs,
            meta=_meta_dict("sc_get_status", t0),
        ))

    # ──────────────────────────────────────────────────────────────────────────
    # sc_get_changelist
    # ──────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    async def sc_get_changelist(
        ctx: Context,
        changelist: str = "default",
    ) -> str:
        """Get files in a source control changelist.

        For providers without explicit changelists (Git, SVN),
        returns all locally modified files.

        When no provider is configured, returns an empty files list
        (success=True, available=False).

        Args:
            changelist: Changelist name/number. 'default' = default changelist.

        Returns:
            JSON StructuredResult with outputs:
              changelist  — the queried changelist name
              description — changelist description (empty string if unavailable)
              available   — bool — False when no SC provider
              files       — [{path, state}]
        """
        t0 = time.monotonic()

        code = textwrap.dedent(f"""
            import unreal
            _result = {{'changelist': {changelist!r}, 'description': '', 'available': False, 'files': []}}
            try:
                sc = unreal.SourceControlHelpers
                if not sc.is_available():
                    _result['available'] = False
                else:
                    _result['available'] = True
                    # Try to get pending changelists
                    try:
                        cls_list = sc.get_provider().get_state('/Game/', unreal.SourceControlStateType.DEFAULT, True)
                        for f in (cls_list or []):
                            _result['files'].append({{
                                'path':  str(f.get_filename()) if hasattr(f, 'get_filename') else str(f),
                                'state': str(f.get_state()) if hasattr(f, 'get_state') else 'unknown',
                            }})
                    except Exception as _e2:
                        _result['error'] = str(_e2)
            except AttributeError:
                _result['available'] = False
            except Exception as _e:
                _result['available'] = False
                _result['error'] = str(_e)
        """)

        raw = _exec_python(code)
        if not _ok(raw):
            outputs = {
                "changelist":  changelist,
                "description": "",
                "available":   False,
                "files":       [],
            }
            return json.dumps(_make_result(
                success=True, stage="sc_get_changelist",
                message=f"SC changelist '{changelist}': unavailable (UE5 not reachable)",
                outputs=outputs,
                warnings=["UE5 not reachable; returning empty changelist"],
                meta=_meta_dict("sc_get_changelist", t0),
            ))

        out = (raw.get("result") or raw.get("outputs") or {})
        if not isinstance(out, dict):
            out = {}

        outputs = {
            "changelist":  out.get("changelist", changelist),
            "description": out.get("description", ""),
            "available":   bool(out.get("available", False)),
            "files":       out.get("files", []),
        }
        if "error" in out:
            outputs["error"] = out["error"]

        file_count = len(outputs["files"])
        return json.dumps(_make_result(
            success=True, stage="sc_get_changelist",
            message=(
                f"Changelist '{changelist}': {file_count} file(s)"
                if outputs["available"] else
                f"Changelist '{changelist}': no SC provider configured"
            ),
            outputs=outputs,
            meta=_meta_dict("sc_get_changelist", t0),
        ))

    logger.info(
        "Source Control tools registered: "
        "sc_get_provider_info, sc_get_status, sc_get_changelist"
    )
