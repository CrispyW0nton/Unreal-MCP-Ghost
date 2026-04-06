"""
Blueprint Communication Tools - Event Dispatchers, Casting, Blueprint Interfaces,
Direct References, Level Blueprint Communication.
Covers Chapter 4 from the Blueprint book.
"""
import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = unreal.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as e:
        logger.error(f"Error in {command}: {e}")
        return {"success": False, "message": str(e)}


def register_communication_tools(mcp: FastMCP):

    # ── Event Dispatchers ─────────────────────────────────────────────────────

    @mcp.tool()
    def add_event_dispatcher(
        ctx: Context,
        blueprint_name: str,
        dispatcher_name: str,
        params: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Add an Event Dispatcher to a Blueprint.

        Event Dispatchers allow Blueprints to broadcast events that other
        Blueprints can listen to and respond to.

        Args:
            blueprint_name: Blueprint name
            dispatcher_name: Name of the event dispatcher
            params: List of parameter dicts with 'name' and 'type' keys
                    e.g., [{"name": "DamageAmount", "type": "Float"}]
        """
        return _send("add_event_dispatcher", {
            "blueprint_name": blueprint_name,
            "dispatcher_name": dispatcher_name,
            "params": params or []
        })

    @mcp.tool()
    def call_event_dispatcher(
        ctx: Context,
        blueprint_name: str,
        dispatcher_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Call [EventDispatcher]' node to the Blueprint's Event Graph.

        Args:
            blueprint_name: Blueprint containing the dispatcher
            dispatcher_name: Name of the event dispatcher
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with 'node_id'
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("call_event_dispatcher", {
            "blueprint_name": blueprint_name,
            "dispatcher_name": dispatcher_name,
            "node_position": node_position
        })

    @mcp.tool()
    def bind_event_to_dispatcher(
        ctx: Context,
        blueprint_name: str,
        dispatcher_blueprint: str,
        dispatcher_name: str,
        target_variable_name: str = "",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Bind an event to another Blueprint's Event Dispatcher.
        Adds a 'Bind Event to [Dispatcher]' node.

        Args:
            blueprint_name: Blueprint that is binding to the dispatcher
            dispatcher_blueprint: Blueprint that owns the dispatcher
            dispatcher_name: Name of the event dispatcher
            target_variable_name: Variable holding a reference to the dispatcher owner
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("bind_event_to_dispatcher", {
            "blueprint_name": blueprint_name,
            "dispatcher_blueprint": dispatcher_blueprint,
            "dispatcher_name": dispatcher_name,
            "target_variable_name": target_variable_name,
            "node_position": node_position
        })

    @mcp.tool()
    def unbind_event_from_dispatcher(
        ctx: Context,
        blueprint_name: str,
        dispatcher_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an 'Unbind Event from [Dispatcher]' node.

        Args:
            blueprint_name: Blueprint name
            dispatcher_name: Dispatcher to unbind from
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("unbind_event_from_dispatcher", {
            "blueprint_name": blueprint_name,
            "dispatcher_name": dispatcher_name,
            "node_position": node_position
        })

    # ── Direct References & Casting ───────────────────────────────────────────

    @mcp.tool()
    def add_direct_blueprint_reference(
        ctx: Context,
        blueprint_name: str,
        target_blueprint: str,
        variable_name: str,
        is_exposed: bool = True
    ) -> Dict[str, Any]:
        """
        Add a variable to hold a direct reference to another Blueprint.

        This is the Direct Blueprint Communication pattern - you store a reference
        to another actor and call its functions directly.

        Args:
            blueprint_name: Blueprint that will hold the reference
            target_blueprint: Blueprint class to reference
            variable_name: Variable name for the reference
            is_exposed: Make editable in editor (required to assign via editor)
        """
        return _send("add_blueprint_variable", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "variable_type": f"Object:{target_blueprint}",
            "is_exposed": is_exposed
        })

    @mcp.tool()
    def add_cast_node(
        ctx: Context,
        blueprint_name: str,
        target_class: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Cast To [ClassName] node.

        Casting is used to convert a generic object/actor reference to a specific
        type, allowing access to that Blueprint's unique variables and functions.

        Args:
            blueprint_name: Blueprint name
            target_class: Class to cast to (e.g., "BP_MyCharacter", "ACharacter")
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with 'node_id'; pins: 'Object' input, 'then'/'Cast Failed' outputs,
            'As [ClassName]' output for the cast result
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_cast_node", {
            "blueprint_name": blueprint_name,
            "target_class": target_class,
            "node_position": node_position
        })

    # ── Blueprint Interfaces ──────────────────────────────────────────────────

    @mcp.tool()
    def create_blueprint_interface(
        ctx: Context,
        interface_name: str,
        functions: List[Dict[str, Any]] = None,
        path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a Blueprint Interface asset.

        Blueprint Interfaces define a contract that multiple Blueprints can
        implement - useful for calling functions on actors without knowing their type.

        Args:
            interface_name: Interface asset name (e.g., "BPI_Interactable")
            functions: List of function dicts:
                       [{"name": "Interact", "params": [{"name": "Caller", "type": "Actor"}]}]
            path: Content browser path
        """
        return _send("create_blueprint_interface", {
            "interface_name": interface_name,
            "functions": functions or [],
            "path": path
        })

    @mcp.tool()
    def implement_blueprint_interface(
        ctx: Context,
        blueprint_name: str,
        interface_name: str
    ) -> Dict[str, Any]:
        """
        Make a Blueprint implement a Blueprint Interface.

        Args:
            blueprint_name: Blueprint that will implement the interface
            interface_name: Interface asset name
        """
        return _send("implement_blueprint_interface", {
            "blueprint_name": blueprint_name,
            "interface_name": interface_name
        })

    @mcp.tool()
    def add_interface_function_node(
        ctx: Context,
        blueprint_name: str,
        interface_name: str,
        function_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Message [FunctionName]' interface call node.

        Interface messages can be sent to any actor implementing the interface
        without knowing its exact class.

        Args:
            blueprint_name: Calling Blueprint
            interface_name: Interface name
            function_name: Interface function to call
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_interface_function_node", {
            "blueprint_name": blueprint_name,
            "interface_name": interface_name,
            "function_name": function_name,
            "node_position": node_position
        })

    # ── Functions & Macros ────────────────────────────────────────────────────

    @mcp.tool()
    def add_custom_function(
        ctx: Context,
        blueprint_name: str,
        function_name: str,
        inputs: List[Dict[str, str]] = None,
        outputs: List[Dict[str, str]] = None,
        is_pure: bool = False
    ) -> Dict[str, Any]:
        """
        Add a custom function to a Blueprint.

        Functions have their own local variable scope, can return values,
        and are reusable across the Blueprint.

        Args:
            blueprint_name: Blueprint name
            function_name: Function name
            inputs: List of input params [{"name": "DamageIn", "type": "Float"}]
            outputs: List of output params [{"name": "HealthOut", "type": "Float"}]
            is_pure: Pure functions have no exec pin (like math functions)
        """
        return _send("add_custom_function", {
            "blueprint_name": blueprint_name,
            "function_name": function_name,
            "inputs": inputs or [],
            "outputs": outputs or [],
            "is_pure": is_pure
        })

    @mcp.tool()
    def add_custom_macro(
        ctx: Context,
        blueprint_name: str,
        macro_name: str,
        inputs: List[Dict[str, str]] = None,
        outputs: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Add a custom Macro to a Blueprint.

        Macros are like functions but they exist within a single Blueprint,
        support latent nodes (Delay, etc.), and can have multiple exec outputs.

        Args:
            blueprint_name: Blueprint name
            macro_name: Macro name
            inputs: Input tunnel parameters
            outputs: Output tunnel parameters
        """
        return _send("add_custom_macro", {
            "blueprint_name": blueprint_name,
            "macro_name": macro_name,
            "inputs": inputs or [],
            "outputs": outputs or []
        })

    @mcp.tool()
    def create_blueprint_function_library(
        ctx: Context,
        name: str,
        path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a Blueprint Function Library.

        Function Libraries contain static functions accessible from any Blueprint
        without needing an instance - perfect for utility functions.

        Args:
            name: Library asset name (e.g., "BFL_GameUtils")
            path: Content browser path
        """
        return _send("create_blueprint", {
            "name": name,
            "parent_class": "BlueprintFunctionLibrary"
        })

    @mcp.tool()
    def create_blueprint_macro_library(
        ctx: Context,
        name: str,
        path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a Blueprint Macro Library.

        Macro Libraries contain macros reusable across multiple Blueprints.

        Args:
            name: Library asset name (e.g., "BML_FlowControl")
            path: Content browser path
        """
        return _send("create_blueprint_macro_library", {
            "name": name,
            "path": path
        })

    logger.info("Communication tools registered")
