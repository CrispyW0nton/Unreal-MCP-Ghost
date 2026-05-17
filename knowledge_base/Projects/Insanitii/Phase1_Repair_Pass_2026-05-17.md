# Insanitii Phase 1 Repair Pass - 2026-05-17

## Scope

Repair pass following `Phase1_Smoke_Test_2026-05-17.md`.

Goal: clear the automated Phase 1 smoke blockers without starting Phase 2.

## Repairs Completed

1. Restored the seven expected Phase 1 actors into `Lvl_FirstPerson`.

   Present after repair:

   - `INS_RuntimeBootstrap`
   - `INS_PostProcessController`
   - `INS_TestCube_PleasantMemory`
   - `INS_TestCube_BriefComfort`
   - `INS_TestCube_NeutralMoment`
   - `INS_TestCube_MinorSetback`
   - `INS_TestCube_BadMemory`

2. Recreated broken Blueprint wrapper generated classes.

   The original broken assets were backed up:

   - `/Game/Insanitii/Core/Blueprints/BP_InsanitiiGameMode_Broken_20260517`
   - `/Game/Insanitii/UI/HUD/BP_InsanitiiHUD_Broken_20260517`

   Clean wrappers now load:

   - `/Game/Insanitii/Core/Blueprints/BP_InsanitiiGameMode.BP_InsanitiiGameMode_C`
   - `/Game/Insanitii/UI/HUD/BP_InsanitiiHUD.BP_InsanitiiHUD_C`

3. Saved dirty content and map packages.

   Follow-up verification reported no dirty content packages and no dirty map packages.

## Post-Repair Verification

- Bridge `ping` succeeded on `127.0.0.1:55655`.
- World actor count after repair: `53`.
- All expected `INS_` actors are present by editor label.
- All critical generated classes load:
  - `BP_InsanitiiGameMode_C`
  - `BP_InsanitiiHUD_C`
  - `BP_RuntimeBootstrap_C`
  - `BP_TestInteractable_C`
  - `BP_PostProcessController_C`
- `/Game/Input/IMC_Default` loads and includes all six Insanitii Input Actions:
  - `IA_Breathe`
  - `IA_DebugDecreaseState`
  - `IA_DebugIncreaseState`
  - `IA_Focus`
  - `IA_Interact`
  - `IA_ToggleHUD`
- `DefaultEngine.ini` still points `GlobalDefaultGameMode` at:

  `/Game/Insanitii/Core/Blueprints/BP_InsanitiiGameMode.BP_InsanitiiGameMode_C`

## Actor Details

- `INS_RuntimeBootstrap`
  - Class: `BP_RuntimeBootstrap_C`
  - Location: `(-250, 0, 100)`
  - `bAttachComponentsToPlayer=True`
  - `bEnableLegacyInputBinding=False`

- `INS_PostProcessController`
  - Class: `BP_PostProcessController_C`
  - Location: `(-50, 0, 100)`
  - `LerpSpeed=2.0`

- `INS_TestCube_PleasantMemory`
  - Class: `BP_TestInteractable_C`
  - Location: `(250, -300, 80)`
  - `MentalStateImpact=+0.15`
  - Prompt: `Pleasant memory`

- `INS_TestCube_BriefComfort`
  - Class: `BP_TestInteractable_C`
  - Location: `(250, -150, 80)`
  - `MentalStateImpact=+0.10`
  - Prompt: `Brief comfort`

- `INS_TestCube_NeutralMoment`
  - Class: `BP_TestInteractable_C`
  - Location: `(250, 0, 80)`
  - `MentalStateImpact=0.00`
  - Prompt: `Neutral moment`

- `INS_TestCube_MinorSetback`
  - Class: `BP_TestInteractable_C`
  - Location: `(250, 150, 80)`
  - `MentalStateImpact=-0.10`
  - Prompt: `Minor setback`

- `INS_TestCube_BadMemory`
  - Class: `BP_TestInteractable_C`
  - Location: `(250, 300, 80)`
  - `MentalStateImpact=-0.15`
  - Prompt: `Bad memory`

## Notes

- During repair, Unreal showed an overwrite prompt while recreating `BP_InsanitiiGameMode`; the user cleared the prompt and the operation completed successfully.
- The prompt confirms a tooling limitation: Unreal-MCP-Ghost should avoid editor-modal asset creation paths or expose preflight overwrite handling before calling `AssetTools.create_asset`.
- Automated smoke blockers are now cleared, but Phase 1 is not fully validated until manual possession input is tested.

## Manual Play-in-Editor Gate

Jarrod should now run manual PIE and check:

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

If the manual checklist passes, Phase 1 can be marked validated and Phase 2 can begin.

## Unreal-MCP-Ghost Fixes To Add

- Asset creation commands need a `replace_existing` / `backup_existing` policy to prevent modal overwrite prompts.
- Project smoke tools should include:
  - `project_check_generated_class`
  - `project_find_actors_by_label`
  - `project_inspect_enhanced_input_context`
  - `project_validate_phase_gate`
- `compile_blueprint` should include generated-class load status in the response.
