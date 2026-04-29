# UE5 Collision And Physics Reference
> Sources: Li, Marques/Sherry/Pereira/Fozi; synthesized for Unreal-MCP-Ghost.
> Updated: 2026-04-29

## Collision Model

Collision is configured through object types, trace channels, collision profiles, responses, and primitive component settings. Blocking prevents movement through geometry; overlap generates events without blocking; ignore removes interaction. Characters usually use capsule collision as the root and keep mesh collision minimal.

## Common Patterns

- Interaction trigger: `BoxComponent`/`SphereComponent` set to overlap pawn, with begin/end overlap events.
- Projectile or melee hit: trace by channel/object, validate hit actor, apply damage or interface call.
- Physics prop: static mesh with simple collision, `Simulate Physics`, mass/damping tuned, and an appropriate collision preset.
- Character: capsule blocks world, overlaps interactables, and mesh usually ignores camera/visibility unless needed.

## Physics Setup

Use simple collision for gameplay, complex collision for authored static surfaces only when necessary. Physics simulation requires primitive components and reliable collision geometry. Avoid enabling physics on character root capsules unless building a ragdoll/physics-driven controller.

## MCP Notes

- Use `get_blueprint_components` and actor/component property reads to inspect collision profiles and physics flags.
- Use `set_physics_properties`, component property tools, and trace/collision node tools only after reflecting property names.
- Document any limitation where collision response details require `exec_python` because a direct MCP command does not expose nested response containers.

## Audit Checklist

- Record collision profile names, object types, generated overlap events, blocking channels, and simulated physics flags.
- Flag interactables without overlap components, physics objects without simple collision, and gameplay traces using ambiguous channels.
