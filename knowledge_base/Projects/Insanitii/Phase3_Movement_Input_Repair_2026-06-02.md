# Phase 3 Movement Input Repair

Date: 2026-06-02

## Problem

Manual PIE could not move with WASD or look around with the mouse. This matched an earlier Phase 1 failure mode: the native `AInsanitiiPlayerController` was being used as the runtime controller, replacing the First Person template controller that owns the project movement/look input graph.

## Root Cause

`AInsanitiiGameMode` had been hardened for automation by setting:

```text
PlayerControllerClass = AInsanitiiPlayerController::StaticClass()
```

That satisfied scripted possession probes but regressed manual first-person input. The editor-side Blueprint game mode also needed to be recompiled after reassignment; simply changing the CDO readback was not enough for PIE to launch with the intended controller.

## Fix

Updated the native source of truth:

- `Source/Insanitii/InsanitiiGameMode.cpp` now prefers `/Game/Insanitii/Core/Blueprints/BP_InsanitiiTemplatePlayerController`.
- If that template child is unavailable, it falls back to `/Game/FirstPerson/Blueprints/BP_FirstPersonPlayerController`.
- The default pawn remains `/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter`.
- HUD remains native `AInsanitiiHUD`.

Added `scripts/repair_insanitii_movement_input.py`:

- Assigns `BP_InsanitiiGameMode` to use `BP_InsanitiiTemplatePlayerController`.
- Assigns `BP_FirstPersonCharacter` as the default pawn.
- Keeps `InsanitiiHUD`.
- Sets the current world game mode override to `BP_InsanitiiGameMode`.
- Recompiles and saves the Blueprint game mode.
- Saves the current level.
- Emits an evaluated Unreal readback so the controller assignment is verified without relying on editor stdout capture.

## Live Verification

Repair readback:

```text
game_mode_player_controller = /Game/Insanitii/Core/Blueprints/BP_InsanitiiTemplatePlayerController.BP_InsanitiiTemplatePlayerController_C
game_mode_default_pawn = /Game/FirstPerson/Blueprints/BP_FirstPersonCharacter.BP_FirstPersonCharacter_C
game_mode_hud = /Script/Insanitii.InsanitiiHUD
world_game_mode = /Game/Insanitii/Core/Blueprints/BP_InsanitiiGameMode.BP_InsanitiiGameMode_C
```

PIE runtime report after compiling the repaired Blueprint game mode:

- Status: pass
- Controller: `BP_InsanitiiTemplatePlayerController_C`
- Pawn: `BP_FirstPersonCharacter_C`
- HUD: `InsanitiiHUD`
- Station count: `11`
- Scripted exercise steps: `9`
- Exercise errors: `0`
- Psychosis event fired: `WorldShift`
- Objective completion: `1.0`
- PIE stopped cleanly: `true`
- Blocking dialogs: `0`

## Manual Check

Retest manual Play-in-Editor:

1. WASD movement.
2. Mouse look.
3. `E` interaction prompts from player proximity.
4. HUD controls and mental-state controls still responding while moving.

The automated report proves the correct movement-capable controller is now active in PIE, but physical keyboard/mouse feel still needs a human pass.
