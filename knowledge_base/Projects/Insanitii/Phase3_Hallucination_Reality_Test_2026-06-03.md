# Phase 3 Hallucination Reality Test - 2026-06-03

## Goal

Turn hallucinated presences into a playable stabilization mechanic. The player should be able to look at an imagined presence, press `E`, and actively reality-test it instead of only enduring the visual event.

## Implementation

- `AInsanitiiPsychosisChaser` now implements `IInsanitiiInteractable`.
- Hallucinated presences use query-only visibility collision:
  - line traces can focus them
  - they do not physically block the player or task stations
- Added reality-test state and tuning:
  - `bRealityTested`
  - `RealityTestStabilizationReward`
  - `RealThreatChallengePenalty`
  - `HasBeenRealityTested()`
- Imagined presences expose the prompt `Reality test this presence`.
- Interacting with an imagined presence:
  - applies a small mental-state stabilization reward when the interactor has `UInsanitiiMentalStateComponent`
  - resets the mental cascade
  - marks the presence as tested
  - hides the head/body meshes
  - disables collision
  - makes the actor no longer interactable
- Interacting with a non-imagined chase threat applies a small penalty, preserving the distinction between false and dangerous presences.

## Design Intent

This makes the *A Beautiful Mind*-inspired uncertainty loop more mechanical:

1. Hallucination Surge spawns humanlike imagined presences.
2. The player can choose to inspect and challenge a presence.
3. Correctly testing an imagined presence stabilizes the player and removes that cue.
4. Challenging an actual chase threat is costly, so the mechanic still carries risk.

The result is a first playable version of "distinguish imagined from real" without waiting on final character art.

## Verification

- Closed-editor C++ build passed through `run_insanitii_clean_build_and_tripo_verify.ps1`.
- Tripo bridge verifier passed before build.
- Relaunched editor and bridge responded with 124 actors.
- `probe_insanitii_hallucinated_presence.py` passed:
  - 5 hallucination actors spawned
  - each actor reports `imagined=true`
  - each has head/body meshes
  - each has the `InsanitiiHallucination` tag
  - each exposes `Reality test this presence`
  - each is interactable before testing
  - one test interaction marks the actor tested
  - tested actor becomes non-interactable
  - tested actor hides both meshes
  - tested actor disables both body and head collision
  - director cleanup returns hallucination count to zero
- Regression probes passed:
  - `probe_insanitii_voice_feedback.py`
  - `probe_insanitii_tripo_station_readiness.py`
  - `probe_insanitii_postprocess_vfx.py`
  - `report_insanitii_layout_positions.py` with `max_deviation: 0.0`

## Follow-up

- Add a HUD status flash for successful/failed reality tests.
- Attach spatialized voice or breath sounds to reality-test outcomes.
- Replace the temporary humanoid silhouette with a textured character mesh.
