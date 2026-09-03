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
            "gen_tripo_get_credit_balance",
            "gen_uthana_get_account",
            "gen_uthana_create_character",
            "gen_uthana_get_character",
            "gen_uthana_create_locomotion",
            "gen_uthana_text_to_motion",
            "gen_uthana_get_motion",
            "gen_uthana_check_download_allowed",
            "gen_uthana_download_motion",
            "gen_uthana_import_animation_to_project",
            "gen_save_provider_config",
            "gen_check_credit_budget",
            "gen_prepare_texture_paint_session",
            "gen_capture_texture_paint_snapshot",
            "gen_record_texture_paint_pass",
            "gen_compile_texture_paint_evidence",
            "gen_compile_generated_animation_evidence",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    async def test_save_and_read_provider_config_without_leaking_secret(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"TRIPO_API_KEY": "", "UTHANA_API_KEY": ""}):
            settings_path = Path(tmp) / "Saved" / "MCPChat" / "generative_settings.json"
            secrets_path = Path(tmp) / "Saved" / "MCPChat" / "secrets.json"
            with patch.object(generative_tools, "_SETTINGS_PATH", settings_path), patch.object(generative_tools, "_SECRETS_PATH", secrets_path):
                saved = json.loads(await self.mcp.tools["gen_save_provider_config"](
                    ctx=None,
                    tripo_api_key="sk_test_secret_123456",
                    uthana_api_key="uthana_test_secret_abcdef",
                    store_api_key=True,
                    store_uthana_api_key=True,
                    clear_stored_api_key=False,
                    clear_stored_uthana_api_key=False,
                    default_model_version="tripo-default",
                    default_texture_quality="high",
                    output_folder="/Game/Generated/Enemies",
                    animation_output_folder="/Game/Generated/Animations",
                    uthana_default_character_id="uthana-default-character",
                    session_credit_budget=750,
                ))

                _assert_structured(self, saved, "gen_save_provider_config")
                self.assertTrue(saved["success"])
                self.assertTrue(settings_path.exists())
                self.assertTrue(secrets_path.exists())
                self.assertNotIn("sk_test_secret_123456", json.dumps(saved))
                self.assertNotIn("uthana_test_secret_abcdef", json.dumps(saved))

                loaded = json.loads(await self.mcp.tools["gen_get_provider_config"](
                    ctx=None,
                    include_paths=True,
                ))

                _assert_structured(self, loaded, "gen_get_provider_config")
                self.assertTrue(loaded["outputs"]["api_key_configured"])
                self.assertEqual(loaded["outputs"]["api_key_source"], "Saved/MCPChat/secrets.json")
                self.assertTrue(loaded["outputs"]["uthana_api_key_configured"])
                self.assertEqual(loaded["outputs"]["uthana_api_key_source"], "Saved/MCPChat/secrets.json")
                self.assertEqual(loaded["outputs"]["default_texture_quality"], "high")
                self.assertEqual(loaded["outputs"]["output_folder"], "/Game/Generated/Enemies")
                self.assertEqual(loaded["outputs"]["animation_output_folder"], "/Game/Generated/Animations")
                self.assertEqual(loaded["outputs"]["uthana_default_character_id"], "uthana-default-character")
                self.assertEqual(loaded["outputs"]["session_credit_budget"], 750)
                self.assertNotIn("sk_test_secret_123456", json.dumps(loaded))
                self.assertNotIn("uthana_test_secret_abcdef", json.dumps(loaded))

                secret_payload = json.loads(secrets_path.read_text(encoding="utf-8"))
                self.assertEqual(secret_payload["TRIPO_API_KEY"], "sk_test_secret_123456")
                self.assertEqual(secret_payload["UTHANA_API_KEY"], "uthana_test_secret_abcdef")

                cleared = json.loads(await self.mcp.tools["gen_save_provider_config"](
                    ctx=None,
                    clear_stored_uthana_api_key=True,
                    default_model_version="tripo-default",
                    default_texture_quality="high",
                    output_folder="/Game/Generated/Enemies",
                    animation_output_folder="/Game/Generated/Animations",
                    session_credit_budget=750,
                ))

                _assert_structured(self, cleared, "gen_save_provider_config")
                cleared_secrets = json.loads(secrets_path.read_text(encoding="utf-8"))
                self.assertIn("TRIPO_API_KEY", cleared_secrets)
                self.assertNotIn("UTHANA_API_KEY", cleared_secrets)
                self.assertFalse(cleared["outputs"]["uthana_api_key_configured"])

    async def test_tripo_credit_balance_uses_wallet_endpoint_without_spend(self):
        def fake_balance(timeout_s=30):
            return {
                "balance": 99900,
                "frozen": 120,
                "trace_id": "trace-wallet",
                "http_status": 200,
                "response": {"code": 0, "data": {"balance": 99900, "frozen": 120}},
            }

        with patch("tools.generative_tools._tripo_get_credit_balance", side_effect=fake_balance):
            payload = json.loads(await self.mcp.tools["gen_tripo_get_credit_balance"](
                ctx=None,
                include_raw=True,
                timeout_s=30,
            ))

        _assert_structured(self, payload, "gen_tripo_get_credit_balance")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["api_wallet"]["balance"], 99900)
        self.assertEqual(payload["outputs"]["api_wallet"]["frozen"], 120)
        self.assertTrue(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertIn("raw_response", payload["outputs"])
        self.assertIn("separate balances", " ".join(payload["warnings"]))

    async def test_env_key_takes_precedence_over_local_secret(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"TRIPO_API_KEY": "env_secret_abcdef", "UTHANA_API_KEY": "uthana_env_secret_abcdef"}):
            settings_path = Path(tmp) / "Saved" / "MCPChat" / "generative_settings.json"
            secrets_path = Path(tmp) / "Saved" / "MCPChat" / "secrets.json"
            secrets_path.parent.mkdir(parents=True, exist_ok=True)
            secrets_path.write_text(json.dumps({"TRIPO_API_KEY": "file_secret_abcdef", "UTHANA_API_KEY": "uthana_file_secret_abcdef"}), encoding="utf-8")
            with patch.object(generative_tools, "_SETTINGS_PATH", settings_path), patch.object(generative_tools, "_SECRETS_PATH", secrets_path):
                loaded = json.loads(await self.mcp.tools["gen_get_provider_config"](
                    ctx=None,
                    include_paths=False,
                ))

        _assert_structured(self, loaded, "gen_get_provider_config")
        self.assertTrue(loaded["outputs"]["api_key_configured"])
        self.assertEqual(loaded["outputs"]["api_key_source"], "env:TRIPO_API_KEY")
        self.assertTrue(loaded["outputs"]["uthana_api_key_configured"])
        self.assertEqual(loaded["outputs"]["uthana_api_key_source"], "env:UTHANA_API_KEY")
        self.assertNotIn("settings_path", loaded["outputs"])
        self.assertNotIn("env_secret_abcdef", json.dumps(loaded))
        self.assertNotIn("uthana_env_secret_abcdef", json.dumps(loaded))

    async def test_uthana_account_reports_org_allowance_without_spend(self):
        def fake_account(timeout_s=30):
            return {
                "user": {"id": "user-1", "name": "Dev", "email": "dev@example.test"},
                "org": {
                    "id": "org-1",
                    "name": "Studio",
                    "motion_download_secs_per_month": 1200,
                    "motion_download_secs_per_month_remaining": 900,
                    "characters_allowed_remaining": 4,
                },
                "http_status": 200,
            }

        with patch("tools.generative_tools._uthana_get_account", side_effect=fake_account):
            payload = json.loads(await self.mcp.tools["gen_uthana_get_account"](
                ctx=None,
                include_user=False,
                timeout_s=30,
            ))

        _assert_structured(self, payload, "gen_uthana_get_account")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["provider"], "uthana")
        self.assertEqual(payload["outputs"]["motion_download_secs_per_month_remaining"], 900)
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertTrue(payload["outputs"]["network_required"])
        self.assertNotIn("dev@example.test", json.dumps(payload))

    async def test_uthana_create_character_upload_requires_confirmation_then_returns_character_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            character_file = Path(tmp) / "tripo_hero.fbx"
            character_file.write_bytes(b"fbx")
            needs_confirm = json.loads(await self.mcp.tools["gen_uthana_create_character"](
                ctx=None,
                local_file=str(character_file),
                character_name="TripoHero",
                confirm_usage=False,
            ))

            _assert_structured(self, needs_confirm, "gen_uthana_create_character")
            self.assertFalse(needs_confirm["success"])
            self.assertTrue(needs_confirm["outputs"]["usage_guard"]["confirm_required"])
            self.assertIn("confirm_usage=True", " ".join(needs_confirm["warnings"]))

            def fake_create_character(file_path, name, auto_rig, auto_rig_front_facing, include_fingers, rerig_target="", timeout_s=180):
                return {
                    "character_id": "character-tripo",
                    "character_name": name,
                    "character": {"id": "character-tripo", "name": name, "assets": [{"id": "asset-1", "filename": "tripo_hero.fbx"}]},
                    "auto_rig_confidence": 0.91,
                    "provider_message": "rigged",
                    "http_status": 200,
                }

            with patch("tools.generative_tools._uthana_create_character", side_effect=fake_create_character):
                created = json.loads(await self.mcp.tools["gen_uthana_create_character"](
                    ctx=None,
                    local_file=str(character_file),
                    character_name="TripoHero",
                    auto_rig=True,
                    auto_rig_front_facing=True,
                    include_fingers=True,
                    set_as_default=False,
                    confirm_usage=True,
                ))

        _assert_structured(self, created, "gen_uthana_create_character")
        self.assertTrue(created["success"])
        self.assertEqual(created["outputs"]["character_id"], "character-tripo")
        self.assertEqual(created["outputs"]["auto_rig_confidence"], 0.91)
        self.assertIn("gen_uthana_create_locomotion", created["outputs"]["motion_tools"])
        self.assertTrue(created["outputs"]["usage_guard"]["approved"])
        self.assertTrue(created["outputs"]["spend_required"])

    async def test_uthana_get_character_reports_metadata_without_spend(self):
        def fake_character(character_id, timeout_s=30):
            return {
                "character": {"id": character_id, "name": "TripoHero", "assets": []},
                "http_status": 200,
            }

        with patch("tools.generative_tools._uthana_get_character", side_effect=fake_character):
            payload = json.loads(await self.mcp.tools["gen_uthana_get_character"](
                ctx=None,
                character_id="character-tripo",
                timeout_s=30,
            ))

        _assert_structured(self, payload, "gen_uthana_get_character")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["character"]["id"], "character-tripo")
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertTrue(payload["outputs"]["network_required"])

    async def test_uthana_text_to_motion_requires_confirmation_then_returns_motion_id(self):
        needs_confirm = json.loads(await self.mcp.tools["gen_uthana_text_to_motion"](
            ctx=None,
            prompt="loopable cautious guard patrol walk",
            confirm_usage=False,
            estimated_seconds=6,
        ))

        _assert_structured(self, needs_confirm, "gen_uthana_text_to_motion")
        self.assertFalse(needs_confirm["success"])
        self.assertTrue(needs_confirm["outputs"]["usage_guard"]["confirm_required"])
        self.assertIn("confirm_usage=True", " ".join(needs_confirm["warnings"]))

        calls = []

        def fake_create(prompt, character_id, foot_ik, timeout_s=60):
            calls.append({"prompt": prompt, "character_id": character_id, "foot_ik": foot_ik})
            return {
                "motion_id": "motion-123",
                "motion_name": prompt,
                "motion": {"id": "motion-123", "name": prompt, "assets": []},
                "http_status": 200,
            }

        with patch("tools.generative_tools._uthana_create_text_motion", side_effect=fake_create):
            created = json.loads(await self.mcp.tools["gen_uthana_text_to_motion"](
                ctx=None,
                prompt="loopable cautious guard patrol walk",
                character_id="character-456",
                foot_ik=True,
                confirm_usage=True,
                estimated_seconds=6,
            ))

        _assert_structured(self, created, "gen_uthana_text_to_motion")
        self.assertTrue(created["success"])
        self.assertEqual(created["outputs"]["motion_id"], "motion-123")
        self.assertEqual(created["outputs"]["character_id"], "character-456")
        self.assertEqual(calls[0]["character_id"], "character-456")
        self.assertTrue(created["outputs"]["usage_guard"]["approved"])
        self.assertTrue(created["outputs"]["spend_required"])

    async def test_uthana_create_locomotion_requires_confirmation_then_returns_motion_id(self):
        needs_confirm = json.loads(await self.mcp.tools["gen_uthana_create_locomotion"](
            ctx=None,
            character_id="character-tripo",
            travel_angle=45,
            move_speed=3.5,
            strides=4,
            confirm_usage=False,
        ))

        _assert_structured(self, needs_confirm, "gen_uthana_create_locomotion")
        self.assertFalse(needs_confirm["success"])
        self.assertTrue(needs_confirm["outputs"]["usage_guard"]["confirm_required"])

        calls = []

        def fake_locomotion(character_id, travel_angle, move_speed, strides, style_id="", timeout_s=60):
            calls.append({"character_id": character_id, "travel_angle": travel_angle, "move_speed": move_speed, "strides": strides})
            return {
                "motion_id": "motion-loco-45",
                "motion_name": "locomotion",
                "motion": {"id": "motion-loco-45", "name": "locomotion", "assets": []},
                "http_status": 200,
            }

        with patch("tools.generative_tools._uthana_create_locomotion", side_effect=fake_locomotion):
            created = json.loads(await self.mcp.tools["gen_uthana_create_locomotion"](
                ctx=None,
                character_id="character-tripo",
                travel_angle=45,
                move_speed=3.5,
                strides=4,
                confirm_usage=True,
            ))

        _assert_structured(self, created, "gen_uthana_create_locomotion")
        self.assertTrue(created["success"])
        self.assertEqual(created["outputs"]["motion_id"], "motion-loco-45")
        self.assertEqual(calls[0]["character_id"], "character-tripo")
        self.assertEqual(calls[0]["travel_angle"], 45.0)
        self.assertTrue(created["outputs"]["usage_guard"]["approved"])

    async def test_uthana_video_to_motion_requires_confirmation_then_returns_job_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "reference.mp4"
            video.write_bytes(b"video")
            needs_confirm = json.loads(await self.mcp.tools["gen_uthana_video_to_motion"](
                ctx=None,
                video_file=str(video),
                motion_name="A_ReferenceMove",
                confirm_usage=False,
                estimated_seconds=8,
            ))

            _assert_structured(self, needs_confirm, "gen_uthana_video_to_motion")
            self.assertFalse(needs_confirm["success"])
            self.assertTrue(needs_confirm["outputs"]["usage_guard"]["confirm_required"])
            self.assertEqual(needs_confirm["outputs"]["job_poll_tool"], "gen_uthana_get_job")
            self.assertIn("confirm_usage=True", " ".join(needs_confirm["warnings"]))

            calls = []

            def fake_create(video_file, motion_name, character_id="", model="", timeout_s=180):
                calls.append({"video_file": video_file, "motion_name": motion_name, "character_id": character_id, "model": model})
                return {
                    "job_id": "job-123",
                    "job_status": "READY",
                    "job": {"id": "job-123", "status": "READY", "result": {}},
                    "http_status": 200,
                }

            with patch("tools.generative_tools._uthana_create_video_motion", side_effect=fake_create):
                created = json.loads(await self.mcp.tools["gen_uthana_video_to_motion"](
                    ctx=None,
                    video_file=str(video),
                    motion_name="A_ReferenceMove",
                    character_id="character-456",
                    confirm_usage=True,
                    estimated_seconds=8,
                ))

        _assert_structured(self, created, "gen_uthana_video_to_motion")
        self.assertTrue(created["success"])
        self.assertEqual(created["outputs"]["job_id"], "job-123")
        self.assertEqual(created["outputs"]["status_tool"], "gen_uthana_get_job")
        self.assertEqual(created["outputs"]["character_id"], "character-456")
        self.assertEqual(calls[0]["character_id"], "character-456")
        self.assertTrue(created["outputs"]["usage_guard"]["approved"])
        self.assertTrue(created["outputs"]["spend_required"])

    async def test_uthana_get_job_reports_motion_id_without_spend(self):
        def fake_job(job_id, timeout_s=30):
            return {
                "job_id": job_id,
                "job_status": "FINISHED",
                "motion_id": "motion-789",
                "job": {"id": job_id, "status": "FINISHED", "result": {"result": {"id": "motion-789"}}},
                "http_status": 200,
            }

        with patch("tools.generative_tools._uthana_get_job", side_effect=fake_job):
            payload = json.loads(await self.mcp.tools["gen_uthana_get_job"](
                ctx=None,
                job_id="job-123",
                timeout_s=30,
            ))

        _assert_structured(self, payload, "gen_uthana_get_job")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["motion_id"], "motion-789")
        self.assertTrue(payload["outputs"]["download_ready"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertTrue(payload["outputs"]["network_required"])

    async def test_uthana_download_motion_checks_quota_and_writes_no_secret(self):
        def fake_allowed(character_id, motion_id, timeout_s=30):
            return {"allowed": True, "reason": "ok", "http_status": 200}

        def fake_download(url, target_path, timeout_s=180):
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(b"fbx")
            return {"path": str(target_path), "bytes": 3, "http_status": 200}

        with tempfile.TemporaryDirectory() as tmp, patch("tools.generative_tools._uthana_check_motion_download_allowed", side_effect=fake_allowed), patch("tools.generative_tools._download_uthana_motion_file", side_effect=fake_download):
            payload = json.loads(await self.mcp.tools["gen_uthana_download_motion"](
                ctx=None,
                motion_id="motion-123",
                character_id="character-456",
                output_format="fbx",
                target_folder=tmp,
                fps=30,
                no_mesh="true",
                confirm_usage=True,
            ))

        _assert_structured(self, payload, "gen_uthana_download_motion")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["download_allowed"]["reason"], "ok")
        self.assertEqual(payload["outputs"]["downloads"][0]["format"], "fbx")
        self.assertTrue(payload["outputs"]["retargeting_applied_by_uthana"])
        self.assertNotIn("UTHANA_API_KEY", json.dumps(payload))

    async def test_uthana_import_animation_requires_bridge_ping(self):
        with tempfile.TemporaryDirectory() as tmp:
            motion_path = Path(tmp) / "motion.fbx"
            motion_path.write_bytes(b"fbx")
            with patch("tools.generative_tools._bridge_ping_ready", return_value={"ready": False, "message": "Not connected", "raw": {"success": False}}):
                payload = json.loads(await self.mcp.tools["gen_uthana_import_animation_to_project"](
                    ctx=None,
                    local_file=str(motion_path),
                    motion_id="motion-123",
                    character_id="character-456",
                    content_path="/Game/Generated/Animations",
                    require_bridge_ping=True,
                ))

        _assert_structured(self, payload, "gen_uthana_import_animation_to_project")
        self.assertFalse(payload["success"])
        self.assertIn("unreal_bridge_reachable", " ".join(payload["errors"]))
        self.assertFalse(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["spend_required"])

    async def test_compile_generated_animation_evidence_requires_runtime_and_ledger_proof(self):
        text_motion = {
            "success": True,
            "stage": "gen_uthana_text_to_motion",
            "outputs": {
                "motion_id": "motion-123",
                "character_id": "character-456",
                "motion": {"id": "motion-123", "name": "loopable cautious guard patrol walk"},
            },
        }
        allowed = {
            "success": True,
            "stage": "gen_uthana_check_download_allowed",
            "outputs": {"allowed": True, "reason": "ok"},
        }
        downloaded = {
            "success": True,
            "stage": "gen_uthana_download_motion",
            "outputs": {
                "motion_id": "motion-123",
                "character_id": "character-456",
                "download": {"path": "C:/tmp/motion-123.fbx", "format": "fbx"},
            },
        }
        imported = {
            "success": True,
            "stage": "gen_uthana_import_animation_to_project",
            "outputs": {
                "motion_id": "motion-123",
                "character_id": "character-456",
                "asset_paths": {
                    "primary_asset": "/Game/Generated/Animations/AS_GuardPatrol",
                    "animation_sequence_paths": ["/Game/Generated/Animations/AS_GuardPatrol"],
                    "skeleton_paths": ["/Game/Characters/SK_Guard_Skeleton"],
                },
            },
        }
        retarget = {
            "success": True,
            "stage": "retarget_single_animation",
            "outputs": {"retargeted_asset": "/Game/Generated/Animations/AS_GuardPatrol_Retargeted"},
        }
        animgraph = {
            "success": True,
            "stage": "set_animation_for_state",
            "outputs": {"anim_blueprint": "/Game/Characters/ABP_Guard", "state_name": "Patrol"},
        }
        pie = {
            "success": True,
            "stage": "pie_motion_probe",
            "outputs": {"screenshot_path": "C:/tmp/patrol.png", "observed_actor": "BP_Guard_1"},
        }
        ledger = {
            "success": True,
            "stage": "record_generated_asset_evidence",
            "outputs": {"ledger_path": ".mcp_artifacts/ide_companion_sessions/demo/ledger.json"},
        }

        complete = json.loads(await self.mcp.tools["gen_compile_generated_animation_evidence"](
            ctx=None,
            motion_prompt="loopable cautious guard patrol walk",
            session_name="demo",
            text_motion_result_json=json.dumps(text_motion),
            download_allowed_json=json.dumps(allowed),
            download_result_json=json.dumps(downloaded),
            import_result_json=json.dumps(imported),
            retarget_evidence_json=json.dumps(retarget),
            animgraph_evidence_json=json.dumps(animgraph),
            pie_evidence_json=json.dumps(pie),
            ledger_evidence_json=json.dumps(ledger),
            approval_note="Approved guard patrol motion after PIE inspection.",
        ))
        partial = json.loads(await self.mcp.tools["gen_compile_generated_animation_evidence"](
            ctx=None,
            motion_prompt="loopable cautious guard patrol walk",
            text_motion_result_json=json.dumps(text_motion),
            download_result_json=json.dumps(downloaded),
            import_result_json=json.dumps(imported),
        ))

        _assert_structured(self, complete, "gen_compile_generated_animation_evidence")
        evidence = complete["outputs"]["evidence"]
        self.assertEqual(evidence["schema"], "unreal_mcp_generated_animation_evidence.v1")
        self.assertTrue(evidence["proven"])
        self.assertFalse(evidence["network_required"])
        self.assertFalse(evidence["spend_required"])
        self.assertEqual(evidence["motion_id"], "motion-123")
        self.assertEqual(evidence["character_id"], "character-456")
        self.assertEqual(evidence["downloaded_path"], "C:/tmp/motion-123.fbx")
        self.assertEqual(evidence["primary_imported_asset"], "/Game/Generated/Animations/AS_GuardPatrol")
        self.assertEqual(evidence["approval_note"], "Approved guard patrol motion after PIE inspection.")

        partial_evidence = partial["outputs"]["evidence"]
        self.assertFalse(partial_evidence["proven"])
        self.assertIn("retarget_single_animation", json.dumps(partial_evidence["next_actions"]))
        self.assertIn("PIE evidence tools", json.dumps(partial_evidence["next_actions"]))
        self.assertIn("Generated animation evidence is not final", " ".join(partial["warnings"]))

    async def test_compile_generated_animation_evidence_accepts_video_job_result(self):
        job = {
            "success": True,
            "stage": "gen_uthana_get_job",
            "outputs": {
                "job_id": "job-123",
                "job_status": "FINISHED",
                "motion_id": "motion-789",
                "download_ready": True,
                "final": True,
                "job": {"id": "job-123", "status": "FINISHED", "result": {"result": {"id": "motion-789"}}},
            },
        }
        allowed = {
            "success": True,
            "stage": "gen_uthana_check_download_allowed",
            "outputs": {"allowed": True, "reason": "ok"},
        }
        downloaded = {
            "success": True,
            "stage": "gen_uthana_download_motion",
            "outputs": {
                "motion_id": "motion-789",
                "character_id": "character-456",
                "download": {"path": "C:/tmp/motion-789.fbx", "format": "fbx"},
            },
        }
        imported = {
            "success": True,
            "stage": "gen_uthana_import_animation_to_project",
            "outputs": {
                "motion_id": "motion-789",
                "character_id": "character-456",
                "asset_paths": {
                    "primary_asset": "/Game/Generated/Animations/AS_VideoPatrol",
                    "animation_sequence_paths": ["/Game/Generated/Animations/AS_VideoPatrol"],
                },
            },
        }
        complete = json.loads(await self.mcp.tools["gen_compile_generated_animation_evidence"](
            ctx=None,
            motion_prompt="video reference patrol walk",
            session_name="demo",
            job_result_json=json.dumps(job),
            download_allowed_json=json.dumps(allowed),
            download_result_json=json.dumps(downloaded),
            import_result_json=json.dumps(imported),
            retarget_evidence_json=json.dumps({"success": True, "outputs": {"retargeted_asset": "/Game/A_VideoPatrol_Retargeted"}}),
            animgraph_evidence_json=json.dumps({"success": True, "outputs": {"state_name": "Patrol"}}),
            pie_evidence_json=json.dumps({"success": True, "outputs": {"screenshot_path": "C:/tmp/video-patrol.png"}}),
            ledger_evidence_json=json.dumps({"success": True, "outputs": {"ledger_path": ".mcp_artifacts/demo/ledger.json"}}),
            approval_note="Approved video-derived patrol motion after PIE inspection.",
        ))
        in_progress = json.loads(await self.mcp.tools["gen_compile_generated_animation_evidence"](
            ctx=None,
            motion_prompt="video reference patrol walk",
            job_result_json=json.dumps({
                "success": True,
                "stage": "gen_uthana_get_job",
                "outputs": {
                    "job_id": "job-456",
                    "job_status": "RUNNING",
                    "motion_id": "",
                    "download_ready": False,
                    "final": False,
                    "job": {"id": "job-456", "status": "RUNNING"},
                },
            }),
        ))

        _assert_structured(self, complete, "gen_compile_generated_animation_evidence")
        evidence = complete["outputs"]["evidence"]
        self.assertTrue(evidence["proven"])
        self.assertEqual(evidence["motion_id"], "motion-789")
        self.assertEqual(evidence["job_status"], "FINISHED")
        self.assertEqual(evidence["provider_task_evidence"]["source"], "gen_uthana_get_job")
        self.assertEqual(evidence["provider_task_evidence"]["job_id"], "job-123")
        self.assertEqual(evidence["downloaded_path"], "C:/tmp/motion-789.fbx")
        self.assertEqual(evidence["primary_imported_asset"], "/Game/Generated/Animations/AS_VideoPatrol")
        self.assertTrue(complete["inputs"]["job_result_json_supplied"])

        next_actions = in_progress["outputs"]["evidence"]["next_actions"]
        self.assertFalse(in_progress["outputs"]["evidence"]["proven"])
        self.assertIn("gen_uthana_get_job", json.dumps(next_actions))
        self.assertNotIn("gen_uthana_text_to_motion", json.dumps(next_actions))

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

    async def test_prepare_texture_paint_session_records_plan_without_spend(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp:
            sessions_path = Path(tmp) / "Saved" / "MCPChat" / "texture_paint_sessions.json"
            settings_path = Path(tmp) / "Saved" / "MCPChat" / "generative_settings.json"
            with patch.object(generative_tools, "_TEXTURE_PAINT_SESSIONS_PATH", sessions_path), patch.object(generative_tools, "_SETTINGS_PATH", settings_path):
                payload = json.loads(await self.mcp.tools["gen_prepare_texture_paint_session"](
                    ctx=None,
                    model_task_id="model-task-123",
                    texture_prompt="weathered sci-fi metal",
                    texture_reference_image="C:/Refs/patina.png",
                    view_angle="front-left",
                    brush_strength=0.7,
                    blend_mode="soft blend",
                    paint_notes="preserve panel seams",
                    output_folder="/Game/Generated/Materials",
                    save_asset_name="MI_PatinaPass",
                    session_name="demo",
                ))

                _assert_structured(self, payload, "gen_prepare_texture_paint_session")
                self.assertTrue(payload["success"])
                self.assertTrue(sessions_path.exists())
                session = payload["outputs"]["session"]
                self.assertEqual(session["model_task_id"], "model-task-123")
                self.assertEqual(session["save_asset_name"], "MI_PatinaPass")
                self.assertIn("paint it onto the visible model", session["texture_prompt"])
                self.assertIn("rotate the model", session["texture_prompt"])
                self.assertEqual(payload["outputs"]["next_steps"][0]["tool"], "gen_tripo_texture_model")
                self.assertIn("viewport screenshot", " ".join(payload["outputs"]["evidence_contract"]))

    async def test_capture_texture_paint_snapshot_records_session_handoff_without_spend(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            sessions_path = tmp_path / "Saved" / "MCPChat" / "texture_paint_sessions.json"

            def fake_send(command, params):
                self.assertEqual(command, "take_screenshot")
                Path(params["filepath"]).parent.mkdir(parents=True, exist_ok=True)
                Path(params["filepath"]).write_bytes(b"\x89PNG\r\n\x1a\n")
                return {"success": True, "path": params["filepath"]}

            with patch.object(generative_tools, "_TEXTURE_PAINT_SESSIONS_PATH", sessions_path), \
                    patch.object(generative_tools, "_REPO_ROOT", tmp_path), \
                    patch.object(generative_tools, "_send", side_effect=fake_send), \
                    patch.object(generative_tools, "_tripo_upload_file", return_value={"file_token": "snapshot-token", "trace_id": "trace-upload"}):
                await self.mcp.tools["gen_prepare_texture_paint_session"](
                    ctx=None,
                    model_task_id="model-task-123",
                    texture_prompt="weathered sci-fi metal",
                    session_name="demo",
                )
                payload = json.loads(await self.mcp.tools["gen_capture_texture_paint_snapshot"](
                    ctx=None,
                    session_name="demo",
                    model_task_id="model-task-123",
                    label="source_view",
                    screenshot_dir=".mcp_artifacts/texture_paint",
                    resolution=[800, 450],
                    upload_to_tripo=True,
                ))

                session_data = json.loads(sessions_path.read_text(encoding="utf-8"))
                snapshot_exists = Path(payload["outputs"]["snapshot"]["path"]).exists()

        _assert_structured(self, payload, "gen_capture_texture_paint_snapshot")
        self.assertTrue(payload["success"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertTrue(payload["outputs"]["network_required"])
        self.assertEqual(payload["outputs"]["render_image"]["file_token"], "snapshot-token")
        self.assertTrue(snapshot_exists)
        self.assertTrue(payload["outputs"]["session_update"]["updated"])
        snapshots = session_data["sessions"][0]["viewport_snapshots"]
        self.assertEqual(snapshots[0]["label"], "source_view")
        self.assertEqual(snapshots[0]["render_image"]["file_token"], "snapshot-token")

    async def test_record_texture_paint_pass_appends_no_spend_iteration_evidence(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp:
            sessions_path = Path(tmp) / "Saved" / "MCPChat" / "texture_paint_sessions.json"
            with patch.object(generative_tools, "_TEXTURE_PAINT_SESSIONS_PATH", sessions_path):
                await self.mcp.tools["gen_prepare_texture_paint_session"](
                    ctx=None,
                    model_task_id="model-task-123",
                    texture_prompt="weathered sci-fi metal",
                    view_angle="front-left",
                    brush_strength=0.7,
                    blend_mode="soft blend",
                    session_name="demo",
                )
                payload = json.loads(await self.mcp.tools["gen_record_texture_paint_pass"](
                    ctx=None,
                    session_name="demo",
                    model_task_id="model-task-123",
                    pass_label="front_panel_highlights",
                    source_snapshot_label="source_view",
                    result_snapshot_label="painted_front",
                    texture_task_id="texture-task-456",
                    texture_asset_path="/Game/Generated/MI_PatinaPass",
                    affected_regions="front armor panels and bevel highlights",
                    brush_radius=0.3,
                    blend_amount=0.55,
                    pass_notes="blend the generated brass patina into panel edges",
                    approval_note="Approved front pass after viewport inspection.",
                ))
                session_data = json.loads(sessions_path.read_text(encoding="utf-8"))

        _assert_structured(self, payload, "gen_record_texture_paint_pass")
        self.assertTrue(payload["success"])
        self.assertFalse(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["spend_required"])
        paint_pass = payload["outputs"]["paint_pass"]
        self.assertEqual(paint_pass["pass_label"], "front_panel_highlights")
        self.assertEqual(paint_pass["brush_strength"], 0.7)
        self.assertEqual(paint_pass["brush_radius"], 0.3)
        self.assertTrue(paint_pass["approved"])
        self.assertEqual(session_data["sessions"][0]["paint_passes"][0]["texture_task_id"], "texture-task-456")

    async def test_compile_texture_paint_evidence_reports_complete_and_partial_gates(self):
        import tools.generative_tools as generative_tools

        with tempfile.TemporaryDirectory() as tmp:
            sessions_path = Path(tmp) / "Saved" / "MCPChat" / "texture_paint_sessions.json"
            with patch.object(generative_tools, "_TEXTURE_PAINT_SESSIONS_PATH", sessions_path):
                prepare = json.loads(await self.mcp.tools["gen_prepare_texture_paint_session"](
                    ctx=None,
                    model_task_id="model-task-123",
                    texture_prompt="weathered sci-fi metal",
                    view_angle="front-left",
                    save_asset_name="MI_PatinaPass",
                    session_name="demo",
                ))
                await self.mcp.tools["gen_record_texture_paint_pass"](
                    ctx=None,
                    session_name="demo",
                    model_task_id="model-task-123",
                    pass_label="front_panel_highlights",
                    result_snapshot_label="painted_front",
                    texture_task_id="texture-task-456",
                    texture_asset_path="/Game/Generated/MI_PatinaPass",
                    affected_regions="front armor panels",
                    approval_note="Approved paint pass after inspecting the viewport paint result.",
                )
                texture_task = {
                    "success": True,
                    "stage": "gen_tripo_texture_model",
                    "outputs": {"task_id": "texture-task-456"},
                }
                wait = {
                    "success": True,
                    "stage": "gen_tripo_wait_for_task",
                    "outputs": {"task": {"task_id": "texture-task-456", "status": "success", "consumed_credit": 10}},
                }
                imported = {
                    "success": True,
                    "stage": "gen_tripo_import_to_project",
                    "outputs": {
                        "task": {"task_id": "texture-task-456", "status": "success"},
                        "asset_paths": {"primary_asset": "/Game/Generated/MI_PatinaPass"},
                        "thumbnail": {"path": "C:/tmp/painted.png"},
                    },
                }
                complete = json.loads(await self.mcp.tools["gen_compile_texture_paint_evidence"](
                    ctx=None,
                    session_name="demo",
                    prepare_result_json=json.dumps(prepare),
                    texture_task_result_json=json.dumps(texture_task),
                    wait_result_json=json.dumps(wait),
                    import_result_json=json.dumps(imported),
                ))
                partial = json.loads(await self.mcp.tools["gen_compile_texture_paint_evidence"](
                    ctx=None,
                    session_name="demo",
                    prepare_result_json=json.dumps(prepare),
                ))

        _assert_structured(self, complete, "gen_compile_texture_paint_evidence")
        evidence = complete["outputs"]["evidence"]
        self.assertEqual(evidence["schema"], "unreal_mcp_texture_paint_evidence.v1")
        self.assertTrue(evidence["proven"])
        self.assertFalse(evidence["network_required"])
        self.assertFalse(evidence["spend_required"])
        self.assertEqual(evidence["texture_task_id"], "texture-task-456")
        self.assertEqual(evidence["asset_paths"]["primary_asset"], "/Game/Generated/MI_PatinaPass")
        self.assertEqual(evidence["viewport_evidence"]["path"], "C:/tmp/painted.png")
        self.assertEqual(evidence["latest_paint_pass"]["pass_label"], "front_panel_highlights")
        self.assertEqual(evidence["approval_note"], "Approved paint pass after inspecting the viewport paint result.")

        partial_evidence = partial["outputs"]["evidence"]
        self.assertFalse(partial_evidence["proven"])
        self.assertIn("gen_tripo_texture_model", json.dumps(partial_evidence["next_actions"]))
        self.assertIn("Texture-paint evidence is not final", " ".join(partial["warnings"]))

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
            "HandleRefreshGenerativeBalanceClicked",
            "BuildGenerativeSettingsPanel",
            "GetGenerativeSettingsVisibility",
            "GetGenerativeUthanaApiKeySource",
            "GetGenerativeApiWalletText",
            "RequestGenerativeBalanceRefresh",
            "GenerativeSessionCreditBudget",
            "GenerativePendingSpendCredits",
            "GenerativeApiWalletBalance",
            "GenerativeApiWalletFrozen",
            "GenerativeUthanaApiKey",
            "GenerativeUthanaApiKeyInput",
        ):
            with self.subTest(token=token):
                self.assertIn(token, panel_header)

        for token in (
            "Generate Asset Settings",
            "TRIPO_API_KEY",
            "generative_settings.json",
            "secrets.json",
            "Confirm Spend",
            "Refresh API Balance",
            "https://api.tripo3d.ai/v2/openapi/user/balance",
            "Tripo API Wallet",
            "Saved/MCPChat/secrets.json",
            "env:TRIPO_API_KEY",
            "env:UTHANA_API_KEY",
            "UTHANA_API_KEY for animation generation",
            "GenerativeUthanaApiKeyInput",
            "SetStringField(TEXT(\"UTHANA_API_KEY\"), GenerativeUthanaApiKey",
            "RemoveField(TEXT(\"uthana_api_key\"))",
            ".IsPassword(true)",
            "animation_provider",
            "animation_output_folder",
            "uthana_default_character_id",
            "spend_confirmed",
        ):
            with self.subTest(token=token):
                self.assertIn(token, panel_cpp)

        self.assertIn("UTHANA_API_KEY", generative_text)
        self.assertIn("uthana_api_key_configured", generative_text)

        for token in (
            "Config And Auth",
            "Cost Guard",
        ):
            with self.subTest(token=token):
                self.assertIn(token, kb_text)

        for token in (
            "gen_get_provider_config",
            "gen_tripo_get_credit_balance",
            "gen_save_provider_config",
            "gen_check_credit_budget",
            "gen_prepare_texture_paint_session",
            "gen_capture_texture_paint_snapshot",
            "gen_record_texture_paint_pass",
            "gen_compile_texture_paint_evidence",
            "gen_compile_generated_animation_evidence",
        ):
            with self.subTest(token=token):
                self.assertIn(token, kb_text)
                self.assertIn(token, generative_text)

        self.assertIn("D.2 - Generative config and auth", changelog_text)
        self.assertIn("no Tripo API call is made", changelog_text)


if __name__ == "__main__":
    unittest.main()
