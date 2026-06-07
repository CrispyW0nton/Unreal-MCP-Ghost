# MetaHuman Pipeline
> Source: project notes, Epic MetaHuman documentation, animation/import workflow notes
> Last Updated: 2026-06-07 | UE 5.6

---

## Overview

As of UE 5.6, MetaHuman authoring is centered on MetaHuman Character assets and
in-editor workflows rather than the older web-only creator flow. A production
pipeline must account for assembly, DNA/assets, body/face rig behavior,
materials, animation retargeting, LODs, and package size.

For MCP work, treat a MetaHuman as a multi-asset character package. Inspect the
asset tree, verify generated classes/Blueprint wrappers, and keep animation,
Control Rig, materials, and gameplay components separated.

## Key Classes

| Class or Asset | Role |
| --- | --- |
| MetaHuman Character asset | Authoring asset for character creation/customization. |
| MetaHuman Assembly | Game-ready generated asset set for Unreal or UEFN. |
| Skeletal Mesh assets | Body, head, clothing, and groom-related meshes. |
| Control Rig assets | Face/body rigging and animation control. |
| AnimBP / Post Process AnimBP | Runtime animation behavior. |
| DNA files/data | Identity/rig data for head/body pipelines. |
| Material instances | Skin, eyes, hair, clothing, and performance variants. |

## Common Pitfalls

- Assuming a MetaHuman asset exports or packages like a single character mesh.
- Editing generated assets without understanding whether they will be rebuilt.
- Ignoring LOD and groom cost on gameplay targets.
- Mixing gameplay logic into the MetaHuman Blueprint instead of using a wrapper
  or character base.
- Retargeting animation without checking skeleton, IK, and facial/body split.
- Forgetting that DCC export and game-ready assembly are different paths.

## MCP Tool Mapping

| Task | Preferred MCP direction |
| --- | --- |
| Inspect character assets | `scan_project_assets`, animation/mesh inspection tools |
| Build gameplay wrapper | Blueprint/component tools and generated-class checks |
| Retarget animations | IK Rig, IK Retargeter, batch retarget tools |
| Create animation logic | AnimBP, montage, Control Rig tools |
| Audit materials/performance | material/texture/mesh audit tools |
| Verify runtime | PIE, viewport screenshots, execution journal |

## MCP MetaHuman Tools

| Tool | Use |
| --- | --- |
| `metahuman_import` | Register an assembled/imported MetaHuman asset root, scan its package tree, and write a manifest section for later tools. |
| `metahuman_link_to_skeleton` | Link the body skeletal mesh to skeleton, IK Rig, retargeter, AnimBP, and post-process AnimBP references. |
| `metahuman_assign_dna` | Record DNA asset/file, face mesh, and rig logic metadata for face/body rig validation. |

## Working Example

Goal: integrate a MetaHuman NPC into a gameplay slice.

1. Create or import the MetaHuman Character and assemble game-ready assets.
2. Keep generated MetaHuman assets in a dedicated folder.
3. Create `BP_NPC_MetaHumanWrapper` as the gameplay Actor/Character.
4. Reference the MetaHuman skeletal components and assign AnimBP/Post Process
   AnimBP assets.
5. Retarget locomotion and an idle/talk montage to the body skeleton.
6. Add gameplay interaction components to the wrapper, not generated rig assets.
7. Validate LOD/groom/material cost with a viewport and performance pass.

## Validation Checklist

- Generated and hand-authored assets are separated.
- Animation retargeting is verified on the actual skeleton.
- Gameplay code lives in wrapper/base classes.
- LOD, groom, and material cost are checked against target platform.
- Packaging implications are noted before shipping a vertical slice.

## References

- Epic: Creating Your MetaHuman -
  https://dev.epicgames.com/documentation/en-us/unreal-engine/creating-your-metahuman-in-unreal-engine?application_version=5.6
- Epic: MetaHuman Workflow Changes -
  https://dev.epicgames.com/documentation/en-us/metahuman/metahuman-workflow-changes
