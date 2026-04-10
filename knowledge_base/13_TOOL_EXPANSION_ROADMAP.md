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

### 19. `add_sound_cue_node`
**Why needed:** Play sound effects from Blueprint graph (footsteps, lightsaber sounds).

**Proposed spec:**
```bash
python3 sandbox_ue5cli.py add_play_sound_node '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "graph_name": "EventGraph",
  "sound_path": "/Game/Dantooine/Art/Audio/SFX/SFX_SaberSwing",
  "node_position": {"x": 400, "y": 200}
}'
```

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
