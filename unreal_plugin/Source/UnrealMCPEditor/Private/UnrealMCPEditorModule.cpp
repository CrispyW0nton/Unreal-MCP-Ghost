#include "UnrealMCPEditorModule.h"
#include "MCPChatPanel.h"
#include "TripoWorkspaceSession.h"

#include "AdvancedPreviewScene.h"
#include "Components/StaticMeshComponent.h"
#include "EditorViewportClient.h"
#include "Engine/StaticMesh.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Commands/UIAction.h"
#include "Framework/Docking/TabManager.h"
#include "GenericPlatform/GenericPlatformHttp.h"
#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformApplicationMisc.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "IDetailsView.h"
#include "PropertyEditorModule.h"
#include "SEditorViewport.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Styling/AppStyle.h"
#include "Textures/SlateIcon.h"
#include "ToolMenus.h"
#include "UObject/GCObject.h"
#include "UObject/SoftObjectPath.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SSpinBox.h"
#include "Widgets/Docking/SDockTab.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SSplitter.h"
#include "Widgets/SCompoundWidget.h"
#include "Widgets/SOverlay.h"
#include "Widgets/SViewport.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SWindow.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "FUnrealMCPEditorModule"

namespace
{
	const FName UnrealMCPChatTabId(TEXT("UnrealMCPChat"));
	const FName UnrealMCPTripoWorkspaceTabId(TEXT("UnrealMCPTripoWorkspace"));
	const TCHAR* TripoWorkspaceConfigSection = TEXT("UnrealMCP.TripoWorkspace");
	const TCHAR* TripoWorkspacePreviewHandoffFile = TEXT("generative_workspace_preview.json");
}

class STripoAssetViewport : public SEditorViewport, public FGCObject
{
public:
	SLATE_BEGIN_ARGS(STripoAssetViewport) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs)
	{
		PreviewScene = MakeShared<FAdvancedPreviewScene>(FPreviewScene::ConstructionValues());
		PreviewScene->SetFloorVisibility(true, true);
		PreviewScene->SetEnvironmentVisibility(false, true);

		PreviewMeshComponent = NewObject<UStaticMeshComponent>(GetTransientPackage(), TEXT("TripoWorkspacePreviewMesh"));
		PreviewMeshComponent->SetMobility(EComponentMobility::Movable);
		PreviewMeshComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);
		PreviewMeshComponent->bSelectable = false;
		PreviewScene->AddComponent(PreviewMeshComponent, FTransform::Identity);

		SEditorViewport::Construct(SEditorViewport::FArguments());
	}

	virtual ~STripoAssetViewport() override
	{
		if (PreviewScene.IsValid() && PreviewMeshComponent)
		{
			PreviewScene->RemoveComponent(PreviewMeshComponent);
		}
	}

	bool LoadStaticMeshFromPath(const FString& AssetPath, FText& OutStatus)
	{
		const FString TrimmedPath = AssetPath.TrimStartAndEnd();
		if (TrimmedPath.IsEmpty())
		{
			OutStatus = LOCTEXT("TripoWorkspaceMissingAssetPath", "Enter a Static Mesh asset path.");
			return false;
		}

		FString ObjectPathText = TrimmedPath;
		FSoftObjectPath ObjectPath(ObjectPathText);
		UObject* LoadedObject = ObjectPath.TryLoad();
		if (!LoadedObject && TrimmedPath.StartsWith(TEXT("/Game/")) && !TrimmedPath.Contains(TEXT(".")))
		{
			FString PackagePath;
			FString AssetName;
			if (TrimmedPath.Split(TEXT("/"), &PackagePath, &AssetName, ESearchCase::IgnoreCase, ESearchDir::FromEnd) && !AssetName.IsEmpty())
			{
				ObjectPathText = FString::Printf(TEXT("%s.%s"), *TrimmedPath, *AssetName);
				LoadedObject = FSoftObjectPath(ObjectPathText).TryLoad();
			}
		}
		UStaticMesh* StaticMesh = Cast<UStaticMesh>(LoadedObject);
		if (!StaticMesh)
		{
			OutStatus = FText::Format(LOCTEXT("TripoWorkspaceAssetLoadFailed", "Could not load Static Mesh: {0}"), FText::FromString(TrimmedPath));
			return false;
		}

		PreviewMesh = StaticMesh;
		PreviewMeshComponent->SetStaticMesh(StaticMesh);
		PreviewMeshComponent->SetWorldTransform(FTransform::Identity);
		PreviewMeshComponent->MarkRenderStateDirty();
		FramePreviewMesh();
		OutStatus = FText::Format(LOCTEXT("TripoWorkspaceAssetLoaded", "Loaded preview asset: {0}"), FText::FromString(TrimmedPath));
		return true;
	}

	void FramePreviewMesh()
	{
		if (ViewportClient.IsValid() && PreviewMeshComponent && PreviewMeshComponent->GetStaticMesh())
		{
			PreviewMeshComponent->UpdateBounds();
			const FBoxSphereBounds Bounds = PreviewMeshComponent->Bounds;
			const FBox BoundingBox = Bounds.GetBox();
			ViewportClient->FocusViewportOnBox(BoundingBox, true);
			Invalidate();
		}
	}

	virtual void AddReferencedObjects(FReferenceCollector& Collector) override
	{
		Collector.AddReferencedObject(PreviewMesh);
		Collector.AddReferencedObject(PreviewMeshComponent);
	}

	virtual FString GetReferencerName() const override
	{
		return TEXT("STripoAssetViewport");
	}

protected:
	virtual TSharedRef<FEditorViewportClient> MakeEditorViewportClient() override
	{
		ViewportClient = MakeShareable(new FEditorViewportClient(nullptr, PreviewScene.Get(), StaticCastSharedRef<SEditorViewport>(SharedThis(this))));
		ViewportClient->SetViewportType(LVT_Perspective);
		ViewportClient->SetViewModes(VMI_Lit, VMI_Lit);
		ViewportClient->SetRealtime(true);
		ViewportClient->SetInitialViewTransform(LVT_Perspective, FVector(-250.0, -250.0, 150.0), FRotator(-20.0, 45.0, 0.0), 1024.0f);
		ViewportClient->VisibilityDelegate.BindSP(this, &STripoAssetViewport::IsVisible);
		return ViewportClient.ToSharedRef();
	}

private:
	TSharedPtr<FAdvancedPreviewScene> PreviewScene;
	TSharedPtr<FEditorViewportClient> ViewportClient;
	TObjectPtr<UStaticMeshComponent> PreviewMeshComponent = nullptr;
	TObjectPtr<UStaticMesh> PreviewMesh = nullptr;
};

class STripoWorkspacePanel : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(STripoWorkspacePanel) {}
	SLATE_END_ARGS()

	virtual ~STripoWorkspacePanel()
	{
		for (const TSharedPtr<IHttpRequest, ESPMode::ThreadSafe>& Request : ActiveWorkspaceRequests)
		{
			if (Request.IsValid())
			{
				Request->OnProcessRequestComplete().Unbind();
				Request->CancelRequest();
			}
		}
		ActiveWorkspaceRequests.Empty();
	}

	void Construct(const FArguments& InArgs)
	{
		InitializeWorkspaceSession();
		BuildWorkspaceDetailsView();
		LoadStoredWorkspaceApiKey();

		ChildSlot
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(8.0f, 8.0f, 8.0f, 4.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("TripoWorkspaceTitle", "Tripo Workspace"))
					.Font(FAppStyle::GetFontStyle("NormalFontBold"))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspaceGenerateButton", "Generate"))
					.OnClicked(this, &STripoWorkspacePanel::HandleSendModePromptToChatClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspacePaintButton", "Texture/Paint"))
					.OnClicked(this, &STripoWorkspacePanel::HandleWorkspaceModeClicked, FString(TEXT("texture_paint")))
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(8.0f, 0.0f, 8.0f, 4.0f)
			[
				BuildWorkspaceToolbar()
			]

			+ SVerticalBox::Slot()
			.FillHeight(1.0f)
			.Padding(8.0f, 4.0f, 8.0f, 8.0f)
			[
				SNew(SSplitter)

				+ SSplitter::Slot()
				.Value(0.72f)
				[
					SNew(SBorder)
					.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
					.Padding(0.0f)
					[
						SNew(SOverlay)

						+ SOverlay::Slot()
						[
							SAssignNew(AssetViewport, STripoAssetViewport)
						]

						+ SOverlay::Slot()
						.HAlign(HAlign_Left)
						.VAlign(VAlign_Top)
						.Padding(10.0f)
						[
							SNew(STextBlock)
							.Text(LOCTEXT("TripoWorkspaceViewportLabel", "Generated Asset Viewport"))
							.ColorAndOpacity(FSlateColor::UseSubduedForeground())
						]
					]
				]

				+ SSplitter::Slot()
				.Value(0.28f)
				[
					SNew(SBorder)
					.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
					.Padding(8.0f)
					[
						SNew(SVerticalBox)

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 8.0f)
						[
							SNew(STextBlock)
							.Text(LOCTEXT("TripoWorkspaceModeTitle", "Workspace Modes"))
							.Font(FAppStyle::GetFontStyle("SmallFontBold"))
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 6.0f)
						[
							SAssignNew(PreviewAssetPathInput, SEditableTextBox)
							.HintText(LOCTEXT("TripoWorkspaceAssetPathHint", "/Game/Generated/SM_GeneratedAsset"))
							.Text(FText::FromString(PreviewAssetPath))
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 10.0f)
						[
							SNew(SHorizontalBox)

							+ SHorizontalBox::Slot()
							.FillWidth(1.0f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SNew(SButton)
								.Text(LOCTEXT("TripoWorkspaceLoadPreviewAsset", "Load Preview"))
								.OnClicked(this, &STripoWorkspacePanel::HandleLoadPreviewAssetClicked)
							]

							+ SHorizontalBox::Slot()
							.AutoWidth()
							[
								SNew(SButton)
								.Text(LOCTEXT("TripoWorkspaceFramePreviewAsset", "Frame"))
								.OnClicked(this, &STripoWorkspacePanel::HandleFramePreviewAssetClicked)
							]
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 6.0f)
						[
							SNew(SButton)
							.Text(LOCTEXT("TripoWorkspaceTextTo3D", "Text to 3D"))
							.OnClicked(this, &STripoWorkspacePanel::HandleWorkspaceModeClicked, FString(TEXT("text_to_model")))
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 6.0f)
						[
							SNew(SButton)
							.Text(LOCTEXT("TripoWorkspaceMultiImageTo3D", "Multi Image to 3D"))
							.OnClicked(this, &STripoWorkspacePanel::HandleWorkspaceModeClicked, FString(TEXT("multiview_to_model")))
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 12.0f)
						[
							SNew(SButton)
							.Text(LOCTEXT("TripoWorkspaceTexturePaint", "Texture Paint"))
							.OnClicked(this, &STripoWorkspacePanel::HandleWorkspaceModeClicked, FString(TEXT("texture_paint")))
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 8.0f)
						[
							SNew(STextBlock)
							.Text(this, &STripoWorkspacePanel::GetActiveWorkspaceModeText)
							.Font(FAppStyle::GetFontStyle("SmallFontBold"))
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 8.0f)
						[
							SAssignNew(ModeControlsBox, SVerticalBox)
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 8.0f)
						[
							SNew(SButton)
							.Text(LOCTEXT("TripoWorkspaceCopyModePrompt", "Copy MCP Prompt"))
							.OnClicked(this, &STripoWorkspacePanel::HandleCopyModePromptClicked)
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 8.0f)
						[
							SNew(STextBlock)
							.Text(this, &STripoWorkspacePanel::GetGenerativeCreditText)
							.ColorAndOpacity(FSlateColor::UseSubduedForeground())
							.AutoWrapText(true)
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 8.0f)
						[
							BuildWorkspaceAuthControls()
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 8.0f)
						[
							SNew(STextBlock)
							.Text(this, &STripoWorkspacePanel::GetPreviewStatusText)
							.ColorAndOpacity(FSlateColor::UseSubduedForeground())
							.AutoWrapText(true)
						]

						+ SVerticalBox::Slot()
						.FillHeight(1.0f)
						[
							SNew(SBorder)
							.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
							.Padding(4.0f)
							[
								WorkspaceDetailsView.IsValid() ? WorkspaceDetailsView.ToSharedRef() : SNullWidget::NullWidget
							]
						]
					]
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(8.0f, 0.0f, 8.0f, 8.0f)
			[
				BuildWorkspaceStatusStrip()
			]
		];

		LoadGenerativeSettingsSummary();
		RebuildModeControls();
		LoadRequestedPreviewAssetFromConfig(true);
		RegisterActiveTimer(0.5f, FWidgetActiveTimerDelegate::CreateSP(this, &STripoWorkspacePanel::PollRequestedPreviewAsset));
	}

private:
	TSharedRef<SWidget> BuildWorkspaceToolbar()
	{
		return SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
			.Padding(6.0f, 4.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				.Padding(0.0f, 0.0f, 8.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("TripoWorkspaceToolbarModeLabel", "Mode"))
					.Font(FAppStyle::GetFontStyle("SmallFontBold"))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 4.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspaceToolbarTextTo3D", "Text to 3D"))
					.OnClicked(this, &STripoWorkspacePanel::HandleWorkspaceModeClicked, FString(TEXT("text_to_model")))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 4.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspaceToolbarMultiImageTo3D", "Multi Image to 3D"))
					.OnClicked(this, &STripoWorkspacePanel::HandleWorkspaceModeClicked, FString(TEXT("multiview_to_model")))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 12.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspaceToolbarTexturePaint", "Texture Paint"))
					.OnClicked(this, &STripoWorkspacePanel::HandleWorkspaceModeClicked, FString(TEXT("texture_paint")))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SNullWidget::NullWidget
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 4.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspaceToolbarLoadPreview", "Load Preview"))
					.OnClicked(this, &STripoWorkspacePanel::HandleLoadPreviewAssetClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 4.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspaceToolbarFramePreview", "Frame"))
					.OnClicked(this, &STripoWorkspacePanel::HandleFramePreviewAssetClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 4.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspaceToolbarCopyPrompt", "Copy MCP Prompt"))
					.OnClicked(this, &STripoWorkspacePanel::HandleCopyModePromptClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 4.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspaceToolbarSendToChat", "Send to Chat"))
					.OnClicked(this, &STripoWorkspacePanel::HandleSendModePromptToChatClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.Text(LOCTEXT("TripoWorkspaceToolbarRefreshCredits", "Refresh Credits"))
					.OnClicked(this, &STripoWorkspacePanel::HandleRefreshWorkspaceSettingsClicked)
				]
			];
	}

	TSharedRef<SWidget> BuildWorkspaceStatusStrip()
	{
		return SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
			.Padding(8.0f, 4.0f)
			[
				SNew(SVerticalBox)

				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SNew(SHorizontalBox)

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.VAlign(VAlign_Center)
					.Padding(0.0f, 0.0f, 12.0f, 0.0f)
					[
						SNew(STextBlock)
						.Text(this, &STripoWorkspacePanel::GetActiveWorkspaceModeText)
						.Font(FAppStyle::GetFontStyle("SmallFontBold"))
					]

					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
						SNew(STextBlock)
						.Text(this, &STripoWorkspacePanel::GetPreviewStatusText)
						.ColorAndOpacity(FSlateColor::UseSubduedForeground())
						.AutoWrapText(true)
					]
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 3.0f, 0.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(this, &STripoWorkspacePanel::GetGenerativeCreditText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 3.0f, 0.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(this, &STripoWorkspacePanel::GetWorkspaceApiWalletText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 3.0f, 0.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(this, &STripoWorkspacePanel::GetSmartMeshPolicyText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]
			];
	}

	TSharedRef<SWidget> BuildWorkspaceAuthControls()
	{
		return SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
			.Padding(6.0f)
			[
				SNew(SVerticalBox)

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 0.0f, 0.0f, 4.0f)
				[
					SNew(SHorizontalBox)

					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.VAlign(VAlign_Center)
					[
						SNew(STextBlock)
						.Text(LOCTEXT("TripoWorkspaceAuthTitle", "Tripo API Key"))
						.Font(FAppStyle::GetFontStyle("SmallFontBold"))
					]

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.VAlign(VAlign_Center)
					[
						SNew(STextBlock)
						.Text(this, &STripoWorkspacePanel::GetWorkspaceTripoAuthStatusText)
						.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					]
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 0.0f, 0.0f, 4.0f)
				[
					SAssignNew(WorkspaceApiKeyInput, SEditableTextBox)
					.HintText(LOCTEXT("TripoWorkspaceApiKeyHint", "TRIPO_API_KEY or local Saved/MCPChat/secrets.json value"))
					.Text(FText::FromString(WorkspaceApiKey))
					.IsPassword(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 0.0f, 0.0f, 4.0f)
				[
					SNew(SHorizontalBox)

					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.Padding(0.0f, 0.0f, 6.0f, 0.0f)
					[
						SNew(SButton)
						.Text(LOCTEXT("TripoWorkspaceSaveApiKey", "Save API Key"))
						.OnClicked(this, &STripoWorkspacePanel::HandleSaveWorkspaceApiKeyClicked)
					]

					+ SHorizontalBox::Slot()
					.AutoWidth()
					[
						SNew(SButton)
						.Text(LOCTEXT("TripoWorkspaceClearApiKey", "Clear"))
						.OnClicked(this, &STripoWorkspacePanel::HandleClearWorkspaceApiKeyClicked)
					]
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SNew(STextBlock)
					.Text(this, &STripoWorkspacePanel::GetWorkspaceTripoSecretsPathText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]
			];
	}

	FReply HandleWorkspaceModeClicked(FString NewMode)
	{
		CaptureModeInputs();
		ActiveWorkspaceMode = NewMode;
		if (WorkspaceSession.IsValid())
		{
			WorkspaceSession->ActiveMode = ModeNameToSessionMode(ActiveWorkspaceMode);
		}
		RebuildModeControls();
		RefreshWorkspaceDetails();
		PreviewStatus = FText::Format(LOCTEXT("TripoWorkspaceModeChanged", "Mode: {0}"), GetActiveWorkspaceModeText());
		return FReply::Handled();
	}

	FReply HandleCopyModePromptClicked()
	{
		const FString PromptText = BuildModePromptText();
		FPlatformApplicationMisc::ClipboardCopy(*PromptText);
		PreviewStatus = FText::Format(LOCTEXT("TripoWorkspacePromptCopied", "Copied {0} MCP prompt to clipboard."), GetActiveWorkspaceModeText());
		return FReply::Handled();
	}

	FReply HandleSendModePromptToChatClicked()
	{
		const FString PromptText = BuildModePromptText();
		const FString WorkspaceSessionName = GetWorkspaceChatSessionName();
		const FString Path = TEXT("/chat/send?session=") + FGenericPlatformHttp::UrlEncode(WorkspaceSessionName);
		const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeWorkspaceJsonRequest(BuildWorkspaceServerUrl(Path), TEXT("POST"));

		const TSharedPtr<FJsonObject> Payload = MakeShared<FJsonObject>();
		Payload->SetStringField(TEXT("sender"), TEXT("human"));
		Payload->SetStringField(TEXT("message"), PromptText);
		Payload->SetStringField(TEXT("timestamp"), FDateTime::UtcNow().ToIso8601());
		Payload->SetStringField(TEXT("session"), WorkspaceSessionName);
		Payload->SetObjectField(TEXT("context"), BuildWorkspaceChatContext());

		FString Body;
		const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
		FJsonSerializer::Serialize(Payload.ToSharedRef(), Writer);
		Request->SetContentAsString(Body);

		ActiveWorkspaceRequests.Add(Request);
		PreviewStatus = LOCTEXT("TripoWorkspaceSendingToChat", "Sending generation request to MCP Chat...");
		Request->OnProcessRequestComplete().BindSP(this, &STripoWorkspacePanel::HandleWorkspaceChatSendComplete);
		Request->ProcessRequest();

		FGlobalTabmanager::Get()->TryInvokeTab(UnrealMCPChatTabId);
		return FReply::Handled();
	}

	FReply HandleLoadPreviewAssetClicked()
	{
		if (PreviewAssetPathInput.IsValid())
		{
			PreviewAssetPath = PreviewAssetPathInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspaceSession.IsValid())
		{
			WorkspaceSession->PreviewAssetPath = PreviewAssetPath;
		}
		if (AssetViewport.IsValid())
		{
			AssetViewport->LoadStaticMeshFromPath(PreviewAssetPath, PreviewStatus);
		}
		RefreshWorkspaceDetails();
		return FReply::Handled();
	}

	FReply HandleSaveWorkspaceApiKeyClicked()
	{
		if (WorkspaceApiKeyInput.IsValid())
		{
			WorkspaceApiKey = WorkspaceApiKeyInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspaceApiKey.IsEmpty())
		{
			PreviewStatus = LOCTEXT("TripoWorkspaceApiKeyMissing", "Enter a Tripo API key before saving.");
			UpdateWorkspaceApiKeySource();
			return FReply::Handled();
		}

		const FString SecretsPath = GetGenerativeSecretsFilePath();
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(SecretsPath), true);

		TSharedPtr<FJsonObject> SecretsObject = MakeShared<FJsonObject>();
		FString ExistingSecretsText;
		if (FFileHelper::LoadFileToString(ExistingSecretsText, *SecretsPath))
		{
			const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ExistingSecretsText);
			if (!FJsonSerializer::Deserialize(Reader, SecretsObject) || !SecretsObject.IsValid())
			{
				SecretsObject = MakeShared<FJsonObject>();
			}
		}
		SecretsObject->SetStringField(TEXT("TRIPO_API_KEY"), WorkspaceApiKey);
		SecretsObject->RemoveField(TEXT("tripo_api_key"));
		FString SecretsText;
		const TSharedRef<TJsonWriter<>> SecretsWriter = TJsonWriterFactory<>::Create(&SecretsText);
		FJsonSerializer::Serialize(SecretsObject.ToSharedRef(), SecretsWriter);
		FFileHelper::SaveStringToFile(SecretsText, *SecretsPath);

		UpdateWorkspaceApiKeySource();
		RefreshWorkspaceDetails();
		PreviewStatus = LOCTEXT("TripoWorkspaceApiKeySaved", "Saved Tripo API key for generative work.");
		return FReply::Handled();
	}

	FReply HandleClearWorkspaceApiKeyClicked()
	{
		WorkspaceApiKey.Empty();
		if (WorkspaceApiKeyInput.IsValid())
		{
			WorkspaceApiKeyInput->SetText(FText::GetEmpty());
		}

		const FString SecretsPath = GetGenerativeSecretsFilePath();
		IFileManager::Get().MakeDirectory(*FPaths::GetPath(SecretsPath), true);
		TSharedPtr<FJsonObject> SecretsObject = MakeShared<FJsonObject>();
		FString ExistingSecretsText;
		if (FFileHelper::LoadFileToString(ExistingSecretsText, *SecretsPath))
		{
			const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ExistingSecretsText);
			if (!FJsonSerializer::Deserialize(Reader, SecretsObject) || !SecretsObject.IsValid())
			{
				SecretsObject = MakeShared<FJsonObject>();
			}
		}
		SecretsObject->RemoveField(TEXT("TRIPO_API_KEY"));
		SecretsObject->RemoveField(TEXT("tripo_api_key"));
		FString SecretsText;
		const TSharedRef<TJsonWriter<>> SecretsWriter = TJsonWriterFactory<>::Create(&SecretsText);
		FJsonSerializer::Serialize(SecretsObject.ToSharedRef(), SecretsWriter);
		FFileHelper::SaveStringToFile(SecretsText, *SecretsPath);

		UpdateWorkspaceApiKeySource();
		RefreshWorkspaceDetails();
		PreviewStatus = LOCTEXT("TripoWorkspaceApiKeyCleared", "Cleared the saved Tripo API key. Environment TRIPO_API_KEY still takes precedence if set.");
		return FReply::Handled();
	}

	FReply HandleRefreshWorkspaceSettingsClicked()
	{
		LoadGenerativeSettingsSummary();
		RequestWorkspaceApiWalletRefresh();
		RefreshWorkspaceDetails();
		PreviewStatus = LOCTEXT("TripoWorkspaceSettingsRefreshed", "Refreshing generative workspace settings and Tripo API wallet.");
		return FReply::Handled();
	}

	FReply HandleFramePreviewAssetClicked()
	{
		if (AssetViewport.IsValid())
		{
			AssetViewport->FramePreviewMesh();
			PreviewStatus = LOCTEXT("TripoWorkspacePreviewFramed", "Framed the current preview asset.");
		}
		RefreshWorkspaceDetails();
		return FReply::Handled();
	}

	void RebuildModeControls()
	{
		if (!ModeControlsBox.IsValid())
		{
			return;
		}

		ModeControlsBox->ClearChildren();
		WorkspacePromptInput.Reset();
		WorkspaceReferenceViewsInput.Reset();
		WorkspaceFrontImageInput.Reset();
		WorkspaceLeftImageInput.Reset();
		WorkspaceBackImageInput.Reset();
		WorkspaceRightImageInput.Reset();
		WorkspaceExistingTaskInput.Reset();
		WorkspaceTexturePromptInput.Reset();
		WorkspacePaintViewLabelInput.Reset();
		WorkspaceBrushStrengthInput.Reset();
		WorkspaceBlendAmountInput.Reset();
		WorkspaceBrushRadiusInput.Reset();

		if (ActiveWorkspaceMode == TEXT("multiview_to_model"))
		{
			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("TripoWorkspaceMultiImageSlotsLabel", "Ordered Multi Image Views"))
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				BuildMultiImageSlotRow(LOCTEXT("TripoWorkspaceFrontImageLabel", "Front"), WorkspaceFrontImageInput, WorkspaceFrontImage)
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				BuildMultiImageSlotRow(LOCTEXT("TripoWorkspaceLeftImageLabel", "Left"), WorkspaceLeftImageInput, WorkspaceLeftImage)
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				BuildMultiImageSlotRow(LOCTEXT("TripoWorkspaceBackImageLabel", "Back"), WorkspaceBackImageInput, WorkspaceBackImage)
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				BuildMultiImageSlotRow(LOCTEXT("TripoWorkspaceRightImageLabel", "Right"), WorkspaceRightImageInput, WorkspaceRightImage)
			];
		}
		else if (ActiveWorkspaceMode == TEXT("texture_paint"))
		{
			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(WorkspaceExistingTaskInput, SEditableTextBox)
				.HintText(LOCTEXT("TripoWorkspaceExistingTaskHint", "existing Tripo model task id"))
				.Text(FText::FromString(WorkspaceExistingTaskId))
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
			SAssignNew(WorkspaceTexturePromptInput, SEditableTextBox)
				.HintText(LOCTEXT("TripoWorkspaceTexturePromptHint", "texture or paint direction"))
				.Text(FText::FromString(WorkspaceTexturePrompt))
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(WorkspacePaintViewLabelInput, SEditableTextBox)
				.HintText(LOCTEXT("TripoWorkspacePaintViewLabelHint", "source_view or front_view"))
				.Text(FText::FromString(WorkspacePaintViewLabel))
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("TripoWorkspacePaintControlsLabel", "Texture Paint Controls"))
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(0.45f)
				.VAlign(VAlign_Center)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("TripoWorkspaceBrushStrengthLabel", "Strength"))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(0.55f)
				[
					SAssignNew(WorkspaceBrushStrengthInput, SSpinBox<float>)
					.MinValue(0.0f)
					.MaxValue(1.0f)
					.Value(WorkspaceBrushStrength)
				]
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(0.45f)
				.VAlign(VAlign_Center)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("TripoWorkspaceBlendAmountLabel", "Blend"))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(0.55f)
				[
					SAssignNew(WorkspaceBlendAmountInput, SSpinBox<float>)
					.MinValue(0.0f)
					.MaxValue(1.0f)
					.Value(WorkspaceBlendAmount)
				]
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(0.45f)
				.VAlign(VAlign_Center)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("TripoWorkspaceBrushRadiusLabel", "Radius"))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(0.55f)
				[
					SAssignNew(WorkspaceBrushRadiusInput, SSpinBox<float>)
					.MinValue(0.01f)
					.MaxValue(1.0f)
					.Value(WorkspaceBrushRadius)
				]
			];

			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SCheckBox)
				.IsChecked(this, &STripoWorkspacePanel::GetWorkspaceUploadPaintSnapshotCheckState)
				.OnCheckStateChanged(this, &STripoWorkspacePanel::HandleWorkspaceUploadPaintSnapshotChanged)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("TripoWorkspaceUploadPaintSnapshot", "Upload viewport snapshot to Tripo"))
				]
			];
		}
		else
		{
			ModeControlsBox->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(WorkspacePromptInput, SEditableTextBox)
				.HintText(LOCTEXT("TripoWorkspacePromptHint", "asset prompt"))
				.Text(FText::FromString(WorkspacePrompt))
			];
		}

		ModeControlsBox->AddSlot()
		.AutoHeight()
		[
			SAssignNew(WorkspaceAssetNameInput, SEditableTextBox)
			.HintText(LOCTEXT("TripoWorkspaceAssetNameHint", "SM_GeneratedAsset"))
			.Text(FText::FromString(WorkspaceAssetName))
		];
	}

	TSharedRef<SWidget> BuildMultiImageSlotRow(
		const FText& LabelText,
		TSharedPtr<SEditableTextBox>& ImageInput,
		FString& ImageValue)
	{
		return SNew(SVerticalBox)
			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				SNew(STextBlock)
				.Text(LabelText)
				.Font(FAppStyle::GetFontStyle("SmallFont"))
			]
			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SAssignNew(ImageInput, SEditableTextBox)
				.HintText(LOCTEXT("TripoWorkspaceImageInputHint", "URL or local image path"))
				.Text(FText::FromString(ImageValue))
			];
	}

	FString EscapeWorkspaceInputForPrompt(const FString& Input) const
	{
		FString Escaped = Input;
		Escaped = Escaped.Replace(TEXT("\\"), TEXT("\\\\"), ESearchCase::CaseSensitive);
		Escaped = Escaped.Replace(TEXT("\""), TEXT("\\\""), ESearchCase::CaseSensitive);
		Escaped = Escaped.Replace(TEXT("\r"), TEXT("\\r"), ESearchCase::CaseSensitive);
		Escaped = Escaped.Replace(TEXT("\n"), TEXT("\\n"), ESearchCase::CaseSensitive);
		Escaped = Escaped.Replace(TEXT("\t"), TEXT("\\t"), ESearchCase::CaseSensitive);
		return Escaped;
	}

	void AddOrderedMultiImageEntry(TArray<FString>& Entries, const FString& ViewLabel, const FString& ImageValue) const
	{
		if (!ImageValue.IsEmpty())
		{
			Entries.Add(FString::Printf(TEXT("{\"view\":\"%s\",\"image\":\"%s\"}"), *ViewLabel, *EscapeWorkspaceInputForPrompt(ImageValue)));
		}
	}

	FString BuildOrderedMultiImageInputsText() const
	{
		TArray<FString> Entries;
		AddOrderedMultiImageEntry(Entries, TEXT("front"), WorkspaceFrontImage);
		AddOrderedMultiImageEntry(Entries, TEXT("left"), WorkspaceLeftImage);
		AddOrderedMultiImageEntry(Entries, TEXT("back"), WorkspaceBackImage);
		AddOrderedMultiImageEntry(Entries, TEXT("right"), WorkspaceRightImage);

		if (Entries.Num() == 0)
		{
			return TEXT("[]");
		}

		return FString::Printf(TEXT("[%s]"), *FString::Join(Entries, TEXT(", ")));
	}

	FString BuildOrderedMultiImageViewsText() const
	{
		TArray<FString> Entries;
		if (!WorkspaceFrontImage.IsEmpty())
		{
			Entries.Add(FString::Printf(TEXT("front: %s"), *WorkspaceFrontImage));
		}
		if (!WorkspaceLeftImage.IsEmpty())
		{
			Entries.Add(FString::Printf(TEXT("left: %s"), *WorkspaceLeftImage));
		}
		if (!WorkspaceBackImage.IsEmpty())
		{
			Entries.Add(FString::Printf(TEXT("back: %s"), *WorkspaceBackImage));
		}
		if (!WorkspaceRightImage.IsEmpty())
		{
			Entries.Add(FString::Printf(TEXT("right: %s"), *WorkspaceRightImage));
		}

		return Entries.Num() == 0 ? TEXT("none") : FString::Join(Entries, TEXT(", "));
	}

	void CaptureModeInputs()
	{
		if (WorkspacePromptInput.IsValid())
		{
			WorkspacePrompt = WorkspacePromptInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspaceReferenceViewsInput.IsValid())
		{
			WorkspaceReferenceViews = WorkspaceReferenceViewsInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspaceFrontImageInput.IsValid())
		{
			WorkspaceFrontImage = WorkspaceFrontImageInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspaceLeftImageInput.IsValid())
		{
			WorkspaceLeftImage = WorkspaceLeftImageInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspaceBackImageInput.IsValid())
		{
			WorkspaceBackImage = WorkspaceBackImageInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspaceRightImageInput.IsValid())
		{
			WorkspaceRightImage = WorkspaceRightImageInput->GetText().ToString().TrimStartAndEnd();
		}
		if (ActiveWorkspaceMode == TEXT("multiview_to_model"))
		{
			WorkspaceReferenceViews = BuildOrderedMultiImageViewsText();
		}
		if (WorkspaceExistingTaskInput.IsValid())
		{
			WorkspaceExistingTaskId = WorkspaceExistingTaskInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspaceTexturePromptInput.IsValid())
		{
			WorkspaceTexturePrompt = WorkspaceTexturePromptInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspacePaintViewLabelInput.IsValid())
		{
			WorkspacePaintViewLabel = WorkspacePaintViewLabelInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspaceBrushStrengthInput.IsValid())
		{
			WorkspaceBrushStrength = FMath::Clamp(WorkspaceBrushStrengthInput->GetValue(), 0.0f, 1.0f);
		}
		if (WorkspaceBlendAmountInput.IsValid())
		{
			WorkspaceBlendAmount = FMath::Clamp(WorkspaceBlendAmountInput->GetValue(), 0.0f, 1.0f);
		}
		if (WorkspaceBrushRadiusInput.IsValid())
		{
			WorkspaceBrushRadius = FMath::Clamp(WorkspaceBrushRadiusInput->GetValue(), 0.01f, 1.0f);
		}
		if (WorkspaceAssetNameInput.IsValid())
		{
			WorkspaceAssetName = WorkspaceAssetNameInput->GetText().ToString().TrimStartAndEnd();
		}
		if (WorkspacePrompt.IsEmpty())
		{
			WorkspacePrompt = TEXT("game-ready stylized prop, clean silhouette, PBR textures");
		}
		if (WorkspaceTexturePrompt.IsEmpty())
		{
			WorkspaceTexturePrompt = WorkspacePrompt;
		}
		if (WorkspacePaintViewLabel.IsEmpty())
		{
			WorkspacePaintViewLabel = TEXT("source_view");
		}
		if (WorkspaceAssetName.IsEmpty())
		{
			WorkspaceAssetName = TEXT("SM_GeneratedAsset");
		}
		if (WorkspaceSession.IsValid())
		{
			WorkspaceSession->ActiveMode = ModeNameToSessionMode(ActiveWorkspaceMode);
			WorkspaceSession->PreviewAssetPath = PreviewAssetPath;
			WorkspaceSession->Prompt = WorkspacePrompt;
			WorkspaceSession->ReferenceViews = WorkspaceReferenceViews;
			WorkspaceSession->FrontImage = WorkspaceFrontImage;
			WorkspaceSession->LeftImage = WorkspaceLeftImage;
			WorkspaceSession->BackImage = WorkspaceBackImage;
			WorkspaceSession->RightImage = WorkspaceRightImage;
			WorkspaceSession->ExistingModelTaskId = WorkspaceExistingTaskId;
			WorkspaceSession->TexturePrompt = WorkspaceTexturePrompt;
			WorkspaceSession->PaintViewLabel = WorkspacePaintViewLabel;
			WorkspaceSession->BrushStrength = WorkspaceBrushStrength;
			WorkspaceSession->BlendAmount = WorkspaceBlendAmount;
			WorkspaceSession->BrushRadius = WorkspaceBrushRadius;
			WorkspaceSession->bUploadPaintSnapshot = bWorkspaceUploadPaintSnapshot;
			WorkspaceSession->TargetAssetName = WorkspaceAssetName;
		}
	}

	FString BuildModePromptText()
	{
		CaptureModeInputs();
		const FString SafeSession = TEXT("default");
		const FString SafePrompt = WorkspacePrompt.Replace(TEXT("\""), TEXT("'"));
		const FString SafeTexturePrompt = WorkspaceTexturePrompt.Replace(TEXT("\""), TEXT("'"));
		const FString SafeAssetName = WorkspaceAssetName.Replace(TEXT("\""), TEXT(""));
		const FString SafeReferences = WorkspaceReferenceViews.Replace(TEXT("\""), TEXT("'"));
		const FString SafeTaskId = WorkspaceExistingTaskId.Replace(TEXT("\""), TEXT("'"));
		const FString SafePaintViewLabel = WorkspacePaintViewLabel.Replace(TEXT("\""), TEXT("'"));
		const FString SafeMultiImageInputs = BuildOrderedMultiImageInputsText().Replace(TEXT("\""), TEXT("'"));

		if (ActiveWorkspaceMode == TEXT("multiview_to_model"))
		{
			return FString::Printf(
				TEXT("Use MCP tool `gen_tripo_multiview_to_model` from the Tripo Workspace.\n")
				TEXT("Ordered reference views: \"%s\"\n")
				TEXT("Build the `images` list from these slots, preserving order and using image_path for local files, image_url for URLs, or file_token for uploaded tokens: %s\n")
				TEXT("Parameters: texture=true, pbr=true, smart_low_poly=true, face_limit=12000, session_name=\"%s\", confirm_spend=false.\n")
				TEXT("After success, call `gen_tripo_wait_for_task`, then `gen_tripo_import_to_project` with asset_name \"%s\" and open `preview_asset_path` in the Tripo Workspace."),
				*SafeReferences,
				*SafeMultiImageInputs,
				*SafeSession,
				*SafeAssetName
			);
		}

		if (ActiveWorkspaceMode == TEXT("texture_paint"))
		{
			return FString::Printf(
				TEXT("Use the Tripo Workspace Texture Paint flow for model_task_id \"%s\".\n")
				TEXT("Call `gen_prepare_texture_paint_session` with texture_prompt \"%s\", view_angle \"%s\", brush_strength=%.2f, blend_mode \"soft blend %.2f\", paint_notes \"brush_radius=%.2f; source_snapshot_label %s\", save_asset_name \"%s\", and session_name \"%s\".\n")
				TEXT("Call `gen_capture_texture_paint_snapshot` with label \"%s\" and upload_to_tripo=%s, then call `gen_tripo_texture_model` after spend approval, import the result, capture the painted result, record a paint pass with brush_radius=%.2f and blend_amount=%.2f, and compile texture paint evidence."),
				*SafeTaskId,
				*SafeTexturePrompt,
				*SafePaintViewLabel,
				WorkspaceBrushStrength,
				WorkspaceBlendAmount,
				WorkspaceBrushRadius,
				*SafePaintViewLabel,
				*SafeAssetName,
				*SafeSession,
				*SafePaintViewLabel,
				bWorkspaceUploadPaintSnapshot ? TEXT("true") : TEXT("false"),
				WorkspaceBrushRadius,
				WorkspaceBlendAmount
			);
		}

		return FString::Printf(
			TEXT("Use MCP tool `gen_tripo_text_to_model` from the Tripo Workspace.\n")
			TEXT("Parameters: prompt=\"%s\", texture=true, pbr=true, smart_low_poly=true, face_limit=12000, session_name=\"%s\", confirm_spend=false.\n")
			TEXT("After success, call `gen_tripo_wait_for_task`, then `gen_tripo_import_to_project` with asset_name \"%s\" and open `preview_asset_path` in the Tripo Workspace."),
			*SafePrompt,
			*SafeSession,
			*SafeAssetName
		);
	}

	FText GetPreviewStatusText() const
	{
		return PreviewStatus;
	}

	FText GetActiveWorkspaceModeText() const
	{
		if (ActiveWorkspaceMode == TEXT("multiview_to_model"))
		{
			return LOCTEXT("TripoWorkspaceActiveMultiImage", "Multi Image to 3D");
		}
		if (ActiveWorkspaceMode == TEXT("texture_paint"))
		{
			return LOCTEXT("TripoWorkspaceActiveTexturePaint", "Texture Paint");
		}
		return LOCTEXT("TripoWorkspaceActiveTextTo3D", "Text to 3D");
	}

	FText GetGenerativeCreditText() const
	{
		return GenerativeCreditSummary;
	}

	FText GetWorkspaceApiWalletText() const
	{
		return FText::Format(
			LOCTEXT("TripoWorkspaceApiWalletStatus", "Tripo API Wallet: {0} credits available | Frozen: {1} | Status: {2}"),
			FText::FromString(WorkspaceApiWalletBalance),
			FText::FromString(WorkspaceApiWalletFrozen),
			FText::FromString(WorkspaceApiWalletStatus)
		);
	}

	FText GetSmartMeshPolicyText() const
	{
		return FText::FromString(WorkspaceTopologyPolicy);
	}

	FString ResolveWorkspaceApiKey() const
	{
		FString ApiKey = FPlatformMisc::GetEnvironmentVariable(TEXT("TRIPO_API_KEY")).TrimStartAndEnd();
		if (ApiKey.IsEmpty())
		{
			ApiKey = WorkspaceApiKey.TrimStartAndEnd();
		}
		return ApiKey;
	}

	FString GetWorkspaceChatSessionName() const
	{
		return TEXT("tripo-workspace");
	}

	FString BuildWorkspaceServerUrl(const FString& PathAndQuery) const
	{
		return WorkspaceServerBaseUrl + PathAndQuery;
	}

	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> MakeWorkspaceJsonRequest(const FString& Url, const FString& Verb) const
	{
		TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
		Request->SetURL(Url);
		Request->SetVerb(Verb);
		Request->SetHeader(TEXT("Accept"), TEXT("application/json"));
		Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
		return Request;
	}

	TSharedPtr<FJsonObject> BuildWorkspaceChatContext() const
	{
		const TSharedPtr<FJsonObject> Context = MakeShared<FJsonObject>();
		Context->SetStringField(TEXT("source"), TEXT("tripo_workspace"));
		Context->SetStringField(TEXT("active_mode"), ActiveWorkspaceMode);
		Context->SetStringField(TEXT("preview_asset_path"), PreviewAssetPath);
		Context->SetStringField(TEXT("target_asset_name"), WorkspaceAssetName);
		Context->SetStringField(TEXT("ordered_reference_views"), BuildOrderedMultiImageViewsText());
		Context->SetStringField(TEXT("auth_source"), WorkspaceApiKeySource);
		Context->SetBoolField(TEXT("smart_mesh"), true);
		Context->SetStringField(TEXT("topology_policy"), WorkspaceTopologyPolicy);
		Context->SetNumberField(TEXT("face_limit"), 12000);
		return Context;
	}

	void HandleWorkspaceChatSendComplete(FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveWorkspaceRequests.Remove(RequestPtr);
		const bool bSendSucceeded = bWasSuccessful && Response.IsValid() && Response->GetResponseCode() >= 200 && Response->GetResponseCode() < 300;
		PreviewStatus = bSendSucceeded
			? FText::Format(LOCTEXT("TripoWorkspaceSentToChat", "Sent request to MCP Chat session: {0}"), FText::FromString(GetWorkspaceChatSessionName()))
			: LOCTEXT("TripoWorkspaceSendToChatFailed", "Could not send request to MCP Chat. Check that the local MCP chat server is running.");
	}

	void RequestWorkspaceApiWalletRefresh()
	{
		const FString ApiKey = ResolveWorkspaceApiKey();
		if (ApiKey.IsEmpty())
		{
			WorkspaceApiWalletStatus = TEXT("missing API key");
			PreviewStatus = LOCTEXT("TripoWorkspaceWalletMissingKey", "Tripo API key required for wallet refresh.");
			SyncWorkspaceApiWalletToSession();
			return;
		}

		WorkspaceApiWalletStatus = TEXT("refreshing");
		SyncWorkspaceApiWalletToSession();

		TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
		Request->SetURL(TEXT("https://api.tripo3d.ai/v2/openapi/user/balance"));
		Request->SetVerb(TEXT("GET"));
		Request->SetHeader(TEXT("Accept"), TEXT("application/json"));
		Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
		Request->SetHeader(TEXT("Authorization"), FString::Printf(TEXT("Bearer %s"), *ApiKey));

		ActiveWorkspaceRequests.Add(Request);
		Request->OnProcessRequestComplete().BindSP(this, &STripoWorkspacePanel::HandleWorkspaceApiWalletRefreshComplete);
		Request->ProcessRequest();
	}

	void HandleWorkspaceApiWalletRefreshComplete(FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveWorkspaceRequests.Remove(RequestPtr);
		if (!bWasSuccessful || !Response.IsValid())
		{
			WorkspaceApiWalletStatus = TEXT("request failed");
			PreviewStatus = LOCTEXT("TripoWorkspaceWalletRefreshFailed", "Tripo API wallet refresh failed: request failed.");
			SyncWorkspaceApiWalletToSession();
			return;
		}

		TSharedPtr<FJsonObject> RootObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response->GetContentAsString());
		if (!FJsonSerializer::Deserialize(Reader, RootObject) || !RootObject.IsValid())
		{
			WorkspaceApiWalletStatus = FString::Printf(TEXT("HTTP %d: invalid JSON response"), Response->GetResponseCode());
			PreviewStatus = FText::Format(
				LOCTEXT("TripoWorkspaceWalletInvalid", "Tripo API wallet refresh failed: {0}"),
				FText::FromString(WorkspaceApiWalletStatus)
			);
			SyncWorkspaceApiWalletToSession();
			return;
		}

		double CodeValue = 0.0;
		const bool bHasCode = RootObject->TryGetNumberField(TEXT("code"), CodeValue);
		const TSharedPtr<FJsonObject>* DataObject = nullptr;
		if (Response->GetResponseCode() >= 400 || (bHasCode && FMath::RoundToInt(CodeValue) != 0) || !RootObject->TryGetObjectField(TEXT("data"), DataObject) || !DataObject || !DataObject->IsValid())
		{
			FString Message;
			if (!RootObject->TryGetStringField(TEXT("message"), Message) || Message.TrimStartAndEnd().IsEmpty())
			{
				if (!RootObject->TryGetStringField(TEXT("suggestion"), Message) || Message.TrimStartAndEnd().IsEmpty())
				{
					RootObject->TryGetStringField(TEXT("error"), Message);
				}
			}

			Message = Message.TrimStartAndEnd();
			if (Message.Len() > 180)
			{
				Message = Message.Left(180) + TEXT("...");
			}

			WorkspaceApiWalletStatus = Message.IsEmpty()
				? FString::Printf(TEXT("HTTP %d"), Response->GetResponseCode())
				: FString::Printf(TEXT("HTTP %d: %s"), Response->GetResponseCode(), *Message);
			PreviewStatus = FText::Format(
				LOCTEXT("TripoWorkspaceWalletErrorWithMessage", "Tripo API wallet refresh failed: {0}"),
				FText::FromString(WorkspaceApiWalletStatus)
			);
			SyncWorkspaceApiWalletToSession();
			return;
		}

		double BalanceValue = 0.0;
		double FrozenValue = 0.0;
		if ((*DataObject)->TryGetNumberField(TEXT("balance"), BalanceValue))
		{
			WorkspaceApiWalletBalance = FString::FromInt(FMath::RoundToInt(BalanceValue));
		}
		else
		{
			FString BalanceText;
			(*DataObject)->TryGetStringField(TEXT("balance"), BalanceText);
			WorkspaceApiWalletBalance = BalanceText.IsEmpty() ? TEXT("unknown") : BalanceText;
		}
		if ((*DataObject)->TryGetNumberField(TEXT("frozen"), FrozenValue))
		{
			WorkspaceApiWalletFrozen = FString::FromInt(FMath::RoundToInt(FrozenValue));
		}
		else
		{
			FString FrozenText;
			(*DataObject)->TryGetStringField(TEXT("frozen"), FrozenText);
			WorkspaceApiWalletFrozen = FrozenText.IsEmpty() ? TEXT("unknown") : FrozenText;
		}

		WorkspaceApiWalletStatus = TEXT("refreshed");
		PreviewStatus = LOCTEXT("TripoWorkspaceWalletRefreshed", "Tripo API wallet refreshed.");
		SyncWorkspaceApiWalletToSession();
	}

	void SyncWorkspaceApiWalletToSession()
	{
		if (WorkspaceSession.IsValid())
		{
			WorkspaceSession->WalletStatus = WorkspaceApiWalletStatus;
			WorkspaceSession->ApiWalletBalance = WorkspaceApiWalletBalance;
			WorkspaceSession->ApiWalletFrozen = WorkspaceApiWalletFrozen;
		}
		RefreshWorkspaceDetails();
	}

	ECheckBoxState GetWorkspaceUploadPaintSnapshotCheckState() const
	{
		return bWorkspaceUploadPaintSnapshot ? ECheckBoxState::Checked : ECheckBoxState::Unchecked;
	}

	void HandleWorkspaceUploadPaintSnapshotChanged(ECheckBoxState NewState)
	{
		bWorkspaceUploadPaintSnapshot = NewState == ECheckBoxState::Checked;
		if (WorkspaceSession.IsValid())
		{
			WorkspaceSession->bUploadPaintSnapshot = bWorkspaceUploadPaintSnapshot;
		}
		RefreshWorkspaceDetails();
	}

	FText GetWorkspaceTripoAuthStatusText() const
	{
		return FText::Format(LOCTEXT("TripoWorkspaceAuthStatus", "Auth: {0}"), FText::FromString(WorkspaceApiKeySource));
	}

	FText GetWorkspaceTripoSecretsPathText() const
	{
		return FText::Format(LOCTEXT("TripoWorkspaceSecretsPath", "Secrets: {0}"), FText::FromString(GetGenerativeSecretsFilePath()));
	}

	EActiveTimerReturnType PollRequestedPreviewAsset(double InCurrentTime, float InDeltaTime)
	{
		LoadGenerativeSettingsSummary();
		LoadRequestedPreviewAssetFromConfig(false);
		LoadRequestedPreviewAssetFromHandoff(false);
		return EActiveTimerReturnType::Continue;
	}

	void LoadGenerativeSettingsSummary()
	{
		UpdateWorkspaceApiKeySource();

		const FString SettingsPath = FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("MCPChat"), TEXT("generative_settings.json"));
		FString SettingsText;
		if (!FFileHelper::LoadFileToString(SettingsText, *SettingsPath))
		{
			GenerativeCreditSummary = LOCTEXT("TripoWorkspaceCreditsMissing", "Generative Credits: no saved session budget | Smart Mesh: on");
			if (WorkspaceSession.IsValid())
			{
				WorkspaceSession->SessionCreditBudget = 0;
				WorkspaceSession->PendingSpendCredits = 0;
				WorkspaceSession->bSpendConfirmed = false;
				WorkspaceSession->WalletStatus = WorkspaceApiWalletStatus.IsEmpty() ? TEXT("no saved session budget") : WorkspaceApiWalletStatus;
				WorkspaceSession->ApiWalletBalance = WorkspaceApiWalletBalance;
				WorkspaceSession->ApiWalletFrozen = WorkspaceApiWalletFrozen;
				WorkspaceSession->bSmartMeshEnabled = true;
				WorkspaceSession->FaceLimit = 12000;
				WorkspaceSession->TopologyPolicy = WorkspaceTopologyPolicy;
			}
			RefreshWorkspaceDetails();
			return;
		}

		TSharedPtr<FJsonObject> SettingsObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(SettingsText);
		if (!FJsonSerializer::Deserialize(Reader, SettingsObject) || !SettingsObject.IsValid())
		{
			GenerativeCreditSummary = LOCTEXT("TripoWorkspaceCreditsInvalid", "Generative Credits: settings unreadable | Smart Mesh: on");
			if (WorkspaceSession.IsValid())
			{
				WorkspaceSession->WalletStatus = WorkspaceApiWalletStatus.IsEmpty() ? TEXT("settings unreadable") : WorkspaceApiWalletStatus;
				WorkspaceSession->ApiWalletBalance = WorkspaceApiWalletBalance;
				WorkspaceSession->ApiWalletFrozen = WorkspaceApiWalletFrozen;
				WorkspaceSession->bSmartMeshEnabled = true;
				WorkspaceSession->FaceLimit = 12000;
				WorkspaceSession->TopologyPolicy = WorkspaceTopologyPolicy;
			}
			RefreshWorkspaceDetails();
			return;
		}

		double Budget = 0.0;
		double Pending = 0.0;
		bool bConfirmed = false;
		FString Provider = TEXT("tripo");
		FString OutputFolder = TEXT("/Game/Generated");
		SettingsObject->TryGetStringField(TEXT("provider"), Provider);
		SettingsObject->TryGetNumberField(TEXT("session_credit_budget"), Budget);
		SettingsObject->TryGetNumberField(TEXT("pending_spend_credits"), Pending);
		SettingsObject->TryGetBoolField(TEXT("spend_confirmed"), bConfirmed);
		SettingsObject->TryGetStringField(TEXT("output_folder"), OutputFolder);
		if (WorkspaceSession.IsValid())
		{
			WorkspaceSession->Provider = Provider.IsEmpty() ? TEXT("tripo") : Provider;
			WorkspaceSession->ApiKeySource = WorkspaceApiKeySource;
			WorkspaceSession->OutputFolder = OutputFolder;
			WorkspaceSession->SessionCreditBudget = FMath::Max(0, FMath::RoundToInt(Budget));
			WorkspaceSession->PendingSpendCredits = FMath::Max(0, FMath::RoundToInt(Pending));
			WorkspaceSession->bSpendConfirmed = bConfirmed;
			WorkspaceSession->bSmartMeshEnabled = true;
			WorkspaceSession->FaceLimit = 12000;
			WorkspaceSession->TopologyPolicy = WorkspaceTopologyPolicy;
			WorkspaceSession->WalletStatus = WorkspaceApiWalletStatus;
			WorkspaceSession->ApiWalletBalance = WorkspaceApiWalletBalance;
			WorkspaceSession->ApiWalletFrozen = WorkspaceApiWalletFrozen;
		}
		GenerativeCreditSummary = FText::Format(
			LOCTEXT("TripoWorkspaceCreditsSummary", "Generative Credits: local budget {0}/session | Pending {1} | Confirmed {2} | Output {3} | Smart Mesh: on"),
			FText::AsNumber(FMath::Max(0, FMath::RoundToInt(Budget))),
			FText::AsNumber(FMath::Max(0, FMath::RoundToInt(Pending))),
			bConfirmed ? LOCTEXT("TripoWorkspaceSpendConfirmed", "yes") : LOCTEXT("TripoWorkspaceSpendNotConfirmed", "no"),
			FText::FromString(OutputFolder)
		);
		RefreshWorkspaceDetails();
	}

	FString GetGenerativeSecretsFilePath() const
	{
		return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("MCPChat"), TEXT("secrets.json"));
	}

	FString GetWorkspacePreviewHandoffFilePath() const
	{
		return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("MCPChat"), TripoWorkspacePreviewHandoffFile);
	}

	void LoadStoredWorkspaceApiKey()
	{
		WorkspaceApiKey.Empty();

		FString SecretsText;
		if (FFileHelper::LoadFileToString(SecretsText, *GetGenerativeSecretsFilePath()))
		{
			TSharedPtr<FJsonObject> SecretsObject;
			const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(SecretsText);
			if (FJsonSerializer::Deserialize(Reader, SecretsObject) && SecretsObject.IsValid())
			{
				if (!SecretsObject->TryGetStringField(TEXT("TRIPO_API_KEY"), WorkspaceApiKey))
				{
					SecretsObject->TryGetStringField(TEXT("tripo_api_key"), WorkspaceApiKey);
				}
			}
		}

		if (WorkspaceApiKeyInput.IsValid())
		{
			WorkspaceApiKeyInput->SetText(FText::FromString(WorkspaceApiKey));
		}
		UpdateWorkspaceApiKeySource();
	}

	void UpdateWorkspaceApiKeySource()
	{
		const FString EnvKey = FPlatformMisc::GetEnvironmentVariable(TEXT("TRIPO_API_KEY")).TrimStartAndEnd();
		if (!EnvKey.IsEmpty())
		{
			WorkspaceApiKeySource = TEXT("env:TRIPO_API_KEY");
		}
		else if (!WorkspaceApiKey.TrimStartAndEnd().IsEmpty())
		{
			WorkspaceApiKeySource = TEXT("Saved/MCPChat/secrets.json");
		}
		else
		{
			WorkspaceApiKeySource = TEXT("missing");
		}

		if (WorkspaceSession.IsValid())
		{
			WorkspaceSession->ApiKeySource = WorkspaceApiKeySource;
		}
	}

	void LoadRequestedPreviewAssetFromConfig(bool bForce)
	{
		FString RequestedAssetPath;
		if (!GConfig || !GConfig->GetString(TripoWorkspaceConfigSection, TEXT("PreviewAssetPath"), RequestedAssetPath, GEditorPerProjectIni))
		{
			return;
		}
		RequestedAssetPath = RequestedAssetPath.TrimStartAndEnd();
		if (RequestedAssetPath.IsEmpty() || (!bForce && RequestedAssetPath == LastConfigPreviewAssetPath))
		{
			return;
		}
		LastConfigPreviewAssetPath = RequestedAssetPath;
		ApplyRequestedPreviewAsset(RequestedAssetPath);
	}

	void LoadRequestedPreviewAssetFromHandoff(bool bForce)
	{
		FString HandoffText;
		if (!FFileHelper::LoadFileToString(HandoffText, *GetWorkspacePreviewHandoffFilePath()))
		{
			return;
		}

		TSharedPtr<FJsonObject> HandoffObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(HandoffText);
		if (!FJsonSerializer::Deserialize(Reader, HandoffObject) || !HandoffObject.IsValid())
		{
			return;
		}

		FString RequestedAssetPath;
		if (!HandoffObject->TryGetStringField(TEXT("preview_asset_path"), RequestedAssetPath))
		{
			HandoffObject->TryGetStringField(TEXT("asset_path"), RequestedAssetPath);
		}

		RequestedAssetPath = RequestedAssetPath.TrimStartAndEnd();
		if (RequestedAssetPath.IsEmpty() || (!bForce && RequestedAssetPath == LastHandoffPreviewAssetPath))
		{
			return;
		}
		LastHandoffPreviewAssetPath = RequestedAssetPath;
		ApplyRequestedPreviewAsset(RequestedAssetPath);
	}

	void ApplyRequestedPreviewAsset(const FString& RequestedAssetPath)
	{
		PreviewAssetPath = RequestedAssetPath;
		if (PreviewAssetPathInput.IsValid())
		{
			PreviewAssetPathInput->SetText(FText::FromString(PreviewAssetPath));
		}
		if (WorkspaceSession.IsValid())
		{
			WorkspaceSession->PreviewAssetPath = PreviewAssetPath;
		}
		if (AssetViewport.IsValid())
		{
			AssetViewport->LoadStaticMeshFromPath(PreviewAssetPath, PreviewStatus);
		}
		RefreshWorkspaceDetails();
	}

	void InitializeWorkspaceSession()
	{
		WorkspaceSession = TStrongObjectPtr<UTripoWorkspaceSession>(NewObject<UTripoWorkspaceSession>(GetTransientPackage(), TEXT("TripoWorkspaceSession")));
		if (WorkspaceSession.IsValid())
		{
			WorkspaceSession->ActiveMode = ModeNameToSessionMode(ActiveWorkspaceMode);
			WorkspaceSession->PreviewAssetPath = PreviewAssetPath;
			WorkspaceSession->ApiKeySource = WorkspaceApiKeySource;
			WorkspaceSession->Prompt = WorkspacePrompt;
			WorkspaceSession->ReferenceViews = WorkspaceReferenceViews;
			WorkspaceSession->FrontImage = WorkspaceFrontImage;
			WorkspaceSession->LeftImage = WorkspaceLeftImage;
			WorkspaceSession->BackImage = WorkspaceBackImage;
			WorkspaceSession->RightImage = WorkspaceRightImage;
			WorkspaceSession->ExistingModelTaskId = WorkspaceExistingTaskId;
			WorkspaceSession->TexturePrompt = WorkspaceTexturePrompt;
			WorkspaceSession->PaintViewLabel = WorkspacePaintViewLabel;
			WorkspaceSession->bSmartMeshEnabled = true;
			WorkspaceSession->FaceLimit = 12000;
			WorkspaceSession->TopologyPolicy = WorkspaceTopologyPolicy;
			WorkspaceSession->BrushStrength = WorkspaceBrushStrength;
			WorkspaceSession->BlendAmount = WorkspaceBlendAmount;
			WorkspaceSession->BrushRadius = WorkspaceBrushRadius;
			WorkspaceSession->bUploadPaintSnapshot = bWorkspaceUploadPaintSnapshot;
			WorkspaceSession->TargetAssetName = WorkspaceAssetName;
		}
	}

	void BuildWorkspaceDetailsView()
	{
		FPropertyEditorModule& PropertyEditorModule = FModuleManager::LoadModuleChecked<FPropertyEditorModule>(TEXT("PropertyEditor"));
		FDetailsViewArgs DetailsViewArgs;
		DetailsViewArgs.NameAreaSettings = FDetailsViewArgs::HideNameArea;
		DetailsViewArgs.bAllowSearch = true;
		DetailsViewArgs.bShowOptions = false;
		DetailsViewArgs.bShowScrollBar = true;
		WorkspaceDetailsView = PropertyEditorModule.CreateDetailView(DetailsViewArgs);
		RefreshWorkspaceDetails();
	}

	void RefreshWorkspaceDetails()
	{
		if (WorkspaceDetailsView.IsValid() && WorkspaceSession.IsValid())
		{
			WorkspaceDetailsView->SetObject(WorkspaceSession.Get());
		}
	}

	static ETripoWorkspaceMode ModeNameToSessionMode(const FString& ModeName)
	{
		if (ModeName == TEXT("multiview_to_model"))
		{
			return ETripoWorkspaceMode::MultiImageTo3D;
		}
		if (ModeName == TEXT("texture_paint"))
		{
			return ETripoWorkspaceMode::TexturePaint;
		}
		return ETripoWorkspaceMode::TextTo3D;
	}

	TSharedPtr<STripoAssetViewport> AssetViewport;
	TSharedPtr<SVerticalBox> ModeControlsBox;
	TSharedPtr<IDetailsView> WorkspaceDetailsView;
	TSharedPtr<SEditableTextBox> PreviewAssetPathInput;
	TSharedPtr<SEditableTextBox> WorkspacePromptInput;
	TSharedPtr<SEditableTextBox> WorkspaceReferenceViewsInput;
	TSharedPtr<SEditableTextBox> WorkspaceFrontImageInput;
	TSharedPtr<SEditableTextBox> WorkspaceLeftImageInput;
	TSharedPtr<SEditableTextBox> WorkspaceBackImageInput;
	TSharedPtr<SEditableTextBox> WorkspaceRightImageInput;
	TSharedPtr<SEditableTextBox> WorkspaceExistingTaskInput;
	TSharedPtr<SEditableTextBox> WorkspaceTexturePromptInput;
	TSharedPtr<SEditableTextBox> WorkspacePaintViewLabelInput;
	TSharedPtr<SEditableTextBox> WorkspaceAssetNameInput;
	TSharedPtr<SEditableTextBox> WorkspaceApiKeyInput;
	TSharedPtr<SSpinBox<float>> WorkspaceBrushStrengthInput;
	TSharedPtr<SSpinBox<float>> WorkspaceBlendAmountInput;
	TSharedPtr<SSpinBox<float>> WorkspaceBrushRadiusInput;
	TArray<TSharedPtr<IHttpRequest, ESPMode::ThreadSafe>> ActiveWorkspaceRequests;
	FString WorkspaceServerBaseUrl = TEXT("http://127.0.0.1:8000");
	FString PreviewAssetPath = TEXT("/Game/Generated/SM_GeneratedAsset");
	FString LastConfigPreviewAssetPath;
	FString LastHandoffPreviewAssetPath;
	FString ActiveWorkspaceMode = TEXT("text_to_model");
	FString WorkspacePrompt = TEXT("game-ready stylized prop, clean silhouette, PBR textures");
	FString WorkspaceReferenceViews;
	FString WorkspaceFrontImage;
	FString WorkspaceLeftImage;
	FString WorkspaceBackImage;
	FString WorkspaceRightImage;
	FString WorkspaceExistingTaskId;
	FString WorkspaceTexturePrompt;
	FString WorkspacePaintViewLabel = TEXT("source_view");
	FString WorkspaceAssetName = TEXT("SM_GeneratedAsset");
	FString WorkspaceApiKey;
	FString WorkspaceApiKeySource = TEXT("missing");
	FString WorkspaceApiWalletBalance = TEXT("unknown");
	FString WorkspaceApiWalletFrozen = TEXT("unknown");
	FString WorkspaceApiWalletStatus = TEXT("not refreshed");
	FString WorkspaceTopologyPolicy = TEXT("Smart Mesh: locked on | face_limit=12000 | game-ready topology");
	float WorkspaceBrushStrength = 0.75f;
	float WorkspaceBlendAmount = 0.5f;
	float WorkspaceBrushRadius = 0.2f;
	bool bWorkspaceUploadPaintSnapshot = false;
	TStrongObjectPtr<UTripoWorkspaceSession> WorkspaceSession;
	FText GenerativeCreditSummary = LOCTEXT("TripoWorkspaceCreditsInitial", "Generative Credits: loading | Smart Mesh: on");
	FText PreviewStatus = LOCTEXT("TripoWorkspacePreviewStatusInitial", "Load an imported generated Static Mesh to inspect it here.");
};

class FUnrealMCPEditorModule : public IUnrealMCPEditorModule
{
public:
	virtual void StartupModule() override
	{
		FGlobalTabmanager::Get()->RegisterNomadTabSpawner(
			UnrealMCPChatTabId,
			FOnSpawnTab::CreateRaw(this, &FUnrealMCPEditorModule::SpawnChatTab)
		)
		.SetDisplayName(LOCTEXT("UnrealMCPChatTabTitle", "MCP Chat"))
		.SetTooltipText(LOCTEXT("UnrealMCPChatTooltip", "Open the Unreal MCP chat panel for Cursor communication."))
		.SetMenuType(ETabSpawnerMenuType::Hidden);

		FGlobalTabmanager::Get()->RegisterNomadTabSpawner(
			UnrealMCPTripoWorkspaceTabId,
			FOnSpawnTab::CreateRaw(this, &FUnrealMCPEditorModule::SpawnTripoWorkspaceTab)
		)
		.SetDisplayName(LOCTEXT("UnrealMCPTripoWorkspaceTabTitle", "Tripo Workspace"))
		.SetTooltipText(LOCTEXT("UnrealMCPTripoWorkspaceTooltip", "Open the Unreal MCP Tripo asset workspace."))
		.SetMenuType(ETabSpawnerMenuType::Hidden);

		UToolMenus::RegisterStartupCallback(
			FSimpleMulticastDelegate::FDelegate::CreateRaw(this, &FUnrealMCPEditorModule::RegisterMenus)
		);
	}

	virtual void ShutdownModule() override
	{
		if (UToolMenus::IsToolMenuUIEnabled())
		{
			UToolMenus::UnRegisterStartupCallback(this);
			UToolMenus::UnregisterOwner(this);
		}

		FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(UnrealMCPChatTabId);
		FGlobalTabmanager::Get()->UnregisterNomadTabSpawner(UnrealMCPTripoWorkspaceTabId);

		if (TSharedPtr<SWindow> ExistingWindow = TripoWorkspaceWindow.Pin())
		{
			ExistingWindow->RequestDestroyWindow();
			TripoWorkspaceWindow.Reset();
		}
	}

	virtual void OpenTripoWorkspaceWindow() override
	{
		if (TSharedPtr<SWindow> ExistingWindow = TripoWorkspaceWindow.Pin())
		{
			ExistingWindow->BringToFront();
			return;
		}

		TSharedRef<SWindow> WorkspaceWindow = SNew(SWindow)
			.Title(LOCTEXT("UnrealMCPTripoWorkspaceWindowTitle", "Tripo Workspace"))
			.ClientSize(FVector2D(1280.0f, 760.0f))
			.SizingRule(ESizingRule::UserSized)
			.SupportsMaximize(true)
			.SupportsMinimize(true)
			[
				SNew(STripoWorkspacePanel)
			];

		TripoWorkspaceWindow = WorkspaceWindow;
		FSlateApplication::Get().AddWindow(WorkspaceWindow);
	}

private:
	TSharedRef<SDockTab> SpawnChatTab(const FSpawnTabArgs& Args)
	{
		return SNew(SDockTab)
			.TabRole(ETabRole::NomadTab)
			.Label(LOCTEXT("UnrealMCPChatTabLabel", "MCP Chat"))
			[
				SNew(SMCPChatPanel)
			];
	}

	TSharedRef<SDockTab> SpawnTripoWorkspaceTab(const FSpawnTabArgs& Args)
	{
		return SNew(SDockTab)
			.TabRole(ETabRole::NomadTab)
			.Label(LOCTEXT("UnrealMCPTripoWorkspaceTabLabel", "Tripo Workspace"))
			[
				SNew(STripoWorkspacePanel)
			];
	}

	void RegisterMenus()
	{
		FToolMenuOwnerScoped OwnerScoped(this);

		UToolMenu* WindowMenu = UToolMenus::Get()->ExtendMenu(TEXT("LevelEditor.MainMenu.Window"));
		FToolMenuSection& Section = WindowMenu->FindOrAddSection(TEXT("WindowLayout"));
		Section.AddMenuEntry(
			TEXT("OpenUnrealMCPChat"),
			LOCTEXT("OpenUnrealMCPChatLabel", "MCP Chat"),
			LOCTEXT("OpenUnrealMCPChatTooltip", "Open the Unreal MCP chat panel."),
			FSlateIcon(),
			FUIAction(FExecuteAction::CreateStatic([]()
			{
				FGlobalTabmanager::Get()->TryInvokeTab(UnrealMCPChatTabId);
			}))
		);
		Section.AddMenuEntry(
			TEXT("OpenUnrealMCPTripoWorkspace"),
			LOCTEXT("OpenUnrealMCPTripoWorkspaceLabel", "Tripo Workspace"),
			LOCTEXT("OpenUnrealMCPTripoWorkspaceTooltip", "Open the Unreal MCP Tripo asset workspace."),
			FSlateIcon(),
			FUIAction(FExecuteAction::CreateRaw(this, &FUnrealMCPEditorModule::OpenTripoWorkspaceWindow))
		);
	}

	TWeakPtr<SWindow> TripoWorkspaceWindow;
};

#undef LOCTEXT_NAMESPACE

IMPLEMENT_MODULE(FUnrealMCPEditorModule, UnrealMCPEditor)
