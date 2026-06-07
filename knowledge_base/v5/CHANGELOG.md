# Knowledge Base v5 Changelog
> Append-only log for Workstream A knowledge-base changes.
> Agents can read this file at `kb://v5/CHANGELOG.md` to see what changed since a prior session.

---

## 2026-06-07

### B.2 - graph-aware Blueprint/material diagnostics

- Added `compile_blueprint_and_report` for compile status plus graph summaries.
- Added `compile_material_and_report` for material compile and expression summaries.
- Added `validate_import_result` for post-import existence, class, dirty-state, and dependency evidence.
- Added `get_changed_assets_since` for package mtime and dirty-package asset diffs.
- Added the B.2 diagnostics section to the MCP usage guide and offline smoke tests for all four tools.

### B.1 - pre-existing roadmap gap tools

- Added `bp_add_call_interface_function` for Blueprint Interface message-call nodes.
- Added `bp_add_for_loop_with_break_node` plus the native `add_blueprint_for_loop_with_break_node` route.
- Added `bp_copy_component` plus the native `bp_copy_component` SCS route.
- Added `umg_add_widget_binding` plus the native `umg_add_widget_binding` UMG binding route.
- Added subsystem KB notes for the four B.1 tools in Blueprint fundamentals, Blueprint communication, UMG, component, and MCP usage docs.
- Added offline smoke tests for B.1 tool registration, routing, and StructuredResult shape.

### A.9 - v5 changelog resource

- Added `knowledge_base/v5/CHANGELOG.md` as the append-only KB change log for the v5 directive.
- Exposed `knowledge_base/v5/*.md` files as MCP resources using the `kb://v5/<filename>` URI pattern.

### A.8 - tool docstring KB links

- Added `KB: see knowledge_base/...#anchor` and `Example:` sections to all Git-tracked FastMCP tool docstrings.
- Added `scripts/lint_tool_docstrings.py` so CI can reject tools that omit KB links or examples.
- Updated `docs/ci-smoke.md` to include the docstring lint gate.

### A.7 - modern subsystem guide expansion

- Added `19_GAMEPLAY_ABILITY_SYSTEM.md`.
- Added `20_NETWORKING_AND_REPLICATION.md`.
- Added `21_METASOUNDS_AND_AUDIO_DSP.md`.
- Added `22_GEOMETRY_SCRIPT_AND_MODELING.md`.
- Added `23_MASS_ENTITY_AND_STATETREE.md`.
- Added `24_MOTION_MATCHING_AND_CHOOSERS.md`.
- Added `25_WORLD_PARTITION_AND_HLOD.md`.
- Added `26_CHAOS_PHYSICS_AND_DESTRUCTION.md`.
- Added `27_METAHUMAN_PIPELINE.md`.
- Added `28_MOVIE_RENDER_QUEUE_AND_SEQUENCER.md`.
- Added `29_PIXEL_STREAMING_AND_REMOTE.md`.
- Added `30_ONLINE_SUBSYSTEM_AND_EOS.md`.
- Added `31_GENERATIVE_CONTENT_PIPELINE.md`.
- Added `32_AGENT_PLAYABLE_SLICE_RECIPE.md`.
- Updated `INDEX.md` so the new numbered docs are discoverable from the decision tree and file tables.

### A.1-A.6 - native-mode onboarding surface

- Exposed top-level `knowledge_base/*.md` and `knowledge_base/v4/*.md` files as FastMCP resources.
- Added startup and discovery tools: `get_server_info`, `get_project_context`, `get_onboarding_context`, `scan_project_assets`, and `list_available_tools`.
- Added offline tests for resource metadata, server info, project context caching, onboarding packets, asset scanning, and domain-filtered tool discovery.
