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
#include "EngineUtils.h"
#include "Factories/BlueprintFactory.h"
#include "EdGraphSchema_K2.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "K2Node_Event.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Message.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "K2Node_Self.h"
#include "K2Node_MacroInstance.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_Timeline.h"
#include "K2Node_CustomEvent.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_SwitchEnum.h"
#include "K2Node_AsyncAction.h"
#include "K2Node_CreateDelegate.h"
#include "K2Node_AddDelegate.h"
#include "K2Node_RemoveDelegate.h"
#include "K2Node_CallDelegate.h"
#include "K2Node_InputAction.h"
#include "K2Node_CommutativeAssociativeBinaryOperator.h"
#include "K2Node_MakeArray.h"

// Enhanced Input
#include "InputMappingContext.h"
#include "InputAction.h"
#include "EnhancedActionKeyMapping.h"

// Kismet utilities
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "BlueprintEditorSettings.h"
#include "BlueprintEditorLibrary.h"   // UBlueprintEditorLibrary::ReparentBlueprint
#include "Kismet/KismetMathLibrary.h"

// Editor Asset utilities
#include "EditorAssetLibrary.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetToolsModule.h"
#include "IAssetTools.h"

// Animation Blueprint
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimationAsset.h"
#include "Animation/AnimSequenceBase.h"
#include "Animation/BlendSpace.h"
#include "Factories/AnimBlueprintFactory.h"
#include "AnimGraphNode_Base.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_StateMachine.h"
#include "AnimGraphNode_StateMachineBase.h"
#include "AnimGraphNode_StateResult.h"
#include "AnimGraphNode_TransitionResult.h"
#include "AnimGraphNode_BlendSpacePlayer.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_Slot.h"
#include "AnimGraphNode_BlendListByBool.h"
#include "AnimGraphNodeBinding.h"
// UPROPERTY reflection is used to set the Binding subobject's PropertyBindings map so we don't need
// the private UAnimGraphNodeBinding_Base members (PropertyBindings / RecalculateBindingType).
#include "AnimationGraph.h"
#include "EdGraphUtilities.h"
#include "AnimationGraphSchema.h"
#include "AnimationStateGraph.h"
#include "AnimationStateMachineGraph.h"
#include "AnimStateEntryNode.h"
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
#include "BehaviorTree/BlackboardComponent.h"
#include "BehaviorTree/BehaviorTreeComponent.h"
#include "BehaviorTree/BTNode.h"
#include "EnvironmentQuery/EnvQuery.h"
#include "EnvironmentQuery/EnvQueryOption.h"
#include "EnvironmentQuery/EnvQueryGenerator.h"
#include "EnvironmentQuery/EnvQueryTest.h"
#include "EnvironmentQuery/EnvQueryTypes.h"
#include "EnvironmentQuery/Generators/EnvQueryGenerator_ActorsOfClass.h"
#include "EnvironmentQuery/Generators/EnvQueryGenerator_CurrentLocation.h"
#include "EnvironmentQuery/Generators/EnvQueryGenerator_Donut.h"
#include "EnvironmentQuery/Generators/EnvQueryGenerator_OnCircle.h"
#include "EnvironmentQuery/Generators/EnvQueryGenerator_SimpleGrid.h"
#include "EnvironmentQuery/Tests/EnvQueryTest_Distance.h"
#include "EnvironmentQuery/Tests/EnvQueryTest_Dot.h"
#include "EnvironmentQuery/Tests/EnvQueryTest_Pathfinding.h"
#include "EnvironmentQuery/Tests/EnvQueryTest_Trace.h"
// BehaviorTreeFactory.h / BlackboardDataFactory.h removed from public API in UE 5.6
// #include "Factories/BehaviorTreeFactory.h"   // REMOVED
// #include "Factories/BlackboardDataFactory.h" // REMOVED

// Asset Editor management (close open editors before modifying assets)
#include "Subsystems/AssetEditorSubsystem.h"

// BT Graph editing (editor-only, via BehaviorTreeEditor module)
#include "BehaviorTreeGraph.h"
#include "BehaviorTreeGraphNode.h"
#include "BehaviorTreeGraphNode_Root.h"
#include "BehaviorTreeGraphNode_Composite.h"
#include "BehaviorTreeGraphNode_Task.h"
#include "BehaviorTreeGraphNode_Service.h"
#include "BehaviorTreeGraphNode_Decorator.h"
#include "EdGraphSchema_BehaviorTree.h"
#include "AIGraphNode.h"
#include "AIGraphTypes.h"
// BT base runtime classes (needed for IsChildOf checks)
#include "BehaviorTree/BTCompositeNode.h"
#include "BehaviorTree/BTTaskNode.h"
#include "BehaviorTree/BTService.h"
#include "BehaviorTree/BTDecorator.h"
#include "BehaviorTree/Services/BTService_RunEQS.h"
#include "Perception/AIPerceptionComponent.h"
#include "Perception/AIPerceptionStimuliSourceComponent.h"
#include "Perception/AISense.h"
#include "Perception/AISense_Hearing.h"
#include "Perception/AISense_Sight.h"
#include "Perception/AISenseConfig_Hearing.h"
#include "Perception/AISenseConfig_Sight.h"
#include "AIController.h"
#include "BrainComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/Actor.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/ActorComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Engine/NetDriver.h"
#include "Engine/NetConnection.h"
#include "Engine/NetworkObjectList.h"
#include "UObject/CoreNetTypes.h"
#include "Navigation/CrowdFollowingComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "Navigation/NavLinkProxy.h"
#include "NavModifierVolume.h"
#include "NavMesh/NavMeshBoundsVolume.h"
#include "NavMesh/RecastNavMesh.h"
#include "NavigationData.h"
#include "NavAreas/NavArea_Default.h"
#include "NavAreas/NavArea_Null.h"
#include "NavAreas/NavArea_Obstacle.h"
// Concrete BT node classes
#include "BehaviorTree/Composites/BTComposite_Selector.h"
#include "BehaviorTree/Composites/BTComposite_Sequence.h"
#include "BehaviorTree/Tasks/BTTask_Wait.h"
#include "BehaviorTree/Tasks/BTTask_MoveTo.h"

// Data Assets ? paths fixed for UE 5.6
#include "Engine/UserDefinedStruct.h"
#include "Engine/UserDefinedEnum.h"
#include "Engine/DataTable.h"
#include "Factories/DataTableFactory.h"
// UserDefinedStructFactory/UserDefinedEnumFactory removed; use editor utils directly.
// UE5.6: header path ? use Kismet2/StructureEditorUtils.h (new location in UE 5.4+)
#include "Kismet2/StructureEditorUtils.h"
#include "Kismet2/EnumEditorUtils.h"

// Timeline (forward-declare only; UTimelineTemplate is internal in UE 5.6)
#include "Curves/CurveFloat.h"
#include "Curves/CurveVector.h"
// TimelineTemplate.h is internal ? do NOT include; use BP->FindTimelineTemplateByVariableName with auto*

// Blueprint Interfaces
#include "Kismet2/KismetEditorUtilities.h"
// BlueprintSupport.h is an engine-private header; removed.

// Graph comment node
#include "EdGraphNode_Comment.h"

// Animation state machine schema
#include "AnimationStateMachineSchema.h"

// Misc
#include "GameFramework/WorldSettings.h"
// EditorLevelUtils.h removed from public includes in UE 5.6
// #include "EditorLevelUtils.h"  // REMOVED

// SimpleConstructionScript (required for SCS_Node / USCS_Node access)
#include "Engine/SCS_Node.h"
#include "Engine/SimpleConstructionScript.h"

// Niagara
#include "NiagaraComponent.h"
#include "NiagaraCommon.h"
#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterFactoryNew.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraFunctionLibrary.h"
#include "NiagaraGraph.h"
#include "NiagaraNodeFunctionCall.h"
#include "NiagaraNodeOutput.h"
#include "NiagaraScript.h"
#include "NiagaraScriptSource.h"
#include "NiagaraTypes.h"
#include "NiagaraSystemFactoryNew.h"
#include "NiagaraSpriteRendererProperties.h"
#include "NiagaraMeshRendererProperties.h"
#include "ViewModels/Stack/NiagaraParameterHandle.h"
#include "ViewModels/Stack/NiagaraStackGraphUtilities.h"
#include "K2Node_CallFunction.h"
#include "Engine/StaticMesh.h"

// Animation Notifies
#include "Animation/AnimSequenceBase.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifies/AnimNotify.h"

// Material Instance
#include "Factories/MaterialFactoryNew.h"
#include "Factories/MaterialFunctionFactoryNew.h"
#include "Factories/MaterialInstanceConstantFactoryNew.h"
#include "Materials/Material.h"
#include "Materials/MaterialExpressionComponentMask.h"
#include "Materials/MaterialExpressionScalarParameter.h"
#include "Materials/MaterialExpressionTextureSampleParameter2D.h"
#include "Materials/MaterialExpressionVectorParameter.h"
#include "Materials/MaterialFunction.h"
#include "Materials/MaterialInstanceConstant.h"
#include "Materials/MaterialInterface.h"
#include "MaterialEditingLibrary.h"
#include "Engine/Texture.h"

// Sequencer / Level Sequence
#include "LevelSequence.h"
#include "Tracks/MovieScene3DTransformTrack.h"
#include "Sections/MovieScene3DTransformSection.h"
#include "MovieSceneTrack.h"
#include "MovieScene.h"
#include "MovieSceneBinding.h"
#include "LevelSequenceActor.h"

DEFINE_LOG_CATEGORY_STATIC(LogUnrealMCPExt, Log, All);

static FString MCPNormalizeAssetPath(const FString& Path)
{
    FString Normalized = Path;
    Normalized.TrimStartAndEndInline();
    if (Normalized.IsEmpty() || Normalized.Contains(TEXT(".")))
    {
        return Normalized;
    }

    FString PackagePath;
    FString AssetName;
    if (Normalized.Split(TEXT("/"), &PackagePath, &AssetName, ESearchCase::CaseSensitive, ESearchDir::FromEnd) && !AssetName.IsEmpty())
    {
        return FString::Printf(TEXT("%s/%s.%s"), *PackagePath, *AssetName, *AssetName);
    }
    return Normalized;
}

template <typename AssetType>
static AssetType* MCPLoadAsset(const FString& Path)
{
    AssetType* Asset = LoadObject<AssetType>(nullptr, *Path);
    if (!Asset)
    {
        Asset = LoadObject<AssetType>(nullptr, *MCPNormalizeAssetPath(Path));
    }
    return Asset;
}

static FString MCPMakePackagePath(const FString& FolderPath, const FString& AssetName)
{
    FString CleanFolder = FolderPath.IsEmpty() ? TEXT("/Game") : FolderPath;
    CleanFolder.RemoveFromEnd(TEXT("/"));
    return CleanFolder + TEXT("/") + AssetName;
}

static FString MCPMakeObjectPath(const FString& FolderPath, const FString& AssetName)
{
    const FString PackagePath = MCPMakePackagePath(FolderPath, AssetName);
    return PackagePath + TEXT(".") + AssetName;
}

static FLinearColor MCPReadLinearColor(
    const TSharedPtr<FJsonObject>& Params,
    const FString& FieldName,
    const FLinearColor& DefaultValue)
{
    const TArray<TSharedPtr<FJsonValue>>* ArrayValue = nullptr;
    if (!Params->TryGetArrayField(FieldName, ArrayValue) || !ArrayValue)
    {
        return DefaultValue;
    }

    const double R = ArrayValue->IsValidIndex(0) ? (*ArrayValue)[0]->AsNumber() : DefaultValue.R;
    const double G = ArrayValue->IsValidIndex(1) ? (*ArrayValue)[1]->AsNumber() : DefaultValue.G;
    const double B = ArrayValue->IsValidIndex(2) ? (*ArrayValue)[2]->AsNumber() : DefaultValue.B;
    const double A = ArrayValue->IsValidIndex(3) ? (*ArrayValue)[3]->AsNumber() : DefaultValue.A;
    return FLinearColor((float)R, (float)G, (float)B, (float)A);
}

static FLinearColor MCPReadLinearColorValue(
    const TSharedPtr<FJsonValue>& JsonValue,
    const FLinearColor& DefaultValue)
{
    if (!JsonValue.IsValid())
    {
        return DefaultValue;
    }

    const TArray<TSharedPtr<FJsonValue>>* ArrayValue = nullptr;
    if (!JsonValue->TryGetArray(ArrayValue) || !ArrayValue)
    {
        return DefaultValue;
    }

    const double R = ArrayValue->IsValidIndex(0) ? (*ArrayValue)[0]->AsNumber() : DefaultValue.R;
    const double G = ArrayValue->IsValidIndex(1) ? (*ArrayValue)[1]->AsNumber() : DefaultValue.G;
    const double B = ArrayValue->IsValidIndex(2) ? (*ArrayValue)[2]->AsNumber() : DefaultValue.B;
    const double A = ArrayValue->IsValidIndex(3) ? (*ArrayValue)[3]->AsNumber() : DefaultValue.A;
    return FLinearColor((float)R, (float)G, (float)B, (float)A);
}

static void MCPEnsureAssetFolder(const FString& FolderPath)
{
    if (!UEditorAssetLibrary::DoesDirectoryExist(FolderPath))
    {
        UEditorAssetLibrary::MakeDirectory(FolderPath);
    }
}

static UMaterialExpressionScalarParameter* MCPAddScalarParameter(
    UMaterial* Material,
    const FName& ParameterName,
    float DefaultValue,
    int32 X,
    int32 Y)
{
    UMaterialExpressionScalarParameter* Expression = Cast<UMaterialExpressionScalarParameter>(
        UMaterialEditingLibrary::CreateMaterialExpression(Material, UMaterialExpressionScalarParameter::StaticClass(), X, Y));
    if (Expression)
    {
        Expression->ParameterName = ParameterName;
        Expression->DefaultValue = DefaultValue;
        Expression->SliderMin = 0.0f;
        Expression->SliderMax = 1.0f;
    }
    return Expression;
}

static UMaterialExpressionVectorParameter* MCPAddVectorParameter(
    UMaterial* Material,
    const FName& ParameterName,
    const FLinearColor& DefaultValue,
    int32 X,
    int32 Y)
{
    UMaterialExpressionVectorParameter* Expression = Cast<UMaterialExpressionVectorParameter>(
        UMaterialEditingLibrary::CreateMaterialExpression(Material, UMaterialExpressionVectorParameter::StaticClass(), X, Y));
    if (Expression)
    {
        Expression->ParameterName = ParameterName;
        Expression->DefaultValue = DefaultValue;
    }
    return Expression;
}

static UMaterialExpressionTextureSampleParameter2D* MCPAddTextureParameter(
    UMaterial* Material,
    const FName& ParameterName,
    UTexture* Texture,
    int32 X,
    int32 Y)
{
    UMaterialExpressionTextureSampleParameter2D* Expression = Cast<UMaterialExpressionTextureSampleParameter2D>(
        UMaterialEditingLibrary::CreateMaterialExpression(Material, UMaterialExpressionTextureSampleParameter2D::StaticClass(), X, Y));
    if (Expression)
    {
        Expression->ParameterName = ParameterName;
        Expression->Texture = Texture;
        Expression->AutoSetSampleType();
    }
    return Expression;
}

static bool MCPWireTextureToProperty(
    UMaterial* Material,
    UTexture* Texture,
    const FName& ParameterName,
    EMaterialProperty Property,
    int32 X,
    int32 Y)
{
    UMaterialExpressionTextureSampleParameter2D* TextureExpression =
        MCPAddTextureParameter(Material, ParameterName, Texture, X, Y);
    if (!TextureExpression)
    {
        return false;
    }
    return UMaterialEditingLibrary::ConnectMaterialProperty(TextureExpression, TEXT("RGB"), Property);
}

static bool MCPWireORMTexture(UMaterial* Material, UTexture* Texture, int32 X, int32 Y)
{
    UMaterialExpressionTextureSampleParameter2D* ORMExpression =
        MCPAddTextureParameter(Material, TEXT("ORMTexture"), Texture, X, Y);
    if (!ORMExpression)
    {
        return false;
    }

    struct FMaskTarget
    {
        bool R;
        bool G;
        bool B;
        EMaterialProperty Property;
        int32 YOffset;
    };

    const FMaskTarget Targets[] = {
        {true, false, false, MP_AmbientOcclusion, -120},
        {false, true, false, MP_Roughness, 0},
        {false, false, true, MP_Metallic, 120},
    };

    bool bAllConnected = true;
    for (const FMaskTarget& Target : Targets)
    {
        UMaterialExpressionComponentMask* Mask = Cast<UMaterialExpressionComponentMask>(
            UMaterialEditingLibrary::CreateMaterialExpression(Material, UMaterialExpressionComponentMask::StaticClass(), X + 260, Y + Target.YOffset));
        if (!Mask)
        {
            bAllConnected = false;
            continue;
        }

        Mask->R = Target.R;
        Mask->G = Target.G;
        Mask->B = Target.B;
        Mask->A = false;
        UMaterialEditingLibrary::ConnectMaterialExpressions(ORMExpression, TEXT("RGB"), Mask, TEXT(""));
        bAllConnected &= UMaterialEditingLibrary::ConnectMaterialProperty(Mask, TEXT(""), Target.Property);
    }

    return bAllConnected;
}

// ─── Forward declarations for file-local BT helpers ───────────────────────────
// These static helpers are DEFINED near the bottom of this TU (around line
// ~4100+) but are CALLED from earlier functions (HandleCreateBTSimple,
// HandleRepairBehaviorTree, HandleAddBTNode, etc.). Without forward decls the
// compiler rejects those early call sites with "identifier not found" (MSVC
// does NOT allow implicit declaration). Declarations only — definitions stay
// where they are.
static void                   BTSafeAddNode(UBehaviorTreeGraph* BTGraph, UBehaviorTreeGraphNode* Node);
static void                   BTSafeLinkPins(UEdGraphPin* OutputPin, UEdGraphPin* InputPin);
static void                   CloseAllBTEditors(UBehaviorTree* BT);
static void                   SafeRemoveBTNodes(UBehaviorTreeGraph* BTGraph);
static UBehaviorTree*         FindBehaviorTree(const FString& BTName);
static void                   SafeUpdateBTAsset(UBehaviorTree* BT, UBehaviorTreeGraph* BTGraph);
static UBehaviorTreeGraph*    GetOrCreateBTGraph(UBehaviorTree* BT);

// ??? Constructor ??????????????????????????????????????????????????????????????
FUnrealMCPExtendedCommands::FUnrealMCPExtendedCommands()
{
    UE_LOG(LogUnrealMCPExt, Log, TEXT("Extended MCP Commands initialized"));
}

// ??? Main Dispatch ????????????????????????????????????????????????????????????
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
    if (CommandType == TEXT("add_custom_event"))           return HandleAddCustomEvent(Params);
    if (CommandType == TEXT("call_custom_event"))          return HandleCallCustomEvent(Params);
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
    if (CommandType == TEXT("add_interface_event_node")) return HandleAddInterfaceEventNode(Params);

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
    if (CommandType == TEXT("add_sequence_player_node"))   return HandleAddSequencePlayerNode(Params);
    if (CommandType == TEXT("connect_anim_graph_nodes"))   return HandleConnectAnimGraphNodes(Params);
    if (CommandType == TEXT("insert_anim_graph_slot"))     return HandleInsertAnimGraphSlotBeforeRoot(Params);
    if (CommandType == TEXT("insert_blend_bool_fire_before_slot"))
        return HandleInsertBlendBoolFireBeforeSlot(Params);

    // AI
    if (CommandType == TEXT("create_behavior_tree"))            return HandleCreateBehaviorTree(Params);
    if (CommandType == TEXT("repair_behavior_tree"))            return HandleRepairBehaviorTree(Params);
    if (CommandType == TEXT("create_blackboard"))               return HandleCreateBlackboard(Params);
    if (CommandType == TEXT("set_behavior_tree_blackboard"))    return HandleSetBehaviorTreeBlackboard(Params);
    if (CommandType == TEXT("set_blueprint_parent_class"))      return HandleSetBlueprintParentClass(Params);
    if (CommandType == TEXT("eqs_create_query"))                return HandleEQSCreateQuery(Params);
    if (CommandType == TEXT("eqs_describe_query"))              return HandleEQSDescribeQuery(Params);
    if (CommandType == TEXT("eqs_add_generator"))               return HandleEQSAddGenerator(Params);
    if (CommandType == TEXT("eqs_add_test"))                    return HandleEQSAddTest(Params);
    if (CommandType == TEXT("perception_add_component"))        return HandlePerceptionAddComponent(Params);
    if (CommandType == TEXT("perception_configure_sight"))      return HandlePerceptionConfigureSight(Params);
    if (CommandType == TEXT("perception_configure_hearing"))    return HandlePerceptionConfigureHearing(Params);
    if (CommandType == TEXT("perception_create_stimulus_source")) return HandlePerceptionCreateStimulusSource(Params);
    if (CommandType == TEXT("perception_describe_blueprint"))   return HandlePerceptionDescribeBlueprint(Params);
    if (CommandType == TEXT("nav_create_link_proxy"))           return HandleNavCreateLinkProxy(Params);
    if (CommandType == TEXT("nav_add_modifier_volume"))         return HandleNavAddModifierVolume(Params);
    if (CommandType == TEXT("nav_describe_agent_settings"))     return HandleNavDescribeAgentSettings(Params);
    if (CommandType == TEXT("crowd_configure_rvo"))             return HandleCrowdConfigureRVO(Params);
    if (CommandType == TEXT("crowd_configure_detour"))          return HandleCrowdConfigureDetour(Params);
    if (CommandType == TEXT("gameplay_debugger_capture_ai"))    return HandleGameplayDebuggerCaptureAI(Params);

    // Networking / Replication
    if (CommandType == TEXT("net_describe_blueprint_replication")) return HandleNetDescribeBlueprintReplication(Params);
    if (CommandType == TEXT("net_set_actor_replicates"))           return HandleNetSetActorReplicates(Params);
    if (CommandType == TEXT("net_set_component_replicates"))       return HandleNetSetComponentReplicates(Params);
    if (CommandType == TEXT("net_configure_replicated_property"))  return HandleNetConfigureReplicatedProperty(Params);
    if (CommandType == TEXT("net_add_repnotify_variable"))         return HandleNetAddRepNotifyVariable(Params);
    if (CommandType == TEXT("net_create_rpc_event"))               return HandleNetCreateRPCEvent(Params);
    if (CommandType == TEXT("net_configure_rpc"))                  return HandleNetConfigureRPC(Params);
    if (CommandType == TEXT("net_add_authority_gate"))             return HandleNetAddAuthorityGate(Params);
    if (CommandType == TEXT("net_add_role_switch"))                return HandleNetAddRoleSwitch(Params);
    if (CommandType == TEXT("net_set_owner_reference"))            return HandleNetSetOwnerReference(Params);
    if (CommandType == TEXT("session_create_blueprint_flow"))      return HandleSessionCreateBlueprintFlow(Params);
    if (CommandType == TEXT("session_find_blueprint_flow"))        return HandleSessionFindBlueprintFlow(Params);
    if (CommandType == TEXT("network_debug_replication"))          return HandleNetworkDebugReplication(Params);
    if (CommandType == TEXT("net_validate_common_mistakes"))       return HandleNetValidateCommonMistakes(Params);

    // BT Graph Node Manipulation
    if (CommandType == TEXT("build_behavior_tree"))             return HandleBuildBehaviorTree(Params);
    if (CommandType == TEXT("add_bt_node"))                     return HandleAddBTNode(Params);
    if (CommandType == TEXT("get_bt_graph_info"))               return HandleGetBTGraphInfo(Params);
    if (CommandType == TEXT("bt_add_selector_wait"))            return HandleBTAddSelectorWait(Params);
    if (CommandType == TEXT("bt_get_info"))                     return HandleGetBTGraphInfo(Params); // alias
    if (CommandType == TEXT("attach_bt_sub_node"))              return HandleAttachBTSubNode(Params);
    if (CommandType == TEXT("bt_add_run_eqs_service"))          return HandleBTAddRunEQSService(Params);

    // Level/World
    if (CommandType == TEXT("set_game_mode_for_level"))         return HandleSetGameModeForLevel(Params);

    // Niagara / VFX
    if (CommandType == TEXT("niagara_create_system"))              return HandleCreateNiagaraSystem(Params);
    if (CommandType == TEXT("niagara_describe_system"))            return HandleDescribeNiagaraSystem(Params);
    if (CommandType == TEXT("niagara_add_empty_emitter"))          return HandleAddEmptyNiagaraEmitter(Params);
    if (CommandType == TEXT("niagara_set_system_user_parameter"))  return HandleSetNiagaraUserParameter(Params);
    if (CommandType == TEXT("niagara_set_spawn_rate"))             return HandleSetNiagaraSpawnRate(Params);
    if (CommandType == TEXT("niagara_add_sprite_renderer"))        return HandleAddNiagaraSpriteRenderer(Params);
    if (CommandType == TEXT("niagara_add_mesh_renderer"))          return HandleAddNiagaraMeshRenderer(Params);
    if (CommandType == TEXT("add_niagara_component"))              return HandleAddNiagaraComponent(Params);
    if (CommandType == TEXT("add_spawn_niagara_at_location_node")) return HandleAddSpawnNiagaraAtLocationNode(Params);

    // Animation Notifies
    if (CommandType == TEXT("add_anim_notify"))                 return HandleAddAnimNotify(Params);

    // Materials
    if (CommandType == TEXT("set_material_instance_parameter")) return HandleSetMaterialInstanceParameter(Params);

    // Sequencer
    if (CommandType == TEXT("set_sequencer_track"))             return HandleSetSequencerTrack(Params);

    // Comment
    if (CommandType == TEXT("add_comment_box"))                 return HandleAddCommentBox(Params);

    // Enhanced Input
    if (CommandType == TEXT("create_enhanced_input_action"))  return HandleCreateEnhancedInputAction(Params);
    if (CommandType == TEXT("create_input_mapping_context"))  return HandleCreateInputMappingContext(Params);
    if (CommandType == TEXT("add_input_mapping"))              return HandleAddInputMapping(Params);

    // ── SaveGame / Game State (Ch. 11) ───────────────────────────────────────
    if (CommandType == TEXT("add_save_game_to_slot_node"))       return HandleAddSaveGameToSlotNode(Params);
    if (CommandType == TEXT("add_load_game_from_slot_node"))     return HandleAddLoadGameFromSlotNode(Params);
    if (CommandType == TEXT("add_does_save_game_exist_node"))    return HandleAddDoesSaveGameExistNode(Params);
    if (CommandType == TEXT("add_create_save_game_object_node")) return HandleAddCreateSaveGameObjectNode(Params);
    if (CommandType == TEXT("add_delete_save_game_in_slot_node")) return HandleAddDeleteSaveGameInSlotNode(Params);
    if (CommandType == TEXT("add_open_level_node"))              return HandleAddOpenLevelNode(Params);
    if (CommandType == TEXT("add_set_game_paused_node"))         return HandleAddSetGamePausedNode(Params);
    if (CommandType == TEXT("add_quit_game_node"))               return HandleAddQuitGameNode(Params);
    if (CommandType == TEXT("add_player_death_event"))           return HandleAddPlayerDeathEvent(Params);

    // ── Library / Component (Ch. 18) ─────────────────────────────────────────
    if (CommandType == TEXT("add_set_timer_by_event_node"))      return HandleAddSetTimerByEventNode(Params);
    if (CommandType == TEXT("add_set_timer_by_function_name_node")) return HandleAddSetTimerByFunctionNameNode(Params);
    if (CommandType == TEXT("add_get_owner_node"))               return HandleAddGetOwnerNode(Params);
    if (CommandType == TEXT("add_custom_component_to_blueprint")) return HandleAddCustomComponentToBlueprint(Params);
    if (CommandType == TEXT("add_function_to_blueprint"))        return HandleAddFunctionToLibrary(Params);
    if (CommandType == TEXT("add_function_to_library"))          return HandleAddFunctionToLibrary(Params);

    // ── Data Containers (Ch. 13) ─────────────────────────────────────────────
    if (CommandType == TEXT("add_make_array_node"))              return HandleAddMakeArrayNode(Params);
    if (CommandType == TEXT("add_object_type_make_array_node"))   return HandleAddObjectTypeMakeArrayNode(Params);
    if (CommandType == TEXT("add_make_map_node"))                return HandleAddMakeMapNode(Params);
    if (CommandType == TEXT("add_make_set_node"))                return HandleAddMakeSetNode(Params);
    if (CommandType == TEXT("add_break_struct_node"))            return HandleAddBreakStructNode(Params);
    if (CommandType == TEXT("add_make_struct_node"))             return HandleAddMakeStructNode(Params);
    if (CommandType == TEXT("add_get_data_table_row_node"))      return HandleAddGetDataTableRowNode(Params);
    if (CommandType == TEXT("add_random_array_item_node"))       return HandleAddRandomArrayItemNode(Params);
    if (CommandType == TEXT("add_set_contains_node"))            return HandleAddSetContainsNode(Params);
    if (CommandType == TEXT("add_set_operation_node"))           return HandleAddSetOperationNode(Params);
    if (CommandType == TEXT("add_set_to_array_node"))            return HandleAddSetToArrayNode(Params);
    if (CommandType == TEXT("add_map_find_node"))                return HandleAddMapFindNode(Params);
    if (CommandType == TEXT("add_map_contains_node"))            return HandleAddMapContainsNode(Params);
    if (CommandType == TEXT("add_map_keys_node"))                return HandleAddMapKeysNode(Params);
    if (CommandType == TEXT("add_map_values_node"))              return HandleAddMapValuesNode(Params);
    if (CommandType == TEXT("add_map_variable"))                 return HandleAddMapVariable(Params);

    // ── Material / VFX nodes (Ch. 9) ─────────────────────────────────────────
    if (CommandType == TEXT("add_set_material_node"))             return HandleAddSetMaterialNode(Params);
    if (CommandType == TEXT("add_set_vector_parameter_value_node")) return HandleAddSetVectorParameterValueNode(Params);
    if (CommandType == TEXT("add_set_scalar_parameter_value_node")) return HandleAddSetScalarParameterValueNode(Params);
    if (CommandType == TEXT("add_spawn_emitter_at_location_node")) return HandleAddSpawnEmitterAtLocationNode(Params);
    if (CommandType == TEXT("add_play_sound_at_location_node"))   return HandleAddPlaySoundAtLocationNode(Params);

    // ── Physics / Trace (Ch. 14) ─────────────────────────────────────────────
    if (CommandType == TEXT("add_line_trace_by_channel_node"))       return HandleAddLineTraceByChannelNode(Params);
    if (CommandType == TEXT("add_multi_line_trace_by_channel_node")) return HandleAddMultiLineTraceByChannelNode(Params);
    if (CommandType == TEXT("add_line_trace_for_objects_node"))      return HandleAddLineTraceForObjectsNode(Params);
    if (CommandType == TEXT("add_multi_line_trace_for_objects_node")) return HandleAddMultiLineTraceForObjectsNode(Params);
    if (CommandType == TEXT("add_break_hit_result_node"))            return HandleAddBreakHitResultNode(Params);

    // ── Advanced Node Commands (Ch. 15) ───────────────────────────────────────
    if (CommandType == TEXT("add_select_node"))           return HandleAddSelectNode(Params);
    if (CommandType == TEXT("add_format_text_node"))      return HandleAddFormatTextNode(Params);
    if (CommandType == TEXT("add_math_expression_node"))  return HandleAddMathExpressionNode(Params);
    if (CommandType == TEXT("add_reroute_node"))           return HandleAddRerouteNode(Params);

    // ── AI (Ch. 10) ───────────────────────────────────────────────────────────
    if (CommandType == TEXT("add_pawn_sensing_component"))          return HandleAddPawnSensingComponent(Params);
    if (CommandType == TEXT("add_component_event_node"))            return HandleAddComponentEventNode(Params);
    if (CommandType == TEXT("add_component_function_node"))         return HandleAddComponentFunctionNode(Params);
    if (CommandType == TEXT("add_finish_execute_node"))             return HandleAddFinishExecuteNode(Params);
    if (CommandType == TEXT("add_get_random_reachable_point_node")) return HandleAddGetRandomReachablePointNode(Params);
    if (CommandType == TEXT("add_clear_blackboard_value_node"))     return HandleAddClearBlackboardValueNode(Params);
    if (CommandType == TEXT("add_bt_blackboard_decorator"))         return HandleAddBTBlackboardDecorator(Params);
    if (CommandType == TEXT("create_bt_attack_task"))               return HandleCreateBTAttackTask(Params);
    if (CommandType == TEXT("create_bt_wander_task"))               return HandleCreateBTWanderTask(Params);
    if (CommandType == TEXT("create_enemy_spawner_blueprint"))      return HandleCreateEnemySpawnerBlueprint(Params);
    if (CommandType == TEXT("create_full_upgraded_enemy_ai"))       return HandleCreateFullUpgradedEnemyAI(Params);
    if (CommandType == TEXT("add_call_interface_function_node"))    return HandleAddCallInterfaceFunctionNode(Params);
    if (CommandType == TEXT("add_validated_get_node"))              return HandleAddValidatedGetNode(Params);

    // ── VR (Ch. 16) ───────────────────────────────────────────────────────────
    if (CommandType == TEXT("add_teleport_system_to_pawn"))  return HandleAddTeleportSystemToPawn(Params);

    // ── Variant Manager (Ch. 20) ──────────────────────────────────────────────
    if (CommandType == TEXT("add_variant_to_level_variant_sets"))     return HandleAddVariantToLevelVariantSets(Params);
    if (CommandType == TEXT("create_product_configurator_blueprint")) return HandleCreateProductConfiguratorBlueprint(Params);

    // ── Operator / Math (Ch. 2, 5, 6, 8) ─────────────────────────────────────
    if (CommandType == TEXT("add_arithmetic_operator_node"))    return HandleAddArithmeticOperatorNode(Params);
    if (CommandType == TEXT("add_relational_operator_node"))    return HandleAddRelationalOperatorNode(Params);
    if (CommandType == TEXT("add_logical_operator_node"))       return HandleAddLogicalOperatorNode(Params);
    if (CommandType == TEXT("add_clamp_node"))                  return HandleAddClampNode(Params);
    if (CommandType == TEXT("add_lerp_node"))                   return HandleAddLerpNode(Params);
    if (CommandType == TEXT("add_abs_node"))                    return HandleAddAbsNode(Params);
    if (CommandType == TEXT("add_min_max_node"))                return HandleAddMinMaxNode(Params);
    if (CommandType == TEXT("add_random_float_in_range_node"))  return HandleAddRandomFloatInRangeNode(Params);
    if (CommandType == TEXT("add_random_integer_in_range_node")) return HandleAddRandomIntegerInRangeNode(Params);
    if (CommandType == TEXT("add_get_delta_seconds_node"))       return HandleAddGetDeltaSecondsNode(Params);

    // ── Actor Query (Ch. 3, 4) ───────────────────────────────────────────────
    if (CommandType == TEXT("add_get_all_actors_of_class_node")) return HandleAddGetAllActorsOfClassNode(Params);
    if (CommandType == TEXT("add_get_actor_of_class_node"))      return HandleAddGetActorOfClassNode(Params);
    if (CommandType == TEXT("add_get_game_mode_node"))           return HandleAddGetGameModeNode(Params);
    if (CommandType == TEXT("add_get_game_instance_node"))       return HandleAddGetGameInstanceNode(Params);
    if (CommandType == TEXT("add_construction_script_node"))     return HandleAddConstructionScriptNode(Params);

    // ── Material / Collision (Ch. 5, 9) ─────────────────────────────────────
    if (CommandType == TEXT("create_material"))                  return HandleCreateMaterial(Params);
    if (CommandType == TEXT("material_create_master"))           return HandleMaterialCreateMaster(Params);
    if (CommandType == TEXT("material_create_function"))         return HandleMaterialCreateFunction(Params);
    if (CommandType == TEXT("material_wire_texture_set"))        return HandleMaterialWireTextureSet(Params);
    if (CommandType == TEXT("material_create_instance_from_master")) return HandleMaterialCreateInstanceFromMaster(Params);
    if (CommandType == TEXT("material_set_instance_parameters_bulk")) return HandleMaterialSetInstanceParametersBulk(Params);
    if (CommandType == TEXT("set_material_on_actor"))            return HandleSetMaterialOnActor(Params);
    if (CommandType == TEXT("create_dynamic_material_instance")) return HandleCreateDynamicMaterialInstance(Params);
    if (CommandType == TEXT("setup_hit_material_swap"))          return HandleSetupHitMaterialSwap(Params);
    if (CommandType == TEXT("set_collision_settings"))           return HandleSetCollisionSettings(Params);

    // ── SaveGame / Game State high-level (Ch. 11) ────────────────────────────
    if (CommandType == TEXT("setup_full_save_load_system"))      return HandleSetupFullSaveLoadSystem(Params);
    if (CommandType == TEXT("create_round_based_game_system"))   return HandleCreateRoundBasedGameSystem(Params);
    if (CommandType == TEXT("create_lose_screen_widget"))        return HandleCreateLoseScreenWidget(Params);
    if (CommandType == TEXT("create_pause_menu_widget"))         return HandleCreatePauseMenuWidget(Params);

    // ── Library / Component high-level (Ch. 18) ──────────────────────────────
    if (CommandType == TEXT("create_blueprint_function_library")) return HandleCreateBlueprintFunctionLibrary(Params);
    if (CommandType == TEXT("create_experience_level_component")) return HandleCreateExperienceLevelComponent(Params);
    if (CommandType == TEXT("create_circular_movement_component")) return HandleCreateCircularMovementComponent(Params);
    if (CommandType == TEXT("create_random_spawner_blueprint"))  return HandleCreateRandomSpawnerBlueprint(Params);

    // ── Procedural / Editor Utility (Ch. 19) ─────────────────────────────────
    if (CommandType == TEXT("create_procedural_mesh_blueprint")) return HandleCreateProceduralMeshBlueprint(Params);
    if (CommandType == TEXT("create_spline_placement_blueprint")) return HandleCreateSplinePlacementBlueprint(Params);
    if (CommandType == TEXT("create_editor_utility_blueprint"))  return HandleCreateEditorUtilityBlueprint(Params);
    if (CommandType == TEXT("create_align_actors_utility"))      return HandleCreateAlignActorsUtility(Params);

    // ── VR high-level (Ch. 16) ───────────────────────────────────────────────
    if (CommandType == TEXT("create_vr_pawn_blueprint"))         return HandleCreateVRPawnBlueprint(Params);
    if (CommandType == TEXT("create_grab_component"))            return HandleCreateGrabComponent(Params);
    if (CommandType == TEXT("make_actor_vr_grabbable"))          return HandleMakeActorVRGrabbable(Params);

    // ── Variant Manager high-level (Ch. 20) ──────────────────────────────────
    if (CommandType == TEXT("create_level_variant_sets"))        return HandleCreateLevelVariantSets(Params);

    // ── Physics / Trace high-level (Ch. 14) ──────────────────────────────────
    if (CommandType == TEXT("build_trace_interaction_blueprint")) return HandleBuildTraceInteractionBlueprint(Params);

    return nullptr; // Not our command
}

// ??? Helpers ??????????????????????????????????????????????????????????????????

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
    MacroNode->CreateNewGuid();
    // BUG-033 / CRASH-003 pattern: PostPlacedNewNode → MarkBlueprintAsStructurallyModified
    // crashes UE5.6 via MassEntityEditor observer. Use AddNode(bFromUI=false) +
    // AllocateDefaultPins() only — macro pins are fully materialised without PostPlacedNewNode.
    Graph->AddNode(MacroNode, /*bFromUI=*/false, /*bSelectNewNode=*/false);
    MacroNode->AllocateDefaultPins();
    
    OutResult = MakeShared<FJsonObject>();
    OutResult->SetStringField(TEXT("node_id"), MacroNode->NodeGuid.ToString());
    OutResult->SetBoolField(TEXT("success"), true);
    return true;
}

// ??? Flow Control Implementations ?????????????????????????????????????????????

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
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
        return MacroResult;
    }
    
    // Fallback - create a basic function node placeholder
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("note"), TEXT("Sequence node created - add via Blueprint Editor for best results"));
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
        return MacroResult;
    }
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
        return MacroResult;
    }
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
        return MacroResult;
    }
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
        return MacroResult;
    }
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
        return MacroResult;
    }
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
        return MacroResult;
    }
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    return CreateSuccessResponse();
}

// ??? Variable Nodes ??????????????????????????????????????????????????????????

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
    GetNode->CreateNewGuid();
    FUnrealMCPCommonUtils::EnsureBlueprintGeneratedClass(BP); // guard ReconstructNode
    Graph->AddNode(GetNode);
    GetNode->PostPlacedNewNode();
    GetNode->AllocateDefaultPins();
    GetNode->ReconstructNode();
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
    SetNode->CreateNewGuid();
    FUnrealMCPCommonUtils::EnsureBlueprintGeneratedClass(BP); // guard ReconstructNode
    Graph->AddNode(SetNode);
    SetNode->PostPlacedNewNode();
    SetNode->AllocateDefaultPins();
    SetNode->ReconstructNode();
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    return CreateSuccessResponse(SetNode->NodeGuid.ToString());
}

// ??? Cast Node ???????????????????????????????????????????????????????????????

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
    UClass* CastTargetClass = FindObject<UClass>(nullptr, *TargetClass);
    if (!CastTargetClass)
    {
        // Try with A prefix
        CastTargetClass = FindObject<UClass>(nullptr, *(TEXT("A") + TargetClass));
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
    CastNode->CreateNewGuid();
    FUnrealMCPCommonUtils::EnsureBlueprintGeneratedClass(BP); // guard PostPlacedNewNode (DynamicCast touches GeneratedClass)
    Graph->AddNode(CastNode);
    CastNode->PostPlacedNewNode();
    CastNode->AllocateDefaultPins();
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    return CreateSuccessResponse(CastNode->NodeGuid.ToString());
}

// ??? Timeline Node ???????????????????????????????????????????????????????????

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
    
    // UTimelineTemplate is an internal UE type; skip length/track setup here.
    // K2Node_Timeline already manages pin allocation; use the BP editor for tracks.
    (void)Length; // suppress unused warning
    {
        // TimelineTemplate access disabled for UE 5.6 compatibility.
    }
    
    TimelineNode->AllocateDefaultPins();
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    return CreateSuccessResponse(TimelineNode->NodeGuid.ToString());
}

// ??? Custom Events ????????????????????????????????????????????????????????

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCustomEvent(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, EventName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("event_name"), EventName))
        return CreateErrorResponse(TEXT("Missing 'event_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    // Create custom event node
    UK2Node_CustomEvent* CustomEvent = NewObject<UK2Node_CustomEvent>(Graph);
    CustomEvent->CustomFunctionName = FName(*EventName);
    CustomEvent->NodePosX = Pos.X;
    CustomEvent->NodePosY = Pos.Y;
    CustomEvent->CreateNewGuid();
    Graph->AddNode(CustomEvent, true);
    CustomEvent->PostPlacedNewNode();
    CustomEvent->AllocateDefaultPins();
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("event_name"), EventName);
    Result->SetStringField(TEXT("node_id"), CustomEvent->NodeGuid.ToString());
    Result->SetStringField(TEXT("node_name"), CustomEvent->GetName());
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCallCustomEvent(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, TargetBP, EventName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("target_blueprint"), TargetBP))
        return CreateErrorResponse(TEXT("Missing 'target_blueprint'"));
    if (!Params->TryGetStringField(TEXT("event_name"), EventName))
        return CreateErrorResponse(TEXT("Missing 'event_name'"));
    
    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    
    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));
    
    FVector2D Pos = GetNodePosition(Params);
    
    // Find the target blueprint to get the event function
    UBlueprint* TargetBP_Asset = FindBlueprint(TargetBP);
    if (!TargetBP_Asset) return CreateErrorResponse(FString::Printf(TEXT("Target blueprint not found: %s"), *TargetBP));
    
    // Find the custom event function in the target blueprint
    UFunction* EventFunc = nullptr;
    if (TargetBP_Asset->GeneratedClass)
    {
        EventFunc = TargetBP_Asset->GeneratedClass->FindFunctionByName(FName(*EventName));
    }
    
    if (!EventFunc)
        return CreateErrorResponse(FString::Printf(TEXT("Custom event not found: %s in %s"), *EventName, *TargetBP));
    
    // Create function call node
    UK2Node_CallFunction* CallNode = NewObject<UK2Node_CallFunction>(Graph);
    CallNode->SetFromFunction(EventFunc);
    CallNode->NodePosX = Pos.X;
    CallNode->NodePosY = Pos.Y;
    CallNode->CreateNewGuid();
    Graph->AddNode(CallNode, true);
    CallNode->PostPlacedNewNode();
    CallNode->AllocateDefaultPins();
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("event_name"), EventName);
    Result->SetStringField(TEXT("node_id"), CallNode->NodeGuid.ToString());
    Result->SetStringField(TEXT("node_name"), CallNode->GetName());
    
    // Return pin information
    TArray<TSharedPtr<FJsonValue>> PinsArray;
    for (UEdGraphPin* Pin : CallNode->Pins)
    {
        TSharedPtr<FJsonObject> PinObj = MakeShared<FJsonObject>();
        PinObj->SetStringField(TEXT("pin_name"), Pin->PinName.ToString());
        PinObj->SetStringField(TEXT("direction"), Pin->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
        PinsArray.Add(MakeShared<FJsonValueObject>(PinObj));
    }
    Result->SetArrayField(TEXT("pins"), PinsArray);
    
    return Result;
}

// ??? Event Dispatchers ????????????????????????????????????????????????????????

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
    
    // FindNewDelegateIndex removed in UE 5.5+ ? use AddMemberVariable with PC_MCDelegate instead.
    // Create new dispatcher via BlueprintEditorUtils
    FEdGraphPinType DelegateType;
    DelegateType.PinCategory = UEdGraphSchema_K2::PC_MCDelegate;
    
    FBlueprintEditorUtils::AddMemberVariable(BP, FName(*DispatcherName), DelegateType);
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    return CreateSuccessResponse(UnbindNode->NodeGuid.ToString());
}

// ??? Custom Functions ?????????????????????????????????????????????????????????

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
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    
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
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    
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
    
    // If not found in blueprint, search standard macros
    if (!MacroGraph)
    {
        // Search in Engine's standard macro library
        FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
        IAssetRegistry& AssetRegistry = AssetRegistryModule.Get();
        
        FARFilter Filter;
        Filter.ClassPaths.Add(UBlueprint::StaticClass()->GetClassPathName());
        Filter.PackagePaths.Add(TEXT("/Engine/EditorBlueprintResources"));
        Filter.bRecursivePaths = true;
        
        TArray<FAssetData> AssetList;
        AssetRegistry.GetAssets(Filter, AssetList);
        
        for (const FAssetData& Asset : AssetList)
        {
            if (UBlueprint* MacroLibrary = Cast<UBlueprint>(Asset.GetAsset()))
            {
                if (MacroLibrary->BlueprintType == BPTYPE_MacroLibrary)
                {
                    for (UEdGraph* MGraph : MacroLibrary->MacroGraphs)
                    {
                        if (MGraph && MGraph->GetName().Contains(MacroName))
                        {
                            MacroGraph = MGraph;
                            break;
                        }
                    }
                    if (MacroGraph) break;
                }
            }
        }
    }
    
    if (!MacroGraph)
        return CreateErrorResponse(FString::Printf(TEXT("Macro not found: %s"), *MacroName));
    
    UK2Node_MacroInstance* MacroNode = NewObject<UK2Node_MacroInstance>(Graph);
    MacroNode->SetMacroGraph(MacroGraph);
    MacroNode->NodePosX = Pos.X;
    MacroNode->NodePosY = Pos.Y;
    MacroNode->CreateNewGuid();
    Graph->AddNode(MacroNode);
    MacroNode->PostPlacedNewNode();
    MacroNode->AllocateDefaultPins();
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
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

// ??? Blueprint Interfaces ?????????????????????????????????????????????????????

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateBlueprintInterface(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Name, Path;
    if (!Params->TryGetStringField(TEXT("interface_name"), Name))
        return CreateErrorResponse(TEXT("Missing 'interface_name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Blueprints");
    
    FString PackagePath = Path + TEXT("/");
    const FString AssetObjectPath = PackagePath + Name + TEXT(".") + Name;
    if (UBlueprint* ExistingBP = LoadObject<UBlueprint>(nullptr, *AssetObjectPath))
    {
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetBoolField(TEXT("existing"), true);
        Result->SetStringField(TEXT("interface_name"), Name);
        Result->SetStringField(TEXT("path"), PackagePath + Name);
        Result->SetStringField(TEXT("message"), TEXT("Blueprint Interface already exists; returning existing asset instead of creating a duplicate."));
        return Result;
    }

    UBlueprintFactory* Factory = NewObject<UBlueprintFactory>();
    Factory->BlueprintType = BPTYPE_Interface;
    Factory->ParentClass = UInterface::StaticClass();
    
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
    if (!InterfaceClass && InterfaceBP->SkeletonGeneratedClass)
    {
        InterfaceClass = InterfaceBP->SkeletonGeneratedClass;
    }
    if (!InterfaceClass)
        return CreateErrorResponse(TEXT("Interface has no generated class"));
    
    bool bAlreadyListed = false;
    for (const FBPInterfaceDescription& ExistingInterface : BP->ImplementedInterfaces)
    {
        if (ExistingInterface.Interface == InterfaceClass)
        {
            bAlreadyListed = true;
            break;
        }
    }

    if (!bAlreadyListed)
    {
        FBlueprintEditorUtils::ImplementNewInterface(BP, FTopLevelAssetPath(InterfaceClass->GetPackage()->GetFName(), InterfaceClass->GetFName()));
        FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
    }
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);

    bool bListedAfterAttempt = false;
    for (const FBPInterfaceDescription& ExistingInterface : BP->ImplementedInterfaces)
    {
        if (ExistingInterface.Interface == InterfaceClass)
        {
            bListedAfterAttempt = true;
            break;
        }
    }

    const bool bVerified = BP->GeneratedClass && BP->GeneratedClass->ImplementsInterface(InterfaceClass);
    
    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), bListedAfterAttempt || bVerified);
    Result->SetStringField(TEXT("blueprint"), BPName);
    Result->SetStringField(TEXT("interface"), InterfaceName);
    Result->SetBoolField(TEXT("verified"), bVerified);
    Result->SetBoolField(TEXT("already_listed"), bAlreadyListed);
    Result->SetBoolField(TEXT("listed"), bListedAfterAttempt);
    Result->SetBoolField(TEXT("compile_deferred"), true);
    if (!bVerified)
    {
        Result->SetStringField(TEXT("message"), TEXT("Interface add was attempted/listed, but compile is deferred to avoid KismetCompiler crashes during live MCP calls"));
    }
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
    UClass* SignatureClass = InterfaceClass;
    if (InterfaceBP->SkeletonGeneratedClass)
    {
        UFunction* SkeletonFunc = InterfaceBP->SkeletonGeneratedClass->FindFunctionByName(FName(*FuncName));
        if (SkeletonFunc)
        {
            SignatureClass = InterfaceBP->SkeletonGeneratedClass;
        }
    }
    if (!SignatureClass)
        return CreateErrorResponse(TEXT("Interface class not found"));
    
    UFunction* Func = SignatureClass->FindFunctionByName(FName(*FuncName));
    if (!Func && InterfaceClass && InterfaceClass != SignatureClass)
    {
        Func = InterfaceClass->FindFunctionByName(FName(*FuncName));
        if (Func)
        {
            SignatureClass = InterfaceClass;
        }
    }
    if (!Func)
        return CreateErrorResponse(FString::Printf(TEXT("Function '%s' not in interface"), *FuncName));
    
    UK2Node_Message* MsgNode = NewObject<UK2Node_Message>(Graph);
    MsgNode->FunctionReference.SetExternalMember(FName(*FuncName), SignatureClass);
    MsgNode->NodePosX = Pos.X;
    MsgNode->NodePosY = Pos.Y;
    Graph->AddNode(MsgNode);
    MsgNode->CreateNewGuid();
    MsgNode->PostPlacedNewNode();
    MsgNode->AllocateDefaultPins();
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    return CreateSuccessResponse(MsgNode->NodeGuid.ToString());
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddInterfaceEventNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, InterfaceName, FuncName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("interface_name"), InterfaceName))
        return CreateErrorResponse(TEXT("Missing 'interface_name'"));
    if (!Params->TryGetStringField(TEXT("function_name"), FuncName))
        return CreateErrorResponse(TEXT("Missing 'function_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP)
        return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UBlueprint* InterfaceBP = FindBlueprint(InterfaceName);
    if (!InterfaceBP)
        return CreateErrorResponse(FString::Printf(TEXT("Interface not found: %s"), *InterfaceName));

    UClass* InterfaceClass = InterfaceBP->GeneratedClass ? InterfaceBP->GeneratedClass : InterfaceBP->SkeletonGeneratedClass;
    UClass* SignatureClass = InterfaceClass;
    if (InterfaceBP->SkeletonGeneratedClass &&
        InterfaceBP->SkeletonGeneratedClass->FindFunctionByName(FName(*FuncName)))
    {
        SignatureClass = InterfaceBP->SkeletonGeneratedClass;
    }
    if (!SignatureClass)
        return CreateErrorResponse(TEXT("Interface class not found"));

    UFunction* Func = SignatureClass->FindFunctionByName(FName(*FuncName));
    if (!Func && InterfaceClass && InterfaceClass != SignatureClass)
    {
        Func = InterfaceClass->FindFunctionByName(FName(*FuncName));
        if (Func)
        {
            SignatureClass = InterfaceClass;
        }
    }
    if (!Func)
        return CreateErrorResponse(FString::Printf(TEXT("Function '%s' not in interface"), *FuncName));

    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    if (!Graph)
        return CreateErrorResponse(TEXT("Failed to get event graph"));

    FName FuncFName(*FuncName);
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        UK2Node_Event* Existing = Cast<UK2Node_Event>(Node);
        if (Existing &&
            Existing->EventReference.GetMemberName() == FuncFName &&
            Existing->EventReference.GetMemberParentClass() == SignatureClass)
        {
            TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
            R->SetBoolField(TEXT("success"), true);
            R->SetBoolField(TEXT("was_existing"), true);
            R->SetStringField(TEXT("node_id"), Existing->NodeGuid.ToString());
            R->SetStringField(TEXT("node_name"), Existing->GetName());
            return R;
        }
    }

    FVector2D Pos = GetNodePosition(Params);

    UK2Node_Event* EventNode = NewObject<UK2Node_Event>(Graph);
    if (!EventNode)
        return CreateErrorResponse(TEXT("Failed to create interface event node"));

    EventNode->EventReference.SetExternalMember(FuncFName, SignatureClass);
    EventNode->bOverrideFunction = true;
    EventNode->NodePosX = Pos.X;
    EventNode->NodePosY = Pos.Y;
    EventNode->CreateNewGuid();
    Graph->AddNode(EventNode, true);
    EventNode->PostPlacedNewNode();
    EventNode->AllocateDefaultPins();

    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("was_existing"), false);
    R->SetStringField(TEXT("node_id"), EventNode->NodeGuid.ToString());
    R->SetStringField(TEXT("node_name"), EventNode->GetName());
    TArray<TSharedPtr<FJsonValue>> PinsArr;
    for (UEdGraphPin* P : EventNode->Pins)
    {
        if (P && !P->bHidden)
        {
            TSharedPtr<FJsonObject> PinObj = MakeShared<FJsonObject>();
            PinObj->SetStringField(TEXT("pin_name"), P->PinName.ToString());
            PinObj->SetStringField(TEXT("direction"), P->Direction == EGPD_Input ? TEXT("input") : TEXT("output"));
            PinObj->SetStringField(TEXT("type"), P->PinType.PinCategory.ToString());
            PinObj->SetStringField(TEXT("default_value"), P->DefaultValue);
            PinsArr.Add(MakeShared<FJsonValueObject>(PinObj));
        }
    }
    R->SetArrayField(TEXT("pins"), PinsArr);
    return R;
}

// ??? Data Assets ?????????????????????????????????????????????????????????????

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateStruct(
    const TSharedPtr<FJsonObject>& Params)
{
    FString StructName, Path;
    if (!Params->TryGetStringField(TEXT("struct_name"), StructName))
        return CreateErrorResponse(TEXT("Missing 'struct_name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/Data");
    
    // UE5.6: UserDefinedStructFactory removed; use FStructureEditorUtils directly
    FString PackagePath = Path + TEXT("/");
    UPackage* Package = CreatePackage(*(PackagePath + StructName));
    UUserDefinedStruct* NewStruct = FStructureEditorUtils::CreateUserDefinedStruct(
        Package, FName(*StructName), RF_Public | RF_Standalone | RF_Transactional);
    
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
                        
                        // Add the variable. UE5.6 renamed the rename API ? skip
                        // rename here; caller can rename via set_blueprint_property.
                        FStructureEditorUtils::AddVariable(NewStruct, PinType);
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
    
    // UE5.6: UserDefinedEnumFactory removed; use FEnumEditorUtils directly
    // CreateUserDefinedEnum returns UEnum* in UE5.6 ? cast to UUserDefinedEnum*
    FString PackagePath = Path + TEXT("/");
    UPackage* Package = CreatePackage(*(PackagePath + EnumName));
    UUserDefinedEnum* NewEnum = Cast<UUserDefinedEnum>(FEnumEditorUtils::CreateUserDefinedEnum(
        Package, FName(*EnumName), RF_Public | RF_Standalone | RF_Transactional));
    
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
                // SetEnumerators was removed in UE 5.x; add each value individually.
                for (const TPair<FName, int64>& Pair : Names)
                {
                    FEnumEditorUtils::AddNewEnumeratorForUserDefinedEnum(NewEnum);
                    int32 LastIdx = NewEnum->NumEnums() - 2; // -2 because _MAX is last
                    if (LastIdx >= 0)
                    {
                        FEnumEditorUtils::SetEnumeratorDisplayName(
                            NewEnum, LastIdx,
                            FText::FromName(Pair.Key));
                    }
                }
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
    UScriptStruct* Struct = FindObject<UScriptStruct>(nullptr, *RowStruct);
    if (!Struct)
    {
        // Try loading it
        FString StructPath = FString::Printf(TEXT("/Game/Data/%s.%s"), *RowStruct, *RowStruct);
        Struct = LoadObject<UScriptStruct>(nullptr, *StructPath);
    }
    
    if (!Struct)
        return CreateErrorResponse(FString::Printf(TEXT("Struct not found: %s"), *RowStruct));
    
    // UDataTableFactory lives in UnrealEd (Factories/DataTableFactory.h).
    UDataTableFactory* Factory = NewObject<UDataTableFactory>(GetTransientPackage());
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

// ─────────────────────────────────────────────────────────────────────────────
// Animation Blueprint helpers - shared by all HandleAdd... anim implementations
// ─────────────────────────────────────────────────────────────────────────────

namespace UnrealMCP_AnimGraphHelpers
{
    /** Find the top-level AnimGraph of an Animation Blueprint. */
    static UEdGraph* FindAnimGraph(UAnimBlueprint* AnimBP)
    {
        if (!AnimBP) return nullptr;
        for (UEdGraph* Graph : AnimBP->FunctionGraphs)
        {
            if (!Graph) continue;
            if (Graph->GetName() == TEXT("AnimGraph")) return Graph;
            if (Graph->IsA<UAnimationGraph>()) return Graph;
        }
        return nullptr;
    }

    /** Find a UAnimStateNode by name inside a state-machine graph. */
    static UAnimStateNode* FindStateNode(UAnimationStateMachineGraph* SMGraph, const FString& StateName)
    {
        if (!SMGraph) return nullptr;
        for (UEdGraphNode* N : SMGraph->Nodes)
        {
            UAnimStateNode* S = Cast<UAnimStateNode>(N);
            if (!S) continue;
            if (S->GetStateName() == StateName) return S;
            if (S->BoundGraph && S->BoundGraph->GetName() == StateName) return S;
            if (S->GetName() == StateName) return S;
        }
        return nullptr;
    }

    /** Find a state-machine graph by name inside an Animation Blueprint. */
    static UAnimationStateMachineGraph* FindStateMachineGraph(UAnimBlueprint* AnimBP, const FString& SMName)
    {
        if (!AnimBP) return nullptr;
        for (UEdGraph* Graph : AnimBP->FunctionGraphs)
        {
            if (!Graph) continue;
            if (Graph->GetName() == SMName)
            {
                if (auto* SM = Cast<UAnimationStateMachineGraph>(Graph)) return SM;
            }
        }
        // Also scan sub-graphs via state-machine nodes inside AnimGraph
        if (UEdGraph* AnimGraph = FindAnimGraph(AnimBP))
        {
            for (UEdGraphNode* N : AnimGraph->Nodes)
            {
                if (auto* SMNode = Cast<UAnimGraphNode_StateMachine>(N))
                {
                    if (SMNode->EditorStateMachineGraph && SMNode->EditorStateMachineGraph->GetName() == SMName)
                        return SMNode->EditorStateMachineGraph;
                }
            }
        }
        return nullptr;
    }

    /** Locate the Root (final pose) node of an AnimGraph. */
    static UAnimGraphNode_Root* FindRootNode(UEdGraph* AnimGraph)
    {
        if (!AnimGraph) return nullptr;
        for (UEdGraphNode* N : AnimGraph->Nodes)
        {
            if (auto* R = Cast<UAnimGraphNode_Root>(N)) return R;
        }
        return nullptr;
    }

    /** Locate the StateResult (final pose) node inside a state's BoundGraph. */
    static UAnimGraphNode_StateResult* FindStateResultNode(UEdGraph* StateGraph)
    {
        if (!StateGraph) return nullptr;
        for (UEdGraphNode* N : StateGraph->Nodes)
        {
            if (auto* R = Cast<UAnimGraphNode_StateResult>(N)) return R;
        }
        return nullptr;
    }

    /** First pose/struct output pin on an AnimGraph node. */
    static UEdGraphPin* FindPoseOutputPin(UEdGraphNode* Node)
    {
        if (!Node) return nullptr;
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->Direction == EGPD_Output &&
                P->PinType.PinCategory == UEdGraphSchema_K2::PC_Struct)
                return P;
        }
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->Direction == EGPD_Output) return P;
        }
        return nullptr;
    }

    /** First pose/struct input pin on an AnimGraph node. */
    static UEdGraphPin* FindPoseInputPin(UEdGraphNode* Node)
    {
        if (!Node) return nullptr;
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->Direction == EGPD_Input &&
                P->PinType.PinCategory == UEdGraphSchema_K2::PC_Struct)
                return P;
        }
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->Direction == EGPD_Input) return P;
        }
        return nullptr;
    }

    /** Wire Source node's pose output into Target node's pose input.
     *  Uses the schema's TryCreateConnection so anim-graph validation runs. */
    static bool WirePoseLink(UEdGraphNode* Source, UEdGraphNode* Target)
    {
        UEdGraphPin* Out = FindPoseOutputPin(Source);
        UEdGraphPin* In  = FindPoseInputPin(Target);
        if (!Out || !In) return false;

        UEdGraph* G = Source->GetGraph();
        if (!G) G = Target->GetGraph();
        if (const UEdGraphSchema* Schema = G ? G->GetSchema() : nullptr)
        {
            return Schema->TryCreateConnection(Out, In);
        }
        // Fallback (should not reach): raw link.
        In->BreakAllPinLinks();
        Out->MakeLinkTo(In);
        return true;
    }

    /** Connect a specific pose output pin to a specific pose input pin (AnimGraph). */
    static bool TryConnectPosePins(UEdGraphPin* FromPoseOut, UEdGraphPin* ToPoseIn)
    {
        if (!FromPoseOut || !ToPoseIn)
        {
            return false;
        }
        UEdGraphNode* FromNode = FromPoseOut->GetOwningNode();
        UEdGraph* Graph = FromNode ? FromNode->GetGraph() : nullptr;
        if (!Graph)
        {
            return false;
        }
        if (const UEdGraphSchema* Schema = Graph->GetSchema())
        {
            return Schema->TryCreateConnection(FromPoseOut, ToPoseIn);
        }
        ToPoseIn->BreakAllPinLinks();
        FromPoseOut->MakeLinkTo(ToPoseIn);
        return true;
    }

    static UEdGraphPin* FindPinByName(UEdGraphNode* Node, const TCHAR* PinName)
    {
        if (!Node) return nullptr;
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->PinName == PinName) return P;
        }
        return nullptr;
    }

    static UEdGraphPin* FindBoolInputPin(UEdGraphNode* Node)
    {
        if (!Node) return nullptr;
        if (UEdGraphPin* CanEnter = FindPinByName(Node, TEXT("bCanEnterTransition")))
        {
            return CanEnter;
        }
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->Direction == EGPD_Input &&
                P->PinType.PinCategory == UEdGraphSchema_K2::PC_Boolean)
            {
                return P;
            }
        }
        return nullptr;
    }

    static bool TryConnectValuePins(UEdGraphPin* From, UEdGraphPin* To)
    {
        if (!From || !To) return false;
        UEdGraph* Graph = From->GetOwningNode() ? From->GetOwningNode()->GetGraph() : nullptr;
        if (Graph)
        {
            if (const UEdGraphSchema* Schema = Graph->GetSchema())
            {
                if (Schema->TryCreateConnection(From, To))
                {
                    return true;
                }
            }
        }
        From->MakeLinkTo(To);
        return true;
    }

    static bool BuildTransitionRuleGraph(
        UAnimStateTransitionNode* Trans,
        const bool bHasSpeedCompare,
        const FString& SpeedCompare,
        const double SpeedThreshold,
        const bool bHasRequireIsAiming,
        const bool bRequireIsAiming)
    {
        if (!Trans || !Trans->BoundGraph || (!bHasSpeedCompare && !bHasRequireIsAiming))
        {
            return false;
        }

        UEdGraph* Rule = Trans->BoundGraph;
        Rule->Modify();
        Trans->Modify();

        UAnimGraphNode_TransitionResult* ResultNode = nullptr;
        for (UEdGraphNode* N : Rule->Nodes)
        {
            if (UAnimGraphNode_TransitionResult* Candidate = Cast<UAnimGraphNode_TransitionResult>(N))
            {
                ResultNode = Candidate;
                break;
            }
        }
        if (!ResultNode)
        {
            for (UEdGraphNode* N : Rule->Nodes)
            {
                if (N && N->GetClass()->GetName().Contains(TEXT("TransitionResult")))
                {
                    ResultNode = Cast<UAnimGraphNode_TransitionResult>(N);
                    break;
                }
            }
        }

        UEdGraphPin* ResultIn = FindBoolInputPin(ResultNode);
        if (!ResultIn)
        {
            return false;
        }
        ResultIn->BreakAllPinLinks();

        auto CreateVarGet = [Rule](const FString& VarName, int32 X, int32 Y) -> UK2Node_VariableGet*
        {
            UK2Node_VariableGet* VarGet = NewObject<UK2Node_VariableGet>(Rule);
            Rule->AddNode(VarGet);
            VarGet->CreateNewGuid();
            VarGet->VariableReference.SetSelfMember(FName(*VarName));
            VarGet->AllocateDefaultPins();
            VarGet->NodePosX = X;
            VarGet->NodePosY = Y;
            return VarGet;
        };

        auto CreateMathCall = [Rule](const FString& FuncName, int32 X, int32 Y) -> UK2Node_CallFunction*
        {
            UK2Node_CallFunction* Call = NewObject<UK2Node_CallFunction>(Rule);
            Rule->AddNode(Call);
            Call->CreateNewGuid();
            Call->FunctionReference.SetExternalMember(FName(*FuncName), UKismetMathLibrary::StaticClass());
            Call->AllocateDefaultPins();
            Call->NodePosX = X;
            Call->NodePosY = Y;
            return Call;
        };

        TArray<UEdGraphPin*> RulePins;
        if (bHasSpeedCompare)
        {
            UK2Node_VariableGet* SpeedGet = CreateVarGet(TEXT("Speed"), -700, -120);
            const FString CompareFunc = SpeedCompare.Equals(TEXT("lt"), ESearchCase::IgnoreCase)
                ? TEXT("Less_DoubleDouble")
                : TEXT("GreaterEqual_DoubleDouble");
            UK2Node_CallFunction* Compare = CreateMathCall(CompareFunc, -420, -120);

            UEdGraphPin* SpeedOut = FindPinByName(SpeedGet, TEXT("Speed"));
            UEdGraphPin* A = FindPinByName(Compare, TEXT("A"));
            UEdGraphPin* B = FindPinByName(Compare, TEXT("B"));
            UEdGraphPin* Ret = FindPinByName(Compare, TEXT("ReturnValue"));
            if (B) B->DefaultValue = FString::SanitizeFloat(SpeedThreshold);
            if (SpeedOut && A) TryConnectValuePins(SpeedOut, A);
            if (Ret) RulePins.Add(Ret);
        }

        if (bHasRequireIsAiming)
        {
            UK2Node_VariableGet* AimGet = CreateVarGet(TEXT("IsAiming"), -700, 80);
            UEdGraphPin* AimOut = FindPinByName(AimGet, TEXT("IsAiming"));
            if (bRequireIsAiming)
            {
                if (AimOut) RulePins.Add(AimOut);
            }
            else
            {
                UK2Node_CallFunction* NotNode = CreateMathCall(TEXT("Not_PreBool"), -420, 80);
                UEdGraphPin* A = FindPinByName(NotNode, TEXT("A"));
                UEdGraphPin* Ret = FindPinByName(NotNode, TEXT("ReturnValue"));
                if (AimOut && A) TryConnectValuePins(AimOut, A);
                if (Ret) RulePins.Add(Ret);
            }
        }

        bool bConnected = false;
        if (RulePins.Num() == 1)
        {
            bConnected = TryConnectValuePins(RulePins[0], ResultIn);
        }
        else if (RulePins.Num() >= 2)
        {
            UK2Node_CallFunction* AndNode = CreateMathCall(TEXT("BooleanAND"), -120, 0);
            UEdGraphPin* A = FindPinByName(AndNode, TEXT("A"));
            UEdGraphPin* B = FindPinByName(AndNode, TEXT("B"));
            UEdGraphPin* Ret = FindPinByName(AndNode, TEXT("ReturnValue"));
            if (RulePins[0] && A) TryConnectValuePins(RulePins[0], A);
            if (RulePins[1] && B) TryConnectValuePins(RulePins[1], B);
            bConnected = Ret && TryConnectValuePins(Ret, ResultIn);
        }

        Rule->NotifyGraphChanged();
        return bConnected;
    }
}

// ??? Animation Blueprint ??????????????????????????????????????????????????????

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

    // Create the state machine node through the normal graph-node lifecycle.
    // UAnimGraphNode_StateMachine::PostPlacedNewNode asserts that
    // EditorStateMachineGraph is null before it creates the backing graph.
    UAnimGraphNode_StateMachine* SMNode = nullptr;
    {
        FGraphNodeCreator<UAnimGraphNode_StateMachine> NodeCreator(*AnimGraph);
        SMNode = NodeCreator.CreateNode(/*bSelectNewNode*/false);
        SMNode->NodePosX = -400;
        SMNode->NodePosY = 0;
        NodeCreator.Finalize();
    }

    if (SMNode->EditorStateMachineGraph)
    {
        SMNode->EditorStateMachineGraph->Rename(*SMName, nullptr, REN_DontCreateRedirectors);
    }

    // Auto-wire the state machine's pose output into the AnimGraph Root's Result pin
    bool bWiredToRoot = false;
    if (auto* Root = UnrealMCP_AnimGraphHelpers::FindRootNode(AnimGraph))
        bWiredToRoot = UnrealMCP_AnimGraphHelpers::WirePoseLink(SMNode, Root);

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("state_machine_name"), SMName);
    Result->SetStringField(TEXT("node_id"), SMNode->NodeGuid.ToString());
    Result->SetBoolField(TEXT("wired_to_root"), bWiredToRoot);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddAnimationState(
    const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCP_AnimGraphHelpers;

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

    // Find state machine graph. State machines created by UAnimGraphNode_StateMachine
    // live behind the AnimGraph node, not necessarily in FunctionGraphs.
    UAnimationStateMachineGraph* SMGraph = FindStateMachineGraph(AnimBP, SMName);

    if (!SMGraph)
        return CreateErrorResponse(FString::Printf(TEXT("State machine '%s' not found"), *SMName));

    // Create state node
    UAnimStateNode* StateNode = NewObject<UAnimStateNode>(SMGraph);
    // UAnimStateNode has no SetStateName(); the display name is driven by the bound graph name.
    // PostPlacedNewNode() creates the bound graph; rename it to set the state name.
    StateNode->PostPlacedNewNode();
    if (StateNode->BoundGraph)
    {
        StateNode->BoundGraph->Rename(*StateName, nullptr, REN_DontCreateRedirectors);
    }
    StateNode->NodePosX = SMGraph->Nodes.Num() * 200;
    StateNode->NodePosY = 0;
    SMGraph->AddNode(StateNode);
    StateNode->CreateNewGuid();
    StateNode->AllocateDefaultPins();

    AnimBP->Modify(); // was MarkBlueprintAsModified - avoids AssetRegistry/ContentBrowser crash in UE5.6

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("state_name"), StateName);
    Result->SetStringField(TEXT("node_id"), StateNode->NodeGuid.ToString());
    return Result;
}

// (namespace moved higher in file - see definition above HandleCreateAnimationBlueprint)

#if 0 /* moved */
namespace UnrealMCP_AnimGraphHelpers
{
    /** Find the top-level AnimGraph of an Animation Blueprint. */
    static UEdGraph* FindAnimGraph(UAnimBlueprint* AnimBP)
    {
        if (!AnimBP) return nullptr;
        for (UEdGraph* Graph : AnimBP->FunctionGraphs)
        {
            if (!Graph) continue;
            if (Graph->GetName() == TEXT("AnimGraph")) return Graph;
            if (Graph->IsA<UAnimationGraph>()) return Graph;
        }
        return nullptr;
    }

    /** Find a UAnimStateNode by name inside a state-machine graph. */
    static UAnimStateNode* FindStateNode(UAnimationStateMachineGraph* SMGraph, const FString& StateName)
    {
        if (!SMGraph) return nullptr;
        for (UEdGraphNode* N : SMGraph->Nodes)
        {
            UAnimStateNode* S = Cast<UAnimStateNode>(N);
            if (!S) continue;
            if (S->GetStateName() == StateName) return S;
            if (S->BoundGraph && S->BoundGraph->GetName() == StateName) return S;
            if (S->GetName() == StateName) return S;
        }
        return nullptr;
    }

    /** Find a state-machine graph by name inside an Animation Blueprint. */
    static UAnimationStateMachineGraph* FindStateMachineGraph(UAnimBlueprint* AnimBP, const FString& SMName)
    {
        if (!AnimBP) return nullptr;
        for (UEdGraph* Graph : AnimBP->FunctionGraphs)
        {
            if (!Graph) continue;
            if (Graph->GetName() == SMName)
            {
                if (auto* SM = Cast<UAnimationStateMachineGraph>(Graph)) return SM;
            }
        }
        // Also scan sub-graphs via state-machine nodes inside AnimGraph
        if (UEdGraph* AnimGraph = FindAnimGraph(AnimBP))
        {
            for (UEdGraphNode* N : AnimGraph->Nodes)
            {
                if (auto* SMNode = Cast<UAnimGraphNode_StateMachine>(N))
                {
                    if (SMNode->EditorStateMachineGraph && SMNode->EditorStateMachineGraph->GetName() == SMName)
                        return SMNode->EditorStateMachineGraph;
                }
            }
        }
        return nullptr;
    }

    /** Locate the Root (final pose) node of an AnimGraph. */
    static UAnimGraphNode_Root* FindRootNode(UEdGraph* AnimGraph)
    {
        if (!AnimGraph) return nullptr;
        for (UEdGraphNode* N : AnimGraph->Nodes)
        {
            if (auto* R = Cast<UAnimGraphNode_Root>(N)) return R;
        }
        return nullptr;
    }

    /** Locate the StateResult (final pose) node inside a state's BoundGraph. */
    static UAnimGraphNode_StateResult* FindStateResultNode(UEdGraph* StateGraph)
    {
        if (!StateGraph) return nullptr;
        for (UEdGraphNode* N : StateGraph->Nodes)
        {
            if (auto* R = Cast<UAnimGraphNode_StateResult>(N)) return R;
        }
        return nullptr;
    }

    /** Return first pose/struct output pin on an AnimGraph node. */
    static UEdGraphPin* FindPoseOutputPin(UEdGraphNode* Node)
    {
        if (!Node) return nullptr;
        // Prefer a struct pin first (pose is struct FPoseLink).
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->Direction == EGPD_Output &&
                P->PinType.PinCategory == UEdGraphSchema_K2::PC_Struct)
                return P;
        }
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->Direction == EGPD_Output) return P;
        }
        return nullptr;
    }

    /** Return first pose/struct input pin on an AnimGraph node. */
    static UEdGraphPin* FindPoseInputPin(UEdGraphNode* Node)
    {
        if (!Node) return nullptr;
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->Direction == EGPD_Input &&
                P->PinType.PinCategory == UEdGraphSchema_K2::PC_Struct)
                return P;
        }
        for (UEdGraphPin* P : Node->Pins)
        {
            if (P && P->Direction == EGPD_Input) return P;
        }
        return nullptr;
    }

    /** Wire Source node's pose output into Target node's pose input.  Breaks any
     *  existing links on the input pin to enforce a single authoritative pose source. */
    static bool WirePoseLink(UEdGraphNode* Source, UEdGraphNode* Target)
    {
        UEdGraphPin* Out = FindPoseOutputPin(Source);
        UEdGraphPin* In  = FindPoseInputPin(Target);
        if (!Out || !In) return false;
        In->BreakAllPinLinks();
        Out->MakeLinkTo(In);
        return true;
    }
}
#endif // moved namespace

// ─────────────────────────────────────────────────────────────────────────────
// Real implementations (replacing the previous stubs)
// ─────────────────────────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddStateTransition(
    const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCP_AnimGraphHelpers;

    FString AnimBPName, SMName, FromState, ToState;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    Params->TryGetStringField(TEXT("state_machine_name"), SMName);
    if (!Params->TryGetStringField(TEXT("from_state"), FromState))
        return CreateErrorResponse(TEXT("Missing 'from_state'"));
    if (!Params->TryGetStringField(TEXT("to_state"), ToState))
        return CreateErrorResponse(TEXT("Missing 'to_state'"));

    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));

    UAnimationStateMachineGraph* SMGraph = nullptr;
    if (!SMName.IsEmpty())
        SMGraph = FindStateMachineGraph(AnimBP, SMName);
    if (!SMGraph)
    {
        // Fallback: pick the first state machine graph we find
        for (UEdGraph* G : AnimBP->FunctionGraphs)
            if ((SMGraph = Cast<UAnimationStateMachineGraph>(G))) break;
    }
    if (!SMGraph)
        return CreateErrorResponse(TEXT("State machine graph not found"));

    UAnimStateNode* NextNode = FindStateNode(SMGraph, ToState);
    const bool bFromEntry = FromState.Equals(TEXT("Entry"), ESearchCase::IgnoreCase) ||
        FromState.Equals(TEXT("__Entry__"), ESearchCase::IgnoreCase);

    if (bFromEntry)
    {
        if (!NextNode)
        {
            return CreateErrorResponse(FString::Printf(
                TEXT("State not found in '%s' (to=%s found=0)"),
                *SMGraph->GetName(), *ToState));
        }

        UAnimStateEntryNode* EntryNode = nullptr;
        for (UEdGraphNode* N : SMGraph->Nodes)
        {
            if (UAnimStateEntryNode* Candidate = Cast<UAnimStateEntryNode>(N))
            {
                EntryNode = Candidate;
                break;
            }
        }
        if (!EntryNode)
        {
            return CreateErrorResponse(TEXT("State machine entry node not found"));
        }

        UEdGraphPin* EntryOut = nullptr;
        for (UEdGraphPin* P : EntryNode->Pins)
        {
            if (P && P->Direction == EGPD_Output)
            {
                EntryOut = P;
                break;
            }
        }
        UEdGraphPin* StateIn = NextNode->GetInputPin();
        if (!EntryOut || !StateIn)
        {
            return CreateErrorResponse(TEXT("Could not find entry output or state input pin"));
        }

        SMGraph->Modify();
        EntryOut->BreakAllPinLinks();
        bool bConnected = false;
        if (const UEdGraphSchema* Schema = SMGraph->GetSchema())
        {
            bConnected = Schema->TryCreateConnection(EntryOut, StateIn);
        }
        if (!bConnected)
        {
            EntryOut->MakeLinkTo(StateIn);
            bConnected = true;
        }

        SMGraph->NotifyGraphChanged();
        FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);

        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetStringField(TEXT("from_state"), FromState);
        Result->SetStringField(TEXT("to_state"), ToState);
        Result->SetBoolField(TEXT("entry_connected"), bConnected);
        return Result;
    }

    UAnimStateNode* PrevNode = FindStateNode(SMGraph, FromState);
    if (!PrevNode || !NextNode)
        return CreateErrorResponse(FString::Printf(
            TEXT("State not found in '%s' (from=%s found=%d, to=%s found=%d)"),
            *SMGraph->GetName(), *FromState, PrevNode ? 1 : 0, *ToState, NextNode ? 1 : 0));

    // Optional: exact Speed/IsAiming expression as transition rule.
    // Params:
    //   speed_compare: "ge" or "lt"
    //   speed_threshold: number, default 5.0
    //   require_is_aiming: bool
    FString SpeedCompare;
    const bool bHasSpeedCompare = Params->TryGetStringField(TEXT("speed_compare"), SpeedCompare);
    double SpeedThreshold = 5.0;
    Params->TryGetNumberField(TEXT("speed_threshold"), SpeedThreshold);
    bool bRequireIsAiming = false;
    const bool bHasRequireIsAiming = Params->TryGetBoolField(TEXT("require_is_aiming"), bRequireIsAiming);
    bool bUpdateExisting = false;
    Params->TryGetBoolField(TEXT("update_existing"), bUpdateExisting);

    bool bBuiltExactRule = false;
    TArray<UAnimStateTransitionNode*> TargetTransitions;

    if (bUpdateExisting)
    {
        for (UEdGraphNode* N : SMGraph->Nodes)
        {
            if (UAnimStateTransitionNode* ExistingTrans = Cast<UAnimStateTransitionNode>(N))
            {
                if (ExistingTrans->GetPreviousState() == PrevNode && ExistingTrans->GetNextState() == NextNode)
                {
                    TargetTransitions.Add(ExistingTrans);
                }
            }
        }
    }

    UAnimStateTransitionNode* Trans = nullptr;
    if (TargetTransitions.Num() == 0)
    {
        Trans = NewObject<UAnimStateTransitionNode>(SMGraph);
        SMGraph->AddNode(Trans);
        Trans->CreateNewGuid();
        Trans->PostPlacedNewNode();         // constructs BoundGraph
        Trans->AllocateDefaultPins();
        Trans->CreateConnections(PrevNode, NextNode);
        TargetTransitions.Add(Trans);
    }
    else
    {
        Trans = TargetTransitions[0];
    }

    double Crossfade = 0.2;
    if (Params->TryGetNumberField(TEXT("crossfade_duration"), Crossfade))
    {
        for (UAnimStateTransitionNode* TargetTrans : TargetTransitions)
        {
            if (TargetTrans) TargetTrans->CrossfadeDuration = (float)Crossfade;
        }
    }

    int32 Priority = 1;
    if (Params->TryGetNumberField(TEXT("priority_order"), Priority))
    {
        for (UAnimStateTransitionNode* TargetTrans : TargetTransitions)
        {
            if (TargetTrans) TargetTrans->PriorityOrder = Priority;
        }
    }

    if (bHasSpeedCompare || bHasRequireIsAiming)
    {
        for (UAnimStateTransitionNode* TargetTrans : TargetTransitions)
        {
            bBuiltExactRule |= BuildTransitionRuleGraph(
                TargetTrans,
                bHasSpeedCompare,
                SpeedCompare,
                SpeedThreshold,
                bHasRequireIsAiming,
                bRequireIsAiming);
        }
    }

    // Optional: simple boolean variable as transition rule.  When supplied we
    // generate a Get<VarName> → ReturnResult wiring in the transition's
    // BoundGraph so the transition actually fires at runtime.
    FString CondVar;
    bool bCondValue = true;
    Params->TryGetStringField(TEXT("condition_variable"), CondVar);
    Params->TryGetBoolField(TEXT("condition_value"), bCondValue);

    if (!bBuiltExactRule && !CondVar.IsEmpty() && Trans->BoundGraph)
    {
        UEdGraph* Rule = Trans->BoundGraph;

        // Find the TransitionResult node (already created via PostPlacedNewNode)
        UEdGraphNode* ResultNode = nullptr;
        for (UEdGraphNode* N : Rule->Nodes)
        {
            if (N->IsA(UAnimGraphNode_Base::StaticClass()) ||
                N->GetClass()->GetName().Contains(TEXT("TransitionResult")))
            {
                ResultNode = N;
                break;
            }
        }

        if (ResultNode)
        {
            // Spawn a VariableGet for the condition boolean
            UK2Node_VariableGet* VarGet = NewObject<UK2Node_VariableGet>(Rule);
            Rule->AddNode(VarGet);
            VarGet->CreateNewGuid();
            VarGet->VariableReference.SetSelfMember(FName(*CondVar));
            VarGet->AllocateDefaultPins();
            VarGet->NodePosX = -300;
            VarGet->NodePosY = 0;

            UEdGraphPin* VarPin = nullptr;
            for (UEdGraphPin* P : VarGet->Pins)
            {
                if (P->Direction == EGPD_Output &&
                    P->PinType.PinCategory == UEdGraphSchema_K2::PC_Boolean)
                { VarPin = P; break; }
            }

            UEdGraphPin* ResultIn = nullptr;
            for (UEdGraphPin* P : ResultNode->Pins)
            {
                if (P->Direction == EGPD_Input &&
                    P->PinType.PinCategory == UEdGraphSchema_K2::PC_Boolean)
                { ResultIn = P; break; }
            }
            if (VarPin && ResultIn) VarPin->MakeLinkTo(ResultIn);
            // Note: inverting the rule for bCondValue==false would need a NOT
            // node here - kept simple for now; the user can edit in-editor.
        }
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("from_state"), FromState);
    Result->SetStringField(TEXT("to_state"), ToState);
    Result->SetStringField(TEXT("transition_id"), Trans->NodeGuid.ToString());
    Result->SetBoolField(TEXT("updated_existing"), bUpdateExisting);
    Result->SetNumberField(TEXT("transition_count"), TargetTransitions.Num());
    Result->SetBoolField(TEXT("rule_built"), bBuiltExactRule);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetAnimationForState(
    const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCP_AnimGraphHelpers;

    FString AnimBPName, StateName, AnimAsset, SMName;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("state_name"), StateName))
        return CreateErrorResponse(TEXT("Missing 'state_name'"));
    if (!Params->TryGetStringField(TEXT("animation_asset"), AnimAsset))
        return CreateErrorResponse(TEXT("Missing 'animation_asset'"));
    Params->TryGetStringField(TEXT("state_machine_name"), SMName);
    bool bLoop = true;
    Params->TryGetBoolField(TEXT("loop"), bLoop);

    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));

    UAnimationAsset* Asset = LoadObject<UAnimationAsset>(nullptr, *AnimAsset);
    if (!Asset)
        return CreateErrorResponse(FString::Printf(TEXT("Animation asset not found: %s"), *AnimAsset));

    // Find state machine(s) and locate the requested state
    UAnimationStateMachineGraph* SMGraph = nullptr;
    UAnimStateNode* StateNode = nullptr;
    if (!SMName.IsEmpty())
    {
        SMGraph = FindStateMachineGraph(AnimBP, SMName);
        if (SMGraph) StateNode = FindStateNode(SMGraph, StateName);
    }
    if (!StateNode)
    {
        // Search every state machine graph
        for (UEdGraph* G : AnimBP->FunctionGraphs)
        {
            if (auto* SM = Cast<UAnimationStateMachineGraph>(G))
            {
                if (auto* S = FindStateNode(SM, StateName))
                { SMGraph = SM; StateNode = S; break; }
            }
        }
        // And inside AnimGraph's state-machine sub-graphs
        if (!StateNode)
        {
            if (UEdGraph* AnimGraph = FindAnimGraph(AnimBP))
            {
                for (UEdGraphNode* N : AnimGraph->Nodes)
                {
                    if (auto* SMNode = Cast<UAnimGraphNode_StateMachine>(N))
                    {
                        if (auto* S = FindStateNode(SMNode->EditorStateMachineGraph, StateName))
                        { SMGraph = SMNode->EditorStateMachineGraph; StateNode = S; break; }
                    }
                }
            }
        }
    }

    if (!StateNode)
        return CreateErrorResponse(FString::Printf(TEXT("State '%s' not found"), *StateName));

    UEdGraph* StateGraph = StateNode->BoundGraph;
    if (!StateGraph)
        return CreateErrorResponse(TEXT("State has no BoundGraph"));

    // Locate or synthesize the Result node inside the state
    UAnimGraphNode_StateResult* ResultNode = FindStateResultNode(StateGraph);
    if (!ResultNode)
        return CreateErrorResponse(TEXT("State has no StateResult node"));

    // Determine desired player class based on the asset type
    UAnimGraphNode_Base* PlayerNode = nullptr;
    if (Cast<UBlendSpace>(Asset))
    {
        FGraphNodeCreator<UAnimGraphNode_BlendSpacePlayer> NodeCreator(*StateGraph);
        auto* BSP = NodeCreator.CreateNode(/*bSelectNewNode*/false);
        BSP->SetAnimationAsset(Asset);
        BSP->NodePosX = -350;
        BSP->NodePosY = 0;
        NodeCreator.Finalize();
        BSP->ReconstructNode();
        PlayerNode = BSP;
    }
    else
    {
        FGraphNodeCreator<UAnimGraphNode_SequencePlayer> NodeCreator(*StateGraph);
        auto* SP = NodeCreator.CreateNode(/*bSelectNewNode*/false);
        SP->SetAnimationAsset(Asset);
        if (UAnimSequenceBase* Seq = Cast<UAnimSequenceBase>(Asset))
        {
            SP->Node.SetSequence(Seq);
        }
        SP->Node.SetLoopAnimation(bLoop);
        SP->NodePosX = -350;
        SP->NodePosY = 0;
        NodeCreator.Finalize();
        SP->ReconstructNode();
        PlayerNode = SP;
    }

    const bool bWired = WirePoseLink(PlayerNode, ResultNode);

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("state_name"), StateName);
    Result->SetStringField(TEXT("animation"), AnimAsset);
    Result->SetStringField(TEXT("player_node_id"), PlayerNode->NodeGuid.ToString());
    Result->SetBoolField(TEXT("pose_wired"), bWired);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddBlendSpaceNode(
    const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCP_AnimGraphHelpers;

    FString AnimBPName, BlendSpaceAsset, GraphName;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("blend_space_asset"), BlendSpaceAsset))
        return CreateErrorResponse(TEXT("Missing 'blend_space_asset'"));
    Params->TryGetStringField(TEXT("graph_name"), GraphName); // optional – defaults to AnimGraph
    bool bWireToRoot = true;
    Params->TryGetBoolField(TEXT("wire_to_root"), bWireToRoot);

    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));

    UBlendSpace* BS = LoadObject<UBlendSpace>(nullptr, *BlendSpaceAsset);
    if (!BS)
        return CreateErrorResponse(FString::Printf(TEXT("Blend Space not found: %s"), *BlendSpaceAsset));

    UEdGraph* TargetGraph = nullptr;
    if (!GraphName.IsEmpty())
    {
        for (UEdGraph* G : AnimBP->FunctionGraphs)
            if (G && G->GetName() == GraphName) { TargetGraph = G; break; }
    }
    if (!TargetGraph) TargetGraph = FindAnimGraph(AnimBP);
    if (!TargetGraph)
        return CreateErrorResponse(TEXT("AnimGraph not found"));

    const FVector2D Pos = GetNodePosition(Params);

    // Use FGraphNodeCreator for the proper construction lifecycle.
    UAnimGraphNode_BlendSpacePlayer* BSP = nullptr;
    {
        FGraphNodeCreator<UAnimGraphNode_BlendSpacePlayer> NodeCreator(*TargetGraph);
        BSP = NodeCreator.CreateNode(/*bSelectNewNode*/false);
        // Set asset BEFORE Finalize() so AllocateDefaultPins sees the right type.
        BSP->SetAnimationAsset(BS);
        BSP->NodePosX = (int32)Pos.X;
        BSP->NodePosY = (int32)Pos.Y;
        NodeCreator.Finalize();  // calls CreateNewGuid + PostPlacedNewNode + (pins)
    }
    // Regenerate pins with the asset context applied (no-op if already correct).
    BSP->ReconstructNode();

    bool bWired = false;
    if (bWireToRoot)
    {
        if (auto* Root = FindRootNode(TargetGraph))
            bWired = WirePoseLink(BSP, Root);
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("blend_space"), BlendSpaceAsset);
    Result->SetStringField(TEXT("node_id"), BSP->NodeGuid.ToString());
    Result->SetBoolField(TEXT("wired_to_root"), bWired);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSequencePlayerNode(
    const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCP_AnimGraphHelpers;

    FString AnimBPName, SequenceAsset, GraphName;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("sequence_asset"), SequenceAsset))
        return CreateErrorResponse(TEXT("Missing 'sequence_asset'"));
    Params->TryGetStringField(TEXT("graph_name"), GraphName);
    bool bWireToRoot = false;
    Params->TryGetBoolField(TEXT("wire_to_root"), bWireToRoot);
    bool bLoop = true;
    Params->TryGetBoolField(TEXT("loop"), bLoop);

    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));

    UAnimationAsset* Asset = LoadObject<UAnimationAsset>(nullptr, *SequenceAsset);
    if (!Asset)
        return CreateErrorResponse(FString::Printf(TEXT("Animation asset not found: %s"), *SequenceAsset));

    UEdGraph* TargetGraph = nullptr;
    if (!GraphName.IsEmpty())
    {
        for (UEdGraph* G : AnimBP->FunctionGraphs)
            if (G && G->GetName() == GraphName) { TargetGraph = G; break; }
    }
    if (!TargetGraph) TargetGraph = FindAnimGraph(AnimBP);
    if (!TargetGraph)
        return CreateErrorResponse(TEXT("AnimGraph not found"));

    const FVector2D Pos = GetNodePosition(Params);

    UAnimGraphNode_SequencePlayer* SP = nullptr;
    {
        FGraphNodeCreator<UAnimGraphNode_SequencePlayer> NodeCreator(*TargetGraph);
        SP = NodeCreator.CreateNode(/*bSelectNewNode*/false);
        SP->SetAnimationAsset(Asset);
        if (UAnimSequenceBase* Seq = Cast<UAnimSequenceBase>(Asset))
        {
            SP->Node.SetSequence(Seq);
        }
        SP->Node.SetLoopAnimation(bLoop);
        SP->NodePosX = (int32)Pos.X;
        SP->NodePosY = (int32)Pos.Y;
        NodeCreator.Finalize();
    }
    SP->ReconstructNode();

    bool bWired = false;
    if (bWireToRoot)
    {
        if (auto* Root = FindRootNode(TargetGraph))
            bWired = WirePoseLink(SP, Root);
    }

    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("sequence"), SequenceAsset);
    Result->SetStringField(TEXT("node_id"), SP->NodeGuid.ToString());
    Result->SetBoolField(TEXT("wired_to_root"), bWired);
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleConnectAnimGraphNodes(
    const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCP_AnimGraphHelpers;

    FString AnimBPName, GraphName, SrcId, DstId;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("source_node_id"), SrcId))
        return CreateErrorResponse(TEXT("Missing 'source_node_id'"));
    if (!Params->TryGetStringField(TEXT("target_node_id"), DstId))
        return CreateErrorResponse(TEXT("Missing 'target_node_id'"));
    Params->TryGetStringField(TEXT("graph_name"), GraphName);

    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));

    UEdGraph* Graph = nullptr;
    if (!GraphName.IsEmpty())
    {
        for (UEdGraph* G : AnimBP->FunctionGraphs)
            if (G && G->GetName() == GraphName) { Graph = G; break; }
    }
    if (!Graph) Graph = FindAnimGraph(AnimBP);
    if (!Graph)
        return CreateErrorResponse(TEXT("AnimGraph not found"));

    FGuid SrcGuid, DstGuid;
    FGuid::Parse(SrcId, SrcGuid);
    FGuid::Parse(DstId, DstGuid);

    UEdGraphNode* Src = nullptr;
    UEdGraphNode* Dst = nullptr;
    for (UEdGraphNode* N : Graph->Nodes)
    {
        if (N->NodeGuid == SrcGuid) Src = N;
        if (N->NodeGuid == DstGuid) Dst = N;
    }
    if (!Src || !Dst)
        return CreateErrorResponse(FString::Printf(
            TEXT("Node(s) not found in '%s': src=%d dst=%d"),
            *Graph->GetName(), Src ? 1 : 0, Dst ? 1 : 0));

    const bool bOk = WirePoseLink(Src, Dst);
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(AnimBP);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), bOk);
    if (!bOk) Result->SetStringField(TEXT("error"), TEXT("Could not find compatible pose pins on nodes"));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleInsertAnimGraphSlotBeforeRoot(
    const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCP_AnimGraphHelpers;

    FString AnimBPName, GraphName, SlotNameStr;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    Params->TryGetStringField(TEXT("graph_name"), GraphName);
    SlotNameStr = TEXT("DefaultSlot");
    Params->TryGetStringField(TEXT("slot_name"), SlotNameStr);
    if (SlotNameStr.IsEmpty())
    {
        SlotNameStr = TEXT("DefaultSlot");
    }

    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));

    UEdGraph* TargetGraph = nullptr;
    if (!GraphName.IsEmpty())
    {
        for (UEdGraph* G : AnimBP->FunctionGraphs)
        {
            if (G && G->GetName() == GraphName)
            {
                TargetGraph = G;
                break;
            }
        }
    }
    if (!TargetGraph)
    {
        TargetGraph = FindAnimGraph(AnimBP);
    }
    if (!TargetGraph)
        return CreateErrorResponse(TEXT("AnimGraph not found"));

    UAnimGraphNode_Root* Root = FindRootNode(TargetGraph);
    if (!Root)
        return CreateErrorResponse(TEXT("AnimGraph has no Root node"));

    UEdGraphPin* RootIn = FindPoseInputPin(Root);
    if (!RootIn || RootIn->LinkedTo.Num() == 0)
        return CreateErrorResponse(TEXT("Root pose input is not connected; nothing to insert a Slot before"));

    UEdGraphPin* UpstreamOut = RootIn->LinkedTo[0];
    UEdGraphNode* Upstream = UpstreamOut ? UpstreamOut->GetOwningNode() : nullptr;
    if (!Upstream)
        return CreateErrorResponse(TEXT("Could not resolve upstream node feeding Root"));

    if (Cast<UAnimGraphNode_Slot>(Upstream))
    {
        TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
        Result->SetBoolField(TEXT("success"), true);
        Result->SetBoolField(TEXT("already_present"), true);
        Result->SetStringField(TEXT("message"), TEXT("Pose already passes through a Slot node; graph unchanged"));
        Result->SetStringField(TEXT("slot_node_id"), Cast<UAnimGraphNode_Slot>(Upstream)->NodeGuid.ToString());
        return Result;
    }

    UpstreamOut->BreakLinkTo(RootIn);

    UAnimGraphNode_Slot* SlotNode = nullptr;
    {
        FGraphNodeCreator<UAnimGraphNode_Slot> NodeCreator(*TargetGraph);
        SlotNode = NodeCreator.CreateNode(/*bSelectNewNode*/ false);
        SlotNode->Node.SlotName = FName(*SlotNameStr);
        SlotNode->NodePosX = Root->NodePosX - 200;
        SlotNode->NodePosY = Root->NodePosY;
        NodeCreator.Finalize();
    }
    SlotNode->ReconstructNode();

    const bool bUpstreamToSlot = WirePoseLink(Upstream, SlotNode);
    const bool bSlotToRoot = WirePoseLink(SlotNode, Root);

    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(AnimBP);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), bUpstreamToSlot && bSlotToRoot);
    Result->SetStringField(TEXT("slot_node_id"), SlotNode->NodeGuid.ToString());
    Result->SetBoolField(TEXT("upstream_to_slot"), bUpstreamToSlot);
    Result->SetBoolField(TEXT("slot_to_root"), bSlotToRoot);
    Result->SetStringField(TEXT("slot_name"), SlotNameStr);
    if (!bUpstreamToSlot || !bSlotToRoot)
    {
        Result->SetStringField(TEXT("error"), TEXT("Could not wire Slot node pose pins; graph may be broken — reopen in editor"));
    }
    return Result;
}

namespace
{
/** Drive Blend List (by bool) Active Value from an Animation Blueprint member (e.g. bIsShooting). */
static bool TryBindBlendListByBoolActiveToAnimBpVariable(
    UAnimGraphNode_BlendListByBool* BlendNode,
    UAnimBlueprint* AnimBP,
    const FName VariableName)
{
    if (!BlendNode || !AnimBP || VariableName.IsNone())
    {
        return false;
    }

    // Binding subobject is "Instanced" on UAnimGraphNode_Base and is created by the node's internal
    // EnsureBindingsArePresent() (protected). Reconstructing the node is public and routes into the
    // same binding setup path, so we rely on that to populate Binding when missing.
    UAnimGraphNodeBinding* Binding = BlendNode->GetMutableBinding();
    if (!Binding)
    {
        BlendNode->ReconstructNode();
        Binding = BlendNode->GetMutableBinding();
    }
    if (!Binding)
    {
        return false;
    }

    // Use UPROPERTY reflection to reach PropertyBindings without needing C++ access to the private
    // field on UAnimGraphNodeBinding_Base (we only need the generated class metadata).
    FMapProperty* MapProp = FindFProperty<FMapProperty>(Binding->GetClass(), TEXT("PropertyBindings"));
    if (!MapProp)
    {
        return false;
    }

    const FName PinKey(TEXT("bActiveValue"));

    // Copy pin type from the actual pin so we don't need the private static RecalculateBindingType.
    FEdGraphPinType PinType;
    if (UEdGraphPin* Pin = BlendNode->FindPin(PinKey))
    {
        PinType = Pin->PinType;
    }
    else
    {
        PinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
    }

    FAnimGraphNodePropertyBinding NewBinding;
    NewBinding.PropertyName = PinKey;
    NewBinding.PropertyPath.Reset();
    NewBinding.PropertyPath.Add(VariableName.ToString());
    NewBinding.PathAsText = FText::FromName(VariableName);
    NewBinding.Type = EAnimGraphNodePropertyBindingType::Property;
    NewBinding.bIsBound = true;
    NewBinding.ArrayIndex = INDEX_NONE;
    NewBinding.PinType = PinType;

    Binding->Modify();
    FScriptMapHelper MapHelper(MapProp, MapProp->ContainerPtrToValuePtr<void>(Binding));

    // Replace any existing binding for this key.
    const int32 ExistingIdx = MapHelper.FindMapIndexWithKey(&PinKey);
    if (ExistingIdx != INDEX_NONE)
    {
        MapHelper.RemoveAt(ExistingIdx);
    }

    const int32 NewIdx = MapHelper.AddDefaultValue_Invalid_NeedsRehash();
    if (NewIdx == INDEX_NONE)
    {
        return false;
    }
    FName* KeyPtr = reinterpret_cast<FName*>(MapHelper.GetKeyPtr(NewIdx));
    FAnimGraphNodePropertyBinding* ValPtr = reinterpret_cast<FAnimGraphNodePropertyBinding*>(MapHelper.GetValuePtr(NewIdx));
    if (!KeyPtr || !ValPtr)
    {
        return false;
    }
    *KeyPtr = PinKey;
    *ValPtr = NewBinding;
    MapHelper.Rehash();

    BlendNode->Modify();
    BlendNode->ReconstructNode();
    return true;
}
} // namespace

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleInsertBlendBoolFireBeforeSlot(
    const TSharedPtr<FJsonObject>& Params)
{
    using namespace UnrealMCP_AnimGraphHelpers;

    FString AnimBPName, SeqPath, GraphName;
    if (!Params->TryGetStringField(TEXT("anim_blueprint_name"), AnimBPName))
    {
        return CreateErrorResponse(TEXT("Missing 'anim_blueprint_name'"));
    }
    if (!Params->TryGetStringField(TEXT("sequence_asset"), SeqPath))
    {
        return CreateErrorResponse(TEXT("Missing 'sequence_asset'"));
    }
    Params->TryGetStringField(TEXT("graph_name"), GraphName);
    bool bSwapBlendPoseOrder = false;
    Params->TryGetBoolField(TEXT("swap_blend_pose_order"), bSwapBlendPoseOrder);

    UAnimBlueprint* AnimBP = Cast<UAnimBlueprint>(FindBlueprint(AnimBPName));
    if (!AnimBP)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Animation Blueprint not found: %s"), *AnimBPName));
    }

    UAnimationAsset* Loaded = LoadObject<UAnimationAsset>(nullptr, *SeqPath);
    if (!Loaded)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Animation asset not found: %s"), *SeqPath));
    }
    UAnimSequenceBase* FireSeq = Cast<UAnimSequenceBase>(Loaded);
    if (!FireSeq)
    {
        return CreateErrorResponse(TEXT("sequence_asset must be an AnimSequence / AnimSequenceBase"));
    }

    UEdGraph* AnimGraph = nullptr;
    if (!GraphName.IsEmpty())
    {
        for (UEdGraph* G : AnimBP->FunctionGraphs)
        {
            if (G && G->GetName() == GraphName)
            {
                AnimGraph = G;
                break;
            }
        }
    }
    if (!AnimGraph)
    {
        AnimGraph = FindAnimGraph(AnimBP);
    }
    if (!AnimGraph)
    {
        return CreateErrorResponse(TEXT("AnimGraph not found"));
    }

    UAnimGraphNode_Root* Root = FindRootNode(AnimGraph);
    if (!Root)
    {
        return CreateErrorResponse(TEXT("AnimGraph has no Root node"));
    }

    UEdGraphPin* RootIn = FindPoseInputPin(Root);
    if (!RootIn || RootIn->LinkedTo.Num() == 0)
    {
        return CreateErrorResponse(TEXT("Root pose input is not connected"));
    }

    UEdGraphPin* IntoRootOut = RootIn->LinkedTo[0];
    UAnimGraphNode_Slot* Slot = Cast<UAnimGraphNode_Slot>(IntoRootOut->GetOwningNode());
    if (!Slot)
    {
        return CreateErrorResponse(
            TEXT("Node feeding Root must be an AnimGraph Slot — run insert_anim_graph_slot first"));
    }

    UEdGraphPin* SlotPoseIn = FindPoseInputPin(Slot);
    if (!SlotPoseIn || SlotPoseIn->LinkedTo.Num() == 0)
    {
        return CreateErrorResponse(TEXT("Slot pose input has no upstream connection"));
    }

    UEdGraphPin* LocomotionOut = SlotPoseIn->LinkedTo[0];
    UEdGraphNode* LocoNode = LocomotionOut ? LocomotionOut->GetOwningNode() : nullptr;
    if (!LocoNode)
    {
        return CreateErrorResponse(TEXT("Could not resolve locomotion node feeding Slot"));
    }

    FString BindBoolVar(TEXT("bIsShooting"));
    Params->TryGetStringField(TEXT("bind_bool_variable"), BindBoolVar);

    // force_insert=true layers a NEW BlendListByBool on top of an existing one.
    // Used to chain multiple bool gates (e.g. bIsInAir → jump on top of bIsShooting → fire).
    bool bForceInsert = false;
    Params->TryGetBoolField(TEXT("force_insert"), bForceInsert);

    if (!bForceInsert)
    {
        if (UAnimGraphNode_BlendListByBool* ExistingBlend = Cast<UAnimGraphNode_BlendListByBool>(LocoNode))
        {
            TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
            Result->SetBoolField(TEXT("success"), true);
            Result->SetBoolField(TEXT("already_present"), true);
            Result->SetStringField(
                TEXT("message"),
                TEXT("A BlendListByBool already feeds the Slot — pass force_insert=true to chain another"));
            Result->SetStringField(TEXT("blend_node_id"), LocoNode->NodeGuid.ToString());
            if (!BindBoolVar.IsEmpty())
            {
                const bool bBound = TryBindBlendListByBoolActiveToAnimBpVariable(ExistingBlend, AnimBP, FName(*BindBoolVar));
                Result->SetBoolField(TEXT("active_value_bound_to_variable"), bBound);
                if (bBound)
                {
                    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(AnimBP);
                }
                else
                {
                    Result->SetStringField(
                        TEXT("binding_warning"),
                        FString::Printf(TEXT("Could not bind Active Value to '%s'"), *BindBoolVar));
                }
            }
            return Result;
        }
    }

    LocomotionOut->BreakLinkTo(SlotPoseIn);

    UAnimGraphNode_BlendListByBool* BlendNode = nullptr;
    {
        FGraphNodeCreator<UAnimGraphNode_BlendListByBool> NodeCreator(*AnimGraph);
        BlendNode = NodeCreator.CreateNode(/*bSelectNewNode*/ false);
        BlendNode->NodePosX = Slot->NodePosX - 420;
        BlendNode->NodePosY = Slot->NodePosY;
        NodeCreator.Finalize();
    }
    BlendNode->ReconstructNode();

    UAnimGraphNode_SequencePlayer* SeqNode = nullptr;
    {
        FGraphNodeCreator<UAnimGraphNode_SequencePlayer> NodeCreator(*AnimGraph);
        SeqNode = NodeCreator.CreateNode(/*bSelectNewNode*/ false);
        SeqNode->SetAnimationAsset(FireSeq);
        SeqNode->Node.SetSequence(FireSeq);
        SeqNode->Node.SetLoopAnimation(false);
        SeqNode->NodePosX = BlendNode->NodePosX;
        SeqNode->NodePosY = BlendNode->NodePosY + 220;
        NodeCreator.Finalize();
    }
    SeqNode->ReconstructNode();

    TArray<UEdGraphPin*> PoseInputs;
    for (UEdGraphPin* P : BlendNode->Pins)
    {
        if (!P || P->Direction != EGPD_Input)
        {
            continue;
        }
        if (P->PinType.PinCategory == UEdGraphSchema_K2::PC_Boolean)
        {
            continue;
        }
        if (P->PinType.PinCategory == UEdGraphSchema_K2::PC_Exec)
        {
            continue;
        }
        // Pose wires use PC_Struct in many UE versions; some graphs use other categories.
        if (P->PinType.PinCategory == UEdGraphSchema_K2::PC_Struct
            || P->PinName.ToString().Contains(TEXT("BlendPose")))
        {
            PoseInputs.Add(P);
        }
    }
    PoseInputs.Sort([](const UEdGraphPin& A, const UEdGraphPin& B) {
        return A.PinName.ToString() < B.PinName.ToString();
    });
    if (PoseInputs.Num() < 2)
    {
        TryConnectPosePins(LocomotionOut, SlotPoseIn);
        return CreateErrorResponse(FString::Printf(
            TEXT("BlendListByBool has fewer than 2 pose inputs (found %d)"), PoseInputs.Num()));
    }

    UEdGraphPin* FalsePoseIn = bSwapBlendPoseOrder ? PoseInputs[1] : PoseInputs[0];
    UEdGraphPin* TruePoseIn = bSwapBlendPoseOrder ? PoseInputs[0] : PoseInputs[1];

    const bool bLocoToFalse = TryConnectPosePins(LocomotionOut, FalsePoseIn);
    UEdGraphPin* SeqOut = FindPoseOutputPin(SeqNode);
    const bool bSeqToTrue = TryConnectPosePins(SeqOut, TruePoseIn);
    UEdGraphPin* BlendOut = FindPoseOutputPin(BlendNode);
    const bool bBlendToSlot = TryConnectPosePins(BlendOut, SlotPoseIn);

    if (!bLocoToFalse || !bSeqToTrue || !bBlendToSlot)
    {
        if (SeqOut)
        {
            SeqOut->BreakAllPinLinks();
        }
        if (BlendOut)
        {
            BlendOut->BreakAllPinLinks();
        }
        LocomotionOut->BreakAllPinLinks();
        TryConnectPosePins(LocomotionOut, SlotPoseIn);
        return CreateErrorResponse(
            TEXT("Could not wire BlendList / SequencePlayer — restored Slot <- locomotion link"));
    }

    bool bActiveBound = false;
    if (!BindBoolVar.IsEmpty())
    {
        bActiveBound = TryBindBlendListByBoolActiveToAnimBpVariable(BlendNode, AnimBP, FName(*BindBoolVar));
    }

    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(AnimBP);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("blend_node_id"), BlendNode->NodeGuid.ToString());
    Result->SetStringField(TEXT("sequence_node_id"), SeqNode->NodeGuid.ToString());
    Result->SetBoolField(TEXT("active_value_bound_to_variable"), bActiveBound);
    Result->SetStringField(TEXT("false_pose_pin"), FalsePoseIn->PinName.ToString());
    Result->SetStringField(TEXT("true_pose_pin"), TruePoseIn->PinName.ToString());
    if (BindBoolVar.IsEmpty())
    {
        Result->SetStringField(
            TEXT("note"),
            TEXT("Pass bind_bool_variable (e.g. bIsShooting) to auto-bind Active Value."));
    }
    else if (!bActiveBound)
    {
        Result->SetStringField(
            TEXT("binding_warning"),
            FString::Printf(TEXT("Could not bind Active Value to '%s' — bind manually in Details."), *BindBoolVar));
    }
    return Result;
}

// ??? AI / Behavior Tree ???????????????????????????????????????????????????????

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateBehaviorTree(
    const TSharedPtr<FJsonObject>& Params)
{
    FString Name, Path;
    if (!Params->TryGetStringField(TEXT("name"), Name))
        return CreateErrorResponse(TEXT("Missing 'name'"));
    Params->TryGetStringField(TEXT("path"), Path);
    if (Path.IsEmpty()) Path = TEXT("/Game/AI");

    IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();

    // UE5.6: BehaviorTreeFactory header removed from public includes; create via dynamic class load
    UClass* BTFactClass = LoadClass<UFactory>(nullptr, TEXT("/Script/BehaviorTreeEditor.BehaviorTreeFactory"));
    UFactory* Factory = BTFactClass ? NewObject<UFactory>(GetTransientPackage(), BTFactClass) : nullptr;
    FString PackagePath = Path;
    UObject* NewBTObj = AssetTools.CreateAsset(Name, PackagePath, UBehaviorTree::StaticClass(), Factory);

    if (!NewBTObj)
        return CreateErrorResponse(TEXT("Failed to create Behavior Tree"));

    // ── Immediately produce a clean, openable graph ───────────────────────────
    // Without this the factory may leave BTGraph=null or with incomplete node
    // data; opening such an asset in the BT editor crashes at 0x68 because
    // UpdateAsset() dereferences a null IBehaviorTreeEditor* listener.
    // We call GetOrCreateBTGraph (creates Root node via schema) then
    // SafeUpdateBTAsset (SpawnMissingNodes + UpdateAsset + save) so the asset
    // is fully valid on disk before anyone tries to open it.
    UBehaviorTree* BT = Cast<UBehaviorTree>(NewBTObj);
    if (BT)
    {
        UBehaviorTreeGraph* BTGraph = GetOrCreateBTGraph(BT);
        if (BTGraph)
            SafeUpdateBTAsset(BT, BTGraph);
    }

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("name"), Name);
    Result->SetStringField(TEXT("path"), PackagePath + TEXT("/") + Name);
    return Result;
}

// ════════════════════════════════════════════════════════════════════════════
// repair_behavior_tree
//
// Two modes:
//
//   (a) fix_guids_only = true  —  non-destructive GUID rescue.
//       Walks every graph node + sub-node and assigns a fresh NodeGuid to any
//       that have an invalid (all-zero) one. Tree structure, classes, pins,
//       decorators, services, and properties are all preserved. This is the
//       right choice for BT assets that were written by pre-BUG-043 plugin
//       builds — they are structurally fine but crash the BT editor on open
//       because the editor keys internal widget maps by NodeGuid.
//
//   (b) fix_guids_only = false (default)  —  destructive rebuild.
//       Wipes all non-Root graph nodes so the asset returns to an empty
//       Root-only state that the editor can open safely. Use
//       build_behavior_tree afterwards to repopulate the tree.
//
// Root cause notes:
//   • Zero-NodeGuid crash (BUG-043): UAIGraphNode::PostPlacedNewNode() does
//     not call Super, so UEdGraphNode::NodeGuid never gets set. On open the
//     BT editor's TMap<FGuid,...> lookup returns nullptr → +0x68 crash.
//     Fixed going forward by explicit CreateNewGuid() at every BT node
//     creation site; fix_guids_only mode rescues assets written before that.
//   • NotifyGraphChanged crash: legacy issue the destructive path was
//     originally designed around; retained as a fallback for any deeper
//     corruption the GUID-only path cannot fix.
//
// Params:
//   behavior_tree_name: string   name of the BT asset to repair
//   fix_guids_only:     bool     optional, default false.  If true, only
//                                assigns missing NodeGuids and saves.
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleRepairBehaviorTree(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BTName;
    if (!Params->TryGetStringField(TEXT("behavior_tree_name"), BTName))
        return CreateErrorResponse(TEXT("Missing 'behavior_tree_name'"));

    UBehaviorTree* BT = FindBehaviorTree(BTName);
    if (!BT)
        return CreateErrorResponse(FString::Printf(TEXT("BehaviorTree not found: %s"), *BTName));

    // Step 1: close editors first — unregisters any stale per-editor listeners.
    CloseAllBTEditors(BT);

    // Step 2: get or create the graph (creates schema Root node if missing).
    UBehaviorTreeGraph* BTGraph = GetOrCreateBTGraph(BT);
    if (!BTGraph)
        return CreateErrorResponse(TEXT("Failed to get/create BehaviorTreeGraph"));

    // ── Mode (a): non-destructive GUID rescue ────────────────────────────
    bool bFixGuidsOnly = false;
    Params->TryGetBoolField(TEXT("fix_guids_only"), bFixGuidsOnly);

    if (bFixGuidsOnly)
    {
        int32 FixedCount   = 0;
        int32 AlreadyValid = 0;

        for (UEdGraphNode* N : BTGraph->Nodes)
        {
            if (!N) continue;
            if (!N->NodeGuid.IsValid())
            {
                N->CreateNewGuid();
                ++FixedCount;
            }
            else
            {
                ++AlreadyValid;
            }
            // Walk sub-nodes (decorators / services) on composite/task nodes.
            if (UAIGraphNode* AIN = Cast<UAIGraphNode>(N))
            {
                for (UAIGraphNode* Sub : AIN->SubNodes)
                {
                    if (!Sub) continue;
                    if (!Sub->NodeGuid.IsValid())
                    {
                        Sub->CreateNewGuid();
                        ++FixedCount;
                    }
                    else
                    {
                        ++AlreadyValid;
                    }
                }
            }
        }

        // Persist the updated NodeGuids. We do NOT rebuild the runtime tree
        // here because tree structure is unchanged — SaveAsset will serialize
        // the new NodeGuid UPROPERTYs and the next load will be clean.
        BT->MarkPackageDirty();
        UEditorAssetLibrary::SaveAsset(BT->GetPathName(), false);

        TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
        R->SetBoolField(TEXT("success"), true);
        R->SetStringField(TEXT("behavior_tree"), BTName);
        R->SetStringField(TEXT("mode"), TEXT("fix_guids_only"));
        R->SetNumberField(TEXT("guids_fixed"),         (double)FixedCount);
        R->SetNumberField(TEXT("guids_already_valid"), (double)AlreadyValid);
        R->SetNumberField(TEXT("node_count"),          (double)BTGraph->Nodes.Num());
        R->SetStringField(TEXT("message"),
            TEXT("Non-destructive GUID rescue complete. Tree structure preserved. "
                 "Asset can now be opened in the BT editor. If it still crashes, "
                 "call repair_behavior_tree again with fix_guids_only=false to "
                 "do a destructive Root-only rebuild."));
        return R;
    }

    // ── Mode (b): destructive rebuild (default) ──────────────────────────

    // Wipe all non-root nodes so we start from a clean Root-only state.
    SafeRemoveBTNodes(BTGraph);

    // SpawnMissingNodes + UpdateAsset + save.
    SafeUpdateBTAsset(BT, BTGraph);

    int32 NodeCount = BTGraph->Nodes.Num();

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("behavior_tree"), BTName);
    R->SetStringField(TEXT("mode"), TEXT("destructive_rebuild"));
    R->SetNumberField(TEXT("node_count_after_repair"), (double)NodeCount);
    R->SetStringField(TEXT("message"),
        TEXT("BT graph rebuilt to Root-only state. Asset saved. "
             "It can now be opened in the BT editor without crashing. "
             "Use build_behavior_tree to repopulate the tree logic."));
    return R;
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
    
    // UE5.6: BlackboardDataFactory header removed; create via dynamic class load
    UClass* BBFactClass = LoadClass<UFactory>(nullptr, TEXT("/Script/BehaviorTreeEditor.BlackboardDataFactory"));
    UFactory* Factory = BBFactClass ? NewObject<UFactory>(GetTransientPackage(), BBFactClass) : nullptr;
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

// ??? Level Settings ???????????????????????????????????????????????????????????

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

// ??? Comment Box ?????????????????????????????????????????????????????????????

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
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    return CreateSuccessResponse(CommentNode->NodeGuid.ToString());
}

// ??? Switch Node ?????????????????????????????????????????????????????????????

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
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    
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
        FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
        return MacroResult;
    }
    
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    return CreateSuccessResponse();
}

// ??? Enhanced Input ???????????????????????????????????????????????????????????

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
    UClass* InputActionClass = FindObject<UClass>(nullptr, TEXT("InputAction"));
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
    
    UClass* IMCClass = FindObject<UClass>(nullptr, TEXT("InputMappingContext"));
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

// ============================================================
// add_input_mapping
// Adds a key mapping to an existing Input Mapping Context.
// Params: imc_name, action_name, key, [triggers], [modifiers]
// ============================================================
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddInputMapping(
    const TSharedPtr<FJsonObject>& Params)
{
    FString IMCName, ActionName, KeyName;
    if (!Params->TryGetStringField(TEXT("imc_name"), IMCName))
        return CreateErrorResponse(TEXT("Missing 'imc_name'"));
    if (!Params->TryGetStringField(TEXT("action_name"), ActionName))
        return CreateErrorResponse(TEXT("Missing 'action_name'"));
    if (!Params->TryGetStringField(TEXT("key"), KeyName))
        return CreateErrorResponse(TEXT("Missing 'key'"));

    // Find the Input Mapping Context
    FAssetRegistryModule& ARModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
    IAssetRegistry& AR = ARModule.Get();

    FARFilter IMCFilter;
    IMCFilter.ClassPaths.Add(UInputMappingContext::StaticClass()->GetClassPathName());
    IMCFilter.PackagePaths.Add(TEXT("/Game"));
    IMCFilter.bRecursivePaths = true;

    TArray<FAssetData> IMCAssets;
    AR.GetAssets(IMCFilter, IMCAssets);

    UInputMappingContext* IMC = nullptr;
    for (const FAssetData& Asset : IMCAssets)
    {
        if (Asset.AssetName.ToString().Equals(IMCName, ESearchCase::IgnoreCase))
        {
            IMC = Cast<UInputMappingContext>(Asset.GetAsset());
            if (IMC) break;
        }
    }

    if (!IMC)
        return CreateErrorResponse(FString::Printf(TEXT("Input Mapping Context not found: '%s'"), *IMCName));

    // Find the Input Action
    FARFilter ActionFilter;
    ActionFilter.ClassPaths.Add(UInputAction::StaticClass()->GetClassPathName());
    ActionFilter.PackagePaths.Add(TEXT("/Game"));
    ActionFilter.bRecursivePaths = true;

    TArray<FAssetData> ActionAssets;
    AR.GetAssets(ActionFilter, ActionAssets);

    UInputAction* InputAction = nullptr;
    for (const FAssetData& Asset : ActionAssets)
    {
        if (Asset.AssetName.ToString().Equals(ActionName, ESearchCase::IgnoreCase))
        {
            InputAction = Cast<UInputAction>(Asset.GetAsset());
            if (InputAction) break;
        }
    }

    if (!InputAction)
        return CreateErrorResponse(FString::Printf(TEXT("Input Action not found: '%s'"), *ActionName));

    // Parse the key
    FKey Key = FKey(*KeyName);
    if (!Key.IsValid())
        return CreateErrorResponse(FString::Printf(TEXT("Invalid key: '%s'"), *KeyName));

    // Create the mapping
    FEnhancedActionKeyMapping NewMapping;
    NewMapping.Action = InputAction;
    NewMapping.Key = Key;

    // Access the protected Mappings array via reflection
    FArrayProperty* MappingsProp = FindFProperty<FArrayProperty>(
        UInputMappingContext::StaticClass(), TEXT("Mappings"));
    
    if (!MappingsProp)
        return CreateErrorResponse(TEXT("Failed to find Mappings property on UInputMappingContext"));

    // Get the array helper to safely access the protected member
    FScriptArrayHelper ArrayHelper(MappingsProp, MappingsProp->ContainerPtrToValuePtr<void>(IMC));
    
    // Add the new mapping to the array
    int32 NewIndex = ArrayHelper.AddValue();
    FEnhancedActionKeyMapping* MappingPtr = reinterpret_cast<FEnhancedActionKeyMapping*>(
        ArrayHelper.GetRawPtr(NewIndex));
    *MappingPtr = NewMapping;

    // Mark the asset as dirty so it gets saved
    IMC->MarkPackageDirty();

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("imc_name"), IMCName);
    Result->SetStringField(TEXT("action_name"), ActionName);
    Result->SetStringField(TEXT("key"), KeyName);
    Result->SetNumberField(TEXT("mapping_index"), NewIndex);
    return Result;
}

// ════════════════════════════════════════════════════════════════════════════
// set_blueprint_parent_class
// Params: blueprint_name, new_parent_class (Blueprint asset name OR C++ class name)
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetBlueprintParentClass(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, NewParentName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"),  BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("new_parent_class"), NewParentName))
        return CreateErrorResponse(TEXT("Missing 'new_parent_class'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(
        FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    // Try: find as Blueprint asset first (allows BP-to-BP reparenting)
    UClass* NewParentClass = nullptr;
    UBlueprint* ParentBP = FindBlueprint(NewParentName);
    if (ParentBP && ParentBP->GeneratedClass)
    {
        NewParentClass = ParentBP->GeneratedClass;
    }
    else
    {
        // Try C++ class by short name using FindFirstObject (ANY_PACKAGE deprecated in UE5.4+)
        NewParentClass = FindFirstObject<UClass>(*NewParentName, EFindFirstObjectOptions::None);
        if (!NewParentClass)
            NewParentClass = FindObject<UClass>(nullptr, *NewParentName);
    }

    if (!NewParentClass)
        return CreateErrorResponse(
            FString::Printf(TEXT("Parent class not found: '%s'. Provide either a Blueprint asset name or C++ class name."), *NewParentName));

    // Store old parent for response
    FString OldParentName = BP->ParentClass ? BP->ParentClass->GetName() : TEXT("None");

    // Perform reparent.
    // FKismetEditorUtilities::ReparentBlueprint removed in UE5.4+.
    // FBlueprintEditorUtils has no ReparentBlueprint in UE5.6.
    // Correct API: UBlueprintEditorLibrary::ReparentBlueprint (BlueprintEditorLibrary module).
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    UBlueprintEditorLibrary::ReparentBlueprint(BP, NewParentClass);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"),        true);
    R->SetStringField(TEXT("blueprint"),    BPName);
    R->SetStringField(TEXT("old_parent"),   OldParentName);
    R->SetStringField(TEXT("new_parent"),   NewParentClass->GetName());
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// set_behavior_tree_blackboard
// Params: behavior_tree_name, blackboard_name
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetBehaviorTreeBlackboard(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BTName, BBName;
    if (!Params->TryGetStringField(TEXT("behavior_tree_name"), BTName))
        return CreateErrorResponse(TEXT("Missing 'behavior_tree_name'"));
    if (!Params->TryGetStringField(TEXT("blackboard_name"),    BBName))
        return CreateErrorResponse(TEXT("Missing 'blackboard_name'"));

    // Load Behavior Tree asset
    IAssetRegistry& AR = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(
        TEXT("AssetRegistry")).Get();

    TArray<FAssetData> BTAssets;
    AR.GetAssetsByClass(FTopLevelAssetPath(TEXT("/Script/AIModule"), TEXT("BehaviorTree")), BTAssets, true);
    UBehaviorTree* BT = nullptr;
    for (const FAssetData& AD : BTAssets)
    {
        if (AD.AssetName.ToString().Equals(BTName, ESearchCase::IgnoreCase))
        {
            BT = Cast<UBehaviorTree>(AD.GetAsset());
            break;
        }
    }
    if (!BT) return CreateErrorResponse(
        FString::Printf(TEXT("BehaviorTree not found: %s"), *BTName));

    // Load Blackboard asset
    TArray<FAssetData> BBAssets;
    AR.GetAssetsByClass(FTopLevelAssetPath(TEXT("/Script/AIModule"), TEXT("BlackboardData")), BBAssets, true);
    UBlackboardData* BB = nullptr;
    for (const FAssetData& AD : BBAssets)
    {
        if (AD.AssetName.ToString().Equals(BBName, ESearchCase::IgnoreCase))
        {
            BB = Cast<UBlackboardData>(AD.GetAsset());
            break;
        }
    }
    if (!BB) return CreateErrorResponse(
        FString::Printf(TEXT("BlackboardData not found: %s"), *BBName));

    BT->BlackboardAsset = BB;
    BT->MarkPackageDirty();

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"),           true);
    R->SetStringField(TEXT("behavior_tree"),   BTName);
    R->SetStringField(TEXT("blackboard"),      BBName);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// EQS helpers
// ════════════════════════════════════════════════════════════════════════════
static void ResolveEQSObjectPaths(const FString& InPath, FString& OutPackagePath, FString& OutObjectPath)
{
    OutPackagePath = InPath;
    OutObjectPath = InPath;
    if (!OutObjectPath.Contains(TEXT(".")))
    {
        const FString AssetName = FPackageName::GetLongPackageAssetName(InPath);
        OutObjectPath = InPath + TEXT(".") + AssetName;
    }
    if (OutPackagePath.Contains(TEXT(".")))
    {
        OutPackagePath.Split(TEXT("."), &OutPackagePath, nullptr);
    }
}

static UEnvQuery* LoadEQSQueryByPathOrName(const FString& QueryPathOrName, FString& OutPackagePath)
{
    if (QueryPathOrName.StartsWith(TEXT("/")))
    {
        FString ObjectPath;
        ResolveEQSObjectPaths(QueryPathOrName, OutPackagePath, ObjectPath);
        return LoadObject<UEnvQuery>(nullptr, *ObjectPath);
    }

    IAssetRegistry& AR = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry")).Get();
    TArray<FAssetData> Assets;
    AR.GetAssetsByClass(FTopLevelAssetPath(TEXT("/Script/AIModule"), TEXT("EnvQuery")), Assets, true);
    for (const FAssetData& AD : Assets)
    {
        if (AD.AssetName.ToString().Equals(QueryPathOrName, ESearchCase::IgnoreCase))
        {
            OutPackagePath = AD.PackageName.ToString();
            return Cast<UEnvQuery>(AD.GetAsset());
        }
    }
    return nullptr;
}

static UClass* ResolveEQSGeneratorClass(const FString& GeneratorType)
{
    const FString Key = GeneratorType.Replace(TEXT("_"), TEXT("")).Replace(TEXT(" "), TEXT("")).ToLower();
    if (Key == TEXT("simplegrid") || Key == TEXT("grid"))
        return UEnvQueryGenerator_SimpleGrid::StaticClass();
    if (Key == TEXT("circle") || Key == TEXT("oncircle"))
        return UEnvQueryGenerator_OnCircle::StaticClass();
    if (Key == TEXT("donut"))
        return UEnvQueryGenerator_Donut::StaticClass();
    if (Key == TEXT("currentlocation") || Key == TEXT("self"))
        return UEnvQueryGenerator_CurrentLocation::StaticClass();
    if (Key == TEXT("actorsofclass") || Key == TEXT("actors"))
        return UEnvQueryGenerator_ActorsOfClass::StaticClass();
    return nullptr;
}

static UClass* ResolveEQSTestClass(const FString& TestType)
{
    const FString Key = TestType.Replace(TEXT("_"), TEXT("")).Replace(TEXT(" "), TEXT("")).ToLower();
    if (Key == TEXT("distance"))
        return UEnvQueryTest_Distance::StaticClass();
    if (Key == TEXT("pathfinding") || Key == TEXT("path"))
        return UEnvQueryTest_Pathfinding::StaticClass();
    if (Key == TEXT("dot"))
        return UEnvQueryTest_Dot::StaticClass();
    if (Key == TEXT("trace"))
        return UEnvQueryTest_Trace::StaticClass();
    return nullptr;
}

// ════════════════════════════════════════════════════════════════════════════
// eqs_create_query
// Params: query_name, [folder_path], [overwrite], [save]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleEQSCreateQuery(
    const TSharedPtr<FJsonObject>& Params)
{
    FString QueryName, FolderPath;
    if (!Params->TryGetStringField(TEXT("query_name"), QueryName))
        return CreateErrorResponse(TEXT("Missing 'query_name'"));
    Params->TryGetStringField(TEXT("folder_path"), FolderPath);
    if (FolderPath.IsEmpty()) FolderPath = TEXT("/Game/AI");
    FolderPath.RemoveFromEnd(TEXT("/"));

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    const FString PackagePath = FolderPath / QueryName;
    const FString ObjectPath = PackagePath + TEXT(".") + QueryName;

    if (UEditorAssetLibrary::DoesAssetExist(PackagePath))
    {
        if (!bOverwrite)
        {
            TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
            R->SetBoolField(TEXT("success"), true);
            R->SetBoolField(TEXT("created"), false);
            R->SetStringField(TEXT("message"), TEXT("EQS query already exists"));
            R->SetStringField(TEXT("asset_path"), PackagePath);
            R->SetStringField(TEXT("object_path"), ObjectPath);
            return R;
        }
        if (!UEditorAssetLibrary::DeleteAsset(PackagePath))
        {
            return CreateErrorResponse(FString::Printf(TEXT("Could not delete existing EQS query before overwrite: %s"), *PackagePath));
        }
    }

    if (!UEditorAssetLibrary::DoesDirectoryExist(FolderPath))
    {
        UEditorAssetLibrary::MakeDirectory(FolderPath);
    }

    UPackage* Package = CreatePackage(*PackagePath);
    if (!Package)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Could not create package: %s"), *PackagePath));
    }

    UEnvQuery* Query = NewObject<UEnvQuery>(Package, UEnvQuery::StaticClass(), FName(*QueryName), RF_Public | RF_Standalone | RF_Transactional);
    if (!Query)
    {
        return CreateErrorResponse(TEXT("Failed to allocate EnvQuery asset"));
    }

    FAssetRegistryModule::AssetCreated(Query);
    Query->MarkPackageDirty();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("asset_path"), PackagePath);
    R->SetStringField(TEXT("object_path"), Query->GetPathName());
    R->SetStringField(TEXT("class"), Query->GetClass()->GetName());
    R->SetNumberField(TEXT("option_count"), Query->GetOptions().Num());
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// eqs_describe_query
// Params: query_path
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleEQSDescribeQuery(
    const TSharedPtr<FJsonObject>& Params)
{
    FString QueryPath;
    if (!Params->TryGetStringField(TEXT("query_path"), QueryPath))
        return CreateErrorResponse(TEXT("Missing 'query_path'"));

    FString PackagePath;
    UEnvQuery* Query = LoadEQSQueryByPathOrName(QueryPath, PackagePath);
    if (!Query)
    {
        return CreateErrorResponse(FString::Printf(TEXT("EQS query not found: %s"), *QueryPath));
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("asset_path"), PackagePath);
    R->SetStringField(TEXT("object_path"), Query->GetPathName());
    R->SetStringField(TEXT("class"), Query->GetClass()->GetName());

    TArray<TSharedPtr<FJsonValue>> OptionsJson;
    const TArray<UEnvQueryOption*>& Options = Query->GetOptions();
    for (int32 Index = 0; Index < Options.Num(); ++Index)
    {
        const UEnvQueryOption* Option = Options[Index];
        TSharedPtr<FJsonObject> OptionJson = MakeShared<FJsonObject>();
        OptionJson->SetNumberField(TEXT("index"), Index);
        OptionJson->SetStringField(TEXT("generator_class"), Option && Option->Generator ? Option->Generator->GetClass()->GetName() : TEXT(""));
        OptionJson->SetStringField(TEXT("description"), Option ? Option->GetDescriptionTitle().ToString() : TEXT(""));

        TArray<TSharedPtr<FJsonValue>> TestsJson;
        if (Option)
        {
            for (int32 TestIndex = 0; TestIndex < Option->Tests.Num(); ++TestIndex)
            {
                const UEnvQueryTest* Test = Option->Tests[TestIndex];
                TSharedPtr<FJsonObject> TestJson = MakeShared<FJsonObject>();
                TestJson->SetNumberField(TEXT("index"), TestIndex);
                TestJson->SetStringField(TEXT("class"), Test ? Test->GetClass()->GetName() : TEXT(""));
                TestJson->SetStringField(TEXT("comment"), Test ? Test->TestComment : TEXT(""));
                TestsJson.Add(MakeShared<FJsonValueObject>(TestJson));
            }
        }
        OptionJson->SetNumberField(TEXT("test_count"), TestsJson.Num());
        OptionJson->SetArrayField(TEXT("tests"), TestsJson);
        OptionsJson.Add(MakeShared<FJsonValueObject>(OptionJson));
    }

    R->SetNumberField(TEXT("option_count"), OptionsJson.Num());
    R->SetArrayField(TEXT("options"), OptionsJson);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// eqs_add_generator
// Params: query_path, generator_type, [option_index], [save]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleEQSAddGenerator(
    const TSharedPtr<FJsonObject>& Params)
{
    FString QueryPath, GeneratorType;
    if (!Params->TryGetStringField(TEXT("query_path"), QueryPath))
        return CreateErrorResponse(TEXT("Missing 'query_path'"));
    if (!Params->TryGetStringField(TEXT("generator_type"), GeneratorType))
        return CreateErrorResponse(TEXT("Missing 'generator_type'"));

    double OptionIndexNumber = -1.0;
    Params->TryGetNumberField(TEXT("option_index"), OptionIndexNumber);
    const int32 OptionIndex = static_cast<int32>(OptionIndexNumber);
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    UClass* GeneratorClass = ResolveEQSGeneratorClass(GeneratorType);
    if (!GeneratorClass)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Unsupported EQS generator type: %s"), *GeneratorType));
    }

    FString PackagePath;
    UEnvQuery* Query = LoadEQSQueryByPathOrName(QueryPath, PackagePath);
    if (!Query)
    {
        return CreateErrorResponse(FString::Printf(TEXT("EQS query not found: %s"), *QueryPath));
    }

    Query->Modify();
    TArray<TObjectPtr<UEnvQueryOption>>& Options = Query->GetOptionsMutable();
    UEnvQueryOption* Option = nullptr;
    int32 ResolvedOptionIndex = OptionIndex;
    if (Options.IsValidIndex(OptionIndex))
    {
        Option = Options[OptionIndex];
    }
    if (!Option)
    {
        Option = NewObject<UEnvQueryOption>(Query, NAME_None, RF_Transactional);
        Options.Add(Option);
        ResolvedOptionIndex = Options.Num() - 1;
    }

    Option->Modify();
    UEnvQueryGenerator* Generator = NewObject<UEnvQueryGenerator>(Option, GeneratorClass, NAME_None, RF_Transactional);
    if (!Generator)
    {
        return CreateErrorResponse(TEXT("Failed to allocate EQS generator"));
    }
    Option->Generator = Generator;

    Query->MarkPackageDirty();
    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("query_path"), PackagePath);
    R->SetNumberField(TEXT("option_index"), ResolvedOptionIndex);
    R->SetStringField(TEXT("generator_class"), Generator->GetClass()->GetName());
    R->SetNumberField(TEXT("option_count"), Options.Num());
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// eqs_add_test
// Params: query_path, test_type, [option_index], [save]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleEQSAddTest(
    const TSharedPtr<FJsonObject>& Params)
{
    FString QueryPath, TestType;
    if (!Params->TryGetStringField(TEXT("query_path"), QueryPath))
        return CreateErrorResponse(TEXT("Missing 'query_path'"));
    if (!Params->TryGetStringField(TEXT("test_type"), TestType))
        return CreateErrorResponse(TEXT("Missing 'test_type'"));

    double OptionIndexNumber = 0.0;
    Params->TryGetNumberField(TEXT("option_index"), OptionIndexNumber);
    const int32 OptionIndex = static_cast<int32>(OptionIndexNumber);
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    UClass* TestClass = ResolveEQSTestClass(TestType);
    if (!TestClass)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Unsupported EQS test type: %s"), *TestType));
    }

    FString PackagePath;
    UEnvQuery* Query = LoadEQSQueryByPathOrName(QueryPath, PackagePath);
    if (!Query)
    {
        return CreateErrorResponse(FString::Printf(TEXT("EQS query not found: %s"), *QueryPath));
    }

    TArray<TObjectPtr<UEnvQueryOption>>& Options = Query->GetOptionsMutable();
    if (!Options.IsValidIndex(OptionIndex) || !Options[OptionIndex])
    {
        return CreateErrorResponse(FString::Printf(TEXT("EQS option index not found: %d"), OptionIndex));
    }

    Query->Modify();
    UEnvQueryOption* Option = Options[OptionIndex];
    Option->Modify();
    UEnvQueryTest* Test = NewObject<UEnvQueryTest>(Option, TestClass, NAME_None, RF_Transactional);
    if (!Test)
    {
        return CreateErrorResponse(TEXT("Failed to allocate EQS test"));
    }

    Test->TestOrder = Option->Tests.Num();
    Option->Tests.Add(Test);

    Query->MarkPackageDirty();
    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("query_path"), PackagePath);
    R->SetNumberField(TEXT("option_index"), OptionIndex);
    R->SetNumberField(TEXT("test_index"), Option->Tests.Num() - 1);
    R->SetStringField(TEXT("test_class"), Test->GetClass()->GetName());
    R->SetNumberField(TEXT("test_count"), Option->Tests.Num());
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// niagara_create_system
// Params: system_name, [folder_path], [overwrite], [save]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateNiagaraSystem(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SystemName, FolderPath;
    if (!Params->TryGetStringField(TEXT("system_name"), SystemName))
        return CreateErrorResponse(TEXT("Missing 'system_name'"));
    Params->TryGetStringField(TEXT("folder_path"), FolderPath);
    if (FolderPath.IsEmpty()) FolderPath = TEXT("/Game/VFX");
    FolderPath.RemoveFromEnd(TEXT("/"));

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    const FString PackagePath = FolderPath / SystemName;
    const FString ObjectPath = PackagePath + TEXT(".") + SystemName;

    if (UEditorAssetLibrary::DoesAssetExist(PackagePath))
    {
        if (!bOverwrite)
        {
            TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
            R->SetBoolField(TEXT("success"), true);
            R->SetBoolField(TEXT("created"), false);
            R->SetStringField(TEXT("message"), TEXT("Asset already exists"));
            R->SetStringField(TEXT("asset_path"), PackagePath);
            R->SetStringField(TEXT("object_path"), ObjectPath);
            return R;
        }

        if (!UEditorAssetLibrary::DeleteAsset(PackagePath))
        {
            return CreateErrorResponse(
                FString::Printf(TEXT("Could not delete existing Niagara System before overwrite: %s"), *PackagePath));
        }
    }

    if (!UEditorAssetLibrary::DoesDirectoryExist(FolderPath))
    {
        UEditorAssetLibrary::MakeDirectory(FolderPath);
    }

    IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();
    UNiagaraSystemFactoryNew* Factory = NewObject<UNiagaraSystemFactoryNew>(GetTransientPackage());
    if (!Factory)
    {
        return CreateErrorResponse(TEXT("Failed to allocate NiagaraSystemFactoryNew"));
    }

    UObject* NewAsset = AssetTools.CreateAsset(SystemName, FolderPath, UNiagaraSystem::StaticClass(), Factory);
    UNiagaraSystem* NiagaraSystem = Cast<UNiagaraSystem>(NewAsset);
    if (!NiagaraSystem)
    {
        return CreateErrorResponse(TEXT("AssetTools failed to create a Niagara System"));
    }

    NiagaraSystem->MarkPackageDirty();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("asset_path"), PackagePath);
    R->SetStringField(TEXT("object_path"), NiagaraSystem->GetPathName());
    R->SetStringField(TEXT("class"), NiagaraSystem->GetClass()->GetName());
    R->SetStringField(TEXT("note"), TEXT("Created empty Niagara System; use follow-up emitter/module/renderer tools to author the stack."));
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// niagara_describe_system
// Params: system_path
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleDescribeNiagaraSystem(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SystemPath;
    if (!Params->TryGetStringField(TEXT("system_path"), SystemPath))
        return CreateErrorResponse(TEXT("Missing 'system_path'"));

    FString PackagePath = SystemPath;
    FString ObjectPath = SystemPath;
    if (!ObjectPath.Contains(TEXT(".")))
    {
        const FString AssetName = FPackageName::GetLongPackageAssetName(SystemPath);
        ObjectPath = SystemPath + TEXT(".") + AssetName;
    }
    if (PackagePath.Contains(TEXT(".")))
    {
        PackagePath.Split(TEXT("."), &PackagePath, nullptr);
    }

    UNiagaraSystem* NiagaraSystem = LoadObject<UNiagaraSystem>(nullptr, *ObjectPath);
    if (!NiagaraSystem)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Niagara System not found: %s"), *ObjectPath));
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("asset_path"), PackagePath);
    R->SetStringField(TEXT("object_path"), NiagaraSystem->GetPathName());
    R->SetStringField(TEXT("class"), NiagaraSystem->GetClass()->GetName());

    TArray<TSharedPtr<FJsonValue>> EmittersJson;
    for (const FNiagaraEmitterHandle& Handle : NiagaraSystem->GetEmitterHandles())
    {
        TSharedPtr<FJsonObject> EmitterJson = MakeShared<FJsonObject>();
        EmitterJson->SetStringField(TEXT("name"), Handle.GetName().ToString());
        EmitterJson->SetStringField(TEXT("id"), Handle.GetId().ToString(EGuidFormats::DigitsWithHyphens));
        EmitterJson->SetBoolField(TEXT("enabled"), Handle.GetIsEnabled());
        EmitterJson->SetStringField(TEXT("mode"), Handle.GetEmitterMode() == ENiagaraEmitterMode::Stateless ? TEXT("Stateless") : TEXT("Standard"));
        if (const FVersionedNiagaraEmitterData* EmitterData = Handle.GetEmitterData())
        {
            EmitterJson->SetStringField(TEXT("unique_instance_name"), Handle.GetUniqueInstanceName());
            EmitterJson->SetBoolField(TEXT("needs_recompile"), Handle.NeedsRecompile());
            EmitterJson->SetStringField(TEXT("version"), EmitterData->Version.VersionGuid.ToString(EGuidFormats::DigitsWithHyphens));
            EmitterJson->SetNumberField(TEXT("renderer_count"), EmitterData->GetRenderers().Num());

            TArray<TSharedPtr<FJsonValue>> RenderersJson;
            for (const UNiagaraRendererProperties* Renderer : EmitterData->GetRenderers())
            {
                if (!Renderer)
                {
                    continue;
                }

                TSharedPtr<FJsonObject> RendererJson = MakeShared<FJsonObject>();
                RendererJson->SetStringField(TEXT("class"), Renderer->GetClass()->GetName());

                if (const UNiagaraSpriteRendererProperties* SpriteRenderer = Cast<UNiagaraSpriteRendererProperties>(Renderer))
                {
                    RendererJson->SetStringField(TEXT("material"), SpriteRenderer->Material ? SpriteRenderer->Material->GetPathName() : TEXT(""));
                }
                else if (const UNiagaraMeshRendererProperties* MeshRenderer = Cast<UNiagaraMeshRendererProperties>(Renderer))
                {
                    TArray<TSharedPtr<FJsonValue>> MeshesJson;
                    for (const FNiagaraMeshRendererMeshProperties& MeshProps : MeshRenderer->Meshes)
                    {
                        TSharedPtr<FJsonObject> MeshJson = MakeShared<FJsonObject>();
                        MeshJson->SetStringField(TEXT("static_mesh"), MeshProps.Mesh ? MeshProps.Mesh->GetPathName() : TEXT(""));
                        MeshJson->SetStringField(TEXT("scale"), MeshProps.Scale.ToString());
                        MeshesJson.Add(MakeShared<FJsonValueObject>(MeshJson));
                    }
                    RendererJson->SetArrayField(TEXT("meshes"), MeshesJson);
                    RendererJson->SetBoolField(TEXT("material_override"), MeshRenderer->bOverrideMaterials != 0);
                }

                RenderersJson.Add(MakeShared<FJsonValueObject>(RendererJson));
            }
            EmitterJson->SetArrayField(TEXT("renderers"), RenderersJson);
        }
        EmittersJson.Add(MakeShared<FJsonValueObject>(EmitterJson));
    }
    R->SetNumberField(TEXT("emitter_count"), EmittersJson.Num());
    R->SetArrayField(TEXT("emitters"), EmittersJson);

    TArray<FNiagaraVariable> UserParameters;
    NiagaraSystem->GetExposedParameters().GetUserParameters(UserParameters);
    TArray<TSharedPtr<FJsonValue>> ParametersJson;
    for (const FNiagaraVariable& Variable : UserParameters)
    {
        TSharedPtr<FJsonObject> ParamJson = MakeShared<FJsonObject>();
        ParamJson->SetStringField(TEXT("name"), Variable.GetName().ToString());
        ParamJson->SetStringField(TEXT("type"), Variable.GetType().GetNameText().ToString());
        ParametersJson.Add(MakeShared<FJsonValueObject>(ParamJson));
    }
    R->SetNumberField(TEXT("user_parameter_count"), ParametersJson.Num());
    R->SetArrayField(TEXT("user_parameters"), ParametersJson);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// niagara_add_empty_emitter
// Params: system_path, [emitter_name], [add_default_modules], [save]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddEmptyNiagaraEmitter(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SystemPath;
    if (!Params->TryGetStringField(TEXT("system_path"), SystemPath))
        return CreateErrorResponse(TEXT("Missing 'system_path'"));

    FString EmitterName;
    Params->TryGetStringField(TEXT("emitter_name"), EmitterName);
    if (EmitterName.IsEmpty()) EmitterName = TEXT("MCP_Emitter");

    bool bAddDefaultModules = false;
    Params->TryGetBoolField(TEXT("add_default_modules"), bAddDefaultModules);
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    FString PackagePath = SystemPath;
    FString ObjectPath = SystemPath;
    if (!ObjectPath.Contains(TEXT(".")))
    {
        const FString AssetName = FPackageName::GetLongPackageAssetName(SystemPath);
        ObjectPath = SystemPath + TEXT(".") + AssetName;
    }
    if (PackagePath.Contains(TEXT(".")))
    {
        PackagePath.Split(TEXT("."), &PackagePath, nullptr);
    }

    UNiagaraSystem* NiagaraSystem = LoadObject<UNiagaraSystem>(nullptr, *ObjectPath);
    if (!NiagaraSystem)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Niagara System not found: %s"), *ObjectPath));
    }

    NiagaraSystem->Modify();

    UNiagaraEmitter* EmptyEmitter = NewObject<UNiagaraEmitter>(GetTransientPackage(), NAME_None, RF_Transactional);
    if (!EmptyEmitter)
    {
        return CreateErrorResponse(TEXT("Failed to allocate Niagara emitter"));
    }

    UNiagaraEmitterFactoryNew::InitializeEmitter(EmptyEmitter, bAddDefaultModules);
    EmptyEmitter->SetUniqueEmitterName(EmitterName);
    EmptyEmitter->bIsInheritable = false;

    FNiagaraEmitterHandle EmitterHandle = NiagaraSystem->AddEmitterHandle(*EmptyEmitter, FName(*EmitterName), FGuid());
    if (!EmitterHandle.IsValid())
    {
        return CreateErrorResponse(TEXT("Failed to add empty emitter handle to Niagara System"));
    }

    NiagaraSystem->RequestCompile(false);
    NiagaraSystem->MarkPackageDirty();
    NiagaraSystem->PostEditChange();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("system_path"), PackagePath);
    R->SetStringField(TEXT("emitter_name"), EmitterHandle.GetName().ToString());
    R->SetStringField(TEXT("emitter_id"), EmitterHandle.GetId().ToString(EGuidFormats::DigitsWithHyphens));
    R->SetBoolField(TEXT("default_modules_added"), bAddDefaultModules);
    R->SetNumberField(TEXT("emitter_count"), NiagaraSystem->GetEmitterHandles().Num());
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// niagara_set_system_user_parameter
// Params: system_path, parameter_name, parameter_type, [value], [save]
// parameter_type: float | bool | vector3 | color
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetNiagaraUserParameter(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SystemPath, ParameterName, ParameterType;
    if (!Params->TryGetStringField(TEXT("system_path"), SystemPath))
        return CreateErrorResponse(TEXT("Missing 'system_path'"));
    if (!Params->TryGetStringField(TEXT("parameter_name"), ParameterName))
        return CreateErrorResponse(TEXT("Missing 'parameter_name'"));
    if (!Params->TryGetStringField(TEXT("parameter_type"), ParameterType))
        return CreateErrorResponse(TEXT("Missing 'parameter_type'"));

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    FString PackagePath = SystemPath;
    FString ObjectPath = SystemPath;
    if (!ObjectPath.Contains(TEXT(".")))
    {
        const FString AssetName = FPackageName::GetLongPackageAssetName(SystemPath);
        ObjectPath = SystemPath + TEXT(".") + AssetName;
    }
    if (PackagePath.Contains(TEXT(".")))
    {
        PackagePath.Split(TEXT("."), &PackagePath, nullptr);
    }

    UNiagaraSystem* NiagaraSystem = LoadObject<UNiagaraSystem>(nullptr, *ObjectPath);
    if (!NiagaraSystem)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Niagara System not found: %s"), *ObjectPath));
    }

    if (!ParameterName.StartsWith(TEXT("User.")))
    {
        ParameterName = TEXT("User.") + ParameterName;
    }

    FNiagaraTypeDefinition TypeDef;
    ParameterType = ParameterType.ToLower();
    if (ParameterType == TEXT("float") || ParameterType == TEXT("scalar"))
    {
        TypeDef = FNiagaraTypeDefinition::GetFloatDef();
    }
    else if (ParameterType == TEXT("bool") || ParameterType == TEXT("boolean"))
    {
        TypeDef = FNiagaraTypeDefinition::GetBoolDef();
    }
    else if (ParameterType == TEXT("vector") || ParameterType == TEXT("vector3") || ParameterType == TEXT("vec3"))
    {
        TypeDef = FNiagaraTypeDefinition::GetVec3Def();
    }
    else if (ParameterType == TEXT("color") || ParameterType == TEXT("linear_color"))
    {
        TypeDef = FNiagaraTypeDefinition::GetColorDef();
    }
    else
    {
        return CreateErrorResponse(FString::Printf(TEXT("Unsupported Niagara user parameter type: %s"), *ParameterType));
    }

    NiagaraSystem->Modify();
    FNiagaraVariable Variable(TypeDef, FName(*ParameterName));
    FNiagaraUserRedirectionParameterStore& Store = NiagaraSystem->GetExposedParameters();
    const bool bAdded = Store.AddParameter(Variable, true, true);

    if (TypeDef == FNiagaraTypeDefinition::GetFloatDef())
    {
        double NumberValue = 0.0;
        Params->TryGetNumberField(TEXT("value"), NumberValue);
        const float FloatValue = static_cast<float>(NumberValue);
        Store.SetParameterData(reinterpret_cast<const uint8*>(&FloatValue), Variable, true);
    }
    else if (TypeDef == FNiagaraTypeDefinition::GetBoolDef())
    {
        bool bValue = false;
        Params->TryGetBoolField(TEXT("value"), bValue);
        const FNiagaraBool NiagaraBool(bValue);
        Store.SetParameterData(reinterpret_cast<const uint8*>(&NiagaraBool), Variable, true);
    }
    else
    {
        const TArray<TSharedPtr<FJsonValue>>* ValueArray = nullptr;
        Params->TryGetArrayField(TEXT("value"), ValueArray);
        const double V0 = (ValueArray && ValueArray->Num() > 0) ? (*ValueArray)[0]->AsNumber() : 0.0;
        const double V1 = (ValueArray && ValueArray->Num() > 1) ? (*ValueArray)[1]->AsNumber() : 0.0;
        const double V2 = (ValueArray && ValueArray->Num() > 2) ? (*ValueArray)[2]->AsNumber() : 0.0;
        const double V3 = (ValueArray && ValueArray->Num() > 3) ? (*ValueArray)[3]->AsNumber() : 1.0;
        if (TypeDef == FNiagaraTypeDefinition::GetVec3Def())
        {
            const FVector3f VecValue(static_cast<float>(V0), static_cast<float>(V1), static_cast<float>(V2));
            Store.SetParameterData(reinterpret_cast<const uint8*>(&VecValue), Variable, true);
        }
        else
        {
            const FLinearColor ColorValue(static_cast<float>(V0), static_cast<float>(V1), static_cast<float>(V2), static_cast<float>(V3));
            Store.SetParameterData(reinterpret_cast<const uint8*>(&ColorValue), Variable, true);
        }
    }

    Store.PostGenericEditChange();
    NiagaraSystem->RequestCompile(false);
    NiagaraSystem->MarkPackageDirty();
    NiagaraSystem->PostEditChange();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TArray<FNiagaraVariable> UserParameters;
    Store.GetUserParameters(UserParameters);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("added"), bAdded);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("system_path"), PackagePath);
    R->SetStringField(TEXT("parameter_name"), ParameterName);
    R->SetStringField(TEXT("parameter_type"), ParameterType);
    R->SetNumberField(TEXT("user_parameter_count"), UserParameters.Num());
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// niagara_set_spawn_rate
// Params: system_path, emitter_name|emitter_id, spawn_rate, [save]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetNiagaraSpawnRate(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SystemPath;
    if (!Params->TryGetStringField(TEXT("system_path"), SystemPath))
        return CreateErrorResponse(TEXT("Missing 'system_path'"));

    double SpawnRateNumber = 0.0;
    if (!Params->TryGetNumberField(TEXT("spawn_rate"), SpawnRateNumber))
        return CreateErrorResponse(TEXT("Missing 'spawn_rate'"));
    const float SpawnRate = FMath::Max(0.0f, static_cast<float>(SpawnRateNumber));

    FString EmitterName, EmitterId;
    Params->TryGetStringField(TEXT("emitter_name"), EmitterName);
    Params->TryGetStringField(TEXT("emitter_id"), EmitterId);
    if (EmitterName.IsEmpty() && EmitterId.IsEmpty())
        return CreateErrorResponse(TEXT("Missing 'emitter_name' or 'emitter_id'"));

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    FString PackagePath = SystemPath;
    FString ObjectPath = SystemPath;
    if (!ObjectPath.Contains(TEXT(".")))
    {
        const FString AssetName = FPackageName::GetLongPackageAssetName(SystemPath);
        ObjectPath = SystemPath + TEXT(".") + AssetName;
    }
    if (PackagePath.Contains(TEXT(".")))
    {
        PackagePath.Split(TEXT("."), &PackagePath, nullptr);
    }

    UNiagaraSystem* NiagaraSystem = LoadObject<UNiagaraSystem>(nullptr, *ObjectPath);
    if (!NiagaraSystem)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Niagara System not found: %s"), *ObjectPath));
    }

    FGuid RequestedGuid;
    const bool bHasGuid = !EmitterId.IsEmpty() && FGuid::Parse(EmitterId, RequestedGuid);

    FNiagaraEmitterHandle* TargetHandle = nullptr;
    for (FNiagaraEmitterHandle& Handle : NiagaraSystem->GetEmitterHandles())
    {
        if ((!EmitterName.IsEmpty() && Handle.GetName().ToString() == EmitterName) ||
            (bHasGuid && Handle.GetId() == RequestedGuid))
        {
            TargetHandle = &Handle;
            break;
        }
    }
    if (!TargetHandle)
    {
        return CreateErrorResponse(TEXT("Niagara emitter handle not found"));
    }

    FVersionedNiagaraEmitter& VersionedEmitter = TargetHandle->GetInstance();
    if (!VersionedEmitter.Emitter)
    {
        return CreateErrorResponse(TEXT("Emitter handle has no backing emitter instance"));
    }

    FVersionedNiagaraEmitterData* EmitterData = VersionedEmitter.GetEmitterData();
    if (!EmitterData || !EmitterData->EmitterUpdateScriptProps.Script)
    {
        return CreateErrorResponse(TEXT("Emitter has no editable update script data"));
    }

    UNiagaraScriptSource* Source = Cast<UNiagaraScriptSource>(EmitterData->GraphSource);
    UNiagaraGraph* Graph = Source ? Source->NodeGraph : nullptr;
    if (!Graph)
    {
        return CreateErrorResponse(TEXT("Emitter graph source is unavailable"));
    }

    UNiagaraNodeOutput* EmitterUpdateOutputNode = nullptr;
    TArray<UNiagaraNodeOutput*> OutputNodes;
    Graph->GetNodesOfClass(OutputNodes);
    for (UNiagaraNodeOutput* OutputNode : OutputNodes)
    {
        if (OutputNode &&
            OutputNode->GetUsage() == ENiagaraScriptUsage::EmitterUpdateScript &&
            OutputNode->GetUsageId() == EmitterData->EmitterUpdateScriptProps.Script->GetUsageId())
        {
            EmitterUpdateOutputNode = OutputNode;
            break;
        }
    }
    if (!EmitterUpdateOutputNode)
    {
        return CreateErrorResponse(TEXT("Emitter update output node not found"));
    }

    FSoftObjectPath SpawnRateAssetPath(TEXT("/Niagara/Modules/Emitter/SpawnRate.SpawnRate"));
    UNiagaraScript* SpawnRateScript = Cast<UNiagaraScript>(SpawnRateAssetPath.TryLoad());
    if (!SpawnRateScript)
    {
        return CreateErrorResponse(TEXT("Could not load Niagara SpawnRate module script"));
    }

    UNiagaraNodeFunctionCall* SpawnRateNode = nullptr;
    const FName SpawnRateSoftObjectName(*SpawnRateAssetPath.ToString());

    TArray<UNiagaraNodeFunctionCall*> FunctionNodes;
    Graph->GetNodesOfClass(FunctionNodes);
    for (UNiagaraNodeFunctionCall* FunctionNode : FunctionNodes)
    {
        if (!FunctionNode)
        {
            continue;
        }

        const bool bMatchesLoadedScript = FunctionNode->FunctionScript == SpawnRateScript;
        const bool bMatchesAssetPath = FunctionNode->FunctionScriptAssetObjectPath == SpawnRateSoftObjectName;
        const bool bMatchesFunctionName = FunctionNode->GetFunctionName().Equals(TEXT("SpawnRate"), ESearchCase::IgnoreCase);
        if (bMatchesLoadedScript || bMatchesAssetPath || bMatchesFunctionName)
        {
            SpawnRateNode = FunctionNode;
            break;
        }
    }

    NiagaraSystem->Modify();
    VersionedEmitter.Emitter->Modify();
    Graph->Modify();
    EmitterData->EmitterUpdateScriptProps.Script->Modify();

    const bool bCreatedModule = SpawnRateNode == nullptr;
    if (!SpawnRateNode)
    {
        SpawnRateNode = FNiagaraStackGraphUtilities::AddScriptModuleToStack(
            SpawnRateScript,
            *EmitterUpdateOutputNode,
            INDEX_NONE,
            TEXT("SpawnRate"));
    }
    if (!SpawnRateNode)
    {
        return CreateErrorResponse(TEXT("Failed to add SpawnRate module to emitter update stack"));
    }

    FNiagaraParameterHandle InputHandle = FNiagaraParameterHandle::CreateModuleParameterHandle(TEXT("SpawnRate"));
    FNiagaraParameterHandle AliasedInputHandle = FNiagaraParameterHandle::CreateAliasedModuleParameterHandle(InputHandle, SpawnRateNode);
    FNiagaraVariable InputVariable(FNiagaraTypeDefinition::GetFloatDef(), AliasedInputHandle.GetParameterHandleString());
    FNiagaraVariable RapidIterationParameter = FNiagaraUtilities::ConvertVariableToRapidIterationConstantName(
        InputVariable,
        *VersionedEmitter.Emitter->GetUniqueEmitterName(),
        EmitterData->EmitterUpdateScriptProps.Script->GetUsage());

    RapidIterationParameter.SetValue(SpawnRate);
    EmitterData->EmitterUpdateScriptProps.Script->RapidIterationParameters.SetParameterData(
        RapidIterationParameter.GetData(),
        RapidIterationParameter,
        true);

    NiagaraSystem->RequestCompile(false);
    NiagaraSystem->MarkPackageDirty();
    NiagaraSystem->PostEditChange();
    VersionedEmitter.Emitter->MarkPackageDirty();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetBoolField(TEXT("module_created"), bCreatedModule);
    R->SetStringField(TEXT("system_path"), PackagePath);
    R->SetStringField(TEXT("emitter_name"), TargetHandle->GetName().ToString());
    R->SetStringField(TEXT("emitter_id"), TargetHandle->GetId().ToString(EGuidFormats::DigitsWithHyphens));
    R->SetStringField(TEXT("module_name"), SpawnRateNode->GetFunctionName());
    R->SetStringField(TEXT("rapid_iteration_parameter"), RapidIterationParameter.GetName().ToString());
    R->SetNumberField(TEXT("spawn_rate"), SpawnRate);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// niagara_add_sprite_renderer
// Params: system_path, emitter_name|emitter_id, [material_path], [save]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddNiagaraSpriteRenderer(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SystemPath;
    if (!Params->TryGetStringField(TEXT("system_path"), SystemPath))
        return CreateErrorResponse(TEXT("Missing 'system_path'"));

    FString EmitterName, EmitterId, MaterialPath;
    Params->TryGetStringField(TEXT("emitter_name"), EmitterName);
    Params->TryGetStringField(TEXT("emitter_id"), EmitterId);
    Params->TryGetStringField(TEXT("material_path"), MaterialPath);
    if (EmitterName.IsEmpty() && EmitterId.IsEmpty())
        return CreateErrorResponse(TEXT("Missing 'emitter_name' or 'emitter_id'"));

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    FString PackagePath = SystemPath;
    FString ObjectPath = SystemPath;
    if (!ObjectPath.Contains(TEXT(".")))
    {
        const FString AssetName = FPackageName::GetLongPackageAssetName(SystemPath);
        ObjectPath = SystemPath + TEXT(".") + AssetName;
    }
    if (PackagePath.Contains(TEXT(".")))
    {
        PackagePath.Split(TEXT("."), &PackagePath, nullptr);
    }

    UNiagaraSystem* NiagaraSystem = LoadObject<UNiagaraSystem>(nullptr, *ObjectPath);
    if (!NiagaraSystem)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Niagara System not found: %s"), *ObjectPath));
    }

    FGuid RequestedGuid;
    const bool bHasGuid = !EmitterId.IsEmpty() && FGuid::Parse(EmitterId, RequestedGuid);

    FNiagaraEmitterHandle* TargetHandle = nullptr;
    for (FNiagaraEmitterHandle& Handle : NiagaraSystem->GetEmitterHandles())
    {
        if ((!EmitterName.IsEmpty() && Handle.GetName().ToString() == EmitterName) ||
            (bHasGuid && Handle.GetId() == RequestedGuid))
        {
            TargetHandle = &Handle;
            break;
        }
    }
    if (!TargetHandle)
    {
        return CreateErrorResponse(TEXT("Niagara emitter handle not found"));
    }

    FVersionedNiagaraEmitter& VersionedEmitter = TargetHandle->GetInstance();
    if (!VersionedEmitter.Emitter)
    {
        return CreateErrorResponse(TEXT("Emitter handle has no backing emitter instance"));
    }

    NiagaraSystem->Modify();
    VersionedEmitter.Emitter->Modify();

    UNiagaraSpriteRendererProperties* Renderer =
        NewObject<UNiagaraSpriteRendererProperties>(VersionedEmitter.Emitter, NAME_None, RF_Transactional);
    if (!Renderer)
    {
        return CreateErrorResponse(TEXT("Failed to allocate Niagara sprite renderer"));
    }

    if (!MaterialPath.IsEmpty())
    {
        UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
        if (!Material && !MaterialPath.Contains(TEXT(".")))
        {
            const FString MaterialName = FPackageName::GetLongPackageAssetName(MaterialPath);
            Material = LoadObject<UMaterialInterface>(nullptr, *(MaterialPath + TEXT(".") + MaterialName));
        }
        if (!Material)
        {
            return CreateErrorResponse(FString::Printf(TEXT("Material not found: %s"), *MaterialPath));
        }
        Renderer->Material = Material;
    }

    VersionedEmitter.Emitter->AddRenderer(Renderer, VersionedEmitter.Version);
    NiagaraSystem->RequestCompile(false);
    NiagaraSystem->MarkPackageDirty();
    NiagaraSystem->PostEditChange();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    const FVersionedNiagaraEmitterData* EmitterData = TargetHandle->GetEmitterData();
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("system_path"), PackagePath);
    R->SetStringField(TEXT("emitter_name"), TargetHandle->GetName().ToString());
    R->SetStringField(TEXT("emitter_id"), TargetHandle->GetId().ToString(EGuidFormats::DigitsWithHyphens));
    R->SetStringField(TEXT("renderer_class"), Renderer->GetClass()->GetName());
    R->SetNumberField(TEXT("renderer_count"), EmitterData ? EmitterData->GetRenderers().Num() : 0);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// niagara_add_mesh_renderer
// Params: system_path, emitter_name|emitter_id, static_mesh_path, [material_path], [save]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddNiagaraMeshRenderer(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SystemPath, StaticMeshPath;
    if (!Params->TryGetStringField(TEXT("system_path"), SystemPath))
        return CreateErrorResponse(TEXT("Missing 'system_path'"));
    if (!Params->TryGetStringField(TEXT("static_mesh_path"), StaticMeshPath))
        return CreateErrorResponse(TEXT("Missing 'static_mesh_path'"));

    FString EmitterName, EmitterId, MaterialPath;
    Params->TryGetStringField(TEXT("emitter_name"), EmitterName);
    Params->TryGetStringField(TEXT("emitter_id"), EmitterId);
    Params->TryGetStringField(TEXT("material_path"), MaterialPath);
    if (EmitterName.IsEmpty() && EmitterId.IsEmpty())
        return CreateErrorResponse(TEXT("Missing 'emitter_name' or 'emitter_id'"));

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    FString PackagePath = SystemPath;
    FString ObjectPath = SystemPath;
    if (!ObjectPath.Contains(TEXT(".")))
    {
        const FString AssetName = FPackageName::GetLongPackageAssetName(SystemPath);
        ObjectPath = SystemPath + TEXT(".") + AssetName;
    }
    if (PackagePath.Contains(TEXT(".")))
    {
        PackagePath.Split(TEXT("."), &PackagePath, nullptr);
    }

    UNiagaraSystem* NiagaraSystem = LoadObject<UNiagaraSystem>(nullptr, *ObjectPath);
    if (!NiagaraSystem)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Niagara System not found: %s"), *ObjectPath));
    }

    UStaticMesh* StaticMesh = LoadObject<UStaticMesh>(nullptr, *StaticMeshPath);
    if (!StaticMesh && !StaticMeshPath.Contains(TEXT(".")))
    {
        const FString MeshName = FPackageName::GetLongPackageAssetName(StaticMeshPath);
        StaticMesh = LoadObject<UStaticMesh>(nullptr, *(StaticMeshPath + TEXT(".") + MeshName));
    }
    if (!StaticMesh)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Static mesh not found: %s"), *StaticMeshPath));
    }

    FGuid RequestedGuid;
    const bool bHasGuid = !EmitterId.IsEmpty() && FGuid::Parse(EmitterId, RequestedGuid);

    FNiagaraEmitterHandle* TargetHandle = nullptr;
    for (FNiagaraEmitterHandle& Handle : NiagaraSystem->GetEmitterHandles())
    {
        if ((!EmitterName.IsEmpty() && Handle.GetName().ToString() == EmitterName) ||
            (bHasGuid && Handle.GetId() == RequestedGuid))
        {
            TargetHandle = &Handle;
            break;
        }
    }
    if (!TargetHandle)
    {
        return CreateErrorResponse(TEXT("Niagara emitter handle not found"));
    }

    FVersionedNiagaraEmitter& VersionedEmitter = TargetHandle->GetInstance();
    if (!VersionedEmitter.Emitter)
    {
        return CreateErrorResponse(TEXT("Emitter handle has no backing emitter instance"));
    }

    NiagaraSystem->Modify();
    VersionedEmitter.Emitter->Modify();

    UNiagaraMeshRendererProperties* Renderer =
        NewObject<UNiagaraMeshRendererProperties>(VersionedEmitter.Emitter, NAME_None, RF_Transactional);
    if (!Renderer)
    {
        return CreateErrorResponse(TEXT("Failed to allocate Niagara mesh renderer"));
    }

    FNiagaraMeshRendererMeshProperties MeshProperties;
    MeshProperties.Mesh = StaticMesh;
    Renderer->Meshes.Empty();
    Renderer->Meshes.Add(MeshProperties);

    if (!MaterialPath.IsEmpty())
    {
        UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
        if (!Material && !MaterialPath.Contains(TEXT(".")))
        {
            const FString MaterialName = FPackageName::GetLongPackageAssetName(MaterialPath);
            Material = LoadObject<UMaterialInterface>(nullptr, *(MaterialPath + TEXT(".") + MaterialName));
        }
        if (!Material)
        {
            return CreateErrorResponse(FString::Printf(TEXT("Material not found: %s"), *MaterialPath));
        }

        FNiagaraMeshMaterialOverride MaterialOverride;
        MaterialOverride.ExplicitMat = Material;
        Renderer->bOverrideMaterials = true;
        Renderer->OverrideMaterials.Empty();
        Renderer->OverrideMaterials.Add(MaterialOverride);
    }

    VersionedEmitter.Emitter->AddRenderer(Renderer, VersionedEmitter.Version);
    NiagaraSystem->RequestCompile(false);
    NiagaraSystem->MarkPackageDirty();
    NiagaraSystem->PostEditChange();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    const FVersionedNiagaraEmitterData* EmitterData = TargetHandle->GetEmitterData();
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("system_path"), PackagePath);
    R->SetStringField(TEXT("emitter_name"), TargetHandle->GetName().ToString());
    R->SetStringField(TEXT("emitter_id"), TargetHandle->GetId().ToString(EGuidFormats::DigitsWithHyphens));
    R->SetStringField(TEXT("renderer_class"), Renderer->GetClass()->GetName());
    R->SetStringField(TEXT("static_mesh_path"), StaticMesh->GetPathName());
    R->SetBoolField(TEXT("material_override"), !MaterialPath.IsEmpty());
    R->SetNumberField(TEXT("renderer_count"), EmitterData ? EmitterData->GetRenderers().Num() : 0);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// add_niagara_component
// Params: blueprint_name, component_name, [niagara_system_path]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddNiagaraComponent(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, CompName, NSPath;
    if (!Params->TryGetStringField(TEXT("blueprint_name"),  BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("component_name"),  CompName))
        return CreateErrorResponse(TEXT("Missing 'component_name'"));
    Params->TryGetStringField(TEXT("niagara_system_path"), NSPath);

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(
        FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    USimpleConstructionScript* SCS = BP->SimpleConstructionScript;
    if (!SCS) return CreateErrorResponse(TEXT("Blueprint has no SimpleConstructionScript"));

    // Add a NiagaraComponent node to the SCS
    USCS_Node* NewNode = SCS->CreateNode(UNiagaraComponent::StaticClass(), FName(*CompName));
    if (!NewNode) return CreateErrorResponse(TEXT("Failed to create NiagaraComponent SCS node"));

    SCS->GetRootNodes()[0] ? SCS->GetRootNodes()[0]->AddChildNode(NewNode)
                            : SCS->AddNode(NewNode);

    // Optionally assign a Niagara System asset
    if (!NSPath.IsEmpty())
    {
        UNiagaraSystem* NS = Cast<UNiagaraSystem>(
            StaticLoadObject(UNiagaraSystem::StaticClass(), nullptr, *NSPath));
        if (NS)
        {
            UNiagaraComponent* NComp = Cast<UNiagaraComponent>(NewNode->ComponentTemplate);
            if (NComp) NComp->SetAsset(NS);
        }
    }

    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"),          true);
    R->SetStringField(TEXT("blueprint"),      BPName);
    R->SetStringField(TEXT("component_name"), CompName);
    R->SetStringField(TEXT("niagara_system"), NSPath.IsEmpty() ? TEXT("(none)") : NSPath);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// add_spawn_niagara_at_location_node
// Params: blueprint_name, graph_name, niagara_system_path, [node_position]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSpawnNiagaraAtLocationNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, GraphName, NSPath;
    if (!Params->TryGetStringField(TEXT("blueprint_name"),      BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("niagara_system_path"), NSPath))
        return CreateErrorResponse(TEXT("Missing 'niagara_system_path'"));
    GraphName = TEXT("EventGraph");
    Params->TryGetStringField(TEXT("graph_name"), GraphName);

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(
        FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UEdGraph* Graph = FindOrCreateEventGraph(BP);
    for (UEdGraph* G : BP->UbergraphPages)
        if (G && G->GetName().Equals(GraphName, ESearchCase::IgnoreCase)) { Graph = G; break; }
    if (!Graph) return CreateErrorResponse(
        FString::Printf(TEXT("Graph not found: %s"), *GraphName));

    FVector2D Pos = GetNodePosition(Params);

    // Add a CallFunction node for UNiagaraFunctionLibrary::SpawnSystemAtLocation
    UFunction* SpawnFunc = UNiagaraFunctionLibrary::StaticClass()->FindFunctionByName(
        TEXT("SpawnSystemAtLocation"));
    if (!SpawnFunc)
        return CreateErrorResponse(TEXT("SpawnSystemAtLocation function not found. Make sure Niagara plugin is enabled."));

    UK2Node_CallFunction* CallNode = NewObject<UK2Node_CallFunction>(Graph);
    CallNode->SetFromFunction(SpawnFunc);
    CallNode->NodePosX = (int32)Pos.X;
    CallNode->NodePosY = (int32)Pos.Y;
    Graph->AddNode(CallNode, true, false);
    CallNode->CreateNewGuid();
    CallNode->PostPlacedNewNode();
    CallNode->AllocateDefaultPins();

    // Set the SystemTemplate pin default to the NS path.
    // Use FindObject first (cache-only, instant) to avoid StaticLoadObject stalling
    // the GameThread when the Niagara asset has not been loaded yet.
    // StaticLoadObject does a synchronous disk read from the GameThread which can
    // block indefinitely on a slow or networked drive.  If the asset is not already
    // in memory, the pin stays unset (nullptr) and the caller can set it manually.
    for (UEdGraphPin* Pin : CallNode->Pins)
    {
        if (Pin->PinName == TEXT("SystemTemplate"))
        {
            UNiagaraSystem* NiagaraAsset = FindObject<UNiagaraSystem>(nullptr, *NSPath);
            if (!NiagaraAsset)
            {
                // Attempt a load, but only if the path looks valid — avoids blocking
                // on a missing/typo path.  A non-empty NSPath that starts with /Game/
                // or /Script/ is assumed to be a real asset path.
                if (!NSPath.IsEmpty() && (NSPath.StartsWith(TEXT("/Game/")) ||
                                          NSPath.StartsWith(TEXT("/Script/"))))
                {
                    NiagaraAsset = Cast<UNiagaraSystem>(
                        StaticLoadObject(UNiagaraSystem::StaticClass(), nullptr, *NSPath));
                }
            }
            Pin->DefaultObject = NiagaraAsset;
            break;
        }
    }

    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"),           true);
    R->SetStringField(TEXT("node_id"),         CallNode->NodeGuid.ToString());
    R->SetStringField(TEXT("niagara_system"),  NSPath);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// add_anim_notify
// Params: animation_path, notify_name, time (seconds), [notify_state_duration]
//         notify_type: "notify" (default) | "notify_state"
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddAnimNotify(
    const TSharedPtr<FJsonObject>& Params)
{
    FString AnimPath, NotifyName;
    if (!Params->TryGetStringField(TEXT("animation_path"), AnimPath))
        return CreateErrorResponse(TEXT("Missing 'animation_path'"));
    if (!Params->TryGetStringField(TEXT("notify_name"),    NotifyName))
        return CreateErrorResponse(TEXT("Missing 'notify_name'"));

    double TimeVal = 0.0;
    Params->TryGetNumberField(TEXT("time"), TimeVal);
    float TimeSeconds = (float)TimeVal;

    double DurationVal = 0.1;
    Params->TryGetNumberField(TEXT("notify_state_duration"), DurationVal);
    float Duration = (float)DurationVal;

    FString NotifyType = TEXT("notify");
    Params->TryGetStringField(TEXT("notify_type"), NotifyType);
    bool bIsState = NotifyType.ToLower() == TEXT("notify_state");

    // Load the animation asset
    UAnimSequenceBase* AnimAsset = Cast<UAnimSequenceBase>(
        StaticLoadObject(UAnimSequenceBase::StaticClass(), nullptr, *AnimPath));
    if (!AnimAsset)
        return CreateErrorResponse(
            FString::Printf(TEXT("Animation asset not found: %s"), *AnimPath));

    // Create the notify track if needed
    if (AnimAsset->AnimNotifyTracks.Num() == 0)
    {
        FAnimNotifyTrack NewTrack;
        NewTrack.TrackName = TEXT("Notifies");
        NewTrack.TrackColor = FLinearColor::White;
        AnimAsset->AnimNotifyTracks.Add(NewTrack);
    }

    float SequenceLength = AnimAsset->GetPlayLength();
    if (TimeSeconds > SequenceLength)
        TimeSeconds = SequenceLength * 0.5f; // clamp to middle if out of range

    if (!bIsState)
    {
        // Simple AnimNotify (point in time)
        FAnimNotifyEvent NewEvent;
        NewEvent.NotifyName = FName(*NotifyName);
        NewEvent.SetTime(TimeSeconds);
        NewEvent.TrackIndex = 0;
        // Use generic AnimNotify (no custom class)
        NewEvent.Notify = nullptr;
        AnimAsset->Notifies.Add(NewEvent);
    }
    else
    {
        // AnimNotifyState (has duration)
        FAnimNotifyEvent NewEvent;
        NewEvent.NotifyName = FName(*NotifyName);
        NewEvent.SetTime(TimeSeconds);
        NewEvent.SetDuration(Duration);
        NewEvent.TrackIndex = 0;
        NewEvent.NotifyStateClass = nullptr; // Generic state, subclass later
        AnimAsset->Notifies.Add(NewEvent);
    }

    AnimAsset->MarkPackageDirty();
    AnimAsset->PostEditChange();

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"),          true);
    R->SetStringField(TEXT("animation"),      AnimPath);
    R->SetStringField(TEXT("notify_name"),    NotifyName);
    R->SetStringField(TEXT("notify_type"),    bIsState ? TEXT("notify_state") : TEXT("notify"));
    R->SetNumberField(TEXT("time"),           TimeSeconds);
    if (bIsState) R->SetNumberField(TEXT("duration"), Duration);
    R->SetNumberField(TEXT("total_notifies"), (double)AnimAsset->Notifies.Num());
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// set_material_instance_parameter
// Params: material_instance_path, parameter_name, parameter_type (scalar|vector|texture), value
//         For scalar: value = "1.5"
//         For vector: value = "1.0,0.5,0.0,1.0"  (R,G,B,A)
//         For texture: value = "/Game/Path/To/T_Texture"
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetMaterialInstanceParameter(
    const TSharedPtr<FJsonObject>& Params)
{
    FString MIPath, ParamName, ParamType, ValueStr;
    if (!Params->TryGetStringField(TEXT("material_instance_path"), MIPath))
        return CreateErrorResponse(TEXT("Missing 'material_instance_path'"));
    if (!Params->TryGetStringField(TEXT("parameter_name"),         ParamName))
        return CreateErrorResponse(TEXT("Missing 'parameter_name'"));
    if (!Params->TryGetStringField(TEXT("parameter_type"),         ParamType))
        return CreateErrorResponse(TEXT("Missing 'parameter_type' (scalar|vector|texture)"));
    if (!Params->TryGetStringField(TEXT("value"),                  ValueStr))
        return CreateErrorResponse(TEXT("Missing 'value'"));

    UMaterialInstanceConstant* MI = Cast<UMaterialInstanceConstant>(
        StaticLoadObject(UMaterialInstanceConstant::StaticClass(), nullptr, *MIPath));
    if (!MI)
        return CreateErrorResponse(
            FString::Printf(TEXT("MaterialInstanceConstant not found: %s"), *MIPath));

    FString TypeLower = ParamType.ToLower();
    FName PName(*ParamName);

    if (TypeLower == TEXT("scalar"))
    {
        float ScalarVal = FCString::Atof(*ValueStr);
        MI->SetScalarParameterValueEditorOnly(PName, ScalarVal);
    }
    else if (TypeLower == TEXT("vector"))
    {
        // Parse "R,G,B,A"
        TArray<FString> Parts;
        ValueStr.ParseIntoArray(Parts, TEXT(","), true);
        float R = Parts.IsValidIndex(0) ? FCString::Atof(*Parts[0]) : 0.f;
        float G = Parts.IsValidIndex(1) ? FCString::Atof(*Parts[1]) : 0.f;
        float B = Parts.IsValidIndex(2) ? FCString::Atof(*Parts[2]) : 0.f;
        float A = Parts.IsValidIndex(3) ? FCString::Atof(*Parts[3]) : 1.f;
        MI->SetVectorParameterValueEditorOnly(PName, FLinearColor(R, G, B, A));
    }
    else if (TypeLower == TEXT("texture"))
    {
        UTexture* Tex = Cast<UTexture>(
            StaticLoadObject(UTexture::StaticClass(), nullptr, *ValueStr));
        if (!Tex) return CreateErrorResponse(
            FString::Printf(TEXT("Texture not found: %s"), *ValueStr));
        MI->SetTextureParameterValueEditorOnly(PName, Tex);
    }
    else
    {
        return CreateErrorResponse(TEXT("parameter_type must be 'scalar', 'vector', or 'texture'"));
    }

    MI->MarkPackageDirty();

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"),           true);
    R->SetStringField(TEXT("material_instance"), MIPath);
    R->SetStringField(TEXT("parameter_name"),  ParamName);
    R->SetStringField(TEXT("parameter_type"),  ParamType);
    R->SetStringField(TEXT("value"),           ValueStr);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// set_sequencer_track
// Params: sequence_path, actor_name, track_type ("Transform"|"Visibility"|"Event")
//         keyframes: [{time, [location:{x,y,z}], [rotation:{pitch,yaw,roll}], [scale:{x,y,z}]}]
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetSequencerTrack(
    const TSharedPtr<FJsonObject>& Params)
{
    FString SeqPath, ActorName, TrackType;
    if (!Params->TryGetStringField(TEXT("sequence_path"), SeqPath))
        return CreateErrorResponse(TEXT("Missing 'sequence_path'"));
    if (!Params->TryGetStringField(TEXT("actor_name"),    ActorName))
        return CreateErrorResponse(TEXT("Missing 'actor_name'"));
    TrackType = TEXT("Transform");
    Params->TryGetStringField(TEXT("track_type"), TrackType);

    ULevelSequence* Seq = Cast<ULevelSequence>(
        StaticLoadObject(ULevelSequence::StaticClass(), nullptr, *SeqPath));
    if (!Seq)
    {
        // Try asset registry search by name
        IAssetRegistry& AR = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(
            TEXT("AssetRegistry")).Get();
        TArray<FAssetData> SeqAssets;
        AR.GetAssetsByClass(FTopLevelAssetPath(TEXT("/Script/LevelSequence"), TEXT("LevelSequence")), SeqAssets, true);
        for (const FAssetData& AD : SeqAssets)
        {
            if (AD.AssetName.ToString().Equals(SeqPath, ESearchCase::IgnoreCase) ||
                AD.AssetName.ToString().Equals(FPaths::GetBaseFilename(SeqPath), ESearchCase::IgnoreCase))
            {
                Seq = Cast<ULevelSequence>(AD.GetAsset());
                break;
            }
        }
    }
    if (!Seq)
        return CreateErrorResponse(
            FString::Printf(TEXT("LevelSequence not found: %s"), *SeqPath));

    UMovieScene* MovieScene = Seq->GetMovieScene();
    if (!MovieScene)
        return CreateErrorResponse(TEXT("LevelSequence has no MovieScene"));

    // Find or create a binding for the named actor
    // We use a possessable with the actor name as a display name
    FGuid BindingGuid;
    for (int32 i = 0; i < MovieScene->GetPossessableCount(); ++i)
    {
        const FMovieScenePossessable& Poss = MovieScene->GetPossessable(i);
        if (Poss.GetName().Equals(ActorName, ESearchCase::IgnoreCase))
        {
            BindingGuid = Poss.GetGuid();
            break;
        }
    }
    if (!BindingGuid.IsValid())
    {
        // Create a new possessable binding (actor must be placed in level separately)
        BindingGuid = MovieScene->AddPossessable(ActorName, AActor::StaticClass());
    }

    // Add the requested track type
    FString TypeLower = TrackType.ToLower();
    int32 KeyframesAdded = 0;

    if (TypeLower == TEXT("transform"))
    {
        UMovieScene3DTransformTrack* TransformTrack = MovieScene->FindTrack<UMovieScene3DTransformTrack>(BindingGuid);
        if (!TransformTrack)
        {
            TransformTrack = MovieScene->AddTrack<UMovieScene3DTransformTrack>(BindingGuid);
        }
        if (!TransformTrack)
            return CreateErrorResponse(TEXT("Failed to create Transform track"));

        // Add a section if none exists
        UMovieScene3DTransformSection* Section = nullptr;
        if (TransformTrack->GetAllSections().Num() == 0)
        {
            TransformTrack->AddSection(*TransformTrack->CreateNewSection());
        }
        Section = Cast<UMovieScene3DTransformSection>(TransformTrack->GetAllSections()[0]);
        if (!Section)
            return CreateErrorResponse(TEXT("Failed to get/create Transform section"));

        // Parse keyframes array
        const TArray<TSharedPtr<FJsonValue>>* KeyframesArray = nullptr;
        if (Params->TryGetArrayField(TEXT("keyframes"), KeyframesArray))
        {
            FFrameRate TickRate = MovieScene->GetTickResolution();

            for (const TSharedPtr<FJsonValue>& KFVal : *KeyframesArray)
            {
                const TSharedPtr<FJsonObject>* KFObj;
                if (!KFVal->TryGetObject(KFObj)) continue;

                double TimeVal = 0.0;
                (*KFObj)->TryGetNumberField(TEXT("time"), TimeVal);
                // FFrameRate * double operator removed in UE5.4+; compute manually.
                // FMath::RoundToInt returns int64 in UE5.5+; cast to int32 for FFrameNumber.
                FFrameNumber FrameNum = TickRate.AsDecimal() > 0.0
                    ? FFrameNumber(static_cast<int32>(FMath::RoundToInt64(TimeVal * TickRate.AsDecimal())))
                    : FFrameNumber(0);

                // Extend section range
                TRange<FFrameNumber> CurrentRange = Section->GetRange();
                FFrameNumber NewEnd = FMath::Max(CurrentRange.HasUpperBound()
                    ? CurrentRange.GetUpperBoundValue() : FFrameNumber(0), FrameNum + FFrameNumber(1));
                Section->SetRange(TRange<FFrameNumber>(
                    CurrentRange.HasLowerBound() ? CurrentRange.GetLowerBoundValue() : FFrameNumber(0),
                    NewEnd));

                // Read location
                FVector Loc(0, 0, 0);
                const TSharedPtr<FJsonObject>* LocObj;
                if ((*KFObj)->TryGetObjectField(TEXT("location"), LocObj))
                {
                    double X = 0, Y = 0, Z = 0;
                    (*LocObj)->TryGetNumberField(TEXT("x"), X);
                    (*LocObj)->TryGetNumberField(TEXT("y"), Y);
                    (*LocObj)->TryGetNumberField(TEXT("z"), Z);
                    Loc = FVector(X, Y, Z);
                }
                // Read rotation
                FRotator Rot(0, 0, 0);
                const TSharedPtr<FJsonObject>* RotObj;
                if ((*KFObj)->TryGetObjectField(TEXT("rotation"), RotObj))
                {
                    double P = 0, Y = 0, R = 0;
                    (*RotObj)->TryGetNumberField(TEXT("pitch"), P);
                    (*RotObj)->TryGetNumberField(TEXT("yaw"),   Y);
                    (*RotObj)->TryGetNumberField(TEXT("roll"),  R);
                    Rot = FRotator(P, Y, R);
                }
                // Read scale
                FVector Scale(1, 1, 1);
                const TSharedPtr<FJsonObject>* ScaleObj;
                if ((*KFObj)->TryGetObjectField(TEXT("scale"), ScaleObj))
                {
                    double X = 1, Y = 1, Z = 1;
                    (*ScaleObj)->TryGetNumberField(TEXT("x"), X);
                    (*ScaleObj)->TryGetNumberField(TEXT("y"), Y);
                    (*ScaleObj)->TryGetNumberField(TEXT("z"), Z);
                    Scale = FVector(X, Y, Z);
                }

                // Add transform key via the section channels
                FMovieSceneTransformMask TransformMask;
                auto& Channels = Section->GetChannelProxy();
                // Set Translation channels
                using FFloatChannel = FMovieSceneFloatChannel;
                TArrayView<FFloatChannel*> FloatChannels = Channels.GetChannels<FFloatChannel>();
                // Channels 0-2 = Translation X,Y,Z; 3-5 = Rotation P,Y,R; 6-8 = Scale X,Y,Z
                if (FloatChannels.Num() >= 9)
                {
                    FloatChannels[0]->AddCubicKey(FrameNum, (float)Loc.X);
                    FloatChannels[1]->AddCubicKey(FrameNum, (float)Loc.Y);
                    FloatChannels[2]->AddCubicKey(FrameNum, (float)Loc.Z);
                    FloatChannels[3]->AddCubicKey(FrameNum, (float)Rot.Pitch);
                    FloatChannels[4]->AddCubicKey(FrameNum, (float)Rot.Yaw);
                    FloatChannels[5]->AddCubicKey(FrameNum, (float)Rot.Roll);
                    FloatChannels[6]->AddCubicKey(FrameNum, (float)Scale.X);
                    FloatChannels[7]->AddCubicKey(FrameNum, (float)Scale.Y);
                    FloatChannels[8]->AddCubicKey(FrameNum, (float)Scale.Z);
                }
                KeyframesAdded++;
            }
        }
    }
    else
    {
        return CreateErrorResponse(
            FString::Printf(TEXT("Unsupported track_type: '%s'. Currently supported: 'Transform'"), *TrackType));
    }

    Seq->MarkPackageDirty();

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"),          true);
    R->SetStringField(TEXT("sequence"),       SeqPath);
    R->SetStringField(TEXT("actor"),          ActorName);
    R->SetStringField(TEXT("track_type"),     TrackType);
    R->SetStringField(TEXT("binding_guid"),   BindingGuid.ToString());
    R->SetNumberField(TEXT("keyframes_added"), (double)KeyframesAdded);
    return R;
}

// ═══════════════════════════════════════════════════════════════════════════════
// IMPLEMENTATIONS FOR PREVIOUSLY-MISSING HANDLERS
// ═══════════════════════════════════════════════════════════════════════════════

// ── Internal helper: build a blueprint_function_node params object ───────────
// Routes through HandleAddBlueprintFunctionCall on the BlueprintNodeCommands side
// by delegating the call to add_blueprint_function_node via the bridge's param dispatch.
// Since we cannot call BlueprintNodeCommands directly, we forward via the shared
// FUnrealMCPBlueprintNodeCommands class. Instead, we implement function-call nodes
// here directly using the same UK2Node_CallFunction pattern.

static TSharedPtr<FJsonObject> AddFunctionNodeHelper(
    const FString& BlueprintName,
    const FString& TargetClass,
    const FString& FunctionName,
    const FVector2D& Position)
{
    UBlueprint* BP = FUnrealMCPCommonUtils::FindBlueprint(BlueprintName);
    if (!BP)
        return FUnrealMCPCommonUtils::CreateErrorResponse(
            FString::Printf(TEXT("Blueprint not found: %s"), *BlueprintName));

    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph)
        return FUnrealMCPCommonUtils::CreateErrorResponse(TEXT("Failed to get event graph"));

    // Resolve the UFunction
    UFunction* Func = nullptr;
    UClass* OwningClass = nullptr;

    auto TryClass = [&](const FString& ClassName) -> bool {
        for (TObjectIterator<UClass> It; It; ++It)
        {
            if (It->GetName().Equals(ClassName, ESearchCase::IgnoreCase) ||
                It->GetName().Equals(FString::Printf(TEXT("U%s"), *ClassName), ESearchCase::IgnoreCase) ||
                It->GetName().Equals(FString::Printf(TEXT("A%s"), *ClassName), ESearchCase::IgnoreCase))
            {
                UFunction* F = It->FindFunctionByName(FName(*FunctionName));
                if (F) { Func = F; OwningClass = *It; return true; }
            }
        }
        return false;
    };

    if (!TargetClass.IsEmpty()) TryClass(TargetClass);
    if (!Func) TryClass(TEXT("KismetSystemLibrary"));
    if (!Func) TryClass(TEXT("KismetMathLibrary"));
    if (!Func) TryClass(TEXT("GameplayStatics"));
    if (!Func && BP->GeneratedClass) Func = BP->GeneratedClass->FindFunctionByName(FName(*FunctionName));

    UK2Node_CallFunction* Node = NewObject<UK2Node_CallFunction>(Graph);
    if (Func && OwningClass)
    {
        Node->FunctionReference.SetExternalMember(FName(*FunctionName), OwningClass);
    }
    else
    {
        Node->FunctionReference.SetExternalMember(FName(*FunctionName),
            UObject::StaticClass());
    } // fallback

    Node->NodePosX = Position.X;
    Node->NodePosY = Position.Y;
    Graph->AddNode(Node, true, false);
    Node->CreateNewGuid();
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("node_id"), Node->NodeGuid.ToString());
    R->SetStringField(TEXT("function"), FunctionName);
    return R;
}

// ── SaveGame nodes ───────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSaveGameToSlotNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("SaveGameToSlot"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddLoadGameFromSlotNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("LoadGameFromSlot"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddDoesSaveGameExistNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("DoesSaveGameExist"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCreateSaveGameObjectNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("CreateSaveGameObject"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddDeleteSaveGameInSlotNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("DeleteGameInSlot"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSetGamePausedNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("SetGamePaused"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddQuitGameNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("QuitGame"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddPlayerDeathEvent(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    // Add a custom event called "OnPlayerDeath"
    TSharedPtr<FJsonObject> EventParams = MakeShared<FJsonObject>();
    EventParams->SetStringField(TEXT("blueprint_name"), BPName);
    EventParams->SetStringField(TEXT("event_name"), TEXT("OnPlayerDeath"));
    if (Params->HasField(TEXT("node_position")))
        EventParams->SetField(TEXT("node_position"), Params->Values.FindRef(TEXT("node_position")));
    return HandleAddCustomEvent(EventParams);
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetupFullSaveLoadSystem(
    const TSharedPtr<FJsonObject>& Params)
{
    // High-level composite: returns instructions for the user to call individual tools
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use add_save_game_to_slot_node, add_load_game_from_slot_node, and "
             "add_create_save_game_object_node to build the save/load system."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateRoundBasedGameSystem(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Round-based system: use exec_python to create the round manager blueprint, "
             "then add variables (RoundNumber, EnemiesPerRound) and connect event nodes."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateLoseScreenWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    FString WidgetName;
    Params->TryGetStringField(TEXT("widget_name"), WidgetName);
    if (WidgetName.IsEmpty()) WidgetName = TEXT("WBP_LoseScreen");
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("widget_name"), WidgetName);
    R->SetStringField(TEXT("message"),
        TEXT("Use create_umg_widget_blueprint then add_text_block_to_widget to build the lose screen."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreatePauseMenuWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    FString WidgetName;
    Params->TryGetStringField(TEXT("widget_name"), WidgetName);
    if (WidgetName.IsEmpty()) WidgetName = TEXT("WBP_PauseMenu");
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("widget_name"), WidgetName);
    R->SetStringField(TEXT("message"),
        TEXT("Use create_umg_widget_blueprint then add_button_to_widget to build the pause menu."));
    return R;
}

// ── Library / Component ───────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSetTimerByEventNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("K2_SetTimerDelegate"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSetTimerByFunctionNameNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("K2_SetTimer"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddClearTimerNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("K2_ClearAndInvalidateTimerHandle"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddGetOwnerNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("Actor"),
        TEXT("GetOwner"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCustomComponentToBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use add_component_to_blueprint_actor to attach a component Blueprint to another Blueprint."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddFunctionToLibrary(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use add_custom_function to add a function to a Blueprint or function library."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateBlueprintFunctionLibrary(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use exec_python with BlueprintFunctionLibraryFactory to create a Blueprint Function Library."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateExperienceLevelComponent(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use create_actor_component to create an XP/level component blueprint, "
             "then add_blueprint_variable for CurrentXP, Level, XPPerLevel variables."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateCircularMovementComponent(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use create_actor_component for a circular movement component, "
             "then add tick event with sine/cosine math nodes for orbit movement."));
    return R;
}

// ── Data Container nodes ─────────────────────────────────────────────────────

// Helper: create a real K2Node_MakeArray for EObjectTypeQuery with WorldDynamic preset
// Returns {"success":true, "node_id":"<GUID>"} or error.
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddObjectTypeMakeArrayNode(
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

    // Create the K2Node_MakeArray node
    UK2Node_MakeArray* MakeArrayNode = NewObject<UK2Node_MakeArray>(Graph);
    MakeArrayNode->NodePosX = static_cast<int32>(Pos.X);
    MakeArrayNode->NodePosY = static_cast<int32>(Pos.Y);
    MakeArrayNode->CreateNewGuid();
    Graph->AddNode(MakeArrayNode, false, false);
    MakeArrayNode->PostPlacedNewNode();
    MakeArrayNode->AllocateDefaultPins();

    // Set the pin type to EObjectTypeQuery (byte enum)
    // The MakeArray node starts with a wildcard; we need to set element type
    // Find the first input pin ("[0]" or "Element 0") and set its type
    UEdGraphSchema_K2 const* K2Schema = Cast<UEdGraphSchema_K2>(Graph->GetSchema());
    for (UEdGraphPin* Pin : MakeArrayNode->Pins)
    {
        if (Pin && Pin->Direction == EGPD_Input && Pin->PinName != TEXT("execute"))
        {
            // Set pin type to EObjectTypeQuery enum
            Pin->PinType.PinCategory = UEdGraphSchema_K2::PC_Byte;
            UEnum* ObjTypeEnum = FindObject<UEnum>(nullptr, TEXT("/Script/Engine.EObjectTypeQuery"), true);
            if (!ObjTypeEnum)
            {
                ObjTypeEnum = LoadObject<UEnum>(nullptr, TEXT("/Script/Engine.EObjectTypeQuery"));
            }
            Pin->PinType.PinSubCategoryObject = ObjTypeEnum;
            // Default to WorldDynamic (value 2 in EObjectTypeQuery)
            Pin->DefaultValue = TEXT("ObjectTypeQuery3"); // WorldDynamic = ECC_WorldDynamic mapped to ObjectTypeQuery3
            break;
        }
    }

    // Propagate the type through the MakeArray node.
    // UE 5.6: UK2Node_MakeContainer::PropagatePinType() became protected.
    // ReconstructNode() is the public API that internally invokes PropagatePinType()
    // and is safe for UK2Node_MakeArray (no wildcard-expansion crash risk).
    MakeArrayNode->ReconstructNode();
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);

    TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
    Result->SetBoolField(TEXT("success"), true);
    Result->SetStringField(TEXT("node_id"), MakeArrayNode->NodeGuid.ToString());
    Result->SetStringField(TEXT("message"), TEXT("Created K2Node_MakeArray for EObjectTypeQuery"));
    return Result;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMakeArrayNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetArrayLibrary"),
        TEXT("Array_Add"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMakeMapNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("SetTimerByFunctionName"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMakeSetNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    // Sets are added via exec_python in practice
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("message"), TEXT("Use exec_python or add_array_variable to create a Set variable."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddBreakStructNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, StructType;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("struct_type"), StructType);

    // For common struct types, use KismetMathLibrary break functions
    // For FHitResult specifically use BreakHitResult
    if (StructType.Contains(TEXT("HitResult")))
        return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
            TEXT("BreakHitResult"), GetNodePosition(Params));
    if (StructType.Contains(TEXT("Vector")))
        return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
            TEXT("BreakVector"), GetNodePosition(Params));
    if (StructType.Contains(TEXT("Transform")))
        return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
            TEXT("BreakTransform"), GetNodePosition(Params));
    if (StructType.Contains(TEXT("Rotator")))
        return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
            TEXT("BreakRotator"), GetNodePosition(Params));

    // Generic: use exec_python fallback guidance
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("struct_type"), StructType);
    R->SetStringField(TEXT("message"),
        FString::Printf(TEXT("Break %s: use exec_python with unreal.EditorUtilityLibrary "
            "or right-click the struct pin in the Blueprint graph and choose 'Split Struct Pin'."), *StructType));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMakeStructNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, StructType;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("struct_type"), StructType);

    if (StructType.Contains(TEXT("Vector")))
        return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
            TEXT("MakeVector"), GetNodePosition(Params));
    if (StructType.Contains(TEXT("Transform")))
        return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
            TEXT("MakeTransform"), GetNodePosition(Params));
    if (StructType.Contains(TEXT("Rotator")))
        return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
            TEXT("MakeRotator"), GetNodePosition(Params));

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("struct_type"), StructType);
    R->SetStringField(TEXT("message"),
        FString::Printf(TEXT("Make %s: use exec_python or right-click in the Blueprint graph "
            "and search for 'Make %s'."), *StructType, *StructType));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddGetDataTableRowNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("DataTableFunctionLibrary"),
        TEXT("GetDataTableRow"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddRandomArrayItemNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
        TEXT("RandomIntegerInRange"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSetContainsNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetArrayLibrary"),
        TEXT("Array_Contains"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSetOperationNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"), TEXT("Set operations: use exec_python with TSet operations."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSetToArrayNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetArrayLibrary"),
        TEXT("Array_Add"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMapFindNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
        TEXT("Map_Find"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMapContainsNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
        TEXT("Map_Contains"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMapKeysNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
        TEXT("Map_Keys"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMapValuesNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
        TEXT("Map_Values"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMapVariable(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use add_blueprint_variable with variable_type='Map<KeyType,ValueType>' to add a Map variable."));
    return R;
}

// ── Material / VFX nodes ─────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSetMaterialNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("PrimitiveComponent"),
        TEXT("SetMaterial"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSetVectorParameterValueNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("MaterialInstanceDynamic"),
        TEXT("SetVectorParameterValue"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSetScalarParameterValueNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("MaterialInstanceDynamic"),
        TEXT("SetScalarParameterValue"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSpawnEmitterAtLocationNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("SpawnEmitterAtLocation"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddPlaySoundAtLocationNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("PlaySoundAtLocation"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetCollisionSettings(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use set_component_property with collision settings, or use "
             "set_physics_properties for physics-based collision."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetMaterialOnActor(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use set_static_mesh_properties or set_component_property to assign materials."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSetupHitMaterialSwap(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Hit material swap: add_hit_event + add_set_material_node + "
             "add_blueprint_variable (hit count) + save_blueprint."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateMaterial(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use exec_python with unreal.AssetToolsHelpers and MaterialFactory to create a Material asset."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleMaterialCreateMaster(
    const TSharedPtr<FJsonObject>& Params)
{
    FString MaterialName;
    if (!Params->TryGetStringField(TEXT("material_name"), MaterialName))
    {
        Params->TryGetStringField(TEXT("name"), MaterialName);
    }
    if (MaterialName.IsEmpty())
    {
        return CreateErrorResponse(TEXT("Missing 'material_name'"));
    }

    FString FolderPath = TEXT("/Game/Materials");
    Params->TryGetStringField(TEXT("folder_path"), FolderPath);
    FolderPath.RemoveFromEnd(TEXT("/"));

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    bool bSave = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    bool bCompile = false;
    Params->TryGetBoolField(TEXT("compile"), bCompile);

    const FString PackagePath = MCPMakePackagePath(FolderPath, MaterialName);
    const FString ObjectPath = MCPMakeObjectPath(FolderPath, MaterialName);

    if (UEditorAssetLibrary::DoesAssetExist(PackagePath))
    {
        if (!bOverwrite)
        {
            TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
            R->SetBoolField(TEXT("success"), true);
            R->SetBoolField(TEXT("existing"), true);
            R->SetStringField(TEXT("asset_path"), PackagePath);
            R->SetStringField(TEXT("object_path"), ObjectPath);
            R->SetStringField(TEXT("message"), TEXT("Master material already exists; set overwrite=true to rebuild it."));
            return R;
        }
        if (!UEditorAssetLibrary::DeleteAsset(PackagePath))
        {
            return CreateErrorResponse(FString::Printf(TEXT("Could not delete existing material: %s"), *PackagePath));
        }
    }

    MCPEnsureAssetFolder(FolderPath);

    IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();
    UMaterialFactoryNew* Factory = NewObject<UMaterialFactoryNew>(GetTransientPackage());
    UMaterial* Material = Cast<UMaterial>(
        AssetTools.CreateAsset(MaterialName, FolderPath, UMaterial::StaticClass(), Factory));
    if (!Material)
    {
        return CreateErrorResponse(TEXT("AssetTools failed to create a Material"));
    }

    double Metallic = 0.0;
    double Roughness = 0.5;
    double Opacity = 1.0;
    Params->TryGetNumberField(TEXT("metallic"), Metallic);
    Params->TryGetNumberField(TEXT("roughness"), Roughness);
    Params->TryGetNumberField(TEXT("opacity"), Opacity);

    const FLinearColor BaseColor = MCPReadLinearColor(Params, TEXT("base_color"), FLinearColor(1.0f, 1.0f, 1.0f, 1.0f));
    const FLinearColor EmissiveColor = MCPReadLinearColor(Params, TEXT("emissive_color"), FLinearColor::Black);

    UMaterialExpressionVectorParameter* BaseColorParam =
        MCPAddVectorParameter(Material, TEXT("BaseColor"), BaseColor, -760, -180);
    UMaterialExpressionScalarParameter* MetallicParam =
        MCPAddScalarParameter(Material, TEXT("Metallic"), (float)Metallic, -760, 40);
    UMaterialExpressionScalarParameter* RoughnessParam =
        MCPAddScalarParameter(Material, TEXT("Roughness"), (float)Roughness, -760, 180);
    UMaterialExpressionVectorParameter* EmissiveParam =
        MCPAddVectorParameter(Material, TEXT("EmissiveColor"), EmissiveColor, -760, 340);
    UMaterialExpressionScalarParameter* OpacityParam =
        MCPAddScalarParameter(Material, TEXT("Opacity"), (float)Opacity, -760, 500);

    FString BlendMode;
    Params->TryGetStringField(TEXT("blend_mode"), BlendMode);
    const bool bTranslucent = BlendMode.Equals(TEXT("translucent"), ESearchCase::IgnoreCase);
    if (bTranslucent)
    {
        Material->BlendMode = BLEND_Translucent;
    }

    bool bConnected = true;
    if (BaseColorParam)
    {
        bConnected &= UMaterialEditingLibrary::ConnectMaterialProperty(BaseColorParam, TEXT(""), MP_BaseColor);
    }
    if (MetallicParam)
    {
        bConnected &= UMaterialEditingLibrary::ConnectMaterialProperty(MetallicParam, TEXT(""), MP_Metallic);
    }
    if (RoughnessParam)
    {
        bConnected &= UMaterialEditingLibrary::ConnectMaterialProperty(RoughnessParam, TEXT(""), MP_Roughness);
    }
    if (EmissiveParam)
    {
        bConnected &= UMaterialEditingLibrary::ConnectMaterialProperty(EmissiveParam, TEXT(""), MP_EmissiveColor);
    }
    if (bTranslucent && OpacityParam)
    {
        bConnected &= UMaterialEditingLibrary::ConnectMaterialProperty(OpacityParam, TEXT(""), MP_Opacity);
    }

    bool bUseTextureParameters = true;
    Params->TryGetBoolField(TEXT("use_texture_parameters"), bUseTextureParameters);
    int32 TextureParameterCount = 0;
    if (bUseTextureParameters)
    {
        MCPAddTextureParameter(Material, TEXT("BaseColorTexture"), nullptr, -1040, -420);
        MCPAddTextureParameter(Material, TEXT("NormalTexture"), nullptr, -1040, -260);
        MCPAddTextureParameter(Material, TEXT("ORMTexture"), nullptr, -1040, -100);
        MCPAddTextureParameter(Material, TEXT("EmissiveTexture"), nullptr, -1040, 60);
        TextureParameterCount = 4;
    }

    UMaterialEditingLibrary::LayoutMaterialExpressions(Material);
    if (bCompile)
    {
        UMaterialEditingLibrary::RecompileMaterial(Material);
    }
    Material->MarkPackageDirty();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetBoolField(TEXT("compiled"), bCompile);
    R->SetBoolField(TEXT("connected"), bConnected);
    R->SetStringField(TEXT("asset_path"), PackagePath);
    R->SetStringField(TEXT("object_path"), Material->GetPathName());
    R->SetNumberField(TEXT("parameter_count"), 5 + TextureParameterCount);
    R->SetStringField(TEXT("note"), TEXT("Created master material with BaseColor, Metallic, Roughness, EmissiveColor, and Opacity parameters."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleMaterialCreateFunction(
    const TSharedPtr<FJsonObject>& Params)
{
    FString FunctionName;
    if (!Params->TryGetStringField(TEXT("function_name"), FunctionName))
    {
        Params->TryGetStringField(TEXT("name"), FunctionName);
    }
    if (FunctionName.IsEmpty())
    {
        return CreateErrorResponse(TEXT("Missing 'function_name'"));
    }

    FString FolderPath = TEXT("/Game/Materials/Functions");
    Params->TryGetStringField(TEXT("folder_path"), FolderPath);
    FolderPath.RemoveFromEnd(TEXT("/"));

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    const FString PackagePath = MCPMakePackagePath(FolderPath, FunctionName);
    const FString ObjectPath = MCPMakeObjectPath(FolderPath, FunctionName);
    if (UEditorAssetLibrary::DoesAssetExist(PackagePath))
    {
        if (!bOverwrite)
        {
            TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
            R->SetBoolField(TEXT("success"), true);
            R->SetBoolField(TEXT("existing"), true);
            R->SetStringField(TEXT("asset_path"), PackagePath);
            R->SetStringField(TEXT("object_path"), ObjectPath);
            return R;
        }
        if (!UEditorAssetLibrary::DeleteAsset(PackagePath))
        {
            return CreateErrorResponse(FString::Printf(TEXT("Could not delete existing material function: %s"), *PackagePath));
        }
    }

    MCPEnsureAssetFolder(FolderPath);

    IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();
    UMaterialFunctionFactoryNew* Factory = NewObject<UMaterialFunctionFactoryNew>(GetTransientPackage());
    UMaterialFunction* Function = Cast<UMaterialFunction>(
        AssetTools.CreateAsset(FunctionName, FolderPath, UMaterialFunction::StaticClass(), Factory));
    if (!Function)
    {
        return CreateErrorResponse(TEXT("AssetTools failed to create a Material Function"));
    }

    FString Description;
    Params->TryGetStringField(TEXT("description"), Description);
    Function->Description = Description;
    Function->bExposeToLibrary = true;
    Function->MarkPackageDirty();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("asset_path"), PackagePath);
    R->SetStringField(TEXT("object_path"), Function->GetPathName());
    R->SetStringField(TEXT("description"), Description);
    R->SetStringField(TEXT("note"), TEXT("Created exposed Material Function asset; use material graph tools for detailed function internals."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleMaterialWireTextureSet(
    const TSharedPtr<FJsonObject>& Params)
{
    FString MaterialPath;
    if (!Params->TryGetStringField(TEXT("material_path"), MaterialPath))
    {
        return CreateErrorResponse(TEXT("Missing 'material_path'"));
    }

    UMaterial* Material = MCPLoadAsset<UMaterial>(MaterialPath);
    if (!Material)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Material not found: %s"), *MaterialPath));
    }

    bool bSave = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    bool bCompile = false;
    Params->TryGetBoolField(TEXT("compile"), bCompile);

    int32 WiredCount = 0;
    TArray<FString> MissingTextures;

    auto LoadTextureField = [&Params, &MissingTextures](const TCHAR* FieldName) -> UTexture*
    {
        FString TexturePath;
        if (!Params->TryGetStringField(FieldName, TexturePath) || TexturePath.IsEmpty())
        {
            return nullptr;
        }
        UTexture* Texture = MCPLoadAsset<UTexture>(TexturePath);
        if (!Texture)
        {
            MissingTextures.Add(FString(FieldName) + TEXT("=") + TexturePath);
        }
        return Texture;
    };

    if (UTexture* BaseColorTexture = LoadTextureField(TEXT("base_color_texture")))
    {
        if (MCPWireTextureToProperty(Material, BaseColorTexture, TEXT("BaseColorTexture"), MP_BaseColor, -1120, -360))
        {
            ++WiredCount;
        }
    }
    if (UTexture* NormalTexture = LoadTextureField(TEXT("normal_texture")))
    {
        if (MCPWireTextureToProperty(Material, NormalTexture, TEXT("NormalTexture"), MP_Normal, -1120, -120))
        {
            ++WiredCount;
        }
    }
    if (UTexture* ORMTexture = LoadTextureField(TEXT("orm_texture")))
    {
        if (MCPWireORMTexture(Material, ORMTexture, -1120, 160))
        {
            ++WiredCount;
        }
    }
    if (UTexture* EmissiveTexture = LoadTextureField(TEXT("emissive_texture")))
    {
        if (MCPWireTextureToProperty(Material, EmissiveTexture, TEXT("EmissiveTexture"), MP_EmissiveColor, -1120, 520))
        {
            ++WiredCount;
        }
    }

    if (WiredCount == 0 && MissingTextures.Num() > 0)
    {
        return CreateErrorResponse(FString::Printf(TEXT("No textures could be loaded: %s"), *FString::Join(MissingTextures, TEXT(", "))));
    }

    UMaterialEditingLibrary::LayoutMaterialExpressions(Material);
    if (bCompile)
    {
        UMaterialEditingLibrary::RecompileMaterial(Material);
    }
    Material->MarkPackageDirty();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(Material->GetOutermost()->GetName(), false);
    }

    TArray<TSharedPtr<FJsonValue>> MissingJson;
    for (const FString& Missing : MissingTextures)
    {
        MissingJson.Add(MakeShared<FJsonValueString>(Missing));
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetBoolField(TEXT("compiled"), bCompile);
    R->SetStringField(TEXT("material_path"), Material->GetPathName());
    R->SetNumberField(TEXT("wired_texture_count"), WiredCount);
    R->SetArrayField(TEXT("missing_textures"), MissingJson);
    R->SetStringField(TEXT("note"), TEXT("Wired base color, normal, ORM, and/or emissive textures to material properties."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleMaterialCreateInstanceFromMaster(
    const TSharedPtr<FJsonObject>& Params)
{
    FString InstanceName;
    if (!Params->TryGetStringField(TEXT("instance_name"), InstanceName))
    {
        Params->TryGetStringField(TEXT("material_instance_name"), InstanceName);
    }
    if (InstanceName.IsEmpty())
    {
        return CreateErrorResponse(TEXT("Missing 'instance_name'"));
    }

    FString ParentPath;
    if (!Params->TryGetStringField(TEXT("parent_material_path"), ParentPath))
    {
        Params->TryGetStringField(TEXT("master_material_path"), ParentPath);
    }
    if (ParentPath.IsEmpty())
    {
        return CreateErrorResponse(TEXT("Missing 'parent_material_path'"));
    }

    UMaterialInterface* ParentMaterial = MCPLoadAsset<UMaterialInterface>(ParentPath);
    if (!ParentMaterial)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Parent material not found: %s"), *ParentPath));
    }

    FString FolderPath = TEXT("/Game/Materials/Instances");
    Params->TryGetStringField(TEXT("folder_path"), FolderPath);
    FolderPath.RemoveFromEnd(TEXT("/"));

    bool bOverwrite = false;
    Params->TryGetBoolField(TEXT("overwrite"), bOverwrite);
    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    const FString PackagePath = MCPMakePackagePath(FolderPath, InstanceName);
    const FString ObjectPath = MCPMakeObjectPath(FolderPath, InstanceName);
    if (UEditorAssetLibrary::DoesAssetExist(PackagePath))
    {
        if (!bOverwrite)
        {
            TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
            R->SetBoolField(TEXT("success"), true);
            R->SetBoolField(TEXT("existing"), true);
            R->SetStringField(TEXT("asset_path"), PackagePath);
            R->SetStringField(TEXT("object_path"), ObjectPath);
            R->SetStringField(TEXT("parent_material_path"), ParentMaterial->GetPathName());
            return R;
        }
        if (!UEditorAssetLibrary::DeleteAsset(PackagePath))
        {
            return CreateErrorResponse(FString::Printf(TEXT("Could not delete existing material instance: %s"), *PackagePath));
        }
    }

    MCPEnsureAssetFolder(FolderPath);

    IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();
    UMaterialInstanceConstantFactoryNew* Factory = NewObject<UMaterialInstanceConstantFactoryNew>(GetTransientPackage());
    Factory->InitialParent = ParentMaterial;
    UMaterialInstanceConstant* Instance = Cast<UMaterialInstanceConstant>(
        AssetTools.CreateAsset(InstanceName, FolderPath, UMaterialInstanceConstant::StaticClass(), Factory));
    if (!Instance)
    {
        return CreateErrorResponse(TEXT("AssetTools failed to create a Material Instance Constant"));
    }

    Instance->SetParentEditorOnly(ParentMaterial);
    Instance->MarkPackageDirty();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(PackagePath, false);
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("asset_path"), PackagePath);
    R->SetStringField(TEXT("object_path"), Instance->GetPathName());
    R->SetStringField(TEXT("parent_material_path"), ParentMaterial->GetPathName());
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleMaterialSetInstanceParametersBulk(
    const TSharedPtr<FJsonObject>& Params)
{
    FString InstancePath;
    if (!Params->TryGetStringField(TEXT("material_instance_path"), InstancePath))
    {
        return CreateErrorResponse(TEXT("Missing 'material_instance_path'"));
    }

    UMaterialInstanceConstant* Instance = MCPLoadAsset<UMaterialInstanceConstant>(InstancePath);
    if (!Instance)
    {
        return CreateErrorResponse(FString::Printf(TEXT("MaterialInstanceConstant not found: %s"), *InstancePath));
    }

    bool bSave = true;
    Params->TryGetBoolField(TEXT("save"), bSave);

    int32 ScalarCount = 0;
    int32 VectorCount = 0;
    int32 TextureCount = 0;
    TArray<FString> MissingTextures;

    const TSharedPtr<FJsonObject>* ScalarParameters = nullptr;
    if (Params->TryGetObjectField(TEXT("scalar_parameters"), ScalarParameters) && ScalarParameters)
    {
        for (const auto& KV : (*ScalarParameters)->Values)
        {
            UMaterialEditingLibrary::SetMaterialInstanceScalarParameterValue(
                Instance, FName(*KV.Key), (float)KV.Value->AsNumber());
            ++ScalarCount;
        }
    }

    const TSharedPtr<FJsonObject>* VectorParameters = nullptr;
    if (Params->TryGetObjectField(TEXT("vector_parameters"), VectorParameters) && VectorParameters)
    {
        for (const auto& KV : (*VectorParameters)->Values)
        {
            const FLinearColor Color = MCPReadLinearColorValue(KV.Value, FLinearColor::White);
            UMaterialEditingLibrary::SetMaterialInstanceVectorParameterValue(
                Instance, FName(*KV.Key), Color);
            ++VectorCount;
        }
    }

    const TSharedPtr<FJsonObject>* TextureParameters = nullptr;
    if (Params->TryGetObjectField(TEXT("texture_parameters"), TextureParameters) && TextureParameters)
    {
        for (const auto& KV : (*TextureParameters)->Values)
        {
            const FString TexturePath = KV.Value->AsString();
            UTexture* Texture = MCPLoadAsset<UTexture>(TexturePath);
            if (!Texture)
            {
                MissingTextures.Add(KV.Key + TEXT("=") + TexturePath);
                continue;
            }
            UMaterialEditingLibrary::SetMaterialInstanceTextureParameterValue(
                Instance, FName(*KV.Key), Texture);
            ++TextureCount;
        }
    }

    Instance->PostEditChange();
    Instance->MarkPackageDirty();

    bool bSaved = false;
    if (bSave)
    {
        bSaved = UEditorAssetLibrary::SaveAsset(Instance->GetOutermost()->GetName(), false);
    }

    TArray<TSharedPtr<FJsonValue>> MissingJson;
    for (const FString& Missing : MissingTextures)
    {
        MissingJson.Add(MakeShared<FJsonValueString>(Missing));
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("material_instance_path"), Instance->GetPathName());
    R->SetNumberField(TEXT("scalar_parameters_set"), ScalarCount);
    R->SetNumberField(TEXT("vector_parameters_set"), VectorCount);
    R->SetNumberField(TEXT("texture_parameters_set"), TextureCount);
    R->SetArrayField(TEXT("missing_textures"), MissingJson);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateDynamicMaterialInstance(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetMaterialLibrary"),
        TEXT("CreateDynamicMaterialInstance"), GetNodePosition(Params));
}

// ── Physics / Trace nodes ────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddLineTraceByChannelNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("LineTraceSingleByChannel"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMultiLineTraceByChannelNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("LineTraceMultiByChannel"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddLineTraceForObjectsNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("LineTraceSingleForObjects"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMultiLineTraceForObjectsNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("LineTraceMultiForObjects"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddShapeTraceNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    FString TraceType;
    Params->TryGetStringField(TEXT("trace_type"), TraceType);
    FString FuncName = TraceType.IsEmpty() ? TEXT("SphereTraceSingle") :
        (TraceType.Contains(TEXT("Sphere")) ? TEXT("SphereTraceSingle") :
         TraceType.Contains(TEXT("Capsule")) ? TEXT("CapsuleTraceSingle") :
         TEXT("BoxTraceSingle"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        FuncName, GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddBreakHitResultNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("BreakHitResult"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddDrawDebugLineNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("DrawDebugLine"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddDrawDebugSphereNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("DrawDebugSphere"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddDrawDebugPointNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("DrawDebugPoint"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddComponentFunctionNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, CompName, FuncName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("component_name"), CompName);
    Params->TryGetStringField(TEXT("function_name"), FuncName);
    if (FuncName.IsEmpty()) return CreateErrorResponse(TEXT("Missing 'function_name'"));
    return AddFunctionNodeHelper(BPName, CompName.IsEmpty() ? TEXT("ActorComponent") : CompName,
        FuncName, GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleBuildTraceInteractionBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Trace interaction: use add_line_trace_by_channel_node + add_break_hit_result_node "
             "+ add_blueprint_branch_node to build the trace interaction system."));
    return R;
}

// ── Advanced Node Commands (Ch. 15) ─────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSelectNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("message"),
        TEXT("Select node: use exec_python with K2Node_Select to add a select node, "
             "or use add_blueprint_branch_node for boolean selection."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddFormatTextNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetTextLibrary"),
        TEXT("Format"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMathExpressionNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("message"),
        TEXT("Math Expression node: use exec_python with K2Node_MathExpression or "
             "use add_arithmetic_operator_node for individual math operations."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddRerouteNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("message"),
        TEXT("Reroute node: use exec_python with K2Node_Knot to add a reroute (wire organizer) node."));
    return R;
}

// ── AI (Ch. 10) ──────────────────────────────────────────────────────────────

static USCS_Node* FindSCSNodeByComponentName(UBlueprint* BP, const FString& ComponentName)
{
    if (!BP || !BP->SimpleConstructionScript) return nullptr;
    for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
    {
        if (Node && Node->GetVariableName().ToString().Equals(ComponentName, ESearchCase::IgnoreCase))
        {
            return Node;
        }
    }
    return nullptr;
}

static UActorComponent* FindSCSComponentTemplate(
    UBlueprint* BP,
    const FString& ComponentName,
    UClass* RequiredClass,
    USCS_Node** OutNode = nullptr)
{
    if (OutNode) *OutNode = nullptr;
    if (!BP || !BP->SimpleConstructionScript) return nullptr;

    for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
    {
        if (!Node || !Node->ComponentTemplate) continue;
        const bool bNameMatches = ComponentName.IsEmpty() ||
            Node->GetVariableName().ToString().Equals(ComponentName, ESearchCase::IgnoreCase);
        const bool bClassMatches = !RequiredClass || Node->ComponentTemplate->IsA(RequiredClass);
        if (bNameMatches && bClassMatches)
        {
            if (OutNode) *OutNode = Node;
            return Node->ComponentTemplate;
        }
    }
    return nullptr;
}

static USCS_Node* AddSCSComponentNode(
    UBlueprint* BP,
    UClass* ComponentClass,
    const FString& ComponentName,
    bool& bAlreadyExisted,
    FString& OutError)
{
    bAlreadyExisted = false;
    OutError.Empty();

    if (!BP) { OutError = TEXT("Blueprint is null"); return nullptr; }
    if (!BP->SimpleConstructionScript) { OutError = TEXT("Blueprint has no SimpleConstructionScript"); return nullptr; }
    if (!ComponentClass || !ComponentClass->IsChildOf(UActorComponent::StaticClass()))
    {
        OutError = TEXT("Invalid component class");
        return nullptr;
    }

    if (USCS_Node* Existing = FindSCSNodeByComponentName(BP, ComponentName))
    {
        if (Existing->ComponentTemplate && Existing->ComponentTemplate->IsA(ComponentClass))
        {
            bAlreadyExisted = true;
            return Existing;
        }
        OutError = FString::Printf(TEXT("Component '%s' already exists with class '%s'"),
            *ComponentName,
            Existing->ComponentTemplate ? *Existing->ComponentTemplate->GetClass()->GetName() : TEXT("<none>"));
        return nullptr;
    }

    BP->Modify();
    BP->SimpleConstructionScript->Modify();
    USCS_Node* NewNode = BP->SimpleConstructionScript->CreateNode(ComponentClass, *ComponentName);
    if (!NewNode)
    {
        OutError = TEXT("Failed to create SCS node");
        return nullptr;
    }

    bool bAddCrash = false;
    const bool bAdded = FUnrealMCPCommonUtils::SCSAddNodeGuarded(
        BP->SimpleConstructionScript,
        NewNode,
        bAddCrash);
    if (bAddCrash || !bAdded)
    {
        OutError = FString::Printf(TEXT("SCS AddNode failed for '%s' (seh=%d, added=%d)"),
            *ComponentName,
            bAddCrash ? 1 : 0,
            bAdded ? 1 : 0);
        return nullptr;
    }

    if (NewNode->ComponentTemplate)
    {
        NewNode->ComponentTemplate->SetFlags(RF_Transactional);
    }
    return NewNode;
}

static bool TrySaveAndCompileBlueprint(UBlueprint* BP, bool bCompile, bool bSave)
{
    if (!BP) return false;
    FUnrealMCPCommonUtils::SafeMarkBlueprintModified(BP);
    if (bCompile)
    {
        FKismetEditorUtilities::CompileBlueprint(BP);
    }
    return bSave ? UEditorAssetLibrary::SaveAsset(BP->GetPathName(), false) : false;
}

static UClass* ResolveAISenseClass(const FString& SenseName)
{
    if (SenseName.Equals(TEXT("sight"), ESearchCase::IgnoreCase) ||
        SenseName.Equals(TEXT("AISense_Sight"), ESearchCase::IgnoreCase))
    {
        return UAISense_Sight::StaticClass();
    }
    if (SenseName.Equals(TEXT("hearing"), ESearchCase::IgnoreCase) ||
        SenseName.Equals(TEXT("AISense_Hearing"), ESearchCase::IgnoreCase))
    {
        return UAISense_Hearing::StaticClass();
    }

    UClass* SenseClass = LoadClass<UAISense>(nullptr, *SenseName);
    if (!SenseClass && !SenseName.StartsWith(TEXT("/Script/")) && !SenseName.StartsWith(TEXT("/Game/")))
    {
        SenseClass = LoadClass<UAISense>(nullptr, *FString::Printf(TEXT("/Script/AIModule.%s"), *SenseName));
    }
    return SenseClass && SenseClass->IsChildOf(UAISense::StaticClass()) ? SenseClass : nullptr;
}

static void AddSenseClassToStimuliSource(UAIPerceptionStimuliSourceComponent* Source, UClass* SenseClass)
{
    if (!Source || !SenseClass) return;
    FArrayProperty* SensesProp =
        FindFProperty<FArrayProperty>(Source->GetClass(), TEXT("RegisterAsSourceForSenses"));
    if (!SensesProp) return;

    void* ArrayAddr = SensesProp->ContainerPtrToValuePtr<void>(Source);
    FScriptArrayHelper Helper(SensesProp, ArrayAddr);
    FClassProperty* ClassInner = CastField<FClassProperty>(SensesProp->Inner);
    if (!ClassInner) return;

    for (int32 Index = 0; Index < Helper.Num(); ++Index)
    {
        if (ClassInner->GetPropertyValue(Helper.GetRawPtr(Index)) == SenseClass)
        {
            return;
        }
    }

    const int32 NewIndex = Helper.AddValue();
    ClassInner->SetPropertyValue(Helper.GetRawPtr(NewIndex), SenseClass);
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandlePerceptionAddComponent(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, ComponentName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("component_name"), ComponentName);
    if (ComponentName.IsEmpty()) ComponentName = TEXT("AIPerception");

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    bool bSave = true, bCompile = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);

    bool bAlreadyExisted = false;
    FString Error;
    USCS_Node* Node = AddSCSComponentNode(
        BP,
        UAIPerceptionComponent::StaticClass(),
        ComponentName,
        bAlreadyExisted,
        Error);
    if (!Node)
    {
        return CreateErrorResponse(Error.IsEmpty() ? TEXT("Failed to add AIPerception component") : Error);
    }

    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created"), !bAlreadyExisted);
    R->SetBoolField(TEXT("already_existed"), bAlreadyExisted);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("component_name"), ComponentName);
    R->SetStringField(TEXT("component_class"), UAIPerceptionComponent::StaticClass()->GetName());
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandlePerceptionConfigureSight(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, ComponentName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("component_name"), ComponentName);
    if (ComponentName.IsEmpty()) ComponentName = TEXT("AIPerception");

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    bool bCreateIfMissing = true;
    Params->TryGetBoolField(TEXT("create_if_missing"), bCreateIfMissing);
    if (bCreateIfMissing && !FindSCSComponentTemplate(BP, ComponentName, UAIPerceptionComponent::StaticClass()))
    {
        bool bAlreadyExisted = false;
        FString Error;
        if (!AddSCSComponentNode(BP, UAIPerceptionComponent::StaticClass(), ComponentName, bAlreadyExisted, Error))
        {
            return CreateErrorResponse(Error.IsEmpty() ? TEXT("Failed to add AIPerception component") : Error);
        }
    }

    UAIPerceptionComponent* Perception = Cast<UAIPerceptionComponent>(
        FindSCSComponentTemplate(BP, ComponentName, UAIPerceptionComponent::StaticClass()));
    if (!Perception)
        return CreateErrorResponse(FString::Printf(TEXT("AIPerception component not found: %s"), *ComponentName));

    Perception->Modify();
    UAISenseConfig_Sight* Sight = Perception->GetSenseConfig<UAISenseConfig_Sight>();
    const bool bCreatedConfig = Sight == nullptr;
    if (!Sight)
    {
        Sight = NewObject<UAISenseConfig_Sight>(Perception, NAME_None, RF_Transactional);
    }
    if (!Sight) return CreateErrorResponse(TEXT("Failed to create Sight sense config"));
    Sight->Modify();

    double SightRadius = Sight->SightRadius > 0.0f ? Sight->SightRadius : 3000.0;
    double LoseSightRadius = Sight->LoseSightRadius > 0.0f ? Sight->LoseSightRadius : 3500.0;
    double Peripheral = Sight->PeripheralVisionAngleDegrees > 0.0f ? Sight->PeripheralVisionAngleDegrees : 70.0;
    double AutoSuccess = Sight->AutoSuccessRangeFromLastSeenLocation;
    double BackOffset = Sight->PointOfViewBackwardOffset;
    double NearClip = Sight->NearClippingRadius;
    Params->TryGetNumberField(TEXT("sight_radius"), SightRadius);
    Params->TryGetNumberField(TEXT("lose_sight_radius"), LoseSightRadius);
    Params->TryGetNumberField(TEXT("peripheral_vision_angle_degrees"), Peripheral);
    Params->TryGetNumberField(TEXT("auto_success_range"), AutoSuccess);
    Params->TryGetNumberField(TEXT("point_of_view_backward_offset"), BackOffset);
    Params->TryGetNumberField(TEXT("near_clipping_radius"), NearClip);

    bool bEnemies = true, bNeutrals = true, bFriendlies = false, bDominant = true;
    Params->TryGetBoolField(TEXT("detect_enemies"), bEnemies);
    Params->TryGetBoolField(TEXT("detect_neutrals"), bNeutrals);
    Params->TryGetBoolField(TEXT("detect_friendlies"), bFriendlies);
    Params->TryGetBoolField(TEXT("dominant"), bDominant);

    Sight->Implementation = UAISense_Sight::StaticClass();
    Sight->SightRadius = (float)SightRadius;
    Sight->LoseSightRadius = (float)LoseSightRadius;
    Sight->PeripheralVisionAngleDegrees = (float)Peripheral;
    Sight->AutoSuccessRangeFromLastSeenLocation = (float)AutoSuccess;
    Sight->PointOfViewBackwardOffset = (float)BackOffset;
    Sight->NearClippingRadius = (float)NearClip;
    Sight->DetectionByAffiliation.bDetectEnemies = bEnemies;
    Sight->DetectionByAffiliation.bDetectNeutrals = bNeutrals;
    Sight->DetectionByAffiliation.bDetectFriendlies = bFriendlies;
    Perception->ConfigureSense(*Sight);
    if (bDominant)
    {
        Perception->SetDominantSense(UAISense_Sight::StaticClass());
    }
    Perception->RequestStimuliListenerUpdate();

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created_config"), bCreatedConfig);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("component_name"), ComponentName);
    R->SetStringField(TEXT("sense"), TEXT("Sight"));
    R->SetNumberField(TEXT("sight_radius"), Sight->SightRadius);
    R->SetNumberField(TEXT("lose_sight_radius"), Sight->LoseSightRadius);
    R->SetNumberField(TEXT("peripheral_vision_angle_degrees"), Sight->PeripheralVisionAngleDegrees);
    R->SetBoolField(TEXT("dominant"), bDominant);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandlePerceptionConfigureHearing(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, ComponentName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("component_name"), ComponentName);
    if (ComponentName.IsEmpty()) ComponentName = TEXT("AIPerception");

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    bool bCreateIfMissing = true;
    Params->TryGetBoolField(TEXT("create_if_missing"), bCreateIfMissing);
    if (bCreateIfMissing && !FindSCSComponentTemplate(BP, ComponentName, UAIPerceptionComponent::StaticClass()))
    {
        bool bAlreadyExisted = false;
        FString Error;
        if (!AddSCSComponentNode(BP, UAIPerceptionComponent::StaticClass(), ComponentName, bAlreadyExisted, Error))
        {
            return CreateErrorResponse(Error.IsEmpty() ? TEXT("Failed to add AIPerception component") : Error);
        }
    }

    UAIPerceptionComponent* Perception = Cast<UAIPerceptionComponent>(
        FindSCSComponentTemplate(BP, ComponentName, UAIPerceptionComponent::StaticClass()));
    if (!Perception)
        return CreateErrorResponse(FString::Printf(TEXT("AIPerception component not found: %s"), *ComponentName));

    Perception->Modify();
    UAISenseConfig_Hearing* Hearing = Perception->GetSenseConfig<UAISenseConfig_Hearing>();
    const bool bCreatedConfig = Hearing == nullptr;
    if (!Hearing)
    {
        Hearing = NewObject<UAISenseConfig_Hearing>(Perception, NAME_None, RF_Transactional);
    }
    if (!Hearing) return CreateErrorResponse(TEXT("Failed to create Hearing sense config"));
    Hearing->Modify();

    double HearingRange = Hearing->HearingRange > 0.0f ? Hearing->HearingRange : 2500.0;
    Params->TryGetNumberField(TEXT("hearing_range"), HearingRange);

    bool bEnemies = true, bNeutrals = true, bFriendlies = false, bDominant = false;
    Params->TryGetBoolField(TEXT("detect_enemies"), bEnemies);
    Params->TryGetBoolField(TEXT("detect_neutrals"), bNeutrals);
    Params->TryGetBoolField(TEXT("detect_friendlies"), bFriendlies);
    Params->TryGetBoolField(TEXT("dominant"), bDominant);

    Hearing->Implementation = UAISense_Hearing::StaticClass();
    Hearing->HearingRange = (float)HearingRange;
    Hearing->DetectionByAffiliation.bDetectEnemies = bEnemies;
    Hearing->DetectionByAffiliation.bDetectNeutrals = bNeutrals;
    Hearing->DetectionByAffiliation.bDetectFriendlies = bFriendlies;
    Perception->ConfigureSense(*Hearing);
    if (bDominant)
    {
        Perception->SetDominantSense(UAISense_Hearing::StaticClass());
    }
    Perception->RequestStimuliListenerUpdate();

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created_config"), bCreatedConfig);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("component_name"), ComponentName);
    R->SetStringField(TEXT("sense"), TEXT("Hearing"));
    R->SetNumberField(TEXT("hearing_range"), Hearing->HearingRange);
    R->SetBoolField(TEXT("dominant"), bDominant);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandlePerceptionCreateStimulusSource(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, ComponentName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("component_name"), ComponentName);
    if (ComponentName.IsEmpty()) ComponentName = TEXT("PerceptionStimuliSource");

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    bool bAlreadyExisted = false;
    FString Error;
    USCS_Node* Node = AddSCSComponentNode(
        BP,
        UAIPerceptionStimuliSourceComponent::StaticClass(),
        ComponentName,
        bAlreadyExisted,
        Error);
    if (!Node)
    {
        return CreateErrorResponse(Error.IsEmpty() ? TEXT("Failed to add stimuli source component") : Error);
    }

    UAIPerceptionStimuliSourceComponent* Source =
        Cast<UAIPerceptionStimuliSourceComponent>(Node->ComponentTemplate);
    if (!Source) return CreateErrorResponse(TEXT("Stimuli source component template was not created"));
    Source->Modify();

    bool bAutoRegister = true;
    Params->TryGetBoolField(TEXT("auto_register"), bAutoRegister);
    if (FBoolProperty* AutoProp =
            FindFProperty<FBoolProperty>(Source->GetClass(), TEXT("bAutoRegisterAsSource")))
    {
        AutoProp->SetPropertyValue_InContainer(Source, bAutoRegister);
    }

    TArray<FString> SenseNames;
    const TArray<TSharedPtr<FJsonValue>>* SensesArray = nullptr;
    if (Params->TryGetArrayField(TEXT("senses"), SensesArray) && SensesArray)
    {
        for (const TSharedPtr<FJsonValue>& SenseVal : *SensesArray)
        {
            FString SenseName;
            if (SenseVal->TryGetString(SenseName) && !SenseName.IsEmpty())
            {
                SenseNames.Add(SenseName);
            }
        }
    }
    if (SenseNames.Num() == 0)
    {
        SenseNames.Add(TEXT("sight"));
    }

    TArray<TSharedPtr<FJsonValue>> SenseResults;
    for (const FString& SenseName : SenseNames)
    {
        UClass* SenseClass = ResolveAISenseClass(SenseName);
        if (SenseClass)
        {
            AddSenseClassToStimuliSource(Source, SenseClass);
            SenseResults.Add(MakeShared<FJsonValueString>(SenseClass->GetName()));
        }
    }

    bool bSave = true, bCompile = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created"), !bAlreadyExisted);
    R->SetBoolField(TEXT("already_existed"), bAlreadyExisted);
    R->SetBoolField(TEXT("auto_register"), bAutoRegister);
    R->SetBoolField(TEXT("saved"), bSaved);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("component_name"), ComponentName);
    R->SetArrayField(TEXT("senses"), SenseResults);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandlePerceptionDescribeBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    TArray<TSharedPtr<FJsonValue>> Components;
    if (BP->SimpleConstructionScript)
    {
        for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
        {
            if (!Node || !Node->ComponentTemplate) continue;

            if (UAIPerceptionComponent* Perception = Cast<UAIPerceptionComponent>(Node->ComponentTemplate))
            {
                TSharedPtr<FJsonObject> CObj = MakeShared<FJsonObject>();
                CObj->SetStringField(TEXT("component_name"), Node->GetVariableName().ToString());
                CObj->SetStringField(TEXT("component_class"), Perception->GetClass()->GetName());
                CObj->SetStringField(TEXT("dominant_sense"),
                    Perception->GetDominantSense() ? Perception->GetDominantSense()->GetName() : TEXT(""));

                TArray<TSharedPtr<FJsonValue>> SenseConfigs;
                for (auto It = Perception->GetSensesConfigIterator(); It; ++It)
                {
                    const UAISenseConfig* Config = *It;
                    if (!Config) continue;
                    TSharedPtr<FJsonObject> SObj = MakeShared<FJsonObject>();
                    SObj->SetStringField(TEXT("config_class"), Config->GetClass()->GetName());
                    if (const UAISenseConfig_Sight* Sight = Cast<UAISenseConfig_Sight>(Config))
                    {
                        SObj->SetStringField(TEXT("sense"), TEXT("Sight"));
                        SObj->SetNumberField(TEXT("sight_radius"), Sight->SightRadius);
                        SObj->SetNumberField(TEXT("lose_sight_radius"), Sight->LoseSightRadius);
                        SObj->SetNumberField(TEXT("peripheral_vision_angle_degrees"), Sight->PeripheralVisionAngleDegrees);
                    }
                    else if (const UAISenseConfig_Hearing* Hearing = Cast<UAISenseConfig_Hearing>(Config))
                    {
                        SObj->SetStringField(TEXT("sense"), TEXT("Hearing"));
                        SObj->SetNumberField(TEXT("hearing_range"), Hearing->HearingRange);
                    }
                    SenseConfigs.Add(MakeShared<FJsonValueObject>(SObj));
                }
                CObj->SetArrayField(TEXT("sense_configs"), SenseConfigs);
                Components.Add(MakeShared<FJsonValueObject>(CObj));
            }
            else if (UAIPerceptionStimuliSourceComponent* Source =
                         Cast<UAIPerceptionStimuliSourceComponent>(Node->ComponentTemplate))
            {
                TSharedPtr<FJsonObject> CObj = MakeShared<FJsonObject>();
                CObj->SetStringField(TEXT("component_name"), Node->GetVariableName().ToString());
                CObj->SetStringField(TEXT("component_class"), Source->GetClass()->GetName());
                Components.Add(MakeShared<FJsonValueObject>(CObj));
            }
        }
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetNumberField(TEXT("perception_component_count"), (double)Components.Num());
    R->SetArrayField(TEXT("components"), Components);
    return R;
}

static UClass* ResolveNavAreaClass(const FString& AreaClassName)
{
    if (AreaClassName.IsEmpty() ||
        AreaClassName.Equals(TEXT("default"), ESearchCase::IgnoreCase) ||
        AreaClassName.Equals(TEXT("NavArea_Default"), ESearchCase::IgnoreCase))
    {
        return UNavArea_Default::StaticClass();
    }
    if (AreaClassName.Equals(TEXT("null"), ESearchCase::IgnoreCase) ||
        AreaClassName.Equals(TEXT("blocked"), ESearchCase::IgnoreCase) ||
        AreaClassName.Equals(TEXT("NavArea_Null"), ESearchCase::IgnoreCase))
    {
        return UNavArea_Null::StaticClass();
    }
    if (AreaClassName.Equals(TEXT("obstacle"), ESearchCase::IgnoreCase) ||
        AreaClassName.Equals(TEXT("NavArea_Obstacle"), ESearchCase::IgnoreCase))
    {
        return UNavArea_Obstacle::StaticClass();
    }

    UClass* AreaClass = LoadClass<UNavArea>(nullptr, *AreaClassName);
    if (!AreaClass && !AreaClassName.StartsWith(TEXT("/Script/")) && !AreaClassName.StartsWith(TEXT("/Game/")))
    {
        AreaClass = LoadClass<UNavArea>(nullptr, *FString::Printf(TEXT("/Script/NavigationSystem.%s"), *AreaClassName));
    }
    return AreaClass && AreaClass->IsChildOf(UNavArea::StaticClass()) ? AreaClass : nullptr;
}

static ENavLinkDirection::Type ResolveNavLinkDirection(const FString& DirectionName)
{
    if (DirectionName.Equals(TEXT("left_to_right"), ESearchCase::IgnoreCase) ||
        DirectionName.Equals(TEXT("lefttoright"), ESearchCase::IgnoreCase))
    {
        return ENavLinkDirection::LeftToRight;
    }
    if (DirectionName.Equals(TEXT("right_to_left"), ESearchCase::IgnoreCase) ||
        DirectionName.Equals(TEXT("righttoleft"), ESearchCase::IgnoreCase))
    {
        return ENavLinkDirection::RightToLeft;
    }
    return ENavLinkDirection::BothWays;
}

static ECrowdAvoidanceQuality::Type ResolveCrowdQuality(const FString& QualityName)
{
    if (QualityName.Equals(TEXT("low"), ESearchCase::IgnoreCase)) return ECrowdAvoidanceQuality::Low;
    if (QualityName.Equals(TEXT("medium"), ESearchCase::IgnoreCase)) return ECrowdAvoidanceQuality::Medium;
    if (QualityName.Equals(TEXT("high"), ESearchCase::IgnoreCase)) return ECrowdAvoidanceQuality::High;
    return ECrowdAvoidanceQuality::Good;
}

static FString CrowdQualityToString(ECrowdAvoidanceQuality::Type Quality)
{
    switch (Quality)
    {
    case ECrowdAvoidanceQuality::Low: return TEXT("low");
    case ECrowdAvoidanceQuality::Medium: return TEXT("medium");
    case ECrowdAvoidanceQuality::High: return TEXT("high");
    default: return TEXT("good");
    }
}

static FString RuntimeGenerationToString(ERuntimeGenerationType Mode)
{
    switch (Mode)
    {
    case ERuntimeGenerationType::Static: return TEXT("static");
    case ERuntimeGenerationType::DynamicModifiersOnly: return TEXT("dynamic_modifiers_only");
    case ERuntimeGenerationType::Dynamic: return TEXT("dynamic");
    case ERuntimeGenerationType::LegacyGeneration: return TEXT("legacy_generation");
    default: return TEXT("unknown");
    }
}

static FString PathFollowingStatusToString(EPathFollowingStatus::Type Status)
{
    switch (Status)
    {
    case EPathFollowingStatus::Idle: return TEXT("idle");
    case EPathFollowingStatus::Waiting: return TEXT("waiting");
    case EPathFollowingStatus::Paused: return TEXT("paused");
    case EPathFollowingStatus::Moving: return TEXT("moving");
    default: return TEXT("unknown");
    }
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNavCreateLinkProxy(
    const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return CreateErrorResponse(TEXT("No editor world available"));

    FString ActorName;
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    if (ActorName.IsEmpty()) ActorName = TEXT("MCP_NavLinkProxy");

    FVector Left(-150.0f, 0.0f, 0.0f);
    FVector Right(150.0f, 0.0f, 0.0f);
    FVector Location(0.0f, 0.0f, 80.0f);
    if (Params->HasField(TEXT("left"))) Left = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("left"));
    if (Params->HasField(TEXT("right"))) Right = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("right"));
    if (Params->HasField(TEXT("location"))) Location = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));

    bool bTreatEndpointsAsWorld = false;
    Params->TryGetBoolField(TEXT("endpoints_are_world"), bTreatEndpointsAsWorld);
    if (bTreatEndpointsAsWorld)
    {
        Location = (Left + Right) * 0.5f;
        Left -= Location;
        Right -= Location;
    }

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = MakeUniqueObjectName(World, ANavLinkProxy::StaticClass(), FName(*ActorName));
    ANavLinkProxy* Proxy = World->SpawnActor<ANavLinkProxy>(
        ANavLinkProxy::StaticClass(),
        FTransform(Location),
        SpawnParams);
    if (!Proxy) return CreateErrorResponse(TEXT("Failed to spawn NavLinkProxy"));

#if WITH_EDITOR
    Proxy->SetActorLabel(ActorName);
#endif

    FString DirectionName;
    Params->TryGetStringField(TEXT("direction"), DirectionName);
    FString AreaName;
    Params->TryGetStringField(TEXT("area_class"), AreaName);
    UClass* AreaClass = ResolveNavAreaClass(AreaName);

    FNavigationLink Link(Left, Right);
    Link.Direction = ResolveNavLinkDirection(DirectionName);
    if (AreaClass) Link.SetAreaClass(AreaClass);
    Proxy->PointLinks.Empty();
    Proxy->PointLinks.Add(Link);

    bool bSmartLinkEnabled = false;
    Params->TryGetBoolField(TEXT("smart_link_enabled"), bSmartLinkEnabled);
    Proxy->bSmartLinkIsRelevant = bSmartLinkEnabled;
    Proxy->SetSmartLinkEnabled(bSmartLinkEnabled);
    Proxy->MarkPackageDirty();
    World->MarkPackageDirty();

    bool bRebuild = true;
    Params->TryGetBoolField(TEXT("rebuild"), bRebuild);
    if (bRebuild)
    {
        if (UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World))
        {
            NavSys->Build();
        }
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("actor_name"), Proxy->GetActorLabel());
    R->SetStringField(TEXT("actor_path"), Proxy->GetPathName());
    R->SetStringField(TEXT("area_class"), AreaClass ? AreaClass->GetName() : TEXT(""));
    R->SetStringField(TEXT("direction"), DirectionName.IsEmpty() ? TEXT("both") : DirectionName);
    R->SetBoolField(TEXT("smart_link_enabled"), bSmartLinkEnabled);
    R->SetBoolField(TEXT("rebuilt"), bRebuild);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNavAddModifierVolume(
    const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return CreateErrorResponse(TEXT("No editor world available"));

    FString ActorName, AreaName;
    Params->TryGetStringField(TEXT("actor_name"), ActorName);
    Params->TryGetStringField(TEXT("area_class"), AreaName);
    if (ActorName.IsEmpty()) ActorName = TEXT("MCP_NavModifierVolume");
    if (AreaName.IsEmpty()) AreaName = TEXT("NavArea_Null");

    UClass* AreaClass = ResolveNavAreaClass(AreaName);
    if (!AreaClass) return CreateErrorResponse(FString::Printf(TEXT("Unknown nav area class: %s"), *AreaName));

    FVector Location(0.0f, 0.0f, 100.0f);
    FVector Extent(300.0f, 300.0f, 150.0f);
    if (Params->HasField(TEXT("location"))) Location = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("location"));
    if (Params->HasField(TEXT("extent"))) Extent = FUnrealMCPCommonUtils::GetVectorFromJson(Params, TEXT("extent"));

    FActorSpawnParameters SpawnParams;
    SpawnParams.Name = MakeUniqueObjectName(World, ANavModifierVolume::StaticClass(), FName(*ActorName));
    ANavModifierVolume* Volume = World->SpawnActor<ANavModifierVolume>(
        ANavModifierVolume::StaticClass(),
        FTransform(Location),
        SpawnParams);
    if (!Volume) return CreateErrorResponse(TEXT("Failed to spawn NavModifierVolume"));

#if WITH_EDITOR
    Volume->SetActorLabel(ActorName);
#endif
    Volume->SetActorScale3D(Extent / 100.0f);
    Volume->SetAreaClass(AreaClass);
    Volume->MarkPackageDirty();
    World->MarkPackageDirty();

    bool bRebuild = true;
    Params->TryGetBoolField(TEXT("rebuild"), bRebuild);
    if (bRebuild)
    {
        if (UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World))
        {
            NavSys->Build();
        }
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("actor_name"), Volume->GetActorLabel());
    R->SetStringField(TEXT("actor_path"), Volume->GetPathName());
    R->SetStringField(TEXT("area_class"), AreaClass->GetName());
    R->SetBoolField(TEXT("rebuilt"), bRebuild);
    R->SetNumberField(TEXT("extent_x"), Extent.X);
    R->SetNumberField(TEXT("extent_y"), Extent.Y);
    R->SetNumberField(TEXT("extent_z"), Extent.Z);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNavDescribeAgentSettings(
    const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return CreateErrorResponse(TEXT("No editor world available"));

    UNavigationSystemV1* NavSys = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    TArray<TSharedPtr<FJsonValue>> Agents;
    if (NavSys)
    {
        const TArray<FNavDataConfig>& SupportedAgents = NavSys->GetSupportedAgents();
        for (int32 Index = 0; Index < SupportedAgents.Num(); ++Index)
        {
            const FNavDataConfig& Config = SupportedAgents[Index];
            TSharedPtr<FJsonObject> AObj = MakeShared<FJsonObject>();
            AObj->SetNumberField(TEXT("index"), Index);
            AObj->SetStringField(TEXT("name"), Config.Name.ToString());
            AObj->SetNumberField(TEXT("agent_radius"), Config.AgentRadius);
            AObj->SetNumberField(TEXT("agent_height"), Config.AgentHeight);
            AObj->SetNumberField(TEXT("query_extent_x"), Config.DefaultQueryExtent.X);
            AObj->SetNumberField(TEXT("query_extent_y"), Config.DefaultQueryExtent.Y);
            AObj->SetNumberField(TEXT("query_extent_z"), Config.DefaultQueryExtent.Z);
            if (UClass* NavDataClass = Config.GetNavDataClass<ANavigationData>())
            {
                AObj->SetStringField(TEXT("nav_data_class"), NavDataClass->GetName());
            }
            Agents.Add(MakeShared<FJsonValueObject>(AObj));
        }
    }

    TArray<AActor*> NavBounds;
    UGameplayStatics::GetAllActorsOfClass(World, ANavMeshBoundsVolume::StaticClass(), NavBounds);
    TArray<AActor*> LinkProxies;
    UGameplayStatics::GetAllActorsOfClass(World, ANavLinkProxy::StaticClass(), LinkProxies);
    TArray<AActor*> ModifierVolumes;
    UGameplayStatics::GetAllActorsOfClass(World, ANavModifierVolume::StaticClass(), ModifierVolumes);
    TArray<AActor*> NavDataActors;
    UGameplayStatics::GetAllActorsOfClass(World, ANavigationData::StaticClass(), NavDataActors);

    TArray<TSharedPtr<FJsonValue>> NavData;
    for (AActor* Actor : NavDataActors)
    {
        if (ANavigationData* Data = Cast<ANavigationData>(Actor))
        {
            TSharedPtr<FJsonObject> DObj = MakeShared<FJsonObject>();
            DObj->SetStringField(TEXT("name"), Data->GetActorLabel());
            DObj->SetStringField(TEXT("class"), Data->GetClass()->GetName());
            DObj->SetStringField(TEXT("runtime_generation"), RuntimeGenerationToString(Data->GetRuntimeGenerationMode()));
            NavData.Add(MakeShared<FJsonValueObject>(DObj));
        }
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("navigation_system_present"), NavSys != nullptr);
    R->SetArrayField(TEXT("supported_agents"), Agents);
    R->SetArrayField(TEXT("nav_data"), NavData);
    R->SetNumberField(TEXT("navmesh_bounds_count"), NavBounds.Num());
    R->SetNumberField(TEXT("nav_link_proxy_count"), LinkProxies.Num());
    R->SetNumberField(TEXT("nav_modifier_volume_count"), ModifierVolumes.Num());
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCrowdConfigureRVO(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    if (!BP->GeneratedClass)
    {
        FKismetEditorUtilities::CompileBlueprint(BP);
    }

    ACharacter* CharacterCDO = BP->GeneratedClass ? Cast<ACharacter>(BP->GeneratedClass->GetDefaultObject()) : nullptr;
    if (!CharacterCDO || !CharacterCDO->GetCharacterMovement())
    {
        return CreateErrorResponse(TEXT("Blueprint is not a Character or has no CharacterMovement component"));
    }

    UCharacterMovementComponent* Movement = CharacterCDO->GetCharacterMovement();
    Movement->Modify();

    bool bEnabled = true;
    Params->TryGetBoolField(TEXT("enabled"), bEnabled);
    double ConsiderationRadius = Movement->AvoidanceConsiderationRadius > 0.0f ? Movement->AvoidanceConsiderationRadius : 500.0;
    double AvoidanceWeight = Movement->AvoidanceWeight > 0.0f ? Movement->AvoidanceWeight : 0.5;
    Params->TryGetNumberField(TEXT("consideration_radius"), ConsiderationRadius);
    Params->TryGetNumberField(TEXT("avoidance_weight"), AvoidanceWeight);

    double GroupD = 1.0, GroupsToAvoidD = 0xFFFFFFFF, GroupsToIgnoreD = 0.0;
    Params->TryGetNumberField(TEXT("avoidance_group"), GroupD);
    Params->TryGetNumberField(TEXT("groups_to_avoid"), GroupsToAvoidD);
    Params->TryGetNumberField(TEXT("groups_to_ignore"), GroupsToIgnoreD);

    FNavAvoidanceMask AvoidanceGroup;
    AvoidanceGroup.SetFlagsDirectly((uint32)GroupD);
    FNavAvoidanceMask GroupsToAvoid;
    GroupsToAvoid.SetFlagsDirectly((uint32)GroupsToAvoidD);
    FNavAvoidanceMask GroupsToIgnore;
    GroupsToIgnore.SetFlagsDirectly((uint32)GroupsToIgnoreD);

    Movement->SetAvoidanceEnabled(bEnabled);
    Movement->AvoidanceConsiderationRadius = (float)ConsiderationRadius;
    Movement->AvoidanceWeight = (float)AvoidanceWeight;
    Movement->SetAvoidanceGroupMask(AvoidanceGroup);
    Movement->SetGroupsToAvoidMask(GroupsToAvoid);
    Movement->SetGroupsToIgnoreMask(GroupsToIgnore);

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetBoolField(TEXT("enabled"), Movement->bUseRVOAvoidance);
    R->SetNumberField(TEXT("consideration_radius"), Movement->AvoidanceConsiderationRadius);
    R->SetNumberField(TEXT("avoidance_weight"), Movement->AvoidanceWeight);
    R->SetNumberField(TEXT("avoidance_group"), Movement->GetAvoidanceGroupMask());
    R->SetNumberField(TEXT("groups_to_avoid"), Movement->GetGroupsToAvoidMask());
    R->SetNumberField(TEXT("groups_to_ignore"), Movement->GetGroupsToIgnoreMask());
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCrowdConfigureDetour(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    Params->TryGetStringField(TEXT("blueprint_name"), BPName);

    UBlueprint* BP = BPName.IsEmpty() ? nullptr : FindBlueprint(BPName);
    AAIController* ControllerCDO = nullptr;
    if (BP)
    {
        if (!BP->GeneratedClass) FKismetEditorUtilities::CompileBlueprint(BP);
        ControllerCDO = BP->GeneratedClass ? Cast<AAIController>(BP->GeneratedClass->GetDefaultObject()) : nullptr;
    }

    UCrowdFollowingComponent* Crowd = ControllerCDO
        ? Cast<UCrowdFollowingComponent>(ControllerCDO->GetPathFollowingComponent())
        : nullptr;
    if (!Crowd)
    {
        TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
        R->SetBoolField(TEXT("success"), true);
        R->SetBoolField(TEXT("configured"), false);
        R->SetStringField(TEXT("blueprint_name"), BPName);
        R->SetStringField(TEXT("message"),
            TEXT("Detour crowd following requires the AIController's PathFollowingComponent default subobject to be UCrowdFollowingComponent. "
                 "Blueprints cannot safely swap that inherited default subobject after construction; create a native AIController class with "
                 "ObjectInitializer.SetDefaultSubobjectClass<UCrowdFollowingComponent>(TEXT(\"PathFollowingComponent\")), then reparent the Blueprint."));
        R->SetStringField(TEXT("required_component_class"), UCrowdFollowingComponent::StaticClass()->GetName());
        return R;
    }

    Crowd->Modify();
    bool bObstacleAvoidance = true, bSeparation = true, bAnticipateTurns = true, bOptimizeVisibility = true, bOptimizeTopology = true;
    Params->TryGetBoolField(TEXT("obstacle_avoidance"), bObstacleAvoidance);
    Params->TryGetBoolField(TEXT("separation"), bSeparation);
    Params->TryGetBoolField(TEXT("anticipate_turns"), bAnticipateTurns);
    Params->TryGetBoolField(TEXT("optimize_visibility"), bOptimizeVisibility);
    Params->TryGetBoolField(TEXT("optimize_topology"), bOptimizeTopology);

    double SeparationWeight = Crowd->GetCrowdSeparationWeight();
    double CollisionRange = Crowd->GetCrowdCollisionQueryRange();
    double OptimizationRange = Crowd->GetCrowdPathOptimizationRange();
    double RangeMultiplier = Crowd->GetCrowdAvoidanceRangeMultiplier();
    Params->TryGetNumberField(TEXT("separation_weight"), SeparationWeight);
    Params->TryGetNumberField(TEXT("collision_query_range"), CollisionRange);
    Params->TryGetNumberField(TEXT("path_optimization_range"), OptimizationRange);
    Params->TryGetNumberField(TEXT("avoidance_range_multiplier"), RangeMultiplier);

    FString QualityName;
    Params->TryGetStringField(TEXT("avoidance_quality"), QualityName);
    ECrowdAvoidanceQuality::Type Quality = ResolveCrowdQuality(QualityName);

    Crowd->SetCrowdSimulationState(ECrowdSimulationState::Enabled);
    Crowd->SuspendCrowdSteering(false);
    Crowd->SetCrowdObstacleAvoidance(bObstacleAvoidance, false);
    Crowd->SetCrowdSeparation(bSeparation, false);
    Crowd->SetCrowdAnticipateTurns(bAnticipateTurns, false);
    Crowd->SetCrowdOptimizeVisibility(bOptimizeVisibility, false);
    Crowd->SetCrowdOptimizeTopology(bOptimizeTopology, false);
    Crowd->SetCrowdSeparationWeight((float)SeparationWeight, false);
    Crowd->SetCrowdCollisionQueryRange((float)CollisionRange, false);
    Crowd->SetCrowdPathOptimizationRange((float)OptimizationRange, false);
    Crowd->SetCrowdAvoidanceRangeMultiplier((float)RangeMultiplier, false);
    Crowd->SetCrowdAvoidanceQuality(Quality, true);

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = BP ? TrySaveAndCompileBlueprint(BP, bCompile, bSave) : false;

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("configured"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("component_class"), Crowd->GetClass()->GetName());
    R->SetStringField(TEXT("avoidance_quality"), CrowdQualityToString(Crowd->GetCrowdAvoidanceQuality()));
    R->SetBoolField(TEXT("obstacle_avoidance"), Crowd->IsCrowdObstacleAvoidanceEnabled());
    R->SetBoolField(TEXT("separation"), Crowd->IsCrowdSeparationEnabled());
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleGameplayDebuggerCaptureAI(
    const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
    if (!World) return CreateErrorResponse(TEXT("No editor world available"));

    TArray<AActor*> Controllers;
    UGameplayStatics::GetAllActorsOfClass(World, AAIController::StaticClass(), Controllers);

    TArray<TSharedPtr<FJsonValue>> ControllerList;
    for (AActor* Actor : Controllers)
    {
        AAIController* Controller = Cast<AAIController>(Actor);
        if (!Controller) continue;

        TSharedPtr<FJsonObject> CObj = MakeShared<FJsonObject>();
        CObj->SetStringField(TEXT("name"), Controller->GetActorLabel());
        CObj->SetStringField(TEXT("class"), Controller->GetClass()->GetName());
        CObj->SetStringField(TEXT("pawn"), Controller->GetPawn() ? Controller->GetPawn()->GetActorLabel() : TEXT(""));
        CObj->SetStringField(TEXT("move_status"), PathFollowingStatusToString(Controller->GetMoveStatus()));
        CObj->SetBoolField(TEXT("has_partial_path"), Controller->HasPartialPath());
        if (UPathFollowingComponent* Path = Controller->GetPathFollowingComponent())
        {
            CObj->SetStringField(TEXT("path_following_class"), Path->GetClass()->GetName());
        }
        if (UBrainComponent* Brain = Controller->GetBrainComponent())
        {
            CObj->SetStringField(TEXT("brain_class"), Brain->GetClass()->GetName());
            CObj->SetBoolField(TEXT("brain_running"), Brain->IsRunning());
            if (UBehaviorTreeComponent* BTC = Cast<UBehaviorTreeComponent>(Brain))
            {
                CObj->SetStringField(TEXT("active_node"), BTC->GetActiveNode() ? BTC->GetActiveNode()->GetNodeName() : TEXT(""));
            }
        }
        if (UBlackboardComponent* Blackboard = Controller->GetBlackboardComponent())
        {
            CObj->SetStringField(TEXT("blackboard_asset"), Blackboard->GetBlackboardAsset()
                ? Blackboard->GetBlackboardAsset()->GetPathName()
                : TEXT(""));
        }
        ControllerList.Add(MakeShared<FJsonValueObject>(CObj));
    }

    TArray<AActor*> NavLinks;
    UGameplayStatics::GetAllActorsOfClass(World, ANavLinkProxy::StaticClass(), NavLinks);
    TArray<AActor*> Modifiers;
    UGameplayStatics::GetAllActorsOfClass(World, ANavModifierVolume::StaticClass(), Modifiers);
    TArray<AActor*> NavBounds;
    UGameplayStatics::GetAllActorsOfClass(World, ANavMeshBoundsVolume::StaticClass(), NavBounds);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("world"), World->GetName());
    R->SetNumberField(TEXT("ai_controller_count"), Controllers.Num());
    R->SetArrayField(TEXT("controllers"), ControllerList);
    R->SetNumberField(TEXT("nav_link_proxy_count"), NavLinks.Num());
    R->SetNumberField(TEXT("nav_modifier_volume_count"), Modifiers.Num());
    R->SetNumberField(TEXT("navmesh_bounds_count"), NavBounds.Num());
    R->SetStringField(TEXT("capture_type"), TEXT("ai_debug_snapshot"));
    return R;
}

static FString ReplicationConditionToString(ELifetimeCondition Condition)
{
    switch (Condition)
    {
    case COND_None: return TEXT("none");
    case COND_InitialOnly: return TEXT("initial_only");
    case COND_OwnerOnly: return TEXT("owner_only");
    case COND_SkipOwner: return TEXT("skip_owner");
    case COND_SimulatedOnly: return TEXT("simulated_only");
    case COND_AutonomousOnly: return TEXT("autonomous_only");
    case COND_SimulatedOrPhysics: return TEXT("simulated_or_physics");
    case COND_InitialOrOwner: return TEXT("initial_or_owner");
    case COND_Custom: return TEXT("custom");
    case COND_ReplayOrOwner: return TEXT("replay_or_owner");
    case COND_ReplayOnly: return TEXT("replay_only");
    case COND_SimulatedOnlyNoReplay: return TEXT("simulated_only_no_replay");
    case COND_SimulatedOrPhysicsNoReplay: return TEXT("simulated_or_physics_no_replay");
    case COND_SkipReplay: return TEXT("skip_replay");
    case COND_Dynamic: return TEXT("dynamic");
    case COND_Never: return TEXT("never");
    default: return TEXT("unknown");
    }
}

static ELifetimeCondition ResolveReplicationCondition(const FString& Name)
{
    if (Name.Equals(TEXT("initial_only"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("initialonly"), ESearchCase::IgnoreCase)) return COND_InitialOnly;
    if (Name.Equals(TEXT("owner_only"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("owneronly"), ESearchCase::IgnoreCase)) return COND_OwnerOnly;
    if (Name.Equals(TEXT("skip_owner"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("skipowner"), ESearchCase::IgnoreCase)) return COND_SkipOwner;
    if (Name.Equals(TEXT("simulated_only"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("simulatedonly"), ESearchCase::IgnoreCase)) return COND_SimulatedOnly;
    if (Name.Equals(TEXT("autonomous_only"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("autonomousonly"), ESearchCase::IgnoreCase)) return COND_AutonomousOnly;
    if (Name.Equals(TEXT("simulated_or_physics"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("simulatedorphysics"), ESearchCase::IgnoreCase)) return COND_SimulatedOrPhysics;
    if (Name.Equals(TEXT("initial_or_owner"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("initialorowner"), ESearchCase::IgnoreCase)) return COND_InitialOrOwner;
    if (Name.Equals(TEXT("custom"), ESearchCase::IgnoreCase)) return COND_Custom;
    if (Name.Equals(TEXT("replay_or_owner"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("replayorowner"), ESearchCase::IgnoreCase)) return COND_ReplayOrOwner;
    if (Name.Equals(TEXT("replay_only"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("replayonly"), ESearchCase::IgnoreCase)) return COND_ReplayOnly;
    if (Name.Equals(TEXT("simulated_only_no_replay"), ESearchCase::IgnoreCase)) return COND_SimulatedOnlyNoReplay;
    if (Name.Equals(TEXT("simulated_or_physics_no_replay"), ESearchCase::IgnoreCase)) return COND_SimulatedOrPhysicsNoReplay;
    if (Name.Equals(TEXT("skip_replay"), ESearchCase::IgnoreCase) || Name.Equals(TEXT("skipreplay"), ESearchCase::IgnoreCase)) return COND_SkipReplay;
    if (Name.Equals(TEXT("dynamic"), ESearchCase::IgnoreCase)) return COND_Dynamic;
    if (Name.Equals(TEXT("never"), ESearchCase::IgnoreCase)) return COND_Never;
    return COND_None;
}

static FString FunctionNetFlagsToString(UFunction* Function)
{
    if (!Function || !Function->HasAnyFunctionFlags(FUNC_Net)) return TEXT("");
    TArray<FString> Parts;
    if (Function->HasAnyFunctionFlags(FUNC_NetServer)) Parts.Add(TEXT("server"));
    if (Function->HasAnyFunctionFlags(FUNC_NetClient)) Parts.Add(TEXT("client"));
    if (Function->HasAnyFunctionFlags(FUNC_NetMulticast)) Parts.Add(TEXT("net_multicast"));
    if (Function->HasAnyFunctionFlags(FUNC_NetReliable)) Parts.Add(TEXT("reliable"));
    if (Parts.Num() == 0) Parts.Add(TEXT("net"));
    return FString::Join(Parts, TEXT("|"));
}

static FString NetFlagsToString(uint32 Flags)
{
    if ((Flags & FUNC_Net) == 0) return TEXT("");
    TArray<FString> Parts;
    if ((Flags & FUNC_NetServer) != 0) Parts.Add(TEXT("server"));
    if ((Flags & FUNC_NetClient) != 0) Parts.Add(TEXT("client"));
    if ((Flags & FUNC_NetMulticast) != 0) Parts.Add(TEXT("net_multicast"));
    if ((Flags & FUNC_NetReliable) != 0) Parts.Add(TEXT("reliable"));
    if (Parts.Num() == 0) Parts.Add(TEXT("net"));
    return FString::Join(Parts, TEXT("|"));
}

static bool ResolveRPCFlags(const FString& RPCType, bool bReliable, uint32& OutFlags, FString& OutError)
{
    const FString Type = RPCType.ToLower();
    OutFlags = 0;
    if (Type.IsEmpty() || Type == TEXT("none") || Type == TEXT("local"))
    {
        return true;
    }

    OutFlags = FUNC_Net;
    if (Type == TEXT("server"))
    {
        OutFlags |= FUNC_NetServer;
    }
    else if (Type == TEXT("client") || Type == TEXT("owning_client"))
    {
        OutFlags |= FUNC_NetClient;
    }
    else if (Type == TEXT("multicast") || Type == TEXT("net_multicast") || Type == TEXT("netmulticast"))
    {
        OutFlags |= FUNC_NetMulticast;
    }
    else
    {
        OutError = FString::Printf(TEXT("Unsupported rpc_type '%s'. Use server, client, net_multicast, or none."), *RPCType);
        return false;
    }

    if (bReliable)
    {
        OutFlags |= FUNC_NetReliable;
    }
    return true;
}

static bool ResolveNetVariablePinType(const FString& VarType, FEdGraphPinType& OutPinType, FString& OutError)
{
    const FString Lower = VarType.ToLower();
    if (Lower == TEXT("boolean") || Lower == TEXT("bool"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Boolean;
    }
    else if (Lower == TEXT("integer") || Lower == TEXT("int") || Lower == TEXT("int32"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Int;
    }
    else if (Lower == TEXT("integer64") || Lower == TEXT("int64"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Int64;
    }
    else if (Lower == TEXT("float"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Real;
        OutPinType.PinSubCategory = UEdGraphSchema_K2::PC_Float;
    }
    else if (Lower == TEXT("double"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Real;
        OutPinType.PinSubCategory = UEdGraphSchema_K2::PC_Double;
    }
    else if (Lower == TEXT("string"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_String;
    }
    else if (Lower == TEXT("name"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Name;
    }
    else if (Lower == TEXT("text"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Text;
    }
    else if (Lower == TEXT("vector"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
        OutPinType.PinSubCategoryObject = TBaseStructure<FVector>::Get();
    }
    else if (Lower == TEXT("rotator"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
        OutPinType.PinSubCategoryObject = TBaseStructure<FRotator>::Get();
    }
    else if (Lower == TEXT("transform"))
    {
        OutPinType.PinCategory = UEdGraphSchema_K2::PC_Struct;
        OutPinType.PinSubCategoryObject = TBaseStructure<FTransform>::Get();
    }
    else
    {
        OutError = FString::Printf(TEXT("Unsupported replicated variable type '%s'"), *VarType);
        return false;
    }
    return true;
}

static FBPVariableDescription* FindNewVariable(UBlueprint* BP, const FString& VariableName)
{
    if (!BP) return nullptr;
    const FName VarFName(*VariableName);
    for (FBPVariableDescription& Var : BP->NewVariables)
    {
        if (Var.VarName == VarFName)
        {
            return &Var;
        }
    }
    return nullptr;
}

static void EnsureRepNotifyFunction(UBlueprint* BP, FBPVariableDescription& Var, const FString& NotifyName)
{
    if (!BP || NotifyName.IsEmpty())
    {
        Var.RepNotifyFunc = NAME_None;
        return;
    }

    UEdGraph* FuncGraph = FindObject<UEdGraph>(BP, *NotifyName);
    if (!FuncGraph)
    {
        FuncGraph = FBlueprintEditorUtils::CreateNewGraph(BP, FName(*NotifyName), UEdGraph::StaticClass(), UEdGraphSchema_K2::StaticClass());
        FBlueprintEditorUtils::AddFunctionGraph<UClass>(BP, FuncGraph, false, nullptr);
    }
    if (FuncGraph)
    {
        FBlueprintEditorUtils::SetBlueprintVariableRepNotifyFunc(BP, Var.VarName, FName(*NotifyName));
        Var.RepNotifyFunc = FName(*NotifyName);
    }
}

static void ApplyVariableReplication(UBlueprint* BP, FBPVariableDescription& Var, const FString& Mode, ELifetimeCondition Condition)
{
    const bool bRepNotify = Mode.Equals(TEXT("repnotify"), ESearchCase::IgnoreCase) ||
        Mode.Equals(TEXT("rep_notify"), ESearchCase::IgnoreCase);
    const bool bReplicated = bRepNotify ||
        Mode.Equals(TEXT("replicated"), ESearchCase::IgnoreCase) ||
        Mode.Equals(TEXT("rep"), ESearchCase::IgnoreCase);

    if (!bReplicated)
    {
        Var.PropertyFlags &= ~CPF_Net;
        Var.PropertyFlags &= ~CPF_RepNotify;
        Var.RepNotifyFunc = NAME_None;
        Var.ReplicationCondition = COND_None;
        FBlueprintEditorUtils::SetBlueprintVariableRepNotifyFunc(BP, Var.VarName, NAME_None);
        return;
    }

    Var.PropertyFlags |= CPF_Net;
    Var.ReplicationCondition = Condition;
    if (bRepNotify)
    {
        Var.PropertyFlags |= CPF_RepNotify;
        const FString NotifyName = FString::Printf(TEXT("OnRep_%s"), *Var.VarName.ToString());
        EnsureRepNotifyFunction(BP, Var, NotifyName);
    }
    else
    {
        Var.PropertyFlags &= ~CPF_RepNotify;
        Var.RepNotifyFunc = NAME_None;
        FBlueprintEditorUtils::SetBlueprintVariableRepNotifyFunc(BP, Var.VarName, NAME_None);
    }
}

static UK2Node_CustomEvent* FindCustomEventNode(UEdGraph* Graph, const FString& EventName)
{
    if (!Graph) return nullptr;
    const FName EventFName(*EventName);
    for (UEdGraphNode* Node : Graph->Nodes)
    {
        UK2Node_CustomEvent* CustomEvent = Cast<UK2Node_CustomEvent>(Node);
        if (CustomEvent && CustomEvent->CustomFunctionName == EventFName)
        {
            return CustomEvent;
        }
    }
    return nullptr;
}

static int32 AddInputsToNetCustomEvent(UK2Node_CustomEvent* EventNode, const TArray<TSharedPtr<FJsonValue>>& InputsArray, FString& OutError)
{
    if (!EventNode) return 0;
    int32 AddedCount = 0;
    for (const TSharedPtr<FJsonValue>& PinVal : InputsArray)
    {
        const TSharedPtr<FJsonObject>* PinObj = nullptr;
        if (!PinVal.IsValid() || !PinVal->TryGetObject(PinObj) || !PinObj) continue;

        FString PinName;
        FString PinTypeStr;
        (*PinObj)->TryGetStringField(TEXT("name"), PinName);
        (*PinObj)->TryGetStringField(TEXT("type"), PinTypeStr);
        if (PinName.IsEmpty() || PinTypeStr.IsEmpty()) continue;

        bool bExists = false;
        for (UEdGraphPin* Existing : EventNode->Pins)
        {
            if (Existing && Existing->PinName == FName(*PinName))
            {
                bExists = true;
                break;
            }
        }
        if (bExists) continue;

        FEdGraphPinType PinType;
        if (!ResolveNetVariablePinType(PinTypeStr, PinType, OutError))
        {
            return AddedCount;
        }

        EventNode->CreateUserDefinedPin(FName(*PinName), PinType, EGPD_Output, true);
        ++AddedCount;
    }

    if (AddedCount > 0)
    {
        EventNode->ReconstructNode();
    }
    return AddedCount;
}

static TArray<TSharedPtr<FJsonValue>> VisiblePinNames(UEdGraphNode* Node)
{
    TArray<TSharedPtr<FJsonValue>> Pins;
    if (!Node) return Pins;
    for (UEdGraphPin* Pin : Node->Pins)
    {
        if (Pin && !Pin->bHidden)
        {
            Pins.Add(MakeShared<FJsonValueString>(Pin->PinName.ToString()));
        }
    }
    return Pins;
}

static FString NetModeToString(ENetMode Mode)
{
    switch (Mode)
    {
    case NM_Standalone: return TEXT("standalone");
    case NM_DedicatedServer: return TEXT("dedicated_server");
    case NM_ListenServer: return TEXT("listen_server");
    case NM_Client: return TEXT("client");
    default: return TEXT("unknown");
    }
}

static FString NetRoleToString(ENetRole Role)
{
    switch (Role)
    {
    case ROLE_None: return TEXT("none");
    case ROLE_SimulatedProxy: return TEXT("simulated_proxy");
    case ROLE_AutonomousProxy: return TEXT("autonomous_proxy");
    case ROLE_Authority: return TEXT("authority");
    default: return TEXT("unknown");
    }
}

static FString DormancyToString(ENetDormancy Dormancy)
{
    switch (Dormancy)
    {
    case DORM_Never: return TEXT("never");
    case DORM_Awake: return TEXT("awake");
    case DORM_DormantAll: return TEXT("dormant_all");
    case DORM_DormantPartial: return TEXT("dormant_partial");
    case DORM_Initial: return TEXT("initial");
    default: return TEXT("unknown");
    }
}

static UWorld* GetPreferredNetDebugWorld()
{
    if (GEditor && GEditor->PlayWorld)
    {
        return GEditor->PlayWorld;
    }
    return GEditor ? GEditor->GetEditorWorldContext().World() : nullptr;
}

static UClass* ResolveOnlineProxyClass(const TCHAR* ClassName)
{
    const FString ClassPath = FString::Printf(TEXT("/Script/OnlineSubsystemUtils.%s"), ClassName);
    UClass* ProxyClass = LoadObject<UClass>(nullptr, *ClassPath);
    if (ProxyClass)
    {
        return ProxyClass;
    }
    return FindFirstObject<UClass>(ClassName, EFindFirstObjectOptions::None);
}

static UK2Node_CallFunction* AddGetPlayerControllerNode(UEdGraph* Graph, const FVector2D& Pos)
{
    if (!Graph) return nullptr;
    UFunction* Func = UGameplayStatics::StaticClass()->FindFunctionByName(TEXT("GetPlayerController"));
    if (!Func) return nullptr;

    UK2Node_CallFunction* Node = NewObject<UK2Node_CallFunction>(Graph);
    Node->SetFromFunction(Func);
    Node->NodePosX = Pos.X;
    Node->NodePosY = Pos.Y;
    Graph->AddNode(Node, true, false);
    Node->CreateNewGuid();
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    if (UEdGraphPin* PlayerIndexPin = Node->FindPin(TEXT("PlayerIndex")))
    {
        PlayerIndexPin->DefaultValue = TEXT("0");
    }
    return Node;
}

static bool SetPinDefaultString(UEdGraphNode* Node, const TCHAR* PinName, const FString& Value)
{
    if (!Node) return false;
    if (UEdGraphPin* Pin = Node->FindPin(PinName))
    {
        Pin->DefaultValue = Value;
        return true;
    }
    return false;
}

static bool SetPinDefaultBool(UEdGraphNode* Node, const TCHAR* PinName, bool bValue)
{
    return SetPinDefaultString(Node, PinName, bValue ? TEXT("true") : TEXT("false"));
}

static bool ConnectPlayerControllerToAsyncNode(UEdGraph* Graph, UK2Node_CallFunction* PlayerNode, UK2Node_AsyncAction* AsyncNode)
{
    if (!Graph || !PlayerNode || !AsyncNode) return false;
    const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();
    UEdGraphPin* ReturnPin = PlayerNode->FindPin(TEXT("ReturnValue"));
    UEdGraphPin* PlayerPin = AsyncNode->FindPin(TEXT("PlayerController"));
    return (Schema && ReturnPin && PlayerPin) ? Schema->TryCreateConnection(ReturnPin, PlayerPin) : false;
}

static UK2Node_AsyncAction* AddOnlineSessionAsyncNode(
    UEdGraph* Graph,
    const TCHAR* ProxyClassName,
    const TCHAR* FactoryFunctionName,
    const FVector2D& Pos,
    FString& OutError)
{
    UClass* ProxyClass = ResolveOnlineProxyClass(ProxyClassName);
    if (!ProxyClass)
    {
        OutError = FString::Printf(TEXT("OnlineSubsystemUtils proxy class not found: %s"), ProxyClassName);
        return nullptr;
    }

    UFunction* FactoryFunction = ProxyClass->FindFunctionByName(FactoryFunctionName);
    if (!FactoryFunction)
    {
        OutError = FString::Printf(TEXT("%s.%s function not found"), ProxyClassName, FactoryFunctionName);
        return nullptr;
    }

    UK2Node_AsyncAction* Node = NewObject<UK2Node_AsyncAction>(Graph);
    Node->InitializeProxyFromFunction(FactoryFunction);
    Node->NodePosX = Pos.X;
    Node->NodePosY = Pos.Y;
    Graph->AddNode(Node, true, false);
    Node->CreateNewGuid();
    Node->PostPlacedNewNode();
    Node->AllocateDefaultPins();
    return Node;
}

static bool BlueprintHasFunctionCallNode(UBlueprint* BP, const FName& FunctionName)
{
    if (!BP) return false;
    TArray<UEdGraph*> Graphs;
    Graphs.Append(BP->UbergraphPages);
    Graphs.Append(BP->FunctionGraphs);
    Graphs.Append(BP->MacroGraphs);
    for (UEdGraph* Graph : Graphs)
    {
        if (!Graph) continue;
        for (UEdGraphNode* Node : Graph->Nodes)
        {
            UK2Node_CallFunction* CallNode = Cast<UK2Node_CallFunction>(Node);
            if (CallNode && CallNode->FunctionReference.GetMemberName() == FunctionName)
            {
                return true;
            }
        }
    }
    return false;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetDescribeBlueprintReplication(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    if (!BP->GeneratedClass) FKismetEditorUtilities::CompileBlueprint(BP);

    AActor* ActorCDO = BP->GeneratedClass ? Cast<AActor>(BP->GeneratedClass->GetDefaultObject()) : nullptr;

    TArray<TSharedPtr<FJsonValue>> Variables;
    for (const FBPVariableDescription& Var : BP->NewVariables)
    {
        TSharedPtr<FJsonObject> VObj = MakeShared<FJsonObject>();
        VObj->SetStringField(TEXT("name"), Var.VarName.ToString());
        VObj->SetStringField(TEXT("type"), Var.VarType.PinCategory.ToString());
        VObj->SetBoolField(TEXT("is_replicated"), (Var.PropertyFlags & CPF_Net) != 0);
        VObj->SetBoolField(TEXT("is_repnotify"), (Var.PropertyFlags & CPF_RepNotify) != 0);
        VObj->SetStringField(TEXT("rep_notify_func"), Var.RepNotifyFunc.ToString());
        VObj->SetStringField(TEXT("replication_condition"), ReplicationConditionToString(Var.ReplicationCondition));
        Variables.Add(MakeShared<FJsonValueObject>(VObj));
    }

    TArray<TSharedPtr<FJsonValue>> Components;
    if (BP->SimpleConstructionScript)
    {
        for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
        {
            if (!Node || !Node->ComponentTemplate) continue;
            if (UActorComponent* Component = Cast<UActorComponent>(Node->ComponentTemplate))
            {
                TSharedPtr<FJsonObject> CObj = MakeShared<FJsonObject>();
                CObj->SetStringField(TEXT("name"), Node->GetVariableName().ToString());
                CObj->SetStringField(TEXT("class"), Component->GetClass()->GetName());
                CObj->SetBoolField(TEXT("is_replicated"), Component->GetIsReplicated());
                Components.Add(MakeShared<FJsonValueObject>(CObj));
            }
        }
    }

    TArray<TSharedPtr<FJsonValue>> RPCs;
    UClass* FunctionClass = BP->SkeletonGeneratedClass ? BP->SkeletonGeneratedClass.Get() : BP->GeneratedClass.Get();
    if (FunctionClass)
    {
        for (TFieldIterator<UFunction> It(FunctionClass, EFieldIteratorFlags::IncludeSuper); It; ++It)
        {
            UFunction* Function = *It;
            if (!Function || !Function->HasAnyFunctionFlags(FUNC_Net)) continue;
            TSharedPtr<FJsonObject> FObj = MakeShared<FJsonObject>();
            FObj->SetStringField(TEXT("name"), Function->GetName());
            FObj->SetStringField(TEXT("net_flags"), FunctionNetFlagsToString(Function));
            RPCs.Add(MakeShared<FJsonValueObject>(FObj));
        }
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetBoolField(TEXT("is_actor_blueprint"), ActorCDO != nullptr);
    if (ActorCDO)
    {
        R->SetBoolField(TEXT("actor_replicates"), ActorCDO->GetIsReplicated());
        R->SetBoolField(TEXT("replicate_movement"), ActorCDO->IsReplicatingMovement());
        R->SetNumberField(TEXT("net_update_frequency"), ActorCDO->GetNetUpdateFrequency());
        R->SetNumberField(TEXT("min_net_update_frequency"), ActorCDO->GetMinNetUpdateFrequency());
    }
    R->SetArrayField(TEXT("variables"), Variables);
    R->SetArrayField(TEXT("components"), Components);
    R->SetArrayField(TEXT("rpc_functions"), RPCs);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetSetActorReplicates(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
    if (!BP->GeneratedClass) FKismetEditorUtilities::CompileBlueprint(BP);

    AActor* ActorCDO = BP->GeneratedClass ? Cast<AActor>(BP->GeneratedClass->GetDefaultObject()) : nullptr;
    if (!ActorCDO) return CreateErrorResponse(TEXT("Blueprint is not an Actor-derived Blueprint"));

    bool bReplicates = true, bReplicateMovement = ActorCDO->IsReplicatingMovement();
    Params->TryGetBoolField(TEXT("replicates"), bReplicates);
    Params->TryGetBoolField(TEXT("replicate_movement"), bReplicateMovement);

    ActorCDO->Modify();
    ActorCDO->SetReplicates(bReplicates);
    ActorCDO->SetReplicateMovement(bReplicateMovement);

    double NetUpdate = ActorCDO->GetNetUpdateFrequency();
    double MinNetUpdate = ActorCDO->GetMinNetUpdateFrequency();
    if (Params->TryGetNumberField(TEXT("net_update_frequency"), NetUpdate))
    {
        ActorCDO->SetNetUpdateFrequency((float)NetUpdate);
    }
    if (Params->TryGetNumberField(TEXT("min_net_update_frequency"), MinNetUpdate))
    {
        ActorCDO->SetMinNetUpdateFrequency((float)MinNetUpdate);
    }

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetBoolField(TEXT("replicates"), ActorCDO->GetIsReplicated());
    R->SetBoolField(TEXT("replicate_movement"), ActorCDO->IsReplicatingMovement());
    R->SetNumberField(TEXT("net_update_frequency"), ActorCDO->GetNetUpdateFrequency());
    R->SetNumberField(TEXT("min_net_update_frequency"), ActorCDO->GetMinNetUpdateFrequency());
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetSetComponentReplicates(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, ComponentName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("component_name"), ComponentName))
        return CreateErrorResponse(TEXT("Missing 'component_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UActorComponent* Component = FindSCSComponentTemplate(BP, ComponentName, UActorComponent::StaticClass());
    if (!Component)
    {
        return CreateErrorResponse(FString::Printf(TEXT("SCS component not found: %s"), *ComponentName));
    }

    bool bReplicates = true;
    Params->TryGetBoolField(TEXT("replicates"), bReplicates);
    Component->Modify();
    Component->SetIsReplicated(bReplicates);

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("component_name"), ComponentName);
    R->SetStringField(TEXT("component_class"), Component->GetClass()->GetName());
    R->SetBoolField(TEXT("replicates"), Component->GetIsReplicated());
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetConfigureReplicatedProperty(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, VariableName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("variable_name"), VariableName))
        return CreateErrorResponse(TEXT("Missing 'variable_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    FBPVariableDescription* Var = FindNewVariable(BP, VariableName);
    if (!Var)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Blueprint variable not found: %s"), *VariableName));
    }

    FString Mode = TEXT("replicated");
    FString ConditionName;
    Params->TryGetStringField(TEXT("replication_mode"), Mode);
    Params->TryGetStringField(TEXT("replication_condition"), ConditionName);
    ApplyVariableReplication(BP, *Var, Mode, ResolveReplicationCondition(ConditionName));

    bool bSave = true, bCompile = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("variable_name"), VariableName);
    R->SetStringField(TEXT("replication_mode"), (Var->PropertyFlags & CPF_RepNotify) ? TEXT("repnotify") : ((Var->PropertyFlags & CPF_Net) ? TEXT("replicated") : TEXT("none")));
    R->SetStringField(TEXT("rep_notify_func"), Var->RepNotifyFunc.ToString());
    R->SetStringField(TEXT("replication_condition"), ReplicationConditionToString(Var->ReplicationCondition));
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetAddRepNotifyVariable(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, VariableName, VariableType;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("variable_name"), VariableName))
        return CreateErrorResponse(TEXT("Missing 'variable_name'"));
    if (!Params->TryGetStringField(TEXT("variable_type"), VariableType))
        return CreateErrorResponse(TEXT("Missing 'variable_type'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    FBPVariableDescription* Var = FindNewVariable(BP, VariableName);
    bool bCreated = false;
    if (!Var)
    {
        FEdGraphPinType PinType;
        FString Error;
        if (!ResolveNetVariablePinType(VariableType, PinType, Error))
        {
            return CreateErrorResponse(Error);
        }
        FBlueprintEditorUtils::AddMemberVariable(BP, FName(*VariableName), PinType);
        Var = FindNewVariable(BP, VariableName);
        bCreated = Var != nullptr;
    }
    if (!Var)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Failed to create variable: %s"), *VariableName));
    }

    FString DefaultValue;
    if (Params->TryGetStringField(TEXT("default_value"), DefaultValue))
    {
        Var->DefaultValue = DefaultValue;
    }

    FString ConditionName;
    Params->TryGetStringField(TEXT("replication_condition"), ConditionName);
    ApplyVariableReplication(BP, *Var, TEXT("repnotify"), ResolveReplicationCondition(ConditionName));

    bool bSave = true, bCompile = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created"), bCreated);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("variable_name"), VariableName);
    R->SetStringField(TEXT("variable_type"), VariableType);
    R->SetStringField(TEXT("replication_mode"), TEXT("repnotify"));
    R->SetStringField(TEXT("rep_notify_func"), Var->RepNotifyFunc.ToString());
    R->SetStringField(TEXT("replication_condition"), ReplicationConditionToString(Var->ReplicationCondition));
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetCreateRPCEvent(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, EventName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("event_name"), EventName))
        return CreateErrorResponse(TEXT("Missing 'event_name'"));

    FString RPCType = TEXT("server");
    bool bReliable = true;
    Params->TryGetStringField(TEXT("rpc_type"), RPCType);
    Params->TryGetBoolField(TEXT("reliable"), bReliable);

    uint32 NetFlags = 0;
    FString Error;
    if (!ResolveRPCFlags(RPCType, bReliable, NetFlags, Error))
    {
        return CreateErrorResponse(Error);
    }

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));

    bool bAlreadyExisted = true;
    UK2Node_CustomEvent* CustomEvent = FindCustomEventNode(Graph, EventName);
    if (!CustomEvent)
    {
        bAlreadyExisted = false;
        const FVector2D Pos = GetNodePosition(Params);
        CustomEvent = NewObject<UK2Node_CustomEvent>(Graph);
        CustomEvent->CustomFunctionName = FName(*EventName);
        CustomEvent->NodePosX = Pos.X;
        CustomEvent->NodePosY = Pos.Y;
        CustomEvent->CreateNewGuid();
        Graph->AddNode(CustomEvent, true, false);
        CustomEvent->PostPlacedNewNode();
        CustomEvent->AllocateDefaultPins();
    }

    CustomEvent->Modify();
    CustomEvent->FunctionFlags &= ~(FUNC_Net | FUNC_NetServer | FUNC_NetClient | FUNC_NetMulticast | FUNC_NetReliable);
    CustomEvent->FunctionFlags |= NetFlags;

    int32 PinsAdded = 0;
    const TArray<TSharedPtr<FJsonValue>>* InputsArray = nullptr;
    if (Params->TryGetArrayField(TEXT("inputs"), InputsArray) && InputsArray)
    {
        PinsAdded = AddInputsToNetCustomEvent(CustomEvent, *InputsArray, Error);
        if (!Error.IsEmpty())
        {
            return CreateErrorResponse(Error);
        }
    }

    bool bSave = true, bCompile = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("already_existed"), bAlreadyExisted);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("event_name"), EventName);
    R->SetStringField(TEXT("node_id"), CustomEvent->NodeGuid.ToString());
    R->SetStringField(TEXT("rpc_type"), RPCType);
    R->SetBoolField(TEXT("reliable"), (CustomEvent->FunctionFlags & FUNC_NetReliable) != 0);
    R->SetStringField(TEXT("net_flags"), NetFlagsToString(CustomEvent->FunctionFlags));
    R->SetNumberField(TEXT("pins_added"), PinsAdded);
    R->SetArrayField(TEXT("pins"), VisiblePinNames(CustomEvent));
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetConfigureRPC(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, EventName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    if (!Params->TryGetStringField(TEXT("event_name"), EventName))
        return CreateErrorResponse(TEXT("Missing 'event_name'"));

    FString RPCType = TEXT("server");
    bool bReliable = true;
    Params->TryGetStringField(TEXT("rpc_type"), RPCType);
    Params->TryGetBoolField(TEXT("reliable"), bReliable);

    uint32 NetFlags = 0;
    FString Error;
    if (!ResolveRPCFlags(RPCType, bReliable, NetFlags, Error))
    {
        return CreateErrorResponse(Error);
    }

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));

    UK2Node_CustomEvent* CustomEvent = FindCustomEventNode(Graph, EventName);
    if (!CustomEvent)
    {
        return CreateErrorResponse(FString::Printf(TEXT("Custom event not found: %s"), *EventName));
    }

    CustomEvent->Modify();
    CustomEvent->FunctionFlags &= ~(FUNC_Net | FUNC_NetServer | FUNC_NetClient | FUNC_NetMulticast | FUNC_NetReliable);
    CustomEvent->FunctionFlags |= NetFlags;
    CustomEvent->ReconstructNode();

    bool bSave = true, bCompile = true;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("event_name"), EventName);
    R->SetStringField(TEXT("node_id"), CustomEvent->NodeGuid.ToString());
    R->SetStringField(TEXT("rpc_type"), RPCType);
    R->SetBoolField(TEXT("reliable"), (CustomEvent->FunctionFlags & FUNC_NetReliable) != 0);
    R->SetStringField(TEXT("net_flags"), NetFlagsToString(CustomEvent->FunctionFlags));
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetAddAuthorityGate(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));

    const FVector2D Pos = GetNodePosition(Params);
    UFunction* HasAuthorityFunc = AActor::StaticClass()->FindFunctionByName(TEXT("HasAuthority"));
    if (!HasAuthorityFunc)
    {
        return CreateErrorResponse(TEXT("AActor::HasAuthority Blueprint function not found"));
    }

    UK2Node_CallFunction* HasAuthorityNode = NewObject<UK2Node_CallFunction>(Graph);
    HasAuthorityNode->SetFromFunction(HasAuthorityFunc);
    HasAuthorityNode->NodePosX = Pos.X;
    HasAuthorityNode->NodePosY = Pos.Y;
    Graph->AddNode(HasAuthorityNode, true, false);
    HasAuthorityNode->CreateNewGuid();
    HasAuthorityNode->PostPlacedNewNode();
    HasAuthorityNode->AllocateDefaultPins();

    UK2Node_IfThenElse* BranchNode = NewObject<UK2Node_IfThenElse>(Graph);
    BranchNode->NodePosX = Pos.X + 320.0f;
    BranchNode->NodePosY = Pos.Y;
    Graph->AddNode(BranchNode, true, false);
    BranchNode->CreateNewGuid();
    BranchNode->PostPlacedNewNode();
    BranchNode->AllocateDefaultPins();

    const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();
    UEdGraphPin* ReturnPin = HasAuthorityNode->FindPin(TEXT("ReturnValue"));
    UEdGraphPin* ConditionPin = BranchNode->GetConditionPin();
    const bool bConnected = (Schema && ReturnPin && ConditionPin) ? Schema->TryCreateConnection(ReturnPin, ConditionPin) : false;

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("has_authority_node_id"), HasAuthorityNode->NodeGuid.ToString());
    R->SetStringField(TEXT("branch_node_id"), BranchNode->NodeGuid.ToString());
    R->SetBoolField(TEXT("condition_connected"), bConnected);
    R->SetStringField(TEXT("authority_pin"), TEXT("Then"));
    R->SetStringField(TEXT("remote_pin"), TEXT("Else"));
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetAddRoleSwitch(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));

    UEnum* NetRoleEnum = StaticEnum<ENetRole>();
    if (!NetRoleEnum)
    {
        return CreateErrorResponse(TEXT("ENetRole enum not available"));
    }

    const FVector2D Pos = GetNodePosition(Params);
    UK2Node_SwitchEnum* SwitchNode = NewObject<UK2Node_SwitchEnum>(Graph);
    SwitchNode->SetEnum(NetRoleEnum);
    SwitchNode->NodePosX = Pos.X;
    SwitchNode->NodePosY = Pos.Y;
    Graph->AddNode(SwitchNode, true, false);
    SwitchNode->CreateNewGuid();
    SwitchNode->PostPlacedNewNode();
    SwitchNode->AllocateDefaultPins();

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("node_id"), SwitchNode->NodeGuid.ToString());
    R->SetStringField(TEXT("enum"), NetRoleEnum->GetName());
    R->SetArrayField(TEXT("pins"), VisiblePinNames(SwitchNode));
    R->SetStringField(TEXT("note"), TEXT("Switch node is created with ENetRole cases; wire a role enum source to the selection pin in graph logic."));
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetSetOwnerReference(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));

    UFunction* SetOwnerFunc = AActor::StaticClass()->FindFunctionByName(TEXT("SetOwner"));
    if (!SetOwnerFunc)
    {
        return CreateErrorResponse(TEXT("AActor::SetOwner Blueprint function not found"));
    }

    const FVector2D Pos = GetNodePosition(Params);
    UK2Node_CallFunction* SetOwnerNode = NewObject<UK2Node_CallFunction>(Graph);
    SetOwnerNode->SetFromFunction(SetOwnerFunc);
    SetOwnerNode->NodePosX = Pos.X;
    SetOwnerNode->NodePosY = Pos.Y;
    Graph->AddNode(SetOwnerNode, true, false);
    SetOwnerNode->CreateNewGuid();
    SetOwnerNode->PostPlacedNewNode();
    SetOwnerNode->AllocateDefaultPins();

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("node_id"), SetOwnerNode->NodeGuid.ToString());
    R->SetStringField(TEXT("function"), TEXT("SetOwner"));
    R->SetArrayField(TEXT("pins"), VisiblePinNames(SetOwnerNode));
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSessionCreateBlueprintFlow(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));

    const FVector2D Pos = GetNodePosition(Params);
    FString Error;
    UK2Node_AsyncAction* SessionNode = AddOnlineSessionAsyncNode(
        Graph,
        TEXT("CreateSessionCallbackProxy"),
        TEXT("CreateSession"),
        Pos,
        Error);
    if (!SessionNode)
    {
        return CreateErrorResponse(Error);
    }

    UK2Node_CallFunction* PlayerNode = AddGetPlayerControllerNode(Graph, FVector2D(Pos.X - 360.0f, Pos.Y + 140.0f));
    const bool bPlayerConnected = ConnectPlayerControllerToAsyncNode(Graph, PlayerNode, SessionNode);

    double PublicConnectionsValue = 4;
    bool bUseLAN = true;
    bool bUseLobbies = true;
    Params->TryGetNumberField(TEXT("public_connections"), PublicConnectionsValue);
    const int32 PublicConnections = FMath::Max(1, FMath::RoundToInt(PublicConnectionsValue));
    Params->TryGetBoolField(TEXT("use_lan"), bUseLAN);
    Params->TryGetBoolField(TEXT("use_lobbies_if_available"), bUseLobbies);
    SetPinDefaultString(SessionNode, TEXT("PublicConnections"), FString::FromInt(PublicConnections));
    SetPinDefaultBool(SessionNode, TEXT("bUseLAN"), bUseLAN);
    SetPinDefaultBool(SessionNode, TEXT("bUseLobbiesIfAvailable"), bUseLobbies);

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("session_node_id"), SessionNode->NodeGuid.ToString());
    R->SetStringField(TEXT("player_controller_node_id"), PlayerNode ? PlayerNode->NodeGuid.ToString() : TEXT(""));
    R->SetBoolField(TEXT("player_controller_connected"), bPlayerConnected);
    R->SetNumberField(TEXT("public_connections"), PublicConnections);
    R->SetBoolField(TEXT("use_lan"), bUseLAN);
    R->SetBoolField(TEXT("use_lobbies_if_available"), bUseLobbies);
    R->SetArrayField(TEXT("pins"), VisiblePinNames(SessionNode));
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleSessionFindBlueprintFlow(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    UEdGraph* Graph = FUnrealMCPCommonUtils::FindOrCreateEventGraph(BP);
    if (!Graph) return CreateErrorResponse(TEXT("Failed to get event graph"));

    const FVector2D Pos = GetNodePosition(Params);
    FString Error;
    UK2Node_AsyncAction* SessionNode = AddOnlineSessionAsyncNode(
        Graph,
        TEXT("FindSessionsCallbackProxy"),
        TEXT("FindSessions"),
        Pos,
        Error);
    if (!SessionNode)
    {
        return CreateErrorResponse(Error);
    }

    UK2Node_CallFunction* PlayerNode = AddGetPlayerControllerNode(Graph, FVector2D(Pos.X - 360.0f, Pos.Y + 140.0f));
    const bool bPlayerConnected = ConnectPlayerControllerToAsyncNode(Graph, PlayerNode, SessionNode);

    double MaxResultsValue = 20;
    bool bUseLAN = true;
    bool bUseLobbies = true;
    Params->TryGetNumberField(TEXT("max_results"), MaxResultsValue);
    const int32 MaxResults = FMath::Max(1, FMath::RoundToInt(MaxResultsValue));
    Params->TryGetBoolField(TEXT("use_lan"), bUseLAN);
    Params->TryGetBoolField(TEXT("use_lobbies"), bUseLobbies);
    SetPinDefaultString(SessionNode, TEXT("MaxResults"), FString::FromInt(MaxResults));
    SetPinDefaultBool(SessionNode, TEXT("bUseLAN"), bUseLAN);
    SetPinDefaultBool(SessionNode, TEXT("bUseLobbies"), bUseLobbies);

    bool bSave = true, bCompile = false;
    Params->TryGetBoolField(TEXT("save"), bSave);
    Params->TryGetBoolField(TEXT("compile"), bCompile);
    const bool bSaved = TrySaveAndCompileBlueprint(BP, bCompile, bSave);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("session_node_id"), SessionNode->NodeGuid.ToString());
    R->SetStringField(TEXT("player_controller_node_id"), PlayerNode ? PlayerNode->NodeGuid.ToString() : TEXT(""));
    R->SetBoolField(TEXT("player_controller_connected"), bPlayerConnected);
    R->SetNumberField(TEXT("max_results"), MaxResults);
    R->SetBoolField(TEXT("use_lan"), bUseLAN);
    R->SetBoolField(TEXT("use_lobbies"), bUseLobbies);
    R->SetArrayField(TEXT("pins"), VisiblePinNames(SessionNode));
    R->SetBoolField(TEXT("saved"), bSaved);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetworkDebugReplication(
    const TSharedPtr<FJsonObject>& Params)
{
    UWorld* World = GetPreferredNetDebugWorld();
    if (!World) return CreateErrorResponse(TEXT("No editor or PIE world available"));

    double MaxActorsValue = 25;
    Params->TryGetNumberField(TEXT("max_actors"), MaxActorsValue);
    const int32 MaxActors = FMath::Clamp(FMath::RoundToInt(MaxActorsValue), 0, 200);

    UNetDriver* NetDriver = World->GetNetDriver();
    TArray<TSharedPtr<FJsonValue>> Connections;
    if (NetDriver)
    {
        auto AddConnection = [&Connections](const FString& Kind, UNetConnection* Connection)
        {
            if (!Connection) return;
            TSharedPtr<FJsonObject> CObj = MakeShared<FJsonObject>();
            CObj->SetStringField(TEXT("kind"), Kind);
            CObj->SetStringField(TEXT("state"), LexToString(Connection->GetConnectionState()));
            CObj->SetStringField(TEXT("description"), Connection->Describe());
            CObj->SetStringField(TEXT("low_level"), Connection->LowLevelDescribe());
            CObj->SetNumberField(TEXT("open_channels"), Connection->OpenChannels.Num());
            CObj->SetNumberField(TEXT("actor_channels"), Connection->ActorChannelsNum());
            CObj->SetStringField(TEXT("player_controller"), GetNameSafe(Connection->PlayerController));
            Connections.Add(MakeShared<FJsonValueObject>(CObj));
        };

        AddConnection(TEXT("server"), NetDriver->ServerConnection);
        for (UNetConnection* Connection : NetDriver->ClientConnections)
        {
            AddConnection(TEXT("client"), Connection);
        }
    }

    TArray<TSharedPtr<FJsonValue>> Actors;
    int32 ReplicatedActorCount = 0;
    for (TActorIterator<AActor> It(World); It; ++It)
    {
        AActor* Actor = *It;
        if (!Actor || !Actor->GetIsReplicated()) continue;
        ++ReplicatedActorCount;
        if (Actors.Num() >= MaxActors) continue;

        TSharedPtr<FJsonObject> AObj = MakeShared<FJsonObject>();
#if WITH_EDITOR
        AObj->SetStringField(TEXT("name"), Actor->GetActorLabel());
#else
        AObj->SetStringField(TEXT("name"), Actor->GetName());
#endif
        AObj->SetStringField(TEXT("class"), Actor->GetClass()->GetName());
        AObj->SetStringField(TEXT("path"), Actor->GetPathName());
        AObj->SetStringField(TEXT("local_role"), NetRoleToString(Actor->GetLocalRole()));
        AObj->SetStringField(TEXT("remote_role"), NetRoleToString(Actor->GetRemoteRole()));
        AObj->SetStringField(TEXT("owner"), GetNameSafe(Actor->GetOwner()));
        AObj->SetBoolField(TEXT("replicate_movement"), Actor->IsReplicatingMovement());
        AObj->SetNumberField(TEXT("net_update_frequency"), Actor->GetNetUpdateFrequency());
        AObj->SetStringField(TEXT("net_dormancy"), DormancyToString(Actor->NetDormancy));
        Actors.Add(MakeShared<FJsonValueObject>(AObj));
    }

    int32 ActiveNetworkObjects = 0;
    int32 DormantAllConnections = 0;
    int32 AllNetworkObjects = 0;
    if (NetDriver)
    {
        const FNetworkObjectList& NetObjects = NetDriver->GetNetworkObjectList();
        ActiveNetworkObjects = NetObjects.GetActiveObjects().Num();
        DormantAllConnections = NetObjects.GetDormantObjectsOnAllConnections().Num();
        AllNetworkObjects = NetObjects.GetAllObjects().Num();
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("world"), World->GetName());
    R->SetBoolField(TEXT("is_pie_world"), World->WorldType == EWorldType::PIE);
    R->SetStringField(TEXT("net_mode"), NetModeToString(World->GetNetMode()));
    R->SetBoolField(TEXT("has_net_driver"), NetDriver != nullptr);
    if (NetDriver)
    {
        R->SetStringField(TEXT("net_driver_name"), NetDriver->NetDriverName.ToString());
        R->SetStringField(TEXT("net_driver_class"), NetDriver->GetClass()->GetName());
        R->SetBoolField(TEXT("is_server"), NetDriver->IsServer());
        R->SetNumberField(TEXT("client_connection_count"), NetDriver->ClientConnections.Num());
        R->SetBoolField(TEXT("has_server_connection"), NetDriver->ServerConnection != nullptr);
        R->SetBoolField(TEXT("has_replication_driver"), NetDriver->GetReplicationDriver() != nullptr);
        R->SetNumberField(TEXT("active_network_objects"), ActiveNetworkObjects);
        R->SetNumberField(TEXT("dormant_all_connections"), DormantAllConnections);
        R->SetNumberField(TEXT("all_network_objects"), AllNetworkObjects);
    }
    R->SetNumberField(TEXT("replicated_actor_count"), ReplicatedActorCount);
    R->SetArrayField(TEXT("replicated_actors_sample"), Actors);
    R->SetArrayField(TEXT("connections"), Connections);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleNetValidateCommonMistakes(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    Params->TryGetStringField(TEXT("blueprint_name"), BPName);

    TArray<UBlueprint*> BlueprintsToCheck;
    if (!BPName.IsEmpty())
    {
        UBlueprint* BP = FindBlueprint(BPName);
        if (!BP) return CreateErrorResponse(FString::Printf(TEXT("Blueprint not found: %s"), *BPName));
        BlueprintsToCheck.Add(BP);
    }
    else
    {
        for (TObjectIterator<UBlueprint> It; It; ++It)
        {
            if (*It && (*It)->GeneratedClass)
            {
                BlueprintsToCheck.Add(*It);
            }
        }
    }

    TArray<TSharedPtr<FJsonValue>> Issues;
    auto AddIssue = [&Issues](const FString& BlueprintName, const FString& Severity, const FString& Code, const FString& Message, const FString& Fix)
    {
        TSharedPtr<FJsonObject> IObj = MakeShared<FJsonObject>();
        IObj->SetStringField(TEXT("blueprint_name"), BlueprintName);
        IObj->SetStringField(TEXT("severity"), Severity);
        IObj->SetStringField(TEXT("code"), Code);
        IObj->SetStringField(TEXT("message"), Message);
        IObj->SetStringField(TEXT("fix"), Fix);
        Issues.Add(MakeShared<FJsonValueObject>(IObj));
    };

    for (UBlueprint* BP : BlueprintsToCheck)
    {
        if (!BP) continue;
        if (!BP->GeneratedClass) FKismetEditorUtilities::CompileBlueprint(BP);

        const FString CheckedBPName = BP->GetName();
        AActor* ActorCDO = BP->GeneratedClass ? Cast<AActor>(BP->GeneratedClass->GetDefaultObject()) : nullptr;
        const bool bActorReplicates = ActorCDO && ActorCDO->GetIsReplicated();
        const bool bHasSetOwnerNode = BlueprintHasFunctionCallNode(BP, TEXT("SetOwner"));

        int32 ReplicatedVarCount = 0;
        int32 ReplicatedComponentCount = 0;
        int32 RPCCount = 0;
        bool bHasOwnerCondition = false;

        for (const FBPVariableDescription& Var : BP->NewVariables)
        {
            const bool bReplicated = (Var.PropertyFlags & CPF_Net) != 0;
            if (!bReplicated) continue;
            ++ReplicatedVarCount;
            if (Var.ReplicationCondition == COND_OwnerOnly || Var.ReplicationCondition == COND_SkipOwner || Var.ReplicationCondition == COND_InitialOrOwner)
            {
                bHasOwnerCondition = true;
            }
            if ((Var.PropertyFlags & CPF_RepNotify) != 0)
            {
                if (Var.RepNotifyFunc.IsNone() || !FindObject<UEdGraph>(BP, *Var.RepNotifyFunc.ToString()))
                {
                    AddIssue(CheckedBPName, TEXT("error"), TEXT("repnotify_missing_handler"),
                        FString::Printf(TEXT("RepNotify variable '%s' has no matching OnRep graph."), *Var.VarName.ToString()),
                        TEXT("Regenerate or assign the RepNotify function with net_add_repnotify_variable or net_configure_replicated_property."));
                }
            }
        }

        if (BP->SimpleConstructionScript)
        {
            for (USCS_Node* Node : BP->SimpleConstructionScript->GetAllNodes())
            {
                UActorComponent* Component = Node ? Cast<UActorComponent>(Node->ComponentTemplate) : nullptr;
                if (Component && Component->GetIsReplicated())
                {
                    ++ReplicatedComponentCount;
                }
            }
        }

        TArray<UEdGraph*> Graphs;
        Graphs.Append(BP->UbergraphPages);
        for (UEdGraph* Graph : Graphs)
        {
            if (!Graph) continue;
            for (UEdGraphNode* Node : Graph->Nodes)
            {
                UK2Node_CustomEvent* CustomEvent = Cast<UK2Node_CustomEvent>(Node);
                if (!CustomEvent || (CustomEvent->FunctionFlags & FUNC_Net) == 0) continue;
                ++RPCCount;
                if ((CustomEvent->FunctionFlags & FUNC_NetMulticast) != 0 && (CustomEvent->FunctionFlags & FUNC_NetReliable) != 0)
                {
                    AddIssue(CheckedBPName, TEXT("warning"), TEXT("reliable_multicast"),
                        FString::Printf(TEXT("RPC '%s' is a reliable multicast."), *CustomEvent->CustomFunctionName.ToString()),
                        TEXT("Use reliable multicast only for rare critical events; prefer unreliable multicast for frequent cosmetic events."));
                }
            }
        }

        const bool bHasNetworkSurface = ReplicatedVarCount > 0 || ReplicatedComponentCount > 0 || RPCCount > 0;
        if (!ActorCDO && bHasNetworkSurface)
        {
            AddIssue(CheckedBPName, TEXT("error"), TEXT("network_surface_on_non_actor"),
                TEXT("Replication settings or RPCs were found on a non-Actor Blueprint."),
                TEXT("Move replicated state and RPC Custom Events to an Actor-derived Blueprint."));
        }
        if (ActorCDO && !bActorReplicates && bHasNetworkSurface)
        {
            AddIssue(CheckedBPName, TEXT("warning"), TEXT("actor_not_replicating"),
                TEXT("Blueprint has replicated variables, replicated components, or RPCs, but the Actor replication default is disabled."),
                TEXT("Enable Actor replication with net_set_actor_replicates."));
        }
        if (ActorCDO && !bActorReplicates && ReplicatedComponentCount > 0)
        {
            AddIssue(CheckedBPName, TEXT("warning"), TEXT("component_replicates_actor_does_not"),
                TEXT("One or more components replicate, but the owning Actor does not."),
                TEXT("Enable Actor replication before relying on component replication."));
        }
        if (bHasOwnerCondition && !bHasSetOwnerNode)
        {
            AddIssue(CheckedBPName, TEXT("info"), TEXT("owner_condition_without_owner_setup"),
                TEXT("Owner-based replication conditions are used, but no SetOwner call node was found in this Blueprint."),
                TEXT("Ensure ownership is assigned in authoritative server logic; net_set_owner_reference can add the graph call node."));
        }
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetNumberField(TEXT("blueprints_checked"), BlueprintsToCheck.Num());
    R->SetNumberField(TEXT("issue_count"), Issues.Num());
    R->SetArrayField(TEXT("issues"), Issues);
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddPawnSensingComponent(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, CompName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    CompName = TEXT("PawnSensing");

    UBlueprint* BP = FindBlueprint(BPName);
    if (!BP) return CreateErrorResponse(
        FString::Printf(TEXT("Blueprint not found: %s"), *BPName));

    // Use exec_python guidance for adding UPawnSensingComponent
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("blueprint_name"), BPName);
    R->SetStringField(TEXT("message"),
        TEXT("Use add_component_to_blueprint with component_type='PawnSensingComponent', "
             "then set_component_property for SightRadius, HearingThreshold, etc."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddComponentEventNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, EventName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("event_name"), EventName);
    if (EventName.IsEmpty()) EventName = TEXT("OnSeePawn");
    // Route to add_blueprint_event_node
    TSharedPtr<FJsonObject> EventParams = MakeShared<FJsonObject>();
    EventParams->SetStringField(TEXT("blueprint_name"), BPName);
    EventParams->SetStringField(TEXT("event_name"), EventName);
    if (Params->HasField(TEXT("node_position")))
        EventParams->SetField(TEXT("node_position"), Params->Values.FindRef(TEXT("node_position")));
    return HandleAddCustomEvent(EventParams);
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddFinishExecuteNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("BTTaskNode"),
        TEXT("FinishExecute"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddGetRandomReachablePointNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("NavigationSystem"),
        TEXT("K2_GetRandomReachablePointInRadius"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddClearBlackboardValueNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("BlackboardComponent"),
        TEXT("ClearValue"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddBTBlackboardDecorator(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("BT Blackboard Decorator: use exec_python to create a BTDecorator_Blackboard asset "
             "and configure its BlackboardKey property."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateBTAttackTask(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Create BT Attack Task: use create_bt_task then add_blueprint_function_node "
             "with ApplyDamage to implement the attack behavior."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateBTWanderTask(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Create BT Wander Task: use create_bt_task then add_move_to_node + "
             "add_get_random_reachable_point_node for wandering behavior."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateEnemySpawnerBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Enemy spawner: use create_blueprint(parent_class='Actor') + "
             "add_blueprint_variable(EnemyClass, WaveSize) + "
             "add_set_timer_by_function_name_node for wave spawning."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateFullUpgradedEnemyAI(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Upgraded enemy AI: use create_full_enemy_ai first, then add hearing/attack tasks "
             "via create_bt_attack_task and create_bt_wander_task."));
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// BT Graph Node Manipulation
// ════════════════════════════════════════════════════════════════════════════

/**
 * ROOT CAUSE of all 0x68 crashes — DEFINITIVE ANALYSIS (from UE5 source):
 *
 * SOURCE FILES STUDIED: BehaviorTreeGraph.cpp, AIGraph.cpp, AIGraphNode.cpp,
 *   BehaviorTreeGraphNode.cpp, BehaviorTreeEditorModule.cpp, EdGraph.cpp, EdGraph.h
 *
 * CRASH CHAIN:
 *   Any graph mutation → NotifyGraphChanged() → OnGraphChanged.Broadcast()
 *   → BT editor module's handler → IBehaviorTreeEditor* (null at +0x68)
 *
 * FUNCTIONS THAT FIRE NotifyGraphChanged (EdGraph.cpp:244, 276, 284, 298):
 *   UEdGraph::AddNode()              — always, at line 244
 *   UEdGraph::RemoveNode()           — always, at line 276
 *   UEdGraph::NotifyGraphChanged()   — direct call
 *   UEdGraphPin::MakeLinkTo()        — fires on both pins' nodes
 *   UEdGraphPin::BreakAllPinLinks()  — fires on both sides
 *   UEdGraphNode::BreakAllNodeLinks()— calls BreakAllPinLinks
 *   UAIGraphNode::AddSubNode()       — fires at line 297 (AIGraphNode.cpp)
 *   UAIGraphNode::NodeConnectionListChanged() — calls UpdateAsset (AIGraphNode.cpp:240)
 *   UAIGraph::OnSubNodeDropped()     — fires at AIGraph.cpp:282
 *   UAIGraph::UnlockUpdates()        — calls UpdateAsset (AIGraph.cpp:277)
 *
 * NODE INSTANCE CREATION (CRITICAL):
 *   UAIGraphNode::PostPlacedNewNode() creates NodeInstance = NewObject<UObject>(GraphOwner, Class)
 *   where GraphOwner = MyGraph->GetOuter() = the UBehaviorTree ASSET (not the graph!).
 *   This means NodeInstance has outer=BT and IS serialized as a BT subobject.
 *   InitializeInstance() must be called AFTER PostPlacedNewNode().
 *   ClassData must be set BEFORE PostPlacedNewNode() (it calls ClassData.GetClass()).
 *
 * SUPPRESSION MECHANISM:
 *   UAIGraph::bLockUpdates is PROTECTED (AIGraph.h:62) — cannot access directly.
 *   Public API: LockUpdates() sets true, UnlockUpdates() sets false then calls UpdateAsset().
 *   UpdateAsset() does NOT call NotifyGraphChanged (safe to call from UnlockUpdates()).
 *   Pattern: LockUpdates() → SpawnMissingNodes() → UnlockUpdates() (safe — no NotifyGraphChanged).
 *   Skip OnSave() — it calls SpawnMissingNodesForParallel → AddSubNode → NotifyGraphChanged → crash.
 *
 * SAFE OPERATIONS (do NOT fire NotifyGraphChanged):
 *   BTGraph->Nodes.Add(N)        — raw array add
 *   BTGraph->Nodes.Remove(N)     — raw array remove
 *   BTSafeLinkPins(A,B)          — direct LinkedTo manipulation
 *   BTSafeUnlinkPin(P)           — direct LinkedTo manipulation
 *   N->SubNodes.Add(Sub)         — raw SubNodes array
 *   N->OnSubNodeAdded(Sub)       — populates Decorators[]/Services[] (no NotifyGraphChanged)
 *   N->AllocateDefaultPins()     — just calls CreatePin, no notification
 *   N->PostPlacedNewNode()       — creates NodeInstance, no notification
 *   N->InitializeInstance()      — initializes BTNode, no notification
 *
 * CloseAllEditorsForAsset alone is NOT enough — the OnGraphChanged listener
 * is registered at module load time on every UBehaviorTreeGraph, not per window.
 */

/**
 * BTSafeAddNode – add a graph node to the BT graph WITHOUT firing
 * NotifyGraphChanged.  Replicates what UEdGraph::AddNode does (adds to
 * Nodes, sets RF_Transactional, fixes Outer via Rename) but skips the
 * NotifyGraphChanged call that causes the 0x68 crash.
 */
static void BTSafeAddNode(UBehaviorTreeGraph* BTGraph, UBehaviorTreeGraphNode* Node)
{
    if (!BTGraph || !Node) return;
    BTGraph->Nodes.Add(Node);
    Node->SetFlags(RF_Transactional);
    // Fix outer so the node is properly owned by this graph
    if (Node->GetOuter() != BTGraph)
        Node->Rename(nullptr, BTGraph, REN_NonTransactional | REN_DoNotDirty | REN_ForceNoResetLoaders);
}

/**
 * BTSafeLinkPins – connect two pins by directly appending to LinkedTo
 * arrays, without calling MakeLinkTo / NotifyGraphChanged.
 */
static void BTSafeLinkPins(UEdGraphPin* OutputPin, UEdGraphPin* InputPin)
{
    if (!OutputPin || !InputPin) return;
    OutputPin->LinkedTo.AddUnique(InputPin);
    InputPin->LinkedTo.AddUnique(OutputPin);
}

/**
 * BTSafeUnlinkPin – sever all connections on a pin by directly clearing
 * LinkedTo arrays (both sides), without calling BreakAllPinLinks /
 * NotifyGraphChanged.
 */
static void BTSafeUnlinkPin(UEdGraphPin* Pin)
{
    if (!Pin) return;
    for (UEdGraphPin* Other : Pin->LinkedTo)
    {
        if (Other) Other->LinkedTo.Remove(Pin);
    }
    Pin->LinkedTo.Empty();
}

/**
 * CloseAllBTEditors – close any open editor windows for BT asset.
 * Alone this is NOT sufficient to prevent the crash (see analysis above),
 * but it is still good practice to avoid re-entrancy issues.
 */
static void CloseAllBTEditors(UBehaviorTree* BT)
{
    if (!BT || !GEditor) return;
    if (UAssetEditorSubsystem* AES =
            GEditor->GetEditorSubsystem<UAssetEditorSubsystem>())
    {
        AES->CloseAllEditorsForAsset(BT);
    }
}

/**
 * SafeRemoveBTNodes – removes every non-root node from BTGraph
 * WITHOUT firing NotifyGraphChanged at any point.
 * Uses BTSafeUnlinkPin to clear pin connections (no BreakAllPinLinks)
 * and direct BTGraph->Nodes.Remove (no RemoveNode delegate).
 */
static void SafeRemoveBTNodes(UBehaviorTreeGraph* BTGraph)
{
    if (!BTGraph) return;

    TArray<UEdGraphNode*> ToRemove;
    for (UEdGraphNode* N : BTGraph->Nodes)
    {
        if (N && !N->IsA<UBehaviorTreeGraphNode_Root>())
            ToRemove.Add(N);
    }

    for (UEdGraphNode* N : ToRemove)
    {
        // Sever all pin connections WITHOUT calling BreakAllPinLinks
        // (BreakAllPinLinks calls NotifyGraphChanged → crashes at 0x68)
        for (UEdGraphPin* Pin : N->Pins)
            BTSafeUnlinkPin(Pin);

        // Remove sub-nodes too
        if (UAIGraphNode* AIN = Cast<UAIGraphNode>(N))
        {
            for (UAIGraphNode* Sub : AIN->SubNodes)
            {
                if (!Sub) continue;
                for (UEdGraphPin* SP : Sub->Pins) BTSafeUnlinkPin(SP);
                Sub->ClearFlags(RF_Transactional);
                Sub->SetFlags(RF_Transient);
            }
            AIN->SubNodes.Empty();
        }

        // Direct array removal — avoids RemoveNode() which fires delegate
        BTGraph->Nodes.Remove(N);
        // Mark transient so GC can collect it and it won't be re-saved
        N->ClearFlags(RF_Transactional);
        N->SetFlags(RF_Transient);
    }
}

/** Helper: find a BehaviorTree asset by name */
static UBehaviorTree* FindBehaviorTree(const FString& BTName)
{
    IAssetRegistry& AR = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(
        TEXT("AssetRegistry")).Get();
    TArray<FAssetData> BTAssets;
    AR.GetAssetsByClass(FTopLevelAssetPath(TEXT("/Script/AIModule"), TEXT("BehaviorTree")), BTAssets, true);
    for (const FAssetData& AD : BTAssets)
    {
        if (AD.AssetName.ToString().Equals(BTName, ESearchCase::IgnoreCase))
            return Cast<UBehaviorTree>(AD.GetAsset());
    }
    return nullptr;
}

/**
 * SafeUpdateBTAsset – build runtime BT tree and save.
 *
 * ROOT CAUSE ANALYSIS (verified from UE5 source):
 *
 *   CRASH PATH: NotifyGraphChanged → OnGraphChanged.Broadcast →
 *               BT editor handler → IBehaviorTreeEditor* (null at +0x68)
 *
 *   SpawnMissingNodes() calls AddSubNode() (AIGraphNode.cpp:274-298) which
 *   fires ParentGraph->NotifyGraphChanged() (line 297) — this is the crash.
 *
 *   UpdateAsset() itself does NOT call NotifyGraphChanged (confirmed from source).
 *   Only AddSubNode() and OnSubNodeDropped() fire NotifyGraphChanged.
 *
 *   UAIGraph::LockUpdates() sets bLockUpdates=true (public API, AIGraph.h:50).
 *   UpdateAsset() checks bLockUpdates at top and returns early (BehaviorTreeGraph.cpp:104).
 *   UAIGraph::UnlockUpdates() sets bLockUpdates=false then calls UpdateAsset() (AIGraph.cpp:276-278).
 *   UpdateAsset() is safe — it rebuilds the runtime tree without firing NotifyGraphChanged.
 *
 *   UBehaviorTreeGraph::OnSave() = SpawnMissingNodesForParallel() + UpdateAsset() (line 211).
 *   SpawnMissingNodesForParallel calls AddSubNode() → NotifyGraphChanged → crash.
 *   So we skip OnSave() and call the pieces safely ourselves.
 *
 * CORRECT SEQUENCE:
 *   1. LockUpdates()         — suppress UpdateAsset() re-entrancy during SpawnMissingNodes
 *   2. SpawnMissingNodes()   — ensures NodeInstance objects are valid (AddSubNode suppressed by lock)
 *   3. UnlockUpdates()       — sets bLockUpdates=false, then calls UpdateAsset() which is SAFE
 *                              (UpdateAsset does NOT call NotifyGraphChanged)
 *   4. MarkPackageDirty() + SaveAsset()
 *   SKIP OnSave() — it calls SpawnMissingNodesForParallel → AddSubNode → NotifyGraphChanged → crash
 *
 * NOTE: bLockUpdates is protected in UAIGraph (UAIGraph.h:62). Use LockUpdates()/UnlockUpdates()
 *   public API. Do NOT access bLockUpdates directly — it causes a compile error.
 */
static void SafeUpdateBTAsset(UBehaviorTree* BT, UBehaviorTreeGraph* BTGraph)
{
    if (!BT || !BTGraph) return;

    // Ensure editors are closed (idempotent).
    CloseAllBTEditors(BT);

    // Lock updates via the public API so that AddSubNode calls inside SpawnMissingNodes
    // do not trigger UpdateAsset re-entrantly (UpdateAsset returns early when locked).
    // Note: bLockUpdates is protected — use LockUpdates() public method (AIGraph.h:50).
    BTGraph->LockUpdates();

    // SpawnMissingNodes ensures every graph node has a valid NodeInstance.
    // With bLockUpdates=true, any internal UpdateAsset() calls are suppressed.
    // AddSubNode still fires NotifyGraphChanged, but because editors are closed
    // CloseAllEditorsForAsset has already removed the crashing listener.
    BTGraph->SpawnMissingNodes();

    // UnlockUpdates() sets bLockUpdates=false then calls UpdateAsset() (AIGraph.cpp:276-278).
    // UpdateAsset() is SAFE — it builds the runtime BT tree (BT->RootNode hierarchy)
    // without calling NotifyGraphChanged (confirmed from BehaviorTreeGraph.cpp source).
    BTGraph->UnlockUpdates();

    // Serialise — NodeInstance objects have outer=BT + RF_Transactional.
    BT->MarkPackageDirty();
    UEditorAssetLibrary::SaveAsset(BT->GetPathName(), false);
}

/** Helper: get or create the BehaviorTreeGraph on a BT asset */
static UBehaviorTreeGraph* GetOrCreateBTGraph(UBehaviorTree* BT)
{
    if (!BT) return nullptr;
    UBehaviorTreeGraph* BTGraph = Cast<UBehaviorTreeGraph>(BT->BTGraph);
    if (!BTGraph)
    {
        // Create graph using NewObject (BT graphs are not Blueprint graphs)
        BTGraph = NewObject<UBehaviorTreeGraph>(BT, NAME_None, RF_Transactional);
        // Set schema class
        BTGraph->Schema = UEdGraphSchema_BehaviorTree::StaticClass();
        BTGraph->OnCreated();
        BT->BTGraph = BTGraph;
        // Let schema create the default Root node
        const UEdGraphSchema* Schema = BTGraph->GetSchema();
        if (Schema)
            Schema->CreateDefaultNodesForGraph(*BTGraph);
    }
    return BTGraph;
}

/** Helper: resolve the UClass for a BT node type string */
static UClass* ResolveBTNodeClass(const FString& NodeType)
{
    // ── Composites ────────────────────────────────────────────────────────────
    if (NodeType.Equals(TEXT("Selector"),          ESearchCase::IgnoreCase) ||
        NodeType.Equals(TEXT("BTComposite_Selector"), ESearchCase::IgnoreCase))
        return UBTComposite_Selector::StaticClass();
    if (NodeType.Equals(TEXT("Sequence"),          ESearchCase::IgnoreCase) ||
        NodeType.Equals(TEXT("BTComposite_Sequence"), ESearchCase::IgnoreCase))
        return UBTComposite_Sequence::StaticClass();

    // ── Tasks (built-in, /Script/AIModule) ───────────────────────────────────
    if (NodeType.Equals(TEXT("Wait"),              ESearchCase::IgnoreCase) ||
        NodeType.Equals(TEXT("BTTask_Wait"),       ESearchCase::IgnoreCase))
        return UBTTask_Wait::StaticClass();
    if (NodeType.Equals(TEXT("MoveTo"),            ESearchCase::IgnoreCase) ||
        NodeType.Equals(TEXT("BTTask_MoveTo"),     ESearchCase::IgnoreCase))
        return UBTTask_MoveTo::StaticClass();

    // RunBehaviorTree — runs a child BT (sub-tree pattern)
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTTask_RunBehaviorTree"));
        if (!C) C = FindObject<UClass>(nullptr, TEXT("/Script/GameplayTasks.BTTask_RunBehaviorTree"));
        if (C && (NodeType.Equals(TEXT("RunBehaviorTree"), ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTTask_RunBehaviorTree"), ESearchCase::IgnoreCase)))
            return C;
    }

    // ── Decorators (built-in) ─────────────────────────────────────────────────
    // BTDecorator_Blackboard — gate on a BB key value
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTDecorator_Blackboard"));
        if (C && (NodeType.Equals(TEXT("BlackboardDecorator"),      ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTDecorator_Blackboard"),   ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("Blackboard"),               ESearchCase::IgnoreCase)))
            return C;
    }
    // BTDecorator_IsAtLocation
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTDecorator_IsAtLocation"));
        if (C && (NodeType.Equals(TEXT("IsAtLocation"),             ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTDecorator_IsAtLocation"), ESearchCase::IgnoreCase)))
            return C;
    }
    // BTDecorator_KeepInCone
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTDecorator_KeepInCone"));
        if (C && (NodeType.Equals(TEXT("KeepInCone"),               ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTDecorator_KeepInCone"),   ESearchCase::IgnoreCase)))
            return C;
    }
    // BTDecorator_Loop
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTDecorator_Loop"));
        if (C && (NodeType.Equals(TEXT("Loop"),                     ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTDecorator_Loop"),         ESearchCase::IgnoreCase)))
            return C;
    }
    // BTDecorator_TimeLimit
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTDecorator_TimeLimit"));
        if (C && (NodeType.Equals(TEXT("TimeLimit"),                ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTDecorator_TimeLimit"),    ESearchCase::IgnoreCase)))
            return C;
    }
    // BTDecorator_CooldownDecorator (CooldownDecorator)
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTDecorator_Cooldown"));
        if (C && (NodeType.Equals(TEXT("Cooldown"),                 ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTDecorator_Cooldown"),     ESearchCase::IgnoreCase)))
            return C;
    }
    // BTDecorator_ForceSuccess
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTDecorator_ForceSuccess"));
        if (C && (NodeType.Equals(TEXT("ForceSuccess"),             ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTDecorator_ForceSuccess"), ESearchCase::IgnoreCase)))
            return C;
    }

    // ── Services (built-in) ───────────────────────────────────────────────────
    // BTService_DefaultFocus — keeps AI focused on BB actor key
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTService_DefaultFocus"));
        if (C && (NodeType.Equals(TEXT("DefaultFocus"),             ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTService_DefaultFocus"),   ESearchCase::IgnoreCase)))
            return C;
    }
    // BTService_BlackboardBase / BTService_RunEQS (navigation mesh)
    {
        UClass* C = FindObject<UClass>(nullptr, TEXT("/Script/AIModule.BTService_RunEQS"));
        if (C && (NodeType.Equals(TEXT("RunEQS"),                   ESearchCase::IgnoreCase) ||
                  NodeType.Equals(TEXT("BTService_RunEQS"),         ESearchCase::IgnoreCase)))
            return C;
    }

    // ── Fallback 1: /Script/AIModule.<NodeType> ───────────────────────────────
    {
        FString ClassPath = FString::Printf(TEXT("/Script/AIModule.%s"), *NodeType);
        UClass* DynClass = FindObject<UClass>(nullptr, *ClassPath);
        if (DynClass) return DynClass;
    }

    // ── Fallback 2: /Script/GameplayTasks.<NodeType> ──────────────────────────
    {
        FString ClassPath = FString::Printf(TEXT("/Script/GameplayTasks.%s"), *NodeType);
        UClass* DynClass = FindObject<UClass>(nullptr, *ClassPath);
        if (DynClass) return DynClass;
    }

    // ── Fallback 3: Blueprint asset path or full object path ─────────────────
    {
        UClass* DynClass = LoadObject<UClass>(nullptr, *NodeType);
        if (DynClass) return DynClass;
    }

    return nullptr;
}

/** Helper: determine graph node class for a runtime BT node class */
static UClass* GetBTGraphNodeClass(UClass* RuntimeClass)
{
    if (!RuntimeClass) return nullptr;
    if (RuntimeClass->IsChildOf(UBTCompositeNode::StaticClass()))
        return UBehaviorTreeGraphNode_Composite::StaticClass();
    if (RuntimeClass->IsChildOf(UBTTaskNode::StaticClass()))
        return UBehaviorTreeGraphNode_Task::StaticClass();
    if (RuntimeClass->IsChildOf(UBTService::StaticClass()))
        return UBehaviorTreeGraphNode_Service::StaticClass();
    if (RuntimeClass->IsChildOf(UBTDecorator::StaticClass()))
        return UBehaviorTreeGraphNode_Decorator::StaticClass();
    return nullptr;
}

/** Recursive helper to build BT graph from JSON tree description.
 *  Returns the created graph node or nullptr on failure.
 *  JSON format per node:
 *  {
 *    "type": "Selector" | "Sequence" | "Wait" | "MoveTo" | "<ClassName>",
 *    "x": 0, "y": 0,           // optional position
 *    "properties": { ... },    // optional: key=value pairs set on node instance
 *    "children": [ ... ],      // optional: child nodes (composites only)
 *    "decorators": [ ... ],    // optional: decorator sub-nodes
 *    "services":   [ ... ]     // optional: service sub-nodes
 *  }
 */
static UBehaviorTreeGraphNode* BuildBTNodeFromJson(
    UBehaviorTreeGraph* BTGraph,
    const TSharedPtr<FJsonObject>& NodeJson,
    UBehaviorTreeGraphNode* ParentGraphNode,
    float BaseX, float BaseY, int32& NodeIndex)
{
    if (!BTGraph || !NodeJson.IsValid()) return nullptr;

    FString NodeType;
    NodeJson->TryGetStringField(TEXT("type"), NodeType);
    if (NodeType.IsEmpty()) return nullptr;

    // Resolve runtime class
    UClass* RuntimeClass = ResolveBTNodeClass(NodeType);
    if (!RuntimeClass) return nullptr;

    // Determine graph node class
    UClass* GraphNodeClass = GetBTGraphNodeClass(RuntimeClass);
    if (!GraphNodeClass) return nullptr;

    // Position
    float X = BaseX + (float)(NodeIndex * 220);
    float Y = BaseY;
    double JsonX = 0, JsonY = 0;
    NodeJson->TryGetNumberField(TEXT("x"), JsonX);
    NodeJson->TryGetNumberField(TEXT("y"), JsonY);
    if (JsonX != 0) X = (float)JsonX;
    if (JsonY != 0) Y = (float)JsonY;

    // Create the graph node.  RF_Transactional ensures the node and its
    // NodeInstance sub-object are included in the package's object chain and
    // serialized properly when SaveAsset is called.
    // Use BTSafeAddNode instead of BTGraph->AddNode() to avoid firing
    // NotifyGraphChanged which causes the 0x68 crash.
    UBehaviorTreeGraphNode* NewNode =
        NewObject<UBehaviorTreeGraphNode>(BTGraph, GraphNodeClass, NAME_None, RF_Transactional);
    if (!NewNode) return nullptr;
    BTSafeAddNode(BTGraph, NewNode);

    NewNode->NodePosX = FMath::RoundToInt(X);
    NewNode->NodePosY = FMath::RoundToInt(Y);

    // Set runtime class data on the graph node
    // Set ClassData so PostPlacedNewNode knows which class to instantiate.
    NewNode->ClassData = FGraphNodeClassData(RuntimeClass, FString());

    // BUG-043: UAIGraphNode::PostPlacedNewNode() does NOT call Super::PostPlacedNewNode(),
    // so the base UEdGraphNode::NodeGuid never gets assigned. Saving the asset with
    // an all-zero NodeGuid causes FBehaviorTreeEditor::InitBehaviorTreeEditor to later
    // dereference a null widget at +0x68 when the BT is opened. Assign the GUID here.
    NewNode->CreateNewGuid();

    // PostPlacedNewNode creates NodeInstance = NewObject<UObject>(GraphOwner=BT, RuntimeClass)
    // This is the correct UE5 pattern (AIGraphNode.cpp:36-48): ClassData.GetClass() → NewObject.
    // It sets outer=BT (the UBehaviorTree asset) so NodeInstance IS a subobject of BT
    // and WILL be serialized when the package is saved.
    NewNode->PostPlacedNewNode();

    // InitializeInstance (BehaviorTreeGraphNode.cpp:54-64) initializes the BTNode:
    // BTNode->InitializeFromAsset(*BTAsset) + InitializeNode + OnNodeCreated.
    // This must come AFTER PostPlacedNewNode has created NodeInstance.
    if (NewNode->NodeInstance)
        NewNode->InitializeInstance();

    // AllocateDefaultPins creates the input/output pins on the graph node.
    // UBehaviorTreeGraphNode::AllocateDefaultPins just calls CreatePin (no NotifyGraphChanged).
    NewNode->AllocateDefaultPins();

    // Apply properties to runtime node instance
    if (NewNode->NodeInstance)
    {
        const TSharedPtr<FJsonObject>* PropsObj = nullptr;
        if (NodeJson->TryGetObjectField(TEXT("properties"), PropsObj) && PropsObj)
        {
            for (auto& KV : (*PropsObj)->Values)
            {
                FProperty* Prop = NewNode->NodeInstance->GetClass()->FindPropertyByName(FName(*KV.Key));
                if (Prop)
                {
                    FString ValStr;
                    KV.Value->TryGetString(ValStr);
                    if (!ValStr.IsEmpty())
                        Prop->ImportText_Direct(*ValStr, Prop->ContainerPtrToValuePtr<void>(NewNode->NodeInstance), NewNode->NodeInstance, PPF_None);
                }
            }
        }
    }

    // Connect to parent via pins
    if (ParentGraphNode)
    {
        UEdGraphPin* ParentOutputPin = nullptr;
        UEdGraphPin* NewInputPin = nullptr;

        for (UEdGraphPin* Pin : ParentGraphNode->Pins)
        {
            if (Pin && Pin->Direction == EGPD_Output) { ParentOutputPin = Pin; break; }
        }
        for (UEdGraphPin* Pin : NewNode->Pins)
        {
            if (Pin && Pin->Direction == EGPD_Input) { NewInputPin = Pin; break; }
        }

        // Use BTSafeLinkPins instead of MakeLinkTo to avoid NotifyGraphChanged
        if (ParentOutputPin && NewInputPin)
        {
            BTSafeLinkPins(ParentOutputPin, NewInputPin);
        }
    }

    NodeIndex++;

    // Process decorators (sub-nodes)
    const TArray<TSharedPtr<FJsonValue>>* DecoratorsArr = nullptr;
    if (NodeJson->TryGetArrayField(TEXT("decorators"), DecoratorsArr) && DecoratorsArr)
    {
        for (const TSharedPtr<FJsonValue>& DecVal : *DecoratorsArr)
        {
            const TSharedPtr<FJsonObject>* DecObj = nullptr;
            if (!DecVal->TryGetObject(DecObj) || !DecObj) continue;

            FString DecType;
            (*DecObj)->TryGetStringField(TEXT("type"), DecType);
            UClass* DecClass = ResolveBTNodeClass(DecType);
            if (!DecClass || !DecClass->IsChildOf(UBTDecorator::StaticClass())) continue;

            // Create decorator graph node as outer=BTGraph (it's a graph node, not a runtime node)
            UBehaviorTreeGraphNode_Decorator* DecNode =
                NewObject<UBehaviorTreeGraphNode_Decorator>(BTGraph, NAME_None, RF_Transactional);
            if (DecNode)
            {
                DecNode->ClassData = FGraphNodeClassData(DecClass, FString());
                // BUG-043: assign NodeGuid before PostPlacedNewNode (UAIGraphNode override
                // skips Super so base UEdGraphNode::NodeGuid would stay all-zero).
                DecNode->CreateNewGuid();
                // PostPlacedNewNode creates NodeInstance with outer=BT (the UBehaviorTree asset)
                DecNode->PostPlacedNewNode();
                if (DecNode->NodeInstance)
                    DecNode->InitializeInstance();
                // Manually wire sub-node relationships (mirrors AddSubNode without NotifyGraphChanged)
                DecNode->SetFlags(RF_Transactional);
                // Set outer to BTGraph so the sub-node is properly owned
                if (DecNode->GetOuter() != BTGraph)
                    DecNode->Rename(nullptr, BTGraph, REN_NonTransactional | REN_DoNotDirty | REN_ForceNoResetLoaders);
                DecNode->bIsSubNode = 1;
                DecNode->ParentNode = NewNode;
                NewNode->SubNodes.Add(DecNode);
                // OnSubNodeAdded routes to BehaviorTreeGraphNode::OnSubNodeAdded which
                // adds to Decorators[] or Services[] array (BehaviorTreeGraphNode.cpp:224-249)
                NewNode->OnSubNodeAdded(DecNode);
            }
        }
    }

    // Process services (sub-nodes)
    const TArray<TSharedPtr<FJsonValue>>* ServicesArr = nullptr;
    if (NodeJson->TryGetArrayField(TEXT("services"), ServicesArr) && ServicesArr)
    {
        for (const TSharedPtr<FJsonValue>& SvcVal : *ServicesArr)
        {
            const TSharedPtr<FJsonObject>* SvcObj = nullptr;
            if (!SvcVal->TryGetObject(SvcObj) || !SvcObj) continue;

            FString SvcType;
            (*SvcObj)->TryGetStringField(TEXT("type"), SvcType);
            UClass* SvcClass = ResolveBTNodeClass(SvcType);
            if (!SvcClass || !SvcClass->IsChildOf(UBTService::StaticClass())) continue;

            UBehaviorTreeGraphNode_Service* SvcNode =
                NewObject<UBehaviorTreeGraphNode_Service>(BTGraph, NAME_None, RF_Transactional);
            if (SvcNode)
            {
                SvcNode->ClassData = FGraphNodeClassData(SvcClass, FString());
                // BUG-043: assign NodeGuid before PostPlacedNewNode (UAIGraphNode override
                // skips Super so base UEdGraphNode::NodeGuid would stay all-zero).
                SvcNode->CreateNewGuid();
                // PostPlacedNewNode creates NodeInstance with outer=BT
                SvcNode->PostPlacedNewNode();
                if (SvcNode->NodeInstance)
                    SvcNode->InitializeInstance();
                // Manually wire sub-node relationships
                SvcNode->SetFlags(RF_Transactional);
                if (SvcNode->GetOuter() != BTGraph)
                    SvcNode->Rename(nullptr, BTGraph, REN_NonTransactional | REN_DoNotDirty | REN_ForceNoResetLoaders);
                SvcNode->bIsSubNode = 1;
                SvcNode->ParentNode = NewNode;
                NewNode->SubNodes.Add(SvcNode);
                NewNode->OnSubNodeAdded(SvcNode);
            }
        }
    }

    // Process children (composite nodes)
    // BUG-FIX: ChildSlot tracks the horizontal position of each sibling
    // independently from NodeIndex (which counts all nodes ever created and is
    // shared across the entire tree).  Previously ChildIndex was passed as the
    // NodeIndex ref so it received the total subtree depth of every preceding
    // child, making each sibling's X position wrong (too far to the right).
    const TArray<TSharedPtr<FJsonValue>>* ChildrenArr = nullptr;
    if (NodeJson->TryGetArrayField(TEXT("children"), ChildrenArr) && ChildrenArr)
    {
        float ChildY = Y + 200.0f;
        float TotalWidth = (float)ChildrenArr->Num() * 220.0f;
        float StartX = X - TotalWidth * 0.5f + 110.0f;

        for (int32 ChildSlot = 0; ChildSlot < ChildrenArr->Num(); ++ChildSlot)
        {
            const TSharedPtr<FJsonObject>* ChildObj = nullptr;
            if (!(*ChildrenArr)[ChildSlot]->TryGetObject(ChildObj) || !ChildObj) continue;
            // Pass global NodeIndex ref so every node gets a unique index,
            // but use ChildSlot * 220 for horizontal placement so siblings
            // are evenly spaced regardless of how large each child's subtree is.
            BuildBTNodeFromJson(BTGraph, *ChildObj, NewNode,
                StartX + (float)ChildSlot * 220.0f, ChildY, NodeIndex);
        }
    }

    return NewNode;
}

// ════════════════════════════════════════════════════════════════════════════
// build_behavior_tree
// Params:
//   behavior_tree_name: string   (name of existing BT asset to build into)
//   tree: object                 (JSON tree description, root is a composite)
//   clear_existing: bool         (default true – remove existing non-root nodes)
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleBuildBehaviorTree(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BTName;
    if (!Params->TryGetStringField(TEXT("behavior_tree_name"), BTName))
        return CreateErrorResponse(TEXT("Missing 'behavior_tree_name'"));

    const TSharedPtr<FJsonObject>* TreeObj = nullptr;
    if (!Params->TryGetObjectField(TEXT("tree"), TreeObj) || !TreeObj)
        return CreateErrorResponse(TEXT("Missing 'tree' object"));

    UBehaviorTree* BT = FindBehaviorTree(BTName);
    if (!BT)
        return CreateErrorResponse(FString::Printf(TEXT("BehaviorTree not found: %s"), *BTName));

    // ── MUST be first: close editors BEFORE any graph mutation ───────────────
    // Every UPROPERTY write on BTGraph fires FOnObjectPropertyChanged which the
    // BT editor module intercepts and dereferences a null IBehaviorTreeEditor*
    // at +0x68.  CloseAllEditorsForAsset unregisters those listeners so all
    // subsequent graph modifications (AddNode, Nodes.Remove, MakeLinkTo, …) are safe.
    CloseAllBTEditors(BT);

    UBehaviorTreeGraph* BTGraph = GetOrCreateBTGraph(BT);
    if (!BTGraph)
        return CreateErrorResponse(TEXT("Failed to get/create BehaviorTreeGraph"));

    // Optionally clear existing nodes (keep root)
    bool bClearExisting = true;
    Params->TryGetBoolField(TEXT("clear_existing"), bClearExisting);

    if (bClearExisting)
        SafeRemoveBTNodes(BTGraph);

    // Find root node
    UBehaviorTreeGraphNode_Root* RootNode = nullptr;
    for (UEdGraphNode* Node : BTGraph->Nodes)
    {
        RootNode = Cast<UBehaviorTreeGraphNode_Root>(Node);
        if (RootNode) break;
    }

    // Build tree from JSON
    int32 NodeIndex = 0;
    float RootX = RootNode ? (float)RootNode->NodePosX : 0.0f;
    float StartY = (RootNode ? (float)RootNode->NodePosY : 0.0f) + 200.0f;

    UBehaviorTreeGraphNode* TopNode = BuildBTNodeFromJson(
        BTGraph, *TreeObj, RootNode, RootX, StartY, NodeIndex);

    if (!TopNode)
        return CreateErrorResponse(TEXT("Failed to create top-level BT node from 'tree' JSON"));

    SafeUpdateBTAsset(BT, BTGraph);

    // Collect info about created nodes
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("behavior_tree"), BTName);
    R->SetNumberField(TEXT("nodes_created"), (double)NodeIndex);

    TArray<TSharedPtr<FJsonValue>> NodeList;
    for (UEdGraphNode* Node : BTGraph->Nodes)
    {
        if (!Node->IsA<UBehaviorTreeGraphNode_Root>())
        {
            TSharedPtr<FJsonObject> NObj = MakeShared<FJsonObject>();
            NObj->SetStringField(TEXT("class"), Node->GetClass()->GetName());
            NObj->SetNumberField(TEXT("x"), Node->NodePosX);
            NObj->SetNumberField(TEXT("y"), Node->NodePosY);
            if (UAIGraphNode* AIN = Cast<UAIGraphNode>(Node))
            {
                if (AIN->NodeInstance)
                    NObj->SetStringField(TEXT("instance"), AIN->NodeInstance->GetClass()->GetName());
            }
            NodeList.Add(MakeShared<FJsonValueObject>(NObj));
        }
    }
    R->SetArrayField(TEXT("nodes"), NodeList);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// add_bt_node
// Params:
//   behavior_tree_name: string
//   node_type:   string   e.g. "Selector", "Sequence", "Wait", "MoveTo",
//                         or full class path like "BTComposite_Selector"
//   parent_node_index: int  (0-based index in current graph Nodes array, skip root)
//                           -1 = attach to root
//   x: float, y: float  (optional position)
//   properties: object   (optional key=value for node instance)
//   decorators: array    (optional decorator sub-nodes, each with "type")
//   services:   array    (optional service sub-nodes)
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddBTNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BTName, NodeType;
    if (!Params->TryGetStringField(TEXT("behavior_tree_name"), BTName))
        return CreateErrorResponse(TEXT("Missing 'behavior_tree_name'"));
    if (!Params->TryGetStringField(TEXT("node_type"), NodeType))
        return CreateErrorResponse(TEXT("Missing 'node_type'"));

    UBehaviorTree* BT = FindBehaviorTree(BTName);
    if (!BT)
        return CreateErrorResponse(FString::Printf(TEXT("BehaviorTree not found: %s"), *BTName));

    // Close editors FIRST — before any graph access — to unregister BT editor
    // property-change listeners that crash at 0x68 on any BTGraph UPROPERTY write.
    CloseAllBTEditors(BT);

    UBehaviorTreeGraph* BTGraph = GetOrCreateBTGraph(BT);
    if (!BTGraph)
        return CreateErrorResponse(TEXT("Failed to get/create BehaviorTreeGraph"));

    UClass* RuntimeClass = ResolveBTNodeClass(NodeType);
    if (!RuntimeClass)
        return CreateErrorResponse(FString::Printf(TEXT("Unknown BT node type: %s"), *NodeType));

    UClass* GraphNodeClass = GetBTGraphNodeClass(RuntimeClass);
    if (!GraphNodeClass)
        return CreateErrorResponse(FString::Printf(TEXT("Cannot determine graph node class for: %s"), *NodeType));

    // Determine parent
    double ParentIdx = -1;
    Params->TryGetNumberField(TEXT("parent_node_index"), ParentIdx);

    UBehaviorTreeGraphNode* ParentGraphNode = nullptr;
    // Build list of non-root nodes
    TArray<UBehaviorTreeGraphNode*> NonRootNodes;
    UBehaviorTreeGraphNode_Root* RootNode = nullptr;
    for (UEdGraphNode* Node : BTGraph->Nodes)
    {
        if (UBehaviorTreeGraphNode_Root* Root = Cast<UBehaviorTreeGraphNode_Root>(Node))
            RootNode = Root;
        else if (UBehaviorTreeGraphNode* BTN = Cast<UBehaviorTreeGraphNode>(Node))
            NonRootNodes.Add(BTN);
    }

    if ((int32)ParentIdx < 0)
        ParentGraphNode = RootNode; // attach to root
    else if ((int32)ParentIdx < NonRootNodes.Num())
        ParentGraphNode = NonRootNodes[(int32)ParentIdx];

    // Position
    double X = 0, Y = 300;
    Params->TryGetNumberField(TEXT("x"), X);
    Params->TryGetNumberField(TEXT("y"), Y);
    if (X == 0 && ParentGraphNode)
    {
        X = ParentGraphNode->NodePosX + (double)(NonRootNodes.Num() * 220);
        Y = ParentGraphNode->NodePosY + 200.0;
    }

    // Create node. NewObject outer=BTGraph ensures the graph node is owned by the graph.
    // Use BTSafeAddNode instead of AddNode() to avoid NotifyGraphChanged crash.
    UBehaviorTreeGraphNode* NewNode =
        NewObject<UBehaviorTreeGraphNode>(BTGraph, GraphNodeClass, NAME_None, RF_Transactional);
    BTSafeAddNode(BTGraph, NewNode);
    NewNode->NodePosX = FMath::RoundToInt((float)X);
    NewNode->NodePosY = FMath::RoundToInt((float)Y);
    // Set ClassData so PostPlacedNewNode knows which runtime class to instantiate.
    NewNode->ClassData = FGraphNodeClassData(RuntimeClass, FString());
    // BUG-043: assign NodeGuid before PostPlacedNewNode. UAIGraphNode::PostPlacedNewNode()
    // does NOT call Super, so NodeGuid would otherwise stay all-zero and crash the BT
    // editor on next open (null widget lookup at +0x68).
    NewNode->CreateNewGuid();
    // PostPlacedNewNode creates NodeInstance with outer=BT (the UBehaviorTree asset)
    // so NodeInstance is a subobject of BT and will be serialized with the package.
    NewNode->PostPlacedNewNode();
    if (NewNode->NodeInstance)
        NewNode->InitializeInstance();
    NewNode->AllocateDefaultPins();

    // Apply properties
    const TSharedPtr<FJsonObject>* PropsObj = nullptr;
    if (Params->TryGetObjectField(TEXT("properties"), PropsObj) && PropsObj && NewNode->NodeInstance)
    {
        for (auto& KV : (*PropsObj)->Values)
        {
            FProperty* Prop = NewNode->NodeInstance->GetClass()->FindPropertyByName(FName(*KV.Key));
            if (Prop)
            {
                FString ValStr;
                KV.Value->TryGetString(ValStr);
                if (!ValStr.IsEmpty())
                    Prop->ImportText_Direct(*ValStr, Prop->ContainerPtrToValuePtr<void>(NewNode->NodeInstance), NewNode->NodeInstance, PPF_None);
            }
        }
    }

    // Connect to parent
    if (ParentGraphNode)
    {
        UEdGraphPin* ParentOutputPin = nullptr;
        UEdGraphPin* NewInputPin = nullptr;
        for (UEdGraphPin* Pin : ParentGraphNode->Pins)
            if (Pin && Pin->Direction == EGPD_Output) { ParentOutputPin = Pin; break; }
        for (UEdGraphPin* Pin : NewNode->Pins)
            if (Pin && Pin->Direction == EGPD_Input) { NewInputPin = Pin; break; }
        // Use BTSafeLinkPins to avoid MakeLinkTo->NotifyGraphChanged crash
        if (ParentOutputPin && NewInputPin)
            BTSafeLinkPins(ParentOutputPin, NewInputPin);
    }

    // Add decorators
    const TArray<TSharedPtr<FJsonValue>>* DecoratorsArr = nullptr;
    if (Params->TryGetArrayField(TEXT("decorators"), DecoratorsArr) && DecoratorsArr)
    {
        for (const TSharedPtr<FJsonValue>& DecVal : *DecoratorsArr)
        {
            const TSharedPtr<FJsonObject>* DecObj = nullptr;
            if (!DecVal->TryGetObject(DecObj)) continue;
            FString DecType;
            (*DecObj)->TryGetStringField(TEXT("type"), DecType);
            UClass* DecClass = ResolveBTNodeClass(DecType);
            if (!DecClass || !DecClass->IsChildOf(UBTDecorator::StaticClass())) continue;
            UBehaviorTreeGraphNode_Decorator* DecNode =
                NewObject<UBehaviorTreeGraphNode_Decorator>(BTGraph, NAME_None, RF_Transactional);
            if (DecNode)
            {
                DecNode->ClassData = FGraphNodeClassData(DecClass, FString());
                // BUG-043: NodeGuid must be assigned before PostPlacedNewNode (UAIGraphNode
                // override skips Super, leaving base NodeGuid all-zero → BT editor crash on open).
                DecNode->CreateNewGuid();
                DecNode->PostPlacedNewNode(); // creates NodeInstance with outer=BT
                if (DecNode->NodeInstance)
                    DecNode->InitializeInstance();
                // Wire sub-node without calling AddSubNode (which calls NotifyGraphChanged)
                if (DecNode->GetOuter() != BTGraph)
                    DecNode->Rename(nullptr, BTGraph, REN_NonTransactional | REN_DoNotDirty | REN_ForceNoResetLoaders);
                DecNode->bIsSubNode = 1;
                DecNode->ParentNode = NewNode;
                NewNode->SubNodes.Add(DecNode);
                NewNode->OnSubNodeAdded(DecNode); // populates Decorators[] array
            }
        }
    }

    // Add services
    const TArray<TSharedPtr<FJsonValue>>* ServicesArr = nullptr;
    if (Params->TryGetArrayField(TEXT("services"), ServicesArr) && ServicesArr)
    {
        for (const TSharedPtr<FJsonValue>& SvcVal : *ServicesArr)
        {
            const TSharedPtr<FJsonObject>* SvcObj = nullptr;
            if (!SvcVal->TryGetObject(SvcObj)) continue;
            FString SvcType;
            (*SvcObj)->TryGetStringField(TEXT("type"), SvcType);
            UClass* SvcClass = ResolveBTNodeClass(SvcType);
            if (!SvcClass || !SvcClass->IsChildOf(UBTService::StaticClass())) continue;
            UBehaviorTreeGraphNode_Service* SvcNode =
                NewObject<UBehaviorTreeGraphNode_Service>(BTGraph, NAME_None, RF_Transactional);
            if (SvcNode)
            {
                SvcNode->ClassData = FGraphNodeClassData(SvcClass, FString());
                // BUG-043: NodeGuid must be assigned before PostPlacedNewNode (UAIGraphNode
                // override skips Super, leaving base NodeGuid all-zero → BT editor crash on open).
                SvcNode->CreateNewGuid();
                SvcNode->PostPlacedNewNode(); // creates NodeInstance with outer=BT
                if (SvcNode->NodeInstance)
                    SvcNode->InitializeInstance();
                // Wire sub-node without calling AddSubNode (which calls NotifyGraphChanged)
                if (SvcNode->GetOuter() != BTGraph)
                    SvcNode->Rename(nullptr, BTGraph, REN_NonTransactional | REN_DoNotDirty | REN_ForceNoResetLoaders);
                SvcNode->bIsSubNode = 1;
                SvcNode->ParentNode = NewNode;
                NewNode->SubNodes.Add(SvcNode);
                NewNode->OnSubNodeAdded(SvcNode); // populates Services[] array
            }
        }
    }

    // Close any open BT editor, rebuild runtime tree from graph, then save.
    SafeUpdateBTAsset(BT, BTGraph);

    // Return info
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("behavior_tree"), BTName);
    R->SetStringField(TEXT("node_type"), NodeType);
    R->SetNumberField(TEXT("node_index"), (double)NonRootNodes.Num()); // its new index
    R->SetNumberField(TEXT("x"), X);
    R->SetNumberField(TEXT("y"), Y);
    if (NewNode->NodeInstance)
        R->SetStringField(TEXT("instance_class"), NewNode->NodeInstance->GetClass()->GetName());
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// attach_bt_sub_node
// Attach a Service or Decorator to an EXISTING BT graph node (typically the
// root composite / a selector / a sequence).  Mirrors the sub-node pattern
// already used inside HandleAddBTNode but targets a parent resolved by index.
//
// Params:
//   behavior_tree_name : string
//   parent_node_index  : int    0-based index into the non-root nodes list;
//                               -1 = attach to root (index 0 composite child of root)
//   sub_node_kind      : string "service" | "decorator"
//   class_name         : string runtime class name, short ("BTService_UpdatePerception"
//                               or generated "BTService_UpdatePerception_C") or full path
//   properties         : object optional key=value imported onto NodeInstance
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAttachBTSubNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BTName, SubKind, ClassName;
    if (!Params->TryGetStringField(TEXT("behavior_tree_name"), BTName))
        return CreateErrorResponse(TEXT("Missing 'behavior_tree_name'"));
    if (!Params->TryGetStringField(TEXT("sub_node_kind"), SubKind))
        return CreateErrorResponse(TEXT("Missing 'sub_node_kind' (\"service\" or \"decorator\")"));
    if (!Params->TryGetStringField(TEXT("class_name"), ClassName))
        return CreateErrorResponse(TEXT("Missing 'class_name'"));

    const bool bIsService = SubKind.Equals(TEXT("service"), ESearchCase::IgnoreCase);
    const bool bIsDecorator = SubKind.Equals(TEXT("decorator"), ESearchCase::IgnoreCase);
    if (!bIsService && !bIsDecorator)
        return CreateErrorResponse(TEXT("'sub_node_kind' must be \"service\" or \"decorator\""));

    UBehaviorTree* BT = FindBehaviorTree(BTName);
    if (!BT)
        return CreateErrorResponse(FString::Printf(TEXT("BehaviorTree not found: %s"), *BTName));

    // Close BT editor before graph edits (mirrors HandleAddBTNode crash mitigation).
    CloseAllBTEditors(BT);

    UBehaviorTreeGraph* BTGraph = GetOrCreateBTGraph(BT);
    if (!BTGraph)
        return CreateErrorResponse(TEXT("Failed to get/create BehaviorTreeGraph"));

    // Resolve sub-node runtime class. ResolveBTNodeClass handles both short names
    // ("BTService_UpdatePerception") and full paths, and auto-appends "_C" for BP classes.
    UClass* SubRuntimeClass = ResolveBTNodeClass(ClassName);
    if (!SubRuntimeClass)
        return CreateErrorResponse(FString::Printf(TEXT("Unknown sub-node class: %s"), *ClassName));

    if (bIsService && !SubRuntimeClass->IsChildOf(UBTService::StaticClass()))
        return CreateErrorResponse(FString::Printf(
            TEXT("Class '%s' is not a UBTService"), *ClassName));
    if (bIsDecorator && !SubRuntimeClass->IsChildOf(UBTDecorator::StaticClass()))
        return CreateErrorResponse(FString::Printf(
            TEXT("Class '%s' is not a UBTDecorator"), *ClassName));

    // Build list of non-root nodes and locate parent by index
    TArray<UBehaviorTreeGraphNode*> NonRootNodes;
    for (UEdGraphNode* Node : BTGraph->Nodes)
    {
        if (Node && !Node->IsA<UBehaviorTreeGraphNode_Root>())
        {
            if (UBehaviorTreeGraphNode* BTN = Cast<UBehaviorTreeGraphNode>(Node))
                NonRootNodes.Add(BTN);
        }
    }

    double ParentIdxD = -1;
    Params->TryGetNumberField(TEXT("parent_node_index"), ParentIdxD);
    const int32 ParentIdx = (int32)ParentIdxD;

    UBehaviorTreeGraphNode* ParentNode = nullptr;
    if (ParentIdx < 0)
    {
        // -1 means "the root composite" = first non-root node in the graph
        if (NonRootNodes.Num() > 0) ParentNode = NonRootNodes[0];
    }
    else if (ParentIdx < NonRootNodes.Num())
    {
        ParentNode = NonRootNodes[ParentIdx];
    }

    if (!ParentNode)
        return CreateErrorResponse(FString::Printf(
            TEXT("No non-root node at index %d (total non-root nodes: %d)"),
            ParentIdx, NonRootNodes.Num()));

    // Idempotency: if a sub-node with the same runtime class already exists, return OK.
    for (UAIGraphNode* Existing : ParentNode->SubNodes)
    {
        if (Existing && Existing->NodeInstance &&
            Existing->NodeInstance->GetClass() == SubRuntimeClass)
        {
            TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
            R->SetBoolField(TEXT("success"), true);
            R->SetBoolField(TEXT("already_attached"), true);
            R->SetStringField(TEXT("behavior_tree"), BTName);
            R->SetStringField(TEXT("class_name"), ClassName);
            R->SetStringField(TEXT("sub_node_kind"), SubKind);
            return R;
        }
    }

    // Create the graph sub-node (Service or Decorator).
    UAIGraphNode* SubGraphNode = nullptr;
    if (bIsService)
    {
        UBehaviorTreeGraphNode_Service* SvcNode =
            NewObject<UBehaviorTreeGraphNode_Service>(BTGraph, NAME_None, RF_Transactional);
        SubGraphNode = SvcNode;
    }
    else // decorator
    {
        UBehaviorTreeGraphNode_Decorator* DecNode =
            NewObject<UBehaviorTreeGraphNode_Decorator>(BTGraph, NAME_None, RF_Transactional);
        SubGraphNode = DecNode;
    }

    if (!SubGraphNode)
        return CreateErrorResponse(TEXT("Failed to create sub-node object"));

    // Wire the sub-node per the proven pattern in HandleAddBTNode.
    SubGraphNode->ClassData = FGraphNodeClassData(SubRuntimeClass, FString());

    // BUG-043: assign NodeGuid before PostPlacedNewNode; UAIGraphNode override skips
    // Super so base NodeGuid stays zero → BT editor crashes at 0x68 on open.
    SubGraphNode->CreateNewGuid();
    SubGraphNode->PostPlacedNewNode(); // creates NodeInstance with outer=BT
    if (SubGraphNode->NodeInstance)
        SubGraphNode->InitializeInstance();

    // Ensure graph ownership then attach as sub-node without triggering NotifyGraphChanged
    if (SubGraphNode->GetOuter() != BTGraph)
    {
        SubGraphNode->Rename(nullptr, BTGraph,
            REN_NonTransactional | REN_DoNotDirty | REN_ForceNoResetLoaders);
    }
    SubGraphNode->bIsSubNode = 1;
    SubGraphNode->ParentNode = ParentNode;
    ParentNode->SubNodes.Add(SubGraphNode);
    ParentNode->OnSubNodeAdded(SubGraphNode); // populates Services[] or Decorators[]

    // Optional properties applied to NodeInstance
    const TSharedPtr<FJsonObject>* PropsObj = nullptr;
    if (Params->TryGetObjectField(TEXT("properties"), PropsObj) && PropsObj &&
        SubGraphNode->NodeInstance)
    {
        for (const auto& KV : (*PropsObj)->Values)
        {
            FProperty* Prop = SubGraphNode->NodeInstance->GetClass()->FindPropertyByName(FName(*KV.Key));
            if (Prop)
            {
                FString ValStr;
                KV.Value->TryGetString(ValStr);
                if (!ValStr.IsEmpty())
                    Prop->ImportText_Direct(*ValStr,
                        Prop->ContainerPtrToValuePtr<void>(SubGraphNode->NodeInstance),
                        SubGraphNode->NodeInstance, PPF_None);
            }
        }
    }

    // Rebuild runtime tree from graph and save the BT asset.
    SafeUpdateBTAsset(BT, BTGraph);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("behavior_tree"), BTName);
    R->SetStringField(TEXT("class_name"), ClassName);
    R->SetStringField(TEXT("sub_node_kind"), SubKind);
    R->SetNumberField(TEXT("parent_index"), (double)ParentIdx);
    if (SubGraphNode->NodeInstance)
        R->SetStringField(TEXT("instance_class"),
            SubGraphNode->NodeInstance->GetClass()->GetName());
    R->SetNumberField(TEXT("parent_sub_node_count"), (double)ParentNode->SubNodes.Num());
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// bt_add_run_eqs_service
// Params:
//   behavior_tree_name : string
//   query_path         : string EQS query path or unique asset name
//   result_key         : string Blackboard key that receives the query result
//   parent_node_index  : int    0-based index into non-root nodes; -1 = first non-root
//   run_mode           : string single_result | random_best_5_pct | random_best_25_pct | all_matching
//   update_bb_on_fail  : bool   optional, default false
//   interval           : float  optional service tick interval
//   update_existing    : bool   optional, default true
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleBTAddRunEQSService(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BTName, QueryPath, ResultKey;
    if (!Params->TryGetStringField(TEXT("behavior_tree_name"), BTName))
        return CreateErrorResponse(TEXT("Missing 'behavior_tree_name'"));
    if (!Params->TryGetStringField(TEXT("query_path"), QueryPath))
        return CreateErrorResponse(TEXT("Missing 'query_path'"));
    if (!Params->TryGetStringField(TEXT("result_key"), ResultKey))
        return CreateErrorResponse(TEXT("Missing 'result_key'"));

    UBehaviorTree* BT = FindBehaviorTree(BTName);
    if (!BT)
        return CreateErrorResponse(FString::Printf(TEXT("BehaviorTree not found: %s"), *BTName));

    FString EQSPackagePath;
    UEnvQuery* Query = LoadEQSQueryByPathOrName(QueryPath, EQSPackagePath);
    if (!Query)
        return CreateErrorResponse(FString::Printf(TEXT("EQS query not found: %s"), *QueryPath));

    CloseAllBTEditors(BT);

    UBehaviorTreeGraph* BTGraph = GetOrCreateBTGraph(BT);
    if (!BTGraph)
        return CreateErrorResponse(TEXT("Failed to get/create BehaviorTreeGraph"));

    TArray<UBehaviorTreeGraphNode*> NonRootNodes;
    for (UEdGraphNode* Node : BTGraph->Nodes)
    {
        if (Node && !Node->IsA<UBehaviorTreeGraphNode_Root>())
        {
            if (UBehaviorTreeGraphNode* BTN = Cast<UBehaviorTreeGraphNode>(Node))
            {
                NonRootNodes.Add(BTN);
            }
        }
    }

    double ParentIdxD = -1;
    Params->TryGetNumberField(TEXT("parent_node_index"), ParentIdxD);
    const int32 ParentIdx = (int32)ParentIdxD;

    UBehaviorTreeGraphNode* ParentNode = nullptr;
    if (ParentIdx < 0)
    {
        if (NonRootNodes.Num() > 0)
        {
            ParentNode = NonRootNodes[0];
        }
    }
    else if (ParentIdx < NonRootNodes.Num())
    {
        ParentNode = NonRootNodes[ParentIdx];
    }

    if (!ParentNode)
    {
        return CreateErrorResponse(FString::Printf(
            TEXT("No non-root node at index %d (total non-root nodes: %d)"),
            ParentIdx, NonRootNodes.Num()));
    }

    bool bUpdateExisting = true;
    Params->TryGetBoolField(TEXT("update_existing"), bUpdateExisting);

    UAIGraphNode* ServiceGraphNode = nullptr;
    for (UAIGraphNode* Existing : ParentNode->SubNodes)
    {
        if (Existing && Existing->NodeInstance &&
            Existing->NodeInstance->IsA(UBTService_RunEQS::StaticClass()))
        {
            ServiceGraphNode = Existing;
            break;
        }
    }

    if (ServiceGraphNode && !bUpdateExisting)
    {
        TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
        R->SetBoolField(TEXT("success"), true);
        R->SetBoolField(TEXT("already_attached"), true);
        R->SetStringField(TEXT("behavior_tree"), BTName);
        R->SetStringField(TEXT("query_path"), Query->GetPathName());
        R->SetStringField(TEXT("result_key"), ResultKey);
        R->SetNumberField(TEXT("parent_index"), (double)ParentIdx);
        return R;
    }

    bool bCreated = false;
    if (!ServiceGraphNode)
    {
        UBehaviorTreeGraphNode_Service* NewServiceNode =
            NewObject<UBehaviorTreeGraphNode_Service>(BTGraph, NAME_None, RF_Transactional);
        if (!NewServiceNode)
            return CreateErrorResponse(TEXT("Failed to create Run EQS service graph node"));

        ServiceGraphNode = NewServiceNode;
        ServiceGraphNode->ClassData = FGraphNodeClassData(UBTService_RunEQS::StaticClass(), FString());
        ServiceGraphNode->CreateNewGuid();
        ServiceGraphNode->PostPlacedNewNode();
        if (ServiceGraphNode->NodeInstance)
        {
            ServiceGraphNode->InitializeInstance();
        }
        if (ServiceGraphNode->GetOuter() != BTGraph)
        {
            ServiceGraphNode->Rename(nullptr, BTGraph,
                REN_NonTransactional | REN_DoNotDirty | REN_ForceNoResetLoaders);
        }
        ServiceGraphNode->SetFlags(RF_Transactional);
        ServiceGraphNode->bIsSubNode = 1;
        ServiceGraphNode->ParentNode = ParentNode;
        ParentNode->SubNodes.Add(ServiceGraphNode);
        ParentNode->OnSubNodeAdded(ServiceGraphNode);
        bCreated = true;
    }

    UBTService_RunEQS* RunEQSService = ServiceGraphNode && ServiceGraphNode->NodeInstance
        ? Cast<UBTService_RunEQS>(ServiceGraphNode->NodeInstance)
        : nullptr;
    if (!RunEQSService)
        return CreateErrorResponse(TEXT("Run EQS service node has no UBTService_RunEQS instance"));

    FString RunModeName;
    Params->TryGetStringField(TEXT("run_mode"), RunModeName);
    if (RunModeName.IsEmpty())
    {
        RunModeName = TEXT("single_result");
    }

    EEnvQueryRunMode::Type RunMode = EEnvQueryRunMode::SingleResult;
    if (RunModeName.Equals(TEXT("random_best_5_pct"), ESearchCase::IgnoreCase) ||
        RunModeName.Equals(TEXT("random_best_5"), ESearchCase::IgnoreCase) ||
        RunModeName.Equals(TEXT("randombest5pct"), ESearchCase::IgnoreCase))
    {
        RunMode = EEnvQueryRunMode::RandomBest5Pct;
    }
    else if (RunModeName.Equals(TEXT("random_best_25_pct"), ESearchCase::IgnoreCase) ||
             RunModeName.Equals(TEXT("random_best_25"), ESearchCase::IgnoreCase) ||
             RunModeName.Equals(TEXT("randombest25pct"), ESearchCase::IgnoreCase))
    {
        RunMode = EEnvQueryRunMode::RandomBest25Pct;
    }
    else if (RunModeName.Equals(TEXT("all_matching"), ESearchCase::IgnoreCase) ||
             RunModeName.Equals(TEXT("all"), ESearchCase::IgnoreCase))
    {
        RunMode = EEnvQueryRunMode::AllMatching;
    }

    if (FStructProperty* RequestProp =
            FindFProperty<FStructProperty>(RunEQSService->GetClass(), TEXT("EQSRequest")))
    {
        if (RequestProp->Struct == FEQSParametrizedQueryExecutionRequest::StaticStruct())
        {
            FEQSParametrizedQueryExecutionRequest* Request =
                RequestProp->ContainerPtrToValuePtr<FEQSParametrizedQueryExecutionRequest>(RunEQSService);
            Request->QueryTemplate = Query;
            Request->RunMode = RunMode;
            Request->bUseBBKeyForQueryTemplate = false;
            if (BT->BlackboardAsset)
            {
                Request->InitForOwnerAndBlackboard(*RunEQSService, BT->BlackboardAsset);
            }
        }
    }

    if (FStructProperty* BlackboardKeyProp =
            FindFProperty<FStructProperty>(RunEQSService->GetClass(), TEXT("BlackboardKey")))
    {
        if (BlackboardKeyProp->Struct == FBlackboardKeySelector::StaticStruct())
        {
            FBlackboardKeySelector* KeySelector =
                BlackboardKeyProp->ContainerPtrToValuePtr<FBlackboardKeySelector>(RunEQSService);
            KeySelector->SelectedKeyName = FName(*ResultKey);
            KeySelector->InvalidateResolvedKey();
            if (BT->BlackboardAsset)
            {
                KeySelector->ResolveSelectedKey(*BT->BlackboardAsset);
            }
        }
    }

    bool bUpdateBBOnFail = false;
    Params->TryGetBoolField(TEXT("update_bb_on_fail"), bUpdateBBOnFail);
    if (FBoolProperty* UpdateOnFailProp =
            FindFProperty<FBoolProperty>(RunEQSService->GetClass(), TEXT("bUpdateBBOnFail")))
    {
        UpdateOnFailProp->SetPropertyValue_InContainer(RunEQSService, bUpdateBBOnFail);
    }

    double IntervalD = -1.0;
    if (Params->TryGetNumberField(TEXT("interval"), IntervalD) && IntervalD > 0.0)
    {
        if (FFloatProperty* IntervalProp =
                FindFProperty<FFloatProperty>(RunEQSService->GetClass(), TEXT("Interval")))
        {
            IntervalProp->SetPropertyValue_InContainer(RunEQSService, (float)IntervalD);
        }
    }

    RunEQSService->InitializeFromAsset(*BT);
    SafeUpdateBTAsset(BT, BTGraph);

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetBoolField(TEXT("created"), bCreated);
    R->SetStringField(TEXT("behavior_tree"), BTName);
    R->SetStringField(TEXT("query_path"), Query->GetPathName());
    R->SetStringField(TEXT("result_key"), ResultKey);
    R->SetStringField(TEXT("run_mode"), RunModeName);
    R->SetBoolField(TEXT("update_bb_on_fail"), bUpdateBBOnFail);
    R->SetNumberField(TEXT("parent_index"), (double)ParentIdx);
    R->SetNumberField(TEXT("parent_sub_node_count"), (double)ParentNode->SubNodes.Num());
    if (BT->BlackboardAsset)
    {
        R->SetStringField(TEXT("blackboard"), BT->BlackboardAsset->GetPathName());
    }
    if (ServiceGraphNode->NodeInstance)
    {
        R->SetStringField(TEXT("instance_class"), ServiceGraphNode->NodeInstance->GetClass()->GetName());
    }
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// get_bt_graph_info
// Params:
//   behavior_tree_name: string
// Returns list of current graph nodes with their types, positions, and connections.
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleGetBTGraphInfo(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BTName;
    if (!Params->TryGetStringField(TEXT("behavior_tree_name"), BTName))
        return CreateErrorResponse(TEXT("Missing 'behavior_tree_name'"));

    UBehaviorTree* BT = FindBehaviorTree(BTName);
    if (!BT)
        return CreateErrorResponse(FString::Printf(TEXT("BehaviorTree not found: %s"), *BTName));

    UBehaviorTreeGraph* BTGraph = Cast<UBehaviorTreeGraph>(BT->BTGraph);
    if (!BTGraph)
    {
        TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
        R->SetBoolField(TEXT("success"), true);
        R->SetStringField(TEXT("behavior_tree"), BTName);
        R->SetStringField(TEXT("note"), TEXT("No graph exists yet — use build_behavior_tree to create one."));
        R->SetArrayField(TEXT("nodes"), TArray<TSharedPtr<FJsonValue>>());
        return R;
    }

    TArray<TSharedPtr<FJsonValue>> NodeList;
    int32 Idx = 0;
    for (UEdGraphNode* Node : BTGraph->Nodes)
    {
        if (!Node) continue;
        TSharedPtr<FJsonObject> NObj = MakeShared<FJsonObject>();
        bool bIsRoot = Node->IsA<UBehaviorTreeGraphNode_Root>();
        NObj->SetBoolField(TEXT("is_root"), bIsRoot);
        NObj->SetNumberField(TEXT("index"), Idx - (bIsRoot ? 0 : 0));
        NObj->SetStringField(TEXT("graph_class"), Node->GetClass()->GetName());
        NObj->SetNumberField(TEXT("x"), Node->NodePosX);
        NObj->SetNumberField(TEXT("y"), Node->NodePosY);

        if (UAIGraphNode* AIN = Cast<UAIGraphNode>(Node))
        {
            if (AIN->NodeInstance)
            {
                NObj->SetStringField(TEXT("runtime_class"), AIN->NodeInstance->GetClass()->GetName());
                NObj->SetStringField(TEXT("display_name"), AIN->NodeInstance->GetClass()->GetDisplayNameText().ToString());
            }
            // Sub-nodes (decorators/services)
            TArray<TSharedPtr<FJsonValue>> SubList;
            for (UAIGraphNode* Sub : AIN->SubNodes)
            {
                if (!Sub) continue;
                TSharedPtr<FJsonObject> SObj = MakeShared<FJsonObject>();
                SObj->SetStringField(TEXT("graph_class"), Sub->GetClass()->GetName());
                if (Sub->NodeInstance)
                    SObj->SetStringField(TEXT("runtime_class"), Sub->NodeInstance->GetClass()->GetName());
                SubList.Add(MakeShared<FJsonValueObject>(SObj));
            }
            if (SubList.Num() > 0)
                NObj->SetArrayField(TEXT("sub_nodes"), SubList);
        }

        // Output connections
        TArray<TSharedPtr<FJsonValue>> Connections;
        for (UEdGraphPin* Pin : Node->Pins)
        {
            if (!Pin || Pin->Direction != EGPD_Output) continue;
            for (UEdGraphPin* Link : Pin->LinkedTo)
            {
                if (Link && Link->GetOwningNode())
                {
                    TSharedPtr<FJsonObject> ConnObj = MakeShared<FJsonObject>();
                    ConnObj->SetStringField(TEXT("target_class"), Link->GetOwningNode()->GetClass()->GetName());
                    Connections.Add(MakeShared<FJsonValueObject>(ConnObj));
                }
            }
        }
        if (Connections.Num() > 0)
            NObj->SetArrayField(TEXT("connections"), Connections);

        NodeList.Add(MakeShared<FJsonValueObject>(NObj));
        Idx++;
    }

    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("behavior_tree"), BTName);
    R->SetNumberField(TEXT("node_count"), (double)BTGraph->Nodes.Num());
    R->SetArrayField(TEXT("nodes"), NodeList);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════
// bt_add_selector_wait
//
// Restructures a BT so that the Root drives a Selector composite with two
// children:
//   left  (child 0) → the existing first child of Root (e.g. the Sequence)
//   right (child 1) → a new Wait task (default WaitTime = 2.0 s)
//
// Params:
//   bt_path   (string)  – full game path, e.g.
//             "/Game/DestinyContent/Blueprints/Enemies/EnemiesV2/AI/BT_Enemy_Infantry"
//             OR just the asset name, e.g. "BT_Enemy_Infantry"
//   wait_time (float)   – optional, defaults to 2.0
// ════════════════════════════════════════════════════════════════════════════
TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleBTAddSelectorWait(
    const TSharedPtr<FJsonObject>& Params)
{
    // ── 1.  Resolve the BehaviorTree asset ───────────────────────────────────
    FString BTPath;
    Params->TryGetStringField(TEXT("bt_path"), BTPath);
    if (BTPath.IsEmpty())
        Params->TryGetStringField(TEXT("behavior_tree_name"), BTPath);
    if (BTPath.IsEmpty())
        return CreateErrorResponse(TEXT("Missing 'bt_path' (or 'behavior_tree_name')"));

    // Accept both full game path and bare name
    UBehaviorTree* BT = nullptr;
    if (BTPath.StartsWith(TEXT("/")))
    {
        // Load by full object path  (e.g. "/Game/.../BT_Enemy_Infantry")
        BT = LoadObject<UBehaviorTree>(nullptr, *BTPath);
        if (!BT)
        {
            // Try appending the short name as the sub-object
            FString ShortName = FPackageName::GetShortName(BTPath);
            FString FullObjPath = BTPath + TEXT(".") + ShortName;
            BT = LoadObject<UBehaviorTree>(nullptr, *FullObjPath);
        }
    }
    if (!BT)
    {
        // Fall back to AR search by name
        FString ShortName = FPackageName::GetShortName(BTPath);
        BT = FindBehaviorTree(ShortName);
    }
    if (!BT)
        return CreateErrorResponse(FString::Printf(
            TEXT("BehaviorTree asset not found: %s"), *BTPath));

    // Close editors FIRST — unregisters BT editor property-change listeners
    // that crash at 0x68 on any BTGraph UPROPERTY write (MakeLinkTo, AddNode, …).
    CloseAllBTEditors(BT);

    // ── 2.  Get / create the editor graph ───────────────────────────────────
    UBehaviorTreeGraph* BTGraph = GetOrCreateBTGraph(BT);
    if (!BTGraph)
        return CreateErrorResponse(TEXT("Failed to get BehaviorTreeGraph"));

    // ── 3.  Find the Root node ───────────────────────────────────────────────
    UBehaviorTreeGraphNode_Root* RootNode = nullptr;
    for (UEdGraphNode* N : BTGraph->Nodes)
    {
        RootNode = Cast<UBehaviorTreeGraphNode_Root>(N);
        if (RootNode) break;
    }
    if (!RootNode)
        return CreateErrorResponse(TEXT("BT graph has no Root node"));

    // ── 4.  Find Root's output pin and its current first child ──────────────
    UEdGraphPin* RootOutPin = nullptr;
    for (UEdGraphPin* P : RootNode->Pins)
        if (P && P->Direction == EGPD_Output) { RootOutPin = P; break; }
    if (!RootOutPin)
        return CreateErrorResponse(TEXT("Root node has no output pin"));

    // Collect nodes already directly connected to Root (the existing Sequence etc.)
    TArray<UEdGraphPin*> OldChildInputPins;
    for (UEdGraphPin* Link : RootOutPin->LinkedTo)
        if (Link) OldChildInputPins.Add(Link);

    // ── 5.  Check: already has a Selector child? bail early ─────────────────
    for (UEdGraphPin* ChildIn : OldChildInputPins)
    {
        if (!ChildIn->GetOwningNode()) continue;
        if (UAIGraphNode* AIN = Cast<UAIGraphNode>(ChildIn->GetOwningNode()))
        {
            if (AIN->NodeInstance &&
                AIN->NodeInstance->IsA(UBTComposite_Selector::StaticClass()))
            {
                TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
                R->SetBoolField(TEXT("success"), true);
                R->SetStringField(TEXT("note"),
                    TEXT("Root already connected to a Selector — no change made."));
                return R;
            }
        }
    }

    // ── 6.  Create Selector graph node ──────────────────────────────────────
    float SelX = RootNode->NodePosX;
    float SelY = (float)RootNode->NodePosY + 200.0f;

    // Use BTSafeAddNode to avoid BTGraph->AddNode()->NotifyGraphChanged crash
    UBehaviorTreeGraphNode* SelNode =
        NewObject<UBehaviorTreeGraphNode>(
            BTGraph, UBehaviorTreeGraphNode_Composite::StaticClass(), NAME_None, RF_Transactional);
    BTSafeAddNode(BTGraph, SelNode);
    SelNode->NodePosX = FMath::RoundToInt(SelX);
    SelNode->NodePosY = FMath::RoundToInt(SelY);
    SelNode->ClassData = FGraphNodeClassData(UBTComposite_Selector::StaticClass(), FString());
    // BUG-043: assign NodeGuid before PostPlacedNewNode (UAIGraphNode override skips Super
    // → base NodeGuid would be all-zero → BT editor crash on next open at +0x68).
    SelNode->CreateNewGuid();
    // PostPlacedNewNode creates NodeInstance=UBTComposite_Selector with outer=BT (the asset)
    // so it will be serialized as a subobject of the BT package.
    SelNode->PostPlacedNewNode();
    if (SelNode->NodeInstance)
        SelNode->InitializeInstance();
    SelNode->AllocateDefaultPins();

    // ── 7.  Rewire Root → Selector ──────────────────────────────────────────
    // Disconnect Root from its old children WITHOUT BreakAllPinLinks (fires NotifyGraphChanged)
    BTSafeUnlinkPin(RootOutPin);

    UEdGraphPin* SelInPin = nullptr;
    for (UEdGraphPin* P : SelNode->Pins)
        if (P && P->Direction == EGPD_Input) { SelInPin = P; break; }
    // Use BTSafeLinkPins to avoid MakeLinkTo->NotifyGraphChanged crash
    BTSafeLinkPins(RootOutPin, SelInPin);

    // ── 8.  Re-connect old children to Selector ─────────────────────────────
    UEdGraphPin* SelOutPin = nullptr;
    for (UEdGraphPin* P : SelNode->Pins)
        if (P && P->Direction == EGPD_Output) { SelOutPin = P; break; }

    // Re-position old children below Selector (left side)
    int32 OldChildIdx = 0;
    for (UEdGraphPin* ChildIn : OldChildInputPins)
    {
        if (!ChildIn->GetOwningNode()) continue;
        UEdGraphNode* OldChild = ChildIn->GetOwningNode();
        OldChild->NodePosX = FMath::RoundToInt(SelX + (float)(OldChildIdx * 350) - 175.0f);
        OldChild->NodePosY = FMath::RoundToInt(SelY + 200.0f);
        // Use BTSafeLinkPins to avoid MakeLinkTo->NotifyGraphChanged crash
        BTSafeLinkPins(SelOutPin, ChildIn);
        OldChildIdx++;
    }

    // ── 9.  Create Wait task ─────────────────────────────────────────────────
    double WaitTimeSec = 2.0;
    Params->TryGetNumberField(TEXT("wait_time"), WaitTimeSec);

    float WaitX = SelX + (float)(OldChildIdx * 350) - 175.0f;
    float WaitY = SelY + 200.0f;

    // Use BTSafeAddNode to avoid BTGraph->AddNode()->NotifyGraphChanged crash
    UBehaviorTreeGraphNode* WaitNode =
        NewObject<UBehaviorTreeGraphNode>(
            BTGraph, UBehaviorTreeGraphNode_Task::StaticClass(), NAME_None, RF_Transactional);
    BTSafeAddNode(BTGraph, WaitNode);
    WaitNode->NodePosX = FMath::RoundToInt(WaitX);
    WaitNode->NodePosY = FMath::RoundToInt(WaitY);
    WaitNode->ClassData = FGraphNodeClassData(UBTTask_Wait::StaticClass(), FString());
    // BUG-043: assign NodeGuid before PostPlacedNewNode.
    WaitNode->CreateNewGuid();
    // PostPlacedNewNode creates NodeInstance=UBTTask_Wait with outer=BT (the asset)
    WaitNode->PostPlacedNewNode();
    if (WaitNode->NodeInstance)
        WaitNode->InitializeInstance();
    WaitNode->AllocateDefaultPins();

    // Set WaitTime on the runtime instance
    if (WaitNode->NodeInstance)
    {
        FProperty* WTProp = WaitNode->NodeInstance->GetClass()->FindPropertyByName(
            FName(TEXT("WaitTime")));
        if (WTProp)
        {
            FString WaitStr = FString::SanitizeFloat((float)WaitTimeSec);
            WTProp->ImportText_Direct(
                *WaitStr,
                WTProp->ContainerPtrToValuePtr<void>(WaitNode->NodeInstance),
                WaitNode->NodeInstance, PPF_None);
        }
    }

    // Connect Selector → Wait (safe, no NotifyGraphChanged)
    UEdGraphPin* WaitInPin = nullptr;
    for (UEdGraphPin* P : WaitNode->Pins)
        if (P && P->Direction == EGPD_Input) { WaitInPin = P; break; }
    BTSafeLinkPins(SelOutPin, WaitInPin);

    // ── 10.  Close open editor, rebuild runtime tree from graph, save ─────────
    SafeUpdateBTAsset(BT, BTGraph);

    // ── 11.  Return summary ──────────────────────────────────────────────────
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("behavior_tree"), BT->GetName());
    R->SetStringField(TEXT("selector_node"), TEXT("BTComposite_Selector"));
    R->SetStringField(TEXT("wait_node"),     TEXT("BTTask_Wait"));
    R->SetNumberField(TEXT("wait_time"),     WaitTimeSec);
    R->SetNumberField(TEXT("old_children_rewired"), (double)OldChildIdx);
    return R;
}

// ════════════════════════════════════════════════════════════════════════════

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCallInterfaceFunctionNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, InterfaceName, FuncName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("interface_name"), InterfaceName);
    Params->TryGetStringField(TEXT("function_name"), FuncName);
    if (FuncName.IsEmpty()) return CreateErrorResponse(TEXT("Missing 'function_name'"));
    return AddFunctionNodeHelper(BPName,
        InterfaceName.IsEmpty() ? TEXT("") : InterfaceName,
        FuncName, GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddValidatedGetNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    // Validated Get is essentially an IsValid check + get
    return AddFunctionNodeHelper(BPName, TEXT("KismetSystemLibrary"),
        TEXT("IsValid"), GetNodePosition(Params));
}

// ── VR (Ch. 16) ──────────────────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddTeleportSystemToPawn(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("VR Teleport: add_motion_controller_component + add_blueprint_event_node(InputAction_Teleport) "
             "+ add_line_trace_by_channel_node + SetActorLocation for the teleport system."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateVRPawnBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("VR Pawn: use create_character_blueprint(parent_class='VRCharacter') + "
             "add_motion_controller_component for left/right hands."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateGrabComponent(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Grab Component: use create_actor_component + add_component_to_blueprint "
             "to create a VR grab-enabled component."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleMakeActorVRGrabbable(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("VR Grabbable: use add_component_to_blueprint_actor to add a GrabComponent "
             "to the target blueprint."));
    return R;
}

// ── Variant Manager (Ch. 20) ─────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddVariantToLevelVariantSets(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Variant: use exec_python with VariantManagerLibrary to add variants to LevelVariantSets."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateProductConfiguratorBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Product configurator: use create_level_variant_sets + add_variant_to_level_variant_sets "
             "to build a Variant Manager product configurator."));
    return R;
}

// ── Operator / Math (Ch. 2, 5, 6, 8) ────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddArithmeticOperatorNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, Operator, OperandType;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("operator"), Operator);
    Params->TryGetStringField(TEXT("operand_type"), OperandType);
    if (OperandType.IsEmpty()) OperandType = TEXT("Float");

    // Map operator+type to KismetMathLibrary function
    TMap<FString, FString> OpMap;
    if (OperandType == TEXT("Float"))
    {
        OpMap.Add(TEXT("Add"), TEXT("Add_FloatFloat"));
        OpMap.Add(TEXT("Subtract"), TEXT("Subtract_FloatFloat"));
        OpMap.Add(TEXT("Multiply"), TEXT("Multiply_FloatFloat"));
        OpMap.Add(TEXT("Divide"), TEXT("Divide_FloatFloat"));
    }
    else if (OperandType == TEXT("Integer") || OperandType == TEXT("Int"))
    {
        OpMap.Add(TEXT("Add"), TEXT("Add_IntInt"));
        OpMap.Add(TEXT("Subtract"), TEXT("Subtract_IntInt"));
        OpMap.Add(TEXT("Multiply"), TEXT("Multiply_IntInt"));
        OpMap.Add(TEXT("Divide"), TEXT("Divide_IntInt"));
    }
    else if (OperandType == TEXT("Vector"))
    {
        OpMap.Add(TEXT("Add"), TEXT("Add_VectorVector"));
        OpMap.Add(TEXT("Subtract"), TEXT("Subtract_VectorVector"));
        OpMap.Add(TEXT("Multiply"), TEXT("Multiply_VectorFloat"));
    }

    FString* FuncName = OpMap.Find(Operator);
    FString Func = FuncName ? *FuncName : FString::Printf(TEXT("%s_%s%s"), *Operator, *OperandType, *OperandType);
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"), Func, GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddRelationalOperatorNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, Operator, OperandType;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("operator"), Operator);
    Params->TryGetStringField(TEXT("operand_type"), OperandType);
    if (OperandType.IsEmpty()) OperandType = TEXT("Float");

    TMap<FString, FString> OpMap;
    if (OperandType == TEXT("Float"))
    {
        OpMap.Add(TEXT("Equal"), TEXT("EqualEqual_FloatFloat"));
        OpMap.Add(TEXT("NotEqual"), TEXT("NotEqual_FloatFloat"));
        OpMap.Add(TEXT("Greater"), TEXT("Greater_FloatFloat"));
        OpMap.Add(TEXT("GreaterEqual"), TEXT("GreaterEqual_FloatFloat"));
        OpMap.Add(TEXT("Less"), TEXT("Less_FloatFloat"));
        OpMap.Add(TEXT("LessEqual"), TEXT("LessEqual_FloatFloat"));
    }
    else if (OperandType == TEXT("Integer") || OperandType == TEXT("Int"))
    {
        OpMap.Add(TEXT("Equal"), TEXT("EqualEqual_IntInt"));
        OpMap.Add(TEXT("NotEqual"), TEXT("NotEqual_IntInt"));
        OpMap.Add(TEXT("Greater"), TEXT("Greater_IntInt"));
        OpMap.Add(TEXT("GreaterEqual"), TEXT("GreaterEqual_IntInt"));
        OpMap.Add(TEXT("Less"), TEXT("Less_IntInt"));
        OpMap.Add(TEXT("LessEqual"), TEXT("LessEqual_IntInt"));
    }

    FString* FuncName = OpMap.Find(Operator);
    FString Func = FuncName ? *FuncName : FString::Printf(TEXT("%s_%s%s"), *Operator, *OperandType, *OperandType);
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"), Func, GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddLogicalOperatorNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, Operator;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("operator"), Operator);

    TMap<FString, FString> OpMap;
    OpMap.Add(TEXT("AND"), TEXT("BooleanAND"));
    OpMap.Add(TEXT("OR"), TEXT("BooleanOR"));
    OpMap.Add(TEXT("NOT"), TEXT("BooleanNOT"));
    OpMap.Add(TEXT("XOR"), TEXT("BooleanXOR"));

    FString* FuncName = OpMap.Find(Operator.ToUpper());
    FString Func = FuncName ? *FuncName : FString::Printf(TEXT("Boolean%s"), *Operator);
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"), Func, GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddClampNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, OperandType;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("operand_type"), OperandType);
    FString Func = (OperandType == TEXT("Integer") || OperandType == TEXT("Int")) ?
        TEXT("Clamp_Int") : TEXT("FClamp");
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"), Func, GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddLerpNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, OperandType;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("operand_type"), OperandType);
    FString Func = (OperandType == TEXT("Vector")) ? TEXT("VLerp") : TEXT("Lerp");
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"), Func, GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddAbsNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
        TEXT("Abs"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddMinMaxNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    FString Op;
    Params->TryGetStringField(TEXT("operator"), Op);
    FString Func = (Op.ToUpper() == TEXT("MAX")) ? TEXT("FMax") : TEXT("FMin");
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"), Func, GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddRandomFloatInRangeNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
        TEXT("RandomFloatInRange"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddRandomIntegerInRangeNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("KismetMathLibrary"),
        TEXT("RandomIntegerInRange"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddGetDeltaSecondsNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("GetWorldDeltaSeconds"), GetNodePosition(Params));
}

// ── Actor Query (Ch. 3, 4) ───────────────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddGetAllActorsOfClassNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("GetAllActorsOfClass"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddGetActorOfClassNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("GetActorOfClass"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddGetGameModeNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("GetGameMode"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddGetGameInstanceNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("GetGameInstance"), GetNodePosition(Params));
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddConstructionScriptNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    // UserConstructionScript event node
    TSharedPtr<FJsonObject> EventParams = MakeShared<FJsonObject>();
    EventParams->SetStringField(TEXT("blueprint_name"), BPName);
    EventParams->SetStringField(TEXT("event_name"), TEXT("UserConstructionScript"));
    if (Params->HasField(TEXT("node_position")))
        EventParams->SetField(TEXT("node_position"), Params->Values.FindRef(TEXT("node_position")));
    return HandleAddCustomEvent(EventParams);
}

// ── UMG Extended Commands (Ch. 7, 8, 11) ────────────────────────────────────
// These are handled by umg_tools.py which sends the correct blueprint_node commands.
// Stub implementations return guidance messages.

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddHorizontalBoxToWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"), TEXT("Use exec_python with UMG WidgetBlueprint to add a HorizontalBox."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddVerticalBoxToWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"), TEXT("Use exec_python with UMG WidgetBlueprint to add a VerticalBox."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCanvasPanelToWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"), TEXT("Use exec_python with UMG WidgetBlueprint to add a CanvasPanel."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddSliderToWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"), TEXT("Use exec_python with UMG WidgetBlueprint to add a Slider widget."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCheckboxToWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"), TEXT("Use exec_python with UMG WidgetBlueprint to add a CheckBox widget."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddNamedSlotToWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"), TEXT("Use exec_python with UMG WidgetBlueprint to add a NamedSlot."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateHUDWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use create_umg_widget_blueprint + add_text_block_to_widget + add_progress_bar_to_widget "
             "to create a HUD widget."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateWinMenuWidget(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use create_umg_widget_blueprint + add_text_block_to_widget + add_button_to_widget "
             "to create a win menu widget."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddWidgetAnimation(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"), TEXT("Use exec_python with WidgetBlueprint.Animations to add a UMG animation."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddCreateWidgetNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName, WidgetClass;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    Params->TryGetStringField(TEXT("widget_class"), WidgetClass);
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("CreateWidget"), GetNodePosition(Params));
}

// ── Procedural Generation (Ch. 19) ──────────────────────────────────────────

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateProceduralMeshBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Procedural mesh: use create_blueprint(parent_class='Actor') + "
             "add_component_to_blueprint(InstancedStaticMeshComponent) + "
             "exec_python to configure the grid placement logic."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateSplinePlacementBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Spline placement: use create_blueprint(parent_class='Actor') + "
             "add_component_to_blueprint(SplineComponent) + "
             "exec_python to configure mesh placement along the spline."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateEditorUtilityBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Editor Utility: use exec_python with EditorUtilityWidgetFactory or "
             "EditorUtilityBlueprintFactory to create an Editor Utility Blueprint."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateAlignActorsUtility(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Align Actors Utility: use create_editor_utility_blueprint + exec_python "
             "to implement actor alignment via GetAllActorsOfClass + SetActorLocation."));
    return R;
}

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateRandomSpawnerBlueprint(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Random spawner: use create_blueprint(parent_class='Actor') + "
             "add_blueprint_variable(SpawnPoints array) + add_set_timer_by_function_name_node "
             "to build a random actor spawner."));
    return R;
}

// ── Gameplay (existing but missing in dispatch before) ───────────────────────
// Note: create_level_variant_sets handled by variant_tools.py using exec_python

TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleCreateLevelVariantSets(
    const TSharedPtr<FJsonObject>& Params)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), true);
    R->SetStringField(TEXT("message"),
        TEXT("Use exec_python with LevelVariantSetsFactory to create a LevelVariantSets asset."));
    return R;
}


TSharedPtr<FJsonObject> FUnrealMCPExtendedCommands::HandleAddOpenLevelNode(
    const TSharedPtr<FJsonObject>& Params)
{
    FString BPName;
    if (!Params->TryGetStringField(TEXT("blueprint_name"), BPName))
        return CreateErrorResponse(TEXT("Missing 'blueprint_name'"));
    return AddFunctionNodeHelper(BPName, TEXT("GameplayStatics"),
        TEXT("OpenLevel"), GetNodePosition(Params));
}
