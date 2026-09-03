"""Clean-room PCG wrappers for native-alignment world generation workflows."""

from __future__ import annotations

import json
import logging
import re
import textwrap
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP.tools.pcg_tools")

PCG_RESULT_SCHEMA = "unreal_mcp_ghost.pcg_tool_result.v1"


def _exec_structured(code: str, stage_name: str) -> Dict[str, Any]:
    from tools.exec_substrate import exec_python_structured

    return exec_python_structured(code, stage_name)


def _clean_path(value: str) -> str:
    path = (value or "").strip().replace("\\", "/").rstrip("/")
    while "//" in path:
        path = path.replace("//", "/")
    return path


def _split_asset_path(asset_path: str) -> Tuple[str, str, str]:
    path = _clean_path(asset_path)
    if "." in path.rsplit("/", 1)[-1]:
        path = path.split(".", 1)[0]
    if not path.startswith("/Game/"):
        raise ValueError("asset path must start with /Game/")
    if path.endswith("/"):
        raise ValueError("asset path must include an asset name")
    folder, _, name = path.rpartition("/")
    if not folder or not name:
        raise ValueError("asset path must include a folder and asset name")
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        raise ValueError("asset name must be a valid Unreal object name")
    return path, folder, name


def _vector3(value: Optional[Sequence[float]], default: Sequence[float], field_name: str) -> List[float]:
    raw = list(default if value is None else value)
    if len(raw) != 3:
        raise ValueError(f"{field_name} must contain exactly three numbers")
    return [float(raw[0]), float(raw[1]), float(raw[2])]


def _local_result(
    *,
    success: bool,
    stage: str,
    tool: str,
    message: str,
    inputs: Dict[str, Any],
    t0: float,
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
) -> str:
    payload = {
        "success": success,
        "schema": PCG_RESULT_SCHEMA,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": tool, "duration_ms": int((time.monotonic() - t0) * 1000)},
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _json_result(stage: str, tool: str, inputs: Dict[str, Any], result: Dict[str, Any], t0: float) -> str:
    if not isinstance(result, dict):
        result = {
            "success": False,
            "stage": stage,
            "message": "Unreal execution returned a non-object payload",
            "outputs": {"raw": str(result)},
            "warnings": [],
            "errors": ["Unreal execution returned a non-object payload"],
            "log_tail": [],
        }

    payload = dict(result)
    payload["schema"] = PCG_RESULT_SCHEMA
    payload["stage"] = payload.get("stage") or stage
    payload["inputs"] = inputs
    payload.setdefault("outputs", {})
    payload.setdefault("warnings", [])
    payload.setdefault("errors", [])
    payload.setdefault("log_tail", [])
    payload.setdefault("message", "Operation completed")
    if payload.get("errors") and payload.get("success") is not False:
        payload["success"] = False
        if payload.get("message") == "Operation completed":
            payload["message"] = "Operation completed with blocking PCG errors"
    payload.setdefault("success", not bool(payload.get("errors")))

    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    meta.update({"tool": tool, "duration_ms": int((time.monotonic() - t0) * 1000)})
    payload["meta"] = meta
    return json.dumps(payload, indent=2, sort_keys=True)


def _support_code() -> str:
    return textwrap.dedent(
        """\
        class_names = [
            "PCGGraph",
            "PCGComponent",
            "PCGVolume",
            "PCGGraphFactory",
            "PCGSubsystem",
        ]
        available_classes = {}
        class_modules = {}
        for class_name in class_names:
            cls = getattr(unreal, class_name, None)
            available_classes[class_name] = cls is not None
            class_modules[class_name] = getattr(cls, "__module__", "") if cls is not None else ""

        _result["available_classes"] = available_classes
        _result["class_modules"] = class_modules
        _result["pcg_available"] = bool(
            available_classes.get("PCGGraph")
            and (available_classes.get("PCGVolume") or available_classes.get("PCGComponent"))
        )
        _result["can_create_graph_asset"] = bool(
            available_classes.get("PCGGraph") and available_classes.get("PCGGraphFactory")
        )
        _result["can_spawn_pcg_volume"] = bool(available_classes.get("PCGVolume"))

        if not _result["pcg_available"]:
            _warnings.append("PCG classes are not available; enable the Procedural Content Generation Framework plugin and restart Unreal Editor.")
        if available_classes.get("PCGGraph") and not available_classes.get("PCGGraphFactory"):
            _warnings.append("PCGGraph exists but PCGGraphFactory is unavailable through Unreal Python; graph creation may need a C++ bridge wrapper.")
        """
    )


def _graph_asset_code(graph_path: str, folder_path: str, asset_name: str, overwrite: bool, save: bool) -> str:
    return textwrap.dedent(
        f"""\
        graph_path = {graph_path!r}
        folder_path = {folder_path!r}
        asset_name = {asset_name!r}
        overwrite = {bool(overwrite)!r}
        save = {bool(save)!r}

        graph_class = getattr(unreal, "PCGGraph", None)
        factory_class = getattr(unreal, "PCGGraphFactory", None)
        if graph_class is None:
            _errors.append("PCGGraph class is unavailable; enable the PCG plugin before creating graph assets.")
        elif factory_class is None:
            _errors.append("PCGGraphFactory is unavailable through Unreal Python; add a native bridge wrapper for reliable PCG graph asset creation.")
        else:
            existing = unreal.EditorAssetLibrary.load_asset(graph_path)
            if existing is not None and not overwrite:
                _result["asset_path"] = graph_path
                _result["created"] = False
                _result["reused_existing"] = True
                _warnings.append("PCG graph already exists; pass overwrite=True to replace it.")
            else:
                if existing is not None and overwrite:
                    if not unreal.EditorAssetLibrary.delete_asset(graph_path):
                        _errors.append("Existing PCG graph could not be deleted before overwrite.")
                    else:
                        _result["deleted_existing"] = True
                if not _errors:
                    if not unreal.EditorAssetLibrary.does_directory_exist(folder_path):
                        unreal.EditorAssetLibrary.make_directory(folder_path)
                    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                    factory = factory_class()
                    asset = asset_tools.create_asset(asset_name, folder_path, graph_class, factory)
                    if asset is None:
                        _errors.append("Unreal AssetTools failed to create the PCG graph asset.")
                    else:
                        _result["asset_path"] = graph_path
                        _result["created"] = True
                        _result["reused_existing"] = False
                        if save:
                            _result["saved"] = bool(unreal.EditorAssetLibrary.save_asset(graph_path, only_if_is_dirty=False))
                        else:
                            _result["saved"] = False
        """
    )


def _pcg_component_code(prefix: str = "actor") -> str:
    return textwrap.dedent(
        f"""\
        component_class = getattr(unreal, "PCGComponent", None)
        pcg_components = []
        if component_class is not None and {prefix} is not None:
            try:
                pcg_components = list({prefix}.get_components_by_class(component_class))
            except Exception as _component_exc:
                _warnings.append("Could not query PCGComponent directly: " + str(_component_exc))
        if not pcg_components and {prefix} is not None:
            try:
                all_components = list({prefix}.get_components_by_class(unreal.ActorComponent))
                for component in all_components:
                    class_name = component.get_class().get_name()
                    if "PCG" in class_name or "PCG" in component.get_name():
                        pcg_components.append(component)
            except Exception as _fallback_exc:
                _warnings.append("Could not inspect actor components for PCG fallback: " + str(_fallback_exc))
        """
    )


def _volume_code(
    *,
    actor_label: str,
    graph_path: str,
    location: Sequence[float],
    rotation: Sequence[float],
    scale: Sequence[float],
    generate: bool,
) -> str:
    component_code = textwrap.indent(_pcg_component_code("actor").rstrip(), "        ")
    return textwrap.dedent(
        f"""\
        actor_label = {actor_label!r}
        graph_path = {graph_path!r}
        location = {list(location)!r}
        rotation = {list(rotation)!r}
        scale = {list(scale)!r}
        should_generate = {bool(generate)!r}

        volume_class = getattr(unreal, "PCGVolume", None)
        if volume_class is None:
            _errors.append("PCGVolume class is unavailable; enable the PCG plugin before spawning PCG volumes.")
            actor = None
        else:
            actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            actor = actor_subsystem.spawn_actor_from_class(
                volume_class,
                unreal.Vector(float(location[0]), float(location[1]), float(location[2])),
                unreal.Rotator(float(rotation[0]), float(rotation[1]), float(rotation[2])),
            )
            if actor is None:
                _errors.append("Unreal failed to spawn a PCGVolume actor.")
            else:
                try:
                    actor.set_actor_label(actor_label)
                except Exception as _label_exc:
                    _warnings.append("Could not set actor label: " + str(_label_exc))
                try:
                    actor.set_actor_scale3d(unreal.Vector(float(scale[0]), float(scale[1]), float(scale[2])))
                except Exception as _scale_exc:
                    _warnings.append("Could not set actor scale: " + str(_scale_exc))

{component_code}

        assignment_attempts = []
        if actor is not None and graph_path:
            graph = unreal.EditorAssetLibrary.load_asset(graph_path)
            if graph is None:
                _errors.append("PCG graph asset not found: " + graph_path)
            else:
                if not pcg_components:
                    _warnings.append("Spawned PCG volume has no discoverable PCG component to receive the graph.")
                for component in pcg_components:
                    for prop in ("graph", "graph_instance", "pcg_graph", "Graph", "GraphInstance"):
                        try:
                            component.set_editor_property(prop, graph)
                            assignment_attempts.append({{"component": component.get_name(), "property": prop, "success": True}})
                            break
                        except Exception as _assign_exc:
                            assignment_attempts.append({{"component": component.get_name(), "property": prop, "success": False, "error": str(_assign_exc)}})

        generation_attempts = []
        if should_generate and actor is not None:
            targets = list(pcg_components) + [actor]
            for target in targets:
                for method_name in ("generate", "generate_local", "refresh", "dirty_generated", "schedule_generate", "schedule_refresh"):
                    method = getattr(target, method_name, None)
                    if callable(method):
                        try:
                            method()
                            generation_attempts.append({{"target": target.get_name(), "method": method_name, "success": True}})
                            break
                        except Exception as _generate_exc:
                            generation_attempts.append({{"target": target.get_name(), "method": method_name, "success": False, "error": str(_generate_exc)}})
            if not generation_attempts:
                _warnings.append("No known PCG generation method was callable through Unreal Python.")

        _result["actor_label"] = actor.get_actor_label() if actor is not None else actor_label
        _result["actor_name"] = actor.get_name() if actor is not None else ""
        _result["graph_path"] = graph_path
        _result["component_count"] = len(pcg_components)
        _result["component_names"] = [component.get_name() for component in pcg_components]
        _result["assignment_attempts"] = assignment_attempts
        _result["generation_attempts"] = generation_attempts
        """
    )


def _refresh_code(actor_label: str, cleanup: bool, generate: bool) -> str:
    component_code = textwrap.indent(_pcg_component_code("actor").rstrip(), "        ")
    return textwrap.dedent(
        f"""\
        actor_label = {actor_label!r}
        cleanup = {bool(cleanup)!r}
        should_generate = {bool(generate)!r}
        actors = list(unreal.EditorLevelLibrary.get_all_level_actors())
        actor = None
        for candidate in actors:
            try:
                if candidate.get_actor_label() == actor_label or candidate.get_name() == actor_label:
                    actor = candidate
                    break
            except Exception:
                if candidate.get_name() == actor_label:
                    actor = candidate
                    break

        if actor is None:
            _errors.append("No actor found by label or name: " + actor_label)

{component_code}

        cleanup_attempts = []
        generation_attempts = []
        if actor is not None:
            targets = list(pcg_components) + [actor]
            if cleanup:
                for target in targets:
                    for method_name in ("cleanup", "cleanup_local", "clear_generated", "remove_generated_content"):
                        method = getattr(target, method_name, None)
                        if callable(method):
                            try:
                                method()
                                cleanup_attempts.append({{"target": target.get_name(), "method": method_name, "success": True}})
                                break
                            except Exception as _cleanup_exc:
                                cleanup_attempts.append({{"target": target.get_name(), "method": method_name, "success": False, "error": str(_cleanup_exc)}})
            if should_generate:
                for target in targets:
                    for method_name in ("generate", "generate_local", "refresh", "dirty_generated", "schedule_generate", "schedule_refresh"):
                        method = getattr(target, method_name, None)
                        if callable(method):
                            try:
                                method()
                                generation_attempts.append({{"target": target.get_name(), "method": method_name, "success": True}})
                                break
                            except Exception as _generate_exc:
                                generation_attempts.append({{"target": target.get_name(), "method": method_name, "success": False, "error": str(_generate_exc)}})
            if cleanup and not cleanup_attempts:
                _warnings.append("No known PCG cleanup method was callable through Unreal Python.")
            if should_generate and not generation_attempts:
                _warnings.append("No known PCG generation method was callable through Unreal Python.")

        _result["actor_label"] = actor.get_actor_label() if actor is not None else actor_label
        _result["actor_name"] = actor.get_name() if actor is not None else ""
        _result["component_count"] = len(pcg_components)
        _result["component_names"] = [component.get_name() for component in pcg_components]
        _result["cleanup_attempts"] = cleanup_attempts
        _result["generation_attempts"] = generation_attempts
        """
    )


def register_pcg_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def pcg_check_support(ctx: Context) -> str:
        """Report whether Unreal Python exposes the PCG classes needed by Ghost.

        KB: see knowledge_base/10_WORLD_BUILDING.md#4-procedural-content-generation-pcg
        Example:
            pcg_check_support()"""
        t0 = time.monotonic()
        inputs: Dict[str, Any] = {}
        result = _exec_structured(_support_code(), "pcg_check_support")
        return _json_result("pcg_check_support", "pcg_check_support", inputs, result, t0)

    @mcp.tool()
    def pcg_create_graph_asset(
        ctx: Context,
        graph_path: str = "/Game/PCG/PCG_CityDistrict",
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create or reuse a PCG graph asset through Unreal Python when available.

        Args:
            graph_path: Content Browser path such as /Game/PCG/PCG_CityDistrict.
            overwrite: Delete an existing graph before creation.
            save: Save the graph package after creation.

        KB: see knowledge_base/10_WORLD_BUILDING.md#4-procedural-content-generation-pcg
        Example:
            pcg_create_graph_asset(graph_path="/Game/PCG/PCG_CityDistrict")"""
        t0 = time.monotonic()
        inputs = {"graph_path": graph_path, "overwrite": overwrite, "save": save}
        try:
            clean_graph_path, folder_path, asset_name = _split_asset_path(graph_path)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="pcg_create_graph_asset",
                tool="pcg_create_graph_asset",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        code = _graph_asset_code(clean_graph_path, folder_path, asset_name, overwrite, save)
        result = _exec_structured(code, "pcg_create_graph_asset")
        return _json_result("pcg_create_graph_asset", "pcg_create_graph_asset", inputs, result, t0)

    @mcp.tool()
    def pcg_create_volume(
        ctx: Context,
        actor_label: str = "PCG_CityDistrictVolume",
        graph_path: str = "",
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
        generate: bool = True,
    ) -> str:
        """Spawn a PCG volume and optionally assign a PCG graph.

        Args:
            actor_label: Editor label for the new PCG volume actor.
            graph_path: Optional /Game path to an existing PCG graph asset.
            location: World location [x, y, z].
            rotation: World rotation [pitch, yaw, roll].
            scale: Actor scale [x, y, z].
            generate: Try known PCG generation methods after graph assignment.

        KB: see knowledge_base/10_WORLD_BUILDING.md#4-procedural-content-generation-pcg
        Example:
            pcg_create_volume(actor_label="PCG_Downtown", graph_path="/Game/PCG/PCG_CityDistrict")"""
        t0 = time.monotonic()
        inputs = {
            "actor_label": actor_label,
            "graph_path": graph_path,
            "location": location or [0.0, 0.0, 0.0],
            "rotation": rotation or [0.0, 0.0, 0.0],
            "scale": scale or [10.0, 10.0, 2.0],
            "generate": generate,
        }
        try:
            loc = _vector3(location, [0.0, 0.0, 0.0], "location")
            rot = _vector3(rotation, [0.0, 0.0, 0.0], "rotation")
            scl = _vector3(scale, [10.0, 10.0, 2.0], "scale")
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="pcg_create_volume",
                tool="pcg_create_volume",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        clean_graph_path = _clean_path(graph_path)
        code = _volume_code(
            actor_label=actor_label,
            graph_path=clean_graph_path,
            location=loc,
            rotation=rot,
            scale=scl,
            generate=generate,
        )
        result = _exec_structured(code, "pcg_create_volume")
        return _json_result("pcg_create_volume", "pcg_create_volume", inputs, result, t0)

    @mcp.tool()
    def pcg_refresh_volume(
        ctx: Context,
        actor_label: str,
        cleanup: bool = False,
        generate: bool = True,
    ) -> str:
        """Refresh an existing PCG volume by label or actor name.

        Args:
            actor_label: Existing PCG volume actor label or object name.
            cleanup: Try known cleanup methods before regeneration.
            generate: Try known generation/refresh methods.

        KB: see knowledge_base/10_WORLD_BUILDING.md#4-procedural-content-generation-pcg
        Example:
            pcg_refresh_volume(actor_label="PCG_Downtown", cleanup=True)"""
        t0 = time.monotonic()
        inputs = {"actor_label": actor_label, "cleanup": cleanup, "generate": generate}
        if not str(actor_label or "").strip():
            return _local_result(
                success=False,
                stage="pcg_refresh_volume",
                tool="pcg_refresh_volume",
                message="actor_label is required",
                inputs=inputs,
                errors=["actor_label is required"],
                t0=t0,
            )
        result = _exec_structured(_refresh_code(actor_label, cleanup, generate), "pcg_refresh_volume")
        return _json_result("pcg_refresh_volume", "pcg_refresh_volume", inputs, result, t0)

    logger.info("PCG native-alignment tools registered successfully")
