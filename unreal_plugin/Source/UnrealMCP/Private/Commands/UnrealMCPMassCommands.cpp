#include "Commands/UnrealMCPMassCommands.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Commands/UnrealMCPCommonUtils.h"
#include "Dom/JsonValue.h"
#include "Editor.h"
#include "EditorAssetLibrary.h"
#include "Engine/World.h"
#include "GameplayTagContainer.h"
#include "GameplayTagsManager.h"
#include "MassEntityConfigAsset.h"
#include "MassEntityTraitBase.h"
#include "Misc/ScopedSlowTask.h"
#include "ScopedTransaction.h"
#include "SmartObjectDefinition.h"
#include "StateTree.h"
#include "StateTreeEditorData.h"
#include "StateTreeFactory.h"
#include "StateTreeSchema.h"
#include "StateTreeState.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "UObject/UObjectIterator.h"

FUnrealMCPMassCommands::FUnrealMCPMassCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("mass_create_entity_config")) return HandleMassCreateEntityConfig(Params);
    if (CommandType == TEXT("mass_add_trait")) return HandleMassAddTrait(Params);
    if (CommandType == TEXT("mass_inspect_entity_config")) return HandleMassInspectEntityConfig(Params);
    if (CommandType == TEXT("statetree_create")) return HandleStateTreeCreate(Params);
    if (CommandType == TEXT("statetree_add_state")) return HandleStateTreeAddState(Params);
    if (CommandType == TEXT("statetree_inspect")) return HandleStateTreeInspect(Params);
    if (CommandType == TEXT("smartobject_create_definition")) return HandleSmartObjectCreateDefinition(Params);
    if (CommandType == TEXT("smartobject_add_slot")) return HandleSmartObjectAddSlot(Params);
    if (CommandType == TEXT("smartobject_inspect_definition")) return HandleSmartObjectInspectDefinition(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown Mass/StateTree/SmartObject command: %s"), *CommandType));
}

FString FUnrealMCPMassCommands::NormalizeAssetPath(const FString& InPath) const
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

FString FUnrealMCPMassCommands::MakeObjectPath(const FString& AssetPath) const
{
    const FString CleanPath = NormalizeAssetPath(AssetPath);
    return FString::Printf(TEXT("%s.%s"), *CleanPath, *FPaths::GetBaseFilename(CleanPath));
}

bool FUnrealMCPMassCommands::SplitPackagePath(const FString& AssetPath, FString& OutPackagePath, FString& OutAssetName) const
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

UObject* FUnrealMCPMassCommands::LoadAsset(const FString& AssetOrObjectPath) const
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

UClass* FUnrealMCPMassCommands::ResolveClass(const FString& ClassName, UClass* RequiredBaseClass) const
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
            if (!Candidate)
            {
                continue;
            }
            const FString CandidateName = Candidate->GetName();
            if (CandidateName == Query || CandidateName == ShortQuery ||
                CandidateName.EndsWith(TEXT(".") + Query) || Candidate->GetPathName() == Query)
            {
                FoundClass = Candidate;
                break;
            }
        }
    }

    if (!FoundClass || !FoundClass->IsChildOf(RequiredBaseClass) || FoundClass->HasAnyClassFlags(CLASS_Abstract))
    {
        return nullptr;
    }
    return FoundClass;
}

TArray<FString> FUnrealMCPMassCommands::GetStringArrayField(const TSharedPtr<FJsonObject>& Params, const FString& FieldName) const
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

TArray<TSharedPtr<FJsonValue>> FUnrealMCPMassCommands::MakeStringArray(const TArray<FString>& Values) const
{
    TArray<TSharedPtr<FJsonValue>> JsonValues;
    for (const FString& Value : Values)
    {
        JsonValues.Add(MakeShared<FJsonValueString>(Value));
    }
    return JsonValues;
}

TArray<TSharedPtr<FJsonValue>> FUnrealMCPMassCommands::MakeVectorArray(const FVector& Value) const
{
    TArray<TSharedPtr<FJsonValue>> JsonValues;
    JsonValues.Add(MakeShared<FJsonValueNumber>(Value.X));
    JsonValues.Add(MakeShared<FJsonValueNumber>(Value.Y));
    JsonValues.Add(MakeShared<FJsonValueNumber>(Value.Z));
    return JsonValues;
}

TArray<TSharedPtr<FJsonValue>> FUnrealMCPMassCommands::MakeRotatorArray(const FRotator& Value) const
{
    TArray<TSharedPtr<FJsonValue>> JsonValues;
    JsonValues.Add(MakeShared<FJsonValueNumber>(Value.Pitch));
    JsonValues.Add(MakeShared<FJsonValueNumber>(Value.Yaw));
    JsonValues.Add(MakeShared<FJsonValueNumber>(Value.Roll));
    return JsonValues;
}

UWorld* FUnrealMCPMassCommands::GetEditorWorld() const
{
    return GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::SummarizeMassConfig(UMassEntityConfigAsset* ConfigAsset, bool bValidate) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), ConfigAsset != nullptr);
    Result->SetStringField(TEXT("stage"), TEXT("mass_inspect_entity_config"));
    if (!ConfigAsset)
    {
        return Result;
    }

    const FMassEntityConfig& Config = ConfigAsset->GetConfig();
    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(ConfigAsset->GetPathName()));
    Result->SetStringField(TEXT("object_path"), ConfigAsset->GetPathName());
    Result->SetStringField(TEXT("config_guid"), Config.GetGuid().ToString(EGuidFormats::DigitsWithHyphens));
    Result->SetStringField(TEXT("parent_config"), Config.GetParent() ? Config.GetParent()->GetPathName() : TEXT(""));

    TArray<FString> TraitNames;
    TArray<TSharedPtr<FJsonValue>> TraitObjects;
    for (UMassEntityTraitBase* Trait : Config.GetTraits())
    {
        if (!Trait)
        {
            continue;
        }
        TraitNames.Add(Trait->GetClass()->GetName());
        TSharedPtr<FJsonObject> TraitObject = MakeShared<FJsonObject>();
        TraitObject->SetStringField(TEXT("name"), Trait->GetClass()->GetName());
        TraitObject->SetStringField(TEXT("class"), Trait->GetClass()->GetPathName());
        TraitObject->SetStringField(TEXT("object_path"), Trait->GetPathName());
        TraitObjects.Add(MakeShared<FJsonValueObject>(TraitObject));
    }
    Result->SetNumberField(TEXT("trait_count"), TraitNames.Num());
    Result->SetArrayField(TEXT("traits"), MakeStringArray(TraitNames));
    Result->SetArrayField(TEXT("trait_details"), TraitObjects);

    if (bValidate)
    {
        if (UWorld* World = GetEditorWorld())
        {
            Result->SetBoolField(TEXT("validation_available"), true);
            Result->SetBoolField(TEXT("validation_passed"), ConfigAsset->GetMutableConfig().ValidateEntityTemplate(*World));
        }
        else
        {
            Result->SetBoolField(TEXT("validation_available"), false);
            Result->SetBoolField(TEXT("validation_passed"), false);
        }
    }
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleMassCreateEntityConfig(const TSharedPtr<FJsonObject>& Params)
{
    FString Name;
    Params->TryGetStringField(TEXT("name"), Name);
    FString Path = TEXT("/Game/Mass/EntityConfigs");
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
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("MassEntity config path must be under /Game"));
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

    FScopedSlowTask SlowTask(2.0f, FText::FromString(TEXT("MCP Create MassEntity Config")));
    SlowTask.MakeDialog(false);
    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Create MassEntity Config")));
    SlowTask.EnterProgressFrame(1.0f, FText::FromString(TEXT("Creating MassEntity config asset")));

    UEditorAssetLibrary::MakeDirectory(PackagePath);
    UPackage* Package = CreatePackage(*AssetPath);
    UMassEntityConfigAsset* ConfigAsset = NewObject<UMassEntityConfigAsset>(
        Package,
        *AssetName,
        RF_Public | RF_Standalone | RF_Transactional);
    if (!ConfigAsset)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create MassEntity config asset"));
    }

    FString ParentConfigPath;
    Params->TryGetStringField(TEXT("parent_config"), ParentConfigPath);
    if (!ParentConfigPath.IsEmpty())
    {
        UMassEntityConfigAsset* ParentConfig = Cast<UMassEntityConfigAsset>(LoadAsset(ParentConfigPath));
        if (!ParentConfig)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load parent_config: %s"), *ParentConfigPath));
        }
        ConfigAsset->GetMutableConfig().SetParentAsset(*ParentConfig);
    }

    TArray<FString> AddedTraits;
    for (const FString& TraitName : GetStringArrayField(Params, TEXT("traits")))
    {
        UClass* TraitClass = ResolveClass(TraitName, UMassEntityTraitBase::StaticClass());
        if (!TraitClass)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not resolve MassEntity trait class: %s"), *TraitName));
        }
        if (UMassEntityTraitBase* Trait = ConfigAsset->AddTrait(TraitClass))
        {
            AddedTraits.Add(Trait->GetClass()->GetName());
        }
    }

    SlowTask.EnterProgressFrame(1.0f, FText::FromString(TEXT("Registering MassEntity config asset")));
    ConfigAsset->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(ConfigAsset);

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ObjectPath, false);
    }

    TSharedPtr<FJsonObject> Result = SummarizeMassConfig(ConfigAsset, false);
    Result->SetStringField(TEXT("stage"), TEXT("mass_create_entity_config"));
    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(AssetPath));
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    Result->SetArrayField(TEXT("added_traits"), MakeStringArray(AddedTraits));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleMassAddTrait(const TSharedPtr<FJsonObject>& Params)
{
    FString ConfigPath;
    FString TraitName;
    Params->TryGetStringField(TEXT("config_asset"), ConfigPath);
    Params->TryGetStringField(TEXT("trait_class"), TraitName);
    if (ConfigPath.IsEmpty() || TraitName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'config_asset' or 'trait_class' parameter"));
    }

    UMassEntityConfigAsset* ConfigAsset = Cast<UMassEntityConfigAsset>(LoadAsset(ConfigPath));
    UClass* TraitClass = ResolveClass(TraitName, UMassEntityTraitBase::StaticClass());
    if (!ConfigAsset)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load MassEntity config: %s"), *ConfigPath));
    }
    if (!TraitClass)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not resolve MassEntity trait class: %s"), *TraitName));
    }

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Add MassEntity Trait")));
    ConfigAsset->Modify();
    UMassEntityTraitBase* AddedTrait = ConfigAsset->AddTrait(TraitClass);
    ConfigAsset->MarkPackageDirty();

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ConfigAsset->GetPathName(), false);
    }

    TSharedPtr<FJsonObject> Result = SummarizeMassConfig(ConfigAsset, false);
    Result->SetStringField(TEXT("stage"), TEXT("mass_add_trait"));
    Result->SetStringField(TEXT("added_trait"), AddedTrait ? AddedTrait->GetClass()->GetPathName() : TraitClass->GetPathName());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleMassInspectEntityConfig(const TSharedPtr<FJsonObject>& Params)
{
    FString ConfigPath;
    Params->TryGetStringField(TEXT("config_asset"), ConfigPath);
    if (ConfigPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'config_asset' parameter"));
    }
    UMassEntityConfigAsset* ConfigAsset = Cast<UMassEntityConfigAsset>(LoadAsset(ConfigPath));
    if (!ConfigAsset)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load MassEntity config: %s"), *ConfigPath));
    }

    bool bValidate = false;
    Params->TryGetBoolField(TEXT("validate"), bValidate);
    return SummarizeMassConfig(ConfigAsset, bValidate);
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleStateTreeCreate(const TSharedPtr<FJsonObject>& Params)
{
    FString Name;
    Params->TryGetStringField(TEXT("name"), Name);
    FString Path = TEXT("/Game/AI/StateTrees");
    Params->TryGetStringField(TEXT("path"), Path);
    if (Name.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }
    if (!Path.StartsWith(TEXT("/Game")))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("StateTree path must be under /Game"));
    }

    Path.RemoveFromEnd(TEXT("/"));
    const FString AssetPath = FString::Printf(TEXT("%s/%s"), *Path, *Name);
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

    FString SchemaName = TEXT("/Script/GameplayStateTreeModule.StateTreeComponentSchema");
    Params->TryGetStringField(TEXT("schema_class"), SchemaName);
    UClass* SchemaClass = ResolveClass(SchemaName, UStateTreeSchema::StaticClass());
    if (!SchemaClass)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not resolve StateTree schema class: %s"), *SchemaName));
    }

    FScopedSlowTask SlowTask(2.0f, FText::FromString(TEXT("MCP Create StateTree")));
    SlowTask.MakeDialog(false);
    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Create StateTree")));
    UEditorAssetLibrary::MakeDirectory(Path);

    UStateTreeFactory* Factory = NewObject<UStateTreeFactory>();
    TObjectPtr<UClass> SchemaPtr = SchemaClass;
    Factory->SetSchemaClass(SchemaPtr);
    UObject* NewAsset = Factory->FactoryCreateNew(
        UStateTree::StaticClass(),
        CreatePackage(*AssetPath),
        *Name,
        RF_Public | RF_Standalone | RF_Transactional,
        nullptr,
        GWarn);
    UStateTree* StateTree = Cast<UStateTree>(NewAsset);
    if (!StateTree)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create StateTree asset"));
    }

    StateTree->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(StateTree);
    StateTree->CompileIfChanged();

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ObjectPath, false);
    }

    TSharedPtr<FJsonObject> Result = SummarizeStateTree(StateTree);
    Result->SetStringField(TEXT("stage"), TEXT("statetree_create"));
    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(AssetPath));
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    return Result;
}

UStateTreeState* FUnrealMCPMassCommands::FindState(UStateTreeEditorData* EditorData, const FString& StateNameOrID) const
{
    if (!EditorData || StateNameOrID.IsEmpty())
    {
        return nullptr;
    }

    TArray<UStateTreeState*> Stack;
    for (UStateTreeState* SubTree : EditorData->SubTrees)
    {
        if (SubTree)
        {
            Stack.Add(SubTree);
        }
    }
    while (!Stack.IsEmpty())
    {
        UStateTreeState* State = Stack.Pop(EAllowShrinking::No);
        if (!State)
        {
            continue;
        }
        if (State->Name.ToString() == StateNameOrID ||
            State->ID.ToString(EGuidFormats::DigitsWithHyphens) == StateNameOrID ||
            State->ID.ToString(EGuidFormats::Digits) == StateNameOrID)
        {
            return State;
        }
        for (UStateTreeState* Child : State->Children)
        {
            if (Child)
            {
                Stack.Add(Child);
            }
        }
    }
    return nullptr;
}

static EStateTreeStateType ParseStateType(const FString& StateTypeName)
{
    const FString Lower = StateTypeName.ToLower();
    if (Lower == TEXT("group")) return EStateTreeStateType::Group;
    if (Lower == TEXT("linked")) return EStateTreeStateType::Linked;
    if (Lower == TEXT("linked_asset")) return EStateTreeStateType::LinkedAsset;
    if (Lower == TEXT("subtree")) return EStateTreeStateType::Subtree;
    return EStateTreeStateType::State;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleStateTreeAddState(const TSharedPtr<FJsonObject>& Params)
{
    FString StateTreePath;
    FString Name;
    Params->TryGetStringField(TEXT("state_tree"), StateTreePath);
    Params->TryGetStringField(TEXT("name"), Name);
    if (StateTreePath.IsEmpty() || Name.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'state_tree' or 'name' parameter"));
    }

    UStateTree* StateTree = Cast<UStateTree>(LoadAsset(StateTreePath));
    if (!StateTree)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load StateTree: %s"), *StateTreePath));
    }
    UStateTreeEditorData* EditorData = Cast<UStateTreeEditorData>(StateTree->EditorData);
    if (!EditorData)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("StateTree has no editor data"));
    }

    FString StateTypeName = TEXT("state");
    Params->TryGetStringField(TEXT("state_type"), StateTypeName);
    bool bAsSubTree = false;
    Params->TryGetBoolField(TEXT("as_subtree"), bAsSubTree);
    bool bEnabled = true;
    Params->TryGetBoolField(TEXT("enabled"), bEnabled);
    FString Description;
    Params->TryGetStringField(TEXT("description"), Description);

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Add StateTree State")));
    StateTree->Modify();
    EditorData->Modify();

    UStateTreeState* NewState = nullptr;
    if (bAsSubTree || EditorData->SubTrees.Num() == 0)
    {
        NewState = &EditorData->AddSubTree(FName(*Name));
    }
    else
    {
        FString ParentStateName;
        Params->TryGetStringField(TEXT("parent_state"), ParentStateName);
        UStateTreeState* ParentState = FindState(EditorData, ParentStateName);
        if (!ParentState && EditorData->SubTrees.Num() > 0)
        {
            ParentState = EditorData->SubTrees[0];
        }
        if (!ParentState)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Could not find a parent StateTree state"));
        }
        ParentState->Modify();
        NewState = &ParentState->AddChildState(FName(*Name), ParseStateType(StateTypeName));
    }

    if (!NewState)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to add StateTree state"));
    }
    NewState->Modify();
    NewState->ID = FGuid::NewGuid();
    NewState->Description = Description;
    NewState->bEnabled = bEnabled;
    if (bAsSubTree)
    {
        NewState->Type = EStateTreeStateType::Subtree;
    }

    StateTree->CompileIfChanged();
    StateTree->MarkPackageDirty();

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(StateTree->GetPathName(), false);
    }

    TSharedPtr<FJsonObject> Result = SummarizeStateTree(StateTree);
    Result->SetStringField(TEXT("stage"), TEXT("statetree_add_state"));
    Result->SetStringField(TEXT("added_state"), NewState->Name.ToString());
    Result->SetStringField(TEXT("added_state_id"), NewState->ID.ToString(EGuidFormats::DigitsWithHyphens));
    return Result;
}

void FUnrealMCPMassCommands::AppendStateSummary(UStateTreeState* State, TArray<TSharedPtr<FJsonValue>>& OutStates, int32 Depth) const
{
    if (!State)
    {
        return;
    }

    TSharedPtr<FJsonObject> StateObject = MakeShared<FJsonObject>();
    StateObject->SetStringField(TEXT("name"), State->Name.ToString());
    StateObject->SetStringField(TEXT("id"), State->ID.ToString(EGuidFormats::DigitsWithHyphens));
    StateObject->SetStringField(TEXT("description"), State->Description);
    StateObject->SetStringField(TEXT("type"), StaticEnum<EStateTreeStateType>()->GetNameStringByValue(static_cast<int64>(State->Type)));
    StateObject->SetBoolField(TEXT("enabled"), State->bEnabled);
    StateObject->SetNumberField(TEXT("depth"), Depth);
    StateObject->SetNumberField(TEXT("child_count"), State->Children.Num());
    OutStates.Add(MakeShared<FJsonValueObject>(StateObject));

    for (UStateTreeState* Child : State->Children)
    {
        AppendStateSummary(Child, OutStates, Depth + 1);
    }
}

int32 FUnrealMCPMassCommands::CountEditorStates(UStateTreeEditorData* EditorData) const
{
    if (!EditorData)
    {
        return 0;
    }

    TArray<TSharedPtr<FJsonValue>> States;
    for (UStateTreeState* SubTree : EditorData->SubTrees)
    {
        AppendStateSummary(SubTree, States, 0);
    }
    return States.Num();
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::SummarizeStateTree(UStateTree* StateTree) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), StateTree != nullptr);
    Result->SetStringField(TEXT("stage"), TEXT("statetree_inspect"));
    if (!StateTree)
    {
        return Result;
    }

    UStateTreeEditorData* EditorData = Cast<UStateTreeEditorData>(StateTree->EditorData);
    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(StateTree->GetPathName()));
    Result->SetStringField(TEXT("object_path"), StateTree->GetPathName());
    Result->SetBoolField(TEXT("ready_to_run"), StateTree->IsReadyToRun());
    Result->SetNumberField(TEXT("compiled_state_count"), StateTree->GetStates().Num());
    Result->SetNumberField(TEXT("editor_state_count"), CountEditorStates(EditorData));
    Result->SetBoolField(TEXT("has_editor_data"), EditorData != nullptr);
    Result->SetStringField(TEXT("schema_class"), EditorData && EditorData->Schema ? EditorData->Schema->GetClass()->GetPathName() : TEXT(""));

    TArray<TSharedPtr<FJsonValue>> States;
    if (EditorData)
    {
        for (UStateTreeState* SubTree : EditorData->SubTrees)
        {
            AppendStateSummary(SubTree, States, 0);
        }
    }
    Result->SetArrayField(TEXT("states"), States);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleStateTreeInspect(const TSharedPtr<FJsonObject>& Params)
{
    FString StateTreePath;
    Params->TryGetStringField(TEXT("state_tree"), StateTreePath);
    if (StateTreePath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'state_tree' parameter"));
    }
    UStateTree* StateTree = Cast<UStateTree>(LoadAsset(StateTreePath));
    if (!StateTree)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load StateTree: %s"), *StateTreePath));
    }
    return SummarizeStateTree(StateTree);
}

static void AddTagsToContainer(
    const TArray<FString>& TagNames,
    FGameplayTagContainer& OutContainer,
    TArray<FString>& OutWarnings)
{
    UGameplayTagsManager& TagsManager = UGameplayTagsManager::Get();
    for (const FString& TagName : TagNames)
    {
        const FGameplayTag Tag = TagsManager.RequestGameplayTag(FName(*TagName), false);
        if (Tag.IsValid())
        {
            OutContainer.AddTag(Tag);
        }
        else
        {
            OutWarnings.Add(FString::Printf(TEXT("Gameplay tag not found: %s"), *TagName));
        }
    }
}

static TArray<FString> GameplayTagsToStrings(const FGameplayTagContainer& Tags)
{
    TArray<FString> Values;
    for (const FGameplayTag& Tag : Tags.GetGameplayTagArray())
    {
        Values.Add(Tag.ToString());
    }
    return Values;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleSmartObjectCreateDefinition(const TSharedPtr<FJsonObject>& Params)
{
    FString Name;
    Params->TryGetStringField(TEXT("name"), Name);
    FString Path = TEXT("/Game/AI/SmartObjects");
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
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("SmartObject definition path must be under /Game"));
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

    FScopedSlowTask SlowTask(2.0f, FText::FromString(TEXT("MCP Create SmartObject Definition")));
    SlowTask.MakeDialog(false);
    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Create SmartObject Definition")));
    UEditorAssetLibrary::MakeDirectory(PackagePath);

    USmartObjectDefinition* Definition = NewObject<USmartObjectDefinition>(
        CreatePackage(*AssetPath),
        *AssetName,
        RF_Public | RF_Standalone | RF_Transactional);
    if (!Definition)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create SmartObject definition asset"));
    }

    FString SlotName = TEXT("Default");
    Params->TryGetStringField(TEXT("slot_name"), SlotName);
    if (!SlotName.IsEmpty())
    {
        FSmartObjectSlotDefinition& Slot = Definition->DebugAddSlot();
#if WITH_EDITORONLY_DATA
        Slot.Name = FName(*SlotName);
#endif
        Slot.bEnabled = true;
    }

    Definition->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(Definition);

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(ObjectPath, false);
    }

    TSharedPtr<FJsonObject> Result = SummarizeSmartObject(Definition);
    Result->SetStringField(TEXT("stage"), TEXT("smartobject_create_definition"));
    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(AssetPath));
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleSmartObjectAddSlot(const TSharedPtr<FJsonObject>& Params)
{
    FString DefinitionPath;
    Params->TryGetStringField(TEXT("definition"), DefinitionPath);
    if (DefinitionPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'definition' parameter"));
    }

    USmartObjectDefinition* Definition = Cast<USmartObjectDefinition>(LoadAsset(DefinitionPath));
    if (!Definition)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load SmartObject definition: %s"), *DefinitionPath));
    }

    FString SlotName = TEXT("Slot");
    Params->TryGetStringField(TEXT("slot_name"), SlotName);
    const FVector Offset = Params->HasField(TEXT("offset"))
        ? FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("offset"))
        : FVector::ZeroVector;
    const FRotator Rotation = Params->HasField(TEXT("rotation"))
        ? FUnrealMCPCommonUtils::GetRotatorFromJson(Params, TEXT("rotation"))
        : FRotator::ZeroRotator;
    bool bEnabled = true;
    Params->TryGetBoolField(TEXT("enabled"), bEnabled);

    const FScopedTransaction Transaction(FText::FromString(TEXT("MCP Add SmartObject Slot")));
    Definition->Modify();
    FSmartObjectSlotDefinition& Slot = Definition->DebugAddSlot();
#if WITH_EDITORONLY_DATA
    Slot.Name = FName(*SlotName);
#endif
    Slot.Offset = FVector3f(Offset);
    Slot.Rotation = FRotator3f(Rotation);
    Slot.bEnabled = bEnabled;

    TArray<FString> Warnings;
    AddTagsToContainer(GetStringArrayField(Params, TEXT("activity_tags")), Slot.ActivityTags, Warnings);
    AddTagsToContainer(GetStringArrayField(Params, TEXT("runtime_tags")), Slot.RuntimeTags, Warnings);

    Definition->MarkPackageDirty();
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    if (bSave)
    {
        UEditorAssetLibrary::SaveAsset(Definition->GetPathName(), false);
    }

    TSharedPtr<FJsonObject> Result = SummarizeSmartObject(Definition);
    Result->SetStringField(TEXT("stage"), TEXT("smartobject_add_slot"));
    Result->SetNumberField(TEXT("added_slot_index"), Definition->GetSlots().Num() - 1);
    Result->SetStringField(TEXT("added_slot_name"), SlotName);
    Result->SetArrayField(TEXT("warnings"), MakeStringArray(Warnings));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::SummarizeSmartObject(USmartObjectDefinition* Definition) const
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), Definition != nullptr);
    Result->SetStringField(TEXT("stage"), TEXT("smartobject_inspect_definition"));
    if (!Definition)
    {
        return Result;
    }

    Result->SetStringField(TEXT("asset_path"), NormalizeAssetPath(Definition->GetPathName()));
    Result->SetStringField(TEXT("object_path"), Definition->GetPathName());
    Result->SetNumberField(TEXT("slot_count"), Definition->GetSlots().Num());

    TArray<TSharedPtr<FJsonValue>> Slots;
    int32 SlotIndex = 0;
    for (const FSmartObjectSlotDefinition& Slot : Definition->GetSlots())
    {
        TSharedPtr<FJsonObject> SlotObject = MakeShared<FJsonObject>();
        SlotObject->SetNumberField(TEXT("index"), SlotIndex++);
#if WITH_EDITORONLY_DATA
        SlotObject->SetStringField(TEXT("name"), Slot.Name.ToString());
#else
        SlotObject->SetStringField(TEXT("name"), FString::Printf(TEXT("Slot_%d"), SlotIndex - 1));
#endif
        SlotObject->SetArrayField(TEXT("offset"), MakeVectorArray(FVector(Slot.Offset)));
        SlotObject->SetArrayField(TEXT("rotation"), MakeRotatorArray(FRotator(Slot.Rotation)));
        SlotObject->SetBoolField(TEXT("enabled"), Slot.bEnabled);
        SlotObject->SetArrayField(TEXT("activity_tags"), MakeStringArray(GameplayTagsToStrings(Slot.ActivityTags)));
        SlotObject->SetArrayField(TEXT("runtime_tags"), MakeStringArray(GameplayTagsToStrings(Slot.RuntimeTags)));
        Slots.Add(MakeShared<FJsonValueObject>(SlotObject));
    }
    Result->SetArrayField(TEXT("slots"), Slots);

    const FBox Bounds = Definition->GetBounds();
    Result->SetArrayField(TEXT("bounds_min"), MakeVectorArray(Bounds.Min));
    Result->SetArrayField(TEXT("bounds_max"), MakeVectorArray(Bounds.Max));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPMassCommands::HandleSmartObjectInspectDefinition(const TSharedPtr<FJsonObject>& Params)
{
    FString DefinitionPath;
    Params->TryGetStringField(TEXT("definition"), DefinitionPath);
    if (DefinitionPath.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'definition' parameter"));
    }

    USmartObjectDefinition* Definition = Cast<USmartObjectDefinition>(LoadAsset(DefinitionPath));
    if (!Definition)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(FString::Printf(TEXT("Could not load SmartObject definition: %s"), *DefinitionPath));
    }
    return SummarizeSmartObject(Definition);
}
