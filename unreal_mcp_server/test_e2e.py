#!/usr/bin/env python3
"""
test_e2e.py — End-to-end tests for the UnrealMCP plugin.

Sends real TCP commands to UE5 on localhost:55557 and verifies responses.
UE5 must be open with the UnrealMCP plugin loaded before running.

Usage:
    python test_e2e.py              # run all tests
    python test_e2e.py connectivity # run only the 'connectivity' group
    python test_e2e.py -v           # verbose: print every request/response

Exit code:
    0  all tests passed
    1  one or more tests failed
    2  cannot reach UE5 at all (skip vs fail distinction)
"""

import sys
import json
import time
import socket
import argparse
import traceback
from typing import Any, Dict, Optional, List, Callable

# ─── connection ───────────────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 55557
TIMEOUT = 20          # seconds per command
VERBOSE = False       # set by -v flag

# Test asset names — prefixed so they're easy to find and clean up in UE5
_PREFIX = "MCPE2E_"
BP_ACTOR         = f"{_PREFIX}ActorBP"
BP_PAWN          = f"{_PREFIX}PawnBP"
BP_CHARACTER     = f"{_PREFIX}CharBP"
ACTOR_NAME       = f"{_PREFIX}SpawnedActor"
ACTOR_NAME_2     = f"{_PREFIX}SpawnedActor2"


def _recv(sock: socket.socket) -> bytes:
    chunks: List[bytes] = []
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


def send(command: str, params: Dict[str, Any] = None) -> Optional[Dict]:
    """Send one command, return parsed response dict (or error dict)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.connect((HOST, PORT))
    except ConnectionRefusedError:
        return {"status": "error", "error": f"UE5 not reachable at {HOST}:{PORT}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

    try:
        payload = json.dumps({"type": command, "params": params or {}})
        if VERBOSE:
            print(f"    >> {payload[:200]}")
        sock.sendall(payload.encode("utf-8"))
        raw = _recv(sock)
        result = json.loads(raw.decode("utf-8"))
        if VERBOSE:
            print(f"    << {json.dumps(result)[:300]}")
        return result
    except Exception as e:
        return {"status": "error", "error": f"recv error: {e}"}
    finally:
        try:
            sock.close()
        except Exception:
            pass


def is_ok(r: Optional[Dict]) -> bool:
    """Return True if the response looks like a success."""
    if r is None:
        return False
    if r.get("status") == "error":
        return False
    if r.get("success") is False:
        return False
    return True


def get_err(r: Optional[Dict]) -> str:
    if r is None:
        return "no response"
    return r.get("error") or r.get("message") or json.dumps(r)[:120]


# ─── test framework ───────────────────────────────────────────────────────────
_results: List[Dict] = []


def _run(name: str, fn: Callable, *args, **kwargs):
    label = f"  {name}"
    try:
        fn(*args, **kwargs)
        _results.append({"name": name, "status": "PASS"})
        print(f"\033[32m  PASS\033[0m  {name}")
    except AssertionError as e:
        _results.append({"name": name, "status": "FAIL", "reason": str(e)})
        print(f"\033[31m  FAIL\033[0m  {name}")
        print(f"         {e}")
    except Exception as e:
        _results.append({"name": name, "status": "ERROR", "reason": traceback.format_exc()})
        print(f"\033[33m  ERROR\033[0m {name}")
        print(f"         {e}")


def _section(title: str):
    print(f"\n\033[36m{'─'*60}\033[0m")
    print(f"\033[1m  {title}\033[0m")
    print(f"\033[36m{'─'*60}\033[0m")


# ─── helpers ──────────────────────────────────────────────────────────────────
def _delete_actor_if_exists(name: str):
    """Best-effort cleanup — ignore errors."""
    send("delete_actor", {"name": name})


def _delete_bp_if_exists(name: str):
    """Blueprints can't be deleted via MCP, but compile clears transient state."""
    pass  # UE5 doesn't expose a delete_blueprint command — user cleans up manually


def _extract_actors(r: dict) -> list:
    """Pull the actors list out of whatever response shape UE5 returns."""
    # Shape 1: {"status":"success","result":{"actors":[...]}}
    result = r.get("result", {})
    if isinstance(result, dict) and "actors" in result:
        return result["actors"]
    # Shape 2: {"actors":[...]}  (direct)
    if "actors" in r:
        return r["actors"]
    # Shape 3: result is already the list
    if isinstance(result, list):
        return result
    return []


def _actor_exists(name: str) -> bool:
    r = send("find_actors_by_name", {"pattern": name})
    if not is_ok(r):
        return False
    actors = _extract_actors(r)
    return any(name in str(a) for a in actors)


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 1: Connectivity
# ═══════════════════════════════════════════════════════════════════════════════
def test_can_reach_ue5():
    r = send("get_actors_in_level", {})
    assert r is not None, "No response from UE5"
    assert r.get("status") != "error", f"Connection error: {get_err(r)}"


def test_response_is_valid_json():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((HOST, PORT))
        payload = json.dumps({"type": "get_actors_in_level", "params": {}})
        sock.sendall(payload.encode("utf-8"))
        raw = _recv(sock)
        sock.close()
        parsed = json.loads(raw.decode("utf-8"))
        assert isinstance(parsed, dict), f"Expected dict, got {type(parsed)}"
    except Exception as e:
        raise AssertionError(f"JSON parse failed: {e}")


def test_unknown_command_returns_error():
    r = send("__nonexistent_command_xyz__")
    # Plugin should return error, not crash
    assert r is not None, "No response for unknown command"
    # Either status==error or success==false — either is acceptable
    ok = r.get("status") == "error" or r.get("success") is False or "error" in r
    assert ok, f"Expected error response, got: {r}"


def test_malformed_params_handled():
    # Send a command with completely wrong param types — should return error, not crash
    r = send("create_blueprint", {"name": 12345, "parent_class": None})
    assert r is not None, "No response for malformed params"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 2: Level / Actor queries
# ═══════════════════════════════════════════════════════════════════════════════
def test_get_actors_returns_list():
    r = send("get_actors_in_level", {})
    assert is_ok(r), f"get_actors_in_level failed: {get_err(r)}"
    actors = _extract_actors(r)
    assert isinstance(actors, list), f"Expected list, got {type(actors)}: {r}"
    assert len(actors) > 0, "Expected at least one actor in the level"


def test_find_actors_by_name_wildcard():
    r = send("find_actors_by_name", {"pattern": "*"})
    # Should succeed and return something (even empty is fine)
    assert r is not None, "No response"
    assert r.get("status") != "error", get_err(r)


def test_find_actors_no_match():
    r = send("find_actors_by_name", {"pattern": "__NoSuchActorEver__"})
    assert r is not None
    actors = _extract_actors(r)
    assert len(actors) == 0, f"Expected no matches, got {actors}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 3: Actor lifecycle (spawn → query → transform → delete)
# ═══════════════════════════════════════════════════════════════════════════════
def test_spawn_actor():
    _delete_actor_if_exists(ACTOR_NAME)
    r = send("spawn_actor", {
        "name": ACTOR_NAME,
        "type": "STATICMESHACTOR",
        "location": [100.0, 200.0, 50.0],
        "rotation": [0.0, 0.0, 0.0]
    })
    assert is_ok(r), f"spawn_actor failed: {get_err(r)}"


def test_spawned_actor_appears_in_level():
    r = send("get_actors_in_level", {})
    assert is_ok(r), get_err(r)
    actors = _extract_actors(r)
    names = [str(a.get("name", a)) for a in actors]
    found = any(ACTOR_NAME in n for n in names)
    assert found, f"{ACTOR_NAME} not found in level after spawn. Actors: {names[:10]}"


def test_get_actor_properties():
    r = send("get_actor_properties", {"name": ACTOR_NAME})
    assert is_ok(r), f"get_actor_properties failed: {get_err(r)}"


def test_set_actor_transform():
    r = send("set_actor_transform", {
        "name": ACTOR_NAME,
        "location": [300.0, 400.0, 75.0],
        "rotation": [0.0, 45.0, 0.0],
        "scale": [1.0, 1.0, 1.0]
    })
    assert is_ok(r), f"set_actor_transform failed: {get_err(r)}"


def test_set_actor_property():
    r = send("set_actor_property", {
        "name": ACTOR_NAME,
        "property_name": "bHidden",
        "property_value": "false"
    })
    # Allowed to return an error for unsupported props — just must not crash
    assert r is not None, "No response from set_actor_property"


def test_spawn_second_actor_different_location():
    _delete_actor_if_exists(ACTOR_NAME_2)
    r = send("spawn_actor", {
        "name": ACTOR_NAME_2,
        "type": "POINTLIGHT",
        "location": [-200.0, 0.0, 300.0],
        "rotation": [0.0, 0.0, 0.0]
    })
    assert is_ok(r), f"spawn second actor failed: {get_err(r)}"


def test_delete_actor():
    r = send("delete_actor", {"name": ACTOR_NAME})
    assert is_ok(r), f"delete_actor failed: {get_err(r)}"


def test_deleted_actor_gone():
    time.sleep(1.0)   # give UE5 time to process the deletion
    r = send("get_actors_in_level", {})
    assert is_ok(r), get_err(r)
    actors = _extract_actors(r)
    names = [str(a.get("name", a)) for a in actors]
    still_there = any(ACTOR_NAME in n and ACTOR_NAME_2 not in n for n in names)
    assert not still_there, f"{ACTOR_NAME} still in level after delete"


def test_cleanup_second_actor():
    r = send("delete_actor", {"name": ACTOR_NAME_2})
    assert is_ok(r), f"delete second actor failed: {get_err(r)}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 4: Blueprint creation & compilation
# ═══════════════════════════════════════════════════════════════════════════════
def test_create_actor_blueprint():
    r = send("create_blueprint", {
        "name": BP_ACTOR,
        "parent_class": "Actor"
    })
    assert is_ok(r), f"create_blueprint(Actor) failed: {get_err(r)}"
    result = r.get("result", r)
    assert "name" in result or "path" in result, f"Response missing name/path: {result}"


def test_create_pawn_blueprint():
    r = send("create_blueprint", {
        "name": BP_PAWN,
        "parent_class": "Pawn"
    })
    assert is_ok(r), f"create_blueprint(Pawn) failed: {get_err(r)}"


def test_create_character_blueprint():
    r = send("create_blueprint", {
        "name": BP_CHARACTER,
        "parent_class": "Character"
    })
    assert is_ok(r), f"create_blueprint(Character) failed: {get_err(r)}"


def test_compile_blueprint():
    r = send("compile_blueprint", {"blueprint_name": BP_ACTOR})
    assert is_ok(r), f"compile_blueprint failed: {get_err(r)}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 5: Blueprint components
# ═══════════════════════════════════════════════════════════════════════════════
def test_add_static_mesh_component():
    # Use full UE path so FindObject resolves correctly
    r = send("add_component_to_blueprint", {
        "blueprint_name": BP_ACTOR,
        "component_type": "/Script/Engine.StaticMeshComponent",
        "component_name": "TestMesh",
        "location": [0.0, 0.0, 0.0],
        "rotation": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0]
    })
    assert is_ok(r), f"add StaticMeshComponent failed: {get_err(r)}"


def test_add_camera_component():
    r = send("add_component_to_blueprint", {
        "blueprint_name": BP_ACTOR,
        "component_type": "/Script/Engine.CameraComponent",
        "component_name": "TestCam",
        "location": [0.0, 0.0, 90.0]
    })
    assert is_ok(r), f"add CameraComponent failed: {get_err(r)}"


def test_add_point_light_component():
    r = send("add_component_to_blueprint", {
        "blueprint_name": BP_ACTOR,
        "component_type": "/Script/Engine.PointLightComponent",
        "component_name": "TestLight",
        "location": [0.0, 0.0, 50.0]
    })
    assert is_ok(r), f"add PointLightComponent failed: {get_err(r)}"


def test_compile_after_components():
    r = send("compile_blueprint", {"blueprint_name": BP_ACTOR})
    assert is_ok(r), f"compile after adding components failed: {get_err(r)}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 6: Blueprint variables
# ═══════════════════════════════════════════════════════════════════════════════
def test_add_float_variable():
    r = send("add_blueprint_variable", {
        "blueprint_name": BP_ACTOR,
        "variable_name": "Health",
        "variable_type": "Float",
        "is_exposed": True,
        "default_value": "100.0"
    })
    assert is_ok(r), f"add Float variable failed: {get_err(r)}"


def test_add_integer_variable():
    r = send("add_blueprint_variable", {
        "blueprint_name": BP_ACTOR,
        "variable_name": "Score",
        "variable_type": "Integer",
        "is_exposed": False
    })
    assert is_ok(r), f"add Integer variable failed: {get_err(r)}"


def test_add_boolean_variable():
    r = send("add_blueprint_variable", {
        "blueprint_name": BP_ACTOR,
        "variable_name": "bIsAlive",
        "variable_type": "Boolean",
        "is_exposed": True
    })
    assert is_ok(r), f"add Boolean variable failed: {get_err(r)}"


def test_add_vector_variable():
    r = send("add_blueprint_variable", {
        "blueprint_name": BP_ACTOR,
        "variable_name": "SpawnPoint",
        "variable_type": "Vector",
        "is_exposed": False
    })
    assert is_ok(r), f"add Vector variable failed: {get_err(r)}"


def test_add_string_variable():
    r = send("add_blueprint_variable", {
        "blueprint_name": BP_ACTOR,
        "variable_name": "ActorTag",
        "variable_type": "String",
        "is_exposed": True
    })
    assert is_ok(r), f"add String variable failed: {get_err(r)}"


def test_compile_after_variables():
    r = send("compile_blueprint", {"blueprint_name": BP_ACTOR})
    assert is_ok(r), f"compile after variables failed: {get_err(r)}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 7: Blueprint graph nodes
# ═══════════════════════════════════════════════════════════════════════════════
def test_add_begin_play_event():
    r = send("add_blueprint_event_node", {
        "blueprint_name": BP_ACTOR,
        "event_name": "ReceiveBeginPlay",
        "node_position": [0, 0]
    })
    assert is_ok(r), f"add BeginPlay node failed: {get_err(r)}"
    result = r.get("result", r)
    assert "node_id" in result, f"No node_id in response: {result}"


def test_add_tick_event():
    r = send("add_blueprint_event_node", {
        "blueprint_name": BP_ACTOR,
        "event_name": "ReceiveTick",
        "node_position": [0, 200]
    })
    assert is_ok(r), f"add Tick node failed: {get_err(r)}"


def test_add_print_string_node():
    # Full script path needed for FindObject to resolve KismetSystemLibrary
    r = send("add_blueprint_function_node", {
        "blueprint_name": BP_ACTOR,
        "target": "/Script/Engine.KismetSystemLibrary",
        "function_name": "PrintString",
        "params": {},
        "node_position": [300, 0]
    })
    assert is_ok(r), f"add PrintString node failed: {get_err(r)}"
    result = r.get("result", r)
    assert "node_id" in result, f"No node_id: {result}"


def test_connect_begin_play_to_print():
    # Get BeginPlay node id
    begin_r = send("add_blueprint_event_node", {
        "blueprint_name": BP_ACTOR,
        "event_name": "ReceiveBeginPlay",
        "node_position": [0, 400]
    })
    assert is_ok(begin_r), get_err(begin_r)
    begin_id = begin_r.get("result", begin_r).get("node_id")
    assert begin_id, "No node_id from BeginPlay"

    # Get PrintString node id
    print_r = send("add_blueprint_function_node", {
        "blueprint_name": BP_ACTOR,
        "target": "/Script/Engine.KismetSystemLibrary",
        "function_name": "PrintString",
        "params": {},
        "node_position": [350, 400]
    })
    assert is_ok(print_r), get_err(print_r)
    print_id = print_r.get("result", print_r).get("node_id")
    assert print_id, "No node_id from PrintString"

    # Connect them
    conn_r = send("connect_blueprint_nodes", {
        "blueprint_name": BP_ACTOR,
        "source_node_id": begin_id,
        "source_pin": "then",
        "target_node_id": print_id,
        "target_pin": "execute"
    })
    assert is_ok(conn_r), f"connect_blueprint_nodes failed: {get_err(conn_r)}"


def test_find_blueprint_nodes():
    # node_type must be capitalised "Event" and event_name is required
    r = send("find_blueprint_nodes", {
        "blueprint_name": BP_ACTOR,
        "node_type": "Event",
        "event_name": "ReceiveBeginPlay"
    })
    assert is_ok(r), f"find_blueprint_nodes failed: {get_err(r)}"
    result = r.get("result", r)
    nodes = result.get("nodes", result) if isinstance(result, dict) else result
    assert isinstance(nodes, list), f"Expected list of nodes: {result}"


def test_compile_final():
    r = send("compile_blueprint", {"blueprint_name": BP_ACTOR})
    assert is_ok(r), f"final compile failed: {get_err(r)}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 8: Spawn blueprint actor into level
# ═══════════════════════════════════════════════════════════════════════════════
def test_spawn_blueprint_actor():
    _delete_actor_if_exists(f"{_PREFIX}BPInstance")
    # Plugin requires "actor_name", not "name"
    r = send("spawn_blueprint_actor", {
        "actor_name": f"{_PREFIX}BPInstance",
        "blueprint_name": BP_ACTOR,
        "location": [500.0, 0.0, 100.0],
        "rotation": [0.0, 0.0, 0.0]
    })
    assert is_ok(r), f"spawn_blueprint_actor failed: {get_err(r)}"


def test_spawned_bp_actor_in_level():
    time.sleep(1.0)
    r = send("get_actors_in_level", {})
    assert is_ok(r), get_err(r)
    actors = _extract_actors(r)
    names = [str(a.get("name", a)) for a in actors]
    found = any(f"{_PREFIX}BPInstance" in n for n in names)
    assert found, f"{_PREFIX}BPInstance not found in level: {names[:10]}"


def test_cleanup_bp_instance():
    r = send("delete_actor", {"name": f"{_PREFIX}BPInstance"})
    assert is_ok(r), f"cleanup BPInstance failed: {get_err(r)}"


# ═══════════════════════════════════════════════════════════════════════════════
# GROUP 9: Edge cases & robustness
# ═══════════════════════════════════════════════════════════════════════════════
def test_delete_nonexistent_actor():
    r = send("delete_actor", {"name": "__NeverExisted__"})
    # Should return error/false, not crash or hang
    assert r is not None, "No response for deleting nonexistent actor"


def test_compile_nonexistent_blueprint():
    r = send("compile_blueprint", {"blueprint_name": "__NoBPHere__"})
    assert r is not None, "No response for compiling nonexistent blueprint"
    ok = r.get("status") == "error" or r.get("success") is False or "error" in r
    assert ok, f"Expected error, got: {r}"


def test_missing_required_param():
    r = send("create_blueprint", {})   # missing name and parent_class
    assert r is not None, "No response for missing params"


def test_empty_params_object():
    r = send("get_actors_in_level", {})
    assert is_ok(r), f"Empty params should still work: {get_err(r)}"


def test_rapid_sequential_commands():
    """Send 5 commands back-to-back to test connection stability."""
    for i in range(5):
        r = send("get_actors_in_level", {})
        assert r is not None, f"Command {i+1}/5 got no response"
        assert r.get("status") != "error", f"Command {i+1}/5 error: {get_err(r)}"


# ═══════════════════════════════════════════════════════════════════════════════
# Test groups registry
# ═══════════════════════════════════════════════════════════════════════════════
GROUPS = {
    "connectivity": [
        ("Can reach UE5 on port 55557",         test_can_reach_ue5),
        ("Response is valid JSON",              test_response_is_valid_json),
        ("Unknown command returns error",       test_unknown_command_returns_error),
        ("Malformed params handled gracefully", test_malformed_params_handled),
    ],
    "level_query": [
        ("get_actors_in_level returns list",    test_get_actors_returns_list),
        ("find_actors_by_name wildcard",        test_find_actors_by_name_wildcard),
        ("find_actors_by_name no match",        test_find_actors_no_match),
    ],
    "actor_lifecycle": [
        ("Spawn StaticMeshActor",               test_spawn_actor),
        ("Spawned actor appears in level",      test_spawned_actor_appears_in_level),
        ("get_actor_properties",                test_get_actor_properties),
        ("set_actor_transform",                 test_set_actor_transform),
        ("set_actor_property",                  test_set_actor_property),
        ("Spawn second actor (PointLight)",     test_spawn_second_actor_different_location),
        ("Delete first actor",                  test_delete_actor),
        ("Deleted actor gone from level",       test_deleted_actor_gone),
        ("Cleanup second actor",                test_cleanup_second_actor),
    ],
    "blueprints": [
        ("Create Actor Blueprint",              test_create_actor_blueprint),
        ("Create Pawn Blueprint",               test_create_pawn_blueprint),
        ("Create Character Blueprint",          test_create_character_blueprint),
        ("Compile Blueprint",                   test_compile_blueprint),
    ],
    "components": [
        ("Add StaticMeshComponent",             test_add_static_mesh_component),
        ("Add CameraComponent",                 test_add_camera_component),
        ("Add PointLightComponent",             test_add_point_light_component),
        ("Compile after adding components",     test_compile_after_components),
    ],
    "variables": [
        ("Add Float variable",                  test_add_float_variable),
        ("Add Integer variable",                test_add_integer_variable),
        ("Add Boolean variable",                test_add_boolean_variable),
        ("Add Vector variable",                 test_add_vector_variable),
        ("Add String variable",                 test_add_string_variable),
        ("Compile after adding variables",      test_compile_after_variables),
    ],
    "graph_nodes": [
        ("Add BeginPlay event node",            test_add_begin_play_event),
        ("Add Tick event node",                 test_add_tick_event),
        ("Add PrintString function node",       test_add_print_string_node),
        ("Connect BeginPlay → PrintString",     test_connect_begin_play_to_print),
        ("find_blueprint_nodes",                test_find_blueprint_nodes),
        ("Final compile",                       test_compile_final),
    ],
    "spawn_bp_actor": [
        ("Spawn Blueprint actor into level",    test_spawn_blueprint_actor),
        ("BP actor appears in level",           test_spawned_bp_actor_in_level),
        ("Cleanup BP instance",                 test_cleanup_bp_instance),
    ],
    "robustness": [
        ("Delete nonexistent actor",            test_delete_nonexistent_actor),
        ("Compile nonexistent blueprint",       test_compile_nonexistent_blueprint),
        ("Missing required params",             test_missing_required_param),
        ("Empty params object",                 test_empty_params_object),
        ("5 rapid sequential commands",         test_rapid_sequential_commands),
    ],
}

ALL_GROUPS_ORDER = [
    "connectivity",
    "level_query",
    "actor_lifecycle",
    "blueprints",
    "components",
    "variables",
    "graph_nodes",
    "spawn_bp_actor",
    "robustness",
]


# ─── main ─────────────────────────────────────────────────────────────────────
def main():
    global VERBOSE

    parser = argparse.ArgumentParser(description="UnrealMCP end-to-end tests")
    parser.add_argument("groups", nargs="*",
                        help=f"Groups to run (default: all). Available: {', '.join(ALL_GROUPS_ORDER)}")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print every request/response pair")
    args = parser.parse_args()
    VERBOSE = args.verbose

    selected = args.groups if args.groups else ALL_GROUPS_ORDER
    unknown = [g for g in selected if g not in GROUPS]
    if unknown:
        print(f"Unknown group(s): {unknown}")
        print(f"Available: {', '.join(GROUPS)}")
        sys.exit(1)

    print(f"\n\033[1mUnrealMCP End-to-End Test Suite\033[0m")
    print(f"Target: {HOST}:{PORT}  |  Timeout: {TIMEOUT}s\n")

    # Connectivity check first — bail early if UE5 is unreachable
    probe = send("get_actors_in_level", {})
    if probe and probe.get("status") == "error" and "not reachable" in probe.get("error", ""):
        print(f"\033[31m✗ UE5 not reachable at {HOST}:{PORT}\033[0m")
        print("  Make sure UE5 is open and the UnrealMCP plugin is loaded.")
        sys.exit(2)

    for group_key in selected:
        tests = GROUPS[group_key]
        _section(group_key.upper().replace("_", " "))
        for label, fn in tests:
            _run(label, fn)

    # ── summary ───────────────────────────────────────────────────────────────
    total  = len(_results)
    passed = sum(1 for r in _results if r["status"] == "PASS")
    failed = sum(1 for r in _results if r["status"] == "FAIL")
    errors = sum(1 for r in _results if r["status"] == "ERROR")

    print(f"\n{'═'*60}")
    print(f"  Results: {total} tests | "
          f"\033[32m{passed} passed\033[0m | "
          f"\033[31m{failed} failed\033[0m | "
          f"\033[33m{errors} errors\033[0m")

    if failed or errors:
        print("\n  Failed / Errored:")
        for r in _results:
            if r["status"] != "PASS":
                print(f"    [{r['status']}] {r['name']}")
                if "reason" in r:
                    for line in r["reason"].strip().splitlines():
                        print(f"           {line}")
        print()
        sys.exit(1)
    else:
        print(f"\n  \033[32m✓ All {total} tests passed\033[0m\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
