"""
Animation Tools - Animation Blueprints, State Machines, Blend Spaces,
IK Rig creation, and IK Retargeter (animation retargeting) tools.

IK Rig / Retargeter tools use exec_python to call the UE5 Python API
(unreal.IKRigController, unreal.IKRetargeterController) because those
classes live in the IKRigEditor module and are not exposed via the MCP
C++ bridge.
"""
import logging
import ast
import json
import textwrap
import time
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


def _make_result(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": stage, "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _bridge_result(
    *,
    stage: str,
    raw: Dict[str, Any],
    inputs: Dict[str, Any],
    message: str,
    t0: float,
) -> str:
    raw = raw or {}
    failed = raw.get("success") is False or raw.get("status") == "error" or bool(raw.get("error"))
    if failed:
        msg = raw.get("error") or raw.get("message") or f"{stage} failed"
        return json.dumps(_make_result(
            success=False,
            stage="error",
            message=msg,
            inputs=inputs,
            errors=[msg],
            t0=t0,
        ))

    warnings = raw.get("warnings") if isinstance(raw.get("warnings"), list) else []
    outputs = {
        key: value for key, value in raw.items()
        if key not in {"success", "status", "message", "error", "warnings"}
    }
    return json.dumps(_make_result(
        success=True,
        stage=stage,
        message=message,
        inputs=inputs,
        outputs=outputs,
        warnings=warnings,
        t0=t0,
    ))


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


def _eval_script(script: str) -> Dict[str, Any]:
    """Run a UE Python script and return the script's `_mcp_result` dict."""
    from unreal_mcp_server import get_unreal_connection
    expression = f"(lambda ns: (exec({script!r}, ns), ns.get('_mcp_result', {{}}))[1])({{}})"
    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        response = unreal.send_command(
            "exec_python",
            {"code": expression, "mode": "evaluate_statement"}
        ) or {}
    except Exception as e:
        logger.error(f"exec_python evaluate error: {e}")
        return {"success": False, "message": str(e)}

    if not response.get("success", response.get("status") != "error"):
        return {
            "success": False,
            "message": response.get("error") or response.get("message") or "exec_python failed",
            "response": response,
        }

    raw = response.get("command_result")
    if raw is None and isinstance(response.get("result"), dict):
        raw = response["result"].get("command_result")
    if isinstance(raw, dict):
        return raw
    if raw in (None, "", "None"):
        return {"success": False, "message": "No _mcp_result returned", "response": response}
    try:
        parsed = ast.literal_eval(raw)
    except (SyntaxError, ValueError) as e:
        return {
            "success": False,
            "message": f"Could not parse Control Rig result: {e}",
            "raw": raw,
        }
    if isinstance(parsed, dict):
        return parsed
    return {"success": False, "message": "Control Rig script returned a non-dict result", "raw": raw}


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
        """Create an Animation Blueprint (AnimBP).

        Animation Blueprints control skeletal mesh animations using an
        EventGraph (for logic) and AnimGraph (for pose blending).

        Args:
            name: AnimBP name (e.g., "ABP_Character")
            skeleton: Skeleton asset path (e.g., "/Game/Characters/SK_Character")
            parent_class: Parent class (default: "AnimInstance")
            path: Content browser path

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            create_animation_blueprint(name="ExampleName")"""
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
        """Add a State Machine to an Animation Blueprint's AnimGraph.

        State Machines define animation states (Idle, Walk, Run, Jump)
        and transitions between them.

        Args:
            anim_blueprint_name: Animation Blueprint name
            state_machine_name: Name for the state machine node

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            add_state_machine(anim_blueprint_name="/Game/MCP_Test/BP_Example")"""
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
        """Add an animation state to a State Machine.

        Args:
            anim_blueprint_name: Animation Blueprint name
            state_machine_name: State machine name
            state_name: State name (e.g., "Idle", "Walk", "Run", "Jump", "Death")
            animation_asset: Optional animation sequence asset path

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            add_animation_state(anim_blueprint_name="/Game/MCP_Test/BP_Example", state_machine_name="ExampleName", state_name="ExampleName")"""
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
        """Add a transition between two animation states.

        Args:
            anim_blueprint_name: Animation Blueprint name
            state_machine_name: State machine name
            from_state: Source state name
            to_state: Destination state name
            condition_variable: Bool variable to use as transition condition
            condition_value: Expected value to trigger transition (True/False)

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            add_state_transition(anim_blueprint_name="/Game/MCP_Test/BP_Example", state_machine_name="ExampleName", from_state="ExampleName", to_state="ExampleName")"""
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
        """Assign an animation sequence to a State Machine state.

        Args:
            anim_blueprint_name: Animation Blueprint name
            state_machine_name: State machine name
            state_name: State to assign animation to
            animation_asset: Animation Sequence asset path
            loop: Loop the animation

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            set_animation_for_state(anim_blueprint_name="/Game/MCP_Test/BP_Example", state_machine_name="ExampleName", state_name="ExampleName", animation_asset="/Game/MCP_Test/Example")"""
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
        """Add a variable to an Animation Blueprint (for use in transitions/logic).

        Args:
            anim_blueprint_name: Animation Blueprint name
            variable_name: Variable name (e.g., "Speed", "bIsJumping", "Direction")
            variable_type: Type (Boolean, Float, Integer, Vector)
            default_value: Optional default value

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            add_anim_blueprint_variable(anim_blueprint_name="/Game/MCP_Test/BP_Example", variable_name="ExampleName", variable_type="ExampleName")"""
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
        """Add a Blend Space node to an Animation Blueprint's AnimGraph.

        Blend Spaces blend animations based on one or two float parameters
        (e.g., Speed and Direction for a locomotion blend space).

        Args:
            anim_blueprint_name: Animation Blueprint name
            blend_space_asset: Blend Space asset path
            node_position: Optional graph position

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            add_blend_space_node(anim_blueprint_name="/Game/MCP_Test/BP_Example", blend_space_asset="/Game/MCP_Test/Example")"""
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
        """Insert a Slot node on the main AnimGraph between the current pose chain and Root.

        Use this so `PlaySlotAnimationAsDynamicMontage` / montages targeting the same
        slot name layer aim and fire animations over locomotion from the state machine.

        Args:
            anim_blueprint_name: AnimBP asset path or name (e.g. ABP_SithSoldier or full /Game/... path)
            slot_name: Anim slot name (default DefaultSlot — must match montage slot / blueprint calls)
            graph_name: Optional graph name; defaults to AnimGraph

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            insert_anim_graph_slot(anim_blueprint_name="/Game/MCP_Test/BP_Example")"""
        params: Dict[str, Any] = {
            "anim_blueprint_name": anim_blueprint_name,
            "slot_name": slot_name,
        }
        if graph_name:
            params["graph_name"] = graph_name
        return _send("insert_anim_graph_slot", params)

    @mcp.tool()
    def add_anim_notify(
        ctx: Context,
        animation_path: str,
        notify_name: str,
        time: float = 0.0,
        notify_type: str = "notify",
        notify_state_duration: float = 0.1
    ) -> Dict[str, Any]:
        """Add an Anim Notify or Notify State to an Animation Sequence or Montage.

        Args:
            animation_path: Full asset path (e.g. /Game/Characters/Run.Run)
            notify_name: Event name to trigger from the AnimBP
            time: Time in seconds
            notify_type: "notify" or "notify_state"
            notify_state_duration: Duration for notify_state entries

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            add_anim_notify(animation_path="/Game/MCP_Test/Example", notify_name="ExampleName")"""
        return _send("add_anim_notify", {
            "animation_path": animation_path,
            "notify_name": notify_name,
            "time": time,
            "notify_type": notify_type,
            "notify_state_duration": notify_state_duration,
        })

    @mcp.tool()
    def anim_create_montage(
        ctx: Context,
        montage_name: str,
        folder_path: str = "/Game/Animation/Montages",
        source_animation_path: str = "",
        skeleton_path: str = "",
        slot_name: str = "DefaultSlot",
        section_name: str = "Default",
        overwrite: bool = False,
        save: bool = True,
        play_rate: float = 1.0,
        loop_count: int = 1
    ) -> Dict[str, Any]:
        """Create an Animation Montage asset from a source AnimSequence or Skeleton.

        Args:
            montage_name: New montage asset name
            folder_path: Content Browser destination folder
            source_animation_path: Optional AnimSequence used to seed the first slot
            skeleton_path: Optional Skeleton; required when source_animation_path is empty
            slot_name: Initial montage slot
            section_name: Initial section name
            overwrite: Replace an existing asset with the same name
            save: Save the asset after creation
            play_rate: Playback rate for the seeded segment
            loop_count: Loop count for the seeded segment

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            anim_create_montage(montage_name="ExampleName")"""
        return _send("anim_create_montage", {
            "montage_name": montage_name,
            "folder_path": folder_path,
            "source_animation_path": source_animation_path,
            "skeleton_path": skeleton_path,
            "slot_name": slot_name,
            "section_name": section_name,
            "overwrite": overwrite,
            "save": save,
            "play_rate": play_rate,
            "loop_count": loop_count,
        })

    @mcp.tool()
    def anim_describe_montage(
        ctx: Context,
        montage_path: str
    ) -> Dict[str, Any]:
        """Inspect a Montage's slots, segments, sections, and notifies.

        Args:
            montage_path: Full montage asset path

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            anim_describe_montage(montage_path="/Game/MCP_Test/Example")"""
        return _send("anim_describe_montage", {"montage_path": montage_path})

    @mcp.tool()
    def anim_add_montage_slot(
        ctx: Context,
        montage_path: str,
        slot_name: str,
        source_animation_path: str = "",
        start_time: float = 0.0,
        play_rate: float = 1.0,
        loop_count: int = 1,
        replace_existing: bool = False,
        save: bool = True
    ) -> Dict[str, Any]:
        """Add or update a slot on an Animation Montage, optionally adding a segment.

        Args:
            montage_path: Full montage asset path
            slot_name: Slot name to create or update
            source_animation_path: Optional AnimSequence/AnimSequenceBase to add as a segment
            start_time: Segment start time in montage seconds
            play_rate: Segment playback rate
            loop_count: Segment loop count
            replace_existing: Clear existing segments on the slot before adding
            save: Save the montage after editing

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            anim_add_montage_slot(montage_path="/Game/MCP_Test/Example", slot_name="ExampleName")"""
        return _send("anim_add_montage_slot", {
            "montage_path": montage_path,
            "slot_name": slot_name,
            "source_animation_path": source_animation_path,
            "start_time": start_time,
            "play_rate": play_rate,
            "loop_count": loop_count,
            "replace_existing": replace_existing,
            "save": save,
        })

    @mcp.tool()
    def anim_set_montage_section(
        ctx: Context,
        montage_path: str,
        section_name: str,
        start_time: float = 0.0,
        next_section_name: str = "",
        save: bool = True
    ) -> Dict[str, Any]:
        """Create or reposition a Montage section and optionally set its next section.

        Args:
            montage_path: Full montage asset path
            section_name: Section name
            start_time: Section start time in seconds
            next_section_name: Optional next section for looping/chaining
            save: Save the montage after editing

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            anim_set_montage_section(montage_path="/Game/MCP_Test/Example", section_name="ExampleName")"""
        return _send("anim_set_montage_section", {
            "montage_path": montage_path,
            "section_name": section_name,
            "start_time": start_time,
            "next_section_name": next_section_name,
            "save": save,
        })

    @mcp.tool()
    def anim_add_branching_point(
        ctx: Context,
        montage_path: str,
        branching_point_name: str,
        time: float = 0.0,
        notify_type: str = "notify",
        notify_state_duration: float = 0.1,
        save: bool = True
    ) -> Dict[str, Any]:
        """Add a Montage Branching Point backed by a branching AnimNotify event.

        Args:
            montage_path: Full montage asset path
            branching_point_name: Branching event name
            time: Time in seconds
            notify_type: "notify" or "notify_state"
            notify_state_duration: Duration for notify_state entries
            save: Save the montage after editing

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            anim_add_branching_point(montage_path="/Game/MCP_Test/Example", branching_point_name="ExampleName")"""
        return _send("anim_add_branching_point", {
            "montage_path": montage_path,
            "branching_point_name": branching_point_name,
            "time": time,
            "notify_type": notify_type,
            "notify_state_duration": notify_state_duration,
            "save": save,
        })

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
        """Insert **Blend List By Bool** + **Sequence Player** between locomotion and the AnimGraph **Slot**
        (requires ``insert_anim_graph_slot`` first: Root ← Slot ← …).

        Locomotion feeds the **false** branch; ``sequence_asset`` (e.g. fire rifle) feeds the **true** branch.
        ``bind_bool_variable`` (default ``bIsShooting``) auto-binds Active Value when the editor plugin supports it.
        ``force_insert=True`` layers a NEW BlendListByBool above an existing one (chain multiple gates,
        e.g. bIsInAir → jump on top of bIsShooting → fire).  Default rebinds the existing node instead.

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            insert_blend_bool_fire_before_slot(anim_blueprint_name="/Game/MCP_Test/BP_Example", sequence_asset="/Game/MCP_Test/Example")"""
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
        """Create a complete character Animation Blueprint with:
        - Speed and IsJumping variables
        - Idle, Walk, Run, and Jump states
        - Transitions based on Speed and jump state

        Args:
            anim_blueprint_name: Animation Blueprint name
            skeleton: Skeleton asset path

        Returns:
            Dict with creation results

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            create_character_animation_setup(anim_blueprint_name="/Game/MCP_Test/BP_Example")"""
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
    # CONTROL RIG TOOLS
    # ─────────────────────────────────────────────────────────────────────────

    @mcp.tool()
    def control_rig_create(
        ctx: Context,
        rig_name: str,
        folder_path: str = "/Game/Animation/ControlRigs",
        skeletal_mesh_path: str = "",
        modular_rig: bool = False,
        import_bones: bool = True,
        overwrite: bool = False,
        save: bool = True
    ) -> Dict[str, Any]:
        """Create a Control Rig Blueprint asset, optionally seeded from a Skeletal Mesh.

        Args:
            rig_name: New Control Rig asset name
            folder_path: Content Browser destination folder
            skeletal_mesh_path: Optional Skeletal Mesh used as preview mesh and bone source
            modular_rig: Create as a modular rig when supported by the engine version
            import_bones: Import bones from the Skeletal Mesh into the rig hierarchy
            overwrite: Delete and replace an existing Control Rig asset
            save: Save the asset after creation

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            control_rig_create(rig_name="ExampleName")"""
        script = textwrap.dedent(f"""\
import unreal

def _finish(result):
    global _mcp_result
    _mcp_result = result

try:
    rig_name = {rig_name!r}
    folder_path = {folder_path!r}.rstrip("/")
    asset_path = f"{{folder_path}}/{{rig_name}}"
    skeletal_mesh_path = {skeletal_mesh_path!r}
    save_asset = {bool(save)!r}
    imported_bones = []

    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        if {bool(overwrite)!r}:
            unreal.EditorAssetLibrary.delete_asset(asset_path)
        else:
            rig = unreal.load_asset(asset_path)
            hierarchy = rig.get_editor_property("hierarchy")
            keys = hierarchy.get_all_keys() if hierarchy else []
            _finish({{
                "success": True,
                "existed": True,
                "asset_path": asset_path,
                "bone_count": len([k for k in keys if k.type == unreal.RigElementType.BONE]),
                "control_count": len([k for k in keys if k.type == unreal.RigElementType.CONTROL]),
                "message": "Control Rig already exists"
            }})
            raise SystemExit

    try:
        rig = unreal.ControlRigBlueprintFactory.create_new_control_rig_asset(
            asset_path, {bool(modular_rig)!r}
        )
    except TypeError:
        rig = unreal.ControlRigBlueprintFactory().create_new_control_rig_asset(
            asset_path, {bool(modular_rig)!r}
        )

    if rig is None:
        _finish({{"success": False, "asset_path": asset_path, "message": "Failed to create Control Rig asset"}})
        raise SystemExit

    preview_mesh = None
    if skeletal_mesh_path:
        preview_mesh = unreal.load_asset(skeletal_mesh_path)
        if preview_mesh is None:
            _finish({{
                "success": False,
                "asset_path": asset_path,
                "message": f"Skeletal Mesh not found: {{skeletal_mesh_path}}"
            }})
            raise SystemExit
        if not isinstance(preview_mesh, unreal.SkeletalMesh):
            loaded_class = preview_mesh.get_class().get_name() if preview_mesh.get_class() else "Unknown"
            _finish({{
                "success": False,
                "asset_path": asset_path,
                "message": f"Asset is {{loaded_class}}, not SkeletalMesh: {{skeletal_mesh_path}}"
            }})
            raise SystemExit
        rig.set_preview_mesh(preview_mesh, True)
        if {bool(import_bones)!r}:
            controller = rig.get_hierarchy_controller()
            imported_bones = controller.import_bones_from_skeletal_mesh(
                preview_mesh, unreal.Name(""), True, True, False, False, False
            )

    try:
        unreal.ControlRigBlueprintLibrary.recompile_vm(rig)
    except Exception:
        pass
    if save_asset:
        unreal.EditorAssetLibrary.save_asset(asset_path)

    hierarchy = rig.get_editor_property("hierarchy")
    keys = hierarchy.get_all_keys() if hierarchy else []
    _finish({{
        "success": True,
        "asset_path": asset_path,
        "preview_mesh": preview_mesh.get_path_name() if preview_mesh else "",
        "imported_bone_count": len(imported_bones),
        "bone_count": len([k for k in keys if k.type == unreal.RigElementType.BONE]),
        "control_count": len([k for k in keys if k.type == unreal.RigElementType.CONTROL]),
        "message": "Control Rig created"
    }})
except SystemExit:
    pass
except Exception as exc:
    _finish({{"success": False, "message": str(exc)}})
""")
        return _eval_script(script)

    @mcp.tool()
    def control_rig_describe(
        ctx: Context,
        rig_path: str,
        include_names: bool = True
    ) -> Dict[str, Any]:
        """Inspect a Control Rig hierarchy, preview mesh, controls, bones, and nulls.

        Args:
            rig_path: Full Control Rig asset path
            include_names: Include element name lists in the result

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            control_rig_describe(rig_path="/Game/MCP_Test/Example")"""
        script = textwrap.dedent(f"""\
import unreal

def _finish(result):
    global _mcp_result
    _mcp_result = result

try:
    rig_path = {rig_path!r}
    rig = unreal.load_asset(rig_path)
    if rig is None:
        _finish({{"success": False, "message": f"Control Rig not found: {{rig_path}}"}})
        raise SystemExit

    hierarchy = rig.get_editor_property("hierarchy")
    keys = hierarchy.get_all_keys() if hierarchy else []
    bones = [str(k.name) for k in keys if k.type == unreal.RigElementType.BONE]
    controls = [str(k.name) for k in keys if k.type == unreal.RigElementType.CONTROL]
    nulls = [str(k.name) for k in keys if k.type == unreal.RigElementType.NULL]
    curves = [str(k.name) for k in keys if k.type == unreal.RigElementType.CURVE]
    preview_mesh = ""
    try:
        mesh = rig.get_preview_mesh()
        preview_mesh = mesh.get_path_name() if mesh else ""
    except Exception:
        pass

    result = {{
        "success": True,
        "asset_path": rig_path,
        "preview_mesh": preview_mesh,
        "element_count": len(keys),
        "bone_count": len(bones),
        "control_count": len(controls),
        "null_count": len(nulls),
        "curve_count": len(curves)
    }}
    if {bool(include_names)!r}:
        result.update({{
            "bones": bones[:250],
            "controls": controls[:250],
            "nulls": nulls[:250],
            "curves": curves[:250]
        }})
    _finish(result)
except SystemExit:
    pass
except Exception as exc:
    _finish({{"success": False, "message": str(exc)}})
""")
        return _eval_script(script)

    @mcp.tool()
    def control_rig_add_control(
        ctx: Context,
        rig_path: str,
        control_name: str,
        parent_name: str = "",
        parent_type: str = "BONE",
        control_type: str = "EULER_TRANSFORM",
        shape_name: str = "Circle",
        shape_color: Optional[List[float]] = None,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
        default_float: float = 0.0,
        default_bool: bool = False,
        save: bool = True
    ) -> Dict[str, Any]:
        """Add an animation control to a Control Rig hierarchy.

        Args:
            rig_path: Full Control Rig asset path
            control_name: New control element name
            parent_name: Optional parent element name
            parent_type: BONE, NULL, or CONTROL
            control_type: EULER_TRANSFORM, POSITION, ROTATOR, FLOAT, BOOL, SCALE, or VECTOR2D
            shape_name: Control shape name from the Control Rig shape library
            shape_color: Optional RGBA list, 0-1 floats
            location: Optional XYZ default location
            rotation: Optional Pitch/Yaw/Roll default rotation
            scale: Optional XYZ default scale
            default_float: Default value for FLOAT/SCALE_FLOAT controls
            default_bool: Default value for BOOL controls
            save: Save the asset after editing

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            control_rig_add_control(rig_path="/Game/MCP_Test/Example", control_name="ExampleName")"""
        shape_color = shape_color or [1.0, 0.55, 0.05, 1.0]
        location = location or [0.0, 0.0, 0.0]
        rotation = rotation or [0.0, 0.0, 0.0]
        scale = scale or [1.0, 1.0, 1.0]
        script = textwrap.dedent(f"""\
import unreal

def _finish(result):
    global _mcp_result
    _mcp_result = result

def _element_type(value):
    return {{
        "BONE": unreal.RigElementType.BONE,
        "NULL": unreal.RigElementType.NULL,
        "CONTROL": unreal.RigElementType.CONTROL,
        "CURVE": unreal.RigElementType.CURVE
    }}.get(str(value).upper(), unreal.RigElementType.NONE)

def _make_key(name, type_name):
    key = unreal.RigElementKey()
    key.set_editor_property("name", unreal.Name(name))
    key.set_editor_property("type", _element_type(type_name))
    return key

try:
    rig_path = {rig_path!r}
    control_name = {control_name!r}
    rig = unreal.load_asset(rig_path)
    if rig is None:
        _finish({{"success": False, "message": f"Control Rig not found: {{rig_path}}"}})
        raise SystemExit

    hierarchy = rig.get_editor_property("hierarchy")
    controller = rig.get_hierarchy_controller()
    existing_key = _make_key(control_name, "CONTROL")
    if hierarchy and hierarchy.contains(existing_key):
        _finish({{
            "success": True,
            "asset_path": rig_path,
            "control_name": control_name,
            "existed": True,
            "message": "Control already exists"
        }})
        raise SystemExit

    parent_key = unreal.RigElementKey()
    parent_name = {parent_name!r}
    if parent_name:
        parent_key = _make_key(parent_name, {parent_type!r})

    control_type_name = str({control_type!r}).upper()
    control_type_map = {{
        "BOOL": unreal.RigControlType.BOOL,
        "FLOAT": unreal.RigControlType.FLOAT,
        "INTEGER": unreal.RigControlType.INTEGER,
        "VECTOR2D": unreal.RigControlType.VECTOR2D,
        "POSITION": unreal.RigControlType.POSITION,
        "SCALE": unreal.RigControlType.SCALE,
        "ROTATOR": unreal.RigControlType.ROTATOR,
        "TRANSFORM": unreal.RigControlType.EULER_TRANSFORM,
        "EULER_TRANSFORM": unreal.RigControlType.EULER_TRANSFORM,
        "SCALE_FLOAT": unreal.RigControlType.SCALE_FLOAT
    }}
    rig_control_type = control_type_map.get(control_type_name, unreal.RigControlType.EULER_TRANSFORM)

    settings = unreal.RigControlSettings()
    settings.set_editor_property("control_type", rig_control_type)
    settings.set_editor_property("animation_type", unreal.RigControlAnimationType.ANIMATION_CONTROL)
    settings.set_editor_property("display_name", control_name)
    settings.set_editor_property("shape_name", unreal.Name({shape_name!r}))
    rgba = {shape_color!r}
    settings.set_editor_property("shape_color", unreal.LinearColor(float(rgba[0]), float(rgba[1]), float(rgba[2]), float(rgba[3])))
    try:
        settings.set_editor_property("shape_visible", True)
    except Exception:
        pass

    loc = {location!r}
    rot = {rotation!r}
    scl = {scale!r}
    if rig_control_type == unreal.RigControlType.BOOL:
        value = hierarchy.make_control_value_from_bool({bool(default_bool)!r})
    elif rig_control_type in (unreal.RigControlType.FLOAT, unreal.RigControlType.SCALE_FLOAT):
        value = hierarchy.make_control_value_from_float(float({default_float!r}))
    elif rig_control_type == unreal.RigControlType.POSITION:
        value = hierarchy.make_control_value_from_vector(unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2])))
    else:
        transform = unreal.Transform(
            unreal.Vector(float(loc[0]), float(loc[1]), float(loc[2])),
            unreal.Rotator(float(rot[0]), float(rot[1]), float(rot[2])),
            unreal.Vector(float(scl[0]), float(scl[1]), float(scl[2]))
        )
        value = hierarchy.make_control_value_from_transform(transform)

    key = controller.add_control(unreal.Name(control_name), parent_key, settings, value, True, False)
    try:
        unreal.ControlRigBlueprintLibrary.recompile_vm(rig)
    except Exception:
        pass
    if {bool(save)!r}:
        unreal.EditorAssetLibrary.save_asset(rig_path)

    keys = hierarchy.get_all_keys() if hierarchy else []
    _finish({{
        "success": True,
        "asset_path": rig_path,
        "control_name": str(key.name),
        "parent_name": parent_name,
        "control_count": len([k for k in keys if k.type == unreal.RigElementType.CONTROL]),
        "message": "Control added"
    }})
except SystemExit:
    pass
except Exception as exc:
    _finish({{"success": False, "message": str(exc)}})
""")
        return _eval_script(script)

    @mcp.tool()
    def control_rig_add_constraint(
        ctx: Context,
        rig_path: str,
        child_name: str,
        parent_name: str,
        child_type: str = "CONTROL",
        parent_type: str = "BONE",
        constraint_type: str = "parent",
        weight: float = 1.0,
        maintain_global_transform: bool = True,
        display_label: str = "",
        save: bool = True
    ) -> Dict[str, Any]:
        """Add a Control Rig hierarchy parent or available-space constraint.

        Args:
            rig_path: Full Control Rig asset path
            child_name: Child element name
            parent_name: Parent/space element name
            child_type: CONTROL, BONE, or NULL
            parent_type: BONE, NULL, or CONTROL
            constraint_type: "parent" for weighted hierarchy parent, "space" for available space
            weight: Parent weight for parent constraints
            maintain_global_transform: Preserve child global transform when adding parent
            display_label: Optional label shown for a space/parent relationship
            save: Save the asset after editing

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            control_rig_add_constraint(rig_path="/Game/MCP_Test/Example", child_name="ExampleName", parent_name="ExampleName")"""
        script = textwrap.dedent(f"""\
import unreal

def _finish(result):
    global _mcp_result
    _mcp_result = result

def _element_type(value):
    return {{
        "BONE": unreal.RigElementType.BONE,
        "NULL": unreal.RigElementType.NULL,
        "CONTROL": unreal.RigElementType.CONTROL,
        "CURVE": unreal.RigElementType.CURVE
    }}.get(str(value).upper(), unreal.RigElementType.NONE)

def _make_key(name, type_name):
    key = unreal.RigElementKey()
    key.set_editor_property("name", unreal.Name(name))
    key.set_editor_property("type", _element_type(type_name))
    return key

try:
    rig_path = {rig_path!r}
    rig = unreal.load_asset(rig_path)
    if rig is None:
        _finish({{"success": False, "message": f"Control Rig not found: {{rig_path}}"}})
        raise SystemExit

    hierarchy = rig.get_editor_property("hierarchy")
    controller = rig.get_hierarchy_controller()
    child_key = _make_key({child_name!r}, {child_type!r})
    parent_key = _make_key({parent_name!r}, {parent_type!r})

    missing = []
    if hierarchy and not hierarchy.contains(child_key):
        missing.append(f"child {{child_key.name}}")
    if hierarchy and not hierarchy.contains(parent_key):
        missing.append(f"parent {{parent_key.name}}")
    if missing:
        _finish({{
            "success": False,
            "asset_path": rig_path,
            "message": "Missing hierarchy element(s): " + ", ".join(missing)
        }})
        raise SystemExit

    label = {display_label!r} or str(parent_key.name)
    if str({constraint_type!r}).lower() == "space":
        added = controller.add_available_space(child_key, parent_key, label, False, False)
        mode = "space"
    else:
        added = controller.add_parent(
            child_key,
            parent_key,
            float({weight!r}),
            {bool(maintain_global_transform)!r},
            label,
            False
        )
        mode = "parent"

    try:
        unreal.ControlRigBlueprintLibrary.recompile_vm(rig)
    except Exception:
        pass
    if {bool(save)!r}:
        unreal.EditorAssetLibrary.save_asset(rig_path)

    _finish({{
        "success": bool(added),
        "asset_path": rig_path,
        "child_name": str(child_key.name),
        "parent_name": str(parent_key.name),
        "constraint_type": mode,
        "message": "Constraint added" if added else "Constraint was not added"
    }})
except SystemExit:
    pass
except Exception as exc:
    _finish({{"success": False, "message": str(exc)}})
""")
        return _eval_script(script)

    @mcp.tool()
    def control_rig_bake_to_sequence(
        ctx: Context,
        level_sequence_path: str = "",
        control_rig_path: str = "",
        binding_display_name: str = "",
        reduce_keys: bool = True,
        tolerance: float = 0.001,
        reset_controls: bool = True
    ) -> Dict[str, Any]:
        """Bake a Sequencer skeletal binding to a Control Rig track when binding context exists.

        This is a guarded adapter over Unreal's ControlRigSequencerLibrary. It validates
        the Level Sequence, Control Rig, and binding name before invoking the bake call.

        Args:
            level_sequence_path: LevelSequence asset containing the skeletal binding
            control_rig_path: Control Rig Blueprint asset to bake onto
            binding_display_name: Display name of the Sequencer binding to bake
            reduce_keys: Run key reduction during bake
            tolerance: Key reduction tolerance
            reset_controls: Reset controls to their initial value on each baked frame

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            control_rig_bake_to_sequence()"""
        script = textwrap.dedent(f"""\
import unreal

def _finish(result):
    global _mcp_result
    _mcp_result = result

try:
    level_sequence_path = {level_sequence_path!r}
    control_rig_path = {control_rig_path!r}
    binding_display_name = {binding_display_name!r}
    if not level_sequence_path or not control_rig_path or not binding_display_name:
        _finish({{
            "success": False,
            "available": hasattr(unreal, "ControlRigSequencerLibrary"),
            "message": "level_sequence_path, control_rig_path, and binding_display_name are required",
            "required_inputs": ["level_sequence_path", "control_rig_path", "binding_display_name"]
        }})
        raise SystemExit

    sequence = unreal.load_asset(level_sequence_path)
    rig = unreal.load_asset(control_rig_path)
    if sequence is None:
        _finish({{"success": False, "message": f"Level Sequence not found: {{level_sequence_path}}"}})
        raise SystemExit
    if rig is None:
        _finish({{"success": False, "message": f"Control Rig not found: {{control_rig_path}}"}})
        raise SystemExit

    binding = None
    binding_names = []
    for candidate in sequence.get_bindings():
        name = str(candidate.get_display_name())
        binding_names.append(name)
        if name == binding_display_name:
            binding = candidate
            break
    if binding is None:
        _finish({{
            "success": False,
            "message": f"Binding '{{binding_display_name}}' not found in sequence",
            "available_bindings": binding_names
        }})
        raise SystemExit

    rig_class = None
    for attr in ("generated_class", "get_control_rig_class"):
        try:
            value = getattr(rig, attr)
            rig_class = value() if callable(value) else value
            if rig_class:
                break
        except Exception:
            pass
    if rig_class is None:
        _finish({{"success": False, "message": "Could not resolve generated Control Rig class"}})
        raise SystemExit

    world = unreal.EditorLevelLibrary.get_editor_world()
    export_options = unreal.AnimSeqExportOption()
    baked = unreal.ControlRigSequencerLibrary.bake_to_control_rig(
        world,
        sequence,
        rig_class,
        export_options,
        {bool(reduce_keys)!r},
        float({tolerance!r}),
        binding,
        {bool(reset_controls)!r}
    )
    _finish({{
        "success": bool(baked),
        "level_sequence_path": level_sequence_path,
        "control_rig_path": control_rig_path,
        "binding_display_name": binding_display_name,
        "message": "Control Rig bake completed" if baked else "Control Rig bake returned false"
    }})
except SystemExit:
    pass
except Exception as exc:
    _finish({{"success": False, "message": str(exc)}})
""")
        return _eval_script(script)

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
        """Create an IK Rig asset for a Skeletal Mesh.

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

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            create_ik_rig(ik_rig_name="ExampleName", skeletal_mesh_path="/Game/MCP_Test/Example")"""
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
        """Add a named retarget chain to an existing IK Rig asset.

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

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            add_ik_rig_retarget_chain(ik_rig_name="ExampleName", ik_rig_path="/Game/MCP_Test/Example", chain_name="ExampleName", start_bone="Example", end_bone="Example")"""
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
        """Set the retarget root bone on an IK Rig.

        The retarget root is typically the pelvis/hips bone.  It is used by the
        IK Retargeter to align the global position of source and target characters.

        Args:
            ik_rig_name: Asset name (e.g. "IKR_MyCharacter")
            ik_rig_path: Content folder (e.g. "/Game/Animation/IKRigs")
            root_bone: Bone name to use as retarget root (e.g. "pelvis")

        Returns:
            dict with keys: success, message

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            set_ik_rig_retarget_root(ik_rig_name="ExampleName", ik_rig_path="/Game/MCP_Test/Example", root_bone="Example")"""
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
        """Create an IK Retargeter asset that maps animations from a source skeleton
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

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            create_ik_retargeter(retargeter_name="ExampleName", source_ik_rig_path="/Game/MCP_Test/Example", target_ik_rig_path="/Game/MCP_Test/Example")"""
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
        """Retarget a list of animation sequences using an existing IK Retargeter.

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

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            batch_retarget_animations(retargeter_path="/Game/MCP_Test/Example", source_animation_paths="/Game/MCP_Test/Example", output_path="/Game/MCP_Test/Example")"""
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
        """One-shot pipeline: create IK Rigs for source + target, create IK Retargeter,
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

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            setup_full_retargeting_pipeline(source_skeletal_mesh="Example", target_skeletal_mesh="Example", source_ik_rig_name="ExampleName", target_ik_rig_name="ExampleName", retargeter_name="ExampleName")"""
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
        """List all bone names in a Skeletal Mesh's skeleton.

        Use this before setting up an IK Rig to discover the exact bone names
        required for retarget chains (start_bone / end_bone parameters).

        Args:
            skeletal_mesh_path: Content path to the Skeletal Mesh
                                (e.g. "/Game/Characters/Player/SK_Player")

        Returns:
            dict with keys: success, bone_count, bone_names (list of strings), message

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            get_skeleton_bone_names(skeletal_mesh_path="/Game/MCP_Test/Example")"""
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
        """Retarget a single animation sequence using an existing IK Retargeter.

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

        KB: see knowledge_base/05_ANIMATION_SYSTEM.md#overview
        Example:
            retarget_single_animation(retargeter_path="/Game/MCP_Test/Example", source_animation_path="/Game/MCP_Test/Example", output_path="/Game/MCP_Test/Example")"""
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

    @mcp.tool()
    def motion_create_pose_search_schema(
        ctx: Context,
        name: str,
        path: str = "/Game/Animation/MotionMatching",
        skeleton: str = "",
        sample_rate: int = 30,
        add_default_channels: bool = True,
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a Pose Search schema asset for Motion Matching databases.

        Args:
            name: Asset name to create.
            path: Content Browser folder under /Game.
            skeleton: Optional Skeleton or Skeletal Mesh asset used to seed the schema.
            sample_rate: Pose sampling rate in Hz.
            add_default_channels: Add UE's default Pose Search feature channels.
            overwrite: Delete an existing schema asset before creation.
            save: Save the asset package after creation.

        Returns:
            Structured JSON with schema asset path, skeletons, sample rate, and channel count.

        KB: see knowledge_base/24_MOTION_MATCHING_AND_CHOOSERS.md#mcp-motion-matching-and-chooser-tools
        Example:
            motion_create_pose_search_schema(name="PSS_Locomotion", skeleton="/Game/Characters/Hero/SK_Hero")"""
        t0 = time.monotonic()
        inputs = {
            "name": name,
            "path": path,
            "skeleton": skeleton,
            "sample_rate": sample_rate,
            "add_default_channels": add_default_channels,
            "overwrite": overwrite,
            "save": save,
        }
        raw = _send("motion_create_pose_search_schema", inputs)
        return _bridge_result(stage="motion_create_pose_search_schema", raw=raw, inputs=inputs, message="Created Pose Search schema", t0=t0)

    @mcp.tool()
    def motion_create_pose_search_database(
        ctx: Context,
        name: str,
        schema: str,
        path: str = "/Game/Animation/MotionMatching",
        sequences: Optional[List[str]] = None,
        search_mode: str = "pca_kd_tree",
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a Pose Search database asset and optionally seed animation sequences.

        Args:
            name: Asset name to create.
            schema: Pose Search schema asset path.
            path: Content Browser folder under /Game.
            sequences: Optional AnimSequence asset paths to add to the database.
            search_mode: Search mode, such as pca_kd_tree, brute_force, vp_tree, or event_only.
            overwrite: Delete an existing database asset before creation.
            save: Save the asset package after creation.

        Returns:
            Structured JSON with database path, schema, search mode, tags, and animation assets.

        KB: see knowledge_base/24_MOTION_MATCHING_AND_CHOOSERS.md#mcp-motion-matching-and-chooser-tools
        Example:
            motion_create_pose_search_database(name="PSD_Locomotion", schema="/Game/Animation/MotionMatching/PSS_Locomotion")"""
        t0 = time.monotonic()
        inputs = {
            "name": name,
            "schema": schema,
            "path": path,
            "sequences": sequences or [],
            "search_mode": search_mode,
            "overwrite": overwrite,
            "save": save,
        }
        raw = _send("motion_create_pose_search_database", inputs)
        return _bridge_result(stage="motion_create_pose_search_database", raw=raw, inputs=inputs, message="Created Pose Search database", t0=t0)

    @mcp.tool()
    def motion_add_database_sequence(
        ctx: Context,
        database: str,
        sequence: str,
        enabled: bool = True,
        disable_reselection: bool = False,
        mirror_option: str = "unmirrored",
        sampling_range: Optional[List[float]] = None,
        save: bool = True,
    ) -> str:
        """Add an AnimSequence entry to a Pose Search database.

        Args:
            database: Pose Search database asset path.
            sequence: AnimSequence asset path to add.
            enabled: Whether the database entry participates in search.
            disable_reselection: Prevent immediate reselection of the same source asset.
            mirror_option: unmirrored, mirrored_only, or both.
            sampling_range: Optional [start_seconds, end_seconds] trim range; [0, 0] means full asset.
            save: Save the database asset after mutation.

        Returns:
            Structured JSON with the added sequence and updated database summary.

        KB: see knowledge_base/24_MOTION_MATCHING_AND_CHOOSERS.md#mcp-motion-matching-and-chooser-tools
        Example:
            motion_add_database_sequence(database="/Game/Animation/MotionMatching/PSD_Locomotion", sequence="/Game/Characters/Hero/Animations/A_Run")"""
        t0 = time.monotonic()
        inputs = {
            "database": database,
            "sequence": sequence,
            "enabled": enabled,
            "disable_reselection": disable_reselection,
            "mirror_option": mirror_option,
            "sampling_range": sampling_range or [0.0, 0.0],
            "save": save,
        }
        raw = _send("motion_add_database_sequence", inputs)
        return _bridge_result(stage="motion_add_database_sequence", raw=raw, inputs=inputs, message="Added sequence to Pose Search database", t0=t0)

    @mcp.tool()
    def motion_inspect_pose_search_asset(
        ctx: Context,
        asset: str,
    ) -> str:
        """Inspect a Pose Search schema or database asset.

        Args:
            asset: Pose Search schema or database asset path.

        Returns:
            Structured JSON with schema channels or database animation assets.

        KB: see knowledge_base/24_MOTION_MATCHING_AND_CHOOSERS.md#mcp-motion-matching-and-chooser-tools
        Example:
            motion_inspect_pose_search_asset(asset="/Game/Animation/MotionMatching/PSD_Locomotion")"""
        t0 = time.monotonic()
        inputs = {"asset": asset}
        raw = _send("motion_inspect_pose_search_asset", inputs)
        return _bridge_result(stage="motion_inspect_pose_search_asset", raw=raw, inputs=inputs, message="Inspected Pose Search asset", t0=t0)

    @mcp.tool()
    def chooser_create_table(
        ctx: Context,
        name: str,
        path: str = "/Game/Animation/Choosers",
        result_class: str = "/Script/CoreUObject.Object",
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a Chooser table configured for object asset results.

        Args:
            name: Asset name to create.
            path: Content Browser folder under /Game.
            result_class: Output object class path or class name.
            overwrite: Delete an existing Chooser table before creation.
            save: Save the asset package after creation.

        Returns:
            Structured JSON with Chooser path, result class, rows, and columns.

        KB: see knowledge_base/24_MOTION_MATCHING_AND_CHOOSERS.md#mcp-motion-matching-and-chooser-tools
        Example:
            chooser_create_table(name="CH_Locomotion", result_class="/Script/Engine.AnimationAsset")"""
        t0 = time.monotonic()
        inputs = {
            "name": name,
            "path": path,
            "result_class": result_class,
            "overwrite": overwrite,
            "save": save,
        }
        raw = _send("chooser_create_table", inputs)
        return _bridge_result(stage="chooser_create_table", raw=raw, inputs=inputs, message="Created Chooser table", t0=t0)

    @mcp.tool()
    def chooser_add_asset_row(
        ctx: Context,
        chooser: str,
        asset: str,
        enabled: bool = True,
        save: bool = True,
    ) -> str:
        """Add a hard asset result row to a Chooser table.

        Args:
            chooser: Chooser table asset path.
            asset: Asset path to use as the row result.
            enabled: Whether the row is enabled.
            save: Save the Chooser table after mutation.

        Returns:
            Structured JSON with the added asset, row index, and updated row list.

        KB: see knowledge_base/24_MOTION_MATCHING_AND_CHOOSERS.md#mcp-motion-matching-and-chooser-tools
        Example:
            chooser_add_asset_row(chooser="/Game/Animation/Choosers/CH_Locomotion", asset="/Game/Characters/Hero/Animations/A_Run")"""
        t0 = time.monotonic()
        inputs = {"chooser": chooser, "asset": asset, "enabled": enabled, "save": save}
        raw = _send("chooser_add_asset_row", inputs)
        return _bridge_result(stage="chooser_add_asset_row", raw=raw, inputs=inputs, message="Added asset row to Chooser table", t0=t0)

    @mcp.tool()
    def chooser_inspect_table(
        ctx: Context,
        chooser: str,
    ) -> str:
        """Inspect a Chooser table's rows, columns, and result settings.

        Args:
            chooser: Chooser table asset path.

        Returns:
            Structured JSON with result type, output class, rows, and columns.

        KB: see knowledge_base/24_MOTION_MATCHING_AND_CHOOSERS.md#mcp-motion-matching-and-chooser-tools
        Example:
            chooser_inspect_table(chooser="/Game/Animation/Choosers/CH_Locomotion")"""
        t0 = time.monotonic()
        inputs = {"chooser": chooser}
        raw = _send("chooser_inspect_table", inputs)
        return _bridge_result(stage="chooser_inspect_table", raw=raw, inputs=inputs, message="Inspected Chooser table", t0=t0)

    @mcp.tool()
    def metahuman_import(
        ctx: Context,
        character_name: str,
        metahuman_root: str = "",
        expected_blueprint: str = "",
        body_skeletal_mesh: str = "",
        face_skeletal_mesh: str = "",
        create_manifest: bool = True,
    ) -> str:
        """Register an assembled MetaHuman package and scan its imported asset tree.

        KB: see knowledge_base/27_METAHUMAN_PIPELINE.md#mcp-metahuman-tools
        Example:
            metahuman_import(character_name="Ada", metahuman_root="/Game/MetaHumans/Ada")"""
        t0 = time.monotonic()
        inputs = {
            "character_name": character_name,
            "metahuman_root": metahuman_root or f"/Game/MetaHumans/{character_name}",
            "expected_blueprint": expected_blueprint,
            "body_skeletal_mesh": body_skeletal_mesh,
            "face_skeletal_mesh": face_skeletal_mesh,
            "create_manifest": create_manifest,
        }
        raw = _send("metahuman_import", inputs)
        return _bridge_result(stage="metahuman_import", raw=raw, inputs=inputs, message="Registered MetaHuman package", t0=t0)

    @mcp.tool()
    def metahuman_inspect_package(
        ctx: Context,
        character_name: str,
        metahuman_root: str = "",
    ) -> str:
        """Inspect a registered MetaHuman manifest and scan its package assets.

        KB: see knowledge_base/27_METAHUMAN_PIPELINE.md#mcp-metahuman-tools
        Example:
            metahuman_inspect_package(character_name="Ada", metahuman_root="/Game/MetaHumans/Ada")"""
        t0 = time.monotonic()
        inputs = {
            "character_name": character_name,
            "metahuman_root": metahuman_root,
        }
        raw = _send("metahuman_inspect_package", inputs)
        return _bridge_result(stage="metahuman_inspect_package", raw=raw, inputs=inputs, message="Inspected MetaHuman package", t0=t0)

    @mcp.tool()
    def metahuman_link_to_skeleton(
        ctx: Context,
        character_name: str,
        body_skeletal_mesh: str,
        target_skeleton: str = "",
        ik_rig: str = "",
        retargeter: str = "",
        anim_blueprint: str = "",
        post_process_anim_blueprint: str = "",
    ) -> str:
        """Link a MetaHuman package to body skeleton, IK, retargeting, and animation assets.

        KB: see knowledge_base/27_METAHUMAN_PIPELINE.md#mcp-metahuman-tools
        Example:
            metahuman_link_to_skeleton(character_name="Ada", body_skeletal_mesh="/Game/MetaHumans/Ada/Body/SK_Ada_Body")"""
        t0 = time.monotonic()
        inputs = {
            "character_name": character_name,
            "body_skeletal_mesh": body_skeletal_mesh,
            "target_skeleton": target_skeleton,
            "ik_rig": ik_rig,
            "retargeter": retargeter,
            "anim_blueprint": anim_blueprint,
            "post_process_anim_blueprint": post_process_anim_blueprint,
        }
        raw = _send("metahuman_link_to_skeleton", inputs)
        return _bridge_result(stage="metahuman_link_to_skeleton", raw=raw, inputs=inputs, message="Linked MetaHuman skeleton and animation assets", t0=t0)

    @mcp.tool()
    def metahuman_assign_dna(
        ctx: Context,
        character_name: str,
        dna_asset: str = "",
        dna_file: str = "",
        face_skeletal_mesh: str = "",
        rig_logic_asset: str = "",
    ) -> str:
        """Assign DNA, face mesh, and rig logic metadata for a MetaHuman package.

        KB: see knowledge_base/27_METAHUMAN_PIPELINE.md#mcp-metahuman-tools
        Example:
            metahuman_assign_dna(character_name="Ada", dna_asset="/Game/MetaHumans/Ada/Face/Ada_DNA")"""
        t0 = time.monotonic()
        inputs = {
            "character_name": character_name,
            "dna_asset": dna_asset,
            "dna_file": dna_file,
            "face_skeletal_mesh": face_skeletal_mesh,
            "rig_logic_asset": rig_logic_asset,
        }
        raw = _send("metahuman_assign_dna", inputs)
        return _bridge_result(stage="metahuman_assign_dna", raw=raw, inputs=inputs, message="Assigned MetaHuman DNA metadata", t0=t0)

    @mcp.tool()
    def metahuman_configure_wrapper(
        ctx: Context,
        character_name: str,
        wrapper_blueprint: str,
        parent_class: str = "/Script/Engine.Character",
        body_component_name: str = "Body",
        face_component_name: str = "Face",
        attach_to_component: str = "Mesh",
        gameplay_tag: str = "Character.MetaHuman",
    ) -> str:
        """Configure wrapper Blueprint metadata for a MetaHuman gameplay character.

        KB: see knowledge_base/27_METAHUMAN_PIPELINE.md#mcp-metahuman-tools
        Example:
            metahuman_configure_wrapper(character_name="Ada", wrapper_blueprint="/Game/Characters/BP_AdaWrapper")"""
        t0 = time.monotonic()
        inputs = {
            "character_name": character_name,
            "wrapper_blueprint": wrapper_blueprint,
            "parent_class": parent_class,
            "body_component_name": body_component_name,
            "face_component_name": face_component_name,
            "attach_to_component": attach_to_component,
            "gameplay_tag": gameplay_tag,
        }
        raw = _send("metahuman_configure_wrapper", inputs)
        return _bridge_result(stage="metahuman_configure_wrapper", raw=raw, inputs=inputs, message="Configured MetaHuman wrapper metadata", t0=t0)

    logger.info("Animation tools registered (including IK Rig / IK Retargeter)")
