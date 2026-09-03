# 11 — Rigging & Skinning Fundamentals

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Reference for skeleton, bone, socket, and physics asset concepts as they apply to the MCP toolset.

## Skeleton Hierarchy
All Endar Spire characters use the UE5 Mannequin-compatible bone naming:
- Root → pelvis → spine_01 → spine_02 → spine_03 → neck_01 → head
- pelvis → thigh_l/r → calf_l/r → foot_l/r → ball_l/r
- spine_03 → clavicle_l/r → upperarm_l/r → lowerarm_l/r → hand_l/r

## Sockets Used in Project
| Socket | Bone | Used By |
|--------|------|---------|
| WeaponSocket | hand_r | BP_SithTrooper Gun component |
| GunBarrel | ik_hand_gun | Projectile spawn point |
| headSocket | head | True first-person camera |

## Physics Assets
Created automatically on skeletal mesh import. Can be customized:
exec_python code: | import unreal pa = unreal.load_asset('/Game/EndarSpire/Characters/RiggedModels/SithSoldier/SithSoldier_PhysicsAsset') # Modify bodies/constraints via PhysicsAssetEditor Python API

## Ragdoll Activation (used in death)
exec_python snippet or Blueprint nodes: → Set Mesh collision enabled (QueryAndPhysics) → Set Mesh simulate physics (true) → Set All Bodies Below Simulate Physics (true) → Disable capsule collision

The native combat director handles this automatically for Sith/Heavy/Republic death sequences.
