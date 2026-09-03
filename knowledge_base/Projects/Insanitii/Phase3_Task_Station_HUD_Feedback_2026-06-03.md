# Phase 3: Task Station HUD Feedback

Date: 2026-06-03

## Goal

Make ordinary task interactions more readable during the playable slice. Completing a task or slipping because of low mental state should produce immediate HUD feedback, not only a label or hidden state change.

## Change

Native HUD:

- Added `AInsanitiiHUD::NotifyTaskStationResult`.
- Added `AInsanitiiHUD::GetDemoStatusDebugSummary` so automation can verify the status-message layer.
- Successful task use now displays `Task complete: <station prompt>.` in green.
- Mental-friction slips now display `Task slipped: stabilize and try again. Friction risk <n>%.` in red.

Native task stations:

- `AInsanitiiTaskStation::OnInteract_Implementation` now notifies the HUD after both successful station use and friction slips.
- The station still plays the existing local success/slip audio and refreshes its in-world label.

Automation:

- Extended `insanitii_phase3_pie_runtime_report` to capture HUD status summaries in PIE snapshots.
- The report now fails if scripted Day 1 station interactions do not produce HUD task-complete feedback.
- The report now forces a low-mental-state grocery-station friction slip after the normal loop and fails if the HUD does not show the task-slip/risk message.
- Added `scripts/probe_insanitii_task_station_hud_feedback.py` as a focused wrapper around the hardened PIE report.

## Verification

Clean closed-editor C++ build passed:

```powershell
.\scripts\run_insanitii_clean_build_and_tripo_verify.ps1
```

PIE runtime feedback probe passed:

```powershell
python scripts\probe_insanitii_task_station_hud_feedback.py
```

Key results:

- `task_complete_status_count: 9`
- `exercise_step_count: 9`
- `report_status: pass`
- forced slip result:
  - `station_used: false`
  - `last_use_succeeded: false`
  - `friction_risk: 1.0`
  - HUD: `Task slipped: stabilize and try again. Friction risk 100%.`

Full Phase 3 PIE runtime report passed with the same HUD coverage:

```powershell
python scripts\run_insanitii_report.py insanitii_phase3_pie_runtime_report --wait-seconds 20
```

Regression probes passed:

- `probe_insanitii_tripo_station_readiness.py`
- `probe_insanitii_station_audio.py`
- `report_insanitii_layout_positions.py` with `max_deviation: 0.0`
- `probe_insanitii_voice_feedback.py`
- `probe_insanitii_postprocess_vfx.py`

## Notes

The first standalone probe attempted to start PIE and inspect it in one direct bridge execution. That repeated the known empty-output PIE quirk. The final probe uses the established async-safe Phase 3 runtime report path instead.

This makes the core ordinary-task loop clearer: success is acknowledged, and low-state task failure explicitly tells the player to stabilize and try again.
