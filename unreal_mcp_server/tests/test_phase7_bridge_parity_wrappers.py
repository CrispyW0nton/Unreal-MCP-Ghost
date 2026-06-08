"""Offline coverage for native bridge parity wrappers."""

from __future__ import annotations

import sys
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
        def _decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return _decorator


class _FakeUnreal:
    def __init__(self):
        self.calls = []

    def send_command(self, command, params):
        self.calls.append((command, params))
        return {"success": True, "command": command, "params": params}


class TestBridgeParityWrappers(unittest.TestCase):
    def test_advanced_node_tools_use_native_routes_without_regressing_fallbacks(self):
        from tools.advanced_node_tools import register_advanced_node_tools

        mcp = _MockMCP()
        register_advanced_node_tools(mcp)

        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "command": command, "params": params}

        with patch("tools.advanced_node_tools._send", side_effect=fake_send):
            mcp.tools["add_open_level_node"](None, "/Game/MCP_Test/BP_Example")
            mcp.tools["add_open_level_node"](None, "/Game/MCP_Test/BP_Example", "Dungeon01")
            mcp.tools["add_arithmetic_operator_node"](None, "/Game/MCP_Test/BP_Example", "Add", "Float")
            mcp.tools["add_arithmetic_operator_node"](None, "/Game/MCP_Test/BP_Example", "Power", "Float")
            mcp.tools["add_relational_operator_node"](None, "/Game/MCP_Test/BP_Example", "Equal", "Integer")
            mcp.tools["add_relational_operator_node"](None, "/Game/MCP_Test/BP_Example", "Equal", "String")
            mcp.tools["add_construction_script_node"](None, "/Game/MCP_Test/BP_Example")

        self.assertEqual(calls[0][0], "add_open_level_node")
        self.assertEqual(calls[1][0], "add_blueprint_function_node")
        self.assertEqual(calls[2][0], "add_arithmetic_operator_node")
        self.assertEqual(calls[3][0], "add_blueprint_function_node")
        self.assertEqual(calls[4][0], "add_relational_operator_node")
        self.assertEqual(calls[5][0], "add_blueprint_function_node")
        self.assertEqual(calls[6][0], "add_construction_script_node")

    def test_blueprint_native_wrappers_register_and_dispatch(self):
        from tools.blueprint_tools import register_blueprint_tools

        mcp = _MockMCP()
        register_blueprint_tools(mcp)
        fake_unreal = _FakeUnreal()

        with patch("unreal_mcp_server.get_unreal_connection", return_value=fake_unreal):
            niagara = mcp.tools["add_niagara_component"](
                None,
                "/Game/MCP_Test/BP_Example",
                "FX_Glow",
                "/Game/VFX/NS_Glow.NS_Glow",
            )
            parent = mcp.tools["set_blueprint_parent_class"](
                None,
                "/Game/MCP_Test/BP_Enemy",
                "Character",
            )

        self.assertTrue(niagara["success"])
        self.assertTrue(parent["success"])
        self.assertEqual(fake_unreal.calls[0][0], "add_niagara_component")
        self.assertEqual(fake_unreal.calls[0][1]["component_name"], "FX_Glow")
        self.assertEqual(fake_unreal.calls[1][0], "set_blueprint_parent_class")
        self.assertEqual(fake_unreal.calls[1][1]["new_parent_class"], "Character")

    def test_node_native_wrappers_register_and_dispatch(self):
        from tools.node_tools import register_blueprint_node_tools

        mcp = _MockMCP()
        register_blueprint_node_tools(mcp)
        fake_unreal = _FakeUnreal()

        with patch("unreal_mcp_server.get_unreal_connection", return_value=fake_unreal):
            reconstruct = mcp.tools["reconstruct_blueprint_node"](
                None,
                "/Game/MCP_Test/BP_Example",
                "K2Node_CallFunction_0",
            )
            spawn_class = mcp.tools["set_spawn_actor_class"](
                None,
                "/Game/MCP_Test/BP_Example",
                "K2Node_SpawnActorFromClass_0",
                "BP_Enemy_C",
            )
            rename_comment = mcp.tools["rename_blueprint_comment_node"](
                None,
                "/Game/MCP_Test/BP_Example",
                "EdGraphNode_Comment_0",
                "Generated Combat Loop",
            )
            custom_event = mcp.tools["add_blueprint_custom_event_node"](
                None,
                "/Game/MCP_Test/BP_Enemy",
                "ApplyGeneratedDamage",
                inputs=[{"name": "Damage", "type": "Float"}],
            )
            function = mcp.tools["add_blueprint_function_with_pins"](
                None,
                "/Game/MCP_Test/BP_Enemy",
                "CanSeePlayer",
                outputs=[{"name": "CanSee", "type": "Boolean"}],
                is_pure=True,
            )

        self.assertTrue(reconstruct["success"])
        self.assertTrue(spawn_class["success"])
        self.assertTrue(rename_comment["success"])
        self.assertTrue(custom_event["success"])
        self.assertTrue(function["success"])
        self.assertEqual(fake_unreal.calls[0][0], "reconstruct_blueprint_node")
        self.assertEqual(fake_unreal.calls[1][0], "set_spawn_actor_class")
        self.assertEqual(fake_unreal.calls[1][1]["actor_class"], "BP_Enemy_C")
        self.assertEqual(fake_unreal.calls[2][0], "rename_blueprint_comment_node")
        self.assertEqual(fake_unreal.calls[2][1]["comment_text"], "Generated Combat Loop")
        self.assertEqual(fake_unreal.calls[3][0], "add_blueprint_custom_event_node")
        self.assertEqual(fake_unreal.calls[3][1]["event_name"], "ApplyGeneratedDamage")
        self.assertEqual(fake_unreal.calls[3][1]["inputs"], [{"name": "Damage", "type": "Float"}])
        self.assertEqual(fake_unreal.calls[4][0], "add_blueprint_function_with_pins")
        self.assertEqual(fake_unreal.calls[4][1]["function_name"], "CanSeePlayer")
        self.assertEqual(fake_unreal.calls[4][1]["outputs"], [{"name": "CanSee", "type": "Boolean"}])
        self.assertTrue(fake_unreal.calls[4][1]["is_pure"])

    def test_communication_native_wrappers_register_and_dispatch(self):
        from tools.communication_tools import register_communication_tools

        mcp = _MockMCP()
        register_communication_tools(mcp)

        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "command": command, "params": params}

        with patch("tools.communication_tools._send", side_effect=fake_send):
            interface_event = mcp.tools["add_interface_event_node"](
                None,
                "/Game/MCP_Test/BP_Door",
                "/Game/MCP_Test/BPI_Interactable",
                "Interact",
                [120, 240],
            )
            custom_event = mcp.tools["add_custom_event"](
                None,
                "/Game/MCP_Test/BP_Encounter",
                "StartEncounter",
            )
            custom_call = mcp.tools["call_custom_event"](
                None,
                "/Game/MCP_Test/BP_Button",
                "/Game/MCP_Test/BP_Door",
                "OpenDoor",
                [360, 120],
            )

        self.assertTrue(interface_event["success"])
        self.assertTrue(custom_event["success"])
        self.assertTrue(custom_call["success"])
        self.assertEqual(calls[0][0], "add_interface_event_node")
        self.assertEqual(calls[0][1]["interface_name"], "/Game/MCP_Test/BPI_Interactable")
        self.assertEqual(calls[0][1]["function_name"], "Interact")
        self.assertEqual(calls[0][1]["node_position"], [120, 240])
        self.assertEqual(calls[1][0], "add_custom_event")
        self.assertEqual(calls[1][1]["event_name"], "StartEncounter")
        self.assertEqual(calls[1][1]["node_position"], [0, 0])
        self.assertEqual(calls[2][0], "call_custom_event")
        self.assertEqual(calls[2][1]["target_blueprint"], "/Game/MCP_Test/BP_Door")
        self.assertEqual(calls[2][1]["event_name"], "OpenDoor")

    def test_animation_native_wrappers_register_and_dispatch(self):
        from tools.animation_tools import register_animation_tools

        mcp = _MockMCP()
        register_animation_tools(mcp)

        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "command": command, "params": params}

        with patch("tools.animation_tools._send", side_effect=fake_send):
            sequence = mcp.tools["add_sequence_player_node"](
                None,
                "/Game/MCP_Test/ABP_Enemy",
                "/Game/MCP_Test/A_Idle.A_Idle",
                graph_name="AnimGraph",
                wire_to_root=True,
                loop=False,
                node_position=[100, 200],
            )
            connection = mcp.tools["connect_anim_graph_nodes"](
                None,
                "/Game/MCP_Test/ABP_Enemy",
                "source-guid",
                "target-guid",
            )

        self.assertTrue(sequence["success"])
        self.assertTrue(connection["success"])
        self.assertEqual(calls[0][0], "add_sequence_player_node")
        self.assertEqual(calls[0][1]["anim_blueprint_name"], "/Game/MCP_Test/ABP_Enemy")
        self.assertEqual(calls[0][1]["sequence_asset"], "/Game/MCP_Test/A_Idle.A_Idle")
        self.assertEqual(calls[0][1]["graph_name"], "AnimGraph")
        self.assertTrue(calls[0][1]["wire_to_root"])
        self.assertFalse(calls[0][1]["loop"])
        self.assertEqual(calls[1][0], "connect_anim_graph_nodes")
        self.assertEqual(calls[1][1]["source_node_id"], "source-guid")
        self.assertEqual(calls[1][1]["target_node_id"], "target-guid")


if __name__ == "__main__":
    unittest.main()
