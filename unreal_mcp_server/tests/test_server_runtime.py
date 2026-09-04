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

from server_runtime import (  # noqa: E402
    SERVER_LIFECYCLE_SCHEMA,
    SERVER_METADATA_REFRESH_SCHEMA,
    SERVER_OPERATION_CANCEL_SCHEMA,
    SERVER_OPERATION_LIST_SCHEMA,
    SERVER_OPERATION_STATUS_SCHEMA,
    SERVER_PROTOCOL_CONTRACT_SCHEMA,
    SERVER_TRANSPORT_DIAGNOSTICS_SCHEMA,
    ServerRuntimeState,
    bridge_response_succeeded,
    is_loopback_http_host,
)
from toolset_registry import ToolsetRegistry  # noqa: E402
from server_runtime_tools import register_server_runtime_tools  # noqa: E402


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


def _inventory_path(category: str = "runtime_demo") -> Path:
    temp_dir = tempfile.TemporaryDirectory()
    path = Path(temp_dir.name) / "tool_inventory_categories.json"
    path.write_text(
        json.dumps(
            {
                "tools.runtime_demo": {
                    "category": category,
                    "roadmap_phase": "native_mcp_alignment",
                    "status": "live",
                },
            }
        ),
        encoding="utf-8",
    )
    _TEMP_DIRS.append(temp_dir)
    return path


def _registry(path: Path) -> ToolsetRegistry:
    registry = ToolsetRegistry(inventory_path=path)

    def runtime_demo_tool() -> str:
        return "ok"

    runtime_demo_tool.__module__ = "tools.runtime_demo"
    registry.register_tool(runtime_demo_tool)
    return registry


_TEMP_DIRS: list[Any] = []


class TestServerRuntime(unittest.TestCase):
    def test_http_bind_and_bridge_response_safety_helpers(self) -> None:
        self.assertTrue(is_loopback_http_host("127.0.0.1"))
        self.assertTrue(is_loopback_http_host("::1"))
        self.assertTrue(is_loopback_http_host("localhost"))
        self.assertFalse(is_loopback_http_host("0.0.0.0"))
        self.assertFalse(is_loopback_http_host("192.168.1.25"))
        self.assertTrue(bridge_response_succeeded({"status": "success", "result": {}}))
        self.assertFalse(bridge_response_succeeded({"status": "error", "error": "not ready"}))
        self.assertFalse(bridge_response_succeeded({"success": False, "message": "failed"}))
        self.assertFalse(bridge_response_succeeded(None))

    def test_lifecycle_snapshot_reports_transport_bridge_and_catalog(self) -> None:
        state = ServerRuntimeState()
        state.attach_toolset_registry(_registry(_inventory_path()))
        state.configure(
            transport="streamable-http",
            mcp_host="127.0.0.1",
            mcp_port=9001,
            unreal_host="127.0.0.1",
            unreal_port=55655,
            tool_search_mode=True,
            direct_tools_enabled=False,
        )
        state.mark_starting("test startup")
        state.record_unreal_connection(connected=False, detail="offline for unit test")
        state.record_warmup(attempted=True, success=False, detail="no editor")
        operation_id = state.begin_operation(
            tool_name="demo",
            toolset_name="tools.runtime_demo",
            qualified_name="tools.runtime_demo.demo",
        )
        state.record_operation_progress(operation_id, stage="testing", message="Unit test progress.", percent=0.5)
        state.mark_running("ready")

        payload = state.lifecycle_snapshot()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], SERVER_LIFECYCLE_SCHEMA)
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["transport"]["active"], "streamable-http")
        self.assertEqual(payload["transport"]["streamable_http_url"], "http://127.0.0.1:9001/mcp")
        self.assertFalse(payload["unreal_bridge"]["connected"])
        self.assertEqual(payload["tool_catalog"]["toolset_count"], 1)
        self.assertEqual(payload["tool_catalog"]["tool_count"], 1)
        self.assertEqual(payload["tool_catalog"]["mode"], "tool_search_only")
        self.assertEqual(payload["operations"]["active_count"], 1)
        self.assertIn("legal_review_required", payload)

    def test_transport_diagnostics_preserves_ghost_compatibility_and_flags_gaps(self) -> None:
        state = ServerRuntimeState()
        state.configure(transport="sse", sse_tunnel_compatibility=True)

        payload = state.transport_diagnostics()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], SERVER_TRANSPORT_DIAGNOSTICS_SCHEMA)
        self.assertEqual(payload["active_transport"], "sse")
        self.assertIn("streamable-http", payload["supported_transports"])
        self.assertTrue(payload["security_posture"]["sse_tunnel_compatibility"])
        self.assertIn("knowledge_base tools and resources", payload["compatibility_preserved"])
        self.assertIn("Ghost is not yet an Unreal Editor native HTTP MCP server.", payload["native_gaps"])
        self.assertEqual(payload["operation_behavior"]["cancellation_scope"], "cooperative request flag; running TCP bridge commands are not preempted")

    def test_protocol_contract_describes_session_origin_and_parity_boundaries(self) -> None:
        state = ServerRuntimeState()
        state.configure(
            transport="streamable-http",
            mcp_host="127.0.0.1",
            mcp_port=8123,
            tool_search_mode=True,
            sse_tunnel_compatibility=True,
        )

        payload = state.protocol_contract()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], SERVER_PROTOCOL_CONTRACT_SCHEMA)
        self.assertEqual(payload["active_transport"], "streamable-http")
        self.assertEqual(payload["endpoints"]["streamable_http"]["url"], "http://127.0.0.1:8123/mcp")
        self.assertEqual(payload["endpoints"]["streamable_http"]["recommended_local_url"], "http://127.0.0.1:8123/mcp")
        self.assertIn("FastMCP", " ".join(payload["contract_scope"]["delegated_to_fastmcp"]))
        self.assertEqual(payload["request_headers"]["mcp_session_id"]["header"], "Mcp-Session-Id")
        self.assertEqual(payload["request_headers"]["origin"]["header"], "Origin")
        self.assertEqual(payload["request_headers"]["protocol_version"]["header"], "MCP-Protocol-Version")
        self.assertTrue(payload["json_rpc_surface"]["tool_listing_modes"]["tool_search_only"])
        self.assertIn("tool_contribution_contract", payload["json_rpc_surface"]["tool_listing_modes"]["meta_tools"])
        self.assertIn("server_cancel_operation", payload["streaming_and_cancellation"]["operation_lookup"])
        self.assertIn("knowledge_base resources and project workflows", payload["compatibility_preserved"])
        self.assertIn("Epic private Mcp-Session-Id store", payload["native_parity_not_claimed"])
        self.assertIn("Any direct embedding of Epic ModelContextProtocol or ToolsetRegistry source.", payload["legal_review_required"])

    def test_refresh_metadata_reloads_registry_inventory_without_reregistering_tools(self) -> None:
        path = _inventory_path(category="old_runtime")
        registry = _registry(path)
        state = ServerRuntimeState()
        state.attach_toolset_registry(registry)

        path.write_text(
            json.dumps(
                {
                    "tools.runtime_demo": {
                        "category": "new_runtime",
                        "roadmap_phase": "native_mcp_alignment",
                        "status": "partial",
                    },
                }
            ),
            encoding="utf-8",
        )

        payload = state.refresh_metadata(dry_run=False)
        described = json.loads(registry.describe_toolset("tools.runtime_demo"))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], SERVER_METADATA_REFRESH_SCHEMA)
        self.assertEqual(payload["tool_inventory"]["tool_count"], 1)
        self.assertEqual(described["category"], "new_runtime")
        self.assertEqual(described["status"], "partial")

    def test_operation_list_status_cancel_and_registry_tracking(self) -> None:
        path = _inventory_path(category="runtime_ops")
        registry = _registry(path)
        state = ServerRuntimeState()
        state.attach_toolset_registry(registry)
        registry.attach_runtime_state(state)

        result = asyncio.run(
            registry.call_tool(
                tool_name="runtime_demo_tool",
                toolset_name="tools.runtime_demo",
                arguments={},
            )
        )
        self.assertEqual(result, "ok")

        operations = state.list_operations(include_completed=True)
        self.assertEqual(operations["schema"], SERVER_OPERATION_LIST_SCHEMA)
        self.assertEqual(operations["count"], 1)
        [operation] = operations["operations"]
        self.assertEqual(operation["status"], "completed")
        self.assertEqual(operation["qualified_name"], "tools.runtime_demo.runtime_demo_tool")

        status = state.operation_status(operation["operation_id"])
        self.assertTrue(status["success"])
        self.assertEqual(status["schema"], SERVER_OPERATION_STATUS_SCHEMA)
        self.assertEqual(status["result_summary"]["type"], "str")
        self.assertGreaterEqual(len(status["progress"]), 3)

        cancel = state.request_operation_cancel(operation["operation_id"], reason="unit test")
        self.assertTrue(cancel["success"])
        self.assertEqual(cancel["schema"], SERVER_OPERATION_CANCEL_SCHEMA)
        self.assertFalse(cancel["accepted"])
        cancelled_status = state.operation_status(operation["operation_id"])
        self.assertTrue(cancelled_status["cancellation"]["requested"])

    def test_mcp_tool_wrappers_return_json_payloads(self) -> None:
        mcp = FakeMCP()
        register_server_runtime_tools(mcp)

        self.assertEqual(
            set(mcp.tools),
            {
                "server_lifecycle_status",
                "server_transport_diagnostics",
                "server_protocol_contract",
                "server_refresh_metadata",
                "server_list_operations",
                "server_operation_status",
                "server_cancel_operation",
            },
        )

        lifecycle = json.loads(mcp.tools["server_lifecycle_status"](ctx=None))
        diagnostics = json.loads(mcp.tools["server_transport_diagnostics"](ctx=None))
        contract = json.loads(mcp.tools["server_protocol_contract"](ctx=None))
        dry_refresh = json.loads(mcp.tools["server_refresh_metadata"](ctx=None, dry_run=True))
        operations = json.loads(mcp.tools["server_list_operations"](ctx=None, include_completed=True))
        missing_status = json.loads(mcp.tools["server_operation_status"](ctx=None, operation_id="missing"))
        missing_cancel = json.loads(mcp.tools["server_cancel_operation"](ctx=None, operation_id="missing"))

        self.assertEqual(lifecycle["schema"], SERVER_LIFECYCLE_SCHEMA)
        self.assertEqual(diagnostics["schema"], SERVER_TRANSPORT_DIAGNOSTICS_SCHEMA)
        self.assertEqual(contract["schema"], SERVER_PROTOCOL_CONTRACT_SCHEMA)
        self.assertEqual(dry_refresh["schema"], SERVER_METADATA_REFRESH_SCHEMA)
        self.assertEqual(operations["schema"], SERVER_OPERATION_LIST_SCHEMA)
        self.assertEqual(missing_status["schema"], SERVER_OPERATION_STATUS_SCHEMA)
        self.assertEqual(missing_cancel["schema"], SERVER_OPERATION_CANCEL_SCHEMA)


if __name__ == "__main__":
    unittest.main()
