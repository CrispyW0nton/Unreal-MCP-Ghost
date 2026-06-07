"""Offline guard for FastMCP tool docstring metadata."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent


def _load_docstring_linter():
    spec = importlib.util.spec_from_file_location(
        "lint_tool_docstrings",
        REPO_ROOT / "scripts" / "lint_tool_docstrings.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_tool_inventory():
    spec = importlib.util.spec_from_file_location(
        "tool_inventory",
        REPO_ROOT / "scripts" / "tool_inventory.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class TestToolDocstrings(unittest.TestCase):
    def test_all_tracked_tools_have_kb_links_and_examples(self):
        result = _load_docstring_linter().lint_tool_docstrings()
        inventory = _load_tool_inventory().build_inventory()

        self.assertEqual(result["source_scope"], "git_tracked_worktree")
        self.assertEqual(result["checked"], inventory["tool_count"])
        self.assertEqual(result["violations"], [])


if __name__ == "__main__":
    unittest.main()
