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

    logger.info("Blueprint tools registered")
