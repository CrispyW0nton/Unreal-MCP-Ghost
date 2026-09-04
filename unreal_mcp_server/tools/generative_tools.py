"""Generative content provider and import pipeline scaffold tools."""

from __future__ import annotations

import asyncio
import json
import logging
import mimetypes
import os
import base64
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP
from tools.generative import ProviderRegistry
from tools.generative.tripo import TRIPO_PROVIDER
from tools.generative.uthana import UTHANA_PROVIDER

logger = logging.getLogger("UnrealMCP")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHAT_DIR = _REPO_ROOT / "Saved" / "MCPChat"
_SECRETS_PATH = _CHAT_DIR / "secrets.json"
_SETTINGS_PATH = _CHAT_DIR / "generative_settings.json"
_PROVIDERS = ProviderRegistry([TRIPO_PROVIDER, UTHANA_PROVIDER])
_TRIPO_PROVIDER = _PROVIDERS.get("tripo")
_UTHANA_PROVIDER = _PROVIDERS.get("uthana")
_TRIPO_BASE_URL = _TRIPO_PROVIDER.base_url
_UTHANA_BASE_URL = _UTHANA_PROVIDER.base_url
_UTHANA_DOWNLOAD_BASE_URL = "https://uthana.com"
_TRIPO_FINAL_STATUSES = set(_TRIPO_PROVIDER.final_statuses)
_UTHANA_FINAL_STATUSES = set(_UTHANA_PROVIDER.final_statuses)
_TRIPO_MODEL_OUTPUT_KEYS = tuple(_TRIPO_PROVIDER.output_policy.model_output_keys)
_TRIPO_IMPORT_OUTPUT_KEYS = tuple(_TRIPO_PROVIDER.output_policy.import_output_keys)
_TRIPO_MODEL_EXTS = set(_TRIPO_PROVIDER.output_policy.model_extensions)
_TRIPO_IMAGE_EXTS = set(_TRIPO_PROVIDER.output_policy.image_extensions)
_UTHANA_MOTION_EXTS = set(_UTHANA_PROVIDER.output_policy.model_extensions)
_DEFAULT_GENERATIVE_SETTINGS: Dict[str, Any] = {
    "provider": "tripo",
    "animation_provider": "uthana",
    "default_model_version": "tripo-default",
    "default_texture_quality": "standard",
    "output_folder": "/Game/Generated",
    "animation_output_folder": "/Game/Generated/Animations",
    "uthana_default_character_id": "cXi2eAP19XwQ",
    "session_credit_budget": 1000,
    "credit_usage_by_session": {},
}
_TEXTURE_PAINT_SESSIONS_PATH = _CHAT_DIR / "texture_paint_sessions.json"


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


def _normalize_optional_path_or_url(value: str) -> str:
    text = (value or "").strip().replace("\\", "/")
    if text.lower().startswith(("http://", "https://")):
        return text
    return text


def _save_texture_paint_session(session_record: Dict[str, Any]) -> Dict[str, Any]:
    data = _read_json_file(_TEXTURE_PAINT_SESSIONS_PATH)
    sessions = data.get("sessions")
    if not isinstance(sessions, list):
        sessions = []
    sessions.append(session_record)
    data["sessions"] = sessions[-100:]
    _write_json_file(_TEXTURE_PAINT_SESSIONS_PATH, data)
    return {"sessions_path": str(_TEXTURE_PAINT_SESSIONS_PATH), "saved_count": len(data["sessions"])}


def _load_texture_paint_sessions() -> List[Dict[str, Any]]:
    data = _read_json_file(_TEXTURE_PAINT_SESSIONS_PATH)
    sessions = data.get("sessions")
    return [item for item in sessions if isinstance(item, dict)] if isinstance(sessions, list) else []


def _coerce_json_object(value: str) -> Dict[str, Any]:
    text = _clean_optional_text(value)
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _nested_dict(data: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _readiness_gate(name: str, ready: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "ready": bool(ready), "detail": detail}


def _latest_texture_paint_session(session_name: str = "", model_task_id: str = "") -> Dict[str, Any]:
    sessions = _load_texture_paint_sessions()
    safe_session = _clean_optional_text(session_name)
    safe_model_task_id = _clean_optional_text(model_task_id)
    for session in reversed(sessions):
        if safe_session and session.get("session_name") != safe_session:
            continue
        if safe_model_task_id and session.get("model_task_id") != safe_model_task_id:
            continue
        return session
    return sessions[-1] if sessions else {}


def _record_texture_paint_snapshot(
    *,
    session_name: str,
    model_task_id: str,
    snapshot: Dict[str, Any],
) -> Dict[str, Any]:
    data = _read_json_file(_TEXTURE_PAINT_SESSIONS_PATH)
    sessions = data.get("sessions")
    if not isinstance(sessions, list):
        return {"updated": False, "reason": "no texture-paint sessions file"}
    safe_session = _clean_optional_text(session_name)
    safe_model_task_id = _clean_optional_text(model_task_id)
    for index in range(len(sessions) - 1, -1, -1):
        session = sessions[index]
        if not isinstance(session, dict):
            continue
        if safe_session and session.get("session_name") != safe_session:
            continue
        if safe_model_task_id and session.get("model_task_id") != safe_model_task_id:
            continue
        snapshots = session.get("viewport_snapshots")
        if not isinstance(snapshots, list):
            snapshots = []
        snapshots.append(snapshot)
        session["viewport_snapshots"] = snapshots[-25:]
        sessions[index] = session
        data["sessions"] = sessions
        _write_json_file(_TEXTURE_PAINT_SESSIONS_PATH, data)
        return {"updated": True, "session": session, "sessions_path": str(_TEXTURE_PAINT_SESSIONS_PATH)}
    return {"updated": False, "reason": "matching texture-paint session was not found"}


def _record_texture_paint_pass(
    *,
    session_name: str,
    model_task_id: str,
    paint_pass: Dict[str, Any],
) -> Dict[str, Any]:
    data = _read_json_file(_TEXTURE_PAINT_SESSIONS_PATH)
    sessions = data.get("sessions")
    if not isinstance(sessions, list):
        return {"updated": False, "reason": "no texture-paint sessions file"}
    safe_session = _clean_optional_text(session_name)
    safe_model_task_id = _clean_optional_text(model_task_id)
    for index in range(len(sessions) - 1, -1, -1):
        session = sessions[index]
        if not isinstance(session, dict):
            continue
        if safe_session and session.get("session_name") != safe_session:
            continue
        if safe_model_task_id and session.get("model_task_id") != safe_model_task_id:
            continue
        paint_passes = session.get("paint_passes")
        if not isinstance(paint_passes, list):
            paint_passes = []
        paint_passes.append(paint_pass)
        session["paint_passes"] = paint_passes[-100:]
        sessions[index] = session
        data["sessions"] = sessions
        _write_json_file(_TEXTURE_PAINT_SESSIONS_PATH, data)
        return {"updated": True, "session": session, "sessions_path": str(_TEXTURE_PAINT_SESSIONS_PATH)}
    return {"updated": False, "reason": "matching texture-paint session was not found"}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_optional_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _clean_model_version(value: Optional[str]) -> str:
    return _TRIPO_PROVIDER.normalize_model_version(value)


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


def _safe_name(value: str, default: str = "GeneratedAsset") -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in (value or "").strip())
    cleaned = cleaned.strip("_")
    return cleaned or default


_TEXTURE_CHANNEL_ALIASES = {
    "basecolor": "BaseColor",
    "base_color": "BaseColor",
    "albedo": "BaseColor",
    "diffuse": "BaseColor",
    "normal": "Normal",
    "normals": "Normal",
    "orm": "ORM",
    "occlusionroughnessmetallic": "ORM",
    "occlusion_roughness_metallic": "ORM",
    "emissive": "Emissive",
    "emissivecolor": "Emissive",
    "emissive_color": "Emissive",
}
_TEXTURE_PARAMETER_NAMES = {
    "BaseColor": "BaseColorTexture",
    "Normal": "NormalTexture",
    "ORM": "ORMTexture",
    "Emissive": "EmissiveTexture",
}
_TEXTURE_RESOLUTIONS = {512, 1024, 2048, 4096}


def _normalize_texture_channels(channels: Optional[List[str]]) -> Dict[str, Any]:
    requested = channels or ["BaseColor", "Normal", "ORM"]
    normalized: List[str] = []
    invalid: List[str] = []
    for channel in requested:
        raw = str(channel or "").strip()
        key = raw.replace("-", "_").replace(" ", "_").lower()
        canonical = _TEXTURE_CHANNEL_ALIASES.get(key)
        if not canonical:
            invalid.append(raw)
            continue
        if canonical not in normalized:
            normalized.append(canonical)
    return {
        "channels": normalized,
        "invalid_channels": invalid,
    }


def _normalize_texture_resolution(resolution: int) -> Dict[str, Any]:
    value = _safe_int(resolution, 1024)
    return {
        "resolution": value,
        "valid": value in _TEXTURE_RESOLUTIONS,
        "allowed_resolutions": sorted(_TEXTURE_RESOLUTIONS),
    }


def _content_parent_and_name(asset_path: str, default_folder: str, default_name: str) -> Dict[str, str]:
    normalized = _normalize_content_folder(asset_path) if asset_path.startswith("/Game") else ""
    if not normalized:
        return {"folder": default_folder, "name": default_name, "path": f"{default_folder}/{default_name}"}
    parts = normalized.rsplit("/", 1)
    if len(parts) == 1:
        return {"folder": default_folder, "name": default_name, "path": f"{default_folder}/{default_name}"}
    folder, name = parts
    safe_name = _safe_name(name, default_name)
    return {"folder": folder or default_folder, "name": safe_name, "path": f"{folder}/{safe_name}"}


def _texture_from_prompt_plan(
    *,
    prompt: str,
    channels: List[str],
    resolution: int,
    content_path: str,
    asset_name: str,
    master_material_path: str,
) -> Dict[str, Any]:
    safe_content_path = _normalize_content_folder(content_path)
    safe_asset_name = _safe_name(asset_name or prompt[:48], "GeneratedTexture")
    texture_folder = f"{safe_content_path}/Textures"
    material_folder = f"{safe_content_path}/Materials"
    master = _content_parent_and_name(
        master_material_path or "/Game/Materials/M_Master_GeneratedTexture",
        "/Game/Materials",
        "M_Master_GeneratedTexture",
    )
    material_instance_path = f"{material_folder}/MI_{safe_asset_name}"
    texture_paths = {
        channel: f"{texture_folder}/T_{safe_asset_name}_{channel}"
        for channel in channels
    }
    texture_parameters = {
        _TEXTURE_PARAMETER_NAMES[channel]: texture_paths[channel]
        for channel in channels
        if channel in _TEXTURE_PARAMETER_NAMES
    }
    return {
        "provider": "tripo",
        "prompt": prompt,
        "channels": channels,
        "resolution": resolution,
        "content_path": safe_content_path,
        "texture_folder": texture_folder,
        "texture_assets": texture_paths,
        "master_material": master["path"],
        "material_instance": material_instance_path,
        "texture_parameters": texture_parameters,
        "material_tool_handoff": [
            {
                "tool": "material_create_master",
                "args": {
                    "material_name": master["name"],
                    "folder_path": master["folder"],
                    "use_texture_parameters": True,
                    "save": True,
                },
            },
            {
                "tool": "material_create_instance_from_master",
                "args": {
                    "instance_name": f"MI_{safe_asset_name}",
                    "parent_material_path": master["path"],
                    "folder_path": material_folder,
                    "save": True,
                },
            },
            {
                "tool": "material_set_instance_parameters_bulk",
                "args": {
                    "material_instance_path": material_instance_path,
                    "texture_parameters": texture_parameters,
                    "save": True,
                },
            },
        ],
    }


def _default_tripo_download_folder(task_id: str) -> Path:
    return _CHAT_DIR / "tripo_downloads" / _safe_name(task_id, "tripo_task")


def _suffix_for_tripo_output(key: str, url: str) -> str:
    return _TRIPO_PROVIDER.output_suffix(key, url)


def _download_tripo_output_files(
    *,
    task_id: str,
    output: Dict[str, Any],
    target_folder: Path,
    output_keys: List[str],
) -> List[Dict[str, Any]]:
    downloads: List[Dict[str, Any]] = []
    for key in output_keys:
        url = output.get(key)
        if not url:
            continue
        suffix = _suffix_for_tripo_output(key, str(url))
        filename = f"{_safe_name(task_id, 'tripo_task')}_{key}{suffix}"
        download = _download_url(str(url), target_folder / filename)
        download["key"] = key
        download["suffix"] = suffix
        downloads.append(download)
    return downloads


def _select_primary_model_download(downloads: List[Dict[str, Any]]) -> Dict[str, Any]:
    return _TRIPO_PROVIDER.select_primary_model_download(downloads)


def _capture_import_thumbnail(task_id: str, asset_name: str) -> Dict[str, Any]:
    artifact_dir = _REPO_ROOT / ".mcp_artifacts" / "screenshots"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{int(time.time())}_{_safe_name(task_id, 'tripo_task')}_{_safe_name(asset_name, 'asset')}_thumbnail.png"
    filepath = artifact_dir / filename
    raw = _send("take_screenshot", {
        "filepath": str(filepath),
        "filename": str(filepath),
        "show_ui": False,
        "resolution": [1024, 1024],
    })
    failed = raw.get("success") is False or raw.get("status") == "error" or bool(raw.get("error"))
    return {
        "success": not failed and filepath.exists(),
        "path": str(filepath) if filepath.exists() else "",
        "native_response": raw,
    }


def _get_tripo_api_key() -> str:
    env_key = os.environ.get("TRIPO_API_KEY", "").strip()
    if env_key:
        return env_key
    secrets = _read_json_file(_SECRETS_PATH)
    return str(secrets.get("TRIPO_API_KEY") or secrets.get("tripo_api_key") or "").strip()


def _get_uthana_api_key() -> str:
    env_key = os.environ.get("UTHANA_API_KEY", "").strip()
    if env_key:
        return env_key
    secrets = _read_json_file(_SECRETS_PATH)
    return str(secrets.get("UTHANA_API_KEY") or secrets.get("uthana_api_key") or "").strip()


def _load_generative_settings() -> Dict[str, Any]:
    settings = dict(_DEFAULT_GENERATIVE_SETTINGS)
    file_settings = _read_json_file(_SETTINGS_PATH)
    settings.update({key: value for key, value in file_settings.items() if key != "tripo_api_key"})
    settings["output_folder"] = _normalize_content_folder(str(settings.get("output_folder", "/Game/Generated")))
    settings["animation_output_folder"] = _normalize_content_folder(str(settings.get("animation_output_folder", "/Game/Generated/Animations")))
    settings["session_credit_budget"] = max(0, _safe_int(settings.get("session_credit_budget"), 1000))
    usage = settings.get("credit_usage_by_session")
    settings["credit_usage_by_session"] = usage if isinstance(usage, dict) else {}
    return settings


def _tripo_headers(api_key: str, *, content_type: str = "application/json") -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {api_key}"}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def _uthana_headers(api_key: str, *, content_type: str = "application/json") -> Dict[str, str]:
    auth_value = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    headers = {"Authorization": f"Basic {auth_value}"}
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


def _uthana_graphql_request(query: str, variables: Optional[Dict[str, Any]] = None, timeout_s: int = 60) -> Dict[str, Any]:
    api_key = _get_uthana_api_key()
    if not api_key:
        raise RuntimeError("UTHANA_API_KEY is not configured in the environment or Saved/MCPChat/secrets.json")

    payload = {"query": query, "variables": variables or {}}
    request = urllib.request.Request(
        _UTHANA_BASE_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=_uthana_headers(api_key),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(1, int(timeout_s))) as response:
            text = response.read().decode("utf-8", errors="replace")
            body = json.loads(text) if text else {}
            errors = body.get("errors") if isinstance(body, dict) else None
            if errors:
                first_error = errors[0] if isinstance(errors, list) and errors else {}
                message = first_error.get("message") if isinstance(first_error, dict) else str(first_error)
                raise RuntimeError(message or "Uthana GraphQL request failed")
            return {
                "http_status": response.status,
                "body": body,
            }
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            body_data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            body_data = {"message": text}
        message = body_data.get("message") if isinstance(body_data, dict) else ""
        errors = body_data.get("errors") if isinstance(body_data, dict) else None
        if isinstance(errors, list) and errors:
            first_error = errors[0]
            if isinstance(first_error, dict):
                message = first_error.get("message") or message
        raise RuntimeError(message or f"Uthana GraphQL request failed with HTTP {exc.code}") from exc


def _uthana_graphql_multipart_upload(
    *,
    query: str,
    variables: Dict[str, Any],
    file_variable: str,
    file_path: Path,
    timeout_s: int = 180,
) -> Dict[str, Any]:
    api_key = _get_uthana_api_key()
    if not api_key:
        raise RuntimeError("UTHANA_API_KEY is not configured in the environment or Saved/MCPChat/secrets.json")
    if not file_path.exists():
        raise FileNotFoundError(f"Video file does not exist: {file_path}")

    boundary = f"----unrealmcputhana{int(time.time() * 1000)}"
    operations = {"query": query, "variables": variables}
    upload_map = {"0": [f"variables.{file_variable}"]}
    mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    file_bytes = file_path.read_bytes()
    body = b"".join([
        f"--{boundary}\r\n".encode("utf-8"),
        b'Content-Disposition: form-data; name="operations"\r\n',
        b"Content-Type: application/json\r\n\r\n",
        json.dumps(operations).encode("utf-8"),
        b"\r\n",
        f"--{boundary}\r\n".encode("utf-8"),
        b'Content-Disposition: form-data; name="map"\r\n',
        b"Content-Type: application/json\r\n\r\n",
        json.dumps(upload_map).encode("utf-8"),
        b"\r\n",
        f"--{boundary}\r\n".encode("utf-8"),
        f'Content-Disposition: form-data; name="0"; filename="{file_path.name}"\r\n'.encode("utf-8"),
        f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
        file_bytes,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ])
    request = urllib.request.Request(
        _UTHANA_BASE_URL,
        data=body,
        headers=_uthana_headers(api_key, content_type=f"multipart/form-data; boundary={boundary}"),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(1, int(timeout_s))) as response:
            text = response.read().decode("utf-8", errors="replace")
            body_data = json.loads(text) if text else {}
            errors = body_data.get("errors") if isinstance(body_data, dict) else None
            if errors:
                first_error = errors[0] if isinstance(errors, list) and errors else {}
                message = first_error.get("message") if isinstance(first_error, dict) else str(first_error)
                raise RuntimeError(message or "Uthana GraphQL upload failed")
            return {
                "http_status": response.status,
                "body": body_data,
            }
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            body_data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            body_data = {"message": text}
        message = body_data.get("message") if isinstance(body_data, dict) else ""
        errors = body_data.get("errors") if isinstance(body_data, dict) else None
        if isinstance(errors, list) and errors:
            first_error = errors[0]
            if isinstance(first_error, dict):
                message = first_error.get("message") or message
        raise RuntimeError(message or f"Uthana GraphQL upload failed with HTTP {exc.code}") from exc


def _uthana_get_account(timeout_s: int = 30) -> Dict[str, Any]:
    query = """
    query UnrealMCPUthanaAccount {
      user {
        id
        name
        email
        org {
          id
          name
          motion_download_secs_per_month
          motion_download_secs_per_month_remaining
          characters_allowed
          characters_allowed_remaining
        }
      }
    }
    """
    response = _uthana_graphql_request(query, timeout_s=timeout_s)
    data = response.get("body", {}).get("data", {})
    user = data.get("user") if isinstance(data, dict) else {}
    user = user if isinstance(user, dict) else {}
    return {
        "user": user,
        "org": user.get("org") if isinstance(user.get("org"), dict) else {},
        "http_status": response.get("http_status", 0),
    }


def _uthana_create_character(
    *,
    file_path: str,
    name: str,
    auto_rig: bool,
    auto_rig_front_facing: bool,
    include_fingers: bool,
    rerig_target: str = "",
    timeout_s: int = 180,
) -> Dict[str, Any]:
    query = """
    mutation UnrealMCPCreateCharacter(
      $file: Upload!,
      $name: String!,
      $autoRig: Boolean,
      $autoRigFrontFacing: Boolean,
      $includeFingers: Boolean,
      $rerigTarget: String
    ) {
      create_character(
        file: $file,
        name: $name,
        auto_rig: $autoRig,
        auto_rig_front_facing: $autoRigFrontFacing,
        include_fingers: $includeFingers,
        rerig_target: $rerigTarget
      ) {
        character {
          id
          name
          created
          updated
          assets {
            id
            filename
            mimetype
            type
            size
          }
        }
        auto_rig_confidence
        message
      }
    }
    """
    variables = {
        "file": None,
        "name": name,
        "autoRig": bool(auto_rig),
        "autoRigFrontFacing": bool(auto_rig_front_facing),
        "includeFingers": bool(include_fingers),
        "rerigTarget": _clean_optional_text(rerig_target) or None,
    }
    response = _uthana_graphql_multipart_upload(
        query=query,
        variables=variables,
        file_variable="file",
        file_path=Path(file_path),
        timeout_s=timeout_s,
    )
    data = response.get("body", {}).get("data", {})
    created = data.get("create_character") if isinstance(data, dict) else {}
    created = created if isinstance(created, dict) else {}
    character = created.get("character") if isinstance(created.get("character"), dict) else {}
    character_id = _clean_optional_text(str(character.get("id", "")))
    if not character_id:
        raise RuntimeError("Uthana create_character response did not include character.id")
    return {
        "character": character,
        "character_id": character_id,
        "character_name": character.get("name", ""),
        "auto_rig_confidence": created.get("auto_rig_confidence"),
        "provider_message": created.get("message", ""),
        "http_status": response.get("http_status", 0),
    }


def _uthana_get_character(character_id: str, timeout_s: int = 30) -> Dict[str, Any]:
    safe_character_id = _clean_optional_text(character_id)
    if not safe_character_id:
        raise ValueError("character_id is required")
    query = """
    query UnrealMCPUthanaCharacter($id: String!) {
      character(id: $id) {
        id
        name
        created
        updated
        deleted
        org_id
        assets {
          id
          filename
          mimetype
          type
          size
        }
      }
    }
    """
    response = _uthana_graphql_request(query, {"id": safe_character_id}, timeout_s=timeout_s)
    data = response.get("body", {}).get("data", {})
    character = data.get("character") if isinstance(data, dict) else {}
    character = character if isinstance(character, dict) else {}
    if not character:
        raise RuntimeError(f"Uthana character not found or not accessible: {safe_character_id}")
    return {"character": character, "http_status": response.get("http_status", 0)}


def _uthana_create_text_motion(*, prompt: str, character_id: str, foot_ik: bool, timeout_s: int = 60) -> Dict[str, Any]:
    query = """
    mutation UnrealMCPCreateTextToMotion($prompt: String!, $characterId: String, $footIk: Boolean) {
      create_text_to_motion(prompt: $prompt, character_id: $characterId, foot_ik: $footIk) {
        motion {
          id
          name
          created
          updated
          assets {
            id
            filename
          }
        }
      }
    }
    """
    response = _uthana_graphql_request(
        query,
        {"prompt": prompt, "characterId": _clean_optional_text(character_id) or None, "footIk": bool(foot_ik)},
        timeout_s=timeout_s,
    )
    data = response.get("body", {}).get("data", {})
    created = data.get("create_text_to_motion") if isinstance(data, dict) else {}
    motion = created.get("motion") if isinstance(created, dict) else {}
    motion = motion if isinstance(motion, dict) else {}
    motion_id = _clean_optional_text(str(motion.get("id", "")))
    if not motion_id:
        raise RuntimeError("Uthana create_text_to_motion response did not include motion.id")
    return {
        "motion": motion,
        "motion_id": motion_id,
        "motion_name": motion.get("name", ""),
        "http_status": response.get("http_status", 0),
    }


def _uthana_create_locomotion(
    *,
    character_id: str,
    travel_angle: float,
    move_speed: float,
    strides: int,
    style_id: str = "",
    timeout_s: int = 60,
) -> Dict[str, Any]:
    query = """
    mutation UnrealMCPCreateLocomotion(
      $characterId: String!,
      $travelAngle: Float,
      $moveSpeed: Float,
      $strides: Int,
      $styleId: String
    ) {
      create_locomotion(
        character_id: $characterId,
        travel_angle: $travelAngle,
        move_speed: $moveSpeed,
        strides: $strides,
        style_id: $styleId
      ) {
        motion {
          id
          name
          created
          updated
          assets {
            id
            filename
          }
        }
      }
    }
    """
    response = _uthana_graphql_request(
        query,
        {
            "characterId": _clean_optional_text(character_id),
            "travelAngle": float(travel_angle),
            "moveSpeed": float(move_speed),
            "strides": int(strides),
            "styleId": _clean_optional_text(style_id) or None,
        },
        timeout_s=timeout_s,
    )
    data = response.get("body", {}).get("data", {})
    created = data.get("create_locomotion") if isinstance(data, dict) else {}
    motion = created.get("motion") if isinstance(created, dict) else {}
    motion = motion if isinstance(motion, dict) else {}
    motion_id = _clean_optional_text(str(motion.get("id", "")))
    if not motion_id:
        raise RuntimeError("Uthana create_locomotion response did not include motion.id")
    return {
        "motion": motion,
        "motion_id": motion_id,
        "motion_name": motion.get("name", ""),
        "http_status": response.get("http_status", 0),
    }


def _uthana_create_video_motion(
    *,
    video_file: str,
    motion_name: str,
    character_id: str = "",
    model: str = "",
    timeout_s: int = 180,
) -> Dict[str, Any]:
    safe_model = _clean_optional_text(model)
    if safe_model:
        query = """
        mutation UnrealMCPCreateVideoToMotion($file: Upload!, $motionName: String!, $characterId: String, $model: String) {
          create_video_to_motion(file: $file, motion_name: $motionName, character_id: $characterId, model: $model) {
            job {
              id
              status
              result
            }
          }
        }
        """
        variables: Dict[str, Any] = {"file": None, "motionName": motion_name, "characterId": _clean_optional_text(character_id) or None, "model": safe_model}
    else:
        query = """
        mutation UnrealMCPCreateVideoToMotion($file: Upload!, $motionName: String!, $characterId: String) {
          create_video_to_motion(file: $file, motion_name: $motionName, character_id: $characterId) {
            job {
              id
              status
              result
            }
          }
        }
        """
        variables = {"file": None, "motionName": motion_name, "characterId": _clean_optional_text(character_id) or None}
    response = _uthana_graphql_multipart_upload(
        query=query,
        variables=variables,
        file_variable="file",
        file_path=Path(video_file),
        timeout_s=timeout_s,
    )
    data = response.get("body", {}).get("data", {})
    created = data.get("create_video_to_motion") if isinstance(data, dict) else {}
    job = created.get("job") if isinstance(created, dict) else {}
    job = job if isinstance(job, dict) else {}
    job_id = _clean_optional_text(str(job.get("id", "")))
    if not job_id:
        raise RuntimeError("Uthana create_video_to_motion response did not include job.id")
    return {
        "job": job,
        "job_id": job_id,
        "job_status": job.get("status", ""),
        "http_status": response.get("http_status", 0),
    }


def _uthana_get_job(job_id: str, timeout_s: int = 30) -> Dict[str, Any]:
    safe_job_id = _clean_optional_text(job_id)
    if not safe_job_id:
        raise ValueError("job_id is required")
    query = """
    query UnrealMCPUthanaJob($jobId: String!) {
      job(job_id: $jobId) {
        id
        status
        result
      }
    }
    """
    response = _uthana_graphql_request(query, {"jobId": safe_job_id}, timeout_s=timeout_s)
    data = response.get("body", {}).get("data", {})
    job = data.get("job") if isinstance(data, dict) else {}
    job = job if isinstance(job, dict) else {}
    if not job:
        raise RuntimeError(f"Uthana job not found or not accessible: {safe_job_id}")
    result = job.get("result") if isinstance(job.get("result"), dict) else {}
    nested_result = result.get("result") if isinstance(result.get("result"), dict) else {}
    motion_id = _clean_optional_text(str(nested_result.get("id", ""))) if nested_result else ""
    if not motion_id:
        motion_id = _clean_optional_text(str(result.get("id", "")))
    return {
        "job": job,
        "job_id": safe_job_id,
        "job_status": job.get("status", ""),
        "motion_id": motion_id,
        "http_status": response.get("http_status", 0),
    }


def _uthana_get_motion(motion_id: str, timeout_s: int = 30) -> Dict[str, Any]:
    safe_motion_id = _clean_optional_text(motion_id)
    if not safe_motion_id:
        raise ValueError("motion_id is required")
    query = """
    query UnrealMCPUthanaMotion($id: String!) {
      motion(id: $id) {
        id
        name
        org_id
        tags
        assets {
          id
          filename
          mimetype
          type
          size
        }
        created
        updated
        deleted
      }
    }
    """
    response = _uthana_graphql_request(query, {"id": safe_motion_id}, timeout_s=timeout_s)
    data = response.get("body", {}).get("data", {})
    motion = data.get("motion") if isinstance(data, dict) else {}
    motion = motion if isinstance(motion, dict) else {}
    if not motion:
        raise RuntimeError(f"Uthana motion not found or not accessible: {safe_motion_id}")
    return {"motion": motion, "http_status": response.get("http_status", 0)}


def _uthana_check_motion_download_allowed(character_id: str, motion_id: str, timeout_s: int = 30) -> Dict[str, Any]:
    safe_character_id = _clean_optional_text(character_id)
    safe_motion_id = _clean_optional_text(motion_id)
    if not safe_character_id:
        raise ValueError("character_id is required")
    if not safe_motion_id:
        raise ValueError("motion_id is required")
    query = """
    query UnrealMCPUthanaMotionDownloadAllowed($characterId: String!, $motionId: String!) {
      motion_download_allowed(character_id: $characterId, motion_id: $motionId) {
        allowed
        reason
      }
    }
    """
    response = _uthana_graphql_request(query, {"characterId": safe_character_id, "motionId": safe_motion_id}, timeout_s=timeout_s)
    data = response.get("body", {}).get("data", {})
    allowed = data.get("motion_download_allowed") if isinstance(data, dict) else {}
    allowed = allowed if isinstance(allowed, dict) else {}
    return {
        "allowed": bool(allowed.get("allowed")),
        "reason": str(allowed.get("reason") or ""),
        "http_status": response.get("http_status", 0),
    }


def _default_uthana_download_folder(motion_id: str) -> Path:
    return _CHAT_DIR / "uthana_downloads" / _safe_name(motion_id, "uthana_motion")


def _uthana_motion_download_url(
    *,
    character_id: str,
    motion_id: str,
    output_format: str,
    filename: str,
    fps: int,
    no_mesh: str,
    in_place: bool,
    torso_only: bool,
    speed_multiplier: float,
    motion_only: bool,
) -> str:
    route = "animation" if motion_only and output_format == "glb" else "file"
    quoted_character = urllib.parse.quote(character_id, safe="")
    quoted_motion = urllib.parse.quote(motion_id, safe="")
    quoted_filename = urllib.parse.quote(filename, safe="")
    url = f"{_UTHANA_DOWNLOAD_BASE_URL}/motion/{route}/motion_viewer/{quoted_character}/{quoted_motion}/{output_format}/{quoted_filename}"
    query_params: Dict[str, str] = {}
    if fps:
        query_params["fps"] = str(fps)
    if no_mesh:
        query_params["no_mesh"] = no_mesh
    if in_place:
        query_params["in_place"] = "true"
    if torso_only:
        query_params["torso_only"] = "true"
    if speed_multiplier != 1.0:
        query_params["speed_multiplier"] = f"{speed_multiplier:.3f}".rstrip("0").rstrip(".")
    if query_params:
        url = f"{url}?{urllib.parse.urlencode(query_params)}"
    return url


def _download_uthana_motion_file(url: str, target_path: Path, timeout_s: int = 180) -> Dict[str, Any]:
    api_key = _get_uthana_api_key()
    if not api_key:
        raise RuntimeError("UTHANA_API_KEY is not configured in the environment or Saved/MCPChat/secrets.json")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers=_uthana_headers(api_key, content_type=""), method="GET")
    with urllib.request.urlopen(request, timeout=max(1, int(timeout_s))) as response:
        target_path.write_bytes(response.read())
        return {
            "path": str(target_path),
            "bytes": target_path.stat().st_size,
            "http_status": response.status,
        }


def _bridge_ping_ready() -> Dict[str, Any]:
    raw = _send("ping", {})
    failed = raw.get("success") is False or raw.get("status") == "error" or bool(raw.get("error"))
    message = raw.get("message") or raw.get("error") or ""
    return {
        "ready": not failed and str(message).lower() == "pong",
        "raw": raw,
        "message": message,
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


def _tripo_get_credit_balance(timeout_s: int = 30) -> Dict[str, Any]:
    response = _tripo_json_request("GET", "/user/balance", timeout_s=timeout_s)
    body = response.get("body", {})
    if response.get("http_status", 0) >= 400 or body.get("code", 0) != 0:
        message = body.get("message") or body.get("suggestion") or "Tripo credit balance query failed"
        raise RuntimeError(message)
    data = body.get("data", {})
    if not isinstance(data, dict):
        data = {}
    return {
        "balance": data.get("balance"),
        "frozen": data.get("frozen"),
        "response": body,
        "trace_id": response.get("trace_id", ""),
        "http_status": response.get("http_status", 0),
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
    return _TRIPO_PROVIDER.estimate_credits(task_type, payload)


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


def _uthana_usage_guard(*, estimated_seconds: int, confirm_usage: bool, operation: str) -> Dict[str, Any]:
    safe_estimate = max(0, _safe_int(estimated_seconds, 0))
    confirm_required = safe_estimate > 0 and not confirm_usage
    return {
        "provider": "uthana",
        "operation": operation,
        "estimated_motion_seconds": safe_estimate,
        "confirm_required": confirm_required,
        "approved": not confirm_required,
        "quota_evidence_required": True,
        "spend_required": safe_estimate > 0,
    }


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


def _import_generated_static_mesh(
    *,
    file_path: str,
    content_path: str,
    asset_name: str,
    create_material_instance: bool,
    create_blueprint: bool,
    overwrite_existing: bool,
) -> Dict[str, Any]:
    from tools.asset_import_tools import SUPPORTED_STATIC_MESH_EXTS, _get_substrate

    source = Path(file_path)
    if source.suffix.lower() not in SUPPORTED_STATIC_MESH_EXTS:
        raise ValueError(f"Unsupported generated mesh extension for import: {source.suffix}")

    safe_asset_name = _safe_name(asset_name or source.stem, "GeneratedAsset")
    safe_content_path = _normalize_content_folder(content_path)
    user_code = f"""
import json
import os
import unreal

file_path = {str(source)!r}
destination_path = {safe_content_path!r}.rstrip("/") or "/Game/Generated"
asset_name = {safe_asset_name!r}
create_material_instance = {bool(create_material_instance)!r}
create_blueprint = {bool(create_blueprint)!r}
overwrite_existing = {bool(overwrite_existing)!r}

unreal.EditorAssetLibrary.make_directory(destination_path)
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

with unreal.ScopedSlowTask(100, "MCP D.4 Tripo import: " + asset_name) as slow:
    slow.make_dialog(True)
    slow.enter_progress_frame(35, "Importing generated mesh")
    with unreal.ScopedEditorTransaction("MCP D.4 Tripo import: " + asset_name):
        task = unreal.AssetImportTask()
        task.filename = file_path
        task.destination_path = destination_path
        task.destination_name = asset_name
        task.automated = True
        task.save = True
        task.replace_existing = overwrite_existing

        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".fbx", ".obj"):
            options = unreal.FbxImportUI()
            options.set_editor_property("import_mesh", True)
            options.set_editor_property("import_as_skeletal", False)
            options.set_editor_property("import_materials", True)
            options.set_editor_property("import_textures", True)
            smd = options.static_mesh_import_data
            smd.set_editor_property("combine_meshes", True)
            smd.set_editor_property("generate_lightmap_u_vs", True)
            smd.set_editor_property("auto_generate_collision", True)
            task.set_editor_property("options", options)

        asset_tools.import_asset_tasks([task])
        imported = list(task.get_editor_property("imported_object_paths") or [])
        if not imported:
            raise RuntimeError("Generated mesh import returned no asset paths for: " + file_path)

        asset_path_full = imported[0]
        asset_path_clean = asset_path_full.split(".")[0] if "." in asset_path_full else asset_path_full
        mesh = unreal.load_asset(asset_path_full)
        if not (mesh and isinstance(mesh, unreal.StaticMesh)):
            _warnings.append("Imported primary asset did not load as StaticMesh; verify in Content Browser")

        material_instance_path = ""
        if create_material_instance and mesh and isinstance(mesh, unreal.StaticMesh):
            slow.enter_progress_frame(25, "Creating material instance")
            base_material = None
            static_materials = list(mesh.get_editor_property("static_materials") or [])
            if static_materials:
                base_material = static_materials[0].material_interface
            if base_material:
                mi_name = "MI_" + asset_name
                mi_package = destination_path + "/" + mi_name
                if overwrite_existing and unreal.EditorAssetLibrary.does_asset_exist(mi_package):
                    unreal.EditorAssetLibrary.delete_asset(mi_package)
                mi = unreal.load_asset(mi_package + "." + mi_name)
                if not mi:
                    factory = unreal.MaterialInstanceConstantFactoryNew()
                    mi = asset_tools.create_asset(mi_name, destination_path, unreal.MaterialInstanceConstant, factory)
                if mi:
                    mi.set_editor_property("parent", base_material)
                    mesh.set_material(0, mi)
                    unreal.EditorAssetLibrary.save_loaded_asset(mi)
                    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
                    material_instance_path = mi_package
                else:
                    _warnings.append("Material instance creation returned no asset")
            else:
                _warnings.append("No imported base material found; material instance creation skipped")

        blueprint_path = ""
        if create_blueprint:
            slow.enter_progress_frame(25, "Creating Blueprint shell")
            bp_name = "BP_" + asset_name
            bp_package = destination_path + "/" + bp_name
            if overwrite_existing and unreal.EditorAssetLibrary.does_asset_exist(bp_package):
                unreal.EditorAssetLibrary.delete_asset(bp_package)
            bp = unreal.load_asset(bp_package + "." + bp_name)
            if not bp:
                factory = unreal.BlueprintFactory()
                factory.set_editor_property("parent_class", unreal.Actor)
                bp = asset_tools.create_asset(bp_name, destination_path, unreal.Blueprint, factory)
            if bp:
                unreal.EditorAssetLibrary.save_loaded_asset(bp)
                blueprint_path = bp_package
                _warnings.append("Created Actor Blueprint shell; add a StaticMeshComponent before gameplay use")
            else:
                _warnings.append("Blueprint shell creation returned no asset")

        slow.enter_progress_frame(15, "Saving generated import outputs")
        _result["asset_path"] = asset_path_clean
        _result["asset_type"] = "StaticMesh"
        _result["imported_object_paths"] = imported
        _result["material_instance"] = material_instance_path
        _result["blueprint"] = blueprint_path
        _result["content_path"] = destination_path
        _result["asset_name"] = asset_name

        saved_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
        handoff_dir = os.path.join(saved_dir, "MCPChat")
        os.makedirs(handoff_dir, exist_ok=True)
        handoff_path = os.path.join(handoff_dir, "generative_workspace_preview.json")
        handoff = {{
            "schema": "unreal_mcp_generative_workspace_preview.v1",
            "provider": "tripo",
            "preview_asset_path": asset_path_clean,
            "asset_path": asset_path_clean,
            "asset_type": "StaticMesh",
            "content_path": destination_path,
            "asset_name": asset_name,
            "imported_object_paths": imported,
        }}
        with open(handoff_path, "w", encoding="utf-8") as handoff_file:
            json.dump(handoff, handoff_file, indent=2, sort_keys=True)
        _result["workspace_preview_handoff_path"] = handoff_path
"""
    exec_structured = _get_substrate()
    return exec_structured(user_code, "gen_tripo_import_to_project")


def _import_uthana_animation_fbx(
    *,
    file_path: str,
    content_path: str,
    skeleton: str,
    import_materials: bool,
) -> Dict[str, Any]:
    from tools.exec_substrate import exec_python_structured

    user_code = f"""
import os
import unreal

file_path = {file_path!r}
destination_path = {content_path!r}
skeleton_path = {skeleton!r}
do_import_materials = {import_materials!r}

asset_name = os.path.splitext(os.path.basename(file_path))[0]
dest = destination_path.rstrip("/") or "/Game/Generated/Animations"
unreal.EditorAssetLibrary.make_directory(dest)

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
options = unreal.FbxImportUI()
options.set_editor_property("import_mesh", True)
options.set_editor_property("import_as_skeletal", True)
options.set_editor_property("import_animations", True)
options.set_editor_property("import_materials", do_import_materials)

reused_skeleton = False
if skeleton_path:
    skel = unreal.EditorAssetLibrary.load_asset(skeleton_path)
    if skel and isinstance(skel, unreal.Skeleton):
        options.set_editor_property("skeleton", skel)
        reused_skeleton = True
    else:
        _warnings.append(f"Skeleton not found at {{skeleton_path}}; Unreal will import using the FBX skeleton")

task = unreal.AssetImportTask()
task.filename = file_path
task.destination_path = dest
task.destination_name = asset_name
task.automated = True
task.save = True
task.replace_existing = True
task.set_editor_property("options", options)

asset_tools.import_asset_tasks([task])

imported = list(task.get_editor_property("imported_object_paths") or [])
if not imported:
    raise RuntimeError("Import returned no paths. Verify the FBX exists on the UE host: " + file_path)

anim_sequences = []
skeletal_meshes = []
skeletons = []
for path in imported:
    asset = unreal.load_asset(path)
    clean_path = path.split(".")[0] if "." in path else path
    if asset and isinstance(asset, unreal.AnimSequence):
        anim_sequences.append(clean_path)
    elif asset and isinstance(asset, unreal.SkeletalMesh):
        skeletal_meshes.append(clean_path)
        skel_obj = asset.get_editor_property("skeleton")
        if skel_obj:
            skeletons.append(skel_obj.get_path_name().split(".")[0])
    elif asset and isinstance(asset, unreal.Skeleton):
        skeletons.append(clean_path)

_result["asset_path"] = anim_sequences[0] if anim_sequences else (skeletal_meshes[0] if skeletal_meshes else imported[0].split(".")[0])
_result["asset_type"] = "AnimationSequence" if anim_sequences else "SkeletalMesh"
_result["animation_sequence_paths"] = anim_sequences
_result["skeletal_mesh_paths"] = skeletal_meshes
_result["skeleton_paths"] = sorted(set(skeletons))
_result["imported_object_paths"] = imported
_result["reused_skeleton"] = reused_skeleton
_result["content_path"] = dest
_result["asset_name"] = asset_name
"""
    return exec_python_structured(user_code, "gen_uthana_import_animation_to_project")



def _resolve_provider_api_key(env_name: str, secret_name: str) -> Dict[str, Any]:
    env_key = os.environ.get(env_name, "").strip()
    if env_key:
        return {
            "configured": True,
            "source": f"env:{env_name}",
            "masked": f"{env_key[:4]}...{env_key[-4:]}" if len(env_key) >= 8 else "configured",
        }

    secrets = _read_json_file(_SECRETS_PATH)
    secrets_key = str(secrets.get(env_name) or secrets.get(secret_name) or "").strip()
    if secrets_key:
        return {
            "configured": True,
            "source": "Saved/MCPChat/secrets.json",
            "masked": f"{secrets_key[:4]}...{secrets_key[-4:]}" if len(secrets_key) >= 8 else "configured",
        }

    return {"configured": False, "source": "missing", "masked": ""}


def _resolve_tripo_api_key() -> Dict[str, Any]:
    return _resolve_provider_api_key("TRIPO_API_KEY", "tripo_api_key")


def _save_generative_settings(
    *,
    tripo_api_key: str,
    uthana_api_key: str,
    store_api_key: bool,
    store_uthana_api_key: bool,
    clear_stored_api_key: bool,
    clear_stored_uthana_api_key: bool,
    default_model_version: str,
    default_texture_quality: str,
    output_folder: str,
    animation_output_folder: str,
    uthana_default_character_id: str,
    session_credit_budget: int,
) -> Dict[str, Any]:
    settings = _load_generative_settings()
    settings.update({
        "provider": "tripo",
        "animation_provider": "uthana",
        "default_model_version": (default_model_version or "tripo-default").strip() or "tripo-default",
        "default_texture_quality": (default_texture_quality or "standard").strip() or "standard",
        "output_folder": _normalize_content_folder(output_folder),
        "animation_output_folder": _normalize_content_folder(animation_output_folder or "/Game/Generated/Animations"),
        "uthana_default_character_id": (uthana_default_character_id or "cXi2eAP19XwQ").strip() or "cXi2eAP19XwQ",
        "session_credit_budget": max(0, _safe_int(session_credit_budget, 1000)),
    })
    _write_json_file(_SETTINGS_PATH, settings)

    secrets = _read_json_file(_SECRETS_PATH)
    if clear_stored_api_key:
        secrets.pop("TRIPO_API_KEY", None)
        secrets.pop("tripo_api_key", None)
    if clear_stored_uthana_api_key:
        secrets.pop("UTHANA_API_KEY", None)
        secrets.pop("uthana_api_key", None)
    if store_api_key and tripo_api_key.strip():
        secrets["TRIPO_API_KEY"] = tripo_api_key.strip()
    if store_uthana_api_key and uthana_api_key.strip():
        secrets["UTHANA_API_KEY"] = uthana_api_key.strip()
    if secrets:
        _write_json_file(_SECRETS_PATH, secrets)
    elif _SECRETS_PATH.exists():
        _SECRETS_PATH.unlink()
    return settings


def _provider_config_outputs() -> Dict[str, Any]:
    settings = _load_generative_settings()
    key_state = _resolve_tripo_api_key()
    uthana_key_state = _resolve_provider_api_key("UTHANA_API_KEY", "uthana_api_key")
    return {
        "provider": "tripo",
        "animation_provider": settings.get("animation_provider", "uthana"),
        "api_key_configured": key_state["configured"],
        "api_key_source": key_state["source"],
        "api_key_masked": key_state["masked"],
        "uthana_api_key_configured": uthana_key_state["configured"],
        "uthana_api_key_source": uthana_key_state["source"],
        "uthana_api_key_masked": uthana_key_state["masked"],
        "default_model_version": settings["default_model_version"],
        "default_texture_quality": settings["default_texture_quality"],
        "output_folder": settings["output_folder"],
        "animation_output_folder": settings.get("animation_output_folder", "/Game/Generated/Animations"),
        "uthana_default_character_id": settings.get("uthana_default_character_id", "cXi2eAP19XwQ"),
        "session_credit_budget": settings["session_credit_budget"],
        "credit_usage_by_session": settings["credit_usage_by_session"],
        "settings_path": str(_SETTINGS_PATH),
        "secrets_path": str(_SECRETS_PATH),
        "network_required": False,
        "spend_confirmation_required": True,
    }


def _provider_scaffold() -> List[Dict[str, Any]]:
    config = _provider_config_outputs()
    return [provider.describe(config) for provider in _PROVIDERS.list()]


def _playable_slice_readiness_plan(brief: str, content_path: str) -> Dict[str, Any]:
    safe_brief = _clean_optional_text(brief) or "third-person dungeon-crawler demo with a hero, two props, and an enemy"
    try:
        from skills.playable_slice.skill import build_playable_slice_plan, validate_playable_slice_plan

        plan = build_playable_slice_plan(safe_brief, _normalize_content_folder(content_path))
        validation_errors = validate_playable_slice_plan(plan)
    except Exception as exc:
        return {
            "brief": safe_brief,
            "plan": {},
            "validation_errors": [str(exc)],
            "estimated_asset_credits": 0,
            "asset_count": 0,
        }

    settings = _load_generative_settings()
    model_version = _clean_model_version(str(settings.get("default_model_version", "")))
    estimated_credits = 0
    for asset in plan.get("assets", []):
        if not isinstance(asset, dict):
            continue
        payload: Dict[str, Any] = {
            "type": "text_to_model",
            "prompt": asset.get("prompt", ""),
            "texture": bool(asset.get("texture", True)),
            "pbr": bool(asset.get("pbr", True)),
            "texture_quality": asset.get("texture_quality", settings.get("default_texture_quality", "standard")),
            "face_limit": int(asset.get("face_limit", 12000) or 12000),
        }
        if model_version:
            payload["model_version"] = model_version
        estimated_credits += _estimate_tripo_credits("text_to_model", payload)

    return {
        "brief": safe_brief,
        "plan": plan,
        "validation_errors": validation_errors,
        "estimated_asset_credits": estimated_credits,
        "asset_count": len(plan.get("assets", [])) if isinstance(plan.get("assets"), list) else 0,
    }


def _mechanic_animation_readiness_plan(mechanic_brief: str, content_path: str) -> Dict[str, Any]:
    safe_brief = _clean_optional_text(mechanic_brief)
    if not safe_brief:
        return {
            "brief": "",
            "plan": {},
            "validation_errors": [],
            "prompt_count": 0,
            "prompts": [],
            "estimated_motion_seconds": 0,
            "requires_animation_generation": False,
        }
    try:
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        result = skill_plan_gameplay_mechanic(
            safe_brief,
            content_path=_normalize_content_folder(content_path),
            include_generated_assets=True,
        )
        plan = result.get("outputs", {}).get("plan", {}) if isinstance(result, dict) else {}
        prompts = plan.get("generated_animation_prompts", []) if isinstance(plan.get("generated_animation_prompts"), list) else []
        estimated_seconds = sum(int(prompt.get("estimated_seconds", 0) or 0) for prompt in prompts if isinstance(prompt, dict))
        errors = result.get("errors", []) if isinstance(result, dict) and isinstance(result.get("errors"), list) else []
        return {
            "brief": safe_brief,
            "plan": plan,
            "validation_errors": errors,
            "prompt_count": len(prompts),
            "prompts": prompts,
            "estimated_motion_seconds": estimated_seconds,
            "requires_animation_generation": bool(prompts),
        }
    except Exception as exc:
        return {
            "brief": safe_brief,
            "plan": {},
            "validation_errors": [str(exc)],
            "prompt_count": 0,
            "prompts": [],
            "estimated_motion_seconds": 0,
            "requires_animation_generation": False,
        }


def _workspace_files_ready() -> Dict[str, Any]:
    files = [
        _REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp",
        _REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "UnrealMCPEditorModule.cpp",
        _REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Public" / "TripoWorkspaceSession.h",
    ]
    missing = [str(path) for path in files if not path.exists()]
    return {
        "ready": not missing,
        "checked_files": [str(path) for path in files],
        "missing_files": missing,
    }


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
                },
                {
                    "tool": "gen_tripo_import_to_project",
                    "native_route": "gen_prepare_import_manifest",
                    "status": "live",
                    "purpose": "Download a successful Tripo task result, import the StaticMesh, and return viewport evidence.",
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
    async def gen_compile_ide_companion_readiness(
        ctx: Context,
        brief: str = "third-person dungeon-crawler demo with a hero, two props, and an enemy",
        mechanic_brief: str = "",
        content_path: str = "/Game/Generated/PlayableSlice",
        session_name: str = "ide-companion",
        include_api_wallet: bool = False,
        include_animation_account: bool = False,
        include_unreal_bridge: bool = False,
        timeout_s: int = 30,
    ) -> str:
        """Compile no-spend readiness for generated assets plus playable-slice development.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#ide-companion-readiness
        Example:
            gen_compile_ide_companion_readiness(brief="third-person dungeon demo", include_api_wallet=True)"""
        t0 = time.monotonic()
        safe_timeout = max(1, min(_safe_int(timeout_s, 30), 120))
        inputs = {
            "brief": brief,
            "mechanic_brief": mechanic_brief,
            "content_path": content_path,
            "session_name": session_name,
            "include_api_wallet": include_api_wallet,
            "include_animation_account": include_animation_account,
            "include_unreal_bridge": include_unreal_bridge,
            "timeout_s": safe_timeout,
        }
        config = _provider_config_outputs()
        providers = _provider_scaffold()
        plan_state = _playable_slice_readiness_plan(brief, content_path)
        animation_state = _mechanic_animation_readiness_plan(mechanic_brief, content_path)
        credit_guard = _check_and_reserve_credit_budget(
            estimated_credits=plan_state["estimated_asset_credits"],
            session_name=session_name,
            operation="skill_generate_playable_slice",
            confirm_spend=False,
            reserve_credits=False,
        )
        workspace = _workspace_files_ready()

        optional_checks: Dict[str, Any] = {
            "api_wallet": {"checked": False, "ready": None, "detail": "skipped"},
            "uthana_account": {"checked": False, "ready": None, "detail": "skipped"},
            "unreal_bridge": {"checked": False, "ready": None, "detail": "skipped"},
        }
        if include_api_wallet:
            try:
                balance = await asyncio.to_thread(_tripo_get_credit_balance, timeout_s=safe_timeout)
                balance_value = _safe_int(balance.get("balance"), 0)
                optional_checks["api_wallet"] = {
                    "checked": True,
                    "ready": balance_value > 0,
                    "detail": f"{balance_value} API wallet credits available",
                    "balance": balance.get("balance"),
                    "frozen": balance.get("frozen"),
                    "trace_id": balance.get("trace_id", ""),
                    "http_status": balance.get("http_status", 0),
                    "spend_required": False,
                }
            except Exception as exc:
                optional_checks["api_wallet"] = {
                    "checked": True,
                    "ready": False,
                    "detail": str(exc),
                    "spend_required": False,
                }
        if include_animation_account:
            if not animation_state["requires_animation_generation"]:
                optional_checks["uthana_account"] = {
                    "checked": False,
                    "ready": None,
                    "detail": "not required for current mechanic_brief",
                    "spend_required": False,
                }
            else:
                try:
                    account = await asyncio.to_thread(_uthana_get_account, timeout_s=safe_timeout)
                    org = account.get("org") if isinstance(account.get("org"), dict) else {}
                    remaining = org.get("motion_download_secs_per_month_remaining")
                    remaining_value = _safe_int(remaining, 0)
                    optional_checks["uthana_account"] = {
                        "checked": True,
                        "ready": remaining_value > 0,
                        "detail": f"{remaining_value} Uthana motion download second(s) remaining",
                        "motion_download_secs_per_month": org.get("motion_download_secs_per_month"),
                        "motion_download_secs_per_month_remaining": remaining,
                        "characters_allowed_remaining": org.get("characters_allowed_remaining"),
                        "http_status": account.get("http_status", 0),
                        "spend_required": False,
                    }
                except Exception as exc:
                    optional_checks["uthana_account"] = {
                        "checked": True,
                        "ready": False,
                        "detail": str(exc),
                        "spend_required": False,
                    }
        if include_unreal_bridge:
            raw = await asyncio.to_thread(_send, "ping", {})
            failed = raw.get("success") is False or raw.get("status") == "error" or bool(raw.get("error"))
            optional_checks["unreal_bridge"] = {
                "checked": True,
                "ready": not failed,
                "detail": raw.get("message") or raw.get("error") or ("bridge responded" if not failed else "bridge check failed"),
                "response": raw,
            }

        gates = [
            _readiness_gate("tripo_provider_registered", any(provider.get("provider") == "tripo" for provider in providers), "Tripo provider scaffold is registered"),
            _readiness_gate("api_key_configured", bool(config.get("api_key_configured")), str(config.get("api_key_source", "missing"))),
            _readiness_gate("playable_slice_plan_valid", not plan_state["validation_errors"] and plan_state["asset_count"] >= 4, f"{plan_state['asset_count']} planned asset(s)"),
            _readiness_gate("credit_budget_within_session", bool(credit_guard.get("within_budget")), f"{credit_guard.get('estimated_credits')} estimated credits, {credit_guard.get('remaining')} remaining in session budget"),
            _readiness_gate("spend_confirmation_enforced", bool(credit_guard.get("confirm_required")) and not credit_guard.get("approved"), "paid Tripo submission is blocked until confirm_spend=True"),
            _readiness_gate("import_handoff_available", True, "gen_tripo_import_to_project and gen_prepare_import_manifest are registered in this module"),
            _readiness_gate("editor_workspace_files_present", bool(workspace.get("ready")), "Tripo Workspace and chat dock source files are present" if workspace.get("ready") else "Tripo Workspace source files are missing"),
        ]
        if include_api_wallet:
            wallet = optional_checks["api_wallet"]
            gates.append(_readiness_gate("api_wallet_has_credits", bool(wallet.get("ready")), wallet.get("detail", "")))
        if animation_state["requires_animation_generation"]:
            gates.extend([
                _readiness_gate("uthana_provider_registered", any(provider.get("provider") == "uthana" for provider in providers), "Uthana provider scaffold is registered"),
                _readiness_gate("animation_provider_key_configured", bool(config.get("uthana_api_key_configured")), str(config.get("uthana_api_key_source", "missing"))),
                _readiness_gate("animation_usage_confirmation_enforced", True, "Uthana motion submission remains blocked until confirm_usage=True"),
            ])
            if include_animation_account:
                uthana_account = optional_checks["uthana_account"]
                gates.append(_readiness_gate("uthana_motion_allowance_available", bool(uthana_account.get("ready")), uthana_account.get("detail", "")))
        if include_unreal_bridge:
            bridge = optional_checks["unreal_bridge"]
            gates.append(_readiness_gate("unreal_bridge_reachable", bool(bridge.get("ready")), bridge.get("detail", "")))

        next_actions = []
        if not config.get("api_key_configured"):
            next_actions.append({"tool": "gen_save_provider_config", "reason": "Store a Tripo API key or set TRIPO_API_KEY before paid generation."})
        if plan_state["validation_errors"]:
            next_actions.append({"tool": "skill_generate_playable_slice", "reason": "Repair the playable-slice plan validation errors."})
        if animation_state["validation_errors"]:
            next_actions.append({"tool": "skill_plan_gameplay_mechanic", "reason": "Repair the mechanic plan validation errors before generated animation readiness."})
        if not credit_guard.get("within_budget"):
            next_actions.append({"tool": "gen_save_provider_config", "reason": "Raise the session_credit_budget or reduce the planned asset count/quality."})
        if include_api_wallet and not optional_checks["api_wallet"].get("ready"):
            next_actions.append({"tool": "Tripo API wallet", "reason": "Fund the API wallet before submitting paid generation tasks."})
        if animation_state["requires_animation_generation"] and not config.get("uthana_api_key_configured"):
            next_actions.append({"tool": "gen_save_provider_config", "reason": "Store a Uthana API key or set UTHANA_API_KEY before paid animation generation."})
        if animation_state["requires_animation_generation"] and include_animation_account and not optional_checks["uthana_account"].get("ready"):
            next_actions.append({"tool": "gen_uthana_get_account", "reason": "Confirm Uthana org motion allowance before generated animation usage."})
        if include_unreal_bridge and not optional_checks["unreal_bridge"].get("ready"):
            next_actions.append({"tool": "scripts/bridge_ping.py", "reason": "Start Unreal Editor with the UnrealMCP plugin loaded, then rerun the bridge check."})
        if animation_state["requires_animation_generation"] and config.get("uthana_api_key_configured"):
            next_actions.append({"tool": "gen_uthana_text_to_motion", "reason": "Submit planned Uthana motion prompts only after allowance review and confirm_usage=True."})
        if not next_actions:
            next_actions.append({"tool": "skill_generate_playable_slice", "reason": "Run mode='submit_assets' with confirm_spend=True after user approval."})

        blocking_gates = [gate for gate in gates if not gate["ready"]]
        ready = not blocking_gates
        warnings = [] if ready else ["IDE companion readiness has unmet gates; inspect outputs.gates and outputs.next_actions."]
        return _result_json(
            success=True,
            stage="gen_compile_ide_companion_readiness",
            message="Compiled Unreal MCP IDE companion readiness",
            inputs=inputs,
            outputs={
                "schema": "unreal_mcp_ide_companion_readiness.v1",
                "ready": ready,
                "provider_config": config,
                "providers": providers,
                "playable_slice": plan_state,
                "generated_animation": animation_state,
                "credit_guard": credit_guard,
                "workspace": workspace,
                "optional_checks": optional_checks,
                "gates": gates,
                "blocking_gates": blocking_gates,
                "next_actions": next_actions,
                "network_required": bool(include_api_wallet or (include_animation_account and animation_state["requires_animation_generation"])),
                "bridge_required": bool(include_unreal_bridge),
                "spend_required": False,
            },
            warnings=warnings,
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
            warnings=[
                warning for warning in (
                    None if outputs["api_key_configured"] else "TRIPO_API_KEY is not configured in the environment or Saved/MCPChat/secrets.json",
                    None if outputs["uthana_api_key_configured"] else "UTHANA_API_KEY is not configured in the environment or Saved/MCPChat/secrets.json",
                )
                if warning
            ],
            t0=t0,
        )

    @mcp.tool()
    async def gen_tripo_get_credit_balance(ctx: Context, include_raw: bool = False, timeout_s: int = 30) -> str:
        """Fetch the authenticated Tripo API wallet credit balance.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#api-wallet-balance
        Example:
            gen_tripo_get_credit_balance()"""
        t0 = time.monotonic()
        safe_timeout = max(1, min(_safe_int(timeout_s, 30), 120))
        inputs = {
            "provider": "tripo",
            "include_raw": include_raw,
            "timeout_s": safe_timeout,
        }
        try:
            balance = await asyncio.to_thread(_tripo_get_credit_balance, timeout_s=safe_timeout)
            wallet = {
                "balance": balance.get("balance"),
                "frozen": balance.get("frozen"),
            }
            outputs: Dict[str, Any] = {
                "provider": "tripo",
                "api_wallet": wallet,
                "balance": wallet["balance"],
                "frozen": wallet["frozen"],
                "trace_id": balance.get("trace_id", ""),
                "http_status": balance.get("http_status", 0),
                "network_required": True,
                "spend_required": False,
            }
            if include_raw:
                outputs["raw_response"] = balance.get("response", {})
            return _result_json(
                success=True,
                stage="gen_tripo_get_credit_balance",
                message=f"Tripo API wallet balance: {wallet['balance']} credits, frozen: {wallet['frozen']}",
                inputs=inputs,
                outputs=outputs,
                warnings=["Tripo webapp credits and API wallet credits are separate balances; this reports the API wallet only."],
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_tripo_get_credit_balance",
                message=str(exc),
                inputs=inputs,
                outputs={"provider": "tripo", "network_required": True, "spend_required": False},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_save_provider_config(
        ctx: Context,
        tripo_api_key: str = "",
        uthana_api_key: str = "",
        store_api_key: bool = False,
        store_uthana_api_key: bool = False,
        clear_stored_api_key: bool = False,
        clear_stored_uthana_api_key: bool = False,
        default_model_version: str = "tripo-default",
        default_texture_quality: str = "standard",
        output_folder: str = "/Game/Generated",
        animation_output_folder: str = "/Game/Generated/Animations",
        uthana_default_character_id: str = "cXi2eAP19XwQ",
        session_credit_budget: int = 1000,
    ) -> str:
        """Save Tripo/Uthana defaults and optionally store/clear local API keys.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#config-and-auth
        Example:
            gen_save_provider_config(default_model_version="tripo-default", output_folder="/Game/Generated", session_credit_budget=750)"""
        t0 = time.monotonic()
        inputs = {
            "store_api_key": store_api_key,
            "store_uthana_api_key": store_uthana_api_key,
            "clear_stored_api_key": clear_stored_api_key,
            "clear_stored_uthana_api_key": clear_stored_uthana_api_key,
            "default_model_version": default_model_version,
            "default_texture_quality": default_texture_quality,
            "output_folder": output_folder,
            "animation_output_folder": animation_output_folder,
            "uthana_default_character_id": uthana_default_character_id,
            "session_credit_budget": session_credit_budget,
            "tripo_api_key_supplied": bool(tripo_api_key.strip()),
            "uthana_api_key_supplied": bool(uthana_api_key.strip()),
        }
        settings = _save_generative_settings(
            tripo_api_key=tripo_api_key,
            uthana_api_key=uthana_api_key,
            store_api_key=store_api_key,
            store_uthana_api_key=store_uthana_api_key,
            clear_stored_api_key=clear_stored_api_key,
            clear_stored_uthana_api_key=clear_stored_uthana_api_key,
            default_model_version=default_model_version,
            default_texture_quality=default_texture_quality,
            output_folder=output_folder,
            animation_output_folder=animation_output_folder,
            uthana_default_character_id=uthana_default_character_id,
            session_credit_budget=session_credit_budget,
        )
        outputs = _provider_config_outputs()
        outputs["saved_settings"] = {
            "default_model_version": settings["default_model_version"],
            "default_texture_quality": settings["default_texture_quality"],
            "output_folder": settings["output_folder"],
            "animation_output_folder": settings["animation_output_folder"],
            "uthana_default_character_id": settings["uthana_default_character_id"],
            "session_credit_budget": settings["session_credit_budget"],
        }
        warnings = []
        if tripo_api_key and not store_api_key:
            warnings.append("tripo_api_key was supplied but not stored because store_api_key=False")
        if uthana_api_key and not store_uthana_api_key:
            warnings.append("uthana_api_key was supplied but not stored because store_uthana_api_key=False")
        if outputs["api_key_source"].startswith("env:"):
            warnings.append("TRIPO_API_KEY environment variable takes precedence over Saved/MCPChat/secrets.json")
        if outputs["uthana_api_key_source"].startswith("env:"):
            warnings.append("UTHANA_API_KEY environment variable takes precedence over Saved/MCPChat/secrets.json")
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
    async def gen_uthana_get_account(ctx: Context, include_user: bool = False, timeout_s: int = 30) -> str:
        """Fetch Uthana account/org allowance state without exposing the API key.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_get_account()"""
        t0 = time.monotonic()
        safe_timeout = max(1, min(_safe_int(timeout_s, 30), 120))
        inputs = {
            "provider": "uthana",
            "include_user": include_user,
            "timeout_s": safe_timeout,
        }
        try:
            account = await asyncio.to_thread(_uthana_get_account, timeout_s=safe_timeout)
            user = account.get("user") if isinstance(account.get("user"), dict) else {}
            org = account.get("org") if isinstance(account.get("org"), dict) else {}
            safe_user = {
                "id": user.get("id", ""),
                "name": user.get("name", ""),
            }
            if include_user:
                safe_user["email"] = user.get("email", "")
            outputs = {
                "provider": "uthana",
                "user": safe_user,
                "org": org,
                "motion_download_secs_per_month": org.get("motion_download_secs_per_month"),
                "motion_download_secs_per_month_remaining": org.get("motion_download_secs_per_month_remaining"),
                "characters_allowed_remaining": org.get("characters_allowed_remaining"),
                "http_status": account.get("http_status", 0),
                "network_required": True,
                "spend_required": False,
            }
            return _result_json(
                success=True,
                stage="gen_uthana_get_account",
                message="Loaded Uthana account and organization allowance state",
                inputs=inputs,
                outputs=outputs,
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_get_account",
                message=str(exc),
                inputs=inputs,
                outputs={"provider": "uthana", "network_required": True, "spend_required": False},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_create_character(
        ctx: Context,
        local_file: str,
        character_name: str = "",
        auto_rig: bool = True,
        auto_rig_front_facing: bool = True,
        include_fingers: bool = True,
        rerig_target: str = "",
        set_as_default: bool = True,
        session_name: str = "default",
        confirm_usage: bool = False,
        timeout_s: int = 180,
    ) -> str:
        """Upload a Tripo/exported character file to Uthana and create an auto-rigged character target.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_create_character(local_file="C:/Generated/Hero.fbx", character_name="Hero", confirm_usage=True)"""
        t0 = time.monotonic()
        safe_file = _normalize_optional_path_or_url(local_file)
        safe_path = Path(safe_file)
        safe_name = _clean_optional_text(character_name) or _safe_name(safe_path.stem, "UthanaCharacter")
        safe_timeout = max(1, min(_safe_int(timeout_s, 180), 600))
        usage_guard = _uthana_usage_guard(
            estimated_seconds=1,
            confirm_usage=confirm_usage,
            operation="create_character",
        )
        inputs = {
            "provider": "uthana",
            "local_file": safe_file,
            "character_name": safe_name,
            "auto_rig": auto_rig,
            "auto_rig_front_facing": auto_rig_front_facing,
            "include_fingers": include_fingers,
            "rerig_target": rerig_target,
            "set_as_default": set_as_default,
            "session_name": session_name,
            "confirm_usage": confirm_usage,
            "timeout_s": safe_timeout,
        }
        if not safe_file:
            return _result_json(success=False, stage="gen_uthana_create_character", message="local_file is required", inputs=inputs, outputs={"usage_guard": usage_guard}, errors=["local_file is required"], t0=t0)
        if safe_path.suffix.lower() not in {".fbx", ".glb", ".gltf"}:
            return _result_json(
                success=False,
                stage="gen_uthana_create_character",
                message="Unsupported Uthana character format",
                inputs=inputs,
                outputs={"supported_extensions": [".fbx", ".glb", ".gltf"], "usage_guard": usage_guard},
                errors=["local_file must be .fbx, .glb, or .gltf"],
                t0=t0,
            )
        if not safe_path.exists():
            return _result_json(success=False, stage="gen_uthana_create_character", message=f"local_file does not exist: {safe_file}", inputs=inputs, outputs={"usage_guard": usage_guard}, errors=[f"local_file does not exist: {safe_file}"], t0=t0)
        if not usage_guard["approved"]:
            return _result_json(
                success=False,
                stage="gen_uthana_create_character",
                message="Uthana character creation requires explicit usage confirmation",
                inputs=inputs,
                outputs={
                    "request": {
                        "filename": safe_path.name,
                        "character_name": safe_name,
                        "auto_rig": bool(auto_rig),
                        "auto_rig_front_facing": bool(auto_rig_front_facing),
                        "include_fingers": bool(include_fingers),
                        "rerig_target": _clean_optional_text(rerig_target),
                    },
                    "usage_guard": usage_guard,
                },
                warnings=["Set confirm_usage=True after user approval and allowance review to upload/auto-rig a Uthana character."],
                t0=t0,
            )
        try:
            created = await asyncio.to_thread(
                _uthana_create_character,
                file_path=safe_file,
                name=safe_name,
                auto_rig=bool(auto_rig),
                auto_rig_front_facing=bool(auto_rig_front_facing),
                include_fingers=bool(include_fingers),
                rerig_target=rerig_target,
                timeout_s=safe_timeout,
            )
            character_id = str(created.get("character_id") or "")
            if set_as_default and character_id:
                settings = _load_generative_settings()
                settings["uthana_default_character_id"] = character_id
                _write_json_file(_SETTINGS_PATH, settings)
            return _result_json(
                success=True,
                stage="gen_uthana_create_character",
                message=f"Created Uthana character {character_id}",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "character_id": character_id,
                    "character": created.get("character", {}),
                    "auto_rig_confidence": created.get("auto_rig_confidence"),
                    "provider_message": created.get("provider_message", ""),
                    "set_as_default": bool(set_as_default and character_id),
                    "usage_guard": usage_guard,
                    "motion_tools": ["gen_uthana_create_locomotion", "gen_uthana_text_to_motion", "gen_uthana_video_to_motion"],
                    "download_tool": "gen_uthana_download_motion",
                    "network_required": True,
                    "spend_required": True,
                    "http_status": created.get("http_status", 0),
                },
                warnings=["Use the returned character_id for every Uthana motion before downloading animations into Unreal."],
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_create_character",
                message=str(exc),
                inputs=inputs,
                outputs={"usage_guard": usage_guard, "network_required": True, "spend_required": True},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_get_character(ctx: Context, character_id: str, timeout_s: int = 30) -> str:
        """Fetch Uthana character metadata by ID without downloading assets.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_get_character(character_id="character-id")"""
        t0 = time.monotonic()
        safe_timeout = max(1, min(_safe_int(timeout_s, 30), 120))
        inputs = {"provider": "uthana", "character_id": character_id, "timeout_s": safe_timeout}
        try:
            loaded = await asyncio.to_thread(_uthana_get_character, character_id, timeout_s=safe_timeout)
            return _result_json(
                success=True,
                stage="gen_uthana_get_character",
                message=f"Loaded Uthana character {character_id}",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "character": loaded.get("character", {}),
                    "http_status": loaded.get("http_status", 0),
                    "network_required": True,
                    "spend_required": False,
                },
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_get_character",
                message=str(exc),
                inputs=inputs,
                outputs={"provider": "uthana", "network_required": True, "spend_required": False},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_text_to_motion(
        ctx: Context,
        prompt: str,
        character_id: str = "",
        foot_ik: bool = False,
        estimated_seconds: int = 5,
        session_name: str = "default",
        confirm_usage: bool = False,
        timeout_s: int = 60,
    ) -> str:
        """Generate a Uthana motion from text after explicit usage approval.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_text_to_motion(prompt="loopable guard patrol walk", confirm_usage=True)"""
        t0 = time.monotonic()
        settings = _load_generative_settings()
        safe_prompt = _clean_optional_text(prompt)
        safe_character_id = _clean_optional_text(character_id) or str(settings.get("uthana_default_character_id") or "cXi2eAP19XwQ")
        safe_estimate = max(1, min(_safe_int(estimated_seconds, 5), 600))
        safe_timeout = max(1, min(_safe_int(timeout_s, 60), 180))
        inputs = {
            "provider": "uthana",
            "prompt": prompt,
            "character_id": safe_character_id,
            "foot_ik": foot_ik,
            "estimated_seconds": safe_estimate,
            "session_name": session_name,
            "confirm_usage": confirm_usage,
            "timeout_s": safe_timeout,
        }
        usage_guard = _uthana_usage_guard(
            estimated_seconds=safe_estimate,
            confirm_usage=confirm_usage,
            operation="text_to_motion",
        )
        if not safe_prompt:
            return _result_json(
                success=False,
                stage="gen_uthana_text_to_motion",
                message="prompt is required",
                inputs=inputs,
                outputs={"usage_guard": usage_guard},
                errors=["prompt is required"],
                t0=t0,
            )
        if not usage_guard["approved"]:
            return _result_json(
                success=False,
                stage="gen_uthana_text_to_motion",
                message="Uthana motion generation requires explicit usage confirmation",
                inputs=inputs,
                outputs={"request": {"prompt": safe_prompt, "foot_ik": bool(foot_ik)}, "usage_guard": usage_guard},
                warnings=["Set confirm_usage=True after user approval and allowance review to call Uthana."],
                t0=t0,
            )
        try:
            created = await asyncio.to_thread(
                _uthana_create_text_motion,
                prompt=safe_prompt,
                character_id=safe_character_id,
                foot_ik=bool(foot_ik),
                timeout_s=safe_timeout,
            )
            motion = created.get("motion", {})
            return _result_json(
                success=True,
                stage="gen_uthana_text_to_motion",
                message=f"Created Uthana motion {created.get('motion_id')}",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "motion_id": created.get("motion_id", ""),
                    "motion": motion,
                    "character_id": safe_character_id,
                    "usage_guard": usage_guard,
                    "download_tool": "gen_uthana_download_motion",
                    "import_tool": "gen_uthana_import_animation_to_project",
                    "network_required": True,
                    "spend_required": True,
                    "http_status": created.get("http_status", 0),
                },
                warnings=["character_id was sent to Uthana; use the same character_id when downloading the resulting motion."],
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_text_to_motion",
                message=str(exc),
                inputs=inputs,
                outputs={"usage_guard": usage_guard, "network_required": True, "spend_required": True},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_create_locomotion(
        ctx: Context,
        character_id: str = "",
        travel_angle: float = 0.0,
        move_speed: float = 3.0,
        strides: int = 4,
        style_id: str = "",
        estimated_seconds: int = 4,
        session_name: str = "default",
        confirm_usage: bool = False,
        timeout_s: int = 60,
    ) -> str:
        """Generate Uthana locomotion for a character using travel angle, speed, and stride count.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_create_locomotion(character_id="character-id", travel_angle=45, confirm_usage=True)"""
        t0 = time.monotonic()
        settings = _load_generative_settings()
        safe_character_id = _clean_optional_text(character_id) or str(settings.get("uthana_default_character_id") or "")
        safe_estimate = max(1, min(_safe_int(estimated_seconds, 4), 600))
        safe_strides = max(1, min(_safe_int(strides, 4), 32))
        try:
            safe_angle = float(travel_angle)
        except (TypeError, ValueError):
            safe_angle = 0.0
        try:
            safe_speed = float(move_speed)
        except (TypeError, ValueError):
            safe_speed = 3.0
        safe_speed = max(0.01, min(safe_speed, 20.0))
        safe_timeout = max(1, min(_safe_int(timeout_s, 60), 180))
        usage_guard = _uthana_usage_guard(
            estimated_seconds=safe_estimate,
            confirm_usage=confirm_usage,
            operation="create_locomotion",
        )
        inputs = {
            "provider": "uthana",
            "character_id": safe_character_id,
            "travel_angle": safe_angle,
            "move_speed": safe_speed,
            "strides": safe_strides,
            "style_id": style_id,
            "estimated_seconds": safe_estimate,
            "session_name": session_name,
            "confirm_usage": confirm_usage,
            "timeout_s": safe_timeout,
        }
        if not safe_character_id:
            return _result_json(success=False, stage="gen_uthana_create_locomotion", message="character_id is required", inputs=inputs, outputs={"usage_guard": usage_guard}, errors=["character_id is required"], t0=t0)
        if not usage_guard["approved"]:
            return _result_json(
                success=False,
                stage="gen_uthana_create_locomotion",
                message="Uthana locomotion generation requires explicit usage confirmation",
                inputs=inputs,
                outputs={"request": {"character_id": safe_character_id, "travel_angle": safe_angle, "move_speed": safe_speed, "strides": safe_strides}, "usage_guard": usage_guard},
                warnings=["Set confirm_usage=True after user approval and allowance review to call Uthana."],
                t0=t0,
            )
        try:
            created = await asyncio.to_thread(
                _uthana_create_locomotion,
                character_id=safe_character_id,
                travel_angle=safe_angle,
                move_speed=safe_speed,
                strides=safe_strides,
                style_id=style_id,
                timeout_s=safe_timeout,
            )
            return _result_json(
                success=True,
                stage="gen_uthana_create_locomotion",
                message=f"Created Uthana locomotion motion {created.get('motion_id')}",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "motion_id": created.get("motion_id", ""),
                    "motion": created.get("motion", {}),
                    "character_id": safe_character_id,
                    "usage_guard": usage_guard,
                    "download_tool": "gen_uthana_download_motion",
                    "import_tool": "gen_uthana_import_animation_to_project",
                    "network_required": True,
                    "spend_required": True,
                    "http_status": created.get("http_status", 0),
                },
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_create_locomotion",
                message=str(exc),
                inputs=inputs,
                outputs={"usage_guard": usage_guard, "network_required": True, "spend_required": True},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_video_to_motion(
        ctx: Context,
        video_file: str,
        motion_name: str = "",
        model: str = "video-to-motion-v2",
        character_id: str = "",
        estimated_seconds: int = 10,
        session_name: str = "default",
        confirm_usage: bool = False,
        timeout_s: int = 180,
    ) -> str:
        """Create a Uthana video-to-motion job after explicit usage approval.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_video_to_motion(video_file="C:/capture/reference.mp4", motion_name="A_ReferenceMove", confirm_usage=True)"""
        t0 = time.monotonic()
        settings = _load_generative_settings()
        safe_file = _normalize_optional_path_or_url(video_file)
        safe_path = Path(safe_file)
        safe_motion_name = _clean_optional_text(motion_name) or _safe_name(safe_path.stem, "VideoMotion")
        safe_model = _clean_optional_text(model) or "video-to-motion-v2"
        safe_character_id = _clean_optional_text(character_id) or str(settings.get("uthana_default_character_id") or "cXi2eAP19XwQ")
        safe_estimate = max(1, min(_safe_int(estimated_seconds, 10), 600))
        safe_timeout = max(1, min(_safe_int(timeout_s, 180), 600))
        usage_guard = _uthana_usage_guard(
            estimated_seconds=safe_estimate,
            confirm_usage=confirm_usage,
            operation="video_to_motion",
        )
        inputs = {
            "provider": "uthana",
            "video_file": safe_file,
            "motion_name": safe_motion_name,
            "model": safe_model,
            "character_id": safe_character_id,
            "estimated_seconds": safe_estimate,
            "session_name": session_name,
            "confirm_usage": confirm_usage,
            "timeout_s": safe_timeout,
        }
        if not safe_file:
            return _result_json(
                success=False,
                stage="gen_uthana_video_to_motion",
                message="video_file is required",
                inputs=inputs,
                outputs={"usage_guard": usage_guard},
                errors=["video_file is required"],
                t0=t0,
            )
        if safe_path.suffix.lower() not in {".mp4", ".mov", ".avi"}:
            return _result_json(
                success=False,
                stage="gen_uthana_video_to_motion",
                message="Unsupported Uthana video format",
                inputs=inputs,
                outputs={"usage_guard": usage_guard, "supported_extensions": [".mp4", ".mov", ".avi"]},
                errors=["video_file must be .mp4, .mov, or .avi"],
                t0=t0,
            )
        if not usage_guard["approved"]:
            return _result_json(
                success=False,
                stage="gen_uthana_video_to_motion",
                message="Uthana video-to-motion requires explicit usage confirmation",
                inputs=inputs,
                outputs={
                    "request": {
                        "video_filename": safe_path.name,
                        "motion_name": safe_motion_name,
                        "model": safe_model,
                    },
                    "usage_guard": usage_guard,
                    "job_poll_tool": "gen_uthana_get_job",
                },
                warnings=["Set confirm_usage=True after user approval and allowance review to upload video to Uthana."],
                t0=t0,
            )
        if not safe_path.exists():
            return _result_json(
                success=False,
                stage="gen_uthana_video_to_motion",
                message=f"video_file does not exist: {safe_file}",
                inputs=inputs,
                outputs={"usage_guard": usage_guard},
                errors=[f"video_file does not exist: {safe_file}"],
                t0=t0,
            )
        try:
            created = await asyncio.to_thread(
                _uthana_create_video_motion,
                video_file=safe_file,
                motion_name=safe_motion_name,
                character_id=safe_character_id,
                model=safe_model,
                timeout_s=safe_timeout,
            )
            return _result_json(
                success=True,
                stage="gen_uthana_video_to_motion",
                message=f"Created Uthana video-to-motion job {created.get('job_id')}",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "job_id": created.get("job_id", ""),
                    "job_status": created.get("job_status", ""),
                    "job": created.get("job", {}),
                    "character_id": safe_character_id,
                    "usage_guard": usage_guard,
                    "status_tool": "gen_uthana_get_job",
                    "download_tool": "gen_uthana_download_motion",
                    "import_tool": "gen_uthana_import_animation_to_project",
                    "network_required": True,
                    "spend_required": True,
                    "http_status": created.get("http_status", 0),
                },
                warnings=[
                    "Video-to-motion is asynchronous; poll gen_uthana_get_job until FINISHED, then use the returned motion id for download/import.",
                    "character_id was sent to Uthana; use the same character_id when downloading the resulting motion.",
                ],
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_video_to_motion",
                message=str(exc),
                inputs=inputs,
                outputs={"usage_guard": usage_guard, "network_required": True, "spend_required": True},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_get_job(ctx: Context, job_id: str, timeout_s: int = 30) -> str:
        """Poll a Uthana async job, such as video-to-motion, without downloading output.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_get_job(job_id="job-id")"""
        t0 = time.monotonic()
        safe_timeout = max(1, min(_safe_int(timeout_s, 30), 120))
        inputs = {"provider": "uthana", "job_id": job_id, "timeout_s": safe_timeout}
        try:
            job = await asyncio.to_thread(_uthana_get_job, job_id, timeout_s=safe_timeout)
            status = str(job.get("job_status", ""))
            final = status.upper() in {"FINISHED", "FAILED"}
            return _result_json(
                success=True,
                stage="gen_uthana_get_job",
                message=f"Loaded Uthana job {job_id}",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "job_id": job.get("job_id", job_id),
                    "job_status": status,
                    "job": job.get("job", {}),
                    "motion_id": job.get("motion_id", ""),
                    "final": final,
                    "download_ready": status.upper() == "FINISHED" and bool(job.get("motion_id", "")),
                    "download_tool": "gen_uthana_download_motion",
                    "http_status": job.get("http_status", 0),
                    "network_required": True,
                    "spend_required": False,
                },
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_get_job",
                message=str(exc),
                inputs=inputs,
                outputs={"provider": "uthana", "network_required": True, "spend_required": False},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_get_motion(ctx: Context, motion_id: str, timeout_s: int = 30) -> str:
        """Get Uthana motion metadata by ID.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_get_motion(motion_id="motion-id")"""
        t0 = time.monotonic()
        safe_timeout = max(1, min(_safe_int(timeout_s, 30), 120))
        inputs = {"provider": "uthana", "motion_id": motion_id, "timeout_s": safe_timeout}
        try:
            motion = await asyncio.to_thread(_uthana_get_motion, motion_id, timeout_s=safe_timeout)
            return _result_json(
                success=True,
                stage="gen_uthana_get_motion",
                message=f"Loaded Uthana motion {motion_id}",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "motion": motion.get("motion", {}),
                    "final": True,
                    "http_status": motion.get("http_status", 0),
                    "network_required": True,
                    "spend_required": False,
                },
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_get_motion",
                message=str(exc),
                inputs=inputs,
                outputs={"provider": "uthana", "network_required": True, "spend_required": False},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_check_download_allowed(ctx: Context, motion_id: str, character_id: str = "", timeout_s: int = 30) -> str:
        """Check whether a Uthana motion download is allowed before consuming quota.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_check_download_allowed(motion_id="motion-id")"""
        t0 = time.monotonic()
        settings = _load_generative_settings()
        safe_character_id = _clean_optional_text(character_id) or str(settings.get("uthana_default_character_id") or "cXi2eAP19XwQ")
        safe_timeout = max(1, min(_safe_int(timeout_s, 30), 120))
        inputs = {
            "provider": "uthana",
            "motion_id": motion_id,
            "character_id": safe_character_id,
            "timeout_s": safe_timeout,
        }
        try:
            allowed = await asyncio.to_thread(
                _uthana_check_motion_download_allowed,
                safe_character_id,
                motion_id,
                timeout_s=safe_timeout,
            )
            return _result_json(
                success=True,
                stage="gen_uthana_check_download_allowed",
                message="Uthana motion download is allowed" if allowed.get("allowed") else "Uthana motion download is not allowed",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "allowed": bool(allowed.get("allowed")),
                    "reason": allowed.get("reason", ""),
                    "http_status": allowed.get("http_status", 0),
                    "network_required": True,
                    "spend_required": False,
                },
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_check_download_allowed",
                message=str(exc),
                inputs=inputs,
                outputs={"provider": "uthana", "network_required": True, "spend_required": False},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_download_motion(
        ctx: Context,
        motion_id: str,
        character_id: str = "",
        output_format: str = "fbx",
        target_folder: str = "",
        fps: int = 30,
        no_mesh: str = "true",
        in_place: bool = False,
        torso_only: bool = False,
        speed_multiplier: float = 1.0,
        motion_only: bool = False,
        confirm_usage: bool = False,
        check_download_allowed: bool = True,
        timeout_s: int = 180,
    ) -> str:
        """Download a Uthana motion file after explicit usage approval.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_download_motion(motion_id="motion-id", output_format="fbx", confirm_usage=True)"""
        t0 = time.monotonic()
        settings = _load_generative_settings()
        safe_motion_id = _clean_optional_text(motion_id)
        safe_character_id = _clean_optional_text(character_id) or str(settings.get("uthana_default_character_id") or "cXi2eAP19XwQ")
        safe_format = (output_format or "fbx").strip().lower()
        safe_fps = _safe_int(fps, 30)
        safe_no_mesh = (no_mesh or "true").strip().lower()
        try:
            safe_speed = float(speed_multiplier)
        except (TypeError, ValueError):
            safe_speed = 1.0
        safe_speed = max(0.01, min(2.0, safe_speed))
        safe_timeout = max(1, min(_safe_int(timeout_s, 180), 600))
        usage_guard = _uthana_usage_guard(
            estimated_seconds=1,
            confirm_usage=confirm_usage,
            operation="download_motion",
        )
        inputs = {
            "provider": "uthana",
            "motion_id": safe_motion_id,
            "character_id": safe_character_id,
            "output_format": safe_format,
            "target_folder": target_folder,
            "fps": safe_fps,
            "no_mesh": safe_no_mesh,
            "in_place": in_place,
            "torso_only": torso_only,
            "speed_multiplier": safe_speed,
            "motion_only": motion_only,
            "confirm_usage": confirm_usage,
            "check_download_allowed": check_download_allowed,
            "timeout_s": safe_timeout,
        }
        if not safe_motion_id:
            return _result_json(success=False, stage="gen_uthana_download_motion", message="motion_id is required", inputs=inputs, outputs={"usage_guard": usage_guard}, errors=["motion_id is required"], t0=t0)
        if safe_format not in {"fbx", "glb", "bvh"}:
            return _result_json(success=False, stage="gen_uthana_download_motion", message="Unsupported Uthana motion format", inputs=inputs, outputs={"usage_guard": usage_guard}, errors=["output_format must be one of: fbx, glb, bvh"], t0=t0)
        if safe_fps not in {24, 30, 60}:
            return _result_json(success=False, stage="gen_uthana_download_motion", message="Unsupported Uthana download FPS", inputs=inputs, outputs={"usage_guard": usage_guard}, errors=["fps must be one of: 24, 30, 60"], t0=t0)
        if safe_no_mesh not in {"true", "false", "minimal", ""}:
            return _result_json(success=False, stage="gen_uthana_download_motion", message="Unsupported no_mesh option", inputs=inputs, outputs={"usage_guard": usage_guard}, errors=["no_mesh must be true, false, minimal, or empty"], t0=t0)
        if safe_no_mesh == "minimal" and safe_format != "glb":
            return _result_json(success=False, stage="gen_uthana_download_motion", message="no_mesh=minimal is only supported for GLB", inputs=inputs, outputs={"usage_guard": usage_guard}, errors=["no_mesh=minimal is only supported for GLB"], t0=t0)
        if not usage_guard["approved"]:
            return _result_json(
                success=False,
                stage="gen_uthana_download_motion",
                message="Uthana motion download requires explicit usage confirmation",
                inputs=inputs,
                outputs={"usage_guard": usage_guard},
                warnings=["Set confirm_usage=True after user approval and allowance review to download Uthana motion files."],
                t0=t0,
            )
        try:
            allowed: Dict[str, Any] = {}
            if check_download_allowed:
                allowed = await asyncio.to_thread(
                    _uthana_check_motion_download_allowed,
                    safe_character_id,
                    safe_motion_id,
                    timeout_s=min(safe_timeout, 120),
                )
                if not allowed.get("allowed"):
                    return _result_json(
                        success=False,
                        stage="gen_uthana_download_motion",
                        message="Uthana download quota check did not allow this download",
                        inputs=inputs,
                        outputs={"download_allowed": allowed, "usage_guard": usage_guard},
                        errors=[allowed.get("reason") or "download not allowed"],
                        t0=t0,
                    )
            folder = Path(target_folder) if target_folder else _default_uthana_download_folder(safe_motion_id)
            filename = f"{_safe_name(safe_motion_id, 'uthana_motion')}.{safe_format}"
            target_path = folder / filename
            url = await asyncio.to_thread(
                _uthana_motion_download_url,
                character_id=safe_character_id,
                motion_id=safe_motion_id,
                output_format=safe_format,
                filename=filename,
                fps=safe_fps,
                no_mesh=safe_no_mesh,
                in_place=bool(in_place),
                torso_only=bool(torso_only),
                speed_multiplier=safe_speed,
                motion_only=bool(motion_only),
            )
            download = await asyncio.to_thread(
                _download_uthana_motion_file,
                url,
                target_path,
                timeout_s=safe_timeout,
            )
            download.update({"key": f"motion_{safe_format}", "format": safe_format})
            return _result_json(
                success=True,
                stage="gen_uthana_download_motion",
                message="Downloaded Uthana motion file",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "motion_id": safe_motion_id,
                    "character_id": safe_character_id,
                    "download": download,
                    "downloads": [download],
                    "download_allowed": allowed,
                    "usage_guard": usage_guard,
                    "retargeting_applied_by_uthana": True,
                    "import_tool": "gen_uthana_import_animation_to_project",
                    "network_required": True,
                    "spend_required": True,
                },
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_uthana_download_motion",
                message=str(exc),
                inputs=inputs,
                outputs={"usage_guard": usage_guard, "network_required": True, "spend_required": True},
                errors=[str(exc)],
                t0=t0,
            )

    @mcp.tool()
    async def gen_uthana_import_animation_to_project(
        ctx: Context,
        local_file: str,
        motion_id: str = "",
        character_id: str = "",
        content_path: str = "/Game/Generated/Animations",
        skeleton: str = "",
        import_materials: bool = False,
        require_bridge_ping: bool = True,
    ) -> str:
        """Import a downloaded Uthana FBX into Unreal and report remaining retarget/readback gates.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#uthana-motion-task-family
        Example:
            gen_uthana_import_animation_to_project(local_file="C:/MCP/uthana/motion.fbx")"""
        t0 = time.monotonic()
        safe_file = _normalize_optional_path_or_url(local_file)
        safe_content_path = _normalize_content_folder(content_path or "/Game/Generated/Animations")
        inputs = {
            "provider": "uthana",
            "local_file": safe_file,
            "motion_id": motion_id,
            "character_id": character_id,
            "content_path": safe_content_path,
            "skeleton": skeleton,
            "import_materials": import_materials,
            "require_bridge_ping": require_bridge_ping,
        }
        source = Path(safe_file)
        if not safe_file:
            return _result_json(success=False, stage="gen_uthana_import_animation_to_project", message="local_file is required", inputs=inputs, errors=["local_file is required"], t0=t0)
        if source.suffix.lower() != ".fbx":
            return _result_json(
                success=False,
                stage="gen_uthana_import_animation_to_project",
                message="Uthana Unreal animation import currently requires FBX",
                inputs=inputs,
                outputs={"supported_extensions": [".fbx"], "download_tool": "gen_uthana_download_motion"},
                errors=["Download output_format='fbx' before importing generated animation into Unreal."],
                t0=t0,
            )
        if not source.exists():
            return _result_json(success=False, stage="gen_uthana_import_animation_to_project", message=f"local_file does not exist: {safe_file}", inputs=inputs, errors=[f"local_file does not exist: {safe_file}"], t0=t0)
        bridge_state: Dict[str, Any] = {}
        if require_bridge_ping:
            bridge_state = await asyncio.to_thread(_bridge_ping_ready)
            if not bridge_state.get("ready"):
                return _result_json(
                    success=False,
                    stage="gen_uthana_import_animation_to_project",
                    message="Unreal bridge ping is required before importing generated animation",
                    inputs=inputs,
                    outputs={"bridge": bridge_state, "network_required": False, "spend_required": False},
                    errors=["unreal_bridge_reachable gate is not ready"],
                    t0=t0,
                )
        try:
            import_result = await asyncio.to_thread(
                _import_uthana_animation_fbx,
                file_path=str(source),
                content_path=safe_content_path,
                skeleton=skeleton,
                import_materials=bool(import_materials),
            )
            success = bool(import_result.get("success"))
            outputs = import_result.get("outputs", {}) if isinstance(import_result.get("outputs"), dict) else {}
            asset_paths = {
                "primary_asset": outputs.get("asset_path", ""),
                "animation_sequence_paths": outputs.get("animation_sequence_paths", []),
                "skeletal_mesh_paths": outputs.get("skeletal_mesh_paths", []),
                "skeleton_paths": outputs.get("skeleton_paths", []),
            }
            warnings = list(import_result.get("warnings") or [])
            warnings.append("Import is not final proof; retarget readback, AnimGraph reference, PIE proof, and ledger evidence are still required.")
            return _result_json(
                success=success,
                stage="gen_uthana_import_animation_to_project",
                message="Imported Uthana animation FBX into Unreal project" if success else "Uthana animation import failed",
                inputs=inputs,
                outputs={
                    "provider": "uthana",
                    "motion_id": motion_id,
                    "character_id": character_id,
                    "import_result": import_result,
                    "asset_paths": asset_paths,
                    "bridge": bridge_state,
                    "remaining_quality_gates": [
                        "animation_retarget_readback",
                        "animgraph_or_state_machine_reference",
                        "pie_motion_proof",
                        "ledger_animation_evidence",
                    ],
                    "network_required": False,
                    "spend_required": False,
                },
                warnings=warnings,
                errors=[] if success else import_result.get("errors") or ["Uthana animation import failed"],
                t0=t0,
            )
        except Exception as exc:
            return _result_json(success=False, stage="gen_uthana_import_animation_to_project", message=str(exc), inputs=inputs, errors=[str(exc)], t0=t0)

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
    async def gen_prepare_texture_paint_session(
        ctx: Context,
        model_task_id: str,
        texture_prompt: str,
        texture_reference_image: str = "",
        view_angle: str = "current viewport/front",
        brush_strength: float = 0.65,
        blend_mode: str = "soft blend",
        paint_notes: str = "",
        output_folder: str = "/Game/Generated",
        save_asset_name: str = "MI_GeneratedPaintedTexture",
        session_name: str = "default",
    ) -> str:
        """Plan a Tripo texture-paint edit session without making a paid request.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#d9-chat-dock-integration
        Example:
            gen_prepare_texture_paint_session(model_task_id="task_123", texture_prompt="weathered brass", view_angle="front", save_asset_name="MI_BrassPass")"""
        t0 = time.monotonic()
        safe_model_task_id = _clean_optional_text(model_task_id)
        safe_texture_prompt = _clean_optional_text(texture_prompt)
        safe_session = (session_name or "default").strip() or "default"
        safe_output_folder = _normalize_content_folder(output_folder)
        safe_save_name = _safe_name(save_asset_name, "MI_GeneratedPaintedTexture")
        safe_reference = _normalize_optional_path_or_url(texture_reference_image)
        safe_view_angle = _clean_optional_text(view_angle) or "current viewport/front"
        safe_blend_mode = _clean_optional_text(blend_mode) or "soft blend"
        safe_paint_notes = _clean_optional_text(paint_notes)
        try:
            safe_brush_strength = max(0.0, min(1.0, float(brush_strength)))
        except (TypeError, ValueError):
            safe_brush_strength = 0.65
        inputs = {
            "model_task_id": model_task_id,
            "texture_prompt": texture_prompt,
            "texture_reference_image": texture_reference_image,
            "view_angle": view_angle,
            "brush_strength": brush_strength,
            "blend_mode": blend_mode,
            "paint_notes": paint_notes,
            "output_folder": output_folder,
            "save_asset_name": save_asset_name,
            "session_name": session_name,
        }
        errors = []
        if not safe_model_task_id:
            errors.append("model_task_id is required")
        if not safe_texture_prompt:
            errors.append("texture_prompt is required")
        if errors:
            return _result_json(
                success=False,
                stage="gen_prepare_texture_paint_session",
                message="Texture-paint session inputs are incomplete",
                inputs=inputs,
                errors=errors,
                t0=t0,
            )

        prompt_parts = [safe_texture_prompt]
        if safe_reference:
            prompt_parts.append(f"use texture reference image {safe_reference} as the visual style target")
        if safe_paint_notes:
            prompt_parts.append(f"paint/blend notes: {safe_paint_notes}")
        prompt_parts.append(
            "texture edit workspace controls: generate the high-fidelity texture image "
            f"from the {safe_view_angle} mesh view, paint it onto the visible model, "
            f"rotate the model as needed, use brush strength {safe_brush_strength:.2f}, "
            f"use {safe_blend_mode}, then save the satisfied result as {safe_save_name}"
        )
        composed_prompt = "; ".join(prompt_parts)
        session_record = {
            "session_name": safe_session,
            "model_task_id": safe_model_task_id,
            "texture_prompt": composed_prompt,
            "texture_reference_image": safe_reference,
            "view_angle": safe_view_angle,
            "brush_strength": safe_brush_strength,
            "blend_mode": safe_blend_mode,
            "paint_notes": safe_paint_notes,
            "output_folder": safe_output_folder,
            "save_asset_name": safe_save_name,
            "created_at": int(time.time()),
        }
        save_info = _save_texture_paint_session(session_record)
        texture_quality = _load_generative_settings().get("default_texture_quality", "standard")
        next_steps = [
            {
                "tool": "gen_tripo_texture_model",
                "args": {
                    "task_id": safe_model_task_id,
                    "texture_prompt": composed_prompt,
                    "texture_quality": texture_quality,
                    "texture_alignment": "original_image",
                    "session_name": safe_session,
                    "confirm_spend": False,
                },
            },
            {"tool": "gen_tripo_wait_for_task", "args": {"task_id": "<texture_task_id>", "timeout_s": 900, "poll_s": 10}},
            {
                "tool": "gen_tripo_import_to_project",
                "args": {
                    "task_id": "<texture_task_id>",
                    "content_path": safe_output_folder,
                    "asset_name": safe_save_name,
                    "create_material_instance": True,
                    "create_blueprint": False,
                },
            },
        ]
        evidence_contract = [
            "texture_task_id and final Tripo status",
            "imported material/static-mesh asset paths",
            "viewport screenshot of the painted result",
            "paint/blend settings used by the user",
            "human approval note before marking the texture pass final",
        ]
        return _result_json(
            success=True,
            stage="gen_prepare_texture_paint_session",
            message="Prepared Tripo texture-paint session plan",
            inputs=inputs,
            outputs={
                "session": session_record,
                "next_steps": next_steps,
                "evidence_contract": evidence_contract,
                **save_info,
            },
            warnings=[
                "This planner does not call Tripo or paint pixels; run gen_tripo_texture_model after user spend approval.",
                "Dedicated image-reference texture API support should replace prompt-encoded references when Tripo exposes it through the task API.",
            ],
            t0=t0,
        )

    @mcp.tool()
    async def gen_compile_texture_paint_evidence(
        ctx: Context,
        session_name: str = "default",
        model_task_id: str = "",
        prepare_result_json: str = "",
        texture_task_result_json: str = "",
        wait_result_json: str = "",
        import_result_json: str = "",
        viewport_evidence_json: str = "",
        approval_note: str = "",
    ) -> str:
        """Compile a no-spend evidence receipt for a Tripo texture-paint pass.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#texture-paint-evidence
        Example:
            gen_compile_texture_paint_evidence(session_name="demo", texture_task_result_json="<json>", import_result_json="<json>")"""
        t0 = time.monotonic()
        safe_session = (session_name or "default").strip() or "default"
        prepare_result = _coerce_json_object(prepare_result_json)
        texture_task_result = _coerce_json_object(texture_task_result_json)
        wait_result = _coerce_json_object(wait_result_json)
        import_result = _coerce_json_object(import_result_json)
        viewport_evidence = _coerce_json_object(viewport_evidence_json)
        safe_model_task_id = _clean_optional_text(model_task_id)

        session_from_prepare = _nested_dict(prepare_result, "outputs", "session")
        if not safe_model_task_id:
            safe_model_task_id = _clean_optional_text(str(session_from_prepare.get("model_task_id", "")))
        latest_saved_session = _latest_texture_paint_session(safe_session, safe_model_task_id)
        session = dict(session_from_prepare) if session_from_prepare else latest_saved_session
        if session_from_prepare and latest_saved_session:
            for dynamic_key in ("viewport_snapshots", "paint_passes"):
                dynamic_value = latest_saved_session.get(dynamic_key)
                if isinstance(dynamic_value, list):
                    session[dynamic_key] = dynamic_value
        if not safe_model_task_id:
            safe_model_task_id = _clean_optional_text(str(session.get("model_task_id", "")))

        texture_outputs = _nested_dict(texture_task_result, "outputs")
        wait_outputs = _nested_dict(wait_result, "outputs")
        import_outputs = _nested_dict(import_result, "outputs")
        task_from_wait = wait_outputs.get("task") if isinstance(wait_outputs.get("task"), dict) else {}
        task_from_status = _nested_dict(import_outputs, "task")
        texture_task_id = (
            _clean_optional_text(str(texture_outputs.get("task_id", ""))) or
            _clean_optional_text(str(task_from_wait.get("task_id", ""))) or
            _clean_optional_text(str(task_from_status.get("task_id", "")))
        )
        final_status = (
            _clean_optional_text(str(task_from_wait.get("status", ""))) or
            _clean_optional_text(str(task_from_status.get("status", ""))) or
            _clean_optional_text(str(wait_result.get("message", "")))
        )
        consumed_credit = task_from_wait.get("consumed_credit", task_from_status.get("consumed_credit"))
        asset_paths = import_outputs.get("asset_paths") if isinstance(import_outputs.get("asset_paths"), dict) else {}
        thumbnail = import_outputs.get("thumbnail") if isinstance(import_outputs.get("thumbnail"), dict) else {}
        viewport_outputs = _nested_dict(viewport_evidence, "outputs")
        session_snapshots = session.get("viewport_snapshots") if isinstance(session.get("viewport_snapshots"), list) else []
        latest_session_snapshot = session_snapshots[-1] if session_snapshots and isinstance(session_snapshots[-1], dict) else {}
        paint_passes = session.get("paint_passes") if isinstance(session.get("paint_passes"), list) else []
        latest_paint_pass = paint_passes[-1] if paint_passes and isinstance(paint_passes[-1], dict) else {}
        viewport_path = (
            _clean_optional_text(str(thumbnail.get("path", ""))) or
            _clean_optional_text(str(viewport_outputs.get("screenshot_path", ""))) or
            _clean_optional_text(str(viewport_outputs.get("path", ""))) or
            _clean_optional_text(str(latest_paint_pass.get("result_snapshot_path", ""))) or
            _clean_optional_text(str(latest_session_snapshot.get("path", "")))
        )
        approval = _clean_optional_text(approval_note) or _clean_optional_text(str(latest_paint_pass.get("approval_note", "")))
        gates = [
            _readiness_gate("texture_paint_session", bool(session), "prepared session found" if session else "run gen_prepare_texture_paint_session"),
            _readiness_gate("source_model_task", bool(safe_model_task_id), safe_model_task_id or "missing original model_task_id"),
            _readiness_gate("texture_task", bool(texture_task_id), texture_task_id or "run gen_tripo_texture_model"),
            _readiness_gate("final_status", final_status.lower() == "success" or task_from_wait.get("status") == "success" or task_from_status.get("status") == "success", final_status or "run gen_tripo_wait_for_task"),
            _readiness_gate("imported_assets", bool(asset_paths), "imported asset paths present" if asset_paths else "run gen_tripo_import_to_project"),
            _readiness_gate("viewport_evidence", bool(viewport_path), viewport_path or "capture/import thumbnail or viewport screenshot"),
            _readiness_gate("paint_pass_recorded", bool(paint_passes), f"{len(paint_passes)} paint pass(es) recorded" if paint_passes else "run gen_record_texture_paint_pass after painting/blending"),
            _readiness_gate("human_approval", bool(approval), approval or "add approval_note after inspecting the painted result"),
        ]
        proven = all(gate["ready"] for gate in gates)
        next_actions = []
        if not session:
            next_actions.append({"tool": "gen_prepare_texture_paint_session", "reason": "Create the texture-paint session plan."})
        if not texture_task_id:
            next_actions.append({"tool": "gen_tripo_texture_model", "reason": "Submit the approved texture generation task."})
        if not (task_from_wait.get("status") == "success" or task_from_status.get("status") == "success"):
            next_actions.append({"tool": "gen_tripo_wait_for_task", "reason": "Wait for a successful texture task result."})
        if not asset_paths:
            next_actions.append({"tool": "gen_tripo_import_to_project", "reason": "Import the textured output into Unreal."})
        if not viewport_path:
            next_actions.append({"tool": "viewport evidence tool", "reason": "Capture the painted/imported result in the editor viewport."})
        if not paint_passes:
            next_actions.append({"tool": "gen_record_texture_paint_pass", "reason": "Record the user's paint/blend pass controls and affected model regions."})
        if not approval:
            next_actions.append({"tool": "human review", "reason": "Record approval after inspecting the painted/blended result."})

        evidence = {
            "schema": "unreal_mcp_texture_paint_evidence.v1",
            "proven": proven,
            "provider": "tripo",
            "session_name": safe_session,
            "model_task_id": safe_model_task_id,
            "texture_task_id": texture_task_id,
            "final_status": final_status,
            "consumed_credit": consumed_credit,
            "texture_prompt": session.get("texture_prompt", ""),
            "reference_image": session.get("texture_reference_image", ""),
            "paint_controls": {
                "view_angle": session.get("view_angle", ""),
                "brush_strength": session.get("brush_strength"),
                "blend_mode": session.get("blend_mode", ""),
                "paint_notes": session.get("paint_notes", ""),
            },
            "paint_passes": paint_passes,
            "latest_paint_pass": latest_paint_pass,
            "asset_paths": asset_paths,
            "viewport_evidence": {
                "path": viewport_path,
                "thumbnail": thumbnail,
                "session_snapshot": latest_session_snapshot,
            },
            "approval_note": approval,
            "network_required": False,
            "spend_required": False,
            "gates": gates,
            "next_actions": next_actions,
        }
        return _result_json(
            success=True,
            stage="gen_compile_texture_paint_evidence",
            message="Compiled complete texture-paint evidence" if proven else "Compiled partial texture-paint evidence with remaining gates",
            inputs={
                "session_name": session_name,
                "model_task_id": model_task_id,
                "prepare_result_json_supplied": bool(prepare_result_json),
                "texture_task_result_json_supplied": bool(texture_task_result_json),
                "wait_result_json_supplied": bool(wait_result_json),
                "import_result_json_supplied": bool(import_result_json),
                "viewport_evidence_json_supplied": bool(viewport_evidence_json),
                "approval_note_supplied": bool(approval_note),
            },
            outputs={"evidence": evidence},
            warnings=[] if proven else ["Texture-paint evidence is not final until all gates are ready."],
            t0=t0,
        )

    @mcp.tool()
    async def gen_compile_generated_animation_evidence(
        ctx: Context,
        motion_prompt: str = "",
        session_name: str = "default",
        motion_id: str = "",
        character_id: str = "",
        text_motion_result_json: str = "",
        job_result_json: str = "",
        motion_result_json: str = "",
        download_allowed_json: str = "",
        download_result_json: str = "",
        import_result_json: str = "",
        retarget_evidence_json: str = "",
        animgraph_evidence_json: str = "",
        pie_evidence_json: str = "",
        ledger_evidence_json: str = "",
        approval_note: str = "",
    ) -> str:
        """Compile no-spend evidence for a generated Uthana animation lifecycle.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#generated-animation-evidence
        Example:
            gen_compile_generated_animation_evidence(motion_id="motion-id", import_result_json="<json>")"""
        t0 = time.monotonic()
        safe_session = (session_name or "default").strip() or "default"
        safe_prompt = _clean_optional_text(motion_prompt)
        text_motion_result = _coerce_json_object(text_motion_result_json)
        job_result = _coerce_json_object(job_result_json)
        motion_result = _coerce_json_object(motion_result_json)
        download_allowed = _coerce_json_object(download_allowed_json)
        download_result = _coerce_json_object(download_result_json)
        import_result = _coerce_json_object(import_result_json)
        retarget_evidence = _coerce_json_object(retarget_evidence_json)
        animgraph_evidence = _coerce_json_object(animgraph_evidence_json)
        pie_evidence = _coerce_json_object(pie_evidence_json)
        ledger_evidence = _coerce_json_object(ledger_evidence_json)

        text_outputs = _nested_dict(text_motion_result, "outputs")
        job_outputs = _nested_dict(job_result, "outputs")
        motion_outputs = _nested_dict(motion_result, "outputs")
        download_allowed_outputs = _nested_dict(download_allowed, "outputs")
        download_outputs = _nested_dict(download_result, "outputs")
        import_outputs = _nested_dict(import_result, "outputs")
        job_obj = job_outputs.get("job") if isinstance(job_outputs.get("job"), dict) else {}
        job_result_obj = job_obj.get("result") if isinstance(job_obj.get("result"), dict) else {}
        job_nested_result_obj = job_result_obj.get("result") if isinstance(job_result_obj.get("result"), dict) else {}
        motion_obj = motion_outputs.get("motion") if isinstance(motion_outputs.get("motion"), dict) else {}
        text_motion_obj = text_outputs.get("motion") if isinstance(text_outputs.get("motion"), dict) else {}
        download_obj = download_outputs.get("download") if isinstance(download_outputs.get("download"), dict) else {}
        asset_paths = import_outputs.get("asset_paths") if isinstance(import_outputs.get("asset_paths"), dict) else {}

        safe_motion_id = (
            _clean_optional_text(motion_id) or
            _clean_optional_text(str(text_outputs.get("motion_id", ""))) or
            _clean_optional_text(str(job_outputs.get("motion_id", ""))) or
            _clean_optional_text(str(job_nested_result_obj.get("id", ""))) or
            _clean_optional_text(str(job_result_obj.get("id", ""))) or
            _clean_optional_text(str(motion_obj.get("id", ""))) or
            _clean_optional_text(str(text_motion_obj.get("id", ""))) or
            _clean_optional_text(str(download_outputs.get("motion_id", ""))) or
            _clean_optional_text(str(import_outputs.get("motion_id", "")))
        )
        safe_character_id = (
            _clean_optional_text(character_id) or
            _clean_optional_text(str(text_outputs.get("character_id", ""))) or
            _clean_optional_text(str(download_outputs.get("character_id", ""))) or
            _clean_optional_text(str(import_outputs.get("character_id", ""))) or
            str(_load_generative_settings().get("uthana_default_character_id") or "")
        )
        if not safe_prompt:
            safe_prompt = _clean_optional_text(str(text_motion_obj.get("name", ""))) or _clean_optional_text(str(motion_obj.get("name", "")))
        job_status = _clean_optional_text(str(job_outputs.get("job_status", "") or job_obj.get("status", "")))
        provider_task_evidence = {}
        if job_result:
            provider_task_evidence = {
                "source": "gen_uthana_get_job",
                "job_id": _clean_optional_text(str(job_outputs.get("job_id", "") or job_obj.get("id", ""))),
                "job_status": job_status,
                "motion_id": safe_motion_id,
                "download_ready": bool(job_outputs.get("download_ready", False)),
                "final": bool(job_outputs.get("final", False)),
            }
        elif text_motion_result:
            provider_task_evidence = {
                "source": "gen_uthana_text_to_motion",
                "motion_id": safe_motion_id,
            }
        elif motion_result:
            provider_task_evidence = {
                "source": "gen_uthana_get_motion",
                "motion_id": safe_motion_id,
            }

        def evidence_ready(packet: Dict[str, Any]) -> bool:
            return bool(packet) and packet.get("success") is not False and not bool(packet.get("errors"))

        allowed_ready = bool(download_allowed_outputs.get("allowed")) or not download_allowed
        downloaded_path = (
            _clean_optional_text(str(download_obj.get("path", ""))) or
            _clean_optional_text(str((download_outputs.get("downloads") or [{}])[0].get("path", "") if isinstance(download_outputs.get("downloads"), list) and download_outputs.get("downloads") else ""))
        )
        animation_paths = asset_paths.get("animation_sequence_paths") if isinstance(asset_paths.get("animation_sequence_paths"), list) else []
        primary_imported_asset = (
            _clean_optional_text(str(asset_paths.get("primary_asset", ""))) or
            (_clean_optional_text(str(animation_paths[0])) if animation_paths else "")
        )
        retarget_outputs = _nested_dict(retarget_evidence, "outputs")
        animgraph_outputs = _nested_dict(animgraph_evidence, "outputs")
        pie_outputs = _nested_dict(pie_evidence, "outputs")
        ledger_outputs = _nested_dict(ledger_evidence, "outputs")
        retarget_summary = retarget_outputs or retarget_evidence
        animgraph_summary = animgraph_outputs or animgraph_evidence
        pie_summary = pie_outputs or pie_evidence
        ledger_summary = ledger_outputs or ledger_evidence
        approval = _clean_optional_text(approval_note) or _clean_optional_text(str(ledger_summary.get("approval_note", "")))

        gates = [
            _readiness_gate("motion_prompt", bool(safe_prompt), safe_prompt or "record the source text-to-motion prompt"),
            _readiness_gate("motion_id", bool(safe_motion_id), safe_motion_id or "run gen_uthana_text_to_motion"),
            _readiness_gate("character_id", bool(safe_character_id), safe_character_id or "record the Uthana character id used for retargeted download"),
            _readiness_gate("download_allowed", allowed_ready, download_allowed_outputs.get("reason", "") or "run gen_uthana_check_download_allowed when quota evidence is required"),
            _readiness_gate("motion_file_downloaded", bool(downloaded_path), downloaded_path or "run gen_uthana_download_motion"),
            _readiness_gate("animation_imported", bool(primary_imported_asset), primary_imported_asset or "run gen_uthana_import_animation_to_project"),
            _readiness_gate("retarget_readback", evidence_ready(retarget_evidence), "retarget/readback evidence supplied" if evidence_ready(retarget_evidence) else "run retarget/readback tools and supply the result JSON"),
            _readiness_gate("animgraph_reference", evidence_ready(animgraph_evidence), "AnimGraph/state-machine evidence supplied" if evidence_ready(animgraph_evidence) else "wire the generated animation into AnimGraph/state machine and supply readback JSON"),
            _readiness_gate("pie_motion_proof", evidence_ready(pie_evidence), "PIE/runtime proof supplied" if evidence_ready(pie_evidence) else "capture PIE log, actor state, or viewport proof of the motion in gameplay"),
            _readiness_gate("ledger_evidence", evidence_ready(ledger_evidence), "ledger evidence supplied" if evidence_ready(ledger_evidence) else "record generated animation evidence in the IDE companion ledger"),
            _readiness_gate("human_approval", bool(approval), approval or "record approval after inspecting the generated motion in gameplay context"),
        ]
        proven = all(gate["ready"] for gate in gates)

        next_actions = []
        if not safe_motion_id:
            if job_result:
                next_actions.append({"tool": "gen_uthana_get_job", "reason": "Poll the Uthana video-to-motion job until it returns a finished motion id."})
            else:
                next_actions.append({"tool": "gen_uthana_text_to_motion", "reason": "Create the generated motion after Uthana usage approval."})
        if not downloaded_path:
            next_actions.append({"tool": "gen_uthana_download_motion", "reason": "Download FBX/GLB/BVH motion output after allowance and usage approval."})
        if not primary_imported_asset:
            next_actions.append({"tool": "gen_uthana_import_animation_to_project", "reason": "Import the downloaded FBX after the Unreal bridge ping gate is ready."})
        if not evidence_ready(retarget_evidence):
            next_actions.append({"tool": "retarget_single_animation", "reason": "Retarget the imported animation and capture readback against the target skeleton."})
        if not evidence_ready(animgraph_evidence):
            next_actions.append({"tool": "set_animation_for_state", "reason": "Reference the generated motion from an Animation Blueprint state or AnimGraph node and capture readback."})
        if not evidence_ready(pie_evidence):
            next_actions.append({"tool": "PIE evidence tools", "reason": "Capture runtime proof that the generated motion plays in context."})
        if not evidence_ready(ledger_evidence):
            next_actions.append({"tool": "record_generated_asset_evidence", "reason": "Attach generated animation evidence to the companion ledger."})
        if not approval:
            next_actions.append({"tool": "human review", "reason": "Approve the generated motion after visual/runtime inspection."})

        evidence = {
            "schema": "unreal_mcp_generated_animation_evidence.v1",
            "proven": proven,
            "provider": "uthana",
            "session_name": safe_session,
            "motion_prompt": safe_prompt,
            "motion_id": safe_motion_id,
            "character_id": safe_character_id,
            "motion_metadata": motion_obj or text_motion_obj,
            "provider_task_evidence": provider_task_evidence,
            "job": job_obj,
            "job_status": job_status,
            "download_allowed": download_allowed_outputs,
            "download": download_obj,
            "downloaded_path": downloaded_path,
            "asset_paths": asset_paths,
            "primary_imported_asset": primary_imported_asset,
            "retarget_evidence": retarget_summary,
            "animgraph_evidence": animgraph_summary,
            "pie_evidence": pie_summary,
            "ledger_evidence": ledger_summary,
            "approval_note": approval,
            "network_required": False,
            "spend_required": False,
            "gates": gates,
            "next_actions": next_actions,
        }
        return _result_json(
            success=True,
            stage="gen_compile_generated_animation_evidence",
            message="Compiled complete generated-animation evidence" if proven else "Compiled partial generated-animation evidence with remaining gates",
            inputs={
                "session_name": session_name,
                "motion_id": motion_id,
                "character_id": character_id,
                "text_motion_result_json_supplied": bool(text_motion_result_json),
                "job_result_json_supplied": bool(job_result_json),
                "motion_result_json_supplied": bool(motion_result_json),
                "download_allowed_json_supplied": bool(download_allowed_json),
                "download_result_json_supplied": bool(download_result_json),
                "import_result_json_supplied": bool(import_result_json),
                "retarget_evidence_json_supplied": bool(retarget_evidence_json),
                "animgraph_evidence_json_supplied": bool(animgraph_evidence_json),
                "pie_evidence_json_supplied": bool(pie_evidence_json),
                "ledger_evidence_json_supplied": bool(ledger_evidence_json),
                "approval_note_supplied": bool(approval_note),
            },
            outputs={"evidence": evidence},
            warnings=[] if proven else ["Generated animation evidence is not final until motion, download, import, retarget, AnimGraph, PIE, ledger, and approval gates are ready."],
            t0=t0,
        )

    @mcp.tool()
    async def gen_record_texture_paint_pass(
        ctx: Context,
        session_name: str = "default",
        model_task_id: str = "",
        pass_label: str = "paint_pass_01",
        source_snapshot_label: str = "source_view",
        result_snapshot_label: str = "painted_view",
        texture_task_id: str = "",
        texture_asset_path: str = "",
        affected_regions: str = "",
        brush_strength: float = -1.0,
        brush_radius: float = 0.25,
        blend_amount: float = 0.50,
        blend_mode: str = "",
        pass_notes: str = "",
        approval_note: str = "",
    ) -> str:
        """Record a no-spend Texture/Paint brush pass for evidence and iteration.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#texture-paint-pass-records
        Example:
            gen_record_texture_paint_pass(session_name="demo", pass_label="front_highlights", affected_regions="front panels", approval_note="Approved pass")"""
        t0 = time.monotonic()
        safe_session = (session_name or "default").strip() or "default"
        safe_model_task_id = _clean_optional_text(model_task_id)
        session = _latest_texture_paint_session(safe_session, safe_model_task_id)
        if not safe_model_task_id:
            safe_model_task_id = _clean_optional_text(str(session.get("model_task_id", "")))
        if not session:
            return _result_json(
                success=False,
                stage="gen_record_texture_paint_pass",
                message="No matching Texture/Paint session found",
                inputs={
                    "session_name": session_name,
                    "model_task_id": model_task_id,
                    "pass_label": pass_label,
                },
                outputs={"network_required": False, "spend_required": False},
                errors=["run gen_prepare_texture_paint_session before recording paint passes"],
                t0=t0,
            )

        safe_pass_label = _safe_name(pass_label, "paint_pass_01")
        safe_source_label = _safe_name(source_snapshot_label, "source_view")
        safe_result_label = _safe_name(result_snapshot_label, "painted_view")
        safe_task_id = _clean_optional_text(texture_task_id)
        safe_asset_path = _normalize_optional_path_or_url(texture_asset_path)
        safe_regions = _clean_optional_text(affected_regions)
        safe_blend_mode = _clean_optional_text(blend_mode) or _clean_optional_text(str(session.get("blend_mode", ""))) or "soft blend"
        safe_notes = _clean_optional_text(pass_notes)
        safe_approval = _clean_optional_text(approval_note)
        try:
            parsed_strength = float(brush_strength)
        except (TypeError, ValueError):
            parsed_strength = -1.0
        if parsed_strength < 0.0:
            parsed_strength = session.get("brush_strength", 0.65)
        try:
            safe_strength = max(0.0, min(1.0, float(parsed_strength)))
        except (TypeError, ValueError):
            safe_strength = 0.65
        try:
            safe_radius = max(0.01, min(1.0, float(brush_radius)))
        except (TypeError, ValueError):
            safe_radius = 0.25
        try:
            safe_blend = max(0.0, min(1.0, float(blend_amount)))
        except (TypeError, ValueError):
            safe_blend = 0.50

        snapshots = session.get("viewport_snapshots") if isinstance(session.get("viewport_snapshots"), list) else []
        matching_source = next((item for item in reversed(snapshots) if isinstance(item, dict) and item.get("label") == safe_source_label), {})
        matching_result = next((item for item in reversed(snapshots) if isinstance(item, dict) and item.get("label") == safe_result_label), {})
        paint_pass = {
            "pass_label": safe_pass_label,
            "session_name": safe_session,
            "model_task_id": safe_model_task_id,
            "source_snapshot_label": safe_source_label,
            "source_snapshot_path": matching_source.get("path", ""),
            "result_snapshot_label": safe_result_label,
            "result_snapshot_path": matching_result.get("path", ""),
            "texture_task_id": safe_task_id,
            "texture_asset_path": safe_asset_path,
            "affected_regions": safe_regions,
            "brush_strength": safe_strength,
            "brush_radius": safe_radius,
            "blend_amount": safe_blend,
            "blend_mode": safe_blend_mode,
            "pass_notes": safe_notes,
            "approval_note": safe_approval,
            "approved": bool(safe_approval),
            "created_at": int(time.time()),
        }
        update_info = _record_texture_paint_pass(
            session_name=safe_session,
            model_task_id=safe_model_task_id,
            paint_pass=paint_pass,
        )
        warnings = []
        if not matching_source:
            warnings.append(f"No viewport snapshot matched source label '{safe_source_label}'.")
        if not matching_result:
            warnings.append(f"No viewport snapshot matched result label '{safe_result_label}'.")
        if not safe_approval:
            warnings.append("Paint pass recorded without an approval_note; final evidence will still require human approval.")
        if not update_info.get("updated"):
            warnings.append(str(update_info.get("reason") or "Paint pass was not attached to a texture-paint session."))
        return _result_json(
            success=bool(update_info.get("updated")),
            stage="gen_record_texture_paint_pass",
            message="Recorded Texture/Paint pass" if update_info.get("updated") else "Texture/Paint pass was not recorded",
            inputs={
                "session_name": session_name,
                "model_task_id": model_task_id,
                "pass_label": pass_label,
                "source_snapshot_label": source_snapshot_label,
                "result_snapshot_label": result_snapshot_label,
                "texture_task_id": texture_task_id,
                "texture_asset_path": texture_asset_path,
                "affected_regions": affected_regions,
                "brush_strength": brush_strength,
                "brush_radius": brush_radius,
                "blend_amount": blend_amount,
                "blend_mode": blend_mode,
                "pass_notes": pass_notes,
                "approval_note_supplied": bool(approval_note),
            },
            outputs={
                "paint_pass": paint_pass,
                "session_update": update_info,
                "network_required": False,
                "spend_required": False,
            },
            warnings=warnings,
            errors=[] if update_info.get("updated") else [str(update_info.get("reason") or "record failed")],
            t0=t0,
        )

    @mcp.tool()
    async def gen_capture_texture_paint_snapshot(
        ctx: Context,
        session_name: str = "default",
        model_task_id: str = "",
        label: str = "before_paint",
        screenshot_dir: str = ".mcp_artifacts/texture_paint",
        show_ui: bool = False,
        resolution: Optional[List[int]] = None,
        upload_to_tripo: bool = False,
    ) -> str:
        """Capture the active Unreal viewport for a Texture/Paint session.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#texture-paint-viewport-snapshots
        Example:
            gen_capture_texture_paint_snapshot(session_name="demo", label="front_view", upload_to_tripo=False)"""
        t0 = time.monotonic()
        safe_session = (session_name or "default").strip() or "default"
        safe_label = _safe_name(label, "texture_paint_snapshot")
        safe_model_task_id = _clean_optional_text(model_task_id)
        session = _latest_texture_paint_session(safe_session, safe_model_task_id)
        if not safe_model_task_id:
            safe_model_task_id = _clean_optional_text(str(session.get("model_task_id", "")))

        raw_resolution = resolution or [1024, 1024]
        width = max(128, min(_safe_int(raw_resolution[0] if len(raw_resolution) > 0 else 1024, 1024), 4096))
        height = max(128, min(_safe_int(raw_resolution[1] if len(raw_resolution) > 1 else width, width), 4096))
        output_dir = (_REPO_ROOT / screenshot_dir).resolve() if not Path(screenshot_dir).is_absolute() else Path(screenshot_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{int(time.time())}_{_safe_name(safe_session, 'session')}_{_safe_name(safe_model_task_id, 'model')}_{safe_label}.png"
        filepath = output_dir / filename
        inputs = {
            "session_name": session_name,
            "model_task_id": model_task_id,
            "label": label,
            "screenshot_dir": screenshot_dir,
            "show_ui": show_ui,
            "resolution": [width, height],
            "upload_to_tripo": upload_to_tripo,
        }
        raw = await asyncio.to_thread(
            _send,
            "take_screenshot",
            {
                "filepath": str(filepath),
                "show_ui": show_ui,
                "resolution": [width, height],
            },
        )
        failed = raw.get("success") is False or raw.get("status") == "error" or bool(raw.get("error"))
        if failed or not filepath.exists():
            message = raw.get("error") or raw.get("message") or "Texture/Paint viewport snapshot failed"
            return _result_json(
                success=False,
                stage="gen_capture_texture_paint_snapshot",
                message=message,
                inputs=inputs,
                outputs={"native_response": raw, "path": str(filepath), "network_required": False, "spend_required": False},
                errors=[message],
                t0=t0,
            )

        render_image: Dict[str, Any] = {"type": "image", "path": str(filepath)}
        warnings: List[str] = []
        if upload_to_tripo:
            try:
                uploaded = await asyncio.to_thread(_tripo_upload_file, str(filepath))
                render_image = {
                    "type": "image",
                    "path": str(filepath),
                    "file_token": uploaded.get("file_token", ""),
                    "trace_id": uploaded.get("trace_id", ""),
                }
            except Exception as exc:
                warnings.append(f"Snapshot captured, but Tripo upload failed: {exc}")

        snapshot = {
            "label": safe_label,
            "path": str(filepath),
            "session_name": safe_session,
            "model_task_id": safe_model_task_id,
            "resolution": [width, height],
            "show_ui": show_ui,
            "created_at": int(time.time()),
            "render_image": render_image,
        }
        update_info = _record_texture_paint_snapshot(
            session_name=safe_session,
            model_task_id=safe_model_task_id,
            snapshot=snapshot,
        )
        if not update_info.get("updated"):
            warnings.append(str(update_info.get("reason") or "Snapshot was not attached to a texture-paint session."))
        return _result_json(
            success=True,
            stage="gen_capture_texture_paint_snapshot",
            message="Captured Texture/Paint viewport snapshot",
            inputs=inputs,
            outputs={
                "snapshot": snapshot,
                "render_image": render_image,
                "native_response": raw,
                "session_update": update_info,
                "network_required": bool(upload_to_tripo),
                "spend_required": False,
            },
            warnings=warnings,
            t0=t0,
        )

    @mcp.tool()
    async def gen_texture_from_prompt(
        ctx: Context,
        prompt: str,
        channels: Optional[List[str]] = None,
        resolution: int = 1024,
        content_path: str = "/Game/Generated",
        asset_name: str = "",
        master_material_path: str = "/Game/Materials/M_Master_GeneratedTexture",
        provider: str = "tripo",
    ) -> str:
        """Plan a prompt-only texture set and material instance handoff.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#texture-only-path
        Example:
            gen_texture_from_prompt(prompt="wet mossy stone", channels=["BaseColor", "Normal", "ORM"], resolution=1024)"""
        t0 = time.monotonic()
        selected_provider = (provider or "tripo").strip().lower() or "tripo"
        channel_state = _normalize_texture_channels(channels)
        resolution_state = _normalize_texture_resolution(resolution)
        safe_prompt = _clean_optional_text(prompt)
        inputs = {
            "prompt": prompt,
            "channels": channels or ["BaseColor", "Normal", "ORM"],
            "resolution": resolution,
            "content_path": content_path,
            "asset_name": asset_name,
            "master_material_path": master_material_path,
            "provider": selected_provider,
        }
        if not safe_prompt:
            return _result_json(
                success=False,
                stage="gen_texture_from_prompt",
                message="prompt is required",
                inputs=inputs,
                errors=["prompt is required"],
                t0=t0,
            )
        if channel_state["invalid_channels"] or not channel_state["channels"]:
            return _result_json(
                success=False,
                stage="gen_texture_from_prompt",
                message="Unsupported texture channel requested",
                inputs=inputs,
                outputs={"channel_state": channel_state},
                errors=[f"Unsupported texture channel(s): {', '.join(channel_state['invalid_channels'])}"],
                t0=t0,
            )
        if not resolution_state["valid"]:
            allowed = ", ".join(str(item) for item in resolution_state["allowed_resolutions"])
            return _result_json(
                success=False,
                stage="gen_texture_from_prompt",
                message="Unsupported texture resolution requested",
                inputs=inputs,
                outputs={"resolution_state": resolution_state},
                errors=[f"resolution must be one of: {allowed}"],
                t0=t0,
            )
        try:
            provider_obj = _PROVIDERS.get(selected_provider)
        except KeyError as exc:
            return _result_json(
                success=False,
                stage="gen_texture_from_prompt",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        material_plan = _texture_from_prompt_plan(
            prompt=safe_prompt,
            channels=channel_state["channels"],
            resolution=resolution_state["resolution"],
            content_path=content_path,
            asset_name=asset_name,
            master_material_path=master_material_path,
        )
        support = provider_obj.texture_from_prompt_status()
        if not provider_obj.supports_texture_from_prompt():
            return _result_json(
                success=False,
                stage="gen_texture_from_prompt",
                message="Standalone prompt-to-texture generation is not supported by the selected provider",
                inputs=inputs,
                outputs={
                    "provider_support": support,
                    "requested_texture_set": {
                        "prompt": safe_prompt,
                        "channels": channel_state["channels"],
                        "resolution": resolution_state["resolution"],
                    },
                    "materialization_plan": material_plan,
                    "network_required": False,
                    "tripo_model_task_alternative": {
                        "tool": "gen_tripo_texture_model",
                        "requires": "original_model_task_id",
                    },
                },
                warnings=[
                    "No paid provider request was sent.",
                    "Use the material_tool_handoff once a future texture provider supplies Texture2D assets.",
                ],
                errors=[str(support.get("reason", "Provider does not support prompt-only texture generation."))],
                t0=t0,
            )

        return _result_json(
            success=False,
            stage="gen_texture_from_prompt",
            message="Provider support is declared, but no texture provider transport is wired yet",
            inputs=inputs,
            outputs={"provider_support": support, "materialization_plan": material_plan},
            errors=["Texture provider transport is not implemented."],
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
        smart_low_poly: bool = True,
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
        return await asyncio.to_thread(
            _submit_guarded_tripo_task,
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
        smart_low_poly: bool = True,
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
            payload["file"] = await asyncio.to_thread(
                _as_file_object,
                image_path=image_path,
                image_url=image_url,
                file_token=file_token,
            )
            task_response = await asyncio.to_thread(_tripo_submit_task, payload)
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
        smart_low_poly: bool = True,
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
                    file_objects.append(await asyncio.to_thread(
                        _as_file_object,
                        image_path=item.get("image_path", ""),
                        image_url=item.get("image_url", ""),
                        file_token=item.get("file_token", ""),
                    ))
                while len(file_objects) < 4:
                    file_objects.append({"type": "image"})
                payload["files"] = file_objects
            task_response = await asyncio.to_thread(_tripo_submit_task, payload)
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
        return await asyncio.to_thread(
            _submit_guarded_tripo_task,
            stage="gen_tripo_refine_model",
            inputs=inputs,
            payload=payload,
            estimated_credits=_estimate_tripo_credits("refine_model", payload),
            session_name=session_name,
            confirm_spend=confirm_spend,
            t0=t0,
        )

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
        return await asyncio.to_thread(
            _submit_guarded_tripo_task,
            stage="gen_tripo_texture_model",
            inputs=inputs,
            payload=payload,
            estimated_credits=_estimate_tripo_credits("texture_model", payload),
            session_name=session_name,
            confirm_spend=confirm_spend,
            t0=t0,
        )

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
        return await asyncio.to_thread(
            _submit_guarded_tripo_task,
            stage="gen_tripo_post_process",
            inputs=inputs,
            payload=payload,
            estimated_credits=_estimate_tripo_credits("convert_model", payload),
            session_name=session_name,
            confirm_spend=confirm_spend,
            t0=t0,
        )

    @mcp.tool()
    async def gen_tripo_get_task_status(ctx: Context, task_id: str) -> str:
        """Get Tripo task status and output URLs.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#tripo-task-family
        Example:
            gen_tripo_get_task_status(task_id="model-task-id")"""
        t0 = time.monotonic()
        inputs = {"task_id": task_id}
        try:
            result = await asyncio.to_thread(_tripo_get_task, task_id)
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
                result = await asyncio.to_thread(_tripo_get_task, task_id)
                task = result["task"]
                snapshots.append({"status": task.get("status"), "progress": task.get("progress"), "running_left_time": task.get("running_left_time")})
                if task.get("status") in _TRIPO_FINAL_STATUSES:
                    return _result_json(success=task.get("status") == "success", stage="gen_tripo_wait_for_task", message=f"Tripo task finalized: {task.get('status')}", inputs=inputs, outputs={"task": task, "snapshots": snapshots}, errors=[] if task.get("status") == "success" else [f"Tripo task finalized as {task.get('status')}"], t0=t0)
                if time.monotonic() >= deadline:
                    return _result_json(success=False, stage="gen_tripo_wait_for_task", message="Timed out waiting for Tripo task", inputs=inputs, outputs={"snapshots": snapshots}, errors=["Timed out waiting for Tripo task"], t0=t0)
                await asyncio.sleep(max(1, int(poll_s)))
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
            result = await asyncio.to_thread(_tripo_get_task, task_id)
            task = result["task"]
            if task.get("status") != "success":
                return _result_json(success=False, stage="gen_tripo_download_result", message=f"Task is not successful: {task.get('status')}", inputs=inputs, outputs={"task": task}, errors=[f"Task is not successful: {task.get('status')}"], t0=t0)
            output = task.get("output") if isinstance(task.get("output"), dict) else {}
            downloads = await asyncio.to_thread(
                _download_tripo_output_files,
                task_id=task_id,
                output=output,
                target_folder=Path(target_folder),
                output_keys=keys,
            )
            return _result_json(success=bool(downloads), stage="gen_tripo_download_result", message=f"Downloaded {len(downloads)} Tripo output file(s)", inputs=inputs, outputs={"task_id": task_id, "downloads": downloads, "source_output": output}, errors=[] if downloads else ["No requested output URLs were available to download"], t0=t0)
        except Exception as exc:
            return _result_json(success=False, stage="gen_tripo_download_result", message=str(exc), inputs=inputs, errors=[str(exc)], t0=t0)

    @mcp.tool()
    async def gen_tripo_import_to_project(
        ctx: Context,
        task_id: str,
        content_path: str = "/Game/Generated",
        create_material_instance: bool = True,
        create_blueprint: bool = False,
        target_folder: str = "",
        asset_name: str = "",
        output_keys: Optional[List[str]] = None,
        overwrite_existing: bool = False,
        capture_thumbnail: bool = True,
    ) -> str:
        """Download a successful Tripo task result, import it, and capture viewport evidence.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#auto-import-bridge
        Example:
            gen_tripo_import_to_project(task_id="model-task-id", content_path="/Game/Generated/Enemies", create_material_instance=True)"""
        t0 = time.monotonic()
        keys = output_keys or list(_TRIPO_IMPORT_OUTPUT_KEYS)
        safe_content_path = _normalize_content_folder(content_path)
        inputs = {
            "task_id": task_id,
            "content_path": safe_content_path,
            "create_material_instance": create_material_instance,
            "create_blueprint": create_blueprint,
            "target_folder": target_folder,
            "asset_name": asset_name,
            "output_keys": keys,
            "overwrite_existing": overwrite_existing,
            "capture_thumbnail": capture_thumbnail,
        }
        try:
            task_result = await asyncio.to_thread(_tripo_get_task, task_id)
            task = task_result["task"]
            if task.get("status") != "success":
                return _result_json(
                    success=False,
                    stage="gen_tripo_import_to_project",
                    message=f"Task is not successful: {task.get('status')}",
                    inputs=inputs,
                    outputs={"task": task, "trace_id": task_result.get("trace_id", "")},
                    errors=[f"Task is not successful: {task.get('status')}"],
                    t0=t0,
                )

            output = task.get("output") if isinstance(task.get("output"), dict) else {}
            download_folder = Path(target_folder) if target_folder else _default_tripo_download_folder(task_id)
            downloads = await asyncio.to_thread(
                _download_tripo_output_files,
                task_id=task_id,
                output=output,
                target_folder=download_folder,
                output_keys=keys,
            )
            primary_model = _select_primary_model_download(downloads)
            if not primary_model:
                return _result_json(
                    success=False,
                    stage="gen_tripo_import_to_project",
                    message="No downloaded Tripo model output was available for import",
                    inputs=inputs,
                    outputs={"task": task, "downloads": downloads, "source_output": output},
                    errors=["No downloaded output had a supported StaticMesh extension."],
                    t0=t0,
                )

            local_files = [item["path"] for item in downloads if item.get("path")]
            requested_asset_name = asset_name or Path(str(primary_model["path"])).stem
            manifest_inputs = {
                "task_id": task_id,
                "local_files": local_files,
                "content_path": safe_content_path,
                "asset_name": requested_asset_name,
                "provider": "tripo",
                "create_material_instance": create_material_instance,
                "create_blueprint": create_blueprint,
                "overwrite_existing": overwrite_existing,
            }
            manifest_raw = await asyncio.to_thread(_send, "gen_prepare_import_manifest", manifest_inputs)
            manifest_failed = manifest_raw.get("success") is False or manifest_raw.get("status") == "error" or bool(manifest_raw.get("error"))
            if manifest_failed:
                message = manifest_raw.get("error") or manifest_raw.get("message") or "Import manifest preparation failed"
                return _result_json(
                    success=False,
                    stage="gen_tripo_import_to_project",
                    message=message,
                    inputs=inputs,
                    outputs={"task": task, "downloads": downloads, "manifest_response": manifest_raw},
                    errors=[message],
                    t0=t0,
                )
            manifest = manifest_raw.get("manifest", manifest_raw)
            safe_asset_name = str(manifest.get("asset_name") or _safe_name(requested_asset_name, "GeneratedAsset"))

            import_result = await asyncio.to_thread(
                _import_generated_static_mesh,
                file_path=str(primary_model["path"]),
                content_path=safe_content_path,
                asset_name=safe_asset_name,
                create_material_instance=create_material_instance,
                create_blueprint=create_blueprint,
                overwrite_existing=overwrite_existing,
            )
            if not import_result.get("success"):
                return _result_json(
                    success=False,
                    stage="gen_tripo_import_to_project",
                    message=import_result.get("message") or "Generated mesh import failed",
                    inputs=inputs,
                    outputs={"task": task, "downloads": downloads, "manifest": manifest, "import_result": import_result},
                    errors=import_result.get("errors") or [import_result.get("message") or "Generated mesh import failed"],
                    t0=t0,
                )

            thumbnail: Dict[str, Any] = {}
            warnings = list(import_result.get("warnings") or [])
            if capture_thumbnail:
                thumbnail = await asyncio.to_thread(_capture_import_thumbnail, task_id, safe_asset_name)
                if not thumbnail.get("success"):
                    warnings.append("Thumbnail screenshot was requested but could not be captured from the active viewport.")

            import_outputs = import_result.get("outputs", {})
            asset_paths = {
                "primary_asset": import_outputs.get("asset_path") or manifest.get("expected_assets", {}).get("primary_asset", ""),
                "material_instance": import_outputs.get("material_instance", ""),
                "blueprint": import_outputs.get("blueprint", ""),
                "imported_object_paths": import_outputs.get("imported_object_paths", []),
            }
            preview_asset_path = _clean_optional_text(str(asset_paths.get("primary_asset", "")))
            preview_asset_reference = f"@asset:{preview_asset_path}" if preview_asset_path else ""
            workspace_preview_handoff_path = _clean_optional_text(str(import_outputs.get("workspace_preview_handoff_path", "")))
            return _result_json(
                success=True,
                stage="gen_tripo_import_to_project",
                message="Imported Tripo task result into Unreal project",
                inputs=inputs,
                outputs={
                    "task_id": task_id,
                    "task": task,
                    "downloads": downloads,
                    "primary_model": primary_model,
                    "manifest": manifest,
                    "import_result": import_result,
                    "asset_paths": asset_paths,
                    "preview_asset_path": preview_asset_path,
                    "preview_asset_reference": preview_asset_reference,
                    "tripo_workspace_handoff": {
                        "preview_asset_path": preview_asset_path,
                        "preview_asset_reference": preview_asset_reference,
                        "unreal_config_section": "UnrealMCP.TripoWorkspace",
                        "unreal_config_key": "PreviewAssetPath",
                        "handoff_file": "Saved/MCPChat/generative_workspace_preview.json",
                        "handoff_file_path": workspace_preview_handoff_path,
                    },
                    "thumbnail": thumbnail,
                    "trace_id": task_result.get("trace_id", ""),
                },
                warnings=warnings,
                t0=t0,
            )
        except Exception as exc:
            return _result_json(success=False, stage="gen_tripo_import_to_project", message=str(exc), inputs=inputs, errors=[str(exc)], t0=t0)

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
        raw = await asyncio.to_thread(_send, "gen_prepare_import_manifest", inputs)
        return _bridge_result(
            stage="gen_prepare_import_manifest",
            raw=raw,
            inputs=inputs,
            message="Prepared generated asset import manifest",
            t0=t0,
        )

    logger.info("Generative content tools registered")
