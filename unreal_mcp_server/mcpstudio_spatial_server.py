"""Narrow Unreal-MCP-Ghost spatial and exact-pilot surface for MCPStudio.

The regular Unreal-MCP-Ghost server intentionally remains comprehensive. This
entry point is different: its catalog is fixed to reviewed spatial observation
and planning tools plus explicitly pinned pilot operators. Registration drift
fails closed and generic Python or bridge-command execution is never exposed
as an MCP tool.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import sys
from typing import Any

# MCPStudio launches this fixed entry point with Python isolated mode (`-I`).
# Isolated script execution deliberately omits the script directory from
# sys.path, so add only this entry point's own resolved directory before local
# imports. No caller-controlled path is accepted.
_SERVER_ROOT = str(Path(__file__).resolve().parent)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)

from mcp.server.fastmcp import FastMCP

from tools.enclave_material_pilot_tools import register_enclave_material_pilot_tools
from tools.enclave_ebon_hawk_handoff_tools import register_enclave_ebon_hawk_handoff_tools
from tools.enclave_landing_scale_bake_tools import register_enclave_landing_scale_bake_tools
from tools.enclave_staged_prop_scale_bake_tools import register_enclave_staged_prop_scale_bake_tools
from tools.enclave_landing_material_pass_tools import register_enclave_landing_material_pass_tools
from tools.enclave_landing_ground_refine_tools import register_enclave_landing_ground_refine_tools
from tools.enclave_landing_ground_material_repair_tools import register_enclave_landing_ground_material_repair_tools
from tools.enclave_landing_exposure_repair_tools import register_enclave_landing_exposure_repair_tools
from tools.enclave_landing_daylight_pass_tools import register_enclave_landing_daylight_pass_tools
from tools.enclave_landing_lighting_audit_tools import register_enclave_landing_lighting_audit_tools
from tools.enclave_landing_review_capture_tools import register_enclave_landing_review_capture_tools
from tools.static_mesh_section_tools import register_static_mesh_section_tools
from tools.spatial_awareness_tools import register_spatial_awareness_tools


MCPSTUDIO_SPATIAL_TOOL_NAMES = frozenset(
    {
        "inspect_static_mesh_sections",
        "enclave_sandstone_pilot",
        "enclave_ebon_hawk_handoff",
        "enclave_landing_scale_bake",
        "enclave_staged_prop_scale_bake",
        "enclave_landing_material_pass",
        "enclave_landing_ground_refine",
        "enclave_landing_ground_material_repair",
        "enclave_landing_exposure_repair",
        "enclave_landing_daylight_pass",
        "enclave_landing_lighting_audit",
        "enclave_landing_review_capture",
        "spatial_scene_overview",
        "spatial_analyze_room",
        "spatial_infer_functional_zones",
        "spatial_query_actors",
        "spatial_describe_actor",
        "spatial_proximity_map",
        "spatial_view_context",
        "spatial_surface_probe",
        "spatial_validate_placement",
        "spatial_infer_placement_policy",
        "spatial_catalog_project_assets",
        "spatial_resolve_project_assets",
        "spatial_preflight_interior_layout",
        "spatial_preflight_candidate_clearance",
        "spatial_assess_environment_coherence",
        "spatial_compile_worldbuilding_readiness",
        "spatial_plan_worldbuilding_work_order",
        "spatial_content_selection_context",
    }
)

MCPSTUDIO_FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "exec_python",
        "call_bridge_command",
        "spatial_apply_composition_plan",
        "spatial_place_selected_assets",
        "spatial_select_actors",
        "spatial_add_asset_to_scene",
    }
)


class _AllowlistedRegistrationSurface:
    """Present a decorator-compatible, fail-closed view of a FastMCP server."""

    def __init__(self, server: FastMCP, allowed_names: frozenset[str]) -> None:
        self._server = server
        self._allowed_names = allowed_names
        self.seen_allowed_names: set[str] = set()

    def tool(self, *decorator_args: Any, **decorator_kwargs: Any) -> Callable[..., Any]:
        def decorate(function: Callable[..., Any]) -> Callable[..., Any]:
            declared_name = str(
                decorator_kwargs.get("name") or getattr(function, "__name__", "")
            )
            if declared_name not in self._allowed_names:
                return function
            if declared_name in self.seen_allowed_names:
                raise RuntimeError(f"Duplicate MCPStudio Ghost tool: {declared_name}")
            self.seen_allowed_names.add(declared_name)
            return self._server.tool(*decorator_args, **decorator_kwargs)(function)

        return decorate


def build_mcpstudio_spatial_server() -> FastMCP:
    server = FastMCP(
        "Unreal-MCP-Ghost Spatial for MCPStudio",
        instructions=(
            "Unreal Engine spatial observation and exact-version pilot work "
            "through the UnrealMCP plugin. Generic execution is not part of "
            "this catalog; mutations are confined to explicitly pinned tools."
        ),
    )
    surface = _AllowlistedRegistrationSurface(server, MCPSTUDIO_SPATIAL_TOOL_NAMES)
    register_static_mesh_section_tools(surface)
    register_enclave_material_pilot_tools(surface)
    register_enclave_ebon_hawk_handoff_tools(surface)
    register_enclave_landing_scale_bake_tools(surface)
    register_enclave_staged_prop_scale_bake_tools(surface)
    register_enclave_landing_material_pass_tools(surface)
    register_enclave_landing_ground_refine_tools(surface)
    register_enclave_landing_ground_material_repair_tools(surface)
    register_enclave_landing_exposure_repair_tools(surface)
    register_enclave_landing_daylight_pass_tools(surface)
    register_enclave_landing_lighting_audit_tools(surface)
    register_enclave_landing_review_capture_tools(surface)
    register_spatial_awareness_tools(surface)

    missing = MCPSTUDIO_SPATIAL_TOOL_NAMES - surface.seen_allowed_names
    forbidden = MCPSTUDIO_FORBIDDEN_TOOL_NAMES & surface.seen_allowed_names
    if missing or forbidden:
        raise RuntimeError(
            "MCPStudio Ghost spatial catalog failed closed: "
            f"missing={sorted(missing)}, forbidden={sorted(forbidden)}"
        )
    return server


def main() -> None:
    build_mcpstudio_spatial_server().run(transport="stdio")


if __name__ == "__main__":
    main()
