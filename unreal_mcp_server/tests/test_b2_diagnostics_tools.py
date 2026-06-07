"""Offline smoke coverage for Workstream B.2 diagnostic report tools."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SERVER_ROOT = Path(__file__).resolve().parents[1]
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


def _exec_response(payload: dict) -> dict:
    return {"success": True, "result": {"output": json.dumps(payload)}}


def _assert_structured(testcase: unittest.TestCase, payload: dict, stage: str):
    for key in ("success", "stage", "message", "inputs", "outputs", "warnings", "errors", "log_tail"):
        testcase.assertIn(key, payload)
    testcase.assertEqual(payload["stage"], stage)


class TestB2DiagnosticsTools(unittest.TestCase):
    def setUp(self):
        from tools.diagnostics_tools import register_diagnostics_tools

        self.mcp = _MockMCP()
        register_diagnostics_tools(self.mcp)

    def test_b2_tools_register(self):
        for name in {
            "compile_blueprint_and_report",
            "compile_material_and_report",
            "validate_import_result",
            "get_changed_assets_since",
        }:
            self.assertIn(name, self.mcp.tools)

    def test_compile_blueprint_and_report_parses_exec_evidence(self):
        async def run():
            with patch("tools.diagnostics_tools._exec_python", return_value=_exec_response({
                "compile_status": "clean",
                "compile_clean": True,
                "had_errors": False,
                "had_warnings": False,
                "errors": [],
                "warnings": [],
                "graph_summaries": [{"graph_name": "EventGraph", "node_count": 3}],
                "graph_count": 1,
                "blueprint_path": "/Game/BP_Test",
            })):
                return json.loads(await self.mcp.tools["compile_blueprint_and_report"](
                    ctx=None,
                    blueprint_path="/Game/BP_Test",
                ))

        payload = asyncio.run(run())
        _assert_structured(self, payload, "compile_blueprint_and_report")
        self.assertTrue(payload["outputs"]["compile_clean"])
        self.assertTrue(payload["outputs"]["safe_to_continue"])
        self.assertEqual(payload["outputs"]["graph_count"], 1)

    def test_compile_material_and_report_parses_expression_summary(self):
        async def run():
            with patch("tools.diagnostics_tools._exec_python", return_value=_exec_response({
                "compile_status": "warnings_only",
                "compile_clean": True,
                "had_errors": False,
                "errors": [],
                "warnings": [{"code": "MAT_NO_EXPRESSIONS"}],
                "expression_count": 0,
                "expression_summaries": [],
                "material_path": "/Game/M_Test",
            })):
                return json.loads(await self.mcp.tools["compile_material_and_report"](
                    ctx=None,
                    material_path="/Game/M_Test",
                ))

        payload = asyncio.run(run())
        _assert_structured(self, payload, "compile_material_and_report")
        self.assertEqual(payload["outputs"]["compile_status"], "warnings_only")
        self.assertEqual(payload["outputs"]["expression_count"], 0)

    def test_validate_import_result_marks_valid_asset(self):
        async def run():
            with patch("tools.diagnostics_tools._exec_python", return_value=_exec_response({
                "asset_path": "/Game/SM_Table",
                "exists": True,
                "class_name": "StaticMesh",
                "expected_class": "StaticMesh",
                "class_matches": True,
                "package_name": "/Game/SM_Table",
                "object_path": "/Game/SM_Table.SM_Table",
                "dirty": False,
                "source_file_exists": True,
                "referencer_count": 0,
                "dependency_count": 1,
                "warnings": [],
                "errors": [],
            })):
                return json.loads(await self.mcp.tools["validate_import_result"](
                    ctx=None,
                    expected_asset_path="/Game/SM_Table",
                    expected_class="StaticMesh",
                    source_file="C:/tmp/table.fbx",
                ))

        payload = asyncio.run(run())
        _assert_structured(self, payload, "validate_import_result")
        self.assertTrue(payload["outputs"]["valid"])
        self.assertTrue(payload["outputs"]["class_matches"])

    def test_get_changed_assets_since_parses_dirty_and_changed_assets(self):
        async def run():
            with patch("tools.diagnostics_tools._exec_python", return_value=_exec_response({
                "timestamp": "2026-06-07T00:00:00Z",
                "path": "/Game",
                "changed_assets": [{"asset_path": "/Game/BP_Test"}],
                "dirty_assets": ["/Game/M_Test"],
                "changed_count": 1,
                "dirty_count": 1,
                "errors": [],
            })):
                return json.loads(await self.mcp.tools["get_changed_assets_since"](
                    ctx=None,
                    timestamp="2026-06-07T00:00:00Z",
                ))

        payload = asyncio.run(run())
        _assert_structured(self, payload, "get_changed_assets_since")
        self.assertEqual(payload["outputs"]["changed_count"], 1)
        self.assertEqual(payload["outputs"]["dirty_count"], 1)


if __name__ == "__main__":
    unittest.main()
