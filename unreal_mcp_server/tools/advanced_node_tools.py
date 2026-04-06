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

    logger.info("Advanced node tools registered")
