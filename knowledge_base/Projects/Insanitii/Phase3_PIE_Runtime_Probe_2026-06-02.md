# Phase 3 PIE Runtime Probe - 2026-06-02

## Purpose

Close the Phase 3 automation gap by proving the playable slice can enter PIE, expose a possessed player/HUD/mental-state runtime, exercise the Day 1 task loop, trigger a psychosis event, stabilize, sleep, and stop PIE cleanly through Unreal MCP.

## MCP Tooling Added

- Added `insanitii_phase3_pie_runtime_report` in `unreal_mcp_server/tools/editor_tools.py`.
- Added async-safe PIE helpers for status, launch, and stop instead of relying on one blocking Unreal Python script.
- Added a runtime probe that reads controller, pawn, HUD, mental state, objective director, psychosis director, lifestyle/economy, and task station facts.
- Added scripted station-loop exercise:
  - sandwich
  - medication
  - Email Triage
  - overwhelming noise stress
  - psychosis start/end readback
  - sleep
- Added offline coverage in `unreal_mcp_server/tests/test_phase9_insanitii_pie_runtime_report.py`.

## Runtime Fixes

- Added `INS_PlayerPawn` to `Lvl_FirstPerson` from `/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter`.
- Set `INS_PlayerPawn` to auto-possess Player 0 and saved the level.
- Hardened `AInsanitiiGameMode`:
  - Uses native `AInsanitiiPlayerController` directly.
  - Spawns the default pawn with `AdjustIfPossibleButAlwaysSpawn`.
- Hardened `AInsanitiiPlayerController`:
  - Ticks during PIE.
  - Exposes `EnsurePossessedPawn()` as a callable fallback.
  - Spawns and possesses the configured default pawn at `PlayerStart` when PIE gives the project a controller without a pawn.
- Updated the PIE report to call `ensure_possessed_pawn()` when runtime readback finds an unpossessed controller.

## Live Verification

Clean builds succeeded after the native changes:

- `Build.bat InsanitiiEditor Win64 Development -Project=...\Insanitii.uproject -WaitMutex`
- Final reflected build generated 3 UHT outputs and linked `UnrealEditor-Insanitii.dll`.

Focused MCP tests passed:

- `python -m pytest unreal_mcp_server\tests\test_phase8_insanitii_readiness_report.py unreal_mcp_server\tests\test_phase8_insanitii_lifestyle_report.py unreal_mcp_server\tests\test_phase9_insanitii_objective_report.py unreal_mcp_server\tests\test_phase9_insanitii_pie_runtime_report.py`
- Result: `4 passed`

Final live report:

- Tool: `insanitii_phase3_pie_runtime_report`
- Status: `pass`
- Controller: `InsanitiiPlayerController`
- Pawn: `BP_FirstPersonCharacter_C`
- HUD: `InsanitiiHUD`
- Initial mental state: about `0.70`
- Task station count: `5`
- Scripted interaction steps: `5`
- Exercise errors: `0`
- Objective completion: `1.0`
- Psychosis event observed: `WorldShift | 24.0s`
- Work reward observed: cash rose from `250` to `314`
- Sleep/living-cost rollover observed: cash ended at `269`, time advanced to `Day 2 07:00`
- PIE stopped cleanly: yes

## Remaining Manual Check

The automated report invokes station APIs directly. Manual PIE should still confirm:

- normal keyboard/mouse movement;
- proximity prompt behavior;
- `E` interaction from the player detector;
- HUD readability during actual movement and visual distortion;
- subjective feel of the psychosis effects.

## Audio / Content Generation Status

Superseded by `Phase3_Audio_Feedback_Slice_2026-06-02.md`. ChromeMCP can now see the authenticated ElevenLabs/Tripo tabs, and ElevenLabs Sound Effects generated Insanitii history entries with credits spent, but playback/download remains disabled in the page UI. Local placeholder WAVs are imported and wired into the playable slice through `INS_AudioFeedbackDirector` until ElevenLabs downloads are available.
