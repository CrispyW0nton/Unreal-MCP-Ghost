from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from toolset_registry import META_TOOL_NAMES, TOOL_CONTRIBUTION_CONTRACT_SCHEMA, ToolsetRegistry


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        name = kwargs.get("name")

        if len(args) == 1 and callable(args[0]) and not kwargs:
            fn = args[0]
            self.tools[getattr(fn, "__name__", "")] = fn
            return fn

        def decorator(fn: Any) -> Any:
            self.tools[name or getattr(fn, "__name__", "")] = fn
            return fn

        return decorator


def _inventory_path() -> Path:
    temp_dir = tempfile.TemporaryDirectory()
    path = Path(temp_dir.name) / "tool_inventory_categories.json"
    path.write_text(
        json.dumps(
            {
                "tools.demo": {
                    "category": "demo_category",
                    "roadmap_phase": "demo_phase",
                    "status": "live",
                    "coverage_note": "Demo tools for registry tests.",
                },
                "tools.other": {
                    "category": "other_category",
                    "roadmap_phase": "demo_phase",
                    "status": "partial",
                },
            }
        ),
        encoding="utf-8",
    )
    _TEMP_DIRS.append(temp_dir)
    return path


_TEMP_DIRS: list[Any] = []


class TestToolsetRegistry(unittest.TestCase):
    def test_collects_and_exposes_direct_tools_by_default(self) -> None:
        registry = ToolsetRegistry(inventory_path=_inventory_path())
        mcp = FakeMCP()
        facade = registry.bind(mcp, expose_direct_tools=True)

        def make_label(ctx: Any, name: str, repeat: int = 1) -> dict[str, Any]:
            """Create a repeated label."""

            return {"success": True, "label": name * repeat, "ctx": ctx}

        make_label.__module__ = "tools.demo"
        facade.tool()(make_label)
        registry.register_meta_tools(mcp)

        self.assertIn("make_label", mcp.tools)
        self.assertTrue(META_TOOL_NAMES.issubset(set(mcp.tools)))

        listing = mcp.tools["list_toolsets"]()
        self.assertIn("tools.demo", listing)
        self.assertIn("demo_category", listing)

        description = json.loads(mcp.tools["describe_toolset"]("tools.demo"))
        self.assertTrue(description["success"])
        self.assertEqual(description["schema"], "unreal_mcp_ghost.toolset_descriptor.v1")
        self.assertEqual(description["category"], "demo_category")
        self.assertEqual(description["tool_count"], 1)
        self.assertEqual(description["metadata"]["status"], "live")
        [tool] = description["tools"]
        self.assertEqual(tool["name"], "make_label")
        self.assertEqual(tool["toolset_name"], "tools.demo")
        self.assertEqual(tool["inputSchema"]["required"], ["name"])
        self.assertNotIn("ctx", tool["inputSchema"]["properties"])
        self.assertEqual(tool["inputSchema"]["properties"]["name"]["type"], "string")
        self.assertEqual(tool["inputSchema"]["properties"]["repeat"]["type"], "integer")

    def test_tool_search_mode_hides_direct_tools_but_dispatches_them(self) -> None:
        registry = ToolsetRegistry(inventory_path=_inventory_path())
        mcp = FakeMCP()
        facade = registry.bind(mcp, expose_direct_tools=False)

        def make_label(ctx: Any, name: str, repeat: int = 1) -> dict[str, Any]:
            return {"success": True, "label": name * repeat, "ctx": ctx}

        make_label.__module__ = "tools.demo"
        facade.tool()(make_label)
        registry.register_meta_tools(mcp)

        self.assertNotIn("make_label", mcp.tools)
        self.assertTrue(META_TOOL_NAMES.issubset(set(mcp.tools)))

        result = asyncio.run(
            mcp.tools["call_tool"](
                toolset_name="tools.demo",
                tool_name="make_label",
                arguments={"name": "A", "repeat": 3},
            )
        )
        self.assertEqual(result, {"success": True, "label": "AAA", "ctx": None})

    def test_call_tool_reports_ambiguous_unqualified_names(self) -> None:
        registry = ToolsetRegistry(inventory_path=_inventory_path())
        mcp = FakeMCP()
        facade = registry.bind(mcp, expose_direct_tools=False)

        def first() -> str:
            return "first"

        def second() -> str:
            return "second"

        first.__name__ = "duplicate"
        first.__module__ = "tools.demo"
        second.__name__ = "duplicate"
        second.__module__ = "tools.other"

        facade.tool()(first)
        facade.tool()(second)
        registry.register_meta_tools(mcp)

        ambiguous = asyncio.run(mcp.tools["call_tool"](tool_name="duplicate"))
        self.assertFalse(ambiguous["success"])
        self.assertIn("ambiguous", ambiguous["error"])
        self.assertEqual(
            sorted(ambiguous["candidates"]),
            ["tools.demo.duplicate", "tools.other.duplicate"],
        )

        resolved = asyncio.run(
            mcp.tools["call_tool"](tool_name="duplicate", toolset_name="tools.other")
        )
        self.assertEqual(resolved, "second")

    def test_call_tool_refuses_meta_tool_self_dispatch(self) -> None:
        registry = ToolsetRegistry(inventory_path=_inventory_path())
        mcp = FakeMCP()
        registry.register_meta_tools(mcp)

        result = asyncio.run(mcp.tools["call_tool"](tool_name="call_tool"))
        contribution_result = asyncio.run(
            mcp.tools["call_tool"](tool_name="tool_contribution_contract")
        )

        self.assertFalse(result["success"])
        self.assertIn("Refusing", result["error"])
        self.assertFalse(contribution_result["success"])
        self.assertIn("Refusing", contribution_result["error"])

    def test_list_toolsets_supports_category_status_and_json_response(self) -> None:
        registry = ToolsetRegistry(inventory_path=_inventory_path())
        mcp = FakeMCP()
        facade = registry.bind(mcp, expose_direct_tools=False)

        def demo_tool() -> str:
            return "demo"

        def other_tool() -> str:
            return "other"

        demo_tool.__module__ = "tools.demo"
        other_tool.__module__ = "tools.other"
        facade.tool()(demo_tool)
        facade.tool()(other_tool)
        registry.register_meta_tools(mcp)

        text = mcp.tools["list_toolsets"](category="demo_category", status="live")
        self.assertIn("tools.demo", text)
        self.assertNotIn("tools.other", text)

        payload = json.loads(mcp.tools["list_toolsets"](
            filter_text="demo",
            category="demo_category",
            response_format="json",
        ))
        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], "unreal_mcp_ghost.toolset_list.v1")
        self.assertEqual(payload["count"], 1)
        [toolset] = payload["toolsets"]
        self.assertEqual(toolset["name"], "tools.demo")
        self.assertEqual(toolset["category"], "demo_category")
        self.assertEqual(toolset["tool_count"], 1)
        self.assertNotIn("tools", toolset)

    def test_describe_toolset_filters_tools(self) -> None:
        registry = ToolsetRegistry(inventory_path=_inventory_path())
        mcp = FakeMCP()
        facade = registry.bind(mcp, expose_direct_tools=False)

        def alpha_tool() -> str:
            """Alpha operation."""
            return "alpha"

        def beta_tool() -> str:
            """Beta operation."""
            return "beta"

        alpha_tool.__module__ = "tools.demo"
        beta_tool.__module__ = "tools.demo"
        facade.tool()(alpha_tool)
        facade.tool()(beta_tool)
        registry.register_meta_tools(mcp)

        payload = json.loads(mcp.tools["describe_toolset"]("tools.demo", tool_filter="alpha"))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["tool_filter"], "alpha")
        self.assertEqual(payload["tool_count"], 1)
        self.assertEqual(payload["tools"][0]["name"], "alpha_tool")

    def test_call_tool_accepts_json_object_string_arguments(self) -> None:
        registry = ToolsetRegistry(inventory_path=_inventory_path())
        mcp = FakeMCP()
        facade = registry.bind(mcp, expose_direct_tools=False)

        def make_label(name: str, repeat: int = 1) -> dict[str, Any]:
            return {"success": True, "label": name * repeat}

        make_label.__module__ = "tools.demo"
        facade.tool()(make_label)
        registry.register_meta_tools(mcp)

        result = asyncio.run(
            registry.call_tool(
                toolset_name="tools.demo",
                tool_name="make_label",
                arguments='{"name": "B", "repeat": 2}',
            )
        )
        self.assertEqual(result, {"success": True, "label": "BB"})

        invalid = asyncio.run(
            registry.call_tool(
                toolset_name="tools.demo",
                tool_name="make_label",
                arguments="[1, 2, 3]",
            )
        )
        self.assertFalse(invalid["success"])
        self.assertIn("JSON must decode to an object", invalid["error"])

    def test_search_tools_returns_stable_descriptors(self) -> None:
        registry = ToolsetRegistry(inventory_path=_inventory_path())
        mcp = FakeMCP()
        facade = registry.bind(mcp, expose_direct_tools=False)

        def make_label(name: str) -> str:
            """Create a repeated label."""
            return name

        make_label.__module__ = "tools.demo"
        facade.tool()(make_label)

        payload = registry.search_tools(query="label", category="demo_category")

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], "unreal_mcp_ghost.tool_search_result.v1")
        self.assertEqual(payload["count"], 1)
        [tool] = payload["tools"]
        self.assertEqual(tool["name"], "make_label")
        self.assertEqual(tool["qualified_name"], "tools.demo.make_label")
        self.assertNotIn("inputSchema", tool)

    def test_tool_contribution_contract_describes_clean_room_invariants(self) -> None:
        registry = ToolsetRegistry(inventory_path=_inventory_path())
        mcp = FakeMCP()
        facade = registry.bind(mcp, expose_direct_tools=False)

        def make_label(name: str) -> str:
            return name

        make_label.__module__ = "tools.demo"
        facade.tool()(make_label)
        registry.register_meta_tools(mcp)

        payload = json.loads(mcp.tools["tool_contribution_contract"]())

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], TOOL_CONTRIBUTION_CONTRACT_SCHEMA)
        self.assertEqual(payload["current_registry"]["toolset_count"], 1)
        self.assertEqual(payload["current_registry"]["tool_count"], 1)
        self.assertIn("tool_contribution_contract", payload["discovery_and_dispatch"]["meta_tools"])
        self.assertIn(
            "decorated_python_tool_module",
            [item["style"] for item in payload["accepted_contribution_styles"]],
        )
        self.assertIn(
            "This is not Epic's module-level C++ AddTool API.",
            payload["unsupported_native_gaps"],
        )
        self.assertIn(
            "Any direct copying of Epic ModelContextProtocol, ToolsetRegistry, GASToolsets, or MCPClientToolset source.",
            payload["legal_review_required"],
        )
        self.assertIn(
            "knowledge_base tools and project context",
            payload["preserved_ghost_differentiators"],
        )

        text = mcp.tools["tool_contribution_contract"](response_format="text")
        self.assertIn("Unreal-MCP-Ghost tool contribution contract", text)
        self.assertIn("unsupported native gaps", text)


if __name__ == "__main__":
    unittest.main()
