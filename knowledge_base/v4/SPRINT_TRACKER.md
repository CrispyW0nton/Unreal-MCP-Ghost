# Unreal-MCP-Ghost — Sprint Tracker (V4)

> Last updated: 2026-04-16  
> Branch: `genspark_ai_developer`

---

## CURRENT STATE SNAPSHOT

| Metric | Value |
|--------|-------|
| MCP Tools | **378** (362 legacy + 16 V4 graph/mat tools) |
| C++ Commands | 119 |
| Python Tool Modules | 26 |
| Automated Tests | **137** (all passing) |
| Knowledge Base Docs | 32 (19 core + 13 v4/) |
| Graph Tools (bp_*) | **12** |
| Material Tools (mat_*) | **4** |

---

## PHASE 1 — STABILIZATION (Weeks 1-2) ✅ COMPLETE

| # | Task | Status |
|---|------|--------|
| 1.1 | Reconcile tool/module counts | ✅ 378 tools, 26 modules confirmed |
| 1.2 | Clean stale project-specific content | ✅ Removed EnclaveProject/Dantooine artefacts |
| 1.3 | Expand .gitignore | ✅ UE artefacts, IDE files, binary dumps |
| 1.4 | Update DEVELOPER_LOG.md | ✅ Generic plugin log, no project content |
| 1.5 | Expand test suite | ✅ 103 → 137 tests passing |
| 1.6 | V4 knowledge base integration | ✅ 13-doc handoff package in knowledge_base/v4/ |
| 1.7 | Integrate V4 SPRINT_TRACKER | ✅ (this file) |

---

## PHASE 2 — GRAPH-NATIVE SCRIPTING CORE (Weeks 3-5) ✅ BOOTSTRAP COMPLETE

### 2A: Blueprint Graph Operations

| Tool | Status | C++ Bridge |
|------|--------|------------|
| `bp_get_graph_summary` | ✅ **DONE** | `get_blueprint_nodes` |
| `bp_create_graph` | ✅ **DONE** | exec_python transactional |
| `bp_add_node` | ✅ **DONE** | 12+ C++ node commands |
| `bp_inspect_node` | ✅ **DONE** | `get_node_by_id` |
| `bp_connect_pins` | ✅ **DONE** | `connect_blueprint_nodes` |
| `bp_disconnect_pin` | ✅ **DONE** | `disconnect_blueprint_nodes` |
| `bp_set_pin_default` | ✅ **DONE** | `set_node_pin_value` |
| `bp_add_variable` | ✅ **DONE** | `add_blueprint_variable` |
| `bp_add_function` | ✅ **DONE** | exec_python transactional |
| `bp_remove_node` | ✅ **DONE** | `delete_blueprint_node` |
| `bp_compile` | ✅ **DONE** | `compile_blueprint` + `save_blueprint` |
| `bp_auto_format_graph` | ✅ **DONE** | `get_blueprint_nodes` + exec_python |
| `bp_diff_snapshot` | 🔲 Pending | — |

### 2B: Material Graph Operations

| Tool | Status | API |
|------|--------|-----|
| `mat_create_material` | ✅ **DONE** | `MaterialFactoryNew` |
| `mat_add_expression` | ✅ **DONE** | `MaterialEditingLibrary` |
| `mat_connect_expressions` | ✅ **DONE** | `MaterialEditingLibrary` |
| `mat_compile` | ✅ **DONE** | `MaterialEditingLibrary.recompile_material` |
| `mat_create_instance` | 🔲 Pending | `MaterialInstanceConstantFactoryNew` |
| `mat_set_parameter` | 🔲 Pending | `MaterialInstanceDynamic` / `EditorAssetLibrary` |

### 2C: End-to-End Demo Workflows

| Demo | Status |
|------|--------|
| Demo A — BeginPlay→PrintString→Branch + variable + compile | 🔲 Needs live UE test |
| Demo B — Function with params, variable get/set, compile | 🔲 Needs live UE test |
| Demo C — Material: PBR setup (Texture × Normal × Roughness) | 🔲 Needs live UE test |
| Demo D — Health system Blueprint (full gameplay pattern) | 🔲 Pending |
| Demo E — Master material + 3 instances with params | 🔲 Pending |

### 2D: Phase 2 Exit Criteria

- [x] All 12 bp_* tools implemented and tested
- [x] All 4 mat_* tools implemented and tested
- [x] StructuredResult enforced on all 16 new tools
- [x] 137/137 tests passing
- [ ] Demo A proven end-to-end with live UE instance
- [ ] Demo C proven end-to-end with live UE instance
- [ ] bp_diff_snapshot implemented
- [ ] mat_create_instance + mat_set_parameter implemented

---

## PHASE 3 — PROJECT INTELLIGENCE (Weeks 6-8)

| Tool | Status | Source |
|------|--------|--------|
| `project_find_assets` | 🔲 Pending | Asset Registry API |
| `project_get_references` | 🔲 Pending | UnrealCopilot pattern |
| `project_get_dependency_chain` | 🔲 Pending | Asset Registry |
| `project_get_dirty_packages` | 🔲 Pending | Editor API |
| `cpp_analyze_class` | 🔲 Pending | tree-sitter |
| `cpp_find_hierarchy` | 🔲 Pending | UnrealCopilot |
| `cpp_detect_patterns` | 🔲 Pending | unreal-analyzer-mcp pattern |
| `cpp_search_code` | 🔲 Pending | — |
| `xref_trace_chain` | 🔲 Pending | UnrealCopilot |
| `project_context_summary` | 🔲 Pending | — |

---

## PHASE 4 — VERIFICATION & TESTING (Weeks 8-10)

| Feature | Status |
|---------|--------|
| Auto-compile after each mutation | 🔲 Pending |
| Capture UE Output Log in StructuredResult | 🔲 Pending |
| Produce before/after graph diff summaries | 🔲 Pending (`bp_diff_snapshot`) |
| UE Automation test integration | 🔲 Pending |
| Loop protection for agent scripting | 🔲 Pending |
| Viewport screenshot capture | 🔲 Pending |

---

## PHASE 5 — SOURCE-CONTROL-AWARE AUTONOMY (Weeks 10-12)

| Feature | Status |
|---------|--------|
| Detect checkout state | 🔲 Pending |
| Auto-checkout before edit | 🔲 Pending |
| Conflict detection | 🔲 Pending |
| Intelligent dirty-package saving | 🔲 Pending |
| Changelog generation | 🔲 Pending |
| Hot-reload awareness | 🔲 Pending |

---

## PHASE 6 — SIGNATURE WORKFLOWS (Weeks 12-16)

| Workflow | Status |
|----------|--------|
| Full health system Blueprint from prompt | 🔲 Pending |
| Blueprint repair (diagnose + fix broken graph) | 🔲 Pending |
| Character import → IK retarget pipeline | 🔲 Pending |
| Master material generation | 🔲 Pending |
| Project subsystem analysis | 🔲 Pending |
| KotOR → UE5 pipeline | 🔲 Pending |

---

## IMMEDIATE NEXT TASKS (Priority-ordered)

1. **Demo A end-to-end** — Run Demo Workflow A with live UE instance to validate
   all 12 bp_* tools work together. This is the Phase 2 completion gate.

2. **`bp_diff_snapshot`** — Before/after JSON graph snapshot + diff output.
   Needed for agent self-verification of each edit step.

3. **`mat_create_instance`** — Create `MaterialInstanceConstant` from parent material.
   The natural complement to `mat_create_material`.

4. **`mat_set_parameter`** — Set scalar/vector/texture params on material instances.
   Needed to make material instances useful.

5. **StructuredResult retrofit** — 360 legacy tools still return plain dicts.
   Batch-wrap the top 50 most-used tools (node_tools, blueprint_tools, editor_tools).

6. **Test count to ≥165** — V4 validation matrix specifies 165 test scenarios.
   Currently at 137. Need ~28 more tests covering edge cases and E2E scenarios.

---

## METRICS TRAJECTORY

| Metric | Phase 1 ✅ | Phase 2 (now) | Phase 3 target | Phase 6 target |
|--------|-----------|---------------|----------------|----------------|
| MCP Tools | 378 | 378 | ~388 | ~420 |
| C++ Commands | 119 | 119 | ~125 | ~135 |
| Automated Tests | 137 | 137 | ≥165 | ≥200 |
| StructuredResult coverage | ~0.4% | ~4% | ~15% | ~80% |
| Graph tools (bp_*+mat_*) | 16 | 16 | 20 | 25 |
| Live E2E demos validated | 0 | 0 | 2 | 5 |
