# Phase 3 Reality Test Visual Pulse - 2026-06-03

## Goal

Make reality testing affect the player's perception immediately, not only HUD/audio. Correctly identifying an imagined presence should briefly feel clarifying; challenging a real threat should briefly feel more destabilizing.

## Implementation

- Extended `AInsanitiiPostProcessController` with reality-test pulse controls:
  - `RealityTestSuccessClarityPulse`
  - `RealityTestFailureDistortionPulse`
  - `RealityTestPulseDurationSeconds`
  - `CurrentRealityTestPulse`
  - `TriggerRealityTestPulse(bool bSuccess)`
  - `GetRealityTestPulseStrength()`
- The pulse is signed:
  - successful reality tests apply a negative clarity pulse that lowers effective distortion
  - failed reality tests apply a positive distortion pulse
- The pulse decays over time using squared falloff and contributes to the normal post-process target, so it stacks naturally with mental-state distortion and psychosis event pulses.
- `GetDebugSummary()` now includes `RealityPulse`.
- `AInsanitiiPsychosisChaser` now notifies the post-process controller after a reality-test interaction.

## Design Intent

Reality testing now has a sensory consequence:

1. The player looks at a hallucinated presence.
2. Pressing `E` tests whether it is imagined.
3. If it is imagined, the presence disappears and the world briefly clears.
4. If the player challenges a real threat, the world briefly destabilizes further.

This makes stabilization feel embodied, while preserving the risk of misjudging what is real.

## Verification

- Closed-editor C++ build passed through `run_insanitii_clean_build_and_tripo_verify.ps1`.
- Tripo bridge verifier passed before build.
- Relaunched editor and bridge responded with 124 actors.
- `probe_insanitii_postprocess_vfx.py` passed:
  - success pulse after trigger was negative
  - failure pulse after trigger was positive
  - debug summary includes `RealityPulse`
  - configured pulse magnitudes and duration are above zero
- `probe_insanitii_hallucinated_presence.py` passed:
  - successful reality-test interaction triggered a negative clarity pulse
  - tested hallucination still hides, disables collision, and becomes non-interactable
- Regression probes passed:
  - `probe_insanitii_voice_feedback.py`
  - `probe_insanitii_tripo_station_readiness.py`
  - `probe_insanitii_station_audio.py`
  - `report_insanitii_layout_positions.py` with `max_deviation: 0.0`

## Follow-up

- Tune the pulse duration in manual PIE to ensure it is readable but not nauseating.
- Add a separate subtle color-temperature shift for success versus failure.
- Pair the pulse with dedicated ElevenLabs reality-test audio once final sound variants are generated.
