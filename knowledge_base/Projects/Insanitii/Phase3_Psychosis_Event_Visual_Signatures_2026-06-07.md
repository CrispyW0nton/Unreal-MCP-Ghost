# Phase 3 Psychosis Event Visual Signatures - 2026-06-07

## Intent

Psychosis events now need to feel different from each other in the player's body and camera, not only in spawned actors or shifted props. This pass gives each event family a distinct post-process signature while preserving the existing mental-state distortion, reality-test pulses, task feedback pulses, FOV/DOF system, and locked Day 1 layout.

The design follows the *A Beautiful Mind* direction already recorded for Insanitii: the experience should communicate false certainty, attention capture, and unstable interpretation inside ordinary spaces. The event signatures are intentionally readable in different ways:

- **Chase**: warmer threat color, heavier vignette, faster/wider FOV pulse, and slight focus pressure.
- **Hallucination Surge**: cooler color drift, unstable focus, lower/fluttering saturation, and a narrowed FOV pulse.
- **World Shift**: stronger focus warp, oscillating color/saturation, boosted contrast, and a broader FOV wave.

## Runtime Changes

Updated `AInsanitiiPostProcessController`:

- Added psychosis-event visual tuning properties:
  - `ChaseFOVPulseMultiplier`
  - `ChaseVignetteBoost`
  - `ChaseWarmColorShift`
  - `HallucinationCoolColorShift`
  - `HallucinationFocusPulseStrength`
  - `HallucinationSaturationFlutter`
  - `WorldShiftFocusWarpStrength`
  - `WorldShiftContrastBoost`
  - `WorldShiftFOVWaveMultiplier`
- Added transient runtime readbacks:
  - `CurrentPsychosisEventVisualSignature`
  - `CurrentEventColorShift`
  - `CurrentEventFocusWarp`
  - `CurrentEventSaturationShift`
  - `CurrentEventContrastBoost`
  - `CurrentEventVignetteBoost`
  - `CurrentEventFOVPulseMultiplier`
- Added `GetPsychosisEventVisualDebugSummary()` and extended `GetDebugSummary()` with event visual readbacks.
- Folded event signatures into the existing post-process pipeline:
  - Vignette boost
  - Color saturation/gamma shifts
  - Contrast boost
  - FOV pulse multiplier
  - Depth-of-field focus warp

## Tooling

Added:

- `scripts/probe_insanitii_psychosis_event_visual_signatures.py`

The probe launches PIE, forces each psychosis event, waits for runtime ticks, samples the post-process actor, and verifies that each event reports the expected visual signature and direction.

## Verification

Passed:

- `python -m py_compile scripts\probe_insanitii_psychosis_event_visual_signatures.py scripts\probe_insanitii_postprocess_vfx.py`
- `powershell -ExecutionPolicy Bypass -File scripts\run_insanitii_clean_build_and_tripo_verify.ps1`
- `python scripts\bridge_ping.py`
- `python scripts\probe_insanitii_psychosis_event_visual_signatures.py`
- `python scripts\probe_insanitii_postprocess_vfx.py`
- `python scripts\probe_insanitii_psychosis_event_variety.py`
- `python scripts\probe_insanitii_tripo_station_readiness.py`
- `python scripts\report_insanitii_layout_positions.py`
- `python scripts\run_insanitii_report.py insanitii_phase3_pie_runtime_report --wait-seconds 20`
- `python -m pytest -q unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py unreal_mcp_server\tests\test_phase13_insanitii_world_reactivity_report.py`

Results of note:

- Chase visual sample: `EventColor 0.16`, `EventVignette 0.18`, `EventFOVx 1.55`.
- Hallucination Surge visual sample: `EventColor -0.12`, `EventFocus 0.18`, `EventSaturation -0.17`, `EventFOVx 0.75`.
- World Shift visual sample: `EventColor 0.21`, `EventFocus 0.37`, `EventContrast 0.16`, `EventFOVx 1.25`.
- Tripo station readiness still reports zero standalone/non-station Tripo blockers.
- Layout verification still reports `max_deviation: 0.0`.
- The full Phase 3 PIE runtime report still passes with no warnings or failures.

Automation note:

- `insanitii_phase3_pie_runtime_report` samples the post-process summary immediately after forcing a psychosis event, so that single immediate sample can still show `EventVisual None` before the next post-process tick. The dedicated visual-signature probe waits for PIE ticks and verifies the actual runtime event-specific signatures.

Known unrelated warning:

- `bridge_ping.py` still reports the existing `BP_BlackHole` introspection warning.
