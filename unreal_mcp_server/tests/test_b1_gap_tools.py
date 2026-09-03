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

    def test_set_blueprint_parent_class_wraps_native_reparent_route(self):
        from tools.blueprint_tools import register_blueprint_tools

        mcp = _MockMCP()
        register_blueprint_tools(mcp)
        self.assertIn("set_blueprint_parent_class", mcp.tools)

        connection = _MockUnrealConnection()
        with _PatchServerModule(connection):
            payload = mcp.tools["set_blueprint_parent_class"](
                ctx=None,
                blueprint_name="/Game/BP_Enemy",
                new_parent_class="Character",
            )

        self.assertTrue(payload["success"])
        self.assertEqual(connection.calls[0][0], "set_blueprint_parent_class")
        self.assertEqual(connection.calls[0][1]["blueprint_name"], "/Game/BP_Enemy")
        self.assertEqual(connection.calls[0][1]["new_parent_class"], "Character")

    def test_construction_script_node_uses_native_route(self):
        from tools.advanced_node_tools import register_advanced_node_tools

        mcp = _MockMCP()
        register_advanced_node_tools(mcp)
        self.assertIn("add_construction_script_node", mcp.tools)

        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "node_id": "NODE-1"}

        with patch("tools.advanced_node_tools._send", side_effect=fake_send):
            payload = mcp.tools["add_construction_script_node"](
                ctx=None,
                blueprint_name="/Game/BP_GeneratedActor",
                node_position=[120.0, 240.0],
            )

        self.assertTrue(payload["success"])
        self.assertEqual(calls[0][0], "add_construction_script_node")
        self.assertEqual(calls[0][1]["blueprint_name"], "/Game/BP_GeneratedActor")
        self.assertEqual(calls[0][1]["node_position"], [120.0, 240.0])

    def test_math_operator_nodes_use_native_routes(self):
        from tools.advanced_node_tools import register_advanced_node_tools

        mcp = _MockMCP()
        register_advanced_node_tools(mcp)
        self.assertIn("add_arithmetic_operator_node", mcp.tools)
        self.assertIn("add_relational_operator_node", mcp.tools)

        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "node_id": "NODE-1"}

        with patch("tools.advanced_node_tools._send", side_effect=fake_send):
            arithmetic_payload = mcp.tools["add_arithmetic_operator_node"](
                ctx=None,
                blueprint_name="/Game/BP_CombatMath",
                operator="Multiply",
                operand_type="Float",
                node_position=[10.0, 20.0],
            )
            relational_payload = mcp.tools["add_relational_operator_node"](
                ctx=None,
                blueprint_name="/Game/BP_CombatMath",
                operator="GreaterEqual",
                operand_type="Integer",
                node_position=[30.0, 40.0],
            )

        self.assertTrue(arithmetic_payload["success"])
        self.assertTrue(relational_payload["success"])
        self.assertEqual(calls[0][0], "add_arithmetic_operator_node")
        self.assertEqual(calls[0][1]["operator"], "Multiply")
        self.assertEqual(calls[0][1]["operand_type"], "Float")
        self.assertEqual(calls[1][0], "add_relational_operator_node")
        self.assertEqual(calls[1][1]["operator"], "GreaterEqual")
        self.assertEqual(calls[1][1]["operand_type"], "Integer")

    def test_function_with_pins_and_spawn_actor_class_use_native_routes(self):
        from tools.node_tools import register_blueprint_node_tools

        mcp = _MockMCP()
        register_blueprint_node_tools(mcp)
        self.assertIn("add_blueprint_function_with_pins", mcp.tools)
        self.assertIn("set_spawn_actor_class", mcp.tools)

        connection = _MockUnrealConnection()
        with _PatchServerModule(connection):
            function_payload = mcp.tools["add_blueprint_function_with_pins"](
                ctx=None,
                blueprint_name="/Game/BP_Damageable",
                function_name="ComputeDamage",
                inputs=[{"name": "BaseDamage", "type": "float"}],
                outputs=[{"name": "FinalDamage", "type": "float"}],
                is_pure=True,
            )
            spawn_payload = mcp.tools["set_spawn_actor_class"](
                ctx=None,
                blueprint_name="/Game/BP_Spawner",
                graph_name="EventGraph",
                node_id="SPAWN-NODE",
                actor_class="BP_Enemy_C",
            )

        self.assertTrue(function_payload["success"])
        self.assertTrue(spawn_payload["success"])
        self.assertEqual(connection.calls[0][0], "add_blueprint_function_with_pins")
        self.assertEqual(connection.calls[0][1]["function_name"], "ComputeDamage")
        self.assertEqual(connection.calls[0][1]["inputs"][0]["name"], "BaseDamage")
        self.assertEqual(connection.calls[0][1]["outputs"][0]["name"], "FinalDamage")
        self.assertTrue(connection.calls[0][1]["is_pure"])
        self.assertEqual(connection.calls[1][0], "set_spawn_actor_class")
        self.assertEqual(connection.calls[1][1]["node_id"], "SPAWN-NODE")
        self.assertEqual(connection.calls[1][1]["actor_class"], "BP_Enemy_C")

    def test_data_and_flow_helpers_use_native_routes(self):
        from tools.advanced_node_tools import register_advanced_node_tools
        from tools.data_tools import register_data_tools

        data_mcp = _MockMCP()
        register_data_tools(data_mcp)
        self.assertIn("add_map_variable", data_mcp.tools)

        data_calls = []

        def fake_data_send(command, params):
            data_calls.append((command, params))
            return {"success": True, "command": command}

        with patch("tools.data_tools._send", side_effect=fake_data_send):
            payload = data_mcp.tools["add_map_variable"](
                ctx=None,
                blueprint_name="/Game/BP_SaveState",
                variable_name="QuestFlags",
                key_type="Name",
                value_type="Bool",
                is_exposed=True,
            )

        self.assertTrue(payload["success"])
        self.assertEqual(data_calls[0][0], "add_map_variable")
        self.assertEqual(data_calls[0][1]["key_type"], "Name")
        self.assertEqual(data_calls[0][1]["value_type"], "Bool")
        self.assertTrue(data_calls[0][1]["is_exposed"])

        advanced_mcp = _MockMCP()
        register_advanced_node_tools(advanced_mcp)
        self.assertIn("add_open_level_node", advanced_mcp.tools)

        advanced_calls = []

        def fake_advanced_send(command, params):
            advanced_calls.append((command, params))
            return {"success": True, "command": command}

        with patch("tools.advanced_node_tools._send", side_effect=fake_advanced_send):
            payload = advanced_mcp.tools["add_open_level_node"](
                ctx=None,
                blueprint_name="/Game/UI/WBP_MainMenu",
                level_name="L_Arena",
                node_position=[64.0, 128.0],
            )

        self.assertTrue(payload["success"])
        self.assertEqual(advanced_calls[0][0], "add_open_level_node")
        self.assertEqual(advanced_calls[0][1]["level_name"], "L_Arena")
        self.assertEqual(advanced_calls[0][1]["node_position"], [64.0, 128.0])

    def test_reconstruct_blueprint_node_uses_native_repair_route(self):
        from tools.node_tools import register_blueprint_node_tools

        mcp = _MockMCP()
        register_blueprint_node_tools(mcp)
        self.assertIn("reconstruct_blueprint_node", mcp.tools)

        connection = _MockUnrealConnection()
        with _PatchServerModule(connection):
            payload = mcp.tools["reconstruct_blueprint_node"](
                ctx=None,
                blueprint_name="/Game/BP_RepairMe",
                graph_name="EventGraph",
                node_id="NODE-TO-RECONSTRUCT",
            )

        self.assertTrue(payload["success"])
        self.assertEqual(connection.calls[0][0], "reconstruct_blueprint_node")
        self.assertEqual(connection.calls[0][1]["blueprint_name"], "/Game/BP_RepairMe")
        self.assertEqual(connection.calls[0][1]["node_id"], "NODE-TO-RECONSTRUCT")

    def test_custom_and_interface_event_wrappers_use_native_routes(self):
        from tools.advanced_node_tools import register_advanced_node_tools

        mcp = _MockMCP()
        register_advanced_node_tools(mcp)
        self.assertIn("add_custom_event", mcp.tools)
        self.assertIn("call_custom_event", mcp.tools)
        self.assertIn("add_interface_event_node", mcp.tools)

        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "command": command, **params}

        with patch("tools.advanced_node_tools._send", side_effect=fake_send):
            add_payload = mcp.tools["add_custom_event"](
                ctx=None,
                blueprint_name="/Game/BP_Door",
                event_name="OpenDoor",
                node_position=[100.0, 200.0],
            )
            call_payload = mcp.tools["call_custom_event"](
                ctx=None,
                blueprint_name="/Game/BP_Button",
                target_blueprint="/Game/BP_Door",
                event_name="OpenDoor",
            )
            interface_payload = mcp.tools["add_interface_event_node"](
                ctx=None,
                blueprint_name="/Game/BP_Door",
                interface_name="/Game/BPI_Interactable",
                function_name="Interact",
                node_position=[-200.0, 50.0],
            )

        self.assertTrue(add_payload["success"])
        self.assertTrue(call_payload["success"])
        self.assertTrue(interface_payload["success"])
        self.assertEqual(calls[0][0], "add_custom_event")
        self.assertEqual(calls[0][1]["event_name"], "OpenDoor")
        self.assertEqual(calls[0][1]["node_position"], [100.0, 200.0])
        self.assertEqual(calls[1][0], "call_custom_event")
        self.assertEqual(calls[1][1]["target_blueprint"], "/Game/BP_Door")
        self.assertEqual(calls[1][1]["node_position"], [0, 0])
        self.assertEqual(calls[2][0], "add_interface_event_node")
        self.assertEqual(calls[2][1]["interface_name"], "/Game/BPI_Interactable")
        self.assertEqual(calls[2][1]["function_name"], "Interact")

    def test_comment_rename_and_pawn_property_wrappers_use_native_routes(self):
        from tools.blueprint_tools import register_blueprint_tools
        from tools.node_tools import register_blueprint_node_tools

        node_mcp = _MockMCP()
        register_blueprint_node_tools(node_mcp)
        self.assertIn("rename_blueprint_comment_node", node_mcp.tools)

        node_connection = _MockUnrealConnection()
        with _PatchServerModule(node_connection):
            comment_payload = node_mcp.tools["rename_blueprint_comment_node"](
                ctx=None,
                blueprint_name="/Game/BP_Door",
                graph_name="EventGraph",
                node_id="COMMENT-1",
                comment_text="Interact Flow",
                color=[0.2, 0.6, 1.0, 0.65],
            )

        self.assertTrue(comment_payload["success"])
        self.assertEqual(node_connection.calls[0][0], "rename_blueprint_comment_node")
        self.assertEqual(node_connection.calls[0][1]["node_id"], "COMMENT-1")
        self.assertEqual(node_connection.calls[0][1]["comment_text"], "Interact Flow")
        self.assertEqual(node_connection.calls[0][1]["color"], [0.2, 0.6, 1.0, 0.65])

        blueprint_mcp = _MockMCP()
        register_blueprint_tools(blueprint_mcp)
        self.assertIn("set_pawn_properties", blueprint_mcp.tools)

        blueprint_connection = _MockUnrealConnection()
        with _PatchServerModule(blueprint_connection):
            pawn_payload = blueprint_mcp.tools["set_pawn_properties"](
                ctx=None,
                blueprint_name="/Game/BP_Enemy",
                auto_possess_ai="PlacedInWorldOrSpawned",
                use_controller_rotation_yaw=False,
                can_be_damaged=True,
            )

        self.assertTrue(pawn_payload["success"])
        self.assertEqual(blueprint_connection.calls[0][0], "set_pawn_properties")
        self.assertEqual(blueprint_connection.calls[0][1]["blueprint_name"], "/Game/BP_Enemy")
        self.assertEqual(blueprint_connection.calls[0][1]["auto_possess_ai"], "PlacedInWorldOrSpawned")
        self.assertFalse(blueprint_connection.calls[0][1]["use_controller_rotation_yaw"])
        self.assertTrue(blueprint_connection.calls[0][1]["can_be_damaged"])
        self.assertNotIn("auto_possess_player", blueprint_connection.calls[0][1])

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

    def test_bind_widget_component_event_wraps_native_component_bound_route(self):
        from tools.umg_tools import register_umg_tools

        mcp = _MockMCP()
        register_umg_tools(mcp)
        self.assertIn("bind_widget_component_event", mcp.tools)

        connection = _MockUnrealConnection()
        with _PatchServerModule(connection):
            payload = mcp.tools["bind_widget_component_event"](
                ctx=None,
                widget_blueprint_path="/Game/UI/WBP_MainMenu",
                widget_name="BTN_Start",
                event_name="OnClicked",
                compile=False,
            )

        _assert_structured_dict(self, payload, "bind_widget_component_event")
        self.assertTrue(payload["success"])
        self.assertEqual(connection.calls[0][0], "bind_widget_component_event")
        self.assertEqual(connection.calls[0][1]["widget_blueprint_path"], "/Game/UI/WBP_MainMenu")
        self.assertEqual(connection.calls[0][1]["widget_name"], "BTN_Start")
        self.assertEqual(connection.calls[0][1]["event_name"], "OnClicked")
        self.assertFalse(connection.calls[0][1]["compile"])


if __name__ == "__main__":
    unittest.main()
