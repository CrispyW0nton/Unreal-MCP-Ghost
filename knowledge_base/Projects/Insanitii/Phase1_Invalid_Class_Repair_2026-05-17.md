# Phase 1 Invalid-Class Repair - 2026-05-17

## Symptom

Manual Play-in-Editor was blocked by Unreal modal prompts:

- `Blueprint Compilation Errors`
- `Blueprint could not be loaded because it derives from an invalid class`

The errored assets shown by Unreal were:

- `/Game/Insanitii/Core/Blueprints/BP_InsanitiiGameMode_Broken_20260517`
- `/Game/Insanitii/UI/HUD/BP_InsanitiiHUD_Broken_20260517`

## Root Cause

The real Insanitii Blueprint wrappers were valid again, but two backup assets with invalid/null parent classes were still inside `Content`. PIE tried to compile those backup assets, which made the editor report unresolved Blueprint compiler errors even though the current wrappers were loadable.

The native `AInsanitiiGameMode` constructor also referenced a stale controller Blueprint path:

- stale: `/Game/Insanitii/Core/Blueprints/BP_InsanitiiTemplatePlayerController`
- correct: `/Game/Insanitii/Core/Blueprints/BP_InsanitiiPlayerController`

## Repair Applied

1. Dismissed blocking editor prompts conservatively with Escape/Cancel.
2. Updated `Source/Insanitii/InsanitiiGameMode.cpp` to use `BP_InsanitiiPlayerController`.
3. Moved the two invalid backup `.uasset` files out of `Content` to:
   - `Saved/InvalidBlueprintBackups/2026-05-17/BP_InsanitiiGameMode_Broken_20260517.uasset`
   - `Saved/InvalidBlueprintBackups/2026-05-17/BP_InsanitiiHUD_Broken_20260517.uasset`
4. Cleared the stale editor asset-registry entries with `EditorAssetLibrary.delete_asset`.
5. Recompiled and saved the 8 core Insanitii Blueprint wrappers through native MCP:
   - `BP_InsanitiiGameMode`
   - `BP_InsanitiiPlayerController`
   - `BP_RuntimeBootstrap`
   - `BP_MentalStateComponent`
   - `BP_InteractionDetector`
   - `BP_TestInteractable`
   - `BP_PostProcessController`
   - `BP_InsanitiiHUD`

## Validation

- `insanitii_phase1_readiness_report()` returned `success=true`, `status=warn`.
- Found all 7 placed Insanitii actors.
- Found all 5 placed `BP_TestInteractable` actors.
- Verified all 8 Blueprint wrappers have generated classes.
- Found all 6 Insanitii Enhanced Input actions in `/Game/Input/IMC_Default`.
- Found 0 blocking dialogs.
- Confirmed the two broken assets no longer exist in the editor asset registry.
- Automated Simulate-in-Editor launched and stopped successfully.
- Log evidence after the repair:
  - `PlayLevel: No blueprints needed recompiling`
  - PIE world `/Game/FirstPerson/UEDPIE_0_Lvl_FirstPerson` was created.
  - No new `Blueprint failed to compile` entries were produced during the simulate smoke.

## Remaining Warning

The open editor still uses fallback MCP probes for the newest native smoke-test routes until the plugin module is reloaded. Full `Build.bat` validation also cannot complete while Unreal Editor and LiveCodingConsole hold loaded DLL/PDB files:

- `UnrealEditor-Insanitii.dll`
- `UnrealEditor-UnrealMCP.dll`
- `UnrealEditor-UnrealMCP.pdb`

The C++ compile step reached and compiled `InsanitiiGameMode.cpp`; the failure was link-time file locking, not a C++ syntax error.

## Next Action

Manual PIE validation can be retried. If full binary validation is needed, close Unreal Editor and LiveCodingConsole, then run:

```powershell
& 'C:\Program Files\Epic Games\UE_5.6\Engine\Build\BatchFiles\Build.bat' InsanitiiEditor Win64 Development -Project='C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Insanitii.uproject' -WaitMutex -NoHotReloadFromIDE
```
