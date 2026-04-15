"""
Enhanced Input System Setup for ThePlayerCharacter
====================================================
1. Create IA_ assets:  IA_FirePulse, IA_FireShotgun, IA_DeployNanomachines, IA_Hack
2. Ensure IMC_Default exists and add key mappings
3. Delete the 8 stub CustomEvent nodes (Fire Pulse, Shotgun, etc.)
4. Add K2Node_EnhancedInputAction for each mechanic
5. Wire Triggered -> downstream node (preserving existing logic)
6. Fix WorldOrigin pins on SphereOverlapActors nodes
7. Add AddMappingContext to BeginPlay if not present
8. Compile
"""
import sys, json
sys.path.insert(0, '/home/user/webapp')
from mcp_client import _send_sync

def mcp(cmd, **kw):
    r = _send_sync(cmd, kw)
    return r

def ok(r):
    s = r.get("status","")
    res = r.get("result", r)
    return s == "success" or res.get("success", False) or res.get("compiled", False)

# ─── Step 1: Create IA_ assets ───────────────────────────────────────────────
print("\n=== STEP 1: Create Enhanced Input Action assets ===")

actions = [
    ("IA_FirePulse",          "Digital",  "/Game/Input"),
    ("IA_FireShotgun",        "Digital",  "/Game/Input"),
    ("IA_DeployNanomachines", "Digital",  "/Game/Input"),
    ("IA_Hack",               "Digital",  "/Game/Input"),
]

ia_paths = {}
for action_name, value_type, path in actions:
    r = mcp("create_enhanced_input_action",
            action_name=action_name,
            value_type=value_type,
            path=path)
    result = r.get("result", r)
    success = ok(r)
    asset_path = result.get("asset_path", f"{path}/{action_name}.{action_name}")
    ia_paths[action_name] = asset_path
    print(f"  {action_name}: {'OK' if success else 'FAIL'} -> {asset_path}")
    print(f"    raw: {json.dumps(r)[:200]}")

# ─── Step 2: Ensure IMC_Default exists and add mappings ──────────────────────
print("\n=== STEP 2: Setup IMC_Default ===")

# Key bindings: Q=FirePulse, E=FireShotgun (or Left Mouse), R=DeployNanomachines, F=Hack
key_bindings = [
    ("IA_FirePulse",          "Q"),
    ("IA_FireShotgun",        "LeftMouseButton"),
    ("IA_DeployNanomachines", "R"),
    ("IA_Hack",               "F"),
]

# Try to create IMC_Default (will update if exists)
imc_mappings = [{"action": a, "key": k} for a, k in key_bindings]
r = mcp("create_input_mapping_context",
        context_name="IMC_Default",
        mappings=imc_mappings,
        path="/Game/Input")
print(f"  create_input_mapping_context: {json.dumps(r)[:300]}")

# Also try add_input_mapping for each action to be safe
for action_name, key in key_bindings:
    r2 = mcp("add_input_mapping",
             imc_name="IMC_Default",
             action_name=action_name,
             key=key)
    print(f"  add_input_mapping {action_name} -> {key}: {json.dumps(r2)[:200]}")

print("\n=== STEP 3: Inspect existing node layout in ThePlayerCharacter ===")

r = mcp("get_blueprint_nodes", blueprint_name="ThePlayerCharacter")
nodes = r.get("result", r).get("nodes", r.get("nodes", []))
print(f"  Total nodes: {len(nodes)}")

# Identify the 8 CustomEvent nodes and their downstream connections
custom_events = [n for n in nodes if n.get("node_type") == "K2Node_CustomEvent"]
print(f"  CustomEvent nodes: {len(custom_events)}")

# Group by Y position to identify mechanics:
# Y≈-880: Fire Pulse
# Y≈-688: Rapid Recycling (nanomachines via GetAllActorsOfClass at -680)
# Y≈-280 to -144: Fire Shotgun
# Y≈384: Deploy Nanomachines (GetAllActorsOfClass at 368)
# Y≈912: another overlap?
# Y≈1228: Hack (SphereTrace + Print)
# Y≈1724: Hack2?

# The plan:
# We have 8 custom events. Looking at the connections:
# DAEA453F(-880)  -> SphereOverlapActors = FIRE PULSE
# ABA18AFF(-688)  -> GetAllActorsOfClass = likely an older mechanic attempt  
# B7C2FECD(-280)  -> GetAllActorsOfClass at Y=-280 = SHOTGUN?
# 24C4FF14(-144)  -> SphereTraceSingle = FIRE SHOTGUN (trace to find WarDrone)
# 209DDE1F(384)   -> GetAllActorsOfClass at 368 = DEPLOY NANOMACHINES
# 1414D441(912)   -> SphereOverlapActors at 912 = DEPLOY NANOMACHINES (overlap)
# 245DC5B0(1228)  -> SphereTraceSingle at 1232 = HACK
# 56EE1BD1(1724)  -> SphereTraceSingle at 1724 = HACK (or second Hack variant)

# Map each custom event to a mechanic
# Based on Y positions and connected functions:
mechanic_map = {
    "DAEA453F": "FirePulse",       # y=-880, SphereOverlapActors -> destroy PacifistDrones
    "24C4FF14": "FireShotgun",     # y=-144, SphereTraceSingle -> destroy WarDrone  
    "B7C2FECD": "FireShotgun2",    # y=-280, GetAllActorsOfClass (duplicate/secondary)
    "ABA18AFF": "Nanomachines2",   # y=-688, GetAllActorsOfClass (duplicate)
    "1414D441": "DeployNanomachines", # y=912, SphereOverlapActors -> destroy PacifistDrones
    "209DDE1F": "Nanomachines3",   # y=384, GetAllActorsOfClass
    "245DC5B0": "Hack",            # y=1228, SphereTraceSingle -> Hack targets
    "56EE1BD1": "Hack2",           # y=1724, SphereTraceSingle
}

# PRIMARY events (one per mechanic) - we'll replace these with EI Action nodes
primary_events = {
    "FirePulse":          "DAEA453F",  # y=-880
    "FireShotgun":        "24C4FF14",  # y=-144 (shotgun trace)
    "DeployNanomachines": "1414D441",  # y=912
    "Hack":               "245DC5B0",  # y=1228
}

# SECONDARY/DUPLICATE events - we'll delete these
secondary_events = ["B7C2FECD", "ABA18AFF", "209DDE1F", "56EE1BD1"]

print("\nPrimary events to replace with EI nodes:")
for mech, eid in primary_events.items():
    print(f"  {eid} -> {mech}")

print("\nSecondary/duplicate events to delete:")
for eid in secondary_events:
    print(f"  {eid}")

# ─── Step 4: Delete secondary duplicate custom events ────────────────────────
print("\n=== STEP 4: Delete duplicate custom event nodes ===")
for eid in secondary_events:
    r = mcp("delete_blueprint_node", blueprint_name="ThePlayerCharacter", node_id=eid)
    print(f"  delete {eid}: {json.dumps(r)[:200]}")

# ─── Step 5: Delete primary custom events & replace with EI Action nodes ─────
print("\n=== STEP 5: Replace CustomEvents with K2Node_EnhancedInputAction nodes ===")

# Get Y positions of primary events for placement
primary_positions = {
    "FirePulse":          [-1728, -880],
    "FireShotgun":        [-1664, -144],
    "DeployNanomachines": [-1728,  912],
    "Hack":               [-1728, 1228],
}

# Downstream connections to restore (from the EventNode.then pin analysis)
# EventNode.then -> first downstream node (the overlap/trace/etc)
downstream_first_node = {
    "DAEA453F": ("K2Node_CallFunction_8",  "B33C2208", "SphereOverlapActors"),
    "24C4FF14": ("K2Node_CallFunction_14", "03023485", "SphereTraceSingle"),
    "1414D441": ("K2Node_CallFunction_23", "6A446C40", "SphereOverlapActors"),
    "245DC5B0": ("K2Node_CallFunction_49", "ED251A00", "SphereTraceSingle"),
}

# Delete primary custom events first
for mech, eid in primary_events.items():
    r = mcp("delete_blueprint_node", blueprint_name="ThePlayerCharacter", node_id=eid)
    print(f"  delete primary {eid} ({mech}): {json.dumps(r)[:150]}")

# Now add EI Action nodes at the same positions
new_ei_nodes = {}
for mech, (ia_name, key) in [
    ("FirePulse",          ("IA_FirePulse",          "Q")),
    ("FireShotgun",        ("IA_FireShotgun",         "LeftMouseButton")),
    ("DeployNanomachines", ("IA_DeployNanomachines",  "R")),
    ("Hack",               ("IA_Hack",                "F")),
]:
    pos = primary_positions[mech]
    r = mcp("add_blueprint_enhanced_input_action_node",
            blueprint_name="ThePlayerCharacter",
            action_asset=ia_name,
            graph_name="EventGraph",
            node_position=pos)
    result = r.get("result", r)
    node_id = result.get("node_id","")
    success = bool(node_id)
    new_ei_nodes[mech] = node_id
    print(f"  add EI node {ia_name} at {pos}: {'OK' if success else 'FAIL'} node_id={node_id}")
    print(f"    raw: {json.dumps(r)[:300]}")

