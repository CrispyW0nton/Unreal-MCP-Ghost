"""Clean-room MCP client configuration generation for Unreal-MCP-Ghost.

Epic's UE 5.8 MCP plugin ships a native client-config command. This module
implements the same idea for Ghost's Python server without copying Epic source,
and keeps Ghost's stdio/SSE/streamable-http transport choices available.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional


ClientName = Literal["claude_code", "cursor", "vscode", "gemini", "codex"]
TargetName = Literal["claude_code", "cursor", "vscode", "gemini", "codex", "all"]
TransportName = Literal["stdio", "sse", "streamable-http"]

SUPPORTED_CLIENTS: tuple[ClientName, ...] = (
    "claude_code",
    "cursor",
    "vscode",
    "gemini",
    "codex",
)

CLIENT_ALIASES: dict[str, TargetName] = {
    "all": "all",
    "claude": "claude_code",
    "claude_code": "claude_code",
    "claudecode": "claude_code",
    "cursor": "cursor",
    "vs": "vscode",
    "vscode": "vscode",
    "vs_code": "vscode",
    "gemini": "gemini",
    "codex": "codex",
}


@dataclass(frozen=True)
class ClientDescriptor:
    name: ClientName
    relative_path: str
    root_key: str
    url_key: str
    include_type: bool = False
    is_toml: bool = False


DESCRIPTORS: dict[ClientName, ClientDescriptor] = {
    "claude_code": ClientDescriptor("claude_code", ".mcp.json", "mcpServers", "url", include_type=True),
    "cursor": ClientDescriptor("cursor", ".cursor/mcp.json", "mcpServers", "url"),
    "vscode": ClientDescriptor("vscode", ".vscode/mcp.json", "servers", "url", include_type=True),
    "gemini": ClientDescriptor("gemini", ".gemini/settings.json", "mcpServers", "httpUrl"),
    "codex": ClientDescriptor("codex", ".codex/config.toml", "mcp_servers", "url", is_toml=True),
}

DEFAULT_SERVER_NAME = "unreal-mcp"
DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8000
DEFAULT_UNREAL_HOST = "127.0.0.1"
DEFAULT_UNREAL_PORT = 55655
DEFAULT_PYTHON_COMMAND = "python"

CODEX_BEGIN = "# BEGIN Unreal-MCP-Ghost generated MCP server"
CODEX_END = "# END Unreal-MCP-Ghost generated MCP server"
SERVER_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


@dataclass(frozen=True)
class ClientConfigOptions:
    target: TargetName = "all"
    transport: TransportName = "streamable-http"
    base_dir: Path = Path.cwd()
    server_name: str = DEFAULT_SERVER_NAME
    python_command: str = DEFAULT_PYTHON_COMMAND
    server_script: Optional[Path] = None
    mcp_host: str = DEFAULT_HTTP_HOST
    mcp_port: int = DEFAULT_HTTP_PORT
    unreal_host: str = DEFAULT_UNREAL_HOST
    unreal_port: int = DEFAULT_UNREAL_PORT
    tool_search_mode: bool = False
    dry_run: bool = False
    overwrite_codex_section: bool = True


def normalize_client_target(target: str) -> TargetName:
    normalized = target.strip().lower().replace("-", "_")
    if normalized not in CLIENT_ALIASES:
        raise ValueError(f"Unsupported client target '{target}'.")
    return CLIENT_ALIASES[normalized]


def selected_clients(target: str) -> tuple[ClientName, ...]:
    normalized = normalize_client_target(target)
    if normalized == "all":
        return SUPPORTED_CLIENTS
    return (normalized,)


def build_server_url(transport: TransportName, host: str, port: int) -> str:
    if transport == "sse":
        path = "/sse"
    elif transport == "streamable-http":
        path = "/mcp"
    else:
        raise ValueError("stdio transport does not use an HTTP URL.")
    return f"http://{host}:{port}{path}"


def default_server_script() -> Path:
    return Path(__file__).with_name("unreal_mcp_server.py").resolve()


def write_client_configurations(options: ClientConfigOptions) -> dict[str, Any]:
    try:
        validate_server_name(options.server_name)
    except ValueError as exc:
        return {
            "success": False,
            "target": options.target,
            "transport": options.transport,
            "dry_run": options.dry_run,
            "written_count": 0,
            "results": [],
            "error": str(exc),
        }

    results: list[dict[str, Any]] = []
    for client in selected_clients(options.target):
        result = write_client_configuration(client, options)
        results.append(result)

    return {
        "success": all(item["success"] for item in results),
        "target": options.target,
        "transport": options.transport,
        "dry_run": options.dry_run,
        "written_count": sum(1 for item in results if item.get("written")),
        "results": results,
    }


def write_client_configuration(client: ClientName, options: ClientConfigOptions) -> dict[str, Any]:
    validate_server_name(options.server_name)
    descriptor = DESCRIPTORS[client]
    path = (options.base_dir / descriptor.relative_path).resolve()
    entry = build_server_entry(descriptor, options)

    if options.dry_run:
        return {
            "success": True,
            "written": False,
            "client": client,
            "path": str(path),
            "entry": entry,
        }

    try:
        if descriptor.is_toml:
            content = _build_codex_config(path, options, entry)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        else:
            root = _load_json_object(path)
            servers = root.get(descriptor.root_key)
            if not isinstance(servers, dict):
                servers = {}
            servers[options.server_name] = entry
            root[descriptor.root_key] = servers
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(root, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception as exc:
        return {
            "success": False,
            "written": False,
            "client": client,
            "path": str(path),
            "error": str(exc),
        }

    return {
        "success": True,
        "written": True,
        "client": client,
        "path": str(path),
        "entry": entry,
    }


def validate_server_name(server_name: str) -> str:
    """Validate one portable MCP client configuration key."""

    value = str(server_name or "")
    if not SERVER_NAME_PATTERN.fullmatch(value):
        raise ValueError("server_name must contain 1-64 ASCII letters, digits, underscores, or hyphens.")
    return value


def build_server_entry(descriptor: ClientDescriptor, options: ClientConfigOptions) -> dict[str, Any]:
    if options.transport == "stdio":
        return _stdio_entry(options)

    entry: dict[str, Any] = {
        descriptor.url_key: build_server_url(options.transport, options.mcp_host, options.mcp_port)
    }
    if descriptor.include_type:
        entry["type"] = "sse" if options.transport == "sse" else "http"
    return entry


def _stdio_entry(options: ClientConfigOptions) -> dict[str, Any]:
    script = (options.server_script or default_server_script()).resolve()
    entry: dict[str, Any] = {
        "command": options.python_command,
        "args": [
            str(script),
            "--transport",
            "stdio",
        ],
        "env": {
            "UNREAL_HOST": options.unreal_host,
            "UNREAL_PORT": str(options.unreal_port),
        },
    }
    if options.tool_search_mode:
        entry["env"]["UNREAL_MCP_TOOL_SEARCH_MODE"] = "1"
    return entry


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Existing JSON is malformed: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Existing JSON root must be an object: {path}")
    return value


def _build_codex_config(path: Path, options: ClientConfigOptions, entry: dict[str, Any]) -> str:
    validate_server_name(options.server_name)
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    block = _codex_block(options.server_name, entry)

    if CODEX_BEGIN in existing or CODEX_END in existing:
        if not options.overwrite_codex_section:
            raise ValueError("Codex generated block already exists and overwrite is disabled.")
        return _replace_managed_block(existing, block)

    section_header = f"[mcp_servers.{options.server_name}]"
    if section_header in existing:
        raise ValueError(
            f"Codex config already contains {section_header}. "
            "Remove it or enable a managed generated block first."
        )

    if existing and not existing.endswith("\n"):
        existing += "\n"
    return existing + ("\n" if existing.strip() else "") + block


def _replace_managed_block(existing: str, block: str) -> str:
    start = existing.find(CODEX_BEGIN)
    end = existing.find(CODEX_END)
    if start == -1 or end == -1 or end < start:
        raise ValueError("Codex generated block markers are malformed.")
    end += len(CODEX_END)
    suffix = existing[end:]
    if suffix.startswith("\n"):
        suffix = suffix[1:]
    return existing[:start].rstrip() + "\n\n" + block + ("\n" + suffix if suffix else "")


def _codex_block(server_name: str, entry: dict[str, Any]) -> str:
    lines = [
        CODEX_BEGIN,
        f"[mcp_servers.{server_name}]",
    ]

    for key in ("command", "url"):
        if key in entry:
            lines.append(f"{key} = {_toml_string(entry[key])}")
    if "args" in entry:
        args = ", ".join(_toml_string(value) for value in entry["args"])
        lines.append(f"args = [{args}]")
    if "env" in entry and entry["env"]:
        lines.append("")
        lines.append(f"[mcp_servers.{server_name}.env]")
        for key, value in sorted(entry["env"].items()):
            lines.append(f"{key} = {_toml_string(value)}")

    lines.append(CODEX_END)
    return "\n".join(lines) + "\n"


def _toml_string(value: Any) -> str:
    text = str(value)
    return json.dumps(text)
