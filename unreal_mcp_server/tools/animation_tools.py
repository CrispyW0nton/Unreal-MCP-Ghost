"""
Animation Tools - Animation Blueprints, State Machines, Blend Spaces.
Covers Chapter 17 from the Blueprint book.
"""
import logging
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

    logger.info("Animation tools registered")
