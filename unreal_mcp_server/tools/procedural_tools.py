"""
Procedural Generation Tools for Unreal MCP.
Covers Chapter 19 (Procedural Generation) from the Blueprint book.

Provides tools for:
- Instanced Static Mesh component (optimized batch rendering)
- Construction Script procedural generation (BP_ProceduralMeshes)
- Blueprint Spline component (BP_SplinePlacement - place instances along a path)
- Spline Mesh component (deform a Static Mesh along a spline)
- Editor Utility Blueprints (ActorActionUtility, AssetActionUtility)
- For Loop node in Construction Script context
- Add Instance function for Instanced Static Mesh
- Get Selection Set (editor scripting)
- NavMesh Bounds Volume placement
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


def register_procedural_tools(mcp: FastMCP):

    @mcp.tool()
    def create_procedural_mesh_blueprint(
        ctx: Context,
        name: str = "BP_ProceduralMeshes",
        static_mesh_path: str = "/Game/StarterContent/Props/SM_Chair",
        default_instances_per_row: int = 1,
        default_number_of_rows: int = 1,
        default_space_between_instances: float = 100.0,
        default_space_between_rows: float = 150.0,
        folder_path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a procedural mesh placement Blueprint using Construction Script.

        From Ch. 19: Creates BP_ProceduralMeshes that uses an Instanced Static Mesh
        component and nested For Loops in the Construction Script to place rows of
        static mesh instances. All parameters are Instance Editable so level designers
        can configure them per instance.

        The result is a Blueprint that, when placed in a level, automatically generates
        a grid of mesh instances (e.g., rows of chairs, plants, lights).

        Args:
            name: Blueprint name (e.g., \"BP_ProceduralMeshes\")
            static_mesh_path: Default Static Mesh asset path
            default_instances_per_row: Number of instances per row
            default_number_of_rows: Number of rows
            default_space_between_instances: Spacing between instances in a row (UE units)
            default_space_between_rows: Spacing between rows (UE units)
            folder_path: Content browser folder
        """
        return _send("create_procedural_mesh_blueprint", {
            "name": name,
            "static_mesh_path": static_mesh_path,
            "default_instances_per_row": default_instances_per_row,
            "default_number_of_rows": default_number_of_rows,
            "default_space_between_instances": default_space_between_instances,
            "default_space_between_rows": default_space_between_rows,
            "folder_path": folder_path
        })

    @mcp.tool()
    def create_spline_placement_blueprint(
        ctx: Context,
        name: str = "BP_SplinePlacement",
        static_mesh_path: str = "/Engine/BasicShapes/Arrow",
        default_space_between_instances: float = 100.0,
        folder_path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a Blueprint that places Static Mesh instances along a Spline component.

        From Ch. 19: Creates BP_SplinePlacement with:
        - Spline component (editable in Level Editor by dragging spline points)
        - Instanced Static Mesh component
        - CalculateNumberOfInstances macro (GetSplineLength / SpaceBetweenInstances)
        - Construction Script that iterates along the spline, placing instances
          at each distance interval using GetLocationAtDistanceAlongSpline +
          GetRotationAtDistanceAlongSpline

        Args:
            name: Blueprint name
            static_mesh_path: Default Static Mesh asset path for instances
            default_space_between_instances: Distance between instances along the spline
            folder_path: Content browser folder
        """
        return _send("create_spline_placement_blueprint", {
            "name": name,
            "static_mesh_path": static_mesh_path,
            "default_space_between_instances": default_space_between_instances,
            "folder_path": folder_path
        })

    @mcp.tool()
    def add_instanced_static_mesh_component(
        ctx: Context,
        blueprint_name: str,
        component_name: str = "InstancedStaticMesh",
        static_mesh_path: str = "",
        attach_to_root: bool = True
    ) -> Dict[str, Any]:
        """
        Add an Instanced Static Mesh component to a Blueprint.

        From Ch. 19: The Instanced Static Mesh (ISM) component is optimized to render
        many copies of the same mesh efficiently. It's the core tool for procedural
        generation and environment population.

        Note: There is also HISM (Hierarchical ISM) for meshes with LOD.

        Args:
            blueprint_name: Blueprint to add the component to
            component_name: Component name in the Components panel
            static_mesh_path: Static Mesh asset to assign (can be set later)
            attach_to_root: Attach to root component (True) or as child
        """
        return _send("add_component_to_blueprint", {
            "blueprint_name": blueprint_name,
            "component_type": "InstancedStaticMeshComponent",
            "component_name": component_name,
            "location": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
            "component_properties": {
                "StaticMesh": static_mesh_path
            } if static_mesh_path else {}
        })

    @mcp.tool()
    def add_spline_component(
        ctx: Context,
        blueprint_name: str,
        component_name: str = "Spline",
        num_points: int = 2
    ) -> Dict[str, Any]:
        """
        Add a Spline component to a Blueprint.

        From Ch. 19: The Spline component defines a curved path in 3D space.
        Its points can be edited in the Level Editor (Add Spline Point Here,
        translate and rotate points). Used with GetLocationAtDistanceAlongSpline
        and GetRotationAtDistanceAlongSpline for instance placement.

        Args:
            blueprint_name: Blueprint to add the Spline component to
            component_name: Component name
            num_points: Initial number of spline points (minimum 2)
        """
        return _send("add_component_to_blueprint", {
            "blueprint_name": blueprint_name,
            "component_type": "SplineComponent",
            "component_name": component_name,
            "location": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
            "component_properties": {}
        })

    @mcp.tool()
    def add_spline_mesh_component(
        ctx: Context,
        blueprint_name: str,
        component_name: str = "SplineMesh",
        static_mesh_path: str = "",
        start_pos: List[float] = [0.0, 0.0, 0.0],
        end_pos: List[float] = [100.0, 0.0, 0.0]
    ) -> Dict[str, Any]:
        """
        Add a Spline Mesh component to deform a Static Mesh along a two-point spline.

        From Ch. 19: The Spline Mesh component deforms a Static Mesh between two
        control points. Use SetStartAndEnd in the Construction Script to define the
        shape. Perfect for creating curved pipes, rails, fences, etc.

        Args:
            blueprint_name: Blueprint to add the component to
            component_name: Component name
            static_mesh_path: Static Mesh asset to deform
            start_pos: Start point world position
            end_pos: End point world position
        """
        return _send("add_component_to_blueprint", {
            "blueprint_name": blueprint_name,
            "component_type": "SplineMeshComponent",
            "component_name": component_name,
            "location": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
            "component_properties": {
                "StaticMesh": static_mesh_path,
                "StartPosition": start_pos,
                "EndPosition": end_pos
            }
        })

    @mcp.tool()
    def create_editor_utility_blueprint(
        ctx: Context,
        name: str,
        utility_type: str = "ActorActionUtility",
        functions: List[Dict[str, Any]] = None,
        folder_path: str = "/Game/EditorUtilities"
    ) -> Dict[str, Any]:
        """
        Create an Editor Utility Blueprint that runs in the Unreal Editor.

        From Ch. 19: Editor Utility Blueprints can manipulate Assets and Actors
        in Edit Mode (not during Play). They appear as right-click context menu
        options in the Level Editor or Content Browser.

        Types:
        - \"ActorActionUtility\": manipulate selected Actors in the Level Editor.
          Functions appear under Right-click > Scripted Actor Actions.
        - \"AssetActionUtility\": manipulate Assets in the Content Browser.
          Functions appear under Right-click > Scripted Asset Actions.
        - \"EditorUtilityBlueprint\": general editor scripting.

        Available editor scripting nodes include:
        - GetSelectionSet: get selected Actors
        - GetActorLocation/SetActorLocation
        - EditorScripting category functions

        Args:
            name: Blueprint name (e.g., \"BPU_ActorAction\")
            utility_type: \"ActorActionUtility\", \"AssetActionUtility\", or \"EditorUtilityBlueprint\"
            functions: Function definitions [{\"name\", \"inputs\", \"outputs\"}]
            folder_path: Content browser folder
        """
        if functions is None:
            functions = []

        result = _send("create_editor_utility_blueprint", {
            "name": name,
            "utility_type": utility_type,
            "folder_path": folder_path
        })

        if not result.get("success", True):
            return result

        for func in functions:
            _send("add_function_to_blueprint", {
                "blueprint_name": name,
                "function_name": func["name"],
                "inputs": func.get("inputs", []),
                "outputs": func.get("outputs", [])
            })

        _send("compile_blueprint", {"blueprint_name": name})
        return {"success": True, "message": f"Editor Utility Blueprint '{name}' ({utility_type}) created"}

    @mcp.tool()
    def create_align_actors_utility(
        ctx: Context,
        name: str = "BPU_AlignActors",
        folder_path: str = "/Game/EditorUtilities"
    ) -> Dict[str, Any]:
        """
        Create the AlignOnXAxis Editor Utility Blueprint from Ch. 19.

        Creates BPU_AlignActors (ActorActionUtility) with an AlignOnXAxis function:
        1. GetSelectionSet -> get array of selected actors
        2. Get Location X of first actor (index 0)
        3. ForEachLoop -> SetActorLocation X on each selected actor

        Right-click multiple actors in the level -> Scripted Actor Actions -> AlignOnXAxis.

        Args:
            name: Blueprint name
            folder_path: Content browser folder
        """
        return _send("create_align_actors_utility", {
            "name": name,
            "folder_path": folder_path
        })

    @mcp.tool()
    def add_get_spline_length_node(
        ctx: Context,
        blueprint_name: str,
        spline_component_variable: str = "Spline",
        node_position: List[int] = [300, 0]
    ) -> Dict[str, Any]:
        """
        Add a GetSplineLength node to get the total length of a Spline.

        From Ch. 19: Used in the CalculateNumberOfInstances macro to determine
        how many instances fit along the spline at a given spacing.

        Args:
            blueprint_name: Blueprint containing the Spline component
            spline_component_variable: Spline component reference name
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": spline_component_variable,
            "function_name": "GetSplineLength",
            "params": {},
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_location_at_distance_along_spline_node(
        ctx: Context,
        blueprint_name: str,
        spline_component_variable: str = "Spline",
        coordinate_space: str = "Local",
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add a GetLocationAtDistanceAlongSpline node.

        From Ch. 19: Returns the world or local location at a specified distance
        along the spline. Used in Construction Script to position instances
        at regular intervals along the spline path.

        Args:
            blueprint_name: Blueprint to add the node to
            spline_component_variable: Spline component reference name
            coordinate_space: \"Local\" or \"World\"
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": spline_component_variable,
            "function_name": "GetLocationAtDistanceAlongSpline",
            "params": {"CoordinateSpace": coordinate_space},
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_rotation_at_distance_along_spline_node(
        ctx: Context,
        blueprint_name: str,
        spline_component_variable: str = "Spline",
        coordinate_space: str = "Local",
        node_position: List[int] = [400, 100]
    ) -> Dict[str, Any]:
        """
        Add a GetRotationAtDistanceAlongSpline node.

        From Ch. 19: Returns the rotation at a specified distance along the spline.
        Paired with GetLocationAtDistanceAlongSpline to orient instances so they
        face along the spline direction.

        Args:
            blueprint_name: Blueprint to add the node to
            spline_component_variable: Spline component reference name
            coordinate_space: \"Local\" or \"World\"
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": spline_component_variable,
            "function_name": "GetRotationAtDistanceAlongSpline",
            "params": {"CoordinateSpace": coordinate_space},
            "node_position": node_position
        })

    @mcp.tool()
    def add_instanced_mesh_add_instance_node(
        ctx: Context,
        blueprint_name: str,
        instanced_mesh_variable: str = "InstancedStaticMesh",
        node_position: List[int] = [500, 0]
    ) -> Dict[str, Any]:
        """
        Add an AddInstance node for an Instanced Static Mesh component.

        From Ch. 19: The core of procedural generation. AddInstance takes an
        Instance Transform (Location, Rotation, Scale) and adds a new mesh
        instance at that transform. Called in loops to batch-create many instances.

        Args:
            blueprint_name: Blueprint to add the node to
            instanced_mesh_variable: Instanced Static Mesh component variable name
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": instanced_mesh_variable,
            "function_name": "AddInstance",
            "params": {},
            "node_position": node_position
        })

    @mcp.tool()
    def place_navmesh_bounds_volume(
        ctx: Context,
        location: List[float] = [0.0, 0.0, 460.0],
        scale: List[float] = [20.0, 44.0, 7.0]
    ) -> Dict[str, Any]:
        """
        Place a NavMesh Bounds Volume in the current level.

        From Ch. 9: The NavMesh Bounds Volume defines the navigable area for AI.
        The editor automatically generates the navigation mesh within this volume.
        Press P in the viewport to toggle NavMesh visibility (green overlay).

        Scale the volume to cover all walkable surfaces. AI agents can only
        navigate within the bounds of this volume.

        Args:
            location: [X, Y, Z] world location for the volume center
            scale: [X, Y, Z] scale to cover the navigable area
        """
        return _send("spawn_actor", {
            "name": "NavMeshBoundsVolume",
            "type": "NavMeshBoundsVolume",
            "location": location,
            "rotation": [0, 0, 0]
        })

    @mcp.tool()
    def add_construction_script_for_loop(
        ctx: Context,
        blueprint_name: str,
        first_index: int = 1,
        last_index_variable: str = "NumberOfRows",
        nested: bool = False,
        node_position: List[int] = [300, 0]
    ) -> Dict[str, Any]:
        """
        Add a For Loop node in a Blueprint's Construction Script.

        From Ch. 19: Used in BP_ProceduralMeshes Construction Script to iterate
        over rows and instances. Nested For Loops create 2D grids of instances.

        The Construction Script runs in the Editor when an instance is placed
        or its properties are changed, making it perfect for procedural generation.

        Args:
            blueprint_name: Blueprint to add the node to
            first_index: Starting index (usually 1 for 1-based counting)
            last_index_variable: Variable providing the max loop count
            nested: Whether this is a nested (inner) loop
            node_position: [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "KismetSystemLibrary",
            "function_name": "ForLoop",
            "params": {
                "FirstIndex": first_index,
                "LastIndex": last_index_variable
            },
            "node_position": node_position,
            "graph": "ConstructionScript"
        })

    logger.info("Procedural generation tools registered successfully")
