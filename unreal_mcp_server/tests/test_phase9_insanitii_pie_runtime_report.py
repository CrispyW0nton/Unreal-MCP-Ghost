"""Offline coverage for the Insanitii Phase 3 PIE runtime workflow."""

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


class _PieRuntimeConnection:
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

        if self.exec_count == 1:
            payload = {
                "success": True,
                "is_in_play_in_editor": False,
                "pie_world_count": 0,
                "pie_world_names": [],
            }
            return {"success": True, "result": {"output": json.dumps(payload)}}

        if self.exec_count == 2:
            payload = {
                "success": True,
                "requested_mode": "play",
                "launch_requested": True,
                "was_in_pie": False,
                "is_in_play_in_editor": False,
            }
            return {"success": True, "result": {"output": json.dumps(payload)}}

        if self.exec_count == 4:
            payload = {
                "success": True,
                "stop_requested": True,
                "is_in_play_in_editor": True,
            }
            return {"success": True, "result": {"output": json.dumps(payload)}}

        if self.exec_count == 5:
            payload = {
                "success": True,
                "is_in_play_in_editor": False,
                "pie_world_count": 0,
                "pie_world_names": [],
            }
            return {"success": True, "result": {"output": json.dumps(payload)}}

        before = {
            "controller_class": "BP_InsanitiiTemplatePlayerController_C",
            "controller_name": "BP_InsanitiiTemplatePlayerController_C_0",
            "pawn_class": "InsanitiiCharacter",
            "pawn_name": "BP_FirstPersonCharacter_C_0",
            "hud_class": "InsanitiiHUD",
            "hud_status": "Status \"\" | Time 0.00 | Color 1.00,1.00,1.00",
            "objective_marker_summary": "Anchor Clean | Instability 0.45 | Confidence 0.55 | Conflict false | FalseCue none | Target INS_TaskStation_Food_Sandwich",
            "completion_summary": "Complete false | Percent 0.00 | Objective \"Make a sandwich before the day starts.\" | Progress \"Food -- | Meds -- | Grocery -- | Laundry -- | Package -- | Commute -- | Work -- | Stress -- | Psychosis -- | Sleep --\"",
            "task_feedback_pulse": 0.0,
            "task_feedback_color_shift": 0.0,
            "mental_state": 0.55,
            "focus_charges": 2.0,
            "breathe_cooldown": 0.0,
            "in_psychosis_event": False,
            "objective_text": "Make a sandwich before the day starts.",
            "objective_progress": "Food -- | Meds -- | Grocery -- | Laundry -- | Package -- | Commute -- | Work -- | Stress -- | Psychosis -- | Sleep --",
            "objective_completion_percent": 0.0,
            "psychosis_summary": "No active psychosis event.",
            "psychosis_active": False,
            "station_count": 9,
            "world_reactivity_tracked_count": 40,
            "world_reactivity_intensity": 0.0,
            "world_reactivity_pattern_actor_count": 8,
            "world_reactivity_pattern_intensity": 0.0,
            "world_reactivity_summary": "Reactive actors: 40 | Scale 1.00 | Intensity 0.00 | Pattern 0.00 | PatternText 8 | Tag InsanitiiWorldReactive",
            "cash_balance": 68.0,
            "formatted_time": "07:15",
        }
        after = {
            **before,
            "mental_state": 1.0,
            "objective_text": "Day 1 complete.",
            "objective_progress": "Food OK | Meds OK | Grocery OK | Laundry OK | Package OK | Commute OK | Work OK | Stress OK | Psychosis OK | Sleep OK",
            "objective_completion_percent": 1.0,
            "psychosis_summary": "Recovered from Chase.",
            "psychosis_active": False,
            "hud_status": "Status \"Task complete: Sleep Until Morning.\" | Time 1.50 | Color 0.36,1.00,0.62",
            "objective_marker_summary": "Anchor Clean | Instability 0.00 | Confidence 1.00 | Conflict false | FalseCue none | Target None",
            "completion_summary": "Complete true | Percent 1.00 | Objective \"Day 1 complete. You made it through.\" | Progress \"Food OK | Meds OK | Grocery OK | Laundry OK | Package OK | Commute OK | Work OK | Stress OK | Psychosis OK | Sleep OK\"",
        }
        task_steps = [
            {"step": "food", "station": "INS_TaskStation_Food_Sandwich", "after": {"hud_status": "Status \"Task complete: Make a Sandwich.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": -0.22, "task_feedback_color_shift": -0.12}},
            {"step": "medication", "station": "INS_TaskStation_Medication", "after": {"hud_status": "Status \"Task complete: Take Medication.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": -0.22, "task_feedback_color_shift": -0.12}},
            {"step": "grocery", "station": "INS_TaskStation_Grocery_Corner", "after": {"hud_status": "Status \"Task complete: Buy Groceries.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": -0.22, "task_feedback_color_shift": -0.12}},
            {"step": "laundry", "station": "INS_TaskStation_Laundry_Washer", "after": {"hud_status": "Status \"Task complete: Do Laundry.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": -0.22, "task_feedback_color_shift": -0.12}},
            {"step": "package", "station": "INS_TaskStation_Package_Dropoff", "after": {"hud_status": "Status \"Task complete: Deliver Package.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": 0.0, "task_feedback_color_shift": 0.0}},
            {"step": "commute", "station": "INS_TaskStation_Commute_Car", "after": {"hud_status": "Status \"Task complete: Drive to Work.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": 0.0, "task_feedback_color_shift": 0.0}},
            {"step": "work", "station": "INS_TaskStation_Work_EmailTriage", "after": {"hud_status": "Status \"Task complete: Work: Email Triage.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": 0.0, "task_feedback_color_shift": 0.0}},
            {"step": "stress", "station": "INS_TaskStation_Stress_OverwhelmingNoise", "after": {"hud_status": "Status \"Task complete: Endure Overwhelming Noise.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": 0.0, "task_feedback_color_shift": 0.0, "world_reactivity_intensity": 0.7, "world_reactivity_pattern_intensity": 0.35}},
            {"step": "sleep", "station": "INS_TaskStation_Sleep_Bed", "after": {"hud_status": "Status \"Task complete: Sleep Until Morning.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": -0.22, "task_feedback_color_shift": -0.12}},
        ]
        payload = {
            "success": True,
            "requested_mode": "play",
            "launch_requested": True,
            "was_in_pie": False,
            "is_in_play_in_editor": True,
            "pie_world_count": 1,
            "pie_world_names": ["UEDPIE_0_Lvl_FirstPerson"],
            "world_name": "UEDPIE_0_Lvl_FirstPerson",
            "runtime": {
                "before_exercise": before,
                "after_exercise": after,
            },
            "objective_anchor_samples": {
                "clean": "Anchor Clean | Instability 0.00 | Confidence 1.00 | Conflict false | FalseCue none | Target INS_TaskStation_Food_Sandwich",
                "strained": "Anchor Strained | Instability 0.85 | Confidence 0.15 | Conflict false | FalseCue none | Target INS_TaskStation_Food_Sandwich",
                "psychosis": "Anchor Verify | Instability 1.00 | Confidence 0.00 | Conflict false | FalseCue none | Target INS_TaskStation_Food_Sandwich",
                "false_cue": "Anchor Verify | Instability 1.00 | Confidence 0.00 | Conflict true | FalseCue active | Target INS_TaskStation_Food_Sandwich",
            },
            "exercise": {
                "requested": True,
                "steps": task_steps,
                "errors": [],
                "stabilization_tools": {
                    "breathe_result": True,
                    "breathe_after": {"hud_status": "Status \"Breathing steadied you. Mental state 55%.\" | Time 1.50 | Color 0.42,0.96,1.00", "task_feedback_pulse": -0.22, "task_feedback_color_shift": -0.12},
                    "focus_result": True,
                    "focus_after": {"hud_status": "Status \"Focus anchor held. Charges 90.\" | Time 1.50 | Color 0.42,0.96,1.00", "task_feedback_pulse": -0.22, "task_feedback_color_shift": -0.12},
                },
                "friction_slip": {
                    "station": "INS_TaskStation_Grocery_Corner",
                    "station_used": False,
                    "last_use_succeeded": False,
                    "friction_risk": 1.0,
                    "requires_stabilized_retry": True,
                    "used_stabilized_grace": False,
                    "after": {"hud_status": "Status \"Task slipped: stabilize and try again. Friction risk 100%.\" | Time 1.50 | Color 1.00,0.24,0.28", "task_feedback_pulse": 0.28, "task_feedback_color_shift": 0.12},
                },
                "friction_unrecovered_retry": {
                    "station": "INS_TaskStation_Grocery_Corner",
                    "station_used": False,
                    "last_use_succeeded": False,
                    "friction_risk": 1.0,
                    "requires_stabilized_retry": True,
                    "used_stabilized_grace": False,
                    "feedback": "Too overwhelmed. Breathe or focus before trying again.",
                    "after": {"hud_status": "Status \"Task slipped: stabilize and try again. Friction risk 100%.\" | Time 1.50 | Color 1.00,0.24,0.28", "task_feedback_pulse": 0.28, "task_feedback_color_shift": 0.12},
                },
                "friction_stabilized_retry": {
                    "station": "INS_TaskStation_Grocery_Corner",
                    "station_used": True,
                    "last_use_succeeded": True,
                    "friction_risk": 0.0,
                    "requires_stabilized_retry": False,
                    "used_stabilized_grace": True,
                    "after": {"hud_status": "Status \"Task complete: Buy Groceries.\" | Time 1.50 | Color 0.36,1.00,0.62", "task_feedback_pulse": -0.22, "task_feedback_color_shift": -0.12},
                },
                "fresh_start_after_preflight": before,
                "after_psychosis_start": {**before, "psychosis_active": True},
                "after_psychosis_end": after,
            },
            "stop": {
                "requested": True,
                "is_in_play_in_editor": False,
                "pie_world_count": 0,
                "pie_world_names": [],
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


class TestInsanitiiPieRuntimeReport(unittest.TestCase):
    def test_report_passes_when_pie_loop_boots_exercises_and_stops(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _PieRuntimeConnection()

        with _PatchServerModule(connection):
            report = mcp.tools["insanitii_phase3_pie_runtime_report"](ctx=None, include_dialogs=False)

        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["pie_world_count"], 1)
        self.assertEqual(report["summary"]["pawn_class"], "InsanitiiCharacter")
        self.assertEqual(report["summary"]["hud_class"], "InsanitiiHUD")
        self.assertGreaterEqual(report["summary"]["station_count"], 9)
        self.assertGreaterEqual(report["summary"]["world_reactivity_tracked_count"], 40)
        self.assertGreaterEqual(report["summary"]["world_reactivity_pattern_actor_count"], 5)
        self.assertEqual(report["summary"]["exercise_step_count"], 9)
        self.assertEqual(report["summary"]["exercise_error_count"], 0)
        self.assertEqual(report["summary"]["objective_completion_percent"], 1.0)
        self.assertIn("Complete true", report["summary"]["completion_summary"])
        fresh_start = report["checks"]["exercise"]["fresh_start_after_preflight"]
        self.assertIn("Psychosis --", fresh_start["objective_progress"])
        self.assertEqual(fresh_start["objective_completion_percent"], 0.0)
        self.assertTrue(report["checks"]["exercise"]["friction_slip"]["requires_stabilized_retry"])
        self.assertTrue(report["checks"]["exercise"]["friction_unrecovered_retry"]["requires_stabilized_retry"])
        self.assertTrue(report["checks"]["exercise"]["friction_stabilized_retry"]["used_stabilized_grace"])
        self.assertTrue(report["summary"]["stopped_cleanly"])
        self.assertEqual(report["warnings"], [])
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
