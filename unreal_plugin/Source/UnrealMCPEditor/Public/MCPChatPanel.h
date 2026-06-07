#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Widgets/SCompoundWidget.h"

class SScrollBox;
class SMultiLineEditableTextBox;
class STextBlock;
class SVerticalBox;

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

	struct FToolCallView
	{
		FString MessageId;
		FString ToolName;
		FString ArgsSummary;
		FString Status;
		FString ResultSummary;
		FString DetailJson;
		FString LogTail;
		bool bError = false;
	};

	FReply HandleSendClicked();
	FReply HandleClearClicked();
	FReply HandleComposerKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent);
	FReply HandleCopyClicked(FString Message) const;
	FReply HandleRerunClicked(FString Message, FString Sender);
	FReply HandleOpenLogClicked();
	FReply HandleRevealAssetClicked(FString Message);
	FReply HandleToolDetailsClicked(FToolCallView ToolCall);
	FReply HandleRepairToolClicked(FToolCallView ToolCall);
	virtual FReply OnDragOver(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent) override;
	virtual FReply OnDrop(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent) override;
	bool HandlePollTick(float DeltaTime);

	void LoadHistory();
	void PollAgentMessages();
	void SendHumanMessage(const FString& Message);
	void ClearHistoryOnServer();

	void AddMessage(const FChatMessage& ChatMessage);
	void RebuildMessageList();
	TSharedRef<SWidget> BuildMessageWidget(const FChatMessage& ChatMessage);
	TSharedRef<SWidget> BuildMarkdownMessageBody(const FChatMessage& ChatMessage);
	TSharedRef<SWidget> BuildToolCallCards(const FChatMessage& ChatMessage);
	TSharedRef<SWidget> BuildToolCallCard(const FToolCallView& ToolCall);
	void AddMarkdownBlocks(const FString& MarkdownText, const FString& MessageId, TSharedRef<SVerticalBox> BodyBox);
	void AppendStreamingDelta(const FString& MessageId, const FString& Sender, const FString& Delta, bool bDone);
	bool ApplySseLine(const FString& Line);
	void InsertComposerText(const FString& Text);
	void ShowToolDetailDrawer(const FToolCallView& ToolCall);
	void SetStatus(const FText& Text, const FSlateColor& Color);
	void UpdateLastAgentTimestamp(const TArray<FChatMessage>& Messages);

	void ExtractToolCallsFromMessage(const FChatMessage& ChatMessage, TArray<FToolCallView>& OutToolCalls) const;
	bool TryBuildToolCallFromJsonObject(const TSharedPtr<class FJsonObject>& Object, const FString& MessageId, FToolCallView& OutToolCall) const;
	FString JsonObjectToString(const TSharedPtr<class FJsonObject>& Object) const;
	FString JsonValueToString(const TSharedPtr<class FJsonValue>& Value) const;
	FString SummarizeJsonObject(const TSharedPtr<class FJsonObject>& Object, int32 MaxChars = 180) const;
	FString SummarizeJsonValue(const TSharedPtr<class FJsonValue>& Value, int32 MaxChars = 180) const;
	FString TruncateForCard(const FString& Text, int32 MaxChars = 180) const;
	FString MakeLocalMessageId() const;
	FString NormaliseSender(const FString& Sender) const;
	FText GetSenderLabel(const FString& Sender) const;
	FSlateColor GetMessageColor(const FString& Sender) const;
	FString BuildDropReference(const TSharedPtr<class FDragDropOperation>& Operation) const;
	FString ExtractFirstAssetReference(const FString& Message) const;
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
	TSharedPtr<SVerticalBox> ToolDetailDrawer;
	TSharedPtr<STextBlock> ToolDetailTitle;
	TSharedPtr<STextBlock> ToolDetailBody;
	TMap<FString, TSharedPtr<STextBlock>> StreamingMessageTextBlocks;

	FTSTicker::FDelegateHandle PollTickerHandle;
};
