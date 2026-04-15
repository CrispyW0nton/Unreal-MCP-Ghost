# exec_python fix script — run this block in the exec_python tool
# Fixes K2Node_ComponentBoundEvent nodes in BP_Smuggler that have the
# "_GEN_VARIABLE" suffix in ComponentPropertyName, which causes a
# "CopyInternal compiler error inside CreateExecutionSchedule" ICE.
#
# Usage via MCP exec_python tool:
#   paste the entire contents of this file as the `code` parameter.

import unreal

BLUEPRINT_PATH = '/Game/Blueprints/BP_Smuggler'

# Map of broken suffix -> correct bare SCS variable name
CORRECTIONS = {
    'InteractionSphere_GEN_VARIABLE': 'InteractionSphere',
    'ShootingZone_GEN_VARIABLE':      'ShootingZone',
}

# ── 1. Load the blueprint ──────────────────────────────────────────────────────
bp = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
if bp is None:
    print('ERROR: Could not load', BLUEPRINT_PATH)
    raise SystemExit(1)

print('Loaded blueprint:', bp.get_name())

# ── 2. Collect all graphs ──────────────────────────────────────────────────────
# Try BlueprintEditorLibrary first; fall back to get_editor_property
try:
    graphs = unreal.BlueprintEditorLibrary.get_blueprint_event_graphs(bp)
except Exception as e:
    print(f'BlueprintEditorLibrary.get_blueprint_event_graphs failed ({e}), using fallback')
    graphs = bp.get_editor_property('uber_graph_pages') or []

print(f'Found {len(graphs)} event graph(s)')

# ── 3. Walk nodes and apply corrections ───────────────────────────────────────
fixed = 0
for graph in graphs:
    # get_all_nodes() is the UE Python method on UEdGraph
    try:
        nodes = graph.get_all_nodes()
    except Exception as e:
        print(f'  graph.get_all_nodes() failed ({e}) — skipping graph {graph.get_name()}')
        continue

    print(f'  Graph "{graph.get_name()}": {len(nodes)} node(s)')

    for node in nodes:
        cls_name = node.get_class().get_name()
        if cls_name != 'K2Node_ComponentBoundEvent':
            continue

        # Read the current ComponentPropertyName
        try:
            prop_name_obj = node.get_editor_property('component_property_name')
            prop_str = str(prop_name_obj)
        except Exception as e:
            print(f'    Could not read component_property_name on {node.get_name()}: {e}')
            continue

        print(f'    K2Node_ComponentBoundEvent "{node.get_name()}": ComponentPropertyName="{prop_str}"')

        if prop_str in CORRECTIONS:
            correct = CORRECTIONS[prop_str]
            try:
                node.set_editor_property('component_property_name', unreal.Name(correct))
                # Verify the write
                verify = str(node.get_editor_property('component_property_name'))
                if verify == correct:
                    print(f'      FIXED: "{prop_str}" -> "{correct}" (verified)')
                    fixed += 1
                else:
                    print(f'      WARNING: set_editor_property wrote but readback="{verify}" (expected "{correct}")')
            except Exception as e:
                print(f'      ERROR setting property: {e}')
        else:
            print(f'      OK (no correction needed)')

# ── 4. Recompile and save if any fixes were applied ───────────────────────────
if fixed > 0:
    print(f'\nFixed {fixed} node(s). Recompiling blueprint...')
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        print('Compile complete.')
    except Exception as e:
        print(f'compile_blueprint error: {e}')

    print('Saving...')
    try:
        unreal.EditorAssetLibrary.save_asset(BLUEPRINT_PATH, only_if_is_dirty=False)
        print('Saved.')
    except Exception as e:
        print(f'save_asset error: {e}')
        # Fallback save
        try:
            pkg = bp.get_outer()
            unreal.EditorLoadingAndSavingUtils.save_packages_with_dialog([pkg], only_dirty=False)
            print('Saved via fallback method.')
        except Exception as e2:
            print(f'Fallback save also failed: {e2}')

    print(f'\nDone. {fixed} K2Node_ComponentBoundEvent node(s) corrected and saved.')
else:
    print('\nNo nodes needed correction. BP_Smuggler ComponentPropertyName fields are already correct.')
    print('If the ICE compile error persists, try:')
    print('  1. Open BP_Smuggler in the Blueprint editor')
    print('  2. Delete all K2Node_ComponentBoundEvent nodes')
    print('  3. Re-add them via the Components panel')
