# SKILL: Import Skeletal Mesh

**Category:** Asset Import  
**Version:** 1.0  
**Added:** 2026-04-16  

## Description

Import an FBX file from the UE5 host machine as a `SkeletalMesh` asset,
with optional animation import, morph targets, material import, and
skeleton reuse.  The imported mesh, its skeleton, and any animations are
all returned in the structured result.

## Required Tools

| Tool | Module | Purpose |
|---|---|---|
| `import_skeletal_mesh` | `asset_import_tools` | Core import |
| `ue_describe_asset` | `reflection_tools` | Verify SkeletalMesh + Skeleton |
| `get_recent_output_log` | `reflection_tools` | Check for rig/bone warnings |

## Pre-conditions

- [ ] The FBX file exists on the **Windows machine running UE5**.
- [ ] File extension is `.fbx` (FBX only for skeletal meshes).
- [ ] If reusing an existing skeleton, the Content Browser path is known.
- [ ] The destination Content Browser folder is valid.

## Parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `file_path` | str | — | Absolute OS path on UE5 machine |
| `destination_path` | str | `/Game/Characters/` | Content Browser destination |
| `skeleton` | str | `""` | Existing Skeleton path to reuse, or `""` to create new |
| `import_animations` | bool | `True` | Import embedded AnimSequences |
| `import_morph_targets` | bool | `True` | Import blend shapes / morph targets |
| `import_materials` | bool | `True` | Import embedded materials |

## Skeleton Reuse

To retarget a character to an existing rig (e.g., UE5 Mannequin):
```python
import_skeletal_mesh(
    file_path="C:/Characters/Bastila.fbx",
    destination_path="/Game/Characters/Bastila/",
    skeleton="/Game/Mannequin/Animations/Skeleton",
)
```
If the specified skeleton is not found, a warning is added to the result
and a new skeleton is created automatically.

## Post-conditions

On success:
```json
{
  "success": true,
  "stage": "import_skeletal_mesh",
  "outputs": {
    "asset_path": "/Game/Characters/Bastila/SK_Bastila",
    "asset_type": "SkeletalMesh",
    "skeleton_path": "/Game/Characters/Bastila/SK_Bastila_Skeleton",
    "animations_imported": ["Idle", "Walk", "Attack"],
    "reused_skeleton": false
  }
}
```

## Validation Steps

1. `ue_describe_asset("/Game/Characters/Bastila/SK_Bastila")` — `class_name: SkeletalMesh`.
2. `ue_describe_asset("/Game/Characters/Bastila/SK_Bastila_Skeleton")` — `class_name: Skeleton`.
3. `get_recent_output_log(filter_category="LogFbx")` — check for missing bone warnings.
4. If `reused_skeleton: true`, verify animations play correctly in the editor.

## Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| `"Import returned no paths"` | File missing on UE5 host | Verify path |
| `animations_imported: []` despite `import_animations=True` | No animations in FBX | Normal — animations may be in separate FBX files |
| `reused_skeleton: false` with skeleton specified | Skeleton path invalid | Check with `ue_describe_asset` first |
| Mesh deforms badly | Bone count mismatch when reusing skeleton | Use a skeleton with the same joint hierarchy |
| `"LogFbx: Warning: Some bones were not found"` | Mismatched skeleton | Don't reuse the skeleton; let UE5 create a new one |

## Example Prompts

- "Import `Bastila.fbx` as a skeletal mesh into `/Game/Characters/Bastila/`"
- "Import the KotOR character FBX with morph targets enabled"
- "Import `SK_NPC.fbx` reusing the UE5 Mannequin skeleton"

## Example Code

```python
# New character, auto-create skeleton:
import_skeletal_mesh(
    file_path="C:/KotOR/exports/Bastila.fbx",
    destination_path="/Game/Characters/Bastila/",
    skeleton="",
    import_animations=True,
    import_morph_targets=True,
)

# Re-use an existing skeleton:
import_skeletal_mesh(
    file_path="C:/KotOR/exports/SoldierNPC.fbx",
    destination_path="/Game/Characters/Soldiers/",
    skeleton="/Game/Characters/BaseSkeleton",
    import_morph_targets=False,
)
```
