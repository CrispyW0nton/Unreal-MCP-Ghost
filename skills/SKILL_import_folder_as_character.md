# SKILL: Import Folder as Character

**Category:** Asset Import  
**Version:** 1.0  
**Added:** 2026-04-16  

## Description

Import a complete character export package — skeletal mesh FBX, textures,
and optional animations — from a structured local folder into UE5 as a
single organized asset set under one Content Browser destination.

This skill is the primary pipeline for KotOR/GhostRigger character imports
where GhostRigger has already exported the MDL → FBX + textures layout.

## Required Tools

| Tool | Module | Purpose |
|---|---|---|
| `import_folder_as_character` | `folder_import_tools` | All-in-one character pipeline |
| `scan_export_folder` | `folder_import_tools` | Optional pre-flight check |
| `ue_describe_asset` | `reflection_tools` | Verify imported assets |
| `get_recent_output_log` | `reflection_tools` | Check for rig/texture errors |

## Expected Folder Layout

```
<folder_path>/
  <character_name>.fbx      ← skeletal mesh (REQUIRED — must be in root)
  textures/                 ← optional subfolder (or textures in root)
    T_<name>_d.tga          ← diffuse (BaseColor)
    T_<name>_n.tga          ← normal map
    T_<name>_s.tga          ← specular / ORM mask
  animations/               ← optional — FBXs here imported with skeleton reuse
    Idle.fbx
    Walk.fbx
```

If no `animations/` subfolder is found, animation FBXs in other subfolders
are also picked up (unless they are the root FBX, which is treated as the mesh).

## Parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `folder_path` | str | — | Absolute path on MCP server machine |
| `character_name` | str | — | Creates `/Game/Characters/<character_name>/` |
| `ue5_base_path` | str | `/Game/Characters/` | Root for the character destination |
| `skeleton` | str | `""` | Existing skeleton to reuse, or `""` for new |
| `import_animations` | bool | `True` | Import animation FBXs |
| `import_morph_targets` | bool | `True` | Import blend shapes from the mesh FBX |

## UE5 Destination Structure

```
/Game/Characters/<character_name>/
  SK_<mesh_name>           ← SkeletalMesh
  SK_<mesh_name>_Skeleton  ← Skeleton
  Textures/
    T_<name>_d             ← diffuse (TC_DEFAULT, sRGB=True)
    T_<name>_n             ← normal  (TC_NORMALMAP, sRGB=False)
    ...
  Animations/
    Idle
    Walk
```

## Post-conditions

On success:
```json
{
  "success": true,
  "stage": "import_folder_as_character",
  "outputs": {
    "character_name": "Bastila",
    "ue5_destination": "/Game/Characters/Bastila",
    "skeletal_mesh": "/Game/Characters/Bastila/SK_Bastila",
    "skeleton": "/Game/Characters/Bastila/SK_Bastila_Skeleton",
    "textures": [
      "/Game/Characters/Bastila/Textures/T_Bastila_d",
      "/Game/Characters/Bastila/Textures/T_Bastila_n"
    ],
    "animations": ["Idle", "Walk"],
    "reused_skeleton": false
  }
}
```

## Validation Steps

1. `ue_describe_asset("/Game/Characters/Bastila/SK_Bastila")` → `class_name: SkeletalMesh`.
2. `ue_describe_asset("/Game/Characters/Bastila/SK_Bastila_Skeleton")` → `class_name: Skeleton`.
3. Check `outputs.textures` list — each entry should be verifiable via `ue_describe_asset`.
4. `get_recent_output_log(filter_category="LogFbx")` — check for bone/morph warnings.
5. Open the SkeletalMesh in the UE5 editor to confirm it poses correctly.

## Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| `success: false, error: "No FBX file found in folder root"` | FBX is in a subfolder, not root | Move FBX to folder root |
| `skeletal_mesh: ""` | FBX import failed | Check `errors` field + `get_recent_output_log` |
| `textures: []` | No texture files found | Check folder layout; textures must be `.png/.tga/.jpg` |
| `animations: []` with files present | Animation files not in `animations/` subfolder | Create an `animations/` subfolder or move FBXs there |
| Textures look dark/washed out | Wrong compression applied | Re-run `import_texture` for each texture with explicit `texture_type` |
| `reused_skeleton: false` when `skeleton` was specified | Skeleton path invalid | Verify with `ue_describe_asset` first |

## Example Prompts

- "Import the Bastila character from `/home/user/exports/Bastila/` into the project"
- "Import the KotOR NPC from `/mnt/aidrive/exports/Carth/` with morph targets"
- "Import the character folder at `/exports/Revan/` reusing the base humanoid skeleton"

## Example Code

```python
# Pre-flight scan
scan_export_folder(folder_path="/home/user/exports/Bastila/")

# Full character import
import_folder_as_character(
    folder_path="/home/user/exports/Bastila/",
    character_name="Bastila",
    ue5_base_path="/Game/Characters/",
    skeleton="",            # create new skeleton
    import_animations=True,
    import_morph_targets=True,
)

# Verify
ue_describe_asset("/Game/Characters/Bastila/SK_Bastila")
get_recent_output_log(filter_category="LogFbx", lines=100)
```
