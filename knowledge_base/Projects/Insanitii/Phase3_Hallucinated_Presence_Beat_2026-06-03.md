# Phase 3 Hallucinated Presence Beat - 2026-06-03

## Goal

Move hallucination surge closer to the long-term goal of people who may or may not be real. The immediate demo beat should spawn visible imagined presences that are distinct from task objects, do not block interactions, and can be verified through MCP without entering PIE.

## Implementation

- Extended `AInsanitiiPsychosisChaser` from a single primitive into a simple humanoid presence:
  - body mesh uses the engine cylinder mesh
  - head mesh uses the engine sphere mesh
  - both components render custom depth
  - hallucination decoys are marked as imagined and do not generate overlap events
- Added presence state:
  - `bImaginedPresence`
  - `PresenceLabel`
  - `SetImaginedPresence(bool)`
  - `IsImaginedPresence()`
- Updated hallucination surge spawning:
  - decoys call `SetImaginedPresence(true)`
  - decoys receive the `InsanitiiHallucination` tag
  - chase events explicitly mark their chaser as non-imagined
- Extended `AInsanitiiPsychosisEventDirector` debug support:
  - `StartPsychosisEventForDebug(EInsanitiiPsychosisEventType)`
  - `StartHallucinationSurgeForDebug()`
  - `GetActiveHallucinationCount()`
  - debug summary now reports hallucination and world-shift counts
- The debug hallucination path can anchor around `PlayerStart` in editor mode, allowing safe non-PIE reflection checks.

## Design Intent

This creates the first visible form of the "is this real?" mechanic. The hallucinations are not yet fully authored characters, but they now read as humanlike presences instead of generic primitives. They can orbit the player during Hallucination Surge, while future passes can replace the silhouette with authored or Tripo-generated character meshes and pair each presence with spatialized voice lines.

## Verification

- Closed-editor C++ build passed through `run_insanitii_clean_build_and_tripo_verify.ps1`.
- Tripo bridge verifier passed before build.
- Relaunched editor and bridge responded with 124 actors.
- `probe_insanitii_hallucinated_presence.py` passed:
  - `StartHallucinationSurgeForDebug()` spawned 5 hallucination actors
  - each actor reports `imagined=true`
  - each actor has both head and body meshes
  - each actor has the `InsanitiiHallucination` tag
  - `EndActivePsychosisEvent()` returned the director to `None` with zero hallucinations
- Regression probes passed:
  - `probe_insanitii_voice_feedback.py`
  - `probe_insanitii_tripo_station_readiness.py`
  - `probe_insanitii_postprocess_vfx.py`
  - `report_insanitii_layout_positions.py` with `max_deviation: 0.0`

## Follow-up

- Replace the simple head/body silhouette with a textured Smart Mesh character or custom hallucination mesh.
- Add a player-facing reality-test interaction that can identify imagined presences at a mental-state cost or reward.
- Attach spatialized friendly/unfriendly voice variants to individual presences.
