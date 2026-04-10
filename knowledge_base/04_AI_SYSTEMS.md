# AI Systems — Complete Reference
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero)
> Last Updated: 2026-04-10 | UE 5.6

---

## 1. AI Architecture Overview

```
AIController (Brain) ─── possesses ──→ Character/Pawn (Body)
       │                                      │
       ├── Runs ──→ Behavior Tree             └── Uses ──→ NavMesh (Navigation)
       │             └── Reads/Writes
       │                   Blackboard (Memory)
       │
       └── Optional: AIPerceptionComponent (Sight/Hearing/Damage sensors)

PawnSensing (older, simpler) OR AIPerception (modern, recommended)
```

---

## 2. Navigation Mesh (NavMesh)

**Required for all AI movement.**

### Setup
1. Place a `Nav Mesh Bounds Volume` in the level
2. Scale it to cover entire playable area (X, Y = footprint; Z = height)
3. Press **P** to visualize (green = walkable, missing = not covered)
4. NavMesh builds automatically on Play, or manually: **Build → Build All**

### Key Settings (NavMesh Bounds Volume)
| Setting | Description |
|---------|-------------|
| `Agent Radius` | Minimum gap AI can navigate through |
| `Agent Height` | Minimum ceiling height AI can pass under |
| `Cell Size` | Precision (smaller = more accurate, more memory) |

### Navigation Nodes
| Node | Description |
|------|-------------|
| `Move To Actor` | AI moves to target actor via pathfinding |
| `Move To Location` | AI moves to world position |
| `Get Random Point in Navigable Radius` | Random walkable point within radius |
| `Get Random Reachable Point in Radius` | Random point guaranteed reachable |
| `Project Point to Navigation` | Snap a point to nearest walkable location |
| `Simple Move to Location` | Simpler move without full controller overhead |
| `Navigate to Location` | Lower-level navigation call |

---

## 3. AIController

**The "brain" Blueprint that possesses and drives the AI Character/Pawn.**

### Setup
1. Blueprint Class → Parent: `AIController`
2. Name with `BP_` prefix (e.g., `BP_NPC_AIController`)
3. In the AI Character Blueprint → Details → `AI Controller Class` → select your controller
4. Set `Auto Possess AI` → `Placed in World or Spawned`

### Standard BeginPlay Pattern
```
Event BeginPlay →
  Run Behavior Tree (BT Asset: BT_RoamingNPC)
```

### Key Functions
| Node | Description |
|------|-------------|
| `Run Behavior Tree` | Starts executing a Behavior Tree asset |
| `Get Blackboard` | Returns the Blackboard component for key access |
| `Set Value as Bool` | Writes Bool to a Blackboard key |
| `Set Value as Float` | Writes Float to a Blackboard key |
| `Set Value as Int` | Writes Int to a Blackboard key |
| `Set Value as Vector` | Writes Vector to a Blackboard key |
| `Set Value as Object` | Writes Object reference to a Blackboard key |
| `Set Value as Class` | Writes Class reference to a Blackboard key |
| `Set Value as Rotator` | Writes Rotator to a Blackboard key |
| `Get Value as Bool/Float/etc.` | Reads from Blackboard key |
| `Clear Value` | Resets a Blackboard key to default |
| `Move To Actor` | Commands possession pawn to move to actor |
| `Move To Location` | Commands pawn to move to location |
| `Stop Movement` | Immediately halts navigation |
| `Get Controlled Pawn` | Returns possessed pawn |
| `Get Pawn` | Same (shorter) |

---

## 4. Blackboard

**AI working memory — key-value store shared between AIController and Behavior Tree.**

### Creating a Blackboard
```
Content Browser → Right-click → Artificial Intelligence → Blackboard
Name: BB_RoamingNPC (use BB_ prefix)
```

### Key Types
| Type | Used For |
|------|----------|
| `Bool` | Flags: IsTalking, FightActive, HasSeenPlayer, HasHeardSound |
| `Float` | Numeric values: DistanceToTarget, WaitDuration, Timer |
| `Int` | Counters: HitsTaken, PatrolIndex |
| `Vector` | Locations: PatrolLocation, LastKnownLocation, WanderPoint |
| `Object` | Actor refs: TargetActor, ConversationTarget, PlayerCharacter |
| `Class` | Class refs |
| `Rotator` | Rotation data |
| `String` / `Name` | Text identifiers |

### Blackboard Keys — Dantooine Project

**BB_RoamingNPC Keys:**
| Key | Type | Purpose |
|-----|------|---------|
| `PatrolLocation` | Vector | Next patrol destination |
| `IsTalking` | Bool | Currently in dialogue |
| `ConversationTarget` | Object | Who they're talking to |
| `WaitDuration` | Float | How long to pause at a point |

**BB_Sparring Keys:**
| Key | Type | Purpose |
|-----|------|---------|
| `TargetActor` | Object | Who to fight |
| `FightActive` | Bool | Combat is active |
| `HitsTaken` | Int | Damage counter |

### Common Blackboard Keys (General Patterns from Book)
```
CurrentPatrolPoint  → Object/Actor: target patrol waypoint
PlayerCharacter     → Object: cached player reference
HasHeardSound       → Bool: sound detection flag
LocationOfSound     → Vector: where sound was heard
WanderPoint         → Vector: random wander destination
LastKnownPlayerLoc  → Vector: player's last seen location
AlertLevel          → Float: 0-1 awareness meter
```

---

## 5. Behavior Tree

**Tree-based decision-making. Executes top-to-bottom, left-to-right.**

### Behavior Tree Node Types

#### Composite Nodes (Control Flow)
| Node | Behavior | Rule |
|------|----------|------|
| `Selector` | Tries children left→right; stops at first **SUCCESS** | Like "OR" — find first working option |
| `Sequence` | Runs children left→right; stops at first **FAILURE** | Like "AND" — all steps must succeed |
| `Simple Parallel` | Runs a Task + a subtree simultaneously | Background behavior while moving |

#### Task Nodes (Actions / Leaves)
| Node | Behavior |
|------|----------|
| `Move To` | Navigates to a Blackboard key (Vector or Object) |
| `Wait` | Pauses execution for duration (can use random deviation) |
| `Play Sound` | Plays a sound cue |
| `Clear Blackboard Value` | Resets a BB key |
| `Set Blackboard Value` | Writes a value to a BB key |
| `Run Behavior Tree` | Calls a sub-tree |
| `Rotate to Face BB Entry` | Rotates AI to face a location/actor BB key |
| Custom BTT Blueprint | Your own task logic |

#### Decorator Nodes (Conditions)
Attached to composite or task nodes; block execution if condition fails.

| Decorator | Behavior |
|-----------|----------|
| `Blackboard` | Check BB key: Is Set, Is Not Set, == value, != value, etc. |
| `Is at Location` | Is AI within acceptable distance of a location |
| `Does Path Exist` | Is there a nav path to target |
| `Cooldown` | Prevent re-execution for N seconds |
| `Loop` | Repeat decorated branch N times or infinitely |
| `Force Success` | Always return success (optional branches) |
| `Time Limit` | Abort if takes too long |
| Custom BTD Blueprint | Your own condition logic |

#### Service Nodes (Tick Updates)
Attached to composite nodes; run periodically while branch is active.

| Service | Use |
|---------|-----|
| `Default Focus` | Keep AI looking at a target |
| `Run EQS Query` | Environment Query System spatial query |
| Custom BTS Blueprint | Update Blackboard values on interval |

---

## 6. Custom BT Task Blueprints

**How to create a custom task action.**

### Setup
1. Content Browser → Blueprint Class → Parent: `BTTask_BlueprintBase`
2. Name: `BTT_FindRandomPatrol` (BTT_ prefix)

### Implementation
```
Override: Event Receive Execute AI
  Input: Owner Controller (AIController), Controlled Pawn (Pawn)
  
  Owner Controller → Get Blackboard →
  Get Random Reachable Point in Radius (Origin: Pawn Location, Radius: 1000) →
  Set Value as Vector (Key: PatrolLocation) →
  Finish Execute (Success: true)

Override: Event Receive Tick AI (optional — for tasks that run over multiple frames)
  → Check progress each frame
  → When done: Finish Execute (Success: true)
  → On fail: Finish Execute (Success: false)

CRITICAL: ALWAYS call Finish Execute at the end.
  Success: true → Task succeeds (Sequence continues to next node)
  Success: false → Task fails (Selector tries next child)
```

### Task-Available Functions
| Function | Description |
|----------|-------------|
| `Get AIController` | Returns the owning AIController |
| `Get Blackboard Component` | Returns the Blackboard |
| `Apply Movement Input` | Sends movement to the pawn |
| `Finish Execute` | End the task (Required!) |
| `Finish Latent Execute` | End a latent task (delayed) |

---

## 7. Custom BT Decorator Blueprints

**How to create a custom condition check.**

```
Parent: BTDecorator_BlueprintBase
Name: BTD_CanSeePlayer (BTD_ prefix)

Override: Perform Condition Check AI
  Owner Controller: AIController
  Controlled Pawn: Pawn
  
  → Do visibility check (LineTrace)
  → Return: Bool (true = condition met = allow execution)
```

---

## 8. Custom BT Service Blueprints

**How to create a periodic update service.**

```
Parent: BTService_BlueprintBase
Name: BTS_UpdatePlayerLocation (BTS_ prefix)

Override: Event Receive Tick AI
  Owner Controller: AIController
  Controlled Pawn: Pawn
  
  → Get Player Pawn (index 0)
  → Get Actor Location
  → Set Value as Vector (BB Key: LastKnownPlayerLoc)
```

---

## 9. Pawn Sensing Component (Simpler/Older System)

**Add to AI Character or AIController for basic sight + hearing.**

### Adding
Open AI Character Blueprint → Add Component → `Pawn Sensing`

### Properties
| Property | Description |
|----------|-------------|
| `Sight Radius` | Max vision distance (cm) |
| `Peripheral Vision Angle` | Half-angle of vision cone (0–180°) |
| `Hearing Threshold` | Max hearing distance |
| `LOSSightRadius` | Line-of-sight maximum radius |
| `bSeePawns` | Detect Pawns |
| `bHearNoises` | Detect noises |

### Events (Bind in AIController BeginPlay)
```
Get Pawn Sensing Component → 
  Bind Event to OnSeePawn → [Custom Event: HandleSeePawn(SeenPawn: Pawn)]
  Bind Event to OnHearNoise → [Custom Event: HandleHearNoise(Instigator, Location, Volume)]

HandleSeePawn:
  Get Blackboard → Set Value as Object (Key: PlayerCharacter, Value: SeenPawn)
  Get Blackboard → Set Value as Bool (Key: HasSeenPlayer, Value: true)

HandleHearNoise:
  Get Blackboard → Set Value as Bool (Key: HasHeardSound, Value: true)
  Get Blackboard → Set Value as Vector (Key: LocationOfSound, Value: Location)
```

### PawnNoise Emitter (On Player Character)
```
Add PawnNoiseEmitter component to BP_PlayerJediCharacter
On footstep AnimNotify:
  Make Noise (Instigator: self, Loudness: 0.5, Location: GetActorLocation)
```

---

## 10. AI Perception System (Modern Recommended)

More powerful than PawnSensing. Uses `AIPerceptionComponent` on the AIController.

### Setup
1. Add `AIPerception` component to AIController
2. In Details: Add Senses (Sight, Hearing, etc.)
3. Configure radius, cone angle, detection rates
4. Bind `On Target Perception Updated` event

### Sense Types
| Sense | Detects |
|-------|---------|
| `AISense_Sight` | Visual detection via line of sight |
| `AISense_Hearing` | Sound events via Report Noise |
| `AISense_Damage` | Damage received |
| `AISense_Touch` | Physical contact |
| `AISense_Prediction` | Anticipates target movement |
| `AISense_Team` | Team awareness |

### Event Pattern
```
On Target Perception Updated (Actor: Actor, Stimulus: FAIStimulus)
  → Break AIStimulus → Was Successfully Sensed (Bool)
  → Branch:
    True → Set Blackboard TargetActor = Actor; Set FightActive = true
    False → Clear Blackboard TargetActor; Set FightActive = false
```

---

## 11. Environment Query System (EQS)

**Spatial query system for finding the BEST position for AI actions.**

### Enable Plugin
`Edit → Plugins → Environment Query Editor → Enable`

### Creating an EQS Query
```
Content Browser → Artificial Intelligence → Environment Query
Name: EQS_FindAttackPosition

Query Graph:
  Points:Circle Generator
    Center Context: AI Actor location
    Radius: 400
    Number of Rings: 2
    Points per Ring: 8
  
  Tests:
    Distance (from AI): Filter Minimum = 100 (don't stand on top of target)
    Trace (visibility to player): Filter → must be visible
    Dot (facing direction): Score → prefer positions in front of player
```

### Using EQS in Behavior Tree
- Add `Run EQS Query` service to a composite node
- Or use `EQS Query` task node

### EQS Generators
| Generator | Creates Candidates From |
|-----------|------------------------|
| `Actors of Class` | Existing actor locations |
| `Points: Circle` | Ring around context |
| `Points: Grid` | Grid around context |
| `Points: Cone` | Cone in a direction |
| `Points: Donut` | Ring with inner + outer radius |
| `Points: Pathing Grid` | Nav-aware grid |
| `Current Location` | Where the querier is standing |

### EQS Tests
| Test | Purpose |
|------|---------|
| `Distance` | Score by distance from context |
| `Dot` | Score by directional alignment |
| `Pathfinding` | Filter non-navigable points |
| `Trace` | Check line-of-sight |
| `Overlap` | Check spatial clearance |
| `Gameplay Tags` | Filter by actor tags |

---

## 12. SpawnDefaultController — Critical Rule

**Any AI Character/Pawn spawned via `Spawn Actor from Class` at RUNTIME does NOT automatically get its AIController. You MUST call `SpawnDefaultController` manually.**

```
In spawned AI Character's Event BeginPlay:
  SpawnDefaultController

OR at the spawn point:
  Spawn Actor from Class → Return Value → SpawnDefaultController
```

**Pawns/Characters placed in the Level Editor** get their controller automatically.
**Runtime-spawned** ones do NOT — always add the SpawnDefaultController call.

---

## 13. Behavior Tree Design Patterns

### Patrol Pattern (BT_RoamingNPC)
```
ROOT
  └── Selector
        ├── Sequence [Decorator: Blackboard IsTalking == true]
        │     └── Wait (5s)  ← NPC stands and talks
        └── Sequence (default patrol loop)
              ├── BTT_FindRandomPatrol → sets BB PatrolLocation
              ├── Move To (BB: PatrolLocation)
              └── Wait (Random: 2-4s)
```

### Alert/Investigate Pattern
```
ROOT
  └── Selector
        ├── Sequence [Decorator: Blackboard FightActive == true]
        │     ├── Move To (BB: TargetActor)
        │     └── Custom Task: ExecuteAttack
        ├── Sequence [Decorator: Blackboard HasHeardSound == true]
        │     ├── Move To (BB: LocationOfSound)
        │     └── Clear Blackboard Value (HasHeardSound)
        └── Sequence (idle patrol)
              └── ... patrol tasks ...
```

### Sparring Combat Pattern (BT_Sparring)
```
ROOT
  └── Selector
        ├── Sequence [Decorator: Blackboard FightActive == true]
        │     ├── Move To TargetActor (Acceptable Radius: 150)
        │     └── Custom Task: DoAttack
        └── Wait (2s)  ← idle until fight starts
```
