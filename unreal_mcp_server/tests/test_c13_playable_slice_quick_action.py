"""Static checks for the MCP Chat playable-slice quick action."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
PLAYABLE_KB = REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class PlayableSliceQuickActionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.kb = PLAYABLE_KB.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_playable_slice_surface_is_declared(self) -> None:
        for symbol in (
            "HandleOpenPlayableSliceClicked",
            "HandleInsertPlayableSlicePromptClicked",
            "BuildPlayableSliceDialog",
            "BuildPlayableSlicePrompt",
            "GetPlayableSlicePreviewText",
            "GetPlayableSliceDialogVisibility",
            "bPlayableSliceDialogVisible",
            "PlayableSliceBriefInput",
            "PlayableSliceAssetRolesInput",
            "PlayableSliceGameplayLoopInput",
            "PlayableSliceAcceptanceInput",
            "PlayableSliceEvidenceInput",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.cpp + self.header)

    def test_top_bar_and_palette_expose_playable_slice(self) -> None:
        for token in (
            "Playable Slice",
            "PlayableSliceQuickAction",
            "BuildPlayableSliceDialog()",
            "Playable Slice quick action",
            "BuildPlayableSlicePrompt()",
            "playable_slice_workflow_prompt_inserted",
            "Add a Tripo API key before generating a playable slice",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_prompt_links_generation_import_gameplay_and_verification(self) -> None:
        for token in (
            "in-editor AI IDE",
            "one-sentence brief",
            "generated_asset_roles",
            "skill_generate_playable_slice",
            "mode=\\\"plan\\\"",
            "mode=\\\"submit_assets\\\"",
            "mode=\\\"orchestrate\\\"",
            "gen_tripo_text_to_model",
            "smart_low_poly=true",
            "gen_tripo_wait_for_task",
            "gen_tripo_import_to_project",
            "gen_prepare_texture_paint_session",
            "gen_tripo_magic_brush_generate",
            "compile_blueprint_and_report",
            "pie_launch_session",
            "pie_capture_log",
            "viewport_capture_screenshot",
            "pie_stop_session",
            "credit usage",
            "human design review",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_kb_and_changelog_record_playable_slice_action(self) -> None:
        for token in (
            "Chat Dock Playable Slice Builder",
            "Playable Slice",
            "Smart Mesh Tripo assets",
            "gen_tripo_text_to_model",
            "gen_tripo_import_to_project",
            "pie_capture_log",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.kb + self.changelog)


if __name__ == "__main__":
    unittest.main()
