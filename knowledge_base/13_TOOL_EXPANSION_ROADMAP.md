# Unreal-MCP-Ghost Roadmap

Last updated: 2026-05-16

This roadmap is the working plan for turning Unreal-MCP-Ghost into a production-grade AI game development platform for Unreal Engine 5. It replaces older command-by-command expansion notes that were useful during the 300-400 tool era, but are now too stale to guide the next phase.

## North Star

Unreal-MCP-Ghost should let an AI agent build, inspect, repair, and verify full UE5 gameplay systems while preserving editor stability and project integrity.

The target is not simply "more tools." The target is reliable end-to-end workflows:

1. Discover project state before mutation.
2. Make small, structured editor changes through engine APIs.
3. Compile, save, inspect, and verify after each meaningful change.
4. Return evidence: graph summaries, diagnostics, screenshots, logs, or asset diffs.
5. Keep risky operations auditable and reversible.

## Current Baseline

Static registry audit currently finds 481 MCP tools: 478 Python tools under `unreal_mcp_server/tools` plus 3 higher-level skills under `unreal_mcp_server/skills`.

Strong areas:

- Blueprint creation, graph editing, variables, functions, nodes, comments, diagnostics, and repair.
- Behavior Tree and Blackboard authoring, including full-tree JSON construction.
- Animation Blueprint basics, state machines, AnimGraph slot insertion, IK Rig, IK Retargeter, skeleton inspection, and batch retargeting.
- Import pipelines for textures, meshes, skeletal meshes, audio, batch folders, and GhostRigger assets.
- UMG/widget, gameplay, data, save-game, procedural, physics, VR, variant, reflection, project intelligence, C++ bridge, source control, and editor chat surfaces.
- Dual MCP transport support: stdio, SSE, and streamable HTTP.
- C++ plugin bridge with editor GameThread command execution and an optional MCP Chat dock tab.

Partially live areas:

- Niagara/VFX exists, but is mostly discovery, safe system settings, Blueprint spawn nodes, component attachment, and recipes. Full native Niagara emitter/module/renderer authoring is not yet present.
- AI covers Blackboard/BT/PawnSensing, data-level EQS query authoring, BT Run EQS wiring, AI Perception components, sight/hearing configs, stimulus sources, nav links, nav modifier volumes, RVO defaults, Detour guidance, and AI debug snapshots.
- Technical art now covers basic materials, material instance parameters, master material creation, material function assets, texture-set wiring, material instance creation, bulk instance parameter updates, ORM texture generation, texture memory audits, vertex paint automation, mesh UV-channel audits, shader graph complexity estimates, diagnostic viewmode captures, overdraw visualization, and lightweight GPU/performance snapshots.
- Autonomous verification exists in pieces through diagnostics, screenshots, source control status, and chat, but needs a formal execution journal, risk evaluation, PIE automation, and screenshot analysis loop.

Missing or thin areas:

- Multiplayer/networking tools: Slices 1-3 now cover replication inspection/defaults, RepNotify variables, RPC Custom Event authoring/configuration, authority/role/owner graph helpers, Blueprint session flow nodes, runtime replication snapshots, and common mistake validation.
- Niagara native authoring: systems from recipes, emitters, modules, renderers, parameters, events, ribbons, GPU/CPU collision, fluid/flipbook workflows, and profiling.
- Production distribution/performance: command registry generated from metadata, startup profiling, and optional high-performance server packaging.

## Engineering Principles

These come from the repo knowledge-base guides and current plugin lessons:

- Prefer narrow C++ bridge commands for editor operations that Python cannot do safely or completely.
- Prefer structured JSON results over silent no-ops or string-only errors.
- Avoid editor-crash paths already documented in the plugin, especially direct graph notifications in fragile asset editors.
- Keep Blueprint/BT/AnimGraph mutations transaction-sized and immediately inspectable.
- Use vertical-slice tests: create or inspect a tiny realistic asset, then verify the resulting state.
- Add high-level skill workflows only after the underlying low-level tools are trustworthy.
- Keep docs, tests, and reported tool counts synchronized.

## Phase 0 - Roadmap And Registry Hygiene

Goal: make the current surface measurable and keep planning artifacts honest.

Status: complete.

Tasks:

- Replace stale 362/406/419-era roadmap notes with this current roadmap. Done.
- Reconcile documented tool count to the current static count. Done.
- Add an offline test that checks `README.md` and `tests/last_tool_count.txt` against the static tool registry count. Done.
- Create or document a single canonical tool inventory command. Done: `python scripts/tool_inventory.py --markdown`.
- Add a machine-readable category map for tools and skills. Done: `unreal_mcp_server/tool_inventory_categories.json`.
- Mark implemented, partial, and missing areas in the knowledge base index. Done.

Definition of done:

- `python -m unittest unreal_mcp_server.tests.test_tool_count` passes.
- README and `last_tool_count.txt` agree with the static registry count.
- Roadmap has clear first implementation slices.

## Phase 1 - Niagara Native Authoring

Goal: make VFX creation a first-class MCP workflow instead of a recipe-only workflow.

Status: Slice 1 native bridge foundation is implemented and live-tested in Lab5E. Slice 2 native renderer tools and spawn-rate module editing are implemented and live-tested.

Why first:

- It is the largest confirmed gap.
- The plugin already has Niagara module dependencies.
- Existing Python tools already establish naming, result shape, and tests.

Slice 1:

- `niagara_validate_authoring_support` - implemented as a read-only Python/editor API probe.
- `niagara_create_system` - implemented as a native C++ bridge command with Python fallback for older installed plugins.
- `niagara_describe_system` - upgraded to use native C++ bridge inspection when available, including emitter handles and user parameters.
- `niagara_add_empty_emitter` - implemented as a native C++ bridge command for adding an empty emitter handle to a system.
- `niagara_set_system_user_parameter` - implemented as a native C++ bridge command for exposed float, bool, vector3, and color parameters.
- `niagara_set_fixed_bounds` - implemented as a focused fixed-bounds setter.
- `niagara_profile_system` - implemented as a lightweight asset-level profile/inspection tool.

Slice 2:

- `niagara_add_sprite_renderer` - implemented as a native C++ bridge command for adding a sprite renderer to an emitter handle.
- `niagara_add_mesh_renderer` - implemented as a native C++ bridge command for adding a mesh renderer backed by a Static Mesh asset.
- `niagara_set_spawn_rate` - implemented as a native C++ bridge command for adding/updating the emitter `SpawnRate` module's particles-per-second value.
- `niagara_add_force_module`
- `niagara_add_collision_module`
- `niagara_add_event_handler`

Slice 3:

- `niagara_create_system_from_recipe`
- `niagara_add_ribbon_renderer`
- `niagara_configure_subuv_animation`
- `niagara_bake_flipbook`
- `niagara_create_fluid_simulation_preset` where engine APIs permit.

Validation:

- Offline wrapper tests for tool registration and schema.
- UE live smoke test that creates a minimal system, adds one emitter, sets bounds/user params, saves, describes, and profiles.
- Screenshot or viewport capture for a placed NiagaraComponent when feasible.

Lab5E smoke result, 2026-05-16:

- Live Coding loaded the updated Lab5E project plugin.
- Created `/Game/MCP_Test/VFX/NS_MCP_Phase1_NativeSmoke`.
- Added emitter handle `MCP_TestEmitter`.
- Added one sprite renderer to `MCP_TestEmitter`.
- Added exposed float parameter `MCP_Intensity`.
- Native describe reported 1 emitter, 1 renderer, and 1 user parameter.
- Created `/Game/MCP_Test/VFX/NS_MCP_Phase1_MeshSmoke`.
- Added emitter handle `MCP_MeshEmitter`.
- Added one mesh renderer backed by `/Engine/BasicShapes/Cube.Cube`.
- Native describe reported renderer class and static mesh path.
- Created `/Game/MCP_Test/VFX/NS_MCP_Phase1_SpawnRateSmoke`.
- Added emitter handle `MCP_SpawnEmitter`.
- Set the native `SpawnRate` module to `42`, creating the module.
- Set the native `SpawnRate` module to `84`, updating the existing module without duplicating it.

## Phase 2 - Modern AI Systems

Goal: move from BT/Blackboard-only AI to full encounter authoring and debugging.

Status: Slice 1 EQS data-asset authoring and Behavior Tree Run EQS service wiring are implemented and live-tested in Lab5E. Slice 2 AI Perception listener/source authoring is implemented and live-tested in Lab5E. Slice 3 navigation/crowd/debug tooling is implemented and live-tested in Lab5E.

Slice 1:

- `eqs_create_query` - implemented as a native C++ bridge command with a Python MCP wrapper.
- `eqs_add_generator` - implemented for Simple Grid, Circle, Donut, Current Location, and Actors of Class generator classes.
- `eqs_add_test` - implemented for Distance, Pathfinding, Dot, and Trace test classes.
- `eqs_describe_query` - implemented as readback inspection for query options, generators, and tests.
- `bt_add_run_eqs_service` - implemented as a native C++ bridge command that attaches or updates `BTService_RunEQS`, sets the EQS query, result Blackboard key, run mode, interval, and update-on-fail behavior.

Slice 2:

- `perception_add_component` - implemented as a native C++ bridge command for adding/finding `AIPerceptionComponent` on Blueprint SCS.
- `perception_configure_sight` - implemented for Sight radius, lose-sight radius, peripheral vision angle, affiliation filters, and dominant sense.
- `perception_configure_hearing` - implemented for Hearing range, affiliation filters, and optional dominant sense.
- `perception_create_stimulus_source` - implemented as a native C++ bridge command for `AIPerceptionStimuliSourceComponent` with sight/hearing source registration.
- `perception_bind_updated_event` - implemented as a Python wrapper around the existing component-bound event node command for Perception delegates.
- `perception_describe_blueprint` - implemented as readback inspection for perception listeners and configured sense assets.

Slice 3:

- `nav_create_link_proxy` - implemented as a native C++ bridge command that spawns and configures point-link `ANavLinkProxy` actors.
- `nav_add_modifier_volume` - implemented as a native C++ bridge command that spawns `ANavModifierVolume` actors with a chosen `UNavArea`.
- `nav_describe_agent_settings` - implemented as readback inspection for supported agents, nav data, navmesh bounds, links, and modifier counts.
- `crowd_configure_rvo` - implemented for Character Blueprint `CharacterMovement` RVO avoidance defaults and masks.
- `crowd_configure_detour` - implemented for existing native `UCrowdFollowingComponent` controllers, with structured guidance when a Blueprint cannot retrofit the required default subobject.
- `gameplay_debugger_capture_ai` - implemented as a lightweight AI/navigation world snapshot.

Validation:

- Tiny AI vertical slice: Character + AIController + Blackboard + BT + EQS query + perception component.
- Verify navmesh, controller possession, blackboard keys, and BT graph info.

Lab5E smoke result, 2026-05-16:

- Live Coding loaded the updated Lab5E project plugin.
- Created `/Game/MCP_Test/AI/EQS_MCP_Phase2_FindPoint`.
- Added one `EnvQueryGenerator_SimpleGrid` option.
- Added one `EnvQueryTest_Distance` test.
- Native describe reported 1 option, the Simple Grid generator, and 1 Distance test.
- Created `/Game/MCP_Test/AI/BB_MCP_Phase2_EQSService` with vector key `EQSResult`.
- Created `/Game/MCP_Test/AI/BT_MCP_Phase2_EQSService`, assigned the Blackboard, and built a Selector/Wait smoke tree.
- Attached `BTService_RunEQS` to the Selector, targeting `/Game/MCP_Test/AI/EQS_MCP_Phase2_FindPoint` and Blackboard key `EQSResult`.
- Re-ran the tool with a different run mode and interval; it updated the existing service without duplicating the sub-node.
- Created `BP_MCP_Phase2_PerceptionController`, added `AIPerception`, configured Sight at 4200/5000 radius with 85-degree peripheral vision, and configured Hearing at 2800 range.
- Native describe reported `AISense_Sight` as dominant with Sight and Hearing configs.
- Created `BP_MCP_Phase2_StimulusSource` and added `PerceptionStimuliSource` registered for Sight and Hearing.
- Added an `OnTargetPerceptionUpdated` component-bound event node on the perception controller Blueprint.
- Spawned `MCP_Phase2_NavLink` with a point link using `NavArea_Default`; native readback reported 1 nav link proxy.
- Spawned `MCP_Phase2_NavBlocker` as a `NavArea_Null` modifier volume; native readback reported 1 nav modifier volume.
- Captured an AI debug snapshot for world `Lab-0X`; it reported nav link/modifier counts and no active AI controllers in the current level.
- Created/reparented `BP_MCP_Phase2_RVOCharacter` to `Character` and configured RVO defaults: enabled, 650 radius, 0.7 weight, group mask 1, avoid-all mask.
- Ran `crowd_configure_detour` against `BP_MCP_Phase2_PerceptionController`; it correctly returned `configured:false` with native `UCrowdFollowingComponent` constructor guidance.

## Phase 3 - Multiplayer And Networking

Goal: support networked gameplay authoring without relying on generic property setters.

Status: Slice 1 replication inspection and safe replication defaults are implemented and live-tested in Lab5E. Slice 2 RPC and authority graph helpers are implemented and live-tested in Lab5E. Slice 3 session flow helpers and replication diagnostics are implemented and live-tested in Lab5E.

Slice 1:

- `net_describe_blueprint_replication` - implemented as readback for Actor replication defaults, replicated Blueprint variables, RepNotify functions, SCS component replication, and existing RPC functions.
- `net_set_actor_replicates` - implemented for Actor-derived Blueprint CDO defaults: `bReplicates`, movement replication, update frequency, and min update frequency.
- `net_set_component_replicates` - implemented for Blueprint SCS component templates using the public component replication API.
- `net_configure_replicated_property` - implemented for existing Blueprint member variables with none/replicated/RepNotify modes and lifetime conditions.
- `net_add_repnotify_variable` - implemented for adding simple Blueprint member variables and generating the `OnRep_` function graph.

Slice 2:

- `net_create_rpc_event` - implemented for creating/updating Custom Events with Server, Client, NetMulticast, reliable, and simple typed input parameters.
- `net_configure_rpc` - implemented for retagging existing Custom Events with RPC type/reliability flags.
- `net_add_authority_gate` - implemented as `AActor::HasAuthority` wired into a Branch node so `Then` is authority/server flow and `Else` is remote/client flow.
- `net_add_role_switch` - implemented as an `ENetRole` switch node with role case pins for graph wiring.
- `net_set_owner_reference` - implemented as an `AActor::SetOwner` call node for server-side ownership setup.

Slice 3:

- `session_create_blueprint_flow` - implemented as a `CreateSession` async Blueprint node with `GetPlayerController(0)` wired and public connection/LAN/lobby defaults set.
- `session_find_blueprint_flow` - implemented as a `FindSessions` async Blueprint node with `GetPlayerController(0)` wired and max result/LAN/lobby defaults set.
- `network_debug_replication` - implemented as a runtime/editor snapshot for net mode, net driver, connections, network object counts, and replicated actor samples.
- `net_validate_common_mistakes` - implemented for Actor replication defaults, replicated components/variables, RepNotify handlers, owner-conditioned variables, and risky reliable multicast RPCs.

Validation:

- Two-player PIE smoke plan if available.
- Static graph inspection for RPC flags, replicated variables, RepNotify handlers, and authority guards.

Lab5E smoke result, 2026-05-16:

- Live Coding loaded the updated Lab5E project plugin after UE 5.6 API fixes for movement replication readback and component replication.
- Created `BP_MCP_Phase3_NetActor`.
- Added SCS component `ReplicatedMesh` and configured it to replicate.
- Enabled Actor replication and movement replication; set net update frequency to `30` and min net update frequency to `5`.
- Added existing variable `Score` and configured it as replicated with `owner_only` lifetime condition.
- Added RepNotify variable `Health`, generated `OnRep_Health`, and configured it with `skip_owner` lifetime condition.
- Native readback reported `actor_replicates=true`, `replicate_movement=true`, `ReplicatedMesh.is_replicated=true`, `Score.is_replicated=true`, and `Health.is_repnotify=true`.
- Created RPC Custom Event `Server_Phase3_DoThing` with a `Damage` float input, initially configured as reliable Server, then reconfigured to NetMulticast.
- Added a live authority gate; readback confirmed the HasAuthority return pin was connected to the Branch condition.
- Added an `ENetRole` switch node with `ROLE_None`, `ROLE_SimulatedProxy`, `ROLE_AutonomousProxy`, and `ROLE_Authority` pins.
- Added a `SetOwner` call node exposing the `NewOwner` pin.
- Native readback reported `Server_Phase3_DoThing` under `rpc_functions` with `net_multicast` flags.
- Added a `CreateSession` async Blueprint flow with `GetPlayerController(0)` wired, `PublicConnections=6`, LAN enabled, and lobbies enabled.
- Added a `FindSessions` async Blueprint flow with `GetPlayerController(0)` wired, `MaxResults=12`, LAN enabled, and lobbies enabled.
- Captured a runtime replication snapshot for world `Lab-0X`; the standalone editor world reported no active net driver and 4 replicated actor samples.
- Ran common networking validation against `BP_MCP_Phase3_NetActor`; it checked 1 Blueprint and reported 0 issues.

## Phase 4 - Technical Art Pipeline

Goal: make materials, textures, and performance views as automatable as Blueprints.

Status: Slice 1 master material and material instance pipeline tooling is implemented and live-tested in Lab5E. Slice 2 texture/mesh/vertex-paint audit helpers are implemented and live-tested in Lab5E. Slice 3 shader/viewmode/GPU audit helpers are implemented and live-tested in Lab5E.

Slice 1:

- `material_create_master` - implemented as a native C++ bridge command with a Python MCP wrapper for standard BaseColor, Metallic, Roughness, EmissiveColor, Opacity, and texture parameters.
- `material_create_function` - implemented as a native C++ bridge command with a Python MCP wrapper for exposed Material Function assets.
- `material_wire_texture_set` - implemented as a native C++ bridge command with a Python MCP wrapper for BaseColor, Normal, ORM, and Emissive texture wiring. ORM maps R/G/B to AO/Roughness/Metallic.
- `material_create_instance_from_master` - implemented as a native C++ bridge command with a Python MCP wrapper for Material Instance Constant creation.
- `material_set_instance_parameters_bulk` - implemented as a native C++ bridge command with a Python MCP wrapper for scalar, vector, and texture parameter updates in one call.

Slice 2:

- `texture_generate_orm` - implemented as a native C++ bridge command with a Python MCP wrapper for packed R/G/B ORM Texture2D generation from source maps or flat defaults.
- `texture_audit_memory` - implemented as a native C++ bridge command with a Python MCP wrapper for Texture2D size, mip, compression, streaming, source-format, and estimated source-memory readback.
- `vertex_paint_actor` - implemented as a native C++ bridge command with a Python MCP wrapper for component override vertex colors on placed StaticMesh actors/components.
- `mesh_audit_uv_channels` - implemented as a native C++ bridge command with a Python MCP wrapper for StaticMesh LOD, UV-channel, vertex, triangle, and vertex-color readback.

Slice 3:

- `shader_analyze_complexity` - implemented as a native C++ bridge command with a Python MCP wrapper for fast graph-level shader complexity estimates and recommendations.
- `renderer_capture_viewmode` - implemented as a native C++ bridge command with a Python MCP wrapper for active viewport diagnostic PNG capture.
- `shader_visualize_overdraw` - implemented as a native C++ bridge command with a Python MCP wrapper for shader complexity plus quad-overdraw review.
- `performance_audit_gpu` - implemented as a native C++ bridge command with a Python MCP wrapper for RHI adapter, feature level, memory, viewport, and scene/component snapshots.

Validation:

- Build one PBR master material from a texture set.
- Verify material compile diagnostics, parameter names, texture compression, and asset references.
- Capture shader complexity and overdraw viewmodes from a live editor viewport.
- Return GPU/RHI, memory, viewport, and scene-count evidence for lightweight performance triage.

Lab5E smoke result, 2026-05-16:

- Live Coding loaded the updated Lab5E project plugin after UE 5.6 material API checks and timeout fixes.
- Created `/Game/MCP_Test/Materials/M_MCP_Phase4_MasterFast3` with standard scalar/vector/texture parameters; native result reported `connected=true`, `saved=false`, and `compiled=false`.
- Created and saved `/Game/MCP_Test/Materials/MF_MCP_Phase4_Test` as an exposed Material Function asset.
- Created and saved `/Game/MCP_Test/Materials/MI_MCP_Phase4_MasterFast` from `/Game/MCP_Test/Materials/M_MCP_Phase4_MasterFast`.
- Bulk-updated `MI_MCP_Phase4_MasterFast` parameters: `Metallic`, `Roughness`, and `BaseColor`; native result reported 2 scalar and 1 vector parameters set.
- Wired `/Engine/EngineResources/DefaultTexture.DefaultTexture` into the master material as `BaseColorTexture`; native result reported 1 wired texture and no missing textures.
- Added `RenderCore` as a plugin dependency for component override vertex-color initialization.
- Created and saved `/Game/MCP_Test/Materials/T_MCP_Phase4_Slice2_ORM` as an 8x8 packed ORM texture; native result reported `R=Occlusion, G=Roughness, B=Metallic, A=255`.
- Audited `T_MCP_Phase4_Slice2_ORM`; native readback reported `TC_Masks`, `SRGB=false`, `source_format=TSF_BGRA8`, 1 mip, and 256 estimated source bytes.
- Audited `/Engine/BasicShapes/Cube.Cube`; native readback reported 1 LOD, 54 vertices, 48 triangles, and 2 UV channels.
- Spawned `MCP_Phase4_VertexPaintActor` in the editor world and applied component override vertex colors to 54 vertices on LOD 0.
- Added `RHI` as a plugin dependency for GPU adapter and feature-level readback.
- Live Coding recompiled the updated Lab5E project plugin successfully.
- Analyzed `/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial`; native readback reported 2 expressions, risk `low`, and a graph heuristic score of 2.
- Captured `shader_complexity` and `shader_complexity_with_quad_overdraw` PNGs from the active Lab5E viewport at 1431x870.
- Captured a lightweight GPU audit: NVIDIA GeForce RTX 3090, SM6, active `lit` viewport, 39 actors, 19 StaticMeshComponents, and 54 PrimitiveComponents.

## Phase 5 - Animation Closure

Goal: close the remaining animation gaps rather than rebuilding what already works.

Already strong:

- Animation Blueprints.
- State machines, states, transitions, and sequence assignment.
- Blend-space nodes.
- AnimGraph slot insertion.
- IK Rig and IK Retargeter setup.
- Batch retargeting.
- Anim notify native handler exists in the plugin.

Slices:

- Add Python wrapper coverage for native `add_anim_notify` if missing from registered tools.
- `anim_create_montage`
- `anim_add_montage_slot`
- `anim_set_montage_section`
- `anim_add_branching_point`
- `control_rig_create`
- `control_rig_add_control`
- `control_rig_add_constraint`
- `control_rig_bake_to_sequence`

Validation:

- Locomotion AnimBP with state machine and slot.
- Montage with notify.
- Optional Control Rig asset creation and basic inspection.

## Phase 6 - Autonomous Verification Loop

Goal: give agents a repeatable plan-execute-verify loop.

Slices:

- `execution_journal_start`
- `execution_journal_log`
- `execution_journal_finish`
- `risk_evaluate_action`
- `pie_launch_session`
- `pie_stop_session`
- `pie_capture_log`
- `pie_simulate_input`
- `viewport_capture_screenshot`
- `viewport_compare_screenshot`

Later:

- Vision-language screenshot analysis integration.
- Automatic rollback/checkpoint suggestions for high-risk failures.

Validation:

- Agent builds a small gameplay slice, launches PIE, captures log/screenshot, and returns a journal.

## Phase 7 - Performance And Distribution

Goal: make the platform easier to run in production and CI.

Slices:

- Profile startup and most-used tool latency.
- Add command metadata registry to reduce routing drift between Python and C++.
- Investigate T3D or bulk Blueprint graph injection for large graph creation.
- Add headless build and smoke-test documentation.
- Evaluate optional single-binary or Go/Rust sidecar only after command metadata and test coverage are solid.

Validation:

- Startup time baseline.
- Repeatable CI smoke commands.
- Large Blueprint creation benchmark before and after bulk injection.

## Immediate Execution Queue

1. Phase 0: reconcile tool-count docs and add drift guard test.
2. Phase 1: add Niagara authoring support probe and schema wrappers.
3. Phase 1: implement the first native Niagara command in C++ only after live API probe confirms the safest editor path.
4. Phase 4 Slice 3: add shader complexity, overdraw, renderer viewmode, and GPU/performance audit helpers. Done.
5. Phase 5: close animation montage/control-rig gaps.

## Backlog Notes

- Keep historical command-level notes in git history rather than preserving stale workaround sections in this roadmap.
- When adding a tool, update tests first or in the same change.
- When adding a C++ bridge command, update Python wrapper, README tool category summary, and knowledge-base usage notes.
- Use `local-book-paths.json` only for short local retrieval from licensed PDFs; do not commit book text.
