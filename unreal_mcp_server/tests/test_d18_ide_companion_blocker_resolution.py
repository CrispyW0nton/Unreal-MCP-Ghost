"""Offline smoke coverage for IDE companion blocker resolution."""

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
    testcase.assertEqual(payload["meta"]["tool"], "skill_compile_ide_companion_blocker_resolution")


def _session_plan() -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_session

    result = skill_compile_ide_companion_session(
        project_brief="solo developer blocker resolution slice",
        mechanic_brief="enemy AI patrol that updates the objective HUD",
        session_name="blocker-test",
        include_generated_assets=True,
    )
    return result["outputs"]["plan"]


class TestD18IdeCompanionBlockerResolution(unittest.TestCase):
    def test_wallet_blocker_recommends_placeholder_path(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_blocker_resolution

        plan = _session_plan()
        status = {
            "schema": "unreal_mcp_ide_companion_status.v1",
            "blocking_gates": ["api_wallet_has_credits"],
            "next_action": {"tool": "gen_compile_ide_companion_readiness"},
        }
        result = skill_compile_ide_companion_blocker_resolution(
            session_plan=plan,
            companion_status=status,
            preferred_strategy="continue_with_placeholders",
        )

        _assert_structured(self, result, "blocker_resolution_ready")
        resolution = result["outputs"]["resolution"]
        self.assertEqual(resolution["schema"], "unreal_mcp_ide_companion_blocker_resolution.v1")
        self.assertIn("api_wallet_has_credits", resolution["blocking_gates"])
        self.assertEqual(resolution["recommended_path"]["strategy"], "continue_with_placeholders")
        self.assertIn("Placeholders", resolution["placeholder_policy"]["content_path"])
        self.assertIn("Use placeholder meshes", json.dumps(resolution["resolutions"]))

    def test_bridge_blocker_has_editor_offline_policy(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_blocker_resolution

        result = skill_compile_ide_companion_blocker_resolution(
            session_plan=_session_plan(),
            companion_status={
                "schema": "unreal_mcp_ide_companion_status.v1",
                "blocking_gates": ["unreal_bridge_reachable"],
            },
            preferred_strategy="unblock",
        )

        _assert_structured(self, result, "blocker_resolution_ready")
        resolution = result["outputs"]["resolution"]
        self.assertEqual(resolution["recommended_path"]["strategy"], "unblock_first")
        self.assertIn("scripts/bridge_ping.py succeeds", json.dumps(resolution["resolutions"]))
        self.assertIn("Do not call editor mutation tools", json.dumps(resolution["bridge_offline_policy"]))

    def test_registered_tool_returns_json(self):
        from skills.playable_slice.skill import register_playable_slice_skill

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_compile_ide_companion_blocker_resolution", mcp.tools)
        payload = json.loads(asyncio.run(mcp.tools["skill_compile_ide_companion_blocker_resolution"](
            None,
            session_plan=_session_plan(),
            companion_status={"schema": "unreal_mcp_ide_companion_status.v1", "blocking_gates": []},
        )))

        _assert_structured(self, payload, "blocker_resolution_ready")
        self.assertEqual(payload["outputs"]["resolution"]["recommended_path"]["strategy"], "continue")

    def test_missing_plan_is_structured(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_blocker_resolution

        payload = skill_compile_ide_companion_blocker_resolution()

        _assert_structured(self, payload, "missing_session_plan")
        self.assertFalse(payload["success"])
        self.assertIn("session_plan must use unreal_mcp_ide_companion_session_plan.v1", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("skill_compile_ide_companion_blocker_resolution", skill_text)
        self.assertIn("unreal_mcp_ide_companion_blocker_resolution.v1", skill_text)
        self.assertIn("D18 IDE Companion Blocker Resolution", kb_text)
        self.assertIn("skill_compile_ide_companion_blocker_resolution", kb_text)
        self.assertIn("D.18 - IDE companion blocker resolution", changelog_text)
        self.assertIn("Resolve IDE Companion Blockers", panel_text)
        self.assertIn("unreal_mcp_ide_companion_blocker_resolution.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
