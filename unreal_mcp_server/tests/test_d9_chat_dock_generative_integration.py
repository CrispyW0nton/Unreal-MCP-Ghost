"""Static checks for Workstream D.9 MCP Chat generative integration."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"
GENERATIVE_KB = REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md"


class D9ChatDockGenerativeIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")
        cls.kb = GENERATIVE_KB.read_text(encoding="utf-8")

    def test_generate_asset_quick_action_is_declared(self) -> None:
        for symbol in (
            "HandleOpenGenerateAssetClicked",
            "HandleInsertGenerateAssetToolCallClicked",
            "BuildGenerateAssetDialog",
            "BuildGenerateAssetToolCallPrompt",
            "GetGenerateAssetPreviewText",
            "GetGenerateAssetDialogVisibility",
            "GenerateAssetPromptInput",
            "GenerateAssetNameInput",
            "bGenerateAssetDialogVisible",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_generate_asset_dialog_inserts_tripo_tool_call(self) -> None:
        for token in (
            "Generate Asset",
            "GenerateAssetQuickAction",
            "BuildGenerateAssetDialog()",
            "gen_tripo_text_to_model",
            "gen_tripo_wait_for_task",
            "gen_tripo_import_to_project",
            "confirm_spend",
            "bGenerativeSpendConfirmed ? TEXT(\"true\") : TEXT(\"false\")",
            "InsertComposerText(BuildGenerateAssetToolCallPrompt())",
            "generate_asset_quick_action_inserted",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_tripo_progress_cards_are_rendered_and_refreshed(self) -> None:
        for token in (
            '#include "Widgets/Notifications/SProgressBar.h"',
            "BuildTripoProgressPanel",
            "Tripo progress: {0}%",
            "SNew(SProgressBar)",
            "ProgressFraction",
            "bHasProgress",
            "ToolName.Contains(TEXT(\"tripo\"), ESearchCase::IgnoreCase)",
            "TryReadProgress(Object)",
            "TryReadProgress(*OutputsObject)",
            "gen_tripo_wait_for_task",
            "RebuildMessageList()",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp + self.header)

    def test_kb_and_changelog_record_d9(self) -> None:
        for token in (
            "D9 Chat Dock Integration",
            "Generate Asset action",
            "inline progress bar",
            "gen_tripo_wait_for_task",
            "Magic Brush Texture Edit Sessions",
            "gen_prepare_texture_paint_session",
            "retexture_generate",
            "apply_retexture",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.kb)

        self.assertIn("D.9 - Chat dock generative integration", self.changelog)
        self.assertIn("Generate Asset quick action", self.changelog)
        self.assertIn("inline Tripo progress rendering", self.changelog)
        self.assertIn("gen_prepare_texture_paint_session", self.changelog)


if __name__ == "__main__":
    unittest.main()
