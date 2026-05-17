"""Offline coverage for the Insanitii Phase 2 lifestyle-readiness workflow."""

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


class _Phase2Connection:
    def __init__(self):
        self.calls = []

    def send_command(self, command, params):
        self.calls.append((command, params))
        if command == "ping":
            return {"status": "success"}
        if command != "exec_python":
            return {"status": "error", "error": f"Unknown command: {command}"}

        payload = {
            "success": True,
            "class_checks": {
                "time_of_day_component": {"success": True, "class_path": "/Script/Insanitii.InsanitiiTimeOfDayComponent"},
                "economy_component": {"success": True, "class_path": "/Script/Insanitii.InsanitiiEconomyComponent"},
                "lifestyle_manager": {"success": True, "class_path": "/Script/Insanitii.InsanitiiLifestyleManager"},
            },
            "blueprint": {
                "success": True,
                "asset_path": "/Game/Insanitii/Gameplay/Lifestyles/BP_LifestyleManager",
                "has_generated_class": True,
                "generated_class": "/Game/Insanitii/Gameplay/Lifestyles/BP_LifestyleManager.BP_LifestyleManager_C",
                "parent_class": "/Script/Insanitii.InsanitiiLifestyleManager",
            },
            "actor": {
                "success": True,
                "label": "INS_LifestyleManager",
                "class_name": "BP_LifestyleManager_C",
            },
            "manager_probe": {
                "success": True,
                "debug_summary": "Day 1 08:00 | Office Worker | Cash $250",
                "task_count": 3,
                "sample_tasks": [
                    {"task_id": "Office_EmailTriage", "display_name": "Email Triage", "base_payout": "45.0"},
                    {"task_id": "Office_DataEntry", "display_name": "Data Entry", "base_payout": "55.0"},
                    {"task_id": "Office_Meeting", "display_name": "Status Meeting", "base_payout": "65.0"},
                ],
                "time": {"current_day": 1, "formatted_time": "08:00", "period": "Morning"},
                "economy": {"cash_balance": 250.0, "daily_living_cost": 45.0, "ledger_count": 0},
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


class TestInsanitiiLifestyleReport(unittest.TestCase):
    def test_report_passes_when_phase2_manager_is_loaded_and_placed(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _Phase2Connection()

        with _PatchServerModule(connection):
            report = mcp.tools["insanitii_phase2_lifestyle_report"](ctx=None, include_dialogs=False)

        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["summary"]["native_class_count"], 3)
        self.assertTrue(report["summary"]["blueprint_has_generated_class"])
        self.assertTrue(report["summary"]["manager_actor_placed"])
        self.assertEqual(report["summary"]["generated_task_count"], 3)
        self.assertEqual(report["summary"]["cash_balance"], 250.0)
        self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
