#include "Commands/UnrealMCPMotionCommands.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Chooser.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Dom/JsonValue.h"
#include "EditorAssetLibrary.h"
#include "Animation/AnimSequence.h"
#include "Animation/MirrorDataTable.h"
#include "Engine/SkeletalMesh.h"
#include "IHasContext.h"
#include "Math/Interval.h"
#include "Misc/Paths.h"
#include "Misc/ScopedSlowTask.h"
#include "ObjectChooser_Asset.h"
#include "PoseSearch/PoseSearchDatabase.h"
#include "PoseSearch/PoseSearchSchema.h"
#include "ScopedTransaction.h"
#include "StructUtils/InstancedStruct.h"
#include "UObject/Package.h"
#include "UObject/UObjectIterator.h"

FUnrealMCPMotionCommands::FUnrealMCPMotionCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("motion_create_pose_search_schema")) return HandleCreatePoseSearchSchema(Params);
    if (CommandType == TEXT("motion_create_pose_search_database")) return HandleCreatePoseSearchDatabase(Params);
    if (CommandType == TEXT("motion_add_database_sequence")) return HandleAddPoseSearchSequence(Params);
    if (CommandType == TEXT("motion_inspect_pose_search_asset")) return HandleInspectPoseSearchAsset(Params);
    if (CommandType == TEXT("chooser_create_table")) return HandleCreateChooserTable(Params);
    if (CommandType == TEXT("chooser_add_asset_row")) return HandleAddChooserAssetRow(Params);
    if (CommandType == TEXT("chooser_inspect_table")) return HandleInspectChooserTable(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown Motion Matching / Chooser command: %s"), *CommandType));
}

FString FUnrealMCPMotionCommands::NormalizeAssetPath(const FString& InPath) const
{
    FString AssetPath = InPath;
    AssetPath.TrimStartAndEndInline();
    if (AssetPath.Contains(TEXT(".")))
    {
        AssetPath.LeftInline(AssetPath.Find(TEXT(".")));
    }
    AssetPath.RemoveFromEnd(TEXT("/"));
    return AssetPath;
}

FString FUnrealMCPMotionCommands::MakeObjectPath(const FString& AssetPath) const
{
    const FString CleanPath = NormalizeAssetPath(AssetPath);
    return FString::Printf(TEXT("%s.%s"), *CleanPath, *FPaths::GetBaseFilename(CleanPath));
}

bool FUnrealMCPMotionCommands::SplitPackagePath(const FString& AssetPath, FString& OutPackagePath, FString& OutAssetName) const
{
    const FString CleanPath = NormalizeAssetPath(AssetPath);
    int32 LastSlash = INDEX_NONE;
    if (!CleanPath.StartsWith(TEXT("/Game/")) || !CleanPath.FindLastChar(TEXT('/'), LastSlash) || LastSlash <= 0)
    {
        return false;
    }
    OutPackagePath = CleanPath.Left(LastSlash);
    OutAssetName = CleanPath.Mid(LastSlash + 1);
    return !OutPackagePath.IsEmpty() && !OutAssetName.IsEmpty();
}

UObject* FUnrealMCPMotionCommands::LoadAsset(const FString& AssetOrObjectPath) const
{
    if (AssetOrObjectPath.IsEmpty())
    {
        return nullptr;
    }
    const FString ObjectPath = AssetOrObjectPath.Contains(TEXT("."))
        ? AssetOrObjectPath
        : MakeObjectPath(AssetOrObjectPath);
    if (UObject* Loaded = StaticLoadObject(UObject::StaticClass(), nullptr, *ObjectPath))
    {
        return Loaded;
    }
    return StaticLoadObject(UObject::StaticClass(), nullptr, *AssetOrObjectPath);
}

UClass* FUnrealMCPMotionCommands::ResolveClass(const FString& ClassName, UClass* RequiredBaseClass) const
{
    if (!RequiredBaseClass)
    {
        return nullptr;
    }

    FString Query = ClassName;
    Query.TrimStartAndEndInline();
    if (Query.IsEmpty())
    {
        return RequiredBaseClass;
    }

    UClass* FoundClass = FindObject<UClass>(nullptr, *Query);
    if (!FoundClass)
    {
        FoundClass = LoadObject<UClass>(nullptr, *Query);
    }

    const FString ShortQuery = Query.StartsWith(TEXT("U")) ? Query.Mid(1) : Query;
    if (!FoundClass)
    {
        for (TObjectIterator<UClass> It; It; ++It)
        {
            UClass* Candidate = *It;
            if (Candidate && (Candidate->GetName() == Query || Candidate->GetName() == ShortQuery || Candidate->GetPathName() == Query))
            {
                FoundClass = Candidate;
                break;
            }
        }
    }

    if (!FoundClass || !FoundClass->IsChildOf(RequiredBaseClass))
    {
        return nullptr;
    }
    return FoundClass;
}

TArray<FString> FUnrealMCPMotionCommands::GetStringArrayField(const TSharedPtr<FJsonObject>& Params, const FString& FieldName) const
{
    TArray<FString> Values;
    const TArray<TSharedPtr<FJsonValue>>* JsonValues = nullptr;
    if (Params.IsValid() && Params->TryGetArrayField(FieldName, JsonValues))
    {
        for (const TSharedPtr<FJsonValue>& Value : *JsonValues)
        {
            if (Value.IsValid())
            {
                Values.Add(Value->AsString());
            }
        }
    }
    return Values;
}

TArray<TSharedPtr<FJsonValue>> FUnrealMCPMotionCommands::MakeStringArray(const TArray<FString>& Values) const
{
    TArray<TSharedPtr<FJsonValue>> JsonValues;
    for (const FString& Value : Values)
    {
        JsonValues.Add(MakeShared<FJsonValueString>(Value));
    }
    return JsonValues;
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::HandleCreatePoseSearchSchema(const TSharedPtr<FJsonObject>& Params)
{
    FString Name;
    Params->TryGetStringField(TEXT("name"), Name);
    FString Path = TEXT("/Game/Animation/MotionMatching");
    Params->TryGetStringField(TEXT("path"), Path);
    if (Name.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    Path.RemoveFromEnd(TEXT("/"));
    const FString AssetPath = FString::Printf(TEXT("%s/%s"), *Path, *Name);
    FString PackagePath;
    FString AssetName;
    if (!SplitPackagePath(AssetPath, PackagePath, AssetName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Pose Search schema path must be under /Game"));
    }

    const FString ObjectPath = MakeObjectPath(AssetPath);
    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    if (UEditorAssetLibrary::DoesAssetExist(ObjectPath))
    {
        if (!bOverwrite)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Asset already exists: %s"), *ObjectPath));
        }
        UEditorAssetLibrary::DeleteAsset(ObjectPath);
    }

    FScopedSlowTask SlowTask(2.0f, FText::FromString(TEXT("MCP Create Pose Search Schema")));
    SlowTask.MakeDialog(false);
    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Create Pose Search Schema")));
    UEditorAssetLibrary::MakeDirectory(PackagePath);

    UPoseSearchSchema* Schema = NewObject<UPoseSearchSchema>(
        CreatePackage(*AssetPath),
        *AssetName,
        RF_Public | RF_Standalone | RF_Transactional);
    if (!Schema)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Pose Search schema"));
    }

    int32 SampleRate = 30;
    Params->TryGetNumberField(TEXT("sample_rate"), SampleRate);
    Schema->SampleRate = FMath::Clamp(SampleRate, 1, 240);

    FString SkeletonPath;
    Params->TryGetStringField(TEXT("skeleton"), SkeletonPath);
    if (!SkeletonPath.IsEmpty())
    {
        USkeleton* Skeleton = Cast<USkeleton>(LoadAsset(SkeletonPath));
        if (!Skeleton)
        {
            if (USkeletalMesh* Mesh = Cast<USkeletalMesh>(LoadAsset(SkeletonPath)))
            {
                Skeleton = Mesh->GetSkeleton();
            }
        }
        if (!Skeleton)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not resolve skeleton or skeletal mesh: %s"), *SkeletonPath));
        }
        Schema->AddSkeleton(Skeleton);
    }

    bool bAddDefaultChannels = true;
    Params->TryGetBoolField(TEXT("add_default_channels"), bAddDefaultChannels);
    if (bAddDefaultChannels)
    {
        Schema->AddDefaultChannels();
    }

    Schema->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Schema);
    Schema->PostEditChange();

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ObjectPath, false);
    }

    TSharedPtr<FJsonObject> Result = SummarizePoseSearchSchema(Schema);
    Result->SetStringField(TEXT("stage"), TEXT("motion_create_pose_search_schema"));
    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(AssetPath));
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::HandleCreatePoseSearchDatabase(const TSharedPtr<FJsonObject>& Params)
{
    FString Name;
    Params->TryGetStringField(TEXT("name"), Name);
    FString Path = TEXT("/Game/Animation/MotionMatching");
    Params->TryGetStringField(TEXT("path"), Path);
    FString SchemaPath;
    Params->TryGetStringField(TEXT("schema"), SchemaPath);
    if (Name.IsEmpty() || SchemaPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' or 'schema' parameter"));
    }

    UPoseSearchSchema* Schema = Cast<UPoseSearchSchema>(LoadAsset(SchemaPath));
    if (!Schema)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load Pose Search schema: %s"), *SchemaPath));
    }

    Path.RemoveFromEnd(TEXT("/"));
    const FString AssetPath = FString::Printf(TEXT("%s/%s"), *Path, *Name);
    FString PackagePath;
    FString AssetName;
    if (!SplitPackagePath(AssetPath, PackagePath, AssetName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Pose Search database path must be under /Game"));
    }

    const FString ObjectPath = MakeObjectPath(AssetPath);
    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    if (UEditorAssetLibrary::DoesAssetExist(ObjectPath))
    {
        if (!bOverwrite)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Asset already exists: %s"), *ObjectPath));
        }
        UEditorAssetLibrary::DeleteAsset(ObjectPath);
    }

    FScopedSlowTask SlowTask(2.0f, FText::FromString(TEXT("MCP Create Pose Search Database")));
    SlowTask.MakeDialog(false);
    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Create Pose Search Database")));
    UEditorAssetLibrary::MakeDirectory(PackagePath);

    UPoseSearchDatabase* Database = NewObject<UPoseSearchDatabase>(
        CreatePackage(*AssetPath),
        *AssetName,
        RF_Public | RF_Standalone | RF_Transactional);
    if (!Database)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Pose Search database"));
    }
    Database->Schema = Schema;

    FString SearchMode;
    Params->TryGetStringField(TEXT("search_mode"), SearchMode);
    SearchMode = SearchMode.ToLower();
    if (SearchMode == TEXT("bruteforce") || SearchMode == TEXT("brute_force"))
    {
        Database->PoseSearchMode = EPoseSearchMode::BruteForce;
    }
    else if (SearchMode == TEXT("vptree"))
    {
        Database->PoseSearchMode = EPoseSearchMode::VPTree;
    }
    else if (SearchMode == TEXT("event_only"))
    {
        Database->PoseSearchMode = EPoseSearchMode::EventOnly;
    }

    for (const FString& Tag : GetStringArrayField(Params, TEXT("tags")))
    {
        Database->Tags.AddUnique(FName(*Tag));
    }

    Database->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Database);

    for (const FString& SequencePath : GetStringArrayField(Params, TEXT("sequences")))
    {
        UAnimSequence* Sequence = Cast<UAnimSequence>(LoadAsset(SequencePath));
        if (!Sequence)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load AnimSequence: %s"), *SequencePath));
        }

        FPoseSearchDatabaseSequence DatabaseSequence;
        DatabaseSequence.Sequence = Sequence;
#if WITH_EDITORONLY_DATA
        DatabaseSequence.bEnabled = true;
        DatabaseSequence.bDisableReselection = false;
        DatabaseSequence.MirrorOption = EPoseSearchMirrorOption::UnmirroredOnly;
#endif
        Database->AddAnimationAsset(FInstancedStruct::Make(DatabaseSequence));
    }

    Database->NotifyDerivedDataRebuild();
    Database->PostEditChange();

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ObjectPath, false);
    }

    TSharedPtr<FJsonObject> Result = SummarizePoseSearchDatabase(Database);
    Result->SetStringField(TEXT("stage"), TEXT("motion_create_pose_search_database"));
    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(AssetPath));
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::HandleAddPoseSearchSequence(const TSharedPtr<FJsonObject>& Params)
{
    FString DatabasePath;
    FString SequencePath;
    Params->TryGetStringField(TEXT("database"), DatabasePath);
    Params->TryGetStringField(TEXT("sequence"), SequencePath);
    if (DatabasePath.IsEmpty() || SequencePath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'database' or 'sequence' parameter"));
    }

    UPoseSearchDatabase* Database = Cast<UPoseSearchDatabase>(LoadAsset(DatabasePath));
    UAnimSequence* Sequence = Cast<UAnimSequence>(LoadAsset(SequencePath));
    if (!Database)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load Pose Search database: %s"), *DatabasePath));
    }
    if (!Sequence)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load AnimSequence: %s"), *SequencePath));
    }

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Add Pose Search Sequence")));
    Database->Modify();
    FPoseSearchDatabaseSequence DatabaseSequence;
    DatabaseSequence.Sequence = Sequence;

#if WITH_EDITORONLY_DATA
    bool bEnabled = true;
    Params->TryGetBoolField(TEXT("enabled"), bEnabled);
    DatabaseSequence.bEnabled = bEnabled;
    bool bDisableReselection = false;
    Params->TryGetBoolField(TEXT("disable_reselection"), bDisableReselection);
    DatabaseSequence.bDisableReselection = bDisableReselection;
    FString MirrorOption;
    Params->TryGetStringField(TEXT("mirror_option"), MirrorOption);
    MirrorOption = MirrorOption.ToLower();
    if (MirrorOption == TEXT("mirrored_only"))
    {
        DatabaseSequence.MirrorOption = EPoseSearchMirrorOption::MirroredOnly;
    }
    else if (MirrorOption == TEXT("both") || MirrorOption == TEXT("unmirrored_and_mirrored"))
    {
        DatabaseSequence.MirrorOption = EPoseSearchMirrorOption::UnmirroredAndMirrored;
    }
    const TArray<TSharedPtr<FJsonValue>>* SamplingRange = nullptr;
    if (Params->TryGetArrayField(TEXT("sampling_range"), SamplingRange) && SamplingRange && SamplingRange->Num() >= 2)
    {
        DatabaseSequence.SamplingRange = FFloatInterval(
            static_cast<float>((*SamplingRange)[0]->AsNumber()),
            static_cast<float>((*SamplingRange)[1]->AsNumber()));
    }
#endif

    Database->AddAnimationAsset(FInstancedStruct::Make(DatabaseSequence));
    Database->NotifyDerivedDataRebuild();
    Database->MarkPackageDirty();
    Database->PostEditChange();

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(Database->GetPathName(), false);
    }

    TSharedPtr<FJsonObject> Result = SummarizePoseSearchDatabase(Database);
    Result->SetStringField(TEXT("stage"), TEXT("motion_add_database_sequence"));
    Result->SetStringField(TEXT("added_sequence"), Sequence->GetPathName());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::SummarizePoseSearchSchema(UPoseSearchSchema* Schema) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Schema != nullptr);
    Result->SetStringField(TEXT("stage"), TEXT("motion_inspect_pose_search_asset"));
    Result->SetStringField(TEXT("asset_type"), TEXT("pose_search_schema"));
    if (!Schema)
    {
        return Result;
    }

    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(Schema->GetPathName()));
    Result->SetStringField(TEXT("object_path"), Schema->GetPathName());
    Result->SetNumberField(TEXT("sample_rate"), Schema->SampleRate);
    Result->SetNumberField(TEXT("schema_cardinality"), Schema->SchemaCardinality);
    Result->SetNumberField(TEXT("channel_count"), Schema->GetChannels().Num());

    TArray<TSharedPtr<FJsonValue>> Skeletons;
    for (const FPoseSearchRoledSkeleton& RoledSkeleton : Schema->GetRoledSkeletons())
    {
        TSharedPtr<FJsonObject> SkeletonObject = MakeShared<FJsonObject>();
        SkeletonObject->SetStringField(TEXT("role"), RoledSkeleton.Role.ToString());
        SkeletonObject->SetStringField(TEXT("skeleton"), RoledSkeleton.Skeleton ? RoledSkeleton.Skeleton->GetPathName() : TEXT(""));
        const UMirrorDataTable* MirrorDataTable = RoledSkeleton.MirrorDataTable.Get();
        SkeletonObject->SetStringField(TEXT("mirror_data_table"), MirrorDataTable ? MirrorDataTable->GetPathName() : TEXT(""));
        Skeletons.Add(MakeShared<FJsonValueObject>(SkeletonObject));
    }
    Result->SetArrayField(TEXT("skeletons"), Skeletons);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::SummarizePoseSearchDatabase(UPoseSearchDatabase* Database) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Database != nullptr);
    Result->SetStringField(TEXT("stage"), TEXT("motion_inspect_pose_search_asset"));
    Result->SetStringField(TEXT("asset_type"), TEXT("pose_search_database"));
    if (!Database)
    {
        return Result;
    }

    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(Database->GetPathName()));
    Result->SetStringField(TEXT("object_path"), Database->GetPathName());
    Result->SetStringField(TEXT("schema"), Database->Schema ? Database->Schema->GetPathName() : TEXT(""));
    Result->SetStringField(TEXT("search_mode"), StaticEnum<EPoseSearchMode>()->GetNameStringByValue(static_cast<int64>(Database->PoseSearchMode)));
    Result->SetNumberField(TEXT("animation_asset_count"), Database->GetNumAnimationAssets());
    Result->SetNumberField(TEXT("base_cost_bias"), Database->BaseCostBias);
    Result->SetNumberField(TEXT("continuing_pose_cost_bias"), Database->ContinuingPoseCostBias);
    Result->SetArrayField(TEXT("tags"), MakeStringArray([&]()
    {
        TArray<FString> Tags;
        for (const FName& Tag : Database->Tags)
        {
            Tags.Add(Tag.ToString());
        }
        return Tags;
    }()));

    TArray<TSharedPtr<FJsonValue>> Assets;
    for (int32 Index = 0; Index < Database->GetNumAnimationAssets(); ++Index)
    {
        TSharedPtr<FJsonObject> AssetObject = MakeShared<FJsonObject>();
        UObject* AnimAsset = Database->GetAnimationAsset(Index);
        AssetObject->SetNumberField(TEXT("index"), Index);
        AssetObject->SetStringField(TEXT("asset"), AnimAsset ? AnimAsset->GetPathName() : TEXT(""));
        AssetObject->SetStringField(TEXT("class"), AnimAsset ? AnimAsset->GetClass()->GetName() : TEXT(""));
        Assets.Add(MakeShared<FJsonValueObject>(AssetObject));
    }
    Result->SetArrayField(TEXT("animation_assets"), Assets);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::HandleInspectPoseSearchAsset(const TSharedPtr<FJsonObject>& Params)
{
    FString AssetPath;
    Params->TryGetStringField(TEXT("asset"), AssetPath);
    if (AssetPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'asset' parameter"));
    }

    UObject* Asset = LoadAsset(AssetPath);
    if (UPoseSearchDatabase* Database = Cast<UPoseSearchDatabase>(Asset))
    {
        return SummarizePoseSearchDatabase(Database);
    }
    if (UPoseSearchSchema* Schema = Cast<UPoseSearchSchema>(Asset))
    {
        return SummarizePoseSearchSchema(Schema);
    }
    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Asset is not a Pose Search schema or database: %s"), *AssetPath));
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::HandleCreateChooserTable(const TSharedPtr<FJsonObject>& Params)
{
    FString Name;
    Params->TryGetStringField(TEXT("name"), Name);
    FString Path = TEXT("/Game/Animation/Choosers");
    Params->TryGetStringField(TEXT("path"), Path);
    if (Name.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    Path.RemoveFromEnd(TEXT("/"));
    const FString AssetPath = FString::Printf(TEXT("%s/%s"), *Path, *Name);
    FString PackagePath;
    FString AssetName;
    if (!SplitPackagePath(AssetPath, PackagePath, AssetName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Chooser table path must be under /Game"));
    }

    const FString ObjectPath = MakeObjectPath(AssetPath);
    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    if (UEditorAssetLibrary::DoesAssetExist(ObjectPath))
    {
        if (!bOverwrite)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Asset already exists: %s"), *ObjectPath));
        }
        UEditorAssetLibrary::DeleteAsset(ObjectPath);
    }

    FScopedSlowTask SlowTask(2.0f, FText::FromString(TEXT("MCP Create Chooser Table")));
    SlowTask.MakeDialog(false);
    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Create Chooser Table")));
    UEditorAssetLibrary::MakeDirectory(PackagePath);

    UChooserTable* Chooser = NewObject<UChooserTable>(
        CreatePackage(*AssetPath),
        *AssetName,
        RF_Public | RF_Standalone | RF_Transactional);
    if (!Chooser)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Chooser table"));
    }

    FString ResultClassName = TEXT("/Script/CoreUObject.Object");
    Params->TryGetStringField(TEXT("result_class"), ResultClassName);
    if (UClass* ResultClass = ResolveClass(ResultClassName, UObject::StaticClass()))
    {
        Chooser->OutputObjectType = ResultClass;
    }
    Chooser->ResultType = EObjectChooserResultType::ObjectResult;
    Chooser->Compile(true);
    Chooser->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Chooser);

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ObjectPath, false);
    }

    TSharedPtr<FJsonObject> Result = SummarizeChooserTable(Chooser);
    Result->SetStringField(TEXT("stage"), TEXT("chooser_create_table"));
    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(AssetPath));
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::HandleAddChooserAssetRow(const TSharedPtr<FJsonObject>& Params)
{
    FString ChooserPath;
    FString AssetPath;
    Params->TryGetStringField(TEXT("chooser"), ChooserPath);
    Params->TryGetStringField(TEXT("asset"), AssetPath);
    if (ChooserPath.IsEmpty() || AssetPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'chooser' or 'asset' parameter"));
    }

    UChooserTable* Chooser = Cast<UChooserTable>(LoadAsset(ChooserPath));
    UObject* Asset = LoadAsset(AssetPath);
    if (!Chooser)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load Chooser table: %s"), *ChooserPath));
    }
    if (!Asset)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load chooser row asset: %s"), *AssetPath));
    }

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Add Chooser Asset Row")));
    Chooser->Modify();
    FAssetChooser AssetChooser;
    AssetChooser.Asset = Asset;
    Chooser->ResultsStructs.Add(FInstancedStruct::Make(AssetChooser));

    bool bEnabled = true;
    Params->TryGetBoolField(TEXT("enabled"), bEnabled);
    Chooser->DisabledRows.SetNum(Chooser->ResultsStructs.Num());
    Chooser->DisabledRows[Chooser->ResultsStructs.Num() - 1] = !bEnabled;
    Chooser->Compile(true);
    Chooser->MarkPackageDirty();

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(Chooser->GetPathName(), false);
    }

    TSharedPtr<FJsonObject> Result = SummarizeChooserTable(Chooser);
    Result->SetStringField(TEXT("stage"), TEXT("chooser_add_asset_row"));
    Result->SetStringField(TEXT("added_asset"), Asset->GetPathName());
    Result->SetNumberField(TEXT("added_row_index"), Chooser->ResultsStructs.Num() - 1);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::SummarizeChooserTable(UChooserTable* Chooser) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Chooser != nullptr);
    Result->SetStringField(TEXT("stage"), TEXT("chooser_inspect_table"));
    if (!Chooser)
    {
        return Result;
    }

    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(Chooser->GetPathName()));
    Result->SetStringField(TEXT("object_path"), Chooser->GetPathName());
    Result->SetStringField(TEXT("result_type"), StaticEnum<EObjectChooserResultType>()->GetNameStringByValue(static_cast<int64>(Chooser->ResultType)));
    Result->SetStringField(TEXT("result_class"), Chooser->OutputObjectType ? Chooser->OutputObjectType->GetPathName() : TEXT(""));
#if WITH_EDITORONLY_DATA
    Result->SetNumberField(TEXT("row_count"), Chooser->ResultsStructs.Num());
    Result->SetNumberField(TEXT("column_count"), Chooser->ColumnsStructs.Num());

    TArray<TSharedPtr<FJsonValue>> Rows;
    for (int32 Index = 0; Index < Chooser->ResultsStructs.Num(); ++Index)
    {
        TSharedPtr<FJsonObject> RowObject = MakeShared<FJsonObject>();
        const FInstancedStruct& Row = Chooser->ResultsStructs[Index];
        RowObject->SetNumberField(TEXT("index"), Index);
        RowObject->SetBoolField(TEXT("enabled"), !Chooser->IsRowDisabled(Index));
        RowObject->SetStringField(TEXT("struct"), Row.IsValid() && Row.GetScriptStruct() ? Row.GetScriptStruct()->GetPathName() : TEXT(""));
        if (const FAssetChooser* AssetChooser = Row.GetPtr<FAssetChooser>())
        {
            RowObject->SetStringField(TEXT("asset"), AssetChooser->Asset ? AssetChooser->Asset->GetPathName() : TEXT(""));
        }
        Rows.Add(MakeShared<FJsonValueObject>(RowObject));
    }
    Result->SetArrayField(TEXT("rows"), Rows);
#else
    Result->SetNumberField(TEXT("row_count"), Chooser->CookedResults.Num());
    Result->SetNumberField(TEXT("column_count"), Chooser->ColumnsStructs.Num());
    Result->SetArrayField(TEXT("rows"), TArray<TSharedPtr<FJsonValue>>());
#endif
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMotionCommands::HandleInspectChooserTable(const TSharedPtr<FJsonObject>& Params)
{
    FString ChooserPath;
    Params->TryGetStringField(TEXT("chooser"), ChooserPath);
    if (ChooserPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'chooser' parameter"));
    }

    UChooserTable* Chooser = Cast<UChooserTable>(LoadAsset(ChooserPath));
    if (!Chooser)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load Chooser table: %s"), *ChooserPath));
    }
    return SummarizeChooserTable(Chooser);
}
