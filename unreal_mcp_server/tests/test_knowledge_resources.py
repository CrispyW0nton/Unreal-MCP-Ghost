"""Offline tests for knowledge-base MCP resource registration."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


_HERE = Path(__file__).resolve().parent
_SERVER_ROOT = _HERE.parent
_REPO_ROOT = _SERVER_ROOT.parent
if str(_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVER_ROOT))


class TestKnowledgeResources(unittest.TestCase):
    def setUp(self):
        from mcp.server.fastmcp import FastMCP
        import tools.knowledge_tools as kt
        from tools.knowledge_tools import register_knowledge_tools

        self._old_transport = os.environ.get("UNREAL_MCP_TRANSPORT")
        os.environ["UNREAL_MCP_TRANSPORT"] = "stdio"
        kt._PROJECT_CONTEXT_CACHE = {"timestamp": 0.0, "context": None}
        self.mcp = FastMCP("test_knowledge_resources")
        register_knowledge_tools(self.mcp)

    def tearDown(self):
        if self._old_transport is None:
            os.environ.pop("UNREAL_MCP_TRANSPORT", None)
        else:
            os.environ["UNREAL_MCP_TRANSPORT"] = self._old_transport

    def _expected_resource_uris(self) -> set[str]:
        kb_root = _REPO_ROOT / "knowledge_base"
        expected = {f"kb://{path.name}" for path in kb_root.glob("*.md")}
        expected.update(f"kb://v4/{path.name}" for path in (kb_root / "v4").glob("*.md"))
        expected.update(f"kb://v5/{path.name}" for path in (kb_root / "v5").glob("*.md"))
        return expected

    def test_registers_top_level_v4_and_v5_markdown_as_resources(self):
        resources = self.mcp._resource_manager.list_resources()
        actual = {str(resource.uri) for resource in resources}

        self.assertEqual(actual, self._expected_resource_uris())

    def test_resources_have_human_metadata(self):
        for resource in self.mcp._resource_manager.list_resources():
            with self.subTest(uri=str(resource.uri)):
                self.assertEqual(resource.mime_type, "text/markdown")
                self.assertTrue(resource.title)
                self.assertTrue(resource.description)
                self.assertNotEqual(resource.title, resource.name)

    def test_a7_modern_system_docs_exist_with_required_sections(self):
        expected_docs = [
            "19_GAMEPLAY_ABILITY_SYSTEM.md",
            "20_NETWORKING_AND_REPLICATION.md",
            "21_METASOUNDS_AND_AUDIO_DSP.md",
            "22_GEOMETRY_SCRIPT_AND_MODELING.md",
            "23_MASS_ENTITY_AND_STATETREE.md",
            "24_MOTION_MATCHING_AND_CHOOSERS.md",
            "25_WORLD_PARTITION_AND_HLOD.md",
            "26_CHAOS_PHYSICS_AND_DESTRUCTION.md",
            "27_METAHUMAN_PIPELINE.md",
            "28_MOVIE_RENDER_QUEUE_AND_SEQUENCER.md",
            "29_PIXEL_STREAMING_AND_REMOTE.md",
            "30_ONLINE_SUBSYSTEM_AND_EOS.md",
            "31_GENERATIVE_CONTENT_PIPELINE.md",
            "32_AGENT_PLAYABLE_SLICE_RECIPE.md",
        ]
        required_headings = [
            "## Overview",
            "## Key Classes",
            "## Common Pitfalls",
            "## MCP Tool Mapping",
            "## Working Example",
        ]
        kb_root = _REPO_ROOT / "knowledge_base"

        for filename in expected_docs:
            with self.subTest(filename=filename):
                content = (kb_root / filename).read_text(encoding="utf-8")
                self.assertTrue(content.startswith("# "))
                for heading in required_headings:
                    self.assertIn(heading, content)

    def test_resource_reads_markdown_content(self):
        uri = "kb://00_AGENT_KNOWLEDGE_BASE.md"
        resource = next(
            r for r in self.mcp._resource_manager.list_resources()
            if str(r.uri) == uri
        )

        content = asyncio.run(resource.read())

        self.assertIn("#", content)
        self.assertIn("Knowledge", content)

    def test_v5_changelog_resource_reads_append_only_log(self):
        uri = "kb://v5/CHANGELOG.md"
        resource = next(
            r for r in self.mcp._resource_manager.list_resources()
            if str(r.uri) == uri
        )

        content = asyncio.run(resource.read())

        self.assertIn("# Knowledge Base v5 Changelog", content)
        self.assertIn("A.9 - v5 changelog resource", content)

    def test_get_server_info_returns_a2_payload(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}

        self.assertIn("get_server_info", tools)

        payload = json.loads(tools["get_server_info"]())

        self.assertTrue(payload["success"])
        self.assertEqual(payload["version"], "2.0.0")
        self.assertEqual(payload["transport"], "stdio")
        self.assertEqual(payload["tool_count"], len(tools))
        self.assertEqual(payload["kb_doc_count"], len(self._expected_resource_uris()))
        self.assertGreaterEqual(payload["resource_count"], payload["kb_doc_count"])
        self.assertIn("start_here", payload)
        self.assertIn("kb_docs", payload)
        self.assertIn(
            "kb://00_AGENT_KNOWLEDGE_BASE.md",
            {doc["uri"] for doc in payload["kb_docs"]},
        )

    def test_get_project_context_returns_a3_payload(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}
        fake_context = {
            "success": True,
            "stage": "get_project_context",
            "uproject": "C:/Project/Demo.uproject",
            "project_name": "Demo",
            "engine_version": "5.6.0",
            "open_level": {"map_name": "DemoMap", "package_name": "/Game/Maps/DemoMap"},
            "selected_actor": {"name": "BP_Player_0", "class": "BP_Player_C", "path": "/Game/BP_Player_0"},
            "selected_actors": [{"name": "BP_Player_0", "class": "BP_Player_C", "path": "/Game/BP_Player_0"}],
            "dirty_packages": ["/Game/Blueprints/BP_Player"],
            "content_folders": ["Blueprints", "Maps"],
            "plugins": [{"name": "UnrealMCP", "enabled": True, "source": "uproject"}],
        }

        self.assertIn("get_project_context", tools)

        with patch("tools.knowledge_tools._fetch_project_context_live", return_value=fake_context):
            payload = json.loads(tools["get_project_context"]())

        self.assertTrue(payload["success"])
        self.assertFalse(payload["cached"])
        for key in (
            "uproject",
            "engine_version",
            "open_level",
            "selected_actor",
            "dirty_packages",
            "content_folders",
            "plugins",
        ):
            self.assertIn(key, payload)
        self.assertEqual(payload["uproject"], "C:/Project/Demo.uproject")
        self.assertEqual(payload["cache_ttl_s"], 5.0)

    def test_get_project_context_uses_five_second_cache(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}
        first_context = {
            "success": True,
            "stage": "get_project_context",
            "uproject": "C:/Project/First.uproject",
            "engine_version": "5.6.0",
            "open_level": None,
            "selected_actor": None,
            "selected_actors": [],
            "dirty_packages": [],
            "content_folders": [],
            "plugins": [],
        }
        second_context = dict(first_context, uproject="C:/Project/Second.uproject")

        with patch(
            "tools.knowledge_tools._fetch_project_context_live",
            side_effect=[first_context, second_context],
        ) as fetch:
            first_payload = json.loads(tools["get_project_context"]())
            second_payload = json.loads(tools["get_project_context"]())
            refreshed_payload = json.loads(tools["get_project_context"](force_refresh=True))

        self.assertEqual(fetch.call_count, 2)
        self.assertFalse(first_payload["cached"])
        self.assertTrue(second_payload["cached"])
        self.assertEqual(second_payload["uproject"], "C:/Project/First.uproject")
        self.assertFalse(refreshed_payload["cached"])
        self.assertEqual(refreshed_payload["uproject"], "C:/Project/Second.uproject")

    def test_get_onboarding_context_supports_required_a4_tasks(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}

        self.assertIn("get_onboarding_context", tools)

        payload = json.loads(tools["get_onboarding_context"]("generative"))
        required = {
            "blueprints",
            "animation",
            "ai",
            "materials",
            "niagara",
            "umg",
            "world_building",
            "audio",
            "generative",
            "multiplayer",
            "gas",
            "metasounds",
        }

        self.assertTrue(payload["success"])
        self.assertEqual(set(payload["available_tasks"]), required)
        self.assertEqual(payload["task"], "generative")
        self.assertIn("documents", payload)
        self.assertIn("tool_domains", payload)
        self.assertIn("workflow", payload)
        self.assertIn("kb://13_TOOL_EXPANSION_ROADMAP.md", payload["resource_uris"])
        self.assertIn("knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md", payload["expected_future_docs"])
        self.assertNotIn(
            "knowledge_base/31_GENERATIVE_CONTENT_PIPELINE.md",
            payload["missing_expected_docs"],
        )
        self.assertTrue(all(doc["available"] for doc in payload["documents"]))
        self.assertTrue(any(doc["content"] for doc in payload["documents"]))

    def test_get_onboarding_context_resolves_aliases(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}

        payload = json.loads(tools["get_onboarding_context"]("ui"))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["task"], "umg")
        self.assertIn("kb://06_UI_UMG_SYSTEMS.md", payload["resource_uris"])

    def test_get_onboarding_context_rejects_unknown_task(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}

        payload = json.loads(tools["get_onboarding_context"]("not_a_real_task"))

        self.assertFalse(payload["success"])
        self.assertIn("available_tasks", payload)
        self.assertIn("generative", payload["available_tasks"])

    def test_scan_project_assets_returns_a5_inventory(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}
        fake_scan = {
            "success": True,
            "stage": "scan_project_assets",
            "path": "/Game/Blueprints",
            "depth": 1,
            "class_filter": ["Blueprint"],
            "total_assets": 2,
            "returned_assets": 2,
            "total_size_bytes": 3072,
            "by_class": {"Blueprint": 2},
            "assets": [
                {
                    "package_name": "/Game/Blueprints/BP_Player",
                    "asset_name": "BP_Player",
                    "package_path": "/Game/Blueprints",
                    "class": "Blueprint",
                    "class_path": "/Script/Engine.Blueprint",
                    "object_path": "/Game/Blueprints/BP_Player.BP_Player",
                    "size_bytes": 2048,
                    "references_count": 3,
                    "dependencies_count": 7,
                    "folder_depth": 0,
                },
                {
                    "package_name": "/Game/Blueprints/AI/BP_Enemy",
                    "asset_name": "BP_Enemy",
                    "package_path": "/Game/Blueprints/AI",
                    "class": "Blueprint",
                    "class_path": "/Script/Engine.Blueprint",
                    "object_path": "/Game/Blueprints/AI/BP_Enemy.BP_Enemy",
                    "size_bytes": 1024,
                    "references_count": 1,
                    "dependencies_count": 5,
                    "folder_depth": 1,
                },
            ],
        }

        self.assertIn("scan_project_assets", tools)

        with patch("tools.knowledge_tools._scan_project_assets_live", return_value=fake_scan):
            payload = json.loads(
                tools["scan_project_assets"](
                    path="/Game/Blueprints",
                    depth=1,
                    class_filter="Blueprint",
                )
            )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["stage"], "scan_project_assets")
        self.assertEqual(payload["path"], "/Game/Blueprints")
        self.assertEqual(payload["depth"], 1)
        self.assertEqual(payload["class_filter"], ["Blueprint"])
        self.assertEqual(payload["total_assets"], 2)
        self.assertEqual(payload["total_size_bytes"], 3072)
        self.assertEqual(payload["by_class"], {"Blueprint": 2})
        for asset in payload["assets"]:
            for key in ("class", "size_bytes", "references_count"):
                self.assertIn(key, asset)

    def test_scan_project_assets_clamps_negative_depth(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}

        with patch(
            "tools.knowledge_tools._scan_project_assets_live",
            return_value={
                "success": True,
                "stage": "scan_project_assets",
                "path": "/Game",
                "depth": 0,
                "class_filter": [],
                "total_assets": 0,
                "returned_assets": 0,
                "total_size_bytes": 0,
                "by_class": {},
                "assets": [],
            },
        ) as scan:
            payload = json.loads(tools["scan_project_assets"](path="", depth=-4))

        scan.assert_called_once_with("/Game", 0, "")
        self.assertTrue(payload["success"])
        self.assertEqual(payload["depth"], 0)

    def test_list_available_tools_filters_by_category(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}

        self.assertIn("list_available_tools", tools)

        payload = json.loads(tools["list_available_tools"](domain="knowledge_base"))
        names = {tool["name"] for tool in payload["tools"]}

        self.assertTrue(payload["success"])
        self.assertEqual(payload["resolved_categories"], ["knowledge_base"])
        self.assertIn("get_server_info", names)
        self.assertIn("list_available_tools", names)
        self.assertTrue(all(tool["category"] == "knowledge_base" for tool in payload["tools"]))
        self.assertIn("knowledge_base", payload["tools_by_category"])

    def test_list_available_tools_resolves_friendly_aliases(self):
        def fake_blueprint_tool(blueprint_name: str) -> str:
            """Fake Blueprint tool for category discovery tests."""
            return blueprint_name

        fake_blueprint_tool.__module__ = "tools.blueprint_tools"
        self.mcp.tool()(fake_blueprint_tool)
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}

        payload = json.loads(tools["list_available_tools"](domain="blueprints"))
        names = {tool["name"] for tool in payload["tools"]}

        self.assertTrue(payload["success"])
        self.assertIn("blueprint_asset", payload["resolved_categories"])
        self.assertIn("fake_blueprint_tool", names)
        discovered = next(tool for tool in payload["tools"] if tool["name"] == "fake_blueprint_tool")
        self.assertEqual(discovered["module"], "tools.blueprint_tools")
        self.assertEqual(discovered["parameters"], ["blueprint_name"])

    def test_list_available_tools_rejects_unknown_domain(self):
        tools = {tool.name: tool.fn for tool in self.mcp._tool_manager.list_tools()}

        payload = json.loads(tools["list_available_tools"](domain="not_a_domain"))

        self.assertFalse(payload["success"])
        self.assertEqual(payload["total"], 0)
        self.assertIn("available_categories", payload)


if __name__ == "__main__":
    unittest.main()
