# Online Subsystem and EOS
> Source: project notes, Epic OSS/EOS documentation, networking study guide
> Last Updated: 2026-06-07 | UE 5.6+

---

## Overview

Unreal's Online Subsystem (OSS) and Online Services plugins provide common
interfaces for identity, sessions, friends, achievements, stats, leaderboards,
voice, storage, and other platform services. Epic Online Services (EOS) can be
used through OSS EOS or newer Online Services EOS/EOSGS plugin paths.

Choose the integration path early. Sessions, authentication, cross-platform
identity, and deployment configuration affect game architecture and cannot be
cleanly solved by sprinkling Blueprint session nodes at the end.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| Online Subsystem | Legacy/common interface layer for online providers. |
| OSS EOS plugin | EOS implementation for Online Subsystem interfaces. |
| Online Services EOS/EOSGS | Newer Online Services plugin path for EOS features. |
| `IOnlineIdentity` | Login/logout and user identity. |
| `IOnlineSession` | Create, find, join, update, and destroy sessions. |
| `FOnlineSessionSettings` | Session advertised settings and provider-specific attributes. |
| EOS Developer Portal artifacts | Product, sandbox, deployment, client, and artifact configuration. |

## Common Pitfalls

- Mixing Online Subsystem and Online Services approaches without a plan.
- Hardcoding client secrets or encryption keys into source.
- Forgetting EOS Developer Portal product/artifact/deployment alignment.
- Testing session creation with LAN settings and assuming EOS matchmaking works.
- Not handling login failure, account linking, or overlay-disabled cases.
- Using inconsistent stat names; OSS EOS expects upper-case stat configuration.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Create Blueprint session nodes | `session_create_blueprint_flow`, `session_find_blueprint_flow` |
| Inspect input/project state | `get_project_context`, `scan_project_assets` |
| Verify replication/session readiness | `network_debug_replication`, networking validators |
| Build UI flows | UMG/widget tools |
| Record config evidence | execution journal and report tools |

## Working Example

Goal: create an EOS-ready session prototype.

1. Register the product in the EOS Developer Portal.
2. Configure product id, sandbox id, deployment id, client id, and artifact
   settings in project config or secure deployment config.
3. Enable the chosen plugin path: OSS EOS or Online Services EOS/EOSGS.
4. Implement login with Account Portal for broad testing or Developer auth for
   local desktop iteration.
5. Add Create Session and Find Sessions flows with explicit LAN/lobby settings.
6. Add failure UI for login/session callbacks.
7. Test once locally, then with the intended EOS auth/session configuration.

## Validation Checklist

- Integration path is chosen and documented.
- Secrets and encryption keys are not committed.
- Login method and failure behavior are tested.
- Session settings match LAN, lobby, EOS, and platform expectations.
- Replication and session flows are verified together in a small multiplayer
  slice.

## References

- Epic: Online Subsystem EOS Plugin -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/online-subsystem-eos-plugin-in-unreal-engine?application_version=5.6
- Epic: Enable and Configure Online Services EOS -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/enable-and-configure-online-services-eos-in-unreal-engine?application_version=5.6
- Epic: Online Subsystems and Services -
  https://dev.epicgames.com/documentation/unreal-engine/online-subsystems-and-services-in-unreal-engine
