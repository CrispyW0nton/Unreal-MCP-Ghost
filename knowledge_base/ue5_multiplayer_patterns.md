# UE5 Multiplayer Patterns Reference
> Sources: Li, Marques/Sherry/Pereira/Fozi; synthesized for Unreal-MCP-Ghost.
> Updated: 2026-04-29

## Authority Model

Unreal gameplay is server-authoritative. `GameModeBase` exists only on the server. `GameStateBase` and `PlayerState` replicate shared and per-player state. Pawns, actors, components, and variables replicate only when explicitly configured.

## Replication Building Blocks

- Actor replication: enable `bReplicates`; use `bReplicateMovement` for transform sync when appropriate.
- Variable replication: mark properties replicated; use RepNotify callbacks when clients need side effects.
- RPCs: `Server` for client-to-server requests, `Client` for server-to-owning-client notifications, `NetMulticast` for server-to-all cosmetic events.
- Ownership matters: only owning clients can send server RPCs through owned actors/controllers.

## Blueprint/C++ Split

Use C++ or carefully structured Blueprints for authoritative state changes. Avoid putting authoritative rules in widgets or purely client-local actors. Cosmetic VFX/audio can often run client-side, but damage, scoring, inventory, and win/loss flow should be server-owned.

## MCP Notes

- Audit replicated flags via Blueprint variable metadata and CDO/class properties where available.
- Use `exec_python` reflection when direct MCP tools do not expose replication flags or function specifiers.
- Document any Lab4D system that appears single-player only so future multiplayer work does not assume replication exists.

## Audit Checklist

- Identify custom `GameMode`, `GameState`, `PlayerState`, `PlayerController`, pawn, and replicated actors.
- Record replicated variables, RepNotify functions, and RPC functions.
- Flag client-only UI/Blueprint logic that modifies gameplay state directly.
