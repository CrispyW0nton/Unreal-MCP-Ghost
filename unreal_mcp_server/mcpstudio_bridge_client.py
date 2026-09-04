"""Authenticated private-spool client for MCPStudio's Unreal spatial tools."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import stat
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bridge_auth import load_bridge_authentication


_SCHEMA = "unreal-spatial-bridge-spool/v1"
_ALLOWED_COMMANDS = frozenset({
    "exec_python",
    "inspect_static_mesh_sections",
    "focus_viewport",
    "take_screenshot",
})
_MAX_REQUEST_BYTES = 1024 * 1024
_DEFAULT_MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_DEFAULT_TIMEOUT_MS = 12_000
_MAX_CAPTURE_POLICY_BYTES = 64 * 1024


@dataclass(frozen=True)
class CapturePolicy:
    """Local, project-specific allowlist for viewport evidence commands."""

    focus_views: tuple[dict[str, Any], ...]
    screenshot_paths: frozenset[str]
    screenshot_resolution: tuple[int, int]

    def allows_focus(self, params: object) -> bool:
        return isinstance(params, dict) and any(params == view for view in self.focus_views)

    def allows_screenshot(self, params: object) -> bool:
        if not isinstance(params, dict) or set(params) != {"filepath", "show_ui", "resolution"}:
            return False
        filepath = params.get("filepath")
        return (
            params.get("show_ui") is False
            and params.get("resolution") == list(self.screenshot_resolution)
            and isinstance(filepath, str)
            and os.path.normcase(os.path.realpath(filepath)) in self.screenshot_paths
        )


def _load_capture_policy() -> CapturePolicy:
    """Load a local policy without embedding private project paths in source control."""

    policy_text = os.environ.get("UNREAL_MCP_SPATIAL_CAPTURE_POLICY", "").strip()
    if not policy_text:
        return CapturePolicy((), frozenset(), (1600, 900))

    policy_path = Path(policy_text)
    if not policy_path.is_absolute():
        raise RuntimeError("Unreal spatial capture policy path must be absolute")
    try:
        metadata = policy_path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise RuntimeError("Unreal spatial capture policy file is unsafe")
        if metadata.st_size <= 0 or metadata.st_size > _MAX_CAPTURE_POLICY_BYTES:
            raise RuntimeError("Unreal spatial capture policy size is invalid")
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Unreal spatial capture policy could not be loaded") from exc

    if not isinstance(payload, dict) or set(payload) != {
        "focus_views",
        "screenshot_paths",
        "screenshot_resolution",
    }:
        raise RuntimeError("Unreal spatial capture policy fields are invalid")

    focus_views = payload["focus_views"]
    screenshot_paths = payload["screenshot_paths"]
    resolution = payload["screenshot_resolution"]
    if not isinstance(focus_views, list) or len(focus_views) > 32:
        raise RuntimeError("Unreal spatial capture focus views are invalid")
    for view in focus_views:
        if not isinstance(view, dict) or set(view) != {"location", "distance", "orientation"}:
            raise RuntimeError("Unreal spatial capture focus view is invalid")
        if (
            not isinstance(view["location"], list)
            or len(view["location"]) != 3
            or not isinstance(view["orientation"], list)
            or len(view["orientation"]) != 3
            or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in view["location"] + view["orientation"])
            or isinstance(view["distance"], bool)
            or not isinstance(view["distance"], (int, float))
        ):
            raise RuntimeError("Unreal spatial capture focus view values are invalid")
    if not isinstance(screenshot_paths, list) or len(screenshot_paths) > 32:
        raise RuntimeError("Unreal spatial capture screenshot paths are invalid")
    normalized_paths = set()
    for value in screenshot_paths:
        if not isinstance(value, str) or not value or not Path(value).is_absolute():
            raise RuntimeError("Unreal spatial capture screenshot path is invalid")
        normalized_paths.add(os.path.normcase(os.path.realpath(value)))
    if (
        not isinstance(resolution, list)
        or len(resolution) != 2
        or any(isinstance(value, bool) or not isinstance(value, int) for value in resolution)
        or not 1 <= resolution[0] <= 7680
        or not 1 <= resolution[1] <= 4320
    ):
        raise RuntimeError("Unreal spatial capture resolution is invalid")
    return CapturePolicy(
        tuple(dict(view) for view in focus_views),
        frozenset(normalized_paths),
        (resolution[0], resolution[1]),
    )


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sign(payload: dict[str, Any], token: bytes) -> dict[str, Any]:
    encoded = _canonical_bytes(payload)
    return {
        "schema": _SCHEMA,
        "id": payload["id"],
        "payload_base64": base64.b64encode(encoded).decode("ascii"),
        "payload_sha256": _sha256(encoded),
        "mac": hmac.new(token, encoded, hashlib.sha256).hexdigest(),
    }


def _verify(
    value: object,
    token: bytes,
    expected_id: str,
) -> tuple[dict[str, Any], str]:
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "id",
        "payload_base64",
        "payload_sha256",
        "mac",
    }:
        raise RuntimeError("Unreal spatial spool envelope fields are invalid")
    if value.get("schema") != _SCHEMA or value.get("id") != expected_id:
        raise RuntimeError("Unreal spatial spool envelope identity mismatched")
    try:
        encoded = base64.b64decode(value["payload_base64"], validate=True)
    except Exception as exc:
        raise RuntimeError("Unreal spatial spool payload encoding is invalid") from exc
    supplied_digest = value.get("payload_sha256")
    supplied_mac = value.get("mac")
    if (
        not isinstance(supplied_digest, str)
        or _sha256(encoded) != supplied_digest
        or not isinstance(supplied_mac, str)
        or not hmac.compare_digest(
            hmac.new(token, encoded, hashlib.sha256).hexdigest(), supplied_mac
        )
    ):
        raise RuntimeError("Unreal spatial spool authentication failed")
    try:
        payload = json.loads(encoded.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Unreal spatial spool payload is invalid JSON") from exc
    if not isinstance(payload, dict) or payload.get("id") != expected_id:
        raise RuntimeError("Unreal spatial spool payload identity mismatched")
    return payload, supplied_digest


def _safe_directory(path: Path) -> Path:
    if not path.is_absolute():
        raise RuntimeError("Unreal spatial spool directory must be absolute")
    metadata = path.lstat()
    file_attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or bool(file_attributes & reparse_attribute)
    ):
        raise RuntimeError("Unreal spatial spool directory is unsafe")
    return path


def _read_stable_file(path: Path, maximum_bytes: int) -> bytes:
    before = path.stat(follow_symlinks=False)
    if not path.is_symlink() and path.is_file() and before.st_nlink > 1:
        raise BlockingIOError("Unreal spatial spool publication is still in progress")
    if path.is_symlink() or not path.is_file() or before.st_nlink != 1:
        raise RuntimeError("Unreal spatial spool response file is unsafe")
    if before.st_size <= 0 or before.st_size > maximum_bytes:
        raise RuntimeError("Unreal spatial spool response size is invalid")
    with path.open("rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise RuntimeError("Unreal spatial spool response identity changed")
        value = handle.read(maximum_bytes + 1)
        after = os.fstat(handle.fileno())
    if (
        len(value) != before.st_size
        or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    ):
        raise RuntimeError("Unreal spatial spool response changed during read")
    return value


class McpStudioUnrealConnection:
    """Send only reviewed spatial substrate calls through the private spool."""

    def __init__(self) -> None:
        authentication = load_bridge_authentication()
        if not authentication.enabled or authentication.token is None:
            raise RuntimeError("MCPStudio Unreal bridge authentication is required")
        self._token = authentication.token.encode("ascii")
        spool_text = os.environ.get("UNREAL_MCP_SPOOL_ROOT", "").strip()
        if not spool_text:
            raise RuntimeError("MCPStudio Unreal spatial spool is not configured")
        spool = Path(spool_text)
        if not spool.is_absolute():
            raise RuntimeError("MCPStudio Unreal spatial spool path must be absolute")
        self._spool = _safe_directory(spool)
        self._requests = _safe_directory(self._spool / "requests")
        self._responses = _safe_directory(self._spool / "responses")
        self._timeout_ms = int(
            os.environ.get("UNREAL_MCP_SPOOL_TIMEOUT_MS", _DEFAULT_TIMEOUT_MS)
        )
        self._max_response_bytes = int(
            os.environ.get(
                "UNREAL_MCP_SPOOL_MAX_RESPONSE_BYTES",
                _DEFAULT_MAX_RESPONSE_BYTES,
            )
        )
        if self._timeout_ms <= 0 or self._max_response_bytes <= 0:
            raise RuntimeError("MCPStudio Unreal spatial spool budgets are invalid")
        self._capture_policy = _load_capture_policy()

    def send_command(
        self,
        command: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if command not in _ALLOWED_COMMANDS:
            return {
                "status": "error",
                "error": "Command is outside the MCPStudio spatial bridge allowlist",
            }
        if command == "exec_python":
            if (
                not isinstance(params, dict)
                or set(params) != {"code", "mode"}
                or params.get("mode") != "evaluate_statement"
            ):
                return {"status": "error", "error": "Spatial command params are invalid"}
            code = params.get("code")
            if not isinstance(code, str) or len(code.encode("utf-8")) > 768 * 1024:
                return {"status": "error", "error": "Spatial command code is invalid"}
        elif command == "inspect_static_mesh_sections":
            if not isinstance(params, dict) or set(params) != {
                "asset_path",
                "lod_index",
                "max_sections",
            }:
                return {"status": "error", "error": "Static-mesh section params are invalid"}
            asset_path = params.get("asset_path")
            lod_index = params.get("lod_index")
            max_sections = params.get("max_sections")
            if (
                not isinstance(asset_path, str)
                or not asset_path.startswith("/Game/")
                or len(asset_path) > 512
                or asset_path.endswith("/")
                or "\\" in asset_path
                or ".." in asset_path
                or any(ord(character) < 32 for character in asset_path)
                or isinstance(lod_index, bool)
                or not isinstance(lod_index, int)
                or not 0 <= lod_index <= 7
                or isinstance(max_sections, bool)
                or not isinstance(max_sections, int)
                or not 1 <= max_sections <= 128
            ):
                return {"status": "error", "error": "Static-mesh section params are invalid"}
        elif command == "focus_viewport":
            if not self._capture_policy.allows_focus(params):
                return {"status": "error", "error": "Landing review viewport params are invalid"}
        elif command == "take_screenshot":
            if not self._capture_policy.allows_screenshot(params):
                return {"status": "error", "error": "Landing review screenshot params are invalid"}

        request_id = secrets.token_hex(16)
        expires_unix_ms = int(time.time() * 1000) + self._timeout_ms
        payload = {
            "schema": _SCHEMA,
            "id": request_id,
            "method": command,
            "params": params,
            "expires_unix_ms": expires_unix_ms,
        }
        encoded = _canonical_bytes(_sign(payload, self._token))
        if len(encoded) > _MAX_REQUEST_BYTES:
            return {"status": "error", "error": "Spatial spool request is too large"}
        request_path = self._requests / f"{request_id}.json"
        pending_path = self._requests / f"{request_id}.{secrets.token_hex(16)}.pending"
        response_path = self._responses / f"{request_id}.json"
        descriptor = os.open(
            pending_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.link(pending_path, request_path)
        finally:
            pending_path.unlink(missing_ok=True)

        deadline = time.monotonic() + self._timeout_ms / 1000.0
        try:
            while time.monotonic() < deadline:
                if response_path.exists():
                    try:
                        raw = _read_stable_file(
                            response_path, self._max_response_bytes
                        )
                    except BlockingIOError:
                        time.sleep(0.01)
                        continue
                    response_path.unlink()
                    envelope = json.loads(raw.decode("utf-8"))
                    response, _ = _verify(envelope, self._token, request_id)
                    if response.get("request_sha256") != _sha256(
                        _canonical_bytes(payload)
                    ):
                        raise RuntimeError("Unreal spatial spool request digest mismatched")
                    if response.get("ok") is True and "result" in response:
                        result = response["result"]
                        return result if isinstance(result, dict) else {"result": result}
                    error = response.get("error")
                    message = (
                        error.get("message")
                        if isinstance(error, dict)
                        else "Unreal spatial spool request failed"
                    )
                    return {"status": "error", "error": str(message)}
                time.sleep(0.01)
        finally:
            request_path.unlink(missing_ok=True)
        return {"status": "error", "error": "Unreal spatial spool request timed out"}


_CONNECTION: Optional[McpStudioUnrealConnection] = None


def get_mcpstudio_unreal_connection() -> McpStudioUnrealConnection:
    global _CONNECTION
    if _CONNECTION is None:
        _CONNECTION = McpStudioUnrealConnection()
    return _CONNECTION
