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


class TestMaterialToolsRegistration(unittest.TestCase):
    def test_phase_4_material_pipeline_tools_register(self):
        from tools.material_tools import register_material_tools

        mcp = _MockMCP()
        register_material_tools(mcp)

        names = set(mcp.list_tool_names())
        self.assertIn("material_create_master", names)
        self.assertIn("material_create_function", names)
        self.assertIn("material_wire_texture_set", names)
        self.assertIn("material_create_instance_from_master", names)
        self.assertIn("material_set_instance_parameters_bulk", names)


if __name__ == "__main__":
    unittest.main()
