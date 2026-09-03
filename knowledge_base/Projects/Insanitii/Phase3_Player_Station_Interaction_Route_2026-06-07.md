# Phase 3 Player Station Interaction Route - 2026-06-07

## Context

The Tripo Smart Mesh assets were already assigned directly to the `INS_TaskStation_*` interactables, with standalone Tripo blocker actors removed. The remaining risk was player-facing: imported mesh collision and irregular bounds could still prevent the possessed first-person pawn from focusing the task station with the normal interaction detector.

## Changes

- Added a hidden `StationFocusTrace` `UBoxComponent` to `AInsanitiiTaskStation`.
  - The focus box is query-only, hidden in game, blocks `Visibility`, ignores physical collision, and is refreshed on construction and begin play from the current station mesh bounds.
  - This keeps Tripo meshes as the visible/base station mesh while giving interaction traces a stable target that does not physically block the player.
- Updated `UInsanitiiInteractionDetectorComponent` to trace from the possessed controller/player viewpoint first.
  - This avoids relying on whichever camera component `FindComponentByClass<UCameraComponent>()` returns from the First Person blueprint.
  - Camera and actor-forward tracing remain as fallback paths.
- Added a narrow view-cone interactable fallback in the detector.
  - If exact `Visibility` trace hits imported collision or a non-interactable blocker, the detector can still select a nearby interactable the player is clearly looking toward.
  - This is intentionally bounded by range, forward projection, and lateral distance so it supports interaction ergonomics without becoming a broad proximity pickup.
- Added `scripts/probe_insanitii_player_station_interaction_route.py` and MCP tool coverage for all 11 Day 1 stations.
  - The probe launches PIE, places the possessed `BP_FirstPersonCharacter_C` at each station approach, aims from the player viewpoint, waits for detector tick, and calls `UInsanitiiInteractionDetectorComponent::AttemptInteract()`.
  - The probe also verifies each station remains backed by a `/Game/TripoModels/` mesh.

## Verification

Closed-editor build:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_insanitii_clean_build_and_tripo_verify.ps1
```

Result: succeeded.

Player-facing interaction route:

```powershell
python scripts\probe_insanitii_player_station_interaction_route.py
```

Result: passed.

Summary:

- `route_count`: 11
- `focus_success_count`: 11
- `prompt_success_count`: 11
- `interaction_success_count`: 11
- `tripo_success_count`: 11
- `stopped_cleanly`: true
- `blocking_dialog_count`: 0

Regression checks:

```powershell
python scripts\probe_insanitii_tripo_station_readiness.py
python scripts\report_insanitii_layout_positions.py
python scripts\probe_insanitii_station_audio.py
python scripts\probe_insanitii_manual_control_readiness.py
python scripts\run_insanitii_report.py insanitii_phase3_pie_runtime_report --wait-seconds 20
```

Results:

- Tripo station readiness passed: all 11 stations are `InsanitiiTaskStation`, interactable, prompted, and directly assigned `/Game/TripoModels/` meshes; no standalone or non-station Tripo mesh actors remain.
- Layout report passed with `max_deviation: 0.0`, preserving the wide saved arena layout.
- Station audio passed: all 11 station foley overrides and shared slip/fallback audio assets exist.
- Manual control readiness passed: possessed pawn, WASD mappings, `Mouse2D -> IA_Look`, movement response, look response, hidden cursor, and clean PIE stop.
- Phase 3 PIE runtime loop passed: Day 1 objective loop, station completion, psychosis start/end, world reactivity, objective marker, task friction, stabilized retry, and completion all verified.

## Notes

This closes the practical blocker behind "Tripo meshes are blocking interactables": the mesh art remains on the gameplay station actor, but interaction no longer depends on fragile imported collision or arbitrary blueprint camera-component ordering.

The remaining manual work is subjective feel: walking the full Day 1 route by hand, listening to the foley/voice mix, and tuning prompt distance or view-cone width if the interaction feels too strict or too generous.
