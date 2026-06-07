#include "Commands/UnrealMCPEditorCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"

// Python scripting plugin interface
#include "IPythonScriptPlugin.h"
#include "EngineUtils.h"       // TActorIterator

#include "Editor.h"
#include "EditorViewportClient.h"
#include "LevelEditorViewport.h"
#include "ImageUtils.h"
#include "HighResScreenshot.h"
#include "Engine/GameViewportClient.h"
#include "Misc/FileHelper.h"
#include "GameFramework/Actor.h"
#include "Engine/Selection.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/PackageName.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/DirectionalLight.h"
#include "Engine/PointLight.h"
#include "Engine/SpotLight.h"
#include "Camera/CameraActor.h"
#include "Components/StaticMeshComponent.h"
#include "EditorSubsystem.h"
#include "Subsystems/EditorActorSubsystem.h"
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetToolsModule.h"
#include "InputAction.h"
#include "InputModifiers.h"
#include "InputMappingContext.h"
#include "InputTriggers.h"
#include "DataLayer/DataLayerFactory.h"
#include "DataLayer/DataLayerEditorSubsystem.h"
#include "EditorAssetLibrary.h"
#include "EditorBuildUtils.h"
#include "Misc/Paths.h"
#include "Misc/ScopedSlowTask.h"
#include "ScopedTransaction.h"
#include "UObject/SavePackage.h"
#include "WorldPartition/LoaderAdapter/LoaderAdapterShape.h"
#include "WorldPartition/WorldPartition.h"
#include "WorldPartition/WorldPartitionActorLoaderInterface.h"
#include "WorldPartition/WorldPartitionEditorLoaderAdapter.h"
#include "WorldPartition/WorldPartitionHelpers.h"
#include "WorldPartition/DataLayer/DataLayerAsset.h"
#include "WorldPartition/DataLayer/DataLayerInstance.h"
#include "WorldPartition/HLOD/HLODLayer.h"

namespace UnrealMCPExecPythonDetail
{
	// ExecPythonCommandEx can AV inside EditorScriptingUtilities / MassEntity observers
	// when Python dirties assets synchronously. MSVC SEH (__try/__except) returns cleanly
	// so the editor survives and MCP returns JSON instead of EXCEPTION_ACCESS_VIOLATION.
	//
	// - Use __except(1) instead of EXCEPTION_EXECUTE_HANDLER so we do not depend on
	//   <excpt.h> / Windows.h macro order in IWYU builds.
	// - Gate on real MSVC only: Clang (and clang-cl) do not support __try/__except.
	static bool ExecPythonWithSeh(IPythonScriptPlugin* Py, FPythonCommandEx& Cmd, bool& bOutSehCrash)
	{
		bOutSehCrash = false;
#if PLATFORM_WINDOWS && defined(_MSC_VER) && !defined(__clang__)
		__try
		{
			return Py->ExecPythonCommandEx(Cmd);
		}
		__except (1)
		{
			bOutSehCrash = true;
			return false;
		}
#else
		return Py->ExecPythonCommandEx(Cmd);
#endif
	}
} // namespace UnrealMCPExecPythonDetail

namespace UnrealMCPEditorCommandDetail
{
    static UWorld* GetEditorWorld()
    {
        return GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    }

    static FString NormalizeAssetPath(const FString& InPath)
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

    static FString MakeObjectPath(const FString& AssetPath)
    {
        const FString CleanPath = NormalizeAssetPath(AssetPath);
        return FString::Printf(TEXT("%s.%s"), *CleanPath, *FPaths::GetBaseFilename(CleanPath));
    }

    static bool SplitPackagePath(const FString& AssetPath, FString& OutPackagePath, FString& OutAssetName)
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

    static UObject* LoadAsset(const FString& AssetOrObjectPath)
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

    static FVector ReadVectorField(const TSharedPtr<FJsonObject>& Params, const TCHAR* FieldName, const FVector& DefaultValue)
    {
        const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
        if (Params.IsValid() && Params->TryGetArrayField(FieldName, Values) && Values && Values->Num() >= 3)
        {
            return FVector((*Values)[0]->AsNumber(), (*Values)[1]->AsNumber(), (*Values)[2]->AsNumber());
        }
        return DefaultValue;
    }

    static FBox ReadRegionBox(const TSharedPtr<FJsonObject>& Params)
    {
        const FVector Center = ReadVectorField(Params, TEXT("center"), FVector::ZeroVector);
        const FVector Extent = ReadVectorField(Params, TEXT("extent"), FVector(50000.0, 50000.0, 50000.0));
        const FVector Min = ReadVectorField(Params, TEXT("min"), Center - Extent);
        const FVector Max = ReadVectorField(Params, TEXT("max"), Center + Extent);
        return FBox(Min, Max);
    }

    static TArray<TSharedPtr<FJsonValue>> VectorToJson(const FVector& Value)
    {
        TArray<TSharedPtr<FJsonValue>> Values;
        Values.Add(MakeShared<FJsonValueNumber>(Value.X));
        Values.Add(MakeShared<FJsonValueNumber>(Value.Y));
        Values.Add(MakeShared<FJsonValueNumber>(Value.Z));
        return Values;
    }

    static TSharedPtr<FJsonObject> BoxToJson(const FBox& Box)
    {
        TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
        Obj->SetArrayField(TEXT("min"), VectorToJson(Box.Min));
        Obj->SetArrayField(TEXT("max"), VectorToJson(Box.Max));
        Obj->SetArrayField(TEXT("center"), VectorToJson(Box.GetCenter()));
        Obj->SetArrayField(TEXT("extent"), VectorToJson(Box.GetExtent()));
        return Obj;
    }

    static TArray<TSharedPtr<FJsonValue>> MakeStringArray(const TArray<FString>& Values)
    {
        TArray<TSharedPtr<FJsonValue>> JsonValues;
        for (const FString& Value : Values)
        {
            JsonValues.Add(MakeShared<FJsonValueString>(Value));
        }
        return JsonValues;
    }

    static TArray<FString> GetStringArrayField(const TSharedPtr<FJsonObject>& Params, const FString& FieldName)
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

    static TSharedPtr<FJsonObject> SummarizeDataLayer(UDataLayerInstance* DataLayer, UDataLayerAsset* Asset)
    {
        TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
        Obj->SetStringField(TEXT("name"), DataLayer ? DataLayer->GetDataLayerShortName() : TEXT(""));
        Obj->SetStringField(TEXT("full_name"), DataLayer ? DataLayer->GetDataLayerFullName() : TEXT(""));
        Obj->SetStringField(TEXT("object_path"), DataLayer ? DataLayer->GetPathName() : TEXT(""));
        Obj->SetStringField(TEXT("asset_path"), Asset ? NormalizeAssetPath(Asset->GetPathName()) : TEXT(""));
        Obj->SetStringField(TEXT("asset_object_path"), Asset ? Asset->GetPathName() : TEXT(""));
        Obj->SetBoolField(TEXT("is_runtime"), DataLayer ? DataLayer->IsRuntime() : false);
        Obj->SetBoolField(TEXT("is_visible"), DataLayer ? DataLayer->IsVisible() : false);
        Obj->SetBoolField(TEXT("is_loaded_in_editor"), DataLayer ? DataLayer->IsLoadedInEditor() : false);
        Obj->SetStringField(TEXT("initial_runtime_state"), DataLayer ? GetDataLayerRuntimeStateName(DataLayer->GetInitialRuntimeState()) : TEXT(""));
        return Obj;
    }

    static AActor* FindActorByNameOrLabel(UWorld* World, const FString& Query)
    {
        if (!World || Query.IsEmpty())
        {
            return nullptr;
        }

        for (TActorIterator<AActor> It(World); It; ++It)
        {
            AActor* Actor = *It;
            if (Actor && (Actor->GetName().Equals(Query, ESearchCase::IgnoreCase) ||
                Actor->GetActorLabel().Equals(Query, ESearchCase::IgnoreCase) ||
                Actor->GetPathName().Equals(Query, ESearchCase::IgnoreCase)))
            {
                return Actor;
            }
        }
        return nullptr;
    }

    static EDataLayerRuntimeState ParseRuntimeState(const FString& State)
    {
        const FString Lower = State.ToLower();
        if (Lower == TEXT("loaded"))
        {
            return EDataLayerRuntimeState::Loaded;
        }
        if (Lower == TEXT("activated") || Lower == TEXT("active") || Lower == TEXT("visible"))
        {
            return EDataLayerRuntimeState::Activated;
        }
        return EDataLayerRuntimeState::Unloaded;
    }

    static bool MatchesText(const FString& Value, const FString& Query, bool bExact)
    {
        if (Query.IsEmpty())
        {
            return true;
        }
        return bExact
            ? Value.Equals(Query, ESearchCase::IgnoreCase)
            : Value.Contains(Query, ESearchCase::IgnoreCase);
    }

    static TSharedPtr<FJsonObject> ClassEntryToJson(UClass* Class)
    {
        TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
        Obj->SetStringField(TEXT("name"), Class ? Class->GetName() : TEXT(""));
        Obj->SetStringField(TEXT("path"), Class ? Class->GetPathName() : TEXT(""));
        return Obj;
    }

    static TArray<TSharedPtr<FJsonValue>> ClassChainToJson(UClass* Class)
    {
        TArray<TSharedPtr<FJsonValue>> Chain;
        for (UClass* Current = Class; Current; Current = Current->GetSuperClass())
        {
            Chain.Add(MakeShared<FJsonValueObject>(ClassEntryToJson(Current)));
        }
        return Chain;
    }

    static void AppendClassChainStrings(UClass* Class, TArray<FString>& OutNames)
    {
        for (UClass* Current = Class; Current; Current = Current->GetSuperClass())
        {
            OutNames.Add(Current->GetName());
            OutNames.Add(Current->GetPathName());
        }
    }

    static TSharedPtr<FJsonObject> ActorIdentityToJson(AActor* Actor)
    {
        TSharedPtr<FJsonObject> Obj = MakeShared<FJsonObject>();
        if (!Actor)
        {
            return Obj;
        }

        UClass* Class = Actor->GetClass();
        Obj->SetStringField(TEXT("label"), Actor->GetActorLabel());
        Obj->SetStringField(TEXT("name"), Actor->GetName());
        Obj->SetStringField(TEXT("path"), Actor->GetPathName());
        Obj->SetStringField(TEXT("class"), Class ? Class->GetName() : TEXT(""));
        Obj->SetStringField(TEXT("class_path"), Class ? Class->GetPathName() : TEXT(""));
        Obj->SetArrayField(TEXT("class_chain"), ClassChainToJson(Class));
        return Obj;
    }

    static UBlueprint* LoadBlueprintByPathOrName(const FString& Query)
    {
        if (Query.IsEmpty())
        {
            return nullptr;
        }

        TArray<FString> Candidates;
        Candidates.Add(Query);
        if (Query.StartsWith(TEXT("/Game/")) && !Query.Contains(TEXT(".")))
        {
            const FString AssetName = FPackageName::GetShortName(Query);
            Candidates.Add(Query + TEXT(".") + AssetName);
        }

        for (const FString& Candidate : Candidates)
        {
            if (UBlueprint* Blueprint = LoadObject<UBlueprint>(nullptr, *Candidate))
            {
                return Blueprint;
            }
        }

        return FUnrealMCPCommonUtils::FindBlueprint(Query);
    }

    static UInputMappingContext* LoadInputMappingContextByPathOrName(const FString& Query)
    {
        if (Query.IsEmpty())
        {
            return nullptr;
        }

        TArray<FString> Candidates;
        Candidates.Add(Query);
        if (Query.StartsWith(TEXT("/Game/")) && !Query.Contains(TEXT(".")))
        {
            const FString AssetName = FPackageName::GetShortName(Query);
            Candidates.Add(Query + TEXT(".") + AssetName);
        }

        for (const FString& Candidate : Candidates)
        {
            if (UInputMappingContext* IMC = LoadObject<UInputMappingContext>(nullptr, *Candidate))
            {
                return IMC;
            }
        }

        const FString ShortName = FPackageName::GetShortName(Query);
        FAssetRegistryModule& AssetRegistryModule =
            FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
        FARFilter Filter;
        Filter.PackagePaths.Add(FName(TEXT("/Game")));
        Filter.bRecursivePaths = true;
        Filter.ClassPaths.Add(UInputMappingContext::StaticClass()->GetClassPathName());

        TArray<FAssetData> Assets;
        AssetRegistryModule.Get().GetAssets(Filter, Assets);
        for (const FAssetData& Asset : Assets)
        {
            if (Asset.AssetName.ToString().Equals(ShortName, ESearchCase::IgnoreCase) ||
                Asset.PackageName.ToString().EndsWith(TEXT("/") + ShortName, ESearchCase::IgnoreCase))
            {
                return Cast<UInputMappingContext>(Asset.GetAsset());
            }
        }
        return nullptr;
    }
}

FUnrealMCPEditorCommands::FUnrealMCPEditorCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    // Actor manipulation commands
    if (CommandType == TEXT("get_actors_in_level"))
    {
        return HandleGetActorsInLevel(Params);
    }
    else if (CommandType == TEXT("get_actor_identity"))
    {
        return HandleGetActorIdentity(Params);
    }
    else if (CommandType == TEXT("find_actors_by_name"))
    {
        return HandleFindActorsByName(Params);
    }
    else if (CommandType == TEXT("find_actors_by_class"))
    {
        return HandleFindActorsByClass(Params);
    }
    else if (CommandType == TEXT("spawn_actor") || CommandType == TEXT("create_actor"))
    {
        if (CommandType == TEXT("create_actor"))
        {
            UE_LOG(LogTemp, Warning, TEXT("'create_actor' command is deprecated and will be removed in a future version. Please use 'spawn_actor' instead."));
        }
        return HandleSpawnActor(Params);
    }
    else if (CommandType == TEXT("delete_actor"))
    {
        return HandleDeleteActor(Params);
    }
    else if (CommandType == TEXT("set_actor_transform"))
    {
        return HandleSetActorTransform(Params);
    }
    else if (CommandType == TEXT("get_actor_properties"))
    {
        return HandleGetActorProperties(Params);
    }
    else if (CommandType == TEXT("set_actor_property"))
    {
        return HandleSetActorProperty(Params);
    }
    else if (CommandType == TEXT("check_blueprint_generated_class"))
    {
        return HandleCheckBlueprintGeneratedClass(Params);
    }
    else if (CommandType == TEXT("inspect_input_mapping_context"))
    {
        return HandleInspectInputMappingContext(Params);
    }
    // Blueprint actor spawning
    else if (CommandType == TEXT("spawn_blueprint_actor"))
    {
        return HandleSpawnBlueprintActor(Params);
    }
    // Editor viewport commands
    else if (CommandType == TEXT("focus_viewport"))
    {
        return HandleFocusViewport(Params);
    }
    else if (CommandType == TEXT("take_screenshot"))
    {
        return HandleTakeScreenshot(Params);
    }
    else if (CommandType == TEXT("wp_load_region"))
    {
        return HandleWorldPartitionLoadRegion(Params);
    }
    else if (CommandType == TEXT("wp_unload_region"))
    {
        return HandleWorldPartitionUnloadRegion(Params);
    }
    else if (CommandType == TEXT("wp_create_data_layer"))
    {
        return HandleWorldPartitionCreateDataLayer(Params);
    }
    else if (CommandType == TEXT("hlod_generate"))
    {
        return HandleHLODGenerate(Params);
    }
    else if (CommandType == TEXT("hlod_assign_layer"))
    {
        return HandleHLODAssignLayer(Params);
    }
    else if (CommandType == TEXT("exec_python"))
    {
        return HandleExecPython(Params);
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown editor command: %s"), *CommandType));
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleGetActorsInLevel(const TSharedPtr<FJsonObject>& Params)
{
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    TArray<TSharedPtr<FJsonValue>> ActorArray;
    for (AActor* Actor : AllActors)
    {
        if (Actor)
        {
            ActorArray.Add(FUnrealMCPCommonUtils::ActorToJson(Actor));
        }
    }
    
    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetArrayField(TEXT("actors"), ActorArray);
    
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleGetActorIdentity(const TSharedPtr<FJsonObject>& Params)
{
    FString Query;
    Params->TryGetStringField(TEXT("actor_name_or_label"), Query);

    bool bIncludeAll = false;
    Params->TryGetBoolField(TEXT("include_all"), bIncludeAll);

    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);

    TArray<TSharedPtr<FJsonValue>> MatchingActors;
    for (AActor* Actor : AllActors)
    {
        if (!Actor)
        {
            continue;
        }

        UClass* Class = Actor->GetClass();
        const FString SearchText = FString::Printf(
            TEXT("%s %s %s %s %s"),
            *Actor->GetActorLabel(),
            *Actor->GetName(),
            *Actor->GetPathName(),
            Class ? *Class->GetName() : TEXT(""),
            Class ? *Class->GetPathName() : TEXT(""));

        if (bIncludeAll || Query.IsEmpty() || SearchText.Contains(Query, ESearchCase::IgnoreCase))
        {
            MatchingActors.Add(MakeShared<FJsonValueObject>(
                UnrealMCPEditorCommandDetail::ActorIdentityToJson(Actor)));
        }
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("query"), Query);
    ResultObj->SetNumberField(TEXT("count"), MatchingActors.Num());
    ResultObj->SetArrayField(TEXT("actors"), MatchingActors);
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleFindActorsByName(const TSharedPtr<FJsonObject>& Params)
{
    FString Pattern;
    if (!Params->TryGetStringField(TEXT("pattern"), Pattern))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'pattern' parameter"));
    }
    
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    TArray<TSharedPtr<FJsonValue>> MatchingActors;
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName().Contains(Pattern))
        {
            MatchingActors.Add(FUnrealMCPCommonUtils::ActorToJson(Actor));
        }
    }
    
    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetArrayField(TEXT("actors"), MatchingActors);
    
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleFindActorsByClass(const TSharedPtr<FJsonObject>& Params)
{
    FString ClassName;
    if (!Params->TryGetStringField(TEXT("class_name"), ClassName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'class_name' parameter"));
    }

    bool bExact = false;
    Params->TryGetBoolField(TEXT("exact"), bExact);

    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);

    TArray<TSharedPtr<FJsonValue>> MatchingActors;
    for (AActor* Actor : AllActors)
    {
        if (!Actor)
        {
            continue;
        }

        TArray<FString> ClassNames;
        UnrealMCPEditorCommandDetail::AppendClassChainStrings(Actor->GetClass(), ClassNames);

        bool bMatched = false;
        for (const FString& Candidate : ClassNames)
        {
            if (UnrealMCPEditorCommandDetail::MatchesText(Candidate, ClassName, bExact))
            {
                bMatched = true;
                break;
            }
        }

        if (bMatched)
        {
            MatchingActors.Add(MakeShared<FJsonValueObject>(
                UnrealMCPEditorCommandDetail::ActorIdentityToJson(Actor)));
        }
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("class_name"), ClassName);
    ResultObj->SetBoolField(TEXT("exact"), bExact);
    ResultObj->SetNumberField(TEXT("count"), MatchingActors.Num());
    ResultObj->SetArrayField(TEXT("actors"), MatchingActors);
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleSpawnActor(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString ActorType;
    if (!Params->TryGetStringField(TEXT("type"), ActorType))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'type' parameter"));
    }

    // Get actor name (required parameter)
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Get optional transform parameters
    FVector Location(0.0f, 0.0f, 0.0f);
    FRotator Rotation(0.0f, 0.0f, 0.0f);
    FVector Scale(1.0f, 1.0f, 1.0f);

    if (Params->HasField(TEXT("location")))
    {
        Location = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
    }
    if (Params->HasField(TEXT("rotation")))
    {
        Rotation = FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"));
    }
    if (Params->HasField(TEXT("scale")))
    {
        Scale = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("scale"));
    }

    // Create the actor based on type
    AActor* NewActor = nullptr;
    UWorld* World = GEditor->GetEditorWorldContext().World();

    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    // Check if an actor with this name already exists
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(World, AActor::StaticClass(), AllActors);
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName() == ActorName)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor with name '%s' already exists"), *ActorName));
        }
    }

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = *ActorName;

    // Normalise type string to canonical mixed-case for comparison
    FString ActorTypeNorm = ActorType.ToLower();

    if (ActorTypeNorm == TEXT("staticmeshactor"))
    {
        NewActor = World->SpawnActor<AStaticMeshActor>(AStaticMeshActor::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorTypeNorm == TEXT("pointlight"))
    {
        NewActor = World->SpawnActor<APointLight>(APointLight::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorTypeNorm == TEXT("spotlight"))
    {
        NewActor = World->SpawnActor<ASpotLight>(ASpotLight::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorTypeNorm == TEXT("directionallight"))
    {
        NewActor = World->SpawnActor<ADirectionalLight>(ADirectionalLight::StaticClass(), Location, Rotation, SpawnParams);
    }
    else if (ActorTypeNorm == TEXT("cameraactor"))
    {
        NewActor = World->SpawnActor<ACameraActor>(ACameraActor::StaticClass(), Location, Rotation, SpawnParams);
    }
    else
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Unknown actor type: %s"), *ActorType));
    }

    if (NewActor)
    {
        // Set scale (since SpawnActor only takes location and rotation)
        FTransform Transform = NewActor->GetTransform();
        Transform.SetScale3D(Scale);
        NewActor->SetActorTransform(Transform);

        // Return the created actor's details
        return FUnrealMCPCommonUtils::ActorToJsonObject(NewActor, true);
    }

    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create actor"));
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleDeleteActor(const TSharedPtr<FJsonObject>& Params)
{
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName() == ActorName)
        {
            // Store actor info before deletion for the response
            TSharedPtr<FJsonObject> ActorInfo = FUnrealMCPCommonUtils::ActorToJsonObject(Actor);
            
            // Delete the actor
            Actor->Destroy();
            
            TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
            ResultObj->SetObjectField(TEXT("deleted_actor"), ActorInfo);
            return ResultObj;
        }
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleSetActorTransform(const TSharedPtr<FJsonObject>& Params)
{
    // Get actor name
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Find the actor
    AActor* TargetActor = nullptr;
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName() == ActorName)
        {
            TargetActor = Actor;
            break;
        }
    }

    if (!TargetActor)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    // Get transform parameters
    FTransform NewTransform = TargetActor->GetTransform();

    if (Params->HasField(TEXT("location")))
    {
        NewTransform.SetLocation(FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location")));
    }
    if (Params->HasField(TEXT("rotation")))
    {
        NewTransform.SetRotation(FQuat(FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"))));
    }
    if (Params->HasField(TEXT("scale")))
    {
        NewTransform.SetScale3D(FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("scale")));
    }

    // Set the new transform
    TargetActor->SetActorTransform(NewTransform);

    // Return updated actor info
    return FUnrealMCPCommonUtils::ActorToJsonObject(TargetActor, true);
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleGetActorProperties(const TSharedPtr<FJsonObject>& Params)
{
    // Get actor name
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Find the actor
    AActor* TargetActor = nullptr;
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName() == ActorName)
        {
            TargetActor = Actor;
            break;
        }
    }

    if (!TargetActor)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    // Always return detailed properties for this command
    return FUnrealMCPCommonUtils::ActorToJsonObject(TargetActor, true);
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleSetActorProperty(const TSharedPtr<FJsonObject>& Params)
{
    // Get actor name
    FString ActorName;
    if (!Params->TryGetStringField(TEXT("name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    // Find the actor
    AActor* TargetActor = nullptr;
    TArray<AActor*> AllActors;
    UGameplayStatics::GetAllActorsOfClass(GWorld, AActor::StaticClass(), AllActors);
    
    for (AActor* Actor : AllActors)
    {
        if (Actor && Actor->GetName() == ActorName)
        {
            TargetActor = Actor;
            break;
        }
    }

    if (!TargetActor)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Actor not found: %s"), *ActorName));
    }

    // Get property name
    FString PropertyName;
    if (!Params->TryGetStringField(TEXT("property_name"), PropertyName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'property_name' parameter"));
    }

    // Get property value
    if (!Params->HasField(TEXT("property_value")))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'property_value' parameter"));
    }
    
    TSharedPtr<FJsonValue> PropertyValue = Params->Values.FindRef(TEXT("property_value"));
    
    // Set the property using our utility function
    FString ErrorMessage;
    if (FUnrealMCPCommonUtils::SetObjectProperty(TargetActor, PropertyName, PropertyValue, ErrorMessage))
    {
        // Property set successfully
        TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
        ResultObj->SetStringField(TEXT("actor"), ActorName);
        ResultObj->SetStringField(TEXT("property"), PropertyName);
        ResultObj->SetBoolField(TEXT("success"), true);
        
        // Also include the full actor details
        ResultObj->SetObjectField(TEXT("actor_details"), FUnrealMCPCommonUtils::ActorToJsonObject(TargetActor, true));
        return ResultObj;
    }
    else
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(ErrorMessage);
    }
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleSpawnBlueprintActor(const TSharedPtr<FJsonObject>& Params)
{
    // Get required parameters
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    FString ActorName;
    if (!Params->TryGetStringField(TEXT("actor_name"), ActorName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'actor_name' parameter"));
    }

    // Find the blueprint
    if (BlueprintName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Blueprint name is empty"));
    }

    // Resolve by short asset name anywhere under /Game (same as other MCP blueprint commands).
    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint || !IsValid(Blueprint))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));
    }

    // Get transform parameters
    FVector Location(0.0f, 0.0f, 0.0f);
    FRotator Rotation(0.0f, 0.0f, 0.0f);
    FVector Scale(1.0f, 1.0f, 1.0f);

    if (Params->HasField(TEXT("location")))
    {
        Location = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
    }
    if (Params->HasField(TEXT("rotation")))
    {
        Rotation = FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"));
    }
    if (Params->HasField(TEXT("scale")))
    {
        Scale = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("scale"));
    }

    // Spawn the actor
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get editor world"));
    }

    FTransform SpawnTransform;
    SpawnTransform.SetLocation(Location);
    SpawnTransform.SetRotation(FQuat(Rotation));
    SpawnTransform.SetScale3D(Scale);

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = *ActorName;

    AActor* NewActor = World->SpawnActor<AActor>(Blueprint->GeneratedClass, SpawnTransform, SpawnParams);
    if (NewActor)
    {
        return FUnrealMCPCommonUtils::ActorToJsonObject(NewActor, true);
    }

    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn blueprint actor"));
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleCheckBlueprintGeneratedClass(const TSharedPtr<FJsonObject>& Params)
{
    FString BlueprintPathOrName;
    if (!Params->TryGetStringField(TEXT("blueprint_path_or_name"), BlueprintPathOrName) &&
        !Params->TryGetStringField(TEXT("blueprint_name"), BlueprintPathOrName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("Missing 'blueprint_path_or_name' parameter"));
    }

    UBlueprint* Blueprint = UnrealMCPEditorCommandDetail::LoadBlueprintByPathOrName(BlueprintPathOrName);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintPathOrName));
    }

    UClass* GeneratedClass = Blueprint->GeneratedClass;
    UClass* ParentClass = Blueprint->ParentClass;
    UObject* CDO = GeneratedClass ? GeneratedClass->GetDefaultObject(false) : nullptr;

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), GeneratedClass != nullptr);
    ResultObj->SetStringField(TEXT("query"), BlueprintPathOrName);
    ResultObj->SetStringField(TEXT("blueprint_name"), Blueprint->GetName());
    ResultObj->SetStringField(TEXT("blueprint_path"), Blueprint->GetPathName());
    ResultObj->SetBoolField(TEXT("has_generated_class"), GeneratedClass != nullptr);
    ResultObj->SetStringField(TEXT("generated_class_name"), GeneratedClass ? GeneratedClass->GetName() : TEXT(""));
    ResultObj->SetStringField(TEXT("generated_class_path"), GeneratedClass ? GeneratedClass->GetPathName() : TEXT(""));
    ResultObj->SetStringField(TEXT("parent_class_name"), ParentClass ? ParentClass->GetName() : TEXT(""));
    ResultObj->SetStringField(TEXT("parent_class_path"), ParentClass ? ParentClass->GetPathName() : TEXT(""));
    ResultObj->SetStringField(TEXT("class_default_object_path"), CDO ? CDO->GetPathName() : TEXT(""));
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleInspectInputMappingContext(const TSharedPtr<FJsonObject>& Params)
{
    FString IMCPathOrName;
    if (!Params->TryGetStringField(TEXT("imc_path_or_name"), IMCPathOrName) &&
        !Params->TryGetStringField(TEXT("imc_name"), IMCPathOrName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("Missing 'imc_path_or_name' parameter"));
    }

    UInputMappingContext* IMC =
        UnrealMCPEditorCommandDetail::LoadInputMappingContextByPathOrName(IMCPathOrName);
    if (!IMC)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Input Mapping Context not found: %s"), *IMCPathOrName));
    }

    TArray<TSharedPtr<FJsonValue>> MappingArray;
    const TArray<FEnhancedActionKeyMapping>& Mappings = IMC->GetMappings();
    for (int32 Index = 0; Index < Mappings.Num(); ++Index)
    {
        const FEnhancedActionKeyMapping& Mapping = Mappings[Index];
        TSharedPtr<FJsonObject> MappingObj = MakeShared<FJsonObject>();
        MappingObj->SetNumberField(TEXT("index"), Index);
        MappingObj->SetStringField(TEXT("action_name"), Mapping.Action ? Mapping.Action->GetName() : TEXT(""));
        MappingObj->SetStringField(TEXT("action_path"), Mapping.Action ? Mapping.Action->GetPathName() : TEXT(""));
        MappingObj->SetStringField(TEXT("key"), Mapping.Key.ToString());

        TArray<TSharedPtr<FJsonValue>> Modifiers;
        for (const UInputModifier* Modifier : Mapping.Modifiers)
        {
            Modifiers.Add(MakeShared<FJsonValueString>(
                Modifier && Modifier->GetClass() ? Modifier->GetClass()->GetName() : TEXT("")));
        }
        MappingObj->SetArrayField(TEXT("modifiers"), Modifiers);

        TArray<TSharedPtr<FJsonValue>> Triggers;
        for (const UInputTrigger* Trigger : Mapping.Triggers)
        {
            Triggers.Add(MakeShared<FJsonValueString>(
                Trigger && Trigger->GetClass() ? Trigger->GetClass()->GetName() : TEXT("")));
        }
        MappingObj->SetArrayField(TEXT("triggers"), Triggers);
        MappingArray.Add(MakeShared<FJsonValueObject>(MappingObj));
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("query"), IMCPathOrName);
    ResultObj->SetStringField(TEXT("name"), IMC->GetName());
    ResultObj->SetStringField(TEXT("path"), IMC->GetPathName());
    ResultObj->SetNumberField(TEXT("mapping_count"), MappingArray.Num());
    ResultObj->SetArrayField(TEXT("mappings"), MappingArray);
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleFocusViewport(const TSharedPtr<FJsonObject>& Params)
{
    // Get target actor name if provided
    FString TargetActorName;
    bool HasTargetActor = Params->TryGetStringField(TEXT("target"), TargetActorName);

    // Get location if provided
    FVector Location(0.0f, 0.0f, 0.0f);
    bool HasLocation = false;
    if (Params->HasField(TEXT("location")))
    {
        Location = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
        HasLocation = true;
    }

    // Get distance
    float Distance = 1000.0f;
    if (Params->HasField(TEXT("distance")))
    {
        Distance = Params->GetNumberField(TEXT("distance"));
    }

    // Get orientation if provided
    FRotator Orientation(0.0f, 0.0f, 0.0f);
    bool HasOrientation = false;
    if (Params->HasField(TEXT("orientation")))
    {
        Orientation = FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("orientation"));
        HasOrientation = true;
    }

    // ── Safely get the active viewport ──────────────────────────────────────
    // GEditor->GetActiveViewport() may return nullptr when no editor viewport
    // is focused (e.g. the Blueprint editor or another modal has focus).
    // Previously this caused a null-dereference → UE5 crash → GameThread hang.
    FLevelEditorViewportClient* ViewportClient = nullptr;
    if (GEditor && GEditor->GetActiveViewport())
    {
        ViewportClient = (FLevelEditorViewportClient*)GEditor->GetActiveViewport()->GetClient();
    }
    // If no viewport found via GetActiveViewport, try the level editor viewports
    if (!ViewportClient)
    {
        for (FLevelEditorViewportClient* LVC : GEditor->GetLevelViewportClients())
        {
            if (LVC)
            {
                ViewportClient = LVC;
                break;
            }
        }
    }
    if (!ViewportClient)
    {
        // Return a soft error (not a hard failure) so the test suite can continue.
        TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
        ResultObj->SetBoolField(TEXT("success"), false);
        ResultObj->SetStringField(TEXT("error"), TEXT("No active level viewport found. Open the level editor viewport and try again."));
        return ResultObj;
    }

    // ── Determine target location ────────────────────────────────────────────
    FVector FocusLocation = FVector::ZeroVector;

    if (HasTargetActor)
    {
        // Use FindActorByLabel/Name first (O(N) over all actors in world, but
        // terminates early on first match — much faster than GetAllActorsOfClass
        // on a 4256-actor world).
        AActor* TargetActor = nullptr;
        if (GWorld)
        {
            // TActorIterator provides early-exit (faster than GetAllActorsOfClass
            // which always fills the full array before returning).
            for (TActorIterator<AActor> It(GWorld); It; ++It)
            {
                AActor* A = *It;
                if (A && (A->GetName() == TargetActorName || A->GetActorLabel() == TargetActorName))
                {
                    TargetActor = A;
                    break;
                }
            }
        }

        if (!TargetActor)
        {
            TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
            ResultObj->SetBoolField(TEXT("success"), false);
            ResultObj->SetStringField(TEXT("error"),
                FString::Printf(TEXT("Actor not found: %s"), *TargetActorName));
            return ResultObj;
        }
        FocusLocation = TargetActor->GetActorLocation();
    }
    else if (HasLocation)
    {
        FocusLocation = Location;
    }
    else
    {
        // No target or location — just report success; caller may only want
        // to bring the viewport to the front without repositioning.
        TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
        ResultObj->SetBoolField(TEXT("success"), true);
        ResultObj->SetStringField(TEXT("note"), TEXT("No 'target' or 'location' provided; viewport was not moved."));
        return ResultObj;
    }

    // ── Position and orient the camera ──────────────────────────────────────
    ViewportClient->SetViewLocation(FocusLocation - FVector(Distance, 0.0f, 0.0f));

    if (HasOrientation)
    {
        ViewportClient->SetViewRotation(Orientation);
    }

    // Force viewport to redraw
    ViewportClient->Invalidate();

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleTakeScreenshot(const TSharedPtr<FJsonObject>& Params)
{
    // Get file path parameter
    FString FilePath;
    if (!Params->TryGetStringField(TEXT("filepath"), FilePath))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'filepath' parameter"));
    }
    
    // Ensure the file path has a proper extension
    if (!FilePath.EndsWith(TEXT(".png")))
    {
        FilePath += TEXT(".png");
    }

    // Get the active viewport
    if (GEditor && GEditor->GetActiveViewport())
    {
        FViewport* Viewport = GEditor->GetActiveViewport();
        TArray<FColor> Bitmap;
        FIntRect ViewportRect(0, 0, Viewport->GetSizeXY().X, Viewport->GetSizeXY().Y);
        
        if (Viewport->ReadPixels(Bitmap, FReadSurfaceDataFlags(), ViewportRect))
        {
            // UE5.6: PNGCompressImageArray requires TArray64<uint8> (64-bit allocator)
            TArray64<uint8> CompressedBitmap64;
            FImageUtils::PNGCompressImageArray(Viewport->GetSizeXY().X, Viewport->GetSizeXY().Y, Bitmap, CompressedBitmap64);
            // Convert to TArray<uint8> for SaveArrayToFile
            TArray<uint8> CompressedBitmap(CompressedBitmap64.GetData(), (int32)CompressedBitmap64.Num());
            
            if (FFileHelper::SaveArrayToFile(CompressedBitmap, *FilePath))
            {
                TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
                ResultObj->SetStringField(TEXT("filepath"), FilePath);
                return ResultObj;
            }
        }
    }
    
    return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to take screenshot"));
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleWorldPartitionLoadRegion(const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCPEditorCommandDetail;

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No active editor world"));
    }

    UWorldPartition* WorldPartition = World->GetWorldPartition();
    if (!WorldPartition)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Active world is not a World Partition world"));
    }

    const FBox RegionBox = ReadRegionBox(Params);
    if (!RegionBox.IsValid)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid region bounds"));
    }

    FString Label = TEXT("MCP Loaded Region");
    Params->TryGetStringField(TEXT("label"), Label);
    if (Label.IsEmpty())
    {
        Label = TEXT("MCP Loaded Region");
    }

    UWorldPartitionEditorLoaderAdapter* EditorLoaderAdapter =
        WorldPartition->CreateEditorLoaderAdapter<FLoaderAdapterShape>(World, RegionBox, Label);
    if (!EditorLoaderAdapter || !EditorLoaderAdapter->GetLoaderAdapter())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create World Partition loader adapter"));
    }

    IWorldPartitionActorLoaderInterface::ILoaderAdapter* LoaderAdapter = EditorLoaderAdapter->GetLoaderAdapter();
    LoaderAdapter->SetUserCreated(true);
    LoaderAdapter->Load();

    if (GEditor)
    {
        GEditor->RedrawLevelEditingViewports();
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("label"), Label);
    ResultObj->SetBoolField(TEXT("is_loaded"), LoaderAdapter->IsLoaded());
    ResultObj->SetObjectField(TEXT("region"), BoxToJson(RegionBox));
    ResultObj->SetStringField(TEXT("world"), World->GetPathName());
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleWorldPartitionUnloadRegion(const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCPEditorCommandDetail;

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No active editor world"));
    }

    UWorldPartition* WorldPartition = World->GetWorldPartition();
    if (!WorldPartition)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Active world is not a World Partition world"));
    }

    FString Label;
    Params->TryGetStringField(TEXT("label"), Label);

    bool bExact = false;
    Params->TryGetBoolField(TEXT("exact"), bExact);

    const bool bHasRegion = Params->HasField(TEXT("center")) || Params->HasField(TEXT("extent")) ||
        Params->HasField(TEXT("min")) || Params->HasField(TEXT("max"));
    const FBox RegionBox = bHasRegion ? ReadRegionBox(Params) : FBox(ForceInit);
    if (bHasRegion && !RegionBox.IsValid)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Invalid region bounds"));
    }

    if (Label.IsEmpty() && !bHasRegion)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Provide a loader 'label' or region bounds to unload"));
    }

    TArray<UWorldPartitionEditorLoaderAdapter*> MatchedAdapters;
    for (const TObjectPtr<UWorldPartitionEditorLoaderAdapter>& EditorLoaderAdapterPtr : WorldPartition->GetRegisteredEditorLoaderAdapters())
    {
        UWorldPartitionEditorLoaderAdapter* EditorLoaderAdapter = EditorLoaderAdapterPtr.Get();
        if (!EditorLoaderAdapter || !EditorLoaderAdapter->GetLoaderAdapter())
        {
            continue;
        }

        IWorldPartitionActorLoaderInterface::ILoaderAdapter* LoaderAdapter = EditorLoaderAdapter->GetLoaderAdapter();
        bool bMatches = true;

        if (!Label.IsEmpty())
        {
            const TOptional<FString> AdapterLabel = LoaderAdapter->GetLabel();
            bMatches = AdapterLabel.IsSet() && AdapterLabel.GetValue().Equals(Label, ESearchCase::IgnoreCase);
        }

        if (bMatches && bHasRegion)
        {
            const TOptional<FBox> AdapterBox = LoaderAdapter->GetBoundingBox();
            if (!AdapterBox.IsSet())
            {
                bMatches = false;
            }
            else if (bExact)
            {
                bMatches = AdapterBox.GetValue().Min.Equals(RegionBox.Min, 1.0) &&
                    AdapterBox.GetValue().Max.Equals(RegionBox.Max, 1.0);
            }
            else
            {
                bMatches = AdapterBox.GetValue().Intersect(RegionBox);
            }
        }

        if (bMatches)
        {
            MatchedAdapters.Add(EditorLoaderAdapter);
        }
    }

    TArray<FString> UnloadedLabels;
    for (UWorldPartitionEditorLoaderAdapter* EditorLoaderAdapter : MatchedAdapters)
    {
        IWorldPartitionActorLoaderInterface::ILoaderAdapter* LoaderAdapter = EditorLoaderAdapter->GetLoaderAdapter();
        if (LoaderAdapter)
        {
            const TOptional<FString> AdapterLabel = LoaderAdapter->GetLabel();
            UnloadedLabels.Add(AdapterLabel.IsSet() ? AdapterLabel.GetValue() : EditorLoaderAdapter->GetName());
            LoaderAdapter->Unload();
        }
        WorldPartition->ReleaseEditorLoaderAdapter(EditorLoaderAdapter);
    }

    if (GEditor)
    {
        GEditor->RedrawLevelEditingViewports();
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetNumberField(TEXT("unloaded_count"), MatchedAdapters.Num());
    ResultObj->SetArrayField(TEXT("unloaded_labels"), MakeStringArray(UnloadedLabels));
    if (bHasRegion)
    {
        ResultObj->SetObjectField(TEXT("region"), BoxToJson(RegionBox));
    }
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleWorldPartitionCreateDataLayer(const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCPEditorCommandDetail;

    FString Name;
    if (!Params->TryGetStringField(TEXT("name"), Name) || Name.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    FString Type = TEXT("runtime");
    Params->TryGetStringField(TEXT("type"), Type);
    const bool bRuntime = !Type.Equals(TEXT("editor"), ESearchCase::IgnoreCase);

    FString AssetPath;
    Params->TryGetStringField(TEXT("asset_path"), AssetPath);
    if (AssetPath.IsEmpty())
    {
        AssetPath = FString::Printf(TEXT("/Game/DataLayers/%s"), *Name);
    }
    AssetPath = NormalizeAssetPath(AssetPath);

    FString PackagePath;
    FString AssetName;
    if (!SplitPackagePath(AssetPath, PackagePath, AssetName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("asset_path must be under /Game and include an asset name"));
    }

    bool bPrivate = false;
    Params->TryGetBoolField(TEXT("private"), bPrivate);
    bool bInitiallyVisible = true;
    Params->TryGetBoolField(TEXT("initially_visible"), bInitiallyVisible);
    bool bLoadedInEditor = true;
    Params->TryGetBoolField(TEXT("loaded_in_editor"), bLoadedInEditor);
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    FString RuntimeStateText = TEXT("unloaded");
    Params->TryGetStringField(TEXT("initial_runtime_state"), RuntimeStateText);

    UDataLayerEditorSubsystem* DataLayerSubsystem = UDataLayerEditorSubsystem::Get();
    if (!DataLayerSubsystem)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Data Layer editor subsystem is unavailable"));
    }

    UDataLayerAsset* DataLayerAsset = Cast<UDataLayerAsset>(LoadAsset(AssetPath));
    bool bCreatedAsset = false;
    if (!DataLayerAsset)
    {
        IAssetTools& AssetTools = FModuleManager::GetModuleChecked<FAssetToolsModule>(TEXT("AssetTools")).Get();
        UDataLayerFactory* DataLayerFactory = NewObject<UDataLayerFactory>();
        UObject* CreatedAsset = AssetTools.CreateAsset(AssetName, PackagePath, UDataLayerAsset::StaticClass(), DataLayerFactory);
        DataLayerAsset = Cast<UDataLayerAsset>(CreatedAsset);
        bCreatedAsset = DataLayerAsset != nullptr;
    }

    if (!DataLayerAsset)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create or load Data Layer asset"));
    }

    DataLayerAsset->Modify();
    DataLayerAsset->SetType(bRuntime ? EDataLayerType::Runtime : EDataLayerType::Editor);

    UDataLayerInstance* DataLayerInstance = DataLayerSubsystem->GetDataLayerInstance(FName(*Name));
    bool bCreatedInstance = false;
    if (!DataLayerInstance)
    {
        FDataLayerCreationParameters CreationParams;
        CreationParams.DataLayerAsset = DataLayerAsset;
        CreationParams.bIsPrivate = bPrivate;
        DataLayerInstance = DataLayerSubsystem->CreateDataLayerInstance(CreationParams);
        bCreatedInstance = DataLayerInstance != nullptr;
    }

    if (!DataLayerInstance)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Data Layer instance"));
    }

    DataLayerSubsystem->SetDataLayerShortName(DataLayerInstance, Name);
    DataLayerSubsystem->SetDataLayerIsInitiallyVisible(DataLayerInstance, bInitiallyVisible);
    DataLayerSubsystem->SetDataLayerIsLoadedInEditor(DataLayerInstance, bLoadedInEditor, true);
    if (bRuntime)
    {
        DataLayerSubsystem->SetDataLayerInitialRuntimeState(DataLayerInstance, ParseRuntimeState(RuntimeStateText));
    }

    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(MakeObjectPath(AssetPath), false);
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetBoolField(TEXT("created_asset"), bCreatedAsset);
    ResultObj->SetBoolField(TEXT("created_instance"), bCreatedInstance);
    ResultObj->SetObjectField(TEXT("data_layer"), SummarizeDataLayer(DataLayerInstance, DataLayerAsset));
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleHLODGenerate(const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCPEditorCommandDetail;

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No active editor world"));
    }
    if (!World->GetWorldPartition())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Active world is not a World Partition world"));
    }

    bool bSetup = true;
    Params->TryGetBoolField(TEXT("setup"), bSetup);
    bool bBuild = true;
    Params->TryGetBoolField(TEXT("build"), bBuild);
    bool bDelete = false;
    Params->TryGetBoolField(TEXT("delete"), bDelete);
    bool bStats = false;
    Params->TryGetBoolField(TEXT("stats"), bStats);
    bool bForce = false;
    Params->TryGetBoolField(TEXT("force"), bForce);
    bool bReportOnly = false;
    Params->TryGetBoolField(TEXT("report_only"), bReportOnly);

    FString Layer;
    Params->TryGetStringField(TEXT("layer"), Layer);
    FString Actor;
    Params->TryGetStringField(TEXT("actor"), Actor);
    FString ExtraArgs;
    Params->TryGetStringField(TEXT("extra_args"), ExtraArgs);

    TArray<FString> BuilderArgs;
    BuilderArgs.Add(TEXT("-run=WorldPartitionBuilderCommandlet"));
    BuilderArgs.Add(World->GetPackage()->GetName());
    BuilderArgs.Add(TEXT("-Builder=WorldPartitionHLODsBuilder"));
    BuilderArgs.Add(TEXT("-AllowCommandletRendering"));
    BuilderArgs.Add(TEXT("-log=WorldPartitionHLODBuilderLog.txt"));
    if (bDelete)
    {
        BuilderArgs.Add(TEXT("-DeleteHLODs"));
    }
    if (bSetup)
    {
        BuilderArgs.Add(TEXT("-SetupHLODs"));
    }
    if (bBuild)
    {
        BuilderArgs.Add(bForce ? TEXT("-RebuildHLODs") : TEXT("-BuildHLODs"));
    }
    if (bStats)
    {
        BuilderArgs.Add(TEXT("-DumpStats"));
    }
    if (bReportOnly)
    {
        BuilderArgs.Add(TEXT("-ReportOnly"));
    }
    if (!Layer.IsEmpty())
    {
        BuilderArgs.Add(FString::Printf(TEXT("-BuildHLODLayer=%s"), *Layer));
    }
    if (!Actor.IsEmpty())
    {
        BuilderArgs.Add(FString::Printf(TEXT("-BuildSingleHLOD=%s"), *Actor));
    }
    if (!ExtraArgs.IsEmpty())
    {
        BuilderArgs.Add(ExtraArgs);
    }

    const FString ProjectFile = FPaths::ConvertRelativePathToFull(FPaths::GetProjectFilePath());
    if (ProjectFile.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Project file path is unavailable"));
    }

    FString CommandLineArguments = FString::Printf(TEXT("\"%s\" %s"), *ProjectFile, *FString::Join(BuilderArgs, TEXT(" ")));
    const FString MapPackage = World->GetPackage()->GetName();
    const bool bSuccess = FEditorBuildUtils::RunWorldPartitionBuilder(
        MapPackage,
        FText::FromString(TEXT("Running World Partition HLOD builder")),
        FText::FromString(TEXT("World Partition HLOD builder cancelled")),
        FText::FromString(TEXT("World Partition HLOD builder failed")),
        CommandLineArguments);

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), bSuccess);
    ResultObj->SetStringField(TEXT("map"), MapPackage);
    ResultObj->SetStringField(TEXT("command_line_arguments"), CommandLineArguments);
    ResultObj->SetArrayField(TEXT("builder_args"), MakeStringArray(BuilderArgs));
    return ResultObj;
}

TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleHLODAssignLayer(const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCPEditorCommandDetail;

    UWorld* World = GetEditorWorld();
    if (!World)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No active editor world"));
    }

    FString HLODLayerPath;
    if (!Params->TryGetStringField(TEXT("hlod_layer"), HLODLayerPath) || HLODLayerPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'hlod_layer' parameter"));
    }

    UHLODLayer* HLODLayer = Cast<UHLODLayer>(LoadAsset(HLODLayerPath));
    if (!HLODLayer)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("HLOD Layer asset not found: %s"), *HLODLayerPath));
    }

    TArray<FString> ActorQueries = GetStringArrayField(Params, TEXT("actors"));
    FString SingleActor;
    if (Params->TryGetStringField(TEXT("actor"), SingleActor) && !SingleActor.IsEmpty())
    {
        ActorQueries.Add(SingleActor);
    }

    TArray<AActor*> ActorsToUpdate;
    TArray<FString> MissingActors;
    for (const FString& ActorQuery : ActorQueries)
    {
        AActor* Actor = FindActorByNameOrLabel(World, ActorQuery);
        if (Actor)
        {
            ActorsToUpdate.Add(Actor);
        }
        else
        {
            MissingActors.Add(ActorQuery);
        }
    }

    if (ActorsToUpdate.Num() == 0 && ActorQueries.Num() == 0 && GEditor)
    {
        USelection* Selection = GEditor->GetSelectedActors();
        if (Selection)
        {
            for (FSelectionIterator It(*Selection); It; ++It)
            {
                if (AActor* Actor = Cast<AActor>(*It))
                {
                    ActorsToUpdate.Add(Actor);
                }
            }
        }
    }

    if (ActorsToUpdate.Num() == 0)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No target actors found; pass 'actors', 'actor', or select actors in the editor"));
    }

    TArray<FString> AssignedActors;
    for (AActor* Actor : ActorsToUpdate)
    {
        if (!Actor)
        {
            continue;
        }
        Actor->Modify();
        Actor->SetHLODLayer(HLODLayer);
        AssignedActors.Add(Actor->GetActorLabel());
    }

    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), true);
    ResultObj->SetStringField(TEXT("hlod_layer"), HLODLayer->GetPathName());
    ResultObj->SetNumberField(TEXT("assigned_count"), AssignedActors.Num());
    ResultObj->SetArrayField(TEXT("assigned_actors"), MakeStringArray(AssignedActors));
    ResultObj->SetArrayField(TEXT("missing_actors"), MakeStringArray(MissingActors));
    return ResultObj;
}

// ?????????????????????????????????????????????????????????????????????????????
// exec_python ? execute arbitrary Python code inside the UE editor context
//
// Request params:
//   code        (string, required) ? the Python source to execute.
//               Multi-line code must use \n as line separator.
//   mode        (string, optional) ? execution mode:
//                 "execute_file"      (default) run as a script / file
//                 "execute_statement" run a single statement (prints result)
//                 "evaluate_statement" evaluate an expression, return its value
//
// Response fields on success:
//   output      (string) ? captured log output from the Python run
//   result      (string) ? expression result (only for evaluate_statement mode)
//   success     (bool)   ? true
//
// Response on failure:
//   error       (string) ? Python traceback / error description
//   success     (bool)   ? false
// ?????????????????????????????????????????????????????????????????????????????
TSharedPtr<FJsonObject> FUnrealMCPEditorCommands::HandleExecPython(const TSharedPtr<FJsonObject>& Params)
{
    // ?? 1. Check that Python scripting is available ???????????????????????????
    IPythonScriptPlugin* PythonPlugin = IPythonScriptPlugin::Get();
    if (!PythonPlugin || !PythonPlugin->IsPythonAvailable())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("Python scripting is not available. Enable the 'Python Editor Script Plugin' in Edit ? Plugins."));
    }

    // ?? 2. Get required 'code' parameter ????????????????????????????????????
    FString Code;
    if (!Params->TryGetStringField(TEXT("code"), Code))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'code' parameter"));
    }

    if (Code.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("'code' parameter must not be empty"));
    }

    // Hard cap: huge scripts blow up the repr-wrapper, Python lexer, and editor observers.
    constexpr int32 MaxExecPythonChars = 384 * 1024;
    if (Code.Len() > MaxExecPythonChars)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(
            TEXT("code too large (%d chars, max %d). Split into multiple exec_python calls or use native MCP commands."),
            Code.Len(), MaxExecPythonChars));
    }

    // ?? 3. Parse optional 'mode' parameter ??????????????????????????????????
    //  "execute_file"      ? EPythonCommandExecutionMode::ExecuteFile      (default)
    //  "execute_statement" ? EPythonCommandExecutionMode::ExecuteStatement
    //  "evaluate_statement"? EPythonCommandExecutionMode::EvaluateStatement
    FString ModeStr;
    Params->TryGetStringField(TEXT("mode"), ModeStr);

    EPythonCommandExecutionMode ExecMode = EPythonCommandExecutionMode::ExecuteFile;
    if (ModeStr == TEXT("execute_statement"))
    {
        ExecMode = EPythonCommandExecutionMode::ExecuteStatement;
    }
    else if (ModeStr == TEXT("evaluate_statement"))
    {
        ExecMode = EPythonCommandExecutionMode::EvaluateStatement;
    }
    // else default: execute_file (runs multi-line scripts)

    UE_LOG(LogTemp, Display, TEXT("exec_python: running mode=%s, code length=%d"),
           *ModeStr, Code.Len());

    // ?? 4. Execute ????????????????????????????????????????????????????????????
    // ?? 4a. Wrap user code so ALL Python exceptions (including SyntaxError)
    //        are caught and returned as clean error JSON instead of hanging.
    //
    // Problem with simple try/except indentation:
    //   Python compiles the entire try-block before executing it.
    //   A SyntaxError in the user code fires at compile time — BEFORE
    //   the try/except is entered — so it leaks out of the wrapper.
    //
    // Solution: repr() the user code into a string variable (_mcp_src),
    //   then call compile() + exec() inside the try/except.
    //   compile() raises SyntaxError as a regular exception, so it IS caught.
    //
    // Template (Python) — error stored silently in builtins._mcp_last_error:
    //   import traceback as _mcp_tb
    //   import builtins as _mcp_bi
    //   _mcp_bi._mcp_last_error = ''
    //   _mcp_src = <repr(Code)>
    //   try:
    //       exec(compile(_mcp_src, '<mcp_exec>', 'exec'))
    //   except Exception:
    //       _mcp_bi._mcp_last_error = '__MCP_ERR__' + _mcp_tb.format_exc()
    //
    // After ExecPythonCommandEx returns, C++ reads builtins._mcp_last_error
    // via a fast EvaluateStatement call.  If it starts with '__MCP_ERR__',
    // success=false with the traceback as error detail.
    // This avoids the 20-30 s GLog flush that print() or raise would cause.

    FString WrappedCode;
    if (ExecMode == EPythonCommandExecutionMode::EvaluateStatement)
    {
        // evaluate_statement: single expression, errors surface via bOk=false
        WrappedCode = Code;
    }
    else
    {
        // Build a Python repr() of the code string so it is safe to embed
        // in a Python script regardless of quotes, backslashes, or newlines.
        // Strategy: escape backslashes, then escape single quotes, then wrap
        // in single quotes.  This matches Python's repr() for typical code.
        FString Escaped = Code;
        Escaped.ReplaceInline(TEXT("\\"), TEXT("\\\\"), ESearchCase::CaseSensitive);
        Escaped.ReplaceInline(TEXT("'"),  TEXT("\\'"),  ESearchCase::CaseSensitive);
        // Newlines inside the repr string must stay as \n (escaped)
        Escaped.ReplaceInline(TEXT("\r\n"), TEXT("\\n"), ESearchCase::CaseSensitive);
        Escaped.ReplaceInline(TEXT("\n"),   TEXT("\\n"), ESearchCase::CaseSensitive);
        Escaped.ReplaceInline(TEXT("\r"),   TEXT("\\n"), ESearchCase::CaseSensitive);

        // Error-capture strategy: store traceback in a module-level variable
        // (_mcp_last_error) instead of print()ing or raising.
        //
        // WHY NOT print():
        //   print() routes through UE5's GLog which flushes all log listeners
        //   synchronously.  On large projects with many AR / ContentBrowser
        //   listeners this blocks 20-30 s even for a one-line ZeroDivisionError.
        //
        // WHY NOT raise SystemExit():
        //   SystemExit propagates out of ExecPythonCommandEx and triggers the
        //   same slow UE5 error-formatting / log pipeline before returning bOk=false.
        //
        // SOLUTION: catch the exception silently, store the traceback in the
        // well-known global variable _mcp_last_error (a module-level attribute),
        // and return normally (bOk=true, zero log I/O).  The C++ side checks
        // whether Command.CommandResult starts with "__MCP_ERR__" after execution.
        //
        // The wrapper sets _mcp_last_error to "" on entry (success case) and
        // to "__MCP_ERR__<traceback>" on exception.  C++ reads CommandResult
        // via the EvaluateStatement round-trip below.
        WrappedCode = FString::Printf(
            TEXT("import traceback as _mcp_tb\n")
            TEXT("import builtins as _mcp_bi\n")
            TEXT("_mcp_bi._mcp_last_error = ''\n")
            TEXT("_mcp_src = '%s'\n")
            TEXT("try:\n")
            TEXT("    exec(compile(_mcp_src, '<mcp_exec>', 'exec'))\n")
            TEXT("except Exception:\n")
            TEXT("    _mcp_bi._mcp_last_error = '__MCP_ERR__' + _mcp_tb.format_exc()\n"),
            *Escaped
        );
    }

    FPythonCommandEx Command;
    Command.Command  = WrappedCode;
    // ── IMPORTANT: always use ExecuteFile mode for our wrapper script. ──────
    // ExecuteStatement mode uses Py_single_input which only accepts ONE
    // statement and truncates multi-line scripts silently.
    // ExecuteFile mode (Py_file_input) handles the full multi-line wrapper
    // including the try/except block.
    // For EvaluateStatement we already set WrappedCode = Code (no wrapper),
    // so using its original ExecMode is correct.
    Command.ExecutionMode = (ExecMode == EPythonCommandExecutionMode::EvaluateStatement)
        ? ExecMode
        : EPythonCommandExecutionMode::ExecuteFile;
    Command.FileExecutionScope = EPythonFileExecutionScope::Public; // share globals/locals with console

    // NOTE: UE 5.6+ no longer ships a stable public `EditorScriptExecutionGuard.h` on all
    // installs; notification batching was removed here. SEH below is the primary guard.

    bool bSehCrashMain = false;
    const bool bOk = UnrealMCPExecPythonDetail::ExecPythonWithSeh(PythonPlugin, Command, bSehCrashMain);
    if (bSehCrashMain)
    {
        TSharedPtr<FJsonObject> CrashObj = MakeShared<FJsonObject>();
        CrashObj->SetBoolField(TEXT("success"), false);
        CrashObj->SetStringField(TEXT("output"), TEXT(""));
        CrashObj->SetStringField(TEXT("command_result"), TEXT(""));
        CrashObj->SetStringField(
            TEXT("error"),
            TEXT("exec_python: native access violation inside ExecPythonCommandEx (often EditorScriptingUtilities / "
                 "MassEntityEditor observers on synchronous asset work). The crash was caught — split the script into "
                 "smaller exec_python payloads and prefer MCP compile_blueprint / save_blueprint / add_component."));
        UE_LOG(LogTemp, Error, TEXT("[MCP] exec_python SEH crash (main ExecPythonCommandEx)"));
        return CrashObj;
    }

    // ── Detect Python exceptions ──────────────────────────────────────────
    // The wrapper stores errors silently in builtins._mcp_last_error to
    // avoid the slow GLog flush caused by print() or raise.
    // After execution, read that variable via a fast EvaluateStatement call.
    bool bHasPythonError = false;
    FString PythonErrorDetail;

    if (bOk)
    {
        // Fast path: read the error variable without any log I/O.
        FPythonCommandEx ReadCmd;
        ReadCmd.Command       = TEXT("getattr(__import__('builtins'), '_mcp_last_error', '')");
        ReadCmd.ExecutionMode = EPythonCommandExecutionMode::EvaluateStatement;
        ReadCmd.FileExecutionScope = EPythonFileExecutionScope::Public;
        bool bSehCrashRead = false;
        const bool bReadOk =
            UnrealMCPExecPythonDetail::ExecPythonWithSeh(PythonPlugin, ReadCmd, bSehCrashRead);
        if (bSehCrashRead)
        {
            bHasPythonError  = true;
            PythonErrorDetail =
                TEXT("exec_python: SEH crash while reading _mcp_last_error after main run (Python interpreter unstable).");
        }
        else if (bReadOk && ReadCmd.CommandResult.StartsWith(TEXT("__MCP_ERR__")))
        {
            bHasPythonError  = true;
            PythonErrorDetail = ReadCmd.CommandResult.Mid(11); // strip "__MCP_ERR__" prefix
        }
    }
    else
    {
        // bOk=false: UE5's Python runner itself errored (e.g. plugin not loaded,
        // or the wrapper script itself has a syntax error — should never happen).
        bHasPythonError  = true;
        PythonErrorDetail = Command.CommandResult;
    }

    // ?? 5. Collect log output ????????????????????????????????????????????????????
    FString LogOutput;
    for (const FPythonLogOutputEntry& Entry : Command.LogOutput)
    {
        FString Prefix;
        switch (Entry.Type)
        {
            case EPythonLogOutputType::Info:    Prefix = TEXT("[Info] ");    break;
            case EPythonLogOutputType::Warning: Prefix = TEXT("[Warning] "); break;
            case EPythonLogOutputType::Error:   Prefix = TEXT("[Error] ");   break;
            default:                            Prefix = TEXT("[Log] ");     break;
        }
        LogOutput += Prefix + Entry.Output + TEXT("\n");
    }
    LogOutput = LogOutput.TrimEnd();
    PythonErrorDetail = PythonErrorDetail.TrimEnd();

    // Determine overall success: C++ bOk AND no Python-level exception
    const bool bFinalOk = bOk && !bHasPythonError;

    // ?? 6. Build response ?????????????????????????????????????????????????????
    TSharedPtr<FJsonObject> ResultObj = MakeShared<FJsonObject>();
    ResultObj->SetBoolField(TEXT("success"), bFinalOk);
    ResultObj->SetStringField(TEXT("output"), LogOutput);
    ResultObj->SetStringField(TEXT("command_result"), Command.CommandResult);

    if (!bFinalOk)
    {
        // Surface the most informative error detail available.
        // Priority: Python wrapper traceback (from _mcp_last_error) > C++ CommandResult > LogOutput
        FString ErrorDetail;
        if (bHasPythonError && !PythonErrorDetail.IsEmpty())
        {
            ErrorDetail = PythonErrorDetail; // already stripped of __MCP_ERR__ prefix
        }
        else if (!Command.CommandResult.IsEmpty())
        {
            ErrorDetail = Command.CommandResult;
        }
        else
        {
            ErrorDetail = LogOutput;
        }
        ResultObj->SetStringField(TEXT("error"), ErrorDetail);
        UE_LOG(LogTemp, Error, TEXT("[MCP] exec_python failed: %s"), *ErrorDetail);
    }
    else
    {
        UE_LOG(LogTemp, Display, TEXT("exec_python succeeded. result=%s"), *Command.CommandResult);
    }

    return ResultObj;
}
