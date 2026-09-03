# Phase 3 Playable Slice Scaffold - 2026-06-02

## Scope

This pass moved Insanitii from debug-key-only daily loop testing toward an in-world playable slice scaffold:

- ordinary task/stabilization stations placed in the level,
- a native psychosis event director,
- a chase-capable psychosis event actor,
- stronger event-driven post-process feedback,
- MCP smoke wrapper repair for the live bridge ping response.

The work follows the current best-fit native C++ plus Blueprint-wrapper architecture. The new classes are native and Blueprintable so designers can skin, tune, or subclass them without duplicating core mechanics.

## Native Runtime Additions

Added these classes under the Insanitii module:

- `AInsanitiiTaskStation`
  - Implements `IInsanitiiInteractable`.
  - Supports `WorkTask`, `Sleep`, `Medication`, `Food`, and `StressTrigger` actions.
  - Work stations call `AInsanitiiLifestyleManager::ExecuteDailyTaskByIndex`.
  - Sleep stations call `SleepToNextMorning` and apply a small stabilizing mental-state reward.
  - Medication and food stations stabilize mental state and reset failure cascade pressure.
  - Stress stations destabilize mental state to help trigger psychosis tests.

- `AInsanitiiPsychosisEventDirector`
  - Binds to `UInsanitiiMentalStateComponent::OnPsychosisEventReady`.
  - Randomly starts one of:
    - `Chase`,
    - `HallucinationSurge`,
    - `WorldShift`.
  - Owns event duration, survival stabilization reward, and ongoing event pressure.
  - Broadcasts Blueprint events on start/end for future audio, UI, and level scripting.

- `AInsanitiiPsychosisChaser`
  - Placeholder visible pressure actor for chase psychosis events.
  - Moves toward the player and drains mental state while close.

Updated:

- `AInsanitiiHUD`
  - Caches and displays the psychosis director state.
  - Shows active event type and remaining time in the existing debug HUD.

- `AInsanitiiPostProcessController`
  - Finds the psychosis director.
  - Adds event pulse and stronger contrast/saturation/vignette changes while a psychosis event is active.
  - Keeps Focus as the temporary clarity mechanic.

## Level Placement

After a closed-editor full build and editor relaunch, these actors were placed and saved in `Lvl_FirstPerson`:

- `INS_PsychosisEventDirector`
- `INS_TaskStation_Work_EmailTriage`
- `INS_TaskStation_Food_Sandwich`
- `INS_TaskStation_Medication`
- `INS_TaskStation_Sleep_Bed`
- `INS_TaskStation_Stress_OverwhelmingNoise`

These stations are deliberately placeholder geometry for now. They prove the playable loop before custom Tripo/ElevenLabs content is layered in.

## Tooling Improvement

Patched `unreal_mcp_server/tools/editor_tools.py` so the Insanitii smoke wrappers accept the live bridge ping shape:

```json
{"message": "pong"}
```

Previously both reports falsely failed because they only accepted `status=success` or `success=true`.

## Build And Verification

Required guide compliance:

- Read `.cursor/rules/unreal-mcp-book-knowledge.mdc`.
- Read the required `docs/knowledge-base/` Unreal guide files before bridge/project work.

Build:

```text
Build.bat InsanitiiEditor Win64 Development -Project=C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Insanitii.uproject -WaitMutex
Result: Succeeded
```

Live editor verification:

- Unreal bridge responded on `127.0.0.1:55655`.
- New native classes were visible through reflection:
  - `/Script/Insanitii.InsanitiiTaskStation`
  - `/Script/Insanitii.InsanitiiPsychosisEventDirector`
  - `/Script/Insanitii.InsanitiiPsychosisChaser`
- Map placement saved successfully.
- `insanitii_phase1_readiness_report`: `pass`
  - Found 14 `INS_` actors.
  - Found 5 `BP_TestInteractable` actors.
  - Input mapping count: 18.
  - No failures or warnings.
- `insanitii_phase2_lifestyle_report`: `pass`
  - Native Phase 2 class count: 3.
  - `BP_LifestyleManager` generated class valid.
  - `INS_LifestyleManager` placed.
  - Generated task count: 3.
  - Cash: `$250`.
  - Time: `Day 1 08:00`.
  - No failures or warnings.
- Focused MCP tests:
  - `test_phase8_insanitii_readiness_report.py`: pass.
  - `test_phase8_insanitii_lifestyle_report.py`: pass.

## Remaining Manual PIE Checklist

Completion is not proven until possessed PIE validates:

- Player can walk to each new station and interact with `E`.
- Work station executes a daily task and updates money/task outcome.
- Food and medication visibly stabilize mental state.
- Stress station lowers mental state enough to trigger psychosis readiness.
- Psychosis director starts random events when threshold/cooldown conditions are met.
- Chase event spawns and applies proximity pressure.
- WorldShift/HallucinationSurge produce noticeable post-process changes.
- Focus and Breathe remain effective stabilization tools during/after events.
- Sleep advances the day and applies living cost exactly once.

## Next Content Pass

Use the already-open Chrome session for authenticated content generation:

- ElevenLabs workspace: `https://elevenlabs.io/app/sound-effects`
  - Generate placeholder psychosis start, hallucination bed, chase sting, breathe confirmation, medication relief, and task success/failure sounds.
  - Account/session: user-approved Google account already open in Chrome; address intentionally omitted.
- Tripo workspace: `https://studio.tripo3d.ai/workspace/generate`
  - Generate simple textured smart meshes for home/work/stabilization stations after the interaction loop is manually validated.

## Chrome Content Generation Attempt

After the code/build/placement pass, Chrome control was attempted for the ElevenLabs/Tripo audio/content workflow. Both lightweight tab-list attempts failed before tab discovery with:

```text
node_repl kernel exited unexpectedly
windows sandbox failed: setup refresh failed with status exit code: 1
```

No ElevenLabs or Tripo assets were generated in this pass. The blocker was logged as `LIM-0007` in `knowledge_base/Limitation log/ACTIVE_LIMITATIONS.md`.
