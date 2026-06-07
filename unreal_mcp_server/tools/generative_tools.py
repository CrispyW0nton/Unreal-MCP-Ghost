"""Generative content provider and import pipeline scaffold tools."""

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


def _result_json(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> str:
    return json.dumps(_make_result(
        success=success,
        stage=stage,
        message=message,
        inputs=inputs,
        outputs=outputs,
        warnings=warnings,
        errors=errors,
        t0=t0,
    ))


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
        return _result_json(
            success=False,
            stage="error",
            message=msg,
            inputs=inputs,
            errors=[msg],
            t0=t0,
        )

    raw_warnings = raw.get("warnings") if isinstance(raw.get("warnings"), list) else []
    outputs = {
        key: value for key, value in raw.items()
        if key not in {"success", "status", "message", "error", "warnings"}
    }
    return _result_json(
        success=True,
        stage=stage,
        message=message,
        inputs=inputs,
        outputs=outputs,
        warnings=(warnings or []) + raw_warnings,
        t0=t0,
    )


def _provider_scaffold() -> List[Dict[str, Any]]:
    return [
        {
            "provider": "tripo",
            "status": "planned",
            "capabilities": [
                "text_to_model",
                "image_to_model",
                "multiview_to_model",
                "refine_model",
                "texture_model",
                "post_process",
                "download_result",
            ],
            "next_milestones": ["D.2 config/auth", "D.3 Tripo task tools", "D.4 auto-import bridge"],
        }
    ]


def register_generative_tools(mcp: FastMCP):

    @mcp.tool()
    async def gen_list_providers(
        ctx: Context,
        include_import_helpers: bool = True,
    ) -> str:
        """List configured generative providers and D.1 import helper readiness.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#provider-scaffold
        Example:
            gen_list_providers(include_import_helpers=True)"""
        t0 = time.monotonic()
        inputs = {"include_import_helpers": include_import_helpers}
        outputs: Dict[str, Any] = {
            "providers": _provider_scaffold(),
            "default_provider": "tripo",
            "network_required": False,
        }
        if include_import_helpers:
            outputs["import_helpers"] = [
                {
                    "tool": "gen_prepare_import_manifest",
                    "native_route": "gen_prepare_import_manifest",
                    "status": "live",
                    "purpose": "Validate source files and normalize /Game import targets before D.4 imports.",
                }
            ]
        return _result_json(
            success=True,
            stage="gen_list_providers",
            message="Listed generative provider scaffold",
            inputs=inputs,
            outputs=outputs,
            t0=t0,
        )

    @mcp.tool()
    async def gen_prepare_import_manifest(
        ctx: Context,
        task_id: str,
        local_files: Optional[List[str]] = None,
        content_path: str = "/Game/Generated",
        asset_name: str = "",
        provider: str = "tripo",
        create_material_instance: bool = True,
        create_blueprint: bool = False,
        overwrite_existing: bool = False,
    ) -> str:
        """Validate and normalize a generated asset import manifest for Unreal.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#import-manifest-helper
        Example:
            gen_prepare_import_manifest(task_id="tripo_task_123", local_files=["C:/Gen/slime.glb"], content_path="/Game/Generated/Enemies")"""
        t0 = time.monotonic()
        inputs = {
            "task_id": task_id,
            "local_files": local_files or [],
            "content_path": content_path,
            "asset_name": asset_name,
            "provider": provider,
            "create_material_instance": create_material_instance,
            "create_blueprint": create_blueprint,
            "overwrite_existing": overwrite_existing,
        }
        raw = _send("gen_prepare_import_manifest", inputs)
        return _bridge_result(
            stage="gen_prepare_import_manifest",
            raw=raw,
            inputs=inputs,
            message="Prepared generated asset import manifest",
            t0=t0,
        )

    logger.info("Generative content tools registered")
