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
import time
from typing import Any, Dict, List, Optional

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


def _make_result(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
    t0: float,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": stage, "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def _bridge_result(
    *,
    stage: str,
    raw: Dict[str, Any],
    inputs: Dict[str, Any],
    message: str,
    t0: float,
    warnings: Optional[List[str]] = None,
) -> str:
    raw = raw or {}
    failed = raw.get("success") is False or raw.get("status") == "error" or bool(raw.get("error"))
    if failed:
        msg = raw.get("error") or raw.get("message") or f"{stage} failed"
        return json.dumps(_make_result(
            success=False,
            stage="error",
            message=msg,
            inputs=inputs,
            errors=[msg],
            t0=t0,
        ))

    outputs = {
        key: value for key, value in raw.items()
        if key not in {"success", "status", "message", "error"}
    }
    return json.dumps(_make_result(
        success=True,
        stage=stage,
        message=message,
        inputs=inputs,
        outputs=outputs,
        warnings=warnings,
        t0=t0,
    ))


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

        KB: see knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md#overview
        Example:
            import_sound_asset(file_path="/Game/MCP_Test/Example")"""
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

        # Optionally create a companion SoundCue. UE 5.6 can expose
        # SoundCueFactoryNew.initial_sound_wave as a protected property; keep
        # the SoundWave import successful if cue prewiring is unavailable.
        if auto_create_cue and asset_obj and isinstance(asset_obj, unreal.SoundWave):
            cue_name    = asset_name + "_Cue"
            cue_factory = unreal.SoundCueFactoryNew()
            try:
                cue_factory.set_editor_property("initial_sound_wave", asset_obj)
                cue_asset = asset_tools.create_asset(cue_name, dest, unreal.SoundCue, cue_factory)
            except Exception as cue_exc:
                cue_asset = None
                result["cue_warning"] = (
                    "SoundCue prewire unavailable; SoundWave imported successfully. "
                    + str(cue_exc)
                )
            if cue_asset:
                cue_path = f"{{dest}}/{{cue_name}}"
                unreal.EditorAssetLibrary.save_asset(f"{{dest}}/{{cue_name}}.{{cue_name}}")
                result["cue_path"] = cue_path
                sys.stdout.write(f"[MCP] Created SoundCue: {{cue_path}}\\n")
            elif "cue_warning" not in result:
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

    @mcp.tool()
    async def metasound_create_source(
        ctx: Context,
        name: str,
        path: str = "/Game/Audio/MetaSounds",
        one_shot: bool = True,
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a MetaSound Source asset for playable procedural audio.

        Args:
            name: Asset name such as MS_GeneratorHum.
            path: Content Browser folder under /Game.
            one_shot: Metadata hint for source intent; true for one-shot sources.
            overwrite: Delete an existing asset with the same name first.
            save: Save the package after creation.

        KB: see knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md#mcp-audio-tools
        Example:
            metasound_create_source(name="MS_GeneratorHum", path="/Game/Audio/MetaSounds")
        """
        t0 = time.monotonic()
        params = {
            "name": name,
            "path": path,
            "one_shot": bool(one_shot),
            "overwrite": bool(overwrite),
            "save": bool(save),
        }
        raw = _send("metasound_create_source", params)
        return _bridge_result(
            stage="metasound_create_source",
            raw=raw,
            inputs=params,
            message=f"Created MetaSound Source '{name}'",
            t0=t0,
        )

    @mcp.tool()
    async def metasound_create_patch(
        ctx: Context,
        name: str,
        path: str = "/Game/Audio/MetaSounds/Patches",
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a reusable MetaSound Patch asset for shared DSP logic.

        Args:
            name: Asset name such as MSP_DamageCrackle.
            path: Content Browser folder under /Game.
            overwrite: Delete an existing asset with the same name first.
            save: Save the package after creation.

        KB: see knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md#mcp-audio-tools
        Example:
            metasound_create_patch(name="MSP_DamageCrackle", path="/Game/Audio/MetaSounds/Patches")
        """
        t0 = time.monotonic()
        params = {"name": name, "path": path, "overwrite": bool(overwrite), "save": bool(save)}
        raw = _send("metasound_create_patch", params)
        return _bridge_result(
            stage="metasound_create_patch",
            raw=raw,
            inputs=params,
            message=f"Created MetaSound Patch '{name}'",
            t0=t0,
        )

    @mcp.tool()
    async def metasound_add_node(
        ctx: Context,
        metasound: str,
        class_name: str,
        class_namespace: str = "",
        class_variant: str = "",
        major_version: int = 1,
        node_position: Optional[List[float]] = None,
    ) -> str:
        """Add a native MetaSound node by registered class name.

        Args:
            metasound: MetaSound Source/Patch asset path.
            class_name: Registered MetaSound node class name.
            class_namespace: Optional registered class namespace.
            class_variant: Optional registered class variant.
            major_version: Native class major version.
            node_position: Optional [X, Y] editor graph location.

        KB: see knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md#mcp-audio-tools
        Example:
            metasound_add_node(metasound="/Game/Audio/MetaSounds/MS_GeneratorHum", class_name="Sine", class_namespace="UE")
        """
        t0 = time.monotonic()
        params: Dict[str, Any] = {
            "metasound": metasound,
            "class_name": class_name,
            "class_namespace": class_namespace,
            "class_variant": class_variant,
            "major_version": int(major_version),
        }
        if node_position:
            params["node_position"] = node_position
        raw = _send("metasound_add_node", params)
        return _bridge_result(
            stage="metasound_add_node",
            raw=raw,
            inputs=params,
            message=f"Added MetaSound node '{class_name}'",
            t0=t0,
        )

    @mcp.tool()
    async def metasound_connect_pins(
        ctx: Context,
        metasound: str,
        from_node_id: str,
        from_output_id: str,
        to_node_id: str,
        to_input_id: str,
    ) -> str:
        """Connect a MetaSound node output vertex to a node input vertex.

        Args:
            metasound: MetaSound Source/Patch asset path.
            from_node_id: Source node GUID returned by metasound_add_node or inspection.
            from_output_id: Source output vertex GUID.
            to_node_id: Destination node GUID.
            to_input_id: Destination input vertex GUID.

        KB: see knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md#mcp-audio-tools
        Example:
            metasound_connect_pins(metasound="/Game/Audio/MetaSounds/MS_GeneratorHum", from_node_id="...", from_output_id="...", to_node_id="...", to_input_id="...")
        """
        t0 = time.monotonic()
        params = {
            "metasound": metasound,
            "from_node_id": from_node_id,
            "from_output_id": from_output_id,
            "to_node_id": to_node_id,
            "to_input_id": to_input_id,
        }
        raw = _send("metasound_connect_pins", params)
        return _bridge_result(
            stage="metasound_connect_pins",
            raw=raw,
            inputs=params,
            message="Connected MetaSound pins",
            t0=t0,
        )

    @mcp.tool()
    async def metasound_compile(
        ctx: Context,
        metasound: str,
        save: bool = True,
    ) -> str:
        """Build, conform, and optionally save a MetaSound Source/Patch asset.

        Args:
            metasound: MetaSound Source/Patch asset path.
            save: Save the package after compile/build.

        KB: see knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md#mcp-audio-tools
        Example:
            metasound_compile(metasound="/Game/Audio/MetaSounds/MS_GeneratorHum")
        """
        t0 = time.monotonic()
        params = {"metasound": metasound, "save": bool(save)}
        raw = _send("metasound_compile", params)
        return _bridge_result(
            stage="metasound_compile",
            raw=raw,
            inputs=params,
            message=f"Compiled MetaSound '{metasound}'",
            t0=t0,
        )

    @mcp.tool()
    async def audio_create_soundcue(
        ctx: Context,
        name: str,
        path: str = "/Game/Audio/Cues",
        sound_wave: str = "",
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a SoundCue asset, optionally prewired to a SoundWave.

        Args:
            name: Asset name such as SC_Footstep_Dirt.
            path: Content Browser folder under /Game.
            sound_wave: Optional SoundWave asset path to seed the cue.
            overwrite: Delete an existing asset with the same name first.
            save: Save the package after creation.

        KB: see knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md#mcp-audio-tools
        Example:
            audio_create_soundcue(name="SC_Footstep_Dirt", sound_wave="/Game/Audio/SFX/SW_Footstep_Dirt")
        """
        t0 = time.monotonic()
        params = {
            "name": name,
            "path": path,
            "sound_wave": sound_wave,
            "overwrite": bool(overwrite),
            "save": bool(save),
        }
        raw = _send("audio_create_soundcue", params)
        return _bridge_result(
            stage="audio_create_soundcue",
            raw=raw,
            inputs=params,
            message=f"Created SoundCue '{name}'",
            t0=t0,
        )

    @mcp.tool()
    async def audio_create_attenuation(
        ctx: Context,
        name: str,
        path: str = "/Game/Audio/Attenuation",
        radius: float = 400.0,
        falloff_distance: float = 3600.0,
        spatialize: bool = True,
        attenuate: bool = True,
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a Sound Attenuation asset with common 3D falloff defaults.

        Args:
            name: Asset name such as SA_RoomTone.
            path: Content Browser folder under /Game.
            radius: Inner sphere radius.
            falloff_distance: Distance after radius over which volume falls off.
            spatialize: Enable 3D spatialization.
            attenuate: Enable distance attenuation.
            overwrite: Delete an existing asset with the same name first.
            save: Save the package after creation.

        KB: see knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md#mcp-audio-tools
        Example:
            audio_create_attenuation(name="SA_RoomTone", radius=500.0, falloff_distance=3000.0)
        """
        t0 = time.monotonic()
        params = {
            "name": name,
            "path": path,
            "radius": float(radius),
            "falloff_distance": float(falloff_distance),
            "spatialize": bool(spatialize),
            "attenuate": bool(attenuate),
            "overwrite": bool(overwrite),
            "save": bool(save),
        }
        raw = _send("audio_create_attenuation", params)
        return _bridge_result(
            stage="audio_create_attenuation",
            raw=raw,
            inputs=params,
            message=f"Created Sound Attenuation '{name}'",
            t0=t0,
        )

    @mcp.tool()
    async def audio_create_concurrency(
        ctx: Context,
        name: str,
        path: str = "/Game/Audio/Concurrency",
        max_count: int = 8,
        resolution_rule: str = "stop_farthest_then_oldest",
        limit_to_owner: bool = False,
        retrigger_time: float = 0.0,
        overwrite: bool = False,
        save: bool = True,
    ) -> str:
        """Create a Sound Concurrency asset for voice limiting.

        Args:
            name: Asset name such as SCN_Impacts.
            path: Content Browser folder under /Game.
            max_count: Maximum active voices in the group.
            resolution_rule: prevent_new, stop_oldest, stop_quietest, stop_lowest_priority, or stop_farthest_then_oldest.
            limit_to_owner: Limit concurrency per owning actor.
            retrigger_time: Minimum seconds between accepted plays.
            overwrite: Delete an existing asset with the same name first.
            save: Save the package after creation.

        KB: see knowledge_base/21_METASOUNDS_AND_AUDIO_DSP.md#mcp-audio-tools
        Example:
            audio_create_concurrency(name="SCN_Impacts", max_count=6, resolution_rule="stop_quietest")
        """
        t0 = time.monotonic()
        params = {
            "name": name,
            "path": path,
            "max_count": int(max_count),
            "resolution_rule": resolution_rule,
            "limit_to_owner": bool(limit_to_owner),
            "retrigger_time": float(retrigger_time),
            "overwrite": bool(overwrite),
            "save": bool(save),
        }
        raw = _send("audio_create_concurrency", params)
        return _bridge_result(
            stage="audio_create_concurrency",
            raw=raw,
            inputs=params,
            message=f"Created Sound Concurrency '{name}'",
            t0=t0,
        )
