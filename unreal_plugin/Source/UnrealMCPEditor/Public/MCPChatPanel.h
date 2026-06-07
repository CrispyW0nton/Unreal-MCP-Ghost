#pragma once

#include "CoreMinimal.h"
#include "Containers/Ticker.h"
#include "Widgets/SCompoundWidget.h"

class SScrollBox;
class SEditableTextBox;
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
		TArray<FString> ScreenshotPaths;
		TArray<FString> LogSnippets;
		TArray<FString> PieResults;
		bool bError = false;
	};

	struct FToolPaletteEntry
	{
		FString Name;
		FString Description;
		FString Category;
		TArray<FString> Parameters;
	};

	struct FChatSessionEntry
	{
		FString Name;
		FString UpdatedAt;
		int32 MessageCount = 0;
		bool bPinned = false;
	};

	struct FCommandPaletteItem
	{
		FString Label;
		FString Detail;
		FString InsertText;
		FString Kind;
	};

	FReply HandleSendClicked();
	FReply HandleClearClicked();
	FReply HandleNewSessionClicked();
	FReply HandleContinueLastSessionClicked();
	FReply HandleRenameSessionClicked();
	FReply HandlePinSessionClicked();
	FReply HandleDeleteSessionClicked();
	FReply HandleExportSessionClicked();
	FReply HandleSessionClicked(FChatSessionEntry Session);
	FReply HandleToggleToolPaletteClicked();
	FReply HandleRefreshToolPaletteClicked();
	FReply HandleToolPaletteToolClicked(FToolPaletteEntry Tool);
	FReply HandleOpenCommandPaletteClicked();
	void HandleCommandPaletteTextChanged(const FText& Text);
	FReply HandleCommandPaletteItemClicked(FCommandPaletteItem Item);
	FReply HandleToggleTelemetryClicked();
	FReply HandleComposerKeyDown(const FGeometry& MyGeometry, const FKeyEvent& InKeyEvent);
	FReply HandleCopyClicked(FString Message) const;
	FReply HandleRerunClicked(FString Message, FString Sender);
	FReply HandleOpenLogClicked();
	FReply HandleRevealAssetClicked(FString Message);
	FReply HandleToolDetailsClicked(FToolCallView ToolCall);
	FReply HandleRepairToolClicked(FToolCallView ToolCall);
	FReply HandleContextChipClicked(FString Reference);
	virtual FReply OnDragOver(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent) override;
	virtual FReply OnDrop(const FGeometry& MyGeometry, const FDragDropEvent& DragDropEvent) override;
	bool HandlePollTick(float DeltaTime);

	void LoadHistory();
	void PollAgentMessages();
	void SendHumanMessage(const FString& Message);
	void ClearHistoryOnServer();
	void LoadToolPalette();
	void LoadSessions();
	void SendSessionAction(const FString& Path, const TSharedPtr<class FJsonObject>& Payload, const FText& StatusOnSuccess);

	void LoadLayoutSettings();
	void SaveLayoutSettings() const;
	void RecordHorizontalSplitterResize(float Size, int32 SlotIndex);
	void RecordVerticalSplitterResize(float Size, int32 SlotIndex);
	void RecordServerLatency(double RequestStartSeconds);
	void RecordTelemetryEvent(const FString& EventName);
	FString GetMetricsFilePath() const;
	void AddMessage(const FChatMessage& ChatMessage);
	void RebuildMessageList();
	void RebuildToolPaletteList();
	void RebuildSessionList();
	void RefreshCommandPaletteItems();
	void RebuildCommandPaletteResults();
	void AddCommandPaletteItem(const FString& Label, const FString& Detail, const FString& InsertText, const FString& Kind);
	TSharedRef<SWidget> BuildMessageWidget(const FChatMessage& ChatMessage);
	TSharedRef<SWidget> BuildMarkdownMessageBody(const FChatMessage& ChatMessage);
	TSharedRef<SWidget> BuildToolCallCards(const FChatMessage& ChatMessage);
	TSharedRef<SWidget> BuildToolCallCard(const FToolCallView& ToolCall);
	TSharedRef<SWidget> BuildEvidencePanel(const FToolCallView& ToolCall);
	TSharedRef<SWidget> BuildScreenshotEvidenceWidget(const FString& ScreenshotPath);
	TSharedRef<SWidget> BuildSessionSidebar();
	TSharedRef<SWidget> BuildToolPalette();
	TSharedRef<SWidget> BuildToolPaletteCategory(const FString& Category, const TArray<FToolPaletteEntry>& Tools);
	TSharedRef<SWidget> BuildCommandPalette();
	TSharedRef<SWidget> BuildContextChips();
	void AddMarkdownBlocks(const FString& MarkdownText, const FString& MessageId, TSharedRef<SVerticalBox> BodyBox);
	void AppendStreamingDelta(const FString& MessageId, const FString& Sender, const FString& Delta, bool bDone);
	bool ApplySseLine(const FString& Line);
	void InsertComposerText(const FString& Text);
	void ShowToolDetailDrawer(const FToolCallView& ToolCall);
	void SetStatus(const FText& Text, const FSlateColor& Color);
	void UpdateLastAgentTimestamp(const TArray<FChatMessage>& Messages);

	void ExtractToolCallsFromMessage(const FChatMessage& ChatMessage, TArray<FToolCallView>& OutToolCalls) const;
	void ExtractEvidenceFromJsonObject(const TSharedPtr<class FJsonObject>& Object, FToolCallView& OutToolCall) const;
	void ExtractEvidenceFromJsonValue(const FString& FieldName, const TSharedPtr<class FJsonValue>& Value, FToolCallView& OutToolCall) const;
	void UpdateLastCompileStateFromMessage(const FChatMessage& ChatMessage);
	bool TryBuildToolCallFromJsonObject(const TSharedPtr<class FJsonObject>& Object, const FString& MessageId, FToolCallView& OutToolCall) const;
	FString JsonObjectToString(const TSharedPtr<class FJsonObject>& Object) const;
	FString JsonValueToString(const TSharedPtr<class FJsonValue>& Value) const;
	FString SummarizeJsonObject(const TSharedPtr<class FJsonObject>& Object, int32 MaxChars = 180) const;
	FString SummarizeJsonValue(const TSharedPtr<class FJsonValue>& Value, int32 MaxChars = 180) const;
	FString TruncateForCard(const FString& Text, int32 MaxChars = 180) const;
	FText GetOpenLevelChipText() const;
	FText GetSelectedActorChipText() const;
	FText GetDirtyAssetsChipText() const;
	FText GetLastCompileChipText() const;
	FText GetServerChipText() const;
	FString GetOpenLevelReference() const;
	FString GetSelectedActorReference() const;
	FString GetDirtyAssetsReference() const;
	FString GetLastCompileReference() const;
	FString GetServerReference() const;
	FString GetOpenLevelName() const;
	FString GetSelectedActorName() const;
	int32 CountDirtyPackages() const;
	FString MakeLocalMessageId() const;
	FString NormaliseSender(const FString& Sender) const;
	FText GetSenderLabel(const FString& Sender) const;
	FSlateColor GetMessageColor(const FString& Sender) const;
	EVisibility GetToolPaletteVisibility() const;
	EVisibility GetCommandPaletteVisibility() const;
	FText GetToolPaletteToggleText() const;
	FText GetStatusFooterText() const;
	FText GetTelemetryToggleText() const;
	FString BuildSessionQueryParam() const;
	FString BuildNewSessionName() const;
	FString BuildRenamedSessionName() const;
	FString BuildToolPromptTemplate(const FToolPaletteEntry& Tool) const;
	bool CommandPaletteItemMatches(const FString& Filter, const FCommandPaletteItem& Item) const;
	bool ParseSessionsResponse(const FString& JsonText, TArray<FChatSessionEntry>& OutSessions, FString& OutLastSession) const;
	bool ParseToolPaletteResponse(const FString& JsonText, TMap<FString, TArray<FToolPaletteEntry>>& OutToolsByCategory) const;
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
	FString LastCompileStatus = TEXT("unknown");
	FString ServerBaseUrl = TEXT("http://127.0.0.1:8000");
	FString CurrentSessionName = TEXT("default");
	FString LastSessionName = TEXT("default");
	bool bToolPaletteVisible = true;
	bool bToolPaletteLoaded = false;
	bool bCommandPaletteVisible = false;
	bool bTelemetryEnabled = false;
	FString CommandPaletteFilter;
	float SessionSidebarSize = 0.18f;
	float ToolPaletteSize = 0.22f;
	float ChatWorkspaceSize = 0.60f;
	float ConversationSize = 0.78f;
	float ComposerSize = 0.22f;
	int32 LastServerLatencyMs = 0;
	int32 ToolCount = 0;
	int32 KbDocCount = 5;
	int32 TelemetryEventCount = 0;
	TMap<FString, TArray<FToolPaletteEntry>> ToolPaletteByCategory;
	TArray<FChatSessionEntry> ChatSessions;
	TArray<FCommandPaletteItem> CommandPaletteItems;

	TSharedPtr<SVerticalBox> SessionList;
	TSharedPtr<SVerticalBox> ToolPaletteList;
	TSharedPtr<SVerticalBox> CommandPaletteResults;
	TSharedPtr<SScrollBox> MessageScrollBox;
	TSharedPtr<SEditableTextBox> CommandPaletteInput;
	TSharedPtr<SMultiLineEditableTextBox> MessageInput;
	TSharedPtr<STextBlock> StatusText;
	TSharedPtr<SVerticalBox> ToolDetailDrawer;
	TSharedPtr<STextBlock> ToolDetailTitle;
	TSharedPtr<STextBlock> ToolDetailBody;
	TMap<FString, TSharedPtr<STextBlock>> StreamingMessageTextBlocks;
	TArray<TSharedPtr<struct FSlateDynamicImageBrush>> EvidenceImageBrushes;

	FTSTicker::FDelegateHandle PollTickerHandle;
};
