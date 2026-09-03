# 08 — Player Force Powers

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Force powers are abilities the player activates via input. Each power has a cooldown managed by a timer. Timer callbacks MUST be zero-parameter custom events (UE bug UE-61800).

## Endar Spire Correction
Recon on 2026-05-02 found player work should target `BP_TitanCharacter_P1`. The input system already has `IA_Super` and `IA_Super2` under `/Game/FirstPerson/Input/Actions/`, mapped through `/Game/FirstPerson/Input/IMC_Default_Destiny`. Use those for force powers unless the user explicitly asks for a new input action.

## Timer Bug UE-61800
When using Set Timer by Function Name, the target function must have ZERO parameters. If the function has parameters, the timer silently fails. Always use separate timer handles and zero-parameter wrapper events.

## Force Push Example

### Variables
add_blueprint_variable → ForcePushCooldown (float, default 5.0) add_blueprint_variable → ForcePushRange (float, default 1500.0) add_blueprint_variable → ForcePushForce (float, default 2000.0) add_blueprint_variable → bCanForcePush (bool, default true) add_blueprint_variable → ForcePushTimerHandle (TimerHandle)

### Input
Use existing input action → IA_Super or IA_Super2. Use existing mapping context → IMC_Default_Destiny.

### Graph Flow
IA_Super or IA_Super2 (Triggered) → Branch: bCanForcePush → Set bCanForcePush = false → SphereOverlapActors at player location + forward * ForcePushRange/2 → For each overlapping actor: → If implements Damageable or is Character: → LaunchCharacter away from player * ForcePushForce → ApplyDamage 50 → Play VFX (SpawnEmitterAtLocation) → Play SFX (PlaySoundAtLocation) → SetTimerByFunctionName("ResetForcePush", ForcePushCooldown)

ResetForcePush (CustomEvent, ZERO parameters): → Set bCanForcePush = true

### CRITICAL: Separate Timer Handles
Every timer-based cooldown needs its OWN TimerHandle variable. Do NOT reuse handles between force push, force pull, force lightning, etc.
