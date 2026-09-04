"""Offline coverage for the Insanitii ordinary errand station placement tool."""

from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path


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


class _PlacementConnection:
    def __init__(self):
        self.calls = []
        self.exec_count = 0

    def send_command(self, command, params):
        self.calls.append((command, params))
        if command == "ping":
            return {"message": "pong"}
        if command != "exec_python":
            return {"status": "error", "error": f"Unknown command: {command}"}

        self.exec_count += 1
        code = params.get("code", "")
        if self.exec_count == 1:
            payload = {"success": True, "loaded": True}
        elif "save_current_level" in code:
            payload = {"success": True, "saved_current_level": True}
        else:
            label = "unknown"
            for candidate in (
                "INS_TaskStation_Grocery_Corner",
                "INS_TaskStation_Laundry_Washer",
                "INS_TaskStation_Package_Dropoff",
                "INS_TaskStation_Commute_Car",
            ):
                if candidate in code:
                    label = candidate
                    break
            payload = {"success": True, "label": label, "created": False}
        return {"success": True, "result": {"output": json.dumps(payload)}}


class _PatchServerModule:
    def __init__(self, connection):
        self.fake = types.ModuleType("unreal_mcp_server")
        self.fake.get_unreal_connection = lambda: connection
        self.previous = None

    def __enter__(self):
        self.previous = sys.modules.get("unreal_mcp_server")
        sys.modules["unreal_mcp_server"] = self.fake

    def __exit__(self, exc_type, exc, tb):
        if self.previous is None:
            sys.modules.pop("unreal_mcp_server", None)
        else:
            sys.modules["unreal_mcp_server"] = self.previous


class TestInsanitiiErrandStationPlacement(unittest.TestCase):
    def test_tool_splits_load_four_placements_and_save(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _PlacementConnection()

        with _PatchServerModule(connection):
            report = mcp.tools["insanitii_place_ordinary_errand_stations"](ctx=None)

        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["placement_count"], 4)
        self.assertEqual(report["summary"]["placement_success_count"], 4)
        self.assertTrue(report["summary"]["load_success"])
        self.assertTrue(report["summary"]["save_success"])
        self.assertEqual(connection.exec_count, 6)
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
