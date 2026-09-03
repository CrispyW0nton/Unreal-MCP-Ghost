#include "MCPChatPanel.h"
#include "UnrealMCPEditorModule.h"

#include "AssetRegistry/AssetData.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Brushes/SlateDynamicImageBrush.h"
#include "ContentBrowserModule.h"
#include "DragAndDrop/ActorDragDropOp.h"
#include "DragAndDrop/AssetDragDropOp.h"
#include "Editor.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "HAL/PlatformTime.h"
#include "HAL/PlatformApplicationMisc.h"
#include "IContentBrowserSingleton.h"
#include "Input/DragAndDrop.h"
#include "HttpModule.h"
#include "InputCoreTypes.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Dom/JsonObject.h"
#include "GameFramework/Actor.h"
#include "GenericPlatform/GenericPlatformHttp.h"
#include "Misc/ConfigCacheIni.h"
#include "Misc/FileHelper.h"
#include "Misc/Guid.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonWriter.h"
#include "Selection.h"
#include "Styling/AppStyle.h"
#include "UObject/SoftObjectPath.h"
#include "UObject/Package.h"
#include "UObject/UObjectIterator.h"
#include "Widgets/Layout/SExpandableArea.h"
#include "Widgets/Input/SHyperlink.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SSplitter.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Input/SCheckBox.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Input/SSpinBox.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "SMCPChatPanel"

namespace
{
	const FSlateColor HumanMessageColor(FLinearColor(0.12f, 0.30f, 0.55f, 1.0f));
	const FSlateColor AgentMessageColor(FLinearColor(0.12f, 0.42f, 0.22f, 1.0f));
	const FSlateColor ToolMessageColor(FLinearColor(0.36f, 0.26f, 0.55f, 1.0f));
	const FSlateColor CodeBlockColor(FLinearColor(0.06f, 0.07f, 0.09f, 1.0f));
	const FSlateColor MarkdownAccentColor(FLinearColor(0.72f, 0.82f, 1.0f, 1.0f));
	const FSlateColor ToolCardColor(FLinearColor(0.10f, 0.10f, 0.13f, 1.0f));
	const FSlateColor ToolErrorColor(FLinearColor(0.46f, 0.10f, 0.10f, 1.0f));
	const FSlateColor ErrorStatusColor(FLinearColor(0.9f, 0.18f, 0.12f, 1.0f));
	const FSlateColor OkStatusColor(FLinearColor(0.2f, 0.75f, 0.28f, 1.0f));
	const FSlateColor PendingStatusColor(FLinearColor(0.75f, 0.62f, 0.22f, 1.0f));
	constexpr int32 CoreCommandPaletteKbDocCount = 5;
	const TCHAR* ChatPanelConfigSection = TEXT("UnrealMCP.ChatPanel");

	FString GetStringField(const TSharedPtr<FJsonObject>& Object, const FString& FieldName)
	{
		FString Value;
		if (Object.IsValid())
		{
			Object->TryGetStringField(FieldName, Value);
		}
		return Value;
	}
}

void SMCPChatPanel::Construct(const FArguments& InArgs)
{
	LoadLayoutSettings();
	LoadGenerativeSettings();

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
				.Text(LOCTEXT("Title", "Unreal MCP Chat"))
				.Font(FAppStyle::GetFontStyle("NormalFontBold"))
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Center)
			.Padding(8.0f, 0.0f)
			[
				SAssignNew(StatusText, STextBlock)
				.Text(LOCTEXT("StatusConnecting", "Connecting..."))
				.ColorAndOpacity(PendingStatusColor)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SButton)
				.Text(this, &SMCPChatPanel::GetToolPaletteToggleText)
				.OnClicked(this, &SMCPChatPanel::HandleToggleToolPaletteClicked)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("CommandPalette", "Command Palette"))
				.OnClicked(this, &SMCPChatPanel::HandleOpenCommandPaletteClicked)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("RefreshCockpit", "Cockpit"))
				.ToolTipText(LOCTEXT("RefreshCockpitTooltip", "Refresh the read-only IDE companion cockpit overview for this chat session."))
				.OnClicked(this, &SMCPChatPanel::HandleRefreshCockpitClicked)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SButton)
				.Text(this, &SMCPChatPanel::GetSamplePromptsToggleText)
				.OnClicked(this, &SMCPChatPanel::HandleToggleSamplePromptsClicked)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("GenerateAssetQuickAction", "Generate Asset"))
				.OnClicked(this, &SMCPChatPanel::HandleOpenGenerateAssetClicked)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("OpenTripoWorkspaceAction", "Tripo Workspace"))
				.OnClicked(this, &SMCPChatPanel::HandleOpenTripoWorkspaceClicked)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SButton)
				.Text(this, &SMCPChatPanel::GetGenerativeSettingsToggleText)
				.OnClicked(this, &SMCPChatPanel::HandleToggleGenerativeSettingsClicked)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("ShowTour", "Tour"))
				.OnClicked(this, &SMCPChatPanel::HandleOnboardingNextClicked)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			[
				SNew(SButton)
				.Text(LOCTEXT("ClearHistory", "Clear History"))
				.OnClicked(this, &SMCPChatPanel::HandleClearClicked)
			]
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f, 0.0f, 8.0f, 4.0f)
		[
			SNew(STextBlock)
			.Text(FText::Format(LOCTEXT("Endpoint", "Endpoint: {0}"), FText::FromString(ServerBaseUrl)))
			.ColorAndOpacity(FSlateColor::UseSubduedForeground())
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f, 0.0f, 8.0f, 4.0f)
		[
			SNew(SBox)
			.Visibility(this, &SMCPChatPanel::GetOnboardingVisibility)
			[
				BuildOnboardingOverlay()
			]
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f, 0.0f, 8.0f, 4.0f)
		[
			SNew(SBox)
			.Visibility(this, &SMCPChatPanel::GetSamplePromptsVisibility)
			[
				BuildSamplePrompts()
			]
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f, 0.0f, 8.0f, 4.0f)
		[
			SNew(SBox)
			.Visibility(this, &SMCPChatPanel::GetGenerateAssetDialogVisibility)
			[
				BuildGenerateAssetDialog()
			]
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f, 0.0f, 8.0f, 4.0f)
		[
			SNew(SBox)
			.Visibility(this, &SMCPChatPanel::GetGenerativeSettingsVisibility)
			[
				BuildGenerativeSettingsPanel()
			]
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f, 0.0f, 8.0f, 4.0f)
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
			.Padding(8.0f)
			[
				SAssignNew(ToolDetailDrawer, SVerticalBox)

				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SAssignNew(ToolDetailTitle, STextBlock)
					.Text(LOCTEXT("ToolDetailEmptyTitle", "Tool Call Details"))
					.Font(FAppStyle::GetFontStyle("SmallFontBold"))
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 4.0f, 0.0f, 0.0f)
				[
					SAssignNew(ToolDetailBody, STextBlock)
					.Text(LOCTEXT("ToolDetailEmptyBody", "Select a tool card to inspect full args, outputs, and log tail."))
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]
			]
		]

		+ SVerticalBox::Slot()
		.FillHeight(1.0f)
		.Padding(8.0f, 4.0f, 8.0f, 8.0f)
		[
			SNew(SSplitter)
			.Orientation(Orient_Horizontal)
			.ResizeMode(ESplitterResizeMode::Fill)

			+ SSplitter::Slot()
			.Value(SessionSidebarSize)
			.OnSlotResized(SSplitter::FOnSlotResized::CreateSP(this, &SMCPChatPanel::RecordHorizontalSplitterResize, 0))
			[
				BuildSessionSidebar()
			]

			+ SSplitter::Slot()
			.Value(ToolPaletteSize)
			.OnSlotResized(SSplitter::FOnSlotResized::CreateSP(this, &SMCPChatPanel::RecordHorizontalSplitterResize, 1))
			[
				SNew(SBox)
				.Visibility(this, &SMCPChatPanel::GetToolPaletteVisibility)
				[
					BuildToolPalette()
				]
			]

			+ SSplitter::Slot()
			.Value(ChatWorkspaceSize)
			.OnSlotResized(SSplitter::FOnSlotResized::CreateSP(this, &SMCPChatPanel::RecordHorizontalSplitterResize, 2))
			[
				SNew(SSplitter)
				.Orientation(Orient_Vertical)
				.ResizeMode(ESplitterResizeMode::Fill)

				+ SSplitter::Slot()
				.Value(ConversationSize)
				.OnSlotResized(SSplitter::FOnSlotResized::CreateSP(this, &SMCPChatPanel::RecordVerticalSplitterResize, 0))
				[
					SNew(SVerticalBox)

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 0.0f, 0.0f, 6.0f)
					[
						BuildCockpitOverviewBar()
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 0.0f, 0.0f, 6.0f)
					[
						SNew(SBox)
						.Visibility(this, &SMCPChatPanel::GetCommandPaletteVisibility)
						[
							BuildCommandPalette()
						]
					]

					+ SVerticalBox::Slot()
					.FillHeight(1.0f)
					[
						SNew(SBorder)
						.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
						.Padding(6.0f)
						[
							SAssignNew(MessageScrollBox, SScrollBox)
						]
					]
				]

			+ SSplitter::Slot()
			.Value(ComposerSize)
			.OnSlotResized(SSplitter::FOnSlotResized::CreateSP(this, &SMCPChatPanel::RecordVerticalSplitterResize, 1))
			[
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
				.Padding(8.0f)
				[
					SNew(SVerticalBox)

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 0.0f, 0.0f, 6.0f)
					[
						BuildContextChips()
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 0.0f, 0.0f, 6.0f)
					[
						SNew(STextBlock)
						.Text(LOCTEXT("ComposerDropHint", "Drop assets, actors, or files here. Enter sends; Shift+Enter adds a new line."))
						.ColorAndOpacity(FSlateColor::UseSubduedForeground())
						.AutoWrapText(true)
					]

					+ SVerticalBox::Slot()
					.FillHeight(1.0f)
					[
						SAssignNew(MessageInput, SMultiLineEditableTextBox)
						.HintText(LOCTEXT("InputHint", "Type a message for the agent..."))
						.AutoWrapText(true)
						.OnKeyDownHandler(this, &SMCPChatPanel::HandleComposerKeyDown)
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 8.0f, 0.0f, 0.0f)
					[
						SNew(SHorizontalBox)

						+ SHorizontalBox::Slot()
						.FillWidth(1.0f)
						[
							SNew(STextBlock)
							.Text(LOCTEXT("ComposerMode", "Markdown supported. Code fences render as highlighted blocks."))
							.ColorAndOpacity(FSlateColor::UseSubduedForeground())
						]

						+ SHorizontalBox::Slot()
						.AutoWidth()
						[
							SNew(SButton)
							.Text(LOCTEXT("Send", "Send"))
							.OnClicked(this, &SMCPChatPanel::HandleSendClicked)
						]
					]
				]
			]
			]
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f, 0.0f, 8.0f, 8.0f)
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
			.Padding(6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(this, &SMCPChatPanel::GetStatusFooterText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				[
					SNew(SButton)
					.Text(this, &SMCPChatPanel::GetTelemetryToggleText)
					.OnClicked(this, &SMCPChatPanel::HandleToggleTelemetryClicked)
				]
			]
		]
	];

	LoadSessions();
	LoadHistory();
	LoadCockpitOverview();
	LoadToolPalette();
	PollAgentMessages();
	PollTickerHandle = FTSTicker::GetCoreTicker().AddTicker(
		FTickerDelegate::CreateRaw(this, &SMCPChatPanel::HandlePollTick),
		2.0f
	);
}

SMCPChatPanel::~SMCPChatPanel()
{
	SaveLayoutSettings();

	if (PollTickerHandle.IsValid())
	{
		FTSTicker::GetCoreTicker().RemoveTicker(PollTickerHandle);
	}

	for (const TSharedPtr<IHttpRequest, ESPMode::ThreadSafe>& Request : ActiveRequests)
	{
		if (Request.IsValid())
		{
			Request->OnProcessRequestComplete().Unbind();
			Request->CancelRequest();
		}
	}
	ActiveRequests.Reset();
}

FReply SMCPChatPanel::HandleSendClicked()
{
	if (!MessageInput.IsValid())
	{
		return FReply::Handled();
	}

	const FString Text = MessageInput->GetText().ToString().TrimStartAndEnd();
	if (Text.IsEmpty())
	{
		return FReply::Handled();
	}

	MessageInput->SetText(FText::GetEmpty());
	SendHumanMessage(Text);
	AddMessage(FChatMessage{MakeLocalMessageId(), TEXT("human"), Text, MakeCurrentTimestamp()});

	return FReply::Handled();
}

FReply SMCPChatPanel::HandleClearClicked()
{
	ClearHistoryOnServer();
	Messages.Reset();
	StreamingMessageTextBlocks.Reset();
	EvidenceImageBrushes.Reset();
	RebuildMessageList();
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleNewSessionClicked()
{
	const FString NewSessionName = BuildNewSessionName();
	const TSharedPtr<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("name"), NewSessionName);
	CurrentSessionName = NewSessionName;
	LastAgentPollTimestamp.Empty();
	Messages.Reset();
	RebuildMessageList();
	SendSessionAction(TEXT("/chat/session/new"), Payload, LOCTEXT("StatusSessionCreated", "Session created"));
	LoadHistory();
	LoadCockpitOverview();
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleContinueLastSessionClicked()
{
	if (!LastSessionName.IsEmpty())
	{
		CurrentSessionName = LastSessionName;
		LastAgentPollTimestamp.Empty();
		LoadHistory();
		LoadCockpitOverview();
		RebuildSessionList();
		SetStatus(FText::Format(LOCTEXT("StatusSessionContinued", "Continuing {0}"), FText::FromString(CurrentSessionName)), OkStatusColor);
	}
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleRenameSessionClicked()
{
	const FString NewName = BuildRenamedSessionName();
	const TSharedPtr<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("old_name"), CurrentSessionName);
	Payload->SetStringField(TEXT("new_name"), NewName);
	CurrentSessionName = NewName;
	SendSessionAction(TEXT("/chat/session/rename"), Payload, LOCTEXT("StatusSessionRenamed", "Session renamed"));
	return FReply::Handled();
}

FReply SMCPChatPanel::HandlePinSessionClicked()
{
	bool bCurrentlyPinned = false;
	for (const FChatSessionEntry& Session : ChatSessions)
	{
		if (Session.Name == CurrentSessionName)
		{
			bCurrentlyPinned = Session.bPinned;
			break;
		}
	}

	const TSharedPtr<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("name"), CurrentSessionName);
	Payload->SetBoolField(TEXT("pinned"), !bCurrentlyPinned);
	SendSessionAction(TEXT("/chat/session/pin"), Payload, LOCTEXT("StatusSessionPinned", "Session pin updated"));
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleDeleteSessionClicked()
{
	const TSharedPtr<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("name"), CurrentSessionName);
	SendSessionAction(TEXT("/chat/session/delete"), Payload, LOCTEXT("StatusSessionDeleted", "Session deleted"));
	CurrentSessionName = TEXT("default");
	LastAgentPollTimestamp.Empty();
	Messages.Reset();
	RebuildMessageList();
	LoadHistory();
	LoadCockpitOverview();
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleExportSessionClicked()
{
	const FString Path = TEXT("/chat/session/export?name=") + FGenericPlatformHttp::UrlEncode(CurrentSessionName);
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(Path), TEXT("GET"));
	const double RequestStartSeconds = FPlatformTime::Seconds();
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
		RecordServerLatency(RequestStartSeconds);
		if (!bWasSuccessful || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
		{
			SetStatus(LOCTEXT("StatusSessionExportFailed", "Export failed"), ErrorStatusColor);
			return;
		}

		FPlatformApplicationMisc::ClipboardCopy(*Response->GetContentAsString());
		SetStatus(LOCTEXT("StatusSessionExported", "Session markdown copied"), OkStatusColor);
	});
	Request->ProcessRequest();
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleSessionClicked(FChatSessionEntry Session)
{
	if (!Session.Name.IsEmpty())
	{
		CurrentSessionName = Session.Name;
		LastAgentPollTimestamp.Empty();
		LoadHistory();
		LoadCockpitOverview();
		RebuildSessionList();
		SetStatus(FText::Format(LOCTEXT("StatusSessionLoaded", "Loaded {0}"), FText::FromString(CurrentSessionName)), OkStatusColor);
	}
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleToggleToolPaletteClicked()
{
	bToolPaletteVisible = !bToolPaletteVisible;
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleRefreshToolPaletteClicked()
{
	LoadToolPalette();
	SetStatus(LOCTEXT("StatusToolPaletteRefresh", "Refreshing tools"), PendingStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleToolPaletteToolClicked(FToolPaletteEntry Tool)
{
	const FString PromptTemplate = BuildToolPromptTemplate(Tool);
	InsertComposerText(PromptTemplate);
	SetStatus(FText::Format(LOCTEXT("StatusToolTemplateInserted", "Inserted {0} template"), FText::FromString(Tool.Name)), OkStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleOpenCommandPaletteClicked()
{
	OpenCommandPaletteWithFilter(TEXT(""), LOCTEXT("StatusCommandPaletteOpened", "Command palette opened"));
	RecordTelemetryEvent(TEXT("command_palette_opened"));
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleOpenWorkflowActionsClicked()
{
	OpenCommandPaletteWithFilter(TEXT("workflow"), LOCTEXT("StatusWorkflowActionsOpened", "Workflow actions opened"));
	RecordTelemetryEvent(TEXT("workflow_actions_opened"));
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleRefreshCockpitClicked()
{
	LoadCockpitOverview();
	SetStatus(LOCTEXT("StatusCockpitRefreshing", "Refreshing cockpit overview"), PendingStatusColor);
	return FReply::Handled();
}

void SMCPChatPanel::HandleCommandPaletteTextChanged(const FText& Text)
{
	CommandPaletteFilter = Text.ToString();
	RebuildCommandPaletteResults();
}

FReply SMCPChatPanel::HandleCommandPaletteItemClicked(FCommandPaletteItem Item)
{
	if (Item.Kind == TEXT("slash") && Item.Label == TEXT("/clear"))
	{
		HandleClearClicked();
	}
	else
	{
		InsertComposerText(Item.InsertText.IsEmpty() ? Item.Label : Item.InsertText);
		SetStatus(FText::Format(LOCTEXT("StatusCommandPaletteInserted", "Inserted {0}"), FText::FromString(Item.Label)), OkStatusColor);
	}

	bCommandPaletteVisible = false;
	CommandPaletteFilter.Empty();
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleToggleTelemetryClicked()
{
	bTelemetryEnabled = !bTelemetryEnabled;
	SaveLayoutSettings();
	if (bTelemetryEnabled)
	{
		RecordTelemetryEvent(TEXT("telemetry_enabled"));
		SetStatus(LOCTEXT("StatusTelemetryEnabled", "Metrics enabled"), OkStatusColor);
	}
	else
	{
		SetStatus(LOCTEXT("StatusTelemetryDisabled", "Metrics disabled"), PendingStatusColor);
	}
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleOpenGenerateAssetClicked()
{
	bGenerateAssetDialogVisible = !bGenerateAssetDialogVisible;
	if (bGenerateAssetDialogVisible)
	{
		LoadGenerativeSettings();
	}
	SetStatus(
		bGenerateAssetDialogVisible ? LOCTEXT("StatusGenerateAssetOpen", "Generate Asset quick action open") : LOCTEXT("StatusGenerateAssetClosed", "Generate Asset quick action hidden"),
		PendingStatusColor
	);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleOpenTripoWorkspaceClicked()
{
	IUnrealMCPEditorModule::Get().OpenTripoWorkspaceWindow();
	RecordTelemetryEvent(TEXT("tripo_workspace_opened"));
	SetStatus(LOCTEXT("StatusTripoWorkspaceOpen", "Tripo Workspace window opened"), OkStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleInsertGenerateAssetToolCallClicked()
{
	if (GenerateAssetModeInput.IsValid())
	{
		GenerateAssetMode = GenerateAssetModeInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetPromptInput.IsValid())
	{
		GenerateAssetPrompt = GenerateAssetPromptInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetNameInput.IsValid())
	{
		GenerateAssetName = GenerateAssetNameInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetReferenceImagesInput.IsValid())
	{
		GenerateAssetReferenceImages = GenerateAssetReferenceImagesInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetExistingTaskIdInput.IsValid())
	{
		GenerateAssetExistingTaskId = GenerateAssetExistingTaskIdInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetTexturePromptInput.IsValid())
	{
		GenerateAssetTexturePrompt = GenerateAssetTexturePromptInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetPaintViewLabelInput.IsValid())
	{
		GenerateAssetPaintViewLabel = GenerateAssetPaintViewLabelInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetMode.IsEmpty())
	{
		GenerateAssetMode = TEXT("text_to_model");
	}
	if (GenerateAssetPrompt.IsEmpty())
	{
		GenerateAssetPrompt = TEXT("game-ready stylized prop, clean silhouette, PBR textures");
	}
	if (GenerateAssetName.IsEmpty())
	{
		GenerateAssetName = TEXT("SM_GeneratedAsset");
	}
	if (GenerateAssetTexturePrompt.IsEmpty())
	{
		GenerateAssetTexturePrompt = GenerateAssetPrompt;
	}
	if (GenerateAssetPaintViewLabel.IsEmpty())
	{
		GenerateAssetPaintViewLabel = TEXT("source_view");
	}
	GenerateAssetPaintBrushStrength = FMath::Clamp(GenerateAssetPaintBrushStrength, 0.0f, 1.0f);
	GenerateAssetPaintBlend = FMath::Clamp(GenerateAssetPaintBlend, 0.0f, 1.0f);
	GenerateAssetPaintBrushRadius = FMath::Clamp(GenerateAssetPaintBrushRadius, 0.01f, 1.0f);

	InsertComposerText(BuildGenerateAssetToolCallPrompt());
	bGenerateAssetDialogVisible = false;
	RecordTelemetryEvent(TEXT("generate_asset_quick_action_inserted"));
	SetStatus(
		bGenerativeSpendConfirmed ? LOCTEXT("StatusGenerateAssetInsertedConfirmed", "Inserted Tripo asset generation call") : LOCTEXT("StatusGenerateAssetInsertedNeedsSpend", "Inserted Tripo call; confirm spend before paid execution"),
		bGenerativeSpendConfirmed ? OkStatusColor : PendingStatusColor
	);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleToggleGenerativeSettingsClicked()
{
	bGenerativeSettingsVisible = !bGenerativeSettingsVisible;
	if (bGenerativeSettingsVisible)
	{
		LoadGenerativeSettings();
	}
	SetStatus(
		bGenerativeSettingsVisible ? LOCTEXT("StatusGenerativeSettingsOpen", "Generate settings open") : LOCTEXT("StatusGenerativeSettingsClosed", "Generate settings hidden"),
		PendingStatusColor
	);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleSaveGenerativeSettingsClicked()
{
	if (GenerativeApiKeyInput.IsValid())
	{
		GenerativeApiKey = GenerativeApiKeyInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerativeUthanaApiKeyInput.IsValid())
	{
		GenerativeUthanaApiKey = GenerativeUthanaApiKeyInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerativeModelVersionInput.IsValid())
	{
		GenerativeModelVersion = GenerativeModelVersionInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerativeTextureQualityInput.IsValid())
	{
		GenerativeTextureQuality = GenerativeTextureQualityInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerativeOutputFolderInput.IsValid())
	{
		GenerativeOutputFolder = GenerativeOutputFolderInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerativeCreditBudgetInput.IsValid())
	{
		GenerativeSessionCreditBudget = FMath::Max(0, FCString::Atoi(*GenerativeCreditBudgetInput->GetText().ToString()));
	}

	if (GenerativeModelVersion.IsEmpty())
	{
		GenerativeModelVersion = TEXT("tripo-default");
	}
	if (GenerativeTextureQuality.IsEmpty())
	{
		GenerativeTextureQuality = TEXT("standard");
	}
	if (!GenerativeOutputFolder.StartsWith(TEXT("/Game")))
	{
		GenerativeOutputFolder = TEXT("/Game/Generated");
	}

	SaveGenerativeSettingsToDisk();
	RecordTelemetryEvent(TEXT("generative_settings_saved"));
	SetStatus(LOCTEXT("StatusGenerativeSettingsSaved", "Generative settings saved"), OkStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleConfirmGenerativeSpendClicked()
{
	if (GenerativePendingSpendInput.IsValid())
	{
		GenerativePendingSpendCredits = FMath::Max(0, FCString::Atoi(*GenerativePendingSpendInput->GetText().ToString()));
	}
	bGenerativeSpendConfirmed = GenerativePendingSpendCredits > 0 && GenerativePendingSpendCredits <= GenerativeSessionCreditBudget;
	SaveGenerativeSettingsToDisk();
	SetStatus(
		bGenerativeSpendConfirmed ? LOCTEXT("StatusGenerativeSpendConfirmed", "Next generative spend confirmed") : LOCTEXT("StatusGenerativeSpendRejected", "Spend exceeds budget or is empty"),
		bGenerativeSpendConfirmed ? OkStatusColor : ErrorStatusColor
	);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleRefreshGenerativeBalanceClicked()
{
	if (GenerativeApiKeyInput.IsValid())
	{
		GenerativeApiKey = GenerativeApiKeyInput->GetText().ToString().TrimStartAndEnd();
	}
	RequestGenerativeBalanceRefresh();
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleOnboardingNextClicked()
{
	bOnboardingVisible = true;
	if (bOnboardingCompleted)
	{
		bOnboardingCompleted = false;
		OnboardingStepIndex = 0;
	}
	else if (OnboardingStepIndex < 3)
	{
		++OnboardingStepIndex;
	}
	else
	{
		bOnboardingCompleted = true;
		bOnboardingVisible = false;
	}
	SaveLayoutSettings();
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleOnboardingDismissClicked()
{
	bOnboardingCompleted = true;
	bOnboardingVisible = false;
	SaveLayoutSettings();
	SetStatus(LOCTEXT("StatusOnboardingDone", "Onboarding complete"), OkStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleToggleSamplePromptsClicked()
{
	bSamplePromptsVisible = !bSamplePromptsVisible;
	SetStatus(
		bSamplePromptsVisible ? LOCTEXT("StatusSamplePromptsOpen", "Sample prompts open") : LOCTEXT("StatusSamplePromptsClosed", "Sample prompts hidden"),
		PendingStatusColor
	);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleSamplePromptClicked(FSamplePromptItem Item)
{
	InsertComposerText(Item.Prompt);
	bSamplePromptsVisible = false;
	RecordTelemetryEvent(TEXT("sample_prompt_inserted"));
	SetStatus(FText::Format(LOCTEXT("StatusSamplePromptInserted", "Inserted sample: {0}"), FText::FromString(Item.Label)), OkStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleComposerKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent)
{
	if (InKeyEvent.GetKey() == EKeys::K && InKeyEvent.IsControlDown())
	{
		return HandleOpenCommandPaletteClicked();
	}

	if (InKeyEvent.GetKey() == EKeys::Enter && !InKeyEvent.IsShiftDown())
	{
		return HandleSendClicked();
	}

	return FReply::Unhandled();
}

FReply SMCPChatPanel::HandleCopyClicked(FString Message) const
{
	FPlatformApplicationMisc::ClipboardCopy(*Message);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleRerunClicked(FString Message, FString Sender)
{
	if (NormaliseSender(Sender) == TEXT("user"))
	{
		SendHumanMessage(Message);
		AddMessage(FChatMessage{MakeLocalMessageId(), TEXT("human"), Message, MakeCurrentTimestamp()});
		SetStatus(LOCTEXT("StatusRerunSent", "Prompt re-run"), OkStatusColor);
	}
	else
	{
		InsertComposerText(Message);
		SetStatus(LOCTEXT("StatusRerunCopied", "Message copied to composer"), PendingStatusColor);
	}

	return FReply::Handled();
}

FReply SMCPChatPanel::HandleOpenLogClicked()
{
	FGlobalTabmanager::Get()->TryInvokeTab(FName(TEXT("OutputLog")));
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleRevealAssetClicked(FString Message)
{
	const FString AssetReference = ExtractFirstAssetReference(Message);
	if (AssetReference.IsEmpty())
	{
		SetStatus(LOCTEXT("StatusNoAssetReference", "No @asset reference found"), PendingStatusColor);
		return FReply::Handled();
	}

	FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
	TArray<FAssetData> Assets;
	AssetRegistryModule.Get().GetAssetsByPackageName(FName(*AssetReference), Assets);

	if (Assets.IsEmpty() && AssetReference.Contains(TEXT(".")))
	{
		const FAssetData AssetData = AssetRegistryModule.Get().GetAssetByObjectPath(FSoftObjectPath(AssetReference));
		if (AssetData.IsValid())
		{
			Assets.Add(AssetData);
		}
	}

	if (Assets.IsEmpty())
	{
		SetStatus(FText::Format(LOCTEXT("StatusAssetNotFound", "Asset not found: {0}"), FText::FromString(AssetReference)), ErrorStatusColor);
		return FReply::Handled();
	}

	FContentBrowserModule& ContentBrowserModule = FModuleManager::LoadModuleChecked<FContentBrowserModule>(TEXT("ContentBrowser"));
	ContentBrowserModule.Get().SyncBrowserToAssets(Assets);
	SetStatus(FText::Format(LOCTEXT("StatusAssetRevealed", "Revealed {0}"), FText::FromString(AssetReference)), OkStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleOpenTripoWorkspaceAssetClicked(FString Message)
{
	const FString AssetReference = ExtractFirstAssetReference(Message);
	if (AssetReference.IsEmpty())
	{
		SetStatus(LOCTEXT("StatusNoTripoPreviewAsset", "No generated /Game asset path found for Tripo preview"), PendingStatusColor);
		return FReply::Handled();
	}

	const TCHAR* TripoWorkspaceConfigSection = TEXT("UnrealMCP.TripoWorkspace");
	GConfig->SetString(TripoWorkspaceConfigSection, TEXT("PreviewAssetPath"), *AssetReference, GEditorPerProjectIni);
	GConfig->Flush(false, GEditorPerProjectIni);
	IUnrealMCPEditorModule::Get().OpenTripoWorkspaceWindow();
	RecordTelemetryEvent(TEXT("tripo_workspace_asset_preview_requested"));
	SetStatus(FText::Format(LOCTEXT("StatusTripoWorkspacePreviewAsset", "Opening Tripo preview window for {0}"), FText::FromString(AssetReference)), OkStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleToolDetailsClicked(FToolCallView ToolCall)
{
	ShowToolDetailDrawer(ToolCall);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleRepairToolClicked(FToolCallView ToolCall)
{
	const FString RepairPrompt = FString::Printf(
		TEXT("Run the repair_tools chain for failed MCP tool `%s`. Status: %s. Result: %s. Details: %s"),
		*ToolCall.ToolName,
		*ToolCall.Status,
		*ToolCall.ResultSummary,
		*ToolCall.DetailJson
	);
	SendHumanMessage(RepairPrompt);
	AddMessage(FChatMessage{MakeLocalMessageId(), TEXT("human"), RepairPrompt, MakeCurrentTimestamp()});
	SetStatus(LOCTEXT("StatusRepairQueued", "Repair request queued"), PendingStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleContextChipClicked(FString Reference)
{
	if (Reference == TEXT("level"))
	{
		Reference = GetOpenLevelReference();
	}
	else if (Reference == TEXT("actor"))
	{
		Reference = GetSelectedActorReference();
	}
	else if (Reference == TEXT("dirty"))
	{
		Reference = GetDirtyAssetsReference();
	}
	else if (Reference == TEXT("compile"))
	{
		Reference = GetLastCompileReference();
	}
	else if (Reference == TEXT("server"))
	{
		Reference = GetServerReference();
	}

	InsertComposerText(Reference);
	SetStatus(FText::Format(LOCTEXT("StatusContextInserted", "Inserted {0}"), FText::FromString(Reference)), OkStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::OnDragOver(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent)
{
	const TSharedPtr<FDragDropOperation> Operation = DragDropEvent.GetOperation();
	if (!Operation.IsValid())
	{
		return FReply::Unhandled();
	}

	return (Operation->IsOfType<FAssetDragDropOp>() ||
		Operation->IsOfType<FActorDragDropOp>() ||
		Operation->IsOfType<FExternalDragOperation>() ||
		Operation->IsExternalOperation()) ? FReply::Handled() : FReply::Unhandled();
}

FReply SMCPChatPanel::OnDrop(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent)
{
	const TSharedPtr<FDragDropOperation> Operation = DragDropEvent.GetOperation();
	if (!Operation.IsValid())
	{
		return FReply::Unhandled();
	}

	const FString DropReference = BuildDropReference(Operation);
	if (DropReference.IsEmpty())
	{
		SetStatus(LOCTEXT("StatusUnsupportedDrop", "Unsupported drop"), ErrorStatusColor);
		return FReply::Handled();
	}

	InsertComposerText(DropReference);
	SetStatus(FText::Format(LOCTEXT("StatusDropInserted", "Inserted dropped reference: {0}"), FText::FromString(DropReference)), OkStatusColor);
	return FReply::Handled();
}

bool SMCPChatPanel::HandlePollTick(float DeltaTime)
{
	PollAgentMessages();
	return true;
}

void SMCPChatPanel::LoadHistory()
{
	const FString Path = TEXT("/chat/history?limit=50") + BuildSessionQueryParam();
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(Path), TEXT("GET"));
	const double RequestStartSeconds = FPlatformTime::Seconds();
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
		RecordServerLatency(RequestStartSeconds);

		if (!bWasSuccessful || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
		{
			SetStatus(LOCTEXT("StatusOffline", "MCP server offline"), ErrorStatusColor);
			return;
		}

		TArray<FChatMessage> LoadedMessages;
		if (ParseMessagesResponse(Response->GetContentAsString(), LoadedMessages))
		{
			Messages = LoadedMessages;
			UpdateLastAgentTimestamp(LoadedMessages);
			RebuildMessageList();
			if (bCommandPaletteVisible)
			{
				RefreshCommandPaletteItems();
				RebuildCommandPaletteResults();
			}
			SetStatus(FText::Format(LOCTEXT("StatusConnectedSession", "Connected: {0}"), FText::FromString(CurrentSessionName)), OkStatusColor);
		}
		else
		{
			SetStatus(LOCTEXT("StatusHistoryError", "History parse failed"), ErrorStatusColor);
		}
	});
	Request->ProcessRequest();
}

void SMCPChatPanel::PollAgentMessages()
{
	if (bAgentPollInFlight)
	{
		return;
	}

	FString Path = TEXT("/chat/poll?sender=agent") + BuildSessionQueryParam();
	if (!LastAgentPollTimestamp.IsEmpty())
	{
		Path += TEXT("&since=");
		Path += FGenericPlatformHttp::UrlEncode(LastAgentPollTimestamp);
	}

	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(Path), TEXT("GET"));
	const double RequestStartSeconds = FPlatformTime::Seconds();
	bAgentPollInFlight = true;
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		bAgentPollInFlight = false;
		ActiveRequests.Remove(RequestPtr);
		RecordServerLatency(RequestStartSeconds);

		if (!bWasSuccessful || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
		{
			SetStatus(LOCTEXT("StatusPollOffline", "MCP server offline"), ErrorStatusColor);
			return;
		}

		const FString ResponseBody = Response->GetContentAsString();
		TArray<FChatMessage> NewMessages;
		if (!ParseMessagesResponse(ResponseBody, NewMessages))
		{
			TArray<FString> Lines;
			ResponseBody.ParseIntoArrayLines(Lines, false);
			bool bAppliedStreamDelta = false;
			for (const FString& Line : Lines)
			{
				bAppliedStreamDelta |= ApplySseLine(Line);
			}

			if (!bAppliedStreamDelta)
			{
				SetStatus(LOCTEXT("StatusPollParseError", "Poll parse failed"), ErrorStatusColor);
				return;
			}

			SetStatus(LOCTEXT("StatusStreamConnected", "Streaming"), OkStatusColor);
			return;
		}

		for (const FChatMessage& ChatMessage : NewMessages)
		{
			AddMessage(ChatMessage);
		}
		UpdateLastAgentTimestamp(NewMessages);
		SetStatus(LOCTEXT("StatusPollConnected", "Connected"), OkStatusColor);
	});
	if (!Request->ProcessRequest())
	{
		bAgentPollInFlight = false;
		ActiveRequests.Remove(Request);
	}
}

void SMCPChatPanel::SendHumanMessage(const FString& Message)
{
	const FString Path = TEXT("/chat/send?session=") + FGenericPlatformHttp::UrlEncode(CurrentSessionName);
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(Path), TEXT("POST"));
	const double RequestStartSeconds = FPlatformTime::Seconds();

	const TSharedPtr<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("sender"), TEXT("human"));
	Payload->SetStringField(TEXT("message"), Message);
	Payload->SetStringField(TEXT("timestamp"), MakeCurrentTimestamp());
	Payload->SetStringField(TEXT("session"), CurrentSessionName);
	Payload->SetObjectField(TEXT("context"), BuildEditorContext());

	FString Body;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
	FJsonSerializer::Serialize(Payload.ToSharedRef(), Writer);
	Request->SetContentAsString(Body);

	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
		RecordServerLatency(RequestStartSeconds);

		if (!bWasSuccessful || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
		{
			SetStatus(LOCTEXT("StatusSendFailed", "Send failed"), ErrorStatusColor);
			return;
		}

		SetStatus(LOCTEXT("StatusSendOk", "Connected"), OkStatusColor);
		RecordTelemetryEvent(TEXT("message_sent"));
		LoadSessions();
	});
	Request->ProcessRequest();
}

void SMCPChatPanel::ClearHistoryOnServer()
{
	const FString Path = TEXT("/chat/clear?session=") + FGenericPlatformHttp::UrlEncode(CurrentSessionName);
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(Path), TEXT("POST"));
	const double RequestStartSeconds = FPlatformTime::Seconds();
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
		RecordServerLatency(RequestStartSeconds);
		const bool bClearSucceeded = bWasSuccessful && Response.IsValid() && Response->GetResponseCode() >= 200 && Response->GetResponseCode() < 300;
		SetStatus(
			bClearSucceeded
				? LOCTEXT("StatusClearOk", "History cleared")
				: LOCTEXT("StatusClearFailed", "Clear failed"),
			bClearSucceeded ? OkStatusColor : ErrorStatusColor
		);
	});
	Request->ProcessRequest();
}

void SMCPChatPanel::LoadToolPalette()
{
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(TEXT("/tools/list?domain=all")), TEXT("GET"));
	const double RequestStartSeconds = FPlatformTime::Seconds();
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
		RecordServerLatency(RequestStartSeconds);

		if (!bWasSuccessful || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
		{
			SetStatus(LOCTEXT("StatusToolPaletteOffline", "Tool palette unavailable"), ErrorStatusColor);
			return;
		}

		TMap<FString, TArray<FToolPaletteEntry>> ParsedTools;
		if (!ParseToolPaletteResponse(Response->GetContentAsString(), ParsedTools))
		{
			SetStatus(LOCTEXT("StatusToolPaletteParseFailed", "Tool palette parse failed"), ErrorStatusColor);
			return;
		}

		ToolPaletteByCategory = MoveTemp(ParsedTools);
		bToolPaletteLoaded = true;
		ToolCount = 0;
		for (const TPair<FString, TArray<FToolPaletteEntry>>& CategoryTools : ToolPaletteByCategory)
		{
			ToolCount += CategoryTools.Value.Num();
		}
		KbDocCount = CoreCommandPaletteKbDocCount;
		RebuildToolPaletteList();
		if (bCommandPaletteVisible)
		{
			RefreshCommandPaletteItems();
			RebuildCommandPaletteResults();
		}
		SetStatus(LOCTEXT("StatusToolPaletteLoaded", "Tool palette loaded"), OkStatusColor);
	});
	Request->ProcessRequest();
}

void SMCPChatPanel::LoadSessions()
{
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(TEXT("/chat/sessions")), TEXT("GET"));
	const double RequestStartSeconds = FPlatformTime::Seconds();
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
		RecordServerLatency(RequestStartSeconds);
		if (!bWasSuccessful || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
		{
			SetStatus(LOCTEXT("StatusSessionsUnavailable", "Sessions unavailable"), ErrorStatusColor);
			return;
		}

		TArray<FChatSessionEntry> ParsedSessions;
		FString ParsedLastSession;
		if (!ParseSessionsResponse(Response->GetContentAsString(), ParsedSessions, ParsedLastSession))
		{
			SetStatus(LOCTEXT("StatusSessionsParseFailed", "Session list parse failed"), ErrorStatusColor);
			return;
		}

		ChatSessions = MoveTemp(ParsedSessions);
		LastSessionName = ParsedLastSession.IsEmpty() ? CurrentSessionName : ParsedLastSession;
		if (CurrentSessionName.IsEmpty())
		{
			CurrentSessionName = LastSessionName;
		}
		RebuildSessionList();
	});
	Request->ProcessRequest();
}

void SMCPChatPanel::LoadCockpitOverview()
{
	const FString Path = TEXT("/chat/cockpit/overview?limit=20") + BuildSessionQueryParam();
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(Path), TEXT("GET"));
	const double RequestStartSeconds = FPlatformTime::Seconds();
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
		RecordServerLatency(RequestStartSeconds);
		if (!bWasSuccessful || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
		{
			CockpitOverview = FCockpitOverview();
			CockpitOverview.Session = CurrentSessionName;
			CockpitOverview.BlockersSummary = TEXT("Cockpit unavailable");
			CockpitOverview.QueueSummary = TEXT("Queue unknown");
			CockpitOverview.QueueActionsSummary = TEXT("Actions unknown");
			CockpitOverview.EvidenceSummary = TEXT("Evidence unknown");
			CockpitOverview.EvidenceTimelineSummary = TEXT("Timeline unknown");
			CockpitOverview.SuggestedAction = TEXT("Start the MCP chat server, then refresh.");
			SetStatus(LOCTEXT("StatusCockpitUnavailable", "Cockpit overview unavailable"), ErrorStatusColor);
			return;
		}

		FCockpitOverview ParsedOverview;
		if (!ParseCockpitOverviewResponse(Response->GetContentAsString(), ParsedOverview))
		{
			CockpitOverview = FCockpitOverview();
			CockpitOverview.Session = CurrentSessionName;
			CockpitOverview.BlockersSummary = TEXT("Cockpit parse failed");
			CockpitOverview.QueueSummary = TEXT("Queue unknown");
			CockpitOverview.QueueActionsSummary = TEXT("Actions unknown");
			CockpitOverview.EvidenceSummary = TEXT("Evidence unknown");
			CockpitOverview.EvidenceTimelineSummary = TEXT("Timeline unknown");
			CockpitOverview.SuggestedAction = TEXT("Check the MCP server response shape.");
			SetStatus(LOCTEXT("StatusCockpitParseFailed", "Cockpit overview parse failed"), ErrorStatusColor);
			return;
		}

		CockpitOverview = MoveTemp(ParsedOverview);
		SetStatus(LOCTEXT("StatusCockpitLoaded", "Cockpit overview loaded"), CockpitOverview.bBlocked ? PendingStatusColor : OkStatusColor);
	});
	Request->ProcessRequest();
}

void SMCPChatPanel::SendSessionAction(const FString& Path, const TSharedPtr<FJsonObject>& Payload, const FText& StatusOnSuccess)
{
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(Path), TEXT("POST"));
	const double RequestStartSeconds = FPlatformTime::Seconds();
	FString Body;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
	FJsonSerializer::Serialize(Payload.ToSharedRef(), Writer);
	Request->SetContentAsString(Body);

	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, StatusOnSuccess, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
		RecordServerLatency(RequestStartSeconds);
		if (!bWasSuccessful || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
		{
			SetStatus(LOCTEXT("StatusSessionActionFailed", "Session action failed"), ErrorStatusColor);
			return;
		}

		SetStatus(StatusOnSuccess, OkStatusColor);
		LoadSessions();
		LoadCockpitOverview();
	});
	Request->ProcessRequest();
}

void SMCPChatPanel::LoadLayoutSettings()
{
	KbDocCount = CoreCommandPaletteKbDocCount;
	if (!GConfig)
	{
		return;
	}

	GConfig->GetFloat(ChatPanelConfigSection, TEXT("SessionSidebarSize"), SessionSidebarSize, GEditorPerProjectIni);
	GConfig->GetFloat(ChatPanelConfigSection, TEXT("ToolPaletteSize"), ToolPaletteSize, GEditorPerProjectIni);
	GConfig->GetFloat(ChatPanelConfigSection, TEXT("ChatWorkspaceSize"), ChatWorkspaceSize, GEditorPerProjectIni);
	GConfig->GetFloat(ChatPanelConfigSection, TEXT("ConversationSize"), ConversationSize, GEditorPerProjectIni);
	GConfig->GetFloat(ChatPanelConfigSection, TEXT("ComposerSize"), ComposerSize, GEditorPerProjectIni);
	GConfig->GetBool(ChatPanelConfigSection, TEXT("TelemetryEnabled"), bTelemetryEnabled, GEditorPerProjectIni);
	GConfig->GetBool(ChatPanelConfigSection, TEXT("OnboardingCompleted"), bOnboardingCompleted, GEditorPerProjectIni);

	SessionSidebarSize = FMath::Clamp(SessionSidebarSize, 0.10f, 0.45f);
	ToolPaletteSize = FMath::Clamp(ToolPaletteSize, 0.0f, 0.45f);
	ChatWorkspaceSize = FMath::Clamp(ChatWorkspaceSize, 0.35f, 0.85f);
	ConversationSize = FMath::Clamp(ConversationSize, 0.35f, 0.90f);
	ComposerSize = FMath::Clamp(ComposerSize, 0.10f, 0.65f);
	bOnboardingVisible = !bOnboardingCompleted;
	OnboardingStepIndex = FMath::Clamp(OnboardingStepIndex, 0, 3);
}

void SMCPChatPanel::SaveLayoutSettings() const
{
	if (!GConfig)
	{
		return;
	}

	GConfig->SetFloat(ChatPanelConfigSection, TEXT("SessionSidebarSize"), SessionSidebarSize, GEditorPerProjectIni);
	GConfig->SetFloat(ChatPanelConfigSection, TEXT("ToolPaletteSize"), ToolPaletteSize, GEditorPerProjectIni);
	GConfig->SetFloat(ChatPanelConfigSection, TEXT("ChatWorkspaceSize"), ChatWorkspaceSize, GEditorPerProjectIni);
	GConfig->SetFloat(ChatPanelConfigSection, TEXT("ConversationSize"), ConversationSize, GEditorPerProjectIni);
	GConfig->SetFloat(ChatPanelConfigSection, TEXT("ComposerSize"), ComposerSize, GEditorPerProjectIni);
	GConfig->SetBool(ChatPanelConfigSection, TEXT("TelemetryEnabled"), bTelemetryEnabled, GEditorPerProjectIni);
	GConfig->SetBool(ChatPanelConfigSection, TEXT("OnboardingCompleted"), bOnboardingCompleted, GEditorPerProjectIni);
	GConfig->Flush(false, GEditorPerProjectIni);
}

void SMCPChatPanel::RecordHorizontalSplitterResize(float Size, int32 SlotIndex)
{
	const float ClampedSize = FMath::Clamp(Size, 0.0f, 1.0f);
	if (SlotIndex == 0)
	{
		SessionSidebarSize = ClampedSize;
	}
	else if (SlotIndex == 1)
	{
		ToolPaletteSize = ClampedSize;
	}
	else if (SlotIndex == 2)
	{
		ChatWorkspaceSize = ClampedSize;
	}
	SaveLayoutSettings();
}

void SMCPChatPanel::RecordVerticalSplitterResize(float Size, int32 SlotIndex)
{
	const float ClampedSize = FMath::Clamp(Size, 0.0f, 1.0f);
	if (SlotIndex == 0)
	{
		ConversationSize = ClampedSize;
	}
	else if (SlotIndex == 1)
	{
		ComposerSize = ClampedSize;
	}
	SaveLayoutSettings();
}

void SMCPChatPanel::RecordServerLatency(double RequestStartSeconds)
{
	LastServerLatencyMs = FMath::Max(0, FMath::RoundToInt((FPlatformTime::Seconds() - RequestStartSeconds) * 1000.0));
	RecordTelemetryEvent(TEXT("server_response"));
}

void SMCPChatPanel::RecordTelemetryEvent(const FString& EventName)
{
	if (!bTelemetryEnabled)
	{
		return;
	}

	++TelemetryEventCount;
	const FString MetricsPath = GetMetricsFilePath();
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(MetricsPath), true);

	const FString JsonText = FString::Printf(
		TEXT("{\n  \"last_event\": \"%s\",\n  \"last_timestamp\": \"%s\",\n  \"event_count\": %d,\n  \"last_latency_ms\": %d,\n  \"tool_count\": %d,\n  \"kb_doc_count\": %d,\n  \"queue_depth\": %d\n}\n"),
		*EventName,
		*MakeCurrentTimestamp(),
		TelemetryEventCount,
		LastServerLatencyMs,
		ToolCount,
		KbDocCount,
		ActiveRequests.Num()
	);
	FFileHelper::SaveStringToFile(JsonText, *MetricsPath);
}

FString SMCPChatPanel::GetMetricsFilePath() const
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("MCPChat"), TEXT("metrics.json"));
}

void SMCPChatPanel::AddMessage(const FChatMessage& ChatMessage)
{
	FChatMessage MessageToAdd = ChatMessage;
	if (MessageToAdd.MessageId.IsEmpty())
	{
		MessageToAdd.MessageId = MakeLocalMessageId();
	}

	if (!MessageToAdd.MessageId.IsEmpty())
	{
		for (const FChatMessage& Existing : Messages)
		{
			if (Existing.MessageId == MessageToAdd.MessageId)
			{
				return;
			}
		}
	}

	Messages.Add(MessageToAdd);
	UpdateLastCompileStateFromMessage(MessageToAdd);
	if (bCommandPaletteVisible)
	{
		RefreshCommandPaletteItems();
		RebuildCommandPaletteResults();
	}

	if (!MessageScrollBox.IsValid())
	{
		return;
	}

	MessageScrollBox->AddSlot()
	.Padding(0.0f, 0.0f, 0.0f, 6.0f)
	[
		BuildMessageWidget(MessageToAdd)
	];

	MessageScrollBox->ScrollToEnd();
}

TSharedRef<SWidget> SMCPChatPanel::BuildMessageWidget(const FChatMessage& ChatMessage)
{
	const FSlateColor MessageColor = GetMessageColor(ChatMessage.Sender);
	const FText SenderLabel = GetSenderLabel(ChatMessage.Sender);

	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.BorderBackgroundColor(MessageColor)
		.Padding(8.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				[
					SNew(SBorder)
					.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
					.BorderBackgroundColor(FSlateColor(FLinearColor(0.02f, 0.02f, 0.025f, 0.6f)))
					.Padding(6.0f, 2.0f)
					[
						SNew(STextBlock)
						.Text(SenderLabel)
						.Font(FAppStyle::GetFontStyle("SmallFontBold"))
					]
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				.Padding(8.0f, 0.0f, 0.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(FText::FromString(ChatMessage.Timestamp))
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
				]

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SNew(SSpacer)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SHorizontalBox)

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(3.0f, 0.0f)
					[
						SNew(SButton)
						.Text(LOCTEXT("CopyMessage", "Copy"))
						.OnClicked(this, &SMCPChatPanel::HandleCopyClicked, ChatMessage.Message)
					]

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(3.0f, 0.0f)
					[
						SNew(SButton)
						.Text(LOCTEXT("RerunMessage", "Re-run"))
						.OnClicked(this, &SMCPChatPanel::HandleRerunClicked, ChatMessage.Message, ChatMessage.Sender)
					]

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(3.0f, 0.0f)
					[
						SNew(SButton)
						.Text(LOCTEXT("OpenLog", "Open Log"))
						.OnClicked(this, &SMCPChatPanel::HandleOpenLogClicked)
					]

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(3.0f, 0.0f)
					[
						SNew(SButton)
						.Text(LOCTEXT("RevealAsset", "Reveal Asset"))
						.OnClicked(this, &SMCPChatPanel::HandleRevealAssetClicked, ChatMessage.Message)
					]

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(3.0f, 0.0f)
					[
						SNew(SButton)
						.Text(LOCTEXT("PreviewInTripoWorkspace", "Tripo Preview"))
						.OnClicked(this, &SMCPChatPanel::HandleOpenTripoWorkspaceAssetClicked, ChatMessage.Message)
					]
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 6.0f, 0.0f, 0.0f)
			[
				BuildMarkdownMessageBody(ChatMessage)
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 6.0f, 0.0f, 0.0f)
			[
				BuildToolCallCards(ChatMessage)
			]
		];
}

void SMCPChatPanel::RebuildMessageList()
{
	if (!MessageScrollBox.IsValid())
	{
		return;
	}

	const TArray<FChatMessage> ExistingMessages = Messages;
	Messages.Reset();
	StreamingMessageTextBlocks.Reset();
	EvidenceImageBrushes.Reset();
	MessageScrollBox->ClearChildren();

	for (const FChatMessage& ChatMessage : ExistingMessages)
	{
		AddMessage(ChatMessage);
	}
}

TSharedRef<SWidget> SMCPChatPanel::BuildMarkdownMessageBody(const FChatMessage& ChatMessage)
{
	TSharedRef<SVerticalBox> BodyBox = SNew(SVerticalBox);
	AddMarkdownBlocks(ChatMessage.Message, ChatMessage.MessageId, BodyBox);
	return BodyBox;
}

TSharedRef<SWidget> SMCPChatPanel::BuildToolCallCards(const FChatMessage& ChatMessage)
{
	TArray<FToolCallView> ToolCalls;
	ExtractToolCallsFromMessage(ChatMessage, ToolCalls);

	TSharedRef<SVerticalBox> ToolCardsBox = SNew(SVerticalBox);
	for (const FToolCallView& ToolCall : ToolCalls)
	{
		ToolCardsBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 2.0f, 0.0f, 4.0f)
		[
			BuildToolCallCard(ToolCall)
		];
	}

	return ToolCardsBox;
}

TSharedRef<SWidget> SMCPChatPanel::BuildToolCallCard(const FToolCallView& ToolCall)
{
	const FSlateColor CardColor = ToolCall.bError ? ToolErrorColor : ToolCardColor;
	const FText HeaderText = FText::Format(
		LOCTEXT("ToolCardHeader", "{0}  |  {1}"),
		FText::FromString(ToolCall.ToolName),
		FText::FromString(ToolCall.Status.IsEmpty() ? TEXT("pending") : ToolCall.Status)
	);

	return SNew(SExpandableArea)
		.InitiallyCollapsed(false)
		.HeaderContent()
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
			.BorderBackgroundColor(CardColor)
			.Padding(6.0f)
			[
				SNew(STextBlock)
				.Text(HeaderText)
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			]
		]
		.BodyContent()
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
			.BorderBackgroundColor(CardColor)
			.Padding(8.0f)
			[
				SNew(SVerticalBox)

				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SNew(STextBlock)
					.Text(FText::Format(LOCTEXT("ToolArgsSummary", "Args: {0}"), FText::FromString(ToolCall.ArgsSummary)))
					.AutoWrapText(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 4.0f, 0.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(FText::Format(LOCTEXT("ToolResultSummary", "Result: {0}"), FText::FromString(ToolCall.ResultSummary)))
					.AutoWrapText(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 6.0f, 0.0f, 0.0f)
				[
					BuildTripoProgressPanel(ToolCall)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 6.0f, 0.0f, 0.0f)
				[
					BuildEvidencePanel(ToolCall)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 6.0f, 0.0f, 0.0f)
				[
					SNew(SHorizontalBox)

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(0.0f, 0.0f, 6.0f, 0.0f)
					[
						SNew(SButton)
						.Text(LOCTEXT("ToolDetails", "Details"))
						.OnClicked(this, &SMCPChatPanel::HandleToolDetailsClicked, ToolCall)
					]

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(0.0f, 0.0f, 6.0f, 0.0f)
					[
						SNew(SButton)
						.Text(LOCTEXT("ToolTripoPreview", "Tripo Preview"))
						.OnClicked(this, &SMCPChatPanel::HandleOpenTripoWorkspaceAssetClicked, ToolCall.DetailJson)
					]

					+ SHorizontalBox::Slot()
					.AutoWidth()
					.Padding(0.0f, 0.0f, 6.0f, 0.0f)
					[
						SNew(SButton)
						.Visibility(ToolCall.bError ? EVisibility::Visible : EVisibility::Collapsed)
						.Text(LOCTEXT("ToolRepair", "Repair"))
						.OnClicked(this, &SMCPChatPanel::HandleRepairToolClicked, ToolCall)
					]
				]
			]
	];
}

TSharedRef<SWidget> SMCPChatPanel::BuildTripoProgressPanel(const FToolCallView& ToolCall)
{
	if (!ToolCall.bHasProgress)
	{
		return SNew(SBox)
			.Visibility(EVisibility::Collapsed);
	}

	const int32 ProgressPercent = FMath::Clamp(FMath::RoundToInt(ToolCall.ProgressFraction * 100.0f), 0, 100);
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
		.Padding(6.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				SNew(STextBlock)
				.Text(FText::Format(LOCTEXT("TripoProgressLabel", "Tripo progress: {0}%"), FText::AsNumber(ProgressPercent)))
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SProgressBar)
				.Percent(TOptional<float>(ToolCall.ProgressFraction))
			]
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildEvidencePanel(const FToolCallView& ToolCall)
{
	if (ToolCall.ScreenshotPaths.IsEmpty() && ToolCall.LogSnippets.IsEmpty() && ToolCall.PieResults.IsEmpty())
	{
		return SNew(SBox)
			.Visibility(EVisibility::Collapsed);
	}

	TSharedRef<SVerticalBox> EvidenceBox = SNew(SVerticalBox);
	EvidenceBox->AddSlot()
	.AutoHeight()
	.Padding(0.0f, 0.0f, 0.0f, 4.0f)
	[
		SNew(STextBlock)
		.Text(LOCTEXT("InlineEvidencePanel", "Evidence"))
		.Font(FAppStyle::GetFontStyle("SmallFontBold"))
	];

	for (const FString& ScreenshotPath : ToolCall.ScreenshotPaths)
	{
		EvidenceBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 2.0f, 0.0f, 4.0f)
		[
			BuildScreenshotEvidenceWidget(ScreenshotPath)
		];
	}

	for (const FString& PieResult : ToolCall.PieResults)
	{
		EvidenceBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 2.0f, 0.0f, 4.0f)
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
			.Padding(6.0f)
			[
				SNew(STextBlock)
				.Text(FText::Format(LOCTEXT("InlinePieEvidence", "PIE: {0}"), FText::FromString(PieResult)))
				.AutoWrapText(true)
			]
		];
	}

	for (const FString& LogSnippet : ToolCall.LogSnippets)
	{
		EvidenceBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 2.0f, 0.0f, 4.0f)
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
			.BorderBackgroundColor(CodeBlockColor)
			.Padding(6.0f)
			[
				SNew(STextBlock)
				.Text(FText::Format(LOCTEXT("InlineLogEvidence", "Log: {0}"), FText::FromString(LogSnippet)))
				.Font(FAppStyle::GetFontStyle("Mono"))
				.AutoWrapText(true)
			]
		];
	}

	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.Padding(6.0f)
		[
			EvidenceBox
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildScreenshotEvidenceWidget(const FString& ScreenshotPath)
{
	FString NormalizedPath = ScreenshotPath;
	NormalizedPath.RemoveFromStart(TEXT("file://"));
	NormalizedPath.TrimStartAndEndInline();
	FPaths::NormalizeFilename(NormalizedPath);

	const FString Extension = FPaths::GetExtension(NormalizedPath).ToLower();
	const bool bLooksLikeImage = Extension == TEXT("png") || Extension == TEXT("jpg") || Extension == TEXT("jpeg") || Extension == TEXT("bmp");
	const bool bCanRenderInline = bLooksLikeImage && FPaths::FileExists(NormalizedPath);

	TSharedRef<SVerticalBox> ScreenshotBox = SNew(SVerticalBox);
	ScreenshotBox->AddSlot()
	.AutoHeight()
	.Padding(0.0f, 0.0f, 0.0f, 4.0f)
	[
		SNew(STextBlock)
		.Text(FText::Format(LOCTEXT("InlineScreenshotPath", "Screenshot: {0}"), FText::FromString(NormalizedPath)))
		.AutoWrapText(true)
	];

	if (bCanRenderInline)
	{
		const TSharedPtr<FSlateDynamicImageBrush> ScreenshotBrush = MakeShared<FSlateDynamicImageBrush>(
			FName(*NormalizedPath),
			FVector2D(320.0f, 180.0f)
		);
		EvidenceImageBrushes.Add(ScreenshotBrush);

		ScreenshotBox->AddSlot()
		.AutoHeight()
		[
			SNew(SBox)
			.HeightOverride(180.0f)
			[
				SNew(SImage)
				.Image(ScreenshotBrush.Get())
			]
		];
	}

	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
		.Padding(6.0f)
		[
			ScreenshotBox
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildSessionSidebar()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.Padding(8.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("SessionSidebarTitle", "Sessions"))
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("ContinueLastSession", "Continue Last"))
				.OnClicked(this, &SMCPChatPanel::HandleContinueLastSessionClicked)
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("NewSession", "New"))
				.OnClicked(this, &SMCPChatPanel::HandleNewSessionClicked)
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SWrapBox)

				+ SWrapBox::Slot()
				.Padding(0.0f, 0.0f, 4.0f, 4.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("RenameSession", "Rename"))
					.OnClicked(this, &SMCPChatPanel::HandleRenameSessionClicked)
				]

				+ SWrapBox::Slot()
				.Padding(0.0f, 0.0f, 4.0f, 4.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("PinSession", "Pin"))
					.OnClicked(this, &SMCPChatPanel::HandlePinSessionClicked)
				]

				+ SWrapBox::Slot()
				.Padding(0.0f, 0.0f, 4.0f, 4.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("DeleteSession", "Delete"))
					.OnClicked(this, &SMCPChatPanel::HandleDeleteSessionClicked)
				]

				+ SWrapBox::Slot()
				.Padding(0.0f, 0.0f, 4.0f, 4.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("ExportSession", "Export"))
					.OnClicked(this, &SMCPChatPanel::HandleExportSessionClicked)
				]
			]

			+ SVerticalBox::Slot()
			.FillHeight(1.0f)
			[
				SNew(SScrollBox)

				+ SScrollBox::Slot()
				[
					SAssignNew(SessionList, SVerticalBox)

					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(STextBlock)
						.Text(LOCTEXT("SessionsLoading", "Loading sessions..."))
						.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					]
				]
			]
		];
}

void SMCPChatPanel::RebuildSessionList()
{
	if (!SessionList.IsValid())
	{
		return;
	}

	SessionList->ClearChildren();
	if (ChatSessions.IsEmpty())
	{
		SessionList->AddSlot()
		.AutoHeight()
		[
			SNew(STextBlock)
			.Text(LOCTEXT("SessionsEmpty", "No sessions"))
			.ColorAndOpacity(FSlateColor::UseSubduedForeground())
		];
		return;
	}

	for (const FChatSessionEntry& Session : ChatSessions)
	{
		const FString Prefix = Session.bPinned ? TEXT("* ") : TEXT("");
		const FString Suffix = Session.Name == CurrentSessionName ? TEXT("  <") : TEXT("");
		const FString Label = FString::Printf(TEXT("%s%s (%d)%s"), *Prefix, *Session.Name, Session.MessageCount, *Suffix);
		SessionList->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 0.0f, 0.0f, 4.0f)
		[
			SNew(SButton)
			.Text(FText::FromString(Label))
			.ToolTipText(FText::FromString(Session.UpdatedAt))
			.OnClicked(this, &SMCPChatPanel::HandleSessionClicked, Session)
		];
	}
}

TSharedRef<SWidget> SMCPChatPanel::BuildToolPalette()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.Padding(8.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("ToolPaletteTitle", "Tool Palette"))
					.Font(FAppStyle::GetFontStyle("SmallFontBold"))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.Text(LOCTEXT("ToolPaletteRefresh", "Refresh"))
					.OnClicked(this, &SMCPChatPanel::HandleRefreshToolPaletteClicked)
				]
			]

			+ SVerticalBox::Slot()
			.FillHeight(1.0f)
			[
				SNew(SScrollBox)

				+ SScrollBox::Slot()
				[
					SAssignNew(ToolPaletteList, SVerticalBox)

					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(STextBlock)
						.Text(LOCTEXT("ToolPaletteLoading", "Loading tools..."))
						.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					]
				]
			]
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildToolPaletteCategory(const FString& Category, const TArray<FToolPaletteEntry>& Tools)
{
	TSharedRef<SVerticalBox> ToolButtons = SNew(SVerticalBox);
	for (const FToolPaletteEntry& Tool : Tools)
	{
		ToolButtons->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 0.0f, 0.0f, 4.0f)
		[
			SNew(SButton)
			.Text(FText::FromString(Tool.Name))
			.ToolTipText(FText::FromString(Tool.Description))
			.OnClicked(this, &SMCPChatPanel::HandleToolPaletteToolClicked, Tool)
		];
	}

	return SNew(SExpandableArea)
		.InitiallyCollapsed(true)
		.HeaderContent()
		[
			SNew(STextBlock)
			.Text(FText::Format(LOCTEXT("ToolPaletteCategoryHeader", "{0} ({1})"), FText::FromString(Category), FText::AsNumber(Tools.Num())))
			.Font(FAppStyle::GetFontStyle("SmallFontBold"))
		]
		.BodyContent()
		[
			ToolButtons
		];
}

void SMCPChatPanel::RebuildToolPaletteList()
{
	if (!ToolPaletteList.IsValid())
	{
		return;
	}

	ToolPaletteList->ClearChildren();
	if (!bToolPaletteLoaded || ToolPaletteByCategory.IsEmpty())
	{
		ToolPaletteList->AddSlot()
		.AutoHeight()
		[
			SNew(STextBlock)
			.Text(LOCTEXT("ToolPaletteEmpty", "No tools loaded"))
			.ColorAndOpacity(FSlateColor::UseSubduedForeground())
		];
		return;
	}

	TArray<FString> Categories;
	ToolPaletteByCategory.GetKeys(Categories);
	Categories.Sort();
	for (const FString& Category : Categories)
	{
		if (const TArray<FToolPaletteEntry>* Tools = ToolPaletteByCategory.Find(Category))
		{
			ToolPaletteList->AddSlot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				BuildToolPaletteCategory(Category, *Tools)
			];
		}
	}
}

TSharedRef<SWidget> SMCPChatPanel::BuildCockpitOverviewBar()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.Padding(6.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("CockpitOverviewTitle", "IDE Cockpit"))
					.Font(FAppStyle::GetFontStyle("SmallFontBold"))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				.Padding(0.0f, 0.0f, 4.0f, 0.0f)
				[
					SNew(SButton)
					.Text(this, &SMCPChatPanel::GetCockpitWorkflowActionsText)
					.ToolTipText(this, &SMCPChatPanel::GetCockpitWorkflowActionsTooltip)
					.OnClicked(this, &SMCPChatPanel::HandleOpenWorkflowActionsClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				[
					SNew(SButton)
					.Text(LOCTEXT("CockpitOverviewRefresh", "Refresh"))
					.OnClicked(this, &SMCPChatPanel::HandleRefreshCockpitClicked)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 4.0f, 0.0f, 0.0f)
			[
				SNew(SVerticalBox)

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 0.0f, 0.0f, 2.0f)
				[
					SNew(STextBlock)
					.Text(this, &SMCPChatPanel::GetCockpitHudSummaryText)
					.ColorAndOpacity(FSlateColor::UseForeground())
					.AutoWrapText(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 0.0f, 0.0f, 2.0f)
				[
					SNew(STextBlock)
					.Text_Lambda([this]()
					{
						return FText::Format(
							LOCTEXT("CockpitOverviewLineOne", "{0} | {1}"),
							GetCockpitSessionText(),
							GetCockpitBlockersText()
						);
					})
					.ColorAndOpacity(FSlateColor::UseForeground())
					.AutoWrapText(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 0.0f, 0.0f, 2.0f)
				[
					SNew(STextBlock)
					.Text_Lambda([this]()
					{
						return FText::Format(
							LOCTEXT("CockpitOverviewLineTwo", "{0} | {1} | {2}"),
							GetCockpitQueueText(),
							GetCockpitEvidenceText(),
							GetCockpitActionText()
						);
					})
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 0.0f, 0.0f, 2.0f)
				[
					SNew(STextBlock)
					.Text(this, &SMCPChatPanel::GetCockpitQueueActionsText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SNew(STextBlock)
					.Text(this, &SMCPChatPanel::GetCockpitEvidenceTimelineText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				.Padding(0.0f, 2.0f, 0.0f, 0.0f)
				[
					SNew(STextBlock)
					.Text(this, &SMCPChatPanel::GetCockpitRecoveryText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]
			]
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildCommandPalette()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.Padding(8.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("CommandPaletteTitle", "Command Palette"))
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(CommandPaletteInput, SEditableTextBox)
				.HintText(LOCTEXT("CommandPaletteHint", "Search tools, KB docs, assets, prompts, and slash commands"))
				.OnTextChanged(this, &SMCPChatPanel::HandleCommandPaletteTextChanged)
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SScrollBox)
				.Orientation(Orient_Vertical)

				+ SScrollBox::Slot()
				[
					SAssignNew(CommandPaletteResults, SVerticalBox)

					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(STextBlock)
						.Text(LOCTEXT("CommandPaletteEmpty", "Open with Ctrl+K"))
						.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					]
				]
			]
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildGenerateAssetDialog()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.Padding(8.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("GenerateAssetDialogTitle", "Generate Asset Workspace"))
					.Font(FAppStyle::GetFontStyle("SmallFontBold"))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(this, &SMCPChatPanel::GetGenerativeAuthStatusText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(0.38f)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SAssignNew(GenerateAssetModeInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerateAssetModeHint", "text_to_model | image_to_model | multiview_to_model | texture_paint"))
					.Text(FText::FromString(GenerateAssetMode))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(0.62f)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("GenerateAssetSmartMeshSummary", "Smart Mesh on for game-ready topology | text, image, multiview, texture paint"))
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(GenerateAssetPromptInput, SEditableTextBox)
				.HintText(LOCTEXT("GenerateAssetPromptHint", "Prompt for Tripo generation or texture direction"))
				.Text(FText::FromString(GenerateAssetPrompt))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(0.5f)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SAssignNew(GenerateAssetNameInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerateAssetNameHint", "Unreal asset name, for example SM_SlimeEnemy"))
					.Text(FText::FromString(GenerateAssetName))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(0.5f)
				[
					SNew(STextBlock)
					.Text(FText::Format(LOCTEXT("GenerateAssetSettingsSummary", "Model {0} | Texture {1} | Folder {2}"), FText::FromString(GenerativeModelVersion), FText::FromString(GenerativeTextureQuality), FText::FromString(GenerativeOutputFolder)))
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(0.5f)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SAssignNew(GenerateAssetReferenceImagesInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerateAssetReferenceImagesHint", "Reference image path/URL, or 2-4 ordered multiview entries separated by ;"))
					.Text(FText::FromString(GenerateAssetReferenceImages))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(0.5f)
				[
					SAssignNew(GenerateAssetExistingTaskIdInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerateAssetExistingTaskHint", "Existing Tripo model task id for texture paint"))
					.Text(FText::FromString(GenerateAssetExistingTaskId))
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(GenerateAssetTexturePromptInput, SEditableTextBox)
				.HintText(LOCTEXT("GenerateAssetTexturePromptHint", "Texture/paint prompt, for example worn brass edge highlights"))
				.Text(FText::FromString(GenerateAssetTexturePrompt))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
				.Padding(6.0f)
				[
					SNew(SVerticalBox)

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 0.0f, 0.0f, 4.0f)
					[
						SNew(STextBlock)
						.Text(LOCTEXT("GenerateAssetPaintControlsTitle", "Texture/Paint Controls"))
						.Font(FAppStyle::GetFontStyle("SmallFontBold"))
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(SHorizontalBox)

						+ SHorizontalBox::Slot()
						.FillWidth(0.28f)
						.Padding(0.0f, 0.0f, 6.0f, 0.0f)
						[
							SAssignNew(GenerateAssetPaintViewLabelInput, SEditableTextBox)
							.HintText(LOCTEXT("GenerateAssetPaintViewHint", "view label"))
							.Text(FText::FromString(GenerateAssetPaintViewLabel))
						]

						+ SHorizontalBox::Slot()
						.FillWidth(0.20f)
						.Padding(0.0f, 0.0f, 6.0f, 0.0f)
						[
							SNew(SVerticalBox)

							+ SVerticalBox::Slot()
							.AutoHeight()
							[
								SNew(STextBlock)
								.Text(LOCTEXT("GenerateAssetBrushStrengthLabel", "Strength"))
								.ColorAndOpacity(FSlateColor::UseSubduedForeground())
							]

							+ SVerticalBox::Slot()
							.AutoHeight()
							[
								SNew(SSpinBox<float>)
								.MinValue(0.0f)
								.MaxValue(1.0f)
								.MinSliderValue(0.0f)
								.MaxSliderValue(1.0f)
								.Delta(0.05f)
								.Value(GenerateAssetPaintBrushStrength)
								.OnValueChanged_Lambda([this](float NewValue)
								{
									GenerateAssetPaintBrushStrength = FMath::Clamp(NewValue, 0.0f, 1.0f);
								})
							]
						]

						+ SHorizontalBox::Slot()
						.FillWidth(0.20f)
						.Padding(0.0f, 0.0f, 6.0f, 0.0f)
						[
							SNew(SVerticalBox)

							+ SVerticalBox::Slot()
							.AutoHeight()
							[
								SNew(STextBlock)
								.Text(LOCTEXT("GenerateAssetBlendLabel", "Blend"))
								.ColorAndOpacity(FSlateColor::UseSubduedForeground())
							]

							+ SVerticalBox::Slot()
							.AutoHeight()
							[
								SNew(SSpinBox<float>)
								.MinValue(0.0f)
								.MaxValue(1.0f)
								.MinSliderValue(0.0f)
								.MaxSliderValue(1.0f)
								.Delta(0.05f)
								.Value(GenerateAssetPaintBlend)
								.OnValueChanged_Lambda([this](float NewValue)
								{
									GenerateAssetPaintBlend = FMath::Clamp(NewValue, 0.0f, 1.0f);
								})
							]
						]

						+ SHorizontalBox::Slot()
						.FillWidth(0.20f)
						.Padding(0.0f, 0.0f, 6.0f, 0.0f)
						[
							SNew(SVerticalBox)

							+ SVerticalBox::Slot()
							.AutoHeight()
							[
								SNew(STextBlock)
								.Text(LOCTEXT("GenerateAssetBrushRadiusLabel", "Radius"))
								.ColorAndOpacity(FSlateColor::UseSubduedForeground())
							]

							+ SVerticalBox::Slot()
							.AutoHeight()
							[
								SNew(SSpinBox<float>)
								.MinValue(0.01f)
								.MaxValue(1.0f)
								.MinSliderValue(0.01f)
								.MaxSliderValue(1.0f)
								.Delta(0.05f)
								.Value(GenerateAssetPaintBrushRadius)
								.OnValueChanged_Lambda([this](float NewValue)
								{
									GenerateAssetPaintBrushRadius = FMath::Clamp(NewValue, 0.01f, 1.0f);
								})
							]
						]

						+ SHorizontalBox::Slot()
						.FillWidth(0.12f)
						.VAlign(VAlign_Center)
						[
							SNew(SCheckBox)
							.IsChecked_Lambda([this]()
							{
								return bGenerateAssetUploadPaintSnapshot ? ECheckBoxState::Checked : ECheckBoxState::Unchecked;
							})
							.OnCheckStateChanged_Lambda([this](ECheckBoxState NewState)
							{
								bGenerateAssetUploadPaintSnapshot = (NewState == ECheckBoxState::Checked);
							})
							[
								SNew(STextBlock)
								.Text(LOCTEXT("GenerateAssetUploadSnapshotLabel", "Upload view"))
								.ColorAndOpacity(FSlateColor::UseSubduedForeground())
							]
						]
					]
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
				.Padding(6.0f)
				[
					SNew(STextBlock)
					.Text(this, &SMCPChatPanel::GetGenerateAssetPreviewText)
					.AutoWrapText(true)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("InsertGenerateAssetToolCall", "Insert Tool Call"))
					.OnClicked(this, &SMCPChatPanel::HandleInsertGenerateAssetToolCallClicked)
				]

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(this, &SMCPChatPanel::GetGenerativeBudgetText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]
			]
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildGenerativeSettingsPanel()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.Padding(8.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(LOCTEXT("GenerativeSettingsTitle", "Generate Asset Settings"))
					.Font(FAppStyle::GetFontStyle("SmallFontBold"))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.VAlign(VAlign_Center)
				[
					SNew(STextBlock)
					.Text(this, &SMCPChatPanel::GetGenerativeAuthStatusText)
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(STextBlock)
				.Text(FText::Format(LOCTEXT("GenerativeSettingsFiles", "Settings: {0} | Secrets: {1}"), FText::FromString(GetGenerativeSettingsFilePath()), FText::FromString(GetGenerativeSecretsFilePath())))
				.ColorAndOpacity(FSlateColor::UseSubduedForeground())
				.AutoWrapText(true)
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(STextBlock)
				.Text(this, &SMCPChatPanel::GetGenerativeApiWalletText)
				.ColorAndOpacity(FSlateColor::UseSubduedForeground())
				.AutoWrapText(true)
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SAssignNew(GenerativeApiKeyInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerativeApiKeyHint", "TRIPO_API_KEY for mesh generation"))
					.Text(FText::FromString(GenerativeApiKey))
					.IsPassword(true)
				]

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SAssignNew(GenerativeUthanaApiKeyInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerativeUthanaApiKeyHint", "UTHANA_API_KEY for animation generation"))
					.Text(FText::FromString(GenerativeUthanaApiKey))
					.IsPassword(true)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SAssignNew(GenerativeModelVersionInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerativeModelVersionHint", "default model_version"))
					.Text(FText::FromString(GenerativeModelVersion))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SAssignNew(GenerativeTextureQualityInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerativeTextureQualityHint", "default texture_quality"))
					.Text(FText::FromString(GenerativeTextureQuality))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(1.0f)
				[
					SAssignNew(GenerativeOutputFolderInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerativeOutputFolderHint", "/Game/Generated"))
					.Text(FText::FromString(GenerativeOutputFolder))
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.FillWidth(0.55f)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SAssignNew(GenerativeCreditBudgetInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerativeCreditBudgetHint", "per-session credit budget"))
					.Text(FText::AsNumber(GenerativeSessionCreditBudget))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(0.45f)
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SAssignNew(GenerativePendingSpendInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerativePendingSpendHint", "credits to confirm"))
					.Text(FText::AsNumber(GenerativePendingSpendCredits))
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("ConfirmGenerativeSpend", "Confirm Spend"))
					.OnClicked(this, &SMCPChatPanel::HandleConfirmGenerativeSpendClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("RefreshGenerativeBalance", "Refresh API Balance"))
					.OnClicked(this, &SMCPChatPanel::HandleRefreshGenerativeBalanceClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.Text(LOCTEXT("SaveGenerativeSettings", "Save"))
					.OnClicked(this, &SMCPChatPanel::HandleSaveGenerativeSettingsClicked)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(STextBlock)
				.Text(this, &SMCPChatPanel::GetGenerativeBudgetText)
				.ColorAndOpacity(FSlateColor::UseSubduedForeground())
				.AutoWrapText(true)
			]
		];
}

void SMCPChatPanel::RefreshCommandPaletteItems()
{
	CommandPaletteItems.Reset();

	AddCommandPaletteItem(TEXT("/help"), TEXT("Slash command"), TEXT("/help"), TEXT("slash"));
	AddCommandPaletteItem(TEXT("/clear"), TEXT("Slash command"), TEXT("/clear"), TEXT("slash"));
	AddCommandPaletteItem(TEXT("/undo"), TEXT("Slash command"), TEXT("/undo"), TEXT("slash"));
	AddCommandPaletteItem(
		TEXT("/repair"),
		TEXT("Slash command"),
		TEXT("Run the repair_tools chain for the most recent failed MCP action and explain the fix."),
		TEXT("slash")
	);
	AddCommandPaletteItem(
		TEXT("Generate Asset quick action"),
		TEXT("Open the Tripo generate-asset workspace"),
		TEXT("Open Generate Asset Workspace and insert a Smart Mesh Tripo request using text, image, multiview, or texture-paint mode."),
		TEXT("generative")
	);
	AddCommandPaletteItem(
		TEXT("Start IDE Companion Session"),
		TEXT("Plan a full asset, gameplay, and verification session"),
		TEXT("Use MCP tool `skill_compile_ide_companion_session` to plan the full Unreal IDE companion workflow before spending credits or mutating the editor.\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.start_companion_session.target_start_context` first, then use its session name, readiness state, existing ledger state, queue count, generated asset count, and stop policy.\n")
		TEXT("Parameters:\n")
		TEXT("- project_brief: \"single-developer playable slice with generated assets and one guided gameplay mechanic\"\n")
		TEXT("- mechanic_brief: \"enemy AI patrol that chases the player and updates an objective HUD\"\n")
		TEXT("- content_path: \"/Game/Generated/PlayableSlice\"\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- include_generated_assets: true\n")
		TEXT("Return the `unreal_mcp_ide_companion_session_plan.v1` plan, then summarize phases, gates, generated asset prompts, gameplay mechanic hooks, fallback paths, and the next MCP tool sequence. Run `gen_compile_ide_companion_readiness` before any paid Tripo task or editor mutation."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Update IDE Companion Status"),
		TEXT("Summarize phase progress, evidence, blockers, and next action"),
		TEXT("Use MCP tool `skill_compile_ide_companion_status` with the latest session plan, readiness report, completed phase names, and evidence map.\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.refresh_companion_status.target_status_context` first, then use its ledger path, session-plan state, readiness state, blocker count, evidence count, and next phase/tool.\n")
		TEXT("Parameters:\n")
		TEXT("- session_plan: <paste the `unreal_mcp_ide_companion_session_plan.v1` plan>\n")
		TEXT("- readiness_report: <paste the latest `gen_compile_ide_companion_readiness` result, if available>\n")
		TEXT("- completed_phases: []\n")
		TEXT("- evidence: {}\n")
		TEXT("- current_blockers: []\n")
		TEXT("Return the `unreal_mcp_ide_companion_status.v1` receipt, then summarize blocking gates, phase states, missing evidence, readiness for paid generation/editor mutation/runtime verification, and the next safe MCP action."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Generate IDE Companion Work Order"),
		TEXT("Create the next executable phase order"),
		TEXT("Use MCP tool `skill_compile_ide_companion_work_order` with the latest session plan and status receipt.\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.generate_work_order.target_work_order_context` first, then use its target phase, session-plan/status state, readiness state, blocker count, template operation counts, and stop policy.\n")
		TEXT("Parameters:\n")
		TEXT("- session_plan: <paste the `unreal_mcp_ide_companion_session_plan.v1` plan>\n")
		TEXT("- companion_status: <paste the latest `unreal_mcp_ide_companion_status.v1` receipt, if available>\n")
		TEXT("- target_phase: \"\"\n")
		TEXT("- readiness_report: <paste the latest readiness report if status is not available>\n")
		TEXT("Return the `unreal_mcp_ide_companion_work_order.v1` work order, then summarize target phase, prerequisites, blockers, tool steps, evidence to collect, acceptance criteria, stop conditions, and the after-completion status refresh."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Gameplay Template Plan"),
		TEXT("Inspect selected feature template gates before editor work"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_gameplay_template_plan.target_gameplay_template_context` first, then `outputs.work_order_template`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the template name, assets, graph/component operations, operation proof contracts, compile/readback checks, PIE validation, evidence requirements, repair notes, ownership domains, placeholder/generated asset swap requirements, generated animation prompt requirements, paid-animation readiness gates, Uthana allowance/evidence tools, and stop-before-editor/provider policy before queueing or executing editor work. This command is review-only: do not mutate Unreal, queue actions, run PIE, write ledger evidence, call providers, or spend credits."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Evidence Requirements"),
		TEXT("Inspect pending, blocked, and recorded proof before ledger writes"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_evidence_requirements.target_evidence_review_context` first, then `outputs.evidence_recording` and `outputs.workflow_actions.record_evidence.target_evidence_context`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the evidence item counts, selected target evidence row, artifact preview, bridge requirement, and stop-before-ledger-write policy to decide whether to record evidence, resolve blockers, run a safe step, or gather missing proof. This command is review-only: do not mutate Unreal, write ledger evidence, call providers, spend credits, or bypass readiness gates."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Record IDE Companion Evidence"),
		TEXT("Persist phase proof and refresh session status"),
		TEXT("Use MCP tool `skill_record_ide_companion_evidence` after completing or stopping a companion phase.\n")
		TEXT("Parameters:\n")
		TEXT("- session_plan: <paste the `unreal_mcp_ide_companion_session_plan.v1` plan>\n")
		TEXT("- phase_name: \"orient_to_project\"\n")
		TEXT("- evidence_type: \"context | readiness | asset | blueprint | runtime | report | blocker\"\n")
		TEXT("- summary: \"what was proven or why the phase stopped\"\n")
		TEXT("- artifacts: []\n")
		TEXT("- readiness_report: <latest readiness report, if relevant>\n")
		TEXT("- companion_status: <latest status receipt, if relevant>\n")
		TEXT("- work_order: <latest work order, if relevant>\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.record_evidence.target_evidence_context` first, then `outputs.workflow_actions.record_evidence.target_evidence_item` and `outputs.evidence_recording.items`; prefer the backend-selected pending row, including generated-asset metadata, queued-action metadata, runtime-verification metadata, artifact previews, or `record_readiness_policy` gate proof.\n")
		TEXT("Return the `unreal_mcp_ide_companion_evidence_record.v1` receipt, ledger path, updated status, missing evidence, blocking gates, and next safe action."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Record Queued Action Evidence"),
		TEXT("Persist compile and readback proof for the selected queued editor action"),
		TEXT("Use MCP tool `skill_record_ide_companion_evidence` after the cockpit-selected queued editor action has completed or stopped.\n")
		TEXT("Parameters:\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- phase_name: <from `outputs.workflow_actions.record_queued_action_evidence.arguments.phase_name`>\n")
		TEXT("- evidence_type: \"editor_queue\"\n")
		TEXT("- summary: <from `outputs.workflow_actions.record_queued_action_evidence.arguments.summary`>\n")
		TEXT("- artifacts: <compile/readback proof from `outputs.workflow_actions.record_queued_action_evidence.arguments.artifacts`>\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.record_queued_action_evidence.target_evidence_context` first, including its `queued_action` metadata, then `outputs.next_safe_step`, `outputs.execution_review`, and `outputs.evidence_recording.items.record_editor_queue_1`.\n")
		TEXT("Do not execute queued work from this command. Record only evidence that already exists, or summarize why queued action proof remains blocked."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Record Generated Asset Evidence"),
		TEXT("Persist provider, placeholder, import-path, and quality-gate proof"),
		TEXT("Use MCP tool `skill_record_ide_companion_evidence` after generated-asset lifecycle proof is available.\n")
		TEXT("Parameters:\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- phase_name: <from `outputs.workflow_actions.record_generated_asset_evidence.arguments.phase_name`>\n")
		TEXT("- evidence_type: \"generated_asset_quality_gate\"\n")
		TEXT("- summary: <from `outputs.workflow_actions.record_generated_asset_evidence.arguments.summary`>\n")
		TEXT("- artifacts: <provider, placeholder, import-path, and quality proof from `outputs.workflow_actions.record_generated_asset_evidence.arguments.artifacts`>\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.record_generated_asset_evidence.target_evidence_context` first, including its `generated_asset` metadata, then `outputs.generated_asset_quality_gate` and `outputs.evidence_recording.items.record_generated_asset_quality_gate`.\n")
		TEXT("Do not submit provider tasks or import assets from this command. Record only evidence that already exists, or summarize why generated asset proof remains blocked."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Record Paid Generation Evidence"),
		TEXT("Persist Tripo wallet, Uthana allowance, and human approval proof"),
		TEXT("Use MCP tool `skill_record_ide_companion_evidence` after no-spend provider readiness proof and explicit human spend/usage approval are available.\n")
		TEXT("Parameters:\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- phase_name: <from `outputs.workflow_actions.record_paid_generation_evidence.arguments.phase_name`>\n")
		TEXT("- evidence_type: \"paid_generation_evidence\"\n")
		TEXT("- summary: <from `outputs.workflow_actions.record_paid_generation_evidence.arguments.summary`>\n")
		TEXT("- artifacts: <wallet, allowance, approval, and no-provider-call proof from `outputs.workflow_actions.record_paid_generation_evidence.arguments.artifacts`>\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.record_paid_generation_evidence.target_evidence_context` first, then `outputs.workflow_actions.review_provider_spend_gate.target_provider_spend_context` and `outputs.evidence_recording.items.record_paid_generation_evidence`.\n")
		TEXT("Do not call Tripo or Uthana, download files, import assets, reserve credits, approve spend, or mutate Unreal from this command. Record only evidence that already exists, or summarize why paid generation remains blocked."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Record Generated Animation Evidence"),
		TEXT("Persist Uthana motion, retarget, AnimGraph, PIE, and ledger proof"),
		TEXT("Use MCP tool `skill_record_ide_companion_evidence` after generated-animation lifecycle proof is available or blocked.\n")
		TEXT("Parameters:\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- phase_name: <from `outputs.workflow_actions.record_generated_animation_evidence.arguments.phase_name`>\n")
		TEXT("- evidence_type: \"generated_animation_evidence\"\n")
		TEXT("- summary: <from `outputs.workflow_actions.record_generated_animation_evidence.arguments.summary`>\n")
		TEXT("- artifacts: <motion, target skeleton, import path, compiler, and missing-stage proof from `outputs.workflow_actions.record_generated_animation_evidence.arguments.artifacts`>\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.record_generated_animation_evidence.target_evidence_context` first, including its `generated_animation` metadata, then `outputs.workflow_actions.compile_generated_animation_evidence` and `outputs.evidence_recording.items.record_generated_animation_evidence`.\n")
		TEXT("Do not call Uthana, download files, import animations, run PIE, or mutate Unreal from this command. Record only evidence that already exists, or summarize why generated animation proof remains blocked."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Record Feature Completion Contract"),
		TEXT("Persist gameplay feature proof gates after evidence review"),
		TEXT("Use MCP tool `skill_record_ide_companion_evidence` after the gameplay feature completion contract has been reviewed and its underlying proof rows exist.\n")
		TEXT("Parameters:\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- phase_name: <from `outputs.workflow_actions.record_feature_completion_contract.arguments.phase_name`>\n")
		TEXT("- evidence_type: \"feature_completion_contract\"\n")
		TEXT("- summary: <from `outputs.workflow_actions.record_feature_completion_contract.arguments.summary`>\n")
		TEXT("- artifacts: <required-evidence and proof-gate preview from `outputs.workflow_actions.record_feature_completion_contract.arguments.artifacts`>\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.record_feature_completion_contract.target_evidence_context` first, including its `feature_completion_contract` metadata, then `outputs.work_order_template` and `outputs.evidence_recording.items.record_feature_completion_contract`.\n")
		TEXT("Do not mutate Unreal, run PIE, call providers, or bypass missing proof from this command. Record only the contract review after compile/readback, PIE, asset, repair, and ledger evidence has been gathered or explicitly blocked."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Record Runtime Evidence"),
		TEXT("Persist PIE, screenshot, actor-state, compile, and readback proof"),
		TEXT("Use MCP tool `skill_record_ide_companion_evidence` after scoped runtime verification proof is available.\n")
		TEXT("Parameters:\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- phase_name: <from `outputs.workflow_actions.record_runtime_evidence.arguments.phase_name`>\n")
		TEXT("- evidence_type: \"runtime_verification\"\n")
		TEXT("- summary: <from `outputs.workflow_actions.record_runtime_evidence.arguments.summary`>\n")
		TEXT("- artifacts: <PIE log, viewport screenshot, actor state, compile, and readback proof>\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.record_runtime_evidence.target_evidence_context` first, including its `runtime_verification` metadata, then `outputs.runtime_review` and `outputs.evidence_recording.items.record_runtime_verification`.\n")
		TEXT("Do not run PIE or mutate Unreal from this command. Record only evidence that already exists, or summarize why runtime proof remains blocked."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Resume IDE Companion Session"),
		TEXT("Load ledger state and produce the next work order"),
		TEXT("Use MCP tool `skill_resume_ide_companion_session` to resume a local companion ledger.\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.resume_companion_session.target_resume_context` first, then use its ledger path, next phase/tool, latest phase, and blocking gate preview.\n")
		TEXT("Parameters:\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- ledger_path: \"\"\n")
		TEXT("- readiness_report: <latest readiness report, optional>\n")
		TEXT("- current_blockers: []\n")
		TEXT("Return the `unreal_mcp_ide_companion_resume.v1` packet, then summarize completed phases, blocking gates, next action, next work order, and ledger path."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Show IDE Companion Dashboard"),
		TEXT("Render readiness, progress, next work, assets, mechanics, and evidence"),
		TEXT("Use MCP tool `skill_compile_ide_companion_dashboard` to compile a display-ready companion dashboard.\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.show_companion_dashboard.target_dashboard_context` first, then use its ledger path, readiness state, queue counts, generated asset state, runtime state, and repair state.\n")
		TEXT("Parameters:\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- ledger_path: \"\"\n")
		TEXT("- session_plan: <optional `unreal_mcp_ide_companion_session_plan.v1` plan if no ledger exists>\n")
		TEXT("- readiness_report: <latest readiness report, optional>\n")
		TEXT("- current_blockers: []\n")
		TEXT("Return the `unreal_mcp_ide_companion_dashboard.v1` packet, then summarize dashboard cards, primary action, blocking gates, next work order, generated asset count, mechanic hooks, and ledger path."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Show Evidence Ledger"),
		TEXT("Inspect bounded ledger events, artifacts, status, and work-order proof"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.show_evidence_ledger.target_evidence_ledger_context`, then call `chat_get_cockpit_ledger_detail` with its ledger path or session name.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- ledger_path: \"\"\n")
		TEXT("- limit: 50\n")
		TEXT("Return the `unreal_mcp_chat_ledger_detail.v1` packet, then summarize timeline events, artifact previews, latest status/work order, missing evidence, and next safe evidence action. Do not record evidence or mutate Unreal from this inspection step."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Refresh IDE Cockpit Overview"),
		TEXT("Load session, ledger, queue, blockers, cards, and suggested actions"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current MCP Chat session.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Return the `unreal_mcp_chat_cockpit_overview.v1` packet, then summarize selected session, blocker gates, editor queue state, evidence ledger state, disabled/enabled suggested actions, and the safest next user-visible action. Do not execute queued editor actions unless readiness gates pass."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Resolve IDE Companion Blockers"),
		TEXT("Choose unblock, placeholder, or stop paths for current gates"),
		TEXT("Use MCP tool `skill_compile_ide_companion_blocker_resolution` when readiness/status gates block the companion.\n")
		TEXT("Parameters:\n")
		TEXT("- dashboard: <optional latest `unreal_mcp_ide_companion_dashboard.v1` packet>\n")
		TEXT("- session_plan: <optional `unreal_mcp_ide_companion_session_plan.v1` plan>\n")
		TEXT("- companion_status: <optional latest `unreal_mcp_ide_companion_status.v1` receipt>\n")
		TEXT("- readiness_report: <optional latest readiness report>\n")
		TEXT("- preferred_strategy: \"continue_with_placeholders\"\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.resolve_blockers` first; prefer its `target_blocker_resolution`, especially `unblock_action`, `fallback_action`, `evidence_required`, and `can_continue_offline`, then use `arguments.target_blocker`, `arguments.current_blockers`, and `outputs.blocker_resolutions` before asking for pasted JSON.\n")
		TEXT("For `provider_api_key_configured` or `animation_provider_api_key_configured`, prefer the native Generate Settings masked `TRIPO_API_KEY` and `UTHANA_API_KEY` fields when available; env vars and `gen_save_provider_config` remain valid no-leak fallback paths.\n")
		TEXT("Return the `unreal_mcp_ide_companion_blocker_resolution.v1` packet, then summarize blocking gates, recommended path, unblock actions, fallback actions, placeholder policy, bridge-offline policy, and evidence to record."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Compile Placeholder Asset Manifest"),
		TEXT("Plan no-spend placeholders for blocked generated assets"),
		TEXT("Use MCP tool `skill_compile_ide_companion_placeholder_manifest` when generated assets are blocked but gameplay proof can continue.\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.compile_placeholder_manifest.target_placeholder_context` first, then use its asset counts, selected target asset, blocker count, placeholder root, session-plan state, and stop policy.\n")
		TEXT("Parameters:\n")
		TEXT("- session_plan: <paste the `unreal_mcp_ide_companion_session_plan.v1` plan>\n")
		TEXT("- placeholder_root: \"\"\n")
		TEXT("- blocker_resolution: <optional latest `unreal_mcp_ide_companion_blocker_resolution.v1` packet>\n")
		TEXT("Return the `unreal_mcp_ide_companion_placeholder_manifest.v1` manifest, then summarize placeholder assets, replacement map, tool steps, evidence to collect, and replacement policy for later Tripo imports."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Compile Generated Asset Lifecycle"),
		TEXT("Track provider-neutral generation, import, replacement, and proof gates"),
		TEXT("Use MCP tool `skill_compile_ide_companion_asset_lifecycle_manifest` after an IDE companion session plan exists, optionally with the placeholder manifest.\n")
		TEXT("Parameters:\n")
		TEXT("- session_plan: <paste the `unreal_mcp_ide_companion_session_plan.v1` plan>\n")
		TEXT("- placeholder_manifest: <optional latest `unreal_mcp_ide_companion_placeholder_manifest.v1` packet>\n")
		TEXT("- preferred_provider: \"tripo\"\n")
		TEXT("- write_manifest: true\n")
		TEXT("- manifest_name: \"asset_lifecycle\"\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.compile_asset_lifecycle_manifest.target_asset_lifecycle_compile_context` first, then `outputs.work_order_template` generated prompt counts and `outputs.generated_asset_lifecycles`, before asking for pasted lifecycle JSON.\n")
		TEXT("Return the `unreal_mcp_ide_companion_generated_asset_lifecycle.v1` manifest, then summarize provider task contracts, spend gates, placeholder replacement mapping, quality gates, viewport proof, and ledger evidence requirements."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Generated Asset Gate"),
		TEXT("Inspect generated asset provider, import, quality, and evidence gates"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_generated_asset_gate.target_generated_asset_review_context` first, then `outputs.generated_asset_quality_gate`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the selected target asset, provider/import/quality counts, placeholder count, next gate, manifest path, and quality proof preview to decide whether to resolve blockers, continue with placeholders, import assets, or record evidence. This command is review-only: do not submit provider tasks, spend credits, import assets, replace placeholders, mutate Unreal, or record evidence from this command."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Generated Asset Lifecycle Gate"),
		TEXT("Inspect prompt, provider, task, placeholder, import, quality, and evidence lifecycle completeness"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_generated_asset_lifecycle_gate.target_generated_asset_lifecycle_context` first, then `outputs.generated_asset_lifecycles` and `outputs.generated_asset_quality_gate`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the provider-neutral lifecycle summary, preferred provider, manifest path preview, prompt/provider/task/placeholder/import/quality/evidence stage counts, selected asset, and stop-condition count to decide whether to review provider spend, import readiness, placeholder fallback, or evidence requirements. This command is review-only: do not call providers, spend credits, import assets, mutate Unreal, replace placeholders, run queued actions, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Generated Animation Lifecycle Gate"),
		TEXT("Inspect Uthana motion generation, retarget, AnimGraph, PIE, and ledger gates"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_generated_animation_lifecycle_gate.target_generated_animation_lifecycle_context` first, especially `next_safe_action`, then `outputs.generated_asset_lifecycles.preview_animation_assets` and `outputs.readiness_policy`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the selected Uthana motion prompt, motion id, target skeleton, expected Animation Sequence path, animation quality proof contract, quality_proof_required_preview, quality gate preview, missing paid/editor gates, and stop-before-animation-generation-or-import policy before text-to-motion, download, animation import, retarget, AnimGraph work, PIE proof, or ledger evidence. This command is review-only: do not call Uthana, download files, import animations, mutate Unreal, run queued actions, spend credits, compile, save assets, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Compile Generated Animation Evidence"),
		TEXT("Build the no-spend Uthana motion evidence receipt"),
		TEXT("Use MCP tool `gen_compile_generated_animation_evidence` after collecting provider, download, import, retarget/readback, AnimGraph, PIE, ledger, and approval proof.\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.compile_generated_animation_evidence.target_generated_animation_lifecycle_context` first, including `next_safe_action`, then use `outputs.workflow_actions.compile_generated_animation_evidence.arguments` as the starter input and fill captured proof JSON only from evidence that exists.\n")
		TEXT("Parameters:\n")
		TEXT("- session_name: \"ide-companion\"\n")
		TEXT("- motion_prompt: <from selected generated animation or source prompt>\n")
		TEXT("- motion_id: <from Uthana text-to-motion, video job poll, or metadata result>\n")
		TEXT("- character_id: <from selected/generated animation character id>\n")
		TEXT("- text_motion_result_json, job_result_json, motion_result_json, download_allowed_json, download_result_json, import_result_json, retarget_evidence_json, animgraph_evidence_json, pie_evidence_json, ledger_evidence_json, approval_note: <captured proof only>\n")
		TEXT("This command compiles evidence only: do not call Uthana, download files, import animations, mutate Unreal, run PIE, save assets, write ledger evidence, or approve work from this command."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Generated Asset Import Gate"),
		TEXT("Inspect import path, placeholder, and quality proof gates"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_generated_asset_import_gate.target_generated_asset_import_context` first, then `outputs.generated_asset_quality_gate.items` and `outputs.readiness_policy.editor_mutation`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the selected import/quality-pending asset, expected import path, imported asset path, placeholder state, quality proof counts, missing bridge gates, and stop-before-import-or-quality-work policy before generated asset import, material/collision work, viewport proof, or placeholder replacement. This command is review-only: do not import assets, mutate Unreal, replace placeholders, run queued actions, call providers, spend credits, compile, save assets, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Generated Asset Quality Proof Gate"),
		TEXT("Inspect material, collision, viewport, and ledger proof requirements"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_generated_asset_quality_proof_gate.target_generated_asset_quality_proof_context` first, then `outputs.generated_asset_quality_gate.items` and `outputs.readiness_policy.editor_mutation`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the selected generated asset, quality proof contract, quality_proof_required_preview, quality gate preview, material/collision/viewport/ledger proof flags, missing editor gates, imported asset path, and stop-before-quality-proof-work policy before quality checks, viewport capture, placeholder replacement, or ledger evidence recording. This command is review-only: do not capture viewports, mutate Unreal, import assets, replace placeholders, run queued actions, call providers, spend credits, compile, save assets, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Generated Asset Replacement Gate"),
		TEXT("Inspect placeholder-to-generated asset replacement readiness"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_generated_asset_replacement_gate.target_generated_asset_replacement_context` first, then `outputs.generated_asset_lifecycles.preview_assets` and `outputs.readiness_policy.editor_mutation`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the selected placeholder asset path, expected/imported generated asset path, quality proof counts, replacement policy preview, missing editor gates, and stop-before-placeholder-replacement policy before replacing placeholder references with generated assets. This command is review-only: do not replace placeholders, mutate Unreal, import assets, run queued actions, call providers, spend credits, compile, save assets, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Provider Spend Gate"),
		TEXT("Inspect provider credentials, wallet, and spend gates before generation"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_provider_spend_gate.target_provider_spend_context` first, then `outputs.readiness_policy.paid_generation` and `outputs.generated_asset_quality_gate`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the selected provider-pending asset, provider name, missing provider/wallet/spend gates, required evidence, `fallback_placeholder_available`, `fallback_action_id`, fallback tool/queue tool, and stop-before-provider-call policy to decide whether to refresh readiness, continue with placeholders, or stop for explicit spend confirmation. This command is review-only: do not submit provider tasks, spend credits, call providers, import assets, mutate Unreal, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Continue With Placeholder Fallback"),
		TEXT("Compile no-spend placeholders when provider spend is blocked"),
		TEXT("Use MCP tool `skill_compile_ide_companion_placeholder_manifest` only when a cockpit overview exposes `outputs.workflow_actions.continue_with_placeholder_fallback` and `target_provider_spend_context.fallback_placeholder_available` is true.\n")
		TEXT("Parameters:\n")
		TEXT("- session_plan: <latest session_plan from ledger, dashboard, or resume output>\n")
		TEXT("- placeholder_root: <from `outputs.workflow_actions.continue_with_placeholder_fallback.arguments.placeholder_root`>\n")
		TEXT("- blocker_resolution: <optional latest `unreal_mcp_ide_companion_blocker_resolution.v1` packet>\n")
		TEXT("Use `target_placeholder_context`, `fallback_action_id`, fallback tool/queue tool, selected target asset, placeholder root, and stop policy before compiling placeholder manifests. This command must not submit provider tasks, spend credits, call providers, import assets, mutate Unreal, queue actions, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Generated Asset Provider Task Gate"),
		TEXT("Inspect provider task status and download/import readiness"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_generated_asset_provider_task_gate.target_generated_asset_provider_task_context` first, then `outputs.generated_asset_lifecycles.preview_assets` and `outputs.readiness_policy.paid_generation`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the selected provider task status, task id, status/download/import tools, downloaded path, expected/imported asset path, missing provider gates, and stop-before-provider-task-or-download policy before polling provider status, downloading outputs, importing assets, or writing ledger evidence. This command is review-only: do not call providers, poll status, download files, import assets, mutate Unreal, spend credits, run queued actions, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Resolve Generated Asset"),
		TEXT("Continue from the cockpit-selected generated asset blocker"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.resolve_generated_asset.target_generated_asset_context` first, then `outputs.generated_asset_quality_gate.items`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the selected target asset id, manifest path, current state, next gate, placeholder availability, import path, quality-gate preview, and ledger path to choose the next safe step. If provider or spend gates are blocked, continue with placeholders or evidence recording; do not submit provider tasks, spend credits, import assets, replace placeholders, mutate Unreal, or record evidence until the relevant readiness gates and human intent are explicit."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Editor Queue"),
		TEXT("Inspect queued editor actions, blockers, and evidence requirements"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_editor_queue.target_queue_review_context` first, then `outputs.editor_queues` and `outputs.next_safe_step`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the queue count, action count, executable/blocked queue counts, bridge blockers, next action, evidence count, and stop policy to decide whether to execute one safe step, recompile the queue, record evidence, or wait for bridge readiness. This command is review-only: do not mutate Unreal, run queued actions, or record evidence from this command."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Queue IDE Companion Editor Actions"),
		TEXT("Persist bridge-gated editor work for later execution"),
		TEXT("Use MCP tool `skill_compile_ide_companion_editor_queue` when the Unreal bridge is unavailable or editor work needs a durable execution list.\n")
		TEXT("Parameters:\n")
		TEXT("- session_plan: <paste the `unreal_mcp_ide_companion_session_plan.v1` plan>\n")
		TEXT("- companion_status: <optional latest `unreal_mcp_ide_companion_status.v1` receipt>\n")
		TEXT("- work_order: <optional latest `unreal_mcp_ide_companion_work_order.v1` packet>\n")
		TEXT("- placeholder_manifest: <optional latest `unreal_mcp_ide_companion_placeholder_manifest.v1` packet>\n")
		TEXT("- queue_name: \"editor_queue\"\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.queue_editor_actions.target_queue_context` first, then use `arguments.target_phase`, `arguments.ledger_path`, and `chat_get_cockpit_ledger_detail` before asking for pasted plan/status JSON.\n")
		TEXT("Return the `unreal_mcp_ide_companion_editor_queue.v1` packet and queue path, then summarize bridge gate state, prerequisites, queued actions, stop conditions, evidence to collect, and after-execution ledger/dashboard steps."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Execute Next Safe Step"),
		TEXT("Run only the cockpit-approved next editor action"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.execute_next_safe_step.target_execution_review_context` first, then `outputs.workflow_actions.execute_next_safe_step.target_execute_context` and `outputs.next_safe_step`, and continue only if `can_execute_now` is true.\n")
		TEXT("Before executing, follow `pre_execution_checklist` and `executor_contract`; after the single action, record `post_execution_evidence_required` before continuing the queue.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("If ready, run only `next_safe_step.next_action_tool` for `next_safe_step.next_action_id` from `next_safe_step.queue_path`, then stop and record the listed after-execution evidence before any second queued action. If bridge/readiness gates are blocked, do not mutate Unreal; summarize blockers and recovery tools instead."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Runtime Verification"),
		TEXT("Inspect PIE, compile, readback, and evidence proof gates"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_runtime_verification.target_runtime_review_context` first, then `outputs.runtime_review` and `outputs.runtime_verification`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("If runtime verification is blocked, do not mutate Unreal or run PIE; summarize missing bridge/readiness/proof gates and record required evidence. If ready, capture only the scoped runtime probe, stop, and record PIE log, viewport screenshot, actor state, compile, and readback evidence before continuing."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Repair Failed Step"),
		TEXT("Compile a bounded repair pass from cockpit triage"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.repair_failed_step.target_repair_review_context` first, then `outputs.workflow_actions.repair_failed_step.target_repair_context`, `outputs.failure_triage`, and `outputs.repair_loop`, and compile a scoped repair work order.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("If a repair is needed, use `skill_compile_ide_companion_work_order` with the latest ledger/work-order context and a repair-oriented target phase. Apply no editor mutation until bridge/readiness gates pass, and record evidence for the repair outcome."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("IDE Companion Readiness"),
		TEXT("Check asset, gameplay, budget, and bridge gates"),
		TEXT("Use MCP tool `gen_compile_ide_companion_readiness` before starting a full Unreal companion session.\n")
		TEXT("If a cockpit overview is available, inspect `outputs.workflow_actions.check_readiness.target_readiness_policy_context` first, then `outputs.readiness_policy`, before asking for pasted readiness JSON.\n")
		TEXT("Parameters:\n")
		TEXT("- project_brief: \"single-developer playable slice with generated assets and one guided gameplay mechanic\"\n")
		TEXT("- expected_generated_assets: 3\n")
		TEXT("- include_api_wallet: true\n")
		TEXT("- include_unreal_bridge: true\n")
		TEXT("Return the `unreal_mcp_ide_companion_readiness.v1` report, then summarize readiness, blocking gates, Tripo mesh auth, Uthana animation auth, wallet state, session budget, bridge status, workspace files, and the safest next MCP tool sequence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Readiness Repair Queue"),
		TEXT("Inspect the prioritized blocker repair order"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_readiness_repair_queue.target_readiness_repair_queue_context` first, then `outputs.readiness_repair_queue` if deeper evidence is needed.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the recommended next repair, next gate, next tool, required command, priority policy, evidence preview, and stop-before-running-repair policy before running receipt scripts, bridge checks, provider checks, or evidence recording. This command is review-only: do not execute scripts, ping the bridge, call providers, check wallets, mutate Unreal, stage files, commit, clean, merge, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Platform Preflight Gate"),
		TEXT("Inspect registry, bridge, chat, provider, build, and dirty-state gates"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context` first, then `outputs.readiness_policy` and `scripts/audit_ide_companion_readiness.py` if deeper evidence is needed.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use tool-count reproducibility, dirty-state risk, bridge/chat/provider/build state, build-wrapper reference readiness, platform-stability blockers, and stop-before-editor-provider-or-blueprint policy before risky work. This command is review-only: do not mutate Unreal, ping the bridge manually, call providers, spend credits, write ledger evidence, compile, save assets, or run test lanes."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Live Editor Bridge Gate"),
		TEXT("Inspect bridge, queue, PIE, and evidence gates before editor work"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_live_editor_bridge_gate.target_live_editor_context` first, then `outputs.next_safe_step`, `outputs.execution_review`, and `outputs.runtime_review` if deeper evidence is needed.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use bridge reachability, queued action state, runtime/PIE readiness, after-execution evidence, and stop-before-editor-or-PIE policy before live editor work. This command is review-only: do not mutate Unreal, manually ping the bridge, run PIE, execute queued actions, compile, save assets, call providers, spend credits, or write ledger evidence."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review WIP Promotion Gate"),
		TEXT("Inspect whether WIP is stable enough to move toward main"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_wip_promotion_gate.target_wip_promotion_context` first, then the platform preflight, bridge wrapper, and test lane review targets if deeper evidence is needed.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use registry reproducibility, no-mutation CI lane state, bridge wrapper coverage, build-wrapper reference readiness, last plugin build, dirty-state grouping, chat cockpit reachability, and the wip-to-main promotion policy before release movement. This command is review-only: do not create branches, stage files, commit, merge, mutate Unreal, call providers, spend credits, or run live lanes."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Blueprint Mutation Gate"),
		TEXT("Inspect pre-read, compile, and readback gates before Blueprint edits"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_blueprint_mutation_gate.target_blueprint_mutation_context` first, then `outputs.readiness_policy.blueprint_mutation`.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the missing bridge/pre-read/compile/readback gates, evidence requirements, selected work-order template, queue counts, and stop-before-blueprint-mutation policy before any graph or component edit. This command is review-only: do not mutate Blueprints, compile, save assets, run queued actions, write ledger evidence, or ping the bridge."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Bridge Wrapper Coverage"),
		TEXT("Inspect high-value native bridge wrapper reachability"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_bridge_wrapper_coverage.target_bridge_wrapper_context` first, then run `scripts/audit_high_value_wrapper_coverage.py` only if deeper source evidence is needed.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the coverage status, capability count, command count, failing capability preview, audit tool, and bridge registry tool to decide whether wrapper work is already covered or needs a focused follow-up. This command is review-only: do not mutate Unreal, ping the bridge, edit Blueprint assets, or run provider tasks."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Review Test Lane Gates"),
		TEXT("Inspect offline, live-bridge, and paid-provider CI separation"),
		TEXT("Use MCP tool `chat_get_cockpit_overview` for the current session, inspect `outputs.workflow_actions.review_test_lane_gates.target_test_lane_context` first, then `docs/ci-smoke.md` if deeper lane guidance is needed.\n")
		TEXT("Parameters:\n")
		TEXT("- session: \"ide-companion\"\n")
		TEXT("- message_limit: 20\n")
		TEXT("- limit: 50\n")
		TEXT("Use the default discovery pattern, offline/live/paid/manual counts, violation preview, audit tool, and CI doc to decide whether default offline tests are safe or whether live bridge/provider checks require explicit operator intent. This command is review-only: do not run live bridge tests, paid-provider tests, mutate Unreal, call providers, or spend credits."),
		TEXT("workflow")
	);
	AddCommandPaletteItem(
		TEXT("Plan Gameplay Mechanic"),
		TEXT("Create an Unreal-ready mechanic plan"),
		TEXT("Use MCP tool `skill_plan_gameplay_mechanic` to plan this mechanic before editing Unreal.\n")
		TEXT("Parameters:\n")
		TEXT("- brief: \"player dash ability with cooldown and HUD feedback\"\n")
		TEXT("- content_path: \"/Game/Generated/Mechanics\"\n")
		TEXT("- include_generated_assets: true\n")
		TEXT("Return the `unreal_mcp_gameplay_mechanic_plan.v1` plan, then summarize Blueprint/component assets, generated asset prompts, AI/HUD/save/replication hooks, validation gates, and the next MCP tool sequence."),
		TEXT("gameplay")
	);

	AddCommandPaletteItem(
		TEXT("KB doc: v5 changelog"),
		TEXT("kb://v5/CHANGELOG.md"),
		TEXT("Open kb://v5/CHANGELOG.md and summarize the relevant recent MCP Chat changes."),
		TEXT("kb")
	);
	AddCommandPaletteItem(
		TEXT("KB doc: Unreal MCP book guidance"),
		TEXT("docs/knowledge-base/README.md"),
		TEXT("Use docs/knowledge-base/README.md and the Unreal MCP book study guides before planning this editor/plugin change."),
		TEXT("kb")
	);
	AddCommandPaletteItem(
		TEXT("KB doc: UE C++ scripting guide"),
		TEXT("docs/knowledge-base/unreal-cpp-li-2023.md"),
		TEXT("Use docs/knowledge-base/unreal-cpp-li-2023.md to check Unreal C++ and reflection guidance for this change."),
		TEXT("kb")
	);
	AddCommandPaletteItem(
		TEXT("KB doc: UE editor experience guide"),
		TEXT("docs/knowledge-base/elevating-game-experiences-ue5-2e.md"),
		TEXT("Use docs/knowledge-base/elevating-game-experiences-ue5-2e.md to check editor workflow and UI quality guidance."),
		TEXT("kb")
	);
	AddCommandPaletteItem(
		TEXT("KB doc: UE AI guide"),
		TEXT("docs/knowledge-base/game-ai-unreal-sapio-2019.md"),
		TEXT("Use docs/knowledge-base/game-ai-unreal-sapio-2019.md to check Behavior Tree, Blackboard, nav, and EQS guidance."),
		TEXT("kb")
	);

	TArray<FString> Categories;
	ToolPaletteByCategory.GetKeys(Categories);
	Categories.Sort();
	for (const FString& Category : Categories)
	{
		if (const TArray<FToolPaletteEntry>* Tools = ToolPaletteByCategory.Find(Category))
		{
			for (const FToolPaletteEntry& Tool : *Tools)
			{
				const FString Detail = Tool.Description.IsEmpty()
					? FString::Printf(TEXT("Tool in %s"), *Category)
					: FString::Printf(TEXT("%s - %s"), *Category, *Tool.Description);
				AddCommandPaletteItem(Tool.Name, Detail, BuildToolPromptTemplate(Tool), TEXT("tool"));
			}
		}
	}

	TSet<FString> SeenAssetReferences;
	for (const FChatMessage& Message : Messages)
	{
		int32 SearchIndex = 0;
		while (SearchIndex < Message.Message.Len())
		{
			const int32 ReferenceIndex = Message.Message.Find(TEXT("@asset:"), ESearchCase::IgnoreCase, ESearchDir::FromStart, SearchIndex);
			if (ReferenceIndex == INDEX_NONE)
			{
				break;
			}

			int32 ReferenceEnd = ReferenceIndex;
			while (ReferenceEnd < Message.Message.Len() && !FChar::IsWhitespace(Message.Message[ReferenceEnd]))
			{
				++ReferenceEnd;
			}

			const FString Reference = Message.Message.Mid(ReferenceIndex, ReferenceEnd - ReferenceIndex).TrimStartAndEnd();
			if (!Reference.IsEmpty() && !SeenAssetReferences.Contains(Reference))
			{
				SeenAssetReferences.Add(Reference);
				AddCommandPaletteItem(
					FString::Printf(TEXT("Recent asset: %s"), *Reference),
					TEXT("Recent asset reference"),
					Reference,
					TEXT("asset")
				);
			}
			SearchIndex = ReferenceEnd + 1;
		}
	}

	int32 RecentPromptCount = 0;
	for (int32 MessageIndex = Messages.Num() - 1; MessageIndex >= 0 && RecentPromptCount < 12; --MessageIndex)
	{
		const FChatMessage& Message = Messages[MessageIndex];
		if (NormaliseSender(Message.Sender) != TEXT("user") || Message.Message.TrimStartAndEnd().IsEmpty())
		{
			continue;
		}

		const FString Prompt = Message.Message.TrimStartAndEnd();
		AddCommandPaletteItem(
			FString::Printf(TEXT("Recent prompt: %s"), *TruncateForCard(Prompt, 64)),
			Message.Timestamp.IsEmpty() ? TEXT("Recent prompt") : Message.Timestamp,
			Prompt,
			TEXT("prompt")
		);
		++RecentPromptCount;
	}
}

void SMCPChatPanel::RebuildCommandPaletteResults()
{
	if (!CommandPaletteResults.IsValid())
	{
		return;
	}

	CommandPaletteResults->ClearChildren();

	int32 MatchCount = 0;
	for (const FCommandPaletteItem& Item : CommandPaletteItems)
	{
		if (!CommandPaletteItemMatches(CommandPaletteFilter, Item))
		{
			continue;
		}

		CommandPaletteResults->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 0.0f, 0.0f, 4.0f)
		[
			SNew(SButton)
			.ToolTipText(FText::FromString(Item.Detail))
			.OnClicked(this, &SMCPChatPanel::HandleCommandPaletteItemClicked, Item)
			[
				SNew(SVerticalBox)

				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SNew(STextBlock)
					.Text(FText::FromString(Item.Label))
					.Font(FAppStyle::GetFontStyle("SmallFontBold"))
				]

				+ SVerticalBox::Slot()
				.AutoHeight()
				[
					SNew(STextBlock)
					.Text(FText::FromString(Item.Detail))
					.ColorAndOpacity(FSlateColor::UseSubduedForeground())
					.AutoWrapText(true)
				]
			]
		];

		++MatchCount;
		if (MatchCount >= 20)
		{
			break;
		}
	}

	if (MatchCount == 0)
	{
		CommandPaletteResults->AddSlot()
		.AutoHeight()
		[
			SNew(STextBlock)
			.Text(LOCTEXT("CommandPaletteNoMatches", "No command matches"))
			.ColorAndOpacity(FSlateColor::UseSubduedForeground())
		];
	}
}

void SMCPChatPanel::AddCommandPaletteItem(const FString& Label, const FString& Detail, const FString& InsertText, const FString& Kind)
{
	FCommandPaletteItem Item;
	Item.Label = Label;
	Item.Detail = Detail;
	Item.InsertText = InsertText;
	Item.Kind = Kind;
	CommandPaletteItems.Add(Item);
}

void SMCPChatPanel::OpenCommandPaletteWithFilter(const FString& Filter, const FText& InStatusText)
{
	bCommandPaletteVisible = true;
	CommandPaletteFilter = Filter;
	RefreshCommandPaletteItems();
	RebuildCommandPaletteResults();
	if (CommandPaletteInput.IsValid())
	{
		CommandPaletteInput->SetText(FText::FromString(Filter));
		FSlateApplication::Get().SetKeyboardFocus(CommandPaletteInput.ToSharedRef());
	}
	SetStatus(InStatusText, PendingStatusColor);
}

TArray<SMCPChatPanel::FSamplePromptItem> SMCPChatPanel::GetSamplePromptItems() const
{
	TArray<FSamplePromptItem> Items;

	auto AddSample = [&Items](const FString& Label, const FString& Prompt)
	{
		FSamplePromptItem Item;
		Item.Label = Label;
		Item.Prompt = Prompt;
		Items.Add(Item);
	};

	AddSample(
		TEXT("Health System"),
		TEXT("Create a health system Blueprint and add it to my selected player character. Use the health_system skill plus Blueprint component tools, compile the Blueprint, report warnings, and include the asset paths you changed.")
	);
	AddSample(
		TEXT("Build Slime Enemy"),
		TEXT("Build me a slime enemy demo chain inside the current level: create the enemy Blueprint, add simple movement/chase AI with Blackboard and Behavior Tree tools, place one instance, compile assets, run a PIE/log smoke check, and show evidence.")
	);
	AddSample(
		TEXT("Dungeon Starter"),
		TEXT("Create a small third-person dungeon starter using editor placement tools: block out a room, add a player start, add lighting, create a nav-ready enemy patrol path, save changed assets, and return a vertical-slice checklist.")
	);
	AddSample(
		TEXT("HUD Health Bar"),
		TEXT("Create a UMG HUD with a health bar bound to the selected player health component, add it to the player flow, compile the widget Blueprint, and report any binding or runtime risks.")
	);
	AddSample(
		TEXT("Repair Blueprint"),
		TEXT("Audit the selected Blueprint for compile/runtime issues, run the repair_broken_blueprint skill where needed, recompile, and summarize every fixed node or unresolved warning.")
	);
	AddSample(
		TEXT("Asset Import Pass"),
		TEXT("Import or validate a dropped @file mesh or texture, create material instances with material tools, place the asset in the current level, capture viewport evidence, and list the generated Content Browser paths.")
	);

	return Items;
}

TSharedRef<SWidget> SMCPChatPanel::BuildOnboardingOverlay()
{
	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.Padding(8.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 4.0f)
			[
				SNew(STextBlock)
				.Text(this, &SMCPChatPanel::GetOnboardingStepTitle)
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 8.0f)
			[
				SNew(STextBlock)
				.Text(this, &SMCPChatPanel::GetOnboardingStepText)
				.ColorAndOpacity(FSlateColor::UseSubduedForeground())
				.AutoWrapText(true)
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(this, &SMCPChatPanel::GetSamplePromptsToggleText)
					.OnClicked(this, &SMCPChatPanel::HandleToggleSamplePromptsClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(this, &SMCPChatPanel::GetOnboardingNextText)
					.OnClicked(this, &SMCPChatPanel::HandleOnboardingNextClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.Text(LOCTEXT("OnboardingDismiss", "Done"))
					.OnClicked(this, &SMCPChatPanel::HandleOnboardingDismissClicked)
				]
			]
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildSamplePrompts()
{
	TSharedRef<SWrapBox> PromptButtons = SNew(SWrapBox);
	for (const FSamplePromptItem& Item : GetSamplePromptItems())
	{
		PromptButtons->AddSlot()
		.Padding(0.0f, 0.0f, 6.0f, 4.0f)
		[
			SNew(SButton)
			.Text(FText::FromString(Item.Label))
			.ToolTipText(FText::FromString(Item.Prompt))
			.OnClicked(this, &SMCPChatPanel::HandleSamplePromptClicked, Item)
		];
	}

	return SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.Padding(8.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(STextBlock)
				.Text(LOCTEXT("SamplePromptsTitle", "Sample Prompts"))
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				PromptButtons
			]
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildContextChips()
{
	return SNew(SWrapBox)

		+ SWrapBox::Slot()
		.Padding(0.0f, 0.0f, 6.0f, 4.0f)
		[
			SNew(SButton)
			.Text(this, &SMCPChatPanel::GetOpenLevelChipText)
			.OnClicked(this, &SMCPChatPanel::HandleContextChipClicked, FString(TEXT("level")))
		]

		+ SWrapBox::Slot()
		.Padding(0.0f, 0.0f, 6.0f, 4.0f)
		[
			SNew(SButton)
			.Text(this, &SMCPChatPanel::GetSelectedActorChipText)
			.OnClicked(this, &SMCPChatPanel::HandleContextChipClicked, FString(TEXT("actor")))
		]

		+ SWrapBox::Slot()
		.Padding(0.0f, 0.0f, 6.0f, 4.0f)
		[
			SNew(SButton)
			.Text(this, &SMCPChatPanel::GetDirtyAssetsChipText)
			.OnClicked(this, &SMCPChatPanel::HandleContextChipClicked, FString(TEXT("dirty")))
		]

		+ SWrapBox::Slot()
		.Padding(0.0f, 0.0f, 6.0f, 4.0f)
		[
			SNew(SButton)
			.Text(this, &SMCPChatPanel::GetLastCompileChipText)
			.OnClicked(this, &SMCPChatPanel::HandleContextChipClicked, FString(TEXT("compile")))
		]

		+ SWrapBox::Slot()
		.Padding(0.0f, 0.0f, 6.0f, 4.0f)
		[
			SNew(SButton)
			.Text(this, &SMCPChatPanel::GetServerChipText)
			.OnClicked(this, &SMCPChatPanel::HandleContextChipClicked, FString(TEXT("server")))
		];
}

void SMCPChatPanel::AddMarkdownBlocks(const FString& MarkdownText, const FString& MessageId, TSharedRef<SVerticalBox> BodyBox)
{
	TArray<FString> Lines;
	MarkdownText.ParseIntoArrayLines(Lines, false);

	FString CurrentBlock;
	FString CurrentCodeBlock;
	bool bInCodeBlock = false;
	bool bRegisteredStreamingText = false;

	auto FlushTextBlock = [&]()
	{
		if (CurrentBlock.IsEmpty())
		{
			return;
		}

		TSharedPtr<STextBlock> TextBlock;
		BodyBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 0.0f, 0.0f, 4.0f)
		[
			SAssignNew(TextBlock, STextBlock)
			.Text(FText::FromString(CurrentBlock.TrimStartAndEnd()))
			.AutoWrapText(true)
		];

		if (!bRegisteredStreamingText && !MessageId.IsEmpty())
		{
			StreamingMessageTextBlocks.Add(MessageId, TextBlock);
			bRegisteredStreamingText = true;
		}

		CurrentBlock.Reset();
	};

	auto FlushCodeBlock = [&]()
	{
		if (CurrentCodeBlock.IsEmpty())
		{
			return;
		}

		BodyBox->AddSlot()
		.AutoHeight()
		.Padding(0.0f, 2.0f, 0.0f, 6.0f)
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
			.BorderBackgroundColor(CodeBlockColor)
			.Padding(8.0f)
			[
				SNew(STextBlock)
				.Text(FText::FromString(CurrentCodeBlock.TrimStartAndEnd()))
				.Font(FAppStyle::GetFontStyle("Monospaced"))
				.ColorAndOpacity(MarkdownAccentColor)
				.AutoWrapText(true)
			]
		];

		CurrentCodeBlock.Reset();
	};

	for (const FString& Line : Lines)
	{
		if (Line.StartsWith(TEXT("```")))
		{
			if (bInCodeBlock)
			{
				bInCodeBlock = false;
				FlushCodeBlock();
			}
			else
			{
				FlushTextBlock();
				bInCodeBlock = true;
			}
			continue;
		}

		if (bInCodeBlock)
		{
			CurrentCodeBlock += Line;
			CurrentCodeBlock += LINE_TERMINATOR;
		}
		else
		{
			CurrentBlock += Line;
			CurrentBlock += LINE_TERMINATOR;
		}
	}

	FlushTextBlock();
	FlushCodeBlock();
}

void SMCPChatPanel::AppendStreamingDelta(const FString& MessageId, const FString& Sender, const FString& Delta, bool bDone)
{
	if (MessageId.IsEmpty() || Delta.IsEmpty())
	{
		return;
	}

	for (FChatMessage& Message : Messages)
	{
		if (Message.MessageId == MessageId)
		{
			Message.Message += Delta;
			if (TSharedPtr<STextBlock>* ExistingTextBlock = StreamingMessageTextBlocks.Find(MessageId))
			{
				if (ExistingTextBlock->IsValid())
				{
					(*ExistingTextBlock)->SetText(FText::FromString(Message.Message));
				}
			}
			if (Delta.Contains(TEXT("gen_tripo_wait_for_task"), ESearchCase::IgnoreCase) ||
				Delta.Contains(TEXT("\"progress\""), ESearchCase::IgnoreCase))
			{
				RebuildMessageList();
			}
			return;
		}
	}

	AddMessage(FChatMessage{MessageId, Sender.IsEmpty() ? TEXT("agent") : Sender, Delta, MakeCurrentTimestamp()});
}

bool SMCPChatPanel::ApplySseLine(const FString& Line)
{
	if (!Line.StartsWith(TEXT("data:")))
	{
		return false;
	}

	const FString Payload = Line.RightChop(5).TrimStartAndEnd();
	TSharedPtr<FJsonObject> EventObject;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Payload);
	if (!FJsonSerializer::Deserialize(Reader, EventObject) || !EventObject.IsValid())
	{
		return false;
	}

	FString MessageId;
	FString Sender;
	FString Delta;
	bool bDone = false;
	EventObject->TryGetStringField(TEXT("message_id"), MessageId);
	EventObject->TryGetStringField(TEXT("sender"), Sender);
	EventObject->TryGetStringField(TEXT("delta"), Delta);
	EventObject->TryGetBoolField(TEXT("done"), bDone);

	AppendStreamingDelta(MessageId, Sender, Delta, bDone);
	return true;
}

void SMCPChatPanel::InsertComposerText(const FString& Text)
{
	if (!MessageInput.IsValid())
	{
		return;
	}

	const FString ExistingText = MessageInput->GetText().ToString();
	const FString Separator = ExistingText.IsEmpty() || ExistingText.EndsWith(TEXT("\n")) ? TEXT("") : LINE_TERMINATOR;
	MessageInput->SetText(FText::FromString(ExistingText + Separator + Text));
}

void SMCPChatPanel::ShowToolDetailDrawer(const FToolCallView& ToolCall)
{
	if (ToolDetailTitle.IsValid())
	{
		ToolDetailTitle->SetText(FText::Format(LOCTEXT("ToolDetailTitle", "{0} details"), FText::FromString(ToolCall.ToolName)));
	}

	if (ToolDetailBody.IsValid())
	{
		FString EvidenceText;
		if (!ToolCall.ScreenshotPaths.IsEmpty())
		{
			EvidenceText += TEXT("Screenshots:\n");
			EvidenceText += FString::Join(ToolCall.ScreenshotPaths, LINE_TERMINATOR);
			EvidenceText += TEXT("\n\n");
		}
		if (!ToolCall.PieResults.IsEmpty())
		{
			EvidenceText += TEXT("PIE results:\n");
			EvidenceText += FString::Join(ToolCall.PieResults, LINE_TERMINATOR);
			EvidenceText += TEXT("\n\n");
		}
		if (!ToolCall.LogSnippets.IsEmpty())
		{
			EvidenceText += TEXT("Log snippets:\n");
			EvidenceText += FString::Join(ToolCall.LogSnippets, LINE_TERMINATOR);
			EvidenceText += TEXT("\n\n");
		}
		if (EvidenceText.IsEmpty())
		{
			EvidenceText = TEXT("(none)");
		}

		const FString DetailText = FString::Printf(
			TEXT("Status: %s\n\nArgs summary:\n%s\n\nResult:\n%s\n\nInline evidence:\n%s\nFull detail:\n%s\n\nLog tail:\n%s"),
			*ToolCall.Status,
			*ToolCall.ArgsSummary,
			*ToolCall.ResultSummary,
			*EvidenceText,
			*ToolCall.DetailJson,
			*ToolCall.LogTail
		);
		ToolDetailBody->SetText(FText::FromString(DetailText));
	}

	SetStatus(LOCTEXT("StatusToolDetailsOpen", "Tool details open"), OkStatusColor);
}

void SMCPChatPanel::UpdateLastCompileStateFromMessage(const FChatMessage& ChatMessage)
{
	TArray<FToolCallView> ToolCalls;
	ExtractToolCallsFromMessage(ChatMessage, ToolCalls);
	for (const FToolCallView& ToolCall : ToolCalls)
	{
		if (ToolCall.ToolName.Contains(TEXT("compile"), ESearchCase::IgnoreCase))
		{
			LastCompileStatus = ToolCall.bError ? TEXT("fail") : TEXT("ok");
			return;
		}
	}

	const FString Text = ChatMessage.Message;
	if (!Text.Contains(TEXT("compile"), ESearchCase::IgnoreCase))
	{
		return;
	}

	if (Text.Contains(TEXT("failed"), ESearchCase::IgnoreCase) ||
		Text.Contains(TEXT("failure"), ESearchCase::IgnoreCase) ||
		Text.Contains(TEXT("error"), ESearchCase::IgnoreCase))
	{
		LastCompileStatus = TEXT("fail");
	}
	else if (Text.Contains(TEXT("succeeded"), ESearchCase::IgnoreCase) ||
		Text.Contains(TEXT("success"), ESearchCase::IgnoreCase) ||
		Text.Contains(TEXT("compiled"), ESearchCase::IgnoreCase))
	{
		LastCompileStatus = TEXT("ok");
	}
}

FText SMCPChatPanel::GetOpenLevelChipText() const
{
	const FString LevelName = GetOpenLevelName();
	return FText::Format(
		LOCTEXT("OpenLevelChip", "Open Level: {0}"),
		FText::FromString(LevelName.IsEmpty() ? TEXT("none") : LevelName)
	);
}

FText SMCPChatPanel::GetSelectedActorChipText() const
{
	const FString ActorName = GetSelectedActorName();
	return FText::Format(
		LOCTEXT("SelectedActorChip", "Selected Actor: {0}"),
		FText::FromString(ActorName.IsEmpty() ? TEXT("none") : ActorName)
	);
}

FText SMCPChatPanel::GetDirtyAssetsChipText() const
{
	return FText::Format(
		LOCTEXT("DirtyAssetsChip", "Dirty Assets ({0})"),
		FText::AsNumber(CountDirtyPackages())
	);
}

FText SMCPChatPanel::GetLastCompileChipText() const
{
	if (LastCompileStatus == TEXT("ok"))
	{
		return FText::FromString(TEXT("Last Compile: \u2705"));
	}
	if (LastCompileStatus == TEXT("fail"))
	{
		return FText::FromString(TEXT("Last Compile: \u274C"));
	}
	return LOCTEXT("LastCompileUnknownChip", "Last Compile: ?");
}

FText SMCPChatPanel::GetServerChipText() const
{
	return LOCTEXT("ServerChip", "Server: SSE 8000");
}

FText SMCPChatPanel::GetCockpitSessionText() const
{
	const FString Session = CockpitOverview.Session.IsEmpty()
		? (CurrentSessionName.IsEmpty() ? FString(TEXT("default")) : CurrentSessionName)
		: CockpitOverview.Session;
	return FText::Format(LOCTEXT("CockpitSessionText", "Session: {0}"), FText::FromString(Session));
}

FText SMCPChatPanel::GetCockpitBlockersText() const
{
	if (!CockpitOverview.bLoaded)
	{
		return LOCTEXT("CockpitBlockersLoading", "Blockers: loading");
	}
	if (CockpitOverview.BlockingGateCount <= 0)
	{
		return LOCTEXT("CockpitBlockersClear", "Blockers: clear");
	}
	return FText::Format(
		LOCTEXT("CockpitBlockersText", "Blockers ({0}): {1}"),
		FText::AsNumber(CockpitOverview.BlockingGateCount),
		FText::FromString(CockpitOverview.BlockersSummary)
	);
}

FText SMCPChatPanel::GetCockpitQueueText() const
{
	if (!CockpitOverview.bLoaded)
	{
		return LOCTEXT("CockpitQueueLoading", "Queue: loading");
	}
	return FText::Format(
		LOCTEXT("CockpitQueueText", "Queue: {0}"),
		FText::FromString(CockpitOverview.QueueSummary)
	);
}

FText SMCPChatPanel::GetCockpitQueueActionsText() const
{
	if (!CockpitOverview.bLoaded)
	{
		return LOCTEXT("CockpitActionsLoading", "Queued Actions: loading");
	}
	return FText::Format(
		LOCTEXT("CockpitActionsText", "Queued Actions: {0}"),
		FText::FromString(CockpitOverview.QueueActionsSummary.IsEmpty() ? FString(TEXT("none")) : CockpitOverview.QueueActionsSummary)
	);
}

FText SMCPChatPanel::GetCockpitEvidenceText() const
{
	if (!CockpitOverview.bLoaded)
	{
		return LOCTEXT("CockpitEvidenceLoading", "Evidence: loading");
	}
	if (!CockpitOverview.EvidenceRecordingSummary.IsEmpty())
	{
		return FText::Format(
			LOCTEXT("CockpitEvidenceTextWithRecording", "Evidence: {0} | Record: {1}"),
			FText::FromString(CockpitOverview.EvidenceSummary),
			FText::FromString(CockpitOverview.EvidenceRecordingSummary)
		);
	}
	return FText::Format(
		LOCTEXT("CockpitEvidenceText", "Evidence: {0}"),
		FText::FromString(CockpitOverview.EvidenceSummary)
	);
}

FText SMCPChatPanel::GetCockpitEvidenceTimelineText() const
{
	if (!CockpitOverview.bLoaded)
	{
		return LOCTEXT("CockpitEvidenceTimelineLoading", "Evidence Timeline: loading");
	}
	return FText::Format(
		LOCTEXT("CockpitEvidenceTimelineText", "Evidence Timeline: {0}"),
		FText::FromString(CockpitOverview.EvidenceTimelineSummary.IsEmpty() ? FString(TEXT("none")) : CockpitOverview.EvidenceTimelineSummary)
	);
}

FText SMCPChatPanel::GetCockpitRecoveryText() const
{
	if (!CockpitOverview.bLoaded)
	{
		return LOCTEXT("CockpitRecoveryLoading", "Recovery: loading");
	}
	if (!CockpitOverview.HudBlueprintMutationSummary.IsEmpty())
	{
		return FText::Format(
			LOCTEXT("CockpitRecoveryWithBlueprintText", "Safe Step: {0} | Recovery: {1} | Assets: {2} | Policy: {3} | BP: {4}"),
			FText::FromString(CockpitOverview.NextSafeStepSummary.IsEmpty() ? FString(TEXT("none")) : CockpitOverview.NextSafeStepSummary),
			FText::FromString(CockpitOverview.FailureTriageSummary.IsEmpty() ? FString(TEXT("clear")) : CockpitOverview.FailureTriageSummary),
			FText::FromString(CockpitOverview.AssetQualitySummary.IsEmpty() ? FString(TEXT("none")) : CockpitOverview.AssetQualitySummary),
			FText::FromString(CockpitOverview.ReadinessPolicySummary.IsEmpty() ? FString(TEXT("none")) : CockpitOverview.ReadinessPolicySummary),
			FText::FromString(CockpitOverview.HudBlueprintMutationSummary)
		);
	}
	return FText::Format(
		LOCTEXT("CockpitRecoveryText", "Safe Step: {0} | Recovery: {1} | Assets: {2} | Policy: {3}"),
		FText::FromString(CockpitOverview.NextSafeStepSummary.IsEmpty() ? FString(TEXT("none")) : CockpitOverview.NextSafeStepSummary),
		FText::FromString(CockpitOverview.FailureTriageSummary.IsEmpty() ? FString(TEXT("clear")) : CockpitOverview.FailureTriageSummary),
		FText::FromString(CockpitOverview.AssetQualitySummary.IsEmpty() ? FString(TEXT("none")) : CockpitOverview.AssetQualitySummary),
		FText::FromString(CockpitOverview.ReadinessPolicySummary.IsEmpty() ? FString(TEXT("none")) : CockpitOverview.ReadinessPolicySummary)
	);
}

FText SMCPChatPanel::GetCockpitHudSummaryText() const
{
	if (!CockpitOverview.bLoaded)
	{
		return LOCTEXT("CockpitHudSummaryLoading", "HUD: loading");
	}
	if (!CockpitOverview.bHasHudSummary)
	{
		return FText::Format(
			LOCTEXT("CockpitHudSummaryFallback", "HUD: {0} | {1}"),
			GetCockpitSessionText(),
			GetCockpitBlockersText()
		);
	}
	if (!CockpitOverview.HudAnimationSummary.IsEmpty())
	{
		return FText::Format(
			LOCTEXT("CockpitHudSummaryWithAnimationText", "HUD: {0} | {1} | {2} | {3} | Anim: {4} | {5}"),
			FText::FromString(CockpitOverview.HudStateSummary.IsEmpty() ? FString(TEXT("state unknown")) : CockpitOverview.HudStateSummary),
			FText::FromString(CockpitOverview.HudReadinessSummary.IsEmpty() ? FString(TEXT("readiness unknown")) : CockpitOverview.HudReadinessSummary),
			FText::FromString(CockpitOverview.HudFeatureSummary.IsEmpty() ? FString(TEXT("feature none")) : CockpitOverview.HudFeatureSummary),
			FText::FromString(CockpitOverview.HudNextStepSummary.IsEmpty() ? FString(TEXT("next step none")) : CockpitOverview.HudNextStepSummary),
			FText::FromString(CockpitOverview.HudAnimationSummary),
			FText::FromString(CockpitOverview.HudEvidenceSummary.IsEmpty() ? FString(TEXT("evidence none")) : CockpitOverview.HudEvidenceSummary)
		);
	}
	return FText::Format(
		LOCTEXT("CockpitHudSummaryText", "HUD: {0} | {1} | {2} | {3} | {4}"),
		FText::FromString(CockpitOverview.HudStateSummary.IsEmpty() ? FString(TEXT("state unknown")) : CockpitOverview.HudStateSummary),
		FText::FromString(CockpitOverview.HudReadinessSummary.IsEmpty() ? FString(TEXT("readiness unknown")) : CockpitOverview.HudReadinessSummary),
		FText::FromString(CockpitOverview.HudFeatureSummary.IsEmpty() ? FString(TEXT("feature none")) : CockpitOverview.HudFeatureSummary),
		FText::FromString(CockpitOverview.HudNextStepSummary.IsEmpty() ? FString(TEXT("next step none")) : CockpitOverview.HudNextStepSummary),
		FText::FromString(CockpitOverview.HudEvidenceSummary.IsEmpty() ? FString(TEXT("evidence none")) : CockpitOverview.HudEvidenceSummary)
	);
}

FText SMCPChatPanel::GetCockpitActionText() const
{
	if (!CockpitOverview.bLoaded)
	{
		return LOCTEXT("CockpitActionLoading", "Next: refresh");
	}
	if (!CockpitOverview.HudOperatorHandoffSummary.IsEmpty())
	{
		return FText::Format(
			LOCTEXT("CockpitActionWithHandoffText", "Next: {0} | Handoff: {1}"),
			FText::FromString(CockpitOverview.SuggestedAction.IsEmpty() ? FString(TEXT("review session")) : CockpitOverview.SuggestedAction),
			FText::FromString(CockpitOverview.HudOperatorHandoffSummary)
		);
	}
	return FText::Format(
		LOCTEXT("CockpitActionText", "Next: {0}"),
		FText::FromString(CockpitOverview.SuggestedAction.IsEmpty() ? FString(TEXT("review session")) : CockpitOverview.SuggestedAction)
	);
}

FText SMCPChatPanel::GetCockpitWorkflowActionsText() const
{
	if (CockpitOverview.WorkflowActionCount > 0)
	{
		return FText::Format(
			LOCTEXT("CockpitWorkflowActionsWithCount", "Actions ({0})"),
			FText::AsNumber(CockpitOverview.EnabledWorkflowActionCount)
		);
	}
	return LOCTEXT("CockpitWorkflowActions", "Actions");
}

FText SMCPChatPanel::GetCockpitWorkflowActionsTooltip() const
{
	if (CockpitOverview.WorkflowActionCount > 0)
	{
		return FText::Format(
			LOCTEXT("CockpitWorkflowActionsTooltipWithCount", "Open {0} enabled of {1} IDE Companion workflow actions"),
			FText::AsNumber(CockpitOverview.EnabledWorkflowActionCount),
			FText::AsNumber(CockpitOverview.WorkflowActionCount)
		);
	}
	return LOCTEXT("CockpitWorkflowActionsTooltip", "Open IDE Companion workflow actions");
}

FString SMCPChatPanel::GetOpenLevelReference() const
{
	const FString LevelName = GetOpenLevelName();
	return FString::Printf(TEXT("@level:%s"), LevelName.IsEmpty() ? TEXT("none") : *LevelName);
}

FString SMCPChatPanel::GetSelectedActorReference() const
{
	const FString ActorName = GetSelectedActorName();
	return FString::Printf(TEXT("@actor:%s"), ActorName.IsEmpty() ? TEXT("none") : *ActorName);
}

FString SMCPChatPanel::GetDirtyAssetsReference() const
{
	return FString::Printf(TEXT("@dirty-assets:%d"), CountDirtyPackages());
}

FString SMCPChatPanel::GetLastCompileReference() const
{
	return FString::Printf(TEXT("@last-compile:%s"), LastCompileStatus.IsEmpty() ? TEXT("unknown") : *LastCompileStatus);
}

FString SMCPChatPanel::GetServerReference() const
{
	return TEXT("@server:sse:8000");
}

FString SMCPChatPanel::GetOpenLevelName() const
{
	if (!GEditor)
	{
		return FString();
	}

	const UWorld* World = GEditor->GetEditorWorldContext().World();
	if (!World || !World->GetOutermost())
	{
		return FString();
	}

	return FPackageName::GetShortName(World->GetOutermost()->GetName());
}

FString SMCPChatPanel::GetSelectedActorName() const
{
	if (!GEditor)
	{
		return FString();
	}

	USelection* SelectedActors = GEditor->GetSelectedActors();
	if (!SelectedActors)
	{
		return FString();
	}

	for (FSelectionIterator Iterator(*SelectedActors); Iterator; ++Iterator)
	{
		if (const AActor* Actor = Cast<AActor>(*Iterator))
		{
			return Actor->GetName();
		}
	}

	return FString();
}

int32 SMCPChatPanel::CountDirtyPackages() const
{
	int32 DirtyPackages = 0;
	for (TObjectIterator<UPackage> Iterator; Iterator; ++Iterator)
	{
		const UPackage* Package = *Iterator;
		if (!Package || Package->HasAnyFlags(RF_Transient))
		{
			continue;
		}

		if (Package->IsDirty())
		{
			++DirtyPackages;
		}
	}
	return DirtyPackages;
}

void SMCPChatPanel::ExtractToolCallsFromMessage(const FChatMessage& ChatMessage, TArray<FToolCallView>& OutToolCalls) const
{
	const FString Text = ChatMessage.Message.TrimStartAndEnd();
	if (Text.IsEmpty() || (!Text.StartsWith(TEXT("{")) && !Text.StartsWith(TEXT("["))))
	{
		return;
	}

	TSharedPtr<FJsonValue> RootValue;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Text);
	if (!FJsonSerializer::Deserialize(Reader, RootValue) || !RootValue.IsValid())
	{
		return;
	}

	if (RootValue->Type == EJson::Object)
	{
		FToolCallView ToolCall;
		if (TryBuildToolCallFromJsonObject(RootValue->AsObject(), ChatMessage.MessageId, ToolCall))
		{
			OutToolCalls.Add(ToolCall);
		}
		return;
	}

	if (RootValue->Type == EJson::Array)
	{
		for (const TSharedPtr<FJsonValue>& Item : RootValue->AsArray())
		{
			if (!Item.IsValid() || Item->Type != EJson::Object)
			{
				continue;
			}

			FToolCallView ToolCall;
			if (TryBuildToolCallFromJsonObject(Item->AsObject(), ChatMessage.MessageId, ToolCall))
			{
				OutToolCalls.Add(ToolCall);
			}
		}
	}
}

void SMCPChatPanel::ExtractEvidenceFromJsonObject(const TSharedPtr<FJsonObject>& Object, FToolCallView& OutToolCall) const
{
	if (!Object.IsValid())
	{
		return;
	}

	for (const TPair<FString, TSharedPtr<FJsonValue>>& Field : Object->Values)
	{
		ExtractEvidenceFromJsonValue(Field.Key, Field.Value, OutToolCall);
	}
}

void SMCPChatPanel::ExtractEvidenceFromJsonValue(const FString& FieldName, const TSharedPtr<FJsonValue>& Value, FToolCallView& OutToolCall) const
{
	if (!Value.IsValid())
	{
		return;
	}

	const FString LowerField = FieldName.ToLower();
	const bool bScreenshotField = LowerField.Contains(TEXT("screenshot")) ||
		LowerField.Contains(TEXT("thumbnail")) ||
		LowerField.Contains(TEXT("viewport_image")) ||
		LowerField.Contains(TEXT("image_path"));
	const bool bLogField = LowerField.Contains(TEXT("log_tail")) ||
		LowerField.Contains(TEXT("log_snippet")) ||
		LowerField.Contains(TEXT("log_excerpt")) ||
		LowerField == TEXT("log");
	const bool bPieField = LowerField.Contains(TEXT("pie")) ||
		LowerField.Contains(TEXT("play_in_editor"));

	if (Value->Type == EJson::String)
	{
		FString StringValue = Value->AsString().TrimStartAndEnd();
		if (StringValue.IsEmpty())
		{
			return;
		}

		const FString LowerValue = StringValue.ToLower();
		const bool bImageValue = LowerValue.EndsWith(TEXT(".png")) ||
			LowerValue.EndsWith(TEXT(".jpg")) ||
			LowerValue.EndsWith(TEXT(".jpeg")) ||
			LowerValue.EndsWith(TEXT(".bmp"));
		if (bScreenshotField || bImageValue)
		{
			OutToolCall.ScreenshotPaths.AddUnique(StringValue);
		}
		else if (bPieField)
		{
			OutToolCall.PieResults.AddUnique(TruncateForCard(StringValue, 360));
		}
		else if (bLogField)
		{
			OutToolCall.LogSnippets.AddUnique(TruncateForCard(StringValue, 480));
		}
		return;
	}

	if (Value->Type == EJson::Object)
	{
		ExtractEvidenceFromJsonObject(Value->AsObject(), OutToolCall);
		if (bPieField)
		{
			OutToolCall.PieResults.AddUnique(TruncateForCard(JsonValueToString(Value), 360));
		}
		return;
	}

	if (Value->Type == EJson::Array)
	{
		TArray<FString> EvidenceParts;
		for (const TSharedPtr<FJsonValue>& Item : Value->AsArray())
		{
			if (!Item.IsValid())
			{
				continue;
			}

			ExtractEvidenceFromJsonValue(FieldName, Item, OutToolCall);
			if ((bLogField || bPieField) && Item->Type != EJson::Object && Item->Type != EJson::Array)
			{
				EvidenceParts.Add(JsonValueToString(Item));
			}
		}

		if (!EvidenceParts.IsEmpty())
		{
			const FString JoinedEvidence = TruncateForCard(FString::Join(EvidenceParts, LINE_TERMINATOR), bLogField ? 480 : 360);
			if (bLogField)
			{
				OutToolCall.LogSnippets.AddUnique(JoinedEvidence);
			}
			else if (bPieField)
			{
				OutToolCall.PieResults.AddUnique(JoinedEvidence);
			}
		}
		return;
	}

	if (bPieField)
	{
		OutToolCall.PieResults.AddUnique(TruncateForCard(JsonValueToString(Value), 360));
	}
	else if (bLogField)
	{
		OutToolCall.LogSnippets.AddUnique(TruncateForCard(JsonValueToString(Value), 480));
	}
}

bool SMCPChatPanel::TryBuildToolCallFromJsonObject(const TSharedPtr<FJsonObject>& Object, const FString& MessageId, FToolCallView& OutToolCall) const
{
	if (!Object.IsValid())
	{
		return false;
	}

	FString ToolName = GetStringField(Object, TEXT("tool"));
	if (ToolName.IsEmpty())
	{
		ToolName = GetStringField(Object, TEXT("tool_name"));
	}
	if (ToolName.IsEmpty())
	{
		ToolName = GetStringField(Object, TEXT("name"));
	}

	const TSharedPtr<FJsonObject>* InvocationObject = nullptr;
	if (ToolName.IsEmpty() && Object->TryGetObjectField(TEXT("tool_call"), InvocationObject) && InvocationObject && InvocationObject->IsValid())
	{
		return TryBuildToolCallFromJsonObject(*InvocationObject, MessageId, OutToolCall);
	}

	if (ToolName.IsEmpty())
	{
		return false;
	}

	FString Status = GetStringField(Object, TEXT("status"));
	if (Status.IsEmpty())
	{
		Status = GetStringField(Object, TEXT("stage"));
	}

	bool bSuccess = false;
	const bool bHasSuccess = Object->TryGetBoolField(TEXT("success"), bSuccess);
	bool bError = Status.Contains(TEXT("error"), ESearchCase::IgnoreCase) || Status.Contains(TEXT("fail"), ESearchCase::IgnoreCase);
	if (bHasSuccess)
	{
		bError = !bSuccess;
		if (Status.IsEmpty())
		{
			Status = bSuccess ? TEXT("success") : TEXT("error");
		}
	}
	if (Status.IsEmpty())
	{
		Status = TEXT("pending");
	}

	const TSharedPtr<FJsonObject>* ArgsObject = nullptr;
	FString ArgsSummary = TEXT("(none)");
	if (Object->TryGetObjectField(TEXT("args"), ArgsObject) && ArgsObject && ArgsObject->IsValid())
	{
		ArgsSummary = SummarizeJsonObject(*ArgsObject);
	}
	else if (Object->TryGetObjectField(TEXT("arguments"), ArgsObject) && ArgsObject && ArgsObject->IsValid())
	{
		ArgsSummary = SummarizeJsonObject(*ArgsObject);
	}
	else if (const TSharedPtr<FJsonValue> ArgsValue = Object->TryGetField(TEXT("args")); ArgsValue.IsValid())
	{
		ArgsSummary = SummarizeJsonValue(ArgsValue);
	}

	const TSharedPtr<FJsonObject>* OutputsObject = nullptr;
	FString ResultSummary = GetStringField(Object, TEXT("message"));
	if (ResultSummary.IsEmpty() && Object->TryGetObjectField(TEXT("outputs"), OutputsObject) && OutputsObject && OutputsObject->IsValid())
	{
		ResultSummary = SummarizeJsonObject(*OutputsObject);
	}
	else if (const TSharedPtr<FJsonValue> OutputValue = Object->TryGetField(TEXT("result")); ResultSummary.IsEmpty() && OutputValue.IsValid())
	{
		ResultSummary = SummarizeJsonValue(OutputValue);
	}
	if (ResultSummary.IsEmpty())
	{
		ResultSummary = TEXT("(no structured result yet)");
	}

	const TArray<TSharedPtr<FJsonValue>>* LogTailArray = nullptr;
	FString LogTail = TEXT("(empty)");
	if (Object->TryGetArrayField(TEXT("log_tail"), LogTailArray) && LogTailArray)
	{
		TArray<FString> LogLines;
		for (const TSharedPtr<FJsonValue>& LogValue : *LogTailArray)
		{
			LogLines.Add(SummarizeJsonValue(LogValue, 240));
		}
		LogTail = FString::Join(LogLines, LINE_TERMINATOR);
	}

	bool bHasProgress = false;
	float ProgressFraction = 0.0f;
	const auto TryReadProgress = [&bHasProgress, &ProgressFraction](const TSharedPtr<FJsonObject>& Candidate)
	{
		if (!Candidate.IsValid() || bHasProgress)
		{
			return;
		}

		double ProgressValue = 0.0;
		if (Candidate->TryGetNumberField(TEXT("progress"), ProgressValue))
		{
			ProgressFraction = ProgressValue > 1.0 ? static_cast<float>(ProgressValue / 100.0) : static_cast<float>(ProgressValue);
			ProgressFraction = FMath::Clamp(ProgressFraction, 0.0f, 1.0f);
			bHasProgress = true;
			return;
		}

		const TSharedPtr<FJsonObject>* NestedTask = nullptr;
		if (Candidate->TryGetObjectField(TEXT("task"), NestedTask) && NestedTask && NestedTask->IsValid())
		{
			double NestedProgress = 0.0;
			if ((*NestedTask)->TryGetNumberField(TEXT("progress"), NestedProgress))
			{
				ProgressFraction = NestedProgress > 1.0 ? static_cast<float>(NestedProgress / 100.0) : static_cast<float>(NestedProgress);
				ProgressFraction = FMath::Clamp(ProgressFraction, 0.0f, 1.0f);
				bHasProgress = true;
			}
		}
	};

	if (ToolName.Contains(TEXT("tripo"), ESearchCase::IgnoreCase))
	{
		TryReadProgress(Object);
		if (OutputsObject && OutputsObject->IsValid())
		{
			TryReadProgress(*OutputsObject);
		}
		const TSharedPtr<FJsonObject>* ResultObject = nullptr;
		if (Object->TryGetObjectField(TEXT("result"), ResultObject) && ResultObject && ResultObject->IsValid())
		{
			TryReadProgress(*ResultObject);
		}
	}

	OutToolCall.MessageId = MessageId;
	OutToolCall.ToolName = ToolName;
	OutToolCall.ArgsSummary = ArgsSummary;
	OutToolCall.Status = Status;
	OutToolCall.ResultSummary = TruncateForCard(ResultSummary, 240);
	OutToolCall.DetailJson = JsonObjectToString(Object);
	OutToolCall.LogTail = LogTail;
	OutToolCall.ProgressFraction = ProgressFraction;
	OutToolCall.bHasProgress = bHasProgress;
	OutToolCall.bError = bError;
	ExtractEvidenceFromJsonObject(Object, OutToolCall);
	if (!LogTail.IsEmpty() && LogTail != TEXT("(empty)"))
	{
		OutToolCall.LogSnippets.AddUnique(TruncateForCard(LogTail, 480));
	}
	return true;
}

FString SMCPChatPanel::JsonObjectToString(const TSharedPtr<FJsonObject>& Object) const
{
	if (!Object.IsValid())
	{
		return TEXT("{}");
	}

	FString Text;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
	FJsonSerializer::Serialize(Object.ToSharedRef(), Writer);
	return Text;
}

FString SMCPChatPanel::JsonValueToString(const TSharedPtr<FJsonValue>& Value) const
{
	if (!Value.IsValid())
	{
		return TEXT("");
	}

	FString Text;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Text);
	FJsonSerializer::Serialize(Value, TEXT(""), Writer);
	return Text;
}

FString SMCPChatPanel::SummarizeJsonObject(const TSharedPtr<FJsonObject>& Object, int32 MaxChars) const
{
	return TruncateForCard(JsonObjectToString(Object), MaxChars);
}

FString SMCPChatPanel::SummarizeJsonValue(const TSharedPtr<FJsonValue>& Value, int32 MaxChars) const
{
	return TruncateForCard(JsonValueToString(Value), MaxChars);
}

FString SMCPChatPanel::TruncateForCard(const FString& Text, int32 MaxChars) const
{
	FString Compact = Text;
	Compact.ReplaceInline(TEXT("\r"), TEXT(" "));
	Compact.ReplaceInline(TEXT("\n"), TEXT(" "));
	Compact = Compact.TrimStartAndEnd();
	if (Compact.Len() > MaxChars)
	{
		return Compact.Left(MaxChars - 3) + TEXT("...");
	}
	return Compact;
}

void SMCPChatPanel::SetStatus(const FText& Text, const FSlateColor& Color)
{
	if (StatusText.IsValid())
	{
		StatusText->SetText(Text);
		StatusText->SetColorAndOpacity(Color);
	}
}

void SMCPChatPanel::UpdateLastAgentTimestamp(const TArray<FChatMessage>& InMessages)
{
	for (const FChatMessage& ChatMessage : InMessages)
	{
		if (ChatMessage.Sender.Equals(TEXT("agent"), ESearchCase::IgnoreCase) && !ChatMessage.Timestamp.IsEmpty())
		{
			LastAgentPollTimestamp = ChatMessage.Timestamp;
		}
	}

	if (LastAgentPollTimestamp.IsEmpty())
	{
		LastAgentPollTimestamp = MakeCurrentTimestamp();
	}
}

FString SMCPChatPanel::MakeLocalMessageId() const
{
	return FString::Printf(TEXT("local-%s"), *FGuid::NewGuid().ToString(EGuidFormats::DigitsWithHyphensLower));
}

FString SMCPChatPanel::NormaliseSender(const FString& Sender) const
{
	if (Sender.Equals(TEXT("human"), ESearchCase::IgnoreCase) || Sender.Equals(TEXT("user"), ESearchCase::IgnoreCase))
	{
		return TEXT("user");
	}
	if (Sender.Equals(TEXT("tool"), ESearchCase::IgnoreCase))
	{
		return TEXT("tool");
	}
	return TEXT("agent");
}

FText SMCPChatPanel::GetSenderLabel(const FString& Sender) const
{
	const FString NormalisedSender = NormaliseSender(Sender);
	if (NormalisedSender == TEXT("user"))
	{
		return LOCTEXT("HumanSender", "User");
	}
	if (NormalisedSender == TEXT("tool"))
	{
		return LOCTEXT("ToolSender", "Tool");
	}
	return LOCTEXT("AgentSender", "Agent");
}

FSlateColor SMCPChatPanel::GetMessageColor(const FString& Sender) const
{
	const FString NormalisedSender = NormaliseSender(Sender);
	if (NormalisedSender == TEXT("user"))
	{
		return HumanMessageColor;
	}
	if (NormalisedSender == TEXT("tool"))
	{
		return ToolMessageColor;
	}
	return AgentMessageColor;
}

EVisibility SMCPChatPanel::GetToolPaletteVisibility() const
{
	return bToolPaletteVisible ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SMCPChatPanel::GetCommandPaletteVisibility() const
{
	return bCommandPaletteVisible ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SMCPChatPanel::GetGenerativeSettingsVisibility() const
{
	return bGenerativeSettingsVisible ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SMCPChatPanel::GetOnboardingVisibility() const
{
	return bOnboardingVisible ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SMCPChatPanel::GetSamplePromptsVisibility() const
{
	return bSamplePromptsVisible ? EVisibility::Visible : EVisibility::Collapsed;
}

FText SMCPChatPanel::GetToolPaletteToggleText() const
{
	return bToolPaletteVisible ? LOCTEXT("HideToolPalette", "Hide Tools") : LOCTEXT("ShowToolPalette", "Show Tools");
}

FText SMCPChatPanel::GetGenerativeSettingsToggleText() const
{
	return bGenerativeSettingsVisible ? LOCTEXT("HideGenerativeSettings", "Hide Generate") : LOCTEXT("ShowGenerativeSettings", "Generate Settings");
}

FText SMCPChatPanel::GetGenerativeAuthStatusText() const
{
	return FText::Format(
		LOCTEXT("GenerativeAuthStatus", "Tripo auth: {0} | Uthana auth: {1}"),
		FText::FromString(GetGenerativeApiKeySource()),
		FText::FromString(GetGenerativeUthanaApiKeySource())
	);
}

FText SMCPChatPanel::GetGenerativeBudgetText() const
{
	return FText::Format(
		LOCTEXT("GenerativeBudgetStatus", "Generative Credits: API {0} available / {1} frozen | Local budget: {2}/session | Pending spend: {3} | Confirmed: {4} | Output: {5} | Smart Mesh: on"),
		FText::FromString(GenerativeApiWalletBalance),
		FText::FromString(GenerativeApiWalletFrozen),
		FText::AsNumber(GenerativeSessionCreditBudget),
		FText::AsNumber(GenerativePendingSpendCredits),
		bGenerativeSpendConfirmed ? LOCTEXT("GenerativeSpendYes", "yes") : LOCTEXT("GenerativeSpendNo", "no"),
		FText::FromString(GenerativeOutputFolder)
	);
}

FText SMCPChatPanel::GetGenerativeApiWalletText() const
{
	return FText::Format(
		LOCTEXT("GenerativeApiWalletStatus", "Tripo API Wallet: {0} credits available | Frozen: {1} | Status: {2}"),
		FText::FromString(GenerativeApiWalletBalance),
		FText::FromString(GenerativeApiWalletFrozen),
		FText::FromString(GenerativeApiWalletStatus)
	);
}

FText SMCPChatPanel::GetOnboardingStepTitle() const
{
	return FText::Format(LOCTEXT("OnboardingStepTitle", "MCP Chat Tour {0}/4"), FText::AsNumber(OnboardingStepIndex + 1));
}

FText SMCPChatPanel::GetOnboardingStepText() const
{
	switch (OnboardingStepIndex)
	{
	case 0:
		return LOCTEXT("OnboardingConnectServer", "Connect server: confirm the endpoint is reachable and the footer reports latency, tool count, KB docs, and queue depth.");
	case 1:
		return LOCTEXT("OnboardingAskQuestion", "Ask a question: type a short request in the composer or insert a sample prompt, then send it to the agent.");
	case 2:
		return LOCTEXT("OnboardingDragAsset", "Drag an asset: drop Content Browser assets, Outliner actors, or files into the composer to create typed references.");
	default:
		return LOCTEXT("OnboardingRunWorkflow", "Run a workflow: choose a sample such as Health System or Build Slime Enemy, then let the tool cards and inline evidence show progress.");
	}
}

FText SMCPChatPanel::GetOnboardingNextText() const
{
	return OnboardingStepIndex >= 3 ? LOCTEXT("FinishOnboarding", "Finish") : LOCTEXT("NextOnboarding", "Next");
}

FText SMCPChatPanel::GetSamplePromptsToggleText() const
{
	return bSamplePromptsVisible ? LOCTEXT("HideSamplePrompts", "Hide Samples") : LOCTEXT("ShowSamplePrompts", "Sample Prompts");
}

FText SMCPChatPanel::GetStatusFooterText() const
{
	return FText::Format(
		LOCTEXT("StatusFooter", "Latency: {0} ms | Tools: {1} | KB docs: {2} | Queue: {3} | Metrics: {4}"),
		FText::AsNumber(LastServerLatencyMs),
		FText::AsNumber(ToolCount),
		FText::AsNumber(KbDocCount),
		FText::AsNumber(ActiveRequests.Num()),
		bTelemetryEnabled ? LOCTEXT("MetricsOn", "On") : LOCTEXT("MetricsOff", "Off")
	);
}

FText SMCPChatPanel::GetTelemetryToggleText() const
{
	return bTelemetryEnabled ? LOCTEXT("DisableMetrics", "Disable Metrics") : LOCTEXT("EnableMetrics", "Enable Metrics");
}

FString SMCPChatPanel::BuildSessionQueryParam() const
{
	return TEXT("&session=") + FGenericPlatformHttp::UrlEncode(CurrentSessionName.IsEmpty() ? TEXT("default") : CurrentSessionName);
}

FString SMCPChatPanel::BuildNewSessionName() const
{
	return FString::Printf(TEXT("Session-%s"), *FDateTime::UtcNow().ToString(TEXT("%Y%m%d-%H%M%S")));
}

FString SMCPChatPanel::BuildRenamedSessionName() const
{
	return FString::Printf(TEXT("%s-renamed-%s"), *CurrentSessionName, *FDateTime::UtcNow().ToString(TEXT("%H%M%S")));
}

FString SMCPChatPanel::BuildToolPromptTemplate(const FToolPaletteEntry& Tool) const
{
	FString Template = FString::Printf(
		TEXT("Use MCP tool `%s` from `%s`.\n"),
		*Tool.Name,
		*Tool.Category
	);

	if (!Tool.Parameters.IsEmpty())
	{
		Template += TEXT("Parameters:\n");
		for (const FString& Parameter : Tool.Parameters)
		{
			Template += FString::Printf(TEXT("- %s: <%s>\n"), *Parameter, *Parameter);
		}
	}
	else
	{
		Template += TEXT("Parameters: none\n");
	}

	Template += TEXT("Return the StructuredResult and summarize warnings/errors.");
	return Template;
}

FString SMCPChatPanel::BuildGenerateAssetToolCallPrompt() const
{
	const FString Mode = GetGenerateAssetMode();
	const FString SafePrompt = GenerateAssetPrompt.Replace(TEXT("\""), TEXT("'"));
	const FString SafeTexturePrompt = (GenerateAssetTexturePrompt.IsEmpty() ? GenerateAssetPrompt : GenerateAssetTexturePrompt).Replace(TEXT("\""), TEXT("'"));
	const FString SafeReferences = GenerateAssetReferenceImages.Replace(TEXT("\""), TEXT("'"));
	const FString SafeTaskId = GenerateAssetExistingTaskId.Replace(TEXT("\""), TEXT("'"));
	const FString SafePaintViewLabel = (GenerateAssetPaintViewLabel.IsEmpty() ? FString(TEXT("source_view")) : GenerateAssetPaintViewLabel).Replace(TEXT("\""), TEXT("'"));
	const FString SafePaintedViewLabel = FString::Printf(TEXT("%s_painted"), *SafePaintViewLabel);
	const FString SafePaintPassLabel = FString::Printf(TEXT("%s_pass"), *SafePaintViewLabel);
	const FString SafeSession = CurrentSessionName.IsEmpty() ? FString(TEXT("default")) : CurrentSessionName;
	const FString SafeAssetName = GenerateAssetName.Replace(TEXT("\""), TEXT(""));
	const TCHAR* ConfirmSpendText = bGenerativeSpendConfirmed ? TEXT("true") : TEXT("false");
	const TCHAR* UploadSnapshotText = bGenerateAssetUploadPaintSnapshot ? TEXT("true") : TEXT("false");
	const float SafeBrushStrength = FMath::Clamp(GenerateAssetPaintBrushStrength, 0.0f, 1.0f);
	const float SafePaintBlend = FMath::Clamp(GenerateAssetPaintBlend, 0.0f, 1.0f);
	const float SafeBrushRadius = FMath::Clamp(GenerateAssetPaintBrushRadius, 0.01f, 1.0f);
	const FString SafeBlendMode = FString::Printf(TEXT("soft blend %.2f with brush radius %.2f"), SafePaintBlend, SafeBrushRadius);
	const FString SafePaintNotes = FString::Printf(TEXT("rotate the model between strokes; brush_radius %.2f; blend %.2f; capture label %s"), SafeBrushRadius, SafePaintBlend, *SafePaintViewLabel);

	if (Mode == TEXT("image_to_model") || Mode == TEXT("image"))
	{
		return FString::Printf(
			TEXT("Use MCP tool `gen_tripo_image_to_model` to generate a Smart Mesh asset from this reference image, then show progress with `gen_tripo_wait_for_task` in the chat tool card.\n")
			TEXT("Reference image path/URL/token: \"%s\"\n")
			TEXT("Parameters:\n")
			TEXT("- prompt context: \"%s\"\n")
			TEXT("- model_version: \"%s\"\n")
			TEXT("- texture: true\n")
			TEXT("- pbr: true\n")
			TEXT("- texture_quality: \"%s\"\n")
			TEXT("- smart_low_poly: true\n")
			TEXT("- face_limit: 12000\n")
			TEXT("- session_name: \"%s\"\n")
			TEXT("- confirm_spend: %s\n")
			TEXT("Choose exactly one image_path, image_url, or file_token from the reference, then after the task succeeds call `gen_tripo_import_to_project` with content_path \"%s\" and asset_name \"%s\"."),
			*SafeReferences,
			*SafePrompt,
			*GenerativeModelVersion,
			*GenerativeTextureQuality,
			*SafeSession,
			ConfirmSpendText,
			*GenerativeOutputFolder,
			*SafeAssetName
		);
	}

	if (Mode == TEXT("multiview_to_model") || Mode == TEXT("multi_image_to_model") || Mode == TEXT("multiview"))
	{
		return FString::Printf(
			TEXT("Use MCP tool `gen_tripo_multiview_to_model` to generate a Smart Mesh asset from 2-4 ordered reference views, then show progress with `gen_tripo_wait_for_task` in the chat tool card.\n")
			TEXT("Ordered views, front/left/back/right when available: \"%s\"\n")
			TEXT("Parameters:\n")
			TEXT("- prompt context: \"%s\"\n")
			TEXT("- model_version: \"%s\"\n")
			TEXT("- texture: true\n")
			TEXT("- pbr: true\n")
			TEXT("- texture_quality: \"%s\"\n")
			TEXT("- smart_low_poly: true\n")
			TEXT("- face_limit: 12000\n")
			TEXT("- session_name: \"%s\"\n")
			TEXT("- confirm_spend: %s\n")
			TEXT("Build the `images` array from the ordered views, using image_path, image_url, or file_token for each entry. After the task succeeds, call `gen_tripo_import_to_project` with content_path \"%s\" and asset_name \"%s\"."),
			*SafeReferences,
			*SafePrompt,
			*GenerativeModelVersion,
			*GenerativeTextureQuality,
			*SafeSession,
			ConfirmSpendText,
			*GenerativeOutputFolder,
			*SafeAssetName
		);
	}

	if (Mode == TEXT("texture_paint") || Mode == TEXT("texture") || Mode == TEXT("paint"))
	{
		return FString::Printf(
			TEXT("Use the Texture/Paint workspace flow for an existing Tripo model task.\n")
			TEXT("1. Call `gen_prepare_texture_paint_session` with model_task_id \"%s\", texture_prompt \"%s\", texture_reference_image \"%s\", view_angle \"%s\", brush_strength %.2f, blend_mode \"%s\", paint_notes \"%s\", output_folder \"%s\", save_asset_name \"%s\", and session_name \"%s\".\n")
			TEXT("2. Call `gen_capture_texture_paint_snapshot` with the same session_name/model_task_id, label \"%s\", resolution [1024, 1024], and upload_to_tripo %s to capture the current mesh viewport before generation.\n")
			TEXT("3. After user spend approval, call `gen_tripo_texture_model` with task_id \"%s\", texture_prompt from prepare_result.outputs.tripo_texture_prompt, texture_quality \"%s\", session_name \"%s\", and confirm_spend %s. If the prepare result is unavailable, use texture_prompt \"%s\".\n")
			TEXT("4. Show progress with `gen_tripo_wait_for_task`, then call `gen_tripo_import_to_project` for the textured result.\n")
			TEXT("5. After the user inspects the painted/blended model in the viewport, call `gen_capture_texture_paint_snapshot` again with label \"%s\" for result evidence.\n")
			TEXT("6. Call `gen_record_texture_paint_pass` with pass_label \"%s\", source_snapshot_label \"%s\", result_snapshot_label \"%s\", texture_task_id from the texture task, texture_asset_path from the import result, affected_regions from the user's paint target, brush_strength %.2f, brush_radius %.2f, blend_amount %.2f, blend_mode \"%s\", pass_notes \"%s\", and the human approval_note.\n")
			TEXT("7. Call `gen_compile_texture_paint_evidence` with the prepare, snapshots, texture task, wait, import, paint pass, viewport evidence JSON, and a human approval_note that includes brush_strength %.2f, blend %.2f, brush_radius %.2f, and view_label \"%s\". Report the `unreal_mcp_texture_paint_evidence.v1` schema, proven flag, gates, and next_actions."),
			*SafeTaskId,
			*SafeTexturePrompt,
			*SafeReferences,
			*SafePaintViewLabel,
			SafeBrushStrength,
			*SafeBlendMode,
			*SafePaintNotes,
			*GenerativeOutputFolder,
			*SafeAssetName,
			*SafeSession,
			*SafePaintViewLabel,
			UploadSnapshotText,
			*SafeTaskId,
			*GenerativeTextureQuality,
			*SafeSession,
			ConfirmSpendText,
			*SafeTexturePrompt,
			*SafePaintedViewLabel,
			*SafePaintPassLabel,
			*SafePaintViewLabel,
			*SafePaintedViewLabel,
			SafeBrushStrength,
			SafeBrushRadius,
			SafePaintBlend,
			*SafeBlendMode,
			*SafePaintNotes,
			SafeBrushStrength,
			SafePaintBlend,
			SafeBrushRadius,
			*SafePaintViewLabel
		);
	}

	return FString::Printf(
		TEXT("Use MCP tool `gen_tripo_text_to_model` to generate a Smart Mesh asset, then show progress with `gen_tripo_wait_for_task` in the chat tool card.\n")
		TEXT("Parameters:\n")
		TEXT("- prompt: \"%s\"\n")
		TEXT("- model_version: \"%s\"\n")
		TEXT("- texture: true\n")
		TEXT("- pbr: true\n")
		TEXT("- texture_quality: \"%s\"\n")
		TEXT("- smart_low_poly: true\n")
		TEXT("- face_limit: 12000\n")
		TEXT("- session_name: \"%s\"\n")
		TEXT("- confirm_spend: %s\n")
		TEXT("After the task succeeds, call `gen_tripo_import_to_project` with content_path \"%s\" and asset_name \"%s\"."),
		*SafePrompt,
		*GenerativeModelVersion,
		*GenerativeTextureQuality,
		*SafeSession,
		ConfirmSpendText,
		*GenerativeOutputFolder,
		*SafeAssetName
	);
}

FText SMCPChatPanel::GetGenerateAssetPreviewText() const
{
	if (GetGenerateAssetMode() == TEXT("texture_paint") || GetGenerateAssetMode() == TEXT("texture") || GetGenerateAssetMode() == TEXT("paint"))
	{
		return FText::Format(
			LOCTEXT("GenerateAssetTexturePaintPreview", "Preview: Texture/Paint -> viewport snapshot -> Tripo texture_model -> import/evidence. Strength {0} | Blend {1} | Radius {2} | Confirmed spend: {3}."),
			FText::AsNumber(GenerateAssetPaintBrushStrength),
			FText::AsNumber(GenerateAssetPaintBlend),
			FText::AsNumber(GenerateAssetPaintBrushRadius),
			bGenerativeSpendConfirmed ? LOCTEXT("GenerateAssetSpendYes", "yes") : LOCTEXT("GenerateAssetSpendNo", "no")
		);
	}

	return FText::Format(
		LOCTEXT("GenerateAssetPreview", "Preview: {0} Smart Mesh -> gen_tripo_wait_for_task progress -> gen_tripo_import_to_project. Confirmed spend: {1}."),
		FText::FromString(GetGenerateAssetMode()),
		bGenerativeSpendConfirmed ? LOCTEXT("GenerateAssetSpendYes", "yes") : LOCTEXT("GenerateAssetSpendNo", "no")
	);
}

EVisibility SMCPChatPanel::GetGenerateAssetDialogVisibility() const
{
	return bGenerateAssetDialogVisible ? EVisibility::Visible : EVisibility::Collapsed;
}

FString SMCPChatPanel::GetGenerateAssetMode() const
{
	const FString Mode = GenerateAssetMode.TrimStartAndEnd().ToLower();
	return Mode.IsEmpty() ? FString(TEXT("text_to_model")) : Mode;
}

FString SMCPChatPanel::GetGenerativeSettingsFilePath() const
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("MCPChat"), TEXT("generative_settings.json"));
}

FString SMCPChatPanel::GetGenerativeSecretsFilePath() const
{
	return FPaths::Combine(FPaths::ProjectSavedDir(), TEXT("MCPChat"), TEXT("secrets.json"));
}

FString SMCPChatPanel::GetGenerativeApiKeySource() const
{
	const FString EnvKey = FPlatformMisc::GetEnvironmentVariable(TEXT("TRIPO_API_KEY"));
	if (!EnvKey.TrimStartAndEnd().IsEmpty())
	{
		return TEXT("env:TRIPO_API_KEY");
	}
	if (!GenerativeApiKey.TrimStartAndEnd().IsEmpty())
	{
		return TEXT("Saved/MCPChat/secrets.json");
	}
	return TEXT("missing");
}

FString SMCPChatPanel::GetGenerativeUthanaApiKeySource() const
{
	const FString EnvKey = FPlatformMisc::GetEnvironmentVariable(TEXT("UTHANA_API_KEY"));
	if (!EnvKey.TrimStartAndEnd().IsEmpty())
	{
		return TEXT("env:UTHANA_API_KEY");
	}
	if (!GenerativeUthanaApiKey.TrimStartAndEnd().IsEmpty())
	{
		return TEXT("Saved/MCPChat/secrets.json");
	}

	FString SecretsText;
	if (FFileHelper::LoadFileToString(SecretsText, *GetGenerativeSecretsFilePath()))
	{
		TSharedPtr<FJsonObject> SecretsObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(SecretsText);
		if (FJsonSerializer::Deserialize(Reader, SecretsObject) && SecretsObject.IsValid())
		{
			FString UthanaKey;
			if (!SecretsObject->TryGetStringField(TEXT("UTHANA_API_KEY"), UthanaKey))
			{
				SecretsObject->TryGetStringField(TEXT("uthana_api_key"), UthanaKey);
			}
			if (!UthanaKey.TrimStartAndEnd().IsEmpty())
			{
				return TEXT("Saved/MCPChat/secrets.json");
			}
		}
	}
	return TEXT("missing");
}

void SMCPChatPanel::RequestGenerativeBalanceRefresh()
{
	FString ApiKey = FPlatformMisc::GetEnvironmentVariable(TEXT("TRIPO_API_KEY")).TrimStartAndEnd();
	if (ApiKey.IsEmpty())
	{
		ApiKey = GenerativeApiKey.TrimStartAndEnd();
	}
	if (ApiKey.IsEmpty())
	{
		GenerativeApiWalletStatus = TEXT("missing API key");
		SetStatus(LOCTEXT("StatusGenerativeBalanceMissingKey", "Tripo API key required for balance refresh"), ErrorStatusColor);
		return;
	}

	GenerativeApiWalletStatus = TEXT("refreshing");
	SetStatus(LOCTEXT("StatusGenerativeBalanceRefreshing", "Refreshing Tripo API balance"), PendingStatusColor);

	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
	Request->SetURL(TEXT("https://api.tripo3d.ai/v2/openapi/user/balance"));
	Request->SetVerb(TEXT("GET"));
	Request->SetHeader(TEXT("Accept"), TEXT("application/json"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	Request->SetHeader(TEXT("Authorization"), FString::Printf(TEXT("Bearer %s"), *ApiKey));

	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
		if (!bWasSuccessful || !Response.IsValid())
		{
			GenerativeApiWalletStatus = TEXT("request failed");
			SetStatus(LOCTEXT("StatusGenerativeBalanceFailed", "Tripo API balance refresh failed"), ErrorStatusColor);
			return;
		}

		TSharedPtr<FJsonObject> RootObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(Response->GetContentAsString());
		if (!FJsonSerializer::Deserialize(Reader, RootObject) || !RootObject.IsValid())
		{
			GenerativeApiWalletStatus = TEXT("invalid response");
			SetStatus(LOCTEXT("StatusGenerativeBalanceInvalid", "Tripo API balance response was invalid"), ErrorStatusColor);
			return;
		}

		double CodeValue = 0.0;
		const bool bHasCode = RootObject->TryGetNumberField(TEXT("code"), CodeValue);
		const TSharedPtr<FJsonObject>* DataObject = nullptr;
		if (Response->GetResponseCode() >= 400 || (bHasCode && FMath::RoundToInt(CodeValue) != 0) || !RootObject->TryGetObjectField(TEXT("data"), DataObject) || !DataObject || !DataObject->IsValid())
		{
			FString Message;
			RootObject->TryGetStringField(TEXT("message"), Message);
			GenerativeApiWalletStatus = Message.IsEmpty() ? FString::Printf(TEXT("HTTP %d"), Response->GetResponseCode()) : Message;
			SetStatus(LOCTEXT("StatusGenerativeBalanceError", "Tripo API balance returned an error"), ErrorStatusColor);
			return;
		}

		double BalanceValue = 0.0;
		double FrozenValue = 0.0;
		if ((*DataObject)->TryGetNumberField(TEXT("balance"), BalanceValue))
		{
			GenerativeApiWalletBalance = FString::FromInt(FMath::RoundToInt(BalanceValue));
		}
		else
		{
			FString BalanceText;
			(*DataObject)->TryGetStringField(TEXT("balance"), BalanceText);
			GenerativeApiWalletBalance = BalanceText.IsEmpty() ? TEXT("unknown") : BalanceText;
		}
		if ((*DataObject)->TryGetNumberField(TEXT("frozen"), FrozenValue))
		{
			GenerativeApiWalletFrozen = FString::FromInt(FMath::RoundToInt(FrozenValue));
		}
		else
		{
			FString FrozenText;
			(*DataObject)->TryGetStringField(TEXT("frozen"), FrozenText);
			GenerativeApiWalletFrozen = FrozenText.IsEmpty() ? TEXT("unknown") : FrozenText;
		}

		GenerativeApiWalletStatus = TEXT("refreshed");
		SetStatus(LOCTEXT("StatusGenerativeBalanceRefreshed", "Tripo API balance refreshed"), OkStatusColor);
	});
	Request->ProcessRequest();
}

void SMCPChatPanel::LoadGenerativeSettings()
{
	GenerativeModelVersion = TEXT("tripo-default");
	GenerativeTextureQuality = TEXT("standard");
	GenerativeOutputFolder = TEXT("/Game/Generated");
	GenerativeSessionCreditBudget = 1000;
	GenerativePendingSpendCredits = 0;
	GenerativeApiKey.Empty();
	GenerativeUthanaApiKey.Empty();
	bGenerativeSpendConfirmed = false;

	FString SettingsText;
	if (FFileHelper::LoadFileToString(SettingsText, *GetGenerativeSettingsFilePath()))
	{
		TSharedPtr<FJsonObject> SettingsObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(SettingsText);
		if (FJsonSerializer::Deserialize(Reader, SettingsObject) && SettingsObject.IsValid())
		{
			SettingsObject->TryGetStringField(TEXT("default_model_version"), GenerativeModelVersion);
			SettingsObject->TryGetStringField(TEXT("default_texture_quality"), GenerativeTextureQuality);
			SettingsObject->TryGetStringField(TEXT("output_folder"), GenerativeOutputFolder);

			double NumberValue = 0.0;
			if (SettingsObject->TryGetNumberField(TEXT("session_credit_budget"), NumberValue))
			{
				GenerativeSessionCreditBudget = FMath::Max(0, FMath::RoundToInt(NumberValue));
			}
			if (SettingsObject->TryGetNumberField(TEXT("pending_spend_credits"), NumberValue))
			{
				GenerativePendingSpendCredits = FMath::Max(0, FMath::RoundToInt(NumberValue));
			}
			SettingsObject->TryGetBoolField(TEXT("spend_confirmed"), bGenerativeSpendConfirmed);
		}
	}

	FString SecretsText;
	if (FFileHelper::LoadFileToString(SecretsText, *GetGenerativeSecretsFilePath()))
	{
		TSharedPtr<FJsonObject> SecretsObject;
		const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(SecretsText);
		if (FJsonSerializer::Deserialize(Reader, SecretsObject) && SecretsObject.IsValid())
		{
			if (!SecretsObject->TryGetStringField(TEXT("TRIPO_API_KEY"), GenerativeApiKey))
			{
				SecretsObject->TryGetStringField(TEXT("tripo_api_key"), GenerativeApiKey);
			}
			if (!SecretsObject->TryGetStringField(TEXT("UTHANA_API_KEY"), GenerativeUthanaApiKey))
			{
				SecretsObject->TryGetStringField(TEXT("uthana_api_key"), GenerativeUthanaApiKey);
			}
		}
	}
}

void SMCPChatPanel::SaveGenerativeSettingsToDisk() const
{
	IFileManager::Get().MakeDirectory(*FPaths::GetPath(GetGenerativeSettingsFilePath()), true);

	const TSharedPtr<FJsonObject> SettingsObject = BuildGenerativeSettingsJson();
	FString SettingsText;
	const TSharedRef<TJsonWriter<>> SettingsWriter = TJsonWriterFactory<>::Create(&SettingsText);
	FJsonSerializer::Serialize(SettingsObject.ToSharedRef(), SettingsWriter);
	FFileHelper::SaveStringToFile(SettingsText, *GetGenerativeSettingsFilePath());

	TSharedPtr<FJsonObject> SecretsObject = MakeShared<FJsonObject>();
	FString ExistingSecretsText;
	if (FFileHelper::LoadFileToString(ExistingSecretsText, *GetGenerativeSecretsFilePath()))
	{
		TSharedPtr<FJsonObject> ExistingSecretsObject;
		const TSharedRef<TJsonReader<>> ExistingSecretsReader = TJsonReaderFactory<>::Create(ExistingSecretsText);
		if (FJsonSerializer::Deserialize(ExistingSecretsReader, ExistingSecretsObject) && ExistingSecretsObject.IsValid())
		{
			SecretsObject = ExistingSecretsObject;
		}
	}

	if (!GenerativeApiKey.TrimStartAndEnd().IsEmpty())
	{
		SecretsObject->SetStringField(TEXT("TRIPO_API_KEY"), GenerativeApiKey.TrimStartAndEnd());
		SecretsObject->RemoveField(TEXT("tripo_api_key"));
	}
	if (!GenerativeUthanaApiKey.TrimStartAndEnd().IsEmpty())
	{
		SecretsObject->SetStringField(TEXT("UTHANA_API_KEY"), GenerativeUthanaApiKey.TrimStartAndEnd());
		SecretsObject->RemoveField(TEXT("uthana_api_key"));
	}

	if (!SecretsObject->Values.IsEmpty())
	{
		FString SecretsText;
		const TSharedRef<TJsonWriter<>> SecretsWriter = TJsonWriterFactory<>::Create(&SecretsText);
		FJsonSerializer::Serialize(SecretsObject.ToSharedRef(), SecretsWriter);
		FFileHelper::SaveStringToFile(SecretsText, *GetGenerativeSecretsFilePath());
	}
}

TSharedPtr<FJsonObject> SMCPChatPanel::BuildGenerativeSettingsJson() const
{
	const TSharedPtr<FJsonObject> SettingsObject = MakeShared<FJsonObject>();
	SettingsObject->SetStringField(TEXT("provider"), TEXT("tripo"));
	SettingsObject->SetStringField(TEXT("animation_provider"), TEXT("uthana"));
	SettingsObject->SetStringField(TEXT("default_model_version"), GenerativeModelVersion.IsEmpty() ? TEXT("tripo-default") : GenerativeModelVersion);
	SettingsObject->SetStringField(TEXT("default_texture_quality"), GenerativeTextureQuality.IsEmpty() ? TEXT("standard") : GenerativeTextureQuality);
	SettingsObject->SetStringField(TEXT("output_folder"), GenerativeOutputFolder.StartsWith(TEXT("/Game")) ? GenerativeOutputFolder : TEXT("/Game/Generated"));
	SettingsObject->SetStringField(TEXT("animation_output_folder"), TEXT("/Game/Generated/Animations"));
	SettingsObject->SetStringField(TEXT("uthana_default_character_id"), TEXT("cXi2eAP19XwQ"));
	SettingsObject->SetNumberField(TEXT("session_credit_budget"), FMath::Max(0, GenerativeSessionCreditBudget));
	SettingsObject->SetNumberField(TEXT("pending_spend_credits"), FMath::Max(0, GenerativePendingSpendCredits));
	SettingsObject->SetBoolField(TEXT("spend_confirmed"), bGenerativeSpendConfirmed);
	return SettingsObject;
}

bool SMCPChatPanel::CommandPaletteItemMatches(const FString& Filter, const FCommandPaletteItem& Item) const
{
	const FString Needle = Filter.TrimStartAndEnd().ToLower();
	if (Needle.IsEmpty())
	{
		return true;
	}

	const FString ItemKind = Item.Kind.TrimStartAndEnd().ToLower();
	if (Needle == TEXT("slash") ||
		Needle == TEXT("generative") ||
		Needle == TEXT("workflow") ||
		Needle == TEXT("gameplay") ||
		Needle == TEXT("kb") ||
		Needle == TEXT("tool") ||
		Needle == TEXT("asset") ||
		Needle == TEXT("prompt"))
	{
		return ItemKind == Needle;
	}

	const FString Haystack = FString::Printf(
		TEXT("%s %s %s %s"),
		*Item.Label,
		*Item.Detail,
		*Item.InsertText,
		*Item.Kind
	).ToLower();
	if (Haystack.Contains(Needle))
	{
		return true;
	}

	int32 HaystackIndex = 0;
	for (int32 NeedleIndex = 0; NeedleIndex < Needle.Len(); ++NeedleIndex)
	{
		bool bMatchedCharacter = false;
		while (HaystackIndex < Haystack.Len())
		{
			if (Haystack[HaystackIndex] == Needle[NeedleIndex])
			{
				bMatchedCharacter = true;
				++HaystackIndex;
				break;
			}
			++HaystackIndex;
		}

		if (!bMatchedCharacter)
		{
			return false;
		}
	}

	return true;
}

FString SMCPChatPanel::BuildDropReference(const TSharedPtr<FDragDropOperation>& Operation) const
{
	if (!Operation.IsValid())
	{
		return TEXT("");
	}

	if (Operation->IsOfType<FAssetDragDropOp>())
	{
		const TSharedPtr<FAssetDragDropOp> AssetDragDropOp = StaticCastSharedPtr<FAssetDragDropOp>(Operation);
		TArray<FString> References;
		if (AssetDragDropOp.IsValid() && AssetDragDropOp->HasAssets())
		{
			for (const FAssetData& AssetData : AssetDragDropOp->GetAssets())
			{
				if (!AssetData.PackageName.IsNone())
				{
					References.Add(FString::Printf(TEXT("@asset:%s"), *AssetData.PackageName.ToString()));
				}
			}
		}
		if (AssetDragDropOp.IsValid() && AssetDragDropOp->HasAssetPaths())
		{
			for (const FString& AssetPath : AssetDragDropOp->GetAssetPaths())
			{
				if (!AssetPath.IsEmpty())
				{
					References.Add(FString::Printf(TEXT("@asset:%s"), *AssetPath));
				}
			}
		}
		if (!References.IsEmpty())
		{
			return FString::Join(References, LINE_TERMINATOR);
		}
		return TEXT("@asset:<dropped-asset>");
	}

	if (Operation->IsOfType<FActorDragDropOp>())
	{
		const TSharedPtr<FActorDragDropOp> ActorDragDropOp = StaticCastSharedPtr<FActorDragDropOp>(Operation);
		TArray<FString> References;
		if (ActorDragDropOp.IsValid())
		{
			for (const TWeakObjectPtr<AActor>& ActorPtr : ActorDragDropOp->Actors)
			{
				if (ActorPtr.IsValid())
				{
					References.Add(FString::Printf(TEXT("@actor:%s"), *ActorPtr->GetName()));
				}
			}
		}
		if (!References.IsEmpty())
		{
			return FString::Join(References, LINE_TERMINATOR);
		}
		return TEXT("@actor:<dropped-actor>");
	}

	if (Operation->IsOfType<FExternalDragOperation>())
	{
		const TSharedPtr<FExternalDragOperation> ExternalDragDropOp = StaticCastSharedPtr<FExternalDragOperation>(Operation);
		TArray<FString> References;
		if (ExternalDragDropOp.IsValid() && ExternalDragDropOp->HasFiles())
		{
			for (const FString& FilePath : ExternalDragDropOp->GetFiles())
			{
				if (FilePath.IsEmpty())
				{
					continue;
				}

				FString NormalizedFilePath = FPaths::ConvertRelativePathToFull(FilePath);
				FPaths::MakeStandardFilename(NormalizedFilePath);
				References.Add(FString::Printf(TEXT("@file:%s"), *NormalizedFilePath));
			}
		}
		if (!References.IsEmpty())
		{
			return FString::Join(References, LINE_TERMINATOR);
		}
		if (ExternalDragDropOp.IsValid() && ExternalDragDropOp->HasText())
		{
			return FString::Printf(TEXT("@text:%s"), *ExternalDragDropOp->GetText());
		}
	}

	return Operation->IsExternalOperation() ? TEXT("@file:<dropped-file>") : TEXT("");
}

FString SMCPChatPanel::ExtractFirstAssetReference(const FString& Message) const
{
	const FString Marker = TEXT("@asset:");
	const int32 AssetMarkerIndex = Message.Find(Marker, ESearchCase::IgnoreCase);
	int32 ReferenceStartIndex = INDEX_NONE;
	int32 MarkerLength = 0;
	if (AssetMarkerIndex != INDEX_NONE)
	{
		ReferenceStartIndex = AssetMarkerIndex;
		MarkerLength = Marker.Len();
	}
	else
	{
		ReferenceStartIndex = Message.Find(TEXT("/Game/"), ESearchCase::IgnoreCase);
	}

	if (ReferenceStartIndex == INDEX_NONE)
	{
		return TEXT("");
	}

	FString Remaining = Message.Mid(ReferenceStartIndex + MarkerLength).TrimStartAndEnd();
	int32 EndIndex = Remaining.Len();
	for (int32 Index = 0; Index < Remaining.Len(); ++Index)
	{
		const TCHAR Char = Remaining[Index];
		if (FChar::IsWhitespace(Char) || Char == TEXT(',') || Char == TEXT(')') || Char == TEXT(']') || Char == TEXT('}') || Char == TEXT(';'))
		{
			EndIndex = Index;
			break;
		}
	}

	FString Reference = Remaining.Left(EndIndex).TrimStartAndEnd();
	Reference.RemoveFromStart(TEXT("\""));
	Reference.RemoveFromEnd(TEXT("\""));
	Reference.RemoveFromStart(TEXT("'"));
	Reference.RemoveFromEnd(TEXT("'"));
	Reference.RemoveFromEnd(TEXT("."));
	return Reference;
}

FString SMCPChatPanel::BuildServerUrl(const FString& PathAndQuery) const
{
	return ServerBaseUrl + PathAndQuery;
}

FString SMCPChatPanel::MakeCurrentTimestamp() const
{
	return FDateTime::UtcNow().ToIso8601();
}

TSharedRef<IHttpRequest, ESPMode::ThreadSafe> SMCPChatPanel::MakeJsonRequest(const FString& Url, const FString& Verb) const
{
	TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = FHttpModule::Get().CreateRequest();
	Request->SetURL(Url);
	Request->SetVerb(Verb);
	Request->SetHeader(TEXT("Accept"), TEXT("application/json"));
	Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
	return Request;
}

TSharedPtr<FJsonObject> SMCPChatPanel::BuildEditorContext() const
{
	const TSharedPtr<FJsonObject> Context = MakeShared<FJsonObject>();

	if (GEditor)
	{
		if (const UWorld* World = GEditor->GetEditorWorldContext().World())
		{
			Context->SetStringField(TEXT("current_level"), World->GetOutermost()->GetName());
		}

		if (USelection* SelectedActors = GEditor->GetSelectedActors())
		{
			if (SelectedActors->Num() > 0)
			{
				if (AActor* SelectedActor = Cast<AActor>(SelectedActors->GetSelectedObject(0)))
				{
					Context->SetStringField(TEXT("selected_actor"), SelectedActor->GetName());
					Context->SetStringField(TEXT("selected_actor_class"), SelectedActor->GetClass()->GetName());
				}
			}
		}
	}

	return Context;
}

bool SMCPChatPanel::ParseToolPaletteResponse(const FString& JsonText, TMap<FString, TArray<FToolPaletteEntry>>& OutToolsByCategory) const
{
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonText);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return false;
	}

	const TSharedPtr<FJsonObject>* ToolsByCategoryObject = nullptr;
	if (!Root->TryGetObjectField(TEXT("tools_by_category"), ToolsByCategoryObject) || ToolsByCategoryObject == nullptr || !ToolsByCategoryObject->IsValid())
	{
		return false;
	}

	for (const TPair<FString, TSharedPtr<FJsonValue>>& CategoryPair : (*ToolsByCategoryObject)->Values)
	{
		const FString& Category = CategoryPair.Key;
		const TArray<TSharedPtr<FJsonValue>>* ToolValues = nullptr;
		if (!CategoryPair.Value.IsValid() || !CategoryPair.Value->TryGetArray(ToolValues) || ToolValues == nullptr)
		{
			continue;
		}

		TArray<FToolPaletteEntry>& Entries = OutToolsByCategory.FindOrAdd(Category);
		for (const TSharedPtr<FJsonValue>& ToolValue : *ToolValues)
		{
			const TSharedPtr<FJsonObject> ToolObject = ToolValue.IsValid() ? ToolValue->AsObject() : nullptr;
			if (!ToolObject.IsValid())
			{
				continue;
			}

			FToolPaletteEntry Entry;
			Entry.Name = GetStringField(ToolObject, TEXT("name"));
			Entry.Description = GetStringField(ToolObject, TEXT("description"));
			Entry.Category = GetStringField(ToolObject, TEXT("category"));
			if (Entry.Category.IsEmpty())
			{
				Entry.Category = Category;
			}

			const TArray<TSharedPtr<FJsonValue>>* ParameterValues = nullptr;
			if (ToolObject->TryGetArrayField(TEXT("parameters"), ParameterValues) && ParameterValues != nullptr)
			{
				for (const TSharedPtr<FJsonValue>& ParameterValue : *ParameterValues)
				{
					FString ParameterName;
					if (ParameterValue.IsValid() && ParameterValue->TryGetString(ParameterName) && !ParameterName.IsEmpty())
					{
						Entry.Parameters.Add(ParameterName);
					}
				}
			}

			if (!Entry.Name.IsEmpty())
			{
				Entries.Add(Entry);
			}
		}
	}

	return !OutToolsByCategory.IsEmpty();
}

bool SMCPChatPanel::ParseSessionsResponse(const FString& JsonText, TArray<FChatSessionEntry>& OutSessions, FString& OutLastSession) const
{
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonText);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return false;
	}

	Root->TryGetStringField(TEXT("last_session"), OutLastSession);
	const TArray<TSharedPtr<FJsonValue>>* SessionValues = nullptr;
	if (!Root->TryGetArrayField(TEXT("sessions"), SessionValues) || SessionValues == nullptr)
	{
		return false;
	}

	for (const TSharedPtr<FJsonValue>& Value : *SessionValues)
	{
		const TSharedPtr<FJsonObject> Object = Value.IsValid() ? Value->AsObject() : nullptr;
		if (!Object.IsValid())
		{
			continue;
		}

		FChatSessionEntry Session;
		Session.Name = GetStringField(Object, TEXT("name"));
		Session.UpdatedAt = GetStringField(Object, TEXT("updated_at"));
		Session.bPinned = Object->GetBoolField(TEXT("pinned"));
		Session.MessageCount = static_cast<int32>(Object->GetIntegerField(TEXT("message_count")));
		if (!Session.Name.IsEmpty())
		{
			OutSessions.Add(Session);
		}
	}

	return !OutSessions.IsEmpty();
}

bool SMCPChatPanel::ParseCockpitOverviewResponse(const FString& JsonText, FCockpitOverview& OutOverview) const
{
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonText);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return false;
	}

	FString Schema;
	Root->TryGetStringField(TEXT("schema"), Schema);
	if (Schema != TEXT("unreal_mcp_chat_cockpit_overview.v1"))
	{
		return false;
	}

	OutOverview = FCockpitOverview();
	OutOverview.bLoaded = true;
	Root->TryGetStringField(TEXT("session"), OutOverview.Session);
	if (OutOverview.Session.IsEmpty())
	{
		OutOverview.Session = CurrentSessionName.IsEmpty() ? FString(TEXT("default")) : CurrentSessionName;
	}

	TArray<FString> BlockingGates;
	const TArray<TSharedPtr<FJsonValue>>* BlockingGateValues = nullptr;
	if (Root->TryGetArrayField(TEXT("blocking_gates"), BlockingGateValues) && BlockingGateValues != nullptr)
	{
		for (const TSharedPtr<FJsonValue>& GateValue : *BlockingGateValues)
		{
			FString Gate;
			if (GateValue.IsValid() && GateValue->TryGetString(Gate) && !Gate.IsEmpty())
			{
				BlockingGates.Add(Gate);
			}
		}
	}
	OutOverview.BlockingGateCount = BlockingGates.Num();
	OutOverview.bBlocked = OutOverview.BlockingGateCount > 0;
	OutOverview.BlockersSummary = OutOverview.bBlocked ? FString::Join(BlockingGates, TEXT(", ")) : TEXT("clear");

	const TSharedPtr<FJsonObject>* HudSummaryObject = nullptr;
	if (Root->TryGetObjectField(TEXT("hud_summary"), HudSummaryObject) && HudSummaryObject && HudSummaryObject->IsValid())
	{
		FString HudSchema;
		(*HudSummaryObject)->TryGetStringField(TEXT("schema"), HudSchema);
		if (HudSchema == TEXT("unreal_mcp_chat_cockpit_hud_summary.v1"))
		{
			OutOverview.bHasHudSummary = true;
			const FString HudState = GetStringField(*HudSummaryObject, TEXT("state"));
			double VisibleCardCount = 0.0;
			(*HudSummaryObject)->TryGetNumberField(TEXT("visible_card_count"), VisibleCardCount);
			OutOverview.HudVisibleCardCount = FMath::Max(0, FMath::RoundToInt(VisibleCardCount));
			OutOverview.HudStateSummary = TruncateForCard(FString::Printf(
				TEXT("%s, %d card(s)"),
				*(HudState.IsEmpty() ? FString(TEXT("unknown")) : HudState),
				OutOverview.HudVisibleCardCount
			), 64);

			TArray<FString> HudBlockers;
			const TArray<TSharedPtr<FJsonValue>>* HudBlockerValues = nullptr;
			if ((*HudSummaryObject)->TryGetArrayField(TEXT("primary_blocker_preview"), HudBlockerValues) && HudBlockerValues != nullptr)
			{
				for (const TSharedPtr<FJsonValue>& BlockerValue : *HudBlockerValues)
				{
					FString Blocker;
					if (BlockerValue.IsValid() && BlockerValue->TryGetString(Blocker) && !Blocker.IsEmpty())
					{
						HudBlockers.Add(Blocker);
					}
				}
			}
			double HudBlockerOverflow = 0.0;
			(*HudSummaryObject)->TryGetNumberField(TEXT("primary_blocker_overflow_count"), HudBlockerOverflow);
			if (!HudBlockers.IsEmpty())
			{
				const int32 OverflowCount = FMath::Max(0, FMath::RoundToInt(HudBlockerOverflow));
				const FString OverflowSuffix = OverflowCount > 0 ? FString::Printf(TEXT(" +%d"), OverflowCount) : FString();
				OutOverview.BlockersSummary = TruncateForCard(FString::Printf(
					TEXT("%s%s"),
					*FString::Join(HudBlockers, TEXT(", ")),
					*OverflowSuffix
				), 120);
			}

			const TArray<TSharedPtr<FJsonValue>>* HudCardValues = nullptr;
			if ((*HudSummaryObject)->TryGetArrayField(TEXT("compact_cards"), HudCardValues) && HudCardValues != nullptr)
			{
				for (const TSharedPtr<FJsonValue>& HudCardValue : *HudCardValues)
				{
					const TSharedPtr<FJsonObject> HudCardObject = HudCardValue.IsValid() ? HudCardValue->AsObject() : nullptr;
					if (!HudCardObject.IsValid())
					{
						continue;
					}
					const FString CardId = GetStringField(HudCardObject, TEXT("id"));
					const FString Primary = GetStringField(HudCardObject, TEXT("primary"));
					const FString Secondary = GetStringField(HudCardObject, TEXT("secondary"));
					const FString Summary = Secondary.IsEmpty() ? Primary : FString::Printf(TEXT("%s - %s"), *Primary, *Secondary);
					if (Summary.IsEmpty())
					{
						continue;
					}
					if (CardId == TEXT("readiness"))
					{
						OutOverview.HudReadinessSummary = TruncateForCard(Summary, 96);
					}
					else if (CardId == TEXT("feature"))
					{
						OutOverview.HudFeatureSummary = TruncateForCard(Summary, 96);
					}
					else if (CardId == TEXT("next_safe_step"))
					{
						OutOverview.HudNextStepSummary = TruncateForCard(Summary, 96);
					}
					else if (CardId == TEXT("generation"))
					{
						OutOverview.HudGenerationSummary = TruncateForCard(Summary, 96);
					}
					else if (CardId == TEXT("evidence"))
					{
						OutOverview.HudEvidenceSummary = TruncateForCard(Summary, 96);
					}
				}
			}

			const FString AnimationProvider = GetStringField(*HudSummaryObject, TEXT("generated_animation_provider"));
			const FString AnimationTargetName = GetStringField(*HudSummaryObject, TEXT("generated_animation_target_name"));
			const FString AnimationNextActionId = GetStringField(*HudSummaryObject, TEXT("generated_animation_next_safe_action_id"));
			const FString AnimationUsageHandoffId = GetStringField(*HudSummaryObject, TEXT("generated_animation_usage_next_operator_handoff_id"));
			TArray<FString> AnimationSummaryParts;
			if (!AnimationProvider.IsEmpty() || !AnimationTargetName.IsEmpty())
			{
				const FString ProviderAndTarget = AnimationProvider.IsEmpty()
					? AnimationTargetName
					: (AnimationTargetName.IsEmpty()
						? AnimationProvider
						: FString::Printf(TEXT("%s: %s"), *AnimationProvider, *AnimationTargetName));
				AnimationSummaryParts.Add(ProviderAndTarget);
			}
			if (!AnimationNextActionId.IsEmpty())
			{
				AnimationSummaryParts.Add(AnimationNextActionId);
			}
			if (!AnimationUsageHandoffId.IsEmpty())
			{
				AnimationSummaryParts.Add(FString::Printf(TEXT("handoff %s"), *AnimationUsageHandoffId));
			}
			if (!AnimationSummaryParts.IsEmpty())
			{
				OutOverview.HudAnimationSummary = TruncateForCard(FString::Join(AnimationSummaryParts, TEXT(" -> ")), 96);
			}

			const FString HandoffLabel = GetStringField(*HudSummaryObject, TEXT("next_operator_handoff_label"));
			const FString HandoffId = GetStringField(*HudSummaryObject, TEXT("next_operator_handoff_id"));
			const FString HandoffKind = GetStringField(*HudSummaryObject, TEXT("next_operator_handoff_command_kind"));
			const FString HandoffReceiptPath = GetStringField(*HudSummaryObject, TEXT("next_operator_handoff_receipt_path"));
			const FString HandoffSafetyLabel = GetStringField(*HudSummaryObject, TEXT("next_operator_handoff_safety_label"));
			TArray<FString> HandoffSummaryParts;
			const FString HandoffDisplay = HandoffLabel.IsEmpty() ? HandoffId : HandoffLabel;
			if (!HandoffDisplay.IsEmpty())
			{
				HandoffSummaryParts.Add(HandoffDisplay);
			}
			if (!HandoffSafetyLabel.IsEmpty())
			{
				HandoffSummaryParts.Add(HandoffSafetyLabel);
			}
			if (!HandoffKind.IsEmpty())
			{
				HandoffSummaryParts.Add(HandoffKind);
			}
			if (!HandoffReceiptPath.IsEmpty())
			{
				HandoffSummaryParts.Add(HandoffReceiptPath);
			}
			if (!HandoffSummaryParts.IsEmpty())
			{
				OutOverview.HudOperatorHandoffSummary = TruncateForCard(FString::Join(HandoffSummaryParts, TEXT(" -> ")), 120);
			}

			const FString BlueprintEvidenceState = GetStringField(*HudSummaryObject, TEXT("blueprint_mutation_evidence_state"));
			const FString BlueprintEvidenceSummary = GetStringField(*HudSummaryObject, TEXT("blueprint_mutation_evidence_summary"));
			const FString BlueprintNextGate = GetStringField(*HudSummaryObject, TEXT("blueprint_mutation_next_gate"));
			const FString BlueprintNextHandoffId = GetStringField(*HudSummaryObject, TEXT("blueprint_mutation_next_operator_handoff_id"));
			const FString BlueprintSafetyLabel = GetStringField(*HudSummaryObject, TEXT("blueprint_mutation_safety_label"));
			double BlueprintMissingCount = 0.0;
			(*HudSummaryObject)->TryGetNumberField(TEXT("blueprint_mutation_evidence_missing_count"), BlueprintMissingCount);
			if (!BlueprintEvidenceState.IsEmpty() || !BlueprintEvidenceSummary.IsEmpty() || !BlueprintNextGate.IsEmpty() || !BlueprintNextHandoffId.IsEmpty())
			{
				TArray<FString> BlueprintSummaryParts;
				BlueprintSummaryParts.Add(BlueprintEvidenceState.IsEmpty() ? FString(TEXT("unknown")) : BlueprintEvidenceState);
				if (!BlueprintEvidenceSummary.IsEmpty())
				{
					BlueprintSummaryParts.Add(BlueprintEvidenceSummary);
				}
				if (BlueprintMissingCount > 0.0)
				{
					BlueprintSummaryParts.Add(FString::Printf(TEXT("%d missing"), FMath::Max(0, FMath::RoundToInt(BlueprintMissingCount))));
				}
				if (!BlueprintNextGate.IsEmpty())
				{
					BlueprintSummaryParts.Add(BlueprintNextGate);
				}
				if (!BlueprintNextHandoffId.IsEmpty())
				{
					BlueprintSummaryParts.Add(BlueprintNextHandoffId);
				}
				if (!BlueprintSafetyLabel.IsEmpty())
				{
					BlueprintSummaryParts.Add(BlueprintSafetyLabel);
				}
				OutOverview.HudBlueprintMutationSummary = TruncateForCard(FString::Join(BlueprintSummaryParts, TEXT(" -> ")), 120);
			}
		}
	}

	const TSharedPtr<FJsonObject>* ReadinessRepairObject = nullptr;
	if (Root->TryGetObjectField(TEXT("readiness_repair_queue"), ReadinessRepairObject) && ReadinessRepairObject && ReadinessRepairObject->IsValid())
	{
		const FString RecommendedNext = GetStringField(*ReadinessRepairObject, TEXT("recommended_next"));
		double ActionCount = 0.0;
		(*ReadinessRepairObject)->TryGetNumberField(TEXT("action_count"), ActionCount);
		const TSharedPtr<FJsonObject>* NextActionObject = nullptr;
		FString Gate;
		FString RecommendedTool;
		if ((*ReadinessRepairObject)->TryGetObjectField(TEXT("next_action"), NextActionObject) && NextActionObject && NextActionObject->IsValid())
		{
			Gate = GetStringField(*NextActionObject, TEXT("gate"));
			RecommendedTool = GetStringField(*NextActionObject, TEXT("recommended_tool"));
		}
		const FString DisplayAction = RecommendedNext.IsEmpty() ? Gate : RecommendedNext;
		if (!DisplayAction.IsEmpty())
		{
			const FString GateSuffix = Gate.IsEmpty() ? FString() : FString::Printf(TEXT(", gate %s"), *Gate);
			const FString ToolSuffix = RecommendedTool.IsEmpty() ? FString() : FString::Printf(TEXT(", via %s"), *RecommendedTool);
			OutOverview.ReadinessRepairSummary = TruncateForCard(FString::Printf(
				TEXT("next repair %s%s%s, %d action(s)"),
				*DisplayAction,
				*GateSuffix,
				*ToolSuffix,
				FMath::Max(0, FMath::RoundToInt(ActionCount))
			), 128);
		}
	}
	if (!OutOverview.ReadinessRepairSummary.IsEmpty() && OutOverview.bBlocked)
	{
		OutOverview.BlockersSummary = TruncateForCard(FString::Printf(
			TEXT("%s; %s"),
			*OutOverview.BlockersSummary,
			*OutOverview.ReadinessRepairSummary
		), 180);
	}

	const TArray<TSharedPtr<FJsonValue>>* CardValues = nullptr;
	if (Root->TryGetArrayField(TEXT("cards"), CardValues) && CardValues != nullptr)
	{
		for (const TSharedPtr<FJsonValue>& CardValue : *CardValues)
		{
			const TSharedPtr<FJsonObject> CardObject = CardValue.IsValid() ? CardValue->AsObject() : nullptr;
			if (!CardObject.IsValid())
			{
				continue;
			}

			const FString CardId = GetStringField(CardObject, TEXT("id"));
			const FString Summary = GetStringField(CardObject, TEXT("summary"));
			if (CardId == TEXT("evidence") && !Summary.IsEmpty())
			{
				OutOverview.EvidenceSummary = TruncateForCard(Summary, 120);
			}
			else if (CardId == TEXT("blockers") && !Summary.IsEmpty() && !OutOverview.bBlocked)
			{
				OutOverview.BlockersSummary = TruncateForCard(Summary, 120);
			}
			else if (CardId == TEXT("editor_queue") && !Summary.IsEmpty())
			{
				OutOverview.QueueSummary = TruncateForCard(Summary, 120);
			}
		}
	}

	const TArray<TSharedPtr<FJsonValue>>* QueueValues = nullptr;
	if (Root->TryGetArrayField(TEXT("editor_queues"), QueueValues) && QueueValues != nullptr)
	{
		FString FirstNextTool;
		TArray<FString> ActionPreviewParts;
		for (const TSharedPtr<FJsonValue>& QueueValue : *QueueValues)
		{
			const TSharedPtr<FJsonObject> QueueObject = QueueValue.IsValid() ? QueueValue->AsObject() : nullptr;
			if (!QueueObject.IsValid())
			{
				continue;
			}

			double ActionCount = 0.0;
			QueueObject->TryGetNumberField(TEXT("action_count"), ActionCount);
			OutOverview.QueuedActionCount += FMath::Max(0, FMath::RoundToInt(ActionCount));
			bool bCanExecuteNow = false;
			QueueObject->TryGetBoolField(TEXT("can_execute_now"), bCanExecuteNow);
			OutOverview.bQueueExecutable = OutOverview.bQueueExecutable || bCanExecuteNow;
			if (FirstNextTool.IsEmpty())
			{
				FirstNextTool = GetStringField(QueueObject, TEXT("next_action_tool"));
			}

			const TArray<TSharedPtr<FJsonValue>>* PreviewActionValues = nullptr;
			if (QueueObject->TryGetArrayField(TEXT("preview_actions"), PreviewActionValues) && PreviewActionValues != nullptr)
			{
				for (const TSharedPtr<FJsonValue>& PreviewValue : *PreviewActionValues)
				{
					if (ActionPreviewParts.Num() >= 5)
					{
						break;
					}
					const TSharedPtr<FJsonObject> PreviewObject = PreviewValue.IsValid() ? PreviewValue->AsObject() : nullptr;
					if (!PreviewObject.IsValid())
					{
						continue;
					}
					double ActionIndex = 0.0;
					PreviewObject->TryGetNumberField(TEXT("index"), ActionIndex);
					const FString Tool = GetStringField(PreviewObject, TEXT("tool"));
					const FString Id = GetStringField(PreviewObject, TEXT("id"));
					const FString Name = Tool.IsEmpty() ? Id : Tool;
					if (!Name.IsEmpty())
					{
						const int32 DisplayIndex = FMath::Max(1, FMath::RoundToInt(ActionIndex));
						ActionPreviewParts.Add(FString::Printf(TEXT("%d. %s"), DisplayIndex, *Name));
					}
				}
			}
		}

		if (OutOverview.QueuedActionCount > 0)
		{
			const FString QueueState = OutOverview.bQueueExecutable ? TEXT("ready") : TEXT("blocked");
			OutOverview.QueueSummary = FirstNextTool.IsEmpty()
				? FString::Printf(TEXT("%d action(s), %s"), OutOverview.QueuedActionCount, *QueueState)
				: FString::Printf(TEXT("%d action(s), next %s, %s"), OutOverview.QueuedActionCount, *FirstNextTool, *QueueState);
			if (!ActionPreviewParts.IsEmpty())
			{
				OutOverview.QueueActionsSummary = TruncateForCard(FString::Join(ActionPreviewParts, TEXT(" -> ")), 180);
			}
		}
	}

	const TArray<TSharedPtr<FJsonValue>>* EvidenceTimelineValues = nullptr;
	if (Root->TryGetArrayField(TEXT("evidence_timeline"), EvidenceTimelineValues) && EvidenceTimelineValues != nullptr)
	{
		TArray<FString> TimelineParts;
		for (const TSharedPtr<FJsonValue>& TimelineValue : *EvidenceTimelineValues)
		{
			if (TimelineParts.Num() >= 5)
			{
				break;
			}
			const TSharedPtr<FJsonObject> TimelineObject = TimelineValue.IsValid() ? TimelineValue->AsObject() : nullptr;
			if (!TimelineObject.IsValid())
			{
				continue;
			}

			double EventIndex = 0.0;
			double ArtifactCount = 0.0;
			TimelineObject->TryGetNumberField(TEXT("index"), EventIndex);
			TimelineObject->TryGetNumberField(TEXT("artifact_count"), ArtifactCount);
			const FString PhaseName = GetStringField(TimelineObject, TEXT("phase_name"));
			const FString EvidenceType = GetStringField(TimelineObject, TEXT("evidence_type"));
			const FString Label = EvidenceType.IsEmpty() ? PhaseName : FString::Printf(TEXT("%s/%s"), *PhaseName, *EvidenceType);
			if (!Label.IsEmpty())
			{
				const int32 DisplayIndex = FMath::Max(1, FMath::RoundToInt(EventIndex));
				const int32 DisplayArtifactCount = FMath::Max(0, FMath::RoundToInt(ArtifactCount));
				FString ArtifactHint;
				const TArray<TSharedPtr<FJsonValue>>* ArtifactPreviewValues = nullptr;
				if (TimelineObject->TryGetArrayField(TEXT("artifact_preview"), ArtifactPreviewValues) && ArtifactPreviewValues != nullptr && ArtifactPreviewValues->Num() > 0)
				{
					const TSharedPtr<FJsonValue>& FirstArtifactValue = (*ArtifactPreviewValues)[0];
					if (FirstArtifactValue.IsValid())
					{
						ArtifactHint = TruncateForCard(FirstArtifactValue->AsString(), 44);
					}
				}
				FString ArtifactSuffix;
				if (!ArtifactHint.IsEmpty())
				{
					ArtifactSuffix = FString::Printf(TEXT(" [%d artifacts: %s]"), DisplayArtifactCount, *ArtifactHint);
				}
				else if (DisplayArtifactCount > 0)
				{
					ArtifactSuffix = FString::Printf(TEXT(" [%d artifacts]"), DisplayArtifactCount);
				}
				TimelineParts.Add(FString::Printf(TEXT("%d. %s%s"), DisplayIndex, *Label, *ArtifactSuffix));
			}
		}
		if (!TimelineParts.IsEmpty())
		{
			OutOverview.EvidenceTimelineSummary = TruncateForCard(FString::Join(TimelineParts, TEXT(" -> ")), 180);
		}
	}

	const TSharedPtr<FJsonObject>* EvidenceRecordingObject = nullptr;
	if (Root->TryGetObjectField(TEXT("evidence_recording"), EvidenceRecordingObject) && EvidenceRecordingObject && EvidenceRecordingObject->IsValid())
	{
		double ItemCount = 0.0;
		double PendingCount = 0.0;
		double BlockedCount = 0.0;
		double RecordedCount = 0.0;
		(*EvidenceRecordingObject)->TryGetNumberField(TEXT("item_count"), ItemCount);
		(*EvidenceRecordingObject)->TryGetNumberField(TEXT("pending_count"), PendingCount);
		(*EvidenceRecordingObject)->TryGetNumberField(TEXT("blocked_count"), BlockedCount);
		(*EvidenceRecordingObject)->TryGetNumberField(TEXT("recorded_count"), RecordedCount);

		bool bHasReadinessPolicyRow = false;
		bool bHasReadinessRepairQueueRow = false;
		const TArray<TSharedPtr<FJsonValue>>* EvidenceItemValues = nullptr;
		if ((*EvidenceRecordingObject)->TryGetArrayField(TEXT("items"), EvidenceItemValues) && EvidenceItemValues != nullptr)
		{
			for (const TSharedPtr<FJsonValue>& ItemValue : *EvidenceItemValues)
			{
				const TSharedPtr<FJsonObject> ItemObject = ItemValue.IsValid() ? ItemValue->AsObject() : nullptr;
				if (!ItemObject.IsValid())
				{
					continue;
				}

				const FString ItemId = GetStringField(ItemObject, TEXT("id"));
				const FString EvidenceType = GetStringField(ItemObject, TEXT("evidence_type"));
				if (ItemId == TEXT("record_readiness_repair_queue") || EvidenceType == TEXT("readiness_repair_queue"))
				{
					bHasReadinessRepairQueueRow = true;
				}
				if (ItemId == TEXT("record_readiness_policy") || EvidenceType == TEXT("readiness_policy"))
				{
					bHasReadinessPolicyRow = true;
				}
				if (bHasReadinessRepairQueueRow && bHasReadinessPolicyRow)
				{
					break;
				}
			}
		}

		const int32 DisplayItemCount = FMath::Max(0, FMath::RoundToInt(ItemCount));
		if (DisplayItemCount > 0)
		{
			TArray<FString> EvidenceHints;
			if (bHasReadinessRepairQueueRow)
			{
				EvidenceHints.Add(TEXT("repair queue"));
			}
			if (bHasReadinessPolicyRow)
			{
				EvidenceHints.Add(TEXT("policy evidence"));
			}
			const FString EvidenceHintSuffix = EvidenceHints.IsEmpty()
				? FString()
				: FString::Printf(TEXT(", %s"), *FString::Join(EvidenceHints, TEXT(" + ")));
			OutOverview.EvidenceRecordingSummary = TruncateForCard(FString::Printf(
				TEXT("%d item(s), %d pending, %d blocked, %d recorded%s"),
				DisplayItemCount,
				FMath::Max(0, FMath::RoundToInt(PendingCount)),
				FMath::Max(0, FMath::RoundToInt(BlockedCount)),
				FMath::Max(0, FMath::RoundToInt(RecordedCount)),
				*EvidenceHintSuffix
			), 160);
		}
		else
		{
			OutOverview.EvidenceRecordingSummary = TEXT("clear");
		}
	}

	const TArray<TSharedPtr<FJsonValue>>* WorkflowActionValues = nullptr;
	if (Root->TryGetArrayField(TEXT("workflow_actions"), WorkflowActionValues) && WorkflowActionValues != nullptr)
	{
		for (const TSharedPtr<FJsonValue>& ActionValue : *WorkflowActionValues)
		{
			const TSharedPtr<FJsonObject> ActionObject = ActionValue.IsValid() ? ActionValue->AsObject() : nullptr;
			if (!ActionObject.IsValid())
			{
				continue;
			}

			OutOverview.WorkflowActionCount++;
			bool bWorkflowEnabled = false;
			ActionObject->TryGetBoolField(TEXT("enabled"), bWorkflowEnabled);
			if (bWorkflowEnabled)
			{
				OutOverview.EnabledWorkflowActionCount++;
			}

			if (GetStringField(ActionObject, TEXT("id")) != TEXT("record_evidence"))
			{
				continue;
			}

			const TSharedPtr<FJsonObject>* TargetObject = nullptr;
			if (!ActionObject->TryGetObjectField(TEXT("target_evidence_context"), TargetObject) || !TargetObject || !TargetObject->IsValid())
			{
				ActionObject->TryGetObjectField(TEXT("target_evidence_item"), TargetObject);
			}
			if (TargetObject && TargetObject->IsValid())
			{
				const FString TargetType = GetStringField(*TargetObject, TEXT("evidence_type"));
				const FString TargetId = GetStringField(*TargetObject, TEXT("id"));
				const FString TargetState = GetStringField(*TargetObject, TEXT("state"));
				double ArtifactCount = 0.0;
				if (!(*TargetObject)->TryGetNumberField(TEXT("artifact_count"), ArtifactCount))
				{
					(*TargetObject)->TryGetNumberField(TEXT("required_artifact_count"), ArtifactCount);
				}

				FString ArtifactHint;
				const TArray<TSharedPtr<FJsonValue>>* ArtifactPreviewValues = nullptr;
				if ((*TargetObject)->TryGetArrayField(TEXT("artifact_preview"), ArtifactPreviewValues) && ArtifactPreviewValues != nullptr && ArtifactPreviewValues->Num() > 0)
				{
					const TSharedPtr<FJsonValue>& FirstArtifactValue = (*ArtifactPreviewValues)[0];
					if (FirstArtifactValue.IsValid())
					{
						ArtifactHint = TruncateForCard(FirstArtifactValue->AsString(), 42);
					}
				}
				else if ((*TargetObject)->TryGetArrayField(TEXT("required_artifacts"), ArtifactPreviewValues) && ArtifactPreviewValues != nullptr && ArtifactPreviewValues->Num() > 0)
				{
					const TSharedPtr<FJsonValue>& FirstArtifactValue = (*ArtifactPreviewValues)[0];
					if (FirstArtifactValue.IsValid())
					{
						ArtifactHint = TruncateForCard(FirstArtifactValue->AsString(), 42);
					}
				}

				FString AssetHint;
				const TSharedPtr<FJsonObject>* GeneratedAssetObject = nullptr;
				if ((*TargetObject)->TryGetObjectField(TEXT("generated_asset"), GeneratedAssetObject) && GeneratedAssetObject && GeneratedAssetObject->IsValid())
				{
					const FString AssetName = GetStringField(*GeneratedAssetObject, TEXT("asset_name"));
					const FString AssetId = GetStringField(*GeneratedAssetObject, TEXT("asset_id"));
					const FString Provider = GetStringField(*GeneratedAssetObject, TEXT("provider"));
					const FString NextGate = GetStringField(*GeneratedAssetObject, TEXT("next_gate"));
					const FString DisplayAsset = AssetName.IsEmpty() ? AssetId : AssetName;
					if (!DisplayAsset.IsEmpty())
					{
						const FString ProviderSuffix = Provider.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *Provider);
						const FString GateHint = TruncateForCard(NextGate, 38);
						const FString GateSuffix = GateHint.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *GateHint);
						AssetHint = FString::Printf(TEXT("asset %s%s%s"), *DisplayAsset, *ProviderSuffix, *GateSuffix);
					}
				}

				const FString TargetName = TargetType.IsEmpty() ? TargetId : TargetType;
				if (!TargetName.IsEmpty())
				{
					const FString StateSuffix = TargetState.IsEmpty() ? FString() : FString::Printf(TEXT(" %s"), *TargetState);
					const FString ArtifactSuffix = ArtifactCount > 0.0
						? FString::Printf(TEXT(", %d artifact(s)"), FMath::Max(0, FMath::RoundToInt(ArtifactCount)))
						: FString();
					const FString DetailSource = !AssetHint.IsEmpty() ? AssetHint : ArtifactHint;
					const FString DetailSuffix = DetailSource.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *DetailSource);
					OutOverview.EvidenceTargetSummary = TruncateForCard(FString::Printf(
						TEXT("target %s%s%s%s"),
						*TargetName,
						*StateSuffix,
						*ArtifactSuffix,
						*DetailSuffix
					), 140);
					OutOverview.EvidenceTargetDetailSummary = DetailSource;
				}
			}
			break;
		}

		if (!OutOverview.EvidenceTargetSummary.IsEmpty())
		{
			OutOverview.EvidenceRecordingSummary = OutOverview.EvidenceRecordingSummary.IsEmpty()
				? OutOverview.EvidenceTargetSummary
				: TruncateForCard(FString::Printf(TEXT("%s; %s"), *OutOverview.EvidenceRecordingSummary, *OutOverview.EvidenceTargetSummary), 180);
		}
	}

	const TSharedPtr<FJsonObject>* NextSafeStepObject = nullptr;
	if (Root->TryGetObjectField(TEXT("next_safe_step"), NextSafeStepObject) && NextSafeStepObject && NextSafeStepObject->IsValid())
	{
		const FString State = GetStringField(*NextSafeStepObject, TEXT("state"));
		const FString NextTool = GetStringField(*NextSafeStepObject, TEXT("next_action_tool"));
		const FString NextId = GetStringField(*NextSafeStepObject, TEXT("next_action_id"));
		bool bCanExecuteNow = false;
		(*NextSafeStepObject)->TryGetBoolField(TEXT("can_execute_now"), bCanExecuteNow);
		bool bBridgeBlocked = false;
		(*NextSafeStepObject)->TryGetBoolField(TEXT("bridge_blocked"), bBridgeBlocked);
		const FString ActionName = NextTool.IsEmpty() ? NextId : NextTool;
		const FString GateHint = bBridgeBlocked ? TEXT(", bridge blocked") : TEXT("");
		const FString StepState = bCanExecuteNow ? FString(TEXT("ready")) : (State.IsEmpty() ? FString(TEXT("blocked")) : State);
		if (!ActionName.IsEmpty())
		{
			OutOverview.NextSafeStepSummary = FString::Printf(
				TEXT("%s %s%s"),
				*ActionName,
				*StepState,
				*GateHint
			);
		}
		else
		{
			OutOverview.NextSafeStepSummary = State.IsEmpty() ? TEXT("empty") : State;
		}
	}

	const TSharedPtr<FJsonObject>* FailureTriageObject = nullptr;
	if (Root->TryGetObjectField(TEXT("failure_triage"), FailureTriageObject) && FailureTriageObject && FailureTriageObject->IsValid())
	{
		const FString State = GetStringField(*FailureTriageObject, TEXT("state"));
		double ItemCount = 0.0;
		double BlockedCount = 0.0;
		double NeedsRepairCount = 0.0;
		(*FailureTriageObject)->TryGetNumberField(TEXT("item_count"), ItemCount);
		(*FailureTriageObject)->TryGetNumberField(TEXT("blocked_count"), BlockedCount);
		(*FailureTriageObject)->TryGetNumberField(TEXT("needs_repair_count"), NeedsRepairCount);
		OutOverview.FailureTriageCount = FMath::Max(0, FMath::RoundToInt(ItemCount));

		TArray<FString> ToolHints;
		const TArray<TSharedPtr<FJsonValue>>* RecommendedToolValues = nullptr;
		if ((*FailureTriageObject)->TryGetArrayField(TEXT("recommended_tools"), RecommendedToolValues) && RecommendedToolValues != nullptr)
		{
			for (const TSharedPtr<FJsonValue>& ToolValue : *RecommendedToolValues)
			{
				if (ToolHints.Num() >= 2)
				{
					break;
				}
				FString ToolName;
				if (ToolValue.IsValid() && ToolValue->TryGetString(ToolName) && !ToolName.IsEmpty())
				{
					ToolHints.Add(ToolName);
				}
			}
		}

		if (OutOverview.FailureTriageCount > 0)
		{
			const int32 DisplayBlockedCount = FMath::Max(0, FMath::RoundToInt(BlockedCount));
			const int32 DisplayNeedsRepairCount = FMath::Max(0, FMath::RoundToInt(NeedsRepairCount));
			const FString ToolSuffix = ToolHints.IsEmpty() ? FString() : FString::Printf(TEXT(", use %s"), *FString::Join(ToolHints, TEXT(" or ")));
			OutOverview.FailureTriageSummary = TruncateForCard(FString::Printf(
				TEXT("%s: %d signal(s), %d repair, %d blocked%s"),
				*(State.IsEmpty() ? FString(TEXT("review")) : State),
				OutOverview.FailureTriageCount,
				DisplayNeedsRepairCount,
				DisplayBlockedCount,
				*ToolSuffix
			), 180);
		}
		else
		{
			OutOverview.FailureTriageSummary = TEXT("clear");
		}
	}

	const TSharedPtr<FJsonObject>* AssetQualityObject = nullptr;
	if (Root->TryGetObjectField(TEXT("generated_asset_quality_gate"), AssetQualityObject) && AssetQualityObject && AssetQualityObject->IsValid())
	{
		const FString State = GetStringField(*AssetQualityObject, TEXT("state"));
		double AssetCount = 0.0;
		double ProviderPendingCount = 0.0;
		double ImportPendingCount = 0.0;
		double QualityPendingCount = 0.0;
		double ReadyCount = 0.0;
		double PlaceholderCount = 0.0;
		(*AssetQualityObject)->TryGetNumberField(TEXT("asset_count"), AssetCount);
		(*AssetQualityObject)->TryGetNumberField(TEXT("provider_pending_count"), ProviderPendingCount);
		(*AssetQualityObject)->TryGetNumberField(TEXT("import_pending_count"), ImportPendingCount);
		(*AssetQualityObject)->TryGetNumberField(TEXT("quality_pending_count"), QualityPendingCount);
		(*AssetQualityObject)->TryGetNumberField(TEXT("ready_count"), ReadyCount);
		(*AssetQualityObject)->TryGetNumberField(TEXT("placeholder_count"), PlaceholderCount);

		const int32 DisplayAssetCount = FMath::Max(0, FMath::RoundToInt(AssetCount));
		if (DisplayAssetCount > 0)
		{
			OutOverview.AssetQualitySummary = TruncateForCard(FString::Printf(
				TEXT("%s: %d asset(s), %d provider, %d import, %d quality, %d ready, %d placeholders"),
				*(State.IsEmpty() ? FString(TEXT("review")) : State),
				DisplayAssetCount,
				FMath::Max(0, FMath::RoundToInt(ProviderPendingCount)),
				FMath::Max(0, FMath::RoundToInt(ImportPendingCount)),
				FMath::Max(0, FMath::RoundToInt(QualityPendingCount)),
				FMath::Max(0, FMath::RoundToInt(ReadyCount)),
				FMath::Max(0, FMath::RoundToInt(PlaceholderCount))
			), 180);
		}
		else
		{
			OutOverview.AssetQualitySummary = TEXT("none");
		}
	}

	const TSharedPtr<FJsonObject>* ReadinessPolicyObject = nullptr;
	if (Root->TryGetObjectField(TEXT("readiness_policy"), ReadinessPolicyObject) && ReadinessPolicyObject && ReadinessPolicyObject->IsValid())
	{
		const FString State = GetStringField(*ReadinessPolicyObject, TEXT("state"));
		double BlockedPolicyCount = 0.0;
		(*ReadinessPolicyObject)->TryGetNumberField(TEXT("blocked_policy_count"), BlockedPolicyCount);

		TArray<FString> MissingGateHints;
		auto AppendMissingGatePreview = [&MissingGateHints](const TSharedPtr<FJsonObject>& PolicyObject, const TCHAR* FieldName)
		{
			const TSharedPtr<FJsonObject>* RowObject = nullptr;
			if (PolicyObject->TryGetObjectField(FieldName, RowObject) && RowObject && RowObject->IsValid())
			{
				const TArray<TSharedPtr<FJsonValue>>* MissingValues = nullptr;
				if ((*RowObject)->TryGetArrayField(TEXT("missing_gates"), MissingValues) && MissingValues != nullptr)
				{
					for (const TSharedPtr<FJsonValue>& MissingValue : *MissingValues)
					{
						if (MissingGateHints.Num() >= 3)
						{
							return;
						}
						FString MissingGate;
						if (MissingValue.IsValid() && MissingValue->TryGetString(MissingGate) && !MissingGate.IsEmpty())
						{
							MissingGateHints.Add(MissingGate);
						}
					}
				}
			}
		};
		AppendMissingGatePreview(*ReadinessPolicyObject, TEXT("editor_mutation"));
		AppendMissingGatePreview(*ReadinessPolicyObject, TEXT("paid_generation"));
		AppendMissingGatePreview(*ReadinessPolicyObject, TEXT("paid_animation_generation"));
		AppendMissingGatePreview(*ReadinessPolicyObject, TEXT("blueprint_mutation"));

		const int32 DisplayBlockedPolicyCount = FMath::Max(0, FMath::RoundToInt(BlockedPolicyCount));
		if (DisplayBlockedPolicyCount > 0)
		{
			const FString GateSuffix = MissingGateHints.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *FString::Join(MissingGateHints, TEXT(", ")));
			OutOverview.ReadinessPolicySummary = TruncateForCard(FString::Printf(
				TEXT("%s: %d blocked%s"),
				*(State.IsEmpty() ? FString(TEXT("blocked")) : State),
				DisplayBlockedPolicyCount,
				*GateSuffix
			), 180);
		}
		else
		{
			OutOverview.ReadinessPolicySummary = State.IsEmpty() ? TEXT("ready") : State;
		}
	}

	const TArray<TSharedPtr<FJsonValue>>* ActionValues = nullptr;
	if (Root->TryGetArrayField(TEXT("suggested_actions"), ActionValues) && ActionValues != nullptr)
	{
		FString FirstAction;
		FString FirstEnabledAction;
		for (const TSharedPtr<FJsonValue>& ActionValue : *ActionValues)
		{
			const TSharedPtr<FJsonObject> ActionObject = ActionValue.IsValid() ? ActionValue->AsObject() : nullptr;
			if (!ActionObject.IsValid())
			{
				continue;
			}

			const FString Label = GetStringField(ActionObject, TEXT("label"));
			if (Label.IsEmpty())
			{
				continue;
			}
			if (FirstAction.IsEmpty())
			{
				FirstAction = Label;
			}

			bool bEnabled = false;
			ActionObject->TryGetBoolField(TEXT("enabled"), bEnabled);
			if (bEnabled && FirstEnabledAction.IsEmpty())
			{
				FirstEnabledAction = Label;
			}
		}
		OutOverview.SuggestedAction = FirstEnabledAction.IsEmpty() ? FirstAction : FirstEnabledAction;
	}

	if (WorkflowActionValues != nullptr)
	{
		FString BestWorkflowAction;
		int32 BestWorkflowPriority = MAX_int32;
		for (const TSharedPtr<FJsonValue>& WorkflowValue : *WorkflowActionValues)
		{
			const TSharedPtr<FJsonObject> WorkflowObject = WorkflowValue.IsValid() ? WorkflowValue->AsObject() : nullptr;
			if (!WorkflowObject.IsValid())
			{
				continue;
			}

			bool bEnabled = false;
			WorkflowObject->TryGetBoolField(TEXT("enabled"), bEnabled);
			if (!bEnabled)
			{
				continue;
			}

			const FString ActionId = GetStringField(WorkflowObject, TEXT("id"));
			const FString Label = GetStringField(WorkflowObject, TEXT("label"));
			if (ActionId.IsEmpty() || Label.IsEmpty())
			{
				continue;
			}

			if (ActionId == TEXT("start_companion_session") && OutOverview.StartTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_start_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString ReadinessState = GetStringField(*TargetObject, TEXT("readiness_state"));
					const FString RecommendedNext = GetStringField(*TargetObject, TEXT("recommended_next"));
					bool bHasExistingLedger = false;
					(*TargetObject)->TryGetBoolField(TEXT("has_existing_ledger"), bHasExistingLedger);
					double EventCount = 0.0;
					double BlockedPolicyCount = 0.0;
					double QueueCount = 0.0;
					double GeneratedAssetCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("event_count"), EventCount);
					(*TargetObject)->TryGetNumberField(TEXT("blocked_policy_count"), BlockedPolicyCount);
					(*TargetObject)->TryGetNumberField(TEXT("queue_count"), QueueCount);
					(*TargetObject)->TryGetNumberField(TEXT("generated_asset_count"), GeneratedAssetCount);
					const FString ReadinessText = ReadinessState.IsEmpty() ? FString(TEXT("readiness")) : ReadinessState;
					const FString LedgerText = bHasExistingLedger ? FString::Printf(TEXT("%d event(s)"), FMath::Max(0, FMath::RoundToInt(EventCount))) : FString(TEXT("new ledger"));
					const FString NextSuffix = RecommendedNext.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *RecommendedNext);
					OutOverview.StartTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %s, %d policy blocker(s), %d queue(s), %d asset(s)%s"),
						*ReadinessText,
						*LedgerText,
						FMath::Max(0, FMath::RoundToInt(BlockedPolicyCount)),
						FMath::Max(0, FMath::RoundToInt(QueueCount)),
						FMath::Max(0, FMath::RoundToInt(GeneratedAssetCount)),
						*NextSuffix
					), 140);
				}
			}
			else if (ActionId == TEXT("refresh_companion_status") && OutOverview.StatusTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_status_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString ReadinessState = GetStringField(*TargetObject, TEXT("readiness_state"));
					const FString NextPhase = GetStringField(*TargetObject, TEXT("next_phase"));
					const FString NextTool = GetStringField(*TargetObject, TEXT("next_tool"));
					bool bHasSessionPlan = false;
					(*TargetObject)->TryGetBoolField(TEXT("has_session_plan"), bHasSessionPlan);
					double CompletedPhaseCount = 0.0;
					double BlockingGateCount = 0.0;
					double EvidenceItemCount = 0.0;
					double QueueCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("completed_phase_count"), CompletedPhaseCount);
					(*TargetObject)->TryGetNumberField(TEXT("blocking_gate_count"), BlockingGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("evidence_item_count"), EvidenceItemCount);
					(*TargetObject)->TryGetNumberField(TEXT("queue_count"), QueueCount);
					const FString ReadinessText = ReadinessState.IsEmpty() ? FString(TEXT("readiness")) : ReadinessState;
					const FString PlanText = bHasSessionPlan ? FString(TEXT("plan")) : FString(TEXT("plan needed"));
					const FString PhaseSuffix = NextPhase.IsEmpty() ? FString() : FString::Printf(TEXT(", next %s"), *NextPhase);
					const FString ToolSuffix = NextTool.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *NextTool);
					OutOverview.StatusTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %s, %d complete, %d blocker(s), %d evidence, %d queue(s)%s%s"),
						*ReadinessText,
						*PlanText,
						FMath::Max(0, FMath::RoundToInt(CompletedPhaseCount)),
						FMath::Max(0, FMath::RoundToInt(BlockingGateCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceItemCount)),
						FMath::Max(0, FMath::RoundToInt(QueueCount)),
						*PhaseSuffix,
						*ToolSuffix
					), 140);
				}
			}
			else if (ActionId == TEXT("generate_work_order") && OutOverview.WorkOrderTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_work_order_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString TargetPhase = GetStringField(*TargetObject, TEXT("target_phase"));
					const FString DisplayName = GetStringField(*TargetObject, TEXT("display_name"));
					const FString TemplateName = GetStringField(*TargetObject, TEXT("template_name"));
					const FString ReadinessState = GetStringField(*TargetObject, TEXT("readiness_state"));
					bool bHasSessionPlan = false;
					bool bHasStatusReceipt = false;
					(*TargetObject)->TryGetBoolField(TEXT("has_session_plan"), bHasSessionPlan);
					(*TargetObject)->TryGetBoolField(TEXT("has_status_receipt"), bHasStatusReceipt);
					double BlockingGateCount = 0.0;
					double OperationCount = 0.0;
					double EditorOperationCount = 0.0;
					double CompileCheckCount = 0.0;
					double EvidenceRequirementCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("blocking_gate_count"), BlockingGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("operation_count"), OperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("editor_operation_count"), EditorOperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("compile_check_count"), CompileCheckCount);
					(*TargetObject)->TryGetNumberField(TEXT("evidence_requirement_count"), EvidenceRequirementCount);
					const FString PhaseText = TargetPhase.IsEmpty() ? FString(TEXT("next phase")) : TargetPhase;
					const FString PlanText = bHasSessionPlan ? FString(TEXT("plan")) : FString(TEXT("plan needed"));
					const FString StatusStateText = bHasStatusReceipt ? FString(TEXT("status")) : FString(TEXT("status needed"));
					const FString ReadinessSuffix = ReadinessState.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *ReadinessState);
					const FString TemplateText = !DisplayName.IsEmpty() ? DisplayName : TemplateName;
					const FString TemplateSuffix = TemplateText.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *TemplateText);
					OutOverview.WorkOrderTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %s/%s, %d blocker(s), %d op(s), %d checklist, %d compile, %d evidence%s%s"),
						*PhaseText,
						*PlanText,
						*StatusStateText,
						FMath::Max(0, FMath::RoundToInt(BlockingGateCount)),
						FMath::Max(0, FMath::RoundToInt(OperationCount)),
						FMath::Max(0, FMath::RoundToInt(EditorOperationCount)),
						FMath::Max(0, FMath::RoundToInt(CompileCheckCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceRequirementCount)),
						*ReadinessSuffix,
						*TemplateSuffix
					), 140);
				}
			}
			else if (ActionId == TEXT("review_gameplay_template_plan") && OutOverview.GameplayTemplateTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_gameplay_template_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString DisplayName = GetStringField(*TargetObject, TEXT("display_name"));
					const FString TemplateName = GetStringField(*TargetObject, TEXT("template_name"));
					const FString TemplateText = !DisplayName.IsEmpty() ? DisplayName : TemplateName;
					double AssetCount = 0.0;
					double OperationCount = 0.0;
					double EditorOperationCount = 0.0;
					double BridgeRequiredOperationCount = 0.0;
					double CompileCheckCount = 0.0;
					double PieValidationCount = 0.0;
					double EvidenceRequirementCount = 0.0;
					double RepairInstructionCount = 0.0;
					double GeneratedAssetReplacementOperationCount = 0.0;
					double GeneratedAnimationPromptCount = 0.0;
					double GeneratedAnimationPaidMissingGateCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("asset_count"), AssetCount);
					(*TargetObject)->TryGetNumberField(TEXT("operation_count"), OperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("editor_operation_count"), EditorOperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("bridge_required_operation_count"), BridgeRequiredOperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("compile_check_count"), CompileCheckCount);
					(*TargetObject)->TryGetNumberField(TEXT("pie_validation_count"), PieValidationCount);
					(*TargetObject)->TryGetNumberField(TEXT("evidence_requirement_count"), EvidenceRequirementCount);
					(*TargetObject)->TryGetNumberField(TEXT("repair_instruction_count"), RepairInstructionCount);
					(*TargetObject)->TryGetNumberField(TEXT("generated_asset_replacement_operation_count"), GeneratedAssetReplacementOperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("generated_animation_prompt_count"), GeneratedAnimationPromptCount);
					(*TargetObject)->TryGetNumberField(TEXT("generated_animation_paid_missing_gate_count"), GeneratedAnimationPaidMissingGateCount);
					const FString ReviewName = TemplateText.IsEmpty() ? FString(TEXT("template")) : TemplateText;
					const FString SwapSuffix = GeneratedAssetReplacementOperationCount > 0.0
						? FString::Printf(TEXT(", %d swap"), FMath::Max(0, FMath::RoundToInt(GeneratedAssetReplacementOperationCount)))
						: FString();
					const FString AnimationSuffix = GeneratedAnimationPromptCount > 0.0
						? FString::Printf(TEXT(", %d anim"), FMath::Max(0, FMath::RoundToInt(GeneratedAnimationPromptCount)))
						: FString();
					const FString AnimationGateSuffix = GeneratedAnimationPaidMissingGateCount > 0.0
						? FString::Printf(TEXT(", %d anim gate"), FMath::Max(0, FMath::RoundToInt(GeneratedAnimationPaidMissingGateCount)))
						: FString();
					OutOverview.GameplayTemplateTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d asset(s), %d op(s), %d checklist/%d bridge, %d compile, %d PIE, %d evidence, %d repair%s%s%s"),
						*ReviewName,
						FMath::Max(0, FMath::RoundToInt(AssetCount)),
						FMath::Max(0, FMath::RoundToInt(OperationCount)),
						FMath::Max(0, FMath::RoundToInt(EditorOperationCount)),
						FMath::Max(0, FMath::RoundToInt(BridgeRequiredOperationCount)),
						FMath::Max(0, FMath::RoundToInt(CompileCheckCount)),
						FMath::Max(0, FMath::RoundToInt(PieValidationCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceRequirementCount)),
						FMath::Max(0, FMath::RoundToInt(RepairInstructionCount)),
						*SwapSuffix,
						*AnimationSuffix,
						*AnimationGateSuffix
					), 120);
				}
			}
			else if ((ActionId == TEXT("compile_placeholder_manifest") || ActionId == TEXT("continue_with_placeholder_fallback")) && OutOverview.PlaceholderTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_placeholder_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString GateState = GetStringField(*TargetObject, TEXT("generated_asset_state"));
					const FString ReadinessState = GetStringField(*TargetObject, TEXT("readiness_state"));
					bool bHasSessionPlan = false;
					(*TargetObject)->TryGetBoolField(TEXT("has_session_plan"), bHasSessionPlan);
					double AssetCount = 0.0;
					double ProviderPendingCount = 0.0;
					double PlaceholderCount = 0.0;
					double BlockingGateCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("asset_count"), AssetCount);
					(*TargetObject)->TryGetNumberField(TEXT("provider_pending_count"), ProviderPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("placeholder_count"), PlaceholderCount);
					(*TargetObject)->TryGetNumberField(TEXT("blocking_gate_count"), BlockingGateCount);
					FString TargetName;
					const TSharedPtr<FJsonObject>* TargetAssetObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("target_asset"), TargetAssetObject) && TargetAssetObject && TargetAssetObject->IsValid())
					{
						TargetName = GetStringField(*TargetAssetObject, TEXT("name"));
						if (TargetName.IsEmpty())
						{
							TargetName = GetStringField(*TargetAssetObject, TEXT("id"));
						}
					}
					const FString StateText = GateState.IsEmpty() ? FString(TEXT("assets")) : GateState;
					const FString PlanText = bHasSessionPlan ? FString(TEXT("plan")) : FString(TEXT("plan needed"));
					const FString ReadinessSuffix = ReadinessState.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *ReadinessState);
					const FString TargetSuffix = TargetName.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *TargetName);
					OutOverview.PlaceholderTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %s, %d asset(s), %d provider, %d placeholder(s), %d blocker(s)%s%s"),
						*StateText,
						*PlanText,
						FMath::Max(0, FMath::RoundToInt(AssetCount)),
						FMath::Max(0, FMath::RoundToInt(ProviderPendingCount)),
						FMath::Max(0, FMath::RoundToInt(PlaceholderCount)),
						FMath::Max(0, FMath::RoundToInt(BlockingGateCount)),
						*ReadinessSuffix,
						*TargetSuffix
					), 140);
				}
			}
			else if (ActionId == TEXT("resolve_blockers") && OutOverview.BlockerTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_blocker_resolution"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString Blocker = GetStringField(*TargetObject, TEXT("blocker"));
					const FString Strategy = GetStringField(*TargetObject, TEXT("recommended_strategy"));
					const FString Severity = GetStringField(*TargetObject, TEXT("severity"));
					const FString Tool = GetStringField(*TargetObject, TEXT("recommended_tool"));
					const FString EvidenceRequired = GetStringField(*TargetObject, TEXT("evidence_required"));
					bool bCanContinueOffline = false;
					(*TargetObject)->TryGetBoolField(TEXT("can_continue_offline"), bCanContinueOffline);
					const FString TargetName = Blocker.IsEmpty() ? Severity : Blocker;
					if (!TargetName.IsEmpty())
					{
						const FString StrategySuffix = Strategy.IsEmpty() ? FString() : FString::Printf(TEXT(" -> %s"), *Strategy);
						const FString ToolSuffix = Tool.IsEmpty() ? FString() : FString::Printf(TEXT(", use %s"), *Tool);
						const FString EvidenceSuffix = EvidenceRequired.IsEmpty() ? FString() : FString::Printf(TEXT(", evidence %s"), *EvidenceRequired);
						const FString OfflineSuffix = bCanContinueOffline ? FString(TEXT(", offline ok")) : FString(TEXT(", stop"));
						OutOverview.BlockerTargetSummary = TruncateForCard(FString::Printf(
							TEXT("target %s%s%s%s%s"),
							*TargetName,
							*StrategySuffix,
							*ToolSuffix,
							*EvidenceSuffix,
							*OfflineSuffix
						), 128);
					}
				}
			}
			else if (ActionId == TEXT("check_readiness") && OutOverview.ReadinessTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_readiness_policy_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double BlockedPolicyCount = 0.0;
					double MissingGateCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("blocked_policy_count"), BlockedPolicyCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_gate_count"), MissingGateCount);
					TArray<FString> MissingGatePreview;
					const TArray<TSharedPtr<FJsonValue>>* MissingGateValues = nullptr;
					if ((*TargetObject)->TryGetArrayField(TEXT("missing_gate_preview"), MissingGateValues) && MissingGateValues != nullptr)
					{
						for (const TSharedPtr<FJsonValue>& MissingGateValue : *MissingGateValues)
						{
							if (MissingGatePreview.Num() >= 3)
							{
								break;
							}
							FString MissingGate;
							if (MissingGateValue.IsValid() && MissingGateValue->TryGetString(MissingGate) && !MissingGate.IsEmpty())
							{
								MissingGatePreview.Add(MissingGate);
							}
						}
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("readiness")) : State;
					const FString MissingSuffix = MissingGatePreview.Num() > 0
						? FString::Printf(TEXT(", %s"), *FString::Join(MissingGatePreview, TEXT(", ")))
						: FString();
					OutOverview.ReadinessTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d policy area(s), %d missing gate(s)%s"),
						*ReviewState,
						FMath::Max(0, FMath::RoundToInt(BlockedPolicyCount)),
						FMath::Max(0, FMath::RoundToInt(MissingGateCount)),
						*MissingSuffix
					), 120);
				}
			}
			else if (ActionId == TEXT("review_readiness_repair_queue") && OutOverview.ReadinessRepairTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_readiness_repair_queue_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString RecommendedNext = GetStringField(*TargetObject, TEXT("recommended_next"));
					const FString NextGate = GetStringField(*TargetObject, TEXT("next_gate"));
					const FString NextTool = GetStringField(*TargetObject, TEXT("next_tool"));
					const FString NextRequiredCommand = GetStringField(*TargetObject, TEXT("next_required_command"));
					const FString PriorityPolicy = GetStringField(*TargetObject, TEXT("priority_policy"));
					double ActionCount = 0.0;
					double BlockingGateCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("action_count"), ActionCount);
					(*TargetObject)->TryGetNumberField(TEXT("blocking_gate_count"), BlockingGateCount);
					bool bStopBeforeRunningRepair = true;
					(*TargetObject)->TryGetBoolField(TEXT("stop_before_running_repair"), bStopBeforeRunningRepair);
					const FString TargetName = !RecommendedNext.IsEmpty()
						? RecommendedNext
						: (!NextGate.IsEmpty() ? NextGate : FString(TEXT("repair queue")));
					const FString GateSuffix = NextGate.IsEmpty() ? FString() : FString::Printf(TEXT(", gate %s"), *NextGate);
					const FString ToolName = NextTool.IsEmpty() ? NextRequiredCommand : NextTool;
					const FString ToolSuffix = ToolName.IsEmpty() ? FString() : FString::Printf(TEXT(", via %s"), *ToolName);
					const FString PolicySuffix = PriorityPolicy.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *PriorityPolicy);
					const FString SafetySuffix = bStopBeforeRunningRepair ? FString(TEXT(", review-only")) : FString();
					OutOverview.ReadinessRepairTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s%s, %d action(s), %d blocker(s)%s%s"),
						*TargetName,
						*GateSuffix,
						*ToolSuffix,
						FMath::Max(0, FMath::RoundToInt(ActionCount)),
						FMath::Max(0, FMath::RoundToInt(BlockingGateCount)),
						*PolicySuffix,
						*SafetySuffix
					), 128);
				}
			}
			else if (ActionId == TEXT("review_platform_preflight_gate") && OutOverview.PlatformPreflightTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_platform_preflight_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString DirtyRisk = GetStringField(*TargetObject, TEXT("dirty_risk"));
					const FString CurrentBranch = GetStringField(*TargetObject, TEXT("current_branch"));
					const FString BranchRole = GetStringField(*TargetObject, TEXT("branch_role"));
					const FString BuildStatus = GetStringField(*TargetObject, TEXT("last_plugin_build_status"));
					const FString BuildWrapperStatus = GetStringField(*TargetObject, TEXT("build_wrapper_status"));
					const FString BuildHealth = GetStringField(*TargetObject, TEXT("build_health"));
					double PreflightToolCount = 0.0;
					double RecordedCount = 0.0;
					double BuildWrapperMissingReferenceCount = 0.0;
					double BuildWarningCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("tool_count"), PreflightToolCount);
					(*TargetObject)->TryGetNumberField(TEXT("recorded_count"), RecordedCount);
					(*TargetObject)->TryGetNumberField(TEXT("build_wrapper_missing_reference_count"), BuildWrapperMissingReferenceCount);
					(*TargetObject)->TryGetNumberField(TEXT("last_plugin_build_warning_count"), BuildWarningCount);
					bool bBridgeReady = false;
					bool bChatReady = false;
					bool bPlatformReady = false;
					(*TargetObject)->TryGetBoolField(TEXT("bridge_ready"), bBridgeReady);
					(*TargetObject)->TryGetBoolField(TEXT("chat_ready"), bChatReady);
					(*TargetObject)->TryGetBoolField(TEXT("ready_for_platform_stability"), bPlatformReady);
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("preflight")) : State;
					const FString RiskLabel = DirtyRisk.IsEmpty() ? FString(TEXT("unknown")) : DirtyRisk;
					const FString BuildLabel = BuildStatus.IsEmpty() ? FString(TEXT("unknown")) : BuildStatus;
					const FString WrapperLabel = BuildWrapperStatus.IsEmpty() ? FString(TEXT("unknown")) : BuildWrapperStatus;
					const FString HealthLabel = BuildHealth.IsEmpty() ? FString(TEXT("unknown")) : BuildHealth;
					const FString WarningSeverity = GetStringField(*TargetObject, TEXT("last_plugin_build_warning_severity"));
					const FString WarningLabel = WarningSeverity.IsEmpty() ? FString(TEXT("unknown")) : WarningSeverity;
					const FString BranchLabel = CurrentBranch.IsEmpty() ? FString(TEXT("unknown")) : CurrentBranch;
					const FString BranchRoleLabel = BranchRole.IsEmpty() ? FString(TEXT("unknown")) : BranchRole;
					OutOverview.PlatformPreflightTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, branch %s/%s, tools %d/%d, dirty %s, bridge %s, chat %s, platform %s, wrapper %s/%s, missing %d, build %s, warnings %d/%s"),
						*ReviewState,
						*BranchLabel,
						*BranchRoleLabel,
						FMath::Max(0, FMath::RoundToInt(PreflightToolCount)),
						FMath::Max(0, FMath::RoundToInt(RecordedCount)),
						*RiskLabel,
						bBridgeReady ? TEXT("ready") : TEXT("blocked"),
						bChatReady ? TEXT("ready") : TEXT("blocked"),
						bPlatformReady ? TEXT("ready") : TEXT("blocked"),
						*WrapperLabel,
						*HealthLabel,
						FMath::Max(0, FMath::RoundToInt(BuildWrapperMissingReferenceCount)),
						*BuildLabel,
						FMath::Max(0, FMath::RoundToInt(BuildWarningCount)),
						*WarningLabel
					), 120);
				}
			}
			else if (ActionId == TEXT("review_live_editor_bridge_gate") && OutOverview.LiveEditorBridgeTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_live_editor_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString NextTool = GetStringField(*TargetObject, TEXT("next_action_tool"));
					double MissingGateCount = 0.0;
					double QueuedActionCount = 0.0;
					double ExecutableQueueCount = 0.0;
					double BridgeBlockedCount = 0.0;
					double RuntimeProofCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("missing_gate_count"), MissingGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("queued_action_count"), QueuedActionCount);
					(*TargetObject)->TryGetNumberField(TEXT("executable_queue_count"), ExecutableQueueCount);
					(*TargetObject)->TryGetNumberField(TEXT("bridge_blocked_count"), BridgeBlockedCount);
					(*TargetObject)->TryGetNumberField(TEXT("runtime_proof_count"), RuntimeProofCount);
					bool bBridgeReady = false;
					bool bCanExecuteNow = false;
					bool bCanVerifyNow = false;
					(*TargetObject)->TryGetBoolField(TEXT("bridge_ready"), bBridgeReady);
					(*TargetObject)->TryGetBoolField(TEXT("can_execute_now"), bCanExecuteNow);
					(*TargetObject)->TryGetBoolField(TEXT("can_verify_now"), bCanVerifyNow);
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("bridge")) : State;
					const FString ToolSuffix = NextTool.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *NextTool);
					OutOverview.LiveEditorBridgeTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s, bridge %s, %d gate(s), %d queued, %d executable, %d blocked, exec %s, PIE %s, %d proof"),
						*ReviewState,
						*ToolSuffix,
						bBridgeReady ? TEXT("ready") : TEXT("blocked"),
						FMath::Max(0, FMath::RoundToInt(MissingGateCount)),
						FMath::Max(0, FMath::RoundToInt(QueuedActionCount)),
						FMath::Max(0, FMath::RoundToInt(ExecutableQueueCount)),
						FMath::Max(0, FMath::RoundToInt(BridgeBlockedCount)),
						bCanExecuteNow ? TEXT("ready") : TEXT("blocked"),
						bCanVerifyNow ? TEXT("ready") : TEXT("blocked"),
						FMath::Max(0, FMath::RoundToInt(RuntimeProofCount))
					), 120);
				}
			}
			else if (ActionId == TEXT("review_wip_promotion_gate") && OutOverview.WipPromotionTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_wip_promotion_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString DirtyRisk = GetStringField(*TargetObject, TEXT("dirty_risk"));
					const FString CurrentBranch = GetStringField(*TargetObject, TEXT("current_branch"));
					const FString BranchRole = GetStringField(*TargetObject, TEXT("branch_role"));
					const FString BuildStatus = GetStringField(*TargetObject, TEXT("last_plugin_build_status"));
					const FString BuildWrapperStatus = GetStringField(*TargetObject, TEXT("build_wrapper_status"));
					const FString BuildHealth = GetStringField(*TargetObject, TEXT("build_health"));
					const FString TargetReviewGroup = GetStringField(*TargetObject, TEXT("target_review_group"));
					double ReadyGateCount = 0.0;
					double GateCount = 0.0;
					double TrackedChangeCount = 0.0;
					double ReviewBatchCount = 0.0;
					double EvidenceMatrixCount = 0.0;
					double EvidenceUnresolvedCount = 0.0;
					double FocusedTestCommandCount = 0.0;
					double TestLaneViolationCount = 0.0;
					double FailingWrapperCount = 0.0;
					double BuildWrapperMissingReferenceCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("ready_gate_count"), ReadyGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("gate_count"), GateCount);
					(*TargetObject)->TryGetNumberField(TEXT("tracked_change_count"), TrackedChangeCount);
					(*TargetObject)->TryGetNumberField(TEXT("dirty_promotion_review_batch_count"), ReviewBatchCount);
					(*TargetObject)->TryGetNumberField(TEXT("dirty_promotion_evidence_review_matrix_count"), EvidenceMatrixCount);
					(*TargetObject)->TryGetNumberField(TEXT("dirty_promotion_evidence_unresolved_count"), EvidenceUnresolvedCount);
					(*TargetObject)->TryGetNumberField(TEXT("dirty_promotion_focused_test_command_count"), FocusedTestCommandCount);
					(*TargetObject)->TryGetNumberField(TEXT("test_lane_violation_count"), TestLaneViolationCount);
					(*TargetObject)->TryGetNumberField(TEXT("failing_wrapper_count"), FailingWrapperCount);
					(*TargetObject)->TryGetNumberField(TEXT("build_wrapper_missing_reference_count"), BuildWrapperMissingReferenceCount);
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("promotion")) : State;
					const FString RiskLabel = DirtyRisk.IsEmpty() ? FString(TEXT("unknown")) : DirtyRisk;
					const FString BuildLabel = BuildStatus.IsEmpty() ? FString(TEXT("unknown")) : BuildStatus;
					const FString WrapperLabel = BuildWrapperStatus.IsEmpty() ? FString(TEXT("unknown")) : BuildWrapperStatus;
					const FString HealthLabel = BuildHealth.IsEmpty() ? FString(TEXT("unknown")) : BuildHealth;
					const FString BranchLabel = CurrentBranch.IsEmpty() ? FString(TEXT("unknown")) : CurrentBranch;
					const FString BranchRoleLabel = BranchRole.IsEmpty() ? FString(TEXT("unknown")) : BranchRole;
					const FString TargetSuffix = TargetReviewGroup.IsEmpty() ? FString() : FString::Printf(TEXT(", target %s"), *TargetReviewGroup);
					OutOverview.WipPromotionTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, branch %s/%s, %d/%d gate(s), dirty %s%s, tracked %d, batch %d, evidence %d/%d open, tests %d, lane %d, wrapper %d, build %s/%s, refs %d, last %s"),
						*ReviewState,
						*BranchLabel,
						*BranchRoleLabel,
						FMath::Max(0, FMath::RoundToInt(ReadyGateCount)),
						FMath::Max(0, FMath::RoundToInt(GateCount)),
						*RiskLabel,
						*TargetSuffix,
						FMath::Max(0, FMath::RoundToInt(TrackedChangeCount)),
						FMath::Max(0, FMath::RoundToInt(ReviewBatchCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceUnresolvedCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceMatrixCount)),
						FMath::Max(0, FMath::RoundToInt(FocusedTestCommandCount)),
						FMath::Max(0, FMath::RoundToInt(TestLaneViolationCount)),
						FMath::Max(0, FMath::RoundToInt(FailingWrapperCount)),
						*WrapperLabel,
						*HealthLabel,
						FMath::Max(0, FMath::RoundToInt(BuildWrapperMissingReferenceCount)),
						*BuildLabel
					), 120);
				}
			}
			else if (ActionId == TEXT("review_bridge_wrapper_coverage") && OutOverview.BridgeWrapperTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_bridge_wrapper_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double CapabilityCount = 0.0;
					double CoveredCapabilityCount = 0.0;
					double CommandCount = 0.0;
					double SchemaCoveredCommandCount = 0.0;
					double SchemaCommandCount = 0.0;
					double FailingCapabilityCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("capability_count"), CapabilityCount);
					(*TargetObject)->TryGetNumberField(TEXT("covered_capability_count"), CoveredCapabilityCount);
					(*TargetObject)->TryGetNumberField(TEXT("command_count"), CommandCount);
					(*TargetObject)->TryGetNumberField(TEXT("schema_covered_command_count"), SchemaCoveredCommandCount);
					(*TargetObject)->TryGetNumberField(TEXT("schema_command_count"), SchemaCommandCount);
					(*TargetObject)->TryGetNumberField(TEXT("failing_capability_count"), FailingCapabilityCount);
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("coverage")) : State;
					OutOverview.BridgeWrapperTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d/%d capability, %d command(s), schema %d/%d, %d issue(s)"),
						*ReviewState,
						FMath::Max(0, FMath::RoundToInt(CoveredCapabilityCount)),
						FMath::Max(0, FMath::RoundToInt(CapabilityCount)),
						FMath::Max(0, FMath::RoundToInt(CommandCount)),
						FMath::Max(0, FMath::RoundToInt(SchemaCoveredCommandCount)),
						FMath::Max(0, FMath::RoundToInt(SchemaCommandCount)),
						FMath::Max(0, FMath::RoundToInt(FailingCapabilityCount))
					), 96);
				}
			}
			else if (ActionId == TEXT("review_blueprint_mutation_gate") && OutOverview.BlueprintMutationTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_blueprint_mutation_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString TemplateName = GetStringField(*TargetObject, TEXT("display_name")).IsEmpty()
						? GetStringField(*TargetObject, TEXT("template_name"))
						: GetStringField(*TargetObject, TEXT("display_name"));
					double MissingGateCount = 0.0;
					double EvidenceRequiredCount = 0.0;
					double OperationCount = 0.0;
					double EditorOperationCount = 0.0;
					double CompileCheckCount = 0.0;
					double QueuedActionCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("missing_gate_count"), MissingGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("evidence_required_count"), EvidenceRequiredCount);
					(*TargetObject)->TryGetNumberField(TEXT("operation_count"), OperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("editor_operation_count"), EditorOperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("compile_check_count"), CompileCheckCount);
					(*TargetObject)->TryGetNumberField(TEXT("queued_action_count"), QueuedActionCount);
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("blueprint")) : State;
					const FString TemplateSuffix = TemplateName.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *TemplateName);
					OutOverview.BlueprintMutationTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s, %d gate(s), %d evidence, %d op(s), %d checklist, %d compile, %d queued"),
						*ReviewState,
						*TemplateSuffix,
						FMath::Max(0, FMath::RoundToInt(MissingGateCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceRequiredCount)),
						FMath::Max(0, FMath::RoundToInt(OperationCount)),
						FMath::Max(0, FMath::RoundToInt(EditorOperationCount)),
						FMath::Max(0, FMath::RoundToInt(CompileCheckCount)),
						FMath::Max(0, FMath::RoundToInt(QueuedActionCount))
					), 120);
				}
			}
			else if (ActionId == TEXT("review_test_lane_gates") && OutOverview.TestLaneTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_test_lane_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double OfflineCount = 0.0;
					double LiveBridgeCount = 0.0;
					double LiveBridgeManualCount = 0.0;
					double PaidProviderCount = 0.0;
					double ManualCount = 0.0;
					double ViolationCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("offline_count"), OfflineCount);
					(*TargetObject)->TryGetNumberField(TEXT("live_bridge_count"), LiveBridgeCount);
					(*TargetObject)->TryGetNumberField(TEXT("live_bridge_manual_count"), LiveBridgeManualCount);
					(*TargetObject)->TryGetNumberField(TEXT("paid_provider_count"), PaidProviderCount);
					(*TargetObject)->TryGetNumberField(TEXT("manual_count"), ManualCount);
					(*TargetObject)->TryGetNumberField(TEXT("violation_count"), ViolationCount);
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("lanes")) : State;
					OutOverview.TestLaneTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d offline, %d live, %d paid, %d manual, %d violation(s)"),
						*ReviewState,
						FMath::Max(0, FMath::RoundToInt(OfflineCount)),
						FMath::Max(0, FMath::RoundToInt(LiveBridgeCount + LiveBridgeManualCount)),
						FMath::Max(0, FMath::RoundToInt(PaidProviderCount)),
						FMath::Max(0, FMath::RoundToInt(ManualCount)),
						FMath::Max(0, FMath::RoundToInt(ViolationCount))
					), 96);
				}
			}
			else if (ActionId == TEXT("resume_companion_session") && OutOverview.ResumeTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_resume_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString NextPhase = GetStringField(*TargetObject, TEXT("next_phase"));
					const FString WorkOrderPhase = GetStringField(*TargetObject, TEXT("work_order_phase"));
					const FString LatestPhase = GetStringField(*TargetObject, TEXT("latest_phase"));
					const FString NextTool = GetStringField(*TargetObject, TEXT("next_tool"));
					double EventCount = 0.0;
					double CompletedPhaseCount = 0.0;
					double BlockingGateCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("event_count"), EventCount);
					(*TargetObject)->TryGetNumberField(TEXT("completed_phase_count"), CompletedPhaseCount);
					(*TargetObject)->TryGetNumberField(TEXT("blocking_gate_count"), BlockingGateCount);
					const FString TargetPhase = !NextPhase.IsEmpty() ? NextPhase : (!WorkOrderPhase.IsEmpty() ? WorkOrderPhase : LatestPhase);
					const FString PhaseSuffix = TargetPhase.IsEmpty() ? FString() : FString::Printf(TEXT(", next %s"), *TargetPhase);
					const FString ToolSuffix = NextTool.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *NextTool);
					OutOverview.ResumeTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%d event(s), %d complete, %d blocker(s)%s%s"),
						FMath::Max(0, FMath::RoundToInt(EventCount)),
						FMath::Max(0, FMath::RoundToInt(CompletedPhaseCount)),
						FMath::Max(0, FMath::RoundToInt(BlockingGateCount)),
						*PhaseSuffix,
						*ToolSuffix
					), 120);
				}
			}
			else if (ActionId == TEXT("show_companion_dashboard") && OutOverview.DashboardTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_dashboard_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString ReadinessState = GetStringField(*TargetObject, TEXT("readiness_state"));
					const FString AssetState = GetStringField(*TargetObject, TEXT("generated_asset_state"));
					const FString RuntimeState = GetStringField(*TargetObject, TEXT("runtime_review_state"));
					const FString RepairState = GetStringField(*TargetObject, TEXT("repair_loop_state"));
					double EventCount = 0.0;
					double BlockingGateCount = 0.0;
					double QueuedActionCount = 0.0;
					double EvidenceItemCount = 0.0;
					double GeneratedAssetCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("event_count"), EventCount);
					(*TargetObject)->TryGetNumberField(TEXT("blocking_gate_count"), BlockingGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("queued_action_count"), QueuedActionCount);
					(*TargetObject)->TryGetNumberField(TEXT("evidence_item_count"), EvidenceItemCount);
					(*TargetObject)->TryGetNumberField(TEXT("generated_asset_count"), GeneratedAssetCount);
					const FString ReadinessText = ReadinessState.IsEmpty() ? FString(TEXT("readiness")) : ReadinessState;
					const FString AssetSuffix = AssetState.IsEmpty() ? FString() : FString::Printf(TEXT(", assets %s"), *AssetState);
					const FString RuntimeSuffix = RuntimeState.IsEmpty() ? FString() : FString::Printf(TEXT(", runtime %s"), *RuntimeState);
					const FString RepairSuffix = RepairState.IsEmpty() ? FString() : FString::Printf(TEXT(", repair %s"), *RepairState);
					OutOverview.DashboardTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d event(s), %d blocker(s), %d queued, %d evidence, %d asset(s)%s%s%s"),
						*ReadinessText,
						FMath::Max(0, FMath::RoundToInt(EventCount)),
						FMath::Max(0, FMath::RoundToInt(BlockingGateCount)),
						FMath::Max(0, FMath::RoundToInt(QueuedActionCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceItemCount)),
						FMath::Max(0, FMath::RoundToInt(GeneratedAssetCount)),
						*AssetSuffix,
						*RuntimeSuffix,
						*RepairSuffix
					), 140);
				}
			}
			else if (ActionId == TEXT("resolve_generated_asset") && OutOverview.GeneratedAssetTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_generated_asset_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString AssetName = GetStringField(*TargetObject, TEXT("name"));
					const FString AssetId = GetStringField(*TargetObject, TEXT("id"));
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString NextGate = GetStringField(*TargetObject, TEXT("next_gate"));
					const FString TargetName = AssetName.IsEmpty() ? AssetId : AssetName;
					if (!TargetName.IsEmpty())
					{
						const FString StateSuffix = State.IsEmpty() ? FString() : FString::Printf(TEXT(" %s"), *State);
						const FString GateSuffix = NextGate.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *NextGate);
						OutOverview.GeneratedAssetTargetSummary = TruncateForCard(FString::Printf(
							TEXT("target %s%s%s"),
							*TargetName,
							*StateSuffix,
							*GateSuffix
						), 96);
					}
				}
			}
			else if (ActionId == TEXT("review_generated_asset_gate") && OutOverview.GeneratedAssetReviewTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* ReviewObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_generated_asset_review_context"), ReviewObject) && ReviewObject && ReviewObject->IsValid())
				{
					const FString State = GetStringField(*ReviewObject, TEXT("state"));
					double AssetCount = 0.0;
					double ProviderPendingCount = 0.0;
					double ImportPendingCount = 0.0;
					double QualityPendingCount = 0.0;
					double PlaceholderCount = 0.0;
					(*ReviewObject)->TryGetNumberField(TEXT("asset_count"), AssetCount);
					(*ReviewObject)->TryGetNumberField(TEXT("provider_pending_count"), ProviderPendingCount);
					(*ReviewObject)->TryGetNumberField(TEXT("import_pending_count"), ImportPendingCount);
					(*ReviewObject)->TryGetNumberField(TEXT("quality_pending_count"), QualityPendingCount);
					(*ReviewObject)->TryGetNumberField(TEXT("placeholder_count"), PlaceholderCount);
					const TSharedPtr<FJsonObject>* AssetObject = nullptr;
					FString AssetName;
					FString AssetState;
					if ((*ReviewObject)->TryGetObjectField(TEXT("target_asset"), AssetObject) && AssetObject && AssetObject->IsValid())
					{
						AssetName = GetStringField(*AssetObject, TEXT("name"));
						AssetState = GetStringField(*AssetObject, TEXT("state"));
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("review")) : State;
					const FString AssetSuffix = AssetName.IsEmpty()
						? FString()
						: (AssetState.IsEmpty()
							? FString::Printf(TEXT(", %s"), *AssetName)
							: FString::Printf(TEXT(", %s %s"), *AssetName, *AssetState));
					OutOverview.GeneratedAssetReviewTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s, %d asset(s), %d provider, %d import, %d quality, %d placeholder(s)"),
						*ReviewState,
						*AssetSuffix,
						FMath::Max(0, FMath::RoundToInt(AssetCount)),
						FMath::Max(0, FMath::RoundToInt(ProviderPendingCount)),
						FMath::Max(0, FMath::RoundToInt(ImportPendingCount)),
						FMath::Max(0, FMath::RoundToInt(QualityPendingCount)),
						FMath::Max(0, FMath::RoundToInt(PlaceholderCount))
					), 120);
				}
			}
			else if (ActionId == TEXT("review_generated_asset_lifecycle_gate") && OutOverview.GeneratedAssetLifecycleTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* LifecycleObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_generated_asset_lifecycle_context"), LifecycleObject) && LifecycleObject && LifecycleObject->IsValid())
				{
					const FString State = GetStringField(*LifecycleObject, TEXT("state"));
					double ManifestCount = 0.0;
					double AssetCount = 0.0;
					double ProviderPendingCount = 0.0;
					double ImportPendingCount = 0.0;
					double QualityPendingCount = 0.0;
					double PlaceholderCount = 0.0;
					double MissingStageCount = 0.0;
					double StopConditionCount = 0.0;
					(*LifecycleObject)->TryGetNumberField(TEXT("manifest_count"), ManifestCount);
					(*LifecycleObject)->TryGetNumberField(TEXT("asset_count"), AssetCount);
					(*LifecycleObject)->TryGetNumberField(TEXT("provider_pending_count"), ProviderPendingCount);
					(*LifecycleObject)->TryGetNumberField(TEXT("import_pending_count"), ImportPendingCount);
					(*LifecycleObject)->TryGetNumberField(TEXT("quality_pending_count"), QualityPendingCount);
					(*LifecycleObject)->TryGetNumberField(TEXT("placeholder_count"), PlaceholderCount);
					(*LifecycleObject)->TryGetNumberField(TEXT("missing_stage_count"), MissingStageCount);
					(*LifecycleObject)->TryGetNumberField(TEXT("stop_condition_count"), StopConditionCount);
					FString AssetName;
					FString AssetState;
					const TSharedPtr<FJsonObject>* AssetObject = nullptr;
					if ((*LifecycleObject)->TryGetObjectField(TEXT("target_asset"), AssetObject) && AssetObject && AssetObject->IsValid())
					{
						AssetName = GetStringField(*AssetObject, TEXT("name"));
						if (AssetName.IsEmpty())
						{
							AssetName = GetStringField(*AssetObject, TEXT("id"));
						}
						AssetState = GetStringField(*AssetObject, TEXT("state"));
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("lifecycle")) : State;
					const FString AssetSuffix = AssetName.IsEmpty()
						? FString()
						: (AssetState.IsEmpty()
							? FString::Printf(TEXT(", %s"), *AssetName)
							: FString::Printf(TEXT(", %s %s"), *AssetName, *AssetState));
					OutOverview.GeneratedAssetLifecycleTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s, %d manifest(s), %d asset(s), %d provider, %d import, %d quality, %d placeholder, %d stage(s), %d stop"),
						*ReviewState,
						*AssetSuffix,
						FMath::Max(0, FMath::RoundToInt(ManifestCount)),
						FMath::Max(0, FMath::RoundToInt(AssetCount)),
						FMath::Max(0, FMath::RoundToInt(ProviderPendingCount)),
						FMath::Max(0, FMath::RoundToInt(ImportPendingCount)),
						FMath::Max(0, FMath::RoundToInt(QualityPendingCount)),
						FMath::Max(0, FMath::RoundToInt(PlaceholderCount)),
						FMath::Max(0, FMath::RoundToInt(MissingStageCount)),
						FMath::Max(0, FMath::RoundToInt(StopConditionCount))
					), 128);
				}
			}
			else if (ActionId == TEXT("compile_asset_lifecycle_manifest") && OutOverview.AssetLifecycleCompileTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_asset_lifecycle_compile_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					bool bHasSessionPlan = false;
					bool bWriteManifestRecommended = false;
					(*TargetObject)->TryGetBoolField(TEXT("has_session_plan"), bHasSessionPlan);
					(*TargetObject)->TryGetBoolField(TEXT("write_manifest_recommended"), bWriteManifestRecommended);
					double PlannedAssetPromptCount = 0.0;
					double PlannedAnimationPromptCount = 0.0;
					double ManifestCount = 0.0;
					double ManifestPendingCount = 0.0;
					double EstimatedUthanaSeconds = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("planned_asset_prompt_count"), PlannedAssetPromptCount);
					(*TargetObject)->TryGetNumberField(TEXT("planned_animation_prompt_count"), PlannedAnimationPromptCount);
					(*TargetObject)->TryGetNumberField(TEXT("manifest_count"), ManifestCount);
					(*TargetObject)->TryGetNumberField(TEXT("manifest_pending_count"), ManifestPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("estimated_uthana_motion_seconds"), EstimatedUthanaSeconds);
					int32 FutureGateCount = 0;
					const TArray<TSharedPtr<FJsonValue>>* MissingFutureGateValues = nullptr;
					if ((*TargetObject)->TryGetArrayField(TEXT("missing_future_gate_preview"), MissingFutureGateValues) && MissingFutureGateValues != nullptr)
					{
						FutureGateCount = MissingFutureGateValues->Num();
					}

					const FString ReviewState = State.IsEmpty() ? FString(TEXT("compile")) : State;
					const FString PlanText = bHasSessionPlan ? FString(TEXT("plan")) : FString(TEXT("plan needed"));
					const FString WriteSuffix = bWriteManifestRecommended ? FString(TEXT(", write")) : FString();
					const FString UthanaSuffix = EstimatedUthanaSeconds > 0.0
						? FString::Printf(TEXT(", %ds motion"), FMath::Max(0, FMath::RoundToInt(EstimatedUthanaSeconds)))
						: FString();
					OutOverview.AssetLifecycleCompileTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %s, %d mesh, %d anim, %d manifest(s), %d pending, %d future gate(s)%s%s"),
						*ReviewState,
						*PlanText,
						FMath::Max(0, FMath::RoundToInt(PlannedAssetPromptCount)),
						FMath::Max(0, FMath::RoundToInt(PlannedAnimationPromptCount)),
						FMath::Max(0, FMath::RoundToInt(ManifestCount)),
						FMath::Max(0, FMath::RoundToInt(ManifestPendingCount)),
						FMath::Max(0, FutureGateCount),
						*UthanaSuffix,
						*WriteSuffix
					), 128);
				}
			}
			else if (ActionId == TEXT("review_generated_animation_lifecycle_gate") && OutOverview.GeneratedAnimationLifecycleTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_generated_animation_lifecycle_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString Provider = GetStringField(*TargetObject, TEXT("animation_provider"));
					double AnimationAssetCount = 0.0;
					double AnimationPendingCount = 0.0;
					double MissingStageCount = 0.0;
					double MissingPaidGateCount = 0.0;
					double MissingEditorGateCount = 0.0;
					double QualityGateCount = 0.0;
					double QualityEvidenceCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("animation_asset_count"), AnimationAssetCount);
					(*TargetObject)->TryGetNumberField(TEXT("animation_pending_count"), AnimationPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_stage_count"), MissingStageCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_paid_gate_count"), MissingPaidGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_editor_gate_count"), MissingEditorGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_gate_count"), QualityGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_evidence_count"), QualityEvidenceCount);
					FString AnimationName;
					FString AnimationStatus;
					FString TargetSkeleton;
					FString NextActionLabel;
					FString NextActionState;
					FString NextActionTool;
					const TSharedPtr<FJsonObject>* AnimationObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("target_animation"), AnimationObject) && AnimationObject && AnimationObject->IsValid())
					{
						AnimationName = GetStringField(*AnimationObject, TEXT("name"));
						if (AnimationName.IsEmpty())
						{
							AnimationName = GetStringField(*AnimationObject, TEXT("id"));
						}
						AnimationStatus = GetStringField(*AnimationObject, TEXT("task_status"));
						TargetSkeleton = GetStringField(*AnimationObject, TEXT("target_skeleton"));
					}
					const TSharedPtr<FJsonObject>* NextActionObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("next_safe_action"), NextActionObject) && NextActionObject && NextActionObject->IsValid())
					{
						NextActionLabel = GetStringField(*NextActionObject, TEXT("label"));
						if (NextActionLabel.IsEmpty())
						{
							NextActionLabel = GetStringField(*NextActionObject, TEXT("action_id"));
						}
						NextActionState = GetStringField(*NextActionObject, TEXT("state"));
						NextActionTool = GetStringField(*NextActionObject, TEXT("tool"));
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("animation")) : State;
					const FString ProviderSuffix = Provider.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *Provider);
					const FString AnimationSuffix = AnimationName.IsEmpty()
						? FString()
						: FString::Printf(TEXT(", %s %s"), *AnimationName, *AnimationStatus);
					const FString SkeletonSuffix = TargetSkeleton.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *TargetSkeleton);
					const FString NextActionStateSuffix = NextActionState.IsEmpty() ? FString() : FString::Printf(TEXT(" %s"), *NextActionState);
					const FString NextActionSuffix = NextActionLabel.IsEmpty()
						? FString()
						: (NextActionTool.IsEmpty()
							? FString::Printf(TEXT(", next %s%s"), *NextActionLabel, *NextActionStateSuffix)
							: FString::Printf(TEXT(", next %s%s via %s"), *NextActionLabel, *NextActionStateSuffix, *NextActionTool));
					OutOverview.GeneratedAnimationLifecycleTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s%s%s%s, %d motion(s), %d pending, proof %d/%d, %d stage(s), %d paid, %d editor"),
						*ReviewState,
						*ProviderSuffix,
						*AnimationSuffix,
						*SkeletonSuffix,
						*NextActionSuffix,
						FMath::Max(0, FMath::RoundToInt(AnimationAssetCount)),
						FMath::Max(0, FMath::RoundToInt(AnimationPendingCount)),
						FMath::Max(0, FMath::RoundToInt(QualityEvidenceCount)),
						FMath::Max(0, FMath::RoundToInt(QualityGateCount)),
						FMath::Max(0, FMath::RoundToInt(MissingStageCount)),
						FMath::Max(0, FMath::RoundToInt(MissingPaidGateCount)),
						FMath::Max(0, FMath::RoundToInt(MissingEditorGateCount))
					), 128);
				}
			}
			else if (ActionId == TEXT("compile_generated_animation_evidence") && OutOverview.GeneratedAnimationCompileTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_generated_animation_lifecycle_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString Provider = GetStringField(*TargetObject, TEXT("animation_provider"));
					double MissingStageCount = 0.0;
					double QualityGateCount = 0.0;
					double QualityEvidenceCount = 0.0;
					double MissingPaidGateCount = 0.0;
					double MissingEditorGateCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("missing_stage_count"), MissingStageCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_gate_count"), QualityGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_evidence_count"), QualityEvidenceCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_paid_gate_count"), MissingPaidGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_editor_gate_count"), MissingEditorGateCount);
					FString AnimationName;
					FString MotionId;
					FString TargetSkeleton;
					const TSharedPtr<FJsonObject>* AnimationObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("target_animation"), AnimationObject) && AnimationObject && AnimationObject->IsValid())
					{
						AnimationName = GetStringField(*AnimationObject, TEXT("name"));
						if (AnimationName.IsEmpty())
						{
							AnimationName = GetStringField(*AnimationObject, TEXT("id"));
						}
						MotionId = GetStringField(*AnimationObject, TEXT("motion_id"));
						TargetSkeleton = GetStringField(*AnimationObject, TEXT("target_skeleton"));
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("animation evidence")) : State;
					const FString ProviderSuffix = Provider.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *Provider);
					const FString AnimationSuffix = AnimationName.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *AnimationName);
					const FString MotionSuffix = MotionId.IsEmpty() ? FString(TEXT(", no motion id")) : FString::Printf(TEXT(", %s"), *MotionId);
					const FString SkeletonSuffix = TargetSkeleton.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *TargetSkeleton);
					OutOverview.GeneratedAnimationCompileTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s%s%s%s, proof %d/%d, %d stage(s), %d paid, %d editor"),
						*ReviewState,
						*ProviderSuffix,
						*AnimationSuffix,
						*MotionSuffix,
						*SkeletonSuffix,
						FMath::Max(0, FMath::RoundToInt(QualityEvidenceCount)),
						FMath::Max(0, FMath::RoundToInt(QualityGateCount)),
						FMath::Max(0, FMath::RoundToInt(MissingStageCount)),
						FMath::Max(0, FMath::RoundToInt(MissingPaidGateCount)),
						FMath::Max(0, FMath::RoundToInt(MissingEditorGateCount))
					), 128);
				}
			}
			else if (ActionId == TEXT("review_generated_asset_import_gate") && OutOverview.GeneratedAssetImportTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_generated_asset_import_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double MissingGateCount = 0.0;
					double ImportPendingCount = 0.0;
					double QualityPendingCount = 0.0;
					double QualityGateCount = 0.0;
					double QualityEvidenceCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("missing_gate_count"), MissingGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("import_pending_count"), ImportPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_pending_count"), QualityPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_gate_count"), QualityGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_evidence_count"), QualityEvidenceCount);
					FString AssetName;
					FString AssetState;
					bool bHasPlaceholder = false;
					const TSharedPtr<FJsonObject>* AssetObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("target_asset"), AssetObject) && AssetObject && AssetObject->IsValid())
					{
						AssetName = GetStringField(*AssetObject, TEXT("name"));
						if (AssetName.IsEmpty())
						{
							AssetName = GetStringField(*AssetObject, TEXT("id"));
						}
						AssetState = GetStringField(*AssetObject, TEXT("state"));
						(*AssetObject)->TryGetBoolField(TEXT("has_placeholder"), bHasPlaceholder);
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("import")) : State;
					const FString AssetSuffix = AssetName.IsEmpty()
						? FString()
						: (AssetState.IsEmpty()
							? FString::Printf(TEXT(", %s"), *AssetName)
							: FString::Printf(TEXT(", %s %s"), *AssetName, *AssetState));
					OutOverview.GeneratedAssetImportTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s, %d gate(s), %d import, %d quality, proof %d/%d, placeholder %s"),
						*ReviewState,
						*AssetSuffix,
						FMath::Max(0, FMath::RoundToInt(MissingGateCount)),
						FMath::Max(0, FMath::RoundToInt(ImportPendingCount)),
						FMath::Max(0, FMath::RoundToInt(QualityPendingCount)),
						FMath::Max(0, FMath::RoundToInt(QualityEvidenceCount)),
						FMath::Max(0, FMath::RoundToInt(QualityGateCount)),
						bHasPlaceholder ? TEXT("yes") : TEXT("no")
					), 120);
				}
			}
			else if (ActionId == TEXT("review_generated_asset_quality_proof_gate") && OutOverview.GeneratedAssetQualityProofTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_generated_asset_quality_proof_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					bool bProofReady = false;
					bool bRequiresImportedAsset = false;
					(*TargetObject)->TryGetBoolField(TEXT("quality_proof_ready"), bProofReady);
					(*TargetObject)->TryGetBoolField(TEXT("requires_imported_asset"), bRequiresImportedAsset);
					double QualityCandidateCount = 0.0;
					double MissingGateCount = 0.0;
					double MissingStageCount = 0.0;
					double QualityGateCount = 0.0;
					double QualityEvidenceCount = 0.0;
					double QualityMissingCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("quality_candidate_count"), QualityCandidateCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_gate_count"), MissingGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_stage_count"), MissingStageCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_gate_count"), QualityGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_evidence_count"), QualityEvidenceCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_evidence_missing_count"), QualityMissingCount);
					FString AssetName;
					FString AssetState;
					const TSharedPtr<FJsonObject>* AssetObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("target_asset"), AssetObject) && AssetObject && AssetObject->IsValid())
					{
						AssetName = GetStringField(*AssetObject, TEXT("name"));
						if (AssetName.IsEmpty())
						{
							AssetName = GetStringField(*AssetObject, TEXT("id"));
						}
						AssetState = GetStringField(*AssetObject, TEXT("state"));
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("quality")) : State;
					const FString AssetSuffix = AssetName.IsEmpty()
						? FString()
						: (AssetState.IsEmpty()
							? FString::Printf(TEXT(", %s"), *AssetName)
							: FString::Printf(TEXT(", %s %s"), *AssetName, *AssetState));
					OutOverview.GeneratedAssetQualityProofTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s, %d candidate(s), proof %d/%d, %d missing, %d gate(s), %d stage(s), import %s, ready %s"),
						*ReviewState,
						*AssetSuffix,
						FMath::Max(0, FMath::RoundToInt(QualityCandidateCount)),
						FMath::Max(0, FMath::RoundToInt(QualityEvidenceCount)),
						FMath::Max(0, FMath::RoundToInt(QualityGateCount)),
						FMath::Max(0, FMath::RoundToInt(QualityMissingCount)),
						FMath::Max(0, FMath::RoundToInt(MissingGateCount)),
						FMath::Max(0, FMath::RoundToInt(MissingStageCount)),
						bRequiresImportedAsset ? TEXT("needed") : TEXT("present"),
						bProofReady ? TEXT("yes") : TEXT("no")
					), 128);
				}
			}
			else if (ActionId == TEXT("review_generated_asset_replacement_gate") && OutOverview.GeneratedAssetReplacementTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_generated_asset_replacement_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					bool bReplacementReady = false;
					(*TargetObject)->TryGetBoolField(TEXT("replacement_ready"), bReplacementReady);
					double PlaceholderCount = 0.0;
					double ReplacementPendingCount = 0.0;
					double MissingGateCount = 0.0;
					double MissingStageCount = 0.0;
					double QualityGateCount = 0.0;
					double QualityEvidenceCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("placeholder_count"), PlaceholderCount);
					(*TargetObject)->TryGetNumberField(TEXT("replacement_pending_count"), ReplacementPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_gate_count"), MissingGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_stage_count"), MissingStageCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_gate_count"), QualityGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("quality_evidence_count"), QualityEvidenceCount);
					FString AssetName;
					FString PlaceholderPath;
					const TSharedPtr<FJsonObject>* AssetObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("target_asset"), AssetObject) && AssetObject && AssetObject->IsValid())
					{
						AssetName = GetStringField(*AssetObject, TEXT("name"));
						if (AssetName.IsEmpty())
						{
							AssetName = GetStringField(*AssetObject, TEXT("id"));
						}
						PlaceholderPath = GetStringField(*AssetObject, TEXT("placeholder_asset_path"));
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("replacement")) : State;
					const FString AssetSuffix = AssetName.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *AssetName);
					const FString PlaceholderSuffix = PlaceholderPath.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *PlaceholderPath);
					OutOverview.GeneratedAssetReplacementTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s%s, %d placeholder(s), %d pending, %d gate(s), %d stage(s), proof %d/%d, ready %s"),
						*ReviewState,
						*AssetSuffix,
						*PlaceholderSuffix,
						FMath::Max(0, FMath::RoundToInt(PlaceholderCount)),
						FMath::Max(0, FMath::RoundToInt(ReplacementPendingCount)),
						FMath::Max(0, FMath::RoundToInt(MissingGateCount)),
						FMath::Max(0, FMath::RoundToInt(MissingStageCount)),
						FMath::Max(0, FMath::RoundToInt(QualityEvidenceCount)),
						FMath::Max(0, FMath::RoundToInt(QualityGateCount)),
						bReplacementReady ? TEXT("yes") : TEXT("no")
					), 128);
				}
			}
			else if (ActionId == TEXT("review_provider_spend_gate") && OutOverview.ProviderSpendTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_provider_spend_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString Provider = GetStringField(*TargetObject, TEXT("provider"));
					bool bAllowed = false;
					bool bFallbackAvailable = false;
					(*TargetObject)->TryGetBoolField(TEXT("paid_generation_allowed"), bAllowed);
					(*TargetObject)->TryGetBoolField(TEXT("fallback_placeholder_available"), bFallbackAvailable);
					bool bMeshWalletEvidenceRecorded = false;
					bool bAnimationAllowanceEvidenceRecorded = false;
					bool bUsageApprovalRecorded = false;
					const TSharedPtr<FJsonObject>* PaidEvidenceObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("paid_generation_evidence_contract"), PaidEvidenceObject) && PaidEvidenceObject && PaidEvidenceObject->IsValid())
					{
						(*PaidEvidenceObject)->TryGetBoolField(TEXT("mesh_wallet_evidence_recorded"), bMeshWalletEvidenceRecorded);
						(*PaidEvidenceObject)->TryGetBoolField(TEXT("animation_allowance_evidence_recorded"), bAnimationAllowanceEvidenceRecorded);
						(*PaidEvidenceObject)->TryGetBoolField(TEXT("explicit_usage_approval_recorded"), bUsageApprovalRecorded);
					}
					double ProviderPendingCount = 0.0;
					double MissingGateCount = 0.0;
					double EvidenceRequiredCount = 0.0;
					double PlaceholderCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("provider_pending_count"), ProviderPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_gate_count"), MissingGateCount);
					(*TargetObject)->TryGetNumberField(TEXT("evidence_required_count"), EvidenceRequiredCount);
					(*TargetObject)->TryGetNumberField(TEXT("placeholder_count"), PlaceholderCount);
					FString AssetName;
					const TSharedPtr<FJsonObject>* AssetObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("target_asset"), AssetObject) && AssetObject && AssetObject->IsValid())
					{
						AssetName = GetStringField(*AssetObject, TEXT("name"));
						if (AssetName.IsEmpty())
						{
							AssetName = GetStringField(*AssetObject, TEXT("id"));
						}
					}
					const FString ReviewState = bAllowed ? FString(TEXT("ready")) : (State.IsEmpty() ? FString(TEXT("blocked")) : State);
					const FString ProviderSuffix = Provider.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *Provider);
					const FString AssetSuffix = AssetName.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *AssetName);
					const FString FallbackSuffix = bFallbackAvailable ? FString(TEXT(", fallback placeholders")) : FString(TEXT(", no fallback"));
					const FString EvidenceSuffix = FString::Printf(
						TEXT(", mesh %s, anim %s, usage %s"),
						bMeshWalletEvidenceRecorded ? TEXT("ok") : TEXT("need"),
						bAnimationAllowanceEvidenceRecorded ? TEXT("ok") : TEXT("need"),
						bUsageApprovalRecorded ? TEXT("ok") : TEXT("need")
					);
					OutOverview.ProviderSpendTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s%s, %d provider, %d gate(s), %d evidence, %d placeholder(s)%s%s"),
						*ReviewState,
						*ProviderSuffix,
						*AssetSuffix,
						FMath::Max(0, FMath::RoundToInt(ProviderPendingCount)),
						FMath::Max(0, FMath::RoundToInt(MissingGateCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceRequiredCount)),
						FMath::Max(0, FMath::RoundToInt(PlaceholderCount)),
						*FallbackSuffix,
						*EvidenceSuffix
					), 120);
				}
			}
			else if (ActionId == TEXT("review_generated_asset_provider_task_gate") && OutOverview.GeneratedAssetProviderTaskTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_generated_asset_provider_task_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					bool bProviderTaskReady = false;
					(*TargetObject)->TryGetBoolField(TEXT("provider_task_ready"), bProviderTaskReady);
					double ProviderPendingCount = 0.0;
					double ProviderSuccessCount = 0.0;
					double TaskIdMissingCount = 0.0;
					double DownloadPendingCount = 0.0;
					double ImportPendingCount = 0.0;
					double MissingStageCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("provider_pending_count"), ProviderPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("provider_success_count"), ProviderSuccessCount);
					(*TargetObject)->TryGetNumberField(TEXT("task_id_missing_count"), TaskIdMissingCount);
					(*TargetObject)->TryGetNumberField(TEXT("download_pending_count"), DownloadPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("import_pending_count"), ImportPendingCount);
					(*TargetObject)->TryGetNumberField(TEXT("missing_stage_count"), MissingStageCount);
					FString AssetName;
					FString TaskStatus;
					FString TaskId;
					const TSharedPtr<FJsonObject>* AssetObject = nullptr;
					if ((*TargetObject)->TryGetObjectField(TEXT("target_asset"), AssetObject) && AssetObject && AssetObject->IsValid())
					{
						AssetName = GetStringField(*AssetObject, TEXT("name"));
						if (AssetName.IsEmpty())
						{
							AssetName = GetStringField(*AssetObject, TEXT("id"));
						}
						TaskStatus = GetStringField(*AssetObject, TEXT("task_status"));
						TaskId = GetStringField(*AssetObject, TEXT("task_id"));
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("task")) : State;
					const FString AssetSuffix = AssetName.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *AssetName);
					const FString StatusSuffix = TaskStatus.IsEmpty() ? FString() : FString::Printf(TEXT(" %s"), *TaskStatus);
					const FString TaskSuffix = TaskId.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *TaskId);
					OutOverview.GeneratedAssetProviderTaskTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s%s%s, %d pending, %d success, %d task id, %d download, %d import, %d stage(s), ready %s"),
						*ReviewState,
						*AssetSuffix,
						*StatusSuffix,
						*TaskSuffix,
						FMath::Max(0, FMath::RoundToInt(ProviderPendingCount)),
						FMath::Max(0, FMath::RoundToInt(ProviderSuccessCount)),
						FMath::Max(0, FMath::RoundToInt(TaskIdMissingCount)),
						FMath::Max(0, FMath::RoundToInt(DownloadPendingCount)),
						FMath::Max(0, FMath::RoundToInt(ImportPendingCount)),
						FMath::Max(0, FMath::RoundToInt(MissingStageCount)),
						bProviderTaskReady ? TEXT("yes") : TEXT("no")
					), 128);
				}
			}
			else if (ActionId == TEXT("show_evidence_ledger") && OutOverview.EvidenceLedgerTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_evidence_ledger_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					double EventCount = 0.0;
					double ArtifactCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("event_count"), EventCount);
					(*TargetObject)->TryGetNumberField(TEXT("artifact_count"), ArtifactCount);
					const FString LatestPhase = GetStringField(*TargetObject, TEXT("latest_phase"));
					const FString LatestType = GetStringField(*TargetObject, TEXT("latest_evidence_type"));
					const FString LatestName = LatestType.IsEmpty() ? LatestPhase : FString::Printf(TEXT("%s/%s"), *LatestPhase, *LatestType);
					const FString LatestSuffix = LatestName.IsEmpty() ? FString() : FString::Printf(TEXT(", latest %s"), *LatestName);
					OutOverview.EvidenceLedgerTargetSummary = TruncateForCard(FString::Printf(
						TEXT("target %d event(s), %d artifact(s)%s"),
						FMath::Max(0, FMath::RoundToInt(EventCount)),
						FMath::Max(0, FMath::RoundToInt(ArtifactCount)),
						*LatestSuffix
					), 96);
				}
			}
			else if (ActionId == TEXT("review_editor_queue") && OutOverview.QueueReviewTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_queue_review_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString NextTool = GetStringField(*TargetObject, TEXT("next_action_tool"));
					const FString NextActionId = GetStringField(*TargetObject, TEXT("next_action_id"));
					double QueueCount = 0.0;
					double QueuedActionCount = 0.0;
					double ExecutableQueueCount = 0.0;
					double BlockedQueueCount = 0.0;
					double BridgeBlockedCount = 0.0;
					double EvidenceCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("queue_count"), QueueCount);
					(*TargetObject)->TryGetNumberField(TEXT("queued_action_count"), QueuedActionCount);
					(*TargetObject)->TryGetNumberField(TEXT("executable_queue_count"), ExecutableQueueCount);
					(*TargetObject)->TryGetNumberField(TEXT("blocked_queue_count"), BlockedQueueCount);
					(*TargetObject)->TryGetNumberField(TEXT("bridge_blocked_count"), BridgeBlockedCount);
					(*TargetObject)->TryGetNumberField(TEXT("evidence_count"), EvidenceCount);
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("queue")) : State;
					const FString NextAction = NextTool.IsEmpty() ? NextActionId : NextTool;
					const FString NextSuffix = NextAction.IsEmpty() ? FString() : FString::Printf(TEXT(", next %s"), *NextAction);
					OutOverview.QueueReviewTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d queue(s), %d action(s), %d executable, %d blocked, %d bridge, %d evidence%s"),
						*ReviewState,
						FMath::Max(0, FMath::RoundToInt(QueueCount)),
						FMath::Max(0, FMath::RoundToInt(QueuedActionCount)),
						FMath::Max(0, FMath::RoundToInt(ExecutableQueueCount)),
						FMath::Max(0, FMath::RoundToInt(BlockedQueueCount)),
						FMath::Max(0, FMath::RoundToInt(BridgeBlockedCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceCount)),
						*NextSuffix
					), 120);
				}
			}
			else if (ActionId == TEXT("queue_editor_actions") && OutOverview.QueueTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_queue_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString TargetPhase = GetStringField(*TargetObject, TEXT("target_phase"));
					const FString DisplayName = GetStringField(*TargetObject, TEXT("display_name"));
					const FString TemplateName = GetStringField(*TargetObject, TEXT("template_name"));
					double OperationCount = 0.0;
					double EditorOperationCount = 0.0;
					double CompileCheckCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("operation_count"), OperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("editor_operation_count"), EditorOperationCount);
					(*TargetObject)->TryGetNumberField(TEXT("compile_check_count"), CompileCheckCount);
					const FString TargetName = !DisplayName.IsEmpty() ? DisplayName : (!TemplateName.IsEmpty() ? TemplateName : TargetPhase);
					if (!TargetName.IsEmpty())
					{
						OutOverview.QueueTargetSummary = TruncateForCard(FString::Printf(
							TEXT("target %s, %d op(s), %d checklist, %d compile check(s)"),
							*TargetName,
							FMath::Max(0, FMath::RoundToInt(OperationCount)),
							FMath::Max(0, FMath::RoundToInt(EditorOperationCount)),
							FMath::Max(0, FMath::RoundToInt(CompileCheckCount))
						), 96);
					}
				}
			}
			else if (ActionId == TEXT("repair_failed_step") && OutOverview.RepairTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				const TSharedPtr<FJsonObject>* ReviewObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_repair_review_context"), ReviewObject) && ReviewObject && ReviewObject->IsValid())
				{
					const FString State = GetStringField(*ReviewObject, TEXT("state"));
					double FailureSignalCount = 0.0;
					double EvidenceCount = 0.0;
					(*ReviewObject)->TryGetNumberField(TEXT("failure_signal_count"), FailureSignalCount);
					const TArray<TSharedPtr<FJsonValue>>* EvidencePreviewValues = nullptr;
					if ((*ReviewObject)->TryGetArrayField(TEXT("evidence_preview"), EvidencePreviewValues) && EvidencePreviewValues != nullptr)
					{
						EvidenceCount = static_cast<double>(EvidencePreviewValues->Num());
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("review")) : State;
					OutOverview.RepairReviewTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d signal(s), %d evidence item(s)"),
						*ReviewState,
						FMath::Max(0, FMath::RoundToInt(FailureSignalCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceCount))
					), 96);
				}
				if (WorkflowObject->TryGetObjectField(TEXT("target_repair_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString LabelText = GetStringField(*TargetObject, TEXT("label"));
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					const FString Tool = GetStringField(*TargetObject, TEXT("recommended_tool"));
					if (!LabelText.IsEmpty())
					{
						const FString StateSuffix = State.IsEmpty() ? FString() : FString::Printf(TEXT(" %s"), *State);
						const FString ToolSuffix = Tool.IsEmpty() ? FString() : FString::Printf(TEXT(", use %s"), *Tool);
						OutOverview.RepairTargetSummary = TruncateForCard(FString::Printf(
							TEXT("target %s%s%s"),
							*LabelText,
							*StateSuffix,
							*ToolSuffix
						), 96);
					}
				}
			}
			else if (ActionId == TEXT("review_runtime_verification") && OutOverview.RuntimeReviewTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* ReviewObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_runtime_review_context"), ReviewObject) && ReviewObject && ReviewObject->IsValid())
				{
					const FString State = GetStringField(*ReviewObject, TEXT("state"));
					double PieValidationCount = 0.0;
					double EvidenceRequirementCount = 0.0;
					double RuntimeEvidenceEventCount = 0.0;
					(*ReviewObject)->TryGetNumberField(TEXT("pie_validation_count"), PieValidationCount);
					(*ReviewObject)->TryGetNumberField(TEXT("evidence_requirement_count"), EvidenceRequirementCount);
					(*ReviewObject)->TryGetNumberField(TEXT("runtime_evidence_event_count"), RuntimeEvidenceEventCount);
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("review")) : State;
					OutOverview.RuntimeReviewTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d PIE step(s), %d proof item(s), %d recorded"),
						*ReviewState,
						FMath::Max(0, FMath::RoundToInt(PieValidationCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceRequirementCount)),
						FMath::Max(0, FMath::RoundToInt(RuntimeEvidenceEventCount))
					), 96);
				}
			}
			else if (ActionId == TEXT("review_evidence_requirements") && OutOverview.EvidenceReviewTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* ReviewObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_evidence_review_context"), ReviewObject) && ReviewObject && ReviewObject->IsValid())
				{
					const FString State = GetStringField(*ReviewObject, TEXT("state"));
					const FString TargetEvidenceType = GetStringField(*ReviewObject, TEXT("target_evidence_type"));
					double ItemCount = 0.0;
					double PendingCount = 0.0;
					double BlockedCount = 0.0;
					double RecordedCount = 0.0;
					double TargetArtifactCount = 0.0;
					(*ReviewObject)->TryGetNumberField(TEXT("item_count"), ItemCount);
					(*ReviewObject)->TryGetNumberField(TEXT("pending_count"), PendingCount);
					(*ReviewObject)->TryGetNumberField(TEXT("blocked_count"), BlockedCount);
					(*ReviewObject)->TryGetNumberField(TEXT("recorded_count"), RecordedCount);
					(*ReviewObject)->TryGetNumberField(TEXT("target_artifact_count"), TargetArtifactCount);
					FString TargetLabel;
					const TSharedPtr<FJsonObject>* TargetEvidenceObject = nullptr;
					if ((*ReviewObject)->TryGetObjectField(TEXT("target_evidence"), TargetEvidenceObject) && TargetEvidenceObject && TargetEvidenceObject->IsValid())
					{
						TargetLabel = GetStringField(*TargetEvidenceObject, TEXT("label"));
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("evidence")) : State;
					const FString TargetName = TargetEvidenceType.IsEmpty() ? TargetLabel : TargetEvidenceType;
					const FString TargetSuffix = TargetName.IsEmpty() ? FString() : FString::Printf(TEXT(", target %s"), *TargetName);
					OutOverview.EvidenceReviewTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d item(s), %d pending, %d blocked, %d recorded, %d artifact(s)%s"),
						*ReviewState,
						FMath::Max(0, FMath::RoundToInt(ItemCount)),
						FMath::Max(0, FMath::RoundToInt(PendingCount)),
						FMath::Max(0, FMath::RoundToInt(BlockedCount)),
						FMath::Max(0, FMath::RoundToInt(RecordedCount)),
						FMath::Max(0, FMath::RoundToInt(TargetArtifactCount)),
						*TargetSuffix
					), 120);
				}
			}
			else if (ActionId == TEXT("record_runtime_evidence") && OutOverview.RuntimeEvidenceTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_evidence_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double ArtifactCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("artifact_count"), ArtifactCount);
					const TSharedPtr<FJsonObject>* RuntimeObject = nullptr;
					double PieValidationCount = 0.0;
					double EvidenceRequirementCount = 0.0;
					if ((*TargetObject)->TryGetObjectField(TEXT("runtime_verification"), RuntimeObject) && RuntimeObject && RuntimeObject->IsValid())
					{
						(*RuntimeObject)->TryGetNumberField(TEXT("pie_validation_count"), PieValidationCount);
						(*RuntimeObject)->TryGetNumberField(TEXT("evidence_requirement_count"), EvidenceRequirementCount);
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("runtime")) : State;
					OutOverview.RuntimeEvidenceTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d artifact(s), %d PIE step(s), %d proof item(s)"),
						*ReviewState,
						FMath::Max(0, FMath::RoundToInt(ArtifactCount)),
						FMath::Max(0, FMath::RoundToInt(PieValidationCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceRequirementCount))
					), 96);
				}
			}
			else if (ActionId == TEXT("record_queued_action_evidence") && OutOverview.QueuedEvidenceTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_evidence_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double ArtifactCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("artifact_count"), ArtifactCount);
					const TSharedPtr<FJsonObject>* QueueObject = nullptr;
					FString Tool;
					FString ActionIdText;
					double ArgumentCount = 0.0;
					if ((*TargetObject)->TryGetObjectField(TEXT("queued_action"), QueueObject) && QueueObject && QueueObject->IsValid())
					{
						Tool = GetStringField(*QueueObject, TEXT("next_action_tool"));
						ActionIdText = GetStringField(*QueueObject, TEXT("next_action_id"));
						const TArray<TSharedPtr<FJsonValue>>* ArgumentKeyValues = nullptr;
						if ((*QueueObject)->TryGetArrayField(TEXT("argument_keys"), ArgumentKeyValues) && ArgumentKeyValues != nullptr)
						{
							ArgumentCount = static_cast<double>(ArgumentKeyValues->Num());
						}
					}
					const FString DisplayAction = Tool.IsEmpty() ? ActionIdText : Tool;
					const FString ActionSuffix = DisplayAction.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *DisplayAction);
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("queue")) : State;
					OutOverview.QueuedEvidenceTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s, %d artifact(s), %d arg(s)"),
						*ReviewState,
						*ActionSuffix,
						FMath::Max(0, FMath::RoundToInt(ArtifactCount)),
						FMath::Max(0, FMath::RoundToInt(ArgumentCount))
					), 96);
				}
			}
			else if (ActionId == TEXT("record_generated_asset_evidence") && OutOverview.GeneratedAssetEvidenceTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_evidence_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double ArtifactCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("artifact_count"), ArtifactCount);
					const TSharedPtr<FJsonObject>* AssetObject = nullptr;
					FString AssetName;
					FString AssetId;
					FString Provider;
					FString AssetState;
					double QualityGateCount = 0.0;
					if ((*TargetObject)->TryGetObjectField(TEXT("generated_asset"), AssetObject) && AssetObject && AssetObject->IsValid())
					{
						AssetName = GetStringField(*AssetObject, TEXT("asset_name"));
						AssetId = GetStringField(*AssetObject, TEXT("asset_id"));
						Provider = GetStringField(*AssetObject, TEXT("provider"));
						AssetState = GetStringField(*AssetObject, TEXT("state"));
						(*AssetObject)->TryGetNumberField(TEXT("quality_gate_count"), QualityGateCount);
					}
					const FString TargetName = AssetName.IsEmpty() ? AssetId : AssetName;
					if (!TargetName.IsEmpty())
					{
						const FString ReviewState = AssetState.IsEmpty() ? State : AssetState;
						const FString StateSuffix = ReviewState.IsEmpty() ? FString() : FString::Printf(TEXT(" %s"), *ReviewState);
						const FString ProviderSuffix = Provider.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *Provider);
						OutOverview.GeneratedAssetEvidenceTargetSummary = TruncateForCard(FString::Printf(
							TEXT("%s%s%s, %d gate(s), %d artifact(s)"),
							*TargetName,
							*StateSuffix,
							*ProviderSuffix,
							FMath::Max(0, FMath::RoundToInt(QualityGateCount)),
							FMath::Max(0, FMath::RoundToInt(ArtifactCount))
						), 96);
					}
				}
			}
			else if (ActionId == TEXT("record_paid_generation_evidence") && OutOverview.PaidGenerationEvidenceTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_evidence_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double ArtifactCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("artifact_count"), ArtifactCount);
					const TSharedPtr<FJsonObject>* PaidEvidenceObject = nullptr;
					FString MeshProvider = TEXT("tripo");
					FString AnimationProvider = TEXT("uthana");
					FString WalletTool;
					FString ApprovalField;
					bool bMeshWalletEvidenceRecorded = false;
					bool bAnimationAllowanceEvidenceRecorded = false;
					bool bUsageApprovalRecorded = false;
					double MissingGateCount = 0.0;
					if ((*TargetObject)->TryGetObjectField(TEXT("paid_generation_evidence"), PaidEvidenceObject) && PaidEvidenceObject && PaidEvidenceObject->IsValid())
					{
						MeshProvider = GetStringField(*PaidEvidenceObject, TEXT("mesh_provider"));
						AnimationProvider = GetStringField(*PaidEvidenceObject, TEXT("animation_provider"));
						WalletTool = GetStringField(*PaidEvidenceObject, TEXT("mesh_wallet_tool"));
						ApprovalField = GetStringField(*PaidEvidenceObject, TEXT("spend_approval_field"));
						(*PaidEvidenceObject)->TryGetBoolField(TEXT("mesh_wallet_evidence_recorded"), bMeshWalletEvidenceRecorded);
						(*PaidEvidenceObject)->TryGetBoolField(TEXT("animation_allowance_evidence_recorded"), bAnimationAllowanceEvidenceRecorded);
						(*PaidEvidenceObject)->TryGetBoolField(TEXT("explicit_usage_approval_recorded"), bUsageApprovalRecorded);
						(*PaidEvidenceObject)->TryGetNumberField(TEXT("missing_gate_count"), MissingGateCount);
					}
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("pending")) : State;
					const FString ProviderSuffix = FString::Printf(TEXT(", %s/%s"), *MeshProvider, *AnimationProvider);
					const FString WalletSuffix = WalletTool.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *WalletTool);
					const FString ApprovalSuffix = ApprovalField.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *TruncateForCard(ApprovalField, 42));
					const FString EvidenceSuffix = FString::Printf(
						TEXT(", mesh %s, anim %s, usage %s"),
						bMeshWalletEvidenceRecorded ? TEXT("ok") : TEXT("need"),
						bAnimationAllowanceEvidenceRecorded ? TEXT("ok") : TEXT("need"),
						bUsageApprovalRecorded ? TEXT("ok") : TEXT("need")
					);
					OutOverview.PaidGenerationEvidenceTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s, %d gate(s), %d artifact(s)%s%s%s"),
						*ReviewState,
						*ProviderSuffix,
						FMath::Max(0, FMath::RoundToInt(MissingGateCount)),
						FMath::Max(0, FMath::RoundToInt(ArtifactCount)),
						*WalletSuffix,
						*ApprovalSuffix,
						*EvidenceSuffix
					), 120);
				}
			}
			else if (ActionId == TEXT("record_generated_animation_evidence") && OutOverview.GeneratedAnimationEvidenceTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_evidence_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double ArtifactCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("artifact_count"), ArtifactCount);
					const TSharedPtr<FJsonObject>* AnimationObject = nullptr;
					FString AnimationName;
					FString AnimationId;
					FString Provider;
					FString TaskStatus;
					FString TargetSkeleton;
					double QualityGateCount = 0.0;
					double QualityEvidenceCount = 0.0;
					double QualityMissingCount = 0.0;
					if ((*TargetObject)->TryGetObjectField(TEXT("generated_animation"), AnimationObject) && AnimationObject && AnimationObject->IsValid())
					{
						AnimationName = GetStringField(*AnimationObject, TEXT("animation_name"));
						AnimationId = GetStringField(*AnimationObject, TEXT("animation_id"));
						Provider = GetStringField(*AnimationObject, TEXT("provider"));
						TaskStatus = GetStringField(*AnimationObject, TEXT("task_status"));
						TargetSkeleton = GetStringField(*AnimationObject, TEXT("target_skeleton"));
						(*AnimationObject)->TryGetNumberField(TEXT("quality_gate_count"), QualityGateCount);
						(*AnimationObject)->TryGetNumberField(TEXT("quality_evidence_count"), QualityEvidenceCount);
						(*AnimationObject)->TryGetNumberField(TEXT("quality_evidence_missing_count"), QualityMissingCount);
					}
					const FString TargetName = AnimationName.IsEmpty() ? AnimationId : AnimationName;
					if (!TargetName.IsEmpty())
					{
						const FString ReviewState = TaskStatus.IsEmpty() ? State : TaskStatus;
						const FString StateSuffix = ReviewState.IsEmpty() ? FString() : FString::Printf(TEXT(" %s"), *ReviewState);
						const FString ProviderSuffix = Provider.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *Provider);
						const FString SkeletonSuffix = TargetSkeleton.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *TargetSkeleton);
						OutOverview.GeneratedAnimationEvidenceTargetSummary = TruncateForCard(FString::Printf(
							TEXT("%s%s%s%s, proof %d/%d, %d missing, %d artifact(s)"),
							*TargetName,
							*StateSuffix,
							*ProviderSuffix,
							*SkeletonSuffix,
							FMath::Max(0, FMath::RoundToInt(QualityEvidenceCount)),
							FMath::Max(0, FMath::RoundToInt(QualityGateCount)),
							FMath::Max(0, FMath::RoundToInt(QualityMissingCount)),
							FMath::Max(0, FMath::RoundToInt(ArtifactCount))
						), 112);
					}
				}
			}
			else if (ActionId == TEXT("record_feature_completion_contract") && OutOverview.FeatureCompletionContractTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_evidence_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString State = GetStringField(*TargetObject, TEXT("state"));
					double ArtifactCount = 0.0;
					(*TargetObject)->TryGetNumberField(TEXT("artifact_count"), ArtifactCount);
					const TSharedPtr<FJsonObject>* ContractObject = nullptr;
					FString TemplateName;
					FString DisplayName;
					double ProofGateCount = 0.0;
					double RequiredEvidenceCount = 0.0;
					double StopConditionCount = 0.0;
					if ((*TargetObject)->TryGetObjectField(TEXT("feature_completion_contract"), ContractObject) && ContractObject && ContractObject->IsValid())
					{
						TemplateName = GetStringField(*ContractObject, TEXT("template_name"));
						DisplayName = GetStringField(*ContractObject, TEXT("display_name"));
						(*ContractObject)->TryGetNumberField(TEXT("proof_gate_count"), ProofGateCount);
						(*ContractObject)->TryGetNumberField(TEXT("required_evidence_count"), RequiredEvidenceCount);
						(*ContractObject)->TryGetNumberField(TEXT("stop_condition_count"), StopConditionCount);
					}
					const FString TargetName = DisplayName.IsEmpty() ? TemplateName : DisplayName;
					const FString ReviewState = State.IsEmpty() ? FString(TEXT("pending")) : State;
					const FString TargetSuffix = TargetName.IsEmpty() ? FString() : FString::Printf(TEXT(", %s"), *TargetName);
					OutOverview.FeatureCompletionContractTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s%s, %d proof gate(s), %d evidence, %d stop(s), %d artifact(s)"),
						*ReviewState,
						*TargetSuffix,
						FMath::Max(0, FMath::RoundToInt(ProofGateCount)),
						FMath::Max(0, FMath::RoundToInt(RequiredEvidenceCount)),
						FMath::Max(0, FMath::RoundToInt(StopConditionCount)),
						FMath::Max(0, FMath::RoundToInt(ArtifactCount))
					), 112);
				}
			}
			else if (ActionId == TEXT("execute_next_safe_step") && OutOverview.ExecuteTargetSummary.IsEmpty())
			{
				const TSharedPtr<FJsonObject>* TargetObject = nullptr;
				const TSharedPtr<FJsonObject>* ReviewObject = nullptr;
				if (WorkflowObject->TryGetObjectField(TEXT("target_execution_review_context"), ReviewObject) && ReviewObject && ReviewObject->IsValid())
				{
					const FString State = GetStringField(*ReviewObject, TEXT("state"));
					double MissingGateCount = 0.0;
					double EvidenceCount = 0.0;
					(*ReviewObject)->TryGetNumberField(TEXT("missing_gate_count"), MissingGateCount);
					(*ReviewObject)->TryGetNumberField(TEXT("after_execution_evidence_count"), EvidenceCount);
					bool bCanExecuteNow = false;
					(*ReviewObject)->TryGetBoolField(TEXT("can_execute_now"), bCanExecuteNow);
					const FString ReviewState = bCanExecuteNow ? FString(TEXT("ready")) : (State.IsEmpty() ? FString(TEXT("blocked")) : State);
					OutOverview.ExecutionReviewTargetSummary = TruncateForCard(FString::Printf(
						TEXT("%s, %d gate(s), %d evidence item(s)"),
						*ReviewState,
						FMath::Max(0, FMath::RoundToInt(MissingGateCount)),
						FMath::Max(0, FMath::RoundToInt(EvidenceCount))
					), 96);
				}
				if (WorkflowObject->TryGetObjectField(TEXT("target_execute_context"), TargetObject) && TargetObject && TargetObject->IsValid())
				{
					const FString Tool = GetStringField(*TargetObject, TEXT("tool"));
					const FString LabelText = GetStringField(*TargetObject, TEXT("label"));
					const FString ActionIdText = GetStringField(*TargetObject, TEXT("action_id"));
					const FString TargetName = !LabelText.IsEmpty() ? LabelText : (!Tool.IsEmpty() ? Tool : ActionIdText);
					double ArgumentCount = 0.0;
					const TArray<TSharedPtr<FJsonValue>>* ArgumentKeyValues = nullptr;
					if (TargetObject->Get()->TryGetArrayField(TEXT("argument_keys"), ArgumentKeyValues) && ArgumentKeyValues != nullptr)
					{
						ArgumentCount = static_cast<double>(ArgumentKeyValues->Num());
					}
					if (!TargetName.IsEmpty())
					{
						const FString ToolSuffix = Tool.IsEmpty() || Tool == TargetName ? FString() : FString::Printf(TEXT(", %s"), *Tool);
						OutOverview.ExecuteTargetSummary = TruncateForCard(FString::Printf(
							TEXT("target %s%s, %d arg(s)"),
							*TargetName,
							*ToolSuffix,
							FMath::Max(0, FMath::RoundToInt(ArgumentCount))
						), 96);
					}
				}
			}

			int32 Priority = 90;
			if (ActionId == TEXT("review_evidence_requirements") && !OutOverview.EvidenceReviewTargetSummary.IsEmpty())
			{
				Priority = 9;
			}
			else if (ActionId == TEXT("record_evidence") && !OutOverview.EvidenceTargetSummary.IsEmpty())
			{
				Priority = 10;
			}
			else if (ActionId == TEXT("record_queued_action_evidence") && !OutOverview.QueuedEvidenceTargetSummary.IsEmpty())
			{
				Priority = 11;
			}
			else if (ActionId == TEXT("record_generated_asset_evidence") && !OutOverview.GeneratedAssetEvidenceTargetSummary.IsEmpty())
			{
				Priority = 12;
			}
			else if (ActionId == TEXT("record_paid_generation_evidence") && !OutOverview.PaidGenerationEvidenceTargetSummary.IsEmpty())
			{
				Priority = 13;
			}
			else if (ActionId == TEXT("record_generated_animation_evidence") && !OutOverview.GeneratedAnimationEvidenceTargetSummary.IsEmpty())
			{
				Priority = 14;
			}
			else if (ActionId == TEXT("record_feature_completion_contract") && !OutOverview.FeatureCompletionContractTargetSummary.IsEmpty())
			{
				Priority = 15;
			}
			else if (ActionId == TEXT("record_runtime_evidence") && !OutOverview.RuntimeEvidenceTargetSummary.IsEmpty())
			{
				Priority = 16;
			}
			else if (ActionId == TEXT("execute_next_safe_step"))
			{
				Priority = 20;
			}
			else if (ActionId == TEXT("repair_failed_step"))
			{
				Priority = 30;
			}
			else if (ActionId == TEXT("review_runtime_verification"))
			{
				Priority = 32;
			}
			else if (ActionId == TEXT("resolve_blockers"))
			{
				Priority = 35;
			}
			else if (ActionId == TEXT("review_generated_asset_gate") && !OutOverview.GeneratedAssetReviewTargetSummary.IsEmpty())
			{
				Priority = 36;
			}
			else if (ActionId == TEXT("review_generated_asset_lifecycle_gate") && !OutOverview.GeneratedAssetLifecycleTargetSummary.IsEmpty())
			{
				Priority = 37;
			}
			else if (ActionId == TEXT("compile_asset_lifecycle_manifest") && !OutOverview.AssetLifecycleCompileTargetSummary.IsEmpty())
			{
				Priority = 38;
			}
			else if (ActionId == TEXT("review_generated_animation_lifecycle_gate") && !OutOverview.GeneratedAnimationLifecycleTargetSummary.IsEmpty())
			{
				Priority = 39;
			}
			else if (ActionId == TEXT("compile_generated_animation_evidence") && !OutOverview.GeneratedAnimationCompileTargetSummary.IsEmpty())
			{
				Priority = 40;
			}
			else if (ActionId == TEXT("review_generated_asset_import_gate") && !OutOverview.GeneratedAssetImportTargetSummary.IsEmpty())
			{
				Priority = 41;
			}
			else if (ActionId == TEXT("review_generated_asset_quality_proof_gate") && !OutOverview.GeneratedAssetQualityProofTargetSummary.IsEmpty())
			{
				Priority = 42;
			}
			else if (ActionId == TEXT("review_generated_asset_replacement_gate") && !OutOverview.GeneratedAssetReplacementTargetSummary.IsEmpty())
			{
				Priority = 43;
			}
			else if (ActionId == TEXT("continue_with_placeholder_fallback") && !OutOverview.PlaceholderTargetSummary.IsEmpty())
			{
				Priority = 44;
			}
			else if (ActionId == TEXT("review_provider_spend_gate") && !OutOverview.ProviderSpendTargetSummary.IsEmpty())
			{
				Priority = 45;
			}
			else if (ActionId == TEXT("review_generated_asset_provider_task_gate") && !OutOverview.GeneratedAssetProviderTaskTargetSummary.IsEmpty())
			{
				Priority = 46;
			}
			else if (ActionId == TEXT("resolve_generated_asset"))
			{
				Priority = 47;
			}
			else if (ActionId == TEXT("compile_placeholder_manifest") && !OutOverview.PlaceholderTargetSummary.IsEmpty())
			{
				Priority = 47;
			}
			else if (ActionId == TEXT("review_editor_queue") && !OutOverview.QueueReviewTargetSummary.IsEmpty())
			{
				Priority = 46;
			}
			else if (ActionId == TEXT("queue_editor_actions"))
			{
				Priority = 47;
			}
			else if (ActionId == TEXT("generate_work_order"))
			{
				Priority = 48;
			}
			else if (ActionId == TEXT("review_gameplay_template_plan") && !OutOverview.GameplayTemplateTargetSummary.IsEmpty())
			{
				Priority = 49;
			}
			else if (ActionId == TEXT("check_readiness"))
			{
				Priority = 50;
			}
			else if (ActionId == TEXT("review_readiness_repair_queue") && !OutOverview.ReadinessRepairTargetSummary.IsEmpty())
			{
				Priority = 51;
			}
			else if (ActionId == TEXT("review_platform_preflight_gate") && !OutOverview.PlatformPreflightTargetSummary.IsEmpty())
			{
				Priority = 51;
			}
			else if (ActionId == TEXT("review_live_editor_bridge_gate") && !OutOverview.LiveEditorBridgeTargetSummary.IsEmpty())
			{
				Priority = 52;
			}
			else if (ActionId == TEXT("review_wip_promotion_gate") && !OutOverview.WipPromotionTargetSummary.IsEmpty())
			{
				Priority = 53;
			}
			else if (ActionId == TEXT("review_blueprint_mutation_gate") && !OutOverview.BlueprintMutationTargetSummary.IsEmpty())
			{
				Priority = 54;
			}
			else if (ActionId == TEXT("review_bridge_wrapper_coverage") && !OutOverview.BridgeWrapperTargetSummary.IsEmpty())
			{
				Priority = 55;
			}
			else if (ActionId == TEXT("review_test_lane_gates") && !OutOverview.TestLaneTargetSummary.IsEmpty())
			{
				Priority = 56;
			}
			else if (ActionId == TEXT("refresh_companion_status"))
			{
				Priority = 56;
			}
			else if (ActionId == TEXT("resume_companion_session"))
			{
				Priority = 55;
			}
			else if (ActionId == TEXT("show_companion_dashboard"))
			{
				Priority = 57;
			}
			else if (ActionId == TEXT("show_evidence_ledger"))
			{
				Priority = 58;
			}
			else if (ActionId == TEXT("start_companion_session"))
			{
				Priority = 60;
			}

			FString Suffix;
			if (ActionId == TEXT("review_evidence_requirements") && !OutOverview.EvidenceReviewTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.EvidenceReviewTargetSummary);
			}
			else if (ActionId == TEXT("record_evidence") && !OutOverview.EvidenceTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.EvidenceTargetSummary);
			}
			else if (ActionId == TEXT("record_queued_action_evidence") && !OutOverview.QueuedEvidenceTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.QueuedEvidenceTargetSummary);
			}
			else if (ActionId == TEXT("record_generated_asset_evidence") && !OutOverview.GeneratedAssetEvidenceTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAssetEvidenceTargetSummary);
			}
			else if (ActionId == TEXT("record_paid_generation_evidence") && !OutOverview.PaidGenerationEvidenceTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.PaidGenerationEvidenceTargetSummary);
			}
			else if (ActionId == TEXT("record_generated_animation_evidence") && !OutOverview.GeneratedAnimationEvidenceTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAnimationEvidenceTargetSummary);
			}
			else if (ActionId == TEXT("record_feature_completion_contract") && !OutOverview.FeatureCompletionContractTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.FeatureCompletionContractTargetSummary);
			}
			else if (ActionId == TEXT("record_runtime_evidence") && !OutOverview.RuntimeEvidenceTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.RuntimeEvidenceTargetSummary);
			}
			else if (ActionId == TEXT("execute_next_safe_step") && !OutOverview.ExecuteTargetSummary.IsEmpty())
			{
				Suffix = OutOverview.ExecutionReviewTargetSummary.IsEmpty()
					? FString::Printf(TEXT(": %s"), *OutOverview.ExecuteTargetSummary)
					: FString::Printf(TEXT(": %s, %s"), *OutOverview.ExecuteTargetSummary, *OutOverview.ExecutionReviewTargetSummary);
			}
			else if (ActionId == TEXT("resolve_blockers") && !OutOverview.BlockerTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.BlockerTargetSummary);
			}
			else if (ActionId == TEXT("review_generated_asset_gate") && !OutOverview.GeneratedAssetReviewTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAssetReviewTargetSummary);
			}
			else if (ActionId == TEXT("review_generated_asset_lifecycle_gate") && !OutOverview.GeneratedAssetLifecycleTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAssetLifecycleTargetSummary);
			}
			else if (ActionId == TEXT("compile_asset_lifecycle_manifest") && !OutOverview.AssetLifecycleCompileTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.AssetLifecycleCompileTargetSummary);
			}
			else if (ActionId == TEXT("review_generated_animation_lifecycle_gate") && !OutOverview.GeneratedAnimationLifecycleTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAnimationLifecycleTargetSummary);
			}
			else if (ActionId == TEXT("compile_generated_animation_evidence") && !OutOverview.GeneratedAnimationCompileTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAnimationCompileTargetSummary);
			}
			else if (ActionId == TEXT("review_generated_asset_import_gate") && !OutOverview.GeneratedAssetImportTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAssetImportTargetSummary);
			}
			else if (ActionId == TEXT("review_generated_asset_quality_proof_gate") && !OutOverview.GeneratedAssetQualityProofTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAssetQualityProofTargetSummary);
			}
			else if (ActionId == TEXT("review_generated_asset_replacement_gate") && !OutOverview.GeneratedAssetReplacementTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAssetReplacementTargetSummary);
			}
			else if (ActionId == TEXT("review_provider_spend_gate") && !OutOverview.ProviderSpendTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.ProviderSpendTargetSummary);
			}
			else if (ActionId == TEXT("continue_with_placeholder_fallback") && !OutOverview.PlaceholderTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.PlaceholderTargetSummary);
			}
			else if (ActionId == TEXT("review_generated_asset_provider_task_gate") && !OutOverview.GeneratedAssetProviderTaskTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAssetProviderTaskTargetSummary);
			}
			else if (ActionId == TEXT("resolve_generated_asset") && !OutOverview.GeneratedAssetTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GeneratedAssetTargetSummary);
			}
			else if (ActionId == TEXT("compile_placeholder_manifest") && !OutOverview.PlaceholderTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.PlaceholderTargetSummary);
			}
			else if (ActionId == TEXT("review_editor_queue") && !OutOverview.QueueReviewTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.QueueReviewTargetSummary);
			}
			else if (ActionId == TEXT("queue_editor_actions") && !OutOverview.QueueTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.QueueTargetSummary);
			}
			else if (ActionId == TEXT("generate_work_order") && !OutOverview.WorkOrderTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.WorkOrderTargetSummary);
			}
			else if (ActionId == TEXT("review_gameplay_template_plan") && !OutOverview.GameplayTemplateTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.GameplayTemplateTargetSummary);
			}
			else if (ActionId == TEXT("check_readiness") && !OutOverview.ReadinessTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.ReadinessTargetSummary);
			}
			else if (ActionId == TEXT("review_readiness_repair_queue") && !OutOverview.ReadinessRepairTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.ReadinessRepairTargetSummary);
			}
			else if (ActionId == TEXT("review_platform_preflight_gate") && !OutOverview.PlatformPreflightTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.PlatformPreflightTargetSummary);
			}
			else if (ActionId == TEXT("review_live_editor_bridge_gate") && !OutOverview.LiveEditorBridgeTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.LiveEditorBridgeTargetSummary);
			}
			else if (ActionId == TEXT("review_wip_promotion_gate") && !OutOverview.WipPromotionTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.WipPromotionTargetSummary);
			}
			else if (ActionId == TEXT("review_blueprint_mutation_gate") && !OutOverview.BlueprintMutationTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.BlueprintMutationTargetSummary);
			}
			else if (ActionId == TEXT("review_bridge_wrapper_coverage") && !OutOverview.BridgeWrapperTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.BridgeWrapperTargetSummary);
			}
			else if (ActionId == TEXT("review_test_lane_gates") && !OutOverview.TestLaneTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.TestLaneTargetSummary);
			}
			else if (ActionId == TEXT("refresh_companion_status") && !OutOverview.StatusTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.StatusTargetSummary);
			}
			else if (ActionId == TEXT("repair_failed_step") && !OutOverview.RepairTargetSummary.IsEmpty())
			{
				Suffix = OutOverview.RepairReviewTargetSummary.IsEmpty()
					? FString::Printf(TEXT(": %s"), *OutOverview.RepairTargetSummary)
					: FString::Printf(TEXT(": %s, %s"), *OutOverview.RepairTargetSummary, *OutOverview.RepairReviewTargetSummary);
			}
			else if (ActionId == TEXT("review_runtime_verification") && !OutOverview.RuntimeReviewTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.RuntimeReviewTargetSummary);
			}
			else if (ActionId == TEXT("show_evidence_ledger") && !OutOverview.EvidenceLedgerTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.EvidenceLedgerTargetSummary);
			}
			else if (ActionId == TEXT("resume_companion_session") && !OutOverview.ResumeTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.ResumeTargetSummary);
			}
			else if (ActionId == TEXT("show_companion_dashboard") && !OutOverview.DashboardTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.DashboardTargetSummary);
			}
			else if (ActionId == TEXT("start_companion_session") && !OutOverview.StartTargetSummary.IsEmpty())
			{
				Suffix = FString::Printf(TEXT(": %s"), *OutOverview.StartTargetSummary);
			}

			if (Priority < BestWorkflowPriority)
			{
				BestWorkflowPriority = Priority;
				BestWorkflowAction = TruncateForCard(FString::Printf(TEXT("%s%s"), *Label, *Suffix), 120);
			}
		}

		if (!BestWorkflowAction.IsEmpty())
		{
			OutOverview.SuggestedAction = BestWorkflowAction;
		}
	}

	if (OutOverview.QueueSummary.IsEmpty())
	{
		OutOverview.QueueSummary = TEXT("empty");
	}
	if (OutOverview.QueueActionsSummary.IsEmpty())
	{
		OutOverview.QueueActionsSummary = OutOverview.QueuedActionCount > 0 ? TEXT("preview unavailable") : TEXT("none");
	}
	if (OutOverview.EvidenceSummary.IsEmpty())
	{
		OutOverview.EvidenceSummary = TEXT("no ledger");
	}
	if (OutOverview.EvidenceTimelineSummary.IsEmpty())
	{
		OutOverview.EvidenceTimelineSummary = TEXT("none");
	}
	if (OutOverview.NextSafeStepSummary.IsEmpty())
	{
		OutOverview.NextSafeStepSummary = OutOverview.QueuedActionCount > 0
			? (OutOverview.bQueueExecutable ? TEXT("queue ready") : TEXT("queue blocked"))
			: TEXT("empty");
	}
	if (OutOverview.FailureTriageSummary.IsEmpty())
	{
		OutOverview.FailureTriageSummary = TEXT("clear");
	}
	if (OutOverview.AssetQualitySummary.IsEmpty())
	{
		OutOverview.AssetQualitySummary = TEXT("none");
	}
	if (OutOverview.ReadinessPolicySummary.IsEmpty())
	{
		OutOverview.ReadinessPolicySummary = TEXT("none");
	}
	if (OutOverview.SuggestedAction.IsEmpty())
	{
		OutOverview.SuggestedAction = OutOverview.bBlocked ? TEXT("resolve blockers") : TEXT("review dashboard");
	}

	return true;
}

bool SMCPChatPanel::ParseMessagesResponse(const FString& JsonText, TArray<FChatMessage>& OutMessages) const
{
	TSharedPtr<FJsonObject> Root;
	const TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonText);
	if (!FJsonSerializer::Deserialize(Reader, Root) || !Root.IsValid())
	{
		return false;
	}

	const TArray<TSharedPtr<FJsonValue>>* MessageValues = nullptr;
	if (!Root->TryGetArrayField(TEXT("messages"), MessageValues) || MessageValues == nullptr)
	{
		return false;
	}

	for (const TSharedPtr<FJsonValue>& Value : *MessageValues)
	{
		const TSharedPtr<FJsonObject> Object = Value.IsValid() ? Value->AsObject() : nullptr;
		if (!Object.IsValid())
		{
			continue;
		}

		FChatMessage Message;
		Message.MessageId = GetStringField(Object, TEXT("message_id"));
		Message.Sender = GetStringField(Object, TEXT("sender"));
		Message.Message = GetStringField(Object, TEXT("message"));
		Message.Timestamp = GetStringField(Object, TEXT("timestamp"));

		if (!Message.Sender.IsEmpty() && !Message.Message.IsEmpty())
		{
			OutMessages.Add(Message);
		}
	}

	return true;
}

#undef LOCTEXT_NAMESPACE
