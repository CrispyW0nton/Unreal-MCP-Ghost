# Deep Research Report V4 — Unreal-MCP-Ghost

> **Date**: 2026-04-16 | **Scope**: Open-source repos, UE engine systems, competitive landscape, strategic recommendations

---

## 1. Executive Summary

Unreal-MCP-Ghost has reached 362 tools across 24 modules with a safe execution substrate, reflection/diagnostics, and a skills library. The project is at an inflection point: it can either continue adding tools (diminishing returns) or pivot to becoming the **definitive AI scripting layer for Unreal Engine** (compounding returns).

This research identifies the 10 most relevant open-source repos, 8 critical Unreal Engine subsystems, and a concrete technical strategy for the next 90 days focused on graph-native scripting, project intelligence, and verification.

---

## 2. Competitive Landscape Analysis

### 2.1 Direct Competitors (Unreal MCP Servers)

#### flopperam/unreal-engine-mcp
- **URL**: https://github.com/flopperam/unreal-engine-mcp
- **Strengths**: Autonomous "Flop Agent" with multi-step planning, 23+ Blueprint node types across 6 categories, live compile/validate loops, native C++ plugin for low latency, hosted remote MCP option
- **Weaknesses**: Closed commercial model (flopperam.com), less transparent architecture, no skills/resource system
- **Lesson for Ghost**: Copy the atomic graph-editing philosophy. Their blueprint-graph-guide.md is the best reference for pin naming, node spacing (300-400 X units), and compile-after-edit patterns
- **Key URL**: https://github.com/flopperam/unreal-engine-mcp/blob/main/Guides/blueprint-graph-guide.md

#### syan2018/UnrealCopilot
- **URL**: https://github.com/syan2018/UnrealCopilot
- **Strengths**: Skill system (discoverable, documented, executable), tree-sitter C++ analysis, cross-domain reference tracing (BP ↔ C++ ↔ assets), transactional Blueprint editing, dual-port architecture (MCP:19840, plugin:8080)
- **Weaknesses**: Smaller tool surface, TypeScript MCP server (vs Ghost's Python), newer project
- **Lesson for Ghost**: The skill system and cross-domain intelligence are the most architecturally sophisticated patterns in the Unreal MCP space. Copy the SKILL.md structure, the CppSkillApiSubsystem decomposition, and the cross-domain tracing concept
- **Key URL**: https://github.com/syan2018/UnrealCopilot/blob/main/ARCHITECTURE.md

#### ChiR24/Unreal_mcp
- **URL**: https://github.com/ChiR24/Unreal_mcp
- **Strengths**: 36 tools, safety filters, rate limiting, asset caching, optional GraphQL endpoint, Prometheus metrics
- **Lesson for Ghost**: Observability (metrics) and safety filters are good production patterns to adopt later

#### kvick-games/UnrealMCP
- **URL**: https://github.com/kvick-games/UnrealMCP
- **Strengths**: Simple TCP server, UI toolbar, ready-to-use Claude Desktop config
- **Lesson for Ghost**: Simplicity of onboarding matters; keep the "1 minute to first tool call" experience

#### prajwalshettydev/UnrealGenAISupport
- **URL**: https://github.com/prajwalshettydev/UnrealGenAISupport
- **Strengths**: Multi-LLM provider support (OpenAI, Anthropic, Deepseek, Grok), MCP client integration
- **Weaknesses**: Known node-connection failures, no undo/redo, poor error handling
- **Lesson for Ghost**: Multi-provider support has demand; robust error handling is non-negotiable

### 2.2 Indirect Competitors / Complementary Tools

#### TREE-Ind/UnrealGPT
- **URL**: https://github.com/TREE-Ind/UnrealGPT
- **Strengths**: Scene summary + screenshot for multimodal context, loop protection, result-size limits, execution timeouts, in-editor dockable tab
- **Lesson for Ghost**: Operational discipline patterns (loop protection, timeouts, size limits) are immediately adoptable

#### ZackBradshaw/Bluepy
- **URL**: https://github.com/ZackBradshaw/Bluepy
- **Strengths**: AI-native Blueprint node generation UX, chat-in-graph-editor concept
- **Lesson for Ghost**: Validates demand for AI-driven node generation; Ghost's graph API should support this UX pattern

#### protospatial/NodeToCode
- **URL**: https://github.com/protospatial/NodeToCode
- **Strengths**: Custom K2Node/K2Pin serialization to compact JSON (60-90% token reduction vs UE text format), multi-language translation, nested graph traversal (up to 5 levels), integrated editor UI
- **Lesson for Ghost**: Graph serialization to AI-readable form is critical. Ghost needs a `bp_get_graph_summary` tool that produces compact structured representations, not screenshots

---

## 3. Editor Tooling & Scripting Repos

### cgerchenhp/UE_TAPython_Plugin_Release
- **URL**: https://github.com/cgerchenhp/UE_TAPython_Plugin_Release
- **Strengths**: 200+ editor APIs (PythonBPLib, PythonMaterialLib, PythonTextureLib, PythonMeshLib, etc.), JSON-defined Slate UI, live hot-reload, custom editor modes without C++, viewport interaction capture, menu system customization
- **Lesson for Ghost**: TAPython proves that Python + JSON UI is sufficient for sophisticated editor tooling. If Ghost ever needs an in-editor visual panel, this is the reference implementation

### JonasReich/OpenUnrealUtilities
- **URL**: https://github.com/JonasReich/OpenUnrealUtilities
- **Strengths**: FAutomationTestWorld for isolated test environments, AutomationTestParameterParser, CollectionTestFunctions, OUUTestMacros, Sequential Frame Scheduler, Gameplay Debugger extensions
- **Lesson for Ghost**: The testing infrastructure patterns are directly relevant for production hardening. The frame scheduler concept matters for distributing heavy AI operations across multiple ticks

### kiwi-lang/uetools
- **URL**: https://github.com/kiwi-lang/uetools
- **Strengths**: CLI wrapping 222 commandlets + 83 commands + 1237 parameters, multi-engine-version support, plugin install/disable, build/cook/test/localize, Python enablement, project-to-C++ conversion
- **Lesson for Ghost**: When Ghost needs build/test/cook automation, uetools is the correct CLI backbone rather than reinventing UAT/UBT wrapping

### RedpointGames/uet
- **URL**: https://github.com/RedpointGames/uet
- **Strengths**: BuildGraph distribution, cross-platform builds, automatic retries, fault tolerance, version-synced builds via BuildConfig.json
- **Lesson for Ghost**: For CI/CD pipeline integration, UET provides the production-grade build distribution model

---

## 4. Graph Layout & Code Translation

### howaajin/graphformatter
- **URL**: https://github.com/howaajin/graphformatter
- **Algorithm**: Layered graph drawing (Sugiyama-style) based on "Fast and Simple Horizontal Coordinate Assignment" and "Size- and Port-Aware Horizontal Node Coordinate Assignment"
- **Key patterns**: Comment-based grouping, variable duplication for high-fan-out nodes, reroute nodes for long connections, PCG graph support
- **Lesson for Ghost**: AI-generated graphs become unreadable without auto-formatting. Ghost should either integrate GraphFormatter or implement equivalent layout rules

### ayeletstudioindia/unreal-analyzer-mcp
- **URL**: https://github.com/ayeletstudioindia/unreal-analyzer-mcp
- **Strengths**: Class analysis, hierarchy mapping, code search, reference finding, subsystem analysis, pattern detection (UPROPERTY/UFUNCTION), best-practices guides, API documentation query
- **Lesson for Ghost**: This is a good reference for the Phase 3 C++ analysis tools. The pattern detection and best-practices query features are especially valuable for code review workflows

---

## 5. Unreal Engine Systems Deep Dive

### 5.1 KismetCompiler (Blueprint Compilation)
- **Doc**: https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/KismetCompiler/FKismetCompilerContext
- **Key concepts**: Function graph creation, ubergraph merging, node expansion (macros/tunnels), timeline expansion, pin validation (wildcard checks, self-pin checks), CDO propagation, class finalization
- **Relevance**: Ghost must understand compilation to diagnose errors, validate graph edits, and ensure generated Blueprints compile cleanly
- **Critical methods**: `CreateFunctionList()`, `MergeUbergraphPagesIn()`, `ExpandTunnelsAndMacros()`, `ValidateGeneratedClass()`, `CheckConnectionResponse()`

### 5.2 BlueprintGraph (Node-Level Authoring)
- **Doc**: https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Editor/BlueprintGraph
- **Key classes**: `FEdGraphSchemaAction_K2NewNode` (add node), `FEdGraphSchemaAction_K2AddEvent` (add event), `FEdGraphSchemaAction_K2AddComponent` (add component), `FEdGraphSchemaAction_K2AddCustomEvent` (custom event), `UK2Node_*` variants
- **Relevance**: These are the primitives Ghost's `bp_add_node` should map to

### 5.3 Asset Registry
- **Doc**: https://dev.epicgames.com/documentation/en-us/unreal-engine/asset-registry-in-unreal-engine
- **Key capabilities**: `GetAssetsByClass()`, `GetAssetsByPath()`, `GetAssetsByTagValues()`, `GetAssets()` with `FARFilter`, async discovery via `OnAssetAdded()`/`OnAssetRemoved()`/`OnAssetRenamed()` delegates, `TagsAndValues` map with `AssetRegistrySearchable` properties
- **Relevance**: Foundation for all project intelligence tools

### 5.4 Interchange Framework
- **Doc**: https://dev.epicgames.com/documentation/unreal-engine/importing-assets-using-interchange-in-unreal-engine
- **Key capabilities**: File-format agnostic, asynchronous, customizable pipeline stack (C++/Blueprint/Python), runtime capable
- **Relevance**: Long-term replacement for ad-hoc per-format import tools; enables AI-driven custom import pipelines

### 5.5 Automation Test Framework
- **Doc**: https://dev.epicgames.com/documentation/unreal-engine/automation-test-framework-in-unreal-engine
- **Test types**: Unit, Feature, Smoke (< 1 second), Content Stress, Screenshot Comparison
- **Key interfaces**: Automation Spec (BDD), Automation Driver (input simulation), Functional Testing (level-based), CQTest (async fixtures), Editor Testing with Python
- **Design guidelines**: Don't assume state; leave disk as found; assume bad previous state
- **Relevance**: Ghost should trigger targeted Automation Tests post-edit and interpret results

### 5.6 Python Editor Scripting (Safety Contract)
- **Doc**: https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python
- **Non-negotiable rules**: Use Unreal asset APIs (never `os`/`shutil`), use `set_editor_property()`, wrap in `ScopedEditorTransaction`, use `ScopedSlowTask`, use `unreal.log()`, prefer Unreal utilities over custom implementations
- **Relevance**: This IS the safety contract for Ghost's execution substrate

### 5.7 IK Rig Python API
- **Doc**: https://dev.epicgames.com/documentation/unreal-engine/using-python-to-create-and-edit-ik-rigs-in-unreal-engine
- **Key APIs**: `IKRigController.get_controller()`, `set_retarget_root()`, `add_retarget_chain()`, `apply_auto_generated_retarget_definition()`, `apply_auto_fbik()`, `is_skeletal_mesh_compatible()`
- **Relevance**: Enables the "import character → IK retarget" signature workflow

### 5.8 Source Control
- **Doc**: https://dev.epicgames.com/documentation/unreal-engine/source-control-in-unreal-engine
- **Key capabilities**: Perforce/SVN support, auto-checkout on modification, content hot-reload, checkout/checkin/diff/history via Content Browser context menu
- **Relevance**: Ghost must be source-control-aware before it becomes more autonomous

---

## 6. Key Technical Patterns to Adopt

### From flopperam: Atomic Graph Operations
```
1. Create node → get node_id
2. Save node_id for connections
3. Connect pins by exact name (case-sensitive)
4. Always compile after modifications
5. Use consistent spacing (300-400 X units)
```

### From UnrealCopilot: Transactional Editing
```
1. Inspect current state
2. Begin transaction (ScopedEditorTransaction)
3. Execute mutations
4. Compile and validate
5. Return structured result with error context (graph_name, node_guid)
6. On failure: roll back and report
```

### From NodeToCode: Graph Serialization
```
1. Walk K2Nodes and K2Pins
2. Extract execution flows, data connections, variable refs, comments
3. Serialize to compact JSON schema (60-90% token reduction)
4. Support nested graph traversal (configurable depth)
```

### From OpenUnrealUtilities: Test Infrastructure
```
1. Use FAutomationTestWorld for isolated test environments
2. Parse test parameters from FString
3. Use collection-aware assertions
4. BDD-style specs for readable test organization
```

### From UnrealGPT: Agent Safety
```
1. Max toolcall iteration count (loop protection)
2. Tool result size limits (context overflow prevention)
3. Execution timeouts for risky scripts
4. Scene summary + screenshot for verification
```

---

## 7. The Unreal Engine Source ZIP

The shared Google Drive file `UnrealEngine-release.zip` is too large to preview or analyze through available tools. For source-level study, the recommended approach is:

1. **Extract locally** and navigate to the specific directories listed in Section 5
2. **Priority folders**:
   - `Engine/Source/Editor/KismetCompiler/` — Blueprint compilation
   - `Engine/Source/Editor/BlueprintGraph/` — Graph node primitives
   - `Engine/Source/Runtime/AssetRegistry/` — Asset discovery/search
   - `Engine/Source/Editor/UnrealEd/Private/Interchange/` — Import pipeline
   - `Engine/Source/Developer/AutomationDriver/` — Test framework
   - `Engine/Source/Editor/UnrealEd/Private/Kismet2/` — Blueprint editor internals
   - `Engine/Plugins/Animation/IKRig/` — IK retargeting
3. **Study method**: Read header files first (`.h`) for API surface, then implementation (`.cpp`) for behavior

---

## 8. Strategic Recommendation

**Build the best AI scripting layer, not the biggest tool collection.**

The moat is not 362 tools (others can add tools). The moat is:
- Safe, transactional, verifiable graph editing
- Project-wide intelligence (asset registry, cross-references, C++ analysis)
- Higher-order skills that compose atomic operations into reliable workflows
- Source-control-aware autonomy for real production use

That is what will make Unreal-MCP-Ghost the tool that a solo/duo team trusts to help build AAA-quality games in ≤6 months.
