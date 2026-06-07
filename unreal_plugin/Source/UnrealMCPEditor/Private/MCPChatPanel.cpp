#include "MCPChatPanel.h"

#include "AssetRegistry/AssetData.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "ContentBrowserModule.h"
#include "DragAndDrop/ActorDragDropOp.h"
#include "DragAndDrop/AssetDragDropOp.h"
#include "Editor.h"
#include "Engine/World.h"
#include "Framework/Application/SlateApplication.h"
#include "Framework/Docking/TabManager.h"
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
#include "Misc/Guid.h"
#include "Misc/PackageName.h"
#include "Modules/ModuleManager.h"
#include "Serialization/JsonSerializer.h"
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
			.Orientation(Orient_Vertical)

			+ SSplitter::Slot()
			.Value(0.78f)
			[
				SNew(SBorder)
				.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
				.Padding(6.0f)
				[
					SAssignNew(MessageScrollBox, SScrollBox)
				]
			]

			+ SSplitter::Slot()
			.Value(0.22f)
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
	];

	LoadHistory();
	PollAgentMessages();
	PollTickerHandle = FTSTicker::GetCoreTicker().AddTicker(
		FTickerDelegate::CreateRaw(this, &SMCPChatPanel::HandlePollTick),
		2.0f
	);
}

SMCPChatPanel::~SMCPChatPanel()
{
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
	RebuildMessageList();
	return FReply::Handled();
}

FReply SMCPChatPanel::HandleComposerKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent)
{
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
	return DragDropEvent.GetOperation().IsValid() ? FReply::Handled() : FReply::Unhandled();
}

FReply SMCPChatPanel::OnDrop(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent)
{
	const TSharedPtr<FDragDropOperation> Operation = DragDropEvent.GetOperation();
	if (!Operation.IsValid())
	{
		return FReply::Unhandled();
	}

	InsertComposerText(BuildDropReference(Operation));
	return FReply::Handled();
}

bool SMCPChatPanel::HandlePollTick(float DeltaTime)
{
	PollAgentMessages();
	return true;
}

void SMCPChatPanel::LoadHistory()
{
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(TEXT("/chat/history?limit=50")), TEXT("GET"));
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);

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
			SetStatus(LOCTEXT("StatusConnected", "Connected"), OkStatusColor);
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
	FString Path = TEXT("/chat/poll?sender=agent");
	if (!LastAgentPollTimestamp.IsEmpty())
	{
		Path += TEXT("&since=");
		Path += FGenericPlatformHttp::UrlEncode(LastAgentPollTimestamp);
	}

	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(Path), TEXT("GET"));
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);

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
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(TEXT("/chat/send")), TEXT("POST"));

	const TSharedPtr<FJsonObject> Payload = MakeShared<FJsonObject>();
	Payload->SetStringField(TEXT("sender"), TEXT("human"));
	Payload->SetStringField(TEXT("message"), Message);
	Payload->SetStringField(TEXT("timestamp"), MakeCurrentTimestamp());
	Payload->SetObjectField(TEXT("context"), BuildEditorContext());

	FString Body;
	const TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Body);
	FJsonSerializer::Serialize(Payload.ToSharedRef(), Writer);
	Request->SetContentAsString(Body);

	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);

		if (!bWasSuccessful || !Response.IsValid() || Response->GetResponseCode() < 200 || Response->GetResponseCode() >= 300)
		{
			SetStatus(LOCTEXT("StatusSendFailed", "Send failed"), ErrorStatusColor);
			return;
		}

		SetStatus(LOCTEXT("StatusSendOk", "Connected"), OkStatusColor);
	});
	Request->ProcessRequest();
}

void SMCPChatPanel::ClearHistoryOnServer()
{
	const TSharedRef<IHttpRequest, ESPMode::ThreadSafe> Request = MakeJsonRequest(BuildServerUrl(TEXT("/chat/clear")), TEXT("POST"));
	ActiveRequests.Add(Request);
	Request->OnProcessRequestComplete().BindLambda([this](FHttpRequestPtr RequestPtr, FHttpResponsePtr Response, bool bWasSuccessful)
	{
		ActiveRequests.Remove(RequestPtr);
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
		const FString DetailText = FString::Printf(
			TEXT("Status: %s\n\nArgs summary:\n%s\n\nResult:\n%s\n\nFull detail:\n%s\n\nLog tail:\n%s"),
			*ToolCall.Status,
			*ToolCall.ArgsSummary,
			*ToolCall.ResultSummary,
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

	OutToolCall.MessageId = MessageId;
	OutToolCall.ToolName = ToolName;
	OutToolCall.ArgsSummary = ArgsSummary;
	OutToolCall.Status = Status;
	OutToolCall.ResultSummary = TruncateForCard(ResultSummary, 240);
	OutToolCall.DetailJson = JsonObjectToString(Object);
	OutToolCall.LogTail = LogTail;
	OutToolCall.bError = bError;
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

FString SMCPChatPanel::BuildDropReference(const TSharedPtr<FDragDropOperation>& Operation) const
{
	if (!Operation.IsValid())
	{
		return TEXT("");
	}

	if (Operation->IsOfType<FAssetDragDropOp>())
	{
		const TSharedPtr<FAssetDragDropOp> AssetDragDropOp = StaticCastSharedPtr<FAssetDragDropOp>(Operation);
		if (AssetDragDropOp.IsValid() && AssetDragDropOp->HasAssets())
		{
			const FAssetData& FirstAsset = AssetDragDropOp->GetAssets()[0];
			return FString::Printf(TEXT("@asset:%s"), *FirstAsset.PackageName.ToString());
		}
		if (AssetDragDropOp.IsValid() && AssetDragDropOp->HasAssetPaths())
		{
			return FString::Printf(TEXT("@asset:%s"), *AssetDragDropOp->GetAssetPaths()[0]);
		}
		return TEXT("@asset:<dropped-asset>");
	}

	if (Operation->IsOfType<FActorDragDropOp>())
	{
		const TSharedPtr<FActorDragDropOp> ActorDragDropOp = StaticCastSharedPtr<FActorDragDropOp>(Operation);
		if (ActorDragDropOp.IsValid() && ActorDragDropOp->Actors.Num() > 0 && ActorDragDropOp->Actors[0].IsValid())
		{
			return FString::Printf(TEXT("@actor:%s"), *ActorDragDropOp->Actors[0]->GetName());
		}
		return TEXT("@actor:<dropped-actor>");
	}

	if (Operation->IsExternalOperation())
	{
		return TEXT("@file:<dropped-file>");
	}

	return TEXT("@drop:slate-operation");
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
