# SKILL: Batch Import Folder

**Category:** Asset Import  
**Version:** 1.0  
**Added:** 2026-04-16  

## Description

Scan a local export folder on the MCP server machine for importable assets
(textures, meshes, audio), then forward all recognized files to UE5 in a
single batch operation.  Supports dry-run mode, selective type import,
recursive scanning, and Content Browser folder structure preservation.

## Required Tools

| Tool | Module | Purpose |
|---|---|---|
| `scan_export_folder` | `folder_import_tools` | Local scan — no UE5 needed |
| `batch_import_folder` | `folder_import_tools` | Batch UE5 import |
| `get_recent_output_log` | `reflection_tools` | Check for per-asset errors |
| `ue_summarize_operation_effects` | `reflection_tools` | Snapshot before/after |

## Pre-conditions

- [ ] The folder exists on the **MCP server machine** (not the UE5 machine).
- [ ] The files inside the folder must be on the **UE5 Windows machine** at the
      same paths (or accessible via a shared drive / mapped path).
- [ ] The Content Browser destination root is valid.

## Parameters — scan_export_folder

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `folder_path` | str | — | Absolute path on MCP server |
| `recursive` | bool | `True` | Scan subdirectories |

## Parameters — batch_import_folder

| Parameter | Type | Default | Notes |
|---|---|---|---|
| `folder_path` | str | — | Same folder as scan |
| `ue5_base_path` | str | `/Game/Imported/` | Content Browser root for imports |
| `recursive` | bool | `True` | Import subdirectory assets too |
| `import_textures` | bool | `True` | Include texture files |
| `import_meshes` | bool | `True` | Include mesh files |
| `import_audio` | bool | `True` | Include audio files |
| `preserve_folder_structure` | bool | `True` | Mirror subfolder layout in UE5 |
| `dry_run` | bool | `False` | Preview only — no UE5 import |

## Recommended Workflow

```
Step 1: scan_export_folder  ← always start here
Step 2: review manifest     ← check category counts, confirm paths are right
Step 3: batch_import_folder(dry_run=True)  ← preview what will be imported
Step 4: batch_import_folder(dry_run=False) ← execute
Step 5: get_recent_output_log(filter_category="Error")  ← check for failures
```

## Post-conditions

On success:
```json
{
  "success": true,
  "stage": "batch_import_folder",
  "outputs": {
    "dry_run": false,
    "total": 15,
    "imported": 14,
    "failed": 1,
    "results": [
      {"file": "T_Rock_d.tga", "success": true, "asset_path": "/Game/..."},
      {"file": "SM_BadFile.fbx", "success": false, "error": "..."}
    ]
  }
}
```

## Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| `success: false, error: "Folder not found"` | Wrong local path | Verify path exists on MCP server machine |
| `imported: 0` but `total > 0` | Files not on UE5 machine | Files need to be accessible from the UE5 host |
| Per-file `"Import returned no paths"` | File path mismatch between MCP and UE5 host | Use shared/mapped drive paths |
| Audio files skipped | `import_audio=False` | Set `import_audio=True` |
| Folder structure not mirrored | `preserve_folder_structure=False` | Set to `True` |

## Example Prompts

- "Import all assets from `/home/user/exports/KotOR_props/` into `/Game/KotOR/`"
- "Scan the export folder at `/mnt/aidrive/character_exports/` and show me what's there"
- "Batch import all textures and meshes from the export folder, skip audio"
- "Do a dry run of importing `/home/user/exports/level_01/` to see what would be imported"

## Example Code

```python
# Step 1: scan
scan_export_folder(folder_path="/home/user/exports/KotOR_props/", recursive=True)

# Step 2: dry run
batch_import_folder(
    folder_path="/home/user/exports/KotOR_props/",
    ue5_base_path="/Game/KotOR/Props/",
    dry_run=True,
)

# Step 3: real import
batch_import_folder(
    folder_path="/home/user/exports/KotOR_props/",
    ue5_base_path="/Game/KotOR/Props/",
    dry_run=False,
    import_textures=True,
    import_meshes=True,
    import_audio=False,
    preserve_folder_structure=True,
)

# Step 4: check
get_recent_output_log(filter_category="Error", lines=100)
```
