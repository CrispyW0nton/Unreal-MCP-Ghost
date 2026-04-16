"""
test_source_control.py — V5 Source Control tool tests
=====================================================

Tests for: sc_get_provider_info, sc_get_status, sc_get_changelist

All tests run offline — no UE5 or Perforce required.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

_HERE = os.path.dirname(__file__)
_SERVER_ROOT = os.path.dirname(_HERE)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)


def _parse(s) -> dict:
    return json.loads(s) if isinstance(s, str) else s


class _MockMCP:
    def __init__(self):
        self._tools = {}

    def tool(self):
        def dec(fn):
            self._tools[fn.__name__] = fn
            return fn
        return dec

    def get_tool(self, n):
        return self._tools.get(n)

    def list_tool_names(self):
        return list(self._tools.keys())


def _mock_ctx():
    return MagicMock()


# ── Registration ──────────────────────────────────────────────────────────────

class TestSourceControlRegistration(unittest.TestCase):

    def setUp(self):
        from tools.source_control_tools import register_source_control_tools
        self.mcp = _MockMCP()
        register_source_control_tools(self.mcp)

    def test_all_3_sc_tools_registered(self):
        expected = {"sc_get_provider_info", "sc_get_status", "sc_get_changelist"}
        missing  = expected - set(self.mcp.list_tool_names())
        self.assertEqual(missing, set(), f"Missing: {missing}")


# ── sc_get_provider_info tests ────────────────────────────────────────────────

class TestScGetProviderInfo(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from tools.source_control_tools import register_source_control_tools
        self.mcp = _MockMCP()
        register_source_control_tools(self.mcp)
        self.tool = self.mcp.get_tool("sc_get_provider_info")

    async def test_graceful_when_no_provider(self):
        """No provider configured → success=True, provider='None', available=False."""
        def _mock(code):
            return {"success": True, "result": {"provider": "None", "available": False}}
        with patch("tools.source_control_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx())
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["provider"], "None")
        self.assertFalse(data["outputs"]["available"])

    async def test_no_connection_still_succeeds(self):
        """Even when UE5 not reachable, returns success=True with stub data."""
        def _mock(code):
            return {"success": False, "message": "Not connected"}
        with patch("tools.source_control_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx())
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertIn("provider",  data["outputs"])
        self.assertIn("available", data["outputs"])

    async def test_perforce_provider_fields(self):
        """Perforce provider returns all expected fields."""
        def _mock(code):
            return {"success": True, "result": {
                "provider": "Perforce", "available": True,
                "workspace": "dev_workspace", "server": "localhost:1666", "user": "dev"
            }}
        with patch("tools.source_control_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx())
        data = _parse(result)
        self.assertTrue(data["success"])
        out = data["outputs"]
        self.assertEqual(out["provider"], "Perforce")
        self.assertTrue(out["available"])


# ── sc_get_status tests ───────────────────────────────────────────────────────

class TestScGetStatus(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from tools.source_control_tools import register_source_control_tools
        self.mcp = _MockMCP()
        register_source_control_tools(self.mcp)
        self.tool = self.mcp.get_tool("sc_get_status")

    async def test_returns_state_key(self):
        def _mock(code):
            return {"success": True, "result": {"path": "/Game/Blueprints/BP_HealthSystem",
                                                  "state": "unchanged", "revision": "#5"}}
        with patch("tools.source_control_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), path="/Game/Blueprints/BP_HealthSystem")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertIn("state", data["outputs"])

    async def test_no_connection_returns_unknown_not_error(self):
        """SC unavailable → success=True, state='unknown'."""
        def _mock(code):
            return {"success": False, "message": "Not connected"}
        with patch("tools.source_control_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), path="/Game/Blueprints/BP_HealthSystem")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertEqual(data["outputs"]["state"], "unknown")

    async def test_state_normalisation(self):
        """Raw 'checked out' → 'checked_out'."""
        def _mock(code):
            return {"success": True, "result": {"path": "/Game/X",
                                                  "state": "checked out", "revision": "#3"}}
        with patch("tools.source_control_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), path="/Game/X")
        data = _parse(result)
        self.assertEqual(data["outputs"]["state"], "checked_out")


# ── sc_get_changelist tests ───────────────────────────────────────────────────

class TestScGetChangelist(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        from tools.source_control_tools import register_source_control_tools
        self.mcp = _MockMCP()
        register_source_control_tools(self.mcp)
        self.tool = self.mcp.get_tool("sc_get_changelist")

    async def test_no_provider_returns_empty_files(self):
        def _mock(code):
            return {"success": True, "result": {"changelist": "default",
                                                  "description": "", "available": False, "files": []}}
        with patch("tools.source_control_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), changelist="default")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertFalse(data["outputs"]["available"])
        self.assertEqual(data["outputs"]["files"], [])

    async def test_no_connection_succeeds_with_stub(self):
        def _mock(code):
            return {"success": False, "message": "Not connected"}
        with patch("tools.source_control_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx())
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertIn("changelist", data["outputs"])

    async def test_with_files_returns_list(self):
        def _mock(code):
            return {"success": True, "result": {
                "changelist": "default", "description": "WIP", "available": True,
                "files": [{"path": "/Game/BP_Test.uasset", "state": "checked out"}]
            }}
        with patch("tools.source_control_tools._exec_python", side_effect=_mock):
            result = await self.tool(_mock_ctx(), changelist="default")
        data = _parse(result)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["outputs"]["files"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
