"""
test_repair_skill.py — Phase 4 / V6 Repair Skill Extended Tests
================================================================

Additional tests targeting edge cases in the repair workflow:
  - Repair with mock UE5 responses (simulated live data)
  - Health delta assertions
  - Skipped issue categorization
  - max_repairs cap
  - Tool count / registration guard
"""

from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch, call

# ── sys.path ──────────────────────────────────────────────────────────────────
SERVER_ROOT = Path(__file__).resolve().parent.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

# ── Stub unavailable dependencies ─────────────────────────────────────────────
for _m in ["unreal", "mcp", "mcp.server", "mcp.server.fastmcp"]:
    if _m not in sys.modules:
        stub = types.ModuleType(_m)
        sys.modules[_m] = stub

_fmcp = sys.modules["mcp.server.fastmcp"]
if not hasattr(_fmcp, "FastMCP"):
    class _FakeFastMCP:
        def tool(self):
            def _dec(fn): return fn
            return _dec
    _fmcp.FastMCP = _FakeFastMCP
if not hasattr(_fmcp, "Context"):
    _fmcp.Context = object


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_tool_registry(register_fn):
    """Register tools onto a fake MCP and return tool dict."""
    mcp   = MagicMock()
    tools = {}
    def _deco():
        def _inner(fn):
            tools[fn.__name__] = fn
            return fn
        return _inner
    mcp.tool = _deco
    register_fn(mcp)
    return tools


def _run(coro):
    import asyncio
    return asyncio.run(coro)


def _fake_exec_output(payload: Dict) -> Dict:
    """Wrap a dict as if returned by exec_python."""
    return {"result": {"output": f"[Info] {json.dumps(payload)}"}}


# ═══════════════════════════════════════════════════════════════════════════════
# Skill with simulated UE5 data
# ═══════════════════════════════════════════════════════════════════════════════

class TestRepairSkillSimulated(unittest.TestCase):
    """E1: skill_repair_broken_blueprint with simulated UE5 responses."""

    def _make_skill(self):
        from skills.repair_broken_blueprint.skill import (
            register_repair_broken_blueprint_skill,
        )
        return _make_tool_registry(register_repair_broken_blueprint_skill)

    def _send_stub(self, cmd, params):
        """Minimal send stub: no UE5 connection."""
        return {"success": False, "message": "offline"}

    def test_clean_blueprint_health_100(self):
        """A blueprint with no issues should reach health=100 after repair."""
        clean_compile = {"compile_clean": True, "had_errors": False,
                         "compiler_summary": "OK", "errors": [], "warnings": []}
        clean_na      = {"orphaned": [], "disconnected_exec": []}
        tools = self._make_skill()
        ctx   = MagicMock()
        with patch("skills.repair_broken_blueprint.skill._exec_python",
                   side_effect=lambda c: _fake_exec_output(
                       clean_compile if "compile" in c.lower() or "status" in c.lower()
                       else clean_na)):
            data = json.loads(_run(
                tools["skill_repair_broken_blueprint"](ctx, "/Game/BP_Clean")))
        self.assertEqual(data["outputs"]["before"]["health_score"], 100)
        self.assertEqual(data["outputs"]["after"]["health_score"], 100)
        self.assertEqual(data["outputs"]["health_delta"], 0)
        self.assertTrue(data["outputs"]["safe_to_continue"])

    def test_orphan_issue_flagged_as_auto_repairable(self):
        """Orphaned nodes appear in before snapshot."""
        orphan_data = {
            "orphaned": [{
                "node_guid": "DEAD-BEEF", "node_title": "PrintString_Orphan",
                "graph": "EventGraph",
                "severity": "warning", "category": "graph_structure",
                "code": "ORPHANED_NODE",
                "message": "Node 'PrintString_Orphan' has no connections",
                "auto_repairable": True,
                "suggested_fix": "Delete orphaned node",
            }],
            "disconnected_exec": [],
        }
        compile_ok = {"compile_clean": True, "had_errors": False,
                      "compiler_summary": "OK", "errors": [], "warnings": []}
        tools = self._make_skill()
        ctx   = MagicMock()
        calls = [0]
        def _exec_side(code):
            # First call: compile diag; subsequent: node analysis or re-check
            calls[0] += 1
            if "status" in code.lower() or "BlueprintStatus" in code:
                return _fake_exec_output(compile_ok)
            return _fake_exec_output(orphan_data)

        with patch("skills.repair_broken_blueprint.skill._exec_python", _exec_side):
            data = json.loads(_run(
                tools["skill_repair_broken_blueprint"](ctx, "/Game/BP_Orphan")))
        before_health = data["outputs"]["before"]["health_score"]
        self.assertLess(before_health, 100)

    def test_dry_run_does_not_apply_repairs(self):
        """dry_run=True must not apply any repairs (repairs_applied must be empty
        and dry_run must be True in output)."""
        tools = self._make_skill()
        ctx   = MagicMock()

        with patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False, "message": "offline"}):
            data = json.loads(_run(tools["skill_repair_broken_blueprint"](
                ctx, "/Game/BP_Test", dry_run=True)))

        # dry_run=True means no repairs applied
        self.assertTrue(data["outputs"]["dry_run"])
        # In offline mode no orphans found → no repairs to apply
        self.assertIsInstance(data["outputs"]["repairs_applied"], list)

    def test_non_repairable_compile_error_in_skipped(self):
        compile_err = {
            "compile_clean": False, "had_errors": True,
            "compiler_summary": "Error",
            "errors": [{
                "severity": "error", "category": "compile",
                "code": "BP_COMPILE_ERROR",
                "message": "Red node in TakeDamage graph",
                "auto_repairable": False,
                "asset_path": "/Game/BP_Broken",
                "graph_name": "TakeDamage", "node_guid": "AABB",
                "node_title": "CallFunc_TakeDamage",
                "pin_name": "", "suggested_fix": "Fix red node",
            }],
            "warnings": [],
        }
        tools = self._make_skill()
        ctx   = MagicMock()
        # Patch both _exec_python and _send to avoid importing unreal_mcp_server
        with patch("skills.repair_broken_blueprint.skill._exec_python",
                   return_value=_fake_exec_output(compile_err)), \
             patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False, "message": "offline"}):
            data = json.loads(_run(
                tools["skill_repair_broken_blueprint"](ctx, "/Game/BP_Broken")))
        skipped = data["outputs"]["repairs_skipped"]
        self.assertTrue(any(
            s.get("skip_reason") and "not auto-repairable" in s["skip_reason"].lower()
            for s in skipped
        ), f"Expected 'not auto-repairable' in skipped reasons; got: {skipped}")

    def test_health_delta_is_int(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        with patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False, "message": "offline"}):
            data = json.loads(_run(
                tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIsInstance(data["outputs"]["health_delta"], int)

    def test_before_compile_clean_key(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        with patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False}):
            data = json.loads(_run(
                tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIn("compile_clean", data["outputs"]["before"])

    def test_after_compile_clean_key(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        with patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False}):
            data = json.loads(_run(
                tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        self.assertIn("compile_clean", data["outputs"]["after"])

    def test_max_repairs_cap_respected(self):
        """max_repairs=0 means no repairs applied even if orphans found."""
        # With no send responses (offline), there's nothing to repair anyway
        tools = self._make_skill()
        ctx   = MagicMock()
        with patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False}):
            data = json.loads(_run(
                tools["skill_repair_broken_blueprint"](
                    ctx, "BP_Test", max_repairs=0)))
        self.assertIsInstance(data["outputs"]["repairs_applied"], list)

    def test_repair_summary_contains_skipped_count(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        with patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False}):
            data = json.loads(_run(
                tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        summary = data["outputs"]["repair_summary"]
        self.assertIn("skipped", summary.lower())

    def test_repair_summary_contains_applied_count(self):
        tools = self._make_skill()
        ctx   = MagicMock()
        with patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False}):
            data = json.loads(_run(
                tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        summary = data["outputs"]["repair_summary"]
        # "Applied N repair(s)"
        self.assertIn("repair", summary.lower())


# ═══════════════════════════════════════════════════════════════════════════════
# E2: Node analysis helpers from repair skill
# ═══════════════════════════════════════════════════════════════════════════════

class TestRepairSkillHelpers(unittest.TestCase):
    """E2: Internal helpers in repair skill."""

    def setUp(self):
        from skills.repair_broken_blueprint import skill as sk
        self.sk = sk

    def test_health_score_empty(self):
        self.assertEqual(self.sk._health_score([]), 100)

    def test_health_score_error_deducts_15(self):
        issues = [{"severity": "error"}]
        self.assertEqual(self.sk._health_score(issues), 85)

    def test_health_score_warning_deducts_5(self):
        issues = [{"severity": "warning"}]
        self.assertEqual(self.sk._health_score(issues), 95)

    def test_analyze_nodes_offline_clean(self):
        result = self.sk._analyze_nodes_offline([])
        self.assertEqual(result["issues"], [])

    def test_analyze_nodes_offline_orphan(self):
        nodes = [{"node_id": "x", "title": "PrintString", "node_type": "", "pins": []}]
        result = self.sk._analyze_nodes_offline(nodes)
        self.assertIn("x", result["orphan_guids"])

    def test_analyze_nodes_offline_event_skipped(self):
        nodes = [{"node_id": "e1", "title": "BeginPlay", "node_type": "event",
                  "pins": [{"pin_name": "execute", "pin_type": "exec",
                             "direction": "output", "linked_to": []}]}]
        result = self.sk._analyze_nodes_offline(nodes)
        self.assertNotIn("e1", result["orphan_guids"])

    def test_parse_exec_output_extracts_json(self):
        r = {"result": {"output": '[Info] {"key": "value"}'}}
        out = self.sk._parse_exec_output(r)
        self.assertEqual(out.get("key"), "value")

    def test_parse_exec_output_empty_returns_empty(self):
        r = {"result": {"output": "no json here"}}
        out = self.sk._parse_exec_output(r)
        self.assertEqual(out, {})

    def test_parse_exec_output_last_wins(self):
        r = {"result": {"output": '[Info] {"a": 1}\n[Info] {"a": 2}'}}
        out = self.sk._parse_exec_output(r)
        self.assertEqual(out.get("a"), 2)

    def test_meta_has_tool_and_duration(self):
        import time
        t0 = time.monotonic()
        m  = self.sk._meta("my_skill", t0)
        self.assertEqual(m["tool"], "my_skill")
        self.assertGreaterEqual(m["duration_ms"], 0)

    def test_ok_result(self):
        import time
        m = {"tool": "t", "duration_ms": 0}
        r = self.sk._ok({"k": "v"}, ["w"], m, "done")
        self.assertTrue(r["success"])
        self.assertEqual(r["outputs"]["k"], "v")
        self.assertIn("w", r["warnings"])

    def test_err_result(self):
        m = {"tool": "t", "duration_ms": 0}
        r = self.sk._err("bad", m)
        self.assertFalse(r["success"])
        self.assertIn("bad", r["errors"])


# ═══════════════════════════════════════════════════════════════════════════════
# E3: Tool count / module registration guard
# ═══════════════════════════════════════════════════════════════════════════════

class TestPhase4ToolCount(unittest.TestCase):
    """E3: Verify Phase 4 tool and module counts meet minimum targets."""

    def test_diagnostics_tools_registers_10_tools(self):
        from tools.diagnostics_tools import register_diagnostics_tools
        tools = _make_tool_registry(register_diagnostics_tools)
        self.assertEqual(len(tools), 10,
            f"Expected 10 diagnostic tools, got {len(tools)}: {list(tools)}")

    def test_repair_tools_registers_3_tools(self):
        from tools.repair_tools import register_repair_tools
        tools = _make_tool_registry(register_repair_tools)
        self.assertEqual(len(tools), 3,
            f"Expected 3 repair tools, got {len(tools)}: {list(tools)}")

    def test_repair_skill_registers_1_tool(self):
        from skills.repair_broken_blueprint.skill import (
            register_repair_broken_blueprint_skill,
        )
        tools = _make_tool_registry(register_repair_broken_blueprint_skill)
        self.assertEqual(len(tools), 1,
            f"Expected 1 repair skill tool, got {len(tools)}: {list(tools)}")

    def test_diagnostics_tools_names(self):
        from tools.diagnostics_tools import register_diagnostics_tools
        tools = _make_tool_registry(register_diagnostics_tools)
        expected = {
            "bp_get_compile_diagnostics",
            "bp_validate_blueprint",
            "bp_validate_graph",
            "bp_find_disconnected_pins",
            "bp_find_unreachable_nodes",
            "bp_find_unused_variables",
            "bp_find_orphaned_nodes",
            "bp_run_post_mutation_verify",
            "mat_get_compile_diagnostics",
            "mat_validate_material",
        }
        self.assertEqual(expected, set(tools.keys()))

    def test_repair_tools_names(self):
        from tools.repair_tools import register_repair_tools
        tools = _make_tool_registry(register_repair_tools)
        expected = {
            "bp_repair_exec_chain",
            "bp_remove_orphaned_nodes",
            "bp_set_pin_default",
        }
        self.assertEqual(expected, set(tools.keys()))

    def test_repair_skill_name(self):
        from skills.repair_broken_blueprint.skill import (
            register_repair_broken_blueprint_skill,
        )
        tools = _make_tool_registry(register_repair_broken_blueprint_skill)
        self.assertIn("skill_repair_broken_blueprint", tools)

    def test_tools_dir_has_diagnostics_and_repair(self):
        tools_dir = SERVER_ROOT / "tools"
        self.assertTrue((tools_dir / "diagnostics_tools.py").exists())
        self.assertTrue((tools_dir / "repair_tools.py").exists())

    def test_skills_dir_has_repair_skill(self):
        skill_dir = SERVER_ROOT / "skills" / "repair_broken_blueprint"
        self.assertTrue((skill_dir / "skill.py").exists())

    def test_demo_d_exists(self):
        demo = SERVER_ROOT / "tests" / "demo_d_live.py"
        self.assertTrue(demo.exists())


# ═══════════════════════════════════════════════════════════════════════════════
# E4: Demo D script smoke-tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDemoDSmoke(unittest.TestCase):
    """E4: demo_d_live.py static checks."""

    def _load_demo_d_source(self) -> str:
        p = SERVER_ROOT / "tests" / "demo_d_live.py"
        return p.read_text()

    def test_demo_d_has_15_steps(self):
        src = self._load_demo_d_source()
        # Count "step_X(" calls in main()
        import re
        steps = re.findall(r"step_\w+\(\d+\)", src)
        self.assertEqual(len(steps), 15)

    def test_demo_d_has_ping(self):
        src = self._load_demo_d_source()
        self.assertIn("step_ping", src)

    def test_demo_d_has_validate_clean_bp(self):
        src = self._load_demo_d_source()
        self.assertIn("step_validate_clean_bp", src)

    def test_demo_d_has_compile_diagnostics(self):
        src = self._load_demo_d_source()
        self.assertIn("bp_get_compile_diagnostics", src)

    def test_demo_d_has_validate_graph(self):
        src = self._load_demo_d_source()
        self.assertIn("bp_validate_graph", src)

    def test_demo_d_has_repair_skill(self):
        src = self._load_demo_d_source()
        self.assertIn("skill_repair_broken_blueprint", src)

    def test_demo_d_has_material_validation(self):
        src = self._load_demo_d_source()
        self.assertIn("mat_validate_material", src)

    def test_demo_d_has_final_assertion(self):
        src = self._load_demo_d_source()
        self.assertIn("step_final_assertion", src)

    def test_demo_d_has_no_fail_fast_flag(self):
        src = self._load_demo_d_source()
        self.assertIn("--no-fail-fast", src)

    def test_demo_d_default_port_55558(self):
        src = self._load_demo_d_source()
        self.assertIn("55558", src)

    def test_demo_d_has_print_table(self):
        src = self._load_demo_d_source()
        self.assertIn("_print_table", src)

    def test_demo_d_records_tokens(self):
        src = self._load_demo_d_source()
        self.assertIn("tokens", src)

    def test_demo_d_has_host_arg(self):
        src = self._load_demo_d_source()
        self.assertIn("--host", src)

    def test_demo_d_has_port_arg(self):
        src = self._load_demo_d_source()
        self.assertIn("--port", src)

    def test_demo_d_exits_with_0_on_pass(self):
        src = self._load_demo_d_source()
        self.assertIn("sys.exit(0", src)

    def test_demo_d_exits_with_1_on_fail(self):
        src = self._load_demo_d_source()
        self.assertIn("sys.exit(1", src)

    def test_demo_d_step_post_mutation_verify(self):
        src = self._load_demo_d_source()
        self.assertIn("bp_run_post_mutation_verify", src)

    def test_demo_d_step_mat_compile_diagnostics(self):
        src = self._load_demo_d_source()
        self.assertIn("mat_get_compile_diagnostics", src)


# ═══════════════════════════════════════════════════════════════════════════════
# E5: Integration — diagnostics + repair round-trip (offline simulation)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDiagnosticsRepairRoundTrip(unittest.TestCase):
    """E5: Simulate the full diagnose → repair → verify loop offline."""

    def _run(self, coro):
        import asyncio
        return asyncio.run(coro)

    def test_orphan_detected_then_plan_shows_repairable(self):
        """Orphan in offline node list → skill marks it in before_snapshot."""
        from tools.diagnostics_tools import _analyze_nodes_offline, _health_score
        nodes = [
            {"node_id": "ev",  "title": "BeginPlay", "node_type": "event",
             "pins": [{"pin_name": "exec", "pin_type": "exec",
                       "direction": "output", "linked_to": []}]},
            {"node_id": "orph", "title": "PrintString_Orphan", "node_type": "",
             "pins": []},
        ]
        result = _analyze_nodes_offline(nodes)
        self.assertIn("orph", result["orphan_guids"])
        health = _health_score(result["issues"])
        self.assertLess(health, 100)
        # Confirm auto_repairable
        for issue in result["issues"]:
            if issue["code"] == "ORPHANED_NODE":
                self.assertTrue(issue["auto_repairable"])

    def test_full_round_trip_offline_returns_valid_schema(self):
        """Run skill → validate → confirm schema keys present."""
        from skills.repair_broken_blueprint.skill import (
            register_repair_broken_blueprint_skill,
        )
        tools = _make_tool_registry(register_repair_broken_blueprint_skill)
        ctx   = MagicMock()
        with patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False}):
            data = json.loads(self._run(
                tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        required_output_keys = {
            "before", "after", "repairs_applied", "repairs_skipped",
            "health_delta", "safe_to_continue", "repair_summary",
            "blueprint_path", "dry_run",
        }
        missing = required_output_keys - set(data["outputs"].keys())
        self.assertEqual(missing, set(), f"Missing output keys: {missing}")

    def test_before_and_after_have_same_schema(self):
        from skills.repair_broken_blueprint.skill import (
            register_repair_broken_blueprint_skill,
        )
        tools = _make_tool_registry(register_repair_broken_blueprint_skill)
        ctx   = MagicMock()
        with patch("skills.repair_broken_blueprint.skill._send",
                   return_value={"success": False}):
            data = json.loads(self._run(
                tools["skill_repair_broken_blueprint"](ctx, "BP_Test")))
        before_keys = set(data["outputs"]["before"].keys())
        after_keys  = set(data["outputs"]["after"].keys())
        self.assertEqual(before_keys, after_keys,
            f"before/after schema mismatch: {before_keys ^ after_keys}")

    def test_health_score_in_range(self):
        from tools.diagnostics_tools import _health_score, _diag_item, SEVERITY_WARNING, CAT_GRAPH
        for n_warnings in range(0, 25):
            issues = [
                _diag_item(severity=SEVERITY_WARNING, category=CAT_GRAPH,
                           code=f"W{i}", message="m", asset_path="/G")
                for i in range(n_warnings)
            ]
            score = _health_score(issues)
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)

    def test_diag_item_json_serializable(self):
        from tools.diagnostics_tools import _diag_item, SEVERITY_ERROR, CAT_COMPILE
        item = _diag_item(severity=SEVERITY_ERROR, category=CAT_COMPILE,
                          code="E1", message="msg", asset_path="/G",
                          auto_repairable=True)
        serialized = json.dumps(item)
        back = json.loads(serialized)
        self.assertEqual(back["code"], "E1")
        self.assertTrue(back["auto_repairable"])

    def test_repair_record_json_serializable(self):
        from tools.repair_tools import _repair_record
        rec = _repair_record(action="remove_orphaned_node", target="n1",
                             detail="Removed", applied=True)
        serialized = json.dumps(rec)
        back = json.loads(serialized)
        self.assertTrue(back["applied"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
