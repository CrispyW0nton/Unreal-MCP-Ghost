# SKILL: Diagnose Failed Import

**Category:** Diagnostics  
**Version:** 1.0  
**Added:** 2026-04-16  

## Description

Systematically diagnose why an asset import failed and provide actionable
recovery guidance.  This skill chains reflection and log tools to determine
the root cause: missing file, wrong path, missing plugin, bad FBX, or UE5
connection issue.

## Required Tools

| Tool | Module | Purpose |
|---|---|---|
| `get_recent_output_log` | `reflection_tools` | Read the UE5 Output Log |
| `ue_describe_asset` | `reflection_tools` | Check if the asset was partially created |
| `ue_exec_safe` | `exec_substrate` | Run diagnostic Python snippets |
| `ue_summarize_operation_effects` | `reflection_tools` | Check Content Browser state |

## Pre-conditions

- [ ] An import tool (`import_texture`, `import_static_mesh`, etc.) returned
      `success: false` or the asset is not in the expected location.

## Diagnostic Decision Tree

```
1. Did the tool return success=false with an error message?
   → Read the "error" field first — it's usually self-explanatory.
   → "Import returned no paths" → go to Step A (file existence check)
   → "exec_python failed" → go to Step B (connection check)
   → Other errors → go to Step C (log check)

2. Step A — File existence check
   ue_exec_safe(code='''
   import os
   path = "C:/path/to/file.fbx"
   _result["exists"] = os.path.exists(path)
   _result["path"] = path
   ''')
   → If exists=false: file is missing on the UE5 host. Copy it there.
   → If exists=true: proceed to Step C.

3. Step B — Connection check
   ue_exec_safe(code="_result['ping'] = 'pong'")
   → If success=false: UE5 not connected. Restart the plugin on TCP 55557.

4. Step C — Log check
   get_recent_output_log(filter_category="Error", lines=200)
   get_recent_output_log(filter_category="LogFbx", lines=200)
   get_recent_output_log(filter_category="LogAssetTools", lines=200)
   → Look for: "Cannot find file", "Invalid root", "Importer failed"

5. Step D — Partial asset check
   ue_describe_asset(asset_path="<expected_path>")
   → If exists=true but class is wrong: delete and re-import
   → If exists=false: import genuinely failed
```

## Common Error Patterns

| Log message | Root cause | Fix |
|---|---|---|
| `Cannot find file` | Wrong path or file not on UE5 host | Verify path, use shared drive |
| `Invalid root path` | Destination path doesn't start with `/Game/` | Correct the `destination_path` |
| `FBX: Bone name mismatch` | Wrong skeleton used | Remove `skeleton` argument to auto-create |
| `Import interrupted by user` | Dialog appeared (automated=False) | Ensure `task.automated=True` |
| `Python: AttributeError` | UE5 Python API changed | Use `ue_list_uclass_methods` to check API |
| `Module not found` | Plugin disabled | Enable the plugin in the UE5 Plugin Manager |

## Recovery Actions

### Re-run import with explicit parameters
```python
# If auto-detection failed, be explicit:
import_texture(
    file_path="C:/Textures/T_Rock_n.tga",
    destination_path="/Game/Textures/",
    texture_type="normal",  # explicit — don't rely on auto
)
```

### Clear partial asset and retry
```python
ue_exec_safe(code="""
import unreal
path = "/Game/Meshes/SM_BrokenAsset"
if unreal.EditorAssetLibrary.does_asset_exist(path):
    unreal.EditorAssetLibrary.delete_asset(path)
    _result["deleted"] = True
else:
    _result["deleted"] = False
""")
```

### Check file path on UE5 host
```python
ue_exec_safe(code="""
import os
test_paths = [
    "C:/Exports/SK_Bastila.fbx",
    "D:/KotOR/Exports/SK_Bastila.fbx",
]
for p in test_paths:
    _result[p] = os.path.exists(p)
""")
```

## Post-conditions

After successful diagnosis:
- Root cause is identified (file, connection, path, or API issue).
- Recovery action is clear.
- If re-import was attempted, validate with `ue_describe_asset`.

## Example Prompts

- "The import_texture call failed — diagnose why"
- "Why did `import_skeletal_mesh` return no paths?"
- "Check the UE5 output log for import errors"
- "The batch import had 3 failures — what went wrong?"
