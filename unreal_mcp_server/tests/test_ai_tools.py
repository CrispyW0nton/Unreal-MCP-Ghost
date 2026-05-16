import sys
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
