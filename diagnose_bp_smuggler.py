# exec_python diagnostic script for BP_Smuggler
# Run this FIRST to see the current state of all nodes in BP_Smuggler's event graph.
# This helps diagnose what's broken before the fix script runs.

import unreal

# Try both common paths
CANDIDATE_PATHS = [
    '/Game/Blueprints/BP_Smuggler',
    '/Game/Dantooine/Blueprints/NPC/BP_Smuggler',
    '/Game/Dantooine/Blueprints/Characters/BP_Smuggler',
    '/Game/Characters/BP_Smuggler',
]

bp = None
bp_path = None
for path in CANDIDATE_PATHS:
    candidate = unreal.EditorAssetLibrary.load_asset(path)
    if candidate is not None:
        bp = candidate
        bp_path = path
        break

if bp is None:
    # Try to find it by listing assets
    print('BP_Smuggler not found at default paths. Searching...')
    assets = unreal.EditorAssetLibrary.list_assets('/Game', recursive=True, include_folder=False)
    for a in assets:
        if 'BP_Smuggler' in a or 'Smuggler' in a:
            print('  Found:', a)
    print('Please check the path above and update fix_smuggler_bound_events.py')
else:
    print(f'Found BP_Smuggler at: {bp_path}')
    print(f'  Class: {bp.get_class().get_name()}')

    try:
        graphs = unreal.BlueprintEditorLibrary.get_blueprint_event_graphs(bp)
    except Exception:
        graphs = bp.get_editor_property('uber_graph_pages') or []

    print(f'  Event graphs: {len(graphs)}')

    for graph in graphs:
        try:
            nodes = graph.get_all_nodes()
        except Exception as e:
            print(f'  Graph {graph.get_name()}: cannot read nodes: {e}')
            continue

        print(f'\n  Graph "{graph.get_name()}" — {len(nodes)} node(s):')
        for node in nodes:
            cls = node.get_class().get_name()
            try:
                title = str(node.get_node_title(unreal.NodeTitleType.FULL_TITLE))
            except Exception:
                title = '(no title)'

            if cls == 'K2Node_ComponentBoundEvent':
                try:
                    cpn = str(node.get_editor_property('component_property_name'))
                    dpn = str(node.get_editor_property('delegate_property_name'))
                except Exception as e:
                    cpn = f'(error: {e})'
                    dpn = '?'
                status = '⚠️  BROKEN' if '_GEN_VARIABLE' in cpn else '✅  OK'
                print(f'    [{status}] {cls}: ComponentPropertyName="{cpn}"  DelegatePropertyName="{dpn}"')
            else:
                print(f'    {cls}: {title}')
