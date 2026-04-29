# Lab4D Blueprint Logic Map
> Audit date: 2026-04-29
> Source: live MCP `get_blueprint_graphs`, `get_blueprint_nodes`, `get_blueprint_components`, `get_blueprint_variables`, `get_blueprint_functions`

## Summary

- Blueprint assets found: `8`
- Blueprints with meaningful Event Graph logic: `7`
- Blueprint with only unconnected/default event nodes: `LabWall`
- Widget Blueprints: `0`
- AI Behavior Tree / Blackboard assets: `0`

Raw graph extraction:

- `C:/Users/NewAdmin/Documents/Academy of Art University/2026/Gam115/UnrealProject/Lab4D/Saved/MCP/phase2_blueprint_graphs.json`

## `LabWall`

Components:

- `Box` / `BoxComponent`, collision `BlockAll`
- Native `StaticMeshComponent`

Variables: none.

Graphs:

- `EventGraph`: 3 nodes, only `ReceiveBeginPlay`, `ReceiveTick`, and `ReceiveActorBeginOverlap`; no function calls or variable access found.
- `UserConstructionScript`: function entry only.

Assessment: structural wall Blueprint, no meaningful gameplay graph logic.

## `BP_Bullet`

Components:

- `BulletMesh` / `StaticMeshComponent`, visual mesh uses `RedBeam`, configured `NoCollision`
- `ProjectileMovement`, initial/max speed `2000`, gravity scale `0`
- `CollisionSphere` / `SphereComponent`

Variables: none.

Event Graph:

- Events: `ReceiveBeginPlay`, component begin overlap
- Calls: `SetLifeSpan`, `DealDamage`, `PrintString`, `K2_DestroyActor`
- Casts: one dynamic cast

Behavior: projectile sets a lifespan on spawn, reacts to overlap, calls damage on a cast target, prints debug text, then destroys itself.

## `BP_DefenseLaser`

Components:

- `SourcePointA` / `StaticMeshComponent`
- `SourcePointB` / `StaticMeshComponent`

Variables:

- `bOnCooldown: bool`

Event Graph:

- Event: `ReceiveTick`
- Calls: `K2_GetComponentLocation`, `SphereTraceSingle`, `BreakHitResult`, `DealDamage`, `Delay`, `PrintString`
- Variables read: `SourcePointA`, `SourcePointB`, `bOnCooldown`
- Variables set: `bOnCooldown`
- Casts: one dynamic cast

Behavior: each Tick traces between the two source points, gates damage through `bOnCooldown`, damages a cast target, delays, then clears cooldown. This is the main level hazard system.

## `BP_DroneFactory`

Components:

- `FactoryMesh` / `StaticMeshComponent`, `BlockAllDynamic`
- `InteractRadius` / `SphereComponent`, `OverlapAllDynamic`

Variables:

- `bIsHackable: bool`
- `bPlayerInRange: bool`

Event Graph:

- Events: `InteractRadius` begin overlap, `InteractRadius` end overlap
- Calls: `PrintString`
- Variables set: `bPlayerInRange`
- Casts: two dynamic casts

Function graph `SpawnWarDrone`:

- Calls: `GetTransform`
- Reads: `bPlayerInRange`
- Nodes: function entry, branch, spawn actor from class

Behavior: tracks whether the player is inside the factory interaction radius and exposes a `SpawnWarDrone` function that conditionally spawns a war drone.

## `BP_LaserTurret`

Components:

- `TurretMesh` / `StaticMeshComponent`, `BlockAllDynamic`
- `TurretMesh1` / `StaticMeshComponent`, `BlockAllDynamic`
- `HackZone` / `SphereComponent`, `OverlapAllDynamic`

Variables:

- `bIsHackable: bool`
- `FireRate: real`
- `BulletClass: class`
- `bIsShutdown: bool`

Event Graph:

- Events: `ReceiveBeginPlay`, `ReceiveTick`, component begin overlap, plus custom events
- Calls: `K2_SetTimer`, `GetPlayerPawn`, `K2_GetActorLocation`, `FindLookAtRotation`, `K2_SetActorRotation`, `SphereTraceSingle`, `GetActorForwardVector`, `GetTransform`, `PlaySound2D`, `PrintString`
- Spawns: one `SpawnActorFromClass` node using `BulletClass`
- Variables read: `BulletClass`, `bIsShutdown`
- Variables set: `bIsShutdown`

Behavior: turret starts a timer, rotates toward the player, performs trace/visibility style checks, fires/spawns bullets, plays sound, and can be shut down through hack/overlap logic.

## `BP_PacifistDrone`

Components:

- `DroneMesh` / `StaticMeshComponent`, `BlockAllDynamic`

Variables:

- `MoveSpeed: real`
- `IsShortCircuited: bool`

Event Graph:

- Event: `ReceiveTick`
- Custom event: short-circuit style event
- Calls: `GetActorForwardVector`, `K2_AddActorWorldOffset`, `Multiply_VectorFloat`
- Variables read: `MoveSpeed`, `IsShortCircuited`
- Variables set: `IsShortCircuited`

Function graph `DestroyIfShortCircuited`:

- Reads `IsShortCircuited`
- Branches and calls `K2_DestroyActor`

Behavior: moves forward every Tick unless short-circuited; exposes cleanup behavior when the short-circuit flag is set.

## `BP_WarDrone`

Components:

- `DroneMesh` / `StaticMeshComponent`, `BlockAllDynamic`

Variables:

- `MoveSpeed: real`
- `DroneHealth: int`

Event Graph:

- Event: `ReceiveTick`
- Event: component begin overlap
- Custom event: damage/health style entry point
- Calls: `GetPlayerPawn`, `K2_GetActorLocation`, vector subtract/normalize/multiply, `K2_AddActorWorldOffset`, `DealDamage`, integer subtraction/comparison, `K2_DestroyActor`, `PrintString`
- Variables read: `MoveSpeed`, `DroneHealth`
- Variables set: `DroneHealth`
- Casts: one dynamic cast

Behavior: seeks the player via Tick-driven movement, deals damage on overlap, tracks health, and destroys itself when health reaches zero.

## `ThePlayerCharacter`

Components:

- `CapsuleComponent`
- `CharacterMovementComponent`
- `SkeletalMeshComponent`
- `CameraBoom` / `SpringArmComponent`
- `FollowCamera` / `CameraComponent`

Variables:

- `PacifistDroneClass: class`
- `CoreHealth: real`
- `ShieldCharges: int`
- `IsDisabled: bool`

Event Graph:

- Events: `ReceiveBeginPlay`, `ReceiveControllerChanged`, plus custom events
- Enhanced Input action nodes: 7
- Calls include:
  - Input/setup: `AddMappingContext`, `AddMovementInput`, `Jump`, `StopJumping`
  - Movement/camera math: `GetControlRotation`, `GetForwardVector`, `GetRightVector`
  - Combat/interaction traces: `SphereTraceSingle`, `BreakHitResult`
  - Gameplay calls: `DealDamage`, `DestroyIfShortCircuited`, `ShortCircuit`, `ShutDown`, `SpawnWarDrone`
  - State updates: `DisableMovement`, `K2_DestroyActor`, `Delay`
  - Debug/UI-adjacent: `PrintString`, string/text conversion functions, `PlaySound2D`
- Variables read: `PacifistDroneClass`, `CoreHealth`, `ShieldCharges`, `IsDisabled`, `CharacterMovement`
- Variables set: `CoreHealth`, `ShieldCharges`, `IsDisabled`
- Casts: 7 dynamic casts

Behavior: central gameplay hub. Handles Enhanced Input, movement, jump, combat/trace interactions, drone deployment, hacking/short-circuiting, health/shields, disabled/death state, sound, and debug messaging.

## Communication Map

- `ThePlayerCharacter` calls gameplay functions on level actors after traces/casts:
  - `SpawnWarDrone` on factory
  - `ShutDown` on turret
  - `ShortCircuit` / `DestroyIfShortCircuited` on pacifist drone
  - `DealDamage` on damage-capable actors
- `BP_Bullet`, `BP_DefenseLaser`, and `BP_WarDrone` all call `DealDamage`.
- `BP_DroneFactory`, `BP_LaserTurret`, and `ThePlayerCharacter` use overlap/trace checks and dynamic casts rather than interfaces.

## Risks / Cleanup Opportunities

- Heavy reliance on dynamic casts; Blueprint Interfaces would reduce coupling for hackable/damageable/interactable actors.
- Tick-driven movement/detection in `BP_DefenseLaser`, `BP_WarDrone`, `BP_PacifistDrone`, and `BP_LaserTurret`; acceptable for a small lab but should be profiled or event/timer-driven if expanded.
- Debug `PrintString` calls remain in gameplay graphs.
- No UMG feedback layer exists for health, shields, hack prompts, or disabled/death state.
- No AIController/BT/NavMesh framework; drone behavior is direct Blueprint scripting.
