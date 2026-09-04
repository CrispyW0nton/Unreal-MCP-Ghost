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
DEFAULT_CHAT_SESSION_DIR = (
    Path(os.environ["UNREAL_MCP_CHAT_SESSION_DIR"])
    if os.environ.get("UNREAL_MCP_CHAT_SESSION_DIR")
    else _REPO_ROOT / "Saved" / "MCPChat"
)
DEFAULT_SESSION_NAME = "default"
SESSION_INDEX_FILENAME = "sessions.json"

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


def _session_dir(session_dir: Optional[Path | str] = None) -> Path:
    return Path(session_dir) if session_dir else DEFAULT_CHAT_SESSION_DIR


def _safe_session_name(name: Optional[str]) -> str:
    text = str(name or DEFAULT_SESSION_NAME).strip() or DEFAULT_SESSION_NAME
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_", " ") else "_" for ch in text)
    return safe.strip() or DEFAULT_SESSION_NAME


def _session_path(session: Optional[str], session_dir: Optional[Path | str] = None) -> Path:
    return _session_dir(session_dir) / f"{_safe_session_name(session)}.json"


def _session_index_path(session_dir: Optional[Path | str] = None) -> Path:
    return _session_dir(session_dir) / SESSION_INDEX_FILENAME


def _read_session_index(session_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    path = _session_index_path(session_dir)
    if not path.exists():
        return {"last_session": DEFAULT_SESSION_NAME, "pinned": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"last_session": DEFAULT_SESSION_NAME, "pinned": []}
    if not isinstance(payload, dict):
        return {"last_session": DEFAULT_SESSION_NAME, "pinned": []}
    payload.setdefault("last_session", DEFAULT_SESSION_NAME)
    payload.setdefault("pinned", [])
    return payload


def _write_session_index(payload: Dict[str, Any], session_dir: Optional[Path | str] = None) -> None:
    path = _session_index_path(session_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _touch_session_index(
    session: str,
    *,
    pinned: Optional[bool] = None,
    session_dir: Optional[Path | str] = None,
) -> None:
    safe = _safe_session_name(session)
    index = _read_session_index(session_dir)
    index["last_session"] = safe
    pinned_sessions = {str(item) for item in index.get("pinned", [])}
    if pinned is True:
        pinned_sessions.add(safe)
    elif pinned is False:
        pinned_sessions.discard(safe)
    index["pinned"] = sorted(pinned_sessions)
    _write_session_index(index, session_dir)


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


def read_history(
    path: Optional[Path | str] = None,
    *,
    session: Optional[str] = None,
    session_dir: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    history_file = Path(path) if path else (_session_path(session, session_dir) if session else DEFAULT_CHAT_HISTORY_PATH)
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


def write_history(
    messages: List[Dict[str, Any]],
    path: Optional[Path | str] = None,
    *,
    session: Optional[str] = None,
    session_dir: Optional[Path | str] = None,
) -> None:
    history_file = Path(path) if path else (_session_path(session, session_dir) if session else DEFAULT_CHAT_HISTORY_PATH)
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


def append_message(
    message: Dict[str, Any],
    path: Optional[Path | str] = None,
    *,
    session: Optional[str] = None,
    session_dir: Optional[Path | str] = None,
) -> Dict[str, Any]:
    entry = _normalise_message(message)
    with _LOCK:
        messages = read_history(path, session=session, session_dir=session_dir)
        messages.append(entry)
        write_history(messages, path, session=session, session_dir=session_dir)
        if session:
            _touch_session_index(session, session_dir=session_dir)
    return entry


def poll_messages(
    *,
    since: Optional[str] = None,
    sender: Optional[str] = None,
    path: Optional[Path | str] = None,
    session: Optional[str] = None,
    session_dir: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    if sender and sender not in VALID_SENDERS:
        raise ValueError("sender must be 'human' or 'agent'")

    since_dt = parse_iso8601(since)
    matches: List[Dict[str, Any]] = []

    for item in read_history(path, session=session, session_dir=session_dir):
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


def get_recent_messages(
    limit: int = 50,
    path: Optional[Path | str] = None,
    *,
    session: Optional[str] = None,
    session_dir: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(int(limit or 50), 500))
    return read_history(path, session=session, session_dir=session_dir)[-safe_limit:]


def clear_history(
    path: Optional[Path | str] = None,
    *,
    session: Optional[str] = None,
    session_dir: Optional[Path | str] = None,
) -> None:
    write_history([], path, session=session, session_dir=session_dir)
    if session:
        _touch_session_index(session, session_dir=session_dir)


def list_sessions(session_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    base = _session_dir(session_dir)
    index = _read_session_index(session_dir)
    pinned = {str(item) for item in index.get("pinned", [])}
    sessions: List[Dict[str, Any]] = []

    if base.exists():
        for file_path in base.glob("*.json"):
            if file_path.name == SESSION_INDEX_FILENAME:
                continue
            name = file_path.stem
            messages = read_history(file_path)
            updated_at = ""
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    updated_at = str(payload.get("updated_at", ""))
            except json.JSONDecodeError:
                pass
            sessions.append({
                "name": name,
                "message_count": len(messages),
                "updated_at": updated_at,
                "pinned": name in pinned,
            })

    if not sessions:
        sessions.append({
            "name": DEFAULT_SESSION_NAME,
            "message_count": 0,
            "updated_at": "",
            "pinned": DEFAULT_SESSION_NAME in pinned,
        })

    sessions.sort(key=lambda item: (not bool(item["pinned"]), str(item["name"]).lower()))
    last_session = _safe_session_name(str(index.get("last_session") or sessions[0]["name"]))
    return {"sessions": sessions, "last_session": last_session}


def create_session(name: str, session_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    safe = _safe_session_name(name)
    with _LOCK:
        path = _session_path(safe, session_dir)
        if not path.exists():
            write_history([], path)
        _touch_session_index(safe, session_dir=session_dir)
    return {"name": safe, "path": str(path)}


def rename_session(old_name: str, new_name: str, session_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    old_safe = _safe_session_name(old_name)
    new_safe = _safe_session_name(new_name)
    old_path = _session_path(old_safe, session_dir)
    new_path = _session_path(new_safe, session_dir)
    with _LOCK:
        old_path.parent.mkdir(parents=True, exist_ok=True)
        if not old_path.exists():
            write_history([], old_path)
        if new_path.exists() and old_path != new_path:
            raise ValueError(f"session already exists: {new_safe}")
        old_path.replace(new_path)
        index = _read_session_index(session_dir)
        pinned = {str(item) for item in index.get("pinned", [])}
        if old_safe in pinned:
            pinned.discard(old_safe)
            pinned.add(new_safe)
        if index.get("last_session") == old_safe:
            index["last_session"] = new_safe
        index["pinned"] = sorted(pinned)
        _write_session_index(index, session_dir)
    return {"name": new_safe, "old_name": old_safe}


def delete_session(name: str, session_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    safe = _safe_session_name(name)
    path = _session_path(safe, session_dir)
    with _LOCK:
        if path.exists():
            path.unlink()
        index = _read_session_index(session_dir)
        pinned = {str(item) for item in index.get("pinned", [])}
        pinned.discard(safe)
        index["pinned"] = sorted(pinned)
        if index.get("last_session") == safe:
            index["last_session"] = DEFAULT_SESSION_NAME
        _write_session_index(index, session_dir)
    return {"name": safe}


def pin_session(name: str, pinned: bool = True, session_dir: Optional[Path | str] = None) -> Dict[str, Any]:
    safe = _safe_session_name(name)
    with _LOCK:
        create_session(safe, session_dir=session_dir)
        _touch_session_index(safe, pinned=pinned, session_dir=session_dir)
    return {"name": safe, "pinned": pinned}


def export_session_markdown(name: str, session_dir: Optional[Path | str] = None) -> str:
    safe = _safe_session_name(name)
    messages = read_history(session=safe, session_dir=session_dir)
    lines = [f"# MCP Chat Session: {safe}", ""]
    for message in messages:
        sender = str(message.get("sender", "message")).title()
        timestamp = str(message.get("timestamp", ""))
        body = str(message.get("message", ""))
        lines.extend([f"## {sender} - {timestamp}", "", body, ""])
    return "\n".join(lines).rstrip() + "\n"

