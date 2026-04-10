# Game Systems Cookbook — Recipes for Dantooine
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero), Unreal Engine Blueprint Game Developer (Asadullah Alam)
> Complete, step-by-step implementation recipes for all major Dantooine game systems.
> Each recipe is a complete, working pattern that an AI agent can implement.

---

## RECIPE 1: HEALTH AND DAMAGE SYSTEM

### Components
- `BP_PlayerJediCharacter` — takes damage, dies
- `AC_HealthComponent` (optional component pattern)
- `WBP_HUD` — displays health bar
- `WBP_SparringHUD` — displays opponent health

### Variables on BP_PlayerJediCharacter
```
MaxHealth: Float = 100.0 (instance editable)
CurrentHealth: Float = 100.0
bIsDead: Bool = false
```

### Event Dispatcher on BP_PlayerJediCharacter
```
OnHealthChanged (Float NewPercent)
OnDeath ()
```

### Take Damage (Override AnyDamage)
```
Event AnyDamage (Damage, DamageType, InstigatedBy, DamageCauser)
  → Branch: !bIsDead → True:
      CurrentHealth - Damage → Clamp (0, MaxHealth) → Set CurrentHealth
      Broadcast OnHealthChanged (CurrentHealth / MaxHealth)
      Branch: CurrentHealth <= 0 → True:
        Set bIsDead = true
        Broadcast OnDeath
        Play Death Montage
        Disable Input (PlayerController)
```

### Apply Damage (from attacker)
```
Apply Damage
  → Damaged Actor: Target Actor reference
  → Base Damage: 25.0
  → Event Instigator: Self (Controller)
  → Damage Causer: Self
  → Damage Type Class: DamageType (default)
```

### HUD Health Bar Update
```
WBP_HUD Event BeginPlay:
  Get Player Character → Cast → Bind OnHealthChanged → UpdateHealthBar

UpdateHealthBar (Float NewPercent):
  HealthProgressBar → Set Percent (NewPercent)
```

---

## RECIPE 2: LIGHTSABER WORKBENCH INTERACTION

### Components
- `BP_LightsaberWorkbench` — implements BPI_Interactable
- `BP_PlayerJediCharacter` — sends interact input
- `WBP_InteractPrompt` — shows "Press E to Interact"
- `LS_LightsaberBuild` — Level Sequence plays on completion

### On Overlap (in BP_TrainingAreaTrigger or on Workbench itself)
```
Event ActorBeginOverlap
  → Other Actor → Cast To BP_PlayerJediCharacter → [player ref]
  → WBP_InteractPrompt → Create Widget → Add to Viewport
  → Store ref in PlayerRef, PromptRef

Event ActorEndOverlap
  → PromptRef → Remove from Parent
  → Clear refs
```

### Interact Input → Call Interface
```
Input Action IA_Interact (Started)
  → Nearest Interactable → Is Valid → 
  → Message: Interact (BPI_Interactable) on Nearest Interactable
```

### Implement Interact on BP_LightsaberWorkbench
```
Event Interact (BPI_Interactable)
  → Play Level Sequence (LS_LightsaberBuild)
  → On Sequence Finished:
      Get Game Instance → Cast → Set Quest Stage = BuildLightsaber
      Broadcast OnQuestStageChanged
```

---

## RECIPE 3: DIALOGUE SYSTEM

### Data Setup
- `ST_DialogueLine`: SpeakerName (Name), LineText (Text), AudioCue (SoundBase)
- `ST_DialogueChoice`: ChoiceText (Text), NextNodeID (Int)
- `ST_DialogueNode`: NodeID (Int), Lines (ST_DialogueLine[]), Choices (ST_DialogueChoice[])
- `DT_MasterJediDialogue` — Data Table with ST_DialogueNode rows

### Opening Dialogue
```
Player Interacts with BP_MasterJedi:
  → Message: Interact (BPI_Interactable)
  
BP_MasterJedi: Event Interact
  → Get Current Quest Stage from Game Instance
  → Get Data Table Row (DT_MasterJediDialogue, RowName: QuestStage as String)
  → Row Found → True:
      Create WBP_DialogueBox → Add to Viewport
      Set Input Mode: UI Only
      Widget: ShowDialogueNode (Node data from table)
```

### Advancing Dialogue
```
WBP_DialogueBox:
  Function ShowDialogueNode (ST_DialogueNode Node)
    → Clear choices panel
    → For Each Line in Node.Lines:
        Display LineText on Text Block
        Play AudioCue if valid
    → For Each Choice in Node.Choices:
        Create WBP_DialogueChoice widget
        Set Choice Text
        Bind OnChoiceClicked → HandleChoice(NextNodeID)

  Function HandleChoice (Int NextNodeID)
    → -1: Close dialogue → Set Input Mode Game Only
    → Else: Get next node from table → ShowDialogueNode
```

---

## RECIPE 4: QUEST MANAGER SYSTEM

### BP_DantooineQuestManager Variables
```
CurrentStage: E_QuestStage = NotStarted
```

### Event Dispatchers
```
OnQuestStageChanged (E_QuestStage NewStage, E_QuestStage OldStage)
```

### AdvanceQuest Function
```
Function AdvanceQuest (E_QuestStage NewStage)
  → OldStage = CurrentStage
  → Set CurrentStage = NewStage
  → Save to Game Instance
  → Broadcast OnQuestStageChanged (NewStage, OldStage)
```

### Check Quest Condition
```
Function CanAdvanceTo (E_QuestStage Stage) → Bool
  → Switch on Enum (Stage)
    → CollectCrystals: always True (first stage)
    → BuildLightsaber: CurrentStage == CollectCrystals
    → TrainWithMaster: CurrentStage == BuildLightsaber AND HasLightsaber
    → SparringComplete: CurrentStage == TrainWithMaster
    → Complete: CurrentStage == SparringComplete
    → else: False
```

---

## RECIPE 5: NPC ROAMING AI SYSTEM

### Setup
1. `BP_RoamingNPC_Base` (parent: Character)
2. `BP_NPC_AIController` (parent: AIController)
3. `BB_RoamingNPC` with keys: `PatrolLocation` (Vector), `IsTalking` (Bool)
4. `BT_RoamingNPC` — behavior tree
5. `BTT_FindRandomPatrol` — custom BT task

### BP_NPC_AIController BeginPlay
```
Event BeginPlay
  → Run Behavior Tree (BT: BT_RoamingNPC)
```

### BT_RoamingNPC Structure
```
ROOT
└── Selector (repeat = true via Loop decorator)
      ├── Sequence [IsTalking == true]
      │     └── Wait (indefinitely — will be interrupted when IsTalking clears)
      └── Sequence (patrol)
            ├── Task: BTT_FindRandomPatrol → sets PatrolLocation
            ├── Move To (BB: PatrolLocation)
            └── Wait (Random Range: 2.0 to 5.0)
```

### BTT_FindRandomPatrol Task
```
Event Receive Execute AI (AI Controller, Controlled Pawn)
  → Get Controlled Pawn → Get Actor Location → Origin
  → Get Random Point in Navigable Radius (Origin, Radius: 1000)
  → Get Blackboard Component → Set Value as Vector (PatrolLocation, found point)
  → Finish Execute (Success: true)
```

### NPC Dialogue Interrupt
```
When player talks to NPC:
  → AIController → Get Blackboard → Set Value as Bool (IsTalking, true)
  
When dialogue ends:
  → AIController → Get Blackboard → Set Value as Bool (IsTalking, false)
```

---

## RECIPE 6: SPARRING COMBAT SYSTEM

### Setup
- `BP_SparringOpponent` (parent: Character)
- `BP_Sparring_AIController` (parent: AIController)
- `BB_Sparring` keys: `TargetActor` (Object), `FightActive` (Bool), `HitsTaken` (Int)
- `BT_Sparring`

### Sparring Start Trigger (BP_TrainingAreaTrigger)
```
Event ActorBeginOverlap → Other Actor → Cast To BP_PlayerJediCharacter
  → Spawn BP_SparringOpponent at designated spawn point
  → Spawned Opponent → Spawn Default Controller
  → Get Sparring AI Controller → Bind TargetActor BB key = Player
  → Set FightActive = true
  → Show WBP_SparringHUD
```

### BT_Sparring Structure
```
ROOT
└── Selector
      ├── Sequence [FightActive == false]
      │     └── Wait (idle)
      └── Sequence [FightActive == true]
            ├── Service: Update player distance (runs every 0.5s)
            ├── Move To (TargetActor, Acceptance Radius: 100)
            └── Task: ExecuteAttack
```

### Hit Detection (Melee)
```
On Attack Notify in BP_SparringOpponent:
  → Sphere Trace (weapon bone location, radius 60)
  → Break Hit Result → Hit Actor
  → Cast To BP_PlayerJediCharacter → Is Blocking?
      → True: Play Block reaction, no damage
      → False: Apply Damage 25.0
  → Increment HitsTaken in Blackboard
  → HitsTaken >= MaxHits: Broadcast OnSparringComplete
```

### Sparring End
```
OnSparringComplete:
  → Set FightActive = false in Blackboard
  → Stop Behavior Tree
  → Destroy opponent (or play defeat animation then destroy)
  → Hide WBP_SparringHUD
  → Quest Manager: AdvanceQuest (SparringComplete)
  → Show WBP_LevelComplete
```

---

## RECIPE 7: CAMERA SYSTEM

### Third-Person Camera Setup (in BP_PlayerJediCharacter)
```
Components:
  CapsuleComponent (Root)
  └── SkeletalMesh (character body)
  └── SpringArmComponent (camera boom)
      └── CameraComponent (view)

Spring Arm Settings:
  Target Arm Length: 300
  Use Pawn Control Rotation: true
  Enable Camera Lag: true (smooth follow)
  Camera Lag Speed: 10.0

Camera Settings:
  Field of View: 90
  Use Pawn Control Rotation: false (spring arm handles it)
```

### FOV Zoom for Lightsaber Precision
```
Input Action IA_Aim (held)
  → Timeline: FOV from 90 to 60 over 0.2 seconds
  → Timeline Update: Set Field of View (CameraComp, Alpha value)
Input Action IA_Aim (released)
  → Timeline Reverse
```

### Look/Rotate Input
```
Input Action IA_Look (Triggered)
  → Add Controller Yaw Input (Action Value X × Sensitivity)
  → Add Controller Pitch Input (Action Value Y × -1 × Sensitivity) [invert Y]
```

---

## RECIPE 8: SPAWN ACTOR PATTERN

### Spawning an NPC at Runtime
```
Spawn Actor from Class
  → Class: BP_RoamingNPC_StudentA
  → Spawn Transform: Make Transform
      → Location: SpawnPoint actor location (from a named Target Point actor)
      → Rotation: (0, 0, 0)
      → Scale: (1, 1, 1)
  → Collision Handling Override: Always Spawn Ignore Collisions

→ [Return Value: Spawned Actor]
→ SpawnDefaultController (!! CRITICAL: AI won't work without this for runtime-spawned pawns)
→ Store reference if you need to interact with it later
```

---

## RECIPE 9: LEVEL COMPLETION SEQUENCE

### Setup
- `LS_LightsaberBuild` — Sequencer cutscene
- `WBP_LevelComplete` — completion screen
- `BP_LevelCompletionHandler` — manages the sequence

### Trigger Flow
```
Quest Manager broadcasts OnQuestStageChanged (Complete)
  → BP_LevelCompletionHandler receives via binding
  
BP_LevelCompletionHandler:
  Event OnQuestComplete:
    → Disable Player Input
    → Play Level Sequence (LS_LightsaberBuild)
    → On Sequence Finished:
        → Save Game (save current progress)
        → Create WBP_LevelComplete → Add to Viewport
        → Start 3-second timer
        → On Timer: Open Level "Credits" or "MainMenu"
```

### WBP_LevelComplete
```
Canvas Panel
└── Vertical Box (centered)
    ├── Text "JEDI TRAINING COMPLETE!"
    ├── Text "Your lightsaber has been forged."
    └── Button "Play Again"

Button OnClicked: Open Level (same level)
```

---

## RECIPE 10: SAVE GAME FULL IMPLEMENTATION

### Save Flow (triggered by Quest Manager on stage change)
```
Event: QuestStageChanged
  → Create Save Game Object (BP_DantooineGameSave)
  → Cast To BP_DantooineGameSave
  → Set QuestStage = CurrentStage
  → Set PlayerLocation = Get Actor Location
  → Set PlayTime = accumulated play time
  → Save Game to Slot ("DantooineSlot1", 0)
```

### Load Flow (Game Instance BeginPlay)
```
Event Init (GameInstance):
  → Does Save Game Exist ("DantooineSlot1", 0)
  → True:
      Load Game from Slot → Cast To BP_DantooineGameSave
      → Restore QuestStage to GameInstance variable
      → Restore PlayTime
      → Set bHasSaveData = true
  → False:
      Initialize default values
      Set bHasSaveData = false
```

### Starting Level with Save
```
BP_DantooineGameMode BeginPlay:
  → Get Game Instance → Cast → bHasSaveData?
  → True:
      Get QuestStage → Broadcast to Quest Manager
      Get PlayerLocation → Set Actor Location
  → False:
      Start fresh (default positions)
```

---

## RECIPE 11: AMBIENT BIRD SHIP (BP_SkyBirdShip)

### Overview
The SkyBirdShip is a large ship silhouette flying slowly across the horizon for atmosphere.

### Components
```
BP_SkyBirdShip (parent: Actor)
  └── StaticMesh (SM_DantooineSkyShip)
  └── SplineComponent (flight path, set in editor)
  └── AudioComponent (ambient engine hum)
```

### Movement Along Spline (Tick)
```
Event Tick:
  CurrentDistance + (Speed × DeltaSeconds) → Clamp or Wrap
  → Set CurrentDistance
  → Get Location at Distance Along Spline (CurrentDistance, World Space)
  → Set Actor Location
  → Get Rotation at Distance Along Spline
  → Set Actor Rotation
```

### Loop
```
If CurrentDistance >= Spline Length:
  → Reset CurrentDistance = 0 (or teleport to beginning)
```
