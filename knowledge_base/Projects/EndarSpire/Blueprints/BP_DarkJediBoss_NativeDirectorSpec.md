# BP_DarkJediBoss — Native Combat Director Specification
**Date**: 2026-05-03
**Blueprint**: /Game/EndarSpire/AI/SithV2/BP_DarkJediBoss
**AnimBP**: /Game/EndarSpire/AI/SithV2/ABP_DarkJediBoss
**Widget**: /Game/EndarSpire/AI/SithV2/BPW_DarkJediBossHP
**Status**: Ready for C++ implementation

**Recon notes (2026-05-03, live editor via MCP)**
- Event graph: 293 nodes; 19 custom events (includes `UpdateBossPhase`, `Die` plus director table below).
- Character mesh (placed instance `BP_DarkJediBoss_C_1`): `/Game/EndarSpire/Characters/RiggedModels/SithWarrior/SithWarrior1.SithWarrior1`.
- `LightsaberBlade` component default: `bHiddenInGame = true` set on Blueprint; placed Sandbox instance updated in-editor so verification reads `true` (older instances may need delete/re-place if still false).
- Root motion on `ABP_DarkJediBoss`: confirm in Editor **Class Defaults → Root Motion → Root Motion from Everything: Ignore** (MCP `exec_python` could not read `AnimBlueprint` root-motion properties reliably in this environment).

---

## 1. Identification

- **Actor identification**: `IsDarkJediBossActor(AActor* Actor)`
- **Match when**:
  - `Actor->GetPathName()` contains `BP_DarkJediBoss`, **or**
  - `Actor->GetClass()->GetName()` contains `BP_DarkJediBoss_C` (Blueprint generated class).
- **Cardinality**: Design assumes **one** boss instance per active encounter level (Sandbox currently has `BP_DarkJediBoss_C_1`).
- **Dispatch**: In the main combat director tick, evaluate **before** trooper/heavy/Republic branches:

```cpp
if (IsDarkJediBossActor(Actor)) { DarkJediBossDirectorTick(Actor, DeltaTime); }
else if (IsHeavySithTrooperActor(Actor)) { ... }
else if (IsSithTrooperActor(Actor)) { ... }
```

---

## 2. Runtime setup (first tick only)

Perform once when the Dark Jedi boss actor is first registered with the director:

| Action | Detail |
|--------|--------|
| Disable Blueprint tick | `Actor->SetActorTickEnabled(false)` — director owns periodic work |
| Disable PawnSensing | Find `UPawnSensingComponent` by name `PawnSensing`; set `bEnableSensingUpdates = false` (director implements sight + LOS). |
| Movement config | On `UCharacterMovementComponent`: `bOrientRotationToMovement = false`, `bUseControllerDesiredRotation = true`, `RotationRate = FRotator(0.f, 720.f, 0.f)` |
| Health bar setup | Resolve `HealthBarWidgetComp` (`UWidgetComponent`). `UUserWidget* W = HealthBarWidgetComp->GetUserWidget();` If valid, ensure children exist: `UProgressBar* HealthBar` (name `HealthBar`, fill `FLinearColor(0.8f, 0.1f, 0.1f, 1.f)`, percent `1.f`), `UTextBlock* BossNameText` (name `BossNameText`, text `Dark Jedi`, font size 14, white, centered). If widget tree cannot be modified (sealed / empty widget), call Blueprint custom event `ConfigureBossHealthBar` once as fallback. |
| Lightsaber blade | Ensure `LightsaberBlade->SetHiddenInGame(true)` at runtime if not already true (Blueprint BeginPlay also hides). |
| Cache references | `Mesh` (`USkeletalMeshComponent`), `CharacterMovement`, `CapsuleComponent`, `LightsaberBlade`, `LightsaberHandle`, `HealthBarWidgetComp`, `UAnimInstance*` → cast to `UABP_DarkJediBoss_C*` (or native `UAnimInstance` subclass if promoted). |
| Initialize state | Read `BossPhase`, `Health`, `MaxHealth`, `IsDead`. If not dead: set **`BossCombatState = 0` (IDLE)**. **Do not** overwrite `BossPhase` (phase is driven by Blueprint `UpdateBossPhase`). |

---

## 3. Targeting

Run logic every **0.2 s** using an accumulator (not `FTimerHandle`):

| Step | Detail |
|------|--------|
| Player | `APawn* Player = World->GetFirstPlayerController() ? World->GetFirstPlayerController()->GetPawn() : nullptr;` |
| Distance | `float Dist = FVector::Dist(Boss->GetActorLocation(), Player->GetActorLocation());` |
| Acquire | If `Dist < 2000.0` (matches `PawnSensing` SightRadius) **and** line trace Boss eyes → Player `ECC_Visibility`, ignore self: set **`PlayerSeen = true`**, **`TargetActor = Player`**. |
| Lose | If `Dist > 2500.0` **or** LOS fails: track **fail duration**; if failed for **≥ 3.0 s**: `PlayerSeen = false`, `TargetActor = nullptr`, `BossCombatState = IDLE (0)`. |
| First sight | On transition `PlayerSeen: false → true` and **`bSaberActive == false`**: call `PlayDrawSaberMontage`, then `StartTauntLoop`. |

Use `UFunction`/`ProcessEvent` or a thin Blueprint callable dispatcher to invoke custom events by name if hard bindings are undesirable.

---

## 4. State machine

Read/write integer **`BossCombatState`** on the boss Blueprint.

| Value | Name | Meaning |
|------:|------|---------|
| 0 | IDLE | No valid target |
| 1 | ENGAGE | Closing on target |
| 2 | ATTACKING | Melee combo |
| 3 | DISENGAGING | Back off |
| 4 | STRAFING | Orbit / break LOS rhythm |
| 5 | FORCE_PUSH | Push montage + effect |
| 6 | FORCE_LIGHTNING | Lightning montage + DOT |
| 7 | FORCE_PULL_ENGAGE | Pull montage + reposition |
| 8 | DEAD | Boss finished |

### IDLE (0)
- No `TargetActor` / `PlayerSeen == false`. Locomotion `Speed` should trend to 0 via velocity.
- **→ ENGAGE (1)** when `PlayerSeen == true`.

### ENGAGE (1)
- Face target: `LookAt = FindLookAtRotation(BossLoc, TargetLoc)`; `Controller->SetControlRotation(FMath::RInterpTo(Current, LookAt, DeltaTime, 8.f))`.
- Move: `CharacterMovement->MaxWalkSpeed = ChargeSpeed` (float on BP; default `450`; Phase 4 Blueprint may raise to `550`).
- Pathing: `UAIBlueprintHelperLibrary::SimpleMoveToActor` or `MoveTo` with `AcceptanceRadius` appropriate for `MeleeRange`.
- Push **Speed** / **Direction** to AnimBP each frame (see §9).
- **→ ATTACKING (2)** when `Dist < MeleeRange` (default `200`).
- Optional force rolled during approach **Phase 3+** only, if `MeleeRange < Dist < 800` → delegate to §5 → may enter FORCE_* states.

### ATTACKING (2)
- **On enter**: call Blueprint `PlaySlashMontage` (increments combo in BP).
- First tick: `StopMovementImmediately()`.
- Face target (same rotation interp).
- **Damage**: use §6 sphere trace window; apply damage via `UGameplayStatics::ApplyDamage` and/or `ApplyMeleeDamageToPlayer` for parity with BP.
- After **`AttackCooldown`** since enter (default `1.0` s BP; may differ if designer tunes):
  - If `ComboCounter < MaxComboHits` **and** `Dist < MeleeRange * 1.5` → stay in ATTACKING (director triggers next slash by calling `PlaySlashMontage` again on re-entry or same state re-arm).
  - Else **→ DISENGAGING (3)**.

### DISENGAGING (3)
- Direction `(BossLoc - TargetLoc).GetSafeNormal()`; goal `BossLoc + Dir * DisengageDistance` (BP default `1000`; phase 4 may use `600`).
- `MaxWalkSpeed = StrafeSpeed` (default `200`; phase 4 may use `300`).
- Face target throughout.
- **→ STRAFING (4)** when `DistToTarget >= DisengageDistance` **or** `2.0` s elapsed.

### STRAFING (4)
- Perpendicular strafe around target; alternate sign using an internal **strafe sign** flip each cycle.
- `MaxWalkSpeed = StrafeSpeed`.
- Duration **`StrafeDuration`** (default `4.0`; phase 4 may use `2.0`).
- On exit run **§5 Decision Logic**.

### FORCE_PUSH (5)
- Call `PlayForcePushMontage`. Stop movement. Face target.
- At **50%** of montage length (~1.0 s if montage ~2 s): execute push — `LaunchCharacter(Forward * 1200 + Up * 300, …)`, `ApplyDamage(..., 50, …)`, `ApplyForcePushEffect`, play `push` at boss location.
- After **2.0 s** → **STRAFING (4)**.

### FORCE_LIGHTNING (6)
- Call `PlayForceLightningMontage`. Stop movement. Face target.
- **DOT**: `ApplyDamage(..., 15)` every **0.3 s** for **2.0 s**; play `lightning` once at start; call `ApplyForceLightningEffect` on first tick.
- After **2.5 s** → **ENGAGE (1)**.

### FORCE_PULL_ENGAGE (7)
- Call `PlayForcePullMontage`. Stop movement. Face target.
- At **50%** montage: `ApplyForcePullEffect`; move player toward `BossLoc + Forward * (MeleeRange + 50)` over **0.3 s** (`VInterpTo`); `ApplyDamage(..., 20)`; play `pull`.
- After **1.5 s** → **ATTACKING (2)**.

### DEAD (8)
- When `IsDead == true`: clear accumulators, stop movement, **do not** call `Die` or `Play` montages again; remove from tracking.

---

## 5. Decision logic

Run after **STRAFING** and **DISENGAGING** (and optionally from ENGAGE when attempting mid-range force).

```
ChooseNextState(BossPhase, bCanForcePush, bCanForceLightning, bCanForcePull,
                bForcePushOnCooldown, bForceLightningOnCooldown, bForcePullOnCooldown):

  Roll = FRandRange(0.f, 1.f)

  if BossPhase == 1: return ENGAGE

  if BossPhase == 2:
    if bCanForcePush && !bForcePushOnCooldown && Roll < 0.30f: return FORCE_PUSH
    return ENGAGE

  if BossPhase == 3:
    Cumulative = 0.f
    if bCanForcePush && !bForcePushOnCooldown { Cumulative += 0.25f; if (Roll < Cumulative) return FORCE_PUSH }
    if bCanForceLightning && !bForceLightningOnCooldown { Cumulative += 0.20f; if (Roll < Cumulative) return FORCE_LIGHTNING }
    if bCanForcePull && !bForcePullOnCooldown { Cumulative += 0.20f; if (Roll < Cumulative) return FORCE_PULL_ENGAGE }
    return ENGAGE

  if BossPhase == 4:
    // Escalated tuning (mirror Blueprint phase 4)
    SetBlueprintProperty ChargeSpeed = 550.f
    SetBlueprintProperty StrafeSpeed = 300.f
    Cumulative = 0.f
    if bCanForcePush && !bForcePushOnCooldown { Cumulative += 0.30f; if (Roll < Cumulative) return FORCE_PUSH }
    if bCanForceLightning && !bForceLightningOnCooldown { Cumulative += 0.25f; if (Roll < Cumulative) return FORCE_LIGHTNING }
    if bCanForcePull && !bForcePullOnCooldown { Cumulative += 0.25f; if (Roll < Cumulative) return FORCE_PULL_ENGAGE }
    return ENGAGE
```

---

## 6. Melee damage delivery

Director-owned detection (Blueprint `ApplyMeleeDamageToPlayer` remains a thin `ApplyDamage` wrapper for notifies).

```
State ATTACKING:
  Accumulate AttackTime since state entry.

  DamageWindowStart = AttackCooldown * 0.35
  DamageWindowEnd   = AttackCooldown * 0.55

  if AttackTime in [Start, End] && !bDamageAppliedThisSwing:
      Sphere sweep:
        Start  = LightsaberBlade->GetComponentLocation()
        End    = Start + Boss->GetActorForwardVector() * 150.f
        Radius = 50.f
        Channel = ECC_Pawn
        Ignore  = Boss

      if HitPawn == PlayerPawn:
        ApplyDamage(PlayerPawn, MeleeDamage, Controller, Boss, nullptr)
        Optional: call ApplyMeleeDamageToPlayer (same damage — avoid double-damage if BP also applies; prefer single ApplyDamage in C++)
        PlaySoundAtLocation(saberhit or saberhit1, Hit.ImpactPoint, 50/50)
        bDamageAppliedThisSwing = true

  On exit ATTACKING: bDamageAppliedThisSwing = false
```

**Note:** If `AttackCooldown` differs from `1.5 s`, adjust windows accordingly; the formula is always **35%–55%** of `AttackCooldown`.

---

## 7. Force power effects

| Power | Custom events | Director action | Damage | Sound | Next state (after delay) |
|-------|----------------|-----------------|--------|-------|---------------------------|
| Push | `PlayForcePushMontage`, `ApplyForcePushEffect` | `LaunchCharacter` forward + up; `ApplyDamage` 50 | 50 | `/Game/EndarSpire/Audio/push` | STRAFING (2.0 s) |
| Lightning | `PlayForceLightningMontage`, `ApplyForceLightningEffect` | `ApplyDamage` 15 each 0.3 s for 2.0 s | ~105 | `/Game/EndarSpire/Audio/lightning` (once) | ENGAGE (2.5 s) |
| Pull | `PlayForcePullMontage`, `ApplyForcePullEffect` | Interp target to `BossForward * (MeleeRange+50)` in 0.3 s; `ApplyDamage` 20 | 20 | `/Game/EndarSpire/Audio/pull` | ATTACKING (1.5 s) |

Blueprint already plays montage + sound in graph for some paths; **avoid double audio** if both BP and C++ fire—prefer **either** BP **or** C++ as single owner (recommended: C++ director owns gameplay; BP montage nodes stay for animation notify alignment).

---

## 8. Health bar update

Every director tick (or every 0.1 s):

1. Resolve widget from `HealthBarWidgetComp->GetUserWidget()`.
2. Find named `HealthBar` (`UProgressBar`); `SetPercent(Health / MaxHealth)`.
3. Optionally update `BossNameText`.
4. If widgets missing, one-shot runtime construction per §2 or call `ConfigureBossHealthBar`.

---

## 9. Animation variable pipeline

Mirror BP tick into AnimBP **every frame** the director runs (even with BP tick off):

| ABP variable | Source |
|--------------|--------|
| `Speed` | `Velocity.Size()` |
| `Direction` | `UKismetAnimationLibrary::CalculateDirection(Velocity, ActorRotation)` |
| `IsInCombat` | `PlayerSeen` |
| `IsAttacking` | `bIsAttacking` |
| `IsDead` | `IsDead` |
| `BossCombatState` | `BossCombatState` |

---

## 10. Death handling

When `IsDead == true`:

1. `BossCombatState = 8`.
2. `StopMovementImmediately()`.
3. Clear boss-specific timers/accumulators.
4. **Do not** call `Die` (Blueprint already handles montage, taunt stop, blade hide, saber-off sound, lifespan).
5. Unregister from director.

---

## 11. Integration with existing director

```cpp
void UnrealMCPBridge::SithCombatDirectorTick(float DeltaTime)
{
    for (AActor* Actor : TrackedActors)
    {
        if (IsDarkJediBossActor(Actor))
            DarkJediBossDirectorTick(Actor, DeltaTime);
        else if (IsHeavySithTrooperActor(Actor))
            HeavySithTrooperDirectorTick(Actor, DeltaTime);
        else if (IsSithTrooperActor(Actor))
            SithTrooperDirectorTick(Actor, DeltaTime);
        // Republic soldiers, etc.
    }
}
```

---

## 12. Blueprint variables reference table

**Legend:** R = read, W = write, RW = both.

| Variable | Type | Default (CDO / BP) | Director |
|----------|------|---------------------|----------|
| Health | real | 500 | RW |
| MaxHealth | real | 500 | R |
| IsDead | bool | False | R |
| BossPhase | int | 1 | R |
| BossCombatState | int | 0 | RW |
| TargetActor | object:Actor | None | RW |
| PlayerSeen | bool | False | RW |
| bIsAttacking | bool | False | R |
| bIsPlayingMontage | bool | False | R |
| MeleeDamage | real | 35 | R |
| MeleeRange | real | 200 | R |
| ComboCount | int | 0 | R (legacy; prefer ComboCounter) |
| MaxComboHits | int | 1 | R |
| bCanForcePush | bool | False | R |
| ForcePushDamage | real | 25 | R |
| ForcePushForce | real | 2000 | R |
| ForcePushCooldown | real | 8 | R |
| bCanForceLightning | bool | False | R |
| ForceLightningDamage | real | 15 | R |
| ForceLightningDuration | real | 2 | R |
| ForceLightningCooldown | real | 12 | R |
| bCanForcePull | bool | False | R |
| ForcePullRange | real | 1500 | R |
| ForcePullForce | real | 3000 | R |
| ForcePullCooldown | real | 10 | R |
| ChargeSpeed | real | 450 | RW (phase 4 written) |
| StrafeSpeed | real | 200 | RW |
| StrafeDirection | real | 1 | R |
| StrafeDuration | real | 4 | R |
| DisengageDistance | real | 1000 | R |
| PatrolRadius | real | 600 | R |
| EngagementDistance | real | 200 | R |
| Speed | real | 0 | W (mirror to ABP; BP may still write) |
| Direction | real | 0 | W |
| ForcePushCooldownHandle | TimerHandle | () | R |
| ForceLightningCooldownHandle | TimerHandle | () | R |
| ForcePullCooldownHandle | TimerHandle | () | R |
| DeathMontage | object | RT_SW_Death_Montage | R |
| bSaberActive | bool | false | R |
| DrawSaberMontage | object | RT_SW_LightsaberDraw_Montage | R |
| SaberHumSound | object | saberhum1 (DarkJedi path) | R |
| SaberHumLoopHandle | TimerHandle | — | R |
| TauntInterval | real | 12 | R |
| TauntTimerHandle | TimerHandle | — | RW (stop/clear on death / target loss) |
| ComboCounter | int | 0 | R |
| AttackCooldown | real | 1 | R |
| bForcePushOnCooldown | bool | false | R |
| bForceLightningOnCooldown | bool | false | R |
| bForcePullOnCooldown | bool | false | R |

---

## 13. Custom events reference table

| Event name | Called by | Purpose |
|------------|-----------|---------|
| `PlayDrawSaberMontage` | Director (first sight) / BP | Draw saber |
| `StartTauntLoop` | Director (first sight) / BP | Start taunt timer |
| `StopTauntLoop` | BP death / Director (optional target loss) | Stop taunts |
| `PlaySlashMontage` | Director (ATTACKING) | Combo melee |
| `ResetMontageState` | BP timer (`K2_SetTimer`) | Clear `bIsAttacking` |
| `PlayForcePushMontage` | Director | Push montage |
| `PlayForceLightningMontage` | Director | Lightning montage |
| `PlayForcePullMontage` | Director | Pull montage |
| `ResetForcePushCooldown` | BP timer | Cooldown clear |
| `ResetForceLightningCooldown` | BP timer | Cooldown clear |
| `ResetForcePullCooldown` | BP timer | Cooldown clear |
| `ApplyMeleeDamageToPlayer` | Director (window) | Damage stub |
| `ApplyForcePushEffect` | Director | Push gameplay hook |
| `ApplyForceLightningEffect` | Director | DOT/VFX hook |
| `ApplyForcePullEffect` | Director | Pull hook |
| `ConfigureBossHealthBar` | Director | Widget fallback |
| `PlayRandomTaunt` | BP taunt timer | Voice line |
| `UpdateBossPhase` | BP (`ReceiveAnyDamage` path) | Phase scaling |
| `Die` | BP | Death sequence |

---

## 14. Component reference table

| Name | Class | Parent | Key properties (recon) |
|------|-------|--------|---------------------------|
| RootComponent | SceneComponent | — | Native |
| CapsuleComponent | CapsuleComponent | Root | Collision |
| CharacterMovement | CharacterMovementComponent | Capsule | Movement |
| Mesh | SkeletalMeshComponent | Capsule | SK: `SithWarrior1`; anim class `ABP_DarkJediBoss` |
| ArrowComponent | ArrowComponent | Capsule | Native |
| InputComponent | InputComponent | Root | Native |
| PawnSensing | PawnSensingComponent | Capsule | SightRadius 2000; HearingThreshold 1600 |
| HealthBarWidgetComp | WidgetComponent | Capsule | Screen; class `BPW_DarkJediBossHP`; DrawSize (200,50); Z offset 120 |
| LightsaberHandle | StaticMeshComponent | Mesh (verify socket `WeaponSocket` in viewport) | Mesh `lshandle06` |
| LightsaberBlade | StaticMeshComponent | LightsaberHandle | Mesh `blade_out`; **`bHiddenInGame = true`** (default + verified on instance) |

---

## 15. Montage reference table

Paths below use project convention `*.AssetName`. **Lengths** are approximate — confirm in Editor.

| Logical name | Asset path | Usage |
|--------------|------------|--------|
| Draw | `/Game/EndarSpire/AI/DarkJedi/Animations/RT_SW_LightsaberDraw_Montage.RT_SW_LightsaberDraw_Montage` | First sight |
| Slash 1–3 | `/Game/EndarSpire/AI/DarkJedi/Animations/RT_SW_LightsaberSlash{N}_Montage.RT_SW_LightsaberSlash{N}_Montage` (N=1..3) | Combo |
| Slash 4–5 | `/Game/EndarSpire/AI/DarkJedi/Animations/RT_SW_LightsaberSlash4_Montage.RT_SW_LightsaberSlash4_Montage`, `RT_SW_LightsaberSlash5_Montage` | Combo |
| Block | `/Game/EndarSpire/AI/DarkJedi/Animations/RT_SW_LightsaberBlock_Montage.RT_SW_LightsaberBlock_Montage` | Future block pass |
| Heavy | `/Game/EndarSpire/AI/DarkJedi/Animations/RT_SW_LightsaberHeavyAttack_Montage.RT_SW_LightsaberHeavyAttack_Montage` | Future heavy |
| Force Push | `/Game/EndarSpire/AI/DarkJedi/Animations/RT_SW_ForcePush_Montage.RT_SW_ForcePush_Montage` | Force |
| Force Lightning | `/Game/EndarSpire/AI/DarkJedi/Animations/RT_SW_ForceLightning_Montage.RT_SW_ForceLightning_Montage` | Force |
| Force Pull | `/Game/EndarSpire/AI/DarkJedi/Animations/RT_SW_ForcePull_Montage.RT_SW_ForcePull_Montage` | Force |
| Death | `/Game/EndarSpire/Characters/SithWarrior/Animations/Montages/RT_SW_Death_Montage.RT_SW_Death_Montage` (BP `DeathMontage` CDO) | Death |

**Skeleton:** Shared with `SithWarrior1` skeletal mesh (see §14).

---

## 16. Sound reference table

Base folder: `/Game/EndarSpire/Audio/` (use exact asset names below).

| ID | Path | Usage | Playback |
|----|------|-------|----------|
| saberhum1 | `.../saberhum1.saberhum1` | Saber idle hum | At location (BP draw) |
| enemy_saber_off | `.../enemy_saber_off.enemy_saber_off` | Death saber off | At location |
| cowardtaunt | `.../cowardtaunt.*` | Taunt | 2D |
| illbreakyou_taunt | `.../illbreakyou_taunt.*` | Taunt | 2D |
| thatwontstopme_taunt | `.../thatwontstopme_taunt.*` | Taunt | 2D |
| youre_nothing_taunt | `.../youre_nothing_taunt.*` | Taunt | 2D |
| push | `.../push.*` | Force push | At location |
| pull | `.../pull.*` | Force pull | At location |
| lightning | `.../lightning.*` | Force lightning | At location |
| saberhit | `.../saberhit.*` | Melee hit | At location |
| saberhit1 | `.../saberhit1.*` | Melee hit alt | At location |
| saberblock1 | `.../saberblock1.*` | Future block | — |
| saberblock2 | `.../saberblock2.*` | Future block | — |

---

## 17. Sandbox / level instance

- **Level**: user Sandbox (actors query).
- **Actor**: `BP_DarkJediBoss_C_1` at approximately `(-25189, 10931, -2105)` (editor snapshot 2026-05-03).

---

*End of specification.*
