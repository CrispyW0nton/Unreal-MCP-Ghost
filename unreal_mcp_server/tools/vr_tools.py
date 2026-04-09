"""
VR Development Tools for Unreal MCP.
Covers Chapter 16 (Introduction to VR Development) from the Blueprint book.

Provides tools for:
- VRPawn Blueprint setup (Motion Controllers, HMD, TeleportTrace Niagara)
- Teleportation system (StartTeleportTrace, TeleportTrace, EndTeleportTrace, TryTeleport)
- Object grabbing (GrabComponent, Try Grab, Try Release, Grab Types)
- Blueprint Interfaces (VRInteractionBPI pattern)
- Snap Turn (left thumbstick rotate)
- Widget Interaction component for VR menus
- MotionController component setup
- Predict Projectile Path By Object Type (for teleport arc)
- InputAxis events for VR controllers
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


def register_vr_tools(mcp: FastMCP):

    @mcp.tool()
    def create_vr_pawn_blueprint(
        ctx: Context,
        name: str = "BP_VRPawn",
        enable_teleportation: bool = True,
        enable_object_grabbing: bool = True,
        enable_snap_turn: bool = True,
        enable_widget_interaction: bool = True,
        folder_path: str = "/Game/VR/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a VRPawn Blueprint with motion controller support.

        From Ch. 16: Replicates the VR template VRPawn structure with:
        - Camera component (player view / HMD position)
        - MotionControllerRight + MotionControllerLeft components
        - MotionControllerRightAim + MotionControllerLeftAim (aim locations)
        - HMD Static Mesh (visual representation in spectator view)
        - TeleportTraceNiagaraSystem component (teleport arc particle system)
        - WidgetInteraction component (interact with VR menus)
        - Input events for thumbstick teleportation, grip grab, trigger fire, menu toggle

        Args:
            name: Pawn Blueprint name
            enable_teleportation: Add teleportation input events and functions
            enable_object_grabbing: Add grab input events and GrabComponent logic
            enable_snap_turn: Add snap turn input event (rotate by fixed angle)
            enable_widget_interaction: Add WidgetInteraction component for menus
            folder_path: Content browser folder
        """
        return _send("create_vr_pawn_blueprint", {
            "name": name,
            "enable_teleportation": enable_teleportation,
            "enable_object_grabbing": enable_object_grabbing,
            "enable_snap_turn": enable_snap_turn,
            "enable_widget_interaction": enable_widget_interaction,
            "folder_path": folder_path
        })

    @mcp.tool()
    def add_motion_controller_component(
        ctx: Context,
        blueprint_name: str,
        component_name: str = "MotionControllerRight",
        motion_source: str = "Right",
        display_device_model: bool = True,
        is_aim_controller: bool = False
    ) -> Dict[str, Any]:
        """
        Add a Motion Controller component to a Blueprint.

        From Ch. 16: Motion Controller components track the physical VR controller
        position and rotation in real-time. The VR template uses pairs of controllers:
        - Grip controllers (MotionControllerRight/Left) - default grip location
        - Aim controllers (MotionControllerRightAim/LeftAim) - pointer/aim location

        MotionSource values: \"Right\", \"Left\", \"RightAim\", \"LeftAim\",
        \"Head\", \"Special1\" through \"Special8\"

        Args:
            blueprint_name: Blueprint to add the component to
            component_name: Component name in the Components panel
            motion_source: Controller source (\"Right\", \"Left\", \"RightAim\", \"LeftAim\")
            display_device_model: Whether to render the controller mesh in game
            is_aim_controller: If True, hide device model (for aim-only controllers)
        """
        return _send("add_component_to_blueprint", {
            "blueprint_name": blueprint_name,
            "component_type": "MotionControllerComponent",
            "component_name": component_name,
            "location": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
            "component_properties": {
                "MotionSource": motion_source,
                "bDisplayDeviceModel": not is_aim_controller and display_device_model
            }
        })

    @mcp.tool()
    def add_widget_interaction_component(
        ctx: Context,
        blueprint_name: str,
        component_name: str = "WidgetInteraction",
        interaction_distance: float = 500.0,
        show_debug: bool = False
    ) -> Dict[str, Any]:
        """
        Add a Widget Interaction component for VR UI interaction.

        From Ch. 16: The Widget Interaction component works like a laser pointer,
        allowing the user to interact with UMG Widget Blueprints placed in the world.
        Used in the VR menu system activated by the Menu button.

        Args:
            blueprint_name: Blueprint to add the component to
            component_name: Component name
            interaction_distance: Max distance for widget interaction (UE units)
            show_debug: Show debug visualization beam
        """
        return _send("add_component_to_blueprint", {
            "blueprint_name": blueprint_name,
            "component_type": "WidgetInteractionComponent",
            "component_name": component_name,
            "location": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
            "component_properties": {
                "InteractionDistance": interaction_distance,
                "bShowDebug": show_debug
            }
        })

    @mcp.tool()
    def add_call_interface_function_node(
        ctx: Context,
        blueprint_name: str,
        interface_name: str,
        function_name: str,
        target_variable: str = "",
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add a node to call a Blueprint Interface function on a target object.

        From Ch. 16: The VRPawn calls TriggerPressed on whatever Grabbable Actor
        the controller is holding - if the Actor implements VRInteractionBPI, the
        function executes; if not, nothing happens (safe call, no crash).

        This is the key advantage of interfaces over direct casting: you can call
        functions on unknown object types safely.

        Args:
            blueprint_name: Blueprint making the call
            interface_name: Interface containing the function
            function_name: Interface function name to call
            target_variable: Variable or node providing the target Actor reference
            node_position: [X, Y] graph position
        """
        return _send("add_call_interface_function_node", {
            "blueprint_name": blueprint_name,
            "interface_name": interface_name,
            "function_name": function_name,
            "target_variable": target_variable,
            "node_position": node_position
        })

    @mcp.tool()
    def create_grab_component(
        ctx: Context,
        name: str = "BP_GrabComponent",
        default_grab_type: str = "Free",
        folder_path: str = "/Game/VR/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a GrabComponent Scene Component for VR object grabbing.

        From Ch. 16: The GrabComponent is added to any Actor you want to be
        grabbable in VR. It handles attachment to the motion controller and
        supports multiple grab types.

        Grab Types (from the book):
        - \"None\": Grabbing disabled (without removing component)
        - \"Free\": Object attaches at current relative position (cubes, balls)
        - \"Snap\": Object snaps to predefined grip location/rotation (weapons)
        - \"Custom\": Use OnGrabbed/OnDropped event dispatchers for custom logic

        The Actor must have Mobility set to Movable.

        Args:
            name: Component Blueprint name
            default_grab_type: Default grab type (\"Free\", \"Snap\", \"None\", \"Custom\")
            folder_path: Content browser folder
        """
        return _send("create_grab_component", {
            "name": name,
            "default_grab_type": default_grab_type,
            "folder_path": folder_path
        })

    @mcp.tool()
    def make_actor_vr_grabbable(
        ctx: Context,
        blueprint_name: str,
        grab_type: str = "Free",
        grab_component_name: str = "GrabComponent",
        simulate_physics: bool = True
    ) -> Dict[str, Any]:
        """
        Make a Blueprint Actor grabbable in VR by adding a GrabComponent.

        From Ch. 16: To make any Actor grabbable, add GrabComponent and set
        Mobility to Movable on the root mesh. The VRPawn's InputAction GrabLeft/Right
        uses a sphere trace near the motion controller to find GrabComponents.

        Args:
            blueprint_name: Blueprint to make grabbable
            grab_type: Grab type (\"Free\", \"Snap\", \"None\", \"Custom\")
            grab_component_name: Name for the GrabComponent
            simulate_physics: Enable physics simulation for realistic grabbing
        """
        return _send("make_actor_vr_grabbable", {
            "blueprint_name": blueprint_name,
            "grab_type": grab_type,
            "grab_component_name": grab_component_name,
            "simulate_physics": simulate_physics
        })

    @mcp.tool()
    def add_teleport_system_to_pawn(
        ctx: Context,
        blueprint_name: str,
        teleport_visualizer_blueprint: str = "BP_TeleportVisualizer",
        deadzone_threshold: float = 0.5,
        use_projectile_path: bool = True
    ) -> Dict[str, Any]:
        """
        Add the complete teleportation system to a VR Pawn Blueprint.

        From Ch. 16: Implements the full teleport system:
        1. InputAxis MovementAxisRight_Y (thumbstick up detection + deadzone check)
        2. DoOnce -> StartTeleportTrace function
        3. TeleportTrace function (PredictProjectilePathByObjectType for arc)
        4. On release: EndTeleportTrace + TryTeleport
        5. Visual feedback via TeleportTrace Niagara System + TeleportVisualizer

        The StartTeleportTrace, TeleportTrace, EndTeleportTrace, TryTeleport
        functions are all created in the pawn Blueprint.

        Args:
            blueprint_name: VR Pawn Blueprint to modify
            teleport_visualizer_blueprint: Blueprint to use as teleport destination marker
            deadzone_threshold: Minimum axis value to start teleport (prevents accidental triggers)
            use_projectile_path: Use projectile arc (True) or straight line (False)
        """
        return _send("add_teleport_system_to_pawn", {
            "blueprint_name": blueprint_name,
            "teleport_visualizer_blueprint": teleport_visualizer_blueprint,
            "deadzone_threshold": deadzone_threshold,
            "use_projectile_path": use_projectile_path
        })

    @mcp.tool()
    def add_vr_input_action_node(
        ctx: Context,
        blueprint_name: str,
        input_action: str,
        node_position: List[int] = [200, 0]
    ) -> Dict[str, Any]:
        """
        Add a VR input action event node to a Blueprint.

        From Ch. 16: VR input actions from the VR template include:
        - \"GrabLeft\" / \"GrabRight\" (grip button)
        - \"TriggerLeft\" / \"TriggerRight\" (trigger button)
        - \"MenuToggleLeft\" / \"MenuToggleRight\" (menu button)
        - \"TeleportLeft\" / \"TeleportRight\" (thumbstick)

        VR axis inputs (use add_blueprint_input_action_node for these):
        - \"MovementAxisRight_Y\" / \"MovementAxisRight_X\" (right thumbstick)
        - \"MovementAxisLeft_Y\" / \"MovementAxisLeft_X\" (left thumbstick)

        Args:
            blueprint_name: Blueprint to add the input node to
            input_action: VR input action name
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_input_action_node", {
            "blueprint_name": blueprint_name,
            "action_name": input_action,
            "node_position": node_position
        })

    @mcp.tool()
    def add_predict_projectile_path_node(
        ctx: Context,
        blueprint_name: str,
        simulation_frequency: float = 15.0,
        max_sim_time: float = 2.0,
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add a PredictProjectilePathByObjectType node for VR teleport arc.

        From Ch. 16: The TeleportTrace function uses this node to calculate the
        arc trajectory of the teleport. Returns the predicted path positions array
        and the landing location for the teleport visualizer.

        Args:
            blueprint_name: Blueprint to add the node to
            simulation_frequency: Path simulation frequency
            max_sim_time: Maximum simulation time for the arc (seconds)
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "GameplayStatics",
            "function_name": "PredictProjectilePathByObjectType",
            "params": {
                "SimFrequency": simulation_frequency,
                "MaxSimTime": max_sim_time
            },
            "node_position": node_position
        })

    @mcp.tool()
    def add_validated_get_node(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        cast_to_class: str = "",
        node_position: List[int] = [300, 0]
    ) -> Dict[str, Any]:
        """
        Add a Validated Get node for safe object reference access.

        From Ch. 16: A Validated Get node (right-click -> Convert to Validated Get)
        adds execution pins to check if an object reference is valid before using it.
        This prevents crashes from accessing destroyed or null references.

        The node has:
        - Is Valid execution pin (proceed normally)
        - Is Not Valid execution pin (handle null case)

        Args:
            blueprint_name: Blueprint to add the node to
            variable_name: Variable to access with validation
            cast_to_class: Optional class to cast to after validation
            node_position: [X, Y] graph position
        """
        return _send("add_validated_get_node", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "cast_to_class": cast_to_class,
            "node_position": node_position
        })

    logger.info("VR tools registered successfully")
