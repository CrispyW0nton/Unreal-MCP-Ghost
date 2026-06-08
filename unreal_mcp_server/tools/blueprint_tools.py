"""
Blueprint Tools - Create/modify Blueprint classes and components.
Ported from: https://github.com/chongdashu/unreal-mcp
"""
import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_blueprint_tools(mcp: FastMCP):
    def _structured_bridge_result(
        raw: Dict[str, Any],
        *,
        stage: str,
        message: str,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize native Blueprint command responses for new B.1 tools."""
        raw = raw or {}
        error_message = raw.get("error") or raw.get("message") or ""
        success = raw.get("success") is not False and raw.get("status") != "error" and not raw.get("error")
        return {
            "success": success,
            "stage": stage,
            "message": message if success else (error_message or f"{stage} failed"),
            "inputs": inputs,
            "outputs": {
                key: value
                for key, value in raw.items()
                if key not in {"success", "status", "message", "error"}
            } if success else {},
            "warnings": [],
            "errors": [] if success else [error_message or f"{stage} failed"],
            "log_tail": [],
        }

    @mcp.tool()
    def create_blueprint(
        ctx: Context,
        name: str,
        parent_class: str
    ) -> Dict[str, Any]:
        """Create a new Blueprint class in /Game/Blueprints/.

        Args:
            name: Blueprint asset name (e.g., "BP_MyActor")
            parent_class: Parent class (Actor, Pawn, Character, PlayerController,
                          GameModeBase, GameInstance, HUD, UserWidget, AIController, etc.)

        Returns:
            Dict with 'name' and 'path' of the created Blueprint

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            create_blueprint(name="ExampleName", parent_class="Actor")"""
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
    def bp_copy_component(
        ctx: Context,
        source_bp: str,
        dest_bp: str,
        component_name: str,
        new_component_name: str = "",
    ) -> Dict[str, Any]:
        """Copy an SCS component from one Blueprint to another.

        The native route creates a new component node with the same component
        class, copies editable template properties, preserves a matching parent
        component when present, and marks the destination Blueprint dirty using
        the plugin's deferred dirty-marking path.

        Args:
            source_bp: Source Blueprint asset name or path.
            dest_bp: Destination Blueprint asset name or path.
            component_name: SCS component variable name to copy.
            new_component_name: Optional destination component name. Defaults to component_name.

        KB: see knowledge_base/11_BLUEPRINT_LIBRARIES_AND_COMPONENTS.md#overview
        Example:
            bp_copy_component(source_bp="/Game/MCP_Test/BP_Source", dest_bp="/Game/MCP_Test/BP_Dest", component_name="ExampleComponent")
        """
        from unreal_mcp_server import get_unreal_connection
        inputs = {
            "source_bp": source_bp,
            "dest_bp": dest_bp,
            "component_name": component_name,
            "new_component_name": new_component_name or component_name,
        }
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {
                    "success": False,
                    "stage": "bp_copy_component",
                    "message": "Not connected to Unreal Engine",
                    "inputs": inputs,
                    "outputs": {},
                    "warnings": [],
                    "errors": ["Not connected to Unreal Engine"],
                    "log_tail": [],
                }
            raw = unreal.send_command("bp_copy_component", inputs) or {}
            return _structured_bridge_result(
                raw,
                stage="bp_copy_component",
                message=f"Copied component '{component_name}' from '{source_bp}' to '{dest_bp}'",
                inputs=inputs,
            )
        except Exception as e:
            return {
                "success": False,
                "stage": "bp_copy_component",
                "message": str(e),
                "inputs": inputs,
                "outputs": {},
                "warnings": [],
                "errors": [str(e)],
                "log_tail": [],
            }

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
        """Add a component to an existing Blueprint.

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

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            add_component_to_blueprint(blueprint_name="/Game/MCP_Test/BP_Example", component_type="Actor", component_name="ExampleComponent")"""
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
    def add_niagara_component(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        niagara_system_path: str = "",
    ) -> Dict[str, Any]:
        """Add a NiagaraComponent to a Blueprint through the native bridge route.

        Use this for playable-slice VFX hooks such as enemy hit sparks, ambient
        magic props, portals, or generated asset preview effects. The native
        command adds an SCS NiagaraComponent and optionally assigns a Niagara
        System asset.

        Args:
            blueprint_name: Blueprint asset name or path.
            component_name: SCS variable name for the NiagaraComponent.
            niagara_system_path: Optional UNiagaraSystem asset path.

        KB: see knowledge_base/09_VISUAL_EFFECTS_NIAGARA.md#overview
        Example:
            add_niagara_component(blueprint_name="/Game/MCP_Test/BP_Example", component_name="FX_Glow")
        """
        from unreal_mcp_server import get_unreal_connection
        inputs: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "niagara_system_path": niagara_system_path,
        }
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {
                    "success": False,
                    "stage": "add_niagara_component",
                    "message": "Not connected to Unreal Engine",
                    "inputs": inputs,
                    "outputs": {},
                    "warnings": [],
                    "errors": ["Not connected to Unreal Engine"],
                    "log_tail": [],
                }
            raw = unreal.send_command("add_niagara_component", inputs) or {}
            return _structured_bridge_result(
                raw,
                stage="add_niagara_component",
                message=f"Added Niagara component '{component_name}' to '{blueprint_name}'",
                inputs=inputs,
            )
        except Exception as e:
            return {
                "success": False,
                "stage": "add_niagara_component",
                "message": str(e),
                "inputs": inputs,
                "outputs": {},
                "warnings": [],
                "errors": [str(e)],
                "log_tail": [],
            }

    @mcp.tool()
    def set_static_mesh_properties(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        static_mesh: str = "/Engine/BasicShapes/Cube.Cube",
        material: str = ""
    ) -> Dict[str, Any]:
        """Assign a static mesh (and optionally a material) to a StaticMeshComponent.

        Args:
            blueprint_name: Blueprint name
            component_name: StaticMeshComponent name
            static_mesh: Asset path (e.g., "/Engine/BasicShapes/Sphere.Sphere")
            material: Optional material asset path

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            set_static_mesh_properties(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent")"""
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
    def set_blueprint_parent_class(
        ctx: Context,
        blueprint_name: str,
        new_parent_class: str,
    ) -> Dict[str, Any]:
        """Reparent a Blueprint to a Blueprint or native C++ parent class.

        Use this when a generated gameplay Blueprint needs to move from a
        generic Actor shell to Pawn, Character, Controller, or a project-specific
        base class before the playable slice is compiled.

        Args:
            blueprint_name: Blueprint asset name or path to reparent.
            new_parent_class: Blueprint asset name/path or native class name.

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            set_blueprint_parent_class(blueprint_name="/Game/MCP_Test/BP_Enemy", new_parent_class="Character")
        """
        from unreal_mcp_server import get_unreal_connection
        inputs = {
            "blueprint_name": blueprint_name,
            "new_parent_class": new_parent_class,
        }
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {
                    "success": False,
                    "stage": "set_blueprint_parent_class",
                    "message": "Not connected to Unreal Engine",
                    "inputs": inputs,
                    "outputs": {},
                    "warnings": [],
                    "errors": ["Not connected to Unreal Engine"],
                    "log_tail": [],
                }
            raw = unreal.send_command("set_blueprint_parent_class", inputs) or {}
            return _structured_bridge_result(
                raw,
                stage="set_blueprint_parent_class",
                message=f"Reparented '{blueprint_name}' to '{new_parent_class}'",
                inputs=inputs,
            )
        except Exception as e:
            return {
                "success": False,
                "stage": "set_blueprint_parent_class",
                "message": str(e),
                "inputs": inputs,
                "outputs": {},
                "warnings": [],
                "errors": [str(e)],
                "log_tail": [],
            }

    @mcp.tool()
    def set_pawn_properties(
        ctx: Context,
        blueprint_name: str,
        auto_possess_player: str = "",
        auto_possess_ai: str = "",
        use_controller_rotation_yaw: Optional[bool] = None,
        use_controller_rotation_pitch: Optional[bool] = None,
        use_controller_rotation_roll: Optional[bool] = None,
        can_be_damaged: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Set common Pawn/Character class-default properties on a Blueprint.

        Use this after creating or reparenting a playable slice pawn so spawned
        characters have the right possession, controller-rotation, and damage
        defaults before compile/save validation.

        Args:
            blueprint_name: Pawn or Character Blueprint asset name/path.
            auto_possess_player: Optional AutoPossessPlayer enum string.
            auto_possess_ai: Optional AutoPossessAI enum string.
            use_controller_rotation_yaw: Optional bUseControllerRotationYaw.
            use_controller_rotation_pitch: Optional bUseControllerRotationPitch.
            use_controller_rotation_roll: Optional bUseControllerRotationRoll.
            can_be_damaged: Optional bCanBeDamaged value.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            set_pawn_properties(blueprint_name="/Game/MCP_Test/BP_Enemy", auto_possess_ai="PlacedInWorldOrSpawned", can_be_damaged=True)
        """
        from unreal_mcp_server import get_unreal_connection
        inputs: Dict[str, Any] = {"blueprint_name": blueprint_name}
        if auto_possess_player:
            inputs["auto_possess_player"] = auto_possess_player
        if auto_possess_ai:
            inputs["auto_possess_ai"] = auto_possess_ai
        if use_controller_rotation_yaw is not None:
            inputs["use_controller_rotation_yaw"] = use_controller_rotation_yaw
        if use_controller_rotation_pitch is not None:
            inputs["use_controller_rotation_pitch"] = use_controller_rotation_pitch
        if use_controller_rotation_roll is not None:
            inputs["use_controller_rotation_roll"] = use_controller_rotation_roll
        if can_be_damaged is not None:
            inputs["can_be_damaged"] = can_be_damaged

        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {
                    "success": False,
                    "stage": "set_pawn_properties",
                    "message": "Not connected to Unreal Engine",
                    "inputs": inputs,
                    "outputs": {},
                    "warnings": [],
                    "errors": ["Not connected to Unreal Engine"],
                    "log_tail": [],
                }
            raw = unreal.send_command("set_pawn_properties", inputs) or {}
            return _structured_bridge_result(
                raw,
                stage="set_pawn_properties",
                message=f"Set Pawn defaults on '{blueprint_name}'",
                inputs=inputs,
            )
        except Exception as e:
            return {
                "success": False,
                "stage": "set_pawn_properties",
                "message": str(e),
                "inputs": inputs,
                "outputs": {},
                "warnings": [],
                "errors": [str(e)],
                "log_tail": [],
            }

    @mcp.tool()
    def set_component_property(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        property_name: str,
        property_value
    ) -> Dict[str, Any]:
        """Set any property on a Blueprint component.

        Args:
            blueprint_name: Blueprint name
            component_name: Component name
            property_name: C++ property name (e.g., "TargetArmLength", "bUsePawnControlRotation")
            property_value: Value (bool, int, float, string, or [x,y,z] array for vectors)

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            set_component_property(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent", property_name="ExampleName", property_value="ExampleName")"""
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
        """Configure physics simulation on a primitive component.

        Args:
            blueprint_name: Blueprint name
            component_name: Component name (must be a PrimitiveComponent)
            simulate_physics: Enable physics simulation
            gravity_enabled: Enable gravity
            mass: Mass in kg
            linear_damping: Linear damping coefficient
            angular_damping: Angular damping coefficient

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            set_physics_properties(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent")"""
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
        """Compile a Blueprint to apply all changes.

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            compile_blueprint(blueprint_name="/Game/MCP_Test/BP_Example")"""
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
        """Set a property on the Blueprint class default object (CDO).

        Args:
            blueprint_name: Blueprint name
            property_name: Property name (e.g., "AutoPossessPlayer", "bUseControllerRotationYaw")
            property_value: New value

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            set_blueprint_property(blueprint_name="/Game/MCP_Test/BP_Example", property_name="ExampleName", property_value="ExampleName")"""
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
        """Assign a SkeletalMesh asset and/or materials to a SkeletalMeshComponent in a Blueprint.

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

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            set_skeletal_mesh_properties(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent")"""
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
        """Attach a Blueprint component to a named bone/socket on its parent SkeletalMeshComponent.

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

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            set_component_parent_socket(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent", parent_socket="Example")"""
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
        """Add or replace a socket on the USkeleton used by a skeletal mesh (e.g. GunBarrel).

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

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            add_skeleton_socket(skeletal_mesh_path="/Game/MCP_Test/Example")"""
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
        """Set the AIControllerClass on a Pawn/Character Blueprint.

        This sets the AI Controller Class in the Blueprint's Class Defaults,
        which is required for AI movement (MoveToActor, SimpleMoveToActor) to work.

        Args:
            blueprint_name:   Name of the Blueprint (must be a Pawn or Character subclass).
            controller_class: Short class name like 'AIController' (default) or a custom
                              controller class name.

        Returns:
            Dict with 'blueprint', 'ai_controller_class', and 'success'.

        KB: see knowledge_base/01_BLUEPRINT_FUNDAMENTALS.md#overview
        Example:
            set_blueprint_ai_controller(blueprint_name="/Game/MCP_Test/BP_Example")"""
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
