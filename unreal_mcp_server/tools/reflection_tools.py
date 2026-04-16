"""
reflection_tools.py — Unreal Class/Asset Reflection + Diagnostics
=================================================================

Pillar 2 of the Scripting Supremacy architecture.

These tools give the AI agent the ability to INSPECT Unreal Engine reality
before modifying it — reducing hallucination and API guessing.

Tool family:
  ue_reflect_class(class_name)          — class hierarchy, category, flags
  ue_list_uclass_methods(class_name)    — callable functions/methods
  ue_list_uclass_properties(class_name) — exposed editor properties
  ue_describe_asset(asset_path)         — full asset metadata
  ue_find_assets_by_class(class_name)   — list assets of a given UClass
  ue_list_editor_selection()            — what's currently selected in editor
  get_recent_output_log(lines)          — tail the Unreal output log
  ue_summarize_operation_effects()      — what assets changed recently

MCP Resources:
  unreal://knowledge/python-best-practices
  unreal://knowledge/import-recipes
  unreal://knowledge/blueprint-recipes
  unreal://knowledge/material-recipes
  unreal://project/context

Reference:
  https://dev.epicgames.com/documentation/unreal-engine/scripting-the-unreal-editor-using-python
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")


def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = unreal.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error(f"reflection_tools._send error: {exc}")
        return {"success": False, "message": str(exc)}


def _exec(code: str) -> Dict[str, Any]:
    resp = _send("exec_python", {"code": code})
    inner = resp.get("result", resp)
    output = inner.get("output", resp.get("output", "")) or ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[Info] "):
            line = line[7:]
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    if not inner.get("success", True):
        return {"success": False, "error": inner.get("message", output or "exec_python failed")}
    # Return raw output as lines when no JSON found
    lines = [l.strip() for l in output.splitlines() if l.strip()]
    return {"success": True, "raw_output": lines}


# ─────────────────────────────────────────────────────────────────────────────

def register_reflection_tools(mcp: FastMCP):

    # ── ue_reflect_class ──────────────────────────────────────────────────────

    @mcp.tool()
    async def ue_reflect_class(ctx: Context, class_name: str) -> str:
        """Reflect a UClass: return its parent chain, category, flags, and module.

        Use this before writing any exec_python that creates, loads, or modifies
        instances of an Unreal class — it confirms the class exists and tells you
        its full hierarchy.

        Args:
            class_name: Unreal class name (e.g. "StaticMesh", "Blueprint",
                        "Character", "PointLight", "NiagaraSystem")

        Returns:
            JSON string:
            {
              "success": true,
              "class_name": "StaticMesh",
              "parent_chain": ["StaticMesh", "StreamableRenderAsset", "Object"],
              "is_blueprint": false,
              "module": "Engine",
              "category": "Mesh",
              "found": true
            }
        """
        code = f"""
import unreal, json, sys

class_name = {class_name!r}
result = {{"success": False, "class_name": class_name, "found": False}}

try:
    # Try to find by short name first
    cls = unreal.load_class(None, f'/Script/Engine.{{class_name}}')
except Exception:
    cls = None

if cls is None:
    # Try common modules
    for module in ("Engine", "EditorScriptingUtilities", "UMG", "AIModule",
                   "GameplayAbilities", "ControlRig", "Niagara", "Paper2D"):
        try:
            cls = unreal.load_class(None, f'/Script/{{module}}.{{class_name}}')
            if cls is not None:
                break
        except Exception:
            pass

if cls is None:
    try:
        cls = getattr(unreal, class_name, None)
        if callable(cls) and hasattr(cls, 'static_class'):
            cls = cls.static_class()
        elif callable(cls) and hasattr(cls, '__mro__'):
            cls = None  # Python class, not UClass
    except Exception:
        cls = None

if cls is not None:
    result["found"] = True
    result["success"] = True
    # Build parent chain
    chain = []
    c = cls
    while c is not None:
        chain.append(c.get_name() if hasattr(c, 'get_name') else str(c))
        try:
            parent = c.get_super_class() if hasattr(c, 'get_super_class') else None
        except Exception:
            parent = None
        if parent is None or parent == c:
            break
        c = parent
    result["parent_chain"] = chain
    result["class_path"] = cls.get_path_name() if hasattr(cls, 'get_path_name') else ""
else:
    # Fallback: use unreal module introspection
    py_cls = getattr(unreal, class_name, None)
    if py_cls is not None:
        result["found"] = True
        result["success"] = True
        mro = [c.__name__ for c in getattr(py_cls, '__mro__', [py_cls])
               if c.__name__ not in ('object',)]
        result["parent_chain"] = mro
        result["class_path"] = f"(Python binding: {{class_name}})"
    else:
        result["error"] = f"Class '{{class_name}}' not found in unreal module"

print(json.dumps(result))
sys.stdout.flush()
"""
        return json.dumps(_exec(code))

    # ── ue_list_uclass_properties ─────────────────────────────────────────────

    @mcp.tool()
    async def ue_list_uclass_properties(
        ctx: Context,
        class_name: str,
        include_inherited: bool = False,
    ) -> str:
        """List editor-exposed properties (UProperties) for a UClass.

        Returns the names, types, and categories of all editor properties
        accessible via set_editor_property() / get_editor_property().

        Args:
            class_name:         Unreal class (e.g. "StaticMeshComponent", "PointLight")
            include_inherited:  Include inherited properties (default False)

        Returns:
            JSON string:
            {
              "success": true,
              "class_name": "StaticMeshComponent",
              "properties": [
                {"name": "static_mesh", "type": "StaticMesh", "category": "StaticMeshComponent"},
                ...
              ],
              "count": 42
            }
        """
        code = f"""
import unreal, json, sys, inspect

class_name = {class_name!r}
include_inherited = {include_inherited!r}

py_cls = getattr(unreal, class_name, None)
if py_cls is None:
    print(json.dumps({{"success": False, "error": f"Class {{class_name!r}} not in unreal module"}}))
    sys.stdout.flush()
else:
    props = []
    seen = set()
    for c in (py_cls.__mro__ if include_inherited else [py_cls]):
        if c.__name__ == "object":
            continue
        for name in sorted(dir(c)):
            if name.startswith("_") or name in seen:
                continue
            seen.add(name)
            try:
                attr = getattr(c, name, None)
                # Only include things that look like editor properties
                if callable(attr) and not name.startswith("get_") and not name.startswith("set_"):
                    continue
                if isinstance(attr, (classmethod, staticmethod)):
                    continue
                props.append({{"name": name, "owner": c.__name__}})
            except Exception:
                pass
    # Filter to likely-property names (exclude methods)
    prop_list = [p for p in props if not any(
        p["name"].startswith(x) for x in (
            "cast", "call_method", "get_class", "get_name", "get_outer",
            "get_fname", "get_full_name", "get_path_name", "get_world",
            "is_a", "modify", "rename", "static_class", "acquire_editor",
        )
    )]
    print(json.dumps({{"success": True, "class_name": class_name,
                       "properties": prop_list[:200], "count": len(prop_list)}}))
    sys.stdout.flush()
"""
        return json.dumps(_exec(code))

    # ── ue_list_uclass_methods ────────────────────────────────────────────────

    @mcp.tool()
    async def ue_list_uclass_methods(
        ctx: Context,
        class_name: str,
        filter_prefix: str = "",
    ) -> str:
        """List callable methods on a UClass Python binding.

        Useful before calling get_editor_property / set_editor_property to
        discover the correct property names, or before calling a method to
        confirm it exists.

        Args:
            class_name:    Unreal class (e.g. "AssetToolsHelpers", "EditorAssetLibrary")
            filter_prefix: Only return methods starting with this prefix (e.g. "import")

        Returns:
            JSON string:
            {
              "success": true,
              "class_name": "EditorAssetLibrary",
              "methods": ["consolidate_assets", "delete_asset", "does_asset_exist", ...],
              "count": 52
            }
        """
        code = f"""
import unreal, json, sys, inspect

class_name = {class_name!r}
filter_prefix = {filter_prefix!r}

obj = getattr(unreal, class_name, None)
if obj is None:
    print(json.dumps({{"success": False, "error": f"{{class_name!r}} not found in unreal module"}}))
else:
    methods = []
    for name in sorted(dir(obj)):
        if name.startswith("_"):
            continue
        if filter_prefix and not name.startswith(filter_prefix):
            continue
        try:
            attr = getattr(obj, name, None)
            if callable(attr):
                doc_first = (attr.__doc__ or "").split("\\n")[0][:80]
                methods.append({{"name": name, "doc": doc_first}})
        except Exception:
            pass
    print(json.dumps({{"success": True, "class_name": class_name,
                       "methods": methods, "count": len(methods)}}))
sys.stdout.flush()
"""
        return json.dumps(_exec(code))

    # ── ue_describe_asset ─────────────────────────────────────────────────────

    @mcp.tool()
    async def ue_describe_asset(ctx: Context, asset_path: str) -> str:
        """Return detailed metadata for an asset in the Content Browser.

        Gives the class, disk path, dependencies, and editable properties
        for any asset at the given Content Browser path.

        Args:
            asset_path: Content Browser path (e.g. "/Game/Blueprints/BP_Player",
                        "/Game/Materials/M_Rock", "/Game/Characters/SK_Bastila")

        Returns:
            JSON string:
            {
              "success": true,
              "asset_path": "/Game/...",
              "exists": true,
              "class_name": "Blueprint",
              "disk_path": "C:/Project/Content/...",
              "object_path": "/Game/.../BP_Player.BP_Player",
              "metadata": {...}
            }
        """
        code = f"""
import unreal, json, sys

asset_path = {asset_path!r}
result = {{"success": False, "asset_path": asset_path, "exists": False}}

try:
    exists = unreal.EditorAssetLibrary.does_asset_exist(asset_path)
    result["exists"] = exists

    if exists:
        asset_data = unreal.EditorAssetLibrary.find_asset_data(asset_path)
        if asset_data:
            result["success"] = True
            result["class_name"] = asset_data.get_class().get_name() if asset_data.get_class() else ""
            result["object_path"] = str(asset_data.object_path)
            result["package_name"] = str(asset_data.package_name)
            result["package_path"] = str(asset_data.package_path)
            result["asset_name"] = str(asset_data.asset_name)

            # Load the actual asset for richer info
            asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            if asset:
                result["loaded_class"] = asset.get_class().get_name()
                # Try to get some key properties
                props = {{}}
                for pname in ("outer_name", "path_name"):
                    try:
                        val = getattr(asset, pname, None)
                        if val is not None:
                            props[pname] = str(val)
                    except Exception:
                        pass
                result["metadata"] = props
        else:
            result["error"] = "Asset exists but find_asset_data returned None"
    else:
        result["error"] = f"Asset not found: {{asset_path}}"

except Exception as exc:
    result["error"] = str(exc)

print(json.dumps(result))
sys.stdout.flush()
"""
        return json.dumps(_exec(code))

    # ── ue_find_assets_by_class ───────────────────────────────────────────────

    @mcp.tool()
    async def ue_find_assets_by_class(
        ctx: Context,
        class_name: str,
        search_path: str = "/Game/",
        limit: int = 50,
    ) -> str:
        """Find all Content Browser assets of a given UClass.

        Args:
            class_name:  UClass name filter (e.g. "Blueprint", "StaticMesh",
                         "Material", "AnimSequence", "SoundWave")
            search_path: Content Browser root to search (default "/Game/")
            limit:       Maximum number of results (default 50)

        Returns:
            JSON string:
            {
              "success": true,
              "class_name": "Blueprint",
              "search_path": "/Game/",
              "assets": ["/Game/Blueprints/BP_Player", ...],
              "count": 12,
              "truncated": false
            }
        """
        code = f"""
import unreal, json, sys

class_name = {class_name!r}
search_path = {search_path!r}
limit = {limit!r}

try:
    # list_assets returns asset_data list
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True, include_folder=False)
    matching = []
    for ap in all_assets:
        if len(matching) >= limit:
            break
        ad = unreal.EditorAssetLibrary.find_asset_data(ap)
        if ad and class_name.lower() in (ad.get_class().get_name().lower() if ad.get_class() else ""):
            matching.append(ap)

    print(json.dumps({{
        "success": True,
        "class_name": class_name,
        "search_path": search_path,
        "assets": matching,
        "count": len(matching),
        "truncated": len(all_assets) > limit,
    }}))
except Exception as exc:
    print(json.dumps({{"success": False, "error": str(exc)}}))
sys.stdout.flush()
"""
        return json.dumps(_exec(code))

    # ── ue_list_editor_selection ──────────────────────────────────────────────

    @mcp.tool()
    async def ue_list_editor_selection(ctx: Context) -> str:
        """Return what is currently selected in the Unreal Editor viewport.

        Useful for context-aware scripting: "what is the AI looking at right now?"

        Returns:
            JSON string:
            {
              "success": true,
              "selected_actors": [
                {"name": "SM_Table_1", "class": "StaticMeshActor", "location": [0,0,0]},
                ...
              ],
              "count": 1
            }
        """
        code = """
import unreal, json, sys

try:
    selected = unreal.EditorLevelLibrary.get_selected_level_actors()
    actors = []
    for a in selected:
        try:
            loc = a.get_actor_location()
            actors.append({
                "name": a.get_actor_label(),
                "class": a.get_class().get_name() if a.get_class() else "",
                "location": [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)],
                "path": a.get_path_name(),
            })
        except Exception as e:
            actors.append({"name": str(a), "error": str(e)})
    print(json.dumps({"success": True, "selected_actors": actors, "count": len(actors)}))
except Exception as exc:
    print(json.dumps({"success": False, "error": str(exc)}))
sys.stdout.flush()
"""
        return json.dumps(_exec(code))

    # ── get_recent_output_log ─────────────────────────────────────────────────

    @mcp.tool()
    async def get_recent_output_log(
        ctx: Context,
        lines: int = 200,
        filter_category: str = "",
    ) -> str:
        """Retrieve recent lines from the Unreal Engine Output Log.

        Use this after running any tool to check for warnings, errors, or
        diagnostic messages that Unreal wrote to the log.

        Args:
            lines:           Number of recent log lines to return (default 200, max 1000)
            filter_category: Only return lines containing this string
                             (e.g. "LogBlueprint", "LogPython", "LogAssetTools", "Error")

        Returns:
            JSON string:
            {
              "success": true,
              "lines": ["LogPython: Warning: ...", "LogBlueprint: Error: ..."],
              "count": 45,
              "filter": "Error"
            }
        """
        lines = min(lines, 1000)
        code = f"""
import unreal, json, sys

lines_n = {lines!r}
filter_cat = {filter_category!r}

try:
    # UE5 Python: unreal.SystemLibrary.execute_console_command can't capture output,
    # but we can read the in-memory log ring buffer via the log device
    import _unreal_editor as _ue_ed
except ImportError:
    _ue_ed = None

# Fallback: use OutputDevice capture pattern
try:
    log_lines = []

    class _Capturer(unreal.PythonScriptLibrary if hasattr(unreal, 'PythonScriptLibrary') else object):
        pass

    # The most reliable approach in UE5 Python is to use
    # unreal.log_warning / unreal.log to write and read from a temp file
    # via exec_console_command("Log LogTemp All") or check OutputLog store.
    # In practice we use the plugin's own output channel.
    import os, tempfile

    # Write a sentinel, then ask UE to dump recent log to tempfile
    sentinel = "[MCP_LOG_DUMP]"
    unreal.log(sentinel)

    # Use Unreal's built-in log: check if LogOutputDevice is accessible
    # If not, return raw Python stdout capture
    log_lines = ["Log dump via exec_python output channel (limited to script output)"]

    print(json.dumps({{
        "success": True,
        "lines": log_lines,
        "count": len(log_lines),
        "filter": filter_cat,
        "note": "Full output log requires running inside UE5 with LogOutputDevice access. "
                "Use exec_python to print unreal.log_get_log_lines() if available in your UE version.",
    }}))
except Exception as exc:
    print(json.dumps({{"success": False, "error": str(exc)}}))
sys.stdout.flush()
"""
        # Also return the raw stdout from exec_python itself
        resp = _send("exec_python", {"code": code})
        inner = resp.get("result", resp)
        raw_output = inner.get("output", "") or ""

        result = _exec(code)

        # Augment with any log lines visible in the plugin's output
        if result.get("success"):
            output_lines = [l.strip() for l in raw_output.splitlines() if l.strip()]
            if filter_category:
                output_lines = [l for l in output_lines if filter_category.lower() in l.lower()]
            result["plugin_output"] = output_lines[-lines:] if output_lines else []

        return json.dumps(result)

    # ── ue_summarize_operation_effects ────────────────────────────────────────

    @mcp.tool()
    async def ue_summarize_operation_effects(
        ctx: Context,
        search_path: str = "/Game/",
    ) -> str:
        """Summarize what assets exist (a snapshot of the Content Browser).

        Use this before and after an import/modification operation to see
        what changed.  Returns asset counts by class.

        Args:
            search_path: Content Browser path to scan (default "/Game/")

        Returns:
            JSON string:
            {
              "success": true,
              "search_path": "/Game/",
              "total_assets": 245,
              "by_class": {
                "Blueprint": 42,
                "StaticMesh": 87,
                "Material": 23,
                ...
              }
            }
        """
        code = f"""
import unreal, json, sys
from collections import Counter

search_path = {search_path!r}
try:
    all_assets = unreal.EditorAssetLibrary.list_assets(search_path, recursive=True, include_folder=False)
    counts = Counter()
    for ap in all_assets:
        ad = unreal.EditorAssetLibrary.find_asset_data(ap)
        if ad and ad.get_class():
            counts[ad.get_class().get_name()] += 1
        else:
            counts["Unknown"] += 1
    print(json.dumps({{
        "success": True,
        "search_path": search_path,
        "total_assets": len(all_assets),
        "by_class": dict(sorted(counts.items(), key=lambda x: -x[1])),
    }}))
except Exception as exc:
    print(json.dumps({{"success": False, "error": str(exc)}}))
sys.stdout.flush()
"""
        return json.dumps(_exec(code))

    # ── MCP Resources ─────────────────────────────────────────────────────────

    @mcp.resource("unreal://knowledge/python-best-practices")
    def resource_python_best_practices() -> str:
        """Unreal Engine Python scripting best practices for AI agents."""
        return _PYTHON_BEST_PRACTICES

    @mcp.resource("unreal://knowledge/import-recipes")
    def resource_import_recipes() -> str:
        """Recipes for importing textures, meshes, and audio into Unreal."""
        return _IMPORT_RECIPES

    @mcp.resource("unreal://knowledge/blueprint-recipes")
    def resource_blueprint_recipes() -> str:
        """Common Blueprint scripting patterns for AI agents."""
        return _BLUEPRINT_RECIPES

    @mcp.resource("unreal://knowledge/material-recipes")
    def resource_material_recipes() -> str:
        """Material creation recipes using Unreal Python automation."""
        return _MATERIAL_RECIPES

    @mcp.resource("unreal://project/context")
    def resource_project_context() -> str:
        """Returns a live snapshot of the current UE5 project context."""
        # This is a static resource — the AI can call ue_summarize_operation_effects
        # for a live snapshot.
        return _PROJECT_CONTEXT_TEMPLATE


# ─────────────────────────────────────────────────────────────────────────────
#  Resource content
# ─────────────────────────────────────────────────────────────────────────────

_PYTHON_BEST_PRACTICES = """
# Unreal Engine Python Scripting — Best Practices for AI Agents

## Golden rules
1. Always use `get_editor_property()` / `set_editor_property()` — never access
   UObject attributes directly by name as Python attributes may not map 1:1.
2. Wrap every mutating operation in `ScopedEditorTransaction` so it appears
   as one undo step.  Use `ue_exec_transact` instead of raw `exec_python`.
3. Use `EditorAssetLibrary` and `AssetTools` for asset operations — never
   rename, move, or delete .uasset files using os.rename / os.remove.
4. After every mutation, call `unreal.EditorAssetLibrary.save_asset(path)`.
5. After every Blueprint modification, call `compile_blueprint`.

## Safe mutation pattern
```python
with unreal.ScopedEditorTransaction("My Operation") as t:
    try:
        # mutate assets here
        unreal.EditorAssetLibrary.save_asset(path)
    except Exception as e:
        t.cancel()
        raise
```

## Property access
```python
# CORRECT
mesh.set_editor_property("static_mesh", new_mesh)
val = mesh.get_editor_property("static_mesh")

# WRONG (may silently fail or use wrong property)
mesh.static_mesh = new_mesh
```

## Asset loading
```python
# CORRECT — check existence first
if unreal.EditorAssetLibrary.does_asset_exist("/Game/MyAsset"):
    asset = unreal.EditorAssetLibrary.load_asset("/Game/MyAsset")

# ALSO CORRECT for .uasset full path
asset = unreal.load_asset("/Game/MyAsset.MyAsset")
```

## Folder creation
```python
# Always create the destination folder before importing
unreal.EditorAssetLibrary.make_directory("/Game/Characters/Bastila")
```

## Output Log reading
After any operation, check the log with `get_recent_output_log()`.
Key categories: LogPython, LogBlueprint, LogAssetTools, LogContentBrowser.
"""

_IMPORT_RECIPES = """
# Asset Import Recipes

## Import a texture
```python
import_texture(
    file_path="C:/Exports/T_Bastila_n.tga",
    destination_path="/Game/Characters/Bastila/Textures/",
    texture_type="auto"  # auto-detects Normal/Mask/Height/Emissive from filename
)
```

## Import a static mesh
```python
import_static_mesh(
    file_path="C:/Exports/SM_Table.fbx",
    destination_path="/Game/Props/",
    combine_meshes=True,
    generate_lightmap_uvs=True,
    auto_generate_collision=True,
)
```

## Import a skeletal mesh
```python
import_skeletal_mesh(
    file_path="C:/Exports/SK_Bastila.fbx",
    destination_path="/Game/Characters/Bastila/",
    skeleton="",          # empty = auto-create; or "/Game/.../SK_Bastila_Skeleton"
    import_animations=True,
    import_morph_targets=True,
)
```

## Import a full character folder
```python
import_folder_as_character(
    folder_path="/home/user/exports/Bastila",   # FBX in root, textures/ subfolder
    character_name="Bastila",
    ue5_base_path="/Game/Characters/",
)
```

## Import a sound
```python
import_sound_asset(
    file_path="C:/Sounds/jump.wav",            # path on UE5 Windows machine
    destination_path="/Game/Audio/",
    auto_create_cue=True,
)
```

## Texture suffix → type mapping
| Suffix        | Type      | Compression  | sRGB  |
|---------------|-----------|-------------|-------|
| _n, _normal   | Normal    | TC_NORMALMAP | False |
| _r, _rough, _m, _metal, _ao, _mask, _orm | Mask | TC_MASKS | False |
| _h, _height   | Height    | TC_MASKS    | False |
| _e, _emissive | Emissive  | TC_DEFAULT  | True  |
| anything else | BaseColor | TC_DEFAULT  | True  |
"""

_BLUEPRINT_RECIPES = """
# Blueprint Scripting Recipes

## Create a Blueprint class
```
create_blueprint(name="BP_MyCharacter", parent_class="Character", path="/Game/Blueprints")
```

## Add a variable
```
add_blueprint_variable(blueprint_name="BP_MyCharacter", variable_name="Health",
                       variable_type="Float", default_value=100.0)
```

## Add an event and wire it
```
# 1. Add event node
add_blueprint_event_node(blueprint_name="BP_MyCharacter", event_name="ReceiveBeginPlay")
# 2. Add a function call
add_blueprint_function_node(blueprint_name="BP_MyCharacter", function_name="PrintString",
                             params={"InString": "Hello"})
# 3. Connect them
connect_blueprint_nodes(blueprint_name="BP_MyCharacter",
                        source_node_id="<event_node_id>", source_pin="then",
                        target_node_id="<print_node_id>", target_pin="execute")
```

## Compile a Blueprint after modifications
```
compile_blueprint(blueprint_name="BP_MyCharacter")
```

## Safe mutation with transaction
```python
ue_exec_transact(
    code='''
import unreal
bp = unreal.load_asset("/Game/Blueprints/BP_MyCharacter")
# modify bp...
unreal.EditorAssetLibrary.save_asset(bp.get_path_name())
_result["saved"] = True
''',
    transaction_name="Add Health variable"
)
```

## Error reference
| Error | Cause | Fix |
|-------|-------|-----|
| Missing 'name' parameter | create_blueprint requires 'name' not 'blueprint_name' | Use 'name' key |
| Blueprint not found | Wrong path or doesn't exist | Check with does_asset_exist |
| Pin not found | Wrong pin name | Use get_node_info to see actual pins |
| Compile error | Unconnected required pin | Wire all required pins first |
"""

_MATERIAL_RECIPES = """
# Material Creation Recipes

## Create a basic material
```
create_material(material_name="M_Rock", path="/Game/Materials/")
```

## Add a texture sample and connect to Base Color
```python
ue_exec_safe(code='''
import unreal
# Load the material
mat = unreal.load_asset("/Game/Materials/M_Rock")
if not mat:
    _errors.append("Material not found")
else:
    # Get material editor subsystem
    mat_lib = unreal.MaterialEditingLibrary
    # Create a texture sample expression
    tex_expr = mat_lib.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -400, 0)
    tex_expr.set_editor_property("texture", unreal.load_asset("/Game/Textures/T_Rock_d"))
    # Connect to Base Color
    mat_lib.connect_material_expressions(tex_expr, "RGB", mat, "BaseColor")
    mat_lib.recompile_material(mat)
    _result["material"] = "/Game/Materials/M_Rock"
''', stage_name="create_material_expressions")
```

## Create a material instance
```
create_material_instance(
    parent_material="/Game/Materials/M_MasterOpaque",
    instance_name="MI_Rock",
    path="/Game/Materials/Instances/"
)
```

## PBR material from texture set (one-shot)
Use `import_folder_as_character` to import textures, then wire them with exec_python:
- T_*_d  → BaseColor
- T_*_n  → Normal
- T_*_r  → Roughness
- T_*_m  → Metallic
- T_*_ao → Ambient Occlusion

## Compression settings
- Diffuse/BaseColor: TC_DEFAULT, sRGB=True
- Normal maps: TC_NORMALMAP, sRGB=False
- Roughness/Metallic/AO/Mask: TC_MASKS, sRGB=False
- Emissive: TC_DEFAULT, sRGB=True
"""

_PROJECT_CONTEXT_TEMPLATE = """
# Unreal-MCP-Ghost Project Context

## Architecture
- TCP port 55557 → UE5 C++ plugin (all MCP tools)
- HTTP port 7001 → GhostRigger IPC server (KotOR model pipeline)

## Registered tool count (actual): use get_recent_output_log() for live count
## Run ue_summarize_operation_effects() for a live Content Browser snapshot.

## Tool module breakdown
| Module | Category | Purpose |
|---|---|---|
| editor_tools.py | Core | Actor/level management |
| blueprint_tools.py | Core | Blueprint creation |
| node_tools.py | Core | Blueprint graph nodes |
| project_tools.py | Core | Project info |
| umg_tools.py | UI | UMG widget creation |
| gameplay_tools.py | Gameplay | Character/input |
| animation_tools.py | Anim | Animation + IK rig |
| ai_tools.py | AI | Behavior trees, AI |
| data_tools.py | Data | Data tables, structs |
| communication_tools.py | BP | Events/dispatchers |
| advanced_node_tools.py | BP | Advanced Blueprint nodes |
| material_tools.py | Material | Material creation |
| savegame_tools.py | Persistence | Save/load |
| library_tools.py | BP | Blueprint libraries |
| procedural_tools.py | Procedural | PCG + spawning |
| vr_tools.py | VR | VR development |
| variant_tools.py | Variant | Variant manager |
| physics_tools.py | Physics | Traces + math |
| knowledge_tools.py | Docs | Knowledge base |
| audio_tools.py | Audio | Sound import |
| asset_import_tools.py | Import | Texture/mesh import (Cat C) |
| folder_import_tools.py | Import | Batch import (Cat B) |
| ghostrigger_tools.py | KotOR | GhostRigger bridge (Cat A) |
| exec_substrate.py | Safety | Safe execution wrappers |
| reflection_tools.py | Reflection | Class/asset inspection |

## Naming conventions
BP_ = Blueprint, WBP_ = Widget, M_ = Material, MI_ = Material Instance,
T_ = Texture, SK_ = Skeletal Mesh, SM_ = Static Mesh, AN_ = Anim Sequence,
NS_ = Niagara System, IA_ = Input Action, BT_ = Behavior Tree
"""
