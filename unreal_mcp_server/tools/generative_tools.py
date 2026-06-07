"""Generative content provider and import pipeline scaffold tools."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHAT_DIR = _REPO_ROOT / "Saved" / "MCPChat"
_SECRETS_PATH = _CHAT_DIR / "secrets.json"
_SETTINGS_PATH = _CHAT_DIR / "generative_settings.json"
_DEFAULT_GENERATIVE_SETTINGS: Dict[str, Any] = {
    "provider": "tripo",
    "default_model_version": "tripo-default",
    "default_texture_quality": "standard",
    "output_folder": "/Game/Generated",
    "session_credit_budget": 1000,
    "credit_usage_by_session": {},
}


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


def _read_json_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return {}


def _write_json_file(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _normalize_content_folder(value: str) -> str:
    folder = (value or "/Game/Generated").strip().replace("\\", "/")
    if not folder.startswith("/Game"):
        folder = "/Game/Generated"
    while "//" in folder:
        folder = folder.replace("//", "/")
    return folder.rstrip("/") or "/Game/Generated"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_generative_settings() -> Dict[str, Any]:
    settings = dict(_DEFAULT_GENERATIVE_SETTINGS)
    file_settings = _read_json_file(_SETTINGS_PATH)
    settings.update({key: value for key, value in file_settings.items() if key != "tripo_api_key"})
    settings["output_folder"] = _normalize_content_folder(str(settings.get("output_folder", "/Game/Generated")))
    settings["session_credit_budget"] = max(0, _safe_int(settings.get("session_credit_budget"), 1000))
    usage = settings.get("credit_usage_by_session")
    settings["credit_usage_by_session"] = usage if isinstance(usage, dict) else {}
    return settings


def _resolve_tripo_api_key() -> Dict[str, Any]:
    env_key = os.environ.get("TRIPO_API_KEY", "").strip()
    if env_key:
        return {
            "configured": True,
            "source": "env:TRIPO_API_KEY",
            "masked": f"{env_key[:4]}...{env_key[-4:]}" if len(env_key) >= 8 else "configured",
        }

    secrets = _read_json_file(_SECRETS_PATH)
    secrets_key = str(secrets.get("TRIPO_API_KEY") or secrets.get("tripo_api_key") or "").strip()
    if secrets_key:
        return {
            "configured": True,
            "source": "Saved/MCPChat/secrets.json",
            "masked": f"{secrets_key[:4]}...{secrets_key[-4:]}" if len(secrets_key) >= 8 else "configured",
        }

    return {"configured": False, "source": "missing", "masked": ""}


def _save_generative_settings(
    *,
    tripo_api_key: str,
    store_api_key: bool,
    clear_stored_api_key: bool,
    default_model_version: str,
    default_texture_quality: str,
    output_folder: str,
    session_credit_budget: int,
) -> Dict[str, Any]:
    settings = _load_generative_settings()
    settings.update({
        "provider": "tripo",
        "default_model_version": (default_model_version or "tripo-default").strip() or "tripo-default",
        "default_texture_quality": (default_texture_quality or "standard").strip() or "standard",
        "output_folder": _normalize_content_folder(output_folder),
        "session_credit_budget": max(0, _safe_int(session_credit_budget, 1000)),
    })
    _write_json_file(_SETTINGS_PATH, settings)

    secrets = _read_json_file(_SECRETS_PATH)
    if clear_stored_api_key:
        secrets.pop("TRIPO_API_KEY", None)
        secrets.pop("tripo_api_key", None)
    if store_api_key and tripo_api_key.strip():
        secrets["TRIPO_API_KEY"] = tripo_api_key.strip()
    if secrets:
        _write_json_file(_SECRETS_PATH, secrets)
    elif _SECRETS_PATH.exists():
        _SECRETS_PATH.unlink()
    return settings


def _provider_config_outputs() -> Dict[str, Any]:
    settings = _load_generative_settings()
    key_state = _resolve_tripo_api_key()
    return {
        "provider": "tripo",
        "api_key_configured": key_state["configured"],
        "api_key_source": key_state["source"],
        "api_key_masked": key_state["masked"],
        "default_model_version": settings["default_model_version"],
        "default_texture_quality": settings["default_texture_quality"],
        "output_folder": settings["output_folder"],
        "session_credit_budget": settings["session_credit_budget"],
        "credit_usage_by_session": settings["credit_usage_by_session"],
        "settings_path": str(_SETTINGS_PATH),
        "secrets_path": str(_SECRETS_PATH),
        "network_required": False,
        "spend_confirmation_required": True,
    }


def _provider_scaffold() -> List[Dict[str, Any]]:
    config = _provider_config_outputs()
    return [
        {
            "provider": "tripo",
            "status": "configured" if config["api_key_configured"] else "auth_missing",
            "capabilities": [
                "text_to_model",
                "image_to_model",
                "multiview_to_model",
                "refine_model",
                "texture_model",
                "post_process",
                "download_result",
            ],
            "config": {
                "api_key_configured": config["api_key_configured"],
                "api_key_source": config["api_key_source"],
                "default_model_version": config["default_model_version"],
                "default_texture_quality": config["default_texture_quality"],
                "output_folder": config["output_folder"],
                "session_credit_budget": config["session_credit_budget"],
            },
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
            "config": _provider_config_outputs(),
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
    async def gen_get_provider_config(
        ctx: Context,
        include_paths: bool = True,
    ) -> str:
        """Read Tripo auth/config state without exposing the API key value.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#config-and-auth
        Example:
            gen_get_provider_config(include_paths=True)"""
        t0 = time.monotonic()
        inputs = {"include_paths": include_paths}
        outputs = _provider_config_outputs()
        if not include_paths:
            outputs.pop("settings_path", None)
            outputs.pop("secrets_path", None)
        return _result_json(
            success=True,
            stage="gen_get_provider_config",
            message="Loaded generative provider config",
            inputs=inputs,
            outputs=outputs,
            warnings=[] if outputs["api_key_configured"] else ["TRIPO_API_KEY is not configured in the environment or Saved/MCPChat/secrets.json"],
            t0=t0,
        )

    @mcp.tool()
    async def gen_save_provider_config(
        ctx: Context,
        tripo_api_key: str = "",
        store_api_key: bool = False,
        clear_stored_api_key: bool = False,
        default_model_version: str = "tripo-default",
        default_texture_quality: str = "standard",
        output_folder: str = "/Game/Generated",
        session_credit_budget: int = 1000,
    ) -> str:
        """Save Tripo defaults and optionally store/clear the local API key.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#config-and-auth
        Example:
            gen_save_provider_config(default_model_version="tripo-default", output_folder="/Game/Generated", session_credit_budget=750)"""
        t0 = time.monotonic()
        inputs = {
            "store_api_key": store_api_key,
            "clear_stored_api_key": clear_stored_api_key,
            "default_model_version": default_model_version,
            "default_texture_quality": default_texture_quality,
            "output_folder": output_folder,
            "session_credit_budget": session_credit_budget,
            "tripo_api_key_supplied": bool(tripo_api_key.strip()),
        }
        settings = _save_generative_settings(
            tripo_api_key=tripo_api_key,
            store_api_key=store_api_key,
            clear_stored_api_key=clear_stored_api_key,
            default_model_version=default_model_version,
            default_texture_quality=default_texture_quality,
            output_folder=output_folder,
            session_credit_budget=session_credit_budget,
        )
        outputs = _provider_config_outputs()
        outputs["saved_settings"] = {
            "default_model_version": settings["default_model_version"],
            "default_texture_quality": settings["default_texture_quality"],
            "output_folder": settings["output_folder"],
            "session_credit_budget": settings["session_credit_budget"],
        }
        warnings = []
        if tripo_api_key and not store_api_key:
            warnings.append("tripo_api_key was supplied but not stored because store_api_key=False")
        if outputs["api_key_source"].startswith("env:"):
            warnings.append("TRIPO_API_KEY environment variable takes precedence over Saved/MCPChat/secrets.json")
        return _result_json(
            success=True,
            stage="gen_save_provider_config",
            message="Saved generative provider config",
            inputs=inputs,
            outputs=outputs,
            warnings=warnings,
            t0=t0,
        )

    @mcp.tool()
    async def gen_check_credit_budget(
        ctx: Context,
        estimated_credits: int,
        session_name: str = "default",
        operation: str = "tripo_generation",
        confirm_spend: bool = False,
        reserve_credits: bool = False,
    ) -> str:
        """Guard a Tripo spend against the per-session credit budget.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#cost-guard
        Example:
            gen_check_credit_budget(estimated_credits=120, session_name="demo", operation="text_to_model", confirm_spend=True, reserve_credits=True)"""
        t0 = time.monotonic()
        safe_estimate = max(0, _safe_int(estimated_credits, 0))
        safe_session = (session_name or "default").strip() or "default"
        inputs = {
            "estimated_credits": safe_estimate,
            "session_name": safe_session,
            "operation": operation,
            "confirm_spend": confirm_spend,
            "reserve_credits": reserve_credits,
        }
        settings = _load_generative_settings()
        budget = max(0, _safe_int(settings.get("session_credit_budget"), 0))
        usage = settings.setdefault("credit_usage_by_session", {})
        used = max(0, _safe_int(usage.get(safe_session), 0))
        remaining = max(0, budget - used)
        within_budget = safe_estimate <= remaining
        confirm_required = safe_estimate > 0 and not confirm_spend
        approved = within_budget and not confirm_required
        reserved = False
        used_after = used
        remaining_after = remaining
        if approved and reserve_credits and safe_estimate > 0:
            used_after = used + safe_estimate
            remaining_after = max(0, budget - used_after)
            usage[safe_session] = used_after
            settings["credit_usage_by_session"] = usage
            _write_json_file(_SETTINGS_PATH, settings)
            reserved = True

        outputs = {
            "session_name": safe_session,
            "operation": operation,
            "budget": budget,
            "used": used,
            "used_after": used_after,
            "remaining": remaining,
            "remaining_after": remaining_after,
            "estimated_credits": safe_estimate,
            "within_budget": within_budget,
            "confirm_required": confirm_required,
            "approved": approved,
            "reserved": reserved,
        }
        warnings: List[str] = []
        errors: List[str] = []
        message = "Credit spend approved"
        if not within_budget:
            message = "Estimated credit spend exceeds the session budget"
            errors.append(message)
        elif confirm_required:
            message = "Credit spend requires explicit confirmation"
            warnings.append("Set confirm_spend=True only after the user confirms this Tripo credit spend.")

        return _result_json(
            success=approved,
            stage="gen_check_credit_budget",
            message=message,
            inputs=inputs,
            outputs=outputs,
            warnings=warnings,
            errors=errors,
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
