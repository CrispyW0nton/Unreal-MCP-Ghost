"""
SaveGame & Game State Tools for Unreal MCP.
Covers Chapter 11 (Game States and Finishing Touches) from the Blueprint book.

Provides tools for:
- Creating SaveGame Blueprint classes (Ch. 11)
- Save/Load game data (SaveGameToSlot, LoadGameFromSlot, DoesSaveGameExist)
- Round-based game scaling system
- Game state management (pause, win/lose screens)
- Player death handling
- Set Game Paused, Show Mouse Cursor
- Transition/round screens
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


def register_savegame_tools(mcp: FastMCP):

    @mcp.tool()
    def create_savegame_blueprint(
        ctx: Context,
        name: str,
        variables: List[Dict[str, Any]] = None,
        folder_path: str = "/Game/Blueprints"
    ) -> Dict[str, Any]:
        """
        Create a SaveGame Blueprint class to store persistent game data.

        From Ch. 11 of the book: create BP_SaveInfo as a child of SaveGame.
        SaveGame Blueprints hold variables like current Round, high score,
        player settings, etc. that persist between play sessions.

        Args:
            name: Blueprint name (e.g., \"BP_SaveInfo\")
            variables: List of variable definitions, each a dict with:
                       {\"name\": str, \"type\": str, \"default_value\": any}
                       Types: \"Integer\", \"Float\", \"Boolean\", \"String\", \"Vector\"
            folder_path: Content browser folder path

        Example variables:
            [{\"name\": \"Round\", \"type\": \"Integer\", \"default_value\": 1},
             {\"name\": \"HighScore\", \"type\": \"Integer\", \"default_value\": 0}]
        """
        if variables is None:
            variables = [{"name": "Round", "type": "Integer", "default_value": 1}]

        result = _send("create_blueprint", {
            "name": name,
            "parent_class": "SaveGame",
            "folder_path": folder_path
        })

        if not result.get("success", True):
            return result

        for var in variables:
            _send("add_blueprint_variable", {
                "blueprint_name": name,
                "variable_name": var["name"],
                "variable_type": var.get("type", "Integer"),
                "is_exposed": False
            })
            if "default_value" in var:
                _send("set_blueprint_property", {
                    "blueprint_name": name,
                    "property_name": var["name"],
                    "property_value": var["default_value"]
                })

        _send("compile_blueprint", {"blueprint_name": name})
        return {"success": True, "message": f"SaveGame Blueprint '{name}' created with {len(variables)} variable(s)"}

    @mcp.tool()
    def add_save_game_to_slot_node(
        ctx: Context,
        blueprint_name: str,
        save_game_variable: str = "SaveInfoRef",
        slot_name_variable: str = "SaveSlotName",
        user_index: int = 0,
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add a SaveGameToSlot node to a Blueprint.

        From Ch. 11: saves the SaveGame object to a named slot on disk.
        This corresponds to the \"Save Game to Slot\" node in the Blueprint graph.

        Args:
            blueprint_name: Blueprint to add the node to
            save_game_variable: Variable holding the SaveGame instance reference
            slot_name_variable: Variable holding the save slot filename string
            user_index: Player index (use 0 for single player)
            node_position: [X, Y] graph position
        """
        return _send("add_save_game_to_slot_node", {
            "blueprint_name": blueprint_name,
            "save_game_variable": save_game_variable,
            "slot_name_variable": slot_name_variable,
            "user_index": user_index,
            "node_position": node_position
        })

    @mcp.tool()
    def add_load_game_from_slot_node(
        ctx: Context,
        blueprint_name: str,
        slot_name_variable: str = "SaveSlotName",
        save_game_class: str = "BP_SaveInfo",
        save_game_variable: str = "SaveInfoRef",
        user_index: int = 0,
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add LoadGameFromSlot + DoesSaveGameExist + Cast nodes to a Blueprint.

        From Ch. 11: the complete LoadRound macro pattern. Checks if a save
        file exists, loads it, casts to the SaveGame class, and stores the
        reference. Uses Branch node to handle both existing and new save files.

        Args:
            blueprint_name: Blueprint to add nodes to
            slot_name_variable: Variable holding the save slot filename
            save_game_class: SaveGame Blueprint class name (e.g., \"BP_SaveInfo\")
            save_game_variable: Variable to store the loaded SaveGame reference
            user_index: Player index
            node_position: [X, Y] graph position for the first node
        """
        return _send("add_load_game_from_slot_node", {
            "blueprint_name": blueprint_name,
            "slot_name_variable": slot_name_variable,
            "save_game_class": save_game_class,
            "save_game_variable": save_game_variable,
            "user_index": user_index,
            "node_position": node_position
        })

    @mcp.tool()
    def add_does_save_game_exist_node(
        ctx: Context,
        blueprint_name: str,
        slot_name: str = "SaveGameFile",
        user_index: int = 0,
        node_position: List[int] = [200, 0]
    ) -> Dict[str, Any]:
        """
        Add a DoesSaveGameExist node to check if a save file is present.

        From Ch. 11: used before loading to branch logic - if save exists,
        load it; if not, use defaults (Round 1).

        Args:
            blueprint_name: Blueprint to add the node to
            slot_name: Save slot name string to check
            user_index: Player index
            node_position: [X, Y] graph position
        """
        return _send("add_does_save_game_exist_node", {
            "blueprint_name": blueprint_name,
            "slot_name": slot_name,
            "user_index": user_index,
            "node_position": node_position
        })

    @mcp.tool()
    def add_create_save_game_object_node(
        ctx: Context,
        blueprint_name: str,
        save_game_class: str = "BP_SaveInfo",
        output_variable: str = "SaveInfoRef",
        node_position: List[int] = [300, 100]
    ) -> Dict[str, Any]:
        """
        Add a CreateSaveGameObject node to instantiate a new SaveGame object.

        From Ch. 11: used when no save file exists yet, to create a fresh
        SaveGame instance before calling SaveGameToSlot.

        Args:
            blueprint_name: Blueprint to add the node to
            save_game_class: SaveGame Blueprint class name
            output_variable: Variable name to store the new instance
            node_position: [X, Y] graph position
        """
        return _send("add_create_save_game_object_node", {
            "blueprint_name": blueprint_name,
            "save_game_class": save_game_class,
            "output_variable": output_variable,
            "node_position": node_position
        })

    @mcp.tool()
    def add_delete_save_game_in_slot_node(
        ctx: Context,
        blueprint_name: str,
        slot_name_variable: str = "SaveSlotName",
        user_index: int = 0,
        node_position: List[int] = [400, 0]
    ) -> Dict[str, Any]:
        """
        Add a DeleteGameInSlot node to reset/clear the save file.

        From Ch. 11 (Resetting the save file from the pause menu).
        Use this to implement a \"New Game\" or \"Reset Progress\" button.

        Args:
            blueprint_name: Blueprint to add the node to
            slot_name_variable: Variable holding the save slot name
            user_index: Player index
            node_position: [X, Y] graph position
        """
        return _send("add_delete_save_game_in_slot_node", {
            "blueprint_name": blueprint_name,
            "slot_name_variable": slot_name_variable,
            "user_index": user_index,
            "node_position": node_position
        })

    @mcp.tool()
    def setup_full_save_load_system(
        ctx: Context,
        character_blueprint: str = "BP_FirstPersonCharacter",
        save_blueprint_name: str = "BP_SaveInfo",
        save_variables: List[Dict[str, Any]] = None,
        slot_name: str = "SaveGameFile"
    ) -> Dict[str, Any]:
        """
        Set up the complete save/load system as described in Ch. 11.

        Creates:
        1. BP_SaveInfo SaveGame Blueprint with Round variable
        2. Variables in character BP: CurrentRound, SaveInfoRef, SaveSlotName
        3. SaveRound macro (check validity, create if new, set round, save to slot)
        4. LoadRound macro (check if exists, load, cast, store reference)

        This mirrors the complete round-persistence system from the book.

        Args:
            character_blueprint: Player character Blueprint name
            save_blueprint_name: SaveGame Blueprint to create
            save_variables: Variables for the save game (default: [{Round: Integer}])
            slot_name: Save file slot name string
        """
        if save_variables is None:
            save_variables = [{"name": "Round", "type": "Integer", "default_value": 1}]

        return _send("setup_full_save_load_system", {
            "character_blueprint": character_blueprint,
            "save_blueprint_name": save_blueprint_name,
            "save_variables": save_variables,
            "slot_name": slot_name
        })

    @mcp.tool()
    def add_set_game_paused_node(
        ctx: Context,
        blueprint_name: str,
        paused: bool = True,
        show_mouse_cursor: bool = True,
        node_position: List[int] = [300, 0]
    ) -> Dict[str, Any]:
        """
        Add SetGamePaused + ShowMouseCursor nodes to pause/unpause the game.

        From Ch. 11 (Creating a pause menu) and Ch. 8 (Win screen).
        Pauses the game tick and optionally shows the mouse cursor for UI interaction.

        Args:
            blueprint_name: Blueprint to add the node to
            paused: True to pause, False to unpause
            show_mouse_cursor: Whether to show the cursor when paused
            node_position: [X, Y] graph position
        """
        return _send("add_set_game_paused_node", {
            "blueprint_name": blueprint_name,
            "paused": paused,
            "show_mouse_cursor": show_mouse_cursor,
            "node_position": node_position
        })

    @mcp.tool()
    def add_quit_game_node(
        ctx: Context,
        blueprint_name: str,
        quit_preference: str = "Quit",
        node_position: List[int] = [400, 100]
    ) -> Dict[str, Any]:
        """
        Add a QuitGame node to exit the application.

        From Ch. 8 (Win/Lose menu Quit button) and Ch. 11 (Pause menu).

        Args:
            blueprint_name: Blueprint to add the node to
            quit_preference: \"Quit\" or \"Background\"
            node_position: [X, Y] graph position
        """
        return _send("add_quit_game_node", {
            "blueprint_name": blueprint_name,
            "quit_preference": quit_preference,
            "node_position": node_position
        })

    @mcp.tool()
    def create_round_based_game_system(
        ctx: Context,
        character_blueprint: str = "BP_FirstPersonCharacter",
        game_mode_blueprint: str = "BP_GameMode",
        save_blueprint_name: str = "BP_SaveInfo",
        round_scale_multiplier: int = 2,
        initial_target_goal: int = 5
    ) -> Dict[str, Any]:
        """
        Create a complete round-based game progression system from Ch. 11.

        Sets up the full arcade-style round system:
        1. SaveGame blueprint for persistent round data
        2. LoadRound / SaveRound macros in the character Blueprint
        3. SetRoundTargetGoal macro to scale difficulty per round
        4. Win condition check that advances rounds
        5. Integration with the save/load system

        Args:
            character_blueprint: Player character Blueprint name
            game_mode_blueprint: GameMode Blueprint name
            save_blueprint_name: SaveGame Blueprint name
            round_scale_multiplier: How much target goal multiplies per round
            initial_target_goal: Starting number of targets to eliminate
        """
        return _send("create_round_based_game_system", {
            "character_blueprint": character_blueprint,
            "game_mode_blueprint": game_mode_blueprint,
            "save_blueprint_name": save_blueprint_name,
            "round_scale_multiplier": round_scale_multiplier,
            "initial_target_goal": initial_target_goal
        })

    @mcp.tool()
    def create_lose_screen_widget(
        ctx: Context,
        widget_name: str = "WBP_LoseMenu",
        message_text: str = "You Lose!",
        message_color: List[float] = [0.6, 0.0, 0.0, 1.0],
        show_restart_button: bool = True,
        show_quit_button: bool = True
    ) -> Dict[str, Any]:
        """
        Create a Lose/Death screen Widget Blueprint as described in Ch. 11.

        Mirrors the Win screen duplication approach from the book. Creates a UMG
        Widget Blueprint with a loss message, restart, and quit buttons.

        Args:
            widget_name: Widget Blueprint name (e.g., \"WBP_LoseMenu\")
            message_text: The main message (e.g., \"You Lose!\")
            message_color: RGBA color for the message [R, G, B, A]
            show_restart_button: Add a Restart (reload level) button
            show_quit_button: Add a Quit Game button
        """
        return _send("create_lose_screen_widget", {
            "widget_name": widget_name,
            "message_text": message_text,
            "message_color": message_color,
            "show_restart_button": show_restart_button,
            "show_quit_button": show_quit_button
        })

    @mcp.tool()
    def create_pause_menu_widget(
        ctx: Context,
        widget_name: str = "WBP_PauseMenu",
        resume_button: bool = True,
        restart_button: bool = True,
        reset_save_button: bool = True,
        quit_button: bool = True
    ) -> Dict[str, Any]:
        """
        Create a Pause Menu Widget Blueprint as described in Ch. 11.

        Creates the pause menu with Resume, Restart, Reset Save, and Quit buttons.
        Also sets up the pause menu toggle (input action -> SetGamePaused + widget).

        Args:
            widget_name: Widget Blueprint name (e.g., \"WBP_PauseMenu\")
            resume_button: Include a Resume (unpause) button
            restart_button: Include a Restart level button
            reset_save_button: Include a Reset Save File button
            quit_button: Include a Quit Game button
        """
        return _send("create_pause_menu_widget", {
            "widget_name": widget_name,
            "resume_button": resume_button,
            "restart_button": restart_button,
            "reset_save_button": reset_save_button,
            "quit_button": quit_button
        })

    @mcp.tool()
    def add_player_death_event(
        ctx: Context,
        blueprint_name: str,
        lose_widget_name: str = "WBP_LoseMenu",
        health_variable: str = "PlayerHealth",
        node_position: List[int] = [300, 0]
    ) -> Dict[str, Any]:
        """
        Add a custom LostGame event to handle player death as described in Ch. 11.

        Creates:
        1. Custom Event \"LostGame\"
        2. SetGamePaused(true)
        3. ShowMouseCursor(true)
        4. CreateWidget(LoseMenu) + AddToViewport
        5. Modify EventAnyDamage to call LostGame when health reaches 0

        Args:
            blueprint_name: Player character Blueprint name
            lose_widget_name: Widget to display on player death
            health_variable: Variable holding player health float
            node_position: [X, Y] graph position for the custom event node
        """
        return _send("add_player_death_event", {
            "blueprint_name": blueprint_name,
            "lose_widget_name": lose_widget_name,
            "health_variable": health_variable,
            "node_position": node_position
        })

    logger.info("SaveGame tools registered successfully")
