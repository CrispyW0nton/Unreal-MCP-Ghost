"""Offline tests for Phase 7 bridge command metadata auditing."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent


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


class TestPhase7BridgeCommandAudit(unittest.TestCase):
    def test_registry_reports_python_and_cpp_commands(self):
        audit = _load_audit_module()

        registry = audit.build_registry()

        self.assertEqual(registry["schema"], "unreal_mcp_bridge_command_registry.v1")
        self.assertEqual(registry["source_scope"], "git_tracked_worktree")
        self.assertGreaterEqual(registry["counts"]["python_referenced"], 250)
        self.assertGreaterEqual(registry["counts"]["cpp_routed"], 250)
        commands = {entry["command"]: entry for entry in registry["commands"]}
        self.assertIn("create_blueprint", commands)
        self.assertIn("exec_python", commands)
        self.assertGreater(commands["create_blueprint"]["python_references"], 0)
        self.assertGreater(commands["create_blueprint"]["cpp_routes"], 0)
        review = {entry["command"]: entry for entry in registry["cpp_unreferenced_review"]}
        self.assertIn("ping", review)
        self.assertEqual(review["ping"]["recommendation"], "needs_python_wrapper")
        self.assertIn("widget_set_property", review)
        self.assertEqual(review["widget_set_property"]["priority"], "high")

    def test_registry_snapshot_comparison_is_stable_after_write(self):
        audit = _load_audit_module()
        registry = audit.build_registry()

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            registry_path = Path(tmp) / "bridge_command_registry.json"
            audit.write_registry(registry, registry_path)
            recorded = audit.load_registry(registry_path)
            comparison = audit.compare_registry(registry, recorded)

            self.assertFalse(comparison["signature_changed"])
            self.assertEqual(comparison["new_commands"], [])
            self.assertEqual(comparison["removed_commands"], [])

    def test_markdown_report_names_current_drift_sections(self):
        audit = _load_audit_module()
        registry = audit.build_registry()
        markdown = audit.format_markdown(registry)

        self.assertIn("# Bridge Command Registry", markdown)
        self.assertIn("## Drift Summary", markdown)
        self.assertIn("## C++-Only Route Review", markdown)
        self.assertIn("## Commands By Category", markdown)
        self.assertIn("Python missing C++ routes", markdown)
        self.assertIn("widget_set_property", markdown)


if __name__ == "__main__":
    unittest.main()
