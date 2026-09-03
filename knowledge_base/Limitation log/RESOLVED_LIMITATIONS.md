# Resolved Limitations

Move entries here from `ACTIVE_LIMITATIONS.md` only after the fix is implemented and verified.

## Template

```text
- [x] LIM-0000 - Short title
  - Fixed in: Commit, file, or report.
  - Verification: Command/tool/report that proves the limitation is gone.
  - Date resolved: YYYY-MM-DD.
```

## Resolved

- [x] LIM-0006 - `UImage::SetBrushSize` deprecation warning in UnrealMCP UMG commands
  - Fixed in: D157, `unreal_plugin/Source/UnrealMCP/Private/Commands/UnrealMCPUMGCommands.cpp`.
  - Verification: `python -m unittest unreal_mcp_server.tests.test_phase7_bridge_command_audit` guards against `SetBrushSize`, and `.\_build_plugin.bat` no longer reports the deprecation warning.
  - Date resolved: 2026-06-15.
