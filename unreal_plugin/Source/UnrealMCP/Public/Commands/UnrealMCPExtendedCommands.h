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

    // ── Material Commands (Ch. 5, 6, 9) ──────────────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateMaterial(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetMaterialOnActor(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSetMaterialNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateDynamicMaterialInstance(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSetVectorParameterValueNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSetScalarParameterValueNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetupHitMaterialSwap(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSpawnEmitterAtLocationNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddPlaySoundAtLocationNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetCollisionSettings(const TSharedPtr<FJsonObject>& Params);

    // ── SaveGame / Game State Commands (Ch. 11) ───────────────────────────────
    TSharedPtr<FJsonObject> HandleAddSaveGameToSlotNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddLoadGameFromSlotNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddDoesSaveGameExistNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddCreateSaveGameObjectNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddDeleteSaveGameInSlotNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetupFullSaveLoadSystem(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSetGamePausedNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddOpenLevelNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddQuitGameNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateRoundBasedGameSystem(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateLoseScreenWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreatePauseMenuWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddPlayerDeathEvent(const TSharedPtr<FJsonObject>& Params);

    // ── Library / Component Commands (Ch. 18) ────────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateBlueprintFunctionLibrary(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddFunctionToLibrary(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateExperienceLevelComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateCircularMovementComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddCustomComponentToBlueprint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSetTimerByEventNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSetTimerByFunctionNameNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddClearTimerNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddGetOwnerNode(const TSharedPtr<FJsonObject>& Params);

    // ── Procedural Generation Commands (Ch. 19) ───────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateProceduralMeshBlueprint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateSplinePlacementBlueprint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateEditorUtilityBlueprint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateAlignActorsUtility(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateRandomSpawnerBlueprint(const TSharedPtr<FJsonObject>& Params);

    // ── VR Commands (Ch. 16) ──────────────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateVRPawnBlueprint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateGrabComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleMakeActorVRGrabbable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddTeleportSystemToPawn(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddCallInterfaceFunctionNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddValidatedGetNode(const TSharedPtr<FJsonObject>& Params);

    // ── Variant Manager Commands (Ch. 20) ─────────────────────────────────────
    TSharedPtr<FJsonObject> HandleCreateLevelVariantSets(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddVariantToLevelVariantSets(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateProductConfiguratorBlueprint(const TSharedPtr<FJsonObject>& Params);

    // ── Advanced Node Commands (Ch. 15) ───────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddSelectNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddFormatTextNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMathExpressionNode(const TSharedPtr<FJsonObject>& Params);

    // ── UMG Extended Commands (Ch. 7, 8, 11) ─────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddHorizontalBoxToWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddVerticalBoxToWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddCanvasPanelToWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSliderToWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddCheckboxToWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddNamedSlotToWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateHUDWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateWinMenuWidget(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddWidgetAnimation(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddCreateWidgetNode(const TSharedPtr<FJsonObject>& Params);

    // ── Data Container Extended Commands (Ch. 13) ─────────────────────────────
    TSharedPtr<FJsonObject> HandleAddSetContainsNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSetOperationNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddSetToArrayNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMakeSetNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMapFindNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMapContainsNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMapKeysNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMapValuesNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMakeMapNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMakeArrayNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddRandomArrayItemNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddGetDataTableRowNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBreakStructNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMakeStructNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMapVariable(const TSharedPtr<FJsonObject>& Params);

    // ── Physics / Math / Trace Commands (Ch. 14) ─────────────────────────────
    TSharedPtr<FJsonObject> HandleAddLineTraceByChannelNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMultiLineTraceByChannelNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddLineTraceForObjectsNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMultiLineTraceForObjectsNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddShapeTraceNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBreakHitResultNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddDrawDebugLineNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddDrawDebugSphereNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddDrawDebugPointNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddComponentFunctionNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleBuildTraceInteractionBlueprint(const TSharedPtr<FJsonObject>& Params);

    // ── Advanced AI Commands (Ch. 10) ─────────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddPawnSensingComponent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddComponentEventNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddFinishExecuteNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddGetRandomReachablePointNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddClearBlackboardValueNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBTBlackboardDecorator(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateBTAttackTask(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateBTWanderTask(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateEnemySpawnerBlueprint(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleCreateFullUpgradedEnemyAI(const TSharedPtr<FJsonObject>& Params);

    // ── Operator / Math Node Commands (Ch. 2, 5, 6, 8) ────────────────────────
    TSharedPtr<FJsonObject> HandleAddArithmeticOperatorNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddRelationalOperatorNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddLogicalOperatorNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddClampNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddLerpNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddAbsNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddMinMaxNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddRandomFloatInRangeNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddRandomIntegerInRangeNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddGetDeltaSecondsNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddRerouteNode(const TSharedPtr<FJsonObject>& Params);

    // ── Actor Query Commands (Ch. 3, 4) ───────────────────────────────────────
    TSharedPtr<FJsonObject> HandleAddGetAllActorsOfClassNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddGetActorOfClassNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddGetGameModeNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddGetGameInstanceNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddConstructionScriptNode(const TSharedPtr<FJsonObject>& Params);

    // ── Helpers ───────────────────────────────────────────────────────────────
    UBlueprint* FindBlueprint(const FString& BlueprintName);
    UEdGraph* FindOrCreateEventGraph(UBlueprint* Blueprint);
    TSharedPtr<FJsonObject> CreateErrorResponse(const FString& Message);
    TSharedPtr<FJsonObject> CreateSuccessResponse(const FString& NodeId = "");
    FVector2D GetNodePosition(const TSharedPtr<FJsonObject>& Params);
    bool AddFlowControlMacroNode(UEdGraph* Graph, const FString& MacroName,
                                  const FVector2D& Position, TSharedPtr<FJsonObject>& OutResult);
};
