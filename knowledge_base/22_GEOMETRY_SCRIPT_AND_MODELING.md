# Geometry Script and Modeling
> Source: project notes, Epic Geometry Script documentation, technical art workflow notes
> Last Updated: 2026-06-07 | UE 5.6+

---

## Overview

Geometry Script is Unreal's Blueprint/Python-accessible mesh processing library.
It is most useful for editor tooling, procedural mesh cleanup, generated static
meshes, collision helpers, UV operations, mesh booleans, and technical-art
automation. Most operations work through `UDynamicMesh`, so plan conversion into
and out of dynamic mesh data.

Use Geometry Script to produce or repair assets. Do not use it as a substitute
for runtime gameplay logic unless the feature has been profiled and the target
functions are runtime-safe.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| `UDynamicMesh` | Primary mutable mesh container for Geometry Script operations. |
| `UDynamicMeshComponent` | Component for displaying dynamic mesh data. |
| `ADynamicMeshActor` | Actor wrapper for dynamic mesh workflows. |
| `UGeometryScriptLibrary_*` | Function libraries for mesh read/write, booleans, UVs, normals, and queries. |
| Static Mesh asset | Common source and final output for authored game content. |
| Editor Utility Blueprint | Safe place for many editor-only Geometry Script operations. |

## Common Pitfalls

- Assuming all Geometry Script nodes are runtime-safe; some are editor-only.
- Forgetting that many functions must run on the game thread.
- Leaving production content as dynamic mesh components when Static Mesh assets
  are needed for Nanite, LODs, distance fields, or instancing.
- Ignoring collision and UV generation after procedural mesh edits.
- Running expensive mesh operations repeatedly in tick or construction scripts.
- Expecting Geometry Script to support landscapes, grooms, cloth, or geometry
  collections the same way it supports dynamic/static meshes.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Inspect mesh assets | `scan_project_assets`, mesh audit tools |
| Generate procedural assets | procedural/world tools, editor Python execution where safe |
| Create and edit dynamic mesh actors | `geom_create_dynamic_mesh`, `geom_boolean_op`, `geom_extrude`, `geom_remesh`, `geom_apply_displacement` |
| Generate UVs and bake assets | `geom_uv_unwrap`, `geom_bake_to_static_mesh` |
| Create materials for generated meshes | `material_*`, `mat_*`, texture tools |
| Place generated results | actor/viewport/editor tools |
| Verify performance | technical art audits, screenshot capture, execution journal |

## MCP Geometry Tools

B.6 adds native Geometry Script bridge routes in `geometry_tools.py` for
editor-safe DynamicMesh authoring:

- `geom_create_dynamic_mesh` spawns an `ADynamicMeshActor` and seeds it with a
  box, sphere, cylinder, plane, or empty mesh.
- `geom_boolean_op` applies union, intersection, subtract, trim-inside, or
  trim-outside operations between DynamicMesh actors.
- `geom_extrude` applies linear face extrusion through Geometry Script
  modeling options.
- `geom_remesh` applies uniform remeshing by target triangle count or target
  edge length.
- `geom_uv_unwrap` generates or lays out UVs with XAtlas, PatchBuilder,
  recompute, or layout modes.
- `geom_bake_to_static_mesh` writes a DynamicMesh actor to a saved Static Mesh
  asset under `/Game`.
- `geom_apply_displacement` applies Perlin-noise displacement for rock,
  terrain, and blockout variation passes.

Treat these as technical-art/editor authoring tools. After baking, verify the
Static Mesh asset path, material slots, collision, UV channel count, and runtime
rendering before deleting the source DynamicMesh actor.

## Working Example

Goal: create a clean prototype cover block asset from a generated mesh.

1. Use editor-safe Python or an Editor Utility Blueprint to create a
   `UDynamicMesh`.
2. Append box primitives for the cover shape.
3. Weld coincident vertices and recompute normals.
4. Generate simple UVs and assign a master material instance.
5. Bake or write the result to `SM_CoverBlock_A`.
6. Add simple collision and save the package.
7. Use MCP mesh/material audit tools to verify asset path, material slot, size,
   and reference counts.

## Validation Checklist

- The function path is editor-only or runtime-safe by design.
- Expensive operations are not in tick.
- Final gameplay assets use Static Mesh where Nanite/LOD/instancing matter.
- Collision, UVs, normals, and material slots are explicitly checked.
- Generated assets are named and saved in the expected Content folder.

## References

- Epic: Geometry Scripting Users Guide -
  https://dev.epicgames.com/documentation/unreal-engine/geometry-scripting-users-guide-in-unreal-engine
- Epic: Geometry Scripting Reference -
  https://dev.epicgames.com/documentation/unreal-engine/geometry-scripting-reference-in-unreal-engine
