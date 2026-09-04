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
        """Create a GameModeBase Blueprint with optional class assignments.

        The GameMode controls which classes (Pawn, HUD, PlayerController, etc.)
        are used when the level starts.

        Args:
            name: Blueprint name (e.g., "BP_MyGameMode")
            default_pawn_class: Default pawn Blueprint name
            hud_class: HUD Blueprint name
            player_controller_class: PlayerController Blueprint name
            game_state_class: GameState Blueprint name
            spectator_class: Spectator pawn Blueprint name

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            create_game_mode(name="ExampleName")"""
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
        """Create a PlayerController Blueprint.

        Args:
            name: Blueprint name (e.g., "BP_MyPlayerController")
            show_mouse_cursor: Show mouse cursor in game
            enable_click_events: Enable actor click events
            enable_touch_events: Enable touch events

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            create_player_controller(name="ExampleName")"""
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
        """Create a GameInstance Blueprint.

        GameInstance persists across level loads and is ideal for storing
        player progress, settings, and cross-level data.

        Args:
            name: Blueprint name (e.g., "BP_MyGameInstance")

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            create_game_instance(name="ExampleName")"""
        result = _send("create_blueprint", {"name": name, "parent_class": "GameInstance"})
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_hud_blueprint(ctx: Context, name: str) -> Dict[str, Any]:
        """Create a HUD Blueprint.

        Args:
            name: Blueprint name (e.g., "BP_MyHUD")

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            create_hud_blueprint(name="ExampleName")"""
        result = _send("create_blueprint", {"name": name, "parent_class": "HUD"})
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def set_game_mode_for_level(
        ctx: Context,
        game_mode_name: str
    ) -> Dict[str, Any]:
        """Set the GameMode override for the current level (World Settings).

        Args:
            game_mode_name: GameMode Blueprint name

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            set_game_mode_for_level(game_mode_name="ExampleName")"""
        return _send("set_game_mode_for_level", {"game_mode_name": game_mode_name})

    @mcp.tool()
    def net_describe_blueprint_replication(
        ctx: Context,
        blueprint_name: str,
    ) -> Dict[str, Any]:
        """Inspect an Actor Blueprint's replication defaults, replicated variables,
        RepNotify callbacks, replicated components, and existing RPC functions.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_describe_blueprint_replication(blueprint_name="/Game/MCP_Test/BP_Example")"""
        return _send("net_describe_blueprint_replication", {
            "blueprint_name": blueprint_name,
        })

    @mcp.tool()
    def net_set_actor_replicates(
        ctx: Context,
        blueprint_name: str,
        replicates: bool = True,
        replicate_movement: bool = False,
        net_update_frequency: float = -1.0,
        min_net_update_frequency: float = -1.0,
        save: bool = True,
        compile: bool = False,
    ) -> Dict[str, Any]:
        """Configure safe Actor replication defaults on an Actor-derived Blueprint.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_set_actor_replicates(blueprint_name="/Game/MCP_Test/BP_Example")"""
        params = {
            "blueprint_name": blueprint_name,
            "replicates": replicates,
            "replicate_movement": replicate_movement,
            "save": save,
            "compile": compile,
        }
        if net_update_frequency > 0:
            params["net_update_frequency"] = net_update_frequency
        if min_net_update_frequency > 0:
            params["min_net_update_frequency"] = min_net_update_frequency
        return _send("net_set_actor_replicates", params)

    @mcp.tool()
    def net_set_component_replicates(
        ctx: Context,
        blueprint_name: str,
        component_name: str,
        replicates: bool = True,
        save: bool = True,
        compile: bool = False,
    ) -> Dict[str, Any]:
        """Configure replication-by-default on a Blueprint SCS component template.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_set_component_replicates(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent")"""
        return _send("net_set_component_replicates", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "replicates": replicates,
            "save": save,
            "compile": compile,
        })

    @mcp.tool()
    def net_configure_replicated_property(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        replication_mode: str = "replicated",
        replication_condition: str = "none",
        save: bool = True,
        compile: bool = True,
    ) -> Dict[str, Any]:
        """Configure an existing Blueprint member variable as none, replicated, or RepNotify.

        Supported replication_condition values include none, initial_only,
        owner_only, skip_owner, simulated_only, autonomous_only, initial_or_owner,
        replay_only, skip_replay, custom, dynamic, and never.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_configure_replicated_property(blueprint_name="/Game/MCP_Test/BP_Example", variable_name="ExampleName")"""
        return _send("net_configure_replicated_property", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "replication_mode": replication_mode,
            "replication_condition": replication_condition,
            "save": save,
            "compile": compile,
        })

    @mcp.tool()
    def net_add_repnotify_variable(
        ctx: Context,
        blueprint_name: str,
        variable_name: str,
        variable_type: str = "Boolean",
        default_value: str = "",
        replication_condition: str = "none",
        save: bool = True,
        compile: bool = True,
    ) -> Dict[str, Any]:
        """Add a Blueprint member variable and configure it for RepNotify.

        Supported variable_type values: Boolean, Integer, Integer64, Float,
        Double, String, Name, Text, Vector, Rotator, and Transform.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_add_repnotify_variable(blueprint_name="/Game/MCP_Test/BP_Example", variable_name="ExampleName")"""
        params = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "variable_type": variable_type,
            "replication_condition": replication_condition,
            "save": save,
            "compile": compile,
        }
        if default_value:
            params["default_value"] = default_value
        return _send("net_add_repnotify_variable", params)

    @mcp.tool()
    def net_create_rpc_event(
        ctx: Context,
        blueprint_name: str,
        event_name: str,
        rpc_type: str = "server",
        reliable: bool = True,
        inputs: Optional[List[Dict[str, str]]] = None,
        node_position: Optional[List[float]] = None,
        save: bool = True,
        compile: bool = True,
    ) -> Dict[str, Any]:
        """Create or update a Custom Event as a Blueprint RPC.

        Supported rpc_type values: server, client, net_multicast, and none.
        Optional inputs are simple typed event parameters, for example
        [{"name": "Damage", "type": "Float"}].

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_create_rpc_event(blueprint_name="/Game/MCP_Test/BP_Example", event_name="ExampleName")"""
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "event_name": event_name,
            "rpc_type": rpc_type,
            "reliable": reliable,
            "save": save,
            "compile": compile,
        }
        if inputs:
            params["inputs"] = inputs
        if node_position:
            params["node_position"] = node_position
        return _send("net_create_rpc_event", params)

    @mcp.tool()
    def net_configure_rpc(
        ctx: Context,
        blueprint_name: str,
        event_name: str,
        rpc_type: str = "server",
        reliable: bool = True,
        save: bool = True,
        compile: bool = True,
    ) -> Dict[str, Any]:
        """Configure network flags on an existing Blueprint Custom Event RPC.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_configure_rpc(blueprint_name="/Game/MCP_Test/BP_Example", event_name="ExampleName")"""
        return _send("net_configure_rpc", {
            "blueprint_name": blueprint_name,
            "event_name": event_name,
            "rpc_type": rpc_type,
            "reliable": reliable,
            "save": save,
            "compile": compile,
        })

    @mcp.tool()
    def net_add_authority_gate(
        ctx: Context,
        blueprint_name: str,
        node_position: Optional[List[float]] = None,
        save: bool = True,
        compile: bool = False,
    ) -> Dict[str, Any]:
        """Add a HasAuthority function node wired into a Branch node.
        The Branch Then pin represents authority/server flow; Else is remote/client flow.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_add_authority_gate(blueprint_name="/Game/MCP_Test/BP_Example")"""
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "save": save,
            "compile": compile,
        }
        if node_position:
            params["node_position"] = node_position
        return _send("net_add_authority_gate", params)

    @mcp.tool()
    def net_add_role_switch(
        ctx: Context,
        blueprint_name: str,
        node_position: Optional[List[float]] = None,
        save: bool = True,
        compile: bool = False,
    ) -> Dict[str, Any]:
        """Add an ENetRole switch node for role-specific Blueprint flow.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_add_role_switch(blueprint_name="/Game/MCP_Test/BP_Example")"""
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "save": save,
            "compile": compile,
        }
        if node_position:
            params["node_position"] = node_position
        return _send("net_add_role_switch", params)

    @mcp.tool()
    def net_set_owner_reference(
        ctx: Context,
        blueprint_name: str,
        node_position: Optional[List[float]] = None,
        save: bool = True,
        compile: bool = False,
    ) -> Dict[str, Any]:
        """Add an AActor.SetOwner call node for server-side ownership setup.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_set_owner_reference(blueprint_name="/Game/MCP_Test/BP_Example")"""
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "save": save,
            "compile": compile,
        }
        if node_position:
            params["node_position"] = node_position
        return _send("net_set_owner_reference", params)

    @mcp.tool()
    def session_create_blueprint_flow(
        ctx: Context,
        blueprint_name: str,
        public_connections: int = 4,
        use_lan: bool = True,
        use_lobbies_if_available: bool = True,
        node_position: Optional[List[float]] = None,
        save: bool = True,
        compile: bool = False,
    ) -> Dict[str, Any]:
        """Add a Create Session async Blueprint node and wire GetPlayerController(0).

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            session_create_blueprint_flow(blueprint_name="/Game/MCP_Test/BP_Example")"""
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "public_connections": public_connections,
            "use_lan": use_lan,
            "use_lobbies_if_available": use_lobbies_if_available,
            "save": save,
            "compile": compile,
        }
        if node_position:
            params["node_position"] = node_position
        return _send("session_create_blueprint_flow", params)

    @mcp.tool()
    def session_find_blueprint_flow(
        ctx: Context,
        blueprint_name: str,
        max_results: int = 20,
        use_lan: bool = True,
        use_lobbies: bool = True,
        node_position: Optional[List[float]] = None,
        save: bool = True,
        compile: bool = False,
    ) -> Dict[str, Any]:
        """Add a Find Sessions async Blueprint node and wire GetPlayerController(0).

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            session_find_blueprint_flow(blueprint_name="/Game/MCP_Test/BP_Example")"""
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "max_results": max_results,
            "use_lan": use_lan,
            "use_lobbies": use_lobbies,
            "save": save,
            "compile": compile,
        }
        if node_position:
            params["node_position"] = node_position
        return _send("session_find_blueprint_flow", params)

    @mcp.tool()
    def network_debug_replication(
        ctx: Context,
        max_actors: int = 25,
    ) -> Dict[str, Any]:
        """Capture a runtime/editor replication snapshot: net mode, net driver,
        connections, network object counts, and replicated actor samples.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            network_debug_replication()"""
        return _send("network_debug_replication", {
            "max_actors": max_actors,
        })

    @mcp.tool()
    def net_validate_common_mistakes(
        ctx: Context,
        blueprint_name: str = "",
    ) -> Dict[str, Any]:
        """Validate common Blueprint networking mistakes such as replicated state
        on non-replicating Actors, missing RepNotify handlers, and risky RPCs.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            net_validate_common_mistakes()"""
        params: Dict[str, Any] = {}
        if blueprint_name:
            params["blueprint_name"] = blueprint_name
        return _send("net_validate_common_mistakes", params)

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
        """Create a Character Blueprint with optional camera setup.

        Characters include: CapsuleComponent, CharacterMovement, SkeletalMesh.

        Args:
            name: Blueprint name
            add_camera: Add a CameraComponent
            add_spring_arm: Add a SpringArmComponent for the camera
            camera_location: Camera relative location
            camera_rotation: Camera relative rotation
            spring_arm_length: SpringArm target arm length

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            create_character_blueprint(name="ExampleName")"""
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
        """Create a First-Person Shooter character Blueprint.
        Adds a first-person camera and arms mesh components.

        Args:
            name: Blueprint name (e.g., "BP_FPSCharacter")

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            create_fps_character(name="ExampleName")"""
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
        event_name: str = "OnComponentBeginOverlap",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """Add an OnComponentBeginOverlap event node bound to a SPECIFIC SCS component.

        Creates a K2Node_ComponentBoundEvent — equivalent to clicking the [+] button
        next to the event in the component's Details panel.  Multiple components in
        the same Blueprint each get their own event node (per component variable GUID).

        Use get_scs_nodes to list available component names and their GUIDs.

        Args:
            blueprint_name: Blueprint asset name (e.g. "BP_MyActor")
            component_name: SCS component variable name (e.g. "InteractionSphere")
            event_name:     Delegate event name. Default "OnComponentBeginOverlap".
                            Other options: "OnComponentEndOverlap", "OnComponentHit".
            node_position:  Optional [X, Y] canvas position.

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            add_overlap_event(blueprint_name="/Game/MCP_Test/BP_Example", component_name="ExampleComponent")"""
        if node_position is None:
            node_position = [0, 0]
        # BUG-030 fix: route to add_component_overlap_event (K2Node_ComponentBoundEvent)
        # instead of add_blueprint_event_node (actor-level, one-per-Blueprint only).
        return _send("add_component_overlap_event", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "event_name":     event_name,
            "node_position":  node_position,
        })

    @mcp.tool()
    def add_hit_event(
        ctx: Context,
        blueprint_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """Add an OnActorHit event node (fires when actor is hit by collision).

        Args:
            blueprint_name: Blueprint name
            node_position: Optional graph position

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            add_hit_event(blueprint_name="/Game/MCP_Test/BP_Example")"""
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
        """Create a Projectile Blueprint with movement component.

        Args:
            name: Blueprint name (e.g., "BP_Projectile")
            speed: Projectile speed in cm/s
            gravity_scale: Gravity influence (0 = no gravity)
            damage: Damage amount on hit

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            create_projectile_blueprint(name="ExampleName")"""
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
        """Create a pickup actor Blueprint (health, ammo, powerup, etc.).

        Args:
            name: Blueprint name
            pickup_type: Type label ("Health", "Ammo", "Key", etc.)
            value: Pickup value amount
            rotate_speed: Degrees per second rotation (0 = no rotation)

        KB: see knowledge_base/03_GAMEPLAY_FRAMEWORK.md#overview
        Example:
            create_pickup_blueprint(name="ExampleName")"""
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
