# Blueprint Fundamentals — Complete Reference
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero), Unreal Engine Blueprint Game Developer (Asadullah Alam)
> Last Updated: 2026-04-10 | UE 5.6

---

## 1. What Are Blueprints?

Blueprints Visual Scripting is a node-based programming system built into Unreal Engine. It compiles to bytecode that runs on the Unreal Virtual Machine. Blueprints allow complete game logic, AI, UI, and gameplay without writing C++.

**Key facts:**
- Every Blueprint is a **class** — it defines variables (state) and events/functions (behavior)
- Every Blueprint placed in a level is an **instance** of that class
- All instances share the same class defaults but can have per-instance overrides via **Instance Editable** variables
- Blueprints are compiled — always **compile** after any change

---

## 2. Blueprint Types

| Type | Created Via | Purpose |
|------|------------|---------|
| **Blueprint Class** | Blueprint > Blueprint Class | Interactive game objects (actors, pawns, characters) |
| **Level Blueprint** | Toolbar > Blueprints > Open Level Blueprint | Level-specific one-off logic; exists once per level; cannot be reused |
| **Widget Blueprint** | Blueprint > Widget Blueprint | UMG UI screens, HUDs, menus |
| **Animation Blueprint** | Blueprint > Animation Blueprint | Character animation logic + state machines |
| **Blueprint Interface** | Blueprint > Blueprint Interface | Defines a contract of functions any class can implement |
| **Blueprint Macro Library** | Blueprint > Blueprint Macro Library | Shared macros (reusable node groups with multi exec pins) |
| **Blueprint Function Library** | Blueprint > Blueprint Function Library | Shared static utility functions callable from any Blueprint |
| **Data-Only Blueprint** | Blueprint > Blueprint Class (no code) | Blueprint with only CDO variable overrides, no graph logic |
| **Enumeration** | Blueprint > Enumeration | Named list of constants |
| **Structure** | Blueprint > Structure | Grouped set of named typed fields |

---

## 3. Blueprint Editor Panels

| Panel | Purpose |
|-------|---------|
| **Toolbar** | Compile, Save, Play, Class Settings, Class Defaults |
| **Components** | Add/manage components attached to the Actor (Mesh, Camera, Collision, Audio...) |
| **My Blueprint** | Lists all Variables, Functions, Macros, Event Dispatchers, Graphs |
| **Details** | Properties of the selected node or component |
| **Viewport** | 3D preview of the Blueprint actor and its components |
| **Event Graph** | Main visual scripting canvas — where nodes are placed and connected |
| **Construction Script** | Runs at edit-time and on spawn; procedural setup |
| **Function Graphs** | Separate graphs for each defined function |

---

## 4. Variable Types (Pin Colors)

| Type | Pin Color | Size | Use For |
|------|-----------|------|---------|
| **Boolean** | Red | 1 bit | True/False flags |
| **Byte** | Teal | 8-bit | 0–255 integer |
| **Integer** | Cyan | 32-bit | Whole numbers |
| **Integer64** | Dark Cyan | 64-bit | Large whole numbers |
| **Float** | Light Green | 32-bit | Decimal numbers (positions, timers) |
| **Double** | Dark Green | 64-bit | High-precision decimals |
| **Name** | Violet | — | Immutable identifier; used for asset names, socket names |
| **String** | Magenta | — | Mutable text; for display/debug |
| **Text** | Pink | — | Localizable display text |
| **Vector** | Yellow/Gold | 3 floats | 3D positions, directions, scales |
| **Rotator** | Purple | 3 floats | Roll, Pitch, Yaw in degrees |
| **Transform** | Orange | 10 floats | Location + Rotation + Scale combined |
| **Object Reference** | Blue | pointer | Reference to an instance of any UObject class |
| **Class Reference** | Purple | pointer | Reference to the class TYPE (not an instance) |
| **Struct** | Dark Green | varies | Custom grouped data |
| **Enum** | Pink | byte | Named option from a defined list |
| **Array** | 3D pin border | N × type | Ordered list of same-type elements |
| **Set** | Square pin | N × type | Unordered unique-element list |
| **Map** | Double pin | N × K+V | Key-value dictionary |

### Variable Property Flags

| Flag | Meaning |
|------|---------|
| **Instance Editable** | Exposes the variable to the Level Editor Details panel per-instance |
| **Blueprint Read Only** | Can be read but not set by other Blueprints |
| **Expose on Spawn** | Accessible as a pin on the Spawn Actor node |
| **Private** | Only accessible inside the owning Blueprint |
| **Expose to Cinematics** | Controllable via Sequencer tracks |
| **Transient** | Not saved with the level; reset each session |
| **Config** | Value persists to a .ini config file |
| **Replicated** | Value synced across network (multiplayer) |

---

## 5. Node Types

### Event Nodes (Red Headers)
- Start execution chains; triggered by the engine or external calls
- Have no return value pin
- **Most important events:**

| Event | When It Fires |
|-------|--------------|
| `Event BeginPlay` | Once when actor enters the game world |
| `Event Tick` | Every frame; outputs `Delta Seconds` |
| `Event EndPlay` | When actor is removed from world |
| `Event Hit` | On hard (blocking) collision |
| `Event ActorBeginOverlap` | Another actor enters overlap volume |
| `Event ActorEndOverlap` | Another actor exits overlap volume |
| `Event AnyDamage` | Actor receives any amount of damage |
| `Event PointDamage` | Actor receives directional damage |
| `Event RadialDamage` | Actor receives AOE/explosion damage |
| `Event Destroyed` | Just before actor is fully destroyed |
| `InputAction [Name]` | Input pressed/released (Pressed, Released pins) |
| `InputAxis [Name]` | Every frame with float Axis Value (-1 to 1) |
| `Event Blueprint Update Animation` | Animation Blueprint — fires every animation update |

### Function Nodes (Blue / White)
- Execute logic, may return values
- **Pure Functions** — no execution pin; evaluates when connected (green); must not have side effects
- **Impure Functions** — have execution pins; run when execution reaches them

### Macro Nodes (Green)
- Like functions but can contain latent (time-delayed) operations
- Can have multiple input AND output execution pins
- Defined in a Blueprint or a Macro Library
- NOT callable across Blueprint classes (use functions for cross-Blueprint calls)

### Custom Events
- Named execution entry points callable from within the Blueprint or from other Blueprints
- Can have input parameters
- Support `Call in Editor` flag for editor-time execution
- Created in My Blueprint panel → Events → + button

---

## 6. OOP Core Concepts

### Classes and Instances
```
Blueprint Class = Template (defines variables + behavior)
Instance = Object placed in the level from that class

Example:
BP_Tree (class) → drag 50 times into level → 50 instances
Each instance: same mesh, behavior
Per-instance overrides: height, scale (Instance Editable vars)
```

### Inheritance Chain
```
UObject (base of everything)
  └── AActor (can be placed in levels)
        ├── APawn (can be possessed/controlled)
        │     └── ACharacter (has movement, capsule, mesh)
        ├── AController
        │     ├── APlayerController (human input)
        │     └── AAIController (AI brain)
        ├── AGameModeBase (game rules)
        ├── AGameStateBase (replicated game state)
        └── APlayerState (per-player network state)
```

### Encapsulation
- **Private** variables/functions: only accessible within the owning Blueprint
- **Public** variables/functions: accessible from other Blueprints
- Use `Instance Editable` to expose variables to the level editor
- Use `Blueprint Read Only` to prevent external code from writing to variables

### Polymorphism
- A child class overrides parent functions using the `Override` dropdown
- Parent functions can be called from the child using `Parent: [FunctionName]` node
- The `Cast To` node safely converts a base class reference to a specific subclass

---

## 7. Flow Control Nodes — Complete List

| Node | Behavior | Key Pins |
|------|----------|----------|
| **Branch** | If/Else | `execute`, `Condition` (bool), `True`, `False` |
| **Switch on Int** | Routes to output pin matching int value | `execute`, `Selection` (int), case pins |
| **Switch on String** | Routes to output matching string | same pattern |
| **Switch on Enum** | Routes to output matching enum value | same pattern |
| **Flip Flop** | Alternates A/B each execution | `execute`, `A`, `B`, `Is A` (bool) |
| **Sequence** | Fires Then 0, Then 1, Then 2... in order | `execute`, `Then 0`, `Then 1`, ... |
| **Do Once** | Passes through only once; Reset re-enables | `execute`, `Reset`, `Completed` |
| **Do N** | Passes N times then stops; Reset re-enables | `execute`, `N`, `Reset`, `Completed`, `Counter` |
| **Gate** | Open/Close/Toggle control pass-through | `Enter`, `Open`, `Close`, `Toggle`, `Exit`, `Start Closed` |
| **MultiGate** | Routes through outputs sequentially or randomly | `execute`, `Reset`, `Is Random`, `Loop`, `Start Index`, out pins |
| **For Loop** | Iterates First Index to Last Index | `execute`, `First Index`, `Last Index`, `Loop Body`, `Index`, `Completed` |
| **For Loop with Break** | Same + `Break` pin to exit early | adds `Break` pin |
| **For Each Loop** | Iterates every array element | `execute`, `Array`, `Loop Body`, `Array Element`, `Array Index`, `Completed` |
| **For Each Loop with Break** | Same + `Break` pin | adds `Break` pin |
| **Reverse For Each Loop** | Iterates array in reverse | same as For Each |
| **While Loop** | Repeats while condition is True | `execute`, `Condition`, `Loop Body`, `Completed` |

---

## 8. Functions vs Macros vs Custom Events

| Feature | Function | Macro | Custom Event |
|---------|----------|-------|-------------|
| Can be called from other Blueprints | ✅ | ❌ (within same BP only) | ✅ |
| Can be overridden in child class | ✅ | ❌ | ✅ |
| Multiple execution outputs | ❌ | ✅ | ❌ |
| Can contain latent (Delay) nodes | ❌ | ✅ | ✅ |
| Has a Return node | ✅ | ✅ | ❌ |
| Pure function option | ✅ | ✅ | ❌ |
| Local variables | ✅ | ✅ | ❌ |
| Callable in editor | ✅ | ❌ | ✅ (with flag) |

**Rule of thumb:**
- Use **Functions** for reusable logic that other Blueprints might call
- Use **Macros** when you need multiple exec outputs or Delay nodes
- Use **Custom Events** for named callbacks or async event responses

---

## 9. Math Nodes — Complete Reference

### Scalar Math
| Node | Operation |
|------|-----------|
| `Add (float)` | A + B |
| `Subtract (float)` | A - B |
| `Multiply (float)` | A × B |
| `Divide (float)` | A / B |
| `Modulo` | A % B (remainder) |
| `Power` | Base ^ Exponent |
| `Sqrt` | √A |
| `Abs` | |A| (removes sign) |
| `Floor` | Round down |
| `Ceil` | Round up |
| `Round` | Round to nearest |
| `Clamp (float)` | Clamp between Min and Max |
| `Lerp (float)` | A + (B-A) × Alpha |
| `FInterp To` | Smooth float toward target (needs Delta Time) |
| `VInterp To` | Smooth vector toward target |
| `RInterp To` | Smooth rotator toward target |
| `Min / Max` | Returns lesser / greater of two values |
| `Sin / Cos / Tan` | Trigonometric functions (input in radians by default) |
| `Random Float` | 0.0 – 1.0 |
| `Random Float in Range` | Min to Max |
| `Random Int in Range` | Min to Max (inclusive) |

### Vector Math
| Node | Operation |
|------|-----------|
| `Vector + Vector` | Adds two vectors |
| `Vector - Vector` | Subtracts; B-A gives direction FROM A TO B |
| `Vector * Float` | Scales a vector |
| `Vector Length` | Returns scalar magnitude |
| `Normalize` | Returns unit vector (length = 1.0) |
| `Dot Product` | Scalar alignment (-1 to 1); 1=same dir, 0=perpendicular |
| `Cross Product` | Vector perpendicular to both inputs |
| `Get Forward/Right/Up Vector` | Actor's local axes as unit vectors |
| `Break Vector` | Splits into X, Y, Z floats |
| `Make Vector` | Combines X, Y, Z floats |
| `Distance (Vector)` | Distance between two points |
| `Mirror Vector by Normal` | Reflects a vector off a surface |

---

## 10. Transform Nodes

| Node | Description |
|------|-------------|
| `GetActorLocation` | Returns actor world position (Vector) |
| `SetActorLocation` | Teleports actor to world position |
| `AddActorWorldOffset` | Moves actor by delta in world space |
| `AddActorLocalOffset` | Moves actor by delta in local space |
| `GetActorRotation` | Returns Rotator |
| `SetActorRotation` | Sets absolute rotation |
| `AddActorWorldRotation` | Adds rotation delta in world space |
| `AddActorLocalRotation` | Adds rotation delta in local space |
| `GetActorScale3D` | Returns scale as Vector |
| `SetActorScale3D` | Sets scale |
| `GetActorTransform` | Full Transform (Location + Rotation + Scale) |
| `SetActorTransform` | Sets all transform at once |
| `Break Transform` | Splits Transform into parts |
| `Make Transform` | Combines parts into Transform |

---

## 11. Trace / Raycast Nodes

| Node | Description |
|------|-------------|
| `LineTraceByChannel` | Single ray; returns first hit against collision channel |
| `LineTraceForObjects` | Single ray against specified Object Types |
| `MultiLineTraceByChannel` | Returns ALL hits along the ray |
| `SphereTraceByChannel` | Sphere-shaped trace |
| `CapsuleTraceByChannel` | Capsule-shaped trace |
| `BoxTraceByChannel` | Box-shaped trace |
| `Break Hit Result` | Splits Hit Result: Hit Actor, Hit Component, Location, Normal, Bone Name, Blocking Hit (bool) |

### Trace Workflow
```
Get Camera World Location → (Start)
Get Actor Forward Vector × Distance + Camera Location → (End)
LineTraceByChannel → Out Hit → Break Hit Result → Hit Actor
```

---

## 12. Timeline Node — Full Reference

**Tracks:**
| Track | Output | Used For |
|-------|--------|---------|
| **Float (f)** | float per frame | FOV zoom, opacity, speed ramp |
| **Vector (V)** | Vector per frame | Position along path, scale animation |
| **Color (C)** | LinearColor | Color transitions |
| **Event (!)** | Exec pin at keyframe | Trigger exact-frame events |

**Input Pins:**
- `Play` — Play from current time
- `Play from Start` — Reset and play
- `Stop` — Pause
- `Reverse` — Play backward from current time
- `Reverse from End` — Reset to end and reverse
- `Set New Time` — Jump to time (seconds)

**Output Pins:**
- `Update` — Fires every frame while active → connect to Set nodes
- `Finished` — Fires when done
- `Direction` — Forward or Backward enum

**Common Use Cases:**
- Smooth door rotation: Float track 0→90 over 1 second → Set Actor Rotation
- FOV zoom: Float track 90→45 → Set FOV
- UI fade: Float track 1→0 → Set Widget Opacity
- Color lerp: Color track → Set Material Color Parameter

---

## 13. Collision and Physics

### Collision Response Types
| Response | Behavior |
|----------|----------|
| **Ignore** | No interaction |
| **Overlap** | Passes through; fires Begin/End Overlap events |
| **Block** | Stops movement; fires Hit event |

### Mobility Settings
| Mobility | Physics | Use |
|----------|---------|-----|
| **Static** | None | Environment props; best performance |
| **Stationary** | None | Lights that don't move |
| **Movable** | Can simulate | Any runtime-moving actor |

### Physics Nodes
| Node | Description |
|------|-------------|
| `SetSimulatePhysics` | Enable/disable physics on component |
| `SetEnableGravity` | Toggle gravity |
| `AddImpulse` | Instant force (explosion, jump boost) |
| `AddForce` | Continuous force |
| `AddTorque` | Rotational force |
| `GetPhysicsLinearVelocity` | Current velocity |
| `SetPhysicsLinearVelocity` | Override velocity |

### Collision Events
- `Event Hit` — Hard collision: OtherActor, NormalImpulse, HitLocation, HitNormal
- `Event ActorBeginOverlap` — Trigger entry: OtherActor, OtherComp
- `Event ActorEndOverlap` — Trigger exit
- `Apply Damage` — Sends damage to another actor
- `Apply Point Damage` — Directional damage with hit info
- `Apply Radial Damage` — AOE damage with falloff

---

## 14. Camera System

### Component Setup Pattern
```
Spring Arm Component
  └── Camera Component

Spring Arm:
  Target Arm Length = 300 (3rd person), 0 (1st person)
  bUsePawnControlRotation = true
  Lag Speed = 10 (smooth follow)

Camera:
  Field of View = 90 (default)
```

### Camera Nodes
| Node | Description |
|------|-------------|
| `Set View Target with Blend` | Switch player view to actor; Blend Time for smooth cut |
| `Get Player Camera Manager` | Returns Camera Manager |
| `Set Field of View` | Change FOV |
| `Play Camera Shake` | Screen shake effect |
| `Start Camera Fade` | Fade to/from black |

### FOV Zoom Pattern
```
Input Pressed → Timeline Play
Input Released → Timeline Reverse
Timeline Update → [FOV float] → Set FOV (Camera Component)
```

---

## 15. Delta Time — Frame Independence

**RULE: Any value applied per-frame MUST be multiplied by Delta Seconds**

```
Event Tick → [Delta Seconds]
Speed (float) × Delta Seconds → Add Actor World Offset
```

Without Delta Time: speed is frame-rate dependent (broken at 30fps vs 120fps)
With Delta Time: speed is consistent at any frame rate

---

## 16. Actor Spawning and Lifecycle

### Spawn Nodes
| Node | Description |
|------|-------------|
| `Spawn Actor from Class` | Spawns an actor into the world |
| `Destroy Actor` | Immediately removes actor |
| `Set Life Span` | Actor auto-destroys after N seconds |
| `Is Valid` | Checks if object reference is not null/garbage |
| `Is Pending Kill` | Checks if object is about to be destroyed |

### Spawn Pattern
```
Spawn Actor from Class:
  Class: [BP_MyActor]
  Spawn Transform: Make Transform (Location, Rotation, Scale)
  Collision Handling Override: Always Spawn
  → Return Value: reference to spawned actor
```

### Lifecycle Order
```
Constructor → BeginPlay → Tick (every frame) → EndPlay → Destroyed
Construction Script runs at: edit-time placement, property changes, BeginPlay spawn
```

---

## 17. Construction Script

Runs when:
1. Blueprint placed in the level (edit-time)
2. Any Instance Editable property is changed in editor
3. Actor spawns at runtime (before BeginPlay)

**Common Construction Script Patterns:**
```
Dynamic Mesh Swap:
  Get MeshType variable → Branch → Set Static Mesh

Procedural ISM Placement:
  Get Spline Length → Divide by Spacing → Floor → For Loop
  → Get Location at Distance → Add Instance (ISM component)

Material Parameter Init:
  Get Color variable → Create Dynamic Material Instance → Set Vector Parameter
```

---

## 18. Spline System

### Components
- **Spline Component** — Curved path; editable in viewport by moving control points
- **Spline Mesh Component** — Deforms a mesh between two spline points
- **Instanced Static Mesh (ISM)** — Places many identical meshes efficiently

### Spline Nodes
| Node | Description |
|------|-------------|
| `Get Spline Length` | Total length in cm |
| `Get Location at Distance Along Spline` | World position at distance |
| `Get Rotation at Distance Along Spline` | World rotation at distance |
| `Get Tangent at Distance Along Spline` | Direction vector at distance |
| `Get Number of Spline Points` | Count of control points |
| `Add Spline Point` | Append control point |
| `Set Tangents at Spline Point` | Adjust curve shape |

### Spline Fence/Path Pattern (Construction Script)
```
Get Spline Length → / SpaceBetweenFencePosts → Floor → (Count)
For Loop 0 to Count:
  Index × SpaceBetweenFencePosts → Get Location at Distance Along Spline → Location
  Same distance → Get Rotation at Distance Along Spline → Rotation
  → Add Instance (ISM, Location, Rotation)
```

---

## 19. Blueprint Best Practices (From Books)

### Organization
- Press **C** to wrap selected nodes in a Comment Box with a label
- Color-code comment boxes: green = working, yellow = WIP, red = broken
- Keep Event Graph clean; move complex logic into named Functions
- Use `Collapsed Graph` to fold a set of nodes into a single node visually

### Performance
- **Never Cast in Tick** — Cast once in BeginPlay and cache the reference
- **Use Is Valid before every object call** — prevents null-pointer crashes
- **Avoid deep inheritance chains** — prefer composition (components) over deep hierarchy
- **Do Once** — use Do Once node to prevent an event firing more than once per session
- **Pure functions** are re-evaluated every time they're read; avoid expensive pure functions
- Replace complex math with **texture lookups** in materials (faster on GPU)

### Debugging
- `Print String` — prints to screen (Duration, Color, Key for unique messages)
- `Draw Debug Line / Box / Sphere / Point` — visualize traces and bounds in editor
- Right-click a variable → `Watch This Value` — show live value in editor
- Breakpoints: right-click a node → `Add Breakpoint` to pause execution
- `Log` category in Output Log: `UE_LOG(LogTemp, Warning, TEXT("..."))`

### Code Smell to Avoid
```
BAD: Every frame → Cast To BP_Player → Get Health → Update UI
GOOD: Cache cast result in BeginPlay → Event Dispatcher → OnHealthChanged → Update UI

BAD: Level Blueprint has all the game logic
GOOD: Each actor manages its own state; GameMode manages rules

BAD: Giant monolithic Event Graph with 200 nodes
GOOD: Functions named clearly; each doing one thing
```

