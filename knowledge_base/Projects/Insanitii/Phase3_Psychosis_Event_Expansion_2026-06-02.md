# Phase 3 Psychosis Event Expansion - 2026-06-02

## Scope

This pass made the random psychosis event set more player-facing and testable.

Before this pass:

- `Chase` spawned a pressure actor.
- `HallucinationSurge` applied mental-state drain and post-process intensity.
- `WorldShift` applied mental-state drain and post-process intensity.

After this pass:

- `Chase` remains the direct pursuit event.
- `HallucinationSurge` spawns visible decoy actors around the player and orbits them during the event.
- `WorldShift` temporarily displaces, rotates, and scales the ordinary task stations, then restores their original transforms when the event ends.

This better satisfies the playable-slice requirement that psychosis events include being chased, hallucinating, and the world changing significantly.

## Native Runtime Changes

Updated `AInsanitiiPsychosisEventDirector`:

- Added hallucination tuning:
  - `HallucinationDecoyCount`
  - `HallucinationOrbitRadius`
  - `HallucinationOrbitSpeed`
- Added world-shift tuning:
  - `WorldShiftOffsetRadius`
  - `WorldShiftVerticalOffset`
  - `WorldShiftScaleMultiplier`
- Added runtime state:
  - active hallucination decoys,
  - shifted actors,
  - original transforms for restoration.
- Added behavior:
  - `SpawnHallucinationSurge`
  - `ApplyWorldShift`
  - `RestoreWorldShift`
  - `TickHallucinations`

## Build And Verification

Closed-editor reflected C++ build:

```text
Build.bat InsanitiiEditor Win64 Development -Project=C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Insanitii.uproject -WaitMutex
Result: Succeeded
```

Live editor verification:

- Unreal bridge responded on `127.0.0.1:55655`.
- `INS_PsychosisEventDirector` class path: `/Script/Insanitii.InsanitiiPsychosisEventDirector`.
- Reflected tuning readback:
  - `hallucination_decoy_count`: `5`
  - `hallucination_orbit_radius`: `520.0`
  - `hallucination_orbit_speed`: `1.65`
  - `world_shift_offset_radius`: `260.0`
  - `world_shift_vertical_offset`: `70.0`
  - `world_shift_scale_multiplier`: `1.35`
- `insanitii_phase3_objective_report`: `pass`
  - Objective actor placed: true.
  - Task station count: 5.
  - Current objective: `Make a sandwich before the day starts.`
  - Completion percent: `0.0`.

## Chrome / Content Generation Status

Chrome control through the Codex Chrome plugin still failed twice with:

```text
node_repl kernel exited unexpectedly
windows sandbox failed: setup refresh failed with status exit code: 1
```

The local `ChromeMCP` server tools are available and `chrome_tabs` works against the debug profile on port `9222`, but the exposed tab is currently:

```text
Host Havoc - DayZ | 30 slots | 144.48.104.106:2322
```

It does not expose the already-open ElevenLabs/Tripo tabs from the user's normal Chrome session. `LIM-0007` remains active.

## Remaining Manual PIE Checklist

- Trigger the stress station and confirm each random event type is visible across repeated tests.
- Confirm `WorldShift` restores stations after the event ends.
- Confirm hallucination decoys do not persist after event end.
- Confirm chase pressure still drains mental state at close range.
- Confirm Focus/Breathe remain useful during these more intense events.
