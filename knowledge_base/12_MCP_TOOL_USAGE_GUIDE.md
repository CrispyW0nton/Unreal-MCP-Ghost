# UnrealMCP Tool Usage Guide — DEFINITIVE REFERENCE
> The ONLY authoritative guide for any AI agent using the Unreal-MCP-Ghost plugin.
> DO NOT invent command names. DO NOT guess parameters. Use ONLY what is documented here.
> Version: 2026-04-10 | Plugin: UnrealMCPBlueprintCommands.cpp + UnrealMCPBlueprintNodeCommands.cpp

---

## MANDATORY RULES FOR ALL AI AGENTS

### The 12 Commandments
1. **NEVER invent a command name** — only use commands in this document
2. **NEVER guess a parameter name** — every parameter is listed here with exact spelling
3. **ALWAYS check node existence before connecting** — call `get_blueprint_nodes` first
4. **ALWAYS compile after node changes** — `compile_blueprint` is the last step always
5. **ALWAYS verify node was created** — check the returned `node_id` before connecting
6. **ALWAYS use `exec_python` for asset creation** — `create_blueprint` hardcodes wrong path
7. **ALWAYS call `SpawnDefaultController`** — for any runtime-spawned AI pawn
8. **ALWAYS multiply by Delta Seconds** — any per-frame movement value
9. **NEVER hardcode node GUIDs** — always get them from `get_blueprint_nodes` response
10. **ALWAYS handle Cast Failed path** — null references crash the game
11. **ALWAYS check Is Valid** — before using any object reference from Get functions
12. **Parent classes use C++ names** — `GameModeBase` not `GameMode`, `Character` not `ACharacter`

---

## Connection and Discovery

### Test Plugin Connection
```bash
python3 sandbox_ue5cli.py get_actors_in_level '{}'
```
If this returns actors or an empty array, the plugin is connected on port **55557**.

### Get UE5 Version
```bash
python3 sandbox_ue5cli.py exec_python '{"code": "import unreal; print(unreal.SystemLibrary.get_engine_version())"}'
```

---

## COMPLETE COMMAND REFERENCE

---

### 1. Level / Actor Commands

#### `get_actors_in_level`
```bash
python3 sandbox_ue5cli.py get_actors_in_level '{}'
```
Returns: Array of all actors with class, location, rotation, scale.

#### `find_actors_by_name`
```bash
python3 sandbox_ue5cli.py find_actors_by_name '{"name": "BP_PlayerJediCharacter"}'
```
| Parameter | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | Partial name match |

#### `spawn_actor` / `create_actor`
```bash
python3 sandbox_ue5cli.py spawn_actor '{"name": "BP_RoamingNPC_StudentA", "location": [0,0,0], "rotation": [0,0,0]}'
```
| Parameter | Type | Required |
|---|---|---|
| `name` | string | ✅ |
| `location` | [x,y,z] | ❌ |
| `rotation` | [p,y,r] | ❌ |

#### `spawn_blueprint_actor`
```bash
python3 sandbox_ue5cli.py spawn_blueprint_actor '{
  "blueprint_path": "/Game/Dantooine/Blueprints/NPC/BP_MasterJedi",
  "location": {"x": 0, "y": 0, "z": 0},
  "rotation": {"pitch": 0, "yaw": 0, "roll": 0}
}'
```
| Parameter | Type | Required |
|---|---|---|
| `blueprint_path` | string (full content path) | ✅ |
| `location` | {x,y,z} | ❌ |
| `rotation` | {pitch,yaw,roll} | ❌ |
| `scale` | {x,y,z} | ❌ |

#### `delete_actor`
```bash
python3 sandbox_ue5cli.py delete_actor '{"name": "BP_RoamingNPC_StudentA_0"}'
```

#### `set_actor_transform`
```bash
python3 sandbox_ue5cli.py set_actor_transform '{
  "name": "BP_MasterJedi_0",
  "location": {"x": 100, "y": 0, "z": 0},
  "rotation": {"pitch": 0, "yaw": 90, "roll": 0},
  "scale": {"x": 1, "y": 1, "z": 1}
}'
```

#### `get_actor_properties`
```bash
python3 sandbox_ue5cli.py get_actor_properties '{"name": "BP_MasterJedi_0"}'
```

#### `set_actor_property`
```bash
python3 sandbox_ue5cli.py set_actor_property '{"name": "BP_MasterJedi_0", "property": "bHidden", "value": "false"}'
```

---

### 2. Blueprint Class Commands

#### `create_blueprint`
⚠️ **ALWAYS saves to `/Game/Blueprints/` — use `exec_python` for custom paths!**
```bash
python3 sandbox_ue5cli.py create_blueprint '{"name": "BP_TestActor", "parent_class": "Actor"}'
```
| Parameter | Type | Required | Notes |
|---|---|---|---|
| `name` | string | ✅ | Asset name (will be in /Game/Blueprints/) |
| `parent_class` | string | ❌ | Default: `Actor` |

**Supported parent_class values:** `Actor`, `Pawn`, `Character`, `PlayerController`, `GameModeBase`, `AIController`, `GameInstance`, `SaveGame`, `ActorComponent`, `SceneComponent`

#### `compile_blueprint`
**ALWAYS call after modifying nodes. Never skip this.**
```bash
python3 sandbox_ue5cli.py compile_blueprint '{"blueprint_name": "BP_PlayerJediCharacter"}'
```

#### `set_blueprint_property`
Sets a default property value on the Blueprint Class Default Object (CDO).
```bash
python3 sandbox_ue5cli.py set_blueprint_property '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "property_name": "MaxHealth",
  "property_value": "100.0"
}'
```

#### `set_blueprint_variable_default`
```bash
python3 sandbox_ue5cli.py set_blueprint_variable_default '{
  "blueprint_name": "BP_FloatingBot",
  "variable_name": "Speed",
  "default_value": "300"
}'
```

#### `set_pawn_properties`
```bash
python3 sandbox_ue5cli.py set_pawn_properties '{
  "blueprint_name": "BP_RoamingNPC_Base",
  "auto_possess_ai": "PlacedInWorldOrSpawned"
}'
```

#### `set_blueprint_ai_controller`
```bash
python3 sandbox_ue5cli.py set_blueprint_ai_controller '{
  "blueprint_name": "BP_RoamingNPC_Base",
  "ai_controller_class": "BP_NPC_AIController",
  "auto_possess_ai": "PlacedInWorldOrSpawned"
}'
```

---

### 3. Component Commands

#### `add_component_to_blueprint`
```bash
python3 sandbox_ue5cli.py add_component_to_blueprint '{
  "blueprint_name": "BP_LightsaberWorkbench",
  "component_type": "StaticMeshComponent",
  "component_name": "WorkbenchMesh"
}'
```
| Parameter | Type | Required |
|---|---|---|
| `blueprint_name` | string | ✅ |
| `component_type` | string | ✅ |
| `component_name` | string | ✅ |

**Common component_type values:**
- `StaticMeshComponent`, `SkeletalMeshComponent`
- `BoxComponent`, `SphereComponent`, `CapsuleComponent`
- `PointLightComponent`, `SpotLightComponent`
- `AudioComponent`
- `FloatingPawnMovement`, `CharacterMovementComponent`
- `SpringArmComponent`, `CameraComponent`
- `NiagaraComponent`
- `NavMovementComponent`
- `PawnSensing`

#### `set_component_property`
```bash
python3 sandbox_ue5cli.py set_component_property '{
  "blueprint_name": "BP_FloatingBot",
  "component_name": "FloatingPawnMovement",
  "property_name": "MaxSpeed",
  "property_value": "600.0"
}'
```

#### `set_physics_properties`
```bash
python3 sandbox_ue5cli.py set_physics_properties '{
  "blueprint_name": "BP_DebrisActor",
  "component_name": "BodyMesh",
  "simulate_physics": true,
  "gravity_enabled": true
}'
```

#### `set_static_mesh_properties`
```bash
python3 sandbox_ue5cli.py set_static_mesh_properties '{
  "blueprint_name": "BP_LightsaberWorkbench",
  "component_name": "WorkbenchMesh",
  "static_mesh_path": "/Game/Dantooine/Art/Environment/SM_Workbench"
}'
```

---

### 4. Blueprint Node Read Commands

#### `get_blueprint_nodes`
**Use this BEFORE connecting anything.** Returns all nodes with IDs and pin names.
```bash
python3 sandbox_ue5cli.py get_blueprint_nodes '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "graph_name": "EventGraph"
}'
```
Response: `{nodes: [{id: "GUID", type: "...", name: "...", pins: [...]}]}`

#### `get_node_info` / `get_blueprint_node_details`
```bash
python3 sandbox_ue5cli.py get_node_info '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "graph_name": "EventGraph",
  "node_id": "BAC2829C42AE060F02D4E4A93536C397"
}'
```

---

### 5. Node Creation Commands

#### `add_blueprint_event_node`
Adds red event nodes.
```bash
python3 sandbox_ue5cli.py add_blueprint_event_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "event_name": "ReceiveBeginPlay",
  "node_position": {"x": -200, "y": 0}
}'
```
**Common event_name values:**
- `ReceiveBeginPlay` — BeginPlay event
- `ReceiveTick` — Tick event (outputs `DeltaSeconds`, `then`)
- `ReceiveEndPlay` — EndPlay event
- `ReceiveHit` — Collision Hit
- `ReceiveActorBeginOverlap` — Overlap enter
- `ReceiveActorEndOverlap` — Overlap exit
- `ReceiveAnyDamage` — Any damage received
- `ReceivePointDamage` — Directional damage

#### `add_blueprint_function_node`
```bash
python3 sandbox_ue5cli.py add_blueprint_function_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "function_name": "GetActorLocation",
  "node_position": {"x": 200, "y": 0}
}'
```
| Parameter | Type | Required |
|---|---|---|
| `blueprint_name` | string | ✅ |
| `graph_name` | string | ✅ |
| `function_name` | string | ✅ |
| `target_class` | string | ❌ |
| `node_position` | {x,y} | ❌ |

**Verified function_name values:**
- `GetActorLocation`, `SetActorLocation`, `AddActorWorldOffset`, `AddActorLocalOffset`
- `GetActorRotation`, `SetActorRotation`, `GetActorForwardVector`
- `GetVelocity`, `GetActorTransform`, `SetActorTransform`
- `SpawnDefaultController` — CRITICAL for runtime AI
- `GetPlayerPawn`, `GetPlayerController`, `GetPlayerCharacter`
- `ApplyDamage`, `ApplyPointDamage`
- `PlayAnimMontage`, `StopAnimMontage`
- `CreateWidget`, `AddToViewport`, `RemoveFromParent`
- `IsValid`, `IsValidClass`
- `LineTraceByChannel`, `LineTraceForObjects`
- `GetWorldTimerManager`
- `Multiply`, `Add`, `Subtract`, `Divide` (math operators)
- `VectorLength`, `Normalize`, `DotProduct`
- `GetRandomPointInNavigableRadius`
- `MoveToActor`, `MoveToLocation`, `StopMovement`
- `RunBehaviorTree` (AIController)

#### `add_blueprint_custom_event_node`
```bash
python3 sandbox_ue5cli.py add_blueprint_custom_event_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "event_name": "OnPlayerDetected",
  "node_position": {"x": 0, "y": 400}
}'
```

#### `add_blueprint_variable_get_node`
```bash
python3 sandbox_ue5cli.py add_blueprint_variable_get_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "variable_name": "Speed",
  "node_position": {"x": 100, "y": 100}
}'
```

#### `add_blueprint_variable_set_node`
```bash
python3 sandbox_ue5cli.py add_blueprint_variable_set_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "variable_name": "Health",
  "node_position": {"x": 400, "y": 0}
}'
```

#### `add_blueprint_set_component_property`
Creates SET node for a component property in the graph.
```bash
python3 sandbox_ue5cli.py add_blueprint_set_component_property '{
  "blueprint_name": "BP_FloatingBot",
  "graph_name": "EventGraph",
  "component_name": "FloatingPawnMovement",
  "property_name": "Velocity",
  "node_position": {"x": 320, "y": 144}
}'
```
⚠️ **The `self` pin on the SET node IS the Target pin** — wire FPM component GET to it.

#### `add_blueprint_cast_node`
```bash
python3 sandbox_ue5cli.py add_blueprint_cast_node '{
  "blueprint_name": "BP_NPCController",
  "graph_name": "EventGraph",
  "cast_target_class": "BP_PlayerJediCharacter",
  "node_position": {"x": 400, "y": 0}
}'
```
Pins: `execute`, `Object` (input), `Cast Succeeded` (exec out), `Cast Failed` (exec out), `As BP_PlayerJediCharacter` (typed ref out)

#### `add_blueprint_branch_node`
```bash
python3 sandbox_ue5cli.py add_blueprint_branch_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 300, "y": 0}
}'
```
Pins: `execute` (in), `Condition` (bool in), `True` (exec out), `False` (exec out)

#### `add_blueprint_sequence_node`
Pins: `execute`, `Then 0`, `Then 1`, `Then 2`...
```bash
python3 sandbox_ue5cli.py add_blueprint_sequence_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 200, "y": 0}
}'
```

#### `add_blueprint_timeline_node`
```bash
python3 sandbox_ue5cli.py add_blueprint_timeline_node '{
  "blueprint_name": "BP_SkyBirdShip",
  "graph_name": "EventGraph",
  "timeline_name": "FlyByTimeline",
  "node_position": {"x": 300, "y": 0}
}'
```

#### `add_event_dispatcher`
```bash
python3 sandbox_ue5cli.py add_event_dispatcher '{
  "blueprint_name": "BP_DantooineQuestManager",
  "dispatcher_name": "OnQuestStageChanged"
}'
```

#### `call_event_dispatcher`
```bash
python3 sandbox_ue5cli.py call_event_dispatcher '{
  "blueprint_name": "BP_DantooineQuestManager",
  "graph_name": "EventGraph",
  "dispatcher_name": "OnQuestStageChanged",
  "node_position": {"x": 600, "y": 0}
}'
```

#### Flow Control Nodes (all use same params pattern)
```bash
# Gate node — pins: Enter, Open, Close, Toggle, Exit
python3 sandbox_ue5cli.py add_blueprint_gate_node '{"blueprint_name": "BP_X", "graph_name": "EventGraph", "node_position": {"x": 200, "y": 0}}'

# Do Once node — pins: execute, Reset, Completed
python3 sandbox_ue5cli.py add_blueprint_do_once_node '{"blueprint_name": "BP_X", "graph_name": "EventGraph", "node_position": {"x": 200, "y": 0}}'

# Do N node — pins: execute, Reset, Completed, Counter
python3 sandbox_ue5cli.py add_blueprint_do_n_node '{"blueprint_name": "BP_X", "graph_name": "EventGraph", "node_position": {"x": 200, "y": 0}}'

# Flip Flop node — pins: execute, A, B, Is A
python3 sandbox_ue5cli.py add_blueprint_flipflop_node '{"blueprint_name": "BP_X", "graph_name": "EventGraph", "node_position": {"x": 200, "y": 0}}'

# For Each Loop node — pins: execute, Array, Loop Body, Array Element, Array Index, Completed
python3 sandbox_ue5cli.py add_blueprint_for_each_loop_node '{"blueprint_name": "BP_X", "graph_name": "EventGraph", "node_position": {"x": 200, "y": 0}}'

# For Loop node — pins: execute, First Index, Last Index, Index, Loop Body, Completed
python3 sandbox_ue5cli.py add_blueprint_for_loop_node '{"blueprint_name": "BP_X", "graph_name": "EventGraph", "node_position": {"x": 200, "y": 0}}'

# While Loop node — pins: execute, Condition, Loop Body, Completed
python3 sandbox_ue5cli.py add_blueprint_while_loop_node '{"blueprint_name": "BP_X", "graph_name": "EventGraph", "node_position": {"x": 200, "y": 0}}'

# Switch node — integer switch
python3 sandbox_ue5cli.py add_blueprint_switch_node '{"blueprint_name": "BP_X", "graph_name": "EventGraph", "node_position": {"x": 200, "y": 0}}'

# MultiGate node
python3 sandbox_ue5cli.py add_blueprint_multigate_node '{"blueprint_name": "BP_X", "graph_name": "EventGraph", "node_position": {"x": 200, "y": 0}}'
```

---

### 6. Node Connection Command

#### `connect_blueprint_nodes`
**CRITICAL: Use `source_pin` and `target_pin` — not any other naming!**
```bash
python3 sandbox_ue5cli.py connect_blueprint_nodes '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "source_node_id": "GUID-FROM-GET-NODES",
  "target_node_id": "GUID-FROM-GET-NODES",
  "source_pin": "then",
  "target_pin": "execute"
}'
```
| Parameter | Type | Required |
|---|---|---|
| `blueprint_name` | string | ✅ |
| `graph_name` | string | ✅ |
| `source_node_id` | string (GUID) | ✅ |
| `target_node_id` | string (GUID) | ✅ |
| `source_pin` | string | ✅ |
| `target_pin` | string | ✅ |

### Complete Pin Name Reference

| Pin | Found On | Direction |
|---|---|---|
| `execute` | All action nodes | Input execution |
| `then` | All action nodes | Output execution |
| `then` | Event Tick | Output execution |
| `DeltaSeconds` | Event Tick | Output float |
| `ReturnValue` | All function calls | Output data |
| `Target` | Most function nodes | Input (who to call on) |
| `self` | Variable SET nodes (component) | Input object (IS the Target) |
| `A` | Math nodes (Multiply, Add, etc.) | Input data |
| `B` | Math nodes | Input data |
| `Condition` | Branch | Input bool |
| `True` | Branch | Output exec |
| `False` | Branch | Output exec |
| `Then 0`, `Then 1`... | Sequence | Output exec |
| `Array` | For Each Loop | Input array |
| `Loop Body` | For Each Loop | Output exec (per element) |
| `Array Element` | For Each Loop | Output data (current element) |
| `Array Index` | For Each Loop | Output int |
| `Completed` | For Each/For/While loops | Output exec (after all iterations) |
| `Object` | Cast To nodes | Input object ref |
| `Cast Succeeded` | Cast To | Output exec |
| `Cast Failed` | Cast To | Output exec |
| `As [ClassName]` | Cast To | Output typed ref |
| `Enter` | Gate | Input exec |
| `Open` | Gate | Input exec |
| `Close` | Gate | Input exec |
| `Toggle` | Gate | Input exec |
| `Exit` | Gate | Output exec |
| `Velocity` | SET Velocity on FPM | Input Vector |
| `New Location` | Set Actor Location | Input Vector |
| `New Rotation` | Set Actor Rotation | Input Rotator |
| `New Scale 3D` | Set Actor Scale 3D | Input Vector |
| `In Montage` | Play Anim Montage | Input AnimMontage ref |
| `In Play Rate` | Play Anim Montage | Input float |
| `Is A` | Flip Flop | Output bool |

---

### 7. Node Management

#### `delete_blueprint_node`
```bash
python3 sandbox_ue5cli.py delete_blueprint_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_id": "GUID-FROM-GET-NODES"
}'
```

#### `set_spawn_actor_class`
Sets the class pin of a SpawnActorFromClass node.
```bash
python3 sandbox_ue5cli.py set_spawn_actor_class '{
  "blueprint_name": "BP_EnemySpawner",
  "graph_name": "EventGraph",
  "node_id": "SPAWN-NODE-GUID",
  "class_path": "/Game/Dantooine/Blueprints/Combat/BP_SparringOpponent"
}'
```

---

### 8. Additional Commands (Node Commands Module)

These commands are in the `UnrealMCPBlueprintNodeCommands` module and fully functional.

#### `find_blueprint_nodes`
Search nodes by type and optional filters.
```bash
python3 sandbox_ue5cli.py find_blueprint_nodes '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_type": "event",
  "event_name": "ReceiveBeginPlay"
}'
```
| Parameter | Required | Notes |
|---|---|---|
| `blueprint_name` | ✅ | |
| `graph_name` | ✅ | |
| `node_type` | ❌ | `event`, `function`, `variable`, `input_action` |
| `event_name` | ❌ | Filter by event name |
| `function_name` | ❌ | Filter by function name |
| `variable_name` | ❌ | Filter by variable name |

#### `get_blueprint_graphs`
List all graphs in a Blueprint.
```bash
python3 sandbox_ue5cli.py get_blueprint_graphs '{"blueprint_name": "BP_MyActor"}'
```
Returns: Array of graph names. Default graphs: `EventGraph`, `ConstructionScript`.

#### `get_node_by_id`
Get full details of a specific node.
```bash
python3 sandbox_ue5cli.py get_node_by_id '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_id": "GUID-HERE"
}'
```

#### `disconnect_blueprint_nodes`
Disconnect a specific pin or all connections between two nodes.
```bash
# Disconnect a single pin
python3 sandbox_ue5cli.py disconnect_blueprint_nodes '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_id": "SOURCE-NODE-GUID",
  "pin_name": "then"
}'
# Disconnect two specific nodes
python3 sandbox_ue5cli.py disconnect_blueprint_nodes '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "source_node_id": "NODE-A-GUID",
  "target_node_id": "NODE-B-GUID"
}'
```

#### `set_node_pin_value`
Set a literal value on a pin (replaces typing a value in the node field).
```bash
python3 sandbox_ue5cli.py set_node_pin_value '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_id": "NODE-GUID",
  "pin_name": "Duration",
  "value": "2.5"
}'
```
| Parameter | Required | Notes |
|---|---|---|
| `blueprint_name` | ✅ | |
| `graph_name` | ✅ | |
| `node_id` | ✅ | |
| `pin_name` | ✅ | Exact pin name from get_blueprint_nodes |
| `value` | ✅ | String, number, or boolean |

#### `add_blueprint_variable`
Add a variable to a Blueprint's class (not a node — adds to the Variables panel).
```bash
python3 sandbox_ue5cli.py add_blueprint_variable '{
  "blueprint_name": "BP_MyActor",
  "variable_name": "Health",
  "variable_type": "Float",
  "is_exposed": true,
  "default_value": "100.0"
}'
```
| Parameter | Required | Notes |
|---|---|---|
| `blueprint_name` | ✅ | |
| `variable_name` | ✅ | |
| `variable_type` | ✅ | `Boolean`, `Integer`, `Float`, `Double`, `String`, `Name`, `Text`, `Vector`, `Rotator`, `Transform`, `Object/<ClassPath>` |
| `is_exposed` | ❌ | Bool — makes variable instance-editable |
| `default_value` | ❌ | String representation of default value |

#### `get_blueprint_variable_defaults`
Get current default values of Blueprint variables.
```bash
python3 sandbox_ue5cli.py get_blueprint_variable_defaults '{
  "blueprint_name": "BP_MyActor",
  "variable_name": "Health"
}'
```
Omit `variable_name` to get ALL variable defaults.

#### `get_blueprint_components`
Get a list of all components in a Blueprint.
```bash
python3 sandbox_ue5cli.py get_blueprint_components '{"blueprint_name": "BP_PlayerJediCharacter"}'
```
Returns: Array of `{name, class, variable_name}` for each component.

#### `move_blueprint_node`
Move an existing node to a new position.
```bash
python3 sandbox_ue5cli.py move_blueprint_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_id": "NODE-GUID",
  "node_position": {"x": 400, "y": 0}
}'
```

#### `setup_navmesh`
Create or resize a NavMeshBoundsVolume in the current level.
```bash
python3 sandbox_ue5cli.py setup_navmesh '{
  "extent": {"x": 5000, "y": 5000, "z": 500},
  "location": {"x": 0, "y": 0, "z": 0},
  "rebuild": true
}'
```
All parameters optional. Default extent: 5000×5000×500. If a NavMeshBoundsVolume already exists, it is resized.

#### `add_blueprint_enhanced_input_action_node`
Add an Enhanced Input Action binding node (UE5 Enhanced Input system).
```bash
python3 sandbox_ue5cli.py add_blueprint_enhanced_input_action_node '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "graph_name": "EventGraph",
  "action_asset": "/Game/Dantooine/Data/Input/IA_Jump",
  "node_position": {"x": 0, "y": 0}
}'
```
> **IMPORTANT**: `action_asset` is the FULL content path to the IA_ asset, not just its name.
> The output pins are: `Triggered`, `Started`, `Ongoing`, `Canceled`, `Completed`.

#### `add_blueprint_self_reference`
Add a `Self` node (returns the Blueprint's own actor reference).
```bash
python3 sandbox_ue5cli.py add_blueprint_self_reference '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 0, "y": 200}
}'
```
Output pin: `self`

#### `add_blueprint_get_self_component_reference`
Add a GET node for a component that exists ON THIS Blueprint.
```bash
python3 sandbox_ue5cli.py add_blueprint_get_self_component_reference '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "graph_name": "EventGraph",
  "component_name": "CapsuleComponent",
  "node_position": {"x": 0, "y": 200}
}'
```

#### `add_blueprint_get_component_node`
Add a generic component GET node.
```bash
python3 sandbox_ue5cli.py add_blueprint_get_component_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "component_name": "CharacterMovement",
  "node_position": {"x": 0, "y": 200}
}'
```

#### `add_blueprint_for_loop_node`
Add a `For Loop` node (integer range iteration).
```bash
python3 sandbox_ue5cli.py add_blueprint_for_loop_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 400, "y": 0}
}'
```
Pins: `Execute`, `First Index`, `Last Index`, `Increment` → `Loop Body` (exec, Index int), `Completed` (exec)

#### `add_blueprint_for_each_loop_node`
Add a `ForEach` loop node (array iteration).
```bash
python3 sandbox_ue5cli.py add_blueprint_for_each_loop_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 400, "y": 0}
}'
```
Pins: `Execute`, `Array` → `Loop Body` (exec, Array Element, Array Index), `Completed` (exec)

#### `add_blueprint_flip_flop_node`
Add a `Flip Flop` node (alternates between A/B each call).
```bash
python3 sandbox_ue5cli.py add_blueprint_flip_flop_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 400, "y": 0}
}'
```
Pins: `execute` → `A` (exec), `B` (exec), `Is A` (bool)

#### `add_blueprint_do_once_node`
Add a `Do Once` node (executes the first time, ignores after unless reset).
```bash
python3 sandbox_ue5cli.py add_blueprint_do_once_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 400, "y": 0}
}'
```
Pins: `execute`, `Reset` (exec) → `Completed` (exec)

#### `add_blueprint_gate_node`
Add a `Gate` node (acts as a conditional pass-through).
```bash
python3 sandbox_ue5cli.py add_blueprint_gate_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 400, "y": 0}
}'
```
Pins: `Enter`, `Open`, `Close`, `Toggle` (all exec) → `Exit` (exec)

#### `add_blueprint_switch_on_int_node`
Add a `Switch on Int` node.
```bash
python3 sandbox_ue5cli.py add_blueprint_switch_on_int_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 400, "y": 0}
}'
```
Pins: `execute`, `Selection` (int) → `Case 0`, `Case 1`, ... `Default` (exec)

#### `add_blueprint_spawn_actor_node`
Add a `Spawn Actor from Class` node.
```bash
python3 sandbox_ue5cli.py add_blueprint_spawn_actor_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "node_position": {"x": 600, "y": 0}
}'
```
Pins: `execute`, `Class`, `Spawn Transform`, `Collision Handling Override` → `then` (exec), `Return Value` (Actor ref)
> After adding: use `set_spawn_actor_class` to set the Class pin.

#### `add_blueprint_comment_node`
Add a comment box to organize the graph visually.
```bash
python3 sandbox_ue5cli.py add_blueprint_comment_node '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "comment": "Initialize Health System",
  "node_position": {"x": -100, "y": -80},
  "width": 600,
  "height": 200
}'
```

#### `focus_viewport`
Focus the viewport on a specific location.
```bash
python3 sandbox_ue5cli.py focus_viewport '{
  "location": {"x": 0, "y": 0, "z": 0}
}'
```

#### `take_screenshot`
Take a screenshot from the editor viewport.
```bash
python3 sandbox_ue5cli.py take_screenshot '{
  "filename": "screenshot_01"
}'
```

---

### 9. Extended Commands (ExtendedCommands Module)

These are in `UnrealMCPExtendedCommands.cpp`. Many overlap with NodeCommands but use older naming.

#### `set_game_mode_for_level`
Set the GameMode override for the current level.
```bash
python3 sandbox_ue5cli.py set_game_mode_for_level '{
  "game_mode_name": "BP_DantooineGameMode"
}'
```
> ⚠️ **PARAM FIX**: Use `game_mode_name` (Blueprint asset name only, NOT full path). The plugin resolves the path internally.
> **PREFERRED** over manually setting Project Settings when only one level needs a specific GameMode.

#### `create_blueprint_interface`
Create a Blueprint Interface asset.
```bash
python3 sandbox_ue5cli.py create_blueprint_interface '{
  "name": "BPI_Interactable",
  "path": "/Game/Dantooine/Interfaces"
}'
```

#### `implement_blueprint_interface`
Make a Blueprint implement a Blueprint Interface.
```bash
python3 sandbox_ue5cli.py implement_blueprint_interface '{
  "blueprint_name": "BP_LightsaberWorkbench",
  "interface_name": "BPI_Interactable"
}'
```
> ⚠️ **PARAM FIX**: Use `interface_name` (asset name only, NOT `interface_path`). The plugin searches by name, not path.

#### `add_interface_function_node`
Add a node to call an interface function.
```bash
python3 sandbox_ue5cli.py add_interface_function_node '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "graph_name": "EventGraph",
  "interface_name": "BPI_Interactable",
  "function_name": "Interact",
  "node_position": {"x": 400, "y": 0}
}'
```

#### `create_struct`
Create a Blueprint Struct asset.
```bash
python3 sandbox_ue5cli.py create_struct '{
  "name": "ST_DialogueLine",
  "path": "/Game/Dantooine/Data/Structs"
}'
```

#### `create_enum`
Create a Blueprint Enum asset.
```bash
python3 sandbox_ue5cli.py create_enum '{
  "name": "E_QuestStage",
  "path": "/Game/Dantooine/Data/Enums"
}'
```

#### `create_data_table`
Create a Data Table asset.
```bash
python3 sandbox_ue5cli.py create_data_table '{
  "name": "DT_DialogueLines",
  "path": "/Game/Dantooine/Data/DataTables",
  "row_struct": "/Game/Dantooine/Data/Structs/ST_DialogueLine"
}'
```

#### `create_animation_blueprint`
Create an Animation Blueprint.
```bash
python3 sandbox_ue5cli.py create_animation_blueprint '{
  "name": "ABP_PlayerJedi",
  "path": "/Game/Dantooine/Animation/Player",
  "skeleton_path": "/Game/Dantooine/Art/Characters/SK_PlayerJedi"
}'
```
> Leave `skeleton_path` blank if skeleton isn't imported yet; assign later in the editor.

#### `add_state_machine`
Add a State Machine to an Animation Blueprint's AnimGraph.
```bash
python3 sandbox_ue5cli.py add_state_machine '{
  "blueprint_name": "ABP_PlayerJedi",
  "name": "LocomotionSM"
}'
```

#### `add_animation_state`
Add a state to a State Machine.
```bash
python3 sandbox_ue5cli.py add_animation_state '{
  "blueprint_name": "ABP_PlayerJedi",
  "state_machine_name": "LocomotionSM",
  "state_name": "Idle"
}'
```

#### `add_state_transition`
Add a transition between two states.
```bash
python3 sandbox_ue5cli.py add_state_transition '{
  "blueprint_name": "ABP_PlayerJedi",
  "state_machine_name": "LocomotionSM",
  "from_state": "Idle",
  "to_state": "Walk"
}'
```

#### `set_animation_for_state`
Assign an animation sequence to a state.
```bash
python3 sandbox_ue5cli.py set_animation_for_state '{
  "blueprint_name": "ABP_PlayerJedi",
  "state_machine_name": "LocomotionSM",
  "state_name": "Idle",
  "animation_path": "/Game/Dantooine/Animation/Player/AN_Player_Idle"
}'
```

#### `create_behavior_tree`
Create a Behavior Tree asset.
```bash
python3 sandbox_ue5cli.py create_behavior_tree '{
  "name": "BT_RoamingNPC",
  "path": "/Game/Dantooine/AI/BehaviorTrees"
}'
```

#### `create_blackboard`
Create a Blackboard asset. Optionally pre-populate keys in the same call.
```bash
python3 sandbox_ue5cli.py create_blackboard '{
  "name": "BB_RoamingNPC",
  "path": "/Game/Dantooine/AI/Blackboard"
}'
```
**With pre-populated keys (recommended):**
```bash
python3 sandbox_ue5cli.py create_blackboard '{
  "name": "BB_RoamingNPC",
  "path": "/Game/Dantooine/AI/Blackboard",
  "keys": [
    {"name": "PatrolLocation", "type": "Vector"},
    {"name": "IsTalking",      "type": "Bool"},
    {"name": "TargetActor",   "type": "Object"}
  ]
}'
```
| Key `type` value | Blackboard Key Type |
|---|---|
| `Vector` | Blackboard Vector |
| `Bool` / `Boolean` | Blackboard Bool |
| `Float` | Blackboard Float |
| `Int` / `Integer` | Blackboard Integer |
| `String` | Blackboard String |
| `Object` / `Actor` | Blackboard Object (Actor) |
> **TIP**: Using the `keys` array here is the ONLY way to add keys via MCP. There is no separate `add_blackboard_key` command.

#### `add_custom_event` (Extended — alias for add_blueprint_custom_event_node)
```bash
python3 sandbox_ue5cli.py add_custom_event '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "event_name": "OnHealthChanged",
  "node_position": {"x": 0, "y": 200}
}'
```

#### `bind_event_to_dispatcher`
Bind a custom event to an Event Dispatcher.
```bash
python3 sandbox_ue5cli.py bind_event_to_dispatcher '{
  "blueprint_name": "BP_MyActor",
  "graph_name": "EventGraph",
  "dispatcher_name": "OnQuestStageChanged",
  "event_name": "HandleQuestStageChanged",
  "node_position": {"x": 400, "y": 0}
}'
```

#### `add_custom_function`
Add a custom function graph to a Blueprint.
```bash
python3 sandbox_ue5cli.py add_custom_function '{
  "blueprint_name": "BP_MyActor",
  "function_name": "CalculateDamage"
}'
```

---

### 10. UMG Commands (UMGCommands Module)

#### `create_umg_widget_blueprint`
Create a Widget Blueprint asset.
```bash
python3 sandbox_ue5cli.py create_umg_widget_blueprint '{
  "name": "WBP_HUD",
  "path": "/Game/Dantooine/Widgets"
}'
```
> Prefer `exec_python` with `WidgetBlueprintFactory` for more control.

#### `add_text_block_to_widget`
Add a Text Block widget to a Widget Blueprint.
```bash
python3 sandbox_ue5cli.py add_text_block_to_widget '{
  "widget_name": "WBP_HUD",
  "text_block_name": "HealthText",
  "text": "100",
  "position": {"x": 10, "y": 10}
}'
```

#### `add_button_to_widget`
Add a Button widget to a Widget Blueprint.
```bash
python3 sandbox_ue5cli.py add_button_to_widget '{
  "widget_name": "WBP_HUD",
  "button_name": "RestartButton",
  "position": {"x": 100, "y": 100}
}'
```

#### `bind_widget_event`
Bind a widget event (e.g., button click) to a function.
```bash
python3 sandbox_ue5cli.py bind_widget_event '{
  "widget_name": "WBP_HUD",
  "widget_element_name": "RestartButton",
  "event_name": "OnClicked",
  "function_name": "HandleRestartClicked"
}'
```

---

### 11. exec_python — The Universal Tool

**Use `exec_python` for everything not covered by direct commands.**

#### Syntax
```bash
python3 sandbox_ue5cli.py exec_python '{"code": "PYTHON_CODE_HERE"}'
```
For multi-line code, use escaped newlines:
```bash
python3 sandbox_ue5cli.py exec_python '{"code": "import unreal\nat=unreal.AssetToolsHelpers.get_asset_tools()\nprint(\"ready\")"}'
```

#### Asset Creation Patterns

**Create Blueprint in custom folder:**
```python
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()
factory = unreal.BlueprintFactory()
factory.set_editor_property("parent_class", unreal.Character)
asset = at.create_asset("BP_PlayerJediCharacter", "/Game/Dantooine/Blueprints/Player", unreal.Blueprint, factory)
print("OK" if asset else "FAIL")
```

**Create Widget Blueprint:**
```python
factory = unreal.WidgetBlueprintFactory()
asset = at.create_asset("WBP_HUD", "/Game/Dantooine/Widgets", unreal.WidgetBlueprint, factory)
```

**Create Blackboard:**
```python
asset = at.create_asset("BB_RoamingNPC", "/Game/Dantooine/AI/Blackboard", unreal.BlackboardData, unreal.BlackboardDataFactory())
```

**Create Behavior Tree:**
```python
asset = at.create_asset("BT_RoamingNPC", "/Game/Dantooine/AI/BehaviorTrees", unreal.BehaviorTree, unreal.BehaviorTreeFactory())
```

**Create BT Task Blueprint:**
```python
factory = unreal.BlueprintFactory()
factory.set_editor_property("parent_class", unreal.BTTask_BlueprintBase)
asset = at.create_asset("BTT_FindRandomPatrol", "/Game/Dantooine/AI/Tasks", unreal.Blueprint, factory)
```

**Create BT Decorator Blueprint:**
```python
factory = unreal.BlueprintFactory()
factory.set_editor_property("parent_class", unreal.BTDecorator_BlueprintBase)
asset = at.create_asset("BTD_CanSeePlayer", "/Game/Dantooine/AI/Decorators", unreal.Blueprint, factory)
```

**Create BT Service Blueprint:**
```python
factory = unreal.BlueprintFactory()
factory.set_editor_property("parent_class", unreal.BTService_BlueprintBase)
asset = at.create_asset("BTS_UpdatePlayerLocation", "/Game/Dantooine/AI/Services", unreal.Blueprint, factory)
```

**Create AI Controller:**
```python
factory = unreal.BlueprintFactory()
factory.set_editor_property("parent_class", unreal.AIController)
asset = at.create_asset("BP_NPC_AIController", "/Game/Dantooine/Blueprints/AI", unreal.Blueprint, factory)
```

**Create Animation Blueprint (no skeleton yet):**
```python
factory = unreal.AnimBlueprintFactory()
factory.set_editor_property("target_skeleton", None)
factory.set_editor_property("blueprint_type", unreal.BlueprintType.BPTYPE_NORMAL)
asset = at.create_asset("ABP_PlayerJedi", "/Game/Dantooine/Animation/Player", unreal.AnimBlueprint, factory)
```

**Create Enum:**
```python
asset = at.create_asset("E_QuestStage", "/Game/Dantooine/Data/Enums", unreal.UserDefinedEnum, unreal.EnumFactory())
```

**Create Struct:**
```python
asset = at.create_asset("ST_DialogueLine", "/Game/Dantooine/Data/Structs", unreal.UserDefinedStruct, unreal.StructureFactory())
```

**Create Blueprint Interface:**
```python
asset = at.create_asset("BPI_Interactable", "/Game/Dantooine/Interfaces", unreal.Blueprint, unreal.BlueprintInterfaceFactory())
```

**Create Input Action:**
```python
asset = at.create_asset("IA_Jump", "/Game/Dantooine/Data/Input", unreal.InputAction, unreal.InputAction_Factory())
```

**Create Input Mapping Context:**
```python
asset = at.create_asset("IMC_Dantooine", "/Game/Dantooine/Data/Input", unreal.InputMappingContext, unreal.InputMappingContext_Factory())
```

**Create Level Sequence:**
```python
asset = at.create_asset("LS_LightsaberBuild", "/Game/Dantooine/Sequences/LightsaberBuild", unreal.LevelSequence, unreal.LevelSequenceFactoryNew())
```

**Create Folder:**
```python
unreal.EditorAssetLibrary.make_directory("/Game/Dantooine/NewFolder")
```

**List All Assets:**
```python
assets = unreal.EditorAssetLibrary.list_assets("/Game/Dantooine", recursive=True, include_folder=False)
for a in sorted(assets): print(a)
```

**Check Asset Exists:**
```python
exists = unreal.EditorAssetLibrary.does_asset_exist("/Game/Dantooine/Blueprints/Core/BP_DantooineGameMode")
print("EXISTS" if exists else "MISSING")
```

**Save All Modified Assets:**
```python
unreal.EditorAssetLibrary.save_directory("/Game/Dantooine", recursive=True)
```

**Get All Level Actors:**
```python
world = unreal.EditorLevelLibrary.get_editor_world()
actors = unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors: print(a.get_actor_label(), a.get_class().get_name())
```

---

### 12. New Commands (Priority 1–3 Implementation)

#### `add_blueprint_function_with_pins`
Create a new function graph with typed input and output pins in one call.
```bash
python3 sandbox_ue5cli.py add_blueprint_function_with_pins '{
  "blueprint_name": "BP_PlayerJediCharacter",
  "function_name": "TakeDamage",
  "inputs":  [{"name": "DamageAmount", "type": "Float"},
              {"name": "DamageSource",  "type": "Object", "sub_type": "Actor"}],
  "outputs": [{"name": "NewHealth",    "type": "Float"},
              {"name": "bIsDead",      "type": "Boolean"}]
}'
```
| Parameter | Required | Notes |
|---|---|---|
| `blueprint_name` | ✅ | |
| `function_name` | ✅ | Must be unique within the Blueprint |
| `inputs` | ❌ | Array of `{name, type, [sub_type]}` |
| `outputs` | ❌ | Array of `{name, type, [sub_type]}` |
Returns: `{success, function_name, graph_name, entry_node_id, result_node_id}`
> After creation, use `add_blueprint_function_node` with `function_name` to call this function from other graphs, or use `get_blueprint_nodes` with `graph_name: "TakeDamage"` to add logic inside the function.

---

#### `get_blueprint_variables`
List all member variables declared on a Blueprint.
```bash
python3 sandbox_ue5cli.py get_blueprint_variables '{"blueprint_name": "BP_PlayerJediCharacter"}'
```
Optional: `"category": "Combat"` to filter by category.

Returns array of `{name, type, sub_type, default_value, category, is_exposed, is_editable, is_replicated, is_array, is_map, is_set}`

---

#### `get_blueprint_functions`
List all function graphs (and macro graphs) on a Blueprint.
```bash
python3 sandbox_ue5cli.py get_blueprint_functions '{"blueprint_name": "BP_PlayerJediCharacter"}'
```
Returns array of `{name, graph_type, inputs:[{name,type}], outputs:[{name,type}], is_pure, node_count}`

---

#### `set_blueprint_parent_class`
Reparent a Blueprint to a new parent class (Blueprint or C++ class).
```bash
python3 sandbox_ue5cli.py set_blueprint_parent_class '{
  "blueprint_name":  "BP_RoamingNPC_StudentA",
  "new_parent_class": "BP_RoamingNPC_Base"
}'
```
| Parameter | Notes |
|---|---|
| `blueprint_name` | Target BP to reparent |
| `new_parent_class` | Blueprint asset name (e.g. `BP_RoamingNPC_Base`) OR C++ class name (e.g. `Character`) |
Returns: `{success, blueprint, old_parent, new_parent}`
> ⚠️ Reparenting can break existing nodes if the new parent class is missing variables/functions the BP uses. Always compile and check for errors after reparenting.

---

#### `set_behavior_tree_blackboard`
Link a Blackboard asset to a Behavior Tree asset.
```bash
python3 sandbox_ue5cli.py set_behavior_tree_blackboard '{
  "behavior_tree_name": "BT_RoamingNPC",
  "blackboard_name":    "BB_RoamingNPC"
}'
```
> Both parameters are asset names only (not full paths). Use this immediately after `create_behavior_tree` + `create_blackboard`.

---

#### `add_niagara_component`
Add a NiagaraComponent to a Blueprint's component hierarchy.
```bash
python3 sandbox_ue5cli.py add_niagara_component '{
  "blueprint_name":       "BP_LightsaberWorkbench",
  "component_name":       "SparksEffect",
  "niagara_system_path":  "/Game/Dantooine/Art/FX/NS_WorkbenchSparks"
}'
```
| Parameter | Required | Notes |
|---|---|---|
| `blueprint_name` | ✅ | |
| `component_name` | ✅ | Variable name for the component |
| `niagara_system_path` | ❌ | Full content path to an NS_ asset. If omitted, component is created with no system assigned. |
> Requires the **Niagara** plugin to be enabled in the project.

---

#### `add_spawn_niagara_at_location_node`
Add a `SpawnSystemAtLocation` node from `UNiagaraFunctionLibrary` to a Blueprint graph.
```bash
python3 sandbox_ue5cli.py add_spawn_niagara_at_location_node '{
  "blueprint_name":      "BP_LightsaberWorkbench",
  "graph_name":          "EventGraph",
  "niagara_system_path": "/Game/Dantooine/Art/FX/NS_WorkbenchSparks",
  "node_position":       {"x": 600, "y": 0}
}'
```
Output pins: `execute` (exec in), `then` (exec out), `SystemTemplate` (NS_ asset ref), `Location`, `Rotation`, `Scale`, `bAutoDestroy`, Return Value (`UNiagaraComponent*`)

---

#### `add_anim_notify`
Add an AnimNotify or AnimNotifyState marker to an Animation Sequence or Montage.
```bash
python3 sandbox_ue5cli.py add_anim_notify '{
  "animation_path": "/Game/Dantooine/Animation/Montages/AM_LightsaberAttack",
  "notify_name":    "HitDetection",
  "time":           0.45
}'
```
**For AnimNotifyState (with duration):**
```bash
python3 sandbox_ue5cli.py add_anim_notify '{
  "animation_path":           "/Game/Dantooine/Animation/Montages/AM_LightsaberAttack",
  "notify_name":              "HitWindow",
  "time":                     0.3,
  "notify_type":              "notify_state",
  "notify_state_duration":    0.25
}'
```
| Parameter | Required | Notes |
|---|---|---|
| `animation_path` | ✅ | Full content path to AN_ or AM_ asset |
| `notify_name` | ✅ | Name for the notify (no class prefix needed) |
| `time` | ✅ | Time in seconds from animation start |
| `notify_type` | ❌ | `"notify"` (default) or `"notify_state"` |
| `notify_state_duration` | ❌ | Duration in seconds (only for notify_state, default 0.1) |

---

#### `set_material_instance_parameter`
Set a scalar, vector, or texture parameter on a Material Instance Constant asset.
```bash
# Scalar
python3 sandbox_ue5cli.py set_material_instance_parameter '{
  "material_instance_path": "/Game/Dantooine/Art/Materials/MI_LightsaberBlade",
  "parameter_name":         "EmissiveIntensity",
  "parameter_type":         "scalar",
  "value":                  "5.0"
}'
# Vector (R,G,B,A)
python3 sandbox_ue5cli.py set_material_instance_parameter '{
  "material_instance_path": "/Game/Dantooine/Art/Materials/MI_LightsaberBlade",
  "parameter_name":         "BladeColor",
  "parameter_type":         "vector",
  "value":                  "0.0,0.5,1.0,1.0"
}'
# Texture
python3 sandbox_ue5cli.py set_material_instance_parameter '{
  "material_instance_path": "/Game/Dantooine/Art/Materials/MI_GroundSurface",
  "parameter_name":         "DiffuseTexture",
  "parameter_type":         "texture",
  "value":                  "/Game/Dantooine/Art/Textures/T_Ground_D"
}'
```
| `parameter_type` | `value` format |
|---|---|
| `scalar` | Number as string: `"5.0"` |
| `vector` | `"R,G,B,A"` as floats 0–1: `"0.0,0.5,1.0,1.0"` |
| `texture` | Full content path to a T_ asset |

---

#### `set_sequencer_track`
Add actor tracks and keyframes to a Level Sequence asset.
```bash
python3 sandbox_ue5cli.py set_sequencer_track '{
  "sequence_path": "/Game/Dantooine/Sequences/LightsaberBuild/LS_LightsaberBuild",
  "actor_name":    "BP_LightsaberWorkbench_0",
  "track_type":    "Transform",
  "keyframes": [
    {"time": 0.0, "location": {"x":0,"y":0,"z":0},   "rotation": {"pitch":0,"yaw":0,"roll":0}},
    {"time": 2.0, "location": {"x":0,"y":0,"z":100},  "rotation": {"pitch":0,"yaw":180,"roll":0}},
    {"time": 4.0, "location": {"x":0,"y":0,"z":0},   "rotation": {"pitch":0,"yaw":360,"roll":0}, "scale": {"x":1,"y":1,"z":1}}
  ]
}'
```
| Parameter | Required | Notes |
|---|---|---|
| `sequence_path` | ✅ | Full content path OR asset name only |
| `actor_name` | ✅ | Actor label as placed in the level |
| `track_type` | ❌ | `"Transform"` (default, currently only supported type) |
| `keyframes` | ❌ | Array of keyframe objects |
> The actor must be **placed in the level** before calling this — the command creates a possessable binding by name. `location`, `rotation`, and `scale` are all optional per keyframe (unset channels stay at default).

---

## WORKFLOW PATTERNS FOR AI AGENTS

### Pattern A: Complete Blueprint Graph Build
```
Step 1: exec_python → create_asset (if Blueprint doesn't exist)
Step 2: get_blueprint_nodes (see what already exists)
Step 3: add_blueprint_event_node (ReceiveBeginPlay or ReceiveTick)
Step 4: add_blueprint_function_node (each function call)
Step 5: add_blueprint_variable_get/set_node (each variable)
Step 6: add_blueprint_branch_node (if needed)
Step 7: get_blueprint_nodes AGAIN (get all node IDs and pin names)
Step 8: connect_blueprint_nodes (exec wires first, then data wires)
Step 9: compile_blueprint
Step 10: get_blueprint_nodes (verify connections correct)
```

### Pattern B: Tick-Driven Movement
```
Event Tick (DeltaSeconds out)
→ GetActorForwardVector (ReturnValue out)
→ Multiply (A=ForwardVector, B=Speed variable)
→ Multiply Again (A=result, B=DeltaSeconds) ← MANDATORY
→ AddActorWorldOffset (input: DeltaOffset)
```

### Pattern C: BeginPlay → SpawnDefaultController (AI)
```
Event BeginPlay → SpawnDefaultController
[For AI pawns spawned at runtime — not placed in editor]
```

### Pattern D: BeginPlay → Run Behavior Tree (AIController)
```
Event BeginPlay → Run Behavior Tree (BT: BT_RoamingNPC)
```

### Pattern E: Float Velocity Movement (Floating Pawn)
```
Event Tick (DeltaSeconds, then)
→ GetActorForwardVector (ReturnValue)
→ GET Speed variable (Speed)
→ Multiply (A=ReturnValue, B=Speed) → result
→ GET FloatingPawnMovement (FloatingPawnMovement)
→ SET FloatingPawnMovement.Velocity
  ├── self pin ← FloatingPawnMovement GET
  └── Velocity pin ← Multiply result
→ compile
```

### Pattern F: Safe Actor Reference
```
GetPlayerCharacter → Cast To BP_PlayerJediCharacter
  Cast Succeeded → As BP_PlayerJediCharacter → [use reference]
  Cast Failed → IsValid → (stop — don't crash)
Cache result: SET PlayerRef variable — don't cast on every Tick
```

### Pattern G: Create Widget HUD
```
[In PlayerController BeginPlay]
Create Widget (Class: WBP_HUD, Owning Player: self)
→ Store result in HUDRef variable
→ Add to Viewport
```

### Pattern H: Batch Asset Creation (exec_python)
```python
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary

# Create all folders
folders = [
    "/Game/Dantooine/AI/Tasks",
    "/Game/Dantooine/AI/Services",
    "/Game/Dantooine/AI/Decorators",
]
for f in folders:
    eal.make_directory(f)
    print(f"DIR: {f}")

# Create assets
assets_to_create = [
    ("BTT_FinishTask", "/Game/Dantooine/AI/Tasks", unreal.BTTask_BlueprintBase),
]
for name, path, parent in assets_to_create:
    f = unreal.BlueprintFactory()
    f.set_editor_property("parent_class", parent)
    a = at.create_asset(name, path, unreal.Blueprint, f)
    print(f"{'OK' if a else 'FAIL'}: {path}/{name}")
```

---

## ERROR REFERENCE

| Error | Cause | Fix |
|---|---|---|
| `Missing 'name' parameter` | `create_blueprint` uses `name` not `blueprint_name` | Use `name` key |
| `Missing 'source_pin'` | Wrong pin param name | Use `source_pin` and `target_pin` |
| `Unknown command` | Command not in plugin | Use `exec_python` instead |
| `Blueprint not found` | Wrong name or doesn't exist | Check with `does_asset_exist` |
| `Property not found` | Wrong C++ property name | Check UE docs for exact name |
| `Pin not found` | Wrong pin name | Use `get_node_info` to see actual pins |
| `Graph not found` | Capitalization wrong | Use `EventGraph` (capital E and G) |
| Compile error after changes | Unconnected required pin | Check all required pins are wired |
| Velocity = 0 at runtime | CDO default not set | Call `set_blueprint_variable_default` |
| AI doesn't move after spawn | No AIController | Call `SpawnDefaultController` in BeginPlay |
| `self` pin on SET node | Internal UE naming | `self` IS the component Target — wire GET to it |
| Speed ignores frame rate | Missing Delta Time | Multiply ALL per-frame values by DeltaSeconds |
| Widget not visible | Not added to viewport | Call `Add to Viewport` after `Create Widget` |
| Anim BP has no skeleton | Created without skeleton | Open ABP, assign skeleton after importing SK_ mesh |
| Cast returns null | Cast Failed path not handled | Always wire Cast Failed → IsValid → stop gracefully |

---

## NAMING CONVENTIONS (MANDATORY)

| Prefix | Asset Type | Example |
|---|---|---|
| `BP_` | Blueprint Class | `BP_PlayerJediCharacter` |
| `WBP_` | Widget Blueprint | `WBP_HUD` |
| `BPI_` | Blueprint Interface | `BPI_Interactable` |
| `ABP_` | Animation Blueprint | `ABP_PlayerJedi` |
| `BT_` | Behavior Tree | `BT_RoamingNPC` |
| `BB_` | Blackboard | `BB_RoamingNPC` |
| `BTT_` | BT Task Blueprint | `BTT_FindRandomPatrol` |
| `BTD_` | BT Decorator Blueprint | `BTD_CanSeePlayer` |
| `BTS_` | BT Service Blueprint | `BTS_UpdatePlayerLocation` |
| `E_` | Enum | `E_QuestStage` |
| `ST_` | Struct | `ST_DialogueLine` |
| `DA_` | Data Asset | `DA_WeaponConfig` |
| `DT_` | Data Table | `DT_DialogueLines` |
| `IA_` | Input Action | `IA_Jump` |
| `IMC_` | Input Mapping Context | `IMC_Dantooine` |
| `LS_` | Level Sequence | `LS_LightsaberBuild` |
| `NS_` | Niagara System | `NS_SaberTrail` |
| `M_` | Material | `M_MasterOpaque` |
| `MI_` | Material Instance | `MI_PlayerJedi` |
| `T_` | Texture | `T_PlayerJedi_D` |
| `SK_` | Skeletal Mesh | `SK_PlayerJedi` |
| `SM_` | Static Mesh | `SM_LightsaberWorkbench` |
| `AN_` | Animation Sequence | `AN_Player_Walk` |
| `AM_` | Animation Montage | `AM_LightsaberAttack` |
| `BS_` | Blend Space | `BS_Locomotion` |
| `AC_` | Actor Component | `AC_HealthSystem` |
| `BFL_` | Blueprint Function Library | `BFL_DantooineHelpers` |

---
