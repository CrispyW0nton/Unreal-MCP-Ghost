# Phase 3 Tripo Station Mesh Ownership Hardening - 2026-06-07

## Goal

Prevent imported Tripo Smart Mesh actors from blocking task-station interaction by making each `INS_TaskStation_*` actor own the appropriate Tripo `StaticMesh` directly on its interactable mesh component.

## Work Completed

- Reapplied `scripts/apply_insanitii_tripo_station_meshes.py` against the live Unreal editor session.
- Confirmed all 11 Day 1 task stations use `/Game/TripoModels/...` meshes directly:
  - sandwich, medication, and sleep use the home/kitchen/bed mesh.
  - grocery uses the checkout/shelves mesh.
  - laundry uses the washer/dryer mesh.
  - package dropoff uses the delivery mesh.
  - commute uses the sedan mesh.
  - work uses the desk mesh.
  - stress/noise uses the noise-cluster mesh.
  - grounding card/snack use the grounding table mesh.
- Hardened `scripts/apply_insanitii_tripo_station_meshes.py` so cleanup removes any non-station actor using a Tripo static mesh, not only labels starting with `INS_Tripo_`.
- Hardened `scripts/probe_insanitii_tripo_station_readiness.py` so future verification fails if any non-station actor still uses a `/Game/TripoModels/` mesh.
- Restored and saved the wide Day 1 play-area layout after a layout report found several floor/path actors and `PlayerStart` had snapped to origin.

## Verification

- `python -m py_compile scripts\apply_insanitii_tripo_station_meshes.py scripts\probe_insanitii_tripo_station_readiness.py` passed.
- `python scripts\redistribute_insanitii_day1_layout.py` passed and saved the level/external actor packages.
- `python scripts\apply_insanitii_tripo_station_meshes.py` passed and saved the current level/dirty packages.
- `python scripts\probe_insanitii_tripo_station_readiness.py` passed:
  - all 11 task stations are interactable.
  - all station prompts are present.
  - all 11 station meshes are Tripo meshes.
  - `standalone_tripo_actors` is empty.
  - `non_station_tripo_mesh_actors` is empty.
- `python scripts\report_insanitii_layout_positions.py` passed with `max_deviation: 0.0`.
- `python scripts\probe_insanitii_task_station_hud_feedback.py` passed after resetting PIE, confirming task interactions and HUD feedback still work after the Tripo mesh ownership pass.

## Notes

- The task-station probe returned a warning that pattern-flood intensity did not rise during the scripted stress beat. That warning is unrelated to the Tripo mesh blocker fix and should be handled in the psychosis visual-effects pass.
