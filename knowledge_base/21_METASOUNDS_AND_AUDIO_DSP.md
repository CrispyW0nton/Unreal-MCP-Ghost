# MetaSounds and Audio DSP
> Source: project notes, Epic MetaSounds documentation, Marques editor/audio workflow study guide
> Last Updated: 2026-06-07 | UE 5.6

---

## Overview

MetaSounds are procedural audio graphs for sound sources. Use them when sound
needs sample-accurate timing, parameterized variation, synthesis, reusable
patches, or gameplay-driven modulation. Use Sound Waves for recorded content,
Sound Cues for simpler legacy routing, and MetaSound Sources/Patches when the
audio behavior itself is a graph.

For MCP work, treat audio as a system with assets, attenuation, runtime
parameters, and verification. Do not leave audio as an afterthought attached to
the final Blueprint node.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| `UMetaSoundSource` | Playable MetaSound asset used like a sound source. |
| MetaSound Patch | Reusable subgraph for shared DSP logic. |
| `UAudioComponent` | Runtime component that plays and parameterizes sounds. |
| `USoundAttenuation` | 3D falloff, spatialization, and listener behavior. |
| `USoundConcurrency` | Voice limits and concurrency policy. |
| `USoundSubmix` | Mix routing, effects, recording, and analysis paths. |
| Audio parameters | Runtime controls for volume, pitch, filters, intensity, state. |

## Common Pitfalls

- Creating one-off MetaSound graphs with no reusable patches or naming scheme.
- Forgetting attenuation, causing 3D sounds to play as full-volume 2D audio.
- Driving many parameter updates every tick when events or timers would do.
- Shipping graphs that depend on editor-only debug assets.
- Ignoring concurrency for repeated impact, footstep, or weapon sounds.
- Mixing gameplay state and DSP implementation in the same unreadable graph.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Find audio assets | `scan_project_assets(path="/Game", class_filter="Sound")` |
| Import source audio | audio/import tools and `scan_project_assets` readback |
| Wire gameplay playback | Blueprint graph tools for `AudioComponent` or play-sound nodes |
| Attach to actors | component/Blueprint tools plus project context inspection |
| Verify runtime | PIE tools, log capture, viewport/audio-adjacent evidence notes |
| Package evidence | execution journal and vertical slice report tools |

## Working Example

Goal: create a reactive generator hum.

1. Create `MS_GeneratorHum` as a MetaSound Source with inputs:
   `User.Load`, `User.Damage`, and `User.Powered`.
2. Use a looped noise/oscillator layer for the base hum and modulate filter
   cutoff with `Load`.
3. Add intermittent crackle controlled by `Damage`.
4. Assign a `SoundAttenuation` asset with believable room falloff.
5. In `BP_Generator`, add an `AudioComponent` using `MS_GeneratorHum`.
6. On state changes, call parameter setters instead of respawning audio.
7. Verify in PIE by toggling powered state and logging parameter changes.

## Validation Checklist

- MetaSound assets use `MS_` or the project audio naming convention.
- 3D sounds have attenuation and concurrency policies.
- Runtime parameters are named, bounded, and updated on meaningful events.
- Reusable DSP logic lives in patches where appropriate.
- Gameplay Blueprint remains readable: it controls parameters, not graph internals.

## References

- Epic: MetaSounds Overview -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/metasounds-the-next-generation-sound-sources-in-unreal-engine?application_version=5.6
- Epic: MetaSounds Quick Start -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/metasounds-quick-start?application_version=5.6
- Epic: MetaSounds Reference Guide -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/metasounds-reference-guide-in-unreal-engine?application_version=5.6
