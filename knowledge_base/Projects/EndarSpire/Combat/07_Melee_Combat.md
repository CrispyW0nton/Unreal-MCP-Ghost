# 07 — Melee Combat System

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Melee attacks use Animation Montages with AnimNotifies to trigger damage windows. A sphere trace or overlap check fires during the notify window.

## Endar Spire Correction
Recon on 2026-05-02 found the input action `IA_Melee` already exists under `/Game/FirstPerson/Input/Actions/` and should be used for `BP_TitanCharacter_P1` player melee work. Do not create duplicate melee input or default mapping-context assets. The planned Sith melee trooper variant has been removed from scope for development time; focus future enemy melee work on the Sith Warrior/Dark Jedi boss.

## SithTrooper Melee (Existing)
- `MeleeRange`: float variable, distance threshold
- `MeleeDamage`: float variable, damage per hit
- `CheckCloseRange`: checks distance to TargetActor against MeleeRange
- `JumpAway`: evasion when player is too close (JumpBackForce launch + JumpResetTimerHandle)

## Player Melee Attack Setup

### 1. Create input action
Use existing input action: `/Game/FirstPerson/Input/Actions/IA_Melee`

Use existing mapping context: `/Game/FirstPerson/Input/IMC_Default_Destiny`

### 2. Add variables
add_blueprint_variable → IsAttacking (bool) add_blueprint_variable → MeleeDamage (float, default 25.0) add_blueprint_variable → MeleeRange (float, default 150.0) add_blueprint_variable → AttackMontage (AnimMontage)

### 3. Attack graph flow
IA_Melee (Triggered) → Branch: NOT IsAttacking → Set IsAttacking = true → PlayMontage (AttackMontage, on DefaultSlot) → On Completed: Set IsAttacking = false → On Interrupted: Set IsAttacking = false

### 4. Damage via AnimNotify
Add an AnimNotify `AN_MeleeDamageWindow` at the impact frame of the attack montage.
In the Blueprint, handle the notify:
AnimNotify_AN_MeleeDamageWindow → SphereTraceByChannel from character forward * MeleeRange → For each hit actor: ApplyDamage (MeleeDamage)

## Helper Actor Compatibility
The existing project uses overlap-based helper actors for damage:
- `BP_ApplyDamage` → 15 damage
- `BP_ApplyMeleeDamage` → 50 damage
- `BP_ApplyMeleeDamage_Bash` → 100 damage
BP_SithTrooper has a ReceiveActorBeginOverlap path that recognizes these helpers and calls ApplyDamage on itself.
