"""Pinned scale-normalization operator for exact Enclave landing-area props."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from tools.enclave_material_pilot_tools import _operation_from_context, _operation_receipt
from tools.exec_substrate import exec_python_structured as _exec_structured
from tools.tool_registration_surface import ToolRegistrationSurface


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "fixed_scripts" / "enclave_landing_scale_bake_v1.py"
_SCRIPT_SHA256 = "a7be7a8dd8c0047682d7e7418b33b22f06cbb3119575c208dbb043f29a606f89"


def _pinned_script(mode: str) -> str:
    expected_root = Path(__file__).resolve().parents[1] / "fixed_scripts"
    if _SCRIPT_PATH.parent != expected_root:
        raise RuntimeError("The fixed landing scale-bake script escaped its pinned root")
    metadata = _SCRIPT_PATH.lstat()
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        _SCRIPT_PATH.is_symlink()
        or not _SCRIPT_PATH.is_file()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse_attribute)
    ):
        raise RuntimeError("The fixed landing scale-bake script identity is unsafe")
    code = _SCRIPT_PATH.read_bytes()
    if hashlib.sha256(code).hexdigest() != _SCRIPT_SHA256:
        raise RuntimeError("The fixed landing scale-bake script digest mismatched")
    return f"_MCPSTUDIO_FIXED_MODE = {mode!r}\n" + code.decode("utf-8")


def _deferred_apply_code(code: str) -> str:
    return f'''\
import json as _deferred_json
import os as _deferred_os
import traceback as _deferred_traceback
import unreal as _deferred_unreal

_DEFERRED_BODY = {code!r}
_DEFERRED_RECEIPT_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_landing_scale_bake_v1_receipt.json",
))
_DEFERRED_PERSISTENCE_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_landing_scale_bake_v1_persistence.json",
))
_DEFERRED_REPAIR_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_landing_scale_bake_v2_repair_receipt.json",
))
_DEFERRED_FAILURE_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_landing_scale_bake_v2_repair_failure.json",
))

if _deferred_os.path.exists(_DEFERRED_REPAIR_PATH):
    exec(_DEFERRED_BODY)
else:
    if _deferred_os.path.exists(_DEFERRED_FAILURE_PATH):
        raise RuntimeError("The prior deferred landing scale bake failed; inspect its fixed evidence")
    _deferred_state = {{}}

    def _run_deferred_landing_scale_bake(_delta_seconds):
        _handle = _deferred_state.pop("handle", None)
        if _handle is not None:
            _deferred_unreal.unregister_slate_post_tick_callback(_handle)
        _namespace = {{"_result": {{}}, "_warnings": [], "_errors": [], "_log_tail": []}}
        try:
            exec(_DEFERRED_BODY, _namespace, _namespace)
            _deferred_unreal.log("MCPStudio landing scale-bake deferred apply completed")
        except Exception as _deferred_exc:
            _deferred_os.makedirs(_deferred_os.path.dirname(_DEFERRED_FAILURE_PATH), exist_ok=True)
            _failure = {{
                "schema": "unreal_mcp_ghost.enclave-landing-scale-bake-deferred-failure/v1",
                "error": str(_deferred_exc),
                "traceback": _deferred_traceback.format_exc().splitlines()[-30:],
                "receipt_path": _DEFERRED_RECEIPT_PATH,
            }}
            with open(_DEFERRED_FAILURE_PATH, "x", encoding="utf-8") as _stream:
                _deferred_json.dump(_failure, _stream, indent=2, sort_keys=True)
                _stream.write("\\n")
            _deferred_unreal.log_error("MCPStudio landing scale bake failed: " + str(_deferred_exc))

    _deferred_state["handle"] = _deferred_unreal.register_slate_post_tick_callback(
        _run_deferred_landing_scale_bake
    )
    _result.update({{
        "queued_deferred_apply": True,
        "receipt_path": _DEFERRED_RECEIPT_PATH,
        "failure_path": _DEFERRED_FAILURE_PATH,
    }})
'''


def register_enclave_landing_scale_bake_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def enclave_landing_scale_bake(
        ctx: Context,
        mode: Literal["dry_run", "apply", "rollback"] = "dry_run",
        confirm_operation: bool = False,
    ) -> dict[str, Any]:
        """Bake exact landing prop scales into protected mesh duplicates.

        The operation accepts no paths, actors, meshes, scales, or destinations
        from the caller. It is pinned to five reviewed landing-area actors,
        duplicates every source into an exclusive MCPStudio namespace, applies
        each staged scale through every LOD's build settings, preserves placed
        bounds, and resets actors to unit scale. Rollback restores the exact
        source meshes and staged scales.
        """
        operation = _operation_from_context(ctx, mode)
        if mode in {"apply", "rollback"} and confirm_operation is not True:
            raise RuntimeError(f"confirm_operation=true is required for {mode}")
        code = _pinned_script(mode)
        if mode == "apply":
            code = _deferred_apply_code(code)
        result = _exec_structured(code, f"enclave_landing_scale_bake_{mode}")
        if not isinstance(result, dict):
            raise RuntimeError("The fixed landing scale bake returned an invalid result")
        outputs = result.get("outputs")
        if mode == "apply" and isinstance(outputs, dict) and outputs.get("queued_deferred_apply") is True:
            raise RuntimeError(
                "The fixed landing scale bake was queued on Unreal's next editor tick; "
                "MCPStudio must reconcile the fixed local receipt before replay"
            )
        return _operation_receipt(operation, mode, result)
