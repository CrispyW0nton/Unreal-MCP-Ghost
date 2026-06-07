"""HTTP routes for UE editor chat integration."""

from __future__ import annotations

import json
from typing import Any, Dict

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .storage import append_message, clear_history, get_recent_messages, poll_messages
from tools.knowledge_tools import _tool_discovery_payload


def _error(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"status": "error", "error": message}, status_code=status_code)


async def chat_send(request: Request) -> Response:
    """POST /chat/send."""
    try:
        payload: Dict[str, Any] = await request.json()
    except json.JSONDecodeError:
        return _error("Invalid JSON body")

    try:
        entry = append_message(payload)
    except ValueError as exc:
        return _error(str(exc))
    except Exception as exc:
        return _error(f"Failed to store message: {exc}", status_code=500)

    return JSONResponse({"status": "ok", "message_id": entry["message_id"]})


async def chat_poll(request: Request) -> Response:
    """GET /chat/poll?since=<ISO8601>&sender=<human|agent>."""
    sender = request.query_params.get("sender")
    since = request.query_params.get("since")

    try:
        messages = poll_messages(since=since, sender=sender)
    except ValueError as exc:
        return _error(str(exc))
    except Exception as exc:
        return _error(f"Failed to poll messages: {exc}", status_code=500)

    return JSONResponse({"messages": messages})


async def chat_history(request: Request) -> Response:
    """GET /chat/history?limit=N."""
    raw_limit = request.query_params.get("limit", "50")
    try:
        limit = int(raw_limit)
    except ValueError:
        return _error("limit must be an integer")

    try:
        messages = get_recent_messages(limit=limit)
    except Exception as exc:
        return _error(f"Failed to read history: {exc}", status_code=500)

    return JSONResponse({"messages": messages})


async def chat_clear(request: Request) -> Response:
    """POST /chat/clear."""
    try:
        clear_history()
    except Exception as exc:
        return _error(f"Failed to clear history: {exc}", status_code=500)
    return JSONResponse({"status": "ok"})


def register_chat_routes(mcp) -> None:
    """Register chat HTTP endpoints on FastMCP."""
    async def tools_list(request: Request) -> Response:
        """GET /tools/list?domain=<domain>."""
        domain = request.query_params.get("domain", "all")
        return JSONResponse(_tool_discovery_payload(mcp, domain))

    mcp.custom_route("/chat/send", methods=["POST"], name="chat_send")(chat_send)
    mcp.custom_route("/chat/poll", methods=["GET"], name="chat_poll")(chat_poll)
    mcp.custom_route("/chat/history", methods=["GET"], name="chat_history")(chat_history)
    mcp.custom_route("/chat/clear", methods=["POST"], name="chat_clear")(chat_clear)
    mcp.custom_route("/tools/list", methods=["GET"], name="tools_list")(tools_list)

