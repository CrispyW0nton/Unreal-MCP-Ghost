"""Native-alignment runtime lifecycle and transport tools."""

from __future__ import annotations

import json

from mcp.server.fastmcp import Context, FastMCP

from server_runtime import runtime_state


def register_server_runtime_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def server_lifecycle_status(ctx: Context) -> str:
        """Report Ghost server lifecycle, transport, bridge, and catalog state."""

        return json.dumps(runtime_state.lifecycle_snapshot(), indent=2, sort_keys=True)

    @mcp.tool()
    def server_transport_diagnostics(ctx: Context) -> str:
        """Describe active MCP transport behavior, compatibility, security posture, and native gaps."""

        return json.dumps(runtime_state.transport_diagnostics(), indent=2, sort_keys=True)

    @mcp.tool()
    def server_protocol_contract(ctx: Context) -> str:
        """Describe Ghost's client-visible MCP protocol contract and native parity boundaries."""

        return json.dumps(runtime_state.protocol_contract(), indent=2, sort_keys=True)

    @mcp.tool()
    def server_refresh_metadata(ctx: Context, dry_run: bool = True) -> str:
        """Refresh runtime metadata that can safely update without re-registering Python tools."""

        return json.dumps(runtime_state.refresh_metadata(dry_run=dry_run), indent=2, sort_keys=True)

    @mcp.tool()
    def server_list_operations(ctx: Context, include_completed: bool = False, limit: int = 25) -> str:
        """List tracked indirect tool operations and their latest progress event."""

        return json.dumps(
            runtime_state.list_operations(include_completed=include_completed, limit=limit),
            indent=2,
            sort_keys=True,
        )

    @mcp.tool()
    def server_operation_status(ctx: Context, operation_id: str) -> str:
        """Return detailed progress and cancellation state for one operation."""

        return json.dumps(runtime_state.operation_status(operation_id), indent=2, sort_keys=True)

    @mcp.tool()
    def server_cancel_operation(ctx: Context, operation_id: str, reason: str = "") -> str:
        """Request cooperative cancellation for a tracked operation."""

        return json.dumps(
            runtime_state.request_operation_cancel(operation_id, reason=reason),
            indent=2,
            sort_keys=True,
        )
