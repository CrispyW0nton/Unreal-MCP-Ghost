#include "MCPChatPanel.h"

#include "Editor.h"
#include "Engine/World.h"
#include "HttpModule.h"
#include "Interfaces/IHttpRequest.h"
#include "Interfaces/IHttpResponse.h"
#include "Dom/JsonObject.h"
#include "GameFramework/Actor.h"
#include "GenericPlatform/GenericPlatformHttp.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"
#include "Selection.h"
#include "Styling/AppStyle.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SMultiLineEditableTextBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSeparator.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Text/STextBlock.h"

#define LOCTEXT_NAMESPACE "SMCPChatPanel"

namespace
{
	const FSlateColor HumanMessageColor(FLinearColor(0.12f, 0.30f, 0.55f, 1.0f));
	const FSlateColor AgentMessageColor(FLinearColor(0.12f, 0.42f, 0.22f, 1.0f));
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
		.FillHeight(1.0f)
		.Padding(8.0f, 4.0f)
		[
			SNew(SBorder)
			.BorderImage(FAppStyle::GetBrush("Brushes.Recessed"))
			.Padding(6.0f)
			[
				SAssignNew(MessageScrollBox, SScrollBox)
			]
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f, 4.0f)
		[
			SNew(SSeparator)
		]

		+ SVerticalBox::Slot()
		.AutoHeight()
		.Padding(8.0f)
		[
			SNew(SHorizontalBox)

			+ SHorizontalBox::Slot()
			.FillWidth(1.0f)
			.MinWidth(300.0f)
			[
				SNew(SBox)
				.MinDesiredHeight(72.0f)
				[
					SAssignNew(MessageInput, SMultiLineEditableTextBox)
					.HintText(LOCTEXT("InputHint", "Type a message for Cursor..."))
					.AutoWrapText(true)
				]
			]

			+ SHorizontalBox::Slot()
			.AutoWidth()
			.VAlign(VAlign_Bottom)
			.Padding(8.0f, 0.0f, 0.0f, 0.0f)
			[
				SNew(SButton)
				.Text(LOCTEXT("Send", "Send"))
				.OnClicked(this, &SMCPChatPanel::HandleSendClicked)
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
	AddMessage(FChatMessage{TEXT(""), TEXT("human"), Text, MakeCurrentTimestamp()});

	return FReply::Handled();
}

FReply SMCPChatPanel::HandleClearClicked()
{
	ClearHistoryOnServer();
	Messages.Reset();
	RebuildMessageList();
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

		TArray<FChatMessage> NewMessages;
		if (!ParseMessagesResponse(Response->GetContentAsString(), NewMessages))
		{
			SetStatus(LOCTEXT("StatusPollParseError", "Poll parse failed"), ErrorStatusColor);
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
	if (!ChatMessage.MessageId.IsEmpty())
	{
		for (const FChatMessage& Existing : Messages)
		{
			if (Existing.MessageId == ChatMessage.MessageId)
			{
				return;
			}
		}
	}

	Messages.Add(ChatMessage);

	if (!MessageScrollBox.IsValid())
	{
		return;
	}

	const bool bHuman = ChatMessage.Sender.Equals(TEXT("human"), ESearchCase::IgnoreCase);
	const FSlateColor MessageColor = bHuman ? HumanMessageColor : AgentMessageColor;
	const FText SenderLabel = bHuman ? LOCTEXT("HumanSender", "You") : LOCTEXT("AgentSender", "Cursor");

	MessageScrollBox->AddSlot()
	.Padding(0.0f, 0.0f, 0.0f, 6.0f)
	[
		SNew(SBorder)
		.BorderImage(FAppStyle::GetBrush("Brushes.Panel"))
		.BorderBackgroundColor(MessageColor)
		.Padding(8.0f)
		[
			SNew(SVerticalBox)

			+ SVerticalBox::Slot()
			.AutoHeight()
			[
				SNew(STextBlock)
				.Text(FText::Format(LOCTEXT("MessageHeader", "{0}  {1}"), SenderLabel, FText::FromString(ChatMessage.Timestamp)))
				.Font(FAppStyle::GetFontStyle("SmallFontBold"))
			]

			+ SVerticalBox::Slot()
			.AutoHeight()
			.Padding(0.0f, 4.0f, 0.0f, 0.0f)
			[
				SNew(STextBlock)
				.Text(FText::FromString(ChatMessage.Message))
				.AutoWrapText(true)
			]
		]
	];

	MessageScrollBox->ScrollToEnd();
}

void SMCPChatPanel::RebuildMessageList()
{
	if (!MessageScrollBox.IsValid())
	{
		return;
	}

	const TArray<FChatMessage> ExistingMessages = Messages;
	Messages.Reset();
	MessageScrollBox->ClearChildren();

	for (const FChatMessage& ChatMessage : ExistingMessages)
	{
		AddMessage(ChatMessage);
	}
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
