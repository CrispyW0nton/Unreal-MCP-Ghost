"""Static checks for the Workstream C.2 core chat panel UX."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
BUILD_CS = EDITOR_MODULE / "UnrealMCPEditor.Build.cs"


class CoreChatPanelUxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.build_cs = BUILD_CS.read_text(encoding="utf-8")

    def test_two_pane_composer_layout_and_key_handling(self) -> None:
        self.assertIn("SNew(SSplitter)", self.cpp)
        self.assertIn(".Orientation(Orient_Vertical)", self.cpp)
        self.assertIn("SAssignNew(MessageInput, SMultiLineEditableTextBox)", self.cpp)
        self.assertIn(".OnKeyDownHandler(this, &SMCPChatPanel::HandleComposerKeyDown)", self.cpp)
        self.assertIn("EKeys::Enter", self.cpp)
        self.assertIn("!InKeyEvent.IsShiftDown()", self.cpp)

    def test_role_tagged_message_bubbles_have_actions(self) -> None:
        for role in ("User", "Agent", "Tool"):
            with self.subTest(role=role):
                self.assertIn(role, self.cpp)

        for action in ("Copy", "Re-run", "Open Log", "Reveal Asset"):
            with self.subTest(action=action):
                self.assertIn(action, self.cpp)

        self.assertIn("BuildMessageWidget", self.header)
        self.assertIn("GetMessageColor", self.header)
        self.assertIn("NormaliseSender", self.header)

    def test_drag_drop_target_is_wired_to_composer(self) -> None:
        self.assertIn("virtual FReply OnDragOver", self.header)
        self.assertIn("virtual FReply OnDrop", self.header)
        self.assertIn("BuildDropReference", self.header)
        self.assertIn("@asset:<dropped-asset>", self.cpp)
        self.assertIn("@actor:<dropped-actor>", self.cpp)
        self.assertIn("@file:<dropped-file>", self.cpp)
        self.assertIn("InsertComposerText(BuildDropReference(Operation))", self.cpp)

    def test_streaming_delta_path_updates_existing_text_block(self) -> None:
        self.assertIn("AppendStreamingDelta", self.header)
        self.assertIn("ApplySseLine", self.header)
        self.assertIn("StreamingMessageTextBlocks", self.header)
        self.assertIn("Line.StartsWith(TEXT(\"data:\"))", self.cpp)
        self.assertIn("EventObject->TryGetStringField(TEXT(\"delta\"), Delta)", self.cpp)
        self.assertIn("(*ExistingTextBlock)->SetText", self.cpp)

    def test_markdown_code_blocks_are_rendered_separately(self) -> None:
        self.assertIn("BuildMarkdownMessageBody", self.header)
        self.assertIn("AddMarkdownBlocks", self.header)
        self.assertIn("Line.StartsWith(TEXT(\"```\"))", self.cpp)
        self.assertIn("FAppStyle::GetFontStyle(\"Monospaced\")", self.cpp)
        self.assertIn("CodeBlockColor", self.cpp)

    def test_module_dependencies_cover_core_panel_features(self) -> None:
        for dependency in ("ApplicationCore", "InputCore", "AssetRegistry", "ContentBrowser", "Slate", "SlateCore"):
            with self.subTest(dependency=dependency):
                self.assertIn(f'"{dependency}"', self.build_cs)


if __name__ == "__main__":
    unittest.main()
