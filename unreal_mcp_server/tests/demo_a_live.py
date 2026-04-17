"""
Demo A — End-to-End Blueprint Graph Test
Tests the full bp_* tool chain against a live Unreal Engine instance.

Workflow:
  1. Ping UE5
  2. Create (or open) BP_DemoA blueprint
  3. bp_get_graph_summary — confirm EventGraph exists
  4. bp_add_variable — add bIsReady (Boolean)
  5. bp_add_node — add BeginPlay event
  6. bp_add_node — add PrintString node
  7. bp_add_node — add Branch node
  8. bp_get_graph_summary — get node IDs
  9. bp_inspect_node — inspect PrintString for pin names
 10. bp_connect_pins — BeginPlay.then -> PrintString.execute
 11. bp_connect_pins — PrintString.then -> Branch.execute
 12. bp_set_pin_default — PrintString "In String" = "Demo A: Hello from MCP!"
 13. bp_add_function — add TakeDamage function
 14. bp_compile — compile and check had_errors=False
 15. bp_get_graph_summary — final state
"""

import sys, json, socket, textwrap

TUNNEL_HOST = "lie-instability.with.playit.plus"
TUNNEL_PORT = 5462
TIMEOUT = 90  # seconds for slow ops

BP_NAME = "BP_DemoA"

# ── Low-level TCP send ────────────────────────────────────────────────────────

def send(cmd, params, timeout=TIMEOUT):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((TUNNEL_HOST, TUNNEL_PORT))
        msg = json.dumps({"type": cmd, "params": params}) + "\n"
        s.sendall(msg.encode())
        data = b""
        while True:
            chunk = s.recv(8192)
            if not chunk:
                break
            data += chunk
            if b"\n" in data:
                break
        return json.loads(data.decode().strip())
    finally:
        s.close()

# ── Pretty printer ────────────────────────────────────────────────────────────

passed = 0
failed = 0

def check(step, result, expect_success=True):
    global passed, failed
    ok = result.get("status") == "success" or result.get("success") is True
    # For StructuredResult wrappers
    if "result" in result and isinstance(result["result"], dict):
        inner = result["result"]
        ok = ok or inner.get("success") is True
    if expect_success and ok:
        passed += 1
        print(f"  ✅ {step}")
        return result.get("result") or result
    elif not expect_success and not ok:
        passed += 1
        print(f"  ✅ {step} (expected failure)")
        return result.get("result") or result
    else:
        failed += 1
        print(f"  ❌ {step}")
        print(f"     → {json.dumps(result, indent=2)[:500]}")
        return result.get("result") or result

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

# ═══════════════════════════════════════════════════════════════
# STEP 1 — Ping
# ═══════════════════════════════════════════════════════════════
section("STEP 1: Ping UE5")
r = send("ping", {}, timeout=10)
check("ping", r)
print(f"  UE5 says: {r}")

# ═══════════════════════════════════════════════════════════════
# STEP 2 — Create Blueprint
# ═══════════════════════════════════════════════════════════════
section("STEP 2: Create Blueprint BP_DemoA")
r = send("create_blueprint", {
    "name": BP_NAME,
    "parent_class": "Actor",
    "blueprint_path": "/Game/Blueprints"
}, timeout=60)
check("create_blueprint", r)
print(f"  Result: {json.dumps(r, indent=2)[:300]}")

# ═══════════════════════════════════════════════════════════════
# STEP 3 — Get initial graph summary
# ═══════════════════════════════════════════════════════════════
section("STEP 3: bp_get_graph_summary (initial state)")
r = send("get_blueprint_nodes", {
    "blueprint_name": BP_NAME,
    "graph_name": "EventGraph",
    "include_hidden_pins": False,
})
check("get_blueprint_nodes (initial)", r)
nodes_initial = (r.get("result") or r).get("nodes") or []
print(f"  Initial node count: {len(nodes_initial)}")

# ═══════════════════════════════════════════════════════════════
# STEP 4 — Add variable
# ═══════════════════════════════════════════════════════════════
section("STEP 4: bp_add_variable — bIsReady (Boolean)")
r = send("add_blueprint_variable", {
    "blueprint_name": BP_NAME,
    "variable_name": "bIsReady",
    "variable_type": "Boolean",
    "is_exposed": True,
    "default_value": "false",
})
check("add_blueprint_variable", r)
print(f"  Result: {json.dumps(r, indent=2)[:300]}")

# ═══════════════════════════════════════════════════════════════
# STEP 5 — Add BeginPlay event node
# ═══════════════════════════════════════════════════════════════
section("STEP 5: bp_add_node — event:BeginPlay at (-400, 0)")
r = send("add_blueprint_event_node", {
    "blueprint_name": BP_NAME,
    "graph_name": "EventGraph",
    "event_name": "BeginPlay",
    "node_x": -400,
    "node_y": 0,
})
check("add_blueprint_event_node", r)
begin_result = r.get("result") or r
begin_id = begin_result.get("node_id") or begin_result.get("node_guid") or ""
print(f"  BeginPlay node_id: {begin_id}")

# ═══════════════════════════════════════════════════════════════
# STEP 6 — Add PrintString node
# ═══════════════════════════════════════════════════════════════
section("STEP 6: bp_add_node — print_string at (0, 0)")
r = send("add_blueprint_function_node", {
    "blueprint_name": BP_NAME,
    "graph_name": "EventGraph",
    "function_name": "PrintString",
    "node_x": 0,
    "node_y": 0,
})
check("add_blueprint_function_node (PrintString)", r)
print_result = r.get("result") or r
print_id = print_result.get("node_id") or print_result.get("node_guid") or ""
print(f"  PrintString node_id: {print_id}")

# ═══════════════════════════════════════════════════════════════
# STEP 7 — Add Branch node
# ═══════════════════════════════════════════════════════════════
section("STEP 7: bp_add_node — branch at (400, 0)")
r = send("add_blueprint_branch_node", {
    "blueprint_name": BP_NAME,
    "graph_name": "EventGraph",
    "node_x": 400,
    "node_y": 0,
})
check("add_blueprint_branch_node", r)
branch_result = r.get("result") or r
branch_id = branch_result.get("node_id") or branch_result.get("node_guid") or ""
print(f"  Branch node_id: {branch_id}")

# ═══════════════════════════════════════════════════════════════
# STEP 8 — Graph summary (get all node IDs)
# ═══════════════════════════════════════════════════════════════
section("STEP 8: bp_get_graph_summary (after adding nodes)")
r = send("get_blueprint_nodes", {
    "blueprint_name": BP_NAME,
    "graph_name": "EventGraph",
    "include_hidden_pins": False,
})
check("get_blueprint_nodes (after adding)", r)
nodes_data = (r.get("result") or r)
nodes = nodes_data.get("nodes") or []
print(f"  Node count: {len(nodes)}")
for n in nodes:
    nid = n.get("node_id") or n.get("node_guid") or "?"
    ntype = n.get("node_type") or n.get("node_name") or "?"
    title = n.get("function_name") or n.get("event_name") or n.get("title") or ntype
    print(f"    [{nid[:12]}] {title}")
    # Capture IDs if we didn't get them from add responses
    if not begin_id and ("BeginPlay" in title or "ReceiveBeginPlay" in title):
        begin_id = nid
    if not print_id and "Print" in title:
        print_id = nid
    if not branch_id and ("Branch" in title or "IfThenElse" in title):
        branch_id = nid

print(f"\n  Using IDs:")
print(f"    BeginPlay:   {begin_id}")
print(f"    PrintString: {print_id}")
print(f"    Branch:      {branch_id}")

# ═══════════════════════════════════════════════════════════════
# STEP 9 — Inspect PrintString for pin names
# ═══════════════════════════════════════════════════════════════
section("STEP 9: bp_inspect_node — PrintString pin names")
if print_id:
    r = send("get_node_by_id", {
        "blueprint_name": BP_NAME,
        "graph_name": "EventGraph",
        "node_id": print_id,
    })
    check("get_node_by_id (PrintString)", r)
    node_data = (r.get("result") or r).get("node") or (r.get("result") or r)
    pins = node_data.get("pins") or []
    print_exec_in = ""
    print_exec_out = ""
    for p in pins:
        pname = p.get("pin_name") or p.get("name") or ""
        pdir = p.get("direction") or ""
        ptype = p.get("pin_type") or p.get("type") or ""
        print(f"    pin: '{pname}' dir={pdir} type={ptype}")
        if ptype in ("exec", "execute", "") and pdir in ("input", "EGPD_Input", 0):
            if not print_exec_in:
                print_exec_in = pname
        if ptype in ("exec", "execute", "") and pdir in ("output", "EGPD_Output", 1):
            if not print_exec_out:
                print_exec_out = pname
    # Common aliases if detection failed
    if not print_exec_in: print_exec_in = "execute"
    if not print_exec_out: print_exec_out = "then"
    print(f"\n  PrintString exec-in pin:  '{print_exec_in}'")
    print(f"  PrintString exec-out pin: '{print_exec_out}'")
else:
    print("  SKIP — no PrintString node_id")
    print_exec_in = "execute"
    print_exec_out = "then"

# ═══════════════════════════════════════════════════════════════
# STEP 10 — Connect BeginPlay.then -> PrintString.execute
# ═══════════════════════════════════════════════════════════════
section("STEP 10: bp_connect_pins — BeginPlay.then → PrintString.execute")
if begin_id and print_id:
    r = send("connect_blueprint_nodes", {
        "blueprint_name": BP_NAME,
        "graph_name": "EventGraph",
        "source_node_id": begin_id,
        "source_pin": "then",
        "target_node_id": print_id,
        "target_pin": print_exec_in,
    })
    check("connect_blueprint_nodes (BeginPlay→PrintString)", r)
    print(f"  Result: {json.dumps(r, indent=2)[:300]}")
else:
    print("  SKIP — missing node IDs")

# ═══════════════════════════════════════════════════════════════
# STEP 11 — Connect PrintString.then -> Branch.execute
# ═══════════════════════════════════════════════════════════════
section("STEP 11: bp_connect_pins — PrintString.then → Branch.execute")
if print_id and branch_id:
    r = send("connect_blueprint_nodes", {
        "blueprint_name": BP_NAME,
        "graph_name": "EventGraph",
        "source_node_id": print_id,
        "source_pin": print_exec_out,
        "target_node_id": branch_id,
        "target_pin": "execute",
    })
    check("connect_blueprint_nodes (PrintString→Branch)", r)
    print(f"  Result: {json.dumps(r, indent=2)[:300]}")
else:
    print("  SKIP — missing node IDs")

# ═══════════════════════════════════════════════════════════════
# STEP 12 — Set PrintString default value
# ═══════════════════════════════════════════════════════════════
section("STEP 12: bp_set_pin_default — PrintString 'In String'")
if print_id:
    # Try common pin names for the string input
    for pin_name in ["In String", "InString", "String"]:
        r = send("set_node_pin_value", {
            "blueprint_name": BP_NAME,
            "graph_name": "EventGraph",
            "node_id": print_id,
            "pin_name": pin_name,
            "value": "Demo A: Hello from MCP!",
        })
        ok = r.get("status") == "success" or r.get("success") is True
        if ok:
            check(f"set_node_pin_value pin='{pin_name}'", r)
            print(f"  Set '{pin_name}' successfully")
            break
        else:
            print(f"  pin '{pin_name}' → {r.get('error') or r.get('message') or 'failed'}")
    else:
        failed += 1
        print(f"  ❌ Could not find the string input pin on PrintString")
else:
    print("  SKIP — no PrintString node_id")

# ═══════════════════════════════════════════════════════════════
# STEP 13 — Add TakeDamage function
# ═══════════════════════════════════════════════════════════════
section("STEP 13: bp_add_function — TakeDamage")
# Use exec_python to create function graph
add_fn_code = """
import unreal

def find_bp(name):
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    results = reg.get_assets_by_class('Blueprint', True)
    for a in results:
        if a.asset_name == name:
            return unreal.load_asset(a.object_path)
    return None

bp = unreal.load_asset('/Game/Blueprints/BP_DemoA') or find_bp('BP_DemoA')
if bp is None:
    raise RuntimeError("Blueprint BP_DemoA not found")

existing = [g.get_name() for g in (bp.function_graphs or [])]
if 'TakeDamage' not in existing:
    g = unreal.BlueprintEditorLibrary.add_function_graph(bp, 'TakeDamage')
    if g is None:
        raise RuntimeError("add_function_graph returned None")
    unreal.BlueprintEditorLibrary.mark_blueprint_as_structurally_modified(bp)
    result = 'created'
else:
    result = 'already_existed'

print(result)
"""
r = send("exec_python", {"code": add_fn_code.strip()}, timeout=60)
ok = r.get("status") == "success" or (r.get("result") or {}).get("success") is True
output = (r.get("result") or r).get("output") or str(r)
print(f"  exec_python output: {output[:200]}")
if ok or "created" in str(output) or "already_existed" in str(output):
    passed += 1
    print(f"  ✅ bp_add_function (TakeDamage via exec_python)")
else:
    failed += 1
    print(f"  ❌ bp_add_function (TakeDamage) → {json.dumps(r)[:400]}")

# ═══════════════════════════════════════════════════════════════
# STEP 14 — Compile
# ═══════════════════════════════════════════════════════════════
section("STEP 14: bp_compile — BP_DemoA")
r = send("compile_blueprint", {"blueprint_name": BP_NAME}, timeout=90)
check("compile_blueprint", r)
compile_data = r.get("result") or r
had_errors = compile_data.get("had_errors", False)
msgs = compile_data.get("compile_messages") or compile_data.get("messages") or []
print(f"  had_errors: {had_errors}")
if msgs:
    print("  compile_messages:")
    for m in msgs[:5]:
        print(f"    {m}")

# ═══════════════════════════════════════════════════════════════
# STEP 15 — Final graph summary
# ═══════════════════════════════════════════════════════════════
section("STEP 15: bp_get_graph_summary (final state)")
r = send("get_blueprint_nodes", {
    "blueprint_name": BP_NAME,
    "graph_name": "EventGraph",
    "include_hidden_pins": False,
})
check("get_blueprint_nodes (final)", r)
nodes_final = (r.get("result") or r).get("nodes") or []
print(f"  Final node count: {len(nodes_final)}")
for n in nodes_final:
    nid = n.get("node_id") or n.get("node_guid") or "?"
    title = n.get("function_name") or n.get("event_name") or n.get("title") or n.get("node_type") or "?"
    pins = n.get("pins") or []
    connected = [p for p in pins if p.get("linked_to")]
    print(f"    [{nid[:12]}] {title} — {len(pins)} pins, {len(connected)} connected")

# ═══════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
print(f"  DEMO A RESULTS: {passed} passed, {failed} failed")
compile_verdict = "✅ CLEAN COMPILE" if not had_errors else "❌ COMPILE ERRORS"
print(f"  Compile: {compile_verdict}")
print(f"{'═'*60}\n")

sys.exit(0 if failed == 0 else 1)
