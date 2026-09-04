"""Shared fixed-command connection selection for Unreal MCP tool modules."""

from __future__ import annotations

import os
from typing import Any, Dict


def send_unreal_command(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if os.environ.get("MCPSTUDIO_SPATIAL_SERVER") == "1":
        from mcpstudio_bridge_client import get_mcpstudio_unreal_connection

        unreal = get_mcpstudio_unreal_connection()
    else:
        from unreal_mcp_server import get_unreal_connection

        unreal = get_unreal_connection()
    if not unreal:
        return {"success": False, "message": "Not connected to Unreal Engine"}
    return unreal.send_command(command, params) or {
        "success": False,
        "message": "No response from Unreal Engine",
    }
