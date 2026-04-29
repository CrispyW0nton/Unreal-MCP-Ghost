# BP_SithHeavyTrooperV1 Framework Log

Last updated: 2026-04-28

This document tracks the current handoff state for `BP_SithHeavyTrooper`, the heavy tank Sith variant derived from `BP_SithTrooper`. Treat this as the working truth before continuing Blueprint configuration, native director behavior, projectile damage wiring, and playtesting.

## Primary Assets

- Source Blueprint: `/Game/EndarSpire/AI/SithV2/BP_SithTrooper`
- Planned Heavy Blueprint: `/Game/EndarSpire/AI/SithV2/BP_SithHeavyTrooper`
- Heavy skeletal mesh: `/Game/EndarSpire/Characters/RiggedModels/HeavySithTrooper/HeavySithTrooper1`
- Heavy skeleton: `/Game/EndarSpire/Characters/RiggedModels/HeavySithTrooper/HeavySithTrooper_Skeleton`
- Source Sith skeletal mesh: `/Game/EndarSpire/Characters/RiggedModels/SithSoldier/SithSoldier`
- Source Sith skeleton: `/Game/EndarSpire/Characters/RiggedModels/SithSoldier/SithSoldier_Skeleton`
- Source IK Rig: `/Game/EndarSpire/Characters/Sith/IKRig_SithSoldier`
- Heavy IK Rig: `/Game/EndarSpire/Characters/HeavySithTrooper/IKRig_HeavySithTrooper`
- Heavy retargeter: `/Game/EndarSpire/Characters/HeavySithTrooper/RTG_Sith_to_HeavySith`

## Design Goal

`BP_SithHeavyTrooper` is intended to be a slow, durable tank enemy:

- `Health = 200.0`, `MaxHealth = 200.0`
- Slow direct advance, with `MaxWalkSpeed = 120.0`
- No flanking, retreating, cover movement, or grenades
- Sustained fire: native director-controlled suppression windows, `0.08` seconds between shots for `6.0-10.0` seconds, then `0.75` seconds pause
- Shoots while walking
- Targets both the player and Republic soldiers
- Uses an orange health bar labeled `Sith Heavy Trooper`
- Uses the Heavy Trooper mesh with retargeted Sith combat and locomotion animations

## Folder Structure

Created and verified:

- `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/`
- `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/Locomotion/`
- `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/Locomotion/RetargetedHeavy/`
- `/Game/EndarSpire/Characters/HeavySithTrooper/Materials/`

## Retargeting Work Completed

The Heavy Sith Trooper animation retargeting has been completed through MCP.

Completed assets/configuration:

- Created `IKRig_HeavySithTrooper`.
- Created `RTG_Sith_to_HeavySith`.
- Set the source IK Rig to `IKRig_SithSoldier`.
- Set the target IK Rig to `IKRig_HeavySithTrooper`.
- Retargeted all requested combat/death animations.
- Retargeted all `50` `RT_Sith_*` locomotion animations.

Retargeted output folders:

- Combat/death: `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/`
- Locomotion: `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/Locomotion/RetargetedHeavy/`

Final verified output count:

- Combat/death animations: `10/10`
- Locomotion animations: `50/50`
- Failed retarget outputs: `0`

## Retargeting Issue and Fix

Initial Heavy retarget outputs were visually warped even though the batch retarget operation technically succeeded.

Root cause:

- `IKRig_SithSoldier` used a simple 5-chain setup.
- `IKRig_HeavySithTrooper` had been auto-generated with extra root, neck, head, clavicle, finger, metacarpal, and IK-goal chains.
- The Heavy rig also had hand/foot IK goals on limb chains.
- This target chain layout did not match the Sith source rig and produced warped animation output.

Fix applied:

- Rebuilt `IKRig_HeavySithTrooper` to match the source Sith rig exactly.
- Set retarget root to `pelvis`.
- Removed the extra auto-generated chains, IK goals, and solver stack.
- Added only these chains:
  - `Spine`: `spine_01` to `head`
  - `LeftArm`: `clavicle_l` to `hand_l`
  - `RightArm`: `clavicle_r` to `hand_r`
  - `LeftLeg`: `thigh_l` to `foot_l`
  - `RightLeg`: `thigh_r` to `foot_r`
- Rebuilt `RTG_Sith_to_HeavySith` with exact chain mappings.
- Reset the target retarget pose back to `Default Pose`.
- Deleted the warped `RT_Heavy_*` animation outputs.
- Regenerated all Heavy retargeted animations.

Final retarget verification:

- Heavy retarget root: `pelvis`
- Heavy chain count: `5`
- Chain mappings:
  - `Spine -> Spine`
  - `LeftArm -> LeftArm`
  - `RightArm -> RightArm`
  - `LeftLeg -> LeftLeg`
  - `RightLeg -> RightLeg`
- Target retarget pose: `Default Pose`

User visual verification:

- The user confirmed the animations now look properly done.

## Logic and Asset Dump - 2026-04-28

This section is a full handoff/debug dump for the current `BP_SithHeavyTrooper` implementation after the Heavy Blueprint, AnimBlueprint, health widget, projectile class, retargeted animations, and native combat director changes were created.

### Current Blueprint Asset State

Primary Heavy Blueprint:

- Blueprint: `/Game/EndarSpire/AI/SithV2/BP_SithHeavyTrooper`
- Generated class: `/Game/EndarSpire/AI/SithV2/BP_SithHeavyTrooper.BP_SithHeavyTrooper_C`
- Source Blueprint: `/Game/EndarSpire/AI/SithV2/BP_SithTrooper`
- EventGraph node count from MCP dump: `401`
- Important inherited graph events/functions still present: `ReceiveBeginPlay`, PawnSeen-style custom event with `SeenPawn`, `StartBurstFire`, `FireOneShot`, `ApplyDamage`, `AIMoveTo`, health bar update logic, death logic, grenade checks, projectile spawn logic.

Important default values currently on `BP_SithHeavyTrooper`:

- `Health = 200.0`
- `MaxHealth = 200.0`
- `ProjectileClass = /Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile_Slugger.BP_EnemyProjectile_Slugger_C`
- `MaxBurstShots = 10`
- `ShotDelay = 0.08`
- `TimeBetweenBursts = 0.75`
- `BulletSpread = 1.5`
- `CombatMoveRadius = 0.0`
- `EngagementDistance = 0.0`
- `MinEngagementDistance = 0.0`
- `MoveCooldown = 3.0`
- `CombatMoveInterval = 3.0`
- `PatrolRadius = 400.0`
- `IdleMoveInterval = 8.0`
- `bCanThrowGrenade = false`
- `GrenadeChance = 0.0`
- `DeathAnimation = /Game/EndarSpire/Characters/HeavySithTrooper/Animations/RT_Heavy_Death`
- Runtime state defaults: `TargetActor = None`, `PlayerSeen = false`, `bWeaponRaised = false`, `IsShooting? = false`, `bIsMoving = false`

Component/default dump:

- `CollisionCylinder`: `CapsuleComponent`
- `Arrow`: `ArrowComponent`
- `CharMoveComp`: `CharacterMovementComponent`, `MaxWalkSpeed = 120.0`
- `CharacterMesh0`: `SkeletalMeshComponent`
- `CharacterMesh0.SkeletalMesh = /Game/EndarSpire/Characters/RiggedModels/HeavySithTrooper/HeavySithTrooper1`
- `CharacterMesh0.AnimClass = /Game/EndarSpire/AI/SithV2/ABP_SithHeavyTrooper.ABP_SithHeavyTrooper_C`
- `CharacterMesh0.AnimationMode = AnimationBlueprint`
- `CharacterMesh0.RelativeLocation = X 0, Y 0, Z -90`
- `CharacterMesh0.RelativeRotation = Pitch 0, Yaw -90, Roll 0`

Health widget:

- Widget asset exists: `/Game/EndarSpire/AI/SithV2/BPW_SithHeavyTrooperHP`
- Native director loads class: `/Game/EndarSpire/AI/SithV2/BPW_SithHeavyTrooperHP.BPW_SithHeavyTrooperHP_C`
- Native director sets orange health fill: `FLinearColor(0.9f, 0.4f, 0.1f, 1.0f)`
- Native director sets display text: `Sith Heavy Trooper`
- Native director creates `HealthBarWidgetComp` at runtime if missing from the actor and Heavy/Republic logic needs it.

### Blueprint Logic Still Present

Because `BP_SithHeavyTrooper` was duplicated from `BP_SithTrooper`, it still contains inherited Sith graph logic. The intended current design is that the native director takes ownership of Heavy behavior at runtime.

Important inherited Blueprint graph observations:

- The EventGraph still contains a `GetPlayerCharacter` node connected into `TargetActor` setup.
- The PawnSeen-style event still has a `SeenPawn` pin and inherited cast/target setup.
- The inherited graph still contains `StartBurstFire` and timer-based burst behavior.
- The inherited graph still contains `FireOneShot`, and `FireOneShot` spawns from the `ProjectileClass` variable.
- The projectile spawn node's `Class` pin is driven by `ProjectileClass`, so the Heavy currently spawns `BP_EnemyProjectile_Slugger`.
- The inherited graph still contains grenade checks using `bCanThrowGrenade` and `GrenadeChance`, but Heavy defaults set them to `false` and `0.0`.
- The inherited graph still contains `AIMoveTo` nodes, but native director clears `MoveTimerHandle` and disables PawnSensing for Heavy to prevent duplicate movement/targeting behavior.

Important failure mode:

- If the native MCP plugin/director is not active, not compiled, not loaded, or not identifying the actor as `BP_SithHeavyTrooper`, the Heavy may fall back to inherited `BP_SithTrooper` Blueprint behavior. That inherited behavior can target the player through `GetPlayerCharacter`, use old timer/burst flow, and not behave like the intended slow direct-advance Heavy unit.

### Native Director Ownership

The behavior that makes Heavy different from base Sith is currently controlled in `unreal_plugin/Source/UnrealMCP/Private/UnrealMCPBridge.cpp`, mainly in `SithCombatDirectorTick`.

Identification:

- `IsHeavySithTrooperActor()` returns true when the actor class path contains `/Game/EndarSpire/AI/SithV2/BP_SithHeavyTrooper.`
- `IsNativeInfantryCombatActor()` includes Sith Troopers, Heavy Sith Troopers, and Republic Soldiers.

Runtime setup/optimization:

- Heavy is included in the native director actor loop.
- Actor tick is disabled with `Trooper->SetActorTickEnabled(false)`.
- `PawnSensing` is disabled for Heavy units to prevent duplicated inherited Sith targeting from fighting native targeting.
- `MoveTimerHandle` is cleared once so old Blueprint random repositioning does not keep issuing movement orders.
- Mesh animation class is forced to `/Game/EndarSpire/AI/SithV2/ABP_SithHeavyTrooper.ABP_SithHeavyTrooper_C`.
- Mesh animation update rate optimization remains enabled.
- Health bar tick is explicitly enabled and rendered.

Targeting:

- Heavy calls `FindNearestVisibleHeavyTarget(World, Trooper, AIController, PlayerPawn, 3600.0f)`.
- Candidate targets are:
  - Player pawn from `UGameplayStatics::GetPlayerPawn(World, 0)`
  - All actors recognized by `IsRepublicSoldierActor()`
- Dead targets are skipped if their `IsDead` bool is true.
- Line of sight is checked with `AIController->LineOfSightTo(Candidate)`.
- The closest visible valid target wins.
- `TargetActor` is set to the chosen target while in combat.

Movement:

- In combat, Heavy always sets `Movement->MaxWalkSpeed = 120.0f`.
- Heavy sets `Movement->bUseControllerDesiredRotation = true`.
- Heavy sets `Movement->bOrientRotationToMovement = false`.
- Heavy keeps controller focus on the target while moving/firing.
- Heavy rotates toward target using `RInterpTo(..., 8.0f)`.
- Heavy issues direct `MoveToLocation(State.Target->GetActorLocation(), 160.0f, ...)`.
- Heavy refreshes direct advance every `0.4` seconds while target is valid.
- Heavy does not use random flank, retreat, or cover repositioning.

Firing rhythm:

- On combat entry, Heavy sets `State.ShotsRemaining = MAX_int32`.
- On combat entry, Heavy sets first shot delay to about `0.25` seconds.
- On combat entry, Heavy sets `State.BurstEndTime = Now + RandRange(6.0f, 10.0f)`.
- Heavy can fire while moving because the native firing condition allows `(bHeavyTrooper || !State.bMoveInProgress)`.
- Heavy fires if line of sight is valid, target is within `3600.0`, and `Now >= State.NextShotTime`.
- Each shot:
  - Sets `IsShooting? = true`
  - Sets `BurstShots = 0` for Heavy
  - Plays `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/RT_Heavy_Fire_Rifle_Montage`
  - Calls Blueprint event `FireOneShot`
- During the suppression window, Heavy sets `State.NextShotTime = Now + 0.08f`.
- When `Now >= State.BurstEndTime`, Heavy stops shooting, waits `0.75` seconds, then schedules another `6.0-10.0` second suppression window.

AnimBlueprint variable pipeline:

- Native director writes `Speed` and `Direction` on the AnimInstance.
- During movement, direction is forced to `0.0` for stable forward locomotion.
- Heavy sets `IsAiming = bInCombat`, even while moving.
- Heavy sets `IsShooting` and `bIsShooting` from Blueprint variable `IsShooting?`.
- Heavy sets `IsDead` from the actor's `IsDead` variable.

Death:

- Heavy death uses `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/RT_Heavy_Death_Montage`.
- Native death flow stops movement, disables capsule collision, plays the death montage, delays ragdoll based on montage length, then enables mesh physics/ragdoll.

### Heavy Animation Assets

AnimBlueprint:

- `/Game/EndarSpire/AI/SithV2/ABP_SithHeavyTrooper`
- Generated class: `/Game/EndarSpire/AI/SithV2/ABP_SithHeavyTrooper.ABP_SithHeavyTrooper_C`
- Important variables exist and default to:
  - `Speed = 0.0`
  - `Direction = 0.0`
  - `IsAiming = false`
  - `IsShooting = false`
  - `IsDead = false`

Combat/death animation folder: `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/`

- `RT_Heavy_Death`
- `RT_Heavy_Fire_Rifle`
- `RT_Heavy_Jump_Land`
- `RT_Heavy_Jump_Loop`
- `RT_Heavy_Jump_Start`
- `RT_Heavy_Rifle_Aim_To_Down`
- `RT_Heavy_Rifle_Aiming_Idle`
- `RT_Heavy_Rifle_Down_To_Aim`
- `RT_Heavy_Rifle_Idle`
- `RT_Heavy_Run_Fwd`

Heavy montages:

- `RT_Heavy_Death_Montage`
- `RT_Heavy_Fire_Rifle_Montage`
- `RT_Heavy_Rifle_Aim_To_Down_Montage`
- `RT_Heavy_Rifle_Down_To_Aim_Montage`

Locomotion:

- Folder: `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/Locomotion/RetargetedHeavy/`
- `RT_Heavy_*` locomotion asset count: `50`
- Blend space: `/Game/EndarSpire/Characters/HeavySithTrooper/Animations/Locomotion/BS_Heavy_8Dir_Locomotion`
- Blend space skeleton: `/Game/EndarSpire/Characters/RiggedModels/HeavySithTrooper/HeavySithTrooper_Skeleton`
- Blend space sample count: `28`
- Wrong/non-Heavy sample references found: `0`
- Blend space uses Heavy references such as `RT_Heavy_idle`, `RT_Heavy_walk_forward`, `RT_Heavy_run_forward`, `RT_Heavy_sprint_forward`, and directional variants.

### Retargeting Assets

Heavy IK Rig:

- `/Game/EndarSpire/Characters/HeavySithTrooper/IKRig_HeavySithTrooper`
- Retarget root: `pelvis`
- Chains:
  - `Spine`: `spine_01` to `head`
  - `LeftArm`: `clavicle_l` to `hand_l`
  - `RightArm`: `clavicle_r` to `hand_r`
  - `LeftLeg`: `thigh_l` to `foot_l`
  - `RightLeg`: `thigh_r` to `foot_r`
- IK goals: `None` on all five chains.

Heavy retargeter:

- `/Game/EndarSpire/Characters/HeavySithTrooper/RTG_Sith_to_HeavySith`
- Source IK Rig: `/Game/EndarSpire/Characters/Sith/IKRig_SithSoldier`
- Target IK Rig: `/Game/EndarSpire/Characters/HeavySithTrooper/IKRig_HeavySithTrooper`
- Chain mappings:
  - `Spine -> Spine`
  - `LeftArm -> LeftArm`
  - `RightArm -> RightArm`
  - `LeftLeg -> LeftLeg`
  - `RightLeg -> RightLeg`
- Retarget operations present:
  - `Pelvis Motion`
  - `Retarget FK Chains`
  - `Retarget IK Goals`
  - `Run IK Rig`
  - `Root Motion`
  - `Remap Curves`

### Projectile and Damage Assets

Heavy projectile:

- `BP_SithHeavyTrooper.ProjectileClass = /Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile_Slugger.BP_EnemyProjectile_Slugger_C`
- `FireOneShot` still uses the inherited projectile spawn path, but the spawn class pin is driven by `ProjectileClass`.
- Slugger reference Blueprint: `/Game/DestinyContent/Blueprints/Enemies/EnemiesV2/BP_Slugger`
- Slugger projectile asset exists: `/Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile_Slugger`

Projectile damage wiring:

- `/Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile` EventGraph node count from MCP dump: `34`
- `BP_EnemyProjectile` has an `OnHit`/component-bound damage chain with `ApplyDamage` calls.
- The dump found the Heavy cast path:
  - Cast `OtherActor` to `/Game/EndarSpire/AI/SithV2/BP_SithHeavyTrooper.BP_SithHeavyTrooper_C`
  - On success, pass `AsBP Sith Heavy Trooper` into `ApplyDamage.DamagedActor`
- `/Game/DestinyContent/Blueprints/Enem_Projectile/BP_EnemyProjectile_Slugger` EventGraph node count from MCP dump: `3`
- `BP_EnemyProjectile_Slugger` appears to have minimal graph logic in EventGraph; inherited/component/default behavior may be where its actual projectile movement/damage setup lives.

### Current Likely Debug Leads

- The Heavy Blueprint still contains inherited player-centric Blueprint logic. Native director is expected to suppress it. If Heavy is not being picked up by `IsHeavySithTrooperActor()` or the compiled plugin is not running, Heavy behavior will not match the design.
- Heavy direct advance currently refreshes `MoveToLocation` every `0.4` seconds toward the target's current location. If the Heavy appears stuck, jittery, or unable to shoot, inspect whether repeated move orders, collision, or acceptance radius `160.0` are fighting aim/shoot timing.
- Heavy's Blueprint defaults set `EngagementDistance`, `MinEngagementDistance`, and `CombatMoveRadius` to `0.0`. Native Heavy logic ignores these for targeting/firing and uses `3600.0`, but inherited Blueprint logic may behave incorrectly if native ownership is not active.
- If the Heavy is not firing continuously, verify in live PIE that native `SithCombatDirectorTick` is loaded from the rebuilt plugin and that `CallBlueprintEvent(Trooper, TEXT("FireOneShot"))` is hitting the Heavy instance.
- If Heavy projectile behavior differs from Slugger, compare `BP_EnemyProjectile_Slugger` component/default values against Slugger's own attack graph, because the Heavy currently borrows only the projectile class and still calls inherited `FireOneShot` rather than duplicating Slugger's full weapon/fire graph.
