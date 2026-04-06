"""
Gameplay Framework Tools - GameMode, GameInstance, PlayerController, HUD.
Covers Chapter 3 (OOP + Gameplay Framework) from the Blueprint book.
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


def register_gameplay_tools(mcp: FastMCP):

    @mcp.tool()
    def create_game_mode(
        ctx: Context,
        name: str,
        default_pawn_class: str = "",
        hud_class: str = "",
        player_controller_class: str = "",
        game_state_class: str = "",
        spectator_class: str = ""
    ) -> Dict[str, Any]:
        """
        Create a GameModeBase Blueprint with optional class assignments.

        The GameMode controls which classes (Pawn, HUD, PlayerController, etc.)
        are used when the level starts.

        Args:
            name: Blueprint name (e.g., "BP_MyGameMode")
            default_pawn_class: Default pawn Blueprint name
            hud_class: HUD Blueprint name
            player_controller_class: PlayerController Blueprint name
            game_state_class: GameState Blueprint name
            spectator_class: Spectator pawn Blueprint name
        """
        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "GameModeBase"
        })
        if not result.get("success", True):
            return result

        # Set class properties if provided
        props = {
            "DefaultPawnClass": default_pawn_class,
            "HUDClass": hud_class,
            "PlayerControllerClass": player_controller_class,
            "GameStateClass": game_state_class,
            "SpectatorClass": spectator_class
        }
        for prop_name, bp_name in props.items():
            if bp_name:
                _send("set_blueprint_property", {
                    "blueprint_name": name,
                    "property_name": prop_name,
                    "property_value": bp_name
                })

        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_player_controller(
        ctx: Context,
        name: str,
        show_mouse_cursor: bool = False,
        enable_click_events: bool = False,
        enable_touch_events: bool = False
    ) -> Dict[str, Any]:
        """
        Create a PlayerController Blueprint.

        Args:
            name: Blueprint name (e.g., "BP_MyPlayerController")
            show_mouse_cursor: Show mouse cursor in game
            enable_click_events: Enable actor click events
            enable_touch_events: Enable touch events
        """
        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "PlayerController"
        })
        if show_mouse_cursor:
            _send("set_blueprint_property", {
                "blueprint_name": name,
                "property_name": "bShowMouseCursor",
                "property_value": True
            })
        if enable_click_events:
            _send("set_blueprint_property", {
                "blueprint_name": name,
                "property_name": "bEnableClickEvents",
                "property_value": True
            })
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_game_instance(ctx: Context, name: str) -> Dict[str, Any]:
        """
        Create a GameInstance Blueprint.

        GameInstance persists across level loads and is ideal for storing
        player progress, settings, and cross-level data.

        Args:
            name: Blueprint name (e.g., "BP_MyGameInstance")
        """
        result = _send("create_blueprint", {"name": name, "parent_class": "GameInstance"})
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_hud_blueprint(ctx: Context, name: str) -> Dict[str, Any]:
        """
        Create a HUD Blueprint.

        Args:
            name: Blueprint name (e.g., "BP_MyHUD")
        """
        result = _send("create_blueprint", {"name": name, "parent_class": "HUD"})
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def set_game_mode_for_level(
        ctx: Context,
        game_mode_name: str
    ) -> Dict[str, Any]:
        """
        Set the GameMode override for the current level (World Settings).

        Args:
            game_mode_name: GameMode Blueprint name
        """
        return _send("set_game_mode_for_level", {"game_mode_name": game_mode_name})

    @mcp.tool()
    def create_character_blueprint(
        ctx: Context,
        name: str,
        add_camera: bool = True,
        add_spring_arm: bool = True,
        camera_location: List[float] = [0.0, 0.0, 300.0],
        camera_rotation: List[float] = [-60.0, 0.0, 0.0],
        spring_arm_length: float = 600.0
    ) -> Dict[str, Any]:
        """
        Create a Character Blueprint with optional camera setup.

        Characters include: CapsuleComponent, CharacterMovement, SkeletalMesh.

        Args:
            name: Blueprint name
            add_camera: Add a CameraComponent
            add_spring_arm: Add a SpringArmComponent for the camera
            camera_location: Camera relative location
            camera_rotation: Camera relative rotation  
            spring_arm_length: SpringArm target arm length
        """
        result = _send("create_blueprint", {"name": name, "parent_class": "Character"})

        if add_spring_arm:
            _send("add_component_to_blueprint", {
                "blueprint_name": name,
                "component_type": "SpringArmComponent",
                "component_name": "CameraBoom",
                "location": [0.0, 0.0, 60.0],
                "rotation": [0.0, 0.0, 0.0],
                "scale": [1.0, 1.0, 1.0]
            })
            _send("set_component_property", {
                "blueprint_name": name,
                "component_name": "CameraBoom",
                "property_name": "TargetArmLength",
                "property_value": spring_arm_length
            })
            _send("set_component_property", {
                "blueprint_name": name,
                "component_name": "CameraBoom",
                "property_name": "bUsePawnControlRotation",
                "property_value": True
            })

        if add_camera:
            _send("add_component_to_blueprint", {
                "blueprint_name": name,
                "component_type": "CameraComponent",
                "component_name": "FollowCamera",
                "location": camera_location,
                "rotation": camera_rotation,
                "scale": [1.0, 1.0, 1.0]
            })

        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_fps_character(
        ctx: Context,
        name: str
    ) -> Dict[str, Any]:
        """
        Create a First-Person Shooter character Blueprint.
        Adds a first-person camera and arms mesh components.

        Args:
            name: Blueprint name (e.g., "BP_FPSCharacter")
        """
        result = _send("create_blueprint", {"name": name, "parent_class": "Character"})

        # FPS Camera
        _send("add_component_to_blueprint", {
            "blueprint_name": name,
            "component_type": "CameraComponent",
            "component_name": "FPSCamera",
            "location": [0.0, 0.0, 60.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0]
        })
        _send("set_component_property", {
            "blueprint_name": name,
            "component_name": "FPSCamera",
            "property_name": "bUsePawnControlRotation",
            "property_value": True
        })

        # Arms mesh
        _send("add_component_to_blueprint", {
            "blueprint_name": name,
            "component_type": "SkeletalMeshComponent",
            "component_name": "ArmsMesh",
            "location": [-0.5, 0.0, -150.0],
            "rotation": [0.0, -90.0, 0.0],
            "scale": [1.0, 1.0, 1.0]
        })

        # Pawn settings
        _send("set_blueprint_property", {
            "blueprint_name": name,
            "property_name": "bUseControllerRotationYaw",
            "property_value": True
        })

        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def add_overlap_event(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an OnComponentBeginOverlap event node for a component.

        Args:
            blueprint_name: Blueprint name
            component_name: Component that triggers overlap (e.g., "CollisionBox")
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_event_node", {
            "blueprint_name": blueprint_name,
            "event_name": "ReceiveActorBeginOverlap",
            "node_position": node_position
        })

    @mcp.tool()
    def add_hit_event(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add an OnActorHit event node (fires when actor is hit by collision).

        Args:
            blueprint_name: Blueprint name
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_event_node", {
            "blueprint_name": blueprint_name,
            "event_name": "ReceiveHit",
            "node_position": node_position
        })

    @mcp.tool()
    def create_projectile_blueprint(
        ctx: Context,
        name: str,
        speed: float = 3000.0,
        gravity_scale: float = 0.0,
        damage: float = 20.0
    ) -> Dict[str, Any]:
        """
        Create a Projectile Blueprint with movement component.

        Args:
            name: Blueprint name (e.g., "BP_Projectile")
            speed: Projectile speed in cm/s
            gravity_scale: Gravity influence (0 = no gravity)
            damage: Damage amount on hit
        """
        result = _send("create_blueprint", {"name": name, "parent_class": "Actor"})

        # Collision sphere
        _send("add_component_to_blueprint", {
            "blueprint_name": name,
            "component_type": "SphereComponent",
            "component_name": "CollisionSphere",
            "location": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0]
        })

        # Mesh
        _send("add_component_to_blueprint", {
            "blueprint_name": name,
            "component_type": "StaticMeshComponent",
            "component_name": "ProjectileMesh",
            "location": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [0.2, 0.2, 0.2]
        })
        _send("set_static_mesh_properties", {
            "blueprint_name": name,
            "component_name": "ProjectileMesh",
            "static_mesh": "/Engine/BasicShapes/Sphere.Sphere"
        })

        # Projectile Movement component
        _send("add_component_to_blueprint", {
            "blueprint_name": name,
            "component_type": "ProjectileMovementComponent",
            "component_name": "ProjectileMovement",
            "location": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0]
        })
        _send("set_component_property", {
            "blueprint_name": name,
            "component_name": "ProjectileMovement",
            "property_name": "InitialSpeed",
            "property_value": speed
        })
        _send("set_component_property", {
            "blueprint_name": name,
            "component_name": "ProjectileMovement",
            "property_name": "MaxSpeed",
            "property_value": speed
        })
        _send("set_component_property", {
            "blueprint_name": name,
            "component_name": "ProjectileMovement",
            "property_name": "ProjectileGravityScale",
            "property_value": gravity_scale
        })

        # Blueprint variable for damage
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "DamageAmount",
            "variable_type": "Float",
            "is_exposed": True
        })
        _send("set_blueprint_property", {
            "blueprint_name": name,
            "property_name": "DamageAmount",
            "property_value": damage
        })

        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_pickup_blueprint(
        ctx: Context,
        name: str,
        pickup_type: str = "Health",
        value: float = 25.0,
        rotate_speed: float = 90.0
    ) -> Dict[str, Any]:
        """
        Create a pickup actor Blueprint (health, ammo, powerup, etc.).

        Args:
            name: Blueprint name
            pickup_type: Type label ("Health", "Ammo", "Key", etc.)
            value: Pickup value amount
            rotate_speed: Degrees per second rotation (0 = no rotation)
        """
        result = _send("create_blueprint", {"name": name, "parent_class": "Actor"})

        _send("add_component_to_blueprint", {
            "blueprint_name": name,
            "component_type": "StaticMeshComponent",
            "component_name": "PickupMesh",
            "location": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.0, 1.0, 1.0]
        })

        _send("add_component_to_blueprint", {
            "blueprint_name": name,
            "component_type": "SphereComponent",
            "component_name": "OverlapSphere",
            "location": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
            "scale": [1.5, 1.5, 1.5]
        })

        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "PickupValue",
            "variable_type": "Float",
            "is_exposed": True
        })

        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "bIsActive",
            "variable_type": "Boolean",
            "is_exposed": False
        })

        _send("compile_blueprint", {"blueprint_name": name})
        return result

    logger.info("Gameplay tools registered")
