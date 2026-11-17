"""MCP tools for working with several Unreal editors at once (one per project)."""
from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

import instance_registry


def register_instance_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def list_unreal_instances() -> str:
        """List the open Unreal editors that run the UnrealMCP bridge (project, pid, port) and which one this
        session targets. Read-only."""
        return json.dumps({
            "selected_project": instance_registry.selected_project(),
            "instances": instance_registry.instances_report(),
        }, indent=2)

    @mcp.tool()
    def select_unreal_instance(project: str = "") -> str:
        """Target the editor open on `project` (a .uproject path or a project name) for the rest of this session.
        An empty value clears the choice (then UNREAL_MCP_PROJECT, or the only open editor, is used)."""
        instance_registry.select_project(project or None)
        try:
            host, port, inst = instance_registry.resolve_target(instance_registry.selected_project())
        except instance_registry.TargetResolutionError as e:
            return json.dumps({"status": "error", "error": str(e)})
        return json.dumps({"status": "success", "host": host, "port": port,
                           "instance": inst.describe() if inst else None,
                           "selected_project": instance_registry.selected_project()})
