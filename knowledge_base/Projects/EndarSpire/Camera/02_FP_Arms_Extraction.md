# 02 — First-Person Arms Extraction & Visibility

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
For true first-person, the full body mesh is always rendered. The player's head and possibly upper torso are hidden from the owning player using Owner No See. Arms stay visible.

## Endar Spire Correction
Recon on 2026-05-02 found the active player target for new work is `/Game/FirstPerson/Blueprints/BP_TitanCharacter_P1`. The existing Destiny-style player Blueprints already include `FirstPersonMesh`, `ThirdPersonMesh`, and weapon mesh components; inspect components before adding duplicate FP arms.

## Approach A — Owner No See on Head (Preferred)

### exec_python: set head material to Owner No See
exec_python code: | import unreal bp = unreal.load_object(None, '/Game/FirstPerson/Blueprints/BP_TitanCharacter_P1.BP_TitanCharacter_P1') scs = bp.simple_construction_script for node in scs.get_all_nodes(): comp = node.component_template if comp.get_name() in ('Mesh', 'CharacterMesh0', 'ThirdPersonMesh'): comp.set_editor_property('owner_no_see', True) break

Note: A more refined approach hides only the head bone's material slots rather than the whole mesh. This requires per-material-slot visibility which UE5 doesn't expose directly — instead, duplicate the mesh into two components (head-only, body-only) and set Owner No See on the head component.

## Approach B — Separate FP Arms Mesh
If the project has a dedicated FP arms skeletal mesh:
add_component blueprint_name: "BP_TitanCharacter_P1" component_type: "SkeletalMeshComponent" component_name: "FP_Arms" parent_component: "FirstPersonCamera"

Then:
set_component_property → bOnlyOwnerSee = true set_component_property → bCastDynamicShadow = false set_component_property → SkeletalMesh =

## Compile
compile_blueprint → blueprint_name: "BP_TitanCharacter_P1"

Do not call `save_asset` or `SavePackage` from MCP in this project. The user should manually save in Unreal with Ctrl+S after inspection.
