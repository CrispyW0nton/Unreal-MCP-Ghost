# 04 — Sequencer & Animation Playback

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Use Level Sequencer for cutscenes, camera work, and baked animation. For runtime animation, use Animation Montages played through AnimBP slots.

## Creating a Level Sequence
exec_python code: | import unreal factory = unreal.LevelSequenceFactoryNew() asset_tools = unreal.AssetToolsHelpers.get_asset_tools() seq = asset_tools.create_asset('LS_Intro', '/Game/EndarSpire/Sequences', None, factory)

## Adding an actor to a Sequence
exec_python code: | import unreal seq = unreal.load_asset('/Game/EndarSpire/Sequences/LS_Intro') world = unreal.EditorLevelLibrary.get_editor_world() actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Character) for a in actors: if 'BP_SithTrooper' in a.get_name(): binding = seq.add_possessable(a) break

## Runtime Montage Playback (preferred for gameplay)
Play a montage from Blueprint logic:
create_node blueprint_name: "BP_SithTrooper" node_type: "PlayMontage" → connect MontageToPlay pin to the animation montage asset → connect Target pin to Mesh → GetAnimInstance

Or through the native combat director calling:
CallBlueprintEvent(Trooper, TEXT("FireOneShot"))

which internally triggers montage play.

## Montage Assets Used
| Montage | Purpose |
|---------|---------|
| Rifle_Down_To_Aim_Sith_Montage | Combat entry raise rifle |
| Rifle_Aim_To_Down_Sith_Montage | Combat exit lower rifle |
| A_Sith_Grenade_Throw_Montage | Grenade throw |
| RT_Heavy_Fire_Rifle_Montage | Heavy sustained fire |
| RT_Heavy_Death_Montage | Heavy death before ragdoll |
