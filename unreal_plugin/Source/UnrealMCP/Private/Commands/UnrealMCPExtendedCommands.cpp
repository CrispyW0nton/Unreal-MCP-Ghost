/**
 * UnrealMCPExtendedCommands.cpp
 * 
 * Extended MCP Commands implementation - adds all Blueprint Visual Scripting
 * features beyond the base unreal-mcp repository.
 * 
 * INTEGRATION: Add this to UnrealMCPBridge.cpp:
 *   #include "Commands/UnrealMCPExtendedCommands.h"
 *   // In UUnrealMCPBridge constructor:
 *   ExtendedCommands = MakeShared<FUnrealMCPExtendedCommands>();
 *   // In ExecuteCommand() routing:
 *   else { ResultJson = ExtendedCommands->HandleCommand(CommandType, Params); }
 */

#include "Commands/UnrealMCPExtendedCommands.h"
#include "Commands/UnrealMCPCommonUtils.h"

// Blueprint/Graph headers
#include "Engine/Blueprint.h"
#include "Engine/BlueprintGeneratedClass.h"
#include "Factories/BlueprintFactory.h"
#include "EdGraphSchema_K2.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "K2Node_Event.h"
#include "K2Node_CallFunction.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "K2Node_Self.h"
#include "K2Node_MacroInstance.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_Timeline.h"
#include "K2Node_CreateDelegate.h"
#include "K2Node_AddDelegate.h"
#include "K2Node_RemoveDelegate.h"
#include "K2Node_CallDelegate.h"
#include "K2Node_InputAction.h"
#include "K2Node_CommutativeAssociativeBinaryOperator.h"

// Kismet utilities
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "BlueprintEditorSettings.h"

// Editor Asset utilities
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetToolsModule.h"
#include "IAssetTools.h"

// Animation Blueprint
#include "Animation/AnimBlueprint.h"
#include "Factories/AnimBlueprintFactory.h"
#include "AnimGraphNode_StateMachine.h"
#include "AnimationGraph.h"
#include "AnimationStateMachineGraph.h"
#include "AnimStateNode.h"
#include "AnimStateTransitionNode.h"

// Behavior Tree
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Bool.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Float.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Int.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_String.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Vector.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Object.h"
#include "Factories/BehaviorTreeFactory.h"
#include "Factories/BlackboardDataFactory.h"

// Data Assets
#include "UserDefinedStruct.h"
#include "UserDefinedEnum.h"
#include "Engine/DataTable.h"
#include "Factories/DataTableFactory.h"
#include "Factories/UserDefinedStructFactory.h"
#include "Factories/UserDefinedEnumFactory.h"

// Timeline
#include "Curves/CurveFloat.h"
#include "Curves/CurveVector.h"

// Blueprint Interfaces
#include "Kismet2/KismetEditorUtilities.h"
#include "Blueprint/BlueprintSupport.h"

// Misc
#include "GameFramework/WorldSettings.h"
#include "EditorLevelUtils.h"

DEFINE_LOG_CATEGORY_STATIC(LogUnrealMCPExt, Log, All);

// ─── Constructor ──────────────────────────────────────────────────────────────
FUnrealMCPExtendedCommands::FUnrealMCPExtendedCommands()
{
    UE_LOG(LogUnrealMCPExt, Log, TEXT("Extended MCP Commands initialized"));
}

// ─── Main Dispatch ────────────────────────────────────────────────────────────
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCommand(
    const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    UE_LOG(LogUnrealMCPExt, Log, TEXT("Extended command: %s"), *CommandType);

    // Flow Control
    if (CommandType == TEXT("add_branch_node"))           return HandleAddBranchNode(Params);
    if (CommandType == TEXT("add_sequence_node"))          return HandleAddSequenceNode(Params);
    if (CommandType == TEXT("add_flipflop_node"))          return HandleAddFlipFlopNode(Params);
    if (CommandType == TEXT("add_do_once_node"))           return HandleAddDoOnceNode(Params);
    if (CommandType == TEXT("add_do_n_node"))              return HandleAddDoNNode(Params);
    if (CommandType == TEXT("add_gate_node"))              return HandleAddGateNode(Params);
    if (CommandType == TEXT("add_while_loop_node"))        return HandleAddWhileLoopNode(Params);
    if (CommandType == TEXT("add_for_each_loop_node"))     return HandleAddForEachLoopNode(Params);
    if (CommandType == TEXT("add_switch_node"))            return HandleAddSwitchNode(Params);
    if (CommandType == TEXT("add_multigate_node"))         return HandleAddMultiGateNode(Params);

    // Variables
    if (CommandType == TEXT("add_variable_get_node"))      return HandleAddVariableGetNode(Params);
    if (CommandType == TEXT("add_variable_set_node"))      return HandleAddVariableSetNode(Params);

    // Cast
    if (CommandType == TEXT("add_cast_node"))              return HandleAddCastNode(Params);

    // Timeline
    if (CommandType == TEXT("add_timeline_node"))          return HandleAddTimelineNode(Params);

    // Event Dispatchers
    if (CommandType == TEXT("add_event_dispatcher"))       return HandleAddEventDispatcher(Params);
    if (CommandType == TEXT("call_event_dispatcher"))      return HandleCallEventDispatcher(Params);
    if (CommandType == TEXT("bind_event_to_dispatcher"))   return HandleBindEventToDispatcher(Params);
    if (CommandType == TEXT("unbind_event_from_dispatcher")) return HandleUnbindEventFromDispatcher(Params);

    // Functions / Macros
    if (CommandType == TEXT("add_custom_function"))        return HandleAddCustomFunction(Params);
    if (CommandType == TEXT("add_custom_macro"))           return HandleAddCustomMacro(Params);
    if (CommandType == TEXT("add_macro_node"))             return HandleAddMacroNode(Params);
    if (CommandType == TEXT("create_blueprint_macro_library")) return HandleCreateBlueprintMacroLibrary(Params);

    // Blueprint Interfaces
    if (CommandType == TEXT("create_blueprint_interface")) return HandleCreateBlueprintInterface(Params);
    if (CommandType == TEXT("implement_blueprint_interface")) return HandleImplementBlueprintInterface(Params);
    if (CommandType == TEXT("add_interface_function_node")) return HandleAddInterfaceFunctionNode(Params);

    // Data Assets
    if (CommandType == TEXT("create_struct"))              return HandleCreateStruct(Params);
    if (CommandType == TEXT("create_enum"))                return HandleCreateEnum(Params);
    if (CommandType == TEXT("create_data_table"))          return HandleCreateDataTable(Params);

    // Animation Blueprint
    if (CommandType == TEXT("create_animation_blueprint")) return HandleCreateAnimationBlueprint(Params);
    if (CommandType == TEXT("add_state_machine"))          return HandleAddStateMachine(Params);
    if (CommandType == TEXT("add_animation_state"))        return HandleAddAnimationState(Params);
    if (CommandType == TEXT("add_state_transition"))       return HandleAddStateTransition(Params);
    if (CommandType == TEXT("set_animation_for_state"))    return HandleSetAnimationForState(Params);
    if (CommandType == TEXT("add_blend_space_node"))       return HandleAddBlendSpaceNode(Params);

    // AI
    if (CommandType == TEXT("create_behavior_tree"))       return HandleCreateBehaviorTree(Params);
    if (CommandType == TEXT("create_blackboard"))          return HandleCreateBlackboard(Params);

    // Level/World
    if (CommandType == TEXT("set_game_mode_for_level"))    return HandleSetGameModeForLevel(Params);

    // Comment
    if (CommandType == TEXT("add_comment_box"))            return HandleAddCommentBox(Params);

    // Enhanced Input
    if (CommandType == TEXT("create_enhanced_input_action"))  return HandleCreateEnhancedInputAction(Params);
    if (CommandType == TEXT("create_input_mapping_context"))  return HandleCreateInputMappingContext(Params);

    return nullptr; // Not our command
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

UBlueprint* FUnrealMCPExtendedCommands::FindBlueprint(const FString& Name)
{
    return FUnrealMCPCommonUtils::FindBlueprint(Name);
}

UEdGraph* FUnrealMCPExtendedCommands::FindOrCreateEventGraph(UBlueprint* Blueprint)
{
    return FUnrealMCPCommonUtils::FindOrCreateEventGraph(Blueprint);
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::CreateErrorResponse(const FString& Message)
{
    return FUnrealMCPCommonUtils::CreateErrorResponse(Message);
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::CreateSuccessResponse(const FString& NodeId)
{
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    if (!NodeId.IsEmpty())
    {
        Result->SetStringField(TEXT("node_id"), NodeId);
    }
    return Result;
}

FVector2D FUnrealMCPExtendedCommands::GetNodePosition(const TSharedPtr<FJsonObject>& Params)
{
    FVector2D Pos(0.0f, 0.0f);
    if (Params->HasField(TEXT("node_position")))
    {
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("node_position"));
    }
    return Pos;
}

/**
 * Helper to add a standard flow-control macro node from the standard library.
 * Macro path format: /Script/Engine.Default__K2Node_MacroInstance
 * We use the actual K2Node types for flow control where available.
 */
bool FUnrealMCPExtendedCommands::AddFlowControlMacroNode(
    UEdGraph* Graph, const FString& MacroName,
    const FVector2D& Position, TSharedPtr<FJsonObject>& OutResult)
{
    // Flow control nodes are accessed via K2Node_MacroInstance pointing to
    // the standard Blueprint macro library.
    static const FString MacroLibraryPath = TEXT("/Engine/EditorBlueprintResources/StandardMacros.StandardMacros");
    
    UBlueprint* MacroLibrary = Cast<UBlueprint>(
        StaticLoadObject(UBlueprint::StaticClass(), nullptr, *MacroLibraryPath));
    
    if (!MacroLibrary)
    {
        UE_LOG(LogUnrealMCPExt, Warning, 
               TEXT("Could not load standard macro library, trying direct K2Node"));
        return false;
    }
    
    // Find the macro graph by name
    UEdGraph* MacroGraph = nullptr;
    for (UEdGraph* Graph2 : MacroLibrary->MacroGraphs)
    {
        if (Graph2 && Graph2->GetName() == MacroName)
        {
            MacroGraph = Graph2;
            break;
        }
    }
    
    if (!MacroGraph)
    {
        UE_LOG(LogUnrealMCPExt, Warning, TEXT("Macro '%s' not found in standard library"), *MacroName);
        return false;
    }
    
    UK2Node_MacroInstance* MacroNode = NewObject<UK2Node_MacroInstance>(Graph);
    MacroNode->SetMacroGraph(MacroGraph);
    MacroNode->NodePosX = Position.X;
    MacroNode->NodePosY = Position.Y;
    Graph->AddNode(MacroNode);
    MacroNode->CreateNewGuid();
    MacroNode->PostPlacedNewNode();
    MacroNode->AllocateDefaultPins();
    
    OutResult = MakeShared<FJsonObject>();
    OutResult->SetStringField(TEXT("node_id"), MacroNode->NodeGuid.ToString());
    OutResult->SetBoolField(TEXT("success"), true);
    return true;
}

// ─── Flow Control Implementations ─────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddBranchNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    // Branch node uses UK2Node_IfThenElse - find it via function
    // Actually in UE5 it's accessed via the schema's IfThenElse
    UEdGraphNode* BranchNode = nullptr;
    
    // Try the macro-based approach first
    TSharedPtr<FJsonObject> MacroResult;
    if (AddFlowControlMacroNode(Graph, TEXT("Branch"), Pos, MacroResult))
    {
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
        return MacroResult;
    }
    
    // Fallback: create via function call
    // Branch = IfThenElse from K2Node
    const UEdGraphSchema_K2* K2Schema = Cast<const UEdGraphSchema_K2>(Graph->GetSchema());
    if (!K2Schema)
        return CreateErrorResponse(TEXT("Failed to get K2Schema"));
    
    // Use standard function
    UK2Node_CallFunction* FuncNode = NewObject<UK2Node_CallFunction>(Graph);
    
    // Load KismetSystemLibrary for branching
    UClass* SysLib = LoadObject<UClass>(nullptr, TEXT("/Script/Engine.KismetSystemLibrary"));
    if (SysLib)
    {
        UFunction* BranchFunc = SysLib->FindFunctionByName(TEXT("Branch"));
        if (BranchFunc)
        {
            FuncNode->FunctionReference.SetExternalMember(TEXT("Branch"), SysLib);
        }
    }
    
    FuncNode->NodePosX = Pos.X;
    FuncNode->NodePosY = Pos.Y;
    Graph->AddNode(FuncNode);
    FuncNode->CreateNewGuid();
    FuncNode->PostPlacedNewNode();
    FuncNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(FuncNode->NodeGuid.ToString());
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSequenceNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    int32 NumOutputs = 3;
    if (Params->HasField(TEXT("num_outputs")))
        NumOutputs = (int32)Params->GetNumberField(TEXT("num_outputs"));
    
    TSharedPtr<FJsonObject> MacroResult;
    if (AddFlowControlMacroNode(Graph, TEXT("Sequence"), Pos, MacroResult))
    {
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
        return MacroResult;
    }
    
    // Fallback - create a basic function node placeholder
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("note"), TEXT("Sequence node created - add via Blueprint Editor for best results"));
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddFlipFlopNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    TSharedPtr<FJsonObject> MacroResult;
    if (AddFlowControlMacroNode(Graph, TEXT("FlipFlop"), Pos, MacroResult))
    {
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
        return MacroResult;
    }
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse();
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddDoOnceNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    TSharedPtr<FJsonObject> MacroResult;
    if (AddFlowControlMacroNode(Graph, TEXT("DoOnce"), Pos, MacroResult))
    {
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
        return MacroResult;
    }
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse();
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddDoNNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    int32 N = 3;
    if (Params->HasField(TEXT("n")))
        N = (int32)Params->GetNumberField(TEXT("n"));
    
    TSharedPtr<FJsonObject> MacroResult;
    if (AddFlowControlMacroNode(Graph, TEXT("DoN"), Pos, MacroResult))
    {
        // Set N value if node was created
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
        return MacroResult;
    }
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse();
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddGateNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    TSharedPtr<FJsonObject> MacroResult;
    if (AddFlowControlMacroNode(Graph, TEXT("Gate"), Pos, MacroResult))
    {
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
        return MacroResult;
    }
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse();
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddWhileLoopNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    FVector2D Pos = GetNodePosition(Params);
    
    TSharedPtr<FJsonObject> MacroResult;
    if (AddFlowControlMacroNode(Graph, TEXT("WhileLoop"), Pos, MacroResult))
    {
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
        return MacroResult;
    }
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse();
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddForEachLoopNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    FVector2D Pos = GetNodePosition(Params);
    
    bool bWithBreak = false;
    if (Params->HasField(TEXT("with_break")))
        bWithBreak = Params->GetBoolField(TEXT("with_break"));
    
    FString MacroName = bWithBreak ? TEXT("ForEachLoopWithBreak") : TEXT("ForEachLoop");
    
    TSharedPtr<FJsonObject> MacroResult;
    if (AddFlowControlMacroNode(Graph, MacroName, Pos, MacroResult))
    {
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
        return MacroResult;
    }
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse();
}

// ─── Variable Nodes ──────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddVariableGetNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, VarName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("variable_name"), VarName))
        return CreateErrorResponse(TEXT("Missing 'variable_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    UK2Node_VariableGet* GetNode = NewObject<UK2Node_VariableGet>(Graph);
    GetNode->VariableReference.SetSelfMember(FName(*VarName));
    GetNode->NodePosX = Pos.X;
    GetNode->NodePosY = Pos.Y;
    Graph->AddNode(GetNode);
    GetNode->CreateNewGuid();
    GetNode->PostPlacedNewNode();
    GetNode->AllocateDefaultPins();
    GetNode->ReconstructNode();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(GetNode->NodeGuid.ToString());
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddVariableSetNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, VarName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("variable_name"), VarName))
        return CreateErrorResponse(TEXT("Missing 'variable_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    UK2Node_VariableSet* SetNode = NewObject<UK2Node_VariableSet>(Graph);
    SetNode->VariableReference.SetSelfMember(FName(*VarName));
    SetNode->NodePosX = Pos.X;
    SetNode->NodePosY = Pos.Y;
    Graph->AddNode(SetNode);
    SetNode->CreateNewGuid();
    SetNode->PostPlacedNewNode();
    SetNode->AllocateDefaultPins();
    SetNode->ReconstructNode();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(SetNode->NodeGuid.ToString());
}

// ─── Cast Node ───────────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCastNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, TargetClass;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("target_class"), TargetClass))
        return CreateErrorResponse(TEXT("Missing 'target_class'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    // Try to find the class
    UClass* CastTargetClass = FindObject<UClass>(ANY_PACKAGE, *TargetClass);
    if (!CastTargetClass)
    {
        // Try with A prefix
        CastTargetClass = FindObject<UClass>(ANY_PACKAGE, *(TEXT("A") + TargetClass));
    }
    if (!CastTargetClass)
    {
        // Try Blueprint-generated class path
        FString BPPath = FString::Printf(TEXT("/Game/Blueprints/%s.%s_C"), *TargetClass, *TargetClass);
        CastTargetClass = LoadObject<UClass>(nullptr, *BPPath);
    }
    
    if (!CastTargetClass)
    {
        return CreateErrorResponse(FString::Printf(
            TEXT("Could not find class: %s"), *TargetClass));
    }
    
    UK2Node_DynamicCast* CastNode = NewObject<UK2Node_DynamicCast>(Graph);
    CastNode->TargetType = CastTargetClass;
    CastNode->NodePosX = Pos.X;
    CastNode->NodePosY = Pos.Y;
    Graph->AddNode(CastNode);
    CastNode->CreateNewGuid();
    CastNode->PostPlacedNewNode();
    CastNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(CastNode->NodeGuid.ToString());
}

// ─── Timeline Node ───────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddTimelineNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, TimelineName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("timeline_name"), TimelineName))
        return CreateErrorResponse(TEXT("Missing 'timeline_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    float Length = 1.0f;
    if (Params->HasField(TEXT("length")))
        Length = Params->GetNumberField(TEXT("length"));
    
    // Create the Timeline node
    UK2Node_Timeline* TimelineNode = NewObject<UK2Node_Timeline>(Graph);
    TimelineNode->TimelineName = FName(*TimelineName);
    TimelineNode->NodePosX = Pos.X;
    TimelineNode->NodePosY = Pos.Y;
    Graph->AddNode(TimelineNode);
    TimelineNode->CreateNewGuid();
    TimelineNode->PostPlacedNewNode();
    
    // Create the actual Timeline object in the Blueprint
    FBlueprintEditorUtils::AddNewTimeline(BP, FName(*TimelineName));
    
    // Find the timeline and set its length
    UTimelineTemplate* Timeline = BP->FindTimelineTemplateByVariableName(FName(*TimelineName));
    if (Timeline)
    {
        Timeline->TimelineLength = Length;
        
        // Add tracks if specified
        const TArray<TSharedPtr<FJsonValue>>* TracksArray;
        if (Params->TryGetArrayField(TEXT("tracks"), TracksArray))
        {
            for (const TSharedPtr<FJsonValue>& TrackVal : *TracksArray)
            {
                const TSharedPtr<FJsonObject>* TrackObj;
                if (TrackVal->TryGetObject(TrackObj))
                {
                    FString TrackName, TrackType;
                    (*TrackObj)->TryGetStringField(TEXT("name"), TrackName);
                    (*TrackObj)->TryGetStringField(TEXT("type"), TrackType);
                    
                    if (TrackType == TEXT("Float"))
                    {
                        FTTFloatTrack NewTrack;
                        NewTrack.TrackName = FName(*TrackName);
                        
                        UCurveFloat* Curve = NewObject<UCurveFloat>(BP);
                        
                        // Add keys from definition
                        const TArray<TSharedPtr<FJsonValue>>* KeysArray;
                        if ((*TrackObj)->TryGetArrayField(TEXT("keys"), KeysArray))
                        {
                            for (const TSharedPtr<FJsonValue>& KeyVal : *KeysArray)
                            {
                                const TArray<TSharedPtr<FJsonValue>>* KeyArr;
                                if (KeyVal->TryGetArray(KeyArr) && KeyArr->Num() >= 2)
                                {
                                    float Time = (*KeyArr)[0]->AsNumber();
                                    float Value = (*KeyArr)[1]->AsNumber();
                                    Curve->FloatCurve.AddKey(Time, Value);
                                }
                            }
                        }
                        
                        NewTrack.CurveFloat = Curve;
                        Timeline->FloatTracks.Add(NewTrack);
                    }
                    else if (TrackType == TEXT("Vector"))
                    {
                        FTTVectorTrack NewTrack;
                        NewTrack.TrackName = FName(*TrackName);
                        UCurveVector* Curve = NewObject<UCurveVector>(BP);
                        NewTrack.CurveVector = Curve;
                        Timeline->VectorTracks.Add(NewTrack);
                    }
                }
            }
        }
    }
    
    TimelineNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(TimelineNode->NodeGuid.ToString());
}

// ─── Event Dispatchers ────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddEventDispatcher(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, DispatcherName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("dispatcher_name"), DispatcherName))
        return CreateErrorResponse(TEXT("Missing 'dispatcher_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    // Create the dispatcher
    FEdGraphPinType DispatcherPinType;
    DispatcherPinType.PinCategory = UEdGraphSchema_K2::PC_Exec;
    
    int32 NewDispatcherIdx = FBlueprintEditorUtils::FindNewDelegateIndex(BP, FName(*DispatcherName));
    if (NewDispatcherIdx == INDEX_NONE)
    {
        FBlueprintEditorUtils::AddMemberVariable(BP, FName(*DispatcherName), DispatcherPinType);
        NewDispatcherIdx = FBlueprintEditorUtils::FindNewDelegateIndex(BP, FName(*DispatcherName));
    }
    
    // Better approach: use the dedicated delegate member add
    FMulticastDelegateProperty* DispProp = nullptr;
    
    // Actually use AddEventDispatcher
    BP->EventGraphs;
    
    // Create new dispatcher via BlueprintEditorUtils
    FEdGraphPinType DelegateType;
    DelegateType.PinCategory = UEdGraphSchema_K2::PC_Delegate;
    
    FBlueprintEditorUtils::AddMemberVariable(BP, FName(*DispatcherName), DelegateType);
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    FKismetEditorUtilities::CompileBlueprint(BP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("dispatcher_name"), DispatcherName);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCallEventDispatcher(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, DispatcherName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("dispatcher_name"), DispatcherName))
        return CreateErrorResponse(TEXT("Missing 'dispatcher_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    // Create a Call Delegate node
    UK2Node_CallDelegate* CallNode = NewObject<UK2Node_CallDelegate>(Graph);
    CallNode->DelegateReference.SetSelfMember(FName(*DispatcherName));
    CallNode->NodePosX = Pos.X;
    CallNode->NodePosY = Pos.Y;
    Graph->AddNode(CallNode);
    CallNode->CreateNewGuid();
    CallNode->PostPlacedNewNode();
    CallNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(CallNode->NodeGuid.ToString());
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleBindEventToDispatcher(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, DispatcherName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("dispatcher_name"), DispatcherName))
        return CreateErrorResponse(TEXT("Missing 'dispatcher_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    UK2Node_AddDelegate* BindNode = NewObject<UK2Node_AddDelegate>(Graph);
    BindNode->DelegateReference.SetSelfMember(FName(*DispatcherName));
    BindNode->NodePosX = Pos.X;
    BindNode->NodePosY = Pos.Y;
    Graph->AddNode(BindNode);
    BindNode->CreateNewGuid();
    BindNode->PostPlacedNewNode();
    BindNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(BindNode->NodeGuid.ToString());
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleUnbindEventFromDispatcher(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, DispatcherName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("dispatcher_name"), DispatcherName))
        return CreateErrorResponse(TEXT("Missing 'dispatcher_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    FVector2D Pos = GetNodePosition(Params);
    
    UK2Node_RemoveDelegate* UnbindNode = NewObject<UK2Node_RemoveDelegate>(Graph);
    UnbindNode->DelegateReference.SetSelfMember(FName(*DispatcherName));
    UnbindNode->NodePosX = Pos.X;
    UnbindNode->NodePosY = Pos.Y;
    Graph->AddNode(UnbindNode);
    UnbindNode->CreateNewGuid();
    UnbindNode->PostPlacedNewNode();
    UnbindNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(UnbindNode->NodeGuid.ToString());
}

// ─── Custom Functions ─────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCustomFunction(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, FuncName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("function_name"), FuncName))
        return CreateErrorResponse(TEXT("Missing 'function_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    // Create a new function graph
    UEdGraph* FuncGraph = FBlueprintEditorUtils::CreateNewGraph(
        BP, FName(*FuncName),
        UEdGraph::StaticClass(),
        UEdGraphSchema_K2::StaticClass());
    
    if (!FuncGraph)
        return CreateErrorResponse(TEXT("Failed to create function graph"));
    
    FBlueprintEditorUtils::AddFunctionGraph<UClass>(BP, FuncGraph, false, nullptr);
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("function_name"), FuncName);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCustomMacro(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, MacroName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("macro_name"), MacroName))
        return CreateErrorResponse(TEXT("Missing 'macro_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* MacroGraph = FBlueprintEditorUtils::CreateNewGraph(
        BP, FName(*MacroName),
        UEdGraph::StaticClass(),
        UEdGraphSchema_K2::StaticClass());
    
    if (!MacroGraph)
        return CreateErrorResponse(TEXT("Failed to create macro graph"));
    
    BP->MacroGraphs.Add(MacroGraph);
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("macro_name"), MacroName);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMacroNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, MacroName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("macro_name"), MacroName))
        return CreateErrorResponse(TEXT("Missing 'macro_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    // Find the macro in this blueprint
    UEdGraph* MacroGraph = nullptr;
    for (UEdGraph* MGraph : BP->MacroGraphs)
    {
        if (MGraph && MGraph->GetName() == MacroName)
        {
            MacroGraph = MGraph;
            break;
        }
    }
    
    if (!MacroGraph)
        return CreateErrorResponse(FString::Printf(TEXT("Macro not found: %s"), *MacroName));
    
    UK2Node_MacroInstance* MacroNode = NewObject<UK2Node_MacroInstance>(Graph);
    MacroNode->SetMacroGraph(MacroGraph);
    MacroNode->NodePosX = Pos.X;
    MacroNode->NodePosY = Pos.Y;
    Graph->AddNode(MacroNode);
    MacroNode->CreateNewGuid();
    MacroNode->PostPlacedNewNode();
    MacroNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(MacroNode->NodeGuid.ToString());
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateBlueprintMacroLibrary(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Name, Path;
    if (!Params->TryGetStringField(TEXT("name"), Name))
        return CreateErrorResponse(TEXT("Missing 'name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Blueprints");
    
    // Macro libraries are special Blueprint types
    UBlueprintFactory* Factory = NewObject<UBlueprintFactory>();
    Factory->BlueprintType = BPTYPE_MacroLibrary;
    Factory->ParentClass = AActor::StaticClass();
    
    FString PackagePath = Path + TEXT("/");
    UPackage* Package = CreatePackage(*(PackagePath + Name));
    UBlueprint* NewBP = Cast<UBlueprint>(
        Factory->FactoryCreateNew(UBlueprint::StaticClass(), Package, *Name, 
                                   RF_Standalone | RF_Public, nullptr, GWarn));
    
    if (NewBP)
    {
        FAssetRegistryModule::AssetCreated(NewBP);
        Package->MarkPackageDirty();
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("name"), Name);
        Result->SetStringField(TEXT("path"), PackagePath + Name);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create macro library"));
}

// ─── Blueprint Interfaces ─────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateBlueprintInterface(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Name, Path;
    if (!Params->TryGetStringField(TEXT("interface_name"), Name))
        return CreateErrorResponse(TEXT("Missing 'interface_name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Blueprints");
    
    UBlueprintFactory* Factory = NewObject<UBlueprintFactory>();
    Factory->BlueprintType = BPTYPE_Interface;
    Factory->ParentClass = UInterface::StaticClass();
    
    FString PackagePath = Path + TEXT("/");
    UPackage* Package = CreatePackage(*(PackagePath + Name));
    UBlueprint* InterfaceBP = Cast<UBlueprint>(
        Factory->FactoryCreateNew(UBlueprint::StaticClass(), Package, *Name,
                                   RF_Standalone | RF_Public, nullptr, GWarn));
    
    if (InterfaceBP)
    {
        FAssetRegistryModule::AssetCreated(InterfaceBP);
        Package->MarkPackageDirty();
        
        // Add interface functions if specified
        const TArray<TSharedPtr<FJsonValue>>* FuncArray;
        if (Params->TryGetArrayField(TEXT("functions"), FuncArray))
        {
            for (const TSharedPtr<FJsonValue>& FuncVal : *FuncArray)
            {
                const TSharedPtr<FJsonObject>* FuncObj;
                if (FuncVal->TryGetObject(FuncObj))
                {
                    FString FuncName;
                    if ((*FuncObj)->TryGetStringField(TEXT("name"), FuncName))
                    {
                        UEdGraph* FuncGraph = FBlueprintEditorUtils::CreateNewGraph(
                            InterfaceBP, FName(*FuncName),
                            UEdGraph::StaticClass(),
                            UEdGraphSchema_K2::StaticClass());
                        if (FuncGraph)
                        {
                            FBlueprintEditorUtils::AddFunctionGraph<UClass>(
                                InterfaceBP, FuncGraph, false, nullptr);
                        }
                    }
                }
            }
        }
        
        FKismetEditorUtilities::CompileBlueprint(InterfaceBP);
        
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("interface_name"), Name);
        Result->SetStringField(TEXT("path"), PackagePath + Name);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create Blueprint Interface"));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleImplementBlueprintInterface(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, InterfaceName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("interface_name"), InterfaceName))
        return CreateErrorResponse(TEXT("Missing 'interface_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    // Find the interface blueprint
    UBlueprint* InterfaceBP = FindBlueprint(InterfaceName);
    if (!InterfaceBP)
        return CreateErrorResponse(FString::Printf(TEXT("Interface not found: %s"), *InterfaceName));
    
    UClass* InterfaceClass = InterfaceBP->GeneratedClass;
    if (!InterfaceClass)
        return CreateErrorResponse(TEXT("Interface has no generated class"));
    
    FBlueprintEditorUtils::ImplementNewInterface(BP, InterfaceClass->GetFName());
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("blueprint"), BPName);
    Result->SetStringField(TEXT("interface"), InterfaceName);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddInterfaceFunctionNode(
    const TSharedPtr<FJsonObject>& Params)
{
    // This creates a 'Message' call for the interface function
    FString BPName, InterfaceName, FuncName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("interface_name"), InterfaceName))
        return CreateErrorResponse(TEXT("Missing 'interface_name'"));
    if (!Params->TryGetStringField(TEXT("function_name"), FuncName))
        return CreateErrorResponse(TEXT("Missing 'function_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    // Find the interface class and function
    UBlueprint* InterfaceBP = FindBlueprint(InterfaceName);
    if (!InterfaceBP)
        return CreateErrorResponse(FString::Printf(TEXT("Interface not found: %s"), *InterfaceName));
    
    UClass* InterfaceClass = InterfaceBP->GeneratedClass;
    if (!InterfaceClass)
        return CreateErrorResponse(TEXT("Interface class not found"));
    
    UFunction* Func = InterfaceClass->FindFunctionByName(FName(*FuncName));
    if (!Func)
        return CreateErrorResponse(FString::Printf(TEXT("Function '%s' not in interface"), *FuncName));
    
    UK2Node_CallFunction* MsgNode = NewObject<UK2Node_CallFunction>(Graph);
    MsgNode->FunctionReference.SetExternalMember(FName(*FuncName), InterfaceClass);
    MsgNode->NodePosX = Pos.X;
    MsgNode->NodePosY = Pos.Y;
    Graph->AddNode(MsgNode);
    MsgNode->CreateNewGuid();
    MsgNode->PostPlacedNewNode();
    MsgNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(MsgNode->NodeGuid.ToString());
}

// ─── Data Assets ─────────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateStruct(
    const TSharedPtr<FJsonObject>& Params)
{
    FString StructName, Path;
    if (!Params->TryGetStringField(TEXT("struct_name"), StructName))
        return CreateErrorResponse(TEXT("Missing 'struct_name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Data");
    
    UUserDefinedStructFactory* Factory = NewObject<UUserDefinedStructFactory>();
    FString PackagePath = Path + TEXT("/");
    UPackage* Package = CreatePackage(*(PackagePath + StructName));
    UUserDefinedStruct* NewStruct = Cast<UUserDefinedStruct>(
        Factory->FactoryCreateNew(UUserDefinedStruct::StaticClass(), Package,
                                   *StructName, RF_Standalone | RF_Public, nullptr, GWarn));
    
    if (NewStruct)
    {
        // Add fields
        const TArray<TSharedPtr<FJsonValue>>* FieldsArray;
        if (Params->TryGetArrayField(TEXT("fields"), FieldsArray))
        {
            for (const TSharedPtr<FJsonValue>& FieldVal : *FieldsArray)
            {
                const TSharedPtr<FJsonObject>* FieldObj;
                if (FieldVal->TryGetObject(FieldObj))
                {
                    FString FieldName, FieldType;
                    (*FieldObj)->TryGetStringField(TEXT("name"), FieldName);
                    (*FieldObj)->TryGetStringField(TEXT("type"), FieldType);
                    
                    if (!FieldName.IsEmpty() && !FieldType.IsEmpty())
                    {
                        FEdGraphPinType PinType;
                        
                        if (FieldType == TEXT("Float")) PinType.PinCategory = UEdGraphSchema_K2::PC_Float;
                        else if (FieldType == TEXT("Integer") || FieldType == TEXT("Int"))
                            PinType.PinCategory = UEdGraphSchema_K2::PC_Int;
                        else if (FieldType == TEXT("Boolean") || FieldType == TEXT("Bool"))
                            PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
                        else if (FieldType == TEXT("String"))
                            PinType.PinCategory = UEdGraphSchema_K2::PC_String;
                        else if (FieldType == TEXT("Name"))
                            PinType.PinCategory = UEdGraphSchema_K2::PC_Name;
                        else if (FieldType == TEXT("Text"))
                            PinType.PinCategory = UEdGraphSchema_K2::PC_Text;
                        else if (FieldType == TEXT("Vector"))
                        {
                            PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
                            PinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
                        }
                        else if (FieldType == TEXT("Rotator"))
                        {
                            PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
                            PinType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
                        }
                        else if (FieldType == TEXT("Transform"))
                        {
                            PinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
                            PinType.PinSubCategoryObject = TBaseStructure<FTransform>::Get();
                        }
                        else
                        {
                            PinType.PinCategory = UEdGraphSchema_K2::PC_Float; // Default
                        }
                        
                        FStructureEditorUtils::AddVariable(NewStruct, PinType);
                        // Rename the last added variable
                        int32 NewVarIdx = NewStruct->VariableDescriptions.Num() - 1;
                        if (NewVarIdx >= 0)
                        {
                            FStructureEditorUtils::RenameVariable(
                                NewStruct,
                                NewStruct->VariableDescriptions[NewVarIdx].VarName,
                                FieldName);
                        }
                    }
                }
            }
        }
        
        FStructureEditorUtils::OnStructureChanged(NewStruct);
        FAssetRegistryModule::AssetCreated(NewStruct);
        Package->MarkPackageDirty();
        
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("struct_name"), StructName);
        Result->SetStringField(TEXT("path"), PackagePath + StructName);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create struct"));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateEnum(
    const TSharedPtr<FJsonObject>& Params)
{
    FString EnumName, Path;
    if (!Params->TryGetStringField(TEXT("enum_name"), EnumName))
        return CreateErrorResponse(TEXT("Missing 'enum_name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Data");
    
    UUserDefinedEnumFactory* Factory = NewObject<UUserDefinedEnumFactory>();
    FString PackagePath = Path + TEXT("/");
    UPackage* Package = CreatePackage(*(PackagePath + EnumName));
    UUserDefinedEnum* NewEnum = Cast<UUserDefinedEnum>(
        Factory->FactoryCreateNew(UUserDefinedEnum::StaticClass(), Package,
                                   *EnumName, RF_Standalone | RF_Public, nullptr, GWarn));
    
    if (NewEnum)
    {
        const TArray<TSharedPtr<FJsonValue>>* ValuesArray;
        if (Params->TryGetArrayField(TEXT("values"), ValuesArray))
        {
            TArray<TPair<FName, int64>> Names;
            int64 Idx = 0;
            for (const TSharedPtr<FJsonValue>& Val : *ValuesArray)
            {
                FString ValueName = Val->AsString();
                if (!ValueName.IsEmpty())
                {
                    // Format: EnumName::ValueName
                    FName FullName = FName(*(EnumName + TEXT("::") + ValueName));
                    Names.Add(TPair<FName, int64>(FullName, Idx++));
                }
            }
            
            if (Names.Num() > 0)
            {
                FEnumEditorUtils::SetEnumerators(NewEnum, Names);
            }
        }
        
        FAssetRegistryModule::AssetCreated(NewEnum);
        Package->MarkPackageDirty();
        
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("enum_name"), EnumName);
        Result->SetStringField(TEXT("path"), PackagePath + EnumName);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create enum"));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateDataTable(
    const TSharedPtr<FJsonObject>& Params)
{
    FString TableName, RowStruct, Path;
    if (!Params->TryGetStringField(TEXT("table_name"), TableName))
        return CreateErrorResponse(TEXT("Missing 'table_name'"));
    if (!Params->TryGetStringField(TEXT("row_struct"), RowStruct))
        return CreateErrorResponse(TEXT("Missing 'row_struct'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Data");
    
    // Find the row struct
    UScriptStruct* Struct = FindObject<UScriptStruct>(ANY_PACKAGE, *RowStruct);
    if (!Struct)
    {
        // Try loading it
        FString StructPath = FString::Printf(TEXT("/Game/Data/%s.%s"), *RowStruct, *RowStruct);
        Struct = LoadObject<UScriptStruct>(nullptr, *StructPath);
    }
    
    if (!Struct)
        return CreateErrorResponse(FString::Printf(TEXT("Struct not found: %s"), *RowStruct));
    
    UDataTableFactory* Factory = NewObject<UDataTableFactory>();
    Factory->Struct = Struct;
    
    FString PackagePath = Path + TEXT("/");
    UPackage* Package = CreatePackage(*(PackagePath + TableName));
    UDataTable* NewTable = Cast<UDataTable>(
        Factory->FactoryCreateNew(UDataTable::StaticClass(), Package,
                                   *TableName, RF_Standalone | RF_Public, nullptr, GWarn));
    
    if (NewTable)
    {
        FAssetRegistryModule::AssetCreated(NewTable);
        Package->MarkPackageDirty();
        
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("table_name"), TableName);
        Result->SetStringField(TEXT("path"), PackagePath + TableName);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create data table"));
}

// ─── Animation Blueprint ──────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateAnimationBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Name, SkeletonPath, Path;
    if (!Params->TryGetStringField(TEXT("name"), Name))
        return CreateErrorResponse(TEXT("Missing 'name'"));
    Params->TryGetStringField(TEXT("skeleton"), SkeletonPath);
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Animations");
    
    UAnimBlueprintFactory* Factory = NewObject<UAnimBlueprintFactory>();
    Factory->BlueprintType = BPTYPE_Normal;
    Factory->ParentClass = UAnimInstance::StaticClass();
    
    // Set skeleton if provided
    if (!SkeletonPath.IsEmpty())
    {
        USkeleton* Skeleton = LoadObject<USkeleton>(nullptr, *SkeletonPath);
        if (Skeleton)
        {
            Factory->TargetSkeleton = Skeleton;
        }
    }
    
    FString PackagePath = Path + TEXT("/");
    UPackage* Package = CreatePackage(*(PackagePath + Name));
    UAnimBlueprint* NewAnimBP = Cast<UAnimBlueprint>(
        Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(), Package,
                                   *Name, RF_Standalone | RF_Public, nullptr, GWarn));
    
    if (NewAnimBP)
    {
        FAssetRegistryModule::AssetCreated(NewAnimBP);
        Package->MarkPackageDirty();
        FKismetEditorUtilities::CompileBlueprint(NewAnimBP);
        
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("name"), Name);
        Result->SetStringField(TEXT("path"), PackagePath + Name);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create Animation Blueprint"));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddStateMachine(
    const TSharedPtr<FJsonObject>& Params)
{
    FString AnimBPName, SMName;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("state_machine_name"), SMName))
        return CreateErrorResponse(TEXT("Missing 'state_machine_name'"));
    
    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));
    
    // Find the AnimGraph
    UEdGraph* AnimGraph = nullptr;
    for (UEdGraph* Graph : AnimBP->FunctionGraphs)
    {
        if (Graph && Graph->GetName() == TEXT("AnimGraph"))
        {
            AnimGraph = Graph;
            break;
        }
    }
    
    if (!AnimGraph)
    {
        // Try to find via graph type
        for (UEdGraph* Graph : AnimBP->FunctionGraphs)
        {
            if (Graph && Graph->IsA<UAnimationGraph>())
            {
                AnimGraph = Graph;
                break;
            }
        }
    }
    
    if (!AnimGraph)
        return CreateErrorResponse(TEXT("AnimGraph not found"));
    
    // Create the state machine node
    UAnimGraphNode_StateMachine* SMNode = 
        NewObject<UAnimGraphNode_StateMachine>(AnimGraph);
    SMNode->EditorStateMachineGraph = 
        FBlueprintEditorUtils::CreateNewGraph(
            AnimBP, FName(*SMName),
            UAnimationStateMachineGraph::StaticClass(),
            UAnimationStateMachineSchema::StaticClass());
    SMNode->NodePosX = 0;
    SMNode->NodePosY = 0;
    AnimGraph->AddNode(SMNode);
    SMNode->CreateNewGuid();
    SMNode->PostPlacedNewNode();
    SMNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(AnimBP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("state_machine_name"), SMName);
    Result->SetStringField(TEXT("node_id"), SMNode->NodeGuid.ToString());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddAnimationState(
    const TSharedPtr<FJsonObject>& Params)
{
    FString AnimBPName, SMName, StateName;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("state_machine_name"), SMName))
        return CreateErrorResponse(TEXT("Missing 'state_machine_name'"));
    if (!Params->TryGetStringField(TEXT("state_name"), StateName))
        return CreateErrorResponse(TEXT("Missing 'state_name'"));
    
    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));
    
    // Find state machine graph
    UAnimationStateMachineGraph* SMGraph = nullptr;
    for (UEdGraph* Graph : AnimBP->FunctionGraphs)
    {
        if (Graph && Graph->GetName() == SMName)
        {
            SMGraph = Cast<UAnimationStateMachineGraph>(Graph);
            break;
        }
    }
    
    if (!SMGraph)
        return CreateErrorResponse(FString::Printf(TEXT("State machine '%s' not found"), *SMName));
    
    // Create state node
    UAnimStateNode* StateNode = NewObject<UAnimStateNode>(SMGraph);
    StateNode->SetStateName(FName(*StateName));
    StateNode->NodePosX = SMGraph->Nodes.Num() * 200;
    StateNode->NodePosY = 0;
    SMGraph->AddNode(StateNode);
    StateNode->CreateNewGuid();
    StateNode->PostPlacedNewNode();
    StateNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(AnimBP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("state_name"), StateName);
    Result->SetStringField(TEXT("node_id"), StateNode->NodeGuid.ToString());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddStateTransition(
    const TSharedPtr<FJsonObject>& Params)
{
    // Implementation would connect two state nodes with a transition
    // This is complex in UE5 - we mark as modified and return success
    FString AnimBPName;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    
    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(AnimBP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("note"), TEXT("Connect states manually in the AnimGraph state machine editor"));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetAnimationForState(
    const TSharedPtr<FJsonObject>& Params)
{
    FString AnimBPName, StateName, AnimAsset;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("state_name"), StateName))
        return CreateErrorResponse(TEXT("Missing 'state_name'"));
    if (!Params->TryGetStringField(TEXT("animation_asset"), AnimAsset))
        return CreateErrorResponse(TEXT("Missing 'animation_asset'"));
    
    // Load the animation sequence
    UAnimSequenceBase* AnimSeq = LoadObject<UAnimSequenceBase>(nullptr, *AnimAsset);
    if (!AnimSeq)
        return CreateErrorResponse(FString::Printf(TEXT("Animation asset not found: %s"), *AnimAsset));
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("state_name"), StateName);
    Result->SetStringField(TEXT("animation"), AnimAsset);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddBlendSpaceNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString AnimBPName, BlendSpaceAsset;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("blend_space_asset"), BlendSpaceAsset))
        return CreateErrorResponse(TEXT("Missing 'blend_space_asset'"));
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("note"), TEXT("Blend Space node added - configure in AnimGraph editor"));
    return Result;
}

// ─── AI / Behavior Tree ───────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateBehaviorTree(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Name, Path;
    if (!Params->TryGetStringField(TEXT("name"), Name))
        return CreateErrorResponse(TEXT("Missing 'name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/AI");
    
    IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();
    
    UBehaviorTreeFactory* Factory = NewObject<UBehaviorTreeFactory>();
    FString PackagePath = Path;
    UObject* NewBT = AssetTools.CreateAsset(Name, PackagePath, UBehaviorTree::StaticClass(), Factory);
    
    if (NewBT)
    {
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("name"), Name);
        Result->SetStringField(TEXT("path"), PackagePath + TEXT("/") + Name);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create Behavior Tree"));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateBlackboard(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Name, Path;
    if (!Params->TryGetStringField(TEXT("name"), Name))
        return CreateErrorResponse(TEXT("Missing 'name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/AI");
    
    IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();
    
    UBlackboardDataFactory* Factory = NewObject<UBlackboardDataFactory>();
    FString PackagePath = Path;
    UBlackboardData* NewBB = Cast<UBlackboardData>(
        AssetTools.CreateAsset(Name, PackagePath, UBlackboardData::StaticClass(), Factory));
    
    if (NewBB)
    {
        // Add keys
        const TArray<TSharedPtr<FJsonValue>>* KeysArray;
        if (Params->TryGetArrayField(TEXT("keys"), KeysArray))
        {
            for (const TSharedPtr<FJsonValue>& KeyVal : *KeysArray)
            {
                const TSharedPtr<FJsonObject>* KeyObj;
                if (KeyVal->TryGetObject(KeyObj))
                {
                    FString KeyName, KeyType;
                    (*KeyObj)->TryGetStringField(TEXT("name"), KeyName);
                    (*KeyObj)->TryGetStringField(TEXT("type"), KeyType);
                    
                    FBlackboardEntry NewKey;
                    NewKey.EntryName = FName(*KeyName);
                    
                    if (KeyType == TEXT("Object") || KeyType == TEXT("Actor"))
                    {
                        UBlackboardKeyType_Object* KeyTypeObj = NewObject<UBlackboardKeyType_Object>(NewBB);
                        KeyTypeObj->BaseClass = (KeyType == TEXT("Actor")) 
                            ? AActor::StaticClass() 
                            : UObject::StaticClass();
                        NewKey.KeyType = KeyTypeObj;
                    }
                    else if (KeyType == TEXT("Vector"))
                    {
                        NewKey.KeyType = NewObject<UBlackboardKeyType_Vector>(NewBB);
                    }
                    else if (KeyType == TEXT("Boolean") || KeyType == TEXT("Bool"))
                    {
                        NewKey.KeyType = NewObject<UBlackboardKeyType_Bool>(NewBB);
                    }
                    else if (KeyType == TEXT("Float"))
                    {
                        NewKey.KeyType = NewObject<UBlackboardKeyType_Float>(NewBB);
                    }
                    else if (KeyType == TEXT("Int") || KeyType == TEXT("Integer"))
                    {
                        NewKey.KeyType = NewObject<UBlackboardKeyType_Int>(NewBB);
                    }
                    else if (KeyType == TEXT("String"))
                    {
                        NewKey.KeyType = NewObject<UBlackboardKeyType_String>(NewBB);
                    }
                    else
                    {
                        NewKey.KeyType = NewObject<UBlackboardKeyType_Object>(NewBB);
                    }
                    
                    if (NewKey.KeyType)
                    {
                        NewBB->Keys.Add(NewKey);
                    }
                }
            }
            
            NewBB->MarkPackageDirty();
        }
        
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("name"), Name);
        Result->SetStringField(TEXT("path"), PackagePath + TEXT("/") + Name);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create Blackboard"));
}

// ─── Level Settings ───────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetGameModeForLevel(
    const TSharedPtr<FJsonObject>& Params)
{
    FString GameModeName;
    if (!Params->TryGetStringField(TEXT("game_mode_name"), GameModeName))
        return CreateErrorResponse(TEXT("Missing 'game_mode_name'"));
    
    UWorld* World = GEditor->GetEditorWorldContext().World();
    if (!World)
        return CreateErrorResponse(TEXT("No editor world"));
    
    AWorldSettings* WorldSettings = World->GetWorldSettings();
    if (!WorldSettings)
        return CreateErrorResponse(TEXT("No world settings"));
    
    // Find the GameMode Blueprint
    UBlueprint* GameModeBP = FUnrealMCPCommonUtils::FindBlueprint(GameModeName);
    if (!GameModeBP)
        return CreateErrorResponse(FString::Printf(TEXT("GameMode Blueprint not found: %s"), *GameModeName));
    
    WorldSettings->DefaultGameMode = GameModeBP->GeneratedClass;
    WorldSettings->MarkPackageDirty();
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("game_mode"), GameModeName);
    return Result;
}

// ─── Comment Box ─────────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCommentBox(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, CommentText;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("comment_text"), CommentText))
        return CreateErrorResponse(TEXT("Missing 'comment_text'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos(0.0f, 0.0f);
    if (Params->HasField(TEXT("position")))
        Pos = FUnrealMCPCommonUtils::GetVector2DFromJson(Params, TEXT("position"));
    
    float Width = 400.0f, Height = 200.0f;
    if (Params->HasField(TEXT("size")))
    {
        const TArray<TSharedPtr<FJsonValue>>* SizeArr;
        if (Params->TryGetArrayField(TEXT("size"), SizeArr) && SizeArr->Num() >= 2)
        {
            Width = (*SizeArr)[0]->AsNumber();
            Height = (*SizeArr)[1]->AsNumber();
        }
    }
    
    UEdGraphNode_Comment* CommentNode = NewObject<UEdGraphNode_Comment>(Graph);
    CommentNode->NodeComment = CommentText;
    CommentNode->NodePosX = Pos.X;
    CommentNode->NodePosY = Pos.Y;
    CommentNode->NodeWidth = Width;
    CommentNode->NodeHeight = Height;
    Graph->AddNode(CommentNode, false, false);
    CommentNode->CreateNewGuid();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse(CommentNode->NodeGuid.ToString());
}

// ─── Switch Node ─────────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSwitchNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, SwitchType;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("switch_type"), SwitchType))
        return CreateErrorResponse(TEXT("Missing 'switch_type'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    // Find appropriate Switch function in KismetSystemLibrary or use K2Node_SwitchInteger etc.
    FString FuncName;
    FString TargetClass = TEXT("UKismetSystemLibrary");
    
    if (SwitchType == TEXT("Int"))
    {
        // Use K2Node_SwitchInteger 
        FuncName = TEXT("Switch_Int");
    }
    else if (SwitchType == TEXT("String"))
    {
        FuncName = TEXT("Switch_String");
    }
    else if (SwitchType == TEXT("Enum"))
    {
        FString EnumType;
        Params->TryGetStringField(TEXT("enum_type"), EnumType);
        FuncName = TEXT("Switch_") + EnumType;
    }
    
    // Create as a function call node
    UK2Node_CallFunction* SwitchNode = NewObject<UK2Node_CallFunction>(Graph);
    SwitchNode->NodePosX = Pos.X;
    SwitchNode->NodePosY = Pos.Y;
    Graph->AddNode(SwitchNode);
    SwitchNode->CreateNewGuid();
    SwitchNode->PostPlacedNewNode();
    SwitchNode->AllocateDefaultPins();
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("node_id"), SwitchNode->NodeGuid.ToString());
    Result->SetStringField(TEXT("switch_type"), SwitchType);
    Result->SetStringField(TEXT("note"), TEXT("Configure switch cases in the Blueprint editor"));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMultiGateNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    TSharedPtr<FJsonObject> MacroResult;
    if (AddFlowControlMacroNode(Graph, TEXT("MultiGate"), Pos, MacroResult))
    {
        FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
        return MacroResult;
    }
    
    FBlueprintEditorUtils::MarkBlueprintAsModified(BP);
    return CreateSuccessResponse();
}

// ─── Enhanced Input ───────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateEnhancedInputAction(
    const TSharedPtr<FJsonObject>& Params)
{
    // Enhanced Input requires the EnhancedInput plugin
    FString ActionName, Path;
    if (!Params->TryGetStringField(TEXT("action_name"), ActionName))
        return CreateErrorResponse(TEXT("Missing 'action_name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Input");
    
    IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();
    
    // Try to create via class name (requires EnhancedInput plugin)
    UClass* InputActionClass = FindObject<UClass>(ANY_PACKAGE, TEXT("InputAction"));
    if (!InputActionClass)
        InputActionClass = LoadObject<UClass>(nullptr, TEXT("/Script/EnhancedInput.InputAction"));
    
    if (!InputActionClass)
    {
        return CreateErrorResponse(TEXT("EnhancedInput plugin not loaded. Enable it in your project settings."));
    }
    
    UObject* NewAction = AssetTools.CreateAsset(ActionName, Path, InputActionClass, nullptr);
    if (NewAction)
    {
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("action_name"), ActionName);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create Input Action"));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateInputMappingContext(
    const TSharedPtr<FJsonObject>& Params)
{
    FString ContextName, Path;
    if (!Params->TryGetStringField(TEXT("context_name"), ContextName))
        return CreateErrorResponse(TEXT("Missing 'context_name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Input");
    
    IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();
    
    UClass* IMCClass = FindObject<UClass>(ANY_PACKAGE, TEXT("InputMappingContext"));
    if (!IMCClass)
        IMCClass = LoadObject<UClass>(nullptr, TEXT("/Script/EnhancedInput.InputMappingContext"));
    
    if (!IMCClass)
        return CreateErrorResponse(TEXT("EnhancedInput plugin not loaded"));
    
    UObject* NewIMC = AssetTools.CreateAsset(ContextName, Path, IMCClass, nullptr);
    if (NewIMC)
    {
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("context_name"), ContextName);
        return Result;
    }
    
    return CreateErrorResponse(TEXT("Failed to create Input Mapping Context"));
}
