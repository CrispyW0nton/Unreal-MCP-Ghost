# Insanitii Phase 1 Implementation Log

## 2026-05-12 Session

### Pre-Flight

- Unreal bridge reachable on `127.0.0.1:55655`.
- Cursor MCP wrapper still reports the server as errored, so editor operations were routed through the UnrealMCP bridge CLI.
- Unreal project: `Insanitii`
- Engine: `5.6.1-44394996+++UE5+Release-5.6`
- Project path: `C:/Users/NewAdmin/Documents/KaiGenInteractive/Insanitii/Insanitii/`
- PIE active: no
- Level actor count at baseline: 46
- First Person template assets found under `/Game/FirstPerson`.
- Baseline screenshot captured:
  - `Saved/Screenshots/WindowsEditor/phase1_00_baseline.png`

### Completed Editor Setup

- Created `/Game/Insanitii` content hierarchy with 19 project folders.
- Created Enhanced Input Actions:
  - `/Game/Insanitii/Core/Input/IA_Focus`
  - `/Game/Insanitii/Core/Input/IA_Breathe`
  - `/Game/Insanitii/Core/Input/IA_Interact`
  - `/Game/Insanitii/Core/Input/IA_DebugDecreaseState`
  - `/Game/Insanitii/Core/Input/IA_DebugIncreaseState`
  - `/Game/Insanitii/Core/Input/IA_ToggleHUD`
- Added mappings to `/Game/FirstPerson/Input/IMC_Default`:
  - `F` -> `IA_Focus`
  - `Tab` -> `IA_Breathe`
  - `E` -> `IA_Interact`
  - `Hyphen` -> `IA_DebugDecreaseState`
  - `Equals` -> `IA_DebugIncreaseState`
  - `Tilde` -> `IA_ToggleHUD`

### Native Runtime Layer Added

Added C++ classes to the Unreal project source for a stable runtime foundation:

- `UInsanitiiMentalStateComponent`
- `UInsanitiiInteractionDetectorComponent`
- `UInsanitiiInteractable`
- `AInsanitiiTestInteractable`
- `AInsanitiiRuntimeBootstrap`
- `AInsanitiiPostProcessController`
- `AInsanitiiHUD`
- `AInsanitiiPlayerController`
- `AInsanitiiGameMode`

This runtime layer implements the functional mental state, focus, breathe, interaction trace, prompt/HUD drawing, test cube interaction, post-process tuning, and game mode/controller foundation. Blueprint wrapper assets still need to be generated after the native classes compile.

### Current Blocker

The first Live Coding compile exposed C++ errors in the newly added runtime layer. These were fixed:

- `FVector4f` changed to `FVector4` for `FPostProcessSettings`.
- HUD `K2_DrawText` calls now pass `FString` instead of `FText`.
- Replaced `FLinearColor::Cyan` with an explicit cyan color value.
- Added the missing `AInsanitiiPlayerController` constructor declaration.

After those fixes, the Live Coding build succeeded.

The current blocker is that the running editor still cannot see the newly added reflected native classes through Python/reflection:

- `/Script/Insanitii.InsanitiiMentalStateComponent`
- `/Script/Insanitii.InsanitiiInteractionDetectorComponent`
- `/Script/Insanitii.InsanitiiTestInteractable`
- `/Script/Insanitii.InsanitiiRuntimeBootstrap`
- `/Script/Insanitii.InsanitiiPostProcessController`
- `/Script/Insanitii.InsanitiiPlayerController`
- `/Script/Insanitii.InsanitiiGameMode`
- `/Script/Insanitii.InsanitiiHUD`

This is expected for new `UCLASS` types added during Live Coding. The Unreal Editor needs to be restarted so the module loads the new reflected classes normally.

### Resume Point

After Unreal Editor is restarted, resume with:

1. Confirm bridge connectivity on `127.0.0.1:55655`.
2. Verify the new native classes load from `/Script/Insanitii`.
3. Create Blueprint wrapper assets in `/Game/Insanitii`.
4. Place bootstrap, post-process controller, and five test interactables.
5. Set `BP_InsanitiiGameMode` as default game mode.
6. Run PIE playtest.

### Resume Completed

- Reflected native classes are now visible in the running editor.
- Created and compiled Blueprint wrappers:
  - `/Game/Insanitii/Core/Components/BP_MentalStateComponent`
  - `/Game/Insanitii/Core/Components/BP_InteractionDetector`
  - `/Game/Insanitii/Gameplay/Interactions/BP_TestInteractable`
  - `/Game/Insanitii/Core/Blueprints/BP_RuntimeBootstrap`
  - `/Game/Insanitii/VFX/PostProcess/BP_PostProcessController`
  - `/Game/Insanitii/Core/Blueprints/BP_InsanitiiPlayerController`
  - `/Game/Insanitii/Core/Blueprints/BP_InsanitiiGameMode`
  - `/Game/Insanitii/UI/HUD/BP_InsanitiiHUD`
- Created placeholder assets:
  - `BPI_Interactable`
  - `WBP_DebugHUD`
  - `WBP_InteractionPrompt`
  - `M_PsychosisPostProcess`
  - `MI_PsychosisPostProcess_Runtime`
  - `NS_VisualStatic`
  - Audio sound classes and `SM_DefaultMix`
  - Two CurveFloat assets
- Placed Phase 1 level actors:
  - `INS_RuntimeBootstrap`
  - `INS_PostProcessController`
  - `INS_TestCube_PleasantMemory`
  - `INS_TestCube_BriefComfort`
  - `INS_TestCube_NeutralMoment`
  - `INS_TestCube_MinorSetback`
  - `INS_TestCube_BadMemory`
- Set current level game mode and `DefaultEngine.ini` global game mode to `BP_InsanitiiGameMode`.
- PIE simulation started successfully. Runtime validation found:
  - PIE world active.
  - `InsanitiiHUD` active.
  - Mental State component attached to player pawn.
  - Interaction Detector component attached to player pawn.

### Remaining Gaps

- The automated PIE path available through this bridge starts simulation mode, so it produced a `SpectatorPawn`/base `PlayerController` rather than a full possess-and-input play session. Manual Play-in-Editor should be used to validate WASD, mouse look, and key presses.
- Post-process material and Niagara are placeholders. The native post-process controller currently drives built-in post-process settings for immediate visual feedback.
- Curve assets exist, but Python curve-key insertion did not expose the expected `float_curve` property in this UE Python binding.
- Data table struct/table creation is deferred; a JSON placeholder was attempted for tuning defaults, but the asset-level DataTable still needs a proper struct path.

### MCP Configuration Repair

- Updated `cursor_mcp_config.json` to use:
  - `C:\Users\NewAdmin\Documents\GDeveloper\Workspaces\Unreal-MCP-Ghost\unreal_mcp_server\unreal_mcp_server.py`
- Updated `cursor_setup/mcp.json` to use the same workspace server path.
- Created user-level Cursor MCP config:
  - `C:\Users\NewAdmin\AppData\Roaming\Cursor\User\mcp.json`
- Set `UNREAL_HOST=127.0.0.1` and `UNREAL_PORT=55655`.
- Validated all three JSON files.
- Confirmed the Unreal bridge port is still reachable.

Cursor still needs to be restarted before the MCP wrapper can reload this configuration and expose tool schemas.

### Movement/Look Playtest Fix

Manual PIE showed the HUD worked but the player could not move or look around. Root cause: `BP_InsanitiiGameMode` was using `AInsanitiiPlayerController`, replacing the First Person Template controller that owns the template movement/look setup.

Fix applied:

- `AInsanitiiGameMode` now uses `/Game/FirstPerson/Blueprints/BP_FirstPersonPlayerController` as the player controller.
- It still uses the First Person character and `AInsanitiiHUD`.
- `AInsanitiiRuntimeBootstrap` now polls Phase 1 keys directly:
  - `F` -> Focus
  - `Tab` -> Breathe
  - `E` -> Interact
  - `-` -> Decrease Mental State
  - `=` -> Increase Mental State
  - `H` -> Toggle HUD
- Recompiled native code successfully through Live Coding.
- Recompiled `BP_InsanitiiGameMode` and `BP_RuntimeBootstrap`.
- Verified `BP_InsanitiiGameMode` defaults:
  - Player Controller: `BP_FirstPersonPlayerController`
  - Pawn: `BP_FirstPersonCharacter`
  - HUD: `InsanitiiHUD`

Retest manual Play-in-Editor. Movement and mouse look should now come from the template controller, while Insanitii mechanics are handled by the bootstrap.

### Second Movement/Look Fix

Manual PIE still could not move/look. Actual PIE inspection showed the player controller was still `/Script/Insanitii.InsanitiiPlayerController`, even though editor-side defaults appeared to point at the template controller.

Fix applied:

- Created `/Game/Insanitii/Core/Blueprints/BP_InsanitiiTemplatePlayerController` as a child of `/Game/FirstPerson/Blueprints/BP_FirstPersonPlayerController`.
- Forced `BP_InsanitiiGameMode` to use:
  - Player Controller: `BP_InsanitiiTemplatePlayerController`
  - Pawn: `BP_FirstPersonCharacter`
  - HUD: `InsanitiiHUD`
- Recompiled and saved the game mode.
- Started actual PIE through `LevelEditorSubsystem.editor_request_begin_play`.
- Verified runtime PIE now uses:
  - Player Controller: `BP_InsanitiiTemplatePlayerController`
  - Pawn: `BP_FirstPersonCharacter`
  - HUD: `InsanitiiHUD`
  - View target: `BP_FirstPersonCharacter`

This should preserve the stock template movement/look graph via inheritance while keeping the Insanitii HUD and bootstrap systems.

### Mechanics Key Input Fix

Manual PIE showed movement/look worked, but mechanics keys (`H`, `E`, `F`, `Tab`, `-`, `=`) did not. The bootstrap actor was present in PIE but its tick was disabled, so its polling path was unreliable.

Fix applied:

- Updated `AInsanitiiPlayerController` to add the actual First Person template Enhanced Input mapping contexts:
  - `/Game/Input/IMC_Default`
  - `/Game/Input/IMC_MouseLook`
- Bound Phase 1 mechanics keys directly on the controller with raw key bindings:
  - `F` -> Focus
  - `Tab` -> Breathe
  - `E` -> Interact
  - `-` / numpad subtract -> Decrease Mental State
  - `=` / numpad add -> Increase Mental State
  - `H` -> Toggle HUD
- Controller now lazily ensures the Mental State and Interaction Detector components exist on the possessed pawn, so mechanics are no longer dependent on bootstrap tick.
- Set `BP_InsanitiiGameMode` back to `BP_InsanitiiPlayerController`.
- Actual PIE verification now shows:
  - Player Controller: `BP_InsanitiiPlayerController`
  - Pawn: `BP_FirstPersonCharacter`
  - HUD: `InsanitiiHUD`
  - Mental State component present
  - Interaction Detector component present

Movement/look should continue to work because the controller now adds the same mapping contexts as the First Person template controller.

### Input Architecture Follow-Up

Manual testing showed that using the native controller before adding the real template mapping contexts broke movement/look. Then using the template-derived controller restored movement/look but mechanics keys were unreliable because the bootstrap actor remained tick-disabled in PIE.

Current setup:

- `BP_InsanitiiGameMode` uses `BP_InsanitiiPlayerController`.
- `BP_InsanitiiPlayerController` now adds the actual First Person mapping contexts:
  - `/Game/Input/IMC_Default`
  - `/Game/Input/IMC_MouseLook`
- It also binds mechanics keys directly:
  - `F`, `Tab`, `E`, `-`, `=`, `H`
- Actual PIE verification:
  - Player Controller: `BP_InsanitiiPlayerController`
  - Pawn: `BP_FirstPersonCharacter`
  - HUD: `InsanitiiHUD`
  - Mental State component present
  - Interaction Detector component present

Retest manual PIE after this change. If movement/look still fails, the next step is to move mechanics binding into a child Blueprint of the template controller graph instead of using native controller input.

### HUD-Based Mechanics Input Fix

Manual testing showed that the native Insanitii controller still broke movement/look. The final separation is now:

- `BP_InsanitiiGameMode` uses `BP_InsanitiiTemplatePlayerController`, a child of the stock First Person controller, for movement/look.
- `AInsanitiiHUD` now ticks and polls Phase 1 mechanics input:
  - `F` -> Focus
  - `Tab` -> Breathe
  - `E` -> Interact
  - `-` / numpad subtract -> Decrease Mental State
  - `=` / numpad add -> Increase Mental State
  - `H` -> Toggle HUD
- `AInsanitiiHUD` also ensures the Mental State and Interaction Detector components exist on the possessed pawn.
- Actual PIE verification after this change:
  - Player Controller: `BP_InsanitiiTemplatePlayerController`
  - Pawn: `BP_FirstPersonCharacter`
  - HUD: `InsanitiiHUD`
  - Mental State component present
  - Interaction Detector component present

This keeps movement/look entirely in the working template controller while putting Insanitii mechanics on the always-active HUD.

### HUD Toggle Key Change

Manual testing showed the tilde/backtick key opens the Unreal console, so HUD toggle was moved to `H`.

- Runtime bootstrap now checks `EKeys::H`.
- Native HUD controls text now displays `H = Toggle HUD`.
- Live Coding build succeeded after the change.

### Enhanced Input Character Binding Fix

Manual testing showed the template controller restored movement/look, but HUD/raw polling did not fire the Phase 1 mechanics actions. The input path has now been aligned with the First Person Template architecture.

- Added the Insanitii actions to the actual template mapping context `/Game/Input/IMC_Default`.
- Removed duplicate Insanitii mappings and removed the old `IA_ToggleHUD` tilde mapping, leaving:
  - `IA_Focus` -> `F`
  - `IA_Breathe` -> `Tab`
  - `IA_Interact` -> `E`
  - `IA_DebugDecreaseState` -> `Hyphen`
  - `IA_DebugIncreaseState` -> `Equals`
  - `IA_ToggleHUD` -> `H`
- Added `InsanitiiMentalState` and `InsanitiiInteractionDetector` components to `BP_FirstPersonCharacter`.
- Updated `UInsanitiiMentalStateComponent` to bind the six `UInputAction` assets through the possessed character/controller `UEnhancedInputComponent`.
- Live Coding build succeeded after the Enhanced Input binding change.

Manual PIE retest should confirm movement/look still works and that `H`, `F`, `Tab`, `E`, `-`, and `=` now trigger through Enhanced Input.

Follow-up playtest showed the actions still did not fire. The runtime state confirmed `BP_FirstPersonCharacter` is possessed, owns `InsanitiiMentalState`, owns `InsanitiiInteractionDetector`, and also owns an `EnhancedInputComponent`. The binding code was corrected to bind through the pawn/character input component rather than the player controller input component, with a fallback that directly locates the pawn-owned `UEnhancedInputComponent`.

- HUD now displays `Input: Enhanced Bound` or `Input: Waiting for Enhanced Input` under the debug stats.
- Live Coding build succeeded with `-NoUBA` after UBA stalled under memory pressure.
- Manual PIE retest should check the new HUD input status line first.

### Full Audit (Input/System Cross-Check)

A full audit was run across C++ runtime files, IMC assets, and the Insanitii knowledge-base logs.

Confirmed:

- `/Game/Input/IMC_Default` contains exactly one mapping for each Insanitii action:
  - `IA_Focus`=`F`, `IA_Breathe`=`Tab`, `IA_Interact`=`E`,
    `IA_DebugDecreaseState`=`Hyphen`, `IA_DebugIncreaseState`=`Equals`, `IA_ToggleHUD`=`H`.
- Insanitii `UInputAction` assets are valid boolean actions with no unusual trigger/modifier constraints.
- Native code compiles cleanly after adding `UInsanitiiInputBlueprintLibrary`.

Critical architecture issue found:

- There are still multiple concurrent mechanics-input systems active in code:
  - `UInsanitiiMentalStateComponent` Enhanced Input binding.
  - `AInsanitiiHUD` key polling (`WasInputKeyJustPressed`).
  - `UInsanitiiMechanicsInputComponent` key polling injected from game mode `PostLogin`.
  - `AInsanitiiRuntimeBootstrap` input binding code.
  - Legacy key binding code still present in `AInsanitiiPlayerController`.

This overlap is the primary source of non-deterministic behavior and has diverged from the intended single Enhanced Input path.

Additional cross-check mismatch:

- Knowledge-base entries that mark Enhanced input handling as complete are premature while manual playtests still show no fired actions.

### Plugin Limitation Patch + Runtime Consolidation

Per follow-up request, UnrealMCP Blueprint-node handling was patched in both the workspace plugin and the active Insanitii plugin copy:

- `UnrealMCPBlueprintNodeCommands.cpp`:
  - Added stronger target-class resolution (`ResolveTargetClassByName`) for project/module classes.
  - Added unresolved-call guard to reconstruct call nodes and emit explicit errors when a call node remains zero-pin.
- `UnrealMCPCommonUtils.cpp`:
  - Updated `CreateFunctionCallNode` to retry with an explicit external member reference + reconstruct when initial pin allocation is empty.

Project runtime input was also consolidated to reduce competing systems:

- Removed `AInsanitiiGameMode::PostLogin` injection of `UInsanitiiMechanicsInputComponent`.
- Kept mechanics handling in `AInsanitiiHUD` and switched edge detection from `WasInputKeyJustPressed` to deterministic `IsInputKeyDown` transition tracking per key.
- Disabled bootstrap legacy key binding by default via `bEnableLegacyInputBinding=false`.

Live Coding build succeeded after these changes.
