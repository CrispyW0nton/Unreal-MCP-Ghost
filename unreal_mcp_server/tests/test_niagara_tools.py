import unittest
import sys
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
                "add_niagara_component",
                "niagara_describe_system",
                "niagara_apply_system_settings",
                "niagara_set_fixed_bounds",
                "niagara_profile_system",
                "niagara_get_effect_recipe",
            },
        )


class TestNiagaraRecipe(unittest.IsolatedAsyncioTestCase):
    async def test_add_niagara_component_calls_native_route(self):
        from tools.niagara_tools import register_niagara_tools

        mcp = _MockMCP()
        register_niagara_tools(mcp)
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "blueprint": params["blueprint_name"],
                "component_name": params["component_name"],
                "niagara_system": params["niagara_system_path"],
            }

        with patch("tools.niagara_tools._send", side_effect=fake_send):
            result = await mcp.get_tool("add_niagara_component")(
                None,
                blueprint_name="/Game/BP_BlackHoleFX",
                component_name="BlackHoleNiagara",
                niagara_system_path="/Game/VFX/NS_BlackHole",
            )

        self.assertTrue(result["success"])
        self.assertEqual(result["outputs"]["component_name"], "BlackHoleNiagara")
        self.assertEqual(calls[0][0], "add_niagara_component")
        self.assertEqual(calls[0][1]["blueprint_name"], "/Game/BP_BlackHoleFX")
        self.assertEqual(calls[0][1]["niagara_system_path"], "/Game/VFX/NS_BlackHole")

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
