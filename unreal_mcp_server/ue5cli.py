#!/usr/bin/env python3
"""
ue5cli.py — Interactive CLI for Unreal Engine 5 via the UnrealMCP TCP plugin.

Usage:
    python ue5cli.py                  # interactive REPL
    python ue5cli.py <command> [json] # single shot, e.g.:
        python ue5cli.py get_actors_in_level
        python ue5cli.py create_blueprint '{"name":"BP_Test","parent_class":"Actor"}'
        python ue5cli.py spawn_actor '{"name":"Cube1","type":"StaticMeshActor","location":[0,0,100]}'

The plugin must be running in UE5 (port 55557 on localhost).
"""

import sys
import json
import socket
import textwrap
import readline  # noqa: F401 — gives up/down arrow history on most platforms
from typing import Optional, Dict, Any

HOST = "127.0.0.1"
PORT = 55557
TIMEOUT = 15

# ── colour helpers ────────────────────────────────────────────────────────────
try:
    import os
    _COLOUR = os.name != "nt" or "WT_SESSION" in os.environ
except Exception:
    _COLOUR = False

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOUR else text

OK   = lambda t: _c("32", t)   # green
ERR  = lambda t: _c("31", t)   # red
WARN = lambda t: _c("33", t)   # yellow
DIM  = lambda t: _c("2",  t)   # grey
BOLD = lambda t: _c("1",  t)   # bold
HEAD = lambda t: _c("36", t)   # cyan


# ── low-level socket send/receive ─────────────────────────────────────────────
def _receive(sock: socket.socket) -> bytes:
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
            return data          # valid JSON → done
        except json.JSONDecodeError:
            continue             # keep reading
    return b"".join(chunks)


def send_command(command: str, params: Dict[str, Any] = None) -> Optional[Dict]:
    """Open a fresh TCP connection, send one command, return parsed JSON."""
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
        raw = _receive(sock)
        return json.loads(raw.decode("utf-8"))
    except Exception as e:
        return {"status": "error", "error": f"Communication error: {e}"}
    finally:
        try:
            sock.close()
        except Exception:
            pass


# ── pretty-print a response ───────────────────────────────────────────────────
def pretty(response: Any, indent: int = 0) -> str:
    return json.dumps(response, indent=2, ensure_ascii=False)


def print_response(response: Optional[Dict]):
    if response is None:
        print(ERR("  No response received."))
        return
    status = response.get("status", "")
    if status == "error" or response.get("success") is False:
        msg = response.get("error") or response.get("message", "Unknown error")
        print(ERR(f"  ✗ {msg}"))
        extra = {k: v for k, v in response.items() if k not in ("status", "error", "success", "message")}
        if extra:
            print(DIM(textwrap.indent(pretty(extra), "    ")))
    else:
        result = response.get("result", response)
        print(OK("  ✓") + " " + DIM(pretty(result)))


# ── built-in command shortcuts ────────────────────────────────────────────────
SHORTCUTS: Dict[str, tuple] = {
    # alias : (ue_command, description, example_params)
    "actors":   ("get_actors_in_level",  "List all actors in level",             {}),
    "ping":     ("get_actors_in_level",  "Quick connectivity check",             {}),
    "save":     ("save_current_level",   "Save the current level",               {}),
    "compile":  ("compile_blueprint",    "Compile a blueprint (needs name=...)", {}),
    "screenshot":("take_screenshot",     "Take a viewport screenshot",           {}),
}

HELP_TEXT = f"""
{BOLD("ue5cli")} — direct CLI to Unreal Engine 5 via UnrealMCP plugin (port {PORT})

{HEAD("Usage:")}
  <command> [key=value ...]     send a raw UE5 command with optional params
  <command> {{...json...}}       send with a JSON param object
  <alias>   [key=value ...]     use a built-in shortcut (see below)

{HEAD("Built-in shortcuts:")}
""" + "\n".join(
    f"  {BOLD(alias):<14}  {desc}  {DIM('→ ' + cmd)}"
    for alias, (cmd, desc, _) in SHORTCUTS.items()
) + f"""

{HEAD("Common commands:")}
  get_actors_in_level
  spawn_actor          name=MyActor type=StaticMeshActor location=[0,0,100]
  delete_actor         name=MyActor
  create_blueprint     name=BP_Hero parent_class=Character
  compile_blueprint    blueprint_name=BP_Hero
  add_component_to_blueprint  blueprint_name=BP_Hero component_type=CameraComponent component_name=Cam
  add_blueprint_variable      blueprint_name=BP_Hero variable_name=Health variable_type=Float
  save_current_level
  take_screenshot

{HEAD("Params syntax (either form works):")}
  create_blueprint name=BP_Test parent_class=Actor
  create_blueprint {{"name":"BP_Test","parent_class":"Actor"}}

{HEAD("Special commands:")}
  help / ?      show this message
  quit / exit   leave the CLI
  raw           toggle pretty-print vs raw JSON output
"""


# ── param parsing ─────────────────────────────────────────────────────────────
def _coerce(v: str) -> Any:
    """Try to convert a string value to int, float, bool, list, dict, or leave as str."""
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


def parse_params(tokens: list[str]) -> Dict[str, Any]:
    """
    Parse   key=value key2=value2   OR   {"key":"value"}   into a dict.
    Handles values with spaces if quoted, e.g.  name="My Actor".
    """
    if not tokens:
        return {}
    joined = " ".join(tokens).strip()
    # If it looks like a JSON object, parse directly
    if joined.startswith("{"):
        try:
            return json.loads(joined)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON params: {e}") from e
    # key=value pairs
    params: Dict[str, Any] = {}
    for token in tokens:
        if "=" not in token:
            raise ValueError(f"Cannot parse param token: {token!r}  (expected key=value or JSON object)")
        k, _, v = token.partition("=")
        params[k.strip()] = _coerce(v)
    return params


# ── single-shot mode ──────────────────────────────────────────────────────────
def run_single(argv: list[str]):
    command = argv[0]
    params = parse_params(argv[1:]) if len(argv) > 1 else {}
    if command in SHORTCUTS:
        command, _, _ = SHORTCUTS[command]
    response = send_command(command, params)
    print(pretty(response))


# ── REPL ──────────────────────────────────────────────────────────────────────
def repl():
    print(HEAD(f"\n  ue5cli  ·  UnrealMCP {HOST}:{PORT}"))
    print(DIM("  Type 'help' for commands, 'quit' to exit.\n"))

    raw_mode = False

    while True:
        try:
            line = input(BOLD("ue5> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        tokens = line.split()
        cmd = tokens[0].lower()
        rest = tokens[1:]

        if cmd in ("quit", "exit", "q"):
            print(DIM("  Bye."))
            break

        if cmd in ("help", "?"):
            print(HELP_TEXT)
            continue

        if cmd == "raw":
            raw_mode = not raw_mode
            print(DIM(f"  Raw mode: {'on' if raw_mode else 'off'}"))
            continue

        # Expand shortcut aliases
        ue_cmd = SHORTCUTS[cmd][0] if cmd in SHORTCUTS else cmd

        try:
            params = parse_params(rest)
        except ValueError as e:
            print(WARN(f"  ⚠ {e}"))
            continue

        print(DIM(f"  → {ue_cmd}({params if params else ''})"))
        response = send_command(ue_cmd, params)

        if raw_mode:
            print(pretty(response))
        else:
            print_response(response)
        print()


# ── entrypoint ────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) > 1:
        run_single(sys.argv[1:])
    else:
        repl()


if __name__ == "__main__":
    main()
