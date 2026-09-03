# BP_DarkJediBoss — Framework Log
**Date**: 2026-05-03
**Phase**: D.6 Complete
**Blueprint**: /Game/EndarSpire/AI/SithV2/BP_DarkJediBoss
**Compile Status**: pass (bridge `had_errors: false`; deferred compile — save in UE)
**Event Graph Nodes**: 293

---

## 1. Primary Assets

| Asset | Path |
|-------|------|
| Blueprint | `/Game/EndarSpire/AI/SithV2/BP_DarkJediBoss` |
| AnimBP | `/Game/EndarSpire/AI/SithV2/ABP_DarkJediBoss` |
| Health widget | `/Game/EndarSpire/AI/SithV2/BPW_DarkJediBossHP` |
| Boss mesh (current) | `/Game/EndarSpire/Characters/RiggedModels/SithWarrior/SithWarrior1.SithWarrior1` |
| Blade mesh | `/Game/EndarSpire/WeaponModels/Sabers/blade_out.blade_out` |
| Handle mesh | `/Game/EndarSpire/WeaponModels/Sabers/lshandle06.lshandle06` |
| Skeleton | Inherits from SithWarrior mesh asset (confirm in SK editor) |
| Physics | Use SK’s paired physics asset (confirm in Content Browser) |

---

## 2. Component List

| Component | Class | Parent | Key properties |
|-----------|-------|--------|----------------|
| RootComponent | SceneComponent | — | Native |
| CapsuleComponent | CapsuleComponent | Root | Character collision |
| CharacterMovement | CharacterMovementComponent | Capsule | Movement |
| Mesh | SkeletalMeshComponent | Capsule | `SithWarrior1` |
| ArrowComponent | ArrowComponent | Capsule | Native |
| InputComponent | InputComponent | Root | Native |
| PawnSensing | PawnSensingComponent | Capsule | SightRadius `2000`, HearingThreshold `1600` |
| HealthBarWidgetComp | WidgetComponent | Capsule | `BPW_DarkJediBossHP`, screen space, Z+120 |
| LightsaberHandle | StaticMeshComponent | Mesh (verify `WeaponSocket`) | `lshandle06` |
| LightsaberBlade | StaticMeshComponent | LightsaberHandle | `blade_out`, **`bHiddenInGame = true`** |

---

## 3. Variable Table

Full list (49) with defaults from **CDO recon** (`get_blueprint_variable_defaults`) unless noted.

| Name | Type | Default | Category (grouping) |
|------|------|---------|---------------------|
| Health | float | 500 | Health |
| MaxHealth | float | 500 | Health |
| IsDead | bool | False | Health |
| BossPhase | int | 1 | Combat |
| BossCombatState | int | 0 | Combat |
| TargetActor | Actor | None | Combat |
| PlayerSeen | bool | False | Combat |
| bIsAttacking | bool | False | Combat |
| bIsPlayingMontage | bool | False | Animation |
| MeleeDamage | float | 35 | Combat |
| MeleeRange | float | 200 | Combat |
| ComboCount | int | 0 | Combat (legacy) |
| MaxComboHits | int | 1 | Combat |
| bCanForcePush | bool | False | Force |
| ForcePushDamage | float | 25 | Force |
| ForcePushForce | float | 2000 | Force |
| ForcePushCooldown | float | 8 | Force |
| bCanForceLightning | bool | False | Force |
| ForceLightningDamage | float | 15 | Force |
| ForceLightningDuration | float | 2 | Force |
| ForceLightningCooldown | float | 12 | Force |
| bCanForcePull | bool | False | Force |
| ForcePullRange | float | 1500 | Force |
| ForcePullForce | float | 3000 | Force |
| ForcePullCooldown | float | 10 | Force |
| ChargeSpeed | float | 450 | Movement |
| StrafeSpeed | float | 200 | Movement |
| StrafeDirection | float | 1 | Movement |
| StrafeDuration | float | 4 | Movement |
| DisengageDistance | float | 1000 | Movement |
| PatrolRadius | float | 600 | Movement |
| EngagementDistance | float | 200 | Movement |
| Speed | float | 0 | Animation |
| Direction | float | 0 | Animation |
| ForcePushCooldownHandle | TimerHandle | () | Timer |
| ForceLightningCooldownHandle | TimerHandle | () | Timer |
| ForcePullCooldownHandle | TimerHandle | () | Timer |
| DeathMontage | AnimMontage | RT_SW_Death_Montage | Animation |
| bSaberActive | bool | false | Combat |
| DrawSaberMontage | AnimMontage | RT_SW_LightsaberDraw_Montage | Animation |
| SaberHumSound | SoundBase | saberhum1 (DarkJedi path) | Audio |
| SaberHumLoopHandle | TimerHandle | — | Timer |
| TauntInterval | float | 12 | Audio |
| TauntTimerHandle | TimerHandle | — | Timer |
| ComboCounter | int | 0 | Combat |
| AttackCooldown | float | 1 | Combat |
| bForcePushOnCooldown | bool | false | Force |
| bForceLightningOnCooldown | bool | false | Force |
| bForcePullOnCooldown | bool | false | Force |

---

## 4. Event Graph Section Map

Comment labels in graph; approximate **node counts** by vertical band (nodes assigned to nearest band — melee/custom/perception share one vertical lane).

| Section label | Approx. nodes | Purpose |
|---------------|--------------|---------|
| INIT - Health and Phase Setup | 12 | Defaults |
| DAMAGE - Health / Phase check | 18 | `ReceiveAnyDamage` |
| PHASE UPDATE | 38 | `UpdateBossPhase` |
| DEATH | 25 | `Die`, lifespan, saber shutdown |
| DAMAGE HELPER OVERLAP | 26 | Legacy overlap damage |
| ANIMATION SYNC | 19 | Push vars to ABP |
| MELEE COMBAT | (within 5400–7550 lane) | Combo / slash |
| CUSTOM EVENTS - Native Director Hooks | (shared lane) | Stubs + force entry |
| PERCEPTION - ON SEE PAWN | (shared lane) | `PawnSensing` `OnSeePawn` |
| FORCE POWERS | (shared lane) | Force montages |
| D.6.1 LIGHTSABER ACTIVATION | 8 | Draw saber |
| TAUNT SYSTEM | 13 | Timer + taunts |
| HEALTH BAR RUNTIME SETUP | 1 | `ConfigureBossHealthBar` stub |
| QUARANTINE | 4 | Orphan nodes |
| **Total** | **293** | — |

---

## 5. Custom Events

| Event | Wiring | Caller |
|-------|--------|--------|
| `UpdateBossPhase` | Wired | BP damage flow |
| `Die` | Wired | BP |
| `PlaySlashMontage` | Wired | BP; director will call |
| `PlayForcePushMontage` | Wired | BP; director |
| `PlayForceLightningMontage` | Wired | BP; director |
| `PlayForcePullMontage` | Wired | BP; director |
| `PlayDrawSaberMontage` | Wired | BP; director |
| `ResetMontageState` | Wired | BP timer |
| `ResetForcePushCooldown` | Wired | BP timer |
| `ResetForceLightningCooldown` | Wired | BP timer |
| `ResetForcePullCooldown` | Wired | BP timer |
| `StartTauntLoop` | Wired | BP / perception |
| `StopTauntLoop` | Wired | BP death; inline timer clear also in death chain |
| `PlayRandomTaunt` | Wired | Taunt timer |
| `ApplyMeleeDamageToPlayer` | Wired stub | Director / BP |
| `ApplyForcePushEffect` | Stub | Director |
| `ApplyForceLightningEffect` | Stub | Director |
| `ApplyForcePullEffect` | Stub | Director |
| `ConfigureBossHealthBar` | Stub | Director |

---

## 6. Animation Assets

| Asset | Path |
|-------|------|
| ABP | `/Game/EndarSpire/AI/SithV2/ABP_DarkJediBoss` |
| Draw montage | `.../DarkJedi/Animations/RT_SW_LightsaberDraw_Montage` |
| Slash 1–5 | `RT_SW_LightsaberSlash1_Montage` … `RT_SW_LightsaberSlash5_Montage` |
| Block | `RT_SW_LightsaberBlock_Montage` |
| Heavy | `RT_SW_LightsaberHeavyAttack_Montage` |
| Force Push / Lightning / Pull | `RT_SW_ForcePush_Montage`, `RT_SW_ForceLightning_Montage`, `RT_SW_ForcePull_Montage` |
| Death | `RT_SW_Death_Montage` (see `DeathMontage` variable under SithWarrior path) |

---

## 7. Sound Assets

| Sound | Path (prefix `/Game/EndarSpire/Audio/`) | Usage |
|-------|----------------------------------------|--------|
| saberhum1 | DarkJedi/Sounds or Audio (project-dependent) | Draw |
| enemy_saber_off | Audio | Death |
| cowardtaunt, illbreakyou_taunt, thatwontstopme_taunt, youre_nothing_taunt | Audio | Taunts 2D |
| push, pull, lightning | Audio | Force |
| saberhit, saberhit1 | Audio | Melee |
| saberblock1, saberblock2 | Audio | Future block |

---

## 8. Native Director Spec

- **Document**: [BP_DarkJediBoss_NativeDirectorSpec.md](BP_DarkJediBoss_NativeDirectorSpec.md)
- **Status**: Initial C++ implementation added — `IsDarkJediBossActor` dispatches before infantry actors, `DarkJediBossDirectorTick` owns target acquisition, saber activation/audio, AIController movement, melee timing/damage, state transitions, and AnimBP variable sync.
- **Follow-up fix**: Boss runtime setup now forces `AIControllerClass = AAIController`, `AutoPossessAI = PlacedInWorldOrSpawned`, `bCanBeDamaged = true`, plays `enemy_saber_on` before `saberhum1`, and includes native overlap-radius damage intake for player melee/grenade damage helper actors.
- **Second playtest follow-up**: Native director now sets `RootMotionMode = IgnoreRootMotion`, removes duplicate movement-input steering when AIController pathing is active, plays slash/force montages directly, writes player `HP`/`Overshield` damage directly, adds initial Push/Lightning/Pull director states, and performs death ragdoll after the death montage.
- **Aggression tuning**: Native loop now charges at `660`, uses `0.62s` attack cadence, forces 3-5 hit saber combos, rotates force powers after combo windows, and immediately re-engages instead of backing off for long pauses. Blueprint defaults updated to `MaxComboHits=4`, `MeleeRange=260`, and all force availability booleans enabled.
- **Pressure-loop correction**: Native loop now prioritizes closing to melee before casting: run at player → random 1-4 slice combo → Force Push → Lightning → re-engage melee while the player recovers, with a chance to Force Pull into another 1-4 slice combo. Added runtime particle helpers for `P_Dor_Lightning_01` and `P_Shield_Spawn` using common effect folders.
- **Smoothness/VFX follow-up**: Particle loading now searches the Asset Registry for `P_Dor_Lightning_01` / `P_Shield_Spawn` anywhere under `/Game`, approach `MoveToActor` updates less frequently with a smaller acceptance radius, and native montage playback no longer double-calls the Blueprint slash/force montage events.
- **Lightning VFX duration fix**: Lightning channel duration now follows `RT_SW_ForceLightning_Montage` length and respawns the elongated `P_Dor_Lightning_01` effect every `0.12s` during the full channel so short-burst particle assets remain visible throughout the animation.
- **Aggressive melee/VFX/audio fix**: Native VFX spawning now supports Niagara systems as well as Cascade particles, lightning spawns from both the boss casting origin and midpoint with distance-scaled length, saber hum is spawned as a stoppable attached audio component and destroyed on death, and the melee loop now sprints closer, refreshes pathing quickly, and lunges during slash startup before allowing force-power follow-ups.
- **Custom lightning + health fix**: Boss runtime setup now doubles `MaxHealth` and fills `Health` to that doubled value. Force Lightning now has a native procedural fallback inspired by beam-style lightning VFX: every `0.05s`, jagged blue-white arcs are emitted from detected hand/fingertip sockets toward the player, with endpoint glow and secondary branches, so the lightning remains visible even when `P_Dor_Lightning_01` cannot be resolved.
- **Player lethal-damage fix**: Boss direct player damage now calls a native lethal bridge when `HP` reaches zero. The bridge sets common dead-state booleans and invokes any matching no-argument player death handler (`Die`, `Death`, `PlayerDeath`, `HandleDeath`, etc.) so the player death flow can run instead of only freezing movement at zero health.

---

## 9. Plugin Upgrades Performed During Phase D.6

| Area | Change |
|------|--------|
| `get_blueprint_nodes` | `K2Node_CustomEvent` exposes `event_name` / `custom_function_name` (additional serializer paths). |
| `add_blueprint_variable` | `Struct/TimerHandle` supported. |
| `add_blueprint_function_node` | Self-member fallback for Blueprint-owned functions / new custom events; later patch for zero-pin `CreateFunctionCallNode` on BP-owned `UFunction`. |
| `set_component_property` | Aliases `hidden_in_game` → `bHiddenInGame`. |
| Graph tools | `bp_add_node` / `bp_inspect_node` routed in bridge (when rebuilt). |
| Native director | Added `FDarkJediBossCombatState` and `DarkJediBossDirectorTick` to the bridge/project plugin copy for boss-specific movement and melee. |
| Native boss hardening | Added AIController fallback, activation audio, direct movement-input fallback, and native damage intake sweep for Dark Jedi boss. |
| Native boss combat | Added direct slash montage playback, player HP/Overshield damage helper, Push/Lightning/Pull state handling, root-motion ignore, and death ragdoll timing. |
| Native boss aggression | Retuned state machine for fast charge → multi-slash combo → force power → re-charge pressure loop. |
| Native force VFX | Added Cascade particle spawning for lightning (`P_Dor_Lightning_01`, elongated scale) and push/pull (`P_Shield_Spawn`) when assets resolve at runtime. |
| Native smoothness | Asset Registry particle lookup, less frequent close-distance path refresh, smaller melee acceptance radius, and removed duplicate Blueprint montage event calls. |
| Native lightning VFX | Repeated elongated lightning emitter spawn across the full montage-driven channel. |
| Known gap | `add_blueprint_switch_on_int_node` creates switch without case exec pins — melee uses int compare cascade. |

---

## 10. Caveats & Known Limitations

- **Widget** `BPW_DarkJediBossHP`: may have no authored children; runtime/native setup or `ConfigureBossHealthBar` required.
- **Switch-on-int**: no per-case exec pins from MCP helper — branching uses `EqualEqual_IntInt` chain for taunts/combo.
- **Graph deletes**: MCP `delete_blueprint_node` often skipped (`force_unsafe_delete` guard); quarantine area holds orphans.
- **`exec_python`**: Editor Python lacks some APIs (`AnimBlueprintLibrary` etc.) for root-motion read; verify ABP in Editor.
- **Placed instances**: Component defaults updated in BP may not refresh existing level instances until re-placed or instance property edited (Sandbox boss blade hidden fixed in-session).

---

## 11. Next Steps

- Rebuild plugin with `Ctrl+Alt+F11`, then playtest perception, saber activation/audio, movement, melee combo, and death.
- Add force-power director states after base locomotion/melee feel stable.
- Add Niagara / VFX for lightning (`ApplyForceLightningEffect`).
- Block / deflect using `RT_SW_LightsaberBlock_Montage` + `saberblock1` / `saberblock2`.
- Finish health bar UMG authoring or native widget construction.
- Arena trigger / encounter scripting.

---

*End of framework log.*
