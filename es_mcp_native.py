"""Helper that sends native C++ bridge commands to the UE plugin.

The UE plugin exposes ~405 native commands (not just exec_python).
This module is a thin TCP client that wires them up cleanly.
"""
from __future__ import annotations
import json, socket
from typing import Any

HOST, PORT = "127.0.0.1", 55557


def send(command: str, params: dict | None = None, timeout: float = 120.0) -> dict:
    """Send a native bridge command."""
    req = {"type": command, "params": params or {}}
    s = socket.create_connection((HOST, PORT), 10)
    try:
        s.settimeout(timeout)
        s.sendall((json.dumps(req) + "\n").encode("utf-8"))
        buf = b""
        while True:
            ch = s.recv(1 << 20)
            if not ch:
                break
            buf += ch
            try:
                return json.loads(buf.decode("utf-8").strip())
            except json.JSONDecodeError:
                continue
        return json.loads(buf.decode("utf-8", errors="replace").strip())
    finally:
        s.close()


def ok(r: dict) -> bool:
    return bool(r) and (r.get("status") == "success" or r.get("success") is True)


if __name__ == "__main__":
    print("ping:", send("ping"))
    print()
    r = send("get_blueprint_nodes", {
        "blueprint_name": "BTService_UpdatePerception",
        "graph_name": "EventGraph",
    })
    print("get_blueprint_nodes BTService_UpdatePerception:")
    print(json.dumps(r, indent=2)[:4000])
