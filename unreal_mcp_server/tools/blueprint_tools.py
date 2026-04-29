"""
Blueprint Tools - Create/modify Blueprint classes and components.
Ported from: https://github.com/chongdashu/unreal-mcp
"""
import logging
from typing import Dict, List, Any
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_blueprint_tools(mcp: FastMCP):

    @mcp.tool()
    def create_blueprint(
        ctx: Context,
        name: str,
        parent_class: str
    ) -> Dict[str, Any]:
        """
        Create a new Blueprint class in /Game/Blueprints/.

        Args:
            name: Blueprint asset name (e.g., "BP_MyActor")
            parent_class: Parent class (Actor, Pawn, Character, PlayerController,
                          GameModeBase, GameInstance, HUD, UserWidget, AIController, etc.)

        Returns:
            Dict with 'name' and 'path' of the created Blueprint
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("create_blueprint", {
                "name": name,
                "parent_class": parent_class
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_component_to_blueprint(
        ctx: Context,
        blueprint_name: str,
        component_type: str,
        component_name: str,
        location: List[float] = [0.0, 0.0, 0.0],
        rotation: List[float] = [0.0, 0.0, 0.0],
        scale: List[float] = [1.0, 1.0, 1.0],
        component_properties: Dict[str, Any] = {}
    ) -> Dict[str, Any]:
        """
        Add a component to an existing Blueprint.

        Args:
            blueprint_name: Name of the Blueprint
            component_type: Component class (StaticMeshComponent, CameraComponent,
                           SpringArmComponent, BoxComponent, AudioComponent,
                           PointLightComponent, CharacterMovementComponent, etc.)
            component_name: Name for the new component
            location: Relative [X,Y,Z] location
            rotation: Relative [Pitch,Yaw,Roll] rotation
            scale: Relative [X,Y,Z] scale
            component_properties: Additional properties dict
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params = {
                "blueprint_name": blueprint_name,
                "component_type": component_type,
                "component_name": component_name,
                "location": [float(v) for v in location],
                "rotation": [float(v) for v in rotation],
                "scale": [float(v) for v in scale],
            }
            if component_properties:
                params["component_properties"] = component_properties
            return unreal.send_command("add_component_to_blueprint", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_static_mesh_properties(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        static_mesh: str = "/Engine/BasicShapes/Cube.Cube",
        material: str = ""
    ) -> Dict[str, Any]:
        """
        Assign a static mesh (and optionally a material) to a StaticMeshComponent.

        Args:
            blueprint_name: Blueprint name
            component_name: StaticMeshComponent name
            static_mesh: Asset path (e.g., "/Engine/BasicShapes/Sphere.Sphere")
            material: Optional material asset path
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params = {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "static_mesh": static_mesh
            }
            if material:
                params["material"] = material
            return unreal.send_command("set_static_mesh_properties", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_component_property(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        property_name: str,
        property_value
    ) -> Dict[str, Any]:
        """
        Set any property on a Blueprint component.

        Args:
            blueprint_name: Blueprint name
            component_name: Component name
            property_name: C++ property name (e.g., "TargetArmLength", "bUsePawnControlRotation")
            property_value: Value (bool, int, float, string, or [x,y,z] array for vectors)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("set_component_property", {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "property_name": property_name,
                "property_value": property_value
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_physics_properties(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        simulate_physics: bool = True,
        gravity_enabled: bool = True,
        mass: float = 1.0,
        linear_damping: float = 0.01,
        angular_damping: float = 0.0
    ) -> Dict[str, Any]:
        """
        Configure physics simulation on a primitive component.

        Args:
            blueprint_name: Blueprint name
            component_name: Component name (must be a PrimitiveComponent)
            simulate_physics: Enable physics simulation
            gravity_enabled: Enable gravity
            mass: Mass in kg
            linear_damping: Linear damping coefficient
            angular_damping: Angular damping coefficient
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("set_physics_properties", {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "simulate_physics": simulate_physics,
                "gravity_enabled": gravity_enabled,
                "mass": float(mass),
                "linear_damping": float(linear_damping),
                "angular_damping": float(angular_damping)
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def compile_blueprint(ctx: Context, blueprint_name: str) -> Dict[str, Any]:
        """Compile a Blueprint to apply all changes."""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("compile_blueprint", {"blueprint_name": blueprint_name}) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_blueprint_property(
        ctx: Context,
        blueprint_name: str,
        property_name: str,
        property_value
    ) -> Dict[str, Any]:
        """
        Set a property on the Blueprint class default object (CDO).

        Args:
            blueprint_name: Blueprint name
            property_name: Property name (e.g., "AutoPossessPlayer", "bUseControllerRotationYaw")
            property_value: New value
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("set_blueprint_property", {
                "blueprint_name": blueprint_name,
                "property_name": property_name,
                "property_value": property_value
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_skeletal_mesh_properties(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        skeletal_mesh: str = "",
        material: str = "",
        materials: List[Dict[str, Any]] = []
    ) -> Dict[str, Any]:
        """
        Assign a SkeletalMesh asset and/or materials to a SkeletalMeshComponent in a Blueprint.

        Use this for character armor pieces, clothing, accessories — any SkeletalMeshComponent
        that needs a mesh assigned and materials applied (textures).

        Args:
            blueprint_name: Blueprint containing the SkeletalMeshComponent
            component_name: SCS variable name of the SkeletalMeshComponent
            skeletal_mesh:  Content path to USkeletalMesh asset
                            (e.g. "/Game/Characters/Armor/SK_ChestPlate")
            material:       Shorthand — assign a single material to slot 0
                            (e.g. "/Game/Materials/M_ArmorBlue")
            materials:      Per-slot list: [{"slot": 0, "material": "/Game/M_Foo"},
                                            {"slot": 1, "material": "/Game/M_Bar"}]
                            Use this when the mesh has multiple material slots.

        Returns:
            Dict with 'success', 'component'
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params: Dict[str, Any] = {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
            }
            if skeletal_mesh:
                params["skeletal_mesh"] = skeletal_mesh
            if material:
                params["material"] = material
            if materials:
                params["materials"] = materials
            return unreal.send_command("set_skeletal_mesh_properties", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_component_parent_socket(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        parent_socket: str,
        parent_component: str = ""
    ) -> Dict[str, Any]:
        """
        Attach a Blueprint component to a named bone/socket on its parent SkeletalMeshComponent.

        This is the correct way to make armor pieces "snap" to the right place on a character.
        Instead of manually tweaking relative transforms, you attach the armor SCS node to a
        specific bone socket (e.g. "hand_r", "spine_01", "head") and UE5 positions it
        automatically following skeleton animation.

        Common bone socket names (UE5 Mannequin):
          "pelvis", "spine_01", "spine_02", "spine_03",
          "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
          "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
          "neck_01", "head",
          "thigh_l", "calf_l", "foot_l", "ball_l",
          "thigh_r", "calf_r", "foot_r", "ball_r"

        Args:
            blueprint_name:   Blueprint to modify
            component_name:   SCS variable name of the child armor/accessory component
            parent_socket:    Bone or socket name to attach to (e.g. "hand_r")
            parent_component: (optional) SCS variable name of the SkeletalMeshComponent to attach to.
                              If omitted, only the socket name is updated on the current parent.

        Returns:
            Dict with 'success', 'component', 'parent_socket'
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params: Dict[str, Any] = {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "parent_socket": parent_socket,
            }
            if parent_component:
                params["parent_component"] = parent_component
            return unreal.send_command("set_component_parent_socket", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_skeleton_socket(
        ctx: Context,
        skeletal_mesh_path: str,
        socket_name: str = "GunBarrel",
        bone_name: str = "ik_hand_gun",
        relative_location: List[float] = None,
        relative_rotation: List[float] = None,
        relative_scale: List[float] = None,
        save: bool = True,
    ) -> Dict[str, Any]:
        """
        Add or replace a socket on the USkeleton used by a skeletal mesh (e.g. GunBarrel).

        Infantry uses the ``GunBarrel`` socket name with ``GetSocketTransform`` on the mesh.
        Sockets are stored on the skeleton asset; Python ``mesh.add_socket`` is unreliable in UE5.6.

        Defaults parent the socket to ``ik_hand_gun`` (Mannequin weapon IK bone) with a 22 cm
        offset along local +X (typical muzzle direction). Override ``relative_rotation`` as
        ``[pitch, yaw, roll]`` in degrees if traces fire along the wrong axis.

        Args:
            skeletal_mesh_path: Content path to the USkeletalMesh (e.g. ``/Game/.../SithSoldier``).
            socket_name: Socket name (default ``GunBarrel``).
            bone_name: Parent bone (default ``ik_hand_gun``; use ``hand_r`` if your rig has no IK gun bone).
            relative_location: Optional ``[x, y, z]`` in cm relative to the bone.
            relative_rotation: Optional ``[pitch, yaw, roll]`` in degrees.
            relative_scale: Optional ``[x, y, z]`` scale (default 1,1,1).
            save: If True, persist the skeleton package via low-level SavePackage.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params: Dict[str, Any] = {
                "skeletal_mesh_path": skeletal_mesh_path,
                "socket_name": socket_name,
                "bone_name": bone_name,
                "save": save,
            }
            if relative_location is not None:
                params["relative_location"] = relative_location
            if relative_rotation is not None:
                params["relative_rotation"] = relative_rotation
            if relative_scale is not None:
                params["relative_scale"] = relative_scale
            return unreal.send_command("add_skeleton_socket", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_blueprint_ai_controller(
        ctx: Context,
        blueprint_name: str,
        controller_class: str = "AIController"
    ) -> dict:
        """
        Set the AIControllerClass on a Pawn/Character Blueprint.

        This sets the AI Controller Class in the Blueprint's Class Defaults,
        which is required for AI movement (MoveToActor, SimpleMoveToActor) to work.

        Args:
            blueprint_name:   Name of the Blueprint (must be a Pawn or Character subclass).
            controller_class: Short class name like 'AIController' (default) or a custom
                              controller class name.

        Returns:
            Dict with 'blueprint', 'ai_controller_class', and 'success'.
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("set_blueprint_ai_controller", {
                "blueprint_name": blueprint_name,
                "controller_class": controller_class,
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("Blueprint tools registered")
