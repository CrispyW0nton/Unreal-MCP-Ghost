# BP_RepublicSoldierV1 Framework Log

Last updated: 2026-04-27

This document tracks the current handoff state for `BP_RepublicSoldier`, the friendly Republic ally derived from `BP_SithTrooper`. Treat this as the working truth before continuing animation retargeting, Blueprint configuration, and combat testing.

## Primary Assets

- Source Blueprint: `/Game/EndarSpire/AI/SithV2/BP_SithTrooper`
- New Blueprint: `/Game/EndarSpire/AI/RepublicV1/Blueprints/BP_RepublicSoldier`
- New health widget: `/Game/EndarSpire/AI/RepublicV1/Blueprints/BPW_RepublicSoldierHP`
- Republic skeletal mesh: `/Game/EndarSpire/Characters/RiggedModels/RepublicSoldier/RepublicSoldier`
- Republic skeleton: `/Game/EndarSpire/Characters/RiggedModels/RepublicSoldier/RepublicSoldier_Skeleton`
- Republic material: `/Game/EndarSpire/Characters/RiggedModels/RepublicSoldier/RepublicSoldierMale_basecolor_Mat`
- AI controller currently assigned: `/Game/EndarSpire/AI/Sith/BP_SithSoldierController`
- Native combat director: `SithCombatDirectorTick` in `unreal_plugin/Source/UnrealMCP/Private/UnrealMCPBridge.cpp`

## Current Asset State

- `/Game/EndarSpire/AI/RepublicV1/Blueprints/BP_RepublicSoldier` was duplicated from `/Game/EndarSpire/AI/SithV2/BP_SithTrooper`.
- `/Game/EndarSpire/AI/RepublicV1/Blueprints/BPW_RepublicSoldierHP` was duplicated from `/Game/EndarSpire/AI/SithV2/BPW_SithTrooperHP`.
- `BP_RepublicSoldier` has been configured with:
  - `Health = 40.0`
  - `MaxHealth = 40.0`
  - `AutoPossessAI = Placed in World or Spawned`
  - `AIControllerClass = BP_SithSoldierController`
  - Mesh set to the Republic Soldier skeletal mesh
- `BP_RepublicSoldier` was restored from `/Game/EndarSpire/AI/SithV2/BP_SithTrooper` after recon showed the previous short-name-resolved Republic asset only had a 24-node overlap/blackboard graph instead of the 395-node Sith combat surface.
- `BP_RepublicSoldier` mesh Anim Class is assigned to `/Game/EndarSpire/AI/RepublicV1/Blueprints/ABP_RepublicSoldier.ABP_RepublicSoldier_C`.
- Removed the temporary `/Game/ABP_RepublicSoldier_PreFixBackup` asset because it preserved the known-bad Blendspace Player reference and caused project compile noise.
- MCP compile currently uses the safe deferred-compile path. Open the Blueprint in Unreal and compile/save manually after editor-side retargeting/configuration.

## Folder Structure

Created and verified:

- `/Game/EndarSpire/AI/RepublicV1/`
- `/Game/EndarSpire/AI/RepublicV1/Blueprints/`
- `/Game/EndarSpire/Characters/RepublicSoldier/Animations/`
- `/Game/EndarSpire/Characters/RepublicSoldier/Animations/Locomotion/`
- `/Game/EndarSpire/Characters/RepublicSoldier/Animations/Locomotion/RetargetedRepublic/`
- `/Game/EndarSpire/Characters/RepublicSoldier/Materials/`

## Native Director Support

The plugin source has been updated so the native director recognizes Republic soldiers separately from Sith troopers.

- Sith troopers remain player-targeted.
- Republic soldiers are recognized by class path under `RepublicV1` and target visible `BP_SithTrooper` actors.
- Republic soldiers do not have the Sith AnimBP forced onto their mesh by the native director.
- The native director still calls `FireOneShot`, drives combat movement, and updates AnimBP variables through the duplicated Sith combat variable surface.
- Republic `PawnSensing` is disabled at runtime so the duplicated Sith `OnPawnSeen` graph cannot react to the player; the native director supplies the Sith target instead.
- Republic health bars are updated natively by reading `Health`/`MaxHealth`, setting the progress bar percent, and applying a green fill color.
- Both Sith and Republic deaths now play faction death montages before native ragdoll activation.

Build status:

- `_sync_plugin.bat && _build_plugin.bat` succeeded after the Live Coding mutex cleared.
- The sync script still prints a missing `unreal_plugin/Resources` warning, but the plugin build succeeds.
- Latest `_sync_plugin.bat && _build_plugin.bat` attempt was blocked by active Unreal Live Coding. Close Unreal or press `Ctrl+Alt+F11` in the editor to compile the native changes.

## Recon Findings

Republic import folder contains:

- Skeletal mesh: `RepublicSoldier`
- Skeleton: `RepublicSoldier_Skeleton`
- Material: `RepublicSoldierMale_basecolor_Mat`
- Texture: `RepublicSoldierMale_basecolor`
- Physics asset: none assigned

Sith animation source set contains all requested combat animations/montages plus exactly `50` `RT_Sith_*` locomotion assets.

Existing older friendly assets were found in:

- `/Game/EndarSpire/AI/Friendly/`
- `/Game/EndarSpire/Characters/Friendly/`

Those older assets appear to be a separate Cabal-style friendly setup and do not carry the Sith combat variables needed for this RepublicV1 approach.

## Animation Retargeting Status

Completed:

- Created and verified `RTG_Sith_to_Republic`; preview poses look correct in the retargeter.
- Retargeted the requested Sith combat animations into `/Game/EndarSpire/Characters/RepublicSoldier/Animations/`.
- Retargeted all `50` `RT_Sith_*` locomotion animations into `/Game/EndarSpire/Characters/RepublicSoldier/Animations/Locomotion/RetargetedRepublic/`.
- Created montage assets:
  - `RT_Republic_Rifle_Down_To_Aim_Montage`
  - `RT_Republic_Rifle_Aim_To_Down_Montage`
  - `RT_Republic_Grenade_Throw_Montage`
  - `RT_Republic_Fire_Rifle_Montage`
- Created `/Game/EndarSpire/Characters/RepublicSoldier/Animations/Locomotion/BS_Republic_8Dir_Locomotion`.
- Removed failed automated AnimBP-retarget duplicate clutter from `/Game/EndarSpire/AI/RepublicV1/Blueprints/`.
- Created `/Game/EndarSpire/AI/RepublicV1/Blueprints/ABP_RepublicSoldier` on the Republic Soldier skeleton.
- Repaired `/Game/EndarSpire/AI/RepublicV1/Blueprints/ABP_RepublicSoldier` after a `Blendspace Player references an unknown Blend Space` compile failure:
  - Removed two invalid Blendspace Player nodes from `AnimGraph`.
  - Added one new Blendspace Player node that references `/Game/EndarSpire/Characters/RepublicSoldier/Animations/Locomotion/BS_Republic_8Dir_Locomotion`.
  - `compile_blueprint` reports no errors through MCP's deferred compile path.
- Created death montages:
  - `/Game/EndarSpire/Characters/Sith/Animations/Locomotion/SithRetargeted/A_Sith_Death_Montage`
  - `/Game/EndarSpire/Characters/RepublicSoldier/Animations/Locomotion/RetargetedRepublic/RT_Republic_Death_Montage`

Pending editor-side work:

- Open `/Game/EndarSpire/AI/RepublicV1/Blueprints/ABP_RepublicSoldier`, press Compile, then save to confirm the editor-side full compile also passes.

## Health Widget Status

- `BPW_RepublicSoldierHP` exists as a duplicate of `BPW_SithTrooperHP`.
- Native director now sets Republic health bar progress to `Health / MaxHealth` and applies a green fill color at runtime.
- MCP still cannot reliably find `HealthBarWidgetComp` on the Blueprint template, so runtime widget handling remains the safer path.

## Behavior Goals

Expected final behavior:

- Friendly to the player.
- Never targets or attacks the player.
- Targets and fights nearby `BP_SithTrooper` actors.
- Low health ally: dies after a few Sith projectile hits.
- Uses Republic mesh and Republic-retargeted locomotion/combat animations.
- Uses green health bar for visual distinction.

## Pending Test Checklist

After retargeting and manual Blueprint compile/save:

- Place one `BP_RepublicSoldier` near one `BP_SithTrooper`.
- Confirm the Republic Soldier ignores the player.
- Confirm the Republic Soldier targets the Sith Trooper.
- Confirm projectiles fire toward the Sith Trooper.
- Confirm green health bar appears and updates.
- Confirm `Health = 40` makes the Republic Soldier fragile.
- Confirm the Sith Trooper still targets the player normally.
- Test 3 Republic Soldiers and 3 Sith Troopers for stability.

## Current Blocking Work

The remaining blocking work is native compilation plus editor-side verification:

- Compile the plugin after Live Coding is cleared.
- Manual Blueprint compile/save inside Unreal.
- Playtest Republic vs Sith combat and death animation timing.
