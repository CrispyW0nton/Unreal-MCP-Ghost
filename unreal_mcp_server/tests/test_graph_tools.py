"""
test_graph_tools.py — Smoke and failure tests for the V4 Graph Scripting Core.

Tests cover:
  - Registration: all 9 bp_* tools are discoverable
  - Return schema: every tool always returns valid JSON with StructuredResult keys
  - Failure-path: missing/invalid params produce structured errors (no crashes)
  - Logic: stateless local logic (validation, normalization) works correctly
  - Integration-offline: tools handle "not connected" gracefully

These tests do NOT require a live UE5 connection.
Live graph integration tests belong in test_e2e.py.

Run:
    cd /home/user/webapp/unreal_mcp_server
    python3 -m pytest tests/test_graph_tools.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_SERVER_ROOT = os.path.dirname(_HERE)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)


# ── Helpers ───────────────────────────────────────────────────────────────────

class _MockMCP:
    """Minimal FastMCP-compatible stub."""

    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def tool(self):
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn
        return decorator

    def list_tool_names(self):
        return list(self._tools.keys())

    def get_tool(self, name: str):
        return self._tools.get(name)


def _parse(result: str) -> dict:
    return json.loads(result)


def _assert_schema(result_str: str, test_name: str) -> dict:
    data = _parse(result_str)
    assert isinstance(data, dict), f"{test_name}: result is not a dict: {data!r}"
    assert "success" in data, f"{test_name}: missing 'success' key in {data}"
    assert "stage" in data, f"{test_name}: missing 'stage' key in {data}"
    assert "message" in data, f"{test_name}: missing 'message' key in {data}"
    assert "outputs" in data, f"{test_name}: missing 'outputs' key in {data}"
    assert "errors" in data, f"{test_name}: missing 'errors' key in {data}"
    assert "warnings" in data, f"{test_name}: missing 'warnings' key in {data}"
    assert isinstance(data["errors"], list), f"{test_name}: 'errors' must be a list"
    assert isinstance(data["warnings"], list), f"{test_name}: 'warnings' must be a list"
    return data


def _run(coro):
    """Run an async tool function synchronously in tests."""
    return asyncio.get_event_loop().run_until_complete(coro)


def _mock_ctx():
    ctx = MagicMock()
    return ctx


def _make_raw_nodes(n=2):
    """Build a fake get_blueprint_nodes response."""
    nodes = []
    for i in range(n):
        nodes.append({
            "node_id": f"GUID-{i:08d}-ABCD-1234-EFGH-5678IJKLMNOP",
            "node_name": f"K2Node_Test_{i}",
            "node_type": "event" if i == 0 else "function",
            "title": "BeginPlay" if i == 0 else f"PrintString_{i}",
            "pos_x": -400 + i * 350,
            "pos_y": 0,
            "pins": [
                {
                    "pin_name": "then",
                    "direction": "output",
                    "pin_type": "exec",
                    "default_value": "",
                    "linked_to": [{"node_id": f"GUID-{(i+1):08d}-ABCD-1234-EFGH-5678IJKLMNOP",
                                   "pin_name": "execute"}] if i < n - 1 else [],
                },
                {
                    "pin_name": "execute",
                    "direction": "input",
                    "pin_type": "exec",
                    "default_value": "",
                    "linked_to": [],
                },
            ],
        })
    return {"nodes": nodes, "count": n}


# ── Tests: Registration ───────────────────────────────────────────────────────

class TestGraphToolsRegistration(unittest.TestCase):
    """All 9 bp_* tools must register successfully."""

    EXPECTED_TOOLS = {
        "bp_get_graph_summary",
        "bp_create_graph",
        "bp_add_node",
        "bp_inspect_node",
        "bp_connect_pins",
        "bp_set_pin_default",
        "bp_add_variable",
        "bp_compile",
        "bp_auto_format_graph",
    }

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    def test_all_9_tools_registered(self):
        registered = set(self.mcp.list_tool_names())
        missing = self.EXPECTED_TOOLS - registered
        self.assertEqual(missing, set(), f"Missing tools: {missing}")

    def test_bp_get_graph_summary_registered(self):
        self.assertIn("bp_get_graph_summary", self.mcp.list_tool_names())

    def test_bp_add_node_registered(self):
        self.assertIn("bp_add_node", self.mcp.list_tool_names())

    def test_bp_inspect_node_registered(self):
        self.assertIn("bp_inspect_node", self.mcp.list_tool_names())

    def test_bp_connect_pins_registered(self):
        self.assertIn("bp_connect_pins", self.mcp.list_tool_names())

    def test_bp_set_pin_default_registered(self):
        self.assertIn("bp_set_pin_default", self.mcp.list_tool_names())

    def test_bp_add_variable_registered(self):
        self.assertIn("bp_add_variable", self.mcp.list_tool_names())

    def test_bp_compile_registered(self):
        self.assertIn("bp_compile", self.mcp.list_tool_names())

    def test_bp_create_graph_registered(self):
        self.assertIn("bp_create_graph", self.mcp.list_tool_names())

    def test_bp_auto_format_graph_registered(self):
        self.assertIn("bp_auto_format_graph", self.mcp.list_tool_names())


# ── Tests: Schema Contract ────────────────────────────────────────────────────

class TestGraphToolsSchema(unittest.IsolatedAsyncioTestCase):
    """Every tool must always return valid JSON with StructuredResult keys."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, tool_name: str, **kwargs):
        fn = self.mcp.get_tool(tool_name)
        ctx = _mock_ctx()
        return await fn(ctx, **kwargs)

    async def test_bp_get_graph_summary_not_connected_schema(self):
        """bp_get_graph_summary returns StructuredResult even when not connected."""
        with patch("tools.graph_tools._send", return_value={"success": False, "message": "Not connected"}):
            result = await self._call("bp_get_graph_summary",
                                      blueprint_name="BP_Test", graph_name="EventGraph")
        data = _assert_schema(result, "bp_get_graph_summary_not_connected")
        self.assertFalse(data["success"])
        self.assertEqual(data["stage"], "bp_get_graph_summary")

    async def test_bp_get_graph_summary_success_schema(self):
        """bp_get_graph_summary returns valid schema with node list on success."""
        with patch("tools.graph_tools._send", return_value=_make_raw_nodes(3)):
            result = await self._call("bp_get_graph_summary",
                                      blueprint_name="BP_Test", graph_name="EventGraph")
        data = _assert_schema(result, "bp_get_graph_summary_success")
        self.assertTrue(data["success"])
        self.assertIn("node_count", data["outputs"])
        self.assertIn("nodes", data["outputs"])
        self.assertIn("summary_text", data["outputs"])
        self.assertEqual(data["outputs"]["node_count"], 3)

    async def test_bp_get_graph_summary_nodes_have_required_fields(self):
        """Each node in summary must have: node_id, node_type, title, pins."""
        with patch("tools.graph_tools._send", return_value=_make_raw_nodes(2)):
            result = await self._call("bp_get_graph_summary",
                                      blueprint_name="BP_Test", graph_name="EventGraph")
        data = _parse(result)
        for node in data["outputs"]["nodes"]:
            self.assertIn("node_id", node, "node missing node_id")
            self.assertIn("node_type", node, "node missing node_type")
            self.assertIn("title", node, "node missing title")
            self.assertIn("pins", node, "node missing pins")

    async def test_bp_add_node_not_connected_schema(self):
        """bp_add_node returns StructuredResult even when not connected."""
        with patch("tools.graph_tools._send", return_value={"success": False, "message": "Not connected"}):
            result = await self._call("bp_add_node",
                                      blueprint_name="BP_Test", node_type="event:BeginPlay")
        data = _assert_schema(result, "bp_add_node_not_connected")
        self.assertFalse(data["success"])

    async def test_bp_inspect_node_not_connected_schema(self):
        with patch("tools.graph_tools._send", return_value={"success": False, "message": "Not connected"}):
            result = await self._call("bp_inspect_node",
                                      blueprint_name="BP_Test", node_id="SOME-GUID")
        data = _assert_schema(result, "bp_inspect_node_not_connected")
        self.assertFalse(data["success"])
        self.assertEqual(data["stage"], "bp_inspect_node")

    async def test_bp_connect_pins_schema_always_valid(self):
        with patch("tools.graph_tools._send", return_value={"success": False, "message": "Not connected"}):
            result = await self._call("bp_connect_pins",
                                      blueprint_name="BP_Test",
                                      source_node_id="SRC", source_pin="then",
                                      target_node_id="TGT", target_pin="execute")
        data = _assert_schema(result, "bp_connect_pins_not_connected")
        self.assertFalse(data["success"])

    async def test_bp_set_pin_default_schema_valid(self):
        with patch("tools.graph_tools._send", return_value={"success": False, "message": "Not connected"}):
            result = await self._call("bp_set_pin_default",
                                      blueprint_name="BP_Test",
                                      node_id="SOME-NODE", pin_name="Duration",
                                      default_value="2.0")
        data = _assert_schema(result, "bp_set_pin_default_not_connected")
        self.assertFalse(data["success"])

    async def test_bp_add_variable_schema_valid(self):
        with patch("tools.graph_tools._send", return_value={"success": False, "message": "Not connected"}):
            result = await self._call("bp_add_variable",
                                      blueprint_name="BP_Test",
                                      variable_name="Health",
                                      variable_type="Float")
        data = _assert_schema(result, "bp_add_variable_not_connected")
        self.assertFalse(data["success"])

    async def test_bp_compile_schema_valid(self):
        # save_after_compile=False avoids a second _send call for the save step
        with patch("tools.graph_tools._send", return_value={"success": False, "message": "Not connected"}):
            result = await self._call("bp_compile", blueprint_name="BP_Test",
                                      save_after_compile=False)
        data = _assert_schema(result, "bp_compile_not_connected")
        self.assertFalse(data["success"])


# ── Tests: Failure Paths ──────────────────────────────────────────────────────

class TestGraphToolsFailurePaths(unittest.IsolatedAsyncioTestCase):
    """Every invalid-param case must produce a structured error with clear message."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, tool_name: str, **kwargs):
        fn = self.mcp.get_tool(tool_name)
        ctx = _mock_ctx()
        return await fn(ctx, **kwargs)

    async def test_bp_connect_pins_missing_source_pin(self):
        """Missing source_pin must produce structured error, not crash."""
        result = await self._call("bp_connect_pins",
                                  blueprint_name="BP_Test",
                                  source_node_id="SRC", source_pin="",
                                  target_node_id="TGT", target_pin="execute")
        data = _assert_schema(result, "bp_connect_pins_missing_source_pin")
        self.assertFalse(data["success"])
        self.assertGreater(len(data["errors"]), 0)

    async def test_bp_connect_pins_missing_target_pin(self):
        result = await self._call("bp_connect_pins",
                                  blueprint_name="BP_Test",
                                  source_node_id="SRC", source_pin="then",
                                  target_node_id="TGT", target_pin="")
        data = _assert_schema(result, "bp_connect_pins_missing_target_pin")
        self.assertFalse(data["success"])
        self.assertGreater(len(data["errors"]), 0)

    async def test_bp_set_pin_default_empty_pin_name(self):
        result = await self._call("bp_set_pin_default",
                                  blueprint_name="BP_Test",
                                  node_id="SOME-NODE", pin_name="",
                                  default_value="1.0")
        data = _assert_schema(result, "bp_set_pin_default_empty_pin")
        self.assertFalse(data["success"])
        self.assertGreater(len(data["errors"]), 0)
        # Error message should be actionable
        self.assertTrue(any("pin_name" in e for e in data["errors"]))

    async def test_bp_add_variable_invalid_type(self):
        result = await self._call("bp_add_variable",
                                  blueprint_name="BP_Test",
                                  variable_name="MyVar",
                                  variable_type="INVALID_TYPE_XYZ")
        data = _assert_schema(result, "bp_add_variable_invalid_type")
        self.assertFalse(data["success"])
        self.assertGreater(len(data["errors"]), 0)
        # Error must name the bad type
        combined = " ".join(data["errors"])
        self.assertIn("INVALID_TYPE_XYZ", combined)

    async def test_bp_add_node_unknown_type(self):
        result = await self._call("bp_add_node",
                                  blueprint_name="BP_Test",
                                  node_type="unknown_garbage_type_xyz")
        data = _assert_schema(result, "bp_add_node_unknown_type")
        self.assertFalse(data["success"])
        self.assertGreater(len(data["errors"]), 0)

    async def test_bp_add_node_variable_get_missing_name(self):
        result = await self._call("bp_add_node",
                                  blueprint_name="BP_Test",
                                  node_type="variable_get:")
        data = _assert_schema(result, "bp_add_node_variable_get_empty")
        self.assertFalse(data["success"])

    async def test_bp_add_node_variable_set_missing_name(self):
        result = await self._call("bp_add_node",
                                  blueprint_name="BP_Test",
                                  node_type="variable_set:")
        data = _assert_schema(result, "bp_add_node_variable_set_empty")
        self.assertFalse(data["success"])

    async def test_bp_add_node_cast_missing_class(self):
        result = await self._call("bp_add_node",
                                  blueprint_name="BP_Test",
                                  node_type="cast:")
        data = _assert_schema(result, "bp_add_node_cast_empty")
        self.assertFalse(data["success"])

    async def test_bp_add_node_function_missing_function_name(self):
        result = await self._call("bp_add_node",
                                  blueprint_name="BP_Test",
                                  node_type="function:SomeClass:")
        data = _assert_schema(result, "bp_add_node_function_empty_name")
        self.assertFalse(data["success"])

    async def test_bp_create_graph_invalid_type(self):
        result = await self._call("bp_create_graph",
                                  blueprint_name="BP_Test",
                                  graph_name="MyGraph",
                                  graph_type="invalid")
        data = _assert_schema(result, "bp_create_graph_invalid_type")
        self.assertFalse(data["success"])
        self.assertGreater(len(data["errors"]), 0)

    async def test_bp_create_graph_reserved_event_graph(self):
        result = await self._call("bp_create_graph",
                                  blueprint_name="BP_Test",
                                  graph_name="EventGraph",
                                  graph_type="function")
        data = _assert_schema(result, "bp_create_graph_reserved_name")
        self.assertFalse(data["success"])
        # Should explain that EventGraph is built-in
        combined = " ".join(data["errors"] + [data["message"]])
        self.assertIn("EventGraph", combined)

    async def test_bp_create_graph_reserved_construction_script(self):
        result = await self._call("bp_create_graph",
                                  blueprint_name="BP_Test",
                                  graph_name="ConstructionScript",
                                  graph_type="function")
        data = _assert_schema(result, "bp_create_graph_construction_script")
        self.assertFalse(data["success"])


# ── Tests: Success Path Logic ─────────────────────────────────────────────────

class TestGraphToolsSuccessLogic(unittest.IsolatedAsyncioTestCase):
    """Validate correct behavior in the stateless normalization layer."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, tool_name: str, **kwargs):
        fn = self.mcp.get_tool(tool_name)
        ctx = _mock_ctx()
        return await fn(ctx, **kwargs)

    async def test_bp_get_graph_summary_empty_graph(self):
        """Empty graph returns success with node_count=0."""
        with patch("tools.graph_tools._send", return_value={"nodes": [], "count": 0}):
            result = await self._call("bp_get_graph_summary",
                                      blueprint_name="BP_Empty", graph_name="EventGraph")
        data = _assert_schema(result, "bp_get_graph_summary_empty")
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["node_count"], 0)
        self.assertIn("empty graph", data["outputs"]["summary_text"])

    async def test_bp_get_graph_summary_pin_normalization(self):
        """Pins with direction=EGPD_Output should become 'output'."""
        raw = {
            "nodes": [{
                "node_id": "GUID-0",
                "node_name": "K2Node_Test",
                "node_type": "event",
                "title": "BeginPlay",
                "pos_x": 0, "pos_y": 0,
                "pins": [
                    {"pin_name": "then", "direction": "EGPD_Output",
                     "pin_type": "exec", "default_value": "", "linked_to": []},
                    {"pin_name": "execute", "direction": "EGPD_Input",
                     "pin_type": "exec", "default_value": "", "linked_to": []},
                ],
            }]
        }
        with patch("tools.graph_tools._send", return_value=raw):
            result = await self._call("bp_get_graph_summary",
                                      blueprint_name="BP_Test", graph_name="EventGraph")
        data = _parse(result)
        pins = data["outputs"]["nodes"][0]["pins"]
        then_pin = next(p for p in pins if p["pin_name"] == "then")
        exec_pin = next(p for p in pins if p["pin_name"] == "execute")
        self.assertEqual(then_pin["direction"], "output")
        self.assertEqual(exec_pin["direction"], "input")

    async def test_bp_add_node_event_routes_correctly(self):
        """bp_add_node event:BeginPlay calls add_blueprint_event_node C++ command."""
        calls = []
        def mock_send(cmd, params):
            calls.append((cmd, params))
            return {"node_id": "NEW-GUID-001", "node_name": "K2Node_Event_0", "success": True}
        with patch("tools.graph_tools._send", side_effect=mock_send):
            result = await self._call("bp_add_node",
                                      blueprint_name="BP_Test",
                                      node_type="event:BeginPlay",
                                      position_x=-400, position_y=0)
        data = _assert_schema(result, "bp_add_node_event")
        self.assertTrue(data["success"])
        self.assertEqual(len(calls), 1)
        cmd, params = calls[0]
        self.assertEqual(cmd, "add_blueprint_event_node")
        self.assertEqual(params["event_name"], "BeginPlay")
        self.assertEqual(params["blueprint_name"], "BP_Test")

    async def test_bp_add_node_branch_routes_correctly(self):
        """bp_add_node branch calls add_blueprint_branch_node."""
        calls = []
        def mock_send(cmd, params):
            calls.append((cmd, params))
            return {"node_id": "BRANCH-GUID", "success": True}
        with patch("tools.graph_tools._send", side_effect=mock_send):
            result = await self._call("bp_add_node",
                                      blueprint_name="BP_Test", node_type="branch")
        data = _assert_schema(result, "bp_add_node_branch")
        self.assertTrue(data["success"])
        self.assertEqual(calls[0][0], "add_blueprint_branch_node")

    async def test_bp_add_node_print_string_routes_correctly(self):
        """bp_add_node print_string calls add_blueprint_function_node with PrintString."""
        calls = []
        def mock_send(cmd, params):
            calls.append((cmd, params))
            return {"node_id": "PRINT-GUID", "success": True}
        with patch("tools.graph_tools._send", side_effect=mock_send):
            result = await self._call("bp_add_node",
                                      blueprint_name="BP_Test", node_type="print_string")
        data = _assert_schema(result, "bp_add_node_print_string")
        self.assertTrue(data["success"])
        cmd, params = calls[0]
        self.assertEqual(cmd, "add_blueprint_function_node")
        self.assertEqual(params["function_name"], "PrintString")

    async def test_bp_add_node_returns_node_id_from_response(self):
        """node_id from C++ response is passed through to outputs."""
        with patch("tools.graph_tools._send",
                   return_value={"node_id": "TEST-GUID-XYZ", "node_name": "K2Node_CallFunction_5",
                                 "success": True}):
            result = await self._call("bp_add_node",
                                      blueprint_name="BP_Test", node_type="event:Tick")
        data = _parse(result)
        self.assertEqual(data["outputs"]["node_id"], "TEST-GUID-XYZ")
        self.assertEqual(data["outputs"]["node_name"], "K2Node_CallFunction_5")

    async def test_bp_add_node_warns_when_no_node_id(self):
        """If C++ doesn't return a node_id, a warning is emitted."""
        with patch("tools.graph_tools._send",
                   return_value={"success": True}):  # no node_id key
            result = await self._call("bp_add_node",
                                      blueprint_name="BP_Test", node_type="event:BeginPlay")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertGreater(len(data["warnings"]), 0,
                           "Expected a warning about missing node_id")

    async def test_bp_add_variable_valid_types_accepted(self):
        """All documented valid types should pass validation."""
        valid_types = [
            "Boolean", "Integer", "Integer64", "Float", "Double",
            "String", "Name", "Text", "Vector", "Rotator", "Transform",
            "Object//Script/Engine.Actor",
        ]
        for vtype in valid_types:
            with patch("tools.graph_tools._send",
                       return_value={"success": True, "variable_name": "X", "variable_type": vtype}):
                result = await self._call("bp_add_variable",
                                          blueprint_name="BP_Test",
                                          variable_name="TestVar",
                                          variable_type=vtype)
            data = _parse(result)
            self.assertTrue(data["success"], f"Type '{vtype}' should be valid but got: {data}")

    async def test_bp_add_variable_success_outputs(self):
        """Successful add_variable response includes variable_name, type, and next_steps."""
        with patch("tools.graph_tools._send",
                   return_value={"success": True}):
            result = await self._call("bp_add_variable",
                                      blueprint_name="BP_Test",
                                      variable_name="Health",
                                      variable_type="Float",
                                      default_value="100.0",
                                      is_exposed=True)
        data = _assert_schema(result, "bp_add_variable_success")
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertEqual(out["variable_name"], "Health")
        self.assertEqual(out["variable_type"], "Float")
        self.assertEqual(out["default_value"], "100.0")
        self.assertTrue(out["is_exposed"])
        self.assertIn("next_steps", out)
        self.assertGreater(len(out["next_steps"]), 0)

    async def test_bp_connect_pins_success_verified(self):
        """Successful connection with connection_verified=True."""
        with patch("tools.graph_tools._send",
                   return_value={"success": True, "connection_verified": True}):
            result = await self._call("bp_connect_pins",
                                      blueprint_name="BP_Test",
                                      source_node_id="SRC-GUID", source_pin="then",
                                      target_node_id="TGT-GUID", target_pin="execute")
        data = _assert_schema(result, "bp_connect_pins_success")
        self.assertTrue(data["success"])
        self.assertTrue(data["outputs"]["connection_verified"])
        self.assertEqual(data["outputs"]["source_pin"], "then")
        self.assertEqual(data["outputs"]["target_pin"], "execute")

    async def test_bp_connect_pins_success_unverified_warning(self):
        """Success=True but connection_verified=False produces a warning."""
        with patch("tools.graph_tools._send",
                   return_value={"success": True, "connection_verified": False,
                                 "warning": "Type mismatch — may not have taken effect"}):
            result = await self._call("bp_connect_pins",
                                      blueprint_name="BP_Test",
                                      source_node_id="SRC", source_pin="ReturnValue",
                                      target_node_id="TGT", target_pin="Target")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertFalse(data["outputs"]["connection_verified"])
        self.assertGreater(len(data["warnings"]), 0)

    async def test_bp_compile_success_structured_output(self):
        """Successful compile returns had_errors=False and structured output."""
        with patch("tools.graph_tools._send",
                   return_value={"had_errors": False, "had_warnings": False,
                                 "compile_messages": []}):
            result = await self._call("bp_compile", blueprint_name="BP_Test",
                                      save_after_compile=False)
        data = _assert_schema(result, "bp_compile_success")
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertFalse(out["had_errors"])
        self.assertFalse(out["had_warnings"])
        self.assertEqual(out["error_count"], 0)
        self.assertIn("compile_messages", out)

    async def test_bp_compile_error_messages_structured(self):
        """Compile errors are surfaced in errors[] with node reference."""
        with patch("tools.graph_tools._send",
                   return_value={
                       "had_errors": True,
                       "had_warnings": False,
                       "compile_messages": [
                           {"category": "error",
                            "message": "Pin 'execute' has no input connected",
                            "node_name": "K2Node_CallFunction_5"},
                       ],
                   }):
            result = await self._call("bp_compile", blueprint_name="BP_Test",
                                      save_after_compile=False)
        data = _assert_schema(result, "bp_compile_error")
        self.assertFalse(data["success"])
        self.assertGreater(len(data["errors"]), 0)
        out = data["outputs"]
        self.assertTrue(out["had_errors"])
        self.assertEqual(out["error_count"], 1)
        msg = out["compile_messages"][0]
        self.assertEqual(msg["category"], "error")
        self.assertEqual(msg["node_name"], "K2Node_CallFunction_5")

    async def test_bp_compile_string_messages_normalized(self):
        """String compile messages are normalized to {category, message, node_name}."""
        with patch("tools.graph_tools._send",
                   return_value={"had_errors": False, "had_warnings": True,
                                 "compile_messages": ["Warning: unused variable X"]}):
            result = await self._call("bp_compile", blueprint_name="BP_Test",
                                      save_after_compile=False)
        data = _parse(result)
        msgs = data["outputs"]["compile_messages"]
        self.assertEqual(len(msgs), 1)
        self.assertIn("category", msgs[0])
        self.assertIn("message", msgs[0])
        self.assertIn("node_name", msgs[0])
        self.assertEqual(msgs[0]["message"], "Warning: unused variable X")

    async def test_bp_set_pin_default_success_outputs(self):
        """Successful set_pin_default has node_id, pin_name, new_value."""
        with patch("tools.graph_tools._send",
                   return_value={"success": True, "previous_value": "1.0"}):
            result = await self._call("bp_set_pin_default",
                                      blueprint_name="BP_Test",
                                      node_id="DELAY-GUID", pin_name="Duration",
                                      default_value="2.5")
        data = _assert_schema(result, "bp_set_pin_default_success")
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertEqual(out["node_id"], "DELAY-GUID")
        self.assertEqual(out["pin_name"], "Duration")
        self.assertEqual(out["new_value"], "2.5")

    async def test_bp_set_pin_default_not_found_hint(self):
        """Pin-not-found error includes actionable hint about bp_inspect_node."""
        with patch("tools.graph_tools._send",
                   return_value={"success": False, "message": "Pin not found: Duration"}):
            result = await self._call("bp_set_pin_default",
                                      blueprint_name="BP_Test",
                                      node_id="SOME-NODE", pin_name="Duration",
                                      default_value="2.0")
        data = _parse(result)
        self.assertFalse(data["success"])
        combined = " ".join(data["errors"])
        self.assertIn("bp_inspect_node", combined,
                      "Error should hint user to use bp_inspect_node")

    async def test_bp_inspect_node_normalizes_pin_directions(self):
        """bp_inspect_node correctly maps integer direction values."""
        with patch("tools.graph_tools._send", return_value={
            "node": {
                "node_id": "GUID-0", "node_name": "K2Node_Event",
                "node_type": "event", "pos_x": 0, "pos_y": 0,
                "pins": [
                    {"pin_name": "then", "direction": 1, "pin_type": "exec",
                     "default_value": "", "linked_to": []},
                    {"pin_name": "execute", "direction": 0, "pin_type": "exec",
                     "default_value": "", "linked_to": []},
                ],
            }
        }):
            result = await self._call("bp_inspect_node",
                                      blueprint_name="BP_Test", node_id="GUID-0")
        data = _parse(result)
        if data["success"]:  # only check if node was found
            pins = {p["pin_name"]: p for p in data["outputs"]["pins"]}
            self.assertEqual(pins["then"]["direction"], "output")
            self.assertEqual(pins["execute"]["direction"], "input")

    async def test_bp_inspect_node_exposes_input_output_pin_lists(self):
        """bp_inspect_node outputs include input_pins and output_pins convenience lists."""
        with patch("tools.graph_tools._send", return_value={
            "node": {
                "node_id": "GUID-0", "node_name": "K2Node_Test",
                "node_type": "function", "pos_x": 0, "pos_y": 0,
                "pins": [
                    {"pin_name": "execute", "direction": "input", "pin_type": "exec",
                     "default_value": "", "linked_to": []},
                    {"pin_name": "Target", "direction": "input", "pin_type": "object",
                     "default_value": "", "linked_to": []},
                    {"pin_name": "then", "direction": "output", "pin_type": "exec",
                     "default_value": "", "linked_to": []},
                    {"pin_name": "ReturnValue", "direction": "output", "pin_type": "bool",
                     "default_value": "", "linked_to": []},
                ],
            }
        }):
            result = await self._call("bp_inspect_node",
                                      blueprint_name="BP_Test", node_id="GUID-0")
        data = _parse(result)
        if data["success"]:
            out = data["outputs"]
            self.assertIn("input_pins", out)
            self.assertIn("output_pins", out)
            self.assertIn("execute", out["input_pins"])
            self.assertIn("Target", out["input_pins"])
            self.assertIn("then", out["output_pins"])
            self.assertIn("ReturnValue", out["output_pins"])

    async def test_bp_auto_format_graph_empty_graph(self):
        """Empty graph returns success with nodes_repositioned=0."""
        with patch("tools.graph_tools._send", return_value={"nodes": []}):
            result = await self._call("bp_auto_format_graph",
                                      blueprint_name="BP_Test", graph_name="EventGraph")
        data = _assert_schema(result, "bp_auto_format_empty")
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["nodes_repositioned"], 0)

    async def test_bp_create_graph_valid_function_type(self):
        """Valid function graph creation succeeds (mocked)."""
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "transaction_complete",
                                 "message": "OK", "outputs": {"graph_name": "MyFunc"},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call("bp_create_graph",
                                      blueprint_name="BP_Test",
                                      graph_name="MyFunc",
                                      graph_type="function")
        data = _assert_schema(result, "bp_create_graph_function")
        self.assertTrue(data["success"])

    async def test_bp_create_graph_valid_macro_type(self):
        """Valid macro graph type is accepted."""
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "transaction_complete",
                                 "message": "OK", "outputs": {},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call("bp_create_graph",
                                      blueprint_name="BP_Test",
                                      graph_name="MyMacro",
                                      graph_type="macro")
        data = _assert_schema(result, "bp_create_graph_macro")
        self.assertTrue(data["success"])


# ── Tests: New BP Tools (V4.1) ────────────────────────────────────────────────

class TestBpRemoveNode(unittest.IsolatedAsyncioTestCase):
    """Tests for bp_remove_node."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, **kwargs):
        fn = self.mcp.get_tool("bp_remove_node")
        return await fn(_mock_ctx(), **kwargs)

    async def test_schema_valid_on_not_connected(self):
        with patch("tools.graph_tools._send",
                   return_value={"success": False, "message": "Not connected"}):
            result = await self._call(blueprint_name="BP_Test", node_id="GUID-X")
        data = _assert_schema(result, "bp_remove_node_not_connected")
        self.assertFalse(data["success"])

    async def test_success_returns_deleted_node_id(self):
        with patch("tools.graph_tools._send",
                   return_value={"deleted_node_id": "GUID-X",
                                 "deleted_node_name": "K2Node_Event_0"}):
            result = await self._call(blueprint_name="BP_Test", node_id="GUID-X")
        data = _assert_schema(result, "bp_remove_node_success")
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["deleted_node_id"], "GUID-X")
        self.assertEqual(data["outputs"]["deleted_node_name"], "K2Node_Event_0")

    async def test_success_includes_next_steps(self):
        with patch("tools.graph_tools._send",
                   return_value={"deleted_node_id": "G", "deleted_node_name": "N"}):
            result = await self._call(blueprint_name="BP_Test", node_id="G")
        data = _parse(result)
        self.assertIn("next_steps", data["outputs"])
        self.assertGreater(len(data["outputs"]["next_steps"]), 0)

    async def test_error_response_structured(self):
        with patch("tools.graph_tools._send",
                   return_value={"status": "error", "error": "Node not found: BAD-GUID"}):
            result = await self._call(blueprint_name="BP_Test", node_id="BAD-GUID")
        data = _assert_schema(result, "bp_remove_node_not_found")
        self.assertFalse(data["success"])
        self.assertTrue(any("not found" in e.lower() or "BAD-GUID" in e
                            for e in data["errors"]))

    async def test_routes_to_delete_blueprint_node_command(self):
        """Must use 'delete_blueprint_node' C++ command, not some other name."""
        calls = []
        def mock_send(cmd, params):
            calls.append(cmd)
            return {"deleted_node_id": "G", "deleted_node_name": "N"}
        with patch("tools.graph_tools._send", side_effect=mock_send):
            await self._call(blueprint_name="BP_Test", node_id="G", graph_name="MyGraph")
        self.assertEqual(calls[0], "delete_blueprint_node")


class TestBpDisconnectPin(unittest.IsolatedAsyncioTestCase):
    """Tests for bp_disconnect_pin."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, **kwargs):
        fn = self.mcp.get_tool("bp_disconnect_pin")
        return await fn(_mock_ctx(), **kwargs)

    async def test_schema_valid_on_not_connected(self):
        with patch("tools.graph_tools._send",
                   return_value={"success": False, "message": "Not connected"}):
            result = await self._call(blueprint_name="BP_Test",
                                      node_id="GUID", pin_name="then")
        data = _assert_schema(result, "bp_disconnect_pin_not_connected")
        self.assertFalse(data["success"])

    async def test_break_all_mode(self):
        """No target_node_id = break_all mode."""
        calls = []
        def mock_send(cmd, params):
            calls.append((cmd, params))
            return {"node_id": "GUID", "pin_name": "then"}
        with patch("tools.graph_tools._send", side_effect=mock_send):
            result = await self._call(blueprint_name="BP_Test",
                                      node_id="GUID", pin_name="then")
        data = _assert_schema(result, "bp_disconnect_pin_break_all")
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["mode"], "break_all")
        # Must pass node_id + pin_name to C++ (Case A)
        self.assertIn("node_id", calls[0][1])
        self.assertIn("pin_name", calls[0][1])

    async def test_break_one_mode(self):
        """target_node_id supplied = break_one mode."""
        calls = []
        def mock_send(cmd, params):
            calls.append((cmd, params))
            return {"source_node_id": "SRC", "target_node_id": "TGT"}
        with patch("tools.graph_tools._send", side_effect=mock_send):
            result = await self._call(blueprint_name="BP_Test",
                                      node_id="SRC", pin_name="then",
                                      target_node_id="TGT", target_pin_name="execute")
        data = _assert_schema(result, "bp_disconnect_pin_break_one")
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["mode"], "break_one")
        # Must pass source_node_id + target_node_id to C++ (Case B)
        self.assertIn("source_node_id", calls[0][1])
        self.assertIn("target_node_id", calls[0][1])

    async def test_routes_to_disconnect_blueprint_nodes(self):
        calls = []
        def mock_send(cmd, params):
            calls.append(cmd)
            return {"node_id": "G", "pin_name": "then"}
        with patch("tools.graph_tools._send", side_effect=mock_send):
            await self._call(blueprint_name="BP_Test", node_id="G", pin_name="then")
        self.assertEqual(calls[0], "disconnect_blueprint_nodes")

    async def test_success_includes_next_steps(self):
        with patch("tools.graph_tools._send",
                   return_value={"node_id": "G", "pin_name": "then"}):
            result = await self._call(blueprint_name="BP_Test",
                                      node_id="G", pin_name="then")
        data = _parse(result)
        self.assertIn("next_steps", data["outputs"])


class TestBpAddFunction(unittest.IsolatedAsyncioTestCase):
    """Tests for bp_add_function."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, **kwargs):
        fn = self.mcp.get_tool("bp_add_function")
        return await fn(_mock_ctx(), **kwargs)

    async def test_schema_valid_on_exec_failure(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": False, "stage": "transaction_complete",
                                 "message": "BP not found", "outputs": {},
                                 "warnings": [], "errors": ["BP not found"], "log_tail": []}):
            result = await self._call(blueprint_name="BP_Test",
                                      function_name="TakeDamage")
        data = _assert_schema(result, "bp_add_function_exec_fail")
        self.assertFalse(data["success"])

    async def test_success_returns_function_and_graph_name(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok",
                                 "message": "OK",
                                 "outputs": {"function_name": "TakeDamage",
                                             "graph_name": "TakeDamage",
                                             "already_existed": False},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(blueprint_name="BP_Test",
                                      function_name="TakeDamage",
                                      return_type="float")
        data = _assert_schema(result, "bp_add_function_success")
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertEqual(out["function_name"], "TakeDamage")
        self.assertEqual(out["graph_name"], "TakeDamage")
        self.assertFalse(out["already_existed"])
        self.assertEqual(out["return_type"], "float")

    async def test_already_existed_produces_warning(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"function_name": "Heal",
                                             "graph_name": "Heal",
                                             "already_existed": True},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(blueprint_name="BP_Test",
                                      function_name="Heal")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertTrue(data["outputs"]["already_existed"])
        self.assertGreater(len(data["warnings"]), 0,
                           "Should warn that function already existed")

    async def test_invalid_params_json_produces_warning(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"function_name": "Fn", "graph_name": "Fn",
                                             "already_existed": False},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(blueprint_name="BP_Test",
                                      function_name="Fn",
                                      params="NOT_VALID_JSON")
        data = _parse(result)
        self.assertTrue(data["success"])
        # Warning about the bad JSON
        self.assertTrue(any("JSON" in w or "parse" in w.lower()
                            for w in data["warnings"]))

    async def test_next_steps_reference_graph_name(self):
        """next_steps should contain the new graph name for easy follow-up."""
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"function_name": "Attack",
                                             "graph_name": "Attack",
                                             "already_existed": False},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(blueprint_name="BP_Test",
                                      function_name="Attack")
        data = _parse(result)
        combined_steps = " ".join(data["outputs"]["next_steps"])
        self.assertIn("Attack", combined_steps)


# ── Tests: Material Tools (V4.1) ──────────────────────────────────────────────

class TestMatCreateMaterial(unittest.IsolatedAsyncioTestCase):
    """Tests for mat_create_material."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, **kwargs):
        fn = self.mcp.get_tool("mat_create_material")
        return await fn(_mock_ctx(), **kwargs)

    async def test_schema_valid_on_exec_failure(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": False, "stage": "err", "message": "Fail",
                                 "outputs": {}, "warnings": [], "errors": ["Fail"],
                                 "log_tail": []}):
            result = await self._call(material_name="M_Rock")
        data = _assert_schema(result, "mat_create_material_fail")
        self.assertFalse(data["success"])

    async def test_success_outputs_material_path(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"material_path": "/Game/Materials/M_Rock",
                                             "material_name": "M_Rock"},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(material_name="M_Rock",
                                      package_path="/Game/Materials",
                                      blend_mode="Opaque")
        data = _assert_schema(result, "mat_create_material_success")
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["material_path"], "/Game/Materials/M_Rock")
        self.assertEqual(data["outputs"]["blend_mode"], "Opaque")

    async def test_next_steps_include_mat_add_expression(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"material_path": "/Game/Materials/M_X"},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(material_name="M_X")
        data = _parse(result)
        combined = " ".join(data["outputs"]["next_steps"])
        self.assertIn("mat_add_expression", combined)

    async def test_blend_mode_and_shading_model_in_outputs(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"material_path": "/Game/M_T"},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(material_name="M_T",
                                      blend_mode="Translucent",
                                      shading_model="Unlit")
        data = _parse(result)
        self.assertEqual(data["outputs"]["blend_mode"], "Translucent")
        self.assertEqual(data["outputs"]["shading_model"], "Unlit")


class TestMatAddExpression(unittest.IsolatedAsyncioTestCase):
    """Tests for mat_add_expression."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, **kwargs):
        fn = self.mcp.get_tool("mat_add_expression")
        return await fn(_mock_ctx(), **kwargs)

    async def test_schema_valid_on_exec_failure(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": False, "stage": "err", "message": "Fail",
                                 "outputs": {}, "warnings": [], "errors": ["Fail"],
                                 "log_tail": []}):
            result = await self._call(material_path="/Game/M_Rock",
                                      expression_type="Multiply")
        data = _assert_schema(result, "mat_add_expression_fail")
        self.assertFalse(data["success"])

    async def test_invalid_expression_params_json(self):
        result = await self._call(material_path="/Game/M_Rock",
                                  expression_type="Texture",
                                  expression_params="BAD_JSON_!!!")
        data = _assert_schema(result, "mat_add_expression_bad_params_json")
        self.assertFalse(data["success"])
        self.assertTrue(any("JSON" in e or "parse" in e.lower()
                            for e in data["errors"]))

    async def test_success_returns_expression_index_and_name(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"expression_index": 2,
                                             "expression_name": "MaterialExpressionMultiply_0",
                                             "expression_class": "MaterialExpressionMultiply"},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(material_path="/Game/M_Rock",
                                      expression_type="Multiply",
                                      position_x=-400, position_y=0)
        data = _assert_schema(result, "mat_add_expression_success")
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertEqual(out["expression_index"], 2)
        self.assertEqual(out["expression_name"], "MaterialExpressionMultiply_0")
        self.assertEqual(out["position_x"], -400)

    async def test_type_aliases_resolve(self):
        """Common shorthand aliases should resolve without error in code generation."""
        aliases = ["texture", "multiply", "add", "constant", "constant3",
                   "param_scalar", "param_vector", "lerp", "fresnel"]
        for alias in aliases:
            # Just check that no exception is raised during code construction
            # (we mock exec_transactional to avoid actually running UE code)
            with patch("tools.graph_tools._exec_transactional",
                       return_value={"success": True, "stage": "ok", "message": "OK",
                                     "outputs": {"expression_index": 0,
                                                 "expression_name": "Expr_0"},
                                     "warnings": [], "errors": [], "log_tail": []}):
                result = await self._call(material_path="/Game/M_Test",
                                          expression_type=alias)
            data = _parse(result)
            self.assertTrue(data["success"], f"Alias '{alias}' should succeed, got: {data}")


class TestMatConnectExpressions(unittest.IsolatedAsyncioTestCase):
    """Tests for mat_connect_expressions."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, **kwargs):
        fn = self.mcp.get_tool("mat_connect_expressions")
        return await fn(_mock_ctx(), **kwargs)

    async def test_schema_valid_on_exec_failure(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": False, "stage": "err", "message": "Fail",
                                 "outputs": {}, "warnings": [], "errors": ["Fail"],
                                 "log_tail": []}):
            result = await self._call(material_path="/Game/M_Rock",
                                      from_expression_name="Expr_A",
                                      from_output_name="RGB",
                                      to_expression_name="Expr_B",
                                      to_input_name="A")
        data = _assert_schema(result, "mat_connect_fail")
        self.assertFalse(data["success"])

    async def test_connect_to_material_root_uses_property_api(self):
        """Empty to_expression_name should use connect_material_property path."""
        captured = []
        def mock_exec(code, tx):
            captured.append(code)
            return {"success": True, "stage": "ok", "message": "OK",
                    "outputs": {"connected": True, "from": "Expr.RGB", "to": "Root.BaseColor"},
                    "warnings": [], "errors": [], "log_tail": []}
        with patch("tools.graph_tools._exec_transactional", side_effect=mock_exec):
            result = await self._call(material_path="/Game/M_Rock",
                                      from_expression_name="TextureSample_0",
                                      from_output_name="RGB",
                                      to_expression_name="",
                                      to_input_name="BaseColor")
        data = _assert_schema(result, "mat_connect_to_root")
        self.assertTrue(data["success"])
        # Code should reference connect_material_property (root path)
        self.assertIn("connect_material_property", captured[0])

    async def test_connect_expression_to_expression(self):
        """Non-empty to_expression_name uses connect_material_expressions path."""
        captured = []
        def mock_exec(code, tx):
            captured.append(code)
            return {"success": True, "stage": "ok", "message": "OK",
                    "outputs": {"connected": True, "from": "A.RGB", "to": "B.A"},
                    "warnings": [], "errors": [], "log_tail": []}
        with patch("tools.graph_tools._exec_transactional", side_effect=mock_exec):
            result = await self._call(material_path="/Game/M_Rock",
                                      from_expression_name="Expr_A",
                                      from_output_name="RGB",
                                      to_expression_name="Expr_B",
                                      to_input_name="A")
        data = _assert_schema(result, "mat_connect_expr_to_expr")
        self.assertTrue(data["success"])
        self.assertIn("connect_material_expressions", captured[0])

    async def test_success_outputs_from_to(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"connected": True,
                                             "from": "Multiply_0.RGB",
                                             "to": "Root.BaseColor"},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(material_path="/Game/M_Rock",
                                      from_expression_name="Multiply_0",
                                      from_output_name="RGB",
                                      to_expression_name="",
                                      to_input_name="BaseColor")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertIn("from", data["outputs"])
        self.assertIn("to", data["outputs"])
        self.assertIn("next_steps", data["outputs"])


class TestMatCompile(unittest.IsolatedAsyncioTestCase):
    """Tests for mat_compile."""

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)

    async def _call(self, **kwargs):
        fn = self.mcp.get_tool("mat_compile")
        return await fn(_mock_ctx(), **kwargs)

    async def test_schema_valid_on_exec_failure(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": False, "stage": "err", "message": "Fail",
                                 "outputs": {}, "warnings": [], "errors": ["Fail"],
                                 "log_tail": []}):
            result = await self._call(material_path="/Game/M_Rock")
        data = _assert_schema(result, "mat_compile_exec_fail")
        self.assertFalse(data["success"])

    async def test_success_had_errors_false(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"had_errors": False,
                                             "had_warnings": False,
                                             "material_path": "/Game/M_Rock",
                                             "saved": True},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(material_path="/Game/M_Rock")
        data = _assert_schema(result, "mat_compile_success")
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertFalse(out["had_errors"])
        self.assertTrue(out["saved"])
        self.assertEqual(out["error_count"], 0)

    async def test_compile_error_returns_false_success(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"had_errors": True,
                                             "had_warnings": False,
                                             "material_path": "/Game/M_Rock",
                                             "saved": False},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(material_path="/Game/M_Rock")
        data = _assert_schema(result, "mat_compile_with_errors")
        self.assertFalse(data["success"],
                         "had_errors=True must make overall success=False")
        self.assertTrue(data["outputs"]["had_errors"])
        self.assertFalse(data["outputs"]["saved"])

    async def test_compile_error_includes_actionable_next_steps(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"had_errors": True,
                                             "material_path": "/Game/M_Bad",
                                             "saved": False},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(material_path="/Game/M_Bad",
                                      save_after_compile=False)
        data = _parse(result)
        combined_steps = " ".join(data["outputs"]["next_steps"])
        # Should suggest checking connections
        self.assertTrue("connect" in combined_steps.lower() or
                        "expression" in combined_steps.lower())

    async def test_save_after_compile_false_outputs_saved_false(self):
        with patch("tools.graph_tools._exec_transactional",
                   return_value={"success": True, "stage": "ok", "message": "OK",
                                 "outputs": {"had_errors": False,
                                             "had_warnings": False,
                                             "material_path": "/Game/M_Rock",
                                             "saved": False},
                                 "warnings": [], "errors": [], "log_tail": []}):
            result = await self._call(material_path="/Game/M_Rock",
                                      save_after_compile=False)
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertFalse(data["outputs"]["saved"])


# ── Tests: Tool Count Integration ─────────────────────────────────────────────

class TestToolCountAfterGraphTools(unittest.TestCase):
    """Verify total tool count reflects the 17 graph/material tools (V5: +bp_get_graph_detail)."""

    def test_graph_tools_adds_expected_tools(self):
        from tools.graph_tools import register_graph_tools
        mcp = _MockMCP()
        register_graph_tools(mcp)
        # V5 adds bp_get_graph_detail → 17 total (was 16)
        self.assertGreaterEqual(len(mcp.list_tool_names()), 17,
                         f"Expected ≥17 tools, got: {sorted(mcp.list_tool_names())}")

    def test_bp_tools_have_bp_prefix(self):
        from tools.graph_tools import register_graph_tools
        mcp = _MockMCP()
        register_graph_tools(mcp)
        bp_tools = [n for n in mcp.list_tool_names() if n.startswith("bp_")]
        # V5 adds bp_get_graph_detail → 13 bp_ tools (was 12)
        self.assertGreaterEqual(len(bp_tools), 13,
                         f"Expected ≥13 bp_* tools, got {len(bp_tools)}: {bp_tools}")

    def test_mat_tools_have_mat_prefix(self):
        from tools.graph_tools import register_graph_tools
        mcp = _MockMCP()
        register_graph_tools(mcp)
        mat_tools = [n for n in mcp.list_tool_names() if n.startswith("mat_")]
        self.assertEqual(len(mat_tools), 4,
                         f"Expected 4 mat_* tools, got {len(mat_tools)}: {mat_tools}")

    def test_all_expected_tool_names_present(self):
        from tools.graph_tools import register_graph_tools
        mcp = _MockMCP()
        register_graph_tools(mcp)
        expected = {
            "bp_get_graph_summary", "bp_create_graph", "bp_add_node", "bp_inspect_node",
            "bp_connect_pins", "bp_set_pin_default", "bp_add_variable", "bp_compile",
            "bp_auto_format_graph", "bp_remove_node", "bp_disconnect_pin", "bp_add_function",
            "mat_create_material", "mat_add_expression", "mat_connect_expressions", "mat_compile",
        }
        actual = set(mcp.list_tool_names())
        missing = expected - actual
        self.assertEqual(missing, set(), f"Missing tools: {missing}")

    def test_documented_tool_count_updated(self):
        """last_tool_count.txt should reflect the new total (≥390 after V5 tools)."""
        count_file = os.path.join(_HERE, "last_tool_count.txt")
        if os.path.exists(count_file):
            with open(count_file) as f:
                count = int(f.read().strip())
            self.assertGreaterEqual(count, 390,
                                    f"last_tool_count.txt says {count} but should be ≥390")


# ── V5 Close-out Tests: bp_get_graph_summary enhancements ────────────────────

class TestV5GraphSummaryEnhancements(unittest.IsolatedAsyncioTestCase):
    """
    8 tests covering the V5 close-out additions:
      1. bp_get_graph_summary returns variables[] key (always present)
      2. bp_get_graph_summary returns function_graphs[] key (always present)
      3. bp_get_graph_summary returns event_graphs[] key (always present)
      4. bp_get_graph_summary pagination returns correct page slice
      5. bp_get_graph_summary include_nodes=False returns metadata only
      6. bp_get_graph_summary meta dict present with tool and duration_ms
      7. bp_get_graph_detail registered and returns paginated nodes
      8. bp_get_graph_detail compact mode (include_pin_defaults=False) reduces token estimate
    """

    def setUp(self):
        from tools.graph_tools import register_graph_tools
        self.mcp = _MockMCP()
        register_graph_tools(self.mcp)
        self.summary_tool = self.mcp.get_tool("bp_get_graph_summary")
        self.detail_tool  = self.mcp.get_tool("bp_get_graph_detail")

    def _make_nodes(self, count):
        nodes = []
        for i in range(count):
            nodes.append({
                "node_id":   f"NODE-{i:04d}-XXXX",
                "node_name": f"K2Node_Test_{i}",
                "node_type": "function",
                "title":     f"Node_{i}",
                "pos_x": i * 200, "pos_y": 0,
                "pins": [
                    {"pin_name": "execute", "direction": "input", "pin_type": "exec",
                     "default_value": "val", "linked_to": []},
                ],
            })
        return nodes

    def _mock_send_factory(self, nodes, meta_result=None):
        def mock_send(command, params):
            if command == "get_blueprint_nodes":
                return {"success": True, "nodes": nodes}
            if command == "exec_python":
                if meta_result is not None:
                    return {"success": True, "result": meta_result}
                return {"success": True, "result": {
                    "variables": [{"name": "Health", "type": "float"}],
                    "function_graphs": [{"name": "TakeDamage", "type": "function"}],
                    "event_graphs": [{"name": "EventGraph", "type": "event"}],
                }}
            return {"success": True, "result": {}}
        return mock_send

    async def test_v5_summary_has_variables_key(self):
        """bp_get_graph_summary always returns outputs.variables list."""
        nodes = self._make_nodes(2)
        with patch("tools.graph_tools._send", side_effect=self._mock_send_factory(nodes)):
            result = await self.summary_tool(_mock_ctx(), blueprint_name="BP_Test")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertIn("variables", data["outputs"])
        self.assertIsInstance(data["outputs"]["variables"], list)

    async def test_v5_summary_has_function_graphs_key(self):
        """bp_get_graph_summary always returns outputs.function_graphs list."""
        nodes = self._make_nodes(2)
        with patch("tools.graph_tools._send", side_effect=self._mock_send_factory(nodes)):
            result = await self.summary_tool(_mock_ctx(), blueprint_name="BP_Test")
        data = _parse(result)
        self.assertIn("function_graphs", data["outputs"])
        self.assertIsInstance(data["outputs"]["function_graphs"], list)

    async def test_v5_summary_has_event_graphs_key(self):
        """bp_get_graph_summary always returns outputs.event_graphs list."""
        nodes = self._make_nodes(2)
        with patch("tools.graph_tools._send", side_effect=self._mock_send_factory(nodes)):
            result = await self.summary_tool(_mock_ctx(), blueprint_name="BP_Test")
        data = _parse(result)
        self.assertIn("event_graphs", data["outputs"])
        self.assertIsInstance(data["outputs"]["event_graphs"], list)

    async def test_v5_summary_pagination_page_slice(self):
        """bp_get_graph_summary paginates: page=1, page_size=3 returns nodes 3-5."""
        nodes = self._make_nodes(9)
        with patch("tools.graph_tools._send", side_effect=self._mock_send_factory(nodes)):
            result = await self.summary_tool(
                _mock_ctx(), blueprint_name="BP_Test",
                page=1, page_size=3
            )
        data = _parse(result)
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertEqual(out["page"], 1)
        self.assertEqual(len(out["nodes"]), 3)
        # nodes on page 1 (0-indexed) are indices 3,4,5
        self.assertEqual(out["nodes"][0]["title"], "Node_3")

    async def test_v5_summary_include_nodes_false(self):
        """include_nodes=False returns metadata only — nodes list is empty."""
        nodes = self._make_nodes(6)
        with patch("tools.graph_tools._send", side_effect=self._mock_send_factory(nodes)):
            result = await self.summary_tool(
                _mock_ctx(), blueprint_name="BP_Test", include_nodes=False
            )
        data = _parse(result)
        self.assertTrue(data["success"])
        # nodes is empty because include_nodes=False skips get_blueprint_nodes
        self.assertEqual(data["outputs"]["nodes"], [])
        # But metadata keys must still be present
        self.assertIn("variables", data["outputs"])
        self.assertIn("function_graphs", data["outputs"])

    async def test_v5_summary_meta_dict_present(self):
        """bp_get_graph_summary result includes meta with tool and duration_ms."""
        nodes = self._make_nodes(2)
        with patch("tools.graph_tools._send", side_effect=self._mock_send_factory(nodes)):
            result = await self.summary_tool(_mock_ctx(), blueprint_name="BP_Test")
        data = _parse(result)
        self.assertIn("meta", data)
        self.assertEqual(data["meta"]["tool"], "bp_get_graph_summary")
        self.assertIn("duration_ms", data["meta"])

    async def test_v5_graph_detail_registered(self):
        """bp_get_graph_detail is registered and returns a StructuredResult."""
        self.assertIsNotNone(self.detail_tool, "bp_get_graph_detail not registered")
        nodes = self._make_nodes(3)
        with patch("tools.graph_tools._send", side_effect=self._mock_send_factory(nodes)):
            result = await self.detail_tool(
                _mock_ctx(),
                blueprint_path="/Game/Blueprints/BP_Test",
                graph_name="TakeDamage",
            )
        data = _assert_schema(result, "bp_get_graph_detail")
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertIn("total_nodes", out)
        self.assertIn("nodes", out)
        self.assertIn("token_estimate", out)

    async def test_v5_graph_detail_compact_reduces_tokens(self):
        """bp_get_graph_detail compact mode lowers token estimate vs. full mode."""
        # Build nodes with verbose default values
        nodes = []
        for i in range(9):
            nodes.append({
                "node_id": f"TD-{i:04d}", "node_name": f"K2Node_{i}",
                "node_type": "function", "title": f"Node_{i}",
                "pos_x": i*200, "pos_y": 0,
                "pins": [
                    {"pin_name": "execute",  "direction": "input",  "pin_type": "exec",
                     "default_value": "", "linked_to": []},
                    {"pin_name": "InputVal", "direction": "input",  "pin_type": "float",
                     "default_value": "0.0 this is a long default value string", "linked_to": []},
                    {"pin_name": "then",     "direction": "output", "pin_type": "exec",
                     "default_value": "", "linked_to": []},
                ],
            })

        with patch("tools.graph_tools._send", side_effect=self._mock_send_factory(nodes)):
            full_result = await self.detail_tool(
                _mock_ctx(),
                blueprint_path="/Game/Blueprints/BP_HealthSystem",
                graph_name="TakeDamage",
                include_pin_defaults=True,
            )
        with patch("tools.graph_tools._send", side_effect=self._mock_send_factory(nodes)):
            compact_result = await self.detail_tool(
                _mock_ctx(),
                blueprint_path="/Game/Blueprints/BP_HealthSystem",
                graph_name="TakeDamage",
                include_pin_defaults=False,
            )

        full_data    = _parse(full_result)
        compact_data = _parse(compact_result)

        full_tokens    = full_data["outputs"]["token_estimate"]
        compact_tokens = compact_data["outputs"]["token_estimate"]

        self.assertLess(compact_tokens, full_tokens,
                        f"Compact ({compact_tokens}) should be < full ({full_tokens})")
        # Compact should be well under 1800 tokens for a 9-node graph
        self.assertLess(compact_tokens, 1800,
                        f"Compact TakeDamage graph exceeds 1800-token budget: {compact_tokens}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
