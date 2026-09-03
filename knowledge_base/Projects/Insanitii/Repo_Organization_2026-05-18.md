# Insanitii Repo Organization - 2026-05-18

## Decision

Keep the Unreal-MCP-Ghost repo as the toolchain repo, and keep all Insanitii planning, reports, and decision records under:

`knowledge_base/Projects/Insanitii/`

The Unreal game project remains external at:

`C:\Users\NewAdmin\Documents\KaiGenInteractive\Insanitii\Insanitii`

## What Changed

- Added `GDD_Integration_2026-05-18.md` for the user-provided GDD and production adjustments.
- Added `Next_Development_Roadmap_2026-05-18.md` as the current action roadmap.
- Added global `knowledge_base/Limitation log/` for MCP/plugin/server limitations discovered during real project work.
- Updated project and master KB indexes so future sessions can find Insanitii quickly.

## Working Layout

Use these locations going forward:

- `knowledge_base/Projects/Insanitii/` - Insanitii GDD, roadmap, smoke reports, implementation logs, status.
- `knowledge_base/Limitation log/` - active and resolved Unreal-MCP-Ghost limitations.
- `scripts/` - reusable project/tooling scripts only.
- Repo root - keep as clean as possible; one-off probes should match ignored scratch patterns or be promoted into `scripts/` if reusable.
- `unreal_plugin/` - canonical plugin source before syncing into game projects.
- `unreal_mcp_server/` - Python MCP server and tool wrappers.

## Caution

The worktree already contains many unrelated modified and untracked files. No broad file moves were performed during this organization pass, because moving existing dirty files would risk disrupting user work.

Future cleanup should be done as a separate, explicit pass with a before/after inventory.
