# UE5 AI And Navigation Reference
> Sources: Sapio, Li, Marques/Sherry/Pereira/Fozi; synthesized for Unreal-MCP-Ghost.
> Updated: 2026-04-29

## Architecture

AI is usually split into a body (`Pawn`/`Character`), a brain (`AIController`), memory (`Blackboard`), decision flow (`BehaviorTree`), spatial reasoning (`NavMesh` and optionally EQS), and sensing (`AIPerception` or older `PawnSensing`).

## Navigation

AI movement requires a `NavMeshBoundsVolume` covering the playable area and a movement-capable pawn. Character-based AI normally uses `CharacterMovementComponent`. Always verify the navmesh covers the target locations and that the pawn capsule fits the agent settings.

## Behavior Tree Pattern

Use a `Selector` for priority choices, `Sequence` for ordered required steps, decorators for conditions, services for periodic blackboard updates, and tasks for small actions. Blackboard keys should be the single source of truth for target actor, patrol location, alert state, and combat state.

## Perception

Use `AIPerceptionComponent` for modern sight/hearing/damage sensing. Write sensed actors and locations to Blackboard keys, and let the Behavior Tree react. Use EQS when the AI needs "best place" choices such as cover, flank, or attack positions.

## MCP Notes

- Useful tools include `create_behavior_tree`, `create_blackboard`, `set_behavior_tree_blackboard`, `setup_navmesh`, AI controller Blueprint graph inspection, and `exec_python` for asset registry checks.
- Behavior Tree graph editing is still limited/manual; document BT assets and linked blackboards even when node-level BT graph extraction is unavailable.
- Runtime-spawned AI must call `SpawnDefaultController` or be configured with auto possess AI.

## Audit Checklist

- List AI characters, AI controllers, BT/BB assets, nav volumes, perception components, EQS assets, and patrol/target actors.
- Flag AI pawns without controller classes, missing navmesh, missing blackboard links, or BT assets with no run call.
