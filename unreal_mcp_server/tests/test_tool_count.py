"""Offline guard for documented MCP tool count drift."""

from __future__ import annotations

import re
import unittest
import importlib.util
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent


def _load_inventory_module():
    spec = importlib.util.spec_from_file_location("tool_inventory", REPO_ROOT / "scripts" / "tool_inventory.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _static_tool_count() -> int:
    """Count registered FastMCP tools through the canonical inventory script."""
    return _load_inventory_module().build_inventory()["tool_count"]


class TestToolCountDocumentation(unittest.TestCase):
    def test_last_tool_count_matches_static_registry(self):
        expected = _static_tool_count()
        recorded = int((SERVER_ROOT / "tests" / "last_tool_count.txt").read_text(encoding="utf-8").strip())

        self.assertEqual(recorded, expected)

    def test_readme_tool_count_matches_static_registry(self):
        expected = _static_tool_count()
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        counts = {int(match) for match in re.findall(r"(\d+) registered MCP tools|registers \*\*(\d+) MCP tools", readme) for match in match if match}

        self.assertEqual(counts, {expected})

    def test_tool_inventory_has_categories_for_all_tool_modules(self):
        inventory = _load_inventory_module().build_inventory()

        self.assertEqual(inventory["missing_category_modules"], [])


if __name__ == "__main__":
    unittest.main()
