# Phase 3 Hallucinated Instruction Beat - 2026-06-03

## Goal

Add a playable psychosis beat inspired by the *A Beautiful Mind* direction: voices should not only comment on the player, but sometimes give misleading instructions that directly compete with the grounded Day 1 objective loop.

## Implementation

- Extended `AInsanitiiAudioFeedbackDirector` with a false-instruction subtitle state:
  - `FalseInstructionLines`
  - `CurrentFalseInstructionLine`
  - `bFalseInstructionActive`
  - `GetCurrentFalseInstructionLine()`
  - `HasActiveFalseInstruction()`
  - `TriggerFalseInstructionForDebug()`
- Psychosis starts now force both:
  - an unfriendly voice line
  - a timed false instruction cue
- High instability can resurface a false cue while psychosis is active or mental state is critically low.
- The HUD now renders the false instruction as an `unverified cue` below the voice subtitle while the objective marker remains the reality anchor.
- `GetDebugSummary()` now includes `falseCue=...` so MCP probes and manual debugging can see whether hallucinated instructions are active.

## Built-in False Instruction Lines

- Ignore the marker. The package goes somewhere else.
- Skip the groceries. The shelves are watching.
- Do not go home. The bed is a trap.
- Drive away from work. The road knows.
- Leave the laundry. It is not yours.

## Design Intent

The feature creates a clearer moment-to-moment psychosis friction loop:

1. The grounded task system tells the player what ordinary action matters.
2. The objective marker stays visually present as the reality anchor.
3. Psychosis voices produce a conflicting cue that sounds urgent but is explicitly unverified.
4. The player must stabilize, check the objective, and continue the ordinary task instead of obeying the false instruction.

This preserves player agency while making hallucination pressure mechanical instead of purely cosmetic.

## Verification

- Closed-editor C++ build passed through `run_insanitii_clean_build_and_tripo_verify.ps1`.
- Tripo bridge verifier passed before build.
- Relaunched editor and bridge responded with 124 actors.
- `probe_insanitii_voice_feedback.py` passed:
  - five friendly lines
  - five unfriendly lines
  - five false instruction lines
  - debug voice trigger active
  - debug false instruction trigger active
  - debug summary includes `voice=` and `falseCue=`
- `probe_insanitii_tripo_station_readiness.py` passed:
  - all 11 task stations remain interactable
  - all station mesh components use Tripo StaticMesh assets
  - no standalone `INS_Tripo_*` blockers remain
- `probe_insanitii_postprocess_vfx.py` passed.
- `report_insanitii_layout_positions.py` passed with `max_deviation: 0.0`.

## Follow-up

- Replace subtitle-only false cues with spatialized ElevenLabs voice variants once the station Foley/download history is ready.
- Add hallucinated NPCs that appear during psychosis and can be tested against objective/state cues.
- Add a dedicated HUD affordance for grounding checks so the player has a diegetic way to reject unverified instructions.
