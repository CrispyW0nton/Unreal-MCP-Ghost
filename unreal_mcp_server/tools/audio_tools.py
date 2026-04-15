"""
Audio Tools - Import sound assets into UE5 Content Browser.

Provides import_sound_asset: imports a WAV/OGG/MP3 file that already lives on
the UE5 host machine (e.g. C:/Sounds/jump.wav) into the Content Browser as a
SoundWave asset, optionally auto-creating a companion SoundCue.

For files that exist on the sandbox (Linux side) rather than the UE5 Windows
machine, use import_sound_asset_from_sandbox in data_tools.py instead.
"""
import json
import logging
import os
from typing import Any, Dict

from mcp.server.fastmcp import Context, FastMCP

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


def register_audio_tools(mcp: FastMCP):

    @mcp.tool()
    async def import_sound_asset(
        ctx: Context,
        file_path: str,
        destination_path: str = "/Game/Audio/",
        auto_create_cue: bool = False,
    ) -> str:
        """Import a WAV, OGG, or MP3 file from the UE5 host machine into the
        Content Browser as a SoundWave asset.

        The file must already be present on the Windows machine running UE5
        (e.g. "C:/Sounds/jump.wav" or "D:/Project/Audio/SFX_Shoot.wav").
        For files that exist on the sandbox, use import_sound_asset_from_sandbox
        instead.

        Args:
            file_path:        Absolute OS path to the audio file on the UE5
                              Windows machine (e.g. "C:/Sounds/jump.wav").
                              Supports WAV, OGG, and MP3 formats.
            destination_path: Content Browser folder for the imported asset.
                              Default: "/Game/Audio/"
            auto_create_cue:  If True, also creates a SoundCue asset wired to
                              the imported SoundWave in the same folder.
                              The cue is named <asset_name>_Cue.

        Returns:
            JSON string with the result:
              Success: {"success": true, "asset_path": "/Game/Audio/jump",
                        "asset_type": "SoundWave",
                        "cue_path": "/Game/Audio/jump_Cue"}  (cue_path only if auto_create_cue=True)
              Failure: {"success": false, "error": "<reason>"}

        Example usage:
            import_sound_asset(
                file_path="C:/Sounds/SFX_TurretFire.wav",
                destination_path="/Game/Audio/SFX/",
                auto_create_cue=True
            )
        """
        # Build the Unreal Python code to run inside UE5 via exec_python
        code = f"""
import unreal
import sys
import os
import json

file_path        = {file_path!r}
destination_path = {destination_path!r}
auto_create_cue  = {auto_create_cue!r}

result = {{"success": False, "error": ""}}

try:
    # Derive asset name from file basename (no extension)
    asset_name = os.path.splitext(os.path.basename(file_path))[0]
    # Normalise destination: strip trailing slash so UE5 doesn't double-slash
    dest = destination_path.rstrip("/") or "/Game/Audio"

    # Ensure destination folder exists in the Content Browser
    unreal.EditorAssetLibrary.make_directory(dest)

    # Build and run the import task
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    task = unreal.AssetImportTask()
    task.filename         = file_path
    task.destination_path = dest
    task.destination_name = asset_name
    task.automated        = True
    task.save             = True
    task.replace_existing = True

    asset_tools.import_asset_tasks([task])

    imported = task.get_editor_property("imported_object_paths")
    sys.stdout.write(f"[MCP] imported_object_paths: {{list(imported)}}\\n")
    sys.stdout.flush()

    if not imported:
        result = {{
            "success": False,
            "error": (
                "Import returned no paths. Check that the file exists on the "
                "UE5 host machine at: " + file_path
            )
        }}
    else:
        # UE4/5 asset paths look like "/Game/Audio/jump.jump" — keep only the
        # part before the dot for a clean Content Browser reference.
        asset_path_full  = imported[0]
        asset_path_clean = asset_path_full.split(".")[0] if "." in asset_path_full else asset_path_full

        # Detect the asset type (SoundWave, SoundBase, …)
        asset_obj  = unreal.load_asset(asset_path_full)
        asset_type = type(asset_obj).__name__ if asset_obj else "SoundWave"

        result = {{
            "success": True,
            "asset_path": asset_path_clean,
            "asset_type": asset_type,
        }}

        # Optionally create a companion SoundCue
        if auto_create_cue and asset_obj and isinstance(asset_obj, unreal.SoundWave):
            cue_name    = asset_name + "_Cue"
            cue_factory = unreal.SoundCueFactoryNew()
            cue_factory.set_editor_property("initial_sound_wave", asset_obj)
            cue_asset   = asset_tools.create_asset(cue_name, dest, unreal.SoundCue, cue_factory)
            if cue_asset:
                cue_path = f"{{dest}}/{{cue_name}}"
                unreal.EditorAssetLibrary.save_asset(f"{{dest}}/{{cue_name}}.{{cue_name}}")
                result["cue_path"] = cue_path
                sys.stdout.write(f"[MCP] Created SoundCue: {{cue_path}}\\n")
            else:
                result["cue_warning"] = "SoundCue creation failed (SoundWave imported successfully)"
            sys.stdout.flush()

except Exception as exc:
    result = {{"success": False, "error": str(exc)}}

print(json.dumps(result))
sys.stdout.flush()
"""

        resp = _send("exec_python", {"code": code})

        # The inner result dict lives under resp["result"] or resp directly
        inner = resp.get("result", resp)
        output = inner.get("output", resp.get("output", ""))

        # Find the JSON line printed by the Python snippet
        parsed = None
        for line in (output or "").splitlines():
            line = line.strip()
            # Strip the UE "[Info] " prefix that the plugin prepends
            if line.startswith("[Info] "):
                line = line[len("[Info] "):]
            if line.startswith("{") and line.endswith("}"):
                try:
                    parsed = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

        if parsed is None:
            # Fallback: exec_python itself reported an error
            if not inner.get("success", True):
                parsed = {"success": False, "error": inner.get("message", output or "exec_python failed")}
            else:
                parsed = {"success": False, "error": f"Could not parse UE output: {output!r}"}

        return json.dumps(parsed)
