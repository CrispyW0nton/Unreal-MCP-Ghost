#!/usr/bin/env python3
"""
ue5cli.py — One-shot CLI for Unreal Engine 5 via the UnrealMCP TCP plugin.

Usage:
    python ue5cli.py <command> [key=value ...]
    python ue5cli.py <command> '{"key":"value"}'
    python ue5cli.py --list

Param rules:
  • key=value pairs: strings stay as strings, numbers become int/float, true/false
    become booleans, [1,2,3] becomes a JSON array.
  • Single JSON object: pass the whole params dict as a quoted JSON string.

Examples:
    python ue5cli.py get_actors_in_level
    python ue5cli.py find_actors_by_name pattern=BP_
    python ue5cli.py spawn_actor name=Cube type=StaticMeshActor location=[0,0,100]
    python ue5cli.py delete_actor name=Cube
    python ue5cli.py create_blueprint name=BP_Hero parent_class=Character
    python ue5cli.py compile_blueprint blueprint_name=BP_Hero
    python ue5cli.py add_component_to_blueprint blueprint_name=BP_Hero component_type=StaticMesh component_name=Mesh
    python ue5cli.py add_blueprint_variable blueprint_name=BP_Hero variable_name=Health variable_type=Float
    python ue5cli.py add_blueprint_event_node blueprint_name=BP_Hero event_name=ReceiveBeginPlay
    python ue5cli.py add_blueprint_function_node blueprint_name=BP_Hero target=KismetSystemLibrary function_name=PrintString
    python ue5cli.py connect_blueprint_nodes blueprint_name=BP_Hero source_node_id=<guid> source_pin=then target_node_id=<guid> target_pin=execute
    python ue5cli.py find_blueprint_nodes blueprint_name=BP_Hero node_type=Event event_name=ReceiveBeginPlay
    python ue5cli.py spawn_blueprint_actor blueprint_name=BP_Hero actor_name=Hero1 location=[0,0,0]
    python ue5cli.py take_screenshot filepath=C:/screenshot.png
    python ue5cli.py exec_python code="import unreal; print(unreal.SystemLibrary.get_engine_version())"
    python ue5cli.py exec_python code="1+1" mode=evaluate_statement
"""

import os
import sys
import json
import socket
import argparse
from typing import Any, Dict, Optional

# ─── Configuration ────────────────────────────────────────────────────────────
# Priority: --host/--port flags  >  UNREAL_HOST/UNREAL_PORT env vars  >  defaults
HOST = os.environ.get("UNREAL_HOST", "127.0.0.1")
PORT = int(os.environ.get("UNREAL_PORT", "55557"))
TIMEOUT = 15

# ── command catalogue ─────────────────────────────────────────────────────────
# Each entry: (command_name, short_description, example_params, required_params)
COMMANDS = [
    # ─ Editor / level ─────────────────────────────────────────────────────────
    (
        "get_actors_in_level",
        "List all actors in the current level",
        "",
        [],
    ),
    (
        "find_actors_by_name",
        "Find actors whose name contains <pattern>",
        "pattern=BP_",
        ["pattern"],
    ),
    (
        "spawn_actor",
        "Spawn a primitive actor into the level",
        "name=Cube type=StaticMeshActor location=[0,0,100]",
        ["name", "type"],
        # type values: StaticMeshActor | PointLight | SpotLight | DirectionalLight | CameraActor
    ),
    (
        "delete_actor",
        "Delete an actor from the level by exact name",
        "name=Cube",
        ["name"],
    ),
    (
        "set_actor_transform",
        "Move / rotate / scale an actor  (all transform fields optional)",
        "name=Cube location=[0,0,200] rotation=[0,45,0] scale=[2,2,2]",
        ["name"],
    ),
    (
        "get_actor_properties",
        "Return all properties of an actor",
        "name=Cube",
        ["name"],
    ),
    (
        "set_actor_property",
        "Set a single property on an actor",
        "name=Cube property_name=bHidden property_value=true",
        ["name", "property_name", "property_value"],
    ),
    (
        "focus_viewport",
        "Move the editor viewport camera  (target= or location= required)",
        "target=Cube distance=500",
        [],
    ),
    (
        "take_screenshot",
        "Save a viewport screenshot to a local file path",
        "filepath=C:/Users/NewAdmin/Desktop/shot.png",
        ["filepath"],
    ),
    # ─ Blueprint assets ────────────────────────────────────────────────────────
    (
        "create_blueprint",
        "Create a new Blueprint asset under /Game/Blueprints/",
        "name=BP_Hero parent_class=Character",
        ["name"],
        # parent_class default: Actor. Options: Actor | Pawn | Character | etc.
    ),
    (
        "compile_blueprint",
        "Compile a Blueprint asset",
        "blueprint_name=BP_Hero",
        ["blueprint_name"],
    ),
    (
        "set_blueprint_property",
        "Set a property on a Blueprint's class default object",
        "blueprint_name=BP_Hero property_name=bReplicates property_value=true",
        ["blueprint_name", "property_name", "property_value"],
    ),
    (
        "set_pawn_properties",
        "Set common Pawn properties (auto_possess_player, use_controller_rotation_*)",
        "blueprint_name=BP_Hero auto_possess_player=Player0",
        ["blueprint_name"],
    ),
    # ─ Components ──────────────────────────────────────────────────────────────
    (
        "add_component_to_blueprint",
        "Add a component to a Blueprint's construction script",
        "blueprint_name=BP_Hero component_type=StaticMesh component_name=Mesh",
        ["blueprint_name", "component_type", "component_name"],
        # component_type short names (case-insensitive, 'Component' suffix optional):
        #   StaticMesh  Camera  PointLight  SpotLight  DirectionalLight
        #   Box  Sphere  Capsule  Arrow  Audio  SpringArm  SkeletalMesh
        #   Widget  CharacterMovement  ProjectileMovement  Scene  ChildActor
    ),
    (
        "set_component_property",
        "Set a property on a Blueprint component template",
        "blueprint_name=BP_Hero component_name=Mesh property_name=bCastShadow property_value=false",
        ["blueprint_name", "component_name", "property_name", "property_value"],
    ),
    (
        "set_static_mesh_properties",
        "Assign a static mesh asset and/or material to a StaticMeshComponent",
        "blueprint_name=BP_Hero component_name=Mesh static_mesh=/Game/Meshes/Cube",
        ["blueprint_name", "component_name"],
    ),
    (
        "set_physics_properties",
        "Configure physics on a PrimitiveComponent in a Blueprint",
        "blueprint_name=BP_Hero component_name=Mesh simulate_physics=true mass=50",
        ["blueprint_name", "component_name"],
    ),
    # ─ Blueprint variables ─────────────────────────────────────────────────────
    (
        "add_blueprint_variable",
        "Add a member variable to a Blueprint",
        "blueprint_name=BP_Hero variable_name=Health variable_type=Float is_exposed=true",
        ["blueprint_name", "variable_name", "variable_type"],
        # variable_type: Boolean | Integer | Int | Float | String | Vector
    ),
    # ─ Blueprint graph nodes ───────────────────────────────────────────────────
    (
        "add_blueprint_event_node",
        "Add an event node to the event graph",
        "blueprint_name=BP_Hero event_name=ReceiveBeginPlay node_position=[0,0]",
        ["blueprint_name", "event_name"],
        # Common event names: ReceiveBeginPlay  ReceiveTick  ReceiveEndPlay
        #   ReceiveHit  ReceiveActorBeginOverlap  ReceiveActorEndOverlap
    ),
    (
        "add_blueprint_function_node",
        "Add a function call node (use target= to specify class)",
        "blueprint_name=BP_Hero target=KismetSystemLibrary function_name=PrintString node_position=[300,0]",
        ["blueprint_name", "function_name"],
        # target examples: KismetSystemLibrary  UGameplayStatics  KismetMathLibrary
        # or omit target to search the blueprint's own class
    ),
    (
        "connect_blueprint_nodes",
        "Connect two graph nodes by pin name",
        "blueprint_name=BP_Hero source_node_id=<guid> source_pin=then target_node_id=<guid> target_pin=execute",
        ["blueprint_name", "source_node_id", "source_pin", "target_node_id", "target_pin"],
    ),
    (
        "find_blueprint_nodes",
        "Search for nodes in the event graph  (node_type=Event requires event_name=)",
        "blueprint_name=BP_Hero node_type=Event event_name=ReceiveBeginPlay",
        ["blueprint_name", "node_type"],
        # node_type must be exactly: Event
        # When node_type=Event you must also pass event_name=<EventName>
    ),
    (
        "add_blueprint_self_reference",
        "Add a 'Get self' node to the event graph",
        "blueprint_name=BP_Hero node_position=[0,200]",
        ["blueprint_name"],
    ),
    (
        "add_blueprint_get_self_component_reference",
        "Add a 'Get component' node for a component owned by this Blueprint",
        "blueprint_name=BP_Hero component_name=Mesh node_position=[0,300]",
        ["blueprint_name", "component_name"],
    ),
    (
        "add_blueprint_input_action_node",
        "Add a legacy Input Action event node",
        "blueprint_name=BP_Hero action_name=Jump node_position=[0,400]",
        ["blueprint_name", "action_name"],
    ),
    # ─ Blueprint actor spawning ────────────────────────────────────────────────
    (
        "spawn_blueprint_actor",
        "Place a compiled Blueprint instance in the level",
        "blueprint_name=BP_Hero actor_name=Hero1 location=[500,0,100]",
        ["blueprint_name", "actor_name"],
        # NOTE: use 'actor_name' (not 'name') for the instance label
    ),
    # ─ Python execution ────────────────────────────────────────────────────────
    (
        "exec_python",
        "Execute arbitrary Python code inside the UE5 editor  (requires Python Editor Script Plugin)",
        r'code="import unreal; print(unreal.SystemLibrary.get_engine_version())"',
        ["code"],
        # mode (optional):
        #   execute_file       (default) run multi-line scripts; \n = newline
        #   execute_statement  run one statement and print its result
        #   evaluate_statement evaluate one expression and return its value
        #
        # Multi-line example:
        #   python ue5cli.py exec_python code="import unreal\nactors = unreal.EditorLevelLibrary.get_all_level_actors()\nprint(len(actors))"
        #
        # Single expression example:
        #   python ue5cli.py exec_python code="1+1" mode=evaluate_statement
        #
        # Response fields:
        #   output         - captured log (info/warning/error lines)
        #   command_result - expression value (evaluate_statement only)
        #   success        - true/false
    ),
]


# ── socket send/receive ───────────────────────────────────────────────────────
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
            return data          # complete JSON → done
        except json.JSONDecodeError:
            continue             # partial → keep reading
    return b"".join(chunks)


def send_command(command: str, params: Dict[str, Any] = None) -> Optional[Dict]:
    """Send one command to UE5 and return the parsed JSON response."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        return {
            "status": "error",
            "error": (
                f"Cannot connect to UE5 on {HOST}:{PORT}. "
                "Is the UnrealMCP plugin loaded and UE5 running?"
            ),
        }
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
    """Convert a string token to the most appropriate Python type."""
    s = v.strip()
    if s.lower() == "true":  return True
    if s.lower() == "false": return False
    if s.lower() == "null":  return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    try:
        parsed = json.loads(s)
        if isinstance(parsed, (list, dict)):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass
    return s


def parse_params(tokens: list) -> Dict[str, Any]:
    """Parse key=value tokens or a single JSON object string into a dict."""
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
                f"  Example:  create_blueprint name=BP_Test parent_class=Actor"
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
            "quick examples:",
            "  python ue5cli.py get_actors_in_level",
            "  python ue5cli.py create_blueprint name=BP_Hero parent_class=Character",
            "  python ue5cli.py spawn_actor name=Cube type=StaticMeshActor location=[0,0,100]",
            "  python ue5cli.py add_component_to_blueprint blueprint_name=BP_Hero component_type=StaticMesh component_name=Mesh",
            "  python ue5cli.py add_blueprint_event_node blueprint_name=BP_Hero event_name=ReceiveBeginPlay",
            "  python ue5cli.py add_blueprint_function_node blueprint_name=BP_Hero target=KismetSystemLibrary function_name=PrintString",
            "  python ue5cli.py find_blueprint_nodes blueprint_name=BP_Hero node_type=Event event_name=ReceiveBeginPlay",
            "  python ue5cli.py spawn_blueprint_actor blueprint_name=BP_Hero actor_name=Hero1 location=[500,0,100]",
            "  python ue5cli.py compile_blueprint blueprint_name=BP_Hero",
            "  python ue5cli.py delete_actor name=Cube",
        ]),
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="UE5 command to send  (use --list to see all commands)",
    )
    parser.add_argument(
        "params",
        nargs="*",
        help="Parameters as key=value pairs or a single JSON object",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Print all available commands with required params and examples",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="UE5 hostname — overrides UNREAL_HOST env var (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=None,
        help="UnrealMCP port — overrides UNREAL_PORT env var (default: 55557)",
    )
    parser.add_argument(
        "--raw", "-r",
        action="store_true",
        help="Print compact JSON (default: pretty-printed)",
    )

    args = parser.parse_args()
    # --host/--port flags take priority over env vars (env vars already in module globals)
    if args.host is not None:
        HOST = args.host
    if args.port is not None:
        PORT = args.port

    # ── --list ────────────────────────────────────────────────────────────────
    if args.list:
        print(f"\nUnrealMCP commands  →  {HOST}:{PORT}\n")
        for entry in COMMANDS:
            cmd, desc, example = entry[0], entry[1], entry[2]
            req = entry[3] if len(entry) > 3 else []
            notes = [l.strip() for l in (entry[4] if len(entry) > 4 else "").splitlines() if l.strip()]
            print(f"  {cmd}")
            print(f"      {desc}")
            if req:
                print(f"      required: {', '.join(req)}")
            if example:
                print(f"      e.g.  python ue5cli.py {cmd} {example}")
            for note in notes:
                print(f"      # {note}")
            print()
        sys.exit(0)

    # ── run command ───────────────────────────────────────────────────────────
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

    # Exit 1 on error so PowerShell / bash can check $LASTEXITCODE / $?
    if response and (
        response.get("status") == "error"
        or response.get("error") is not None
        or response.get("success") is False
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
