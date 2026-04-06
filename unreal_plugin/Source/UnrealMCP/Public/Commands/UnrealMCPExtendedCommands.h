#pragma once

#include "CoreMinimal.h"
#include "Dom/JsonObject.h"

/**
 * Extended MCP Commands
 * Handles all new Blueprint Visual Scripting commands beyond the base unreal-mcp.
 * 
 * NEW COMMAND CATEGORIES:
 * - Flow Control Nodes (Branch, Sequence, FlipFlop, DoOnce, DoN, Gate, WhileLoop)
 * - Variable Get/Set Nodes
 * - Cast Nodes
 * - Timeline Nodes
 * - Switch Nodes (Int, String, Enum)
 * - MultiGate Node
 * - ForEach Loop Node
 * - Event Dispatchers
 * - Blueprint Interfaces
 * - Custom Functions & Macros
 * - Animation Blueprint Commands
 * - AI / Behavior Tree Commands
 * - Data Assets (Struct, Enum, DataTable)
 * - Comment Boxes
 * - Gameplay Framework Helpers
 */
class UNREALMCP_API FUnrealMCPExtendedCommands
{
public:
    FUnrealMCPExtendedCommands();

    /** Dispatch a command by type. Returns nullptr if command not recognized. */
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    // ── Flow Control Nodes ───────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddBranchNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSequenceNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddFlipFlopNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddDoOnceNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddDoNNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddGateNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddWhileLoopNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddForEachLoopNode(const TSharedPtr<FJsonObject>& Params);

    // ── Switch Nodes ─────────────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddSwitchNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMultiGateNode(const TSharedPtr<FJsonObject>& Params);

    // ── Variable Nodes ───────────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddVariableGetNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddVariableSetNode(const TSharedPtr<FJsonObject>& Params);

    // ── Cast Node ────────────────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddCastNode(const TSharedPtr<FJsonObject>& Params);

    // ── Timeline ─────────────────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddTimelineNode(const TSharedPtr<FJsonObject>& Params);

    // ── Event Dispatchers ────────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddEventDispatcher(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCallEventDispatcher(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBindEventToDispatcher(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleUnbindEventFromDispatcher(const TSharedPtr<FJsonObject>& Params);

    // ── Custom Functions / Macros ─────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddCustomFunction(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddCustomMacro(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMacroNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateBlueprintMacroLibrary(const TSharedPtr<FJsonObject>& Params);

    // ── Blueprint Interfaces ──────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateBlueprintInterface(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleImplementBlueprintInterface(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddInterfaceFunctionNode(const TSharedPtr<FJsonObject>& Params);

    // ── Data Assets ───────────────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateStruct(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateEnum(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateDataTable(const TSharedPtr<FJsonObject>& Params);

    // ── Animation Blueprint ───────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateAnimationBlueprint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddStateMachine(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddAnimationState(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddStateTransition(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetAnimationForState(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlendSpaceNode(const TSharedPtr<FJsonObject>& Params);

    // ── AI / Behavior Tree ────────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateBehaviorTree(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateBlackboard(const TSharedPtr<FJsonObject>& Params);

    // ── Level / World ─────────────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleSetGameModeForLevel(const TSharedPtr<FJsonObject>& Params);

    // ── Comment & Decoration ──────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddCommentBox(const TSharedPtr<FJsonObject>& Params);

    // ── Enhanced Input ────────────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateEnhancedInputAction(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateInputMappingContext(const TSharedPtr<FJsonObject>& Params);

    // ── Helpers ───────────────────────────────────────────────────────────────
    UBlueprint* FindBlueprint(const FString& BlueprintName);
    UEdGraph* FindOrCreateEventGraph(UBlueprint* Blueprint);
    TSharedPtr<FJsonObject> CreateErrorResponse(const FString& Message);
    TSharedPtr<FJsonObject> CreateSuccessResponse(const FString& NodeId = "");
    FVector2D GetNodePosition(const TSharedPtr<FJsonObject>& Params);
    bool AddFlowControlMacroNode(UEdGraph* Graph, const FString& MacroName,
                                  const FVector2D& Position, TSharedPtr<FJsonObject>& OutResult);
};
