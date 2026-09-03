from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

import bridge_descriptor_tools  # noqa: E402
from bridge_descriptor_tools import register_bridge_descriptor_tools  # noqa: E402
from bridge_descriptors import BridgeDescriptorRegistry  # noqa: E402


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


def _sample_registry_path() -> Path:
    temp_dir = tempfile.TemporaryDirectory()
    path = Path(temp_dir.name) / "bridge_command_registry.json"
    path.write_text(
        json.dumps(
            {
                "schema": "unreal_mcp_bridge_command_registry.v1",
                "source_scope": "test",
                "counts": {
                    "commands_total": 3,
                    "cpp_routed": 3,
                    "python_referenced": 2,
                    "cpp_unreferenced_by_python": 1,
                },
                "cpp_unreferenced_review": [
                    {
                        "command": "set_blueprint_parent_class",
                        "recommendation": "needs_python_wrapper",
                        "priority": "high",
                        "rationale": "Class refactor primitive.",
                    }
                ],
                "commands": [
                    {
                        "command": "get_actors_in_level",
                        "category": "general",
                        "status": "routed",
                        "cpp_routes": 1,
                        "python_references": 1,
                        "cpp_sources": [{"path": "Bridge.cpp", "line": 10}],
                        "python_sources": [{"path": "editor_tools.py", "line": 20}],
                    },
                    {
                        "command": "spawn_actor",
                        "category": "general",
                        "status": "routed",
                        "cpp_routes": 1,
                        "python_references": 1,
                        "cpp_sources": [{"path": "Bridge.cpp", "line": 11}],
                        "python_sources": [{"path": "editor_tools.py", "line": 21}],
                    },
                    {
                        "command": "set_blueprint_parent_class",
                        "category": "blueprint",
                        "status": "cpp_only",
                        "cpp_routes": 1,
                        "python_references": 0,
                        "cpp_sources": [{"path": "Bridge.cpp", "line": 12}],
                        "python_sources": [],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    _TEMP_DIRS.append(temp_dir)
    return path


_TEMP_DIRS: list[Any] = []


class TestBridgeDescriptors(unittest.TestCase):
    def test_summary_and_toolset_listing(self) -> None:
        registry = BridgeDescriptorRegistry(_sample_registry_path())

        summary = registry.summary()
        self.assertTrue(summary["success"])
        self.assertEqual(summary["schema"], "unreal_mcp_ghost.bridge_descriptor_summary.v1")
        self.assertEqual(summary["counts"]["commands_total"], 3)
        self.assertEqual(summary["category_counts"], {"blueprint": 1, "general": 2})
        self.assertEqual(summary["mutation_class_counts"]["read_only"], 1)
        self.assertEqual(summary["mutation_class_counts"]["editor_mutation"], 2)

        listing = json.loads(registry.list_toolsets(response_format="json"))
        self.assertTrue(listing["success"])
        self.assertEqual(listing["count"], 2)
        names = {item["name"] for item in listing["toolsets"]}
        self.assertEqual(names, {"bridge.blueprint", "bridge.general"})

    def test_describe_toolset_carries_review_and_sources(self) -> None:
        registry = BridgeDescriptorRegistry(_sample_registry_path())

        payload = json.loads(registry.describe_toolset("bridge.blueprint"))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], "unreal_mcp_ghost.bridge_toolset_descriptor.v1")
        self.assertEqual(payload["name"], "bridge.blueprint")
        self.assertEqual(payload["command_count"], 1)
        [command] = payload["commands"]
        self.assertEqual(command["qualified_name"], "bridge.blueprint.set_blueprint_parent_class")
        self.assertEqual(command["mutation_class"], "editor_mutation")
        self.assertEqual(command["review"]["priority"], "high")
        self.assertEqual(command["cpp_sources"][0]["path"], "Bridge.cpp")

    def test_search_commands_filters_by_category_and_mutation(self) -> None:
        registry = BridgeDescriptorRegistry(_sample_registry_path())

        read_only = registry.search_commands(category="general", mutation_class="read_only")
        self.assertTrue(read_only["success"])
        self.assertEqual(read_only["count"], 1)
        self.assertEqual(read_only["commands"][0]["command"], "get_actors_in_level")
        self.assertNotIn("cpp_sources", read_only["commands"][0])

        with_sources = registry.search_commands(query="parent", include_sources=True)
        self.assertEqual(with_sources["count"], 1)
        self.assertIn("cpp_sources", with_sources["commands"][0])

    def test_command_call_plan_blocks_mutations_by_default(self) -> None:
        registry = BridgeDescriptorRegistry(_sample_registry_path())

        plan = registry.command_call_plan(
            command_name="bridge.general.spawn_actor",
            params={"name": "BP_Test"},
            dry_run=False,
        )

        self.assertFalse(plan["success"])
        self.assertFalse(plan["will_execute"])
        self.assertIn("allow_mutation=true", plan["error"])
        self.assertEqual(plan["descriptor"]["mutation_class"], "editor_mutation")

    def test_command_call_plan_allows_read_only_execution_plan(self) -> None:
        registry = BridgeDescriptorRegistry(_sample_registry_path())

        plan = registry.command_call_plan(
            command_name="bridge.general.get_actors_in_level",
            params={"limit": 5},
            dry_run=False,
        )

        self.assertTrue(plan["success"])
        self.assertTrue(plan["will_execute"])
        self.assertEqual(plan["command"], "get_actors_in_level")
        self.assertEqual(plan["descriptor"]["mutation_class"], "read_only")

    def test_mcp_tools_return_json_payloads(self) -> None:
        mcp = FakeMCP()
        register_bridge_descriptor_tools(mcp)
        registry_path = str(_sample_registry_path())

        summary = json.loads(mcp.tools["bridge_descriptor_summary"](ctx=None, registry_path=registry_path))
        self.assertTrue(summary["success"])

        listed = json.loads(mcp.tools["list_bridge_toolsets"](
            ctx=None,
            registry_path=registry_path,
            response_format="json",
        ))
        self.assertEqual(listed["count"], 2)

        described = json.loads(mcp.tools["describe_bridge_toolset"](
            ctx=None,
            registry_path=registry_path,
            toolset_name="general",
            command_filter="spawn",
        ))
        self.assertEqual(described["filtered_command_count"], 1)
        self.assertEqual(described["commands"][0]["command"], "spawn_actor")

        searched = json.loads(mcp.tools["search_bridge_commands"](
            ctx=None,
            registry_path=registry_path,
            query="parent",
            limit=5,
        ))
        self.assertEqual(searched["count"], 1)

        planned = json.loads(mcp.tools["call_bridge_command"](
            ctx=None,
            registry_path=registry_path,
            command_name="bridge.general.get_actors_in_level",
            params_json='{"limit": 5}',
        ))
        self.assertTrue(planned["success"])
        self.assertTrue(planned["dry_run"])
        self.assertFalse(planned["will_execute"])
        self.assertEqual(planned["params"], {"limit": 5})

    def test_call_bridge_command_executes_only_after_gates_pass(self) -> None:
        mcp = FakeMCP()
        register_bridge_descriptor_tools(mcp)
        registry_path = str(_sample_registry_path())

        with patch.object(
            bridge_descriptor_tools,
            "_send_bridge_command",
            return_value={"success": True, "status": "ok", "actors": []},
        ) as send:
            executed = json.loads(mcp.tools["call_bridge_command"](
                ctx=None,
                registry_path=registry_path,
                command_name="get_actors_in_level",
                params={"limit": 10},
                dry_run=False,
            ))

        self.assertTrue(executed["success"])
        self.assertFalse(executed["dry_run"])
        self.assertTrue(executed["will_execute"])
        self.assertEqual(executed["execution"]["status"], "ok")
        send.assert_called_once_with("get_actors_in_level", {"limit": 10})

    def test_call_bridge_command_rejects_invalid_json_params(self) -> None:
        mcp = FakeMCP()
        register_bridge_descriptor_tools(mcp)
        payload = json.loads(mcp.tools["call_bridge_command"](
            ctx=None,
            registry_path=str(_sample_registry_path()),
            command_name="get_actors_in_level",
            params_json="[1, 2, 3]",
        ))

        self.assertFalse(payload["success"])
        self.assertIn("JSON object", payload["error"])


if __name__ == "__main__":
    unittest.main()
