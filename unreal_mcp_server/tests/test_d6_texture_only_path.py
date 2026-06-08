"""Offline smoke coverage for Workstream D.6 texture-only path."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
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


def _assert_structured(testcase: unittest.TestCase, payload: dict, stage: str):
    for key in ("success", "stage", "message", "inputs", "outputs", "warnings", "errors", "log_tail", "meta"):
        testcase.assertIn(key, payload)
    testcase.assertEqual(payload["stage"], stage)
    testcase.assertEqual(payload["meta"]["tool"], stage)


class TestD6TextureOnlyPath(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.generative_tools import register_generative_tools

        self.mcp = _MockMCP()
        register_generative_tools(self.mcp)

    def test_d6_tool_registers(self):
        self.assertIn("gen_texture_from_prompt", self.mcp.tools)

    async def test_tripo_texture_from_prompt_reports_unsupported_with_material_plan(self):
        payload = json.loads(await self.mcp.tools["gen_texture_from_prompt"](
            ctx=None,
            prompt="wet mossy stone floor, hand-painted fantasy style",
            channels=["albedo", "normal", "orm"],
            resolution=1024,
            content_path="/Game/Generated/Dungeon",
            asset_name="MossyStone",
        ))

        _assert_structured(self, payload, "gen_texture_from_prompt")
        self.assertFalse(payload["success"])
        self.assertFalse(payload["outputs"]["provider_support"]["supported"])
        self.assertFalse(payload["outputs"]["network_required"])
        requested = payload["outputs"]["requested_texture_set"]
        self.assertEqual(requested["channels"], ["BaseColor", "Normal", "ORM"])
        plan = payload["outputs"]["materialization_plan"]
        self.assertEqual(plan["texture_parameters"]["BaseColorTexture"], "/Game/Generated/Dungeon/Textures/T_MossyStone_BaseColor")
        self.assertEqual(plan["texture_parameters"]["NormalTexture"], "/Game/Generated/Dungeon/Textures/T_MossyStone_Normal")
        self.assertEqual(plan["texture_parameters"]["ORMTexture"], "/Game/Generated/Dungeon/Textures/T_MossyStone_ORM")
        self.assertEqual(plan["material_tool_handoff"][0]["tool"], "material_create_master")
        self.assertEqual(plan["material_tool_handoff"][2]["tool"], "material_set_instance_parameters_bulk")
        self.assertEqual(payload["outputs"]["tripo_model_task_alternative"]["tool"], "gen_tripo_texture_model")

    async def test_texture_from_prompt_validates_channels_and_resolution(self):
        bad_channel = json.loads(await self.mcp.tools["gen_texture_from_prompt"](
            ctx=None,
            prompt="painted wood planks",
            channels=["BaseColor", "Specular"],
            resolution=1024,
        ))
        bad_resolution = json.loads(await self.mcp.tools["gen_texture_from_prompt"](
            ctx=None,
            prompt="painted wood planks",
            channels=["BaseColor"],
            resolution=1536,
        ))

        _assert_structured(self, bad_channel, "gen_texture_from_prompt")
        _assert_structured(self, bad_resolution, "gen_texture_from_prompt")
        self.assertFalse(bad_channel["success"])
        self.assertIn("Specular", bad_channel["outputs"]["channel_state"]["invalid_channels"])
        self.assertFalse(bad_resolution["success"])
        self.assertIn(1024, bad_resolution["outputs"]["resolution_state"]["allowed_resolutions"])

    def test_d6_static_kb_and_changelog(self):
        kb_text = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        generative_text = (SERVER_ROOT / "tools" / "generative_tools.py").read_text(encoding="utf-8")
        tripo_text = (SERVER_ROOT / "tools" / "generative" / "tripo.py").read_text(encoding="utf-8")

        self.assertIn("Texture-Only Path", kb_text)
        self.assertIn("gen_texture_from_prompt", kb_text)
        self.assertIn("material_create_instance_from_master", kb_text)
        self.assertIn("D.6 - Texture-only path", changelog_text)
        self.assertIn("gen_texture_from_prompt", generative_text)
        self.assertIn("supports_texture_from_prompt", tripo_text)


if __name__ == "__main__":
    unittest.main()
