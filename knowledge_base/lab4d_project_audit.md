# Lab4D Project Audit
> Project: `C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam115\UnrealProject\Lab4D`
> Audit date: 2026-04-29
> Status: Phase 2 live MCP audit completed after enabling the Lab4D `UnrealMCP` plugin.

## Connection And Recovery Notes

Initial Phase 2 attempts failed because `Lab4D.uproject` had `"UnrealMCP": false` and the UE bridge port `127.0.0.1:55557` was closed. The project file was updated to enable `UnrealMCP`, Lab4D was launched in UE 5.6, and the bridge then accepted connections.

Raw snapshots were written by MCP scripts to:

- `C:/Users/NewAdmin/Documents/Academy of Art University/2026/Gam115/UnrealProject/Lab4D/Saved/MCP/phase2_snapshot.json`
- `C:/Users/NewAdmin/Documents/Academy of Art University/2026/Gam115/UnrealProject/Lab4D/Saved/MCP/phase2_blueprint_graphs.json`

## Levels

- Total level assets found: `1`
- Current open level: `/Game/Lab-0X.Lab-0X`
- Level asset: `/Game/Lab-0X`
- World Partition: enabled
- Prior editor log map check: `0 Error(s), 0 Warning(s)`

## Asset Summary

- Total `/Game` assets: `659`
- Blueprint assets: `8`
- Animation Blueprints: `4`
- Widget Blueprints: `0`
- AI assets (`BT_`, `BB_`, EQS, BehaviorTree, Blackboard): `0`
- Enhanced Input assets: `8` Input Actions, `1` Input Mapping Context, plus one redirector named `IMC_Default`
- Static meshes: `447`
- Skeletal meshes: `11`
- Animation sequences: `39`
- Materials/material instances: `13`

Blueprint assets:

- `/Game/ArtAssets/Environments/Conveyor/LabWall`
- `/Game/Blueprints/BP_Bullet`
- `/Game/Blueprints/BP_DefenseLaser`
- `/Game/Blueprints/BP_DroneFactory`
- `/Game/Blueprints/BP_LaserTurret`
- `/Game/Blueprints/BP_PacifistDrone`
- `/Game/Blueprints/BP_WarDrone`
- `/Game/ThePlayerCharacter`

Animation Blueprint assets:

- `ABP_Manny`
- `ABP_Quinn`
- `ABP_Manny_PostProcess`
- `ABP_Quinn_PostProcess`

## Actor Summary

- Total actors in current level: `30`
- Gameplay actors:
  - `ThePlayerCharacter`: 1
  - `BP_DefenseLaser`: 9
  - `BP_DroneFactory`: 1
  - `BP_LaserTurret`: 1
  - `BP_PacifistDrone`: 1
  - `BP_WarDrone`: 1
  - `LabWall`: 4
- Environment/editor actors:
  - `DirectionalLight`: 3
  - `StaticMeshActor`: 2
  - `SkyLight`, `SkyAtmosphere`, `VolumetricCloud`, `ExponentialHeightFog`, `PostProcessVolume`
  - `WorldDataLayers`, `WorldPartitionMiniMap`

## Player Character Setup

The current level contains a placed `ThePlayerCharacter_C` at approximately `(-29.124, 794.195, 90)`, yaw `-90`.

Components:

- `CollisionCylinder` / `CapsuleComponent`, collision profile `Custom`
- `CharMoveComp` / `CharacterMovementComponent`
- `CharacterMesh0` / `SkeletalMeshComponent`, collision profile `CharacterMesh`
- `CameraBoom` / `SpringArmComponent`
- `FollowCamera` / `CameraComponent`
- editor camera helper components with `NoCollision`

Variables:

- `PacifistDroneClass`
- `CoreHealth`
- `ShieldCharges`
- `IsDisabled`

Input/action graph evidence:

- `ThePlayerCharacter` has 7 Enhanced Input action nodes.
- Input assets found include `IA_Move`, `IA_Look`, `IA_Jump`, `IA_FirePulse`, `IA_FireShotgun`, `IA_DeployNanomachines`, `IA_Hack`, and `IA_Interact`.
- `IMC_Default` contains mappings to the above actions, though UE Python returned key structs rather than readable key names.
- `DefaultInput.ini` also contains legacy mappings for Jump, Move, Look, and Turn.

## Gameplay Systems Identified

- Player health/shield/disabled state on `ThePlayerCharacter`.
- Pacifist drone deployment and short-circuit behavior.
- War drone movement, damage, and health.
- Drone factory interaction radius and `SpawnWarDrone` function.
- Laser turret tracking/firing/shutdown behavior.
- Defense laser tick-driven sphere tracing and cooldown.
- Bullet projectile movement, overlap damage, and lifespan.

## AI And Navigation

No Behavior Trees, Blackboards, EQS assets, AIControllers, or NavMesh actors/assets were found in the live audit. Drone behavior appears implemented directly in Blueprint Tick/overlap logic rather than UE AI framework assets.

## UI / UMG

No Widget Blueprint assets were found. No UI widgets were identified as being added to the viewport during graph inspection.

## Collision And Physics

Notable collision profiles:

- `LabWall`: visual mesh `NoCollision`, `BoxComponent` `BlockAll`
- `LabFloor`: `BlockAll`
- `BP_DefenseLaser` endpoints: `BlockAllDynamic`
- `BP_DroneFactory`: `FactoryMesh` `BlockAllDynamic`, `InteractRadius` `OverlapAllDynamic`
- `BP_LaserTurret`: turret meshes `BlockAllDynamic`, `HackZone` `OverlapAllDynamic`
- `BP_PacifistDrone` and `BP_WarDrone`: drone mesh `BlockAllDynamic`
- `ThePlayerCharacter`: capsule `Custom`, skeletal mesh `CharacterMesh`
- `BP_Bullet`: bullet mesh configured `NoCollision`; separate `CollisionSphere` component exists for collision behavior

No audited gameplay component was simulating physics.

## Framework Settings

`DefaultEngine.ini` declares:

- Editor startup map: `/Game/Lab-0X.Lab-0X`
- Game default map: `/Game/Lab-0X.Lab-0X`
- Global default GameMode: `/Game/TopDown/Blueprints/BP_TopDownGameMode.BP_TopDownGameMode_C`

The live asset registry did not find a matching TopDown GameMode asset under `/Game`, so the configured GameMode path should be verified in the editor. The level contains a placed `ThePlayerCharacter`, so gameplay may currently rely on the placed pawn rather than a valid GameMode default pawn.

## Issues / Warnings

- Configured global GameMode path appears unresolved in `/Game` asset scan.
- No UI widgets exist despite gameplay systems that may need player feedback.
- No AI framework assets/navmesh were found; drone behavior is Blueprint-driven.
- `BP_DefenseLaser` runs trace/damage logic from Tick, which can be acceptable for hazards but should be profiled if scaled up.
- `BP_Bullet` uses a visible `BulletMesh` with `NoCollision` and a separate `CollisionSphere`; this is intentional only if the sphere is correctly sized and bound.
- Editor logs previously warned that additive `RedBeam` / `GreenBeam` materials are used on Nanite static mesh `arrow-basic`; either disable Nanite on those meshes/components or use an opaque/masked material path.
