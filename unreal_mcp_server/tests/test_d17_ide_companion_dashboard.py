"""Offline smoke coverage for IDE companion dashboard packets."""

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
    testcase.assertEqual(payload["meta"]["tool"], "skill_compile_ide_companion_dashboard")


def _session_plan() -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_session

    result = skill_compile_ide_companion_session(
        project_brief="solo developer dashboard test slice",
        mechanic_brief="enemy AI patrol that updates the objective HUD",
        session_name="dashboard-test",
        include_generated_assets=True,
    )
    return result["outputs"]["plan"]


class TestD17IdeCompanionDashboard(unittest.TestCase):
    def test_dashboard_from_ledger_has_cards_and_next_work(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import skill_compile_ide_companion_dashboard, skill_record_ide_companion_evidence

        plan = _session_plan()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                skill_record_ide_companion_evidence(
                    session_plan=plan,
                    phase_name="orient_to_project",
                    summary="Context loaded",
                    readiness_report={"outputs": {"ready": False, "blocking_gates": [{"name": "api_wallet_has_credits"}]}},
                )
                result = skill_compile_ide_companion_dashboard(session_name="dashboard-test")

        _assert_structured(self, result, "dashboard_ready")
        dashboard = result["outputs"]["dashboard"]
        self.assertEqual(dashboard["schema"], "unreal_mcp_ide_companion_dashboard.v1")
        self.assertGreaterEqual(len(dashboard["cards"]), 6)
        self.assertIn("api_wallet_has_credits", dashboard["status"]["blocking_gates"])
        self.assertEqual(dashboard["work_order"]["target_phase"], "session_preflight")
        self.assertIn("Show IDE Companion Dashboard", dashboard["command_palette"])

    def test_dashboard_from_initial_plan_without_ledger(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_dashboard

        plan = _session_plan()
        result = skill_compile_ide_companion_dashboard(
            session_plan=plan,
            readiness_report={"outputs": {"ready": True, "blocking_gates": []}},
        )

        _assert_structured(self, result, "dashboard_ready")
        dashboard = result["outputs"]["dashboard"]
        self.assertEqual(dashboard["status"]["completed_phase_count"], 0)
        self.assertTrue(dashboard["status"]["ready_for_paid_generation"])
        self.assertGreater(len(dashboard["cards"]), 0)

    def test_registered_tool_returns_json(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import register_playable_slice_skill, skill_record_ide_companion_evidence

        plan = _session_plan()
        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_compile_ide_companion_dashboard", mcp.tools)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                skill_record_ide_companion_evidence(plan, "orient_to_project", summary="Context loaded")
                payload = json.loads(asyncio.run(mcp.tools["skill_compile_ide_companion_dashboard"](
                    None,
                    session_name="dashboard-test",
                )))

        _assert_structured(self, payload, "dashboard_ready")
        self.assertEqual(payload["outputs"]["dashboard"]["schema"], "unreal_mcp_ide_companion_dashboard.v1")

    def test_missing_plan_is_structured(self):
        import skills.playable_slice.skill as skill_module
        from skills.playable_slice.skill import skill_compile_ide_companion_dashboard

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                payload = skill_compile_ide_companion_dashboard(session_name="missing")

        _assert_structured(self, payload, "missing_session_plan")
        self.assertFalse(payload["success"])
        self.assertIn("session_plan must use unreal_mcp_ide_companion_session_plan.v1", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("skill_compile_ide_companion_dashboard", skill_text)
        self.assertIn("unreal_mcp_ide_companion_dashboard.v1", skill_text)
        self.assertIn("D17 IDE Companion Dashboard", kb_text)
        self.assertIn("skill_compile_ide_companion_dashboard", kb_text)
        self.assertIn("D.17 - IDE companion dashboard", changelog_text)
        self.assertIn("Show IDE Companion Dashboard", panel_text)
        self.assertIn("unreal_mcp_ide_companion_dashboard.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
