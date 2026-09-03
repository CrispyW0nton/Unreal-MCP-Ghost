# Insanitii Blueprint Logic Implementation Plan

## Objective

Convert the current "input debug only" state into a real, stable Blueprint gameplay loop with clean event-graph organization and verifiable mechanics behavior.

Current architecture note: this plan is no longer a Blueprint-only constraint. Keep the graph hygiene, event-routing, debug, and PIE verification guidance, but implement each mechanic in native C++, Blueprint, or a native-plus-wrapper split based on the best fit for reliability and iteration.

## Scope for This Plan

- `IA_Focus`
- `IA_Breathe`
- `IA_Interact`
- `IA_DebugDecreaseState`
- `IA_DebugIncreaseState`
- `IA_ToggleHUD`
- Mental state runtime behavior
- Visual distortion hooks
- Interaction contract and prompt loop
- Debug HUD signal quality

## Non-Goals (Current Pass)

- Advanced AI behavior trees
- Content-heavy cinematic or asset production
- Full audio middleware integration

## Blueprint Organization Standard

## `BP_FirstPersonCharacter` responsibilities

- Owns or exposes the active `IA_*` event entry points.
- Routes each input to one dedicated handler path.
- Holds or references canonical gameplay state.
- Emits events or calls wrapper hooks for UI/VFX/audio subscribers.

## Supporting Blueprint assets

- `BP_MentalStateComponent` or native mental-state component wrapper: state math, utility functions, and designer-facing tuning.
- `BP_InteractionDetector` or native interaction component wrapper: trace target resolution only.
- `BPI_Interactable`: interaction entry contract.
- `WBP_DebugHUD`: state visibility and diagnostics.

If components are unstable, consolidate the runtime path first, then re-extract into native components or Blueprint wrappers once behavior is stable.

## Required Event Graph Entry Routing

Each input event should be a two-step pattern:

1. Event node (`Triggered` or appropriate trigger pin).
2. Immediate call to one named function.

Example mapping:

- `IA_Focus` -> `Handle_FocusInput`
- `IA_Breathe` -> `Handle_BreatheInput`
- `IA_Interact` -> `Handle_InteractInput`
- `IA_DebugDecreaseState` -> `Handle_DebugDecreaseMentalState`
- `IA_DebugIncreaseState` -> `Handle_DebugIncreaseMentalState`
- `IA_ToggleHUD` -> `Handle_ToggleHUDInput`

No long logic chains directly off `IA_*` nodes.

## Function-Level Build Plan

## Step 1 - Canonical state + safeguards

Create/normalize variables on `BP_FirstPersonCharacter`:

- `MentalState` float, clamp 0..100
- `FocusActive` bool
- `BreatheActive` bool
- `HUDVisible` bool
- `InteractionTarget` actor ref
- `PsychosisIntensity` float (derived)

Create utility functions:

- `ClampMentalState`
- `RecomputePsychosisIntensity`
- `BroadcastStateChanged`

## Step 2 - Mental-state mutation APIs

Create two dedicated APIs and use only these for state changes:

- `AddMentalStateDelta(float Delta, Name SourceTag)`
- `SetMentalState(float NewValue, Name SourceTag)`

Within these:

- apply clamp
- recompute derived intensity
- emit debug/state dispatcher

## Step 3 - Implement each input function

### `Handle_FocusInput`

- Gate on cooldown/valid state as needed.
- Set `FocusActive = true` with timer-backed exit (`EndFocus`).
- Apply temporary mental-state effect and psychosis-visual modulation.

### `Handle_BreatheInput`

- Gate on cooldown.
- Trigger short stabilization window.
- Apply negative delta to mental stress (or positive recovery, depending sign convention).

### `Handle_InteractInput`

- Call `ResolveInteractionTarget`.
- If target implements `BPI_Interactable`, call interface event.
- Push result to debug HUD and optional prompt text.

### `Handle_DebugDecreaseMentalState`

- Call `AddMentalStateDelta(-DebugStep, "DebugDecrease")`.

### `Handle_DebugIncreaseMentalState`

- Call `AddMentalStateDelta(+DebugStep, "DebugIncrease")`.

### `Handle_ToggleHUDInput`

- Toggle `HUDVisible`.
- Show/hide debug widget.
- Print one-line confirmation message.

## Step 4 - Interaction detector function set

Implement:

- `ResolveInteractionTarget` (line trace from camera forward)
- `UpdateInteractionPrompt` (show/hide + label)

Key constraints:

- Use one trace channel strategy.
- Keep trace params centralized.
- Handle null target and invalid interface cleanly.

## Step 5 - Visual feedback integration

Implement function:

- `ApplyPsychosisVisuals(float Intensity)`

Drive this from `RecomputePsychosisIntensity` and only from there.

Initial target:

- simple post-process scalar and optional camera FX values
- no heavy Niagara coupling until baseline is stable

## Step 6 - Debug visibility and QA hooks

Debug HUD minimum fields:

- current `MentalState`
- `PsychosisIntensity`
- `FocusActive`
- `BreatheActive`
- interaction target name (or None)
- last input action received

Add one optional on-screen test command function:

- `RunMechanicsSelfTest` (simulates deltas and validates clamps)

## Verification Checklist (Must Pass)

## Compile and graph integrity

- All touched native code and Blueprints compile cleanly.
- No missing pins, missing function references, or stale node bindings.

## Input and behavior

- Each key produces expected behavior in PIE:
  - `F`, `Tab`, `E`, `-`, `=`, `H`
- No duplicate-trigger symptoms (single press causes one transition).
- Movement/look remains intact while mechanics run.

## State correctness

- `MentalState` never leaves 0..100.
- `PsychosisIntensity` always reflects mental-state mapping.
- Cooldown-gated actions do not retrigger early.

## UX/debug quality

- HUD toggle works reliably.
- Interaction prompt appears/disappears correctly with target.
- Debug fields update in real time and match actual behavior.

## Implementation Order (Recommended Session Sequence)

1. Normalize state variables and utility functions.
2. Wire all six `IA_*` events to dedicated handlers.
3. Implement debug +/- mental-state handlers first.
4. Implement focus and breathe mechanics.
5. Implement interaction target resolution and interface call.
6. Implement psychosis visual scalar path.
7. Add/clean debug HUD fields.
8. Run full PIE checklist and fix regressions.

## Done Definition for "Real Logic Started"

This phase is complete when:

- all six input actions execute real gameplay functions (not print-only),
- mental-state loop is bounded and visible,
- interaction pipeline calls real interface behavior,
- HUD and visuals reflect state changes in real time,
- and the full verification checklist passes in manual PIE.
