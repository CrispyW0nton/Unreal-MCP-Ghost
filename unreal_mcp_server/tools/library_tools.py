"""
Blueprint Library & Component Tools for Unreal MCP.
Covers Chapter 18 (Creating Blueprint Libraries and Components) from the Blueprint book.

Provides tools for:
- Blueprint Function Libraries (shared utility functions across all Blueprints)
- Blueprint Macro Libraries (shared macros with parent class restriction)
- Actor Components (encapsulated behaviour - experience/level system, health regen)
- Scene Components (location-based behaviour - circular rotation, orbit shield)
- Local variables in functions
- Get Owner node (get Actor owner from a component)
- Set Timer by Event / Set Timer by Function Name
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


def register_library_tools(mcp: FastMCP):

    @mcp.tool()
    def create_blueprint_function_library(
        ctx: Context,
        name: str,
        functions: List[Dict[str, Any]] = None,
        folder_path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a Blueprint Function Library with shared utility functions.

        From Ch. 18: Create a Function Library (e.g., BP_DiceLibrary) whose functions
        are available globally in every Blueprint of the project. No instantiation needed.

        Functions are defined as a list of dicts with:
          - name: function name
          - inputs: [{\"name\": str, \"type\": str, \"default_value\": any}]
          - outputs: [{\"name\": str, \"type\": str}]
          - description: optional description

        Args:
            name: Library Blueprint name (e.g., \"BP_DiceLibrary\", \"BP_MathUtils\")
            functions: List of function definitions
            folder_path: Content browser folder

        Example - dice roll library from the book:
            functions=[
              {\"name\": \"RollOneDie\",
               \"inputs\": [{\"name\": \"NumberOfFaces\", \"type\": \"Integer\", \"default_value\": 6}],
               \"outputs\": [{\"name\": \"Result\", \"type\": \"Integer\"}]},
            ]
        """
        if functions is None:
            functions = []

        result = _send("create_blueprint_function_library", {
            "name": name,
            "folder_path": folder_path
        })

        if not result.get("success", True):
            return result

        for func in functions:
            _send("add_function_to_library", {
                "library_name": name,
                "function_name": func["name"],
                "inputs": func.get("inputs", []),
                "outputs": func.get("outputs", []),
                "description": func.get("description", "")
            })

        _send("compile_blueprint", {"blueprint_name": name})
        return {"success": True, "message": f"Function Library '{name}' created with {len(functions)} function(s)"}

    @mcp.tool()
    def create_blueprint_macro_library(
        ctx: Context,
        name: str,
        parent_class: str = "Actor",
        folder_path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a Blueprint Macro Library for shared macros across Blueprints.

        From Ch. 18: Macro Libraries gather macros that can be shared between all
        Blueprints of the parent class. Unlike Function Libraries, Macro Libraries
        require a parent class and can only be used in subclasses of that parent.

        Args:
            name: Macro Library Blueprint name (e.g., \"BP_MacroLibrary\")
            parent_class: Parent class restriction (\"Actor\" works for most cases)
            folder_path: Content browser folder
        """
        return _send("create_blueprint_macro_library", {
            "name": name,
            "parent_class": parent_class,
            "folder_path": folder_path
        })

    @mcp.tool()
    def create_actor_component(
        ctx: Context,
        name: str,
        variables: List[Dict[str, Any]] = None,
        functions: List[Dict[str, Any]] = None,
        folder_path: str = "/Game/Components"
    ) -> Dict[str, Any]:
        """
        Create an Actor Component Blueprint for encapsulated gameplay behaviour.

        From Ch. 18: Actor Components are reusable behaviour modules that can be added
        to any Actor. The book example creates BP_ExpLevelComp for experience/leveling.

        An Actor Component has no Transform (unlike Scene Component). It can access
        its owning Actor via the \"Get Owner\" node.

        Example use cases:
        - Experience/leveling system (BP_ExpLevelComp from the book)
        - Health regeneration component
        - Inventory component
        - Status effect manager

        Args:
            name: Component Blueprint name (e.g., \"BP_ExpLevelComp\")
            variables: List of variable definitions [{\"name\", \"type\", \"default_value\", \"is_array\"}]
            functions: List of function definitions [{\"name\", \"inputs\", \"outputs\"}]
            folder_path: Content browser folder
        """
        if variables is None:
            variables = []
        if functions is None:
            functions = []

        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "ActorComponent",
            "folder_path": folder_path
        })

        if not result.get("success", True):
            return result

        for var in variables:
            _send("add_blueprint_variable", {
                "blueprint_name": name,
                "variable_name": var["name"],
                "variable_type": var.get("type", "Float"),
                "is_array": var.get("is_array", False),
                "is_exposed": var.get("is_exposed", False)
            })

        for func in functions:
            _send("add_function_to_blueprint", {
                "blueprint_name": name,
                "function_name": func["name"],
                "inputs": func.get("inputs", []),
                "outputs": func.get("outputs", [])
            })

        _send("compile_blueprint", {"blueprint_name": name})
        return {"success": True, "message": f"Actor Component '{name}' created"}

    @mcp.tool()
    def create_experience_level_component(
        ctx: Context,
        name: str = "BP_ExpLevelComp",
        max_level: int = 10,
        xp_per_level: List[int] = None,
        folder_path: str = "/Game/Components"
    ) -> Dict[str, Any]:
        """
        Create the complete experience/level-up Actor Component from Ch. 18.

        Creates BP_ExpLevelComp with:
        - CurrentLevel (Integer)
        - CurrentXP (Integer)
        - ExpLevel array (Integer array for XP thresholds per level)
        - CanLevelUp macro
        - XpReachesNewLevel macro
        - IncreaseExperience function (returns bool LeveledUp)

        Args:
            name: Component Blueprint name
            max_level: Maximum number of levels
            xp_per_level: XP required for each level up. Defaults to [10,20,40,80,...]
            folder_path: Content browser folder
        """
        if xp_per_level is None:
            xp_per_level = [10 * (2 ** i) for i in range(max_level)]

        return _send("create_experience_level_component", {
            "name": name,
            "max_level": max_level,
            "xp_per_level": xp_per_level,
            "folder_path": folder_path
        })

    @mcp.tool()
    def create_scene_component(
        ctx: Context,
        name: str,
        variables: List[Dict[str, Any]] = None,
        folder_path: str = "/Game/Components"
    ) -> Dict[str, Any]:
        """
        Create a Scene Component Blueprint (has Transform - location/rotation/scale).

        From Ch. 18: Scene Components can be attached to other Scene Components,
        creating a hierarchy. The book creates BP_CircularMovComp that orbits
        around the Actor and can have other components (like a Static Mesh shield)
        attached to it.

        Use cases:
        - Orbiting/rotating attachments (the book's rotating shield)
        - Floating damage numbers
        - Aura/effect that follows an actor
        - Socket attachment points

        Args:
            name: Component Blueprint name (e.g., \"BP_CircularMovComp\")
            variables: Variable definitions [{\"name\", \"type\", \"default_value\"}]
            folder_path: Content browser folder
        """
        if variables is None:
            variables = []

        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "SceneComponent",
            "folder_path": folder_path
        })

        if not result.get("success", True):
            return result

        for var in variables:
            _send("add_blueprint_variable", {
                "blueprint_name": name,
                "variable_name": var["name"],
                "variable_type": var.get("type", "Float"),
                "is_exposed": var.get("is_exposed", False)
            })
            if "default_value" in var:
                _send("set_blueprint_property", {
                    "blueprint_name": name,
                    "property_name": var["name"],
                    "property_value": var["default_value"]
                })

        _send("compile_blueprint", {"blueprint_name": name})
        return {"success": True, "message": f"Scene Component '{name}' created"}

    @mcp.tool()
    def create_circular_movement_component(
        ctx: Context,
        name: str = "BP_CircularMovComp",
        rotation_per_second: float = 180.0,
        orbit_radius: float = 70.0,
        folder_path: str = "/Game/Components"
    ) -> Dict[str, Any]:
        """
        Create the orbiting Scene Component from Ch. 18 of the book.

        Creates BP_CircularMovComp that:
        - Uses Event Tick + Delta Seconds to calculate per-frame delta angle
        - Applies SetRelativeLocation + AddLocalRotation to orbit around owner
        - Default speed: 180 deg/sec (completes full orbit in 2 seconds)

        This is perfect for rotating shields, orbiting particles, or
        any attachment that needs to circle around an actor.

        Args:
            name: Component Blueprint name
            rotation_per_second: Orbit speed in degrees per second
            orbit_radius: Radius of the circular orbit in Unreal units
            folder_path: Content browser folder
        """
        return _send("create_circular_movement_component", {
            "name": name,
            "rotation_per_second": rotation_per_second,
            "orbit_radius": orbit_radius,
            "folder_path": folder_path
        })

    @mcp.tool()
    def add_component_to_blueprint_actor(
        ctx: Context,
        blueprint_name: str,
        component_blueprint_name: str,
        attach_to_component: str = "",
        component_location: List[float] = [0.0, 0.0, 0.0]
    ) -> Dict[str, Any]:
        """
        Add a custom Blueprint Component to an existing Blueprint Actor.

        From Ch. 18: Adding BP_ExpLevelComp or BP_CircularMovComp to
        ThirdPersonCharacter. The component's events and functions become
        available in the Actor's Blueprint graph.

        Args:
            blueprint_name: Target Actor Blueprint to modify
            component_blueprint_name: Component Blueprint to add
            attach_to_component: Parent component name to attach to (empty = root)
            component_location: Relative location for the component
        """
        return _send("add_custom_component_to_blueprint", {
            "blueprint_name": blueprint_name,
            "component_blueprint_name": component_blueprint_name,
            "attach_to_component": attach_to_component,
            "component_location": component_location
        })

    @mcp.tool()
    def add_set_timer_by_event_node(
        ctx: Context,
        blueprint_name: str,
        time_seconds: float = 1.0,
        looping: bool = True,
        custom_event_name: str = "TimerCallback",
        trigger_event: str = "ReceiveBeginPlay",
        node_position: List[int] = [300, 0]
    ) -> Dict[str, Any]:
        """
        Add a SetTimerByEvent node with a connected Custom Event.

        From Ch. 18 (Actor Component testing): Set Timer by Event calls a custom
        event on a regular interval. Used in the book to trigger GainXP every second.

        Args:
            blueprint_name: Blueprint to add the node to
            time_seconds: Timer interval in seconds
            looping: True for repeating timer
            custom_event_name: Name of the custom event that gets called
            trigger_event: Event that starts the timer (e.g., \"ReceiveBeginPlay\")
            node_position: [X, Y] graph position
        """
        return _send("add_set_timer_by_event_node", {
            "blueprint_name": blueprint_name,
            "time_seconds": time_seconds,
            "looping": looping,
            "custom_event_name": custom_event_name,
            "trigger_event": trigger_event,
            "node_position": node_position
        })

    @mcp.tool()
    def add_get_owner_node(
        ctx: Context,
        blueprint_name: str,
        cast_to_class: str = "",
        node_position: List[int] = [200, 0]
    ) -> Dict[str, Any]:
        """
        Add a GetOwner node to retrieve the Actor that owns this component.

        From Ch. 18: When scripting inside a component Blueprint, GetOwner
        returns a reference to the Actor that has this component added to it.
        Optionally cast to a specific class to access class-specific functionality.

        Args:
            blueprint_name: Component Blueprint to add the node to
            cast_to_class: Class to cast the owner to (e.g., \"BP_Character\"). Empty = no cast.
            node_position: [X, Y] graph position
        """
        return _send("add_get_owner_node", {
            "blueprint_name": blueprint_name,
            "cast_to_class": cast_to_class,
            "node_position": node_position
        })

    logger.info("Library tools registered successfully")
