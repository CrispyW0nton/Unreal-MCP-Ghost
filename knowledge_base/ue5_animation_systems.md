# UE5 Animation Systems Reference
> Sources: Li, Marques/Sherry/Pereira/Fozi, Sapio; synthesized for Unreal-MCP-Ghost.
> Updated: 2026-04-29

## Core Assets

Animation systems revolve around skeletal meshes, skeletons, animation sequences, blend spaces, animation montages, animation notifies, physics assets, IK rigs, control rigs, and Animation Blueprints. Keep game state in the character/controller and copy only animation-driving values into the Animation Blueprint.

## Animation Blueprint Pattern

- Event Graph: cache owning pawn/character, validate it, then update variables such as `Speed`, `Direction`, `IsInAir`, `IsCrouching`, `IsAttacking`, and `IsBlocking`.
- AnimGraph: blend poses only. Use state machines, blend spaces, slots, layered blends, aim offsets, IK, and output pose.
- State machines model durable movement/combat states; montages handle one-off actions such as attacks, hits, emotes, and workbench interactions.

## Montages and Notifies

Use montages for triggered actions with clear entry/exit rules. Use slots for upper-body or full-body playback. Use Anim Notifies for frame-accurate gameplay cues such as hit windows, footstep sounds, AI noise, VFX, and weapon activation.

## MCP Notes

- Direct AnimGraph automation is limited; verify with available animation tools and fall back to editor/manual steps where needed.
- `create_animation_blueprint`, `add_state_machine`, `add_animation_state`, `add_state_transition`, `set_animation_for_state`, and `add_anim_notify` are useful when available.
- Always document skeleton assignment status; an Animation Blueprint without a compatible skeleton will not be production-ready.

## Audit Checklist

- List all `ABP_`, `BS_`, `AM_`, `AN_`, skeletal mesh, skeleton, and physics assets.
- Record state machines, animation variables, montage slots, notifies, and owning character classes.
- Flag missing skeletons, unassigned meshes, gameplay logic in AnimGraphs, and montage actions without notify/event cleanup.
