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
        self.assertTrue(result["outputs"]["credit_guard"]["reserved"])
        self.assertEqual(len(result["outputs"]["task_submissions"]), 4)

    def test_assemble_requires_imported_assets_without_requiring_tripo_key(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        tmp, settings_patch, secrets_patch, env_patch = self._settings_context(api_key="")
        with tmp, settings_patch, secrets_patch, env_patch, patch("tools.generative_tools._tripo_submit_task") as submit:
            result = skill_generate_playable_slice(
                "third-person dungeon demo with a slime",
                mode="assemble",
                run_pie_seconds=0,
            )

        _assert_structured(self, result, "asset_inputs_required")
        self.assertFalse(result["success"])
        self.assertIn("imported_asset_paths", result["outputs"])
        submit.assert_not_called()

    def test_assemble_with_imported_assets_runs_blueprint_ai_hud_pie_and_report_chain(self):
        import skills.playable_slice.skill as playable_slice

        commands = []

        def fake_send(command, params):
            commands.append((command, params))
            if command == "take_screenshot":
                return {"success": True, "filepath": str(Path(params["filepath"]))}
            if command in {"create_blueprint", "create_blackboard", "create_behavior_tree", "create_umg_widget_blueprint"}:
                name = params.get("name") or params.get("widget_name") or params.get("behavior_tree_name")
                return {"success": True, "command": command, "params": params, "path": f"/Game/Test/{name}"}
            return {"success": True, "command": command, "params": params}

        def fake_exec_transactional(code, transaction_name):
            return {
                "success": True,
                "stage": "ue_exec_transact",
                "message": "assembled",
                "outputs": {"placed_actor_count": 6, "transaction_name": transaction_name},
                "warnings": [],
                "errors": [],
            }

        def fake_pie(seconds):
            return {
                "success": True,
                "stage": "playable_slice_pie_smoke",
                "message": "PIE smoke passed",
                "outputs": {"requested_seconds": seconds, "entered_pie": True},
                "warnings": [],
                "errors": [],
            }

        def fake_report(plan, artifacts, verification):
            return {
                "success": True,
                "stage": "skill_package_vertical_slice_report",
                "message": "report written",
                "outputs": {"report_path": "knowledge_base/Reports/playable_slice.md", "verification_keys": sorted(verification)},
                "warnings": [],
                "errors": [],
            }

        imported_assets = [
            "/Game/Generated/PlayableSlice/Assets/SM_Hero",
            "/Game/Generated/PlayableSlice/Assets/SM_Prop1",
            "/Game/Generated/PlayableSlice/Assets/SM_Prop2",
            "/Game/Generated/PlayableSlice/Assets/SM_Enemy",
        ]
        with tempfile.TemporaryDirectory() as tmp, \
            patch.object(playable_slice, "_REPO_ROOT", Path(tmp)), \
            patch.object(playable_slice, "_send", side_effect=fake_send), \
            patch.object(playable_slice, "_exec_transactional", side_effect=fake_exec_transactional), \
            patch.object(playable_slice, "_run_pie_smoke", side_effect=fake_pie), \
            patch.object(playable_slice, "_package_slice_report", side_effect=fake_report):
            result = playable_slice.skill_generate_playable_slice(
                "third-person dungeon demo with a slime and boss",
                mode="assemble",
                imported_asset_paths=imported_assets,
                run_pie_seconds=0,
            )

        _assert_structured(self, result, "assembled")
        self.assertTrue(result["success"])
        command_names = [name for name, _params in commands]
        for expected in (
            "create_blueprint",
            "create_blackboard",
            "create_behavior_tree",
            "build_behavior_tree",
            "create_umg_widget_blueprint",
            "add_component_to_blueprint",
            "set_static_mesh_properties",
            "compile_blueprint",
            "setup_navmesh",
            "take_screenshot",
        ):
            self.assertIn(expected, command_names)
        mesh_assignments = [
            params for name, params in commands
            if name == "set_static_mesh_properties"
        ]
        self.assertEqual(mesh_assignments[0]["static_mesh"], imported_assets[0])
        self.assertEqual(mesh_assignments[1]["static_mesh"], imported_assets[3])
        hud_text = [params for name, params in commands if name == "add_text_block_to_widget"][0]
        self.assertEqual(hud_text["blueprint_name"], result["outputs"]["verification"]["hud_widget"].rsplit("/", 1)[-1])
        self.assertEqual(hud_text["widget_name"], "ObjectiveText")
        self.assertIn("skill_package_vertical_slice_report", result["outputs"]["report"]["stage"])
        self.assertIn("pie_smoke", result["outputs"]["verification"])
        self.assertIn("generated_mesh_assignments", result["outputs"]["verification"])

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
        self.assertIn('"assemble"', skill_text)
        self.assertIn("task_ids", skill_text)
        self.assertIn("imported_asset_paths", skill_text)
        self.assertIn("D7 Playable Slice Skill", kb_text)
        self.assertIn("D.7 - Playable slice skill", changelog_text)
        self.assertEqual(schema["title"], "Unreal MCP Playable Slice Plan")


if __name__ == "__main__":
    unittest.main()
