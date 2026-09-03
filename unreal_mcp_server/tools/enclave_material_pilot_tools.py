"""Exact, pinned operator for the Enclave sandstone pavilion pilot."""

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


_SCRIPT_ROOT = Path(__file__).resolve().parents[1] / "fixed_scripts"
_SCRIPT_SPECS = {
    "dry_run": (
        "enclave_sandstone_pilot_v1_dry_run.py",
        "f1adf18bdf396dfbf6943259ef32fddc5936d0685094f68a47ac0d167eb6c38e",
    ),
    "apply": (
        "enclave_sandstone_pilot_v1_apply.py",
        "c2de3f5eaab738cb9e334a48167026703248ff53f46dca3715ee45dbcc638f9f",
    ),
    "rollback": (
        "enclave_sandstone_pilot_v1_rollback.py",
        "d017eea4293ac370d333cf6e9ce55ee12552c9f5d6dc3bb4f852321375c5b094",
    ),
}
_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_OPERATION_TEXT_LIMITS = {
    "operationId": 160,
    "idempotencyKey": 256,
    "expectedRevision": 256,
}
_DEFERRED_FAILURE_FILENAME = "enclave_sandstone_pilot_v1_deferred_failure.json"


def _deferred_apply_code(code: str) -> str:
    """Queue the first mutating apply outside the bridge's request callback.

    Unreal's asset import task re-enters the task graph when invoked directly
    from the bridge's synchronous ``exec_python`` game-thread callback.  A
    one-shot Slate post-tick callback gives that request callback time to
    unwind.  Once the fixed body writes its trusted receipt, exact replays run
    synchronously because their readback-only branch performs no import.
    """
    return f'''\
import json as _deferred_json
import os as _deferred_os
import traceback as _deferred_traceback
import unreal as _deferred_unreal

_DEFERRED_BODY = {code!r}
_DEFERRED_RECEIPT_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_sandstone_pilot_v1_receipt.json",
))
_DEFERRED_FAILURE_PATH = _deferred_os.path.realpath(_deferred_os.path.join(
    _deferred_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/{_DEFERRED_FAILURE_FILENAME}",
))

if _deferred_os.path.exists(_DEFERRED_RECEIPT_PATH):
    exec(_DEFERRED_BODY)
else:
    if _deferred_os.path.exists(_DEFERRED_FAILURE_PATH):
        raise RuntimeError(
            "The prior deferred Enclave pilot failed; inspect the fixed local failure evidence"
        )
    _deferred_state = {{}}

    def _run_deferred_enclave_pilot(_delta_seconds):
        _handle = _deferred_state.pop("handle", None)
        if _handle is not None:
            _deferred_unreal.unregister_slate_post_tick_callback(_handle)
        _namespace = {{
            "_result": {{}},
            "_warnings": [],
            "_errors": [],
            "_log_tail": [],
        }}
        try:
            exec(_DEFERRED_BODY, _namespace, _namespace)
            _deferred_unreal.log(
                "MCPStudio Enclave sandstone pilot deferred apply completed"
            )
        except Exception as _deferred_exc:
            _deferred_os.makedirs(
                _deferred_os.path.dirname(_DEFERRED_FAILURE_PATH), exist_ok=True
            )
            _failure = {{
                "schema": "unreal_mcp_ghost.enclave-sandstone-pilot-deferred-failure/v1",
                "error": str(_deferred_exc),
                "traceback": _deferred_traceback.format_exc().splitlines()[-30:],
                "receipt_path": _DEFERRED_RECEIPT_PATH,
            }}
            with open(_DEFERRED_FAILURE_PATH, "x", encoding="utf-8") as _stream:
                _deferred_json.dump(_failure, _stream, indent=2, sort_keys=True)
                _stream.write("\\n")
            _deferred_unreal.log_error(
                "MCPStudio Enclave sandstone pilot deferred apply failed: "
                + str(_deferred_exc)
            )

    _deferred_state["handle"] = _deferred_unreal.register_slate_post_tick_callback(
        _run_deferred_enclave_pilot
    )
    _result.update({{
        "queued_deferred_apply": True,
        "receipt_path": _DEFERRED_RECEIPT_PATH,
        "failure_path": _DEFERRED_FAILURE_PATH,
    }})
'''


def _pinned_script(mode: str) -> str:
    filename, expected_sha256 = _SCRIPT_SPECS[mode]
    # `_SCRIPT_ROOT` is derived from this already-resolved, sealed module and
    # `filename` comes only from the fixed table above. Re-resolving the leaf
    # inside a low-integrity AppContainer can require parent-directory access
    # Windows intentionally withholds, even though the sealed file itself is
    # readable. Keep the lexical fixed-root proof and verify the leaf identity
    # plus bytes directly.
    path = _SCRIPT_ROOT / filename
    if path.parent != _SCRIPT_ROOT:
        raise RuntimeError("The fixed Enclave pilot script escaped its pinned root")
    metadata = path.lstat()
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        path.is_symlink()
        or not path.is_file()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse_attribute)
    ):
        raise RuntimeError("The fixed Enclave pilot script identity is unsafe")
    code = path.read_bytes()
    if hashlib.sha256(code).hexdigest() != expected_sha256:
        raise RuntimeError("The fixed Enclave pilot script digest mismatched")
    return code.decode("utf-8")


def _operation_from_context(ctx: Context, mode: str) -> dict[str, Any]:
    """Read the Studio-owned operation binding; caller arguments cannot spoof it."""
    request_context = getattr(ctx, "request_context", None)
    meta = getattr(request_context, "meta", None)
    extra = getattr(meta, "model_extra", None) if meta is not None else None
    operation = extra.get("mcpstudio/operation") if isinstance(extra, dict) else None
    if not isinstance(operation, dict):
        raise RuntimeError("The fixed Enclave pilot lacks its MCPStudio operation binding")
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
        raise RuntimeError("The MCPStudio operation binding has an invalid shape")
    for key, limit in _OPERATION_TEXT_LIMITS.items():
        value = operation.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise RuntimeError(f"The MCPStudio operation binding has invalid {key}")
    if not isinstance(operation.get("invocationDigest"), str) or not _SHA256.fullmatch(
        operation["invocationDigest"]
    ):
        raise RuntimeError("The MCPStudio operation binding has an invalid invocation digest")
    stable_ids = operation.get("affectedStableIds")
    if (
        not isinstance(stable_ids, list)
        or not 1 <= len(stable_ids) <= 256
        or any(not isinstance(value, str) or not value.strip() or len(value) > 512 for value in stable_ids)
        or len(set(stable_ids)) != len(stable_ids)
    ):
        raise RuntimeError("The MCPStudio operation binding has invalid stable IDs")
    rollback = operation.get("rollback")
    if not isinstance(rollback, dict) or rollback.get("strategy") not in {
        "undo",
        "restore-copy",
        "child-created-restore-copy",
    }:
        raise RuntimeError("The MCPStudio operation binding has an invalid rollback strategy")
    expected_preview = mode == "dry_run"
    if expected_preview != (
        operation.get("intent") == "preview" and operation.get("dryRun") is True
    ):
        if expected_preview or not (
            operation.get("intent") == "apply" and operation.get("dryRun") is False
        ):
            raise RuntimeError("The pilot mode does not match its MCPStudio operation intent")
    return operation


def _operation_receipt(
    operation: dict[str, Any], mode: str, result: dict[str, Any]
) -> dict[str, Any]:
    success = result.get("success")
    if success is not True:
        errors = result.get("errors")
        detail = errors[0] if isinstance(errors, list) and errors else "unknown failure"
        raise RuntimeError(f"The fixed Enclave pilot failed: {detail}")
    canonical_result = json.dumps(result, sort_keys=True, separators=(",", ":"))
    if mode == "dry_run":
        after_revision = operation["expectedRevision"]
        outcome = "previewed"
    else:
        after_revision = "unreal-enclave-pilot-v1:" + hashlib.sha256(
            canonical_result.encode("utf-8")
        ).hexdigest()
        pilot_outputs = result.get("outputs")
        outcome = (
            "replayed"
            if isinstance(pilot_outputs, dict)
            and pilot_outputs.get("idempotent_replay") is True
            else "applied"
        )
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
            "data": {"pilot": result},
        }
    }


def register_enclave_material_pilot_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def enclave_sandstone_pilot(
        ctx: Context,
        mode: Literal["dry_run", "apply", "rollback"] = "dry_run",
        confirm_operation: bool = False,
    ) -> dict[str, Any]:
        """Dry-run, apply, or roll back one exact Enclave sandstone pilot.

        The operation accepts no path, script, asset, material, or map chosen by
        the caller. It is pinned to the staged Middle Eastern Wall PBR set, a
        duplicate of the central pavilion, and
        ``/Game/MCPStudio/EnclavePilot/v1``. Apply and rollback require an
        explicit confirmation. Protected source-map, pavilion, and Ebon Hawk
        package hashes are checked before and after the operation.
        """
        operation = _operation_from_context(ctx, mode)
        if mode in {"apply", "rollback"} and confirm_operation is not True:
            raise RuntimeError(f"confirm_operation=true is required for {mode}")
        code = _pinned_script(mode)
        if mode == "apply":
            code = _deferred_apply_code(code)
        result = _exec_structured(code, f"enclave_sandstone_pilot_{mode}")
        if not isinstance(result, dict):
            raise RuntimeError("The fixed Enclave pilot returned an invalid result")
        outputs = result.get("outputs")
        if mode == "apply" and isinstance(outputs, dict) and outputs.get(
            "queued_deferred_apply"
        ) is True:
            raise RuntimeError(
                "The fixed Enclave pilot was queued on Unreal's next editor tick; "
                "MCPStudio must reconcile the fixed local receipt before replay"
            )
        return _operation_receipt(operation, mode, result)
