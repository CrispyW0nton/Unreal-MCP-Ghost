"""Geometry Script / Modeling tools for DynamicMesh authoring in UE5."""

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
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = unreal.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error("Error in %s: %s", command, exc)
        return {"success": False, "message": str(exc)}


def _make_result(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": stage, "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _bridge_result(
    *,
    stage: str,
    raw: Dict[str, Any],
    inputs: Dict[str, Any],
    message: str,
    t0: float,
    warnings: Optional[List[str]] = None,
) -> str:
    raw = raw or {}
    failed = raw.get("success") is False or raw.get("status") == "error" or bool(raw.get("error"))
    if failed:
        msg = raw.get("error") or raw.get("message") or f"{stage} failed"
        return json.dumps(_make_result(
            success=False,
            stage="error",
            message=msg,
            inputs=inputs,
            errors=[msg],
            t0=t0,
        ))

    outputs = {
        key: value for key, value in raw.items()
        if key not in {"success", "status", "message", "error"}
    }
    return json.dumps(_make_result(
        success=True,
        stage=stage,
        message=message,
        inputs=inputs,
        outputs=outputs,
        warnings=warnings,
        t0=t0,
    ))


def register_geometry_tools(mcp: FastMCP):

    @mcp.tool()
    async def geom_create_dynamic_mesh(
        ctx: Context,
        actor_name: str = "DM_GeneratedMesh",
        primitive: str = "box",
        dimensions: Optional[List[float]] = None,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        radial_steps: int = 16,
        height_steps: int = 0,
        overwrite: bool = False,
    ) -> str:
        """Create an editor DynamicMesh actor and seed it with a primitive mesh.

        Args:
            actor_name: DynamicMesh actor label to create.
            primitive: One of "box", "sphere", "cylinder", "plane", or "empty".
            dimensions: Primitive dimensions in centimeters. Box/plane use X,Y,Z;
                sphere uses X as radius; cylinder uses X radius and Z height.
            location: Optional world location [x, y, z].
            rotation: Optional world rotation [pitch, yaw, roll].
            radial_steps: Segment count for sphere/cylinder primitives.
            height_steps: Vertical segments for cylinder and box-like primitives.
            overwrite: Delete an existing actor with the same label before creating.

        Returns:
            Structured JSON with actor label, primitive, and mesh counts.

        KB: see knowledge_base/22_GEOMETRY_SCRIPT_AND_MODELING.md#mcp-geometry-tools
        Example:
            geom_create_dynamic_mesh(actor_name="DM_CoverBlock", primitive="box", dimensions=[200, 80, 120])"""
        t0 = time.monotonic()
        inputs = {
            "actor_name": actor_name,
            "primitive": primitive,
            "dimensions": dimensions or [100.0, 100.0, 100.0],
            "location": location or [0.0, 0.0, 0.0],
            "rotation": rotation or [0.0, 0.0, 0.0],
            "radial_steps": radial_steps,
            "height_steps": height_steps,
            "overwrite": overwrite,
        }
        raw = _send("geom_create_dynamic_mesh", inputs)
        return _bridge_result(stage="geom_create_dynamic_mesh", raw=raw, inputs=inputs, message="Created DynamicMesh actor", t0=t0)

    @mcp.tool()
    async def geom_boolean_op(
        ctx: Context,
        target_actor: str,
        tool_actor: str,
        operation: str = "subtract",
        output_space: str = "target",
        fill_holes: bool = True,
        simplify_output: bool = True,
        hide_tool: bool = False,
    ) -> str:
        """Apply a Geometry Script boolean operation between two DynamicMesh actors.

        Args:
            target_actor: DynamicMesh actor label to mutate.
            tool_actor: DynamicMesh actor label used as the boolean cutter/tool.
            operation: "union", "intersection", "subtract", "trim_inside", or "trim_outside".
            output_space: "target", "tool", or "shared" transform space for the result.
            fill_holes: Fill holes generated by the boolean operation.
            simplify_output: Simplify coplanar boolean output.
            hide_tool: Hide the tool actor after a successful operation.

        Returns:
            Structured JSON with target actor and resulting mesh counts.

        KB: see knowledge_base/22_GEOMETRY_SCRIPT_AND_MODELING.md#mcp-geometry-tools
        Example:
            geom_boolean_op(target_actor="DM_Block", tool_actor="DM_Cutter", operation="subtract")"""
        t0 = time.monotonic()
        inputs = {
            "target_actor": target_actor,
            "tool_actor": tool_actor,
            "operation": operation,
            "output_space": output_space,
            "fill_holes": fill_holes,
            "simplify_output": simplify_output,
            "hide_tool": hide_tool,
        }
        raw = _send("geom_boolean_op", inputs)
        return _bridge_result(stage="geom_boolean_op", raw=raw, inputs=inputs, message="Applied mesh boolean", t0=t0)

    @mcp.tool()
    async def geom_extrude(
        ctx: Context,
        actor_name: str,
        distance: float = 50.0,
        direction: Optional[List[float]] = None,
        direction_mode: str = "fixed",
        area_mode: str = "entire_selection",
        uv_scale: float = 1.0,
        solids_to_shells: bool = True,
    ) -> str:
        """Extrude faces on a DynamicMesh actor using Geometry Script modeling.

        Args:
            actor_name: DynamicMesh actor label to mutate.
            distance: Extrusion distance in centimeters.
            direction: Fixed extrusion direction [x, y, z].
            direction_mode: "fixed" or "average_face_normal".
            area_mode: "entire_selection", "per_polygroup", or "per_triangle".
            uv_scale: UV scale applied to generated side faces.
            solids_to_shells: Treat solids as shells during extrusion.

        Returns:
            Structured JSON with resulting mesh counts.

        KB: see knowledge_base/22_GEOMETRY_SCRIPT_AND_MODELING.md#mcp-geometry-tools
        Example:
            geom_extrude(actor_name="DM_Panel", distance=25, direction=[0, 0, 1])"""
        t0 = time.monotonic()
        inputs = {
            "actor_name": actor_name,
            "distance": distance,
            "direction": direction or [0.0, 0.0, 1.0],
            "direction_mode": direction_mode,
            "area_mode": area_mode,
            "uv_scale": uv_scale,
            "solids_to_shells": solids_to_shells,
        }
        raw = _send("geom_extrude", inputs)
        return _bridge_result(stage="geom_extrude", raw=raw, inputs=inputs, message="Extruded DynamicMesh faces", t0=t0)

    @mcp.tool()
    async def geom_remesh(
        ctx: Context,
        actor_name: str,
        target_triangle_count: int = 5000,
        target_edge_length: float = 0.0,
        iterations: int = 20,
        discard_attributes: bool = False,
        reproject: bool = True,
    ) -> str:
        """Uniformly remesh a DynamicMesh actor.

        Args:
            actor_name: DynamicMesh actor label to mutate.
            target_triangle_count: Approximate triangle count when target_edge_length is 0.
            target_edge_length: Explicit edge length target; <=0 uses triangle count mode.
            iterations: Number of remeshing iterations.
            discard_attributes: Drop mesh attributes before remeshing.
            reproject: Reproject vertices to the input mesh surface.

        Returns:
            Structured JSON with resulting mesh counts.

        KB: see knowledge_base/22_GEOMETRY_SCRIPT_AND_MODELING.md#mcp-geometry-tools
        Example:
            geom_remesh(actor_name="DM_Rock", target_triangle_count=1200, iterations=12)"""
        t0 = time.monotonic()
        inputs = {
            "actor_name": actor_name,
            "target_triangle_count": target_triangle_count,
            "target_edge_length": target_edge_length,
            "iterations": iterations,
            "discard_attributes": discard_attributes,
            "reproject": reproject,
        }
        raw = _send("geom_remesh", inputs)
        return _bridge_result(stage="geom_remesh", raw=raw, inputs=inputs, message="Remeshed DynamicMesh", t0=t0)

    @mcp.tool()
    async def geom_uv_unwrap(
        ctx: Context,
        actor_name: str,
        uv_channel: int = 0,
        method: str = "xatlas",
        texture_resolution: int = 1024,
        max_iterations: int = 2,
        auto_pack: bool = True,
    ) -> str:
        """Generate or repack UVs for a DynamicMesh actor.

        Args:
            actor_name: DynamicMesh actor label to mutate.
            uv_channel: UV channel index.
            method: "xatlas", "patch_builder", "recompute", or "layout".
            texture_resolution: Layout texture resolution used for packing.
            max_iterations: XAtlas iteration count.
            auto_pack: Pack generated PatchBuilder UVs.

        Returns:
            Structured JSON with UV channel and mesh counts.

        KB: see knowledge_base/22_GEOMETRY_SCRIPT_AND_MODELING.md#mcp-geometry-tools
        Example:
            geom_uv_unwrap(actor_name="DM_CoverBlock", method="xatlas", texture_resolution=2048)"""
        t0 = time.monotonic()
        inputs = {
            "actor_name": actor_name,
            "uv_channel": uv_channel,
            "method": method,
            "texture_resolution": texture_resolution,
            "max_iterations": max_iterations,
            "auto_pack": auto_pack,
        }
        raw = _send("geom_uv_unwrap", inputs)
        return _bridge_result(stage="geom_uv_unwrap", raw=raw, inputs=inputs, message="Updated DynamicMesh UVs", t0=t0)

    @mcp.tool()
    async def geom_bake_to_static_mesh(
        ctx: Context,
        actor_name: str,
        asset_path: str = "/Game/Geometry/SM_BakedDynamicMesh",
        enable_nanite: bool = False,
        enable_collision: bool = True,
        recompute_normals: bool = False,
        recompute_tangents: bool = False,
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Bake a DynamicMesh actor into a StaticMesh asset.

        Args:
            actor_name: DynamicMesh actor label to bake.
            asset_path: Content Browser asset path including asset name.
            enable_nanite: Enable Nanite on the generated static mesh.
            enable_collision: Generate collision settings on the new static mesh.
            recompute_normals: Recompute normals during asset creation.
            recompute_tangents: Recompute tangents during asset creation.
            overwrite: Delete an existing asset at asset_path first.
            save: Save the generated package after creation.

        Returns:
            Structured JSON with baked asset path and mesh counts.

        KB: see knowledge_base/22_GEOMETRY_SCRIPT_AND_MODELING.md#mcp-geometry-tools
        Example:
            geom_bake_to_static_mesh(actor_name="DM_CoverBlock", asset_path="/Game/Geometry/SM_CoverBlock_A")"""
        t0 = time.monotonic()
        inputs = {
            "actor_name": actor_name,
            "asset_path": asset_path,
            "enable_nanite": enable_nanite,
            "enable_collision": enable_collision,
            "recompute_normals": recompute_normals,
            "recompute_tangents": recompute_tangents,
            "overwrite": overwrite,
            "save": save,
        }
        raw = _send("geom_bake_to_static_mesh", inputs)
        return _bridge_result(stage="geom_bake_to_static_mesh", raw=raw, inputs=inputs, message="Baked DynamicMesh to StaticMesh asset", t0=t0)

    @mcp.tool()
    async def geom_apply_displacement(
        ctx: Context,
        actor_name: str,
        magnitude: float = 5.0,
        frequency: float = 0.25,
        seed: int = 0,
        along_normal: bool = True,
    ) -> str:
        """Apply Perlin-noise displacement to a DynamicMesh actor.

        Args:
            actor_name: DynamicMesh actor label to mutate.
            magnitude: Displacement magnitude in centimeters.
            frequency: Perlin noise frequency.
            seed: Deterministic random seed.
            along_normal: Apply displacement along vertex normals.

        Returns:
            Structured JSON with resulting mesh counts.

        KB: see knowledge_base/22_GEOMETRY_SCRIPT_AND_MODELING.md#mcp-geometry-tools
        Example:
            geom_apply_displacement(actor_name="DM_Rock", magnitude=12, frequency=0.08, seed=7)"""
        t0 = time.monotonic()
        inputs = {
            "actor_name": actor_name,
            "magnitude": magnitude,
            "frequency": frequency,
            "seed": seed,
            "along_normal": along_normal,
        }
        raw = _send("geom_apply_displacement", inputs)
        return _bridge_result(stage="geom_apply_displacement", raw=raw, inputs=inputs, message="Applied DynamicMesh displacement", t0=t0)
