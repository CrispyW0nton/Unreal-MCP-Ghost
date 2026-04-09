"""
Material Tools for Unreal MCP.
Covers Chapter 5 (Object Interaction) and Chapter 10 (AI Enemies) from the Blueprint book.

Provides tools for:
- Creating Materials with VectorParameter (color), ScalarParameter (metallic/roughness)
- Setting / swapping Materials on actors and Blueprint components
- Dynamic material instance creation (SetVectorParameterValue, SetScalarParameterValue)
- Material assignment for meshes in Blueprints (Ch. 5, 9, 10)
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


def register_material_tools(mcp: FastMCP):

    @mcp.tool()
    def create_material(
        ctx: Context,
        name: str,
        base_color: List[float] = [1.0, 0.0, 0.0, 1.0],
        metallic: float = 0.0,
        roughness: float = 0.5,
        emissive_color: List[float] = [0.0, 0.0, 0.0, 1.0],
        opacity: float = 1.0,
        folder_path: str = "/Game/Materials"
    ) -> Dict[str, Any]:
        """
        Create a simple Material asset in the Unreal Content Browser.

        As described in Ch. 5, Materials use VectorParameter nodes for color
        and ScalarParameter nodes for Metallic/Roughness. This tool automates
        the creation of a simple solid-color material.

        Args:
            name: Material asset name (e.g., \"M_TargetRed\")
            base_color: RGBA color array [R, G, B, A] 0.0-1.0 (e.g., [1,0,0,1] for red)
            metallic: Metallic value 0.0-1.0
            roughness: Roughness value 0.0-1.0
            emissive_color: RGBA emissive color for glow effects
            opacity: Opacity 0.0-1.0 (1.0 = fully opaque)
            folder_path: Content browser path where material is created
        """
        return _send("create_material", {
            "name": name,
            "base_color": base_color,
            "metallic": metallic,
            "roughness": roughness,
            "emissive_color": emissive_color,
            "opacity": opacity,
            "folder_path": folder_path
        })

    @mcp.tool()
    def set_material_on_actor(
        ctx: Context,
        actor_name: str,
        material_path: str,
        element_index: int = 0
    ) -> Dict[str, Any]:
        """
        Set a Material on a static mesh actor in the level.

        This corresponds to the \"Set Material\" node used in Ch. 5 of the book,
        where the CylinderTarget changes its Material when hit.

        Args:
            actor_name: Name of the actor in the level (e.g., \"CylinderTarget\")
            material_path: Asset path to the Material (e.g., \"/Game/Materials/M_TargetRed\")
            element_index: Material slot index (0 = first material slot)
        """
        return _send("set_material_on_actor", {
            "actor_name": actor_name,
            "material_path": material_path,
            "element_index": element_index
        })

    @mcp.tool()
    def add_set_material_node(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        material_path: str,
        event_name: str = "ReceiveHit",
        node_position: List[int] = [300, 0]
    ) -> Dict[str, Any]:
        """
        Add a \"Set Material\" node to a Blueprint event graph triggered by an event.

        This creates the core gameplay interaction from Ch. 5: detecting a hit on
        an actor and swapping its material (e.g., cylinder turns red when shot).

        Args:
            blueprint_name: Target Blueprint (e.g., \"BP_CylinderTarget\")
            component_name: Mesh component name (e.g., \"StaticMeshComponent\")
            material_path: Material asset path (e.g., \"/Game/Materials/M_TargetRed\")
            event_name: Event that triggers the material change (\"ReceiveHit\", \"ReceiveBeginPlay\")
            node_position: [X, Y] position in graph
        """
        return _send("add_set_material_node", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "material_path": material_path,
            "event_name": event_name,
            "node_position": node_position
        })

    @mcp.tool()
    def create_dynamic_material_instance(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        source_material_path: str,
        variable_name: str = "DynamicMaterial",
        node_position: List[int] = [200, 0]
    ) -> Dict[str, Any]:
        """
        Create a Dynamic Material Instance from a source Material in a Blueprint.

        Dynamic Material Instances allow runtime modification of material parameters
        (color, opacity, scalar values) without creating separate material assets.
        Used extensively in game HUDs, pickups, and interactive props.

        Args:
            blueprint_name: Blueprint to add the node to
            component_name: Mesh component to create the dynamic instance on
            source_material_path: Base material asset path
            variable_name: Variable name to store the dynamic instance reference
            node_position: [X, Y] graph position
        """
        return _send("create_dynamic_material_instance", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "source_material_path": source_material_path,
            "variable_name": variable_name,
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_vector_parameter_value_node(
        ctx: Context,
        blueprint_name: str,
        dynamic_material_variable: str,
        parameter_name: str,
        color_value: List[float] = [1.0, 0.0, 0.0, 1.0],
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add a SetVectorParameterValue node to change a material color at runtime.

        This is the runtime equivalent of double-clicking the VectorParameter node
        in the Material Editor (Ch. 5). Use this to dynamically change an actor's color.

        Args:
            blueprint_name: Blueprint containing the dynamic material reference
            dynamic_material_variable: Variable name holding the Dynamic Material Instance
            parameter_name: Material parameter name (e.g., \"Color\")
            color_value: RGBA values [R, G, B, A]
            node_position: [X, Y] graph position
        """
        return _send("add_set_vector_parameter_value_node", {
            "blueprint_name": blueprint_name,
            "dynamic_material_variable": dynamic_material_variable,
            "parameter_name": parameter_name,
            "color_value": color_value,
            "node_position": node_position
        })

    @mcp.tool()
    def add_set_scalar_parameter_value_node(
        ctx: Context,
        blueprint_name: str,
        dynamic_material_variable: str,
        parameter_name: str,
        scalar_value: float = 0.0,
        node_position: List[int] = [400, 100]
    ) -> Dict[str, Any]:
        """
        Add a SetScalarParameterValue node to change a material float parameter at runtime.

        Useful for animating material effects like opacity fade-in, glow intensity,
        dissolve transitions, etc.

        Args:
            blueprint_name: Blueprint containing the dynamic material reference
            dynamic_material_variable: Variable name holding the Dynamic Material Instance
            parameter_name: Material scalar parameter name (e.g., \"Opacity\", \"Metallic\")
            scalar_value: Float value to set
            node_position: [X, Y] graph position
        """
        return _send("add_set_scalar_parameter_value_node", {
            "blueprint_name": blueprint_name,
            "dynamic_material_variable": dynamic_material_variable,
            "parameter_name": parameter_name,
            "scalar_value": scalar_value,
            "node_position": node_position
        })

    @mcp.tool()
    def setup_hit_material_swap(
        ctx: Context,
        blueprint_name: str,
        mesh_component: str = "StaticMeshComponent",
        default_material_path: str = "",
        hit_material_path: str = "",
        hit_count_to_destroy: int = 2
    ) -> Dict[str, Any]:
        """
        Set up a full hit-detection + material swap interaction as in Ch. 5.

        Creates the complete \"cylinder target\" interaction:
        1. Event Hit -> track hit count
        2. First hit: swap to hit material
        3. Second+ hit: spawn explosion effect + sound + destroy actor

        Args:
            blueprint_name: Blueprint to modify (e.g., \"BP_CylinderTarget\")
            mesh_component: Static mesh component name
            default_material_path: Original material path
            hit_material_path: Material to apply on first hit (e.g., M_TargetRed)
            hit_count_to_destroy: Number of hits before destruction (default 2)
        """
        return _send("setup_hit_material_swap", {
            "blueprint_name": blueprint_name,
            "mesh_component": mesh_component,
            "default_material_path": default_material_path,
            "hit_material_path": hit_material_path,
            "hit_count_to_destroy": hit_count_to_destroy
        })

    @mcp.tool()
    def add_spawn_emitter_at_location_node(
        ctx: Context,
        blueprint_name: str,
        particle_system_path: str = "/Game/FPWeapon/Effects/P_Impact_Default",
        trigger_event: str = "ReceiveHit",
        node_position: List[int] = [500, 200]
    ) -> Dict[str, Any]:
        """
        Add a SpawnEmitterAtLocation node to trigger particle effects in a Blueprint.

        From Ch. 6 (sound and particle effects). Used to spawn explosion effects,
        dust, sparks, etc. when actors are hit or destroyed.

        Args:
            blueprint_name: Target Blueprint
            particle_system_path: Particle System or Niagara System asset path
            trigger_event: Event that triggers the emitter spawn
            node_position: [X, Y] graph position
        """
        return _send("add_spawn_emitter_at_location_node", {
            "blueprint_name": blueprint_name,
            "particle_system_path": particle_system_path,
            "trigger_event": trigger_event,
            "node_position": node_position
        })

    @mcp.tool()
    def add_play_sound_at_location_node(
        ctx: Context,
        blueprint_name: str,
        sound_asset_path: str = "",
        volume_multiplier: float = 1.0,
        pitch_multiplier: float = 1.0,
        node_position: List[int] = [500, 300]
    ) -> Dict[str, Any]:
        """
        Add a PlaySoundAtLocation node to a Blueprint for audio feedback.

        From Ch. 6 (Adding sound and particle effects). Plays a sound cue
        at the actor's world location when called.

        Args:
            blueprint_name: Target Blueprint
            sound_asset_path: Sound asset path (e.g., \"/Game/FPWeapon/Audio/FirstPersonTemplateWeaponFire02\")
            volume_multiplier: Volume scale (1.0 = normal)
            pitch_multiplier: Pitch scale (1.0 = normal)
            node_position: [X, Y] graph position
        """
        return _send("add_play_sound_at_location_node", {
            "blueprint_name": blueprint_name,
            "sound_asset_path": sound_asset_path,
            "volume_multiplier": volume_multiplier,
            "pitch_multiplier": pitch_multiplier,
            "node_position": node_position
        })

    @mcp.tool()
    def set_collision_settings(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        collision_preset: str = "BlockAllDynamic",
        generate_overlap_events: bool = True,
        hidden_in_game: bool = False
    ) -> Dict[str, Any]:
        """
        Set collision and visibility settings on a Blueprint component.

        From Ch. 9 (AI setup) - used to configure CapsuleComponent collision
        and to hide components in-game.

        Collision presets: NoCollision, OverlapAll, BlockAll, BlockAllDynamic,
        OverlapAllDynamic, Pawn, PhysicsActor, Trigger, InvisibleWall

        Args:
            blueprint_name: Target Blueprint
            component_name: Component to configure
            collision_preset: Collision preset name
            generate_overlap_events: Whether to fire overlap events
            hidden_in_game: Hide this component during gameplay
        """
        return _send("set_collision_settings", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "collision_preset": collision_preset,
            "generate_overlap_events": generate_overlap_events,
            "hidden_in_game": hidden_in_game
        })

    logger.info("Material tools registered successfully")
