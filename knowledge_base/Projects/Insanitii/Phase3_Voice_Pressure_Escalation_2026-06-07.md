# Phase 3 Voice Pressure Escalation - 2026-06-07

## Context

The playable slice already had native friendly and unfriendly voice lines, hallucinated false instructions, objective-anchor conflict feedback, and psychosis audio stingers. The remaining gap was that the voice layer could feel too binary: quiet until debug or psychosis beats, then suddenly intrusive. This pass makes the voices escalate in staged pressure as mental state drops, with a clearer recovery path after psychosis ends.

The exposed Chrome debug session did not provide an authenticated ElevenLabs tab during this continuation. It only showed an unrelated tab; navigating the tab to ElevenLabs reached the sign-in page. Because downloaded ElevenLabs station Foley was not available through that exposed session, this pass focused on improving the in-engine voice behavior with the existing audio director and generated/imported audio assets.

## Runtime Changes

- Added `EInsanitiiVoicePressureState` to `AInsanitiiAudioFeedbackDirector` with four stages: `Quiet`, `Anchor`, `Intrusive`, and `Psychosis`.
- Added staged thresholds:
  - `VoicesStartBelowMentalState`
  - `IntrusiveVoicesBelowMentalState`
  - `FalseCueBelowMentalState`
- Added `CurrentVoicePressureState` readback and `ForceVoicePressureForDebug(float MentalState, bool bPsychosisActive)` for deterministic automation probes.
- Voice pressure now reacts immediately when mental state crosses meaningful thresholds:
  - `Quiet`: clears stale false instructions and delays the next voice beat.
  - `Anchor`: starts a softer anchor/voice beat as strain begins and keeps false cues cleared.
  - `Intrusive`: forces an unfriendly voice line and shortens the false-cue cadence.
  - `Psychosis`: forces an unfriendly voice line and a false instruction immediately.
- Psychosis end now clears active false instructions, resets false-cue timers, recomputes the current voice pressure state, and restores objective-marker confidence.
- `GetDebugSummary()` now includes pressure state, whether the current voice is friendly, next voice timing, and false-cue timing.

## Verification

Closed-editor C++ rebuild succeeded with:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_insanitii_clean_build_and_tripo_verify.ps1
```

Runtime verification passed after relaunching Unreal Editor:

```powershell
python scripts\probe_insanitii_voice_feedback.py
python scripts\run_insanitii_report.py insanitii_audio_feedback_report
python scripts\probe_insanitii_tripo_station_readiness.py
python scripts\report_insanitii_layout_positions.py
python scripts\run_insanitii_report.py insanitii_phase3_pie_runtime_report --wait-seconds 20
```

Key results:

- Voice reflection sees five friendly lines, five unfriendly lines, and five false instruction lines.
- `ForceVoicePressureForDebug(0.52, false)` reaches `pressure=Anchor` with an active voice and no false cue.
- `ForceVoicePressureForDebug(0.26, false)` reaches `pressure=Intrusive` with an active unfriendly voice.
- `ForceVoicePressureForDebug(0.12, true)` reaches `pressure=Psychosis` with an active voice and false instruction.
- After a psychosis event ends, the runtime objective marker now reports `FalseCue none` and `Confidence 1.00`.
- The full Phase 3 PIE runtime report still passes with 11 task stations, 58 world-reactive actors, 20 pattern actors, no exercise errors, and clean PIE stop.
- Tripo station ownership remains intact: all 11 task stations directly own `/Game/TripoModels/` meshes, and no standalone Tripo mesh blocker actors remain.
- The wide play-area layout remains locked with `max_deviation: 0.0`.

## Playable-Slice Impact

The player now gets a more readable escalation path: ordinary strain starts with anchor pressure, lower mental state becomes intrusive, and psychosis creates immediate conflicting instruction. Recovery also feels cleaner because stale false cues no longer linger after the player stabilizes or a psychosis event resolves.
