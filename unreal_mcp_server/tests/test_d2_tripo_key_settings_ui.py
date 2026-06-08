"""Static checks for the in-editor Tripo settings and workspace UI."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
GENERATIVE_KB = REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"


class D2TripoKeySettingsUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.kb = GENERATIVE_KB.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")

    def test_tripo_api_key_field_is_secret_and_clearable(self) -> None:
        for token in (
            "GenerativeApiKeyInput",
            "TRIPO_API_KEY",
            ".IsPassword(true)",
            "HandleClearGenerativeApiKeyClicked",
            "GetGenerativeSecretsFilePath()",
            "IFileManager::Get().Delete",
            "Saved/MCPChat/secrets.json",
            "IsGenerativeApiKeyConfigured",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp + self.header)

    def test_generate_workspace_has_all_tripo_modes(self) -> None:
        for token in (
            "HandleGenerateModeTextToModelClicked",
            "HandleGenerateModeImageToModelClicked",
            "HandleGenerateModeMultiviewToModelClicked",
            "HandleGenerateModeTextureModelClicked",
            "GetGenerateTextToModelVisibility",
            "GetGenerateImageToModelVisibility",
            "GetGenerateMultiviewToModelVisibility",
            "GetGenerateTextureModelVisibility",
            "Text to 3D",
            "Image to 3D",
            "Multi-Image to 3D",
            "Texture/Paint",
            "gen_tripo_text_to_model",
            "gen_tripo_image_to_model",
            "gen_tripo_multiview_to_model",
            "gen_tripo_texture_model",
            "smart_low_poly: true",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp + self.header)

    def test_generate_workspace_collapses_irrelevant_mode_fields(self) -> None:
        for token in (
            "GenerateAssetMode == TEXT(\"text_to_model\") ? EVisibility::Visible : EVisibility::Collapsed",
            "GenerateAssetMode == TEXT(\"image_to_model\") ? EVisibility::Visible : EVisibility::Collapsed",
            "GenerateAssetMode == TEXT(\"multiview_to_model\") ? EVisibility::Visible : EVisibility::Collapsed",
            "GenerateAssetMode == TEXT(\"texture_model\") ? EVisibility::Visible : EVisibility::Collapsed",
            ".Visibility(this, &SMCPChatPanel::GetGenerateTextToModelVisibility)",
            ".Visibility(this, &SMCPChatPanel::GetGenerateImageToModelVisibility)",
            ".Visibility(this, &SMCPChatPanel::GetGenerateMultiviewToModelVisibility)",
            ".Visibility(this, &SMCPChatPanel::GetGenerateTextureModelVisibility)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp + self.header)

    def test_texture_paint_controls_are_documented(self) -> None:
        for token in (
            "GenerateTextureReferenceImageInput",
            "GenerateTexturePaintNotes",
            "GenerateTextureViewAngle",
            "GenerateTextureBrushStrength",
            "GenerateTextureBlendMode",
            "GenerateTextureSaveName",
            "GenerateTextureRenderImageBucket",
            "GenerateTextureRenderImageKey",
            "GenerateTextureRenderImageUrl",
            "GenerateTextureCameraMatrix",
            "GenerateTextureImageMapJson",
            "texture reference image",
            "render image bucket",
            "render image key",
            "render image URL",
            "camera matrix JSON",
            "Magic Brush image_map JSON",
            "paint/blend notes",
            "paint it onto the visible model",
            "rotate the model",
            "save the satisfied result",
            "gen_tripo_magic_brush_generate",
            "gen_tripo_magic_brush_apply",
            "Tripo workspace modes",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp + self.header + self.kb + self.changelog)

    def test_generative_credits_display_is_visible_and_preserves_usage(self) -> None:
        for token in (
            "Generative Credits",
            "GetGenerativeCreditsDisplayText",
            "GenerativeSessionCreditsUsed",
            "credit_usage_by_session",
            "Remaining",
            "Next spend",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp + self.header + self.kb + self.changelog)


if __name__ == "__main__":
    unittest.main()
