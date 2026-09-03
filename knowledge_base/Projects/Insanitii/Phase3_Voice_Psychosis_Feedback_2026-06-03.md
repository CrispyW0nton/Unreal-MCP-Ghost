# Phase 3: Voice Psychosis Feedback

Date: 2026-06-03

## Purpose

Add a first playable voice/intrusive-thought layer tied to mental-state pressure and psychosis events. This supports the *A Beautiful Mind* direction: some experiences should feel like plausible internal/social interpretation before they become overtly destabilizing.

## Native Implementation

Updated `AInsanitiiAudioFeedbackDirector`:

- Added voice subtitle controls:
  - `bEnableVoiceSubtitles`
  - `VoicesStartBelowMentalState`
  - `MinVoiceIntervalSeconds`
  - `MaxVoiceIntervalSeconds`
  - `VoiceSubtitleDuration`
- Added five friendly/grounding lines and five unfriendly/intrusive lines.
- Added runtime state:
  - `CurrentVoiceLine`
  - `bCurrentVoiceFriendly`
  - `CurrentVoiceIntensity`
- Added voice query/debug functions:
  - `GetCurrentVoiceLine()`
  - `HasActiveVoiceLine()`
  - `IsCurrentVoiceFriendly()`
  - `TriggerVoiceLineForDebug(bool bFriendly)`
- Voice frequency scales with instability and gets more urgent during active psychosis.
- Unfriendly voices can play one of the existing ElevenLabs psychosis variants as an accent when available.
- Friendly voices can use the stabilization cue softly when the player is not deeply unstable.

Updated `AInsanitiiHUD`:

- Finds `INS_AudioFeedbackDirector`.
- Shows the audio debug summary in the world-feedback debug block.
- Displays active voice subtitles near the lower center of the screen.
- Friendly lines are labeled `anchor`; unfriendly lines are labeled `voice`.

## Example Lines

Friendly:

- "Breathe. Check the task list."
- "One ordinary thing at a time."
- "The objective marker is the anchor."

Unfriendly:

- "They are watching the routine."
- "The marker is wrong. Do not trust it."
- "That sign means something. Look again."

## Verification

Closed-editor clean build passed:

```powershell
.\scripts\run_insanitii_clean_build_and_tripo_verify.ps1
```

The build compiled `InsanitiiAudioFeedbackDirector.cpp` and `InsanitiiHUD.cpp` successfully. The Tripo bridge verifier also passed.

After editor relaunch:

- `bridge_ping.py`: bridge responded with 124 actors.
- `probe_insanitii_voice_feedback.py`: passed.
  - `INS_AudioFeedbackDirector` exists.
  - Voice subtitles are enabled.
  - Friendly line count: 5.
  - Unfriendly line count: 5.
  - Debug summary includes voice intensity.
  - `TriggerVoiceLineForDebug(false)` produced active line: "They are watching the routine."
  - `InsanitiiHUD` class loaded.
- `probe_insanitii_tripo_station_readiness.py`: passed; all 11 task stations still use direct Tripo meshes and remain interactable.
- `probe_insanitii_postprocess_vfx.py`: passed; FOV/DOF psychosis reflection still intact.

## Next Steps

- Replace text-only temporary voice lines with ElevenLabs voice assets once station/voice download flow is stable.
- Add categorized voice banks for friendly, unfriendly, false instruction, grounding reminder, and task commentary.
- Add a hallucinated-instruction event that can present an unfriendly line conflicting with the current HUD objective.
- Tune subtitle placement in manual PIE so it does not fight with the interaction prompt or objective marker.
