"""Private token-session framing for the UnrealMCP editor bridge."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional


TOKEN_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TRUTHY = frozenset({"1", "true", "yes", "on"})
TOKEN_FILE_ENV = "UNREAL_MCP_PRIVATE_TOKEN_FILE"
LEGACY_TOKEN_FILE_ENV = "UNREAL_MCP_BRIDGE_TOKEN_FILE"
DIRECT_TOKEN_ENV = "UNREAL_MCP_BRIDGE_TOKEN"
REQUIRE_AUTH_ENV = "UNREAL_MCP_REQUIRE_AUTH"


class BridgeAuthenticationError(RuntimeError):
    pass


@dataclass(frozen=True)
class BridgeAuthentication:
    required: bool
    token: Optional[str]
    source: str

    @property
    def enabled(self) -> bool:
        return self.token is not None

    def command_payload(self, command: str, params: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": command, "params": dict(params or {})}
        if self.token is not None:
            payload["auth"] = self.token
        elif self.required:
            raise BridgeAuthenticationError("UnrealMCP authentication is required but no valid private token is available.")
        return payload


def _required(environment: Mapping[str, str]) -> bool:
    return str(environment.get(REQUIRE_AUTH_ENV, "")).strip().lower() in TRUTHY


def _read_token_file(path_text: str) -> str:
    path = Path(path_text).expanduser()
    if not path.is_absolute():
        raise BridgeAuthenticationError("UnrealMCP token-file path must be absolute.")
    try:
        if path.is_symlink() or not path.is_file():
            raise BridgeAuthenticationError("UnrealMCP token file must be a regular non-link file.")
        if path.stat().st_size > 256:
            raise BridgeAuthenticationError("UnrealMCP token file exceeds the 256-byte limit.")
        token = path.read_text(encoding="ascii").strip().lower()
    except BridgeAuthenticationError:
        raise
    except Exception as exc:
        raise BridgeAuthenticationError(f"Could not read UnrealMCP token file: {type(exc).__name__}") from exc
    if not TOKEN_PATTERN.fullmatch(token):
        raise BridgeAuthenticationError("UnrealMCP token must contain exactly 64 lowercase hexadecimal characters.")
    return token


def load_bridge_authentication(
    environment: Optional[Mapping[str, str]] = None,
) -> BridgeAuthentication:
    values = os.environ if environment is None else environment
    required = _required(values)
    token_file = str(values.get(TOKEN_FILE_ENV) or values.get(LEGACY_TOKEN_FILE_ENV) or "").strip()
    direct_token = str(values.get(DIRECT_TOKEN_ENV) or "").strip().lower()
    if token_file and direct_token:
        raise BridgeAuthenticationError("Configure one UnrealMCP token source, not both a token file and a direct token.")
    if token_file:
        return BridgeAuthentication(required=True, token=_read_token_file(token_file), source="private-token-file")
    if direct_token:
        if not TOKEN_PATTERN.fullmatch(direct_token):
            raise BridgeAuthenticationError("UnrealMCP direct token must contain exactly 64 lowercase hexadecimal characters.")
        return BridgeAuthentication(required=True, token=direct_token, source="environment-token")
    if required:
        raise BridgeAuthenticationError("UnrealMCP authentication is required but no token source is configured.")
    return BridgeAuthentication(required=False, token=None, source="legacy-unauthenticated")
