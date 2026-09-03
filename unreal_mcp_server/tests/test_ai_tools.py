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


class TestAIToolsRegistration(unittest.TestCase):
    def test_phase_2_eqs_tools_register(self):
        from tools.ai_tools import register_ai_tools

        mcp = _MockMCP()
        register_ai_tools(mcp)

        names = set(mcp.list_tool_names())
        self.assertIn("eqs_create_query", names)
        self.assertIn("eqs_describe_query", names)
        self.assertIn("eqs_add_generator", names)
        self.assertIn("eqs_add_test", names)
        self.assertIn("set_behavior_tree_blackboard", names)
        self.assertIn("bt_get_info", names)
        self.assertIn("bt_add_run_eqs_service", names)
        self.assertIn("perception_add_component", names)
        self.assertIn("perception_configure_sight", names)
        self.assertIn("perception_configure_hearing", names)
        self.assertIn("perception_create_stimulus_source", names)
        self.assertIn("perception_bind_updated_event", names)
        self.assertIn("perception_describe_blueprint", names)
        self.assertIn("nav_create_link_proxy", names)
        self.assertIn("nav_add_modifier_volume", names)
        self.assertIn("nav_describe_agent_settings", names)
        self.assertIn("crowd_configure_rvo", names)
        self.assertIn("crowd_configure_detour", names)
        self.assertIn("gameplay_debugger_capture_ai", names)

    def test_behavior_tree_blackboard_wrappers_call_native_routes(self):
        from tools.ai_tools import register_ai_tools

        mcp = _MockMCP()
        register_ai_tools(mcp)

        with patch("tools.ai_tools._send", return_value={"success": True}) as send:
            result = mcp.tools["set_behavior_tree_blackboard"](
                None,
                behavior_tree_name="BT_EnemyAI",
                blackboard_name="BB_EnemyAI",
            )
            self.assertTrue(result["success"])
            send.assert_called_with("set_behavior_tree_blackboard", {
                "behavior_tree_name": "BT_EnemyAI",
                "blackboard_name": "BB_EnemyAI",
            })

        with patch("tools.ai_tools._send", return_value={"success": True, "nodes": []}) as send:
            result = mcp.tools["bt_get_info"](None, behavior_tree_name="BT_EnemyAI")
            self.assertTrue(result["success"])
            send.assert_called_with("bt_get_info", {
                "behavior_tree_name": "BT_EnemyAI",
            })

    def test_bt_task_graph_helpers_call_native_routes(self):
        from tools.ai_tools import register_ai_tools

        mcp = _MockMCP()
        register_ai_tools(mcp)

        with patch("tools.ai_tools._send", return_value={"success": True}) as send:
            result = mcp.tools["add_get_random_reachable_point_node"](
                None,
                blueprint_name="/Game/AI/BTTask_FindWanderPoint",
                radius=750.0,
                node_position=[100.0, 200.0],
            )
            self.assertTrue(result["success"])
            send.assert_called_with("add_get_random_reachable_point_node", {
                "blueprint_name": "/Game/AI/BTTask_FindWanderPoint",
                "radius": 750.0,
                "node_position": [100.0, 200.0],
            })

        with patch("tools.ai_tools._send", return_value={"success": True}) as send:
            result = mcp.tools["add_finish_execute_node"](
                None,
                blueprint_name="/Game/AI/BTTask_FindWanderPoint",
                success=False,
                node_position=[300.0, 400.0],
            )
            self.assertTrue(result["success"])
            send.assert_called_with("add_finish_execute_node", {
                "blueprint_name": "/Game/AI/BTTask_FindWanderPoint",
                "success": False,
                "node_position": [300.0, 400.0],
            })

        with patch("tools.ai_tools._send", return_value={"success": True}) as send:
            result = mcp.tools["add_clear_blackboard_value_node"](
                None,
                blueprint_name="/Game/AI/BTTask_ClearAlert",
                key_name="HasHeardSound",
                node_position=[500.0, 600.0],
            )
            self.assertTrue(result["success"])
            send.assert_called_with("add_clear_blackboard_value_node", {
                "blueprint_name": "/Game/AI/BTTask_ClearAlert",
                "key_name": "HasHeardSound",
                "node_position": [500.0, 600.0],
            })


if __name__ == "__main__":
    unittest.main()
