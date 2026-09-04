"""Offline smoke coverage for IDE companion editor action queues."""

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
    testcase.assertEqual(payload["meta"]["tool"], "skill_compile_ide_companion_editor_queue")


def _session_plan() -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_session

    result = skill_compile_ide_companion_session(
        project_brief="solo developer queued editor slice",
        mechanic_brief="enemy AI patrol that updates the objective HUD",
        session_name="editor-queue-test",
        include_generated_assets=True,
    )
    return result["outputs"]["plan"]


def _bridge_blocked_status(plan: dict) -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_status

    result = skill_compile_ide_companion_status(
        session_plan=plan,
        current_blockers=["unreal_bridge_reachable", "api_wallet_has_credits"],
    )
    return result["outputs"]["status"]


class TestD20IdeCompanionEditorQueue(unittest.TestCase):
    def test_placeholder_manifest_compiles_bridge_gated_queue(self):
        from skills.playable_slice import skill as skill_module

        plan = _session_plan()
        status = _bridge_blocked_status(plan)
        manifest_result = skill_module.skill_compile_ide_companion_placeholder_manifest(plan)

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                result = skill_module.skill_compile_ide_companion_editor_queue(
                    session_plan=plan,
                    companion_status=status,
                    placeholder_manifest=manifest_result,
                    queue_name="placeholder_queue",
                )
                self.assertTrue(Path(result["outputs"]["queue_path"]).exists())

        _assert_structured(self, result, "editor_queue_ready")
        queue = result["outputs"]["queue"]
        self.assertEqual(queue["schema"], "unreal_mcp_ide_companion_editor_queue.v1")
        self.assertEqual(queue["source"], "placeholder_manifest")
        self.assertTrue(queue["bridge_required"])
        self.assertTrue(queue["bridge_blocked"])
        self.assertFalse(queue["can_execute_now"])
        self.assertIn("unreal_bridge_reachable", queue["blocking_gates"])
        self.assertGreaterEqual(len(queue["actions"]), 3)

    def test_work_order_steps_can_be_queued_without_manifest(self):
        from skills.playable_slice import skill as skill_module

        plan = _session_plan()
        status = _bridge_blocked_status(plan)
        work_order = skill_module.skill_compile_ide_companion_work_order(
            session_plan=plan,
            companion_status=status,
            target_phase="editor_implementation",
        )

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                result = skill_module.skill_compile_ide_companion_editor_queue(
                    session_plan=plan,
                    companion_status=status,
                    work_order=work_order,
                )

        _assert_structured(self, result, "editor_queue_ready")
        queue = result["outputs"]["queue"]
        self.assertEqual(queue["source"], "work_order")
        self.assertEqual(queue["target_phase"], "editor_implementation")
        self.assertFalse(queue["can_execute_now"])
        feature_template = queue["feature_template"]
        self.assertEqual(feature_template["schema"], "unreal_mcp_gameplay_feature_template.v1")
        self.assertEqual(feature_template["template_name"], "enemy_patrol_chase_attack")
        self.assertGreaterEqual(feature_template["editor_operation_count"], 1)
        self.assertEqual(feature_template["next_operation_id"], "enemy_patrol_chase_attack_01")
        self.assertEqual(feature_template["next_operation_type"], "ai_blackboard_behavior_tree")
        self.assertIn("Blackboard keys TargetActor", feature_template["next_operation_summary"])
        self.assertIn("set_behavior_tree_blackboard", feature_template["next_operation_tool_candidates"])
        self.assertIn("unreal_bridge_reachable", feature_template["next_operation_required_before"])
        self.assertIn("graph_or_component_readback", feature_template["next_operation_required_after"])
        self.assertIn("compile report missing or failed", feature_template["next_operation_stop_if_missing"])

    def test_registered_tool_returns_json(self):
        from skills.playable_slice import skill as skill_module

        plan = _session_plan()
        status = _bridge_blocked_status(plan)
        manifest = skill_module.skill_compile_ide_companion_placeholder_manifest(plan)
        mcp = _MockMCP()
        skill_module.register_playable_slice_skill(mcp)

        self.assertIn("skill_compile_ide_companion_editor_queue", mcp.tools)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                payload = json.loads(asyncio.run(mcp.tools["skill_compile_ide_companion_editor_queue"](
                    None,
                    plan,
                    status,
                    None,
                    manifest,
                    "registered_queue",
                )))

        _assert_structured(self, payload, "editor_queue_ready")
        self.assertEqual(payload["outputs"]["queue"]["schema"], "unreal_mcp_ide_companion_editor_queue.v1")

    def test_invalid_session_plan_is_structured(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_editor_queue

        payload = skill_compile_ide_companion_editor_queue({"schema": "wrong"})

        _assert_structured(self, payload, "invalid_session_plan")
        self.assertFalse(payload["success"])
        self.assertIn("session_plan must use unreal_mcp_ide_companion_session_plan.v1", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("skill_compile_ide_companion_editor_queue", skill_text)
        self.assertIn("unreal_mcp_ide_companion_editor_queue.v1", skill_text)
        self.assertIn("D20 IDE Companion Editor Action Queue", kb_text)
        self.assertIn("skill_compile_ide_companion_editor_queue", kb_text)
        self.assertIn("D.20 - IDE companion editor action queue", changelog_text)
        self.assertIn("Queue IDE Companion Editor Actions", panel_text)
        self.assertIn("unreal_mcp_ide_companion_editor_queue.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
