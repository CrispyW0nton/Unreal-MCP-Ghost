"""
Physics, Math, and Trace Tools for Unreal MCP.

Covers Chapter 14 (Math and Trace Nodes) from the Blueprint book:
- World and Relative Transforms: GetActorLocation/Rotation/Scale, SetActorLocation/Rotation/Scale,
  AddActorWorldOffset/Rotation, GetRelativeLocation/SetRelativeLocation (components)
- Vector Math Nodes: Add, Subtract, Multiply, Normalize, Dot Product, Cross Product,
  Vector Length, Get Unit Direction Vector, GetActorForwardVector, etc.
- Line Trace Nodes: LineTraceByChannel, LineTraceForObjects, MultiLineTrace variants
- Shape Trace Nodes: SphereTrace, CapsuleTrace, BoxTrace (by channel / by objects)
- Break Hit Result: decompose Hit Result structure
- Debug Draw Lines, Points, Spheres in viewport
- Collision: Set Collision Profile Name, Set Generate Overlap Events, Set Simulate Physics
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


def register_physics_tools(mcp: FastMCP):

    # ─── Transform Nodes ────────────────────────────────────────────────────────

    @mcp.tool()
    def add_get_actor_location_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Actor Location' node returning a Vector (world location).

        Ch.14: The Location variable of Transform is type Vector (X,Y,Z in cm).
        Use this to read where an actor is in world space.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "GetActorLocation",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_set_actor_location_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set Actor Location' node to teleport an actor to a new Vector.

        Ch.14: Sets New Location directly; use AddActorWorldOffset for relative moves.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "SetActorLocation",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_actor_world_offset_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an 'Add Actor World Offset' node - moves actor by DeltaLocation Vector.

        Ch.14: AddActorWorldOffset uses Delta Location to modify the current location.
        More appropriate than SetActorLocation for incremental movement each tick.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "AddActorWorldOffset",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_get_actor_rotation_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Actor Rotation' node returning a Rotator (Pitch, Yaw, Roll in degrees).

        Ch.14: The Rotation variable of Transform is type Rotator.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "GetActorRotation",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_set_actor_rotation_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set Actor Rotation' node to assign a new Rotator.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "SetActorRotation",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_actor_world_rotation_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an 'Add Actor World Rotation' node - rotates actor by DeltaRotation.

        Ch.14: AddActorWorldRotation adds the Delta Rotation to the current rotation.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "AddActorWorldRotation",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_get_actor_scale_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Actor Scale 3D' node returning the actor's scale as a Vector.

        Ch.14: Scale variable has X, Y, Z values. Use SetActorScale3D to modify.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "GetActorScale3D",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_set_actor_scale_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set Actor Scale 3D' node to set the actor's 3D scale.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "SetActorScale3D",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_get_relative_location_node(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Relative Location' node for a specific component.

        Ch.14: Component transforms are relative to their parent component.
        DefaultSceneRoot is the actor root; all sub-components have relative transforms.

        Args:
            blueprint_name: Blueprint name
            component_name: Component to get relative location from
            node_position: Optional [X, Y] graph position
        """
        return _send("add_component_function_node", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "function_name": "GetRelativeLocation",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_set_relative_location_node(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set Relative Location' node to move a component relative to its parent.

        Ch.14: Relative location is local to the component's parent transform.

        Args:
            blueprint_name: Blueprint name
            component_name: Component to move
            node_position: Optional [X, Y] graph position
        """
        return _send("add_component_function_node", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "function_name": "SetRelativeLocation",
            "node_position": node_position or [0, 0]
        })

    # ─── Vector Math Nodes ──────────────────────────────────────────────────────

    @mcp.tool()
    def add_vector_add_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Vector + Vector addition node.

        Ch.14: couch_location = character_location + movement_vector
        Adds each element: (X1+X2, Y1+Y2, Z1+Z2).

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_math_node", {
            "blueprint_name": blueprint_name,
            "operation": "Add",
            "operand_type": "Vector",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_vector_subtract_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Vector - Vector subtraction node.

        Ch.14: movement = destination - start_point. Subtracts element-wise.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_math_node", {
            "blueprint_name": blueprint_name,
            "operation": "Subtract",
            "operand_type": "Vector",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_vector_multiply_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a Vector * Float multiplication node.

        Ch.14: To find the opposite vector, multiply by -1 (e.g., backward = forward * -1).

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_math_node", {
            "blueprint_name": blueprint_name,
            "operation": "Multiply",
            "operand_type": "Vector",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_normalize_vector_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Normalize' vector node - returns a unit vector (length = 1).

        Ch.14: Normalization gives direction without magnitude.
        Used before multiplying by speed to get direction-based movement.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": "Normal",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_vector_length_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Vector Length' node - returns the magnitude/distance of a vector.

        Ch.14: Length = sqrt(X*X + Y*Y + Z*Z). Use to measure distances.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": "VSize",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_dot_product_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Dot Product' node between two vectors.

        Ch.14: Dot product = X1*X2 + Y1*Y2 + Z1*Z2.
        Returns 1 if parallel, 0 if perpendicular, -1 if opposite.
        Useful for checking if something is in front of/behind actor.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": "Dot_VectorVector",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_cross_product_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Cross Product' node between two vectors.

        Ch.14: Returns a vector perpendicular to both inputs.
        Useful for computing normals and right-angle vectors.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": "Cross_VectorVector",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_get_forward_vector_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Actor Forward Vector' node.

        Ch.14: Returns normalized forward direction vector of the actor.
        Multiply by speed to move in the actor's forward direction.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "GetActorForwardVector",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_get_right_vector_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Actor Right Vector' node.

        Ch.14: Returns normalized right direction vector of the actor.
        Multiply by -1 to get the left vector.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "GetActorRightVector",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_get_up_vector_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Actor Up Vector' node.

        Ch.14: Returns normalized up direction vector of the actor.
        Multiply by -1 to get the down vector.

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "GetActorUpVector",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_get_unit_direction_vector_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Unit Direction Vector' node - normalized direction from A to B.

        Ch.14: Normalized (unit length) vector pointing from From to To.
        Equivalent to normalize(To - From).

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetMathLibrary",
            "function_name": "GetDirectionUnitVector",
            "node_position": node_position or [0, 0]
        })

    # ─── Trace Nodes ────────────────────────────────────────────────────────────

    @mcp.tool()
    def add_line_trace_by_channel_node(
        ctx: Context,
        blueprint_name: str,
        trace_channel: str = "Visibility",
        draw_debug: str = "None",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Line Trace By Channel' node.

        Ch.14: Tests for collisions along a line using Visibility or Camera channel.
        Returns a single Hit Result (first actor hit).
        Use break_hit_result_node to access hit data (Location, Hit Actor, Impact Normal, etc.)

        Args:
            blueprint_name: Blueprint name
            trace_channel: "Visibility" or "Camera"
            draw_debug: "None", "ForOneFrame", "ForDuration", "Persistent"
            node_position: Optional [X, Y] graph position
        """
        return _send("add_line_trace_by_channel_node", {
            "blueprint_name": blueprint_name,
            "trace_channel": trace_channel,
            "draw_debug": draw_debug,
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_multi_line_trace_by_channel_node(
        ctx: Context,
        blueprint_name: str,
        trace_channel: str = "Visibility",
        draw_debug: str = "None",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Multi Line Trace By Channel' node - returns ALL actors hit as array.

        Ch.14: MultiLineTraceByChannel is more expensive but returns every hit
        along the trace line as an array of Hit Result structures.

        Args:
            blueprint_name: Blueprint name
            trace_channel: "Visibility" or "Camera"
            draw_debug: "None", "ForOneFrame", "ForDuration", "Persistent"
            node_position: Optional [X, Y] graph position
        """
        return _send("add_multi_line_trace_by_channel_node", {
            "blueprint_name": blueprint_name,
            "trace_channel": trace_channel,
            "draw_debug": draw_debug,
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_line_trace_for_objects_node(
        ctx: Context,
        blueprint_name: str,
        object_types: List[str] = None,
        draw_debug: str = "None",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Line Trace For Objects' node - traces for specific object types.

        Ch.14: LineTraceForObjects filters by Object Type instead of channel.
        Object types: WorldStatic, WorldDynamic, Pawn, PhysicsBody, Vehicle,
        Destructible, Projectile. Returns first hit matching an object type.

        Args:
            blueprint_name: Blueprint name
            object_types: List of object types to trace against
            draw_debug: "None", "ForOneFrame", "ForDuration", "Persistent"
            node_position: Optional [X, Y] graph position
        """
        return _send("add_line_trace_for_objects_node", {
            "blueprint_name": blueprint_name,
            "object_types": object_types or ["WorldStatic", "WorldDynamic", "Pawn"],
            "draw_debug": draw_debug,
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_multi_line_trace_for_objects_node(
        ctx: Context,
        blueprint_name: str,
        object_types: List[str] = None,
        draw_debug: str = "None",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Multi Line Trace For Objects' node - returns all hits for object types.

        Ch.14: Returns array of Hit Results for all matching objects along the trace line.

        Args:
            blueprint_name: Blueprint name
            object_types: List of object types to trace against
            draw_debug: "None", "ForOneFrame", "ForDuration", "Persistent"
            node_position: Optional [X, Y] graph position
        """
        return _send("add_multi_line_trace_for_objects_node", {
            "blueprint_name": blueprint_name,
            "object_types": object_types or ["WorldStatic", "WorldDynamic", "Pawn"],
            "draw_debug": draw_debug,
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_sphere_trace_for_objects_node(
        ctx: Context,
        blueprint_name: str,
        radius: float = 32.0,
        object_types: List[str] = None,
        draw_debug: str = "None",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Sphere Trace For Objects' node - sphere-shaped collision test.

        Ch.14: Shape traces test along a volume instead of a line. More expensive
        but detects wider areas. SphereTraceForObjects sweeps a sphere.

        Args:
            blueprint_name: Blueprint name
            radius: Sphere radius in Unreal units (cm)
            object_types: Object types to detect
            draw_debug: Debug visualization type
            node_position: Optional [X, Y] graph position
        """
        return _send("add_shape_trace_node", {
            "blueprint_name": blueprint_name,
            "shape_type": "Sphere",
            "trace_mode": "ForObjects",
            "radius": radius,
            "object_types": object_types or ["WorldStatic", "WorldDynamic", "Pawn"],
            "draw_debug": draw_debug,
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_sphere_trace_by_channel_node(
        ctx: Context,
        blueprint_name: str,
        radius: float = 32.0,
        trace_channel: str = "Visibility",
        draw_debug: str = "None",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Sphere Trace By Channel' node - sphere sweep using trace channel.

        Ch.14: SphereTraceByChannel uses Visibility or Camera channel to filter hits.

        Args:
            blueprint_name: Blueprint name
            radius: Sphere radius in cm
            trace_channel: "Visibility" or "Camera"
            draw_debug: Debug visualization type
            node_position: Optional [X, Y] graph position
        """
        return _send("add_shape_trace_node", {
            "blueprint_name": blueprint_name,
            "shape_type": "Sphere",
            "trace_mode": "ByChannel",
            "radius": radius,
            "trace_channel": trace_channel,
            "draw_debug": draw_debug,
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_capsule_trace_by_channel_node(
        ctx: Context,
        blueprint_name: str,
        radius: float = 32.0,
        half_height: float = 88.0,
        trace_channel: str = "Visibility",
        draw_debug: str = "None",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Capsule Trace By Channel' node - capsule-shaped sweep trace.

        Ch.14: CapsuleTrace is more expensive than LineTrace but covers a capsule volume,
        useful for character-sized sweeps (characters use capsules for collision).

        Args:
            blueprint_name: Blueprint name
            radius: Capsule radius
            half_height: Half-height of the capsule
            trace_channel: "Visibility" or "Camera"
            draw_debug: Debug visualization type
            node_position: Optional [X, Y] graph position
        """
        return _send("add_shape_trace_node", {
            "blueprint_name": blueprint_name,
            "shape_type": "Capsule",
            "trace_mode": "ByChannel",
            "radius": radius,
            "half_height": half_height,
            "trace_channel": trace_channel,
            "draw_debug": draw_debug,
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_box_trace_by_channel_node(
        ctx: Context,
        blueprint_name: str,
        half_size: List[float] = None,
        trace_channel: str = "Visibility",
        draw_debug: str = "None",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Box Trace By Channel' node - box-shaped sweep trace.

        Ch.14: BoxTraceByChannel sweeps a box shape along the trace line.

        Args:
            blueprint_name: Blueprint name
            half_size: [X, Y, Z] half extents of the box in cm
            trace_channel: "Visibility" or "Camera"
            draw_debug: Debug visualization type
            node_position: Optional [X, Y] graph position
        """
        return _send("add_shape_trace_node", {
            "blueprint_name": blueprint_name,
            "shape_type": "Box",
            "trace_mode": "ByChannel",
            "half_size": half_size or [32.0, 32.0, 32.0],
            "trace_channel": trace_channel,
            "draw_debug": draw_debug,
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_break_hit_result_node(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Break Hit Result' node - decomposes Hit Result structure.

        Ch.14: Hit Result contains:
        - Blocking Hit (bool): Whether trace hit something
        - Location (Vector): World location of the hit point
        - Impact Normal (Vector): Surface normal at hit point
        - Hit Actor (Actor ref): Reference to the actor that was hit
        - Hit Component (Component ref): Component that was hit
        - Bone Name (Name): Bone hit on a Skeletal Mesh
        - Distance (float): Distance from start to hit

        Args:
            blueprint_name: Blueprint name
            node_position: Optional [X, Y] graph position
        """
        return _send("add_break_hit_result_node", {
            "blueprint_name": blueprint_name,
            "node_position": node_position or [0, 0]
        })

    # ─── Debug Draw Nodes ────────────────────────────────────────────────────────

    @mcp.tool()
    def add_draw_debug_line_node(
        ctx: Context,
        blueprint_name: str,
        duration: float = 1.0,
        color: List[float] = None,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Draw Debug Line' node - draws a line in the viewport for debugging.

        Ch.14: Trace functions have Draw Debug Type option. This node explicitly
        draws a 3D line for custom debug visualization.
        Debug lines are useful to find problems when traces aren't acting as expected.

        Args:
            blueprint_name: Blueprint name
            duration: How long the line persists (0 = one frame)
            color: [R, G, B, A] 0-255 color of the debug line
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetSystemLibrary",
            "function_name": "DrawDebugLine",
            "params": {
                "Duration": duration,
                "LineColor": color or [255, 0, 0, 255]
            },
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_draw_debug_sphere_node(
        ctx: Context,
        blueprint_name: str,
        radius: float = 50.0,
        duration: float = 1.0,
        color: List[float] = None,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Draw Debug Sphere' node for 3D debug visualization.

        Args:
            blueprint_name: Blueprint name
            radius: Sphere radius in cm
            duration: How long the sphere persists (0 = one frame)
            color: [R, G, B, A] color of the debug sphere
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetSystemLibrary",
            "function_name": "DrawDebugSphere",
            "params": {
                "Radius": radius,
                "Duration": duration,
                "LineColor": color or [255, 255, 0, 255]
            },
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_draw_debug_point_node(
        ctx: Context,
        blueprint_name: str,
        size: float = 10.0,
        duration: float = 1.0,
        color: List[float] = None,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Draw Debug Point' node - draws a dot in world space.

        Args:
            blueprint_name: Blueprint name
            size: Point size in screen pixels
            duration: How long the point persists
            color: [R, G, B, A] color of the debug point
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UKismetSystemLibrary",
            "function_name": "DrawDebugPoint",
            "params": {
                "PointSize": size,
                "Duration": duration,
                "PointColor": color or [0, 255, 0, 255]
            },
            "node_position": node_position or [0, 0]
        })

    # ─── Collision Configuration ─────────────────────────────────────────────────

    @mcp.tool()
    def add_set_collision_profile_node(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        profile_name: str = "BlockAll",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set Collision Profile Name' node for a component.

        Ch.14: Collision Presets define how a component responds to traces/overlaps.
        Common presets: BlockAll, OverlapAll, OverlapAllDynamic, Pawn, Custom.

        Args:
            blueprint_name: Blueprint name
            component_name: Component to set collision on
            profile_name: Collision preset: "BlockAll", "OverlapAll",
                         "OverlapAllDynamic", "Pawn", "BlockAllDynamic", "NoCollision"
            node_position: Optional [X, Y] graph position
        """
        return _send("add_component_function_node", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "function_name": "SetCollisionProfileName",
            "params": {"ProfileName": profile_name},
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_set_collision_enabled_node(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        collision_enabled: str = "QueryAndPhysics",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set Collision Enabled' node to toggle collision on a component.

        Args:
            blueprint_name: Blueprint name
            component_name: Component to configure
            collision_enabled: "NoCollision", "QueryOnly", "PhysicsOnly",
                               "QueryAndPhysics", "QueryAndProbe", "ProbeOnly"
            node_position: Optional [X, Y] graph position
        """
        return _send("add_component_function_node", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "function_name": "SetCollisionEnabled",
            "params": {"NewType": collision_enabled},
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_set_generate_overlap_events_node(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        generate_overlap: bool = True,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set Generate Overlap Events' node.

        Ch.5: Required to enable collision overlap callbacks.
        Without this set to True, OnComponentBeginOverlap won't fire.

        Args:
            blueprint_name: Blueprint name
            component_name: Component to configure
            generate_overlap: True to enable overlap events
            node_position: Optional [X, Y] graph position
        """
        return _send("add_component_function_node", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "function_name": "SetGenerateOverlapEvents",
            "params": {"bInGenerateOverlapEvents": generate_overlap},
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_apply_point_damage_node(
        ctx: Context,
        blueprint_name: str,
        damage_amount: float = 25.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an 'Apply Point Damage' node - damage at a specific world location/direction.

        Similar to Apply Damage but includes hit location and direction,
        allowing physics reactions (e.g. pushback from projectile impact).

        Args:
            blueprint_name: Blueprint name
            damage_amount: Default damage amount
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "ApplyPointDamage",
            "params": {"BaseDamage": damage_amount},
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def build_trace_interaction_blueprint(
        ctx: Context,
        blueprint_name: str = "BP_TraceInteractor",
        trace_range: float = 300.0,
        trace_channel: str = "Visibility",
        input_key: str = "E"
    ) -> Dict[str, Any]:
        """
        Build a complete trace-based interaction system from Ch.14.

        Creates the full example from the book:
        1. Adds a 'Trace Locations' macro (camera position + range ahead)
        2. Adds keyboard input event (default: E key)
        3. Adds LineTraceByChannel connected to the macro outputs
        4. Adds Break Hit Result to access the Hit Actor
        5. Compiles the Blueprint

        Args:
            blueprint_name: Target Blueprint (usually FirstPersonCharacter)
            trace_range: How far the trace reaches in cm (default 300cm)
            trace_channel: Trace channel to use
            input_key: Key to trigger interaction (default "E")
        """
        return _send("build_trace_interaction_blueprint", {
            "blueprint_name": blueprint_name,
            "trace_range": trace_range,
            "trace_channel": trace_channel,
            "input_key": input_key
        })

    logger.info("Physics/Math/Trace tools registered")
