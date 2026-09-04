"""Offline smoke coverage for IDE companion placeholder manifests."""

from __future__ import annotations

import asyncio
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
    testcase.assertEqual(payload["meta"]["tool"], "skill_compile_ide_companion_placeholder_manifest")


def _session_plan(include_generated_assets: bool = True) -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_session

    result = skill_compile_ide_companion_session(
        project_brief="solo developer placeholder manifest slice",
        mechanic_brief="enemy AI patrol that updates the objective HUD",
        session_name="placeholder-test",
        include_generated_assets=include_generated_assets,
    )
    return result["outputs"]["plan"]


class TestD19IdeCompanionPlaceholderManifest(unittest.TestCase):
    def test_manifest_maps_generated_prompts_to_placeholders(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_placeholder_manifest

        plan = _session_plan(True)
        result = skill_compile_ide_companion_placeholder_manifest(plan)

        _assert_structured(self, result, "placeholder_manifest_ready")
        manifest = result["outputs"]["manifest"]
        self.assertEqual(manifest["schema"], "unreal_mcp_ide_companion_placeholder_manifest.v1")
        self.assertGreaterEqual(len(manifest["placeholder_assets"]), 4)
        self.assertEqual(len(manifest["placeholder_assets"]), len(manifest["replacement_map"]))
        self.assertIn("/Placeholders", manifest["placeholder_root"])
        self.assertIn("tripo_prompt", manifest["replacement_map"][0])
        self.assertFalse(manifest["network_required"])
        self.assertFalse(manifest["spend_required"])

    def test_manifest_has_focus_placeholder_without_generated_assets(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_placeholder_manifest

        result = skill_compile_ide_companion_placeholder_manifest(_session_plan(False))
        manifest = result["outputs"]["manifest"]

        _assert_structured(self, result, "placeholder_manifest_ready")
        self.assertEqual(len(manifest["placeholder_assets"]), 1)
        self.assertEqual(manifest["placeholder_assets"][0]["placeholder_name"], "PH_MechanicFocus")
        self.assertEqual(manifest["replacement_map"], [])

    def test_registered_tool_returns_json(self):
        from skills.playable_slice.skill import register_playable_slice_skill

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_compile_ide_companion_placeholder_manifest", mcp.tools)
        payload = json.loads(asyncio.run(mcp.tools["skill_compile_ide_companion_placeholder_manifest"](
            None,
            _session_plan(True),
        )))

        _assert_structured(self, payload, "placeholder_manifest_ready")
        self.assertEqual(payload["outputs"]["manifest"]["schema"], "unreal_mcp_ide_companion_placeholder_manifest.v1")

    def test_invalid_session_plan_is_structured(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_placeholder_manifest

        payload = skill_compile_ide_companion_placeholder_manifest({"schema": "wrong"})

        _assert_structured(self, payload, "invalid_session_plan")
        self.assertFalse(payload["success"])
        self.assertIn("session_plan must use unreal_mcp_ide_companion_session_plan.v1", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("skill_compile_ide_companion_placeholder_manifest", skill_text)
        self.assertIn("unreal_mcp_ide_companion_placeholder_manifest.v1", skill_text)
        self.assertIn("D19 IDE Companion Placeholder Manifest", kb_text)
        self.assertIn("skill_compile_ide_companion_placeholder_manifest", kb_text)
        self.assertIn("D.19 - IDE companion placeholder manifest", changelog_text)
        self.assertIn("Compile Placeholder Asset Manifest", panel_text)
        self.assertIn("unreal_mcp_ide_companion_placeholder_manifest.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
