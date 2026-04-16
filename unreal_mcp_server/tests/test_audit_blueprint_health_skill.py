"""
test_audit_blueprint_health_skill.py
=====================================
Tests for skill_audit_blueprint_health (V5).

Tests cover:
  1. Happy path on BP_HealthSystem-like mock (clean compile, 3 vars)
  2. Bogus path failure (Blueprint not found)
  3. Disconnected exec pin warning (execution chain broken)
  4. Unused variable warning
  5. Compile-broken penalty (health_score drops by 30)
  6. Score formula validation
  7. Schema contract — all required keys present
  8. Registration — tool is discoverable

These tests do NOT require a live UE5 connection.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock, patch

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(__file__)
_SERVER_ROOT = os.path.dirname(_HERE)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _parse(s) -> dict:
    if isinstance(s, dict):
        return s
    return json.loads(s)


def _assert_schema(result_str, test_name=""):
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
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn
        return decorator

    def get_tool(self, name):
        return self._tools.get(name)

    def list_tool_names(self):
        return list(self._tools.keys())


def _mock_ctx():
    return MagicMock()


# ── Shared mock responses ─────────────────────────────────────────────────────

def _healthy_bp_responses():
    """Simulate a clean BP_HealthSystem with 3 vars and 1 function graph."""
    return {
        "get_blueprint_nodes:EventGraph": {
            "success": True,
            "nodes": [
                {
                    "node_id": "BP-EVENT-001",
                    "node_name": "K2Node_Event",
                    "node_type": "event",
                    "title": "BeginPlay",
                    "pos_x": -400, "pos_y": 0,
                    "pins": [
                        {"pin_name": "then", "direction": "output", "pin_type": "exec",
                         "default_value": "", "linked_to": [{"node_id": "BP-PRINT-001", "pin_name": "execute"}]},
                    ],
                },
                {
                    "node_id": "BP-PRINT-001",
                    "node_name": "K2Node_CallFunction",
                    "node_type": "function",
                    "title": "PrintString",
                    "pos_x": 0, "pos_y": 0,
                    "pins": [
                        {"pin_name": "execute", "direction": "input", "pin_type": "exec",
                         "default_value": "", "linked_to": [{"node_id": "BP-EVENT-001", "pin_name": "then"}]},
                        {"pin_name": "then", "direction": "output", "pin_type": "exec",
                         "default_value": "", "linked_to": []},
                        {"pin_name": "InString", "direction": "input", "pin_type": "string",
                         "default_value": "[HealthSystem] Initialized", "linked_to": []},
                    ],
                },
            ],
        },
        "get_blueprint_nodes:TakeDamage": {
            "success": True,
            "nodes": [
                {
                    "node_id": "TD-ENTRY-001",
                    "node_name": "K2Node_FunctionEntry",
                    "node_type": "function",
                    "title": "TakeDamage",
                    "pos_x": -400, "pos_y": 0,
                    "pins": [
                        {"pin_name": "then", "direction": "output", "pin_type": "exec",
                         "default_value": "", "linked_to": [{"node_id": "TD-SUB-001", "pin_name": "execute"}]},
                    ],
                },
            ],
        },
        "exec_python:variables": {
            "success": True,
            "result": {"variables": ["Health", "MaxHealth", "bIsDead"], "function_graphs": ["TakeDamage"]},
        },
        "compile_blueprint": {
            "success": True,
            "result": {"had_errors": False},
        },
        "exec_python:references": {
            "success": True,
            "result": {"count": 2},
        },
    }


def _make_send_mock(responses_by_command):
    """Return a _send patch that dispatches based on command name."""
    def mock_send(command: str, params: dict):
        if command == "get_blueprint_nodes":
            graph_name = params.get("graph_name", "EventGraph")
            key = f"get_blueprint_nodes:{graph_name}"
            if key in responses_by_command:
                return responses_by_command[key]
            # Default: empty nodes (blueprint not found)
            return {"success": False, "message": f"Blueprint not found: {params.get('blueprint_name', '?')}"}
        if command == "exec_python":
            code = params.get("code", "")
            if "function_graphs" in code or "variables" in code:
                return responses_by_command.get("exec_python:variables",
                                                {"success": True, "result": {"variables": [], "function_graphs": []}})
            if "get_referencers" in code:
                return responses_by_command.get("exec_python:references",
                                                {"success": True, "result": {"count": 0}})
            return {"success": True, "result": {}}
        if command == "compile_blueprint":
            return responses_by_command.get("compile_blueprint",
                                            {"success": True, "result": {"had_errors": False}})
        return {"success": True, "result": {}}
    return mock_send


# ── Tests: Registration ───────────────────────────────────────────────────────

class TestAuditSkillRegistration(unittest.TestCase):

    def test_skill_registers(self):
        from skills.audit_blueprint_health.skill import register_audit_blueprint_health_skill
        mcp = _MockMCP()
        register_audit_blueprint_health_skill(mcp)
        self.assertIn("skill_audit_blueprint_health", mcp.list_tool_names())


# ── Tests: Schema ─────────────────────────────────────────────────────────────

class TestAuditSkillSchema(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from skills.audit_blueprint_health.skill import register_audit_blueprint_health_skill
        self.mcp = _MockMCP()
        register_audit_blueprint_health_skill(self.mcp)
        self.tool = self.mcp.get_tool("skill_audit_blueprint_health")

    async def test_schema_all_keys_present(self):
        responses = _healthy_bp_responses()
        with patch("skills.audit_blueprint_health.skill._send", side_effect=_make_send_mock(responses)):
            result = await self.tool(_mock_ctx(), blueprint_name="BP_HealthSystem")
        data = _assert_schema(result, "schema")
        # Verify outputs keys
        out = data["outputs"]
        for key in ("compiles_clean", "variable_count", "function_graph_count",
                    "node_count_total", "disconnected_exec_pins", "disconnected_input_pins",
                    "unused_variables", "incoming_references", "warnings", "health_score"):
            self.assertIn(key, out, f"Missing output key: {key}")


# ── Tests: Happy path ─────────────────────────────────────────────────────────

class TestAuditSkillHappyPath(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from skills.audit_blueprint_health.skill import register_audit_blueprint_health_skill
        self.mcp = _MockMCP()
        register_audit_blueprint_health_skill(self.mcp)
        self.tool = self.mcp.get_tool("skill_audit_blueprint_health")

    async def test_happy_path_bp_health_system(self):
        """Happy path: BP_HealthSystem-like blueprint, clean compile, 3 vars."""
        responses = _healthy_bp_responses()
        with patch("skills.audit_blueprint_health.skill._send", side_effect=_make_send_mock(responses)):
            result = await self.tool(_mock_ctx(), blueprint_name="BP_HealthSystem")
        data = _parse(result)
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertTrue(out["compiles_clean"])
        self.assertEqual(out["variable_count"], 3)
        self.assertEqual(out["function_graph_count"], 1)
        self.assertGreater(out["node_count_total"], 0)
        # Score should be high (≥70) for a clean compile with no exec disconnects
        self.assertGreaterEqual(out["health_score"], 70)

    async def test_happy_path_incoming_references(self):
        """incoming_references is correctly populated from exec_python."""
        responses = _healthy_bp_responses()
        with patch("skills.audit_blueprint_health.skill._send", side_effect=_make_send_mock(responses)):
            result = await self.tool(_mock_ctx(), blueprint_name="BP_HealthSystem")
        out = _parse(result)["outputs"]
        self.assertEqual(out["incoming_references"], 2)


# ── Tests: Failure paths ──────────────────────────────────────────────────────

class TestAuditSkillFailurePaths(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from skills.audit_blueprint_health.skill import register_audit_blueprint_health_skill
        self.mcp = _MockMCP()
        register_audit_blueprint_health_skill(self.mcp)
        self.tool = self.mcp.get_tool("skill_audit_blueprint_health")

    async def test_bogus_blueprint_path_fails(self):
        """Blueprint not found → success=False with error message."""
        def fail_send(command, params):
            if command == "get_blueprint_nodes":
                return {"success": False, "message": "Blueprint not found"}
            return {"success": True, "result": {}}

        with patch("skills.audit_blueprint_health.skill._send", side_effect=fail_send):
            result = await self.tool(_mock_ctx(), blueprint_name="BP_DoesNotExist_XYZ")
        data = _parse(result)
        self.assertFalse(data["success"])
        self.assertIn("not accessible", data["message"])

    async def test_disconnected_exec_pin_warning(self):
        """Disconnected exec pin → warning and -10 to score."""
        responses = _healthy_bp_responses()
        # Modify BeginPlay so 'then' is not connected
        responses["get_blueprint_nodes:EventGraph"]["nodes"][0]["pins"][0]["linked_to"] = []

        with patch("skills.audit_blueprint_health.skill._send", side_effect=_make_send_mock(responses)):
            result = await self.tool(_mock_ctx(), blueprint_name="BP_HealthSystem")
        data = _parse(result)
        out = data["outputs"]
        self.assertGreater(len(out["disconnected_exec_pins"]), 0)
        self.assertLess(out["health_score"], 100)
        self.assertTrue(any("disconnected exec" in w for w in out["warnings"]))

    async def test_unused_variable_warning(self):
        """Unused variable → warning and -5 to score."""
        responses = _healthy_bp_responses()
        # Add an extra variable that's never referenced in nodes
        responses["exec_python:variables"]["result"]["variables"] = [
            "Health", "MaxHealth", "bIsDead", "UnusedVar"
        ]

        with patch("skills.audit_blueprint_health.skill._send", side_effect=_make_send_mock(responses)):
            result = await self.tool(_mock_ctx(), blueprint_name="BP_HealthSystem")
        data = _parse(result)
        out = data["outputs"]
        self.assertIn("UnusedVar", out.get("unused_variables", []))
        self.assertTrue(any("unused variable" in w for w in out["warnings"]))

    async def test_compile_broken_penalty(self):
        """Compile failure → score drops by 30."""
        responses = _healthy_bp_responses()
        responses["compile_blueprint"]["result"]["had_errors"] = True

        with patch("skills.audit_blueprint_health.skill._send", side_effect=_make_send_mock(responses)):
            result = await self.tool(_mock_ctx(), blueprint_name="BP_HealthSystem")
        data = _parse(result)
        out = data["outputs"]
        self.assertFalse(out["compiles_clean"])
        self.assertLessEqual(out["health_score"], 70)  # 100 - 30 = 70

    async def test_compile_check_disabled(self):
        """compile_check=False → compiles_clean remains True (assumed)."""
        responses = _healthy_bp_responses()

        with patch("skills.audit_blueprint_health.skill._send", side_effect=_make_send_mock(responses)):
            result = await self.tool(_mock_ctx(), blueprint_name="BP_HealthSystem", compile_check=False)
        data = _parse(result)
        self.assertTrue(data["success"])
        # With no compile step, compiles_clean defaults to True (not penalised)
        self.assertTrue(data["outputs"]["compiles_clean"])


# ── Tests: Score formula ──────────────────────────────────────────────────────

class TestHealthScoreFormula(unittest.TestCase):

    def _score(self, compiles=True, disc_exec=0, disc_inputs=0, unused=0):
        from skills.audit_blueprint_health.skill import _compute_score
        return _compute_score(
            compiles,
            [{}] * disc_exec,
            [{}] * disc_inputs,
            ["x"] * unused,
        )

    def test_perfect_score(self):
        self.assertEqual(self._score(), 100)

    def test_compile_fail_penalty(self):
        self.assertEqual(self._score(compiles=False), 70)

    def test_exec_pin_penalty_capped(self):
        # 3 disconnected exec pins → capped at -20
        self.assertEqual(self._score(disc_exec=3), 80)

    def test_unused_var_penalty_capped(self):
        # 4 unused vars → capped at -15
        self.assertEqual(self._score(unused=4), 85)

    def test_all_penalties_clamped_to_zero(self):
        # Worst possible: compile fail + 3 exec pins + 4 unused vars + 3 input pins
        score = self._score(compiles=False, disc_exec=3, disc_inputs=3, unused=4)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)


if __name__ == "__main__":
    unittest.main()
