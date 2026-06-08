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
    def _structured_comm_result(
        raw: Dict[str, Any],
        *,
        stage: str,
        message: str,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        raw = raw or {}
        error_message = raw.get("error") or raw.get("message") or ""
        success = raw.get("success") is not False and raw.get("status") != "error" and not raw.get("error")
        return {
            "success": success,
            "stage": stage,
            "message": message if success else (error_message or f"{stage} failed"),
            "inputs": inputs,
            "outputs": {
                key: value
                for key, value in raw.items()
                if key not in {"success", "status", "message", "error"}
            } if success else {},
            "warnings": [],
            "errors": [] if success else [error_message or f"{stage} failed"],
            "log_tail": [],
        }

    # ── Event Dispatchers ─────────────────────────────────────────────────────

    @mcp.tool()
    def add_event_dispatcher(
        ctx: Context,
        blueprint_name: str,
        dispatcher_name: str,
        params: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Add an Event Dispatcher to a Blueprint.

        Event Dispatchers allow Blueprints to broadcast events that other
        Blueprints can listen to and respond to.

        Args:
            blueprint_name: Blueprint name
            dispatcher_name: Name of the event dispatcher
            params: List of parameter dicts with 'name' and 'type' keys
                    e.g., [{"name": "DamageAmount", "type": "Float"}]

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            add_event_dispatcher(blueprint_name="/Game/MCP_Test/BP_Example", dispatcher_name="ExampleName")"""
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
        """Add a 'Call [EventDispatcher]' node to the Blueprint's Event Graph.

        Args:
            blueprint_name: Blueprint containing the dispatcher
            dispatcher_name: Name of the event dispatcher
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with 'node_id'

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            call_event_dispatcher(blueprint_name="/Game/MCP_Test/BP_Example", dispatcher_name="ExampleName")"""
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
        """Bind an event to another Blueprint's Event Dispatcher.
        Adds a 'Bind Event to [Dispatcher]' node.

        Args:
            blueprint_name: Blueprint that is binding to the dispatcher
            dispatcher_blueprint: Blueprint that owns the dispatcher
            dispatcher_name: Name of the event dispatcher
            target_variable_name: Variable holding a reference to the dispatcher owner
            node_position: Optional [X, Y] graph position

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            bind_event_to_dispatcher(blueprint_name="/Game/MCP_Test/BP_Example", dispatcher_blueprint="/Game/MCP_Test/BP_Example", dispatcher_name="ExampleName")"""
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
        """Add an 'Unbind Event from [Dispatcher]' node.

        Args:
            blueprint_name: Blueprint name
            dispatcher_name: Dispatcher to unbind from
            node_position: Optional graph position

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            unbind_event_from_dispatcher(blueprint_name="/Game/MCP_Test/BP_Example", dispatcher_name="ExampleName")"""
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
        """Add a variable to hold a direct reference to another Blueprint.

        This is the Direct Blueprint Communication pattern - you store a reference
        to another actor and call its functions directly.

        Args:
            blueprint_name: Blueprint that will hold the reference
            target_blueprint: Blueprint class to reference
            variable_name: Variable name for the reference
            is_exposed: Make editable in editor (required to assign via editor)

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            add_direct_blueprint_reference(blueprint_name="/Game/MCP_Test/BP_Example", target_blueprint="/Game/MCP_Test/BP_Example", variable_name="ExampleName")"""
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
        """Add a Cast To [ClassName] node.

        Casting is used to convert a generic object/actor reference to a specific
        type, allowing access to that Blueprint's unique variables and functions.

        Args:
            blueprint_name: Blueprint name
            target_class: Class to cast to (e.g., "BP_MyCharacter", "ACharacter")
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with 'node_id'; pins: 'Object' input, 'then'/'Cast Failed' outputs,
            'As [ClassName]' output for the cast result

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            add_cast_node(blueprint_name="/Game/MCP_Test/BP_Example", target_class="Actor")"""
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
        """Create a Blueprint Interface asset.

        Blueprint Interfaces define a contract that multiple Blueprints can
        implement - useful for calling functions on actors without knowing their type.

        Args:
            interface_name: Interface asset name (e.g., "BPI_Interactable")
            functions: List of function dicts:
                       [{"name": "Interact", "params": [{"name": "Caller", "type": "Actor"}]}]
            path: Content browser path

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            create_blueprint_interface(interface_name="ExampleName")"""
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
        """Make a Blueprint implement a Blueprint Interface.

        Args:
            blueprint_name: Blueprint that will implement the interface
            interface_name: Interface asset name

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            implement_blueprint_interface(blueprint_name="/Game/MCP_Test/BP_Example", interface_name="ExampleName")"""
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
        """Add a 'Message [FunctionName]' interface call node.

        Interface messages can be sent to any actor implementing the interface
        without knowing its exact class.

        Args:
            blueprint_name: Calling Blueprint
            interface_name: Interface name
            function_name: Interface function to call
            node_position: Optional graph position

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            add_interface_function_node(blueprint_name="/Game/MCP_Test/BP_Example", interface_name="ExampleName", function_name="ExampleName")"""
        if node_position is None:
            node_position = [0, 0]
        return _send("add_interface_function_node", {
            "blueprint_name": blueprint_name,
            "interface_name": interface_name,
            "function_name": function_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_interface_event_node(
        ctx: Context,
        blueprint_name: str,
        interface_name: str,
        function_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """Add an implementation event node for a Blueprint Interface function.

        Use this after `implement_blueprint_interface` when a generated actor
        needs to handle interface-driven interactions such as Interact, Damage,
        or Use without hard references to a concrete class.

        Args:
            blueprint_name: Blueprint implementing the interface.
            interface_name: Blueprint Interface asset name or path.
            function_name: Interface function to implement as an event.
            node_position: Optional [X, Y] graph position.

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            add_interface_event_node(blueprint_name="/Game/MCP_Test/BP_Door", interface_name="/Game/MCP_Test/BPI_Interactable", function_name="Interact")
        """
        if node_position is None:
            node_position = [0, 0]
        inputs = {
            "blueprint_name": blueprint_name,
            "interface_name": interface_name,
            "function_name": function_name,
            "node_position": node_position,
        }
        raw = _send("add_interface_event_node", inputs)
        return _structured_comm_result(
            raw,
            stage="add_interface_event_node",
            message=f"Added interface event '{function_name}' to '{blueprint_name}'",
            inputs=inputs,
        )

    # ── Functions & Macros ────────────────────────────────────────────────────

    @mcp.tool()
    def add_custom_event(
        ctx: Context,
        blueprint_name: str,
        event_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """Add a custom event node to a Blueprint Event Graph.

        Use this for generated gameplay entry points such as StartEncounter,
        SpawnWave, ApplyReward, or any named event that other nodes can call.

        Args:
            blueprint_name: Blueprint asset name or path.
            event_name: Custom event name.
            node_position: Optional [X, Y] graph position.

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            add_custom_event(blueprint_name="/Game/MCP_Test/BP_Encounter", event_name="StartEncounter")
        """
        if node_position is None:
            node_position = [0, 0]
        inputs = {
            "blueprint_name": blueprint_name,
            "event_name": event_name,
            "node_position": node_position,
        }
        raw = _send("add_custom_event", inputs)
        return _structured_comm_result(
            raw,
            stage="add_custom_event",
            message=f"Added custom event '{event_name}' to '{blueprint_name}'",
            inputs=inputs,
        )

    @mcp.tool()
    def call_custom_event(
        ctx: Context,
        blueprint_name: str,
        target_blueprint: str,
        event_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """Add a function-call node for a custom event defined on another Blueprint.

        Use this for generated Blueprint communication where one authored actor
        needs to trigger a named event exposed by another generated Blueprint.

        Args:
            blueprint_name: Calling Blueprint asset name or path.
            target_blueprint: Blueprint that owns the custom event.
            event_name: Custom event/function name to call.
            node_position: Optional [X, Y] graph position.

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            call_custom_event(blueprint_name="/Game/MCP_Test/BP_Button", target_blueprint="/Game/MCP_Test/BP_Door", event_name="OpenDoor")
        """
        if node_position is None:
            node_position = [0, 0]
        inputs = {
            "blueprint_name": blueprint_name,
            "target_blueprint": target_blueprint,
            "event_name": event_name,
            "node_position": node_position,
        }
        raw = _send("call_custom_event", inputs)
        return _structured_comm_result(
            raw,
            stage="call_custom_event",
            message=f"Added custom event call '{event_name}' in '{blueprint_name}'",
            inputs=inputs,
        )

    @mcp.tool()
    def add_custom_function(
        ctx: Context,
        blueprint_name: str,
        function_name: str,
        inputs: List[Dict[str, str]] = None,
        outputs: List[Dict[str, str]] = None,
        is_pure: bool = False
    ) -> Dict[str, Any]:
        """Add a custom function to a Blueprint.

        Functions have their own local variable scope, can return values,
        and are reusable across the Blueprint.

        Args:
            blueprint_name: Blueprint name
            function_name: Function name
            inputs: List of input params [{"name": "DamageIn", "type": "Float"}]
            outputs: List of output params [{"name": "HealthOut", "type": "Float"}]
            is_pure: Pure functions have no exec pin (like math functions)

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            add_custom_function(blueprint_name="/Game/MCP_Test/BP_Example", function_name="ExampleName")"""
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
        """Add a custom Macro to a Blueprint.

        Macros are like functions but they exist within a single Blueprint,
        support latent nodes (Delay, etc.), and can have multiple exec outputs.

        Args:
            blueprint_name: Blueprint name
            macro_name: Macro name
            inputs: Input tunnel parameters
            outputs: Output tunnel parameters

        KB: see knowledge_base/02_BLUEPRINT_COMMUNICATION.md#overview
        Example:
            add_custom_macro(blueprint_name="/Game/MCP_Test/BP_Example", macro_name="ExampleName")"""
        return _send("add_custom_macro", {
            "blueprint_name": blueprint_name,
            "macro_name": macro_name,
            "inputs": inputs or [],
            "outputs": outputs or []
        })

    logger.info("Communication tools registered")
