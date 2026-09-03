"""Pinned production operator for the Enclave landing ground refinement."""

from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from tools.exec_substrate import exec_python_structured as _exec_structured
from tools.tool_registration_surface import ToolRegistrationSurface


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "fixed_scripts" / "enclave_landing_ground_refine_v1.py"
_EXPECTED_SCRIPT_SHA256 = "82fbb3542748deab34fae3fbfda1c1e00ece2d37701ed6c35a0f0de2e0f2bd36"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_RECEIPT_RELATIVE = "MCPStudio/evidence/enclave_landing_ground_refine_v1_receipt.json"
_FAILURE_RELATIVE = "MCPStudio/evidence/enclave_landing_ground_refine_v1_deferred_failure.json"


def _pinned_script(mode: str) -> str:
    metadata = _SCRIPT_PATH.lstat()
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        _SCRIPT_PATH.is_symlink()
        or not _SCRIPT_PATH.is_file()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse)
    ):
        raise RuntimeError("The landing ground script identity is unsafe")
    body = _SCRIPT_PATH.read_bytes()
    if hashlib.sha256(body).hexdigest() != _EXPECTED_SCRIPT_SHA256:
        raise RuntimeError("The landing ground script digest mismatched")
    return f"MCPSTUDIO_MODE = {mode!r}\n" + body.decode("utf-8")


def _operation_from_context(ctx: Context, mode: str) -> dict[str, Any]:
    request_context = getattr(ctx, "request_context", None)
    meta = getattr(request_context, "meta", None)
    extra = getattr(meta, "model_extra", None) if meta is not None else None
    operation = extra.get("mcpstudio/operation") if isinstance(extra, dict) else None
    if not isinstance(operation, dict):
        raise RuntimeError("The landing ground refinement lacks its MCPStudio operation binding")
    required = {
        "operationId",
        "idempotencyKey",
        "expectedRevision",
        "intent",
        "dryRun",
        "affectedStableIds",
        "rollback",
        "invocationDigest",
    }
    if set(operation) != required:
        raise RuntimeError("The landing ground operation binding has an invalid shape")
    if not _SHA256.fullmatch(str(operation.get("invocationDigest", ""))):
        raise RuntimeError("The landing ground operation digest is invalid")
    for key, limit in (("operationId", 160), ("idempotencyKey", 256), ("expectedRevision", 256)):
        value = operation.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise RuntimeError("The landing ground operation has invalid " + key)
    stable_ids = operation.get("affectedStableIds")
    if (
        not isinstance(stable_ids, list)
        or not 1 <= len(stable_ids) <= 256
        or len(stable_ids) != len(set(stable_ids))
        or any(not isinstance(value, str) or not value.strip() or len(value) > 512 for value in stable_ids)
    ):
        raise RuntimeError("The landing ground operation has invalid stable IDs")
    rollback = operation.get("rollback")
    if not isinstance(rollback, dict) or rollback.get("strategy") not in {
        "undo",
        "restore-copy",
        "child-created-restore-copy",
    }:
        raise RuntimeError("The landing ground rollback contract is invalid")
    preview = mode == "dry_run"
    valid_intent = (
        operation.get("intent") == "preview" and operation.get("dryRun") is True
        if preview
        else operation.get("intent") == "apply" and operation.get("dryRun") is False
    )
    if not valid_intent:
        raise RuntimeError("The landing ground mode does not match its operation intent")
    return operation


def _deferred_apply_code(code: str) -> str:
    return f'''
import json as _ground_json
import os as _ground_os
import traceback as _ground_traceback
import unreal as _ground_unreal

_GROUND_BODY = {code!r}
_GROUND_RECEIPT = _ground_os.path.realpath(_ground_os.path.join(
    _ground_unreal.Paths.project_saved_dir(), {_RECEIPT_RELATIVE!r}
))
_GROUND_FAILURE = _ground_os.path.realpath(_ground_os.path.join(
    _ground_unreal.Paths.project_saved_dir(), {_FAILURE_RELATIVE!r}
))
if _ground_os.path.exists(_GROUND_RECEIPT):
    exec(_GROUND_BODY)
else:
    if _ground_os.path.exists(_GROUND_FAILURE):
        raise RuntimeError("The prior deferred landing ground refinement failed; inspect fixed evidence")
    _ground_state = {{}}
    def _run_landing_ground_refine(_delta_seconds):
        _handle = _ground_state.pop("handle", None)
        if _handle is not None:
            _ground_unreal.unregister_slate_post_tick_callback(_handle)
        _namespace = {{"_result": {{}}, "_warnings": [], "_errors": [], "_log_tail": []}}
        try:
            exec(_GROUND_BODY, _namespace, _namespace)
            _ground_unreal.log("MCPStudio landing ground refinement completed")
        except Exception as _exc:
            _ground_os.makedirs(_ground_os.path.dirname(_GROUND_FAILURE), exist_ok=True)
            _failure = {{
                "schema": "unreal_mcp_ghost.enclave-landing-ground-refine-deferred-failure/v1",
                "error": str(_exc),
                "traceback": _ground_traceback.format_exc().splitlines()[-40:],
                "receipt_path": _GROUND_RECEIPT,
            }}
            with open(_GROUND_FAILURE, "x", encoding="utf-8") as _stream:
                _ground_json.dump(_failure, _stream, indent=2, sort_keys=True)
                _stream.write("\\n")
            _ground_unreal.log_error("MCPStudio landing ground refinement failed: " + str(_exc))
    _ground_state["handle"] = _ground_unreal.register_slate_post_tick_callback(
        _run_landing_ground_refine
    )
    _result.update({{
        "queued_deferred_apply": True,
        "receipt_path": _GROUND_RECEIPT,
        "failure_path": _GROUND_FAILURE,
    }})
'''


def _operation_receipt(operation: dict[str, Any], mode: str, result: dict[str, Any]) -> dict[str, Any]:
    if result.get("success") is not True:
        errors = result.get("errors")
        detail = errors[0] if isinstance(errors, list) and errors else "unknown failure"
        raise RuntimeError("The fixed landing ground refinement failed: " + str(detail))
    outputs = result.get("outputs")
    outputs = outputs if isinstance(outputs, dict) else {}
    if mode == "dry_run":
        outcome = "previewed"
        after_revision = operation["expectedRevision"]
    else:
        outcome = "replayed" if outputs.get("idempotent_replay") is True else "applied"
        after_revision = "unreal-enclave-landing-ground-refine-v1:" + hashlib.sha256(
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
            "data": {"landingGroundRefine": result},
        }
    }


def register_enclave_landing_ground_refine_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def enclave_landing_ground_refine(
        ctx: Context,
        mode: Literal["dry_run", "apply", "rollback"] = "dry_run",
        confirm_operation: bool = False,
    ) -> dict[str, Any]:
        """Add or roll back the exact unit-scale landing pad and grass support pass.

        The operation accepts no caller-selected asset, transform, actor, file,
        material, or map. It is pinned to the reviewed Enclave main level,
        existing landing receipts, exact material families, and an exclusive
        Content Browser namespace.
        """
        operation = _operation_from_context(ctx, mode)
        if mode in {"apply", "rollback"} and confirm_operation is not True:
            raise RuntimeError("confirm_operation=true is required for " + mode)
        code = _pinned_script(mode)
        if mode == "apply":
            code = _deferred_apply_code(code)
        result = _exec_structured(code, "enclave_landing_ground_refine_" + mode)
        if not isinstance(result, dict):
            raise RuntimeError("The fixed landing ground refinement returned an invalid result")
        outputs = result.get("outputs")
        if mode == "apply" and isinstance(outputs, dict) and outputs.get("queued_deferred_apply") is True:
            raise RuntimeError(
                "The landing ground refinement was queued on Unreal's next editor tick; "
                "MCPStudio must reconcile the fixed local receipt before replay"
            )
        return _operation_receipt(operation, mode, result)
