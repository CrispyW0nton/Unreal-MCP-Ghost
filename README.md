# Unreal Engine MCP Server - Enhanced Blueprint Visual Scripting Edition

> **Built on top of:** [chongdashu/unreal-mcp](https://github.com/chongdashu/unreal-mcp)  
> **Extended with:** Full support for all topics in *Blueprints Visual Scripting for Unreal Engine 5* by Marcos Romero

This MCP server lets you (or any AI assistant) create, modify, and compile full Unreal Engine 5 gameplay Blueprint systems through natural language — directly from Claude, Cursor, or Windsurf.

---

## Architecture

```
Claude / Cursor / Windsurf
        │
        │ MCP Protocol (stdio)
        ▼
  unreal_mcp_server.py          ← Python MCP Server (this repo)
        │
        │ TCP JSON (port 55557)
        ▼
  UnrealMCP C++ Plugin           ← Must be installed in your UE5 project
        │
        │ UE5 Editor Subsystem
        ▼
  Unreal Engine 5.5+
```

---

## Setup

### 1. Install the C++ Plugin

1. Clone [unreal-mcp](https://github.com/chongdashu/unreal-mcp)
2. Copy `MCPGameProject/Plugins/UnrealMCP` to your project's `Plugins/` folder
3. **Add the extended commands** (see `unreal_plugin/` in this repo):
   - Copy `UnrealMCPExtendedCommands.h` → `Plugins/UnrealMCP/Source/UnrealMCP/Public/Commands/`
   - Copy `UnrealMCPExtendedCommands.cpp` → `Plugins/UnrealMCP/Source/UnrealMCP/Private/Commands/`
   - Apply the integration steps in `UnrealMCPBridge_Integration.patch`
4. Regenerate Visual Studio project files and build

### 2. Start the Python MCP Server

```bash
cd unreal_mcp_server
pip install mcp fastmcp
python unreal_mcp_server.py
```

Or with `uv`:
```bash
cd unreal_mcp_server
uv run unreal_mcp_server.py
```

### 3. Configure Your MCP Client

**Claude Desktop** (`~/.config/claude-desktop/mcp.json`):
```json
{
  "mcpServers": {
    "unrealMCP": {
      "command": "python",
      "args": ["/path/to/unreal_mcp_server/unreal_mcp_server.py"]
    }
  }
}
```

**Cursor** (`.cursor/mcp.json` in project root):
```json
{
  "mcpServers": {
    "unrealMCP": {
      "command": "uv",
      "args": ["--directory", "/path/to/unreal_mcp_server", "run", "unreal_mcp_server.py"]
    }
  }
}
```

---

## What You Can Do (Full Feature List)

### Core Blueprint Development
| Feature | Tool |
|---------|------|
| Create any Blueprint class | `create_blueprint` |
| Add components | `add_component_to_blueprint` |
| Set physics | `set_physics_properties` |
| Compile | `compile_blueprint` |
| Set properties | `set_blueprint_property`, `set_component_property` |

### Event Graph Nodes
| Feature | Tool |
|---------|------|
| Event nodes (BeginPlay, Tick, etc.) | `add_blueprint_event_node` |
| Function calls | `add_blueprint_function_node` |
| Input actions | `add_blueprint_input_action_node` |
| Variables (get/set) | `add_blueprint_variable`, `add_get_variable_node`, `add_set_variable_node` |
| Self/component references | `add_blueprint_self_reference`, `add_blueprint_get_self_component_reference` |
| Node connections | `connect_blueprint_nodes` |

### Flow Control (Book Chapter 13)
| Node | Tool |
|------|------|
| Branch (if/else) | `add_branch_node` |
| Sequence | `add_sequence_node` |
| Flip Flop | `add_flipflop_node` |
| Do Once | `add_do_once_node` |
| Do N | `add_do_n_node` |
| Gate | `add_gate_node` |
| While Loop | `add_while_loop_node` |
| For Each Loop | `add_for_each_loop_node` |
| Switch on Int/String/Enum | `add_switch_on_int_node`, `add_switch_on_string_node`, `add_switch_on_enum_node` |
| MultiGate | `add_multigate_node` |

### Data Structures (Book Chapter 13)
| Feature | Tool |
|---------|------|
| Array variable | `add_array_variable` |
| Map variable | `add_map_variable` |
| Set variable | `add_set_variable` |
| Custom Struct | `create_struct` |
| Custom Enum | `create_enum` |
| DataTable | `create_data_table` |

### Blueprint Communication (Book Chapter 4)
| Feature | Tool |
|---------|------|
| Event Dispatchers | `add_event_dispatcher`, `call_event_dispatcher`, `bind_event_to_dispatcher` |
| Direct References | `add_direct_blueprint_reference` |
| Casting | `add_cast_node` |
| Blueprint Interfaces | `create_blueprint_interface`, `implement_blueprint_interface` |
| Custom Functions | `add_custom_function` |
| Custom Macros | `add_custom_macro`, `add_macro_node` |
| Function Libraries | `create_blueprint_function_library` |
| Macro Libraries | `create_blueprint_macro_library` |

### Gameplay Framework (Book Chapter 3)
| Feature | Tool |
|---------|------|
| GameMode | `create_game_mode` |
| PlayerController | `create_player_controller` |
| GameInstance | `create_game_instance` |
| HUD | `create_hud_blueprint` |
| Character (with camera) | `create_character_blueprint` |
| FPS Character | `create_fps_character` |
| Projectile | `create_projectile_blueprint` |
| Pickup | `create_pickup_blueprint` |
| Set level GameMode | `set_game_mode_for_level` |

### Animation Blueprints (Book Chapter 17)
| Feature | Tool |
|---------|------|
| Animation Blueprint | `create_animation_blueprint` |
| State Machine | `add_state_machine` |
| States | `add_animation_state` |
| Transitions | `add_state_transition` |
| Assign animations | `set_animation_for_state` |
| Blend Space | `add_blend_space_node` |
| Full character setup | `create_character_animation_setup` |

### AI Systems (Book AI Chapter)
| Feature | Tool |
|---------|------|
| Behavior Tree | `create_behavior_tree` |
| Blackboard | `create_blackboard` |
| AI Controller | `create_ai_controller` |
| BT Task | `create_bt_task` |
| BT Decorator | `create_bt_decorator` |
| BT Service | `create_bt_service` |
| Move To node | `add_move_to_node` |
| Blackboard value | `set_blackboard_value` |
| Full enemy AI | `create_full_enemy_ai` |

### UI / UMG (Book UI Chapter)
| Feature | Tool |
|---------|------|
| Widget Blueprint | `create_umg_widget_blueprint` |
| Text Block | `add_text_block_to_widget` |
| Button | `add_button_to_widget` |
| Progress Bar | `add_progress_bar_to_widget` |
| Image | `add_image_to_widget` |
| Widget Events | `bind_widget_event` |
| Add to Viewport | `add_widget_to_viewport` |
| Property Binding | `set_text_block_binding` |

### Debug & Utilities
| Feature | Tool |
|---------|------|
| Print String | `add_print_string_node` |
| Delay | `add_delay_node` |
| Timeline | `add_timeline_node` |
| Line Trace | `add_line_trace_node` |
| Math nodes | `add_math_node` |
| Comment Box | `add_comment_box` |
| Spawn Actor | `add_spawn_actor_node` |
| Destroy Actor | `add_destroy_actor_node` |
| Open Level | `add_open_level_node` |
| Apply Damage | `add_apply_damage_node` |
| Play Sound | `add_play_sound_node` |
| Build full graph | `build_complete_blueprint_graph` |

### Input Systems
| Feature | Tool |
|---------|------|
| Legacy input mapping | `create_input_mapping` |
| Enhanced Input Action | `create_enhanced_input_action` |
| Input Mapping Context | `create_input_mapping_context` |

---

## Example: Creating a Complete FPS Game System

Just tell Claude:

> "Create a complete FPS game setup with a character that has a gun, health system, a HUD showing health, an enemy with AI that chases and attacks the player."

The MCP tools will:
1. Create `BP_FPSCharacter` with camera, arms mesh, health variables
2. Create `BP_Projectile` with ProjectileMovement 
3. Create `BP_GameMode` assigning the character
4. Create `WBP_HUD` with health bar
5. Create `BB_Enemy` blackboard with PlayerActor, health keys
6. Create `BT_Enemy` behavior tree
7. Create `BP_Enemy` character with AIController
8. Wire up all Event Dispatchers for damage communication

---

## Book Coverage Summary (2nd Pass Research)

**217 tools** covering every chapter of *Blueprints Visual Scripting for Unreal Engine 5*:

| Chapter | Topic | Tools |
|---------|-------|-------|
| Ch. 1-2 | Blueprint Editor, Variables, Events, Macros, Functions | `blueprint_tools`, `node_tools` |
| Ch. 3 | OOP, Gameplay Framework (Actor/Pawn/Character/GameMode/GameInstance) | `gameplay_tools` |
| Ch. 4 | Communication (Dispatchers, Casting, Interfaces, Level BP) | `communication_tools` |
| Ch. 5-6 | Object Interaction, Materials, Hit Detection, Sprint, Zoom, Timeline | `material_tools`, `advanced_node_tools` |
| Ch. 7-8 | HUD/UMG, Health/Stamina Bars, Win/Lose Screens, Ammo Counter | `umg_tools`, `savegame_tools` |
| Ch. 9-10 | AI Enemies, NavMesh, Behavior Trees, Blackboard, Patrol, Chase | `ai_tools`, `procedural_tools` |
| Ch. 11 | Game States, SaveGame, Round System, Pause Menu, Player Death | `savegame_tools` |
| Ch. 12 | Build & Publish (packaging handled by UE Editor natively) | - |
| Ch. 13 | Arrays, Sets, Maps, Enums, Structs, DataTables, Flow Control | `data_tools` |
| Ch. 14 | Math & Trace Nodes (Vectors, Transforms, Line/Shape Traces) | `advanced_node_tools` |
| Ch. 15 | Blueprint Tips (Select, Teleport, Format Text, Math Expression, etc.) | `advanced_node_tools` |
| Ch. 16 | VR Development (VRPawn, Teleport, Grab, Blueprint Interfaces) | `vr_tools` |
| Ch. 17 | Animation Blueprints, State Machines, Blend Spaces | `animation_tools` |
| Ch. 18 | Function/Macro Libraries, Actor/Scene Components, Timers | `library_tools` |
| Ch. 19 | Procedural Generation, Splines, Editor Utilities | `procedural_tools` |
| Ch. 20 | Variant Manager, Product Configurator, Level Variant Sets | `variant_tools` |

## Suggested Additional Features (Beyond the Book)

### 🎮 Advanced Gameplay
- **Physical Animation Component** - Ragdoll blending
- **Chaos Physics** - Procedural destruction Blueprint nodes
- **Gameplay Tags** - Add/query/filter by tags
- **Gameplay Abilities (GAS)** - AbilitySystemComponent setup

### 🌍 World & Level
- **Level Streaming** - Load/unload sub-levels
- **World Partition** - HLOD and streaming setup
- **Landscape & Foliage** - Blueprint-controlled terrain painting

### 📸 Cinematics
- **Sequencer** - Create Level Sequences, add tracks
- **Camera Rigs** - Camera shake, crane shots
- **Cinematic Blueprint nodes** - Play/stop sequences

### 🔊 Audio
- **Sound Cue Blueprints** - Procedural audio
- **MetaSound** - Blueprint-controllable audio graphs  
- **Spatialization** - 3D audio setup

### 🤖 Enhanced AI
- **EQS (Environment Query System)** - AI spatial queries
- **AI Perception** - Sight, hearing, damage perception component
- **Navigation Invoker** - Dynamic navmesh generation
- **Crowd Manager** - Flocking/crowd behavior

### 🌐 Multiplayer
- **Network Replication** - Mark variables/events as Replicated
- **RPCs** - Server/Client/Multicast RPC nodes
- **Online Subsystem** - Session management

### 📊 Debugging & Profiling
- **Visual Logger** - Blueprint logging for timeline debugging
- **Blueprint Profiler** - Identify performance bottlenecks

---

## File Structure

```
unreal_mcp_server/
├── unreal_mcp_server.py          # Main MCP server
├── pyproject.toml                # Python package config
└── tools/
    ├── __init__.py
    ├── editor_tools.py           # Actor management, viewport
    ├── blueprint_tools.py        # Blueprint class operations
    ├── node_tools.py             # Event graph nodes
    ├── project_tools.py          # Input mappings
    ├── umg_tools.py              # Widget Blueprints
    ├── gameplay_tools.py         # GameMode, Character, etc.
    ├── communication_tools.py    # Dispatchers, Interfaces, Casting
    ├── data_tools.py             # Structs, Enums, Arrays, Maps, Sets, DataTables, Flow Control
    ├── animation_tools.py        # AnimBP, State Machines, Blend Spaces
    ├── ai_tools.py               # BehaviorTree, Blackboard, AI Tasks/Decorators
    ├── advanced_node_tools.py    # Branch, Delay, Timeline, Math, Select, Format Text, etc.
    ├── material_tools.py         # Material creation, dynamic materials, hit swap (Ch. 5-6)
    ├── savegame_tools.py         # SaveGame, LoadGame, pause, lose/win menus (Ch. 8, 11)
    ├── library_tools.py          # Function Libraries, Macro Libraries, Actor/Scene Components (Ch. 18)
    ├── procedural_tools.py       # Construction Script, ISM, Splines, Editor Utilities (Ch. 19)
    ├── vr_tools.py               # VRPawn, Motion Controllers, Grab, Teleport, Interfaces (Ch. 16)
    └── variant_tools.py          # Variant Manager, Level Variant Sets, Product Configurator (Ch. 20)

unreal_plugin/
├── UnrealMCPBridge_Integration.patch
└── Source/UnrealMCP/
    ├── Public/Commands/
    │   └── UnrealMCPExtendedCommands.h
    └── Private/Commands/
        └── UnrealMCPExtendedCommands.cpp
```

