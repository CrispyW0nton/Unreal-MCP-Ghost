"""Movie Render Queue tools for UE5."""

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


def register_mrq_tools(mcp: FastMCP):

    @mcp.tool()
    async def mrq_create_job(
        ctx: Context,
        job_name: str = "MCP_Render",
        sequence: str = "",
        map: str = "",
        author: str = "MCP",
        output_directory: str = "",
        file_name_format: str = "{sequence_name}.{frame_number}",
        resolution: Optional[List[int]] = None,
        image_format: str = "png",
        overwrite_existing: bool = True,
        clear_queue: bool = False,
    ) -> str:
        """Create and configure a Movie Render Queue job in the editor queue.

        KB: see knowledge_base/28_MOVIE_RENDER_QUEUE_AND_SEQUENCER.md#mcp-movie-render-queue-tools
        Example:
            mrq_create_job(job_name="Trailer_Master", sequence="/Game/Cinematics/LS_Trailer", resolution=[3840, 2160])"""
        t0 = time.monotonic()
        inputs = {
            "job_name": job_name,
            "sequence": sequence,
            "map": map,
            "author": author,
            "output_directory": output_directory,
            "file_name_format": file_name_format,
            "resolution": resolution or [1920, 1080],
            "image_format": image_format,
            "overwrite_existing": overwrite_existing,
            "clear_queue": clear_queue,
        }
        raw = _send("mrq_create_job", inputs)
        return _bridge_result(stage="mrq_create_job", raw=raw, inputs=inputs, message="Created Movie Render Queue job", t0=t0)

    @mcp.tool()
    async def mrq_add_render_setting(
        ctx: Context,
        job_name: str = "",
        setting_type: str = "output",
        output_directory: str = "",
        file_name_format: str = "",
        resolution: Optional[List[int]] = None,
        image_format: str = "",
        custom_frame_rate: Optional[float] = None,
        handle_frames: Optional[int] = None,
        frame_start: Optional[int] = None,
        frame_end: Optional[int] = None,
        temporal_samples: Optional[int] = None,
        spatial_samples: Optional[int] = None,
        warmup_frames: Optional[int] = None,
        console_variables: Optional[Dict[str, float]] = None,
    ) -> str:
        """Add or update an MRQ output, pass, anti-aliasing, or console variable setting.

        KB: see knowledge_base/28_MOVIE_RENDER_QUEUE_AND_SEQUENCER.md#mcp-movie-render-queue-tools
        Example:
            mrq_add_render_setting(job_name="Trailer_Master", setting_type="anti_aliasing", temporal_samples=8, warmup_frames=16)"""
        t0 = time.monotonic()
        inputs: Dict[str, Any] = {
            "job_name": job_name,
            "setting_type": setting_type,
        }
        optional_values = {
            "output_directory": output_directory,
            "file_name_format": file_name_format,
            "resolution": resolution,
            "image_format": image_format,
            "custom_frame_rate": custom_frame_rate,
            "handle_frames": handle_frames,
            "frame_start": frame_start,
            "frame_end": frame_end,
            "temporal_samples": temporal_samples,
            "spatial_samples": spatial_samples,
            "warmup_frames": warmup_frames,
            "console_variables": console_variables,
        }
        inputs.update({
            key: value for key, value in optional_values.items()
            if value is not None and value != ""
        })
        raw = _send("mrq_add_render_setting", inputs)
        return _bridge_result(stage="mrq_add_render_setting", raw=raw, inputs=inputs, message="Updated Movie Render Queue setting", t0=t0)

    @mcp.tool()
    async def mrq_render_queue(
        ctx: Context,
        executor: str = "pie",
        dry_run: bool = True,
    ) -> str:
        """Validate or start rendering the current Movie Render Queue.

        KB: see knowledge_base/28_MOVIE_RENDER_QUEUE_AND_SEQUENCER.md#mcp-movie-render-queue-tools
        Example:
            mrq_render_queue(dry_run=False, executor="pie")"""
        t0 = time.monotonic()
        inputs = {
            "executor": executor,
            "dry_run": dry_run,
        }
        raw = _send("mrq_render_queue", inputs)
        message = "Validated Movie Render Queue" if dry_run else "Started Movie Render Queue render"
        return _bridge_result(stage="mrq_render_queue", raw=raw, inputs=inputs, message=message, t0=t0)

    logger.info("Movie Render Queue tools registered")
