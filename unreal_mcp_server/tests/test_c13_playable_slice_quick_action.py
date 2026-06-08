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
            "HandleInsertPlayableSlicePreflightPromptClicked",
            "HandleInsertPlayableSlicePromptClicked",
            "BuildPlayableSliceDialog",
            "BuildPlayableSlicePreflightPrompt",
            "BuildPlayableSlicePrompt",
            "GetPlayableSlicePreviewText",
            "GetPlayableSlicePreflightStatusText",
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
            "Preflight",
            "BuildPlayableSlicePreflightPrompt()",
            "playable_slice_preflight_prompt_inserted",
            "BuildPlayableSlicePrompt()",
            "playable_slice_workflow_prompt_inserted",
            "Inserted preflight-first workflow; add a Tripo API key before paid execution",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_prompt_links_generation_import_gameplay_and_verification(self) -> None:
        for token in (
            "in-editor AI IDE",
            "one-sentence brief",
            "Run the no-spend Playable Slice preflight",
            "Preflight gates:",
            "tripo_api_key, credit_budget, unreal_build_tooling, packaged_plugin, and unreal_bridge",
            "generated_asset_roles",
            "skill_generate_playable_slice",
            "mode=\\\"preflight\\\"",
            "missing live-readiness gates",
            "does not reserve credits",
            "mode=\\\"plan\\\"",
            "mode=\\\"submit_assets\\\"",
            "mode=\\\"orchestrate\\\"",
            "evidence_readiness",
            "live_playable_slice_proven=false",
            "execution_evidence_json",
            "task_submissions_json",
            "imported_assets_json",
            "evidence_readiness.live_playable_slice_proven",
            "asset_roles=\\\"%s\\\"",
            "gameplay_loop=\\\"%s\\\"",
            "acceptance_criteria=\\\"%s\\\"",
            "required_evidence=\\\"%s\\\"",
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
            "skill_package_vertical_slice_report",
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
