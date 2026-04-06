"""
Blueprint Node Tools - Event nodes, function calls, variables, connections.
Ported from: https://github.com/chongdashu/unreal-mcp
"""
import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_blueprint_node_tools(mcp: FastMCP):

    @mcp.tool()
    def add_blueprint_event_node(
        ctx: Context,
        blueprint_name: str,
        event_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an event node to a Blueprint's Event Graph.

        Args:
            blueprint_name: Blueprint name
            event_name: Event name with 'Receive' prefix:
                        ReceiveBeginPlay, ReceiveTick, ReceiveEndPlay,
                        ReceiveHit, ReceiveActorBeginOverlap, ReceiveActorEndOverlap,
                        ReceivePointDamage, ReceiveAnyDamage
            node_position: Optional [X, Y] position in graph

        Returns:
            Dict with 'node_id' of the created node
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
                "event_name": event_name,
                "node_position": node_position
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_input_action_node(
        ctx: Context,
        blueprint_name: str,
        action_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an Input Action event node (legacy input system).

        Args:
            blueprint_name: Blueprint name
            action_name: Input action name (e.g., "Jump", "Fire")
            node_position: Optional [X, Y] position

        Returns:
            Dict with 'node_id'
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
                "action_name": action_name,
                "node_position": node_position
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_function_node(
        ctx: Context,
        blueprint_name: str,
        target: str,
        function_name: str,
        params: Dict[str, Any] = None,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a function call node to a Blueprint.

        Args:
            blueprint_name: Blueprint name
            target: Target class or component name (e.g., "UGameplayStatics",
                    "UKismetMathLibrary", component name, or "self")
            function_name: Function to call (e.g., "GetActorLocation", "SetActorLocation",
                          "OpenLevel", "PrintString", "ApplyDamage")
            params: Default parameter values dict
            node_position: Optional [X, Y] position

        Returns:
            Dict with 'node_id'
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
                "blueprint_name": blueprint_name,
                "target": target,
                "function_name": function_name,
                "params": params,
                "node_position": node_position
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def connect_blueprint_nodes(
        ctx: Context,
        blueprint_name: str,
        source_node_id: str,
        source_pin: str,
        target_node_id: str,
        target_pin: str
    ) -> Dict[str, Any]:
        """
        Connect two nodes in a Blueprint's Event Graph.

        Args:
            blueprint_name: Blueprint name
            source_node_id: GUID of the source node
            source_pin: Output pin name (e.g., "then", "ReturnValue", "Pressed")
            target_node_id: GUID of the target node
            target_pin: Input pin name (e.g., "execute", "Target", "NewLocation")
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("connect_blueprint_nodes", {
                "blueprint_name": blueprint_name,
                "source_node_id": source_node_id,
                "source_pin": source_pin,
                "target_node_id": target_node_id,
                "target_pin": target_pin
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
        default_value: str = ""
    ) -> Dict[str, Any]:
        """
        Add a variable to a Blueprint.

        Args:
            blueprint_name: Blueprint name
            variable_name: Variable name
            variable_type: Type (Boolean, Integer, Float, Double, String, Name, Text,
                          Vector, Rotator, Transform)
            is_exposed: Expose to editor Details panel
            default_value: Optional default value as string

        Returns:
            Dict with 'variable_name' and 'variable_type'
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params = {
                "blueprint_name": blueprint_name,
                "variable_name": variable_name,
                "variable_type": variable_type,
                "is_exposed": is_exposed
            }
            if default_value:
                params["default_value"] = default_value
            return unreal.send_command("add_blueprint_variable", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_get_self_component_reference(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a node that gets a reference to one of the Blueprint's own components.
        Equivalent to dragging a component from the Components panel.

        Args:
            blueprint_name: Blueprint name
            component_name: Component name to reference
            node_position: Optional [X, Y] position

        Returns:
            Dict with 'node_id'
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
                "node_position": node_position
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_blueprint_self_reference(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get a reference to self' node (returns this actor).

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] position

        Returns:
            Dict with 'node_id'
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
                "node_position": node_position
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def find_blueprint_nodes(
        ctx: Context,
        blueprint_name: str,
        node_type: str = None,
        event_type: str = None
    ) -> Dict[str, Any]:
        """
        Find nodes in a Blueprint's Event Graph by type/event name.

        Args:
            blueprint_name: Blueprint name
            node_type: Node type to find ("Event", "Function", "Variable", etc.)
            event_type: Specific event name for Event nodes (e.g., "ReceiveBeginPlay")

        Returns:
            Dict with 'node_guids' array
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("find_blueprint_nodes", {
                "blueprint_name": blueprint_name,
                "node_type": node_type,
                "event_type": event_type
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("Blueprint node tools registered")
