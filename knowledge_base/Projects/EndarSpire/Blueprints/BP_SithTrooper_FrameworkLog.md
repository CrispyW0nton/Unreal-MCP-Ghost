# BP_SithTrooper Framework Log

Last updated: 2026-04-27

This document is the current handoff state for `BP_SithTrooper` after Phases 1-9, the native combat director pass, the 8-direction locomotion pass, bullet accuracy tuning, and the safe Event Graph organization pass. It should be treated as the working truth before starting the next development phase.

## Primary Assets

- Blueprint: `/Game/EndarSpire/AI/SithV2/BP_SithTrooper`
- Animation Blueprint: `/Game/EndarSpire/AI/SithV2/ABP_SithTrooperElite`
- Health widget: `/Game/EndarSpire/AI/SithV2/BPW_SithTrooperHP`
- AI controller: `/Game/EndarSpire/AI/Sith/BP_SithSoldierController`
- Weapon mesh: `/Game/EndarSpire/WeaponModels/Carbine`
- Sith skeletal mesh: `/Game/EndarSpire/Characters/RiggedModels/SithSoldier/SithSoldier`
- Sith skeleton: `/Game/EndarSpire/Characters/RiggedModels/SithSoldier/SithSoldier_Skeleton`
- Projectile class: `/Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile`
- Grenade class: `/Game/DestinyContent/Blueprints/BP_Grenade`
- Infantry reference enemy: `/Game/DestinyContent/Blueprints/Enemies/EnemiesV2/BP_Infantry`

## Current Compile / Save State

- `BP_SithTrooper` compiles through the MCP bridge with `had_errors = false`.
- `ABP_SithTrooperElite` compiles through the MCP bridge with `had_errors = false`.
- Latest verified EventGraph state after the safe organization pass: `449` nodes total, including `45` comment boxes.
- Latest visible section-label count: `19`.
- Disconnected orphan/unused nodes were moved into a labeled quarantine area instead of force-deleted, because graph node deletion through MCP can crash this project.
- The temporary test comment created while validating the safer comment command was removed.
- MCP package save is disabled in this project because `SavePackage` can crash with `MassEntityEditor`.
- Manual save in Unreal is still required after automated edits: open `BP_SithTrooper` and press `Ctrl+S`.

## Components

Current `BP_SithTrooper` component surface detected through MCP:

- `PawnSensing` (`PawnSensingComponent`)
- `HealthBarWidgetComp` (`WidgetComponent`)
  - Widget class: `/Game/EndarSpire/AI/SithV2/BPW_SithTrooperHP.BPW_SithTrooperHP_C`
  - Latest detected relative location: `(X=0.000000,Y=-62.852793,Z=97.598005)`
- `Gun` (`StaticMeshComponent`)
  - Static mesh: `/Game/EndarSpire/WeaponModels/Carbine.Carbine`
  - MCP repeatedly reports duplicate `Gun` rows with the same SCS GUID/object, so this appears to be duplicated bookkeeping/reporting, not safely confirmed distinct components.
  - `set_component_parent_socket` could set socket metadata but did not reliably reparent the component under native `Mesh`; the user should verify the Components panel visually.
- Native components:
  - `Mesh` / `CharacterMesh0` (`SkeletalMeshComponent`)
  - `CharacterMovement`
  - `CapsuleComponent`
  - `ArrowComponent`
  - `InputComponent`
  - `RootComponent`

## Weapon Attachment State

- Existing skeleton sockets:
  - `WeaponSocket` on bone `hand_r`
  - `GunBarrel` on bone `ik_hand_gun`
- The user previewed the `Carbine` mesh on `WeaponSocket` and adjusted it in the Skeleton Editor.
- The intended final component hierarchy is:
  - `CapsuleComponent`
    - `Mesh`
      - `Gun`
- Required manual verification:
  - Open `BP_SithTrooper`.
  - Confirm `Gun` is visibly indented under `Mesh (CharacterMesh0)`.
  - Select `Gun` and confirm `Parent Socket = WeaponSocket`.
  - Confirm `Gun` relative location/rotation is zeroed and scale is appropriate for the socket preview.
- If `Gun` is still root-level or under the wrong component, drag `Gun` onto `Mesh` in the Components panel manually. The bridge did not reliably perform this native-parent reparent operation.

## Variables

Current variable surface includes the original combat variables plus the newer native-director tuning variables:

- `IsShooting?` (`bool`)
- `Health` (`float`)
- `MaxHealth` (`float`)
- `IsDead` (`bool`)
- `PlayerSeen` (`bool`)
- `BurstShots` (`int`)
- `GrenadeChance` (`float`)
- `TargetActor` (`Actor`)
- `TimeBetweenBursts` (`float`)
- `ShotDelay` (`float`)
- `MaxBurstShots` (`int`)
- `WeaponRange` (`float`)
- `bShouldMove` (`bool`)
- `MoveCooldown` (`float`)
- `PatrolRadius` (`float`)
- `MeleeRange` (`float`)
- `MeleeDamage` (`float`)
- `bIsJumping` (`bool`)
- `JumpBackForce` (`float`)
- `bCanThrowGrenade` (`bool`)
- `GrenadeCooldown` (`float`)
- `bIsPlayingMontage` (`bool`)
- `BurstTimerHandle` (`TimerHandle`)
- `BurstCooldownHandle` (`TimerHandle`)
- `MoveTimerHandle` (`TimerHandle`)
- `GrenadeTimerHandle` (`TimerHandle`)
- `VisibilityTimerHandle` (`TimerHandle`)
- `LoseSightTimerHandle` (`TimerHandle`)
- `JumpResetTimerHandle` (`TimerHandle`)
- `bWeaponRaised` (`bool`)
- `ProjectileClass` (`Actor class`)
- `BulletSpread` (`float`)
- `FireSound` (`SoundBase`)
- `CombatMoveRadius` (`float`, native-director tuning, default verified as `400.0`)
- `EngagementDistance` (`float`, native-director tuning, default verified as `1500.0`)
- `MinEngagementDistance` (`float`, native-director tuning, default verified as `600.0`)
- `bIsMoving` (`bool`, native-director animation/runtime state)
- `CombatMoveInterval` (`float`, native-director tuning, default verified as `4.0`)
- `IdleMoveInterval` (`float`, native-director tuning, default verified as `6.0`)

Suggested manual variable categories, if desired:

- Health: `Health`, `MaxHealth`, `IsDead`
- Combat State: `PlayerSeen`, `bWeaponRaised`, `IsShooting?`, `bIsPlayingMontage`, `TargetActor`
- Shooting: `BurstShots`, `MaxBurstShots`, `ShotDelay`, `TimeBetweenBursts`, `WeaponRange`, `BulletSpread`, `ProjectileClass`, `BurstTimerHandle`, `BurstCooldownHandle`, `FireSound`
- Movement: `bShouldMove`, `MoveCooldown`, `PatrolRadius`, `MoveTimerHandle`, `CombatMoveRadius`, `EngagementDistance`, `MinEngagementDistance`, `bIsMoving`, `CombatMoveInterval`, `IdleMoveInterval`
- Melee & Evasion: `MeleeRange`, `MeleeDamage`, `bIsJumping`, `JumpBackForce`, `JumpResetTimerHandle`
- Grenade: `GrenadeChance`, `bCanThrowGrenade`, `GrenadeCooldown`, `GrenadeTimerHandle`
- Visibility: `VisibilityTimerHandle`, `LoseSightTimerHandle`

## Combat / Detection State

- `PawnSensing.OnSeePawn` calls `OnPawnSeen`.
- `OnPawnSeen` now checks `IsDead` first.
- `OnPawnSeen` uses `bWeaponRaised` as the combat-entry gate.
- First valid sighting:
  - Sets `PlayerSeen = true`.
  - Sets `TargetActor`.
  - Sets `bWeaponRaised = true`.
  - Plays `Rifle_Down_To_Aim_Sith_Montage`.
  - Delays briefly.
  - Calls `StartBurstFire`.
- Repeated sightings while `bWeaponRaised = true` refresh `TargetActor` and do not replay the raise-rifle montage.
- `StopCombat` resets combat state:
  - `IsShooting? = false`
  - `PlayerSeen = false`
  - `bWeaponRaised = false`
  - Plays `Rifle_Aim_To_Down_Sith_Montage`
  - Clears burst timers.

## Visibility / Lose Sight

- `CheckPlayerVisibility` is visibility-focused now.
- It checks dead/combat/target validity before tracing.
- It uses line trace visibility testing instead of restarting combat state directly.
- Sight loss routes to `StopCombat`.
- `LoseSightTimerHandle` exists for delayed sight-loss behavior.
- `CheckCloseRange` remains part of the periodic engagement checks.

## Shooting System

- `StartBurstFire` gates against invalid combat state, including `IsDead`, `PlayerSeen`, `IsShooting?`, `bWeaponRaised`, and `bIsPlayingMontage`.
- `FireOneShot` uses a projectile-style firing path rather than the old direct-damage-only behavior.
- `ProjectileClass` was added and should point to the enemy projectile Blueprint.
- `BulletSpread` was added for shot spread.
- Latest accuracy tuning: `BulletSpread = 0.75`, reduced from the wider combat-test value so shots hit the player more often.
- `FireSound` was added as a `SoundBase` object variable so sound asset references persist correctly.
- Burst flow:
  - Reset/increment `BurstShots`.
  - Spawn projectile with spread.
  - Play firing sound.
  - Stop after `MaxBurstShots`.
  - Clear burst timer and start burst cooldown.

## Tactical Repositioning

- Core tactical movement is now driven by the native C++ `SithCombatDirectorTick` in the Unreal MCP plugin, not by fragile Blueprint graph rewiring.
- The native director reads Blueprint tuning variables from `BP_SithTrooper` and uses fallback values if the generated class has not refreshed yet.
- On first native tick for a trooper, the director clears the old Blueprint `MoveTimerHandle` once so legacy movement timers do not fight the native behavior.
- Combat behavior:
  - Maintains sticky combat state after line of sight.
  - Raises/keeps weapon state through `bWeaponRaised`.
  - Sets AI focus toward the player.
  - Rotates smoothly toward `TargetActor`.
  - Retreats when closer than `MinEngagementDistance`.
  - Repositions laterally/orbit-style around `EngagementDistance`.
  - Uses reachable NavMesh points and `AIController->MoveToLocation`.
  - Prevents shooting while a move is in progress.
  - Uses a move-stop-shoot rhythm with burst windows.
- Idle behavior:
  - Patrols around the spawn location using `PatrolRadius`.
  - Uses slower walk speed and movement-oriented rotation.
- Current character movement settings verified:
  - `bUseAccelerationForPaths = true`
  - `MaxWalkSpeed = 300.0` as the Blueprint-side baseline; the native director adjusts runtime walk speeds for idle/combat.
  - `bOrientRotationToMovement = true` as the Blueprint-side baseline; the native director changes this at runtime during combat.

## Close Range / Evasion

- `CheckCloseRange` checks distance to `TargetActor` against `MeleeRange`.
- `JumpAway` sets `bIsJumping = true`, launches the character, and starts `JumpResetTimerHandle`.
- `ResetJump` sets `bIsJumping = false`.
- `MeleeAttack`/melee behavior should be rechecked during future playtests if close-range observations come up.

## Grenade System

- `TryThrowGrenade` now has comprehensive guard conditions:
  - Not dead.
  - Player is seen.
  - Can throw grenade.
  - Not already shooting / conflicting with combat montage flow.
  - Not currently playing another montage.
  - Random chance must pass `GrenadeChance`.
- On throw:
  - Sets `bCanThrowGrenade = false`.
  - Sets `bIsPlayingMontage = true`.
  - Stops movement.
  - Clears burst firing if needed.
  - Plays `A_Sith_Grenade_Throw_Montage`.
  - Spawns `BP_Grenade` with owner/instigator context.
  - Sets projectile movement velocity for an arc.
  - Attempts to ignore self-collision.
  - Resets montage state.
  - Starts/reset grenade cooldown.
- `Die` clears `GrenadeTimerHandle` and resets `bIsPlayingMontage`.

## Animation Blueprint Sync

`BP_SithTrooper` now pushes state to `/Game/EndarSpire/AI/SithV2/ABP_SithTrooperElite` every tick:

- `Speed` from velocity length.
- `IsAiming` from `bWeaponRaised`.
- `IsShooting` from `IsShooting?`.
- `IsDead` from `IsDead`.

The tick graph still preserves smooth rotation toward `TargetActor` while combat conditions are valid. If the cast to the AnimBP fails, rotation logic still runs.

`ABP_SithTrooperElite` variables added or verified:

- `Speed` (`float`)
- `Direction` (`float`)
- `IsAiming` (`bool`)
- `IsShooting` (`bool`)
- `IsDead` (`bool`)

The current AnimGraph uses the 8-direction locomotion Blend Space through a slot path:

- Blend Space: `/Game/EndarSpire/Characters/Sith/Animations/Locomotion/BS_Sith_8Dir_Locomotion`
- `Speed` drives the Blend Space X axis.
- `Direction` drives the Blend Space Y axis.
- The native combat director pushes `Speed`, `Direction`, `IsAiming`, `IsShooting`, `bIsShooting`, and `IsDead` onto the AnimInstance.
- The Blend Space was rebuilt to reference retargeted Sith-skeleton animations, not the original source-skeleton imports.

## Damage / Health Bar / Death

- `ReceiveAnyDamage` now guards against `IsDead`.
- Health calculation clamps `Health` between `0` and `MaxHealth`.
- Health bar widget update path:
  - Get `HealthBarWidgetComp`.
  - Get widget.
  - Cast to `BPW_SithTrooperHP`.
  - Set progress bar percent to `Health / MaxHealth`.
  - Set enemy name to `Sith Trooper` once.
  - Show health bar on damage.
  - Hide health bar after retriggerable delay.
- `BPW_SithTrooperHP` default display name was set to `Sith Trooper`.
- If `Health <= 0`, `Die` is called.
- `Die`:
  - Sets `IsDead = true`.
  - Sets `PlayerSeen = false`.
  - Sets `IsShooting? = false`.
  - Sets `bIsPlayingMontage = false`.
  - Clears relevant timers.
  - Hides health bar.
  - Disables capsule collision.
  - Enables mesh ragdoll/collision/physics behavior.
  - Sets lifespan.

## Existing Project Damage Compatibility

The existing enemy damage pattern is not pure `ApplyDamage` from the player side. `BP_Infantry` receives many attacks through overlap with short-lived helper actors.

`BP_SithTrooper` now has a compatibility `ReceiveActorBeginOverlap` path that recognizes the same helper actors and calls UE `ApplyDamage` on itself so the existing `ReceiveAnyDamage` health/death path is reused.

Recognized helper actors:

- `BP_ApplyDamage` -> `15`
- `BP_ApplyDamage_Stasis2` -> `30`
- `BP_ApplyMeleeDamage` -> `50`
- `BP_ApplyDamage_Heavy` -> `100`
- `BP_ApplyMeleeDamage_Bash` -> `100`
- `BP_Void_Grenade_AOE` -> `100`
- `BP_Explosive_AOE` -> `100`

Reference enemies:

- `BP_Infantry` contains the real damage handling implementation.
- `BP_Slugger`, `BP_Phalanx`, `BP_Mega`, and `BP_Exploder` appear to be thin variants with no local damage graphs/variables of their own.

## Event Graph Organization

Latest organization pass was intentionally visual and conservative.

- The first attempted forced orphan-delete pass crashed Unreal. Do not repeat broad unsafe graph deletion on this Blueprint.
- After restart, `BP_SithTrooper` still compiled with no errors.
- Safer pass added readable section boxes using `add_comment_box`, which preserves visible comment text.
- The older generic `Comment` boxes were moved out of the main graph into an old-comment parking area.
- Disconnected non-running leftovers were moved into a quarantine area instead of deleted.
- No behavior rewiring was intentionally performed during the successful organization pass.
- No event names were changed.
- No timer callback names were changed.
- No function collapsing was done.
- Latest verification after cleanup:
  - EventGraph nodes: `449`.
  - Comment boxes: `45`.
  - Visible non-generic labels: `19`.
  - `BP_SithTrooper` compile: `had_errors = false`.
  - MCP bridge ping: healthy.

Visible section labels now present:

- `MOVEMENT - Legacy Patrol Timers (Native Director Overrides Movement)`
- `INIT - Health, Target, Timers`
- `PERCEPTION - Pawn Seen Delegate`
- `VISIBILITY - Line Trace And Lose Sight Timer`
- `FIRE CONTROL - Burst Gate`
- `GRENADES - Throw Grenade Sequence`
- `COMBAT ENTRY - Raise Rifle And Start Burst`
- `ANIMATION SYNC - Tick Pushes Speed, Aim, Shooting`
- `COMBAT EXIT - Timeout Wrapper`
- `FIRE CONTROL - Spawn Projectile And Schedule Burst`
- `COMBAT EXIT - Stop Shooting And Lower Rifle`
- `FIRE CONTROL - Start Burst Wrapper`
- `GRENADES - Reset Cooldown`
- `CLOSE RANGE - Jump Away And Reset`
- `DAMAGE - Projectile Overlap Damage`
- `DAMAGE - Health Bar And Death`
- `ORPHANED / UNUSED NODES - Quarantined, Do Not Run`
- `OLD GENERIC COMMENT BOXES - Parked Out Of Main Graph`

Existing older labels that may still be visible:

- `Jump Away When Player is Close`
- `DamageSystem`

## Related Animation Assets

Useful Sith animation assets:

- `/Game/EndarSpire/Characters/Sith/Animations/Rifle_Idle_Sith`
- `/Game/EndarSpire/Characters/Sith/Animations/Rifle_Aiming_Idle_Sith`
- `/Game/EndarSpire/Characters/Sith/Animations/Rifle_Down_To_Aim_Sith`
- `/Game/EndarSpire/Characters/Sith/Animations/Rifle_Down_To_Aim_Sith_Montage`
- `/Game/EndarSpire/Characters/Sith/Animations/Rifle_Aim_To_Down_Sith`
- `/Game/EndarSpire/Characters/Sith/Animations/Rifle_Aim_To_Down_Sith_Montage`
- `/Game/EndarSpire/Characters/Sith/Animations/A_Sith_Fire_Rifle`
- `/Game/EndarSpire/Characters/Sith/Animations/A_Sith_Grenade_Throw`
- `/Game/EndarSpire/Characters/Sith/Animations/A_Sith_Grenade_Throw_Montage`
- `/Game/EndarSpire/Characters/Sith/Animations/A_Sith_Run_Fwd`
- `/Game/EndarSpire/Characters/Sith/Animations/A_Sith_Jump_Start`
- `/Game/EndarSpire/Characters/Sith/Animations/A_Sith_Jump_Loop`
- `/Game/EndarSpire/Characters/Sith/Animations/A_Sith_Jump_Land`
- `/Game/EndarSpire/Characters/Sith/Animations/BS_Sith_Locomotion`
- `/Game/EndarSpire/Characters/Sith/Animations/Locomotion/BS_Sith_8Dir_Locomotion`
- `/Game/EndarSpire/Characters/Sith/Animations/Locomotion/SithRetargeted/RT_Sith_*`

Note: `A_Sith_Fire_Rifle` was identified as an animation sequence, not a montage, so it was not wired as a montage during the firing pass.

8-direction locomotion notes:

- Source pack location: `Sit/Animations/Locomotion`.
- Source skeleton: `Toss_Grenade_Skeleton`.
- Target skeleton: `SithSoldier_Skeleton`.
- Retargeter used: `RTG_MX_TossGrenade_to_Sith`.
- Retargeted output folder: `/Game/EndarSpire/Characters/Sith/Animations/Locomotion/SithRetargeted`.
- The retargeted folder contains `50` `RT_Sith_*` animation sequences.
- `BS_Sith_8Dir_Locomotion` was verified with `28` samples linked to Sith-skeleton animations.

## Known Caveats / Verify Next

- Manually save `BP_SithTrooper`, `ABP_SithTrooperElite`, `BPW_SithTrooperHP`, the 8-direction Blend Space, retargeted animation folder, and the Sith skeleton if any of them show dirty state in Unreal.
- Verify the `Gun` component is truly attached under `Mesh` with `Parent Socket = WeaponSocket`; MCP could not reliably confirm or enforce this final hierarchy.
- If multiple `Gun` components are visible in the actual Components panel, inspect before deleting. MCP reports repeated `Gun` entries using the same GUID/object.
- Verify the newest visible section labels in the Event Graph after manual save/reopen.
- Future cleanup can manually categorize variables in the editor. Automated category edits were skipped to avoid protected metadata writes.
- Future function collapsing should be done only after a dedicated backup/snapshot, because replacing inline timer/montage/death logic can silently change behavior.
- Keep timer-by-function-name strings synchronized with custom event names. Do not rename timer callback events unless every timer string is updated too.
- Avoid broad `force_unsafe_delete` graph cleanup on `BP_SithTrooper`; previous forced deletion caused an editor crash. Prefer quarantine/move-only cleanup unless deleting one clearly isolated temporary node.
- The native combat director is now the source of truth for active movement/combat rhythm. Do not rebuild the old Blueprint repositioning graph unless intentionally replacing the native system.

## Next Development Notes

The user has playtest observations to capture before the next implementation phase. Add those observations below before making more behavior changes:

- Observation 1:
- Observation 2:
- Observation 3:
