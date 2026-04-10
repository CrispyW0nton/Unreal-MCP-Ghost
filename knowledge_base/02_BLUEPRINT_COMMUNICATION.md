# Blueprint Communication — Complete Reference
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero), Unreal Engine Blueprint Game Developer (Asadullah Alam)
> Last Updated: 2026-04-10 | UE 5.6

---

## Overview: 5 Communication Methods

| Method | Use When | Coupling |
|--------|----------|---------|
| **Direct Reference** | Caller knows the exact object it wants to talk to | Tight |
| **Casting** | Caller has a generic reference, needs subclass features | Medium |
| **Event Dispatchers** | One-to-many broadcasting; caller doesn't care who listens | Loose |
| **Blueprint Interfaces** | Caller doesn't know the receiver's class | Loosest |
| **Level Blueprint** | One-off level events referencing placed actors | Level-scoped |

---

## 1. Direct Blueprint Communication

**When to use:** You have a direct reference to a specific actor instance and need to call its functions or read its variables.

### Setup Pattern
```
In Blueprint A:
  1. Create a variable of type [BP_B Object Reference]
  2. Mark it Instance Editable
  3. In the Level Editor, assign the specific BP_B instance to the variable

In Event Graph:
  Get TargetRef (variable) → Is Valid → [call function on it]
```

### Example: Light Switch → Point Light
```
BP_LightSwitch variables:
  Light: PointLightComponent (Object Reference, Instance Editable)

Event ActorBeginOverlap:
  → Get Light → Is Valid → Toggle Visibility (PointLightComponent)
```

### CRITICAL RULE
**Always use `Is Valid` before calling any function on an object reference variable.**
A variable can be invalid because:
- The referenced actor was destroyed
- The variable was never assigned in the editor
- The actor has not yet been spawned

---

## 2. Casting

**When to use:** You have a general reference (e.g., from `GetPlayerCharacter` which returns `Pawn`) and need to access a subclass's specific variables or functions.

### Cast To Node
```
Get Player Character → Cast To BP_PlayerJediCharacter
  ├── Cast Succeeded → As BP_PlayerJediCharacter → [access specific members]
  └── Cast Failed → [handle null case]
```

### Pins
| Pin | Direction | Description |
|-----|-----------|-------------|
| `execute` | Input exec | When to attempt the cast |
| `Object` | Input data | The base-class reference to cast |
| `then` (Cast Succeeded) | Output exec | Fires when cast succeeds |
| `Cast Failed` | Output exec | Fires when cast fails |
| `As [ClassName]` | Output data | The typed reference (use this for calls) |

### Inheritance and Casting
```
Cast succeeds when:
  Actual object type IS the cast type, or IS a subclass of it

Cast fails when:
  Actual object type is NOT related to the cast type
```

### Performance Rule: Cache, Don't Cast Every Frame
```
BAD (in Event Tick):
  Get Player Character → Cast To BP_Player → Get Health

GOOD:
  Event BeginPlay → Get Player Character → Cast To BP_Player
    Cast Succeeded → Set PlayerRef (variable)
  
  Event Tick → Get PlayerRef → Is Valid → Get Health
```

---

## 3. Event Dispatchers (One-to-Many Broadcasting)

**When to use:** One Blueprint needs to notify MULTIPLE other Blueprints of an event without knowing who they are. The dispatcher is created in the broadcaster, and listeners bind to it.

### Creating a Dispatcher
1. My Blueprint panel → Event Dispatchers → click **+**
2. Name it (e.g., `OnHealthChanged`, `OnQuestComplete`)
3. Optional: Add Parameters (the data sent to all listeners)

### Calling (Broadcasting) the Dispatcher
```
[In the owning Blueprint's Event Graph]
Event/Trigger → Call OnHealthChanged
  → (parameters: NewHealth, MaxHealth)
```

### Binding to a Dispatcher (In another Blueprint)
```
[In the listening Blueprint]
Event BeginPlay → Get Reference to Broadcasting Actor
  → Bind Event to OnHealthChanged → Create Event (OnHealthChanged_Listener)

Custom Event: OnHealthChanged_Listener (NewHealth: float, MaxHealth: float)
  → Update UI or do something with the data
```

### Unbinding
```
Unbind Event from OnHealthChanged → removes specific binding
Unbind All from OnHealthChanged → removes ALL bindings
```

### Key Rules
- The Event Dispatcher is OWNED by one Blueprint (the broadcaster)
- Other Blueprints BIND to it — they register to listen
- Bind in **BeginPlay**, unbind in **EndPlay** to prevent memory leaks
- Parameters travel FROM dispatcher → TO all bound events

---

## 4. Blueprint Interfaces

**When to use:** You want to call a function on ANY actor, regardless of its class, as long as it "implements" the interface. Perfect for interaction systems.

### Creating an Interface
```
Content Browser → Right-click → Blueprint → Blueprint Interface
Name: BPI_Interactable (use BPI_ prefix)
  Add Functions:
    - Interact (Input: Instigator: Actor)
    - GetInteractionText (Output: Text)
```

### Implementing an Interface (In a Blueprint Class)
```
Open BP_LightsaberWorkbench
Class Settings → Interfaces → Add: BPI_Interactable
Now the Blueprint has empty "Event Interact" and "GetInteractionText" in the Event Graph
Implement them:
  Event Interact → [do workbench interaction logic]
```

### Calling an Interface Function (From Any Blueprint)
```
Get OverlappedActor → 
  Does Implement Interface (BPI_Interactable) → Branch (True) →
  [Interface] Interact (Target: OverlappedActor, Instigator: Self)
```

OR simply call without checking (will fail silently if not implemented):
```
Get OverlappedActor → [Interface Message] Interact
```

### Interface vs Casting

| Scenario | Use Interface | Use Cast |
|----------|--------------|----------|
| Actor type unknown at compile time | ✅ | ❌ |
| Need access to specific variables | ❌ | ✅ |
| One-size-fits-all API (e.g., all interactables) | ✅ | ❌ |
| Performance-sensitive (interfaces are slightly faster) | ✅ | — |

### Interface Best Practices
- Interfaces define **what** something can do, not **how**
- Keep interfaces small and focused (Single Responsibility)
- Use for: Interactable, Damageable, DialogueParticipant, CombatReceiver
- Prefix: `BPI_`

---

## 5. Level Blueprint Communication

**When to use:** You need to react to level-specific events (a door opens when a trigger is stepped on) that don't need to be reusable.

### How to Reference Level Actors
1. Select the actor in the Level Editor viewport
2. Open the Level Blueprint
3. Right-click in Event Graph → "Create a Reference to [ActorName]"
4. This creates a node specific to THAT instance in THAT level

### Typical Level Blueprint Patterns
```
Event BeginPlay → Set Game Mode Settings → Start Ambient Music

Trigger Volume ActorBeginOverlap → Target Door Actor → Open Door

Custom Game Event → Load Next Level
```

### When NOT to Use Level Blueprint
- For reusable logic (use Blueprint Classes instead)
- For anything that needs to work across multiple levels
- For AI behavior
- For player input

---

## 6. Game Instance Communication (Cross-Level)

**When to use:** You need to pass data between levels (player score, inventory, settings).

```
Project Settings → Maps & Modes → Game Instance Class → BP_MyGameInstance

BP_MyGameInstance:
  Variables: PlayerScore (int), PlayerInventory (array), SavedLevel (name)

Saving data to Game Instance:
  Get Game Instance → Cast To BP_MyGameInstance → Set PlayerScore

Reading from Game Instance:
  Get Game Instance → Cast To BP_MyGameInstance → Get PlayerScore
```

### Game Instance Lifecycle
```
Exists from: Application Start
Destroyed at: Application Quit
Persists across: Level loads, level transitions, seamless travel
```

---

## 7. GetAllActorsOfClass — Broadcast to All

**When to use:** Find all actors of a type in the level and interact with each.

```
Get All Actors of Class (Actor Class: BP_Enemy)
  → Array of Actors → For Each Loop
    → Loop Body → Cast To BP_Enemy → Take Damage (or any call)
```

**Warning:** This is an expensive operation. Cache the result and avoid calling in Tick.

---

## 8. Blueprint Communication Quick Lookup

### "How do I make Actor A call a function on Actor B?"
→ **Direct Reference**: Give A a variable referencing B; assign in editor

### "How do I react to Actor A from multiple different Blueprints?"
→ **Event Dispatcher**: A broadcasts; B, C, D bind to the dispatcher

### "How do I call 'Interact' on any actor without knowing its class?"
→ **Blueprint Interface**: Define BPI_Interactable; any class implements it

### "How do I access the player's speed from an AI Blueprint?"
→ **Cast**: Get Player Pawn → Cast To BP_PlayerJediCharacter → Get Speed

### "How do I share data between levels?"
→ **Game Instance**: Store in BP_GameInstance; accessible anywhere

### "How do I trigger a specific placed actor in the level?"
→ **Level Blueprint**: Reference by selecting in viewport, use in Level BP graph

---

## 9. Dantooine-Specific Communication Map

```
BP_DantooinePlayerController
  → Creates & owns: WBP_HUD
  → Dispatchers: OnQuestUpdated, OnDialogueStarted
  → Casts to: BP_PlayerJediCharacter

BP_PlayerJediCharacter
  → Implements: BPI_CombatReceiver
  → Dispatchers: OnHealthChanged, OnAttack, OnBlock
  → Direct ref to: BP_DantooineQuestManager

BP_DantooineQuestManager
  → Dispatchers: OnQuestStageChanged, OnObjectiveComplete
  → All quest blueprints bind to these

BP_LightsaberWorkbench
  → Implements: BPI_Interactable
  → PlayerController calls Interact(self)

BP_NPC_AIController
  → Reads/Writes: BB_RoamingNPC (Blackboard)
  → Runs: BT_RoamingNPC (Behavior Tree)

BP_Sparring_AIController
  → Reads/Writes: BB_Sparring
  → Runs: BT_Sparring
  → Direct ref to player via Blackboard TargetActor key
```
