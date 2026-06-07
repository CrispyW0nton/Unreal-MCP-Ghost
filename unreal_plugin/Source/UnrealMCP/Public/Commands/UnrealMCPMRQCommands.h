#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
#include "Templates/SubclassOf.h"

class UMoviePipelineExecutorJob;
class UMoviePipelinePrimaryConfig;
class UMoviePipelineQueue;
class UMoviePipelineQueueSubsystem;
class UMoviePipelineSetting;

/**
 * B.11 Movie Render Queue command handler.
 */
class UNREALMCP_API FUnrealMCPMRQCommands
{
public:
    FUnrealMCPMRQCommands();

    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    TSharedPtr<FJsonObject> HandleCreateJob(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddRenderSetting(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleRenderQueue(const TSharedPtr<FJsonObject>& Params);

    UMoviePipelineQueueSubsystem* GetQueueSubsystem() const;
    UMoviePipelineExecutorJob* FindJob(UMoviePipelineQueue* Queue, const FString& JobName) const;
    FString NormalizeObjectPath(const FString& AssetOrObjectPath) const;
    FString GetDefaultMapPath() const;
    TSubclassOf<UMoviePipelineSetting> GetImageOutputClass(const FString& ImageFormat) const;
    TSharedPtr<FJsonObject> MakeQueueResult(const FString& StageName, UMoviePipelineQueue* Queue, UMoviePipelineExecutorJob* FocusJob = nullptr) const;
    TSharedPtr<FJsonObject> MakeJobSummary(UMoviePipelineExecutorJob* Job) const;
    TArray<TSharedPtr<FJsonValue>> MakeSettingsSummary(UMoviePipelinePrimaryConfig* Config) const;
    FIntPoint GetResolutionField(const TSharedPtr<FJsonObject>& Params, const FIntPoint& DefaultValue) const;
};
