"""Offline coverage for the Insanitii audio feedback wiring report."""

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


class _AudioReportConnection:
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
            "level_path": "/Game/FirstPerson/Lvl_FirstPerson",
            "assets": {
                "room_tone": {"exists": True, "class": "SoundWave", "looping": True},
                "stress_layer": {"exists": True, "class": "SoundWave", "looping": True},
                "stabilize": {"exists": True, "class": "SoundWave", "looping": False},
                "psychosis_start": {"exists": True, "class": "SoundWave", "looping": False},
                "psychosis_end": {"exists": True, "class": "SoundWave", "looping": False},
            },
            "actor": {
                "name": "InsanitiiAudioFeedbackDirector_0",
                "label": "INS_AudioFeedbackDirector",
                "class": "InsanitiiAudioFeedbackDirector",
            },
            "slot_assignments": {
                key: {"assigned": True, "matches_expected": True}
                for key in ("room_tone", "stress_layer", "stabilize", "psychosis_start", "psychosis_end")
            },
            "looping_expected": {
                "room_tone": True,
                "stress_layer": True,
                "stabilize": False,
                "psychosis_start": False,
                "psychosis_end": False,
            },
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


class TestInsanitiiAudioFeedbackReport(unittest.TestCase):
    def test_report_passes_when_actor_assets_and_slots_are_wired(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _AudioReportConnection()

        with _PatchServerModule(connection):
            report = mcp.tools["insanitii_audio_feedback_report"](ctx=None)

        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "pass")
        self.assertTrue(report["summary"]["actor_present"])
        self.assertEqual(report["summary"]["asset_count"], 5)
        self.assertEqual(report["summary"]["assigned_slot_count"], 5)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
