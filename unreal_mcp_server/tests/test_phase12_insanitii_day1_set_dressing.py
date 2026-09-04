"""Offline coverage for the Insanitii Day 1 set-dressing placement tool."""

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


class _SetDressingConnection:
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
            if '"kind": "text"' in code:
                kind = "text"
            elif '"kind": "light"' in code:
                kind = "light"
            else:
                kind = "static_mesh"
            payload = {"success": True, "kind": kind, "label": "mock", "created": False}
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


class TestInsanitiiDay1SetDressing(unittest.TestCase):
    def test_tool_places_route_props_text_and_lights_in_chunks(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _SetDressingConnection()

        with _PatchServerModule(connection):
            report = mcp.tools["insanitii_place_day1_set_dressing"](ctx=None)

        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["placement_count"], 40)
        self.assertEqual(report["summary"]["placement_success_count"], 40)
        self.assertEqual(report["summary"]["kind_counts"]["static_mesh"], 26)
        self.assertEqual(report["summary"]["kind_counts"]["text"], 7)
        self.assertEqual(report["summary"]["kind_counts"]["light"], 7)
        self.assertTrue(report["summary"]["load_success"])
        self.assertTrue(report["summary"]["save_success"])
        self.assertEqual(connection.exec_count, 42)
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
