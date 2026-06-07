#include "Commands/UnrealMCPMRQCommands.h"

#include "Commands/UnrealMCPCommonUtils.h"
#include "Dom/JsonValue.h"
#include "Editor.h"
#include "Engine/World.h"
#include "Misc/Paths.h"
#include "MoviePipelineAntiAliasingSetting.h"
#include "MoviePipelineConfigBase.h"
#include "MoviePipelineConsoleVariableSetting.h"
#include "MoviePipelineDeferredPasses.h"
#include "MoviePipelineExecutor.h"
#include "MoviePipelineImageSequenceOutput.h"
#include "MoviePipelineOutputSetting.h"
#include "MoviePipelinePIEExecutor.h"
#include "MoviePipelinePrimaryConfig.h"
#include "MoviePipelineQueue.h"
#include "MoviePipelineQueueSubsystem.h"
#include "MoviePipelineSetting.h"
#include "ScopedTransaction.h"

FUnrealMCPMRQCommands::FUnrealMCPMRQCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPMRQCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("mrq_create_job")) return HandleCreateJob(Params);
    if (CommandType == TEXT("mrq_add_render_setting")) return HandleAddRenderSetting(Params);
    if (CommandType == TEXT("mrq_render_queue")) return HandleRenderQueue(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown Movie Render Queue command: %s"), *CommandType));
}

UMoviePipelineQueueSubsystem* FUnrealMCPMRQCommands::GetQueueSubsystem() const
{
    return GEditor ? GEditor->GetEditorSubsystem<UMoviePipelineQueueSubsystem>() : nullptr;
}

UMoviePipelineExecutorJob* FUnrealMCPMRQCommands::FindJob(UMoviePipelineQueue* Queue, const FString& JobName) const
{
    if (!Queue)
    {
        return nullptr;
    }

    const TArray<UMoviePipelineExecutorJob*> Jobs = Queue->GetJobs();
    if (JobName.IsEmpty())
    {
        return Jobs.Num() > 0 ? Jobs.Last() : nullptr;
    }

    for (UMoviePipelineExecutorJob* Job : Jobs)
    {
        if (Job && (Job->JobName.Equals(JobName, ESearchCase::IgnoreCase) ||
            Job->GetName().Equals(JobName, ESearchCase::IgnoreCase)))
        {
            return Job;
        }
    }
    return nullptr;
}

FString FUnrealMCPMRQCommands::NormalizeObjectPath(const FString& AssetOrObjectPath) const
{
    FString Path = AssetOrObjectPath;
    Path.TrimStartAndEndInline();
    if (Path.StartsWith(TEXT("/Game/")) && !Path.Contains(TEXT(".")))
    {
        Path = FString::Printf(TEXT("%s.%s"), *Path, *FPaths::GetBaseFilename(Path));
    }
    return Path;
}

FString FUnrealMCPMRQCommands::GetDefaultMapPath() const
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World || !World->GetOutermost())
    {
        return FString();
    }

    const FString PackagePath = World->GetOutermost()->GetPathName();
    if (PackagePath.StartsWith(TEXT("/Temp/")) || PackagePath.StartsWith(TEXT("/Transient")))
    {
        return FString();
    }
    return FString::Printf(TEXT("%s.%s"), *PackagePath, *FPaths::GetBaseFilename(PackagePath));
}

TSubclassOf<UMoviePipelineSetting> FUnrealMCPMRQCommands::GetImageOutputClass(const FString& ImageFormat) const
{
    if (ImageFormat.Equals(TEXT("jpg"), ESearchCase::IgnoreCase) ||
        ImageFormat.Equals(TEXT("jpeg"), ESearchCase::IgnoreCase))
    {
        return UMoviePipelineImageSequenceOutput_JPG::StaticClass();
    }
    if (ImageFormat.Equals(TEXT("bmp"), ESearchCase::IgnoreCase))
    {
        return UMoviePipelineImageSequenceOutput_BMP::StaticClass();
    }
    if (ImageFormat.Equals(TEXT("exr"), ESearchCase::IgnoreCase))
    {
        UClass* EXRClass = StaticLoadClass(
            UMoviePipelineSetting::StaticClass(),
            nullptr,
            TEXT("/Script/MovieRenderPipelineRenderPasses.MoviePipelineImageSequenceOutput_EXR"));
        return EXRClass ? EXRClass : UMoviePipelineImageSequenceOutput_PNG::StaticClass();
    }
    return UMoviePipelineImageSequenceOutput_PNG::StaticClass();
}

FIntPoint FUnrealMCPMRQCommands::GetResolutionField(const TSharedPtr<FJsonObject>& Params, const FIntPoint& DefaultValue) const
{
    const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
    if (Params.IsValid() && Params->TryGetArrayField(TEXT("resolution"), Values) && Values && Values->Num() >= 2)
    {
        return FIntPoint(
            FMath::Max(1, FMath::RoundToInt((*Values)[0]->AsNumber())),
            FMath::Max(1, FMath::RoundToInt((*Values)[1]->AsNumber())));
    }
    return DefaultValue;
}

TSharedPtr<FJsonObject> FUnrealMCPMRQCommands::HandleCreateJob(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    UMoviePipelineQueueSubsystem* Subsystem = GetQueueSubsystem();
    if (!Subsystem || !Subsystem->GetQueue())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Movie Render Queue subsystem is unavailable"));
    }

    FString JobName = TEXT("MCP_Render");
    Params->TryGetStringField(TEXT("job_name"), JobName);
    if (JobName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'job_name' parameter"));
    }

    UMoviePipelineQueue* Queue = Subsystem->GetQueue();
    bool bClearQueue = false;
    Params->TryGetBoolField(TEXT("clear_queue"), bClearQueue);
    if (bClearQueue)
    {
        Queue->DeleteAllJobs();
    }

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "MRQCreateJob", "Create Movie Render Queue Job"));
    Queue->Modify();

    UMoviePipelineExecutorJob* Job = Queue->AllocateNewJob(UMoviePipelineExecutorJob::StaticClass());
    if (!Job)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to allocate MRQ job"));
    }

    Job->Modify();
    Job->JobName = JobName;
    Job->SetIsEnabled(true);

    FString Author = TEXT("MCP");
    Params->TryGetStringField(TEXT("author"), Author);
    Job->Author = Author;

    FString SequencePath;
    Params->TryGetStringField(TEXT("sequence"), SequencePath);
    if (!SequencePath.IsEmpty())
    {
        Job->SetSequence(FSoftObjectPath(NormalizeObjectPath(SequencePath)));
    }

    FString MapPath;
    Params->TryGetStringField(TEXT("map"), MapPath);
    MapPath = MapPath.IsEmpty() ? GetDefaultMapPath() : NormalizeObjectPath(MapPath);
    if (!MapPath.IsEmpty())
    {
        Job->Map = FSoftObjectPath(MapPath);
    }

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("MRQ job has no primary configuration"));
    }

    UMoviePipelineOutputSetting* Output = Cast<UMoviePipelineOutputSetting>(
        Config->FindOrAddSettingByClass(UMoviePipelineOutputSetting::StaticClass()));
    if (Output)
    {
        FString OutputDirectory;
        Params->TryGetStringField(TEXT("output_directory"), OutputDirectory);
        if (!OutputDirectory.IsEmpty())
        {
            Output->OutputDirectory.Path = OutputDirectory;
        }

        FString FileNameFormat = TEXT("{sequence_name}.{frame_number}");
        Params->TryGetStringField(TEXT("file_name_format"), FileNameFormat);
        Output->FileNameFormat = FileNameFormat;
        Output->OutputResolution = GetResolutionField(Params, FIntPoint(1920, 1080));

        bool bOverwrite = true;
        Params->TryGetBoolField(TEXT("overwrite_existing"), bOverwrite);
        Output->bOverrideExistingOutput = bOverwrite;
    }

    Config->FindOrAddSettingByClass(UMoviePipelineDeferredPassBase::StaticClass());

    FString ImageFormat = TEXT("png");
    Params->TryGetStringField(TEXT("image_format"), ImageFormat);
    Config->FindOrAddSettingByClass(GetImageOutputClass(ImageFormat));

    Queue->InvalidateSerialNumber();
    return MakeQueueResult(TEXT("mrq_create_job"), Queue, Job);
}

TSharedPtr<FJsonObject> FUnrealMCPMRQCommands::HandleAddRenderSetting(const TSharedPtr<FJsonObject>& Params)
{
    if (!Params.IsValid())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing parameters"));
    }

    UMoviePipelineQueueSubsystem* Subsystem = GetQueueSubsystem();
    UMoviePipelineQueue* Queue = Subsystem ? Subsystem->GetQueue() : nullptr;
    if (!Queue)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Movie Render Queue subsystem is unavailable"));
    }

    FString JobName;
    Params->TryGetStringField(TEXT("job_name"), JobName);
    UMoviePipelineExecutorJob* Job = FindJob(Queue, JobName);
    if (!Job)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("MRQ job not found"));
    }

    UMoviePipelinePrimaryConfig* Config = Job->GetConfiguration();
    if (!Config)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("MRQ job has no primary configuration"));
    }

    FString SettingType = TEXT("output");
    Params->TryGetStringField(TEXT("setting_type"), SettingType);
    SettingType = SettingType.ToLower();

    const FScopedTransaction Transaction(NSLOCTEXT("UnrealMCP", "MRQAddSetting", "Add Movie Render Queue Setting"));
    Job->Modify();
    Config->Modify();

    FString AppliedSetting;
    if (SettingType == TEXT("output"))
    {
        UMoviePipelineOutputSetting* Output = Cast<UMoviePipelineOutputSetting>(
            Config->FindOrAddSettingByClass(UMoviePipelineOutputSetting::StaticClass()));
        if (!Output)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add output setting"));
        }

        FString OutputDirectory;
        if (Params->TryGetStringField(TEXT("output_directory"), OutputDirectory) && !OutputDirectory.IsEmpty())
        {
            Output->OutputDirectory.Path = OutputDirectory;
        }
        FString FileNameFormat;
        if (Params->TryGetStringField(TEXT("file_name_format"), FileNameFormat) && !FileNameFormat.IsEmpty())
        {
            Output->FileNameFormat = FileNameFormat;
        }
        Output->OutputResolution = GetResolutionField(Params, Output->OutputResolution);

        double CustomFrameRate = 0.0;
        if (Params->TryGetNumberField(TEXT("custom_frame_rate"), CustomFrameRate) && CustomFrameRate > 0.0)
        {
            Output->bUseCustomFrameRate = true;
            Output->OutputFrameRate = FFrameRate(FMath::RoundToInt(CustomFrameRate * 1000.0), 1000);
        }

        double HandleFrames = 0.0;
        if (Params->TryGetNumberField(TEXT("handle_frames"), HandleFrames))
        {
            Output->HandleFrameCount = FMath::Max(0, FMath::RoundToInt(HandleFrames));
        }

        double FrameStart = 0.0;
        double FrameEnd = 0.0;
        if (Params->TryGetNumberField(TEXT("frame_start"), FrameStart) &&
            Params->TryGetNumberField(TEXT("frame_end"), FrameEnd))
        {
            Output->bUseCustomPlaybackRange = true;
            Output->CustomStartFrame = FMath::RoundToInt(FrameStart);
            Output->CustomEndFrame = FMath::RoundToInt(FrameEnd);
        }
        AppliedSetting = TEXT("output");
    }
    else if (SettingType == TEXT("deferred_pass") || SettingType == TEXT("deferred"))
    {
        Config->FindOrAddSettingByClass(UMoviePipelineDeferredPassBase::StaticClass());
        AppliedSetting = TEXT("deferred_pass");
    }
    else if (SettingType == TEXT("image_output") || SettingType == TEXT("image") || SettingType == TEXT("png") ||
        SettingType == TEXT("jpg") || SettingType == TEXT("jpeg") || SettingType == TEXT("bmp") || SettingType == TEXT("exr"))
    {
        FString ImageFormat = SettingType;
        Params->TryGetStringField(TEXT("image_format"), ImageFormat);
        Config->FindOrAddSettingByClass(GetImageOutputClass(ImageFormat));
        AppliedSetting = FString::Printf(TEXT("image_output:%s"), *ImageFormat);
    }
    else if (SettingType == TEXT("anti_aliasing") || SettingType == TEXT("aa"))
    {
        UMoviePipelineAntiAliasingSetting* AA = Cast<UMoviePipelineAntiAliasingSetting>(
            Config->FindOrAddSettingByClass(UMoviePipelineAntiAliasingSetting::StaticClass()));
        if (!AA)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add anti-aliasing setting"));
        }

        double TemporalSamples = 0.0;
        if (Params->TryGetNumberField(TEXT("temporal_samples"), TemporalSamples))
        {
            AA->TemporalSampleCount = FMath::Max(1, FMath::RoundToInt(TemporalSamples));
        }
        double SpatialSamples = 0.0;
        if (Params->TryGetNumberField(TEXT("spatial_samples"), SpatialSamples))
        {
            AA->SpatialSampleCount = FMath::Max(1, FMath::RoundToInt(SpatialSamples));
        }
        double WarmupFrames = 0.0;
        if (Params->TryGetNumberField(TEXT("warmup_frames"), WarmupFrames))
        {
            AA->RenderWarmUpCount = FMath::Max(0, FMath::RoundToInt(WarmupFrames));
        }
        AppliedSetting = TEXT("anti_aliasing");
    }
    else if (SettingType == TEXT("console_variables") || SettingType == TEXT("cvars"))
    {
        UMoviePipelineConsoleVariableSetting* CVars = Cast<UMoviePipelineConsoleVariableSetting>(
            Config->FindOrAddSettingByClass(UMoviePipelineConsoleVariableSetting::StaticClass()));
        if (!CVars)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add console variable setting"));
        }

        const TSharedPtr<FJsonObject>* CVarObjectPtr = nullptr;
        if (Params->TryGetObjectField(TEXT("console_variables"), CVarObjectPtr) &&
            CVarObjectPtr && CVarObjectPtr->IsValid())
        {
            const TSharedPtr<FJsonObject>& CVarObject = *CVarObjectPtr;
            for (const TPair<FString, TSharedPtr<FJsonValue>>& Entry : CVarObject->Values)
            {
                if (Entry.Value.IsValid())
                {
                    CVars->AddOrUpdateConsoleVariable(Entry.Key, static_cast<float>(Entry.Value->AsNumber()));
                }
            }
        }
        AppliedSetting = TEXT("console_variables");
    }
    else
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Unsupported MRQ setting_type: %s"), *SettingType));
    }

    Queue->InvalidateSerialNumber();
    TSharedPtr<FJsonObject> Result = MakeQueueResult(TEXT("mrq_add_render_setting"), Queue, Job);
    Result->SetStringField(TEXT("applied_setting"), AppliedSetting);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMRQCommands::HandleRenderQueue(const TSharedPtr<FJsonObject>& Params)
{
    UMoviePipelineQueueSubsystem* Subsystem = GetQueueSubsystem();
    UMoviePipelineQueue* Queue = Subsystem ? Subsystem->GetQueue() : nullptr;
    if (!Subsystem || !Queue)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Movie Render Queue subsystem is unavailable"));
    }

    bool bDryRun = true;
    if (Params.IsValid())
    {
        Params->TryGetBoolField(TEXT("dry_run"), bDryRun);
    }

    if (Queue->GetJobs().Num() == 0)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Movie Render Queue is empty"));
    }

    TSharedPtr<FJsonObject> Result = MakeQueueResult(TEXT("mrq_render_queue"), Queue);
    Result->SetBoolField(TEXT("dry_run"), bDryRun);
    Result->SetBoolField(TEXT("is_rendering"), Subsystem->IsRendering());

    if (bDryRun)
    {
        Result->SetStringField(TEXT("executor"), TEXT("dry_run"));
        return Result;
    }

    if (Subsystem->IsRendering())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Movie Render Queue is already rendering"));
    }

    FString ExecutorName = TEXT("pie");
    if (Params.IsValid())
    {
        Params->TryGetStringField(TEXT("executor"), ExecutorName);
    }

    if (!ExecutorName.Equals(TEXT("pie"), ESearchCase::IgnoreCase))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Only the 'pie' MRQ executor is supported by this tool"));
    }

    UMoviePipelineExecutorBase* Executor = Subsystem->RenderQueueWithExecutor(UMoviePipelinePIEExecutor::StaticClass());
    if (!Executor)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to start Movie Render Queue executor"));
    }

    Result->SetStringField(TEXT("executor"), Executor->GetClass()->GetName());
    Result->SetBoolField(TEXT("is_rendering"), Subsystem->IsRendering());
    return Result;
}

TArray<TSharedPtr<FJsonValue>> FUnrealMCPMRQCommands::MakeSettingsSummary(UMoviePipelinePrimaryConfig* Config) const
{
    TArray<TSharedPtr<FJsonValue>> Settings;
    if (!Config)
    {
        return Settings;
    }

    for (UMoviePipelineSetting* Setting : Config->GetUserSettings())
    {
        if (Setting)
        {
            Settings.Add(MakeShared<FJsonValueString>(Setting->GetClass()->GetName()));
        }
    }
    return Settings;
}

TSharedPtr<FJsonObject> FUnrealMCPMRQCommands::MakeJobSummary(UMoviePipelineExecutorJob* Job) const
{
    TSharedPtr<FJsonObject> Summary = MakeShared<FJsonObject>();
    if (!Job)
    {
        return Summary;
    }

    Summary->SetStringField(TEXT("job_name"), Job->JobName);
    Summary->SetStringField(TEXT("object_name"), Job->GetName());
    Summary->SetStringField(TEXT("sequence"), Job->Sequence.ToString());
    Summary->SetStringField(TEXT("map"), Job->Map.ToString());
    Summary->SetStringField(TEXT("author"), Job->Author);
    Summary->SetBoolField(TEXT("enabled"), Job->IsEnabled());
    Summary->SetBoolField(TEXT("consumed"), Job->IsConsumed());
    Summary->SetNumberField(TEXT("progress"), Job->GetStatusProgress());
    Summary->SetArrayField(TEXT("settings"), MakeSettingsSummary(Job->GetConfiguration()));

    if (UMoviePipelineOutputSetting* Output = Job->GetConfiguration() ?
        Job->GetConfiguration()->FindSetting<UMoviePipelineOutputSetting>(true) : nullptr)
    {
        TSharedPtr<FJsonObject> OutputSummary = MakeShared<FJsonObject>();
        OutputSummary->SetStringField(TEXT("output_directory"), Output->OutputDirectory.Path);
        OutputSummary->SetStringField(TEXT("file_name_format"), Output->FileNameFormat);
        OutputSummary->SetNumberField(TEXT("resolution_x"), Output->OutputResolution.X);
        OutputSummary->SetNumberField(TEXT("resolution_y"), Output->OutputResolution.Y);
        OutputSummary->SetBoolField(TEXT("overwrite_existing"), Output->bOverrideExistingOutput);
        OutputSummary->SetNumberField(TEXT("handle_frames"), Output->HandleFrameCount);
        OutputSummary->SetBoolField(TEXT("custom_playback_range"), Output->bUseCustomPlaybackRange);
        Summary->SetObjectField(TEXT("output"), OutputSummary);
    }

    return Summary;
}

TSharedPtr<FJsonObject> FUnrealMCPMRQCommands::MakeQueueResult(
    const FString& StageName,
    UMoviePipelineQueue* Queue,
    UMoviePipelineExecutorJob* FocusJob) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Queue != nullptr);
    Result->SetStringField(TEXT("stage"), StageName);

    if (!Queue)
    {
        Result->SetStringField(TEXT("error"), TEXT("Movie Render Queue unavailable"));
        return Result;
    }

    const TArray<UMoviePipelineExecutorJob*> Jobs = Queue->GetJobs();
    Result->SetNumberField(TEXT("queue_job_count"), Jobs.Num());
    Result->SetNumberField(TEXT("queue_serial_number"), Queue->GetQueueSerialNumber());

    TArray<TSharedPtr<FJsonValue>> JobSummaries;
    for (UMoviePipelineExecutorJob* Job : Jobs)
    {
        JobSummaries.Add(MakeShared<FJsonValueObject>(MakeJobSummary(Job)));
    }
    Result->SetArrayField(TEXT("jobs"), JobSummaries);

    if (FocusJob)
    {
        Result->SetObjectField(TEXT("job"), MakeJobSummary(FocusJob));
    }
    return Result;
}
