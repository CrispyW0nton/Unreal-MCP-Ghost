# 01 — True First-Person Camera Setup

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Attach a SpringArm + Camera to the head socket of the player's skeletal mesh so the viewport follows the character's head bone. No separate first-person mesh is needed; the third-person body IS the first-person body.

## Endar Spire Correction
Recon on 2026-05-02 found that the old Endar Spire player placeholder path does not exist. Current player work should target `/Game/FirstPerson/Blueprints/BP_TitanCharacter_P1` unless the user explicitly chooses another class. The Destiny-style player Blueprints already have first-person camera/mesh components, so run recon before adding new camera components.

## MCP Tool Sequence

### 1. Add SpringArm component
add_component blueprint_name: "BP_TitanCharacter_P1" component_type: "SpringArmComponent" component_name: "FP_SpringArm" parent_component: "Mesh"

Then set defaults:
set_component_property → TargetArmLength = 0 set_component_property → bDoCollisionTest = false set_component_property → bUsePawnControlRotation = true set_component_property → bInheritPitch = true set_component_property → bInheritYaw = true set_component_property → bInheritRoll = false

### 2. Attach to head socket
exec_python code: | import unreal bp = unreal.load_object(None, '/Game/FirstPerson/Blueprints/BP_TitanCharacter_P1.BP_TitanCharacter_P1') scs = bp.simple_construction_script for node in scs.get_all_nodes(): comp = node.component_template if comp.get_name() == 'FP_SpringArm': comp.set_editor_property('attach_socket_name', 'headSocket') break

### 3. Add Camera component
add_component blueprint_name: "BP_TitanCharacter_P1" component_type: "CameraComponent" component_name: "FP_Camera" parent_component: "FP_SpringArm"

Then:
set_component_property → bUsePawnControlRotation = false (inherits from SpringArm)

### 4. Disable default camera (if one exists)
exec_python code: | import unreal bp = unreal.load_object(None, '/Game/FirstPerson/Blueprints/BP_TitanCharacter_P1.BP_TitanCharacter_P1') scs = bp.simple_construction_script for node in scs.get_all_nodes(): comp = node.component_template if comp.get_name() == 'Camera' and comp.get_class().get_name() == 'CameraComponent': comp.set_editor_property('auto_activate', False) break

### 5. Compile
compile_blueprint → blueprint_name: "BP_TitanCharacter_P1"

Do not call `save_asset` or `SavePackage` from MCP in this project. The user should manually save in Unreal with Ctrl+S after inspection.

## Head Socket Requirement
The skeleton must have a socket named `headSocket` on the `head` bone. If missing:
exec_python code: | import unreal skel = unreal.load_object(None, '/Game/EndarSpire/Characters/Player/PlayerSkeleton') sock = unreal.SkeletalMeshSocket() sock.socket_name = 'headSocket' sock.bone_name = 'head' skel.add_socket(sock)

## Key Gotchas
- SpringArm TargetArmLength MUST be 0 for true first-person.
- bDoCollisionTest MUST be false or camera will push out of walls.
- bInheritRoll = false prevents nausea during animations.
- The player mesh Owner No See (bOnlyOwnerSee = false, bOwnerNoSee = true on the head mesh section) prevents seeing inside the head.
