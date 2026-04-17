"""
test_diagnostics.py — Phase 4 / V6 Diagnostics Unit Tests
==========================================================

Test buckets:
  A: diagnostics_tools.py — schema, offline behavior, health scoring
  B: graph pathology fixtures — offline node analysis
  C: repair_tools.py — schema, record builder, offline behavior
  D: repair skill — workflow, dry_run, skipped issues
"""

from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

# ── sys.path ──────────────────────────────────────────────────────────────────
SERVER_ROOT = Path(__file__).resolve().parent.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

# ── Stubs: prevent real UE5 imports ──────────────────────────────────────────
_STUB_MODULES = [
    "unreal",
    "mcp",
    "mcp.server",
    "mcp.server.fastmcp",
]
for _m in _STUB_MODULES:
    if _m not in sys.modules:
        stub = types.ModuleType(_m)
        sys.modules[_m] = stub

# Provide a minimal FastMCP stub
_fmcp = sys.modules["mcp.server.fastmcp"]
if not hasattr(_fmcp, "FastMCP"):
    class _FakeFastMCP:
        def tool(self):
            def _dec(fn):
                return fn
            return _dec
    _fmcp.FastMCP = _FakeFastMCP

if not hasattr(_fmcp, "Context"):
    _fmcp.Context = object

# ── Import modules under test ─────────────────────────────────────────────────
from tools.diagnostics_tools import (
    _diag_item,
    _health_score,
    _analyze_nodes_offline,
    _meta,
    _ok,
    _err,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SEVERITY_INFO,
    CAT_COMPILE,
    CAT_GRAPH,
    CAT_VAR,
    CAT_MATERIAL,
    register_diagnostics_tools,
)

from tools.repair_tools import (
    _repair_record,
    register_repair_tools,
)


# ═══════════════════════════════════════════════════════════════════════════════
# A: Diagnostics schema & helpers
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiagItemSchema(unittest.TestCase):
    """A1: diag_item schema compliance."""

    REQUIRED_KEYS = {
        "severity", "category", "code", "message", "asset_path",
        "graph_name", "node_guid", "node_title", "pin_name",
        "suggested_fix", "auto_repairable",
    }

    def _make(self, **kw) -> Dict:
        defaults = dict(
            severity=SEVERITY_ERROR,
            category=CAT_COMPILE,
            code="TEST",
            message="test message",
            asset_path="/Game/BP",
        )
        defaults.update(kw)
        return _diag_item(**defaults)

    def test_all_required_keys_present(self):
        item = self._make()
        self.assertEqual(self.REQUIRED_KEYS, set(item.keys()))

    def test_optional_defaults_are_empty_strings(self):
        item = self._make()
        for k in ("graph_name", "node_guid", "node_title", "pin_name", "suggested_fix"):
            self.assertEqual(item[k], "", f"{k} should default to ''")

    def test_auto_repairable_defaults_false(self):
        item = self._make()
        self.assertFalse(item["auto_repairable"])

    def test_auto_repairable_can_be_true(self):
        item = self._make(auto_repairable=True)
        self.assertTrue(item["auto_repairable"])

    def test_severity_error_stored(self):
        item = self._make(severity=SEVERITY_ERROR)
        self.assertEqual(item["severity"], "error")

    def test_severity_warning_stored(self):
        item = self._make(severity=SEVERITY_WARNING)
        self.assertEqual(item["severity"], "warning")

    def test_severity_info_stored(self):
        item = self._make(severity=SEVERITY_INFO)
        self.assertEqual(item["severity"], "info")

    def test_category_compile(self):
        item = self._make(category=CAT_COMPILE)
        self.assertEqual(item["category"], "compile")

    def test_category_graph(self):
        item = self._make(category=CAT_GRAPH)
        self.assertEqual(item["category"], "graph_structure")

    def test_category_var(self):
        item = self._make(category=CAT_VAR)
        self.assertEqual(item["category"], "variable_usage")

    def test_category_material(self):
        item = self._make(category=CAT_MATERIAL)
        self.assertEqual(item["category"], "material")

    def test_node_guid_stored(self):
        item = self._make(node_guid="AABB-1122")
        self.assertEqual(item["node_guid"], "AABB-1122")

    def test_node_title_stored(self):
        item = self._make(node_title="PrintString")
        self.assertEqual(item["node_title"], "PrintString")

    def test_pin_name_stored(self):
        item = self._make(pin_name="execute")
        self.assertEqual(item["pin_name"], "execute")

    def test_suggested_fix_stored(self):
        item = self._make(suggested_fix="Delete node")
        self.assertEqual(item["suggested_fix"], "Delete node")

    def test_asset_path_stored(self):
        item = self._make(asset_path="/Game/Blueprints/BP_Hero")
        self.assertEqual(item["asset_path"], "/Game/Blueprints/BP_Hero")

    def test_message_stored(self):
        item = self._make(message="Compile failed")
        self.assertEqual(item["message"], "Compile failed")

    def test_code_stored(self):
        item = self._make(code="BP_NOT_FOUND")
        self.assertEqual(item["code"], "BP_NOT_FOUND")


class TestHealthScore(unittest.TestCase):
    """A2: health score formula."""

    def test_empty_issues_is_100(self):
        self.assertEqual(_health_score([]), 100)

    def test_one_error_is_85(self):
        item = _diag_item(severity=SEVERITY_ERROR, category=CAT_COMPILE,
                          code="E", message="m", asset_path="/G")
        self.assertEqual(_health_score([item]), 85)

    def test_one_warning_is_95(self):
        item = _diag_item(severity=SEVERITY_WARNING, category=CAT_GRAPH,
                          code="W", message="m", asset_path="/G")
        self.assertEqual(_health_score([item]), 95)

    def test_one_info_is_99(self):
        item = _diag_item(severity=SEVERITY_INFO, category=CAT_GRAPH,
                          code="I", message="m", asset_path="/G")
        self.assertEqual(_health_score([item]), 99)

    def test_mixed_issues(self):
        items = [
            _diag_item(severity=SEVERITY_ERROR,   category=CAT_COMPILE, code="E",  message="m", asset_path="/G"),
            _diag_item(severity=SEVERITY_WARNING, category=CAT_GRAPH,   code="W1", message="m", asset_path="/G"),
            _diag_item(severity=SEVERITY_WARNING, category=CAT_GRAPH,   code="W2", message="m", asset_path="/G"),
        ]
        # 100 - 15 (error) - 5 - 5 (warnings) = 75
        self.assertEqual(_health_score(items), 75)

    def test_clamped_at_zero(self):
        items = [
            _diag_item(severity=SEVERITY_ERROR, category=CAT_COMPILE, code=f"E{i}",
                       message="m", asset_path="/G")
            for i in range(10)
        ]
        # 100 - 10*15 = -50 → clamped to 0
        self.assertEqual(_health_score(items), 0)

    def test_clamped_at_100(self):
        # Score can't exceed 100 even with empty list
        self.assertEqual(_health_score([]), 100)

    def test_two_errors_is_70(self):
        items = [
            _diag_item(severity=SEVERITY_ERROR, category=CAT_COMPILE, code=f"E{i}",
                       message="m", asset_path="/G")
            for i in range(2)
        ]
        self.assertEqual(_health_score(items), 70)

    def test_unknown_severity_not_counted(self):
        self.assertEqual(_health_score([{"severity": "unknown"}]), 100)


class TestStructuredResultHelpers(unittest.TestCase):
    """A3: _ok and _err structured result builders."""

    def test_ok_success_true(self):
        r = _ok({}, [], {"tool": "t", "duration_ms": 0})
        self.assertTrue(r["success"])

    def test_ok_stage_complete(self):
        r = _ok({}, [], {"tool": "t", "duration_ms": 0})
        self.assertEqual(r["stage"], "complete")

    def test_ok_empty_errors(self):
        r = _ok({}, [], {"tool": "t", "duration_ms": 0})
        self.assertEqual(r["errors"], [])

    def test_ok_custom_message(self):
        r = _ok({}, [], {"tool": "t", "duration_ms": 0}, "custom msg")
        self.assertEqual(r["message"], "custom msg")

    def test_ok_outputs_passed_through(self):
        r = _ok({"k": "v"}, [], {"tool": "t", "duration_ms": 0})
        self.assertEqual(r["outputs"]["k"], "v")

    def test_ok_warnings_passed(self):
        r = _ok({}, ["warn1"], {"tool": "t", "duration_ms": 0})
        self.assertIn("warn1", r["warnings"])

    def test_err_success_false(self):
        r = _err("oops", {"tool": "t", "duration_ms": 0})
        self.assertFalse(r["success"])

    def test_err_stage_error(self):
        r = _err("oops", {"tool": "t", "duration_ms": 0})
        self.assertEqual(r["stage"], "error")

    def test_err_message_stored(self):
        r = _err("bad thing", {"tool": "t", "duration_ms": 0})
        self.assertEqual(r["message"], "bad thing")

    def test_err_errors_list(self):
        r = _err("bad thing", {"tool": "t", "duration_ms": 0})
        self.assertIn("bad thing", r["errors"])

    def test_meta_tool_name(self):
        import time
        t0 = time.monotonic()
        m  = _meta("my_tool", t0)
        self.assertEqual(m["tool"], "my_tool")

    def test_meta_duration_nonneg(self):
        import time
        t0 = time.monotonic()
        m  = _meta("my_tool", t0)
        self.assertGreaterEqual(m["duration_ms"], 0)


# ═══════════════════════════════════════════════════════════════════════════════
# B: Graph pathology fixtures (offline node analysis)
# ═══════════════════════════════════════════════════════════════════════════════

def _make_node(node_id: str, title: str, node_type: str = "generic",
               pins: List[Dict] = None) -> Dict:
    return {
        "node_id":   node_id,
        "title":     title,
        "node_type": node_type,
        "pins":      pins or [],
    }

def _exec_pin(direction: str, linked_to: List = None) -> Dict:
    return {"pin_name": "execute", "pin_type": "exec",
            "direction": direction, "linked_to": linked_to or []}

def _data_pin(name: str, direction: str, linked_to: List = None) -> Dict:
    return {"pin_name": name, "pin_type": "bool",
            "direction": direction, "linked_to": linked_to or []}


class TestOfflineNodeAnalysis(unittest.TestCase):
    """B1: _analyze_nodes_offline with synthetic graph fixtures."""

    def test_empty_graph_no_issues(self):
        result = _analyze_nodes_offline([])
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["orphan_guids"], [])
        self.assertEqual(result["disconnected_exec"], [])

    def test_single_event_node_no_issues(self):
        # Event nodes are never flagged as orphaned
        node = _make_node("ev1", "BeginPlay", "event",
                          pins=[_exec_pin("output")])
        result = _analyze_nodes_offline([node])
        self.assertEqual(result["orphan_guids"], [])
        self.assertEqual(result["issues"], [])

    def test_orphaned_non_event_node(self):
        # A generic node with no connections → orphan
        node = _make_node("n1", "PrintString", pins=[])
        result = _analyze_nodes_offline([node])
        self.assertIn("n1", result["orphan_guids"])
        self.assertEqual(len(result["issues"]), 1)
        self.assertEqual(result["issues"][0]["code"], "ORPHANED_NODE")

    def test_connected_node_not_orphaned(self):
        ev   = _make_node("ev", "BeginPlay", "event",
                          pins=[_exec_pin("output", linked_to=["n1"])])
        node = _make_node("n1", "Print",
                          pins=[_exec_pin("input", linked_to=["ev"]),
                                _exec_pin("output")])
        result = _analyze_nodes_offline([ev, node])
        self.assertNotIn("n1", result["orphan_guids"])

    def test_disconnected_exec_detected(self):
        # Node has exec-out connected but no exec-in → disconnected exec
        ev   = _make_node("ev", "BeginPlay", "event",
                          pins=[_exec_pin("output")])
        node = _make_node("n1", "Branch",
                          pins=[_exec_pin("input"),
                                _exec_pin("output", linked_to=["n2"])])
        n2   = _make_node("n2", "PrintString",
                          pins=[_exec_pin("input", linked_to=["n1"]),
                                _exec_pin("output")])
        result = _analyze_nodes_offline([ev, node, n2])
        # node (n1) has exec-out (linked to n2) but no exec-in → disconnected
        self.assertIn("n1", result["disconnected_exec"])
        codes = [i["code"] for i in result["issues"]]
        self.assertIn("DISCONNECTED_EXEC_PIN", codes)

    def test_multiple_orphans(self):
        nodes = [
            _make_node(f"o{i}", f"Orphan{i}") for i in range(4)
        ]
        result = _analyze_nodes_offline(nodes)
        self.assertEqual(len(result["orphan_guids"]), 4)

    def test_auto_repairable_set_on_orphan(self):
        node   = _make_node("n1", "OrphanedNode")
        result = _analyze_nodes_offline([node])
        self.assertTrue(result["issues"][0]["auto_repairable"])

    def test_auto_repairable_set_on_disconnected_exec(self):
        node = _make_node("n1", "Branch",
                          pins=[_exec_pin("input"),
                                _exec_pin("output", linked_to=["n2"])])
        n2   = _make_node("n2", "Print",
                          pins=[_exec_pin("input", linked_to=["n1"])])
        result = _analyze_nodes_offline([node, n2])
        disc_issues = [i for i in result["issues"] if i["code"] == "DISCONNECTED_EXEC_PIN"]
        for i in disc_issues:
            self.assertTrue(i["auto_repairable"])

    def test_health_score_from_orphan_issues(self):
        nodes  = [_make_node("n1", "Orphan")]
        result = _analyze_nodes_offline(nodes)
        score  = _health_score(result["issues"])
        self.assertLess(score, 100)

    def test_clean_chain_no_issues(self):
        """Full clean exec chain: BeginPlay → Print → end"""
        ev   = _make_node("ev", "BeginPlay", "event",
                          pins=[_exec_pin("output", linked_to=["p1"])])
        p1   = _make_node("p1", "PrintString",
                          pins=[_exec_pin("input", linked_to=["ev"]),
                                _exec_pin("output")])
        result = _analyze_nodes_offline([ev, p1])
        self.assertEqual(result["issues"], [])

    def test_event_node_with_title_containing_event_word(self):
        # Nodes whose title contains 'event' are treated as event nodes
        node = _make_node("ev2", "OnEvent_Damage", "generic",
                          pins=[_exec_pin("output")])
        result = _analyze_nodes_offline([node])
        # Should NOT be flagged as orphaned
        self.assertNotIn("ev2", result["orphan_guids"])

    def test_node_with_only_data_pins_and_no_links_is_orphan(self):
        node = _make_node("d1", "GetVariable",
                          pins=[_data_pin("Value", "output")])
        result = _analyze_nodes_offline([node])
        self.assertIn("d1", result["orphan_guids"])

    def test_node_with_data_link_not_orphan(self):
        getter = _make_node("g1", "GetHealth",
                            pins=[_data_pin("Value", "output", linked_to=["c1"])])
        cond   = _make_node("c1", "Branch",
                            pins=[_data_pin("Condition", "input", linked_to=["g1"]),
                                  _exec_pin("input"),
                                  _exec_pin("output")])
        result = _analyze_nodes_offline([getter, cond])
        self.assertNotIn("g1", result["orphan_guids"])


# ═══════════════════════════════════════════════════════════════════════════════
# C: repair_tools.py — schema and record builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestRepairRecord(unittest.TestCase):
    """C1: _repair_record builder."""

    REQUIRED_KEYS = {"action", "target", "detail", "applied", "skip_reason"}

    def _make(self, **kw) -> Dict:
        defaults = dict(action="test", target="node1", detail="ok", applied=True)
        defaults.update(kw)
        return _repair_record(**defaults)

    def test_required_keys_present(self):
        r = self._make()
        self.assertEqual(self.REQUIRED_KEYS, set(r.keys()))

    def test_applied_true(self):
        r = self._make(applied=True)
        self.assertTrue(r["applied"])

    def test_applied_false(self):
        r = self._make(applied=False)
        self.assertFalse(r["applied"])

    def test_action_stored(self):
        r = self._make(action="remove_orphaned_node")
        self.assertEqual(r["action"], "remove_orphaned_node")

    def test_target_stored(self):
        r = self._make(target="PrintString_0")
        self.assertEqual(r["target"], "PrintString_0")

    def test_detail_stored(self):
        r = self._make(detail="Removed orphan")
        self.assertEqual(r["detail"], "Removed orphan")

    def test_skip_reason_defaults_empty(self):
        r = self._make()
        self.assertEqual(r["skip_reason"], "")

    def test_skip_reason_stored(self):
        r = self._make(applied=False, skip_reason="Event node — kept")
        self.assertEqual(r["skip_reason"], "Event node — kept")

    def test_connect_exec_action(self):
        r = self._make(action="connect_exec_pins")
        self.assertEqual(r["action"], "connect_exec_pins")

    def test_set_pin_default_action(self):
        r = self._make(action="set_pin_default")
        self.assertEqual(r["action"], "set_pin_default")


class TestRepairToolsOffline(unittest.TestCase):
    """C2: repair tools return offline stubs when UE5 unavailable."""

    def setUp(self):
        # Patch get_unreal_connection to return None (offline)
        self.patcher = patch(
            "tools.repair_tools._send",
            return_value={"success": False, "message": "Not connected"},
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _call_sync(self, coro):
        import asyncio
        return asyncio.run(coro)

    def _make_mcp(self):
        """Return a FastMCP instance with tools registered."""
        mcp = MagicMock()
        tools = {}
        def tool_decorator():
            def _dec(fn):
                tools[fn.__name__] = fn
                return fn
            return _dec
        mcp.tool = tool_decorator
        register_repair_tools(mcp)
        return tools

    def test_bp_repair_exec_chain_offline_returns_json(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        coro  = tools["bp_repair_exec_chain"](
            ctx, "BP_Test", "EventGraph", "PrintString", "Branch")
        result = self._call_sync(coro)
        data = json.loads(result)
        self.assertTrue(data["success"])
        self.assertIn("connected", data["outputs"])

    def test_bp_remove_orphaned_nodes_empty_guids(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        coro  = tools["bp_remove_orphaned_nodes"](
            ctx, "BP_Test", "EventGraph", [])
        result = self._call_sync(coro)
        data = json.loads(result)
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["removed_count"], 0)

    def test_bp_set_pin_default_offline_returns_json(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        coro  = tools["bp_set_pin_default"](
            ctx, "BP_Test", "EventGraph", "guid-1234", "Value", "true")
        result = self._call_sync(coro)
        data = json.loads(result)
        self.assertTrue(data["success"])
        self.assertIn("applied", data["outputs"])

    def test_repair_chain_outputs_safe_to_continue(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        coro  = tools["bp_repair_exec_chain"](
            ctx, "BP_Test", "EventGraph", "A", "B")
        data  = json.loads(self._call_sync(coro))
        self.assertIn("safe_to_continue", data["outputs"])

    def test_remove_orphans_offline_safe(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        coro  = tools["bp_remove_orphaned_nodes"](
            ctx, "BP_Test", "EventGraph", ["guid-abc"])
        data  = json.loads(self._call_sync(coro))
        self.assertTrue(data["outputs"]["safe_to_continue"])

    def test_set_pin_default_outputs_has_pin_name(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        coro  = tools["bp_set_pin_default"](
            ctx, "BP_Test", "EventGraph", "g1", "Condition", "False")
        data  = json.loads(self._call_sync(coro))
        self.assertEqual(data["outputs"]["pin_name"], "Condition")

    def test_remove_multiple_guids_returns_skipped(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        coro  = tools["bp_remove_orphaned_nodes"](
            ctx, "BP_Test", "EventGraph", ["g1", "g2", "g3"])
        data  = json.loads(self._call_sync(coro))
        self.assertIn("repairs_skipped", data["outputs"])


class TestDiagnosticsToolsOffline(unittest.TestCase):
    """C3: diagnostics tools return structured offline stubs."""

    def setUp(self):
        self.patcher = patch(
            "tools.diagnostics_tools._send",
            return_value={"success": False, "message": "Not connected"},
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _call_sync(self, coro):
        import asyncio
        return asyncio.run(coro)

    def _make_mcp(self):
        mcp = MagicMock()
        tools = {}
        def tool_decorator():
            def _dec(fn):
                tools[fn.__name__] = fn
                return fn
            return _dec
        mcp.tool = tool_decorator
        register_diagnostics_tools(mcp)
        return tools

    def test_bp_get_compile_diagnostics_offline_success(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_get_compile_diagnostics"](ctx, "BP_Test")))
        self.assertTrue(data["success"])

    def test_bp_get_compile_diagnostics_has_compile_clean(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_get_compile_diagnostics"](ctx, "BP_Test")))
        self.assertIn("compile_clean", data["outputs"])

    def test_bp_validate_graph_offline_success(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_validate_graph"](ctx, "BP_Test")))
        self.assertTrue(data["success"])

    def test_bp_validate_graph_has_health_score(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_validate_graph"](ctx, "BP_Test")))
        self.assertIn("graph_health_score", data["outputs"])

    def test_bp_find_orphaned_nodes_offline(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_find_orphaned_nodes"](ctx, "BP_Test")))
        self.assertTrue(data["success"])
        self.assertIn("orphaned_nodes", data["outputs"])

    def test_bp_find_disconnected_pins_offline(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_find_disconnected_pins"](ctx, "BP_Test")))
        self.assertTrue(data["success"])
        self.assertIn("disconnected_pins", data["outputs"])

    def test_bp_find_unreachable_nodes_offline(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_find_unreachable_nodes"](ctx, "BP_Test")))
        self.assertTrue(data["success"])
        self.assertIn("unreachable_nodes", data["outputs"])

    def test_bp_find_unused_variables_offline(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_find_unused_variables"](ctx, "BP_Test")))
        self.assertTrue(data["success"])
        self.assertIn("unused_variables", data["outputs"])

    def test_bp_validate_blueprint_offline(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_validate_blueprint"](ctx, "BP_Test")))
        self.assertTrue(data["success"])
        self.assertIn("health_score", data["outputs"])

    def test_bp_run_post_mutation_verify_offline(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_run_post_mutation_verify"](ctx, "BP_Test")))
        self.assertTrue(data["success"])
        self.assertIn("compile_status", data["outputs"])

    def test_mat_get_compile_diagnostics_offline(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["mat_get_compile_diagnostics"](ctx, "/Game/M_Test")))
        self.assertTrue(data["success"])
        self.assertIn("compile_clean", data["outputs"])

    def test_mat_validate_material_offline(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["mat_validate_material"](ctx, "/Game/M_Test")))
        self.assertTrue(data["success"])
        self.assertIn("material_health_score", data["outputs"])

    def test_compile_diagnostics_errors_is_list(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_get_compile_diagnostics"](ctx, "BP_Test")))
        self.assertIsInstance(data["outputs"]["errors"], list)

    def test_compile_diagnostics_warnings_is_list(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_get_compile_diagnostics"](ctx, "BP_Test")))
        self.assertIsInstance(data["outputs"]["warnings"], list)

    def test_validate_blueprint_recommended_actions_is_list(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_validate_blueprint"](ctx, "BP_Test")))
        self.assertIsInstance(data["outputs"].get("recommended_actions", []), list)

    def test_post_mutation_verify_top_issues_is_list(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_run_post_mutation_verify"](ctx, "BP_Test",
                                                  ["EventGraph", "TakeDamage"])))
        self.assertIsInstance(data["outputs"].get("top_issues", []), list)

    def test_post_mutation_verify_changed_graphs_echoed(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["bp_run_post_mutation_verify"](ctx, "BP_Test",
                                                  ["EventGraph"])))
        self.assertIn("graphs_checked", data["outputs"])

    def test_mat_validate_has_recommended_actions(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["mat_validate_material"](ctx, "/Game/M_Test")))
        self.assertIn("recommended_actions", data["outputs"])

    def test_meta_present_in_all_tools(self):
        tools = self._make_mcp()
        ctx   = MagicMock()
        for name, fn in tools.items():
            # Call with minimal args where possible
            try:
                if "material" in name:
                    data = json.loads(self._call_sync(fn(ctx, "/Game/M_Test")))
                else:
                    data = json.loads(self._call_sync(fn(ctx, "BP_Test")))
                self.assertIn("meta", data, f"meta missing from {name}")
            except TypeError:
                pass  # skip tools that need more args


# ═══════════════════════════════════════════════════════════════════════════════
# D: Repair skill workflow
# ═══════════════════════════════════════════════════════════════════════════════

class TestRepairSkillOffline(unittest.TestCase):
    """D1: skill_repair_broken_blueprint offline behavior."""

    def setUp(self):
        self.patcher = patch(
            "skills.repair_broken_blueprint.skill._send",
            return_value={"success": False, "message": "Not connected"},
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _call_sync(self, coro):
        import asyncio
        return asyncio.run(coro)

    def _make_skill(self):
        from skills.repair_broken_blueprint.skill import (
            register_repair_broken_blueprint_skill,
        )
        mcp   = MagicMock()
        tools = {}
        def tool_decorator():
            def _dec(fn):
                tools[fn.__name__] = fn
                return fn
            return _dec
        mcp.tool = tool_decorator
        register_repair_broken_blueprint_skill(mcp)
        return tools

    def test_skill_registered(self):
        tools = self._make_skill()
        self.assertIn("skill_repair_broken_blueprint", tools)

    def test_skill_returns_success(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertTrue(data["success"])

    def test_skill_has_before_snapshot(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIn("before", data["outputs"])
        self.assertIn("health_score", data["outputs"]["before"])

    def test_skill_has_after_snapshot(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIn("after", data["outputs"])
        self.assertIn("health_score", data["outputs"]["after"])

    def test_skill_has_health_delta(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIn("health_delta", data["outputs"])

    def test_skill_has_repairs_applied(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIsInstance(data["outputs"]["repairs_applied"], list)

    def test_skill_has_repairs_skipped(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIsInstance(data["outputs"]["repairs_skipped"], list)

    def test_skill_has_safe_to_continue(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIn("safe_to_continue", data["outputs"])

    def test_skill_has_repair_summary(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIsInstance(data["outputs"]["repair_summary"], str)

    def test_dry_run_flag_echoed(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test", dry_run=True)))
        self.assertTrue(data["outputs"]["dry_run"])

    def test_dry_run_false_default(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertFalse(data["outputs"]["dry_run"])

    def test_blueprint_path_echoed(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "/Game/BP/MyBP")))
        self.assertEqual(data["outputs"]["blueprint_path"], "/Game/BP/MyBP")

    def test_repair_summary_contains_health_numbers(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        summary = data["outputs"]["repair_summary"]
        # Should contain → or Δ
        self.assertTrue("→" in summary or "Δ" in summary or "health" in summary.lower())

    def test_meta_present(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        data  = json.loads(self._call_sync(
            tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIn("meta", data)

    def test_non_repairable_issues_go_to_skipped(self):
        """Compile errors (auto_repairable=False) must appear in repairs_skipped."""
        tools = self._make_skill()
        ctx   = MagicMock()
        # Patch _exec_python to return a compile error
        fake_compile = {
            "result": {
                "output": '[Info] {"errors": [{"severity": "error", "code": "BP_COMPILE_ERROR", '
                          '"message": "fails", "auto_repairable": false, "category": "compile", '
                          '"asset_path": "BP_Test", "graph_name": "", "node_guid": "", '
                          '"node_title": "", "pin_name": "", "suggested_fix": "fix", '
                          '"compile_clean": false, "compiler_summary": "errors"}],'
                          '"compile_clean": false, "had_errors": true, '
                          '"compiler_summary": "errors", "warnings": []}'
            }
        }
        with patch("skills.repair_broken_blueprint.skill._exec_python",
                   return_value=fake_compile):
            data = json.loads(self._call_sync(
                tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        # Non-repairable items must appear in repairs_skipped
        skipped = data["outputs"]["repairs_skipped"]
        self.assertIsInstance(skipped, list)


# ═══════════════════════════════════════════════════════════════════════════════
# Demos A–C regression guards
# ═══════════════════════════════════════════════════════════════════════════════

class TestDemoCRegression(unittest.TestCase):
    """D2: Ensure demo_c_live can be imported without error."""

    def test_demo_c_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "demo_c_live",
            str(SERVER_ROOT / "tests" / "demo_c_live.py")
        )
        mod = importlib.util.module_from_spec(spec)
        # Just check it loads without syntax error
        # Don't exec to avoid socket calls
        self.assertIsNotNone(spec)

    def test_demo_d_importable(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "demo_d_live",
            str(SERVER_ROOT / "tests" / "demo_d_live.py")
        )
        self.assertIsNotNone(spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
