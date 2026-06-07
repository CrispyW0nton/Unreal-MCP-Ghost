"""MCP tools for the UE editor chat bridge."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from chat.storage import append_message, get_recent_messages, poll_messages, utc_now_iso

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
_KB_ROOT = _REPO_ROOT / "knowledge_base"
_LAST_HUMAN_POLL_SINCE: Optional[str] = None


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
    def chat_poll_messages(since: str = "", limit: int = 50) -> str:
        """Poll for new human messages sent from the UE editor chat widget.

        Args:
            since: Optional ISO-8601 timestamp. If omitted, this tool uses the
                   previous poll cursor for this server process, or returns all
                   human messages on first use.
            limit: Maximum number of messages to return.

        Returns:
            Structured JSON containing messages and next_since for the next poll.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            chat_poll_messages()
        """
        global _LAST_HUMAN_POLL_SINCE

        started = time.monotonic()
        poll_since = since or _LAST_HUMAN_POLL_SINCE
        try:
            messages = poll_messages(since=poll_since, sender="human")
            safe_limit = max(1, min(int(limit or 50), 500))
            messages = messages[-safe_limit:]
            next_since = utc_now_iso()
            _LAST_HUMAN_POLL_SINCE = next_since
            return _make_result(
                success=True,
                stage="chat_poll_messages",
                message=f"Found {len(messages)} human message(s)",
                outputs={
                    "messages": messages,
                    "since": poll_since or "",
                    "next_since": next_since,
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
    def chat_send_response(message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Send an agent response back to the UE editor chat widget.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            chat_send_response(message="I created the requested Blueprint.")
        """
        started = time.monotonic()
        try:
            entry = append_message({
                "sender": "agent",
                "message": message,
                "timestamp": utc_now_iso(),
                "context": context or {},
            })
            return _make_result(
                success=True,
                stage="chat_send_response",
                message="Agent response queued for UE editor",
                outputs={"message": entry},
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
    def chat_get_context(message_limit: int = 10) -> str:
        """Return recent chat context and compact knowledge-base state.

        KB: see knowledge_base/32_AGENT_PLAYABLE_SLICE_RECIPE.md#overview
        Example:
            chat_get_context()
        """
        started = time.monotonic()
        try:
            safe_limit = max(1, min(int(message_limit or 10), 50))
            messages = get_recent_messages(limit=safe_limit)
            return _make_result(
                success=True,
                stage="chat_get_context",
                message=f"Loaded {len(messages)} recent message(s) and knowledge-base context",
                outputs={
                    "recent_messages": messages,
                    "knowledge_base": _knowledge_context(),
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

