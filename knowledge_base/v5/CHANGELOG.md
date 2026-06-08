# Knowledge Base v5 Changelog
> Append-only log for Workstream A knowledge-base changes.
> Agents can read this file at `kb://v5/CHANGELOG.md` to see what changed since a prior session.

---

## 2026-06-08

### D.6 - Texture-only path

- Added `gen_texture_from_prompt` as the prompt-only texture entry point with channel/resolution validation and a Material Instance handoff plan.
- Marked Tripo standalone prompt-to-texture generation as unsupported because `texture_model` requires an existing model task.
- Documented the D.6 fallback path and the material-tools sequence for wiring future provider Texture2D outputs into a master material instance.

## 2026-06-07

### D.5 - Generative provider abstraction

- Added `tools/generative/` with the `GenerativeProvider` protocol, output policy/result dataclasses, and a small provider registry.
- Added `TripoProvider` as the first implementation and delegated Tripo credit estimates, output suffixes, model-version normalization, and primary-model selection through it.
- Added `IGenerativeProvider.h` as the C++ import-side provider metadata interface and documented how to add future providers in the generative content KB.

### D.4 - Tripo auto-import bridge

- Added `gen_tripo_import_to_project` to download successful Tripo task outputs, prepare an import manifest, import the primary StaticMesh, and capture viewport thumbnail evidence.
- Reused the asset import execution substrate for generated mesh imports, with ScopedSlowTask and ScopedEditorTransaction coverage inside Unreal.
- Updated the generative content KB with the D.4 auto-import sequence, return payload, material-instance behavior, and Blueprint-shell boundary.

### D.3 - Tripo task tools

- Added Tripo task-family tools for text, image, multiview, refine, texture, conversion, status polling, waiting, and downloading signed outputs.
- Added provider-side HTTP helpers, local image upload support, explicit credit confirmation, and reservation rollback on failed submission.
- Updated the generative content KB with D.3 task sequencing and output handoff guidance.

### D.2 - Generative config and auth

- Added Tripo config/auth tools for key-source detection, local settings persistence, and per-session credit budget checks.
- Added a Generate Asset Settings drawer in the MCP Chat panel for API key, model version, texture quality, output folder, and spend confirmation.
- Updated the generative content KB with config/auth and cost-guard guidance.
- Kept D.2 offline: no Tripo API call is made until D.3 task tools land.

### D.1 - Generative module scaffold

- Added `tools/generative_tools.py` with `gen_list_providers` and `gen_prepare_import_manifest`.
- Added a native `gen_prepare_import_manifest` bridge helper for generated asset import handoff validation.
- Updated the generative content KB with provider scaffold and import manifest helper guidance.
- Added inventory metadata, bridge audit categorization, and D.1 offline smoke coverage.

### C.11 - Onboarding

- Added a config-backed first-launch MCP Chat tour with four steps: connect server, ask a question, drag an asset, and run a workflow.
- Added persistent onboarding completion state with Tour and Done controls so users can dismiss or reopen the guided overlay.
- Added a Sample Prompts surface with six curated demos: Health System, Build Slime Enemy, Dungeon Starter, HUD Health Bar, Repair Blueprint, and Asset Import Pass.
- Wired sample prompt clicks to insert real tool-chain requests into the composer without terminal copy-paste.
- Added C.11 static tests guarding first-launch state, tour steps, six sample demos, prompt insertion, and this changelog entry.

### C.10 - Accessibility and polish

- Added config-backed splitter persistence for the MCP Chat session rail, tool palette, conversation, and composer regions.
- Kept the panel on editor style tokens and subdued foreground colors so light/dark theme parity follows Unreal editor styling.
- Added a status footer that reports server latency, loaded tool count, KB doc count, request queue depth, and metrics state.
- Added an opt-in metrics toggle that records local chat panel telemetry snapshots to `Saved/MCPChat/metrics.json`.
- Added C.10 static tests guarding persisted layout, status footer fields, local opt-in telemetry, editor theming tokens, and this changelog entry.

### C.9 - Command palette

- Added a Ctrl+K command palette to `SMCPChatPanel` with a header button and in-panel search surface.
- Populated fuzzy-searchable entries from MCP tools, core KB docs, recent `@asset:` references, recent user prompts, and slash commands.
- Wired palette clicks to insert tool templates, KB prompts, asset references, recent prompts, or slash command text into the composer.
- Routed `/clear` through the existing clear-history action while keeping `/help`, `/undo`, and `/repair` available from the palette.
- Added C.9 static tests guarding command palette declarations, Ctrl+K/button wiring, search sources, fuzzy matching, click behavior, and this changelog entry.

### C.8 - Session management

- Added named chat-session storage under `Saved/MCPChat/<session>.json` with session list, create, rename, pin, delete, and Markdown export helpers.
- Exposed `/chat/sessions` plus `/chat/session/new`, `/chat/session/rename`, `/chat/session/pin`, `/chat/session/delete`, and `/chat/session/export` HTTP routes.
- Threaded `session` through chat send, poll, history, and clear routes so multiple conversations stay isolated.
- Added a left-side `SMCPChatPanel` session sidebar with Continue Last, New, Rename, Pin, Delete, Export, and per-session load actions.
- Added C.8 storage, route, and static editor tests guarding named session persistence and session-scoped chat URLs.

### C.7 - PIE/log/viewport evidence inline

- Added inline evidence extraction to `SMCPChatPanel` tool-call cards for screenshot paths, log snippets, and PIE/play-in-editor results.
- Rendered an inline evidence section in the originating tool card so viewport captures, logs, and runtime checks stay attached to the command that produced them.
- Added screenshot image widgets for existing local image files while still showing the captured path for missing or remote artifacts.
- Extended the tool detail drawer with a full inline-evidence summary alongside args, structured result detail, and log tail.
- Added C.7 static tests guarding evidence extraction, inline card rendering, image-widget setup, detail drawer evidence text, and this changelog entry.

### C.6 - In-panel tool palette

- Added a toggleable left-side `SMCPChatPanel` tool palette with expandable categories and per-tool insert buttons.
- Exposed `/tools/list?domain=all` through the chat HTTP route layer using the same discovery payload as `list_available_tools`.
- Tracked the UE editor chat HTTP/MCP support package, bringing the documented inventory to 603 MCP tools.
- Wired tool clicks to insert prompt templates with `<parameter>` placeholders derived from discovered tool parameters.
- Added C.6 static and route tests guarding palette fetch, category rendering, template insertion, and HTTP tool discovery.

### C.5 - Asset drag-and-drop

- Upgraded `SMCPChatPanel` drops to accept Content Browser assets, Outliner actors, and OS file explorer drops as typed prompt references.
- Added multi-item drop handling that inserts one `@asset`, `@actor`, or `@file` reference per line.
- Normalized external file paths before inserting `@file:` references into the composer.
- Added C.5 static tests guarding supported drag sources, typed reference formatting, OS file normalization, and multi-item joining.

### C.4 - Context chips

- Added live context chips above the `SMCPChatPanel` composer for open level, selected actor, dirty assets, last compile status, and the SSE 8000 server.
- Wired chip clicks to insert `@level`, `@actor`, `@dirty-assets`, `@last-compile`, and `@server` context references into the prompt.
- Added editor-state helpers for current level, selected actor, dirty package count, and structured/text compile-result tracking.
- Added C.4 static tests guarding chip labels, click wiring, inserted references, and editor context probes.

### C.3 - Tool-call visualization

- Added structured tool-call parsing to `SMCPChatPanel` for JSON MCP invocation/result payloads.
- Rendered tool calls as collapsible cards showing tool name, args summary, status, and structured result summary.
- Added a tool detail drawer that shows full args/result JSON and `log_tail` for selected tool cards.
- Added a Repair action for failed tool cards that queues a `repair_tools` chain request through the chat bridge.
- Added C.3 static tests guarding card rendering, detail drawer wiring, structured-result parsing, and repair prompt dispatch.

### C.2 - Core MCP Chat panel UX

- Upgraded `SMCPChatPanel` to a resizable two-pane Slate layout with conversation history above a multiline composer.
- Added Enter-to-send and Shift+Enter newline handling, plus generic drag/drop reference insertion for the composer.
- Added role-tagged user, agent, and tool message bubbles with Copy, Re-run, Open Log, and Reveal Asset actions.
- Added Markdown fenced-code rendering as highlighted monospaced blocks and append-on-delta SSE `data:` handling for streaming message updates.
- Added C.2 static tests that guard the core panel UX wiring and editor module dependencies.

### C.1 - Editor-only chat module split

- Added `UnrealMCPEditor`, a dedicated editor-only module for the dockable MCP Chat panel.
- Moved `SMCPChatPanel` under `unreal_plugin/Source/UnrealMCPEditor/` with a Public/Private module split.
- Moved chat tab registration and `Window > MCP Chat` menu wiring out of the core `UnrealMCP` module startup.
- Added static tests to keep the C.1 module boundary and descriptor entry from regressing.

### B.14 - MetaHuman pipeline tools

- Added `metahuman_import` for assembled MetaHuman package registration, asset-tree scanning, and manifest creation.
- Added `metahuman_inspect_package` for manifest and package-root inspection before follow-on animation or wrapper work.
- Added `metahuman_link_to_skeleton` for body skeletal mesh, skeleton, IK Rig, retargeter, AnimBP, and post-process AnimBP references.
- Added `metahuman_assign_dna` for DNA asset/file, face skeletal mesh, and rig logic metadata.
- Added `metahuman_configure_wrapper` for gameplay wrapper Blueprint metadata and integration references.
- Added native bridge routes, animation inventory coverage notes, usage guide notes, KB cross-links, and B.14 offline smoke tests.

### B.13 - Pixel Streaming and remote access tools

- Added `pixelstream_inspect_config` for Pixel Streaming plugin availability and config inspection.
- Added `pixelstream_configure_plugin` for Pixel Streaming generation enablement and preference flags.
- Added `pixelstream_configure_streamer` for signalling URL, streamer id, port, offscreen render, websocket, and encoder bitrate settings.
- Added `pixelstream_create_launch_profile` for reusable launch profiles with standalone launch arguments.
- Added native bridge routes, inventory metadata, usage guide notes, KB cross-links, and B.13 offline smoke tests.

### B.12 - Online Subsystem and EOS tools

- Added `online_inspect_config` for masked Online Subsystem/EOS config and plugin availability inspection.
- Added `online_configure_default_subsystem` for default/native online service config.
- Added `online_create_eos_artifact_config` for EOS artifact/product/sandbox/deployment/client id setup with secret suppression by default.
- Added `online_configure_eos_sessions` for EOS session, lobby, presence, connect, and stat mirroring flags.
- Added native bridge routes, OnlineSubsystem module/plugin dependencies, inventory metadata, usage guide notes, KB cross-links, and B.12 offline smoke tests.

### B.11 - Movie Render Queue tools

- Added `mrq_create_job` for editor MRQ queue job creation with sequence/map assignment, output folder, filename format, resolution, deferred pass, and image output format setup.
- Added `mrq_add_render_setting` for output, image output, deferred pass, anti-aliasing, and console variable render settings.
- Added `mrq_render_queue` for dry-run queue validation by default and explicit PIE executor render starts.
- Added native bridge routes, Movie Render Pipeline module dependencies, inventory metadata, usage guide notes, KB cross-links, and B.11 offline smoke tests.

### B.10 - Chaos destruction and cloth tools

- Added `chaos_create_solver_actor` and `chaos_configure_solver_actor` for Chaos Solver actor creation and event/runtime budget configuration.
- Added `chaos_inspect_geometry_collection` and `chaos_configure_geometry_collection` for Geometry Collection inspection, thresholds, clustering, event flags, and solver assignment.
- Added `chaos_configure_cloth_component` for SkeletalMeshComponent cloth simulation controls.
- Added native bridge routes, Chaos/GeometryCollection/Clothing module dependencies, inventory metadata, usage guide notes, KB cross-links, and B.10 offline smoke tests.

### B.9 - World Partition and HLOD tools

- Added `wp_load_region`, `wp_unload_region`, and `wp_create_data_layer` for World Partition editor region and Data Layer authoring.
- Added `hlod_generate` and `hlod_assign_layer` for World Partition HLOD builder passes and actor HLOD layer assignment.
- Added native bridge routes, WorldPartitionEditor/DataLayerEditor module dependencies, usage guide notes, KB cross-links, inventory metadata, and B.9 offline smoke tests.

### B.8 - Motion Matching and Chooser tools

- Added `motion_create_pose_search_schema`, `motion_create_pose_search_database`, `motion_add_database_sequence`, and `motion_inspect_pose_search_asset` for Pose Search authoring.
- Added `chooser_create_table`, `chooser_add_asset_row`, and `chooser_inspect_table` for Chooser table asset-result setup and inspection.
- Added native bridge routes, PoseSearch/Chooser plugin and module dependencies, usage guide notes, KB cross-links, and B.8 offline smoke tests.

### B.7 - MassEntity, StateTree, and SmartObject tools

- Added `mass_create_entity_config`, `mass_add_trait`, and `mass_inspect_entity_config` for MassEntity config asset authoring.
- Added `statetree_create`, `statetree_add_state`, and `statetree_inspect` for StateTree schema-backed asset creation and hierarchy inspection.
- Added `smartobject_create_definition`, `smartobject_add_slot`, and `smartobject_inspect_definition` for SmartObject definition and slot authoring.
- Added native bridge routes, MassGameplay/StateTree/GameplayStateTree/SmartObjects dependencies, inventory metadata, usage guide notes, KB cross-links, and B.7 offline smoke tests.

### B.6 - Geometry Script and Modeling Mode tools

- Added `geom_create_dynamic_mesh`, `geom_boolean_op`, `geom_extrude`, `geom_remesh`, `geom_uv_unwrap`, `geom_bake_to_static_mesh`, and `geom_apply_displacement` for DynamicMesh authoring and Static Mesh baking.
- Added native Geometry Script bridge routes, GeometryScripting plugin/module dependencies, usage guide notes, KB cross-links, and B.6 offline smoke tests.

### B.5 - MetaSounds and audio asset authoring tools

- Added `metasound_create_source`, `metasound_create_patch`, `metasound_add_node`, `metasound_connect_pins`, and `metasound_compile` for MetaSound asset and graph authoring.
- Added `audio_create_soundcue`, `audio_create_attenuation`, and `audio_create_concurrency` for cue routing, 3D falloff, and voice-limit policy assets.
- Added native audio bridge routes, MetaSound plugin/module dependencies, usage guide notes, KB cross-links, and B.5 offline smoke tests.

### B.4 - Networking and replication authoring tools

- Added `net_set_property_replicated`, `net_set_function_rpc`, and `net_set_replication_condition` for replicated Blueprint state and RPC authoring.
- Added `net_add_replicated_component`, `net_set_role_override`, and `net_get_replication_graph_state` for component replication, authority flow, and runtime replication inspection.
- Added native network bridge routes, inventory category metadata, usage guide notes, KB cross-links, and B.4 offline smoke tests.

### B.3 - Gameplay Ability System authoring tools

- Added `gas_create_ability`, `gas_create_gameplay_effect`, `gas_create_gameplay_cue`, and `gas_create_attribute_set` for GAS asset creation.
- Added `gas_grant_ability`, `gas_apply_effect`, and `gas_add_tag` for ASC-backed Blueprint authoring metadata.
- Added `gas_create_ability_task_node` for AbilityTask factory nodes in GameplayAbility graphs.
- Added native GAS bridge routes, inventory category metadata, usage guide notes, KB cross-links, and B.3 offline smoke tests.

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
