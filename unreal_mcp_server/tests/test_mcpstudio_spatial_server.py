from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcpstudio_spatial_server import (
    MCPSTUDIO_FORBIDDEN_TOOL_NAMES,
    MCPSTUDIO_SPATIAL_TOOL_NAMES,
    _AllowlistedRegistrationSurface,
)
from tools.spatial_awareness_tools import register_spatial_awareness_tools
from tools.static_mesh_section_tools import register_static_mesh_section_tools
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
from tools.exec_substrate import _parse_ue_json


class _FakeMcp:
    def __init__(self) -> None:
        self.registered: list[str] = []

    def tool(self, *args, **kwargs):
        def decorate(function):
            self.registered.append(str(kwargs.get("name") or function.__name__))
            return function

        return decorate


class McpStudioSpatialServerTests(unittest.TestCase):
    def test_bridge_errors_remain_explicit_structured_evidence(self) -> None:
        result = _parse_ue_json(
            {"status": "error", "error": "authenticated spool rejected request"}
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "bridge_error")
        self.assertEqual(result["errors"], ["authenticated spool rejected request"])

        exception_result = _parse_ue_json(
            {"success": False, "message": "spool response digest mismatched"}
        )
        self.assertEqual(exception_result["stage"], "bridge_error")
        self.assertEqual(exception_result["message"], "spool response digest mismatched")
        self.assertEqual(exception_result["errors"], ["spool response digest mismatched"])

    def test_isolated_stdio_launch_lists_the_exact_catalog(self) -> None:
        server_path = Path(__file__).resolve().parents[1] / "mcpstudio_spatial_server.py"

        async def list_tool_names() -> set[str]:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-I", "-B", "-u", "-X", "utf8", str(server_path)],
            )
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    response = await session.list_tools()
                    return {tool.name for tool in response.tools}

        tool_names = asyncio.run(asyncio.wait_for(list_tool_names(), timeout=30.0))
        self.assertEqual(tool_names, set(MCPSTUDIO_SPATIAL_TOOL_NAMES))
        self.assertFalse(tool_names & set(MCPSTUDIO_FORBIDDEN_TOOL_NAMES))

    def test_catalog_is_exact_and_forbidden_tools_are_absent(self) -> None:
        fake = _FakeMcp()
        surface = _AllowlistedRegistrationSurface(fake, MCPSTUDIO_SPATIAL_TOOL_NAMES)
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

        self.assertEqual(set(fake.registered), set(MCPSTUDIO_SPATIAL_TOOL_NAMES))
        self.assertEqual(surface.seen_allowed_names, set(MCPSTUDIO_SPATIAL_TOOL_NAMES))
        self.assertFalse(set(fake.registered) & set(MCPSTUDIO_FORBIDDEN_TOOL_NAMES))

    def test_unreviewed_future_tool_fails_closed(self) -> None:
        fake = _FakeMcp()
        surface = _AllowlistedRegistrationSurface(fake, frozenset({"reviewed"}))

        @surface.tool()
        def unreviewed():
            return "not registered"

        self.assertEqual(unreviewed(), "not registered")
        self.assertEqual(fake.registered, [])


if __name__ == "__main__":
    unittest.main()
