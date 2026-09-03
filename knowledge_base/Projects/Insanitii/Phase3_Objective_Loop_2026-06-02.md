# Phase 3 Objective Loop - 2026-06-02

## Scope

This pass turned the in-world station scaffold into a readable Day 1 objective loop. The player now has a HUD-facing sequence that frames the core Insanitii intent:

1. Make a sandwich.
2. Take medication.
3. Complete Email Triage for pay.
4. Endure an overwhelming stressor.
5. Stabilize after psychosis pressure.
6. Sleep to reach the next morning.

The objective layer sits on top of the native station, lifestyle, mental-state, and psychosis systems from `Phase3_Playable_Slice_Scaffold_2026-06-02.md`.

## Native Runtime Changes

Updated `AInsanitiiTaskStation`:

- Added `FOnInsanitiiTaskStationUsed`.
- Broadcasts station use after successful interaction.
- Keeps station logic reusable for Blueprint wrappers and level scripting.

Added `AInsanitiiSliceObjectiveDirector`:

- Tracks objective step as `EInsanitiiSliceObjectiveStep`.
- Binds to all `AInsanitiiTaskStation` actors in the world.
- Binds to `AInsanitiiPsychosisEventDirector` start/end events.
- Tracks food, medication, work, stress, psychosis survival, and sleep completion.
- Exposes:
  - `GetCurrentObjectiveText`
  - `GetProgressSummary`
  - `GetCompletionPercent`
  - `RebindWorldActors`

Updated `AInsanitiiHUD`:

- Finds `AInsanitiiSliceObjectiveDirector`.
- Draws `DAY 1 OBJECTIVE`.
- Shows current objective text, compact progress summary, and completion bar.

## Level Changes

Placed and saved:

- `INS_SliceObjectiveDirector`

Updated:

- `INS_TaskStation_Stress_OverwhelmingNoise`
  - `MentalStateDelta` set to `0.82`.
  - This is intentionally high for the first playable slice so one clear stress interaction can force mental state below the psychosis threshold and prove the event loop.
- `INS_TaskStation_Work_EmailTriage`
  - Kept deterministic as task index `0`, success enabled.

## Build And Verification

Closed-editor reflected C++ build:

```text
Build.bat InsanitiiEditor Win64 Development -Project=C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Insanitii.uproject -WaitMutex
Result: Succeeded
```

Live editor verification:

- Unreal bridge responded on `127.0.0.1:55655`.
- `INS_SliceObjectiveDirector` placed and saved.
- Reflection sees:
  - `/Script/Insanitii.InsanitiiSliceObjectiveDirector`
  - `/Script/Insanitii.InsanitiiTaskStation`
  - `/Script/Insanitii.InsanitiiPsychosisEventDirector`
- Objective readback:
  - Current objective: `Make a sandwich before the day starts.`
  - Progress: `Food -- | Meds -- | Work -- | Stress -- | Psychosis -- | Sleep --`
  - Completion percent: `0.0`
  - Stress station mental-state delta: `0.82`
- `insanitii_phase1_readiness_report`: `pass`
  - Found 15 `INS_` actors.
  - No warnings or failures.
- `insanitii_phase2_lifestyle_report`: `pass`
  - Lifestyle manager still placed.
  - Generated task count remains 3.
  - Cash remains `$250`.
  - Time remains `Day 1 08:00`.
  - No warnings or failures.
- Added `insanitii_phase3_objective_report` to `unreal_mcp_server/tools/editor_tools.py`.
  - Live result: `pass`.
  - Native class count: 3.
  - Objective actor placed: true.
  - Task station count: 5.
  - Current objective: `Make a sandwich before the day starts.`
  - Completion percent: `0.0`.
- Added offline test coverage:
  - `unreal_mcp_server/tests/test_phase9_insanitii_objective_report.py`
  - Focused report test run: 3 passed.

## Remaining Manual PIE Checklist

Manual possessed PIE is still required before this can be called complete:

- Walk to the sandwich station and confirm objective advances to medication.
- Use medication and confirm objective advances to work.
- Use Email Triage and confirm money/task outcome changes.
- Use the stress station and confirm mental state crosses the psychosis threshold.
- Confirm a random psychosis event starts.
- Stabilize with breathe/focus/food/medication and confirm objective advances to sleep after event recovery.
- Sleep and confirm objective reaches complete and daily living cost applies once.
