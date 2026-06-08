"""Offline smoke coverage for Workstream D.7 playable-slice skill."""

from __future__ import annotations

import asyncio
import json
import os
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
    testcase.assertEqual(payload["meta"]["tool"], "skill_generate_playable_slice")


class TestD7PlayableSliceSkill(unittest.TestCase):
    def _settings_context(self, api_key: str = ""):
        import tools.generative_tools as generative_tools

        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        settings_path = root / "Saved" / "MCPChat" / "generative_settings.json"
        secrets_path = root / "Saved" / "MCPChat" / "secrets.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps({
            "default_model_version": "v3.1-20260211",
            "default_texture_quality": "standard",
            "output_folder": "/Game/Generated",
            "session_credit_budget": 1000,
            "credit_usage_by_session": {},
        }), encoding="utf-8")
        if api_key:
            secrets_path.write_text(json.dumps({"TRIPO_API_KEY": api_key}), encoding="utf-8")
        return tmp, patch.object(generative_tools, "_SETTINGS_PATH", settings_path), patch.object(generative_tools, "_SECRETS_PATH", secrets_path), patch.dict(os.environ, {"TRIPO_API_KEY": ""})

    def test_d7_tool_registers(self):
        from skills.playable_slice.skill import register_playable_slice_skill

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)

        self.assertIn("skill_generate_playable_slice", mcp.tools)

    def test_plan_mode_returns_valid_schema_without_network(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        result = skill_generate_playable_slice("third-person dungeon demo with a slime and boss")

        _assert_structured(self, result, "plan_ready")
        self.assertTrue(result["success"])
        self.assertFalse(result["outputs"]["network_required"])
        plan = result["outputs"]["plan"]
        self.assertEqual(plan["schema"], "unreal_mcp_playable_slice_plan.v1")
        self.assertEqual(len(plan["assets"]), 4)
        self.assertEqual([asset["role"] for asset in plan["assets"]].count("prop"), 2)
        self.assertTrue(all(asset["smart_low_poly"] is True for asset in plan["assets"]))
        self.assertIn("skill_package_vertical_slice_report", plan["validation"]["report_tool"])

    def test_submit_assets_requires_tripo_api_key(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        tmp, settings_patch, secrets_patch, env_patch = self._settings_context(api_key="")
        with tmp, settings_patch, secrets_patch, env_patch:
            result = skill_generate_playable_slice(
                "third-person dungeon demo with a slime",
                mode="submit_assets",
                confirm_spend=True,
            )

        _assert_structured(self, result, "auth_required")
        self.assertFalse(result["success"])
        self.assertIn("TRIPO_API_KEY", result["errors"][0])

    def test_submit_assets_requires_confirmation_before_paid_request(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        tmp, settings_patch, secrets_patch, env_patch = self._settings_context(api_key="tsk_test_secret_123456")
        with tmp, settings_patch, secrets_patch, env_patch, patch("tools.generative_tools._tripo_submit_task") as submit:
            result = skill_generate_playable_slice(
                "third-person dungeon demo with a slime",
                mode="submit_assets",
                confirm_spend=False,
            )

        _assert_structured(self, result, "spend_confirmation_required")
        self.assertFalse(result["success"])
        submit.assert_not_called()

    def test_submit_assets_sends_four_tripo_tasks_after_confirmation(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        submitted = []

        def fake_submit(payload):
            submitted.append(payload)
            return {
                "task_id": f"task-{len(submitted)}",
                "trace_id": f"trace-{len(submitted)}",
                "response": {"code": 0, "data": {"task_id": f"task-{len(submitted)}"}},
            }

        tmp, settings_patch, secrets_patch, env_patch = self._settings_context(api_key="tsk_test_secret_123456")
        with tmp, settings_patch, secrets_patch, env_patch, patch("tools.generative_tools._tripo_submit_task", side_effect=fake_submit):
            result = skill_generate_playable_slice(
                "third-person dungeon demo with a slime and a boss",
                mode="submit_assets",
                session_name="d7-demo",
                confirm_spend=True,
            )

        _assert_structured(self, result, "asset_tasks_submitted")
        self.assertTrue(result["success"])
        self.assertEqual(len(submitted), 4)
        self.assertEqual([payload["type"] for payload in submitted], ["text_to_model"] * 4)
        self.assertTrue(all(payload["smart_low_poly"] is True for payload in submitted))
        self.assertTrue(result["outputs"]["credit_guard"]["reserved"])
        self.assertEqual(len(result["outputs"]["task_submissions"]), 4)

    def test_orchestrate_mode_returns_import_gameplay_and_pie_package(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        task_submissions = json.dumps([
            {"asset_role": "hero", "asset_name": "Demo_Hero", "task_id": "task-hero"},
            {"asset_role": "enemy", "asset_name": "Demo_Enemy", "task_id": "task-enemy"},
        ])
        imported_assets = json.dumps([
            {"asset_role": "hero", "asset_path": "/Game/Generated/PlayableSlice/Assets/Demo_Hero"},
        ])

        result = skill_generate_playable_slice(
            "third-person dungeon demo with a slime and a boss",
            mode="orchestrate",
            task_submissions_json=task_submissions,
            imported_assets_json=imported_assets,
        )

        _assert_structured(self, result, "orchestration_ready")
        self.assertTrue(result["success"])
        orchestration = result["outputs"]["orchestration"]
        self.assertEqual(orchestration["schema"], "unreal_mcp_playable_slice_orchestration.v1")
        phase_names = [phase["phase"] for phase in orchestration["phases"]]
        self.assertIn("wait_and_import_generated_assets", phase_names)
        self.assertIn("assemble_playable_loop", phase_names)
        self.assertIn("verify_and_report", phase_names)
        serialized = json.dumps(orchestration)
        for token in (
            "gen_tripo_wait_for_task",
            "gen_tripo_import_to_project",
            "compile_blueprint_and_report",
            "pie_launch_session",
            "pie_capture_log",
            "viewport_capture_screenshot",
            "skill_package_vertical_slice_report",
        ):
            with self.subTest(token=token):
                self.assertIn(token, serialized)

    def test_orchestrate_mode_rejects_invalid_json_inputs(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        result = skill_generate_playable_slice(
            "third-person dungeon demo with a slime",
            mode="orchestrate",
            task_submissions_json="{not-json",
        )

        _assert_structured(self, result, "orchestration_input_invalid")
        self.assertFalse(result["success"])
        self.assertIn("task_submissions_json must be JSON", result["errors"][0])

    def test_registered_tool_returns_json(self):
        from skills.playable_slice.skill import register_playable_slice_skill

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        payload = json.loads(asyncio.run(mcp.tools["skill_generate_playable_slice"](
            None,
            "third-person dungeon demo with a skeleton",
        )))

        _assert_structured(self, payload, "plan_ready")
        self.assertTrue(payload["success"])

    def test_d7_static_registration_kb_and_schema(self):
        server_text = (SERVER_ROOT / "unreal_mcp_server.py").read_text(encoding="utf-8")
        inventory_text = (SERVER_ROOT / "tool_inventory_categories.json").read_text(encoding="utf-8")
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        schema = json.loads((REPO_ROOT / "knowledge_base" / "v5" / "PLAYABLE_SLICE_SCHEMA.json").read_text(encoding="utf-8"))

        self.assertIn("register_playable_slice_skill", server_text)
        self.assertIn('"skills.playable_slice.skill"', inventory_text)
        self.assertIn("skill_generate_playable_slice", skill_text)
        self.assertIn("D7 Playable Slice Skill", kb_text)
        self.assertIn("D.7 - Playable slice skill", changelog_text)
        self.assertEqual(schema["title"], "Unreal MCP Playable Slice Plan")
        self.assertEqual(schema["properties"]["assets"]["items"]["properties"]["smart_low_poly"]["const"], True)


if __name__ == "__main__":
    unittest.main()
