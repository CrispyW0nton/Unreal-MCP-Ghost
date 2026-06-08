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

    def test_native_bridge_parity_ai_wrappers_register_and_dispatch(self):
        from tools.ai_tools import register_ai_tools

        mcp = _MockMCP()
        register_ai_tools(mcp)

        names = set(mcp.list_tool_names())
        self.assertIn("set_behavior_tree_blackboard", names)
        self.assertIn("bt_get_info", names)

        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "command": command, "params": params}

        with patch("tools.ai_tools._send", side_effect=fake_send):
            assign = mcp.tools["set_behavior_tree_blackboard"](None, "BT_Enemy", "BB_Enemy")
            info = mcp.tools["bt_get_info"](None, "BT_Enemy")

        self.assertTrue(assign["success"])
        self.assertTrue(info["success"])
        self.assertEqual(calls[0][0], "set_behavior_tree_blackboard")
        self.assertEqual(calls[0][1]["behavior_tree_name"], "BT_Enemy")
        self.assertEqual(calls[0][1]["blackboard_name"], "BB_Enemy")
        self.assertEqual(calls[1][0], "bt_get_info")
        self.assertEqual(calls[1][1]["behavior_tree_name"], "BT_Enemy")


if __name__ == "__main__":
    unittest.main()
