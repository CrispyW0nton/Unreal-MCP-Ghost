# SkyrimTest Environment Setup - 2026-05-18

## Project

- Name: `SkyrimTest`
- Path: `C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Project 4\SkyrimTest`
- Purpose: Skyrim level design test project.
- Engine association: Unreal Engine `5.6`
- UnrealMCP plugin is installed under the project `Plugins\UnrealMCP` folder.

## JDK Popup

Observed popup:

```text
******************************************************************
JDK 21+ (64-bit) could not be found and must be manually chosen!
******************************************************************
Enter path to JDK home directory (ENTER for dialog):
```

## Diagnosis

- Local `java -version` reports Oracle Java `17.0.12`.
- `JAVA_HOME`, `ANDROID_HOME`, and `ANDROID_SDK_ROOT` are not set in the current shell.
- No JDK 21+ installation was found in the common local install folders checked.
- A direct Win64 editor build succeeded:

```text
Build.bat SkyrimTestEditor Win64 Development -Project="...\SkyrimTest.uproject" -WaitMutex -NoHotReloadFromIDE
Result: Succeeded
Target is up to date
```

## Meaning

This is not currently a core UnrealMCP plugin compile failure for the Win64 editor target. The popup is caused by an Android-inclusive build/setup path needing JDK 21+.

For a desktop Skyrim level design test, prefer Win64 editor builds unless Android packaging is intentionally needed.

## Fix Options

### Option A - Desktop-only workflow

Use Win64-only build commands and avoid Android targets during plugin packaging:

```powershell
& "C:\Program Files\Epic Games\UE_5.6\Engine\Build\BatchFiles\Build.bat" SkyrimTestEditor Win64 Development -Project="C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Project 4\SkyrimTest\SkyrimTest.uproject" -WaitMutex -NoHotReloadFromIDE
```

If using `RunUAT BuildPlugin`, pass `-TargetPlatforms=Win64` instead of allowing all/default target platforms.

### Option B - Android-capable workflow

Install a 64-bit JDK 21+ distribution, then point Unreal at its JDK home directory, for example:

```text
C:\Program Files\Eclipse Adoptium\jdk-21.x.x.x-hotspot
```

Set `JAVA_HOME` to the JDK home directory and ensure `%JAVA_HOME%\bin` is on PATH. Then rerun the Android-inclusive build/setup step.

## Current Recommendation

For `SkyrimTest`, continue with desktop Win64 builds. Only install/configure JDK 21 if this project needs Android packaging or if a build script is intentionally targeting Android.
