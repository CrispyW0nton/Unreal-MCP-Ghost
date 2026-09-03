"""MCP tools for the UE editor chat bridge."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from chat.cockpit import build_cockpit_overview, build_ledger_detail, build_session_list_payload, build_session_resume_context
from chat.storage import append_message, get_recent_messages, poll_messages, utc_now_iso

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
_KB_ROOT = _REPO_ROOT / "knowledge_base"
_LAST_HUMAN_POLL_SINCE: Dict[str, str] = {}


def _make_result(
    *,
    success: bool,
    stage: str,
    message: str,
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    return json.dumps({
        "success": success,
        "stage": stage,
        "message": message,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": meta or {},
    }, ensure_ascii=False)


def _meta(tool: str, started: float, **extra: Any) -> Dict[str, Any]:
    data = {"tool": tool, "duration_ms": int((time.monotonic() - started) * 1000)}
    data.update(extra)
    return data


def _read_excerpt(path: Path, max_chars: int = 1200) -> Dict[str, Any]:
    if not path.exists():
        return {
            "path": str(path.relative_to(_REPO_ROOT)),
            "exists": False,
            "excerpt": "",
            "headings": [],
        }

    text = path.read_text(encoding="utf-8", errors="replace")
    headings = [
        line.strip()
        for line in text.splitlines()
        if line.startswith("#")
    ][:12]
    return {
        "path": str(path.relative_to(_REPO_ROOT)),
        "exists": True,
        "excerpt": text[:max_chars],
        "headings": headings,
    }


def _knowledge_context() -> Dict[str, Any]:
    project_dir = _KB_ROOT / "Projects" / "Lab4D"
    files = [
        _KB_ROOT / "INDEX.md",
        _KB_ROOT / "iterative_level_design_framework.md",
        _KB_ROOT / "blueprint_organization_standards.md",
        project_dir / "lab4d_modification_log.md",
        project_dir / "lab4d_requirements_checklist.md",
        project_dir / "lab4d_project_audit.md",
    ]

    return {
        "knowledge_base_root": str(_KB_ROOT.relative_to(_REPO_ROOT)),
        "project": "Lab4D" if project_dir.exists() else "",
        "files": [_read_excerpt(path) for path in files],
    }


def register_chat_tools(mcp: FastMCP) -> None:
    @mcp.tool()
    def chat_poll_messages(since: str = "", limit: int = 50, session: str = "") -> str:
        """Poll for new human messages sent from the UE editor chat widget.

        Args:
            since: Optional ISO-8601 timestamp. If omitted, this tool uses the
                   previous poll cursor for this server process, or returns all
                   human messages on first use.
            limit: Maximum number of messages to return.
            session: Optional named chat session. Empty uses the legacy default history.

        Returns:
            Structured JSON containing messages and next_since for the next poll.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            chat_poll_messages()
        """
        started = time.monotonic()
        session_name = session.strip()
        cursor_key = session_name or "__default__"
        poll_since = since or _LAST_HUMAN_POLL_SINCE.get(cursor_key)
        try:
            messages = poll_messages(since=poll_since, sender="human", session=session_name or None)
            safe_limit = max(1, min(int(limit or 50), 500))
            messages = messages[-safe_limit:]
            next_since = utc_now_iso()
            _LAST_HUMAN_POLL_SINCE[cursor_key] = next_since
            return _make_result(
                success=True,
                stage="chat_poll_messages",
                message=f"Found {len(messages)} human message(s)",
                outputs={
                    "messages": messages,
                    "since": poll_since or "",
                    "next_since": next_since,
                    "session": session_name,
                },
                meta=_meta("chat_poll_messages", started),
            )
        except Exception as exc:
            return _make_result(
                success=False,
                stage="chat_poll_messages",
                message="Failed to poll human chat messages",
                errors=[str(exc)],
                meta=_meta("chat_poll_messages", started),
            )

    @mcp.tool()
    def chat_send_response(message: str, context: Optional[Dict[str, Any]] = None, session: str = "") -> str:
        """Send an agent response back to the UE editor chat widget.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            chat_send_response(message="I created the requested Blueprint.")
        """
        started = time.monotonic()
        session_name = session.strip()
        try:
            entry = append_message({
                "sender": "agent",
                "message": message,
                "timestamp": utc_now_iso(),
                "context": context or {},
            }, session=session_name or None)
            return _make_result(
                success=True,
                stage="chat_send_response",
                message="Agent response queued for UE editor",
                outputs={"message": entry, "session": session_name},
                meta=_meta("chat_send_response", started),
            )
        except Exception as exc:
            return _make_result(
                success=False,
                stage="chat_send_response",
                message="Failed to send agent response",
                errors=[str(exc)],
                meta=_meta("chat_send_response", started),
            )

    @mcp.tool()
    def chat_get_context(message_limit: int = 10, session: str = "") -> str:
        """Return recent chat context and compact knowledge-base state.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            chat_get_context()
        """
        started = time.monotonic()
        session_name = session.strip()
        try:
            safe_limit = max(1, min(int(message_limit or 10), 50))
            messages = get_recent_messages(limit=safe_limit, session=session_name or None)
            return _make_result(
                success=True,
                stage="chat_get_context",
                message=f"Loaded {len(messages)} recent message(s) and knowledge-base context",
                outputs={
                    "recent_messages": messages,
                    "knowledge_base": _knowledge_context(),
                    "session": session_name,
                },
                meta=_meta("chat_get_context", started),
            )
        except Exception as exc:
            return _make_result(
                success=False,
                stage="chat_get_context",
                message="Failed to gather chat context",
                errors=[str(exc)],
                meta=_meta("chat_get_context", started),
            )

    @mcp.tool()
    def chat_list_sessions(include_ide_companion_ledgers: bool = True, limit: int = 50) -> str:
        """List saved MCP Chat sessions and optional IDE companion ledgers.

        Use this to drive an editor-side session picker before resuming a
        companion workflow. This tool only reads local JSON files; it does not
        mutate Unreal, call providers, or spend credits.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d21-chat-cockpit-session-picker
        Example:
            chat_list_sessions()
        """
        started = time.monotonic()
        try:
            payload = build_session_list_payload(
                include_ide_companion_ledgers=include_ide_companion_ledgers,
                limit=limit,
            )
            return _make_result(
                success=True,
                stage="chat_sessions_listed",
                message=(
                    f"Loaded {len(payload['sessions'])} chat session(s) and "
                    f"{len(payload['ide_companion_ledgers'])} IDE companion ledger(s)"
                ),
                outputs=payload,
                meta=_meta("chat_list_sessions", started),
            )
        except Exception as exc:
            return _make_result(
                success=False,
                stage="chat_sessions_failed",
                message="Failed to list chat sessions",
                errors=[str(exc)],
                meta=_meta("chat_list_sessions", started),
            )

    @mcp.tool()
    def chat_get_session_resume_context(session: str = "", message_limit: int = 20) -> str:
        """Load recent chat messages plus matching IDE companion ledger summary.

        Use this before showing a resume card in MCP Chat. The matching ledger
        summary can be passed to `skill_resume_ide_companion_session` by path
        when the developer chooses to continue that session.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d21-chat-cockpit-session-picker
        Example:
            chat_get_session_resume_context(session="ide-companion")
        """
        started = time.monotonic()
        try:
            payload = build_session_resume_context(session=session, message_limit=message_limit)
            return _make_result(
                success=True,
                stage="chat_session_resume_context",
                message=f"Loaded resume context for chat session '{payload['session']}'",
                outputs={key: value for key, value in payload.items() if key != "warnings"},
                warnings=payload.get("warnings", []),
                meta=_meta("chat_get_session_resume_context", started),
            )
        except Exception as exc:
            return _make_result(
                success=False,
                stage="chat_session_resume_context_failed",
                message="Failed to load chat session resume context",
                errors=[str(exc)],
                meta=_meta("chat_get_session_resume_context", started),
            )

    @mcp.tool()
    def chat_get_cockpit_overview(session: str = "", message_limit: int = 20, limit: int = 50) -> str:
        """Return a display-ready MCP Chat cockpit overview packet.

        The packet combines saved chat sessions, recent messages, matching IDE
        companion ledger evidence, queued editor actions, blockers, cards, and
        suggested next actions. It only reads local JSON files.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d22-chat-cockpit-overview
        Example:
            chat_get_cockpit_overview(session="ide-companion")
        """
        started = time.monotonic()
        try:
            overview = build_cockpit_overview(session=session, message_limit=message_limit, limit=limit)
            return _make_result(
                success=True,
                stage="chat_cockpit_overview",
                message=f"Loaded cockpit overview for chat session '{overview['session']}'",
                outputs={key: value for key, value in overview.items() if key != "warnings"},
                warnings=overview.get("warnings", []),
                meta=_meta("chat_get_cockpit_overview", started),
            )
        except Exception as exc:
            return _make_result(
                success=False,
                stage="chat_cockpit_overview_failed",
                message="Failed to load chat cockpit overview",
                errors=[str(exc)],
                meta=_meta("chat_get_cockpit_overview", started),
            )

    @mcp.tool()
    def chat_get_cockpit_ledger_detail(
        session: str = "",
        ledger_path: str = "",
        event_index: int = 0,
        limit: int = 20,
        artifact_limit: int = 12,
    ) -> str:
        """Return bounded IDE companion ledger detail for the MCP Chat cockpit.

        The packet includes recent ledger events, per-event artifacts, artifact
        kinds, phase index data, latest status, and latest work order. It only
        reads local IDE companion ledger JSON files and never mutates Unreal,
        calls providers, or spends credits.

        Args:
            session: Chat/companion session name to match when ledger_path is omitted.
            ledger_path: Optional ledger path from a cockpit overview or session list.
            event_index: Optional 1-based event index for single-event drilldown.
            limit: Maximum recent events to return when event_index is omitted.
            artifact_limit: Maximum artifacts to return per event.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#d27-chat-cockpit-ledger-detail
        Example:
            chat_get_cockpit_ledger_detail(session="ide-companion")
        """
        started = time.monotonic()
        try:
            detail = build_ledger_detail(
                session=session,
                ledger_path=ledger_path,
                event_index=event_index,
                limit=limit,
                artifact_limit=artifact_limit,
            )
            found = bool(detail.get("ledger_found", False))
            return _make_result(
                success=found,
                stage="chat_cockpit_ledger_detail" if found else "chat_cockpit_ledger_missing",
                message=(
                    f"Loaded ledger detail for chat session '{detail['session']}'"
                    if found else
                    f"No IDE companion ledger found for chat session '{detail['session']}'"
                ),
                outputs={key: value for key, value in detail.items() if key != "warnings"},
                warnings=detail.get("warnings", []),
                meta=_meta("chat_get_cockpit_ledger_detail", started),
            )
        except Exception as exc:
            return _make_result(
                success=False,
                stage="chat_cockpit_ledger_detail_failed",
                message="Failed to load cockpit ledger detail",
                errors=[str(exc)],
                meta=_meta("chat_get_cockpit_ledger_detail", started),
            )
