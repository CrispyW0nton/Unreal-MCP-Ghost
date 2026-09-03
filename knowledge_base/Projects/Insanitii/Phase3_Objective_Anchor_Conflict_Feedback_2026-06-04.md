# Phase 3: Objective Anchor Conflict Feedback

Date: 2026-06-04

## Purpose

Make the HUD objective marker behave more like the player's reality anchor instead of a simple debug waypoint. This directly follows the *A Beautiful Mind* direction: ordinary goals should remain grounded, but psychosis and false cues should visibly challenge the player's confidence.

## Runtime Changes

- Updated `AInsanitiiHUD::DrawObjectiveMarker`:
  - false-instruction cues now push the marker into `FALSE CUE CONFLICT`;
  - high instability still shows `ANCHOR STRAIN`;
  - active psychosis still shows `VERIFY OBJECTIVE`;
  - the marker now displays an `Anchor confidence` percentage when the state is strained, stabilizing, or conflicted;
  - the confidence bar drops as mental state worsens and drops further when a false cue is active;
  - false-cue conflict adds stronger jitter/ghosting and the guidance line `Reality test before obeying voices`;
  - marker text flips left near the right side of the screen so it is less likely to run off the viewport.
- Updated `AInsanitiiHUD::GetObjectiveMarkerDebugSummary`:
  - keeps the old `Anchor Clean`, `Anchor Strained`, and `Anchor Verify` labels for probe compatibility;
  - adds `Confidence`, `Conflict`, and `FalseCue` readback.
- Restored/verified `INS_AudioFeedbackDirector` placement through `scripts/restore_insanitii_audio_feedback_director.py`.
  - The actor was present after the level reset and saved with generated audio assets plus four psychosis variants wired.

## Tooling Changes

- Extended `insanitii_phase3_pie_runtime_report` to include:
  - per-snapshot `objective_marker_summary`;
  - `objective_anchor_samples` for clean, strained, psychosis, and false-cue cases.
- Replaced the fragile direct-socket `probe_insanitii_objective_anchor.py` flow with a wrapper around the stable PIE runtime report.
- Updated the offline PIE runtime report fixture to include the existing HUD feedback fields plus the new objective-anchor sample data.

## Live Verification

- Clean C++ build: passed.
  - `InsanitiiHUD.cpp` compiled and linked into `UnrealEditor-Insanitii.dll`.
- `python scripts\restore_insanitii_audio_feedback_director.py`: passed.
  - `INS_AudioFeedbackDirector` saved in the level.
  - debug summary reported room/stress/stabilize assets and four psychosis variants.
- `python scripts\probe_insanitii_objective_anchor.py`: passed.
  - clean: `Anchor Clean | Instability 0.00 | Confidence 1.00 | Conflict false | FalseCue none`
  - strained: `Anchor Strained | Instability 0.85 | Confidence 0.15 | Conflict false | FalseCue none`
  - psychosis: `Anchor Verify | Instability 1.00 | Confidence 0.00 | Conflict true | FalseCue active`
  - false cue: `Anchor Strained | Instability 0.71 | Confidence 0.07 | Conflict true | FalseCue active`
- `python scripts\probe_insanitii_task_station_hud_feedback.py`: passed.
  - nine task-complete statuses;
  - five stabilizing clarity/cooling pulses;
  - forced friction slip still reports HUD and post-process feedback.
- `python scripts\probe_insanitii_voice_feedback.py`: passed.
  - five friendly lines;
  - five unfriendly lines;
  - five false-instruction lines;
  - forced false cue reflected in debug summary.
- `python scripts\probe_insanitii_tripo_station_readiness.py`: passed.
  - all 11 task stations own Tripo meshes directly;
  - no standalone Tripo blockers.
- `python scripts\report_insanitii_layout_positions.py`: passed with `max_deviation: 0.0`.
- `python -m pytest unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py`: passed.
- `python -m py_compile scripts\probe_insanitii_objective_anchor.py scripts\restore_insanitii_audio_feedback_director.py unreal_mcp_server\tools\editor_tools.py unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py`: passed.

## Design Notes

The marker remains trustworthy, but not visually calm, under psychosis pressure. False instructions no longer just appear as subtitles; the anchored objective explicitly reacts by lowering confidence and naming the cue conflict. This gives the player a readable rule:

- voices and false cues can make meaning feel urgent;
- the objective marker is the grounded task reference;
- reality testing and stabilization are the correct response before obeying conflicting instructions.

## Remaining Follow-Up

- Tune exact text placement in manual PIE at 16:9, ultrawide, and lower-resolution windows.
- Add a real HUD widget version once the native debug HUD graduates into production UI.
- Later hallucinated NPCs should withhold this objective-anchor language unless the player has verified them through a reality test.
