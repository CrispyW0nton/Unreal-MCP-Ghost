#include "MCPChatPanel.h"

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
#include "Widgets/Input/SEditableTextBox.h"
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
				.Text(LOCTEXT("PlayableSliceQuickAction", "Playable Slice"))
				.OnClicked(this, &SMCPChatPanel::HandleOpenPlayableSliceClicked)
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.Padding(0.0f, 0.0f, 6.0f, 0.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("BuildGameplayQuickAction", "Build Gameplay"))
				.OnClicked(this, &SMCPChatPanel::HandleOpenGameplayBuilderClicked)
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
			.Visibility(this, &SMCPChatPanel::GetPlayableSliceDialogVisibility)
			[
				BuildPlayableSliceDialog()
			]
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f, 0.0f, 8.0f, 4.0f)
		[
			SNew(SBox)
			.Visibility(this, &SMCPChatPanel::GetGameplayBuilderDialogVisibility)
			[
				BuildGameplayBuilderDialog()
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
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleContinueLastSessionClicked()
{
	if (!LastSessionName.IsEmpty())
	{
		CurrentSessionName = LastSessionName;
		LastAgentPollTimestamp.Empty();
		LoadHistory();
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
	bCommandPaletteVisible = true;
	CommandPaletteFilter.Empty();
	RefreshCommandPaletteItems();
	RebuildCommandPaletteResults();
	RecordTelemetryEvent(TEXT("command_palette_opened"));
	if (CommandPaletteInput.IsValid())
	{
		CommandPaletteInput->SetText(FText::GetEmpty());
		FSlateApplication::Get().SetKeyboardFocus(CommandPaletteInput.ToSharedRef());
	}
	SetStatus(LOCTEXT("StatusCommandPaletteOpened", "Command palette opened"), PendingStatusColor);
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

FReply SMCPChatPanel::HandleOpenPlayableSliceClicked()
{
	bPlayableSliceDialogVisible = !bPlayableSliceDialogVisible;
	if (bPlayableSliceDialogVisible)
	{
		LoadGenerativeSettings();
	}
	SetStatus(
		bPlayableSliceDialogVisible ? LOCTEXT("StatusPlayableSliceOpen", "Playable Slice workflow open") : LOCTEXT("StatusPlayableSliceClosed", "Playable Slice workflow hidden"),
		PendingStatusColor
	);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleInsertPlayableSlicePromptClicked()
{
	if (PlayableSliceBriefInput.IsValid())
	{
		PlayableSliceBrief = PlayableSliceBriefInput->GetText().ToString().TrimStartAndEnd();
	}
	if (PlayableSliceAssetRolesInput.IsValid())
	{
		PlayableSliceAssetRoles = PlayableSliceAssetRolesInput->GetText().ToString().TrimStartAndEnd();
	}
	if (PlayableSliceGameplayLoopInput.IsValid())
	{
		PlayableSliceGameplayLoop = PlayableSliceGameplayLoopInput->GetText().ToString().TrimStartAndEnd();
	}
	if (PlayableSliceAcceptanceInput.IsValid())
	{
		PlayableSliceAcceptance = PlayableSliceAcceptanceInput->GetText().ToString().TrimStartAndEnd();
	}
	if (PlayableSliceEvidenceInput.IsValid())
	{
		PlayableSliceEvidence = PlayableSliceEvidenceInput->GetText().ToString().TrimStartAndEnd();
	}
	if (PlayableSliceBrief.IsEmpty())
	{
		PlayableSliceBrief = TEXT("make a tiny playable arena with one generated pickup and a clear win condition");
	}
	if (PlayableSliceAssetRoles.IsEmpty())
	{
		PlayableSliceAssetRoles = TEXT("pickup, gate, arena prop");
	}
	if (PlayableSliceGameplayLoop.IsEmpty())
	{
		PlayableSliceGameplayLoop = TEXT("spawn player, collect pickup, trigger feedback, open gate, show completion");
	}
	if (PlayableSliceAcceptance.IsEmpty())
	{
		PlayableSliceAcceptance = TEXT("generated assets imported, Blueprint gameplay compiled, PIE smoke passes, screenshot evidence captured");
	}
	if (PlayableSliceEvidence.IsEmpty())
	{
		PlayableSliceEvidence = TEXT("Tripo task ids, imported asset paths, compile reports, PIE log, viewport screenshot");
	}
	if (!IsGenerativeApiKeyConfigured())
	{
		bGenerativeSettingsVisible = true;
		SetStatus(LOCTEXT("StatusPlayableSliceMissingKey", "Add a Tripo API key before generating a playable slice"), ErrorStatusColor);
		return FReply::Handled();
	}

	InsertComposerText(BuildPlayableSlicePrompt());
	bPlayableSliceDialogVisible = false;
	RecordTelemetryEvent(TEXT("playable_slice_workflow_prompt_inserted"));
	SetStatus(
		bGenerativeSpendConfirmed ? LOCTEXT("StatusPlayableSliceInsertedConfirmed", "Inserted playable-slice generation workflow") : LOCTEXT("StatusPlayableSliceInsertedNeedsSpend", "Inserted playable-slice workflow; confirm spend before paid execution"),
		bGenerativeSpendConfirmed ? OkStatusColor : PendingStatusColor
	);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleOpenGameplayBuilderClicked()
{
	bGameplayBuilderDialogVisible = !bGameplayBuilderDialogVisible;
	SetStatus(
		bGameplayBuilderDialogVisible ? LOCTEXT("StatusGameplayBuilderOpen", "Build Gameplay quick action open") : LOCTEXT("StatusGameplayBuilderClosed", "Build Gameplay quick action hidden"),
		PendingStatusColor
	);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleInsertGameplayBuilderPromptClicked()
{
	if (GameplayBuilderBriefInput.IsValid())
	{
		GameplayBuilderBrief = GameplayBuilderBriefInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GameplayBuilderTargetInput.IsValid())
	{
		GameplayBuilderTarget = GameplayBuilderTargetInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GameplayBuilderAcceptanceInput.IsValid())
	{
		GameplayBuilderAcceptance = GameplayBuilderAcceptanceInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GameplayBuilderEvidenceInput.IsValid())
	{
		GameplayBuilderEvidence = GameplayBuilderEvidenceInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GameplayBuilderBrief.IsEmpty())
	{
		GameplayBuilderBrief = TEXT("add a small gameplay mechanic with clear player feedback");
	}
	if (GameplayBuilderTarget.IsEmpty())
	{
		GameplayBuilderTarget = TEXT("@selected");
	}
	if (GameplayBuilderAcceptance.IsEmpty())
	{
		GameplayBuilderAcceptance = TEXT("compile touched Blueprints, run PIE/log smoke, capture screenshot evidence, and list changed assets");
	}
	if (GameplayBuilderEvidence.IsEmpty())
	{
		GameplayBuilderEvidence = TEXT("PIE log plus viewport screenshot");
	}

	InsertComposerText(BuildGameplayBuilderPrompt());
	bGameplayBuilderDialogVisible = false;
	RecordTelemetryEvent(TEXT("gameplay_builder_prompt_inserted"));
	SetStatus(LOCTEXT("StatusGameplayBuilderInserted", "Inserted gameplay development workflow prompt"), OkStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleGameplayModeMechanicClicked()
{
	GameplayBuilderMode = TEXT("mechanic");
	SetStatus(LOCTEXT("StatusGameplayModeMechanic", "Gameplay mode: Mechanic"), PendingStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleGameplayModeAIClicked()
{
	GameplayBuilderMode = TEXT("ai");
	SetStatus(LOCTEXT("StatusGameplayModeAI", "Gameplay mode: AI"), PendingStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleGameplayModeHudClicked()
{
	GameplayBuilderMode = TEXT("hud");
	SetStatus(LOCTEXT("StatusGameplayModeHud", "Gameplay mode: HUD"), PendingStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleGameplayModeLevelFlowClicked()
{
	GameplayBuilderMode = TEXT("level_flow");
	SetStatus(LOCTEXT("StatusGameplayModeLevelFlow", "Gameplay mode: Level Flow"), PendingStatusColor);
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

FReply SMCPChatPanel::HandleInsertGenerateAssetToolCallClicked()
{
	if (GenerateAssetPromptInput.IsValid())
	{
		GenerateAssetPrompt = GenerateAssetPromptInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetNameInput.IsValid())
	{
		GenerateAssetName = GenerateAssetNameInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetImageInputBox.IsValid())
	{
		GenerateAssetImageInput = GenerateAssetImageInputBox->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetFrontImageInputBox.IsValid())
	{
		GenerateAssetFrontImageInput = GenerateAssetFrontImageInputBox->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetLeftImageInputBox.IsValid())
	{
		GenerateAssetLeftImageInput = GenerateAssetLeftImageInputBox->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetBackImageInputBox.IsValid())
	{
		GenerateAssetBackImageInput = GenerateAssetBackImageInputBox->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetRightImageInputBox.IsValid())
	{
		GenerateAssetRightImageInput = GenerateAssetRightImageInputBox->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureTaskIdInput.IsValid())
	{
		GenerateTextureTaskId = GenerateTextureTaskIdInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTexturePromptInput.IsValid())
	{
		GenerateTexturePrompt = GenerateTexturePromptInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureReferenceImageInputBox.IsValid())
	{
		GenerateTextureReferenceImageInput = GenerateTextureReferenceImageInputBox->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTexturePaintNotesInput.IsValid())
	{
		GenerateTexturePaintNotes = GenerateTexturePaintNotesInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureViewAngleInput.IsValid())
	{
		GenerateTextureViewAngle = GenerateTextureViewAngleInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureBrushSizeInput.IsValid())
	{
		GenerateTextureBrushSize = GenerateTextureBrushSizeInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureBrushStrengthInput.IsValid())
	{
		GenerateTextureBrushStrength = GenerateTextureBrushStrengthInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureBrushHardnessInput.IsValid())
	{
		GenerateTextureBrushHardness = GenerateTextureBrushHardnessInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureCreativityStrengthInput.IsValid())
	{
		GenerateTextureCreativityStrength = GenerateTextureCreativityStrengthInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTexturePaintModeInput.IsValid())
	{
		GenerateTexturePaintMode = GenerateTexturePaintModeInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTexturePaintColorInput.IsValid())
	{
		GenerateTexturePaintColor = GenerateTexturePaintColorInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureBlendModeInput.IsValid())
	{
		GenerateTextureBlendMode = GenerateTextureBlendModeInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureSaveNameInput.IsValid())
	{
		GenerateTextureSaveName = GenerateTextureSaveNameInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureTripoProjectIdInput.IsValid())
	{
		GenerateTextureTripoProjectId = GenerateTextureTripoProjectIdInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureRenderImageBucketInput.IsValid())
	{
		GenerateTextureRenderImageBucket = GenerateTextureRenderImageBucketInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureRenderImageKeyInput.IsValid())
	{
		GenerateTextureRenderImageKey = GenerateTextureRenderImageKeyInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureRenderImageUrlInput.IsValid())
	{
		GenerateTextureRenderImageUrl = GenerateTextureRenderImageUrlInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureCameraMatrixInput.IsValid())
	{
		GenerateTextureCameraMatrix = GenerateTextureCameraMatrixInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateTextureImageMapJsonInput.IsValid())
	{
		GenerateTextureImageMapJson = GenerateTextureImageMapJsonInput->GetText().ToString().TrimStartAndEnd();
	}
	if (GenerateAssetPrompt.IsEmpty())
	{
		GenerateAssetPrompt = TEXT("game-ready stylized prop, clean silhouette, PBR textures");
	}
	if (GenerateAssetName.IsEmpty())
	{
		GenerateAssetName = TEXT("SM_GeneratedAsset");
	}
	if (!IsGenerativeApiKeyConfigured())
	{
		bGenerativeSettingsVisible = true;
		SetStatus(LOCTEXT("StatusGenerateAssetMissingKey", "Add a Tripo API key before generating"), ErrorStatusColor);
		return FReply::Handled();
	}
	if (GenerateAssetMode == TEXT("image_to_model") && GenerateAssetImageInput.IsEmpty())
	{
		SetStatus(LOCTEXT("StatusGenerateAssetMissingImage", "Image to 3D needs an image path or URL"), ErrorStatusColor);
		return FReply::Handled();
	}
	if (GenerateAssetMode == TEXT("multiview_to_model"))
	{
		int32 ViewCount = 0;
		ViewCount += GenerateAssetFrontImageInput.IsEmpty() ? 0 : 1;
		ViewCount += GenerateAssetLeftImageInput.IsEmpty() ? 0 : 1;
		ViewCount += GenerateAssetBackImageInput.IsEmpty() ? 0 : 1;
		ViewCount += GenerateAssetRightImageInput.IsEmpty() ? 0 : 1;
		if (ViewCount < 2 || GenerateAssetFrontImageInput.IsEmpty())
		{
			SetStatus(LOCTEXT("StatusGenerateAssetMissingMultiview", "Multi-image to 3D needs front plus at least one more view"), ErrorStatusColor);
			return FReply::Handled();
		}
	}
	if (GenerateAssetMode == TEXT("texture_model") && (GenerateTextureTaskId.IsEmpty() || GenerateTexturePrompt.IsEmpty()))
	{
		SetStatus(LOCTEXT("StatusGenerateAssetMissingTextureInputs", "Texture/Paint needs a model task id and texture prompt"), ErrorStatusColor);
		return FReply::Handled();
	}

	InsertComposerText(BuildGenerateAssetToolCallPrompt());
	bGenerateAssetDialogVisible = false;
	RecordTelemetryEvent(TEXT("generate_asset_quick_action_inserted"));
	SetStatus(
		bGenerativeSpendConfirmed ? LOCTEXT("StatusGenerateAssetInsertedConfirmed", "Inserted Tripo asset generation call") : LOCTEXT("StatusGenerateAssetInsertedNeedsSpend", "Inserted Tripo call; confirm spend before paid execution"),
		bGenerativeSpendConfirmed ? OkStatusColor : PendingStatusColor
	);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleGenerateModeTextToModelClicked()
{
	GenerateAssetMode = TEXT("text_to_model");
	SetStatus(LOCTEXT("StatusGenerateModeText", "Generate mode: Text to 3D"), PendingStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleGenerateModeImageToModelClicked()
{
	GenerateAssetMode = TEXT("image_to_model");
	SetStatus(LOCTEXT("StatusGenerateModeImage", "Generate mode: Image to 3D"), PendingStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleGenerateModeMultiviewToModelClicked()
{
	GenerateAssetMode = TEXT("multiview_to_model");
	SetStatus(LOCTEXT("StatusGenerateModeMultiview", "Generate mode: Multi-image to 3D"), PendingStatusColor);
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleGenerateModeTextureModelClicked()
{
	GenerateAssetMode = TEXT("texture_model");
	SetStatus(LOCTEXT("StatusGenerateModeTexture", "Generate mode: Texture/Paint"), PendingStatusColor);
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

FReply SMCPChatPanel::HandleClearGenerativeApiKeyClicked()
{
	GenerativeApiKey.Empty();
	if (GenerativeApiKeyInput.IsValid())
	{
		GenerativeApiKeyInput->SetText(FText::GetEmpty());
	}
	IFileManager::Get().Delete(*GetGenerativeSecretsFilePath(), false, true, true);
	RecordTelemetryEvent(TEXT("generative_api_key_cleared"));
	SetStatus(LOCTEXT("StatusGenerativeApiKeyCleared", "Tripo API key cleared"), PendingStatusColor);
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
	FString Path = TEXT("/chat/poll?sender=agent") + BuildSessionQueryParam();
	if (!LastAgentPollTimestamp.IsEmpty())
	{
		Path += TEXT("&since=");
		Path += FGenericPlatformHttp::UrlEncode(LastAgentPollTimestamp);
	}

	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(Path), TEXT("GET"));
	const double RequestStartSeconds = FPlatformTime::Seconds();
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this, RequestStartSeconds](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
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
	Request->ProcessRequest();
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

TSharedRef<SWidget> SMCPChatPanel::BuildPlayableSliceDialog()
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
					.Text(LOCTEXT("PlayableSliceDialogTitle", "Playable Slice"))
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
				SAssignNew(PlayableSliceBriefInput, SEditableTextBox)
				.HintText(LOCTEXT("PlayableSliceBriefHint", "one-sentence playable game brief"))
				.Text(FText::FromString(PlayableSliceBrief))
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
					SAssignNew(PlayableSliceAssetRolesInput, SEditableTextBox)
					.HintText(LOCTEXT("PlayableSliceAssetRolesHint", "generated asset roles"))
					.Text(FText::FromString(PlayableSliceAssetRoles))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(0.5f)
				[
					SAssignNew(PlayableSliceEvidenceInput, SEditableTextBox)
					.HintText(LOCTEXT("PlayableSliceEvidenceHint", "required evidence"))
					.Text(FText::FromString(PlayableSliceEvidence))
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(PlayableSliceGameplayLoopInput, SEditableTextBox)
				.HintText(LOCTEXT("PlayableSliceGameplayLoopHint", "core playable loop"))
				.Text(FText::FromString(PlayableSliceGameplayLoop))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(PlayableSliceAcceptanceInput, SEditableTextBox)
				.HintText(LOCTEXT("PlayableSliceAcceptanceHint", "acceptance criteria"))
				.Text(FText::FromString(PlayableSliceAcceptance))
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
					[
						SNew(STextBlock)
						.Text(this, &SMCPChatPanel::GetPlayableSlicePreviewText)
						.AutoWrapText(true)
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 4.0f, 0.0f, 0.0f)
					[
						SNew(STextBlock)
						.Text(this, &SMCPChatPanel::GetGenerativeCreditsDisplayText)
						.ColorAndOpacity(FSlateColor::UseSubduedForeground())
						.AutoWrapText(true)
					]
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SButton)
				.Text(LOCTEXT("InsertPlayableSlicePrompt", "Insert Workflow Prompt"))
				.OnClicked(this, &SMCPChatPanel::HandleInsertPlayableSlicePromptClicked)
			]
		];
}

TSharedRef<SWidget> SMCPChatPanel::BuildGameplayBuilderDialog()
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
				.Text(LOCTEXT("GameplayBuilderDialogTitle", "Build Gameplay"))
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SHorizontalBox)

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("GameplayModeMechanic", "Mechanic"))
					.OnClicked(this, &SMCPChatPanel::HandleGameplayModeMechanicClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("GameplayModeAI", "AI"))
					.OnClicked(this, &SMCPChatPanel::HandleGameplayModeAIClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("GameplayModeHud", "HUD"))
					.OnClicked(this, &SMCPChatPanel::HandleGameplayModeHudClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.Text(LOCTEXT("GameplayModeLevelFlow", "Level Flow"))
					.OnClicked(this, &SMCPChatPanel::HandleGameplayModeLevelFlowClicked)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(GameplayBuilderBriefInput, SEditableTextBox)
				.HintText(LOCTEXT("GameplayBuilderBriefHint", "gameplay feature brief"))
				.Text(FText::FromString(GameplayBuilderBrief))
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
					SAssignNew(GameplayBuilderTargetInput, SEditableTextBox)
					.HintText(LOCTEXT("GameplayBuilderTargetHint", "@selected, @asset:/Game/..., or actor name"))
					.Text(FText::FromString(GameplayBuilderTarget))
				]

				+ SHorizontalBox::Slot()
				.FillWidth(0.5f)
				[
					SAssignNew(GameplayBuilderEvidenceInput, SEditableTextBox)
					.HintText(LOCTEXT("GameplayBuilderEvidenceHint", "required evidence"))
					.Text(FText::FromString(GameplayBuilderEvidence))
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SAssignNew(GameplayBuilderAcceptanceInput, SEditableTextBox)
				.HintText(LOCTEXT("GameplayBuilderAcceptanceHint", "acceptance criteria"))
				.Text(FText::FromString(GameplayBuilderAcceptance))
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
					.Text(this, &SMCPChatPanel::GetGameplayBuilderPreviewText)
					.AutoWrapText(true)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(SButton)
				.Text(LOCTEXT("InsertGameplayBuilderPrompt", "Insert Workflow Prompt"))
				.OnClicked(this, &SMCPChatPanel::HandleInsertGameplayBuilderPromptClicked)
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
					.Text(LOCTEXT("GenerateAssetDialogTitle", "Generate Asset"))
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
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("GenerateModeTextToModel", "Text to 3D"))
					.OnClicked(this, &SMCPChatPanel::HandleGenerateModeTextToModelClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("GenerateModeImageToModel", "Image to 3D"))
					.OnClicked(this, &SMCPChatPanel::HandleGenerateModeImageToModelClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				.Padding(0.0f, 0.0f, 6.0f, 0.0f)
				[
					SNew(SButton)
					.Text(LOCTEXT("GenerateModeMultiviewToModel", "Multi-Image to 3D"))
					.OnClicked(this, &SMCPChatPanel::HandleGenerateModeMultiviewToModelClicked)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.Text(LOCTEXT("GenerateModeTextureModel", "Texture/Paint"))
					.OnClicked(this, &SMCPChatPanel::HandleGenerateModeTextureModelClicked)
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SBox)
				.Visibility(this, &SMCPChatPanel::GetGenerateTextToModelVisibility)
				[
					SAssignNew(GenerateAssetPromptInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerateAssetPromptHint", "Prompt for Tripo text_to_model"))
					.Text(FText::FromString(GenerateAssetPrompt))
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
				SNew(SBox)
				.Visibility(this, &SMCPChatPanel::GetGenerateImageToModelVisibility)
				[
					SAssignNew(GenerateAssetImageInputBox, SEditableTextBox)
					.HintText(LOCTEXT("GenerateAssetImageHint", "Image path or URL for image_to_model"))
					.Text(FText::FromString(GenerateAssetImageInput))
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SBox)
				.Visibility(this, &SMCPChatPanel::GetGenerateMultiviewToModelVisibility)
				[
					SNew(SHorizontalBox)

					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.Padding(0.0f, 0.0f, 6.0f, 0.0f)
					[
						SAssignNew(GenerateAssetFrontImageInputBox, SEditableTextBox)
						.HintText(LOCTEXT("GenerateAssetFrontImageHint", "front image path or URL"))
						.Text(FText::FromString(GenerateAssetFrontImageInput))
					]

					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.Padding(0.0f, 0.0f, 6.0f, 0.0f)
					[
						SAssignNew(GenerateAssetLeftImageInputBox, SEditableTextBox)
						.HintText(LOCTEXT("GenerateAssetLeftImageHint", "left image path or URL"))
						.Text(FText::FromString(GenerateAssetLeftImageInput))
					]

					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					.Padding(0.0f, 0.0f, 6.0f, 0.0f)
					[
						SAssignNew(GenerateAssetBackImageInputBox, SEditableTextBox)
						.HintText(LOCTEXT("GenerateAssetBackImageHint", "back image path or URL"))
						.Text(FText::FromString(GenerateAssetBackImageInput))
					]

					+ SHorizontalBox::Slot()
					.FillWidth(1.0f)
					[
						SAssignNew(GenerateAssetRightImageInputBox, SEditableTextBox)
						.HintText(LOCTEXT("GenerateAssetRightImageHint", "right image path or URL"))
						.Text(FText::FromString(GenerateAssetRightImageInput))
					]
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SBox)
				.Visibility(this, &SMCPChatPanel::GetGenerateTextureModelVisibility)
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
							.Text(LOCTEXT("GenerateTextureTargetTitle", "Texture Target"))
							.Font(FAppStyle::GetFontStyle("SmallFontBold"))
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						[
							SNew(SHorizontalBox)

							+ SHorizontalBox::Slot()
							.FillWidth(0.5f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTextureTaskIdInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureTaskIdHint", "existing model task_id"))
								.Text(FText::FromString(GenerateTextureTaskId))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.5f)
							[
								SAssignNew(GenerateTextureSaveNameInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureSaveNameHint", "save asset name"))
								.Text(FText::FromString(GenerateTextureSaveName))
							]
						]
					]
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SBox)
				.Visibility(this, &SMCPChatPanel::GetGenerateTextureModelVisibility)
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
							.Text(LOCTEXT("GenerateTextureDirectionTitle", "Texture Direction"))
							.Font(FAppStyle::GetFontStyle("SmallFontBold"))
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
								SAssignNew(GenerateTexturePromptInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTexturePromptHint", "texture or paint prompt"))
								.Text(FText::FromString(GenerateTexturePrompt))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.5f)
							[
								SAssignNew(GenerateTextureReferenceImageInputBox, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureReferenceImageHint", "texture reference image path or URL"))
								.Text(FText::FromString(GenerateTextureReferenceImageInput))
							]
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						[
							SAssignNew(GenerateTexturePaintNotesInput, SEditableTextBox)
							.HintText(LOCTEXT("GenerateTexturePaintNotesHint", "paint and blend notes"))
							.Text(FText::FromString(GenerateTexturePaintNotes))
						]
					]
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SBox)
				.Visibility(this, &SMCPChatPanel::GetGenerateTextureModelVisibility)
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
							.Text(LOCTEXT("GenerateTexturePaintControlsTitle", "Paint Controls"))
							.Font(FAppStyle::GetFontStyle("SmallFontBold"))
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 6.0f)
						[
							SNew(SHorizontalBox)

							+ SHorizontalBox::Slot()
							.FillWidth(0.25f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTextureViewAngleInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureViewAngleHint", "view angle"))
								.Text(FText::FromString(GenerateTextureViewAngle))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.25f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTextureBrushSizeInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureBrushSizeHint", "brush size"))
								.Text(FText::FromString(GenerateTextureBrushSize))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.25f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTextureBrushStrengthInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureBrushStrengthHint", "brush strength"))
								.Text(FText::FromString(GenerateTextureBrushStrength))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.25f)
							[
								SAssignNew(GenerateTextureBrushHardnessInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureBrushHardnessHint", "hardness"))
								.Text(FText::FromString(GenerateTextureBrushHardness))
							]
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						[
							SNew(SHorizontalBox)

							+ SHorizontalBox::Slot()
							.FillWidth(0.25f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTextureCreativityStrengthInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureCreativityHint", "creativity"))
								.Text(FText::FromString(GenerateTextureCreativityStrength))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.25f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTexturePaintModeInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTexturePaintModeHint", "image or color"))
								.Text(FText::FromString(GenerateTexturePaintMode))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.25f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTexturePaintColorInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTexturePaintColorHint", "#FFFFFF"))
								.Text(FText::FromString(GenerateTexturePaintColor))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.25f)
							[
								SAssignNew(GenerateTextureBlendModeInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureBlendModeHint", "blend mode"))
								.Text(FText::FromString(GenerateTextureBlendMode))
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
					SNew(SVerticalBox)

					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(STextBlock)
						.Text(LOCTEXT("GenerativeCreditsDisplayTitle", "Generative Credits"))
						.Font(FAppStyle::GetFontStyle("SmallFontBold"))
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 2.0f, 0.0f, 0.0f)
					[
						SNew(STextBlock)
						.Text(this, &SMCPChatPanel::GetGenerativeCreditsDisplayText)
						.ColorAndOpacity(FSlateColor::UseSubduedForeground())
						.AutoWrapText(true)
					]
				]
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 0.0f, 0.0f, 6.0f)
			[
				SNew(SBox)
				.Visibility(this, &SMCPChatPanel::GetGenerateTextureModelVisibility)
				[
					SNew(SExpandableArea)
					.InitiallyCollapsed(true)
					.AreaTitle(LOCTEXT("GenerateTextureStudioSnapshotTitle", "Studio Snapshot"))
					.BodyContent()
					[
						SNew(SVerticalBox)

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 6.0f)
						[
							SNew(SHorizontalBox)

							+ SHorizontalBox::Slot()
							.FillWidth(0.5f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTextureTripoProjectIdInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureTripoProjectIdHint", "Tripo project_id"))
								.Text(FText::FromString(GenerateTextureTripoProjectId))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.5f)
							[
								SAssignNew(GenerateTextureCameraMatrixInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureCameraMatrixHint", "camera matrix JSON"))
								.Text(FText::FromString(GenerateTextureCameraMatrix))
							]
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						.Padding(0.0f, 0.0f, 0.0f, 6.0f)
						[
							SNew(SHorizontalBox)

							+ SHorizontalBox::Slot()
							.FillWidth(0.34f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTextureRenderImageBucketInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureRenderImageBucketHint", "render image bucket"))
								.Text(FText::FromString(GenerateTextureRenderImageBucket))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.33f)
							.Padding(0.0f, 0.0f, 6.0f, 0.0f)
							[
								SAssignNew(GenerateTextureRenderImageKeyInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureRenderImageKeyHint", "render image key"))
								.Text(FText::FromString(GenerateTextureRenderImageKey))
							]

							+ SHorizontalBox::Slot()
							.FillWidth(0.33f)
							[
								SAssignNew(GenerateTextureRenderImageUrlInput, SEditableTextBox)
								.HintText(LOCTEXT("GenerateTextureRenderImageUrlHint", "render image URL"))
								.Text(FText::FromString(GenerateTextureRenderImageUrl))
							]
						]

						+ SVerticalBox::Slot()
						.AutoHeight()
						[
							SAssignNew(GenerateTextureImageMapJsonInput, SEditableTextBox)
							.HintText(LOCTEXT("GenerateTextureImageMapJsonHint", "Magic Brush image_map JSON for final painted apply"))
							.Text(FText::FromString(GenerateTextureImageMapJson))
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
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
				.Padding(6.0f)
				[
					SNew(SVerticalBox)

					+ SVerticalBox::Slot()
					.AutoHeight()
					[
						SNew(STextBlock)
						.Text(LOCTEXT("GenerativeSettingsCreditsTitle", "Generative Credits"))
						.Font(FAppStyle::GetFontStyle("SmallFontBold"))
					]

					+ SVerticalBox::Slot()
					.AutoHeight()
					.Padding(0.0f, 2.0f, 0.0f, 0.0f)
					[
						SNew(STextBlock)
						.Text(this, &SMCPChatPanel::GetGenerativeCreditsDisplayText)
						.ColorAndOpacity(FSlateColor::UseSubduedForeground())
						.AutoWrapText(true)
					]
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
					SAssignNew(GenerativeApiKeyInput, SEditableTextBox)
					.HintText(LOCTEXT("GenerativeApiKeyHint", "TRIPO_API_KEY"))
					.Text(FText::FromString(GenerativeApiKey))
					.IsPassword(true)
				]

				+ SHorizontalBox::Slot()
				.AutoWidth()
				[
					SNew(SButton)
					.Text(LOCTEXT("ClearGenerativeApiKey", "Clear Key"))
					.OnClicked(this, &SMCPChatPanel::HandleClearGenerativeApiKeyClicked)
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
		TEXT("Open the Tripo generate-asset dialog"),
		TEXT("Open Generate Asset and insert a gen_tripo_text_to_model request using the current generative settings."),
		TEXT("generative")
	);
	AddCommandPaletteItem(
		TEXT("Playable Slice quick action"),
		TEXT("Insert a guided asset generation plus gameplay workflow"),
		BuildPlayableSlicePrompt(),
		TEXT("gameplay")
	);
	AddCommandPaletteItem(
		TEXT("Build Gameplay quick action"),
		TEXT("Insert a guided gameplay/AI/HUD/level development workflow"),
		BuildGameplayBuilderPrompt(),
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
	return FText::Format(LOCTEXT("GenerativeAuthStatus", "Tripo auth: {0}"), FText::FromString(GetGenerativeApiKeySource()));
}

FText SMCPChatPanel::GetGenerativeBudgetText() const
{
	return FText::Format(
		LOCTEXT("GenerativeBudgetStatus", "Budget: {0} credits/session | Pending spend: {1} | Confirmed: {2} | Output: {3}"),
		FText::AsNumber(GenerativeSessionCreditBudget),
		FText::AsNumber(GenerativePendingSpendCredits),
		bGenerativeSpendConfirmed ? LOCTEXT("GenerativeSpendYes", "yes") : LOCTEXT("GenerativeSpendNo", "no"),
		FText::FromString(GenerativeOutputFolder)
	);
}

FText SMCPChatPanel::GetGenerativeCreditsDisplayText() const
{
	const int32 RemainingCredits = FMath::Max(0, GenerativeSessionCreditBudget - GenerativeSessionCreditsUsed);
	return FText::Format(
		LOCTEXT("GenerativeCreditsDisplay", "Budget {0} | Used {1} | Remaining {2} | Next spend {3} | Confirmed {4}"),
		FText::AsNumber(GenerativeSessionCreditBudget),
		FText::AsNumber(GenerativeSessionCreditsUsed),
		FText::AsNumber(RemainingCredits),
		FText::AsNumber(GenerativePendingSpendCredits),
		bGenerativeSpendConfirmed ? LOCTEXT("GenerativeCreditsConfirmedYes", "yes") : LOCTEXT("GenerativeCreditsConfirmedNo", "no")
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

FString SMCPChatPanel::BuildPlayableSlicePrompt() const
{
	auto Escape = [](const FString& Value) -> FString
	{
		return Value.Replace(TEXT("\""), TEXT("'"));
	};

	const FString SessionName = CurrentSessionName.IsEmpty() ? FString(TEXT("default")) : CurrentSessionName;
	const FString ConfirmSpend = bGenerativeSpendConfirmed ? TEXT("true") : TEXT("false");
	const FString SliceContentPath = FString::Printf(TEXT("%s/PlayableSlice"), *GenerativeOutputFolder);

	return FString::Printf(
		TEXT("Use the MCP Chat dock as the in-editor AI IDE to turn this one-sentence brief into a playable Unreal vertical slice.\n")
		TEXT("Playable-slice parameters:\n")
		TEXT("- brief: \"%s\"\n")
		TEXT("- generated_asset_roles: \"%s\"\n")
		TEXT("- gameplay_loop: \"%s\"\n")
		TEXT("- output_folder: \"%s\"\n")
		TEXT("- acceptance_criteria: \"%s\"\n")
		TEXT("- required_evidence: \"%s\"\n")
		TEXT("- session_name: \"%s\"\n")
		TEXT("- confirm_spend: %s\n")
		TEXT("Workflow:\n")
		TEXT("1. Call `skill_generate_playable_slice` with mode=\"plan\", brief=\"%s\", content_path=\"%s\", asset_roles=\"%s\", gameplay_loop=\"%s\", acceptance_criteria=\"%s\", and required_evidence=\"%s\". Use the returned `unreal_mcp_playable_slice_plan.v1` as the source of truth for asset roles, paths, gameplay targets, and validation.\n")
		TEXT("2. Discover current state with `get_project_context`, `scan_project_assets(path=\"/Game\", depth=3)`, `list_available_tools(domain=\"all\")`, and `get_onboarding_context(task=\"blueprints\")`, `get_onboarding_context(task=\"world_building\")`, and `get_onboarding_context(task=\"umg\")`.\n")
		TEXT("3. Produce a short execution plan that maps each generated_asset_role to a concrete Unreal asset path under \"%s\" and lists the Blueprints, widgets, actors, or level assets to create or modify. Ask only before destructive overwrite.\n")
		TEXT("4. For each missing 3D asset role, either call `skill_generate_playable_slice` with mode=\"submit_assets\", session_name=\"%s\", confirm_spend=%s, and the same asset_roles/gameplay_loop/acceptance_criteria/required_evidence after spend approval, or use MCP tool `gen_tripo_text_to_model` with texture=true, pbr=true, texture_quality=\"%s\", face_limit=12000, smart_low_poly=true, model_version=\"%s\", session_name=\"%s\", confirm_spend=%s, and a prompt that includes the role, the brief, clean game-ready topology, readable silhouette, collision-friendly proportions, and PBR material intent.\n")
		TEXT("5. Call `skill_generate_playable_slice` with mode=\"orchestrate\", the same asset_roles/gameplay_loop/acceptance_criteria/required_evidence, and any submitted task JSON to get the import/gameplay/PIE/report execution package. For each Tripo task, call `gen_tripo_wait_for_task` until complete, then call `gen_tripo_import_to_project` with content_path \"%s\" and a role-specific asset_name. Record task_id, credit usage, imported asset paths, materials, and warnings.\n")
		TEXT("6. If a hero asset needs extra art direction, use the Texture/Paint path: first call `gen_prepare_texture_paint_session`, then use `gen_tripo_magic_brush_generate`, `gen_tripo_magic_brush_get_retexture`, optional `gen_tripo_magic_brush_list_images`, and `gen_tripo_magic_brush_apply` only when project/render/image_map data and spend approval are available.\n")
		TEXT("7. Build the playable loop using the appropriate Blueprint, actor, component, UMG, AI, level, lighting, collision, and placement MCP tools. Prefer small searchable graph/function names, reusable Actor Components for repeated behavior, and visible player feedback.\n")
		TEXT("8. Run `compile_blueprint_and_report` for every touched Blueprint or Widget Blueprint, save changed assets, and use readback/diagnostic tools to confirm generated meshes, materials, collision, references, and gameplay wiring are actually assigned.\n")
		TEXT("9. Verify runtime with `pie_launch_session`, exercise the loop as much as tools allow, capture `pie_capture_log`, capture `viewport_capture_screenshot`, then run `pie_stop_session`.\n")
		TEXT("10. Finish with a concise report containing changed asset paths, Tripo task ids, credit usage, compile status, PIE/log/screenshot evidence paths, unresolved warnings/errors, and what remains for human design review."),
		*Escape(PlayableSliceBrief),
		*Escape(PlayableSliceAssetRoles),
		*Escape(PlayableSliceGameplayLoop),
		*Escape(SliceContentPath),
		*Escape(PlayableSliceAcceptance),
		*Escape(PlayableSliceEvidence),
		*Escape(SessionName),
		*ConfirmSpend,
		*Escape(PlayableSliceBrief),
		*Escape(SliceContentPath),
		*Escape(PlayableSliceAssetRoles),
		*Escape(PlayableSliceGameplayLoop),
		*Escape(PlayableSliceAcceptance),
		*Escape(PlayableSliceEvidence),
		*Escape(SliceContentPath),
		*Escape(SessionName),
		*ConfirmSpend,
		*Escape(GenerativeTextureQuality),
		*Escape(GenerativeModelVersion),
		*Escape(SessionName),
		*ConfirmSpend,
		*Escape(SliceContentPath)
	);
}

FText SMCPChatPanel::GetPlayableSlicePreviewText() const
{
	return FText::Format(
		LOCTEXT("PlayableSlicePreview", "Preview: one brief -> Smart Mesh Tripo assets -> import -> Blueprint/UMG/level build -> compile -> PIE/log/screenshot evidence. Auth: {0}. Confirmed spend: {1}."),
		IsGenerativeApiKeyConfigured() ? LOCTEXT("PlayableSliceAuthReady", "ready") : LOCTEXT("PlayableSliceAuthMissing", "missing"),
		bGenerativeSpendConfirmed ? LOCTEXT("PlayableSliceSpendYes", "yes") : LOCTEXT("PlayableSliceSpendNo", "no")
	);
}

EVisibility SMCPChatPanel::GetPlayableSliceDialogVisibility() const
{
	return bPlayableSliceDialogVisible ? EVisibility::Visible : EVisibility::Collapsed;
}

FString SMCPChatPanel::BuildGameplayBuilderPrompt() const
{
	auto Escape = [](const FString& Value) -> FString
	{
		return Value.Replace(TEXT("\""), TEXT("'"));
	};

	FString ModeLabel = TEXT("Gameplay Mechanic");
	FString OnboardingTask = TEXT("blueprints");
	FString ToolDomains = TEXT("blueprints, gameplay_framework, blueprint_graph, data_systems, diagnostics, execution_substrate");
	FString BuildDirection = TEXT("Use Blueprint/component/gameplay tools to create or modify the target feature, keep graphs named and readable, and prefer reusable Actor Components when the mechanic should attach to multiple actors.");
	if (GameplayBuilderMode == TEXT("ai"))
	{
		ModeLabel = TEXT("AI Behavior");
		OnboardingTask = TEXT("ai");
		ToolDomains = TEXT("ai_behavior_tree, gameplay_framework, editor_actor_viewport, diagnostics, execution_substrate");
		BuildDirection = TEXT("Use AI, Blackboard, Behavior Tree, navigation, and editor placement tools to create an inspectable enemy/NPC behavior loop with clear patrol/chase/attack or interaction states.");
	}
	else if (GameplayBuilderMode == TEXT("hud"))
	{
		ModeLabel = TEXT("HUD/UI");
		OnboardingTask = TEXT("umg");
		ToolDomains = TEXT("ui_umg, blueprint_graph, gameplay_framework, diagnostics, execution_substrate");
		BuildDirection = TEXT("Use UMG/widget tools and Blueprint binding/event tools to create player-facing feedback that is owned by the correct PlayerController, Pawn, or HUD flow.");
	}
	else if (GameplayBuilderMode == TEXT("level_flow"))
	{
		ModeLabel = TEXT("Level Flow");
		OnboardingTask = TEXT("world_building");
		ToolDomains = TEXT("editor_actor_viewport, procedural_world, gameplay_framework, blueprint_graph, diagnostics, execution_substrate");
		BuildDirection = TEXT("Use editor placement, actor, trigger, lighting, navigation, and Blueprint tools to create a compact playable level flow with clear start, interaction, and completion feedback.");
	}

	return FString::Printf(
		TEXT("Use the MCP Chat dock as the in-editor AI development workspace to build this %s request.\n")
		TEXT("Request parameters:\n")
		TEXT("- mode: \"%s\"\n")
		TEXT("- feature_brief: \"%s\"\n")
		TEXT("- target_reference: \"%s\"\n")
		TEXT("- acceptance_criteria: \"%s\"\n")
		TEXT("- required_evidence: \"%s\"\n")
		TEXT("Workflow:\n")
		TEXT("1. Discover current state with `get_project_context`, `scan_project_assets(path=\"/Game\", depth=2)`, `list_available_tools(domain=\"all\")`, and `get_onboarding_context(task=\"%s\")`.\n")
		TEXT("2. Identify the smallest playable change, list the assets you expect to touch, and proceed unless a destructive overwrite or missing target requires a question.\n")
		TEXT("3. Tool-domain focus: %s.\n")
		TEXT("4. Build direction: %s\n")
		TEXT("5. After mutations, run `compile_blueprint_and_report` for every touched Blueprint, save changed assets, and use diagnostic/readback tools to confirm the graph or widget state.\n")
		TEXT("6. Verify runtime with `pie_launch_session`, `pie_capture_log`, `viewport_capture_screenshot`, then `pie_stop_session` when possible.\n")
		TEXT("7. Finish with a concise report containing changed asset paths, tool results, warnings/errors, evidence paths, and what remains for human design review."),
		*ModeLabel,
		*Escape(GameplayBuilderMode),
		*Escape(GameplayBuilderBrief),
		*Escape(GameplayBuilderTarget),
		*Escape(GameplayBuilderAcceptance),
		*Escape(GameplayBuilderEvidence),
		*OnboardingTask,
		*ToolDomains,
		*BuildDirection
	);
}

FText SMCPChatPanel::GetGameplayBuilderPreviewText() const
{
	return FText::Format(
		LOCTEXT("GameplayBuilderPreview", "Preview: {0} workflow -> context/tools -> build -> compile -> PIE/log/screenshot evidence."),
		FText::FromString(GameplayBuilderMode)
	);
}

EVisibility SMCPChatPanel::GetGameplayBuilderDialogVisibility() const
{
	return bGameplayBuilderDialogVisible ? EVisibility::Visible : EVisibility::Collapsed;
}

FString SMCPChatPanel::BuildGenerateAssetToolCallPrompt() const
{
	auto Escape = [](const FString& Value) -> FString
	{
		return Value.Replace(TEXT("\""), TEXT("'"));
	};
	auto ImageArgumentName = [](const FString& Value) -> FString
	{
		return Value.StartsWith(TEXT("http"), ESearchCase::IgnoreCase) ? FString(TEXT("image_url")) : FString(TEXT("image_path"));
	};
	auto ImageObjectJson = [&Escape, &ImageArgumentName](const FString& Value) -> FString
	{
		if (Value.TrimStartAndEnd().IsEmpty())
		{
			return TEXT("{\"type\":\"image\"}");
		}
		return FString::Printf(TEXT("{\"%s\":\"%s\"}"), *ImageArgumentName(Value), *Escape(Value));
	};

	const FString SessionName = CurrentSessionName.IsEmpty() ? FString(TEXT("default")) : CurrentSessionName;
	const FString CleanAssetName = GenerateAssetName.Replace(TEXT("\""), TEXT(""));
	const FString ConfirmSpend = bGenerativeSpendConfirmed ? TEXT("true") : TEXT("false");

	if (GenerateAssetMode == TEXT("image_to_model"))
	{
		return FString::Printf(
			TEXT("Use MCP tool `gen_tripo_image_to_model` to generate a textured 3D model from a reference image, then show progress with `gen_tripo_wait_for_task` in the chat tool card.\n")
			TEXT("Parameters:\n")
			TEXT("- %s: \"%s\"\n")
			TEXT("- model_version: \"%s\"\n")
			TEXT("- texture: true\n")
			TEXT("- pbr: true\n")
			TEXT("- texture_quality: \"%s\"\n")
			TEXT("- texture_alignment: \"original_image\"\n")
			TEXT("- face_limit: 12000\n")
			TEXT("- smart_low_poly: true\n")
			TEXT("- session_name: \"%s\"\n")
			TEXT("- confirm_spend: %s\n")
			TEXT("After the task succeeds, call `gen_tripo_import_to_project` with content_path \"%s\" and asset_name \"%s\"."),
			*ImageArgumentName(GenerateAssetImageInput),
			*Escape(GenerateAssetImageInput),
			*GenerativeModelVersion,
			*GenerativeTextureQuality,
			*SessionName,
			*ConfirmSpend,
			*GenerativeOutputFolder,
			*CleanAssetName
		);
	}

	if (GenerateAssetMode == TEXT("multiview_to_model"))
	{
		const FString ImagesJson = FString::Printf(
			TEXT("[%s,%s,%s,%s]"),
			*ImageObjectJson(GenerateAssetFrontImageInput),
			*ImageObjectJson(GenerateAssetLeftImageInput),
			*ImageObjectJson(GenerateAssetBackImageInput),
			*ImageObjectJson(GenerateAssetRightImageInput)
		);
		return FString::Printf(
			TEXT("Use MCP tool `gen_tripo_multiview_to_model` to generate a textured 3D model from ordered front/left/back/right references, then show progress with `gen_tripo_wait_for_task` in the chat tool card.\n")
			TEXT("Parameters:\n")
			TEXT("- images: %s\n")
			TEXT("- model_version: \"%s\"\n")
			TEXT("- texture: true\n")
			TEXT("- pbr: true\n")
			TEXT("- texture_quality: \"%s\"\n")
			TEXT("- texture_alignment: \"original_image\"\n")
			TEXT("- face_limit: 12000\n")
			TEXT("- smart_low_poly: true\n")
			TEXT("- session_name: \"%s\"\n")
			TEXT("- confirm_spend: %s\n")
			TEXT("After the task succeeds, call `gen_tripo_import_to_project` with content_path \"%s\" and asset_name \"%s\"."),
			*ImagesJson,
			*GenerativeModelVersion,
			*GenerativeTextureQuality,
			*SessionName,
			*ConfirmSpend,
			*GenerativeOutputFolder,
			*CleanAssetName
		);
	}

	if (GenerateAssetMode == TEXT("texture_model"))
	{
		FString TexturePrompt = GenerateTexturePrompt;
		if (!GenerateTextureReferenceImageInput.TrimStartAndEnd().IsEmpty())
		{
			TexturePrompt += FString::Printf(TEXT("; use texture reference image %s as the visual style target"), *GenerateTextureReferenceImageInput);
		}
		if (!GenerateTexturePaintNotes.TrimStartAndEnd().IsEmpty())
		{
			TexturePrompt += FString::Printf(TEXT("; paint/blend notes: %s"), *GenerateTexturePaintNotes);
		}
		TexturePrompt += FString::Printf(
			TEXT("; texture edit workspace controls: generate the high-fidelity texture image from the %s mesh view, paint it onto the visible model, rotate the model as needed, use brush size %s, strength %s, hardness %s, creativity %s, paint mode %s, paint color %s, use %s, then save the satisfied result as %s"),
			*GenerateTextureViewAngle,
			*GenerateTextureBrushSize,
			*GenerateTextureBrushStrength,
			*GenerateTextureBrushHardness,
			*GenerateTextureCreativityStrength,
			*GenerateTexturePaintMode,
			*GenerateTexturePaintColor,
			*GenerateTextureBlendMode,
			*GenerateTextureSaveName
		);
		FString RenderImageForPrompt = TEXT("{}");
		if (!GenerateTextureRenderImageBucket.TrimStartAndEnd().IsEmpty() && !GenerateTextureRenderImageKey.TrimStartAndEnd().IsEmpty())
		{
			RenderImageForPrompt = FString::Printf(
				TEXT("{\"bucket\":\"%s\",\"key\":\"%s\"}"),
				*Escape(GenerateTextureRenderImageBucket),
				*Escape(GenerateTextureRenderImageKey)
			);
		}
		else if (!GenerateTextureRenderImageUrl.TrimStartAndEnd().IsEmpty())
		{
			RenderImageForPrompt = FString::Printf(TEXT("{\"url\":\"%s\"}"), *Escape(GenerateTextureRenderImageUrl));
		}
		const FString CameraMatrixForPrompt = GenerateTextureCameraMatrix.TrimStartAndEnd().IsEmpty()
			? FString(TEXT("[]"))
			: GenerateTextureCameraMatrix.TrimStartAndEnd();
		const FString ImageMapForPrompt = GenerateTextureImageMapJson.TrimStartAndEnd().IsEmpty()
			? FString(TEXT("[]"))
			: GenerateTextureImageMapJson.TrimStartAndEnd();
		return FString::Printf(
			TEXT("First use MCP tool `gen_prepare_texture_paint_session` to record the no-spend Tripo Studio Magic Brush plan for the Texture/Paint workspace.\n")
			TEXT("Plan parameters:\n")
			TEXT("- model_task_id: \"%s\"\n")
			TEXT("- texture_prompt: \"%s\"\n")
			TEXT("- texture_reference_image: \"%s\"\n")
			TEXT("- viewport_view: \"%s\"\n")
			TEXT("- render_image_bucket: \"%s\"\n")
			TEXT("- render_image_key: \"%s\"\n")
			TEXT("- render_image_url: \"%s\"\n")
			TEXT("- render_image: %s\n")
			TEXT("- camera_matrix: %s\n")
			TEXT("- brush_size: %s\n")
			TEXT("- brush_strength: %s\n")
			TEXT("- brush_hardness: %s\n")
			TEXT("- creativity_strength: %s\n")
			TEXT("- paint_mode: \"%s\"\n")
			TEXT("- paint_color: \"%s\"\n")
			TEXT("- blend_mode: \"%s\"\n")
			TEXT("- paint_notes: \"%s\"\n")
			TEXT("- save_name: \"%s\"\n")
			TEXT("- tripo_project_id: \"%s\"\n")
			TEXT("- image_map: %s\n")
			TEXT("- record_session: true\n")
			TEXT("Then, only after spend approval, run the Studio Magic Brush sequence when a Tripo project_id and render snapshot are available:\n")
			TEXT("1. Use MCP tool `gen_tripo_magic_brush_generate` with project_id, prompt, render_image, camera_matrix, strength, and confirm_spend.\n")
			TEXT("2. Use MCP tool `gen_tripo_magic_brush_get_retexture` with the returned draft_id to inspect the generated texture image.\n")
			TEXT("3. Optionally use MCP tool `gen_tripo_magic_brush_list_images` for the project texture image history before painting.\n")
			TEXT("4. After the user paints/blends and image_map contains painted regions, use MCP tool `gen_tripo_magic_brush_apply` with project_id, draft_id, image_map, and confirm_spend.\n")
			TEXT("Studio Magic Brush parameters:\n")
			TEXT("- project_id: \"%s\"\n")
			TEXT("- prompt: \"%s\"\n")
			TEXT("- render_image: %s\n")
			TEXT("- camera_matrix: %s\n")
			TEXT("- strength: %s\n")
			TEXT("- image_map: %s\n")
			TEXT("- confirm_spend: %s\n")
			TEXT("If Studio project/snapshot/image_map data is missing, use public fallback MCP tool `gen_tripo_texture_model` to create the paid texture/paint pass for the existing Tripo model task, then show progress with `gen_tripo_wait_for_task` in the chat tool card.\n")
			TEXT("Paid texture parameters:\n")
			TEXT("- task_id: \"%s\"\n")
			TEXT("- texture_prompt: \"%s\"\n")
			TEXT("- model_version: \"v3.0-20250812\"\n")
			TEXT("- texture: true\n")
			TEXT("- pbr: true\n")
			TEXT("- texture_quality: \"%s\"\n")
			TEXT("- texture_alignment: \"original_image\"\n")
			TEXT("- session_name: \"%s\"\n")
			TEXT("- confirm_spend: %s\n")
			TEXT("After the task succeeds, call `gen_tripo_import_to_project` with content_path \"%s\" and asset_name \"%s\"."),
			*Escape(GenerateTextureTaskId),
			*Escape(GenerateTexturePrompt),
			*Escape(GenerateTextureReferenceImageInput),
			*Escape(GenerateTextureViewAngle),
			*Escape(GenerateTextureRenderImageBucket),
			*Escape(GenerateTextureRenderImageKey),
			*Escape(GenerateTextureRenderImageUrl),
			*RenderImageForPrompt,
			*CameraMatrixForPrompt,
			*Escape(GenerateTextureBrushSize),
			*Escape(GenerateTextureBrushStrength),
			*Escape(GenerateTextureBrushHardness),
			*Escape(GenerateTextureCreativityStrength),
			*Escape(GenerateTexturePaintMode),
			*Escape(GenerateTexturePaintColor),
			*Escape(GenerateTextureBlendMode),
			*Escape(GenerateTexturePaintNotes),
			*Escape(GenerateTextureSaveName),
			*Escape(GenerateTextureTripoProjectId),
			*ImageMapForPrompt,
			*Escape(GenerateTextureTripoProjectId),
			*Escape(TexturePrompt),
			*RenderImageForPrompt,
			*CameraMatrixForPrompt,
			*Escape(GenerateTextureCreativityStrength),
			*ImageMapForPrompt,
			*ConfirmSpend,
			*Escape(GenerateTextureTaskId),
			*Escape(TexturePrompt),
			*GenerativeTextureQuality,
			*SessionName,
			*ConfirmSpend,
			*GenerativeOutputFolder,
			*CleanAssetName
		);
	}

	return FString::Printf(
		TEXT("Use MCP tool `gen_tripo_text_to_model` to generate an asset, then show progress with `gen_tripo_wait_for_task` in the chat tool card.\n")
		TEXT("Parameters:\n")
		TEXT("- prompt: \"%s\"\n")
		TEXT("- model_version: \"%s\"\n")
		TEXT("- texture: true\n")
		TEXT("- pbr: true\n")
		TEXT("- texture_quality: \"%s\"\n")
		TEXT("- face_limit: 12000\n")
		TEXT("- smart_low_poly: true\n")
		TEXT("- session_name: \"%s\"\n")
		TEXT("- confirm_spend: %s\n")
		TEXT("After the task succeeds, call `gen_tripo_import_to_project` with content_path \"%s\" and asset_name \"%s\"."),
		*Escape(GenerateAssetPrompt),
		*GenerativeModelVersion,
		*GenerativeTextureQuality,
		*SessionName,
		*ConfirmSpend,
		*GenerativeOutputFolder,
		*CleanAssetName
	);
}

FText SMCPChatPanel::GetGenerateAssetPreviewText() const
{
	return FText::Format(
		LOCTEXT("GenerateAssetPreview", "Preview: {0} -> gen_tripo_wait_for_task progress -> gen_tripo_import_to_project. Auth: {1}. Confirmed spend: {2}."),
		FText::FromString(GenerateAssetMode),
		IsGenerativeApiKeyConfigured() ? LOCTEXT("GenerateAssetAuthReady", "ready") : LOCTEXT("GenerateAssetAuthMissing", "missing"),
		bGenerativeSpendConfirmed ? LOCTEXT("GenerateAssetSpendYes", "yes") : LOCTEXT("GenerateAssetSpendNo", "no")
	);
}

EVisibility SMCPChatPanel::GetGenerateAssetDialogVisibility() const
{
	return bGenerateAssetDialogVisible ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SMCPChatPanel::GetGenerateTextToModelVisibility() const
{
	return GenerateAssetMode == TEXT("text_to_model") ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SMCPChatPanel::GetGenerateImageToModelVisibility() const
{
	return GenerateAssetMode == TEXT("image_to_model") ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SMCPChatPanel::GetGenerateMultiviewToModelVisibility() const
{
	return GenerateAssetMode == TEXT("multiview_to_model") ? EVisibility::Visible : EVisibility::Collapsed;
}

EVisibility SMCPChatPanel::GetGenerateTextureModelVisibility() const
{
	return GenerateAssetMode == TEXT("texture_model") ? EVisibility::Visible : EVisibility::Collapsed;
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

bool SMCPChatPanel::IsGenerativeApiKeyConfigured() const
{
	return GetGenerativeApiKeySource() != TEXT("missing");
}

void SMCPChatPanel::LoadGenerativeSettings()
{
	GenerativeModelVersion = TEXT("tripo-default");
	GenerativeTextureQuality = TEXT("standard");
	GenerativeOutputFolder = TEXT("/Game/Generated");
	GenerativeSessionCreditBudget = 1000;
	GenerativePendingSpendCredits = 0;
	GenerativeSessionCreditsUsed = 0;
	GenerativeCreditUsageBySession = MakeShared<FJsonObject>();
	GenerativeApiKey.Empty();
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
			const TSharedPtr<FJsonObject>* UsageObject = nullptr;
			if (SettingsObject->TryGetObjectField(TEXT("credit_usage_by_session"), UsageObject) && UsageObject && UsageObject->IsValid())
			{
				GenerativeCreditUsageBySession = *UsageObject;
				const FString SessionKey = CurrentSessionName.IsEmpty() ? TEXT("default") : CurrentSessionName;
				if ((*UsageObject)->TryGetNumberField(SessionKey, NumberValue) || (*UsageObject)->TryGetNumberField(TEXT("default"), NumberValue))
				{
					GenerativeSessionCreditsUsed = FMath::Max(0, FMath::RoundToInt(NumberValue));
				}
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

	if (!GenerativeApiKey.TrimStartAndEnd().IsEmpty())
	{
		const TSharedPtr<FJsonObject> SecretsObject = MakeShared<FJsonObject>();
		SecretsObject->SetStringField(TEXT("TRIPO_API_KEY"), GenerativeApiKey.TrimStartAndEnd());
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
	SettingsObject->SetStringField(TEXT("default_model_version"), GenerativeModelVersion.IsEmpty() ? TEXT("tripo-default") : GenerativeModelVersion);
	SettingsObject->SetStringField(TEXT("default_texture_quality"), GenerativeTextureQuality.IsEmpty() ? TEXT("standard") : GenerativeTextureQuality);
	SettingsObject->SetStringField(TEXT("output_folder"), GenerativeOutputFolder.StartsWith(TEXT("/Game")) ? GenerativeOutputFolder : TEXT("/Game/Generated"));
	SettingsObject->SetNumberField(TEXT("session_credit_budget"), FMath::Max(0, GenerativeSessionCreditBudget));
	SettingsObject->SetNumberField(TEXT("pending_spend_credits"), FMath::Max(0, GenerativePendingSpendCredits));
	SettingsObject->SetObjectField(TEXT("credit_usage_by_session"), GenerativeCreditUsageBySession.IsValid() ? GenerativeCreditUsageBySession : MakeShared<FJsonObject>());
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
	int32 MarkerIndex = INDEX_NONE;
	if (!Message.FindChar(TCHAR('@'), MarkerIndex))
	{
		return TEXT("");
	}

	const int32 AssetMarkerIndex = Message.Find(Marker, ESearchCase::IgnoreCase);
	if (AssetMarkerIndex == INDEX_NONE)
	{
		return TEXT("");
	}

	FString Remaining = Message.Mid(AssetMarkerIndex + Marker.Len()).TrimStartAndEnd();
	int32 EndIndex = Remaining.Len();
	for (int32 Index = 0; Index < Remaining.Len(); ++Index)
	{
		const TCHAR Char = Remaining[Index];
		if (FChar::IsWhitespace(Char) || Char == TEXT(',') || Char == TEXT(')') || Char == TEXT(']'))
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
