"""
test_project_intelligence.py — V5 Project Intelligence tool tests
==================================================================

Tests for:
  project_find_assets, project_get_references, project_trace_reference_chain,
  project_find_blueprint_by_parent, project_list_subsystems

All tests run offline (no live UE5 required).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(__file__)
_SERVER_ROOT = os.path.dirname(_HERE)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _parse(s) -> dict:
    if isinstance(s, dict):
        return s
    return json.loads(s)


def _assert_schema(result_str, test_name="") -> dict:
    data = _parse(result_str)
    assert "success"  in data, f"{test_name}: missing 'success'"
    assert "stage"    in data, f"{test_name}: missing 'stage'"
    assert "message"  in data, f"{test_name}: missing 'message'"
    assert "outputs"  in data, f"{test_name}: missing 'outputs'"
    assert "warnings" in data, f"{test_name}: missing 'warnings'"
    assert "errors"   in data, f"{test_name}: missing 'errors'"
    return data


class _MockMCP:
    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def tool(self):
        def dec(fn):
            self._tools[fn.__name__] = fn
            return fn
        return dec

    def get_tool(self, name):
        return self._tools.get(name)

    def list_tool_names(self):
        return list(self._tools.keys())


def _mock_ctx():
    return MagicMock()


# ── Shared exec_python mock ───────────────────────────────────────────────────

_FAKE_ASSETS = [
    {"package_name": "/Game/Blueprints/BP_DemoA",        "asset_name": "BP_DemoA",
     "class_path": "/Script/Engine.Blueprint",
     "tags": {"ParentClass": "/Script/Engine.Actor"}},
    {"package_name": "/Game/Blueprints/BP_HealthSystem",  "asset_name": "BP_HealthSystem",
     "class_path": "/Script/Engine.Blueprint",
     "tags": {"ParentClass": "/Script/Engine.Actor"}},
    {"package_name": "/Game/Materials/M_DemoB",           "asset_name": "M_DemoB",
     "class_path": "/Script/Engine.Material",
     "tags": {}},
]


def _exec_python_mock_assets(code: str) -> dict:
    """Return fake asset results for exec_python calls (receives code string directly)."""
    if "get_assets" in code or "ARFilter" in code:
        blueprints = [a for a in _FAKE_ASSETS if "Blueprint" in a["class_path"]]
        return {"success": True, "result": {
            "total": len(blueprints),
            "assets": blueprints,
        }}
    if "get_referencers" in code:
        return {"success": True, "result": {"package": "/Game/Blueprints/BP_HealthSystem",
                                              "referencers": ["/Game/Maps/DemoLevel"],
                                              "dependencies": ["/Script/Engine.Actor"]}}
    if "get_dependencies" in code:
        return {"success": True, "result": {"dependencies": ["/Script/Engine.Actor"]}}
    if "get_all_classes_of_type" in code:
        return {"success": True, "result": {
            "engine": [{"class": "UEngineSubsystem", "module": "Engine", "available": True}],
            "editor": [{"class": "UEditorAssetSubsystem", "module": "UnrealEd", "available": True},
                       {"class": "UEditorActorSubsystem", "module": "UnrealEd", "available": True},
                       {"class": "UEditorLevelSubsystem", "module": "UnrealEd", "available": True},
                       {"class": "UEditorMaterialSubsystem", "module": "UnrealEd", "available": True},
                       {"class": "UEditorStaticMeshSubsystem", "module": "UnrealEd", "available": True}],
            "gameinstance": [{"class": "UGameInstanceSubsystem", "module": "Engine", "available": True}],
            "localplayer":  [{"class": "ULocalPlayerSubsystem", "module": "Engine", "available": True}],
        }}
    if "deque" in code:
        return {"success": True, "result": {
            "nodes": [{"package": "/Game/Maps/DemoLevel", "depth": 1, "via": "/Game/Materials/M_DemoB"}],
            "depth_reached": 1,
            "truncated": False,
        }}
    return {"success": True, "result": {}}


# ── Registration test ─────────────────────────────────────────────────────────

class TestProjectIntelligenceRegistration(unittest.TestCase):

    def setUp(self):
        from tools.project_intelligence_tools import register_project_intelligence_tools
        self.mcp = _MockMCP()
        register_project_intelligence_tools(self.mcp)

    def test_all_5_tools_registered(self):
        tools = set(self.mcp.list_tool_names())
        expected = {
            "project_find_assets",
            "project_get_references",
            "project_trace_reference_chain",
            "project_find_blueprint_by_parent",
            "project_list_subsystems",
        }
        missing = expected - tools
        self.assertEqual(missing, set(), f"Missing tools: {missing}")


# ── project_find_assets tests ─────────────────────────────────────────────────

class TestProjectFindAssets(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from tools.project_intelligence_tools import register_project_intelligence_tools
        self.mcp = _MockMCP()
        register_project_intelligence_tools(self.mcp)
        self.tool = self.mcp.get_tool("project_find_assets")

    async def test_schema_is_valid(self):
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_exec_python_mock_assets):
            result = await self.tool(_mock_ctx(), class_names=["Blueprint"], package_paths=["/Game/Blueprints"])
        _assert_schema(result, "find_assets_schema")

    async def test_finds_blueprints(self):
        """Happy: returns BP_DemoA and BP_HealthSystem."""
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_exec_python_mock_assets):
            result = await self.tool(_mock_ctx(), class_names=["Blueprint"], package_paths=["/Game/Blueprints"])
        data = _parse(result)
        self.assertTrue(data["success"])
        names = {a["asset_name"] for a in data["outputs"]["assets"]}
        self.assertIn("BP_DemoA", names)
        self.assertIn("BP_HealthSystem", names)

    async def test_empty_on_bogus_path(self):
        """Empty result (no crash) on a path that returns nothing."""
        def _mock(code):
            return {"success": True, "result": {"total": 0, "assets": []}}
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), package_paths=["/Game/DoesNotExist_XYZ"])
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["total"], 0)

    async def test_not_connected_returns_error(self):
        """When exec_python fails, returns success=False with error_code."""
        def _mock(code):
            return {"success": False, "message": "Not connected", "error_code": "ERR_UNREAL_NOT_CONNECTED"}
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx())
        data = _parse(result)
        self.assertFalse(data["success"])

    async def test_pagination_fields_present(self):
        """Result includes total, page, page_size, total_pages."""
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_exec_python_mock_assets):
            result = await self.tool(_mock_ctx(), class_names=["Blueprint"], limit=50)
        out = _parse(result)["outputs"]
        for key in ("total", "page", "page_size", "total_pages"):
            self.assertIn(key, out, f"Missing pagination key: {key}")


# ── project_get_references tests ──────────────────────────────────────────────

class TestProjectGetReferences(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from tools.project_intelligence_tools import register_project_intelligence_tools
        self.mcp = _MockMCP()
        register_project_intelligence_tools(self.mcp)
        self.tool = self.mcp.get_tool("project_get_references")

    async def test_both_direction_returns_referencers_and_deps(self):
        def _mock(code):
            return {"success": True, "result": {
                "package": "/Game/Blueprints/BP_HealthSystem",
                "referencers": ["/Game/Maps/DemoLevel"],
                "dependencies": ["/Script/Engine.Actor"],
            }}
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(),
                                     package_name="/Game/Blueprints/BP_HealthSystem",
                                     direction="both")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertIn("referencers",  data["outputs"])
        self.assertIn("dependencies", data["outputs"])

    async def test_invalid_direction_returns_error(self):
        result = await self.tool(_mock_ctx(), package_name="/Game/X", direction="sideways")
        data = _parse(result)
        self.assertFalse(data["success"])
        self.assertIn("error_code", data)

    async def test_no_connection_fails_gracefully(self):
        def _mock(code):
            return {"success": False, "message": "Not connected"}
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), package_name="/Game/Blueprints/BP_HealthSystem")
        data = _parse(result)
        self.assertFalse(data["success"])


# ── project_trace_reference_chain tests ──────────────────────────────────────

class TestProjectTraceReferenceChain(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from tools.project_intelligence_tools import register_project_intelligence_tools
        self.mcp = _MockMCP()
        register_project_intelligence_tools(self.mcp)
        self.tool = self.mcp.get_tool("project_trace_reference_chain")

    async def test_happy_path(self):
        def _mock(code):
            return {"success": True, "result": {
                "nodes": [{"package": "/Game/Maps/DemoLevel", "depth": 1, "via": "/Game/Materials/M_DemoB"}],
                "depth_reached": 1, "truncated": False,
            }}
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(),
                                     start_package="/Game/Materials/M_DemoB",
                                     direction="in", max_depth=2)
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertIn("depth_reached", data["outputs"])

    async def test_depth_zero_returns_empty_nodes(self):
        def _mock(code):
            return {"success": True, "result": {"nodes": [], "depth_reached": 0, "truncated": False}}
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), start_package="/Game/X", max_depth=0)
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["nodes"], [])

    async def test_invalid_direction_fails(self):
        result = await self.tool(_mock_ctx(), start_package="/Game/X", direction="sideways")
        data = _parse(result)
        self.assertFalse(data["success"])


# ── project_find_blueprint_by_parent tests ────────────────────────────────────

class TestProjectFindBlueprintByParent(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from tools.project_intelligence_tools import register_project_intelligence_tools
        self.mcp = _MockMCP()
        register_project_intelligence_tools(self.mcp)
        self.tool = self.mcp.get_tool("project_find_blueprint_by_parent")

    async def test_finds_bp_demo_a_by_actor(self):
        def _mock(code):
            return {"success": True, "result": {
                "total": 2,
                "assets": [
                    {"package_name": "/Game/Blueprints/BP_DemoA",        "asset_name": "BP_DemoA",
                     "class_path": "/Script/Engine.Blueprint",
                     "tags": {"ParentClass": "/Script/Engine.Actor"}},
                    {"package_name": "/Game/Blueprints/BP_HealthSystem",  "asset_name": "BP_HealthSystem",
                     "class_path": "/Script/Engine.Blueprint",
                     "tags": {"ParentClass": "/Script/Engine.Actor"}},
                ],
            }}
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), parent_class="Actor")
        data = _parse(result)
        self.assertTrue(data["success"])
        names = {a["asset_name"] for a in data["outputs"]["assets"]}
        self.assertIn("BP_DemoA", names)

    async def test_empty_on_bogus_parent(self):
        def _mock(code):
            return {"success": True, "result": {"total": 0, "assets": []}}
        with patch("tools.project_intelligence_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), parent_class="NonExistentClass_XYZ")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["total"], 0)


# ── project_list_subsystems tests ─────────────────────────────────────────────

class TestProjectListSubsystems(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from tools.project_intelligence_tools import register_project_intelligence_tools
        import tools.project_intelligence_tools as pit
        # Reset cache
        pit._SUBSYSTEM_CACHE    = {}
        pit._SUBSYSTEM_CACHE_TS = 0.0
        self.mcp = _MockMCP()
        register_project_intelligence_tools(self.mcp)
        self.tool = self.mcp.get_tool("project_list_subsystems")

    def _mock_refresh(self):
        return {
            "engine": [{"class": "UEngineSubsystem", "module": "Engine", "available": True}],
            "editor": [{"class": "UEditorAssetSubsystem",   "module": "UnrealEd", "available": True},
                       {"class": "UEditorActorSubsystem",   "module": "UnrealEd", "available": True},
                       {"class": "UEditorLevelSubsystem",   "module": "UnrealEd", "available": True},
                       {"class": "UEditorMaterialSubsystem","module": "UnrealEd", "available": True},
                       {"class": "UEditorStaticMeshSubsystem","module": "UnrealEd", "available": True}],
            "gameinstance": [{"class": "UGameInstanceSubsystem", "module": "Engine", "available": True}],
            "localplayer":  [{"class": "ULocalPlayerSubsystem",  "module": "Engine", "available": True}],
        }

    async def test_editor_category_contains_ueditorassetsubsystem(self):
        import tools.project_intelligence_tools as pit
        with patch.object(pit, "_refresh_subsystem_cache", return_value=self._mock_refresh()):
            result = await self.tool(_mock_ctx(), category="editor", refresh=True)
        data = _parse(result)
        self.assertTrue(data["success"])
        editor_classes = {s["class"] for s in data["outputs"].get("editor", [])}
        self.assertIn("UEditorAssetSubsystem", editor_classes)

    async def test_editor_category_has_at_least_5_entries(self):
        import tools.project_intelligence_tools as pit
        with patch.object(pit, "_refresh_subsystem_cache", return_value=self._mock_refresh()):
            result = await self.tool(_mock_ctx(), category="editor", refresh=True)
        data = _parse(result)
        self.assertGreaterEqual(len(data["outputs"].get("editor", [])), 5)

    async def test_all_category_has_all_subcategories(self):
        import tools.project_intelligence_tools as pit
        with patch.object(pit, "_refresh_subsystem_cache", return_value=self._mock_refresh()):
            result = await self.tool(_mock_ctx(), category="all", refresh=True)
        data = _parse(result)
        out = data["outputs"]
        for cat in ("engine", "editor", "gameinstance", "localplayer"):
            self.assertIn(cat, out, f"Missing category: {cat}")

    async def test_invalid_category_fails(self):
        result = await self.tool(_mock_ctx(), category="invalid_cat")
        data = _parse(result)
        self.assertFalse(data["success"])

    async def test_cache_refresh(self):
        """refresh=True forces a new scan."""
        import tools.project_intelligence_tools as pit
        call_count = [0]
        def mock_refresh():
            call_count[0] += 1
            return self._mock_refresh()
        with patch.object(pit, "_refresh_subsystem_cache", side_effect=mock_refresh):
            await self.tool(_mock_ctx(), category="all", refresh=True)
            await self.tool(_mock_ctx(), category="all", refresh=True)
        self.assertGreaterEqual(call_count[0], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
