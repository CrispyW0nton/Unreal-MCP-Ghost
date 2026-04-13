"""
mcp_client.py — async wrapper around sandbox_ue5cli.send_command
Provides call_tool(tool_name, params) that the AI agent uses to talk to UE5.

Usage:
    import asyncio, json, sys
    sys.path.insert(0, '/home/user/webapp')
    from mcp_client import call_tool

    async def main():
        result = await call_tool("get_actors_in_level", {})
        print(json.dumps(result, indent=2))

    asyncio.run(main())
"""
import asyncio
import json
import socket
from typing import Any, Dict, Optional

HOST = "lie-instability.with.playit.plus"
PORT = 5462
TIMEOUT = 60   # seconds — compile/save can be slow


def _recv(sock: socket.socket) -> bytes:
    """Read until we have a complete JSON object."""
    chunks = []
    sock.settimeout(TIMEOUT)
    while True:
        try:
            chunk = sock.recv(8192)
        except socket.timeout:
            break
        if not chunk:
            break
        chunks.append(chunk)
        data = b"".join(chunks)
        try:
            json.loads(data.decode("utf-8"))
            return data   # complete JSON → done
        except json.JSONDecodeError:
            continue
    return b"".join(chunks)


def _send_sync(command: str, params: Dict[str, Any] = None) -> Dict:
    """Blocking send — runs in a thread so the event loop stays free."""
    msg = json.dumps({"type": command, "params": params or {}}) + "\n"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(TIMEOUT)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        s.connect((HOST, PORT))
        s.sendall(msg.encode("utf-8"))
        raw = _recv(s)
        return json.loads(raw.decode("utf-8").strip())
    except ConnectionRefusedError:
        return {"status": "error", "error": f"Connection refused — is UE5 open and Playit running? ({HOST}:{PORT})"}
    except socket.timeout:
        return {"status": "error", "error": f"Timeout after {TIMEOUT}s — UE5 may be busy"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        try:
            s.close()
        except Exception:
            pass


async def call_tool(tool_name: str, params: Dict[str, Any] = None) -> Dict:
    """
    Async wrapper: runs the blocking socket call in a thread executor
    so it doesn't block the event loop.
    Returns the unwrapped result dict.
    """
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, _send_sync, tool_name, params or {})

    # Unwrap envelope: {"status":"success","result":{...}} → {...}
    if isinstance(raw, dict) and raw.get("status") == "success" and "result" in raw:
        return raw["result"]
    return raw
