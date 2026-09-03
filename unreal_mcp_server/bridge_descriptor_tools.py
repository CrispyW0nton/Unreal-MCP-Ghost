"""MCP tools exposing Ghost TCP bridge descriptors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import Context, FastMCP

from bridge_descriptors import BridgeDescriptorRegistry


def register_bridge_descriptor_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def bridge_descriptor_summary(
        ctx: Context,
        registry_path: str = "",
    ) -> str:
        """Summarize the TCP bridge command registry as native-alignment metadata."""

        registry = _registry(registry_path)
        return json.dumps(registry.summary(), indent=2, sort_keys=True)

    @mcp.tool()
    def list_bridge_toolsets(
        ctx: Context,
        category: str = "",
        status: str = "",
        response_format: str = "text",
        registry_path: str = "",
    ) -> str:
        """List TCP bridge command categories as Toolset-like descriptors."""

        registry = _registry(registry_path)
        return registry.list_toolsets(
            category=category,
            status=status,
            response_format=response_format,
        )

    @mcp.tool()
    def describe_bridge_toolset(
        ctx: Context,
        toolset_name: str,
        command_filter: str = "",
        registry_path: str = "",
    ) -> str:
        """Describe one bridge command category and its command descriptors."""

        registry = _registry(registry_path)
        return registry.describe_toolset(toolset_name, command_filter=command_filter)

    @mcp.tool()
    def search_bridge_commands(
        ctx: Context,
        query: str = "",
        category: str = "",
        status: str = "",
        mutation_class: str = "",
        include_sources: bool = False,
        limit: int = 50,
        registry_path: str = "",
    ) -> str:
        """Search TCP bridge command descriptors by text, category, status, or mutation class."""

        registry = _registry(registry_path)
        result = registry.search_commands(
            query=query,
            category=category,
            status=status,
            mutation_class=mutation_class,
            include_sources=include_sources,
            limit=limit,
        )
        return json.dumps(result, indent=2, sort_keys=True)

    @mcp.tool()
    def call_bridge_command(
        ctx: Context,
        command_name: str,
        params: Optional[dict[str, Any]] = None,
        params_json: str = "",
        dry_run: bool = True,
        allow_mutation: bool = False,
        allow_unknown: bool = False,
        registry_path: str = "",
    ) -> str:
        """Plan or execute one Ghost TCP bridge command through descriptor gates.

        This is a clean-room ToolsetRegistry-style adapter over Ghost's own TCP
        bridge. It is dry-run by default; mutating commands require
        allow_mutation=true before execution.
        """

        try:
            safe_params = _parse_params(params=params, params_json=params_json)
        except ValueError as exc:
            return json.dumps(
                {
                    "schema": "unreal_mcp_ghost.bridge_command_call.v1",
                    "success": False,
                    "dry_run": dry_run,
                    "will_execute": False,
                    "error": str(exc),
                    "command": command_name,
                    "params": {},
                },
                indent=2,
                sort_keys=True,
            )

        registry = _registry(registry_path)
        plan = registry.command_call_plan(
            command_name=command_name,
            params=safe_params,
            dry_run=dry_run,
            allow_mutation=allow_mutation,
            allow_unknown=allow_unknown,
        )
        if not plan.get("success") or plan.get("dry_run") or not plan.get("will_execute"):
            return json.dumps(plan, indent=2, sort_keys=True)

        execution = _send_bridge_command(str(plan.get("command", command_name)), safe_params)
        payload = dict(plan)
        payload["execution"] = execution
        payload["success"] = bool(execution.get("success", False))
        if not payload["success"]:
            payload["error"] = execution.get("error") or execution.get("message") or "Bridge command execution failed."
        return json.dumps(payload, indent=2, sort_keys=True)


def _registry(registry_path: str) -> BridgeDescriptorRegistry:
    path = Path(registry_path).expanduser().resolve() if registry_path else None
    return BridgeDescriptorRegistry(path)


def _parse_params(*, params: Optional[dict[str, Any]], params_json: str) -> dict[str, Any]:
    if params is not None:
        if not isinstance(params, dict):
            raise ValueError("params must be a JSON object.")
        return dict(params)

    if not str(params_json or "").strip():
        return {}

    try:
        parsed = json.loads(params_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"params_json must be a JSON object: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("params_json must decode to a JSON object.")
    return parsed


def _send_bridge_command(command: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        from unreal_mcp_server import get_unreal_connection

        unreal = get_unreal_connection()
        if unreal is None:
            return {
                "success": False,
                "command": command,
                "params": params,
                "error": "Could not connect to Unreal Engine TCP bridge.",
            }

        response = unreal.send_command(command, params) or {}
        if not isinstance(response, dict):
            return {
                "success": False,
                "command": command,
                "params": params,
                "error": "Bridge returned a non-object response.",
                "raw_response": str(response),
            }

        result = dict(response)
        result.setdefault("command", command)
        result.setdefault("params", params)
        result.setdefault("success", result.get("status") != "error" and not bool(result.get("error")))
        return result
    except Exception as exc:
        return {
            "success": False,
            "command": command,
            "params": params,
            "error": f"{type(exc).__name__}: {exc}",
        }
