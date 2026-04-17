"""
Tests for skill_create_health_system (V4 Composition Skill)

These tests run offline (no live UE5 required).
They verify:
  1. The skill's result schema is correct
  2. The skill reports the right variables, functions, and steps
  3. The skill stops on fatal failures and reports the failing step
  4. The skill registration adds exactly 1 tool named 'skill_create_health_system'
  5. The MCP tool wrapper returns valid JSON

All UE5 calls are mocked via unittest.mock.patch.
"""

import asyncio
import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# ── Path setup ────────────────────────────────────────────────────────────────

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills"))


# ── Minimal FastMCP stub ──────────────────────────────────────────────────────

class _MockContext:
    pass


class _MockMCP:
    def __init__(self):
        self._tools = {}

    def tool(self):
        def decorator(fn):
            self._tools[fn.__name__] = fn
            return fn
        return decorator

    def list_tool_names(self):
        return list(self._tools.keys())


# ── Helper ────────────────────────────────────────────────────────────────────

def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def parse_result(json_str: str) -> dict:
    return json.loads(json_str)


# ── Mock UE5 responses ────────────────────────────────────────────────────────

def _make_success(result=None):
    return {"status": "success", "result": result or {"success": True}}


def _make_fail(msg="error"):
    return {"status": "error", "result": {"success": False, "message": msg}}


SUCCESS_CREATE_BP = {"status": "success", "result": {"success": True, "name": "BP_HealthSystem", "path": "/Game/Blueprints/BP_HealthSystem"}}
SUCCESS_ADD_VAR   = {"status": "success", "result": {"success": True, "variable_name": "Health"}}
SUCCESS_EVENT     = {"status": "success", "result": {"success": True, "node_id": "AAAA1111", "node_guid": "AAAA1111"}}
SUCCESS_FUNCTION  = {"status": "success", "result": {"success": True, "node_id": "BBBB2222", "node_guid": "BBBB2222"}}
SUCCESS_CONNECT   = {"status": "success", "result": {"success": True, "connection_verified": True}}
SUCCESS_SET_PIN   = {"status": "success", "result": {"success": True}}
SUCCESS_COMPILE   = {"status": "success", "result": {"success": True, "had_errors": False}}


def _mock_send_success(command, params):
    """Return appropriate success response for each command type."""
    responses = {
        "create_blueprint":              SUCCESS_CREATE_BP,
        "add_blueprint_variable":        SUCCESS_ADD_VAR,
        "add_blueprint_event_node":      SUCCESS_EVENT,
        "add_blueprint_function_node":   SUCCESS_FUNCTION,
        "connect_blueprint_nodes":       SUCCESS_CONNECT,
        "set_node_pin_value":            SUCCESS_SET_PIN,
        "compile_blueprint":             SUCCESS_COMPILE,
    }
    return responses.get(command, _make_success())


def _mock_exec_transactional_success(user_code, tx_name):
    """Mock successful exec_python calls for defaults and TakeDamage."""
    return {
        "success": True,
        "outputs": {
            "Health_default": "100.0",
            "MaxHealth_default": "100.0",
            "bIsDead_default": "false",
            "function_graph_created": True,
            "function_name": "TakeDamage",
            "nodes_added": ["Health_GET", "Subtract", "FClamp", "Health_SET", "LessEqual", "Branch", "bIsDead_SET", "PrintString"],
            "nodes_added_count": 8,
        },
        "warnings": [],
        "errors": [],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite 1 — Registration
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthSystemSkillRegistration(unittest.TestCase):

    def test_registers_exactly_one_tool(self):
        """skill registration must add exactly 1 MCP tool."""
        from skills.health_system import register_health_system_skill
        mock_mcp = _MockMCP()
        register_health_system_skill(mock_mcp)
        self.assertEqual(len(mock_mcp.list_tool_names()), 1)

    def test_tool_name_is_skill_create_health_system(self):
        """The registered tool must be named skill_create_health_system."""
        from skills.health_system import register_health_system_skill
        mock_mcp = _MockMCP()
        register_health_system_skill(mock_mcp)
        self.assertIn("skill_create_health_system", mock_mcp.list_tool_names())

    def test_tool_is_callable(self):
        """The registered tool must be async-callable."""
        from skills.health_system import register_health_system_skill
        mock_mcp = _MockMCP()
        register_health_system_skill(mock_mcp)
        tool_fn = mock_mcp._tools["skill_create_health_system"]
        self.assertTrue(asyncio.iscoroutinefunction(tool_fn))


# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite 2 — Happy Path
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthSystemSkillHappyPath(unittest.TestCase):

    def _run_skill(self, **kwargs):
        """Run the skill function with full mocks."""
        with patch("skills.health_system._send", side_effect=_mock_send_success), \
             patch("skills.health_system._exec_transactional",
                   side_effect=_mock_exec_transactional_success):
            from skills.health_system import skill_create_health_system
            return skill_create_health_system(**kwargs)

    def test_success_flag_is_true(self):
        result = self._run_skill()
        self.assertTrue(result["success"], f"Expected success=True, got: {result}")

    def test_stage_is_correct(self):
        result = self._run_skill()
        self.assertEqual(result["stage"], "skill_create_health_system")

    def test_message_contains_blueprint_name(self):
        result = self._run_skill(blueprint_name="BP_TestHealth")
        self.assertIn("BP_TestHealth", result["message"])

    def test_variables_created(self):
        result = self._run_skill()
        vars_created = result["outputs"]["variables_created"]
        self.assertIn("Health", vars_created)
        self.assertIn("MaxHealth", vars_created)
        self.assertIn("bIsDead", vars_created)

    def test_functions_created(self):
        result = self._run_skill()
        funcs = result["outputs"]["functions_created"]
        self.assertIn("TakeDamage", funcs)

    def test_compile_result_is_clean(self):
        result = self._run_skill()
        self.assertEqual(result["outputs"]["compile_result"], "clean")

    def test_no_steps_failed(self):
        result = self._run_skill()
        self.assertEqual(result["outputs"]["steps_failed"], [])

    def test_steps_completed_contains_key_steps(self):
        result = self._run_skill()
        completed = result["outputs"]["steps_completed"]
        required_steps = [
            "create_blueprint",
            "add_variable_Health",
            "add_variable_MaxHealth",
            "add_variable_bIsDead",
            "add_function_TakeDamage",
            "add_BeginPlay_node",
            "add_PrintString_node",
            "connect_BeginPlay_PrintString",
            "compile",
        ]
        for step in required_steps:
            self.assertIn(step, completed, f"Expected step '{step}' in steps_completed")

    def test_blueprint_path_is_correct(self):
        result = self._run_skill(
            blueprint_name="BP_TestHealth",
            blueprint_path="/Game/TestFolder"
        )
        self.assertEqual(result["outputs"]["blueprint_path"], "/Game/TestFolder/BP_TestHealth")

    def test_exec_python_steps_reported(self):
        result = self._run_skill()
        ep_steps = result["outputs"]["exec_python_steps"]
        self.assertGreater(len(ep_steps), 0,
            "exec_python_steps must be non-empty (skill uses exec_python for defaults + TakeDamage)")

    def test_errors_list_is_empty_on_success(self):
        result = self._run_skill()
        self.assertEqual(result["errors"], [])

    def test_custom_initial_values(self):
        """Skill must pass custom initial values through."""
        result = self._run_skill(
            blueprint_name="BP_TestHealth",
            initial_health=150.0,
            initial_max_health=200.0
        )
        # skill should succeed and blueprint_path should reflect the name
        self.assertTrue(result["success"])
        self.assertIn("BP_TestHealth", result["outputs"]["blueprint_path"])

    def test_mcp_tool_returns_valid_json(self):
        """The MCP tool wrapper must return valid JSON string."""
        from skills.health_system import register_health_system_skill
        mock_mcp = _MockMCP()
        register_health_system_skill(mock_mcp)
        tool_fn = mock_mcp._tools["skill_create_health_system"]
        ctx = _MockContext()

        with patch("skills.health_system._send", side_effect=_mock_send_success), \
             patch("skills.health_system._exec_transactional",
                   side_effect=_mock_exec_transactional_success):
            result_str = run_async(tool_fn(ctx))

        self.assertIsInstance(result_str, str)
        parsed = json.loads(result_str)
        self.assertIn("success", parsed)
        self.assertIn("outputs", parsed)


# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite 3 — Failure Modes
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthSystemSkillFailureModes(unittest.TestCase):

    def _run_with_fail_on(self, fail_command: str, **kwargs):
        """Run skill with one specific command failing."""
        def _mock_send(command, params):
            if command == fail_command:
                return _make_fail(f"Simulated failure for {command}")
            return _mock_send_success(command, params)

        with patch("skills.health_system._send", side_effect=_mock_send), \
             patch("skills.health_system._exec_transactional",
                   side_effect=_mock_exec_transactional_success):
            from skills.health_system import skill_create_health_system
            return skill_create_health_system(**kwargs)

    def test_create_blueprint_failure_stops_immediately(self):
        """If create_blueprint fails, skill must stop and return success=False."""
        result = self._run_with_fail_on("create_blueprint")
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "create_blueprint")
        # No variables should have been created
        self.assertEqual(result["outputs"]["variables_created"], [])

    def test_add_variable_health_failure_stops(self):
        """If add Health variable fails, skill must stop."""
        result = self._run_with_fail_on("add_blueprint_variable")
        self.assertFalse(result["success"])
        self.assertIn("Health", result["stage"])

    def test_failure_result_has_structured_error(self):
        """Failure result must include errors list with description."""
        result = self._run_with_fail_on("create_blueprint")
        self.assertGreater(len(result["errors"]), 0)
        self.assertIsInstance(result["errors"][0], str)

    def test_compile_failure_sets_compile_result_to_errors(self):
        """If compile fails, compile_result must be 'errors' and success=False."""
        def _mock_send_compile_fail(command, params):
            if command == "compile_blueprint":
                return {"status": "success", "result": {"success": True, "had_errors": True}}
            return _mock_send_success(command, params)

        with patch("skills.health_system._send", side_effect=_mock_send_compile_fail), \
             patch("skills.health_system._exec_transactional",
                   side_effect=_mock_exec_transactional_success):
            from skills.health_system import skill_create_health_system
            result = skill_create_health_system()

        self.assertEqual(result["outputs"]["compile_result"], "errors")
        self.assertFalse(result["success"])

    def test_exec_python_failure_in_takedamage_is_non_fatal(self):
        """TakeDamage body wiring failure is non-fatal — skill continues."""
        def _mock_transactional(user_code, tx_name):
            if "wire_takedamage" in tx_name.lower() or "takedamage" in tx_name.lower():
                return {"success": False, "message": "Simulated wiring failure"}
            return _mock_exec_transactional_success(user_code, tx_name)

        with patch("skills.health_system._send", side_effect=_mock_send_success), \
             patch("skills.health_system._exec_transactional",
                   side_effect=_mock_transactional):
            from skills.health_system import skill_create_health_system
            result = skill_create_health_system()

        # Compile should still run despite wiring failure
        self.assertIn("compile", result["outputs"]["steps_completed"])
        # Warning should be added
        self.assertTrue(
            any("TakeDamage" in w or "takedamage" in w.lower() or "wire" in w.lower()
                for w in result["outputs"].get("steps_failed", []) + result.get("warnings", [])),
            f"Expected TakeDamage wiring warning. Got: {result.get('warnings')}, failed: {result['outputs'].get('steps_failed')}"
        )

    def test_failure_reports_partial_state(self):
        """Even on failure, outputs must report what was completed before failure."""
        def _mock_send(command, params):
            if command == "compile_blueprint":
                return _make_fail("compile failed")
            return _mock_send_success(command, params)

        with patch("skills.health_system._send", side_effect=_mock_send), \
             patch("skills.health_system._exec_transactional",
                   side_effect=_mock_exec_transactional_success):
            from skills.health_system import skill_create_health_system
            result = skill_create_health_system()

        # Variables should have been created before compile was attempted
        self.assertIn("Health", result["outputs"]["variables_created"])
        self.assertIn("MaxHealth", result["outputs"]["variables_created"])


# ═══════════════════════════════════════════════════════════════════════════════
# Test Suite 4 — Output Schema Validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthSystemSkillSchema(unittest.TestCase):

    def _run_skill(self):
        with patch("skills.health_system._send", side_effect=_mock_send_success), \
             patch("skills.health_system._exec_transactional",
                   side_effect=_mock_exec_transactional_success):
            from skills.health_system import skill_create_health_system
            return skill_create_health_system()

    def test_result_has_success_key(self):
        self.assertIn("success", self._run_skill())

    def test_result_has_stage_key(self):
        self.assertIn("stage", self._run_skill())

    def test_result_has_message_key(self):
        self.assertIn("message", self._run_skill())

    def test_result_has_outputs_key(self):
        self.assertIn("outputs", self._run_skill())

    def test_result_has_warnings_key(self):
        self.assertIn("warnings", self._run_skill())

    def test_result_has_errors_key(self):
        self.assertIn("errors", self._run_skill())

    def test_outputs_has_blueprint_path(self):
        self.assertIn("blueprint_path", self._run_skill()["outputs"])

    def test_outputs_has_variables_created(self):
        self.assertIn("variables_created", self._run_skill()["outputs"])

    def test_outputs_has_functions_created(self):
        self.assertIn("functions_created", self._run_skill()["outputs"])

    def test_outputs_has_event_graph_nodes(self):
        self.assertIn("event_graph_nodes", self._run_skill()["outputs"])

    def test_outputs_has_connections_made(self):
        self.assertIn("connections_made", self._run_skill()["outputs"])

    def test_outputs_has_compile_result(self):
        self.assertIn("compile_result", self._run_skill()["outputs"])

    def test_outputs_has_exec_python_steps(self):
        self.assertIn("exec_python_steps", self._run_skill()["outputs"])

    def test_outputs_has_steps_completed(self):
        self.assertIn("steps_completed", self._run_skill()["outputs"])

    def test_outputs_has_steps_failed(self):
        self.assertIn("steps_failed", self._run_skill()["outputs"])

    def test_compile_result_is_valid_value(self):
        result = self._run_skill()
        self.assertIn(result["outputs"]["compile_result"], ["clean", "errors", "unknown"])

    def test_variables_created_is_list(self):
        result = self._run_skill()
        self.assertIsInstance(result["outputs"]["variables_created"], list)

    def test_functions_created_is_list(self):
        result = self._run_skill()
        self.assertIsInstance(result["outputs"]["functions_created"], list)

    def test_steps_completed_is_list(self):
        result = self._run_skill()
        self.assertIsInstance(result["outputs"]["steps_completed"], list)

    def test_steps_failed_is_list(self):
        result = self._run_skill()
        self.assertIsInstance(result["outputs"]["steps_failed"], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
