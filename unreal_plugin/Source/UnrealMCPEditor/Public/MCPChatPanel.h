#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Widgets/SCompoundWidget.h"

class SScrollBox;
class SMultiLineEditableTextBox;
class STextBlock;

class SMCPChatPanel : public SCompoundWidget
{
public:
	SLATE_BEGIN_ARGS(SMCPChatPanel) {}
	SLATE_END_ARGS()

	void Construct(const FArguments& InArgs);
	virtual ~SMCPChatPanel() override;

private:
	struct FChatMessage
	{
		FString MessageId;
		FString Sender;
		FString Message;
		FString Timestamp;
	};

	FReply HandleSendClicked();
	FReply HandleClearClicked();
	bool HandlePollTick(float DeltaTime);

	void LoadHistory();
	void PollAgentMessages();
	void SendHumanMessage(const FString& Message);
	void ClearHistoryOnServer();

	void AddMessage(const FChatMessage& ChatMessage);
	void RebuildMessageList();
	void SetStatus(const FText& Text, const FSlateColor& Color);
	void UpdateLastAgentTimestamp(const TArray<FChatMessage>& Messages);

	FString BuildServerUrl(const FString& PathAndQuery) const;
	FString MakeCurrentTimestamp() const;
	TSharedRef<class IHttpRequest, ESPMode::ThreadSafe> MakeJsonRequest(const FString& Url, const FString& Verb) const;
	TSharedPtr<class FJsonObject> BuildEditorContext() const;
	bool ParseMessagesResponse(const FString& JsonText, TArray<FChatMessage>& OutMessages) const;

	TArray<FChatMessage> Messages;
	TArray<TSharedPtr<class IHttpRequest, ESPMode::ThreadSafe>> ActiveRequests;
	FString LastAgentPollTimestamp;
	FString ServerBaseUrl = TEXT("http://127.0.0.1:8000");

	TSharedPtr<SScrollBox> MessageScrollBox;
	TSharedPtr<SMultiLineEditableTextBox> MessageInput;
	TSharedPtr<STextBlock> StatusText;

	FTSTicker::FDelegateHandle PollTickerHandle;
};
