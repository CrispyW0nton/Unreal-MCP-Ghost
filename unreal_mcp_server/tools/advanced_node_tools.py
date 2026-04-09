"""
Advanced Node Tools - Flow control, math, variable get/set, debug, timing nodes.
Extends node_tools.py with all remaining Blueprint node types from the book.
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


def register_advanced_node_tools(mcp: FastMCP):

    # ── Flow Control Nodes ────────────────────────────────────────────────────

    @mcp.tool()
    def add_branch_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Branch (if/else) node to a Blueprint.

        The Branch node takes a boolean condition and routes execution
        to either the 'True' or 'False' output pin.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with 'node_id'; pins: 'Condition' input, 'True'/'False' outputs
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_branch_node", {
            "blueprint_name": blueprint_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_sequence_node(
        ctx: Context,
        blueprint_name: str,
        num_outputs: int = 3,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Sequence node that executes outputs in order.

        Sequence nodes execute 'Then 0', 'Then 1', 'Then 2', etc. in sequence.
        Useful for organizing multiple sequential actions.

        Args:
            blueprint_name: Blueprint name
            num_outputs: Number of output execution pins (2-10)
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_sequence_node", {
            "blueprint_name": blueprint_name,
            "num_outputs": num_outputs,
            "node_position": node_position
        })

    @mcp.tool()
    def add_flipflop_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Flip Flop node that alternates between A and B outputs.

        On the first call it executes 'A', on the second call 'B',
        then back to 'A', etc. Also provides 'IsA' boolean output.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_flipflop_node", {
            "blueprint_name": blueprint_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_do_once_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Do Once node that executes exactly one time.

        After the first execution, subsequent calls are ignored
        until the 'Reset' input is triggered.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_do_once_node", {
            "blueprint_name": blueprint_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_do_n_node(
        ctx: Context,
        blueprint_name: str,
        n: int = 3,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Do N node that executes a specified number of times.

        After N executions, subsequent calls are blocked until Reset.

        Args:
            blueprint_name: Blueprint name
            n: Maximum number of executions (default: 3)
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_do_n_node", {
            "blueprint_name": blueprint_name,
            "n": n,
            "node_position": node_position
        })

    @mcp.tool()
    def add_gate_node(
        ctx: Context,
        blueprint_name: str,
        start_closed: bool = False,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Gate node that controls execution flow.

        When open, the 'Exit' pin fires on each 'Enter'. 
        Use 'Open', 'Close', and 'Toggle' inputs to control state.

        Args:
            blueprint_name: Blueprint name
            start_closed: Whether the gate starts closed
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_gate_node", {
            "blueprint_name": blueprint_name,
            "start_closed": start_closed,
            "node_position": node_position
        })

    @mcp.tool()
    def add_while_loop_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a While Loop node.

        Executes 'Loop Body' while condition is true, then fires 'Completed'.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_while_loop_node", {
            "blueprint_name": blueprint_name,
            "node_position": node_position
        })

    # ── Variable Get/Set Nodes ────────────────────────────────────────────────

    @mcp.tool()
    def add_get_variable_node(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get [VariableName]' node to read a variable's value.

        Args:
            blueprint_name: Blueprint name
            variable_name: Variable to get (must exist in the Blueprint)
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with 'node_id'; output pin named same as variable
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_variable_get_node", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_variable_node(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set [VariableName]' node to write to a variable.

        Args:
            blueprint_name: Blueprint name
            variable_name: Variable to set (must exist in the Blueprint)
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with 'node_id'; has exec pins + value input pin
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_variable_set_node", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "node_position": node_position
        })

    # ── Debug & Utility Nodes ─────────────────────────────────────────────────

    @mcp.tool()
    def add_print_string_node(
        ctx: Context,
        blueprint_name: str,
        message: str = "Hello World",
        duration: float = 2.0,
        color: List[float] = [0.0, 0.66, 1.0],
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Print String node (shows debug message on screen).

        Args:
            blueprint_name: Blueprint name
            message: Default string to print (can be overridden by connection)
            duration: How long message stays on screen
            color: [R, G, B] text color
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetSystemLibrary",
            "function_name": "PrintString",
            "params": {
                "InString": message,
                "Duration": duration,
                "TextColor": color + [1.0]
            },
            "node_position": node_position
        })

    @mcp.tool()
    def add_delay_node(
        ctx: Context,
        blueprint_name: str,
        duration: float = 1.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Delay node (latent - waits before continuing).

        Delay is a latent node - it allows the Blueprint to pause execution
        for a specified duration without blocking the game thread.

        Args:
            blueprint_name: Blueprint name
            duration: Delay in seconds
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetSystemLibrary",
            "function_name": "Delay",
            "params": {"Duration": duration},
            "node_position": node_position
        })

    @mcp.tool()
    def add_timeline_node(
        ctx: Context,
        blueprint_name: str,
        timeline_name: str,
        tracks: List[Dict[str, Any]] = None,
        length: float = 1.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Timeline node for smooth interpolation animations.

        Timelines play float/vector curves over time - great for
        doors opening, lights fading, etc.

        Args:
            blueprint_name: Blueprint name
            timeline_name: Name for the timeline
            tracks: List of track dicts:
                    [{"name": "Alpha", "type": "Float", "keys": [[0,0],[1,1]]}]
            length: Total timeline duration in seconds
            node_position: Optional graph position

        Returns:
            Dict with 'node_id'; pins: 'Play', 'Reverse', 'Stop', 'Update', 'Finished'
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_timeline_node", {
            "blueprint_name": blueprint_name,
            "timeline_name": timeline_name,
            "tracks": tracks or [{"name": "Alpha", "type": "Float", "keys": [[0.0, 0.0], [1.0, 1.0]]}],
            "length": length,
            "node_position": node_position
        })

    # ── Math & Utility Nodes ──────────────────────────────────────────────────

    @mcp.tool()
    def add_math_node(
        ctx: Context,
        blueprint_name: str,
        operation: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a math operation node.

        Args:
            blueprint_name: Blueprint name
            operation: Math operation:
                       "Add_FloatFloat", "Subtract_FloatFloat",
                       "Multiply_FloatFloat", "Divide_FloatFloat",
                       "Add_IntInt", "Subtract_IntInt",
                       "Multiply_IntInt", "Divide_IntInt",
                       "VSize" (vector length), "Normalize" (vector normalize),
                       "Clamp", "Lerp", "FInterpTo", "VInterpTo",
                       "RandomFloat", "RandomFloatInRange",
                       "RandomInt", "RandomIntInRange",
                       "Max_Float", "Min_Float", "Abs_Float",
                       "Sin", "Cos", "Sqrt", "Power"
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": operation,
            "params": {},
            "node_position": node_position
        })

    @mcp.tool()
    def add_line_trace_node(
        ctx: Context,
        blueprint_name: str,
        trace_type: str = "LineTraceSingleByChannel",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Line Trace node (raycast from point A to point B).

        Line traces check for physics collision along a line.
        Useful for hit detection, visibility checks, etc.

        Args:
            blueprint_name: Blueprint name
            trace_type: Trace function:
                        "LineTraceSingleByChannel" - single hit by collision channel
                        "LineTraceSingleByObjectType" - single hit by object type
                        "SphereTraceSingleByChannel" - sphere sweep
                        "BoxTraceSingleByChannel" - box sweep
                        "MultiLineTraceSingleByChannel" - all hits
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetSystemLibrary",
            "function_name": trace_type,
            "params": {},
            "node_position": node_position
        })

    @mcp.tool()
    def add_macro_node(
        ctx: Context,
        blueprint_name: str,
        macro_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a macro call node to a Blueprint.

        Args:
            blueprint_name: Blueprint containing the macro
            macro_name: Name of the macro to call
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_macro_node", {
            "blueprint_name": blueprint_name,
            "macro_name": macro_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_comment_box(
        ctx: Context,
        blueprint_name: str,
        comment_text: str,
        position: List[float] = None,
        size: List[float] = [400.0, 200.0],
        color: List[float] = [0.2, 0.2, 0.2, 0.5]
    ) -> Dict[str, Any]:
        """
        Add a comment box to a Blueprint graph (for documentation).

        Args:
            blueprint_name: Blueprint name
            comment_text: Comment text
            position: [X, Y] graph position
            size: [Width, Height] of the comment box
            color: [R, G, B, A] box color
        """
        if position is None:
            position = [0, 0]
        return _send("add_comment_box", {
            "blueprint_name": blueprint_name,
            "comment_text": comment_text,
            "position": position,
            "size": size,
            "color": color
        })

    @mcp.tool()
    def add_construct_object_node(
        ctx: Context,
        blueprint_name: str,
        object_class: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Construct Object from Class' node.

        Used to create UObject instances at runtime (non-Actor objects).

        Args:
            blueprint_name: Blueprint name
            object_class: Class to construct
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "SpawnObject",
            "params": {"ObjectClass": object_class},
            "node_position": node_position
        })

    @mcp.tool()
    def add_spawn_actor_node(
        ctx: Context,
        blueprint_name: str,
        actor_class: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Spawn Actor from Class' node (SpawnActor).

        Creates a new actor in the world at runtime.

        Args:
            blueprint_name: Blueprint name
            actor_class: Actor class to spawn (e.g., "BP_Projectile")
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "BeginSpawningActorFromClass",
            "params": {"ActorClass": actor_class},
            "node_position": node_position
        })

    @mcp.tool()
    def add_destroy_actor_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Destroy Actor' node.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "K2_DestroyActor",
            "params": {},
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_player_character_node(
        ctx: Context,
        blueprint_name: str,
        player_index: int = 0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Player Character' node.

        Args:
            blueprint_name: Blueprint name
            player_index: Player index (usually 0)
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "GetPlayerCharacter",
            "params": {"PlayerIndex": player_index},
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_player_controller_node(
        ctx: Context,
        blueprint_name: str,
        player_index: int = 0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Player Controller' node.

        Args:
            blueprint_name: Blueprint name
            player_index: Player index (usually 0)
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "GetPlayerController",
            "params": {"PlayerIndex": player_index},
            "node_position": node_position
        })

    @mcp.tool()
    def add_open_level_node(
        ctx: Context,
        blueprint_name: str,
        level_name: str = "",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an 'Open Level (by Name)' node for level loading/switching.

        Args:
            blueprint_name: Blueprint name
            level_name: Default level to open (can be connected via pin)
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "OpenLevel",
            "params": {"LevelName": level_name},
            "node_position": node_position
        })

    @mcp.tool()
    def add_apply_damage_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an 'Apply Damage' node.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "ApplyDamage",
            "params": {},
            "node_position": node_position
        })

    @mcp.tool()
    def add_play_sound_node(
        ctx: Context,
        blueprint_name: str,
        sound_asset: str = "",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Play Sound at Location' node.

        Args:
            blueprint_name: Blueprint name
            sound_asset: Sound asset path
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "PlaySoundAtLocation",
            "params": {"Sound": sound_asset},
            "node_position": node_position
        })

    @mcp.tool()
    def build_complete_blueprint_graph(
        ctx: Context,
        blueprint_name: str,
        graph_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build an entire Blueprint graph from a definition dict.

        This is a high-level helper that creates nodes and connects them
        based on a declarative definition.

        Args:
            blueprint_name: Blueprint name
            graph_definition: Dict describing the graph:
              {
                "nodes": [
                  {"id": "begin_play", "type": "event", "event": "ReceiveBeginPlay", "pos": [0, 0]},
                  {"id": "print", "type": "function", "target": "UKismetSystemLibrary",
                   "function": "PrintString", "params": {"InString": "Hello!"}, "pos": [300, 0]}
                ],
                "connections": [
                  {"from": "begin_play", "from_pin": "then", "to": "print", "to_pin": "execute"}
                ]
              }

        Returns:
            Dict with results for each node and connection
        """
        results = {"nodes": {}, "connections": []}
        node_ids = {}  # local_id -> actual UE node_id

        nodes = graph_definition.get("nodes", [])
        connections = graph_definition.get("connections", [])

        for node_def in nodes:
            local_id = node_def.get("id", "")
            node_type = node_def.get("type", "")
            pos = node_def.get("pos", [0, 0])

            if node_type == "event":
                res = _send("add_blueprint_event_node", {
                    "blueprint_name": blueprint_name,
                    "event_name": node_def.get("event", "ReceiveBeginPlay"),
                    "node_position": pos
                })
            elif node_type == "function":
                res = _send("add_blueprint_function_node", {
                    "blueprint_name": blueprint_name,
                    "target": node_def.get("target", "self"),
                    "function_name": node_def.get("function", ""),
                    "params": node_def.get("params", {}),
                    "node_position": pos
                })
            elif node_type == "variable_get":
                res = _send("add_variable_get_node", {
                    "blueprint_name": blueprint_name,
                    "variable_name": node_def.get("variable", ""),
                    "node_position": pos
                })
            elif node_type == "variable_set":
                res = _send("add_variable_set_node", {
                    "blueprint_name": blueprint_name,
                    "variable_name": node_def.get("variable", ""),
                    "node_position": pos
                })
            elif node_type == "branch":
                res = _send("add_branch_node", {
                    "blueprint_name": blueprint_name,
                    "node_position": pos
                })
            elif node_type == "sequence":
                res = _send("add_sequence_node", {
                    "blueprint_name": blueprint_name,
                    "num_outputs": node_def.get("num_outputs", 3),
                    "node_position": pos
                })
            else:
                res = {"success": False, "message": f"Unknown node type: {node_type}"}

            results["nodes"][local_id] = res

            # Extract node_id from result
            if isinstance(res, dict):
                if "result" in res and isinstance(res["result"], dict):
                    actual_id = res["result"].get("node_id", "")
                else:
                    actual_id = res.get("node_id", "")
                if actual_id:
                    node_ids[local_id] = actual_id

        # Create connections
        for conn in connections:
            from_local = conn.get("from", "")
            to_local = conn.get("to", "")
            from_pin = conn.get("from_pin", "then")
            to_pin = conn.get("to_pin", "execute")

            from_id = node_ids.get(from_local)
            to_id = node_ids.get(to_local)

            if from_id and to_id:
                conn_res = _send("connect_blueprint_nodes", {
                    "blueprint_name": blueprint_name,
                    "source_node_id": from_id,
                    "source_pin": from_pin,
                    "target_node_id": to_id,
                    "target_pin": to_pin
                })
                results["connections"].append(conn_res)
            else:
                results["connections"].append({
                    "success": False,
                    "message": f"Could not find node IDs for {from_local} -> {to_local}"
                })

        _send("compile_blueprint", {"blueprint_name": blueprint_name})
        return results

    # ── Miscellaneous Blueprint Nodes (Ch. 15) ─────────────────────────────────

    @mcp.tool()
    def add_select_node(
        ctx: Context,
        blueprint_name: str,
        index_type: str = "Integer",
        option_type: str = "String",
        num_options: int = 2,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Select node to choose a value based on an index.

        From Ch. 15: The Select node returns the value matching the index input.
        It's a cleaner alternative to chains of Branch nodes for multi-way selection.

        Index type can be: Integer, Enum, Boolean, or Byte.
        Option type can be any type (Actor Class Reference, String, Float, etc.)

        Example from the book: Based on DifficultyLevel enum (Easy/Normal/Hard),
        select which Boss Blueprint class to spawn.

        Args:
            blueprint_name: Blueprint to add the node to
            index_type: Type for the Index input (\"Integer\", \"Enum\", \"Boolean\", \"Byte\")
            option_type: Type for the Option inputs and Return Value
            num_options: Number of option pins to create
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_select_node", {
            "blueprint_name": blueprint_name,
            "index_type": index_type,
            "option_type": option_type,
            "num_options": num_options,
            "node_position": node_position
        })

    @mcp.tool()
    def add_teleport_node(
        ctx: Context,
        blueprint_name: str,
        use_self: bool = True,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Teleport node to safely move an actor to a new location.

        From Ch. 15: The Teleport node moves an actor to a specified location,
        but unlike SetActorLocation, if there's an obstacle at the destination,
        the actor is moved to a nearby valid location to avoid overlap.

        Example from the book: BP_TeleportPlatform - when the player overlaps
        the platform, they teleport to the Next Teleport Platform location.

        Args:
            blueprint_name: Blueprint to add the node to
            use_self: If True, teleport self; if False, pass an Actor input
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self" if use_self else "",
            "function_name": "K2_TeleportTo",
            "params": {},
            "node_position": node_position
        })

    @mcp.tool()
    def add_format_text_node(
        ctx: Context,
        blueprint_name: str,
        format_string: str = "{Name} wins with {Score} points",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Format Text node to build text from a template with parameters.

        From Ch. 15: Format Text uses {ParameterName} delimiters in the format
        string to create input pins dynamically. Each {Name} becomes an input pin.

        Example: format=\"{Name} wins the round with {Score} points\"
        Creates input pins for Name and Score; output is the formatted text.

        Args:
            blueprint_name: Blueprint to add the node to
            format_string: Template with {parameter_name} placeholders
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_format_text_node", {
            "blueprint_name": blueprint_name,
            "format_string": format_string,
            "node_position": node_position
        })

    @mcp.tool()
    def add_math_expression_node(
        ctx: Context,
        blueprint_name: str,
        expression: str = "(A + B) * C",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Math Expression node (collapsed graph from a math formula string).

        From Ch. 15: The Math Expression node creates a collapsed graph based on
        a typed expression. Variable names in the expression become input pins,
        and the result is the Return Value output pin.

        Example from the book: (PlayerLuck/5) * (EnemyHP/30)
        Creates input pins PlayerLuck and EnemyHP.

        Args:
            blueprint_name: Blueprint to add the node to
            expression: Mathematical expression string (variables become input pins)
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_math_expression_node", {
            "blueprint_name": blueprint_name,
            "expression": expression,
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_view_target_with_blend_node(
        ctx: Context,
        blueprint_name: str,
        blend_time: float = 1.0,
        blend_func: str = "VTBlend_Linear",
        blend_exp: float = 0.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a SetViewTargetWithBlend node to switch cameras smoothly.

        From Ch. 15: Used to switch the player's view between different cameras
        (e.g., entering a treasure room activates a security camera, or switching
        to a cinematic camera during a cutscene). The New View Target input is
        usually a Camera Actor reference.

        Args:
            blueprint_name: Blueprint to add the node to (PlayerController)
            blend_time: Duration of the camera transition in seconds
            blend_func: Blend function (\"VTBlend_Linear\", \"VTBlend_Cubic\",
                       \"VTBlend_EaseIn\", \"VTBlend_EaseOut\", \"VTBlend_EaseInOut\")
            blend_exp: Exponent for cubic/ease blend functions
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "PlayerController",
            "function_name": "SetViewTargetWithBlend",
            "params": {
                "BlendTime": blend_time,
                "BlendFunc": blend_func,
                "BlendExp": blend_exp
            },
            "node_position": node_position
        })

    @mcp.tool()
    def add_attach_actor_to_component_node(
        ctx: Context,
        blueprint_name: str,
        location_rule: str = "KeepRelative",
        rotation_rule: str = "KeepRelative",
        scale_rule: str = "KeepRelative",
        weld_simulated_bodies: bool = False,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an AttachActorToComponent node.

        From Ch. 15: Attaches an actor to a component at runtime. Used for
        dynamic attachment (e.g., weapon pickup, mounting to vehicles).

        Attachment rules:
        - \"KeepRelative\": Maintain current relative transform
        - \"KeepWorld\": Maintain current world transform (recalculate relative)
        - \"SnapToTarget\": Reset to component's origin

        Args:
            blueprint_name: Blueprint to add the node to
            location_rule: Location attachment rule
            rotation_rule: Rotation attachment rule
            scale_rule: Scale attachment rule
            weld_simulated_bodies: Weld physics bodies together
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "Actor",
            "function_name": "K2_AttachActorToComponent",
            "params": {
                "LocationRule": location_rule,
                "RotationRule": rotation_rule,
                "ScaleRule": scale_rule,
                "bWeldSimulatedBodies": weld_simulated_bodies
            },
            "node_position": node_position
        })

    @mcp.tool()
    def add_enable_disable_input_node(
        ctx: Context,
        blueprint_name: str,
        enable: bool = True,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an Enable Input or Disable Input node to control actor input reception.

        From Ch. 15: Enable Input allows an actor to receive player input events.
        Disable Input removes input handling. Requires passing a PlayerController reference.

        Use cases:
        - Disable input during cutscenes
        - Enable input only when player is in range of an interactive object
        - Menu screens disable game input

        Args:
            blueprint_name: Blueprint to add the node to
            enable: True = EnableInput, False = DisableInput
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        func_name = "EnableInput" if enable else "DisableInput"
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": func_name,
            "params": {},
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_input_mode_node(
        ctx: Context,
        blueprint_name: str,
        input_mode: str = "GameAndUI",
        mouse_lock_mode: str = "DoNotLock",
        flush_input: bool = True,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Set Input Mode node to control where player input goes.

        From Ch. 15: Controls whether input goes to the game, UI, or both.
        Essential for pause menus and interactive UI screens.

        Input modes:
        - \"GameOnly\": Input handled only by game (no UI interaction)
        - \"UIOnly\": Input handled only by UI (game inputs blocked)
        - \"GameAndUI\": Both game and UI handle input (most flexible)

        Example from the book: Show Win/Pause menu -> SetInputModeUIOnly,
        Resume game -> SetInputModeGameOnly

        Args:
            blueprint_name: Blueprint to add the node to
            input_mode: \"GameOnly\", \"UIOnly\", or \"GameAndUI\"
            mouse_lock_mode: \"DoNotLock\", \"LockOnCapture\", \"LockAlways\", \"LockInFullscreen\"
            flush_input: Clear all pending input when mode changes
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        func_map = {
            "GameOnly": "SetInputMode_GameOnly",
            "UIOnly": "SetInputMode_UIOnlyEx",
            "GameAndUI": "SetInputMode_GameAndUIEx"
        }
        func_name = func_map.get(input_mode, "SetInputMode_GameAndUIEx")
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "PlayerController",
            "function_name": func_name,
            "params": {
                "MouseLockMode": mouse_lock_mode,
                "bFlushInput": flush_input
            },
            "node_position": node_position
        })

    @mcp.tool()
    def add_nearly_equal_float_node(
        ctx: Context,
        blueprint_name: str,
        tolerance: float = 0.0001,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a NearlyEqual (float) node to compare floats with tolerance.

        From Ch. 11: Used to check if PlayerHealth is approximately 0 (player dies).
        Float comparison with == can fail due to floating-point precision,
        so NearlyEqual checks if |A - B| < Tolerance instead.

        Args:
            blueprint_name: Blueprint to add the node to
            tolerance: Maximum allowed difference for equality check
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "KismetMathLibrary",
            "function_name": "NearlyEqual_FloatFloat",
            "params": {"ErrorTolerance": tolerance},
            "node_position": node_position
        })

    @mcp.tool()
    def add_print_text_node(
        ctx: Context,
        blueprint_name: str,
        duration: float = 2.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Print Text node (used in Ch. 18 with Format Text output).

        Like Print String but works with Text type values (localizable text).
        Used with the Format Text node output in the dice roll library example.

        Args:
            blueprint_name: Blueprint to add the node to
            duration: Display duration on screen
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "KismetSystemLibrary",
            "function_name": "PrintText",
            "params": {"Duration": duration},
            "node_position": node_position
        })

    @mcp.tool()
    def add_append_string_node(
        ctx: Context,
        blueprint_name: str,
        string_a: str = "",
        string_b: str = "",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an Append (string concatenation) node.

        From Ch. 18 (Actor Component test): Combines two strings into one.
        Used to build \"Levelled up to \" + CurrentLevel display string.

        Args:
            blueprint_name: Blueprint to add the node to
            string_a: First string (A pin default value)
            string_b: Second string (B pin default value)
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "KismetStringLibrary",
            "function_name": "Concat_StrStr",
            "params": {"A": string_a, "B": string_b},
            "node_position": node_position
        })

    @mcp.tool()
    def add_spawn_actor_from_class_node(
        ctx: Context,
        blueprint_name: str,
        actor_class: str = "",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a SpawnActorFromClass node to instantiate an Actor at runtime.

        From Ch. 3 and Ch. 10: Core node for spawning Blueprints at runtime.
        Used to spawn enemies, projectiles, pickups, particles, effects.

        Takes a Class input and a SpawnTransform (Location, Rotation, Scale),
        returns a reference to the spawned Actor.

        Args:
            blueprint_name: Blueprint to add the node to
            actor_class: Default Actor class to spawn (can be set via pin)
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "GameplayStatics",
            "function_name": "BeginSpawningActorFromClass",
            "params": {"ActorClass": actor_class},
            "node_position": node_position
        })

    @mcp.tool()
    def add_is_valid_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an IsValid macro node to check if an object reference is valid (non-null).

        From Ch. 3, 4, 11, 13: Used before accessing object references to prevent
        crashes from accessing null/destroyed actors. Returns Is Valid and Is Not Valid
        execution pins.

        Args:
            blueprint_name: Blueprint to add the node to
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "KismetSystemLibrary",
            "function_name": "IsValid",
            "params": {},
            "node_position": node_position
        })

    @mcp.tool()
    def add_is_valid_class_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an IsValidClass node to check if a class reference is valid.

        From Ch. 13 (BP_RandomSpawner): Used to validate a Class Reference variable
        before passing it to SpawnActorFromClass. Returns True if the class is valid.

        Args:
            blueprint_name: Blueprint to add the node to
            node_position: [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "KismetSystemLibrary",
            "function_name": "IsValidClass",
            "params": {},
            "node_position": node_position
        })

    # ─── Chapter 2: Operators and Blueprint Programming ──────────────────────────

    @mcp.tool()
    def add_arithmetic_operator_node(
        ctx: Context,
        blueprint_name: str,
        operator: str = "Add",
        operand_type: str = "Float",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an arithmetic operator node (Add, Subtract, Multiply, Divide, Modulo).

        Ch.2: Arithmetic operators create expressions in Blueprints:
        - Add (+): Sum two values
        - Subtract (-): Difference between values
        - Multiply (*): Product of two values
        - Divide (/): Quotient of two values
        - Modulo (%): Remainder after division (integers only)

        Args:
            blueprint_name: Blueprint name
            operator: "Add", "Subtract", "Multiply", "Divide", "Modulo", "Power"
            operand_type: "Float", "Integer", "Vector", "Int64"
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_math_node", {
            "blueprint_name": blueprint_name,
            "operation": operator,
            "operand_type": operand_type,
            "node_position": node_position
        })

    @mcp.tool()
    def add_relational_operator_node(
        ctx: Context,
        blueprint_name: str,
        operator: str = "Equal",
        operand_type: str = "Float",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a relational (comparison) operator node returning a Boolean.

        Ch.2: Relational operators compare two values and return True/False:
        - Equal (==): Both values are the same
        - NotEqual (!=): Values differ
        - Greater (>): Left > Right
        - GreaterEqual (>=): Left >= Right
        - Less (<): Left < Right
        - LessEqual (<=): Left <= Right

        Args:
            blueprint_name: Blueprint name
            operator: "Equal", "NotEqual", "Greater", "GreaterEqual", "Less", "LessEqual"
            operand_type: "Float", "Integer", "String", "Name", "Vector", "Object"
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_math_node", {
            "blueprint_name": blueprint_name,
            "operation": operator,
            "operand_type": operand_type,
            "node_position": node_position
        })

    @mcp.tool()
    def add_logical_operator_node(
        ctx: Context,
        blueprint_name: str,
        operator: str = "AND",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a logical (boolean) operator node.

        Ch.2: Logical operators combine boolean conditions:
        - AND: True only if BOTH inputs are true
        - OR: True if EITHER input is true
        - NOT: Inverts a boolean (True→False, False→True)
        - XOR: True only if inputs are DIFFERENT (exclusive OR)

        Args:
            blueprint_name: Blueprint name
            operator: "AND", "OR", "NOT", "XOR"
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_math_node", {
            "blueprint_name": blueprint_name,
            "operation": operator,
            "operand_type": "Boolean",
            "node_position": node_position
        })

    # ─── Chapter 3: Actor Lifecycle and OOP ─────────────────────────────────────

    @mcp.tool()
    def add_construction_script_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Construction Script event node to a Blueprint.

        Ch.3: The Construction Script runs both in-editor and at runtime before
        BeginPlay. Used for procedural setup based on exposed variables,
        like setting mesh, materials, or modifying component transforms.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_event_node", {
            "blueprint_name": blueprint_name,
            "event_name": "UserConstructionScript",
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_all_actors_of_class_node(
        ctx: Context,
        blueprint_name: str,
        actor_class: str = "Actor",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get All Actors Of Class' node.

        Ch.3: Returns an array of all actors of the specified class in the level.
        Used to find patrol points (TargetPoint actors) or iterate over enemies.
        Note: Expensive operation - avoid calling every tick.

        Args:
            blueprint_name: Blueprint name
            actor_class: Class to search for (e.g., "TargetPoint", "BP_Enemy")
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "GetAllActorsOfClass",
            "params": {"ActorClass": actor_class},
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_actor_of_class_node(
        ctx: Context,
        blueprint_name: str,
        actor_class: str = "Actor",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Actor Of Class' node - returns the first actor found.

        Ch.3/4: Finds the first actor of the specified class in the level.
        Useful for getting a reference to a unique actor like GameMode or PlayerController.

        Args:
            blueprint_name: Blueprint name
            actor_class: Class to search for
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "GetActorOfClass",
            "params": {"ActorClass": actor_class},
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_game_mode_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Game Mode' node.

        Ch.3: Returns the current GameMode. Cast the result to your custom
        GameMode class (e.g., BP_FPSGameMode) to access its properties/functions.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "GetGameMode",
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_game_instance_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Game Instance' node.

        Ch.3: Returns the Game Instance, which persists across level loads.
        Cast to your custom GameInstance class to access persistent data.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "GetGameInstance",
            "node_position": node_position
        })

    @mcp.tool()
    def add_reroute_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Reroute node to organize wire routing in the graph.

        Ch.4: Reroute nodes are dot-shaped nodes used to bend wires and improve
        readability of complex Blueprint graphs without changing logic.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_reroute_node", {
            "blueprint_name": blueprint_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_clamp_node(
        ctx: Context,
        blueprint_name: str,
        operand_type: str = "Float",
        min_value: float = 0.0,
        max_value: float = 1.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Clamp' node to constrain a value within a range.

        Used throughout the book (Ch.6, 8): Clamps health, stamina, ammo values
        between min and max so they never exceed valid ranges.

        Args:
            blueprint_name: Blueprint name
            operand_type: "Float" or "Integer"
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        func_name = "FClamp" if operand_type == "Float" else "Clamp"
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": func_name,
            "params": {"Min": min_value, "Max": max_value},
            "node_position": node_position
        })

    @mcp.tool()
    def add_lerp_node(
        ctx: Context,
        blueprint_name: str,
        operand_type: str = "Float",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Lerp' (Linear Interpolation) node.

        Ch.6: Used for smooth transitions like FOV zoom and stamina drain.
        Lerp(A, B, Alpha) = A + Alpha * (B - A). Alpha ranges 0.0-1.0.

        Args:
            blueprint_name: Blueprint name
            operand_type: "Float", "Vector", "Rotator", "LinearColor"
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        func_map = {
            "Float": "Lerp",
            "Vector": "VLerp",
            "Rotator": "RLerp",
            "LinearColor": "LinearColorLerp"
        }
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": func_map.get(operand_type, "Lerp"),
            "node_position": node_position
        })

    @mcp.tool()
    def add_random_float_in_range_node(
        ctx: Context,
        blueprint_name: str,
        min_value: float = 0.0,
        max_value: float = 1.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Random Float In Range' node.

        Ch.13: Used in BP_RandomSpawner and procedural generation to get random values.
        Returns a random float between Min and Max (inclusive).

        Args:
            blueprint_name: Blueprint name
            min_value: Minimum float value
            max_value: Maximum float value
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": "RandomFloatInRange",
            "params": {"Min": min_value, "Max": max_value},
            "node_position": node_position
        })

    @mcp.tool()
    def add_random_integer_in_range_node(
        ctx: Context,
        blueprint_name: str,
        min_value: int = 0,
        max_value: int = 10,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Random Integer In Range' node.

        Ch.13, Ch.18: Used for dice roll library and random spawning.
        Returns a random integer between Min and Max (inclusive).

        Args:
            blueprint_name: Blueprint name
            min_value: Minimum integer value
            max_value: Maximum integer value
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": "RandomIntegerInRange",
            "params": {"Min": min_value, "Max": max_value},
            "node_position": node_position
        })

    @mcp.tool()
    def add_abs_node(
        ctx: Context,
        blueprint_name: str,
        operand_type: str = "Float",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an 'Abs' (Absolute Value) node.

        Returns the absolute (always-positive) value of a number.
        Useful for computing distances and speeds without sign.

        Args:
            blueprint_name: Blueprint name
            operand_type: "Float" or "Integer"
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        func_name = "Abs" if operand_type == "Float" else "Abs_Int"
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": func_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_min_max_node(
        ctx: Context,
        blueprint_name: str,
        operation: str = "Min",
        operand_type: str = "Float",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Min' or 'Max' node returning the smaller/larger of two values.

        Used in health/stamina clamping and scoring systems throughout the book.

        Args:
            blueprint_name: Blueprint name
            operation: "Min" or "Max"
            operand_type: "Float" or "Integer"
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        func_map = {
            "Min_Float": "Min",
            "Max_Float": "Max",
            "Min_Integer": "Min_Int",
            "Max_Integer": "Max_Int"
        }
        key = f"{operation}_{operand_type}"
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": func_map.get(key, "Min"),
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_timer_by_function_name_node(
        ctx: Context,
        blueprint_name: str,
        function_name: str = "SpawnEnemy",
        timer_rate: float = 5.0,
        looping: bool = True,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set Timer By Function Name' node for recurring callbacks.

        Ch.10: Used in enemy spawner to periodically call SpawnEnemy.
        Ch.8: Used for stamina regeneration over time.
        Starts a timer that calls the named function after the specified delay.

        Args:
            blueprint_name: Blueprint name
            function_name: Name of the function to call on timer tick
            timer_rate: Time in seconds between calls
            looping: If True, repeats indefinitely
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetSystemLibrary",
            "function_name": "SetTimerByFunctionName",
            "params": {
                "FunctionName": function_name,
                "Time": timer_rate,
                "bLooping": looping
            },
            "node_position": node_position
        })

    @mcp.tool()
    def add_clear_timer_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Clear Timer By Handle' or 'Clear and Invalidate Timer By Handle' node.

        Used to stop a running timer (e.g., stop stamina drain when sprinting ends).

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetSystemLibrary",
            "function_name": "ClearAndInvalidateTimerHandle",
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_delta_seconds_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get World Delta Seconds' node.

        Ch.5: Delta time is the time elapsed since the last frame.
        Used to make movement frame-rate independent: Speed = Distance * DeltaSeconds.
        Always multiply movement values by DeltaSeconds for consistent behavior.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "GetWorldDeltaSeconds",
            "node_position": node_position
        })

    logger.info("Advanced node tools registered")
