"""
Project Tools - Input mappings and project-wide settings.
"""
import logging
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_project_tools(mcp: FastMCP):

    @mcp.tool()
    def create_input_mapping(
        ctx: Context,
        action_name: str,
        key: str,
        input_type: str = "Action"
    ) -> Dict[str, Any]:
        """
        Create an input mapping in the project settings (legacy input system).

        Args:
            action_name: Name of the input action (e.g., "Jump", "Fire", "MoveForward")
            key: Key binding (SpaceBar, LeftMouseButton, W, A, S, D,
                 Gamepad_FaceButton_Bottom, etc.)
            input_type: "Action" (button press) or "Axis" (analog/continuous)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("create_input_mapping", {
                "action_name": action_name,
                "key": key,
                "input_type": input_type
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def create_enhanced_input_action(
        ctx: Context,
        action_name: str,
        value_type: str = "Digital",
        path: str = "/Game/Input"
    ) -> Dict[str, Any]:
        """
        Create an Enhanced Input Action asset (UE5 modern input system).

        Args:
            action_name: Name of the input action asset
            value_type: "Digital" (bool), "Axis1D" (float), "Axis2D" (Vector2D), "Axis3D"
            path: Content browser path
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("create_enhanced_input_action", {
                "action_name": action_name,
                "value_type": value_type,
                "path": path
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def create_input_mapping_context(
        ctx: Context,
        context_name: str,
        mappings: List[Dict[str, str]] = None,
        path: str = "/Game/Input"
    ) -> Dict[str, Any]:
        """
        Create an Input Mapping Context for Enhanced Input system.

        Args:
            context_name: Name of the IMC asset
            mappings: List of dicts with 'action' and 'key' fields
            path: Content browser path

        Example mappings:
            [{"action": "IA_Jump", "key": "SpaceBar"},
             {"action": "IA_Move", "key": "W"}]
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("create_input_mapping_context", {
                "context_name": context_name,
                "mappings": mappings or [],
                "path": path
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_input_mapping(imc_name: str, action_name: str, key: str) -> dict:
        """
        Add an input mapping to an existing Input Mapping Context (IMC).
        
        Args:
            imc_name: Name of the Input Mapping Context (e.g., "IMC_Default")
            action_name: Name of the Input Action (e.g., "IA_Jump", "IA_WormholeTP")
            key: Key name to bind (e.g., "SpaceBar", "V", "T", "LeftMouseButton")
        
        Returns:
            dict with success status, imc_name, action_name, key, and mapping_index
        
        Example:
            add_input_mapping("IMC_Default", "IA_WormholeTP", "V")
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("add_input_mapping", {
                "imc_name": imc_name,
                "action_name": action_name,
                "key": key
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("Project tools registered")
