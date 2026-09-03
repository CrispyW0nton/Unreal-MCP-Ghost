"""Pinned scale normalization for the Enclave modular staging kit."""

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


_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixed_scripts"
    / "enclave_staged_prop_scale_bake_v1.py"
)
_SCRIPT_SHA256 = "07519dfad9fc17f1530d564d4b15b41b86bb248997d581ca7e05557a8155d8b5"


def _pinned_script(mode: str, batch: int) -> str:
    expected_root = Path(__file__).resolve().parents[1] / "fixed_scripts"
    if _SCRIPT_PATH.parent != expected_root:
        raise RuntimeError("The fixed staged prop scale-bake script escaped its pinned root")
    metadata = _SCRIPT_PATH.lstat()
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        _SCRIPT_PATH.is_symlink()
        or not _SCRIPT_PATH.is_file()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse_attribute)
    ):
        raise RuntimeError("The fixed staged prop scale-bake script identity is unsafe")
    code = _SCRIPT_PATH.read_bytes()
    if hashlib.sha256(code).hexdigest() != _SCRIPT_SHA256:
        raise RuntimeError("The fixed staged prop scale-bake script digest mismatched")
    return (
        f"_MCPSTUDIO_FIXED_MODE = {mode!r}\n"
        f"_MCPSTUDIO_FIXED_BATCH = {batch!r}\n"
        + code.decode("utf-8")
    )


def _deferred_apply_code(code: str, batch: int) -> str:
    return f'''\
import json as _deferred_json
import os as _deferred_os
import traceback as _deferred_traceback
import unreal as _deferred_unreal

_DEFERRED_BODY = {code!r}
_DEFERRED_BATCH = {batch!r}
_DEFERRED_RECEIPT_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_staged_prop_scale_bake_v1_batch_{batch}_receipt.json",
))
_DEFERRED_FAILURE_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_staged_prop_scale_bake_v1_batch_{batch}_failure.json",
))

if _deferred_os.path.exists(_DEFERRED_RECEIPT_PATH):
    exec(_DEFERRED_BODY)
else:
    if _deferred_os.path.exists(_DEFERRED_FAILURE_PATH):
        raise RuntimeError("The prior deferred staged prop scale bake failed; inspect its fixed evidence")
    _deferred_state = {{}}

    def _run_deferred_staged_prop_scale_bake(_delta_seconds):
        _handle = _deferred_state.pop("handle", None)
        if _handle is not None:
            _deferred_unreal.unregister_slate_post_tick_callback(_handle)
        _namespace = {{"_result": {{}}, "_warnings": [], "_errors": [], "_log_tail": []}}
        try:
            exec(_DEFERRED_BODY, _namespace, _namespace)
            _deferred_unreal.log(
                "MCPStudio staged prop scale-bake batch {{}} completed".format(_DEFERRED_BATCH)
            )
        except Exception as _deferred_exc:
            _deferred_os.makedirs(_deferred_os.path.dirname(_DEFERRED_FAILURE_PATH), exist_ok=True)
            _failure = {{
                "schema": "unreal_mcp_ghost.enclave-staged-prop-scale-bake-deferred-failure/v1",
                "batch": _DEFERRED_BATCH,
                "error": str(_deferred_exc),
                "traceback": _deferred_traceback.format_exc().splitlines()[-30:],
                "receipt_path": _DEFERRED_RECEIPT_PATH,
            }}
            with open(_DEFERRED_FAILURE_PATH, "x", encoding="utf-8") as _stream:
                _deferred_json.dump(_failure, _stream, indent=2, sort_keys=True)
                _stream.write("\\n")
            _deferred_unreal.log_error(
                "MCPStudio staged prop scale bake failed: " + str(_deferred_exc)
            )

    _deferred_state["handle"] = _deferred_unreal.register_slate_post_tick_callback(
        _run_deferred_staged_prop_scale_bake
    )
    _result.update({{
        "queued_deferred_apply": True,
        "batch": _DEFERRED_BATCH,
        "receipt_path": _DEFERRED_RECEIPT_PATH,
        "failure_path": _DEFERRED_FAILURE_PATH,
    }})
'''


def register_enclave_staged_prop_scale_bake_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def enclave_staged_prop_scale_bake(
        ctx: Context,
        mode: Literal["dry_run", "apply", "rollback"] = "dry_run",
        batch: int = 0,
        confirm_operation: bool = False,
    ) -> dict[str, Any]:
        """Bake the fixed Enclave modular-kit scale variants in eight stable batches.

        The caller cannot supply paths, actor identities, meshes, scales, materials,
        destinations, or arbitrary code. The operator considers only exact reviewed
        source meshes under the Enclave ModularKit, creates one merged Content
        Browser mesh for each source/scale/material variant, preserves placed bounds,
        resets affected actors to unit scale, and records a per-batch rollback receipt.
        Generic Cube blockouts and unrelated level actors are out of scope.
        """
        if not isinstance(batch, int) or isinstance(batch, bool) or batch < 0 or batch > 7:
            raise ValueError("batch must be between 0 and 7")
        operation = _operation_from_context(ctx, mode)
        if mode in {"apply", "rollback"} and confirm_operation is not True:
            raise RuntimeError(f"confirm_operation=true is required for {mode}")
        code = _pinned_script(mode, batch)
        if mode == "apply":
            code = _deferred_apply_code(code, batch)
        result = _exec_structured(
            code,
            f"enclave_staged_prop_scale_bake_{mode}_batch_{batch}",
        )
        if not isinstance(result, dict):
            raise RuntimeError("The fixed staged prop scale bake returned an invalid result")
        outputs = result.get("outputs")
        if (
            mode == "apply"
            and isinstance(outputs, dict)
            and outputs.get("queued_deferred_apply") is True
        ):
            raise RuntimeError(
                "The fixed staged prop scale bake was queued on Unreal's next editor tick; "
                "MCPStudio must reconcile the fixed local receipt before replay"
            )
        return _operation_receipt(operation, mode, result)
