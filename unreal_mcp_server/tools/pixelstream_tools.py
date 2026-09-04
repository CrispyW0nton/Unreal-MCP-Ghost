"""Pixel Streaming project configuration tools for UE5."""

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


def register_pixelstream_tools(mcp: FastMCP):

    @mcp.tool()
    async def pixelstream_inspect_config(
        ctx: Context,
        include_plugins: bool = True,
    ) -> str:
        """Inspect Pixel Streaming project configuration and plugin availability.

        KB: see knowledge_base/29_PIXEL_STREAMING_AND_REMOTE.md#mcp-pixel-streaming-tools
        Example:
            pixelstream_inspect_config(include_plugins=True)"""
        t0 = time.monotonic()
        inputs = {"include_plugins": include_plugins}
        raw = _send("pixelstream_inspect_config", inputs)
        return _bridge_result(stage="pixelstream_inspect_config", raw=raw, inputs=inputs, message="Inspected Pixel Streaming configuration", t0=t0)

    @mcp.tool()
    async def pixelstream_configure_plugin(
        ctx: Context,
        enable_pixel_streaming: bool = True,
        enable_pixel_streaming_2: bool = False,
        prefer_pixel_streaming_2: bool = False,
    ) -> str:
        """Set Pixel Streaming enablement and preferred generation flags in project config.

        KB: see knowledge_base/29_PIXEL_STREAMING_AND_REMOTE.md#mcp-pixel-streaming-tools
        Example:
            pixelstream_configure_plugin(enable_pixel_streaming=True, prefer_pixel_streaming_2=False)"""
        t0 = time.monotonic()
        inputs = {
            "enable_pixel_streaming": enable_pixel_streaming,
            "enable_pixel_streaming_2": enable_pixel_streaming_2,
            "prefer_pixel_streaming_2": prefer_pixel_streaming_2,
        }
        raw = _send("pixelstream_configure_plugin", inputs)
        return _bridge_result(stage="pixelstream_configure_plugin", raw=raw, inputs=inputs, message="Configured Pixel Streaming plugin flags", t0=t0)

    @mcp.tool()
    async def pixelstream_configure_streamer(
        ctx: Context,
        signalling_url: str = "ws://127.0.0.1:8888",
        streamer_id: str = "DefaultStreamer",
        web_server_port: int = 80,
        signalling_port: int = 8888,
        use_secure_websocket: bool = False,
        render_offscreen: bool = True,
        encoder_target_bitrate: int = 20000000,
    ) -> str:
        """Configure local Pixel Streaming streamer URL, ports, render, and encoder settings.

        KB: see knowledge_base/29_PIXEL_STREAMING_AND_REMOTE.md#mcp-pixel-streaming-tools
        Example:
            pixelstream_configure_streamer(signalling_url="ws://127.0.0.1:8888", streamer_id="LocalDemo")"""
        t0 = time.monotonic()
        inputs = {
            "signalling_url": signalling_url,
            "streamer_id": streamer_id,
            "web_server_port": web_server_port,
            "signalling_port": signalling_port,
            "use_secure_websocket": use_secure_websocket,
            "render_offscreen": render_offscreen,
            "encoder_target_bitrate": encoder_target_bitrate,
        }
        raw = _send("pixelstream_configure_streamer", inputs)
        return _bridge_result(stage="pixelstream_configure_streamer", raw=raw, inputs=inputs, message="Configured Pixel Streaming streamer settings", t0=t0)

    @mcp.tool()
    async def pixelstream_create_launch_profile(
        ctx: Context,
        profile_name: str = "LocalPixelStreaming",
        signalling_url: str = "ws://127.0.0.1:8888",
        streamer_id: str = "DefaultStreamer",
        render_offscreen: bool = True,
        resolution_x: int = 1280,
        resolution_y: int = 720,
    ) -> str:
        """Create a reusable Pixel Streaming launch profile and return its launch args.

        KB: see knowledge_base/29_PIXEL_STREAMING_AND_REMOTE.md#mcp-pixel-streaming-tools
        Example:
            pixelstream_create_launch_profile(profile_name="LocalPixelStreaming", resolution_x=1280, resolution_y=720)"""
        t0 = time.monotonic()
        inputs = {
            "profile_name": profile_name,
            "signalling_url": signalling_url,
            "streamer_id": streamer_id,
            "render_offscreen": render_offscreen,
            "resolution_x": resolution_x,
            "resolution_y": resolution_y,
        }
        raw = _send("pixelstream_create_launch_profile", inputs)
        return _bridge_result(stage="pixelstream_create_launch_profile", raw=raw, inputs=inputs, message="Created Pixel Streaming launch profile", t0=t0)

    logger.info("Pixel Streaming tools registered")
