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

    def test_preflight_mode_reports_live_readiness_without_brief_or_spend(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        fake_preflight = {
            "schema": "unreal_mcp_playable_slice_live_preflight.v1",
            "ready_for_live_spend": False,
            "network_required": False,
            "spend_required": False,
            "next_actions": ["tripo_api_key: TRIPO_API_KEY env var or Saved/MCPChat/secrets.json"],
            "gates": [
                {"id": "tripo_api_key", "status": "missing"},
                {"id": "packaged_plugin", "status": "ready"},
            ],
        }
        with patch("skills.playable_slice.skill._run_live_preflight", return_value=fake_preflight) as preflight:
            result = skill_generate_playable_slice("", mode="preflight", session_name="demo-preflight")

        _assert_structured(self, result, "preflight_missing_gates")
        self.assertFalse(result["success"])
        self.assertFalse(result["outputs"]["network_required"])
        self.assertFalse(result["outputs"]["unreal_mutation_required"])
        self.assertFalse(result["outputs"]["spend_required"])
        self.assertEqual(result["outputs"]["preflight"]["schema"], "unreal_mcp_playable_slice_live_preflight.v1")
        self.assertIn("preflight", result["outputs"]["execution_modes"])
        self.assertIn("tripo_api_key", result["warnings"][0])
        preflight.assert_called_once_with(session_name="demo-preflight", estimated_credits=120)

    def test_plan_mode_uses_ui_intent_fields(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        result = skill_generate_playable_slice(
            "make a gate arena",
            asset_roles="power core pickup, exit gate, arena marker prop",
            gameplay_loop="collect the power core, open the exit gate, show completion HUD",
            acceptance_criteria="pickup opens gate and HUD confirms completion",
            required_evidence="compile report, PIE log, viewport screenshot",
        )

        _assert_structured(self, result, "plan_ready")
        plan = result["outputs"]["plan"]
        self.assertEqual(plan["requested_asset_roles"], ["power core pickup", "exit gate", "arena marker prop"])
        self.assertEqual(plan["gameplay"]["requested_loop"], "collect the power core, open the exit gate, show completion HUD")
        self.assertEqual(plan["gameplay"]["level_goal"], "collect the power core, open the exit gate, show completion HUD")
        self.assertEqual(plan["validation"]["acceptance_criteria"], "pickup opens gate and HUD confirms completion")
        self.assertEqual(plan["validation"]["required_runtime_evidence"], ["compile report", "PIE log", "viewport screenshot"])
        prompts = " ".join(asset["prompt"] for asset in plan["assets"])
        self.assertIn("power core pickup", prompts)
        self.assertIn("exit gate", prompts)

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
        report_phase = next(phase for phase in orchestration["phases"] if phase["phase"] == "verify_and_report")
        context_phase = next(phase for phase in orchestration["phases"] if phase["phase"] == "context")
        journal_start = next(call for call in context_phase["tool_calls"] if call["tool"] == "execution_journal_start")
        for key in ("title", "goal", "project_name", "tags"):
            with self.subTest(journal_start_arg=key):
                self.assertIn(key, journal_start["args"])
        journal_finish = next(call for call in report_phase["tool_calls"] if call["tool"] == "execution_journal_finish")
        for key in ("journal_path", "status", "summary", "artifacts", "verification"):
            with self.subTest(journal_finish_arg=key):
                self.assertIn(key, journal_finish["args"])
        self.assertNotIn("final_artifacts_json", journal_finish["args"])
        self.assertNotIn("verification_json", journal_finish["args"])
        report_call = next(call for call in report_phase["tool_calls"] if call["tool"] == "skill_package_vertical_slice_report")
        report_args = report_call["args"]
        for key in (
            "title",
            "summary",
            "journal_path",
            "report_dir",
            "project_name",
            "artifacts",
            "verification",
            "include_journal_entries",
            "max_entries",
        ):
            with self.subTest(report_arg=key):
                self.assertIn(key, report_args)
        self.assertIn("brief", report_args["verification"])
        self.assertIn("plan_schema", report_args["verification"])
        self.assertNotIn("changed_assets", report_args)
        readiness = orchestration["evidence_readiness"]
        self.assertEqual(readiness["schema"], "unreal_mcp_playable_slice_evidence_readiness.v1")
        self.assertFalse(readiness["live_playable_slice_proven"])
        gate_status = {gate["id"]: gate["status"] for gate in readiness["gates"]}
        self.assertEqual(gate_status["tripo_asset_tasks"], "partial")
        self.assertEqual(gate_status["imported_generated_assets"], "partial")
        self.assertEqual(gate_status["compile_reports_clean"], "missing")
        self.assertIn("compile_reports_clean", json.dumps(readiness["next_proof_steps"]))

    def test_orchestrate_mode_marks_live_proof_only_when_all_evidence_gates_pass(self):
        from skills.playable_slice.skill import skill_generate_playable_slice

        plan_result = skill_generate_playable_slice("third-person dungeon demo with a slime")
        plan = plan_result["outputs"]["plan"]
        task_submissions = [
            {"asset_role": asset["role"], "asset_name": asset["name"], "task_id": f"task-{index}"}
            for index, asset in enumerate(plan["assets"], start=1)
        ]
        imported_assets = [
            {"asset_role": asset["role"], "asset_name": asset["name"], "asset_path": f"{asset['content_path']}/{asset['name']}"}
            for asset in plan["assets"]
        ]
        execution_evidence = {
            "credit_guard": {"approved": True, "reserved": True},
            "gameplay_assets": {
                "player_blueprint": plan["gameplay"]["player_blueprint"],
                "enemy_blueprint": plan["gameplay"]["enemy_blueprint"],
                "hud_widget": plan["gameplay"]["hud_widget"],
                "level_or_map": f"{plan['content_path']}/Level/L_PlayableSlice",
            },
            "compile_reports": [{"blueprint": plan["gameplay"]["player_blueprint"], "success": True}],
            "compile_clean": True,
            "pie_log_path": "Saved/MCPChat/Evidence/pie.log",
            "pie_duration_s": 60,
            "viewport_screenshot_path": "Saved/MCPChat/Evidence/playable_slice.png",
            "vertical_slice_report_path": "knowledge_base/Reports/playable_slice.md",
        }

        result = skill_generate_playable_slice(
            plan["brief"],
            mode="orchestrate",
            task_submissions_json=json.dumps(task_submissions),
            imported_assets_json=json.dumps(imported_assets),
            execution_evidence_json=json.dumps(execution_evidence),
        )

        _assert_structured(self, result, "orchestration_ready")
        readiness = result["outputs"]["orchestration"]["evidence_readiness"]
        self.assertTrue(readiness["live_playable_slice_proven"])
        self.assertEqual(readiness["next_proof_steps"], [])
        self.assertTrue(all(gate["status"] == "proven" for gate in readiness["gates"]))

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

        result = skill_generate_playable_slice(
            "third-person dungeon demo with a slime",
            mode="orchestrate",
            execution_evidence_json="[]",
        )

        _assert_structured(self, result, "orchestration_input_invalid")
        self.assertFalse(result["success"])
        self.assertIn("execution_evidence_json must be a JSON object", result["errors"][0])

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
        self.assertIn("execution_evidence_json", skill_text)
        self.assertIn("_run_live_preflight", skill_text)
        self.assertIn('"preflight"', skill_text)
        self.assertIn("evidence_readiness", skill_text)
        self.assertIn("D7 Playable Slice Skill", kb_text)
        self.assertIn("evidence readiness", kb_text)
        self.assertIn("Live Preflight", kb_text)
        self.assertIn("D.7 - Playable slice skill", changelog_text)
        self.assertEqual(schema["title"], "Unreal MCP Playable Slice Plan")
        self.assertIn("requested_asset_roles", schema["required"])
        self.assertIn("description", schema["properties"]["assets"]["items"]["required"])
        self.assertIn("requested_loop", schema["properties"]["gameplay"]["required"])
        self.assertIn("acceptance_criteria", schema["properties"]["validation"]["required"])
        self.assertEqual(schema["properties"]["assets"]["items"]["properties"]["smart_low_poly"]["const"], True)


if __name__ == "__main__":
    unittest.main()
