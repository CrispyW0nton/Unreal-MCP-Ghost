"""Gameplay Ability System authoring tools for Unreal MCP.

These wrappers expose native GAS bridge routes for creating Blueprint GAS
assets, recording ability/effect/tag authoring metadata on Blueprints, and
adding ability task factory nodes to ability graphs.
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
        logger.error("gas_tools._send(%s): %s", command, exc)
        return {"success": False, "message": str(exc)}


def _ok(
    *,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    warnings: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": True,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs,
        "warnings": warnings or [],
        "errors": [],
        "log_tail": [],
        "meta": {"tool": stage, "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _err(stage: str, message: str, inputs: Dict[str, Any], t0: float) -> Dict[str, Any]:
    return {
        "success": False,
        "stage": "error",
        "message": message,
        "inputs": inputs,
        "outputs": {},
        "warnings": [],
        "errors": [message],
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
        return json.dumps(_err(stage, msg, inputs, t0))

    outputs = {
        key: value for key, value in raw.items()
        if key not in {"success", "status", "message", "error"}
    }
    return json.dumps(_ok(
        stage=stage,
        message=message,
        inputs=inputs,
        outputs=outputs,
        warnings=warnings,
        t0=t0,
    ))


def _asset_params(
    *,
    name: str,
    path: str,
    parent_class: str,
    overwrite: bool,
) -> Dict[str, Any]:
    params = {"name": name, "path": path, "overwrite": overwrite}
    if parent_class:
        params["parent_class"] = parent_class
    return params


def register_gas_tools(mcp: FastMCP) -> None:  # noqa: C901
    @mcp.tool()
    async def gas_create_ability(
        ctx: Context,
        name: str,
        path: str = "/Game/GAS/Abilities",
        parent_class: str = "",
        overwrite: bool = False,
    ) -> str:
        """Create a Blueprint GameplayAbility asset.

        Args:
            name: Asset name, usually prefixed GA_.
            path: Destination folder under /Game.
            parent_class: Optional parent class path/name. Defaults to UGameplayAbility.
            overwrite: Delete an existing asset with the same path first.

        KB: see knowledge_base/19_GAMEPLAY_ABILITY_SYSTEM.md#mcp-gas-tools
        Example:
            gas_create_ability(name="GA_Dash", path="/Game/GAS/Abilities")
        """
        t0 = time.monotonic()
        params = _asset_params(name=name, path=path, parent_class=parent_class, overwrite=overwrite)
        raw = _send("gas_create_ability", params)
        return _bridge_result(
            stage="gas_create_ability",
            raw=raw,
            inputs=params,
            message=f"Created GameplayAbility Blueprint '{name}'",
            t0=t0,
        )

    @mcp.tool()
    async def gas_create_gameplay_effect(
        ctx: Context,
        name: str,
        path: str = "/Game/GAS/Effects",
        parent_class: str = "",
        overwrite: bool = False,
    ) -> str:
        """Create a Blueprint GameplayEffect asset.

        Args:
            name: Asset name, usually prefixed GE_.
            path: Destination folder under /Game.
            parent_class: Optional parent class path/name. Defaults to UGameplayEffect.
            overwrite: Delete an existing asset with the same path first.

        KB: see knowledge_base/19_GAMEPLAY_ABILITY_SYSTEM.md#mcp-gas-tools
        Example:
            gas_create_gameplay_effect(name="GE_DashCooldown", path="/Game/GAS/Effects")
        """
        t0 = time.monotonic()
        params = _asset_params(name=name, path=path, parent_class=parent_class, overwrite=overwrite)
        raw = _send("gas_create_gameplay_effect", params)
        return _bridge_result(
            stage="gas_create_gameplay_effect",
            raw=raw,
            inputs=params,
            message=f"Created GameplayEffect Blueprint '{name}'",
            t0=t0,
        )

    @mcp.tool()
    async def gas_create_gameplay_cue(
        ctx: Context,
        name: str,
        path: str = "/Game/GAS/Cues",
        notify_type: str = "actor",
        parent_class: str = "",
        overwrite: bool = False,
    ) -> str:
        """Create a GameplayCue notify Blueprint asset.

        Args:
            name: Asset name, usually prefixed GCN_.
            path: Destination folder under /Game.
            notify_type: actor or static. Actor cues can own state; static cues are fire-and-forget.
            parent_class: Optional parent class path/name.
            overwrite: Delete an existing asset with the same path first.

        KB: see knowledge_base/19_GAMEPLAY_ABILITY_SYSTEM.md#mcp-gas-tools
        Example:
            gas_create_gameplay_cue(name="GCN_DashTrail", notify_type="actor")
        """
        t0 = time.monotonic()
        params = _asset_params(name=name, path=path, parent_class=parent_class, overwrite=overwrite)
        params["notify_type"] = notify_type
        raw = _send("gas_create_gameplay_cue", params)
        return _bridge_result(
            stage="gas_create_gameplay_cue",
            raw=raw,
            inputs=params,
            message=f"Created GameplayCue Blueprint '{name}'",
            t0=t0,
        )

    @mcp.tool()
    async def gas_create_attribute_set(
        ctx: Context,
        name: str,
        path: str = "/Game/GAS/Attributes",
        parent_class: str = "",
        overwrite: bool = False,
    ) -> str:
        """Create a Blueprint AttributeSet asset when the project supports it.

        Args:
            name: Asset name, usually prefixed AS_.
            path: Destination folder under /Game.
            parent_class: Optional parent class path/name. Defaults to UAttributeSet.
            overwrite: Delete an existing asset with the same path first.

        KB: see knowledge_base/19_GAMEPLAY_ABILITY_SYSTEM.md#mcp-gas-tools
        Example:
            gas_create_attribute_set(name="AS_HeroCombat", path="/Game/GAS/Attributes")
        """
        t0 = time.monotonic()
        params = _asset_params(name=name, path=path, parent_class=parent_class, overwrite=overwrite)
        raw = _send("gas_create_attribute_set", params)
        return _bridge_result(
            stage="gas_create_attribute_set",
            raw=raw,
            inputs=params,
            message=f"Created AttributeSet Blueprint '{name}'",
            t0=t0,
        )

    @mcp.tool()
    async def gas_grant_ability(
        ctx: Context,
        target_bp: str,
        ability: str,
        level: int = 1,
        input_id: int = -1,
        ensure_asc: bool = True,
    ) -> str:
        """Record a default GameplayAbility grant on a Blueprint and ensure an ASC.

        Args:
            target_bp: Blueprint asset name/path receiving the grant metadata.
            ability: GameplayAbility asset path or class path.
            level: Default grant level.
            input_id: Optional legacy input id. Use -1 when tag/input binding handles activation.
            ensure_asc: Add an AbilitySystemComponent if the Blueprint lacks one.

        KB: see knowledge_base/19_GAMEPLAY_ABILITY_SYSTEM.md#mcp-gas-tools
        Example:
            gas_grant_ability(target_bp="/Game/BP_Hero", ability="/Game/GAS/Abilities/GA_Dash")
        """
        t0 = time.monotonic()
        params = {
            "target_bp": target_bp,
            "ability": ability,
            "level": int(level),
            "input_id": int(input_id),
            "ensure_asc": bool(ensure_asc),
        }
        raw = _send("gas_grant_ability", params)
        return _bridge_result(
            stage="gas_grant_ability",
            raw=raw,
            inputs=params,
            message=f"Recorded ability grant '{ability}' on '{target_bp}'",
            t0=t0,
        )

    @mcp.tool()
    async def gas_apply_effect(
        ctx: Context,
        target_bp: str,
        effect: str,
        level: float = 1.0,
        ensure_asc: bool = True,
    ) -> str:
        """Record a default GameplayEffect application on a Blueprint and ensure an ASC.

        Args:
            target_bp: Blueprint asset name/path receiving the effect metadata.
            effect: GameplayEffect asset path or class path.
            level: Default effect level.
            ensure_asc: Add an AbilitySystemComponent if the Blueprint lacks one.

        KB: see knowledge_base/19_GAMEPLAY_ABILITY_SYSTEM.md#mcp-gas-tools
        Example:
            gas_apply_effect(target_bp="/Game/BP_Hero", effect="/Game/GAS/Effects/GE_StartupStats")
        """
        t0 = time.monotonic()
        params = {
            "target_bp": target_bp,
            "effect": effect,
            "level": float(level),
            "ensure_asc": bool(ensure_asc),
        }
        raw = _send("gas_apply_effect", params)
        return _bridge_result(
            stage="gas_apply_effect",
            raw=raw,
            inputs=params,
            message=f"Recorded effect application '{effect}' on '{target_bp}'",
            t0=t0,
        )

    @mcp.tool()
    async def gas_add_tag(
        ctx: Context,
        target_bp: str,
        tag: str,
        ensure_asc: bool = True,
    ) -> str:
        """Record an owned GameplayTag on a Blueprint and ensure an ASC.

        Args:
            target_bp: Blueprint asset name/path receiving the tag metadata.
            tag: Gameplay tag such as Ability.Movement.Dash or State.Stunned.
            ensure_asc: Add an AbilitySystemComponent if the Blueprint lacks one.

        KB: see knowledge_base/19_GAMEPLAY_ABILITY_SYSTEM.md#mcp-gas-tools
        Example:
            gas_add_tag(target_bp="/Game/BP_Hero", tag="Ability.Movement.Dash")
        """
        t0 = time.monotonic()
        params = {"target_bp": target_bp, "tag": tag, "ensure_asc": bool(ensure_asc)}
        raw = _send("gas_add_tag", params)
        return _bridge_result(
            stage="gas_add_tag",
            raw=raw,
            inputs=params,
            message=f"Recorded GameplayTag '{tag}' on '{target_bp}'",
            t0=t0,
        )

    @mcp.tool()
    async def gas_create_ability_task_node(
        ctx: Context,
        blueprint_name: str,
        task_class: str,
        graph_name: str = "EventGraph",
        task_function: str = "",
        position_x: int = 0,
        position_y: int = 0,
    ) -> str:
        """Add an AbilityTask factory call node to a GameplayAbility Blueprint graph.

        Args:
            blueprint_name: GameplayAbility Blueprint asset name/path.
            task_class: AbilityTask class path/name, e.g. AbilityTask_WaitDelay.
            graph_name: Target graph. Default EventGraph.
            task_function: Optional static BlueprintCallable factory function name.
            position_x: Node canvas X coordinate.
            position_y: Node canvas Y coordinate.

        KB: see knowledge_base/19_GAMEPLAY_ABILITY_SYSTEM.md#mcp-gas-tools
        Example:
            gas_create_ability_task_node(blueprint_name="/Game/GAS/Abilities/GA_Dash", task_class="AbilityTask_WaitDelay")
        """
        t0 = time.monotonic()
        params = {
            "blueprint_name": blueprint_name,
            "task_class": task_class,
            "graph_name": graph_name,
            "task_function": task_function,
            "node_position": {"x": int(position_x), "y": int(position_y)},
        }
        raw = _send("gas_create_ability_task_node", params)
        return _bridge_result(
            stage="gas_create_ability_task_node",
            raw=raw,
            inputs=params,
            message=f"Added ability task node '{task_class}' to '{blueprint_name}.{graph_name}'",
            t0=t0,
        )

    logger.info(
        "GAS tools registered: gas_create_ability, gas_create_gameplay_effect, "
        "gas_create_gameplay_cue, gas_create_attribute_set, gas_grant_ability, "
        "gas_apply_effect, gas_add_tag, gas_create_ability_task_node"
    )
