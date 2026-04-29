"""
Animation Tools - Animation Blueprints, State Machines, Blend Spaces,
IK Rig creation, and IK Retargeter (animation retargeting) tools.

IK Rig / Retargeter tools use exec_python to call the UE5 Python API
(unreal.IKRigController, unreal.IKRetargeterController) because those
classes live in the IKRigEditor module and are not exposed via the MCP
C++ bridge.
"""
import logging
import textwrap
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def _send(command: str, params: dict) -> Dict[str, Any]:
    from unreal_mcp_server import get_unreal_connection
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = unreal.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as e:
        logger.error(f"Error in {command}: {e}")
        return {"success": False, "message": str(e)}


def _exec(code: str) -> Dict[str, Any]:
    """Run Python inside UE5 via exec_python command (tier-3 timeout)."""
    from unreal_mcp_server import get_unreal_connection
    import traceback as _tb
    try:
        compile(code, "<mcp_exec>", "exec")
    except SyntaxError as syn_e:
        return {"success": False, "error": f"SyntaxError: {syn_e}",
                "output": f"SyntaxError: {syn_e}\n{_tb.format_exc()}"}
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        response = unreal.send_command("exec_python", {"code": code}) or {}
        if "output" not in response and "result" in response:
            response["output"] = response["result"]
        if "success" not in response:
            response["success"] = response.get("status") != "error"
        return response
    except Exception as e:
        logger.error(f"exec_python error: {e}")
        return {"success": False, "message": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers shared by both the individual tools and the pipeline tool.
# These are plain functions (not MCP tools) so they can be called from Python.
# ─────────────────────────────────────────────────────────────────────────────

def _create_ik_rig(
    ik_rig_name: str,
    skeletal_mesh_path: str,
    path: str,
    auto_generate_chains: bool
) -> Dict[str, Any]:
    """Internal: create an IKRig asset. Returns {success, asset_path, message}."""
    auto_gen_str = "True" if auto_generate_chains else "False"
    code = textwrap.dedent(f"""\
import unreal

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
pkg_path = "{path}/{ik_rig_name}"

existing = unreal.EditorAssetLibrary.does_asset_exist(pkg_path)
if existing:
    print("ALREADY_EXISTS: " + pkg_path)
else:
    factory = unreal.IKRigDefinitionFactory()
    ik_rig_asset = asset_tools.create_asset(
        "{ik_rig_name}", "{path}", unreal.IKRigDefinition, factory
    )
    if ik_rig_asset is None:
        print("ERROR: Failed to create IKRigDefinition asset at " + pkg_path)
    else:
        ctrl = unreal.IKRigController.get_controller(ik_rig_asset)
        skel_mesh = unreal.load_asset("{skeletal_mesh_path}")
        if skel_mesh is None:
            print("ERROR: Skeletal mesh not found: {skeletal_mesh_path}")
        else:
            ctrl.set_skeletal_mesh(skel_mesh)
            if {auto_gen_str}:
                ctrl.apply_auto_generated_retarget_definition()
            unreal.EditorAssetLibrary.save_asset(pkg_path)
            print("OK: IKRig created at " + pkg_path)
""")
    result = _exec(code)
    output = result.get("output", "")
    asset_path = f"{path}/{ik_rig_name}"
    if "ALREADY_EXISTS:" in output:
        return {"success": True, "asset_path": asset_path,
                "message": f"IKRig already exists: {asset_path}"}
    if "ERROR" in output:
        return {"success": False, "asset_path": asset_path, "message": output.strip()}
    return {"success": result.get("success", False),
            "asset_path": asset_path,
            "message": output.strip() or "IKRig created"}


def _create_ik_retargeter(
    retargeter_name: str,
    source_ik_rig_path: str,
    target_ik_rig_path: str,
    path: str,
    auto_map_chains: bool,
    auto_align_bones: bool
) -> Dict[str, Any]:
    """Internal: create an IKRetargeter asset. Returns {success, asset_path, message}."""
    auto_map_str   = "True" if auto_map_chains   else "False"
    auto_align_str = "True" if auto_align_bones  else "False"
    code = textwrap.dedent(f"""\
import unreal

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
pkg_path = "{path}/{retargeter_name}"

existing = unreal.EditorAssetLibrary.does_asset_exist(pkg_path)
if existing:
    print("ALREADY_EXISTS: " + pkg_path)
else:
    source_rig = unreal.load_asset("{source_ik_rig_path}")
    target_rig = unreal.load_asset("{target_ik_rig_path}")
    if source_rig is None:
        print("ERROR: Source IKRig not found: {source_ik_rig_path}")
    elif target_rig is None:
        print("ERROR: Target IKRig not found: {target_ik_rig_path}")
    else:
        factory = unreal.IKRetargeterFactory()
        rtg_asset = asset_tools.create_asset(
            "{retargeter_name}", "{path}", unreal.IKRetargeter, factory
        )
        if rtg_asset is None:
            print("ERROR: Failed to create IKRetargeter at " + pkg_path)
        else:
            ctrl = unreal.IKRetargeterController.get_controller(rtg_asset)
            ctrl.assign_ik_rig_to_all_ops(source_rig)
            ops = ctrl.get_num_retarget_ops()
            if ops > 0:
                op_ctrl = ctrl.get_op_controller(0)
                if op_ctrl:
                    op_ctrl.set_ik_rig(target_rig)
            if {auto_map_str}:
                ctrl.auto_map_chains()
            if {auto_align_str}:
                ctrl.auto_align_all_bones()
            unreal.EditorAssetLibrary.save_asset(pkg_path)
            print("OK: IKRetargeter created at " + pkg_path)
""")
    result = _exec(code)
    output = result.get("output", "")
    asset_path = f"{path}/{retargeter_name}"
    if "ALREADY_EXISTS:" in output:
        return {"success": True, "asset_path": asset_path,
                "message": f"IKRetargeter already exists: {asset_path}"}
    if "ERROR" in output:
        return {"success": False, "asset_path": asset_path, "message": output.strip()}
    return {"success": result.get("success", False),
            "asset_path": asset_path,
            "message": output.strip() or "IKRetargeter created"}


def _batch_retarget_animations(
    retargeter_path: str,
    source_animation_paths: List[str],
    output_path: str,
    output_suffix: str,
    use_existing_if_found: bool
) -> Dict[str, Any]:
    """Internal: batch-retarget animations. Returns summary dict."""
    paths_repr = repr(source_animation_paths)
    code = textwrap.dedent(f"""\
import unreal

retargeter = unreal.load_asset("{retargeter_path}")
if retargeter is None:
    print("ERROR: IKRetargeter not found: {retargeter_path}")
else:
    source_paths = {paths_repr}
    output_path  = "{output_path}"
    suffix       = "{output_suffix}"
    skip_exist   = {str(use_existing_if_found)}

    retargeted = 0
    skipped    = 0
    failed     = 0

    for src_path in source_paths:
        anim_asset = unreal.load_asset(src_path)
        if anim_asset is None:
            print("FAIL: Animation not found: " + src_path)
            failed += 1
            continue

        asset_name   = src_path.split("/")[-1] + suffix
        out_pkg_path = output_path + "/" + asset_name

        if skip_exist and unreal.EditorAssetLibrary.does_asset_exist(out_pkg_path):
            print("SKIP: " + out_pkg_path)
            skipped += 1
            continue

        exported = None
        if hasattr(unreal, "IKRetargetEditorController"):
            try:
                opts = unreal.AnimationRetargetingOptions()
                exported = unreal.IKRetargetEditorController.export_animations_from_assets(
                    [anim_asset], retargeter, out_pkg_path, opts
                )
            except Exception as e1:
                print("WARN IKRetargetEditorController: " + str(e1))

        if exported is None and hasattr(unreal, "IKRetargetingUtils"):
            try:
                exported = unreal.IKRetargetingUtils.retarget_animation_sequence(
                    retargeter, anim_asset, out_pkg_path
                )
            except Exception as e2:
                print("WARN IKRetargetingUtils: " + str(e2))

        if exported is None:
            try:
                asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                asset_tools.retarget_animation_assets(
                    [anim_asset], output_path, suffix, retargeter
                )
                exported = unreal.load_asset(out_pkg_path)
            except Exception as e3:
                print("FAIL AssetTools: " + src_path + " - " + str(e3))

        if exported:
            unreal.EditorAssetLibrary.save_asset(out_pkg_path)
            print("OK: " + src_path + " -> " + out_pkg_path)
            retargeted += 1
        else:
            print("FAIL: " + src_path + " export returned None")
            failed += 1

    print("SUMMARY retargeted=" + str(retargeted) + " skipped=" + str(skipped) + " failed=" + str(failed))
""")
    result = _exec(code)
    output = result.get("output", "")
    if "ERROR: IKRetargeter" in output:
        return {"success": False, "retargeted": 0, "skipped": 0, "failed": 0,
                "message": output.strip()}

    retargeted = skipped = failed = 0
    for line in output.splitlines():
        if line.startswith("SUMMARY"):
            try:
                parts = {k: int(v) for k, v in
                         (p.split("=") for p in line.split()[1:])}
                retargeted = parts.get("retargeted", 0)
                skipped    = parts.get("skipped",    0)
                failed     = parts.get("failed",     0)
            except Exception:
                pass

    return {
        "success": result.get("success", False) and failed == 0,
        "retargeted": retargeted,
        "skipped":    skipped,
        "failed":     failed,
        "output":     output,
    }


# ─────────────────────────────────────────────────────────────────────────────


def register_animation_tools(mcp: FastMCP):

    @mcp.tool()
    def create_animation_blueprint(
        ctx: Context,
        name: str,
        skeleton: str = "",
        parent_class: str = "AnimInstance",
        path: str = "/Game/Animations"
    ) -> Dict[str, Any]:
        """
        Create an Animation Blueprint (AnimBP).

        Animation Blueprints control skeletal mesh animations using an
        EventGraph (for logic) and AnimGraph (for pose blending).

        Args:
            name: AnimBP name (e.g., "ABP_Character")
            skeleton: Skeleton asset path (e.g., "/Game/Characters/SK_Character")
            parent_class: Parent class (default: "AnimInstance")
            path: Content browser path
        """
        return _send("create_animation_blueprint", {
            "name": name,
            "skeleton": skeleton,
            "parent_class": parent_class,
            "path": path
        })

    @mcp.tool()
    def add_state_machine(
        ctx: Context,
        anim_blueprint_name: str,
        state_machine_name: str = "MainStateMachine"
    ) -> Dict[str, Any]:
        """
        Add a State Machine to an Animation Blueprint's AnimGraph.

        State Machines define animation states (Idle, Walk, Run, Jump)
        and transitions between them.

        Args:
            anim_blueprint_name: Animation Blueprint name
            state_machine_name: Name for the state machine node
        """
        return _send("add_state_machine", {
            "anim_blueprint_name": anim_blueprint_name,
            "state_machine_name": state_machine_name
        })

    @mcp.tool()
    def add_animation_state(
        ctx: Context,
        anim_blueprint_name: str,
        state_machine_name: str,
        state_name: str,
        animation_asset: str = ""
    ) -> Dict[str, Any]:
        """
        Add an animation state to a State Machine.

        Args:
            anim_blueprint_name: Animation Blueprint name
            state_machine_name: State machine name
            state_name: State name (e.g., "Idle", "Walk", "Run", "Jump", "Death")
            animation_asset: Optional animation sequence asset path
        """
        return _send("add_animation_state", {
            "anim_blueprint_name": anim_blueprint_name,
            "state_machine_name": state_machine_name,
            "state_name": state_name,
            "animation_asset": animation_asset
        })

    @mcp.tool()
    def add_state_transition(
        ctx: Context,
        anim_blueprint_name: str,
        state_machine_name: str,
        from_state: str,
        to_state: str,
        condition_variable: str = "",
        condition_value: bool = True
    ) -> Dict[str, Any]:
        """
        Add a transition between two animation states.

        Args:
            anim_blueprint_name: Animation Blueprint name
            state_machine_name: State machine name
            from_state: Source state name
            to_state: Destination state name
            condition_variable: Bool variable to use as transition condition
            condition_value: Expected value to trigger transition (True/False)
        """
        return _send("add_state_transition", {
            "anim_blueprint_name": anim_blueprint_name,
            "state_machine_name": state_machine_name,
            "from_state": from_state,
            "to_state": to_state,
            "condition_variable": condition_variable,
            "condition_value": condition_value
        })

    @mcp.tool()
    def set_animation_for_state(
        ctx: Context,
        anim_blueprint_name: str,
        state_machine_name: str,
        state_name: str,
        animation_asset: str,
        loop: bool = True
    ) -> Dict[str, Any]:
        """
        Assign an animation sequence to a State Machine state.

        Args:
            anim_blueprint_name: Animation Blueprint name
            state_machine_name: State machine name
            state_name: State to assign animation to
            animation_asset: Animation Sequence asset path
            loop: Loop the animation
        """
        return _send("set_animation_for_state", {
            "anim_blueprint_name": anim_blueprint_name,
            "state_machine_name": state_machine_name,
            "state_name": state_name,
            "animation_asset": animation_asset,
            "loop": loop
        })

    @mcp.tool()
    def add_anim_blueprint_variable(
        ctx: Context,
        anim_blueprint_name: str,
        variable_name: str,
        variable_type: str,
        default_value: str = ""
    ) -> Dict[str, Any]:
        """
        Add a variable to an Animation Blueprint (for use in transitions/logic).

        Args:
            anim_blueprint_name: Animation Blueprint name
            variable_name: Variable name (e.g., "Speed", "bIsJumping", "Direction")
            variable_type: Type (Boolean, Float, Integer, Vector)
            default_value: Optional default value
        """
        return _send("add_blueprint_variable", {
            "blueprint_name": anim_blueprint_name,
            "variable_name": variable_name,
            "variable_type": variable_type,
            "is_exposed": False,
            "default_value": default_value
        })

    @mcp.tool()
    def add_blend_space_node(
        ctx: Context,
        anim_blueprint_name: str,
        blend_space_asset: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Blend Space node to an Animation Blueprint's AnimGraph.

        Blend Spaces blend animations based on one or two float parameters
        (e.g., Speed and Direction for a locomotion blend space).

        Args:
            anim_blueprint_name: Animation Blueprint name
            blend_space_asset: Blend Space asset path
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blend_space_node", {
            "anim_blueprint_name": anim_blueprint_name,
            "blend_space_asset": blend_space_asset,
            "node_position": node_position
        })

    @mcp.tool()
    def insert_anim_graph_slot(
        ctx: Context,
        anim_blueprint_name: str,
        slot_name: str = "DefaultSlot",
        graph_name: str = ""
    ) -> Dict[str, Any]:
        """
        Insert a Slot node on the main AnimGraph between the current pose chain and Root.

        Use this so `PlaySlotAnimationAsDynamicMontage` / montages targeting the same
        slot name layer aim and fire animations over locomotion from the state machine.

        Args:
            anim_blueprint_name: AnimBP asset path or name (e.g. ABP_SithSoldier or full /Game/... path)
            slot_name: Anim slot name (default DefaultSlot — must match montage slot / blueprint calls)
            graph_name: Optional graph name; defaults to AnimGraph
        """
        params: Dict[str, Any] = {
            "anim_blueprint_name": anim_blueprint_name,
            "slot_name": slot_name,
        }
        if graph_name:
            params["graph_name"] = graph_name
        return _send("insert_anim_graph_slot", params)

    @mcp.tool()
    def insert_blend_bool_fire_before_slot(
        ctx: Context,
        anim_blueprint_name: str,
        sequence_asset: str,
        graph_name: str = "",
        swap_blend_pose_order: bool = False,
        bind_bool_variable: str = "bIsShooting",
        force_insert: bool = False,
    ) -> Dict[str, Any]:
        """
        Insert **Blend List By Bool** + **Sequence Player** between locomotion and the AnimGraph **Slot**
        (requires ``insert_anim_graph_slot`` first: Root ← Slot ← …).

        Locomotion feeds the **false** branch; ``sequence_asset`` (e.g. fire rifle) feeds the **true** branch.
        ``bind_bool_variable`` (default ``bIsShooting``) auto-binds Active Value when the editor plugin supports it.
        ``force_insert=True`` layers a NEW BlendListByBool above an existing one (chain multiple gates,
        e.g. bIsInAir → jump on top of bIsShooting → fire).  Default rebinds the existing node instead.
        """
        params: Dict[str, Any] = {
            "anim_blueprint_name": anim_blueprint_name,
            "sequence_asset": sequence_asset,
            "swap_blend_pose_order": swap_blend_pose_order,
            "bind_bool_variable": bind_bool_variable,
            "force_insert": force_insert,
        }
        if graph_name:
            params["graph_name"] = graph_name
        return _send("insert_blend_bool_fire_before_slot", params)

    @mcp.tool()
    def create_character_animation_setup(
        ctx: Context,
        anim_blueprint_name: str,
        skeleton: str = ""
    ) -> Dict[str, Any]:
        """
        Create a complete character Animation Blueprint with:
        - Speed and IsJumping variables
        - Idle, Walk, Run, and Jump states
        - Transitions based on Speed and jump state

        Args:
            anim_blueprint_name: Animation Blueprint name
            skeleton: Skeleton asset path

        Returns:
            Dict with creation results
        """
        results = {}

        # Create the Animation Blueprint
        results["create"] = _send("create_animation_blueprint", {
            "name": anim_blueprint_name,
            "skeleton": skeleton,
            "parent_class": "AnimInstance",
            "path": "/Game/Animations"
        })

        # Add variables
        for var_name, var_type in [("Speed", "Float"), ("bIsJumping", "Boolean"),
                                    ("bIsFalling", "Boolean"), ("Direction", "Float")]:
            results[f"var_{var_name}"] = _send("add_blueprint_variable", {
                "blueprint_name": anim_blueprint_name,
                "variable_name": var_name,
                "variable_type": var_type,
                "is_exposed": False
            })

        # Add State Machine
        results["state_machine"] = _send("add_state_machine", {
            "anim_blueprint_name": anim_blueprint_name,
            "state_machine_name": "LocomotionSM"
        })

        # Add States
        for state in ["Idle", "Walk", "Run", "Jump", "Fall"]:
            results[f"state_{state}"] = _send("add_animation_state", {
                "anim_blueprint_name": anim_blueprint_name,
                "state_machine_name": "LocomotionSM",
                "state_name": state
            })

        # Add Transitions
        transitions = [
            ("Idle", "Walk", "Speed", False),
            ("Walk", "Idle", "Speed", False),
            ("Walk", "Run", "Speed", False),
            ("Run", "Walk", "Speed", False),
        ]
        for from_s, to_s, cond, cond_val in transitions:
            results[f"trans_{from_s}_{to_s}"] = _send("add_state_transition", {
                "anim_blueprint_name": anim_blueprint_name,
                "state_machine_name": "LocomotionSM",
                "from_state": from_s,
                "to_state": to_s,
                "condition_variable": cond,
                "condition_value": cond_val
            })

        _send("compile_blueprint", {"blueprint_name": anim_blueprint_name})
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # IK RIG TOOLS
    # ─────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    def create_ik_rig(
        ctx: Context,
        ik_rig_name: str,
        skeletal_mesh_path: str,
        path: str = "/Game/Animation/IKRigs",
        auto_generate_chains: bool = True
    ) -> Dict[str, Any]:
        """
        Create an IK Rig asset for a Skeletal Mesh.

        IK Rigs define retarget chains (bone chains like Spine, LeftArm, RightLeg)
        and are required by the IK Retargeter.  This tool uses the UE5 Python API
        (unreal.IKRigController) via exec_python.

        Typical workflow:
          1. create_ik_rig for source skeleton  (e.g. Mannequin)
          2. create_ik_rig for target skeleton  (e.g. your custom character)
          3. create_ik_retargeter linking source → target
          4. batch_retarget_animations to export retargeted animations

        Args:
            ik_rig_name: Asset name, e.g. "IKR_Mannequin"
            skeletal_mesh_path: Full content path, e.g. "/Game/Characters/Mannequin/SK_Mannequin"
            path: Destination content-browser folder
            auto_generate_chains: If True, calls apply_auto_generated_retarget_definition
                                  to auto-detect spine / limb chains (recommended for
                                  humanoid skeletons).  Set False for custom chain setup.

        Returns:
            dict with keys: success, asset_path, message
        """
        return _create_ik_rig(ik_rig_name, skeletal_mesh_path, path, auto_generate_chains)

    @mcp.tool()
    def add_ik_rig_retarget_chain(
        ctx: Context,
        ik_rig_name: str,
        ik_rig_path: str,
        chain_name: str,
        start_bone: str,
        end_bone: str,
        ik_goal_name: str = ""
    ) -> Dict[str, Any]:
        """
        Add a named retarget chain to an existing IK Rig asset.

        Retarget chains map a contiguous range of bones (e.g. "Spine" from
        pelvis → chest, or "LeftArm" from shoulder → hand) so the IK Retargeter
        knows how to transfer motion from source to target.

        Call this after create_ik_rig when auto_generate_chains=False, or to add
        extra chains the auto-generator missed.

        Args:
            ik_rig_name: Asset name (e.g. "IKR_MyCharacter")
            ik_rig_path: Content folder (e.g. "/Game/Animation/IKRigs")
            chain_name: Logical name for the chain (e.g. "Spine", "LeftArm")
            start_bone: Root bone of the chain (e.g. "spine_01")
            end_bone: Leaf bone of the chain (e.g. "spine_05")
            ik_goal_name: Optional IK goal name to attach to the chain end bone

        Returns:
            dict with keys: success, chain_name, message
        """
        code = textwrap.dedent(f"""\
import unreal

pkg_path = "{ik_rig_path}/{ik_rig_name}"
ik_rig_asset = unreal.load_asset(pkg_path)
if ik_rig_asset is None:
    print("ERROR: IKRig not found: " + pkg_path)
else:
    ctrl = unreal.IKRigController.get_controller(ik_rig_asset)
    existing_chains = [c.chain_name for c in ctrl.get_retarget_chains()]
    if "{chain_name}" in existing_chains:
        print("SKIP: chain '{chain_name}' already exists")
    else:
        ctrl.add_retarget_chain(
            "{chain_name}",
            unreal.Name("{start_bone}"),
            unreal.Name("{end_bone}"),
            unreal.Name("{ik_goal_name}")
        )
        unreal.EditorAssetLibrary.save_asset(pkg_path)
        print("OK: chain '{chain_name}' added ({start_bone} -> {end_bone})")
""")
        result = _exec(code)
        output = result.get("output", "")
        if "ERROR" in output:
            return {"success": False, "chain_name": chain_name, "message": output.strip()}
        return {"success": result.get("success", True),
                "chain_name": chain_name,
                "message": output.strip() or f"Chain '{chain_name}' added"}

    @mcp.tool()
    def set_ik_rig_retarget_root(
        ctx: Context,
        ik_rig_name: str,
        ik_rig_path: str,
        root_bone: str
    ) -> Dict[str, Any]:
        """
        Set the retarget root bone on an IK Rig.

        The retarget root is typically the pelvis/hips bone.  It is used by the
        IK Retargeter to align the global position of source and target characters.

        Args:
            ik_rig_name: Asset name (e.g. "IKR_MyCharacter")
            ik_rig_path: Content folder (e.g. "/Game/Animation/IKRigs")
            root_bone: Bone name to use as retarget root (e.g. "pelvis")

        Returns:
            dict with keys: success, message
        """
        code = textwrap.dedent(f"""\
import unreal

pkg_path = "{ik_rig_path}/{ik_rig_name}"
ik_rig_asset = unreal.load_asset(pkg_path)
if ik_rig_asset is None:
    print("ERROR: IKRig not found: " + pkg_path)
else:
    ctrl = unreal.IKRigController.get_controller(ik_rig_asset)
    ctrl.set_retarget_root(unreal.Name("{root_bone}"))
    unreal.EditorAssetLibrary.save_asset(pkg_path)
    print("OK: retarget root set to '{root_bone}'")
""")
        result = _exec(code)
        output = result.get("output", "")
        if "ERROR" in output:
            return {"success": False, "message": output.strip()}
        return {"success": result.get("success", True),
                "message": output.strip() or f"Retarget root set to '{root_bone}'"}

    # ─────────────────────────────────────────────────────────────────────────
    # IK RETARGETER TOOLS
    # ─────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    def create_ik_retargeter(
        ctx: Context,
        retargeter_name: str,
        source_ik_rig_path: str,
        target_ik_rig_path: str,
        path: str = "/Game/Animation/Retargeters",
        auto_map_chains: bool = True,
        auto_align_bones: bool = True
    ) -> Dict[str, Any]:
        """
        Create an IK Retargeter asset that maps animations from a source skeleton
        to a target skeleton.

        Requires that both source and target IK Rig assets already exist (use
        create_ik_rig first).  This is the equivalent of the UE5 editor
        "Create IK Retargeter" workflow.

        Typical workflow:
          1. create_ik_rig  (source)
          2. create_ik_rig  (target)
          3. create_ik_retargeter  ← this tool
          4. batch_retarget_animations

        Args:
            retargeter_name: Asset name (e.g. "RTG_Mannequin_To_MyChar")
            source_ik_rig_path: Full content path to source IK Rig
                                (e.g. "/Game/Animation/IKRigs/IKR_Mannequin")
            target_ik_rig_path: Full content path to target IK Rig
                                (e.g. "/Game/Animation/IKRigs/IKR_MyCharacter")
            path: Destination content-browser folder
            auto_map_chains: Automatically map chain pairs by name similarity
            auto_align_bones: Automatically align A-pose / T-pose between skeletons

        Returns:
            dict with keys: success, asset_path, message
        """
        return _create_ik_retargeter(
            retargeter_name, source_ik_rig_path, target_ik_rig_path,
            path, auto_map_chains, auto_align_bones
        )

    @mcp.tool()
    def batch_retarget_animations(
        ctx: Context,
        retargeter_path: str,
        source_animation_paths: List[str],
        output_path: str,
        output_suffix: str = "_Retargeted",
        use_existing_if_found: bool = True
    ) -> Dict[str, Any]:
        """
        Retarget a list of animation sequences using an existing IK Retargeter.

        This is the programmatic equivalent of the UE5 editor
        "Retarget Animations → Export Animations" workflow (Method 1 / quick path).

        After setting up the IK Retargeter once (create_ik_retargeter), call this
        tool to batch-export retargeted copies of all your animations.

        Args:
            retargeter_path: Full content path to the IKRetargeter asset
                             (e.g. "/Game/Animation/Retargeters/RTG_Mannequin_To_MyChar")
            source_animation_paths: List of animation sequence content paths to retarget
                             (e.g. ["/Game/Animations/Walk", "/Game/Animations/Run"])
            output_path: Destination folder for retargeted animations
                         (e.g. "/Game/Characters/MyChar/Animations")
            output_suffix: Suffix appended to each output asset name (default "_Retargeted")
            use_existing_if_found: Skip retargeting if the output asset already exists

        Returns:
            dict with keys: success, retargeted (count), skipped (count),
                            failed (count), output (raw UE5 log)
        """
        return _batch_retarget_animations(
            retargeter_path, source_animation_paths,
            output_path, output_suffix, use_existing_if_found
        )

    @mcp.tool()
    def setup_full_retargeting_pipeline(
        ctx: Context,
        source_skeletal_mesh: str,
        target_skeletal_mesh: str,
        source_ik_rig_name: str,
        target_ik_rig_name: str,
        retargeter_name: str,
        ik_rig_path: str = "/Game/Animation/IKRigs",
        retargeter_path: str = "/Game/Animation/Retargeters",
        animations_to_retarget: List[str] = None,
        output_animation_path: str = "/Game/Animation/Retargeted"
    ) -> Dict[str, Any]:
        """
        One-shot pipeline: create IK Rigs for source + target, create IK Retargeter,
        and optionally batch-retarget a list of animations.

        This matches Method 2 (Manual IK Retargeting) described in the UE5 docs:
          1. Create IK Rig for source skeleton (auto-generate chains)
          2. Create IK Rig for target skeleton (auto-generate chains)
          3. Create IK Retargeter (source → target, auto-map chains + auto-align)
          4. Export retargeted animations

        If all your characters share an identical skeleton (same bone names and
        hierarchy) you can skip this and use the quick-retarget workflow in the
        editor; but this pipeline handles mis-matched bone structures.

        Args:
            source_skeletal_mesh: Content path to source Skeletal Mesh
                                  (e.g. "/Game/Characters/Mannequin/SK_Mannequin")
            target_skeletal_mesh: Content path to target Skeletal Mesh
                                  (e.g. "/Game/Dantooine/Art/Characters/Player/SK_Player")
            source_ik_rig_name: Name for source IK Rig asset (e.g. "IKR_Mannequin")
            target_ik_rig_name: Name for target IK Rig asset (e.g. "IKR_Player")
            retargeter_name: Name for IK Retargeter asset
                             (e.g. "RTG_Mannequin_To_Player")
            ik_rig_path: Folder for IK Rig assets
            retargeter_path: Folder for IK Retargeter asset
            animations_to_retarget: Optional list of animation content paths to
                                    retarget immediately after setup
            output_animation_path: Output folder for retargeted animations

        Returns:
            dict with keys: success, steps (dict of per-step results), message
        """
        steps: Dict[str, Any] = {}

        # Step 1: Source IK Rig
        steps["source_ik_rig"] = _create_ik_rig(
            source_ik_rig_name, source_skeletal_mesh, ik_rig_path, True
        )
        src_ok = steps["source_ik_rig"].get("success", False)
        src_msg = steps["source_ik_rig"].get("message", "")
        if not src_ok and "already exists" not in src_msg:
            return {"success": False, "steps": steps,
                    "message": f"Source IK Rig creation failed: {src_msg}"}

        # Step 2: Target IK Rig
        steps["target_ik_rig"] = _create_ik_rig(
            target_ik_rig_name, target_skeletal_mesh, ik_rig_path, True
        )
        tgt_ok = steps["target_ik_rig"].get("success", False)
        tgt_msg = steps["target_ik_rig"].get("message", "")
        if not tgt_ok and "already exists" not in tgt_msg:
            return {"success": False, "steps": steps,
                    "message": f"Target IK Rig creation failed: {tgt_msg}"}

        # Step 3: IK Retargeter
        src_rig_full = f"{ik_rig_path}/{source_ik_rig_name}"
        tgt_rig_full = f"{ik_rig_path}/{target_ik_rig_name}"
        steps["retargeter"] = _create_ik_retargeter(
            retargeter_name, src_rig_full, tgt_rig_full,
            retargeter_path, True, True
        )
        rtg_ok  = steps["retargeter"].get("success", False)
        rtg_msg = steps["retargeter"].get("message", "")
        if not rtg_ok and "already exists" not in rtg_msg:
            return {"success": False, "steps": steps,
                    "message": f"IKRetargeter creation failed: {rtg_msg}"}

        # Step 4: Batch retarget (optional)
        if animations_to_retarget:
            rtg_full = f"{retargeter_path}/{retargeter_name}"
            steps["batch_retarget"] = _batch_retarget_animations(
                rtg_full, animations_to_retarget,
                output_animation_path, "_Retargeted", True
            )

        return {
            "success": True,
            "steps": steps,
            "message": (
                f"Retargeting pipeline complete. "
                f"Source IK Rig: {ik_rig_path}/{source_ik_rig_name}, "
                f"Target IK Rig: {ik_rig_path}/{target_ik_rig_name}, "
                f"Retargeter: {retargeter_path}/{retargeter_name}"
            )
        }

    @mcp.tool()
    def get_skeleton_bone_names(
        ctx: Context,
        skeletal_mesh_path: str
    ) -> Dict[str, Any]:
        """
        List all bone names in a Skeletal Mesh's skeleton.

        Use this before setting up an IK Rig to discover the exact bone names
        required for retarget chains (start_bone / end_bone parameters).

        Args:
            skeletal_mesh_path: Content path to the Skeletal Mesh
                                (e.g. "/Game/Characters/Player/SK_Player")

        Returns:
            dict with keys: success, bone_count, bone_names (list of strings), message
        """
        code = textwrap.dedent(f"""\
import unreal

skel_mesh = unreal.load_asset("{skeletal_mesh_path}")
if skel_mesh is None:
    print("ERROR: Skeletal mesh not found: {skeletal_mesh_path}")
else:
    skeleton = skel_mesh.skeleton
    if skeleton is None:
        print("ERROR: No skeleton attached to {skeletal_mesh_path}")
    else:
        ref_skeleton = skeleton.get_editor_property("reference_skeleton")
        bones = []
        for i in range(ref_skeleton.get_raw_bone_num()):
            bone_info = ref_skeleton.get_raw_ref_bone_info(i)
            bones.append(str(bone_info.name))
        print("BONE_COUNT=" + str(len(bones)))
        print("BONES=" + "|".join(bones))
""")
        result = _exec(code)
        output = result.get("output", "")
        if "ERROR" in output:
            return {"success": False, "bone_count": 0, "bone_names": [],
                    "message": output.strip()}

        bone_names: List[str] = []
        bone_count = 0
        for line in output.splitlines():
            if line.startswith("BONE_COUNT="):
                try:
                    bone_count = int(line.split("=", 1)[1])
                except ValueError:
                    pass
            elif line.startswith("BONES="):
                raw = line.split("=", 1)[1]
                bone_names = [b for b in raw.split("|") if b]

        return {
            "success": result.get("success", False),
            "bone_count": bone_count,
            "bone_names": bone_names,
            "message": f"{bone_count} bones found in {skeletal_mesh_path}"
        }

    @mcp.tool()
    def retarget_single_animation(
        ctx: Context,
        retargeter_path: str,
        source_animation_path: str,
        output_path: str,
        output_name: str = "",
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Retarget a single animation sequence using an existing IK Retargeter.

        Convenience wrapper around batch_retarget_animations for single assets.
        Useful for quick tests before running the full batch.

        Args:
            retargeter_path: Full content path to the IKRetargeter asset
            source_animation_path: Content path of the source animation
            output_path: Destination folder for the retargeted animation
            output_name: Output asset name (default: source name + "_Retargeted")
            overwrite: If True, overwrite an existing output asset

        Returns:
            dict with keys: success, output_asset_path, message
        """
        src_name = source_animation_path.rstrip("/").split("/")[-1]
        out_name = output_name if output_name else f"{src_name}_Retargeted"
        out_full = f"{output_path}/{out_name}"
        overwrite_str = "True" if overwrite else "False"

        code = textwrap.dedent(f"""\
import unreal

retargeter = unreal.load_asset("{retargeter_path}")
if retargeter is None:
    print("ERROR: IKRetargeter not found: {retargeter_path}")
else:
    anim_asset = unreal.load_asset("{source_animation_path}")
    if anim_asset is None:
        print("ERROR: Animation not found: {source_animation_path}")
    else:
        out_pkg = "{out_full}"
        if not {overwrite_str} and unreal.EditorAssetLibrary.does_asset_exist(out_pkg):
            print("SKIP: output already exists: " + out_pkg)
        else:
            exported = None
            if hasattr(unreal, "IKRetargetEditorController"):
                try:
                    opts = unreal.AnimationRetargetingOptions()
                    exported = unreal.IKRetargetEditorController.export_animations_from_assets(
                        [anim_asset], retargeter, out_pkg, opts
                    )
                except Exception as e1:
                    print("WARN IKRetargetEditorController: " + str(e1))

            if exported is None and hasattr(unreal, "IKRetargetingUtils"):
                try:
                    exported = unreal.IKRetargetingUtils.retarget_animation_sequence(
                        retargeter, anim_asset, out_pkg
                    )
                except Exception as e2:
                    print("WARN IKRetargetingUtils: " + str(e2))

            if exported is None:
                try:
                    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
                    asset_tools.retarget_animation_assets(
                        [anim_asset], "{output_path}", "_Retargeted", retargeter
                    )
                    exported = unreal.load_asset(out_pkg)
                except Exception as e3:
                    print("FAIL AssetTools: " + str(e3))

            if exported:
                unreal.EditorAssetLibrary.save_asset(out_pkg)
                print("OK: " + out_pkg)
            else:
                print("FAIL: export returned None for {source_animation_path}")
""")
        result = _exec(code)
        output = result.get("output", "")
        success = result.get("success", False) and "OK:" in output
        return {
            "success": success,
            "output_asset_path": out_full,
            "message": output.strip() or ("Retargeted" if success else "Retarget failed")
        }

    logger.info("Animation tools registered (including IK Rig / IK Retargeter)")
