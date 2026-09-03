"""Pinned Ghost Studio -> Unreal handoff for the Enclave Ebon Hawk candidate."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from tools.enclave_material_pilot_tools import (
    _operation_from_context,
    _operation_receipt,
)
from tools.exec_substrate import exec_python_structured as _exec_structured
from tools.tool_registration_surface import ToolRegistrationSurface


_SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "fixed_scripts"
_SCRIPT_SPECS = {
    "dry_run": (
        "enclave_ebon_hawk_v1_dry_run.py",
        "acab61306c5718be6336c85981bad901dfc74f270c495dd5f9509d2eac1f2d6a",
    ),
    "apply": (
        "enclave_ebon_hawk_v1_apply.py",
        "dde0812c145f920ad77687ca7d37c4b33dfb1f0f67aab4c7c38be1b98ac317a4",
    ),
    "rollback": (
        "enclave_ebon_hawk_v1_rollback.py",
        "5211d6fe97746a745196eb9969c9ead7484b34db804a4610f49a91fb3e61eeee",
    ),
}


def _pinned_script(mode: str) -> str:
    filename, expected_sha256 = _SCRIPT_SPECS[mode]
    path = _SCRIPT_ROOT / filename
    if path.parent != _SCRIPT_ROOT:
        raise RuntimeError("The fixed Ebon Hawk script escaped its pinned root")
    metadata = path.lstat()
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        path.is_symlink()
        or not path.is_file()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse_attribute)
    ):
        raise RuntimeError("The fixed Ebon Hawk script identity is unsafe")
    code = path.read_bytes()
    if hashlib.sha256(code).hexdigest() != expected_sha256:
        raise RuntimeError("The fixed Ebon Hawk script digest mismatched")
    return code.decode("utf-8")


def _deferred_apply_code(code: str) -> str:
    """Run the first FBX import after the synchronous bridge callback unwinds."""
    return f'''\
import json as _deferred_json
import os as _deferred_os
import traceback as _deferred_traceback
import unreal as _deferred_unreal

_DEFERRED_BODY = {code!r}
_DEFERRED_RECEIPT_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_ebon_hawk_v2_receipt.json",
))
_DEFERRED_FAILURE_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_ebon_hawk_v2_deferred_failure.json",
))

if _deferred_os.path.exists(_DEFERRED_RECEIPT_PATH):
    exec(_DEFERRED_BODY)
else:
    if _deferred_os.path.exists(_DEFERRED_FAILURE_PATH):
        raise RuntimeError("The prior deferred Ebon Hawk handoff failed; inspect its fixed evidence")
    _deferred_state = {{}}

    def _run_deferred_ebon_hawk(_delta_seconds):
        _handle = _deferred_state.pop("handle", None)
        if _handle is not None:
            _deferred_unreal.unregister_slate_post_tick_callback(_handle)
        _namespace = {{"_result": {{}}, "_warnings": [], "_errors": [], "_log_tail": []}}
        try:
            exec(_DEFERRED_BODY, _namespace, _namespace)
            _deferred_unreal.log("MCPStudio Ebon Hawk deferred handoff completed")
        except Exception as _deferred_exc:
            _deferred_os.makedirs(_deferred_os.path.dirname(_DEFERRED_FAILURE_PATH), exist_ok=True)
            _failure = {{
                "schema": "unreal_mcp_ghost.enclave-ebon-hawk-deferred-failure/v2",
                "error": str(_deferred_exc),
                "traceback": _deferred_traceback.format_exc().splitlines()[-30:],
                "receipt_path": _DEFERRED_RECEIPT_PATH,
            }}
            with open(_DEFERRED_FAILURE_PATH, "x", encoding="utf-8") as _stream:
                _deferred_json.dump(_failure, _stream, indent=2, sort_keys=True)
                _stream.write("\\n")
            _deferred_unreal.log_error("MCPStudio Ebon Hawk deferred handoff failed: " + str(_deferred_exc))

    _deferred_state["handle"] = _deferred_unreal.register_slate_post_tick_callback(
        _run_deferred_ebon_hawk
    )
    _result.update({{
        "queued_deferred_apply": True,
        "receipt_path": _DEFERRED_RECEIPT_PATH,
        "failure_path": _DEFERRED_FAILURE_PATH,
    }})
'''


def register_enclave_ebon_hawk_handoff_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def enclave_ebon_hawk_handoff(
        ctx: Context,
        mode: Literal["dry_run", "apply", "rollback"] = "dry_run",
        confirm_operation: bool = False,
    ) -> dict[str, Any]:
        """Validate, apply, or roll back the exact K2 Ebon Hawk handoff.

        The caller cannot choose a path, project, actor, mesh, texture, or
        destination. The operation is pinned to the hashed Ghost Studio
        ``K2:v_ehawk`` FBX package in the Enclave working copy and preserves the
        original mesh asset. Apply bakes the corrected uniform scale into the
        imported content-browser mesh, uses a unit-scale actor in an exclusive
        namespace, and swaps only the stable Ebon Hawk actor; rollback restores
        its prior mesh and exact transform.
        The imported diffuse materials are explicitly staging-only until the
        separate Substance Painter PBR upgrade is qualified.
        """
        operation = _operation_from_context(ctx, mode)
        if mode in {"apply", "rollback"} and confirm_operation is not True:
            raise RuntimeError(f"confirm_operation=true is required for {mode}")
        code = _pinned_script(mode)
        if mode == "apply":
            code = _deferred_apply_code(code)
        result = _exec_structured(code, f"enclave_ebon_hawk_handoff_{mode}")
        if not isinstance(result, dict):
            raise RuntimeError("The fixed Ebon Hawk handoff returned an invalid result")
        outputs = result.get("outputs")
        if mode == "apply" and isinstance(outputs, dict) and outputs.get(
            "queued_deferred_apply"
        ) is True:
            raise RuntimeError(
                "The fixed Ebon Hawk handoff was queued on Unreal's next editor tick; "
                "MCPStudio must reconcile the fixed local receipt before replay"
            )
        return _operation_receipt(operation, mode, result)
