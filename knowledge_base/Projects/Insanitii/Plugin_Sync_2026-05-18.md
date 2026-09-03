# Insanitii UnrealMCP Plugin Sync - 2026-05-18

## Scope

Synchronized the Insanitii project-local UnrealMCP plugin with the current `Unreal-MCP-Ghost` workspace plugin.

## Paths

- Source plugin: `C:\Users\NewAdmin\Documents\GDeveloper\Workspaces\Unreal-MCP-Ghost\unreal_plugin`
- Insanitii project plugin: `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Plugins\UnrealMCP`
- Unreal project: `C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Insanitii.uproject`

## Actions

- Fetched the latest remote refs for `Unreal-MCP-Ghost`.
- Confirmed local branch `genspark_ai_developer` is aligned with `origin/genspark_ai_developer` (`0 ahead`, `0 behind`).
- Compared the repo plugin against the Insanitii-installed plugin for `Source`, `Resources`, and `UnrealMCP.uplugin`.
- Found only two project-copy drift files:
  - `Source\UnrealMCP\Private\Commands\UnrealMCPUMGCommands.cpp`
  - `Source\UnrealMCP\Public\Commands\UnrealMCPUMGCommands.h`
- Copied those two files from the repo plugin into the Insanitii project plugin.
- Re-ran the plugin source/hash comparison and confirmed `DIFF_COUNT=0`.

## Build Status

Attempted to compile:

```text
Build.bat InsanitiiEditor Win64 Development -Project="C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Insanitii.uproject" -WaitMutex
```

Result:

```text
Unable to build while Live Coding is active. Exit the editor and game, or press Ctrl+Alt+F11 if iterating on code in the editor or game.
```

`UnrealEditor.exe` was running from UE 5.6 during the build attempt, so the project plugin source is up to date but the compiled plugin DLL still needs either a Live Coding build from the editor or an editor-close command-line rebuild.

Follow-up:

- Confirmed the UnrealMCP bridge is responsive on `127.0.0.1:55655`.
- Sent `LiveCoding.Compile` through `exec_python`; the editor returned success for the command request.
- Project plugin binary timestamps under `Plugins\UnrealMCP\Binaries\Win64` did not change after the request, likely because the source drift was whitespace/newline-only or because Live Coding did not emit an on-disk plugin DLL.
- Retried the command-line build and confirmed it is still blocked by active Live Coding.

## Next Verification

1. In the running editor, press `Ctrl+Alt+F11` to trigger Live Coding, or close Unreal Editor.
2. If the editor is closed, run the command-line `InsanitiiEditor` build again.
3. After compile succeeds, run the Insanitii readiness MCP checks before claiming runtime/plugin readiness.
