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
        """Create a simple Material asset in the Unreal Content Browser.

        As described in Ch. 5, Materials use VectorParameter nodes for color
        and ScalarParameter nodes for Metallic/Roughness. This tool automates
        the creation of a simple solid-color material.

        Args:
            name: Material asset name (e.g., "M_TargetRed")
            base_color: RGBA color array [R, G, B, A] 0.0-1.0 (e.g., [1,0,0,1] for red)
            metallic: Metallic value 0.0-1.0
            roughness: Roughness value 0.0-1.0
            emissive_color: RGBA emissive color for glow effects
            opacity: Opacity 0.0-1.0 (1.0 = fully opaque)
            folder_path: Content browser path where material is created

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            create_material(name="ExampleName")"""
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
    def material_create_master(
        ctx: Context,
        material_name: str,
        folder_path: str = "/Game/Materials",
        base_color: List[float] = [1.0, 1.0, 1.0, 1.0],
        metallic: float = 0.0,
        roughness: float = 0.5,
        emissive_color: List[float] = [0.0, 0.0, 0.0, 1.0],
        opacity: float = 1.0,
        blend_mode: str = "opaque",
        use_texture_parameters: bool = True,
        overwrite: bool = False,
        compile: bool = False,
        save: bool = False,
    ) -> Dict[str, Any]:
        """Create a reusable master Material with standard technical-art parameters.

        The generated graph includes BaseColor, Metallic, Roughness, EmissiveColor,
        and Opacity parameters, plus optional texture parameters for BaseColor,
        Normal, ORM, and Emissive maps. Use material_wire_texture_set to wire
        actual texture assets into the graph after creation.

        Args:
            material_name: Material asset name, e.g. "M_Master_Prop"
            folder_path: Content Browser folder for the asset
            base_color: RGBA default BaseColor parameter
            metallic: Default Metallic scalar
            roughness: Default Roughness scalar
            emissive_color: RGBA default EmissiveColor parameter
            opacity: Default Opacity scalar
            blend_mode: "opaque" or "translucent"
            use_texture_parameters: Add standard texture parameter nodes
            overwrite: Delete/recreate an existing asset at the same path
            compile: Force a material shader compile before returning
            save: Save the asset package immediately

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            material_create_master(material_name="/Game/MCP_Test/M_Example")"""
        return _send("material_create_master", {
            "material_name": material_name,
            "folder_path": folder_path,
            "base_color": base_color,
            "metallic": metallic,
            "roughness": roughness,
            "emissive_color": emissive_color,
            "opacity": opacity,
            "blend_mode": blend_mode,
            "use_texture_parameters": use_texture_parameters,
            "overwrite": overwrite,
            "compile": compile,
            "save": save,
        })

    @mcp.tool()
    def material_create_function(
        ctx: Context,
        function_name: str,
        folder_path: str = "/Game/Materials/Functions",
        description: str = "",
        overwrite: bool = False,
        save: bool = True,
    ) -> Dict[str, Any]:
        """Create a Material Function asset and expose it to the material function library.

        Args:
            function_name: Function asset name, e.g. "MF_TriplanarTint"
            folder_path: Content Browser folder for the function
            description: Tooltip/description shown in the Material Editor
            overwrite: Delete/recreate an existing asset at the same path
            save: Save the asset package immediately

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            material_create_function(function_name="ExampleName")"""
        return _send("material_create_function", {
            "function_name": function_name,
            "folder_path": folder_path,
            "description": description,
            "overwrite": overwrite,
            "save": save,
        })

    @mcp.tool()
    def material_wire_texture_set(
        ctx: Context,
        material_path: str,
        base_color_texture: str = "",
        normal_texture: str = "",
        orm_texture: str = "",
        emissive_texture: str = "",
        compile: bool = False,
        save: bool = False,
    ) -> Dict[str, Any]:
        """Wire a standard texture set into a Material graph.

        ORM textures are assumed to pack Occlusion in R, Roughness in G, and
        Metallic in B. Empty texture paths are ignored.

        Args:
            material_path: Material asset path
            base_color_texture: Texture path wired to BaseColor
            normal_texture: Texture path wired to Normal
            orm_texture: Packed ORM texture path wired to AO/Roughness/Metallic
            emissive_texture: Texture path wired to EmissiveColor
            compile: Force a material shader compile before returning
            save: Save the material package immediately

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            material_wire_texture_set(material_path="/Game/MCP_Test/M_Example")"""
        return _send("material_wire_texture_set", {
            "material_path": material_path,
            "base_color_texture": base_color_texture,
            "normal_texture": normal_texture,
            "orm_texture": orm_texture,
            "emissive_texture": emissive_texture,
            "compile": compile,
            "save": save,
        })

    @mcp.tool()
    def material_create_instance_from_master(
        ctx: Context,
        instance_name: str,
        parent_material_path: str,
        folder_path: str = "/Game/Materials/Instances",
        overwrite: bool = False,
        save: bool = True,
    ) -> Dict[str, Any]:
        """Create a Material Instance Constant from a master Material.

        Args:
            instance_name: Material instance asset name, e.g. "MI_Prop_Red"
            parent_material_path: Parent material or material instance path
            folder_path: Content Browser folder for the instance
            overwrite: Delete/recreate an existing asset at the same path
            save: Save the asset package immediately

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            material_create_instance_from_master(instance_name="ExampleName", parent_material_path="/Game/MCP_Test/M_Example")"""
        return _send("material_create_instance_from_master", {
            "instance_name": instance_name,
            "parent_material_path": parent_material_path,
            "folder_path": folder_path,
            "overwrite": overwrite,
            "save": save,
        })

    @mcp.tool()
    def material_set_instance_parameters_bulk(
        ctx: Context,
        material_instance_path: str,
        scalar_parameters: Optional[Dict[str, float]] = None,
        vector_parameters: Optional[Dict[str, List[float]]] = None,
        texture_parameters: Optional[Dict[str, str]] = None,
        save: bool = True,
    ) -> Dict[str, Any]:
        """Set many Material Instance parameters in one bridge call.

        Args:
            material_instance_path: Material Instance Constant asset path
            scalar_parameters: Mapping of scalar parameter names to floats
            vector_parameters: Mapping of vector parameter names to RGBA arrays
            texture_parameters: Mapping of texture parameter names to texture paths
            save: Save the material instance package immediately

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            material_set_instance_parameters_bulk(material_instance_path="/Game/MCP_Test/M_Example")"""
        return _send("material_set_instance_parameters_bulk", {
            "material_instance_path": material_instance_path,
            "scalar_parameters": scalar_parameters or {},
            "vector_parameters": vector_parameters or {},
            "texture_parameters": texture_parameters or {},
            "save": save,
        })

    @mcp.tool()
    def texture_generate_orm(
        ctx: Context,
        output_name: str,
        folder_path: str = "/Game/Materials/Textures",
        occlusion_texture_path: str = "",
        roughness_texture_path: str = "",
        metallic_texture_path: str = "",
        occlusion_channel: str = "r",
        roughness_channel: str = "r",
        metallic_channel: str = "r",
        occlusion: float = 1.0,
        roughness: float = 0.5,
        metallic: float = 0.0,
        width: int = 4,
        height: int = 4,
        overwrite: bool = False,
        save: bool = True,
    ) -> Dict[str, Any]:
        """Generate a packed ORM Texture2D asset for technical-art material pipelines.

        The output packs Occlusion into R, Roughness into G, Metallic into B, and
        alpha to 255. If a source texture path is omitted or cannot be sampled,
        the matching flat default value is used.

        Args:
            output_name: Texture asset name, e.g. "T_Prop_ORM"
            folder_path: Content Browser folder for the generated texture
            occlusion_texture_path: Optional grayscale/source texture for R
            roughness_texture_path: Optional grayscale/source texture for G
            metallic_texture_path: Optional grayscale/source texture for B
            occlusion_channel: Source channel to sample, one of r/g/b/a
            roughness_channel: Source channel to sample, one of r/g/b/a
            metallic_channel: Source channel to sample, one of r/g/b/a
            occlusion: Flat fallback value 0.0-1.0
            roughness: Flat fallback value 0.0-1.0
            metallic: Flat fallback value 0.0-1.0
            width: Generated texture width when flat/default data is used
            height: Generated texture height when flat/default data is used
            overwrite: Delete/recreate an existing asset at the same path
            save: Save the generated texture package immediately

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            texture_generate_orm(output_name="ExampleName")"""
        return _send("texture_generate_orm", {
            "output_name": output_name,
            "folder_path": folder_path,
            "occlusion_texture_path": occlusion_texture_path,
            "roughness_texture_path": roughness_texture_path,
            "metallic_texture_path": metallic_texture_path,
            "occlusion_channel": occlusion_channel,
            "roughness_channel": roughness_channel,
            "metallic_channel": metallic_channel,
            "occlusion": occlusion,
            "roughness": roughness,
            "metallic": metallic,
            "width": width,
            "height": height,
            "overwrite": overwrite,
            "save": save,
        })

    @mcp.tool()
    def texture_audit_memory(
        ctx: Context,
        texture_path: str,
    ) -> Dict[str, Any]:
        """Inspect Texture2D size, compression, streaming flags, mips, and memory estimate.

        Args:
            texture_path: Texture2D asset path to audit

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            texture_audit_memory(texture_path="/Game/MCP_Test/T_Example")"""
        return _send("texture_audit_memory", {
            "texture_path": texture_path,
        })

    @mcp.tool()
    def vertex_paint_actor(
        ctx: Context,
        actor_name: str,
        component_name: str = "",
        color: List[float] = [1.0, 1.0, 1.0, 1.0],
        lod_index: int = 0,
        apply_to_all_vertices: bool = True,
        save: bool = False,
    ) -> Dict[str, Any]:
        """Apply component override vertex colors to a placed StaticMeshActor/component.

        Args:
            actor_name: Actor name or editor label
            component_name: Optional StaticMeshComponent name
            color: RGBA color array used for all vertices
            lod_index: LOD to paint
            apply_to_all_vertices: Must be true for this initial implementation
            save: Save the actor package/level if supported

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            vertex_paint_actor(actor_name="ExampleName")"""
        return _send("vertex_paint_actor", {
            "actor_name": actor_name,
            "component_name": component_name,
            "color": color,
            "lod_index": lod_index,
            "apply_to_all_vertices": apply_to_all_vertices,
            "save": save,
        })

    @mcp.tool()
    def mesh_audit_uv_channels(
        ctx: Context,
        static_mesh_path: str,
    ) -> Dict[str, Any]:
        """Audit StaticMesh LODs for UV channel counts, vertex counts, and triangles.

        Args:
            static_mesh_path: StaticMesh asset path to inspect

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            mesh_audit_uv_channels(static_mesh_path="/Game/MCP_Test/Example")"""
        return _send("mesh_audit_uv_channels", {
            "static_mesh_path": static_mesh_path,
        })

    @mcp.tool()
    def shader_analyze_complexity(
        ctx: Context,
        material_path: str,
        include_recommendations: bool = True,
    ) -> Dict[str, Any]:
        """Estimate Material shader complexity from graph structure and risk flags.

        This is a fast technical-art audit, not a compiled instruction count.
        Pair it with renderer_capture_viewmode or shader_visualize_overdraw for
        scene-level visual validation.

        Args:
            material_path: Material or Material Instance asset path to inspect
            include_recommendations: Include optimization suggestions

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            shader_analyze_complexity(material_path="/Game/MCP_Test/M_Example")"""
        return _send("shader_analyze_complexity", {
            "material_path": material_path,
            "include_recommendations": include_recommendations,
        })

    @mcp.tool()
    def renderer_capture_viewmode(
        ctx: Context,
        viewmode: str,
        filepath: str = "",
        restore_viewmode: bool = False,
    ) -> Dict[str, Any]:
        """Switch the active level viewport to a diagnostic viewmode and save a PNG.

        Supported viewmodes include lit, unlit, wireframe, shader_complexity,
        quad_overdraw, shader_complexity_with_quad_overdraw,
        material_texture_scale_accuracy, and required_texture_resolution.

        Args:
            viewmode: Diagnostic viewmode to capture
            filepath: Optional output .png path; defaults to Saved/MCP/Viewmodes
            restore_viewmode: Restore the previous viewport mode after capture

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            renderer_capture_viewmode(viewmode="Example")"""
        return _send("renderer_capture_viewmode", {
            "viewmode": viewmode,
            "filepath": filepath,
            "restore_viewmode": restore_viewmode,
        })

    @mcp.tool()
    def shader_visualize_overdraw(
        ctx: Context,
        viewmode: str = "shader_complexity_with_quad_overdraw",
        filepath: str = "",
        restore_viewmode: bool = False,
    ) -> Dict[str, Any]:
        """Capture an overdraw-focused viewport visualization for material review.

        Args:
            viewmode: shader_complexity_with_quad_overdraw or quad_overdraw
            filepath: Optional output .png path; defaults to Saved/MCP/Viewmodes
            restore_viewmode: Restore the previous viewport mode after capture

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            shader_visualize_overdraw()"""
        return _send("shader_visualize_overdraw", {
            "viewmode": viewmode,
            "filepath": filepath,
            "restore_viewmode": restore_viewmode,
        })

    @mcp.tool()
    def performance_audit_gpu(
        ctx: Context,
        include_memory: bool = True,
        include_viewport: bool = True,
    ) -> Dict[str, Any]:
        """Capture a lightweight editor GPU/performance audit snapshot.

        Returns RHI adapter details, memory stats, active viewport state, and
        scene/component counts. Use Unreal's ProfileGPU for pass timings.

        Args:
            include_memory: Include process/platform memory stats
            include_viewport: Include active viewport dimensions and viewmode

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            performance_audit_gpu()"""
        return _send("performance_audit_gpu", {
            "include_memory": include_memory,
            "include_viewport": include_viewport,
        })

    @mcp.tool()
    def set_material_on_actor(
        ctx: Context,
        actor_name: str,
        material_path: str,
        element_index: int = 0
    ) -> Dict[str, Any]:
        """Set a Material on a static mesh actor in the level.

        This corresponds to the "Set Material" node used in Ch. 5 of the book,
        where the CylinderTarget changes its Material when hit.

        Args:
            actor_name: Name of the actor in the level (e.g., "CylinderTarget")
            material_path: Asset path to the Material (e.g., "/Game/Materials/M_TargetRed")
            element_index: Material slot index (0 = first material slot)

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            set_material_on_actor(actor_name="ExampleName", material_path="/Game/MCP_Test/M_Example")"""
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
        """Add a "Set Material" node to a Blueprint event graph triggered by an event.

        This creates the core gameplay interaction from Ch. 5: detecting a hit on
        an actor and swapping its material (e.g., cylinder turns red when shot).

        Args:
            blueprint_name: Target Blueprint (e.g., "BP_CylinderTarget")
            component_name: Mesh component name (e.g., "StaticMeshComponent")
            material_path: Material asset path (e.g., "/Game/Materials/M_TargetRed")
            event_name: Event that triggers the material change ("ReceiveHit", "ReceiveBeginPlay")
            node_position: [X, Y] position in graph

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            add_set_material_node(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent", material_path="/Game/MCP_Test/M_Example")"""
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
        """Create a Dynamic Material Instance from a source Material in a Blueprint.

        Dynamic Material Instances allow runtime modification of material parameters
        (color, opacity, scalar values) without creating separate material assets.
        Used extensively in game HUDs, pickups, and interactive props.

        Args:
            blueprint_name: Blueprint to add the node to
            component_name: Mesh component to create the dynamic instance on
            source_material_path: Base material asset path
            variable_name: Variable name to store the dynamic instance reference
            node_position: [X, Y] graph position

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            create_dynamic_material_instance(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent", source_material_path="/Game/MCP_Test/M_Example")"""
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
        """Add a SetVectorParameterValue node to change a material color at runtime.

        This is the runtime equivalent of double-clicking the VectorParameter node
        in the Material Editor (Ch. 5). Use this to dynamically change an actor's color.

        Args:
            blueprint_name: Blueprint containing the dynamic material reference
            dynamic_material_variable: Variable name holding the Dynamic Material Instance
            parameter_name: Material parameter name (e.g., "Color")
            color_value: RGBA values [R, G, B, A]
            node_position: [X, Y] graph position

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            add_set_vector_parameter_value_node(blueprint_name="/Game/MCP_Test/BP_Example", dynamic_material_variable="/Game/MCP_Test/M_Example", parameter_name="ExampleName")"""
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
        """Add a SetScalarParameterValue node to change a material float parameter at runtime.

        Useful for animating material effects like opacity fade-in, glow intensity,
        dissolve transitions, etc.

        Args:
            blueprint_name: Blueprint containing the dynamic material reference
            dynamic_material_variable: Variable name holding the Dynamic Material Instance
            parameter_name: Material scalar parameter name (e.g., "Opacity", "Metallic")
            scalar_value: Float value to set
            node_position: [X, Y] graph position

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            add_set_scalar_parameter_value_node(blueprint_name="/Game/MCP_Test/BP_Example", dynamic_material_variable="/Game/MCP_Test/M_Example", parameter_name="ExampleName")"""
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
        """Set up a full hit-detection + material swap interaction as in Ch. 5.

        Creates the complete "cylinder target" interaction:
        1. Event Hit -> track hit count
        2. First hit: swap to hit material
        3. Second+ hit: spawn explosion effect + sound + destroy actor

        Args:
            blueprint_name: Blueprint to modify (e.g., "BP_CylinderTarget")
            mesh_component: Static mesh component name
            default_material_path: Original material path
            hit_material_path: Material to apply on first hit (e.g., M_TargetRed)
            hit_count_to_destroy: Number of hits before destruction (default 2)

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            setup_hit_material_swap(blueprint_name="/Game/MCP_Test/BP_Example")"""
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
        """Add a SpawnEmitterAtLocation node to trigger particle effects in a Blueprint.

        From Ch. 6 (sound and particle effects). Used to spawn explosion effects,
        dust, sparks, etc. when actors are hit or destroyed.

        Args:
            blueprint_name: Target Blueprint
            particle_system_path: Particle System or Niagara System asset path
            trigger_event: Event that triggers the emitter spawn
            node_position: [X, Y] graph position

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            add_spawn_emitter_at_location_node(blueprint_name="/Game/MCP_Test/BP_Example")"""
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
        """Add a PlaySoundAtLocation node to a Blueprint for audio feedback.

        From Ch. 6 (Adding sound and particle effects). Plays a sound cue
        at the actor's world location when called.

        Args:
            blueprint_name: Target Blueprint
            sound_asset_path: Sound asset path (e.g., "/Game/FPWeapon/Audio/FirstPersonTemplateWeaponFire02")
            volume_multiplier: Volume scale (1.0 = normal)
            pitch_multiplier: Pitch scale (1.0 = normal)
            node_position: [X, Y] graph position

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            add_play_sound_at_location_node(blueprint_name="/Game/MCP_Test/BP_Example")"""
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
        """Set collision and visibility settings on a Blueprint component.

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

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            set_collision_settings(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent")"""
        return _send("set_collision_settings", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "collision_preset": collision_preset,
            "generate_overlap_events": generate_overlap_events,
            "hidden_in_game": hidden_in_game
        })

    @mcp.tool()
    def add_spawn_niagara_at_location_node(
        ctx: Context,
        blueprint_name: str,
        graph_name: str = "EventGraph",
        niagara_system_path: str = "",
        node_position: List[float] = None,
    ) -> Dict[str, Any]:
        """Add a 'Spawn System At Location' node for a Niagara particle system.

        Use this to fire a one-shot Niagara VFX effect at a world location from
        within a Blueprint graph (e.g., spawn explosion on hit, footstep dust).

        Args:
            blueprint_name: Blueprint to add the node to
            graph_name: Graph to add the node in (default: "EventGraph")
            niagara_system_path: Asset path to the NS_ asset
                                 (e.g., "/Game/VFX/NS_Explosion")
            node_position: Optional [X, Y] graph position

        Returns:
            Dict with node_id and success flag

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            add_spawn_niagara_at_location_node(blueprint_name="/Game/MCP_Test/BP_Example")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_spawn_niagara_at_location_node", {
                "blueprint_name": blueprint_name,
                "graph_name": graph_name,
                "niagara_system_path": niagara_system_path,
                "node_position": node_position or [0, 0],
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_sequencer_track(
        ctx: Context,
        sequence_path: str,
        actor_name: str,
        track_type: str,
        keyframes: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Add or update a track on a Level Sequence (Sequencer) asset.

        Use this to animate actors in a cutscene/cinematic: set transform keys,
        visibility, material parameter, or audio tracks for a specific actor.

        Args:
            sequence_path: Asset path to the LS_ asset
                           (e.g., "/Game/Cinematics/LS_Intro")
            actor_name: Name of the actor to track
            track_type: Track type string, e.g.:
                        "Transform", "Visibility", "MaterialParameter", "Audio"
            keyframes: Optional list of keyframe dicts, e.g.:
                       [{"time": 0.0, "value": [0,0,0]},
                        {"time": 1.0, "value": [0,0,100]}]

        Returns:
            Dict with success flag and track info

        KB: see knowledge_base/08_MATERIALS_AND_RENDERING.md#overview
        Example:
            set_sequencer_track(sequence_path="/Game/MCP_Test/Example", actor_name="ExampleName", track_type="Example")"""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params: Dict[str, Any] = {
                "sequence_path": sequence_path,
                "actor_name": actor_name,
                "track_type": track_type,
            }
            if keyframes:
                params["keyframes"] = keyframes
            return unreal.send_command("set_sequencer_track", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("Material tools registered successfully")
