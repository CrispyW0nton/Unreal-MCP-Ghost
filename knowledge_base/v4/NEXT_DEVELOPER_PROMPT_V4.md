# Unreal-MCP-Ghost — Developer Session Prompt V4

> **Date**: 2026-04-16
> **Branch**: `genspark_ai_developer`
> **Repo**: https://github.com/CrispyW0nton/Unreal-MCP-Ghost
> **Related**: https://github.com/CrispyW0nton/GDeveloper | https://github.com/CrispyW0nton/Kotor-3D-Model-Converter

---

## 🎯 Mission

You are the AI co-architect for **Unreal-MCP-Ghost**, the most capable AI-driven Unreal Engine 5 plugin. Your role is to keep development focused, ensure production-grade architecture, and research open-source tools/code to extend capabilities.

**The product identity is: "The best AI-native scripting and graph-authoring layer for Unreal Engine."**

Imports, GhostRigger, model conversion, retargeting, and material creation are important but serve as **inputs and outputs of a dominant scripting layer**, not as the main identity.

---

## 📊 Current State (Post-PR #15)

| Metric | Value |
|---|---|
| MCP Tools | 362 |
| Modules | 24 |
| C++ Plugin Commands | 119 |
| Transports | stdio, SSE, streamable-HTTP |
| Tests | 48 smoke + failure tests |
| Skills | 7 SKILL.md files |
| Safe Execution | `ue_exec_safe`, `ue_exec_transact`, `ue_exec_progress` |
| Reflection | 8 tools (class/property/method/asset/selection/log/effects) |
| Result Schema | `{success, stage, message, outputs, warnings, errors, log_tail}` |
| Import Pipeline | Texture, StaticMesh, SkeletalMesh, folder batch, character import |
| GhostRigger Bridge | 10 IPC tools (health, ping, open, list, read, export, import) |

### What's Working Well
- Safe execution substrate aligned with Epic's Python scripting guidelines
- Reflection + diagnostics enabling closed-loop agent behavior
- Skills library with preconditions, failure modes, validation steps
- Structured result schema across mutating tools
- Multi-transport support (stdio for local, SSE for remote)

### What Needs Attention
- Blueprint/material graph authoring is not yet granular (no atomic node/pin/connection operations)
- Project intelligence is minimal (no asset registry queries, no reference tracing, no C++ analysis)
- Verification is ad-hoc (no automatic compile-after-edit, no diff summaries)
- Source control awareness is absent
- Graph readability/auto-formatting not addressed
- GDeveloper MCP config has a client-side ID bug (`mcp-${Date.now()}` in MCPServersPanel.tsx)

---

## 🏗️ Architecture Overview

```
AI Client (Claude Desktop / GDeveloper / GenSpark)
    ↓ stdio | SSE | streamable-HTTP
Python MCP Server (unreal_mcp_server.py)
    ↓ TCP JSON (port 55557)
C++ UnrealMCP Plugin (Editor Subsystem)
    ↓ UE5 Reflection / Editor APIs
Unreal Engine 5 Editor
```

Key files:
- `unreal_mcp_server/unreal_mcp_server.py` — main server, tool registration
- `unreal_mcp_server/tools/` — 24 tool modules
- `unreal_mcp_server/tools/exec_substrate.py` — safe execution layer
- `unreal_mcp_server/tools/reflection_tools.py` — reflection/diagnostics
- `unreal_mcp_server/skills/` — 7 SKILL.md files
- `unreal_mcp_server/tests/` — 48 tests
- `Plugins/UnrealMCP/` — C++ plugin source
- `knowledge_base/` — 13+ reference docs from UE5 textbooks

---

## 🚀 V4 Roadmap — Phased Priorities

### Phase 1: Stabilization Sprint (CURRENT — weeks 1-2)
**Goal**: Every mutating tool is safe, structured, and tested.

- [ ] Reconcile tool count: verify 362 tools / 24 modules matches actual registration
- [ ] Ensure ALL mutating tools return StructuredResult schema
- [ ] Wrap remaining asset/blueprint mutations in `ScopedEditorTransaction`
- [ ] Add `ScopedSlowTask` to batch operations (batch_import_folder, etc.)
- [ ] Expand test coverage: target 80+ tests (smoke + failure + edge cases)
- [ ] Fix GDeveloper MCPServersPanel.tsx ID-sync bug
- [ ] End-to-end verification scenarios:
  - A: folder scan → dry-run batch → real batch import
  - B: character import → skeleton validation
  - C: GhostRigger health → export → import to UE5
  - D: safe exec → transact → progress reporting
  - E: reflection → asset describe → find by class

### Phase 2: Graph-Native Scripting Core (weeks 3-5)
**Goal**: Best-in-class AI Blueprint/material graph authoring.

**Atomic Graph Operations** (inspired by flopperam/unreal-engine-mcp):
- [ ] `bp_create_graph` — create new event/function/macro graph
- [ ] `bp_add_node` — add node by class with position (X,Y)
- [ ] `bp_remove_node` — remove node by GUID
- [ ] `bp_inspect_node` — get node details, pins, connections
- [ ] `bp_connect_pins` — connect output pin to input pin by name
- [ ] `bp_disconnect_pin` — break specific connection
- [ ] `bp_set_pin_default` — set default value on unconnected input
- [ ] `bp_add_variable` — add member variable with type/category/flags
- [ ] `bp_add_function` — add function graph with signature
- [ ] `bp_compile` — compile Blueprint, return errors/warnings
- [ ] `bp_diff_snapshot` — capture before/after state for comparison
- [ ] `bp_get_graph_summary` — serialize graph to compact AI-readable form

**Graph Layout & Readability** (inspired by howaajin/graphformatter):
- [ ] `bp_auto_format_graph` — invoke graph layout algorithm
- [ ] Enforce consistent spacing (300-400 X units between nodes)
- [ ] Comment-based node grouping
- [ ] Reroute node insertion for long connections

**Material Graph Operations**:
- [ ] `mat_create_material` — create new material asset
- [ ] `mat_add_expression` — add material expression node
- [ ] `mat_connect_expressions` — wire expression outputs to inputs
- [ ] `mat_create_instance` — create material instance from parent
- [ ] `mat_set_parameter` — set scalar/vector/texture parameter
- [ ] `mat_compile` — compile material, return errors

**Higher-Order Skills**:
- [ ] SKILL: "Create Health System Blueprint" (nodes, variables, events, compile)
- [ ] SKILL: "Create Master Material + Instances" (material, params, instances)
- [ ] SKILL: "Wire Input Action to Character" (input, BP nodes, compile)

### Phase 3: Project Intelligence (weeks 6-8)
**Goal**: Ghost understands the whole project, not just individual assets.

**Asset Registry Integration**:
- [ ] `project_find_assets` — query by class, path, tags
- [ ] `project_get_references` — incoming/outgoing asset references
- [ ] `project_get_dependency_chain` — trace full dependency tree
- [ ] `project_search_by_tag` — search by AssetRegistrySearchable properties
- [ ] `project_get_dirty_packages` — list unsaved assets

**C++ Source Analysis** (inspired by UnrealCopilot + unreal-analyzer-mcp):
- [ ] `cpp_analyze_class` — extract properties, methods, inheritance
- [ ] `cpp_find_hierarchy` — map class hierarchy tree
- [ ] `cpp_detect_patterns` — identify UPROPERTY/UFUNCTION/UCLASS usage
- [ ] `cpp_search_code` — context-aware code search

**Cross-Domain Intelligence**:
- [ ] `xref_trace_chain` — Blueprint ↔ C++ ↔ Asset reference chains
- [ ] `xref_find_blueprint_for_class` — which BP wraps which C++ class
- [ ] `project_context_summary` — high-level project overview for agent context

### Phase 4: Verification & Testing (weeks 8-10)
**Goal**: Every edit is verifiable; agent can prove correctness.

- [ ] Auto-compile after every Blueprint/material mutation
- [ ] Post-operation output log capture and error extraction
- [ ] Pre/post operation diff summaries
- [ ] Integration with UE Automation Test Framework
- [ ] Loop protection: max iterations, result-size limits, execution timeouts
- [ ] Screenshot/viewport capture for visual verification

### Phase 5: Source-Control-Aware Autonomy (weeks 10-12)
**Goal**: Safe multi-asset editing on real production projects.

- [ ] Detect asset checkout state before editing
- [ ] Auto-checkout on modification (respecting UE settings)
- [ ] Lock conflict detection and user prompting
- [ ] Save dirty packages intelligently
- [ ] Generate operation summaries suitable for changelists/commit messages
- [ ] Content hot-reload awareness

### Phase 6: Signature Workflows (weeks 12-16)
**Goal**: High-level AI engineer capabilities.

- [ ] "Create gameplay system from prompt" (full BP + compile + test)
- [ ] "Repair broken Blueprint" (diagnose errors → fix → recompile)
- [ ] "Import character → IK retarget setup" (import → IKRig → chains → auto-FBIK)
- [ ] "Generate master material + instances from description"
- [ ] "Analyze project subsystem → recommend optimizations"
- [ ] "Full KotOR → UE5 pipeline" (GhostRigger → import → material → retarget)

---

## 🔑 Key Open-Source Repos to Reference

### Tier 1 — Study deeply, borrow patterns
| Repo | Why It Matters |
|---|---|
| [flopperam/unreal-engine-mcp](https://github.com/flopperam/unreal-engine-mcp) | Best BP graph scripting benchmark: atomic node ops, autonomous workflows, live compile |
| [syan2018/UnrealCopilot](https://github.com/syan2018/UnrealCopilot) | Best project intelligence: skill system, tree-sitter C++ analysis, cross-domain refs, transactional BP editing |
| [cgerchenhp/UE_TAPython_Plugin_Release](https://github.com/cgerchenhp/UE_TAPython_Plugin_Release) | Best rapid editor tooling: 200+ APIs, hot-reload Python+JSON UI, editor modes, viewport interaction |
| [JonasReich/OpenUnrealUtilities](https://github.com/JonasReich/OpenUnrealUtilities) | Best production hardening: testing helpers, frame scheduler, automation macros |

### Tier 2 — Solve specific gaps
| Repo | Gap It Fills |
|---|---|
| [kiwi-lang/uetools](https://github.com/kiwi-lang/uetools) | CLI build/test/cook/launch automation |
| [RedpointGames/uet](https://github.com/RedpointGames/uet) | BuildGraph distribution, cross-platform builds, CI |
| [howaajin/graphformatter](https://github.com/howaajin/graphformatter) | Graph layout algorithms for readable AI-generated graphs |
| [ayeletstudioindia/unreal-analyzer-mcp](https://github.com/ayeletstudioindia/unreal-analyzer-mcp) | C++ hierarchy analysis, pattern detection, API docs |
| [TREE-Ind/UnrealGPT](https://github.com/TREE-Ind/UnrealGPT) | Scene summary + screenshot context, loop protection, timeouts |
| [protospatial/NodeToCode](https://github.com/protospatial/NodeToCode) | Graph serialization to compact AI-readable structured form |

### Tier 3 — Inspiration
| Repo | Idea |
|---|---|
| [ZackBradshaw/Bluepy](https://github.com/ZackBradshaw/Bluepy) | AI-native Blueprint node generation UX |
| [CoplayDev/unity-mcp](https://github.com/CoplayDev/unity-mcp) | Reflection, batch execution, profiling, multi-instance routing |
| [rdeioris/glTFRuntime](https://github.com/rdeioris/glTFRuntime) | Modular runtime asset loading |
| [xavier150/Blender-For-UnrealEngine-Addons](https://github.com/xavier150/Blender-For-UnrealEngine-Addons) | DCC-to-UE pipeline automation |

---

## 🔍 UE Engine Source Areas to Study

| Module / System | Why | Doc Link |
|---|---|---|
| KismetCompiler | How BP edits become compiled classes | [FKismetCompilerContext](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/KismetCompiler/FKismetCompilerContext) |
| BlueprintGraph | Node-level graph authoring primitives | [BlueprintGraph API](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/BlueprintGraph) |
| Asset Registry | Project-wide asset discovery & dependency tracing | [Asset Registry](https://dev.epicgames.com/documentation/en-us/unreal-engine/asset-registry-in-unreal-engine) |
| Interchange | File-format-agnostic async import pipeline | [Interchange](https://dev.epicgames.com/documentation/unreal-engine/importing-assets-using-interchange-in-unreal-engine) |
| Automation Test Framework | Smoke/feature/content tests, CQTest | [Automation Testing](https://dev.epicgames.com/documentation/unreal-engine/automation-test-framework-in-unreal-engine) |
| Python Editor Scripting | Official safety contract for AI editor ops | [Python Scripting](https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python) |
| IK Rig Python API | Automated retarget chain + FBIK setup | [IK Rig Python](https://dev.epicgames.com/documentation/unreal-engine/using-python-to-create-and-edit-ik-rigs-in-unreal-engine) |
| Source Control | Checkout, diff, lock, hot-reload awareness | [Source Control](https://dev.epicgames.com/documentation/unreal-engine/source-control-in-unreal-engine) |

---

## ⚡ Unreal Python Safety Contract (non-negotiable)

1. **Never** use `os`, `shutil`, or native Python file ops on `.uasset` files — always use `unreal.EditorAssetLibrary` or `unreal.AssetTools`
2. **Always** use `set_editor_property()` / `get_editor_property()` instead of direct attribute access
3. **Always** wrap mutations in `unreal.ScopedEditorTransaction` for undo history
4. **Always** use `unreal.ScopedSlowTask` for batch/long-running operations
5. **Always** use `unreal.log()` / `unreal.log_warning()` / `unreal.log_error()` for output
6. **Remember**: Python scripts run only in the Unreal Editor, not in packaged builds

---

## 📋 Immediate Action Items (Start Here)

1. **Merge PR #15** if not already merged — reconcile final tool/module count
2. **Run full test suite** — verify all 48 tests pass, identify gaps
3. **Pick Phase 2 first deliverable**: implement `bp_add_node` + `bp_connect_pins` + `bp_compile` as the minimal graph-editing primitive set
4. **Study flopperam's blueprint-graph-guide.md** for pin naming, spacing, compile patterns
5. **Study UnrealCopilot's ARCHITECTURE.md** for skill system and transactional editing patterns
6. **Fix GDeveloper ID bug** — make `api.addMCPServer` return backend-authoritative ID
7. **Add `bp_get_graph_summary`** — compact serialized graph for AI reasoning (inspired by NodeToCode)

---

## 🧭 Decision Framework

When deciding what to build next, ask:
1. Does this make Ghost better at **scripting** Unreal Engine? → Priority
2. Does this make Ghost's edits more **verifiable**? → Priority
3. Does this make Ghost **understand the project** better? → Priority
4. Does this add a new import/export format? → Defer unless blocking a scripting workflow
5. Does this add breadth without depth? → Reject

---

## 📚 Files in This Package

| File | Purpose |
|---|---|
| NEXT_DEVELOPER_PROMPT_V4.md | This file — session startup prompt |
| ROADMAP_V4.md | Phased roadmap with success criteria |
| DEEP_RESEARCH_REPORT_V4.md | Full research findings on repos + engine areas |
| REPO_PRIORITIZATION_MATRIX_V4.md | Tiered repo assessment with action items |
| ENGINE_SOURCE_STUDY_GUIDE_V4.md | What to study in UE source and why |
| GRAPH_SCRIPTING_SPEC_V4.md | Technical spec for Phase 2 graph operations |
| VALIDATION_TEST_MATRIX_V4.md | Test scenarios and coverage targets |
| API_REFERENCE_CHEATSHEET.md | Consolidated API reference (carried forward) |
| ARCHITECTURE_BLUEPRINT.md | Architecture documentation (carried forward) |
| GHOSTRIGGER_INTEGRATION_SPEC.md | GhostRigger IPC spec (carried forward) |
| NATIVE_MODE_ENHANCEMENT_SPEC.md | Native mode spec (carried forward) |
| SPRINT_TRACKER.md | Sprint tracking (carried forward) |
