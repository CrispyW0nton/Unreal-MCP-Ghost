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
 *
 * Editing commands:
 *   connect_blueprint_nodes                - connect two node pins (uses schema TryCreateConnection)
 *   disconnect_blueprint_nodes             - break a pin connection
 *   delete_blueprint_node                  - remove a node from the graph
 *   set_node_pin_value                     - set a literal default value on an unconnected pin
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
 *   add_blueprint_get_component_node           - add a VariableGet for a SCS component (validates against SCS, returns class)
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
    TSharedPtr<FJsonObject> HandleAddBlueprintFunctionCall(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintVariableGetNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintVariableSetNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintVariable(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintInputActionNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintEnhancedInputActionNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintSelfReference(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintGetSelfComponentReference(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintGetComponentNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintBranchNode(const TSharedPtr<FJsonObject>& Params);
    TSharedPtr<FJsonObject> HandleAddBlueprintCastNode(const TSharedPtr<FJsonObject>& Params);

    // ---------- shared helpers ----------

    /** Resolve blueprint + optional graph_name -> UEdGraph*.
     *  graph_name defaults to EventGraph. Returns nullptr + fills OutError on failure. */
    UEdGraph* ResolveGraph(const TSharedPtr<FJsonObject>& Params, FString& OutError);

    /** Find a node in a graph by GUID string OR by short object name (e.g. "K2Node_CallFunction_40"). */
    UEdGraphNode* FindNodeByIdOrName(UEdGraph* Graph, const FString& IdOrName);

    /** Serialize a single graph node to JSON (id, type, name, pos, pins). */
    TSharedPtr<FJsonObject> SerializeNode(UEdGraphNode* Node);

    /** Serialize a single pin to JSON. */
    TSharedPtr<FJsonObject> SerializePin(UEdGraphPin* Pin);

    /** Resolve a UFunction* from a full UE path like "/Script/Engine.Actor:K2_GetActorLocation"
     *  or a short "ClassName::FunctionName" / "FunctionName" searched in a target class string. */
    UFunction* ResolveFunction(const FString& FunctionPath, const FString& TargetClass, UBlueprint* Blueprint);

    /** Apply a literal string value to a pin via the K2 schema. */
    bool ApplyPinValue(UEdGraph* Graph, UEdGraphPin* Pin, const FString& Value);
};
