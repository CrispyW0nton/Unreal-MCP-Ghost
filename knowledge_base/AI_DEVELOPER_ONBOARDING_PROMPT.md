# Unreal-MCP-Ghost — AI Developer Onboarding Prompt (V4)

> **V4 — 2026-04-16** | For a full session-startup prompt with V4 roadmap context, see `knowledge_base/v4/NEXT_DEVELOPER_PROMPT_V4.md`.
> Copy and paste the block below as your first message when starting a new AI developer session for any Unreal Engine 5 project using this plugin.
> Replace the [BRACKETED] placeholders in Section 9 with your project's specifics.

---

## ✂️ COPY FROM HERE ✂️

---

You are an AI developer working on an Unreal Engine 5 project using the **Unreal-MCP-Ghost** plugin. This plugin lets you control the UE5 Editor programmatically through the **Model Context Protocol (MCP)**. Read this entire prompt carefully before taking any action.

---

## 0. HOW YOU ARE CONNECTED (READ THIS FIRST)

You interact with Unreal Engine **exclusively through MCP tool calls** — the same tool-call interface you use for everything else. There is no shell, no CLI script to run, no raw TCP socket to manage. The MCP server handles all communication with UE5 on your behalf.

**You have 362 MCP tools available across 24 modules.** Call them directly by name, e.g.:

```
get_actors_in_level()
create_blueprint(name="BP_MyActor", parent_class="Actor")
compile_blueprint(blueprint_name="BP_MyActor")
save_blueprint(blueprint_name="BP_MyActor")
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

1. **Call MCP tools only.** You interact with UE5 exclusively through MCP tool calls. Do not attempt to run shell commands. All 362 tools are available directly.

2. **Never invent a tool name.** If unsure whether a tool exists, check Section 5. Use `exec_python` as a fallback for anything not covered by a dedicated tool.

3. **Never guess a parameter name.** Wrong parameter names silently fail with no error.

4. **Always get node IDs before connecting nodes.** After adding nodes, call `get_blueprint_nodes` to retrieve actual GUIDs, then use those in `connect_blueprint_nodes`. Never hardcode GUIDs.

5. **Always compile AND save after node changes.** After any sequence of node additions and connections, call `compile_blueprint` followed by `save_blueprint`. An uncompiled or unsaved Blueprint is silently broken at runtime or lost on editor restart.

6. **Use `exec_python` for assets in custom folders.** The `create_blueprint` tool hardcodes `/Game/Blueprints/`. For all project-specific paths, use `exec_python` with `AssetToolsHelpers.get_asset_tools()`.

7. **Multiply per-frame values by Delta Seconds.** Any value applied on Event Tick MUST be multiplied by DeltaSeconds. Skipping this breaks the game at non-60fps framerates.

8. **Always call SpawnDefaultController for runtime-spawned AI.** Any AI Pawn/Character spawned at runtime via Spawn Actor from Class needs: `→ Return Value → SpawnDefaultController`.

9. **Always check validity before using references.** After any Cast or Get, wire the Cast Failed / invalid path to a stop node. Never silently continue on null.

10. **Stop and report missing assets.** If an asset that should exist doesn't, stop and tell the user exactly which asset is missing. Do NOT invent substitute paths.

11. **Use asset names, NOT full paths, for name-based commands.**

12. **ALWAYS query the knowledge base before implementing any system.** The knowledge base contains authoritative parameter names, patterns, and gotchas sourced from 4 UE5 textbooks. Never implement from memory alone.
    - Before AI/BT work    → `get_knowledge_base("ai")`
    - Before animation     → `get_knowledge_base("animation")`
    - Before UI/HUD        → `get_knowledge_base("ui")`
    - Before gameplay      → `get_knowledge_base("gameplay")`
    - Before materials     → `get_knowledge_base("materials")`
    - Before input system  → `get_knowledge_base("input")`
    - Before data/structs  → `get_knowledge_base("data")`
    - Before communication → `get_knowledge_base("communication")`
    - Unknown topic?       → `list_knowledge_base_topics()` then `search_knowledge_base("your term")`

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
| `compile_blueprint` | using it alone to save | always follow with `save_blueprint` |

---

## 4. COMPLETE TOOL REFERENCE (362 tools across 24 modules)

> **All 362 tools are documented below.** Every tool is listed with its exact parameter names — use them verbatim. Wrong parameter names fail silently.
> For V4 Phase 2 graph-scripting tool specs (`bp_add_node`, `bp_connect_pins`, `bp_compile`, etc.), see `knowledge_base/v4/GRAPH_SCRIPTING_SPEC_V4.md`.

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
| `focus_viewport` | `location`, `distance` |

### Blueprint Class Tools
| Tool | Key Parameters |
|---|---|
| `create_blueprint` | `name`, `parent_class`, `[path]` — defaults to `/Game/Blueprints/` |
| `compile_blueprint` | `blueprint_name` — marks dirty only; MUST be followed by `save_blueprint` |
| `save_blueprint` | `blueprint_name` — does the real compile (KismetEditorUtilities) + disk save |
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

> **compile_blueprint vs save_blueprint:**
> `compile_blueprint` calls `Blueprint->Modify()` in C++ — fast, marks the asset dirty, but does NOT write to disk and does NOT run the full bytecode compiler (UE5.6 crashes if the C++ plugin calls `FKismetEditorUtilities::CompileBlueprint` from an AsyncTask lambda).
> `save_blueprint` uses `exec_python` to call `unreal.KismetEditorUtilities.compile_blueprint()` + `save_asset()` on UE5's Python thread, which is safe. **Always call both.**

### Blueprint Introspection Tools
| Tool | Key Parameters |
|---|---|
| `get_blueprint_nodes` | `blueprint_name`, `graph_name` — use `"*"` for all graphs at once |
| `find_blueprint_nodes` | `blueprint_name`, `graph_name`, `[node_type]`, `[node_name]` |
| `get_blueprint_graphs` | `blueprint_name` |
| `get_node_by_id` | `blueprint_name`, `graph_name`, `node_id` |
| `get_blueprint_variables` | `blueprint_name`, `[category]` — lists all member variables with types/defaults |
| `get_blueprint_functions` | `blueprint_name` — lists all function graphs with I/O pins |
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
| `add_blueprint_function_node` | `blueprint_name`, `graph_name`, `function_name`, `node_position`, `[target]` (class name, e.g. `"KismetMathLibrary"`) |
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
| `add_blueprint_get_self_component_reference` | `blueprint_name`, `component_name`, `graph_name`, `node_position` |
| `add_blueprint_input_action_node` | `blueprint_name`, `action_name`, `graph_name`, `node_position` |
| `add_blueprint_enhanced_input_action_node` | `blueprint_name`, `graph_name`, `action_asset` (FULL PATH), `node_position` |
| `add_blueprint_comment_node` | `blueprint_name`, `graph_name`, `comment_text`, `node_position`, `[size]` |
| `add_event_dispatcher` | `blueprint_name`, `dispatcher_name` |
| `add_custom_function` | `blueprint_name`, `function_name` |
| `add_timeline_node` | `blueprint_name`, `graph_name`, `timeline_name`, `node_position` |
| `add_delay_node` | `blueprint_name`, `[duration]`, `node_position` |
| `add_branch_node` | `blueprint_name`, `[node_position]` — If/Else branch |
| `add_sequence_node` | `blueprint_name`, `[node_position]` — execute outputs in order |
| `add_flipflop_node` | `blueprint_name`, `[node_position]` — alternates between A and B outputs |
| `add_do_once_node` | `blueprint_name`, `[node_position]` — executes only the first time |
| `add_do_n_node` | `blueprint_name`, `[n]`, `[node_position]` — executes exactly N times |
| `add_gate_node` | `blueprint_name`, `[node_position]` — open/close gate for exec flow |
| `add_while_loop_node` | `blueprint_name`, `[node_position]` — loop while condition is true |
| `add_for_each_loop_node` | `blueprint_name`, `[with_break]`, `[node_position]` — iterates over an Array |
| `add_multigate_node` | `blueprint_name`, `[node_position]` — routes exec to one of N outputs in sequence |
| `add_select_node` | `blueprint_name`, `[index_type]`, `[option_type]`, `[num_options]`, `[node_position]` |
| `add_reroute_node` | `blueprint_name`, `[node_position]` — wire routing dot node |
| `add_comment_box` | `blueprint_name`, `comment_text`, `[position]`, `[size]`, `[color]` — documentation comment |
| `add_macro_node` | `blueprint_name`, `macro_name`, `[node_position]` — call a macro by name |
| `add_custom_macro` | `blueprint_name`, `macro_name`, `[inputs]`, `[outputs]` — define a new Macro |
| `add_construct_object_node` | `blueprint_name`, `object_class`, `[node_position]` — Construct Object from Class |
| `add_spawn_actor_node` | `blueprint_name`, `actor_class`, `[node_position]` — Spawn Actor from Class |
| `add_get_variable_node` | `blueprint_name`, `variable_name`, `[node_position]` — Get a variable's value |
| `add_set_variable_node` | `blueprint_name`, `variable_name`, `[node_position]` — Set a variable's value |
| `add_switch_on_int_node` | `blueprint_name`, `[node_position]` |
| `add_switch_on_string_node` | `blueprint_name`, `[node_position]` |
| `add_switch_on_enum_node` | `blueprint_name`, `enum_type`, `[node_position]` |
| `add_format_text_node` | `blueprint_name`, `[template]`, `[node_position]` — Format Text with `{ParameterName}` slots |
| `add_append_string_node` | `blueprint_name`, `[node_position]` — concatenate strings |
| `add_math_expression_node` | `blueprint_name`, `expression`, `[node_position]` — expression string like `"A + B * C"` |
| `add_print_string_node` | `blueprint_name`, `[message]`, `node_position` |
| `add_print_text_node` | `blueprint_name`, `[message]`, `node_position` |
| `add_get_delta_seconds_node` | `blueprint_name` |
| `add_get_player_character_node` | `blueprint_name`, `node_position` |
| `add_get_player_controller_node` | `blueprint_name`, `node_position` |
| `add_get_game_mode_node` | `blueprint_name`, `node_position` |
| `add_get_game_instance_node` | `blueprint_name`, `node_position` |
| `add_get_owner_node` | `blueprint_name`, `[cast_to_class]`, `[node_position]` — GetOwner for component Blueprints |
| `add_get_all_actors_of_class_node` | `blueprint_name`, `actor_class`, `node_position` |
| `add_get_actor_of_class_node` | `blueprint_name`, `actor_class`, `node_position` |
| `add_destroy_actor_node` | `blueprint_name`, `node_position` |
| `add_spawn_actor_from_class_node` | `blueprint_name`, `actor_class`, `node_position` |
| `add_is_valid_node` | `blueprint_name`, `node_position` |
| `add_is_valid_class_node` | `blueprint_name`, `[node_position]` — check if a class reference is valid |
| `add_validated_get_node` | `blueprint_name`, `variable_name`, `node_position` |
| `add_math_node` | `blueprint_name`, `operation` (e.g. `"Add_FloatFloat"`, `"VSize"`), `node_position` |
| `add_abs_node` | `blueprint_name`, `[operand_type]`, `[node_position]` — absolute value |
| `add_min_max_node` | `blueprint_name`, `[operation]` (`"Min"`/`"Max"`), `[operand_type]`, `[node_position]` |
| `add_nearly_equal_float_node` | `blueprint_name`, `[node_position]` — float equality with tolerance |
| `add_vector_length_node` | `blueprint_name`, `[node_position]` — VSize / vector magnitude |
| `add_get_unit_direction_vector_node` | `blueprint_name`, `[node_position]` — normalized direction vector from A to B |
| `add_cast_node` | `blueprint_name`, `target_class`, `node_position` |

### Node Editing Tools
| Tool | Key Parameters |
|---|---|
| `connect_blueprint_nodes` | `blueprint_name`, `graph_name`, `source_node_id`, `target_node_id`, `source_pin`, `target_pin` |
| `disconnect_blueprint_nodes` | `blueprint_name`, `graph_name`, `source_node_id`, `target_node_id`, `source_pin`, `target_pin` |
| `delete_blueprint_node` | `blueprint_name`, `graph_name`, `node_id` |
| `set_node_pin_value` | `blueprint_name`, `graph_name`, `node_id`, `pin_name`, `value` |
| `move_blueprint_node` | `blueprint_name`, `graph_name`, `node_id`, `node_position` |

### Knowledge Base Tools
| Tool | Key Parameters |
|---|---|
| `list_knowledge_base_topics` | _(none)_ — returns all available topics |
| `get_knowledge_base` | `topic` — full extract for a topic (ai, animation, ui, gameplay, materials, input, data, communication) |
| `search_knowledge_base` | `query` — free-text search across all knowledge base files |

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
| `add_on_see_pawn_event` | `blueprint_name`, `[graph_name]`, `node_position` |
| `add_on_hear_noise_event` | `blueprint_name`, `[graph_name]`, `node_position` |
| `add_report_noise_event_node` | `blueprint_name`, `node_position` |
| `add_get_blackboard_value_node` | `blueprint_name`, `key_name`, `value_type` |
| `set_blackboard_value` | `blueprint_name`, `key_name`, `value` |
| `add_clear_blackboard_value_node` | `blueprint_name`, `key_name` |
| `add_bt_blackboard_decorator` | `behavior_tree_name`, `sequence_name`, `blackboard_key`, `[observer_aborts]`, `[node_name]` |
| `add_finish_execute_node` | `blueprint_name`, `success` |
| `create_bt_attack_task` | `[name]`, `[damage_variable]`, `[default_damage]`, `[target_key_variable]`, `[path]` — BT attack task Blueprint |
| `create_bt_wander_task` | `[name]`, `[wander_radius]`, `[path]` — BT random wander task Blueprint |

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
| `add_anim_blueprint_variable` | `anim_blueprint_name`, `variable_name`, `variable_type`, `[default_value]` — add variable to Anim BP |
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

### Map / Set / Collection Node Tools
| Tool | Key Parameters |
|---|---|
| `add_set_contains_node` | `blueprint_name`, `set_variable`, `[node_position]` — check if element is in Set |
| `add_set_union_node` | `blueprint_name`, `[node_position]` — combine two Sets (removes duplicates) |
| `add_set_intersection_node` | `blueprint_name`, `[node_position]` — elements common to both Sets |
| `add_set_difference_node` | `blueprint_name`, `[node_position]` — elements in first Set but not second |
| `add_set_to_array_node` | `blueprint_name`, `set_variable`, `[node_position]` — convert Set to Array |
| `add_map_find_node` | `blueprint_name`, `map_variable`, `[node_position]` — get Map value by key |
| `add_map_contains_node` | `blueprint_name`, `map_variable`, `[node_position]` — check if key exists in Map |
| `add_map_keys_node` | `blueprint_name`, `map_variable`, `[node_position]` — copy all Map keys to Array |
| `add_map_values_node` | `blueprint_name`, `map_variable`, `[node_position]` — copy all Map values to Array |
| `add_random_array_item_node` | `blueprint_name`, `array_variable`, `[node_position]` — pick a random Array element |
| `add_make_array_node` | `blueprint_name`, `[node_position]` — construct an Array literal |
| `add_make_map_node` | `blueprint_name`, `[node_position]` — construct a Map literal |
| `add_make_set_node` | `blueprint_name`, `[node_position]` — construct a Set literal |

### Input Tools
| Tool | Key Parameters |
|---|---|
| `create_enhanced_input_action` | `name`, `[path]` |
| `create_input_mapping_context` | `name`, `[path]` |
| `add_input_mapping` | `context_name`, `action_name`, `key` |
| `create_input_mapping` | `action_name`, `key`, `[input_type]` — legacy project settings input binding |

### UMG / Widget Tools
| Tool | Key Parameters |
|---|---|
| `create_umg_widget_blueprint` | `name`, `[path]` |
| `create_hud_widget` | `widget_name`, `[health_bar]`, `[stamina_bar]`, `[ammo_counter]` |
| `create_hud_blueprint` | `name` — creates a HUD Blueprint (GameHUD class, not a Widget) |
| `add_text_block_to_widget` | `widget_name`, `text_block_name`, `text`, `position` |
| `add_button_to_widget` | `widget_name`, `button_name`, `position` |
| `add_progress_bar_to_widget` | `widget_name`, `progress_bar_name`, `[position]`, `[size]`, `[fill_color]`, `[background_color]`, `[percent]` |
| `add_image_to_widget` | `widget_name`, `image_name`, `[texture_path]`, `[position]`, `[size]`, `[color]` |
| `add_named_slot_to_widget` | `widget_name`, `slot_name`, `[position]`, `[size]` — Named Slot placeholder |
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
| `create_projectile_blueprint` | `name`, `[parent_class]`, `[path]` |
| `create_pickup_blueprint` | `name`, `[parent_class]`, `[path]` |
| `create_vr_pawn_blueprint` | `name` |
| `make_actor_vr_grabbable` | `blueprint_name` |
| `set_game_mode_for_level` | `game_mode_name` ⚠️ asset name only |
| `add_overlap_event` | `blueprint_name`, `component_name` |
| `add_hit_event` | `blueprint_name`, `component_name` |
| `add_player_death_event` | `blueprint_name`, `lose_widget_name` |
| `add_enable_disable_input_node` | `blueprint_name`, `[enable]`, `node_position` |
| `add_set_input_mode_node` | `blueprint_name`, `input_mode`, `node_position` |

### Material / VFX / Sequencer Tools
| Tool | Key Parameters |
|---|---|
| `create_material` | `name`, `[base_color]`, `[metallic]`, `[roughness]` |
| `create_dynamic_material_instance` | `blueprint_name`, `component_name`, `source_material_path` |
| `set_material_on_actor` | `actor_name`, `material_path` |
| `set_material_instance_parameter` | `material_instance_path`, `parameter_name`, `parameter_type`, `value` |
| `add_set_material_node` | `blueprint_name`, `component_name`, `material_path`, `[event_name]`, `[node_position]` — Set Material at runtime |
| `add_set_vector_parameter_value_node` | `blueprint_name`, `dynamic_material_variable`, `parameter_name`, `[color_value]`, `[node_position]` — change material color |
| `add_set_scalar_parameter_value_node` | `blueprint_name`, `dynamic_material_variable`, `parameter_name`, `[scalar_value]`, `[node_position]` — change material float param |
| `add_play_sound_node` | `blueprint_name`, `[sound_asset]`, `[node_position]` — Play Sound at Location |
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
| `add_multi_line_trace_by_channel_node` | `blueprint_name`, `[trace_channel]`, `[draw_debug]`, `[node_position]` — returns all hits |
| `add_multi_line_trace_for_objects_node` | `blueprint_name`, `[object_types]`, `[node_position]` — multi-hit by object type |
| `add_sphere_trace_by_channel_node` | `blueprint_name`, `[radius]`, `[trace_channel]` |
| `add_capsule_trace_by_channel_node` | `blueprint_name`, `[radius]`, `[half_height]` |
| `add_box_trace_by_channel_node` | `blueprint_name`, `[half_size]`, `[trace_channel]` |
| `add_break_hit_result_node` | `blueprint_name` |
| `add_apply_damage_node` | `blueprint_name`, `[damage_amount]` |
| `add_apply_point_damage_node` | `blueprint_name`, `[damage_amount]` |
| `add_set_collision_enabled_node` | `blueprint_name`, `component_name`, `[collision_enabled]`, `[node_position]` |
| `add_set_collision_profile_node` | `blueprint_name`, `component_name`, `[profile_name]`, `[node_position]` — e.g. `"BlockAll"`, `"OverlapAll"` |
| `add_set_generate_overlap_events_node` | `blueprint_name`, `component_name`, `[generate_overlap]`, `[node_position]` |
| `add_get_actor_location_node` | `blueprint_name` |
| `add_set_actor_location_node` | `blueprint_name` |
| `add_actor_world_offset_node` | `blueprint_name` |
| `add_get_actor_rotation_node` | `blueprint_name` — uses `K2_GetActorRotation` internally |
| `add_set_actor_rotation_node` | `blueprint_name` — uses `K2_SetActorRotation` internally |
| `add_actor_world_rotation_node` | `blueprint_name` |
| `add_get_actor_scale_node` | `blueprint_name` |
| `add_set_actor_scale_node` | `blueprint_name` |
| `add_get_relative_location_node` | `blueprint_name`, `component_name` |
| `add_set_relative_location_node` | `blueprint_name`, `component_name` |
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
| `add_line_trace_node` | `blueprint_name`, `[trace_type]`, `node_position` — generic trace |
| `add_line_trace_for_objects_node` | `blueprint_name`, `[object_types]`, `node_position` |
| `add_sphere_trace_for_objects_node` | `blueprint_name`, `[radius]`, `[object_types]`, `node_position` |
| `add_predict_projectile_path_node` | `blueprint_name`, `node_position` |
| `add_get_actor_scale_node` | `blueprint_name` |
| `build_trace_interaction_blueprint` | `blueprint_name`, `[trace_range]`, `[input_key]` |

### Save Game Tools
| Tool | Key Parameters |
|---|---|
| `create_savegame_blueprint` | `name`, `[variables]` |
| `setup_full_save_load_system` | `character_blueprint`, `save_blueprint_name` |
| `add_save_game_to_slot_node` | `blueprint_name`, `[save_game_variable]`, `[slot_name_variable]` |
| `add_load_game_from_slot_node` | `blueprint_name`, `[slot_name_variable]`, `[save_game_class]` |
| `add_create_save_game_object_node` | `blueprint_name`, `save_game_class`, `node_position` |
| `add_does_save_game_exist_node` | `blueprint_name`, `node_position` |
| `add_delete_save_game_in_slot_node` | `blueprint_name`, `node_position` |
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
| `unbind_event_from_dispatcher` | `blueprint_name`, `dispatcher_name`, `node_position` |
| `add_call_interface_function_node` | `blueprint_name`, `interface_name`, `function_name` |
| `add_direct_blueprint_reference` | `blueprint_name`, `target_blueprint`, `variable_name` |
| `add_interface_function_node` | `blueprint_name`, `interface_name`, `function_name`, `node_position` |

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
| `create_align_actors_utility` | `[name]`, `[folder_path]` — Editor Utility to align actors on X axis |
| `create_enemy_spawner_blueprint` | `name`, `[enemy_class]`, `[wave_size]` |
| `create_random_spawner_blueprint` | `name`, `[spawn_class]` |
| `add_spline_component` | `blueprint_name`, `[component_name]`, `[node_position]` — add Spline component |
| `add_spline_mesh_component` | `blueprint_name`, `[component_name]`, `[static_mesh_path]` — add Spline Mesh component |
| `add_instanced_static_mesh_component` | `blueprint_name`, `[component_name]`, `[static_mesh_path]`, `[attach_to_root]` |
| `add_instanced_mesh_add_instance_node` | `blueprint_name`, `[instanced_mesh_variable]`, `[node_position]` — AddInstance on ISM component |
| `add_construction_script_for_loop` | `blueprint_name`, `[first_index]`, `[last_index_variable]`, `[nested]`, `[node_position]` — For Loop in Construction Script |
| `add_get_spline_length_node` | `blueprint_name`, `[spline_component_variable]`, `[node_position]` |
| `add_get_location_at_distance_along_spline_node` | `blueprint_name`, `[spline_component_variable]`, `[coordinate_space]`, `[node_position]` |
| `add_get_rotation_at_distance_along_spline_node` | `blueprint_name`, `[spline_component_variable]`, `[coordinate_space]`, `[node_position]` |
| `place_navmesh_bounds_volume` | `[location]`, `[scale]` — place NavMeshBoundsVolume in the level |
| `add_set_timer_by_event_node` | `blueprint_name`, `[time_seconds]`, `[looping]`, `[custom_event_name]` |
| `add_set_timer_by_function_name_node` | `blueprint_name`, `[function_name]`, `[time_seconds]` |
| `add_clear_timer_node` | `blueprint_name` — uses `K2_ClearAndInvalidateTimerHandle` internally |
| `add_construction_script_node` | `blueprint_name`, `node_position` |
| `add_teleport_node` | `blueprint_name`, `node_position` |
| `add_set_view_target_with_blend_node` | `blueprint_name`, `node_position` |
| `add_attach_actor_to_component_node` | `blueprint_name`, `node_position` |

### VR Tools
| Tool | Key Parameters |
|---|---|
| `create_vr_pawn_blueprint` | `name` |
| `make_actor_vr_grabbable` | `blueprint_name` |
| `create_grab_component` | `name`, `[parent_class]` |
| `add_motion_controller_component` | `blueprint_name`, `[hand]` |
| `add_widget_interaction_component` | `blueprint_name`, `node_position` |
| `add_vr_input_action_node` | `blueprint_name`, `action_name`, `node_position` |
| `add_teleport_system_to_pawn` | `blueprint_name` |

### Variant / Level Tools
| Tool | Key Parameters |
|---|---|
| `create_level_variant_sets` | `name`, `[path]` |
| `create_product_configurator_blueprint` | `name` |
| `add_activate_variant_node` | `blueprint_name`, `variant_name`, `node_position` |
| `add_activate_variant_set_node` | `blueprint_name`, `variant_set_name`, `node_position` |
| `add_get_variant_sets_node` | `blueprint_name`, `node_position` |
| `add_get_all_variants_node` | `blueprint_name`, `node_position` |
| `add_variant_to_level_variant_sets` | `level_variant_sets_name`, `variant_set_name`, `variant_name` |

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
a = at.create_asset('BP_MyCharacter', '/Game/[YourProject]/Blueprints/Player', unreal.Blueprint, f)
print('OK' if a else 'FAIL')
""")
```

```python
# Widget Blueprint
exec_python(code="""
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()
f = unreal.WidgetBlueprintFactory()
a = at.create_asset('WBP_HUD', '/Game/[YourProject]/Widgets', unreal.WidgetBlueprint, f)
print('OK' if a else 'FAIL')
""")
```

```python
# Behavior Tree
exec_python(code="""
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()
a = at.create_asset('BT_Enemy', '/Game/[YourProject]/AI', unreal.BehaviorTree, unreal.BehaviorTreeFactory())
print('OK' if a else 'FAIL')
""")
```

```python
# Create folder
exec_python(code="import unreal; unreal.EditorAssetLibrary.make_directory('/Game/[YourProject]/Blueprints/Player')")
```

```python
# Check if asset exists
exec_python(code="""
import unreal
exists = unreal.EditorAssetLibrary.does_asset_exist('/Game/[YourProject]/Blueprints/BP_X')
print('EXISTS' if exists else 'MISSING')
""")
```

```python
# Save all assets under a folder
exec_python(code="import unreal; unreal.EditorAssetLibrary.save_directory('/Game/[YourProject]', recursive=True)")
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
9. compile_blueprint                        (marks dirty)
10. save_blueprint                          (real compile + disk save)  ← ALWAYS REQUIRED
11. get_blueprint_nodes                     (verify all connections are correct)
```

### Pattern B — AIController Setup
```
1. exec_python → create AIController Blueprint in correct folder
2. add_blueprint_event_node(event_name="ReceiveBeginPlay")
3. add_blueprint_function_node(function_name="RunBehaviorTree")
4. get_blueprint_nodes → connect BeginPlay.then → RunBehaviorTree.execute
5. set_node_pin_value (BTAsset pin → path to BT asset)
6. compile_blueprint + save_blueprint       ← BOTH required
7. set_blueprint_ai_controller on the Character Blueprint
```

### Pattern C — New Function With Typed I/O
```
1. add_blueprint_function_with_pins (creates function graph + typed entry/result nodes)
2. get_blueprint_nodes(graph_name="FunctionName") → get entry/result node IDs
3. add nodes inside the function graph using graph_name="FunctionName"
4. connect_blueprint_nodes
5. compile_blueprint + save_blueprint       ← BOTH required
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
**Engine Version:** [UE_VERSION — query with: exec_python(code="import unreal; print(unreal.SystemLibrary.get_engine_version())")]
**Content Root:** [CONTENT_ROOT — e.g. /Game/MyProject/]
**Local Path (on developer's machine):** [FULL_LOCAL_PATH — e.g. C:\Users\Name\Documents\MyProject\]
**MCP Server URL:** [MCP_SERVER_URL — e.g. http://localhost:8000/sse or your Playit tunnel URL]

**Project folder structure:**
```
[PASTE YOUR /Game/ FOLDER HIERARCHY HERE, or leave as "Starting fresh"]
```

**Assets already created:**
```
[LIST KEY EXISTING ASSETS, or: "None yet — starting fresh"]

To discover existing assets, run:
exec_python(code="import unreal; a=unreal.EditorAssetLibrary.list_assets('/Game',recursive=True,include_folder=False); print(len(a),'total'); [print(x) for x in a if '/Game/[YourProject]' in x]")
```

**First task for this session:**
```
1. get_actors_in_level()                    → confirm connection
2. exec_python → engine version             → confirm UE version
3. exec_python → list project assets        → get current asset inventory
4. [DESCRIBE EXACTLY WHAT YOU WANT THE AGENT TO BUILD OR DO]
```

---

## ✂️ END OF PROMPT ✂️
