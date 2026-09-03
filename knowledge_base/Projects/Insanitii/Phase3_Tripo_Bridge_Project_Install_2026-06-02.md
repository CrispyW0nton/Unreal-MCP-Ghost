# Phase 3 Tripo Bridge Project Install

Date: 2026-06-02

## Purpose

Install the user-provided Tripo UE bridge so the Insanitii project can import generated Tripo assets after the next clean editor restart.

Source zip:

```text
C:\Users\NewAdmin\Downloads\Tripo3d_UE_Bridge-latest.zip
```

## Required Context

The Tripo readme says to use the plugin package matching the Unreal Engine minor version. Insanitii targets UE `5.6`, so this pass used:

```text
Tripo3DUEBridge-UE5.6-Win64
```

The plugin descriptor reports:

- friendly name: `Tripo Bridge`
- version: `1.0.2`
- engine version: `5.6.0`
- supported platform: `Win64`
- module: `Tripo3DUEBridge`
- module type: `Editor`
- can contain content: `true`

## Installation

Copied the UE5.6 plugin files into:

```text
C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Plugins\Tripo3DUEBridge
```

Installed layout includes:

- `Tripo3DUEBridge.uplugin`
- `Binaries/Win64`
- `Content`
- `Intermediate`
- `Resources`
- `Source`

Enabled the project plugin in:

```text
C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii\Insanitii.uproject
```

New plugin entry:

```json
{
  "Name": "Tripo3DUEBridge",
  "Enabled": true,
  "TargetAllowList": [
    "Editor"
  ]
}
```

The `.uproject` JSON was validated successfully after the edit.

## Current Verification State

Verified:

- UE5.6 plugin files copied into the project.
- `Insanitii.uproject` is valid JSON.
- Tripo plugin is enabled for the editor target.
- `Tripo3DUEBridge.uplugin` declares the required `Interchange` plugin dependency.
- `Binaries/Win64/UnrealEditor-Tripo3DUEBridge.dll` is present.
- `ThirdParty/IXWebSocket/Lib/Win64/IXWebSocket.lib` is present after copying the zip-level `ThirdParty` payload into the installed plugin.
- `scripts/verify_tripo_bridge_install.py` passes with no errors.

Not yet verified:

- clean editor restart loads the plugin
- Tripo panel/menu appears
- bridge accepts generated assets from the signed-in Tripo workspace

Current verifier warning:

```text
IXWebSocket headers are not present; this install should be treated as a precompiled binary plugin unless the vendor supplies the missing ThirdParty/IXWebSocket/ixwebsocket include directory.
```

This means the packaged plugin should be validated as a binary/editor plugin first. A source rebuild of the vendor plugin may fail until the missing IXWebSocket header folder is supplied or the plugin is deliberately converted to precompiled-only behavior.

## Build Repair Notes

Initial project build after enabling the plugin failed because the installed plugin copy did not include:

```text
Plugins/Tripo3DUEBridge/ThirdParty/IXWebSocket/Lib/Win64/IXWebSocket.lib
```

The source zip contains that library under the zip root `Tripo3d_UE_Bridge/ThirdParty`, separate from the versioned UE5.6 plugin folder. Copying that `ThirdParty` payload into the installed plugin fixed the missing-library error.

The next build surfaced a plugin descriptor issue:

```text
Plugin 'Tripo3DUEBridge' does not list plugin 'Interchange' as a dependency, but module 'Tripo3DUEBridge' depends on module 'InterchangePipelines'.
```

The installed `Tripo3DUEBridge.uplugin` now includes:

```json
"Plugins": [
  {
    "Name": "Interchange",
    "Enabled": true
  }
]
```

After that descriptor repair, the build advanced past the Interchange dependency check and found engine zlib, but stopped because Live Coding is active in the still-running editor:

```text
Unable to build while Live Coding is active.
```

Added a non-destructive helper for the next clean verification pass:

```text
scripts/run_insanitii_clean_build_and_tripo_verify.ps1
```

The helper refuses to continue if an Insanitii Unreal Editor process is still open, then runs the Tripo verifier and the UE5.6 `InsanitiiEditor` command-line build. It does not close or kill the editor.

Latest save/close state:

- `scripts/run_unreal_save_dirty.py` returned `Not connected to Unreal Engine`.
- A force-close request for Unreal Editor PID `168664` was rejected because the user has not explicitly approved that exact shutdown risk after the latest disconnect.

## Editor Shutdown Attempts

The long-lived Unreal Editor process remained open and responsive. The following non-destructive quit paths were attempted after saving dirty packages:

- window `CloseMainWindow()`
- `unreal.SystemLibrary.quit_editor()`
- console commands `QUIT_EDITOR`, `QUIT`, and `EXIT`

All commands were accepted or sent, but the editor process remained open. No force-close was performed.

## Chrome / Authenticated Workspace State

Retried Chrome tab claiming for the signed-in Tripo and ElevenLabs tabs. The Chrome control backend failed twice before tab listing with:

```text
windows sandbox failed: setup refresh failed with status exit code: 1
```

Retried the supported Chrome/Node REPL bridge again after the Tripo install repair. The kernel exited before tab inspection with the same sandbox setup failure. No Tripo or ElevenLabs credits were used during this retry.

No account data, browser profile data, cookies, local storage, or alternate browser-control workaround was used.

## Next Required Verification

After a manual editor restart or explicitly approved force-close:

1. Confirm Unreal loads `Tripo3DUEBridge`.
2. Run an editor log check for `Tripo3DUEBridge` load messages.
3. Re-run Insanitii live PIE reports on `UNREAL_PORT=55655`.
4. Retry signed-in Chrome tab claiming for:
   - `https://studio.tripo3d.ai/workspace/generate`
   - `https://elevenlabs.io/app/sound-effects`
