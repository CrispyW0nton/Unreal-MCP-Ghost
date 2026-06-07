"""Offline smoke coverage for Workstream B.6 Geometry Script tools."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


class _MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _assert_structured(testcase: unittest.TestCase, payload: dict, stage: str):
    for key in ("success", "stage", "message", "inputs", "outputs", "warnings", "errors", "log_tail", "meta"):
        testcase.assertIn(key, payload)
    testcase.assertEqual(payload["stage"], stage)
    testcase.assertEqual(payload["meta"]["tool"], stage)


class TestB6GeometryTools(unittest.TestCase):
    def setUp(self):
        from tools.geometry_tools import register_geometry_tools

        self.mcp = _MockMCP()
        register_geometry_tools(self.mcp)

    def test_b6_geometry_tools_register(self):
        expected = {
            "geom_create_dynamic_mesh",
            "geom_boolean_op",
            "geom_extrude",
            "geom_remesh",
            "geom_uv_unwrap",
            "geom_bake_to_static_mesh",
            "geom_apply_displacement",
        }
        self.assertEqual(expected, set(self.mcp.tools))

    def test_geometry_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "route": command,
                "actor_name": params.get("actor_name") or params.get("target_actor", "DM_Target"),
                "triangle_count": 12,
                "vertex_count": 8,
                "asset_path": params.get("asset_path"),
            }

        async def run():
            with patch("tools.geometry_tools._send", side_effect=fake_send):
                created = json.loads(await self.mcp.tools["geom_create_dynamic_mesh"](
                    ctx=None,
                    actor_name="DM_CoverBlock",
                    primitive="box",
                    dimensions=[200, 80, 120],
                    location=[10, 20, 30],
                    radial_steps=12,
                    overwrite=True,
                ))
                boolean = json.loads(await self.mcp.tools["geom_boolean_op"](
                    ctx=None,
                    target_actor="DM_CoverBlock",
                    tool_actor="DM_Cutter",
                    operation="subtract",
                    hide_tool=True,
                ))
                extrude = json.loads(await self.mcp.tools["geom_extrude"](
                    ctx=None,
                    actor_name="DM_CoverBlock",
                    distance=35.0,
                    direction=[0, 0, 1],
                    direction_mode="fixed",
                ))
                remesh = json.loads(await self.mcp.tools["geom_remesh"](
                    ctx=None,
                    actor_name="DM_CoverBlock",
                    target_triangle_count=1500,
                    iterations=10,
                    discard_attributes=True,
                ))
                uv = json.loads(await self.mcp.tools["geom_uv_unwrap"](
                    ctx=None,
                    actor_name="DM_CoverBlock",
                    method="xatlas",
                    texture_resolution=2048,
                ))
                bake = json.loads(await self.mcp.tools["geom_bake_to_static_mesh"](
                    ctx=None,
                    actor_name="DM_CoverBlock",
                    asset_path="/Game/Geometry/SM_CoverBlock_A",
                    enable_nanite=True,
                    overwrite=True,
                ))
                displacement = json.loads(await self.mcp.tools["geom_apply_displacement"](
                    ctx=None,
                    actor_name="DM_CoverBlock",
                    magnitude=12.0,
                    frequency=0.08,
                    seed=7,
                ))
            return created, boolean, extrude, remesh, uv, bake, displacement

        payloads = asyncio.run(run())
        stages = [
            "geom_create_dynamic_mesh",
            "geom_boolean_op",
            "geom_extrude",
            "geom_remesh",
            "geom_uv_unwrap",
            "geom_bake_to_static_mesh",
            "geom_apply_displacement",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertEqual(calls[0][1]["dimensions"], [200, 80, 120])
        self.assertTrue(calls[0][1]["overwrite"])
        self.assertEqual(calls[1][1]["operation"], "subtract")
        self.assertTrue(calls[1][1]["hide_tool"])
        self.assertEqual(calls[2][1]["distance"], 35.0)
        self.assertEqual(calls[3][1]["target_triangle_count"], 1500)
        self.assertTrue(calls[3][1]["discard_attributes"])
        self.assertEqual(calls[4][1]["texture_resolution"], 2048)
        self.assertTrue(calls[5][1]["enable_nanite"])
        self.assertEqual(calls[5][1]["asset_path"], "/Game/Geometry/SM_CoverBlock_A")
        self.assertEqual(calls[6][1]["seed"], 7)


if __name__ == "__main__":
    unittest.main()
