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
		FString EvidenceReadinessSummary;
		TArray<FString> ScreenshotPaths;
		TArray<FString> LogSnippets;
		TArray<FString> PieResults;
		TArray<FString> ProofGateSummaries;
		float ProgressFraction = 0.0f;
		bool bHasProgress = false;
		bool bHasEvidenceReadiness = false;
		bool bLivePlayableSliceProven = false;
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

	struct FSamplePromptItem
	{
		FString Label;
		FString Prompt;
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
	FReply HandleOpenPlayableSliceClicked();
	FReply HandleInsertPlayableSlicePreflightPromptClicked();
	FReply HandleInsertPlayableSlicePromptClicked();
	FReply HandleOpenGameplayBuilderClicked();
	FReply HandleInsertGameplayBuilderPromptClicked();
	FReply HandleGameplayModeMechanicClicked();
	FReply HandleGameplayModeAIClicked();
	FReply HandleGameplayModeHudClicked();
	FReply HandleGameplayModeLevelFlowClicked();
	FReply HandleOpenGenerateAssetClicked();
	FReply HandleInsertGenerateAssetToolCallClicked();
	FReply HandleGenerateModeTextToModelClicked();
	FReply HandleGenerateModeImageToModelClicked();
	FReply HandleGenerateModeMultiviewToModelClicked();
	FReply HandleGenerateModeTextureModelClicked();
	FReply HandleToggleGenerativeSettingsClicked();
	FReply HandleSaveGenerativeSettingsClicked();
	FReply HandleClearGenerativeApiKeyClicked();
	FReply HandleConfirmGenerativeSpendClicked();
	FReply HandleOnboardingNextClicked();
	FReply HandleOnboardingDismissClicked();
	FReply HandleToggleSamplePromptsClicked();
	FReply HandleSamplePromptClicked(FSamplePromptItem Item);
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
	TArray<FSamplePromptItem> GetSamplePromptItems() const;
	TSharedRef<SWidget> BuildMessageWidget(const FChatMessage& ChatMessage);
	TSharedRef<SWidget> BuildMarkdownMessageBody(const FChatMessage& ChatMessage);
	TSharedRef<SWidget> BuildToolCallCards(const FChatMessage& ChatMessage);
	TSharedRef<SWidget> BuildToolCallCard(const FToolCallView& ToolCall);
	TSharedRef<SWidget> BuildTripoProgressPanel(const FToolCallView& ToolCall);
	TSharedRef<SWidget> BuildEvidencePanel(const FToolCallView& ToolCall);
	TSharedRef<SWidget> BuildScreenshotEvidenceWidget(const FString& ScreenshotPath);
	TSharedRef<SWidget> BuildSessionSidebar();
	TSharedRef<SWidget> BuildToolPalette();
	TSharedRef<SWidget> BuildToolPaletteCategory(const FString& Category, const TArray<FToolPaletteEntry>& Tools);
	TSharedRef<SWidget> BuildCommandPalette();
	TSharedRef<SWidget> BuildPlayableSliceDialog();
	TSharedRef<SWidget> BuildGameplayBuilderDialog();
	TSharedRef<SWidget> BuildGenerateAssetDialog();
	TSharedRef<SWidget> BuildGenerativeSettingsPanel();
	TSharedRef<SWidget> BuildOnboardingOverlay();
	TSharedRef<SWidget> BuildSamplePrompts();
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
	void ExtractEvidenceReadinessFromJsonObject(const TSharedPtr<class FJsonObject>& Object, FToolCallView& OutToolCall) const;
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
	EVisibility GetGenerativeSettingsVisibility() const;
	EVisibility GetOnboardingVisibility() const;
	EVisibility GetSamplePromptsVisibility() const;
	FText GetToolPaletteToggleText() const;
	FText GetGenerativeSettingsToggleText() const;
	FText GetGenerativeAuthStatusText() const;
	FText GetGenerativeBudgetText() const;
	FText GetGenerativeCreditsDisplayText() const;
	FText GetOnboardingStepText() const;
	FText GetOnboardingStepTitle() const;
	FText GetOnboardingNextText() const;
	FText GetSamplePromptsToggleText() const;
	FText GetStatusFooterText() const;
	FText GetTelemetryToggleText() const;
	FString BuildSessionQueryParam() const;
	FString BuildNewSessionName() const;
	FString BuildRenamedSessionName() const;
	FString BuildToolPromptTemplate(const FToolPaletteEntry& Tool) const;
	FString BuildPlayableSlicePrompt() const;
	FString BuildPlayableSlicePreflightPrompt() const;
	FText GetPlayableSlicePreviewText() const;
	FText GetPlayableSlicePreflightStatusText() const;
	EVisibility GetPlayableSliceDialogVisibility() const;
	FString BuildGameplayBuilderPrompt() const;
	FText GetGameplayBuilderPreviewText() const;
	EVisibility GetGameplayBuilderDialogVisibility() const;
	FString BuildGenerateAssetToolCallPrompt() const;
	FText GetGenerateAssetPreviewText() const;
	EVisibility GetGenerateAssetDialogVisibility() const;
	EVisibility GetGenerateTextToModelVisibility() const;
	EVisibility GetGenerateImageToModelVisibility() const;
	EVisibility GetGenerateMultiviewToModelVisibility() const;
	EVisibility GetGenerateTextureModelVisibility() const;
	FString GetGenerativeSettingsFilePath() const;
	FString GetGenerativeSecretsFilePath() const;
	FString GetGenerativeApiKeySource() const;
	bool IsGenerativeApiKeyConfigured() const;
	void LoadGenerativeSettings();
	void SaveGenerativeSettingsToDisk() const;
	TSharedPtr<class FJsonObject> BuildGenerativeSettingsJson() const;
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
	bool bPlayableSliceDialogVisible = false;
	bool bGameplayBuilderDialogVisible = false;
	bool bGenerateAssetDialogVisible = false;
	bool bGenerativeSettingsVisible = false;
	bool bGenerativeSpendConfirmed = false;
	bool bTelemetryEnabled = false;
	bool bOnboardingVisible = false;
	bool bOnboardingCompleted = false;
	bool bSamplePromptsVisible = false;
	FString CommandPaletteFilter;
	int32 OnboardingStepIndex = 0;
	float SessionSidebarSize = 0.18f;
	float ToolPaletteSize = 0.22f;
	float ChatWorkspaceSize = 0.60f;
	float ConversationSize = 0.78f;
	float ComposerSize = 0.22f;
	int32 LastServerLatencyMs = 0;
	int32 ToolCount = 0;
	int32 KbDocCount = 5;
	int32 TelemetryEventCount = 0;
	int32 GenerativeSessionCreditBudget = 1000;
	int32 GenerativePendingSpendCredits = 0;
	int32 GenerativeSessionCreditsUsed = 0;
	TSharedPtr<class FJsonObject> GenerativeCreditUsageBySession;
	FString GenerativeApiKey;
	FString GenerativeModelVersion = TEXT("tripo-default");
	FString GenerativeTextureQuality = TEXT("standard");
	FString GenerativeOutputFolder = TEXT("/Game/Generated");
	FString PlayableSliceBrief = TEXT("make a tiny playable arena where the player collects a generated power core and opens an exit gate");
	FString PlayableSliceAssetRoles = TEXT("power core pickup, exit gate, arena marker prop");
	FString PlayableSliceGameplayLoop = TEXT("spawn player, collect generated pickup, trigger feedback, open gate, show completion HUD");
	FString PlayableSliceAcceptance = TEXT("generated assets imported, Blueprint gameplay compiled, PIE smoke passes, screenshot evidence captured");
	FString PlayableSliceEvidence = TEXT("Tripo task ids, imported asset paths, compile reports, PIE log, viewport screenshot");
	FString GameplayBuilderMode = TEXT("mechanic");
	FString GameplayBuilderBrief = TEXT("add an interactable pickup that restores health and gives clear player feedback");
	FString GameplayBuilderTarget = TEXT("@selected");
	FString GameplayBuilderAcceptance = TEXT("compile touched Blueprints, run PIE/log smoke, capture screenshot evidence, and list changed assets");
	FString GameplayBuilderEvidence = TEXT("PIE log plus viewport screenshot");
	FString GenerateAssetMode = TEXT("text_to_model");
	FString GenerateAssetPrompt = TEXT("stylized slime enemy, game-ready proportions, clean silhouette, PBR textures");
	FString GenerateAssetName = TEXT("SM_GeneratedAsset");
	FString GenerateAssetImageInput;
	FString GenerateAssetFrontImageInput;
	FString GenerateAssetLeftImageInput;
	FString GenerateAssetBackImageInput;
	FString GenerateAssetRightImageInput;
	FString GenerateTextureTaskId;
	FString GenerateTexturePrompt = TEXT("gaussian-splatting inspired painterly PBR surface detail");
	FString GenerateTextureReferenceImageInput;
	FString GenerateTexturePaintNotes = TEXT("blend the generated texture across seams and preserve readable game-material detail");
	FString GenerateTextureViewAngle = TEXT("current viewport/front");
	FString GenerateTextureBrushSize = TEXT("0.03");
	FString GenerateTextureBrushStrength = TEXT("0.65");
	FString GenerateTextureBrushHardness = TEXT("0.35");
	FString GenerateTextureCreativityStrength = TEXT("0.6");
	FString GenerateTexturePaintMode = TEXT("image");
	FString GenerateTexturePaintColor = TEXT("#FFFFFF");
	FString GenerateTextureBlendMode = TEXT("soft blend");
	FString GenerateTextureSaveName = TEXT("MI_GeneratedPaintedTexture");
	FString GenerateTextureTripoProjectId;
	FString GenerateTextureRenderImageBucket;
	FString GenerateTextureRenderImageKey;
	FString GenerateTextureRenderImageUrl;
	FString GenerateTextureCameraMatrix;
	FString GenerateTextureImageMapJson = TEXT("[]");
	TMap<FString, TArray<FToolPaletteEntry>> ToolPaletteByCategory;
	TArray<FChatSessionEntry> ChatSessions;
	TArray<FCommandPaletteItem> CommandPaletteItems;

	TSharedPtr<SVerticalBox> SessionList;
	TSharedPtr<SVerticalBox> ToolPaletteList;
	TSharedPtr<SVerticalBox> CommandPaletteResults;
	TSharedPtr<SScrollBox> MessageScrollBox;
	TSharedPtr<SEditableTextBox> GenerativeApiKeyInput;
	TSharedPtr<SEditableTextBox> GenerativeModelVersionInput;
	TSharedPtr<SEditableTextBox> GenerativeTextureQualityInput;
	TSharedPtr<SEditableTextBox> GenerativeOutputFolderInput;
	TSharedPtr<SEditableTextBox> GenerativeCreditBudgetInput;
	TSharedPtr<SEditableTextBox> GenerativePendingSpendInput;
	TSharedPtr<SEditableTextBox> PlayableSliceBriefInput;
	TSharedPtr<SEditableTextBox> PlayableSliceAssetRolesInput;
	TSharedPtr<SEditableTextBox> PlayableSliceGameplayLoopInput;
	TSharedPtr<SEditableTextBox> PlayableSliceAcceptanceInput;
	TSharedPtr<SEditableTextBox> PlayableSliceEvidenceInput;
	TSharedPtr<SEditableTextBox> GameplayBuilderBriefInput;
	TSharedPtr<SEditableTextBox> GameplayBuilderTargetInput;
	TSharedPtr<SEditableTextBox> GameplayBuilderAcceptanceInput;
	TSharedPtr<SEditableTextBox> GameplayBuilderEvidenceInput;
	TSharedPtr<SEditableTextBox> GenerateAssetPromptInput;
	TSharedPtr<SEditableTextBox> GenerateAssetNameInput;
	TSharedPtr<SEditableTextBox> GenerateAssetImageInputBox;
	TSharedPtr<SEditableTextBox> GenerateAssetFrontImageInputBox;
	TSharedPtr<SEditableTextBox> GenerateAssetLeftImageInputBox;
	TSharedPtr<SEditableTextBox> GenerateAssetBackImageInputBox;
	TSharedPtr<SEditableTextBox> GenerateAssetRightImageInputBox;
	TSharedPtr<SEditableTextBox> GenerateTextureTaskIdInput;
	TSharedPtr<SEditableTextBox> GenerateTexturePromptInput;
	TSharedPtr<SEditableTextBox> GenerateTextureReferenceImageInputBox;
	TSharedPtr<SEditableTextBox> GenerateTexturePaintNotesInput;
	TSharedPtr<SEditableTextBox> GenerateTextureViewAngleInput;
	TSharedPtr<SEditableTextBox> GenerateTextureBrushSizeInput;
	TSharedPtr<SEditableTextBox> GenerateTextureBrushStrengthInput;
	TSharedPtr<SEditableTextBox> GenerateTextureBrushHardnessInput;
	TSharedPtr<SEditableTextBox> GenerateTextureCreativityStrengthInput;
	TSharedPtr<SEditableTextBox> GenerateTexturePaintModeInput;
	TSharedPtr<SEditableTextBox> GenerateTexturePaintColorInput;
	TSharedPtr<SEditableTextBox> GenerateTextureBlendModeInput;
	TSharedPtr<SEditableTextBox> GenerateTextureSaveNameInput;
	TSharedPtr<SEditableTextBox> GenerateTextureTripoProjectIdInput;
	TSharedPtr<SEditableTextBox> GenerateTextureRenderImageBucketInput;
	TSharedPtr<SEditableTextBox> GenerateTextureRenderImageKeyInput;
	TSharedPtr<SEditableTextBox> GenerateTextureRenderImageUrlInput;
	TSharedPtr<SEditableTextBox> GenerateTextureCameraMatrixInput;
	TSharedPtr<SEditableTextBox> GenerateTextureImageMapJsonInput;
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
