# Objective System — Framework Log
**Date**: 2026-05-04
**Phase**: E.1-E.8 scaffold
**Level**: `/Game/Sandbox.Sandbox`
**Compile Status**: pass via bridge `compile_blueprint` (`had_errors: false`; deferred compile, save in UE)

---

## 1. Assets Created

| Asset | Path | Status |
|---|---|---|
| Objective manager | `/Game/EndarSpire/Objectives/BP_ObjectiveManager` | Created, variables/events scaffolded |
| Locked door | `/Game/EndarSpire/Objectives/BP_LockedDoor` | Created, simple `UnlockDoor` event scaffolded |
| Terminal | `/Game/EndarSpire/Objectives/BP_Terminal` | Created, `BPI_Interactable` listed, interaction scaffolded |
| Interactable interface | `/Game/EndarSpire/Objectives/BPI_Interactable` | Created with `Interact(Caller: Actor)` |
| Objective HUD | `/Game/EndarSpire/UI/WBP_ObjectiveHUD` | Created as placeholder; Designer layout is manual |

---

## 2. Objective Manager Variables

| Variable | Type | Default | Instance Editable | Purpose |
|---|---|---:|---|---|
| `CurrentObjective` | Integer | `0` | No | 0=none, 1=reactor, 2=bridge, 3=escape, 4=complete |
| `bObjectivesStarted` | Boolean | `false` | No | True after objective flow starts |
| `CountdownTimeRemaining` | Float | `300.0` | No | Five-minute countdown |
| `bCountdownActive` | Boolean | `false` | No | Timer active state |
| `bLevelComplete` | Boolean | `false` | No | Victory reached |
| `bLevelFailed` | Boolean | `false` | No | Timer expired |
| `ReactorDoor` | Actor | None | Yes | Door opened by Objective 1 |
| `BridgeDoor` | Actor | None | Yes | Door opened by Objective 2 |
| `ReactorTerminal` | Actor | None | Yes | Objective 1 target |
| `BridgeTerminal` | Actor | None | Yes | Objective 2 target |
| `EscapePodTerminal` | Actor | None | Yes | Objective 3 target |
| `WaypointTarget` | Actor | None | No | Current HUD waypoint target |
| `CountdownTimerHandle` | TimerHandle | None | No | Countdown timer handle |
| `ObjectiveText` | String | `""` | No | HUD objective display |
| `IntroVideoPath` | String | `""` | Yes | Future MediaPlayer intro source |
| `VictoryVideoPath` | String | `""` | Yes | Future MediaPlayer victory source |
| `DestructionVideoPath` | String | `""` | Yes | Future MediaPlayer destruction source |
| `CutsceneMediaPlayer` | MediaPlayer | None | Yes | Future shared MediaPlayer asset |
| `bCutscenePlaying` | Boolean | `false` | No | Future cutscene input guard |

---

## 3. Event Wiring Status

| Event | Status |
|---|---|
| `ReceiveBeginPlay` | Directly prints intro stub and starts Objective 1 setup |
| `PlayIntroCutscene` | Stub exists; print-string only |
| `OnIntroCutsceneEnd` | Stub exists; print-string only |
| `StartObjectives` | Event exists; variable-set chain for objective 1 also wired through BeginPlay |
| `CompleteObjective1` | Stub chain sets objective 2 state, starts a one-second timer node, and updates waypoint target |
| `CompleteObjective2` | Stub chain sets objective 3 state and updates waypoint target |
| `CompleteObjective3` | Stub chain marks level complete and sets `ObjectiveText = "Escape!"` |
| `OnCountdownTick` | Stub exists; decrement/check logic still needs graph pass |
| `OnCountdownExpired` | Stub chain marks level failed and prints destruction stub |
| `PlayVictoryCutscene` | Stub exists for MediaPlayer phase |
| `PlayDestructionCutscene` | Stub exists for MediaPlayer phase |

Tool limitation: custom event call nodes were created with no exec pins in this session, so BeginPlay uses a direct runtime path instead of calling `PlayIntroCutscene -> OnIntroCutsceneEnd -> StartObjectives`.

---

## 4. Door and Terminal Status

`BP_LockedDoor` has `DoorMesh`, `BlockingVolume`, and variables `bIsLocked`, `OpenOffset`, `OpenSpeed`, `bIsOpening`, and `DoorStartLocation`. `UnlockDoor` currently prints a message, sets `bIsLocked = false`, disables actor collision, and hides the actor.

`BP_Terminal` has `TerminalMesh`, `InteractTrigger`, `InteractPromptWidget`, and variables `bHasBeenUsed`, `bPlayerInRange`, `ObjectiveManager`, `ObjectiveNumber`, `TerminalSound`, and `ManagerEventName`. It implements/listed `BPI_Interactable` and has an `IA_Interact` print/set-used scaffold. The live bridge could not bind overlap events, and manager-event invocation still needs a follow-up graph pass.

---

## 5. Level Placement

| Actor Label | Blueprint | Location | Purpose |
|---|---|---|---|
| `BP_ObjectiveManager_PhaseE` | `BP_ObjectiveManager` | `(-25075, 11906, -1900)` | Objective state manager |
| `BP_ReactorLockedDoor_PhaseE` | `BP_LockedDoor` | `(-30440, 9428, -2098)` | Reactor to central blocker |
| `BP_BridgeLockedDoor_PhaseE` | `BP_LockedDoor` | `(-33272, 10365, -2098)` | Central to starboard blocker |
| `BP_ReactorTerminal_PhaseE` | `BP_Terminal` | `(-25250, 11250, -2100)` | Objective 1 terminal |
| `BP_BridgeTerminal_PhaseE` | `BP_Terminal` | `(-32650, 10050, -2100)` | Objective 2 terminal |
| `BP_EscapePodTerminal_PhaseE` | `BP_Terminal` | `(-40550, 12250, -1735)` | Objective 3 terminal |

Instance references were assigned after marking the relevant variables instance editable.

---

## 6. Manual Setup Checklist

1. Open each new Blueprint once and compile/save with Ctrl+S.
2. In `WBP_ObjectiveHUD`, add a Canvas Panel root, `ObjectiveTextBlock`, `TimerTextBlock`, and gold `WaypointArrow` image.
3. Add HUD creation to the player/controller once the widget layout exists.
4. Finish `BP_Terminal` so interact calls `ObjectiveManager.ManagerEventName` or branches on `ObjectiveNumber` to call `CompleteObjective1/2/3`.
5. Finish `OnCountdownTick` to decrement `CountdownTimeRemaining` and call `OnCountdownExpired` at zero.
6. Replace the cutscene print stubs with the future MediaPlayer overlay system.
7. Replace placeholder cube meshes with final terminal/door art and adjust transforms in the level.

---

## 7. Plugin/Tool Notes

- `add_input_mapping` successfully added `E` to `IA_Interact` in `IMC_Default_Destiny`.
- Live bridge did not expose UMG helper commands (`add_canvas_panel_to_widget`, `add_image_to_widget`), so HUD internals are manual.
- `add_overlap_event` and `add_enable_disable_input_node` returned errors in direct bridge mode.
- Custom event call nodes returned zero pins, so manager event calls remain a follow-up wiring item.
- `bp_get_compile_diagnostics` was unavailable through the direct bridge, but `compile_blueprint` returned `had_errors: false` for the relevant assets.

---

## 8. Phase E.FIX Wiring Update

**Date**: 2026-05-04
**Compile Status**: pass via bridge `compile_blueprint` (`had_errors: false`; deferred compile, save in UE)

- Added `PendingObjectiveCompletion` to `BP_ObjectiveManager` and used it as the terminal-to-manager handshake. The player trace writes the hit terminal's `ObjectiveNumber` into this manager variable.
- Added a `ReceiveTick` router on `BP_ObjectiveManager`: pending value `1` completes the reactor objective, pending value `2` completes the bridge objective, and pending value `3` completes the escape objective. This avoids cross-actor custom event call nodes.
- Wired direct door unlock behavior in the manager router by calling `SetActorEnableCollision(false)` and `SetActorHiddenInGame(true)` on `ReactorDoor` and `BridgeDoor`.
- Added `TimerDisplayText` and wired `OnCountdownTick` to decrement `CountdownTimeRemaining` by `1.0`, update `TimerDisplayText` as a raw numeric string, and trigger the destruction stub when time reaches zero.
- Added a player-owned `IA_Interact` trace chain on `BP_TitanCharacter_P1`: camera location + forward vector * 300, `LineTraceSingle`, cast hit actor to `BP_Terminal`, cast its `ObjectiveManager` to `BP_ObjectiveManager`, then set `PendingObjectiveCompletion`.
- Disabled `BP_Terminal` `AutoReceiveInput` after the player trace path was wired, so all placed terminals do not fire globally on `E`.

Remaining manual work: `WBP_ObjectiveHUD` Designer layout and the later MediaPlayer overlay pass for intro/victory/destruction cutscenes.

---

## 9. Phase E.WIDGET + Intro Registration Update

**Date**: 2026-05-04
**Compile Status**: pass via bridge `compile_blueprint` (`had_errors: false`; deferred compile, save in UE)

- Upgraded the UMG widget bridge commands and changed the live mutation path so `widget_add_child`, `widget_set_property`, and `widget_set_anchor` mark widget Blueprints dirty instead of compiling after every edit. This avoided the editor crash seen during the first widget-tree mutation attempt.
- Built `WBP_ObjectiveHUD` directly through the new widget tools:
  - `RootCanvas` (`CanvasPanel`) is the root widget.
  - `ObjectiveTextBlock` (`TextBlock`) is anchored top-left at `(20, 20)`, size `(500, 40)`, text `Objective`, font size `18`, white.
  - `TimerTextBlock` (`TextBlock`) is anchored top-right at `(-150, 20)`, size `(130, 40)`, alignment `(1, 0)`, text `5:00`, font size `24`, white.
  - `WaypointArrow` (`Image`) is centered, size `(40, 40)`, alignment `(0.5, 0.5)`, gold tint `(1.0, 0.84, 0.0, 1.0)`.
  - All four widgets are marked `Is Variable`.
- Added `ObjectiveManagerRef` to `WBP_ObjectiveHUD`. On Construct, it finds `BP_ObjectiveManager` with `GetActorOfClass` and caches the result. On Tick, it casts that reference, updates `ObjectiveTextBlock` from `ObjectiveText`, updates `TimerTextBlock` from `TimerDisplayText`, and toggles timer visibility from `bCountdownActive`.
- Added `WBP_ObjectiveHUD` creation to `BP_TitanCharacter_P1` at the end of the existing BeginPlay initialization chain: `CreateWidget(WBP_ObjectiveHUD)` then `AddToViewport` with Z-order `10`.
- Registered `IntroVideoPath` on `BP_ObjectiveManager` as `/Game/EndarSpire/Movies/Intro/FinishedIntroMovie`.
- Rewired the intro stub flow: `ReceiveBeginPlay -> DisableInput(player pawn) -> PlayIntroCutscene -> PrintString intro stub -> OnIntroCutsceneEnd -> EnableInput(player pawn) -> StartObjectives`.

Remaining manual work:

1. Press Ctrl+S in Unreal to save modified assets.
2. Open/compile the modified Blueprints once in the editor if Unreal shows deferred compile state.
3. Replace the default `WaypointArrow` brush with a real arrow/triangle texture if desired.
4. Implement the full MediaPlayer overlay pass for intro/victory/destruction MP4 playback.

---

## 10. Phase E.MATHFIX + Cutscene Asset Registration

**Date**: 2026-05-04
**Compile Status**: pass via bridge `compile_blueprint` (`had_errors: false`; deferred compile, save in UE)

- Rescanned `/Game/EndarSpire/Movies` after `TimerFailMovie` was imported. Registered the current movie asset paths on `BP_ObjectiveManager`:
  - `IntroVideoPath`: `/Game/EndarSpire/Movies/Intro/FinishedIntroMovie`
  - `VictoryVideoPath`: `/Game/EndarSpire/Movies/End/End`
  - `DestructionVideoPath`: `/Game/EndarSpire/Movies/TimerFail/TimerFailMovie`
- Deleted three orphaned broken call-function nodes from `BP_ObjectiveManager` that referenced nonexistent member functions: `Conv_FloatToString`, `Subtract_FloatFloat`, and `LessEqual_FloatFloat`.
- Verified the live `OnCountdownTick` graph uses valid pure Kismet real/double nodes for the countdown chain: `Subtract_DoubleDouble`, `Conv_DoubleToString`, and `LessEqual_DoubleDouble`.
- Tightened the countdown expiry path so the true branch clears `CountdownTimerHandle`, sets `bCountdownActive = false`, then calls the centralized `OnCountdownExpired` stub.
- Verified the cutscene stub events still exist on `BP_ObjectiveManager`: `PlayIntroCutscene`, `OnIntroCutsceneEnd`, `PlayVictoryCutscene`, `PlayDestructionCutscene`, and `OnCountdownExpired`.
- Compile-checked `BP_ObjectiveManager`, `BP_Terminal`, `BP_LockedDoor`, `WBP_ObjectiveHUD`, and `BP_TitanCharacter_P1`; all returned `had_errors: false`.

Remaining manual work:

1. Press Ctrl+S in Unreal to save modified assets.
2. Playtest the objective flow from terminal interaction through countdown expiry.
3. Implement the full MediaPlayer overlay pass for the three registered movie sources.

---

## 11. Phase E Playtest Bug Fixes

**Date**: 2026-05-04
**Compile Status**: pass via Unreal `BlueprintEditorLibrary.compile_blueprint` and bridge `compile_blueprint` (`had_errors: false`)

- Fixed `BP_ObjectiveManager` intro-start runtime errors by removing the null-prone `GetPlayerPawn -> DisableInput` and `GetPlayerPawn -> EnableInput` nodes from the stub cutscene flow. The current playtest path is now `ReceiveBeginPlay -> PlayIntroCutscene -> OnIntroCutsceneEnd -> StartObjectives`.
- Updated `WBP_ObjectiveHUD` so `WaypointArrow` no longer remains fixed at the crosshair. The Tick graph now reads `WaypointTarget`, gets the target actor location, projects it with `ProjectWorldLocationToScreen`, sets the arrow's Canvas Panel slot position, and then shows the arrow.
- Added a `PlayerDeath` custom event to `BP_TitanCharacter_P1` and wired it to the existing `ResetLevel` event. This lets the native Dark Jedi boss lethal-damage bridge call a standard player death handler when boss damage drops player `HP` to zero.
- Recompiled and refreshed `BP_ObjectiveManager`, `WBP_ObjectiveHUD`, `BP_TitanCharacter_P1`, `BP_Terminal`, and `BP_LockedDoor`.

Current cutscene status: intro/victory/destruction are still print-string stubs. The real fullscreen MP4 MediaPlayer overlay remains a follow-up implementation pass.

---

## 12. Phase E Repair Pass: Objectives, Death, Boss Targeting, Cutscenes

**Date**: 2026-05-04
**Compile Status**: Blueprint pass via bridge `compile_blueprint` (`had_errors: false`; deferred compile, save in UE). C++ build blocked by active Live Coding; rebuild with Ctrl+Alt+F11 or close UE and run UBT.

- Removed the temporary `PlayerDeath -> ResetLevel` alias from `BP_TitanCharacter_P1`. The Dark Jedi boss C++ path now uses regular `UGameplayStatics::ApplyDamage` instead of directly setting player HP/death flags, so boss kills should follow the same player death/respawn path as Sith troopers after plugin rebuild.
- Updated the Dark Jedi native director in both plugin source copies so the boss acquires the nearest visible player or Republic soldier. Entering combat against Republic soldiers activates saber, saber hum, movement, slashes, force powers, and normal damage delivery.
- Fixed the reactor and bridge objective door chains in `BP_ObjectiveManager`: each unlock path now disables actor collision, then executes `SetActorHiddenInGame(true)`, then advances the objective.
- Fixed countdown timer startup: the timer nodes now call `OnCountdownTick` every `1.0` second, looping, with `Object` wired to self. Reactor objective completion also sets `TimerDisplayText` to `5:00` before enabling `bCountdownActive`.
- Created MediaPlayer overlay assets:
  - `/Game/EndarSpire/Movies/MP_ObjectiveCutscene`
  - `/Game/EndarSpire/Movies/MT_ObjectiveCutscene`
  - `/Game/EndarSpire/UI/WBP_CutsceneOverlay`
- Wired `BP_ObjectiveManager` cutscene events:
  - `PlayIntroCutscene` creates the overlay, opens `/Game/EndarSpire/Movies/Intro/FinishedIntroMovie`, plays it, then calls `OnIntroCutsceneEnd` after a short timer. Cleanup removes the overlay before `StartObjectives`.
  - `PlayVictoryCutscene` creates the overlay, opens `/Game/EndarSpire/Movies/End/End`, plays it, then calls `OnVictoryCutsceneEnd` to clean up and print `LEVEL COMPLETE`.
  - `PlayDestructionCutscene` creates the overlay, opens `/Game/EndarSpire/Movies/TimerFail/TimerFailMovie`, plays it, then calls `OnDestructionCutsceneEnd` to clean up and reopen `CombatLevel_2`.

Remaining manual work:

1. Rebuild the plugin C++ changes with Ctrl+Alt+F11 while Unreal is open, or close Unreal and run the UBT build.
2. Press Ctrl+S in Unreal to save modified Blueprint/widget/media assets.
3. Playtest the cutscene durations; the current Blueprint flow uses fixed cleanup timers rather than binding to MediaPlayer `OnEndReached`.

---

## 13. Phase E Small Stabilization: Cutscene Surface, HUD Timer, Terminal Markers

**Date**: 2026-05-04
**Compile Status**: pass via bridge `compile_blueprint` (`had_errors: false`; deferred compile, save in UE)

- Rebuilt `/Game/EndarSpire/UI/WBP_CutsceneOverlay` through the UMG widget tools. The widget now has:
  - `RootCanvas` as the root `CanvasPanel`.
  - `CutsceneImage` as a fullscreen `Image`, anchored `(0,0)-(1,1)`, visible, and marked variable.
- Re-linked `/Game/EndarSpire/Movies/MT_ObjectiveCutscene` to `/Game/EndarSpire/Movies/MP_ObjectiveCutscene`, and reapplied `BP_ObjectiveManager` defaults for `CutsceneMediaPlayer`, `IntroMediaSource`, `VictoryMediaSource`, and `DestructionMediaSource`.
- Fixed the `WBP_ObjectiveHUD` timer execution order. `TimerTextBlock` visibility is now driven directly after setting timer text, instead of waiting for the old waypoint projection branch to succeed.
- Hid the old screen-space `WaypointArrow` in `WBP_ObjectiveHUD`; objective guidance is now moved to terminal-mounted world markers.
- Added terminal-mounted text components to `BP_Terminal`:
  - `ActivationPromptText` at `Z=190`, intended to display `Press E to activate`.
  - `ObjectiveWaypointText` at `Z=260`, intended as the gold world-space objective marker.

Note: TextRender component text/color assignment through the current bridge is partially limited (`set_component_property` does not support `TextProperty` or `TextRenderColor` yet). The components are present and visible; if the text defaults do not appear correctly in UE, set `ActivationPromptText.Text` to `Press E to activate` and `ObjectiveWaypointText.Text` to `OBJECTIVE` in the BP editor Details panel, or extend the bridge property setter to support `FText`/`FColor`.
