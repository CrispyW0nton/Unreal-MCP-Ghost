"""Offline coverage for the Insanitii save/load report."""

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


class _SaveLoadConnection:
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
        if "is_in_play_in_editor" in code and "editor_request_begin_play" not in code and "editor_request_end_play" not in code:
            payload = {"success": True, "is_in_play_in_editor": False, "pie_world_count": 0, "pie_world_names": []}
        elif "editor_request_begin_play" in code:
            payload = {"success": True, "requested_mode": "play", "launch_requested": True, "was_in_pie": False, "is_in_play_in_editor": False}
        elif "editor_request_end_play" in code:
            payload = {"success": True, "stop_requested": True, "is_in_play_in_editor": True}
        else:
            before = {"day": 1, "minute": 512.0, "cash": 250, "mental_state": 0.7}
            payload = {
                "success": True,
                "save_success": True,
                "load_success": True,
                "save_exists": True,
                "before": before,
                "saved": before,
                "mutated": {"day": 3, "minute": 635.0, "cash": 327, "mental_state": 0.47},
                "restored": before,
                "restored_matches": {"day": True, "cash": True, "mental_state": True},
                "errors": [],
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


class TestInsanitiiSaveLoadReport(unittest.TestCase):
    def test_report_passes_when_save_load_restores_core_state(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _SaveLoadConnection()

        with _PatchServerModule(connection):
            report = mcp.tools["insanitii_save_load_report"](ctx=None, wait_seconds=1.0)

        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["summary"]["save_success"])
        self.assertTrue(report["summary"]["load_success"])
        self.assertTrue(report["summary"]["save_exists"])
        self.assertEqual(report["summary"]["restored_matches"]["day"], True)
        self.assertEqual(report["summary"]["restored_matches"]["cash"], True)
        self.assertEqual(report["summary"]["restored_matches"]["mental_state"], True)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
