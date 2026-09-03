# Phase 3 HUD Objective Marker Fallback - 2026-06-07

## Goal

Make the HUD objective marker reliable after removing the old route/root marker clutter from the level. The marker should still guide the player when the current objective is offscreen or behind the camera, which is the exact moment the player needs help most.

## Work Completed

- Updated `AInsanitiiHUD::DrawObjectiveMarker()` so failed/behind-camera world projection no longer makes the marker disappear.
- Added an edge-of-screen fallback that:
  - computes objective direction in camera-local space.
  - clamps the marker to the visible screen edge.
  - keeps the existing diamond/line/ghosting visual language.
  - labels behind/offscreen objectives as `TURN TO ANCHOR`.
  - clamps marker text to avoid drawing off the viewport.
- Expanded `AInsanitiiHUD::GetObjectiveMarkerDebugSummary()` with:
  - `Behind true/false`.
  - target distance in meters.
- Added `scripts/probe_insanitii_objective_marker_fallback.py` to force/verify behind-camera objective-marker state in PIE.
- Hardened `scripts/probe_insanitii_objective_anchor.py` so objective anchor samples must include behind-camera and distance data.

## Verification

- `python -m py_compile scripts\probe_insanitii_objective_marker_fallback.py scripts\probe_insanitii_objective_anchor.py` passed.
- Clean Unreal build passed after closing the editor:
  - `InsanitiiHUD.cpp` compiled and linked successfully.
- Relaunched Unreal and verified the bridge with `scripts\bridge_ping.py`.
- `python scripts\probe_insanitii_objective_marker_fallback.py` passed:
  - current target `INS_TaskStation_Grounding_Snack`.
  - summary reported `Behind true`.
  - summary reported distance data.
- `python scripts\probe_insanitii_objective_anchor.py` passed:
  - clean, strained, psychosis, and false-cue samples all include confidence/conflict/behind/distance data.
- `python scripts\run_insanitii_report.py insanitii_phase3_pie_runtime_report --wait-seconds 20` passed with no warnings.
- `python scripts\report_insanitii_layout_positions.py` passed with `max_deviation: 0.0`.
- `python scripts\probe_insanitii_tripo_station_readiness.py` passed with all 11 Tripo-owned task stations interactable and no standalone/non-station Tripo mesh actors.

## Current Notes

- The old in-world route/root segment markers remain unnecessary; HUD objective guidance now has explicit behind-camera support.
- The bridge ping still reports the unrelated `BP_BlackHole` introspection warning, but the bridge itself responds normally.
