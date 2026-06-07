#include "Commands/UnrealMCPGASCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"

#include "AbilitySystemComponent.h"
#include "AbilitySystemInterface.h"
#include "Abilities/GameplayAbility.h"
#include "Abilities/Tasks/AbilityTask.h"
#include "AttributeSet.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetToolsModule.h"
#include "EditorAssetLibrary.h"
#include "EdGraph/EdGraph.h"
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"
#include "Factories/BlueprintFactory.h"
#include "GameplayCueNotify_Actor.h"
#include "GameplayCueNotify_Static.h"
#include "GameplayEffect.h"
#include "GameplayTagContainer.h"
#include "K2Node_CallFunction.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Misc/PackageName.h"
#include "Misc/ScopedSlowTask.h"
#include "ScopedTransaction.h"
#include "UObject/FieldIterator.h"
#include "UObject/MetaData.h"
#include "UObject/UnrealType.h"

FUnrealMCPGASCommands::FUnrealMCPGASCommands()
{
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::HandleCommand(
    const FString& CommandType,
    const TSharedPtr<FJsonObject>& Params)
{
    if (CommandType == TEXT("gas_create_ability")) return HandleCreateAbility(Params);
    if (CommandType == TEXT("gas_create_gameplay_effect")) return HandleCreateGameplayEffect(Params);
    if (CommandType == TEXT("gas_create_gameplay_cue")) return HandleCreateGameplayCue(Params);
    if (CommandType == TEXT("gas_create_attribute_set")) return HandleCreateAttributeSet(Params);
    if (CommandType == TEXT("gas_grant_ability")) return HandleGrantAbility(Params);
    if (CommandType == TEXT("gas_apply_effect")) return HandleApplyEffect(Params);
    if (CommandType == TEXT("gas_add_tag")) return HandleAddTag(Params);
    if (CommandType == TEXT("gas_create_ability_task_node")) return HandleCreateAbilityTaskNode(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown GAS command: %s"), *CommandType));
}

UClass* FUnrealMCPGASCommands::ResolveClass(const FString& ClassPathOrName, UClass* FallbackClass) const
{
    if (ClassPathOrName.IsEmpty())
    {
        return FallbackClass;
    }

    if (UClass* Direct = FindObject<UClass>(nullptr, *ClassPathOrName))
    {
        return Direct;
    }

    if (UClass* Loaded = LoadObject<UClass>(nullptr, *ClassPathOrName))
    {
        return Loaded;
    }

    const FString ScriptPath = ClassPathOrName.StartsWith(TEXT("/Script/"))
        ? ClassPathOrName
        : FString::Printf(TEXT("/Script/GameplayAbilities.%s"), *ClassPathOrName);
    if (UClass* ScriptClass = LoadObject<UClass>(nullptr, *ScriptPath))
    {
        return ScriptClass;
    }

    return FallbackClass;
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::CreateBlueprintAsset(
    const TSharedPtr<FJsonObject>& Params,
    const FString& DefaultName,
    const FString& DefaultPath,
    UClass* DefaultParentClass,
    const FString& StageName) const
{
    FString Name = DefaultName;
    Params->TryGetStringField(TEXT("name"), Name);

    FString Path = DefaultPath;
    Params->TryGetStringField(TEXT("path"), Path);
    Params->TryGetStringField(TEXT("folder_path"), Path);

    FString ParentClassName;
    Params->TryGetStringField(TEXT("parent_class"), ParentClassName);
    UClass* ParentClass = ResolveClass(ParentClassName, DefaultParentClass);
    if (!ParentClass)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("%s: GameplayAbilities parent class is unavailable"), *StageName));
    }

    if (Name.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'name' parameter"));
    }

    Path = Path.IsEmpty() ? TEXT("/Game/GAS") : Path;
    if (!Path.StartsWith(TEXT("/Game")))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("GAS asset path must be under /Game"));
    }

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    FString SanitizedPath = Path;
    SanitizedPath.RemoveFromEnd(TEXT("/"));
    const FString AssetPath = FString::Printf(TEXT("%s/%s"), *SanitizedPath, *Name);
    const FString ObjectPath = FString::Printf(TEXT("%s.%s"), *AssetPath, *Name);

    if (UEditorAssetLibrary::DoesAssetExist(ObjectPath))
    {
        if (!bOverwrite)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(
                FString::Printf(TEXT("Asset already exists: %s"), *ObjectPath));
        }
        UEditorAssetLibrary::DeleteAsset(ObjectPath);
    }

    FScopedSlowTask SlowTask(2.0f, FText::FromString(StageName));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f, FText::FromString(TEXT("Creating GAS Blueprint asset")));
    const FScopedTransaction Transaction(FText::FromString(StageName));

    UEditorAssetLibrary::MakeDirectory(Path);

    UBlueprintFactory* Factory = NewObject<UBlueprintFactory>();
    Factory->ParentClass = ParentClass;

    FAssetToolsModule& AssetToolsModule = FModuleManager::LoadModuleChecked<FAssetToolsModule>(TEXT("AssetTools"));
    UObject* NewAsset = AssetToolsModule.Get().CreateAsset(Name, Path, UBlueprint::StaticClass(), Factory);
    UBlueprint* NewBlueprint = Cast<UBlueprint>(NewAsset);
    if (!NewBlueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Failed to create GAS Blueprint asset: %s"), *ObjectPath));
    }

    SlowTask.EnterProgressFrame(1.0f, FText::FromString(TEXT("Marking asset dirty")));
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(NewBlueprint);
    NewBlueprint->MarkPackageDirty();
    FAssetRegistryModule::AssetCreated(NewBlueprint);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), StageName);
    Result->SetStringField(TEXT("asset_path"), AssetPath);
    Result->SetStringField(TEXT("object_path"), ObjectPath);
    Result->SetStringField(TEXT("name"), Name);
    Result->SetStringField(TEXT("parent_class"), ParentClass->GetPathName());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::HandleCreateAbility(const TSharedPtr<FJsonObject>& Params)
{
    return CreateBlueprintAsset(
        Params, TEXT("GA_NewAbility"), TEXT("/Game/GAS/Abilities"),
        UGameplayAbility::StaticClass(), TEXT("gas_create_ability"));
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::HandleCreateGameplayEffect(const TSharedPtr<FJsonObject>& Params)
{
    return CreateBlueprintAsset(
        Params, TEXT("GE_NewEffect"), TEXT("/Game/GAS/Effects"),
        UGameplayEffect::StaticClass(), TEXT("gas_create_gameplay_effect"));
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::HandleCreateGameplayCue(const TSharedPtr<FJsonObject>& Params)
{
    FString NotifyType = TEXT("actor");
    Params->TryGetStringField(TEXT("notify_type"), NotifyType);
    UClass* ParentClass = NotifyType.Equals(TEXT("static"), ESearchCase::IgnoreCase)
        ? UGameplayCueNotify_Static::StaticClass()
        : AGameplayCueNotify_Actor::StaticClass();
    return CreateBlueprintAsset(
        Params, TEXT("GCN_NewCue"), TEXT("/Game/GAS/Cues"),
        ParentClass, TEXT("gas_create_gameplay_cue"));
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::HandleCreateAttributeSet(const TSharedPtr<FJsonObject>& Params)
{
    return CreateBlueprintAsset(
        Params, TEXT("AS_NewAttributes"), TEXT("/Game/GAS/Attributes"),
        UAttributeSet::StaticClass(), TEXT("gas_create_attribute_set"));
}

UBlueprint* FUnrealMCPGASCommands::FindBlueprintChecked(const FString& BlueprintName, FString& OutError) const
{
    if (BlueprintName.IsEmpty())
    {
        OutError = TEXT("Missing 'target_bp' or 'blueprint_name' parameter");
        return nullptr;
    }

    UBlueprint* Blueprint = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!Blueprint)
    {
        OutError = FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName);
    }
    return Blueprint;
}

USCS_Node* FUnrealMCPGASCommands::EnsureAbilitySystemComponent(
    UBlueprint* Blueprint,
    bool& bCreated,
    FString& OutError) const
{
    bCreated = false;
    OutError.Empty();

    if (!Blueprint)
    {
        OutError = TEXT("Blueprint is null");
        return nullptr;
    }
    if (!Blueprint->SimpleConstructionScript)
    {
        OutError = TEXT("Blueprint has no SimpleConstructionScript");
        return nullptr;
    }

    for (USCS_Node* Node : Blueprint->SimpleConstructionScript->GetAllNodes())
    {
        if (Node && Node->ComponentClass && Node->ComponentClass->IsChildOf(UAbilitySystemComponent::StaticClass()))
        {
            return Node;
        }
    }

    Blueprint->Modify();
    Blueprint->SimpleConstructionScript->Modify();
    USCS_Node* NewNode = Blueprint->SimpleConstructionScript->CreateNode(
        UAbilitySystemComponent::StaticClass(),
        FName(TEXT("AbilitySystem")));
    if (!NewNode || !NewNode->ComponentTemplate)
    {
        OutError = TEXT("Failed to create AbilitySystemComponent SCS node");
        return nullptr;
    }

    bool bAddCrash = false;
    const bool bAdded = FUnrealMCPCommonUtils::SCSAddNodeGuarded(
        Blueprint->SimpleConstructionScript,
        NewNode,
        bAddCrash);
    if (bAddCrash || !bAdded)
    {
        OutError = FString::Printf(
            TEXT("Failed to add AbilitySystemComponent SCS node (seh=%d, added=%d)"),
            bAddCrash ? 1 : 0,
            bAdded ? 1 : 0);
        return nullptr;
    }

    bCreated = true;
    return NewNode;
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::AppendBlueprintMetadata(
    const TSharedPtr<FJsonObject>& Params,
    const FString& MetadataKey,
    const FString& ValueField,
    const FString& StageName) const
{
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("target_bp"), BlueprintName))
    {
        Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName);
    }

    FString Error;
    UBlueprint* Blueprint = FindBlueprintChecked(BlueprintName, Error);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
    }

    bool bEnsureASC = true;
    Params->TryGetBoolField(TEXT("ensure_asc"), bEnsureASC);
    bool bAscCreated = false;
    FString AscError;
    FString AscComponentName;
    if (bEnsureASC)
    {
        USCS_Node* AscNode = EnsureAbilitySystemComponent(Blueprint, bAscCreated, AscError);
        if (!AscNode)
        {
            return FUnrealMCPCommonUtils::CreateErrorResponse(AscError);
        }
        AscComponentName = AscNode->GetVariableName().ToString();
    }

    FString Value;
    if (!Params->TryGetStringField(*ValueField, Value) || Value.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Missing '%s' parameter"), *ValueField));
    }
    FString RecordedValue = Value;
    if (Params->HasField(TEXT("level")) || Params->HasField(TEXT("input_id")))
    {
        double Level = 1.0;
        Params->TryGetNumberField(TEXT("level"), Level);
        double InputIdNumber = -1.0;
        Params->TryGetNumberField(TEXT("input_id"), InputIdNumber);
        const int32 InputId = static_cast<int32>(InputIdNumber);
        RecordedValue = FString::Printf(TEXT("%s|level=%.3f|input_id=%d"), *Value, Level, InputId);
    }

    FScopedSlowTask SlowTask(1.0f, FText::FromString(StageName));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f, FText::FromString(TEXT("Recording GAS metadata")));
    const FScopedTransaction Transaction(FText::FromString(StageName));

    UPackage* Package = Blueprint->GetOutermost();
    if (!Package)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Could not access Blueprint package metadata"));
    }
    FMetaData& MetaData = Package->GetMetaData();

    const FString Existing = MetaData.GetValue(Blueprint, *MetadataKey);
    TArray<FString> Values;
    if (!Existing.IsEmpty())
    {
        Existing.ParseIntoArray(Values, TEXT(";"), true);
    }
    if (!Values.Contains(RecordedValue))
    {
        Values.Add(RecordedValue);
    }
    const FString Joined = FString::Join(Values, TEXT(";"));
    MetaData.SetValue(Blueprint, *MetadataKey, *Joined);

    Blueprint->Modify();
    Blueprint->MarkPackageDirty();

    TArray<TSharedPtr<FJsonValue>> JsonValues;
    for (const FString& Item : Values)
    {
        JsonValues.Add(MakeShared<FJsonValueString>(Item));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), StageName);
    Result->SetStringField(TEXT("blueprint_name"), BlueprintName);
    Result->SetStringField(TEXT("metadata_key"), MetadataKey);
    Result->SetStringField(TEXT("value"), Value);
    Result->SetStringField(TEXT("recorded_value"), RecordedValue);
    Result->SetBoolField(TEXT("asc_component_added"), bAscCreated);
    Result->SetStringField(TEXT("asc_component_name"), AscComponentName);
    Result->SetArrayField(TEXT("values"), JsonValues);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::HandleGrantAbility(const TSharedPtr<FJsonObject>& Params)
{
    return AppendBlueprintMetadata(
        Params, TEXT("MCP.GAS.GrantedAbilities"),
        TEXT("ability"), TEXT("gas_grant_ability"));
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::HandleApplyEffect(const TSharedPtr<FJsonObject>& Params)
{
    return AppendBlueprintMetadata(
        Params, TEXT("MCP.GAS.AppliedEffects"),
        TEXT("effect"), TEXT("gas_apply_effect"));
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::HandleAddTag(const TSharedPtr<FJsonObject>& Params)
{
    return AppendBlueprintMetadata(
        Params, TEXT("MCP.GAS.GameplayTags"),
        TEXT("tag"), TEXT("gas_add_tag"));
}

UEdGraph* FUnrealMCPGASCommands::FindGraph(UBlueprint* Blueprint, const FString& GraphName) const
{
    if (!Blueprint)
    {
        return nullptr;
    }

    const FString Wanted = GraphName.IsEmpty() ? TEXT("EventGraph") : GraphName;
    TArray<UEdGraph*> Graphs;
    Blueprint->GetAllGraphs(Graphs);
    for (UEdGraph* Graph : Graphs)
    {
        if (Graph && Graph->GetName() == Wanted)
        {
            return Graph;
        }
    }
    return nullptr;
}

UFunction* FUnrealMCPGASCommands::ResolveAbilityTaskFactory(UClass* TaskClass, const FString& FunctionName) const
{
    if (!TaskClass)
    {
        return nullptr;
    }

    if (!FunctionName.IsEmpty())
    {
        return TaskClass->FindFunctionByName(FName(*FunctionName));
    }

    for (TFieldIterator<UFunction> It(TaskClass, EFieldIteratorFlags::IncludeSuper); It; ++It)
    {
        UFunction* Function = *It;
        if (!Function || !Function->HasAllFunctionFlags(FUNC_Static | FUNC_BlueprintCallable))
        {
            continue;
        }
        if (Function->GetReturnProperty() &&
            Function->GetReturnProperty()->IsA<FObjectProperty>())
        {
            const FObjectProperty* ReturnProp = CastField<FObjectProperty>(Function->GetReturnProperty());
            if (ReturnProp && ReturnProp->PropertyClass && ReturnProp->PropertyClass->IsChildOf(TaskClass))
            {
                return Function;
            }
        }
    }
    return nullptr;
}

TSharedPtr<FJsonObject> FUnrealMCPGASCommands::HandleCreateAbilityTaskNode(const TSharedPtr<FJsonObject>& Params)
{
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name' parameter"));
    }

    FString TaskClassName;
    if (!Params->TryGetStringField(TEXT("task_class"), TaskClassName) || TaskClassName.IsEmpty())
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'task_class' parameter"));
    }

    FString Error;
    UBlueprint* Blueprint = FindBlueprintChecked(BlueprintName, Error);
    if (!Blueprint)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(Error);
    }

    FString GraphName = TEXT("EventGraph");
    Params->TryGetStringField(TEXT("graph_name"), GraphName);
    UEdGraph* Graph = FindGraph(Blueprint, GraphName);
    if (!Graph)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Graph not found: %s"), *GraphName));
    }

    UClass* TaskClass = ResolveClass(TaskClassName, nullptr);
    if (!TaskClass || !TaskClass->IsChildOf(UAbilityTask::StaticClass()))
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Ability task class not found or invalid: %s"), *TaskClassName));
    }

    FString FunctionName;
    Params->TryGetStringField(TEXT("task_function"), FunctionName);
    UFunction* FactoryFunction = ResolveAbilityTaskFactory(TaskClass, FunctionName);
    if (!FactoryFunction)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("No BlueprintCallable static factory found for task: %s"), *TaskClass->GetName()));
    }

    const TSharedPtr<FJsonObject>* PositionObj = nullptr;
    int32 NodeX = 0;
    int32 NodeY = 0;
    if (Params->TryGetObjectField(TEXT("node_position"), PositionObj) && PositionObj && PositionObj->IsValid())
    {
        NodeX = static_cast<int32>((*PositionObj)->GetNumberField(TEXT("x")));
        NodeY = static_cast<int32>((*PositionObj)->GetNumberField(TEXT("y")));
    }

    FScopedSlowTask SlowTask(1.0f, FText::FromString(TEXT("gas_create_ability_task_node")));
    SlowTask.MakeDialog(false);
    SlowTask.EnterProgressFrame(1.0f, FText::FromString(TEXT("Creating ability task call node")));
    const FScopedTransaction Transaction(FText::FromString(TEXT("gas_create_ability_task_node")));

    Graph->Modify();
    UK2Node_CallFunction* Node = NewObject<UK2Node_CallFunction>(Graph);
    Node->FunctionReference.SetExternalMember(FactoryFunction->GetFName(), FactoryFunction->GetOuterUClass());
    Node->NodePosX = NodeX;
    Node->NodePosY = NodeY;
    Graph->AddNode(Node, true, false);
    Node->AllocateDefaultPins();
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("stage"), TEXT("gas_create_ability_task_node"));
    Result->SetStringField(TEXT("blueprint_name"), BlueprintName);
    Result->SetStringField(TEXT("graph_name"), GraphName);
    Result->SetStringField(TEXT("task_class"), TaskClass->GetPathName());
    Result->SetStringField(TEXT("task_function"), FactoryFunction->GetName());
    Result->SetStringField(TEXT("node_id"), Node->NodeGuid.ToString());
    Result->SetStringField(TEXT("node_name"), Node->GetName());
    return Result;
}
