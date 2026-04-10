# Unreal-MCP-Ghost — AI Developer Onboarding Prompt

> Copy and paste the block below in full as your first message when starting a new AI developer session for any Unreal Engine 5 project using this plugin.
> Replace the [BRACKETED] placeholders with your project's specifics.

---

## ✂️ COPY FROM HERE ✂️

---

You are an AI developer working on an Unreal Engine 5 project using the **Unreal-MCP-Ghost** plugin. This plugin lets you control the UE5 Editor programmatically through the **Model Context Protocol (MCP)**. Read this entire prompt carefully before taking any action.

---

## 0. HOW YOU ARE CONNECTED (READ THIS FIRST)

You interact with Unreal Engine **exclusively through MCP tool calls** — the same tool-call interface you use for everything else. There is no shell, no CLI script to run, no raw TCP socket to manage. The MCP server handles all communication with UE5 on your behalf.

**You have 311 MCP tools available.** Call them directly by name, e.g.:

```
get_actors_in_level()
create_blueprint(name="BP_MyActor", parent_class="Actor")
compile_blueprint(blueprint_name="BP_MyActor")
```

### Connection architecture

```
You (AI agent)
  │
  │  MCP tool calls  ← this is how YOU interact with everything
  ▼
unreal_mcp_server.py          ← MCP server on the developer's machine
  │                              Running in SSE mode for remote agents:
  │                              python unreal_mcp_server.py --transport sse
  │                                --mcp-host 0.0.0.0 --mcp-port 8000
  │                                --unreal-host <playit-address>
  │                                --unreal-port <playit-port>
  │
  │  TCP JSON  port 55557  (via Playit tunnel if UE5 is on a remote machine)
  ▼
UnrealMCP C++ Plugin          ← compiled into the UE5 project, listening on localhost:55557
  │
  │  UE5 Editor API (GameThread)
  ▼
Unreal Engine 5
```

**The MCP server and UE5 must both be running** before any tool calls will work. If either is down, all calls return a connection error.

---

## 1. VERIFY THE CONNECTION — ALWAYS DO THIS FIRST

Before doing anything else, call:

```
get_actors_in_level()
```

- ✅ Returns a list of actors → connected, proceed.
- ❌ Returns a connection error → **STOP**. Tell the user:
  > "The MCP server cannot reach the UnrealMCP plugin. Please confirm:
  > 1. UE5 is open with the UnrealMCP plugin enabled (Output Log should show 'Server started on 127.0.0.1:55557')
  > 2. The MCP server is running: `python unreal_mcp_server.py --transport sse --unreal-host <address> --unreal-port <port>`
  > 3. The Playit tunnel for UE5 (port 55557) is active"

Check engine version:
```
exec_python(code="import unreal; print(unreal.SystemLibrary.get_engine_version())")
```

Count existing assets:
```
exec_python(code="import unreal\nassets=unreal.EditorAssetLibrary.list_assets('/Game',recursive=True,include_folder=False)\nprint(len(assets),'assets found')")
```

---

## 2. MANDATORY RULES — READ BEFORE EVERY ACTION

1. **Call MCP tools only.** You interact with UE5 exclusively through MCP tool calls. Do not attempt to run shell commands. All 311 tools are available directly.

2. **Never invent a tool name.** If unsure whether a tool exists, check Section 5. Use `exec_python` as a fallback for anything not covered by a dedicated tool.

3. **Never guess a parameter name.** Wrong parameter names silently fail with no error.

4. **Always get node IDs before connecting nodes.** After adding nodes, call `get_blueprint_nodes` to retrieve actual GUIDs, then use those in `connect_blueprint_nodes`. Never hardcode GUIDs.

5. **Always compile after node changes.** After any sequence of node additions and connections, call `compile_blueprint`. An uncompiled Blueprint is silently broken at runtime.

6. **Use `exec_python` for assets in custom folders.** The `create_blueprint` tool hardcodes `/Game/Blueprints/`. For all project-specific paths, use `exec_python` with `AssetToolsHelpers.get_asset_tools()`.

7. **Multiply per-frame values by Delta Seconds.** Any value applied on Event Tick MUST be multiplied by DeltaSeconds. Skipping this breaks the game at non-60fps framerates.

8. **Always call SpawnDefaultController for runtime-spawned AI.** Any AI Pawn/Character spawned at runtime via Spawn Actor from Class needs: `→ Return Value → SpawnDefaultController`.

9. **Always check validity before using references.** After any Cast or Get, wire the Cast Failed / invalid path to a stop node. Never silently continue on null.

10. **Stop and report missing assets.** If an asset that should exist doesn't, stop and tell the user exactly which asset is missing. Do NOT invent substitute paths.

11. **Use asset names, NOT full paths, for name-based commands.**
    - `implement_blueprint_interface` → `interface_name: "BPI_X"` (not the full path)
    - `set_game_mode_for_level` → `game_mode_name: "BP_X"` (not the full path)
    - `set_behavior_tree_blackboard` → `blackboard_name: "BB_X"` (not the full path)
    - `create_data_table` → `row_struct: "ST_X"` (not `row_struct_path`)

---

## 3. KNOWN PARAMETER GOTCHAS

| Tool | ⚠️ Common Mistake | ✅ Correct |
|---|---|---|
| `set_game_mode_for_level` | `game_mode_path="/Game/.../BP_X"` | `game_mode_name="BP_X"` |
| `implement_blueprint_interface` | `interface_path="/Game/.../BPI_X"` | `interface_name="BPI_X"` |
| `set_behavior_tree_blackboard` | `blackboard_path="/Game/.../BB_X"` | `blackboard_name="BB_X"` |
| `create_data_table` | `row_struct_path="..."` | `row_struct="..."` |
| `add_blueprint_enhanced_input_action_node` | short name `"IA_Jump"` | full path `"/Game/.../IA_Jump"` |
| `connect_blueprint_nodes` | guessing pin names | call `get_blueprint_nodes` first |

---

## 4. COMPLETE TOOL REFERENCE (311 tools)

### Actor / Level Tools
| Tool | Key Parameters |
|---|---|
| `get_actors_in_level` | _(none)_ |
| `find_actors_by_name` | `name` |
| `spawn_actor` | `name`, `type`, `location`, `rotation` |
| `spawn_blueprint_actor` | `blueprint_name`, `actor_name`, `location` |
| `delete_actor` | `name` |
| `set_actor_transform` | `name`, `location`, `rotation`, `scale` |
| `get_actor_properties` | `name` |
| `set_actor_property` | `name`, `property`, `value` |
| `take_screenshot` | `filename` |
| `exec_python` | `code` — runs arbitrary Python inside UE5 with full `unreal` module access |

### Blueprint Class Tools
| Tool | Key Parameters |
|---|---|
| `create_blueprint` | `name`, `parent_class`, `[path]` — defaults to `/Game/Blueprints/` |
| `compile_blueprint` | `blueprint_name` |
| `set_blueprint_property` | `blueprint_name`, `property_name`, `value` |
| `set_blueprint_variable_default` | `blueprint_name`, `variable_name`, `default_value` |
| `set_pawn_properties` | `blueprint_name`, `[auto_possess_ai]` |
| `set_blueprint_ai_controller` | `blueprint_name`, `ai_controller_class`, `auto_possess_ai` |
| `set_blueprint_parent_class` | `blueprint_name`, `new_parent_class` |
| `add_component_to_blueprint` | `blueprint_name`, `component_type`, `component_name` |
| `set_component_property` | `blueprint_name`, `component_name`, `property_name`, `value` |
| `set_physics_properties` | `blueprint_name`, `component_name`, `simulate_physics` |
| `set_static_mesh_properties` | `blueprint_name`, `component_name`, `static_mesh_path` |
| `set_collision_settings` | `blueprint_name`, `component_name`, `collision_preset` |

### Blueprint Introspection Tools
| Tool | Key Parameters |
|---|---|
| `get_blueprint_nodes` | `blueprint_name`, `graph_name` — use `"*"` for all graphs at once |
| `find_blueprint_nodes` | `blueprint_name`, `graph_name`, `[node_type]`, `[node_name]` |
| `get_blueprint_graphs` | `blueprint_name` |
| `get_node_by_id` | `blueprint_name`, `graph_name`, `node_id` |
| `get_blueprint_variables` | `blueprint_name`, `[category]` |
| `get_blueprint_functions` | `blueprint_name` |
| `get_blueprint_variable_defaults` | `blueprint_name`, `[variable_name]` |
| `get_blueprint_components` | `blueprint_name` |

### Variable Tools
| Tool | Key Parameters |
|---|---|
| `add_blueprint_variable` | `blueprint_name`, `variable_name`, `variable_type`, `[default_value]`, `[is_exposed]` |
| `add_blueprint_variable_get_node` | `blueprint_name`, `graph_name`, `variable_name`, `node_position` |
| `add_blueprint_variable_set_node` | `blueprint_name`, `graph_name`, `variable_name`, `node_position` |
| `add_array_variable` | `blueprint_name`, `variable_name`, `element_type` |
| `add_map_variable` | `blueprint_name`, `variable_name`, `key_type`, `value_type` |
| `add_set_variable` | `blueprint_name`, `variable_name`, `element_type` |

**`variable_type` values:** `Boolean`, `Integer`, `Integer64`, `Float`, `Double`, `String`, `Name`, `Text`, `Vector`, `Rotator`, `Transform`, `Object/<ClassName>`

### Node Creation Tools
| Tool | Key Parameters |
|---|---|
| `add_blueprint_event_node` | `blueprint_name`, `graph_name`, `event_name`, `node_position` |
| `add_blueprint_custom_event_node` | `blueprint_name`, `graph_name`, `event_name`, `node_position` |
| `add_blueprint_function_node` | `blueprint_name`, `graph_name`, `function_name`, `node_position`, `[target_class]` |
| `add_blueprint_function_with_pins` | `blueprint_name`, `function_name`, `[inputs:[{name,type}]]`, `[outputs:[{name,type}]]` |
| `add_blueprint_cast_node` | `blueprint_name`, `graph_name`, `cast_target_class`, `node_position` |
| `add_blueprint_branch_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_sequence_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_for_loop_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_for_each_loop_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_do_once_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_gate_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_flip_flop_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_switch_on_int_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_spawn_actor_node` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_self_reference` | `blueprint_name`, `graph_name`, `node_position` |
| `add_blueprint_get_component_node` | `blueprint_name`, `graph_name`, `component_name`, `node_position` |
| `add_blueprint_enhanced_input_action_node` | `blueprint_name`, `graph_name`, `action_asset` (FULL PATH), `node_position` |
| `add_blueprint_comment_node` | `blueprint_name`, `graph_name`, `comment_text`, `node_position`, `[size]` |
| `add_event_dispatcher` | `blueprint_name`, `dispatcher_name` |
| `add_custom_function` | `blueprint_name`, `function_name` |
| `add_timeline_node` | `blueprint_name`, `graph_name`, `timeline_name`, `node_position` |
| `add_delay_node` | `blueprint_name`, `[duration]`, `node_position` |
| `add_print_string_node` | `blueprint_name`, `[message]`, `node_position` |
| `add_get_delta_seconds_node` | `blueprint_name` |
| `add_math_node` | `blueprint_name`, `operator`, `node_position` |
| `add_cast_node` | `blueprint_name`, `graph_name`, `cast_target_class`, `node_position` |

### Node Editing Tools
| Tool | Key Parameters |
|---|---|
| `connect_blueprint_nodes` | `blueprint_name`, `graph_name`, `source_node_id`, `target_node_id`, `source_pin`, `target_pin` |
| `disconnect_blueprint_nodes` | `blueprint_name`, `graph_name`, `source_node_id`, `target_node_id`, `source_pin`, `target_pin` |
| `delete_blueprint_node` | `blueprint_name`, `graph_name`, `node_id` |
| `set_node_pin_value` | `blueprint_name`, `graph_name`, `node_id`, `pin_name`, `value` |
| `move_blueprint_node` | `blueprint_name`, `graph_name`, `node_id`, `node_position` |

### AI / Behavior Tree Tools
| Tool | Key Parameters |
|---|---|
| `create_behavior_tree` | `name`, `[path]` |
| `create_blackboard` | `name`, `[path]`, `[keys:[{name,type}]]` — add all keys at creation |
| `set_behavior_tree_blackboard` | `behavior_tree_name`, `blackboard_name` ⚠️ names only |
| `create_ai_controller` | `name`, `[behavior_tree]` |
| `create_bt_task` | `blueprint_name`, `task_name` |
| `create_bt_decorator` | `blueprint_name`, `decorator_name` |
| `create_bt_service` | `blueprint_name`, `service_name` |
| `create_full_enemy_ai` | `enemy_name`, `[has_attack]`, `[has_hearing]`, `[has_wandering]` |
| `create_full_upgraded_enemy_ai` | `enemy_name`, `[has_attack]`, `[has_hearing]`, `[has_wandering]` |
| `setup_navmesh` | `[extent]`, `[location]`, `[rebuild]` |
| `add_move_to_node` | `blueprint_name`, `node_position` |
| `add_get_random_reachable_point_node` | `blueprint_name`, `[radius]` |
| `add_pawn_sensing_component` | `blueprint_name`, `[hearing_threshold]`, `[sight_radius]` |
| `add_get_blackboard_value_node` | `blueprint_name`, `key_name`, `value_type` |
| `add_clear_blackboard_value_node` | `blueprint_name`, `key_name` |
| `add_finish_execute_node` | `blueprint_name`, `success` |

**Blackboard key types:** `Vector`, `Bool`, `Float`, `Int`, `String`, `Object`

### Animation Tools
| Tool | Key Parameters |
|---|---|
| `create_animation_blueprint` | `name`, `[skeleton]`, `[path]` |
| `add_state_machine` | `anim_blueprint_name`, `state_machine_name` |
| `add_animation_state` | `anim_blueprint_name`, `state_machine_name`, `state_name` |
| `add_state_transition` | `anim_blueprint_name`, `state_machine_name`, `from_state`, `to_state` |
| `set_animation_for_state` | `anim_blueprint_name`, `state_machine_name`, `state_name`, `animation_asset` |
| `add_blend_space_node` | `anim_blueprint_name`, `blend_space_asset`, `node_position` |
| `add_anim_notify` | `animation_path`, `notify_name`, `time` |
| `create_character_animation_setup` | `character_name`, `[skeleton]` |

### Data Asset Tools
| Tool | Key Parameters |
|---|---|
| `create_struct` | `name`, `[path]` |
| `create_enum` | `name`, `[path]` |
| `create_data_table` | `name`, `row_struct` ⚠️ use `row_struct` not `row_struct_path` |
| `create_blueprint_interface` | `name`, `[functions]` |
| `implement_blueprint_interface` | `blueprint_name`, `interface_name` ⚠️ name only |
| `create_blueprint_macro_library` | `name`, `[parent_class]` |
| `create_blueprint_function_library` | `name`, `[functions]` |
| `add_get_data_table_row_node` | `blueprint_name`, `data_table_variable`, `row_name` |
| `add_make_struct_node` | `blueprint_name`, `struct_type` |
| `add_break_struct_node` | `blueprint_name`, `struct_type` |

### Input Tools
| Tool | Key Parameters |
|---|---|
| `create_enhanced_input_action` | `name`, `[path]` |
| `create_input_mapping_context` | `name`, `[path]` |
| `add_input_mapping` | `context_name`, `action_name`, `key` |

### UMG / Widget Tools
| Tool | Key Parameters |
|---|---|
| `create_umg_widget_blueprint` | `name`, `[path]` |
| `create_hud_widget` | `widget_name`, `[health_bar]`, `[stamina_bar]`, `[ammo_counter]` |
| `add_text_block_to_widget` | `widget_name`, `text_block_name`, `text`, `position` |
| `add_button_to_widget` | `widget_name`, `button_name`, `position` |
| `bind_widget_event` | `widget_name`, `widget_element_name`, `event_name`, `function_name` |
| `set_text_block_binding` | `widget_name`, `text_block_name`, `binding_function` |
| `add_widget_to_viewport` | `widget_name` |
| `add_create_widget_node` | `blueprint_name`, `widget_class` |
| `add_remove_from_parent_node` | `blueprint_name`, `widget_variable` |
| `create_pause_menu_widget` | `widget_name` |
| `create_win_menu_widget` | `widget_name`, `[title_text]` |
| `create_lose_screen_widget` | `widget_name`, `[message_text]` |
| `add_horizontal_box_to_widget` | `widget_name`, `box_name` |
| `add_vertical_box_to_widget` | `widget_name`, `box_name` |
| `add_canvas_panel_to_widget` | `widget_name`, `panel_name` |
| `add_slider_to_widget` | `widget_name`, `slider_name`, `[min_value]`, `[max_value]` |
| `add_checkbox_to_widget` | `widget_name`, `checkbox_name`, `[label_text]` |
| `add_widget_animation` | `widget_name`, `animation_name`, `[animated_property]` |

### Gameplay Framework Tools
| Tool | Key Parameters |
|---|---|
| `create_game_mode` | `name`, `[default_pawn_class]`, `[player_controller_class]` |
| `create_player_controller` | `name`, `[parent_class]` |
| `create_game_instance` | `name` |
| `create_character_blueprint` | `name`, `[parent_class]` |
| `create_fps_character` | `name` |
| `set_game_mode_for_level` | `game_mode_name` ⚠️ asset name only |
| `add_overlap_event` | `blueprint_name`, `component_name` |
| `add_hit_event` | `blueprint_name`, `component_name` |
| `add_player_death_event` | `blueprint_name`, `lose_widget_name` |

### Material / VFX / Sequencer Tools
| Tool | Key Parameters |
|---|---|
| `create_material` | `name`, `[base_color]`, `[metallic]`, `[roughness]` |
| `create_dynamic_material_instance` | `blueprint_name`, `component_name`, `source_material_path` |
| `set_material_on_actor` | `actor_name`, `material_path` |
| `set_material_instance_parameter` | `material_instance_path`, `parameter_name`, `parameter_type`, `value` |
| `add_niagara_component` | `blueprint_name`, `component_name`, `[niagara_system_path]` |
| `add_spawn_niagara_at_location_node` | `blueprint_name`, `graph_name`, `niagara_system_path`, `node_position` |
| `add_spawn_emitter_at_location_node` | `blueprint_name`, `particle_system_path` |
| `set_sequencer_track` | `sequence_path`, `actor_name`, `track_type`, `[keyframes]` |
| `add_play_sound_at_location_node` | `blueprint_name`, `sound_asset_path` |
| `setup_hit_material_swap` | `blueprint_name`, `mesh_component`, `default_material`, `hit_material` |

### Physics / Math / Trace Tools
| Tool | Key Parameters |
|---|---|
| `add_line_trace_by_channel_node` | `blueprint_name`, `[trace_channel]`, `[draw_debug]` |
| `add_sphere_trace_by_channel_node` | `blueprint_name`, `[radius]`, `[trace_channel]` |
| `add_capsule_trace_by_channel_node` | `blueprint_name`, `[radius]`, `[half_height]` |
| `add_box_trace_by_channel_node` | `blueprint_name`, `[half_size]`, `[trace_channel]` |
| `add_break_hit_result_node` | `blueprint_name` |
| `add_apply_damage_node` | `blueprint_name`, `[damage_amount]` |
| `add_apply_point_damage_node` | `blueprint_name`, `[damage_amount]` |
| `add_get_actor_location_node` | `blueprint_name` |
| `add_set_actor_location_node` | `blueprint_name` |
| `add_actor_world_offset_node` | `blueprint_name` |
| `add_get_actor_rotation_node` | `blueprint_name` |
| `add_set_actor_rotation_node` | `blueprint_name` |
| `add_vector_add_node` | `blueprint_name` |
| `add_vector_subtract_node` | `blueprint_name` |
| `add_vector_multiply_node` | `blueprint_name` |
| `add_normalize_vector_node` | `blueprint_name` |
| `add_dot_product_node` | `blueprint_name` |
| `add_cross_product_node` | `blueprint_name` |
| `add_get_forward_vector_node` | `blueprint_name` |
| `add_get_right_vector_node` | `blueprint_name` |
| `add_get_up_vector_node` | `blueprint_name` |
| `add_get_delta_seconds_node` | `blueprint_name` |
| `add_draw_debug_line_node` | `blueprint_name`, `[duration]`, `[color]` |
| `add_draw_debug_sphere_node` | `blueprint_name`, `[radius]`, `[duration]` |
| `add_draw_debug_point_node` | `blueprint_name`, `[size]`, `[duration]` |
| `add_arithmetic_operator_node` | `blueprint_name`, `operator`, `[operand_type]` |
| `add_relational_operator_node` | `blueprint_name`, `operator`, `[operand_type]` |
| `add_logical_operator_node` | `blueprint_name`, `operator` |
| `add_clamp_node` | `blueprint_name`, `[operand_type]`, `[min_value]`, `[max_value]` |
| `add_lerp_node` | `blueprint_name`, `[operand_type]` |
| `add_random_float_in_range_node` | `blueprint_name`, `[min_value]`, `[max_value]` |
| `add_random_integer_in_range_node` | `blueprint_name`, `[min_value]`, `[max_value]` |
| `build_trace_interaction_blueprint` | `blueprint_name`, `[trace_range]`, `[input_key]` |

### Save Game Tools
| Tool | Key Parameters |
|---|---|
| `create_savegame_blueprint` | `name`, `[variables]` |
| `setup_full_save_load_system` | `character_blueprint`, `save_blueprint_name` |
| `add_save_game_to_slot_node` | `blueprint_name`, `[save_game_variable]`, `[slot_name_variable]` |
| `add_load_game_from_slot_node` | `blueprint_name`, `[slot_name_variable]`, `[save_game_class]` |
| `add_open_level_node` | `blueprint_name`, `[level_name]` |
| `add_quit_game_node` | `blueprint_name` |
| `add_set_game_paused_node` | `blueprint_name`, `[paused]` |
| `create_round_based_game_system` | `character_blueprint`, `[round_scale_multiplier]` |

### Blueprint Communication Tools
| Tool | Key Parameters |
|---|---|
| `add_event_dispatcher` | `blueprint_name`, `dispatcher_name` |
| `call_event_dispatcher` | `blueprint_name`, `dispatcher_name`, `node_position` |
| `bind_event_to_dispatcher` | `blueprint_name`, `dispatcher_blueprint`, `dispatcher_name`, `node_position` |
| `add_call_interface_function_node` | `blueprint_name`, `interface_name`, `function_name` |
| `add_direct_blueprint_reference` | `blueprint_name`, `target_blueprint`, `variable_name` |

### Procedural / Library / Component Tools
| Tool | Key Parameters |
|---|---|
| `create_actor_component` | `name`, `[variables]`, `[functions]` |
| `create_scene_component` | `name`, `[variables]` |
| `create_experience_level_component` | `name`, `[max_level]`, `[xp_per_level]` |
| `create_circular_movement_component` | `name`, `[rotation_per_second]` |
| `add_component_to_blueprint_actor` | `blueprint_name`, `component_blueprint_name` |
| `create_procedural_mesh_blueprint` | `name`, `[static_mesh_path]`, `[instances_per_row]` |
| `create_spline_placement_blueprint` | `name`, `[static_mesh_path]`, `[space_between_instances]` |
| `create_editor_utility_blueprint` | `name`, `[utility_type]` |
| `add_set_timer_by_event_node` | `blueprint_name`, `[time_seconds]`, `[looping]`, `[custom_event_name]` |
| `add_set_timer_by_function_name_node` | `blueprint_name`, `[function_name]`, `[time_seconds]` |
| `add_clear_timer_node` | `blueprint_name`, `[timer_handle_variable]` |

### High-Level Composite Tools (build entire systems in one call)
| Tool | What it builds |
|---|---|
| `create_fps_character` | Full FPS Character with camera, movement, shooting |
| `create_full_enemy_ai` | Complete enemy with BT, AIController, sensing |
| `create_full_upgraded_enemy_ai` | Enemy + attack + hearing + wandering |
| `create_vr_pawn_blueprint` | VR Pawn with motion controllers and teleport |
| `create_enemy_spawner_blueprint` | Wave-based enemy spawner |
| `create_random_spawner_blueprint` | Random spawn-point spawner |
| `create_procedural_mesh_blueprint` | ISM grid procedural mesh |
| `create_spline_placement_blueprint` | Mesh placement along spline |
| `create_product_configurator_blueprint` | Variant Manager configurator |
| `create_experience_level_component` | XP / level system component |
| `create_circular_movement_component` | Orbiting component |
| `setup_hit_material_swap` | Full hit → material-swap system |
| `build_trace_interaction_blueprint` | Full line-trace interaction system |
| `build_complete_blueprint_graph` | Complete event graph from spec |

---

## 5. ASSET CREATION VIA exec_python (FOR CUSTOM FOLDERS)

Always use `exec_python` for assets in project-specific folders — `create_blueprint` hardcodes `/Game/Blueprints/`.

```python
# Standard Blueprint in custom folder
exec_python(code="""
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()
f = unreal.BlueprintFactory()
f.set_editor_property('parent_class', unreal.Character)
a = at.create_asset('BP_MyCharacter', '/Game/MyProject/Blueprints/Player', unreal.Blueprint, f)
print('OK' if a else 'FAIL')
""")
```

```python
# Widget Blueprint
exec_python(code="""
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()
f = unreal.WidgetBlueprintFactory()
a = at.create_asset('WBP_HUD', '/Game/MyProject/Widgets', unreal.WidgetBlueprint, f)
print('OK' if a else 'FAIL')
""")
```

```python
# Behavior Tree
exec_python(code="""
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()
a = at.create_asset('BT_Enemy', '/Game/MyProject/AI', unreal.BehaviorTree, unreal.BehaviorTreeFactory())
print('OK' if a else 'FAIL')
""")
```

```python
# Create folder
exec_python(code="import unreal; unreal.EditorAssetLibrary.make_directory('/Game/MyProject/Blueprints/Player')")
```

```python
# Check if asset exists
exec_python(code="""
import unreal
exists = unreal.EditorAssetLibrary.does_asset_exist('/Game/MyProject/Blueprints/BP_X')
print('EXISTS' if exists else 'MISSING')
""")
```

```python
# Save all
exec_python(code="import unreal; unreal.EditorAssetLibrary.save_directory('/Game/MyProject', recursive=True)")
```

---

## 6. STANDARD WORKFLOW PATTERNS

### Pattern A — Complete Blueprint Build Sequence
```
1. exec_python → create_asset               (create in custom folder if needed)
2. get_blueprint_variables                  (see what variables already exist)
3. add_blueprint_variable                   (add needed variables)
4. get_blueprint_graphs                     (confirm graph names)
5. add_blueprint_event_node                 (BeginPlay, Tick, etc.)
6. add_blueprint_function_node              (each function call)
7. get_blueprint_nodes                      ← GET ALL NODE IDs BEFORE CONNECTING
8. connect_blueprint_nodes                  (exec wires first, then data wires)
9. compile_blueprint
10. get_blueprint_nodes                     (verify all connections are correct)
```

### Pattern B — AIController Setup
```
1. exec_python → create AIController Blueprint in correct folder
2. add_blueprint_event_node(event_name="ReceiveBeginPlay")
3. add_blueprint_function_node(function_name="RunBehaviorTree")
4. get_blueprint_nodes → connect BeginPlay.then → RunBehaviorTree.execute
5. set_node_pin_value (BTAsset pin → path to BT asset)
6. compile_blueprint
7. set_blueprint_ai_controller on the Character Blueprint
```

### Pattern C — New Function With Typed I/O
```
1. add_blueprint_function_with_pins (creates function graph + typed entry/result nodes)
2. get_blueprint_nodes(graph_name="FunctionName") → get entry/result node IDs
3. add nodes inside the function graph using graph_name="FunctionName"
4. connect_blueprint_nodes
5. compile_blueprint
```

### Pattern D — Safe Actor Reference (ALWAYS use this)
```
GetPlayerCharacter
→ Cast To BP_MyCharacter
  → Cast Succeeded → As BP_MyCharacter → [use reference, store in variable]
  → Cast Failed   → [do nothing / return]
```

### Pattern E — Widget HUD Creation (In PlayerController BeginPlay)
```
Event BeginPlay
→ Create Widget (Class: WBP_HUD, Owning Player: self)
→ Store result in HUDRef variable
→ Add to Viewport
```

---

## 7. BLUEPRINT PARENT CLASS LOOKUP

| Blueprint Purpose | `parent_class` |
|---|---|
| Static props, triggers, managers | `Actor` |
| Simple controllable pawn | `Pawn` |
| Walking character (player or NPC) | `Character` |
| Player input + camera | `PlayerController` |
| AI decision making | `AIController` |
| Game rules (server authority) | `GameModeBase` |
| Persistent data across levels | `GameInstance` |
| Replicated match state | `GameStateBase` |
| Per-player persistent state | `PlayerState` |
| Disk save file | `SaveGame` |
| Reusable logic (no transform) | `ActorComponent` |
| Reusable with transform | `SceneComponent` |
| Global static utilities | `BlueprintFunctionLibrary` |
| Custom BT action | `BTTask_BlueprintBase` |
| Custom BT condition | `BTDecorator_BlueprintBase` |
| Custom BT periodic logic | `BTService_BlueprintBase` |

---

## 8. NAMING CONVENTIONS (MANDATORY)

| Prefix | Asset Type | Prefix | Asset Type |
|---|---|---|---|
| `BP_` | Blueprint Class | `WBP_` | Widget Blueprint |
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

Incorrectly named assets cannot be found by other Blueprints.

---

## 9. THIS PROJECT'S SPECIFIC SETUP

**Project Name:** [PROJECT_NAME]
**Engine Version:** [UE_VERSION — e.g. 5.6]
**Content Root:** [CONTENT_ROOT — e.g. /Game/MyProject/]
**Local Path (on developer's machine):** [FULL LOCAL PATH]

**Project folder structure:**
```
[PASTE YOUR /Game/ FOLDER HIERARCHY HERE]
```

**Assets already created:**
```
[LIST KEY EXISTING ASSETS, OR: "None yet — starting fresh"]
```

**First task for this session:**
```
[DESCRIBE EXACTLY WHAT YOU WANT THE AGENT TO DO]
```

---

## ✂️ END OF PROMPT ✂️
