"""Offline smoke coverage for Workstream D.2 generative config/auth."""

from __future__ import annotations

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
    testcase.assertEqual(payload["meta"]["tool"], stage)


class TestD2GenerativeConfigAuth(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.generative_tools import register_generative_tools

        self.mcp = _MockMCP()
        register_generative_tools(self.mcp)

    def test_d2_generative_tools_register(self):
        expected = {
            "gen_get_provider_config",
            "gen_save_provider_config",
            "gen_tripo_get_wallet_balance",
            "gen_check_credit_budget",
            "gen_generate_asset_preflight",
            "gen_compile_generate_asset_evidence",
            "gen_prepare_texture_paint_session",
            "gen_capture_texture_paint_snapshot",
            "gen_record_texture_paint_stroke",
            "gen_compile_texture_paint_image_map",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    async def test_save_and_read_provider_config_without_leaking_secret(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"TRIPO_API_KEY": ""}):
            settings_path = Path(tmp) / "Saved" / "MCPChat" / "generative_settings.json"
            secrets_path = Path(tmp) / "Saved" / "MCPChat" / "secrets.json"
            with patch.object(generative_tools, "_SETTINGS_PATH", settings_path), patch.object(generative_tools, "_SECRETS_PATH", secrets_path):
                saved = json.loads(await self.mcp.tools["gen_save_provider_config"](
                    ctx=None,
                    tripo_api_key="sk_test_secret_123456",
                    store_api_key=True,
                    clear_stored_api_key=False,
                    default_model_version="tripo-default",
                    default_texture_quality="high",
                    output_folder="/Game/Generated/Enemies",
                    session_credit_budget=750,
                ))

                _assert_structured(self, saved, "gen_save_provider_config")
                self.assertTrue(saved["success"])
                self.assertTrue(settings_path.exists())
                self.assertTrue(secrets_path.exists())
                self.assertNotIn("sk_test_secret_123456", json.dumps(saved))

                loaded = json.loads(await self.mcp.tools["gen_get_provider_config"](
                    ctx=None,
                    include_paths=True,
                ))

                _assert_structured(self, loaded, "gen_get_provider_config")
                self.assertTrue(loaded["outputs"]["api_key_configured"])
                self.assertEqual(loaded["outputs"]["api_key_source"], "Saved/MCPChat/secrets.json")
                self.assertEqual(loaded["outputs"]["default_texture_quality"], "high")
                self.assertEqual(loaded["outputs"]["output_folder"], "/Game/Generated/Enemies")
                self.assertEqual(loaded["outputs"]["session_credit_budget"], 750)
                self.assertNotIn("sk_test_secret_123456", json.dumps(loaded))

    async def test_env_key_takes_precedence_over_local_secret(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"TRIPO_API_KEY": "env_secret_abcdef"}):
            settings_path = Path(tmp) / "Saved" / "MCPChat" / "generative_settings.json"
            secrets_path = Path(tmp) / "Saved" / "MCPChat" / "secrets.json"
            secrets_path.parent.mkdir(parents=True, exist_ok=True)
            secrets_path.write_text(json.dumps({"TRIPO_API_KEY": "file_secret_abcdef"}), encoding="utf-8")
            with patch.object(generative_tools, "_SETTINGS_PATH", settings_path), patch.object(generative_tools, "_SECRETS_PATH", secrets_path):
                loaded = json.loads(await self.mcp.tools["gen_get_provider_config"](
                    ctx=None,
                    include_paths=False,
                ))

        _assert_structured(self, loaded, "gen_get_provider_config")
        self.assertTrue(loaded["outputs"]["api_key_configured"])
        self.assertEqual(loaded["outputs"]["api_key_source"], "env:TRIPO_API_KEY")
        self.assertNotIn("settings_path", loaded["outputs"])
        self.assertNotIn("credit_reconciliation_ledger_path", loaded["outputs"])
        self.assertNotIn("env_secret_abcdef", json.dumps(loaded))

    async def test_credit_budget_requires_confirmation_and_rejects_overage(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "Saved" / "MCPChat" / "generative_settings.json"
            secrets_path = Path(tmp) / "Saved" / "MCPChat" / "secrets.json"
            with patch.object(generative_tools, "_SETTINGS_PATH", settings_path), patch.object(generative_tools, "_SECRETS_PATH", secrets_path):
                await self.mcp.tools["gen_save_provider_config"](
                    ctx=None,
                    session_credit_budget=100,
                    default_model_version="tripo-default",
                    default_texture_quality="standard",
                    output_folder="/Game/Generated",
                )

                needs_confirm = json.loads(await self.mcp.tools["gen_check_credit_budget"](
                    ctx=None,
                    estimated_credits=60,
                    session_name="demo",
                    operation="text_to_model",
                    confirm_spend=False,
                ))
                approved = json.loads(await self.mcp.tools["gen_check_credit_budget"](
                    ctx=None,
                    estimated_credits=60,
                    session_name="demo",
                    operation="text_to_model",
                    confirm_spend=True,
                    reserve_credits=True,
                ))
                overage = json.loads(await self.mcp.tools["gen_check_credit_budget"](
                    ctx=None,
                    estimated_credits=120,
                    session_name="demo",
                    operation="text_to_model",
                    confirm_spend=True,
                ))

        _assert_structured(self, needs_confirm, "gen_check_credit_budget")
        self.assertFalse(needs_confirm["success"])
        self.assertTrue(needs_confirm["outputs"]["confirm_required"])
        self.assertTrue(approved["success"])
        self.assertTrue(approved["outputs"]["approved"])
        self.assertTrue(approved["outputs"]["reserved"])
        self.assertEqual(approved["outputs"]["used_after"], 60)
        self.assertEqual(approved["outputs"]["remaining_after"], 40)
        self.assertFalse(overage["success"])
        self.assertFalse(overage["outputs"]["within_budget"])

    async def test_generate_asset_preflight_reports_no_spend_readiness_schema(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"TRIPO_API_KEY": ""}):
            settings_path = Path(tmp) / "Saved" / "MCPChat" / "generative_settings.json"
            secrets_path = Path(tmp) / "Saved" / "MCPChat" / "secrets.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            settings_path.write_text(json.dumps({
                "session_credit_budget": 100,
                "credit_usage_by_session": {"asset-session": 20},
                "output_folder": "/Game/Generated",
            }), encoding="utf-8")
            secrets_path.write_text(json.dumps({"TRIPO_API_KEY": "tsk_test_secret_123456"}), encoding="utf-8")
            with (
                patch.object(generative_tools, "_SETTINGS_PATH", settings_path),
                patch.object(generative_tools, "_SECRETS_PATH", secrets_path),
                patch.object(generative_tools, "_find_runuat", return_value="C:\\UE\\RunUAT.bat"),
                patch.object(generative_tools, "_latest_plugin_package", return_value={
                    "found": True,
                    "path": "C:\\uebuild\\UnrealMCPBuild_test",
                    "has_descriptor": True,
                    "has_win64_binaries": True,
                }),
                patch.object(generative_tools, "_check_bridge_reachable", return_value={"reachable": True, "host": "127.0.0.1", "port": 55557}),
            ):
                payload = json.loads(await self.mcp.tools["gen_generate_asset_preflight"](
                    ctx=None,
                    mode="multiview_to_model",
                    session_name="asset-session",
                    estimated_credits=60,
                    bridge_timeout_s=0.01,
                ))

        _assert_structured(self, payload, "gen_generate_asset_preflight")
        self.assertTrue(payload["success"])
        preflight = payload["outputs"]["preflight"]
        self.assertEqual(preflight["schema"], "unreal_mcp_generate_asset_live_preflight.v1")
        self.assertFalse(preflight["network_required"])
        self.assertFalse(preflight["spend_required"])
        self.assertEqual(preflight["settings"]["session_credits_remaining"], 80)
        self.assertTrue(preflight["workspace"]["smart_low_poly_default"])
        self.assertIn("gen_tripo_multiview_to_model", preflight["workspace"]["paid_tools"].values())
        self.assertEqual(preflight["workspace"]["wallet_tool"], "gen_tripo_get_wallet_balance")
        self.assertEqual(preflight["workspace"]["proof_tool"], "gen_compile_generate_asset_evidence")
        self.assertTrue(all(gate["status"] == "ready" for gate in preflight["gates"]))
        self.assertIn("smart_mesh_policy", {gate["id"] for gate in preflight["gates"]})

    async def test_prepare_texture_paint_session_records_magic_brush_plan_without_spend(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp:
            session_path = Path(tmp) / "Saved" / "MCPChat" / "texture_paint_sessions.json"
            with patch.object(generative_tools, "_TEXTURE_PAINT_SESSIONS_PATH", session_path):
                payload = json.loads(await self.mcp.tools["gen_prepare_texture_paint_session"](
                    ctx=None,
                    model_task_id="model-task-123",
                    texture_prompt="weathered copper, worn bright edges",
                    texture_reference_image="https://example.test/reference.png",
                    viewport_view="front_three_quarter",
                    camera_matrix=[1.0, 0.0, 0.0, 1.0],
                    brush_size=0.04,
                    brush_strength=0.25,
                    brush_hardness=0.35,
                    creativity_strength=0.7,
                    paint_mode="image",
                    blend_mode="soft_overlay",
                    paint_notes="blend across shoulder seams",
                    save_name="MI_CopperKnight_Edit",
                    tripo_project_id="project-456",
                ))
                self.assertTrue(session_path.exists())
                saved = json.loads(session_path.read_text(encoding="utf-8"))

        _assert_structured(self, payload, "gen_prepare_texture_paint_session")
        self.assertTrue(payload["success"])
        self.assertFalse(payload["outputs"]["spend_required"])
        session = payload["outputs"]["session"]
        self.assertEqual(session["studio_tool_name"], "Magic Brush")
        self.assertEqual(session["workspace_route"], "https://studio.tripo3d.ai/workspace/texture-edit")
        self.assertEqual(session["brush"]["strength"], 0.25)
        self.assertIn("retexture_generate", json.dumps(session["observed_studio_api_contract"]))
        self.assertIn("apply_retexture", json.dumps(session["observed_studio_api_contract"]))
        self.assertEqual(session["mcp_tool_sequence"][0]["tool"], "gen_tripo_texture_model")
        self.assertIn("gen_capture_texture_paint_snapshot", [step["tool"] for step in session["mcp_tool_sequence"]])
        self.assertIn("gen_record_texture_paint_stroke", [step["tool"] for step in session["mcp_tool_sequence"]])
        self.assertIn("gen_compile_texture_paint_image_map", [step["tool"] for step in session["mcp_tool_sequence"]])
        self.assertEqual(saved["sessions"][0]["model_task_id"], "model-task-123")

    async def test_texture_paint_snapshot_captures_and_uploads_without_spend(self):
        import tools.generative_tools as generative_tools

        def fake_send(command, params):
            Path(params["filepath"]).parent.mkdir(parents=True, exist_ok=True)
            Path(params["filepath"]).write_bytes(b"\x89PNG\r\n\x1a\n")
            return {"success": True, "command": command, "filepath": params["filepath"]}

        with tempfile.TemporaryDirectory() as tmp:
            session_path = Path(tmp) / "Saved" / "MCPChat" / "texture_paint_sessions.json"
            snapshot_folder = Path(tmp) / "snapshots"
            with (
                patch.object(generative_tools, "_TEXTURE_PAINT_SESSIONS_PATH", session_path),
                patch("tools.generative_tools._send", side_effect=fake_send),
                patch("tools.generative_tools._tripo_upload_file", return_value={"file_token": "uploaded-snapshot-token", "trace_id": "trace"}),
            ):
                prepared = json.loads(await self.mcp.tools["gen_prepare_texture_paint_session"](
                    ctx=None,
                    model_task_id="model-task-123",
                    texture_prompt="weathered copper",
                    tripo_project_id="project-456",
                ))
                session_id = prepared["outputs"]["session"]["session_id"]
                payload = json.loads(await self.mcp.tools["gen_capture_texture_paint_snapshot"](
                    ctx=None,
                    session_id=session_id,
                    viewport_view="front_three_quarter",
                    target_folder=str(snapshot_folder),
                    resolution=512,
                    upload_to_tripo=True,
                ))
                saved = json.loads(session_path.read_text(encoding="utf-8"))
                snapshot_exists = Path(payload["outputs"]["snapshot"]["path"]).exists()

        _assert_structured(self, payload, "gen_capture_texture_paint_snapshot")
        self.assertTrue(payload["success"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertTrue(payload["outputs"]["network_required"])
        self.assertTrue(payload["outputs"]["attached_to_session"])
        self.assertEqual(payload["outputs"]["render_image"]["file_token"], "uploaded-snapshot-token")
        self.assertTrue(snapshot_exists)
        self.assertEqual(saved["sessions"][0]["latest_render_image"]["file_token"], "uploaded-snapshot-token")
        self.assertEqual(saved["sessions"][0]["viewport_snapshots"][0]["viewport_view"], "front_three_quarter")

    async def test_texture_paint_strokes_compile_apply_ready_image_map_without_spend(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp:
            session_path = Path(tmp) / "Saved" / "MCPChat" / "texture_paint_sessions.json"
            with patch.object(generative_tools, "_TEXTURE_PAINT_SESSIONS_PATH", session_path):
                prepared = json.loads(await self.mcp.tools["gen_prepare_texture_paint_session"](
                    ctx=None,
                    model_task_id="model-task-123",
                    texture_prompt="weathered copper",
                    tripo_project_id="project-456",
                ))
                session_id = prepared["outputs"]["session"]["session_id"]
                stroke = json.loads(await self.mcp.tools["gen_record_texture_paint_stroke"](
                    ctx=None,
                    session_id=session_id,
                    part_name="Body",
                    image_bucket="paint-bucket",
                    image_key="body.png",
                    viewport_view="front",
                    brush_strength=0.35,
                    blend_mode="soft_overlay",
                    paint_notes="blend across shoulder seam",
                ))
                compiled = json.loads(await self.mcp.tools["gen_compile_texture_paint_image_map"](
                    ctx=None,
                    session_id=session_id,
                ))
                saved = json.loads(session_path.read_text(encoding="utf-8"))

        _assert_structured(self, stroke, "gen_record_texture_paint_stroke")
        self.assertTrue(stroke["success"])
        self.assertFalse(stroke["outputs"]["spend_required"])
        self.assertEqual(stroke["outputs"]["image_map"][0]["image"]["bucket"], "paint-bucket")
        _assert_structured(self, compiled, "gen_compile_texture_paint_image_map")
        self.assertTrue(compiled["success"])
        self.assertFalse(compiled["outputs"]["spend_required"])
        self.assertEqual(compiled["outputs"]["project_id"], "project-456")
        self.assertEqual(compiled["outputs"]["apply_tool"], "gen_tripo_magic_brush_apply")
        self.assertEqual(compiled["outputs"]["apply_args"]["image_map"][0]["part_name"], "Body")
        self.assertEqual(saved["sessions"][0]["image_map"][0]["image"]["key"], "body.png")

    def test_d2_static_chat_panel_and_kb_wiring(self):
        panel_header = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Public" / "MCPChatPanel.h").read_text(encoding="utf-8")
        panel_cpp = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        generative_text = (SERVER_ROOT / "tools" / "generative_tools.py").read_text(encoding="utf-8")

        for token in (
            "HandleToggleGenerativeSettingsClicked",
            "HandleSaveGenerativeSettingsClicked",
            "HandleConfirmGenerativeSpendClicked",
            "BuildGenerativeSettingsPanel",
            "GetGenerativeSettingsVisibility",
            "GenerativeSessionCreditBudget",
            "GenerativePendingSpendCredits",
        ):
            with self.subTest(token=token):
                self.assertIn(token, panel_header)

        for token in (
            "Generate Asset Settings",
            "TRIPO_API_KEY",
            "generative_settings.json",
            "secrets.json",
            "Confirm Spend",
            "Saved/MCPChat/secrets.json",
            "env:TRIPO_API_KEY",
            "spend_confirmed",
        ):
            with self.subTest(token=token):
                self.assertIn(token, panel_cpp)

        for token in (
            "Config And Auth",
            "Cost Guard",
        ):
            with self.subTest(token=token):
                self.assertIn(token, kb_text)

        for token in (
            "gen_get_provider_config",
            "gen_save_provider_config",
            "gen_tripo_get_wallet_balance",
            "gen_check_credit_budget",
            "gen_compile_generate_asset_evidence",
            "gen_prepare_texture_paint_session",
            "gen_capture_texture_paint_snapshot",
            "gen_record_texture_paint_stroke",
            "gen_compile_texture_paint_image_map",
        ):
            with self.subTest(token=token):
                self.assertIn(token, kb_text)
                self.assertIn(token, generative_text)

        for token in (
            "Magic Brush",
            "retexture_generate",
            "apply_retexture",
            "texture_paint_sessions.json",
        ):
            with self.subTest(token=token):
                self.assertIn(token, kb_text)
                self.assertIn(token, generative_text)

        self.assertIn("D.2 - Generative config and auth", changelog_text)
        self.assertIn("no Tripo API call is made", changelog_text)


if __name__ == "__main__":
    unittest.main()
