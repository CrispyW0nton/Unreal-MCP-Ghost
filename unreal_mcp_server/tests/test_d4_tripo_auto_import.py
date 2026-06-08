"""Offline smoke coverage for Workstream D.4 Tripo auto-import bridge."""

from __future__ import annotations

import json
import sys
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


class TestD4TripoAutoImport(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.generative_tools import register_generative_tools

        self.mcp = _MockMCP()
        register_generative_tools(self.mcp)

    def test_d4_tool_registers(self):
        self.assertIn("gen_tripo_import_to_project", self.mcp.tools)
        self.assertIn("gen_compile_generate_asset_evidence", self.mcp.tools)

    async def test_import_to_project_downloads_manifests_imports_and_captures_thumbnail(self):
        calls = {"downloads": [], "send": [], "imports": [], "thumbs": []}

        def fake_get_task(task_id):
            return {
                "task": {
                    "task_id": task_id,
                    "status": "success",
                    "output": {
                        "pbr_model": "https://signed.example/slime.glb",
                        "rendered_image": "https://signed.example/slime.png",
                    },
                },
                "trace_id": "trace-d4",
                "response": {"code": 0},
            }

        def fake_download(url, target_path):
            calls["downloads"].append((url, str(target_path)))
            return {"path": str(target_path), "bytes": 2048, "http_status": 200, "url": url}

        def fake_send(command, params):
            calls["send"].append((command, params))
            return {
                "success": True,
                "stage": command,
                "manifest": {
                    "task_id": params["task_id"],
                    "provider": "tripo",
                    "content_path": params["content_path"],
                    "asset_name": "SM_Slime",
                    "source_files": [{"file_path": params["local_files"][0], "import_kind": "static_mesh", "exists_on_host": True}],
                    "expected_assets": {
                        "primary_asset": "/Game/Generated/Enemies/SM_Slime",
                        "material_instance": "/Game/Generated/Enemies/MI_SM_Slime",
                    },
                    "options": params,
                    "all_files_present": True,
                },
                "warnings": [],
            }

        def fake_import(**kwargs):
            calls["imports"].append(kwargs)
            return {
                "success": True,
                "stage": "gen_tripo_import_to_project",
                "message": "Operation completed",
                "outputs": {
                    "asset_path": "/Game/Generated/Enemies/SM_Slime",
                    "asset_type": "StaticMesh",
                    "imported_object_paths": ["/Game/Generated/Enemies/SM_Slime.SM_Slime"],
                    "material_instance": "/Game/Generated/Enemies/MI_SM_Slime",
                    "blueprint": "",
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        def fake_thumbnail(task_id, asset_name):
            calls["thumbs"].append((task_id, asset_name))
            return {"success": True, "path": "C:/Repo/.mcp_artifacts/screenshots/slime.png", "native_response": {"success": True}}

        with patch("tools.generative_tools._tripo_get_task", side_effect=fake_get_task), \
                patch("tools.generative_tools._download_url", side_effect=fake_download), \
                patch("tools.generative_tools._send", side_effect=fake_send), \
                patch("tools.generative_tools._import_generated_static_mesh", side_effect=fake_import), \
                patch("tools.generative_tools._capture_import_thumbnail", side_effect=fake_thumbnail):
            payload = json.loads(await self.mcp.tools["gen_tripo_import_to_project"](
                ctx=None,
                task_id="task-d4",
                content_path="/Game/Generated/Enemies",
                asset_name="SM_Slime",
                create_material_instance=True,
                create_blueprint=False,
                capture_thumbnail=True,
            ))

        _assert_structured(self, payload, "gen_tripo_import_to_project")
        self.assertTrue(payload["success"])
        self.assertEqual(calls["send"][0][0], "gen_prepare_import_manifest")
        self.assertEqual(calls["imports"][0]["file_path"], calls["downloads"][0][1])
        self.assertEqual(calls["imports"][0]["content_path"], "/Game/Generated/Enemies")
        self.assertEqual(payload["outputs"]["asset_paths"]["primary_asset"], "/Game/Generated/Enemies/SM_Slime")
        self.assertEqual(payload["outputs"]["thumbnail"]["path"], "C:/Repo/.mcp_artifacts/screenshots/slime.png")
        self.assertEqual(calls["thumbs"][0], ("task-d4", "SM_Slime"))

    async def test_import_to_project_stops_when_task_is_not_successful(self):
        with patch("tools.generative_tools._tripo_get_task", return_value={"task": {"task_id": "task-d4", "status": "running"}, "trace_id": "trace"}), \
                patch("tools.generative_tools._download_url") as download, \
                patch("tools.generative_tools._import_generated_static_mesh") as import_mesh:
            payload = json.loads(await self.mcp.tools["gen_tripo_import_to_project"](
                ctx=None,
                task_id="task-d4",
                content_path="/Game/Generated/Enemies",
            ))

        _assert_structured(self, payload, "gen_tripo_import_to_project")
        self.assertFalse(payload["success"])
        self.assertIn("Task is not successful", payload["message"])
        download.assert_not_called()
        import_mesh.assert_not_called()

    async def test_compile_generate_asset_evidence_reports_complete_proof(self):
        task_result = {
            "success": True,
            "stage": "gen_tripo_wait_for_task",
            "inputs": {"task_id": "task-d4"},
            "outputs": {
                "task": {"task_id": "task-d4", "status": "success"},
                "credit_reconciliation": {"available": True, "consumed_credits": 42},
            },
        }
        import_result = {
            "success": True,
            "stage": "gen_tripo_import_to_project",
            "inputs": {"task_id": "task-d4"},
            "outputs": {
                "asset_paths": {
                    "primary_asset": "/Game/Generated/Enemies/SM_Slime",
                    "material_instance": "/Game/Generated/Enemies/MI_SM_Slime",
                    "blueprint": "",
                    "imported_object_paths": ["/Game/Generated/Enemies/SM_Slime.SM_Slime"],
                },
                "thumbnail": {"success": True, "path": "C:/Repo/.mcp_artifacts/screenshots/slime.png"},
            },
        }
        validation_result = {
            "success": True,
            "stage": "validate_import_result",
            "outputs": {"asset_path": "/Game/Generated/Enemies/SM_Slime", "exists": True, "class": "StaticMesh"},
        }

        payload = json.loads(await self.mcp.tools["gen_compile_generate_asset_evidence"](
            ctx=None,
            task_result_json=json.dumps(task_result),
            import_result_json=json.dumps(import_result),
            validation_result_json=json.dumps(validation_result),
            session_name="asset-session",
            asset_name="SM_Slime",
            content_path="/Game/Generated/Enemies",
        ))

        _assert_structured(self, payload, "gen_compile_generate_asset_evidence")
        self.assertTrue(payload["success"])
        evidence = payload["outputs"]["evidence"]
        self.assertEqual(evidence["schema"], "unreal_mcp_generate_asset_evidence.v1")
        self.assertTrue(evidence["proven"])
        self.assertFalse(evidence["network_required"])
        self.assertFalse(evidence["spend_required"])
        self.assertEqual(evidence["task_id"], "task-d4")
        self.assertEqual(evidence["asset_paths"]["primary_asset"], "/Game/Generated/Enemies/SM_Slime")
        self.assertEqual(evidence["visual_evidence"]["thumbnail_path"], "C:/Repo/.mcp_artifacts/screenshots/slime.png")
        self.assertTrue(all(gate["status"] == "ready" for gate in evidence["gates"]))

    async def test_compile_generate_asset_evidence_reports_missing_followups(self):
        task_result = {
            "success": True,
            "stage": "gen_tripo_wait_for_task",
            "inputs": {"task_id": "task-d4"},
            "outputs": {"task": {"task_id": "task-d4", "status": "success"}},
        }
        import_result = {
            "success": True,
            "stage": "gen_tripo_import_to_project",
            "inputs": {"task_id": "task-d4"},
            "outputs": {
                "asset_paths": {"primary_asset": "/Game/Generated/Enemies/SM_Slime"},
                "thumbnail": {},
            },
        }

        payload = json.loads(await self.mcp.tools["gen_compile_generate_asset_evidence"](
            ctx=None,
            task_result_json=json.dumps(task_result),
            import_result_json=json.dumps(import_result),
            session_name="asset-session",
            asset_name="SM_Slime",
            content_path="/Game/Generated/Enemies",
        ))

        _assert_structured(self, payload, "gen_compile_generate_asset_evidence")
        self.assertFalse(payload["success"])
        evidence = payload["outputs"]["evidence"]
        self.assertFalse(evidence["proven"])
        gates = {gate["id"]: gate["status"] for gate in evidence["gates"]}
        self.assertEqual(gates["import_validation"], "missing")
        self.assertEqual(gates["visual_evidence"], "missing")
        self.assertIn("validate_import_result", json.dumps(evidence["next_actions"]))
        self.assertIn("viewport_capture_screenshot", json.dumps(evidence["next_actions"]))

    def test_d4_static_kb_and_changelog(self):
        kb_text = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        generative_text = (SERVER_ROOT / "tools" / "generative_tools.py").read_text(encoding="utf-8")

        self.assertIn("Auto-Import Bridge", kb_text)
        self.assertIn("gen_tripo_import_to_project", kb_text)
        self.assertIn("gen_compile_generate_asset_evidence", kb_text)
        self.assertIn("gen_tripo_import_to_project", generative_text)
        self.assertIn("gen_compile_generate_asset_evidence", generative_text)
        self.assertIn("D.4 - Tripo auto-import bridge", changelog_text)


if __name__ == "__main__":
    unittest.main()
