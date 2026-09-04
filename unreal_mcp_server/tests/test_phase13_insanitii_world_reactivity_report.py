"""Offline coverage for the Insanitii world reactivity report."""

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


class _WorldReactivityConnection:
    def __init__(self):
        self.calls = []

    def send_command(self, command, params):
        self.calls.append((command, params))
        if command == "ping":
            return {"message": "pong"}
        if command != "exec_python":
            return {"status": "error", "error": f"Unknown command: {command}"}

        payload = {
            "success": True,
            "errors": [],
            "class": {
                "success": True,
                "class_path": "/Script/Insanitii.InsanitiiWorldReactiveDirector",
                "loaded_name": "InsanitiiWorldReactiveDirector",
            },
            "director": {
                "success": True,
                "label": "INS_WorldReactiveDirector",
                "class": "InsanitiiWorldReactiveDirector",
                "tracked_actor_count": 40,
                "pattern_flood_actor_count": 8,
                "current_reactive_intensity": 0.25,
                "current_pattern_flood_intensity": 0.15,
                "debug_summary": "Reactive actors: 40 | Scale 1.00 | Intensity 0.25 | Pattern 0.15 | PatternText 8 | Tag InsanitiiWorldReactive",
                "reactive_actor_tag": "InsanitiiWorldReactive",
            },
            "reactive_actor_count": 40,
            "reactive_actors": [],
        }
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


class TestInsanitiiWorldReactivityReport(unittest.TestCase):
    def test_report_passes_when_director_tracks_tagged_day1_actors(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _WorldReactivityConnection()

        with _PatchServerModule(connection):
            report = mcp.tools["insanitii_world_reactivity_report"](ctx=None)

        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["summary"]["class_visible"])
        self.assertTrue(report["summary"]["director_present"])
        self.assertGreaterEqual(report["summary"]["reactive_actor_count"], 40)
        self.assertGreaterEqual(report["summary"]["tracked_actor_count"], 40)
        self.assertGreaterEqual(report["summary"]["pattern_flood_actor_count"], 5)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
