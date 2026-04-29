# Lab4D Actor Inventory
> Audit date: 2026-04-29
> Source: live MCP `exec_python` snapshot of `/Game/Lab-0X.Lab-0X`

## Summary

- Total actors: `30`
- Gameplay Blueprint actors: `18`
- Environment/editor actors: `12`
- Current level: `/Game/Lab-0X.Lab-0X`

## Gameplay Actors

| Actor label | Class | Location | Notable components |
| --- | --- | --- | --- |
| `ThePlayerCharacter` | `ThePlayerCharacter_C` | `(-29.124, 794.195, 90)` | Capsule `Custom`, CharacterMovement, SkeletalMesh `CharacterMesh`, SpringArm, Camera |
| `BP_PacifistDrone` | `BP_PacifistDrone_C` | `(-680, 200, 90)` | `DroneMesh` `BlockAllDynamic` |
| `BP_WarDrone` | `BP_WarDrone_C` | `(-690, 110, 80)` | `DroneMesh` `BlockAllDynamic` |
| `BP_DroneFactory` | `BP_DroneFactory_C` | `(-630, 510, 30)` | `FactoryMesh` `BlockAllDynamic`, `InteractRadius` `OverlapAllDynamic` |
| `BP_LaserTurret` | `BP_LaserTurret_C` | `(-640, -100, 30)` | `TurretMesh`, `TurretMesh1` `BlockAllDynamic`, `HackZone` `OverlapAllDynamic` |

## Defense Lasers

All nine defense lasers are `BP_DefenseLaser_C`, scale `(0.5, 0.5, 0.5)`, with `SourcePointA` and `SourcePointB` static mesh components using `BlockAllDynamic`.

| Actor label | Location |
| --- | --- |
| `BP_DefenseLaser` | `(-140, 680, 10)` |
| `BP_DefenseLaser2` | `(-710, 670, 10)` |
| `BP_DefenseLaser3` | `(330, 680, 10)` |
| `BP_DefenseLaser4` | `(330, 370, 10)` |
| `BP_DefenseLaser5` | `(-140, 370, 10)` |
| `BP_DefenseLaser6` | `(-710, 370, 10)` |
| `BP_DefenseLaser7` | `(-710, 70, 10)` |
| `BP_DefenseLaser8` | `(-140, 70, 10)` |
| `BP_DefenseLaser9` | `(330, 70, 10)` |

## Lab Geometry

| Actor label | Class | Location | Collision |
| --- | --- | --- | --- |
| `LabFloor` | `StaticMeshActor` | `(-43.675, 416.765, 0)` | StaticMeshComponent `BlockAll` |
| `LabWall1` | `LabWall_C` | `(793.999, 337.065, 0.004)` | visual mesh `NoCollision`, `Box` `BlockAll` |
| `LabWall2` | `LabWall_C` | `(-883.168, 334.743, 0.004)` | visual mesh `NoCollision`, `Box` `BlockAll` |
| `LabWall3` | `LabWall_C` | `(-63.066, -427.198, 0)` | visual mesh `NoCollision`, `Box` `BlockAll` |
| `LabWall4` | `LabWall_C` | `(-50, 1220, 0)` | visual mesh `NoCollision`, `Box` `BlockAll` |
| `SM_SkySphere` | `StaticMeshActor` | `(-15580, 0, 0)` | `NoCollision` |

## Lighting / Atmosphere / Editor Actors

- `DirectionalLight`, `DirectionalLight2`, `DirectionalLight3`
- `SkyLight`
- `SkyAtmosphere`
- `VolumetricCloud`
- `ExponentialHeightFog`
- `PostProcessVolume`
- `WorldDataLayers`
- `WorldPartitionMiniMap0`

## Notes

- No `NavMeshBoundsVolume` actor was found.
- No actor components audited were simulating physics.
- The level is small and gameplay-focused: one player, one factory, one turret, two drones, nine hazard lasers, four walls, one floor, and environmental lighting/post-process actors.
