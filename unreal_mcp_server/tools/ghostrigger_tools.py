"""
GhostRigger Bridge Tools — Category A (GhostRigger IPC bridge).

These tools communicate with the GhostRigger IPC server running on
http://localhost:7001 (or a configurable host/port).  GhostRigger is the
KotOR 3-D model converter (https://github.com/CrispyW0nton/Kotor-3D-Model-Converter)
and exposes its own MCP-compatible API via the IPC server.

Architecture:
  Unreal-MCP-Ghost (port 55557 TCP → UE5 C++ plugin)
  GhostRigger IPC  (port 7001  HTTP → GhostRigger / KotorMCP)

These tools use plain HTTP (urllib) with no extra dependencies so they work
in any environment where the MCP server runs.

Tool list (10 tools):
  ghostrigger_health           — GET /api/health
  ghostrigger_open_model       — POST /api/open_mdl
  ghostrigger_list_mcp_tools   — GET /mcp/tools/list
  ghostrigger_call_mcp_tool    — POST /mcp/tools/call
  ghostrigger_read_resource    — POST /mcp/resources/read
  ghostrigger_list_resources   — GET /mcp/resources/list
  ghostrigger_export_model     — call ghostrigger_open_model tool to export MDL→FBX
  ghostrigger_import_to_ue5    — export MDL→FBX via GhostRigger then import FBX into UE5
  ghostrigger_open_creature    — POST /api/open_utc
  ghostrigger_ping             — POST /api/ping
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

# ── Default GhostRigger IPC address ──────────────────────────────────────────
# Can be overridden at runtime by setting the GHOSTRIGGER_HOST / GHOSTRIGGER_PORT
# environment variables.
_DEFAULT_HOST = "localhost"
_DEFAULT_PORT = 7001
_TIMEOUT      = 15  # seconds


def _ghostrigger_base() -> str:
    host = os.environ.get("GHOSTRIGGER_HOST", _DEFAULT_HOST)
    port = int(os.environ.get("GHOSTRIGGER_PORT", _DEFAULT_PORT))
    return f"http://{host}:{port}"


def _http_get(path: str, timeout: int = _TIMEOUT) -> Dict[str, Any]:
    """Perform a GET request to the GhostRigger IPC server."""
    url = f"{_ghostrigger_base()}{path}"
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {"error": f"HTTP {exc.code}: {body[:500]}"}
    except urllib.error.URLError as exc:
        return {"error": f"Cannot reach GhostRigger at {_ghostrigger_base()}: {exc.reason}. "
                         "Make sure GhostRigger is running and port 7001 is accessible."}
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON response from GhostRigger: {exc}"}
    except Exception as exc:
        return {"error": str(exc)}


def _http_post(path: str, body: Dict[str, Any], timeout: int = _TIMEOUT) -> Dict[str, Any]:
    """Perform a POST request to the GhostRigger IPC server."""
    url = f"{_ghostrigger_base()}{path}"
    try:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": f"HTTP {exc.code}: {raw[:500]}"}
    except urllib.error.URLError as exc:
        return {"error": f"Cannot reach GhostRigger at {_ghostrigger_base()}: {exc.reason}. "
                         "Make sure GhostRigger is running and port 7001 is accessible."}
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid JSON response from GhostRigger: {exc}"}
    except Exception as exc:
        return {"error": str(exc)}


def _send_to_ue5(command: str, params: dict) -> Dict[str, Any]:
    """Forward a command to UE5 via the TCP connection."""
    from unreal_mcp_server import get_unreal_connection

    try:
        unreal = get_unreal_connection()
        if not unreal:
            return {"success": False, "message": "Not connected to Unreal Engine"}
        result = unreal.send_command(command, params)
        return result or {"success": False, "message": "No response from Unreal Engine"}
    except Exception as exc:
        logger.error(f"UE5 command error ({command}): {exc}")
        return {"success": False, "message": str(exc)}


def _parse_ue_json(resp: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the JSON payload from a UE5 exec_python response."""
    inner = resp.get("result", resp)
    output = inner.get("output", resp.get("output", "")) or ""
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[Info] "):
            line = line[7:]
        if line.startswith("{") and line.endswith("}"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    if not inner.get("success", True):
        return {"success": False, "error": inner.get("message", output or "exec_python failed")}
    return {"success": False, "error": f"Could not parse UE output: {output!r}"}


# ─────────────────────────────────────────────────────────────────────────────

def register_ghostrigger_tools(mcp: FastMCP):

    # ── Tool 1: ghostrigger_health ────────────────────────────────────────────

    @mcp.tool()
    async def ghostrigger_health(ctx: Context) -> str:
        """Check whether the GhostRigger IPC server is running and healthy.

        Returns:
            JSON string:
            {
              "status": "ok",
              "program": "GhostRigger",
              "port": 7001,
              "version": "2.8",
              "mcp": true
            }
            or {"error": "Cannot reach GhostRigger at http://localhost:7001: ..."}
        """
        result = _http_get("/api/health")
        return json.dumps(result)

    # ── Tool 2: ghostrigger_ping ──────────────────────────────────────────────

    @mcp.tool()
    async def ghostrigger_ping(ctx: Context) -> str:
        """Ping the GhostRigger IPC server (POST /api/ping).

        Returns:
            JSON string: {"status": "ok", "action": "ping", "program": "GhostRigger"}
        """
        result = _http_post("/api/ping", {})
        return json.dumps(result)

    # ── Tool 3: ghostrigger_open_model ───────────────────────────────────────

    @mcp.tool()
    async def ghostrigger_open_model(
        ctx: Context,
        resref: str,
        module_dir: str = "",
    ) -> str:
        """Tell GhostRigger to open a KotOR MDL model for viewing/editing.

        Sends POST /api/open_mdl with the given resref.  GhostRigger will
        locate the model in the game library and display it in the 3-D viewport.

        Args:
            resref:     Model resource reference (e.g. "n_bastila", "plc_bench")
            module_dir: Optional path to the module directory if the model is
                        inside a specific module (leave empty to use the game
                        installation library)

        Returns:
            JSON string: {"status": "ok", "action": "open_mdl"}
            or {"error": "..."}
        """
        payload: Dict[str, Any] = {"resref": resref}
        if module_dir:
            payload["module_dir"] = module_dir
        result = _http_post("/api/open_mdl", payload)
        return json.dumps(result)

    # ── Tool 4: ghostrigger_open_creature ────────────────────────────────────

    @mcp.tool()
    async def ghostrigger_open_creature(
        ctx: Context,
        resref: str,
        module_dir: str = "",
    ) -> str:
        """Tell GhostRigger to open a KotOR UTC creature blueprint.

        Sends POST /api/open_utc.  GhostRigger will locate the creature
        blueprint and display it for editing.

        Args:
            resref:     Creature resource reference (e.g. "n_bastila001")
            module_dir: Optional module directory path

        Returns:
            JSON string: {"status": "ok", "action": "open_utc"}
        """
        payload: Dict[str, Any] = {"resref": resref}
        if module_dir:
            payload["module_dir"] = module_dir
        result = _http_post("/api/open_utc", payload)
        return json.dumps(result)

    # ── Tool 5: ghostrigger_list_mcp_tools ───────────────────────────────────

    @mcp.tool()
    async def ghostrigger_list_mcp_tools(ctx: Context) -> str:
        """List all KotorMCP tools available through GhostRigger's /mcp/tools/list endpoint.

        GhostRigger exposes ~68 KotOR resource tools (installation management,
        discovery, game data lookups, 3-D model pipeline, module exploration,
        GFF/2da/TLK reading, animation debug, decompile, and more).

        Returns:
            JSON string: {"tools": [{name, description, inputSchema}, ...]}
        """
        result = _http_get("/mcp/tools/list")
        return json.dumps(result)

    # ── Tool 6: ghostrigger_call_mcp_tool ────────────────────────────────────

    @mcp.tool()
    async def ghostrigger_call_mcp_tool(
        ctx: Context,
        tool_name: str,
        arguments: str = "{}",
    ) -> str:
        """Call a KotorMCP tool through GhostRigger's /mcp/tools/call endpoint.

        Use ghostrigger_list_mcp_tools() first to discover available tool names
        and their argument schemas.

        Key tool names (see ghostrigger_list_mcp_tools for full list):
          ghostrigger_open_model      — open a model by resref
          ghostrigger_render_model    — render a model to PNG
          ghostrigger_model_info      — get geometry/bone/material info
          ghostrigger_list_game_models — list all models in the game
          ghostrigger_audit           — audit model for issues
          kotor_lookup_2da            — look up a 2DA table row
          kotor_lookup_tlk            — look up a TLK dialog string
          kotor_list_modules          — list all game modules
          kotor_describe_module       — describe module contents

        Args:
            tool_name:  Name of the KotorMCP tool to call
            arguments:  JSON string of arguments (e.g. '{"resref": "n_bastila"}')

        Returns:
            JSON string: {"result": {...}} or {"error": "..."}
        """
        try:
            args = json.loads(arguments)
        except json.JSONDecodeError as exc:
            return json.dumps({"error": f"Invalid JSON in arguments: {exc}"})

        result = _http_post("/mcp/tools/call", {"name": tool_name, "arguments": args})
        return json.dumps(result)

    # ── Tool 7: ghostrigger_list_resources ───────────────────────────────────

    @mcp.tool()
    async def ghostrigger_list_resources(ctx: Context) -> str:
        """List all kotor:// URI resource templates available from GhostRigger.

        Returns the list of resource templates defined by KotorMCP, e.g.:
          kotor://k1/2da/{table}
          kotor://k1/tlk/{strref}
          kotor://k1/module/{module_id}/utc/{resref}

        Returns:
            JSON string: {"resources": [{uri, name, description, mimeType}, ...]}
        """
        result = _http_get("/mcp/resources/list")
        return json.dumps(result)

    # ── Tool 8: ghostrigger_read_resource ────────────────────────────────────

    @mcp.tool()
    async def ghostrigger_read_resource(
        ctx: Context,
        uri: str,
    ) -> str:
        """Read a kotor:// resource URI from GhostRigger.

        Examples:
          "kotor://k1/2da/appearance"       — appearance.2da table
          "kotor://k1/tlk/42"               — TLK string 42
          "kotor://k1/module/danm13/utc/n_bastila001" — Bastila's UTC

        Args:
            uri: A kotor:// URI (use ghostrigger_list_resources to see all templates)

        Returns:
            JSON string: {"content": {...}} or {"error": "..."}
        """
        result = _http_post("/mcp/resources/read", {"uri": uri})
        return json.dumps(result)

    # ── Tool 9: ghostrigger_export_model ────────────────────────────────────

    @mcp.tool()
    async def ghostrigger_export_model(
        ctx: Context,
        resref: str,
        export_path: str,
        module_dir: str = "",
        format: str = "fbx",
    ) -> str:
        """Export a KotOR MDL model to FBX (or another format) via GhostRigger.

        Calls the KotorMCP 'ghostrigger_open_model' tool through GhostRigger
        with export options.  The exported FBX is saved to `export_path` on
        the local filesystem.

        This is the first half of the KotOR→UE5 pipeline:
          1. ghostrigger_export_model  → exports MDL to FBX on disk
          2. import_static_mesh / import_skeletal_mesh → imports FBX into UE5

        Args:
            resref:      Model resource reference (e.g. "n_bastila", "plc_bench")
            export_path: Absolute path on the MCP server machine where the FBX
                         should be saved (e.g. "/home/user/exports/n_bastila.fbx"
                         or "C:/exports/n_bastila.fbx")
            module_dir:  Optional path to the module directory
            format:      Export format: "fbx" (default) — future: "gltf", "obj"

        Returns:
            JSON string:
            {
              "success": true,
              "resref": "n_bastila",
              "export_path": "/home/user/exports/n_bastila.fbx",
              "format": "fbx"
            }
            or {"error": "..."}
        """
        # Use ghostrigger_call_mcp_tool to call ghostrigger_open_model
        # with export_path so GhostRigger writes the FBX to disk
        arguments: Dict[str, Any] = {"resref": resref, "export_path": export_path}
        if module_dir:
            arguments["module_dir"] = module_dir

        result = _http_post("/mcp/tools/call", {
            "name": "ghostrigger_open_model",
            "arguments": arguments,
        })

        # Wrap into a consistent response
        if "error" in result:
            return json.dumps(result)

        response: Dict[str, Any] = {
            "success": True,
            "resref": resref,
            "export_path": export_path,
            "format": format,
            "ghostrigger_response": result,
        }
        return json.dumps(response)

    # ── Tool 10: ghostrigger_import_to_ue5 ───────────────────────────────────

    @mcp.tool()
    async def ghostrigger_import_to_ue5(
        ctx: Context,
        resref: str,
        export_path: str,
        ue5_destination_path: str = "/Game/KotOR/Models/",
        is_skeletal: bool = False,
        skeleton: str = "",
        module_dir: str = "",
    ) -> str:
        """Full KotOR→UE5 pipeline: export MDL via GhostRigger then import FBX into UE5.

        Step 1: Calls GhostRigger to export the KotOR model to FBX at `export_path`.
        Step 2: Calls UE5 via exec_python to import the FBX as a StaticMesh or
                SkeletalMesh at `ue5_destination_path`.

        Args:
            resref:               KotOR model resource reference (e.g. "n_bastila")
            export_path:          Absolute path where the FBX should be written
                                  (must be accessible to both GhostRigger and the
                                  UE5 machine — use a shared/mounted folder)
            ue5_destination_path: Content Browser destination (default "/Game/KotOR/Models/")
            is_skeletal:          If True, import as SkeletalMesh (default False)
            skeleton:             Existing skeleton asset path to reuse (SkeletalMesh only)
            module_dir:           Optional module directory for GhostRigger

        Returns:
            JSON string:
            {
              "success": true,
              "resref": "n_bastila",
              "export_path": "/shared/n_bastila.fbx",
              "asset_path": "/Game/KotOR/Models/n_bastila",
              "asset_type": "StaticMesh",
              "ghostrigger_export": {...},
              "ue5_import": {...}
            }
        """
        # ── Step 1: Export via GhostRigger ───────────────────────────────────
        export_arguments: Dict[str, Any] = {
            "resref": resref,
            "export_path": export_path,
        }
        if module_dir:
            export_arguments["module_dir"] = module_dir

        gr_result = _http_post("/mcp/tools/call", {
            "name": "ghostrigger_open_model",
            "arguments": export_arguments,
        })

        if "error" in gr_result:
            return json.dumps({
                "success": False,
                "step": "ghostrigger_export",
                "error": gr_result["error"],
                "resref": resref,
            })

        # ── Step 2: Import FBX into UE5 ─────────────────────────────────────
        asset_name = os.path.splitext(os.path.basename(export_path))[0]

        if is_skeletal:
            skel_path = skeleton or ""
            code = f"""
import unreal
import sys
import os
import json

file_path        = {export_path!r}
destination_path = {ue5_destination_path!r}
asset_name       = {asset_name!r}
skeleton_path    = {skel_path!r}

unreal.EditorAssetLibrary.make_directory(destination_path)

options = unreal.FbxImportUI()
options.set_editor_property("import_mesh",        True)
options.set_editor_property("import_as_skeletal",  True)
options.set_editor_property("import_animations",   True)
options.set_editor_property("import_materials",    True)
if skeleton_path:
    skel = unreal.EditorAssetLibrary.load_asset(skeleton_path)
    if skel and isinstance(skel, unreal.Skeleton):
        options.set_editor_property("skeleton", skel)

task = unreal.AssetImportTask()
task.filename         = file_path
task.destination_path = destination_path
task.destination_name = asset_name
task.automated        = True
task.save             = True
task.replace_existing = True
task.set_editor_property("options", options)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
imported = task.get_editor_property("imported_object_paths")

if imported:
    raw   = imported[0]
    clean = raw.split(".")[0] if "." in raw else raw
    print(json.dumps({{"success": True, "asset_path": clean, "asset_type": "SkeletalMesh"}}))
else:
    print(json.dumps({{"success": False, "error": f"Import returned no paths. Check that {{file_path}} exists on UE5 host."}}))
sys.stdout.flush()
"""
        else:
            code = f"""
import unreal
import sys
import os
import json

file_path        = {export_path!r}
destination_path = {ue5_destination_path!r}
asset_name       = {asset_name!r}

unreal.EditorAssetLibrary.make_directory(destination_path)

options = unreal.FbxImportUI()
options.set_editor_property("import_mesh",        True)
options.set_editor_property("import_as_skeletal",  False)
options.set_editor_property("import_materials",    True)
options.set_editor_property("import_textures",     True)
options.static_mesh_import_data.set_editor_property("combine_meshes",          True)
options.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs",  True)
options.static_mesh_import_data.set_editor_property("auto_generate_collision",  True)

task = unreal.AssetImportTask()
task.filename         = file_path
task.destination_path = destination_path
task.destination_name = asset_name
task.automated        = True
task.save             = True
task.replace_existing = True
task.set_editor_property("options", options)

unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
imported = task.get_editor_property("imported_object_paths")

if imported:
    raw   = imported[0]
    clean = raw.split(".")[0] if "." in raw else raw
    print(json.dumps({{"success": True, "asset_path": clean, "asset_type": "StaticMesh"}}))
else:
    print(json.dumps({{"success": False, "error": f"Import returned no paths. Check that {{file_path}} exists on UE5 host."}}))
sys.stdout.flush()
"""

        ue5_resp = _send_to_ue5("exec_python", {"code": code})
        ue5_result = _parse_ue_json(ue5_resp)

        return json.dumps({
            "success": ue5_result.get("success", False),
            "resref": resref,
            "export_path": export_path,
            "asset_path": ue5_result.get("asset_path", ""),
            "asset_type": ue5_result.get("asset_type", ""),
            "ghostrigger_export": gr_result,
            "ue5_import": ue5_result,
        })
