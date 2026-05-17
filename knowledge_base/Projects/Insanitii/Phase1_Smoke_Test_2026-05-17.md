# Insanitii Phase 1 Smoke Test - 2026-05-17

## Scope

Live smoke test against the open Insanitii Unreal project at:

`C:/Users/NewAdmin/Documents/KaiGenInteractive/Insanitii/Insanitii/`

The test followed the incoming-agent checklist from the current project handoff. The goal was to validate Phase 1 before beginning Phase 2.

## Result

Phase 1 was partially validated on the first pass, but was not cleared for Phase 2.

The blocking findings below were later repaired in `Phase1_Repair_Pass_2026-05-17.md`. Phase 1 still needs manual Play-in-Editor validation before Phase 2 begins.

## Confirmed Working

- Unreal-MCP-Ghost bridge is reachable on `127.0.0.1:55655`.
- Bridge `ping` returned `pong`.
- Current editor world is `Lvl_FirstPerson`.
- `get_actors_in_level` returned a live level response.
- `/Game/Insanitii` asset hierarchy exists with 30 discovered assets.
- All expected native `/Script/Insanitii` classes load:
  - `UInsanitiiMentalStateComponent`
  - `UInsanitiiInteractionDetectorComponent`
  - `UInsanitiiInteractable`
  - `AInsanitiiTestInteractable`
  - `AInsanitiiRuntimeBootstrap`
  - `AInsanitiiPostProcessController`
  - `AInsanitiiHUD`
  - `AInsanitiiPlayerController`
  - `AInsanitiiGameMode`
- Core Blueprint/component/widget assets exist under `/Game/Insanitii`.
- Six Insanitii Input Action assets exist:
  - `IA_Focus`
  - `IA_Breathe`
  - `IA_Interact`
  - `IA_DebugDecreaseState`
  - `IA_DebugIncreaseState`
  - `IA_ToggleHUD`
- The actual mapping context is `/Game/Input/IMC_Default`, not `/Game/FirstPerson/Input/IMC_Default`.
- `/Game/Input/IMC_Default` contains mappings for the six Insanitii Input Actions.
- `DefaultEngine.ini` points `GameDefaultMap` and `EditorStartupMap` at `/Game/FirstPerson/Lvl_FirstPerson`.
- `DefaultEngine.ini` points `GlobalDefaultGameMode` at `/Game/Insanitii/Core/Blueprints/BP_InsanitiiGameMode.BP_InsanitiiGameMode_C`.

## Blocking Findings

1. Expected Phase 1 level actors are not present in the currently loaded level.

   Searches for `INS_`, `Insanitii`, `TestCube`, `RuntimeBootstrap`, and `PostProcessController` returned no placed actors. The handoff expects:

   - `INS_RuntimeBootstrap`
   - `INS_PostProcessController`
   - `INS_TestCube_PleasantMemory`
   - `INS_TestCube_BriefComfort`
   - `INS_TestCube_NeutralMoment`
   - `INS_TestCube_MinorSetback`
   - `INS_TestCube_BadMemory`

   Impact: PIE cannot validate runtime component attachment, interaction cubes, post-process response, or HUD truth display unless these are placed or restored.

2. Two wrapper generated classes do not load by `_C` path.

   These failed `unreal.load_class` checks:

   - `/Game/Insanitii/Core/Blueprints/BP_InsanitiiGameMode.BP_InsanitiiGameMode_C`
   - `/Game/Insanitii/UI/HUD/BP_InsanitiiHUD.BP_InsanitiiHUD_C`

   Impact: `DefaultEngine.ini` currently references `BP_InsanitiiGameMode_C`. If that generated class is genuinely unavailable, manual PIE may fall back, fail to use the intended GameMode, or fail to spawn the intended HUD path.

3. MCP `compile_blueprint` is not strong enough as a gate.

   The command returned `status=success` and `had_errors=false` for every tested wrapper, but the log shows `GeneratedClass null/invalid` for `BP_InsanitiiHUD`, and class loading still failed for `BP_InsanitiiGameMode_C` and `BP_InsanitiiHUD_C`.

   Impact: agents can receive a false sense of compile success. We need a stronger post-compile generated-class verification step in Unreal-MCP-Ghost.

## Blueprint Compile Smoke

The MCP compile command was run for:

- `BP_InsanitiiGameMode`
- `BP_InsanitiiTemplatePlayerController`
- `BP_RuntimeBootstrap`
- `BP_InsanitiiPlayerController`
- `BP_MentalStateComponent`
- `BP_InteractionDetector`
- `BPI_Interactable`
- `BP_TestInteractable`
- `WBP_DebugHUD`
- `BP_InsanitiiHUD`
- `WBP_InteractionPrompt`
- `BP_PostProcessController`

All returned `status=success` and `had_errors=false`, but see the generated-class caveat above.

## Manual Playtest Checklist

Run this only after the expected `INS_` level actors are restored or deliberately replaced:

- [ ] WASD movement works.
- [ ] Mouse look works.
- [ ] F activates Focus and charges decrease.
- [ ] Tab triggers Breathe and mental state increases by about `0.20`.
- [ ] `-` decreases mental state and visual feedback responds.
- [ ] `=` increases mental state.
- [ ] E interacts with focused cubes and changes mental state.
- [ ] `~` toggles HUD.
- [ ] Consecutive failures increment cascade state.
- [ ] Post-process distortion responds to mental state.

## Recommended Next Action

Do not begin Phase 2 yet.

First fix Phase 1 validation blockers:

1. Restore or spawn the seven expected `INS_` actors into `Lvl_FirstPerson`.
2. Re-open or recreate `BP_InsanitiiGameMode` and `BP_InsanitiiHUD` so their generated classes load by `_C` path, or intentionally switch project settings to the native `AInsanitiiGameMode` if the Blueprint wrapper is no longer needed.
3. Rerun this smoke test.
4. Ask Jarrod to perform the manual PIE checklist.

## Unreal-MCP-Ghost Limitations Found

- `ping` exists as a native bridge route, but still needs a first-class Python MCP wrapper.
- `get_actors_in_level` should include actor label and full path, not only object name/class/location, so agents can reliably verify editor-placed actors.
- A dedicated `find_actors_by_class` wrapper is needed for project smoke tests.
- `compile_blueprint` should report whether a generated class exists and loads after compile.
- Blueprint compile diagnostics should be easy to run from the bridge/CLI without requiring the full MCP server.
- Enhanced Input inspection needs a dedicated tool that returns action names and readable key names from mapping contexts.
- Automated full possessed PIE input remains a project/tooling gap; current automation is good for smoke evidence but not enough for WASD/mouse/key validation.
