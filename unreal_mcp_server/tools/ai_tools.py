"""
AI Tools - Behavior Trees, Blackboards, AI Controllers, BT Tasks/Decorators/Services.
Covers the AI chapter from the Blueprint book.
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


def register_ai_tools(mcp: FastMCP):

    @mcp.tool()
    def create_behavior_tree(
        ctx: Context,
        name: str,
        path: str = "/Game/AI"
    ) -> Dict[str, Any]:
        """
        Create a Behavior Tree asset.

        Behavior Trees define AI decision-making using a tree of Tasks,
        Composites (Sequence/Selector), Decorators, and Services.

        Args:
            name: Behavior Tree asset name (e.g., "BT_EnemyAI")
            path: Content browser path
        """
        return _send("create_behavior_tree", {
            "name": name,
            "path": path
        })

    @mcp.tool()
    def create_blackboard(
        ctx: Context,
        name: str,
        keys: List[Dict[str, str]] = None,
        path: str = "/Game/AI"
    ) -> Dict[str, Any]:
        """
        Create a Blackboard asset.

        The Blackboard is the AI's shared memory - it stores data that
        the Behavior Tree reads and writes during execution.

        Args:
            name: Blackboard asset name (e.g., "BB_EnemyAI")
            keys: List of key dicts:
                  [{"name": "TargetActor", "type": "Object"},
                   {"name": "PatrolLocation", "type": "Vector"},
                   {"name": "bIsAlerted", "type": "Boolean"},
                   {"name": "Health", "type": "Float"}]
            path: Content browser path

        Key types: Object, Actor, Class, Enum, Float, Int, Bool (Boolean),
                   String, Name, Vector, Rotator
        """
        return _send("create_blackboard", {
            "name": name,
            "keys": keys or [],
            "path": path
        })

    @mcp.tool()
    def create_ai_controller(
        ctx: Context,
        name: str,
        behavior_tree: str = "",
        auto_run_bt: bool = True
    ) -> Dict[str, Any]:
        """
        Create an AIController Blueprint.

        The AIController possesses an AI Pawn and runs its Behavior Tree.

        Args:
            name: Blueprint name (e.g., "BP_EnemyAIController")
            behavior_tree: Behavior Tree asset name to run automatically
            auto_run_bt: Automatically run the behavior tree on possession
        """
        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "AIController"
        })

        if behavior_tree and auto_run_bt:
            # Add BeginPlay event to run the behavior tree
            bp_result = _send("add_blueprint_event_node", {
                "blueprint_name": name,
                "event_name": "ReceiveBeginPlay",
                "node_position": [0, 0]
            })
            bt_node = _send("add_blueprint_function_node", {
                "blueprint_name": name,
                "target": "self",
                "function_name": "RunBehaviorTree",
                "params": {"BTAsset": behavior_tree},
                "node_position": [250, 0]
            })

        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_bt_task(
        ctx: Context,
        name: str,
        task_description: str = "",
        path: str = "/Game/AI"
    ) -> Dict[str, Any]:
        """
        Create a Behavior Tree Task Blueprint.

        BT Tasks are the leaf nodes of the Behavior Tree - they perform
        actual actions (move to location, attack, play animation, etc.).
        Override ExecuteTask and FinishExecute.

        Args:
            name: Task Blueprint name (e.g., "BTT_AttackPlayer")
            task_description: Description for the task node
            path: Content browser path
        """
        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "BTTask_BlueprintBase"
        })

        # Add blackboard key selector variable
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "BlackboardKey",
            "variable_type": "BlackboardKeySelector",
            "is_exposed": True
        })

        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_bt_decorator(
        ctx: Context,
        name: str,
        path: str = "/Game/AI"
    ) -> Dict[str, Any]:
        """
        Create a Behavior Tree Decorator Blueprint.

        Decorators are conditions attached to BT nodes - they control whether
        a branch can execute or abort. Override PerformConditionCheck.

        Args:
            name: Decorator Blueprint name (e.g., "BTD_CanSeePlayer")
            path: Content browser path
        """
        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "BTDecorator_BlueprintBase"
        })
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_bt_service(
        ctx: Context,
        name: str,
        tick_interval: float = 0.5,
        path: str = "/Game/AI"
    ) -> Dict[str, Any]:
        """
        Create a Behavior Tree Service Blueprint.

        Services run on a tick while their parent node is active - used to
        update Blackboard values (perception, distance checks, etc.).
        Override ReceiveTick.

        Args:
            name: Service Blueprint name (e.g., "BTS_UpdateTarget")
            tick_interval: How often the service ticks in seconds
            path: Content browser path
        """
        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "BTService_BlueprintBase"
        })
        if tick_interval != 0.5:
            _send("set_blueprint_property", {
                "blueprint_name": name,
                "property_name": "Interval",
                "property_value": tick_interval
            })
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def add_move_to_node(
        ctx: Context,
        blueprint_name: str,
        acceptance_radius: float = 50.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'AI Move To' function call node.

        Args:
            blueprint_name: Blueprint (usually AIController or BTTask)
            acceptance_radius: How close AI needs to get to destination
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UAIBlueprintHelperLibrary",
            "function_name": "SimpleMoveToActor",
            "params": {"AcceptanceRadius": acceptance_radius},
            "node_position": node_position
        })

    @mcp.tool()
    def set_blackboard_value(
        ctx: Context,
        blueprint_name: str,
        key_name: str,
        value_type: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Set Blackboard Value as [Type]' node.

        Args:
            blueprint_name: Blueprint name (usually AIController or BTTask)
            key_name: Blackboard key name
            value_type: Value type ("Object", "Vector", "Bool", "Float", "Int", "String")
            node_position: Optional graph position
        """
        if node_position is None:
            node_position = [0, 0]
        function_map = {
            "Object": "SetValueAsObject",
            "Actor": "SetValueAsObject",
            "Vector": "SetValueAsVector",
            "Bool": "SetValueAsBool",
            "Boolean": "SetValueAsBool",
            "Float": "SetValueAsFloat",
            "Int": "SetValueAsInt",
            "Integer": "SetValueAsInt",
            "String": "SetValueAsString",
            "Name": "SetValueAsName",
            "Rotator": "SetValueAsRotator",
            "Class": "SetValueAsClass",
        }
        func_name = function_map.get(value_type, "SetValueAsObject")
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UBlackboardComponent",
            "function_name": func_name,
            "params": {"KeyName": key_name},
            "node_position": node_position
        })

    @mcp.tool()
    def create_full_enemy_ai(
        ctx: Context,
        enemy_name: str,
        has_patrol: bool = True,
        has_chase: bool = True,
        has_attack: bool = True
    ) -> Dict[str, Any]:
        """
        Create a complete enemy AI setup including:
        - Enemy Character Blueprint
        - AIController Blueprint
        - Blackboard with appropriate keys
        - Behavior Tree with patrol/chase/attack logic
        - BT Tasks for each behavior

        Args:
            enemy_name: Base name (e.g., "Enemy" creates BP_Enemy, BT_Enemy, etc.)
            has_patrol: Include patrol behavior
            has_chase: Include chase player behavior
            has_attack: Include attack behavior
        """
        results = {}

        # Create Blackboard with keys
        bb_keys = [
            {"name": "PlayerActor", "type": "Object"},
            {"name": "LastKnownLocation", "type": "Vector"},
            {"name": "bCanSeePlayer", "type": "Boolean"},
        ]
        if has_patrol:
            bb_keys.append({"name": "PatrolTarget", "type": "Vector"})
        if has_attack:
            bb_keys.append({"name": "bIsAttacking", "type": "Boolean"})

        results["blackboard"] = _send("create_blackboard", {
            "name": f"BB_{enemy_name}",
            "keys": bb_keys,
            "path": "/Game/AI"
        })

        # Create Behavior Tree
        results["behavior_tree"] = _send("create_behavior_tree", {
            "name": f"BT_{enemy_name}",
            "path": "/Game/AI"
        })

        # Create BT Tasks
        if has_patrol:
            results["task_patrol"] = _send("create_blueprint", {
                "name": f"BTT_{enemy_name}_Patrol",
                "parent_class": "BTTask_BlueprintBase"
            })
            _send("compile_blueprint", {"blueprint_name": f"BTT_{enemy_name}_Patrol"})

        if has_chase:
            results["task_chase"] = _send("create_blueprint", {
                "name": f"BTT_{enemy_name}_Chase",
                "parent_class": "BTTask_BlueprintBase"
            })
            _send("compile_blueprint", {"blueprint_name": f"BTT_{enemy_name}_Chase"})

        if has_attack:
            results["task_attack"] = _send("create_blueprint", {
                "name": f"BTT_{enemy_name}_Attack",
                "parent_class": "BTTask_BlueprintBase"
            })
            _send("compile_blueprint", {"blueprint_name": f"BTT_{enemy_name}_Attack"})

        # Create AI Service for perception
        results["service"] = _send("create_blueprint", {
            "name": f"BTS_{enemy_name}_Perception",
            "parent_class": "BTService_BlueprintBase"
        })
        _send("compile_blueprint", {"blueprint_name": f"BTS_{enemy_name}_Perception"})

        # Create AI Controller
        results["ai_controller"] = _send("create_blueprint", {
            "name": f"BP_{enemy_name}AIController",
            "parent_class": "AIController"
        })
        _send("compile_blueprint", {"blueprint_name": f"BP_{enemy_name}AIController"})

        # Create Enemy Character
        results["enemy_character"] = _send("create_blueprint", {
            "name": f"BP_{enemy_name}",
            "parent_class": "Character"
        })
        _send("add_blueprint_variable", {
            "blueprint_name": f"BP_{enemy_name}",
            "variable_name": "MaxHealth",
            "variable_type": "Float",
            "is_exposed": True
        })
        _send("add_blueprint_variable", {
            "blueprint_name": f"BP_{enemy_name}",
            "variable_name": "CurrentHealth",
            "variable_type": "Float",
            "is_exposed": False
        })
        _send("add_blueprint_variable", {
            "blueprint_name": f"BP_{enemy_name}",
            "variable_name": "AttackDamage",
            "variable_type": "Float",
            "is_exposed": True
        })
        _send("set_blueprint_property", {
            "blueprint_name": f"BP_{enemy_name}",
            "property_name": "AIControllerClass",
            "property_value": f"BP_{enemy_name}AIController"
        })
        _send("set_blueprint_property", {
            "blueprint_name": f"BP_{enemy_name}",
            "property_name": "AutoPossessAI",
            "property_value": "PlacedInWorldOrSpawned"
        })
        _send("compile_blueprint", {"blueprint_name": f"BP_{enemy_name}"})

        return results

    # ─── Chapter 10 Advanced AI ──────────────────────────────────────────────────

    @mcp.tool()
    def create_bt_attack_task(
        ctx: Context,
        name: str = "BTTask_DoAttack",
        damage_variable: str = "Damage",
        default_damage: float = 0.25,
        target_key_variable: str = "TargetActorKey",
        path: str = "/Game/AI"
    ) -> Dict[str, Any]:
        """
        Create a Behavior Tree Attack Task Blueprint.

        Ch.10: BTTask_DoAttack that deals damage to the player.
        - TargetActorKey (BlackboardKeySelector) - instance editable
        - Damage (Float, instance editable, default 0.25 = 25% of player health)
        - Overrides ReceiveExecute: checks IsValid on target, calls Apply Damage,
          then calls FinishExecute(Success=true)

        Args:
            name: Task Blueprint name (e.g., "BTTask_DoAttack")
            damage_variable: Name of the damage float variable
            default_damage: Default damage amount (0.0-1.0 normalized or raw)
            target_key_variable: Name of the BlackboardKeySelector variable
            path: Content browser path
        """
        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "BTTask_BlueprintBase"
        })
        # Add TargetActorKey variable (BlackboardKeySelector, instance editable)
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": target_key_variable,
            "variable_type": "BlackboardKeySelector",
            "is_exposed": True
        })
        # Add Damage variable (Float, instance editable)
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": damage_variable,
            "variable_type": "Float",
            "is_exposed": True,
            "default_value": str(default_damage)
        })
        # Set the Node Name property visible in BT
        _send("set_blueprint_property", {
            "blueprint_name": name,
            "property_name": "NodeName",
            "property_value": "DoAttack"
        })
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def add_pawn_sensing_component(
        ctx: Context,
        blueprint_name: str,
        hearing_threshold: float = 1600.0,
        see_pawns_in_dark: bool = True,
        sight_radius: float = 2000.0,
        peripheral_vision_angle: float = 45.0
    ) -> Dict[str, Any]:
        """
        Add a PawnSensing component to a Blueprint for AI perception.

        Ch.10: PawnSensing enables enemies to both see and hear the player.
        - OnSeePawn and OnHearNoise events fire when player is detected.
        - HearingThreshold: detection radius for sound (default 1600 units)
        - SightRadius: max sight distance
        - PeripheralVisionAngle: field of view half-angle in degrees

        Args:
            blueprint_name: Enemy character Blueprint
            hearing_threshold: Sound detection radius in cm
            see_pawns_in_dark: Whether to detect pawns in dark areas
            sight_radius: Max sight detection radius
            peripheral_vision_angle: Half-angle of sight cone in degrees
        """
        result = _send("add_component_to_blueprint", {
            "blueprint_name": blueprint_name,
            "component_type": "PawnSensingComponent",
            "component_name": "PawnSensing"
        })
        _send("set_component_property", {
            "blueprint_name": blueprint_name,
            "component_name": "PawnSensing",
            "property_name": "HearingThreshold",
            "property_value": hearing_threshold
        })
        _send("set_component_property", {
            "blueprint_name": blueprint_name,
            "component_name": "PawnSensing",
            "property_name": "SightRadius",
            "property_value": sight_radius
        })
        _send("set_component_property", {
            "blueprint_name": blueprint_name,
            "component_name": "PawnSensing",
            "property_name": "PeripheralVisionAngle",
            "property_value": peripheral_vision_angle
        })
        _send("set_component_property", {
            "blueprint_name": blueprint_name,
            "component_name": "PawnSensing",
            "property_name": "bSeePawns",
            "property_value": see_pawns_in_dark
        })
        _send("compile_blueprint", {"blueprint_name": blueprint_name})
        return result

    @mcp.tool()
    def add_on_see_pawn_event(
        ctx: Context,
        blueprint_name: str,
        pawn_sensing_component: str = "PawnSensing",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Bind the 'On See Pawn' event from a PawnSensing component.

        Ch.10: OnSeePawn fires when the AI spots the player in its sight cone.
        Wire this to set the PlayerCharacter blackboard key and update chase state.

        Args:
            blueprint_name: Enemy Blueprint name
            pawn_sensing_component: Name of PawnSensing component
            node_position: Optional [X, Y] graph position
        """
        return _send("add_component_event_node", {
            "blueprint_name": blueprint_name,
            "component_name": pawn_sensing_component,
            "event_name": "OnSeePawn",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_on_hear_noise_event(
        ctx: Context,
        blueprint_name: str,
        pawn_sensing_component: str = "PawnSensing",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Bind the 'On Hear Noise' event from a PawnSensing component.

        Ch.10: OnHearNoise fires when the AI detects a sound within HearingThreshold.
        Event provides: PawnInstigator (who made the sound), Location (where), Loudness.
        Wire to UpdateSoundBB macro to store HasHeardSound=true and LocationOfSound.

        Args:
            blueprint_name: Enemy AI Controller Blueprint
            pawn_sensing_component: Name of PawnSensing component
            node_position: Optional [X, Y] graph position
        """
        return _send("add_component_event_node", {
            "blueprint_name": blueprint_name,
            "component_name": pawn_sensing_component,
            "event_name": "OnHearNoise",
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_report_noise_event_node(
        ctx: Context,
        blueprint_name: str,
        loudness: float = 1.0,
        max_range: float = 0.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Report Noise Event' node (UAISense_Hearing).

        Ch.10: Reports a noise to the AI perception system so PawnSensing can detect it.
        Used to make the player's actions (shooting, footsteps) audible to AI.

        Args:
            blueprint_name: Blueprint name (usually player Character)
            loudness: How loud the noise is (0.0-1.0)
            max_range: Max range the noise can be heard (0 = use PawnSensing threshold)
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UGameplayStatics",
            "function_name": "ReportNoise",
            "params": {
                "Loudness": loudness,
                "MaxRange": max_range
            },
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def create_enemy_spawner_blueprint(
        ctx: Context,
        name: str = "BP_EnemySpawner",
        enemy_class: str = "BP_EnemyCharacter",
        max_enemies: int = 5,
        spawn_interval: float = 5.0,
        spawn_radius: float = 500.0,
        path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create an Enemy Spawner Blueprint.

        Ch.10: BP_EnemySpawner periodically spawns enemies in the level.
        - EnemyClass variable (class reference, instance editable)
        - MaxEnemies variable (int) - cap on simultaneous enemies
        - SpawnInterval variable (float) - seconds between spawns
        - SpawnRadius variable (float) - radius around spawner to place enemies
        - Timer-based spawning using Set Timer by Function Name

        Args:
            name: Spawner Blueprint name
            enemy_class: Enemy Blueprint class to spawn
            max_enemies: Maximum simultaneous enemy count
            spawn_interval: Seconds between each spawn
            spawn_radius: Random placement radius around spawner
            path: Content browser path
        """
        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "Actor"
        })
        # Add variables
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "EnemyClass",
            "variable_type": "Class",
            "is_exposed": True
        })
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "MaxEnemies",
            "variable_type": "Integer",
            "is_exposed": True,
            "default_value": str(max_enemies)
        })
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "SpawnInterval",
            "variable_type": "Float",
            "is_exposed": True,
            "default_value": str(spawn_interval)
        })
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "SpawnRadius",
            "variable_type": "Float",
            "is_exposed": True,
            "default_value": str(spawn_radius)
        })
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "CurrentEnemyCount",
            "variable_type": "Integer",
            "is_exposed": False
        })
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def create_bt_wander_task(
        ctx: Context,
        name: str = "BTTask_FindWanderPoint",
        wander_radius: float = 1000.0,
        path: str = "/Game/AI"
    ) -> Dict[str, Any]:
        """
        Create a Behavior Tree Task for random wandering.

        Ch.10: BTTask_FindWanderPoint uses the Navigation system to find a random
        reachable location within a radius for enemy wandering behavior.
        - Uses GetRandomReachablePointInRadius
        - Sets the resulting Vector to a Blackboard key (e.g., WanderTarget)
        - Returns Success if a point is found, Failure otherwise

        Args:
            name: Task Blueprint name
            wander_radius: Radius to search for random wander points
            path: Content browser path
        """
        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "BTTask_BlueprintBase"
        })
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "WanderTargetKey",
            "variable_type": "BlackboardKeySelector",
            "is_exposed": True
        })
        _send("add_blueprint_variable", {
            "blueprint_name": name,
            "variable_name": "WanderRadius",
            "variable_type": "Float",
            "is_exposed": True,
            "default_value": str(wander_radius)
        })
        _send("set_blueprint_property", {
            "blueprint_name": name,
            "property_name": "NodeName",
            "property_value": "Find Wander Point"
        })
        _send("compile_blueprint", {"blueprint_name": name})
        return result

    @mcp.tool()
    def add_get_random_reachable_point_node(
        ctx: Context,
        blueprint_name: str,
        radius: float = 1000.0,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Random Reachable Point In Radius' node.

        Ch.10: Used in wandering BT task to find a valid NavMesh location.
        Returns bReachable (bool) and RandomLocation (Vector).
        Wire to SetValueAsVector on blackboard to store the wander destination.

        Args:
            blueprint_name: Blueprint name (usually BTTask Blueprint)
            radius: Search radius for random point
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UNavigationSystemV1",
            "function_name": "GetRandomReachablePointInRadius",
            "params": {"Radius": radius},
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_finish_execute_node(
        ctx: Context,
        blueprint_name: str,
        success: bool = True,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Finish Execute' node to a Behavior Tree Task Blueprint.

        Ch.10: BTTask Blueprints must call FinishExecute to report success or failure
        back to the Behavior Tree. Call this at the end of ReceiveExecute.

        Args:
            blueprint_name: BT Task Blueprint name
            success: True = task succeeded, False = task failed
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "self",
            "function_name": "FinishExecute",
            "params": {"bSuccess": success},
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_get_blackboard_value_node(
        ctx: Context,
        blueprint_name: str,
        key_name: str,
        value_type: str = "Object",
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Get Blackboard Value as [Type]' node.

        Ch.10: Used in BT Tasks to read data from the Blackboard.
        e.g., Get Blackboard Value as Actor to get the Target Actor reference.

        Args:
            blueprint_name: Blueprint name (BT Task or AI Controller)
            key_name: Blackboard key name to read
            value_type: "Object", "Actor", "Vector", "Bool", "Float", "Int", "String"
            node_position: Optional [X, Y] graph position
        """
        function_map = {
            "Object": "GetValueAsObject",
            "Actor": "GetValueAsObject",
            "Vector": "GetValueAsVector",
            "Bool": "GetValueAsBool",
            "Boolean": "GetValueAsBool",
            "Float": "GetValueAsFloat",
            "Int": "GetValueAsInt",
            "Integer": "GetValueAsInt",
            "String": "GetValueAsString",
            "Name": "GetValueAsName",
            "Rotator": "GetValueAsRotator",
            "Class": "GetValueAsClass",
        }
        func_name = function_map.get(value_type, "GetValueAsObject")
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UBlackboardComponent",
            "function_name": func_name,
            "params": {"KeyName": key_name},
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_clear_blackboard_value_node(
        ctx: Context,
        blueprint_name: str,
        key_name: str,
        node_position: List[float] = None
    ) -> Dict[str, Any]:
        """
        Add a 'Clear Blackboard Value' node (BTTask_ClearBBValue).

        Ch.10: Used to reset blackboard keys like HasHeardSound after investigation
        is complete. Resets the value to its default (false/null/zero).

        Args:
            blueprint_name: Blueprint or BT Task name
            key_name: Blackboard key to clear
            node_position: Optional [X, Y] graph position
        """
        return _send("add_blueprint_function_node", {
            "blueprint_name": blueprint_name,
            "target": "UBlackboardComponent",
            "function_name": "ClearValue",
            "params": {"KeyName": key_name},
            "node_position": node_position or [0, 0]
        })

    @mcp.tool()
    def add_bt_blackboard_decorator(
        ctx: Context,
        behavior_tree_name: str,
        sequence_name: str,
        blackboard_key: str,
        observer_aborts: str = "LowerPriority",
        node_name: str = ""
    ) -> Dict[str, Any]:
        """
        Add a Blackboard Decorator to a Behavior Tree sequence/task node.

        Ch.10: Decorators are conditions that control whether a BT branch can execute.
        A Blackboard Decorator checks a key's value to allow or abort execution.

        Args:
            behavior_tree_name: Behavior Tree asset name
            sequence_name: Name of the Sequence/Task node to decorate
            blackboard_key: Blackboard key to monitor (e.g., "HasHeardSound", "bCanSeePlayer")
            observer_aborts: "None", "Self", "LowerPriority", "Both"
            node_name: Display name for the decorator node
        """
        return _send("add_bt_blackboard_decorator", {
            "behavior_tree_name": behavior_tree_name,
            "sequence_name": sequence_name,
            "blackboard_key": blackboard_key,
            "observer_aborts": observer_aborts,
            "node_name": node_name or f"{blackboard_key}?"
        })

    @mcp.tool()
    def create_full_upgraded_enemy_ai(
        ctx: Context,
        enemy_name: str,
        has_patrol: bool = True,
        has_chase: bool = True,
        has_attack: bool = True,
        has_hearing: bool = True,
        has_wandering: bool = True,
        attack_damage: float = 0.25,
        hearing_distance: float = 1600.0
    ) -> Dict[str, Any]:
        """
        Create a complete upgraded enemy AI setup from Ch.9-10.

        Builds:
        - Enemy Character Blueprint (with PawnSensing, health variables)
        - AI Controller Blueprint (runs BT, handles OnSeePawn/OnHearNoise)
        - Blackboard with all keys (PlayerCharacter, HasHeardSound, LocationOfSound,
          CurrentPatrolPoint, bCanSeePlayer)
        - Behavior Tree with Patrol/Chase/Attack/Investigate/Wander sequences
        - BTTask_DoAttack with configurable damage
        - BTTask_FindWanderPoint for random wandering
        - Enemy Spawner Blueprint for wave-based spawning

        Args:
            enemy_name: Base name (creates BP_Enemy, BT_Enemy, BB_Enemy, etc.)
            has_patrol: Include patrol behavior with patrol points
            has_chase: Include player-chasing behavior
            has_attack: Include melee attack behavior
            has_hearing: Include sound-detection behavior
            has_wandering: Include random wandering behavior
            attack_damage: Damage dealt per attack (0.25 = 25% of health)
            hearing_distance: PawnSensing hearing radius in cm
        """
        results = {}

        # Create Blackboard with all keys
        bb_keys = [
            {"name": "PlayerCharacter", "type": "Object"},
            {"name": "LastKnownLocation", "type": "Vector"},
            {"name": "bCanSeePlayer", "type": "Boolean"},
        ]
        if has_patrol:
            bb_keys.append({"name": "CurrentPatrolPoint", "type": "Object"})
        if has_hearing:
            bb_keys.append({"name": "HasHeardSound", "type": "Boolean"})
            bb_keys.append({"name": "LocationOfSound", "type": "Vector"})
        if has_wandering:
            bb_keys.append({"name": "WanderTarget", "type": "Vector"})

        results["blackboard"] = _send("create_blackboard", {
            "name": f"BB_{enemy_name}",
            "keys": bb_keys,
            "path": "/Game/AI"
        })

        # Create Behavior Tree
        results["behavior_tree"] = _send("create_behavior_tree", {
            "name": f"BT_{enemy_name}",
            "path": "/Game/AI"
        })

        # Create BT Tasks
        if has_attack:
            results["task_attack"] = _send("create_blueprint", {
                "name": f"BTTask_{enemy_name}_DoAttack",
                "parent_class": "BTTask_BlueprintBase"
            })
            _send("add_blueprint_variable", {
                "blueprint_name": f"BTTask_{enemy_name}_DoAttack",
                "variable_name": "TargetActorKey",
                "variable_type": "BlackboardKeySelector",
                "is_exposed": True
            })
            _send("add_blueprint_variable", {
                "blueprint_name": f"BTTask_{enemy_name}_DoAttack",
                "variable_name": "Damage",
                "variable_type": "Float",
                "is_exposed": True,
                "default_value": str(attack_damage)
            })
            _send("compile_blueprint", {"blueprint_name": f"BTTask_{enemy_name}_DoAttack"})

        if has_wandering:
            results["task_wander"] = _send("create_blueprint", {
                "name": f"BTTask_{enemy_name}_FindWanderPoint",
                "parent_class": "BTTask_BlueprintBase"
            })
            _send("add_blueprint_variable", {
                "blueprint_name": f"BTTask_{enemy_name}_FindWanderPoint",
                "variable_name": "WanderTargetKey",
                "variable_type": "BlackboardKeySelector",
                "is_exposed": True
            })
            _send("compile_blueprint", {"blueprint_name": f"BTTask_{enemy_name}_FindWanderPoint"})

        # Create AI Controller
        results["ai_controller"] = _send("create_blueprint", {
            "name": f"BP_{enemy_name}AIController",
            "parent_class": "AIController"
        })
        _send("add_blueprint_variable", {
            "blueprint_name": f"BP_{enemy_name}AIController",
            "variable_name": "HearingDistance",
            "variable_type": "Float",
            "is_exposed": True,
            "default_value": str(hearing_distance)
        })
        if has_hearing:
            _send("add_blueprint_variable", {
                "blueprint_name": f"BP_{enemy_name}AIController",
                "variable_name": "HasHeardSoundKey",
                "variable_type": "Name",
                "default_value": "HasHeardSound"
            })
            _send("add_blueprint_variable", {
                "blueprint_name": f"BP_{enemy_name}AIController",
                "variable_name": "LocationOfSoundKey",
                "variable_type": "Name",
                "default_value": "LocationOfSound"
            })
        _send("compile_blueprint", {"blueprint_name": f"BP_{enemy_name}AIController"})

        # Create Enemy Character with PawnSensing
        results["enemy_character"] = _send("create_blueprint", {
            "name": f"BP_{enemy_name}",
            "parent_class": "Character"
        })
        _send("add_component_to_blueprint", {
            "blueprint_name": f"BP_{enemy_name}",
            "component_type": "PawnSensingComponent",
            "component_name": "PawnSensing"
        })
        _send("set_component_property", {
            "blueprint_name": f"BP_{enemy_name}",
            "component_name": "PawnSensing",
            "property_name": "HearingThreshold",
            "property_value": hearing_distance
        })
        _send("add_blueprint_variable", {
            "blueprint_name": f"BP_{enemy_name}",
            "variable_name": "MaxHealth",
            "variable_type": "Float",
            "is_exposed": True,
            "default_value": "100.0"
        })
        _send("add_blueprint_variable", {
            "blueprint_name": f"BP_{enemy_name}",
            "variable_name": "CurrentHealth",
            "variable_type": "Float"
        })
        if has_patrol:
            _send("add_blueprint_variable", {
                "blueprint_name": f"BP_{enemy_name}",
                "variable_name": "PatrolPoints",
                "variable_type": "Array<Actor>",
                "is_exposed": True
            })
            _send("add_blueprint_variable", {
                "blueprint_name": f"BP_{enemy_name}",
                "variable_name": "CurrentPatrolIndex",
                "variable_type": "Integer"
            })
        _send("set_blueprint_property", {
            "blueprint_name": f"BP_{enemy_name}",
            "property_name": "AIControllerClass",
            "property_value": f"BP_{enemy_name}AIController"
        })
        _send("set_blueprint_property", {
            "blueprint_name": f"BP_{enemy_name}",
            "property_name": "AutoPossessAI",
            "property_value": "PlacedInWorldOrSpawned"
        })
        _send("compile_blueprint", {"blueprint_name": f"BP_{enemy_name}"})

        # Create Enemy Spawner
        results["enemy_spawner"] = _send("create_blueprint", {
            "name": f"BP_{enemy_name}Spawner",
            "parent_class": "Actor"
        })
        _send("add_blueprint_variable", {
            "blueprint_name": f"BP_{enemy_name}Spawner",
            "variable_name": "MaxEnemies",
            "variable_type": "Integer",
            "is_exposed": True,
            "default_value": "5"
        })
        _send("add_blueprint_variable", {
            "blueprint_name": f"BP_{enemy_name}Spawner",
            "variable_name": "SpawnInterval",
            "variable_type": "Float",
            "is_exposed": True,
            "default_value": "5.0"
        })
        _send("compile_blueprint", {"blueprint_name": f"BP_{enemy_name}Spawner"})

        return results

    # ── BT Graph Editing Tools ───────────────────────────────────────────────

    @mcp.tool()
    def repair_behavior_tree(
        ctx: Context,
        behavior_tree_name: str
    ) -> Dict[str, Any]:
        """
        Repair a corrupted Behavior Tree asset so it can be opened in the UE5 BT editor.

        BT assets created before the NotifyGraphChanged crash fix was applied may be
        saved with incomplete node data. Opening them in the editor crashes at 0x68
        because UpdateAsset() dereferences a null IBehaviorTreeEditor* listener.

        This command:
          1. Closes any open editor windows for the asset
          2. Wipes all non-Root graph nodes (safe, no NotifyGraphChanged)
          3. Recreates the Root node via schema if missing
          4. Calls SpawnMissingNodes + UpdateAsset + saves to disk

        After repair the asset is in a Root-only (empty) state that the editor
        can open safely. Use build_behavior_tree to repopulate the tree logic.

        Args:
            behavior_tree_name: Name of the BT asset to repair (e.g. "BT_EnemyInfantry")

        Returns:
            Dict with 'success', 'behavior_tree', 'node_count_after_repair', 'message'
        """
        return _send("repair_behavior_tree", {
            "behavior_tree_name": behavior_tree_name,
        })

    @mcp.tool()
    def build_behavior_tree(
        ctx: Context,
        behavior_tree_name: str,
        tree: Dict[str, Any],
        clear_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Build an entire Behavior Tree graph from a JSON description in one call.

        This is the primary tool for creating BT logic. Pass the full tree as a
        nested JSON object and the C++ plugin will build every node, link pins,
        attach decorators/services, and save the asset.

        Node type strings (case-insensitive):
          Composites : "Selector", "Sequence"
          Tasks      : "Wait", "MoveTo"
          Custom     : full class name e.g. "BTTask_MyCustomTask" or Blueprint path

        Tree format:
          {
            "type": "Selector",
            "children": [
              {
                "type": "Sequence",
                "decorators": [{"type": "BTDecorator_Blackboard", "properties": {...}}],
                "services":   [{"type": "BTService_DefaultFocus"}],
                "children": [
                  {"type": "MoveTo",  "properties": {"AcceptableRadius": "50.0"}},
                  {"type": "Wait",    "properties": {"WaitTime": "2.0"}}
                ]
              }
            ]
          }

        Args:
            behavior_tree_name: Name of an EXISTING BT asset (create_behavior_tree first)
            tree:               Root node JSON object (see format above)
            clear_existing:     If True (default), remove all non-root nodes first

        Returns:
            Dict with 'success', 'behavior_tree', 'nodes_created', 'nodes' list
        """
        return _send("build_behavior_tree", {
            "behavior_tree_name": behavior_tree_name,
            "tree": tree,
            "clear_existing": clear_existing,
        })

    @mcp.tool()
    def add_bt_node(
        ctx: Context,
        behavior_tree_name: str,
        node_type: str,
        parent_node_index: int = -1,
        x: float = 0.0,
        y: float = 0.0,
        properties: Dict[str, Any] = {},
        decorators: List[Dict[str, Any]] = [],
        services: List[Dict[str, Any]] = []
    ) -> Dict[str, Any]:
        """
        Add a single node to an existing Behavior Tree graph.

        Use this for incremental edits — add one node at a time after the
        initial tree is built with build_behavior_tree.

        Node type strings (case-insensitive):
          "Selector", "Sequence", "Wait", "MoveTo"
          or a full Blueprint class name/path for custom tasks.

        Args:
            behavior_tree_name: Name of the existing BT asset
            node_type:          Node type string (see above)
            parent_node_index:  0-based index in the graph Nodes array (skip root).
                                -1 = attach directly to root.
            x:                  Graph X position (0 = auto)
            y:                  Graph Y position (0 = auto)
            properties:         Dict of property name → string value for the node instance
                                e.g. {"WaitTime": "3.0", "AcceptableRadius": "100.0"}
            decorators:         List of {"type": "..."} objects for decorator sub-nodes
            services:           List of {"type": "..."} objects for service sub-nodes

        Returns:
            Dict with 'success', 'node_type', 'node_index'
        """
        params: Dict[str, Any] = {
            "behavior_tree_name": behavior_tree_name,
            "node_type": node_type,
            "parent_node_index": parent_node_index,
        }
        if x != 0.0:
            params["x"] = x
        if y != 0.0:
            params["y"] = y
        if properties:
            params["properties"] = properties
        if decorators:
            params["decorators"] = decorators
        if services:
            params["services"] = services
        return _send("add_bt_node", params)

    @mcp.tool()
    def get_bt_graph_info(
        ctx: Context,
        behavior_tree_name: str
    ) -> Dict[str, Any]:
        """
        Inspect the current state of a Behavior Tree graph.

        Returns every node in the BT graph with its type, position, instance class,
        pin connections, and sub-nodes (decorators/services). Use this to verify
        build_behavior_tree or add_bt_node worked correctly.

        Args:
            behavior_tree_name: Name of the BT asset to inspect

        Returns:
            Dict with 'success', 'node_count', 'nodes' array where each node has:
              - 'class':    graph node class name
              - 'instance': runtime BTNode class name
              - 'x', 'y':  graph position
              - 'pins':     pin names and connections
              - 'subnodes': decorator/service sub-nodes
        """
        return _send("get_bt_graph_info", {
            "behavior_tree_name": behavior_tree_name,
        })

    @mcp.tool()
    def bt_add_selector_wait(
        ctx: Context,
        behavior_tree_name: str,
        wait_time: float = 1.0
    ) -> Dict[str, Any]:
        """
        Quick-build: add a root Selector with a single Wait task.

        This is a shortcut for the most basic "idle" behavior tree structure:
          Root → Selector → Wait(wait_time)

        Use build_behavior_tree for full tree construction. This is a convenience
        tool for testing or placeholder BTs.

        Args:
            behavior_tree_name: Name of the existing BT asset
            wait_time:          Wait duration in seconds (default 1.0)

        Returns:
            Dict with 'success', 'behavior_tree'
        """
        return _send("bt_add_selector_wait", {
            "behavior_tree_name": behavior_tree_name,
            "wait_time": wait_time,
        })

    logger.info("AI tools registered")
