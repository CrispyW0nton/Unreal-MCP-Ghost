# SKILL: Import Texture

**Category:** Asset Import  
**Version:** 1.0  
**Added:** 2026-04-16  

## Description

Import a single texture file (PNG / JPG / TGA / EXR / HDR / BMP) from the
Windows host machine running UE5 into the Content Browser as a `Texture2D`
asset, automatically applying the correct compression settings and sRGB flag
based on the filename suffix or explicit `texture_type` argument.

## Required Tools

| Tool | Module | Purpose |
|---|---|---|
| `import_texture` | `asset_import_tools` | Core import + compression |
| `ue_describe_asset` | `reflection_tools` | Verify asset after import |
| `get_recent_output_log` | `reflection_tools` | Check for warnings/errors |

## Pre-conditions

- [ ] The texture file exists on the **Windows machine running UE5** at the
      path you supply (not the MCP server / sandbox machine).
- [ ] The file extension is one of: `.png`, `.jpg`, `.jpeg`, `.tga`, `.exr`,
      `.hdr`, `.bmp`.
- [ ] The Content Browser destination folder is valid (e.g. `/Game/Textures/`).

## Parameters

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `file_path` | str | — | Absolute OS path on the UE5 Windows machine |
| `destination_path` | str | `/Game/Textures/` | Content Browser destination folder |
| `texture_type` | str | `"auto"` | `auto` \| `diffuse` \| `normal` \| `roughness` \| `metallic` \| `ao` \| `emissive` \| `height` \| `default` |

## Auto-detection table (texture_type = "auto")

| Filename suffix | Detected type | Compression | sRGB |
|---|---|---|---|
| `_n`, `_normal`, `_nrm` | Normal | TC_NORMALMAP | False |
| `_r`, `_rough`, `_m`, `_metal`, `_ao`, `_occlusion`, `_mask`, `_orm` | Mask | TC_MASKS | False |
| `_h`, `_height`, `_disp` | Height | TC_MASKS | False |
| `_e`, `_emissive`, `_emit` | Emissive | TC_DEFAULT | True |
| *(anything else)* | BaseColor | TC_DEFAULT | True |

## Post-conditions

On success, the result includes:
```json
{
  "success": true,
  "stage": "import_texture",
  "outputs": {
    "asset_path": "/Game/Textures/T_Rock_BaseColor",
    "asset_type": "Texture2D",
    "texture_type": "BaseColor",
    "srgb": true,
    "compression": "TC_DEFAULT"
  }
}
```

## Validation Steps

1. Call `ue_describe_asset(asset_path="/Game/Textures/T_Rock_BaseColor")` —
   `exists` should be `true`, `class_name` should be `Texture2D`.
2. Call `get_recent_output_log(filter_category="Error")` — should return
   zero lines matching "Error" for this import.

## Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| `"Import returned no paths"` | File doesn't exist on UE5 machine | Verify path on the Windows host; use `import_sound_asset_from_sandbox` pattern if file is on sandbox |
| `success: false, error: "exec_python failed"` | UE5 not connected | Check TCP 55557 connection; restart plugin |
| sRGB is True on a normal map | auto-detection missed suffix | Pass `texture_type="normal"` explicitly |
| Import succeeds but texture looks wrong | Wrong compression | Re-call `import_texture` with explicit `texture_type` |

## Example Prompts

- "Import `C:/KotOR/exports/T_Bastila_n.tga` as a normal map texture into `/Game/Characters/Bastila/Textures/`"
- "Import the diffuse texture at `C:/Textures/T_Rock_d.png` into the project"
- "Add texture `T_Metal_ORM.tga` to `/Game/Materials/Textures/` with mask compression"

## Example Code

```python
# Via MCP tool call:
import_texture(
    file_path="C:/KotOR/exports/T_Bastila_n.tga",
    destination_path="/Game/Characters/Bastila/Textures/",
    texture_type="auto",   # auto-detects Normal from _n suffix
)

# Verify:
ue_describe_asset(asset_path="/Game/Characters/Bastila/Textures/T_Bastila_n")
get_recent_output_log(filter_category="Error", lines=50)
```
