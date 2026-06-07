"""HTTP routes for UE editor chat integration."""

from __future__ import annotations

import json
from typing import Any, Dict

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .storage import (
    append_message,
    clear_history,
    create_session,
    delete_session,
    export_session_markdown,
    get_recent_messages,
    list_sessions,
    pin_session,
    poll_messages,
    rename_session,
)
from tools.knowledge_tools import _tool_discovery_payload


def _error(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"status": "error", "error": message}, status_code=status_code)


async def chat_send(request: Request) -> Response:
    """POST /chat/send."""
    try:
        payload: Dict[str, Any] = await request.json()
    except json.JSONDecodeError:
        return _error("Invalid JSON body")

    session = request.query_params.get("session") or str(payload.get("session") or "")
    try:
        entry = append_message(payload, session=session or None)
    except ValueError as exc:
        return _error(str(exc))
    except Exception as exc:
        return _error(f"Failed to store message: {exc}", status_code=500)

    return JSONResponse({"status": "ok", "message_id": entry["message_id"]})


async def chat_poll(request: Request) -> Response:
    """GET /chat/poll?since=<ISO8601>&sender=<human|agent>."""
    sender = request.query_params.get("sender")
    since = request.query_params.get("since")
    session = request.query_params.get("session")

    try:
        messages = poll_messages(since=since, sender=sender, session=session)
    except ValueError as exc:
        return _error(str(exc))
    except Exception as exc:
        return _error(f"Failed to poll messages: {exc}", status_code=500)

    return JSONResponse({"messages": messages})


async def chat_history(request: Request) -> Response:
    """GET /chat/history?limit=N."""
    raw_limit = request.query_params.get("limit", "50")
    session = request.query_params.get("session")
    try:
        limit = int(raw_limit)
    except ValueError:
        return _error("limit must be an integer")

    try:
        messages = get_recent_messages(limit=limit, session=session)
    except Exception as exc:
        return _error(f"Failed to read history: {exc}", status_code=500)

    return JSONResponse({"messages": messages})


async def chat_clear(request: Request) -> Response:
    """POST /chat/clear."""
    session = request.query_params.get("session")
    try:
        clear_history(session=session)
    except Exception as exc:
        return _error(f"Failed to clear history: {exc}", status_code=500)
    return JSONResponse({"status": "ok"})


async def chat_sessions(request: Request) -> Response:
    """GET /chat/sessions."""
    try:
        return JSONResponse({"status": "ok", **list_sessions()})
    except Exception as exc:
        return _error(f"Failed to list sessions: {exc}", status_code=500)


async def chat_session_new(request: Request) -> Response:
    """POST /chat/session/new."""
    try:
        payload: Dict[str, Any] = await request.json()
    except json.JSONDecodeError:
        return _error("Invalid JSON body")
    name = str(payload.get("name") or "default")
    try:
        session = create_session(name)
    except Exception as exc:
        return _error(f"Failed to create session: {exc}", status_code=500)
    return JSONResponse({"status": "ok", "session": session})


async def chat_session_rename(request: Request) -> Response:
    """POST /chat/session/rename."""
    try:
        payload: Dict[str, Any] = await request.json()
    except json.JSONDecodeError:
        return _error("Invalid JSON body")
    try:
        result = rename_session(str(payload.get("old_name") or ""), str(payload.get("new_name") or ""))
    except ValueError as exc:
        return _error(str(exc))
    except Exception as exc:
        return _error(f"Failed to rename session: {exc}", status_code=500)
    return JSONResponse({"status": "ok", "session": result})


async def chat_session_pin(request: Request) -> Response:
    """POST /chat/session/pin."""
    try:
        payload: Dict[str, Any] = await request.json()
    except json.JSONDecodeError:
        return _error("Invalid JSON body")
    try:
        result = pin_session(str(payload.get("name") or ""), bool(payload.get("pinned", True)))
    except Exception as exc:
        return _error(f"Failed to pin session: {exc}", status_code=500)
    return JSONResponse({"status": "ok", "session": result})


async def chat_session_delete(request: Request) -> Response:
    """POST /chat/session/delete."""
    try:
        payload: Dict[str, Any] = await request.json()
    except json.JSONDecodeError:
        return _error("Invalid JSON body")
    try:
        result = delete_session(str(payload.get("name") or ""))
    except Exception as exc:
        return _error(f"Failed to delete session: {exc}", status_code=500)
    return JSONResponse({"status": "ok", "session": result})


async def chat_session_export(request: Request) -> Response:
    """GET /chat/session/export?name=<session>."""
    name = request.query_params.get("name", "default")
    try:
        markdown = export_session_markdown(name)
    except Exception as exc:
        return _error(f"Failed to export session: {exc}", status_code=500)
    return Response(markdown, media_type="text/markdown")


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
    mcp.custom_route("/chat/sessions", methods=["GET"], name="chat_sessions")(chat_sessions)
    mcp.custom_route("/chat/session/new", methods=["POST"], name="chat_session_new")(chat_session_new)
    mcp.custom_route("/chat/session/rename", methods=["POST"], name="chat_session_rename")(chat_session_rename)
    mcp.custom_route("/chat/session/pin", methods=["POST"], name="chat_session_pin")(chat_session_pin)
    mcp.custom_route("/chat/session/delete", methods=["POST"], name="chat_session_delete")(chat_session_delete)
    mcp.custom_route("/chat/session/export", methods=["GET"], name="chat_session_export")(chat_session_export)
    mcp.custom_route("/tools/list", methods=["GET"], name="tools_list")(tools_list)

