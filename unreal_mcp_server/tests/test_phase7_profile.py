"""Offline tests for Phase 7 startup/profile smoke tooling."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent


def _load_profile_module():
    spec = importlib.util.spec_from_file_location(
        "profile_mcp_startup",
        REPO_ROOT / "scripts" / "profile_mcp_startup.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestPhase7StartupProfile(unittest.TestCase):
    def test_collect_profile_reports_inventory_and_timings(self):
        profiler = _load_profile_module()

        profile = profiler.collect_profile(iterations=1, top=3)

        self.assertEqual(profile["schema"], "unreal_mcp_startup_profile.v1")
        self.assertGreaterEqual(profile["inventory"]["tool_count"], 500)
        self.assertGreaterEqual(profile["inventory"]["module_count"], 30)
        self.assertEqual(profile["inventory"]["missing_category_modules"], [])
        self.assertTrue(profile["timings"]["inventory_build_in_process"]["ok"])
        self.assertIn("tool_inventory_subprocess", profile["timings"]["commands"])
        self.assertLessEqual(len(profile["slowest_module_scans"]), 3)

    def test_markdown_report_contains_ci_relevant_sections(self):
        profiler = _load_profile_module()
        profile = profiler.collect_profile(iterations=1, top=2)

        markdown = profiler.format_markdown(profile)

        self.assertIn("# MCP Startup Profile", markdown)
        self.assertIn("## Timing Summary", markdown)
        self.assertIn("## Slowest Decorator Scans", markdown)
        self.assertIn("## Registry Health", markdown)
        self.assertIn("All tool modules have category metadata.", markdown)

    def test_write_reports_creates_json_and_markdown(self):
        profiler = _load_profile_module()
        profile = profiler.collect_profile(iterations=1, top=1)

        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as tmp:
            tmp_path = Path(tmp)
            json_out = tmp_path / "profile.json"
            markdown_out = tmp_path / "profile.md"

            profiler.write_reports(profile, json_out=json_out, markdown_out=markdown_out)

            self.assertTrue(json_out.exists())
            self.assertTrue(markdown_out.exists())
            self.assertIn("unreal_mcp_startup_profile.v1", json_out.read_text(encoding="utf-8"))
            self.assertIn("# MCP Startup Profile", markdown_out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
