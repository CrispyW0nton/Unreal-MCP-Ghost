# KNOWLEDGE BASE — MASTER INDEX
> Unreal-MCP-Ghost Plugin | EnclaveProject (Dantooine) | UE5.6.1
> Version: 2026-04-10
> **START HERE** if you need to find anything quickly.

---

## WHAT IS THIS KNOWLEDGE BASE?

This is the complete documentation library for the **Unreal-MCP-Ghost** project — an AI agent toolchain for controlling Unreal Engine 5. It contains:
- Full reference for every MCP command the plugin supports
- UE5 system knowledge extracted from 4 professional books
- Complete asset registry for the Dantooine (EnclaveProject) game project
- Step-by-step implementation recipes for all game systems

---

## QUICK DECISION TREE

```
What do you need?
│
├─ "I need to use an MCP command"          → Read 12_MCP_TOOL_USAGE_GUIDE.md
├─ "I need to see what assets exist"       → Read 14_DANTOOINE_PROJECT_REFERENCE.md
├─ "I need to build AI / NavMesh"          → Read 04_AI_SYSTEMS.md
├─ "I need to build a Blueprint graph"     → Read 01_BLUEPRINT_FUNDAMENTALS.md
├─ "I need to connect two Blueprints"      → Read 02_BLUEPRINT_COMMUNICATION.md
├─ "I need to make a UI widget"            → Read 06_UI_UMG_SYSTEMS.md
├─ "I need to add animations"              → Read 05_ANIMATION_SYSTEM.md
├─ "I need to implement a game feature"    → Read 17_GAME_SYSTEMS_COOKBOOK.md
├─ "I need to understand GameMode/Controller" → Read 03_GAMEPLAY_FRAMEWORK.md
├─ "I need to set up player input"         → Read 15_INPUT_SYSTEM_AND_UMG.md
├─ "I need to add materials/shaders"       → Read 08_MATERIALS_AND_RENDERING.md
├─ "I need to add VFX particles"           → Read 09_NIAGARA_VFX.md
├─ "I need to build the level/world"       → Read 10_WORLD_BUILDING.md
├─ "I need to work with data (arrays/structs)" → Read 07_DATA_STRUCTURES.md
├─ "I need to add new MCP commands"        → Read 13_TOOL_EXPANSION_ROADMAP.md
├─ "I need to ship/package the game"       → Read 18_PACKAGING_AND_OPTIMIZATION.md
└─ "I need everything"                     → Read 00_AGENT_KNOWLEDGE_BASE.md
```

---

## COMPLETE FILE LISTING

### 🔴 TIER 1 — ALWAYS READ FIRST

| # | File | Lines | Description |
|---|------|-------|-------------|
| 00 | `00_AGENT_KNOWLEDGE_BASE.md` | 342 | Master index, all 12 agent rules, build order, quick patterns, parent class lookup |
| 12 | `12_MCP_TOOL_USAGE_GUIDE.md` | 817 | **Every** MCP command with exact params, pin names, exec_python patterns, error table |
| 14 | `14_DANTOOINE_PROJECT_REFERENCE.md` | 369 | All 49 assets, 52 folders, asset paths, manual checklist, pending tasks |

### 🟡 TIER 2 — READ BEFORE WORKING ON THAT SYSTEM

| # | File | Lines | Key Topics |
|---|------|-------|------------|
| 01 | `01_BLUEPRINT_FUNDAMENTALS.md` | 531 | Variables, all node types, flow control, math, traces, timelines, construction script |
| 02 | `02_BLUEPRINT_COMMUNICATION.md` | 304 | Direct refs, casting, event dispatchers, interfaces, Level BP, Game Instance |
| 03 | `03_GAMEPLAY_FRAMEWORK.md` | 418 | Actor/Pawn/Character/Controller/GameMode/GameInstance lifecycle and patterns |
| 04 | `04_AI_SYSTEMS.md` | 446 | AIController, BT, Blackboard, NavMesh, PawnSensing, AI Perception, EQS, SpawnDefaultController |
| 05 | `05_ANIMATION_SYSTEM.md` | 421 | ABP structure, State Machines, Blend Spaces, Montages, Slots, Notifies, IK overview |
| 06 | `06_UI_UMG_SYSTEMS.md` | 306 | All widget types, bindings, animations, dialogue/quest/sparring HUD patterns |
| 07 | `07_DATA_STRUCTURES.md` | 392 | Arrays, Sets, Maps, Enums, Structs, Data Tables, flow control nodes deep-dive |

### 🟢 TIER 3 — SPECIALIZED REFERENCES

| # | File | Lines | Key Topics |
|---|------|-------|------------|
| 08 | `08_MATERIALS_AND_RENDERING.md` | 547 | PBR workflow, all material node types, master materials, Lumen, RVT, post-process |
| 09 | `09_NIAGARA_VFX.md` | 268 | Emitter modules, renderers, GPU vs CPU, events, 3 complete VFX recipes |
| 10 | `10_WORLD_BUILDING.md` | 325 | World Partition, Landscape, PCG node reference, lighting, Level Sequencer |
| 11 | `11_BLUEPRINT_LIBRARIES_AND_COMPONENTS.md` | 318 | Function/Macro Libraries, Actor/Scene Components, procedural generation |

### 🔵 TIER 4 — DEEP DIVES AND EXTENDED REFERENCES

| # | File | Lines | Key Topics |
|---|------|-------|------------|
| 13 | `13_TOOL_EXPANSION_ROADMAP.md` | 341 | 20 new MCP commands to build, priority, C++ implementation hints, workarounds |
| 15 | `15_INPUT_SYSTEM_AND_UMG.md` | 439 | Enhanced Input deep-dive, Input Modifiers, Widget hierarchy, dialogue/quest/sparring patterns |
| 16 | `16_ANIMATION_DEEP_DIVE.md` | 370 | Root Motion, advanced IK, Dantooine ABP specs, montage callbacks, performance tips |
| 17 | `17_GAME_SYSTEMS_COOKBOOK.md` | 442 | 11 step-by-step recipes (health, interaction, dialogue, AI, sparring, camera, save/load, etc.) |
| 18 | `18_PACKAGING_AND_OPTIMIZATION.md` | 385 | Build configs, packaging steps, stat commands, Blueprint/rendering/memory optimization |

---

## TOPIC → FILE CROSS-REFERENCE

### Blueprint Graphs
| Topic | Primary File | Also See |
|-------|-------------|----------|
| Adding/connecting nodes | `12_MCP_TOOL_USAGE_GUIDE.md` §Commands | `01_BLUEPRINT_FUNDAMENTALS.md` |
| Variable types | `01_BLUEPRINT_FUNDAMENTALS.md` §Variables | `07_DATA_STRUCTURES.md` |
| Flow control (Branch/Sequence/Loop) | `01_BLUEPRINT_FUNDAMENTALS.md` §Flow | `07_DATA_STRUCTURES.md` §Control |
| Timelines | `01_BLUEPRINT_FUNDAMENTALS.md` §Timelines | — |
| Math nodes | `01_BLUEPRINT_FUNDAMENTALS.md` §Math | — |
| Trace/Line Cast | `01_BLUEPRINT_FUNDAMENTALS.md` §Traces | — |
| exec_python asset creation | `12_MCP_TOOL_USAGE_GUIDE.md` §exec_python | — |

### Blueprint Communication
| Topic | Primary File | Also See |
|-------|-------------|----------|
| Casting to another Blueprint | `02_BLUEPRINT_COMMUNICATION.md` §Casting | `01_BLUEPRINT_FUNDAMENTALS.md` |
| Event Dispatchers | `02_BLUEPRINT_COMMUNICATION.md` §Dispatchers | — |
| Blueprint Interfaces | `02_BLUEPRINT_COMMUNICATION.md` §Interfaces | — |
| Game Instance (global state) | `02_BLUEPRINT_COMMUNICATION.md` §GameInstance | `03_GAMEPLAY_FRAMEWORK.md` |
| Save / Load game | `02_BLUEPRINT_COMMUNICATION.md` §SaveGame | `17_GAME_SYSTEMS_COOKBOOK.md` §Recipe 10 |

### Gameplay Framework
| Topic | Primary File | Also See |
|-------|-------------|----------|
| GameMode setup | `03_GAMEPLAY_FRAMEWORK.md` §GameMode | `14_DANTOOINE_PROJECT_REFERENCE.md` |
| PlayerController patterns | `03_GAMEPLAY_FRAMEWORK.md` §PlayerController | `15_INPUT_SYSTEM_AND_UMG.md` |
| Character movement | `03_GAMEPLAY_FRAMEWORK.md` §Character | `17_GAME_SYSTEMS_COOKBOOK.md` §Recipe 7 |
| Pawn possession | `03_GAMEPLAY_FRAMEWORK.md` §Pawn | `04_AI_SYSTEMS.md` |

### AI Systems
| Topic | Primary File | Also See |
|-------|-------------|----------|
| AIController + Behavior Tree | `04_AI_SYSTEMS.md` §AIController | `17_GAME_SYSTEMS_COOKBOOK.md` §Recipe 5/6 |
| Blackboard setup | `04_AI_SYSTEMS.md` §Blackboard | `14_DANTOOINE_PROJECT_REFERENCE.md` §BB_ keys |
| NavMesh placement | `04_AI_SYSTEMS.md` §NavMesh | `10_WORLD_BUILDING.md` |
| Custom BT Task | `04_AI_SYSTEMS.md` §BTTask | `17_GAME_SYSTEMS_COOKBOOK.md` §Recipe 5 |
| SpawnDefaultController | `04_AI_SYSTEMS.md` §SpawnDefaultController | `12_MCP_TOOL_USAGE_GUIDE.md` |
| Pawn Sensing / AI Perception | `04_AI_SYSTEMS.md` §Sensing | — |
| EQS | `04_AI_SYSTEMS.md` §EQS | — |

### Animation
| Topic | Primary File | Also See |
|-------|-------------|----------|
| ABP structure (EventGraph/AnimGraph) | `05_ANIMATION_SYSTEM.md` §Structure | `16_ANIMATION_DEEP_DIVE.md` |
| State Machines | `05_ANIMATION_SYSTEM.md` §StateMachines | `16_ANIMATION_DEEP_DIVE.md` §SM |
| Blend Spaces | `05_ANIMATION_SYSTEM.md` §BlendSpaces | `16_ANIMATION_DEEP_DIVE.md` §BS |
| Montages | `05_ANIMATION_SYSTEM.md` §Montages | `16_ANIMATION_DEEP_DIVE.md` §Montages |
| Notifies (trigger events from animation) | `05_ANIMATION_SYSTEM.md` §Notifies | `16_ANIMATION_DEEP_DIVE.md` §Notifies |
| IK (foot placement, hand grip) | `05_ANIMATION_SYSTEM.md` §IK | `16_ANIMATION_DEEP_DIVE.md` §IK |
| Root Motion | `16_ANIMATION_DEEP_DIVE.md` §RootMotion | — |
| Dantooine ABP specs | `16_ANIMATION_DEEP_DIVE.md` §Dantooine | `14_DANTOOINE_PROJECT_REFERENCE.md` |

### UI / HUD
| Topic | Primary File | Also See |
|-------|-------------|----------|
| Widget Blueprint creation | `06_UI_UMG_SYSTEMS.md` §Creating | `15_INPUT_SYSTEM_AND_UMG.md` |
| Widget variable bindings | `06_UI_UMG_SYSTEMS.md` §Bindings | — |
| Input modes (Game/UI/Game+UI) | `06_UI_UMG_SYSTEMS.md` §InputModes | `15_INPUT_SYSTEM_AND_UMG.md` §InputModes |
| Dialogue box UI | `06_UI_UMG_SYSTEMS.md` §Dialogue | `17_GAME_SYSTEMS_COOKBOOK.md` §Recipe 3 |
| Quest tracker UI | `15_INPUT_SYSTEM_AND_UMG.md` §QuestTracker | `17_GAME_SYSTEMS_COOKBOOK.md` §Recipe 4 |
| Widget animations | `15_INPUT_SYSTEM_AND_UMG.md` §WidgetAnim | — |

### Data / Structs / Enums
| Topic | Primary File | Also See |
|-------|-------------|----------|
| Enum creation | `07_DATA_STRUCTURES.md` §Enums | `14_DANTOOINE_PROJECT_REFERENCE.md` |
| Struct fields | `07_DATA_STRUCTURES.md` §Structs | `14_DANTOOINE_PROJECT_REFERENCE.md` |
| Arrays (for loops, add/remove) | `07_DATA_STRUCTURES.md` §Arrays | `01_BLUEPRINT_FUNDAMENTALS.md` |
| Data Tables | `07_DATA_STRUCTURES.md` §DataTables | `17_GAME_SYSTEMS_COOKBOOK.md` §Recipe 3 |
| Dantooine struct definitions | `14_DANTOOINE_PROJECT_REFERENCE.md` §Structs | `07_DATA_STRUCTURES.md` |

### Input
| Topic | Primary File | Also See |
|-------|-------------|----------|
| Enhanced Input setup | `15_INPUT_SYSTEM_AND_UMG.md` §EnhancedInput | `03_GAMEPLAY_FRAMEWORK.md` |
| Binding IA_ actions in Blueprint | `15_INPUT_SYSTEM_AND_UMG.md` §Binding | — |
| IMC_Dantooine configuration | `14_DANTOOINE_PROJECT_REFERENCE.md` §Input | `15_INPUT_SYSTEM_AND_UMG.md` |
| Input modifiers | `15_INPUT_SYSTEM_AND_UMG.md` §Modifiers | — |

### Materials / Rendering
| Topic | Primary File | Also See |
|-------|-------------|----------|
| PBR setup | `08_MATERIALS_AND_RENDERING.md` §PBR | — |
| Master material pattern | `08_MATERIALS_AND_RENDERING.md` §Master | — |
| Material instances | `08_MATERIALS_AND_RENDERING.md` §Instances | — |
| Lumen GI | `08_MATERIALS_AND_RENDERING.md` §Lumen | `10_WORLD_BUILDING.md` §Lighting |
| Runtime Virtual Textures | `08_MATERIALS_AND_RENDERING.md` §RVT | `10_WORLD_BUILDING.md` §RVT |

### VFX
| Topic | Primary File | Also See |
|-------|-------------|----------|
| Niagara system overview | `09_NIAGARA_VFX.md` §Overview | — |
| GPU vs CPU particles | `09_NIAGARA_VFX.md` §GPUvsCPU | — |
| Saber glow VFX (Dantooine) | `09_NIAGARA_VFX.md` §Recipes | `14_DANTOOINE_PROJECT_REFERENCE.md` §VFX |

---

## DANTOOINE PROJECT QUICK FACTS

| Property | Value |
|----------|-------|
| Engine | UE5.6.1 |
| Project | EnclaveProject |
| Content Root | `/Game/Dantooine/` |
| Total Blueprints | 22 |
| Total Assets | 49 |
| Total Folders | 52 |
| Plugin Port | 55557 |
| AI CLI | `python3 sandbox_ue5cli.py <command> '<json>'` |

### Build Status Summary
| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Data Layer (Enums, Structs, Interfaces, Input) | ✅ Done |
| 2 | Core Framework (GameMode, Controller, Player, QuestManager) | ✅ Done |
| 3 | UI Widgets (HUD, Dialogue, Quest, Interact, Sparring, Complete) | ✅ Done |
| 4 | World Actors (MasterJedi, Workbench, Trigger, LevelHandler) | ✅ Done |
| 5 | Ambient Systems (SkyShip, RoamingNPC Base/A/B) | ✅ Done |
| 6 | Combat AI (SparringOpponent, AIControllers, BTs, BBs, BTTask) | ✅ Done |
| 7 | Animation Blueprints (3 ABPs — skeleton assignment pending) | ✅ Done |
| 8 | Cinematics (LS_LightsaberBuild Level Sequence) | ✅ Done |
| 9 | Logic wiring, artist assets, project settings | ⏳ Pending |

---

## SOURCES

| Book | Author | Pages | Covered In |
|------|--------|-------|-----------|
| Blueprints Visual Scripting for UE5 (3rd Ed.) | Marcos Romero (Packt 2023) | 566 | Files 01–07, 11, 15–17 |
| Game Development with UE5 Volume 1 | Tiow Wee Tan (Apress 2024) | 423 | Files 08–10 |
| Mastering Technical Art in Unreal Engine | Greg Penninck (CRC Press 2025) | 251 | Files 08–09, 18 |
| Unreal Engine Blueprint Game Developer | Asadullah Alam (BPB Publications) | 386 | Files 01–03 (AI-summarized) |

---

*Generated: 2026-04-10 | Repository: https://github.com/CrispyW0nton/Unreal-MCP-Ghost*
