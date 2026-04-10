# Data Structures — Complete Reference
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero)
> Last Updated: 2026-04-10 | UE 5.6

---

## 1. Arrays

**Ordered list of elements, all the same type. Indexed from 0.**

### Declare
In My Blueprint → Variables → Variable Type → click the grid icon → Array

### Array Nodes
| Node | Description | Output |
|------|-------------|--------|
| `Add` | Appends element to end | New length (int) |
| `Insert` | Inserts at index; shifts everything after | — |
| `Get (a ref)` | Returns element at index (mutable reference) | Element |
| `Get (copy)` | Returns copy at index | Element |
| `Set Array Elem` | Sets value at index | — |
| `Remove Index` | Removes element at index; shifts after | — |
| `Remove Item` | Removes first matching element | Bool (found?) |
| `Clear` | Removes all elements | — |
| `Length` | Returns count of elements | Int |
| `Last Index` | Returns Length - 1 | Int |
| `Is Valid Index` | True if index is within bounds | Bool |
| `Is Empty` | True if array has 0 elements | Bool |
| `Is Not Empty` | True if array has ≥ 1 element | Bool |
| `Contains` | True if element is in array | Bool |
| `Find` | Returns index of first match (-1 if not found) | Int |
| `Find Last` | Returns index of last match | Int |
| `Shuffle` | Randomizes element order | — |
| `Resize` | Sets array to specific length | — |
| `Append` | Adds all elements from another array | — |
| `Random Item` | Returns a random element | Element |
| `Sort` | Sorts in-place | — |
| `Filter Array` | Returns new filtered array | Array |
| `To Set` | Converts to Set | Set |

### Iteration Pattern
```
For Each Loop:
  Array: MyArray
  → Loop Body: Array Element (use this), Array Index
  → Completed: (next execution)
```

### Common Array Uses
```
QuestObjectives: Array of String
CollectedItems: Array of E_InteractableType
DialogueChoices: Array of ST_DialogueChoice
NPCsInArea: Array of BP_RoamingNPC (Object Reference)
```

---

## 2. Sets

**Unordered collection of UNIQUE elements. No duplicates.**

### Set Nodes
| Node | Description |
|------|-------------|
| `Add` | Adds element; ignores if duplicate |
| `Remove` | Removes matching element |
| `Contains` | Checks membership |
| `Clear` | Removes all |
| `Length` | Count of elements |
| `Is Empty / Not Empty` | Empty check |
| `To Array` | Converts to Array |
| `Union` | Returns all elements from both sets |
| `Intersection` | Returns only elements in BOTH sets |
| `Difference` | Returns elements in A but NOT in B |

### When to Use Sets
- Track which items player has collected (no duplicates needed)
- Which quests are active
- Which areas are unlocked

---

## 3. Maps (Dictionaries)

**Key-Value pairs. Look up values by unique key.**

### Map Nodes
| Node | Description |
|------|-------------|
| `Add` | Adds or replaces key-value pair |
| `Remove` | Removes key-value pair |
| `Find` | Returns value for key (or default if not found) |
| `Contains` | Checks if key exists |
| `Length` | Count of pairs |
| `Is Empty / Not Empty` | Empty check |
| `Clear` | Removes all |
| `Keys` | Returns array of all keys |
| `Values` | Returns array of all values |

### Common Map Uses
```
ItemCounts: Map(E_InteractableType → Integer)   (inventory quantity)
NPCDialogueState: Map(Name → E_NPCDialogueMode)  (per-NPC state)
LevelHighScores: Map(String → Integer)            (score by level name)
```

---

## 4. Structs (Structures)

**Custom grouped data — multiple fields of any types.**

### Creating a Struct
```
Content Browser → Blueprint → Structure
Name: ST_DialogueLine (ST_ prefix)

Fields:
  SpeakerName: Name
  LineText: Text
  AudioCue: SoundBase (Object Ref)
  CameraAngle: Rotator
  Duration: Float
```

### Using a Struct
```
Variable Type: ST_DialogueLine
Get → Break ST_DialogueLine → access individual fields
Set → Make ST_DialogueLine → provide all fields
```

### Dantooine Structs Reference
| Struct | Fields |
|--------|--------|
| `ST_DialogueLine` | SpeakerName, LineText, AudioCue, Duration |
| `ST_DialogueNode` | NodeID, Lines (Array of ST_DialogueLine), Choices (Array of ST_DialogueChoice) |
| `ST_DialogueChoice` | ChoiceText, NextNodeID, RequiredQuestStage |
| `ST_NPCBarkSet` | NPCName, Barks (Array of Text), BarkInterval (Float) |
| `ST_SparConfig` | HitLimit, RoundDuration, AttackInterval, DifficultyScale |

---

## 5. Enumerations (Enums)

**Named list of mutually exclusive options. Stored as a byte.**

### Creating an Enum
```
Content Browser → Blueprint → Enumeration
Name: E_QuestStage (E_ prefix)

Entries:
  Not_Started
  Intro_Dialogue
  Find_Workbench
  Build_Lightsaber
  Begin_Sparring
  Complete
```

### Using an Enum
```
Variable Type: E_QuestStage
Switch on Enum → routes execution based on current value
Equals → compare against specific value
```

### Dantooine Enums Reference
| Enum | Values |
|------|--------|
| `E_QuestStage` | Not_Started, Intro_Dialogue, Find_Workbench, Build_Lightsaber, Begin_Sparring, Complete |
| `E_NPCDialogueMode` | Idle, Talking, Walking_And_Talking, Barking |
| `E_InteractableType` | None, LightsaberWorkbench, QuestTrigger, PickupItem, ExitDoor |
| `E_SparringState` | Idle, Circling, Attacking, Blocking, Staggered, Defeated |

---

## 6. Data Tables

**Spreadsheet-like asset driven by a Struct. Row-based data storage.**

### Creating a Data Table
```
Content Browser → Miscellaneous → Data Table
Select Row Struct: ST_DialogueLine (or any struct)
Name: DT_NPCDialogueLines (DT_ prefix)

Edit in the data table editor:
  Row Name: Jedi_Intro_Line_01 | SpeakerName: "Master Jedi" | LineText: "Welcome, young one." | ...
  Row Name: Jedi_Intro_Line_02 | SpeakerName: "Master Jedi" | LineText: "Your journey begins here." | ...
```

### Reading from a Data Table
```
Get Data Table Row (Table: DT_NPCDialogueLines, Row Name: "Jedi_Intro_Line_01")
  → Break ST_DialogueLine → SpeakerName, LineText, etc.
```

### Iterating All Rows
```
Get Data Table Row Names (DT_NPCDialogueLines) → Array of Row Name Strings
For Each → Get Data Table Row → process each
```

---

## 7. Data Assets

**Custom Blueprint-based configurations defined in Project Settings.**

### Creating a Data Asset
```
C++: Create UPrimaryDataAsset subclass (or use DataAsset base)
Blueprint: Blueprint Class → Parent: DataAsset or PrimaryDataAsset
Name: DA_WeaponConfig (DA_ prefix)

Variables:
  BaseDamage: Float = 25
  AttackRange: Float = 200
  SwingAudioCue: SoundBase
  TrailVFX: NiagaraSystem
```

### Using Data Assets
```
Variable of type DA_WeaponConfig (Object Ref)
Set in Details panel per-instance
Read at runtime: Get WeaponConfig → Get BaseDamage
```

---

## 8. Save / Load System (Full Implementation)

### SaveGame Blueprint Setup
```
Content Browser → Blueprint Class → Parent: SaveGame
Name: BP_DantooineProgress

Variables:
  CurrentQuestStage: E_QuestStage
  CompletedObjectives: Array of String
  TotalPlaytime: Float
  LastCheckpointName: String
  PlayerPosition: Vector
```

### Save Function
```
[In BP_DantooineGameMode or BP_DantooinePlayerController]

Function: SaveGame
  Create Save Game Object (Class: BP_DantooineProgress)
  → Cast to BP_DantooineProgress → Store in SaveRef
  
  Set CurrentQuestStage = Get Quest Manager → QuestStage
  Set TotalPlaytime = Get Game Instance → ElapsedTime
  Set PlayerPosition = Get Player Pawn → Get Actor Location
  
  Save Game to Slot (SaveRef, SlotName: "DantooineSlot1", UserIndex: 0)
  → Return: Success (bool)
```

### Load Function
```
Function: LoadGame → Output: Bool (DidLoad)

Does Save Game Exist ("DantooineSlot1", 0) → Branch:
  True:
    Load Game from Slot ("DantooineSlot1", 0)
    → Cast To BP_DantooineProgress
    
    Get Quest Manager → Set QuestStage = SaveRef.CurrentQuestStage
    Get Player Pawn → Set Actor Location = SaveRef.PlayerPosition
    
    Return: true
  
  False:
    Initialize default game state
    Return: false
```

### Auto-Save Pattern
```
Event Tick (throttled — not every frame):
  TimeSinceLastSave += Delta Seconds
  If TimeSinceLastSave >= 300 (5 minutes):
    Call SaveGame function
    Reset TimeSinceLastSave = 0
```

---

## 9. Input System (Enhanced Input — UE 5.1+)

### Input Action Assets
```
Content Browser → Input → Input Action
Name: IA_Move (IA_ prefix)
Value Type: Axis2D (for WASD movement)

IA_Move: Axis2D
IA_Look: Axis2D
IA_Jump: Digital (bool)
IA_Interact: Digital (bool)
IA_Attack: Digital (bool)
IA_Block: Digital (bool)
```

### Input Mapping Context
```
Content Browser → Input → Input Mapping Context
Name: IMC_Dantooine (IMC_ prefix)

Mappings:
  IA_Move → W (Modifier: Swizzle YXZ)
           → S (Modifier: Swizzle YXZ, Negate)
           → A (Modifier: Negate)
           → D (no modifier)
  
  IA_Look → Mouse XY 2D Axis
  
  IA_Jump → Spacebar
  IA_Interact → E
  IA_Attack → Left Mouse Button
  IA_Block → Right Mouse Button
```

### Adding Context in PlayerController
```
Event BeginPlay:
  Get Player Controller → 
  Add Mapping Context (Context: IMC_Dantooine, Priority: 0)
```

### Using Input in Character
```
Enhanced Input Action IA_Move (Triggered):
  → ActionValue.Axis2D → X = MoveRight, Y = MoveForward
  → Get Control Rotation → Make Rotator (Pitch: 0, Yaw: ControlYaw, Roll: 0)
  → Get Forward Vector → × MoveForward → Add Movement Input
  → Get Right Vector → × MoveRight → Add Movement Input

Enhanced Input Action IA_Jump (Started):
  → Jump (Character function)

Enhanced Input Action IA_Jump (Completed):
  → StopJumping
```

---

## 10. Timer System

**Execute code after a delay or on a repeating interval.**

### One-Shot Timer
```
Set Timer by Function Name:
  Object: self
  Function Name: "HandleTimerFired" (string — name of custom event)
  Time: 3.0 (seconds)
  Looping: false
→ Returns: TimerHandle

[Custom Event: HandleTimerFired]
  → Execute delayed logic
```

### Repeating Timer
```
Set Timer by Event:
  Event: [Create Event from Custom Event]
  Time: 0.5 (fires every 0.5 seconds)
  Looping: true
→ Returns: TimerHandle (store this to cancel later)
```

### Cancel Timer
```
Clear Timer by Handle (TimerHandle)
Clear and Invalidate Timer by Handle (TimerHandle) ← preferred
```

### Check Timer
```
Get World Timer Manager →
  Is Timer Active by Handle (TimerHandle) → Bool
  Get Timer Remaining Time by Handle → Float seconds remaining
```
