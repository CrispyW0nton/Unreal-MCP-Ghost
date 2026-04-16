# KNOWLEDGE BASE — MASTER INDEX
> Unreal-MCP-Ghost Plugin | UE 5.6
> Version: 2026-04-16 (V4)
> **START HERE** if you need to find anything quickly.

---

## WHAT IS THIS KNOWLEDGE BASE?

This is the complete documentation library for the **Unreal-MCP-Ghost** project — an AI agent toolchain for controlling Unreal Engine 5. It contains:
- Full reference for every MCP command the plugin supports
- UE5 system knowledge extracted from 4 professional books
- V4 roadmap, architecture specs, and research reports
- Step-by-step implementation recipes for all game systems

---

## QUICK DECISION TREE

```
What do you need?
│
├─ "Where do I start? What's the V4 plan?"  → Read v4/NEXT_DEVELOPER_PROMPT_V4.md
├─ "I need to use an MCP command"           → Read 12_MCP_TOOL_USAGE_GUIDE.md
├─ "I need to build AI / NavMesh"           → Read 04_AI_SYSTEMS.md
├─ "I need to build a Blueprint graph"      → Read 01_BLUEPRINT_FUNDAMENTALS.md + graph_tools.py (bp_* tools)
├─ "I need to connect two Blueprints"       → Read 02_BLUEPRINT_COMMUNICATION.md
├─ "I need to make a UI widget"             → Read 06_UI_UMG_SYSTEMS.md
├─ "I need to add animations"               → Read 05_ANIMATION_SYSTEM.md
├─ "I need to implement a game feature"     → Read 17_GAME_SYSTEMS_COOKBOOK.md
├─ "I need to understand GameMode/Controller" → Read 03_GAMEPLAY_FRAMEWORK.md
├─ "I need to set up player input"          → Read 15_INPUT_SYSTEM_AND_UMG.md
├─ "I need to add materials/shaders"        → Read 08_MATERIALS_AND_RENDERING.md
├─ "I need to add VFX particles"            → Read 09_NIAGARA_VFX.md
├─ "I need to build the level/world"        → Read 10_WORLD_BUILDING.md
├─ "I need to work with data (arrays/structs)" → Read 07_DATA_STRUCTURES.md
├─ "I need to add new MCP commands"         → Read 13_TOOL_EXPANSION_ROADMAP.md + v4/GRAPH_SCRIPTING_SPEC_V4.md
├─ "I need to edit a Blueprint graph (V4)" → Use bp_get_graph_summary, bp_add_node, bp_connect_pins, bp_compile
├─ "I need to remove a node / break a pin" → Use bp_remove_node, bp_disconnect_pin
├─ "I need a new function in a Blueprint"   → Use bp_add_function, then bp_add_node with graph_name=<fn>
├─ "I need to create/edit a Material"       → Use mat_create_material, mat_add_expression, mat_connect_expressions, mat_compile
├─ "I need to ship/package the game"        → Read 18_PACKAGING_AND_OPTIMIZATION.md
├─ "I need to understand the architecture"  → Read v4/ARCHITECTURE_BLUEPRINT.md
├─ "I need UE Python API references"        → Read v4/API_REFERENCE_CHEATSHEET.md
└─ "I need everything"                      → Read 00_AGENT_KNOWLEDGE_BASE.md
```

---

## V4 ROADMAP DOCS (`knowledge_base/v4/`)

> The V4 package represents the strategic direction as of 2026-04-16.
> **Product identity**: "The best AI-native scripting and graph-authoring layer for Unreal Engine."

| File | Purpose |
|------|---------|
| `v4/NEXT_DEVELOPER_PROMPT_V4.md` | **START HERE for new sessions** — full context, roadmap, decision framework |
| `v4/ROADMAP_V4.md` | Phased roadmap (6 phases, 16 weeks) with deliverables and exit criteria |
| `v4/GRAPH_SCRIPTING_SPEC_V4.md` | Technical spec for Phase 2: 12 BP graph ops + 6 material ops |
| `v4/VALIDATION_TEST_MATRIX_V4.md` | 165 test scenarios across 5 phases |
| `v4/DEEP_RESEARCH_REPORT_V4.md` | Full competitive analysis + UE engine systems deep dive |
| `v4/REPO_PRIORITIZATION_MATRIX_V4.md` | 15 repos scored and tiered with action items |
| `v4/ENGINE_SOURCE_STUDY_GUIDE_V4.md` | 8 UE subsystems mapped with study guides |
| `v4/ARCHITECTURE_BLUEPRINT.md` | Current and target system architecture |
| `v4/API_REFERENCE_CHEATSHEET.md` | Consolidated UE5 Python API reference (import, materials, IK, utilities) |
| `v4/GHOSTRIGGER_INTEGRATION_SPEC.md` | GhostRigger ↔ Ghost IPC specification |
| `v4/NATIVE_MODE_ENHANCEMENT_SPEC.md` | Making Claude Desktop experience equal to GenSpark |
| `v4/SPRINT_TRACKER.md` | 12-sprint (24-week) delivery timeline |
| `v4/README.md` | Package overview and 30/60/90 day summary |

---

## COMPLETE FILE LISTING

### 🔴 TIER 1 — ALWAYS READ FIRST

| # | File | Description |
|---|------|-------------|
| 00 | `00_AGENT_KNOWLEDGE_BASE.md` | Master index, all 12 agent rules, build order, quick patterns, parent class lookup |
| 12 | `12_MCP_TOOL_USAGE_GUIDE.md` | **Every** MCP command with exact params, pin names, exec_python patterns, error table |
| V4 | `v4/NEXT_DEVELOPER_PROMPT_V4.md` | V4 session startup prompt — mission, current state, roadmap, decision framework |

### 🟡 TIER 2 — READ BEFORE WORKING ON THAT SYSTEM

| # | File | Key Topics |
|---|------|------------|
| 01 | `01_BLUEPRINT_FUNDAMENTALS.md` | Variables, all node types, flow control, math, traces, timelines, construction script |
| 02 | `02_BLUEPRINT_COMMUNICATION.md` | Direct refs, casting, event dispatchers, interfaces, Level BP, Game Instance |
| 03 | `03_GAMEPLAY_FRAMEWORK.md` | Actor/Pawn/Character/Controller/GameMode/GameInstance lifecycle and patterns |
| 04 | `04_AI_SYSTEMS.md` | AIController, BT, Blackboard, NavMesh, PawnSensing, AI Perception, EQS |
| 05 | `05_ANIMATION_SYSTEM.md` | ABP structure, State Machines, Blend Spaces, Montages, Slots, Notifies, IK overview |
| 06 | `06_UI_UMG_SYSTEMS.md` | All widget types, bindings, animations, dialogue/quest/HUD patterns |
| 07 | `07_DATA_STRUCTURES.md` | Arrays, Sets, Maps, Enums, Structs, Data Tables, flow control nodes deep-dive |

### 🟢 TIER 3 — SPECIALIZED REFERENCES

| # | File | Key Topics |
|---|------|------------|
| 08 | `08_MATERIALS_AND_RENDERING.md` | PBR workflow, all material node types, master materials, Lumen, RVT, post-process |
| 09 | `09_NIAGARA_VFX.md` | Emitter modules, renderers, GPU vs CPU, events, VFX recipes |
| 10 | `10_WORLD_BUILDING.md` | World Partition, Landscape, PCG node reference, lighting, Level Sequencer |
| 11 | `11_BLUEPRINT_LIBRARIES_AND_COMPONENTS.md` | Function/Macro Libraries, Actor/Scene Components, procedural generation |

### 🔵 TIER 4 — DEEP DIVES AND EXTENDED REFERENCES

| # | File | Key Topics |
|---|------|------------|
| 13 | `13_TOOL_EXPANSION_ROADMAP.md` | 20 new MCP commands to build, priority, C++ implementation hints, workarounds |
| 15 | `15_INPUT_SYSTEM_AND_UMG.md` | Enhanced Input deep-dive, Input Modifiers, Widget hierarchy |
| 16 | `16_ANIMATION_DEEP_DIVE.md` | Root Motion, advanced IK, montage callbacks, performance tips |
| 17 | `17_GAME_SYSTEMS_COOKBOOK.md` | 11 step-by-step recipes (health, interaction, dialogue, AI, save/load, etc.) |
| 18 | `18_PACKAGING_AND_OPTIMIZATION.md` | Build configs, packaging steps, stat commands, Blueprint/rendering/memory optimization |

### 🟣 V4 RESEARCH DOCS

| File | Key Topics |
|------|------------|
| `v4/GRAPH_SCRIPTING_SPEC_V4.md` | bp_add_node, bp_connect_pins, bp_compile, mat_* — full function signatures and schemas |
| `v4/DEEP_RESEARCH_REPORT_V4.md` | flopperam, UnrealCopilot, NodeToCode, GraphFormatter competitive analysis |
| `v4/REPO_PRIORITIZATION_MATRIX_V4.md` | 15 repos scored (flopperam 9.2, UnrealCopilot 9.0, TAPython 8.5, OpenUnrealUtils 8.1) |
| `v4/ENGINE_SOURCE_STUDY_GUIDE_V4.md` | KismetCompiler, BlueprintGraph, AssetRegistry, Interchange, AutomationTest |
| `v4/API_REFERENCE_CHEATSHEET.md` | AssetImportTask, MaterialEditingLibrary, IKRigController, EditorAssetLibrary |
| `v4/ARCHITECTURE_BLUEPRINT.md` | Current TCP+Python architecture, target clean architecture with abstract ports |
| `v4/GHOSTRIGGER_INTEGRATION_SPEC.md` | GhostRigger port 7001 IPC, KotOR MCP endpoints, FBX/OBJ exporter |
| `v4/NATIVE_MODE_ENHANCEMENT_SPEC.md` | MCP Resources for KB docs, project context tool, onboarding tool |

---

## TOPIC → FILE CROSS-REFERENCE

### Blueprint Graphs
| Topic | Primary File | Also See |
|-------|-------------|----------|
| Adding/connecting nodes (existing) | `12_MCP_TOOL_USAGE_GUIDE.md` §Commands | `01_BLUEPRINT_FUNDAMENTALS.md` |
| Atomic graph ops (Phase 2 spec) | `v4/GRAPH_SCRIPTING_SPEC_V4.md` | `v4/DEEP_RESEARCH_REPORT_V4.md` §flopperam |
| Variable types | `01_BLUEPRINT_FUNDAMENTALS.md` §Variables | `07_DATA_STRUCTURES.md` |
| Flow control (Branch/Sequence/Loop) | `01_BLUEPRINT_FUNDAMENTALS.md` §Flow | `07_DATA_STRUCTURES.md` §Control |
| exec_python asset creation | `12_MCP_TOOL_USAGE_GUIDE.md` §exec_python | — |

### AI Systems
| Topic | Primary File | Also See |
|-------|-------------|----------|
| AIController + Behavior Tree | `04_AI_SYSTEMS.md` §AIController | `17_GAME_SYSTEMS_COOKBOOK.md` §Recipe 5/6 |
| Blackboard setup | `04_AI_SYSTEMS.md` §Blackboard | — |
| NavMesh placement | `04_AI_SYSTEMS.md` §NavMesh | `10_WORLD_BUILDING.md` |
| Custom BT Task | `04_AI_SYSTEMS.md` §BTTask | `17_GAME_SYSTEMS_COOKBOOK.md` §Recipe 5 |

### Animation
| Topic | Primary File | Also See |
|-------|-------------|----------|
| ABP structure | `05_ANIMATION_SYSTEM.md` §Structure | `16_ANIMATION_DEEP_DIVE.md` |
| State Machines / Blend Spaces / Montages | `05_ANIMATION_SYSTEM.md` | `16_ANIMATION_DEEP_DIVE.md` |
| IK Rig retargeting (auto setup) | `v4/API_REFERENCE_CHEATSHEET.md` §IK | `v4/ENGINE_SOURCE_STUDY_GUIDE_V4.md` §Priority7 |

### Materials / Rendering
| Topic | Primary File | Also See |
|-------|-------------|----------|
| PBR setup | `08_MATERIALS_AND_RENDERING.md` §PBR | — |
| Material Python API | `v4/API_REFERENCE_CHEATSHEET.md` §Materials | `v4/GRAPH_SCRIPTING_SPEC_V4.md` §3 |
| Material graph ops (Phase 2) | `v4/GRAPH_SCRIPTING_SPEC_V4.md` §mat_* | — |

### Import Pipeline
| Topic | Primary File | Also See |
|-------|-------------|----------|
| Import Python APIs | `v4/API_REFERENCE_CHEATSHEET.md` §1 | `12_MCP_TOOL_USAGE_GUIDE.md` |
| Interchange framework | `v4/ENGINE_SOURCE_STUDY_GUIDE_V4.md` §Priority4 | — |
| Batch import / character import | `skills/SKILL_batch_import_folder.md` | `skills/SKILL_import_folder_as_character.md` |

### Plugin Architecture
| Topic | Primary File | Also See |
|-------|-------------|----------|
| System overview | `v4/ARCHITECTURE_BLUEPRINT.md` | `v4/NEXT_DEVELOPER_PROMPT_V4.md` §Architecture |
| V4 Phase 1 stabilization tasks | `v4/ROADMAP_V4.md` §Phase1 | `v4/SPRINT_TRACKER.md` §Sprint1 |
| V4 Phase 2 graph scripting | `v4/GRAPH_SCRIPTING_SPEC_V4.md` | `v4/ROADMAP_V4.md` §Phase2 |
| Test matrix | `v4/VALIDATION_TEST_MATRIX_V4.md` | — |
| GhostRigger bridge | `v4/GHOSTRIGGER_INTEGRATION_SPEC.md` | — |

---

## PLUGIN QUICK FACTS

| Property | Value |
|----------|-------|
| Engine | UE 5.6 |
| MCP Tools | 378 (362 + 16 V4 graph/mat tools) |
| Modules | 25 (added graph_tools.py) |
| C++ Commands | 119 |
| Transports | stdio, SSE, streamable-HTTP |
| Plugin Port | 55557 |
| Tests | 103 (48 import + 55 graph-core) |
| GitHub | https://github.com/CrispyW0nton/Unreal-MCP-Ghost |

---

## SOURCES

| Book | Author | Pages | Covered In |
|------|--------|-------|-----------|
| Blueprints Visual Scripting for UE5 (3rd Ed.) | Marcos Romero (Packt 2023) | 566 | Files 01–07, 11, 15–17 |
| Game Development with UE5 Volume 1 | Tiow Wee Tan (Apress 2024) | 423 | Files 08–10 |
| Mastering Technical Art in Unreal Engine | Greg Penninck (CRC Press 2025) | 251 | Files 08–09, 18 |
| Unreal Engine Blueprint Game Developer | Asadullah Alam (BPB Publications) | 386 | Files 01–03 (AI-summarized) |

---

*Updated: 2026-04-16 (V4) | Repository: https://github.com/CrispyW0nton/Unreal-MCP-Ghost*
