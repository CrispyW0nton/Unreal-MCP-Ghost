# Dantooine Project Reference — Complete Asset Registry
> Source: Dantooine_Manual_Preparation_Guide.pdf + Dantooine_AI_Developer_Execution_Guide.pdf
> Complete record of all 49 created assets, folder structure, and implementation status.

---

## Project Info

| Field | Value |
|---|---|
| **Project Name** | EnclaveProject |
| **Course** | GAM270, Academy of Art University |
| **Year** | 2026 |
| **Engine** | Unreal Engine 5.6 |
| **Project Path** | `C:\Users\NewAdmin\Documents\Academy of Art University\2026\Gam270\Project2\EnclaveProject` |
| **Content Root** | `/Game/Dantooine/` |
| **Plugin** | Unreal-MCP-Ghost (port 55557) |
| **GitHub** | https://github.com/CrispyW0nton/Unreal-MCP-Ghost |

---

## Folder Structure (52 Folders)

```
/Game/Dantooine/
├── AI/
│   ├── BehaviorTrees/
│   ├── Blackboard/
│   ├── Decorators/
│   ├── Services/
│   └── Tasks/
├── Animation/
│   ├── BlendSpaces/
│   ├── MasterJedi/
│   ├── Montages/
│   ├── NPCs/
│   ├── Player/
│   ├── Shared/
│   └── SparringOpponent/
├── Art/
│   ├── Audio/
│   │   ├── Dialogue/
│   │   ├── Music/
│   │   └── SFX/
│   ├── Characters/
│   ├── Environment/
│   ├── FX/
│   └── Weapons/
│       └── Lightsaber/
├── Blueprints/
│   ├── AI/
│   ├── Cinematics/
│   ├── Combat/
│   ├── Core/
│   ├── Debug/
│   ├── Interactables/
│   ├── NPC/
│   ├── Player/
│   ├── Quest/
│   ├── Triggers/
│   └── UI/
├── Data/
│   ├── DataAssets/
│   ├── DataTables/
│   ├── Dialogue/
│   ├── Enums/
│   ├── Input/
│   └── Structs/
├── Interfaces/
│   ├── BPI_CombatReceiver/
│   ├── BPI_DialogueParticipant/
│   └── BPI_Interactable/
├── Maps/
│   └── Dantooine_Level/
├── Sequences/
│   └── LightsaberBuild/
└── Widgets/
```

---

## Complete Asset Registry (49 Assets)

### Data Layer — Enums (4)
| Asset | Path | Status |
|---|---|---|
| `E_QuestStage` | `/Game/Dantooine/Data/Enums/` | ✅ Created |
| `E_NPCDialogueMode` | `/Game/Dantooine/Data/Enums/` | ✅ Created |
| `E_InteractableType` | `/Game/Dantooine/Data/Enums/` | ✅ Created |
| `E_SparringState` | `/Game/Dantooine/Data/Enums/` | ✅ Created |

**E_QuestStage values:** None, Phase1_ArriveAtWorkbench, Phase2_GatherComponents, Phase3_AssembleLightsaber, Phase4_SparringTrial, Complete
**E_NPCDialogueMode values:** Idle, Greeting, InConversation, Farewell
**E_InteractableType values:** None, Workbench, QuestItem, Door, CollectiblePart, InformationTerminal
**E_SparringState values:** Idle, Waiting, Active, Paused, PlayerWon, OpponentWon

### Data Layer — Structs (5)
| Asset | Path | Status |
|---|---|---|
| `ST_DialogueLine` | `/Game/Dantooine/Data/Structs/` | ✅ Created |
| `ST_DialogueNode` | `/Game/Dantooine/Data/Structs/` | ✅ Created |
| `ST_DialogueChoice` | `/Game/Dantooine/Data/Structs/` | ✅ Created |
| `ST_NPCBarkSet` | `/Game/Dantooine/Data/Structs/` | ✅ Created |
| `ST_SparConfig` | `/Game/Dantooine/Data/Structs/` | ✅ Created |

### Data Layer — Interfaces (3)
| Asset | Path | Status | Functions |
|---|---|---|---|
| `BPI_Interactable` | `/Game/Dantooine/Interfaces/` | ✅ Created | `Interact(Instigator: Actor)`, `GetInteractionText() → Text` |
| `BPI_DialogueParticipant` | `/Game/Dantooine/Interfaces/` | ✅ Created | `StartDialogue(Partner: Actor)`, `EndDialogue`, `GetSpeakerName() → string` |
| `BPI_CombatReceiver` | `/Game/Dantooine/Interfaces/` | ✅ Created | `ReceiveHit(Damage: float, Direction: Vector)`, `GetCurrentHealth() → float` |

### Data Layer — Input (7)
| Asset | Path | Type | Status |
|---|---|---|---|
| `IA_Move` | `/Game/Dantooine/Data/Input/` | InputAction (Axis2D) | ✅ Created |
| `IA_Look` | `/Game/Dantooine/Data/Input/` | InputAction (Axis2D) | ✅ Created |
| `IA_Jump` | `/Game/Dantooine/Data/Input/` | InputAction (Digital) | ✅ Created |
| `IA_Interact` | `/Game/Dantooine/Data/Input/` | InputAction (Digital) | ✅ Created |
| `IA_Attack` | `/Game/Dantooine/Data/Input/` | InputAction (Digital) | ✅ Created |
| `IA_Block` | `/Game/Dantooine/Data/Input/` | InputAction (Digital) | ✅ Created |
| `IMC_Dantooine` | `/Game/Dantooine/Data/Input/` | InputMappingContext | ✅ Created |

**IMC_Dantooine bindings to assign (manually in editor):**
- IA_Move → WASD keys + Left Stick
- IA_Look → Mouse XY + Right Stick
- IA_Jump → Spacebar + South Button (A/X)
- IA_Interact → E key + West Button (X/Square)
- IA_Attack → Left Mouse Button + Right Trigger
- IA_Block → Right Mouse Button + Left Trigger

### Core Framework Blueprints (4)
| Asset | Path | Parent | Status |
|---|---|---|---|
| `BP_DantooineGameMode` | `/Game/Dantooine/Blueprints/Core/` | GameModeBase | ✅ Created |
| `BP_DantooinePlayerController` | `/Game/Dantooine/Blueprints/Core/` | PlayerController | ✅ Created |
| `BP_SkyBirdShip` | `/Game/Dantooine/Blueprints/Core/` | Actor | ✅ Created |
| `BP_DantooineQuestManager` | `/Game/Dantooine/Blueprints/Quest/` | Actor | ✅ Created |

### Player Blueprint (1)
| Asset | Path | Parent | Status |
|---|---|---|---|
| `BP_PlayerJediCharacter` | `/Game/Dantooine/Blueprints/Player/` | Character | ✅ Created |

**To implement (manual in editor):**
- Add SpringArm + Camera components
- Bind Enhanced Input actions (IA_Move, IA_Look, IA_Jump, IA_Attack, IA_Block, IA_Interact)
- Variables: Health (float=100), MaxHealth (float=100), IsAttacking (bool), IsBlocking (bool), HasLightsaber (bool)

### Quest Blueprints (2)
| Asset | Path | Status |
|---|---|---|
| `BP_DantooineQuestManager` | `/Game/Dantooine/Blueprints/Quest/` | ✅ Created |
| `BP_LevelCompletionHandler` | `/Game/Dantooine/Blueprints/Quest/` | ✅ Created |

### NPC Blueprints (5)
| Asset | Path | Parent | Status |
|---|---|---|---|
| `BP_MasterJedi` | `/Game/Dantooine/Blueprints/NPC/` | Character | ✅ Created |
| `BP_RoamingNPC_Base` | `/Game/Dantooine/Blueprints/NPC/` | Character | ✅ Created |
| `BP_RoamingNPC_StudentA` | `/Game/Dantooine/Blueprints/NPC/` | Character | ✅ Created |
| `BP_RoamingNPC_StudentB` | `/Game/Dantooine/Blueprints/NPC/` | Character | ✅ Created |
| `BP_SparringOpponent` | `/Game/Dantooine/Blueprints/Combat/` | Character | ✅ Created |

**Reparenting needed (manual in editor):**
- `BP_RoamingNPC_StudentA` → Reparent to `BP_RoamingNPC_Base`
- `BP_RoamingNPC_StudentB` → Reparent to `BP_RoamingNPC_Base`

### World Actor Blueprints (3)
| Asset | Path | Implements | Status |
|---|---|---|---|
| `BP_LightsaberWorkbench` | `/Game/Dantooine/Blueprints/Interactables/` | BPI_Interactable | ✅ Created |
| `BP_TrainingAreaTrigger` | `/Game/Dantooine/Blueprints/Triggers/` | — | ✅ Created |
| `BP_LevelCompletionHandler` | `/Game/Dantooine/Blueprints/Quest/` | — | ✅ Created |

### AI Blueprints (2 Controllers)
| Asset | Path | Parent | Manages | Status |
|---|---|---|---|---|
| `BP_NPC_AIController` | `/Game/Dantooine/Blueprints/AI/` | AIController | BP_RoamingNPC_Base | ✅ Created |
| `BP_Sparring_AIController` | `/Game/Dantooine/Blueprints/AI/` | AIController | BP_SparringOpponent | ✅ Created |

### AI Assets (5)
| Asset | Path | Type | Status |
|---|---|---|---|
| `BB_RoamingNPC` | `/Game/Dantooine/AI/Blackboard/` | BlackboardData | ✅ Created |
| `BB_Sparring` | `/Game/Dantooine/AI/Blackboard/` | BlackboardData | ✅ Created |
| `BT_RoamingNPC` | `/Game/Dantooine/AI/BehaviorTrees/` | BehaviorTree | ✅ Created |
| `BT_Sparring` | `/Game/Dantooine/AI/BehaviorTrees/` | BehaviorTree | ✅ Created |
| `BTT_FindRandomPatrol` | `/Game/Dantooine/AI/Tasks/` | BT Task Blueprint | ✅ Created |

**Blackboard keys to add (manual in editor):**

BB_RoamingNPC:
- `PatrolLocation` (Vector)
- `IsTalking` (Bool)
- `ConversationTarget` (Object)
- `WaitDuration` (Float)

BB_Sparring:
- `TargetActor` (Object)
- `FightActive` (Bool)
- `HitsTaken` (Int)

### Animation Blueprints (3)
| Asset | Path | Skeleton | Status |
|---|---|---|---|
| `ABP_PlayerJedi` | `/Game/Dantooine/Animation/Player/` | SK_PlayerJedi (assign after import) | ✅ Created |
| `ABP_RoamingNPC` | `/Game/Dantooine/Animation/NPCs/` | SK_NPC_Student (assign after import) | ✅ Created |
| `ABP_SparringOpponent` | `/Game/Dantooine/Animation/SparringOpponent/` | SK_SparringOpponent (assign after import) | ✅ Created |

### UI Widgets (6)
| Asset | Path | Status | Purpose |
|---|---|---|---|
| `WBP_HUD` | `/Game/Dantooine/Widgets/` | ✅ Created | Main gameplay HUD |
| `WBP_DialogueBox` | `/Game/Dantooine/Widgets/` | ✅ Created | NPC conversation UI |
| `WBP_QuestTracker` | `/Game/Dantooine/Widgets/` | ✅ Created | Quest progress display |
| `WBP_InteractPrompt` | `/Game/Dantooine/Widgets/` | ✅ Created | "[E] to Interact" prompt |
| `WBP_SparringHUD` | `/Game/Dantooine/Widgets/` | ✅ Created | Combat phase UI |
| `WBP_LevelComplete` | `/Game/Dantooine/Widgets/` | ✅ Created | Victory/completion screen |

### Sequences (1)
| Asset | Path | Status |
|---|---|---|
| `LS_LightsaberBuild` | `/Game/Dantooine/Sequences/LightsaberBuild/` | ✅ Created |

---

## Manual Art Assets Still Needed (Artist Work)

### Skeletal Meshes (required to assign to ABPs)
```
SK_PlayerJedi          → assign to ABP_PlayerJedi
SK_MasterJedi          → goes on BP_MasterJedi
SK_NPC_Student_A       → assign to ABP_RoamingNPC (StudentA variant)
SK_NPC_Student_B       → assign to ABP_RoamingNPC (StudentB variant)
SK_SparringOpponent    → assign to ABP_SparringOpponent
```

### Static Meshes
```
SM_LightsaberWorkbench → assign to BP_LightsaberWorkbench mesh component
SM_TrainingDummy       → scene decoration
SM_DantooineSkyShip    → assign to BP_SkyBirdShip
```

### Animation Sequences (import into appropriate Animation folders)
```
AN_Player_Idle         → ABP_PlayerJedi Idle state
AN_Player_Walk         → ABP_PlayerJedi / BS_Locomotion
AN_Player_Run          → ABP_PlayerJedi / BS_Locomotion
AN_Player_Jump         → ABP_PlayerJedi Jump state
AN_Player_Attack       → AM_LightsaberAttack montage
AN_Player_Block        → ABP_PlayerJedi Block state
AN_NPC_Idle            → ABP_RoamingNPC Idle
AN_NPC_Walk            → ABP_RoamingNPC / BS_NPCLocomotion
AN_Sparring_Attack     → ABP_SparringOpponent combat
```

### Audio
```
SFX_Saber_Hum          → Ambient lightsaber loop
SFX_Saber_Swing        → Attack AnimNotify
SFX_Saber_Block        → Block AnimNotify
SFX_Workbench_Assemble → Workbench interaction
MX_DantooineAmbient    → Background music loop
MX_CombatIntensity     → Sparring background music
```

### VFX Niagara Systems (to create)
```
NS_SaberGlow           → Lightsaber ambient glow
NS_SaberTrail          → Attack swing trail
NS_WorkbenchSparks     → Assembly sequence
NS_LevelComplete       → Victory celebration
NS_ForceField          → Training area boundary
```

---

## Phase 9 — Implementation Notes

Phase 9 covers all work that comes AFTER the initial asset creation. This is where the game actually runs.

### 9A: Project Settings (Manual — UE5 Editor)
These must be set in the editor UI, not via MCP:
```
Project Settings → Maps & Modes:
  Default GameMode: BP_DantooineGameMode
  Game Default Map: /Game/Dantooine/Maps/Dantooine_Level/Dantooine_Level
  Editor Startup Map: same

Project Settings → Input:
  Default Input Component Class: EnhancedInputComponent (already default in UE5.3+)
```

**OR via MCP (preferred for GameMode):**
```bash
python3 sandbox_ue5cli.py set_game_mode_for_level '{
  "game_mode_path": "/Game/Dantooine/Blueprints/Core/BP_DantooineGameMode"
}'
```

---

### 9B: Blackboard Keys (Manual — BB Editor)

Open each Blackboard in the editor and add keys:

**BB_RoamingNPC** (open `/Game/Dantooine/AI/Blackboard/BB_RoamingNPC`):
- Add Key → Vector → name `PatrolLocation`
- Add Key → Bool → name `IsTalking`
- Add Key → Object → name `ConversationTarget`
- Add Key → Float → name `WaitDuration`

**BB_Sparring** (open `/Game/Dantooine/AI/Blackboard/BB_Sparring`):
- Add Key → Object → name `TargetActor`
- Add Key → Bool → name `FightActive`
- Add Key → Int → name `HitsTaken`

---

### 9C: Blueprint Interface Implementations (Can use MCP)

#### BP_LightsaberWorkbench must implement BPI_Interactable
```bash
python3 sandbox_ue5cli.py implement_blueprint_interface '{
  "blueprint_name": "BP_LightsaberWorkbench",
  "interface_path": "/Game/Dantooine/Interfaces/BPI_Interactable"
}'
```

#### BP_MasterJedi must implement BPI_Interactable and BPI_DialogueParticipant
```bash
python3 sandbox_ue5cli.py implement_blueprint_interface '{
  "blueprint_name": "BP_MasterJedi",
  "interface_path": "/Game/Dantooine/Interfaces/BPI_Interactable"
}'
python3 sandbox_ue5cli.py implement_blueprint_interface '{
  "blueprint_name": "BP_MasterJedi",
  "interface_path": "/Game/Dantooine/Interfaces/BPI_DialogueParticipant"
}'
```

#### BP_SparringOpponent must implement BPI_CombatReceiver
```bash
python3 sandbox_ue5cli.py implement_blueprint_interface '{
  "blueprint_name": "BP_SparringOpponent",
  "interface_path": "/Game/Dantooine/Interfaces/BPI_CombatReceiver"
}'
```

---

### 9D: AI Controller Assignment

#### Set AI Controllers on Character Blueprints
```bash
# RoamingNPC uses BP_NPC_AIController
python3 sandbox_ue5cli.py set_blueprint_ai_controller '{
  "blueprint_name": "BP_RoamingNPC_Base",
  "ai_controller_class": "BP_NPC_AIController",
  "auto_possess_ai": "PlacedInWorldOrSpawned"
}'

# SparringOpponent uses BP_Sparring_AIController
python3 sandbox_ue5cli.py set_blueprint_ai_controller '{
  "blueprint_name": "BP_SparringOpponent",
  "ai_controller_class": "BP_Sparring_AIController",
  "auto_possess_ai": "PlacedInWorldOrSpawned"
}'
```

---

### 9E: AIController BeginPlay Logic (MCP)

#### BP_NPC_AIController → Run BT_RoamingNPC
```bash
python3 sandbox_ue5cli.py add_blueprint_event_node '{
  "blueprint_name":"BP_NPC_AIController","graph_name":"EventGraph",
  "event_name":"ReceiveBeginPlay","node_position":{"x":-200,"y":0}}'
python3 sandbox_ue5cli.py add_blueprint_function_node '{
  "blueprint_name":"BP_NPC_AIController","graph_name":"EventGraph",
  "function_name":"RunBehaviorTree","node_position":{"x":100,"y":0}}'
# → get_blueprint_nodes → connect BeginPlay.then → RunBehaviorTree.execute
# → set RunBehaviorTree BTAsset pin to BT_RoamingNPC
python3 sandbox_ue5cli.py compile_blueprint '{"blueprint_name":"BP_NPC_AIController"}'
```

#### BP_Sparring_AIController → Run BT_Sparring
Same pattern but use `BT_Sparring`.

---

### 9F: PlayerController BeginPlay → Enhanced Input + HUD (MCP)

```bash
# BeginPlay node
python3 sandbox_ue5cli.py add_blueprint_event_node '{
  "blueprint_name":"BP_DantooinePlayerController","graph_name":"EventGraph",
  "event_name":"ReceiveBeginPlay","node_position":{"x":-400,"y":0}}'

# Get Enhanced Input Subsystem
python3 sandbox_ue5cli.py add_blueprint_function_node '{
  "blueprint_name":"BP_DantooinePlayerController","graph_name":"EventGraph",
  "function_name":"GetLocalPlayer","node_position":{"x":-200,"y":100}}'

# Add Mapping Context
python3 sandbox_ue5cli.py add_blueprint_function_node '{
  "blueprint_name":"BP_DantooinePlayerController","graph_name":"EventGraph",
  "function_name":"AddMappingContext","node_position":{"x":200,"y":0}}'

# Create HUD Widget
python3 sandbox_ue5cli.py add_blueprint_function_node '{
  "blueprint_name":"BP_DantooinePlayerController","graph_name":"EventGraph",
  "function_name":"CreateWidget","node_position":{"x":400,"y":200}}'

# Add HUD to Viewport
python3 sandbox_ue5cli.py add_blueprint_function_node '{
  "blueprint_name":"BP_DantooinePlayerController","graph_name":"EventGraph",
  "function_name":"AddToViewport","node_position":{"x":600,"y":200}}'

python3 sandbox_ue5cli.py compile_blueprint '{"blueprint_name":"BP_DantooinePlayerController"}'
```

---

### 9G: BP_PlayerJediCharacter Variables (MCP)
```bash
python3 sandbox_ue5cli.py add_blueprint_variable '{
  "blueprint_name":"BP_PlayerJediCharacter",
  "variable_name":"MaxHealth","variable_type":"Float","default_value":"100.0","is_exposed":true}'

python3 sandbox_ue5cli.py add_blueprint_variable '{
  "blueprint_name":"BP_PlayerJediCharacter",
  "variable_name":"CurrentHealth","variable_type":"Float","default_value":"100.0"}'

python3 sandbox_ue5cli.py add_blueprint_variable '{
  "blueprint_name":"BP_PlayerJediCharacter",
  "variable_name":"bIsDead","variable_type":"Boolean","default_value":"false"}'

python3 sandbox_ue5cli.py add_blueprint_variable '{
  "blueprint_name":"BP_PlayerJediCharacter",
  "variable_name":"bIsBlocking","variable_type":"Boolean","default_value":"false"}'

python3 sandbox_ue5cli.py compile_blueprint '{"blueprint_name":"BP_PlayerJediCharacter"}'
```

---

### 9H: NavMesh Setup (MCP)
```bash
python3 sandbox_ue5cli.py setup_navmesh '{
  "extent": {"x": 8000, "y": 8000, "z": 800},
  "location": {"x": 0, "y": 0, "z": 0},
  "rebuild": true
}'
```
After this, press `P` in the viewport to verify green nav mesh overlay covers the playable area.

---

### 9I: Input Action Bindings — Enhanced Input (MCP)

```bash
# IA_Move binding in BP_PlayerJediCharacter
python3 sandbox_ue5cli.py add_blueprint_enhanced_input_action_node '{
  "blueprint_name":"BP_PlayerJediCharacter","graph_name":"EventGraph",
  "action_asset":"/Game/Dantooine/Data/Input/IA_Move",
  "node_position":{"x":0,"y":0}}'

# IA_Jump binding
python3 sandbox_ue5cli.py add_blueprint_enhanced_input_action_node '{
  "blueprint_name":"BP_PlayerJediCharacter","graph_name":"EventGraph",
  "action_asset":"/Game/Dantooine/Data/Input/IA_Jump",
  "node_position":{"x":0,"y":200}}'

# IA_Attack binding
python3 sandbox_ue5cli.py add_blueprint_enhanced_input_action_node '{
  "blueprint_name":"BP_PlayerJediCharacter","graph_name":"EventGraph",
  "action_asset":"/Game/Dantooine/Data/Input/IA_Attack",
  "node_position":{"x":0,"y":400}}'

# IA_Interact binding
python3 sandbox_ue5cli.py add_blueprint_enhanced_input_action_node '{
  "blueprint_name":"BP_PlayerJediCharacter","graph_name":"EventGraph",
  "action_asset":"/Game/Dantooine/Data/Input/IA_Interact",
  "node_position":{"x":0,"y":600}}'
```

---

### 9J: IMC_Dantooine Configuration (Manual — Input Editor)

Open IMC_Dantooine and add mappings:
```
IA_Move → W/A/S/D keys (with WASD axis compositing)
IA_Look → Mouse XY 2D Axis
IA_Jump → Space bar
IA_Interact → E key
IA_Attack → Left Mouse Button
IA_Block → Right Mouse Button (hold)
```

---

### 9K: Reparent StudentA/B to Base (Manual)

1. Open `BP_RoamingNPC_StudentA` in Blueprint Editor
2. File → Reparent Blueprint → select `BP_RoamingNPC_Base`
3. Repeat for `BP_RoamingNPC_StudentB`

---

### 9L: Behavior Tree Graphs (Manual — BT Editor)

Open `BT_RoamingNPC`:
```
ROOT
└── Selector [Repeat=true via Decorator Loop]
      ├── Sequence [Blackboard: IsTalking == true]
      │     └── Wait (Duration: 999, abortable)
      └── Sequence (patrol loop)
            ├── BTT_FindRandomPatrol (sets BB: PatrolLocation)
            ├── Move To (BB: PatrolLocation, AcceptanceRadius: 50)
            └── Wait (Min: 2.0, Max: 5.0)
```

Open `BT_Sparring`:
```
ROOT
└── Selector
      ├── Sequence [Blackboard: FightActive == false]
      │     └── Wait (Duration: 0.5)
      └── Sequence [Blackboard: FightActive == true]
            ├── Move To (BB: TargetActor, AcceptanceRadius: 100)
            └── Task: ExecuteAttack (custom BTT)
```

---

### 9M: Animation Blueprints (After SK_ Import)

After importing skeletal meshes:
1. Open `ABP_PlayerJedi` → Class Defaults → Skeleton → assign `SK_PlayerJedi`
2. Open `ABP_RoamingNPC` → Class Defaults → Skeleton → assign `SK_NPC_Student_A` (or B)
3. Open `ABP_SparringOpponent` → Class Defaults → Skeleton → assign `SK_SparringOpponent`

Then via MCP (animation states):
```bash
python3 sandbox_ue5cli.py add_state_machine '{
  "blueprint_name": "ABP_PlayerJedi",
  "name": "LocomotionSM"}'

python3 sandbox_ue5cli.py add_animation_state '{
  "blueprint_name": "ABP_PlayerJedi",
  "state_machine_name": "LocomotionSM",
  "state_name": "Idle"}'

python3 sandbox_ue5cli.py add_animation_state '{
  "blueprint_name": "ABP_PlayerJedi",
  "state_machine_name": "LocomotionSM",
  "state_name": "Walk"}'

python3 sandbox_ue5cli.py add_state_transition '{
  "blueprint_name": "ABP_PlayerJedi",
  "state_machine_name": "LocomotionSM",
  "from_state": "Idle", "to_state": "Walk"}'

python3 sandbox_ue5cli.py add_state_transition '{
  "blueprint_name": "ABP_PlayerJedi",
  "state_machine_name": "LocomotionSM",
  "from_state": "Walk", "to_state": "Idle"}'
```

---

## Implementation Checklist

### What Agents Can Do Now (MCP commands ready)
- [x] Create any Blueprint class in correct folder
- [x] Add components (StaticMesh, CapsuleComponent, etc.)
- [x] Add Event Tick, BeginPlay nodes
- [x] Wire Tick → Movement logic
- [x] Set blueprint variable defaults
- [x] Add variables to Blueprint classes
- [x] Configure AI controller and pawn settings
- [x] Spawn blueprint actors in the level
- [x] Create widgets and add to viewport
- [x] Build behavior tree task logic
- [x] Set GameMode for level (`set_game_mode_for_level`)
- [x] Implement Blueprint Interfaces (`implement_blueprint_interface`)
- [x] Create State Machines + States + Transitions in ABP
- [x] Create Behavior Trees and Blackboards
- [x] Create Data Structures (structs, enums, data tables)
- [x] Setup NavMesh volume (`setup_navmesh`)
- [x] Add Enhanced Input Action nodes
- [x] Disconnect and rewire nodes (`disconnect_blueprint_nodes`)
- [x] Set literal values on node pins (`set_node_pin_value`)

### What Requires Manual Editor Work
- [ ] Add blackboard keys to BB_ assets (no MCP command for key editing)
- [ ] Reparent StudentA/B to BP_RoamingNPC_Base (Blueprint Editor only)
- [ ] Assign skeletons to ABP_ assets after SK_ mesh import (Editor → Class Defaults)
- [ ] Build full Behavior Tree node graph in BT Editor (composite/decorator/service nodes)
- [ ] Configure Input Mapping Context bindings (Input Editor)
- [ ] Build widget layouts in Designer view (UMG Designer)
- [ ] Add AnimNotify events to animation clips (Anim Sequence editor)
- [ ] Configure Blend Space axes and sample points (Blend Space editor)
- [ ] Set Project Default GameMode in Project Settings (or use `set_game_mode_for_level`)

### What Awaits Artist Assets
- [ ] Import skeletal meshes (SK_PlayerJedi, SK_MasterJedi, SK_NPC_Student_A/B, SK_SparringOpponent)
- [ ] Import animation sequences (AN_Player_Walk, AN_Player_Run, etc.)
- [ ] Import audio files (SFX_Saber_Hum, SFX_Saber_Swing, MX_DantooineAmbient)
- [ ] Create material instances for characters (MI_PlayerJedi, etc.)
- [ ] Create Niagara VFX systems (NS_SaberGlow, NS_SaberTrail, NS_WorkbenchSparks)

---

## Quick Reference: Asset Paths

All assets confirmed existing as of 2026-04-10:
```
/Game/Dantooine/Blueprints/Core/BP_DantooineGameMode
/Game/Dantooine/Blueprints/Core/BP_DantooinePlayerController
/Game/Dantooine/Blueprints/Core/BP_SkyBirdShip
/Game/Dantooine/Blueprints/Player/BP_PlayerJediCharacter
/Game/Dantooine/Blueprints/NPC/BP_MasterJedi
/Game/Dantooine/Blueprints/NPC/BP_RoamingNPC_Base
/Game/Dantooine/Blueprints/NPC/BP_RoamingNPC_StudentA
/Game/Dantooine/Blueprints/NPC/BP_RoamingNPC_StudentB
/Game/Dantooine/Blueprints/Combat/BP_SparringOpponent
/Game/Dantooine/Blueprints/Quest/BP_DantooineQuestManager
/Game/Dantooine/Blueprints/Quest/BP_LevelCompletionHandler
/Game/Dantooine/Blueprints/Interactables/BP_LightsaberWorkbench
/Game/Dantooine/Blueprints/Triggers/BP_TrainingAreaTrigger
/Game/Dantooine/Blueprints/AI/BP_NPC_AIController
/Game/Dantooine/Blueprints/AI/BP_Sparring_AIController
/Game/Dantooine/AI/BehaviorTrees/BT_RoamingNPC
/Game/Dantooine/AI/BehaviorTrees/BT_Sparring
/Game/Dantooine/AI/Blackboard/BB_RoamingNPC
/Game/Dantooine/AI/Blackboard/BB_Sparring
/Game/Dantooine/AI/Tasks/BTT_FindRandomPatrol
/Game/Dantooine/Animation/Player/ABP_PlayerJedi
/Game/Dantooine/Animation/NPCs/ABP_RoamingNPC
/Game/Dantooine/Animation/SparringOpponent/ABP_SparringOpponent
/Game/Dantooine/Widgets/WBP_HUD
/Game/Dantooine/Widgets/WBP_DialogueBox
/Game/Dantooine/Widgets/WBP_QuestTracker
/Game/Dantooine/Widgets/WBP_InteractPrompt
/Game/Dantooine/Widgets/WBP_SparringHUD
/Game/Dantooine/Widgets/WBP_LevelComplete
/Game/Dantooine/Data/Enums/E_QuestStage
/Game/Dantooine/Data/Enums/E_NPCDialogueMode
/Game/Dantooine/Data/Enums/E_InteractableType
/Game/Dantooine/Data/Enums/E_SparringState
/Game/Dantooine/Data/Structs/ST_DialogueLine
/Game/Dantooine/Data/Structs/ST_DialogueNode
/Game/Dantooine/Data/Structs/ST_DialogueChoice
/Game/Dantooine/Data/Structs/ST_NPCBarkSet
/Game/Dantooine/Data/Structs/ST_SparConfig
/Game/Dantooine/Interfaces/BPI_Interactable
/Game/Dantooine/Interfaces/BPI_DialogueParticipant
/Game/Dantooine/Interfaces/BPI_CombatReceiver
/Game/Dantooine/Data/Input/IA_Move
/Game/Dantooine/Data/Input/IA_Look
/Game/Dantooine/Data/Input/IA_Jump
/Game/Dantooine/Data/Input/IA_Interact
/Game/Dantooine/Data/Input/IA_Attack
/Game/Dantooine/Data/Input/IA_Block
/Game/Dantooine/Data/Input/IMC_Dantooine
/Game/Dantooine/Sequences/LightsaberBuild/LS_LightsaberBuild
```

---
