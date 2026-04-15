"""
Data Structures & Flow Control Tools.
Covers Chapter 13 from the Blueprint book:
- Arrays, Sets, Maps
- Enumerations, Structures, Data Tables
- Flow Control: Switch, FlipFlop, Sequence, ForEach, DoOnce, DoN, Gate, MultiGate
"""
import logging
import base64
import os
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

    # ── Set Container Operations (Ch. 13) ─────────────────────────────────────

    @mcp.tool()
    def add_set_contains_node(
        ctx: Context,
        blueprint_name: str,
        set_variable: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Set CONTAINS node to check if an element exists in a Set.

        From Ch. 13: Returns True if the set contains the specified element.

        Args:
            blueprint_name: Blueprint to add the node to
            set_variable: Set variable name
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_set_contains_node", {
            "blueprint_name": blueprint_name,
            "set_variable": set_variable,
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_union_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Set UNION node - combine two sets (removes duplicates).

        From Ch. 13: Returns a new set containing all elements from both sets.

        Args:
            blueprint_name: Blueprint to add the node to
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_set_operation_node", {
            "blueprint_name": blueprint_name,
            "operation": "Union",
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_intersection_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Set INTERSECTION node - elements common to both sets.

        From Ch. 13: Returns elements that exist in BOTH input sets.

        Args:
            blueprint_name: Blueprint to add the node to
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_set_operation_node", {
            "blueprint_name": blueprint_name,
            "operation": "Intersection",
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_difference_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Set DIFFERENCE node - elements in first set but not in second.

        From Ch. 13: Returns elements from set A that are NOT in set B.

        Args:
            blueprint_name: Blueprint to add the node to
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_set_operation_node", {
            "blueprint_name": blueprint_name,
            "operation": "Difference",
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_to_array_node(
        ctx: Context,
        blueprint_name: str,
        set_variable: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Set TO ARRAY node - convert a Set to an Array for iteration.

        From Ch. 13: Sets don't have a GET element node, so convert to array
        first if you need to iterate over elements. Note: copying large object
        sets can be expensive.

        Args:
            blueprint_name: Blueprint to add the node to
            set_variable: Set variable name to convert
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_set_to_array_node", {
            "blueprint_name": blueprint_name,
            "set_variable": set_variable,
            "node_position": node_position
        })

    @mcp.tool()
    def add_make_set_node(
        ctx: Context,
        blueprint_name: str,
        element_type: str = "String",
        num_pins: int = 3,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Make Set node to create a Set from individual variables.

        From Ch. 13: Similar to Make Array but creates a Set (no duplicates).

        Args:
            blueprint_name: Blueprint to add the node to
            element_type: Element type for the Set
            num_pins: Number of input element pins
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_make_set_node", {
            "blueprint_name": blueprint_name,
            "element_type": element_type,
            "num_pins": num_pins,
            "node_position": node_position
        })

    # ── Map Container Operations (Ch. 13) ─────────────────────────────────────

    @mcp.tool()
    def add_map_find_node(
        ctx: Context,
        blueprint_name: str,
        map_variable: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Map FIND node - get a value by key (also checks key existence).

        From Ch. 13: The FIND node is like CONTAINS but also returns the value.
        Returns the Value associated with the key, and a bool indicating if the key was found.

        Args:
            blueprint_name: Blueprint to add the node to
            map_variable: Map variable name
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_map_find_node", {
            "blueprint_name": blueprint_name,
            "map_variable": map_variable,
            "node_position": node_position
        })

    @mcp.tool()
    def add_map_contains_node(
        ctx: Context,
        blueprint_name: str,
        map_variable: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Map CONTAINS node - check if a key exists in a Map.

        From Ch. 13: Returns True if the Map contains an element with the given key.
        Does NOT return the value (use FIND for that).

        Args:
            blueprint_name: Blueprint to add the node to
            map_variable: Map variable name
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_map_contains_node", {
            "blueprint_name": blueprint_name,
            "map_variable": map_variable,
            "node_position": node_position
        })

    @mcp.tool()
    def add_map_keys_node(
        ctx: Context,
        blueprint_name: str,
        map_variable: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Map KEYS node - copy all Map keys to an Array.

        From Ch. 13: Returns an array of all keys in the map.
        Used to iterate over all entries in the map.

        Args:
            blueprint_name: Blueprint to add the node to
            map_variable: Map variable name
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_map_keys_node", {
            "blueprint_name": blueprint_name,
            "map_variable": map_variable,
            "node_position": node_position
        })

    @mcp.tool()
    def add_map_values_node(
        ctx: Context,
        blueprint_name: str,
        map_variable: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Map VALUES node - copy all Map values to an Array.

        From Ch. 13: Returns an array of all values in the map.

        Args:
            blueprint_name: Blueprint to add the node to
            map_variable: Map variable name
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_map_values_node", {
            "blueprint_name": blueprint_name,
            "map_variable": map_variable,
            "node_position": node_position
        })

    @mcp.tool()
    def add_make_map_node(
        ctx: Context,
        blueprint_name: str,
        key_type: str = "String",
        value_type: str = "Float",
        num_pairs: int = 3,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Make Map node to create a Map from key-value pairs.

        From Ch. 13: Creates a Map literal from individual key-value pin inputs.

        Args:
            blueprint_name: Blueprint to add the node to
            key_type: Key type
            value_type: Value type
            num_pairs: Number of key-value pair input pins
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_make_map_node", {
            "blueprint_name": blueprint_name,
            "key_type": key_type,
            "value_type": value_type,
            "num_pairs": num_pairs,
            "node_position": node_position
        })

    # ── Array Advanced Nodes (Ch. 13) ─────────────────────────────────────────

    @mcp.tool()
    def add_make_array_node(
        ctx: Context,
        blueprint_name: str,
        element_type: str = "Actor",
        num_pins: int = 3,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Make Array node to create an Array from individual variables.

        From Ch. 13: Used to create point light arrays in Level Blueprints,
        spawn point lists, or any array built from known variables.

        Args:
            blueprint_name: Blueprint to add the node to
            element_type: Array element type
            num_pins: Number of input element pins
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_make_array_node", {
            "blueprint_name": blueprint_name,
            "element_type": element_type,
            "num_pins": num_pins,
            "node_position": node_position
        })

    @mcp.tool()
    def add_object_type_make_array_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a real K2Node_MakeArray node typed as EObjectTypeQuery (byte enum).
        This is used to provide a valid 'Object Types' array input to
        SphereOverlapActors / SphereOverlapComponents nodes.
        Defaults to ObjectTypeQuery3 (WorldDynamic) on the first pin.

        Args:
            blueprint_name: Blueprint to add the node to
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_object_type_make_array_node", {
            "blueprint_name": blueprint_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_random_array_item_node(
        ctx: Context,
        blueprint_name: str,
        array_variable: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Random Array Item node to get a random element from an Array.

        From Ch. 13 (BP_RandomSpawner): Returns a random element from the array.
        Used to randomly select a spawn point from an array of Target Points.

        Args:
            blueprint_name: Blueprint to add the node to
            array_variable: Array variable name
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_random_array_item_node", {
            "blueprint_name": blueprint_name,
            "array_variable": array_variable,
            "node_position": node_position
        })

    @mcp.tool()
    def create_random_spawner_blueprint(
        ctx: Context,
        name: str = "BP_RandomSpawner",
        folder_path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create the BP_RandomSpawner Blueprint from Ch. 13.

        Creates a Blueprint that:
        - Has a TargetPoints array (Actor Object Reference, Instance Editable)
        - Has a SpawnClass variable (Actor Class Reference, Instance Editable)
        - On BeginPlay: validates both, picks a random TargetPoint from the array,
          gets its transform, and spawns an actor of the SpawnClass at that location

        Args:
            name: Blueprint name
            folder_path: Content browser folder
        """
        return _send("create_random_spawner_blueprint", {
            "name": name,
            "folder_path": folder_path
        })

    # ── Struct / Enum / DataTable Extended Nodes (Ch. 13) ──────────────────────

    @mcp.tool()
    def add_break_struct_node(
        ctx: Context,
        blueprint_name: str,
        struct_type: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Break [StructType] node to extract individual member values.

        From Ch. 13: Break Struct takes a struct as input and exposes all
        member variables as output pins. Used to read individual fields.

        Also see Split Struct Pin (right-click a struct pin in the graph).

        Args:
            blueprint_name: Blueprint to add the node to
            struct_type: Struct type name (e.g., \"FVector\", \"FEnemyData\", \"FHitResult\")
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_break_struct_node", {
            "blueprint_name": blueprint_name,
            "struct_type": struct_type,
            "node_position": node_position
        })

    @mcp.tool()
    def add_make_struct_node(
        ctx: Context,
        blueprint_name: str,
        struct_type: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Make [StructType] node to construct a struct from member values.

        From Ch. 13: Make Struct takes all member variables as input pins
        and outputs the assembled struct. Used to construct FTransform,
        FVector, custom structs, etc.

        Args:
            blueprint_name: Blueprint to add the node to
            struct_type: Struct type name (e.g., \"FVector\", \"FTransform\", \"FEnemyData\")
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_make_struct_node", {
            "blueprint_name": blueprint_name,
            "struct_type": struct_type,
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_data_table_row_node(
        ctx: Context,
        blueprint_name: str,
        data_table_variable: str = "",
        row_name: str = "",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a GetDataTableRow node to look up a row in a Data Table.

        From Ch. 13: Retrieves a struct of data by row name from a Data Table.
        Returns the row struct and a bool indicating if the row was found.

        Args:
            blueprint_name: Blueprint to add the node to
            data_table_variable: Data Table asset variable name or path
            row_name: Default row name to look up
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_get_data_table_row_node", {
            "blueprint_name": blueprint_name,
            "data_table_variable": data_table_variable,
            "row_name": row_name,
            "node_position": node_position
        })

    # ── Asset Import Tools ────────────────────────────────────────────────────

    @mcp.tool()
    def import_sound_asset_from_sandbox(
        ctx: Context,
        local_file_path: str,
        asset_name: str,
        destination_path: str = "/Game/Audio",
        loop: bool = False,
    ) -> Dict[str, Any]:
        """
        Import an audio file that lives on the sandbox (Linux side) into the UE5
        Content Browser as a SoundWave asset.

        The file at `local_file_path` is read, base64-encoded, embedded in a Python
        script that runs inside UE5, decoded back to bytes, written to the Windows temp
        folder on the UE machine, and then imported with AssetTools.

        For audio files that already exist on the UE5 Windows machine (e.g. downloaded
        via a browser or placed manually), use import_sound_asset instead — it is
        simpler and does not require base64 transfer.

        Typical workflow:
            1. Use audio_generation to create a sound → get a Genspark file URL
            2. Use DownloadFileWrapper to save the file to /home/user/webapp/<name>.mp3
            3. Call import_sound_asset_from_sandbox(
                   local_file_path="/home/user/webapp/<name>.mp3", ...)

        Args:
            local_file_path:  Absolute path to the audio file on the sandbox
                              (e.g. "/home/user/webapp/SFX_TurretFire.mp3")
            asset_name:       Name for the new UE SoundWave asset (no spaces, e.g. "SFX_TurretFire")
            destination_path: UE content-browser folder (default "/Game/Audio")
            loop:             If True, sets the SoundWave looping flag

        Returns:
            Dict with 'asset_path' (e.g. "/Game/Audio/SFX_TurretFire.SFX_TurretFire")
            on success, or 'error' on failure.
        """
        if not os.path.isfile(local_file_path):
            return {"error": f"File not found on sandbox: {local_file_path}"}

        ext = os.path.splitext(local_file_path)[1].lower() or ".mp3"
        with open(local_file_path, "rb") as fh:
            audio_b64 = base64.b64encode(fh.read()).decode("utf-8")

        python_code = f"""
import unreal, base64, os, tempfile, sys

audio_b64  = {audio_b64!r}
asset_name = {asset_name!r}
dest_path  = {destination_path!r}
ext        = {ext!r}
do_loop    = {loop!r}

# 1. Decode bytes and write to Windows temp
audio_bytes = base64.b64decode(audio_b64)
tmp_file = os.path.join(tempfile.gettempdir(), asset_name + ext)
with open(tmp_file, 'wb') as f:
    f.write(audio_bytes)
sys.stdout.write(f'[MCP] Wrote {{len(audio_bytes)}} bytes to {{tmp_file}}\\n')
sys.stdout.flush()

# 2. Import via AssetTools
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
task = unreal.AssetImportTask()
task.filename         = tmp_file
task.destination_path = dest_path
task.destination_name = asset_name
task.replace_existing = True
task.automated        = True
task.save             = True
asset_tools.import_asset_tasks([task])

imported = task.get_editor_property('imported_object_paths')
if not imported:
    sys.stdout.write('[MCP] ERROR: Import returned no paths\\n')
    sys.stdout.flush()
else:
    asset_path = imported[0]
    sys.stdout.write(f'[MCP] Imported sound: {{asset_path}}\\n')
    sys.stdout.flush()

    # 3. Optionally enable looping
    if do_loop:
        sw = unreal.load_asset(asset_path)
        if sw and isinstance(sw, unreal.SoundWave):
            sw.set_editor_property('looping', True)
            unreal.EditorAssetLibrary.save_asset(asset_path)
            sys.stdout.write(f'[MCP] Set looping=True on {{asset_path}}\\n')
"""
        resp = _send("exec_python", {"code": python_code})
        inner = resp.get("result", resp)
        output = inner.get("output", resp.get("output", ""))

        if "[MCP] ERROR:" in output or not inner.get("success", True):
            return {"error": output or "Import failed inside UE"}

        asset_path = None
        for line in output.splitlines():
            if "[MCP] Imported sound:" in line:
                asset_path = line.split("[MCP] Imported sound:")[-1].strip()
                break
        if not asset_path:
            asset_path = f"{destination_path}/{asset_name}.{asset_name}"

        return {
            "success": True,
            "asset_path": asset_path,
            "asset_name": asset_name,
            "destination_path": destination_path,
            "output": output,
        }

    @mcp.tool()
    def wire_play_sound_to_blueprint(
        ctx: Context,
        blueprint_name: str,
        sound_asset_path: str,
        after_node_id: str,
        node_position: List[float] = None,
        use_play_at_location: bool = False,
    ) -> Dict[str, Any]:
        """
        Add a PlaySound2D (or PlaySoundAtLocation) node to a Blueprint wired after
        a specific node. Used to attach imported sound assets to Blueprint events.

        Args:
            blueprint_name:       Blueprint to modify (e.g. "BP_LaserTurret")
            sound_asset_path:     UE content-browser path of the SoundWave
                                  (e.g. "/Game/Audio/SFX_TurretFire.SFX_TurretFire")
            after_node_id:        Full node GUID — the 'then' pin of this node will connect
                                  to the new PlaySound node's 'execute' pin
            node_position:        [X, Y] graph position for the new node
            use_play_at_location: If True, use PlaySoundAtLocation (3D); otherwise PlaySound2D (2D/UI)
        """
        if node_position is None:
            node_position = [0, 0]

        func_name = "PlaySoundAtLocation" if use_play_at_location else "PlaySound2D"

        # 1. Add the PlaySound node
        add_resp = _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "function_name": func_name,
            "node_position": node_position,
        })
        if add_resp.get("status") == "error":
            return {"error": f"Could not add {func_name} node: {add_resp.get('error', '')}"}

        result_inner = add_resp.get("result", add_resp)
        node_id = result_inner.get("node_id", "")
        if not node_id:
            return {"error": "No node_id returned from add_blueprint_function_node"}

        # 2. Set the Sound pin default value to the asset path
        pin_resp = _send("set_node_pin_value", {
            "blueprint_name": blueprint_name,
            "node_id": node_id,
            "pin_name": "Sound",
            "value": sound_asset_path,
        })

        # 3. Wire after_node_id.then -> PlaySound.execute
        wire_resp = _send("connect_blueprint_nodes", {
            "blueprint_name": blueprint_name,
            "source_node_id": after_node_id,
            "source_pin": "then",
            "target_node_id": node_id,
            "target_pin": "execute",
        })

        # 4. Compile
        compile_resp = _send("compile_blueprint", {"blueprint_name": blueprint_name})

        return {
            "success": True,
            "play_sound_node_id": node_id,
            "function": func_name,
            "sound_asset_path": sound_asset_path,
            "wire_result": wire_resp.get("result", {}),
            "compile_had_errors": compile_resp.get("result", {}).get("had_errors", False),
        }

    logger.info("Data tools registered")
