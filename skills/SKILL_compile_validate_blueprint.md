# SKILL: Compile & Validate Blueprint

**Category:** Blueprint  
**Version:** 1.0  
**Added:** 2026-04-16  

## Description

Compile a Blueprint asset after modifications, validate that it compiled
without errors, report any warnings, and provide a log tail for diagnosis.
This skill should be called after **every Blueprint modification** to ensure
the editor state is consistent.

## Required Tools

| Tool | Module | Purpose |
|---|---|---|
| `compile_blueprint` | `blueprint_tools` | Trigger Blueprint compilation |
| `ue_describe_asset` | `reflection_tools` | Confirm asset exists and class |
| `get_recent_output_log` | `reflection_tools` | Read compilation output |
| `ue_exec_transact` | `exec_substrate` | Transaction-safe compile wrapper |
| `ue_exec_safe` | `exec_substrate` | Diagnostic Python execution |

## Pre-conditions

- [ ] The Blueprint asset exists at the specified Content Browser path.
- [ ] All referenced assets (parent classes, interfaces, component meshes)
      exist in the project.
- [ ] Any node graph modifications have been saved (or use `ue_exec_transact`
      which saves automatically).

## Compile Steps

### Step 1 — Verify Blueprint Exists
```python
ue_describe_asset(asset_path="/Game/Blueprints/BP_MyCharacter")
# Check: exists=true, class_name="Blueprint"
```

### Step 2 — Compile
```python
compile_blueprint(blueprint_name="BP_MyCharacter")
```

### Step 3 — Check the Log
```python
get_recent_output_log(filter_category="LogBlueprint", lines=100)
get_recent_output_log(filter_category="Error", lines=50)
```

### Step 4 — Verify No Errors via exec
```python
ue_exec_safe(code="""
import unreal
bp_path = "/Game/Blueprints/BP_MyCharacter"
bp = unreal.load_asset(bp_path)
if bp is None:
    _errors.append(f"Blueprint not found: {bp_path}")
else:
    status = bp.get_editor_property("status")
    _result["status"] = str(status)
    _result["class_name"] = bp.get_class().get_name()
    # BS_UpToDate means compiled OK, BS_Dirty or BS_Error means failed
    _result["is_compiled"] = "UpToDate" in str(status)
""", stage_name="blueprint_compile_check")
```

## Post-conditions

After successful compilation:
- `result.outputs.is_compiled = true`
- `result.outputs.status` contains `"UpToDate"`
- `get_recent_output_log(filter_category="Error")` returns no blueprint errors

## Failure Modes

| Symptom | Cause | Fix |
|---|---|---|
| `status: "BS_Error"` | Unconnected pins or missing references | Read the log for specific node errors |
| `"Node not found"` in log | A referenced function/variable was deleted | Check with `find_blueprint_nodes` |
| `"Unresolved pin"` | Pin type mismatch | Reconnect with correct type |
| Blueprint compiles but behaves wrong | Logic error, not compile error | Add debug print nodes and re-run |
| `"Blueprint not found"` | Wrong path or Blueprint not yet created | Check with `ue_describe_asset` first |
| `"parent class not found"` | Parent Blueprint deleted or renamed | Use `set_blueprint_parent_class` or recreate |

## Transaction-Safe Compile Pattern

For modifications that should be one undo step:
```python
ue_exec_transact(
    code="""
import unreal
bp = unreal.load_asset("/Game/Blueprints/BP_MyCharacter")
# ... make changes ...
unreal.EditorAssetLibrary.save_asset(bp.get_path_name())
_result["saved"] = True
""",
    transaction_name="Add Health variable to BP_MyCharacter"
)
# Then compile:
compile_blueprint(blueprint_name="BP_MyCharacter")
# Then validate:
get_recent_output_log(filter_category="LogBlueprint", lines=50)
```

## Full Validation Script

```python
ue_exec_safe(code="""
import unreal

bp_path = "/Game/Blueprints/BP_MyCharacter"

# 1. Check exists
if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
    raise RuntimeError(f"Blueprint not found: {bp_path}")

# 2. Load and check status
bp = unreal.load_asset(bp_path)
status = bp.get_editor_property("status") if bp else None
_result["bp_path"]     = bp_path
_result["status"]      = str(status)
_result["is_compiled"] = status is not None and "UpToDate" in str(status)

# 3. Check for compile errors in object
if not _result["is_compiled"]:
    _errors.append(f"Blueprint status is {status} — not UpToDate")
""", stage_name="blueprint_validation")
```

## Example Prompts

- "Compile `BP_PlayerCharacter` and check for errors"
- "After adding the variable, compile and validate the Blueprint"
- "Is `BP_EnemyAI` compiled? Check the output log for Blueprint errors"
- "Validate all Blueprints in `/Game/Dantooine/Blueprints/`"
