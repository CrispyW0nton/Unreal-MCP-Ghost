# Phase 3 Demo Menu and Visual Tuning

Date: 2026-06-02

## Purpose

This pass made the playable slice easier to present and tune during PIE without opening editor details panels.

The new demo menu/status layer exposes save/load feedback plus runtime controls for the two strongest player-experience effects:

- post-process distortion intensity
- world-reactive movement/light intensity

## Gameplay Changes

Added a demo menu overlay to the native HUD:

- `P` or `Escape`: open/close demo menu.
- `R`: resume from the demo menu.
- `K`: save the Day 1 demo state with an on-screen success/failure message.
- `L`: load the Day 1 demo state with an on-screen success/failure message.
- `[` / `]`: lower/raise visual distortion intensity.
- `,` / `.`: lower/raise world motion intensity.

The HUD now also shows a `WORLD FEEDBACK` debug section with the post-process and world-reactive summaries.

## Runtime Tuning Changes

Updated `AInsanitiiPostProcessController`:

- Added `VisualIntensityScale` with a 0.0 to 1.5 tuning range.
- Applied the scale to mental-state distortion plus psychosis event pulse.
- Added `GetDebugSummary()` for HUD and MCP/readback use.

Updated `AInsanitiiWorldReactiveDirector`:

- Added `ReactivityScale` with a 0.0 to 1.5 tuning range.
- Applied the scale to the mental-instability/psychosis target intensity.
- Extended `GetDebugSummary()` to include the scale.

## Tooling

Added `scripts/run_insanitii_report.py`.

This local runner registers the existing `unreal_mcp_server/tools/editor_tools.py` reports and invokes them directly. It is useful for repeatable live checks from PowerShell, especially when the Unreal MCP plugin is listening on the project port:

```powershell
$env:UNREAL_PORT='55655'
python scripts\run_insanitii_report.py insanitii_phase3_pie_runtime_report
```

Added `scripts/run_insanitii_demo_tuning_probe.py`.

This probe uses `exec_python` through the Unreal MCP bridge to:

- load `InsanitiiHUD`
- temporarily set `INS_PostProcessController.VisualIntensityScale` to `1.2`
- temporarily set `INS_WorldReactiveDirector.ReactivityScale` to `1.2`
- confirm both debug summaries reflect the tuned values
- restore both values to their original `1.0` defaults

Added `scripts/run_unreal_save_dirty.py`.

This helper asks the open editor to save dirty packages through Unreal MCP before risky workflow steps such as plugin installation or editor shutdown.

## Verification

Closed-editor C++ build:

- Target: `InsanitiiEditor Win64 Development`
- Result: passed

Live Unreal MCP reports were run with:

```powershell
$env:UNREAL_PORT='55655'
```

Results:

- `insanitii_phase3_pie_runtime_report`: passed
  - `hud_class`: `InsanitiiHUD`
  - `station_count`: `9`
  - `exercise_step_count`: `9`
  - `objective_completion_percent`: `1.0`
  - `world_reactivity_tracked_count`: `40`
  - psychosis event fired during stress step
  - PIE stopped cleanly
- `insanitii_save_load_report --wait-seconds 1.0`: passed
  - save succeeded
  - load succeeded
  - save exists
  - day/cash/mental state restored after mutation
- `insanitii_world_reactivity_report`: passed
  - `INS_WorldReactiveDirector` present
  - 40 reactive actors tracked
  - debug summary includes `Scale 1.00`
- `insanitii_audio_feedback_report`: passed
  - 5 audio assets found
  - 5 slots assigned
  - 2 looping assets
- `run_insanitii_demo_tuning_probe.py`: passed
  - HUD class loaded
  - post-process tuned scale read back as `1.2`
  - world reactivity tuned scale read back as `1.2`
  - both restored to `1.0`
- `run_unreal_save_dirty.py`: passed
  - dirty packages saved successfully before the Tripo bridge install attempt

## Notes

The current Unreal MCP plugin for this Insanitii editor session listens on `127.0.0.1:55655`. The Python server defaults to `55655`, so live report commands need `UNREAL_PORT=55655` unless the server configuration is changed.

The user confirmed asset-generation work should use the approved signed-in Chrome/Google session; Tripo and ElevenLabs work should use the already-open authenticated Chrome tabs when those passes resume.
