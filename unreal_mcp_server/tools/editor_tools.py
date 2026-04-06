"""
Editor Tools - Actor management, viewport, spawning.
Ported from: https://github.com/chongdashu/unreal-mcp
"""
import logging
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

logger = logging.getLogger("UnrealMCP")


def register_editor_tools(mcp: FastMCP):

    @mcp.tool()
    def get_actors_in_level(ctx: Context) -> List[Dict[str, Any]]:
        """Get a list of all actors in the current UE5 level."""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return []
            response = unreal.send_command("get_actors_in_level", {})
            if not response:
                return []
            if "result" in response and "actors" in response["result"]:
                return response["result"]["actors"]
            elif "actors" in response:
                return response["actors"]
            return []
        except Exception as e:
            logger.error(f"Error getting actors: {e}")
            return []

    @mcp.tool()
    def find_actors_by_name(ctx: Context, pattern: str) -> List[str]:
        """Find actors in the level by name pattern (supports wildcards)."""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return []
            response = unreal.send_command("find_actors_by_name", {"pattern": pattern})
            if not response:
                return []
            return response.get("actors", [])
        except Exception as e:
            logger.error(f"Error finding actors: {e}")
            return []

    @mcp.tool()
    def spawn_actor(
        ctx: Context,
        name: str,
        type: str,
        location: List[float] = [0.0, 0.0, 0.0],
        rotation: List[float] = [0.0, 0.0, 0.0]
    ) -> Dict[str, Any]:
        """
        Spawn a new actor in the current level.

        Args:
            name: Unique name for the actor
            type: Actor type (StaticMeshActor, PointLight, Camera, etc.)
            location: [X, Y, Z] world location
            rotation: [Pitch, Yaw, Roll] in degrees
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected to Unreal Engine"}
            params = {
                "name": name,
                "type": type.upper(),
                "location": [float(v) for v in location],
                "rotation": [float(v) for v in rotation]
            }
            response = unreal.send_command("spawn_actor", params)
            return response or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def delete_actor(ctx: Context, name: str) -> Dict[str, Any]:
        """Delete an actor from the level by name."""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("delete_actor", {"name": name}) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_actor_transform(
        ctx: Context,
        name: str,
        location: List[float] = None,
        rotation: List[float] = None,
        scale: List[float] = None
    ) -> Dict[str, Any]:
        """Set the transform (location, rotation, scale) of an actor."""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params = {"name": name}
            if location is not None:
                params["location"] = location
            if rotation is not None:
                params["rotation"] = rotation
            if scale is not None:
                params["scale"] = scale
            return unreal.send_command("set_actor_transform", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_actor_properties(ctx: Context, name: str) -> Dict[str, Any]:
        """Get all properties of an actor by name."""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("get_actor_properties", {"name": name}) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_actor_property(
        ctx: Context,
        name: str,
        property_name: str,
        property_value
    ) -> Dict[str, Any]:
        """Set a specific property on an actor instance."""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("set_actor_property", {
                "name": name,
                "property_name": property_name,
                "property_value": property_value
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def spawn_blueprint_actor(
        ctx: Context,
        blueprint_name: str,
        actor_name: str,
        location: List[float] = [0.0, 0.0, 0.0],
        rotation: List[float] = [0.0, 0.0, 0.0]
    ) -> Dict[str, Any]:
        """
        Spawn an actor in the level from a Blueprint class.

        Args:
            blueprint_name: Name of the Blueprint asset
            actor_name: Name to give the spawned actor
            location: [X, Y, Z] world location
            rotation: [Pitch, Yaw, Roll] in degrees
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            params = {
                "blueprint_name": blueprint_name,
                "actor_name": actor_name,
                "location": [float(v) for v in location],
                "rotation": [float(v) for v in rotation]
            }
            return unreal.send_command("spawn_blueprint_actor", params) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def take_screenshot(
        ctx: Context,
        filename: str = "screenshot",
        show_ui: bool = False,
        resolution: List[int] = [1920, 1080]
    ) -> Dict[str, Any]:
        """Take a screenshot of the Unreal Editor viewport."""
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("take_screenshot", {
                "filename": filename,
                "show_ui": show_ui,
                "resolution": resolution
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("Editor tools registered")
