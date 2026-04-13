"""
Blueprint Node Tools — graph inspection, node creation, pin wiring.
Covers all UnrealMCP blueprint-node commands.
"""
import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_blueprint_node_tools(mcp: FastMCP):

    # ------------------------------------------------------------------
    # GRAPH INSPECTION
    # ------------------------------------------------------------------

    @mcp.tool()
    def get_blueprint_nodes(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        include_hidden_pins: bool = False,
    ) -> Dict[str, Any]:
        """
        Return every node in a Blueprint graph with full pin data.

        Use this before editing a graph — it gives you node_id (GUID),
        node_name (short object name like 'K2Node_CallFunction_40'),
        node_type, position, function_name / event_name / variable_name
        where applicable, and a pins list (pin_id, pin_name, direction,
        type, default_value, linked_to).

        graph_name special values:
          'EventGraph'  (default) — main event graph
          '*' or 'all'            — EVERY graph in the Blueprint
                                    (EventGraph + functions + macros).
                                    Response has 'graphs' list with per-graph
                                    node lists, plus 'total_count'.

        Args:
            blueprint_name: Asset name, e.g. 'ThePlayerCharacter'
            graph_name: Graph to inspect. Defaults to 'EventGraph'.
                        Pass '*' or 'all' to get every graph at once.
            include_hidden_pins: Include hidden/internal pins in output.

        Returns:
            Single-graph: Dict with 'nodes' list and 'count'.
            All-graphs:   Dict with 'graphs' list (each has graph_name,
                          nodes, count) and 'total_count'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("get_blueprint_nodes", {
                "blueprint_name": blueprint_name,
                "graph_name": graph_name,
                "include_hidden_pins": include_hidden_pins,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_node_by_id(
        ctx: Context,
        blueprint_name: str,
        node_id: str,
        graph_name: str = "EventGraph",
        include_hidden_pins: bool = False,
    ) -> Dict[str, Any]:
        """
        Fast single-node lookup — returns full pin data for exactly one node.

        Use this instead of get_blueprint_nodes when you already know a node's
        ID or name and just need its current pin state (e.g. to verify a
        connection was made, or to read a default value).

        node_id can be:
          - A GUID string  (from previous add_* or get_blueprint_nodes calls)
          - A short object name, e.g. 'K2Node_CallFunction_40'

        Returns the same structure as a single entry from get_blueprint_nodes:
          node_id, node_name, node_type, pos_x, pos_y,
          function_name / event_name / variable_name (where applicable),
          pins list (pin_id, pin_name, direction, type, default_value, linked_to).

        Args:
            blueprint_name:      Asset name, e.g. 'ThePlayerCharacter'
            node_id:             GUID or short object name of the node.
            graph_name:          Graph to search. Default 'EventGraph'.
            include_hidden_pins: Include hidden/internal pins. Default False.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("get_node_by_id", {
                "blueprint_name":      blueprint_name,
                "node_id":             node_id,
                "graph_name":          graph_name,
                "include_hidden_pins": include_hidden_pins,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def find_blueprint_nodes(
        ctx: Context,
        blueprint_name: str,
        node_type: str = "all",
        graph_name: str = "EventGraph",
        event_name: str = "",
        function_name: str = "",
        variable_name: str = "",
        input_action_name: str = "",
        node_name: str = "",
    ) -> Dict[str, Any]:
        """
        Find nodes in a Blueprint graph filtered by type and/or name.

        node_type values:
          'all'                — every node
          'event'              — K2Node_Event (filter by event_name)
          'function'           — K2Node_CallFunction (filter by function_name)
          'variable_get'       — K2Node_VariableGet (filter by variable_name)
          'variable_set'       — K2Node_VariableSet (filter by variable_name)
          'input_action'       — K2Node_InputAction / K2Node_EnhancedInputAction
          Any class substring  — e.g. 'IfThenElse', 'Knot', 'Self'

        Args:
            blueprint_name: Asset name, e.g. 'ThePlayerCharacter'
            node_type: Filter type (see above). Default 'all'.
            graph_name: Graph to search. Default 'EventGraph'.
            event_name: Filter by event name (when node_type='event').
            function_name: Filter by function name (when node_type='function').
            variable_name: Filter by variable name (when node_type='variable_get/set').
            input_action_name: Filter by action name / comment.
            node_name: Filter by exact node object name.

        Returns:
            Dict with 'nodes' (full objects) and 'node_guids' (legacy GUID list).
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params = {
                "blueprint_name": blueprint_name,
                "node_type": node_type,
                "graph_name": graph_name,
            }
            if event_name:        params["event_name"]        = event_name
            if function_name:     params["function_name"]     = function_name
            if variable_name:     params["variable_name"]     = variable_name
            if input_action_name: params["input_action_name"] = input_action_name
            if node_name:         params["node_name"]         = node_name
            return unreal.send_command("find_blueprint_nodes", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # PIN WIRING
    # ------------------------------------------------------------------

    @mcp.tool()
    def connect_blueprint_nodes(
        ctx: Context,
        blueprint_name: str,
        source_node_id: str,
        source_pin: str,
        target_node_id: str,
        target_pin: str,
        graph_name: str = "EventGraph",
    ) -> Dict[str, Any]:
        """
        Connect an output pin on one node to an input pin on another.

        source_node_id / target_node_id can be:
          - A GUID string (from get_blueprint_nodes / add_* commands)
          - The short object name, e.g. 'K2Node_CallFunction_40'

        Common exec pin names: 'then' (output), 'execute' (input).
        Common data pin names: 'ReturnValue', 'Target', 'NewLocation', etc.

        Returns a dict with source_node_id, target_node_id, source_pin,
        target_pin, and connection_verified (True/False).  If
        connection_verified is False a 'warning' field explains why the
        connection may not have taken effect (type mismatch, schema
        disallow, etc.).  When the schema outright forbids the connection
        the command returns an error with the schema's reason message.

        Args:
            blueprint_name: Asset name.
            source_node_id: GUID or object name of the source node.
            source_pin: Output pin name on the source node.
            target_node_id: GUID or object name of the target node.
            target_pin: Input pin name on the target node.
            graph_name: Graph to operate on. Default 'EventGraph'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("connect_blueprint_nodes", {
                "blueprint_name":  blueprint_name,
                "source_node_id":  source_node_id,
                "source_pin":      source_pin,
                "target_node_id":  target_node_id,
                "target_pin":      target_pin,
                "graph_name":      graph_name,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def disconnect_blueprint_nodes(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        node_id: str = "",
        pin_name: str = "",
        source_node_id: str = "",
        source_pin: str = "",
        target_node_id: str = "",
        target_pin: str = "",
    ) -> Dict[str, Any]:
        """
        Break pin connections in a Blueprint graph.

        Two modes:
          A) Break ALL links on a single pin:
             Provide node_id + pin_name.
          B) Break a SPECIFIC link between two nodes:
             Provide source_node_id + source_pin + target_node_id + target_pin.

        Args:
            blueprint_name: Asset name.
            graph_name: Graph to operate on. Default 'EventGraph'.
            node_id: (Mode A) Node GUID or name.
            pin_name: (Mode A) Pin to clear.
            source_node_id: (Mode B) Source node GUID or name.
            source_pin: (Mode B) Output pin on source.
            target_node_id: (Mode B) Target node GUID or name.
            target_pin: (Mode B) Input pin on target.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params: Dict[str, Any] = {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
            }
            if node_id and pin_name:
                params["node_id"]  = node_id
                params["pin_name"] = pin_name
            else:
                params["source_node_id"] = source_node_id
                params["source_pin"]     = source_pin
                params["target_node_id"] = target_node_id
                params["target_pin"]     = target_pin
            return unreal.send_command("disconnect_blueprint_nodes", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_node_pin_value(
        ctx: Context,
        blueprint_name: str,
        node_id: str,
        pin_name: str,
        value: str,
        graph_name: str = "EventGraph",
    ) -> Dict[str, Any]:
        """
        Set a literal default value on an unconnected pin.

        This is equivalent to typing a value into an exposed pin field in
        the Blueprint editor. The pin must NOT be connected to another node.

        Examples:
          Boolean  : value="true" or "false"
          Float    : value="1.5"
          Integer  : value="42"
          String   : value="Hello"
          Vector   : value="(X=100.0,Y=0.0,Z=0.0)"
          Rotator  : value="(Pitch=0.0,Yaw=90.0,Roll=0.0)"

        Args:
            blueprint_name: Asset name.
            node_id: Node GUID or short object name.
            pin_name: Pin name to set.
            value: New literal value as a string.
            graph_name: Graph to operate on. Default 'EventGraph'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("set_node_pin_value", {
                "blueprint_name": blueprint_name,
                "node_id":        node_id,
                "pin_name":       pin_name,
                "value":          value,
                "graph_name":     graph_name,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # NODE DELETION
    # ------------------------------------------------------------------

    @mcp.tool()
    def delete_blueprint_node(
        ctx: Context,
        blueprint_name: str,
        node_id: str,
        graph_name: str = "EventGraph",
    ) -> Dict[str, Any]:
        """
        Delete a node from a Blueprint graph (breaks all its connections first).

        Args:
            blueprint_name: Asset name.
            node_id: Node GUID or short object name (e.g. 'K2Node_CallFunction_40').
            graph_name: Graph to operate on. Default 'EventGraph'.

        Returns:
            Dict with 'deleted_node_id' and 'deleted_node_name'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("delete_blueprint_node", {
                "blueprint_name": blueprint_name,
                "node_id":        node_id,
                "graph_name":     graph_name,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # NODE CREATION
    # ------------------------------------------------------------------

    @mcp.tool()
    def add_blueprint_event_node(
        ctx: Context,
        blueprint_name: str,
        event_name: str,
        graph_name: str = "EventGraph",
        node_position: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Add an event node to a Blueprint graph.

        Common event names:
          ReceiveBeginPlay, ReceiveTick, ReceiveEndPlay,
          ReceiveHit, ReceiveActorBeginOverlap, ReceiveActorEndOverlap

        Args:
            blueprint_name: Asset name.
            event_name: Event to add.
            graph_name: Target graph. Default 'EventGraph'.
            node_position: Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id' and 'node_name'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_event_node", {
                "blueprint_name": blueprint_name,
                "event_name":     event_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_function_node(
        ctx: Context,
        blueprint_name: str,
        function_name: str,
        target: str = "",
        graph_name: str = "EventGraph",
        params: Dict[str, Any] = None,
        node_position: List[float] = None,
        allow_duplicates: bool = False,
    ) -> Dict[str, Any]:
        """
        Add a function-call node to a Blueprint graph.

        function_name can be:
          • Short name: 'K2_GetActorLocation', 'SetActorLocation', 'PrintString'
          • Full UE path: '/Script/Engine.Actor:K2_GetActorLocation'

        target (optional) identifies the class that owns the function:
          • Short name:  'KismetMathLibrary', 'KismetSystemLibrary',
                         'GameplayStatics', 'Actor', 'Character'
          • Full path:   '/Script/Engine.KismetMathLibrary'
          • Leave empty to search the Blueprint's own class hierarchy.

        Duplicate guard: by default (allow_duplicates=False) if a node with the
        same function name already exists within 32 units of node_position, the
        existing node is returned instead of creating a new one.  Set
        allow_duplicates=True to force creation of a new node regardless.

        params values can be strings, numbers, or booleans — all are handled.

        Returns node_id, node_name, pins, and was_existing (True if the
        duplicate guard returned an existing node).

        Args:
            blueprint_name:  Asset name.
            function_name:   Function to call (short name or full path).
            target:          Class that owns the function (optional).
            graph_name:      Graph to add node to. Default 'EventGraph'.
            params:          Dict of pin_name -> default_value to set inline.
            node_position:   Optional [X, Y] canvas position.
            allow_duplicates: Force new node even if one already exists nearby.

        Returns:
            Dict with 'node_id', 'node_name', 'pins', 'was_existing'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if params is None:
                params = {}
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_function_node", {
                "blueprint_name":  blueprint_name,
                "function_name":   function_name,
                "target":          target,
                "graph_name":      graph_name,
                "params":          params,
                "node_position":   node_position,
                "allow_duplicates": allow_duplicates,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_variable_get_node(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        graph_name: str = "EventGraph",
        node_position: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Add a 'Get Variable' node for a Blueprint variable.

        Args:
            blueprint_name: Asset name.
            variable_name:  Name of the variable to get.
            graph_name:     Graph to add node to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_variable_get_node", {
                "blueprint_name": blueprint_name,
                "variable_name":  variable_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_variable_set_node(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        graph_name: str = "EventGraph",
        node_position: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Add a 'Set Variable' node for a Blueprint variable.

        Args:
            blueprint_name: Asset name.
            variable_name:  Name of the variable to set.
            graph_name:     Graph to add node to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_variable_set_node", {
                "blueprint_name": blueprint_name,
                "variable_name":  variable_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_variable(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        variable_type: str,
        is_exposed: bool = False,
        default_value: str = "",
    ) -> Dict[str, Any]:
        """
        Add a member variable to a Blueprint.

        Supported variable_type values:
          Boolean, Integer, Integer64, Float, Double,
          String, Name, Text,
          Vector, Rotator, Transform,
          Object/<FullClassPath>  (e.g. 'Object//Script/Engine.StaticMeshComponent')

        Args:
            blueprint_name: Asset name.
            variable_name:  New variable name.
            variable_type:  Type string (see above).
            is_exposed:     Expose in Details panel (BlueprintVisible + Edit).
            default_value:  Optional initial value string (e.g. '0', 'true',
                            '(X=0.0,Y=0.0,Z=0.0)').  Stored in both the
                            FBPVariableDescription and the Blueprint CDO.

        Returns:
            Dict with 'variable_name' and 'variable_type'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            p = {
                "blueprint_name": blueprint_name,
                "variable_name":  variable_name,
                "variable_type":  variable_type,
                "is_exposed":     is_exposed,
            }
            if default_value:
                p["default_value"] = default_value
            return unreal.send_command("add_blueprint_variable", p) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_input_action_node(
        ctx: Context,
        blueprint_name: str,
        action_name: str,
        graph_name: str = "EventGraph",
        node_position: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Add a legacy Input Action event node (non-Enhanced Input).

        For Enhanced Input actions that already exist in the graph use
        find_blueprint_nodes with node_type='input_action'.

        Args:
            blueprint_name: Asset name.
            action_name:    Input action name, e.g. 'Jump'.
            graph_name:     Graph to add node to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_input_action_node", {
                "blueprint_name": blueprint_name,
                "action_name":    action_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_self_reference(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        node_position: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Add a 'Get a reference to self' node (returns this actor/object).

        Args:
            blueprint_name: Asset name.
            graph_name:     Graph to add node to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_self_reference", {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_get_self_component_reference(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        graph_name: str = "EventGraph",
        node_position: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Add a node that gets a reference to one of the Blueprint's own components.
        Equivalent to dragging a component from the Components panel into the graph.

        Args:
            blueprint_name: Asset name.
            component_name: Component variable name (e.g. 'CapsuleComponent').
            graph_name:     Graph to add node to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_get_self_component_reference", {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_blueprint_graphs(
        ctx: Context,
        blueprint_name: str,
    ) -> Dict[str, Any]:
        """
        List every graph inside a Blueprint: EventGraph(s), function graphs,
        macro graphs, and delegate graphs.

        Use this to discover graph names before calling get_blueprint_nodes
        or add_blueprint_function_node with a non-default graph_name.

        Args:
            blueprint_name: Asset name, e.g. 'ThePlayerCharacter'

        Returns:
            Dict with 'graphs' list. Each entry has:
              graph_name  - name to pass as graph_name to other tools
              graph_type  - 'EventGraph', 'Function', 'Macro', or 'Delegate'
              node_count  - number of nodes currently in the graph
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            result = unreal.send_command("get_blueprint_graphs", {
                "blueprint_name": blueprint_name,
            })
            if result is None:
                return {"success": False, "message": f"No response from Unreal Engine"}
            # If C++ returned an error envelope, surface it as a clear message
            if isinstance(result, dict) and result.get("status") == "error":
                return {"success": False, "message": result.get("error", "Unknown error from C++ side")}
            # Empty dict means Blueprint was not found / no graphs returned
            if not result:
                return {"success": False, "message": f"Blueprint '{blueprint_name}' not found or has no graphs"}
            return result
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_enhanced_input_action_node(
        ctx: Context,
        blueprint_name: str,
        action_asset: str,
        graph_name: str = "EventGraph",
        node_position: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Add an Enhanced Input Action event node (K2Node_EnhancedInputAction) to a
        Blueprint graph, wired to the specified UInputAction asset.

        This is the correct node type for projects using Unreal Engine's Enhanced
        Input system (which replaces the legacy Input Actions in UE5).  The node
        exposes Triggered / Started / Ongoing / Canceled / Completed exec pins as
        well as ActionValue, ElapsedSeconds, and TriggeredSeconds data pins.

        action_asset can be:
          • Full object path:
              "/Game/OtherAssets/_input_/Actions/IA_Blink.IA_Blink"
          • Asset name only (will be found via Asset Registry):
              "IA_Blink"

        After adding the node use connect_blueprint_nodes to wire the exec pins
        to your logic.  Use get_blueprint_nodes to inspect the pin names.

        Args:
            blueprint_name: Asset name of the Blueprint to edit.
            action_asset:   UInputAction asset — full path or short name.
            graph_name:     Target graph. Defaults to 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'input_action', 'input_action_path',
            and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_enhanced_input_action_node", {
                "blueprint_name": blueprint_name,
                "action_asset":   action_asset,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_get_component_node(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        graph_name: str = "EventGraph",
        node_position: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Add a node that gets a reference to one of the Blueprint's SCS components.

        Unlike add_blueprint_get_self_component_reference (which blindly trusts
        the component name), this command validates the component against the
        Blueprint's SimpleConstructionScript and also searches inherited C++
        component properties.  It returns the component's actual class name in
        the response as 'component_class'.

        Use this when you know a component was added in the Blueprint editor
        (e.g. StaticMeshComponent, CapsuleComponent, CharacterMovement).

        Args:
            blueprint_name: Asset name.
            component_name: Variable name of the component (e.g. 'Mesh',
                            'CapsuleComponent', 'CharacterMovement').
            graph_name:     Graph to add node to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'component_name',
            'component_class' (if found), and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_get_component_node", {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_branch_node(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a Branch (If/Then/Else) node to a Blueprint graph.

        This is the standard UE5 Branch node with Condition (bool) input,
        True exec output, and False exec output.

        Args:
            blueprint_name: Asset name of the Blueprint.
            graph_name:     Graph to add to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', and 'pins'
            (execute, Condition, True, False).
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_branch_node", {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_cast_node(
        ctx: Context,
        blueprint_name: str,
        cast_target_class: str,
        graph_name: str = "EventGraph",
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a Cast node (K2Node_DynamicCast) to a Blueprint graph.

        Args:
            blueprint_name:    Asset name of the Blueprint.
            cast_target_class: Class to cast to. Accepts short names like
                               'AIController', 'ThePlayerCharacter', or full
                               paths like '/Script/AIModule.AIController'.
            graph_name:        Graph to add to. Default 'EventGraph'.
            node_position:     Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'cast_class', and 'pins'
            (execute, Object, then/cast-success, CastFailed, As<ClassName>).
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_cast_node", {
                "blueprint_name":    blueprint_name,
                "cast_target_class": cast_target_class,
                "graph_name":        graph_name,
                "node_position":     node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ===================================================================
    # Phase 2: Structural flow-control nodes (L-012)
    # ===================================================================

    @mcp.tool()
    def add_blueprint_for_loop_node(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        first_index: int = 0,
        last_index: int = 9,
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a standard ForLoop macro node to a Blueprint graph.

        Pins: execute, First Index (int), Last Index (int),
              Loop Body (exec), Index (int), Completed (exec).

        Args:
            blueprint_name: Asset name of the Blueprint.
            graph_name:     Graph to add to. Default 'EventGraph'.
            first_index:    Starting index (default 0).
            last_index:     Ending index (default 9).
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'node_type', and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_for_loop_node", {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
                "first_index":    first_index,
                "last_index":     last_index,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_for_each_loop_node(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a ForEachLoop macro node to a Blueprint graph.

        Pins: execute, Array (wildcard array), Loop Body (exec),
              Array Element (wildcard), Array Index (int), Completed (exec).

        Args:
            blueprint_name: Asset name of the Blueprint.
            graph_name:     Graph to add to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'node_type', and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_for_each_loop_node", {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_sequence_node(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a Sequence macro node to a Blueprint graph.

        A Sequence node executes multiple outputs in order (Then 0, Then 1, ...).
        Additional outputs can be added manually in the Blueprint editor.

        Args:
            blueprint_name: Asset name of the Blueprint.
            graph_name:     Graph to add to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'node_type', and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_sequence_node", {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_do_once_node(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a DoOnce macro node to a Blueprint graph.

        The DoOnce node only fires the Completed output once until Reset is triggered.
        Pins: execute, Reset (exec), Completed (exec), bIsOpen (bool).

        Args:
            blueprint_name: Asset name of the Blueprint.
            graph_name:     Graph to add to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'node_type', and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_do_once_node", {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_gate_node(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        start_closed: bool = False,
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a Gate macro node to a Blueprint graph.

        A Gate passes execution through its Exit pin only when open.
        Pins: execute, Open (exec), Close (exec), Toggle (exec),
              Start Closed (bool), Exit (exec).

        Args:
            blueprint_name: Asset name of the Blueprint.
            graph_name:     Graph to add to. Default 'EventGraph'.
            start_closed:   Whether the gate starts closed (default False).
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'node_type', and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_gate_node", {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
                "start_closed":   start_closed,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_flip_flop_node(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a FlipFlop macro node to a Blueprint graph.

        Alternates between A and B exec outputs on each trigger.
        Pins: execute, A (exec), B (exec), IsA (bool).

        Args:
            blueprint_name: Asset name of the Blueprint.
            graph_name:     Graph to add to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'node_type', and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_flip_flop_node", {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_switch_on_int_node(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a Switch on Int node (K2Node_SwitchInteger) to a Blueprint graph.

        Routes execution to Case 0, Case 1, ... Default based on an integer input.

        Args:
            blueprint_name: Asset name of the Blueprint.
            graph_name:     Graph to add to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'node_type', and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_switch_on_int_node", {
                "blueprint_name": blueprint_name,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_spawn_actor_node(
        ctx: Context,
        blueprint_name: str,
        actor_class: str = "",
        graph_name: str = "EventGraph",
        node_position: Optional[List[float]] = None,
    ) -> Dict:
        """Add a SpawnActorFromClass node (K2Node_SpawnActorFromClass) to a Blueprint graph.

        Spawns a new actor of the given class at a given transform.
        Pins: execute, Class, SpawnTransform, CollisionHandlingOverride,
              Owner, Instigator, then, ReturnValue (actor ref).

        Args:
            blueprint_name: Asset name of the Blueprint.
            actor_class:    Short class name to pin as default (e.g. 'BP_AggroBot1').
                            Leave empty to leave the Class pin unwired.
            graph_name:     Graph to add to. Default 'EventGraph'.
            node_position:  Optional [X, Y] canvas position.

        Returns:
            Dict with 'node_id', 'node_name', 'node_type', 'actor_class', and 'pins'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_spawn_actor_node", {
                "blueprint_name": blueprint_name,
                "actor_class":    actor_class,
                "graph_name":     graph_name,
                "node_position":  node_position,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ===================================================================
    # Phase 2: Comment nodes and node repositioning (L-018, L-019)
    # ===================================================================

    @mcp.tool()
    def add_blueprint_comment_node(
        ctx: Context,
        blueprint_name: str,
        comment_text: str = "Comment",
        graph_name: str = "EventGraph",
        node_position: Optional[List[float]] = None,
        width: float = 400.0,
        height: float = 200.0,
        color: Optional[List[float]] = None,
    ) -> Dict:
        """Add a comment box (UEdGraphNode_Comment) to a Blueprint graph.

        Comment boxes are visual organisers that group related nodes.
        They do not affect logic.

        Args:
            blueprint_name: Asset name of the Blueprint.
            comment_text:   Text shown in the comment header.
            graph_name:     Graph to add to. Default 'EventGraph'.
            node_position:  [X, Y] top-left corner of the comment box.
            width:          Width in units (default 400).
            height:         Height in units (default 200).
            color:          Optional [R, G, B, A] color in 0..1 range.
                            Defaults to white semi-transparent.

        Returns:
            Dict with 'node_id', 'node_name', 'comment_text',
            'pos_x', 'pos_y', 'width', 'height'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if node_position is None:
                node_position = [0, 0]
            params: Dict = {
                "blueprint_name": blueprint_name,
                "comment_text":   comment_text,
                "graph_name":     graph_name,
                "node_position":  node_position,
                "width":          width,
                "height":         height,
            }
            if color is not None:
                params["color"] = color
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_blueprint_comment_node", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def move_blueprint_node(
        ctx: Context,
        blueprint_name: str,
        node_id: str,
        node_position: List[float],
        graph_name: str = "EventGraph",
    ) -> Dict:
        """Reposition an existing node on the Blueprint graph canvas.

        Useful for tidying up a graph after programmatic construction.

        Args:
            blueprint_name: Asset name of the Blueprint.
            node_id:        GUID or short name of the node to move.
            node_position:  New [X, Y] canvas position.
            graph_name:     Graph containing the node. Default 'EventGraph'.

        Returns:
            Dict with 'node_id', 'node_name', 'new_pos_x', 'new_pos_y'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("move_blueprint_node", {
                "blueprint_name": blueprint_name,
                "node_id":        node_id,
                "node_position":  node_position,
                "graph_name":     graph_name,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ===================================================================
    # Phase 3: Variable default values (L-013)
    # ===================================================================

    @mcp.tool()
    def get_blueprint_variable_defaults(
        ctx: Context,
        blueprint_name: str,
        variable_name: str = "",
    ) -> Dict:
        """Read the default value(s) of Blueprint member variables.

        Returns both the FBPVariableDescription.DefaultValue (the value
        stored in the Blueprint asset) and the live CDO value exported as text.

        Args:
            blueprint_name: Asset name of the Blueprint.
            variable_name:  If specified, only return this variable.
                            Leave empty to return ALL variables.

        Returns:
            Dict with 'blueprint', 'count', and 'variables' array.
            Each variable entry has: 'variable_name', 'variable_type',
            'default_value', 'tooltip', and optionally 'cdo_value'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params: Dict = {"blueprint_name": blueprint_name}
            if variable_name:
                params["variable_name"] = variable_name
            return unreal.send_command("get_blueprint_variable_defaults", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_blueprint_variable_default(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        default_value: str,
    ) -> Dict:
        """Set the default value of a Blueprint member variable.

        Updates both the FBPVariableDescription record and the CDO
        property via ImportText so changes are visible immediately
        without a full recompile.

        Args:
            blueprint_name: Asset name of the Blueprint.
            variable_name:  Exact name of the variable to update.
            default_value:  New default value as a string (e.g. '42', 'true',
                            '(X=1.0,Y=2.0,Z=3.0)' for vectors).

        Returns:
            Dict with 'blueprint', 'variable_name', 'default_value', 'success'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("set_blueprint_variable_default", {
                "blueprint_name": blueprint_name,
                "variable_name":  variable_name,
                "default_value":  default_value,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ===================================================================
    # Phase 4: Blueprint component inspection (L-020)
    # ===================================================================

    @mcp.tool()
    def get_blueprint_components(
        ctx: Context,
        blueprint_name: str,
    ) -> Dict:
        """List all components of a Blueprint (SCS + native C++ components).

        For each SCS component the response includes its class name and
        any properties that differ from the component class defaults.

        Args:
            blueprint_name: Asset name of the Blueprint.

        Returns:
            Dict with 'blueprint', 'count', and 'components' array.
            Each component entry has: 'name', 'source' ('SCS' or 'NativeC++'),
            'class', and optionally 'modified_properties' (dict of prop -> value).
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("get_blueprint_components", {
                "blueprint_name": blueprint_name,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ===================================================================
    # Phase 5: NavMesh setup (L-014)
    # ===================================================================

    @mcp.tool()
    def setup_navmesh(
        ctx: Context,
        extent: Optional[List[float]] = None,
        location: Optional[List[float]] = None,
        rebuild: bool = True,
    ) -> Dict:
        """Spawn or resize a NavMeshBoundsVolume in the current editor level.

        If a NavMeshBoundsVolume already exists it will be resized and
        repositioned instead of creating a duplicate.  After placement the
        navigation system is optionally rebuilt so AI characters can
        immediately use the navmesh.

        Args:
            extent:   Half-extents [X, Y, Z] in cm (default [5000, 5000, 500]).
                      The volume will cover a 2*X by 2*Y by 2*Z area.
            location: Centre location [X, Y, Z] in cm (default [0, 0, 0]).
            rebuild:  Trigger a nav-system rebuild after placement (default True).

        Returns:
            Dict with 'action' ('created' or 'resized_existing'),
            'actor' (volume name), 'rebuilt', 'success'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            if extent is None:
                extent = [5000.0, 5000.0, 500.0]
            if location is None:
                location = [0.0, 0.0, 0.0]
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("setup_navmesh", {
                "extent":   extent,
                "location": location,
                "rebuild":  rebuild,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_blueprint_variables(
        ctx: Context,
        blueprint_name: str,
        category: str = ""
    ) -> Dict[str, Any]:
        """
        List all member variables defined in a Blueprint class.

        Returns each variable's name, type, default value, and category.
        Use this to inspect existing variables before adding new ones.

        Args:
            blueprint_name: Blueprint asset name (e.g., "BP_MyCharacter")
            category: Optional category filter (empty string = return all)

        Returns:
            Dict with 'variables' list. Each entry has:
              name, type, default_value, category, is_exposed, is_read_only
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params: Dict[str, Any] = {"blueprint_name": blueprint_name}
            if category:
                params["category"] = category
            return unreal.send_command("get_blueprint_variables", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_blueprint_functions(
        ctx: Context,
        blueprint_name: str,
    ) -> Dict[str, Any]:
        """
        List all function graphs defined inside a Blueprint class.

        Returns each function's name, input pins, and output pins.
        Use this before calling add_blueprint_function_node on a custom function,
        or before modifying an existing function graph.

        Args:
            blueprint_name: Blueprint asset name (e.g., "BP_MyCharacter")

        Returns:
            Dict with 'functions' list. Each entry has:
              name, inputs (list of {name, type}), outputs (list of {name, type})
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("get_blueprint_functions", {
                "blueprint_name": blueprint_name,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("Blueprint node tools registered")
