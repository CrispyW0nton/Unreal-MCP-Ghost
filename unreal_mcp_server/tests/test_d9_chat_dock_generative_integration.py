"""Static checks for Workstream D.9 MCP Chat generative integration."""

from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
EDITOR_MODULE = REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor"
PANEL_CPP = EDITOR_MODULE / "Private" / "MCPChatPanel.cpp"
PANEL_H = EDITOR_MODULE / "Public" / "MCPChatPanel.h"
MODULE_H = EDITOR_MODULE / "Public" / "UnrealMCPEditorModule.h"
SESSION_H = EDITOR_MODULE / "Public" / "TripoWorkspaceSession.h"
EDITOR_MODULE_CPP = EDITOR_MODULE / "Private" / "UnrealMCPEditorModule.cpp"
CHANGELOG = REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md"
GENERATIVE_KB = REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md"


class D9ChatDockGenerativeIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cpp = PANEL_CPP.read_text(encoding="utf-8")
        cls.header = PANEL_H.read_text(encoding="utf-8")
        cls.module_header = MODULE_H.read_text(encoding="utf-8")
        cls.session_header = SESSION_H.read_text(encoding="utf-8")
        cls.module_cpp = EDITOR_MODULE_CPP.read_text(encoding="utf-8")
        cls.changelog = CHANGELOG.read_text(encoding="utf-8")
        cls.kb = GENERATIVE_KB.read_text(encoding="utf-8")

    def test_generate_asset_quick_action_is_declared(self) -> None:
        for symbol in (
            "HandleOpenGenerateAssetClicked",
            "HandleOpenTripoWorkspaceClicked",
            "HandleOpenTripoWorkspaceAssetClicked",
            "HandleInsertGenerateAssetToolCallClicked",
            "BuildGenerateAssetDialog",
            "BuildGenerateAssetToolCallPrompt",
            "GetGenerateAssetPreviewText",
            "GetGenerateAssetDialogVisibility",
            "GetGenerateAssetMode",
            "GenerateAssetModeInput",
            "GenerateAssetPromptInput",
            "GenerateAssetNameInput",
            "GenerateAssetReferenceImagesInput",
            "GenerateAssetExistingTaskIdInput",
            "GenerateAssetTexturePromptInput",
            "GenerateAssetPaintViewLabelInput",
            "GenerateAssetPaintBrushStrength",
            "GenerateAssetPaintBlend",
            "GenerateAssetPaintBrushRadius",
            "bGenerateAssetUploadPaintSnapshot",
            "bGenerateAssetDialogVisible",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, self.header)

    def test_generate_asset_dialog_inserts_tripo_tool_call(self) -> None:
        for token in (
            "Generate Asset Workspace",
            "OpenTripoWorkspaceAction",
            "IUnrealMCPEditorModule::Get().OpenTripoWorkspaceWindow()",
            "ToolTripoPreview",
            "HandleOpenTripoWorkspaceAssetClicked",
            "PreviewAssetPath",
            "tripo_workspace_asset_preview_requested",
            "GenerateAssetQuickAction",
            "BuildGenerateAssetDialog()",
            "gen_tripo_text_to_model",
            "gen_tripo_image_to_model",
            "gen_tripo_multiview_to_model",
            "gen_prepare_texture_paint_session",
            "gen_capture_texture_paint_snapshot",
            "gen_tripo_texture_model",
            "gen_record_texture_paint_pass",
            "gen_compile_texture_paint_evidence",
            "unreal_mcp_texture_paint_evidence.v1",
            "Texture/Paint Controls",
            "SSpinBox<float>",
            "upload_to_tripo",
            "brush_strength",
            "blend_mode",
            "paint_notes",
            "source_snapshot_label",
            "result_snapshot_label",
            "prepare_result.outputs.tripo_texture_prompt",
            "gen_tripo_wait_for_task",
            "gen_tripo_import_to_project",
            "smart_low_poly: true",
            "Smart Mesh",
            "Generative Credits",
            "confirm_spend",
            "bGenerativeSpendConfirmed ? TEXT(\"true\") : TEXT(\"false\")",
            "InsertComposerText(BuildGenerateAssetToolCallPrompt())",
            "generate_asset_quick_action_inserted",
            "GenerativeUthanaApiKeyInput",
            "UTHANA_API_KEY for animation generation",
            "SetStringField(TEXT(\"UTHANA_API_KEY\"), GenerativeUthanaApiKey",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.cpp)

    def test_tripo_workspace_opens_as_standalone_editor_window_with_viewport(self) -> None:
        for token in (
            "class IUnrealMCPEditorModule",
            "OpenTripoWorkspaceWindow",
            "LoadModuleChecked<IUnrealMCPEditorModule>",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.module_header)

        for token in (
            "UTripoWorkspaceSession",
            "ETripoWorkspaceMode",
            "UPROPERTY(EditAnywhere, Category = \"Workspace\")",
            "UPROPERTY(VisibleAnywhere, Category = \"Generative Credits\")",
            "bSmartMeshEnabled",
            "ApiKeySource",
            "ApiWalletBalance",
            "ApiWalletFrozen",
            "FaceLimit",
            "TopologyPolicy",
            "Smart Mesh locked on for Unreal game-ready topology",
            "PaintViewLabel",
            "BrushStrength",
            "BlendAmount",
            "BrushRadius",
            "bUploadPaintSnapshot",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.session_header)

        for token in (
            "UnrealMCPTripoWorkspaceTabId",
            "RegisterNomadTabSpawner",
            "SpawnTripoWorkspaceTab",
            "OpenTripoWorkspaceWindow",
            "TWeakPtr<SWindow> TripoWorkspaceWindow",
            "SNew(SWindow)",
            "UnrealMCPTripoWorkspaceWindowTitle",
            ".ClientSize(FVector2D(1280.0f, 760.0f))",
            "BringToFront",
            "FSlateApplication::Get().AddWindow(WorkspaceWindow)",
            "RequestDestroyWindow",
            "UTripoWorkspaceSession",
            "TStrongObjectPtr<UTripoWorkspaceSession> WorkspaceSession",
            "FPropertyEditorModule",
            "FDetailsViewArgs",
            "CreateDetailView",
            "WorkspaceDetailsView",
            "InitializeWorkspaceSession",
            "BuildWorkspaceDetailsView",
            "RefreshWorkspaceDetails",
            "ModeNameToSessionMode",
            "BuildWorkspaceToolbar",
            "BuildWorkspaceStatusStrip",
            "BuildWorkspaceAuthControls",
            "HandleSendModePromptToChatClicked",
            "HandleWorkspaceChatSendComplete",
            "BuildWorkspaceChatContext",
            "MakeWorkspaceJsonRequest",
            "BuildWorkspaceServerUrl",
            "GetWorkspaceChatSessionName",
            "ActiveWorkspaceRequests",
            "WorkspaceServerBaseUrl",
            "TripoWorkspaceToolbarSendToChat",
            "/chat/send?session=",
            "tripo-workspace",
            "source",
            "WorkspaceApiKeyInput",
            ".IsPassword(true)",
            "HandleSaveWorkspaceApiKeyClicked",
            "HandleClearWorkspaceApiKeyClicked",
            "GetWorkspaceTripoAuthStatusText",
            "GetWorkspaceTripoSecretsPathText",
            "GetGenerativeSecretsFilePath",
            "LoadStoredWorkspaceApiKey",
            "UpdateWorkspaceApiKeySource",
            "TRIPO_API_KEY",
            "Saved/MCPChat/secrets.json",
            "HandleRefreshWorkspaceSettingsClicked",
            "TripoWorkspaceToolbarRefreshCredits",
            "TripoWorkspaceSettingsRefreshed",
            "GetWorkspaceApiWalletText",
            "GetSmartMeshPolicyText",
            "RequestWorkspaceApiWalletRefresh",
            "HandleWorkspaceApiWalletRefreshComplete",
            "TripoWorkspaceWalletErrorWithMessage",
            "suggestion",
            "SyncWorkspaceApiWalletToSession",
            "ResolveWorkspaceApiKey",
            "api.tripo3d.ai/v2/openapi/user/balance",
            "Tripo API Wallet",
            "WorkspaceApiWalletBalance",
            "WorkspaceApiWalletFrozen",
            "WorkspaceApiWalletStatus",
            "WorkspaceTopologyPolicy",
            "Smart Mesh: locked on | face_limit=12000 | game-ready topology",
            "topology_policy",
            "STripoWorkspacePanel",
            "STripoAssetViewport",
            "Tripo Workspace",
            "SEditorViewport",
            "FAdvancedPreviewScene",
            "UStaticMeshComponent",
            "LoadStaticMeshFromPath",
            "Load Preview",
            "FramePreviewMesh",
            "LoadRequestedPreviewAssetFromConfig",
            "LoadRequestedPreviewAssetFromHandoff",
            "GetWorkspacePreviewHandoffFilePath",
            "ApplyRequestedPreviewAsset",
            "generative_workspace_preview.json",
            "PollRequestedPreviewAsset",
            "TripoWorkspaceConfigSection",
            "PreviewAssetPath",
            "Generated Asset Viewport",
            "Text to 3D",
            "Multi Image to 3D",
            "Texture Paint",
            "ActiveWorkspaceMode",
            "HandleWorkspaceModeClicked",
            "WorkspacePromptInput",
            "WorkspaceReferenceViewsInput",
            "WorkspaceExistingTaskInput",
            "WorkspacePaintViewLabelInput",
            "WorkspaceBrushStrengthInput",
            "WorkspaceBlendAmountInput",
            "WorkspaceBrushRadiusInput",
            "GetWorkspaceUploadPaintSnapshotCheckState",
            "HandleWorkspaceUploadPaintSnapshotChanged",
            "Texture Paint Controls",
            "brush_strength=%.2f",
            "soft blend %.2f",
            "paint_notes",
            "source_snapshot_label",
            "brush_radius=%.2f",
            "upload_to_tripo=%s",
            "Copy MCP Prompt",
            "BuildModePromptText",
            "GetGenerativeCreditText",
            "generative_settings.json",
            "session_credit_budget",
            "Smart Mesh: on",
            "OpenUnrealMCPTripoWorkspace",
            "CreateRaw(this, &FUnrealMCPEditorModule::OpenTripoWorkspaceWindow)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.module_cpp)

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
            "Generate Asset Workspace",
            "multiview_to_model",
            "texture_paint",
            "gen_capture_texture_paint_snapshot",
            "gen_record_texture_paint_pass",
            "gen_compile_texture_paint_evidence",
            "smart_low_poly=true",
            "inline progress bar",
            "gen_tripo_wait_for_task",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.kb)

        self.assertIn("D.9 - Chat dock generative integration", self.changelog)
        self.assertIn("Generate Asset quick action", self.changelog)
        self.assertIn("inline Tripo progress rendering", self.changelog)
        self.assertIn("D.9 follow-up - Generative workspace modes", self.changelog)
        self.assertIn("smart_low_poly=true", self.changelog)


if __name__ == "__main__":
    unittest.main()
