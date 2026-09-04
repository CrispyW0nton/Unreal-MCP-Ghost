"""Offline smoke coverage for Workstream B.9 World Partition and HLOD tools."""

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


class TestB9WorldPartitionHLODTools(unittest.TestCase):
    def setUp(self):
        from tools.editor_tools import register_editor_tools

        self.mcp = _MockMCP()
        register_editor_tools(self.mcp)

    def test_b9_world_partition_hlod_tools_register(self):
        expected = {
            "wp_load_region",
            "wp_unload_region",
            "wp_create_data_layer",
            "hlod_generate",
            "hlod_assign_layer",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    def test_world_partition_hlod_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "route": command,
                "label": params.get("label"),
                "unloaded_count": 1,
                "data_layer": {"name": params.get("name"), "asset_path": params.get("asset_path")},
                "map": "/Game/Maps/OpenWorld",
                "builder_args": ["-SetupHLODs", "-BuildHLODs"],
                "assigned_count": len(params.get("actors") or [params.get("actor")]),
            }

        with patch("tools.editor_tools._send_unreal_command", side_effect=fake_send):
            payloads = [
                json.loads(self.mcp.tools["wp_load_region"](
                    ctx=None,
                    center=[100.0, 200.0, 0.0],
                    extent=[1000.0, 1000.0, 500.0],
                    label="Downtown",
                )),
                json.loads(self.mcp.tools["wp_unload_region"](
                    ctx=None,
                    label="Downtown",
                    exact=True,
                )),
                json.loads(self.mcp.tools["wp_create_data_layer"](
                    ctx=None,
                    name="Gameplay_POIs",
                    type="runtime",
                    asset_path="/Game/DataLayers/Gameplay_POIs",
                    loaded_in_editor=False,
                    initial_runtime_state="loaded",
                )),
                json.loads(self.mcp.tools["hlod_generate"](
                    ctx=None,
                    setup=True,
                    build=True,
                    force=True,
                    layer="HLODLayer_Buildings",
                    extra_args="-Verbose",
                )),
                json.loads(self.mcp.tools["hlod_assign_layer"](
                    ctx=None,
                    hlod_layer="/Game/HLOD/HLODLayer_Buildings",
                    actors=["Building_A", "Building_B"],
                )),
            ]

        stages = [
            "wp_load_region",
            "wp_unload_region",
            "wp_create_data_layer",
            "hlod_generate",
            "hlod_assign_layer",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertEqual(calls[0][1]["center"], [100.0, 200.0, 0.0])
        self.assertEqual(calls[0][1]["extent"], [1000.0, 1000.0, 500.0])
        self.assertEqual(calls[1][1]["label"], "Downtown")
        self.assertTrue(calls[1][1]["exact"])
        self.assertEqual(calls[2][1]["name"], "Gameplay_POIs")
        self.assertFalse(calls[2][1]["loaded_in_editor"])
        self.assertEqual(calls[2][1]["initial_runtime_state"], "loaded")
        self.assertTrue(calls[3][1]["force"])
        self.assertEqual(calls[3][1]["layer"], "HLODLayer_Buildings")
        self.assertEqual(calls[3][1]["extra_args"], "-Verbose")
        self.assertEqual(calls[4][1]["hlod_layer"], "/Game/HLOD/HLODLayer_Buildings")
        self.assertEqual(calls[4][1]["actors"], ["Building_A", "Building_B"])


if __name__ == "__main__":
    unittest.main()
