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


if __name__ == "__main__":
    unittest.main()
