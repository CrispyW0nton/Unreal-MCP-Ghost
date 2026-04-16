# Validation Test Matrix V4

> **Date**: 2026-04-16 | **Purpose**: Define comprehensive test scenarios across all phases

---

## Test Philosophy

1. **Every mutating tool gets a smoke test** (no exceptions)
2. **Every mutating tool gets a failure test** (invalid input → structured error)
3. **Every transactional tool gets an undo test** (mutate → undo → verify reverted)
4. **Every phase has integration tests** (multi-tool workflows)
5. **Tests must be CI-compatible** (no manual editor interaction required)

---

## Phase 1: Stabilization Tests (Target: 80+)

### Existing Tests to Verify (48 from PR #15)
| Category | Test Count | Status |
|---|---|---|
| Import tools smoke tests | ~16 | Verify pass |
| Import tools failure tests | ~16 | Verify pass |
| Exec substrate tests | ~8 | Verify pass |
| Reflection tool tests | ~8 | Verify pass |

### New Tests Needed (32+)
| ID | Test | Type | Tool(s) |
|---|---|---|---|
| S1.01 | All 362 tools return StructuredResult | Smoke | All |
| S1.02 | StructuredResult has required fields | Unit | Schema validation |
| S1.03 | ScopedEditorTransaction wraps all mutations | Integration | All mutating tools |
| S1.04 | ScopedSlowTask on batch_import_folder | Smoke | batch_import_folder |
| S1.05 | E2E: folder scan → dry-run → real import | Integration | scan_export_folder, batch_import_folder |
| S1.06 | E2E: character import → skeleton check | Integration | import_folder_as_character |
| S1.07 | E2E: GhostRigger health → export → import | Integration | ghostrigger_* tools |
| S1.08 | E2E: safe exec → transact → progress | Integration | ue_exec_safe, ue_exec_transact, ue_exec_progress |
| S1.09 | E2E: reflection → describe → find | Integration | ue_reflect_class, ue_describe_asset, ue_find_assets_by_class |
| S1.10 | Invalid blueprint_path → structured error | Failure | Multiple tools |
| S1.11 | Invalid asset path → structured error | Failure | import_texture, import_static_mesh |
| S1.12 | Missing file → structured error with message | Failure | All import tools |
| S1.13 | GhostRigger offline → graceful failure | Failure | ghostrigger_health |
| S1.14 | Unreal bridge disconnected → structured error | Failure | Any tool |
| S1.15 | Tool count matches README (362 / 24) | Unit | Registration check |

---

## Phase 2: Graph Scripting Tests (Target: 40+)

### Blueprint Graph Tests
| ID | Test | Type | Tool(s) |
|---|---|---|---|
| G2.01 | Create event graph in new BP | Smoke | bp_create_graph |
| G2.02 | Create function graph with params | Smoke | bp_create_graph, bp_add_function |
| G2.03 | Add PrintString node at position | Smoke | bp_add_node |
| G2.04 | Add Branch node | Smoke | bp_add_node |
| G2.05 | Add Event BeginPlay node | Smoke | bp_add_node |
| G2.06 | Add Variable Get node | Smoke | bp_add_node |
| G2.07 | Inspect node returns all pins | Smoke | bp_inspect_node |
| G2.08 | Connect exec pins | Smoke | bp_connect_pins |
| G2.09 | Connect data pins (float→float) | Smoke | bp_connect_pins |
| G2.10 | Connect incompatible pins → error | Failure | bp_connect_pins |
| G2.11 | Disconnect specific pin | Smoke | bp_disconnect_pin |
| G2.12 | Set pin default value | Smoke | bp_set_pin_default |
| G2.13 | Add member variable (float) | Smoke | bp_add_variable |
| G2.14 | Add member variable (replicated) | Smoke | bp_add_variable |
| G2.15 | Compile clean BP → success | Smoke | bp_compile |
| G2.16 | Compile broken BP → structured errors | Failure | bp_compile |
| G2.17 | Graph summary serialization | Smoke | bp_get_graph_summary |
| G2.18 | Auto-format graph layout | Smoke | bp_auto_format_graph |
| G2.19 | Diff snapshot capture + compare | Smoke | bp_diff_snapshot |
| G2.20 | Remove node by GUID | Smoke | bp_remove_node |
| G2.21 | Remove nonexistent node → error | Failure | bp_remove_node |
| G2.22 | Undo: add node → undo → node gone | Undo | bp_add_node |
| G2.23 | Undo: connect → undo → disconnected | Undo | bp_connect_pins |
| G2.24 | Undo: add variable → undo → removed | Undo | bp_add_variable |

### Material Graph Tests
| ID | Test | Type | Tool(s) |
|---|---|---|---|
| M2.01 | Create new material | Smoke | mat_create_material |
| M2.02 | Add TextureSample expression | Smoke | mat_add_expression |
| M2.03 | Add Multiply expression | Smoke | mat_add_expression |
| M2.04 | Connect expression to BaseColor | Smoke | mat_connect_expressions |
| M2.05 | Create material instance | Smoke | mat_create_instance |
| M2.06 | Set scalar parameter | Smoke | mat_set_parameter |
| M2.07 | Set vector parameter | Smoke | mat_set_parameter |
| M2.08 | Compile clean material → success | Smoke | mat_compile |
| M2.09 | Compile broken material → errors | Failure | mat_compile |
| M2.10 | Undo: add expression → undo → removed | Undo | mat_add_expression |

### Integration Tests (Skills)
| ID | Test | Type | Skill |
|---|---|---|---|
| I2.01 | Create Health System BP from scratch | Integration | Full workflow |
| I2.02 | Create PBR Master Material + 3 instances | Integration | Full workflow |
| I2.03 | Wire Input Action to Character | Integration | Full workflow |
| I2.04 | Graph summary → verify serialization accuracy | Integration | bp_get_graph_summary |

---

## Phase 3: Project Intelligence Tests (Target: 20+)

| ID | Test | Type | Tool(s) |
|---|---|---|---|
| P3.01 | Find all StaticMesh assets | Smoke | project_find_assets |
| P3.02 | Find assets by path | Smoke | project_find_assets |
| P3.03 | Get incoming references | Smoke | project_get_references |
| P3.04 | Get outgoing references | Smoke | project_get_references |
| P3.05 | Get dependency chain | Smoke | project_get_dependency_chain |
| P3.06 | List dirty packages | Smoke | project_get_dirty_packages |
| P3.07 | Analyze C++ class | Smoke | cpp_analyze_class |
| P3.08 | Find class hierarchy | Smoke | cpp_find_hierarchy |
| P3.09 | Detect UE patterns | Smoke | cpp_detect_patterns |
| P3.10 | Search code with context | Smoke | cpp_search_code |
| P3.11 | Cross-reference trace | Integration | xref_trace_chain |
| P3.12 | Project context summary | Smoke | project_context_summary |
| P3.13 | Nonexistent asset → structured error | Failure | project_get_references |
| P3.14 | Invalid C++ path → structured error | Failure | cpp_analyze_class |

---

## Phase 4: Verification Tests (Target: 15+)

| ID | Test | Type | Capability |
|---|---|---|---|
| V4.01 | Auto-compile triggers after BP edit | Integration | Auto-compile |
| V4.02 | Output log captured correctly | Smoke | Log capture |
| V4.03 | Diff summary after add node | Smoke | Diff |
| V4.04 | Diff summary after add variable | Smoke | Diff |
| V4.05 | Run targeted Automation Test | Integration | UE Test integration |
| V4.06 | Loop protection triggers at limit | Smoke | Loop protection |
| V4.07 | Result size limit enforced | Smoke | Size limits |
| V4.08 | Execution timeout fires | Smoke | Timeouts |
| V4.09 | Viewport screenshot captured | Smoke | Visual verification |

---

## Phase 5: Source Control Tests (Target: 10+)

| ID | Test | Type | Capability |
|---|---|---|---|
| SC5.01 | Query checkout state | Smoke | Checkout detection |
| SC5.02 | Auto-checkout on modification | Integration | Auto-checkout |
| SC5.03 | Lock conflict detected | Failure | Conflict detection |
| SC5.04 | Save dirty packages | Smoke | Intelligent save |
| SC5.05 | Changelist summary generation | Smoke | Summary |
| SC5.06 | Hot-reload detection | Integration | Hot-reload |

---

## Coverage Targets by Phase

| Phase | New Tests | Cumulative Total | Coverage Target |
|---|---|---|---|
| Phase 1 (Stabilization) | 32 | 80 | 100% of existing tools have smoke tests |
| Phase 2 (Graph Scripting) | 40 | 120 | 100% of graph tools have smoke + failure + undo |
| Phase 3 (Intelligence) | 20 | 140 | 100% of intelligence tools have smoke + failure |
| Phase 4 (Verification) | 15 | 155 | All verification capabilities tested |
| Phase 5 (Source Control) | 10 | 165 | All SC operations tested |
| **Total** | **117** | **165** | Production-ready |

---

## Test Infrastructure Requirements

1. **Test runner**: Python `pytest` compatible (current approach)
2. **UE connection**: Tests must handle "bridge not connected" gracefully
3. **Cleanup**: Every test creates and destroys its own assets
4. **Isolation**: Tests must not depend on execution order
5. **CI-friendly**: No manual editor interaction required
6. **Timing**: Smoke tests < 2 seconds each, integration tests < 10 seconds each
