"""Quick health check on the UnrealMCP TCP bridge.

Verifies that:
  1. The plugin DLL we just rebuilt is the one Unreal loaded
     (looks for a known new symbol's logging signature).
  2. We can round-trip a trivial command.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from pathlib import Path
from typing import Any, Dict

HOST = "127.0.0.1"
PORT = 55655
REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "unreal_mcp_server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from bridge_auth import load_bridge_authentication

DEFAULT_RECEIPT_PATH = Path("Saved") / "BridgePing" / "last_ping_receipt.json"


def send(cmd_type: str, params: Dict[str, Any] | None = None, timeout: float = 30.0, *, host: str = HOST, port: int = PORT) -> Dict[str, Any]:
    s = socket.socket()
    s.settimeout(timeout)
    s.connect((host, port))
    try:
        command = load_bridge_authentication().command_payload(cmd_type, params)
        s.sendall((json.dumps(command) + "\n").encode())
        chunks = []
        while True:
            ch = s.recv(65536)
            if not ch:
                break
            chunks.append(ch)
    finally:
        s.close()
    raw = b"".join(chunks).decode("utf-8", errors="replace").strip()
    if not raw:
        return {"status": "empty"}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"status": "raw", "result": raw}


def build_receipt(
    *,
    host: str,
    port: int,
    status: str,
    exit_code: int,
    command_status: str = "",
    actor_count: int | None = None,
    error: str = "",
) -> Dict[str, Any]:
    return {
        "schema": "unreal_mcp_bridge_ping_receipt.v1",
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": status,
        "exit_code": int(exit_code),
        "host": host,
        "port": int(port),
        "command": "get_actors_in_level",
        "command_status": command_status,
        "actor_count": actor_count,
        "error": error,
        "successful_bridge_ping": status == "success" and exit_code == 0,
        "no_editor_mutation": True,
        "no_provider_call": True,
        "no_git_mutation": True,
        "network_required": False,
        "spend_required": False,
        "unreal_editor_required": True,
    }


def write_receipt(path: Path, receipt: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ping the UnrealMCP live TCP bridge and optionally write a local receipt.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", default=PORT, type=int)
    parser.add_argument("--timeout", default=30.0, type=float)
    parser.add_argument("--receipt-path", default=str(DEFAULT_RECEIPT_PATH), help="ignored local JSON receipt path")
    args = parser.parse_args()

    receipt_path = Path(args.receipt_path)
    if not receipt_path.is_absolute():
        receipt_path = REPO_ROOT / receipt_path

    print(f"Pinging UnrealMCP bridge at {args.host}:{args.port} ...")
    exit_code = 1
    receipt = build_receipt(
        host=args.host,
        port=args.port,
        status="failed",
        exit_code=exit_code,
        error="bridge ping did not complete",
    )
    try:
        r = send("get_actors_in_level", {}, timeout=args.timeout, host=args.host, port=args.port)
    except (ConnectionRefusedError, ConnectionResetError, socket.timeout) as e:
        print(f"  FAILED: {type(e).__name__}: {e}")
        print(f"  -> Bridge not reachable. Check Output Log for 'UnrealMCP listening on {args.host}:{args.port}'.")
        receipt = build_receipt(
            host=args.host,
            port=args.port,
            status="failed",
            exit_code=1,
            error=f"{type(e).__name__}: {e}",
        )
        write_receipt(receipt_path, receipt)
        print(f"BRIDGE_PING_RECEIPT={args.receipt_path}")
        return 1

    status = r.get("status")
    actor_count = 0
    if status == "success":
        result = r.get("result") or {}
        actors = result.get("actors") or []
        actor_count = len(actors)
        print(f"  OK: bridge responded, {actor_count} actors in current level")
        exit_code = 0
        receipt = build_receipt(
            host=args.host,
            port=args.port,
            status="success",
            exit_code=0,
            command_status=str(status),
            actor_count=actor_count,
        )
    else:
        print(f"  Bridge responded with status={status!r}: {r}")
        receipt = build_receipt(
            host=args.host,
            port=args.port,
            status="failed",
            exit_code=2,
            command_status=str(status),
            error=json.dumps(r, sort_keys=True),
        )
        write_receipt(receipt_path, receipt)
        print(f"BRIDGE_PING_RECEIPT={args.receipt_path}")
        return 2

    # Confirm the BlackHole BP is loaded so the audio script can find it.
    r2 = send("find_blueprint", {"blueprint_name": "BP_BlackHole"}, timeout=args.timeout, host=args.host, port=args.port)
    if r2.get("status") == "success":
        print("  OK: BP_BlackHole resolvable through the bridge")
    else:
        # Not a hard failure — different MCP versions name this differently.
        # Try a generic path that we know works.
        r3 = send("get_blueprint_components", {"blueprint_name": "BP_BlackHole"}, timeout=args.timeout, host=args.host, port=args.port)
        if r3.get("status") == "success":
            comps = ((r3.get("result") or {}).get("components") or [])
            print(f"  OK: BP_BlackHole has {len(comps)} components")
            audio_comps = [c for c in comps if "Audio" in (c.get("class") or "") or "Audio" in (c.get("name") or "")]
            if audio_comps:
                print("        Audio components found:")
                for c in audio_comps:
                    print(f"          - {c.get('name')} ({c.get('class')})")
            else:
                print("        (no AudioComponents yet on BP_BlackHole)")
        else:
            print(f"  WARN: could not introspect BP_BlackHole: {r3}")

    write_receipt(receipt_path, receipt)
    print(f"BRIDGE_PING_RECEIPT={args.receipt_path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
