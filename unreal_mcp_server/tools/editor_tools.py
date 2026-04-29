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
    def get_actors_in_level(ctx: Context) -> str:
        """Get a list of all actors in the current UE5 level.

        Returns a compact single-line JSON array of actor objects when the
        editor is connected. When Unreal is unavailable, returns a structured
        JSON error object instead of an empty array so audits do not mistake a
        disconnected bridge for an empty level.
        Example: [{"name": "BP_MyActor", "type": "StaticMeshActor"}, ...]

        Bug #3 fix:
        - Returns a JSON *string* so FastMCP sends it verbatim as a single
          TextContent block (no pydantic_core indent=2 pretty-printing).
        - Connected success responses keep the historical top-level JSON array.
        """
        import json as _json
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return _json.dumps({
                    "success": False,
                    "error_code": "ERR_UNREAL_NOT_CONNECTED",
                    "message": "Not connected to Unreal Engine"
                })
            response = unreal.send_command("get_actors_in_level", {})
            if not response:
                return _json.dumps({
                    "success": False,
                    "error_code": "ERR_UNREAL_NO_RESPONSE",
                    "message": "No response from Unreal Engine"
                })
            if "result" in response and "actors" in response["result"]:
                actors = response["result"]["actors"]
            elif "actors" in response:
                actors = response["actors"]
            else:
                actors = []
            # Compact single-line JSON array — no embedded newlines.
            return _json.dumps(actors)
        except Exception as e:
            logger.error(f"Error getting actors: {e}")
            return _json.dumps({
                "success": False,
                "error_code": "ERR_GET_ACTORS_FAILED",
                "message": str(e)
            })

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

    @mcp.tool()
    def exec_python(ctx: Context, code: str) -> Dict[str, Any]:
        """
        Execute arbitrary Python code inside Unreal Engine via the Python plugin.

        Use this tool when you need to:
        - Create assets in custom project folders (create_blueprint always uses /Game/Blueprints/)
        - Query engine version: import unreal; print(unreal.SystemLibrary.get_engine_version())
        - Count or list assets: unreal.EditorAssetLibrary.list_assets('/Game', recursive=True)
        - Create Widget Blueprints, Behavior Trees, Blackboards, Animation Blueprints
          (use the appropriate factory class since they cannot be created with create_blueprint)
        - Perform bulk operations not covered by other MCP tools

        Args:
            code: Valid Python code string to execute inside UE5.
                  The 'unreal' module is available automatically.
                  Example: "import unreal; print(unreal.SystemLibrary.get_engine_version())"

        Returns:
            dict with 'output' (captured stdout) and 'success' flag.

        IMPORTANT: Always use exec_python for:
          - Assets outside /Game/Blueprints/ (specify full path via AssetTools)
          - Widget Blueprints (WidgetBlueprintFactory)
          - Behavior Trees / Blackboards (BehaviorTreeFactory / BlackboardDataFactory)
          - Animation Blueprints (AnimBlueprintFactory)
          - Checking existing assets before creating duplicates
        """
        from unreal_mcp_server import get_unreal_connection
        import traceback as _tb

        # ── Pre-validate syntax on the Python side (instant, no UE5 round-trip) ──
        # UE5's ExecPythonCommandEx can hang for 30+ s even when a SyntaxError
        # is caught by our try/except wrapper, because the GIL flush after
        # execution is slow on log-heavy projects.
        # Catching SyntaxErrors here returns an error instantly without touching UE5.
        try:
            compile(code, "<mcp_exec>", "exec")
        except SyntaxError as syn_e:
            return {
                "success": False,
                "error": f"SyntaxError: {syn_e}",
                "output": f"SyntaxError: {syn_e}\n{_tb.format_exc()}",
            }

        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected to Unreal Engine"}
            response = unreal.send_command("exec_python", {"code": code}) or {}
            # Normalize response fields — the C++ bridge may use 'output' or 'result'
            if "output" not in response and "result" in response:
                response["output"] = response["result"]
            if "success" not in response:
                response["success"] = response.get("status") != "error"
            return response
        except Exception as e:
            logger.error(f"exec_python error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def save_blueprint(
        ctx: Context,
        blueprint_name: str,
        only_if_dirty: bool = False,
    ) -> Dict[str, Any]:
        """
        Persist a Blueprint package to disk using the UnrealMCP C++ bridge.

        This invokes the native `save_blueprint` MCP command, which writes the
        package via `UEditorLoadingAndSavingUtils::SavePackages` (UnrealEd). It
        does **not** call Python `unreal.EditorAssetLibrary.save_asset` /
        `save_loaded_asset`, which has crashed with EXCEPTION_ACCESS_VIOLATION in
        EditorScriptingUtilities on some UE 5.6 sessions.

        Typical flow after editing a BP via MCP:
          1. `compile_blueprint(blueprint_name=...)` — marks modified (plugin safe path)
          2. `save_blueprint(blueprint_name=...)` — writes `.uasset`

        Optional: `only_if_dirty=True` maps to the engine's "only save dirty
        packages" behavior; default False saves the listed package regardless.

        Args:
            blueprint_name: Blueprint asset name (e.g. "BP_Cabal")
            only_if_dirty: If True, only persist if the package is dirty
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected to Unreal Engine"}
            raw = unreal.send_command(
                "save_blueprint",
                {"blueprint_name": blueprint_name, "only_if_dirty": only_if_dirty},
            ) or {}
            saved = bool(raw.get("saved", raw.get("success")))
            return {
                "success": saved,
                "saved": saved,
                "blueprint": raw.get("blueprint", blueprint_name),
                "package": raw.get("package"),
                "raw": raw,
            }
        except Exception as e:
            logger.error(f"save_blueprint error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def focus_viewport(
        ctx: Context,
        location: List[float] = [0.0, 0.0, 0.0],
        distance: float = 1000.0
    ) -> Dict[str, Any]:
        """
        Move the Unreal Editor viewport camera to focus on a world location.

        Args:
            location: [X, Y, Z] world-space position to look at
            distance: How far back from the location to place the camera (cm)
        """
        from unreal_mcp_server import get_unreal_connection
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected"}
            return unreal.send_command("focus_viewport", {
                "location": [float(v) for v in location],
                "distance": float(distance)
            }) or {}
        except Exception as e:
            return {"success": False, "message": str(e)}

    logger.info("Editor tools registered")
