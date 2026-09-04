"""Regression coverage for retired UMG bridge routes."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


class _MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "bridge_command_audit",
        REPO_ROOT / "scripts" / "bridge_command_audit.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestPhase7UMGRouteRetirement(unittest.TestCase):
    def test_bridge_audit_has_no_python_missing_cpp_routes(self):
        audit = _load_audit_module()
        registry = audit.build_registry()

        self.assertEqual(registry["python_missing_cpp"], [])
        self.assertEqual(registry["counts"]["python_missing_cpp"], 0)

    def test_retired_umg_convenience_tool_returns_clear_status(self):
        from tools.umg_tools import register_umg_tools

        mcp = _MockMCP()
        register_umg_tools(mcp)

        result = mcp.tools["add_slider_to_widget"](
            ctx=None,
            widget_name="WBP_Test",
            slider_name="SensitivitySlider",
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "retired_route")
        self.assertEqual(result["tool"], "add_slider_to_widget")
        self.assertIn("no longer calls its retired native bridge route", result["message"])


if __name__ == "__main__":
    unittest.main()
