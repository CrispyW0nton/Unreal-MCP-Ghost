"""Offline smoke coverage for Workstream B.1 gap-closing tools."""

from __future__ import annotations

import asyncio
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


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
        return {"success": True, "command": command, **params}


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


def _assert_structured_dict(testcase: unittest.TestCase, payload: dict, stage: str):
    for key in ("success", "stage", "message", "outputs", "warnings", "errors", "log_tail"):
        testcase.assertIn(key, payload)
    testcase.assertEqual(payload["stage"], stage)


class TestB1GapTools(unittest.TestCase):
    def test_graph_b1_tools_register_and_call_expected_native_routes(self):
        from tools.graph_tools import register_graph_tools

        mcp = _MockMCP()
        register_graph_tools(mcp)

        self.assertIn("bp_add_call_interface_function", mcp.tools)
        self.assertIn("bp_add_for_loop_with_break_node", mcp.tools)

        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "node_id": "NODE-1", "pins": []}

        async def run():
            with patch("tools.graph_tools._send", side_effect=fake_send):
                interface_payload = json.loads(await mcp.tools["bp_add_call_interface_function"](
                    ctx=None,
                    blueprint_name="/Game/BP_Player",
                    interface_name="/Game/BPI_Interactable",
                    function_name="Interact",
                ))
                loop_payload = json.loads(await mcp.tools["bp_add_for_loop_with_break_node"](
                    ctx=None,
                    blueprint_name="/Game/BP_Player",
                    graph_name="EventGraph",
                    first_index=0,
                    last_index=3,
                ))
            return interface_payload, loop_payload

        interface_payload, loop_payload = asyncio.run(run())

        _assert_structured_dict(self, interface_payload, "bp_add_call_interface_function")
        _assert_structured_dict(self, loop_payload, "bp_add_for_loop_with_break_node")
        self.assertEqual(calls[0][0], "add_call_interface_function_node")
        self.assertEqual(calls[0][1]["function_name"], "Interact")
        self.assertEqual(calls[1][0], "add_blueprint_for_loop_with_break_node")
        self.assertEqual(calls[1][1]["last_index"], 3)

    def test_bp_copy_component_wraps_native_copy_route(self):
        from tools.blueprint_tools import register_blueprint_tools

        mcp = _MockMCP()
        register_blueprint_tools(mcp)
        self.assertIn("bp_copy_component", mcp.tools)

        connection = _MockUnrealConnection()
        with _PatchServerModule(connection):
            payload = mcp.tools["bp_copy_component"](
                ctx=None,
                source_bp="/Game/BP_Source",
                dest_bp="/Game/BP_Dest",
                component_name="CameraBoom",
            )

        _assert_structured_dict(self, payload, "bp_copy_component")
        self.assertTrue(payload["success"])
        self.assertEqual(connection.calls[0][0], "bp_copy_component")
        self.assertEqual(connection.calls[0][1]["source_bp"], "/Game/BP_Source")
        self.assertEqual(connection.calls[0][1]["new_component_name"], "CameraBoom")

    def test_umg_add_widget_binding_wraps_native_binding_route(self):
        from tools.umg_tools import register_umg_tools

        mcp = _MockMCP()
        register_umg_tools(mcp)
        self.assertIn("umg_add_widget_binding", mcp.tools)

        connection = _MockUnrealConnection()
        with _PatchServerModule(connection):
            payload = mcp.tools["umg_add_widget_binding"](
                ctx=None,
                widget="/Game/UI/WBP_HUD",
                property_path="HealthText.Text",
                binding_target="GetHealthText",
            )

        _assert_structured_dict(self, payload, "umg_add_widget_binding")
        self.assertTrue(payload["success"])
        self.assertEqual(connection.calls[0][0], "umg_add_widget_binding")
        self.assertEqual(connection.calls[0][1]["widget_blueprint_path"], "/Game/UI/WBP_HUD")
        self.assertEqual(connection.calls[0][1]["property_path"], "HealthText.Text")
        self.assertEqual(connection.calls[0][1]["binding_target"], "GetHealthText")


if __name__ == "__main__":
    unittest.main()
