import unittest
import sys
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

    def get_tool(self, name):
        return self.tools[name]


class TestNiagaraToolsRegistration(unittest.TestCase):
    def test_niagara_tools_register_expected_names(self):
        from tools.niagara_tools import register_niagara_tools

        mcp = _MockMCP()
        register_niagara_tools(mcp)

        self.assertEqual(
            set(mcp.list_tool_names()),
            {
                "niagara_validate_authoring_support",
                "niagara_find_systems",
                "niagara_create_system",
                "niagara_add_empty_emitter",
                "niagara_set_system_user_parameter",
                "niagara_set_spawn_rate",
                "niagara_add_sprite_renderer",
                "niagara_add_mesh_renderer",
                "niagara_describe_system",
                "niagara_apply_system_settings",
                "niagara_set_fixed_bounds",
                "niagara_profile_system",
                "niagara_get_effect_recipe",
            },
        )


class TestNiagaraRecipe(unittest.IsolatedAsyncioTestCase):
    async def test_blackhole_recipe_is_niagara_first(self):
        from tools.niagara_tools import register_niagara_tools

        mcp = _MockMCP()
        register_niagara_tools(mcp)

        result = await mcp.get_tool("niagara_get_effect_recipe")(None)
        recipe = result["outputs"]["recipe"]

        self.assertTrue(result["success"])
        self.assertEqual(recipe["effect_name"], "NS_BlackHoleOrbInflow")
        self.assertIn("emitters", recipe)
        self.assertIn("Niagara system", " ".join(recipe["notes"]))


if __name__ == "__main__":
    unittest.main()
