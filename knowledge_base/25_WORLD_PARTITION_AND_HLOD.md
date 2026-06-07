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
| Place or update actors | editor actor tools, viewport tools, execution journal |
| Audit performance | `stat`/viewport/profiling helpers, screenshot capture |
| Verify streaming behavior | PIE launch/log tools and manual streaming-source checks |

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
