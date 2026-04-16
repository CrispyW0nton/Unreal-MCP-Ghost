# SKILL: Import Static Mesh

**Category:** Asset Import  
**Version:** 1.0  
**Added:** 2026-04-16  

## Description

Import a 3D model file (FBX / OBJ / glTF / GLB) from the UE5 host machine
into the Content Browser as a `StaticMesh` asset, with configurable options
for mesh combination, lightmap UVs, collision, and embedded materials/textures.

## Required Tools

| Tool | Module | Purpose |
|---|---|---|
| `import_static_mesh` | `asset_import_tools` | Core import |
| `ue_describe_asset` | `reflection_tools` | Verify asset after import |
| `get_recent_output_log` | `reflection_tools` | Check for warnings/errors |

## Pre-conditions

- [ ] The mesh file exists on the **Windows machine running UE5**.
- [ ] File extension is one of: `.fbx`, `.obj`, `.gltf`, `.glb`.
- [ ] The Content Browser destination folder is valid (e.g. `/Game/Meshes/`).

## Parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `file_path` | str | — | Absolute OS path on UE5 machine |
| `destination_path` | str | `/Game/Meshes/` | Content Browser destination |
| `combine_meshes` | bool | `True` | Merge all sub-meshes into one asset |
| `generate_lightmap_uvs` | bool | `True` | Auto-generate UV channel 1 |
| `auto_generate_collision` | bool | `True` | Create simple collision hull |
| `import_materials` | bool | `True` | Import embedded materials |
| `import_textures` | bool | `True` | Import embedded textures |

## Format Notes

- **FBX / OBJ**: Full import options applied via `FbxImportUI`.
- **glTF / GLB**: UE5 Interchange Framework handles import; FBX options
  are not applied but the destination and naming still work correctly.

## Post-conditions

On success:
```json
{
  "success": true,
  "stage": "import_static_mesh",
  "outputs": {
    "asset_path": "/Game/Meshes/SM_Table",
    "asset_type": "StaticMesh",
    "poly_count": -1
  }
}
```
`poly_count: -1` is a sentinel meaning "imported successfully"; the actual
triangle count is not directly accessible via the Python API.

## Validation Steps

1. `ue_describe_asset("/Game/Meshes/SM_Table")` — `exists: true`, `class_name: StaticMesh`.
2. `get_recent_output_log(filter_category="LogStaticMesh")` — check for any LOD or UV warnings.
3. Open in Content Browser (manual) — verify the mesh appears correct.

## Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| `"Import returned no paths"` | File missing on UE5 host | Verify path on Windows machine |
| Asset imports as `SkeletalMesh` | FBX has a skeleton | Set `import_as_skeletal=False` via manual FbxImportUI or use `import_skeletal_mesh` intentionally |
| Materials not imported | Embedded materials not present | Set `import_materials=False`, create materials manually |
| glTF mesh looks wrong | Interchange framework version mismatch | Update UE5 to 5.2+ for full Interchange support |

## Example Prompts

- "Import `C:/Models/SM_Table.fbx` as a static mesh into `/Game/Props/`"
- "Add the rock mesh at `C:/KotOR/SM_Rock.fbx` to the project with lightmap UVs"
- "Import `scene.glb` into `/Game/Environment/`"

## Example Code

```python
import_static_mesh(
    file_path="C:/Models/SM_Table.fbx",
    destination_path="/Game/Props/",
    combine_meshes=True,
    generate_lightmap_uvs=True,
    auto_generate_collision=True,
)
# Verify
ue_describe_asset(asset_path="/Game/Props/SM_Table")
```
