"""Offline coverage for Tripo Studio Magic Brush endpoint wrappers."""

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


class TestD10TripoMagicBrushStudioTools(unittest.IsolatedAsyncioTestCase):
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
            patch.dict(os.environ, {"TRIPO_API_KEY": ""}),
        )

    def test_magic_brush_tools_register(self):
        expected = {
            "gen_tripo_magic_brush_generate",
            "gen_tripo_magic_brush_get_retexture",
            "gen_tripo_magic_brush_list_images",
            "gen_tripo_magic_brush_apply",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    async def test_generate_requires_spend_confirmation_before_studio_call(self):
        tmp, settings_patch, secrets_patch, env_patch = self._settings_context()
        with tmp, settings_patch, secrets_patch, env_patch, patch("tools.generative_tools._tripo_studio_operation") as operation:
            payload = json.loads(await self.mcp.tools["gen_tripo_magic_brush_generate"](
                ctx=None,
                project_id="project-1",
                prompt="worn brass edge highlights",
                render_image_bucket="bucket",
                render_image_key="snapshot.png",
                confirm_spend=False,
            ))

        _assert_structured(self, payload, "gen_tripo_magic_brush_generate")
        self.assertFalse(payload["success"])
        self.assertTrue(payload["outputs"]["credit_guard"]["confirm_required"])
        operation.assert_not_called()

    async def test_generate_get_list_and_apply_submit_studio_payloads(self):
        calls = []

        def fake_operation(operation, payload, timeout_s=60):
            calls.append((operation, payload, timeout_s))
            if operation == "retexture_generate":
                return {"data": {"operator_id": "operator-1"}, "response": {"code": 0}, "trace_id": "trace-generate"}
            if operation == "get_retexture":
                return {"data": {"url": "https://signed.example/retexture.png", "camera_matrix": [1, 0, 0]}, "response": {"code": 0}, "trace_id": "trace-get"}
            if operation == "get_retexture_images":
                return {"data": {"images": [{"url": "https://signed.example/history.png"}]}, "response": {"code": 0}, "trace_id": "trace-list"}
            if operation == "apply_retexture":
                return {"data": {"project_id": payload["project_id"], "status": "success"}, "response": {"code": 0}, "trace_id": "trace-apply"}
            raise AssertionError(operation)

        tmp, settings_patch, secrets_patch, env_patch = self._settings_context()
        image_map = [{"part_name": "Body", "image": {"bucket": "paint-bucket", "key": "body.png"}}]
        with tmp, settings_patch, secrets_patch, env_patch, patch("tools.generative_tools._tripo_studio_operation", side_effect=fake_operation):
            generate = json.loads(await self.mcp.tools["gen_tripo_magic_brush_generate"](
                ctx=None,
                project_id="project-1",
                prompt="paint chipped red enamel",
                render_image={"bucket": "snap-bucket", "key": "front.png"},
                camera_matrix=[1, 0, 0, 0],
                strength=0.7,
                confirm_spend=True,
                session_name="studio",
            ))
            get_result = json.loads(await self.mcp.tools["gen_tripo_magic_brush_get_retexture"](ctx=None, operator_id="operator-1"))
            list_result = json.loads(await self.mcp.tools["gen_tripo_magic_brush_list_images"](ctx=None, project_id="project-1"))
            apply_result = json.loads(await self.mcp.tools["gen_tripo_magic_brush_apply"](
                ctx=None,
                project_id="project-1",
                image_map=image_map,
                confirm_spend=True,
                session_name="studio",
            ))

        _assert_structured(self, generate, "gen_tripo_magic_brush_generate")
        _assert_structured(self, get_result, "gen_tripo_magic_brush_get_retexture")
        _assert_structured(self, list_result, "gen_tripo_magic_brush_list_images")
        _assert_structured(self, apply_result, "gen_tripo_magic_brush_apply")
        self.assertTrue(generate["success"])
        self.assertEqual(generate["outputs"]["operator_id"], "operator-1")
        self.assertTrue(apply_result["success"])
        self.assertEqual([item[0] for item in calls], ["retexture_generate", "get_retexture", "get_retexture_images", "apply_retexture"])
        self.assertEqual(calls[0][1]["render_image"]["bucket"], "snap-bucket")
        self.assertEqual(calls[0][1]["strength"], 0.7)
        self.assertEqual(calls[3][1]["image_map"], image_map)

    async def test_apply_failure_releases_credit_reservation(self):
        tmp, settings_patch, secrets_patch, env_patch = self._settings_context()
        with tmp, settings_patch, secrets_patch, env_patch, patch("tools.generative_tools._tripo_studio_operation", side_effect=RuntimeError("studio unavailable")):
            payload = json.loads(await self.mcp.tools["gen_tripo_magic_brush_apply"](
                ctx=None,
                project_id="project-1",
                image_map=[{"part_name": "Body", "image": {"bucket": "bucket", "key": "body.png"}}],
                confirm_spend=True,
                session_name="studio",
            ))
            import tools.generative_tools as generative_tools
            settings = generative_tools._load_generative_settings()

        _assert_structured(self, payload, "gen_tripo_magic_brush_apply")
        self.assertFalse(payload["success"])
        credit_guard = payload["outputs"]["credit_guard"]
        self.assertFalse(credit_guard["reserved"])
        self.assertTrue(credit_guard["released"])
        self.assertEqual(settings["credit_usage_by_session"]["studio"], 0)

    def test_static_kb_and_changelog_record_magic_brush_wrappers(self):
        kb_text = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        generative_text = (SERVER_ROOT / "tools" / "generative_tools.py").read_text(encoding="utf-8")

        for token in (
            "gen_tripo_magic_brush_generate",
            "gen_tripo_magic_brush_get_retexture",
            "gen_tripo_magic_brush_list_images",
            "gen_tripo_magic_brush_apply",
            "apply_retexture",
        ):
            with self.subTest(token=token):
                self.assertIn(token, kb_text)
                self.assertIn(token, generative_text)
        self.assertIn("Magic Brush Studio endpoint wrappers", changelog_text)


if __name__ == "__main__":
    unittest.main()
