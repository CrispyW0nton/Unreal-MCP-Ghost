"""
Build all Lab-4D gameplay blueprints via MCP plugin commands.
Run with: python build_all_blueprints.py
"""
import sys, json, time
sys.path.insert(0, '/home/user/webapp')
from mcp_client import _send_sync

def mcp(cmd, params=None):
    if params is None:
        params = {}
    r = _send_sync(cmd, params)
    if isinstance(r, dict) and r.get("status") == "success":
        result = r.get("result", r)
        if isinstance(result, dict):
            return result
    return r

def node_id(r):
    """Extract node_id from a result dict."""
    if isinstance(r, dict):
        if "result" in r and isinstance(r["result"], dict):
            return r["result"].get("node_id", "")
        return r.get("node_id", "")
    return ""

def ok(r, label=""):
    nid = node_id(r)
    status = "OK" if nid else "WARN"
    print(f"  [{status}] {label}: node_id={nid}")
    return nid

def connect(bp, src, src_pin, tgt, tgt_pin):
    if not src or not tgt:
        print(f"  [SKIP] connect {src_pin}->{tgt_pin}: missing node id")
        return
    r = mcp("connect_blueprint_nodes", {
        "blueprint_name": bp,
        "source_node_id": src,
        "source_pin": src_pin,
        "target_node_id": tgt,
        "target_pin": tgt_pin
    })
    s = r.get("result", r) if isinstance(r, dict) else r
    success = s.get("success", False) if isinstance(s, dict) else False
    print(f"  [{'OK' if success else 'FAIL'}] connect {src_pin} -> {tgt_pin}")

def compile(bp):
    r = mcp("compile_blueprint", {"blueprint_name": bp})
    s = r.get("result", r) if isinstance(r, dict) else r
    success = s.get("success", False) if isinstance(s, dict) else False
    print(f"  [{'COMPILED' if success else 'COMPILE-FAIL'}] {bp}")

def event(bp, event_name, pos):
    r = mcp("add_blueprint_event_node", {
        "blueprint_name": bp,
        "event_name": event_name,
        "node_position": pos
    })
    return node_id(r)

def func(bp, fn_name, target="", pos=None, params=None):
    if pos is None: pos = [0, 0]
    if params is None: params = {}
    r = mcp("add_blueprint_function_node", {
        "blueprint_name": bp,
        "function_name": fn_name,
        "target": target,
        "node_position": pos,
        "params": params,
        "allow_duplicates": True
    })
    return node_id(r)

def varget(bp, var_name, pos=None):
    if pos is None: pos = [0, 0]
    r = mcp("add_blueprint_variable_get_node", {
        "blueprint_name": bp,
        "variable_name": var_name,
        "node_position": pos
    })
    return node_id(r)

def varset(bp, var_name, pos=None):
    if pos is None: pos = [0, 0]
    r = mcp("add_blueprint_variable_set_node", {
        "blueprint_name": bp,
        "variable_name": var_name,
        "node_position": pos
    })
    return node_id(r)

def branch(bp, pos=None):
    if pos is None: pos = [0, 0]
    r = mcp("add_blueprint_branch_node", {
        "blueprint_name": bp,
        "node_position": pos
    })
    return node_id(r)

def print_string(bp, msg="", pos=None):
    if pos is None: pos = [0, 0]
    r = mcp("add_print_string_node", {
        "blueprint_name": bp,
        "message": msg,
        "node_position": pos
    })
    return node_id(r)

def get_component(bp, comp_name, pos=None):
    if pos is None: pos = [0, 0]
    r = mcp("add_blueprint_get_component_node", {
        "blueprint_name": bp,
        "component_name": comp_name,
        "node_position": pos
    })
    return node_id(r)

def set_pin(bp, nid, pin_name, pin_value):
    r = mcp("set_node_pin_value", {
        "blueprint_name": bp,
        "node_id": nid,
        "pin_name": pin_name,
        "pin_value": str(pin_value)
    })
    return r

# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BUILD 1: BP_PacifistDrone — moves forward slowly on Tick")
print("="*60)
bp = "BP_PacifistDrone"

# EventTick -> GetActorForwardVector -> * MoveSpeed -> AddActorWorldOffset
tick   = event(bp, "ReceiveTick", [0, 0]);         print(f"  tick: {tick}")
fwd    = func(bp, "GetActorForwardVector", "Actor", [300, 0])
mspd   = varget(bp, "MoveSpeed", [300, 100])
mult   = func(bp, "Multiply_VectorFloat", "KismetMathLibrary", [600, 0])
delta  = func(bp, "GetWorldDeltaSeconds", "KismetSystemLibrary", [0, 200])
mult2  = func(bp, "Multiply_VectorFloat", "KismetMathLibrary", [800, 0], allow_duplicates=True) if False else None
addoff = func(bp, "K2_AddActorWorldOffset", "Actor", [900, 0])

print(f"  fwd={fwd}, mspd={mspd}, mult={mult}, delta={delta}, addoff={addoff}")

# Connect: ForwardVector.ReturnValue -> Multiply.A, MoveSpeed -> Multiply.B
connect(bp, fwd, "ReturnValue", mult, "A")
connect(bp, mspd, "MoveSpeed", mult, "B")
# Connect: Tick.then -> AddActorWorldOffset.execute
connect(bp, tick, "then", addoff, "execute")
# Connect: Multiply.ReturnValue -> AddActorWorldOffset.DeltaLocation
connect(bp, mult, "ReturnValue", addoff, "DeltaLocation")
compile(bp)

# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BUILD 2: BP_WarDrone — moves toward player on Tick")
print("="*60)
bp = "BP_WarDrone"

tick     = event(bp, "ReceiveTick", [0, 0])
getpawn  = func(bp, "GetPlayerPawn", "GameplayStatics", [300, 0], {"PlayerIndex": "0"})
ploc     = func(bp, "K2_GetActorLocation", "Actor", [500, -100])  # player location
sloc     = func(bp, "K2_GetActorLocation", "Actor", [500, 100], allow_duplicates=True)   # self location
sub      = func(bp, "Subtract_VectorVector", "KismetMathLibrary", [700, 0])
norm     = func(bp, "Normal", "KismetMathLibrary", [900, 0])
mspd     = varget(bp, "MoveSpeed", [900, 150])
mult     = func(bp, "Multiply_VectorFloat", "KismetMathLibrary", [1100, 0])
addoff   = func(bp, "K2_AddActorWorldOffset", "Actor", [1300, 0])

print(f"  tick={tick}, getpawn={getpawn}, ploc={ploc}, sloc={sloc}")
print(f"  sub={sub}, norm={norm}, mspd={mspd}, mult={mult}, addoff={addoff}")

# GetPlayerPawn feeds player-location node as target
connect(bp, getpawn, "ReturnValue", ploc, "self")
# Self (no target) feeds sloc — self location already defaults to self
# Subtract: player loc - self loc
connect(bp, ploc, "ReturnValue", sub, "A")
connect(bp, sloc, "ReturnValue", sub, "B")
# Normalize direction
connect(bp, sub, "ReturnValue", norm, "A")
# Scale by MoveSpeed
connect(bp, norm, "ReturnValue", mult, "A")
connect(bp, mspd, "MoveSpeed", mult, "B")
# Move
connect(bp, tick, "then", addoff, "execute")
connect(bp, mult, "ReturnValue", addoff, "DeltaLocation")
compile(bp)

# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BUILD 3: BP_DefenseLaser — sphere trace between 2 points, print SECURITY BREACH")
print("="*60)
bp = "BP_DefenseLaser"

# On Tick: sphere trace from SourcePointA to SourcePointB
# If anything hits player → print "SECURITY BREACH."
tick  = event(bp, "ReceiveTick", [0, 0])
getA  = get_component(bp, "SourcePointA", [300, 0])
getB  = get_component(bp, "SourcePointB", [300, 150])
locA  = func(bp, "K2_GetComponentLocation", "SceneComponent", [550, 0])
locB  = func(bp, "K2_GetComponentLocation", "SceneComponent", [550, 150])
trace = func(bp, "SphereTraceSingle", "SystemLibrary", [800, 0], {
    "Radius": "20.0",
    "TraceChannel": "ECC_Pawn",
    "bTraceComplex": "false"
})
brn   = branch(bp, [1100, 0])
pstr  = print_string(bp, "SECURITY BREACH.", [1350, 0])

print(f"  tick={tick}, getA={getA}, getB={getB}, locA={locA}, locB={locB}")
print(f"  trace={trace}, brn={brn}, pstr={pstr}")

connect(bp, getA, "ReturnValue", locA, "self")
connect(bp, getB, "ReturnValue", locB, "self")
connect(bp, locA, "ReturnValue", trace, "Start")
connect(bp, locB, "ReturnValue", trace, "End")
connect(bp, tick, "then", trace, "execute")
connect(bp, trace, "ReturnValue", brn, "Condition")
connect(bp, trace, "then", brn, "execute")
connect(bp, brn, "true", pstr, "execute")
compile(bp)

# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BUILD 4: BP_DroneFactory — overlap with player prints 'Activate Drone Factory'")
print("="*60)
bp = "BP_DroneFactory"

# Use ComponentBeginOverlap on InteractRadius
ovlp  = event(bp, "ComponentBeginOverlap", [0, 0])
cast  = func(bp, "CastToCharacter", "", [300, 0])
pstr  = print_string(bp, "Activate Drone Factory", [600, 0])

print(f"  ovlp={ovlp}, cast={cast}, pstr={pstr}")

connect(bp, ovlp, "then", cast, "execute")
connect(bp, ovlp, "Other Actor", cast, "Object")
connect(bp, cast, "then", pstr, "execute")
compile(bp)

# ═══════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BUILD 5: BP_LaserTurret — track player rotation + fire every 0.5s")
print("="*60)
bp = "BP_LaserTurret"

# BeginPlay: SetTimerByFunctionName "FireLaser" looping 0.5s
bplay   = event(bp, "ReceiveBeginPlay", [0, 0])
timer   = func(bp, "K2_SetTimerByFunctionName", "Actor", [300, 0], {
    "FunctionName": "FireLaser",
    "Time": "0.5",
    "bLooping": "true"
})

# Tick: Get player location, compute look-at rotation, set actor rotation
tick    = event(bp, "ReceiveTick", [0, 1000])
gplayer = func(bp, "GetPlayerPawn", "GameplayStatics", [300, 1000], {"PlayerIndex": "0"})
ploc    = func(bp, "K2_GetActorLocation", "Actor", [500, 900])
sloc    = func(bp, "K2_GetActorLocation", "Actor", [500, 1100])
lookat  = func(bp, "FindLookAtRotation", "KismetMathLibrary", [700, 1000])
setrot  = func(bp, "K2_SetActorRotation", "Actor", [950, 1000])

print(f"  bplay={bplay}, timer={timer}, tick={tick}")
print(f"  gplayer={gplayer}, ploc={ploc}, sloc={sloc}, lookat={lookat}, setrot={setrot}")

connect(bp, bplay, "then", timer, "execute")
connect(bp, gplayer, "ReturnValue", ploc, "self")
connect(bp, tick, "then", setrot, "execute")
connect(bp, sloc, "ReturnValue", lookat, "Start")
connect(bp, ploc, "ReturnValue", lookat, "Target")
connect(bp, lookat, "ReturnValue", setrot, "NewRotation")
compile(bp)

print("\n" + "="*60)
print("ALL BLUEPRINTS BUILT")
print("="*60)
