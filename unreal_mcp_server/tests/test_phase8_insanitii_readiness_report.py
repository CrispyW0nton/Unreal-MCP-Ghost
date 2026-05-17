"""Offline coverage for the Insanitii Phase 1 readiness workflow tool."""

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


class _FallbackConnection:
    def __init__(self):
        self.calls = []

    def send_command(self, command, params):
        self.calls.append((command, params))
        if command == "ping":
            return {"status": "success"}
        if command != "exec_python":
            return {"status": "error", "error": f"Unknown command: {command}"}

        code = params["code"]
        if "needle = \"ins_\"" in code.lower():
            actors = [
                {"label": "INS_RuntimeBootstrap", "name": "INS_RuntimeBootstrap", "class_name": "BP_RuntimeBootstrap_C"},
                {"label": "INS_PostProcessController", "name": "INS_PostProcessController", "class_name": "BP_PostProcessController_C"},
                {"label": "INS_TestCube_PleasantMemory", "name": "INS_TestCube_PleasantMemory", "class_name": "BP_TestInteractable_C"},
                {"label": "INS_TestCube_BriefComfort", "name": "INS_TestCube_BriefComfort", "class_name": "BP_TestInteractable_C"},
                {"label": "INS_TestCube_NeutralMoment", "name": "INS_TestCube_NeutralMoment", "class_name": "BP_TestInteractable_C"},
                {"label": "INS_TestCube_MinorSetback", "name": "INS_TestCube_MinorSetback", "class_name": "BP_TestInteractable_C"},
                {"label": "INS_TestCube_BadMemory", "name": "INS_TestCube_BadMemory", "class_name": "BP_TestInteractable_C"},
            ]
            return {"success": True, "result": {"output": json.dumps({"success": True, "count": 7, "actors": actors})}}
        if "generated_class" in code:
            return {
                "success": True,
                "result": {
                    "output": json.dumps(
                        {
                            "success": True,
                            "asset_path": "/Game/Insanitii/Core/Blueprints/BP_RuntimeBootstrap",
                            "has_generated_class": True,
                            "generated_class": "/Game/Insanitii/Core/Blueprints/BP_RuntimeBootstrap.BP_RuntimeBootstrap_C",
                        }
                    )
                },
            }
        if "BP_TestInteractable" in code or "InsanitiiTestInteractable" in code:
            actors = [{"label": f"INS_TestCube_{idx}", "class_name": "BP_TestInteractable_C"} for idx in range(5)]
            return {"success": True, "result": {"output": json.dumps({"success": True, "count": 5, "actors": actors})}}
        if "mapping_count" in code:
            actions = [
                "IA_Focus",
                "IA_Breathe",
                "IA_Interact",
                "IA_DebugDecreaseState",
                "IA_DebugIncreaseState",
                "IA_ToggleHUD",
            ]
            return {
                "success": True,
                "result": {
                    "output": json.dumps(
                        {
                            "success": True,
                            "asset_path": "/Game/FirstPerson/Input/IMC_Default",
                            "mapping_count": len(actions),
                            "mappings": [{"action_name": action, "key": "Key"} for action in actions],
                        }
                    )
                },
            }
        return {"success": False, "result": {"output": "{}"}}


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


class TestInsanitiiReadinessReport(unittest.TestCase):
    def test_report_uses_exec_python_fallback_when_native_routes_are_not_loaded(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _FallbackConnection()

        with _PatchServerModule(connection):
            report = mcp.tools["insanitii_phase1_readiness_report"](ctx=None, include_dialogs=False)

        self.assertTrue(report["success"])
        self.assertEqual(report["status"], "warn")
        self.assertEqual(report["summary"]["found_insanitii_actor_count"], 7)
        self.assertEqual(report["summary"]["bp_test_interactable_count"], 5)
        self.assertEqual(report["summary"]["native_test_interactable_count"], 5)
        self.assertEqual(report["summary"]["input_mapping_count"], 6)
        self.assertEqual(report["failures"], [])
        self.assertGreater(report["summary"]["native_fallback_count"], 0)
        self.assertTrue(any("exec_python fallback" in warning for warning in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
