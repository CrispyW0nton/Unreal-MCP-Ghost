"""Runtime lifecycle and transport state for Unreal-MCP-Ghost.

This module is a clean-room native-alignment layer. It mirrors useful ideas
from Unreal Engine's native MCP release at the behavior level: explicit server
lifecycle state, transport diagnostics, metadata refresh, and honest gap/legal
notes. It does not copy Epic source and it does not pretend the Python server is
an in-editor Unreal HTTP server.
"""

from __future__ import annotations

import os
import ipaddress
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Mapping, Optional


SERVER_LIFECYCLE_SCHEMA = "unreal_mcp_ghost.server_lifecycle.v1"
SERVER_TRANSPORT_DIAGNOSTICS_SCHEMA = "unreal_mcp_ghost.server_transport_diagnostics.v1"
SERVER_PROTOCOL_CONTRACT_SCHEMA = "unreal_mcp_ghost.server_protocol_contract.v1"
SERVER_METADATA_REFRESH_SCHEMA = "unreal_mcp_ghost.server_metadata_refresh.v1"
SERVER_OPERATION_LIST_SCHEMA = "unreal_mcp_ghost.server_operation_list.v1"
SERVER_OPERATION_STATUS_SCHEMA = "unreal_mcp_ghost.server_operation_status.v1"
SERVER_OPERATION_CANCEL_SCHEMA = "unreal_mcp_ghost.server_operation_cancel.v1"

SUPPORTED_TRANSPORTS = ("stdio", "sse", "streamable-http")
TERMINAL_OPERATION_STATUSES = frozenset({"completed", "failed", "cancelled_before_dispatch"})


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def is_loopback_http_host(host: str) -> bool:
    """Return whether an HTTP bind host is limited to this machine."""

    normalized = str(host or "").strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def bridge_response_succeeded(response: Any) -> bool:
    """Interpret the bridge's legacy and structured response envelopes."""

    if not isinstance(response, Mapping):
        return False
    if str(response.get("status", "")).strip().lower() == "error":
        return False
    if response.get("success") is False or response.get("error"):
        return False
    return True


@dataclass
class RuntimeConfiguration:
    server_name: str = "UnrealMCP"
    transport: str = field(default_factory=lambda: os.environ.get("UNREAL_MCP_TRANSPORT", "stdio") or "stdio")
    mcp_host: str = field(default_factory=lambda: os.environ.get("MCP_SERVER_HOST", "127.0.0.1"))
    mcp_port: int = field(default_factory=lambda: int(os.environ.get("MCP_SERVER_PORT", "8000")))
    unreal_host: str = field(default_factory=lambda: os.environ.get("UNREAL_HOST", "127.0.0.1"))
    unreal_port: int = field(default_factory=lambda: int(os.environ.get("UNREAL_PORT", "55655")))
    tool_search_mode: bool = field(default_factory=lambda: _truthy_env("UNREAL_MCP_TOOL_SEARCH_MODE"))
    direct_tools_enabled: bool = field(default_factory=lambda: not _truthy_env("UNREAL_MCP_TOOL_SEARCH_MODE"))
    sse_tunnel_compatibility: bool = False


class ServerRuntimeState:
    """Tracks lifecycle and transport state without owning the server process."""

    def __init__(self) -> None:
        self.started_monotonic = time.monotonic()
        self.started_at = _utc_now_iso()
        self.status = "created"
        self.configuration = RuntimeConfiguration()
        self._toolset_registry: Any = None
        self._lock = RLock()
        self._events: list[dict[str, Any]] = []
        self._operations: dict[str, dict[str, Any]] = {}
        self._last_unreal_connection: dict[str, Any] = {
            "known": False,
            "connected": False,
            "checked_at": "",
            "detail": "No connection attempt has been recorded.",
        }
        self._warmup: dict[str, Any] = {
            "attempted": False,
            "success": False,
            "detail": "",
            "checked_at": "",
        }

    def configure(
        self,
        *,
        server_name: Optional[str] = None,
        transport: Optional[str] = None,
        mcp_host: Optional[str] = None,
        mcp_port: Optional[int] = None,
        unreal_host: Optional[str] = None,
        unreal_port: Optional[int] = None,
        tool_search_mode: Optional[bool] = None,
        direct_tools_enabled: Optional[bool] = None,
        sse_tunnel_compatibility: Optional[bool] = None,
    ) -> None:
        if server_name is not None:
            self.configuration.server_name = server_name
        if transport is not None:
            self.configuration.transport = transport
        if mcp_host is not None:
            self.configuration.mcp_host = mcp_host
        if mcp_port is not None:
            self.configuration.mcp_port = int(mcp_port)
        if unreal_host is not None:
            self.configuration.unreal_host = unreal_host
        if unreal_port is not None:
            self.configuration.unreal_port = int(unreal_port)
        if tool_search_mode is not None:
            self.configuration.tool_search_mode = bool(tool_search_mode)
        if direct_tools_enabled is not None:
            self.configuration.direct_tools_enabled = bool(direct_tools_enabled)
        if sse_tunnel_compatibility is not None:
            self.configuration.sse_tunnel_compatibility = bool(sse_tunnel_compatibility)

    def attach_toolset_registry(self, registry: Any) -> None:
        self._toolset_registry = registry

    def mark_starting(self, detail: str = "") -> None:
        self.status = "starting"
        self._record_event("starting", detail)

    def mark_running(self, detail: str = "") -> None:
        self.status = "running"
        self._record_event("running", detail)

    def mark_shutting_down(self, detail: str = "") -> None:
        self.status = "shutting_down"
        self._record_event("shutting_down", detail)

    def record_unreal_connection(self, *, connected: bool, detail: str = "") -> None:
        self._last_unreal_connection = {
            "known": True,
            "connected": bool(connected),
            "checked_at": _utc_now_iso(),
            "host": self.configuration.unreal_host,
            "port": self.configuration.unreal_port,
            "detail": detail,
        }

    def record_warmup(self, *, attempted: bool, success: bool, detail: str = "") -> None:
        self._warmup = {
            "attempted": bool(attempted),
            "success": bool(success),
            "detail": detail,
            "checked_at": _utc_now_iso(),
        }

    def begin_operation(
        self,
        *,
        tool_name: str,
        toolset_name: str,
        qualified_name: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        operation_id = f"op_{uuid.uuid4().hex[:16]}"
        operation = {
            "schema": SERVER_OPERATION_STATUS_SCHEMA,
            "operation_id": operation_id,
            "tool_name": tool_name,
            "toolset_name": toolset_name,
            "qualified_name": qualified_name,
            "status": "running",
            "started_at": _utc_now_iso(),
            "finished_at": "",
            "elapsed_seconds": 0.0,
            "metadata": metadata or {},
            "cancellation": {
                "requested": False,
                "requested_at": "",
                "reason": "",
                "mode": "cooperative",
                "can_preempt_running_bridge_command": False,
                "note": "Cancellation is recorded for cooperative tools and diagnostics; existing UE TCP bridge commands rely on timeout/backoff unless a tool explicitly checks this state.",
            },
            "progress": [],
            "result_summary": {},
            "error": "",
        }
        with self._lock:
            self._operations[operation_id] = operation
            self._trim_operations_locked()
            self._append_progress_locked(operation, "queued", "Operation registered.", percent=0.0)
        return operation_id

    def record_operation_progress(
        self,
        operation_id: str,
        *,
        stage: str,
        message: str,
        percent: Optional[float] = None,
        detail: Optional[dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                return
            self._append_progress_locked(operation, stage, message, percent=percent, detail=detail)

    def is_operation_cancel_requested(self, operation_id: str) -> bool:
        with self._lock:
            operation = self._operations.get(operation_id)
            return bool(operation and operation["cancellation"]["requested"])

    def finish_operation(
        self,
        operation_id: str,
        *,
        status: str,
        result: Any = None,
        error: str = "",
    ) -> None:
        with self._lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                return
            operation["status"] = status
            operation["finished_at"] = _utc_now_iso()
            operation["elapsed_seconds"] = _elapsed_seconds(operation.get("started_at", ""), operation["finished_at"])
            operation["error"] = error
            if result is not None:
                operation["result_summary"] = _result_summary(result)
            message = "Operation completed." if status == "completed" else f"Operation ended with status {status}."
            self._append_progress_locked(operation, status, message, percent=1.0)

    def list_operations(self, *, include_completed: bool = False, limit: int = 25) -> dict[str, Any]:
        safe_limit = max(1, min(int(limit), 100))
        with self._lock:
            operations = list(self._operations.values())
            if not include_completed:
                operations = [
                    operation for operation in operations
                    if operation.get("status") not in TERMINAL_OPERATION_STATUSES
                ]
            operations = sorted(operations, key=lambda item: item.get("started_at", ""), reverse=True)[:safe_limit]
            return {
                "schema": SERVER_OPERATION_LIST_SCHEMA,
                "success": True,
                "include_completed": include_completed,
                "limit": safe_limit,
                "count": len(operations),
                "operations": [_operation_summary(operation) for operation in operations],
            }

    def operation_status(self, operation_id: str) -> dict[str, Any]:
        with self._lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                return {
                    "schema": SERVER_OPERATION_STATUS_SCHEMA,
                    "success": False,
                    "operation_id": operation_id,
                    "error": "Unknown operation_id.",
                    "known_operation_ids": sorted(self._operations),
                }
            return {
                "success": True,
                **_copy_operation(operation),
            }

    def request_operation_cancel(self, operation_id: str, *, reason: str = "") -> dict[str, Any]:
        with self._lock:
            operation = self._operations.get(operation_id)
            if operation is None:
                return {
                    "schema": SERVER_OPERATION_CANCEL_SCHEMA,
                    "success": False,
                    "accepted": False,
                    "operation_id": operation_id,
                    "error": "Unknown operation_id.",
                    "known_operation_ids": sorted(self._operations),
                }

            terminal = operation.get("status") in TERMINAL_OPERATION_STATUSES
            if not terminal:
                operation["status"] = "cancel_requested"
            operation["cancellation"]["requested"] = True
            operation["cancellation"]["requested_at"] = _utc_now_iso()
            operation["cancellation"]["reason"] = reason
            self._append_progress_locked(
                operation,
                "cancel_requested",
                "Cancellation requested; cooperative tools can observe this state.",
            )

            return {
                "schema": SERVER_OPERATION_CANCEL_SCHEMA,
                "success": True,
                "accepted": not terminal,
                "operation_id": operation_id,
                "status": operation["status"],
                "reason": reason,
                "note": operation["cancellation"]["note"],
            }

    def lifecycle_snapshot(self) -> dict[str, Any]:
        config = self.configuration
        return {
            "schema": SERVER_LIFECYCLE_SCHEMA,
            "success": True,
            "server_name": config.server_name,
            "status": self.status,
            "started_at": self.started_at,
            "uptime_seconds": round(max(0.0, time.monotonic() - self.started_monotonic), 3),
            "transport": self._transport_summary(),
            "unreal_bridge": dict(self._last_unreal_connection),
            "startup_warmup": dict(self._warmup),
            "tool_catalog": self._tool_catalog_summary(),
            "operations": self._operation_summary(),
            "lifecycle_controls": {
                "start": "process/CLI managed",
                "stop": "process/CLI managed",
                "refresh": "server_refresh_metadata reloads catalog metadata; new Python tools require process restart",
            },
            "native_alignment": [
                "explicit startup/shutdown lifecycle state",
                "transport endpoint and compatibility diagnostics",
                "ToolsetRegistry-style metadata refresh for existing registered tools",
                "cooperative operation ledger for indirect tool dispatch",
                "tool-search mode remains opt-in for broad client compatibility",
            ],
            "legal_review_required": [
                "Do not copy Epic ModelContextProtocol or ToolsetRegistry source into Ghost.",
                "A future Unreal-native in-editor MCP module based closely on Epic internals needs legal review before redistribution.",
            ],
            "recent_events": list(self._events[-10:]),
        }

    def transport_diagnostics(self) -> dict[str, Any]:
        config = self.configuration
        active_transport = config.transport if config.transport in SUPPORTED_TRANSPORTS else "unknown"
        return {
            "schema": SERVER_TRANSPORT_DIAGNOSTICS_SCHEMA,
            "success": True,
            "supported_transports": list(SUPPORTED_TRANSPORTS),
            "active_transport": active_transport,
            "endpoints": self._endpoint_descriptors(),
            "bridge_transport": {
                "kind": "tcp-json",
                "host": config.unreal_host,
                "port": config.unreal_port,
                "owner": "UnrealMCP C++ plugin",
                "note": "Ghost keeps UE editor execution behind its existing TCP bridge.",
            },
            "behavior_reimplemented": [
                "stdio, SSE, and streamable HTTP client surfaces are preserved",
                "sync FastMCP tools are offloaded to worker threads to keep HTTP streams responsive",
                "per-command bridge timeouts return structured errors instead of hanging streams",
                "bridge reconnect/backoff handles editor socket restarts and transient drops",
                "tool-search mode can expose meta-tools only while retaining the full catalog for indirect dispatch",
                "indirect tool calls are recorded as operations with progress events and cooperative cancellation state",
            ],
            "security_posture": {
                "default_http_host": "127.0.0.1",
                "remote_access": "use an authenticated tunnel or reverse proxy; direct non-loopback binds are refused",
                "sse_tunnel_compatibility": config.sse_tunnel_compatibility,
                "sse_dns_rebinding_protection": "disabled in the custom SSE runner only when tunnel compatibility is needed",
            },
            "native_gaps": [
                "Ghost is not yet an Unreal Editor native HTTP MCP server.",
                "Ghost does not expose Epic's private session implementation or in-editor SSE progress stream.",
                "Cancellation is recorded cooperatively; long UE bridge commands remain timeout/backoff based unless individual tools add explicit cancellation checks.",
                "New Python tool functions still require process restart, while metadata can refresh in place.",
            ],
            "compatibility_preserved": [
                "knowledge_base tools and resources",
                "project intelligence tools",
                "higher-level skills",
                "chat/cockpit routes",
                "city/worldbuilding automation",
                "Cursor, Codex, VS Code, Gemini, Claude Code, SSE, streamable HTTP, and stdio clients",
            ],
            "operation_behavior": {
                "tracking_scope": "ToolsetRegistry call_tool indirect dispatch",
                "progress_scope": "server-side stage events; not a replacement for Epic's in-editor SSE progress implementation",
                "cancellation_scope": "cooperative request flag; running TCP bridge commands are not preempted",
            },
        }

    def protocol_contract(self) -> dict[str, Any]:
        """Describe the client-visible MCP protocol contract Ghost owns.

        This intentionally separates Ghost's guarantees from FastMCP's protocol
        implementation and Epic's in-editor native server behavior.
        """

        config = self.configuration
        http_base_url = f"http://{config.mcp_host}:{config.mcp_port}"
        local_http_base_url = f"http://127.0.0.1:{config.mcp_port}"
        return {
            "schema": SERVER_PROTOCOL_CONTRACT_SCHEMA,
            "success": True,
            "server_name": config.server_name,
            "active_transport": config.transport if config.transport in SUPPORTED_TRANSPORTS else "unknown",
            "contract_scope": {
                "ghost_owned": [
                    "CLI-selected transport mode and endpoint reporting",
                    "sync-tool offload wrapper around FastMCP direct dispatch",
                    "ToolsetRegistry-style tool-search mode and indirect call ledger",
                    "structured diagnostics for bridge connectivity, operation status, and cancellation requests",
                    "client config generation for Ghost's stdio, SSE, and streamable HTTP launch modes",
                ],
                "delegated_to_fastmcp": [
                    "JSON-RPC parsing and response envelopes",
                    "MCP initialize/ping/tool-list/tool-call request handling",
                    "streamable HTTP session mechanics exposed by the FastMCP runtime",
                    "stdio framing for local client-launched processes",
                ],
                "unreal_bridge_owned": [
                    "TCP JSON command execution inside Unreal Editor",
                    "per-command bridge timeout/backoff behavior",
                    "editor mutation semantics for individual tools",
                ],
            },
            "endpoints": {
                "stdio": {
                    "supported": True,
                    "active": config.transport == "stdio",
                    "launch": "python unreal_mcp_server/unreal_mcp_server.py --transport stdio",
                    "session_model": "client process owns stdin/stdout lifetime",
                },
                "sse": {
                    "supported": True,
                    "active": config.transport == "sse",
                    "url": f"{http_base_url}/sse",
                    "recommended_local_url": f"{local_http_base_url}/sse",
                    "session_model": "legacy SSE client connection with HTTP POST message channel handled by FastMCP",
                },
                "streamable_http": {
                    "supported": True,
                    "active": config.transport == "streamable-http",
                    "url": f"{http_base_url}/mcp",
                    "recommended_local_url": f"{local_http_base_url}/mcp",
                    "session_model": "streamable HTTP semantics handled by FastMCP; Ghost reports but does not reimplement private session internals",
                },
            },
            "request_headers": {
                "mcp_session_id": {
                    "header": "Mcp-Session-Id",
                    "ghost_behavior": "observed/handled by the active MCP transport runtime when applicable; Ghost does not expose Epic's in-editor session store",
                    "client_guidance": "preserve the header returned by a streamable HTTP MCP client runtime; do not invent cross-client shared session ids",
                },
                "origin": {
                    "header": "Origin",
                    "ghost_behavior": "Ghost restricts its unauthenticated HTTP chat and MCP surfaces to loopback binds",
                    "client_guidance": "use an authenticated tunnel or reverse proxy for remote clients",
                },
                "protocol_version": {
                    "header": "MCP-Protocol-Version",
                    "ghost_behavior": "protocol negotiation is delegated to FastMCP; diagnostics report compatibility posture rather than private Epic validation logic",
                    "client_guidance": "use an MCP client/runtime version compatible with FastMCP streamable HTTP or stdio",
                },
            },
            "json_rpc_surface": {
                "handled_by": "FastMCP plus Ghost-registered tools",
                "expected_methods": [
                    "initialize",
                    "ping",
                    "tools/list",
                    "tools/call",
                    "resources/list",
                    "resources/read",
                    "notifications/cancelled",
                ],
                "tool_listing_modes": {
                    "direct_plus_meta_tools": not config.tool_search_mode,
                    "tool_search_only": config.tool_search_mode,
                    "meta_tools": ["call_tool", "describe_toolset", "list_toolsets", "tool_contribution_contract"],
                },
            },
            "streaming_and_cancellation": {
                "progress_events": "ToolsetRegistry indirect calls record bounded server-side progress events; this is not Epic's in-editor SSE progress stream.",
                "cancellation": "notifications/cancelled and server_cancel_operation are cooperative signals; already-running UE TCP bridge commands are not preempted.",
                "operation_lookup": ["server_list_operations", "server_operation_status", "server_cancel_operation"],
            },
            "security_posture": {
                "default_bind_host": config.mcp_host,
                "recommended_local_bind_host": "127.0.0.1",
                "sse_tunnel_compatibility": config.sse_tunnel_compatibility,
                "unreal_bridge_host": config.unreal_host,
                "unreal_bridge_port": config.unreal_port,
                "notes": [
                    "Prefer localhost binding for desktop clients.",
                    "Use explicit tunnels/firewall rules for remote clients.",
                    "Do not claim parity with Epic's native localhost-origin validation until implemented and tested in Ghost's HTTP stack.",
                ],
            },
            "compatibility_preserved": [
                "stdio clients",
                "legacy SSE clients",
                "streamable HTTP clients",
                "tool-search meta-tool clients",
                "direct tool clients",
                "knowledge_base resources and project workflows",
                "higher-level Ghost skills and city/worldbuilding automation",
            ],
            "native_parity_not_claimed": [
                "Unreal Editor in-process HTTP server",
                "Epic private Mcp-Session-Id store",
                "Epic protocol-version validation implementation",
                "server-side preemption of running editor bridge commands",
                "Epic ToolsetRegistry source or NoRedist implementation details",
            ],
            "legal_review_required": [
                "Any direct embedding of Epic ModelContextProtocol or ToolsetRegistry source.",
                "Any future in-editor MCP module based closely on Epic NoRedist plugin internals.",
            ],
        }

    def refresh_metadata(self, *, dry_run: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": SERVER_METADATA_REFRESH_SCHEMA,
            "success": True,
            "dry_run": dry_run,
            "registry_attached": self._toolset_registry is not None,
            "refresh_scope": [
                "tool inventory category/status/roadmap metadata",
                "runtime lifecycle/transport snapshots",
                "operation list/status/cancel metadata",
                "bridge descriptors on their next tool call",
            ],
            "requires_restart": [
                "adding or removing Python tool functions",
                "changing FastMCP route registration",
                "changing the C++ TCP bridge command dispatcher",
            ],
        }

        if self._toolset_registry is None:
            payload["success"] = False
            payload["error"] = "No ToolsetRegistry facade is attached to the runtime state."
            return payload

        if dry_run:
            payload["would_refresh"] = ["ToolsetRegistry inventory metadata"]
            payload["tool_catalog"] = self._tool_catalog_summary()
            return payload

        refresh = getattr(self._toolset_registry, "refresh_inventory", None)
        if not callable(refresh):
            payload["success"] = False
            payload["error"] = "Attached registry does not support inventory refresh."
            return payload

        payload["tool_inventory"] = refresh()
        payload["tool_catalog"] = self._tool_catalog_summary()
        self._record_event("metadata_refreshed", "Tool inventory metadata reloaded.")
        return payload

    def _transport_summary(self) -> dict[str, Any]:
        config = self.configuration
        return {
            "active": config.transport,
            "tool_search_mode": config.tool_search_mode,
            "direct_tools_enabled": config.direct_tools_enabled,
            "http_host": config.mcp_host,
            "http_port": config.mcp_port,
            "sse_url": f"http://{config.mcp_host}:{config.mcp_port}/sse",
            "streamable_http_url": f"http://{config.mcp_host}:{config.mcp_port}/mcp",
        }

    def _endpoint_descriptors(self) -> list[dict[str, Any]]:
        config = self.configuration
        endpoints = [
            {
                "transport": "stdio",
                "active": config.transport == "stdio",
                "endpoint": "process stdio",
            },
            {
                "transport": "sse",
                "active": config.transport == "sse",
                "endpoint": f"http://{config.mcp_host}:{config.mcp_port}/sse",
            },
            {
                "transport": "streamable-http",
                "active": config.transport == "streamable-http",
                "endpoint": f"http://{config.mcp_host}:{config.mcp_port}/mcp",
            },
        ]
        return endpoints

    def _tool_catalog_summary(self) -> dict[str, Any]:
        registry = self._toolset_registry
        if registry is None:
            return {
                "attached": False,
                "toolset_count": 0,
                "tool_count": 0,
                "mode": "unknown",
            }

        toolsets = getattr(registry, "toolsets", {})
        toolset_count = len(toolsets)
        tool_count = sum(len(getattr(toolset, "tools", {})) for toolset in toolsets.values())
        mode = "tool_search_only" if self.configuration.tool_search_mode else "direct_plus_meta_tools"
        return {
            "attached": True,
            "toolset_count": toolset_count,
            "tool_count": tool_count,
            "mode": mode,
            "meta_tools": ["call_tool", "describe_toolset", "list_toolsets", "tool_contribution_contract"],
        }

    def _operation_summary(self) -> dict[str, Any]:
        with self._lock:
            operations = list(self._operations.values())
            running = [item for item in operations if item.get("status") not in TERMINAL_OPERATION_STATUSES]
            cancel_requested = [item for item in operations if item.get("cancellation", {}).get("requested")]
            return {
                "tracked_count": len(operations),
                "active_count": len(running),
                "cancel_requested_count": len(cancel_requested),
                "recent_operation_ids": [
                    item["operation_id"]
                    for item in sorted(operations, key=lambda value: value.get("started_at", ""), reverse=True)[:5]
                ],
            }

    def _record_event(self, event: str, detail: str = "") -> None:
        self._events.append(
            {
                "event": event,
                "detail": detail,
                "at": _utc_now_iso(),
            }
        )

    def _append_progress_locked(
        self,
        operation: dict[str, Any],
        stage: str,
        message: str,
        *,
        percent: Optional[float] = None,
        detail: Optional[dict[str, Any]] = None,
    ) -> None:
        event: dict[str, Any] = {
            "stage": stage,
            "message": message,
            "at": _utc_now_iso(),
        }
        if percent is not None:
            event["percent"] = max(0.0, min(float(percent), 1.0))
        if detail:
            event["detail"] = detail
        operation.setdefault("progress", []).append(event)
        operation["progress"] = operation["progress"][-25:]

    def _trim_operations_locked(self) -> None:
        if len(self._operations) <= 100:
            return
        ordered = sorted(self._operations.values(), key=lambda item: item.get("started_at", ""))
        removable = [
            item["operation_id"]
            for item in ordered
            if item.get("status") in TERMINAL_OPERATION_STATUSES
        ]
        for operation_id in removable[: len(self._operations) - 100]:
            self._operations.pop(operation_id, None)


def _elapsed_seconds(started_at: str, finished_at: str) -> float:
    try:
        start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finish = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    return round(max(0.0, (finish - start).total_seconds()), 3)


def _result_summary(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return {
            "type": "dict",
            "keys": sorted(str(key) for key in result.keys())[:25],
            "success": result.get("success"),
            "status": result.get("status"),
        }
    if isinstance(result, str):
        return {
            "type": "str",
            "length": len(result),
            "preview": result[:160],
        }
    if isinstance(result, (list, tuple)):
        return {
            "type": type(result).__name__,
            "length": len(result),
        }
    return {"type": type(result).__name__}


def _operation_summary(operation: dict[str, Any]) -> dict[str, Any]:
    return {
        "operation_id": operation["operation_id"],
        "tool_name": operation["tool_name"],
        "toolset_name": operation["toolset_name"],
        "qualified_name": operation["qualified_name"],
        "status": operation["status"],
        "started_at": operation["started_at"],
        "finished_at": operation["finished_at"],
        "elapsed_seconds": operation["elapsed_seconds"],
        "cancel_requested": operation["cancellation"]["requested"],
        "last_progress": operation.get("progress", [])[-1] if operation.get("progress") else {},
    }


def _copy_operation(operation: dict[str, Any]) -> dict[str, Any]:
    return json_safe_copy(operation)


def json_safe_copy(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe_copy(item) for item in value]
    return value


runtime_state = ServerRuntimeState()
