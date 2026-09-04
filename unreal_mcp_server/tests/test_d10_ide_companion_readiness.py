"""Offline smoke coverage for IDE companion readiness compilation."""

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


class TestD10IdeCompanionReadiness(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.generative_tools import register_generative_tools

        self.mcp = _MockMCP()
        register_generative_tools(self.mcp)

    def _settings_context(self, api_key: str = "", uthana_api_key: str = "", budget: int = 1000):
        import tools.generative_tools as generative_tools

        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        settings_path = root / "Saved" / "MCPChat" / "generative_settings.json"
        secrets_path = root / "Saved" / "MCPChat" / "secrets.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps({
            "default_model_version": "tripo-default",
            "default_texture_quality": "standard",
            "output_folder": "/Game/Generated",
            "session_credit_budget": budget,
            "credit_usage_by_session": {},
        }), encoding="utf-8")
        secrets = {}
        if api_key:
            secrets["TRIPO_API_KEY"] = api_key
        if uthana_api_key:
            secrets["UTHANA_API_KEY"] = uthana_api_key
        if secrets:
            secrets_path.write_text(json.dumps(secrets), encoding="utf-8")
        return tmp, patch.object(generative_tools, "_SETTINGS_PATH", settings_path), patch.object(generative_tools, "_SECRETS_PATH", secrets_path), patch.dict(os.environ, {"TRIPO_API_KEY": "", "UTHANA_API_KEY": ""})

    def test_readiness_tool_registers(self):
        self.assertIn("gen_compile_ide_companion_readiness", self.mcp.tools)

    async def test_readiness_compiles_no_spend_gates_without_network(self):
        tmp, settings_patch, secrets_patch, env_patch = self._settings_context(api_key="")
        with tmp, settings_patch, secrets_patch, env_patch:
            payload = json.loads(await self.mcp.tools["gen_compile_ide_companion_readiness"](
                ctx=None,
                brief="third-person dungeon demo with a slime boss",
                include_api_wallet=False,
                include_unreal_bridge=False,
            ))

        _assert_structured(self, payload, "gen_compile_ide_companion_readiness")
        self.assertTrue(payload["success"])
        self.assertFalse(payload["outputs"]["ready"])
        self.assertFalse(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["bridge_required"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertEqual(payload["outputs"]["schema"], "unreal_mcp_ide_companion_readiness.v1")
        self.assertIn("blocking_gates", payload["outputs"])
        gates = {gate["name"]: gate for gate in payload["outputs"]["gates"]}
        self.assertFalse(gates["api_key_configured"]["ready"])
        self.assertTrue(gates["playable_slice_plan_valid"]["ready"])
        self.assertTrue(gates["spend_confirmation_enforced"]["ready"])
        blocking_gates = {gate["name"] for gate in payload["outputs"]["blocking_gates"]}
        self.assertIn("api_key_configured", blocking_gates)
        self.assertGreater(payload["outputs"]["playable_slice"]["estimated_asset_credits"], 0)
        self.assertFalse(payload["outputs"]["generated_animation"]["requires_animation_generation"])
        self.assertIn("gen_save_provider_config", json.dumps(payload["outputs"]["next_actions"]))

    async def test_mechanic_brief_threads_uthana_animation_gates_without_network(self):
        tmp, settings_patch, secrets_patch, env_patch = self._settings_context(api_key="tsk_test_secret_123456")
        with tmp, settings_patch, secrets_patch, env_patch:
            payload = json.loads(await self.mcp.tools["gen_compile_ide_companion_readiness"](
                ctx=None,
                brief="third-person combat slice",
                mechanic_brief="combat attack combo with hit reaction animations",
                include_api_wallet=False,
                include_animation_account=False,
                include_unreal_bridge=False,
            ))

        _assert_structured(self, payload, "gen_compile_ide_companion_readiness")
        self.assertTrue(payload["success"])
        self.assertFalse(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["spend_required"])
        generated_animation = payload["outputs"]["generated_animation"]
        self.assertTrue(generated_animation["requires_animation_generation"])
        self.assertGreaterEqual(generated_animation["prompt_count"], 2)
        self.assertGreater(generated_animation["estimated_motion_seconds"], 0)
        gates = {gate["name"]: gate for gate in payload["outputs"]["gates"]}
        self.assertTrue(gates["uthana_provider_registered"]["ready"])
        self.assertFalse(gates["animation_provider_key_configured"]["ready"])
        self.assertTrue(gates["animation_usage_confirmation_enforced"]["ready"])
        blocking_gates = {gate["name"] for gate in payload["outputs"]["blocking_gates"]}
        self.assertIn("animation_provider_key_configured", blocking_gates)
        self.assertIn("gen_save_provider_config", json.dumps(payload["outputs"]["next_actions"]))

    async def test_optional_uthana_account_check_reports_allowance_gate(self):
        tmp, settings_patch, secrets_patch, env_patch = self._settings_context(
            api_key="tsk_test_secret_123456",
            uthana_api_key="uthana_test_secret_123456",
        )
        with tmp, settings_patch, secrets_patch, env_patch, \
                patch("tools.generative_tools._uthana_get_account", return_value={
                    "org": {
                        "motion_download_secs_per_month": 1200,
                        "motion_download_secs_per_month_remaining": 0,
                        "characters_allowed_remaining": 2,
                    },
                    "http_status": 200,
                }):
            payload = json.loads(await self.mcp.tools["gen_compile_ide_companion_readiness"](
                ctx=None,
                brief="third-person combat slice",
                mechanic_brief="combat attack combo with hit reaction animations",
                include_animation_account=True,
            ))

        _assert_structured(self, payload, "gen_compile_ide_companion_readiness")
        self.assertTrue(payload["success"])
        self.assertTrue(payload["outputs"]["network_required"])
        gates = {gate["name"]: gate for gate in payload["outputs"]["gates"]}
        self.assertTrue(gates["animation_provider_key_configured"]["ready"])
        self.assertFalse(gates["uthana_motion_allowance_available"]["ready"])
        self.assertEqual(payload["outputs"]["optional_checks"]["uthana_account"]["motion_download_secs_per_month_remaining"], 0)
        self.assertIn("gen_uthana_get_account", json.dumps(payload["outputs"]["next_actions"]))

    async def test_optional_wallet_and_bridge_checks_report_actionable_failures(self):
        tmp, settings_patch, secrets_patch, env_patch = self._settings_context(api_key="tsk_test_secret_123456")
        with tmp, settings_patch, secrets_patch, env_patch, \
                patch("tools.generative_tools._tripo_get_credit_balance", return_value={
                    "balance": 0,
                    "frozen": 0,
                    "trace_id": "trace-wallet",
                    "http_status": 200,
                }), \
                patch("tools.generative_tools._send", return_value={
                    "success": False,
                    "message": "Not connected to Unreal Engine",
                }):
            payload = json.loads(await self.mcp.tools["gen_compile_ide_companion_readiness"](
                ctx=None,
                include_api_wallet=True,
                include_unreal_bridge=True,
            ))

        _assert_structured(self, payload, "gen_compile_ide_companion_readiness")
        self.assertTrue(payload["success"])
        self.assertFalse(payload["outputs"]["ready"])
        gates = {gate["name"]: gate for gate in payload["outputs"]["gates"]}
        self.assertTrue(gates["api_key_configured"]["ready"])
        self.assertFalse(gates["api_wallet_has_credits"]["ready"])
        self.assertFalse(gates["unreal_bridge_reachable"]["ready"])
        blocking_gates = {gate["name"] for gate in payload["outputs"]["blocking_gates"]}
        self.assertIn("api_wallet_has_credits", blocking_gates)
        self.assertIn("unreal_bridge_reachable", blocking_gates)
        self.assertEqual(payload["outputs"]["optional_checks"]["api_wallet"]["balance"], 0)
        self.assertIn("Fund the API wallet", json.dumps(payload["outputs"]["next_actions"]))
        self.assertIn("Start Unreal Editor", json.dumps(payload["outputs"]["next_actions"]))

    def test_static_kb_and_readme_reference_readiness_tool(self):
        kb_text = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        generative_text = (SERVER_ROOT / "tools" / "generative_tools.py").read_text(encoding="utf-8")

        self.assertIn("IDE Companion Readiness", kb_text)
        self.assertIn("gen_compile_ide_companion_readiness", kb_text)
        self.assertIn("gen_compile_ide_companion_readiness", generative_text)
        self.assertIn("D.10 - IDE companion readiness", changelog_text)


if __name__ == "__main__":
    unittest.main()
