"""Offline smoke coverage for IDE companion session status receipts."""

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
    testcase.assertEqual(payload["meta"]["tool"], "skill_compile_ide_companion_status")


def _session_plan() -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_session

    result = skill_compile_ide_companion_session(
        project_brief="solo developer stealth slice with generated props",
        mechanic_brief="enemy AI patrol that updates the objective HUD",
        include_generated_assets=True,
    )
    return result["outputs"]["plan"]


class TestD13IdeCompanionStatus(unittest.TestCase):
    def test_status_reports_wallet_blocker_and_next_action(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_status

        plan = _session_plan()
        readiness = {
            "outputs": {
                "ready": False,
                "blocking_gates": [{"name": "api_wallet_has_credits", "ready": False}],
            }
        }
        result = skill_compile_ide_companion_status(
            session_plan=plan,
            readiness_report=readiness,
            completed_phases=["orient_to_project"],
            evidence={"orient_to_project": {"complete": True, "artifacts": ["project context"]}},
        )

        _assert_structured(self, result, "status_ready")
        self.assertTrue(result["success"])
        status = result["outputs"]["status"]
        self.assertEqual(status["schema"], "unreal_mcp_ide_companion_status.v1")
        self.assertIn("api_wallet_has_credits", status["blocking_gates"])
        self.assertFalse(status["ready_for_paid_generation"])
        self.assertEqual(status["next_action"]["tool"], "gen_compile_ide_companion_readiness")
        self.assertGreaterEqual(status["blocked_phase_count"], 1)

    def test_status_accepts_json_strings_and_flags_missing_evidence(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_status

        plan = _session_plan()
        readiness = {"outputs": {"ready": True, "blocking_gates": []}}
        result = skill_compile_ide_companion_status(
            session_plan=json.dumps(plan),
            readiness_report=json.dumps(readiness),
            completed_phases=json.dumps(["orient_to_project", "session_preflight"]),
            evidence={},
        )

        _assert_structured(self, result, "status_ready")
        status = result["outputs"]["status"]
        self.assertTrue(status["ready_for_paid_generation"])
        self.assertTrue(status["ready_for_editor_mutation"])
        self.assertIn("orient_to_project", status["missing_evidence"])
        self.assertIn("session_preflight", status["missing_evidence"])

    def test_registered_tool_returns_json(self):
        from skills.playable_slice.skill import register_playable_slice_skill

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_compile_ide_companion_status", mcp.tools)

        payload = json.loads(asyncio.run(mcp.tools["skill_compile_ide_companion_status"](
            None,
            _session_plan(),
            readiness_report={"outputs": {"ready": True, "blocking_gates": []}},
            completed_phases=["orient_to_project"],
            evidence={"orient_to_project": {"complete": True}},
        )))

        _assert_structured(self, payload, "status_ready")
        self.assertEqual(payload["outputs"]["status"]["session_schema"], "unreal_mcp_ide_companion_session_plan.v1")

    def test_invalid_session_plan_is_structured(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_status

        payload = skill_compile_ide_companion_status({"schema": "wrong"})

        _assert_structured(self, payload, "invalid_session_plan")
        self.assertFalse(payload["success"])
        self.assertIn("session_plan must use unreal_mcp_ide_companion_session_plan.v1", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("skill_compile_ide_companion_status", skill_text)
        self.assertIn("unreal_mcp_ide_companion_status.v1", skill_text)
        self.assertIn("D13 IDE Companion Status Receipt", kb_text)
        self.assertIn("skill_compile_ide_companion_status", kb_text)
        self.assertIn("D.13 - IDE companion status receipt", changelog_text)
        self.assertIn("Update IDE Companion Status", panel_text)
        self.assertIn("unreal_mcp_ide_companion_status.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
