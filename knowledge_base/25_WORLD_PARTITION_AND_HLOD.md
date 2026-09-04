# World Partition and HLOD
> Source: project notes, Epic World Partition documentation, world-building guide
> Last Updated: 2026-06-07 | UE 5.6+

---

## Overview

World Partition replaces manual sublevel streaming for many large worlds by
storing a world in one persistent level divided into streaming grid cells.
Hierarchical Level of Detail (HLOD) generates proxy meshes/materials so distant
unloaded cells still read as part of the world.

Use World Partition for large or streaming worlds, not every small room-based
prototype. Use One File Per Actor and Data Layers intentionally, especially when
MCP automation is placing or editing many actors.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| `UWorldPartition` | World-level partition data and runtime cell management. |
| World Partition grid | Runtime streaming cell layout and loading policy. |
| Data Layers | Authoring/runtime layers for grouping and toggling actors. |
| `AWorldPartitionHLOD` | Runtime HLOD actor representing generated proxy content. |
| HLOD Layer asset | Rules for proxy mesh/material generation. |
| `UWorldPartitionStreamingSourceComponent` | Runtime source that controls which cells stream in. |
| One File Per Actor | Source-control-friendly actor storage model. |

## Common Pitfalls

- Converting a level without source-control discipline or backups.
- Forgetting that unloaded cells can hide actors during editor automation.
- Treating HLOD as only visual polish; it is often a performance requirement.
- Leaving large always-loaded Data Layers that defeat streaming.
- Running world-building MCP commands without checking loaded regions first.
- Shipping without testing runtime streaming sources and HLOD build output.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Inspect current level | `get_project_context`, actor/world inspection tools |
| Scan large-world assets | `scan_project_assets`, world-building tools |
| Load an edit window | `wp_load_region` |
| Unload an edit window | `wp_unload_region` |
| Create a Data Layer | `wp_create_data_layer` |
| Build or report HLODs | `hlod_generate` |
| Assign actor HLOD layer | `hlod_assign_layer` |
| Place or update actors | editor actor tools, viewport tools, execution journal |
| Audit performance | `stat`/viewport/profiling helpers, screenshot capture |
| Verify streaming behavior | PIE launch/log tools and manual streaming-source checks |

## MCP World Partition and HLOD Tools

Use these tools when the active editor world uses World Partition and you need
MCP-safe large-world authoring primitives before actor placement or HLOD builds.

| Tool | Use |
| --- | --- |
| `wp_load_region` | Create a user World Partition loader adapter for a center/extent region and load matching cells in the editor. |
| `wp_unload_region` | Unload and release matching editor loader adapters by label or region bounds. |
| `wp_create_data_layer` | Create or reuse a Data Layer asset and instance, set runtime/editor type, visibility, editor load state, and initial runtime state. |
| `hlod_generate` | Run the World Partition HLOD builder commandlet for setup/build/rebuild/delete/report/stat passes on the active map. |
| `hlod_assign_layer` | Assign an HLOD Layer asset to named actors or the current editor selection. |

Recommended MCP flow:

1. Load a region with `wp_load_region` before placing or editing actors in a
   large world.
2. Group authored content with `wp_create_data_layer` when ownership or runtime
   visibility matters.
3. Assign an HLOD layer to large distant static actors with `hlod_assign_layer`.
4. Run `hlod_generate` in report or build mode and inspect the commandlet log.
5. Unload temporary edit windows with `wp_unload_region` after the edit pass.

## Working Example

Goal: prepare a 2 km open-world prototype for streaming.

1. Create or convert an Open World level with World Partition enabled.
2. Enable One File Per Actor and organize set dressing into Data Layers.
3. Define runtime grid cell size based on traversal speed and sight lines.
4. Create HLOD layers for distant architecture, cliffs, and large static meshes.
5. Build HLODs and inspect generated proxy assets.
6. Use a streaming source on the player pawn and run PIE traversal tests.
7. Capture logs/screenshots at near, mid, and far distances.

## Validation Checklist

- The active work region is loaded before MCP actor edits.
- Data Layers have clear ownership and runtime expectations.
- HLOD layers exist for distant static geometry.
- Streaming source behavior is tested in PIE.
- Performance evidence includes draw calls or frame timing before/after HLOD.

## References

- Epic: World Partition -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/world-partition-in-unreal-engine
- Epic: World Partition HLOD -
  https://dev.epicgames.com/documentation/unreal-engine/world-partition---hierarchical-level-of-detail-in-unreal-engine
- Epic: World Settings -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/world-settings-in-unreal-engine?application_version=5.6
