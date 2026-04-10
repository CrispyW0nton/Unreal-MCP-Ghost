# Blueprint Libraries and Components — Complete Reference
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero, Ch.18 + Ch.19)
> Function Libraries, Macro Libraries, Actor Components, Scene Components, Procedural Generation, Editor Utilities

---

## 1. Blueprint Function Libraries

**A Blueprint class that contains ONLY static functions callable from any Blueprint in the project. No instances needed.**

### Creating a Blueprint Function Library
`Content Browser → Add → Blueprint Class → Blueprint Function Library`
Name with `FL_` or `BFL_` prefix (e.g., `BFL_MathUtilities`, `BFL_DantooineHelpers`)

### Characteristics
- Functions are **static** — no instance required to call them
- Available in the right-click menu of ANY Blueprint graph under the library's category
- Cannot have instance variables (only local function variables)
- Cannot implement interfaces
- Great for: math helpers, string utilities, game-wide helper functions

### Example: BFL_DantooineHelpers
```
[Function: CalculateLightsaberDamage]
  Input: BaseDamage (float), DifficultyMultiplier (float), IsCritical (bool)
  Output: FinalDamage (float)
  Logic:
    result = BaseDamage * DifficultyMultiplier
    Branch (IsCritical = true):
      True → result * 2.5
      False → result
    Return result

[Function: GetNPCDialoguePriority]
  Input: NPCState (E_NPCDialogueMode), PlayerQuestStage (E_QuestStage)
  Output: Priority (int)
  
[Function: IsPlayerInRange]
  Input: PlayerLocation (Vector), TargetLocation (Vector), Range (float)
  Output: InRange (bool)
  Logic:
    VectorLength(PlayerLocation - TargetLocation) <= Range → Return
```

### Calling Library Functions
- Right-click in any Blueprint graph → search for function name
- Functions appear under the library's category label
- Or: right-click → type function name directly

---

## 2. Blueprint Macro Libraries

**A library of reusable Macros callable from Blueprints of the specified parent class.**

### Creating a Blueprint Macro Library
`Content Browser → Add → Blueprint Class → Blueprint Macro Library`
In parent class dialog: choose the base class (usually `Actor`)

### When to Use Macros vs Functions
| Feature | Macro | Function |
|---|---|---|
| Latent operations (Delay) | ✅ Yes | ❌ No |
| Multiple exec inputs/outputs | ✅ Yes | ❌ No (one in/out) |
| Callable from other BPs | ⚠️ Only if in Macro Library | ✅ Yes |
| Local variables | ✅ Yes | ✅ Yes |
| Return values | ✅ Yes | ✅ Yes |

### Macro Library Example: Validation Macros
```
[Macro: SafeGetPlayer]
  Input: exec
  Output: Found (exec), Not Found (exec), PlayerRef (BP_PlayerJediCharacter)
  Logic:
    GetPlayerCharacter → Cast To BP_PlayerJediCharacter
    Cast Succeeded → Found, return cast result
    Cast Failed → Not Found

[Macro: IsInCombatRange]
  Input: exec, Actor A, Actor B, Range (float)
  Output: InRange (exec), OutOfRange (exec)
  Logic:
    GetDistanceTo(A, B) <= Range → Branch → InRange / OutOfRange
```

---

## 3. Actor Components

**Reusable behavior modules attached to Actors. No Transform. Encapsulate a behavior that can be reused.**

### Creating an Actor Component
`Content Browser → Add → Blueprint Class → Actor Component`
Name with `AC_` prefix (e.g., `AC_HealthSystem`, `AC_DialogueHandler`)

### Characteristics
- No position/rotation — pure logic
- Can have variables and functions
- Tick is optional (disable for performance)
- Lifecycle events: BeginPlay, Tick, EndPlay, OnComponentCreated

### Adding to a Blueprint
1. Open target Blueprint
2. Components panel → Add Component → search for your component name
3. In details: configure component properties

### Actor Component Pattern: AC_HealthSystem
```
Variables:
  MaxHealth (float) = 100.0
  CurrentHealth (float) = 100.0
  IsDead (bool) = false

Event Dispatchers:
  OnHealthChanged (NewHealth: float, MaxHealth: float)
  OnDeath

Functions:
  TakeDamage(Amount: float):
    CurrentHealth = Clamp(CurrentHealth - Amount, 0, MaxHealth)
    Call OnHealthChanged (CurrentHealth, MaxHealth)
    Branch (CurrentHealth <= 0.0 AND NOT IsDead):
      → IsDead = true → Call OnDeath
      
  Heal(Amount: float):
    CurrentHealth = Clamp(CurrentHealth + Amount, 0, MaxHealth)
    Call OnHealthChanged (CurrentHealth, MaxHealth)
    
  GetHealthPercent() → float:
    Return CurrentHealth / MaxHealth (Pure function)
```

### Using the Component in Parent Blueprint
```
[In BP_PlayerJediCharacter or BP_SparringOpponent]
BeginPlay:
  Get AC_HealthSystem component
  Bind to OnHealthChanged → Update WBP_HUD health bar
  Bind to OnDeath → Trigger death sequence
  
On damage received:
  Get AC_HealthSystem → TakeDamage(DamageAmount)
```

---

## 4. Scene Components

**Like Actor Components but WITH a Transform (position, rotation, scale). Can have children.**

### Creating a Scene Component
`Content Browser → Add → Blueprint Class → Scene Component`

### When to Use Scene Components
- When the component needs a physical attachment point in space
- When other components need to be parented to it
- Example: `AC_WeaponMount` — a socket at a specific bone position

### Scene Component Pattern: SC_LightsaberSocket
```
This Scene Component represents the lightsaber attachment point.
Variables:
  EquippedLightsaber (BP_Lightsaber object ref)
  IsEquipped (bool)
  
Functions:
  EquipLightsaber(Lightsaber: BP_Lightsaber):
    EquippedLightsaber = Lightsaber
    AttachActorToComponent(Lightsaber, this component, Socket="LightsaberGrip")
    IsEquipped = true
    
  UnequipLightsaber():
    DetachFromComponent(EquippedLightsaber)
    IsEquipped = false
```

---

## 5. Procedural Generation

### Construction Script Patterns (Romero Ch.19)

**Generation at edit-time and spawn-time.**

#### Pattern: Random Spawner Array
```
[Construction Script in BP_TreeLine]
SplineComp = Get Spline Component
SplineLength = Get Spline Length
Count = Floor(SplineLength / TreeSpacing)

For Loop (0 to Count-1):
  DistanceAlong = Index * TreeSpacing
  Location = Get Location at Distance Along Spline (DistanceAlong, World)
  Rotation = Get Rotation at Distance Along Spline (DistanceAlong, World)
  AddInstance (ISM, MakeTransform(Location, Rotation, RandomScale))
```

#### Pattern: Procedural Building Facade
```
[Construction Script in BP_Facade]
For Y (0 to FloorCount-1):
  For X (0 to WindowsPerFloor-1):
    WindowLocation = MakeVector(X * WindowSpacing, 0, Y * FloorHeight)
    AddInstance (WindowISM, MakeTransform(WindowLocation, (0,0,0), (1,1,1)))
```

### Spline Mesh Component Pattern
```
[For a road/rail that deforms along a spline]
Construction Script:
  For each spline segment (0 to NumberOfPoints-2):
    StartPoint = GetLocationAtSplinePoint(i, Local)
    EndPoint = GetLocationAtSplinePoint(i+1, Local)
    StartTangent = GetTangentAtSplinePoint(i, Local)
    EndTangent = GetTangentAtSplinePoint(i+1, Local)
    
    SplineMeshComp = Add Spline Mesh Component
    SplineMeshComp.SetStartAndEnd(StartPoint, StartTangent, EndPoint, EndTangent)
    SplineMeshComp.SetStaticMesh(RoadMeshAsset)
```

---

## 6. Editor Utility Blueprints

**Blueprints that run inside the Unreal Editor (edit-mode only). For creating editor tools.**

### Types
- **Editor Utility Blueprint** — can access editor functionality
- **Actor Action Utility** — right-click actors → run script
- **Asset Action Utility** — right-click assets → run script

### Creating an Actor Action Utility
`Content Browser → Add → Editor Utilities → Editor Utility Blueprint → Actor Action Utility`

### Pattern: Batch Rename Actors
```
[Function: RenameSelectedActors]
  GetSelectedActors → For Each Loop:
    Actor → GetActorLabel → Append "_LOD0"
    Actor → SetActorLabel (new name)
```

### Pattern: Auto-Place NavMesh Bounds
```
[Function: SetupNavMesh]
  Get All Actors of Class (NavMeshBoundsVolume)
  IS EMPTY → Spawn Actor from Class (NavMeshBoundsVolume)
  Set Scale to cover level bounds
```

---

## 7. Blueprint Best Practices Summary (Romero Ch.15 + Ch.18)

### Class Design Rules
1. **Single Responsibility** — Each Blueprint does ONE thing well
2. **No duplicate logic** — Shared behavior → Function Library or Component
3. **No Level Blueprint game rules** — Put in GameMode
4. **Clear naming** — `AC_` for components, `BFL_` for libraries
5. **Collapse to Function** — any repeated group of nodes in same BP
6. **Add tooltips** to all exposed variables

### Component vs. Blueprint Inheritance
| Use Component When | Use Inheritance When |
|---|---|
| Behavior can be mixed and matched | Behavior is fundamental to the class |
| Multiple classes need the same behavior | Subtype relationship is natural |
| Behavior is optional/pluggable | ALL instances need this behavior |

Example: Health system → Component (NPCs, player, breakables all need it, but differently)
Example: AI patrol behavior → NPC base class with derived students/guards (all NPCs share it)

---

## 8. VR Blueprint Patterns (Romero Ch.16)

**The VR Template demonstrates advanced Blueprint Interface usage.**

### VRPawn Component Structure
```
VRPawn (parent: Pawn):
  Camera (HMD view)
  HMD (static mesh representing headset)
  MotionControllerLeft (left hand, grip)
  MotionControllerRight (right hand, grip)
  MotionControllerLeftAim (left hand, aim)
  MotionControllerRightAim (right hand, aim)
  TeleportTraceNiagaraSystem
  WidgetInteraction (for menu laser pointer)
```

### Teleport Implementation Pattern
```
InputAxis MovementAxisRight_Y:
  Axis Value > 0 AND > Deadzone (0.7) → Branch True
    Do Once → StartTeleportTrace
    → Update teleport destination each frame
  Axis Value Released → Execute Teleport
    → Fade screen → Set Actor Location → Fade back
```

### Grab Implementation via Interface
```
GrabbableInterface functions: Grab(MotionController), Drop

On Grip Button Pressed (right controller):
  Get Overlapping Actors (MotionControllerRight sphere)
  For Each → Does Implement Interface (GrabbableInterface)?
    → True → Call Grab on Actor → break loop
    
On Grip Button Released:
  GrabbedObject ref → Call Drop
  Clear GrabbedObject ref
```

---
