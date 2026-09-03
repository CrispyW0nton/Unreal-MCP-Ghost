# Unreal-MCP-Ghost Limitation Log

This folder tracks limitations discovered while using Unreal-MCP-Ghost on real projects.

## Purpose

Use this log when a plugin, Python MCP server, bridge route, editor automation path, or workflow gap blocks project work or forces a workaround.

The rule is simple:

- Add a limitation when it affects real development.
- Keep it in `ACTIVE_LIMITATIONS.md` while it is still true.
- Move it to `RESOLVED_LIMITATIONS.md` when the fix lands and is verified.
- Link project reports or smoke-test notes so the limitation has evidence.

## Entry Format

```text
- [ ] LIM-0000 - Short title
  - Impact: What this blocks or slows down.
  - Evidence: File/report/tool output that proved it.
  - Workaround: Current safe path.
  - Fix target: Plugin, server, docs, or project workflow.
  - Removal test: What must pass before removing it from active limitations.
```

## Scope

This is a global toolchain log. Project-specific impact should still be recorded in that project's KB folder.
