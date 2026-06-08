"""Offline smoke coverage for Workstream D.3 Tripo task tools."""

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


class TestD3TripoTaskTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.generative_tools import register_generative_tools

        self.mcp = _MockMCP()
        register_generative_tools(self.mcp)

    def _settings_context(self):
        import tools.generative_tools as generative_tools

        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        settings_path = root / "Saved" / "MCPChat" / "generative_settings.json"
        secrets_path = root / "Saved" / "MCPChat" / "secrets.json"
        ledger_path = root / "Saved" / "MCPChat" / "tripo_task_credit_ledger.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps({
            "default_model_version": "v3.1-20260211",
            "default_texture_quality": "standard",
            "output_folder": "/Game/Generated",
            "session_credit_budget": 500,
            "credit_usage_by_session": {},
        }), encoding="utf-8")
        secrets_path.write_text(json.dumps({"TRIPO_API_KEY": "tsk_test_secret_123456"}), encoding="utf-8")
        return (
            tmp,
            patch.object(generative_tools, "_SETTINGS_PATH", settings_path),
            patch.object(generative_tools, "_SECRETS_PATH", secrets_path),
            patch.object(generative_tools, "_TRIPO_TASK_CREDIT_LEDGER_PATH", ledger_path),
            patch.dict(os.environ, {"TRIPO_API_KEY": ""}),
        )

    def test_d3_tools_register(self):
        expected = {
            "gen_tripo_text_to_model",
            "gen_tripo_image_to_model",
            "gen_tripo_multiview_to_model",
            "gen_tripo_refine_model",
            "gen_tripo_texture_model",
            "gen_tripo_post_process",
            "gen_tripo_get_task_status",
            "gen_tripo_wait_for_task",
            "gen_tripo_download_result",
            "gen_tripo_get_wallet_balance",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    async def test_text_to_model_requires_confirm_before_submit(self):
        tmp, settings_patch, secrets_patch, ledger_patch, env_patch = self._settings_context()
        with tmp, settings_patch, secrets_patch, ledger_patch, env_patch, patch("tools.generative_tools._tripo_submit_task") as submit:
            payload = json.loads(await self.mcp.tools["gen_tripo_text_to_model"](
                ctx=None,
                prompt="stylized slime enemy",
                confirm_spend=False,
            ))

        _assert_structured(self, payload, "gen_tripo_text_to_model")
        self.assertFalse(payload["success"])
        self.assertTrue(payload["outputs"]["credit_guard"]["confirm_required"])
        submit.assert_not_called()

    async def test_text_to_model_submits_payload_after_confirm(self):
        calls = []

        def fake_submit(payload):
            calls.append(payload)
            return {"task_id": "task-text", "response": {"code": 0, "data": {"task_id": "task-text"}}, "trace_id": "trace-1"}

        tmp, settings_patch, secrets_patch, ledger_patch, env_patch = self._settings_context()
        with tmp, settings_patch, secrets_patch, ledger_patch, env_patch, patch("tools.generative_tools._tripo_submit_task", side_effect=fake_submit):
            payload = json.loads(await self.mcp.tools["gen_tripo_text_to_model"](
                ctx=None,
                prompt="stylized slime enemy",
                face_limit=12000,
                texture=True,
                pbr=True,
                confirm_spend=True,
                session_name="demo",
            ))

        _assert_structured(self, payload, "gen_tripo_text_to_model")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["task_id"], "task-text")
        self.assertEqual(calls[0]["type"], "text_to_model")
        self.assertEqual(calls[0]["prompt"], "stylized slime enemy")
        self.assertEqual(calls[0]["model_version"], "v3.1-20260211")
        self.assertTrue(calls[0]["smart_low_poly"])
        self.assertTrue(payload["outputs"]["credit_guard"]["reserved"])
        self.assertEqual(payload["outputs"]["credit_record"]["task_id"], "task-text")
        self.assertEqual(payload["outputs"]["credit_record"]["session_name"], "demo")

    async def test_status_reconciles_actual_consumed_credit_once(self):
        def fake_submit(_payload):
            return {"task_id": "task-text", "response": {"code": 0, "data": {"task_id": "task-text"}}, "trace_id": "trace-1"}

        final_task = {
            "task_id": "task-text",
            "status": "success",
            "progress": 100,
            "consumed_credit": 34,
            "output": {"model": "https://signed.example/model.glb"},
        }

        tmp, settings_patch, secrets_patch, ledger_patch, env_patch = self._settings_context()
        with tmp, settings_patch, secrets_patch, ledger_patch, env_patch, \
                patch("tools.generative_tools._tripo_submit_task", side_effect=fake_submit), \
                patch("tools.generative_tools._tripo_get_task", return_value={"task": final_task, "trace_id": "trace-status"}):
            submitted = json.loads(await self.mcp.tools["gen_tripo_text_to_model"](
                ctx=None,
                prompt="stylized slime enemy",
                confirm_spend=True,
                session_name="demo",
            ))
            estimated = submitted["outputs"]["credit_guard"]["estimated_credits"]
            status = json.loads(await self.mcp.tools["gen_tripo_get_task_status"](ctx=None, task_id="task-text"))
            status_again = json.loads(await self.mcp.tools["gen_tripo_get_task_status"](ctx=None, task_id="task-text"))
            import tools.generative_tools as generative_tools
            settings = generative_tools._load_generative_settings()

        self.assertGreater(estimated, 34)
        _assert_structured(self, status, "gen_tripo_get_task_status")
        reconciliation = status["outputs"]["credit_reconciliation"]
        self.assertTrue(reconciliation["available"])
        self.assertEqual(reconciliation["estimated_credits"], estimated)
        self.assertEqual(reconciliation["consumed_credits"], 34)
        self.assertEqual(reconciliation["used_after"], 34)
        self.assertTrue(status_again["outputs"]["credit_reconciliation"]["already_reconciled"])
        self.assertEqual(settings["credit_usage_by_session"]["demo"], 34)

    async def test_wallet_balance_reads_live_balance_without_spend(self):
        with patch("tools.generative_tools._tripo_get_wallet_balance", return_value={
            "balance": 300,
            "frozen": 20,
            "trace_id": "trace-wallet",
            "raw_response": {"code": 0, "data": {"balance": 300, "frozen": 20}},
        }):
            payload = json.loads(await self.mcp.tools["gen_tripo_get_wallet_balance"](ctx=None, timeout_s=5))

        _assert_structured(self, payload, "gen_tripo_get_wallet_balance")
        self.assertTrue(payload["success"])
        self.assertTrue(payload["outputs"]["network_required"])
        self.assertFalse(payload["outputs"]["spend_required"])
        self.assertEqual(payload["outputs"]["wallet"]["balance"], 300)
        self.assertEqual(payload["outputs"]["wallet"]["frozen"], 20)

    async def test_submission_failure_releases_credit_reservation(self):
        tmp, settings_patch, secrets_patch, ledger_patch, env_patch = self._settings_context()
        with tmp, settings_patch, secrets_patch, ledger_patch, env_patch, patch("tools.generative_tools._tripo_submit_task", side_effect=RuntimeError("provider unavailable")):
            payload = json.loads(await self.mcp.tools["gen_tripo_text_to_model"](
                ctx=None,
                prompt="stylized slime enemy",
                confirm_spend=True,
                session_name="demo",
            ))
            import tools.generative_tools as generative_tools
            settings = generative_tools._load_generative_settings()

        _assert_structured(self, payload, "gen_tripo_text_to_model")
        credit_guard = payload["outputs"]["credit_guard"]
        self.assertFalse(payload["success"])
        self.assertFalse(credit_guard["reserved"])
        self.assertTrue(credit_guard["released"])
        self.assertEqual(settings["credit_usage_by_session"]["demo"], 0)

    async def test_image_and_multiview_payloads_support_local_upload_and_urls(self):
        submitted = []

        def fake_submit(payload):
            submitted.append(payload)
            return {"task_id": f"task-{payload['type']}", "response": {"code": 0, "data": {"task_id": "task"}}, "trace_id": "trace"}

        tmp, settings_patch, secrets_patch, ledger_patch, env_patch = self._settings_context()
        with tmp, settings_patch, secrets_patch, ledger_patch, env_patch, \
                patch("tools.generative_tools._tripo_submit_task", side_effect=fake_submit), \
                patch("tools.generative_tools._tripo_upload_file", return_value={"file_token": "uploaded-token"}):
            image_payload = json.loads(await self.mcp.tools["gen_tripo_image_to_model"](
                ctx=None,
                image_path="C:/Images/slime.png",
                confirm_spend=True,
            ))
            multiview_payload = json.loads(await self.mcp.tools["gen_tripo_multiview_to_model"](
                ctx=None,
                images=[
                    {"image_url": "https://example.com/front.png"},
                    {"file_token": "left-token"},
                ],
                confirm_spend=True,
            ))

        _assert_structured(self, image_payload, "gen_tripo_image_to_model")
        _assert_structured(self, multiview_payload, "gen_tripo_multiview_to_model")
        self.assertTrue(image_payload["success"])
        self.assertEqual(submitted[0]["file"]["file_token"], "uploaded-token")
        self.assertTrue(submitted[0]["smart_low_poly"])
        self.assertTrue(multiview_payload["success"])
        self.assertEqual(submitted[1]["type"], "multiview_to_model")
        self.assertTrue(submitted[1]["smart_low_poly"])
        self.assertEqual(len(submitted[1]["files"]), 4)
        self.assertEqual(submitted[1]["files"][0]["url"], "https://example.com/front.png")

    async def test_refine_texture_and_post_process_submit_expected_task_types(self):
        submitted = []

        def fake_submit(payload):
            submitted.append(payload)
            return {"task_id": f"task-{payload['type']}", "response": {"code": 0, "data": {"task_id": "task"}}, "trace_id": "trace"}

        tmp, settings_patch, secrets_patch, ledger_patch, env_patch = self._settings_context()
        with tmp, settings_patch, secrets_patch, ledger_patch, env_patch, patch("tools.generative_tools._tripo_submit_task", side_effect=fake_submit):
            refine = json.loads(await self.mcp.tools["gen_tripo_refine_model"](ctx=None, task_id="draft-task", confirm_spend=True))
            texture = json.loads(await self.mcp.tools["gen_tripo_texture_model"](ctx=None, task_id="model-task", texture_prompt="mossy stone", confirm_spend=True))
            convert = json.loads(await self.mcp.tools["gen_tripo_post_process"](ctx=None, task_id="model-task", target_format="FBX", confirm_spend=True))

        self.assertTrue(refine["success"])
        self.assertTrue(texture["success"])
        self.assertTrue(convert["success"])
        self.assertEqual([item["type"] for item in submitted], ["refine_model", "texture_model", "convert_model"])
        self.assertEqual(submitted[1]["texture_prompt"]["text"], "mossy stone")
        self.assertEqual(submitted[2]["format"], "FBX")

    async def test_status_wait_and_download_use_task_outputs(self):
        statuses = [
            {"task_id": "task-1", "status": "queued", "progress": 0, "output": {}},
            {"task_id": "task-1", "status": "success", "progress": 100, "output": {"model": "https://signed.example/model.glb"}},
        ]

        def fake_get(_task_id):
            task = statuses.pop(0) if statuses else {"task_id": "task-1", "status": "success", "progress": 100, "output": {"model": "https://signed.example/model.glb"}}
            return {"task": task, "trace_id": "trace-status", "response": {"code": 0, "data": task}}

        def fake_download(url, target_path):
            return {"path": str(target_path), "bytes": 123, "http_status": 200, "url": url}

        with patch("tools.generative_tools._tripo_get_task", side_effect=fake_get), \
                patch("tools.generative_tools._download_url", side_effect=fake_download), \
                patch("tools.generative_tools.time.sleep"):
            status = json.loads(await self.mcp.tools["gen_tripo_get_task_status"](ctx=None, task_id="task-1"))
            wait = json.loads(await self.mcp.tools["gen_tripo_wait_for_task"](ctx=None, task_id="task-1", timeout_s=5, poll_s=1))
            download = json.loads(await self.mcp.tools["gen_tripo_download_result"](ctx=None, task_id="task-1", target_folder="C:/Generated"))

        _assert_structured(self, status, "gen_tripo_get_task_status")
        _assert_structured(self, wait, "gen_tripo_wait_for_task")
        _assert_structured(self, download, "gen_tripo_download_result")
        self.assertFalse(status["outputs"]["final"])
        self.assertTrue(wait["success"])
        self.assertTrue(download["success"])
        self.assertEqual(download["outputs"]["downloads"][0]["bytes"], 123)

    def test_d3_static_kb_and_changelog(self):
        kb_text = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        generative_text = (SERVER_ROOT / "tools" / "generative_tools.py").read_text(encoding="utf-8")

        self.assertIn("Tripo Task Family", kb_text)

        for token in (
            "gen_tripo_text_to_model",
            "gen_tripo_image_to_model",
            "gen_tripo_multiview_to_model",
            "gen_tripo_get_wallet_balance",
            "gen_tripo_download_result",
            "consumed_credit",
            "confirm_spend=True",
        ):
            with self.subTest(token=token):
                self.assertIn(token, kb_text)
                self.assertIn(token, generative_text)
        self.assertIn("D.3 - Tripo task tools", changelog_text)
        self.assertIn("reservation rollback", changelog_text)


if __name__ == "__main__":
    unittest.main()
