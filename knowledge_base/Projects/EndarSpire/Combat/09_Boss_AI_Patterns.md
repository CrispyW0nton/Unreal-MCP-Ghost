# 09 — Boss AI Patterns (Dark Jedi)

> Project: Endar Spire | Plugin: Unreal-MCP-Ghost (419 tools) | UE 5.6

## Overview
Boss enemies use state-machine-driven AI with multiple attack phases, health thresholds that trigger phase transitions, and unique abilities (force powers, melee combos).

## Design: Dark Jedi Boss

### Stats
Health = 500.0, MaxHealth = 500.0 MeleeDamage = 40.0 ForcePushDamage = 60.0 ForceLightningDamage = 15.0 (per tick, 5 ticks)

### Phase Transitions
| Health % | Phase | Behavior |
|----------|-------|----------|
| 100-75% | Phase 1 | Melee only, slow advance |
| 75-50% | Phase 2 | Melee + Force Push |
| 50-25% | Phase 3 | Melee + Force Push + Force Lightning |
| 25-0% | Phase 4 (Enrage) | All attacks, faster, reduced cooldowns |

### Variables
BossPhase (Integer, default 1) bIsEnraged (bool, default false) ForcePushCooldown (float, default 8.0) LightningCooldown (float, default 12.0) MeleeComboCount (Integer, default 0) MaxMeleeCombo (Integer, default 3)

### AI Pattern
Tick/Timer: → Check Health / MaxHealth ratio → Update BossPhase → If BossPhase >= 4: Set bIsEnraged = true, reduce cooldowns by 50% → Choose attack based on phase + distance + cooldowns: → Close range: Melee combo (play montage per swing) → Mid range + Phase >= 2: Force Push (launch player) → Any range + Phase >= 3: Force Lightning (damage-over-time channel) → Between attacks: advance toward player

### Death
Die: → Stop all timers → Play death montage → Disable collision → Delay → Enable ragdoll → Trigger objective completion event

## Timer Callbacks — All Zero Parameters
ResetForcePushCooldown (zero params) → bCanForcePush = true ResetLightningCooldown (zero params) → bCanLightning = true ResetMeleeCombo (zero params) → MeleeComboCount = 0
