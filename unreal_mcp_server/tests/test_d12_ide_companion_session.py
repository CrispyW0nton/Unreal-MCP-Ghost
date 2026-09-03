"""Offline smoke coverage for IDE companion session orchestration."""

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
    testcase.assertEqual(payload["meta"]["tool"], "skill_compile_ide_companion_session")


class TestD12IdeCompanionSession(unittest.TestCase):
    def test_session_plan_compiles_full_offline_workflow(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_session

        result = skill_compile_ide_companion_session(
            project_brief="single-developer dungeon slice with generated props and one enemy encounter",
            mechanic_brief="enemy AI patrol that chases the player and updates an objective HUD",
            include_generated_assets=True,
        )

        _assert_structured(self, result, "session_plan_ready")
        self.assertTrue(result["success"])
        self.assertFalse(result["outputs"]["network_required"])
        self.assertFalse(result["outputs"]["unreal_editor_required"])
        self.assertFalse(result["outputs"]["spend_required"])
        plan = result["outputs"]["plan"]
        self.assertEqual(plan["schema"], "unreal_mcp_ide_companion_session_plan.v1")
        self.assertEqual(plan["mechanic_plan"]["schema"], "unreal_mcp_gameplay_mechanic_plan.v1")
        self.assertEqual(plan["mechanic_plan"]["mechanic_kind"], "ai_encounter")
        self.assertGreaterEqual(len(plan["phases"]), 7)
        self.assertGreaterEqual(len(plan["generated_asset_prompts"]), 4)
        self.assertGreaterEqual(len(plan["generated_animation_prompts"]), 2)
        self.assertGreater(plan["estimated_tripo_credits"], 0)
        self.assertGreater(plan["estimated_uthana_motion_seconds"], 0)
        self.assertTrue(plan["capabilities"]["animation_generation"])
        self.assertEqual(plan["generated_animation_prompts"], plan["mechanic_plan"]["generated_animation_prompts"])
        self.assertTrue(plan["mechanic_plan"]["system_hooks"]["animation"]["needed"])
        self.assertEqual(plan["generated_animation_prompts"][0]["provider"], "uthana")
        self.assertEqual(plan["generated_animation_prompts"][0]["task_type"], "text_to_motion")
        self.assertIn("gen_uthana_text_to_motion", json.dumps(plan["phases"]))
        self.assertIn("gen_compile_ide_companion_readiness", json.dumps(plan["phases"]))
        self.assertIn("uthana_api_key_configured", json.dumps(plan["gates"]))
        self.assertIn("animation_retarget_readback", json.dumps(plan["gates"]))
        self.assertIn("api_wallet_has_credits", json.dumps(plan["gates"]))
        self.assertIn("unreal_bridge_reachable", json.dumps(plan["gates"]))
        self.assertIn("pie_launch_session", json.dumps(plan["next_actions"]))

    def test_session_plan_can_disable_generated_assets(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_session

        result = skill_compile_ide_companion_session(
            project_brief="prototype a door interaction loop using placeholders",
            mechanic_brief="locked door objective that opens after interaction",
            include_generated_assets=False,
        )

        _assert_structured(self, result, "session_plan_ready")
        plan = result["outputs"]["plan"]
        self.assertEqual(plan["generated_asset_prompts"], [])
        self.assertEqual(plan["generated_animation_prompts"], [])
        self.assertEqual(plan["estimated_tripo_credits"], 0)
        self.assertEqual(plan["estimated_uthana_motion_seconds"], 0)
        self.assertFalse(plan["capabilities"]["asset_generation"])
        self.assertFalse(plan["capabilities"]["animation_generation"])

    def test_registered_tool_returns_json(self):
        from skills.playable_slice.skill import register_playable_slice_skill

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_compile_ide_companion_session", mcp.tools)

        payload = json.loads(asyncio.run(mcp.tools["skill_compile_ide_companion_session"](
            None,
            "solo developer vertical slice with a dash mechanic",
            mechanic_brief="player dash ability with cooldown and HUD feedback",
        )))

        _assert_structured(self, payload, "session_plan_ready")
        self.assertEqual(payload["outputs"]["plan"]["mechanic_plan"]["mechanic_kind"], "ability_cooldown")

    def test_invalid_project_brief_is_structured(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_session

        payload = skill_compile_ide_companion_session("")

        _assert_structured(self, payload, "invalid_project_brief")
        self.assertFalse(payload["success"])
        self.assertIn("project_brief is required", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        server_text = (SERVER_ROOT / "unreal_mcp_server.py").read_text(encoding="utf-8")
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("register_playable_slice_skill", server_text)
        self.assertIn("skill_compile_ide_companion_session", skill_text)
        self.assertIn("unreal_mcp_ide_companion_session_plan.v1", skill_text)
        self.assertIn("D12 IDE Companion Session Orchestrator", kb_text)
        self.assertIn("skill_compile_ide_companion_session", kb_text)
        self.assertIn("D.12 - IDE companion session orchestrator", changelog_text)
        self.assertIn("Start IDE Companion Session", panel_text)
        self.assertIn("unreal_mcp_ide_companion_session_plan.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
