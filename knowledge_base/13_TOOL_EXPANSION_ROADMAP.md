# Tool Expansion Roadmap — New MCP Commands to Implement
> Based on learnings from all 4 books. Prioritized by impact on Dantooine project.
> For each new command: why it's needed + exact implementation spec.

---

## PRIORITY 1 — Critical Missing Commands

### 1. `add_blueprint_variable` ✅ IMPLEMENTED
**Status:** Live in plugin. See Section 8 of 12_MCP_TOOL_USAGE_GUIDE.md for full docs.

Supported `variable_type` values: `Boolean`, `Integer`, `Integer64`, `Float`, `Double`, `String`, `Name`, `Text`, `Vector`, `Rotator`, `Transform`, `Object/<ClassPath>`

Params: `blueprint_name` ✅, `variable_name` ✅, `variable_type` ✅, `is_exposed` ❌, `default_value` ❌

---

### 2. `add_blueprint_function_with_pins` ✅ IMPLEMENTED
**Status:** Live as `add_blueprint_function_with_pins`. Supports typed inputs/outputs in one call.

Returns `entry_node_id` and `result_node_id` so you can immediately add nodes inside the function graph.

See Section 12 of 12_MCP_TOOL_USAGE_GUIDE.md.

---

### 3. `implement_blueprint_interface` ✅ IMPLEMENTED (name differs from roadmap)
**Status:** Live in plugin as `implement_blueprint_interface` (NOT `add_blueprint_interface_implementation`).

⚠️ **CRITICAL**: Parameter is `interface_name` (asset name only), NOT `interface_path`.

```bash
python3 sandbox_ue5cli.py implement_blueprint_interface '{
  "blueprint_name": "BP_LightsaberWorkbench",
  "interface_name": "BPI_Interactable"
}'
```

---

### 4. `set_blueprint_parent_class` ✅ IMPLEMENTED
**Status:** Live. Accepts Blueprint asset name OR C++ class name as `new_parent_class`.

```bash
python3 sandbox_ue5cli.py set_blueprint_parent_class '{
  "blueprint_name":  "BP_RoamingNPC_StudentA",
  "new_parent_class": "BP_RoamingNPC_Base"
}'
```

---

### 5. `add_input_action_node`
**Why needed:** Enhanced Input action bindings need special nodes, different from legacy `add_blueprint_input_action_node`.
**Impact:** Player input system (IA_Attack, IA_Block, IA_Interact all need binding)

**Proposed spec:**
```bash
python3 sandbox_ue5cli.py add_input_action_node '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "graph_name": "EventGraph",
  "input_action_path": "/Game/Dantooine/Data/Input/IA_Attack",
  "trigger_event": "Started",
  "node_position": {"x": 0, "y": 400}
}'
```
Trigger events: `Started`, `Triggered`, `Completed`, `Canceled`, `Ongoing`

---

## PRIORITY 2 — Important Missing Commands

### 6. `add_blackboard_key` ✅ IMPLEMENTED (via `create_blackboard` keys[] param)
**Status:** No standalone `add_blackboard_key` command exists, but `create_blackboard` accepts a `keys` array.

```bash
python3 sandbox_ue5cli.py create_blackboard '{
  "name": "BB_RoamingNPC",
  "path": "/Game/Dantooine/AI/Blackboard",
  "keys": [
    {"name": "PatrolLocation", "type": "Vector"},
    {"name": "IsTalking",      "type": "Bool"}
  ]
}'
```
> ⚠️ Keys can ONLY be set at creation time. To add more keys to an existing blackboard, recreate it.

---

### 7. `set_behavior_tree_blackboard` ✅ IMPLEMENTED
**Status:** Live. Uses asset names (not paths).

```bash
python3 sandbox_ue5cli.py set_behavior_tree_blackboard '{
  "behavior_tree_name": "BT_RoamingNPC",
  "blackboard_name":    "BB_RoamingNPC"
}'
```

---

### 8. `add_niagara_component` ✅ IMPLEMENTED
**Status:** Live. Requires Niagara plugin enabled in project.

```bash
python3 sandbox_ue5cli.py add_niagara_component '{
  "blueprint_name":      "BP_LightsaberWorkbench",
  "component_name":      "SparksEffect",
  "niagara_system_path": "/Game/Dantooine/Art/FX/NS_WorkbenchSparks"
}'
```

---

### 9. `create_data_table` ✅ IMPLEMENTED
**Status:** Live in plugin. See Section 9 of 12_MCP_TOOL_USAGE_GUIDE.md.

```bash
python3 sandbox_ue5cli.py create_data_table '{
  "name": "DT_DialogueLines",
  "path": "/Game/Dantooine/Data/DataTables",
  "row_struct": "/Game/Dantooine/Data/Structs/ST_DialogueLine"
}'
```
> ⚠️ **PARAM FIX**: Parameter is `row_struct`, NOT `row_struct_path`.

---

### 10. `add_anim_notify` ✅ IMPLEMENTED
**Status:** Live. Supports both `notify` and `notify_state` types.

```bash
python3 sandbox_ue5cli.py add_anim_notify '{
  "animation_path": "/Game/Dantooine/Animation/Montages/AM_LightsaberAttack",
  "notify_name":    "HitDetection",
  "time":           0.45
}'
```

---

## PRIORITY 3 — Quality of Life Commands

### 11. `get_blueprint_variables` ✅ IMPLEMENTED
**Status:** Live. Returns full metadata including type, sub_type, default, category, exposure/replication flags.

```bash
python3 sandbox_ue5cli.py get_blueprint_variables '{"blueprint_name": "BP_PlayerJediCharacter"}'
```

---

### 12. `get_blueprint_functions` ✅ IMPLEMENTED
**Status:** Live. Returns function and macro graphs with input/output pin info.

```bash
python3 sandbox_ue5cli.py get_blueprint_functions '{"blueprint_name": "BP_PlayerJediCharacter"}'
```

---

### 13. `add_blueprint_call_interface_function`
**Why needed:** Cannot add Interface function call nodes via MCP.

**Proposed spec:**
```bash
python3 sandbox_ue5cli.py add_blueprint_call_interface_function '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "graph_name": "EventGraph",
  "interface_path": "/Game/Dantooine/Interfaces/BPI_Interactable",
  "function_name": "Interact",
  "node_position": {"x": 400, "y": 0}
}'
```

---

### 14. `add_blueprint_for_loop_with_break_node`
**Why needed:** For Loop with Break not yet exposed.

```bash
python3 sandbox_ue5cli.py add_blueprint_for_loop_with_break_node '{
  "blueprint_name": "BP_X",
  "graph_name": "EventGraph",
  "node_position": {"x": 200, "y": 0}
}'
```

---

### 15. `set_sequencer_track` ✅ IMPLEMENTED
**Status:** Live. Supports Transform track with location/rotation/scale keyframes.

```bash
python3 sandbox_ue5cli.py set_sequencer_track '{
  "sequence_path": "/Game/Dantooine/Sequences/LightsaberBuild/LS_LightsaberBuild",
  "actor_name":    "BP_LightsaberWorkbench_0",
  "track_type":    "Transform",
  "keyframes": [
    {"time": 0.0, "location": {"x":0,"y":0,"z":0}},
    {"time": 2.0, "location": {"x":0,"y":0,"z":100}, "rotation": {"pitch":0,"yaw":180,"roll":0}}
  ]
}'
```

---

### 16. `copy_blueprint_component`
**Why needed:** Can't duplicate components from one BP to another.

---

### 17. `set_material_instance_parameter` ✅ IMPLEMENTED
**Status:** Live. Supports scalar, vector (RGBA), and texture parameters.

```bash
python3 sandbox_ue5cli.py set_material_instance_parameter '{
  "material_instance_path": "/Game/Dantooine/Art/Materials/MI_LightsaberBlade",
  "parameter_name":         "EmissiveIntensity",
  "parameter_type":         "scalar",
  "value":                  "5.0"
}'
```

---

### 18. `add_spawn_niagara_at_location_node` ✅ IMPLEMENTED
**Status:** Live. Adds a `SpawnSystemAtLocation` call node to a Blueprint graph.

```bash
python3 sandbox_ue5cli.py add_spawn_niagara_at_location_node '{
  "blueprint_name":      "BP_LightsaberWorkbench",
  "graph_name":          "EventGraph",
  "niagara_system_path": "/Game/Dantooine/Art/FX/NS_WorkbenchSparks",
  "node_position":       {"x": 600, "y": 0}
}'
```

---

### 19. `import_sound_asset` ✅ IMPLEMENTED

**Why needed:** Import WAV/OGG/MP3 files from the UE5 host machine directly into the Content Browser as SoundWave assets, with optional SoundCue auto-creation.

**Implemented in:** `audio_tools.py` (registered in `unreal_mcp_server.py`)

**Actual usage:**
```python
# Via MCP tool call:
import_sound_asset(
    file_path="C:/Sounds/SFX_SaberSwing.wav",
    destination_path="/Game/Dantooine/Art/Audio/SFX/",
    auto_create_cue=True
)
# Returns: {"success": true, "asset_path": "/Game/Dantooine/Art/Audio/SFX/SFX_SaberSwing",
#            "asset_type": "SoundWave", "cue_path": "/Game/Dantooine/Art/Audio/SFX/SFX_SaberSwing_Cue"}
```

**For sandbox-side files** (from `audio_generation` / `DownloadFileWrapper`), use `import_sound_asset_from_sandbox` instead.

See `12_MCP_TOOL_USAGE_GUIDE.md` § AUDIO IMPORT TOOLS for full documentation.

---

### 20. `add_widget_binding`
**Why needed:** Widget bindings for health/score display require Python-level automation.

---

## Implementation Priority Summary

| Priority | Command | Status | Impact |
|---|---|---|---|
| 1 | `add_blueprint_variable` | ✅ DONE | Essential for every BP |
| 1 | `add_blueprint_function_with_pins` | ✅ DONE | Typed function creation |
| 1 | `implement_blueprint_interface` | ✅ DONE | Required for BPI_ pattern |
| 1 | `set_blueprint_parent_class` | ✅ DONE | Required for inheritance |
| 1 | `add_blueprint_enhanced_input_action_node` | ✅ DONE | Required for Enhanced Input |
| 2 | `add_blackboard_key` | ✅ via create_blackboard keys[] | Required for AI setup |
| 2 | `set_behavior_tree_blackboard` | ✅ DONE | Required for AI setup |
| 2 | `add_niagara_component` | ✅ DONE | VFX components in BPs |
| 2 | `create_data_table` | ✅ DONE | Required for dialogue system |
| 2 | `add_anim_notify` | ✅ DONE | Required for combat system |
| 3 | `get_blueprint_variables` | ✅ DONE | Inspection/debugging |
| 3 | `get_blueprint_functions` | ✅ DONE | Inspection/debugging |
| 3 | `add_blueprint_call_interface_function` | `add_interface_function_node` ✅ | Interface calling |
| 3 | `set_material_instance_parameter` | ✅ DONE | Visual customization |
| 3 | `add_spawn_niagara_at_location_node` | ✅ DONE | Runtime VFX |
| 3 | `set_sequencer_track` | ✅ DONE | Sequencer keyframes |

---

## Current Workarounds (via exec_python)

Use exec_python for commands not yet implemented as dedicated MCP commands:

### ✅ `add_blueprint_variable` — USE THE DIRECT COMMAND (no workaround needed)
```bash
python3 sandbox_ue5cli.py add_blueprint_variable '{"blueprint_name":"BP_PlayerJediCharacter","variable_name":"Health","variable_type":"Float","default_value":"100.0"}'
```

### ✅ `implement_blueprint_interface` — USE THE DIRECT COMMAND (no workaround needed)
```bash
python3 sandbox_ue5cli.py implement_blueprint_interface '{"blueprint_name":"BP_LightsaberWorkbench","interface_name":"BPI_Interactable"}'
```

### ❌ `set_blueprint_parent_class` — WORKAROUND via exec_python
```python
# NOTE: Reparenting via Python is unreliable. Best approach:
# 1. Create the BP with the correct parent from the start (BlueprintFactory.parent_class)
# 2. Or reparent manually in UE editor: right-click BP → Reparent Blueprint
import unreal
# Verify parent of a blueprint:
bp = unreal.load_object(None, "/Game/Dantooine/Blueprints/NPC/BP_RoamingNPC_StudentA")
if bp:
    print(bp.parent_class.get_name())
```

### ❌ `set_behavior_tree_blackboard` — WORKAROUND via exec_python
```python
import unreal
bt = unreal.load_object(None, "/Game/Dantooine/AI/BehaviorTrees/BT_RoamingNPC")
bb = unreal.load_object(None, "/Game/Dantooine/AI/Blackboard/BB_RoamingNPC")
if bt and bb:
    bt.set_editor_property("blackboard_asset", bb)
    unreal.EditorAssetLibrary.save_asset(bt.get_path_name())
    print("BB assigned to BT")
```

### ❌ `get_blueprint_variables` — WORKAROUND via exec_python
```python
import unreal
bp = unreal.load_object(None, "/Game/Dantooine/Blueprints/Player/BP_PlayerJediCharacter")
for v in bp.new_variables:
    print(v.var_name, v.var_type.pc_object.get_name() if v.var_type.pc_object else v.var_type.pin_category)
```

---

---

## ASSET IMPORT PIPELINE — STATUS ✅ FULLY IMPLEMENTED (2026-04-16)

### Category C — Single-Asset Import (asset_import_tools.py) ✅
- `import_texture` ✅ — PNG/JPG/TGA/EXR/HDR/BMP → Texture2D with auto compression detection
- `import_static_mesh` ✅ — FBX/OBJ/glTF/GLB → StaticMesh with full FBX options
- `import_skeletal_mesh` ✅ — FBX → SkeletalMesh with skeleton reuse + morph targets

### Category B — Folder/Batch Import (folder_import_tools.py) ✅
- `scan_export_folder` ✅ — local scan, categorised manifest, no UE5 connection needed
- `batch_import_folder` ✅ — batch import all assets, preserves subfolder structure
- `import_folder_as_character` ✅ — full character import (mesh + textures + animations)

### Category A — GhostRigger IPC Bridge (ghostrigger_tools.py) ✅
- `ghostrigger_health` ✅ — GET /api/health
- `ghostrigger_ping` ✅ — POST /api/ping
- `ghostrigger_open_model` ✅ — POST /api/open_mdl
- `ghostrigger_open_creature` ✅ — POST /api/open_utc
- `ghostrigger_list_mcp_tools` ✅ — GET /mcp/tools/list (68 KotorMCP tools)
- `ghostrigger_call_mcp_tool` ✅ — POST /mcp/tools/call
- `ghostrigger_list_resources` ✅ — GET /mcp/resources/list
- `ghostrigger_read_resource` ✅ — POST /mcp/resources/read
- `ghostrigger_export_model` ✅ — MDL → FBX via GhostRigger tool call
- `ghostrigger_import_to_ue5` ✅ — full KotOR→FBX→UE5 pipeline

**Total new tools: 16 (3 Category C + 3 Category B + 10 Category A)**
**New total: 362 MCP tools**

---

## SCRIPTING SUPREMACY SPRINT — STATUS ✅ PHASE 0+1+2 COMPLETE (2026-04-16)

### Phase 0 — PR #15 Stabilization ✅
- Scope verified: Categories A/B/C all confirmed present
- Test suite: 48 tests, all passing (tests/test_import_tools.py)
- Shared result schema: `{success, stage, message, inputs, outputs, warnings, errors, log_tail}`
- Tool/module count reconciled: **362 tools / 24 modules**

### Phase 1 — Safe Execution Substrate ✅ (exec_substrate.py)
New tools (3):
- `ue_exec_safe` — structured try/except wrapper for any Python snippet
- `ue_exec_transact` — ScopedEditorTransaction wrapper (one undo step)
- `ue_exec_progress` — ScopedSlowTask wrapper (progress dialog + cancel button)

Internal helpers (not MCP tools):
- `exec_python_transactional(user_code, transaction_name)` — callable by other modules
- `exec_python_with_progress(user_code, task_name, total_work)` — callable by other modules
- `exec_python_structured(user_code, stage_name)` — called by asset_import_tools + folder_import_tools
- `make_result(...)` — builds a normalized StructuredResult dict

**Integration:** `asset_import_tools.py` and `folder_import_tools.py` now use
`exec_python_structured` instead of raw `exec_python` + `_parse_ue_json`.
All UE5 code snippets in these modules now populate `_result`, `_warnings`,
`_errors` and are wrapped in try/except by the substrate.

### Phase 2 — Reflection & Diagnostics ✅ (reflection_tools.py)
New tools (8):
- `ue_reflect_class(class_name)` — parent chain, flags, module
- `ue_list_uclass_properties(class_name, include_inherited)` — editor properties
- `ue_list_uclass_methods(class_name, filter_prefix)` — callable methods
- `ue_describe_asset(asset_path)` — full asset metadata
- `ue_find_assets_by_class(class_name, search_path, limit)` — content browser search
- `ue_list_editor_selection()` — current viewport selection
- `get_recent_output_log(lines, filter_category)` — Output Log tail
- `ue_summarize_operation_effects(search_path)` — asset count by class (snapshot)

New MCP Resources (5):
- `unreal://knowledge/python-best-practices`
- `unreal://knowledge/import-recipes`
- `unreal://knowledge/blueprint-recipes`
- `unreal://knowledge/material-recipes`
- `unreal://project/context`

### Phase 2b — Skills Library ✅ (skills/)
New skill files (7):
- `SKILL_import_texture.md`
- `SKILL_import_static_mesh.md`
- `SKILL_import_skeletal_mesh.md`
- `SKILL_batch_import_folder.md`
- `SKILL_import_folder_as_character.md`
- `SKILL_diagnose_failed_import.md`
- `SKILL_compile_validate_blueprint.md`

**New total: 362 MCP tools (351 + 11 new) / 24 modules**

### Next: Phase 3 — Graph-aware Blueprint/Material diagnostics
- `compile_blueprint_and_report` — compile + structured error list
- `compile_material_and_report` — material compile + warnings
- `validate_import_result` — post-import asset health check
- `get_changed_assets_since(timestamp)` — diff Content Browser
