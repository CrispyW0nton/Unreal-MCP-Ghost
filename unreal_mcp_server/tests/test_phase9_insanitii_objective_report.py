"""Offline coverage for the Insanitii Phase 3 objective-loop workflow."""

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


class _Phase3Connection:
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
            "class_checks": {
                "slice_objective_director": {"success": True, "class_path": "/Script/Insanitii.InsanitiiSliceObjectiveDirector"},
                "task_station": {"success": True, "class_path": "/Script/Insanitii.InsanitiiTaskStation"},
                "psychosis_event_director": {"success": True, "class_path": "/Script/Insanitii.InsanitiiPsychosisEventDirector"},
            },
            "actors": {
                "INS_SliceObjectiveDirector": {"success": True, "class_name": "InsanitiiSliceObjectiveDirector"},
                "INS_PsychosisEventDirector": {"success": True, "class_name": "InsanitiiPsychosisEventDirector"},
                "INS_TaskStation_Work_EmailTriage": {"success": True, "class_name": "InsanitiiTaskStation"},
                "INS_TaskStation_Food_Sandwich": {"success": True, "class_name": "InsanitiiTaskStation"},
                "INS_TaskStation_Medication": {"success": True, "class_name": "InsanitiiTaskStation"},
                "INS_TaskStation_Sleep_Bed": {"success": True, "class_name": "InsanitiiTaskStation"},
                "INS_TaskStation_Stress_OverwhelmingNoise": {"success": True, "class_name": "InsanitiiTaskStation"},
            },
            "objective_probe": {
                "success": True,
                "current_objective": "Make a sandwich before the day starts.",
                "progress_summary": "Food -- | Meds -- | Work -- | Stress -- | Psychosis -- | Sleep --",
                "completion_percent": 0.0,
                "stabilized_target": 0.45,
            },
            "station_probe": {
                "count": 5,
                "stations": [
                    {"label": "INS_TaskStation_Food_Sandwich", "mental_state_delta": 0.08},
                    {"label": "INS_TaskStation_Medication", "mental_state_delta": 0.22},
                    {"label": "INS_TaskStation_Work_EmailTriage", "mental_state_delta": 0.08},
                    {"label": "INS_TaskStation_Sleep_Bed", "mental_state_delta": 0.12},
                    {"label": "INS_TaskStation_Stress_OverwhelmingNoise", "mental_state_delta": 0.82},
                ],
            },
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


class TestInsanitiiObjectiveReport(unittest.TestCase):
    def test_report_passes_when_phase3_objective_loop_is_loaded_and_placed(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _Phase3Connection()

        with _PatchServerModule(connection):
            report = mcp.tools["insanitii_phase3_objective_report"](ctx=None, include_dialogs=False)

        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["native_class_count"], 3)
        self.assertTrue(report["summary"]["objective_actor_placed"])
        self.assertEqual(report["summary"]["task_station_count"], 5)
        self.assertEqual(report["summary"]["current_objective"], "Make a sandwich before the day starts.")
        self.assertEqual(report["summary"]["completion_percent"], 0.0)
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
