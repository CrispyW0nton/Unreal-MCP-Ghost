# GAM 115 — Lab-4D: Sphere Tracing & Active Actor Detection
**Course:** GAM_115_OL1 — Elements of Scripting  
**Academy of Art University**  
**Module Focus:** Active actor detection using Sphere Traces, Arrays, Loops, and Vector math

---

## Overview

In previous modules, actor detection was passive — using collision/overlap events that wait for something to come to you. Lab-4D introduces **active detection** using Sphere Traces, where you proactively search for actors at any moment regardless of whether they've entered a trigger volume.

**Practical Example:** A grenade that explodes and actively searches for all actors in its vicinity to apply damage — it doesn't wait for actors to overlap it, it reaches out and finds them.

---

## Module Learning Objectives

1. Implement simple Sphere Traces in Blueprint to find nearby actors
2. Use the **For Each Loop** node to repeat a sequence of nodes for each actor found
3. Exploit vector math to create more interesting and directional Sphere Traces

---

## 1. Check for Nearby Actor — Sphere Trace Basics

**Concept:** Replace passive collision events with an active Sphere Trace.

- Collision/Hit events are **passive** — they sit and wait for another actor to come to them
- Sphere Traces are **active** — at any given moment you can proactively search for actors in a radius

**How it works:**
- A **Sphere Trace** creates a sphere volume and checks if any actor intersects it
- Returns a **boolean** (true/false) for whether anything was hit
- Also returns a **Hit Result struct** containing detailed data about what was found

**Key Blueprint Node:** `Sphere Trace By Channel`
- **Start** pin — where the sphere begins
- **End** pin — where the sphere ends (for a radius check, Start and End can be the same location)
- **Radius** pin — size of the sphere
- **Return Value** — boolean: did it hit anything?
- **Out Hit** — Hit Result struct with full data about the hit

---

## 2. Affect Nearby Actor — Using the Hit Result

**Concept:** Once the Sphere Trace finds an actor, use the Hit Result to get a reference to it and perform actions on it.

**Key Points:**
- The Sphere Trace node doesn't just return true/false — it returns a **laundry list of data** about what it found
- This data is packed into a **struct** (the Out Hit pin)
- To access individual pieces of data (like the actor reference), you must **Break** the struct

**Blueprint Pattern:**
```
Sphere Trace By Channel
  └─ Out Hit (struct) → Break Hit Result
                            └─ Hit Actor → [perform actions on this actor]
```

**Critical node:** `Break Hit Result`
- Drag off the **Out Hit** pin → Break Hit Result
- Exposes individual fields including **Hit Actor** (the actual actor reference you need)
- Also exposes: Impact Point, Impact Normal, Distance, Physical Material, etc.

---

## 3. Get All Nearby Actors — Multi Sphere Trace

**Concept:** Instead of stopping at the first hit, find ALL actors within the sphere.

**Key difference:**
- `Sphere Trace By Channel` — stops at first hit, returns one Hit Result
- `Multi Sphere Trace By Channel` — keeps looking, returns an **Array** of all Hit Results

**What is an Array?**
- A collection of multiple instances of the same type
- Cannot act on an array directly — must iterate through it with a loop

**Blueprint Pattern:**
```
Multi Sphere Trace By Channel
  └─ Out Hits (array of Hit Results) → For Each Loop
                                           └─ Array Element → Break Hit Result
                                                                  └─ Hit Actor → [actions]
```

**Visualization tip:** The Multi Sphere Trace node has debug options to draw the sphere in the viewport so you can see exactly where it's checking.

---

## 4. Affect All Nearby Actors — For Each Loop

**Concept:** Iterate through the array of actors returned by Multi Sphere Trace and perform an action on each one.

**Key Node:** `For Each Loop`
- **Array** input — connect the Out Hits array from Multi Sphere Trace
- **Array Element** output — gives you each Hit Result one at a time, each loop iteration
- **Array Index** output — the current index number (0, 1, 2...)
- **Loop Body** exec — fires once per element
- **Completed** exec — fires when all elements have been processed

**Full Blueprint Pattern:**
```
[Event/Trigger]
  └─ Multi Sphere Trace By Channel (Start, End, Radius)
       └─ Out Hits → For Each Loop
                         Loop Body → Break Hit Result
                                         Hit Actor → Apply Damage / Call Function / etc.
                         Completed → [anything to do after all actors processed]
```

---

## 5. Repeated Sphere Trace — Automatic Polling with Delay

**Concept:** Run the sphere trace automatically on a timer instead of in response to a keypress.

**Key Pattern:** Use a **Delay** node connected back through the loop's **Completed** pin to create a repeating cycle.

**Blueprint Pattern:**
```
Event BeginPlay
  └─ [Start of loop]
       └─ Multi Sphere Trace By Channel
            └─ Out Hits → For Each Loop
                              Loop Body → [actions on each actor]
                              Completed → Delay (Duration: 1.0)
                                             └─ [connect back to Sphere Trace] ← creates the repeat
```

**Critical wiring note:** 
- Connect the **Delay** node to the **Completed** pin of the For Each Loop (NOT the Loop Body)
- This ensures the delay only triggers after ALL actors have been processed
- The delay's output then triggers the next sphere trace, creating the repeating cycle

---

## 6. Look for Actors Between Two Locations

**Concept:** Instead of a sphere around a single point, trace between two different locations to find actors along a path.

**How it works:**
- The standard Sphere Trace takes a **Start** and **End** location
- By default you may have used the same location for both (radius around a point)
- Setting **different** Start and End points makes the sphere sweep along a line between them
- This is useful for checking if anything is between two actors, along a hallway, etc.

**Blueprint Pattern:**
```
Get Actor Location (Actor A) → Start pin ─┐
                                           ├─ Sphere Trace By Channel
Get Actor Location (Actor B) → End pin  ──┘
```

---

## 7. Sphere Trace Forward — Vector Math for Directional Traces

**Concept:** Use the player's forward vector to cast the sphere trace in the direction the player is facing.

**Core Idea:**
- Take the player's current world location as the **Start**
- Add an offset along the player's **forward vector** to get the **End**
- This makes the trace point in whichever direction the player is facing

**Key Nodes:**
- `Get Actor Location` — player's current position (Start)
- `Get Actor Forward Vector` — the unit direction vector the actor is facing
- `Vector * Float` (multiply) — scale the forward vector by a distance (e.g., 500 units)
- `Vector + Vector` (add) — add the scaled forward vector to the player location → gives you the End point

**Blueprint Pattern:**
```
Get Actor Location ──────────────────────────────────────── Start pin ─┐
                                                                        ├─ Sphere Trace
Get Actor Location → [+] → End pin ──────────────────────────────────┘
                     ↑
Get Actor Forward Vector → [×] → (scale by distance, e.g. 500)
```

**Full wiring:**
```
Self (Player) → Get Actor Location → [Vector + Vector] → End
                                            ↑
Self (Player) → Get Actor Forward Vector → [Vector × Float (500)] ──┘
```

---

## 8. Tracking the Player — Find Look At Rotation

**Concept:** Make an actor constantly rotate to face the player using `Find Look at Rotation`.

**Use case:** An enemy or object that wants to fire sphere traces directly at the player needs to first rotate toward the player.

**Key Node:** `Find Look at Rotation`
- **Start** — location of the actor doing the looking
- **Target** — location of the thing to look at
- **Return Value** — a Rotator pointing from Start toward Target

**Blueprint Pattern:**
```
Event Tick
  └─ Find Look at Rotation
       Start  ← Get Actor Location (self)
       Target ← Get Actor Location (player)
       Return Value → Set Actor Rotation (self)
```

**Result:** Every tick, the actor recalculates the rotation needed to face the player and applies it, creating continuous tracking.

**Combined with Sphere Trace Forward:**
Once the actor is facing the player, a forward sphere trace will naturally point directly at them:
```
Event Tick
  └─ Find Look at Rotation → Set Actor Rotation
  └─ Sphere Trace (forward) → hits player if in range
```

---

## Key Nodes Summary — Lab-4D

| Node | Purpose | Key Pins |
|---|---|---|
| `Sphere Trace By Channel` | Find first actor in sphere | Start, End, Radius → Return Value (bool), Out Hit |
| `Multi Sphere Trace By Channel` | Find ALL actors in sphere | Start, End, Radius → Out Hits (array) |
| `Break Hit Result` | Unpack the hit struct | Out Hit → Hit Actor, Impact Point, Distance, etc. |
| `For Each Loop` | Iterate over array | Array → Loop Body (exec per element), Completed |
| `Delay` | Wait N seconds | Duration → [next node after delay] |
| `Get Actor Forward Vector` | Direction actor is facing | → Forward Vector (unit vector) |
| `Vector × Float` | Scale a vector by distance | → Scaled vector |
| `Vector + Vector` | Offset a location | → New location |
| `Find Look at Rotation` | Rotation to face a target | Start, Target → Rotator |
| `Set Actor Rotation` | Apply rotation to actor | New Rotation |

---

## Common Patterns Quick Reference

### Pattern 1: Simple "Is anything nearby?" check
```
[Input Event] → Sphere Trace By Channel (self location, self location, radius 200)
                  Return Value (bool) → Branch → True → [do something]
```

### Pattern 2: Do something TO the nearby actor
```
Sphere Trace → Out Hit → Break Hit Result → Hit Actor → [Cast / Apply Damage / Call Function]
```

### Pattern 3: Do something to ALL nearby actors
```
Multi Sphere Trace → Out Hits → For Each Loop → Array Element → Break Hit Result → Hit Actor → [actions]
```

### Pattern 4: Repeat every second automatically
```
Event BeginPlay → Multi Sphere Trace → For Each Loop → [actions]
                                            Completed → Delay (1.0) → [back to Sphere Trace]
```

### Pattern 5: Trace in the direction you're facing
```
Get Actor Location → Start
Get Actor Location + (Get Actor Forward Vector × 500) → End
→ Sphere Trace By Channel
```

### Pattern 6: Track and face the player every frame
```
Event Tick → Find Look at Rotation (self loc, player loc) → Set Actor Rotation (self)
```

---

## Notes on Passive vs Active Detection

| | Passive (Overlap/Hit Events) | Active (Sphere Trace) |
|---|---|---|
| **Trigger** | Waits for another actor to enter | You call it whenever you want |
| **Best for** | Doors, pickups, triggers | Grenades, enemy awareness, AoE attacks |
| **Control** | Reacts to the world | Reaches out to query the world |
| **Multiple hits** | One event per overlap | Multi Trace returns all at once |
| **Performance** | Very cheap when idle | Costs a raycast per call — use wisely |

---

*Source: GAM_115_OL1 Elements of Scripting — Lab-4D Course Materials, Academy of Art University, 2026*
