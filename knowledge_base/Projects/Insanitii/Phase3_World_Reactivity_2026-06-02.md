# Phase 3 World Reactivity - 2026-06-02

## Goal

Make the dressed Day 1 route respond to mental-state pressure so the world itself begins to feel unstable, not only the HUD or post-process layer.

This pass adds a native runtime director that tracks the Day 1 set-dressing actors and applies subtle-to-strong environmental distortion as mental state drops or a psychosis event is active.

## Runtime Changes

Added native class:

- `AInsanitiiWorldReactiveDirector`

Behavior:

- Finds actors tagged `InsanitiiWorldReactive`.
- Stores baseline transforms and point-light intensities.
- Each tick, reads the player `UInsanitiiMentalStateComponent`.
- Also reads `AInsanitiiPsychosisEventDirector` to add an event boost while psychosis is active.
- Applies pulsing Z drift, sideways drift, yaw/roll wobble, scale pulses, and point-light intensity pulses.
- Smoothly interpolates `CurrentReactiveIntensity` so the world settles after stabilization.

Tuned placement:

- Actor label: `INS_WorldReactiveDirector`
- Reactive tag: `InsanitiiWorldReactive`
- Tracked actor count after placement: `40`
- Max vertical offset: `34`
- Max yaw: `11`
- Max scale pulse: `0.10`
- Pulse speed: `2.8`
- Psychosis event boost: `0.55`
- Light pulse multiplier: `0.90`

## Tooling Updates

Updated `insanitii_place_day1_set_dressing`:

- Every Day 1 set-dressing actor now gets the `InsanitiiWorldReactive` runtime tag.

Added `insanitii_world_reactivity_report`:

- verifies `InsanitiiWorldReactiveDirector` is visible to Unreal reflection;
- verifies `INS_WorldReactiveDirector` is placed;
- verifies at least 40 tagged Day 1 actors exist;
- calls the director rebind path and verifies it tracks at least 40 actors.

Extended `insanitii_phase3_pie_runtime_report`:

- now reads `world_reactivity_tracked_count`;
- now reads `world_reactivity_intensity`;
- fails if the world-reactive director does not bind the Day 1 set dressing in PIE;
- warns if intensity does not rise during the scripted stress beat.

## Verification

- Closed Unreal Editor and built `InsanitiiEditor` with Unreal Build Tool.
  - Result: succeeded.
  - UHT generated reflection for `InsanitiiWorldReactiveDirector`.
- Reran live `insanitii_place_day1_set_dressing`.
  - Result: `pass`.
  - Placement count: `40`.
  - Level save: `true`.
- Placed `INS_WorldReactiveDirector`.
  - Result: created and saved.
  - Immediate tracked actor count: `40`.
  - Debug summary: `Reactive actors: 40 | Intensity 0.00 | Tag InsanitiiWorldReactive`.
- Live `insanitii_world_reactivity_report`.
  - Result: `pass`.
  - Class visible: `true`.
  - Director present: `true`.
  - Reactive actor count: `40`.
  - Tracked actor count: `40`.
- Live `insanitii_phase3_pie_runtime_report`.
  - Result: `pass`.
  - Station count: `9`.
  - Exercise steps: `9`.
  - Objective completion: `1.0`.
  - World reactivity tracked count: `40`.
  - World reactivity intensity during stress beat: `0.30`.
  - Stress beat psychosis event: `Chase | 24.0s`.
  - PIE stopped cleanly.
- `python -m py_compile unreal_mcp_server\tools\editor_tools.py`: passed.
- `python -m pytest unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py unreal_mcp_server\tests\test_phase12_insanitii_day1_set_dressing.py unreal_mcp_server\tests\test_phase13_insanitii_world_reactivity_report.py`: passed.

## Design Impact

The slice now has four layers of mental-state feedback:

1. HUD/objective state.
2. Post-process distortion and color/contrast shift.
3. Psychosis events: chase, hallucination surge, and world shift.
4. Set-dressing reactivity: the ordinary world pulses, drifts, scales, and flickers as stability drops.

This better supports the user goal that ordinary tasks become increasingly difficult when balance with mental state is lost.

## Remaining Work

- Capture manual possessed-PIE footage to judge whether the motion feels tense or distracting.
- Add accessibility/tuning controls for distortion and world-reactivity strength.
- Replace prototype geometry with generated/authored assets while preserving the `InsanitiiWorldReactive` tag.
- Consider a stronger event-specific response for `WorldShift`, such as temporarily reordering zone signs or intensifying only the current objective area.
