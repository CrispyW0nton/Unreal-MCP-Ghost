"""Static checks for Workstream C.9 MCP Chat command palette."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class CommandPaletteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_command_palette_surface_is_declared(self) -> None:
        for symbol in (
            "struct FCommandPaletteItem",
            "HandleOpenCommandPaletteClicked",
            "HandleCommandPaletteTextChanged",
            "HandleCommandPaletteItemClicked",
            "BuildCommandPalette",
            "RefreshCommandPaletteItems",
            "RebuildCommandPaletteResults",
            "AddCommandPaletteItem",
            "CommandPaletteItemMatches",
            "GetCommandPaletteVisibility",
            "CommandPaletteItems",
            "CommandPaletteResults",
            "CommandPaletteInput",
            "bCommandPaletteVisible",
            "CommandPaletteFilter",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_panel_opens_palette_from_button_and_ctrl_k(self) -> None:
        self.assertIn('LOCTEXT("CommandPalette", "Command Palette")', self.cpp)
        self.assertIn(".OnClicked(this, &SMCPChatPanel::HandleOpenCommandPaletteClicked)", self.cpp)
        self.assertIn("InKeyEvent.GetKey() == EKeys::K", self.cpp)
        self.assertIn("InKeyEvent.IsControlDown()", self.cpp)
        self.assertIn("return HandleOpenCommandPaletteClicked();", self.cpp)
        self.assertIn(".Visibility(this, &SMCPChatPanel::GetCommandPaletteVisibility)", self.cpp)

    def test_palette_widget_has_search_and_results(self) -> None:
        self.assertIn("BuildCommandPalette()", self.cpp)
        self.assertIn("SAssignNew(CommandPaletteInput, SEditableTextBox)", self.cpp)
        self.assertIn(".OnTextChanged(this, &SMCPChatPanel::HandleCommandPaletteTextChanged)", self.cpp)
        self.assertIn("SAssignNew(CommandPaletteResults, SVerticalBox)", self.cpp)
        self.assertIn("RebuildCommandPaletteResults()", self.cpp)
        self.assertIn("No command matches", self.cpp)

    def test_palette_sources_are_complete(self) -> None:
        for slash_command in ("/help", "/clear", "/undo", "/repair"):
            with self.subTest(slash_command=slash_command):
                self.assertIn(slash_command, self.cpp)
        for source in (
            "ToolPaletteByCategory.GetKeys",
            "BuildToolPromptTemplate(Tool)",
            "kb://v5/CHANGELOG.md",
            "docs/knowledge-base/README.md",
            "docs/knowledge-base/unreal-cpp-li-2023.md",
            "docs/knowledge-base/elevating-game-experiences-ue5-2e.md",
            "docs/knowledge-base/game-ai-unreal-sapio-2019.md",
            "@asset:",
            "Recent asset",
            "Recent prompt",
            "NormaliseSender(Message.Sender) != TEXT(\"user\")",
        ):
            with self.subTest(source=source):
                self.assertIn(source, self.cpp)

    def test_palette_clicks_insert_or_run_commands(self) -> None:
        self.assertIn("HandleCommandPaletteItemClicked(FCommandPaletteItem Item)", self.cpp)
        self.assertIn('Item.Kind == TEXT("slash") && Item.Label == TEXT("/clear")', self.cpp)
        self.assertIn("HandleClearClicked();", self.cpp)
        self.assertIn("InsertComposerText(Item.InsertText.IsEmpty() ? Item.Label : Item.InsertText)", self.cpp)
        self.assertIn("bCommandPaletteVisible = false", self.cpp)

    def test_palette_uses_fuzzy_matching(self) -> None:
        self.assertIn("CommandPaletteItemMatches(const FString& Filter, const FCommandPaletteItem& Item) const", self.cpp)
        self.assertIn("Haystack.Contains(Needle)", self.cpp)
        self.assertIn("NeedleIndex", self.cpp)
        self.assertIn("HaystackIndex", self.cpp)

    def test_changelog_records_c9(self) -> None:
        self.assertIn("### C.9 - Command palette", self.changelog)
        self.assertIn("Ctrl+K", self.changelog)
        self.assertIn("fuzzy", self.changelog)


if __name__ == "__main__":
    unittest.main()
