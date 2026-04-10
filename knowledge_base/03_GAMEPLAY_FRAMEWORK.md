# Gameplay Framework — Complete Reference
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero)
> Last Updated: 2026-04-10 | UE 5.6

---

## 1. Framework Class Hierarchy

```
UObject
  └── AActor (base of all placeable objects)
        ├── APawn (controllable entity)
        │     └── ACharacter (biped with movement + capsule)
        ├── AController
        │     ├── APlayerController (human input → pawn)
        │     └── AAIController (AI brain → pawn)
        ├── AGameModeBase (rules — SERVER ONLY)
        ├── AGameStateBase (shared state — replicated to all)
        ├── APlayerState (per-player state — replicated)
        ├── AHud (on-screen overlays — client)
        ├── AGameSession (server session management)
        └── AInfo (base for manager actors)

UActorComponent (no transform, logic only)
  └── USceneComponent (has transform, can attach)
        └── UPrimitiveComponent (has geometry + collision)
              ├── UMeshComponent
              │     ├── UStaticMeshComponent
              │     └── USkeletalMeshComponent
              └── UShapeComponent (Box, Sphere, Capsule)
```

---

## 2. Actor

**The base class of everything placeable in a UE5 level.**

### Key Facts
- Has a Transform (Location, Rotation, Scale)
- Can have any number of components
- Has its own Event Graph (BeginPlay, Tick, EndPlay, etc.)
- Can be spawned/destroyed at runtime
- Is NOT controllable by default (use Pawn/Character for that)

### When to use Actor as parent:
- Static world objects (BP_LightsaberWorkbench, BP_TrainingAreaTrigger)
- Managers (BP_QuestManager, BP_LevelCompletionHandler)
- Trigger volumes
- Projectiles
- Pickups
- Cameras with custom behavior

### Actor Lifecycle
```
Constructor
  → Called in editor + at runtime for CDO
BeginPlay
  → Called once when actor enters the game world
Tick (if enabled)
  → Called every frame
EndPlay
  → Called when actor is removed (reason: Destroyed, Level Transition, etc.)
Destroyed
  → Called just before full destruction
```

---

## 3. Pawn

**An Actor that can be "possessed" (controlled) by a Controller.**

### Key Facts
- Base class for controllable entities
- Can be possessed by: PlayerController (human) or AIController (AI)
- Does NOT have built-in movement component (add manually)
- Does NOT have default mesh or collision

### When to use Pawn:
- Vehicles
- Floating bots (add FloatingPawnMovement component)
- Non-humanoid controlled entities
- Simple AI turrets

### Pawn Properties (in Details panel)
| Property | Description |
|----------|-------------|
| `Auto Possess Player` | `Player 0` = automatically possessed by first player |
| `Auto Possess AI` | `Placed in World or Spawned` = auto-gets AI controller |
| `AI Controller Class` | Which AIController class to use |
| `Use Controller Rotation Yaw/Pitch/Roll` | Whether rotation follows controller |

### Movement Component Options for Pawn
| Component | Use |
|-----------|-----|
| `FloatingPawnMovement` | Simple 3D movement without gravity |
| `NavMovementComponent` | Movement with NavMesh pathfinding support |
| Custom | Fully custom physics |

---

## 4. Character

**Pawn with built-in bipedal locomotion, capsule collision, and mesh.**

### Built-In Components
```
Capsule Component (root, collision)
  ├── Arrow Component (forward direction indicator)
  ├── Mesh (SkeletalMesh, character body)
  └── CharacterMovement (handles walk/run/jump/fall/swim/fly)
```

### CharacterMovement Properties
| Property | Description | Default |
|----------|-------------|---------|
| `Max Walk Speed` | Top speed while walking (cm/s) | 600 |
| `Max Walk Speed Crouched` | Top speed while crouching | 300 |
| `Jump Z Velocity` | Upward force on jump | 420 |
| `Gravity Scale` | Multiplier for gravity | 1.0 |
| `Max Acceleration` | How fast to reach top speed | 2048 |
| `Braking Deceleration Walking` | How fast to stop | 2048 |
| `Air Control` | Control while airborne (0=none, 1=full) | 0.05 |
| `Can Ever Crouch` | Enable crouching | false |
| `Max Step Height` | Max height to step up onto | 45 |
| `Walkable Floor Angle` | Max slope walkable (degrees) | 44 |

### Character Nodes
| Node | Description |
|------|-------------|
| `Add Movement Input` | Apply directional input (used in controller) |
| `Jump` | Start jump |
| `StopJumping` | Cancel jump |
| `Crouch` | Enter crouch state |
| `UnCrouch` | Exit crouch state |
| `Launch Character` | Apply impulse (jump boost, knockback) |
| `IsFalling` | Bool: is character in the air |
| `IsCrouched` | Bool: is character crouching |
| `GetVelocity` | Current movement vector |
| `GetCharacterMovement` | Access CharacterMovement component |

### When to use Character:
- Player character (BP_PlayerJediCharacter)
- Human NPCs (BP_MasterJedi, BP_RoamingNPC_Base)
- Enemies with bipedal locomotion (BP_SparringOpponent)

---

## 5. PlayerController

**The "brain" for human player input. One per player. Receives input events.**

### Key Facts
- Exists as long as the game is running (persists across possessing different pawns)
- Receives all input (keyboard, mouse, gamepad, Enhanced Input)
- Controls camera via `SetViewTargetWithBlend`
- Manages HUD/UI widgets
- Network: runs on client AND server (server-authoritative logic goes here)

### Setup in GameMode
```
GameMode → Default Player Controller Class → BP_DantooinePlayerController
```

### PlayerController Patterns

#### Input Setup (Enhanced Input — UE 5.1+)
```
BeginPlay:
  Get Player Controller →
  Add Mapping Context (IMC_Dantooine, Priority: 0)

Input Action IA_Move (Triggered):
  → Get Control Rotation → Break Rotator → Yaw only → Make Rotator
  → Get Forward Vector → × AxisValue → Add Movement Input (to possessed Pawn)

Input Action IA_Jump (Started):
  → Get Controlled Pawn → Cast To Character → Jump
```

#### HUD Setup
```
BeginPlay:
  → Create Widget (Class: WBP_HUD)
  → Store in HUDWidgetRef variable
  → Add to Viewport
```

### PlayerController Key Functions
| Function | Description |
|----------|-------------|
| `Get Controlled Pawn` | Returns the pawn this controller possesses |
| `Possess` | Take control of a Pawn |
| `Unpossess` | Release control |
| `Set View Target with Blend` | Switch camera target |
| `Client Travel` | Move this client to a different level |
| `Add Mapping Context` | Add an Enhanced Input context |
| `Remove Mapping Context` | Remove a context |
| `Set Input Mode Game Only` | Block UI input |
| `Set Input Mode UI Only` | Block game input |
| `Set Input Mode Game and UI` | Allow both |

---

## 6. GameModeBase

**Defines the rules of the game. SERVER ONLY — never use for client-side logic.**

### Key Facts
- Only one GameMode per level
- Does NOT replicate to clients (use GameState for shared state)
- Defines which classes to use for other framework members
- Controls match flow: starting, ending, restarting

### Setting GameMode
```
Project Settings → Maps & Modes → Default Game Mode
OR per-level: World Settings → Game Mode Override
```

### GameMode Class Assignments
```
Open BP_DantooineGameMode:
  Class Defaults:
    Default Pawn Class: BP_PlayerJediCharacter
    HUD Class: none (we create UI in PlayerController)
    Player Controller Class: BP_DantooinePlayerController
    Game State Class: GameStateBase (or custom)
    Player State Class: PlayerState (or custom)
    Spectator Class: SpectatorPawn
```

### GameMode Nodes
| Function | Description |
|----------|-------------|
| `Get Game Mode` | Returns current game mode |
| `Restart Player` | Respawn a player controller's pawn |
| `Start Play` | Override to add match start logic |
| `End Game` | Override to handle end-of-game |

---

## 7. GameInstance

**Persists for the entire application lifetime. Cross-level data storage.**

### Key Facts
- Created when game launches, destroyed when game quits
- Survives level transitions
- Only ONE instance exists (not per-player)
- Perfect for: settings, save game data, player progression, analytics

### Setup
```
Project Settings → Maps & Modes → Game Instance Class → BP_DantooineGameInstance
```

### Common GameInstance Variables
```
PlayerScore: Integer
CurrentQuestStage: E_QuestStage (enum)
CollectedItems: Array of E_InteractableType
GameDifficulty: Float
SaveSlotName: String = "Slot1"
```

### Access Pattern
```
Get Game Instance → Cast To BP_DantooineGameInstance → Get/Set variables
```

---

## 8. SaveGame System

**Serializes Blueprint data to disk.**

### Creating a SaveGame Class
```
Content Browser → Blueprint Class → Parent: SaveGame
Name: BP_DantooineProgress

Variables:
  CompletedQuestStages: Array of E_QuestStage
  LastCheckpointName: String
  TotalPlayTime: Float
```

### Saving
```
Create Save Game Object (Class: BP_DantooineProgress)
  → Cast Return Value to BP_DantooineProgress
  → Set CompletedQuestStages = (current data)
  → Set TotalPlayTime = (current time)
Save Game to Slot (SaveGameObject, SlotName: "Slot1", UserIndex: 0)
```

### Loading
```
Does Save Game Exist ("Slot1", 0) → Branch:
  True → Load Game from Slot ("Slot1", 0)
           → Cast To BP_DantooineProgress
           → Get CompletedQuestStages
  False → Initialize default save data
```

### Deleting a Save
```
Delete Game in Slot (SlotName: "Slot1", UserIndex: 0)
```

---

## 9. GameState and PlayerState

### GameStateBase
- Replicated to ALL clients in multiplayer
- Stores data that all players need to see
- Examples: MatchTimer, TeamScores, CurrentRound
- Access: `Get Game State → Cast To BP_MyGameState`

### PlayerState
- One per connected player, replicated
- Stores player-specific networked data
- Examples: PlayerName, Ping, Score, Kills
- Access: `PlayerController → Get Player State → Cast`

---

## 10. Component System

### Two Component Types
| Type | Transform | Physics | Use |
|------|-----------|---------|-----|
| `ActorComponent` | ❌ None | ❌ | Pure logic modules (inventory, stats, abilities) |
| `SceneComponent` | ✅ Has transform | Optional | Visual/physical parts (mesh, camera, collision) |

### Adding Components in Blueprint
1. Open Blueprint → Components panel → **Add** button
2. Search for component type
3. Name it clearly (e.g., `InteractionBox`, `WorkbenchMesh`)

### Creating a Custom ActorComponent
```
Content Browser → Blueprint Class → Parent: ActorComponent
Name: BP_HealthComponent

Variables: 
  MaxHealth: Float = 100
  CurrentHealth: Float

Functions:
  TakeDamage(Amount: Float): 
    CurrentHealth - Amount → Clamp(0, MaxHealth) → Set CurrentHealth
    If CurrentHealth <= 0 → Call OnDeath event dispatcher

Usage:
  In any Blueprint → Add BP_HealthComponent → BeginPlay → Get Component → Initialize
```

### Creating a Custom SceneComponent
```
Content Browser → Blueprint Class → Parent: SceneComponent  
Name: BP_GrabComponent

Useful for: Grabbable objects, weapon sockets, interactable anchor points
Add to any Actor → attach to specific bone socket
```

### Blueprint Function Library
```
Content Browser → Blueprint Class → Parent: BlueprintFunctionLibrary
Name: FL_DantooineUtils

Functions (all static, no self):
  CalculateSaberDamage(Strength: Float) → Float: return Strength × 1.5
  FormatQuestText(Stage: E_QuestStage) → Text

Usage (from ANY Blueprint):
  FL_DantooineUtils → CalculateSaberDamage(SaberStrength) → DamageAmount
```

### Blueprint Macro Library
```
Content Browser → Blueprint Class → Parent: BlueprintMacroLibrary
Name: ML_DantooineCommon

Macros (with multiple exec pins):
  SafeInteract: 
    Input: Target (Actor), Instigator (Actor)
    → Is Valid check → Does Implement Interface check → Call Interact
    Output: Succeeded (exec), Failed (exec)
```

---

## 11. Parent Class Selection Quick Reference

| Blueprint | Parent Class | C++ Name |
|-----------|-------------|----------|
| World object | Actor | `AActor` |
| Simple controllable | Pawn | `APawn` |
| Humanoid character | Character | `ACharacter` |
| Player brain | PlayerController | `APlayerController` |
| AI brain | AIController | `AAIController` |
| Game rules | GameModeBase | `AGameModeBase` |
| Cross-level data | GameInstance | `UGameInstance` |
| Networked game state | GameStateBase | `AGameStateBase` |
| Per-player network | PlayerState | `APlayerState` |
| Disk save file | SaveGame | `USaveGame` |
| Logic module | ActorComponent | `UActorComponent` |
| Physical module | SceneComponent | `USceneComponent` |
| Screen UI | UserWidget | `UUserWidget` |
| AI task | BTTask_BlueprintBase | `UBTTask_BlueprintBase` |
| AI decorator | BTDecorator_BlueprintBase | `UBTDecorator_BlueprintBase` |
| AI service | BTService_BlueprintBase | `UBTService_BlueprintBase` |
| Utility functions | BlueprintFunctionLibrary | `UBlueprintFunctionLibrary` |
