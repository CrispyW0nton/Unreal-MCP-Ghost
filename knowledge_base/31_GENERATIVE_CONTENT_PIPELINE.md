# Generative Content Pipeline
> Source: project notes, MCP import/tooling roadmap, Unreal asset pipeline practice
> Last Updated: 2026-06-07 | UE 5.6

---

## Overview

Generative content is only useful when it lands in Unreal as controlled,
inspectable, performant game content. Treat generated images, meshes, audio,
animations, and text as inputs to a production pipeline: prompt, generate,
review, import, normalize, materialize, optimize, place, verify, and document.

For Unreal-MCP-Ghost, the agent should never declare generated content complete
at "asset downloaded." Completion means the generated asset is imported or
recorded, named, organized, referenced by gameplay/world assets, audited, and
verified in-editor.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| `UAssetImportTask` | Editor import task for repeatable asset imports. |
| Static Mesh / Skeletal Mesh | Common destinations for generated 3D assets. |
| Texture2D | Destination for generated images, masks, and material inputs. |
| Sound Wave / MetaSound | Destination or wrapper for generated audio. |
| Material / Material Instance | Turns generated textures into consistent PBR assets. |
| Data Asset / Data Table | Stores generated structured design data. |
| Execution journal | Records prompts, source files, imports, audits, and evidence. |

## Common Pitfalls

- Importing generated assets without source prompt/version metadata.
- Accepting broken scale, pivots, collision, UVs, normals, or material slots.
- Using generated textures outside project compression and naming standards.
- Placing large unoptimized meshes directly into a playable map.
- Losing track of license, consent, or provenance for generated content.
- Treating "AI made it" as an excuse to skip art direction and technical review.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Import assets | asset import, batch import, texture/audio import tools |
| Normalize materials | `material_create_master`, `material_create_instance_from_master`, texture tools |
| Audit meshes/textures | mesh, texture, technical-art audit tools |
| Place generated content | editor actor and viewport tools |
| Build procedural variants | procedural/world tools and data assets |
| Verify playable result | PIE/log/screenshot tools and execution journal |

## Working Example

Goal: bring a generated grocery shelf prop into a playable slice.

1. Record the prompt, generator, version, and output files in the journal.
2. Import the mesh into `/Game/Generated/Props/Grocery/`.
3. Normalize scale and pivot; create collision suitable for the prop.
4. Import base color, normal, and ORM textures; compress them appropriately.
5. Create `MI_GroceryShelf_A` from the project master material.
6. Assign materials, save assets, and inspect references/size.
7. Place one prop in the level, capture a screenshot, and log any needed art
   fixes.

## Validation Checklist

- Prompt/provenance and source files are recorded.
- Asset names and folders follow project conventions.
- Mesh scale, pivot, collision, UVs, material slots, and texture compression are
  checked.
- Runtime placement is verified visually and through asset scans.
- Generated content has an owner and follow-up list for human review.

## References

- Epic: Importing Assets Directly -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-directly-into-unreal-engine
- Epic: Working with Assets -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-assets-in-unreal-engine
- Epic: Interchange Framework -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/importing-assets-using-interchange-in-unreal-engine
