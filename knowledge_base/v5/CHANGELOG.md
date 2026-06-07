# Knowledge Base v5 Changelog
> Append-only log for Workstream A knowledge-base changes.
> Agents can read this file at `kb://v5/CHANGELOG.md` to see what changed since a prior session.

---

## 2026-06-07

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
