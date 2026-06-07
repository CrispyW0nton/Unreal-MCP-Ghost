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
            "gen_check_credit_budget",
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
            "gen_check_credit_budget",
        ):
            with self.subTest(token=token):
                self.assertIn(token, kb_text)
                self.assertIn(token, generative_text)

        self.assertIn("D.2 - Generative config and auth", changelog_text)
        self.assertIn("no Tripo API call is made", changelog_text)


if __name__ == "__main__":
    unittest.main()
