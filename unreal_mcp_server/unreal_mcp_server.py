"""
Unreal Engine MCP Server - Enhanced Edition
Based on: https://github.com/chongdashu/unreal-mcp
Extended with full Blueprint Visual Scripting support as described in:
"Blueprints Visual Scripting for Unreal Engine 5" by Marcos Romero

This server enables AI assistants (Claude, Cursor, Windsurf) to control
Unreal Engine 5 through natural language using the Model Context Protocol (MCP).

Architecture:
  - Python MCP Server (this file) <-> TCP Socket (port 55557) <-> UE5 C++ Plugin
  - The C++ plugin (UnrealMCP) must be installed in your UE5 project
"""

import logging
import socket
import sys
import json
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('unreal_mcp.log'),
    ]
)
logger = logging.getLogger("UnrealMCP")

# ─── Configuration ──────────────────────────────────────────────────────────
UNREAL_HOST = "127.0.0.1"
UNREAL_PORT = 55557


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

    def receive_full_response(self, sock, buffer_size=8192) -> bytes:
        chunks = []
        sock.settimeout(15)
        try:
            while True:
                chunk = sock.recv(buffer_size)
                if not chunk:
                    if not chunks:
                        raise Exception("Connection closed before receiving data")
                    break
                chunks.append(chunk)
                data = b''.join(chunks)
                try:
                    json.loads(data.decode('utf-8'))
                    logger.info(f"Received complete response ({len(data)} bytes)")
                    return data
                except json.JSONDecodeError:
                    continue
        except socket.timeout:
            logger.warning("Socket timeout during receive")
            if chunks:
                data = b''.join(chunks)
                try:
                    json.loads(data.decode('utf-8'))
                    return data
                except Exception:
                    pass
            raise Exception("Timeout receiving Unreal response")
        except Exception as e:
            logger.error(f"Error during receive: {str(e)}")
            raise

    def send_command(self, command: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Send a JSON command to UE5 and return the parsed response."""
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
            command_json = json.dumps(command_obj)
            logger.info(f"Sending command: {command_json[:200]}...")
            self.socket.sendall(command_json.encode('utf-8'))

            response_data = self.receive_full_response(self.socket)
            response = json.loads(response_data.decode('utf-8'))
            logger.info(f"Response: {str(response)[:300]}")

            # Normalize error formats
            if response.get("status") == "error":
                error_message = response.get("error") or response.get("message", "Unknown error")
                if "error" not in response:
                    response["error"] = error_message
            elif response.get("success") is False:
                error_message = response.get("error") or response.get("message", "Unknown error")
                response = {"status": "error", "error": error_message}

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
    description="Full Unreal Engine 5 Blueprint Visual Scripting via Model Context Protocol",
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

## COMMON COMPONENT TYPES  
- StaticMeshComponent, SkeletalMeshComponent, CameraComponent
- SpringArmComponent, BoxComponent, SphereComponent, CapsuleComponent
- PointLightComponent, SpotLightComponent, AudioComponent
- CharacterMovementComponent, ProjectileMovementComponent

## COMMON EVENT NAMES
- ReceiveBeginPlay, ReceiveTick, ReceiveEndPlay
- ReceiveHit, ReceiveActorBeginOverlap, ReceiveActorEndOverlap
- ReceivePointDamage, ReceiveRadialDamage, ReceiveAnyDamage

## VARIABLE TYPES
- Boolean, Integer, Float, Double, String, Name, Text
- Vector, Rotator, Transform, Color, LinearColor
- Object Reference, Class Reference, Interface Reference
- Array<T>, Map<K,V>, Set<T> (use add_array_variable, add_map_variable, add_set_variable)
"""


if __name__ == "__main__":
    logger.info("Starting Unreal MCP server with stdio transport")
    mcp.run(transport='stdio')
