"""Offline smoke coverage for Workstream D.1 generative content tools."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


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


class TestD1GenerativeTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.generative_tools import register_generative_tools

        self.mcp = _MockMCP()
        register_generative_tools(self.mcp)

    def test_d1_generative_tools_register(self):
        expected = {
            "gen_list_providers",
            "gen_uthana_text_to_motion",
            "gen_uthana_create_character",
            "gen_uthana_get_character",
            "gen_uthana_create_locomotion",
            "gen_uthana_video_to_motion",
            "gen_uthana_get_job",
            "gen_uthana_download_motion",
            "gen_uthana_import_animation_to_project",
            "gen_compile_generated_animation_evidence",
            "gen_prepare_import_manifest",
            "gen_tripo_wait_for_task",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    async def test_gen_list_providers_reports_tripo_scaffold(self):
        payload = json.loads(await self.mcp.tools["gen_list_providers"](
            ctx=None,
            include_import_helpers=True,
        ))

        _assert_structured(self, payload, "gen_list_providers")
        self.assertTrue(payload["success"])
        self.assertFalse(payload["outputs"]["network_required"])
        providers = payload["outputs"]["providers"]
        self.assertEqual(providers[0]["provider"], "tripo")
        self.assertEqual(providers[1]["provider"], "uthana")
        self.assertEqual(providers[1]["provider_role"], "animation_motion")
        self.assertIn("text_to_motion", providers[1]["capabilities"])
        self.assertIn("D.8 knowledge base", providers[0]["next_milestones"])
        helpers = payload["outputs"]["import_helpers"]
        self.assertEqual(helpers[0]["native_route"], "gen_prepare_import_manifest")
        self.assertEqual(helpers[1]["tool"], "gen_tripo_import_to_project")

    async def test_gen_prepare_import_manifest_calls_native_route(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "stage": command,
                "manifest": {
                    "task_id": params["task_id"],
                    "provider": params["provider"],
                    "content_path": params["content_path"],
                    "asset_name": "SM_SlimeEnemy",
                    "source_files": [
                        {
                            "file_path": params["local_files"][0],
                            "extension": "glb",
                            "import_kind": "static_mesh",
                            "exists_on_host": False,
                        }
                    ],
                    "expected_assets": {
                        "primary_asset": "/Game/Generated/Enemies/SM_SlimeEnemy",
                        "material_instance": "/Game/Generated/Enemies/MI_SM_SlimeEnemy",
                        "blueprint": "/Game/Generated/Enemies/BP_SM_SlimeEnemy",
                    },
                    "options": {
                        "create_material_instance": True,
                        "create_blueprint": True,
                        "overwrite_existing": False,
                    },
                    "all_files_present": False,
                },
                "content_path": params["content_path"],
                "asset_name": "SM_SlimeEnemy",
                "all_files_present": False,
                "warnings": ["Source file does not exist on host yet: C:/Generated/slime_enemy.glb"],
            }

        with patch("tools.generative_tools._send", side_effect=fake_send):
            payload = json.loads(await self.mcp.tools["gen_prepare_import_manifest"](
                ctx=None,
                task_id="tripo_task_123",
                local_files=["C:/Generated/slime_enemy.glb"],
                content_path="/Game/Generated/Enemies",
                asset_name="SM_SlimeEnemy",
                provider="tripo",
                create_material_instance=True,
                create_blueprint=True,
                overwrite_existing=False,
            ))

        _assert_structured(self, payload, "gen_prepare_import_manifest")
        self.assertTrue(payload["success"])
        self.assertEqual(calls[0][0], "gen_prepare_import_manifest")
        self.assertEqual(calls[0][1]["task_id"], "tripo_task_123")
        self.assertEqual(calls[0][1]["local_files"], ["C:/Generated/slime_enemy.glb"])
        manifest = payload["outputs"]["manifest"]
        self.assertEqual(manifest["provider"], "tripo")
        self.assertEqual(manifest["source_files"][0]["import_kind"], "static_mesh")
        self.assertEqual(manifest["expected_assets"]["blueprint"], "/Game/Generated/Enemies/BP_SM_SlimeEnemy")

    async def test_provider_balance_runs_blocking_request_off_event_loop(self):
        fake_balance = {
            "balance": 120,
            "frozen": 0,
            "trace_id": "trace-1",
            "http_status": 200,
        }
        with patch(
            "tools.generative_tools.asyncio.to_thread",
            new=AsyncMock(return_value=fake_balance),
        ) as offload:
            payload = json.loads(await self.mcp.tools["gen_tripo_get_credit_balance"](
                ctx=None,
                timeout_s=30,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["balance"], 120)
        offload.assert_awaited_once()

    async def test_tripo_wait_polls_without_blocking_sleep(self):
        snapshots = [
            {"task": {"status": "running", "progress": 25}},
            {"task": {"status": "success", "progress": 100}},
        ]
        with patch("tools.generative_tools._tripo_get_task", side_effect=snapshots), patch(
            "tools.generative_tools.asyncio.sleep",
            new=AsyncMock(),
        ) as async_sleep:
            payload = json.loads(await self.mcp.tools["gen_tripo_wait_for_task"](
                ctx=None,
                task_id="task-1",
                timeout_s=10,
                poll_s=1,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["outputs"]["snapshots"]), 2)
        async_sleep.assert_awaited_once_with(1)

    def test_d1_static_registration_and_kb_links(self):
        server_text = (SERVER_ROOT / "unreal_mcp_server.py").read_text(encoding="utf-8")
        inventory_text = (SERVER_ROOT / "tool_inventory_categories.json").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        bridge_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCP" / "Private" / "UnrealMCPBridge.cpp").read_text(encoding="utf-8")
        header_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCP" / "Public" / "Commands" / "UnrealMCPGenerativeCommands.h").read_text(encoding="utf-8")
        cpp_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCP" / "Private" / "Commands" / "UnrealMCPGenerativeCommands.cpp").read_text(encoding="utf-8")
        audit_text = (REPO_ROOT / "scripts" / "bridge_command_audit.py").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")

        self.assertIn("from tools.generative_tools import register_generative_tools", server_text)
        self.assertIn("register_generative_tools(tool_mcp)", server_text)
        self.assertIn('"tools.generative_tools"', inventory_text)
        self.assertIn("Provider Scaffold", kb_text)
        self.assertIn("Import Manifest Helper", kb_text)
        self.assertIn("UnrealMCPGenerativeCommands.h", bridge_text)
        self.assertIn('CommandType == TEXT("gen_prepare_import_manifest")', bridge_text)
        self.assertIn("FUnrealMCPGenerativeCommands", header_text)
        self.assertIn("HandlePrepareImportManifest", cpp_text)
        self.assertIn('"gen_": "generative_content_pipeline"', audit_text)
        self.assertIn("D.1 - Generative module scaffold", changelog_text)


if __name__ == "__main__":
    unittest.main()
