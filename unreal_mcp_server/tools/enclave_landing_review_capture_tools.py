"""Pinned visual-review capture operator for the Enclave landing area."""

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


_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "fixed_scripts" / "enclave_landing_review_capture_v1.py"
_SCRIPT_SHA256 = "a3d0053b7c4702e125ea52421a4c600271056fd6628e650ef5689a6137c91a3e"

_CAPTURE_VIEWS = (
    {
        "key": "wide",
        "location": [-14500.0, -12000.0, 5800.0],
        "orientation": [-17.30510694944663, 47.88641854386461, 0.0],
    },
    {
        "key": "mid",
        "location": [-12000.0, -10000.0, 3600.0],
        "orientation": [-12.32414076587462, 48.77546582428982, 0.0],
    },
    {
        "key": "entry",
        "location": [-9300.0, 500.0, 1500.0],
        "orientation": [-8.785298717884604, 0.0, 0.0],
    },
)


def _pinned_script(mode: str) -> str:
    metadata = _SCRIPT_PATH.lstat()
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if _SCRIPT_PATH.is_symlink() or not _SCRIPT_PATH.is_file() or bool(
        getattr(metadata, "st_file_attributes", 0) & reparse
    ):
        raise RuntimeError("The landing review script identity is unsafe")
    body = _SCRIPT_PATH.read_bytes()
    if hashlib.sha256(body).hexdigest() != _SCRIPT_SHA256:
        raise RuntimeError("The landing review script digest mismatched")
    return (
        f"MCPSTUDIO_MODE = {mode!r}\n"
        "MCPSTUDIO_REVIEW_REVISION = 'v3'\n"
        + body.decode("utf-8")
    )


def _deferred_apply_code(code: str) -> str:
    return f'''
import json as _review_json
import os as _review_os
import traceback as _review_traceback
import unreal as _review_unreal

_REVIEW_BODY = {code!r}
_REVIEW_RECEIPT = _review_os.path.realpath(_review_os.path.join(
    _review_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_landing_review_capture_v3_receipt.json",
))
_REVIEW_FAILURE = _review_os.path.realpath(_review_os.path.join(
    _review_unreal.Paths.project_saved_dir(),
    "MCPStudio/evidence/enclave_landing_review_capture_v3_failure.json",
))
if _review_os.path.exists(_REVIEW_FAILURE):
    raise RuntimeError("The prior deferred landing review capture failed; inspect fixed evidence")
_review_state = {{"started": False, "namespace": None}}
def _run_landing_review_capture(_delta_seconds):
    _handle = _review_state.pop("handle", None)
    if _handle is not None:
        _review_unreal.unregister_slate_post_tick_callback(_handle)
    _review_state["started"] = True
    _namespace = {{"_result": {{}}, "_warnings": [], "_errors": [], "_log_tail": []}}
    _review_state["namespace"] = _namespace
    try:
        exec(_REVIEW_BODY, _namespace, _namespace)
        _review_unreal.log("MCPStudio landing review cameras prepared")
    except Exception as _exc:
        _review_os.makedirs(_review_os.path.dirname(_REVIEW_FAILURE), exist_ok=True)
        with open(_REVIEW_FAILURE, "x", encoding="utf-8") as _stream:
            _review_json.dump({{
                "schema": "unreal_mcp_ghost.enclave-landing-review-capture-failure/v1",
                "error": str(_exc),
                "traceback": _review_traceback.format_exc().splitlines()[-40:],
            }}, _stream, indent=2, sort_keys=True)
            _stream.write("\\n")
        _review_unreal.log_error("MCPStudio landing review capture failed: " + str(_exc))
_review_state["handle"] = _review_unreal.register_slate_post_tick_callback(_run_landing_review_capture)
_result.update({{"queued_deferred_setup": True, "receipt_path": _REVIEW_RECEIPT, "failure_path": _REVIEW_FAILURE}})
'''


def _capture_exact_views(expected_paths: dict[str, str]) -> list[dict[str, Any]]:
    if set(expected_paths) != {view["key"] for view in _CAPTURE_VIEWS}:
        raise RuntimeError("The fixed landing review capture paths are incomplete")
    captures: list[dict[str, Any]] = []
    for view in _CAPTURE_VIEWS:
        key = view["key"]
        path = expected_paths[key]
        render = _exec_structured(
            _pinned_script("render_" + key),
            "enclave_landing_review_capture_render_" + key,
        )
        render_outputs = render.get("outputs", {}) if isinstance(render, dict) else {}
        if render_outputs.get("rendered") is not True:
            raise RuntimeError("Could not render the landing review camera: " + key)
        capture_bytes = render_outputs.get("capture_bytes")
        capture_sha256 = render_outputs.get("capture_sha256")
        if (
            isinstance(capture_bytes, bool)
            or not isinstance(capture_bytes, int)
            or capture_bytes <= 0
            or not isinstance(capture_sha256, str)
            or len(capture_sha256) != 64
        ):
            raise RuntimeError("The native landing review capture was not attested: " + key)
        captures.append({
            "key": key,
            "path": path,
            "capture_bytes": capture_bytes,
            "capture_sha256": capture_sha256,
        })
    return captures


def register_enclave_landing_review_capture_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=False,
            destructiveHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
        structured_output=True,
    )
    def enclave_landing_review_capture(
        ctx: Context,
        mode: Literal["dry_run", "apply", "rollback"] = "dry_run",
        confirm_operation: bool = False,
    ) -> dict[str, Any]:
        """Create or roll back three exact landing-area review cameras and captures.

        The operation accepts no paths, camera transforms, map, actors, or
        capture settings from the caller. It is pinned to the reviewed Enclave
        map, exact prerequisite receipts, three fixed composition cameras, and
        fixed local evidence paths.
        """
        operation = _operation_from_context(ctx, mode)
        if mode in {"apply", "rollback"} and confirm_operation is not True:
            raise RuntimeError("confirm_operation=true is required for " + mode)
        if mode == "apply":
            preview = _exec_structured(
                _pinned_script("dry_run"),
                "enclave_landing_review_capture_preflight",
            )
            preview_outputs = preview.get("outputs", {}) if isinstance(preview, dict) else {}
            if preview_outputs.get("eligible_to_apply") is not True:
                raise RuntimeError("The fixed landing review cameras have a label collision")
            expected_labels = {"MCP_LandingReview_Wide_v3", "MCP_LandingReview_Mid_v3", "MCP_LandingReview_Entry_v3"}
            reusable = set(preview_outputs.get("reusable_camera_labels", []))
            if reusable != expected_labels:
                setup = _exec_structured(
                    _deferred_apply_code(_pinned_script("apply")),
                    "enclave_landing_review_capture_setup",
                )
                setup_outputs = setup.get("outputs", {}) if isinstance(setup, dict) else {}
                if setup_outputs.get("queued_deferred_setup") is True:
                    raise RuntimeError(
                        "The exact landing review cameras were queued for repair; "
                        "MCPStudio must reconcile and replay before native capture"
                    )
                raise RuntimeError("The exact landing review cameras could not be prepared")
            expected_paths = preview_outputs.get("expected_capture_paths")
            if not isinstance(expected_paths, dict):
                raise RuntimeError("The fixed landing review paths were unavailable")
            preparation = _exec_structured(
                _pinned_script("prepare_native_capture"),
                "enclave_landing_review_capture_prepare_native",
            )
            preparation_outputs = (
                preparation.get("outputs", {}) if isinstance(preparation, dict) else {}
            )
            if preparation_outputs.get("prepared") is not True:
                raise RuntimeError("The landing review viewport could not be released for capture")
            _capture_exact_views(expected_paths)
            result = _exec_structured(
                _pinned_script("finalize"),
                "enclave_landing_review_capture_finalize",
            )
        else:
            result = _exec_structured(
                _pinned_script(mode),
                "enclave_landing_review_capture_" + mode,
            )
        if not isinstance(result, dict):
            raise RuntimeError("The fixed landing review capture returned an invalid result")
        return _operation_receipt(operation, mode, result)
