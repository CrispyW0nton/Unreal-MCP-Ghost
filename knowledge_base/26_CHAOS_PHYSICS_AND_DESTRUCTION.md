# Chaos Physics and Destruction
> Source: project notes, Epic Chaos/Physics documentation, technical-art performance notes
> Last Updated: 2026-06-07 | UE 5.6

---

## Overview

Chaos is Unreal's physics simulation system. For destruction, it uses Geometry
Collections, fracture workflows, fields, events, caching, and Niagara
integration. Treat destruction as authored content plus runtime policy: fracture
setup, thresholds, collision, cache strategy, event response, and performance
budget all matter.

Use physics simulation where it improves the game feel. For deterministic
gameplay, networked play, or cinematics, prefer constrained simulations, cached
destruction, or server-authored state rather than uncontrolled chaos.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| Geometry Collection | Fractured destruction asset built from one or more meshes. |
| `AChaosSolverActor` | Solver actor for Chaos simulation control. |
| `UChaosEventListenerComponent` | Reads collision, break, trailing, and removal events. |
| Physics Field assets/components | Spatial forces or state changes applied to simulation. |
| Cache Manager / cache assets | Records and replays destruction transforms/events. |
| `UPrimitiveComponent` | Common physics/collision root for simulated components. |
| Niagara Chaos events | VFX response to collision/break events. |

## Common Pitfalls

- Fracturing high-poly meshes without proxy/collision planning.
- Letting all fractured pieces simulate forever.
- Using live destruction for cinematic beats that should be cached.
- Forgetting network implications: physics does not become multiplayer-safe by
  default.
- Missing collision channel setup for gameplay traces and projectiles.
- Spawning Niagara effects per fragment without event filtering or culling.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Inspect physics assets | `scan_project_assets`, physics/procedural tools |
| Create a Chaos solver | `chaos_create_solver_actor` |
| Configure solver events/budget | `chaos_configure_solver_actor` |
| Inspect destructible setup | `chaos_inspect_geometry_collection` |
| Configure Geometry Collection runtime policy | `chaos_configure_geometry_collection` |
| Configure cloth simulation | `chaos_configure_cloth_component` |
| Configure Blueprint actors | Blueprint/component/property tools |
| Attach VFX response | Niagara tools and Blueprint graph tools |
| Validate runtime | PIE, logs, viewport screenshots, performance snapshots |
| Record evidence | execution journal and vertical slice report tools |

## MCP Chaos and Cloth Tools

Use these tools after Geometry Collection fracture assets or cloth skeletal
meshes exist. The B.10 tool surface focuses on runtime-ready configuration:
solver actors, destruction event generation, Geometry Collection thresholds, and
cloth component simulation toggles.

| Tool | Use |
| --- | --- |
| `chaos_create_solver_actor` | Spawn a Chaos Solver actor and optionally make it the current world solver. |
| `chaos_configure_solver_actor` | Tune solver iteration counts, floor behavior, generated collision/break/trailing data, and destruction throttling. |
| `chaos_inspect_geometry_collection` | Inspect a Geometry Collection actor/component or asset path for rest collection, solver, thresholds, and event flags. |
| `chaos_configure_geometry_collection` | Set simulate physics, gravity, clustering, damage thresholds, break/collision notifications, and solver assignment. |
| `chaos_configure_cloth_component` | Suspend/resume cloth, enable editor updates, set cloth scale/blend, and force teleport/reset/recreate operations. |

Recommended MCP flow:

1. Create or locate a solver with `chaos_create_solver_actor`.
2. Enable only the event streams you need with `chaos_configure_solver_actor`;
   break data is useful for dust/VFX, but all streams can be expensive.
3. Inspect the Geometry Collection with `chaos_inspect_geometry_collection`.
4. Set thresholds and event flags with `chaos_configure_geometry_collection`.
5. For cloth actors, use `chaos_configure_cloth_component` to update editor
   simulation, reset teleport state, or temporarily suspend simulation.

## Working Example

Goal: make a destructible barrier that breaks once and spawns dust.

1. Author `GC_Barrier_A` from static mesh pieces with simple collision.
2. Set damage thresholds so the barrier survives incidental bumps.
3. Place a Blueprint wrapper `BP_DestructibleBarrier` with the Geometry
   Collection component.
4. Add a field or damage impulse when the server validates an explosion.
5. Listen for a filtered break event and spawn `NS_BarrierDust`.
6. Disable or sleep small fragments after a short delay.
7. In multiplayer, replicate the gameplay result and keep cosmetics local or
   state-driven.

## Validation Checklist

- Collision, mass, and damage thresholds are authored deliberately.
- Fragments sleep, cache, or cull within a performance budget.
- Niagara event response is filtered.
- Networked gameplay uses server authority for break state.
- PIE evidence includes frame/log behavior during the destruction event.

## References

- Epic: Physics in Unreal Engine -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/physics-in-unreal-engine?application_version=5.6
- Epic: Chaos API -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Runtime/ChaosSolverEngine/Chaos
