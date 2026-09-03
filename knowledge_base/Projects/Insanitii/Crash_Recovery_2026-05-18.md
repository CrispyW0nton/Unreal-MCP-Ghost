# Crash Recovery - 2026-05-18

## Incident

Unreal Editor crashed after the Phase 2A daily-action Live Coding passes.

Crash folder:

`C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Saved\Crashes\UECC-Windows-EF923EF147B57F32C2EE65807DAD7457_0000`

Crash summary:

```text
CrashType: Assert
Fatal error:
[File:D:\build\++UE5\Sync\Engine\Source\Runtime\CoreUObject\Private\Templates\Casts.cpp] [Line: 10]
Cast of Object /Script/CoreUObject.Default__Object to Actor failed
```

The log shows the crash happened during `InternalPromptForCheckoutAndSave` after actor deletion commands. The editor session also had multiple Live Coding patch DLLs loaded:

- `UnrealEditor-Insanitii.patch_0.exe`
- `UnrealEditor-Insanitii.patch_1.exe`
- `UnrealEditor-Insanitii.patch_2.exe`
- UnrealMCP patch DLLs

## What Survived

The source work was not reverted or lost. Disk checks confirmed the Phase 2A additions were still present in:

- `InsanitiiMentalStateComponent.h/.cpp`
- `InsanitiiLifestyleManager.h/.cpp`
- `InsanitiiHUD.h/.cpp`

The apparent reversion came from the editor relaunching against the older base DLL while the latest changes only existed in Live Coding patch DLLs.

## Recovery Actions

1. Confirmed no dirty packages before closing the post-crash editor session.
2. Closed Unreal Editor.
3. Ran a full closed-editor build:

```text
Build.bat InsanitiiEditor Win64 Development -Project=...\Insanitii.uproject -WaitMutex
Result: Succeeded
```

4. Relaunched Unreal Editor.
5. Verified fresh reflection sees the new native APIs:

```text
AInsanitiiLifestyleManager.execute_daily_task_by_index: visible
AInsanitiiLifestyleManager.sleep_to_next_morning: visible
```

6. Found duplicated level infrastructure actors:

```text
INS_RuntimeBootstrap: 2
INS_PostProcessController: 2
INS_TestInteractable: 5
INS_LifestyleManager: 1
```

7. Created a recovery backup of the level before editing:

`C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Saved\RecoveryBackups\Lvl_FirstPerson_20260518_1326*.umap`

8. Removed only the origin-position duplicates:

- duplicate `INS_RuntimeBootstrap` at `(0, 0, 0)`
- duplicate `INS_PostProcessController` at `(0, 0, 0)`

9. Saved the map successfully after the clean build.

## Final Verified State

```text
Unreal Editor: running
Dirty packages: 0
INS_RuntimeBootstrap: 1
INS_PostProcessController: 1
INS_TestInteractable: 5
INS_LifestyleManager: 1
Lifestyle manager summary: Office Worker | Day 1 08:00 | Cash $250 | Skill 0.10 | Rep 0.00
Generated tasks: Email Triage, Data Entry Sprint, Client Meeting
```

## Root Cause Assessment

Most likely cause: reflected native class changes were applied through Live Coding, then the editor attempted to save a dirty level while class reinstancing/patch DLL state was stale or partially remapped.

This matches and strengthens `LIM-0001`.

## New Workflow Rule

For Insanitii, do not rely on Live Coding for reflected native API changes, including:

- adding/removing `UCLASS`,
- adding/removing `UFUNCTION`,
- adding/removing `UPROPERTY`,
- changing reflected `USTRUCT` fields,
- changing class inheritance or constructor component layout.

Use Live Coding only for narrow implementation-body changes after reflected shape is stable.

For reflected C++ changes:

1. Save no dirty assets unless necessary.
2. Close Unreal Editor.
3. Run full command-line build.
4. Relaunch editor.
5. Validate reflection and actor counts.
6. Then save level/assets.

## Next Safe Step

Run manual possessed-PIE validation of the now-cleanly-built Phase 2A daily controls:

- `1`, `2`, `3`: succeed generated task option.
- `Shift+1`, `Shift+2`, `Shift+3`: fail generated task option.
- `N`: sleep to next morning.

If manual PIE is stable, continue with home-base placeholder interactables.
