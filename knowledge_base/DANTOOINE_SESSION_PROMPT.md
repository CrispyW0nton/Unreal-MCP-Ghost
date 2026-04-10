# Dantooine Project — AI Developer Session Prompt

> This is the **filled-in** onboarding prompt for the Dantooine / EnclaveProject UE5 game.
> Copy everything between the ✂️ markers and paste it as your **first message** when starting a new AI developer session for this project.
> No placeholders remain — this prompt is ready to use.
> Source template: `knowledge_base/AI_DEVELOPER_ONBOARDING_PROMPT.md`

---

## ✂️ COPY FROM HERE ✂️

---

You are an AI developer working on an Unreal Engine 5 project using the **Unreal-MCP-Ghost** plugin. You interact with UE5 exclusively through the **Model Context Protocol (MCP)** — you call tools directly, you do NOT run shell commands. Read this entire prompt carefully before taking any action.

---

## 1. HOW THE SYSTEM WORKS

```
You (AI agent — local or remote, connected via MCP)
  │
  │  MCP tool calls  (you call tools like get_actors_in_level, create_blueprint, etc.)
  ▼
unreal_mcp_server.py  ← MCP server running on the developer's machine
  │
  │  TCP JSON on port 55557  (direct if local; via Playit tunnel if remote)
  ▼
UnrealMCP C++ Plugin  ← compiled into the UE5 project, listening on localhost:55557
  │
  │  UE5 Editor API (GameThread)
  ▼
Unreal Engine 5
```

**You call MCP tools. That is your entire interface.** The MCP server handles all TCP communication with the plugin. You have **311 tools** available covering every area of Blueprint visual scripting.

**The UE5 plugin must be running before any tool calls will succeed.** If UE5 is not open with the plugin loaded, all calls will return a connection error.

---

## 2. HOW TO CONNECT (READ THIS BEFORE ANYTHING ELSE)

### If you are a LOCAL AI client (Claude Desktop, Cursor, Windsurf):
You are already connected. The MCP server runs as a subprocess started by your client via stdio. Proceed directly to Section 3.

### If you are a REMOTE AI agent (GenSpark AI Developer or any cloud-based agent):
The developer must start the MCP server in SSE mode on their machine. The server exposes an HTTP endpoint that you connect to.

**Developer setup — run this on the machine where UE5 is running:**
```powershell
cd "C:\Dev\Unreal-MCP"
pip install uvicorn   # only needed once

# Start MCP server in SSE mode (exposed on port 8000)
# Expose port 8000 via a second Playit TCP tunnel (or any port-forward)
python unreal_mcp_server/unreal_mcp_server.py `
    --transport sse `
    --mcp-host 0.0.0.0 `
    --mcp-port 8000 `
    --unreal-host <playit-ue5-address> `
    --unreal-port <playit-ue5-port>
```

The server prints the SSE URL when it starts:
```
[UnrealMCP] SSE server listening on http://0.0.0.0:8000/sse
```

**As the remote agent, you connect to:**
```
http://<playit-mcp-address>:<playit-mcp-port>/sse
```

**Two Playit tunnels are needed:**
| Tunnel | Points to | Purpose |
|---|---|---|
| Tunnel 1 (UE5) | `localhost:55557` | MCP server → UE5 plugin |
| Tunnel 2 (MCP) | `localhost:8000` | GenSpark/cloud → MCP server |

Once connected via SSE, you call tools exactly the same way as any local client. Proceed to Section 3.

---

## 3. VERIFY CONNECTION FIRST — ALWAYS DO THIS BEFORE ANY OTHER ACTION

Call this tool immediately:

```
get_actors_in_level()
```

- ✅ Returns a list of actors → plugin is connected. Proceed.
- ❌ Returns a connection error → STOP. Tell the user:

> "The UnrealMCP plugin does not appear to be running. Please open UE5, enable the UnrealMCP plugin, and confirm the MCP server is connected. Look for 'Server started on 127.0.0.1:55557' in the UE5 Output Log. If you are using a Playit tunnel, confirm the tunnel is active."

Also confirm the engine version:
```python
exec_python(code="import unreal; print(unreal.SystemLibrary.get_engine_version())")
```
Expected: `5.6.x`

---

## 4. MANDATORY RULES — READ BEFORE EVERY ACTION

1. **Call MCP tools only.** Do NOT run shell commands, do NOT use `sandbox_ue5cli.py`. All 311 tools are available as direct MCP function calls.
2. **Never invent tool names or parameter names.** If you are unsure whether a tool exists, use `exec_python` to run an Unreal Python snippet instead of guessing.
3. **Always retrieve node IDs before connecting.** Call `get_blueprint_nodes` first; never hard-code GUIDs or guess node IDs.
4. **Always compile after changes.** Call `compile_blueprint` after any node additions or edits.
5. **Use `exec_python` for assets in custom folders.** The standard create commands default to `/Game/Blueprints/`; use the `exec_python` snippets in Section 8 to create assets in `/Game/Dantooine/` subfolders.
6. **Multiply per-frame values by DeltaSeconds.** All Tick-driven logic must be frame-rate independent.
7. **Call `SpawnDefaultController` for runtime-spawned AI pawns.**
8. **Validate after casts and object gets.** Always check `IsValid` before using a cast result.
9. **Report missing assets; do not guess paths.** If an asset is not found, report it and wait for the user to confirm the correct path.
10. **Use asset names (not full paths) for name-based commands.** See the gotchas table in Section 6.

---

## 5. TOOL REFERENCE (KEY TOOLS BY CATEGORY)

### Actor / Level
| Tool | Key Parameters |
|---|---|
| `get_actors_in_level` | *(none)* |
| `create_actor` | `name`, `type`, `location`, `rotation` |
| `spawn_blueprint_actor` | `blueprint_name`, `location`, `rotation` |
| `set_actor_transform` | `actor_name`, `location`, `rotation`, `scale` |
| `set_actor_property` | `actor_name`, `property_name`, `value` |
| `find_actors_by_name` | `name` |
| `delete_actor` | `actor_name` |
| `take_screenshot` | `filename` |
| `focus_viewport` | `actor_name` |

### Blueprint Class
| Tool | Key Parameters |
|---|---|
| `create_blueprint` | `name`, `parent_class`, `[path]` |
| `compile_blueprint` | `blueprint_name` |
| `add_component_to_blueprint` | `blueprint_name`, `component_type`, `component_name` |
| `set_blueprint_property` | `blueprint_name`, `property_name`, `value` |
| `set_component_property` | `blueprint_name`, `component_name`, `property_name`, `value` |
| `set_static_mesh_properties` | `blueprint_name`, `component_name`, `static_mesh` |
| `set_pawn_properties` | `blueprint_name`, `[auto_possess_ai]` |
| `set_blueprint_ai_controller` | `blueprint_name`, `ai_controller_class`, `auto_possess_ai` |
| `set_blueprint_parent_class` | `blueprint_name`, `new_parent_class` |
| `implement_blueprint_interface` | `blueprint_name`, `interface_name` ⚠️ name only |

### Blueprint Introspection
| Tool | Key Parameters |
|---|---|
| `get_blueprint_nodes` | `blueprint_name`, `graph_name` |
| `get_node_by_id` | `blueprint_name`, `graph_name`, `node_id` |
| `find_blueprint_nodes` | `blueprint_name`, `node_type` |
| `get_blueprint_graphs` | `blueprint_name` |
| `get_blueprint_variables` | `blueprint_name` |
| `get_blueprint_components` | `blueprint_name` |
| `get_blueprint_functions` | `blueprint_name` |
| `get_blueprint_variable_defaults` | `blueprint_name` |

### Variable
| Tool | Key Parameters |
|---|---|
| `add_blueprint_variable` | `blueprint_name`, `variable_name`, `variable_type`, `[is_exposed]` |
| `set_blueprint_variable_default` | `blueprint_name`, `variable_name`, `value` |
| `set_node_pin_value` | `blueprint_name`, `graph_name`, `node_id`, `pin_name`, `value` |

### Node Creation
| Tool | Key Parameters |
|---|---|
| `add_blueprint_event_node` | `blueprint_name`, `graph_name`, `event_name`, `[node_position]` |
| `add_blueprint_function_node` | `blueprint_name`, `graph_name`, `function_name`, `[node_position]` |
| `add_blueprint_variable_get_node` | `blueprint_name`, `graph_name`, `variable_name`, `[node_position]` |
| `add_blueprint_variable_set_node` | `blueprint_name`, `graph_name`, `variable_name`, `[node_position]` |
| `add_blueprint_branch_node` | `blueprint_name`, `graph_name`, `[node_position]` |
| `add_blueprint_cast_node` | `blueprint_name`, `graph_name`, `cast_to`, `[node_position]` |
| `add_blueprint_spawn_actor_node` | `blueprint_name`, `graph_name`, `actor_class`, `[node_position]` |
| `add_blueprint_sequence_node` | `blueprint_name`, `graph_name`, `[num_outputs]`, `[node_position]` |
| `add_blueprint_enhanced_input_action_node` | `blueprint_name`, `graph_name`, `action_asset` (full path), `[node_position]` |
| `add_blueprint_self_reference` | `blueprint_name`, `graph_name`, `[node_position]` |
| `add_blueprint_get_component_node` | `blueprint_name`, `graph_name`, `component_name`, `[node_position]` |
| `add_blueprint_for_loop_node` | `blueprint_name`, `graph_name`, `[node_position]` |
| `add_blueprint_for_each_loop_node` | `blueprint_name`, `graph_name`, `[node_position]` |
| `add_blueprint_do_once_node` | `blueprint_name`, `graph_name`, `[node_position]` |
| `add_blueprint_gate_node` | `blueprint_name`, `graph_name`, `[node_position]` |
| `add_blueprint_flip_flop_node` | `blueprint_name`, `graph_name`, `[node_position]` |
| `add_blueprint_switch_on_int_node` | `blueprint_name`, `graph_name`, `[node_position]` |
| `add_blueprint_comment_node` | `blueprint_name`, `graph_name`, `comment`, `[node_position]` |

### Node Editing
| Tool | Key Parameters |
|---|---|
| `connect_blueprint_nodes` | `blueprint_name`, `graph_name`, `source_node_id`, `source_pin`, `target_node_id`, `target_pin` |
| `disconnect_blueprint_nodes` | `blueprint_name`, `graph_name`, `source_node_id`, `source_pin`, `target_node_id`, `target_pin` |
| `delete_blueprint_node` | `blueprint_name`, `graph_name`, `node_id` |
| `move_blueprint_node` | `blueprint_name`, `graph_name`, `node_id`, `new_position` |

### AI / Behavior Tree
| Tool | Key Parameters |
|---|---|
| `create_behavior_tree` | `name`, `[path]` |
| `create_blackboard` | `name`, `[path]` |
| `set_behavior_tree_blackboard` | `behavior_tree_name`, `blackboard_name` ⚠️ names only |
| `setup_navmesh` | *(none or bounds params)* |
| `create_bt_task` | `name`, `[path]` |
| `create_bt_service` | `name`, `[path]` |
| `create_bt_decorator` | `name`, `[path]` |

### Animation
| Tool | Key Parameters |
|---|---|
| `create_animation_blueprint` | `name`, `skeleton`, `[path]` |
| `add_state_machine` | `anim_blueprint_name`, `state_machine_name` |
| `add_animation_state` | `anim_blueprint_name`, `state_machine_name`, `state_name` |
| `set_animation_for_state` | `anim_blueprint_name`, `state_machine_name`, `state_name`, `animation_asset` |
| `add_state_transition` | `anim_blueprint_name`, `state_machine_name`, `from_state`, `to_state` |
| `add_blend_space_node` | `anim_blueprint_name`, `blend_space_asset`, `[node_position]` |

### Data Assets
| Tool | Key Parameters |
|---|---|
| `create_struct` | `name`, `[path]` |
| `create_enum` | `name`, `[values]`, `[path]` |
| `create_data_table` | `name`, `row_struct`, `[path]` |
| `create_blueprint_interface` | `name`, `[path]` |

### Input
| Tool | Key Parameters |
|---|---|
| `create_enhanced_input_action` | `name`, `[path]` |
| `create_input_mapping_context` | `name`, `[path]` |
| `add_input_mapping` | `context_name`, `action_name`, `key` |

### UMG / Widgets
| Tool | Key Parameters |
|---|---|
| `create_umg_widget_blueprint` | `name`, `[path]` |
| `add_text_block_to_widget` | `widget_name`, `text_block_name`, `text`, `[position]`, `[size]` |
| `add_button_to_widget` | `widget_name`, `button_name`, `[position]`, `[size]` |
| `add_widget_to_viewport` | `blueprint_name`, `graph_name`, `widget_class`, `[node_position]` |
| `bind_widget_event` | `widget_name`, `widget_element`, `event_name`, `function_name` |

### Gameplay Framework
| Tool | Key Parameters |
|---|---|
| `set_game_mode_for_level` | `game_mode_name` ⚠️ asset name only |
| `create_game_mode` | `name`, `[path]` |
| `create_player_controller` | `name`, `[path]` |
| `create_game_instance` | `name`, `[path]` |
| `create_hud_blueprint` | `name`, `[path]` |
| `create_character_blueprint` | `name`, `[path]` |
| `create_ai_controller` | `name`, `[path]` |

### Material / VFX / Sequencer
| Tool | Key Parameters |
|---|---|
| `add_niagara_component` | `blueprint_name`, `component_name`, `[niagara_system]` |
| `add_spawn_niagara_at_location_node` | `blueprint_name`, `graph_name`, `niagara_system`, `[node_position]` |
| `set_material_instance_parameter` | `material_instance`, `parameter_name`, `value` |
| `create_material` | `name`, `[path]` |
| `set_sequencer_track` | `sequence_name`, `actor_name`, `track_type` |

### Save Game
| Tool | Key Parameters |
|---|---|
| `create_savegame_blueprint` | `name`, `[path]` |
| `setup_full_save_load_system` | `savegame_class`, `slot_name` |

### High-Level Composite Tools
| Tool | Description |
|---|---|
| `create_full_enemy_ai` | Creates a complete enemy AI (controller, behavior tree, blackboard) in one call |
| `create_fps_character` | Creates a full FPS character setup |
| `create_full_upgraded_enemy_ai` | Enhanced AI with patrol/combat/sensing |
| `build_complete_blueprint_graph` | Builds a full function graph from a description |
| `setup_full_save_load_system` | Wires up save/load from scratch |
| `create_round_based_game_system` | Creates round management system |
| `create_procedural_mesh_blueprint` | Procedural mesh BP |

---

## 6. COMMON PARAMETER GOTCHAS

| Command | ⚠️ Wrong | ✅ Correct |
|---|---|---|
| `set_game_mode_for_level` | `"/Game/Dantooine/Blueprints/Core/BP_DantooineGameMode"` | `"BP_DantooineGameMode"` |
| `implement_blueprint_interface` | `"/Game/Dantooine/Interfaces/BPI_Interactable"` | `"BPI_Interactable"` |
| `set_behavior_tree_blackboard` | `"/Game/Dantooine/AI/Blackboard/BB_RoamingNPC"` | `"BB_RoamingNPC"` |
| `create_data_table` | `row_struct="/Game/.../ST_DialogueLine"` | `row_struct="ST_DialogueLine"` |
| `add_blueprint_enhanced_input_action_node` | `action_asset="IA_Attack"` | `action_asset="/Game/Dantooine/Data/Input/IA_Attack"` (full path required) |
| `connect_blueprint_nodes` | using guessed node IDs | call `get_blueprint_nodes` first, use returned IDs |

---

## 7. BLUEPRINT PARENT CLASS LOOKUP

| Purpose | parent_class |
|---|---|
| Actor (general) | `Actor` |
| Character (player, NPC) | `Character` |
| AI Controller | `AIController` |
| Player Controller | `PlayerController` |
| Game Mode | `GameModeBase` |
| Game Instance | `GameInstance` |
| Actor Component | `ActorComponent` |
| Scene Component | `SceneComponent` |
| HUD | `HUD` |
| UMG Widget | `UserWidget` |
| Interface | (use `create_blueprint_interface`) |
| Pawn | `Pawn` |
| Trigger Volume | `TriggerVolume` |

---

## 8. ASSET CREATION VIA exec_python (FOR CUSTOM FOLDERS)

When `create_blueprint` or other commands default to `/Game/Blueprints/`, use these `exec_python` snippets to create assets in the correct Dantooine paths:

### Create Blueprint in a custom path
```python
exec_python(code="""
import unreal
factory = unreal.BlueprintFactory()
factory.set_editor_property('ParentClass', unreal.Actor)
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
bp = asset_tools.create_asset('BP_MyActor', '/Game/Dantooine/Blueprints/Core', unreal.Blueprint, factory)
unreal.EditorAssetLibrary.save_asset(bp.get_path_name())
print('Created:', bp.get_path_name())
""")
```

### Create UMG Widget Blueprint in custom path
```python
exec_python(code="""
import unreal
factory = unreal.WidgetBlueprintFactory()
factory.set_editor_property('ParentClass', unreal.UserWidget)
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
bp = asset_tools.create_asset('WBP_MyWidget', '/Game/Dantooine/Widgets', unreal.WidgetBlueprint, factory)
unreal.EditorAssetLibrary.save_asset(bp.get_path_name())
print('Created:', bp.get_path_name())
""")
```

### Create Behavior Tree in custom path
```python
exec_python(code="""
import unreal
factory = unreal.BehaviorTreeFactory()
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
bt = asset_tools.create_asset('BT_MyBT', '/Game/Dantooine/AI/BehaviorTrees', unreal.BehaviorTree, factory)
unreal.EditorAssetLibrary.save_asset(bt.get_path_name())
print('Created:', bt.get_path_name())
""")
```

### Create Blackboard in custom path
```python
exec_python(code="""
import unreal
factory = unreal.BlackboardDataFactory()
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
bb = asset_tools.create_asset('BB_MyBB', '/Game/Dantooine/AI/Blackboard', unreal.BlackboardData, factory)
unreal.EditorAssetLibrary.save_asset(bb.get_path_name())
print('Created:', bb.get_path_name())
""")
```

### Create folder if missing
```python
exec_python(code="""
import unreal
unreal.EditorAssetLibrary.make_directory('/Game/Dantooine/Blueprints/Combat')
print('Folder ready')
""")
```

### Check if asset exists
```python
exec_python(code="""
import unreal
exists = unreal.EditorAssetLibrary.does_asset_exist('/Game/Dantooine/Blueprints/Core/BP_DantooineGameMode')
print('Exists:', exists)
""")
```

### Save all modified assets
```python
exec_python(code="""
import unreal
unreal.EditorAssetLibrary.save_directory('/Game/Dantooine/', recursive=True, only_if_is_dirty=True)
print('All Dantooine assets saved.')
""")
```

---

## 9. STANDARD WORKFLOW PATTERNS

### Pattern A — Build a Blueprint with logic
1. `get_actors_in_level()` — verify connection
2. `get_blueprint_graphs(blueprint_name)` — list available graphs
3. `add_blueprint_event_node(blueprint_name, "EventGraph", "Event BeginPlay")`
4. `add_blueprint_function_node(blueprint_name, "EventGraph", "PrintString")`
5. `get_blueprint_nodes(blueprint_name, "EventGraph")` — get node IDs
6. `connect_blueprint_nodes(...)` — wire them up using IDs from step 5
7. `compile_blueprint(blueprint_name)` — always compile after changes

### Pattern B — Set up an AIController
1. `create_blueprint("BP_MyController", "AIController", "/Game/Dantooine/Blueprints/AI")`
2. `compile_blueprint("BP_MyController")`
3. `set_blueprint_ai_controller("BP_MyPawn", "BP_MyController", "PlacedInWorld")`
4. `compile_blueprint("BP_MyPawn")`

### Pattern C — New function with input/output pins
1. `add_custom_function(blueprint_name, function_name, input_params, output_params)`
2. `get_blueprint_nodes(blueprint_name, function_name)` — get node IDs
3. Add logic nodes, connect them, compile

### Pattern D — Safe actor reference (cast + validity check)
1. `add_blueprint_cast_node(blueprint_name, graph_name, "BP_PlayerJediCharacter")`
2. `add_blueprint_branch_node(blueprint_name, graph_name)` — for IsValid check
3. `get_blueprint_nodes(...)` — get IDs
4. Connect: GetPlayerPawn → Cast → IsValid → Branch → [use result]
5. `compile_blueprint`

### Pattern E — Widget HUD
1. `create_umg_widget_blueprint("WBP_HUD", "/Game/Dantooine/Widgets")`
2. `add_text_block_to_widget("WBP_HUD", "TB_HealthText", "100", [400,20], [200,40])`
3. `add_widget_to_viewport(blueprint_name, "EventGraph", "WBP_HUD")`
4. `compile_blueprint(blueprint_name)`

---

## 10. NAMING CONVENTIONS (MANDATORY)

Always use these prefixes. Incorrectly named assets cannot be located by other Blueprints.

| Prefix | Asset Type | Prefix | Asset Type |
|---|---|---|---|
| `BP_` | Blueprint | `WBP_` | Widget Blueprint |
| `BPI_` | Blueprint Interface | `ABP_` | Animation Blueprint |
| `BT_` | Behavior Tree | `BB_` | Blackboard |
| `BTT_` | BT Task Blueprint | `BTD_` | BT Decorator Blueprint |
| `BTS_` | BT Service Blueprint | `E_` | Enum |
| `ST_` | Struct | `DA_` | Data Asset |
| `DT_` | Data Table | `IA_` | Input Action |
| `IMC_` | Input Mapping Context | `LS_` | Level Sequence |
| `NS_` | Niagara System | `M_` | Material |
| `MI_` | Material Instance | `T_` | Texture |
| `SK_` | Skeletal Mesh | `SM_` | Static Mesh |
| `AN_` | Animation Sequence | `AM_` | Animation Montage |
| `BS_` | Blend Space | `AC_` | Actor Component |
| `BFL_` | Blueprint Function Library | | |

---

## 11. THIS PROJECT'S SPECIFIC SETUP — DANTOOINE (EnclaveProject)

**Project Name:** EnclaveProject
**Course:** GAM270, Academy of Art University, 2026
**Engine Version:** Unreal Engine 5.6
**Content Root:** `/Game/Dantooine/`
**Local Path (on developer's machine):** `C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Project2\EnclaveProject`
**Plugin port:** 55557 (UnrealMCP plugin, listening on localhost)
**GitHub:** https://github.com/CrispyW0nton/Unreal-MCP-Ghost

---

### Folder Structure (52 Folders under /Game/Dantooine/)

```
/Game/Dantooine/
├── AI/
│   ├── BehaviorTrees/
│   ├── Blackboard/
│   ├── Decorators/
│   ├── Services/
│   └── Tasks/
├── Animation/
│   ├── BlendSpaces/
│   ├── MasterJedi/
│   ├── Montages/
│   ├── NPCs/
│   ├── Player/
│   ├── Shared/
│   └── SparringOpponent/
├── Art/
│   ├── Audio/
│   │   ├── Dialogue/
│   │   ├── Music/
│   │   └── SFX/
│   ├── Characters/
│   ├── Environment/
│   ├── FX/
│   └── Weapons/
│       └── Lightsaber/
├── Blueprints/
│   ├── AI/
│   ├── Cinematics/
│   ├── Combat/
│   ├── Core/
│   ├── Debug/
│   ├── Interactables/
│   ├── NPC/
│   ├── Player/
│   ├── Quest/
│   ├── Triggers/
│   └── UI/
├── Data/
│   ├── DataAssets/
│   ├── DataTables/
│   ├── Dialogue/
│   ├── Enums/
│   ├── Input/
│   └── Structs/
├── Interfaces/
│   ├── BPI_CombatReceiver/
│   ├── BPI_DialogueParticipant/
│   └── BPI_Interactable/
├── Maps/
│   └── Dantooine_Level/
├── Sequences/
│   └── LightsaberBuild/
└── Widgets/
```

---

### Assets Already Created (49 of 49)

#### Enums (4) — `/Game/Dantooine/Data/Enums/`
| Asset | Values |
|---|---|
| `E_QuestStage` | None, Phase1_ArriveAtWorkbench, Phase2_GatherComponents, Phase3_AssembleLightsaber, Phase4_SparringTrial, Complete |
| `E_NPCDialogueMode` | Idle, Greeting, InConversation, Farewell |
| `E_InteractableType` | None, Workbench, QuestItem, Door, CollectiblePart, InformationTerminal |
| `E_SparringState` | Idle, Waiting, Active, Paused, PlayerWon, OpponentWon |

#### Structs (5) — `/Game/Dantooine/Data/Structs/`
`ST_DialogueLine`, `ST_DialogueNode`, `ST_DialogueChoice`, `ST_NPCBarkSet`, `ST_SparConfig`

#### Interfaces (3) — `/Game/Dantooine/Interfaces/`
| Asset | Functions |
|---|---|
| `BPI_Interactable` | `Interact(Instigator: Actor)`, `GetInteractionText() → Text` |
| `BPI_DialogueParticipant` | `StartDialogue(Partner: Actor)`, `EndDialogue`, `GetSpeakerName() → string` |
| `BPI_CombatReceiver` | `ReceiveHit(Damage: float, Direction: Vector)`, `GetCurrentHealth() → float` |

#### Input (7) — `/Game/Dantooine/Data/Input/`
| Asset | Type |
|---|---|
| `IA_Move` | InputAction (Axis2D) |
| `IA_Look` | InputAction (Axis2D) |
| `IA_Jump` | InputAction (Digital) |
| `IA_Interact` | InputAction (Digital) |
| `IA_Attack` | InputAction (Digital) |
| `IA_Block` | InputAction (Digital) |
| `IMC_Dantooine` | InputMappingContext |

**IMC_Dantooine bindings (manual in editor):**
- IA_Move → WASD + Left Stick
- IA_Look → Mouse XY + Right Stick
- IA_Jump → Spacebar + South Button
- IA_Interact → E + West Button
- IA_Attack → Left Mouse Button + Right Trigger
- IA_Block → Right Mouse Button + Left Trigger

#### Core Framework Blueprints (4) — `/Game/Dantooine/Blueprints/Core/`
| Asset | Parent |
|---|---|
| `BP_DantooineGameMode` | GameModeBase |
| `BP_DantooinePlayerController` | PlayerController |
| `BP_SkyBirdShip` | Actor |
| *(also in Quest/)* `BP_DantooineQuestManager` | Actor |

#### Player Blueprint (1) — `/Game/Dantooine/Blueprints/Player/`
`BP_PlayerJediCharacter` (parent: Character)
- Variables: Health (float=100), MaxHealth (float=100), IsAttacking (bool), IsBlocking (bool), HasLightsaber (bool)
- SpringArm + Camera components needed (add in editor)
- Enhanced Input bindings: IA_Move, IA_Look, IA_Jump, IA_Attack, IA_Block, IA_Interact

#### Quest Blueprints (2)
| Asset | Path |
|---|---|
| `BP_DantooineQuestManager` | `/Game/Dantooine/Blueprints/Quest/` |
| `BP_LevelCompletionHandler` | `/Game/Dantooine/Blueprints/Quest/` |

#### NPC Blueprints (5)
| Asset | Path | Parent |
|---|---|---|
| `BP_MasterJedi` | `/Game/Dantooine/Blueprints/NPC/` | Character |
| `BP_RoamingNPC_Base` | `/Game/Dantooine/Blueprints/NPC/` | Character |
| `BP_RoamingNPC_StudentA` | `/Game/Dantooine/Blueprints/NPC/` | Character (reparent to BP_RoamingNPC_Base) |
| `BP_RoamingNPC_StudentB` | `/Game/Dantooine/Blueprints/NPC/` | Character (reparent to BP_RoamingNPC_Base) |
| `BP_SparringOpponent` | `/Game/Dantooine/Blueprints/Combat/` | Character |

#### World Actors (3)
| Asset | Path | Implements |
|---|---|---|
| `BP_LightsaberWorkbench` | `/Game/Dantooine/Blueprints/Interactables/` | BPI_Interactable |
| `BP_TrainingAreaTrigger` | `/Game/Dantooine/Blueprints/Triggers/` | — |
| `BP_LevelCompletionHandler` | `/Game/Dantooine/Blueprints/Quest/` | — |

#### AI Controllers (2) — `/Game/Dantooine/Blueprints/AI/`
| Asset | Manages |
|---|---|
| `BP_NPC_AIController` | BP_RoamingNPC_Base |
| `BP_Sparring_AIController` | BP_SparringOpponent |

#### AI Assets (5)
| Asset | Path | Type |
|---|---|---|
| `BB_RoamingNPC` | `/Game/Dantooine/AI/Blackboard/` | BlackboardData |
| `BB_Sparring` | `/Game/Dantooine/AI/Blackboard/` | BlackboardData |
| `BT_RoamingNPC` | `/Game/Dantooine/AI/BehaviorTrees/` | BehaviorTree |
| `BT_Sparring` | `/Game/Dantooine/AI/BehaviorTrees/` | BehaviorTree |
| `BTT_FindRandomPatrol` | `/Game/Dantooine/AI/Tasks/` | BT Task Blueprint |

**Blackboard keys needed (add in editor):**
- `BB_RoamingNPC`: PatrolLocation (Vector), IsTalking (Bool), ConversationTarget (Object), WaitDuration (Float)
- `BB_Sparring`: TargetActor (Object), FightActive (Bool), HitsTaken (Int)

**Behavior Trees:** BT_RoamingNPC linked to BB_RoamingNPC; BT_Sparring linked to BB_Sparring.

#### Animation Blueprints (3)
| Asset | Path | Skeleton |
|---|---|---|
| `ABP_PlayerJedi` | `/Game/Dantooine/Animation/Player/` | SK_PlayerJedi (assign after import) |
| `ABP_RoamingNPC` | `/Game/Dantooine/Animation/NPCs/` | SK_NPC_Student (assign after import) |
| `ABP_SparringOpponent` | `/Game/Dantooine/Animation/SparringOpponent/` | SK_SparringOpponent (assign after import) |

#### UI Widgets (6) — `/Game/Dantooine/Widgets/`
| Asset | Purpose |
|---|---|
| `WBP_HUD` | Main gameplay HUD |
| `WBP_DialogueBox` | NPC conversation UI |
| `WBP_QuestTracker` | Quest progress display |
| `WBP_InteractPrompt` | "[E] to Interact" prompt |
| `WBP_SparringHUD` | Combat phase UI |
| `WBP_LevelComplete` | Victory/completion screen |

#### Sequences (1)
`LS_LightsaberBuild` — `/Game/Dantooine/Sequences/LightsaberBuild/`

---

### Art Assets Still Needed (manual artist work — not MCP-creatable)

**Skeletal Meshes:** SK_PlayerJedi, SK_MasterJedi, SK_NPC_Student_A, SK_NPC_Student_B, SK_SparringOpponent

**Static Meshes:** SM_LightsaberWorkbench, SM_TrainingDummy, SM_DantooineSkyShip

**Animation Sequences:** AN_Player_Idle, AN_Player_Walk, AN_Player_Run, AN_Player_Jump, AN_Player_Attack, AN_Player_Block, AN_NPC_Idle, AN_NPC_Walk, AN_Sparring_Attack

**Audio:** SFX_Saber_Hum, SFX_Saber_Swing, SFX_Saber_Block, SFX_Workbench_Assemble, MX_DantooineAmbient, MX_CombatIntensity

**Niagara Systems:** NS_SaberGlow, NS_SaberTrail, NS_WorkbenchSparks, NS_LevelComplete, NS_ForceField

---

### Project Settings (set in editor, not via MCP)
```
Project Settings → Maps & Modes:
  Default GameMode: BP_DantooineGameMode
  Game Default Map: /Game/Dantooine/Maps/Dantooine_Level/Dantooine_Level
  Editor Startup Map: same
```

**Or via MCP (preferred):**
```
set_game_mode_for_level(game_mode_name="BP_DantooineGameMode")
```

---

### First task for this session:
```
[DESCRIBE EXACTLY WHAT YOU WANT THE AGENT TO DO IN THIS SESSION]

Example: "Wire up BP_PlayerJediCharacter's EventGraph to handle IA_Move and IA_Look 
input actions using Enhanced Input, and add the BeginPlay event that creates and adds 
WBP_HUD to the viewport."
```

---

## ✂️ END OF PROMPT ✂️
