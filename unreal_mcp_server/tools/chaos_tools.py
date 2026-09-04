"""Chaos destruction and cloth tools for UE5."""

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
        warnings=warnings or [],
        t0=t0,
    ))


def register_chaos_tools(mcp: FastMCP):

    @mcp.tool()
    async def chaos_create_solver_actor(
        ctx: Context,
        actor_name: str = "ChaosSolver_MCP",
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        set_as_world_solver: bool = False,
        overwrite: bool = False,
    ) -> str:
        """Create a Chaos Solver actor in the active editor world.

        KB: see knowledge_base/26_CHAOS_PHYSICS_AND_DESTRUCTION.md#mcp-chaos-and-cloth-tools
        Example:
            chaos_create_solver_actor(actor_name="ChaosSolver_Destruction", set_as_world_solver=True)"""
        t0 = time.monotonic()
        inputs = {
            "actor_name": actor_name,
            "location": location or [0.0, 0.0, 0.0],
            "rotation": rotation or [0.0, 0.0, 0.0],
            "set_as_world_solver": set_as_world_solver,
            "overwrite": overwrite,
        }
        raw = _send("chaos_create_solver_actor", inputs)
        return _bridge_result(stage="chaos_create_solver_actor", raw=raw, inputs=inputs, message="Created Chaos Solver actor", t0=t0)

    @mcp.tool()
    async def chaos_configure_solver_actor(
        ctx: Context,
        actor_name: str,
        active: Optional[bool] = None,
        set_as_world_solver: bool = False,
        has_floor: Optional[bool] = None,
        floor_height: Optional[float] = None,
        position_iterations: Optional[int] = None,
        velocity_iterations: Optional[int] = None,
        projection_iterations: Optional[int] = None,
        generate_collision_data: Optional[bool] = None,
        generate_break_data: Optional[bool] = None,
        generate_trailing_data: Optional[bool] = None,
        optimize_runtime_memory: Optional[bool] = None,
        per_advance_breaks_allowed: Optional[int] = None,
        per_advance_breaks_reschedule_limit: Optional[int] = None,
    ) -> str:
        """Configure a Chaos Solver actor's core simulation and event settings.

        KB: see knowledge_base/26_CHAOS_PHYSICS_AND_DESTRUCTION.md#mcp-chaos-and-cloth-tools
        Example:
            chaos_configure_solver_actor(actor_name="ChaosSolver_Destruction", generate_break_data=True, optimize_runtime_memory=True)"""
        t0 = time.monotonic()
        inputs: Dict[str, Any] = {
            "actor_name": actor_name,
            "set_as_world_solver": set_as_world_solver,
        }
        optional_values = {
            "active": active,
            "has_floor": has_floor,
            "floor_height": floor_height,
            "position_iterations": position_iterations,
            "velocity_iterations": velocity_iterations,
            "projection_iterations": projection_iterations,
            "generate_collision_data": generate_collision_data,
            "generate_break_data": generate_break_data,
            "generate_trailing_data": generate_trailing_data,
            "optimize_runtime_memory": optimize_runtime_memory,
            "per_advance_breaks_allowed": per_advance_breaks_allowed,
            "per_advance_breaks_reschedule_limit": per_advance_breaks_reschedule_limit,
        }
        inputs.update({key: value for key, value in optional_values.items() if value is not None})
        raw = _send("chaos_configure_solver_actor", inputs)
        return _bridge_result(stage="chaos_configure_solver_actor", raw=raw, inputs=inputs, message="Configured Chaos Solver actor", t0=t0)

    @mcp.tool()
    async def chaos_inspect_geometry_collection(
        ctx: Context,
        actor_name: str = "",
        asset: str = "",
    ) -> str:
        """Inspect a Geometry Collection actor/component or asset.

        KB: see knowledge_base/26_CHAOS_PHYSICS_AND_DESTRUCTION.md#mcp-chaos-and-cloth-tools
        Example:
            chaos_inspect_geometry_collection(actor_name="BP_DestructibleBarrier_0")"""
        t0 = time.monotonic()
        inputs = {"actor_name": actor_name, "asset": asset}
        raw = _send("chaos_inspect_geometry_collection", inputs)
        return _bridge_result(stage="chaos_inspect_geometry_collection", raw=raw, inputs=inputs, message="Inspected Geometry Collection", t0=t0)

    @mcp.tool()
    async def chaos_configure_geometry_collection(
        ctx: Context,
        actor_name: str,
        simulate_physics: Optional[bool] = None,
        gravity_enabled: Optional[bool] = None,
        enable_clustering: Optional[bool] = None,
        notify_breaks: Optional[bool] = None,
        notify_collisions: Optional[bool] = None,
        enable_damage_from_collision: Optional[bool] = None,
        cluster_group_index: Optional[int] = None,
        max_cluster_level: Optional[int] = None,
        max_simulated_level: Optional[int] = None,
        damage_thresholds: Optional[List[float]] = None,
        solver_actor: Optional[str] = None,
    ) -> str:
        """Configure a Geometry Collection component for Chaos destruction.

        KB: see knowledge_base/26_CHAOS_PHYSICS_AND_DESTRUCTION.md#mcp-chaos-and-cloth-tools
        Example:
            chaos_configure_geometry_collection(actor_name="GC_Barrier_A", simulate_physics=True, notify_breaks=True, damage_thresholds=[500000, 50000, 5000])"""
        t0 = time.monotonic()
        inputs: Dict[str, Any] = {"actor_name": actor_name}
        optional_values = {
            "simulate_physics": simulate_physics,
            "gravity_enabled": gravity_enabled,
            "enable_clustering": enable_clustering,
            "notify_breaks": notify_breaks,
            "notify_collisions": notify_collisions,
            "enable_damage_from_collision": enable_damage_from_collision,
            "cluster_group_index": cluster_group_index,
            "max_cluster_level": max_cluster_level,
            "max_simulated_level": max_simulated_level,
            "damage_thresholds": damage_thresholds,
            "solver_actor": solver_actor,
        }
        inputs.update({key: value for key, value in optional_values.items() if value is not None})
        raw = _send("chaos_configure_geometry_collection", inputs)
        return _bridge_result(stage="chaos_configure_geometry_collection", raw=raw, inputs=inputs, message="Configured Geometry Collection", t0=t0)

    @mcp.tool()
    async def chaos_configure_cloth_component(
        ctx: Context,
        actor_name: str,
        component_name: str = "",
        suspend: Optional[bool] = None,
        allow_cloth_actors: Optional[bool] = None,
        update_in_editor: Optional[bool] = None,
        wait_for_parallel_task: Optional[bool] = None,
        cloth_max_distance_scale: Optional[float] = None,
        cloth_blend_weight: Optional[float] = None,
        force_teleport: bool = False,
        force_reset: bool = False,
        recreate_actors: bool = False,
    ) -> str:
        """Configure cloth simulation on a SkeletalMeshComponent.

        KB: see knowledge_base/26_CHAOS_PHYSICS_AND_DESTRUCTION.md#mcp-chaos-and-cloth-tools
        Example:
            chaos_configure_cloth_component(actor_name="BP_CloakedHero_0", update_in_editor=True, cloth_max_distance_scale=1.0, force_reset=True)"""
        t0 = time.monotonic()
        inputs: Dict[str, Any] = {
            "actor_name": actor_name,
            "component_name": component_name,
            "force_teleport": force_teleport,
            "force_reset": force_reset,
            "recreate_actors": recreate_actors,
        }
        optional_values = {
            "suspend": suspend,
            "allow_cloth_actors": allow_cloth_actors,
            "update_in_editor": update_in_editor,
            "wait_for_parallel_task": wait_for_parallel_task,
            "cloth_max_distance_scale": cloth_max_distance_scale,
            "cloth_blend_weight": cloth_blend_weight,
        }
        inputs.update({key: value for key, value in optional_values.items() if value is not None})
        raw = _send("chaos_configure_cloth_component", inputs)
        return _bridge_result(stage="chaos_configure_cloth_component", raw=raw, inputs=inputs, message="Configured cloth simulation", t0=t0)

    logger.info("Chaos destruction and cloth tools registered")
