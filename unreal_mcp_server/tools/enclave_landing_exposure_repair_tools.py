"""Pinned exposure-state repair for the Enclave landing area."""

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


_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixed_scripts"
    / "enclave_landing_exposure_repair_v1.py"
)
_SCRIPT_SHA256 = "770ea3d742bb648779eb371ef4f108ff940625c51e2a0738d2a1a7169b2a326e"
_RECEIPT_RELATIVE = "MCPStudio/evidence/enclave_landing_exposure_repair_v1_receipt.json"
_FAILURE_RELATIVE = "MCPStudio/evidence/enclave_landing_exposure_repair_v1_deferred_failure.json"


def _pinned_script(mode: str) -> str:
    metadata = _SCRIPT_PATH.lstat()
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        _SCRIPT_PATH.is_symlink()
        or not _SCRIPT_PATH.is_file()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse)
    ):
        raise RuntimeError("The landing exposure-repair script identity is unsafe")
    body = _SCRIPT_PATH.read_bytes()
    if hashlib.sha256(body).hexdigest() != _SCRIPT_SHA256:
        raise RuntimeError("The landing exposure-repair script digest mismatched")
    return f"MCPSTUDIO_MODE = {mode!r}\n" + body.decode("utf-8")


def _deferred_apply_code(code: str) -> str:
    return f'''
import json as _exposure_json
import os as _exposure_os
import traceback as _exposure_traceback
import unreal as _exposure_unreal

_EXPOSURE_BODY = {code!r}
_EXPOSURE_RECEIPT = _exposure_os.path.realpath(_exposure_os.path.join(
    _exposure_unreal.Paths.project_saved_dir(), {_RECEIPT_RELATIVE!r}
))
_EXPOSURE_FAILURE = _exposure_os.path.realpath(_exposure_os.path.join(
    _exposure_unreal.Paths.project_saved_dir(), {_FAILURE_RELATIVE!r}
))
if _exposure_os.path.exists(_EXPOSURE_RECEIPT):
    exec(_EXPOSURE_BODY)
else:
    if _exposure_os.path.exists(_EXPOSURE_FAILURE):
        raise RuntimeError("The prior deferred landing exposure repair failed; inspect fixed evidence")
    _exposure_state = {{}}
    def _run_landing_exposure_repair(_delta_seconds):
        _handle = _exposure_state.pop("handle", None)
        if _handle is not None:
            _exposure_unreal.unregister_slate_post_tick_callback(_handle)
        _namespace = {{"_result": {{}}, "_warnings": [], "_errors": [], "_log_tail": []}}
        try:
            exec(_EXPOSURE_BODY, _namespace, _namespace)
            _exposure_unreal.log("MCPStudio landing exposure repair completed")
        except Exception as _exc:
            _exposure_os.makedirs(_exposure_os.path.dirname(_EXPOSURE_FAILURE), exist_ok=True)
            with open(_EXPOSURE_FAILURE, "x", encoding="utf-8") as _stream:
                _exposure_json.dump({{
                    "schema": "unreal_mcp_ghost.enclave-landing-exposure-repair-failure/v1",
                    "error": str(_exc),
                    "traceback": _exposure_traceback.format_exc().splitlines()[-40:],
                }}, _stream, indent=2, sort_keys=True)
                _stream.write("\\n")
            _exposure_unreal.log_error("MCPStudio landing exposure repair failed: " + str(_exc))
    _exposure_state["handle"] = _exposure_unreal.register_slate_post_tick_callback(
        _run_landing_exposure_repair
    )
    _result.update({{
        "queued_deferred_apply": True,
        "receipt_path": _EXPOSURE_RECEIPT,
        "failure_path": _EXPOSURE_FAILURE,
    }})
'''


def _operation_receipt(
    operation: dict[str, Any], mode: str, result: dict[str, Any]
) -> dict[str, Any]:
    if result.get("success") is not True:
        errors = result.get("errors")
        detail = errors[0] if isinstance(errors, list) and errors else "unknown failure"
        raise RuntimeError("The fixed landing exposure repair failed: " + str(detail))
    outputs = result.get("outputs")
    outputs = outputs if isinstance(outputs, dict) else {}
    if mode == "dry_run":
        outcome = "previewed"
        after_revision = operation["expectedRevision"]
    else:
        outcome = "replayed" if outputs.get("idempotent_replay") is True else "applied"
        after_revision = "unreal-enclave-landing-exposure-repair-v1:" + hashlib.sha256(
            json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    return {
        "operationReceipt": {
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
            "data": {"landingExposureRepair": result},
        }
    }


def register_enclave_landing_exposure_repair_tools(
    mcp: ToolRegistrationSurface,
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def enclave_landing_exposure_repair(
        ctx: Context,
        mode: Literal["dry_run", "apply", "rollback"] = "dry_run",
        confirm_operation: bool = False,
    ) -> dict[str, Any]:
        """Repair or roll back the exact audited landing exposure overrides.

        The operator accepts no map, actor, property, or exposure value from
        the caller. It is pinned to the exact Enclave map, audited unbound
        post-process actor, and prerequisite visual-review receipt. The only
        apply change disables two zero-valued exposure-range overrides.
        """
        operation = _operation_from_context(ctx, mode)
        if mode in {"apply", "rollback"} and confirm_operation is not True:
            raise RuntimeError("confirm_operation=true is required for " + mode)
        code = _pinned_script(mode)
        if mode == "apply":
            code = _deferred_apply_code(code)
        result = _exec_structured(code, "enclave_landing_exposure_repair_" + mode)
        if not isinstance(result, dict):
            raise RuntimeError("The fixed landing exposure repair returned an invalid result")
        outputs = result.get("outputs")
        if (
            mode == "apply"
            and isinstance(outputs, dict)
            and outputs.get("queued_deferred_apply") is True
        ):
            raise RuntimeError(
                "The landing exposure repair was queued on Unreal's next editor tick; "
                "MCPStudio must reconcile the fixed local receipt before replay"
            )
        return _operation_receipt(operation, mode, result)
