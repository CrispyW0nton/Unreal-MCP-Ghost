# Unreal-MCP-Ghost — Roadmap V4

> **Date**: 2026-04-16 | **Branch**: `genspark_ai_developer`

---

## Strategic Direction

**Product Identity**: The best AI-native scripting and graph-authoring layer for Unreal Engine.

**Principle**: Depth over breadth. Master Blueprint/material scripting, project intelligence, and verification before expanding into more import formats or peripheral features.

---

## Phase 1: Stabilization Sprint (Weeks 1-2)

### Objective
Every mutating tool is safe, returns structured results, participates in undo, and has test coverage.

### Deliverables
| # | Task | Success Criteria |
|---|---|---|
| 1.1 | Reconcile tool/module count | `unreal_mcp_server.py` registration matches README (362 / 24) |
| 1.2 | StructuredResult schema enforcement | All 362 tools return `{success, stage, message, outputs, warnings, errors, log_tail}` |
| 1.3 | Transaction wrapping | All asset/BP-mutating tools use `ScopedEditorTransaction` |
| 1.4 | SlowTask wrapping | All batch operations use `ScopedSlowTask` |
| 1.5 | Test expansion | 80+ tests (smoke + failure + edge), CI-compatible |
| 1.6 | E2E verification scenarios | 5 defined scenarios all pass (import, character, GhostRigger, exec, reflection) |
| 1.7 | GDeveloper ID bug fix | `MCPServersPanel.tsx` uses backend-authoritative server IDs |

### Exit Criteria
- Zero test failures on clean checkout
- All mutating tools produce undo-able transactions
- GDeveloper can discover tools via SSE connection

---

## Phase 2: Graph-Native Scripting Core (Weeks 3-5)

### Objective
Best-in-class AI authoring of Blueprint and material graphs via atomic + higher-order tools.

### 2A: Atomic Blueprint Graph Operations
| Tool | Description | Reference |
|---|---|---|
| `bp_create_graph` | Create event/function/macro graph | flopperam |
| `bp_add_node` | Add K2Node by class at (X,Y) position | flopperam, BlueprintGraph API |
| `bp_remove_node` | Remove node by GUID | — |
| `bp_inspect_node` | Get node details, all pins, all connections | UnrealCopilot |
| `bp_connect_pins` | Connect output→input by pin name | flopperam guide |
| `bp_disconnect_pin` | Break specific pin connection | — |
| `bp_set_pin_default` | Set default value on unconnected input | flopperam guide |
| `bp_add_variable` | Add member variable with type, category, flags | UnrealCopilot |
| `bp_add_function` | Add function graph with parameter signature | — |
| `bp_compile` | Compile BP, return structured error/warning list | KismetCompiler |
| `bp_diff_snapshot` | Capture and compare before/after graph state | — |
| `bp_get_graph_summary` | Serialize graph to compact AI-readable JSON | NodeToCode inspiration |

### 2B: Graph Layout & Readability
| Tool | Description | Reference |
|---|---|---|
| `bp_auto_format_graph` | Invoke layered graph layout algorithm | GraphFormatter |
| Spacing rules | 300-400 X units between nodes, aligned Y for related nodes | flopperam guide |
| Comment grouping | Auto-create comment blocks around logical groups | GraphFormatter wiki |
| Reroute insertion | Insert reroute nodes for connections > threshold length | GraphFormatter tips |

### 2C: Material Graph Operations
| Tool | Description |
|---|---|
| `mat_create_material` | Create new material asset |
| `mat_add_expression` | Add material expression node (TextureSample, Multiply, etc.) |
| `mat_connect_expressions` | Wire expression output→input |
| `mat_create_instance` | Create MaterialInstanceConstant from parent |
| `mat_set_parameter` | Set scalar/vector/texture parameter value |
| `mat_compile` | Compile material, return errors |

### 2D: Higher-Order Skills
| Skill | Tools Used | Validation |
|---|---|---|
| "Create Health System BP" | bp_add_variable, bp_add_node (×N), bp_connect_pins (×N), bp_compile | Compiles clean, variables exist, event graph wired |
| "Create Master Material + Instances" | mat_create_material, mat_add_expression (×N), mat_connect_expressions, mat_create_instance | Material compiles, instances inherit params |
| "Wire Input Action to Character" | bp_add_node (InputAction), bp_connect_pins, bp_compile | Input event fires on test |

### Exit Criteria
- Agent can create a complete Health System Blueprint from prompt with zero manual editing
- Agent can create a PBR master material with texture inputs and 3 instances
- All graph mutations produce undo-able transactions
- Graph layout produces readable, non-overlapping node placement

---

## Phase 3: Project Intelligence (Weeks 6-8)

### Objective
Ghost understands the whole project — assets, code, references, and dependencies.

### Deliverables
| Tool | Description | Source |
|---|---|---|
| `project_find_assets` | Query Asset Registry by class/path/tags | UE Asset Registry API |
| `project_get_references` | Incoming/outgoing asset references | UnrealCopilot |
| `project_get_dependency_chain` | Full dependency tree | Asset Registry |
| `project_get_dirty_packages` | List unsaved assets | Editor API |
| `cpp_analyze_class` | Extract properties, methods, inheritance from C++ | tree-sitter / unreal-analyzer-mcp |
| `cpp_find_hierarchy` | Map class inheritance tree | UnrealCopilot |
| `cpp_detect_patterns` | Identify UPROPERTY/UFUNCTION/UCLASS usage | unreal-analyzer-mcp |
| `cpp_search_code` | Context-aware code search | unreal-analyzer-mcp |
| `xref_trace_chain` | BP ↔ C++ ↔ Asset cross-reference chains | UnrealCopilot |
| `project_context_summary` | High-level project overview for agent context window | — |

### Exit Criteria
- Agent can answer "What references this asset?" and "What C++ class backs this Blueprint?"
- Agent can produce a project overview suitable for its own context window
- C++ analysis works on user project source and optionally on engine source

---

## Phase 4: Verification & Testing (Weeks 8-10)

### Objective
Every nontrivial edit is verifiable; the agent can prove correctness.

### Deliverables
| Capability | Description |
|---|---|
| Auto-compile | Automatic `bp_compile` / `mat_compile` after every graph mutation |
| Log capture | Post-operation output log extraction and error classification |
| Diff summaries | Pre/post operation structured diff |
| UE Test integration | Trigger targeted Automation Tests and report results |
| Loop protection | Max iteration count, result-size limits, execution timeouts |
| Visual verification | Viewport screenshot capture for agent visual reasoning |

### Exit Criteria
- Agent receives structured compile results after every BP/mat edit
- Failed operations produce actionable error context (node, pin, type mismatch)
- Agent can run a targeted Automation Test and interpret pass/fail

---

## Phase 5: Source-Control-Aware Autonomy (Weeks 10-12)

### Deliverables
| Capability | Description |
|---|---|
| Checkout detection | Query asset checkout state before editing |
| Auto-checkout | Respect "Automatically Checkout on Asset Modification" setting |
| Lock conflict detection | Detect and surface lock conflicts to user |
| Intelligent save | Save dirty packages with appropriate prompting |
| Changelist summary | Generate structured operation summaries for commit messages |
| Hot-reload awareness | Detect and respond to content hot-reload events |

---

## Phase 6: Signature Workflows (Weeks 12-16)

### Deliverables
| Workflow | Components |
|---|---|
| "Create gameplay system from prompt" | Project analysis → BP creation → graph authoring → compile → test |
| "Repair broken Blueprint" | Error diagnosis → targeted fix → recompile → verify |
| "Import character → IK retarget" | Import → IKRig creation → auto retarget chains → auto FBIK → validate |
| "Generate master material + instances" | Material creation → expression wiring → instance generation → parameter setup |
| "Full KotOR → UE5 pipeline" | GhostRigger export → import → material assignment → retarget → validate |
| "Project health audit" | Asset scan → dependency analysis → broken ref detection → fix recommendations |

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Graph editing API instability across UE versions | High | Version-gate graph operations, test on UE 5.4+ |
| Agent graph edits produce uncompilable BPs | High | Always auto-compile + return errors; never leave dirty state |
| Tool count growth without test coverage | Medium | Gate new tools on test requirement (no tool without smoke test) |
| C++ analysis fragility (tree-sitter edge cases) | Medium | Fallback to regex for simple patterns; flag confidence level |
| GDeveloper ID bug blocks remote testing | Medium | Fix ASAP in Phase 1; fallback to stdio for local dev |
| Source control conflicts in multi-user scenarios | Medium | Detect conflicts before editing; surface to user with clear prompts |
