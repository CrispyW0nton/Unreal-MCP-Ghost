"""Offline smoke coverage for IDE companion work orders."""

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
    testcase.assertEqual(payload["meta"]["tool"], "skill_compile_ide_companion_work_order")


def _session_plan() -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_session

    result = skill_compile_ide_companion_session(
        project_brief="solo developer sci-fi slice with generated props",
        mechanic_brief="enemy AI patrol that updates the objective HUD",
        include_generated_assets=True,
    )
    return result["outputs"]["plan"]


class TestD14IdeCompanionWorkOrder(unittest.TestCase):
    def test_work_order_uses_status_blockers_and_stop_conditions(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_work_order

        plan = _session_plan()
        status = {
            "schema": "unreal_mcp_ide_companion_status.v1",
            "blocking_gates": ["api_wallet_has_credits"],
            "next_phase": "session_preflight",
            "phase_status": [{"name": "session_preflight", "state": "available"}],
        }
        result = skill_compile_ide_companion_work_order(plan, companion_status=status)

        _assert_structured(self, result, "work_order_ready")
        self.assertTrue(result["success"])
        work_order = result["outputs"]["work_order"]
        self.assertEqual(work_order["schema"], "unreal_mcp_ide_companion_work_order.v1")
        self.assertEqual(work_order["target_phase"], "session_preflight")
        self.assertFalse(work_order["safe_to_execute_now"])
        self.assertIn("api_wallet_has_credits", work_order["blocking_gates"])
        self.assertIn("resolve_blocking_gates", json.dumps(work_order["prerequisites"]))
        self.assertIn("Stop before any paid Tripo task", json.dumps(work_order["stop_conditions"]))

    def test_target_phase_asset_generation_emits_tripo_steps(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_work_order

        plan = _session_plan()
        status = {
            "schema": "unreal_mcp_ide_companion_status.v1",
            "blocking_gates": [],
            "next_phase": "asset_generation",
            "phase_status": [{"name": "asset_generation", "state": "available"}],
        }
        result = skill_compile_ide_companion_work_order(
            session_plan=json.dumps(plan),
            companion_status=json.dumps(status),
            target_phase="asset_generation",
        )

        _assert_structured(self, result, "work_order_ready")
        work_order = result["outputs"]["work_order"]
        self.assertTrue(work_order["safe_to_execute_now"])
        self.assertGreaterEqual(len(work_order["tool_steps"]), 4)
        self.assertEqual(work_order["tool_steps"][0]["tool"], "gen_tripo_text_to_model")
        self.assertTrue(work_order["tool_steps"][0]["arguments"]["confirm_spend"])
        self.assertIn("task ids", json.dumps(work_order["evidence_to_collect"]))

    def test_editor_work_order_includes_feature_template_operations(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_work_order

        plan = _session_plan()
        status = {
            "schema": "unreal_mcp_ide_companion_status.v1",
            "blocking_gates": [],
            "next_phase": "editor_implementation",
            "phase_status": [{"name": "editor_implementation", "state": "available"}],
        }
        result = skill_compile_ide_companion_work_order(
            plan,
            companion_status=status,
            target_phase="editor_implementation",
        )

        _assert_structured(self, result, "work_order_ready")
        work_order = result["outputs"]["work_order"]
        template = work_order["feature_template_work"]
        self.assertEqual(template["schema"], "unreal_mcp_gameplay_feature_template.v1")
        self.assertEqual(template["template_name"], "enemy_patrol_chase_attack")
        self.assertIn("Blackboard keys TargetActor", json.dumps(template["graph_component_operations"]))
        self.assertIn("editor_operation_checklist", template)
        self.assertIn("ai_blackboard_behavior_tree", {row["operation_type"] for row in template["editor_operation_checklist"]})
        self.assertIn("bt_get_info", json.dumps(template["editor_operation_checklist"]))
        self.assertTrue(all("operation_proof_contract" in row for row in template["editor_operation_checklist"]))
        self.assertIn("blueprint_compile_report", json.dumps(template["editor_operation_checklist"]))
        self.assertIn("ide_companion_ledger_event", json.dumps(template["editor_operation_checklist"]))
        self.assertEqual(template["completion_contract"]["schema"], "unreal_mcp_gameplay_feature_completion_contract.v1")
        self.assertIn("editor_operations_read_back", json.dumps(template["completion_contract"]["proof_gates"]))
        self.assertIn("compile_blueprint_and_report succeeds", json.dumps(template["compile_readback_checks"]))
        self.assertIn("repair work order", json.dumps(template["repair_instructions"]))
        self.assertIn("feature template packet", work_order["evidence_to_collect"])
        self.assertIn("Feature-template graph/component operations", json.dumps(work_order["acceptance_criteria"]))

    def test_runtime_work_order_includes_template_pie_validation(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_work_order

        plan = _session_plan()
        status = {
            "schema": "unreal_mcp_ide_companion_status.v1",
            "blocking_gates": [],
            "next_phase": "runtime_verification",
            "phase_status": [{"name": "runtime_verification", "state": "available"}],
        }
        result = skill_compile_ide_companion_work_order(
            plan,
            companion_status=status,
            target_phase="runtime_verification",
        )

        _assert_structured(self, result, "work_order_ready")
        work_order = result["outputs"]["work_order"]
        template = work_order["feature_template_work"]
        self.assertEqual(template["template_name"], "enemy_patrol_chase_attack")
        self.assertIn("Enemy patrols when no target is known", json.dumps(template["pie_validation"]))
        self.assertIn("pie_validation_passed", json.dumps(template["completion_contract"]["proof_gates"]))
        self.assertIn("PIE log and viewport screenshot", work_order["evidence_to_collect"])
        self.assertIn("Feature-template PIE validation steps", json.dumps(work_order["acceptance_criteria"]))

    def test_registered_tool_returns_json(self):
        from skills.playable_slice.skill import register_playable_slice_skill

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_compile_ide_companion_work_order", mcp.tools)

        payload = json.loads(asyncio.run(mcp.tools["skill_compile_ide_companion_work_order"](
            None,
            _session_plan(),
            companion_status={"schema": "unreal_mcp_ide_companion_status.v1", "blocking_gates": [], "next_phase": "mechanic_design", "phase_status": [{"name": "mechanic_design", "state": "available"}]},
        )))

        _assert_structured(self, payload, "work_order_ready")
        self.assertEqual(payload["outputs"]["work_order"]["target_phase"], "mechanic_design")

    def test_invalid_session_plan_is_structured(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_work_order

        payload = skill_compile_ide_companion_work_order({"schema": "wrong"})

        _assert_structured(self, payload, "invalid_session_plan")
        self.assertFalse(payload["success"])
        self.assertIn("session_plan must use unreal_mcp_ide_companion_session_plan.v1", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("skill_compile_ide_companion_work_order", skill_text)
        self.assertIn("unreal_mcp_ide_companion_work_order.v1", skill_text)
        self.assertIn("feature_template_work", skill_text)
        self.assertIn("D14 IDE Companion Work Order", kb_text)
        self.assertIn("D37 Feature-Template Work Orders", kb_text)
        self.assertIn("skill_compile_ide_companion_work_order", kb_text)
        self.assertIn("D.37 - Feature-template work orders", changelog_text)
        self.assertIn("D.14 - IDE companion work order", changelog_text)
        self.assertIn("Generate IDE Companion Work Order", panel_text)
        self.assertIn("unreal_mcp_ide_companion_work_order.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
