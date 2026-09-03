# Phase 3: Task Feedback Visual Pulses

Date: 2026-06-03

## Goal

Make the ordinary-task loop feel more connected to the player's internal state. Task friction should not only fail silently or show text; it should briefly distort the world. Stabilizing actions should visibly settle the world.

## Change

Native post-process controller:

- Added a separate task-feedback pulse layer to `AInsanitiiPostProcessController`.
- Task slips trigger a positive distortion pulse and warm color shift.
- Stabilizing task successes trigger a negative clarity pulse and cool color shift.
- Debug output now includes `TaskPulse` and `TaskColor`.
- New reflected controls:
  - `TaskSlipDistortionPulse`
  - `TaskStabilizeClarityPulse`
  - `TaskFeedbackPulseDurationSeconds`
  - `TaskFeedbackColorShiftStrength`
  - `CurrentTaskFeedbackPulse`
  - `CurrentTaskFeedbackColorShift`

Native task stations:

- Task-friction slips now trigger the task-slip post-process pulse after playing the slip sound and HUD message.
- Stabilizing successes now trigger the clarity/cooling pulse.
- Stabilizing station actions currently include sleep, medication, food, grocery, and laundry when they apply a positive mental-state delta.

Automation:

- `probe_insanitii_postprocess_vfx.py` now verifies the new task pulse properties, trigger functions, signed pulse direction, signed color direction, and debug summary fields.
- `insanitii_phase3_pie_runtime_report` now captures task-feedback pulse values during PIE snapshots.
- `probe_insanitii_task_station_hud_feedback.py` now verifies both task HUD feedback and task post-process feedback.

## Verification

Clean closed-editor C++ build passed:

```powershell
.\scripts\run_insanitii_clean_build_and_tripo_verify.ps1
```

Post-process probe passed:

```powershell
python scripts\probe_insanitii_postprocess_vfx.py
```

Key VFX values:

- `task_stabilize_pulse_after_trigger: -0.22`
- `task_stabilize_color_shift_after_trigger: -0.12`
- `task_slip_pulse_after_trigger: 0.28`
- `task_slip_color_shift_after_trigger: 0.12`

PIE task-feedback probe passed:

```powershell
python scripts\probe_insanitii_task_station_hud_feedback.py
```

Key PIE results:

- `task_complete_status_count: 9`
- `stabilizing_pulse_status_count: 5`
- forced friction slip:
  - `station_used: false`
  - `last_use_succeeded: false`
  - `friction_risk: 1.0`
  - HUD: `Task slipped: stabilize and try again. Friction risk 100%.`
  - `friction_slip_task_pulse: 0.28`
  - `friction_slip_task_color_shift: 0.12`

Regression probes passed:

- `probe_insanitii_tripo_station_readiness.py`
- `probe_insanitii_station_audio.py`
- `report_insanitii_layout_positions.py` with `max_deviation: 0.0`
- `probe_insanitii_voice_feedback.py`
- `probe_insanitii_hallucinated_presence.py`

## Notes

This builds on the task-station HUD feedback pass. The same station interaction now produces a coherent package: localized sound, HUD message, in-world label feedback, and a brief post-process pulse that reflects whether the player's state destabilized or settled.
