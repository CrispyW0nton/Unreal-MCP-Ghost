# Lab4D Blueprint Logic Map
> Audit date: 2026-04-29
> Status: Live graph extraction blocked because Unreal-MCP is not connected to the editor.

## MCP Graph Extraction Status

The requested `get_blueprint_nodes` pass could not be completed. The MCP server is reachable, but editor-dependent tools report `Not connected to Unreal Engine`, and the Lab4D project file currently has the `UnrealMCP` plugin disabled.

Because of that, this file records only secondary evidence from saved MCP snapshots. It should be replaced with a full graph map after the bridge is restored.

## Blueprints Seen In Saved MCP Data

### `ThePlayerCharacter`

Known defaults:

- `CoreHealth = 100.0`
- `ShieldCharges = 3`
- `IsDisabled = False`
- `PacifistDroneClass = /Game/Blueprints/BP_PacifistDrone`

Expected audit targets after reconnection:

- Input events for movement, jump, shield, drone interaction, and combat
- Health/shield mutation paths
- Drone spawning or references to `BP_PacifistDrone`
- Damage handling and disabled-state transitions

### `BP_DefenseLaser`

Known defaults:

- `SourcePointA = None`
- `SourcePointB = None`
- `bOnCooldown = False`

Expected audit targets after reconnection:

- BeginPlay setup for endpoints
- Tick/timer logic for beam activation
- Collision/trace logic for laser damage
- Cooldown set/reset nodes

### `BP_PacifistDrone`

Known defaults:

- `IsShortCircuited = False`

Expected audit targets after reconnection:

- Short-circuit event path
- Interactions with player/war drones/turrets
- AI movement or behavior if present

### `BP_WarDrone`

Known defaults:

- `DroneHealth = 5`

Expected audit targets after reconnection:

- Damage and death logic
- Target acquisition
- Movement/AI controller setup
- Communication with factory/turret/player systems

### `BP_DroneFactory`

Known defaults:

- `bPlayerInRange = False`

Expected audit targets after reconnection:

- Begin/end overlap events
- Spawn actor nodes
- Spawn cooldown/limits
- Player interaction gating

### `BP_LaserTurret`

Known defaults:

- `bIsShutdown = False`
- `BulletClass = /Game/Blueprints/BP_Bullet`

Expected audit targets after reconnection:

- Target detection
- Fire timer or Tick loop
- `SpawnActorFromClass` for `BP_Bullet`
- Shutdown state transitions

### `BP_Bullet`

Known defaults:

- No saved default values captured.

Expected audit targets after reconnection:

- Projectile movement component
- Collision hit/overlap events
- Damage application
- Lifetime/destruction logic

## Known Prior Extraction Failures

Saved MCP files show previous Python API attempts failed with:

- `BlueprintEditorLibrary.get_variable_names` missing
- `unreal.K2Node_CallFunction` missing
- `Blueprint` object missing `ubergraph_pages`

These failures suggest direct Python Blueprint reflection is brittle in this project/UE version. Prefer the native MCP graph tools (`get_blueprint_graphs`, `get_blueprint_nodes`, `bp_get_graph_summary`, `bp_get_graph_detail`) once the bridge is restored.
