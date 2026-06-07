# Networking and Replication
> Source: project notes, Epic UE networking documentation, Li C++/multiplayer study guide
> Last Updated: 2026-06-07 | UE 5.6

---

## Overview

Unreal networking is server-authoritative. The server owns the true gameplay
state, clients send input or requests, and the server replicates relevant state
back to clients. Design for multiplayer early: retrofitting replication after a
single-player Blueprint graph is finished usually means rewriting ownership,
authority, and state flow.

Replication is not automatic just because an Actor exists. You must decide which
Actors replicate, which properties replicate, which RPCs are needed, which
connection owns each Actor, and which events should remain cosmetic/local.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| `AActor` | Primary replicated object type; supports replicated properties and RPCs. |
| `APawn` / `ACharacter` | Player and AI bodies; movement replication often starts here. |
| `APlayerController` | Owning client bridge; good for client-specific input and UI. |
| `APlayerState` | Replicated player data visible to everyone. |
| `AGameStateBase` | Replicated match/session state visible to clients. |
| `AGameModeBase` | Server-only rules; never expect clients to read it directly. |
| `UNetDriver` | Runtime network driver and connection state. |
| Replication Graph / Iris | Scale-oriented replication systems for larger projects. |

## Common Pitfalls

- Reading `GameMode` on a client; it exists on the server only.
- Marking every variable replicated instead of separating authoritative,
  owner-only, simulated, and cosmetic state.
- Using reliable multicast RPCs for frequent events.
- Letting clients spawn gameplay Actors that should be server-spawned.
- Forgetting ownership before using owner-only RPCs or owner-conditioned
  variables.
- Assuming meshes, materials, audio, and particles replicate as visuals; usually
  replicated state should drive local cosmetic playback.
- Finishing without a two-player PIE or network log check.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Inspect Blueprint replication | `net_describe_blueprint_replication` |
| Enable Actor/component replication | `net_set_actor_replicates`, `net_set_component_replicates` |
| Configure replicated variables | `net_configure_replicated_property`, `net_add_repnotify_variable` |
| Create RPC flow | `net_create_rpc_event`, `net_configure_rpc`, `net_add_authority_gate` |
| Add ownership/role checks | `net_set_owner_reference`, `net_add_role_switch` |
| Verify runtime state | `network_debug_replication`, `pie_launch_session`, `pie_capture_log` |
| Validate common mistakes | `net_validate_common_mistakes` |

## Working Example

Goal: make an interactable door open in multiplayer.

1. Server owns the door Actor. Enable `bReplicates`.
2. Add replicated `bIsOpen` with `RepNotify`.
3. Client input calls a Server RPC on the owning pawn/controller:
   `Server_RequestOpenDoor(DoorRef)`.
4. The server validates distance, line of sight, and locked state.
5. The server sets `bIsOpen = true`; `OnRep_IsOpen` plays the door animation on
   clients.
6. Use multicast only for non-state one-shot cosmetics when RepNotify cannot
   express the result.
7. Run two-player PIE and capture logs plus `network_debug_replication`.

## Validation Checklist

- Every replicated variable has a reason and owner/relevancy expectation.
- RPCs are sparse, intentional, and not called every tick.
- Server-only logic is protected by authority checks.
- Cosmetic effects are driven by replicated state or local prediction.
- Two-player PIE evidence exists before calling the slice complete.

## References

- Epic: Networking Overview -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-overview-for-unreal-engine?application_version=5.6
- Epic: Networking and Multiplayer -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/networking-and-multiplayer-in-unreal-engine?application_version=5.6
- Epic: Replicate Actor Properties -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/replicate-actor-properties-in-unreal-engine?application_version=5.6
