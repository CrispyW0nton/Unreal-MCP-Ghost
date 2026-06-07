# Mass Entity and StateTree
> Source: project notes, Epic Mass/StateTree/Smart Objects documentation, Sapio AI study guide
> Last Updated: 2026-06-07 | UE 5.6+

---

## Overview

MassEntity is Unreal's data-oriented framework for high-count gameplay entities.
StateTree is a hierarchical state-machine system that can drive Actors, Smart
Objects, and Mass behavior. Together, they are useful when traditional
Actor-per-agent logic becomes too expensive or when AI needs clean state logic
outside a full Behavior Tree.

Behavior Trees remain a good fit for many character AI tasks. Use Mass when
scale and data-oriented processing matter; use StateTree when state, transitions,
evaluators, and tasks should stay inspectable and performant.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| Entity | Runtime id associated with a fragment composition. |
| Fragment | Atomic data unit such as transform, velocity, or LOD state. |
| Tag | Data-less fragment used as a state marker. |
| Archetype | Group of entities with the same fragment composition. |
| Processor | Stateless logic that queries and processes fragments. |
| `UMassEntityConfigAsset` | Editor asset describing traits for spawned entities. |
| StateTree asset | Hierarchical state logic with tasks, evaluators, and transitions. |
| Smart Object assets/components | Reservable world interactions for AI or players. |

## Common Pitfalls

- Using Mass for a handful of complex hero actors where standard Actors are
  easier to inspect and debug.
- Modifying entity composition directly during processing instead of using a
  command buffer.
- Treating fragments as behavior containers; fragments should be data.
- Creating StateTrees with vague transitions that are harder to debug than a
  Behavior Tree.
- Forgetting representation LOD and actor spawning costs in Mass Gameplay.
- Omitting Smart Object reservation rules, causing multiple agents to claim the
  same interaction.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Onboard AI work | `get_onboarding_context("ai")`, `get_onboarding_context("mass")` |
| Inspect project assets | `scan_project_assets` for StateTree, Mass, and Blueprint assets |
| Create supporting BT/BB/EQS | AI MCP tools for classic AI slices |
| Build actor wrappers | Blueprint/component tools where Mass needs placed authoring helpers |
| Verify runtime | PIE launch/log tools and gameplay debugger snapshots |

## Working Example

Goal: create ambient crowd agents with a StateTree idle/wander loop.

1. Define fragments for transform, desired speed, current activity, and LOD.
2. Create a Mass entity config with movement, representation, and StateTree
   traits.
3. Author `ST_CrowdAmbient` with states: Idle, WalkToPoint, UseSmartObject,
   ExitArea.
4. Add Smart Objects for benches, vending machines, or workstations with clear
   reservation behavior.
5. Spawn a small test population first, then scale counts while watching
   representation and processor timing.
6. Capture PIE logs and debug snapshots before increasing density.

## Validation Checklist

- Actor AI and Mass AI responsibilities are separated.
- Fragments are data-only; processors own logic.
- StateTree transitions have readable conditions and fail paths.
- Smart Objects are reservable and release correctly.
- Performance evidence exists at target population counts.

## References

- Epic: MassEntity Overview -
  https://dev.epicgames.com/documentation/unreal-engine/overview-of-mass-entity-in-unreal-engine
- Epic: MassGameplay Overview -
  https://dev.epicgames.com/documentation/unreal-engine/overview-of-mass-gameplay-in-unreal-engine
- Epic: StateTree Quick Start -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/statetree-quick-start-guide?application_version=5.6
- Epic: Smart Objects Quick Start -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/smart-objects-in-unreal-engine---quick-start?application_version=5.6
