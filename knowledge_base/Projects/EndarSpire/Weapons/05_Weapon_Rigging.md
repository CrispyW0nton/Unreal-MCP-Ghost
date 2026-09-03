# 05 — Weapon Rigging & Socket Attachment

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Attach weapon meshes to character skeleton sockets. The Gun component must be a child of the SkeletalMeshComponent (Mesh/CharacterMesh0) and use the correct socket name.

## Existing Sith Trooper Weapon Setup
- Weapon mesh: `/Game/EndarSpire/WeaponModels/Carbine`
- Skeleton sockets:
  - `WeaponSocket` on bone `hand_r`
  - `GunBarrel` on bone `ik_hand_gun`
- Component hierarchy: CapsuleComponent → Mesh → Gun

## Creating a Weapon Socket
exec_python code: | import unreal skel = unreal.load_object(None, '/Game/EndarSpire/Characters/RiggedModels/SithSoldier/SithSoldier_Skeleton') sock = unreal.SkeletalMeshSocket() sock.socket_name = 'WeaponSocket' sock.bone_name = 'hand_r' skel.add_socket(sock)

## Adding a Weapon Component
add_component blueprint_name: "BP_SithTrooper" component_type: "StaticMeshComponent" component_name: "Gun" parent_component: "Mesh"

Then configure:
set_component_property → StaticMesh = /Game/EndarSpire/WeaponModels/Carbine set_component_property → AttachSocketName = WeaponSocket (via exec_python)

## MCP Limitation
`set_component_parent_socket` can set socket metadata but did NOT reliably reparent the component under the native Mesh component. Always verify visually:
1. Open the Blueprint
2. Confirm Gun is indented under Mesh (CharacterMesh0)
3. Confirm Parent Socket = WeaponSocket
4. If wrong, drag Gun onto Mesh in the Components panel manually

## Compile
compile_blueprint → blueprint_name: "BP_SithTrooper"
