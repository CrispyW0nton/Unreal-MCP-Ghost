"""Pinned read-only lighting audit for the Enclave landing area."""

from __future__ import annotations

import hashlib
import json
import stat
from pathlib import Path

from mcp.server.fastmcp import Context
from mcp.types import ToolAnnotations

from tools.exec_substrate import exec_python_structured as _exec_structured
from tools.tool_registration_surface import ToolRegistrationSurface


_SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixed_scripts"
    / "enclave_landing_lighting_audit_v1.py"
)
_SCRIPT_SHA256 = "bf145d1a6e1a6e50ddcabe852f9002aa56112a88f7cb1eb58d1e56a7ee974e00"


def _pinned_script() -> str:
    metadata = _SCRIPT_PATH.lstat()
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        _SCRIPT_PATH.is_symlink()
        or not _SCRIPT_PATH.is_file()
        or bool(getattr(metadata, "st_file_attributes", 0) & reparse)
    ):
        raise RuntimeError("The landing lighting-audit script identity is unsafe")
    body = _SCRIPT_PATH.read_bytes()
    if hashlib.sha256(body).hexdigest() != _SCRIPT_SHA256:
        raise RuntimeError("The landing lighting-audit script digest mismatched")
    return body.decode("utf-8")


def register_enclave_landing_lighting_audit_tools(
    mcp: ToolRegistrationSurface,
) -> None:
    @mcp.tool(
        annotations=ToolAnnotations(
            readOnlyHint=True,
            destructiveHint=False,
            idempotentHint=True,
            openWorldHint=False,
        )
    )
    def enclave_landing_lighting_audit(ctx: Context) -> str:
        """Audit the exact Enclave main-level lighting and exposure context.

        The tool accepts no caller-selected map, actors, properties, paths, or
        execution input. It is pinned to the reviewed Enclave project and
        reports only an explicit allowlist of native lighting, atmosphere,
        fog, and post-process properties without mutating the map.
        """
        result = _exec_structured(
            _pinned_script(),
            "enclave_landing_lighting_audit",
        )
        if not isinstance(result, dict):
            raise RuntimeError("The fixed landing lighting audit returned an invalid result")
        if result.get("success") is not True:
            errors = result.get("errors")
            detail = errors[0] if isinstance(errors, list) and errors else "unknown failure"
            raise RuntimeError("The fixed landing lighting audit failed: " + str(detail))
        return json.dumps(result, sort_keys=True, separators=(",", ":"))
