#pragma once

#include "CoreMinimal.h"
#include "Json.h"

/**
 * Handler class for Blueprint Node-related MCP commands.
 *
 * Inspection commands:
 *   get_blueprint_nodes                    - list every node in a graph with full pin data
 *                                           (graph_name="*" returns nodes from ALL graphs)
 *   find_blueprint_nodes                   - filter nodes by type / name
 *   get_blueprint_graphs                   - list all graphs in a Blueprint
 *   get_node_by_id                         - get full data for a single node by GUID
 *   get_blueprint_components               - list SCS + native components of a Blueprint (L-020)
 *   get_blueprint_variable_defaults        - read variable default values (L-013)
 *
 * Editing commands:
 *   connect_blueprint_nodes                - connect two node pins (uses schema TryCreateConnection)
 *   disconnect_blueprint_nodes             - break a pin connection
 *   delete_blueprint_node                  - remove a node from the graph
 *   set_node_pin_value                     - set a literal default value on an unconnected pin
 *   set_blueprint_variable_default         - write a variable default value (L-013)
 *   move_blueprint_node                    - reposition a node on the canvas (L-019)
 *
 * Node creation commands:
 *   add_blueprint_event_node               - add a K2Node_Event
 *   add_blueprint_function_node            - add a K2Node_CallFunction (any class/library)
 *   add_blueprint_variable_get_node        - add a K2Node_VariableGet
 *   add_blueprint_variable_set_node        - add a K2Node_VariableSet
 *   add_blueprint_variable                 - declare a new Blueprint member variable
 *   add_blueprint_input_action_node        - add a legacy K2Node_InputAction
 *   add_blueprint_enhanced_input_action_node - add K2Node_EnhancedInputAction (UE5 Enhanced Input)
 *   add_blueprint_self_reference           - add a K2Node_Self node
 *   add_blueprint_get_self_component_reference - add a VariableGet for a component property (by name only)
 *   add_blueprint_get_component_node       - add a VariableGet for a SCS component (validates against SCS)
 *   add_blueprint_branch_node              - add a K2Node_IfThenElse (Branch)
 *   add_blueprint_cast_node                - add a K2Node_DynamicCast
 *   add_blueprint_for_loop_node            - add a ForLoop macro node (L-012)
 *   add_blueprint_for_each_loop_node       - add a ForEachLoop macro node (L-012)
 *   add_blueprint_sequence_node            - add a Sequence macro node (L-012)
 *   add_blueprint_do_once_node             - add a DoOnce macro node (L-012)
 *   add_blueprint_gate_node                - add a Gate macro node (L-012)
 *   add_blueprint_flip_flop_node           - add a FlipFlop macro node (L-012)
 *   add_blueprint_switch_on_int_node       - add a K2Node_SwitchInteger (L-012)
 *   add_blueprint_spawn_actor_node         - add a K2Node_SpawnActorFromClass (L-012)
 *   add_blueprint_comment_node             - add a comment box node (L-018)
 *   setup_navmesh                          - spawn/resize a NavMeshBoundsVolume (L-014)
 *   get_blueprint_variables                - list all member variables with type/default/category
 *   get_blueprint_functions                - list all function graphs with input/output pin info
 *   add_blueprint_function_with_pins       - create function graph with typed input/output pins
 */
class UNREALMCP_API FUnrealMCPBlueprintNodeCommands
{
public:
    FUnrealMCPBlueprintNodeCommands();
    TSharedPtr<FJsonObject> HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params);

private:
    // ---------- graph inspection ----------
    TSharedPtr<FJsonObject> HandleGetBlueprintNodes(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleFindBlueprintNodes(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetBlueprintGraphs(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetNodeById(const TSharedPtr<FJsonObject>& Params);

    // ---------- graph editing ----------
    TSharedPtr<FJsonObject> HandleConnectBlueprintNodes(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleDisconnectBlueprintNodes(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleDeleteBlueprintNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetNodePinValue(const TSharedPtr<FJsonObject>& Params);

    // ---------- node creation ----------
    TSharedPtr<FJsonObject> HandleAddBlueprintEvent(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintCustomEventNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetSpawnActorClass(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintFunctionCall(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintVariableGetNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintVariableSetNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintVariable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintInputActionNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintEnhancedInputActionNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintSelfReference(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintGetSelfComponentReference(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintGetComponentNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintSetComponentProperty(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintBranchNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintCastNode(const TSharedPtr<FJsonObject>& Params);

    // ---------- Phase 2: structural nodes (L-012) ----------
    TSharedPtr<FJsonObject> HandleAddBlueprintForLoopNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintForEachLoopNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintSequenceNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintDoOnceNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintGateNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintFlipFlopNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintSwitchOnIntNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintSpawnActorNode(const TSharedPtr<FJsonObject>& Params);

    // ---------- Phase 2: comment + reposition (L-018, L-019) ----------
    TSharedPtr<FJsonObject> HandleAddBlueprintCommentNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleMoveBlueprintNode(const TSharedPtr<FJsonObject>& Params);

    // ---------- Phase 3: variable defaults (L-013) ----------
    TSharedPtr<FJsonObject> HandleGetBlueprintVariableDefaults(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleSetBlueprintVariableDefault(const TSharedPtr<FJsonObject>& Params);

    // ---------- Phase 4: component inspection (L-020) ----------
    TSharedPtr<FJsonObject> HandleGetBlueprintComponents(const TSharedPtr<FJsonObject>& Params);

    // ---------- Phase 5: NavMesh (L-014) ----------
    TSharedPtr<FJsonObject> HandleSetupNavMesh(const TSharedPtr<FJsonObject>& Params);

    // ---------- Phase 6: Blueprint introspection ----------
    TSharedPtr<FJsonObject> HandleGetBlueprintVariables(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleGetBlueprintFunctions(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintFunctionWithPins(const TSharedPtr<FJsonObject>& Params);

    // ---------- shared helpers ----------

    /** Resolve blueprint + optional graph_name -> UEdGraph*.
     *  graph_name defaults to EventGraph. Returns nullptr + fills OutError on failure. */
    UEdGraph* ResolveGraph(const TSharedPtr<FJsonObject>& Params, FString& OutError);

    /** Find a node in a graph by GUID string OR by short object name. */
    UEdGraphNode* FindNodeByIdOrName(UEdGraph* Graph, const FString& IdOrName);

    /** Serialize a single graph node to JSON (id, type, name, pos, pins). */
    TSharedPtr<FJsonObject> SerializeNode(UEdGraphNode* Node);

    /** Serialize a single pin to JSON. */
    TSharedPtr<FJsonObject> SerializePin(UEdGraphPin* Pin);

    /** Resolve a UFunction* from a full UE path or short name+class string. */
    UFunction* ResolveFunction(const FString& FunctionPath, const FString& TargetClass, UBlueprint* Blueprint);

    /** Apply a literal string value to a pin via the K2 schema. */
    bool ApplyPinValue(UEdGraph* Graph, UEdGraphPin* Pin, const FString& Value);
};
