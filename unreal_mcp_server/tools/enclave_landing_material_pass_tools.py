"""Pinned production operator for the Enclave landing material pass."""

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


_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixed_scripts"
    / "enclave_landing_material_pass_v1.py"
)
_EXPECTED_SCRIPT_SHA256 = "5f3d5580595f9c8b051bfc0e6e2550ffaa9ae030cec8de2d661f2dbb3fd46846"
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_RECEIPT_RELATIVE = "MCPStudio/evidence/enclave_landing_material_pass_v1_receipt.json"
_FAILURE_RELATIVE = "MCPStudio/evidence/enclave_landing_material_pass_v1_deferred_failure.json"


def _pinned_script(mode: str) -> str:
    root = _SCRIPT_PATH.parent
    if _SCRIPT_PATH.parent != root:
        raise RuntimeError("The landing material script escaped its fixed root")
    metadata = _SCRIPT_PATH.lstat()
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        _SCRIPT_PATH.is_symlink()
        or not _SCRIPT_PATH.is_file()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse)
    ):
        raise RuntimeError("The landing material script identity is unsafe")
    body = _SCRIPT_PATH.read_bytes()
    if hashlib.sha256(body).hexdigest() != _EXPECTED_SCRIPT_SHA256:
        raise RuntimeError("The landing material script digest mismatched")
    return f"MCPSTUDIO_MODE = {mode!r}\n" + body.decode("utf-8")


def _operation_from_context(ctx: Context, mode: str) -> dict[str, Any]:
    request_context = getattr(ctx, "request_context", None)
    meta = getattr(request_context, "meta", None)
    extra = getattr(meta, "model_extra", None) if meta is not None else None
    operation = extra.get("mcpstudio/operation") if isinstance(extra, dict) else None
    if not isinstance(operation, dict):
        raise RuntimeError("The landing material pass lacks its MCPStudio operation binding")
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
        raise RuntimeError("The landing material operation binding has an invalid shape")
    if not _SHA256.fullmatch(str(operation.get("invocationDigest", ""))):
        raise RuntimeError("The landing material operation digest is invalid")
    for key, limit in (("operationId", 160), ("idempotencyKey", 256), ("expectedRevision", 256)):
        value = operation.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise RuntimeError("The landing material operation has invalid " + key)
    stable_ids = operation.get("affectedStableIds")
    if (
        not isinstance(stable_ids, list)
        or not 1 <= len(stable_ids) <= 256
        or len(stable_ids) != len(set(stable_ids))
        or any(not isinstance(value, str) or not value.strip() or len(value) > 512 for value in stable_ids)
    ):
        raise RuntimeError("The landing material operation has invalid stable IDs")
    rollback = operation.get("rollback")
    if not isinstance(rollback, dict) or rollback.get("strategy") not in {
        "undo",
        "restore-copy",
        "child-created-restore-copy",
    }:
        raise RuntimeError("The landing material rollback contract is invalid")
    preview = mode == "dry_run"
    if preview:
        valid_intent = operation.get("intent") == "preview" and operation.get("dryRun") is True
    else:
        valid_intent = operation.get("intent") == "apply" and operation.get("dryRun") is False
    if not valid_intent:
        raise RuntimeError("The landing material mode does not match its operation intent")
    return operation


def _deferred_apply_code(code: str) -> str:
    return f'''
import json as _landing_json
import os as _landing_os
import traceback as _landing_traceback
import unreal as _landing_unreal

_LANDING_BODY = {code!r}
_LANDING_RECEIPT = _landing_os.path.realpath(_landing_os.path.join(
    _landing_unreal.Paths.project_saved_dir(), {_RECEIPT_RELATIVE!r}
))
_LANDING_FAILURE = _landing_os.path.realpath(_landing_os.path.join(
    _landing_unreal.Paths.project_saved_dir(), {_FAILURE_RELATIVE!r}
))
if _landing_os.path.exists(_LANDING_RECEIPT):
    exec(_LANDING_BODY)
else:
    if _landing_os.path.exists(_LANDING_FAILURE):
        raise RuntimeError("The prior deferred landing material pass failed; inspect fixed evidence")
    _landing_state = {{}}
    def _run_landing_material_pass(_delta_seconds):
        _handle = _landing_state.pop("handle", None)
        if _handle is not None:
            _landing_unreal.unregister_slate_post_tick_callback(_handle)
        _namespace = {{"_result": {{}}, "_warnings": [], "_errors": [], "_log_tail": []}}
        try:
            exec(_LANDING_BODY, _namespace, _namespace)
            _landing_unreal.log("MCPStudio landing material pass completed")
        except Exception as _exc:
            _landing_os.makedirs(_landing_os.path.dirname(_LANDING_FAILURE), exist_ok=True)
            _failure = {{
                "schema": "unreal_mcp_ghost.enclave-landing-material-pass-deferred-failure/v1",
                "error": str(_exc),
                "traceback": _landing_traceback.format_exc().splitlines()[-40:],
                "receipt_path": _LANDING_RECEIPT,
            }}
            with open(_LANDING_FAILURE, "x", encoding="utf-8") as _stream:
                _landing_json.dump(_failure, _stream, indent=2, sort_keys=True)
                _stream.write("\\n")
            _landing_unreal.log_error("MCPStudio landing material pass failed: " + str(_exc))
    _landing_state["handle"] = _landing_unreal.register_slate_post_tick_callback(
        _run_landing_material_pass
    )
    _result.update({{
        "queued_deferred_apply": True,
        "receipt_path": _LANDING_RECEIPT,
        "failure_path": _LANDING_FAILURE,
    }})
'''


def _operation_receipt(operation: dict[str, Any], mode: str, result: dict[str, Any]) -> dict[str, Any]:
    if result.get("success") is not True:
        errors = result.get("errors")
        detail = errors[0] if isinstance(errors, list) and errors else "unknown failure"
        raise RuntimeError("The fixed landing material pass failed: " + str(detail))
    outputs = result.get("outputs")
    outputs = outputs if isinstance(outputs, dict) else {}
    if mode == "dry_run":
        outcome = "previewed"
        after_revision = operation["expectedRevision"]
    else:
        outcome = "replayed" if outputs.get("idempotent_replay") is True else "applied"
        after_revision = "unreal-enclave-landing-material-pass-v1:" + hashlib.sha256(
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
            "data": {"landingMaterialPass": result},
        }
    }


def register_enclave_landing_material_pass_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def enclave_landing_material_pass(
        ctx: Context,
        mode: Literal["dry_run", "apply", "rollback"] = "dry_run",
        confirm_operation: bool = False,
    ) -> dict[str, Any]:
        """Apply or roll back the exact reviewed landing-area PBR family pass.

        No caller-selected file, script, texture, material, actor, or map is
        accepted. The operation is pinned to five scale-baked landing actors,
        eleven hash-verified local material families, and one exclusive output
        namespace. Apply and rollback require explicit confirmation.
        """
        operation = _operation_from_context(ctx, mode)
        if mode in {"apply", "rollback"} and confirm_operation is not True:
            raise RuntimeError("confirm_operation=true is required for " + mode)
        code = _pinned_script(mode)
        if mode == "apply":
            code = _deferred_apply_code(code)
        result = _exec_structured(code, "enclave_landing_material_pass_" + mode)
        if not isinstance(result, dict):
            raise RuntimeError("The fixed landing material pass returned an invalid result")
        outputs = result.get("outputs")
        if mode == "apply" and isinstance(outputs, dict) and outputs.get("queued_deferred_apply") is True:
            raise RuntimeError(
                "The landing material pass was queued on Unreal's next editor tick; "
                "MCPStudio must reconcile the fixed local receipt before replay"
            )
        return _operation_receipt(operation, mode, result)
