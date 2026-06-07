"""JSON-backed chat history storage for UE editor <-> agent messages."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent

DEFAULT_CHAT_HISTORY_PATH = (
    Path(os.environ["UNREAL_MCP_CHAT_HISTORY_PATH"])
    if os.environ.get("UNREAL_MCP_CHAT_HISTORY_PATH")
    else _REPO_ROOT / "Saved" / "MCP" / "chat_history.json"
)

VALID_SENDERS = {"human", "agent"}
_LOCK = threading.RLock()


def utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp using the Z suffix."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 timestamps, accepting the common trailing Z form."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _history_path(path: Optional[Path | str] = None) -> Path:
    return Path(path) if path else DEFAULT_CHAT_HISTORY_PATH


def _normalise_message(raw: Dict[str, Any]) -> Dict[str, Any]:
    sender = str(raw.get("sender", "")).strip()
    if sender not in VALID_SENDERS:
        raise ValueError("sender must be 'human' or 'agent'")

    message = str(raw.get("message", "")).strip()
    if not message:
        raise ValueError("message must not be empty")

    timestamp = str(raw.get("timestamp") or utc_now_iso())
    # Validate once, then keep the compact caller-supplied string if valid.
    parse_iso8601(timestamp)

    entry: Dict[str, Any] = {
        "message_id": str(raw.get("message_id") or uuid.uuid4()),
        "sender": sender,
        "message": message,
        "timestamp": timestamp,
    }

    context = raw.get("context")
    if isinstance(context, dict) and context:
        entry["context"] = context

    return entry


def read_history(path: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    history_file = _history_path(path)
    with _LOCK:
        if not history_file.exists():
            return []
        try:
            data = json.loads(history_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            corrupt_path = history_file.with_suffix(history_file.suffix + ".corrupt")
            history_file.replace(corrupt_path)
            return []

        if isinstance(data, dict):
            messages = data.get("messages", [])
        else:
            messages = data

        return [item for item in messages if isinstance(item, dict)]


def write_history(messages: List[Dict[str, Any]], path: Optional[Path | str] = None) -> None:
    history_file = _history_path(path)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "messages": messages,
        "updated_at": utc_now_iso(),
    }

    with _LOCK:
        fd, tmp_name = tempfile.mkstemp(
            prefix=history_file.name,
            suffix=".tmp",
            dir=str(history_file.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                json.dump(payload, tmp, ensure_ascii=False, indent=2)
                tmp.write("\n")
            os.replace(tmp_name, history_file)
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)


def append_message(message: Dict[str, Any], path: Optional[Path | str] = None) -> Dict[str, Any]:
    entry = _normalise_message(message)
    with _LOCK:
        messages = read_history(path)
        messages.append(entry)
        write_history(messages, path)
    return entry


def poll_messages(
    *,
    since: Optional[str] = None,
    sender: Optional[str] = None,
    path: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    if sender and sender not in VALID_SENDERS:
        raise ValueError("sender must be 'human' or 'agent'")

    since_dt = parse_iso8601(since)
    matches: List[Dict[str, Any]] = []

    for item in read_history(path):
        if sender and item.get("sender") != sender:
            continue
        if since_dt is not None:
            try:
                item_dt = parse_iso8601(str(item.get("timestamp", "")))
            except ValueError:
                continue
            if item_dt is None or item_dt <= since_dt:
                continue
        matches.append(item)

    return matches


def get_recent_messages(limit: int = 50, path: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(int(limit or 50), 500))
    return read_history(path)[-safe_limit:]


def clear_history(path: Optional[Path | str] = None) -> None:
    write_history([], path)

