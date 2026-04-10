# Animation System — Complete Reference
> Source: Blueprints Visual Scripting for UE5 (Marcos Romero), Mastering Technical Art in UE (Greg Penninck)
> Last Updated: 2026-04-10 | UE 5.6

---

## 1. Animation Asset Types

| Asset | Prefix | Description |
|-------|--------|-------------|
| **Skeleton** | `SK_` | Bone hierarchy definition; shared between meshes |
| **Skeletal Mesh** | `SK_` | 3D mesh bound to a skeleton |
| **Animation Sequence** | `AN_` | Single animation clip (walk, idle, attack) |
| **Animation Blueprint** | `ABP_` | Visual logic driving animation state |
| **Blend Space 1D** | `BS_` | Blends animations by one float parameter |
| **Blend Space 2D** | `BS_` | Blends animations by two float parameters |
| **Animation Montage** | `AM_` | On-demand animation with notify events |
| **Aim Offset** | `AO_` | Additive layer for aiming direction |
| **AnimNotify** | — | Instant event at specific frame |
| **AnimNotify State** | — | Begin/End event over a frame range |
| **IK Rig** | — | Inverse kinematics rig asset |
| **Control Rig** | — | Procedural bone control system |
| **Physics Asset** | `PA_` | Ragdoll and physical animation setup |

---

## 2. Animation Blueprint Structure

An Animation Blueprint has **two graphs:**

### Graph 1: Event Graph
- Standard Blueprint graph (same as any Actor Blueprint)
- Runs every animation update frame
- **Purpose**: Read data from the owning Pawn/Character → Update animation variables

### Graph 2: AnimGraph
- Specialized graph for **combining poses**
- Only runs animation pose-blending operations
- Final node is always `Output Pose`
- **Cannot have game logic** — only animation blending

### Data Flow
```
Character BP (game state) ──reads──→ ABP Event Graph ──updates──→ ABP Variables
                                                                        │
                                                                        ↓
                                    AnimGraph ──uses variables──→ Blend/State Machine → Output Pose
                                                                                              │
                                                                                              ↓
                                                                                    Skeletal Mesh
```

---

## 3. Standard Event Graph Pattern

```
Event Blueprint Update Animation (DeltaTimeX: float)
  → Try Get Pawn Owner
  → Is Valid? (Protect against null!)
    → Cast To BP_PlayerJediCharacter
      Cast Succeeded:
        → Get Velocity → VectorLength → Set Speed
        → GetMovementComponent → Is Falling → Set IsInAir
        → IsCrouched → Set IsCrouching
        → GetCharacterMovement → MaxWalkSpeed → Set MaxWalkSpeed
        → Calculate Direction (Velocity, ActorRotation) → Set Direction
        → Get Is Accelerating → Vector Length > 0 → Set IsAccelerating
```

### Standard Animation Variables

| Variable | Type | How to Get |
|----------|------|-----------|
| `Speed` | Float | `GetVelocity` → `VectorLength` |
| `IsInAir` | Bool | `GetMovementComponent` → `IsFalling` |
| `IsCrouching` | Bool | `IsCrouched` |
| `Direction` | Float | `CalculateDirection(Velocity, ActorRotation)` |
| `IsAccelerating` | Bool | `GetCurrentAcceleration` → `VectorLength > 0` |
| `HasWeapon` | Bool | From character equipment state |
| `IsAttacking` | Bool | From character combat state |
| `IsBlocking` | Bool | From character combat state |
| `Health` | Float | From character health variable |

---

## 4. State Machine

**Organizes animation into discrete states with transition rules.**

### Creating a State Machine
1. In AnimGraph: right-click → **Add New State Machine**
2. Name it (e.g., `LocomotionStateMachine`)
3. Double-click to open
4. Drag from `Entry` node to create first state

### States
- Each state has its own mini-pose graph
- The graph outputs a **pose** (animation sequence, blend space, or nested state machine)
- Name states clearly: `Idle`, `Moving`, `Jumping`, `Falling`, `Landing`, `Attack`, `Block`

### Transitions
- Arrow connecting two states
- Double-click the arrow to open the **Transition Rule** graph
- Transition Rule outputs a single **Boolean** — when True, the transition fires
- Add a `Transition Result` node and connect the bool condition to it

### Example Transition Rules

**Idle → Moving:**
```
Get Speed (float var from Event Graph) → Greater Than (0.1) → Result
```

**Moving → Idle:**
```
Get Speed → Less Than Or Equal (0.1) → Result
```

**Any → Jumping:**
```
Get IsInAir → Result
```

**Jumping → Falling:**
```
Get Velocity → Break Vector → Z → Less Than (-10.0) → Result
```

**Falling → Landing:**
```
Get IsInAir → NOT → Result
```

### Locomotion State Machine (Full Pattern)
```
Entry → Idle
  Idle → Moving: Speed > 0.1
  Moving → Idle: Speed ≤ 0.1
  Idle → Jumping: IsInAir
  Moving → Jumping: IsInAir
  Jumping → Falling: Velocity.Z < -10
  Falling → Landing: NOT IsInAir
  Landing → Idle: Landing anim finished (Get Relevant Anim Time Remaining ≤ 0.1)
```

### Combat State Machine (Dantooine)
```
Entry → Unarmed
  Unarmed → Armed: HasLightsaber
  Armed → Attacking: IsAttacking
  Attacking → Armed: Montage finished OR not IsAttacking
  Armed → Blocking: IsBlocking
  Blocking → Armed: NOT IsBlocking
```

---

## 5. Blend Spaces

**Blend multiple animations based on float parameters.**

### 1D Blend Space
- One axis (e.g., `Speed` 0–600)
- Sample points: 0 = Idle, 200 = Walk, 600 = Run
- UE interpolates between samples based on current Speed

### 2D Blend Space (AimOffset or Strafe)
- Two axes (e.g., `Speed` and `Direction`)
- Grid of animation samples:
  - (0, 0) = Idle
  - (600, 0) = Run Forward
  - (600, 90) = Run Right
  - (600, -90) = Run Left
  - (600, 180) = Run Backward

### Using a Blend Space in AnimGraph
```
[BlendSpace Asset node]
  Speed → (float from Event Graph variable)
  Direction → (float from Event Graph variable)
  → Outputs blended Pose
```

---

## 6. Animation Montages

**Plays animations on-demand, outside state machine control.**

### Use Cases
- Attack animations triggered by input
- Hit reactions
- Emotes
- Ability activations (Force Push, lightsaber ignite, workbench interaction)
- Cutscene-style interrupted sequences

### Playing a Montage (From Character Blueprint)
```
Input Action IA_Attack → (Pressed)
  Play Anim Montage:
    Anim Montage: AM_Attack_Slash
    In Play Rate: 1.0
    Starting Section Name: "Start"
  → Return Value: Montage Length (float)
```

### Stopping a Montage
```
Stop Anim Montage:
  Anim Montage: AM_Attack_Slash (or None = stop ALL montages)
  Blend Out Time: 0.25
```

### Montage Sections
- Named regions within a montage for looping or branching
- Jump between sections:
```
Montage Jump To Section:
  Section Name: "Loop"
  For Montage: AM_ComboAttack
```

### Setting Up Montage in AnimGraph
```
[State Machine → Locomotion] → [Slot 'DefaultSlot'] → Output Pose
     OR
[Locomotion] → [Slot 'UpperBody'] → Output Pose
  └── Leg layer from locomotion continues unchanged
```

### Anim Slots
| Slot | Use |
|------|-----|
| `DefaultSlot` | Full-body override |
| `UpperBody` | Upper body only (while legs locomote) |
| `FullBody` | Explicit full-body |
| Custom | Specific limb groups |

---

## 7. AnimNotifies

**Events that fire at specific frames of an animation.**

### Types
| Type | Description |
|------|-------------|
| `AnimNotify` | Fires a single event at one frame |
| `AnimNotifyState` | Begin/End events over a frame range |

### Adding to an Animation
1. Open Animation Sequence or Montage
2. In the Notifies track: right-click → Add Notify → or Add Notify State
3. Name it (e.g., `AN_HitCheck`, `AN_FootstepLeft`)

### Receiving in Character Blueprint
```
Event AN_HitCheck
  → Do hit detection (LineTrace from weapon tip)
  → Apply damage to overlapping enemies

Event AN_FootstepLeft
  → Play footstep sound (foot-surface type based)
  → Make Noise (for AI hearing)
```

### Common Notify Names (Dantooine)
```
AN_AttackHit          → Detect lightsaber hit
AN_FootstepLeft       → Left foot sound + noise
AN_FootstepRight      → Right foot sound + noise
AN_WorkbenchAssemble  → Trigger assembly VFX/sound
AN_DrawSaber          → Lightsaber activation VFX
AN_SheathSaber        → Lightsaber deactivation
```

---

## 8. Aim Offset

**Additive layer for aiming direction (gun or saber aiming).**

### Setup
1. Create Aim Offset asset
2. X axis: Yaw (−180 to 180)
3. Y axis: Pitch (−90 to 90)
4. Add animation samples for 9 key positions (Center, Up, Down, Left, Right, diagonals)

### In AnimGraph
```
[Locomotion State Machine] → [Apply Additive] → Output Pose
[Aim Offset (AimYaw, AimPitch)] ──────────────────↑
```

### Getting Aim Angles (In Event Graph)
```
Get Control Rotation → Yaw → minus → Get Actor Rotation → Yaw → NormalizeAngle → Set AimYaw
Same for Pitch → Set AimPitch
```

---

## 9. Inverse Kinematics (IK)

### Two Bone IK
- Used for: arms reaching for weapons, feet adapting to ground slope
- Requires: Root bone, Joint bone, End Effector bone
- `Effector Location` = where the end (hand/foot) should reach
- `Joint Target Location` = hint for which direction the joint bends (knee/elbow)

### Foot IK Pattern
```
Event Tick:
  Line Trace down from Left Foot bone → Get Hit Location + Normal
  Line Trace down from Right Foot bone → Get Hit Location + Normal
  
In AnimGraph:
  Two Bone IK (Left Foot):
    Effector Location: LeftFootIK_Target (variable from Event Graph)
  Two Bone IK (Right Foot):
    Effector Location: RightFootIK_Target
  Pelvis offset = average of both foot offsets (prevent floating)
```

### Hand IK (Weapon Grip)
```
Two Bone IK for Left Hand:
  Effector: LeftHandSocket on weapon (maintains grip when weapon moves)
  Result: Left hand stays on weapon regardless of locomotion pose
```

---

## 10. Root Motion

**Animation drives the character's actual movement (not CharacterMovement).**

### When to Use Root Motion
- Attack animations with steps (forward strike, dodge roll)
- Ensures animation and movement are perfectly synced

### Setup
1. In Animation Sequence: Enable `Force Root Lock` or enable Root Motion
2. In Character Movement Component: Enable `Allow Root Motion` on the anim montage
3. Disable regular `Add Movement Input` during the montage

### Warning
- Root motion and CharacterMovement can conflict
- Only use root motion for specific montages (attacks, roll), not locomotion

---

## 11. Animation Best Practices (From Books)

### DO:
1. **Cache the pawn reference in Event Begin Play** — set a variable once; don't `Try Get Pawn Owner` every tick
2. **Always IsValid check** before reading from the cached pawn — prevents crashes
3. **Keep AnimGraph clean** — no game logic; only blending operations
4. **Use blend times 0.1–0.3s** — fast enough to feel responsive, not robotic
5. **Use AnimNotifies** for gameplay events (hit detection, sounds) — exact-frame precision
6. **Assign skeleton when importing mesh** — Animation Blueprints REQUIRE a skeleton

### DON'T:
1. **Don't read game variables directly in AnimGraph** — always pass through Event Graph variables
2. **Don't use `Try Get Pawn Owner` every update frame** — expensive; cache it
3. **Don't mix root motion and CharacterMovement locomotion** — pick one
4. **Don't leave ABP without a skeleton** — it will crash or not compile

### Skeleton Assignment (Critical for Dantooine)
```
When you import SK_PlayerJedi:
  1. Assign to ABP_PlayerJedi: Open ABP → Class Settings → Target Skeleton → SK_PlayerJedi_Skeleton
  2. Open each Animation Sequence and verify it uses the same skeleton
  3. Open State Machine → set each state's animation to use the correct AnimSequence/BlendSpace
```

---

## 12. Dantooine Animation Blueprint Setup

### ABP_PlayerJedi
```
Skeleton: SK_PlayerJedi_Skeleton (assign after mesh import)

Event Graph Variables:
  Speed: Float       → from GetVelocity + VectorLength
  IsInAir: Bool      → from IsFalling
  IsAttacking: Bool  → from character combat state
  IsBlocking: Bool   → from character combat state
  HasLightsaber: Bool → from character equipment

AnimGraph:
  LocomotionSM → DefaultSlot (for attack montages) → Output Pose
```

### ABP_RoamingNPC
```
Skeleton: SK_NPC_Student_A_Skeleton (or shared NPC skeleton)

Event Graph Variables:
  Speed: Float
  IsInAir: Bool
  IsTalking: Bool → from Blackboard via AIController

AnimGraph:
  LocomotionSM → DefaultSlot → Output Pose
```

### ABP_SparringOpponent
```
Skeleton: SK_SparringOpponent_Skeleton

Event Graph Variables:
  Speed: Float
  IsAttacking: Bool → from AI state / blackboard
  IsInAir: Bool

AnimGraph:
  CombatSM → DefaultSlot → Output Pose
```
