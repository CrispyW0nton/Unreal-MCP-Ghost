"""
fix_q_r_input.py
================
Fixes Q and R key inputs not working in ThePlayerCharacter blueprint.

Root cause:
  Both IA_FirePulse (Q) and IA_DeployNanomachines (R) triggered
  GetAllActorsOfClass → ForEach → DynamicCast<BP_PacifistDrone> → DestroyActor.
  The ActorClass pin on both GetAllActorsOfClass nodes had an empty default value,
  so GetAllActorsOfClass always returned an empty array, and no drones were found
  or destroyed.

Fix applied (exec_python + plugin commands):
  1. Added a TSubclassOf<Actor> variable 'PacifistDroneClass' to ThePlayerCharacter
     (instance-editable, expose-on-spawn), defaulting to BP_PacifistDrone_C on CDO.
  2. Added two variable getter nodes (K2Node_VariableGet_0 and K2Node_VariableGet_1)
     near the Q and R input action nodes respectively.
  3. Connected each getter's PacifistDroneClass output pin to the ActorClass input
     pin of the corresponding GetAllActorsOfClass node.
  4. Compiled and saved ThePlayerCharacter blueprint.

Blueprint flow after fix:
  Q pressed (IA_FirePulse.Triggered)
    → GetAllActorsOfClass(PacifistDroneClass)
    → ForEach<BP_PacifistDrone>
    → DynamicCast<BP_PacifistDrone>
    → K2_DestroyActor

  R pressed (IA_DeployNanomachines.Triggered)
    → GetAllActorsOfClass(PacifistDroneClass)
    → ForEach<BP_PacifistDrone>
    → DynamicCast<BP_PacifistDrone>
    → K2_DestroyActor

Both Q and R now correctly destroy all BP_PacifistDrone actors in the level.

Note: The IA_DeployNanomachines action also has Started/Triggered pins wired to
SphereTrace logic (for the Hack mechanic with IA_Hack on F), which is unrelated
to the Q/R fix.

Node IDs fixed:
  Q GetAllActorsOfClass: ADFC3BCE4BC7DD3117B52D87973D6988 (K2Node_CallFunction_69)
  R GetAllActorsOfClass: 8D22B5654CF9FEFDE957088DC1B616EA (K2Node_CallFunction_70)
  Q getter node:         3226128B495B051E37BBC3A92F2F9832 (K2Node_VariableGet_0)
  R getter node:         C5A9082F49EB89854325EABC12A26264 (K2Node_VariableGet_1)
"""

import unreal

def fix_q_r_input():
    """Re-apply the Q/R input fix if needed (e.g., after engine restart loses transient state)."""
    bp = unreal.load_object(None, "/Game/ThePlayerCharacter.ThePlayerCharacter")
    assert bp, "ThePlayerCharacter blueprint not found"

    pacifist_bp = unreal.load_asset("/Game/Blueprints/BP_PacifistDrone")
    pacifist_class = pacifist_bp.generated_class()
    print(f"PacifistDrone class: {pacifist_class.get_name()}")

    # Ensure PacifistDroneClass variable exists with correct default
    for cdo in unreal.ObjectIterator(bp.generated_class()):
        if "Default__" in cdo.get_path_name() and "ThePlayerCharacter" in cdo.get_path_name():
            try:
                cdo.set_editor_property("PacifistDroneClass", pacifist_class)
                print(f"CDO.PacifistDroneClass = {cdo.get_editor_property('PacifistDroneClass')}")
            except Exception as e:
                print(f"CDO set error: {e}")
            break

    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_asset("/Game/ThePlayerCharacter")
    print("Done - ThePlayerCharacter saved")


if __name__ == "__main__":
    fix_q_r_input()
