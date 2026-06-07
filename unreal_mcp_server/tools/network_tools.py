"""Networking and replication authoring tools for Unreal MCP.

These B.4 wrappers provide a focused StructuredResult surface for replicated
Blueprint variables, RPC Custom Events, replicated components, role/authority
graph helpers, and replication graph/runtime state inspection.
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
        logger.error("network_tools._send(%s): %s", command, exc)
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


def _normalize_rpc_type(rpc_type: str) -> str:
    value = (rpc_type or "server").strip().lower().replace("-", "_")
    aliases = {
        "multicast": "net_multicast",
        "netmulticast": "net_multicast",
        "net_multicast": "net_multicast",
        "server": "server",
        "client": "client",
        "none": "none",
    }
    return aliases.get(value, value)


def register_network_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    async def net_set_property_replicated(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        replicated: bool = True,
        repnotify: bool = False,
        replication_condition: str = "none",
        save: bool = True,
        compile: bool = True,
    ) -> str:
        """Configure an existing Blueprint variable for replication or RepNotify.

        Args:
            blueprint_name: Actor Blueprint asset name or path.
            variable_name: Existing Blueprint member variable.
            replicated: Enable replication when True; disable when False.
            repnotify: Use RepNotify instead of plain replication.
            replication_condition: Lifetime condition such as none, owner_only, or skip_owner.
            save: Save the Blueprint package after mutation.
            compile: Compile the Blueprint after mutation.

        KB: see knowledge_base/20_NETWORKING_AND_REPLICATION.md#mcp-network-tools
        Example:
            net_set_property_replicated(blueprint_name="/Game/BP_Door", variable_name="bIsOpen", repnotify=True)
        """
        t0 = time.monotonic()
        replication_mode = "repnotify" if repnotify else ("replicated" if replicated else "none")
        params = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "replicated": bool(replicated),
            "repnotify": bool(repnotify),
            "replication_mode": replication_mode,
            "replication_condition": replication_condition,
            "save": bool(save),
            "compile": bool(compile),
        }
        raw = _send("net_set_property_replicated", params)
        return _bridge_result(
            stage="net_set_property_replicated",
            raw=raw,
            inputs=params,
            message=f"Configured replication for '{blueprint_name}.{variable_name}'",
            t0=t0,
        )

    @mcp.tool()
    async def net_set_function_rpc(
        ctx: Context,
        blueprint_name: str,
        function_name: str,
        rpc_type: str = "server",
        reliable: bool = True,
        create_if_missing: bool = True,
        inputs: Optional[List[Dict[str, str]]] = None,
        node_position: Optional[List[float]] = None,
        save: bool = True,
        compile: bool = True,
    ) -> str:
        """Create or configure a Blueprint Custom Event as an RPC.

        Args:
            blueprint_name: Actor Blueprint asset name or path.
            function_name: Custom Event/function name to configure.
            rpc_type: server, client, netmulticast, net_multicast, multicast, or none.
            reliable: Mark the RPC reliable when True.
            create_if_missing: Create the Custom Event if it does not already exist.
            inputs: Optional typed input pins, e.g. [{"name": "Damage", "type": "Float"}].
            node_position: Optional [X, Y] graph position for newly created events.
            save: Save the Blueprint package after mutation.
            compile: Compile the Blueprint after mutation.

        KB: see knowledge_base/20_NETWORKING_AND_REPLICATION.md#mcp-network-tools
        Example:
            net_set_function_rpc(blueprint_name="/Game/BP_Door", function_name="Server_RequestOpen", rpc_type="server")
        """
        t0 = time.monotonic()
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "function_name": function_name,
            "event_name": function_name,
            "rpc_type": _normalize_rpc_type(rpc_type),
            "reliable": bool(reliable),
            "create_if_missing": bool(create_if_missing),
            "save": bool(save),
            "compile": bool(compile),
        }
        if inputs:
            params["inputs"] = inputs
        if node_position:
            params["node_position"] = node_position
        raw = _send("net_set_function_rpc", params)
        return _bridge_result(
            stage="net_set_function_rpc",
            raw=raw,
            inputs=params,
            message=f"Configured RPC '{function_name}' on '{blueprint_name}'",
            t0=t0,
        )

    @mcp.tool()
    async def net_set_replication_condition(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        replication_condition: str,
        replication_mode: str = "replicated",
        save: bool = True,
        compile: bool = True,
    ) -> str:
        """Set the lifetime replication condition for a Blueprint variable.

        Args:
            blueprint_name: Actor Blueprint asset name or path.
            variable_name: Existing Blueprint member variable.
            replication_condition: Condition such as none, initial_only, owner_only, or skip_owner.
            replication_mode: replicated, repnotify, or none.
            save: Save the Blueprint package after mutation.
            compile: Compile the Blueprint after mutation.

        KB: see knowledge_base/20_NETWORKING_AND_REPLICATION.md#mcp-network-tools
        Example:
            net_set_replication_condition(blueprint_name="/Game/BP_Door", variable_name="bIsOpen", replication_condition="owner_only")
        """
        t0 = time.monotonic()
        params = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "replication_condition": replication_condition,
            "replication_mode": replication_mode,
            "save": bool(save),
            "compile": bool(compile),
        }
        raw = _send("net_set_replication_condition", params)
        return _bridge_result(
            stage="net_set_replication_condition",
            raw=raw,
            inputs=params,
            message=f"Set replication condition for '{blueprint_name}.{variable_name}'",
            t0=t0,
        )

    @mcp.tool()
    async def net_add_replicated_component(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        component_type: str = "",
        replicates: bool = True,
        create_if_missing: bool = True,
        save: bool = True,
        compile: bool = False,
    ) -> str:
        """Create or configure a Blueprint component template for replication.

        Args:
            blueprint_name: Actor Blueprint asset name or path.
            component_name: SCS component template variable name.
            component_type: Optional component class/name to create when missing.
            replicates: Component replication flag.
            create_if_missing: Create the component when component_type is supplied and it is absent.
            save: Save the Blueprint package after mutation.
            compile: Compile the Blueprint after mutation.

        KB: see knowledge_base/20_NETWORKING_AND_REPLICATION.md#mcp-network-tools
        Example:
            net_add_replicated_component(blueprint_name="/Game/BP_Door", component_name="ReplicatedMesh", component_type="StaticMeshComponent")
        """
        t0 = time.monotonic()
        params = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "component_type": component_type,
            "replicates": bool(replicates),
            "create_if_missing": bool(create_if_missing),
            "save": bool(save),
            "compile": bool(compile),
        }
        raw = _send("net_add_replicated_component", params)
        return _bridge_result(
            stage="net_add_replicated_component",
            raw=raw,
            inputs=params,
            message=f"Configured replicated component '{component_name}' on '{blueprint_name}'",
            t0=t0,
        )

    @mcp.tool()
    async def net_set_role_override(
        ctx: Context,
        blueprint_name: str,
        node_position: Optional[List[float]] = None,
        save: bool = True,
        compile: bool = False,
    ) -> str:
        """Add a role-switch helper node for authority/role-specific Blueprint flow.

        Args:
            blueprint_name: Actor Blueprint asset name or path.
            node_position: Optional [X, Y] graph position.
            save: Save the Blueprint package after mutation.
            compile: Compile the Blueprint after mutation.

        KB: see knowledge_base/20_NETWORKING_AND_REPLICATION.md#mcp-network-tools
        Example:
            net_set_role_override(blueprint_name="/Game/BP_Door", node_position=[400, 0])
        """
        t0 = time.monotonic()
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "save": bool(save),
            "compile": bool(compile),
        }
        if node_position:
            params["node_position"] = node_position
        raw = _send("net_set_role_override", params)
        return _bridge_result(
            stage="net_set_role_override",
            raw=raw,
            inputs=params,
            message=f"Added role override/switch helper to '{blueprint_name}'",
            t0=t0,
        )

    @mcp.tool()
    async def net_get_replication_graph_state(
        ctx: Context,
        max_actors: int = 25,
    ) -> str:
        """Inspect runtime replication graph/net driver state for the active world.

        Args:
            max_actors: Maximum replicated actor samples to include.

        KB: see knowledge_base/20_NETWORKING_AND_REPLICATION.md#mcp-network-tools
        Example:
            net_get_replication_graph_state(max_actors=10)
        """
        t0 = time.monotonic()
        params = {"max_actors": int(max_actors)}
        raw = _send("net_get_replication_graph_state", params)
        return _bridge_result(
            stage="net_get_replication_graph_state",
            raw=raw,
            inputs=params,
            message="Captured replication graph/net driver state",
            t0=t0,
        )

    logger.info(
        "Network tools registered: net_set_property_replicated, net_set_function_rpc, "
        "net_set_replication_condition, net_add_replicated_component, "
        "net_set_role_override, net_get_replication_graph_state"
    )
