"""
niagara_tools.py - Niagara-first VFX inspection and recipe support.

These tools intentionally avoid Blueprint actor-particle workarounds.  They give
agents a safe way to inspect Niagara assets, apply simple asset-level settings,
and generate effect specs that can be handed to a native Niagara authoring
command or implemented manually in the Niagara editor.

Reference baseline:
  Epic UE 5.6 Python API: NiagaraSystem, NiagaraPythonEmitter,
  NiagaraPythonScriptModuleInput, NiagaraComponent.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")


def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection

    try:
        ue = get_unreal_connection()
        if not ue:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        return ue.send_command(command, params) or {"success": False, "message": "No response"}
    except Exception as exc:
        logger.error(f"niagara_tools._send({command}): {exc}")
        return {"success": False, "message": str(exc)}


def _exec_python(code: str) -> Dict[str, Any]:
    return _send("exec_python", {"code": code})


def _parse_exec_json(raw: Dict[str, Any]) -> Dict[str, Any]:
    inner = raw.get("result", raw)
    output = inner.get("output", "") or ""
    parsed = None
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[Info] "):
            line = line[7:]
        if line.startswith("{") and line.endswith("}"):
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
    if parsed is not None:
        return parsed
    if inner.get("success") is False:
        return {"success": False, "message": inner.get("message", output or "exec_python failed")}
    return {"success": True, "raw_output": [l.strip() for l in output.splitlines() if l.strip()]}


def _result(
    *,
    success: bool,
    tool: str,
    t0: float,
    message: str,
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": "complete" if success else "error",
        "message": message,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "meta": {"tool": tool, "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _asset_object_path(package_path: str) -> str:
    if "." in package_path.rsplit("/", 1)[-1]:
        return package_path
    return f"{package_path}.{package_path.rsplit('/', 1)[-1]}"


BLACKHOLE_INFLOW_SPEC: Dict[str, Any] = {
    "effect_name": "NS_BlackHoleOrbInflow",
    "intent": "Looping sphere of small circular particles pulled aggressively into a center point.",
    "simulation_target": "GPU preferred for high count; CPU acceptable while authoring/debugging.",
    "fixed_bounds": {"min": [-900.0, -900.0, -900.0], "max": [900.0, 900.0, 900.0]},
    "emitters": [
        {
            "name": "OrbInflow",
            "renderer": {
                "type": "SpriteRenderer",
                "material": "Additive unlit circle/orb material driven by Particle Color",
                "alignment": "FaceCamera",
            },
            "emitter_update": [
                {"module": "Emitter State", "loop": "Infinite"},
                {"module": "Spawn Rate", "rate": 140.0},
            ],
            "particle_spawn": [
                {"module": "Initialize Particle", "lifetime": [0.45, 0.9], "sprite_size": [8.0, 18.0]},
                {"module": "Shape Location", "shape": "Sphere", "radius": 650.0, "surface_only": True},
                {"module": "Color", "value": [0.65, 0.15, 1.0, 1.0]},
            ],
            "particle_update": [
                {"module": "Point Attraction Force", "position": [0.0, 0.0, 0.0], "strength": 9500.0, "radius": 900.0},
                {"module": "Vortex Force", "amount": 1800.0, "origin_pull_strength": 2500.0},
                {"module": "Drag", "drag": 0.08},
                {"module": "Scale Color", "alpha_curve": "0 -> 1 quickly, hold, then 0 near death"},
                {"module": "Scale Sprite Size", "curve": "1.0 -> 0.35 over normalized age"},
            ],
        }
    ],
    "notes": [
        "Do not implement this by spawning Blueprint actors per particle.",
        "Use a single Niagara system spawned by BP_BlackHoleFX or a NiagaraComponent.",
        "If Python cannot edit the Niagara stack, add native C++ bridge commands for stack modules and renderer properties.",
    ],
}


def register_niagara_tools(mcp: FastMCP):
    @mcp.tool()
    async def niagara_validate_authoring_support(ctx: Context) -> Dict[str, Any]:
        """Probe available Niagara Python/editor APIs before native authoring work."""
        t0 = time.monotonic()
        code = """
import unreal, json, traceback
out = {
    "success": True,
    "python_symbols": {},
    "uclasses": {},
    "recommendation": "native_bridge_required",
    "warnings": [],
}
try:
    for name in (
        "NiagaraSystem",
        "NiagaraEmitter",
        "NiagaraComponent",
        "NiagaraFunctionLibrary",
        "NiagaraPythonEmitter",
        "NiagaraPythonScriptModuleInput",
        "NiagaraEditorSubsystem",
        "NiagaraSystemFactoryNew",
        "AssetToolsHelpers",
    ):
        out["python_symbols"][name] = bool(hasattr(unreal, name))

    for path in (
        "/Script/Niagara.NiagaraSystem",
        "/Script/Niagara.NiagaraEmitter",
        "/Script/Niagara.NiagaraComponent",
        "/Script/Niagara.NiagaraFunctionLibrary",
        "/Script/NiagaraEditor.NiagaraSystemFactoryNew",
        "/Script/NiagaraEditor.NiagaraEmitterFactoryNew",
    ):
        try:
            cls = unreal.load_class(None, path)
            out["uclasses"][path] = bool(cls)
        except Exception as exc:
            out["uclasses"][path] = False
            out["warnings"].append(f"Could not load {path}: {exc}")

    stack_editing_symbols = (
        out["python_symbols"].get("NiagaraEditorSubsystem", False)
        and out["python_symbols"].get("NiagaraPythonEmitter", False)
        and out["python_symbols"].get("NiagaraPythonScriptModuleInput", False)
    )
    if stack_editing_symbols:
        out["recommendation"] = "python_probe_then_native_bridge"
        out["warnings"].append(
            "Niagara Python stack symbols are present; verify live stack mutation before relying on them."
        )
    else:
        out["warnings"].append(
            "Niagara Python stack authoring symbols are incomplete; implement emitter/module/renderer authoring in the C++ bridge."
        )
except Exception:
    out["success"] = False
    out["message"] = traceback.format_exc()
print(json.dumps(out))
"""
        parsed = _parse_exec_json(_exec_python(code))
        if not parsed.get("success"):
            return _result(
                success=False,
                tool="niagara_validate_authoring_support",
                t0=t0,
                message="Niagara authoring support probe failed",
                errors=[parsed.get("message", str(parsed))],
            )
        return _result(
            success=True,
            tool="niagara_validate_authoring_support",
            t0=t0,
            message="Niagara authoring support probed",
            outputs=parsed,
            warnings=parsed.get("warnings", []),
        )

    @mcp.tool()
    async def niagara_find_systems(
        ctx: Context,
        search: str = "",
        root_path: str = "/Game",
        limit: int = 50,
        page: int = 1,
    ) -> Dict[str, Any]:
        """Find Niagara System and Emitter assets through the Asset Registry."""
        t0 = time.monotonic()
        code = f"""
import unreal, json
search = {search!r}.lower()
root_path = {root_path!r}
limit = max(1, int({limit}))
page = max(1, int({page}))
ar = unreal.AssetRegistryHelpers.get_asset_registry()
assets = ar.get_assets_by_paths([root_path], recursive=True)
rows = []
for asset in assets:
    cls = str(asset.asset_class_path.asset_name)
    name = str(asset.asset_name)
    package = str(asset.package_name)
    if cls not in ("NiagaraSystem", "NiagaraEmitter"):
        continue
    if search and search not in name.lower() and search not in package.lower():
        continue
    rows.append({{"name": name, "path": package, "class": cls}})
rows.sort(key=lambda r: (r["class"], r["path"]))
start = (page - 1) * limit
print(json.dumps({{
    "success": True,
    "total": len(rows),
    "page": page,
    "limit": limit,
    "assets": rows[start:start + limit],
}}))
"""
        parsed = _parse_exec_json(_exec_python(code))
        if not parsed.get("success"):
            return _result(success=False, tool="niagara_find_systems", t0=t0, message="Niagara search failed", errors=[parsed.get("message", str(parsed))])
        return _result(success=True, tool="niagara_find_systems", t0=t0, message="Niagara assets found", outputs=parsed)

    @mcp.tool()
    async def niagara_create_system(
        ctx: Context,
        system_name: str,
        folder_path: str = "/Game/VFX",
        overwrite: bool = False,
        save: bool = True,
    ) -> Dict[str, Any]:
        """Create an empty Niagara System asset when the UE editor factory is available."""
        t0 = time.monotonic()
        safe_folder = folder_path.rstrip("/") or "/Game/VFX"
        package_path = f"{safe_folder}/{system_name}"
        native = _send(
            "niagara_create_system",
            {
                "system_name": system_name,
                "folder_path": safe_folder,
                "overwrite": overwrite,
                "save": save,
            },
        )
        if native.get("status") == "success":
            outputs = native.get("result", native)
            return _result(
                success=True,
                tool="niagara_create_system",
                t0=t0,
                message=outputs.get("message", "Niagara system created through native bridge"),
                outputs=outputs,
                warnings=[outputs.get("note", "")] if outputs.get("note") else [],
            )
        native_error = native.get("error") or native.get("message", "")
        if native_error and "Unknown command" not in native_error and "Not connected" not in native_error:
            return _result(
                success=False,
                tool="niagara_create_system",
                t0=t0,
                message="Native Niagara system creation failed",
                errors=[native_error],
            )

        code = f"""
import unreal, json, traceback
out = {{"success": False, "path": {package_path!r}, "warnings": []}}
try:
    system_name = {system_name!r}
    folder_path = {safe_folder!r}
    package_path = {package_path!r}
    if not hasattr(unreal, "NiagaraSystemFactoryNew"):
        out["message"] = "NiagaraSystemFactoryNew is not exposed to this editor Python environment"
        out["recommendation"] = "Implement niagara_create_system in the native C++ bridge for this engine build"
    elif unreal.EditorAssetLibrary.does_asset_exist(package_path) and not {bool(overwrite)!r}:
        out["success"] = True
        out["created"] = False
        out["message"] = "Asset already exists"
    else:
        if not unreal.EditorAssetLibrary.does_directory_exist(folder_path):
            unreal.EditorAssetLibrary.make_directory(folder_path)
        if unreal.EditorAssetLibrary.does_asset_exist(package_path) and {bool(overwrite)!r}:
            unreal.EditorAssetLibrary.delete_asset(package_path)
        factory = unreal.NiagaraSystemFactoryNew()
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        asset = asset_tools.create_asset(system_name, folder_path, unreal.NiagaraSystem, factory)
        if not asset:
            out["message"] = "AssetTools failed to create NiagaraSystem"
        else:
            out["success"] = True
            out["created"] = True
            out["asset_path"] = asset.get_path_name().split(".")[0]
            out["class"] = asset.get_class().get_name()
            if {bool(save)!r}:
                out["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False))
            out["warnings"].append("Created an empty Niagara System; emitter/module/renderer authoring still requires native bridge support.")
except Exception:
    out["message"] = traceback.format_exc()
print(json.dumps(out))
"""
        parsed = _parse_exec_json(_exec_python(code))
        if not parsed.get("success"):
            return _result(
                success=False,
                tool="niagara_create_system",
                t0=t0,
                message="Niagara system creation failed",
                errors=[parsed.get("message", str(parsed))],
                warnings=parsed.get("warnings", []),
            )
        return _result(
            success=True,
            tool="niagara_create_system",
            t0=t0,
            message=parsed.get("message", "Niagara system created"),
            outputs=parsed,
            warnings=parsed.get("warnings", []),
        )

    @mcp.tool()
    async def niagara_add_empty_emitter(
        ctx: Context,
        system_path: str,
        emitter_name: str = "MCP_Emitter",
        add_default_modules: bool = False,
        save: bool = True,
    ) -> Dict[str, Any]:
        """Add a native empty emitter handle to a Niagara System asset."""
        t0 = time.monotonic()
        native = _send(
            "niagara_add_empty_emitter",
            {
                "system_path": system_path,
                "emitter_name": emitter_name,
                "add_default_modules": add_default_modules,
                "save": save,
            },
        )
        if native.get("status") == "success":
            outputs = native.get("result", native)
            return _result(
                success=True,
                tool="niagara_add_empty_emitter",
                t0=t0,
                message="Niagara emitter added through native bridge",
                outputs=outputs,
            )
        message = native.get("error") or native.get("message", "Native Niagara emitter command failed")
        return _result(
            success=False,
            tool="niagara_add_empty_emitter",
            t0=t0,
            message="Niagara emitter add failed",
            errors=[message],
            warnings=["This operation requires the updated native C++ plugin; run Live Coding or restart the editor after rebuilding."],
        )

    @mcp.tool()
    async def niagara_set_system_user_parameter(
        ctx: Context,
        system_path: str,
        parameter_name: str,
        parameter_type: str = "float",
        value: Any = 0.0,
        save: bool = True,
    ) -> Dict[str, Any]:
        """Add or update a Niagara System exposed user parameter."""
        t0 = time.monotonic()
        native = _send(
            "niagara_set_system_user_parameter",
            {
                "system_path": system_path,
                "parameter_name": parameter_name,
                "parameter_type": parameter_type,
                "value": value,
                "save": save,
            },
        )
        if native.get("status") == "success":
            outputs = native.get("result", native)
            return _result(
                success=True,
                tool="niagara_set_system_user_parameter",
                t0=t0,
                message="Niagara user parameter set through native bridge",
                outputs=outputs,
            )
        message = native.get("error") or native.get("message", "Native Niagara user parameter command failed")
        return _result(
            success=False,
            tool="niagara_set_system_user_parameter",
            t0=t0,
            message="Niagara user parameter update failed",
            errors=[message],
            warnings=["This operation requires the updated native C++ plugin; run Live Coding or restart the editor after rebuilding."],
        )

    @mcp.tool()
    async def niagara_set_spawn_rate(
        ctx: Context,
        system_path: str,
        spawn_rate: float,
        emitter_name: str = "",
        emitter_id: str = "",
        save: bool = True,
    ) -> Dict[str, Any]:
        """Add or update an emitter SpawnRate module and set its particles-per-second value."""
        t0 = time.monotonic()
        native = _send(
            "niagara_set_spawn_rate",
            {
                "system_path": system_path,
                "emitter_name": emitter_name,
                "emitter_id": emitter_id,
                "spawn_rate": float(spawn_rate),
                "save": save,
            },
        )
        if native.get("status") == "success":
            outputs = native.get("result", native)
            return _result(
                success=True,
                tool="niagara_set_spawn_rate",
                t0=t0,
                message="Niagara spawn rate set through native bridge",
                outputs=outputs,
            )
        message = native.get("error") or native.get("message", "Native Niagara spawn-rate command failed")
        return _result(
            success=False,
            tool="niagara_set_spawn_rate",
            t0=t0,
            message="Niagara spawn rate update failed",
            errors=[message],
            warnings=["This operation requires the updated native C++ plugin; run Live Coding or restart the editor after rebuilding."],
        )

    @mcp.tool()
    async def niagara_add_sprite_renderer(
        ctx: Context,
        system_path: str,
        emitter_name: str = "",
        emitter_id: str = "",
        material_path: str = "",
        save: bool = True,
    ) -> Dict[str, Any]:
        """Add a Sprite Renderer to an existing Niagara emitter handle."""
        t0 = time.monotonic()
        native = _send(
            "niagara_add_sprite_renderer",
            {
                "system_path": system_path,
                "emitter_name": emitter_name,
                "emitter_id": emitter_id,
                "material_path": material_path,
                "save": save,
            },
        )
        if native.get("status") == "success":
            outputs = native.get("result", native)
            return _result(
                success=True,
                tool="niagara_add_sprite_renderer",
                t0=t0,
                message="Niagara sprite renderer added through native bridge",
                outputs=outputs,
            )
        message = native.get("error") or native.get("message", "Native Niagara sprite renderer command failed")
        return _result(
            success=False,
            tool="niagara_add_sprite_renderer",
            t0=t0,
            message="Niagara sprite renderer add failed",
            errors=[message],
            warnings=["This operation requires the updated native C++ plugin; run Live Coding or restart the editor after rebuilding."],
        )

    @mcp.tool()
    async def niagara_add_mesh_renderer(
        ctx: Context,
        system_path: str,
        static_mesh_path: str,
        emitter_name: str = "",
        emitter_id: str = "",
        material_path: str = "",
        save: bool = True,
    ) -> Dict[str, Any]:
        """Add a Mesh Renderer to an existing Niagara emitter handle."""
        t0 = time.monotonic()
        native = _send(
            "niagara_add_mesh_renderer",
            {
                "system_path": system_path,
                "static_mesh_path": static_mesh_path,
                "emitter_name": emitter_name,
                "emitter_id": emitter_id,
                "material_path": material_path,
                "save": save,
            },
        )
        if native.get("status") == "success":
            outputs = native.get("result", native)
            return _result(
                success=True,
                tool="niagara_add_mesh_renderer",
                t0=t0,
                message="Niagara mesh renderer added through native bridge",
                outputs=outputs,
            )
        message = native.get("error") or native.get("message", "Native Niagara mesh renderer command failed")
        return _result(
            success=False,
            tool="niagara_add_mesh_renderer",
            t0=t0,
            message="Niagara mesh renderer add failed",
            errors=[message],
            warnings=["This operation requires the updated native C++ plugin; run Live Coding or restart the editor after rebuilding."],
        )

    @mcp.tool()
    async def niagara_describe_system(ctx: Context, system_path: str) -> Dict[str, Any]:
        """Describe a Niagara System asset and report what Python can safely inspect."""
        t0 = time.monotonic()
        native = _send("niagara_describe_system", {"system_path": system_path})
        if native.get("status") == "success":
            outputs = native.get("result", native)
            return _result(
                success=True,
                tool="niagara_describe_system",
                t0=t0,
                message="Niagara system described through native bridge",
                outputs=outputs,
            )

        object_path = _asset_object_path(system_path)
        code = f"""
import unreal, json, traceback
out = {{"success": False, "path": {object_path!r}, "properties": {{}}, "warnings": []}}
try:
    asset = unreal.EditorAssetLibrary.load_asset({object_path!r})
    if not asset:
        out["message"] = "Asset not found"
    else:
        out["success"] = True
        out["class"] = asset.get_class().get_name()
        for prop in ("fixed_bounds", "warmup_time", "warmup_tick_count", "cast_shadow", "receives_decals"):
            try:
                out["properties"][prop] = str(asset.get_editor_property(prop))
            except Exception as exc:
                out["properties"][prop] = "unavailable: " + str(exc)
        out["python_methods"] = [
            name for name in dir(asset)
            if not name.startswith("_") and any(k in name.lower() for k in ("emitter", "parameter", "script", "system"))
        ]
        out["warnings"].append("UE 5.6 Python exposes limited Niagara stack editing; use native bridge commands for full module/renderer authoring.")
except Exception:
    out["message"] = traceback.format_exc()
print(json.dumps(out))
"""
        parsed = _parse_exec_json(_exec_python(code))
        if not parsed.get("success"):
            return _result(success=False, tool="niagara_describe_system", t0=t0, message="Niagara describe failed", errors=[parsed.get("message", str(parsed))])
        return _result(
            success=True,
            tool="niagara_describe_system",
            t0=t0,
            message="Niagara system described",
            outputs=parsed,
            warnings=parsed.get("warnings", []),
        )

    @mcp.tool()
    async def niagara_apply_system_settings(
        ctx: Context,
        system_path: str,
        warmup_time: float = 0.0,
        warmup_tick_count: int = 0,
        fixed_bounds_min: List[float] = [-500.0, -500.0, -500.0],
        fixed_bounds_max: List[float] = [500.0, 500.0, 500.0],
        save: bool = True,
    ) -> Dict[str, Any]:
        """Apply safe Niagara System-level settings such as warmup and fixed bounds."""
        t0 = time.monotonic()
        object_path = _asset_object_path(system_path)
        code = f"""
import unreal, json, traceback
out = {{"success": False, "changed": [], "warnings": []}}
try:
    path = {object_path!r}
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        out["message"] = "Asset not found"
    else:
        asset.modify()
        for name, value in (("warmup_time", float({warmup_time})), ("warmup_tick_count", int({warmup_tick_count}))):
            try:
                asset.set_editor_property(name, value)
                out["changed"].append(name)
            except Exception as exc:
                out["warnings"].append(f"Could not set {{name}}: {{exc}}")
        try:
            box = unreal.Box(
                min=unreal.Vector(*{fixed_bounds_min!r}),
                max=unreal.Vector(*{fixed_bounds_max!r}),
                is_valid=True,
            )
            asset.set_editor_property("fixed_bounds", box)
            out["changed"].append("fixed_bounds")
        except Exception as exc:
            out["warnings"].append(f"Could not set fixed_bounds through Python: {{exc}}")
        if {bool(save)!r}:
            out["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False))
        out["success"] = True
except Exception:
    out["message"] = traceback.format_exc()
print(json.dumps(out))
"""
        parsed = _parse_exec_json(_exec_python(code))
        if not parsed.get("success"):
            return _result(success=False, tool="niagara_apply_system_settings", t0=t0, message="Niagara settings update failed", errors=[parsed.get("message", str(parsed))])
        return _result(
            success=True,
            tool="niagara_apply_system_settings",
            t0=t0,
            message="Niagara system settings applied",
            outputs=parsed,
            warnings=parsed.get("warnings", []),
        )

    @mcp.tool()
    async def niagara_set_fixed_bounds(
        ctx: Context,
        system_path: str,
        fixed_bounds_min: List[float] = [-500.0, -500.0, -500.0],
        fixed_bounds_max: List[float] = [500.0, 500.0, 500.0],
        save: bool = True,
    ) -> Dict[str, Any]:
        """Set Niagara System fixed bounds without changing unrelated system settings."""
        t0 = time.monotonic()
        object_path = _asset_object_path(system_path)
        code = f"""
import unreal, json, traceback
out = {{"success": False, "changed": [], "warnings": []}}
try:
    path = {object_path!r}
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        out["message"] = "Asset not found"
    else:
        asset.modify()
        box = unreal.Box(
            min=unreal.Vector(*{fixed_bounds_min!r}),
            max=unreal.Vector(*{fixed_bounds_max!r}),
            is_valid=True,
        )
        asset.set_editor_property("fixed_bounds", box)
        out["changed"].append("fixed_bounds")
        if {bool(save)!r}:
            out["saved"] = bool(unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False))
        out["success"] = True
except Exception:
    out["message"] = traceback.format_exc()
print(json.dumps(out))
"""
        parsed = _parse_exec_json(_exec_python(code))
        if not parsed.get("success"):
            return _result(
                success=False,
                tool="niagara_set_fixed_bounds",
                t0=t0,
                message="Niagara fixed-bounds update failed",
                errors=[parsed.get("message", str(parsed))],
            )
        return _result(
            success=True,
            tool="niagara_set_fixed_bounds",
            t0=t0,
            message="Niagara fixed bounds set",
            outputs=parsed,
            warnings=parsed.get("warnings", []),
        )

    @mcp.tool()
    async def niagara_profile_system(ctx: Context, system_path: str) -> Dict[str, Any]:
        """Return lightweight asset-level Niagara profiling data and authoring hints."""
        t0 = time.monotonic()
        object_path = _asset_object_path(system_path)
        code = f"""
import unreal, json, os, traceback
out = {{"success": False, "path": {object_path!r}, "warnings": []}}
try:
    path = {object_path!r}
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        out["message"] = "Asset not found"
    else:
        out["success"] = True
        out["class"] = asset.get_class().get_name()
        out["properties"] = {{}}
        for prop in ("fixed_bounds", "warmup_time", "warmup_tick_count"):
            try:
                out["properties"][prop] = str(asset.get_editor_property(prop))
            except Exception as exc:
                out["warnings"].append(f"Could not read {{prop}}: {{exc}}")
        try:
            package_name = str(asset.get_outermost().get_name())
            filename = unreal.PackageName.long_package_name_to_filename(package_name, ".uasset")
            out["package_file"] = filename
            out["package_size_bytes"] = os.path.getsize(filename) if os.path.exists(filename) else None
        except Exception as exc:
            out["warnings"].append(f"Could not resolve package file size: {{exc}}")
        out["available_methods"] = [
            name for name in dir(asset)
            if not name.startswith("_") and any(k in name.lower() for k in ("bound", "emitter", "parameter", "warmup"))
        ][:80]
        out["recommendations"] = [
            "Set fixed bounds for GPU-heavy or large-world effects.",
            "Use native bridge commands for emitter/module/renderer stack profiling.",
            "Use viewport or PIE capture to validate visual density and overdraw once the system is placed.",
        ]
except Exception:
    out["message"] = traceback.format_exc()
print(json.dumps(out))
"""
        parsed = _parse_exec_json(_exec_python(code))
        if not parsed.get("success"):
            return _result(
                success=False,
                tool="niagara_profile_system",
                t0=t0,
                message="Niagara profile failed",
                errors=[parsed.get("message", str(parsed))],
            )
        return _result(
            success=True,
            tool="niagara_profile_system",
            t0=t0,
            message="Niagara system profiled",
            outputs=parsed,
            warnings=parsed.get("warnings", []),
        )

    @mcp.tool()
    async def niagara_get_effect_recipe(ctx: Context, recipe_name: str = "blackhole_orb_inflow") -> Dict[str, Any]:
        """Return an original Niagara module-stack recipe for a named effect."""
        t0 = time.monotonic()
        if recipe_name != "blackhole_orb_inflow":
            return _result(
                success=False,
                tool="niagara_get_effect_recipe",
                t0=t0,
                message=f"Unknown recipe: {recipe_name}",
                errors=["Available recipes: blackhole_orb_inflow"],
            )
        return _result(
            success=True,
            tool="niagara_get_effect_recipe",
            t0=t0,
            message="Niagara effect recipe generated",
            outputs={"recipe": BLACKHOLE_INFLOW_SPEC},
        )
