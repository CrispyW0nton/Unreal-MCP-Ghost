# Epic UE 5.8 MCP Source Audit

Date: 2026-06-19

## Source Provenance

- Epic repository: `EpicGames/UnrealEngine`
- Release inspected: `5.8.0-release`
- Commit inspected: `7deeb413d3dc1fc034f48d1aacc0861301829d32`
- Local source checkout: `C:\Users\NewAdmin\Documents\GDeveloper\External\UnrealEngine-5.8-sparse`

The audit treated Epic's source as reference architecture only. No Epic source code was copied into Unreal-MCP-Ghost.

## Prompt Corrections

- The prompt's `Engine/Plugins/Experimental/ToolsetRegistry/Content/Python/toolset_registry/toolsets/core/actor.py` path is not present in `5.8.0-release`. The checked release does not contain that ToolsetRegistry Python content tree.
- The real official Unreal MCP server implementation is in `Engine/Plugins/Experimental/ModelContextProtocol`, especially `Source/ModelContextProtocol/Private/ModelContextProtocolServer.cpp` and the editor ToolsetRegistry adapter files.
- A separate MCP-related sibling not named in the prompt exists at `Engine/Plugins/Experimental/Toolsets/MCPClientToolset`. It is an editor-only ToolsetRegistry bridge to external MCP servers, not the in-editor Unreal MCP server.
- Spatial awareness audit: the staged sparse checkout contains references to `toolset_registry.toolsets.core.scene.SceneTools.add_to_scene_from_asset` in analytics tests, but the actual `toolset_registry.toolsets.core.scene` Python implementation was not present in the audited checkout.

## Epic Files And Folders Inspected

- `Engine/Plugins/Experimental/ModelContextProtocol/ModelContextProtocol.uplugin`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocol/Public/IModelContextProtocolModule.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocol/Public/IModelContextProtocolTool.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocol/Public/ModelContextProtocol.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocol/Public/ModelContextProtocolServer.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocol/Public/ModelContextProtocolSession.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocol/Private/ModelContextProtocolModule.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocol/Private/ModelContextProtocolModule.cpp`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocol/Private/ModelContextProtocolServer.cpp`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolTests/Private/Tests/ModelContextProtocolAnalyticsTests.cpp`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEngine/Public/ModelContextProtocolSettings.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEngine/Public/ModelContextProtocolClientConfig.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEngine/Public/ModelContextProtocolToolLibrary.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEngine/Private/ModelContextProtocolSettings.cpp`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEngine/Private/ModelContextProtocolClientConfig.cpp`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEngine/Private/ModelContextProtocolEngineModule.cpp`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEngine/Private/ModelContextProtocolToolLibrary.cpp`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEditor/Private/ModelContextProtocolEditor.cpp`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEditor/Private/ModelContextProtocolToolSearch.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEditor/Private/ModelContextProtocolToolSearch.cpp`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEditor/Private/ModelContextProtocolToolsetRegistryAdapter.h`
- `Engine/Plugins/Experimental/ModelContextProtocol/Source/ModelContextProtocolEditor/Private/ModelContextProtocolToolsetRegistryAdapter.cpp`
- `Engine/Plugins/Experimental/ToolsetRegistry/ToolsetRegistry.uplugin`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Public/ToolsetRegistry/ToolsetDefinition.h`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Private/ToolsetRegistry/ToolsetDefinition.cpp`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Public/ToolsetRegistry/Toolset.h`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Private/ToolsetRegistry/Toolset.cpp`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Public/ToolsetRegistry/ToolsetRegistry.h`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Private/ToolsetRegistry/ToolsetRegistry.cpp`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Private/ToolsetRegistry/FunctionLibraryToolset.cpp`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Private/ToolsetRegistry/ObjectFunctionToolCall.h`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Private/ToolsetRegistry/ObjectFunctionToolCall.cpp`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Private/ToolsetRegistry/RunOnMainThread.h`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Public/ToolsetRegistry/UToolsetRegistry.h`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Private/ToolsetRegistry/UToolsetRegistry.cpp`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Public/ToolsetRegistry/AgentSkill.h`
- `Engine/Plugins/Experimental/ToolsetRegistry/Source/ToolsetRegistry/Private/ToolsetRegistry/AgentSkill.cpp`
- `Engine/Plugins/Experimental/Toolsets/GASToolsets/GASToolsets.uplugin`
- `Engine/Plugins/Experimental/Toolsets/GASToolsets/Source/GASToolsets/Private/AttributeSetToolset.h`
- `Engine/Plugins/Experimental/Toolsets/GASToolsets/Source/GASToolsets/Private/AttributeSetToolset.cpp`
- `Engine/Plugins/Experimental/Toolsets/GASToolsets/Source/GASToolsets/Private/GASToolsets.cpp`
- `Engine/Plugins/Experimental/Toolsets/MCPClientToolset/MCPClientToolset.uplugin`
- `Engine/Plugins/Experimental/Toolsets/MCPClientToolset/Source/MCPClientToolset/Public/MCPClientToolset/MCPClientToolset.h`
- `Engine/Plugins/Experimental/Toolsets/MCPClientToolset/Source/MCPClientToolset/Private/MCPClientToolset.cpp`
- `Engine/Plugins/Experimental/Toolsets/MCPClientToolset/Source/MCPClientToolset/Public/MCPClientToolset/MCPToolsetSettings.h`
- `Engine/Plugins/Experimental/Toolsets/MCPClientToolset/Source/MCPClientToolset/Private/MCPToolsetSettings.cpp`
- `Engine/Plugins/Experimental/Toolsets/MCPClientToolset/Source/MCPClientToolset/Private/MCPClientToolsetSubsystem.cpp`

## Architecture Findings

- Server lifecycle: Epic exposes `ModelContextProtocol.StartServer`, `ModelContextProtocol.StopServer`, and `ModelContextProtocol.RefreshTools` console commands through the runtime module. The editor module can auto-start the server from settings or command-line flags.
- Transport: Epic implements an in-editor HTTP server through Unreal's HTTP server module. It binds `POST`, `GET`, and `DELETE` on a configurable path, uses streamable HTTP semantics, validates localhost origins, tracks `Mcp-Session-Id`, validates protocol versions, and returns Server-Sent Event bodies for streaming tool-call responses. `GET` is not used as a separate persistent SSE endpoint in the server path inspected.
- Protocol surface: The server handles JSON-RPC methods including initialization, ping, cancellation notification, tool listing, tool calls, resource listing, and resource reads. Tool calls can stream progress and complete through an SSE `message` event.
- Tool discovery: Epic defaults toward a tool-search pattern through `list_toolsets`, `describe_toolset`, and `call_tool` when Toolset Registry search mode is enabled. This avoids exposing every tool eagerly.
- Toolset adapter: The editor adapter bridges ToolsetRegistry toolsets into MCP. In search mode it exposes meta-tools. Outside search mode it can register individual ToolsetRegistry tools directly as MCP tools.
- Direct registration path: Runtime modules can register custom tools through `IModelContextProtocolTool` and the module `AddTool` API. Names are validated and duplicates are rejected.
- Toolset Registry pattern: `UToolsetDefinition` static functions marked for AI calling become tools. The FunctionLibraryToolset path reflects function signatures into schemas, validates inputs, injects world context when needed, and dispatches on the game thread.
- Spatial awareness breadcrumb: analytics tests reference a ToolsetRegistry identifier for `toolset_registry.toolsets.core.scene.SceneTools.add_to_scene_from_asset`, confirming a native scene-oriented toolset concept even though the implementation was not included in the local sparse checkout.
- Client config generation: The engine module has a console command to generate client config for Claude Code, Cursor, VS Code, Gemini, Codex, or all supported clients.
- Module boundaries: Epic splits core protocol/server types into a runtime module, settings/config helpers into an engine runtime module, and ToolsetRegistry/editor integration into an editor module.

## Gap Analysis Against Unreal-MCP-Ghost

- Ghost's Unreal plugin is a TCP JSON command bridge, not an MCP server inside Unreal Editor. It does not yet have Epic's HTTP session handling, origin checks, protocol negotiation, server-side cancellation, or progress streaming.
- Ghost's Python FastMCP server has broader client compatibility today: stdio, SSE, and streamable HTTP are already supported outside the editor process.
- Ghost's tool catalog is broader and more Blueprint-oriented, but historically flat. Epic's tool-search meta-tool pattern is better for large catalogs and is now adopted in a safe first pass.
- Ghost has project knowledge, higher-level skills, generative workflow tools, chat routes, and Blueprint graph repair workflows that Epic's official plugin does not replace.
- Ghost now has clean-room client config generation for Epic's supported client set and a Python ToolsetRegistry contribution contract that documents Ghost's AddTool-style invariants. Remaining gaps include an Unreal-native module-level AddTool API and a C++/UE reflection-backed ToolsetRegistry adapter.
- Ghost's bridge command dispatcher remains flatter than Epic's ToolsetRegistry dispatch architecture and should be improved in later passes without losing existing command coverage.
- Ghost now has first PCG workflow wrappers and a city/district planning skill. This is native workflow alignment, not full Unreal city-sample parity: rich PCG graph node authoring, ZoneGraph/MassTraffic wrappers, actor/Data Layer assignment, streaming proof, and performance evidence remain open.
- Ghost now exposes clean-room runtime lifecycle, transport diagnostics, protocol contract/session guidance, operation tracking/cancellation, and metadata refresh tools. This improves native-style observability without claiming Epic's in-editor HTTP session implementation.
- Ghost now has clean-room spatial awareness wrappers for scene overview, actor queries, actor descriptors, proximity maps, surface-aware placement probes, placement validation/evidence planning, interior composition planning with guarded Tripo generation/import handoffs, selection, bounds, viewport camera context, and dry-run-first transactional asset placement. These fill the previously missing scene-intelligence, basic scene-placement, and apartment-style composition planning layer without copying or depending on Epic's absent `SceneTools` implementation.
- Ghost now has a guarded descriptor-backed bridge command call adapter. This improves the flatter bridge dispatcher by adding ToolsetRegistry-style discovery, dry-run planning, mutation classification, and explicit mutation/unknown-command gates before sending through Ghost's existing TCP bridge.

## Migration Plan

Pass 1: Add tool-search meta-tools around the existing Python registry while preserving direct tools by default. Done in this pass.

Pass 2: Add clean-room client config generation for Cursor, Claude, VS Code, Gemini, and Codex using Ghost's server transports and existing config locations. Done in the second pass.

Pass 3: Harden transport behavior where Ghost owns HTTP serving: localhost origin guidance, clearer protocol/session diagnostics, cancellation envelopes, and progress-friendly long-running tool conventions. Started in the sixth implementation pass with lifecycle and transport diagnostics; extended in the seventeenth pass with a protocol contract tool. Deeper hard enforcement and in-editor progress behavior remain open.

Pass 4: Refactor C++ bridge command registration toward structured command/toolset descriptors so command discovery, documentation, and tests are generated from one registry.

Pass 5: Add native workflow integrations above the MCP plumbing: PCG support checks, PCG graph/volume wrappers, World Partition/Data Layer/HLOD orchestration, city/district planning, optional Mass/traffic scaffolding, and validation/evidence gates. Started in the fifth implementation pass.

Pass 6: Expose native-style server lifecycle, transport diagnostics, and metadata refresh surfaces for Ghost's Python/FastMCP server while preserving stdio, SSE, streamable HTTP, tool-search mode, and the existing TCP bridge. Started in the sixth implementation pass.

Pass 7: Consider an optional Unreal-native MCP/editor module only after licensing review. Keep it separate from the public bridge unless redistribution constraints are settled.

Pass 8: Expand spatial workflow bridges above the read-only awareness layer: safe asset placement, selection-aware operations, camera-framed validation screenshots, Data Layer assignment, and city/worldbuilding placement helpers. Any close reuse of Epic `SceneTools` implementation should wait for legal review if that source is later located.

## First Implementation Pass

- Added `unreal_mcp_server/toolset_registry.py`.
- Wired `unreal_mcp_server/unreal_mcp_server.py` so tool registrars run through a collecting FastMCP facade.
- Added initial meta-tools named `list_toolsets`, `describe_toolset`, and `call_tool`.
- Preserved direct tool registration by default.
- Added `UNREAL_MCP_TOOL_SEARCH_MODE=1`; in this first pass it exposed those three meta-tools while still cataloging Ghost's 47 toolsets. Later passes added additional meta-tools such as `tool_contribution_contract`.
- Added `unreal_mcp_server/tests/test_toolset_registry.py`.

## Second Implementation Pass

- Added `unreal_mcp_server/client_config.py`.
- Added `unreal_mcp_server/client_config_tools.py`.
- Added the `generate_client_config` MCP tool and registered it through Ghost's toolset registry.
- Supports Epic's client set: Claude Code, Cursor, VS Code, Gemini, Codex, and `all`.
- Supports Ghost's transports: `stdio`, `sse`, and `streamable-http`.
- Uses Epic-style config locations: `.mcp.json`, `.cursor/mcp.json`, `.vscode/mcp.json`, `.gemini/settings.json`, and `.codex/config.toml`.
- Preserves existing JSON client files by upserting only the Ghost server entry.
- Uses a managed TOML block for Codex so generated config can be updated without rewriting unrelated Codex settings.
- Added `unreal_mcp_server/tests/test_client_config.py`.

## Third Implementation Pass

- Expanded `unreal_mcp_server/toolset_registry.py` toward a first-class ToolsetRegistry-style catalog.
- Added stable descriptor schema identifiers:
  - `unreal_mcp_ghost.toolset_descriptor.v1`
  - `unreal_mcp_ghost.toolset_list.v1`
  - `unreal_mcp_ghost.tool_search_result.v1`
- Added stable toolset descriptor fields: `id`, `name`, `module`, `category`, `status`, `roadmap_phase`, `coverage_note`, `metadata`, and `tool_count`.
- Expanded `list_toolsets` with optional `category`, `status`, and `response_format="json"` filters while keeping text output as the default.
- Expanded `describe_toolset` with optional `tool_filter` and schema-rich tool descriptors.
- Added registry-level `search_tools` for category/status/toolset/query searches without adding another public meta-tool.
- Hardened `call_tool` argument handling so it accepts dicts, null, or JSON object strings and returns structured errors for invalid argument payloads.
- Added focused coverage to `unreal_mcp_server/tests/test_toolset_registry.py`.

## Fourth Implementation Pass

- Added `unreal_mcp_server/bridge_descriptors.py`.
- Added `unreal_mcp_server/bridge_descriptor_tools.py`.
- Added `unreal_mcp_server/tests/test_bridge_descriptors.py`.
- Registered bridge descriptor tools through Ghost's toolset registry.
- Added Toolset-like metadata over Ghost's existing TCP bridge command registry without changing the TCP bridge.
- Added bridge descriptor schemas:
  - `unreal_mcp_ghost.bridge_descriptor_summary.v1`
  - `unreal_mcp_ghost.bridge_toolset_descriptor.v1`
  - `unreal_mcp_ghost.bridge_command_search.v1`
- Exposed bridge categories as `bridge.<category>` toolsets.
- Exposed bridge command descriptors with command name, qualified name, category, status, route/reference counts, mutation class, source evidence, and existing drift-review metadata.
- Added MCP tools:
  - `bridge_descriptor_summary`
  - `list_bridge_toolsets`
  - `describe_bridge_toolset`
  - `search_bridge_commands`
- Preserved the existing TCP bridge as the execution path. This pass is metadata/adaptation groundwork for a later optional Unreal-native module.

## Fifth Implementation Pass

- Added `unreal_mcp_server/tools/pcg_tools.py`.
- Added clean-room PCG MCP tools:
  - `pcg_check_support`
  - `pcg_create_graph_asset`
  - `pcg_create_volume`
  - `pcg_refresh_volume`
- The PCG tools use Ghost's existing `exec_python_structured` substrate and Unreal Python reflection instead of Epic source. They defensively check for `PCGGraph`, `PCGGraphFactory`, `PCGVolume`, `PCGComponent`, and PCG generation/refresh methods.
- Added `unreal_mcp_server/skills/city_district/skill.py`.
- Added `unreal_mcp_server/skills/city_district/SKILL.md`.
- Added `skill_generate_city_district`, a no-mutation planner/queue compiler for native-aligned city workflows across:
  - PCG support checks, graph asset shells, PCG volumes, and refresh
  - World Partition edit-region setup
  - Data Layer creation
  - Blueprint spline and ISM blockout fallbacks
  - HLOD assignment/build reporting
  - viewport screenshot evidence
  - optional MassEntity and SmartObject scaffolding
- Registered PCG tools and the city/district skill through Ghost's ToolsetRegistry facade in `unreal_mcp_server/unreal_mcp_server.py`.
- Added inventory metadata for `tools.pcg_tools` and `skills.city_district.skill`.
- Added focused tests:
  - `unreal_mcp_server/tests/test_pcg_tools.py`
  - `unreal_mcp_server/tests/test_city_district_skill.py`
- This pass does not claim full production city generation. It creates the workflow surface and honest validation gates needed before deeper native integration.

## Sixth Implementation Pass

- Added `unreal_mcp_server/server_runtime.py`.
- Added `unreal_mcp_server/server_runtime_tools.py`.
- Added native-alignment MCP tools:
  - `server_lifecycle_status`
  - `server_transport_diagnostics`
  - `server_refresh_metadata`
  - `server_list_operations`
  - `server_operation_status`
  - `server_cancel_operation`
- Wired FastMCP lifespan events into runtime state:
  - startup/running/shutdown transitions
  - lazy Unreal bridge connection attempts
  - startup Python warmup result
  - selected transport, MCP host/port, Unreal bridge host/port, direct/tool-search mode
- Added `ToolsetRegistry.refresh_inventory()` so category/status/roadmap metadata can refresh without re-registering Python functions.
- Added cooperative operation tracking around `ToolsetRegistry.call_tool`, including bounded progress events, result summaries, and cancellation request records.
- Registered the runtime tools through Ghost's ToolsetRegistry facade under category `native_mcp_runtime`.
- Preserved Ghost's existing process-managed server lifecycle: start/stop remain CLI/process concerns, while the new tool surface reports state and supports safe metadata refresh.
- Flagged native gaps directly in tool output: Ghost is not yet an Unreal Editor native HTTP MCP server, does not expose Epic's private session implementation, and cancellation is cooperative rather than hard preemption for running UE TCP bridge commands.
- Added focused tests in `unreal_mcp_server/tests/test_server_runtime.py`.

## Seventh Implementation Pass

- Re-audited the staged UE 5.8 sparse checkout for spatial-awareness source.
- Confirmed the local checkout only exposed `SceneTools.add_to_scene_from_asset` as an analytics/test identifier; no Epic Python `SceneTools` implementation was present to inspect.
- Added `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- Added clean-room read-only MCP tools:
  - `spatial_scene_overview`
  - `spatial_query_actors`
  - `spatial_describe_actor`
  - `spatial_proximity_map`
  - `spatial_view_context`
- The spatial tools use Ghost's existing `exec_python_structured` substrate and Unreal Python editor APIs such as `EditorActorSubsystem` and `LevelEditorSubsystem` where available.
- The toolset reports live actors, selected actors, classes, tags, transforms, bounds, components, proximity ordering, and viewport camera context without mutating the Unreal scene.
- Registered the spatial toolset through Ghost's ToolsetRegistry facade and added inventory metadata under category `spatial_awareness`.
- Added focused tests in `unreal_mcp_server/tests/test_spatial_awareness_tools.py`, including generated Unreal Python parsing checks.
- This pass does not implement Epic's `add_to_scene_from_asset`; a future clean-room placement tool should be designed from Ghost bridge capabilities and public Unreal Python behavior, or sent through legal review if Epic source is located and considered.

## Eighth Implementation Pass

- Completed the first guarded execution layer above `unreal_mcp_server/bridge_descriptors.py`.
- Added `call_bridge_command` to `unreal_mcp_server/bridge_descriptor_tools.py`.
- The tool accepts plain or qualified bridge command names, JSON-object params, and the same descriptor registry path override used by bridge descriptor inspection tools.
- It is dry-run by default and returns schema `unreal_mcp_ghost.bridge_command_call.v1`.
- Read-only bridge commands can execute when `dry_run=false`.
- Commands classified as `editor_mutation` or `unknown` require `allow_mutation=true` before execution.
- Commands absent from the descriptor registry require `allow_unknown=true`, keeping descriptor drift visible instead of silently bypassing the registry.
- Actual execution still uses Ghost's existing `get_unreal_connection().send_command(...)` TCP bridge path; no Epic ToolsetRegistry dispatch code was copied or embedded.
- Added focused tests for dry-run planning, mutation blocking, JSON param validation, and patched execution.

## Ninth Implementation Pass

- Added `spatial_add_asset_to_scene` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- This is a clean-room, public-Unreal-Python implementation of the asset-to-scene workflow implied by the `SceneTools.add_to_scene_from_asset` breadcrumb; no Epic `SceneTools` implementation was available or copied.
- The tool is dry-run by default and returns a placement plan with schema `unreal_mcp_ghost.spatial_asset_placement.v1`.
- Real placement requires `dry_run=false` and `allow_mutation=true`.
- Real placement uses Ghost's `exec_python_transactional` substrate so the operation appears as one Unreal editor transaction where the underlying editor API supports rollback.
- The generated Unreal Python tries `EditorActorSubsystem.spawn_actor_from_object`, falls back to `EditorLevelLibrary.spawn_actor_from_object`, and has Blueprint-class spawning fallbacks when public API access exposes a generated class.
- Added tests for dry-run behavior, mutation gating, content path/vector validation, transactional execution wiring, and generated Unreal Python parsing.

## Tenth Implementation Pass

- Extended `spatial_add_asset_to_scene` with optional `tags`, `data_layer_names`, and `fail_on_missing_data_layer` inputs.
- Dry-run plans now include tag and Data Layer intent before any editor mutation.
- Real placement applies actor tags and then attempts best-effort Data Layer assignment through public Unreal Python `DataLayerEditorSubsystem` APIs when that subsystem is available.
- The generated Unreal Python probes common Data Layer instance/asset method names across UE versions instead of assuming one private implementation shape.
- Missing or unassignable Data Layers are warnings by default, or hard errors when `fail_on_missing_data_layer=true`.
- This is still clean-room Ghost behavior. It does not copy Epic `SceneTools` implementation details and should be runtime-validated in a UE 5.8 World Partition project before claiming parity with native spatial tools.

## Eleventh Implementation Pass

- Added `spatial_select_actors` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- This extends the spatial bridge from passive querying into selection-aware editor workflows without copying Epic `SceneTools` source.
- Dry-run mode executes read-only actor resolution using the same query/class/tag/radius/box filters as the spatial query layer.
- Real execution requires `dry_run=false` and `allow_mutation=true`, then applies editor selection through public Unreal Python `EditorActorSubsystem.set_selected_level_actors` with an `EditorLevelLibrary` fallback.
- The tool supports `replace`, `add`, and `remove` selection modes, optional empty-selection allowance, and an optional viewport camera focus attempt through `LevelEditorSubsystem.set_level_viewport_camera_info` when available.
- Outputs include selected-before/after descriptors, aggregate bounds, focus center, and recommended follow-up calls to Ghost's existing `focus_viewport` and `viewport_capture_screenshot` tools for evidence capture.
- This closes part of the selection-aware and viewport-framed validation gap. Runtime validation in a UE 5.8 editor session is still needed before claiming native SceneTools parity.

## Twelfth Implementation Pass

- Added `spatial_content_selection_context` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- This is a clean-room Content Browser selection bridge: it reads selected assets through public Unreal Python `EditorUtilityLibrary` accessors where available and does not mutate the editor.
- The tool returns selected asset descriptors, conservative placeability hints, and ready-to-review `spatial_add_asset_to_scene` argument sets.
- Placement handoffs support line/grid/stack layout planning plus actor-label prefixes, actor tags, and Data Layer names.
- The generated workflow explicitly keeps execution dry-run-first: review Content Browser selection, dry-run individual placements, execute only with `dry_run=false` and `allow_mutation=true`, then use spatial selection and viewport screenshot evidence tools.
- This closes the first Content Browser selection handoff gap without copying Epic `SceneTools` implementation. Direct native parity is still not claimed.

## Thirteenth Implementation Pass

- Added `spatial_place_selected_assets` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- This is a clean-room batch placement bridge for Content Browser selection and explicit asset-path handoffs.
- Dry-run mode resolves selected assets or explicit paths and returns a batch placement plan with schema `unreal_mcp_ghost.spatial_selected_asset_placement.v1`.
- Real execution requires `dry_run=false` and `allow_mutation=true`, then uses Ghost's transactional Unreal Python substrate to place all resolved assets in one editor transaction.
- Batch placement supports line/grid/stack layout, actor label prefixes, rotation/scale, actor tags, best-effort Data Layer assignment, optional placed-actor selection, and evidence-oriented follow-up recommendations.
- The generated Unreal Python uses public APIs such as `EditorUtilityLibrary.get_selected_assets`, `EditorActorSubsystem.spawn_actor_from_object`, `EditorLevelLibrary.spawn_actor_from_object`, Blueprint generated-class fallbacks, and `DataLayerEditorSubsystem` method probing where available.
- This closes the first direct multi-asset placement-from-selection gap without copying Epic `SceneTools` implementation. Runtime validation in UE 5.8 is still required before claiming native SceneTools parity.

## Fourteenth Implementation Pass

- Added `spatial_infer_placement_policy` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- This is a local, read-only policy planner that classifies asset paths and intent into clean-room placement policies such as `city_block`, `gameplay_poi`, `set_dressing`, `lighting`, `vfx`, `linear_showcase`, and `vertical_stack`.
- The planner returns schema `unreal_mcp_ghost.spatial_placement_policy.v1` with confidence, category scores, effective layout, spacing, tags, advisory Data Layer names, and ready-to-review handoff arguments for `spatial_place_selected_assets` and `spatial_content_selection_context`.
- Recommended Data Layer names are advisory by default; the planner does not silently opt users into editor Data Layer assignment.
- This narrows the placement-policy gap without copying or depending on Epic `SceneTools` implementation. Richer native parity still needs runtime-aware policies such as direct placement snapping, collision clearance, viewport hit testing, and project-authored placement rules.

## Fifteenth Implementation Pass

- Added `spatial_surface_probe` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- This is a clean-room, read-only surface-awareness bridge that performs downward line traces through public Unreal Python APIs and returns hit locations, hit normals, hit actors, surface-adjusted placement locations, and dry-run placement handoff templates.
- The generated Unreal Python tries `world.line_trace_single_by_channel` first and falls back to `unreal.SystemLibrary.line_trace_single`, matching Ghost's existing public-API trace style rather than copying Epic `SceneTools` implementation details.
- The tool supports explicit world-space points or centered probe grids, `visibility`/`camera` trace selection, actor ignore filtering, configurable trace height/depth, and normal-offset placement planning.
- This closes the first surface-awareness gap for placement planning. It does not claim full native `SceneTools.add_to_scene_from_asset` parity: direct snap-on-place behavior, collision clearance, viewport hit testing, and UE 5.8 runtime proof still need live-editor validation or future clean-room tooling.

## Sixteenth Implementation Pass

- Added `spatial_validate_placement` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- This is a clean-room, read-only post-placement validation bridge that resolves actors through the existing spatial filters, traces from actor bounds toward nearby surfaces, and reports actors as `on_surface`, `floating`, `intersecting_or_below_surface`, or `no_surface_hit`.
- The generated Unreal Python also performs a conservative axis-aligned-bounds overlap check with configurable padding. This is collision-clearance evidence, not a replacement for Unreal physics/collision queries.
- Outputs include aggregate bounds, validation summaries, per-actor surface gaps, hit normals, hit actors, potential overlaps, and ready-to-review `focus_viewport` plus `viewport_capture_screenshot` follow-up arguments.
- This narrows the viewport/evidence and collision-clearance planning gap without copying Epic `SceneTools` implementation. Live UE 5.8 validation is still required before claiming native spatial-tool parity.

## Seventeenth Implementation Pass

- Added `server_protocol_contract` to `unreal_mcp_server/server_runtime_tools.py`.
- Added schema `unreal_mcp_ghost.server_protocol_contract.v1` and `ServerRuntimeState.protocol_contract()` in `unreal_mcp_server/server_runtime.py`.
- The contract reports Ghost-owned behavior, FastMCP-delegated behavior, and Unreal TCP bridge-owned behavior separately so clients do not mistake Ghost's Python server for Epic's in-editor HTTP MCP server.
- It documents stdio/SSE/streamable HTTP endpoints, session/header guidance for `Mcp-Session-Id`, `Origin`, and `MCP-Protocol-Version`, JSON-RPC surface expectations, tool-search mode behavior, progress/cancellation scope, security posture, preserved Ghost compatibility, native parity gaps, and legal-review boundaries.
- This narrows the transport/session documentation gap without copying Epic `ModelContextProtocol` source or claiming Epic's private session store, origin validation, or protocol-version validation implementation.

## Eighteenth Implementation Pass

- Added `spatial_plan_interior_composition` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- Added schema `unreal_mcp_ghost.spatial_interior_composition.v1`.
- The planner turns apartment/interior room dimensions, optional screenshot-derived prop observations, required/omitted prop lists, existing asset paths, style intent, and a target content path into:
  - functional room zones such as kitchen, living, sleeping, entry, and bathroom
  - context-aware prop requirements such as refrigerator, stove, counters, cabinets, sink, bar stool, books, clutter, sofa, coffee table, bed, and storage
  - existing-asset matches when Content Browser paths are supplied
  - guarded Tripo generation handoffs using `gen_tripo_text_to_model` and optional crop-required `gen_tripo_image_to_model`, both with `confirm_spend=false`
  - `gen_tripo_import_to_project` import handoffs for successful Tripo tasks
  - dry-run `spatial_add_asset_to_scene`, `spatial_surface_probe`, `spatial_validate_placement`, and screenshot/focus evidence handoffs
- This creates the first clean-room apartment/interior composition bridge above Ghost's lower-level spatial probes and placement tools. It does not perform vision segmentation by itself; screenshot workflows now have a decomposition contract requiring the agent to identify/crop individual props before image-to-model generation.
- This preserves Ghost's Tripo differentiator and avoids copying Epic `SceneTools` source. Runtime validation in a live UE editor scene is still needed before claiming production-quality interior design parity.

## Nineteenth Implementation Pass

- Added schema `unreal_mcp_ghost.tool_contribution_contract.v1` to `unreal_mcp_server/toolset_registry.py`.
- Added `ToolsetRegistry.contribution_contract()` and exposed it as the `tool_contribution_contract` meta-tool.
- The contract documents Ghost-owned contribution styles:
  - decorated Python tool modules captured through `ToolsetCollectingMCP.tool()`
  - direct `ToolsetRegistry.register_tool(...)` registration for tests/adapters
  - bridge descriptor adapters over Ghost's existing TCP bridge command registry
  - higher-level skill modules registered through the same catalog
- It records registration invariants for stable tool names, toolset-qualified names, JSON-serializable defaults, hidden `ctx`/`context` parameters, mutation gates, runtime operation tracking, and inventory metadata.
- It explicitly states unsupported native gaps: this is not Epic's module-level C++ `AddTool` API, not a `UFUNCTION`/`UToolsetDefinition` reflection importer, and not a replacement for an in-editor C++ ToolsetRegistry adapter.
- It carries legal-review gates for direct copying of Epic `ModelContextProtocol`, `ToolsetRegistry`, `GASToolsets`, or `MCPClientToolset` source and preserves Ghost differentiators such as knowledge_base, project intelligence, higher-level skills, Tripo workflows, and spatial/worldbuilding automation.
- Updated `ServerRuntimeState.protocol_contract()` so runtime diagnostics report the fourth meta-tool alongside `list_toolsets`, `describe_toolset`, and `call_tool`.

## Twentieth Implementation Pass

- Added `spatial_plan_screenshot_reconstruction` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- Added schema `unreal_mcp_ghost.spatial_screenshot_reconstruction.v1`.
- The planner formalizes Ghost's screenshot-driven reconstruction workflow:
  - returns an explicit detected-item JSON contract when the agent has not yet segmented the reference image
  - accepts detected props, zones, surfaces, crop boxes, crop hints, placement hints, scale hints, counts, confidence, and optional existing `/Game` asset paths
  - feeds detected props into the existing interior composition planner so image-derived items become dry-run spatial placement steps
  - maps each detected item to an existing asset, a guarded `gen_tripo_image_to_model` crop task, a guarded `gen_tripo_text_to_model` fallback, or an unresolved missing asset
  - keeps all Tripo spend gates at `confirm_spend=false` and requires cropped prop images instead of submitting full-room screenshots
  - carries spatial validation and viewport evidence handoffs through `spatial_surface_probe`, `spatial_validate_placement`, `spatial_select_actors`, `focus_viewport`, and `viewport_capture_screenshot`
- This moves Ghost closer to the requested apartment/interior reconstruction workflow while preserving the vision boundary: the MCP server plans from supplied image detections but does not yet run automated segmentation itself.
- The implementation remains a clean-room Ghost workflow. Legal review is still required before reusing native Epic SceneTools, ToolsetRegistry, or asset-placement source.

## Twenty-First Implementation Pass

- Added `spatial_analyze_room` to `unreal_mcp_server/tools/spatial_awareness_tools.py`.
- Added schema `unreal_mcp_ghost.spatial_room_analysis.v1`.
- The tool reads live Unreal Editor actors through the existing structured execution substrate and infers a planner-ready room model:
  - room bounds, origin, dimensions, floor height, ceiling height, and center from selected or filtered actors
  - functional zones for apartment, studio, kitchen, living room, bedroom, bathroom, hallway, utility, and generic interiors
  - classified floors, walls, ceilings, openings, horizontal supports, and blocking obstacles from actor names/tags/classes plus bounding-box proportions
  - bounds-based clearance summaries and circulation risk flags before mutation
  - handoff arguments for `spatial_plan_interior_composition`, `spatial_surface_probe`, `spatial_infer_placement_policy`, and `spatial_validate_placement`
- Extended the interior room taxonomy and prop library with hallway/utility support, including utility shelving and washer/dryer-style appliance planning.
- This closes part of the gap between manual dimensions and real scene understanding: agents can now ask Ghost to inspect a live apartment/interior shell before generating or placing props. It remains a bounds/name/tag heuristic and should be validated with surface traces, collision checks, viewport evidence, and live editor review.
- The implementation is clean-room Ghost Python over public Unreal editor APIs. It does not copy Epic native SceneTools source; direct reuse of Epic room/surface internals still requires legal review.

## Twenty-Second Implementation Pass

- Added `room_analysis_json` ingestion to `spatial_plan_interior_composition` and `spatial_plan_screenshot_reconstruction`.
- The planners now accept either a full MCP `spatial_analyze_room` result or its `outputs` object, then normalize:
  - measured room type, dimensions, and origin
  - analysis-derived zones
  - surface counts and clearance-risk observations
  - analysis-provided `spatial_surface_probe` points
  - validation clearance padding
- Interior composition now records `room_analysis.applied=true` when analysis context is used, switches its first workflow step to `spatial_analyze_room`, merges room-analysis observations into the screenshot/context evidence list, and uses analysis probe points before generated placement points.
- Screenshot reconstruction now passes the same room-analysis context through to its nested composition plan, letting reference-image workflows rebuild against measured Unreal room bounds instead of hand-entered dimensions.
- This creates the first clean room-analysis-to-composition bridge: an agent can run `spatial_analyze_room`, feed the result into composition/reconstruction, generate missing props through guarded Tripo tasks, and then validate with the existing probe/placement/evidence tools. It remains a planning bridge and does not execute Tripo spend, imports, placement mutation, or automated screenshot segmentation by itself.
- Legal-review status remains unchanged: this is Ghost-owned JSON normalization and planning, not copied Epic native MCP or SceneTools source.

## Twenty-Third Implementation Pass

- Refined `spatial_plan_interior_composition` placement behavior so room-analysis surfaces can influence prop locations:
  - counter/table/shelf props, books, clutter, and fixtures can use `classified_surfaces.horizontal_supports` top centers
  - wall-mounted props such as wall cabinets can use `classified_surfaces.walls`
  - floor props can inherit floor Z from `classified_surfaces.floors`
  - each placement records a `source` such as `room_analysis_horizontal_support`, `room_analysis_wall`, `room_analysis_floor_z`, or `zone_heuristic`
  - placement steps now carry `placement_source` so execution/evidence layers can explain why a prop was positioned there
- Added support actor metadata (`support_actor`, `support_roles`) to planned prop placements when a room-analysis support surface is used.
- Improved interior prop matching so exact names/aliases such as `counter clutter` and `wall cabinets` win over broader substring matches such as `counter` or `cabinets`.
- This improves the apartment/interior workflow from "zone slot placement" toward "place the right thing on the right support surface" while remaining dry-run-first and validation-dependent.
- Legal-review status remains unchanged: this is a clean-room heuristic over Ghost's room-analysis output, not copied Epic SceneTools behavior.

## Twenty-Fourth Implementation Pass

- Added `spatial_plan_composition_iteration` as a local/read-only correction planner over Ghost's own `spatial_plan_interior_composition` and `spatial_validate_placement` outputs.
- Added schema `unreal_mcp_ghost.spatial_composition_iteration.v1`.
- The planner now turns validation statuses into reviewed correction candidates:
  - `floating` lowers the candidate Z by the measured surface gap when available
  - `intersecting_or_below_surface` raises the candidate by the measured gap plus tolerance
  - `no_surface_hit` routes the candidate through `spatial_surface_probe` before final movement
  - `potential_overlap` generates a conservative XY nudge and revalidation handoff
- Correction entries are dry-run-first and carry explicit `allow_mutation=false`; any actual move is expressed only as a reviewed `set_actor_transform` handoff.
- Added viewport evidence and iteration handoffs: resolve actors, focus/capture screenshot, optionally compare against a reference screenshot, re-run `spatial_validate_placement`, then feed the new validation back into the iteration planner.
- This closes part of the apartment/worldbuilding feedback loop: place, validate, see, correct, and validate again. Automated image segmentation, automatic viewport execution, and live UE end-to-end validation remain future work.
- Legal-review status remains unchanged: this is Ghost-owned planning over Ghost schemas and does not copy Epic SceneTools or native MCP implementation code.

## Twenty-Fifth Implementation Pass

- Added `spatial_bind_generated_assets_to_composition` as a local/read-only binding planner between Ghost's guarded Tripo/import pipeline and dry-run spatial placement.
- Added schema `unreal_mcp_ghost.spatial_composition_asset_binding.v1`.
- The planner consumes an interior composition plan plus completed `gen_tripo_import_to_project` results or explicit asset overrides, then:
  - matches imported `/Game` assets back to prop IDs, actor labels, generated asset names, or Tripo task IDs
  - replaces `<IMPORTED_ASSET_PATH_FOR_...>` placeholders in placement steps with real Content Browser asset paths
  - preserves existing `/Game` asset steps without requiring generation
  - separates resolved placement steps from unresolved generated-asset follow-ups
  - carries remaining guarded generation/import handoffs for unresolved props
  - emits `spatial_add_asset_to_scene`, `spatial_validate_placement`, and `spatial_plan_composition_iteration` handoffs for the next build pass
- This strengthens the "generate what is missing, import it, then spatially place and validate it" workflow without calling paid providers or mutating the editor scene inside the binding step.
- Legal-review status remains unchanged: this is Ghost-owned data mapping over Ghost/Tripo result schemas and does not copy Epic native MCP implementation code.

## Twenty-Sixth Implementation Pass

- Added `spatial_preflight_interior_layout` as a local/read-only approximate geometry preflight for apartment/interior composition plans before editor placement.
- Added schema `unreal_mcp_ghost.spatial_layout_preflight.v1`.
- The planner accepts native interior composition outputs, screenshot reconstruction outputs with nested composition plans, and generated-asset binding outputs.
- It checks:
  - approximate room bounds and prop footprints
  - pairwise floor-prop overlap and tight spacing
  - declared zone versus inferred zone
  - suspicious floor/support/wall contact before live traces
  - conservative central circulation band risks
  - simple apartment composition relationships such as sink/counter context and bar-stool anchoring
- It emits advisory issues plus `spatial_surface_probe`, `spatial_validate_placement`, and `spatial_plan_composition_iteration` handoffs so agents can move from local preflight to live Unreal validation and correction.
- This makes "sensible scale, alignment, spacing, surface contact, collision clearance, and visual composition" more explicit before mutation, while preserving live Unreal validation as the authority.
- Legal-review status remains unchanged: this is Ghost-owned approximate layout logic and does not copy Epic native MCP or SceneTools source.

## Twenty-Seventh Implementation Pass

- Improved screenshot-driven reconstruction placement by making detected-item `placement_hint` values influence initial spatial transforms before dry-run placement.
- Added deterministic hint handling for common interior reference-image relationships, including:
  - left/right/front/back wall placement
  - kitchen wall placement
  - coffee-table anchors for books/clutter
  - counter/countertop/island/under-cabinet anchors
  - center/middle hints
  - floor and wall-height contact hints
- Prop placements and placement steps now carry hint-derived provenance such as `placement_hint_anchor_coffee_table` or `placement_hint_left_wall_kitchen_wall`.
- When live room analysis later adjusts a hinted placement for floor/support/wall data, the planner preserves `placement_hint_source` so the agent can explain that both screenshot relationship text and room measurement influenced the final dry-run transform.
- This does not perform computer vision segmentation itself; it makes the spatial planner use the agent/vision detection output more faithfully.
- Legal-review status remains unchanged: this is Ghost-owned relationship parsing over Ghost screenshot reconstruction inputs and does not copy Epic native MCP or SceneTools source.

## Twenty-Eighth Implementation Pass

- Added `spatial_preflight_screenshot_detections` as a local/read-only detection QA and normalization step before screenshot reconstruction or paid Tripo crop generation.
- Added schema `unreal_mcp_ghost.spatial_screenshot_decomposition_preflight.v1`.
- The tool validates agent/vision-supplied `detected_items_json` for crop box availability, image bounds, low confidence, tiny crops, and heavily overlapping crops.
- It infers missing zones, support surfaces, and placement hints from Ghost's interior prop library plus frame position, then emits normalized detected-items JSON for `spatial_plan_screenshot_reconstruction`.
- This gives the screenshot-to-worldbuilding workflow a guarded preflight before crop-to-model spend while preserving the existing Tripo image/text generation and Unreal placement handoffs.
- Legal-review status remains unchanged: this is Ghost-owned detection metadata QA over agent-supplied item records. It does not copy Epic native MCP, SceneTools source, or proprietary vision segmentation logic.

## Twenty-Ninth Implementation Pass

- Added `spatial_prepare_tripo_generation_batch` as a local/read-only bridge from interior composition or screenshot reconstruction plans into a guarded Tripo batch manifest.
- Added schema `unreal_mcp_ghost.spatial_tripo_generation_batch.v1`.
- The batch planner:
  - accepts interior composition, screenshot reconstruction, or generated-asset binding outputs
  - prefers screenshot crop/image-to-model jobs when available, while retaining text-to-model fallbacks
  - preserves `confirm_spend=false` by default and records the user confirmation requirement before paid generation
  - normalizes session names, content paths, wait/import handoffs, post-import binding, placement, validation, and iteration follow-ups
  - keeps actual Tripo submission/import/placement execution outside the planning step
- This closes more of the "generate what is missing, import it, place it spatially, then validate" workflow without hiding paid provider calls behind a spatial planner.
- Legal-review status remains unchanged: this is Ghost-owned batch-manifest orchestration over Ghost composition/screenshot schemas and Ghost Tripo tool names. It does not copy Epic native MCP, SceneTools, or provider implementation source.

## Thirtieth Implementation Pass

- Added `spatial_prepare_screenshot_crop_manifest` as the local file bridge between screenshot detection crop boxes and Tripo image-to-model inputs.
- Added schema `unreal_mcp_ghost.spatial_screenshot_crop_manifest.v1`.
- The tool:
  - accepts either `detected_items_json` plus a local reference screenshot or an existing screenshot reconstruction output
  - opens the local screenshot with Pillow, clips/pads crop boxes, writes one PNG per missing prop crop, and records crop dimensions
  - updates screenshot reconstruction crop tasks from `<CROP_FOR_...>` placeholders to real `image_path` values
  - emits guarded `gen_tripo_image_to_model` handoffs with `confirm_spend=false`
  - feeds directly into `spatial_prepare_tripo_generation_batch`
- This makes screenshot-driven reconstruction materially more executable: after an agent/vision step provides crop boxes, Ghost can produce real local prop crops for Tripo while still requiring human review and explicit spend approval.
- Legal-review status remains unchanged: this is Ghost-owned local image cropping over agent-supplied crop boxes. It does not perform proprietary vision segmentation and does not copy Epic native MCP or SceneTools source.

## Thirty-First Implementation Pass

- Added `spatial_apply_composition_plan` as the dry-run-first bridge from a completed spatial composition or generated-asset binding output into batch editor placement.
- Added schema `unreal_mcp_ghost.spatial_composition_placement_batch.v1`.
- The tool:
  - accepts interior composition, screenshot reconstruction, or generated-asset binding outputs
  - normalizes every placement step into a reviewed placement queue
  - blocks unresolved generated-asset placeholders by default
  - can consume `spatial_preflight_interior_layout` output and block mutation when layout errors remain
  - returns validation, evidence, and iteration handoffs for the post-placement workflow
  - executes live placement only when `dry_run=false` and `allow_mutation=true`, reusing Ghost's existing per-asset transactional Unreal Python placement substrate
- This closes another practical loop in the worldbuilding workflow: after assets are generated/imported/bound, an agent can review and then apply a whole room composition rather than manually calling one placement tool per asset.
- Legal-review status remains unchanged: this is Ghost-owned orchestration over Ghost placement schemas and public Unreal Python editor APIs. It does not copy Epic native MCP or SceneTools source.

## Thirty-Second Implementation Pass

- Added `spatial_infer_screenshot_scene_graph` as a clean-room relationship inference bridge over agent/vision-supplied screenshot detections.
- Added schema `unreal_mcp_ghost.spatial_screenshot_scene_graph.v1`.
- The tool:
  - consumes detected-item metadata and optional crop/image dimensions
  - infers nodes, frame regions, zone clusters, support/contact relationships, left/right/front/back relations, wall anchors, and composition constraints
  - preserves normalized detected items and placement hints for `spatial_plan_screenshot_reconstruction`
  - emits workflow handoffs into crop manifests, reconstruction planning, Tripo generation batches, generated-asset binding, composition batch application, and validation
- This improves screenshot-driven reconstruction from "a list of props" toward "a relational composition" so the agent can preserve object context such as books on a coffee table, clutter on a counter, and appliances against a kitchen wall.
- Legal-review status remains unchanged: this is Ghost-owned relationship inference over Ghost detection metadata. It does not perform proprietary vision segmentation and does not copy Epic native MCP or SceneTools source.

## Thirty-Third Implementation Pass

- Extended `spatial_plan_screenshot_reconstruction` with optional `scene_graph_json` input.
- Added clean-room scene-graph consumption helpers that:
  - accept either direct scene-graph outputs or a wrapped Ghost local-result payload
  - fill missing detected-item metadata from graph nodes and normalized detected items
  - derive placement hints from support and wall-anchor relations, such as `on the coffee table`, `on the kitchen counter run`, or `against the left kitchen wall`
  - preserve graph relations, zone clusters, and composition constraints in the reconstruction output
  - feed relationship observations into the downstream interior composition planner
- `spatial_infer_screenshot_scene_graph` now advertises a reconstruction handoff that includes a `scene_graph_json` placeholder, so agents can pass the graph forward without losing relationship constraints.
- This tightens the screenshot workflow from "infer relationships, then manually remember them" to "infer relationships, pass the graph, and let reconstruction honor support/wall constraints while still requiring review before generation or placement."
- Legal-review status remains unchanged: this is Ghost-owned schema parsing and planning over Ghost scene-graph data. It does not copy Epic native MCP, SceneTools, or proprietary computer-vision source.

## Thirty-Fourth Implementation Pass

- Added `spatial_resolve_project_assets` as a dry-run project asset resolution checkpoint before guarded Tripo generation.
- Added schema `unreal_mcp_ghost.spatial_project_asset_resolution.v1`.
- The tool:
  - accepts an interior composition, screenshot reconstruction, or compatible composition-like payload
  - consumes a provided project asset catalog or explicit candidate `/Game` asset paths
  - scores assets against prop names, ids, aliases, categories, zones, surfaces, tags, classes, folders, and descriptions
  - emits reviewable matches, unresolved props, `asset_overrides_json`, and a `spatial_bind_generated_assets_to_composition` handoff
  - routes unresolved props toward `spatial_prepare_tripo_generation_batch` only after existing project assets are reviewed/bound
- This improves the north-star workflow by preferring known project content before spending Tripo credits, while still preserving the guarded generate/import/bind/place/validate loop for truly missing props.
- Legal-review status remains unchanged: this is Ghost-owned lexical matching over provided project catalog metadata and Ghost composition schemas. It does not copy Epic native MCP, SceneTools, asset registry implementation details, or paid-provider code.

## Thirty-Fifth Implementation Pass

- Added `spatial_catalog_project_assets` as a read-only live project asset catalog bridge for spatial worldbuilding.
- Added schema `unreal_mcp_ghost.spatial_project_asset_catalog.v1`.
- The tool:
  - queries `/Game` folders through public Unreal Python `AssetRegistryHelpers`, with `EditorAssetLibrary.list_assets` as a fallback/enrichment path
  - includes selected assets through `EditorUtilityLibrary` when requested
  - filters by query text and prop-friendly classes such as `StaticMesh` and `Blueprint`
  - emits resolver-ready `asset_catalog_json`
  - hands the catalog to `spatial_resolve_project_assets` so agents can match existing assets before preparing Tripo generation jobs
- This closes the immediate gap between the project-aware resolver and live Unreal project content: agents no longer need a hand-authored catalog to prefer existing meshes/Blueprints for apartment reconstruction.
- Legal-review status remains unchanged: this is Ghost-owned read-only use of public Unreal Python editor APIs. It does not copy Epic native MCP, SceneTools, AssetRegistry source, or NoRedist implementation details.

## Thirty-Sixth Implementation Pass

- Extended `spatial_catalog_project_assets` with optional `include_bounds` support.
- Project catalog rows can now carry `approx_size_cm` from supplied catalog metadata or read-only Unreal asset bounds when requested.
- Extended `spatial_resolve_project_assets` scoring with size-aware candidate matching:
  - close size matches receive a positive score reason such as `size_close_match`
  - plausible matches receive a smaller positive adjustment
  - loose/strong mismatches are penalized so a small prop is less likely to satisfy a full-size appliance requirement
- Candidate rows now include `approx_size_cm` in match results so agents can audit why an existing asset was selected.
- This advances the spatial goal from name-based asset matching toward scale-aware composition, which matters for apartment props such as refrigerators, counters, cabinets, stools, and clutter.
- Legal-review status remains unchanged: this is Ghost-owned scoring over Ghost catalog metadata plus optional public Unreal Python bounds reads. It does not copy Epic native MCP or SceneTools placement code.

## Thirty-Seventh Implementation Pass

- Extended `spatial_plan_interior_composition` to emit Ghost-owned semantic composition constraints in addition to transforms.
- The planner now records intent for:
  - kitchen work triangles between refrigerator, stove/oven, and sink
  - counter adjacency for sinks, stools, appliances, clutter, and related kitchen props
  - support contact for counter/table/shelf/cabinet props
  - wall anchoring for wall-mounted pieces such as upper cabinets
  - living-area visual grouping for sofa, coffee table, and rug
  - central circulation clearance
- Extended `spatial_preflight_interior_layout` to evaluate semantic constraints before placement, producing warnings such as `semantic_counter_adjacency_gap`, `semantic_support_contact_unresolved`, `semantic_wall_anchor_unresolved`, `semantic_kitchen_work_triangle_review`, and `semantic_living_group_spacing`.
- This moves Ghost beyond object-by-object placement toward composition reasoning: the planner can now explain why objects belong near/supporting/anchoring each other before Tripo generation or live Unreal placement.
- Legal-review status remains unchanged: this is clean-room Ghost planning/preflight metadata and approximate geometry logic. It does not copy Epic native MCP or SceneTools implementation code.

## Thirty-Eighth Implementation Pass

- Extended the guarded Tripo path with `spatial_fit` metadata for generated props.
- Text-to-model prompts and text fallbacks now include spatial-fit language for:
  - zone and support/contact target
  - target Unreal-centimeter size
  - floor/counter/table/shelf/wall/ceiling contact requirements
  - relevant semantic constraints such as support contact, counter adjacency, work triangles, living groupings, and circulation
- Image-to-model jobs do not receive unsupported provider prompt arguments; instead the batch manifest carries `spatial_fit` and `review_requirements` so the agent can verify the crop/generated mesh before import, binding, placement, and validation.
- The Tripo spend guard remains unchanged: generated jobs still default to `confirm_spend=false`, and `spatial_prepare_tripo_generation_batch` remains a manifest builder rather than a paid task submitter.
- This advances environment-specific generation: Ghost no longer asks Tripo for isolated props only, but describes how each generated object should fit the Unreal room composition.
- Legal-review status remains unchanged: this is Ghost-owned prompt/manifest enrichment over Ghost composition data and public provider arguments. It does not copy Epic native MCP, SceneTools, or Tripo provider implementation source.

## Thirty-Ninth Implementation Pass

- Extended `spatial_bind_generated_assets_to_composition` with post-import spatial-fit review records.
- Import result and override normalization now preserve optional generated/project asset size/bounds metadata from Tripo/import outputs or richer asset override objects when available.
- Binding output now emits `spatial_fit_reviews`, a review count, and a summary that distinguishes ready assets, missing bounds, size-review candidates, and unresolved imports.
- Each generated/imported or project-resolved asset review compares planned `spatial_fit` or `approx_size_cm` against imported/cataloged bounds using the same clean-room size scoring language as project asset resolution.
- Bound props and dry-run placement steps carry their review record, so agents can inspect scale, surface/contact expectations, and clearance settings before enabling mutation.
- The workflow now includes `review_spatial_fit` between `review_import_results` and dry-run placement, preserving the guarded sequence: prompt planning, spend confirmation, generation, import, fit review, dry-run placement, validation, iteration.
- The review remains advisory and local. Live Unreal traces, collision, viewport evidence, and user approval still govern final placement.
- Legal-review status remains unchanged: this is Ghost-owned review metadata over Ghost composition/import schemas and does not copy Epic native MCP, SceneTools, or provider source.

## Fortieth Implementation Pass

- Extended `spatial_apply_composition_plan` so generated/project asset `spatial_fit_review` records now gate batch placement mutation by default.
- Binding outputs preserve `spatial_fit_reviews` through the composition-like parser, and each placement queue item is annotated with its review status, blocking flag, and blocking reason.
- The batch planner now reports `spatial_fit_review_count`, `spatial_fit_blocker_count`, `spatial_fit_blockers`, and workflow step `review_spatial_fit`.
- Mutation is blocked with status `blocked_by_spatial_fit_review` when a resolved asset still has a review status such as `needs_size_review`, `needs_bounds_review`, `needs_planned_size_review`, or `waiting_for_import_result`.
- Expert recovery remains possible through `block_on_spatial_fit_review=false`, preserving manual control while keeping the normal generated-asset pipeline guarded.
- This closes another pipeline gap: spatial-fit metadata is now carried from prompt/import review into the actual apply-stage safety gate before Unreal scene mutation.
- Legal-review status remains unchanged: this is Ghost-owned orchestration around Ghost schemas and public editor placement calls, not copied Epic SceneTools behavior.

## Forty-First Implementation Pass

- Added `spatial_prepare_screenshot_decomposition_request` as the explicit front-door for screenshot-driven reconstruction.
- The tool does not claim to run computer vision locally. It produces a strict vision-agent request with:
  - the existing `detected_items_json` schema
  - room dimensions/origin and optional `spatial_analyze_room` context
  - requested props, fixtures, clutter, support surfaces, room zones, architectural fill, clearances, and kitchen/living composition anchors
  - a return-only-JSON vision prompt with crop-box expectations for Tripo image-to-model handoffs
- It emits direct handoffs into `spatial_preflight_screenshot_detections`, `spatial_infer_screenshot_scene_graph`, `spatial_plan_screenshot_reconstruction`, `spatial_prepare_screenshot_crop_manifest`, `spatial_prepare_tripo_generation_batch`, generated-asset binding, fit-gated apply, and placement validation.
- This makes the screenshot-to-worldbuilding workflow less implicit: an agent receiving a screenshot now has a Ghost-owned contract for decomposing the image into individual prop/layout requirements before asset resolution or Tripo spend.
- Legal-review status remains unchanged: this is a Ghost-owned prompt/schema/handoff layer and does not copy Epic native MCP, SceneTools, or vision implementation code.

## Forty-Second Implementation Pass

- Added `spatial_compile_worldbuilding_readiness` as a local/read-only readiness bridge for the full room/screenshot worldbuilding pipeline.
- The tool accepts any subset of Ghost spatial outputs and compiles ordered gates for:
  - live room analysis
  - screenshot decomposition request, detection preflight, and scene graph
  - composition/reconstruction planning
  - project asset resolution and guarded Tripo generation
  - generated-asset binding/spatial-fit review
  - layout preflight and fit-gated composition application
  - placement validation, correction iteration, and viewport evidence
- It reports `blocking_gates`, `next_actions`, evidence handoffs, and a canonical workflow so an agent can resume a partially completed apartment reconstruction without remembering every intermediate tool by hand.
- This improves the north-star workflow from a bag of tools toward an inspectable state machine: Ghost can now say what is measured, what is missing, what is blocked, and what should run next before claiming a composition is ready for human review.
- Source-audit sanity recheck for this pass confirmed the staged UE 5.8 sparse checkout still exposes the native roots under `ModelContextProtocol`, `ToolsetRegistry`, and `Toolsets/MCPClientToolset`, while the referenced `toolset_registry.toolsets.core.scene.SceneTools` implementation remains absent from the audited checkout.
- Legal-review status remains unchanged: this readiness compiler only summarizes Ghost-owned schemas and handoffs. It does not execute Unreal mutation, paid Tripo calls, computer vision, or Epic native SceneTools code.

## Forty-Third Implementation Pass

- Added `spatial_plan_worldbuilding_work_order` as a local/read-only orchestration planner for apartment/interior worldbuilding.
- The tool converts a design brief plus optional reference image, room analysis, screenshot detections, scene graph, and project asset catalog into:
  - a screenshot-first, screenshot-reconstruction, or direct-room-composition lane
  - zone program and prop requirements with approximate size, surface, source, asset placeholder, actor label, and Tripo need
  - project asset reuse strategy before generation
  - guarded Tripo strategy with explicit spend blocking
  - workflow handoffs for room analysis, decomposition, scene graph inference, composition/reconstruction, asset cataloging/resolution, Tripo batch review, binding, layout preflight, fit-gated apply, validation, iteration, viewport evidence, and readiness compilation
- This fills a practical agent gap between "a bag of spatial tools" and "here is the apartment build order." Agents can now start from a high-level brief or screenshot and receive a durable work order rather than assembling the full worldbuilding sequence from memory.
- Legal-review status remains unchanged: this work-order planner only composes Ghost-owned schemas and handoffs. It does not execute Unreal mutation, paid Tripo calls, computer vision, or Epic native SceneTools code.

## Forty-Fourth Implementation Pass

- Added `spatial_preflight_candidate_clearance` as a read-only live-scene preflight before composition mutation.
- The tool builds conservative candidate bounds from Ghost composition placement steps and planned prop sizes, then compares those candidate AABBs against existing live Unreal actor bounds through Ghost's execution substrate.
- It reports candidate statuses such as `clear`, `needs_review`, `blocked_by_candidate_preflight`, and `blocked_by_existing_overlap`, plus existing-overlap details, pairwise candidate overlaps, layout-preflight handoffs, iteration handoffs, and dry-run apply handoffs.
- Existing workflow surfaces now point agents through this gate: layout preflight suggestions, composition batch review, readiness workflow, and worldbuilding work orders all include `spatial_preflight_candidate_clearance` before final apply/validation.
- Legal-review status remains unchanged: this is Ghost-owned bounds math and read-only Unreal Python actor inspection. It is not a physics simulation and does not copy Epic native SceneTools code.

## Intentionally Left Alone

- The C++ Unreal plugin transport and TCP bridge command dispatcher were not rewritten in these passes.
- Existing FastMCP stdio, SSE, and streamable HTTP transports were preserved and are now represented in generated client configs and the runtime protocol contract.
- The direct tool surface remains available by default for compatibility with existing clients and tests.
- Chat HTTP routes, knowledge-base resources, higher-level skills, and project workflows were preserved.
- PCG graph node authoring was not hand-rolled. The current pass creates graph assets/volumes and planning surfaces; full PCG node construction should be implemented through a deeper native bridge after API validation.
- ZoneGraph and MassTraffic-specific city simulation were not claimed as solved. The city skill only scaffolds MassEntity/SmartObject work and flags traffic integration as future work.
- Epic `SceneTools.add_to_scene_from_asset` parity is still not claimed. Ghost now has clean-room live room analysis, surface-aware placement probes, placement validation/evidence planning, placement policy inference, interior composition planning, semantic composition constraints/preflight, screenshot vision-decomposition requests, screenshot scene-graph relationship inference, scene-graph-guided screenshot reconstruction planning, size-aware live project asset cataloging and candidate resolution before Tripo spend, local screenshot crop manifests for Tripo image inputs, guarded Tripo generation batch manifests with spatial-fit prompt/review metadata, generated-asset binding from Tripo import results with spatial-fit review, dry-run-first and spatial-fit-gated composition batch application, spatial worldbuilding work orders/readiness gates, local layout preflight, live actor-bounds candidate clearance preflight, iterative correction planning, screenshot detection preflight/normalization, placement-hint-aware screenshot reconstruction planning with guarded Tripo crop/generation/import handoffs, Content Browser selection handoff/batch placement, spatial selection, and dry-run-first asset placement with best-effort tag/Data Layer support, but richer native scene-tool semantics such as direct snap-on-place placement, true physics-backed collision clearance, automated viewport capture execution, automated vision segmentation, and UE-version-specific Data Layer guarantees remain future work.
- Guarded bridge calls and the Python contribution contract are not a full C++ ToolsetRegistry replacement. They add a safer adapter and explicit contribution contract over Ghost's current Python/TCP architecture; deeper C++ registration/reflection work remains future work.

## Licensing And Redistribution Notes

- Epic's `ModelContextProtocol`, `ToolsetRegistry`, `GASToolsets`, and `MCPClientToolset` plugin source in this release is Unreal Engine source and the official plugin descriptor marks relevant components as `NoRedist`.
- Direct copying of Epic source files, function bodies, schemas generated from proprietary reflection code, comments, or private helper structures into this public repo should be treated as requiring legal review.
- Public protocol method names and standard MCP concepts are safe to implement independently. Epic-specific implementation details should remain reference architecture unless legal review approves reuse.
- Any future Unreal-native module based closely on Epic's implementation should be isolated and reviewed before redistribution.
- If the missing native `toolset_registry.toolsets.core.scene.SceneTools` implementation is later found in another staged checkout, compare behavior at the requirements level only unless counsel approves closer reuse.
- The guarded bridge command adapter is Ghost-owned code over Ghost's bridge registry. Any future adapter that directly embeds Epic ToolsetRegistry execution semantics or Unreal-native module structure should still go through legal review before redistribution.

## Verification

- `python -m py_compile unreal_mcp_server\toolset_registry.py unreal_mcp_server\client_config.py unreal_mcp_server\client_config_tools.py unreal_mcp_server\bridge_descriptors.py unreal_mcp_server\bridge_descriptor_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m py_compile unreal_mcp_server\tools\pcg_tools.py unreal_mcp_server\skills\city_district\skill.py unreal_mcp_server\unreal_mcp_server.py`
- PCG generated Unreal Python snippets parsed with `ast.parse` for support check, graph asset creation, volume creation, and volume refresh.
- `python -m pytest unreal_mcp_server\tests\test_pcg_tools.py unreal_mcp_server\tests\test_city_district_skill.py -q`
- `python -m pytest unreal_mcp_server\tests\test_toolset_registry.py -q`
- `python -m pytest unreal_mcp_server\tests\test_client_config.py -q`
- `python -m pytest unreal_mcp_server\tests\test_bridge_descriptors.py -q`
- `python -m pytest unreal_mcp_server\tests\test_pcg_tools.py unreal_mcp_server\tests\test_city_district_skill.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_bridge_descriptors.py -q` passed with 28 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q`
- `python -m pytest unreal_mcp_server\tests\test_phase7_bridge_command_audit.py -q`
- `git -C C:\Users\NewAdmin\Documents\GDeveloper\External\UnrealEngine-5.8-sparse rev-parse HEAD` returned `7deeb413d3dc1fc034f48d1aacc0861301829d32`
- `rg --files C:\Users\NewAdmin\Documents\GDeveloper\External\UnrealEngine-5.8-sparse\Engine\Plugins\Experimental\ModelContextProtocol`
- `rg --files C:\Users\NewAdmin\Documents\GDeveloper\External\UnrealEngine-5.8-sparse\Engine\Plugins\Experimental\ToolsetRegistry C:\Users\NewAdmin\Documents\GDeveloper\External\UnrealEngine-5.8-sparse\Engine\Plugins\Experimental\Toolsets\MCPClientToolset`
- `python -m py_compile unreal_mcp_server\server_runtime.py unreal_mcp_server\server_runtime_tools.py unreal_mcp_server\toolset_registry.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_server_runtime.py -q` passed with 5 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 8 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_bridge_descriptors.py -q` passed with 17 tests and one existing pytest-cache warning.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py unreal_mcp_server\bridge_descriptors.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 12 tests and one existing pytest-cache warning.
- Full server import smoke after the spatial placement pass:
  - normal mode cataloged `tools.spatial_awareness_tools` with 6 tools, including `spatial_add_asset_to_scene`
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` disabled direct tool exposure while `ToolsetRegistry.call_tool("tools.spatial_awareness_tools.spatial_add_asset_to_scene", dry_run=true)` returned schema `unreal_mcp_ghost.spatial_asset_placement.v1` with `will_execute=false`
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 12 tests and one existing pytest-cache warning after the Data Layer-aware placement extension.
- Full server import smoke after the Data Layer-aware placement extension:
  - direct mode exposed `spatial_add_asset_to_scene` with new input fields `tags`, `data_layer_names`, and `fail_on_missing_data_layer`
  - direct mode cataloged `tools.spatial_awareness_tools` with 6 tools
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`
  - `ToolsetRegistry.call_tool("spatial_add_asset_to_scene", toolset_name="tools.spatial_awareness_tools", dry_run=true, tags=["Gameplay_POI"], data_layer_names=["Gameplay_POIs"])` returned schema `unreal_mcp_ghost.spatial_asset_placement.v1`, preserved tag/Data Layer intent, and reported `will_execute=false`
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 16 tests and one existing pytest-cache warning after the selection-aware spatial workflow extension.
- Full server import smoke after the selection-aware spatial workflow extension:
  - direct mode exposed `spatial_select_actors`
  - direct mode cataloged `tools.spatial_awareness_tools` with 7 tools
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`
  - `ToolsetRegistry.call_tool("spatial_select_actors", toolset_name="tools.spatial_awareness_tools", dry_run=false, allow_mutation=false)` returned schema `unreal_mcp_ghost.spatial_actor_selection.v1`, preserved the mutation gate, and reported `will_execute=false`
  - A dry-run actor-resolution dispatch reached the tool but could not resolve live scene data in the no-Unreal smoke environment; runtime editor validation remains required for matched actor outputs.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 18 tests and one existing pytest-cache warning after the Content Browser selection handoff extension.
- Full server import smoke after the Content Browser selection handoff extension:
  - direct mode exposed `spatial_content_selection_context`
  - direct mode cataloged `tools.spatial_awareness_tools` with 8 tools
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`
  - `ToolsetRegistry.call_tool("spatial_content_selection_context", toolset_name="tools.spatial_awareness_tools", placement_layout="grid", tags=["Gameplay_POI"], data_layer_names=["Gameplay_POIs"])` returned schema `unreal_mcp_ghost.spatial_content_selection.v1` and preserved tag/Data Layer handoff inputs; live selected-asset outputs require a connected Unreal Editor.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 22 tests and one existing pytest-cache warning after the selected-asset batch placement extension.
- Full server import smoke after the selected-asset batch placement extension:
  - direct mode exposed `spatial_place_selected_assets`
  - direct mode cataloged `tools.spatial_awareness_tools` with 9 tools
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`
  - `ToolsetRegistry.call_tool("spatial_place_selected_assets", toolset_name="tools.spatial_awareness_tools", asset_paths=["/Game/Props/SM_Table.SM_Table"], dry_run=false, allow_mutation=false)` returned schema `unreal_mcp_ghost.spatial_selected_asset_placement.v1`, preserved the mutation gate, and reported `will_execute=false`
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 24 tests and one existing pytest-cache warning after the placement policy inference extension.
- Full server import smoke after the placement policy inference extension:
  - direct mode exposed `spatial_infer_placement_policy`
  - direct mode cataloged `tools.spatial_awareness_tools` with 10 tools
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`
  - `ToolsetRegistry.call_tool("spatial_infer_placement_policy", toolset_name="tools.spatial_awareness_tools", asset_paths=["/Game/City/SM_CityBlock_A.SM_CityBlock_A"], intent="city district blockout")` returned schema `unreal_mcp_ghost.spatial_placement_policy.v1`, resolved `city_block`, and selected grid layout.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 26 tests and one existing pytest-cache warning after the surface probe extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 34 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_server_runtime.py unreal_mcp_server\tests\test_client_config.py -q` passed with 26 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_pcg_tools.py unreal_mcp_server\tests\test_city_district_skill.py -q` passed with 11 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention; the new spatial module remains part of this dirty worktree's live registry until the broader native-alignment files are added to source control.
- Full server import smoke after the surface probe extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 11 tools, including `spatial_surface_probe`; the live FastMCP registry contained 700 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`.
  - A patched no-Unreal `ToolsetRegistry.call_tool("spatial_surface_probe", toolset_name="tools.spatial_awareness_tools", arguments={"points": [[0, 0, 100]], "placement_offset": 10})` returned schema `unreal_mcp_ghost.spatial_surface_probe.v1` and preserved the surface-adjusted placement output.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 28 tests and one existing pytest-cache warning after the placement validation extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 36 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_server_runtime.py unreal_mcp_server\tests\test_client_config.py -q` passed with 26 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_pcg_tools.py unreal_mcp_server\tests\test_city_district_skill.py -q` passed with 11 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention; the new spatial module remains part of this dirty worktree's live registry until the broader native-alignment files are added to source control.
- Full server import smoke after the placement validation extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 12 tools, including `spatial_surface_probe` and `spatial_validate_placement`; the live FastMCP registry contained 701 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`.
  - A patched no-Unreal `ToolsetRegistry.call_tool("spatial_validate_placement", toolset_name="tools.spatial_awareness_tools", arguments={"actors": ["POI_Table"], "surface_tolerance": 15, "clearance_padding": 25})` returned schema `unreal_mcp_ghost.spatial_placement_validation.v1` and preserved the validation summary output.
- `python -m py_compile unreal_mcp_server\bridge_descriptors.py unreal_mcp_server\bridge_descriptor_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_bridge_descriptors.py -q` passed with 8 tests and one existing pytest-cache warning.
- Full server import smoke after the guarded bridge-call pass:
  - normal mode cataloged `bridge_descriptor_tools` with 5 tools, including `call_bridge_command`
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` disabled direct tools while `ToolsetRegistry.call_tool("bridge_descriptor_tools.call_bridge_command", dry_run=true)` returned schema `unreal_mcp_ghost.bridge_command_call.v1` with `will_execute=false`
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the sixth pass:
  - direct mode cataloged `server_runtime_tools` under `native_mcp_runtime`
  - direct mode cataloged `server_lifecycle_status`, `server_refresh_metadata`, `server_transport_diagnostics`, `server_list_operations`, `server_operation_status`, and `server_cancel_operation`
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` kept direct tools disabled while still cataloging the runtime toolset for indirect dispatch
  - both direct and tool-search modes cataloged 6 runtime tools under `server_runtime_tools`
- `python -m py_compile unreal_mcp_server\server_runtime.py unreal_mcp_server\server_runtime_tools.py unreal_mcp_server\tests\test_server_runtime.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_server_runtime.py -q` passed with 6 tests and one existing pytest-cache warning after the protocol contract extension.
- `python -m pytest unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 27 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention; the new native-alignment modules remain part of this dirty worktree's live registry until added to source control.
- Full server import smoke after the protocol contract extension:
  - direct mode cataloged `server_runtime_tools` with 7 tools, including `server_protocol_contract`; the live FastMCP registry contained 702 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`.
  - `ToolsetRegistry.call_tool("server_protocol_contract", toolset_name="server_runtime_tools")` returned schema `unreal_mcp_ghost.server_protocol_contract.v1`, active transport `stdio`, and FastMCP delegation notes.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 39 tests and one existing pytest-cache warning after the interior composition planner extension.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 58 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention; the new spatial module remains part of this dirty worktree's live registry until added to source control.
- Full server import smoke after the interior composition planner extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 13 tools, including `spatial_plan_interior_composition`; the live FastMCP registry contained 703 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`.
  - `ToolsetRegistry.call_tool("spatial_plan_interior_composition", toolset_name="tools.spatial_awareness_tools", arguments={"room_type": "apartment", "room_dimensions": [700, 520, 280], "required_props": ["fridge", "stove", "counter clutter"], "screenshot_reference": "C:/refs/apartment.png"})` returned schema `unreal_mcp_ghost.spatial_interior_composition.v1`, 3 planned props, 3 Tripo generation tasks, and `gen_tripo_text_to_model` handoffs with `confirm_spend=false`.
- `python -m py_compile unreal_mcp_server\toolset_registry.py unreal_mcp_server\server_runtime.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_server_runtime.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 15 tests and one existing pytest-cache warning after the tool contribution contract extension.
- `python -m pytest unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 28 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- Full server import smoke after the tool contribution contract extension:
  - direct mode exposed `tool_contribution_contract`; the live FastMCP registry contained 704 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 34 tests and one existing pytest-cache warning after the screenshot reconstruction planner extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 43 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 62 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention; the dirty worktree's native-alignment spatial module remains validated through live registry import smokes.
- Full server import smoke after the screenshot reconstruction planner extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 14 tools, including `spatial_plan_screenshot_reconstruction`; the live FastMCP registry contained 705 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_plan_screenshot_reconstruction", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_screenshot_reconstruction.v1`, `decomposition_required=false`, one `gen_tripo_image_to_model` crop task with `confirm_spend=false`, and asset mappings `tripo_image_to_model` plus `existing_asset`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 36 tests and one existing pytest-cache warning after the room analysis extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 45 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 64 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the room analysis extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 15 tools, including `spatial_analyze_room`; the live FastMCP registry contained 706 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_analyze_room", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_room_analysis.v1`, room dimensions, and planner handoffs for `spatial_plan_interior_composition` and `spatial_surface_probe` with Unreal execution monkeypatched for a no-editor smoke.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 38 tests and one existing pytest-cache warning after the room-analysis ingestion extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 47 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 66 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the room-analysis ingestion extension:
  - direct mode still cataloged `tools.spatial_awareness_tools` with 15 tools and the live FastMCP registry contained 706 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_plan_interior_composition", toolset_name="tools.spatial_awareness_tools", arguments={"room_analysis_json": ...})` returned schema `unreal_mcp_ghost.spatial_interior_composition.v1`, `room_analysis.applied=true`, measured dimensions `[720.0, 540.0, 300.0]`, first workflow tool `spatial_analyze_room`, and the analysis-provided first surface probe point `[10.0, 20.0, 160.0]`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 39 tests and one existing pytest-cache warning after the support-surface placement extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 48 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 67 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the support-surface placement extension:
  - direct mode still cataloged `tools.spatial_awareness_tools` with 15 tools and the live FastMCP registry contained 706 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_plan_interior_composition", toolset_name="tools.spatial_awareness_tools", arguments={"room_analysis_json": ..., "required_props": ["counter clutter", "wall cabinets"]})` returned schema `unreal_mcp_ghost.spatial_interior_composition.v1`; `counter_clutter` used `room_analysis_horizontal_support` with support actor `Counter_A`, and `wall_cabinets` used `room_analysis_wall` with support actor `Kitchen_Wall_A`.
  - `tool_contribution_contract()` returned schema `unreal_mcp_ghost.tool_contribution_contract.v1`, current registry counts, accepted contribution styles, unsupported native gaps, legal-review gates, and preserved Ghost differentiators.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 41 tests and one existing pytest-cache warning after the composition-iteration planner extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 50 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 69 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the composition-iteration planner extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 16 tools, including `spatial_plan_composition_iteration`; the live FastMCP registry contained 707 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_plan_composition_iteration", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_composition_iteration.v1`, `success=true`, `correction_count=2`, and evidence handoffs for `spatial_select_actors`, `focus_viewport`, `viewport_capture_screenshot`, and `viewport_compare_screenshot`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 43 tests and one existing pytest-cache warning after the generated-asset binding extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 52 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 71 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the generated-asset binding extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 17 tools, including `spatial_bind_generated_assets_to_composition`; the live FastMCP registry contained 708 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_bind_generated_assets_to_composition", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_composition_asset_binding.v1`, `success=true`, `resolved_count=1`, a bound `/Game/Generated/SpatialInteriors/SM_CounterClutter.SM_CounterClutter` asset path, and a `spatial_validate_placement` handoff.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 45 tests and one existing pytest-cache warning after the layout preflight extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 54 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 73 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the layout preflight extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 18 tools, including `spatial_preflight_interior_layout`; the live FastMCP registry contained 709 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_preflight_interior_layout", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_layout_preflight.v1`, `success=true`, status `blocked_by_preflight`, issue kinds including `footprint_overlap`, `central_circulation_risk`, and `outside_declared_zone`, plus a `spatial_validate_placement` handoff.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 45 tests and one existing pytest-cache warning after the screenshot placement-hint extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 54 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 73 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the screenshot placement-hint extension:
  - direct mode still cataloged `tools.spatial_awareness_tools` with 18 tools and the live FastMCP registry contained 709 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_plan_screenshot_reconstruction", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_screenshot_reconstruction.v1`, `success=true`, refrigerator placement source `placement_hint_left_wall_kitchen_wall` at `[-308.56, -233.376, 0.0]`, and books placement source `placement_hint_anchor_coffee_table` at `[-35.0, 10.4, 47.0]`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 47 tests and one existing pytest-cache warning after the screenshot detection preflight extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 56 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 75 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the screenshot detection preflight extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 19 tools, including `spatial_preflight_screenshot_detections`; the live FastMCP registry contained 710 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_preflight_screenshot_detections", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_screenshot_decomposition_preflight.v1`, `success=true`, status `blocked_by_decomposition`, refrigerator hint `against the left kitchen wall`, books hint `on the coffee table`, and issue kinds `crop_box_out_of_bounds` plus `low_confidence`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 49 tests and one existing pytest-cache warning after the Tripo generation batch extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 58 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 77 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the Tripo generation batch extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 20 tools, including `spatial_prepare_tripo_generation_batch`; the live FastMCP registry contained 711 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_prepare_tripo_generation_batch", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_tripo_generation_batch.v1`, `success=true`, status `needs_user_spend_confirmation`, one image-to-model job, `confirm_spend=false`, content path `/Game/Generated/ApartmentProps`, and a `spatial_bind_generated_assets_to_composition` post-import handoff.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 51 tests and one existing pytest-cache warning after the screenshot crop manifest extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 60 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 79 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the screenshot crop manifest extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 21 tools, including `spatial_prepare_screenshot_crop_manifest`; the live FastMCP registry contained 712 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - A registry smoke created a temporary local screenshot, called `spatial_plan_screenshot_reconstruction`, then `spatial_prepare_screenshot_crop_manifest`, and then `spatial_prepare_tripo_generation_batch`; it returned schema `unreal_mcp_ghost.spatial_screenshot_crop_manifest.v1`, status `ready_for_tripo_image_to_model`, `crop_count=1`, confirmed the PNG existed on disk, and verified the generation batch used that crop path with `confirm_spend=false`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 54 tests and one existing pytest-cache warning after the composition batch application extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 63 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 82 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the composition batch application extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 22 tools, including `spatial_apply_composition_plan`; the live FastMCP registry contained 713 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_apply_composition_plan", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_composition_placement_batch.v1`, status `blocked_by_unresolved_assets`, one executable placement, one unresolved generated-asset placeholder, merged tags `Kitchen` plus `Interior`, `will_execute=false`, and a `spatial_validate_placement` handoff.
- Full server import smoke:
  - normal mode exposed 682 FastMCP tools, including native-alignment toolset, client-config, bridge-descriptor, PCG, and city/district tools
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, and `list_toolsets`
  - both modes cataloged Ghost toolsets for indirect dispatch
  - JSON-filtered `list_toolsets(category="native_mcp_client_config")` returned the `client_config_tools` descriptor
  - `describe_toolset("client_config_tools")` returned schema `unreal_mcp_ghost.toolset_descriptor.v1`
  - tool-search-mode `call_tool` successfully dispatched `client_config_tools.generate_client_config` with `dry_run=true`
  - real bridge descriptor summary reported 381 bridge commands from `knowledge_base/Reports/bridge_command_registry.json`
  - tool-search-mode `call_tool` successfully dispatched `bridge_descriptor_tools.search_bridge_commands`
  - direct mode cataloged `tools.pcg_tools` under `pcg_world_generation` and `skills.city_district.skill` under `skill`
  - tool-search-mode `call_tool` successfully dispatched `skills.city_district.skill.skill_generate_city_district` and returned schema `unreal_mcp_ghost.city_district_plan.v1`
- Client config smoke:
  - generated all 5 supported config files in a temporary directory for `streamable-http`
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 56 tests and one existing pytest-cache warning after the screenshot scene-graph relationship inference extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 65 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 84 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the screenshot scene-graph relationship inference extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 23 tools, including `spatial_infer_screenshot_scene_graph`; the live FastMCP registry contained 714 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - `ToolsetRegistry.call_tool("spatial_infer_screenshot_scene_graph", toolset_name="tools.spatial_awareness_tools", arguments={...})` returned schema `unreal_mcp_ghost.spatial_screenshot_scene_graph.v1`, status `ready_for_reconstruction`, `node_count=5`, `relation_count=26`, support relations for `books -> coffee_table` and `counter_clutter -> kitchen_counter_run`, plus a `spatial_plan_screenshot_reconstruction` handoff.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 57 tests and one existing pytest-cache warning after the scene-graph-guided reconstruction extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 66 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 85 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the scene-graph-guided reconstruction extension:
  - direct mode still cataloged `tools.spatial_awareness_tools` with 23 tools and the live FastMCP registry contained 714 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_infer_screenshot_scene_graph`, passed its outputs into `spatial_plan_screenshot_reconstruction(scene_graph_json=...)`, and returned schema `unreal_mcp_ghost.spatial_screenshot_reconstruction.v1`, `scene_graph.applied=true`, `detected_item_count=5`, `relation_count=26`, `books` as an existing asset with `placement_hint_anchor_coffee_table`, and `counter_clutter` with placement hint `on the counter; on the kitchen counter run` plus `placement_hint_anchor_counter`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 59 tests and one existing pytest-cache warning after the project asset resolution extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 68 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 87 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the project asset resolution extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 24 tools, including `spatial_resolve_project_assets`; the live FastMCP registry contained 715 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_plan_screenshot_reconstruction`, then `spatial_resolve_project_assets` with a project asset catalog; it returned schema `unreal_mcp_ghost.spatial_project_asset_resolution.v1`, status `ready_for_binding`, `resolved_count=3`, `unresolved_count=1`, override keys `books`, `counter_clutter`, and `refrigerator`, plus a binding handoff and a Tripo handoff placeholder for the post-binding output.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 61 tests and one existing pytest-cache warning after the live project asset catalog extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 70 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 89 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the live project asset catalog extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 25 tools, including `spatial_catalog_project_assets`; the live FastMCP registry contained 716 direct tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch repeated the screenshot reconstruction plus project-asset resolution path and returned schema `unreal_mcp_ghost.spatial_project_asset_resolution.v1`, status `ready_for_binding`, `resolved_count=3`, `unresolved_count=1`, and override keys `books`, `counter_clutter`, and `refrigerator`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 62 tests and one existing pytest-cache warning after the size-aware project asset resolution extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 71 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 90 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the size-aware project asset resolution extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 25 tools, including `spatial_catalog_project_assets` and `spatial_resolve_project_assets`; the live FastMCP registry contained 716 direct tools and the ToolsetRegistry catalog contained 713 tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_plan_screenshot_reconstruction`, then `spatial_resolve_project_assets` with two refrigerator candidates; it returned schema `unreal_mcp_ghost.spatial_project_asset_resolution.v1`, status `ready_for_binding`, selected `/Game/Props/Kitchen/SM_RefrigeratorFull.SM_RefrigeratorFull` over `/Game/Props/Kitchen/SM_RefrigeratorMini.SM_RefrigeratorMini`, carried selected candidate size `[92.0, 82.0, 188.0]`, emitted `size_close_match` for the selected full-size fridge, and emitted `size_loose_mismatch` for the mini-fridge candidate.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 64 tests and one existing pytest-cache warning after the semantic composition constraint extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 73 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 92 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the semantic composition constraint extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 25 tools, including `spatial_plan_interior_composition` and `spatial_preflight_interior_layout`; the live FastMCP registry contained 716 direct tools and the ToolsetRegistry catalog contained 713 tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_plan_interior_composition` for a kitchen containing fridge, stove, sink, counter run, bar stool, and counter clutter; the plan emitted semantic constraint kinds `circulation_clearance`, `counter_adjacency`, `kitchen_work_triangle`, and `support_contact`.
  - Registry dispatch then called `spatial_preflight_interior_layout` on a counter/stool layout with excessive separation; it returned status `needs_review`, semantic constraints `circulation_clearance` and `counter_adjacency`, and issue kind `semantic_counter_adjacency_gap`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 64 tests and one existing pytest-cache warning after the Tripo spatial-fit prompt/review extension.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 73 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 92 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the Tripo spatial-fit prompt/review extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 25 tools, including `spatial_prepare_tripo_generation_batch`; the live FastMCP registry contained 716 direct tools and the ToolsetRegistry catalog contained 713 tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_plan_interior_composition`, then `spatial_prepare_tripo_generation_batch` for a kitchen prop set; the batch returned status `needs_user_spend_confirmation`, `confirm_spend=false`, `text_to_model` mode, a job-level `spatial_fit` packet with surface `floor`, a text prompt containing `spatial fit`, and a `review_spatial_fit` workflow step.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 64 tests and one existing pytest-cache warning after the generated-asset spatial-fit binding review extension.
  - Focused coverage verifies both Tripo import bounds review and project-catalog `asset_overrides_json` bounds review before dry-run placement.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 73 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 92 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the generated-asset spatial-fit binding review extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 25 tools, including `spatial_bind_generated_assets_to_composition`; the live FastMCP registry contained 716 direct tools and the ToolsetRegistry catalog contained 713 tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_bind_generated_assets_to_composition` with a Tripo import result carrying bounds; it returned schema `unreal_mcp_ghost.spatial_composition_asset_binding.v1`, status `ready_for_dry_run_placement`, `spatial_fit_review_count=1`, review status `ready_for_spatial_validation`, size reason `size_close_match`, and a `review_spatial_fit` workflow step.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 65 tests and one existing pytest-cache warning after the spatial-fit-gated composition apply extension.
  - Focused coverage verifies dry-run review reporting, default mutation blocking, and explicit `block_on_spatial_fit_review=false` bypass behavior.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 74 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 93 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the spatial-fit-gated composition apply extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 25 tools, including `spatial_apply_composition_plan`; the live FastMCP registry contained 716 direct tools and the ToolsetRegistry catalog contained 713 tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_apply_composition_plan` with a generated-asset binding output carrying `needs_size_review`; it returned schema `unreal_mcp_ghost.spatial_composition_placement_batch.v1`, status `blocked_by_spatial_fit_review`, `spatial_fit_review_count=1`, `spatial_fit_blocker_count=1`, queue review status `needs_size_review`, and a `review_spatial_fit` workflow step.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 67 tests and one existing pytest-cache warning after the screenshot decomposition request extension.
  - Focused coverage verifies the vision-agent JSON contract, crop-box expectations, room-analysis handoff, reconstruction handoffs, and input validation.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 76 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 95 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the screenshot decomposition request extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 26 tools, including `spatial_prepare_screenshot_decomposition_request`; the live FastMCP registry contained 717 direct tools and the ToolsetRegistry catalog contained 714 tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_prepare_screenshot_decomposition_request`; it returned schema `unreal_mcp_ghost.spatial_screenshot_decomposition_request.v1`, status `ready_for_vision_decomposition`, a prompt containing `Return only JSON`, handoffs into screenshot detection preflight, scene graph inference, and screenshot reconstruction, plus a workflow that includes `spatial_prepare_tripo_generation_batch`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 69 tests and one existing pytest-cache warning after the spatial worldbuilding readiness bridge extension.
  - Focused coverage verifies blocked readiness from only a reference screenshot and complete-pipeline readiness when room analysis, screenshot decomposition, scene graph, asset binding, fit-gated apply, placement validation, and viewport evidence are supplied.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 78 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 97 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the spatial worldbuilding readiness bridge extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 27 tools, including `spatial_compile_worldbuilding_readiness`; the live FastMCP registry contained 718 direct tools and the ToolsetRegistry catalog contained 715 tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_compile_worldbuilding_readiness` with only `reference_image="C:/refs/apartment.png"`; it returned schema `unreal_mcp_ghost.spatial_worldbuilding_readiness.v1`, status `blocked`, blocking gates for room analysis, screenshot decomposition/preflight/scene graph, composition planning, asset binding, fit-gated apply, placement validation, and viewport evidence, plus next actions starting with `spatial_analyze_room`, `spatial_prepare_screenshot_decomposition_request`, `spatial_preflight_screenshot_detections`, `spatial_infer_screenshot_scene_graph`, `spatial_plan_screenshot_reconstruction`, and `spatial_resolve_project_assets`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 71 tests and one existing pytest-cache warning after the spatial worldbuilding work-order extension.
  - Focused coverage verifies screenshot-first work-order planning and direct kitchen composition that resolves project assets before leaving unresolved props for guarded Tripo review.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 80 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 99 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the spatial worldbuilding work-order extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 28 tools, including `spatial_plan_worldbuilding_work_order`; the live FastMCP registry contained 719 direct tools and the ToolsetRegistry catalog contained 716 tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch called `spatial_plan_worldbuilding_work_order` with only a reference image, room dimensions, requested kitchen/living zones, and a brief; it returned schema `unreal_mcp_ghost.spatial_worldbuilding_work_order.v1`, status `needs_screenshot_decomposition`, source mode `screenshot_first`, and workflow steps starting with `measure_space`, `decompose_reference`, `preflight_and_graph_reference`, `plan_composition`, and `catalog_project_assets`.
- `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 73 tests and one existing pytest-cache warning after the live actor-bounds candidate clearance preflight extension.
  - Focused coverage verifies `spatial_preflight_candidate_clearance` registration, conservative candidate-bound code generation, schema propagation, and input validation before bridge execution.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 82 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
- `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 101 tests and one existing pytest-cache warning.
- `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
- Full server import smoke after the live actor-bounds candidate clearance preflight extension:
  - direct mode cataloged `tools.spatial_awareness_tools` with 29 tools, including `spatial_preflight_candidate_clearance`; the live FastMCP registry contained 720 direct tools and the ToolsetRegistry catalog contained 717 tools in this dirty worktree.
  - `UNREAL_MCP_TOOL_SEARCH_MODE=1` exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`.
  - Registry dispatch reached `spatial_preflight_candidate_clearance` with a one-prop refrigerator composition, returned the schema `unreal_mcp_ghost.spatial_candidate_clearance.v1`, and showed `candidate_count=1` in inputs. Because this smoke ran without a connected Unreal Editor, it correctly returned `success=false` with `error="Not connected to Unreal Engine"`; live overlap evidence still requires an editor session.

## Forty-Fifth Implementation Pass - Generated-Asset Scale Correction

- Added `spatial_plan_asset_scale_corrections` as a local/read-only planner between generated-asset binding and dry-run placement.
- The tool consumes interior compositions, screenshot reconstruction plans, generated-asset binding outputs, and scale-correction outputs through Ghost's composition-like parser.
- It compares planned prop dimensions against imported/cataloged bounds, prefers uniform scale, supports explicit non-uniform scale opt-in, and blocks assets that require distorted scale or regeneration.
- Scale-corrected reviews use status `ready_for_scaled_spatial_validation`, which the batch apply gate treats as ready while preserving the original raw size evidence in the correction record.
- Binding, Tripo batch, composition apply, readiness, and work-order workflows now surface `spatial_plan_asset_scale_corrections` before layout preflight, live candidate clearance, mutation, and validation.
- Work-order quality gates now include `generated_asset_scale_correction_before_mutation`.
- Legal posture: this pass uses clean-room dimensional arithmetic over Ghost-owned spatial-fit review records. It does not copy Epic native MCP/SceneTools source; direct reuse of staged Epic implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 75 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 84 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 103 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Live direct import smoke reported `direct_tool_count=721`, `registry_tool_count=718`, `spatial_tool_count=30`, and `spatial_plan_asset_scale_corrections` present in both direct and registry catalogs.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; the registry still cataloged 718 tools and the 30-tool spatial toolset.
  - Full-server registry dispatch called `spatial_plan_asset_scale_corrections` on a generated fridge binding and returned schema `unreal_mcp_ghost.spatial_asset_scale_correction.v1`, status `ready_for_scaled_dry_run`, recommended scale `[0.5, 0.5, 0.5]`, and `apply_handoff.enabled=true`.
  - `git diff --check -- README.md unreal_mcp_server\tool_inventory_categories.json unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py knowledge_base\Reports\epic_ue58_mcp_source_audit.md` passed for touched files with only existing LF-to-CRLF warnings on tracked text files.

## Forty-Sixth Implementation Pass - Support-Surface Anchoring

- Added `spatial_plan_support_surface_anchors` as a local/read-only planner between scale correction/binding and layout preflight.
- The tool consumes interior compositions, screenshot reconstruction plans, generated-asset binding outputs, scale-correction outputs, and support-anchor outputs through Ghost's composition-like parser.
- It reuses Ghost's room-analysis surface classifications to update dry-run placement steps for floor, counter, table, shelf, cabinet, and wall contact.
- Anchored steps receive revised location/rotation, `support_actor`, `support_roles`, `placement_source`, and a `support_surface_anchor` review record while preserving `dry_run=true` and `allow_mutation=false`.
- The planner emits `spatial_surface_probe`, layout preflight, live candidate clearance, dry-run apply, and validation handoffs, and blocks when a required counter/table/shelf/wall support is missing from room analysis.
- Binding, Tripo batch, scale-correction, composition apply, readiness, and work-order workflows now surface `spatial_plan_support_surface_anchors` before layout preflight, candidate clearance, mutation, and validation.
- Work-order quality gates now include `support_surface_anchoring_before_layout_preflight`.
- Legal posture: this pass reuses Ghost-owned room-analysis metadata and placement schemas. It does not copy Epic native MCP/SceneTools source; direct reuse of staged Epic implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 77 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 86 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 105 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Live direct import smoke reported `direct_tool_count=722`, `registry_tool_count=719`, `spatial_tool_count=31`, and `spatial_plan_support_surface_anchors` present in both direct and registry catalogs.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; the registry still cataloged 719 tools and the 31-tool spatial toolset.
  - Full-server registry dispatch called `spatial_plan_support_surface_anchors` with a counter-clutter composition and room-analysis support surfaces; it returned schema `unreal_mcp_ghost.spatial_support_surface_anchor.v1`, status `ready_for_support_surface_review`, `anchored_count=1`, support actor `Counter_A`, anchored location `[10.0, 20.0, 97.0]`, and `apply_handoff.enabled=true`.
  - `git diff --check -- README.md unreal_mcp_server\tool_inventory_categories.json unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py knowledge_base\Reports\epic_ue58_mcp_source_audit.md` passed for touched files with only existing LF-to-CRLF warnings on tracked text files.

## Forty-Seventh Implementation Pass - Layout Preflight Correction Planning

- Added `spatial_plan_layout_preflight_corrections` as a local/read-only planner between layout preflight and live candidate clearance.
- The tool consumes an interior composition plus `spatial_preflight_interior_layout` output, then produces a corrected dry-run composition artifact with schema `unreal_mcp_ghost.spatial_layout_preflight_correction.v1`.
- It deterministically clamps fixable room-bound violations, nudges overlapping footprints apart, moves floor props away from the conservative central circulation band, and routes support/semantic issues to `spatial_plan_support_surface_anchors`, `spatial_surface_probe`, or `spatial_plan_composition_iteration` instead of silently guessing.
- Corrected steps preserve `dry_run=true` and `allow_mutation=false`, carry `layout_preflight_corrections` metadata, and round-trip through `spatial_apply_composition_plan` through Ghost's composition-like parser.
- Layout preflight, generated asset binding, Tripo batch, composition apply, readiness, and work-order workflows now surface `spatial_plan_layout_preflight_corrections` before live candidate clearance, mutation, and validation.
- Work-order/readiness quality gates now include `layout_preflight_correction_before_mutation_when_preflight_blocks`.
- Legal posture: this pass uses Ghost-owned approximate geometry records and deterministic transform arithmetic. It does not copy Epic native MCP/SceneTools source; direct reuse of staged Epic implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 79 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 88 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 107 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Live direct import smoke reported `direct_tool_count=723`, `registry_tool_count=720`, `spatial_tool_count=32`, and `spatial_plan_layout_preflight_corrections` present in both direct and registry catalogs.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; the registry still cataloged 720 tools and the 32-tool spatial toolset.
  - Tool-search registry dispatch called `spatial_plan_layout_preflight_corrections` on an out-of-bounds refrigerator layout preflight and returned schema `unreal_mcp_ghost.spatial_layout_preflight_correction.v1`, status `ready_for_corrected_preflight`, and `apply_handoff.enabled=true`.

## Forty-Eighth Implementation Pass - Functional Zone Inference

- Added `spatial_infer_functional_zones` as a local/read-only planner between live room analysis, screenshot decomposition, and interior composition.
- The tool consumes room analysis, detected screenshot items, and existing composition hints, then infers functional kitchen, living, sleeping, entry, utility, work, storage, bath, dining, and circulation zones with confidence, evidence, surface priorities, and recommended props.
- Room-analysis handoffs now route through functional zone inference before surface probing or composition, so apartment-scale workflows can reason about usable zones instead of only raw room bounds.
- `spatial_plan_interior_composition` now accepts `functional_zone_plan_json`, preserves inferred zone geometry, and disables the redundant inference workflow step when a zone plan has already been provided.
- Spatial worldbuilding readiness and work-order planning now include a functional-zone gate and pass inferred zones into direct composition or screenshot reconstruction planning before asset resolution, Tripo review, layout preflight, candidate clearance, mutation, and validation.
- The README and tracked tool inventory advertise functional zone inference as part of Ghost's spatial worldbuilding surface.
- Legal posture: this pass uses clean-room heuristics over Ghost-owned room-analysis, screenshot-detection, and composition records. It does not copy Epic native MCP/SceneTools source; direct reuse of staged Epic implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 82 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 91 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 110 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Live direct import smoke reported `direct_tool_count=724`, `registry_tool_count=721`, `spatial_tool_count=33`, and `spatial_infer_functional_zones` present in both direct and registry catalogs.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; the registry still cataloged 721 tools and the 33-tool spatial toolset.
  - Tool-search registry dispatch called `spatial_infer_functional_zones` on apartment room-analysis plus detected fridge/sofa hints and returned schema `unreal_mcp_ghost.spatial_functional_zone_inference.v1`, status `ready_for_composition`, and zones `kitchen`, `living`, and `entry`.

## Forty-Ninth Implementation Pass - Interior Prop Program Planning

- Added `spatial_plan_interior_prop_program` as a local/read-only planner between functional zone inference and composition.
- The tool turns room analysis, functional zones, screenshot detections, required props, known project assets, and architectural-fill policy into a per-zone prop program for fixtures, furniture, clutter, appliances, and fill pieces.
- Prop programs include per-zone density, category/surface counts, planned props, missing-asset counts, existing asset matches, guarded Tripo prompt seeds, and handoffs into composition and asset resolution.
- `spatial_plan_interior_composition` now accepts `prop_program_json` and honors the exact program prop list when supplied, while preserving the prior heuristic selection path when no program is provided.
- Spatial worldbuilding work orders now build a prop program before direct room composition, so a compact kitchen brief can expand from fridge/stove/clutter into counters, sink, cabinets, backsplash/fill, and other missing composition pieces before asset resolution.
- Tightened project-asset candidate scoring so generic room/context tokens and size compatibility cannot resolve unrelated assets without a meaningful name/alias identity match. This prevents a sparse kitchen catalog from using a fridge or stove asset for counters, sinks, cabinets, or architectural fill.
- README and tracked tool inventory now advertise zone-aware interior prop programming as part of Ghost's spatial worldbuilding surface.
- Legal posture: this pass uses Ghost-owned prop libraries, zone records, and asset-catalog heuristics. It does not copy Epic native MCP/SceneTools source; direct reuse of staged Epic implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 84 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 93 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 112 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Live direct import smoke reported `direct_tool_count=725`, `registry_tool_count=722`, `spatial_tool_count=34`, and `spatial_plan_interior_prop_program` present in both direct and registry catalogs.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; the registry still cataloged 722 tools and the 34-tool spatial toolset.
  - Tool-search registry dispatch called `spatial_plan_interior_prop_program` on apartment kitchen/living functional zones and returned schema `unreal_mcp_ghost.spatial_interior_prop_program.v1`, status `ready_for_composition`, `prop_count=9`, `generation_candidate_count=9`, and `architectural_fill_count=2`.

## Fiftieth Implementation Pass - Prop Program Readiness Gate

- `spatial_compile_worldbuilding_readiness` now accepts `prop_program_json` and records `prop_program_applied` in the normalized input evidence.
- Readiness now includes an explicit `interior_prop_program` gate between `functional_zone_inference` and `composition_plan`.
- Once functional zones are available, missing prop-program evidence is blocking and routes the agent to `spatial_plan_interior_prop_program` before composition, project-asset resolution, or guarded Tripo generation.
- Existing composition or screenshot reconstruction evidence can satisfy the gate as `satisfied_by_composition`, preserving compatibility with already-compiled downstream plans.
- Direct-room composition next actions now include a `prop_program_json` handoff placeholder, and `spatial_plan_worldbuilding_work_order` passes its generated prop program into readiness previews and compile-readiness handoffs.
- Legal posture: this pass is Ghost-owned workflow gating over Ghost spatial schemas and handoffs. It does not copy Epic native MCP/SceneTools source; direct reuse of staged Epic implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 85 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 94 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 113 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Live direct import smoke reported `direct_tool_count=725`, `registry_tool_count=722`, `spatial_tool_count=34`, and both `spatial_compile_worldbuilding_readiness` and `spatial_plan_interior_prop_program` present in the spatial toolset.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; registry dispatch called `spatial_compile_worldbuilding_readiness` with room analysis plus functional zones but no prop program, returning schema `unreal_mcp_ghost.spatial_worldbuilding_readiness.v1`, status `blocked`, `interior_prop_program.ready=false`, `interior_prop_program.blocking=true`, and next tool `spatial_plan_interior_prop_program`.

## Fifty-First Implementation Pass - Screenshot Detected-Prop Programming

- `spatial_plan_screenshot_reconstruction` now infers functional zones from detected reference items before composition.
- Screenshot reconstruction now builds an explicit `spatial_plan_interior_prop_program` artifact from detected props, existing asset hints, optional required props, optional architectural fill, and optional zone recommendations.
- The default screenshot path keeps `include_zone_recommendations=false` so reference rebuilds stay faithful to the segmented image; callers can opt into broader zone-complete prop programs when desired.
- The screenshot composition plan now receives both the inferred functional zone plan and detected-prop program, so `composition_plan.functional_zone_inference.applied=true` and `composition_plan.prop_program.applied=true` for supplied detections.
- Screenshot work orders now adopt the reconstruction's own functional zone plan and prop program, keeping work-order readiness/output aligned with the composition that will feed asset resolution, guarded Tripo crop/text generation, import, placement, and validation.
- README and tracked tool inventory now advertise screenshot-driven detected-prop programming.
- Legal posture: this pass is clean-room Ghost workflow plumbing over Ghost screenshot-detection, zone, prop-program, and composition schemas. It does not perform computer vision, mutate Unreal, submit paid Tripo jobs, or copy Epic native MCP/SceneTools source; direct reuse of staged Epic implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 86 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 95 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 114 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Live direct import smoke reported `direct_tool_count=725`, `registry_tool_count=722`, `spatial_tool_count=34`, and `spatial_plan_screenshot_reconstruction` present in the spatial toolset.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; registry dispatch called `spatial_plan_screenshot_reconstruction` with detected refrigerator/books items and returned schema `unreal_mcp_ghost.spatial_screenshot_reconstruction.v1`, `decomposition_required=false`, prop-program schema `unreal_mcp_ghost.spatial_interior_prop_program.v1`, `prop_count=2`, `detected_prop_count=2`, `zone_recommendations_applied=false`, and `composition_plan.prop_program.applied=true`.

## Fifty-Second Implementation Pass - Guarded Tripo Asset Lifecycle

- `spatial_prepare_tripo_generation_batch` now attaches a `guarded_pipeline` checklist to every generated-asset job.
- Each job's lifecycle explicitly routes through prompt review, user spend confirmation, Tripo submission, wait/result retrieval, Unreal import, composition binding, spatial-fit review, support-surface anchoring, layout preflight, dry-run placement, placement validation, and viewport evidence capture.
- Batch outputs now include `guarded_pipeline_summary` with spend-confirmation status, crop-review blockers, spend blockers, ready-job counts, and the required lifecycle sequence.
- The existing raw `submit`, `wait`, `import`, binding, scale-correction, support-anchor, placement, and validation handoffs are preserved for broad client compatibility while giving higher-level agents a single ordered generated-asset runbook.
- README and tracked tool inventory now describe guarded Tripo batches as carrying per-job prompt/spend/import/placement/validation lifecycle metadata.
- Legal posture: this pass is clean-room Ghost orchestration over Ghost composition and Tripo handoff schemas. It does not submit paid jobs, mutate Unreal, import assets, or copy Epic native MCP/SceneTools source; direct reuse of staged Epic implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 86 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py -q` passed with 95 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 114 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Live direct import smoke reported `direct_tool_count=725`, `registry_tool_count=722`, `spatial_tool_count=34`, and `spatial_prepare_tripo_generation_batch` present in the spatial toolset.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; registry dispatch called `spatial_prepare_tripo_generation_batch` on a one-prop refrigerator composition and returned schema `unreal_mcp_ghost.spatial_tripo_generation_batch.v1`, status `needs_user_spend_confirmation`, `job_count=1`, `guarded_pipeline_summary.spend_confirmation_required=true`, `submit_tripo_generation.status=blocked_by_spend_confirmation`, validation tool `spatial_validate_placement`, and lifecycle tail `dry_run_place_generated_asset`, `validate_generated_asset_placement`, `capture_viewport_evidence`.

## Fifty-Third Implementation Pass - Interior Interaction Clearance Preflight

- Extended `spatial_preflight_interior_layout` with per-prop interaction clearance profiles for appliance door swing, appliance work zones, counter/sink work clearance, seating pullback, and storage access.
- Actor checks now carry an `interaction_clearance` record with required clearance, available room margin, status, severity, and review reason. Top-level layout preflight output also includes `interaction_clearance` and `interaction_clearance_count` for agent-readable summary handling.
- Tight profiles now emit `interaction_clearance_tight` issues before mutation, with actor label, clearance kind, available/required clearance, and room-margin evidence. This complements room bounds, approximate footprint overlap, central circulation, semantic constraints, and live candidate-clearance checks.
- README and tracked tool inventory now describe per-prop interaction clearance as part of Ghost's spatial worldbuilding preflight surface.
- Legal posture: this pass uses clean-room Ghost approximate geometry and prop-category heuristics. It does not copy Epic native MCP, ToolsetRegistry, or SceneTools source; any future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 115 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Live direct import smoke reported `direct_tool_count=725`, `registry_tool_count=722`, `spatial_tool_count=34`, and `spatial_preflight_interior_layout` present in the spatial toolset.
  - Direct registry dispatch called `spatial_preflight_interior_layout` on a compact refrigerator layout and returned schema `unreal_mcp_ghost.spatial_layout_preflight.v1`, status `needs_review`, `interaction_clearance_count=1`, clearance kind `appliance_door_swing`, clearance status `tight_review`, and issue kinds including `interaction_clearance_tight`.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; the registry still cataloged 722 tools and the 34-tool spatial toolset, and indirect dispatch returned the same `interaction_clearance_tight` preflight evidence.

## Fifty-Fourth Implementation Pass - Front-Facing Interaction Clearance

- Refined `spatial_preflight_interior_layout` so interaction clearance is evaluated in the prop's facing/approach direction instead of passing when any room-side margin is large.
- The preflight now derives clearance orientation from explicit placement rotation yaw first, then declared/inferred zone wall, then a fallback largest-margin mode when orientation evidence is unavailable.
- Interaction clearance records now include `front_available_cm`, `max_available_cm`, `front_margin_key`, `facing_direction`, `orientation_source`, and optional yaw/wall evidence while preserving `available_cm` for existing clients.
- This catches apartment-layout cases where a refrigerator, oven, counter, sink, seat, or storage item has plenty of lateral room but not enough door-swing, work-zone, or pullback clearance on the side a user actually approaches.
- README and tracked tool inventory now describe this as front-facing interaction clearance.
- Legal posture: this pass is a clean-room refinement over Ghost's own rotation, zone-wall, and approximate-footprint records. It does not copy Epic native MCP, ToolsetRegistry, or SceneTools source; future direct use of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 88 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 116 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct registry dispatch called `spatial_preflight_interior_layout` on a refrigerator with 15 cm of facing clearance and 455 cm of other margin; it returned schema `unreal_mcp_ghost.spatial_layout_preflight.v1`, status `needs_review`, `front_margin_key=back`, `facing_direction=positive_y`, `orientation_source=rotation_yaw`, and issue kind `interaction_clearance_tight`.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; the registry still cataloged 722 tools and the 34-tool spatial toolset, and indirect dispatch returned the same front-facing clearance evidence.

## Fifty-Fifth Implementation Pass - Opening and Egress Clearance Preflight

- Extended `spatial_preflight_interior_layout` to consume room-analysis `classified_surfaces.openings` plus optional composition/room `openings` records.
- The preflight now builds conservative protected footprints around door/opening surfaces, using the opening span axis, approach depth from `min_walkway_width`, and room-bound clamping.
- Planned actor footprints that overlap protected opening clearance now emit `opening_clearance_blocked` issues. Floor-level blockers are errors that block preflight; non-floor overlaps are warnings. Door-casing/trim style architectural fill is exempted so trim can be planned around openings.
- Layout preflight output now includes `opening_clearance`, `opening_clearance_count`, and `blocked_opening_count`, and correction planning routes blocked openings to `spatial_plan_composition_iteration`.
- README and tracked tool inventory now advertise opening/egress clearance as part of Ghost's spatial worldbuilding preflight surface.
- Legal posture: this pass is clean-room approximate geometry over Ghost room-analysis and composition schemas. It does not copy Epic native MCP, ToolsetRegistry, or SceneTools source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 89 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 117 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct registry dispatch called `spatial_preflight_interior_layout` on an entry-console layout with a room-analysis `Apartment_Entry_Door`; it returned schema `unreal_mcp_ghost.spatial_layout_preflight.v1`, status `blocked_by_preflight`, `opening_clearance_count=1`, `blocked_opening_count=1`, and issue kind `opening_clearance_blocked`.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; the registry still cataloged 722 tools and the 34-tool spatial toolset, and indirect dispatch returned the same blocked-opening clearance evidence.

## Fifty-Sixth Implementation Pass - Entry-to-Anchor Visual Sightlines

- Extended `spatial_preflight_interior_layout` with a visual-composition review that derives entry/view starts from protected openings and chooses major per-zone anchors such as sofas, beds, counters, islands, refrigerators, sinks, and rugs.
- The preflight now evaluates conservative entry-to-anchor sightline corridors and emits `visual_sightline_obstructed` warnings when tall floor props interrupt the read from an opening to a key room anchor.
- Layout preflight output now includes `visual_sightlines`, `visual_sightline_count`, and `obstructed_sightline_count`, with blockers attached back to the responsible actor checks.
- Correction planning routes sightline obstructions to `spatial_plan_composition_iteration`, keeping this as composition review rather than a blind local transform nudge.
- README and tracked tool inventory now advertise entry-to-anchor visual sightlines as part of Ghost's spatial worldbuilding preflight surface.
- Legal posture: this pass is clean-room approximate 2D corridor geometry over Ghost room-analysis, opening, and actor-check records. It does not copy Epic native MCP, ToolsetRegistry, or SceneTools source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 90 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 118 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct registry dispatch called `spatial_preflight_interior_layout` on an apartment entry-to-sofa layout with a bookshelf between the opening and the sofa; it returned schema `unreal_mcp_ghost.spatial_layout_preflight.v1`, status `needs_review`, `visual_sightline_count=1`, `obstructed_sightline_count=1`, sightline status `obstructed_review`, target `Apt_sofa`, blocker `Apt_bookshelf`, and issue kind `visual_sightline_obstructed`.
  - Tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`; the registry still cataloged 722 tools and the 34-tool spatial toolset, and indirect dispatch returned the same sightline-obstruction evidence.

## Fifty-Seventh Implementation Pass - Screenshot Opening Constraint Handoff

- Extended `spatial_plan_screenshot_reconstruction` so agent/vision detections for architectural doors, windows, doorways, archways, portals, and openings become explicit clean-room opening records in the generated composition plan.
- Screenshot-derived openings now carry source, detected item ID, confidence, zone, wall, center, bounds, and approximate width/height metadata. The planner mirrors them into `composition_plan.room.openings` and top-level `composition_plan.openings` for broader client compatibility.
- `spatial_preflight_interior_layout` now dedupes mirrored opening sources and exempts the wall/architectural opening marker itself from blocking its own protected clearance. Floor props that overlap the protected footprint still emit `opening_clearance_blocked`.
- Screenshot reconstruction workflow output now includes a `preflight_detected_openings` step so agents know to run layout preflight before Tripo import or placement mutation when a reference image contains doors/windows/openings.
- README and tracked tool inventory now advertise screenshot-detected opening/window clearance constraints.
- Legal posture: this pass is clean-room approximate geometry over Ghost screenshot-detection, functional-zone, composition, and layout-preflight schemas. It does not copy Epic native MCP, ToolsetRegistry, or SceneTools source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "detected_openings or maps_detected_props"` passed with 2 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 91 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 119 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_screenshot_reconstruction` with an `entry door` screenshot detection. Direct dispatch returned `detected_opening_count=1`, `wall=positive_y`, and one composition opening; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, and indirect dispatch returned `detected_opening_count=1` plus the `preflight_detected_openings` workflow step.
  - `git diff --check -- README.md unreal_mcp_server\tool_inventory_categories.json unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py knowledge_base\Reports\epic_ue58_mcp_source_audit.md` reported only the existing LF-to-CRLF warnings for README and the tracked inventory file.

## Fifty-Eighth Implementation Pass - Composition-Derived Support Surfaces

- Extended `spatial_plan_support_surface_anchors` so screenshot/generated composition plans can derive temporary horizontal support surfaces from planned support props such as kitchen counters, islands, coffee tables, console tables, shelves, base cabinets, and dressers.
- The support-anchor pass now merges those composition-derived surfaces with live `spatial_analyze_room` `classified_surfaces.horizontal_supports`, keeping live room-analysis surfaces first while letting pre-import/generated counters and tables serve as support anchors before they exist in the level.
- Anchors created from those temporary surfaces are labeled with `source=composition_horizontal_support`, carry `composition_support_surface` roles, and propagate `support_actor`, `support_roles`, and summary counts through the updated composition plan.
- This improves screenshot-driven reconstruction for common interior cases such as counter clutter on a generated counter run or books/decor on a detected table without requiring a live room-analysis pass after every generated asset import.
- README and tracked tool inventory now advertise composition-derived support surfaces for screenshot/generated counters and tables.
- Legal posture: this pass is clean-room approximate geometry over Ghost composition, screenshot reconstruction, support-anchor, and preflight schemas. It does not copy Epic native MCP, ToolsetRegistry, or SceneTools source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "support_surface_anchors_uses_screenshot_composition_supports or support_surface_anchors_retargets_binding"` passed with 2 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 92 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 120 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_support_surface_anchors` on a screenshot reconstruction containing a detected `kitchen counter run` and `counter clutter`. Direct dispatch returned `composition_support_surface_count=1`, `support_actor=SmokeSupport_kitchen_counter_run`, and anchor source `composition_horizontal_support`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, and indirect dispatch returned the same composition-support count and anchor source.

## Fifty-Ninth Implementation Pass - Composition-Derived Wall Anchors

- Extended `spatial_plan_support_surface_anchors` so screenshot/generated composition plans can derive temporary wall planes from inferred room zones when the plan contains wall-mounted props but no live room-analysis wall actors yet.
- The support-anchor pass now creates conservative room/zone wall surfaces for `negative_x`, `positive_x`, `negative_y`, and `positive_y` zone hints, exposes them as `composition_wall_surfaces`, and merges them only when live `classified_surfaces.walls` are absent so measured Unreal wall surfaces stay authoritative.
- Wall-mounted props such as screenshot-detected upper cabinets now anchor with `source=composition_room_wall`, carry `composition_wall_surface` roles, and propagate the selected wall label into placement arguments and support-anchor summaries.
- This improves screenshot-driven reconstruction for apartment/kitchen compositions where the agent sees a wall cabinet, shelf, art piece, or other wall prop before the corresponding Unreal wall actor has been classified by `spatial_analyze_room`.
- README and tracked tool inventory now advertise composition-derived room/zone wall anchors for generated wall props.
- Legal posture: this pass is clean-room approximate geometry over Ghost screenshot reconstruction, functional-zone, support-anchor, and room-analysis schemas. It does not copy Epic native MCP, ToolsetRegistry, or SceneTools source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "composition_room_walls or screenshot_composition_supports or support_surface_anchors_retargets_binding"` passed with 3 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 93 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 121 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_support_surface_anchors` on a screenshot reconstruction containing detected `wall cabinets`. Direct dispatch returned status `ready_for_support_surface_review`, `composition_wall_surface_count=2`, `support_actor=composition_wall_kitchen_negative_y`, and anchor source `composition_room_wall`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, and indirect dispatch returned the same wall-anchor source and support actor.

## Sixtieth Implementation Pass - Spatial Generation Briefs for Tripo Jobs

- Extended `spatial_prepare_tripo_generation_batch` so each guarded Tripo job now carries a `spatial_generation_brief` record with room dimensions, zone, surface/contact target, approximate prop size, planned actor label, placement hint, spatial constraints, generation requirements, and post-import validation gates.
- Text-to-model jobs and text fallbacks now append a concise spatial generation brief to the review/submission prompt. Image-to-model jobs keep the real `gen_tripo_image_to_model` API arguments unchanged and expose the brief as a separate review artifact.
- The guarded pipeline now includes `review_spatial_generation_brief` before spend confirmation so screenshot-crop jobs are reviewed against wall/floor/counter contact and intended Unreal placement instead of being treated as context-free crops.
- This improves the Tripo leg of screenshot-driven interior reconstruction, especially wall-mounted or support-dependent props such as wall cabinets, shelves, counter clutter, and appliances that must fit the room composition after import.
- README and tracked tool inventory now advertise spatial generation briefs in guarded Tripo generation batch manifests.
- Legal posture: this pass is clean-room workflow metadata over Ghost composition, screenshot reconstruction, Tripo handoff, and spatial validation schemas. It does not copy Epic native MCP, SceneTools, ToolsetRegistry, or provider implementation source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "prepare_tripo_generation_batch"` passed with 3 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 94 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 122 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_prepare_tripo_generation_batch` on a screenshot reconstruction containing missing `wall cabinets`. Direct dispatch returned status `needs_user_spend_confirmation`, `spatial_generation_brief_count=1`, `mode=image_to_model`, `brief_surface=wall`, and a `review_spatial_generation_brief` pipeline step; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, and indirect dispatch returned the same wall brief and review step.

## Sixty-First Implementation Pass - Concrete Crop Readiness Gate for Tripo Image Jobs

- Tightened `spatial_prepare_tripo_generation_batch` so image-to-model jobs are no longer considered ready just because a screenshot detection has a crop box or crop hint.
- The batch planner now inspects the actual image handoff and only marks an image job ready when it has a concrete local crop file, HTTP(S) image URL, or Tripo file token. Placeholder handoffs such as `<CROP_FOR_wall_cabinets>` now produce `crop_readiness.status=needs_crop_manifest`.
- Guarded pipelines now include `prepare_image_crop` before spend confirmation. Placeholder crop jobs return status `needs_crop_review`, `blocked_by_crop_manifest_count`, and a `spatial_prepare_screenshot_crop_manifest` next-tool hint; already-written crop manifests still proceed to `needs_user_spend_confirmation`.
- This prevents screenshot-driven reconstruction agents from spending Tripo credits on unresolved crop placeholders and keeps the crop-manifest step explicit before image-to-model generation.
- README and tracked tool inventory now advertise concrete image-crop readiness gates in guarded Tripo generation batch manifests.
- Legal posture: this pass is clean-room local validation over Ghost screenshot-crop, Tripo handoff, and spatial generation batch schemas. It does not copy Epic native MCP, SceneTools, ToolsetRegistry, or Tripo provider implementation source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "prepare_tripo_generation_batch or crop_manifest"` passed with 5 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 94 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 122 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_prepare_tripo_generation_batch` on a screenshot reconstruction containing placeholder-cropped `wall cabinets`. Direct dispatch returned status `needs_crop_review`, `ready_job_count=0`, `blocked_by_crop_manifest_count=1`, `crop_readiness_status=needs_crop_manifest`, `prepare_crop_status=required_before_image_submission`, and `submit_status=blocked_by_crop_review`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, and indirect dispatch returned the same crop-manifest blocker.

## Sixty-Second Implementation Pass - Worldbuilding Crop-Manifest Readiness Gates

- Extended `spatial_compile_worldbuilding_readiness` with a dedicated `screenshot_crop_manifest` gate that reads guarded Tripo batch crop blockers and routes them to `spatial_prepare_screenshot_crop_manifest`.
- The generic `guarded_tripo_generation` readiness gate now defers to the crop-manifest handoff when image-to-model jobs still contain unresolved screenshot crop placeholders, so agents get the concrete next action before spend confirmation.
- Extended `spatial_plan_worldbuilding_work_order` with crop-manifest status, blocked job IDs, a crop-manifest handoff, a `prepare_screenshot_crop_manifest` workflow step, and a quality gate for screenshot crop manifests before Tripo image-to-model spend.
- This keeps screenshot reconstruction work orders spatially grounded: reference-image props must be materialized into real local crop files before generated assets enter the Tripo spend/import/placement chain.
- README and tracked tool inventory now advertise screenshot crop-manifest blockers inside spatial worldbuilding readiness/work-order gates.
- Legal posture: this pass is clean-room workflow orchestration over Ghost worldbuilding readiness, screenshot crop, and Tripo batch schemas. It does not copy Epic native MCP, SceneTools, ToolsetRegistry, or provider implementation source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "worldbuilding_readiness or worldbuilding_work_order"` passed with 8 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 95 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 123 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_worldbuilding_work_order` on a screenshot reconstruction containing placeholder-cropped `refrigerator`. Direct dispatch returned status `needs_screenshot_crop_manifest`, `crop_manifest_required=true`, `blocked_by_crop_manifest_count=1`, and `blocked_crop_job_ids=["refrigerator"]`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, and indirect dispatch returned the same crop-manifest blocker.

## Sixty-Third Implementation Pass - Live Candidate-Clearance Readiness Gate

- Extended `spatial_compile_worldbuilding_readiness` with a `candidate_clearance_json` input for `spatial_preflight_candidate_clearance` output.
- Added a first-class `live_candidate_clearance` readiness gate between local layout preflight/correction and dry-run apply. The gate accepts `pass` and `needs_review`, and blocks `blocked_by_clearance` or other non-passing clearance statuses before scene mutation.
- The gate routes blocking live-overlap evidence to `spatial_plan_composition_iteration` and missing evidence to `spatial_preflight_candidate_clearance`, keeping existing live Unreal actors authoritative after local room-bound/footprint planning.
- `spatial_plan_worldbuilding_work_order` readiness handoffs now include `candidate_clearance_json`, matching the existing `live_candidate_clearance_before_mutation` quality gate.
- README and tracked tool inventory now advertise live candidate-clearance blockers inside spatial worldbuilding readiness/work-order gates.
- Legal posture: this pass is clean-room orchestration over Ghost candidate-clearance, worldbuilding readiness, and composition iteration schemas. It does not copy Epic native MCP, SceneTools, ToolsetRegistry, or provider implementation source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "worldbuilding_readiness or worldbuilding_work_order or candidate_clearance"` passed with 11 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 96 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 124 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_compile_worldbuilding_readiness` with `candidate_clearance_json.status=blocked_by_clearance`. Direct dispatch returned status `blocked`, `live_candidate_clearance.status=blocked_by_clearance`, `blocking=true`, and next tool `spatial_plan_composition_iteration`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, and indirect dispatch returned the same live-clearance blocker.

## Sixty-Fourth Implementation Pass - Candidate-Clearance Driven Iteration Corrections

- Extended `spatial_plan_composition_iteration` so its existing `validation_result_json` parameter accepts either `spatial_validate_placement` output or `spatial_preflight_candidate_clearance` output.
- Candidate-clearance candidates are normalized into iteration-friendly validation records with actor labels, probe locations, overlap centers, candidate status, and a `candidate_clearance_summary`.
- Blocking live-overlap results such as `blocked_by_existing_overlap` now produce reviewed dry-run correction candidates, including deterministic XY nudges away from existing actor bounds, instead of failing schema validation.
- Iteration output now exposes `source_validation_schema` so agents can distinguish final placement-validation corrections from pre-mutation live-clearance corrections.
- README and tracked tool inventory now advertise iterative correction planning from placement validation or live candidate-clearance blockers.
- Legal posture: this pass is clean-room schema normalization and correction planning over Ghost candidate-clearance and composition-iteration schemas. It does not copy Epic native MCP, SceneTools, ToolsetRegistry, or provider implementation source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py`
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "composition_iteration or candidate_clearance or worldbuilding_readiness"` passed with 11 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 97 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 125 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_composition_iteration` with `spatial_preflight_candidate_clearance` output for a sofa overlapping an existing table. Direct dispatch returned status `needs_correction`, `source_validation_schema=unreal_mcp_ghost.spatial_candidate_clearance.v1`, `correction_count=1`, and `candidate_location=[0.0, 25.0, 0.0]`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, and indirect dispatch returned the same candidate-clearance correction.

## Sixty-Fifth Implementation Pass - Corrected Composition Plan Handoffs from Iteration

- Extended `spatial_plan_composition_iteration` so reviewed correction candidates are written back into a Ghost composition payload as `updated_composition_plan`, `updated_placement_steps`, and `updated_composition_plan_json`.
- Corrected placement steps now carry `composition_iteration_correction` metadata, stay dry-run-only, and preserve `allow_mutation=false` until the user explicitly approves later mutation.
- Corrected props mirror the updated actor placement location so downstream support anchoring, layout preflight, live candidate clearance, dry-run apply, and validation consume one coherent composition plan rather than loose transform suggestions.
- Iteration output now includes `layout_preflight_handoff`, `candidate_clearance_handoff`, and `apply_handoff` for the corrected composition plan, closing the pre-mutation correction loop after validation or live-clearance blockers.
- The `rerun_iteration_planner` loop step now also receives `updated_composition_plan_json`, so repeated correction cycles continue from corrected placement coordinates rather than a placeholder/original composition payload.
- README and tracked tool inventory now advertise iterative correction planning with corrected composition-plan handoffs.
- Legal posture: this pass is clean-room composition-schema rewriting over Ghost correction and placement records. It does not copy Epic native MCP, SceneTools, ToolsetRegistry, or provider implementation source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py` passed.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "composition_iteration or candidate_clearance"` passed with 6 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 97 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 125 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_composition_iteration` with `spatial_preflight_candidate_clearance` output for a sofa overlapping an existing table. Direct dispatch returned status `needs_correction`, `source_validation_schema=unreal_mcp_ghost.spatial_candidate_clearance.v1`, `correction_count=1`, `candidate_location=[0.0, 25.0, 0.0]`, `updated_step_location=[0.0, 25.0, 0.0]`, `apply_handoff.enabled=true`, and a `rerun_iteration_planner` composition payload containing both `composition_iteration_summary` and the corrected location; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, hid the direct spatial tool, and indirect dispatch returned the same corrected composition-plan handoff.

## Sixty-Sixth Implementation Pass - Project-Asset-Filtered Tripo Work Orders

- Added a post-resolution generation source builder for `spatial_plan_worldbuilding_work_order`. When project asset resolution finds existing assets, the work order now rewrites Ghost's own composition/source payload so resolved props receive concrete `/Game` asset paths and unresolved props retain guarded Tripo generation tasks.
- Work orders now build a real `spatial_prepare_tripo_generation_batch` preview after project-asset resolution instead of only counting unresolved props and leaving a placeholder composition handoff.
- The filtered generation source removes catalog-resolved props from `generation_tasks` and screenshot `crop_tasks`, so guarded Tripo jobs are limited to unresolved props while still preserving dry-run placement steps, spatial-generation briefs, spend guards, import handoffs, and validation handoffs.
- README and tracked tool inventory now advertise guarded Tripo generation manifests with project-asset-filtered unresolved-prop jobs.
- Legal posture: this pass is clean-room orchestration over Ghost project-asset resolution, composition, screenshot reconstruction, and Tripo batch schemas. It does not call paid providers, mutate Unreal, copy Epic native MCP, SceneTools, ToolsetRegistry, or provider implementation source; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py` passed.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "worldbuilding_work_order or tripo_generation_batch or project_asset"` passed with 11 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 97 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 125 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_worldbuilding_work_order` with a kitchen asset catalog resolving `refrigerator` and `stove_and_oven`. Direct dispatch returned status `ready_for_guarded_tripo_review`, resolved ids `refrigerator` and `stove_and_oven`, unresolved ids `backsplash_panel`, `base_cabinets`, `counter_clutter`, `kitchen_counter_run`, and `kitchen_sink`, and a guarded Tripo batch with 5 text jobs, 0 image jobs, and all `confirm_spend=false`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, hid the direct work-order tool, and indirect dispatch returned the same filtered batch preview.

## Sixty-Seventh Implementation Pass - Work-Order Binding Handoffs for Reused and Generated Assets

- Extended `spatial_plan_worldbuilding_work_order` with concrete binding handoffs after project-asset resolution.
- Work orders now expose `asset_strategy.existing_asset_binding_handoff`, which calls `spatial_bind_generated_assets_to_composition` with the selected project asset overrides and `include_unresolved_steps=true`, letting agents bind reused `/Game` assets before spending on missing props.
- Work orders also expose `tripo_strategy.post_generation_binding_handoff`, which binds future Tripo import results back into the same post-project-asset-resolution composition JSON so reused project assets and generated assets place together in one dry-run composition.
- The workflow now has an explicit `bind_existing_project_assets` step plus `bind_review_apply_validate.binding_handoffs` for both pre-generation project assets and post-generation imports.
- README and tracked tool inventory now advertise binding handoffs that merge reused project assets plus generated imports into one dry-run composition.
- Legal posture: this pass is clean-room handoff wiring over Ghost asset-resolution, composition-binding, and work-order schemas. It does not execute Unreal mutation, paid Tripo calls, computer vision, or Epic native SceneTools code; future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py` passed.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "worldbuilding_work_order or tripo_generation_batch or project_asset or composition_asset_binding"` passed with 11 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 97 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 125 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_worldbuilding_work_order` with a kitchen asset catalog resolving `refrigerator` and `stove_and_oven`, then called the emitted `spatial_bind_generated_assets_to_composition` existing-asset handoff. Direct dispatch and indirect ToolsetRegistry dispatch both returned the work-order status `ready_for_guarded_tripo_review`, the same five unresolved Tripo jobs with all `confirm_spend=false`, enabled existing/post-generation binding handoffs, and a bound existing-asset composition with status `waiting_for_generated_assets`, `resolved_count=2`, `unresolved_count=5`, refrigerator `/Game/Props/Kitchen/SM_RefrigeratorFull.SM_RefrigeratorFull`, and stove `/Game/Props/Kitchen/SM_StoveRange.SM_StoveRange`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, and hid both direct spatial tools.

## Sixty-Eighth Implementation Pass - Post-Binding Spatial Pipeline Handoffs

- Added `_work_order_actor_labels` and `_work_order_post_binding_spatial_pipeline` so worldbuilding work orders now expose a first-class post-binding review pipeline after project assets and generated Tripo imports are merged into one composition.
- `spatial_plan_worldbuilding_work_order` now returns `placement_strategy.post_binding_spatial_pipeline` and embeds the same pipeline under the `bind_review_apply_validate` workflow step, making the handoff visible to direct clients and native-style tool-search clients.
- The pipeline sequences scale review, support-surface anchoring, layout preflight, layout-preflight repair, live candidate-clearance preflight, dry-run apply, placement validation, iteration from either placement validation or candidate-clearance blockers, and viewport evidence capture.
- Candidate-clearance handoffs ignore the actors planned by the same work order, so the live-overlap check focuses on pre-existing level geometry rather than self-overlap from the proposed composition.
- Apply remains dry-run-first with `block_on_preflight_errors=true` and `block_on_spatial_fit_review=true`; mutation still requires explicit user approval outside this planner.
- README and tracked tool inventory now advertise post-binding spatial pipeline handoffs for scale review, support anchoring, layout/candidate-clearance preflight, dry-run apply, validation, iteration, and viewport evidence.
- Legal posture: this pass is clean-room handoff wiring over Ghost composition, asset-binding, spatial-validation, and work-order schemas. It does not execute Unreal mutation, paid Tripo calls, computer vision, or Epic native SceneTools code. Future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py` passed.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "worldbuilding_work_order or tripo_generation_batch or project_asset or composition_asset_binding"` passed with 11 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 97 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 125 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_worldbuilding_work_order` with a kitchen asset catalog resolving `refrigerator` and `stove_and_oven`, then called the emitted `spatial_bind_generated_assets_to_composition` existing-asset handoff. Direct dispatch returned status `ready_for_guarded_tripo_review`, the post-binding pipeline schema `unreal_mcp_ghost.spatial_post_binding_pipeline.v1`, `actor_count=7`, required pipeline steps from `bind_assets` through `capture_viewport_evidence`, five unresolved guarded Tripo jobs, and binding status `waiting_for_generated_assets`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, hid both direct spatial tools, and indirect dispatch returned the same work-order and binding statuses.

## Sixty-Ninth Implementation Pass - First-Class Hallway Zones

- Promoted `hallway` from an `entry` alias into a first-class functional zone for apartment, studio, and hallway room analysis/planning.
- Added hallway-specific props to the interior prop library: hallway runner rug, wall hooks, and shoe bench, plus hallway baseboard trim as architectural fill.
- Updated local room-zone templates and the generated `spatial_analyze_room` live-analysis script so both local planners and Unreal-side room analysis agree on corridor-shaped hallway regions.
- Extended functional-zone planning with a `preserve_hallway_linear_circulation` constraint and hallway composition notes, so hallway zones are planned as narrow/wall-hugging circulation spaces rather than generic entry areas.
- Extended composition semantics and layout preflight with `hallway_linear_clearance` and `semantic_hallway_clearance_review`, warning when a hallway floor prop is too wide for a readable corridor lane and routing review toward `spatial_plan_composition_iteration`.
- README and tracked tool inventory now advertise kitchen/living/sleeping/entry/hallway/utility zone planning and hallway linear-clearance review.
- Legal posture: this pass is clean-room heuristic planning over Ghost room, zone, prop-program, composition, and preflight schemas. It does not copy Epic native MCP/SceneTools source, mutate Unreal Editor state, or call paid providers. Future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\unreal_mcp_server.py` passed.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "hallway or functional_zones or prop_program or interior_composition or preflight_interior_layout"` passed with 22 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 99 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 127 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning.
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_infer_functional_zones` for a screenshot-style hallway with `runner rug` and `wall hooks`, then called `spatial_preflight_interior_layout` on a wide hallway floor prop. Direct dispatch returned zone names `hallway` and `entry`, recommended props `hallway runner rug`, `wall hooks`, and `shoe bench`, preflight status `needs_review`, and issue kind `semantic_hallway_clearance_review`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, cataloged the 34-tool spatial toolset, hid the direct hallway tools, and indirect dispatch returned the same hallway/preflight statuses.

## Seventieth Implementation Pass - Authored Room Bounds Designation

- Added `spatial_plan_room_bounds_designation`, a local/read-only contract planner for practical editor authoring of `Ghost.RoomBounds`, `Ghost.RoomId.*`, `Ghost.RoomType.*`, `Ghost.Zone.*`, `Ghost.Opening.*`, `Ghost.Clearance.*`, `Ghost.Path.Required`, and `Ghost.Surface.*` markers.
- Extended generated `spatial_analyze_room` live-analysis code so tagged room-bounds actors become the authoritative room envelope before heuristic aggregate bounds. Tagged zone, opening, clearance, path, and surface markers now appear in an `authored_room_designation` block and marker actors are classified separately from props/obstacles.
- Updated functional-zone inference to treat authored room-analysis zones as strong evidence and to use their actual bounds as zone templates. Authored labels such as `genkan` or `kitchenette` can map to canonical spatial roles such as `entry` or `kitchen` without introducing a fixed prop pack.
- Finished the bedroom-zone cleanup by making apartment/studio/bedroom templates and the live analysis script use `bedroom` as the normal zone name while preserving `sleeping` as a legacy input alias.
- README and tracked tool inventory now advertise spatial room-bounds designation contracts, authored marker recognition, and kitchen/living/bedroom/entry/hallway/utility planning.
- Legal posture: this pass is clean-room Ghost tag-contract and planner implementation over Unreal Python actor tags/bounds. It does not copy Epic native MCP/SceneTools source, mutate Unreal Editor state, create a bundled prop pack, or call paid providers. Future direct reuse of staged Epic spatial implementation details still requires legal review.
- Verification:
  - `python -m py_compile unreal_mcp_server\tools\spatial_awareness_tools.py unreal_mcp_server\tests\test_spatial_awareness_tools.py` passed.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q -k "room_bounds_designation or authored_room_zones or analyze_room_generates"` passed with 3 selected tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py -q` passed with 101 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_spatial_awareness_tools.py unreal_mcp_server\tests\test_toolset_registry.py unreal_mcp_server\tests\test_bridge_descriptors.py unreal_mcp_server\tests\test_client_config.py unreal_mcp_server\tests\test_server_runtime.py -q` passed with 129 tests and one existing pytest-cache warning.
  - `python -m pytest unreal_mcp_server\tests\test_tool_count.py -q` passed with 3 tests and one existing pytest-cache warning under the repo's tracked-only static inventory convention (`tool_count=670`).
  - `python scripts\tool_inventory.py --json` reported `tool_count=670`, `module_count=47`, and no missing category modules under the repo's tracked-only static inventory convention.
  - Direct and tool-search-mode smoke called `spatial_plan_room_bounds_designation` for `apartment_01` with `genkan`, `kitchenette`, `living`, and `bedroom` zones. Direct dispatch returned schema `unreal_mcp_ghost.spatial_room_bounds_designation.v1` with `genkan -> entry` and `kitchenette -> kitchen`; tool-search mode exposed only `call_tool`, `describe_toolset`, `list_toolsets`, and `tool_contribution_contract`, described `spatial_plan_room_bounds_designation`, and indirect dispatch returned the same schema and zone-role mapping.
