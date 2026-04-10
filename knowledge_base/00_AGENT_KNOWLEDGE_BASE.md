# AGENT KNOWLEDGE BASE — Unreal-MCP-Ghost
> Master reference for any AI agent using this repository.
> Read this file FIRST before taking any action in a UE5 project.
> Version: 2026-04-10 | UE5.6 | Dantooine Project (EnclaveProject)
> Built from: 4 professional UE5 books + project experience

---

## WHAT THIS REPOSITORY IS

**Unreal-MCP-Ghost** is a plugin + toolchain that lets an AI agent control Unreal Engine 5 via a socket connection. The plugin (`UnrealMCP`) runs inside UE5 and listens on port **55557**. The agent communicates through `sandbox_ue5cli.py`.

```
AI Agent (sandbox_ue5cli.py) ←──socket:55557──→ UnrealMCP Plugin ←──→ UE5 Editor
```

---

## KNOWLEDGE BASE INDEX

| File | Contents | When to Read |
|---|---|---|
| `00_AGENT_KNOWLEDGE_BASE.md` | **This file** — master index, rules, quick reference | FIRST — always |
| `01_BLUEPRINT_FUNDAMENTALS.md` | Variables, nodes, flow control, math, traces, timelines, delta time, shortcuts | Before any BP graph work |
| `02_BLUEPRINT_COMMUNICATION.md` | Direct ref, casting, dispatchers, interfaces, Level BP, Game Instance, save/load | Before connecting BPs together |
| `03_GAMEPLAY_FRAMEWORK.md` | Actor, Pawn, Character, Controller, GameMode, GameInstance, round systems | Before creating new BP classes |
| `04_AI_SYSTEMS.md` | AIController, Blackboard, BT, NavMesh, PawnSensing, AI Perception, EQS, patterns | Before any AI work |
| `05_ANIMATION_SYSTEM.md` | ABP, State Machines, Blend Spaces, Montages, Notifies, Slots, IK | Before any animation work |
| `06_UI_UMG_SYSTEMS.md` | Widget types, HUD patterns, bindings, animations, input modes, dialogue UI | Before any UI work |
| `07_DATA_STRUCTURES.md` | Arrays, Sets, Maps, Enums, Structs, Data Tables, flow control deep-dive | Before working with data |
| `08_MATERIALS_AND_RENDERING.md` | PBR, material nodes, masters, instances, decals, vertex paint, Lumen, RVT | Before any material work |
| `09_NIAGARA_VFX.md` | All Niagara modules, renderers, events, GPU vs CPU, VFX recipes, integration | Before any VFX work |
| `10_WORLD_BUILDING.md` | World Partition, Landscape, PCG node reference, lighting, Sequencer | Before level design work |
| `11_BLUEPRINT_LIBRARIES_AND_COMPONENTS.md` | Function Libraries, Macro Libraries, Actor/Scene Components, procedural gen, VR patterns | Before creating reusable systems |
| `12_MCP_TOOL_USAGE_GUIDE.md` | **Every MCP command** — exact params, pin names, exec_python patterns, error ref | Before using ANY MCP tool |
| `13_TOOL_EXPANSION_ROADMAP.md` | 20 new commands to implement — specs, priority, workarounds | When current tools aren't enough |
| `14_DANTOOINE_PROJECT_REFERENCE.md` | All 49 assets, 52 folders, implementation status, pending tasks, asset paths | For all Dantooine-specific work |
| `15_INPUT_SYSTEM_AND_UMG.md` | Enhanced Input deep-dive, IMC setup, Widget Blueprint patterns, dialogue/quest/sparring HUD | Extended Input/UI reference |
| `16_ANIMATION_DEEP_DIVE.md` | ABP deep-dive, State Machines, Blend Spaces, Montages, IK, Notifies, Dantooine ABP reference | Advanced animation work |
| `17_GAME_SYSTEMS_COOKBOOK.md` | Step-by-step recipes: health/damage, interaction, dialogue, quests, sparring, save/load | Implementation of all game systems |
| `18_PACKAGING_AND_OPTIMIZATION.md` | Build configs, packaging steps, profiling commands, Blueprint/rendering/memory optimization | Before shipping or performance testing |

---

## ⚠️ CRITICAL PARAMETER CORRECTIONS

> These bugs were discovered by reading the plugin C++ source. The docs in 12_MCP_TOOL_USAGE_GUIDE.md have been corrected, but this table provides a quick safety reference.

| Command | ❌ WRONG (do not use) | ✅ CORRECT |
|---|---|---|
| `set_game_mode_for_level` | `"game_mode_path": "/Game/.../BP_DantooineGameMode"` | `"game_mode_name": "BP_DantooineGameMode"` |
| `implement_blueprint_interface` | `"interface_path": "/Game/Dantooine/Interfaces/BPI_Interactable"` | `"interface_name": "BPI_Interactable"` |
| `create_data_table` | `"row_struct_path": "..."` | `"row_struct": "..."` |
| `add_blackboard_key` | ❌ Command does not exist | Use `create_blackboard` with `"keys":[{...}]` array |

**Rule**: When in doubt, the parameter name is the **asset name only** (no path, no prefix `/Game/`). The plugin resolves paths internally by searching the asset registry.

---

## MANDATORY AGENT RULES

### Rule 1: Read Before Acting
Before ANY action in UE5:
1. `12_MCP_TOOL_USAGE_GUIDE.md` — know which commands exist and their EXACT parameters
2. The relevant KB file for the system you're touching (AI → file 04, UI → file 06, etc.)
3. `14_DANTOOINE_PROJECT_REFERENCE.md` — know what already exists

### Rule 2: Never Guess — Verify
```
BAD:  "I'll try 'add_variable_to_blueprint' and see if it works"
GOOD: Check 12_MCP_TOOL_USAGE_GUIDE.md → it's not listed → use exec_python instead
```

### Rule 3: Always Compile After Node Changes
```
EVERY batch of node additions/connections → compile_blueprint
Uncompiled Blueprint = broken at runtime, no error until you run
```

### Rule 4: Get IDs First, Connect Second
```
NEVER hardcode GUIDs
ALWAYS: add_node → note returned node_id → use that id in connect_blueprint_nodes
If ID is lost: get_blueprint_nodes to retrieve it
```

### Rule 5: Stop and Report Missing Assets
```
If an asset referenced in the project guides does NOT exist:
  STOP → Report to user: "Asset X is missing. Please create it first."
  DO NOT invent a substitute path or skip silently
```

### Rule 6: Naming Conventions Are Mandatory
All assets MUST follow naming conventions in `12_MCP_TOOL_USAGE_GUIDE.md § Naming Conventions`.
A wrongly-named asset cannot be found by the project's other Blueprints.

### Rule 7: Use exec_python for Custom Paths
`create_blueprint` hardcodes `/Game/Blueprints/`. 
**Always use** `exec_python` with `create_asset` when creating assets in Dantooine folders.

### Rule 8: SpawnDefaultController for Runtime AI
Any AI Character/Pawn spawned at runtime via `Spawn Actor from Class` needs:
```
Spawn Actor from Class → Return Value → SpawnDefaultController
OR in the AI pawn's BeginPlay: Event BeginPlay → SpawnDefaultController
```
Without this: AI pawn exists but has no brain → no movement, no BT execution.

### Rule 9: Delta Time for Movement
```
ANY value applied to movement per-frame MUST be multiplied by Delta Seconds (from Event Tick)
Without: movement is frame-rate dependent — broken at 30fps vs 120fps
With: 300 units/second regardless of frame rate
```

### Rule 10: Responsibility Principle
```
Player Blueprint = handles player death, player input, player state
NPC Blueprint = handles NPC patrol, NPC dialogue
GameMode = handles game rules, win/lose
Level Blueprint = level-specific triggers ONLY (not game rules)
```

### Rule 11: Check Is Valid Before Using References
```
Get Player Character → Cast To BP_PlayerJediCharacter → Cast Failed → DO NOT PROCEED
Always handle Cast Failed path
Always check Is Valid on any Get/Find result before using it
```

### Rule 12: Parent Classes Use C++ Names
```
WRONG: "GameMode"  → CORRECT: "GameModeBase"
WRONG: "ACharacter" → CORRECT: "Character"
WRONG: "AController" → CORRECT: "PlayerController" or "AIController"
```

---

## PROJECT: ENCLAVE PROJECT — DANTOOINE

### Project Path
```
C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Project2\EnclaveProject
```

### Content Root
```
/Game/Dantooine/
```

### Build Order (from AI Developer Execution Guide)
```
Phase 1 — Data Layer (DONE ✅):
  ✅ Enums: E_QuestStage, E_NPCDialogueMode, E_InteractableType, E_SparringState
  ✅ Structs: ST_DialogueLine, ST_DialogueNode, ST_DialogueChoice, ST_NPCBarkSet, ST_SparConfig
  ✅ Interfaces: BPI_Interactable, BPI_DialogueParticipant, BPI_CombatReceiver
  ✅ Input: IA_Move, IA_Look, IA_Jump, IA_Interact, IA_Attack, IA_Block, IMC_Dantooine

Phase 2 — Core Framework (DONE ✅):
  ✅ BP_DantooineGameMode (parent: GameModeBase)
  ✅ BP_DantooinePlayerController (parent: PlayerController)
  ✅ BP_PlayerJediCharacter (parent: Character)
  ✅ BP_DantooineQuestManager (parent: Actor)

Phase 3 — UI (DONE ✅):
  ✅ WBP_HUD
  ✅ WBP_DialogueBox
  ✅ WBP_QuestTracker
  ✅ WBP_InteractPrompt
  ✅ WBP_SparringHUD
  ✅ WBP_LevelComplete

Phase 4 — World Actors (DONE ✅):
  ✅ BP_MasterJedi (parent: Character)
  ✅ BP_LightsaberWorkbench (parent: Actor)
  ✅ BP_TrainingAreaTrigger (parent: Actor)
  ✅ BP_LevelCompletionHandler (parent: Actor)

Phase 5 — Ambient Systems (DONE ✅):
  ✅ BP_SkyBirdShip (parent: Actor)
  ✅ BP_RoamingNPC_Base (parent: Character)
  ✅ BP_RoamingNPC_StudentA (parent: Character)
  ✅ BP_RoamingNPC_StudentB (parent: Character)

Phase 6 — Combat + AI (DONE ✅):
  ✅ BP_SparringOpponent (parent: Character)
  ✅ BP_NPC_AIController (parent: AIController)
  ✅ BP_Sparring_AIController (parent: AIController)
  ✅ BB_RoamingNPC, BB_Sparring (Blackboards)
  ✅ BT_RoamingNPC, BT_Sparring (Behavior Trees)
  ✅ BTT_FindRandomPatrol (parent: BTTask_BlueprintBase)

Phase 7 — Animation (DONE ✅ — needs skeleton assignment):
  ✅ ABP_PlayerJedi (assign SK_PlayerJedi skeleton when imported)
  ✅ ABP_RoamingNPC (assign SK_NPC skeleton when imported)
  ✅ ABP_SparringOpponent (assign SK_SparringOpponent skeleton when imported)

Phase 8 — Cinematics (DONE ✅):
  ✅ LS_LightsaberBuild (Level Sequence)

Phase 9 — PENDING (awaiting artist assets):
  ⏳ Import Skeletal Meshes + assign to ABPs
  ⏳ Configure IMC_Dantooine bindings (create_input_mapping)
  ⏳ Set GameMode → use: set_game_mode_for_level '{"game_mode_name":"BP_DantooineGameMode"}'
  ⏳ Build Behavior Tree node graphs in BT Editor (manual — no MCP BT graph commands)
  ⏳ Add Blackboard keys → RECREATE BB_ assets using create_blackboard with "keys":[] array
  ⏳ Implement Blueprint interfaces → implement_blueprint_interface '{"blueprint_name":"X","interface_name":"BPI_Y"}'
  ⏳ Build Widget layouts in Designer (manual — UMG canvas layout not scriptable)
  ⏳ Wire Blueprint logic graphs (use 12_MCP_TOOL_USAGE_GUIDE workflow patterns A–H)
```

---

## QUICK REFERENCE: MOST COMMON PATTERNS

### Start Any Agent Session
```bash
# 1. Verify plugin is connected
python3 sandbox_ue5cli.py get_actors_in_level '{}'

# 2. Check what already exists in Dantooine
python3 sandbox_ue5cli.py exec_python '{"code":"import unreal\nassets=unreal.EditorAssetLibrary.list_assets(\"/Game/Dantooine\",recursive=True,include_folder=False)\nprint(len(assets),\"assets\")"}'
```

### Create a Blueprint in the Right Folder
```bash
python3 sandbox_ue5cli.py exec_python '{
  "code": "import unreal\nat=unreal.AssetToolsHelpers.get_asset_tools()\nf=unreal.BlueprintFactory()\nf.set_editor_property(\"parent_class\",unreal.Character)\na=at.create_asset(\"BP_NewNPC\",\"/Game/Dantooine/Blueprints/NPC\",unreal.Blueprint,f)\nprint(\"OK\" if a else \"FAIL\")"
}'
```

### Wire Event Tick → Forward Movement
```bash
# 1. Add Event Tick
python3 sandbox_ue5cli.py add_blueprint_event_node '{"blueprint_name":"BP_X","graph_name":"EventGraph","event_name":"ReceiveTick","node_position":{"x":-400,"y":0}}'
# 2. Add GetActorForwardVector
python3 sandbox_ue5cli.py add_blueprint_function_node '{"blueprint_name":"BP_X","graph_name":"EventGraph","function_name":"GetActorForwardVector","node_position":{"x":-200,"y":100}}'
# 3. Add Speed GET
python3 sandbox_ue5cli.py add_blueprint_variable_get_node '{"blueprint_name":"BP_X","graph_name":"EventGraph","variable_name":"Speed","node_position":{"x":-200,"y":200}}'
# 4. Add Multiply
python3 sandbox_ue5cli.py add_blueprint_function_node '{"blueprint_name":"BP_X","graph_name":"EventGraph","function_name":"Multiply","node_position":{"x":0,"y":100}}'
# 5. Add AddActorWorldOffset
python3 sandbox_ue5cli.py add_blueprint_function_node '{"blueprint_name":"BP_X","graph_name":"EventGraph","function_name":"AddActorWorldOffset","node_position":{"x":200,"y":0}}'
# 6. Get node IDs
python3 sandbox_ue5cli.py get_blueprint_nodes '{"blueprint_name":"BP_X","graph_name":"EventGraph"}'
# 7. Connect (use actual IDs from step 6)
python3 sandbox_ue5cli.py connect_blueprint_nodes '{"blueprint_name":"BP_X","graph_name":"EventGraph","source_node_id":"TICK_ID","target_node_id":"OFFSET_ID","source_pin":"then","target_pin":"execute"}'
# 8. Compile
python3 sandbox_ue5cli.py compile_blueprint '{"blueprint_name":"BP_X"}'
```

### Wire AIController BeginPlay → Run Behavior Tree
```bash
python3 sandbox_ue5cli.py add_blueprint_event_node '{"blueprint_name":"BP_NPC_AIController","graph_name":"EventGraph","event_name":"ReceiveBeginPlay","node_position":{"x":-200,"y":0}}'
python3 sandbox_ue5cli.py add_blueprint_function_node '{"blueprint_name":"BP_NPC_AIController","graph_name":"EventGraph","function_name":"RunBehaviorTree","node_position":{"x":100,"y":0}}'
# Get node IDs → connect → compile
```

### Create Widget and Add to Viewport
```bash
# In PlayerController BeginPlay
# CreateWidget node → Store ref → AddToViewport
python3 sandbox_ue5cli.py add_blueprint_function_node '{"blueprint_name":"BP_DantooinePlayerController","graph_name":"EventGraph","function_name":"CreateWidget","node_position":{"x":200,"y":0}}'
```

---

## BLUEPRINT PARENT CLASS QUICK LOOKUP

| Blueprint Purpose | Parent Class (exact C++ name) |
|---|---|
| Static props, managers, triggers | `Actor` |
| Controllable vehicle/simple pawn | `Pawn` |
| Walking character (player/NPC) | `Character` |
| Player input/HUD handling | `PlayerController` |
| AI decision making | `AIController` |
| Game rules (server-side) | `GameModeBase` |
| Persistent cross-level data | `GameInstance` |
| Replicated game state | `GameStateBase` |
| Per-player state | `PlayerState` |
| Disk save file | `SaveGame` |
| Reusable logic (no position) | `ActorComponent` |
| Reusable with transform | `SceneComponent` |
| HUD/Menu screen | Use `WidgetBlueprintFactory` |
| AI decision tree | Use `BehaviorTreeFactory` |
| AI data store | Use `BlackboardDataFactory` |
| Custom BT action | `BTTask_BlueprintBase` |
| Custom BT condition | `BTDecorator_BlueprintBase` |
| Custom BT periodic update | `BTService_BlueprintBase` |
| Global static utilities | `BlueprintFunctionLibrary` |

---

## SOURCES — Books Used to Build This Knowledge Base

1. **Blueprints Visual Scripting for Unreal Engine 5** — Marcos Romero (3rd Ed., Packt 2023)
   - 566 pages, 20 chapters + appendix
   - Chapters 1–4: Blueprint editor, variables, OOP, communication
   - Chapters 5–11: Game building (FPS, AI, UI, save/load, game states)
   - Chapters 12–15: Build/publish, data structures, math/traces, BP tips
   - Chapters 16–20: VR, animation BPs, libraries/components, procedural, configurator
   - Full text extracted and integrated into KB files 01–11

2. **Game Development with Unreal Engine 5 Volume 1: Design Phase** — Tiow Wee Tan (Apress 2024)
   - 423 pages, 7 chapters
   - Ch1: UE5 setup, core systems overview
   - Ch2: Landscape, World Partition, heightmap import
   - Ch3: Auto-blend materials, material layering
   - Ch4: Asset import, PCG framework (full node reference)
   - Ch5: Runtime Virtual Textures, landscape blending
   - Ch6: Lumen GI, reflections, post-process
   - Ch7: Niagara VFX (3 complete examples)
   - Full text extracted into KB files 08–10

3. **Mastering Technical Art in Unreal Engine** — Greg Penninck & Stuart Butler (CRC Press 2025)
   - 251 pages, 15+ chapters
   - Ch1–2: Technical art role, rendering pipeline, G-Buffer
   - Ch3–7: Materials, PBR, master materials, instances, vertex painting
   - Ch8–11: VFX materials, Niagara intro, collision events, ribbon/beam
   - Ch12–15: Sub-UV, advanced particles, optimization
   - Full text extracted into KB files 08–09

4. **Unreal Engine Blueprint Game Developer** — Asadullah Alam (BPB Publications)
   - 386 pages (image-based PDF — text extraction not possible)
   - Content summarized via AI analysis into foundational Blueprint patterns
   - Covered topics: project structure, gameplay systems, Blueprint patterns, game loops
   - Integrated into KB files 01–03

---

## CHANGE LOG

| Date | Change |
|---|---|
| 2026-04-10 | Initial knowledge base created from project experience |
| 2026-04-10 | Dantooine project setup complete — 49 assets, 52 folders |
| 2026-04-10 | **MAJOR UPDATE**: Full text extraction from all 4 books, comprehensive rebuild of all 14 KB files |
| 2026-04-10 | Added: 01_BLUEPRINT_FUNDAMENTALS (complete, 24K chars) |
| 2026-04-10 | Added: 02_BLUEPRINT_COMMUNICATION (complete, 8.7K chars) |
| 2026-04-10 | Added: 03_GAMEPLAY_FRAMEWORK (complete, 10.9K chars) |
| 2026-04-10 | Added: 04_AI_SYSTEMS (complete, 16K chars) |
| 2026-04-10 | Added: 05_ANIMATION_SYSTEM (complete, 12K chars) |
| 2026-04-10 | Added: 06_UI_UMG_SYSTEMS (complete, 8.4K chars) |
| 2026-04-10 | Added: 07_DATA_STRUCTURES (complete, 10.8K chars) |
| 2026-04-10 | Added: 08_MATERIALS_AND_RENDERING (complete, 13.9K chars) |
| 2026-04-10 | Added: 09_NIAGARA_VFX (complete, 10.4K chars) |
| 2026-04-10 | Added: 10_WORLD_BUILDING (complete, 9.2K chars) |
| 2026-04-10 | Added: 11_BLUEPRINT_LIBRARIES_AND_COMPONENTS (complete, 10K chars) |
| 2026-04-10 | Added: 12_MCP_TOOL_USAGE_GUIDE (definitive, 27K chars) |
| 2026-04-10 | Added: 13_TOOL_EXPANSION_ROADMAP (20 new commands, 10K chars) |
| 2026-04-10 | Added: 14_DANTOOINE_PROJECT_REFERENCE (complete asset registry, 14K chars) |
| 2026-04-10 | Added: 15_INPUT_SYSTEM_AND_UMG (Enhanced Input + UMG deep-dive, 12.6K chars) |
| 2026-04-10 | Added: 16_ANIMATION_DEEP_DIVE (ABP, State Machines, Montages, IK, Dantooine reference, 10.9K chars) |
| 2026-04-10 | Added: 17_GAME_SYSTEMS_COOKBOOK (complete recipe book for all Dantooine systems, 12.5K chars) |
| 2026-04-10 | Added: 18_PACKAGING_AND_OPTIMIZATION (build configs, packaging, profiling, optimization, 10.9K chars) |
| 2026-04-10 | **FINAL REVISION**: All 19 KB files (00–18) verified complete; INDEX.md created; 14_DANTOOINE_PROJECT_REFERENCE expanded with Phase 9 implementation detail |
| 2026-04-10 | **BUG FIXES**: 3 parameter name corrections discovered via C++ source audit: `game_mode_path`→`game_mode_name`, `interface_path`→`interface_name`, `row_struct_path`→`row_struct`. Roadmap updated: 6 commands marked ✅ DONE, workarounds rewritten. |
