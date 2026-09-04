"""Static checks for Workstream C.4 chat context chips."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"


class ContextChipsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")

    def test_context_chip_surface_is_declared(self) -> None:
        for symbol in (
            "BuildContextChips",
            "HandleContextChipClicked",
            "UpdateLastCompileStateFromMessage",
            "GetOpenLevelChipText",
            "GetSelectedActorChipText",
            "GetDirtyAssetsChipText",
            "GetLastCompileChipText",
            "GetServerChipText",
            "GetOpenLevelReference",
            "GetSelectedActorReference",
            "GetDirtyAssetsReference",
            "GetLastCompileReference",
            "GetServerReference",
            "GetOpenLevelName",
            "GetSelectedActorName",
            "CountDirtyPackages",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_chips_render_above_composer_with_required_labels(self) -> None:
        self.assertIn("BuildContextChips()", self.cpp)
        self.assertLess(self.cpp.index("BuildContextChips()"), self.cpp.index("SAssignNew(MessageInput"))

        for label in ("Open Level:", "Selected Actor:", "Dirty Assets (", "Last Compile:", "Server: SSE 8000"):
            with self.subTest(label=label):
                self.assertIn(label, self.cpp)

        self.assertIn("\\u2705", self.cpp)
        self.assertIn("\\u274C", self.cpp)

    def test_each_chip_uses_live_text_and_click_handler(self) -> None:
        expected_pairs = {
            "GetOpenLevelChipText": 'FString(TEXT("level"))',
            "GetSelectedActorChipText": 'FString(TEXT("actor"))',
            "GetDirtyAssetsChipText": 'FString(TEXT("dirty"))',
            "GetLastCompileChipText": 'FString(TEXT("compile"))',
            "GetServerChipText": 'FString(TEXT("server"))',
        }
        for text_getter, click_reference in expected_pairs.items():
            with self.subTest(text_getter=text_getter):
                self.assertIn(f".Text(this, &SMCPChatPanel::{text_getter})", self.cpp)
                self.assertIn(click_reference, self.cpp)

        self.assertIn("InsertComposerText(Reference)", self.cpp)
        self.assertIn("Inserted {0}", self.cpp)

    def test_chips_read_current_editor_context(self) -> None:
        for context_probe in (
            "GEditor->GetEditorWorldContext().World()",
            "FPackageName::GetShortName",
            "GEditor->GetSelectedActors()",
            "FSelectionIterator Iterator(*SelectedActors)",
            "TObjectIterator<UPackage>",
            "Package->IsDirty()",
        ):
            with self.subTest(context_probe=context_probe):
                self.assertIn(context_probe, self.cpp)

    def test_compile_chip_tracks_structured_and_text_compile_results(self) -> None:
        self.assertIn("LastCompileStatus", self.header)
        self.assertIn("ExtractToolCallsFromMessage(ChatMessage, ToolCalls)", self.cpp)
        self.assertIn('ToolCall.ToolName.Contains(TEXT("compile"), ESearchCase::IgnoreCase)', self.cpp)
        self.assertIn('ToolCall.bError ? TEXT("fail") : TEXT("ok")', self.cpp)
        for token in ("failed", "success", "compiled"):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_inserted_context_references_match_chip_meaning(self) -> None:
        for reference in ("@level:", "@actor:", "@dirty-assets:", "@last-compile:", "@server:sse:8000"):
            with self.subTest(reference=reference):
                self.assertIn(reference, self.cpp)


if __name__ == "__main__":
    unittest.main()
