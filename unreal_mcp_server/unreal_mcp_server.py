"""
Unreal Engine MCP Server - Enhanced Edition
Based on: https://github.com/chongdashu/unreal-mcp
Extended with full Blueprint Visual Scripting support as described in:
"Blueprints Visual Scripting for Unreal Engine 5" by Marcos Romero

This server enables AI assistants to control Unreal Engine 5 through the
Model Context Protocol (MCP). Supports three transport modes:

  stdio           — default; for local AI clients (Claude Desktop, Cursor, Windsurf)
                    configured via the client's MCP config JSON.

  sse             — HTTP + Server-Sent Events; for remote AI agents (GenSpark AI
                    Developer, any cloud-based MCP client). Run the server on the
                    developer's machine, then connect from the remote agent.

  streamable-http — Modern HTTP streaming transport (MCP 2025-03-26 spec).
                    Recommended alternative to SSE for new integrations.

Architecture:
  Remote AI Agent (GenSpark)
    → HTTP POST/SSE to MCP server  (MCP_SERVER_HOST:MCP_SERVER_PORT, default 8000)
    → unreal_mcp_server.py  (this file, running on developer's machine)
    → TCP JSON  (UNREAL_HOST:UNREAL_PORT, default 55557, via Playit tunnel if needed)
    → UnrealMCP C++ Plugin inside UE5 Editor

Quick start for remote agents (GenSpark AI Developer):
  # On the developer's machine, run:
  python unreal_mcp_server.py --transport sse --mcp-host 0.0.0.0 --mcp-port 8000 \\
      --unreal-host lie-instability.with.playit.plus --unreal-port 5462

  # Set up a second Playit tunnel pointing to localhost:8000 (or use any port-forward)
  # Then in GenSpark, connect to the MCP server SSE URL:
  #   http://<playit-address>:<playit-port>/sse
"""

import argparse
import asyncio
import logging
import os
import socket
import sys
import json
import functools
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# ─── Async thread-offload patch ─────────────────────────────────────────────
# Problem: FastMCP calls sync tool functions with a plain `return fn(**args)`,
# which blocks the entire asyncio event loop.  While the event loop is blocked:
#   • no SSE writes can be flushed back to the client
#   • no keep-alive pings can be sent
#   • the client sees a stalled connection and raises RemoteProtocolError
# This means tool call RESULTS are accepted (202) but NEVER written to the SSE
# stream — only the `initialize` response (which is pure async) arrives correctly.
#
# Fix: Monkey-patch FuncMetadata.call_fn_with_arg_validation to run sync
# callables in anyio's default thread pool (run_sync_in_worker_thread), exactly
# as FastMCP would do if every tool were declared `async def`.
# Async callables are still awaited directly — no change to async tools.
# This is a one-line patch at startup, requires zero changes across the 321 tool
# functions spread over 21 files.
import anyio
from mcp.server.fastmcp.utilities import func_metadata as _fm_module

async def _threaded_call_fn(self, fn, fn_is_async, arguments_to_validate, arguments_to_pass_directly):
    """Replacement for FuncMetadata.call_fn_with_arg_validation.

    Async functions are awaited directly (unchanged behaviour).
    Sync functions are offloaded to anyio's worker-thread pool so the
    asyncio event loop remains free to flush SSE writes while the blocking
    socket recv() call waits for UE5 to respond.
    """
    arguments_pre_parsed = self.pre_parse_json(arguments_to_validate)
    arguments_parsed_model = self.arg_model.model_validate(arguments_pre_parsed)
    arguments_parsed_dict = arguments_parsed_model.model_dump_one_level()
    arguments_parsed_dict |= arguments_to_pass_directly or {}

    if fn_is_async:
        return await fn(**arguments_parsed_dict)
    else:
        # Run in a worker thread so the event loop stays responsive.
        # functools.partial is used to bind keyword arguments because
        # anyio.to_thread.run_sync only accepts positional args to the callable.
        return await anyio.to_thread.run_sync(
            functools.partial(fn, **arguments_parsed_dict),
            limiter=None,         # use default 40-thread limit
            abandon_on_cancel=False,
        )


_fm_module.FuncMetadata.call_fn_with_arg_validation = _threaded_call_fn  # type: ignore[method-assign]

# ─── Logging ────────────────────────────────────────────────────────────────
# Write to file only (UTF-8 so emoji/arrow chars in KB tool output don't crash).
# On Windows the default cp1252 console encoding cannot encode characters like
# the arrow (\u2192) or book emoji (\U0001F4DA) emitted by knowledge_tools.py.
# Keeping all logging to a file avoids UnicodeEncodeError on the server console.
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('unreal_mcp.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger("UnrealMCP")

# ─── Configuration ──────────────────────────────────────────────────────────
# UE5 plugin connection (the TCP socket to Unreal Engine)
# Priority: CLI flags > environment variables > defaults
UNREAL_HOST = os.environ.get("UNREAL_HOST", "127.0.0.1")
UNREAL_PORT = int(os.environ.get("UNREAL_PORT", "55557"))

# MCP HTTP server settings (used for sse / streamable-http transports)
MCP_SERVER_HOST = os.environ.get("MCP_SERVER_HOST", "0.0.0.0")
MCP_SERVER_PORT = int(os.environ.get("MCP_SERVER_PORT", "8000"))


# ─── Connection Class ────────────────────────────────────────────────────────
class UnrealConnection:
    """Manages TCP connection to the UE5 C++ plugin."""

    def __init__(self):
        self.socket = None
        self.connected = False

    def connect(self) -> bool:
        try:
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
                self.socket = None

            logger.info(f"Connecting to Unreal at {UNREAL_HOST}:{UNREAL_PORT}...")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 131072)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
            self.socket.connect((UNREAL_HOST, UNREAL_PORT))
            self.connected = True
            logger.info("Connected to Unreal Engine")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Unreal: {e}")
            self.connected = False
            return False

    def disconnect(self):
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        self.socket = None
        self.connected = False

    def receive_full_response(self, sock, buffer_size=65536, timeout=30) -> bytes:
        # Per-command timeout:
        #   30 s covers the vast majority of UE5 GameThread operations including
        #   Blueprint compile (5-15 s) and large node graph mutations (10-25 s).
        #   Commands that hang indefinitely on the GameThread (e.g. AddMemberVariable
        #   triggering an asset-registry refresh on an 8 k-asset project, or
        #   StaticLoadObject on an uncached Niagara asset) would previously block
        #   the SSE stream forever.  With a 30 s limit they return a clear timeout
        #   error to the AI instead of silently starving the event loop.
        #
        #   get_actors_in_level (4 256 actors → several hundred KB) is handled
        #   correctly because we read until EOF, not until first valid json.loads.
        #   The 30 s window is more than enough for the TCP transfer itself.
        #
        # IMPORTANT: Do NOT early-return on a successful json.loads() inside the
        # recv loop.  Read until EOF (recv returns b'') so large multi-chunk
        # responses are never truncated.
        chunks = []
        sock.settimeout(timeout)
        try:
            while True:
                chunk = sock.recv(buffer_size)
                if not chunk:
                    # EOF — C++ closed the connection after writing the full response.
                    break
                chunks.append(chunk)
        except socket.timeout:
            # UE5 GameThread is hung — return a descriptive error immediately so
            # the SSE stream stays unblocked for the next tool call.
            raise Exception(
                f"UE5 command timed out after {timeout}s — the GameThread did not "
                "respond in time.  Likely causes: (1) AddMemberVariable / Modify() "
                "triggered an asset-registry refresh on a large project, "
                "(2) StaticLoadObject blocked on an uncached asset, "
                "(3) global class search over 8k+ assets.  "
                "Retry the command; if it consistently times out, compile & save "
                "the Blueprint first, or use exec_python as a workaround."
            )
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise

        if not chunks:
            raise Exception("Connection closed before receiving data")

        data = b''.join(chunks)
        logger.info(f"Received complete response ({len(data)} bytes)")
        # Validate — raises json.JSONDecodeError if incomplete/corrupt.
        try:
            json.loads(data.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise Exception(f"Incomplete JSON response ({len(data)} bytes): {e}")
        return data

    def send_command(self, command: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Send a JSON command to UE5 and return the parsed response."""
        # Commands that legitimately take longer than 30 s get a higher budget.
        # Everything else is capped at 30 s so a hung GameThread never freezes
        # the SSE stream indefinitely.
        _SLOW_COMMANDS = {
            "compile_blueprint",        # 15-90 s for large Blueprints
            "exec_python",              # arbitrary Python; budget 60 s
            "create_blueprint",         # asset creation can be slow on big projects
            "save_blueprint",           # triggers compile + save pipeline
            "get_actors_in_level",      # large TCP payload (4256 actors → several MB)
        }
        timeout = 90 if command in _SLOW_COMMANDS else 30

        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
            self.connected = False

        if not self.connect():
            logger.error("Failed to connect to Unreal Engine for command")
            return None

        try:
            command_obj = {
                "type": command,
                "params": params or {}
            }
            command_json = json.dumps(command_obj) + "\n"
            logger.info(f"Sending command: {command_json[:200]}...")
            self.socket.sendall(command_json.encode('utf-8'))

            response_data = self.receive_full_response(self.socket, timeout=timeout)
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response: {str(response)[:300]}")

            # ── Normalize response envelope ──────────────────────────────
            # The C++ bridge always wraps successful results as:
            #   {"status": "success", "result": { ... actual data ... }}
            # Unwrap that so every caller gets the flat data dict directly.
            # Error responses keep their shape: {"status":"error","error":"..."}
            if response.get("status") == "error":
                error_message = response.get("error") or response.get("message", "Unknown error")
                response["error"] = error_message
            elif response.get("success") is False:
                error_message = response.get("error") or response.get("message", "Unknown error")
                response = {"status": "error", "error": error_message}
            elif response.get("status") == "success" and "result" in response:
                # Unwrap: return the inner result object directly
                response = response["result"]

            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
            self.connected = False
            return response

        except Exception as e:
            logger.error(f"Error sending command: {e}")
            self.connected = False
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
            return {"status": "error", "error": str(e)}


# ─── Global connection ───────────────────────────────────────────────────────
_unreal_connection: UnrealConnection = None


def get_unreal_connection() -> Optional[UnrealConnection]:
    global _unreal_connection
    try:
        if _unreal_connection is None:
            _unreal_connection = UnrealConnection()
            if not _unreal_connection.connect():
                logger.warning("Could not connect to Unreal Engine")
                _unreal_connection = None
        return _unreal_connection
    except Exception as e:
        logger.error(f"Error getting Unreal connection: {e}")
        return None


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    global _unreal_connection
    logger.info("UnrealMCP server starting up")
    try:
        _unreal_connection = get_unreal_connection()
        if _unreal_connection:
            logger.info("Connected to Unreal Engine on startup")
        else:
            logger.warning("Could not connect to Unreal Engine on startup - will retry on first tool call")
    except Exception as e:
        logger.error(f"Error on startup: {e}")
        _unreal_connection = None
    try:
        yield {}
    finally:
        if _unreal_connection:
            _unreal_connection.disconnect()
            _unreal_connection = None
        logger.info("Unreal MCP server shut down")


# ─── MCP Server ──────────────────────────────────────────────────────────────
mcp = FastMCP(
    "UnrealMCP",
    instructions="Full Unreal Engine 5 Blueprint Visual Scripting via Model Context Protocol",
    lifespan=server_lifespan
)

# ─── Import & register all tool modules ─────────────────────────────────────
from tools.editor_tools import register_editor_tools
from tools.blueprint_tools import register_blueprint_tools
from tools.node_tools import register_blueprint_node_tools
from tools.project_tools import register_project_tools
from tools.umg_tools import register_umg_tools
from tools.gameplay_tools import register_gameplay_tools
from tools.animation_tools import register_animation_tools
from tools.ai_tools import register_ai_tools
from tools.data_tools import register_data_tools
from tools.communication_tools import register_communication_tools
from tools.advanced_node_tools import register_advanced_node_tools
# New tools added from deep book study (2nd pass)
from tools.material_tools import register_material_tools
from tools.savegame_tools import register_savegame_tools
from tools.library_tools import register_library_tools
from tools.procedural_tools import register_procedural_tools
from tools.vr_tools import register_vr_tools
from tools.variant_tools import register_variant_tools
# 3rd pass: Physics/Math/Trace tools (Ch.14), expanded AI (Ch.10)
from tools.physics_tools import register_physics_tools
from tools.knowledge_tools import register_knowledge_tools

register_editor_tools(mcp)
register_blueprint_tools(mcp)
register_blueprint_node_tools(mcp)
register_project_tools(mcp)
register_umg_tools(mcp)
register_gameplay_tools(mcp)
register_animation_tools(mcp)
register_ai_tools(mcp)
register_data_tools(mcp)
register_communication_tools(mcp)
register_advanced_node_tools(mcp)
# New tool modules
register_material_tools(mcp)
register_savegame_tools(mcp)
register_library_tools(mcp)
register_procedural_tools(mcp)
register_vr_tools(mcp)
register_variant_tools(mcp)
# 3rd pass additions
register_physics_tools(mcp)
register_knowledge_tools(mcp)


# ─── Info Prompt ─────────────────────────────────────────────────────────────
@mcp.prompt()
def info():
    """Complete guide to Unreal MCP tools covering all Blueprint Visual Scripting features."""
    return """
# Unreal Engine MCP - Complete Blueprint Visual Scripting Tool

## CORE BLUEPRINT TOOLS
- `create_blueprint(name, parent_class)` - Create Blueprint (Actor, Pawn, Character, etc.)
- `add_component_to_blueprint(blueprint_name, component_type, component_name, location, rotation, scale)`
- `set_static_mesh_properties(blueprint_name, component_name, static_mesh)`
- `set_physics_properties(blueprint_name, component_name, simulate_physics, mass, ...)`
- `compile_blueprint(blueprint_name)`
- `set_blueprint_property(blueprint_name, property_name, property_value)`
- `set_component_property(blueprint_name, component_name, property_name, property_value)`

## BLUEPRINT NODE GRAPH
- `add_blueprint_event_node(blueprint_name, event_name, node_position)` - BeginPlay, Tick, etc.
- `add_blueprint_function_node(blueprint_name, target, function_name, params, node_position)`
- `add_blueprint_input_action_node(blueprint_name, action_name, node_position)`
- `connect_blueprint_nodes(blueprint_name, source_node_id, source_pin, target_node_id, target_pin)`
- `add_blueprint_variable(blueprint_name, variable_name, variable_type, is_exposed)`
- `find_blueprint_nodes(blueprint_name, node_type, event_type)`
- `add_blueprint_get_self_component_reference(blueprint_name, component_name, node_position)`
- `add_blueprint_self_reference(blueprint_name, node_position)`

## ADVANCED NODE TOOLS (NEW)
- `add_branch_node(blueprint_name, node_position)` - If/Else branching
- `add_sequence_node(blueprint_name, num_outputs, node_position)` - Sequential execution
- `add_flipflop_node(blueprint_name, node_position)` - Alternate between A/B
- `add_do_once_node(blueprint_name, node_position)` - Execute logic once
- `add_do_n_node(blueprint_name, n, node_position)` - Execute N times
- `add_gate_node(blueprint_name, node_position)` - Open/close gate
- `add_for_each_loop_node(blueprint_name, node_position)` - Array iteration
- `add_cast_node(blueprint_name, target_class, node_position)` - Type casting
- `add_get_variable_node(blueprint_name, variable_name, node_position)` - Get variable
- `add_set_variable_node(blueprint_name, variable_name, node_position)` - Set variable
- `add_print_string_node(blueprint_name, message, node_position)` - Debug print
- `add_delay_node(blueprint_name, duration, node_position)` - Timed delay
- `add_timeline_node(blueprint_name, timeline_name, node_position)` - Timeline animation
- `add_macro_node(blueprint_name, macro_name, node_position)` - Custom macro

## GAMEPLAY FRAMEWORK TOOLS (NEW)
- `create_game_mode(name, default_pawn_class, hud_class, player_controller_class)` - GameMode setup
- `create_player_controller(name, parent_class)` - PlayerController Blueprint
- `create_game_instance(name)` - Persistent GameInstance Blueprint
- `set_game_mode_for_level(game_mode_name)` - Assign GameMode to level
- `spawn_actor_from_class(blueprint_name, actor_class, location, rotation)` - Runtime actor spawn
- `create_hud_blueprint(name)` - HUD Blueprint creation
- `set_default_pawn_class(game_mode_name, pawn_class)` - Set pawn for GameMode
- `add_overlap_event(blueprint_name, component_name)` - OnComponentBeginOverlap
- `add_hit_event(blueprint_name, component_name)` - OnComponentHit

## BLUEPRINT COMMUNICATION TOOLS (NEW)
- `add_event_dispatcher(blueprint_name, dispatcher_name, params)` - Create dispatcher
- `call_event_dispatcher(blueprint_name, dispatcher_name, node_position)` - Call dispatcher
- `bind_event_to_dispatcher(blueprint_name, dispatcher_blueprint, dispatcher_name, node_position)` - Bind
- `create_blueprint_interface(interface_name, functions)` - Blueprint Interface
- `implement_blueprint_interface(blueprint_name, interface_name)` - Implement interface
- `add_level_blueprint_event(event_name, node_position)` - Level Blueprint events
- `add_direct_blueprint_reference(blueprint_name, target_blueprint, variable_name)` - Direct ref

## DATA STRUCTURES TOOLS (NEW)
- `add_array_variable(blueprint_name, variable_name, element_type)` - Array variable
- `add_map_variable(blueprint_name, variable_name, key_type, value_type)` - Map variable
- `add_set_variable(blueprint_name, variable_name, element_type)` - Set variable
- `create_struct(struct_name, fields)` - Create custom Struct
- `create_enum(enum_name, values)` - Create custom Enum
- `create_data_table(table_name, row_struct)` - Create DataTable
- `add_switch_on_int_node(blueprint_name, node_position)` - Switch on Int
- `add_switch_on_string_node(blueprint_name, node_position)` - Switch on String
- `add_switch_on_enum_node(blueprint_name, enum_type, node_position)` - Switch on Enum
- `add_multigate_node(blueprint_name, num_outputs, node_position)` - MultiGate

## UMG / UI TOOLS
- `create_umg_widget_blueprint(widget_name, parent_class, path)`
- `add_text_block_to_widget(widget_name, text_block_name, text, position, size, font_size, color)`
- `add_button_to_widget(widget_name, button_name, text, position, size, ...)`
- `bind_widget_event(widget_name, widget_component_name, event_name, function_name)`
- `add_widget_to_viewport(widget_name, z_order)`
- `set_text_block_binding(widget_name, text_block_name, binding_property, binding_type)`

## ANIMATION TOOLS (NEW)
- `create_animation_blueprint(name, skeleton, parent_class)` - AnimBP creation
- `add_state_machine(anim_blueprint_name, state_machine_name)` - State machine
- `add_animation_state(anim_blueprint_name, state_machine_name, state_name)` - Add state
- `add_state_transition(anim_blueprint_name, state_machine_name, from_state, to_state, condition_var)` - Transitions
- `set_animation_for_state(anim_blueprint_name, state_machine_name, state_name, animation_asset)` - Assign anim
- `add_blend_space_node(anim_blueprint_name, blend_space_asset, node_position)` - BlendSpace

## AI TOOLS (NEW)
- `create_behavior_tree(name)` - Create BehaviorTree asset
- `create_blackboard(name, keys)` - Create Blackboard with keys
- `create_ai_controller(name, behavior_tree)` - AIController Blueprint
- `add_bt_task(blueprint_name, task_name)` - BTTask Blueprint
- `add_bt_decorator(blueprint_name, decorator_name)` - BTDecorator Blueprint
- `add_bt_service(blueprint_name, service_name)` - BTService Blueprint
- `add_move_to_node(blueprint_name, node_position)` - MoveTo AI node
- `set_blackboard_value(blueprint_name, key_name, value_type, node_position)` - BB value setter

## EDITOR & ACTOR MANAGEMENT
- `get_actors_in_level()` - List all actors
- `find_actors_by_name(pattern)` - Find by name
- `spawn_actor(name, type, location, rotation)` - Spawn actor
- `delete_actor(name)` - Delete actor
- `set_actor_transform(name, location, rotation, scale)` - Set transform
- `get_actor_properties(name)` - Get properties
- `spawn_blueprint_actor(blueprint_name, actor_name, location, rotation)` - Spawn BP actor

## PROJECT TOOLS
- `create_input_mapping(action_name, key, input_type)` - Input mappings

## COMMON PARENT CLASSES
- Actor, Pawn, Character, PlayerController, GameModeBase
- GameInstance, HUD, UserWidget, AnimInstance
- AIController, BehaviorTree, BTTaskNode, BTDecorator, BTService

## MATERIAL TOOLS (Ch. 5, 6, 9, 10)
- `create_material(name, base_color, metallic, roughness)` - Create Material asset
- `set_material_on_actor(actor_name, material_path, element_index)` - Set material at runtime
- `add_set_material_node(blueprint_name, component_name, material_path, event_name)` - Hit->swap material
- `create_dynamic_material_instance(blueprint_name, component_name, source_material_path)` - Dynamic mat
- `add_set_vector_parameter_value_node(...)` - Change material color at runtime
- `add_set_scalar_parameter_value_node(...)` - Change material float parameter at runtime
- `setup_hit_material_swap(blueprint_name, mesh_component, default_material, hit_material)` - Full hit swap
- `add_spawn_emitter_at_location_node(blueprint_name, particle_system_path)` - Particle effects
- `add_play_sound_at_location_node(blueprint_name, sound_asset_path)` - Sound effects
- `set_collision_settings(blueprint_name, component_name, collision_preset, hidden_in_game)` - Collision

## SAVEGAME & GAME STATE TOOLS (Ch. 8, 11)
- `create_savegame_blueprint(name, variables)` - SaveGame class (stores Round, Score, etc.)
- `add_save_game_to_slot_node(blueprint_name, save_game_variable, slot_name_variable)` - Save to disk
- `add_load_game_from_slot_node(blueprint_name, slot_name_variable, save_game_class)` - Load from disk
- `add_does_save_game_exist_node(blueprint_name, slot_name)` - Check if save exists
- `add_create_save_game_object_node(blueprint_name, save_game_class)` - Create new save object
- `add_delete_save_game_in_slot_node(blueprint_name, slot_name_variable)` - Reset save file
- `setup_full_save_load_system(character_blueprint, save_blueprint_name)` - Complete save system
- `add_set_game_paused_node(blueprint_name, paused, show_mouse_cursor)` - Pause game
- `add_open_level_node(blueprint_name, level_name, use_current_level)` - Level transition
- `add_quit_game_node(blueprint_name)` - Quit application
- `create_round_based_game_system(character_blueprint, round_scale_multiplier)` - Arcade rounds
- `create_lose_screen_widget(widget_name, message_text)` - Lose/death screen
- `create_pause_menu_widget(widget_name)` - Pause menu with resume/reset/quit
- `add_player_death_event(blueprint_name, lose_widget_name)` - Player death handler

## BLUEPRINT LIBRARY & COMPONENT TOOLS (Ch. 18)
- `create_blueprint_function_library(name, functions)` - Global function library
- `create_blueprint_macro_library(name, parent_class)` - Macro library
- `create_actor_component(name, variables, functions)` - Custom Actor Component
- `create_experience_level_component(name, max_level, xp_per_level)` - XP/level system
- `create_scene_component(name, variables)` - Custom Scene Component (has Transform)
- `create_circular_movement_component(name, rotation_per_second)` - Orbiting shield/component
- `add_component_to_blueprint_actor(blueprint_name, component_blueprint_name)` - Add BP component
- `add_set_timer_by_event_node(blueprint_name, time_seconds, looping, custom_event_name)` - Timer
- `add_set_timer_by_function_name_node(blueprint_name, function_name, time_seconds)` - Function timer
- `add_clear_timer_node(blueprint_name, timer_handle_variable)` - Stop timer
- `add_get_owner_node(blueprint_name, cast_to_class)` - Get owning Actor from component
- `add_random_integer_in_range_node(blueprint_name, min_value, max_value)` - Random int

## PROCEDURAL GENERATION TOOLS (Ch. 19)
- `create_procedural_mesh_blueprint(name, static_mesh_path, instances_per_row, number_of_rows)` - Procedural grid
- `create_spline_placement_blueprint(name, static_mesh_path, space_between_instances)` - Spline placement
- `add_instanced_static_mesh_component(blueprint_name, component_name)` - ISM component
- `add_spline_component(blueprint_name, component_name)` - Spline component
- `add_spline_mesh_component(blueprint_name, component_name, static_mesh_path)` - Deform mesh along spline
- `create_editor_utility_blueprint(name, utility_type)` - Editor Utility (ActorActionUtility/AssetActionUtility)
- `create_align_actors_utility(name)` - Align selected actors utility
- `add_get_spline_length_node(blueprint_name)` - Get spline total length
- `add_get_location_at_distance_along_spline_node(blueprint_name)` - Position along spline
- `add_get_rotation_at_distance_along_spline_node(blueprint_name)` - Rotation along spline
- `add_instanced_mesh_add_instance_node(blueprint_name)` - Add instance to ISM
- `place_navmesh_bounds_volume(location, scale)` - Place NavMesh for AI navigation

## VR DEVELOPMENT TOOLS (Ch. 16)
- `create_vr_pawn_blueprint(name, enable_teleportation, enable_object_grabbing)` - Full VRPawn setup
- `add_motion_controller_component(blueprint_name, component_name, motion_source)` - Motion controller
- `add_widget_interaction_component(blueprint_name, component_name)` - VR menu interaction
- `create_blueprint_interface(name, functions)` - Blueprint Interface (VRInteractionBPI pattern)
- `implement_blueprint_interface(blueprint_name, interface_name)` - Implement interface
- `add_call_interface_function_node(blueprint_name, interface_name, function_name)` - Call interface
- `create_grab_component(name, default_grab_type)` - VR grab component (Free/Snap/Custom)
- `make_actor_vr_grabbable(blueprint_name, grab_type)` - Make actor VR-grabbable
- `add_teleport_system_to_pawn(blueprint_name)` - Full teleport system
- `add_vr_input_action_node(blueprint_name, input_action)` - VR controller input
- `add_predict_projectile_path_node(blueprint_name)` - Teleport arc calculation
- `add_validated_get_node(blueprint_name, variable_name)` - Safe null-check get

## VARIANT MANAGER TOOLS (Ch. 20)
- `create_level_variant_sets(name, variant_sets)` - Level Variant Sets asset
- `add_variant_to_level_variant_sets(lvs_name, variant_set_name, variant_name)` - Add variant
- `add_activate_variant_node(blueprint_name, lvs_variable, variant_set_name, variant_name)` - Activate variant
- `add_activate_variant_set_node(blueprint_name, lvs_variable, variant_set_name)` - Activate variant set
- `create_product_configurator_blueprint(name, lvs_asset_name)` - Product configurator
- `add_get_all_variants_node(blueprint_name, lvs_variable)` - Get all variants
- `add_get_variant_sets_node(blueprint_name, lvs_variable)` - Get all variant sets

## MISCELLANEOUS NODES (Ch. 15)
- `add_select_node(blueprint_name, index_type, option_type, num_options)` - Multi-way select
- `add_teleport_node(blueprint_name)` - Safe actor teleport
- `add_format_text_node(blueprint_name, format_string)` - Template text ({param} syntax)
- `add_math_expression_node(blueprint_name, expression)` - Inline math formula
- `add_set_view_target_with_blend_node(blueprint_name, blend_time)` - Camera switching
- `add_attach_actor_to_component_node(blueprint_name)` - Dynamic actor attachment
- `add_enable_disable_input_node(blueprint_name, enable)` - Enable/disable input
- `add_set_input_mode_node(blueprint_name, input_mode)` - GameOnly/UIOnly/GameAndUI
- `add_nearly_equal_float_node(blueprint_name, tolerance)` - Float comparison with tolerance
- `add_print_text_node(blueprint_name, duration)` - Print Text (for Format Text output)
- `add_append_string_node(blueprint_name, string_a, string_b)` - String concatenation
- `add_spawn_actor_from_class_node(blueprint_name, actor_class)` - Spawn actor from class
- `add_destroy_actor_node(blueprint_name, use_self)` - Destroy actor
- `add_is_valid_node(blueprint_name)` - Check object reference validity
- `add_is_valid_class_node(blueprint_name)` - Check class reference validity
- `add_construction_script_node(blueprint_name)` - Construction Script event (runs in-editor)
- `add_reroute_node(blueprint_name)` - Wire routing dot node
- `add_clamp_node(blueprint_name, operand_type, min_value, max_value)` - Clamp to range
- `add_lerp_node(blueprint_name, operand_type)` - Linear interpolation
- `add_abs_node(blueprint_name, operand_type)` - Absolute value
- `add_min_max_node(blueprint_name, operation, operand_type)` - Min/Max
- `add_random_float_in_range_node(blueprint_name, min_value, max_value)` - Random float
- `add_random_integer_in_range_node(blueprint_name, min_value, max_value)` - Random int
- `add_get_delta_seconds_node(blueprint_name)` - Frame time for frame-rate-independent movement
- `add_get_all_actors_of_class_node(blueprint_name, actor_class)` - Find all actors by class
- `add_get_actor_of_class_node(blueprint_name, actor_class)` - Find first actor by class
- `add_get_game_mode_node(blueprint_name)` - Get current GameMode reference
- `add_get_game_instance_node(blueprint_name)` - Get persistent GameInstance reference
- `add_arithmetic_operator_node(blueprint_name, operator, operand_type)` - +/-/*// operators
- `add_relational_operator_node(blueprint_name, operator, operand_type)` - ==/>/</>= etc.
- `add_logical_operator_node(blueprint_name, operator)` - AND/OR/NOT/XOR

## PHYSICS / MATH / TRACE TOOLS (Ch. 14, NEW)
- `add_get_actor_location_node(blueprint_name)` - Get world location Vector
- `add_set_actor_location_node(blueprint_name)` - Set world location
- `add_actor_world_offset_node(blueprint_name)` - Add offset (delta movement)
- `add_get_actor_rotation_node(blueprint_name)` - Get Rotator
- `add_set_actor_rotation_node(blueprint_name)` - Set Rotator
- `add_actor_world_rotation_node(blueprint_name)` - Add delta rotation
- `add_get_actor_scale_node(blueprint_name)` - Get 3D scale
- `add_set_actor_scale_node(blueprint_name)` - Set 3D scale
- `add_get_relative_location_node(blueprint_name, component_name)` - Component relative location
- `add_set_relative_location_node(blueprint_name, component_name)` - Set relative location
- `add_vector_add_node(blueprint_name)` - Vector + Vector addition
- `add_vector_subtract_node(blueprint_name)` - Vector - Vector subtraction
- `add_vector_multiply_node(blueprint_name)` - Vector * Float (scale/reverse)
- `add_normalize_vector_node(blueprint_name)` - Normalize to unit vector
- `add_vector_length_node(blueprint_name)` - Vector magnitude/distance
- `add_dot_product_node(blueprint_name)` - Dot product (angle between vectors)
- `add_cross_product_node(blueprint_name)` - Cross product (perpendicular vector)
- `add_get_forward_vector_node(blueprint_name)` - Actor forward direction
- `add_get_right_vector_node(blueprint_name)` - Actor right direction
- `add_get_up_vector_node(blueprint_name)` - Actor up direction
- `add_get_unit_direction_vector_node(blueprint_name)` - Direction A→B normalized
- `add_line_trace_by_channel_node(blueprint_name, trace_channel, draw_debug)` - Line trace
- `add_multi_line_trace_by_channel_node(blueprint_name, trace_channel)` - Multi line trace
- `add_line_trace_for_objects_node(blueprint_name, object_types)` - Object type trace
- `add_multi_line_trace_for_objects_node(blueprint_name, object_types)` - Multi object trace
- `add_sphere_trace_for_objects_node(blueprint_name, radius, object_types)` - Sphere trace
- `add_sphere_trace_by_channel_node(blueprint_name, radius, trace_channel)` - Sphere channel trace
- `add_capsule_trace_by_channel_node(blueprint_name, radius, half_height)` - Capsule trace
- `add_box_trace_by_channel_node(blueprint_name, half_size, trace_channel)` - Box trace
- `add_break_hit_result_node(blueprint_name)` - Decompose Hit Result struct
- `add_draw_debug_line_node(blueprint_name, duration, color)` - Viewport debug line
- `add_draw_debug_sphere_node(blueprint_name, radius, duration)` - Viewport debug sphere
- `add_draw_debug_point_node(blueprint_name, size, duration)` - Viewport debug point
- `add_set_collision_profile_node(blueprint_name, component_name, profile_name)` - Collision preset
- `add_set_collision_enabled_node(blueprint_name, component_name, collision_enabled)` - Toggle collision
- `add_set_generate_overlap_events_node(blueprint_name, component_name)` - Enable overlaps
- `add_apply_damage_node(blueprint_name, damage_amount)` - Apply Damage (Gameplay)
- `add_apply_point_damage_node(blueprint_name, damage_amount)` - Point Damage with location
- `build_trace_interaction_blueprint(blueprint_name, trace_range, input_key)` - Full trace system

## ADVANCED AI TOOLS (Ch. 10, EXPANDED)
- `create_bt_attack_task(name, damage_variable, default_damage)` - Melee attack BT task
- `add_pawn_sensing_component(blueprint_name, hearing_threshold, sight_radius)` - AI senses
- `add_on_see_pawn_event(blueprint_name)` - OnSeePawn event binding
- `add_on_hear_noise_event(blueprint_name)` - OnHearNoise event binding
- `add_play_sound_at_location_node(blueprint_name, sound_asset)` - Sound effect node
- `add_report_noise_event_node(blueprint_name, loudness, max_range)` - Alert AI via sound
- `create_enemy_spawner_blueprint(name, enemy_class, max_enemies, spawn_interval)` - Enemy waves
- `create_bt_wander_task(name, wander_radius)` - Random wandering BT task
- `add_get_random_reachable_point_node(blueprint_name, radius)` - NavMesh random point
- `add_finish_execute_node(blueprint_name, success)` - BT Task finish (success/fail)
- `add_get_blackboard_value_node(blueprint_name, key_name, value_type)` - Read BB key
- `add_clear_blackboard_value_node(blueprint_name, key_name)` - Reset BB key
- `add_bt_blackboard_decorator(behavior_tree_name, sequence_name, blackboard_key)` - BT decorator
- `create_full_upgraded_enemy_ai(enemy_name, has_attack, has_hearing, has_wandering)` - Full AI

## EXTENDED UMG WIDGETS (Ch. 7, 8, 11)
- `add_horizontal_box_to_widget(widget_name, box_name)` - Horizontal layout container
- `add_vertical_box_to_widget(widget_name, box_name)` - Vertical layout container
- `add_canvas_panel_to_widget(widget_name, panel_name)` - Free-placement canvas
- `add_slider_to_widget(widget_name, slider_name, min_value, max_value)` - Slider widget
- `add_checkbox_to_widget(widget_name, checkbox_name, label_text)` - Checkbox
- `add_named_slot_to_widget(widget_name, slot_name)` - Named slot placeholder
- `create_hud_widget(widget_name, health_bar, stamina_bar, ammo_counter)` - Full HUD
- `create_win_menu_widget(widget_name, title_text)` - Win screen
- `add_widget_animation(widget_name, animation_name, animated_property)` - UMG animation
- `add_remove_from_parent_node(blueprint_name, widget_variable)` - Hide/remove widget
- `add_create_widget_node(blueprint_name, widget_class)` - Create widget at runtime

## EXTENDED DATA TOOLS (Ch. 13)
- `add_make_array_node(blueprint_name, element_type, num_pins)` - Make Array literal
- `add_random_array_item_node(blueprint_name, array_variable)` - Random array element
- `create_random_spawner_blueprint(name)` - BP_RandomSpawner (random spawn point)
- `add_set_contains_node(blueprint_name, set_variable)` - Set CONTAINS check
- `add_set_union_node(blueprint_name)` - Set UNION operation
- `add_set_intersection_node(blueprint_name)` - Set INTERSECTION operation
- `add_set_difference_node(blueprint_name)` - Set DIFFERENCE operation
- `add_set_to_array_node(blueprint_name, set_variable)` - Convert Set to Array
- `add_make_set_node(blueprint_name, element_type, num_pins)` - Make Set literal
- `add_map_variable(blueprint_name, variable_name, key_type, value_type)` - Map variable
- `add_map_find_node(blueprint_name, map_variable)` - Map FIND by key
- `add_map_contains_node(blueprint_name, map_variable)` - Map CONTAINS key check
- `add_map_keys_node(blueprint_name, map_variable)` - Get all Map keys
- `add_map_values_node(blueprint_name, map_variable)` - Get all Map values
- `add_make_map_node(blueprint_name, key_type, value_type, num_pairs)` - Make Map literal
- `add_break_struct_node(blueprint_name, struct_type)` - Break struct into members
- `add_make_struct_node(blueprint_name, struct_type)` - Make struct from members
- `add_get_data_table_row_node(blueprint_name, data_table_variable, row_name)` - DataTable lookup

## COMMON COMPONENT TYPES  
- StaticMeshComponent, SkeletalMeshComponent, CameraComponent
- SpringArmComponent, BoxComponent, SphereComponent, CapsuleComponent
- PointLightComponent, SpotLightComponent, AudioComponent
- CharacterMovementComponent, ProjectileMovementComponent
- InstancedStaticMeshComponent, SplineComponent, SplineMeshComponent
- MotionControllerComponent, WidgetInteractionComponent

## COMMON EVENT NAMES
- ReceiveBeginPlay, ReceiveTick, ReceiveEndPlay
- ReceiveHit, ReceiveActorBeginOverlap, ReceiveActorEndOverlap
- ReceivePointDamage, ReceiveRadialDamage, ReceiveAnyDamage

## VARIABLE TYPES
- Boolean, Integer, Float, Double, String, Name, Text
- Vector, Rotator, Transform, Color, LinearColor
- Object Reference, Class Reference, Interface Reference
- Array<T>, Map<K,V>, Set<T> (use add_array_variable, add_map_variable, add_set_variable)

## PDF AUDIT STATUS: 100% of all 20 chapters fully audited (566 pages, all 3 passes)
## TOTAL: 283 MCP TOOLS (3rd deep pass, deduplicated) covering all 20 chapters of "Blueprints Visual Scripting for Unreal Engine 5"
## New in 3rd pass: physics_tools.py (Ch.14 Math/Trace/Vectors), expanded ai_tools.py (Ch.10 attack/hearing/spawner/wander),
##   expanded advanced_node_tools.py (Ch.2 operators, Ch.3 actor queries, Ch.5/6/8 math nodes, timers, delta time)
"""


if __name__ == "__main__":
    # ── Argument parsing ────────────────────────────────────────────────────
    parser = argparse.ArgumentParser(
        description="Unreal Engine MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transport modes:
  stdio            For local AI clients (Claude Desktop, Cursor, Windsurf).
                   No extra flags needed. Used by default.

  sse              HTTP + Server-Sent Events. For remote AI agents (GenSpark,
                   any cloud MCP client). Starts an HTTP server that remote
                   agents connect to via the /sse endpoint.
                   Example: python unreal_mcp_server.py --transport sse
                            --mcp-host 0.0.0.0 --mcp-port 8000

  streamable-http  Modern HTTP streaming (MCP 2025-03-26). Recommended for
                   new integrations. Exposes /mcp endpoint.
                   Example: python unreal_mcp_server.py --transport streamable-http

Unreal Engine connection:
  --unreal-host    Hostname/IP of the UE5 machine (default: 127.0.0.1)
                   Set to your Playit tunnel address when UE5 is remote.
  --unreal-port    Port the UnrealMCP plugin listens on (default: 55557)
                   Set to your Playit tunnel port when using a tunnel.

Environment variable equivalents:
  UNREAL_HOST, UNREAL_PORT      — UE5 plugin TCP address
  MCP_SERVER_HOST, MCP_SERVER_PORT — HTTP server bind address (sse/streamable-http)
        """
    )

    # Transport
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        help="MCP transport to use (default: stdio)"
    )

    # UE5 plugin address
    parser.add_argument(
        "--unreal-host",
        default=None,
        metavar="HOST",
        help="Hostname or IP of the UE5 machine (overrides UNREAL_HOST env var)"
    )
    parser.add_argument(
        "--unreal-port",
        type=int,
        default=None,
        metavar="PORT",
        help="Port the UnrealMCP plugin listens on (overrides UNREAL_PORT env var)"
    )

    # MCP HTTP server address (sse / streamable-http only)
    parser.add_argument(
        "--mcp-host",
        default=None,
        metavar="HOST",
        help="Host to bind the MCP HTTP server to (default: 0.0.0.0). sse/streamable-http only."
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=None,
        metavar="PORT",
        help="Port to bind the MCP HTTP server to (default: 8000). sse/streamable-http only."
    )

    args = parser.parse_args()

    # ── Apply CLI overrides ─────────────────────────────────────────────────
    if args.unreal_host is not None:
        UNREAL_HOST = args.unreal_host
    if args.unreal_port is not None:
        UNREAL_PORT = args.unreal_port
    if args.mcp_host is not None:
        MCP_SERVER_HOST = args.mcp_host
    if args.mcp_port is not None:
        MCP_SERVER_PORT = args.mcp_port

    # ── Apply MCP server HTTP host/port settings ────────────────────────────
    # FastMCP reads these from its settings object; patch them before run()
    if args.transport in ("sse", "streamable-http"):
        mcp.settings.host = MCP_SERVER_HOST
        mcp.settings.port = MCP_SERVER_PORT
        # Allow any Host header so reverse proxies / Playit tunnels work correctly.
        # Without this uvicorn returns 421 Misdirected Request for tunnel hostnames.
        try:
            mcp.settings.allowed_hosts = ["*"]
        except Exception:
            pass

    # ── Launch ──────────────────────────────────────────────────────────────
    if args.transport == "stdio":
        logger.info(
            f"Starting UnrealMCP server | transport=stdio | "
            f"UE5={UNREAL_HOST}:{UNREAL_PORT}"
        )
        mcp.run(transport="stdio")

    elif args.transport == "sse":
        logger.info(
            f"Starting UnrealMCP server | transport=sse | "
            f"HTTP={MCP_SERVER_HOST}:{MCP_SERVER_PORT} | "
            f"UE5={UNREAL_HOST}:{UNREAL_PORT}"
        )
        print(f"[UnrealMCP] SSE server listening on http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/sse")
        print(f"[UnrealMCP] Remote agents: connect to  http://<your-public-ip-or-tunnel>:{MCP_SERVER_PORT}/sse")
        print(f"[UnrealMCP] UE5 plugin target: {UNREAL_HOST}:{UNREAL_PORT}")
        # Run uvicorn directly with DNS rebinding protection disabled.
        # The MCP library's SseServerTransport has its own TransportSecurityMiddleware
        # that rejects any Host header not in its allowed list, returning 421.
        # FastMCP's mcp.run(transport="sse") has no way to pass security_settings
        # through, so we build the Starlette app manually with protection disabled.
        import asyncio
        import uvicorn
        from mcp.server.sse import SseServerTransport
        from mcp.server.transport_security import TransportSecuritySettings
        from starlette.applications import Starlette
        from starlette.requests import Request
        from starlette.routing import Mount, Route

        # Disable DNS rebinding protection so tunnel Host headers are accepted
        security_settings = TransportSecuritySettings(enable_dns_rebinding_protection=False)
        sse = SseServerTransport("/messages/", security_settings=security_settings)

        # ── SSE endpoint design note ─────────────────────────────────────────
        # Starlette's Route() inspects whether the endpoint is a function or a
        # class.  When it's a function, Starlette wraps it with request_response()
        # which *sends an HTTP response* when the function returns.  For SSE that
        # is catastrophic: after the first tool-call exchange the function returns,
        # request_response() sends a bare HTTP 200 response body, and the client
        # sees "peer closed connection without sending complete message body
        # (incomplete chunked read)".  The stream is dead after exactly one response.
        #
        # Fix: make the endpoint a *class* (ASGI app).  Starlette's Route uses
        #   self.app = endpoint          ← for classes (no request_response wrap)
        #   self.app = request_response(endpoint)  ← for functions (WRONG for SSE)
        # A class-based ASGI app receives (scope, receive, send) directly, so the
        # EventSourceResponse inside connect_sse owns the entire HTTP response
        # lifecycle and the stream stays open for the full MCP session.
        # ─────────────────────────────────────────────────────────────────────
        class SseEndpoint:
            """Class-based ASGI endpoint for /sse.

            Starlette detects this as a class and skips request_response() wrapping,
            so the EventSourceResponse inside connect_sse controls the connection
            lifetime instead of being prematurely closed by a wrapping Response.
            """

            async def __call__(self, scope, receive, send):
                if scope["type"] != "http":
                    return
                try:
                    async with sse.connect_sse(scope, receive, send) as streams:
                        await mcp._mcp_server.run(
                            streams[0],
                            streams[1],
                            mcp._mcp_server.create_initialization_options(),
                        )
                except Exception as exc:
                    import anyio
                    # ClosedResourceError = client disconnected cleanly; suppress.
                    if isinstance(exc, anyio.ClosedResourceError):
                        logger.debug("SSE client disconnected cleanly")
                    else:
                        logger.error(f"SSE handler error: {exc}")

        starlette_app = Starlette(
            routes=[
                Route("/sse", endpoint=SseEndpoint(), methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ]
        )

        config = uvicorn.Config(
            starlette_app,
            host=MCP_SERVER_HOST,
            port=MCP_SERVER_PORT,
            log_level="info",
            # Keep HTTP connections open long enough for slow UE5 operations.
            # h11 (HTTP/1.1) has a default incomplete-event size limit that can
            # reject large Blueprint-node responses; bump it to 16 MB.
            # timeout_keep_alive: seconds to hold an idle SSE connection open.
            # timeout_graceful_shutdown: gives in-flight tool calls time to finish.
            timeout_keep_alive=300,
            timeout_graceful_shutdown=10,
            h11_max_incomplete_event_size=16 * 1024 * 1024,  # 16 MB
        )
        server = uvicorn.Server(config)
        asyncio.run(server.serve())

    elif args.transport == "streamable-http":
        logger.info(
            f"Starting UnrealMCP server | transport=streamable-http | "
            f"HTTP={MCP_SERVER_HOST}:{MCP_SERVER_PORT} | "
            f"UE5={UNREAL_HOST}:{UNREAL_PORT}"
        )
        print(f"[UnrealMCP] Streamable-HTTP server listening on http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/mcp")
        print(f"[UnrealMCP] Remote agents: connect to  http://<your-public-ip-or-tunnel>:{MCP_SERVER_PORT}/mcp")
        print(f"[UnrealMCP] UE5 plugin target: {UNREAL_HOST}:{UNREAL_PORT}")
        mcp.run(transport="streamable-http")
