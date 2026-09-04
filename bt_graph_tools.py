"""
BT Graph Tools - Python client wrappers for the new BT graph manipulation commands.
These use the newly-added C++ handlers: HandleBuildBehaviorTree, HandleAddBTNode, HandleGetBTGraphInfo.

New commands added to the UnrealMCP plugin:
  - build_behavior_tree  : populate a full BT from a JSON tree description
  - add_bt_node          : add a single node to a BT graph
  - get_bt_graph_info    : inspect current BT graph
"""
import sys
sys.path.insert(0, '/home/user/webapp')
import ue5_client as ue

def get_bt_graph_info(bt_name):
    """Get info about a BT asset's graph nodes and connections."""
    r = ue.send_cmd('get_bt_graph_info', {'behavior_tree_name': bt_name})
    return r

def add_bt_node(bt_name, node_type, parent_index=-1, x=None, y=None,
                properties=None, decorators=None, services=None):
    """
    Add a single node to a BT graph.
    
    Args:
        bt_name:       Name of the BehaviorTree asset
        node_type:     'Selector', 'Sequence', 'Wait', 'MoveTo', or class path
        parent_index:  Index in non-root node list (-1 = attach to root)
        x, y:          Position (optional)
        properties:    dict of property name -> value string (optional)
        decorators:    list of {'type': 'ClassName'} (optional)
        services:      list of {'type': 'ClassName'} (optional)
    """
    params = {
        'behavior_tree_name': bt_name,
        'node_type': node_type,
        'parent_node_index': parent_index,
    }
    if x is not None: params['x'] = x
    if y is not None: params['y'] = y
    if properties: params['properties'] = properties
    if decorators: params['decorators'] = decorators
    if services: params['services'] = services
    
    r = ue.send_cmd('add_bt_node', params)
    return r

def build_behavior_tree(bt_name, tree_json, clear_existing=True):
    """
    Build a complete behavior tree from a JSON tree description.
    
    The tree_json describes a single root composite node (Selector/Sequence)
    with optional children, decorators, and services.
    
    Example tree_json:
    {
        "type": "Selector",
        "x": 0,
        "y": 200,
        "children": [
            {
                "type": "Sequence",
                "x": -200,
                "y": 400,
                "decorators": [{"type": "BTDecorator_Blackboard"}],
                "children": [
                    {"type": "BTTask_MoveTo", "x": -300, "y": 600},
                    {"type": "BTTask_Wait",   "x": -100, "y": 600,
                     "properties": {"WaitTime": "2.0"}}
                ]
            },
            {
                "type": "BTTask_Wait",
                "x": 200,
                "y": 400,
                "properties": {"WaitTime": "0.5"}
            }
        ]
    }
    """
    params = {
        'behavior_tree_name': bt_name,
        'tree': tree_json,
        'clear_existing': clear_existing,
    }
    r = ue.send_cmd('build_behavior_tree', params)
    return r


# ── Example: Patrol + Chase BT ───────────────────────────────────────────────

PATROL_CHASE_TREE = {
    "type": "Selector",
    "x": 0,
    "y": 200,
    "children": [
        # Branch 1: Chase if enemy is seen
        {
            "type": "Sequence",
            "x": -300,
            "y": 400,
            "decorators": [
                {
                    "type": "BTDecorator_Blackboard",
                }
            ],
            "children": [
                {
                    "type": "BTTask_MoveTo",
                    "x": -300,
                    "y": 600,
                }
            ]
        },
        # Branch 2: Patrol (wander)
        {
            "type": "Sequence",
            "x": 300,
            "y": 400,
            "children": [
                {
                    "type": "BTTask_MoveTo",
                    "x": 200,
                    "y": 600,
                },
                {
                    "type": "BTTask_Wait",
                    "x": 400,
                    "y": 600,
                    "properties": {"WaitTime": "2.0"}
                }
            ]
        }
    ]
}


if __name__ == '__main__':
    import json
    
    # Test: inspect current BT
    print("=== Get BT Graph Info ===")
    r = get_bt_graph_info('BT_Enemy_Infantry')
    print(json.dumps(r, indent=2))
    
    print("\n=== Build Patrol+Chase BT ===")
    r2 = build_behavior_tree('BT_Enemy_Infantry', PATROL_CHASE_TREE)
    print(json.dumps(r2, indent=2))
