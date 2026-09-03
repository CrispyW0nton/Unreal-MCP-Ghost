"""MCP tools for generating AI client config files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import Context, FastMCP

from client_config import (
    ClientConfigOptions,
    normalize_client_target,
    write_client_configurations,
)


def register_client_config_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def generate_client_config(
        ctx: Context,
        client: str = "all",
        transport: str = "streamable-http",
        base_dir: str = "",
        server_name: str = "unreal-mcp",
        python_command: str = "python",
        server_script: str = "",
        mcp_host: str = "127.0.0.1",
        mcp_port: int = 8000,
        unreal_host: str = "127.0.0.1",
        unreal_port: int = 55655,
        tool_search_mode: bool = False,
        dry_run: bool = False,
    ) -> str:
        """Generate MCP client config files for Codex, Cursor, VS Code, Claude, and Gemini.

        Args:
            client: One of "all", "codex", "cursor", "vscode", "claude_code", or "gemini".
            transport: "stdio", "streamable-http", or "sse".
            base_dir: Directory where client config folders/files should be written.
                Defaults to the current repository root.
            server_name: MCP server entry name to write.
            python_command: Python command for stdio configs.
            server_script: Optional absolute path to unreal_mcp_server.py for stdio configs.
            mcp_host: HTTP host for streamable-http or SSE configs.
            mcp_port: HTTP port for streamable-http or SSE configs.
            unreal_host: UE bridge host for stdio configs.
            unreal_port: UE bridge port for stdio configs.
            tool_search_mode: Add UNREAL_MCP_TOOL_SEARCH_MODE=1 to stdio configs.
            dry_run: Return config entries and paths without writing files.
        """

        if transport not in {"stdio", "sse", "streamable-http"}:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Unsupported transport '{transport}'.",
                    "supported_transports": ["stdio", "sse", "streamable-http"],
                },
                indent=2,
                sort_keys=True,
            )

        try:
            target = normalize_client_target(client)
        except ValueError as exc:
            return json.dumps(
                {
                    "success": False,
                    "error": str(exc),
                    "supported_clients": ["all", "codex", "cursor", "vscode", "claude_code", "gemini"],
                },
                indent=2,
                sort_keys=True,
            )

        repo_root = Path(__file__).resolve().parent.parent
        options = ClientConfigOptions(
            target=target,
            transport=transport,  # type: ignore[arg-type]
            base_dir=Path(base_dir).expanduser().resolve() if base_dir else repo_root,
            server_name=server_name,
            python_command=python_command,
            server_script=Path(server_script).expanduser().resolve() if server_script else None,
            mcp_host=mcp_host,
            mcp_port=mcp_port,
            unreal_host=unreal_host,
            unreal_port=unreal_port,
            tool_search_mode=tool_search_mode,
            dry_run=dry_run,
        )
        result = write_client_configurations(options)
        return json.dumps(result, indent=2, sort_keys=True)
