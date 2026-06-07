# Pixel Streaming and Remote Access
> Source: project notes, Epic Pixel Streaming documentation, deployment workflow notes
> Last Updated: 2026-06-07 | UE 5.6+

---

## Overview

Pixel Streaming runs an Unreal application on a host machine and streams frames
and audio to browser clients over WebRTC, while forwarding browser input back to
the application. It is for remote interactive experiences, demos, virtual
production review, configurators, and web-accessible prototypes.

Pixel Streaming depends on packaged or standalone execution for the standard
runtime path, GPU video encoding support, open ports, and external signalling
infrastructure. Treat it as deployment work, not just an editor checkbox.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| Pixel Streaming plugin | Unreal-side capture/input integration. |
| Pixel Streaming 2 plugin | Newer generation; check compatibility/settings before use. |
| Signalling server | WebRTC coordination between app and browser clients. |
| SFU / Matchmaker | Infrastructure for scale and routing when needed. |
| Frontend web app | Browser player and custom UI integration. |
| WebRTC encoder | Hardware/software path for streamed video. |
| Custom data channels | Browser-to-Unreal UI and gameplay messages. |

## Common Pitfalls

- Testing only in PIE when the feature needs standalone/packaged validation.
- Ignoring GPU encoder support on the host machine.
- Leaving ports closed or blocked by cloud/firewall settings.
- Using outdated Pixel Streaming settings with Pixel Streaming 2.
- Treating browser UI input as trusted gameplay authority.
- Forgetting latency/quality tradeoffs for the actual network environment.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Inspect project/plugins | `get_project_context`, plugin/project scans |
| Package/build readiness | packaging docs and build/optimization checks |
| Configure gameplay input | Enhanced Input and Blueprint tools |
| Verify standalone behavior | PIE/standalone logs, screenshots, execution journal |
| Document deployment | report packager and artifact paths |

## Working Example

Goal: prepare a local Pixel Streaming demo.

1. Enable Pixel Streaming or Pixel Streaming 2 as appropriate for the engine.
2. Package or launch the project as Standalone Game with required command-line
   options.
3. Start the Pixel Streaming infrastructure signalling server.
4. Open required local ports, commonly web/signalling defaults from the current
   reference docs.
5. Connect from a browser on the same network.
6. Test mouse, keyboard, touch/gamepad if required, and any custom HTML UI
   messages.
7. Capture host logs and browser connection notes.

## Validation Checklist

- Host OS/GPU supports video encoding requirements.
- The tested mode is standalone or packaged, not only PIE.
- Network ports and signalling infrastructure are documented.
- Browser input is validated and sanitized in gameplay code.
- Latency/quality settings match the demo target.

## References

- Epic: Pixel Streaming -
  https://dev.epicgames.com/documentation/unreal-engine/pixel-streaming-in-unreal-engine
- Epic: Getting Started with Pixel Streaming -
  https://dev.epicgames.com/documentation/unreal-engine/getting-started-with-pixel-streaming-in-unreal-engine
- Epic: Pixel Streaming Reference -
  https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-pixel-streaming-reference
