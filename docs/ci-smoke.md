# CI Smoke And Profiling

These commands are the repeatable Phase 7 smoke path for validating the MCP
server without a live Unreal Editor session.

## Offline Smoke

Run from the repository root:

```powershell
python scripts\tool_inventory.py --markdown
python scripts\profile_mcp_startup.py --iterations 3 --markdown-out knowledge_base\Reports\mcp_startup_profile.md --json-out knowledge_base\Reports\mcp_startup_profile.json
python scripts\bridge_command_audit.py
python -m unittest unreal_mcp_server.tests.test_tool_count unreal_mcp_server.tests.test_phase7_profile unreal_mcp_server.tests.test_phase7_bridge_command_audit
```

Expected results:

- `tool_inventory.py` exits with code `0` and reports no uncategorized modules.
- `profile_mcp_startup.py` exits with code `0`, prints a Markdown timing table, and writes optional JSON/Markdown artifacts when output paths are provided.
- `bridge_command_audit.py` prints the Python/C++ bridge command metadata summary and known routing drift.
- The unittest command passes without requiring Unreal Editor or the TCP bridge.

## Optional Full Server Startup Probe

Use this when Python dependencies are installed and you want a colder proxy for
server import and CLI startup:

```powershell
python scripts\profile_mcp_startup.py --iterations 3 --include-server-help --command-timeout 30
```

This still does not connect to Unreal Editor. It only times the server's
`--help` path in a subprocess.

## Optional Live Bridge Smoke

Use this only when Unreal Editor is already open with the plugin running on
`127.0.0.1:55557`:

```powershell
python scripts\bridge_ping.py
```

If C++ plugin files changed, trigger Live Coding in Unreal Editor with
`Ctrl+Alt+F11`, wait for a successful compile, then rerun the bridge smoke.

## CI Artifact Guidance

Store `knowledge_base\Reports\mcp_startup_profile.json` and
`knowledge_base\Reports\mcp_startup_profile.md` as build artifacts. Compare the
median timings across commits before changing startup-heavy imports, bulk tool
registration, or bridge routing code.

To create a machine-readable bridge command snapshot for review:

```powershell
python scripts\bridge_command_audit.py --write-registry --registry knowledge_base\Reports\bridge_command_registry.json
```

Use `--check --registry <path>` against a saved snapshot when you want CI to
fail on unreviewed command routing drift.
