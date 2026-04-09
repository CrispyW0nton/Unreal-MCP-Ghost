// UnrealMCPBlueprintNodeCommands.cpp
// Comprehensive Blueprint graph manipulation commands for the UnrealMCP plugin.

#include "Commands/UnrealMCPBlueprintNodeCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"

#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphSchema_K2.h"

#include "K2Node_Event.h"
#include "K2Node_CallFunction.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "K2Node_InputAction.h"
#include "K2Node_EnhancedInputAction.h"  // For Enhanced Input support
#include "K2Node_Self.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_MacroInstance.h"
#include "K2Node_ForEachElementInEnum.h"
#include "K2Node_Composite.h"
#include "K2Node_SpawnActorFromClass.h"
#include "EdGraphNode_Comment.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavigationSystem.h"
#include "AI/NavigationSystemBase.h"
#include "Kismet/GameplayStatics.h"

// Enhanced Input
#include "EnhancedInputComponent.h"
#include "InputAction.h"

#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Engine/SimpleConstructionScript.h"
#include "Engine/SCS_Node.h"

DEFINE_LOG_CATEGORY_STATIC(LogMCPNode, Log, All);

// ============================================================
// Constructor
// ============================================================
FUnrealMCPBlueprintNodeCommands::FUnrealMCPBlueprintNodeCommands() {}

// ============================================================
// Dispatch
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleCommand(
    const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    // --- inspection ---
    if (CommandType == TEXT("get_blueprint_nodes"))         return HandleGetBlueprintNodes(Params);
    if (CommandType == TEXT("find_blueprint_nodes"))        return HandleFindBlueprintNodes(Params);
    if (CommandType == TEXT("get_blueprint_graphs"))        return HandleGetBlueprintGraphs(Params);
    if (CommandType == TEXT("get_node_by_id"))             return HandleGetNodeById(Params);

    // --- editing ---
    if (CommandType == TEXT("connect_blueprint_nodes"))     return HandleConnectBlueprintNodes(Params);
    if (CommandType == TEXT("disconnect_blueprint_nodes"))  return HandleDisconnectBlueprintNodes(Params);
    if (CommandType == TEXT("delete_blueprint_node"))       return HandleDeleteBlueprintNode(Params);
    if (CommandType == TEXT("set_node_pin_value"))          return HandleSetNodePinValue(Params);

    // --- node creation ---
    if (CommandType == TEXT("add_blueprint_event_node"))                     return HandleAddBlueprintEvent(Params);
    if (CommandType == TEXT("add_blueprint_function_node"))                  return HandleAddBlueprintFunctionCall(Params);
    if (CommandType == TEXT("add_blueprint_variable_get_node"))              return HandleAddBlueprintVariableGetNode(Params);
    if (CommandType == TEXT("add_blueprint_variable_set_node"))              return HandleAddBlueprintVariableSetNode(Params);
    if (CommandType == TEXT("add_blueprint_variable"))                       return HandleAddBlueprintVariable(Params);
    if (CommandType == TEXT("add_blueprint_input_action_node"))              return HandleAddBlueprintInputActionNode(Params);
    if (CommandType == TEXT("add_blueprint_enhanced_input_action_node"))     return HandleAddBlueprintEnhancedInputActionNode(Params);
    if (CommandType == TEXT("add_blueprint_self_reference"))                 return HandleAddBlueprintSelfReference(Params);
    if (CommandType == TEXT("add_blueprint_get_self_component_reference"))   return HandleAddBlueprintGetSelfComponentReference(Params);
    if (CommandType == TEXT("add_blueprint_get_component_node"))             return HandleAddBlueprintGetComponentNode(Params);
    if (CommandType == TEXT("add_blueprint_branch_node"))                    return HandleAddBlueprintBranchNode(Params);
    if (CommandType == TEXT("add_blueprint_cast_node"))                      return HandleAddBlueprintCastNode(Params);
    // Phase 2: new structural nodes
    if (CommandType == TEXT("add_blueprint_for_loop_node"))                  return HandleAddBlueprintForLoopNode(Params);
    if (CommandType == TEXT("add_blueprint_for_each_loop_node"))             return HandleAddBlueprintForEachLoopNode(Params);
    if (CommandType == TEXT("add_blueprint_sequence_node"))                  return HandleAddBlueprintSequenceNode(Params);
    if (CommandType == TEXT("add_blueprint_do_once_node"))                   return HandleAddBlueprintDoOnceNode(Params);
    if (CommandType == TEXT("add_blueprint_gate_node"))                      return HandleAddBlueprintGateNode(Params);
    if (CommandType == TEXT("add_blueprint_flip_flop_node"))                 return HandleAddBlueprintFlipFlopNode(Params);
    if (CommandType == TEXT("add_blueprint_switch_on_int_node"))             return HandleAddBlueprintSwitchOnIntNode(Params);
    if (CommandType == TEXT("add_blueprint_spawn_actor_node"))               return HandleAddBlueprintSpawnActorNode(Params);
    if (CommandType == TEXT("add_blueprint_comment_node"))                   return HandleAddBlueprintCommentNode(Params);
    if (CommandType == TEXT("move_blueprint_node"))                          return HandleMoveBlueprintNode(Params);
    // Phase 3: variable defaults
    if (CommandType == TEXT("get_blueprint_variable_defaults"))              return HandleGetBlueprintVariableDefaults(Params);
    if (CommandType == TEXT("set_blueprint_variable_default"))               return HandleSetBlueprintVariableDefault(Params);
    if (CommandType == TEXT("get_blueprint_components"))                     return HandleGetBlueprintComponents(Params);
    // Phase 4: NavMesh
    if (CommandType == TEXT("setup_navmesh"))                               return HandleSetupNavMesh(Params);

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Unknown blueprint node command: %s"), *CommandType));
}

// ============================================================
// Shared helpers
// ============================================================

UEdGraph* FUnrealMCPBlueprintNodeCommands::ResolveGraph(
    const TSharedPtr<FJsonObject>& Params, FString& OutError)
{
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
    {
        OutError = TEXT("Missing 'blueprint_name' parameter");
        return nullptr;
    }

    UBlueprint* BP = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!BP)
    {
        OutError = FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName);
        return nullptr;
    }

    FString GraphName;
    if (Params->TryGetStringField(TEXT("graph_name"), GraphName) && !GraphName.IsEmpty())
    {
        // Search UbergraphPages + FunctionGraphs + MacroGraphs
        for (UEdGraph* G : BP->UbergraphPages)
            if (G->GetName().Equals(GraphName, ESearchCase::IgnoreCase)) return G;
        for (UEdGraph* G : BP->FunctionGraphs)
            if (G->GetName().Equals(GraphName, ESearchCase::IgnoreCase)) return G;
        for (UEdGraph* G : BP->MacroGraphs)
            if (G->GetName().Equals(GraphName, ESearchCase::IgnoreCase)) return G;

        OutError = FString::Printf(TEXT("Graph not found: %s"), *GraphName);
        return nullptr;
    }

    // Default: EventGraph (first ubergraph)
    UEdGraph* EG = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!EG) OutError = TEXT("Failed to get EventGraph");
    return EG;
}

UEdGraphNode* FUnrealMCPBlueprintNodeCommands::FindNodeByIdOrName(
    UEdGraph* Graph, const FString& IdOrName)
{
    if (!Graph) return nullptr;

    // Try GUID match first
    FGuid TryGuid;
    if (FGuid::Parse(IdOrName, TryGuid))
    {
        for (UEdGraphNode* N : Graph->Nodes)
            if (N && N->NodeGuid == TryGuid) return N;
    }

    // Try short object name match (e.g. "K2Node_CallFunction_40")
    for (UEdGraphNode* N : Graph->Nodes)
        if (N && N->GetName().Equals(IdOrName, ESearchCase::IgnoreCase)) return N;

    // Try NodeComment match as last resort
    for (UEdGraphNode* N : Graph->Nodes)
        if (N && N->NodeComment.Equals(IdOrName, ESearchCase::IgnoreCase)) return N;

    return nullptr;
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::SerializePin(UEdGraphPin* Pin)
{
    TSharedPtr<FJsonObject> PObj = MakeShared<FJsonObject>();
    PObj->SetStringField(TEXT("pin_id"),    Pin->PinId.ToString());
    PObj->SetStringField(TEXT("pin_name"),  Pin->PinName.ToString());
    PObj->SetStringField(TEXT("direction"), Pin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
    PObj->SetStringField(TEXT("type"),      Pin->PinType.PinCategory.ToString());
    PObj->SetStringField(TEXT("default_value"), Pin->DefaultValue);
    PObj->SetBoolField(TEXT("is_hidden"),   Pin->bHidden);

    // Linked-to list (GUIDs of connected pins)
    TArray<TSharedPtr<FJsonValue>> Links;
    for (UEdGraphPin* LP : Pin->LinkedTo)
    {
        if (!LP) continue;
        TSharedPtr<FJsonObject> LObj = MakeShared<FJsonObject>();
        LObj->SetStringField(TEXT("node_id"), LP->GetOwningNode() ? LP->GetOwningNode()->NodeGuid.ToString() : TEXT(""));
        LObj->SetStringField(TEXT("node_name"), LP->GetOwningNode() ? LP->GetOwningNode()->GetName() : TEXT(""));
        LObj->SetStringField(TEXT("pin_name"), LP->PinName.ToString());
        LObj->SetStringField(TEXT("pin_id"),   LP->PinId.ToString());
        Links.Add(MakeShared<FJsonValueObject>(LObj));
    }
    PObj->SetArrayField(TEXT("linked_to"), Links);
    return PObj;
}

TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::SerializeNode(UEdGraphNode* Node)
{
    TSharedPtr<FJsonObject> NObj = MakeShared<FJsonObject>();
    NObj->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    NObj->SetStringField(TEXT("node_name"), Node->GetName());
    NObj->SetStringField(TEXT("node_type"), Node->GetClass()->GetName());
    NObj->SetStringField(TEXT("node_comment"), Node->NodeComment);
    NObj->SetNumberField(TEXT("pos_x"), (double)Node->NodePosX);
    NObj->SetNumberField(TEXT("pos_y"), (double)Node->NodePosY);

    // For function-call nodes, expose the function name
    if (UK2Node_CallFunction* CF = Cast<UK2Node_CallFunction>(Node))
    {
        NObj->SetStringField(TEXT("function_name"), CF->FunctionReference.GetMemberName().ToString());
        if (UClass* FC = CF->FunctionReference.GetMemberParentClass())
            NObj->SetStringField(TEXT("function_class"), FC->GetPathName());
    }

    // For event nodes, expose event name
    if (UK2Node_Event* EV = Cast<UK2Node_Event>(Node))
        NObj->SetStringField(TEXT("event_name"), EV->EventReference.GetMemberName().ToString());

    // For variable nodes, expose variable name
    if (UK2Node_VariableGet* VG = Cast<UK2Node_VariableGet>(Node))
        NObj->SetStringField(TEXT("variable_name"), VG->VariableReference.GetMemberName().ToString());
    if (UK2Node_VariableSet* VS = Cast<UK2Node_VariableSet>(Node))
        NObj->SetStringField(TEXT("variable_name"), VS->VariableReference.GetMemberName().ToString());

    // Pins
    TArray<TSharedPtr<FJsonValue>> Pins;
    for (UEdGraphPin* P : Node->Pins)
    {
        if (P && !P->bHidden)
            Pins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    }
    NObj->SetArrayField(TEXT("pins"), Pins);
    return NObj;
}

UFunction* FUnrealMCPBlueprintNodeCommands::ResolveFunction(
    const FString& FunctionPath, const FString& TargetClassStr, UBlueprint* Blueprint)
{
    // --- 1. Full path: "/Script/Engine.Actor:K2_GetActorLocation" ---
    if (FunctionPath.Contains(TEXT(":")))
    {
        int32 Colon; FunctionPath.FindLastChar(':', Colon);
        FString ClassPath = FunctionPath.Left(Colon);
        FString FuncName  = FunctionPath.Mid(Colon + 1);
        UClass* C = LoadObject<UClass>(nullptr, *ClassPath);
        if (C) return C->FindFunctionByName(*FuncName, EIncludeSuperFlag::IncludeSuper);
    }

    // --- 2. TargetClass + function name (support short names and full paths) ---
    UClass* TargetClass = nullptr;
    if (!TargetClassStr.IsEmpty())
    {
        // Try direct load (handles full paths like "/Script/Engine.KismetSystemLibrary")
        TargetClass = LoadObject<UClass>(nullptr, *TargetClassStr);

        // Try /Script/Engine.<Name>
        if (!TargetClass)
        {
            FString Stripped = TargetClassStr.StartsWith(TEXT("U")) ? TargetClassStr.Mid(1) : TargetClassStr;
            TargetClass = LoadObject<UClass>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *Stripped));
        }
        if (!TargetClass)
            TargetClass = LoadObject<UClass>(nullptr, *FString::Printf(TEXT("/Script/Engine.%s"), *TargetClassStr));

        // Common library shortcuts
        // Format:  ShortName -> full object path for LoadObject<UClass>
        // NOTE: KismetMathLibrary lives in /Script/Engine (same module as the engine),
        //       NOT /Script/Kismet (that module no longer exists in UE5).
        static const TMap<FString, FString> ShortNames = {
            // Engine / Kismet
            {TEXT("KismetSystemLibrary"),       TEXT("/Script/Engine.KismetSystemLibrary")},
            {TEXT("KismetMathLibrary"),         TEXT("/Script/Engine.KismetMathLibrary")},
            {TEXT("KismetStringLibrary"),       TEXT("/Script/Engine.KismetStringLibrary")},
            {TEXT("KismetArrayLibrary"),        TEXT("/Script/Engine.KismetArrayLibrary")},
            {TEXT("KismetTextLibrary"),         TEXT("/Script/Engine.KismetTextLibrary")},
            {TEXT("KismetInputLibrary"),        TEXT("/Script/Engine.KismetInputLibrary")},
            {TEXT("KismetNodeHelperLibrary"),   TEXT("/Script/Engine.KismetNodeHelperLibrary")},
            {TEXT("GameplayStatics"),           TEXT("/Script/Engine.GameplayStatics")},
            {TEXT("DataTableFunctionLibrary"),  TEXT("/Script/Engine.DataTableFunctionLibrary")},
            // Actor / Component hierarchy
            {TEXT("Actor"),                     TEXT("/Script/Engine.Actor")},
            {TEXT("Character"),                 TEXT("/Script/Engine.Character")},
            {TEXT("Pawn"),                      TEXT("/Script/Engine.Pawn")},
            {TEXT("PlayerController"),          TEXT("/Script/Engine.PlayerController")},
            {TEXT("Controller"),                TEXT("/Script/Engine.Controller")},
            {TEXT("SceneComponent"),            TEXT("/Script/Engine.SceneComponent")},
            {TEXT("PrimitiveComponent"),        TEXT("/Script/Engine.PrimitiveComponent")},
            {TEXT("StaticMeshComponent"),       TEXT("/Script/Engine.StaticMeshComponent")},
            {TEXT("SkeletalMeshComponent"),     TEXT("/Script/Engine.SkeletalMeshComponent")},
            {TEXT("CharacterMovementComponent"),TEXT("/Script/Engine.CharacterMovementComponent")},
            {TEXT("CapsuleComponent"),          TEXT("/Script/Engine.CapsuleComponent")},
            {TEXT("ArrowComponent"),            TEXT("/Script/Engine.ArrowComponent")},
            {TEXT("AudioComponent"),            TEXT("/Script/Engine.AudioComponent")},
            {TEXT("SplineComponent"),           TEXT("/Script/Engine.SplineComponent")},
            {TEXT("TimelineComponent"),         TEXT("/Script/Engine.TimelineComponent")},
            // Enhanced Input
            {TEXT("EnhancedInputComponent"),    TEXT("/Script/EnhancedInput.EnhancedInputComponent")},
            // Gameplay Abilities
            {TEXT("AbilitySystemComponent"),    TEXT("/Script/GameplayAbilities.AbilitySystemComponent")},
            {TEXT("AbilitySystemBlueprintLibrary"), TEXT("/Script/GameplayAbilities.AbilitySystemBlueprintLibrary")},
        };
        if (!TargetClass)
        {
            for (auto& KV : ShortNames)
            {
                if (TargetClassStr.Equals(KV.Key, ESearchCase::IgnoreCase))
                {
                    TargetClass = LoadObject<UClass>(nullptr, *KV.Value);
                    break;
                }
            }
        }
        // Last resort: try /Script/<TargetClassStr>.<TargetClassStr>
        if (!TargetClass)
        {
            FString AutoPath = FString::Printf(TEXT("/Script/%s.%s"), *TargetClassStr, *TargetClassStr);
            TargetClass = LoadObject<UClass>(nullptr, *AutoPath);
        }
    }

    if (TargetClass)
    {
        // Exact match first
        if (UFunction* F = TargetClass->FindFunctionByName(*FunctionPath, EIncludeSuperFlag::IncludeSuper))
            return F;
        // Case-insensitive walk
        for (TFieldIterator<UFunction> It(TargetClass, EFieldIteratorFlags::IncludeSuper); It; ++It)
            if (It->GetName().Equals(FunctionPath, ESearchCase::IgnoreCase)) return *It;
    }

    // --- 3. Search the Blueprint's own generated class ---
    if (Blueprint && Blueprint->GeneratedClass)
    {
        if (UFunction* F = Blueprint->GeneratedClass->FindFunctionByName(*FunctionPath, EIncludeSuperFlag::IncludeSuper))
            return F;
    }

    // --- 4. Global search: walk every loaded UClass looking for the function ---
    // This is a heavyweight fallback that handles functions in plugin classes that
    // are not in the shortname map and whose module is unknown to the caller.
    if (TargetClassStr.IsEmpty())
    {
        for (TObjectIterator<UClass> ClassIt; ClassIt; ++ClassIt)
        {
            UClass* C = *ClassIt;
            if (!C) continue;
            // Only search library/subsystem classes to keep the search fast
            FString CName = C->GetName();
            if (!CName.Contains(TEXT("Library")) && !CName.Contains(TEXT("Statics")) &&
                !CName.Contains(TEXT("BlueprintLibrary")) && !CName.Contains(TEXT("Subsystem")))
                continue;
            for (TFieldIterator<UFunction> It(C, EFieldIteratorFlags::ExcludeSuper); It; ++It)
            {
                if (It->GetName().Equals(FunctionPath, ESearchCase::IgnoreCase))
                {
                    UE_LOG(LogMCPNode, Display,
                        TEXT("ResolveFunction: found '%s' via global search in class '%s'"),
                        *FunctionPath, *CName);
                    return *It;
                }
            }
        }
    }

    return nullptr;
}

bool FUnrealMCPBlueprintNodeCommands::ApplyPinValue(
    UEdGraph* Graph, UEdGraphPin* Pin, const FString& Value)
{
    if (!Pin) return false;
    const UEdGraphSchema_K2* K2 = Cast<const UEdGraphSchema_K2>(Graph->GetSchema());

    // --- R-02: handle class/object pins by resolving the UClass/UObject first ---
    FName PinCat = Pin->PinType.PinCategory;
    if (PinCat == UEdGraphSchema_K2::PC_Class || PinCat == UEdGraphSchema_K2::PC_SoftClass)
    {
        // Try to resolve as a class by name
        UClass* FoundClass = FindFirstObject<UClass>(*Value, EFindFirstObjectOptions::None);
        if (!FoundClass)
        {
            for (TObjectIterator<UClass> It; It; ++It)
            {
                if (It->GetName().Equals(Value, ESearchCase::IgnoreCase))
                {
                    FoundClass = *It;
                    break;
                }
            }
        }
        if (FoundClass && K2)
        {
            K2->TrySetDefaultObject(*Pin, FoundClass);
            return true;
        }
        // fall through to string attempt
    }
    else if (PinCat == UEdGraphSchema_K2::PC_Object || PinCat == UEdGraphSchema_K2::PC_SoftObject)
    {
        // Try to resolve as a UObject asset
        UObject* FoundObj = FindFirstObject<UObject>(*Value, EFindFirstObjectOptions::None);
        if (!FoundObj)
            FoundObj = LoadObject<UObject>(nullptr, *Value);
        if (FoundObj && K2)
        {
            K2->TrySetDefaultObject(*Pin, FoundObj);
            return true;
        }
    }

    if (K2)
    {
        K2->TrySetDefaultValue(*Pin, Value);
        return true;
    }
    // Fallback: set directly
    Pin->DefaultValue = Value;
    return true;
}

// ============================================================
// get_blueprint_nodes   -  return ALL nodes in a graph
// Params: blueprint_name, [graph_name], [include_hidden_pins=false]
//
// graph_name special values:
//   "EventGraph" (default)    -  main event graph
//   "*" or "all"              -  every graph (EventGraph + functions + macros)
//                              Nodes are grouped per graph in the response.
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleGetBlueprintNodes(
    const TSharedPtr<FJsonObject>& Params)
{
    // ---- Handle "all graphs" mode ----
    FString GraphNameParam;
    Params->TryGetStringField(TEXT("graph_name"), GraphNameParam);
    bool bAllGraphs = (GraphNameParam == TEXT("*") || GraphNameParam.ToLower() == TEXT("all"));

    if (bAllGraphs)
    {
        FString BlueprintName;
        if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
            return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
        UBlueprint* BP = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
        if (!BP) return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));

        bool bIncludeHidden = false;
        Params->TryGetBoolField(TEXT("include_hidden_pins"), bIncludeHidden);

        TArray<UEdGraph*> AllGraphs;
        for (UEdGraph* G : BP->UbergraphPages) if (G) AllGraphs.Add(G);
        for (UEdGraph* G : BP->FunctionGraphs) if (G) AllGraphs.Add(G);
        for (UEdGraph* G : BP->MacroGraphs)    if (G) AllGraphs.Add(G);

        TArray<TSharedPtr<FJsonValue>> GraphsResult;
        int32 TotalNodes = 0;
        for (UEdGraph* G : AllGraphs)
        {
            TSharedPtr<FJsonObject> GObj = MakeShared<FJsonObject>();
            GObj->SetStringField(TEXT("graph_name"), G->GetName());
            TArray<TSharedPtr<FJsonValue>> NodesArray;
            for (UEdGraphNode* Node : G->Nodes)
            {
                if (!Node) continue;
                TSharedPtr<FJsonObject> NObj = MakeShared<FJsonObject>();
                NObj->SetStringField(TEXT("node_id"),      Node->NodeGuid.ToString());
                NObj->SetStringField(TEXT("node_name"),    Node->GetName());
                NObj->SetStringField(TEXT("node_type"),    Node->GetClass()->GetName());
                NObj->SetStringField(TEXT("node_comment"), Node->NodeComment);
                NObj->SetNumberField(TEXT("pos_x"), (double)Node->NodePosX);
                NObj->SetNumberField(TEXT("pos_y"), (double)Node->NodePosY);
                if (UK2Node_CallFunction* CF = Cast<UK2Node_CallFunction>(Node))
                {
                    NObj->SetStringField(TEXT("function_name"), CF->FunctionReference.GetMemberName().ToString());
                    if (UClass* FC = CF->FunctionReference.GetMemberParentClass())
                        NObj->SetStringField(TEXT("function_class"), FC->GetPathName());
                }
                if (UK2Node_Event* EV = Cast<UK2Node_Event>(Node))
                    NObj->SetStringField(TEXT("event_name"), EV->EventReference.GetMemberName().ToString());
                if (UK2Node_VariableGet* VG = Cast<UK2Node_VariableGet>(Node))
                    NObj->SetStringField(TEXT("variable_name"), VG->VariableReference.GetMemberName().ToString());
                if (UK2Node_VariableSet* VS = Cast<UK2Node_VariableSet>(Node))
                    NObj->SetStringField(TEXT("variable_name"), VS->VariableReference.GetMemberName().ToString());
                TArray<TSharedPtr<FJsonValue>> PinsArray;
                for (UEdGraphPin* P : Node->Pins)
                {
                    if (!P || (!bIncludeHidden && P->bHidden)) continue;
                    PinsArray.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
                }
                NObj->SetArrayField(TEXT("pins"), PinsArray);
                NodesArray.Add(MakeShared<FJsonValueObject>(NObj));
            }
            GObj->SetArrayField(TEXT("nodes"), NodesArray);
            GObj->SetNumberField(TEXT("count"), (double)NodesArray.Num());
            TotalNodes += NodesArray.Num();
            GraphsResult.Add(MakeShared<FJsonValueObject>(GObj));
        }
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetArrayField(TEXT("graphs"), GraphsResult);
        Result->SetNumberField(TEXT("total_count"), (double)TotalNodes);
        Result->SetBoolField(TEXT("all_graphs"), true);
        return Result;
    }

    // ---- Normal single-graph mode ----
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    bool bIncludeHidden = false;
    Params->TryGetBoolField(TEXT("include_hidden_pins"), bIncludeHidden);

    TArray<TSharedPtr<FJsonValue>> NodesArray;
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        if (!Node) continue;
        TSharedPtr<FJsonObject> NObj = MakeShared<FJsonObject>();
        NObj->SetStringField(TEXT("node_id"),      Node->NodeGuid.ToString());
        NObj->SetStringField(TEXT("node_name"),    Node->GetName());
        NObj->SetStringField(TEXT("node_type"),    Node->GetClass()->GetName());
        NObj->SetStringField(TEXT("node_comment"), Node->NodeComment);
        NObj->SetNumberField(TEXT("pos_x"), (double)Node->NodePosX);
        NObj->SetNumberField(TEXT("pos_y"), (double)Node->NodePosY);

        // Type-specific fields
        if (UK2Node_CallFunction* CF = Cast<UK2Node_CallFunction>(Node))
        {
            NObj->SetStringField(TEXT("function_name"), CF->FunctionReference.GetMemberName().ToString());
            if (UClass* FC = CF->FunctionReference.GetMemberParentClass())
                NObj->SetStringField(TEXT("function_class"), FC->GetPathName());
        }
        if (UK2Node_Event* EV = Cast<UK2Node_Event>(Node))
            NObj->SetStringField(TEXT("event_name"), EV->EventReference.GetMemberName().ToString());
        if (UK2Node_VariableGet* VG = Cast<UK2Node_VariableGet>(Node))
            NObj->SetStringField(TEXT("variable_name"), VG->VariableReference.GetMemberName().ToString());
        if (UK2Node_VariableSet* VS = Cast<UK2Node_VariableSet>(Node))
            NObj->SetStringField(TEXT("variable_name"), VS->VariableReference.GetMemberName().ToString());

        // Pins
        TArray<TSharedPtr<FJsonValue>> PinsArray;
        for (UEdGraphPin* P : Node->Pins)
        {
            if (!P || (!bIncludeHidden && P->bHidden)) continue;
            PinsArray.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
        }
        NObj->SetArrayField(TEXT("pins"), PinsArray);
        NodesArray.Add(MakeShared<FJsonValueObject>(NObj));
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetArrayField(TEXT("nodes"), NodesArray);
    Result->SetNumberField(TEXT("count"), (double)NodesArray.Num());
    Result->SetStringField(TEXT("graph_name"), Graph->GetName());
    return Result;
}

// ============================================================
// find_blueprint_nodes  -  filtered search
// Params: blueprint_name, [graph_name], node_type (or "all"), [event_name], [function_name],
//         [variable_name], [input_action_name], [node_name]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleFindBlueprintNodes(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString NodeType;
    Params->TryGetStringField(TEXT("node_type"), NodeType);
    NodeType = NodeType.ToLower();

    // Optional filters
    FString FilterEventName, FilterFuncName, FilterVarName, FilterActionName, FilterNodeName;
    Params->TryGetStringField(TEXT("event_name"),        FilterEventName);
    Params->TryGetStringField(TEXT("function_name"),     FilterFuncName);
    Params->TryGetStringField(TEXT("variable_name"),     FilterVarName);
    Params->TryGetStringField(TEXT("input_action_name"), FilterActionName);
    Params->TryGetStringField(TEXT("node_name"),         FilterNodeName);

    TArray<TSharedPtr<FJsonValue>> NodesArray;
    TArray<TSharedPtr<FJsonValue>> GuidsArray; // legacy compat

    for (UEdGraphNode* Node : Graph->Nodes)
    {
        if (!Node) continue;
        bool bMatch = false;

        if (NodeType == TEXT("all") || NodeType.IsEmpty())
        {
            bMatch = true;
        }
        else if (NodeType == TEXT("event") || NodeType == TEXT("k2node_event"))
        {
            if (UK2Node_Event* EV = Cast<UK2Node_Event>(Node))
            {
                FString EN = EV->EventReference.GetMemberName().ToString();
                bMatch = FilterEventName.IsEmpty() || EN.Equals(FilterEventName, ESearchCase::IgnoreCase);
            }
        }
        else if (NodeType == TEXT("function") || NodeType == TEXT("callfunction") ||
                 NodeType == TEXT("k2node_callfunction"))
        {
            if (UK2Node_CallFunction* CF = Cast<UK2Node_CallFunction>(Node))
            {
                FString FN = CF->FunctionReference.GetMemberName().ToString();
                bMatch = FilterFuncName.IsEmpty() || FN.Equals(FilterFuncName, ESearchCase::IgnoreCase);
            }
        }
        else if (NodeType == TEXT("variableget") || NodeType == TEXT("variable_get") ||
                 NodeType == TEXT("k2node_variableget"))
        {
            if (UK2Node_VariableGet* VG = Cast<UK2Node_VariableGet>(Node))
            {
                FString VN = VG->VariableReference.GetMemberName().ToString();
                bMatch = FilterVarName.IsEmpty() || VN.Equals(FilterVarName, ESearchCase::IgnoreCase);
            }
        }
        else if (NodeType == TEXT("variableset") || NodeType == TEXT("variable_set") ||
                 NodeType == TEXT("k2node_variableset"))
        {
            if (UK2Node_VariableSet* VS = Cast<UK2Node_VariableSet>(Node))
            {
                FString VN = VS->VariableReference.GetMemberName().ToString();
                bMatch = FilterVarName.IsEmpty() || VN.Equals(FilterVarName, ESearchCase::IgnoreCase);
            }
        }
        else if (NodeType == TEXT("inputaction") || NodeType == TEXT("input_action") ||
                 NodeType == TEXT("enhancedinputaction") || NodeType == TEXT("enhanced_input_action") ||
                 NodeType == TEXT("k2node_inputaction") || NodeType == TEXT("k2node_enhancedinputaction"))
        {
            // Match legacy K2Node_InputAction and Enhanced Input K2Node_EnhancedInputAction
            FString ClassName = Node->GetClass()->GetName().ToLower();
            if (ClassName.Contains(TEXT("inputaction")))
            {
                bMatch = FilterActionName.IsEmpty() ||
                         Node->NodeComment.Contains(FilterActionName) ||
                         Node->GetName().Contains(FilterActionName);
            }
        }
        else
        {
            // Generic class-name substring match
            bMatch = Node->GetClass()->GetName().ToLower().Contains(NodeType);
        }

        // Apply additional name filter
        if (bMatch && !FilterNodeName.IsEmpty())
            bMatch = Node->GetName().Equals(FilterNodeName, ESearchCase::IgnoreCase);

        if (bMatch)
        {
            GuidsArray.Add(MakeShared<FJsonValueString>(Node->NodeGuid.ToString()));
            NodesArray.Add(MakeShared<FJsonValueObject>(SerializeNode(Node)));
        }
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetArrayField(TEXT("nodes"),      NodesArray);
    Result->SetArrayField(TEXT("node_guids"), GuidsArray); // legacy
    Result->SetNumberField(TEXT("count"),     (double)NodesArray.Num());
    return Result;
}

// ============================================================
// connect_blueprint_nodes
// Params: blueprint_name, [graph_name],
//         source_node_id (GUID or name), source_pin,
//         target_node_id (GUID or name), target_pin
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleConnectBlueprintNodes(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString SrcId, DstId, SrcPin, DstPin;
    if (!Params->TryGetStringField(TEXT("source_node_id"), SrcId))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'source_node_id'"));
    if (!Params->TryGetStringField(TEXT("target_node_id"), DstId))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'target_node_id'"));
    if (!Params->TryGetStringField(TEXT("source_pin"), SrcPin))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'source_pin'"));
    if (!Params->TryGetStringField(TEXT("target_pin"), DstPin))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'target_pin'"));

    UEdGraphNode* SrcNode = FindNodeByIdOrName(Graph, SrcId);
    UEdGraphNode* DstNode = FindNodeByIdOrName(Graph, DstId);
    if (!SrcNode) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Source node not found: %s"), *SrcId));
    if (!DstNode) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Target node not found: %s"), *DstId));

    FString ConnectError;
    if (!FUnrealMCPCommonUtils::ConnectGraphNodes(Graph, SrcNode, SrcPin, DstNode, DstPin, ConnectError))
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            ConnectError.IsEmpty()
                ? FString::Printf(TEXT("Failed to connect pin '%s' -> '%s'"), *SrcPin, *DstPin)
                : ConnectError);

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    // Confirm the connection actually took effect by checking the pin's link list.
    // FindPin with EGPD_MAX to mirror what ConnectGraphNodes used.
    UEdGraphPin* ActualSrcPin = FUnrealMCPCommonUtils::FindPin(SrcNode, SrcPin, EGPD_Output);
    if (!ActualSrcPin) ActualSrcPin = FUnrealMCPCommonUtils::FindPin(SrcNode, SrcPin, EGPD_MAX);
    UEdGraphPin* ActualDstPin = FUnrealMCPCommonUtils::FindPin(DstNode, DstPin, EGPD_Input);
    if (!ActualDstPin) ActualDstPin = FUnrealMCPCommonUtils::FindPin(DstNode, DstPin, EGPD_MAX);

    bool bVerified = false;
    if (ActualSrcPin && ActualDstPin)
    {
        for (UEdGraphPin* LP : ActualSrcPin->LinkedTo)
            if (LP == ActualDstPin) { bVerified = true; break; }
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("source_node_id"),   SrcNode->NodeGuid.ToString());
    R->SetStringField(TEXT("target_node_id"),   DstNode->NodeGuid.ToString());
    R->SetStringField(TEXT("source_pin"),       ActualSrcPin ? ActualSrcPin->PinName.ToString() : SrcPin);
    R->SetStringField(TEXT("target_pin"),       ActualDstPin ? ActualDstPin->PinName.ToString() : DstPin);
    R->SetBoolField(TEXT("connection_verified"), bVerified);
    if (!bVerified)
        R->SetStringField(TEXT("warning"),
            TEXT("Connection was attempted but could not be confirmed in the pin's LinkedTo list. "
                 "This may indicate a type mismatch or schema rejection."));
    return R;
}

// ============================================================
// disconnect_blueprint_nodes
// Params: blueprint_name, [graph_name],
//         node_id, pin_name  (breaks ALL links on that pin)
//   OR    source_node_id, source_pin, target_node_id, target_pin  (break specific link)
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleDisconnectBlueprintNodes(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    const UEdGraphSchema_K2* Schema = Cast<const UEdGraphSchema_K2>(Graph->GetSchema());

    // Case A: break all links on one pin
    FString NodeId, PinName;
    if (Params->TryGetStringField(TEXT("node_id"), NodeId) &&
        Params->TryGetStringField(TEXT("pin_name"), PinName))
    {
        UEdGraphNode* Node = FindNodeByIdOrName(Graph, NodeId);
        if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Node not found: %s"), *NodeId));
        UEdGraphPin* Pin = FUnrealMCPCommonUtils::FindPin(Node, PinName);
        if (!Pin) return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Pin not found: %s on node %s"), *PinName, *NodeId));

        if (Schema) Schema->BreakPinLinks(*Pin, true);
        else Pin->BreakAllPinLinks();

        UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
        if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

        TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
        R->SetStringField(TEXT("node_id"), Node->NodeGuid.ToString());
        R->SetStringField(TEXT("pin_name"), PinName);
        return R;
    }

    // Case B: break a specific link
    FString SrcId, DstId, SrcPin, DstPin;
    Params->TryGetStringField(TEXT("source_node_id"), SrcId);
    Params->TryGetStringField(TEXT("target_node_id"), DstId);
    Params->TryGetStringField(TEXT("source_pin"), SrcPin);
    Params->TryGetStringField(TEXT("target_pin"), DstPin);

    if (SrcId.IsEmpty() || DstId.IsEmpty())
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            TEXT("Provide either (node_id + pin_name) or (source_node_id + source_pin + target_node_id + target_pin)"));

    UEdGraphNode* SrcNode = FindNodeByIdOrName(Graph, SrcId);
    UEdGraphNode* DstNode = FindNodeByIdOrName(Graph, DstId);
    if (!SrcNode || !DstNode)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Source or target node not found"));

    UEdGraphPin* SP = FUnrealMCPCommonUtils::FindPin(SrcNode, SrcPin, EGPD_Output);
    UEdGraphPin* DP = FUnrealMCPCommonUtils::FindPin(DstNode, DstPin, EGPD_Input);
    if (!SP || !DP)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Pin not found on source or target node"));

    if (Schema) Schema->BreakSinglePinLink(SP, DP);
    else SP->BreakLinkTo(DP);

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("source_node_id"), SrcNode->NodeGuid.ToString());
    R->SetStringField(TEXT("target_node_id"), DstNode->NodeGuid.ToString());
    return R;
}

// ============================================================
// delete_blueprint_node
// Params: blueprint_name, [graph_name], node_id (GUID or name)
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleDeleteBlueprintNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString NodeId;
    if (!Params->TryGetStringField(TEXT("node_id"), NodeId))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'node_id'"));

    UEdGraphNode* Node = FindNodeByIdOrName(Graph, NodeId);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Node not found: %s"), *NodeId));

    FString DeletedId = Node->NodeGuid.ToString();
    FString DeletedName = Node->GetName();

    // Break all connections first
    const UEdGraphSchema_K2* Schema = Cast<const UEdGraphSchema_K2>(Graph->GetSchema());
    if (Schema) Schema->BreakNodeLinks(*Node);

    Graph->RemoveNode(Node);

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("deleted_node_id"),   DeletedId);
    R->SetStringField(TEXT("deleted_node_name"), DeletedName);
    return R;
}

// ============================================================
// set_node_pin_value
// Params: blueprint_name, [graph_name], node_id, pin_name, value (string)
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleSetNodePinValue(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString NodeId, PinName, Value;
    if (!Params->TryGetStringField(TEXT("node_id"),  NodeId))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'node_id'"));
    if (!Params->TryGetStringField(TEXT("pin_name"), PinName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'pin_name'"));

    // Accept value as string, number, or boolean JSON type
    if (!Params->TryGetStringField(TEXT("value"), Value))
    {
        // Try boolean
        bool BoolVal;
        double NumVal;
        if (Params->TryGetBoolField(TEXT("value"), BoolVal))
            Value = BoolVal ? TEXT("true") : TEXT("false");
        else if (Params->TryGetNumberField(TEXT("value"), NumVal))
            Value = FString::SanitizeFloat(NumVal);
        else
            return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'value'"));
    }

    UEdGraphNode* Node = FindNodeByIdOrName(Graph, NodeId);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Node not found: %s"), *NodeId));

    UEdGraphPin* Pin = FUnrealMCPCommonUtils::FindPin(Node, PinName);
    if (!Pin) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Pin not found: %s"), *PinName));

    if (!ApplyPinValue(Graph, Pin, Value))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to apply pin value"));

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),  Node->NodeGuid.ToString());
    R->SetStringField(TEXT("pin_name"), PinName);
    R->SetStringField(TEXT("value"),    Pin->DefaultValue);
    return R;
}

// ============================================================
// add_blueprint_event_node
// Params: blueprint_name, [graph_name], event_name, [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintEvent(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString EventName;
    if (!Params->TryGetStringField(TEXT("event_name"), EventName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'event_name'"));

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_Event* EventNode = FUnrealMCPCommonUtils::CreateEventNode(Graph, EventName, Pos);
    if (!EventNode) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create event node"));

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   EventNode->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), EventNode->GetName());
    // Return pins so the caller can immediately wire without a second round-trip
    TArray<TSharedPtr<FJsonValue>> PinsArr;
    for (UEdGraphPin* P : EventNode->Pins)
        if (P && !P->bHidden) PinsArr.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), PinsArr);
    return R;
}

// ============================================================
// add_blueprint_function_node
// Params: blueprint_name, [graph_name],
//         function_name  (short name OR "/Script/Engine.Actor:K2_GetActorLocation")
//         [target]       (class short name or full path, e.g. "KismetMathLibrary")
//         [node_position]
//         [params]       (object: pin_name -> default value)
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintFunctionCall(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    UBlueprint* Blueprint = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);

    FString FunctionName;
    if (!Params->TryGetStringField(TEXT("function_name"), FunctionName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'function_name'"));

    FString TargetClass;
    Params->TryGetStringField(TEXT("target"), TargetClass);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    // -- Duplicate guard ------------------------------------------------------
    // If the caller doesn't pass allow_duplicates=true (default false), check
    // whether an identical function-call node already exists near the requested
    // position.  "Near" = within 32 units on both axes (tolerates rounding).
    bool bAllowDuplicates = false;
    Params->TryGetBoolField(TEXT("allow_duplicates"), bAllowDuplicates);

    if (!bAllowDuplicates)
    {
        for (UEdGraphNode* N : Graph->Nodes)
        {
            UK2Node_CallFunction* CF = Cast<UK2Node_CallFunction>(N);
            if (!CF) continue;
            bool bSameName = CF->FunctionReference.GetMemberName().ToString()
                                 .Equals(FunctionName, ESearchCase::IgnoreCase);
            bool bNearPos  = FMath::Abs(CF->NodePosX - (int32)Pos.X) <= 32 &&
                             FMath::Abs(CF->NodePosY - (int32)Pos.Y) <= 32;
            if (bSameName && bNearPos)
            {
                UE_LOG(LogMCPNode, Display,
                    TEXT("add_blueprint_function_node: returning existing node '%s' (duplicate guard)"),
                    *CF->GetName());
                TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
                R->SetStringField(TEXT("node_id"),   CF->NodeGuid.ToString());
                R->SetStringField(TEXT("node_name"), CF->GetName());
                R->SetBoolField(TEXT("was_existing"), true);
                TArray<TSharedPtr<FJsonValue>> PA;
                for (UEdGraphPin* P : CF->Pins)
                    if (P && !P->bHidden) PA.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
                R->SetArrayField(TEXT("pins"), PA);
                return R;
            }
        }
    }
    // ------------------------------------------------------------------------

    // Resolve function
    UFunction* Func = ResolveFunction(FunctionName, TargetClass, Blueprint);

    UK2Node_CallFunction* FuncNode = nullptr;
    if (Func)
    {
        FuncNode = FUnrealMCPCommonUtils::CreateFunctionCallNode(Graph, Func, Pos);
    }
    else
    {
        // Can't find UFunction - try to build the node by name+class path directly.
        // This handles cases where the function exists in a Blueprint class (not native).
        UE_LOG(LogMCPNode, Warning, TEXT("add_blueprint_function_node: UFunction not found for '%s' in '%s', trying direct node construction"), *FunctionName, *TargetClass);

        UClass* DirectClass = nullptr;
        if (!TargetClass.IsEmpty()) DirectClass = LoadObject<UClass>(nullptr, *TargetClass);

        if (DirectClass)
        {
            FuncNode = NewObject<UK2Node_CallFunction>(Graph);
            FuncNode->FunctionReference.SetExternalMember(FName(*FunctionName), DirectClass);
            FuncNode->NodePosX = (int32)Pos.X;
            FuncNode->NodePosY = (int32)Pos.Y;
            FuncNode->CreateNewGuid();
            Graph->AddNode(FuncNode);
            FuncNode->PostPlacedNewNode();
            FuncNode->AllocateDefaultPins();
            FuncNode->ReconstructNode();
        }
    }

    if (!FuncNode)
    {
        // R-03: provide helpful candidates when the function name matches but class is wrong
        TArray<FString> Candidates;
        for (TObjectIterator<UClass> ClassIt; ClassIt; ++ClassIt)
        {
            UClass* C = *ClassIt;
            if (!C) continue;
            for (TFieldIterator<UFunction> FIt(C, EFieldIteratorFlags::ExcludeSuper); FIt; ++FIt)
            {
                if (FIt->GetName().Equals(FunctionName, ESearchCase::IgnoreCase))
                {
                    Candidates.AddUnique(FString::Printf(TEXT("%s (target: %s)"),
                        *FIt->GetName(), *C->GetPathName()));
                    if (Candidates.Num() >= 5) break;
                }
            }
            if (Candidates.Num() >= 5) break;
        }
        FString Hint;
        if (Candidates.Num() > 0)
            Hint = TEXT(" -- Possible matches: ") + FString::Join(Candidates, TEXT(" | "));
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Could not create function node for '%s' (provided target='%s')%s"),
                *FunctionName, *TargetClass, *Hint));
    }

    // Apply inline pin default values
    const TSharedPtr<FJsonObject>* InlineParams;
    if (Params->TryGetObjectField(TEXT("params"), InlineParams))
    {
        for (auto& KV : (*InlineParams)->Values)
        {
            UEdGraphPin* Pin = FUnrealMCPCommonUtils::FindPin(FuncNode, KV.Key);
            if (!Pin) { UE_LOG(LogMCPNode, Warning, TEXT("  pin '%s' not found on node"), *KV.Key); continue; }
            FString StrVal;
            if (KV.Value->Type == EJson::String)  StrVal = KV.Value->AsString();
            else if (KV.Value->Type == EJson::Number) StrVal = FString::SanitizeFloat(KV.Value->AsNumber());
            else if (KV.Value->Type == EJson::Boolean) StrVal = KV.Value->AsBool() ? TEXT("true") : TEXT("false");
            ApplyPinValue(Graph, Pin, StrVal);
        }
    }

    if (Blueprint) FBlueprintEditorUtils::MarkBlueprintAsModified(Blueprint);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   FuncNode->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), FuncNode->GetName());
    // Return pin list so caller knows what to connect
    TArray<TSharedPtr<FJsonValue>> PinsArr;
    for (UEdGraphPin* P : FuncNode->Pins)
        if (P && !P->bHidden) PinsArr.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), PinsArr);
    return R;
}

// ============================================================
// add_blueprint_variable_get_node
// Params: blueprint_name, [graph_name], variable_name, [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintVariableGetNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);
    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);

    FString VarName;
    if (!Params->TryGetStringField(TEXT("variable_name"), VarName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'variable_name'"));

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_VariableGet* Node = FUnrealMCPCommonUtils::CreateVariableGetNode(Graph, BP, VarName, Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Failed to create VariableGet node for '%s'"), *VarName));

    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    TArray<TSharedPtr<FJsonValue>> PinsArr;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) PinsArr.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), PinsArr);
    return R;
}

// ============================================================
// add_blueprint_variable_set_node
// Params: blueprint_name, [graph_name], variable_name, [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintVariableSetNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);
    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);

    FString VarName;
    if (!Params->TryGetStringField(TEXT("variable_name"), VarName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'variable_name'"));

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_VariableSet* Node = FUnrealMCPCommonUtils::CreateVariableSetNode(Graph, BP, VarName, Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Failed to create VariableSet node for '%s'"), *VarName));

    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    TArray<TSharedPtr<FJsonValue>> PinsArr;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) PinsArr.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), PinsArr);
    return R;
}

// ============================================================
// add_blueprint_variable
// Params: blueprint_name, variable_name, variable_type,
//         [is_exposed], [default_value]
// Types: Boolean, Integer, Float, Double, String, Name, Text,
//        Vector, Rotator, Transform, Object/<class path>
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintVariable(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!BP) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));

    FString VarName, VarType;
    if (!Params->TryGetStringField(TEXT("variable_name"), VarName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'variable_name'"));
    if (!Params->TryGetStringField(TEXT("variable_type"), VarType))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'variable_type'"));

    FEdGraphPinType PinType;
    FString VarTypeLower = VarType.ToLower();

    if      (VarTypeLower == TEXT("boolean") || VarTypeLower == TEXT("bool"))
        PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
    else if (VarTypeLower == TEXT("integer") || VarTypeLower == TEXT("int") || VarTypeLower == TEXT("int32"))
        PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
    else if (VarTypeLower == TEXT("integer64") || VarTypeLower == TEXT("int64"))
        PinType.PinCategory = UEdGraphSchema_K2::PC_Int64;
    else if (VarTypeLower == TEXT("float"))
    {
        PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
        PinType.PinSubCategory = UEdGraphSchema_K2::PC_Float;
    }
    else if (VarTypeLower == TEXT("double"))
    {
        PinType.PinCategory = UEdGraphSchema_K2::PC_Real;
        PinType.PinSubCategory = UEdGraphSchema_K2::PC_Double;
    }
    else if (VarTypeLower == TEXT("string"))
        PinType.PinCategory = UEdGraphSchema_K2::PC_String;
    else if (VarTypeLower == TEXT("name"))
        PinType.PinCategory = UEdGraphSchema_K2::PC_Name;
    else if (VarTypeLower == TEXT("text"))
        PinType.PinCategory = UEdGraphSchema_K2::PC_Text;
    else if (VarTypeLower == TEXT("vector"))
    {
        PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
        PinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
    }
    else if (VarTypeLower == TEXT("rotator"))
    {
        PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
        PinType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
    }
    else if (VarTypeLower == TEXT("transform"))
    {
        PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
        PinType.PinSubCategoryObject = TBaseStructure<FTransform>::Get();
    }
    else if (VarType.StartsWith(TEXT("Object/")) || VarType.StartsWith(TEXT("object/")))
    {
        FString ClassPath = VarType.Mid(7); // strip "Object/"
        UClass* ObjClass = LoadObject<UClass>(nullptr, *ClassPath);
        if (!ObjClass) return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Object class not found: %s"), *ClassPath));
        PinType.PinCategory = UEdGraphSchema_K2::PC_Object;
        PinType.PinSubCategoryObject = ObjClass;
    }
    else
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Unsupported variable type '%s'. Supported: Boolean, Integer, Integer64, Float, Double, String, Name, Text, Vector, Rotator, Transform, Object/<ClassPath>"), *VarType));
    }

    FBlueprintEditorUtils::AddMemberVariable(BP, FName(*VarName), PinType);

    // Apply is_exposed and default_value to the FBPVariableDescription we just added
    FString DefaultValue;
    bool bHasDefault = Params->TryGetStringField(TEXT("default_value"), DefaultValue);

    bool bExposed = false;
    Params->TryGetBoolField(TEXT("is_exposed"), bExposed);

    for (FBPVariableDescription& V : BP->NewVariables)
    {
        if (V.VarName == FName(*VarName))
        {
            if (bExposed)
                V.PropertyFlags |= CPF_Edit | CPF_BlueprintVisible;

            if (bHasDefault && !DefaultValue.IsEmpty())
            {
                // Store as a metadata-driven default so it survives compile
                V.DefaultValue = DefaultValue;
                // Also set it via the Blueprint CDO so it takes effect immediately
                if (BP->GeneratedClass)
                {
                    FProperty* Prop = FindFProperty<FProperty>(BP->GeneratedClass, FName(*VarName));
                    if (Prop && BP->GeneratedClass->GetDefaultObject(false))
                    {
                        void* PropAddr = Prop->ContainerPtrToValuePtr<void>(
                            BP->GeneratedClass->GetDefaultObject(false));
                        if (PropAddr)
                        {
                            // Use ImportText to parse the default value string into the property
                            Prop->ImportText_Direct(*DefaultValue, PropAddr, nullptr, PPF_None);
                        }
                    }
                }
            }
            break;
        }
    }

    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("variable_name"), VarName);
    R->SetStringField(TEXT("variable_type"), VarType);
    if (bHasDefault)
        R->SetStringField(TEXT("default_value"), DefaultValue);
    return R;
}

// ============================================================
// add_blueprint_input_action_node
// Params: blueprint_name, [graph_name], action_name, [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintInputActionNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString ActionName;
    if (!Params->TryGetStringField(TEXT("action_name"), ActionName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'action_name'"));

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_InputAction* Node = FUnrealMCPCommonUtils::CreateInputActionNode(Graph, ActionName, Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create input action node"));

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    return R;
}

// ============================================================
// add_blueprint_self_reference
// Params: blueprint_name, [graph_name], [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintSelfReference(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_Self* Node = FUnrealMCPCommonUtils::CreateSelfReferenceNode(Graph, Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Self node"));

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    return R;
}

// ============================================================
// add_blueprint_get_self_component_reference
// Params: blueprint_name, [graph_name], component_name, [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintGetSelfComponentReference(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString CompName;
    if (!Params->TryGetStringField(TEXT("component_name"), CompName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'component_name'"));

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_VariableGet* Node = NewObject<UK2Node_VariableGet>(Graph);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create node"));

    Node->VariableReference.SetSelfMember(FName(*CompName));
    Node->NodePosX = (int32)Pos.X;
    Node->NodePosY = (int32)Pos.Y;
    Node->CreateNewGuid();
    Graph->AddNode(Node);
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    Node->ReconstructNode();

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    TArray<TSharedPtr<FJsonValue>> PinsArr;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) PinsArr.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), PinsArr);
    return R;
}

// ============================================================
// get_blueprint_graphs
// Returns the names and types of all graphs in a Blueprint:
//   EventGraph (ubergraph), function graphs, macro graphs.
// Params: blueprint_name
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleGetBlueprintGraphs(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!BP) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));

    TArray<TSharedPtr<FJsonValue>> GraphsArray;

    auto AddGraphEntry = [&](UEdGraph* G, const FString& GraphType)
    {
        if (!G) return;
        TSharedPtr<FJsonObject> GObj = MakeShared<FJsonObject>();
        GObj->SetStringField(TEXT("graph_name"), G->GetName());
        GObj->SetStringField(TEXT("graph_type"), GraphType);
        GObj->SetNumberField(TEXT("node_count"), (double)G->Nodes.Num());
        GraphsArray.Add(MakeShared<FJsonValueObject>(GObj));
    };

    for (UEdGraph* G : BP->UbergraphPages)
        AddGraphEntry(G, TEXT("EventGraph"));
    for (UEdGraph* G : BP->FunctionGraphs)
        AddGraphEntry(G, TEXT("Function"));
    for (UEdGraph* G : BP->MacroGraphs)
        AddGraphEntry(G, TEXT("Macro"));
    for (UEdGraph* G : BP->DelegateSignatureGraphs)
        AddGraphEntry(G, TEXT("Delegate"));

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetArrayField(TEXT("graphs"), GraphsArray);
    R->SetNumberField(TEXT("count"), (double)GraphsArray.Num());
    return R;
}

// ============================================================
// add_blueprint_enhanced_input_action_node
// Creates a K2Node_EnhancedInputAction wired to a UInputAction asset.
//
// Params:
//   blueprint_name  - asset name of the Blueprint
//   action_asset    - full asset path of the UInputAction,
//                     e.g. "/Game/OtherAssets/_input_/Actions/IA_Blink.IA_Blink"
//                     OR just the short asset name "IA_Blink" (will search via registry)
//   [graph_name]    - defaults to EventGraph
//   [node_position] - [X, Y]
//
// Returns node_id, node_name, pins
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintEnhancedInputActionNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString ActionAssetPath;
    if (!Params->TryGetStringField(TEXT("action_asset"), ActionAssetPath))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'action_asset'"));

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    // Resolve the UInputAction asset.
    UInputAction* InputAction = nullptr;

    // Try direct load first (caller may have passed the full object path)
    InputAction = LoadObject<UInputAction>(nullptr, *ActionAssetPath);

    // If that fails, search the Asset Registry by asset name (short name)
    if (!InputAction)
    {
        FAssetRegistryModule& ARModule =
            FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
        IAssetRegistry& AR = ARModule.Get();

        FARFilter Filter;
        Filter.ClassPaths.Add(UInputAction::StaticClass()->GetClassPathName());
        Filter.PackagePaths.Add(TEXT("/Game"));
        Filter.bRecursivePaths = true;

        TArray<FAssetData> Assets;
        AR.GetAssets(Filter, Assets);

        for (const FAssetData& Asset : Assets)
        {
            if (Asset.AssetName.ToString().Equals(ActionAssetPath, ESearchCase::IgnoreCase))
            {
                InputAction = Cast<UInputAction>(Asset.GetAsset());
                if (InputAction)
                {
                    UE_LOG(LogMCPNode, Display,
                        TEXT("add_blueprint_enhanced_input_action_node: Found '%s' at '%s'"),
                        *ActionAssetPath, *Asset.GetObjectPathString());
                    break;
                }
            }
        }
    }

    if (!InputAction)
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("UInputAction asset not found: '%s'"), *ActionAssetPath));

    // Create the K2Node_EnhancedInputAction node directly
    UK2Node_EnhancedInputAction* Node = NewObject<UK2Node_EnhancedInputAction>(Graph);
    if (!Node)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create K2Node_EnhancedInputAction"));

    Node->NodePosX = (int32)Pos.X;
    Node->NodePosY = (int32)Pos.Y;
    Node->CreateNewGuid();
    Graph->AddNode(Node);

    // Set the InputAction property on the node
    Node->InputAction = InputAction;
    
    // Initialize the node
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    Node->ReconstructNode();

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),         Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"),       Node->GetName());
    R->SetStringField(TEXT("input_action"),    InputAction->GetName());
    R->SetStringField(TEXT("input_action_path"), InputAction->GetPathName());
    TArray<TSharedPtr<FJsonValue>> PinsArr;
    for (UEdGraphPin* P : Node->Pins)
        if (P && !P->bHidden) PinsArr.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), PinsArr);
    return R;
}

// ============================================================
// get_node_by_id
// Fast single-node lookup  -  returns full pin data for one node.
// Avoids fetching the entire graph just to inspect one node.
//
// Params:
//   blueprint_name  - asset name
//   node_id         - GUID string OR short object name (e.g. "K2Node_CallFunction_40")
//   [graph_name]    - defaults to EventGraph
//   [include_hidden_pins] - default false
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleGetNodeById(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString NodeId;
    if (!Params->TryGetStringField(TEXT("node_id"), NodeId))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'node_id'"));

    bool bIncludeHidden = false;
    Params->TryGetBoolField(TEXT("include_hidden_pins"), bIncludeHidden);

    UEdGraphNode* Node = FindNodeByIdOrName(Graph, NodeId);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Node not found: %s"), *NodeId));

    TSharedPtr<FJsonObject> NObj = SerializeNode(Node);

    // If hidden pins were excluded by SerializeNode, optionally re-add them
    if (bIncludeHidden)
    {
        TArray<TSharedPtr<FJsonValue>> AllPins;
        for (UEdGraphPin* P : Node->Pins)
            if (P) AllPins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
        NObj->SetArrayField(TEXT("pins"), AllPins);
    }

    return NObj;
}

// ============================================================
// add_blueprint_get_component_node
//
// Creates a VariableGet node for a named component that lives in
// the Blueprint's SimpleConstructionScript (SCS).  This is the
// C++ equivalent of dragging a component from the Components panel
// into the Event Graph  -  the node type is exactly the same as
// add_blueprint_get_self_component_reference, but this variant
// searches the SCS to validate the component exists and returns
// the component's actual class as additional metadata.
//
// Params:
//   blueprint_name  - asset name of the Blueprint
//   component_name  - name of the SCS component (e.g. "StaticMeshComponent")
//   [graph_name]    - defaults to EventGraph
//   [node_position] - [X, Y]
//
// Returns: node_id, node_name, component_name, component_class, pins
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintGetComponentNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (!BP) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Blueprint not found for graph"));

    FString CompName;
    if (!Params->TryGetStringField(TEXT("component_name"), CompName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'component_name'"));

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    // Validate component exists in SCS and record its class for the response.
    FString ComponentClass;
    if (BP->SimpleConstructionScript)
    {
        for (USCS_Node* SCSNode : BP->SimpleConstructionScript->GetAllNodes())
        {
            if (SCSNode && SCSNode->GetVariableName().ToString().Equals(CompName, ESearchCase::IgnoreCase))
            {
                CompName = SCSNode->GetVariableName().ToString(); // normalise casing
                if (SCSNode->ComponentClass)
                    ComponentClass = SCSNode->ComponentClass->GetName();
                break;
            }
        }
    }
    // Also check generated class properties (handles components added from C++ parent)
    if (ComponentClass.IsEmpty() && BP->GeneratedClass)
    {
        for (TFieldIterator<FObjectProperty> PropIt(BP->GeneratedClass, EFieldIteratorFlags::IncludeSuper); PropIt; ++PropIt)
        {
            if (PropIt->GetName().Equals(CompName, ESearchCase::IgnoreCase))
            {
                CompName = PropIt->GetName();
                ComponentClass = PropIt->PropertyClass ? PropIt->PropertyClass->GetName() : TEXT("");
                break;
            }
        }
    }

    // Create the VariableGet node referencing the component as a self member.
    UK2Node_VariableGet* Node = NewObject<UK2Node_VariableGet>(Graph);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to NewObject UK2Node_VariableGet"));

    Node->VariableReference.SetSelfMember(FName(*CompName));
    Node->NodePosX = (int32)Pos.X;
    Node->NodePosY = (int32)Pos.Y;
    Node->CreateNewGuid();
    Graph->AddNode(Node);
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    Node->ReconstructNode();

    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),        Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"),      Node->GetName());
    R->SetStringField(TEXT("component_name"), CompName);
    if (!ComponentClass.IsEmpty())
        R->SetStringField(TEXT("component_class"), ComponentClass);
    TArray<TSharedPtr<FJsonValue>> PinsArr;
    for (UEdGraphPin* P : Node->Pins)
        if (P && !P->bHidden) PinsArr.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), PinsArr);
    return R;
}

// ============================================================
// add_blueprint_branch_node
// Adds a K2Node_IfThenElse (Branch) node to a graph.
// Params: blueprint_name, [graph_name], [node_position]
// Returns: node_id, node_name, pins (execute, Condition, then, else)
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintBranchNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_IfThenElse* Node = NewObject<UK2Node_IfThenElse>(Graph);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create K2Node_IfThenElse"));

    Node->NodePosX = (int32)Pos.X;
    Node->NodePosY = (int32)Pos.Y;
    Node->CreateNewGuid();
    Graph->AddNode(Node);
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    Node->ReconstructNode();

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    TArray<TSharedPtr<FJsonValue>> BranchPins;
    for (UEdGraphPin* P : Node->Pins)
        if (P && !P->bHidden) BranchPins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), BranchPins);
    return R;
}

// ============================================================
// add_blueprint_cast_node
// Adds a K2Node_DynamicCast targeting a given class.
// Params: blueprint_name, cast_target_class (short name like "AIController"
//         or full path "/Script/AIModule.AIController"),
//         [graph_name], [node_position]
// Returns: node_id, node_name, cast_class, pins
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintCastNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString TargetClassName;
    if (!Params->TryGetStringField(TEXT("cast_target_class"), TargetClassName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'cast_target_class' parameter"));

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    // Resolve the target class - try full path, then short name
    UClass* TargetClass = FindObject<UClass>(nullptr, *TargetClassName);
    if (!TargetClass)
        TargetClass = LoadObject<UClass>(nullptr, *TargetClassName);
    if (!TargetClass)
        TargetClass = FindFirstObject<UClass>(*TargetClassName, EFindFirstObjectOptions::None);
    
    // If still not found, try loading as a Blueprint and get its GeneratedClass
    if (!TargetClass)
    {
        UBlueprint* TargetBP = FUnrealMCPCommonUtils::FindBlueprintByShortName(TargetClassName);
        if (TargetBP && TargetBP->GeneratedClass)
            TargetClass = TargetBP->GeneratedClass;
    }

    // Check if we successfully resolved the target class
    if (!TargetClass)
    {
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Failed to resolve cast target class '%s'"), *TargetClassName));
    }

    UK2Node_DynamicCast* Node = NewObject<UK2Node_DynamicCast>(Graph);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create K2Node_DynamicCast"));

    Node->TargetType = TargetClass;

    Node->NodePosX = (int32)Pos.X;
    Node->NodePosY = (int32)Pos.Y;
    Node->CreateNewGuid();
    Graph->AddNode(Node);
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    Node->ReconstructNode();

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),    Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"),  Node->GetName());
    R->SetStringField(TEXT("cast_class"), TargetClass ? TargetClass->GetName() : TargetClassName);
    TArray<TSharedPtr<FJsonValue>> CastPins;
    for (UEdGraphPin* P : Node->Pins)
        if (P && !P->bHidden) CastPins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), CastPins);
    return R;
}

// ============================================================
// Helper macro: create a macro-instance node by name (ForLoop, Sequence, etc.)
// ============================================================
static UK2Node_MacroInstance* CreateMacroNode(UEdGraph* Graph, const FString& MacroName, const FVector2D& Pos)
{
    // Standard macros live in the engine's "StandardMacros" Blueprint
    static const FString MacroBPPath = TEXT("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros");
    UBlueprint* MacroBP = LoadObject<UBlueprint>(nullptr, *MacroBPPath);
    if (!MacroBP) return nullptr;

    UEdGraph* MacroGraph = nullptr;
    for (UEdGraph* G : MacroBP->MacroGraphs)
    {
        if (G && G->GetName().Equals(MacroName, ESearchCase::IgnoreCase))
        {
            MacroGraph = G;
            break;
        }
    }
    if (!MacroGraph) return nullptr;

    UK2Node_MacroInstance* Node = NewObject<UK2Node_MacroInstance>(Graph);
    Node->SetMacroGraph(MacroGraph);
    Node->NodePosX = (int32)Pos.X;
    Node->NodePosY = (int32)Pos.Y;
    Node->CreateNewGuid();
    Graph->AddNode(Node);
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    Node->ReconstructNode();
    return Node;
}

// ============================================================
// add_blueprint_for_loop_node  (R-07)
// Params: blueprint_name, [graph_name], [first_index=0], [last_index=9], [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintForLoopNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_MacroInstance* Node = CreateMacroNode(Graph, TEXT("ForLoop"), Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create ForLoop macro node"));

    // Set optional first/last index defaults
    double FirstIdx = 0, LastIdx = 9;
    Params->TryGetNumberField(TEXT("first_index"), FirstIdx);
    Params->TryGetNumberField(TEXT("last_index"),  LastIdx);
    if (UEdGraphPin* P = FUnrealMCPCommonUtils::FindPin(Node, TEXT("First Index")))
        ApplyPinValue(Graph, P, FString::Printf(TEXT("%d"), (int32)FirstIdx));
    if (UEdGraphPin* P = FUnrealMCPCommonUtils::FindPin(Node, TEXT("Last Index")))
        ApplyPinValue(Graph, P, FString::Printf(TEXT("%d"), (int32)LastIdx));

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    R->SetStringField(TEXT("node_type"), TEXT("ForLoop"));
    TArray<TSharedPtr<FJsonValue>> Pins;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) Pins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), Pins);
    return R;
}

// ============================================================
// add_blueprint_for_each_loop_node  (R-08)
// Params: blueprint_name, [graph_name], [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintForEachLoopNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_MacroInstance* Node = CreateMacroNode(Graph, TEXT("ForEachLoop"), Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create ForEachLoop macro node"));

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    R->SetStringField(TEXT("node_type"), TEXT("ForEachLoop"));
    TArray<TSharedPtr<FJsonValue>> Pins;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) Pins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), Pins);
    return R;
}

// ============================================================
// add_blueprint_sequence_node  (R-09)
// Params: blueprint_name, [graph_name], [num_outputs=2], [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintSequenceNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_MacroInstance* Node = CreateMacroNode(Graph, TEXT("Sequence"), Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Sequence macro node"));

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    R->SetStringField(TEXT("node_type"), TEXT("Sequence"));
    TArray<TSharedPtr<FJsonValue>> Pins;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) Pins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), Pins);
    return R;
}

// ============================================================
// add_blueprint_do_once_node  (R-10)
// Params: blueprint_name, [graph_name], [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintDoOnceNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_MacroInstance* Node = CreateMacroNode(Graph, TEXT("DoOnce"), Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create DoOnce macro node"));

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    R->SetStringField(TEXT("node_type"), TEXT("DoOnce"));
    TArray<TSharedPtr<FJsonValue>> Pins;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) Pins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), Pins);
    return R;
}

// ============================================================
// add_blueprint_gate_node
// Params: blueprint_name, [graph_name], [start_closed=false], [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintGateNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_MacroInstance* Node = CreateMacroNode(Graph, TEXT("Gate"), Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create Gate macro node"));

    bool bStartClosed = false;
    Params->TryGetBoolField(TEXT("start_closed"), bStartClosed);
    if (bStartClosed)
    {
        if (UEdGraphPin* P = FUnrealMCPCommonUtils::FindPin(Node, TEXT("Start Closed")))
            ApplyPinValue(Graph, P, TEXT("true"));
    }

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    R->SetStringField(TEXT("node_type"), TEXT("Gate"));
    TArray<TSharedPtr<FJsonValue>> Pins;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) Pins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), Pins);
    return R;
}

// ============================================================
// add_blueprint_flip_flop_node
// Params: blueprint_name, [graph_name], [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintFlipFlopNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_MacroInstance* Node = CreateMacroNode(Graph, TEXT("FlipFlop"), Pos);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create FlipFlop macro node"));

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    R->SetStringField(TEXT("node_type"), TEXT("FlipFlop"));
    TArray<TSharedPtr<FJsonValue>> Pins;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) Pins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), Pins);
    return R;
}

// ============================================================
// add_blueprint_switch_on_int_node  (R-11)
// Params: blueprint_name, [graph_name], [num_pins=2], [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintSwitchOnIntNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    // K2Node_SwitchInteger is the native node for Switch on Int
    UClass* SwitchClass = FindObject<UClass>(nullptr, TEXT("/Script/BlueprintGraph.K2Node_SwitchInteger"));
    if (!SwitchClass)
        SwitchClass = FindFirstObject<UClass>(TEXT("K2Node_SwitchInteger"), EFindFirstObjectOptions::None);

    if (!SwitchClass)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("K2Node_SwitchInteger class not found"));

    UEdGraphNode* RawNode = NewObject<UEdGraphNode>(Graph, SwitchClass);
    if (!RawNode) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create SwitchInteger node"));

    RawNode->NodePosX = (int32)Pos.X;
    RawNode->NodePosY = (int32)Pos.Y;
    RawNode->CreateNewGuid();
    Graph->AddNode(RawNode);
    RawNode->PostPlacedNewNode();
    RawNode->AllocateDefaultPins();
    RawNode->ReconstructNode();

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   RawNode->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), RawNode->GetName());
    R->SetStringField(TEXT("node_type"), TEXT("SwitchOnInt"));
    TArray<TSharedPtr<FJsonValue>> Pins;
    for (UEdGraphPin* P : RawNode->Pins) if (P && !P->bHidden) Pins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), Pins);
    return R;
}

// ============================================================
// add_blueprint_spawn_actor_node  (R-12)
// Params: blueprint_name, [graph_name], actor_class, [node_position]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintSpawnActorNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString ActorClassName;
    Params->TryGetStringField(TEXT("actor_class"), ActorClassName);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UK2Node_SpawnActorFromClass* Node = NewObject<UK2Node_SpawnActorFromClass>(Graph);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create SpawnActorFromClass node"));

    Node->NodePosX = (int32)Pos.X;
    Node->NodePosY = (int32)Pos.Y;
    Node->CreateNewGuid();
    Graph->AddNode(Node);
    
    // UK2Node_SpawnActorFromClass requires a unique initialization sequence.
    // We ONLY call AllocateDefaultPins - no PostPlacedNewNode or ReconstructNode.
    // The Blueprint editor will handle full initialization when the graph is opened.
    Node->AllocateDefaultPins();

    // Optionally set the class pin default
    if (!ActorClassName.IsEmpty())
    {
        UClass* ActorClass = FindFirstObject<UClass>(*ActorClassName, EFindFirstObjectOptions::None);
        if (!ActorClass)
        {
            for (TObjectIterator<UClass> It; It; ++It)
            {
                if (It->GetName().Equals(ActorClassName, ESearchCase::IgnoreCase))
                { ActorClass = *It; break; }
            }
        }
        if (ActorClass)
        {
            if (UEdGraphPin* ClassPin = FUnrealMCPCommonUtils::FindPin(Node, TEXT("Class")))
            {
                const UEdGraphSchema_K2* K2 = Cast<const UEdGraphSchema_K2>(Graph->GetSchema());
                if (K2) K2->TrySetDefaultObject(*ClassPin, ActorClass);
            }
        }
    }

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    R->SetStringField(TEXT("node_type"), TEXT("SpawnActorFromClass"));
    if (!ActorClassName.IsEmpty()) R->SetStringField(TEXT("actor_class"), ActorClassName);
    TArray<TSharedPtr<FJsonValue>> Pins;
    for (UEdGraphPin* P : Node->Pins) if (P && !P->bHidden) Pins.Add(MakeShared<FJsonValueObject>(SerializePin(P)));
    R->SetArrayField(TEXT("pins"), Pins);
    return R;
}

// ============================================================
// add_blueprint_comment_node  (R-13 / L-018)
// Params: blueprint_name, [graph_name], [comment_text], [node_position], [width=400], [height=200], [color]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleAddBlueprintCommentNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString CommentText = TEXT("Comment");
    Params->TryGetStringField(TEXT("comment_text"), CommentText);

    FVector2D Pos(0, 0);
    if (Params->HasField(TEXT("node_position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    double Width = 400, Height = 200;
    Params->TryGetNumberField(TEXT("width"),  Width);
    Params->TryGetNumberField(TEXT("height"), Height);

    // Optional RGBA color (array of 4 floats 0..1)
    FLinearColor Color(1.f, 1.f, 1.f, 0.6f);
    const TArray<TSharedPtr<FJsonValue>>* ColorArr;
    if (Params->TryGetArrayField(TEXT("color"), ColorArr) && ColorArr->Num() >= 3)
    {
        Color.R = (float)(*ColorArr)[0]->AsNumber();
        Color.G = (float)(*ColorArr)[1]->AsNumber();
        Color.B = (float)(*ColorArr)[2]->AsNumber();
        Color.A = ColorArr->Num() >= 4 ? (float)(*ColorArr)[3]->AsNumber() : 0.6f;
    }

    UEdGraphNode_Comment* Node = NewObject<UEdGraphNode_Comment>(Graph);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to create comment node"));

    Node->NodeComment = CommentText;
    Node->NodePosX    = (int32)Pos.X;
    Node->NodePosY    = (int32)Pos.Y;
    Node->NodeWidth   = (int32)Width;
    Node->NodeHeight  = (int32)Height;
    Node->CommentColor = Color;

    Node->CreateNewGuid();
    Graph->AddNode(Node);
    Node->PostPlacedNewNode();

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),      Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"),    Node->GetName());
    R->SetStringField(TEXT("comment_text"), CommentText);
    R->SetNumberField(TEXT("pos_x"),  (double)Node->NodePosX);
    R->SetNumberField(TEXT("pos_y"),  (double)Node->NodePosY);
    R->SetNumberField(TEXT("width"),  (double)Node->NodeWidth);
    R->SetNumberField(TEXT("height"), (double)Node->NodeHeight);
    return R;
}

// ============================================================
// move_blueprint_node  (R-14 / L-019)
// Params: blueprint_name, [graph_name], node_id, node_position [x,y]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleMoveBlueprintNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Err;
    UEdGraph* Graph = ResolveGraph(Params, Err);
    if (!Graph) return FUnrealMCPCommonUtils::CreateErrorResponse(Err);

    FString NodeId;
    if (!Params->TryGetStringField(TEXT("node_id"), NodeId))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'node_id'"));

    if (!Params->HasField(TEXT("node_position")))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'node_position'"));
    FVector2D Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));

    UEdGraphNode* Node = FindNodeByIdOrName(Graph, NodeId);
    if (!Node) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Node not found: %s"), *NodeId));

    Node->NodePosX = (int32)Pos.X;
    Node->NodePosY = (int32)Pos.Y;

    UBlueprint* BP = FBlueprintEditorUtils::FindBlueprintForGraph(Graph);
    if (BP) FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("node_id"),   Node->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), Node->GetName());
    R->SetNumberField(TEXT("new_pos_x"), (double)Node->NodePosX);
    R->SetNumberField(TEXT("new_pos_y"), (double)Node->NodePosY);
    return R;
}

// ============================================================
// get_blueprint_variable_defaults  (R-18 / L-013)
// Params: blueprint_name, [variable_name] (if omitted, returns all)
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleGetBlueprintVariableDefaults(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!BP) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));

    UObject* CDO = BP->GeneratedClass ? BP->GeneratedClass->GetDefaultObject(false) : nullptr;

    FString FilterVar;
    Params->TryGetStringField(TEXT("variable_name"), FilterVar);

    TArray<TSharedPtr<FJsonValue>> VarsArray;
    for (const FBPVariableDescription& VarDesc : BP->NewVariables)
    {
        if (!FilterVar.IsEmpty() &&
            !VarDesc.VarName.ToString().Equals(FilterVar, ESearchCase::IgnoreCase))
            continue;

        TSharedPtr<FJsonObject> VObj = MakeShared<FJsonObject>();
        VObj->SetStringField(TEXT("variable_name"), VarDesc.VarName.ToString());
        VObj->SetStringField(TEXT("variable_type"), VarDesc.VarType.PinCategory.ToString());
        VObj->SetStringField(TEXT("default_value"),  VarDesc.DefaultValue);
        VObj->SetStringField(TEXT("tooltip"),        VarDesc.HasMetaData(FBlueprintMetadata::MD_Tooltip) ?
            VarDesc.GetMetaData(FBlueprintMetadata::MD_Tooltip) : TEXT(""));

        // Also read live CDO value if possible
        if (CDO)
        {
            FProperty* Prop = CDO->GetClass()->FindPropertyByName(VarDesc.VarName);
            if (Prop)
            {
                FString ExportedVal;
                Prop->ExportTextItem_Direct(ExportedVal, Prop->ContainerPtrToValuePtr<void>(CDO), nullptr, CDO, PPF_None);
                VObj->SetStringField(TEXT("cdo_value"), ExportedVal);
            }
        }

        VarsArray.Add(MakeShared<FJsonValueObject>(VObj));
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("blueprint"), BlueprintName);
    R->SetArrayField(TEXT("variables"),  VarsArray);
    R->SetNumberField(TEXT("count"),     (double)VarsArray.Num());
    return R;
}

// ============================================================
// set_blueprint_variable_default  (R-19 / L-013)
// Params: blueprint_name, variable_name, default_value (string)
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleSetBlueprintVariableDefault(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BlueprintName, VarName, DefaultValue;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("variable_name"),  VarName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'variable_name'"));
    if (!Params->TryGetStringField(TEXT("default_value"),  DefaultValue))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'default_value'"));

    UBlueprint* BP = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!BP) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));

    for (FBPVariableDescription& VarDesc : BP->NewVariables)
    {
        if (VarDesc.VarName.ToString().Equals(VarName, ESearchCase::IgnoreCase))
        {
            VarDesc.DefaultValue = DefaultValue;

            // Also apply to CDO via ImportText for live update
            UObject* CDO = BP->GeneratedClass ? BP->GeneratedClass->GetDefaultObject(false) : nullptr;
            if (CDO)
            {
                FProperty* Prop = CDO->GetClass()->FindPropertyByName(VarDesc.VarName);
                if (Prop)
                    Prop->ImportText_Direct(*DefaultValue, Prop->ContainerPtrToValuePtr<void>(CDO), CDO, PPF_None);
            }

            FBlueprintEditorUtils::MarkBlueprintAsModified(BP);

            TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
            R->SetStringField(TEXT("blueprint"),     BlueprintName);
            R->SetStringField(TEXT("variable_name"), VarName);
            R->SetStringField(TEXT("default_value"), DefaultValue);
            R->SetBoolField(TEXT("success"), true);
            return R;
        }
    }

    return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Variable not found in Blueprint: %s"), *VarName));
}

// ============================================================
// get_blueprint_components  (R-21 / L-020)
// Returns SCS nodes + native C++ components from a Blueprint
// Params: blueprint_name
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleGetBlueprintComponents(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BlueprintName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BlueprintName))
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!BP) return FUnrealMCPCommonUtils::CreateErrorResponse(
        FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));

    TArray<TSharedPtr<FJsonValue>> Components;

    // --- SCS (Simple Construction Script) components ---
    if (BP->SimpleConstructionScript)
    {
        for (USCS_Node* SCSNode : BP->SimpleConstructionScript->GetAllNodes())
        {
            if (!SCSNode) continue;
            TSharedPtr<FJsonObject> CObj = MakeShared<FJsonObject>();
            CObj->SetStringField(TEXT("name"),   SCSNode->GetVariableName().ToString());
            CObj->SetStringField(TEXT("source"), TEXT("SCS"));
            if (SCSNode->ComponentClass)
                CObj->SetStringField(TEXT("class"), SCSNode->ComponentClass->GetName());
            if (SCSNode->ComponentTemplate)
            {
                // Collect the component's UProperties that are not default
                UActorComponent* Template = SCSNode->ComponentTemplate;
                UActorComponent* CDOComp  = SCSNode->ComponentClass ?
                    Cast<UActorComponent>(SCSNode->ComponentClass->GetDefaultObject(false)) : nullptr;
                TSharedPtr<FJsonObject> Props = MakeShared<FJsonObject>();
                for (TFieldIterator<FProperty> PropIt(Template->GetClass(), EFieldIteratorFlags::IncludeSuper); PropIt; ++PropIt)
                {
                    if (!PropIt->HasAnyPropertyFlags(CPF_Edit)) continue;
                    FString Val;
                    PropIt->ExportTextItem_Direct(Val, PropIt->ContainerPtrToValuePtr<void>(Template), nullptr, Template, PPF_None);
                    FString DefaultVal;
                    if (CDOComp)
                        PropIt->ExportTextItem_Direct(DefaultVal, PropIt->ContainerPtrToValuePtr<void>(CDOComp), nullptr, CDOComp, PPF_None);
                    if (Val != DefaultVal)
                        Props->SetStringField(PropIt->GetName(), Val);
                }
                CObj->SetObjectField(TEXT("modified_properties"), Props);
            }
            Components.Add(MakeShared<FJsonValueObject>(CObj));
        }
    }

    // --- Native C++ component properties from the generated class ---
    if (BP->GeneratedClass)
    {
        for (TFieldIterator<FObjectProperty> PropIt(BP->GeneratedClass, EFieldIteratorFlags::IncludeSuper); PropIt; ++PropIt)
        {
            if (!PropIt->PropertyClass) continue;
            if (!PropIt->PropertyClass->IsChildOf(UActorComponent::StaticClass())) continue;
            // Skip if already listed via SCS
            bool bAlreadyListed = false;
            for (TSharedPtr<FJsonValue> Existing : Components)
            {
                FString ExName;
                Existing->AsObject()->TryGetStringField(TEXT("name"), ExName);
                if (ExName.Equals(PropIt->GetName(), ESearchCase::IgnoreCase)) { bAlreadyListed = true; break; }
            }
            if (bAlreadyListed) continue;

            TSharedPtr<FJsonObject> CObj = MakeShared<FJsonObject>();
            CObj->SetStringField(TEXT("name"),   PropIt->GetName());
            CObj->SetStringField(TEXT("source"), TEXT("NativeC++"));
            CObj->SetStringField(TEXT("class"),  PropIt->PropertyClass->GetName());
            Components.Add(MakeShared<FJsonValueObject>(CObj));
        }
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("blueprint"),  BlueprintName);
    R->SetArrayField(TEXT("components"),  Components);
    R->SetNumberField(TEXT("count"),      (double)Components.Num());
    return R;
}

// ============================================================
// setup_navmesh  (R-23 / L-014)
// Spawns a NavMeshBoundsVolume in the level and optionally rebuilds.
// Params: [extent] = [x,y,z] half-extents (default 5000,5000,500)
//         [location] = [x,y,z] centre (default 0,0,0)
//         [rebuild=true] trigger nav system rebuild
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPBlueprintNodeCommands::HandleSetupNavMesh(
    const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("No editor world available"));

    // Default extent and location
    FVector Extent(5000.f, 5000.f, 500.f);
    FVector Location(0.f, 0.f, 0.f);

    if (Params->HasField(TEXT("extent")))
        Extent = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("extent"));
    if (Params->HasField(TEXT("location")))
        Location = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));

    bool bRebuild = true;
    Params->TryGetBoolField(TEXT("rebuild"), bRebuild);

    // Check for existing NavMeshBoundsVolume
    TArray<AActor*> Existing;
    UGameplayStatics::GetAllActorsOfClass(World, ANavMeshBoundsVolume::StaticClass(), Existing);
    if (Existing.Num() > 0)
    {
        // Resize existing volume instead of adding a new one
        ANavMeshBoundsVolume* ExistingVol = Cast<ANavMeshBoundsVolume>(Existing[0]);
        if (ExistingVol)
        {
            ExistingVol->SetActorLocation(Location);
            ExistingVol->SetActorScale3D(Extent / 100.f); // default brush radius is 100

            if (bRebuild)
            {
                UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
                if (NavSys) NavSys->Build();
            }

            TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
            R->SetStringField(TEXT("action"),   TEXT("resized_existing"));
            R->SetStringField(TEXT("actor"),    ExistingVol->GetName());
            R->SetBoolField(TEXT("rebuilt"),    bRebuild);
            R->SetBoolField(TEXT("success"),    true);
            return R;
        }
    }

    // Spawn a new volume
    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = TEXT("NavMeshBoundsVolume");

    FTransform SpawnTransform;
    SpawnTransform.SetLocation(Location);

    ANavMeshBoundsVolume* NewVol = World->SpawnActor<ANavMeshBoundsVolume>(
        ANavMeshBoundsVolume::StaticClass(), SpawnTransform, SpawnParams);

    if (!NewVol)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to spawn NavMeshBoundsVolume"));

    // Scale the brush so it covers the requested extent
    NewVol->SetActorScale3D(Extent / 100.f);

    if (bRebuild)
    {
        UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
        if (NavSys) NavSys->Build();
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetStringField(TEXT("action"),  TEXT("created"));
    R->SetStringField(TEXT("actor"),   NewVol->GetName());
    R->SetBoolField(TEXT("rebuilt"),   bRebuild);
    R->SetBoolField(TEXT("success"),   true);
    return R;
}
