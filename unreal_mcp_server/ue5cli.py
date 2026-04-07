#!/usr/bin/env python3
"""
ue5cli.py — One-shot CLI for Unreal Engine 5 via the UnrealMCP TCP plugin.

Usage:
    python ue5cli.py <command> [key=value ...]
    python ue5cli.py <command> '{"key":"value"}'
    python ue5cli.py --list

Examples:
    python ue5cli.py get_actors_in_level
    python ue5cli.py create_blueprint name=BP_Hero parent_class=Character
    python ue5cli.py spawn_actor name=Cube type=StaticMeshActor location=[0,0,100]
    python ue5cli.py compile_blueprint blueprint_name=BP_Hero
    python ue5cli.py delete_actor name=Cube
    python ue5cli.py find_actors_by_name pattern=*
"""

import sys
import json
import socket
import argparse
from typing import Any, Dict, Optional

HOST = "127.0.0.1"
PORT = 55557
TIMEOUT = 15

# ── common commands reference ─────────────────────────────────────────────────
COMMANDS = [
    ("get_actors_in_level",          "List all actors in the current level",                       ""),
    ("find_actors_by_name",          "Find actors by name pattern",                                "pattern=*"),
    ("spawn_actor",                  "Spawn an actor into the level",                              "name=MyActor type=StaticMeshActor location=[0,0,100]"),
    ("delete_actor",                 "Delete an actor from the level",                             "name=MyActor"),
    ("set_actor_transform",          "Move/rotate/scale an actor",                                 "name=MyActor location=[0,0,200] rotation=[0,45,0]"),
    ("get_actor_properties",         "Get all properties of an actor",                             "name=MyActor"),
    ("create_blueprint",             "Create a new Blueprint asset",                               "name=BP_Hero parent_class=Character"),
    ("compile_blueprint",            "Compile a Blueprint",                                        "blueprint_name=BP_Hero"),
    ("add_component_to_blueprint",   "Add a component to a Blueprint",                             "blueprint_name=BP_Hero component_type=CameraComponent component_name=Cam"),
    ("add_blueprint_variable",       "Add a variable to a Blueprint",                              "blueprint_name=BP_Hero variable_name=Health variable_type=Float is_exposed=true"),
    ("add_blueprint_event_node",     "Add an event node to the event graph",                       "blueprint_name=BP_Hero event_name=ReceiveBeginPlay node_position=[0,0]"),
    ("add_blueprint_function_node",  "Add a function call node",                                   "blueprint_name=BP_Hero target=UKismetSystemLibrary function_name=PrintString"),
    ("connect_blueprint_nodes",      "Wire two graph nodes together",                              "blueprint_name=BP_Hero source_node_id=<guid> source_pin=then target_node_id=<guid> target_pin=execute"),
    ("find_blueprint_nodes",         "Find nodes in the event graph",                              "blueprint_name=BP_Hero node_type=event"),
    ("spawn_blueprint_actor",        "Place a Blueprint instance in the level",                    "name=Hero1 blueprint_name=BP_Hero location=[0,0,0]"),
    ("take_screenshot",              "Take a viewport screenshot",                                 "filename=screenshot.png"),
    ("save_current_level",           "Save the current level",                                     ""),
]


# ── socket send/receive ───────────────────────────────────────────────────────
def _recv(sock: socket.socket) -> bytes:
    chunks = []
    sock.settimeout(TIMEOUT)
    while True:
        chunk = sock.recv(8192)
        if not chunk:
            break
        chunks.append(chunk)
        data = b"".join(chunks)
        try:
            json.loads(data.decode("utf-8"))
            return data
        except json.JSONDecodeError:
            continue
    return b"".join(chunks)


def send_command(command: str, params: Dict[str, Any] = None) -> Optional[Dict]:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        return {"status": "error",
                "error": f"Cannot connect to UE5 on {HOST}:{PORT}. "
                         "Is the UnrealMCP plugin loaded and UE5 running?"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

    try:
        payload = json.dumps({"type": command, "params": params or {}})
        sock.sendall(payload.encode("utf-8"))
        raw = _recv(sock)
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        return {"status": "error", "error": f"Communication error: {e}"}
    finally:
        try:
            sock.close()
        except Exception:
            pass


# ── param parsing ─────────────────────────────────────────────────────────────
def _coerce(v: str) -> Any:
    s = v.strip()
    if s.lower() == "true":  return True
    if s.lower() == "false": return False
    if s.lower() == "null":  return None
    try: return int(s)
    except ValueError: pass
    try: return float(s)
    except ValueError: pass
    try:
        parsed = json.loads(s)
        if isinstance(parsed, (list, dict)):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return s


def parse_params(tokens: list) -> Dict[str, Any]:
    if not tokens:
        return {}
    joined = " ".join(tokens).strip()
    if joined.startswith("{"):
        try:
            return json.loads(joined)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON params: {e}") from e
    params: Dict[str, Any] = {}
    for token in tokens:
        if "=" not in token:
            raise ValueError(
                f"Bad param {token!r} — use key=value pairs or a JSON object.\n"
                f"  Example: create_blueprint name=BP_Test parent_class=Actor"
            )
        k, _, v = token.partition("=")
        params[k.strip()] = _coerce(v)
    return params


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    global HOST, PORT

    parser = argparse.ArgumentParser(
        prog="ue5cli",
        description="One-shot CLI for Unreal Engine 5 via UnrealMCP (port 55557)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join([
            "examples:",
            "  python ue5cli.py get_actors_in_level",
            "  python ue5cli.py create_blueprint name=BP_Hero parent_class=Character",
            "  python ue5cli.py spawn_actor name=Cube type=StaticMeshActor location=[0,0,100]",
            "  python ue5cli.py compile_blueprint blueprint_name=BP_Hero",
            "  python ue5cli.py delete_actor name=Cube",
            '  python ue5cli.py create_blueprint \'{"name":"BP_Test","parent_class":"Actor"}\'',
        ])
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="UE5 command to send (omit to use --list)"
    )
    parser.add_argument(
        "params",
        nargs="*",
        help="Parameters as key=value pairs or a single JSON object"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Print all available commands and exit"
    )
    parser.add_argument(
        "--host",
        default=HOST,
        help=f"UE5 hostname (default: {HOST})"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=PORT,
        help=f"UnrealMCP port (default: {PORT})"
    )
    parser.add_argument(
        "--raw", "-r",
        action="store_true",
        help="Print raw JSON response (default: pretty-printed)"
    )

    args = parser.parse_args()

    # Override globals if user passed --host/--port
    HOST = args.host
    PORT = args.port

    if args.list:
        print(f"\nAvailable commands  (target: {HOST}:{PORT})\n")
        for cmd, desc, example in COMMANDS:
            print(f"  {cmd}")
            print(f"      {desc}")
            if example:
                print(f"      e.g. python ue5cli.py {cmd} {example}")
        print()
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        params = parse_params(args.params)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    response = send_command(args.command, params)

    if args.raw:
        print(json.dumps(response))
    else:
        print(json.dumps(response, indent=2))

    # Exit 1 on error so scripts can check $LASTEXITCODE
    if response and (response.get("status") == "error" or response.get("success") is False):
        sys.exit(1)


if __name__ == "__main__":
    main()
