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

    logger.info("AI tools registered")
