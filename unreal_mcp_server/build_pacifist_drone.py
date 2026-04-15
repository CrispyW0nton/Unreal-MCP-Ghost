import sys
sys.path.insert(0, '/home/user/webapp')
from mcp_client import _send_sync
import json

def mcp(cmd, params):
    r = _send_sync(cmd, params)
    return r

# Use exec_python to write the full blueprint logic
code = '''
import unreal

# Get the blueprint
bp_path = "/Game/Blueprints/BP_PacifistDrone"
bp = unreal.load_asset(bp_path)
if not bp:
    print("ERROR: Could not load BP_PacifistDrone")
else:
    # Get the generated class and CDO
    gen_class = bp.generated_class()
    print(f"Loaded BP_PacifistDrone: {bp}")

    # Use EditorScriptingUtilities to set up the blueprint graph
    lib = unreal.KismetSystemLibrary
    
    # Get blueprint function library
    bfl = unreal.BlueprintEditorLibrary
    
    # We need to use unreal.EditorAssetLibrary and graph manipulation
    # Get the event graph
    graphs = unreal.BlueprintEditorLibrary.get_blueprint_event_graphs(bp)
    event_graph = None
    for g in graphs:
        if g.get_name() == "EventGraph":
            event_graph = g
            break
    
    if not event_graph:
        print("ERROR: No EventGraph found")
    else:
        print(f"Found EventGraph: {event_graph}")
        
        # Get existing nodes
        nodes = event_graph.nodes
        print(f"Existing nodes: {len(nodes)}")
        for n in nodes:
            print(f"  Node: {n.get_name()} - {n.__class__.__name__}")
        
        # Find the EventTick node
        tick_node = None
        for n in nodes:
            if "EventTick" in n.get_name() or "Event_Tick" in n.get_name():
                tick_node = n
                break
            if hasattr(n, 'get_function_name'):
                fname = str(n.get_function_name())
                if "Tick" in fname:
                    tick_node = n
                    break
        
        if not tick_node:
            print("No tick node found, checking all nodes more carefully...")
            for n in nodes:
                print(f"  Checking: {n.get_name()} type={type(n).__name__}")
        
        print("Script completed successfully")
        unreal.EditorAssetLibrary.save_asset(bp_path)
'''

result = mcp("exec_python", {"code": code})
print("Result:", json.dumps(result, indent=2))
