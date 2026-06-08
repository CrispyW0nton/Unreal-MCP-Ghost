"""Generative content provider and import pipeline scaffold tools."""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHAT_DIR = _REPO_ROOT / "Saved" / "MCPChat"
_SECRETS_PATH = _CHAT_DIR / "secrets.json"
_SETTINGS_PATH = _CHAT_DIR / "generative_settings.json"
_TRIPO_BASE_URL = "https://api.tripo3d.ai/v2/openapi"
_TRIPO_FINAL_STATUSES = {"success", "failed", "banned", "expired", "cancelled", "unknown"}
_TRIPO_MODEL_OUTPUT_KEYS = ("model", "base_model", "pbr_model", "rendered_image", "generated_image")
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


def _clean_optional_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _clean_model_version(value: Optional[str]) -> str:
    version = _clean_optional_text(value)
    return "" if version in {"", "tripo-default", "api-default"} else version


def _as_file_object(*, image_path: str = "", image_url: str = "", file_token: str = "") -> Dict[str, Any]:
    token = _clean_optional_text(file_token)
    url = _clean_optional_text(image_url)
    path = _clean_optional_text(image_path)
    if _file_input_count(image_path=path, image_url=url, file_token=token) != 1:
        raise ValueError("Provide exactly one of image_path, image_url, or file_token")
    if token:
        return {"type": "image", "file_token": token}
    if url:
        return {"type": "image", "url": url}
    uploaded = _tripo_upload_file(path)
    return {"type": "image", "file_token": uploaded["file_token"]}


def _file_input_count(*, image_path: str = "", image_url: str = "", file_token: str = "") -> int:
    return sum(bool(_clean_optional_text(value)) for value in (image_path, image_url, file_token))


def _get_tripo_api_key() -> str:
    env_key = os.environ.get("TRIPO_API_KEY", "").strip()
    if env_key:
        return env_key
    secrets = _read_json_file(_SECRETS_PATH)
    return str(secrets.get("TRIPO_API_KEY") or secrets.get("tripo_api_key") or "").strip()


def _load_generative_settings() -> Dict[str, Any]:
    settings = dict(_DEFAULT_GENERATIVE_SETTINGS)
    file_settings = _read_json_file(_SETTINGS_PATH)
    settings.update({key: value for key, value in file_settings.items() if key != "tripo_api_key"})
    settings["output_folder"] = _normalize_content_folder(str(settings.get("output_folder", "/Game/Generated")))
    settings["session_credit_budget"] = max(0, _safe_int(settings.get("session_credit_budget"), 1000))
    usage = settings.get("credit_usage_by_session")
    settings["credit_usage_by_session"] = usage if isinstance(usage, dict) else {}
    return settings


def _tripo_headers(api_key: str, *, content_type: str = "application/json") -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _tripo_json_request(method: str, path: str, payload: Optional[Dict[str, Any]] = None, timeout_s: int = 60) -> Dict[str, Any]:
    api_key = _get_tripo_api_key()
    if not api_key:
        raise RuntimeError("TRIPO_API_KEY is not configured in the environment or Saved/MCPChat/secrets.json")

    url = f"{_TRIPO_BASE_URL}{path}"
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers=_tripo_headers(api_key),
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=max(1, int(timeout_s))) as response:
            text = response.read().decode("utf-8", errors="replace")
            data = json.loads(text) if text else {}
            return {
                "http_status": response.status,
                "trace_id": response.headers.get("X-Tripo-Trace-ID", ""),
                "body": data,
            }
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            body_data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            body_data = {"message": text}
        return {
            "http_status": exc.code,
            "trace_id": exc.headers.get("X-Tripo-Trace-ID", ""),
            "body": body_data,
        }


def _tripo_upload_file(image_path: str, timeout_s: int = 60) -> Dict[str, Any]:
    api_key = _get_tripo_api_key()
    if not api_key:
        raise RuntimeError("TRIPO_API_KEY is not configured in the environment or Saved/MCPChat/secrets.json")
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file does not exist: {image_path}")
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("Tripo direct upload supports images up to 20 MB")

    boundary = f"----unrealmcp{int(time.time() * 1000)}"
    mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    data = path.read_bytes()
    body = b"".join([
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode("utf-8"),
        f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
        data,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ])
    request = urllib.request.Request(
        f"{_TRIPO_BASE_URL}/upload",
        data=body,
        headers=_tripo_headers(api_key, content_type=f"multipart/form-data; boundary={boundary}"),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=max(1, int(timeout_s))) as response:
        response_body = json.loads(response.read().decode("utf-8", errors="replace"))
        data_obj = response_body.get("data", response_body)
        token = data_obj.get("image_token") or data_obj.get("file_token")
        if not token:
            raise RuntimeError("Tripo upload response did not include image_token")
        return {
            "file_token": token,
            "raw": response_body,
            "trace_id": response.headers.get("X-Tripo-Trace-ID", ""),
        }


def _tripo_submit_task(payload: Dict[str, Any], timeout_s: int = 60) -> Dict[str, Any]:
    response = _tripo_json_request("POST", "/task", payload=payload, timeout_s=timeout_s)
    body = response.get("body", {})
    if response.get("http_status", 0) >= 400 or body.get("code", 0) != 0:
        message = body.get("message") or body.get("suggestion") or "Tripo task submission failed"
        raise RuntimeError(message)
    data = body.get("data", {})
    task_id = data.get("task_id")
    if not task_id:
        raise RuntimeError("Tripo task response did not include task_id")
    return {
        "task_id": task_id,
        "request": payload,
        "response": body,
        "trace_id": response.get("trace_id", ""),
    }


def _tripo_get_task(task_id: str, timeout_s: int = 30) -> Dict[str, Any]:
    if not _clean_optional_text(task_id):
        raise ValueError("task_id is required")
    response = _tripo_json_request("GET", f"/task/{urllib.parse.quote(task_id)}", timeout_s=timeout_s)
    body = response.get("body", {})
    if response.get("http_status", 0) >= 400 or body.get("code", 0) != 0:
        message = body.get("message") or body.get("suggestion") or "Tripo task query failed"
        raise RuntimeError(message)
    return {
        "task": body.get("data", {}),
        "response": body,
        "trace_id": response.get("trace_id", ""),
    }


def _download_url(url: str, target_path: Path, timeout_s: int = 120) -> Dict[str, Any]:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=max(1, int(timeout_s))) as response:
        target_path.write_bytes(response.read())
        return {
            "path": str(target_path),
            "bytes": target_path.stat().st_size,
            "http_status": response.status,
        }


def _estimate_tripo_credits(task_type: str, payload: Dict[str, Any]) -> int:
    model_version = str(payload.get("model_version", ""))
    is_p1 = model_version.startswith("P1")
    texture = bool(payload.get("texture", True) or payload.get("pbr", True))
    quality = str(payload.get("texture_quality", "standard")).lower()
    if task_type == "text_to_model":
        base = 30 if is_p1 else 10
        credits = base + (10 if texture and not is_p1 else (10 if texture else 0))
    elif task_type in {"image_to_model", "multiview_to_model"}:
        base = 40 if is_p1 else 20
        credits = base + (10 if texture and not is_p1 else (10 if texture else 0))
    elif task_type == "texture_model":
        credits = 10
    elif task_type == "convert_model":
        advanced_keys = {"quad", "face_limit", "flatten_bottom", "flatten_bottom_threshold", "texture_size", "texture_format", "pivot_to_center_bottom", "scale_factor"}
        credits = 5 + (5 if any(key in payload and payload.get(key) not in (None, False, "", 0) for key in advanced_keys) else 0)
    elif task_type == "refine_model":
        credits = 20
    else:
        credits = 0
    if task_type in {"text_to_model", "image_to_model", "multiview_to_model", "texture_model"}:
        credits += {"standard": 10, "detailed": 20, "extreme": 30}.get(quality, 0) if texture else 0
        if payload.get("smart_low_poly"):
            credits += 10
        if payload.get("quad"):
            credits += 5
        if payload.get("generate_parts"):
            credits += 20
    return max(0, credits)


def _check_and_reserve_credit_budget(
    *,
    estimated_credits: int,
    session_name: str,
    operation: str,
    confirm_spend: bool,
    reserve_credits: bool = True,
) -> Dict[str, Any]:
    safe_session = (session_name or "default").strip() or "default"
    settings = _load_generative_settings()
    budget = max(0, _safe_int(settings.get("session_credit_budget"), 0))
    usage = settings.setdefault("credit_usage_by_session", {})
    used = max(0, _safe_int(usage.get(safe_session), 0))
    remaining = max(0, budget - used)
    estimate = max(0, _safe_int(estimated_credits, 0))
    within_budget = estimate <= remaining
    confirm_required = estimate > 0 and not confirm_spend
    approved = within_budget and not confirm_required
    reserved = False
    used_after = used
    remaining_after = remaining
    if approved and reserve_credits and estimate > 0:
        used_after = used + estimate
        remaining_after = max(0, budget - used_after)
        usage[safe_session] = used_after
        settings["credit_usage_by_session"] = usage
        _write_json_file(_SETTINGS_PATH, settings)
        reserved = True
    return {
        "session_name": safe_session,
        "operation": operation,
        "budget": budget,
        "used": used,
        "used_after": used_after,
        "remaining": remaining,
        "remaining_after": remaining_after,
        "estimated_credits": estimate,
        "within_budget": within_budget,
        "confirm_required": confirm_required,
        "approved": approved,
        "reserved": reserved,
    }


def _release_credit_reservation(credit_guard: Dict[str, Any]) -> None:
    if not credit_guard.get("reserved"):
        return
    settings = _load_generative_settings()
    usage = settings.setdefault("credit_usage_by_session", {})
    session_name = str(credit_guard.get("session_name") or "default")
    estimate = max(0, _safe_int(credit_guard.get("estimated_credits"), 0))
    current = max(0, _safe_int(usage.get(session_name), 0))
    usage[session_name] = max(0, current - estimate)
    settings["credit_usage_by_session"] = usage
    _write_json_file(_SETTINGS_PATH, settings)
    credit_guard["reserved"] = False
    credit_guard["released"] = True
    credit_guard["used_after"] = usage[session_name]
    credit_guard["remaining_after"] = max(0, _safe_int(credit_guard.get("budget"), 0) - usage[session_name])


def _tripo_task_result_json(
    *,
    stage: str,
    inputs: Dict[str, Any],
    payload: Dict[str, Any],
    task_response: Dict[str, Any],
    credit_guard: Dict[str, Any],
    t0: float,
) -> str:
    return _result_json(
        success=True,
        stage=stage,
        message=f"Submitted Tripo {payload['type']} task",
        inputs=inputs,
        outputs={
            "provider": "tripo",
            "task_id": task_response["task_id"],
            "request": payload,
            "credit_guard": credit_guard,
            "trace_id": task_response.get("trace_id", ""),
            "raw_response": task_response.get("response", {}),
        },
        t0=t0,
    )


def _submit_guarded_tripo_task(
    *,
    stage: str,
    inputs: Dict[str, Any],
    payload: Dict[str, Any],
    estimated_credits: int,
    session_name: str,
    confirm_spend: bool,
    t0: float,
) -> str:
    credit_guard = _check_and_reserve_credit_budget(
        estimated_credits=estimated_credits,
        session_name=session_name,
        operation=payload["type"],
        confirm_spend=confirm_spend,
        reserve_credits=True,
    )
    if not credit_guard["approved"]:
        return _result_json(
            success=False,
            stage=stage,
            message="Tripo credit spend requires confirmation or exceeds the session budget",
            inputs=inputs,
            outputs={"request": payload, "credit_guard": credit_guard},
            warnings=["Set confirm_spend=True after user approval to submit the paid Tripo task."] if credit_guard["confirm_required"] else [],
            errors=[] if credit_guard["confirm_required"] else ["Estimated credit spend exceeds the session budget."],
            t0=t0,
        )

    try:
        task_response = _tripo_submit_task(payload)
        return _tripo_task_result_json(
            stage=stage,
            inputs=inputs,
            payload=payload,
            task_response=task_response,
            credit_guard=credit_guard,
            t0=t0,
        )
    except Exception as exc:
        _release_credit_reservation(credit_guard)
        return _result_json(
            success=False,
            stage=stage,
            message=str(exc),
            inputs=inputs,
            outputs={"request": payload, "credit_guard": credit_guard},
            errors=[str(exc)],
            t0=t0,
        )



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
    async def gen_tripo_text_to_model(
        ctx: Context,
        prompt: str,
        model_version: str = "",
        face_limit: int = 0,
        texture: bool = True,
        pbr: bool = True,
        texture_quality: str = "",
        smart_low_poly: bool = False,
        quad: bool = False,
        auto_size: bool = False,
        generate_parts: bool = False,
        orientation: str = "default",
        negative_prompt: str = "",
        model_seed: int = 0,
        texture_seed: int = 0,
        geometry_quality: str = "standard",
        session_name: str = "default",
        confirm_spend: bool = False,
    ) -> str:
        """Submit a Tripo text_to_model task.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_text_to_model(prompt="stylized slime enemy", texture=True, pbr=True, confirm_spend=True)"""
        t0 = time.monotonic()
        settings = _load_generative_settings()
        version = _clean_model_version(model_version or settings.get("default_model_version", ""))
        quality = _clean_optional_text(texture_quality or settings.get("default_texture_quality", "standard")) or "standard"
        payload: Dict[str, Any] = {
            "type": "text_to_model",
            "prompt": prompt,
            "texture": texture,
            "pbr": pbr,
            "texture_quality": quality,
            "smart_low_poly": smart_low_poly,
            "quad": quad,
            "auto_size": auto_size,
            "generate_parts": generate_parts,
        }
        if version:
            payload["model_version"] = version
        if face_limit > 0:
            payload["face_limit"] = face_limit
        if _clean_optional_text(orientation) and orientation != "default":
            payload["orientation"] = orientation
        if _clean_optional_text(negative_prompt):
            payload["negative_prompt"] = negative_prompt
        if model_seed:
            payload["model_seed"] = model_seed
        if texture_seed:
            payload["texture_seed"] = texture_seed
        if geometry_quality and geometry_quality != "standard":
            payload["geometry_quality"] = geometry_quality
        inputs = dict(payload)
        inputs.update({"session_name": session_name, "confirm_spend": confirm_spend})
        return _submit_guarded_tripo_task(
            stage="gen_tripo_text_to_model",
            inputs=inputs,
            payload=payload,
            estimated_credits=_estimate_tripo_credits("text_to_model", payload),
            session_name=session_name,
            confirm_spend=confirm_spend,
            t0=t0,
        )

    @mcp.tool()
    async def gen_tripo_image_to_model(
        ctx: Context,
        image_path: str = "",
        image_url: str = "",
        file_token: str = "",
        model_version: str = "",
        face_limit: int = 0,
        texture: bool = True,
        pbr: bool = True,
        texture_quality: str = "",
        smart_low_poly: bool = False,
        quad: bool = False,
        auto_size: bool = False,
        generate_parts: bool = False,
        orientation: str = "default",
        enable_image_autofix: bool = False,
        model_seed: int = 0,
        texture_seed: int = 0,
        texture_alignment: str = "original_image",
        geometry_quality: str = "standard",
        session_name: str = "default",
        confirm_spend: bool = False,
    ) -> str:
        """Submit a Tripo image_to_model task from a local image, URL, or file token.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_image_to_model(image_url="https://example.com/slime.png", texture=True, confirm_spend=True)"""
        t0 = time.monotonic()
        settings = _load_generative_settings()
        version = _clean_model_version(model_version or settings.get("default_model_version", ""))
        quality = _clean_optional_text(texture_quality or settings.get("default_texture_quality", "standard")) or "standard"
        payload: Dict[str, Any] = {
            "type": "image_to_model",
            "texture": texture,
            "pbr": pbr,
            "texture_quality": quality,
            "smart_low_poly": smart_low_poly,
            "quad": quad,
            "auto_size": auto_size,
            "generate_parts": generate_parts,
            "enable_image_autofix": enable_image_autofix,
            "texture_alignment": texture_alignment,
        }
        if version:
            payload["model_version"] = version
        if face_limit > 0:
            payload["face_limit"] = face_limit
        if _clean_optional_text(orientation) and orientation != "default":
            payload["orientation"] = orientation
        if model_seed:
            payload["model_seed"] = model_seed
        if texture_seed:
            payload["texture_seed"] = texture_seed
        if geometry_quality and geometry_quality != "standard":
            payload["geometry_quality"] = geometry_quality
        inputs = dict(payload)
        inputs.update({
            "image_path": image_path,
            "image_url": image_url,
            "file_token_supplied": bool(file_token),
            "session_name": session_name,
            "confirm_spend": confirm_spend,
        })
        if _file_input_count(image_path=image_path, image_url=image_url, file_token=file_token) != 1:
            return _result_json(
                success=False,
                stage="gen_tripo_image_to_model",
                message="Provide exactly one of image_path, image_url, or file_token",
                inputs=inputs,
                errors=["Provide exactly one of image_path, image_url, or file_token"],
                t0=t0,
            )
        credit_guard = _check_and_reserve_credit_budget(
            estimated_credits=_estimate_tripo_credits("image_to_model", payload),
            session_name=session_name,
            operation="image_to_model",
            confirm_spend=confirm_spend,
            reserve_credits=True,
        )
        if not credit_guard["approved"]:
            return _result_json(
                success=False,
                stage="gen_tripo_image_to_model",
                message="Tripo credit spend requires confirmation or exceeds the session budget",
                inputs=inputs,
                outputs={"request": payload, "credit_guard": credit_guard},
                warnings=["Set confirm_spend=True after user approval to submit the paid Tripo task."] if credit_guard["confirm_required"] else [],
                errors=[] if credit_guard["confirm_required"] else ["Estimated credit spend exceeds the session budget."],
                t0=t0,
            )
        try:
            payload["file"] = _as_file_object(image_path=image_path, image_url=image_url, file_token=file_token)
            task_response = _tripo_submit_task(payload)
            return _tripo_task_result_json(stage="gen_tripo_image_to_model", inputs=inputs, payload=payload, task_response=task_response, credit_guard=credit_guard, t0=t0)
        except Exception as exc:
            _release_credit_reservation(credit_guard)
            return _result_json(success=False, stage="gen_tripo_image_to_model", message=str(exc), inputs=inputs, outputs={"request": payload, "credit_guard": credit_guard}, errors=[str(exc)], t0=t0)

    @mcp.tool()
    async def gen_tripo_multiview_to_model(
        ctx: Context,
        images: Optional[List[Dict[str, str]]] = None,
        model_version: str = "",
        face_limit: int = 0,
        texture: bool = True,
        pbr: bool = True,
        texture_quality: str = "",
        smart_low_poly: bool = False,
        quad: bool = False,
        auto_size: bool = False,
        generate_parts: bool = False,
        model_seed: int = 0,
        texture_seed: int = 0,
        texture_alignment: str = "original_image",
        geometry_quality: str = "standard",
        original_task_id: str = "",
        session_name: str = "default",
        confirm_spend: bool = False,
    ) -> str:
        """Submit a Tripo multiview_to_model task from ordered front/left/back/right images.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_multiview_to_model(images=[{"image_url":"https://example.com/front.png"},{"image_url":"https://example.com/left.png"}], confirm_spend=True)"""
        t0 = time.monotonic()
        settings = _load_generative_settings()
        version = _clean_model_version(model_version or settings.get("default_model_version", ""))
        quality = _clean_optional_text(texture_quality or settings.get("default_texture_quality", "standard")) or "standard"
        payload: Dict[str, Any] = {
            "type": "multiview_to_model",
            "texture": texture,
            "pbr": pbr,
            "texture_quality": quality,
            "smart_low_poly": smart_low_poly,
            "quad": quad,
            "auto_size": auto_size,
            "generate_parts": generate_parts,
            "texture_alignment": texture_alignment,
        }
        if version:
            payload["model_version"] = version
        if face_limit > 0:
            payload["face_limit"] = face_limit
        if model_seed:
            payload["model_seed"] = model_seed
        if texture_seed:
            payload["texture_seed"] = texture_seed
        if geometry_quality and geometry_quality != "standard":
            payload["geometry_quality"] = geometry_quality
        if _clean_optional_text(original_task_id):
            payload["original_task_id"] = original_task_id
        inputs = dict(payload)
        inputs.update({"images": images or [], "session_name": session_name, "confirm_spend": confirm_spend})
        if not _clean_optional_text(original_task_id):
            if not images or len(images) < 2 or len(images) > 4:
                return _result_json(success=False, stage="gen_tripo_multiview_to_model", message="images must contain 2 to 4 ordered views when original_task_id is not supplied", inputs=inputs, errors=["images must contain 2 to 4 ordered views when original_task_id is not supplied"], t0=t0)
            for item in images:
                if _file_input_count(image_path=item.get("image_path", ""), image_url=item.get("image_url", ""), file_token=item.get("file_token", "")) != 1:
                    return _result_json(success=False, stage="gen_tripo_multiview_to_model", message="Each image entry must provide exactly one of image_path, image_url, or file_token", inputs=inputs, errors=["Each image entry must provide exactly one of image_path, image_url, or file_token"], t0=t0)
        credit_guard = _check_and_reserve_credit_budget(
            estimated_credits=_estimate_tripo_credits("multiview_to_model", payload),
            session_name=session_name,
            operation="multiview_to_model",
            confirm_spend=confirm_spend,
            reserve_credits=True,
        )
        if not credit_guard["approved"]:
            return _result_json(success=False, stage="gen_tripo_multiview_to_model", message="Tripo credit spend requires confirmation or exceeds the session budget", inputs=inputs, outputs={"request": payload, "credit_guard": credit_guard}, warnings=["Set confirm_spend=True after user approval to submit the paid Tripo task."] if credit_guard["confirm_required"] else [], errors=[] if credit_guard["confirm_required"] else ["Estimated credit spend exceeds the session budget."], t0=t0)
        try:
            if not _clean_optional_text(original_task_id):
                file_objects = []
                for item in images:
                    file_objects.append(_as_file_object(
                        image_path=item.get("image_path", ""),
                        image_url=item.get("image_url", ""),
                        file_token=item.get("file_token", ""),
                    ))
                while len(file_objects) < 4:
                    file_objects.append({"type": "image"})
                payload["files"] = file_objects
            task_response = _tripo_submit_task(payload)
            return _tripo_task_result_json(stage="gen_tripo_multiview_to_model", inputs=inputs, payload=payload, task_response=task_response, credit_guard=credit_guard, t0=t0)
        except Exception as exc:
            _release_credit_reservation(credit_guard)
            return _result_json(success=False, stage="gen_tripo_multiview_to_model", message=str(exc), inputs=inputs, outputs={"request": payload, "credit_guard": credit_guard}, errors=[str(exc)], t0=t0)

    @mcp.tool()
    async def gen_tripo_refine_model(
        ctx: Context,
        task_id: str,
        session_name: str = "default",
        confirm_spend: bool = False,
    ) -> str:
        """Submit a Tripo refine_model task for a legacy draft model task.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_refine_model(task_id="draft-task-id", confirm_spend=True)"""
        t0 = time.monotonic()
        payload = {"type": "refine_model", "draft_model_task_id": task_id}
        inputs = dict(payload)
        inputs.update({"session_name": session_name, "confirm_spend": confirm_spend})
        return _submit_guarded_tripo_task(stage="gen_tripo_refine_model", inputs=inputs, payload=payload, estimated_credits=_estimate_tripo_credits("refine_model", payload), session_name=session_name, confirm_spend=confirm_spend, t0=t0)

    @mcp.tool()
    async def gen_tripo_texture_model(
        ctx: Context,
        task_id: str,
        texture_prompt: str,
        model_version: str = "v3.0-20250812",
        texture: bool = True,
        pbr: bool = True,
        texture_quality: str = "",
        texture_alignment: str = "original_image",
        texture_seed: int = 0,
        session_name: str = "default",
        confirm_spend: bool = False,
    ) -> str:
        """Submit a Tripo texture_model task for an existing model task.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_texture_model(task_id="model-task-id", texture_prompt="mossy stone", confirm_spend=True)"""
        t0 = time.monotonic()
        settings = _load_generative_settings()
        quality = _clean_optional_text(texture_quality or settings.get("default_texture_quality", "standard")) or "standard"
        payload: Dict[str, Any] = {
            "type": "texture_model",
            "original_model_task_id": task_id,
            "texture_prompt": {"text": texture_prompt},
            "model_version": model_version,
            "texture": texture,
            "pbr": pbr,
            "texture_quality": quality,
            "texture_alignment": texture_alignment,
        }
        if texture_seed:
            payload["texture_seed"] = texture_seed
        inputs = dict(payload)
        inputs.update({"session_name": session_name, "confirm_spend": confirm_spend})
        return _submit_guarded_tripo_task(stage="gen_tripo_texture_model", inputs=inputs, payload=payload, estimated_credits=_estimate_tripo_credits("texture_model", payload), session_name=session_name, confirm_spend=confirm_spend, t0=t0)

    @mcp.tool()
    async def gen_tripo_post_process(
        ctx: Context,
        task_id: str,
        target_format: str = "FBX",
        quad: bool = False,
        face_limit: int = 0,
        pivot_to_center_bottom: bool = False,
        scale_factor: float = 1.0,
        export_orientation: str = "+x",
        session_name: str = "default",
        confirm_spend: bool = False,
    ) -> str:
        """Submit a Tripo convert_model post-process task.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_post_process(task_id="model-task-id", target_format="FBX", confirm_spend=True)"""
        t0 = time.monotonic()
        payload: Dict[str, Any] = {
            "type": "convert_model",
            "original_model_task_id": task_id,
            "format": target_format.upper(),
            "quad": quad,
            "pivot_to_center_bottom": pivot_to_center_bottom,
            "scale_factor": scale_factor,
            "export_orientation": export_orientation,
        }
        if face_limit > 0:
            payload["face_limit"] = face_limit
        inputs = dict(payload)
        inputs.update({"session_name": session_name, "confirm_spend": confirm_spend})
        return _submit_guarded_tripo_task(stage="gen_tripo_post_process", inputs=inputs, payload=payload, estimated_credits=_estimate_tripo_credits("convert_model", payload), session_name=session_name, confirm_spend=confirm_spend, t0=t0)

    @mcp.tool()
    async def gen_tripo_get_task_status(ctx: Context, task_id: str) -> str:
        """Get Tripo task status and output URLs.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_get_task_status(task_id="model-task-id")"""
        t0 = time.monotonic()
        inputs = {"task_id": task_id}
        try:
            result = _tripo_get_task(task_id)
            task = result["task"]
            return _result_json(success=True, stage="gen_tripo_get_task_status", message=f"Tripo task status: {task.get('status', 'unknown')}", inputs=inputs, outputs={"task": task, "trace_id": result.get("trace_id", ""), "final": task.get("status") in _TRIPO_FINAL_STATUSES}, t0=t0)
        except Exception as exc:
            return _result_json(success=False, stage="gen_tripo_get_task_status", message=str(exc), inputs=inputs, errors=[str(exc)], t0=t0)

    @mcp.tool()
    async def gen_tripo_wait_for_task(ctx: Context, task_id: str, timeout_s: int = 900, poll_s: int = 10) -> str:
        """Poll a Tripo task until it reaches a finalized status or timeout.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_wait_for_task(task_id="model-task-id", timeout_s=900, poll_s=10)"""
        t0 = time.monotonic()
        inputs = {"task_id": task_id, "timeout_s": timeout_s, "poll_s": poll_s}
        deadline = time.monotonic() + max(1, int(timeout_s))
        snapshots: List[Dict[str, Any]] = []
        try:
            while True:
                result = _tripo_get_task(task_id)
                task = result["task"]
                snapshots.append({"status": task.get("status"), "progress": task.get("progress"), "running_left_time": task.get("running_left_time")})
                if task.get("status") in _TRIPO_FINAL_STATUSES:
                    return _result_json(success=task.get("status") == "success", stage="gen_tripo_wait_for_task", message=f"Tripo task finalized: {task.get('status')}", inputs=inputs, outputs={"task": task, "snapshots": snapshots}, errors=[] if task.get("status") == "success" else [f"Tripo task finalized as {task.get('status')}"], t0=t0)
                if time.monotonic() >= deadline:
                    return _result_json(success=False, stage="gen_tripo_wait_for_task", message="Timed out waiting for Tripo task", inputs=inputs, outputs={"snapshots": snapshots}, errors=["Timed out waiting for Tripo task"], t0=t0)
                time.sleep(max(1, int(poll_s)))
        except Exception as exc:
            return _result_json(success=False, stage="gen_tripo_wait_for_task", message=str(exc), inputs=inputs, outputs={"snapshots": snapshots}, errors=[str(exc)], t0=t0)

    @mcp.tool()
    async def gen_tripo_download_result(
        ctx: Context,
        task_id: str,
        target_folder: str,
        output_keys: Optional[List[str]] = None,
    ) -> str:
        """Download signed Tripo output URLs for a successful task into a local folder.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_download_result(task_id="model-task-id", target_folder="C:/Generated/Slime")"""
        t0 = time.monotonic()
        keys = output_keys or list(_TRIPO_MODEL_OUTPUT_KEYS)
        inputs = {"task_id": task_id, "target_folder": target_folder, "output_keys": keys}
        try:
            result = _tripo_get_task(task_id)
            task = result["task"]
            if task.get("status") != "success":
                return _result_json(success=False, stage="gen_tripo_download_result", message=f"Task is not successful: {task.get('status')}", inputs=inputs, outputs={"task": task}, errors=[f"Task is not successful: {task.get('status')}"], t0=t0)
            output = task.get("output") if isinstance(task.get("output"), dict) else {}
            downloads = []
            target = Path(target_folder)
            for key in keys:
                url = output.get(key)
                if not url:
                    continue
                parsed = urllib.parse.urlparse(url)
                suffix = Path(parsed.path).suffix or ".bin"
                filename = f"{task_id}_{key}{suffix}"
                downloads.append(_download_url(url, target / filename))
            return _result_json(success=bool(downloads), stage="gen_tripo_download_result", message=f"Downloaded {len(downloads)} Tripo output file(s)", inputs=inputs, outputs={"task_id": task_id, "downloads": downloads, "source_output": output}, errors=[] if downloads else ["No requested output URLs were available to download"], t0=t0)
        except Exception as exc:
            return _result_json(success=False, stage="gen_tripo_download_result", message=str(exc), inputs=inputs, errors=[str(exc)], t0=t0)

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
