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
            "HandleInsertGenerateAssetPreflightPromptClicked",
            "HandleInsertGenerateAssetToolCallClicked",
            "HandleInsertTripoWalletBalancePromptClicked",
            "BuildGenerateAssetDialog",
            "BuildGenerateAssetPreflightPrompt",
            "BuildGenerateAssetToolCallPrompt",
            "BuildTripoWalletBalancePrompt",
            "GetGenerateAssetPreviewText",
            "GetGenerateAssetPreflightStatusText",
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
            "Check Wallet",
            "GenerateAssetQuickAction",
            "BuildGenerateAssetDialog()",
            "gen_tripo_text_to_model",
            "gen_prepare_texture_paint_session",
            "gen_tripo_wait_for_task",
            "gen_tripo_import_to_project",
            "confirm_spend",
            "smart_low_poly: true",
            "InsertComposerText(BuildGenerateAssetPreflightPrompt())",
            "bGenerativeSpendConfirmed ? TEXT(\"true\") : TEXT(\"false\")",
            "InsertComposerText(BuildGenerateAssetToolCallPrompt())",
            "generate_asset_preflight_prompt_inserted",
            "generate_asset_quick_action_inserted",
            "tripo_wallet_balance_prompt_inserted",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_generate_asset_preflight_is_no_spend_readiness_gate(self) -> None:
        for token in (
            "Run the no-spend Tripo Generate Asset preflight",
            "gen_generate_asset_preflight",
            "unreal_mcp_generate_asset_live_preflight.v1",
            "mode_supported",
            "ready_for_live_spend",
            "smart_mesh_policy",
            "latest packaged plugin path",
            "bridge host/port",
            "do not reserve credits",
            "do not mutate Unreal",
            "Smart Mesh/good topology",
            "gen_tripo_get_wallet_balance",
            "wallet balance/frozen credits",
            "Run the no-spend live Tripo wallet balance check",
            "must not create a generation task",
            "Preflight gates: auth",
            "paid work requires confirmed spend",
            "Use Preflight or add a Tripo API key before paid generation",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_texture_paint_mode_inserts_magic_brush_session_plan(self) -> None:
        for token in (
            "First use MCP tool `gen_prepare_texture_paint_session`",
            "no-spend Tripo Studio Magic Brush plan",
            "Plan parameters:",
            "render_image_bucket",
            "render_image_key",
            "render_image_url",
            "- render_image: %s",
            "- camera_matrix: %s",
            "- brush_size: %s",
            "- brush_hardness: %s",
            "- creativity_strength: %s",
            "- paint_mode:",
            "- paint_color:",
            "- tripo_project_id:",
            "- image_map: %s",
            "Paint stroke controls:",
            "- part_name:",
            "- paint_image: %s",
            "- record_session: true",
            "Then, only after spend approval",
            "gen_tripo_magic_brush_generate",
            "gen_tripo_magic_brush_get_retexture",
            "gen_tripo_magic_brush_list_images",
            "gen_record_texture_paint_stroke",
            "gen_compile_texture_paint_image_map",
            "gen_tripo_magic_brush_apply",
            "compiled image_map",
            "Paid texture parameters:",
            "GenerateTextureBrushSizeInput",
            "GenerateTextureBrushHardnessInput",
            "GenerateTextureCreativityStrengthInput",
            "GenerateTexturePaintModeInput",
            "GenerateTexturePaintColorInput",
            "GenerateTexturePaintPartNameInput",
            "GenerateTexturePaintImageBucketInput",
            "GenerateTexturePaintImageKeyInput",
            "GenerateTexturePaintImageUrlInput",
            "GenerateTexturePaintImageFileTokenInput",
            "GenerateTextureTripoProjectIdInput",
            "GenerateTextureRenderImageBucketInput",
            "GenerateTextureRenderImageKeyInput",
            "GenerateTextureRenderImageUrlInput",
            "GenerateTextureCameraMatrixInput",
            "GenerateTextureImageMapJsonInput",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp + self.header)

    def test_texture_paint_mode_keeps_common_and_advanced_controls_separate(self) -> None:
        for token in (
            "Texture Target",
            "Texture Direction",
            "Paint Controls",
            "Paint Stroke",
            "Studio Snapshot",
            "SExpandableArea",
            ".InitiallyCollapsed(true)",
            "GenerateTextureTaskIdInput",
            "GenerateTexturePromptInput",
            "GenerateTextureBrushSizeInput",
            "GenerateTexturePaintPartNameInput",
            "GenerateTextureTripoProjectIdInput",
            "GenerateTextureCameraMatrixInput",
            "GenerateTextureImageMapJsonInput",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp + self.header)

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
            "Generate Asset panel also includes a **Preflight** action",
            "gen_generate_asset_preflight",
            "unreal_mcp_generate_asset_live_preflight.v1",
            "smart_mesh_policy",
            "ready_for_live_spend",
            "**Paint Stroke**",
            "gen_record_texture_paint_stroke",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.kb)

        self.assertIn("D.9 - Chat dock generative integration", self.changelog)
        self.assertIn("Generate Asset quick action", self.changelog)
        self.assertIn("inline Tripo progress rendering", self.changelog)
        self.assertIn("gen_prepare_texture_paint_session", self.changelog)
        self.assertIn("Generate Asset **Preflight** action", self.changelog)
        self.assertIn("gen_generate_asset_preflight", self.changelog)


if __name__ == "__main__":
    unittest.main()
