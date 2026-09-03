"""Pinned physical-scale tiling repair for the Enclave landing grass material."""

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from tools.enclave_material_pilot_tools import _operation_from_context
from tools.exec_substrate import exec_python_structured as _exec_structured
from tools.tool_registration_surface import ToolRegistrationSurface


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "fixed_scripts" / "enclave_landing_ground_material_repair_v1.py"
_SCRIPT_SHA256 = "d66664f009a8f09394ddeeef7acf31ee373b4c5c43e5255e675c6378766db55b"
_RECEIPT_RELATIVE = "MCPStudio/evidence/enclave_landing_ground_material_repair_v1_receipt.json"
_FAILURE_RELATIVE = "MCPStudio/evidence/enclave_landing_ground_material_repair_v1_deferred_failure.json"


def _pinned_script(mode: str) -> str:
    metadata = _SCRIPT_PATH.lstat()
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if _SCRIPT_PATH.is_symlink() or not _SCRIPT_PATH.is_file() or bool(
        getattr(metadata, "st_file_attributes", 0) & reparse
    ):
        raise RuntimeError("The landing ground-material script identity is unsafe")
    body = _SCRIPT_PATH.read_bytes()
    if hashlib.sha256(body).hexdigest() != _SCRIPT_SHA256:
        raise RuntimeError("The landing ground-material script digest mismatched")
    return f"MCPSTUDIO_MODE = {mode!r}\n" + body.decode("utf-8")


def _deferred_apply_code(code: str) -> str:
    return f'''
import json as _ground_material_json
import os as _ground_material_os
import traceback as _ground_material_traceback
import unreal as _ground_material_unreal
_GROUND_MATERIAL_BODY = {code!r}
_GROUND_MATERIAL_RECEIPT = _ground_material_os.path.realpath(_ground_material_os.path.join(
    _ground_material_unreal.Paths.project_saved_dir(), {_RECEIPT_RELATIVE!r}
))
_GROUND_MATERIAL_FAILURE = _ground_material_os.path.realpath(_ground_material_os.path.join(
    _ground_material_unreal.Paths.project_saved_dir(), {_FAILURE_RELATIVE!r}
))
if _ground_material_os.path.exists(_GROUND_MATERIAL_RECEIPT):
    exec(_GROUND_MATERIAL_BODY)
else:
    if _ground_material_os.path.exists(_GROUND_MATERIAL_FAILURE):
        raise RuntimeError("The prior deferred ground-material repair failed; inspect fixed evidence")
    _ground_material_state = {{}}
    def _run_ground_material_repair(_delta_seconds):
        _handle = _ground_material_state.pop("handle", None)
        if _handle is not None:
            _ground_material_unreal.unregister_slate_post_tick_callback(_handle)
        _namespace = {{"_result": {{}}, "_warnings": [], "_errors": [], "_log_tail": []}}
        try:
            exec(_GROUND_MATERIAL_BODY, _namespace, _namespace)
            _ground_material_unreal.log("MCPStudio landing ground-material repair completed")
        except Exception as _exc:
            _ground_material_os.makedirs(_ground_material_os.path.dirname(_GROUND_MATERIAL_FAILURE), exist_ok=True)
            with open(_GROUND_MATERIAL_FAILURE, "x", encoding="utf-8") as _stream:
                _ground_material_json.dump({{
                    "schema": "unreal_mcp_ghost.enclave-landing-ground-material-repair-failure/v1",
                    "error": str(_exc),
                    "traceback": _ground_material_traceback.format_exc().splitlines()[-40:],
                }}, _stream, indent=2, sort_keys=True)
                _stream.write("\\n")
            _ground_material_unreal.log_error("MCPStudio landing ground-material repair failed: " + str(_exc))
    _ground_material_state["handle"] = _ground_material_unreal.register_slate_post_tick_callback(
        _run_ground_material_repair
    )
    _result.update({{
        "queued_deferred_apply": True,
        "receipt_path": _GROUND_MATERIAL_RECEIPT,
        "failure_path": _GROUND_MATERIAL_FAILURE,
    }})
'''


def _operation_receipt(operation: dict[str, Any], mode: str, result: dict[str, Any]) -> dict[str, Any]:
    if result.get("success") is not True:
        errors = result.get("errors")
        detail = errors[0] if isinstance(errors, list) and errors else "unknown failure"
        raise RuntimeError("The fixed landing ground-material repair failed: " + str(detail))
    outputs = result.get("outputs")
    outputs = outputs if isinstance(outputs, dict) else {}
    if mode == "dry_run":
        outcome = "previewed"
        after_revision = operation["expectedRevision"]
    else:
        outcome = "replayed" if outputs.get("idempotent_replay") is True else "applied"
        after_revision = "unreal-enclave-landing-ground-material-repair-v1:" + hashlib.sha256(
            json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    return {"operationReceipt": {
        "receiptVersion": "1.0",
        "operationId": operation["operationId"],
        "idempotencyKey": operation["idempotencyKey"],
        "intent": operation["intent"],
        "dryRun": operation["dryRun"],
        "outcome": outcome,
        "invocationDigest": operation["invocationDigest"],
        "beforeRevision": operation["expectedRevision"],
        "afterRevision": after_revision,
        "affectedStableIds": operation["affectedStableIds"],
        "rollback": operation["rollback"],
        "data": {"landingGroundMaterialRepair": result},
    }}


def register_enclave_landing_ground_material_repair_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def enclave_landing_ground_material_repair(
        ctx: Context,
        mode: Literal["dry_run", "apply", "rollback"] = "dry_run",
        confirm_operation: bool = False,
    ) -> dict[str, Any]:
        """Repair the exact landing grass material from aliasing to physical-scale tiling.

        The caller cannot select a material, graph node, texture, map, scale, or
        file. The fixed operation changes only the exact audited grass material
        TextureCoordinate node and preserves a durable before/after receipt.
        """
        operation = _operation_from_context(ctx, mode)
        if mode in {"apply", "rollback"} and confirm_operation is not True:
            raise RuntimeError("confirm_operation=true is required for " + mode)
        code = _pinned_script(mode)
        if mode == "apply":
            code = _deferred_apply_code(code)
        result = _exec_structured(code, "enclave_landing_ground_material_repair_" + mode)
        if not isinstance(result, dict):
            raise RuntimeError("The fixed landing ground-material repair returned an invalid result")
        outputs = result.get("outputs")
        if mode == "apply" and isinstance(outputs, dict) and outputs.get("queued_deferred_apply") is True:
            raise RuntimeError(
                "The landing ground-material repair was queued on Unreal's next editor tick; "
                "MCPStudio must reconcile the fixed local receipt before replay"
            )
        return _operation_receipt(operation, mode, result)
