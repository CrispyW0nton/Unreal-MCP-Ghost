"""Generative content provider and import pipeline scaffold tools."""

from __future__ import annotations

import json
import logging
import mimetypes
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP
from tools.generative import ProviderRegistry
from tools.generative.tripo import TRIPO_PROVIDER

logger = logging.getLogger("UnrealMCP")

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHAT_DIR = _REPO_ROOT / "Saved" / "MCPChat"
_SECRETS_PATH = _CHAT_DIR / "secrets.json"
_SETTINGS_PATH = _CHAT_DIR / "generative_settings.json"
_TEXTURE_PAINT_SESSIONS_PATH = _CHAT_DIR / "texture_paint_sessions.json"
_TRIPO_TASK_CREDIT_LEDGER_PATH = _CHAT_DIR / "tripo_task_credit_ledger.json"
_PROVIDERS = ProviderRegistry([TRIPO_PROVIDER])
_TRIPO_PROVIDER = _PROVIDERS.get("tripo")
_TRIPO_BASE_URL = _TRIPO_PROVIDER.base_url
_TRIPO_STUDIO_BASE_URL = "https://api.tripo3d.ai"
_TRIPO_FINAL_STATUSES = set(_TRIPO_PROVIDER.final_statuses)
_TRIPO_MODEL_OUTPUT_KEYS = tuple(_TRIPO_PROVIDER.output_policy.model_output_keys)
_TRIPO_IMPORT_OUTPUT_KEYS = tuple(_TRIPO_PROVIDER.output_policy.import_output_keys)
_TRIPO_MODEL_EXTS = set(_TRIPO_PROVIDER.output_policy.model_extensions)
_TRIPO_IMAGE_EXTS = set(_TRIPO_PROVIDER.output_policy.image_extensions)
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


def _clamp_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _normalize_texture_reference(value: str) -> Dict[str, str]:
    reference = _clean_optional_text(value)
    if not reference:
        return {"kind": "none", "value": ""}
    parsed = urllib.parse.urlparse(reference)
    if parsed.scheme in {"http", "https"}:
        return {"kind": "url", "value": reference}
    return {"kind": "path", "value": str(Path(reference))}


def _build_texture_paint_session_plan(
    *,
    model_task_id: str,
    texture_prompt: str,
    texture_reference_image: str,
    viewport_view: str,
    camera_matrix: Optional[List[float]],
    brush_size: float,
    brush_strength: float,
    brush_hardness: float,
    creativity_strength: float,
    paint_mode: str,
    paint_color: str,
    blend_mode: str,
    paint_notes: str,
    save_name: str,
    tripo_project_id: str,
) -> Dict[str, Any]:
    reference = _normalize_texture_reference(texture_reference_image)
    clean_view = _clean_optional_text(viewport_view) or "current"
    clean_mode = (_clean_optional_text(paint_mode) or "image").lower()
    if clean_mode not in {"image", "color"}:
        clean_mode = "image"
    clean_blend = _clean_optional_text(blend_mode) or "normal"
    clean_save_name = _safe_name(save_name or f"{model_task_id}_MagicBrush", "MagicBrushTexture")
    prompt_parts = [texture_prompt]
    if reference["value"]:
        prompt_parts.append(f"use {reference['kind']} reference {reference['value']} as the texture style target")
    if paint_notes:
        prompt_parts.append(f"paint/blend notes: {paint_notes}")
    prompt_parts.append(
        "Magic Brush intent: generate a high-fidelity texture preview from the mesh view, "
        "paint it onto the visible model, rotate the model for coverage, blend seams, then save"
    )
    prompt_parts.append(
        f"view={clean_view}; brush_size={brush_size:.3f}; brush_strength={brush_strength:.2f}; "
        f"brush_hardness={brush_hardness:.2f}; blend_mode={clean_blend}; save_name={clean_save_name}"
    )
    if clean_mode == "color":
        prompt_parts.append(f"paint mode color={paint_color or '#FFFFFF'}")

    session_id = f"magic_brush_{_safe_name(model_task_id, 'model')}_{int(time.time())}"
    prompt_text = "; ".join(part for part in prompt_parts if part)
    plan = {
        "session_id": session_id,
        "provider": "tripo",
        "workspace_route": "https://studio.tripo3d.ai/workspace/texture-edit",
        "studio_tool_name": "Magic Brush",
        "model_task_id": model_task_id,
        "tripo_project_id": tripo_project_id,
        "prompt": prompt_text,
        "texture_reference": reference,
        "viewport": {
            "view": clean_view,
            "camera_matrix": camera_matrix or [],
        },
        "brush": {
            "mode": clean_mode,
            "size": brush_size,
            "strength": brush_strength,
            "hardness": brush_hardness,
            "creativity_strength": creativity_strength,
            "color": paint_color or "#FFFFFF",
            "blend_mode": clean_blend,
            "notes": paint_notes,
        },
        "save": {
            "name": clean_save_name,
            "apply_behavior": "compile painted image parts and apply them as a saved retexture pass",
        },
        "observed_tripo_studio_flow": [
            "Select or upload a textured model in the right Assets panel.",
            "Use Magic Brush Gen Mode with a prompt and creativity strength to generate preview texture images from the current mesh view.",
            "Choose a generated image or Paint Mode color, open the brush bar, adjust size, strength, and hardness.",
            "Paint/blend onto the model, rotate the viewport for coverage, and repeat as needed.",
            "Save applies uploaded painted image parts to the model.",
        ],
        "observed_studio_api_contract": {
            "generate_preview": {
                "endpoint": "/v2/studio/operation/retexture_generate",
                "body_fields": ["camera_matrix", "model_version", "project_id", "prompt", "render_image", "strength"],
                "poll_then_fetch": "/v2/studio/operation/get_retexture",
                "image_history": "/v2/studio/operation/get_retexture_images",
            },
            "save_apply": {
                "endpoint": "/v2/studio/operation/apply_retexture",
                "body_fields": ["image_map", "model_version", "project_id"],
            },
        },
        "mcp_tool_sequence": [
            {
                "tool": "gen_tripo_texture_model",
                "args": {
                    "task_id": model_task_id,
                    "texture_prompt": prompt_text,
                    "model_version": "v3.0-20250812",
                    "texture": True,
                    "pbr": True,
                    "texture_alignment": "original_image",
                    "confirm_spend": False,
                },
            },
            {"tool": "gen_tripo_wait_for_task", "args": {"task_id": "<texture_task_id>", "timeout_s": 900, "poll_s": 10}},
            {"tool": "gen_tripo_import_to_project", "args": {"task_id": "<texture_task_id>", "content_path": "/Game/Generated", "create_material_instance": True}},
            {
                "tool": "gen_record_texture_paint_stroke",
                "args": {
                    "session_id": session_id,
                    "part_name": "Body",
                    "image_bucket": "<painted_texture_bucket>",
                    "image_key": "<painted_texture_key>",
                    "brush_strength": brush_strength,
                    "blend_mode": clean_blend,
                },
            },
            {
                "tool": "gen_compile_texture_paint_image_map",
                "args": {
                    "session_id": session_id,
                    "prefer_latest_per_part": True,
                },
            },
        ],
    }
    return plan


def _save_texture_paint_session(plan: Dict[str, Any]) -> None:
    sessions = _read_json_file(_TEXTURE_PAINT_SESSIONS_PATH)
    items = sessions.get("sessions")
    if not isinstance(items, list):
        items = []
    items.append(plan)
    sessions["sessions"] = items[-50:]
    _write_json_file(_TEXTURE_PAINT_SESSIONS_PATH, sessions)


def _load_texture_paint_sessions() -> Dict[str, Any]:
    sessions = _read_json_file(_TEXTURE_PAINT_SESSIONS_PATH)
    items = sessions.get("sessions")
    sessions["sessions"] = items if isinstance(items, list) else []
    return sessions


def _write_texture_paint_sessions(sessions: Dict[str, Any]) -> None:
    items = sessions.get("sessions")
    sessions["sessions"] = (items if isinstance(items, list) else [])[-50:]
    _write_json_file(_TEXTURE_PAINT_SESSIONS_PATH, sessions)


def _find_texture_paint_session(sessions: Dict[str, Any], session_id: str) -> Optional[Dict[str, Any]]:
    safe_session_id = _clean_optional_text(session_id)
    for session in sessions.get("sessions", []):
        if isinstance(session, dict) and session.get("session_id") == safe_session_id:
            return session
    return None


def _build_magic_brush_image(
    *,
    image_bucket: str = "",
    image_key: str = "",
    image_url: str = "",
    image_file_token: str = "",
) -> Dict[str, Any]:
    bucket = _clean_optional_text(image_bucket)
    key = _clean_optional_text(image_key)
    url = _clean_optional_text(image_url)
    file_token = _clean_optional_text(image_file_token)
    if bucket and key:
        return {"bucket": bucket, "key": key}
    if url:
        return {"url": url}
    if file_token:
        return {"file_token": file_token}
    return {}


def _session_image_map_from_strokes(session: Dict[str, Any]) -> List[Dict[str, Any]]:
    strokes = session.get("paint_strokes")
    if not isinstance(strokes, list):
        return []

    latest_by_part: Dict[str, Dict[str, Any]] = {}
    for stroke in strokes:
        if not isinstance(stroke, dict):
            continue
        part_name = _clean_optional_text(str(stroke.get("part_name", ""))) or "Body"
        image = stroke.get("image")
        if isinstance(image, dict) and image:
            latest_by_part[part_name] = {
                "part_name": part_name,
                "image": image,
            }
    return [latest_by_part[key] for key in sorted(latest_by_part.keys())]


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


def _tripo_json_request(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout_s: int = 60,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    api_key = _get_tripo_api_key()
    if not api_key:
        raise RuntimeError("TRIPO_API_KEY is not configured in the environment or Saved/MCPChat/secrets.json")

    url = f"{base_url or _TRIPO_BASE_URL}{path}"
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


def _tripo_response_data(response: Dict[str, Any], fallback_message: str) -> Dict[str, Any]:
    body = response.get("body", {})
    if response.get("http_status", 0) >= 400 or body.get("code", 0) != 0:
        message = body.get("message") or body.get("suggestion") or fallback_message
        raise RuntimeError(message)
    data = body.get("data", body)
    return {
        "data": data if isinstance(data, dict) else {"value": data},
        "response": body,
        "trace_id": response.get("trace_id", ""),
    }


def _tripo_studio_operation(operation: str, payload: Dict[str, Any], timeout_s: int = 60) -> Dict[str, Any]:
    response = _tripo_json_request(
        "POST",
        f"/v2/studio/operation/{operation}",
        payload=payload,
        timeout_s=timeout_s,
        base_url=_TRIPO_STUDIO_BASE_URL,
    )
    return _tripo_response_data(response, f"Tripo Studio operation failed: {operation}")


def _build_studio_render_image(
    *,
    render_image: Optional[Dict[str, Any]] = None,
    render_image_bucket: str = "",
    render_image_key: str = "",
    render_image_url: str = "",
) -> Dict[str, Any]:
    if isinstance(render_image, dict) and render_image:
        return dict(render_image)
    bucket = _clean_optional_text(render_image_bucket)
    key = _clean_optional_text(render_image_key)
    url = _clean_optional_text(render_image_url)
    if bucket and key:
        return {"bucket": bucket, "key": key}
    if url:
        return {"url": url}
    return {}


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


def _tripo_get_wallet_balance(timeout_s: int = 30) -> Dict[str, Any]:
    response = _tripo_json_request("GET", "/user/balance", timeout_s=timeout_s)
    body = response.get("body") if isinstance(response.get("body"), dict) else {}
    if response.get("http_status", 0) >= 400 or body.get("code", 0) not in (0, "0", None):
        message = body.get("message") or body.get("suggestion") or f"Tripo wallet balance request failed with HTTP {response.get('http_status')}"
        raise RuntimeError(str(message))
    data = body.get("data") if isinstance(body.get("data"), dict) else body
    return {
        "balance": max(0, _safe_int(data.get("balance"), 0)),
        "frozen": max(0, _safe_int(data.get("frozen"), 0)),
        "http_status": response.get("http_status"),
        "trace_id": response.get("trace_id", ""),
        "raw_response": body,
    }


def _find_runuat(engine_root: str = "") -> str:
    roots = [engine_root] if engine_root else [
        r"C:\Program Files\Epic Games\UE_5.6",
        r"C:\Program Files\Epic Games\UE_5.5",
        r"C:\Program Files\Epic Games\UE_5.4",
    ]
    for root in roots:
        if not root:
            continue
        candidate = Path(root) / "Engine" / "Build" / "BatchFiles" / "RunUAT.bat"
        if candidate.exists():
            return str(candidate)
    return ""


def _latest_plugin_package(package_root: Path) -> Dict[str, Any]:
    if not package_root.exists():
        return {"found": False, "path": "", "has_descriptor": False, "has_win64_binaries": False}

    candidates = sorted(
        [path for path in package_root.glob("UnrealMCPBuild*") if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        descriptor = candidate / "UnrealMCP.uplugin"
        binaries = candidate / "Binaries" / "Win64"
        if descriptor.exists() or binaries.exists():
            return {
                "found": descriptor.exists() and binaries.exists(),
                "path": str(candidate),
                "has_descriptor": descriptor.exists(),
                "has_win64_binaries": binaries.exists(),
            }
    return {"found": False, "path": "", "has_descriptor": False, "has_win64_binaries": False}


def _check_bridge_reachable(host: str, port: int, timeout_s: float) -> Dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=max(0.01, timeout_s)):
            return {"reachable": True, "host": host, "port": port}
    except Exception as exc:
        return {"reachable": False, "host": host, "port": port, "error": str(exc)}


def _readiness_gate(
    gate_id: str,
    label: str,
    passed: bool,
    observed: Optional[List[str]] = None,
    missing: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "id": gate_id,
        "label": label,
        "status": "ready" if passed else "missing",
        "observed": observed or [],
        "missing": missing or [],
    }


def _build_generate_asset_preflight(
    *,
    mode: str,
    session_name: str,
    estimated_credits: int,
    engine_root: str,
    package_root: str,
    bridge_host: str,
    bridge_port: int,
    bridge_timeout_s: float,
) -> Dict[str, Any]:
    safe_mode = (mode or "text_to_model").strip() or "text_to_model"
    safe_session = (session_name or "default").strip() or "default"
    safe_estimate = max(0, _safe_int(estimated_credits, 0))
    supported_modes = {"text_to_model", "image_to_model", "multiview_to_model", "texture_model"}
    settings = _load_generative_settings()
    key_state = _resolve_tripo_api_key()
    budget = max(0, _safe_int(settings.get("session_credit_budget"), 0))
    usage = settings.setdefault("credit_usage_by_session", {})
    used = max(0, _safe_int(usage.get(safe_session), 0))
    remaining = max(0, budget - used)
    runuat = _find_runuat(engine_root or os.environ.get("UE_ENGINE_ROOT", ""))
    wrapper = _REPO_ROOT / "scripts" / "build_unreal_plugin.ps1"
    plugin = _REPO_ROOT / "unreal_plugin" / "UnrealMCP.uplugin"
    package = _latest_plugin_package(Path(package_root or r"C:\uebuild"))
    safe_bridge_port = _safe_int(bridge_port, 55557)
    bridge = _check_bridge_reachable(bridge_host or "127.0.0.1", safe_bridge_port, bridge_timeout_s)
    smart_mesh_required = safe_mode in {"text_to_model", "image_to_model", "multiview_to_model"}
    smart_mesh_ready = True

    gates = [
        _readiness_gate(
            "tripo_api_key",
            "Tripo API key is configured without exposing the secret",
            bool(key_state["configured"]),
            [key_state["source"]] if key_state["configured"] else [],
            ["TRIPO_API_KEY env var or Saved/MCPChat/secrets.json"] if not key_state["configured"] else [],
        ),
        _readiness_gate(
            "mode_supported",
            "Generate Asset mode is supported by the Tripo workspace",
            safe_mode in supported_modes,
            [safe_mode] if safe_mode in supported_modes else [],
            [f"mode must be one of {', '.join(sorted(supported_modes))}"] if safe_mode not in supported_modes else [],
        ),
        _readiness_gate(
            "credit_budget",
            "Session credit budget can cover the estimated Generate Asset spend",
            remaining >= safe_estimate and budget > 0,
            [f"budget={budget}", f"used={used}", f"remaining={remaining}", f"estimated={safe_estimate}"],
            [f"remaining credits < estimated credits ({remaining} < {safe_estimate})"] if remaining < safe_estimate else [],
        ),
        _readiness_gate(
            "smart_mesh_policy",
            "Smart Mesh/good topology policy is enforced for model generation",
            smart_mesh_ready,
            ["smart_low_poly=true for text/image/multi-image model generation"] if smart_mesh_required else ["texture_model reuses an existing model task"],
            [],
        ),
        _readiness_gate(
            "unreal_build_tooling",
            "UE BuildPlugin tooling and wrapper are available",
            bool(runuat) and wrapper.exists() and plugin.exists(),
            [item for item in (runuat, str(wrapper) if wrapper.exists() else "", str(plugin) if plugin.exists() else "") if item],
            [
                item for item, ok in (
                    ("RunUAT.bat", bool(runuat)),
                    ("scripts/build_unreal_plugin.ps1", wrapper.exists()),
                    ("unreal_plugin/UnrealMCP.uplugin", plugin.exists()),
                ) if not ok
            ],
        ),
        _readiness_gate(
            "packaged_plugin",
            "A packaged Win64 UnrealMCP plugin build is available",
            bool(package["found"]),
            [package["path"]] if package["found"] else [],
            [
                item for item, ok in (
                    ("packaged UnrealMCP.uplugin", package["has_descriptor"]),
                    ("packaged Binaries/Win64", package["has_win64_binaries"]),
                ) if not ok
            ],
        ),
        _readiness_gate(
            "unreal_bridge",
            "Unreal MCP bridge socket is reachable for import/viewport follow-up",
            bool(bridge["reachable"]),
            [f"{bridge['host']}:{bridge['port']}"] if bridge["reachable"] else [],
            [f"{bridge['host']}:{bridge['port']}"] if not bridge["reachable"] else [],
        ),
    ]
    ready_for_live_spend = all(item["status"] == "ready" for item in gates)
    next_actions = [f"{item['id']}: {', '.join(item['missing'])}" for item in gates if item["status"] != "ready"]
    return {
        "schema": "unreal_mcp_generate_asset_live_preflight.v1",
        "ready_for_live_spend": ready_for_live_spend,
        "network_required": False,
        "spend_required": False,
        "repo_root": str(_REPO_ROOT),
        "settings": {
            "settings_path": str(_SETTINGS_PATH),
            "output_folder": settings.get("output_folder", ""),
            "default_model_version": settings.get("default_model_version", ""),
            "default_texture_quality": settings.get("default_texture_quality", ""),
            "session_name": safe_session,
            "session_credit_budget": budget,
            "session_credits_used": used,
            "session_credits_remaining": remaining,
            "estimated_credits": safe_estimate,
        },
        "api_key": key_state,
        "build": {"runuat": runuat, "wrapper": str(wrapper), "plugin": str(plugin), "package": package},
        "bridge": bridge,
        "workspace": {
            "mode": safe_mode,
            "supported_modes": sorted(supported_modes),
            "smart_mesh_required": smart_mesh_required,
            "smart_low_poly_default": True,
            "wallet_tool": "gen_tripo_get_wallet_balance",
            "proof_tool": "gen_compile_generate_asset_evidence",
            "paid_tools": {
                "text_to_model": "gen_tripo_text_to_model",
                "image_to_model": "gen_tripo_image_to_model",
                "multiview_to_model": "gen_tripo_multiview_to_model",
                "texture_model": "gen_tripo_texture_model",
            },
            "texture_paint_tools": [
                "gen_prepare_texture_paint_session",
                "gen_tripo_magic_brush_generate",
                "gen_tripo_magic_brush_get_retexture",
                "gen_tripo_magic_brush_list_images",
                "gen_record_texture_paint_stroke",
                "gen_compile_texture_paint_image_map",
                "gen_tripo_magic_brush_apply",
            ],
        },
        "gates": gates,
        "next_actions": next_actions,
    }


def _coerce_json_object(value: Any, field_name: str, warnings: List[str]) -> Dict[str, Any]:
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            warnings.append(f"{field_name} was not valid JSON: {exc.msg}")
            return {}
        if isinstance(parsed, dict):
            return parsed
    warnings.append(f"{field_name} did not contain a JSON object")
    return {}


def _nested_dict(value: Any, *keys: str) -> Dict[str, Any]:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _extract_generated_asset_task(task_result: Dict[str, Any], import_result: Dict[str, Any]) -> Dict[str, Any]:
    task = _nested_dict(task_result, "outputs", "task")
    if not task:
        task = _nested_dict(import_result, "outputs", "task")
    return task


def _extract_generated_asset_task_id(task: Dict[str, Any], task_result: Dict[str, Any], import_result: Dict[str, Any]) -> str:
    for candidate in (
        task.get("task_id"),
        _nested_dict(task_result, "inputs").get("task_id"),
        _nested_dict(task_result, "outputs").get("task_id"),
        _nested_dict(import_result, "inputs").get("task_id"),
        _nested_dict(import_result, "outputs").get("task_id"),
    ):
        if _clean_optional_text(str(candidate or "")):
            return str(candidate)
    return ""


def _extract_generated_asset_paths(import_result: Dict[str, Any], asset_name: str, content_path: str) -> Dict[str, Any]:
    outputs = _nested_dict(import_result, "outputs")
    asset_paths = outputs.get("asset_paths")
    if not isinstance(asset_paths, dict):
        asset_paths = {}
    import_outputs = _nested_dict(outputs, "import_result", "outputs")
    manifest_expected = _nested_dict(outputs, "manifest", "expected_assets")
    primary_asset = (
        asset_paths.get("primary_asset")
        or import_outputs.get("asset_path")
        or manifest_expected.get("primary_asset")
        or ""
    )
    if not primary_asset and _clean_optional_text(asset_name):
        primary_asset = f"{_normalize_content_folder(content_path)}/{_safe_name(asset_name, 'GeneratedAsset')}"
    return {
        "primary_asset": primary_asset,
        "material_instance": asset_paths.get("material_instance") or import_outputs.get("material_instance") or "",
        "blueprint": asset_paths.get("blueprint") or import_outputs.get("blueprint") or "",
        "imported_object_paths": asset_paths.get("imported_object_paths") or import_outputs.get("imported_object_paths") or [],
    }


def _extract_visual_evidence(import_result: Dict[str, Any], screenshot_result: Dict[str, Any]) -> Dict[str, Any]:
    thumbnail = _nested_dict(import_result, "outputs", "thumbnail")
    screenshot_outputs = _nested_dict(screenshot_result, "outputs")
    screenshot = screenshot_outputs if screenshot_outputs else screenshot_result
    thumbnail_path = str(thumbnail.get("path") or thumbnail.get("filepath") or "")
    screenshot_path = str(
        screenshot.get("path")
        or screenshot.get("filepath")
        or screenshot.get("filename")
        or screenshot.get("screenshot_path")
        or ""
    )
    return {
        "thumbnail": thumbnail,
        "screenshot": screenshot if isinstance(screenshot, dict) else {},
        "thumbnail_path": thumbnail_path,
        "screenshot_path": screenshot_path,
        "has_visual_evidence": bool(thumbnail_path or screenshot_path),
    }


def _validation_success(validation_result: Dict[str, Any]) -> bool:
    if not validation_result:
        return False
    outputs = _nested_dict(validation_result, "outputs")
    return bool(
        validation_result.get("success") is True
        or outputs.get("exists") is True
        or outputs.get("asset_exists") is True
        or outputs.get("validated") is True
    )


def _build_generate_asset_evidence(
    *,
    task_result: Dict[str, Any],
    import_result: Dict[str, Any],
    validation_result: Dict[str, Any],
    screenshot_result: Dict[str, Any],
    session_name: str,
    asset_name: str,
    content_path: str,
) -> Dict[str, Any]:
    safe_session = (session_name or "default").strip() or "default"
    safe_content_path = _normalize_content_folder(content_path)
    task = _extract_generated_asset_task(task_result, import_result)
    task_id = _extract_generated_asset_task_id(task, task_result, import_result)
    asset_paths = _extract_generated_asset_paths(import_result, asset_name, safe_content_path)
    visual = _extract_visual_evidence(import_result, screenshot_result)
    credit_reconciliation = _nested_dict(task_result, "outputs", "credit_reconciliation")
    credit_guard = _nested_dict(task_result, "outputs", "credit_guard")
    if not credit_guard:
        credit_guard = _nested_dict(import_result, "outputs", "credit_guard")
    import_success = bool(import_result.get("success") is True and asset_paths.get("primary_asset"))
    validation_ready = _validation_success(validation_result)
    credit_ready = bool(credit_reconciliation.get("available") is True or credit_guard.get("approved") is True or credit_guard.get("reserved") is True)
    gates = [
        _readiness_gate(
            "tripo_task_final_success",
            "Tripo task reached final success before import",
            task.get("status") == "success",
            [f"task_id={task_id}", "status=success"] if task.get("status") == "success" else [f"status={task.get('status', 'unknown')}"],
            ["gen_tripo_wait_for_task success result"] if task.get("status") != "success" else [],
        ),
        _readiness_gate(
            "credit_reconciled",
            "Tripo credit guard or consumed-credit reconciliation is present",
            credit_ready,
            [json.dumps(item, sort_keys=True) for item in (credit_reconciliation or credit_guard,) if item],
            ["credit_reconciliation or credit_guard from Tripo task result"] if not credit_ready else [],
        ),
        _readiness_gate(
            "import_asset_paths",
            "Generated StaticMesh import returned a primary Unreal asset path",
            import_success,
            [str(asset_paths.get("primary_asset"))] if asset_paths.get("primary_asset") else [],
            ["gen_tripo_import_to_project primary_asset"] if not import_success else [],
        ),
        _readiness_gate(
            "import_validation",
            "Imported Unreal asset was validated after import",
            validation_ready,
            [json.dumps(_nested_dict(validation_result, "outputs"), sort_keys=True)] if validation_ready else [],
            ["validate_import_result for the imported primary asset"] if not validation_ready else [],
        ),
        _readiness_gate(
            "visual_evidence",
            "Thumbnail or viewport screenshot exists for review",
            bool(visual["has_visual_evidence"]),
            [path for path in (visual["thumbnail_path"], visual["screenshot_path"]) if path],
            ["thumbnail from gen_tripo_import_to_project or viewport_capture_screenshot"] if not visual["has_visual_evidence"] else [],
        ),
    ]
    next_actions = []
    for gate in gates:
        if gate["status"] == "ready":
            continue
        if gate["id"] == "tripo_task_final_success":
            next_actions.append("Run gen_tripo_wait_for_task until the task status is success.")
        elif gate["id"] == "credit_reconciled":
            next_actions.append("Use the task result with credit_guard or poll status until consumed_credit reconciliation is available.")
        elif gate["id"] == "import_asset_paths":
            next_actions.append("Run gen_tripo_import_to_project with content_path and asset_name.")
        elif gate["id"] == "import_validation":
            next_actions.append("Run validate_import_result for the imported primary asset.")
        elif gate["id"] == "visual_evidence":
            next_actions.append("Capture a thumbnail during import or run viewport_capture_screenshot.")
    proven = all(gate["status"] == "ready" for gate in gates)
    return {
        "schema": "unreal_mcp_generate_asset_evidence.v1",
        "proven": proven,
        "network_required": False,
        "spend_required": False,
        "session_name": safe_session,
        "asset_name": asset_name,
        "content_path": safe_content_path,
        "task_id": task_id,
        "task_status": task.get("status", ""),
        "asset_paths": asset_paths,
        "credit_reconciliation": credit_reconciliation,
        "credit_guard": credit_guard,
        "validation": validation_result,
        "visual_evidence": visual,
        "gates": gates,
        "next_actions": next_actions,
    }


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


def _load_tripo_task_credit_ledger() -> Dict[str, Any]:
    ledger = _read_json_file(_TRIPO_TASK_CREDIT_LEDGER_PATH)
    tasks = ledger.get("tasks")
    ledger["tasks"] = tasks if isinstance(tasks, dict) else {}
    return ledger


def _write_tripo_task_credit_ledger(ledger: Dict[str, Any]) -> None:
    tasks = ledger.get("tasks")
    if isinstance(tasks, dict) and len(tasks) > 250:
        ordered = sorted(
            tasks.items(),
            key=lambda item: _safe_int(item[1].get("updated_at") if isinstance(item[1], dict) else 0, 0),
            reverse=True,
        )
        ledger["tasks"] = dict(ordered[:250])
    else:
        ledger["tasks"] = tasks if isinstance(tasks, dict) else {}
    _write_json_file(_TRIPO_TASK_CREDIT_LEDGER_PATH, ledger)


def _record_tripo_task_credit_ledger(task_id: str, credit_guard: Dict[str, Any]) -> Dict[str, Any]:
    safe_task_id = _clean_optional_text(task_id)
    if not safe_task_id:
        return {}
    ledger = _load_tripo_task_credit_ledger()
    tasks = ledger.setdefault("tasks", {})
    existing = tasks.get(safe_task_id)
    if not isinstance(existing, dict):
        existing = {}
    now = int(time.time())
    existing.update({
        "task_id": safe_task_id,
        "provider": "tripo",
        "session_name": str(credit_guard.get("session_name") or "default"),
        "operation": str(credit_guard.get("operation") or ""),
        "estimated_credits": max(0, _safe_int(credit_guard.get("estimated_credits"), 0)),
        "reserved": bool(credit_guard.get("reserved")),
        "submitted_at": existing.get("submitted_at") or now,
        "updated_at": now,
    })
    tasks[safe_task_id] = existing
    _write_tripo_task_credit_ledger(ledger)
    return existing


def _extract_task_consumed_credits(task: Dict[str, Any]) -> Optional[int]:
    for key in ("consumed_credit", "consumed_credits", "credit_consumed"):
        if key in task and task.get(key) not in (None, ""):
            value = _safe_int(task.get(key), -1)
            return max(0, value) if value >= 0 else None
    return None


def _reconcile_tripo_task_credit_usage(task: Dict[str, Any]) -> Dict[str, Any]:
    task_id = _clean_optional_text(str(task.get("task_id") or task.get("id") or ""))
    consumed = _extract_task_consumed_credits(task)
    if not task_id:
        return {"available": False, "reason": "task_id_missing"}
    if consumed is None:
        return {"available": False, "task_id": task_id, "reason": "consumed_credit_missing"}

    ledger = _load_tripo_task_credit_ledger()
    tasks = ledger.setdefault("tasks", {})
    record = tasks.get(task_id)
    if not isinstance(record, dict):
        return {"available": False, "task_id": task_id, "consumed_credits": consumed, "reason": "task_not_in_local_credit_ledger"}

    already_reconciled = bool(record.get("reconciled"))
    previous_consumed = _safe_int(record.get("consumed_credits"), -1)
    if already_reconciled and previous_consumed == consumed:
        settings = _load_generative_settings()
        usage = settings.setdefault("credit_usage_by_session", {})
        session_name = str(record.get("session_name") or "default")
        return {
            "available": True,
            "task_id": task_id,
            "session_name": session_name,
            "estimated_credits": max(0, _safe_int(record.get("estimated_credits"), 0)),
            "consumed_credits": consumed,
            "delta": 0,
            "already_reconciled": True,
            "used_after": max(0, _safe_int(usage.get(session_name), 0)),
            "settings_path": str(_SETTINGS_PATH),
        }

    settings = _load_generative_settings()
    usage = settings.setdefault("credit_usage_by_session", {})
    session_name = str(record.get("session_name") or "default")
    estimated = max(0, _safe_int(record.get("estimated_credits"), 0))
    baseline = previous_consumed if already_reconciled and previous_consumed >= 0 else estimated
    delta = consumed - baseline
    used_before = max(0, _safe_int(usage.get(session_name), 0))
    used_after = max(0, used_before + delta)
    usage[session_name] = used_after
    settings["credit_usage_by_session"] = usage
    _write_json_file(_SETTINGS_PATH, settings)

    now = int(time.time())
    record.update({
        "consumed_credits": consumed,
        "reconciled": True,
        "reconciled_at": now,
        "updated_at": now,
        "last_delta": delta,
        "used_before": used_before,
        "used_after": used_after,
    })
    tasks[task_id] = record
    _write_tripo_task_credit_ledger(ledger)
    return {
        "available": True,
        "task_id": task_id,
        "session_name": session_name,
        "estimated_credits": estimated,
        "consumed_credits": consumed,
        "delta": delta,
        "already_reconciled": False,
        "used_before": used_before,
        "used_after": used_after,
        "settings_path": str(_SETTINGS_PATH),
        "ledger_path": str(_TRIPO_TASK_CREDIT_LEDGER_PATH),
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
    task_id = str(task_response["task_id"])
    credit_record = _record_tripo_task_credit_ledger(task_id, credit_guard)
    return _result_json(
        success=True,
        stage=stage,
        message=f"Submitted Tripo {payload['type']} task",
        inputs=inputs,
        outputs={
            "provider": "tripo",
            "task_id": task_id,
            "request": payload,
            "credit_guard": credit_guard,
            "credit_record": credit_record,
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
"""
    exec_structured = _get_substrate()
    return exec_structured(user_code, "gen_tripo_import_to_project")



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
        "credit_reconciliation_ledger_path": str(_TRIPO_TASK_CREDIT_LEDGER_PATH),
        "network_required": False,
        "spend_confirmation_required": True,
    }


def _provider_scaffold() -> List[Dict[str, Any]]:
    config = _provider_config_outputs()
    return [provider.describe(config) for provider in _PROVIDERS.list()]


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
            outputs.pop("credit_reconciliation_ledger_path", None)
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
    async def gen_tripo_get_wallet_balance(
        ctx: Context,
        timeout_s: int = 30,
    ) -> str:
        """Read the live Tripo API wallet balance without spending credits.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#cost-guard
        Example:
            gen_tripo_get_wallet_balance(timeout_s=30)"""
        t0 = time.monotonic()
        inputs = {"timeout_s": timeout_s}
        try:
            balance = _tripo_get_wallet_balance(timeout_s=timeout_s)
            return _result_json(
                success=True,
                stage="gen_tripo_get_wallet_balance",
                message="Loaded live Tripo wallet balance",
                inputs=inputs,
                outputs={
                    "provider": "tripo",
                    "wallet": {
                        "balance": balance["balance"],
                        "frozen": balance["frozen"],
                    },
                    "network_required": True,
                    "spend_required": False,
                    "trace_id": balance.get("trace_id", ""),
                    "raw_response": balance.get("raw_response", {}),
                },
                t0=t0,
            )
        except Exception as exc:
            return _result_json(
                success=False,
                stage="gen_tripo_get_wallet_balance",
                message=str(exc),
                inputs=inputs,
                outputs={"provider": "tripo", "network_required": True, "spend_required": False},
                errors=[str(exc)],
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
    async def gen_generate_asset_preflight(
        ctx: Context,
        mode: str = "text_to_model",
        session_name: str = "default",
        estimated_credits: int = 60,
        engine_root: str = "",
        package_root: str = r"C:\uebuild",
        bridge_host: str = "127.0.0.1",
        bridge_port: int = 55557,
        bridge_timeout_s: float = 1.0,
    ) -> str:
        """Run a no-spend readiness check for the Unreal Generate Asset workspace.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#d9-chat-dock-integration
        Example:
            gen_generate_asset_preflight(mode="multiview_to_model", session_name="demo", estimated_credits=80)"""
        t0 = time.monotonic()
        inputs = {
            "mode": mode,
            "session_name": session_name,
            "estimated_credits": estimated_credits,
            "engine_root": engine_root,
            "package_root": package_root,
            "bridge_host": bridge_host,
            "bridge_port": bridge_port,
            "bridge_timeout_s": bridge_timeout_s,
        }
        preflight = _build_generate_asset_preflight(
            mode=mode,
            session_name=session_name,
            estimated_credits=estimated_credits,
            engine_root=engine_root,
            package_root=package_root,
            bridge_host=bridge_host,
            bridge_port=bridge_port,
            bridge_timeout_s=bridge_timeout_s,
        )
        ready = bool(preflight.get("ready_for_live_spend"))
        return _result_json(
            success=ready,
            stage="gen_generate_asset_preflight",
            message="Generate Asset preflight is ready for confirmed spend" if ready else "Generate Asset preflight found missing readiness gates",
            inputs=inputs,
            outputs={"preflight": preflight},
            warnings=[] if ready else list(preflight.get("next_actions", [])),
            t0=t0,
        )

    @mcp.tool()
    async def gen_compile_generate_asset_evidence(
        ctx: Context,
        task_result_json: str = "",
        import_result_json: str = "",
        validation_result_json: str = "",
        screenshot_result_json: str = "",
        session_name: str = "default",
        asset_name: str = "",
        content_path: str = "/Game/Generated",
    ) -> str:
        """Compile no-spend proof that a generated Tripo asset reached Unreal.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#auto-import-bridge
        Example:
            gen_compile_generate_asset_evidence(task_result_json="<gen_tripo_wait_for_task JSON>", import_result_json="<gen_tripo_import_to_project JSON>", validation_result_json="<validate_import_result JSON>")"""
        t0 = time.monotonic()
        warnings: List[str] = []
        inputs = {
            "task_result_json_supplied": bool(task_result_json.strip()),
            "import_result_json_supplied": bool(import_result_json.strip()),
            "validation_result_json_supplied": bool(validation_result_json.strip()),
            "screenshot_result_json_supplied": bool(screenshot_result_json.strip()),
            "session_name": session_name,
            "asset_name": asset_name,
            "content_path": content_path,
        }
        task_result = _coerce_json_object(task_result_json, "task_result_json", warnings)
        import_result = _coerce_json_object(import_result_json, "import_result_json", warnings)
        validation_result = _coerce_json_object(validation_result_json, "validation_result_json", warnings)
        screenshot_result = _coerce_json_object(screenshot_result_json, "screenshot_result_json", warnings)
        evidence = _build_generate_asset_evidence(
            task_result=task_result,
            import_result=import_result,
            validation_result=validation_result,
            screenshot_result=screenshot_result,
            session_name=session_name,
            asset_name=asset_name,
            content_path=content_path,
        )
        proven = bool(evidence.get("proven"))
        return _result_json(
            success=proven,
            stage="gen_compile_generate_asset_evidence",
            message="Generated asset evidence is complete" if proven else "Generated asset evidence has missing gates",
            inputs=inputs,
            outputs={"evidence": evidence},
            warnings=warnings + ([] if proven else list(evidence.get("next_actions", []))),
            t0=t0,
        )

    @mcp.tool()
    async def gen_prepare_texture_paint_session(
        ctx: Context,
        model_task_id: str,
        texture_prompt: str,
        texture_reference_image: str = "",
        viewport_view: str = "current",
        camera_matrix: Optional[List[float]] = None,
        brush_size: float = 0.03,
        brush_strength: float = 0.2,
        brush_hardness: float = 0.0,
        creativity_strength: float = 0.6,
        paint_mode: str = "image",
        paint_color: str = "#FFFFFF",
        blend_mode: str = "normal",
        paint_notes: str = "",
        save_name: str = "",
        tripo_project_id: str = "",
        record_session: bool = True,
    ) -> str:
        """Plan a Tripo Studio Magic Brush texture-paint session without spending credits.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#magic-brush-texture-edit-sessions
        Example:
            gen_prepare_texture_paint_session(model_task_id="model-task-id", texture_prompt="aged brass edge wear", brush_strength=0.25)"""
        t0 = time.monotonic()
        safe_task_id = _clean_optional_text(model_task_id)
        safe_prompt = _clean_optional_text(texture_prompt)
        safe_notes = _clean_optional_text(paint_notes)
        safe_project_id = _clean_optional_text(tripo_project_id)
        normalized_camera = []
        if camera_matrix:
            normalized_camera = [
                _clamp_float(value, 0.0, -1000000.0, 1000000.0)
                for value in camera_matrix
            ]
        normalized_brush_size = _clamp_float(brush_size, 0.03, 0.001, 0.1)
        normalized_brush_strength = _clamp_float(brush_strength, 0.2, 0.01, 1.0)
        normalized_hardness = _clamp_float(brush_hardness, 0.0, 0.0, 1.0)
        normalized_creativity = _clamp_float(creativity_strength, 0.6, 0.0, 1.0)
        inputs = {
            "model_task_id": model_task_id,
            "texture_prompt": texture_prompt,
            "texture_reference_image": texture_reference_image,
            "viewport_view": viewport_view,
            "camera_matrix": camera_matrix or [],
            "brush_size": brush_size,
            "brush_strength": brush_strength,
            "brush_hardness": brush_hardness,
            "creativity_strength": creativity_strength,
            "paint_mode": paint_mode,
            "paint_color": paint_color,
            "blend_mode": blend_mode,
            "paint_notes": paint_notes,
            "save_name": save_name,
            "tripo_project_id": tripo_project_id,
            "record_session": record_session,
        }
        if not safe_task_id:
            return _result_json(
                success=False,
                stage="gen_prepare_texture_paint_session",
                message="model_task_id is required",
                inputs=inputs,
                errors=["model_task_id is required"],
                t0=t0,
            )
        if not safe_prompt:
            return _result_json(
                success=False,
                stage="gen_prepare_texture_paint_session",
                message="texture_prompt is required",
                inputs=inputs,
                errors=["texture_prompt is required"],
                t0=t0,
            )

        plan = _build_texture_paint_session_plan(
            model_task_id=safe_task_id,
            texture_prompt=safe_prompt,
            texture_reference_image=texture_reference_image,
            viewport_view=viewport_view,
            camera_matrix=normalized_camera,
            brush_size=normalized_brush_size,
            brush_strength=normalized_brush_strength,
            brush_hardness=normalized_hardness,
            creativity_strength=normalized_creativity,
            paint_mode=paint_mode,
            paint_color=_clean_optional_text(paint_color) or "#FFFFFF",
            blend_mode=blend_mode,
            paint_notes=safe_notes,
            save_name=save_name,
            tripo_project_id=safe_project_id,
        )
        if record_session:
            _save_texture_paint_session(plan)

        warnings = [
            "This tool only prepares a Magic Brush texture-paint plan; it does not call Tripo, upload viewport images, paint pixels, or spend credits.",
            "Use gen_tripo_magic_brush_generate, gen_tripo_magic_brush_get_retexture, and gen_tripo_magic_brush_apply after the viewport snapshot/image-map data is available.",
        ]
        if not safe_project_id:
            warnings.append("Tripo Studio apply_retexture uses project_id; provide tripo_project_id when mirroring the exact Studio Magic Brush save flow.")

        return _result_json(
            success=True,
            stage="gen_prepare_texture_paint_session",
            message="Prepared Tripo Magic Brush texture-paint session plan",
            inputs=inputs,
            outputs={
                "session": plan,
                "session_file": str(_TEXTURE_PAINT_SESSIONS_PATH) if record_session else "",
                "estimated_credits": 0,
                "spend_required": False,
            },
            warnings=warnings,
            t0=t0,
        )

    @mcp.tool()
    async def gen_record_texture_paint_stroke(
        ctx: Context,
        session_id: str,
        part_name: str = "Body",
        image_bucket: str = "",
        image_key: str = "",
        image_url: str = "",
        image_file_token: str = "",
        viewport_view: str = "current",
        brush_size: float = 0.03,
        brush_strength: float = 0.2,
        brush_hardness: float = 0.0,
        blend_mode: str = "normal",
        paint_notes: str = "",
    ) -> str:
        """Record a no-spend Magic Brush paint/blend stroke in a texture-paint session.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#magic-brush-texture-edit-sessions
        Example:
            gen_record_texture_paint_stroke(session_id="magic_brush_model_123", part_name="Body", image_bucket="bucket", image_key="paint/body.png", brush_strength=0.35)"""
        t0 = time.monotonic()
        safe_session_id = _clean_optional_text(session_id)
        image = _build_magic_brush_image(
            image_bucket=image_bucket,
            image_key=image_key,
            image_url=image_url,
            image_file_token=image_file_token,
        )
        inputs = {
            "session_id": session_id,
            "part_name": part_name,
            "image_bucket": image_bucket,
            "image_key": image_key,
            "image_url": image_url,
            "image_file_token_supplied": bool(_clean_optional_text(image_file_token)),
            "viewport_view": viewport_view,
            "brush_size": brush_size,
            "brush_strength": brush_strength,
            "brush_hardness": brush_hardness,
            "blend_mode": blend_mode,
            "paint_notes": paint_notes,
        }
        if not safe_session_id:
            return _result_json(success=False, stage="gen_record_texture_paint_stroke", message="session_id is required", inputs=inputs, errors=["session_id is required"], t0=t0)
        if not image:
            return _result_json(success=False, stage="gen_record_texture_paint_stroke", message="paint image is required", inputs=inputs, errors=["Provide image_bucket/image_key, image_url, or image_file_token for the painted texture region."], t0=t0)

        sessions = _load_texture_paint_sessions()
        session = _find_texture_paint_session(sessions, safe_session_id)
        if session is None:
            return _result_json(success=False, stage="gen_record_texture_paint_stroke", message="texture paint session not found", inputs=inputs, errors=[f"session_id not found: {safe_session_id}"], t0=t0)

        strokes = session.get("paint_strokes")
        if not isinstance(strokes, list):
            strokes = []
        stroke = {
            "stroke_id": f"stroke_{int(time.time() * 1000)}_{len(strokes) + 1}",
            "part_name": _clean_optional_text(part_name) or "Body",
            "image": image,
            "viewport_view": _clean_optional_text(viewport_view) or "current",
            "brush": {
                "size": _clamp_float(brush_size, 0.03, 0.001, 0.1),
                "strength": _clamp_float(brush_strength, 0.2, 0.01, 1.0),
                "hardness": _clamp_float(brush_hardness, 0.0, 0.0, 1.0),
                "blend_mode": _clean_optional_text(blend_mode) or "normal",
                "notes": _clean_optional_text(paint_notes),
            },
            "recorded_at": int(time.time()),
        }
        strokes.append(stroke)
        session["paint_strokes"] = strokes[-200:]
        session["image_map"] = _session_image_map_from_strokes(session)
        _write_texture_paint_sessions(sessions)

        return _result_json(
            success=True,
            stage="gen_record_texture_paint_stroke",
            message="Recorded Magic Brush paint stroke without spending credits",
            inputs=inputs,
            outputs={
                "session_id": safe_session_id,
                "stroke": stroke,
                "stroke_count": len(session["paint_strokes"]),
                "image_map": session["image_map"],
                "spend_required": False,
            },
            t0=t0,
        )

    @mcp.tool()
    async def gen_compile_texture_paint_image_map(
        ctx: Context,
        session_id: str,
        prefer_latest_per_part: bool = True,
    ) -> str:
        """Compile recorded Magic Brush paint strokes into an apply_retexture image_map.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#magic-brush-texture-edit-sessions
        Example:
            gen_compile_texture_paint_image_map(session_id="magic_brush_model_123", prefer_latest_per_part=True)"""
        t0 = time.monotonic()
        safe_session_id = _clean_optional_text(session_id)
        inputs = {"session_id": session_id, "prefer_latest_per_part": prefer_latest_per_part}
        if not safe_session_id:
            return _result_json(success=False, stage="gen_compile_texture_paint_image_map", message="session_id is required", inputs=inputs, errors=["session_id is required"], t0=t0)

        sessions = _load_texture_paint_sessions()
        session = _find_texture_paint_session(sessions, safe_session_id)
        if session is None:
            return _result_json(success=False, stage="gen_compile_texture_paint_image_map", message="texture paint session not found", inputs=inputs, errors=[f"session_id not found: {safe_session_id}"], t0=t0)

        if prefer_latest_per_part:
            image_map = _session_image_map_from_strokes(session)
        else:
            strokes = session.get("paint_strokes")
            image_map = [
                {"part_name": _clean_optional_text(str(stroke.get("part_name", ""))) or "Body", "image": stroke.get("image")}
                for stroke in (strokes if isinstance(strokes, list) else [])
                if isinstance(stroke, dict) and isinstance(stroke.get("image"), dict) and stroke.get("image")
            ]
        session["image_map"] = image_map
        _write_texture_paint_sessions(sessions)

        warnings: List[str] = []
        if not image_map:
            warnings.append("No paint strokes with images have been recorded yet.")
        return _result_json(
            success=bool(image_map),
            stage="gen_compile_texture_paint_image_map",
            message="Compiled Magic Brush image_map from recorded paint strokes" if image_map else "No Magic Brush paint strokes are ready to apply",
            inputs=inputs,
            outputs={
                "session_id": safe_session_id,
                "project_id": session.get("tripo_project_id", ""),
                "image_map": image_map,
                "stroke_count": len(session.get("paint_strokes", [])) if isinstance(session.get("paint_strokes"), list) else 0,
                "apply_tool": "gen_tripo_magic_brush_apply",
                "apply_args": {
                    "project_id": session.get("tripo_project_id", ""),
                    "image_map": image_map,
                    "confirm_spend": False,
                },
                "spend_required": False,
            },
            warnings=warnings,
            t0=t0,
        )

    @mcp.tool()
    async def gen_tripo_magic_brush_generate(
        ctx: Context,
        project_id: str,
        prompt: str,
        render_image: Optional[Dict[str, Any]] = None,
        render_image_bucket: str = "",
        render_image_key: str = "",
        render_image_url: str = "",
        camera_matrix: Optional[List[float]] = None,
        model_version: str = "v3.0-20250812",
        strength: float = 0.6,
        session_name: str = "default",
        confirm_spend: bool = False,
    ) -> str:
        """Submit the observed Tripo Studio Magic Brush retexture_generate operation.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#magic-brush-texture-edit-sessions
        Example:
            gen_tripo_magic_brush_generate(project_id="studio-project-id", prompt="worn brass edges", render_image_bucket="bucket", render_image_key="snapshot.png", confirm_spend=True)"""
        t0 = time.monotonic()
        safe_project_id = _clean_optional_text(project_id)
        safe_prompt = _clean_optional_text(prompt)
        normalized_camera = [
            _clamp_float(value, 0.0, -1000000.0, 1000000.0)
            for value in (camera_matrix or [])
        ]
        normalized_strength = _clamp_float(strength, 0.6, 0.0, 1.0)
        render_object = _build_studio_render_image(
            render_image=render_image,
            render_image_bucket=render_image_bucket,
            render_image_key=render_image_key,
            render_image_url=render_image_url,
        )
        payload = {
            "camera_matrix": normalized_camera,
            "model_version": model_version,
            "project_id": safe_project_id,
            "prompt": safe_prompt,
            "render_image": render_object,
            "strength": normalized_strength,
        }
        inputs = {
            "project_id": project_id,
            "prompt": prompt,
            "render_image": render_image or {},
            "render_image_bucket": render_image_bucket,
            "render_image_key": render_image_key,
            "render_image_url": render_image_url,
            "camera_matrix": camera_matrix or [],
            "model_version": model_version,
            "strength": strength,
            "session_name": session_name,
            "confirm_spend": confirm_spend,
        }
        if not safe_project_id:
            return _result_json(success=False, stage="gen_tripo_magic_brush_generate", message="project_id is required", inputs=inputs, errors=["project_id is required"], t0=t0)
        if not safe_prompt:
            return _result_json(success=False, stage="gen_tripo_magic_brush_generate", message="prompt is required", inputs=inputs, errors=["prompt is required"], t0=t0)
        if not render_object:
            return _result_json(success=False, stage="gen_tripo_magic_brush_generate", message="render_image is required", inputs=inputs, errors=["Provide render_image or render_image_bucket/render_image_key from the viewport snapshot upload."], t0=t0)

        credit_guard = _check_and_reserve_credit_budget(
            estimated_credits=_estimate_tripo_credits("magic_brush_retexture_generate", payload),
            session_name=session_name,
            operation="magic_brush_retexture_generate",
            confirm_spend=confirm_spend,
            reserve_credits=True,
        )
        if not credit_guard["approved"]:
            return _result_json(
                success=False,
                stage="gen_tripo_magic_brush_generate",
                message="Tripo credit spend requires confirmation or exceeds the session budget",
                inputs=inputs,
                outputs={"request": payload, "credit_guard": credit_guard},
                warnings=["Set confirm_spend=True after user approval to submit the Magic Brush generation."] if credit_guard["confirm_required"] else [],
                errors=[] if credit_guard["confirm_required"] else ["Estimated credit spend exceeds the session budget."],
                t0=t0,
            )

        try:
            result = _tripo_studio_operation("retexture_generate", payload)
            data = result["data"]
            operator_id = data.get("operator_id") or data.get("id") or ""
            return _result_json(
                success=True,
                stage="gen_tripo_magic_brush_generate",
                message="Submitted Tripo Studio Magic Brush retexture generation",
                inputs=inputs,
                outputs={
                    "provider": "tripo",
                    "operator_id": operator_id,
                    "request": payload,
                    "credit_guard": credit_guard,
                    "result": data,
                    "trace_id": result.get("trace_id", ""),
                    "raw_response": result.get("response", {}),
                },
                t0=t0,
            )
        except Exception as exc:
            _release_credit_reservation(credit_guard)
            return _result_json(success=False, stage="gen_tripo_magic_brush_generate", message=str(exc), inputs=inputs, outputs={"request": payload, "credit_guard": credit_guard}, errors=[str(exc)], t0=t0)

    @mcp.tool()
    async def gen_tripo_magic_brush_get_retexture(ctx: Context, operator_id: str) -> str:
        """Fetch a completed Tripo Studio Magic Brush retexture result by operator id.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#magic-brush-texture-edit-sessions
        Example:
            gen_tripo_magic_brush_get_retexture(operator_id="operator-id")"""
        t0 = time.monotonic()
        safe_operator_id = _clean_optional_text(operator_id)
        inputs = {"operator_id": operator_id}
        if not safe_operator_id:
            return _result_json(success=False, stage="gen_tripo_magic_brush_get_retexture", message="operator_id is required", inputs=inputs, errors=["operator_id is required"], t0=t0)
        try:
            request = {"operator_id": safe_operator_id}
            result = _tripo_studio_operation("get_retexture", request)
            return _result_json(
                success=True,
                stage="gen_tripo_magic_brush_get_retexture",
                message="Fetched Tripo Studio Magic Brush retexture result",
                inputs=inputs,
                outputs={"provider": "tripo", "request": request, "result": result["data"], "trace_id": result.get("trace_id", ""), "raw_response": result.get("response", {})},
                t0=t0,
            )
        except Exception as exc:
            return _result_json(success=False, stage="gen_tripo_magic_brush_get_retexture", message=str(exc), inputs=inputs, errors=[str(exc)], t0=t0)

    @mcp.tool()
    async def gen_tripo_magic_brush_list_images(ctx: Context, project_id: str) -> str:
        """List Tripo Studio Magic Brush retexture images for a project.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#magic-brush-texture-edit-sessions
        Example:
            gen_tripo_magic_brush_list_images(project_id="studio-project-id")"""
        t0 = time.monotonic()
        safe_project_id = _clean_optional_text(project_id)
        inputs = {"project_id": project_id}
        if not safe_project_id:
            return _result_json(success=False, stage="gen_tripo_magic_brush_list_images", message="project_id is required", inputs=inputs, errors=["project_id is required"], t0=t0)
        try:
            request = {"project_id": safe_project_id}
            result = _tripo_studio_operation("get_retexture_images", request)
            return _result_json(
                success=True,
                stage="gen_tripo_magic_brush_list_images",
                message="Listed Tripo Studio Magic Brush retexture images",
                inputs=inputs,
                outputs={"provider": "tripo", "request": request, "result": result["data"], "trace_id": result.get("trace_id", ""), "raw_response": result.get("response", {})},
                t0=t0,
            )
        except Exception as exc:
            return _result_json(success=False, stage="gen_tripo_magic_brush_list_images", message=str(exc), inputs=inputs, errors=[str(exc)], t0=t0)

    @mcp.tool()
    async def gen_tripo_magic_brush_apply(
        ctx: Context,
        project_id: str,
        image_map: Optional[List[Dict[str, Any]]] = None,
        model_version: str = "v3.0-20250812",
        session_name: str = "default",
        confirm_spend: bool = False,
    ) -> str:
        """Apply painted Magic Brush image parts to a Tripo Studio project.

        KB: see knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md#magic-brush-texture-edit-sessions
        Example:
            gen_tripo_magic_brush_apply(project_id="studio-project-id", image_map=[{"part_name":"Body","image":{"bucket":"bucket","key":"paint.png"}}], confirm_spend=True)"""
        t0 = time.monotonic()
        safe_project_id = _clean_optional_text(project_id)
        safe_image_map = image_map or []
        payload = {
            "image_map": safe_image_map,
            "model_version": model_version,
            "project_id": safe_project_id,
        }
        inputs = {
            "project_id": project_id,
            "image_map": safe_image_map,
            "model_version": model_version,
            "session_name": session_name,
            "confirm_spend": confirm_spend,
        }
        if not safe_project_id:
            return _result_json(success=False, stage="gen_tripo_magic_brush_apply", message="project_id is required", inputs=inputs, errors=["project_id is required"], t0=t0)
        if not safe_image_map:
            return _result_json(success=False, stage="gen_tripo_magic_brush_apply", message="image_map is required", inputs=inputs, errors=["image_map must include painted image parts from the brush compile step."], t0=t0)

        credit_guard = _check_and_reserve_credit_budget(
            estimated_credits=_estimate_tripo_credits("magic_brush_apply_retexture", payload),
            session_name=session_name,
            operation="magic_brush_apply_retexture",
            confirm_spend=confirm_spend,
            reserve_credits=True,
        )
        if not credit_guard["approved"]:
            return _result_json(
                success=False,
                stage="gen_tripo_magic_brush_apply",
                message="Tripo credit spend requires confirmation or exceeds the session budget",
                inputs=inputs,
                outputs={"request": payload, "credit_guard": credit_guard},
                warnings=["Set confirm_spend=True after user approval to apply the Magic Brush paint pass."] if credit_guard["confirm_required"] else [],
                errors=[] if credit_guard["confirm_required"] else ["Estimated credit spend exceeds the session budget."],
                t0=t0,
            )

        try:
            result = _tripo_studio_operation("apply_retexture", payload)
            return _result_json(
                success=True,
                stage="gen_tripo_magic_brush_apply",
                message="Applied Tripo Studio Magic Brush texture paint",
                inputs=inputs,
                outputs={
                    "provider": "tripo",
                    "request": payload,
                    "credit_guard": credit_guard,
                    "result": result["data"],
                    "trace_id": result.get("trace_id", ""),
                    "raw_response": result.get("response", {}),
                },
                t0=t0,
            )
        except Exception as exc:
            _release_credit_reservation(credit_guard)
            return _result_json(success=False, stage="gen_tripo_magic_brush_apply", message=str(exc), inputs=inputs, outputs={"request": payload, "credit_guard": credit_guard}, errors=[str(exc)], t0=t0)

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
            credit_reconciliation = _reconcile_tripo_task_credit_usage(task)
            return _result_json(success=True, stage="gen_tripo_get_task_status", message=f"Tripo task status: {task.get('status', 'unknown')}", inputs=inputs, outputs={"task": task, "trace_id": result.get("trace_id", ""), "final": task.get("status") in _TRIPO_FINAL_STATUSES, "credit_reconciliation": credit_reconciliation}, t0=t0)
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
                    credit_reconciliation = _reconcile_tripo_task_credit_usage(task)
                    return _result_json(success=task.get("status") == "success", stage="gen_tripo_wait_for_task", message=f"Tripo task finalized: {task.get('status')}", inputs=inputs, outputs={"task": task, "snapshots": snapshots, "credit_reconciliation": credit_reconciliation}, errors=[] if task.get("status") == "success" else [f"Tripo task finalized as {task.get('status')}"], t0=t0)
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
            downloads = _download_tripo_output_files(task_id=task_id, output=output, target_folder=Path(target_folder), output_keys=keys)
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
            task_result = _tripo_get_task(task_id)
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
            downloads = _download_tripo_output_files(
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
            manifest_raw = _send("gen_prepare_import_manifest", manifest_inputs)
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

            import_result = _import_generated_static_mesh(
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
                thumbnail = _capture_import_thumbnail(task_id, safe_asset_name)
                if not thumbnail.get("success"):
                    warnings.append("Thumbnail screenshot was requested but could not be captured from the active viewport.")

            import_outputs = import_result.get("outputs", {})
            asset_paths = {
                "primary_asset": import_outputs.get("asset_path") or manifest.get("expected_assets", {}).get("primary_asset", ""),
                "material_instance": import_outputs.get("material_instance", ""),
                "blueprint": import_outputs.get("blueprint", ""),
                "imported_object_paths": import_outputs.get("imported_object_paths", []),
            }
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
        raw = _send("gen_prepare_import_manifest", inputs)
        return _bridge_result(
            stage="gen_prepare_import_manifest",
            raw=raw,
            inputs=inputs,
            message="Prepared generated asset import manifest",
            t0=t0,
        )

    logger.info("Generative content tools registered")
