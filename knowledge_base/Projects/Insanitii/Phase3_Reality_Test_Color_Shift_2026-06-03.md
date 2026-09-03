# Phase 3 Reality Test Color Shift - 2026-06-03

## Goal

Strengthen the sensory language around reality testing. A successful test should briefly feel cooler and clearer, while a failed challenge should briefly feel warmer and more threatening.

## Implementation

- Extended `AInsanitiiPostProcessController` with color-shift controls:
  - `RealityTestColorShiftStrength`
  - `CurrentRealityTestColorShift`
  - `GetRealityTestColorShift()`
- The existing signed reality-test pulse now also drives a signed color shift:
  - success uses a negative/cool shift
  - failure uses a positive/warm shift
- Color shift contributes to post-process saturation and gamma:
  - success leans cooler/clearer
  - failure leans warmer/redder
- `GetDebugSummary()` now includes `ColorShift`.

## Design Intent

The player now gets three aligned feedback channels after testing a hallucinated presence:

1. HUD language confirms the result.
2. Audio confirms success or failure.
3. Post-process distortion and color move in opposite directions depending on whether the test stabilized or destabilized the player.

This gives reality testing a more embodied feel and makes it easier to understand in a playable demo without relying on debug text.

## Verification

- Closed-editor C++ build passed through `run_insanitii_clean_build_and_tripo_verify.ps1`.
- Tripo bridge verifier passed before build.
- Relaunched editor and bridge responded with 124 actors.
- `probe_insanitii_postprocess_vfx.py` passed:
  - `RealityTestColorShiftStrength` is above zero
  - successful reality-test pulse produced a negative color shift
  - failed reality-test pulse produced a positive color shift
  - debug summary includes `ColorShift`
- `probe_insanitii_hallucinated_presence.py` passed:
  - successful reality-test interaction produced a negative clarity pulse
  - successful reality-test interaction produced a negative/cool color shift
  - tested hallucination still hides, disables collision, and becomes non-interactable
- Regression probes passed:
  - `probe_insanitii_voice_feedback.py`
  - `probe_insanitii_tripo_station_readiness.py`
  - `probe_insanitii_station_audio.py`
  - `report_insanitii_layout_positions.py` with `max_deviation: 0.0`

## Follow-up

- Tune `RealityTestColorShiftStrength` manually in PIE for comfort.
- Add a brief screen-edge shimmer for failed threat challenges.
- Replace temporary fallback audio with dedicated ElevenLabs reality-test confirmation/failure cues.
