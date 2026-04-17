# Repo Prioritization Matrix V4

> **Date**: 2026-04-16 | **Purpose**: Rank external repos by strategic value to Unreal-MCP-Ghost

---

## Scoring Criteria

| Criterion | Weight | Description |
|---|---|---|
| Scripting Relevance | 30% | How directly does this help BP/material graph authoring? |
| Architecture Quality | 20% | How well-designed and adoptable are the patterns? |
| Production Readiness | 20% | Does this help with testing, safety, reliability? |
| Gap Coverage | 15% | Does this fill a specific missing capability? |
| Integration Effort | 15% | How easy is it to learn from / integrate with Ghost? |

---

## Tier 1: Study Deeply, Borrow Patterns (Score 8.0+)

### flopperam/unreal-engine-mcp — Score: 9.2
| Criterion | Score | Notes |
|---|---|---|
| Scripting Relevance | 10 | Best BP graph scripting: 23+ node types, atomic ops, live compile |
| Architecture Quality | 9 | Native C++ plugin, autonomous agent loops, robust TCP |
| Production Readiness | 8 | Auto-reconnection, error recovery, multi-step workflows |
| Gap Coverage | 10 | Directly fills Ghost's #1 gap: graph-level scripting |
| Integration Effort | 9 | Blueprint-graph-guide.md is immediately actionable |

**Action Items**:
1. Study `blueprint-graph-guide.md` for pin naming, spacing, compile patterns
2. Replicate atomic node/pin/connection API design
3. Study autonomous agent loop for error recovery patterns
4. **Do NOT** copy: commercial hosting model, single-platform focus

**URL**: https://github.com/flopperam/unreal-engine-mcp

---

### syan2018/UnrealCopilot — Score: 9.0
| Criterion | Score | Notes |
|---|---|---|
| Scripting Relevance | 8 | BP editing + C++ analysis + cross-domain tracing |
| Architecture Quality | 10 | Best architecture: skill system, dual-port, tree-sitter, CppSkillApiSubsystem |
| Production Readiness | 9 | Transactional editing, structured error context, validation |
| Gap Coverage | 9 | Fills project intelligence + skill discovery gaps |
| Integration Effort | 9 | ARCHITECTURE.md is a detailed blueprint |

**Action Items**:
1. Study ARCHITECTURE.md for skill system design
2. Adopt CppSkillApiSubsystem decomposition pattern (Asset/Blueprint/World/Editor/Validation)
3. Study cross-domain reference tracing implementation
4. Study tree-sitter integration for C++ analysis
5. **Do NOT** copy: TypeScript MCP server (Ghost is Python)

**URL**: https://github.com/syan2018/UnrealCopilot

---

### cgerchenhp/UE_TAPython_Plugin_Release — Score: 8.5
| Criterion | Score | Notes |
|---|---|---|
| Scripting Relevance | 9 | 200+ editor APIs, material/texture/mesh manipulation |
| Architecture Quality | 8 | JSON-UI + Python logic, hot-reload, editor modes |
| Production Readiness | 8 | Extensive API coverage, test cases repo |
| Gap Coverage | 8 | Fills rapid-editor-tooling gap |
| Integration Effort | 9 | Well-documented APIs at tacolor.xyz |

**Action Items**:
1. Study PythonMaterialLib for material expression APIs
2. Study PythonBPLib for editor utility APIs
3. Study editor mode framework for potential Ghost inspector UI
4. Reference API patterns for Ghost's own Python execution layer

**URL**: https://github.com/cgerchenhp/UE_TAPython_Plugin_Release

---

### JonasReich/OpenUnrealUtilities — Score: 8.1
| Criterion | Score | Notes |
|---|---|---|
| Scripting Relevance | 6 | Indirect — utilities, not scripting tools |
| Architecture Quality | 9 | Production-grade patterns, BDD specs, frame scheduler |
| Production Readiness | 10 | Best testing infrastructure in the Unreal open-source space |
| Gap Coverage | 8 | Fills testing/scheduling/debugging gaps |
| Integration Effort | 8 | C++ plugin, requires understanding OUU patterns |

**Action Items**:
1. Study FAutomationTestWorld for isolated test environments
2. Study OUUTestMacros for test boilerplate reduction
3. Consider Sequential Frame Scheduler for heavy AI operations
4. Apply testing patterns to Ghost's C++ plugin side

**URL**: https://github.com/JonasReich/OpenUnrealUtilities

---

## Tier 2: Solve Specific Gaps (Score 6.0-7.9)

### howaajin/graphformatter — Score: 7.8
| Criterion | Score | Notes |
|---|---|---|
| Scripting Relevance | 8 | Directly relevant to graph readability |
| Architecture Quality | 7 | Solid Sugiyama-style layout algorithm |
| Production Readiness | 7 | Marketplace-published, actively maintained |
| Gap Coverage | 9 | Only solution for auto-formatting AI-generated graphs |
| Integration Effort | 7 | C++ plugin, compilation-version-sensitive |

**Action Items**:
1. Study layered graph drawing algorithm for Ghost's `bp_auto_format_graph`
2. Apply comment-based grouping, reroute insertion patterns
3. Consider integrating as optional UE plugin dependency

**URL**: https://github.com/howaajin/graphformatter

---

### kiwi-lang/uetools — Score: 7.4
| Criterion | Score | Notes |
|---|---|---|
| Scripting Relevance | 5 | CLI automation, not editor scripting |
| Architecture Quality | 8 | Clean CLI design, multi-version support |
| Production Readiness | 8 | PyPI published, CI tested, well-documented |
| Gap Coverage | 8 | Fills build/test/cook automation gap |
| Integration Effort | 8 | `pip install uetools`, immediate CLI access |

**Action Items**:
1. Use for automated build/test/cook in CI pipeline
2. Study Python-enablement and plugin-install commands
3. Consider wrapping `uecli test run` in Ghost MCP tool

**URL**: https://github.com/kiwi-lang/uetools

---

### ayeletstudioindia/unreal-analyzer-mcp — Score: 7.2
| Criterion | Score | Notes |
|---|---|---|
| Scripting Relevance | 7 | C++ analysis directly supports scripting decisions |
| Architecture Quality | 7 | Standard MCP server, clean tool organization |
| Production Readiness | 6 | Newer project, less battle-tested |
| Gap Coverage | 8 | Fills C++ hierarchy/pattern analysis gap |
| Integration Effort | 7 | Python MCP server, compatible architecture |

**Action Items**:
1. Study class analysis and hierarchy mapping implementation
2. Study pattern detection for UPROPERTY/UFUNCTION
3. Consider merging analysis tools into Ghost's Phase 3

**URL**: https://github.com/ayeletstudioindia/unreal-analyzer-mcp

---

### RedpointGames/uet — Score: 7.0
| Criterion | Score | Notes |
|---|---|---|
| Scripting Relevance | 4 | Build tool, not scripting |
| Architecture Quality | 8 | BuildGraph, cross-platform, version sync |
| Production Readiness | 9 | Production-grade, MIT licensed |
| Gap Coverage | 7 | Fills CI/CD build distribution gap |
| Integration Effort | 7 | Single executable, immediate use |

**URL**: https://github.com/RedpointGames/uet

---

### TREE-Ind/UnrealGPT — Score: 6.5
| Criterion | Score | Notes |
|---|---|---|
| Scripting Relevance | 6 | Python execution in editor, scene queries |
| Architecture Quality | 6 | Simpler architecture, OpenAI-dependent |
| Production Readiness | 6 | Loop protection and safety patterns are good |
| Gap Coverage | 7 | Fills multimodal context (screenshot + scene) gap |
| Integration Effort | 7 | Patterns are easily adoptable |

**URL**: https://github.com/TREE-Ind/UnrealGPT

---

## Tier 3: Inspiration (Score < 6.0)

### protospatial/NodeToCode — Score: 5.8 (Inspiration)
- **Key idea**: Compact graph serialization (60-90% token reduction)
- **Action**: Implement similar serialization in `bp_get_graph_summary`
- **URL**: https://github.com/protospatial/NodeToCode

### ZackBradshaw/Bluepy — Score: 5.0 (Inspiration)
- **Key idea**: AI-native Blueprint node generation UX
- **URL**: https://github.com/ZackBradshaw/Bluepy

### CoplayDev/unity-mcp — Score: 5.5 (Inspiration)
- **Key ideas**: Reflection, batch execution, profiling suite, multi-instance routing
- **URL**: https://github.com/CoplayDev/unity-mcp

### rdeioris/glTFRuntime — Score: 5.0 (Inspiration)
- **Key idea**: Modular runtime asset loading with format plugins
- **URL**: https://github.com/rdeioris/glTFRuntime

### xavier150/Blender-For-UnrealEngine-Addons — Score: 4.8 (Inspiration)
- **Key idea**: DCC-to-UE pipeline with auto-generated import scripts
- **URL**: https://github.com/xavier150/Blender-For-UnrealEngine-Addons
