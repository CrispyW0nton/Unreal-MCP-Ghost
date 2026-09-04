"""Offline coverage for Phase 7 Slice 6 Insanitii smoke-test wrappers."""

from __future__ import annotations

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


class _MockUnrealConnection:
    def __init__(self):
        self.calls = []

    def send_command(self, command, params):
        self.calls.append((command, params))
        if command == "get_actor_identity":
            return {"success": True, "count": 1, "actors": []}
        if command == "find_actors_by_class":
            return {"success": True, "count": 1, "actors": []}
        if command == "inspect_input_mapping_context":
            return {"success": True, "mapping_count": 1, "mappings": []}
        if command == "check_blueprint_generated_class":
            return {"success": True, "has_generated_class": True}
        return {"success": True, "command": command, "params": params}


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


class TestPhase7InsanitiiSmokeWrappers(unittest.TestCase):
    def test_actor_smoke_wrappers_route_through_exec_python(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)
        connection = _MockUnrealConnection()

        with _PatchServerModule(connection):
            identity = mcp.tools["get_actor_identity"](ctx=None, actor_name_or_label="INS_", include_all=False)
            by_class = mcp.tools["find_actors_by_class"](ctx=None, class_name="InsanitiiTestInteractable")

        self.assertTrue(identity["success"])
        self.assertTrue(by_class["success"])
        self.assertEqual([command for command, _params in connection.calls], ["get_actor_identity", "find_actors_by_class"])
        self.assertEqual(connection.calls[0][1]["actor_name_or_label"], "INS_")
        self.assertEqual(connection.calls[1][1]["class_name"], "InsanitiiTestInteractable")

    def test_project_smoke_wrappers_route_through_exec_python(self):
        from tools.project_tools import register_project_tools

        mcp = _MockMCP()
        register_project_tools(mcp)
        connection = _MockUnrealConnection()

        with _PatchServerModule(connection):
            imc = mcp.tools["inspect_input_mapping_context"](ctx=None, imc_path_or_name="/Game/FirstPerson/Input/IMC_Default")
            bp = mcp.tools["check_blueprint_generated_class"](ctx=None, blueprint_path_or_name="BP_RuntimeBootstrap")

        self.assertTrue(imc["success"])
        self.assertTrue(bp["success"])
        self.assertEqual(
            [command for command, _params in connection.calls],
            ["inspect_input_mapping_context", "check_blueprint_generated_class"],
        )
        self.assertEqual(connection.calls[0][1]["imc_path_or_name"], "/Game/FirstPerson/Input/IMC_Default")
        self.assertEqual(connection.calls[1][1]["blueprint_path_or_name"], "BP_RuntimeBootstrap")

    def test_dialog_listing_is_safe_on_non_windows_or_returns_shape(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)

        result = mcp.tools["editor_list_blocking_dialogs"](ctx=None)

        self.assertIn("success", result)
        self.assertIn("windows", result)

    def test_dialog_dismissal_requires_explicit_button_text(self):
        from tools.editor_tools import register_editor_tools

        mcp = _MockMCP()
        register_editor_tools(mcp)

        result = mcp.tools["editor_dismiss_blocking_dialog"](ctx=None, button_text="")

        self.assertFalse(result["success"])
        self.assertIn("button_text", result["message"])


if __name__ == "__main__":
    unittest.main()
