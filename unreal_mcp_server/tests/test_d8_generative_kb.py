"""Static smoke coverage for Workstream D.8 generative KB runbooks."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestD8GenerativeKnowledgeBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        cls.recipe = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        cls.changelog = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")

    def test_pipeline_runbook_has_prompts_sequence_runtime_and_failures(self):
        for marker in (
            "## D8 Generative Runbook",
            "### Canonical Prompts",
            "### Expected Tool Sequence",
            "### Expected Runtime",
            "### Known Failure Modes",
            "### Evidence Contract",
            "TRIPO_API_KEY",
            "confirm_spend=True",
            "gen_tripo_wait_for_task",
            "gen_tripo_import_to_project",
        ):
            self.assertIn(marker, self.pipeline)

    def test_playable_slice_runbook_has_exact_demo_contract(self):
        for marker in (
            "## D8 Exact Playable-Slice Runbook",
            "### Exact Prompts",
            "### Expected Tool Sequence",
            "### Expected Runtime",
            "### Known Failure Modes",
            "### Minimum Green Report",
            "third-person dungeon-crawler demo",
            "skill_generate_playable_slice",
            "skill_package_vertical_slice_report",
            "60 seconds",
        ):
            self.assertIn(marker, self.recipe)

    def test_changelog_records_d8_kb_milestone(self):
        for marker in (
            "D.8 - Generative knowledge base runbooks",
            "31_GENERATIVE_CONTENT_PIPELINE.md",
            "32_AGENT_PLAYABLE_SLICE_RECIPE.md",
            "static smoke coverage",
        ):
            self.assertIn(marker, self.changelog)


if __name__ == "__main__":
    unittest.main()
