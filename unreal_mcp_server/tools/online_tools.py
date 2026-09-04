"""Online Subsystem and EOS configuration tools for UE5."""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")


def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection

    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = unreal.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error("Error in %s: %s", command, exc)
        return {"success": False, "message": str(exc)}


def _make_result(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": stage, "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _bridge_result(
    *,
    stage: str,
    raw: Dict[str, Any],
    inputs: Dict[str, Any],
    message: str,
    t0: float,
    warnings: Optional[List[str]] = None,
) -> str:
    raw = raw or {}
    failed = raw.get("success") is False or raw.get("status") == "error" or bool(raw.get("error"))
    if failed:
        msg = raw.get("error") or raw.get("message") or f"{stage} failed"
        return json.dumps(_make_result(
            success=False,
            stage="error",
            message=msg,
            inputs=inputs,
            errors=[msg],
            t0=t0,
        ))

    outputs = {
        key: value for key, value in raw.items()
        if key not in {"success", "status", "message", "error"}
    }
    return json.dumps(_make_result(
        success=True,
        stage=stage,
        message=message,
        inputs=inputs,
        outputs=outputs,
        warnings=warnings or [],
        t0=t0,
    ))


def register_online_tools(mcp: FastMCP):

    @mcp.tool()
    async def online_inspect_config(
        ctx: Context,
        include_plugins: bool = True,
    ) -> str:
        """Inspect Online Subsystem and EOS project configuration.

        KB: see knowledge_base/30_ONLINE_SUBSYSTEM_AND_EOS.md#mcp-online-subsystem-and-eos-tools
        Example:
            online_inspect_config(include_plugins=True)"""
        t0 = time.monotonic()
        inputs = {"include_plugins": include_plugins}
        raw = _send("online_inspect_config", inputs)
        return _bridge_result(stage="online_inspect_config", raw=raw, inputs=inputs, message="Inspected online subsystem configuration", t0=t0)

    @mcp.tool()
    async def online_configure_default_subsystem(
        ctx: Context,
        default_service: str = "EOS",
        native_service: str = "",
        enable_online_subsystem: bool = True,
    ) -> str:
        """Set the default Online Subsystem service in project config.

        KB: see knowledge_base/30_ONLINE_SUBSYSTEM_AND_EOS.md#mcp-online-subsystem-and-eos-tools
        Example:
            online_configure_default_subsystem(default_service="EOS", native_service="EOS")"""
        t0 = time.monotonic()
        inputs = {
            "default_service": default_service,
            "native_service": native_service,
            "enable_online_subsystem": enable_online_subsystem,
        }
        raw = _send("online_configure_default_subsystem", inputs)
        return _bridge_result(stage="online_configure_default_subsystem", raw=raw, inputs=inputs, message="Configured default Online Subsystem", t0=t0)

    @mcp.tool()
    async def online_create_eos_artifact_config(
        ctx: Context,
        artifact_name: str,
        product_id: str = "",
        sandbox_id: str = "",
        deployment_id: str = "",
        client_id: str = "",
        client_secret: str = "",
        encryption_key: str = "",
        store_secrets: bool = False,
    ) -> str:
        """Create or update EOS artifact identity settings in project config.

        KB: see knowledge_base/30_ONLINE_SUBSYSTEM_AND_EOS.md#mcp-online-subsystem-and-eos-tools
        Example:
            online_create_eos_artifact_config(artifact_name="Dev", product_id="...", sandbox_id="...", deployment_id="...")"""
        t0 = time.monotonic()
        inputs = {
            "artifact_name": artifact_name,
            "product_id": product_id,
            "sandbox_id": sandbox_id,
            "deployment_id": deployment_id,
            "client_id": client_id,
            "client_secret": client_secret if store_secrets else "",
            "encryption_key": encryption_key if store_secrets else "",
            "store_secrets": store_secrets,
        }
        raw = _send("online_create_eos_artifact_config", inputs)
        warnings = [] if store_secrets else ["client_secret and encryption_key were not forwarded because store_secrets=False"]
        return _bridge_result(stage="online_create_eos_artifact_config", raw=raw, inputs=inputs, message="Configured EOS artifact", warnings=warnings, t0=t0)

    @mcp.tool()
    async def online_configure_eos_sessions(
        ctx: Context,
        use_eos_sessions: bool = True,
        use_eos_lobbies: bool = True,
        use_eos_presence: bool = True,
        use_eos_connect: bool = True,
        mirror_stats_to_eos: bool = False,
    ) -> str:
        """Configure EOS session, lobby, presence, connect, and stat mirroring flags.

        KB: see knowledge_base/30_ONLINE_SUBSYSTEM_AND_EOS.md#mcp-online-subsystem-and-eos-tools
        Example:
            online_configure_eos_sessions(use_eos_sessions=True, use_eos_lobbies=True, use_eos_presence=True)"""
        t0 = time.monotonic()
        inputs = {
            "use_eos_sessions": use_eos_sessions,
            "use_eos_lobbies": use_eos_lobbies,
            "use_eos_presence": use_eos_presence,
            "use_eos_connect": use_eos_connect,
            "mirror_stats_to_eos": mirror_stats_to_eos,
        }
        raw = _send("online_configure_eos_sessions", inputs)
        return _bridge_result(stage="online_configure_eos_sessions", raw=raw, inputs=inputs, message="Configured EOS session flags", t0=t0)

    logger.info("Online Subsystem and EOS tools registered")
