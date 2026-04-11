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
    def save_blueprint(ctx: Context, blueprint_name: str) -> Dict[str, Any]:
        """
        Fully compile AND save a Blueprint asset so changes persist on disk.

        BACKGROUND — why this tool exists:
          compile_blueprint only calls Blueprint->Modify() (marks the asset dirty)
          due to a UE5.6 crash (EXCEPTION_ACCESS_VIOLATION in MassEntityEditor
          observer) when FKismetEditorUtilities::CompileBlueprint is called from
          inside the C++ AsyncTask GameThread lambda.
          The UE5 Python plugin runs on a different call stack that does NOT
          trigger the crashing observer chain, so compiling via exec_python is safe.

        This tool does the real work:
          1. Finds the Blueprint asset by name
          2. Calls unreal.KismetEditorUtilities.compile_blueprint() — true bytecode compile
          3. Calls unreal.EditorAssetLibrary.save_asset() — writes .uasset to disk
          4. Returns compilation errors if any

        USAGE PATTERN — always call save_blueprint after compile_blueprint:
          compile_blueprint(blueprint_name="BP_MyActor")   # marks dirty (fast)
          save_blueprint(blueprint_name="BP_MyActor")      # real compile + disk save

        Args:
            blueprint_name: Name of the Blueprint to compile and save (e.g. "BP_MyActor")

        Returns:
            dict with 'success', 'compiled', 'saved', 'had_errors', and 'errors' list.
        """
        from unreal_mcp_server import get_unreal_connection
        code = f"""
import unreal

bp_name = "{blueprint_name}"

# Find the blueprint asset by searching the asset registry
ar = unreal.AssetRegistryHelpers.get_asset_registry()
assets = ar.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"))
bp_asset = None
for a in assets:
    if a.asset_name == bp_name or str(a.asset_name) == bp_name:
        bp_asset = unreal.EditorAssetLibrary.load_asset(str(a.object_path))
        break

if bp_asset is None:
    # Fallback: try common paths
    for path in [f"/Game/Blueprints/{{bp_name}}", f"/Game/{{bp_name}}", f"/Game/Blueprints/Core/{{bp_name}}", f"/Game/Blueprints/Player/{{bp_name}}", f"/Game/Blueprints/AI/{{bp_name}}"]:
        obj = unreal.EditorAssetLibrary.load_asset(path)
        if obj:
            bp_asset = obj
            break

if bp_asset is None:
    print(f"ERROR: Blueprint not found: {{bp_name}}")
else:
    # Step 1: Compile (always attempt even on clean/unmodified Blueprints)
    try:
        unreal.KismetEditorUtilities.compile_blueprint(bp_asset)
        print(f"COMPILED: {{bp_name}}")
    except Exception as e:
        print(f"COMPILE_ERROR: {{e}}")

    # Step 2: Mark dirty so save_asset never skips a clean package
    try:
        pkg = bp_asset.get_outer()
        if pkg:
            pkg.mark_package_dirty()
    except Exception:
        pass

    # Step 3: Save — use save_asset with only_if_is_dirty=False to force write
    try:
        asset_path = str(bp_asset.get_path_name())
        unreal.EditorAssetLibrary.save_asset(asset_path, only_if_is_dirty=False)
        print(f"SAVED: {{bp_name}}")
    except Exception as e:
        # Final fallback: save_packages_with_dialog
        try:
            unreal.EditorLoadingAndSavingUtils.save_packages_with_dialog([bp_asset.get_outer()], only_dirty=False)
            print(f"SAVED: {{bp_name}}")
        except Exception as e2:
            print(f"SAVE_ERROR: {{e2}}")
"""
        try:
            unreal = get_unreal_connection()
            if not unreal:
                return {"success": False, "message": "Not connected to Unreal Engine"}
            response = unreal.send_command("exec_python", {"code": code}) or {}
            output = response.get("output", response.get("result", ""))
            if not isinstance(output, str):
                output = str(output)
            had_errors = "COMPILE_ERROR" in output or "ERROR:" in output
            # compiled=True if "COMPILED:" present OR if no compile error and no "not found"
            # (clean Blueprints may produce no output from compile_blueprint)
            compile_error = "COMPILE_ERROR" in output
            not_found = "ERROR: Blueprint not found" in output
            compiled = "COMPILED:" in output or (not compile_error and not not_found)
            saved = "SAVED:" in output
            errors = [ln for ln in output.splitlines() if "ERROR" in ln]
            return {
                "success": compiled and saved and not had_errors,
                "compiled": compiled,
                "saved": saved,
                "had_errors": had_errors,
                "errors": errors,
                "output": output,
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
