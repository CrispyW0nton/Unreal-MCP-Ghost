"""Static checks for the MCP Chat gameplay builder quick action."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
PLAYABLE_KB = REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class GameplayBuilderQuickActionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.kb = PLAYABLE_KB.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_gameplay_builder_surface_is_declared(self) -> None:
        for symbol in (
            "HandleOpenGameplayBuilderClicked",
            "HandleInsertGameplayBuilderPromptClicked",
            "HandleGameplayModeMechanicClicked",
            "HandleGameplayModeAIClicked",
            "HandleGameplayModeHudClicked",
            "HandleGameplayModeLevelFlowClicked",
            "BuildGameplayBuilderDialog",
            "BuildGameplayBuilderPrompt",
            "GetGameplayBuilderPreviewText",
            "GetGameplayBuilderDialogVisibility",
            "bGameplayBuilderDialogVisible",
            "GameplayBuilderBriefInput",
            "GameplayBuilderTargetInput",
            "GameplayBuilderAcceptanceInput",
            "GameplayBuilderEvidenceInput",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.cpp + self.header)

    def test_top_bar_and_palette_expose_build_gameplay(self) -> None:
        for token in (
            "Build Gameplay",
            "BuildGameplayQuickAction",
            "BuildGameplayBuilderDialog()",
            "Build Gameplay quick action",
            "BuildGameplayBuilderPrompt()",
            "gameplay_builder_prompt_inserted",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_prompt_uses_real_discovery_build_and_verification_tools(self) -> None:
        for token in (
            "get_project_context",
            "scan_project_assets(path=\\\"/Game\\\", depth=2)",
            "list_available_tools(domain=\\\"all\\\")",
            "get_onboarding_context(task=\\\"%s\\\")",
            "compile_blueprint_and_report",
            "pie_launch_session",
            "pie_capture_log",
            "viewport_capture_screenshot",
            "pie_stop_session",
            "changed asset paths",
            "human design review",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_modes_cover_mechanic_ai_hud_and_level_flow(self) -> None:
        for token in (
            "Gameplay Mechanic",
            "AI Behavior",
            "HUD/UI",
            "Level Flow",
            "blueprints, gameplay_framework",
            "ai_behavior_tree",
            "ui_umg",
            "procedural_world",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_kb_and_changelog_record_gameplay_builder(self) -> None:
        for token in (
            "Chat Dock Gameplay Builder",
            "Build Gameplay",
            "Mechanic, AI, HUD, and Level Flow",
            "compile_blueprint_and_report",
            "pie_capture_log",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.kb + self.changelog)


if __name__ == "__main__":
    unittest.main()
