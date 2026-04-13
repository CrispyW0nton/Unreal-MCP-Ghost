# exec_python fix script — paste this entire block into the exec_python tool
# Fixes K2Node_ComponentBoundEvent nodes that have _GEN_VARIABLE suffix
# in ComponentPropertyName, causing ICE compile errors in BP_Smuggler.

import unreal

BLUEPRINT_PATH = '/Game/Blueprints/BP_Smuggler'

# Map of broken name -> correct bare SCS variable name
CORRECTIONS = {
    'InteractionSphere_GEN_VARIABLE': 'InteractionSphere',
    'ShootingZone_GEN_VARIABLE':      'ShootingZone',
    # Also catch any case where it was stored without suffix but wrong
}

bp = unreal.EditorAssetLibrary.load_asset(BLUEPRINT_PATH)
if bp is None:
    print('ERROR: Could not load', BLUEPRINT_PATH)
else:
    fixed = 0
    graphs = unreal.BlueprintEditorLibrary.get_blueprint_event_graphs(bp)
    for graph in graphs:
        for node in graph.get_all_nodes():
            cls_name = node.get_class().get_name()
            if cls_name != 'K2Node_ComponentBoundEvent':
                continue
            prop_name = node.get_editor_property('component_property_name')
            # prop_name is an unreal.Name; convert to str for comparison
            prop_str = str(prop_name)
            if prop_str in CORRECTIONS:
                correct = CORRECTIONS[prop_str]
                node.set_editor_property('component_property_name', unreal.Name(correct))
                print(f'Fixed node {node.get_name()}: {prop_str} -> {correct}')
                fixed += 1
            else:
                print(f'Node {node.get_name()} ComponentPropertyName={prop_str} (OK or unknown)')

    if fixed > 0:
        # Mark dirty and recompile
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        unreal.EditorAssetLibrary.save_asset(BLUEPRINT_PATH)
        print(f'Done. Fixed {fixed} node(s), compiled and saved.')
    else:
        print('No nodes needed fixing (all ComponentPropertyNames already correct).')
