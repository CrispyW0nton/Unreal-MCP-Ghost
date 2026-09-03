# 10 — Voice Taunts & Combat Audio

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Play voice lines and combat audio at runtime using PlaySoundAtLocation or AudioComponents attached to characters.

## Importing Sound Assets
import_sound_asset source_path: "C:/Assets/Audio/SithTaunt_01.wav" destination: "/Game/EndarSpire/Audio/SFX/SithTaunt_01"

Or via exec_python:
exec_python code: | import unreal task = unreal.AssetImportTask() task.filename = 'C:/Assets/Audio/SithTaunt_01.wav' task.destination_path = '/Game/EndarSpire/Audio/SFX' task.automated = True task.save = True unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

## Playing Sounds in Blueprint
create_node → PlaySoundAtLocation → Sound: SithTaunt_01 → Location: GetActorLocation (self) → VolumeMultiplier: 1.0 → PitchMultiplier: RandRange(0.9, 1.1) for variation

## Random Taunt Selection
add_blueprint_variable → TauntSounds (Array) create_node → GetRandomArrayElement from TauntSounds create_node → PlaySoundAtLocation with the random element

## Existing Sound Variable
BP_SithTrooper already has a `FireSound` variable (SoundBase) used during burst fire.
