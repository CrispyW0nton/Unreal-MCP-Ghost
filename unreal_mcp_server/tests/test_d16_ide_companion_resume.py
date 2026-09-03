"""Offline smoke coverage for resuming IDE companion sessions from ledgers."""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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
    testcase.assertEqual(payload["meta"]["tool"], "skill_resume_ide_companion_session")


def _session_plan() -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_session

    result = skill_compile_ide_companion_session(
        project_brief="solo developer resume test slice",
        mechanic_brief="enemy AI patrol that updates the objective HUD",
        session_name="resume-test",
        include_generated_assets=True,
    )
    return result["outputs"]["plan"]


class TestD16IdeCompanionResume(unittest.TestCase):
    def test_resume_from_session_name_rebuilds_status_and_work_order(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import skill_record_ide_companion_evidence, skill_resume_ide_companion_session

        plan = _session_plan()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                skill_record_ide_companion_evidence(
                    session_plan=plan,
                    phase_name="orient_to_project",
                    summary="Context loaded",
                    readiness_report={"outputs": {"ready": False, "blocking_gates": [{"name": "api_wallet_has_credits"}]}},
                )
                result = skill_resume_ide_companion_session(session_name="resume-test")

        _assert_structured(self, result, "session_resumed")
        self.assertTrue(result["success"])
        outputs = result["outputs"]
        self.assertEqual(outputs["schema"], "unreal_mcp_ide_companion_resume.v1")
        self.assertEqual(outputs["event_count"], 1)
        self.assertIn("orient_to_project", outputs["completed_phases"])
        self.assertIn("api_wallet_has_credits", outputs["status"]["blocking_gates"])
        self.assertEqual(outputs["work_order"]["schema"], "unreal_mcp_ide_companion_work_order.v1")

    def test_resume_from_explicit_path(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import skill_record_ide_companion_evidence, skill_resume_ide_companion_session

        plan = _session_plan()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                record = skill_record_ide_companion_evidence(plan, "mechanic_design", summary="Mechanic planned")
                result = skill_resume_ide_companion_session(ledger_path=record["outputs"]["ledger_path"])

        _assert_structured(self, result, "session_resumed")
        self.assertTrue(result["success"])
        self.assertIn("mechanic_design", result["outputs"]["completed_phases"])

    def test_registered_tool_returns_json(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import register_playable_slice_skill, skill_record_ide_companion_evidence

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_resume_ide_companion_session", mcp.tools)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                skill_record_ide_companion_evidence(_session_plan(), "orient_to_project", summary="Context loaded")
                payload = json.loads(asyncio.run(mcp.tools["skill_resume_ide_companion_session"](
                    None,
                    session_name="resume-test",
                )))

        _assert_structured(self, payload, "session_resumed")
        self.assertEqual(payload["outputs"]["schema"], "unreal_mcp_ide_companion_resume.v1")

    def test_missing_ledger_is_structured(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import skill_resume_ide_companion_session

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                payload = skill_resume_ide_companion_session(session_name="missing")

        _assert_structured(self, payload, "ledger_not_found")
        self.assertFalse(payload["success"])
        self.assertIn("ledger not found or empty", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("skill_resume_ide_companion_session", skill_text)
        self.assertIn("unreal_mcp_ide_companion_resume.v1", skill_text)
        self.assertIn("D16 IDE Companion Session Resume", kb_text)
        self.assertIn("skill_resume_ide_companion_session", kb_text)
        self.assertIn("D.16 - IDE companion session resume", changelog_text)
        self.assertIn("Resume IDE Companion Session", panel_text)
        self.assertIn("unreal_mcp_ide_companion_resume.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
