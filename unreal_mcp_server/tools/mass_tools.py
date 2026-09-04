"""MassEntity, StateTree, and SmartObject authoring tools for UE5."""

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

    warnings = raw.get("warnings") if isinstance(raw.get("warnings"), list) else []
    outputs = {
        key: value for key, value in raw.items()
        if key not in {"success", "status", "message", "error", "warnings"}
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


def register_mass_tools(mcp: FastMCP):

    @mcp.tool()
    async def mass_create_entity_config(
        ctx: Context,
        name: str,
        path: str = "/Game/Mass/EntityConfigs",
        parent_config: str = "",
        traits: Optional[List[str]] = None,
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a MassEntity config asset and optionally seed trait classes.

        Args:
            name: Asset name to create.
            path: Content Browser folder under /Game.
            parent_config: Optional parent MassEntity config asset path.
            traits: Optional MassEntity trait classes, short names or /Script paths.
            overwrite: Delete an existing asset before creation.
            save: Save the asset package after creation.

        Returns:
            Structured JSON with asset path, trait list, and config GUID.

        KB: see knowledge_base/23_MASS_ENTITY_AND_STATETREE.md#mcp-mass-statetree-and-smartobject-tools
        Example:
            mass_create_entity_config(name="EC_CrowdAgent", traits=["MassAssortedFragmentsTrait"])"""
        t0 = time.monotonic()
        inputs = {
            "name": name,
            "path": path,
            "parent_config": parent_config,
            "traits": traits or [],
            "overwrite": overwrite,
            "save": save,
        }
        raw = _send("mass_create_entity_config", inputs)
        return _bridge_result(stage="mass_create_entity_config", raw=raw, inputs=inputs, message="Created MassEntity config", t0=t0)

    @mcp.tool()
    async def mass_add_trait(
        ctx: Context,
        config_asset: str,
        trait_class: str,
        save: bool = True,
    ) -> str:
        """Add a trait class to a MassEntity config asset.

        Args:
            config_asset: MassEntity config asset path or object path.
            trait_class: MassEntity trait class, short name or /Script path.
            save: Save the asset after mutation.

        Returns:
            Structured JSON with the added trait and updated trait list.

        KB: see knowledge_base/23_MASS_ENTITY_AND_STATETREE.md#mcp-mass-statetree-and-smartobject-tools
        Example:
            mass_add_trait(config_asset="/Game/Mass/EntityConfigs/EC_CrowdAgent", trait_class="MassLODTrait")"""
        t0 = time.monotonic()
        inputs = {"config_asset": config_asset, "trait_class": trait_class, "save": save}
        raw = _send("mass_add_trait", inputs)
        return _bridge_result(stage="mass_add_trait", raw=raw, inputs=inputs, message="Added MassEntity trait", t0=t0)

    @mcp.tool()
    async def mass_inspect_entity_config(
        ctx: Context,
        config_asset: str,
        validate: bool = False,
    ) -> str:
        """Inspect traits, parent config, and optional validation for a MassEntity config.

        Args:
            config_asset: MassEntity config asset path or object path.
            validate: Validate the entity template against the editor world when available.

        Returns:
            Structured JSON with trait details, parent path, and validation status.

        KB: see knowledge_base/23_MASS_ENTITY_AND_STATETREE.md#mcp-mass-statetree-and-smartobject-tools
        Example:
            mass_inspect_entity_config(config_asset="/Game/Mass/EntityConfigs/EC_CrowdAgent", validate=True)"""
        t0 = time.monotonic()
        inputs = {"config_asset": config_asset, "validate": validate}
        raw = _send("mass_inspect_entity_config", inputs)
        return _bridge_result(stage="mass_inspect_entity_config", raw=raw, inputs=inputs, message="Inspected MassEntity config", t0=t0)

    @mcp.tool()
    async def statetree_create(
        ctx: Context,
        name: str,
        path: str = "/Game/AI/StateTrees",
        schema_class: str = "/Script/GameplayStateTreeModule.StateTreeComponentSchema",
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a StateTree asset with an editor schema.

        Args:
            name: Asset name to create.
            path: Content Browser folder under /Game.
            schema_class: StateTree schema class, short name or /Script path.
            overwrite: Delete an existing asset before creation.
            save: Save the asset package after creation.

        Returns:
            Structured JSON with asset path, schema class, and readiness info.

        KB: see knowledge_base/23_MASS_ENTITY_AND_STATETREE.md#mcp-mass-statetree-and-smartobject-tools
        Example:
            statetree_create(name="ST_CombatBrain", schema_class="StateTreeComponentSchema")"""
        t0 = time.monotonic()
        inputs = {
            "name": name,
            "path": path,
            "schema_class": schema_class,
            "overwrite": overwrite,
            "save": save,
        }
        raw = _send("statetree_create", inputs)
        return _bridge_result(stage="statetree_create", raw=raw, inputs=inputs, message="Created StateTree asset", t0=t0)

    @mcp.tool()
    async def statetree_add_state(
        ctx: Context,
        state_tree: str,
        name: str,
        parent_state: str = "",
        description: str = "",
        state_type: str = "state",
        as_subtree: bool = False,
        enabled: bool = True,
        save: bool = True,
    ) -> str:
        """Add a root subtree or child state to a StateTree asset.

        Args:
            state_tree: StateTree asset path or object path.
            name: State display name to add.
            parent_state: Optional parent state name or GUID. Empty uses the first root.
            description: Optional editor description for the state.
            state_type: "state", "group", "linked", "linked_asset", or "subtree".
            as_subtree: Add as a top-level subtree instead of child state.
            enabled: Initial enabled flag.
            save: Save the asset after mutation.

        Returns:
            Structured JSON with inserted state details and state counts.

        KB: see knowledge_base/23_MASS_ENTITY_AND_STATETREE.md#mcp-mass-statetree-and-smartobject-tools
        Example:
            statetree_add_state(state_tree="/Game/AI/StateTrees/ST_CombatBrain", name="Patrol", parent_state="Root")"""
        t0 = time.monotonic()
        inputs = {
            "state_tree": state_tree,
            "name": name,
            "parent_state": parent_state,
            "description": description,
            "state_type": state_type,
            "as_subtree": as_subtree,
            "enabled": enabled,
            "save": save,
        }
        raw = _send("statetree_add_state", inputs)
        return _bridge_result(stage="statetree_add_state", raw=raw, inputs=inputs, message="Added StateTree state", t0=t0)

    @mcp.tool()
    async def statetree_inspect(
        ctx: Context,
        state_tree: str,
    ) -> str:
        """Inspect a StateTree asset's schema, readiness, and editor state hierarchy.

        Args:
            state_tree: StateTree asset path or object path.

        Returns:
            Structured JSON with schema, compiled state count, and state hierarchy.

        KB: see knowledge_base/23_MASS_ENTITY_AND_STATETREE.md#mcp-mass-statetree-and-smartobject-tools
        Example:
            statetree_inspect(state_tree="/Game/AI/StateTrees/ST_CombatBrain")"""
        t0 = time.monotonic()
        inputs = {"state_tree": state_tree}
        raw = _send("statetree_inspect", inputs)
        return _bridge_result(stage="statetree_inspect", raw=raw, inputs=inputs, message="Inspected StateTree asset", t0=t0)

    @mcp.tool()
    async def smartobject_create_definition(
        ctx: Context,
        name: str,
        path: str = "/Game/AI/SmartObjects",
        slot_name: str = "Default",
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a SmartObject definition asset and optional default slot.

        Args:
            name: Asset name to create.
            path: Content Browser folder under /Game.
            slot_name: Optional first slot name; empty creates no slot.
            overwrite: Delete an existing asset before creation.
            save: Save the asset package after creation.

        Returns:
            Structured JSON with asset path and slot count.

        KB: see knowledge_base/23_MASS_ENTITY_AND_STATETREE.md#mcp-mass-statetree-and-smartobject-tools
        Example:
            smartobject_create_definition(name="SO_CoverPoint", slot_name="UseCover")"""
        t0 = time.monotonic()
        inputs = {"name": name, "path": path, "slot_name": slot_name, "overwrite": overwrite, "save": save}
        raw = _send("smartobject_create_definition", inputs)
        return _bridge_result(stage="smartobject_create_definition", raw=raw, inputs=inputs, message="Created SmartObject definition", t0=t0)

    @mcp.tool()
    async def smartobject_add_slot(
        ctx: Context,
        definition: str,
        slot_name: str = "Slot",
        offset: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        activity_tags: Optional[List[str]] = None,
        runtime_tags: Optional[List[str]] = None,
        enabled: bool = True,
        save: bool = True,
    ) -> str:
        """Add a slot to a SmartObject definition.

        Args:
            definition: SmartObject definition asset path or object path.
            slot_name: Editor display name for the slot.
            offset: Slot offset [x, y, z] in definition space.
            rotation: Slot rotation [pitch, yaw, roll].
            activity_tags: Gameplay tags describing slot activities.
            runtime_tags: Initial runtime tags for the slot.
            enabled: Initial enabled flag.
            save: Save the asset after mutation.

        Returns:
            Structured JSON with added slot details, tag warnings, and slot count.

        KB: see knowledge_base/23_MASS_ENTITY_AND_STATETREE.md#mcp-mass-statetree-and-smartobject-tools
        Example:
            smartobject_add_slot(definition="/Game/AI/SmartObjects/SO_CoverPoint", slot_name="LeftPeek", offset=[0, -60, 0])"""
        t0 = time.monotonic()
        inputs = {
            "definition": definition,
            "slot_name": slot_name,
            "offset": offset or [0.0, 0.0, 0.0],
            "rotation": rotation or [0.0, 0.0, 0.0],
            "activity_tags": activity_tags or [],
            "runtime_tags": runtime_tags or [],
            "enabled": enabled,
            "save": save,
        }
        raw = _send("smartobject_add_slot", inputs)
        return _bridge_result(stage="smartobject_add_slot", raw=raw, inputs=inputs, message="Added SmartObject slot", t0=t0)

    @mcp.tool()
    async def smartobject_inspect_definition(
        ctx: Context,
        definition: str,
    ) -> str:
        """Inspect a SmartObject definition's slots, tags, and bounds.

        Args:
            definition: SmartObject definition asset path or object path.

        Returns:
            Structured JSON with slot names, transforms, tag containers, and bounds.

        KB: see knowledge_base/23_MASS_ENTITY_AND_STATETREE.md#mcp-mass-statetree-and-smartobject-tools
        Example:
            smartobject_inspect_definition(definition="/Game/AI/SmartObjects/SO_CoverPoint")"""
        t0 = time.monotonic()
        inputs = {"definition": definition}
        raw = _send("smartobject_inspect_definition", inputs)
        return _bridge_result(stage="smartobject_inspect_definition", raw=raw, inputs=inputs, message="Inspected SmartObject definition", t0=t0)
