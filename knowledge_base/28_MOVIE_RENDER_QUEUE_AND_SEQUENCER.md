# Movie Render Queue and Sequencer
> Source: project notes, Epic Sequencer/Movie Render Queue documentation, cinematic workflow notes
> Last Updated: 2026-06-07 | UE 5.6

---

## Overview

Sequencer authors in-engine cinematics through Level Sequence assets and tracks.
Movie Render Queue (MRQ) renders high-quality output, including shot-based jobs,
multiple cameras, and runtime render queues. Use Sequencer for timeline logic,
camera work, animation, events, and renders; use gameplay Blueprints for
interactive state.

For MCP work, keep cinematic assets inspectable: Level Sequence, Level Sequence
Actor, bindings, cameras, shots, render presets, and output folders.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| Level Sequence | Timeline asset containing tracks, bindings, cameras, and shots. |
| Level Sequence Actor | Placed actor that plays a Level Sequence in a world. |
| Cinematic Camera Actor | Camera with filmback, lens, focus, and shot settings. |
| Movie Render Queue | Render job queue and high-quality output system. |
| Movie Pipeline Executor | Runtime or editor execution path for queued renders. |
| Camera Cut track | Selects active camera over time. |
| Subsequence/Shot tracks | Organize larger cinematic timelines. |

## Common Pitfalls

- Rendering from a sequence with no active camera cut.
- Binding possessables to actors that are missing in the render level.
- Changing gameplay state in Sequencer without resetting it after playback.
- Using MRQ before enabling/configuring the plugin.
- Forgetting warm-up frames for particles, cloth, or post-process effects.
- Writing renders into project content folders instead of artifact/output paths.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Inspect cinematic assets | `scan_project_assets`, sequence/camera asset scans |
| Place cameras/actors | editor actor and viewport tools |
| Create animation support | `anim_*`, Control Rig, Blueprint tools |
| Create MRQ jobs | `mrq_create_job` |
| Configure MRQ output/passes | `mrq_add_render_setting` |
| Validate or start queue renders | `mrq_render_queue` |
| Verify visual output | viewport screenshot, PIE/log tools |
| Document output | execution journal and report packager |

## MCP Movie Render Queue Tools

The B.11 `mrq_tools.py` module exposes editor-queue controls backed by native
MRQ bridge commands:

| Tool | Use |
| --- | --- |
| `mrq_create_job` | Allocate an editor queue job, assign sequence/map paths, output folder, filename format, resolution, default deferred pass, and image output format. |
| `mrq_add_render_setting` | Add or update output, image output, deferred pass, anti-aliasing, or console variable settings for a named job or the latest queue job. |
| `mrq_render_queue` | Dry-run validate the current queue by default, or start a PIE executor render when `dry_run=False`. |

Default `mrq_render_queue` calls are dry runs so automation can inspect queue
state safely. Start an actual render only after confirming camera cuts, bindings,
output path, frame range, and warm-up requirements.

## Working Example

Goal: render a 12-second reveal shot.

1. Create `LS_Reveal_Intro` and place `CineCam_Reveal_A`.
2. Add a Camera Cut track covering the full 12 seconds.
3. Bind the hero actor and add transform/focal-length keyframes.
4. Add warm-up frames for Niagara or cloth if present.
5. Configure an MRQ preset for resolution, anti-aliasing, output path, and
   filename format.
6. Render a short preview first, then the final queue.
7. Save screenshot/render paths in the execution journal.

## Validation Checklist

- Active camera cuts cover the render range.
- Bindings resolve in the target level.
- Output path is outside transient or protected folders.
- Warm-up is set for simulation-heavy shots.
- Render evidence and settings are recorded.

## References

- Epic: Sequencer Overview -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-sequencer-movie-tool-overview?application_version=5.6
- Epic: Rendering from Multiple Camera Angles -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/rendering-from-multiple-camera-angles-in-unreal-engine?application_version=5.6
- Epic: Movie Render Queue in Runtime -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/movie-render-queue-in-runtime-in-unreal-engine?application_version=5.6
