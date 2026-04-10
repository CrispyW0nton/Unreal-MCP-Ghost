# Animation System — Complete Reference
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero), Mastering Technical Art in UE (Greg Penninck)
> Covers Animation Blueprints, State Machines, Blend Spaces, Montages, Notifies, IK, and the Dantooine animation setup.

---

## 1. ANIMATION ASSET TYPES

| Asset | Prefix | Description |
|-------|--------|-------------|
| Skeleton | `SK_` | Bone hierarchy for a character rig |
| Skeletal Mesh | `SK_` / `SKM_` | 3D mesh bound to a skeleton |
| Animation Sequence | `AN_` or `A_` | A single animation clip (walk, idle) |
| Blend Space | `BS_` | Blends animations by float/vector parameters |
| Blend Space 1D | `BS1D_` | Blends along a single axis |
| Aim Offset | `AO_` | Head/body aiming blend space |
| Animation Montage | `AM_` | Layered, triggerable animation clip |
| Animation Blueprint | `ABP_` | Visual scripting for animation logic |
| Control Rig | `CR_` | Runtime procedural IK/pose system |
| Pose Asset | `PA_` | Single-frame pose for blending |
| Animation Composite | `AC_` | Multiple sequences played as one |

---

## 2. ANIMATION BLUEPRINT (ABP) STRUCTURE

### Two Graphs
1. **AnimGraph** — Outputs the final pose; runs every frame
2. **EventGraph** — Regular Blueprint logic; reads character state to drive AnimGraph variables

### Data Flow
```
EventGraph:
  Event Tick → Get Owning Character → Get Velocity → Vector Length → Set Speed
  Event Tick → Get Owning Pawn Movement → Is Falling → Set IsInAir

AnimGraph:
  Speed variable → Blend Space → State Machine → Output Pose
```

### Accessing the Owner
```
Get Owning Actor → Cast To BP_PlayerJediCharacter → Store in LocalCharRef
```
Cache this in BeginPlay! Do not cast every tick.

---

## 3. STATE MACHINES

**Purpose:** Transition between animation states based on conditions.

### Creating a State Machine
1. In AnimGraph: right-click → Add New State Machine
2. Name it (e.g., "LocomotionSM")
3. Double-click to open

### States
- Each state plays an animation or blend space
- Add states by right-clicking in the State Machine graph

### Transitions
- Drag from one state's border to another to create a transition
- Each transition has a **Transition Rule** — a Bool (true = allow transition)

### Common Locomotion State Machine
```
States: Idle, Walk, Run, Jump, Land, Fall

Transitions:
  Idle → Walk: Speed > 5.0
  Walk → Run: Speed > 250.0
  Run → Walk: Speed < 250.0
  Walk → Idle: Speed < 5.0 AND IsInAir == false
  Any State → Jump: IsInAir == true
  Jump → Land: IsInAir == false
  Land → Idle: (time-based or AnimNotify)
```

### State Machine for Dantooine Player
```
States:
  Idle
  Walk
  Run
  Jump_InAir
  Attack_Swing (montage slot)
  Block_Hold

Transitions:
  Idle → Walk: Speed > 5.0
  Walk → Run: Speed > 200.0
  * → Jump_InAir: IsInAir
  Jump_InAir → Walk: !IsInAir AND Speed > 5
  Jump_InAir → Idle: !IsInAir AND Speed < 5
```

---

## 4. BLEND SPACES

**Purpose:** Smoothly interpolate between animations along one or two axes.

### 1D Blend Space
- One axis: typically Speed (float)
- Animations at positions: 0 = Idle, 200 = Walk, 600 = Run

### 2D Blend Space
- Two axes: typically Speed (X) and Direction (Y)
- Positions: allows separate animations for moving forward, backward, strafing

### Creating via Content Browser
1. Right-click → Animation → Blend Space (1D or 2D)
2. Select the character's Skeleton
3. Name with `BS_` prefix
4. Add animation samples at positions on the graph

### Aim Offset (Pitch/Yaw)
- Special 2D Blend Space for head/body aiming
- X = Yaw (-90 to 90), Y = Pitch (-90 to 90)
- Add base pose at (0,0) and aim direction poses at extremes
- Apply over locomotion using a Layered Blend Per Bone node

---

## 5. ANIMATION MONTAGES

**Purpose:** Triggerable animation clips that can be played over the base animation, support blending by bone layer, and can play multiple sections.

### Creating a Montage
1. Right-click an Animation Sequence → Create Montage
2. Name with `AM_` prefix
3. Open to add Sections, configure Slots

### Slots
- `DefaultGroup.DefaultSlot` — default slot
- `UpperBody` / `FullBody` — common custom slot names
- Slots define where in the bone hierarchy the montage plays

### Sections
- Named segments of the montage (e.g., `Attack_Start`, `Attack_Loop`, `Attack_End`)
- Can have branching rules between sections

### Playing Montages in Blueprint
```
Play Anim Montage
  → Anim Montage: AM_Attack
  → In Root Motion Mode: Root Motion from Everything
  → Returns: Length (Float)

Stop Anim Montage
  → Anim Montage: AM_Attack (leave blank for "stop all")
  → Blend Out Time: 0.25
```

### Montage End Callback
```
On Montage Ended (from Anim Instance)
  → Bind event on BeginPlay
  → Check if Montage matches AM_Attack
  → Return to gameplay after attack completes
```

### AnimNotify in Montage
- Marks a point in time to trigger a gameplay event
- e.g., at frame 12 of swing animation: notify → spawn lightsaber damage trace

---

## 6. ANIMATION NOTIFIES

**Purpose:** Trigger events at specific frames within an animation.

### Notify Types
| Type | Use |
|------|-----|
| `AnimNotify` | One-shot event at a point in time |
| `AnimNotifyState` | Has Begin, Tick, End; spans a duration |
| `Play Sound` | Built-in — plays a sound at that frame |
| `Play Particle Effect` | Built-in — spawns Niagara at a socket |

### Custom Notify
1. In Montage timeline: right-click → Add Notify → New Notify
2. Name it (e.g., `AN_LightsaberSwing`)
3. In the Animation Blueprint:
   ```
   AnimGraph Event: AN_LightsaberSwing
     → Perform damage trace
     → Apply damage to hit actors
   ```

---

## 7. LAYERED BLENDING

### Layered Blend Per Bone
Blends two poses starting at a specific bone:
```
Full Body Locomotion pose → (Base)
Upper Body Attack pose → (Additive/Override)
→ Layered Blend Per Bone
  → Blend Poses [0]: Locomotion
  → Blend Poses [1]: Attack  
  → Branch Filter: {Bone: "spine_01", Blend Depth: 1}
→ Result: Upper body does attack, lower body continues walking
```

### Apply Additive
Adds an additive animation on top of base:
```
Base Pose (Walk)
Additive Pose (lean forward)
→ Apply Additive (Alpha: 0–1)
```

---

## 8. ROOT MOTION

**What it is:** Animation drives character movement instead of code. The root bone's movement in the clip is applied to the character capsule.

### Enable Root Motion
1. Open Animation Sequence
2. Details → Root Motion → Enable Root Motion: true
3. Root Motion Root Lock: set if needed

### Root Motion in Montages
- Set via `Root Motion Mode` when calling `Play Anim Montage`
- Options: `No Root Motion Extraction`, `Ignore Root Motion`, `Root Motion from Everything`

### When to Use Root Motion
- Attacks with specific step-in movement
- Knockback reactions
- Special ability animations
- Cinematic-quality transitions

---

## 9. INVERSE KINEMATICS (IK)

### What IK Is
- Procedural pose adjustment based on targets
- Used for: foot placement on slopes, hand weapon grip, look-at targets, ledge hang

### Two-Bone IK (Simple)
- Three bones: Root → Mid → Tip (e.g., Thigh → Calf → Foot)
- Define Effector (target position for Tip)
- Joint Target: controls bend direction (e.g., knee forward)

```
Two Bone IK
  → Root: "thigh_r"
  → Joint: "calf_r" (target: in front of knee)
  → Effector: Foot IK position (from IK bone target)
```

### Control Rig
- Full procedural animation system
- Used in Sequencer and Runtime for complex IK setups
- More powerful but complex — see Control Rig documentation

### Foot IK (Common Pattern)
```
Line Trace Down from foot location
→ Hit Location → Set Foot IK Target position
→ Two Bone IK → foot adapts to slope
Offset capsule Z to keep character on ground
```

---

## 10. ANIMATION BLUEPRINT VARIABLES (COMMON)

| Variable | Type | Set From | Used For |
|----------|------|----------|----------|
| `Speed` | Float | Character velocity magnitude | Walk/Run blend space |
| `Direction` | Float | Movement direction angle | Strafe blend |
| `IsInAir` | Bool | Is Falling (from movement comp) | Jump/Land states |
| `IsCrouching` | Bool | Character crouch state | Crouch animation |
| `IsAttacking` | Bool | Attack montage playing | Attack state |
| `IsBlocking` | Bool | Block input held | Block idle state |
| `AimPitch` | Float | Controller rotation pitch | Aim offset |
| `AimYaw` | Float | Character vs controller yaw delta | Aim offset |
| `IsAlive` | Bool | Health > 0 | Death state |

---

## 11. DANTOOINE ANIMATION BLUEPRINT REFERENCE

### ABP_PlayerJedi
**Skeleton:** SK_PlayerJedi (assign when mesh is imported)

**Variables needed:**
- Speed (Float)
- IsInAir (Bool)
- IsAttacking (Bool)
- IsBlocking (Bool)
- AimPitch (Float)

**AnimGraph structure:**
```
Blend Space 1D (BS_Jedi_Locomotion: Idle/Walk/Run based on Speed)
→ Slot Node "UpperBody.AttackSlot" (for attack montages)
→ Layered Blend Per Bone (merge upper/lower body)
→ Apply Aim Offset (AO_JediAim)
→ Output Pose
```

### ABP_RoamingNPC
**Skeleton:** SK_NPC_Student (assign when mesh is imported)

**Variables:**
- Speed (Float)
- IsTalking (Bool)

**AnimGraph:**
```
Blend Space 1D (BS_NPC_Walk based on Speed)
→ (optional) Additive Talk gesture when IsTalking
→ Output Pose
```

### ABP_SparringOpponent
**Skeleton:** SK_SparringOpponent (assign when mesh is imported)

**Variables:**
- Speed (Float)
- IsAttacking (Bool)
- E_SparringState (Enum for idle/attack/block/defeat)

**AnimGraph:**
```
State Machine (SparringSM)
  → Idle: idle animation
  → Approach: walk/run blend space
  → Attack: attack montage slot
  → Block: block hold animation
  → Defeat: defeat animation
```

---

## 12. CREATING ANIMATION BLUEPRINTS VIA exec_python

```python
import unreal
at = unreal.AssetToolsHelpers.get_asset_tools()

# Create an Animation Blueprint (skeleton assigned later when mesh is imported)
factory = unreal.AnimBlueprintFactory()
factory.set_editor_property("target_skeleton", None)  # None = no skeleton yet
factory.set_editor_property("blueprint_type", unreal.BlueprintType.BPTYPE_NORMAL)
asset = at.create_asset("ABP_PlayerJedi", "/Game/Dantooine/Animation/Player", unreal.AnimBlueprint, factory)
print("Created:", asset.get_path_name() if asset else "FAILED")
```

> After importing the skeletal mesh, open ABP and assign the correct skeleton in Class Defaults.

---

## 13. ANIMATION PERFORMANCE TIPS

| Optimization | Effect |
|---|---|
| `Update Rate Optimizations` in mesh | Reduce tick rate for distant characters |
| `Component Use Fixed Skel Bounds` | Skip tight bounds recalculation each frame |
| Use `Thread Safe Update Animation` | Move expensive calculations off game thread |
| Limit animation tick on invisible actors | Don't animate if camera can't see |
| Disable Foot IK for distant NPCs | Expensive; only needed up close |
| Merge additive layers with blending | Fewer blend nodes = faster |
