"""Offline smoke coverage for IDE companion evidence ledger persistence."""

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
    testcase.assertEqual(payload["meta"]["tool"], "skill_record_ide_companion_evidence")


def _session_plan() -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_session

    result = skill_compile_ide_companion_session(
        project_brief="solo developer companion slice with generated props",
        mechanic_brief="enemy AI patrol that updates the objective HUD",
        include_generated_assets=True,
    )
    return result["outputs"]["plan"]


class TestD15IdeCompanionEvidenceLedger(unittest.TestCase):
    def test_records_evidence_and_refreshes_status(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import skill_record_ide_companion_evidence

        plan = _session_plan()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                result = skill_record_ide_companion_evidence(
                    session_plan=plan,
                    phase_name="orient_to_project",
                    evidence_type="context",
                    summary="Project context and required KB guidance loaded.",
                    artifacts=["kb://32_AGENT_PLAYABLE_SLICE_RECIPE.md"],
                    readiness_report={"outputs": {"ready": False, "blocking_gates": [{"name": "api_wallet_has_credits"}]}},
                )
                self.assertTrue(Path(result["outputs"]["ledger_path"]).exists())

        _assert_structured(self, result, "evidence_recorded")
        self.assertTrue(result["success"])
        outputs = result["outputs"]
        self.assertEqual(outputs["schema"], "unreal_mcp_ide_companion_evidence_record.v1")
        self.assertIn("orient_to_project", outputs["ledger"]["evidence"])
        self.assertIn("api_wallet_has_credits", outputs["updated_status"]["blocking_gates"])
        self.assertEqual(outputs["updated_status"]["completed_phase_count"], 1)

    def test_appends_to_existing_ledger(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import skill_record_ide_companion_evidence

        plan = _session_plan()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                first = skill_record_ide_companion_evidence(plan, "orient_to_project", summary="Context loaded")
                second = skill_record_ide_companion_evidence(plan, "session_preflight", summary="Readiness blocked by wallet")

        _assert_structured(self, first, "evidence_recorded")
        _assert_structured(self, second, "evidence_recorded")
        self.assertEqual(len(second["outputs"]["ledger"]["events"]), 2)
        self.assertIn("session_preflight", second["outputs"]["ledger"]["evidence"])

    def test_registered_tool_returns_json(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import register_playable_slice_skill

        plan = _session_plan()
        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_record_ide_companion_evidence", mcp.tools)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                payload = json.loads(asyncio.run(mcp.tools["skill_record_ide_companion_evidence"](
                    None,
                    plan,
                    "mechanic_design",
                    evidence_type="plan",
                    summary="Mechanic plan validated",
                )))

        _assert_structured(self, payload, "evidence_recorded")
        self.assertIn("updated_status", payload["outputs"])

    def test_invalid_phase_is_structured(self):
        from skills.playable_slice.skill import skill_record_ide_companion_evidence

        payload = skill_record_ide_companion_evidence(_session_plan(), "not_a_phase")

        _assert_structured(self, payload, "unknown_phase")
        self.assertFalse(payload["success"])
        self.assertIn("unknown phase: not_a_phase", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("skill_record_ide_companion_evidence", skill_text)
        self.assertIn("unreal_mcp_ide_companion_evidence_record.v1", skill_text)
        self.assertIn("D15 IDE Companion Evidence Ledger", kb_text)
        self.assertIn("skill_record_ide_companion_evidence", kb_text)
        self.assertIn("D.15 - IDE companion evidence ledger", changelog_text)
        self.assertIn("Record IDE Companion Evidence", panel_text)
        self.assertIn("unreal_mcp_ide_companion_evidence_record.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
