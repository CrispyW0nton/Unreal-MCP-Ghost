"""Offline smoke coverage for Workstream B.10 Chaos destruction and cloth tools."""

from __future__ import annotations

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


class TestB10ChaosTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.chaos_tools import register_chaos_tools

        self.mcp = _MockMCP()
        register_chaos_tools(self.mcp)

    def test_b10_chaos_tools_register(self):
        expected = {
            "chaos_create_solver_actor",
            "chaos_configure_solver_actor",
            "chaos_inspect_geometry_collection",
            "chaos_configure_geometry_collection",
            "chaos_configure_cloth_component",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    async def test_chaos_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "route": command,
                "actor_name": params.get("actor_name", "ChaosActor"),
                "component_name": params.get("component_name", "SkeletalMeshComponent0"),
                "generate_break_data": params.get("generate_break_data", False),
                "damage_thresholds": params.get("damage_thresholds", []),
                "cloth_max_distance_scale": params.get("cloth_max_distance_scale", 1.0),
            }

        with patch("tools.chaos_tools._send", side_effect=fake_send):
            payloads = [
                json.loads(await self.mcp.tools["chaos_create_solver_actor"](
                    ctx=None,
                    actor_name="ChaosSolver_Destruction",
                    set_as_world_solver=True,
                    overwrite=True,
                )),
                json.loads(await self.mcp.tools["chaos_configure_solver_actor"](
                    ctx=None,
                    actor_name="ChaosSolver_Destruction",
                    generate_break_data=True,
                    optimize_runtime_memory=True,
                    per_advance_breaks_allowed=12,
                )),
                json.loads(await self.mcp.tools["chaos_inspect_geometry_collection"](
                    ctx=None,
                    actor_name="GC_Barrier_A",
                )),
                json.loads(await self.mcp.tools["chaos_configure_geometry_collection"](
                    ctx=None,
                    actor_name="GC_Barrier_A",
                    simulate_physics=True,
                    notify_breaks=True,
                    damage_thresholds=[500000.0, 50000.0, 5000.0],
                    solver_actor="ChaosSolver_Destruction",
                )),
                json.loads(await self.mcp.tools["chaos_configure_cloth_component"](
                    ctx=None,
                    actor_name="BP_CloakedHero_0",
                    component_name="HeroMesh",
                    update_in_editor=True,
                    cloth_max_distance_scale=0.75,
                    force_reset=True,
                )),
            ]

        stages = [
            "chaos_create_solver_actor",
            "chaos_configure_solver_actor",
            "chaos_inspect_geometry_collection",
            "chaos_configure_geometry_collection",
            "chaos_configure_cloth_component",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertTrue(calls[0][1]["set_as_world_solver"])
        self.assertTrue(calls[0][1]["overwrite"])
        self.assertTrue(calls[1][1]["generate_break_data"])
        self.assertEqual(calls[1][1]["per_advance_breaks_allowed"], 12)
        self.assertEqual(calls[2][1]["actor_name"], "GC_Barrier_A")
        self.assertEqual(calls[3][1]["damage_thresholds"], [500000.0, 50000.0, 5000.0])
        self.assertEqual(calls[3][1]["solver_actor"], "ChaosSolver_Destruction")
        self.assertEqual(calls[4][1]["component_name"], "HeroMesh")
        self.assertEqual(calls[4][1]["cloth_max_distance_scale"], 0.75)
        self.assertTrue(calls[4][1]["force_reset"])


if __name__ == "__main__":
    unittest.main()
