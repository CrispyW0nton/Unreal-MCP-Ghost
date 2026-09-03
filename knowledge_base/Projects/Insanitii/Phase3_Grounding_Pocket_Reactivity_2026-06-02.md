# Phase 3 Grounding Pocket and Reactivity Mobility

Date: 2026-06-02

## Purpose

Add a clearer stabilization affordance after the stress/psychosis beat without changing native C++ while the editor is open.

The Day 1 loop already supports stabilization through `Food`, `Medication`, `Focus`, and `Breathe`. This pass adds a visible late-route grounding pocket near the stress/noise area with reusable station actions that use the existing `Food` and `Medication` mechanics.

## Level Additions

Added and saved the following grounding pocket actors in `Lvl_FirstPerson`:

- `INS_Day1_Path_GroundingFloor`
- `INS_Day1_Grounding_BreathWall`
- `INS_Day1_Grounding_CountObjects`
- `INS_Day1_Grounding_WaterCup`
- `INS_Day1_Sign_Grounding`
- `INS_Day1_Sign_Grounding_Instructions`
- `INS_Day1_Light_Grounding`
- `INS_TaskStation_Grounding_Card`
- `INS_TaskStation_Grounding_Snack`

The two new gameplay stations are reusable:

- `INS_TaskStation_Grounding_Card`
  - action: `MEDICATION`
  - prompt: `Ground Yourself`
  - mental state delta: `+0.35`
- `INS_TaskStation_Grounding_Snack`
  - action: `FOOD`
  - prompt: `Eat and Breathe`
  - mental state delta: `+0.25`

All nine new actors are tagged `InsanitiiWorldReactive`.

## Tooling

Added `scripts/place_insanitii_grounding_pocket.py`.

This helper places or updates the grounding-pocket actors and saves the current level. It is idempotent by actor label.

Added `scripts/fix_insanitii_reactive_mobility.py`.

This helper sets all actors tagged `InsanitiiWorldReactive` to movable component mobility, then saves the level. This addresses PIE log warnings where the world-reactive director attempted to move static mesh/light components.

Added `scripts/reset_insanitii_editor_play_state.py`.

This helper asks Unreal to end any active PIE state, save dirty packages, reload `/Game/FirstPerson/Lvl_FirstPerson`, and save the level.

Added `scripts/probe_unreal_play_start.py`.

This helper probes `LevelEditorSubsystem.editor_request_begin_play()` and `EditorLevelLibrary.editor_play_simulate()` and reports whether a PIE world appears.

## Verification

Placement helper result:

- created/updated all grounding pocket actors
- created both grounding task stations
- saved current level
- no errors

Mobility helper result:

- updated all 49 reactive actors/components to movable
- saved current level
- no errors

Live `insanitii_world_reactivity_report`:

- status: pass
- reactive actor count: `49`
- tracked actor count: `49`
- debug summary: `Reactive actors: 49 | Scale 1.00 | Intensity 0.00 | Tag InsanitiiWorldReactive`

Focused offline regression:

```powershell
python -m pytest `
  unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py `
  unreal_mcp_server\tests\test_phase10_insanitii_audio_feedback_report.py `
  unreal_mcp_server\tests\test_phase13_insanitii_world_reactivity_report.py `
  unreal_mcp_server\tests\test_phase14_insanitii_save_load_report.py `
  unreal_mcp_server\tests\test_editor_take_screenshot_params.py
```

Result:

- `5 passed`
- one existing pytest cache warning

## PIE Limitation In Current Editor Session

After this editor-only placement pass, direct play-start probes could not create a PIE world:

- `LevelEditorSubsystem.editor_request_begin_play()`: no PIE world
- `EditorLevelLibrary.editor_play_simulate()`: no PIE world
- `insanitii_phase3_pie_runtime_report`: failed because no PIE world/pawn/HUD appeared
- `insanitii_save_load_report`: failed because the PIE launch did not produce the runtime mental-state component

The level is saved and editor-world reports still work. This appears to be the same long-lived editor session problem seen during the Tripo install attempt: Unreal remains open and responsive, but it will not close gracefully and now will not enter PIE through automation.

Safe next step for runtime verification is to manually restart Unreal Editor, or explicitly approve force-closing after confirming no unsaved work remains.
