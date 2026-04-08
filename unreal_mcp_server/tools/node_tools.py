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
            return unreal.send_command("get_blueprint_graphs", {
                "blueprint_name": blueprint_name,
            }) or {}
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

    logger.info("Blueprint node tools registered")
