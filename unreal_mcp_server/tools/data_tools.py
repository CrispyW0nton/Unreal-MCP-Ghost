"""
Data Structures & Flow Control Tools.
Covers Chapter 13 from the Blueprint book:
- Arrays, Sets, Maps
- Enumerations, Structures, Data Tables
- Flow Control: Switch, FlipFlop, Sequence, ForEach, DoOnce, DoN, Gate, MultiGate
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


def register_data_tools(mcp: FastMCP):

    # ── Data Structure Assets ─────────────────────────────────────────────────

    @mcp.tool()
    def create_struct(
        ctx: Context,
        struct_name: str,
        fields: List[Dict[str, str]],
        path: str = "/Game/Data"
    ) -> Dict[str, Any]:
        """
        Create a custom Struct asset.

        Structs group related variables together into a single data type,
        making it easy to pass multiple values as one parameter.

        Args:
            struct_name: Struct name (e.g., "S_PlayerData")
            fields: List of field dicts:
                    [{"name": "Health", "type": "Float"},
                     {"name": "PlayerName", "type": "String"},
                     {"name": "Score", "type": "Integer"}]
            path: Content browser path

        Field types: Boolean, Integer, Float, Double, String, Name, Text,
                     Vector, Rotator, Transform, Color, LinearColor
        """
        return _send("create_struct", {
            "struct_name": struct_name,
            "fields": fields,
            "path": path
        })

    @mcp.tool()
    def create_enum(
        ctx: Context,
        enum_name: str,
        values: List[str],
        path: str = "/Game/Data"
    ) -> Dict[str, Any]:
        """
        Create a custom Enumeration (Enum) asset.

        Enums represent a named set of options, perfect for states, types,
        and categories. Use with Switch on Enum nodes.

        Args:
            enum_name: Enum name (e.g., "EWeaponType", "EGameState")
            values: List of enum value names:
                    ["Pistol", "Rifle", "Shotgun", "Sniper"]
            path: Content browser path
        """
        return _send("create_enum", {
            "enum_name": enum_name,
            "values": values,
            "path": path
        })

    @mcp.tool()
    def create_data_table(
        ctx: Context,
        table_name: str,
        row_struct: str,
        path: str = "/Game/Data"
    ) -> Dict[str, Any]:
        """
        Create a DataTable asset.

        DataTables are spreadsheet-like assets that store rows of structured data
        defined by a Struct. Ideal for item databases, enemy stats, level config.

        Args:
            table_name: DataTable asset name (e.g., "DT_WeaponStats")
            row_struct: Struct asset name defining row structure
            path: Content browser path
        """
        return _send("create_data_table", {
            "table_name": table_name,
            "row_struct": row_struct,
            "path": path
        })

    # ── Container Variables ───────────────────────────────────────────────────

    @mcp.tool()
    def add_array_variable(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        element_type: str,
        is_exposed: bool = False
    ) -> Dict[str, Any]:
        """
        Add an Array variable to a Blueprint.

        Arrays are ordered, indexed lists of elements of the same type.

        Args:
            blueprint_name: Blueprint name
            variable_name: Variable name
            element_type: Element type (Boolean, Integer, Float, String, Vector, etc.)
            is_exposed: Expose to editor Details panel
        """
        return _send("add_blueprint_variable", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "variable_type": f"Array:{element_type}",
            "is_exposed": is_exposed
        })

    @mcp.tool()
    def add_map_variable(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        key_type: str,
        value_type: str,
        is_exposed: bool = False
    ) -> Dict[str, Any]:
        """
        Add a Map (dictionary) variable to a Blueprint.

        Maps store key-value pairs with O(1) lookup by key.

        Args:
            blueprint_name: Blueprint name
            variable_name: Variable name
            key_type: Key type (String, Name, Integer, etc.)
            value_type: Value type (Integer, Float, String, Vector, etc.)
            is_exposed: Expose to editor Details panel
        """
        return _send("add_blueprint_variable", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "variable_type": f"Map:{key_type}:{value_type}",
            "is_exposed": is_exposed
        })

    @mcp.tool()
    def add_set_variable(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        element_type: str,
        is_exposed: bool = False
    ) -> Dict[str, Any]:
        """
        Add a Set variable to a Blueprint.

        Sets store unique, unordered elements - useful when you need to track
        membership without duplicates.

        Args:
            blueprint_name: Blueprint name
            variable_name: Variable name
            element_type: Element type (Integer, String, Name, etc.)
            is_exposed: Expose to editor Details panel
        """
        return _send("add_blueprint_variable", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "variable_type": f"Set:{element_type}",
            "is_exposed": is_exposed
        })

    # ── Flow Control Nodes ────────────────────────────────────────────────────

    @mcp.tool()
    def add_switch_on_int_node(
        ctx: Context,
        blueprint_name: str,
        cases: List[int] = None,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Switch on Int' flow control node.

        Routes execution to different paths based on an integer value.

        Args:
            blueprint_name: Blueprint name
            cases: List of integer case values [0, 1, 2, 3]
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with 'node_id'; output pins named by case value + 'Default'
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_switch_node", {
            "blueprint_name": blueprint_name,
            "switch_type": "Int",
            "cases": cases or [0, 1, 2],
            "node_position": node_position
        })

    @mcp.tool()
    def add_switch_on_string_node(
        ctx: Context,
        blueprint_name: str,
        cases: List[str] = None,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Switch on String' flow control node.

        Routes execution based on a string value comparison.

        Args:
            blueprint_name: Blueprint name
            cases: List of string case values ["Walking", "Running", "Dead"]
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_switch_node", {
            "blueprint_name": blueprint_name,
            "switch_type": "String",
            "cases": cases or [],
            "node_position": node_position
        })

    @mcp.tool()
    def add_switch_on_enum_node(
        ctx: Context,
        blueprint_name: str,
        enum_type: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Switch on [EnumType]' flow control node.

        Routes execution based on an enum value - creates one output pin per enum value.

        Args:
            blueprint_name: Blueprint name
            enum_type: Enum class name (e.g., "EWeaponType", "EMovementState")
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_switch_node", {
            "blueprint_name": blueprint_name,
            "switch_type": "Enum",
            "enum_type": enum_type,
            "node_position": node_position
        })

    @mcp.tool()
    def add_multigate_node(
        ctx: Context,
        blueprint_name: str,
        num_outputs: int = 4,
        is_random: bool = False,
        loop: bool = True,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a MultiGate flow control node.

        MultiGate sends execution through multiple output pins in sequence
        (or randomly), optionally looping back to the start.

        Args:
            blueprint_name: Blueprint name
            num_outputs: Number of output pins
            is_random: Randomize execution order
            loop: Loop after reaching the last output
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_multigate_node", {
            "blueprint_name": blueprint_name,
            "num_outputs": num_outputs,
            "is_random": is_random,
            "loop": loop,
            "node_position": node_position
        })

    @mcp.tool()
    def add_for_each_loop_node(
        ctx: Context,
        blueprint_name: str,
        with_break: bool = False,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'For Each Loop' node (iterates over an Array).

        Args:
            blueprint_name: Blueprint name
            with_break: Include a Break input to exit early
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with 'node_id'; pins: 'Array' input, 'Loop Body'/'Completed' outputs,
            'Array Element' and 'Array Index' loop body outputs
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_for_each_loop_node", {
            "blueprint_name": blueprint_name,
            "with_break": with_break,
            "node_position": node_position
        })

    logger.info("Data tools registered")
