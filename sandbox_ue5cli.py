#!/usr/bin/env python3
"""
Sandbox-side UE5 CLI - sends commands through the Playit tunnel to the
UnrealMCP plugin running in the user's UE5 editor.

Usage:
    python3 sandbox_ue5cli.py get_actors_in_level
    python3 sandbox_ue5cli.py create_blueprint name=BP_Test parent_class=Actor

    # Scalar values
    python3 sandbox_ue5cli.py delete_blueprint_node blueprint_name=ThePlayerCharacter node_id=K2Node_CallFunction_40

    # JSON values (wrap in single quotes on the shell)
    python3 sandbox_ue5cli.py add_blueprint_function_node blueprint_name=ThePlayerCharacter function_name=PrintString 'node_position=[0,0]'
    python3 sandbox_ue5cli.py add_blueprint_function_node blueprint_name=BP_Test function_name=Delay 'params={"Duration":"1.5"}'

    # Pass an entire params JSON blob as the second argument
    python3 sandbox_ue5cli.py get_blueprint_nodes '{"blueprint_name":"ThePlayerCharacter","graph_name":"EventGraph"}'
"""
import socket, json, sys
from typing import Any, Dict, Optional

HOST = "lie-instability.with.playit.plus"
PORT = 5462
TIMEOUT = 30


def send_command(command: str, params: Dict[str, Any] = None) -> Optional[Dict]:
    msg = json.dumps({"type": command, "params": params or {}}) + "\n"
    try:
        s = socket.socket()
        s.settimeout(TIMEOUT)
        s.connect((HOST, PORT))
        s.sendall(msg.encode("utf-8"))

        chunks = []
        while True:
            try:
                chunk = s.recv(8192)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)
            data = b"".join(chunks)
            try:
                return json.loads(data.decode("utf-8").strip())
            except json.JSONDecodeError:
                continue
        return {"status": "error", "error": "No complete JSON response received"}
    except Exception as e:
        return {"status": "error", "error": str(e)}
    finally:
        try:
            s.close()
        except Exception:
            pass


def parse_params(args: list) -> Dict[str, Any]:
    """
    Parse CLI arguments into a params dict.

    Supports three forms:
      1. A single bare JSON object as the only argument:
            '{"blueprint_name":"Foo","graph_name":"EventGraph"}'
      2. key=value pairs where the value is a JSON literal:
            blueprint_name=ThePlayerCharacter
            'node_position=[0,200]'
            'params={"Duration":"1.5"}'
            bSweep=false
      3. key=value pairs where the value is a plain string/number/bool
         (auto-coerced as before).
    """
    params: Dict[str, Any] = {}

    # Case 1: single arg that is a bare JSON object
    if len(args) == 1 and args[0].strip().startswith("{"):
        try:
            return json.loads(args[0])
        except json.JSONDecodeError:
            pass  # fall through to key=value parsing

    for token in args:
        if "=" not in token:
            continue
        k, v = token.split("=", 1)

        # Try to parse value as JSON first (handles arrays, objects, bools, numbers)
        try:
            params[k] = json.loads(v)
            continue
        except (json.JSONDecodeError, ValueError):
            pass

        # Plain string fallback
        params[k] = v

    return params


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 sandbox_ue5cli.py <command> [key=value ...]")
        print("       python3 sandbox_ue5cli.py <command> '{\"key\":\"value\",...}'")
        sys.exit(1)

    command = sys.argv[1]
    params  = parse_params(sys.argv[2:])

    print(f"→ {HOST}:{PORT}  command={command}  params={json.dumps(params)}")
    result = send_command(command, params)

    # Unwrap the C++ bridge envelope: {"status":"success","result":{...}} -> {...}
    if isinstance(result, dict) and result.get("status") == "success" and "result" in result:
        result = result["result"]

    print(json.dumps(result, indent=2))
