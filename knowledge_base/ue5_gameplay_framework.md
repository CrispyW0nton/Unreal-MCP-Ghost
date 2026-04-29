# UE5 Gameplay Framework Reference
> Sources: Li, Marques/Sherry/Pereira/Fozi, Sapio; synthesized for Unreal-MCP-Ghost.
> Updated: 2026-04-29

## Class Hierarchy

`UObject` is the reflection/GC root. `AActor` is the base placeable world object. `APawn` adds possession. `ACharacter` adds a capsule, skeletal mesh, and `CharacterMovementComponent`. Controllers separate decision/input from bodies: `APlayerController` for human input and client UI, `AAIController` for behavior-tree/perception driven pawns.

Project rules usually live in `AGameModeBase` (server only), replicated match state in `AGameStateBase`, per-player replicated data in `APlayerState`, and cross-level local data in `UGameInstance`.

## Common Patterns

- Use `Actor` for props, triggers, managers, projectiles, and interactable world objects.
- Use `Character` for biped player/NPC/enemy classes that need walking, jumping, collision, and skeletal animation.
- Put player input and HUD creation in `PlayerController` when the logic should survive pawn changes.
- Put authoritative match rules in `GameModeBase`; never rely on it for client-side UI state.
- Put shared network-visible state in `GameStateBase`; put local persistence and menu flow in `GameInstance`.
- Prefer components for reusable health, inventory, interaction, and sensor logic.

## MCP Audit Notes

- Verify framework setup by querying current world settings, default pawn, player controller, game state, and game instance through `exec_python`.
- For placed actors, use `get_actors_in_level` and then `get_actor_properties` for notable class defaults.
- For Blueprint classes, inspect parent class, components, variables, and graphs before assuming behavior.

## Lab Checklist

- Identify active map and world GameMode override.
- Confirm default pawn/character class and controller class.
- Confirm whether the player pawn is placed, auto-possessed, or spawned by GameMode.
- Look for manager actors that duplicate GameMode/GameInstance responsibilities.
- Flag Tick-heavy actors that could be event-driven.
