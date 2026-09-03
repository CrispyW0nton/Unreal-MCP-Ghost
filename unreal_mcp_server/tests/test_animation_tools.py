import sys
import unittest
from pathlib import Path
from unittest.mock import patch


_SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))


class _MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def _decorator(fn):
            self.tools[fn.__name__] = fn
            return fn

        return _decorator

    def list_tool_names(self):
        return list(self.tools)


class TestAnimationToolsRegistration(unittest.TestCase):
    def test_phase_5_montage_and_notify_tools_register(self):
        from tools.animation_tools import register_animation_tools

        mcp = _MockMCP()
        register_animation_tools(mcp)

        names = set(mcp.list_tool_names())
        self.assertIn("add_anim_notify", names)
        self.assertIn("anim_create_montage", names)
        self.assertIn("anim_describe_montage", names)
        self.assertIn("anim_add_montage_slot", names)
        self.assertIn("anim_set_montage_section", names)
        self.assertIn("anim_add_branching_point", names)
        self.assertIn("control_rig_create", names)
        self.assertIn("control_rig_describe", names)
        self.assertIn("control_rig_add_control", names)
        self.assertIn("control_rig_add_constraint", names)
        self.assertIn("control_rig_bake_to_sequence", names)
        self.assertIn("add_sequence_player_node", names)
        self.assertIn("connect_anim_graph_nodes", names)

    def test_anim_graph_gap_tools_call_native_routes(self):
        from tools.animation_tools import register_animation_tools

        mcp = _MockMCP()
        register_animation_tools(mcp)
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "node_id": "NODE-1", **params}

        with patch("tools.animation_tools._send", side_effect=fake_send):
            sequence_payload = mcp.tools["add_sequence_player_node"](
                ctx=None,
                anim_blueprint_name="/Game/ABP_Enemy",
                sequence_asset="/Game/Anims/A_Idle",
                graph_name="AnimGraph",
                node_position=[100.0, 200.0],
                wire_to_root=True,
                loop=False,
            )
            connect_payload = mcp.tools["connect_anim_graph_nodes"](
                ctx=None,
                anim_blueprint_name="/Game/ABP_Enemy",
                source_node_id="SRC-GUID",
                target_node_id="DST-GUID",
                graph_name="AnimGraph",
            )

        self.assertTrue(sequence_payload["success"])
        self.assertTrue(connect_payload["success"])
        self.assertEqual(calls[0][0], "add_sequence_player_node")
        self.assertEqual(calls[0][1]["sequence_asset"], "/Game/Anims/A_Idle")
        self.assertEqual(calls[0][1]["wire_to_root"], True)
        self.assertEqual(calls[0][1]["loop"], False)
        self.assertEqual(calls[1][0], "connect_anim_graph_nodes")
        self.assertEqual(calls[1][1]["source_node_id"], "SRC-GUID")
        self.assertEqual(calls[1][1]["target_node_id"], "DST-GUID")


if __name__ == "__main__":
    unittest.main()
