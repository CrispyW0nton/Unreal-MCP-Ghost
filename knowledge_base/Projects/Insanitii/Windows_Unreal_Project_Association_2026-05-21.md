# Windows Unreal Project Association Fix - 2026-05-21

## Issue

After installing/downloading Unreal sample projects, Windows shell actions for `.uproject` files began failing with:

`Windows cannot find '<project>.uproject'. Make sure you typed the name correctly, and then try again.`

Affected examples:

- `C:\Users\NewAdmin\Documents\KaiGenInteractive\AnimationLibrary\GameAnimationSample\GameAnimationSample.uproject`
- `C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Project 2\EnclaveProject\EnclaveProject.uproject`

Directly running Unreal tools still worked, which pointed to a Windows file association / shell verb problem rather than corrupted project files.

## Fix Applied

Created a per-user `.uproject` association override under:

`HKCU\Software\Classes`

The merged `HKCR` association now resolves to:

- Open: `"C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor.exe" "%1"`
- Launch game: `"C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64\UnrealEditor.exe" "%1" -game`
- Generate Visual Studio project files: `"C:\Program Files (x86)\Epic Games\Launcher\Engine\Binaries\Win64\UnrealVersionSelector.exe" /projectfiles "%1"`
- Switch Unreal Engine version: `"C:\Program Files (x86)\Epic Games\Launcher\Engine\Binaries\Win64\UnrealVersionSelector.exe" /switchversion "%1"`

Explorer was restarted after the registry update so the shell cache would refresh.

## Validation

- Verified `HKCR\Unreal.ProjectFile\shell\open\command` resolves to the UE 5.6 editor path.
- Verified `HKCR\Unreal.ProjectFile\shell\rungenproj\command` resolves to UnrealVersionSelector `/projectfiles`.
- Ran the Windows shell `rungenproj` verb against Enclave without the prior "cannot find" failure.
- Opened Enclave through the Windows shell association; Unreal Editor launched as `Unreal Editor - EnclaveProject`.

## Notes

The all-users `HKLM\Software\Classes` association was locked from this session, so the stable fix was applied for the active `NewAdmin` account. This should cover normal double-click and right-click behavior for all `.uproject` files opened from this Windows user profile.
