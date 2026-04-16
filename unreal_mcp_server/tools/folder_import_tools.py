"""
Folder Import Tools — Category B (folder-based batch imports).

These tools compose the Category C single-asset tools into batch operations.

KEY DESIGN: scan_export_folder runs LOCALLY on the MCP server process — it reads
the filesystem of whichever machine the MCP server is running on (developer's machine
or sandbox). The import tools then forward file paths to UE5 via exec_python.

Tools:
  scan_export_folder         — scan a folder and return a categorised asset manifest
  batch_import_folder        — import all recognised assets from a folder into UE5
  import_folder_as_character — specialised: import a character folder (mesh + textures
                               + animations) as a complete set under one destination
"""
import json
import logging
import os
from typing import Any, Dict

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")


def _get_substrate():
    """Lazy import of exec_substrate helpers to avoid circular imports."""
    from tools.exec_substrate import exec_python_structured
    return exec_python_structured

# Extensions grouped by asset category
_TEXTURE_EXTS    = {".png", ".jpg", ".jpeg", ".tga", ".exr", ".hdr", ".bmp"}
_STATIC_EXTS     = {".fbx", ".obj", ".gltf", ".glb"}
_SKELETAL_EXTS   = {".fbx"}           # FBX can be either — detected by content
_AUDIO_EXTS      = {".wav", ".ogg", ".mp3"}
_ALL_KNOWN_EXTS  = _TEXTURE_EXTS | _STATIC_EXTS | _AUDIO_EXTS





def _categorise_file(path: str) -> str:
    """Return the asset category for a file based on its extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext in _TEXTURE_EXTS:
        return "texture"
    if ext in _STATIC_EXTS:
        return "mesh"          # static vs skeletal resolved by filename heuristic
    if ext in _AUDIO_EXTS:
        return "audio"
    return "unknown"


def _infer_ue_dest(base_ue_path: str, rel_dir: str) -> str:
    """Map a relative subdirectory to a UE5 Content Browser path."""
    if rel_dir and rel_dir != ".":
        # normalise path separators
        subdir = rel_dir.replace("\\", "/").strip("/")
        return f"{base_ue_path.rstrip('/')}/{subdir}"
    return base_ue_path.rstrip("/")


def register_folder_import_tools(mcp: FastMCP):

    # ── Tool 1: scan_export_folder ────────────────────────────────────────────

    @mcp.tool()
    async def scan_export_folder(
        ctx: Context,
        folder_path: str,
        recursive: bool = True,
    ) -> str:
        """Scan a local folder for importable assets and return a categorised manifest.

        This tool runs LOCALLY on the MCP server machine — it does NOT connect to
        UE5. Use it to preview what would be imported before calling batch_import_folder.

        Args:
            folder_path: Absolute path to the folder on the MCP server machine
                         (e.g. "/home/user/exports/Bastila" or "C:/KotOR/exports")
            recursive:   If True, scan all subdirectories (default True)

        Returns:
            JSON string with a categorised manifest:
            {
              "folder": "/home/user/exports/Bastila",
              "total_files": 12,
              "importable": 10,
              "skipped": 2,
              "categories": {
                "texture": [{"path": "...", "name": "...", "ext": ".png"}, ...],
                "mesh":    [...],
                "audio":   [...],
                "unknown": [...]
              },
              "subdirs": ["textures", "meshes"]
            }
        """
        result: Dict[str, Any] = {
            "success": True,
            "folder": folder_path,
            "total_files": 0,
            "importable": 0,
            "skipped": 0,
            "categories": {"texture": [], "mesh": [], "audio": [], "unknown": []},
            "subdirs": [],
        }

        if not os.path.isdir(folder_path):
            result["success"] = False
            result["error"] = f"Folder not found on MCP server machine: {folder_path}"
            return json.dumps(result)

        try:
            walker = os.walk(folder_path) if recursive else [(folder_path, [], os.listdir(folder_path))]
            subdirs_seen: set = set()

            for dirpath, dirnames, filenames in walker:
                # Track unique top-level subdirs
                rel = os.path.relpath(dirpath, folder_path)
                top = rel.split(os.sep)[0]
                if top != ".":
                    subdirs_seen.add(top)

                for fname in sorted(filenames):
                    full = os.path.join(dirpath, fname)
                    rel_file = os.path.relpath(full, folder_path)
                    ext = os.path.splitext(fname)[1].lower()
                    cat = _categorise_file(full)
                    result["total_files"] += 1
                    entry = {
                        "path": full,
                        "relative_path": rel_file,
                        "name": os.path.splitext(fname)[0],
                        "ext": ext,
                    }
                    if cat != "unknown":
                        result["importable"] += 1
                    else:
                        result["skipped"] += 1
                    result["categories"][cat].append(entry)

            result["subdirs"] = sorted(subdirs_seen)

        except Exception as exc:
            result["success"] = False
            result["error"] = str(exc)

        return json.dumps(result)

    # ── Tool 2: batch_import_folder ───────────────────────────────────────────

    @mcp.tool()
    async def batch_import_folder(
        ctx: Context,
        folder_path: str,
        ue5_base_path: str = "/Game/Imported/",
        recursive: bool = True,
        import_textures: bool = True,
        import_meshes: bool = True,
        import_audio: bool = True,
        preserve_folder_structure: bool = True,
        dry_run: bool = False,
    ) -> str:
        """Batch-import all recognised assets from a local folder into UE5.

        Scans the folder locally (no UE5 connection needed for the scan), then
        sends a single exec_python call to UE5 with an AssetImportTask per file.
        Results are reported per-file.

        Args:
            folder_path:              Absolute path on the MCP server machine to scan
            ue5_base_path:            Root Content Browser path for imported assets
                                      (default "/Game/Imported/")
            recursive:                Scan subdirectories (default True)
            import_textures:          Import texture files (default True)
            import_meshes:            Import FBX/OBJ/glTF mesh files (default True)
            import_audio:             Import WAV/OGG/MP3 audio files (default True)
            preserve_folder_structure: Mirror the local subfolder structure in the
                                      Content Browser (default True)
            dry_run:                  If True, return the manifest without importing
                                      (default False)

        Returns:
            JSON string:
            {
              "success": true,
              "dry_run": false,
              "total": 10,
              "imported": 9,
              "failed": 1,
              "results": [
                {"file": "T_Bastila_n.png", "success": true,  "asset_path": "/Game/..."},
                {"file": "SM_Table.fbx",    "success": false, "error": "..."},
                ...
              ]
            }
        """
        # ── 1. Local scan ─────────────────────────────────────────────────────
        if not os.path.isdir(folder_path):
            return json.dumps({
                "success": False,
                "error": f"Folder not found on MCP server machine: {folder_path}",
            })

        files_to_import = []
        walker = os.walk(folder_path) if recursive else [(folder_path, [], os.listdir(folder_path))]

        for dirpath, _, filenames in walker:
            rel_dir = os.path.relpath(dirpath, folder_path)
            ue_dest = (
                _infer_ue_dest(ue5_base_path, rel_dir)
                if preserve_folder_structure
                else ue5_base_path.rstrip("/")
            )
            for fname in sorted(filenames):
                full = os.path.join(dirpath, fname)
                cat = _categorise_file(full)
                if cat == "texture" and not import_textures:
                    continue
                if cat == "mesh" and not import_meshes:
                    continue
                if cat == "audio" and not import_audio:
                    continue
                if cat == "unknown":
                    continue
                files_to_import.append({
                    "path": full,
                    "name": os.path.splitext(fname)[0],
                    "category": cat,
                    "ue_dest": ue_dest,
                })

        if dry_run:
            return json.dumps({
                "success": True,
                "dry_run": True,
                "total": len(files_to_import),
                "files": files_to_import,
            })

        if not files_to_import:
            return json.dumps({
                "success": True,
                "dry_run": False,
                "total": 0,
                "imported": 0,
                "failed": 0,
                "results": [],
                "message": "No importable files found in folder",
            })

        # ── 2. Build exec_python_structured payload ───────────────────────────
        files_json = json.dumps(files_to_import)

        user_code = f"""
import os

files_to_import = json.loads({files_json!r})
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
per_file_results = []

for entry in files_to_import:
    file_path  = entry["path"]
    asset_name = entry["name"]
    ue_dest    = entry["ue_dest"]
    category   = entry["category"]
    item = {{"file": os.path.basename(file_path), "category": category, "success": False}}

    try:
        unreal.EditorAssetLibrary.make_directory(ue_dest)
        task = unreal.AssetImportTask()
        task.filename         = file_path
        task.destination_path = ue_dest
        task.destination_name = asset_name
        task.automated        = True
        task.save             = True
        task.replace_existing = True

        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".fbx", ".obj"):
            opts = unreal.FbxImportUI()
            opts.set_editor_property("import_mesh",        True)
            opts.set_editor_property("import_as_skeletal", False)
            opts.set_editor_property("import_materials",   True)
            opts.set_editor_property("import_textures",    True)
            opts.static_mesh_import_data.set_editor_property("combine_meshes",          True)
            opts.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs",  True)
            opts.static_mesh_import_data.set_editor_property("auto_generate_collision", True)
            task.set_editor_property("options", opts)

        asset_tools.import_asset_tasks([task])
        imported = task.get_editor_property("imported_object_paths")

        if imported:
            raw   = imported[0]
            clean = raw.split(".")[0] if "." in raw else raw
            item["success"]    = True
            item["asset_path"] = clean
            if category == "texture":
                tcs = unreal.TextureCompressionSettings
                tex = unreal.load_asset(raw)
                if tex and isinstance(tex, unreal.Texture2D):
                    n = asset_name.lower() + "_"
                    if any(s in n for s in ("_n_", "_normal_", "_nrm_")):
                        tex.set_editor_property("compression_settings", tcs.TC_NORMALMAP)
                        tex.set_editor_property("srgb", False)
                    elif any(s in n for s in ("_r_", "_rough_", "_m_", "_metal_",
                                               "_ao_", "_occlusion_", "_mask_", "_orm_")):
                        tex.set_editor_property("compression_settings", tcs.TC_MASKS)
                        tex.set_editor_property("srgb", False)
                    elif any(s in n for s in ("_h_", "_height_", "_disp_")):
                        tex.set_editor_property("compression_settings", tcs.TC_MASKS)
                        tex.set_editor_property("srgb", False)
                    else:
                        tex.set_editor_property("compression_settings", tcs.TC_DEFAULT)
                        tex.set_editor_property("srgb", True)
                    unreal.EditorAssetLibrary.save_asset(raw)
        else:
            item["error"] = "Import returned no paths (file may not exist on UE5 machine)"
            _warnings.append(f"{{item['file']}}: no paths returned")

    except Exception as exc:
        item["error"] = str(exc)
        _errors.append(f"{{item['file']}}: {{exc}}")

    per_file_results.append(item)

imported_count = sum(1 for r in per_file_results if r["success"])
failed_count   = len(per_file_results) - imported_count
_result["dry_run"]  = False
_result["total"]    = len(per_file_results)
_result["imported"] = imported_count
_result["failed"]   = failed_count
_result["results"]  = per_file_results
"""
        exec_structured = _get_substrate()
        r = exec_structured(user_code, "batch_import_folder")
        return json.dumps(r)

    # ── Tool 3: import_folder_as_character ────────────────────────────────────

    @mcp.tool()
    async def import_folder_as_character(
        ctx: Context,
        folder_path: str,
        character_name: str,
        ue5_base_path: str = "/Game/Characters/",
        skeleton: str = "",
        import_animations: bool = True,
        import_morph_targets: bool = True,
    ) -> str:
        """Import a character export folder (mesh + textures + animations) as a
        complete set under one UE5 destination.

        Designed for KotOR/GhostRigger export folders that follow the layout:
          <folder>/
            <name>.fbx           ← skeletal mesh (required)
            textures/
              T_<name>_d.tga     ← diffuse
              T_<name>_n.tga     ← normal map
              ...
            animations/          ← optional animation FBXs
              Idle.fbx
              Walk.fbx

        The skeletal mesh FBX is imported first (establishing the skeleton), then
        all texture files, then any animation FBXs reusing the created skeleton.

        Args:
            folder_path:          Absolute path on MCP server machine
            character_name:       Used for the UE5 subfolder, e.g. "Bastila"
            ue5_base_path:        Root Content Browser path (default "/Game/Characters/")
            skeleton:             Existing skeleton path to reuse (leave empty to auto-create)
            import_animations:    Import FBX files in an "animations" subfolder (default True)
            import_morph_targets: Import morph targets from the skeletal mesh (default True)

        Returns:
            JSON string with the full import report and key asset paths:
            {
              "success": true,
              "character_name": "Bastila",
              "ue5_destination": "/Game/Characters/Bastila",
              "skeletal_mesh": "/Game/Characters/Bastila/SK_Bastila",
              "skeleton":      "/Game/Characters/Bastila/SK_Bastila_Skeleton",
              "textures":      ["/Game/Characters/Bastila/Textures/T_Bastila_d", ...],
              "animations":    ["Idle", "Walk"],
              "reused_skeleton": false,
              "errors": []
            }
        """
        if not os.path.isdir(folder_path):
            return json.dumps({
                "success": False,
                "error": f"Folder not found on MCP server machine: {folder_path}",
            })

        ue5_dest = f"{ue5_base_path.rstrip('/')}/{character_name}"
        errors = []

        # ── Discover files locally ─────────────────────────────────────────────
        mesh_fbx    = None   # primary skeletal mesh FBX
        texture_files: list = []
        anim_fbxs: list     = []

        for dirpath, dirnames, filenames in os.walk(folder_path):
            rel = os.path.relpath(dirpath, folder_path).replace("\\", "/")
            is_anim_dir = any(part in ("animations", "anim", "anims")
                              for part in rel.lower().split("/"))

            for fname in sorted(filenames):
                full = os.path.join(dirpath, fname)
                ext = os.path.splitext(fname)[1].lower()
                name_no_ext = os.path.splitext(fname)[0]

                if ext == ".fbx":
                    if is_anim_dir and import_animations:
                        anim_fbxs.append(full)
                    elif mesh_fbx is None and rel == ".":
                        # Top-level FBX → skeletal mesh
                        mesh_fbx = full
                    elif is_anim_dir and not import_animations:
                        pass  # skip
                    elif rel != ".":
                        # Non-root FBX in non-anim folder → treat as anim
                        if import_animations:
                            anim_fbxs.append(full)

                elif ext in _TEXTURE_EXTS:
                    texture_files.append(full)

        if mesh_fbx is None:
            # Fallback: pick the largest FBX in root (likely the character mesh)
            root_fbxs = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith(".fbx")
            ]
            if root_fbxs:
                mesh_fbx = max(root_fbxs, key=os.path.getsize)

        if mesh_fbx is None:
            return json.dumps({
                "success": False,
                "error": "No FBX file found in folder root. Cannot determine skeletal mesh.",
            })

        # ── Build exec_python payload ─────────────────────────────────────────
        mesh_name = os.path.splitext(os.path.basename(mesh_fbx))[0]
        tex_ue_dest = f"{ue5_dest}/Textures"
        anim_ue_dest = f"{ue5_dest}/Animations"

        payload = {
            "mesh_fbx":        mesh_fbx,
            "mesh_name":       mesh_name,
            "ue5_dest":        ue5_dest,
            "tex_ue_dest":     tex_ue_dest,
            "anim_ue_dest":    anim_ue_dest,
            "texture_files":   texture_files,
            "anim_fbxs":       anim_fbxs,
            "skeleton_path":   skeleton,
            "do_import_morphs": import_morph_targets,
            "character_name":  character_name,
        }
        payload_json = json.dumps(payload)

        user_code = f"""
import os

payload = json.loads({payload_json!r})

mesh_fbx         = payload["mesh_fbx"]
mesh_name        = payload["mesh_name"]
ue5_dest         = payload["ue5_dest"]
tex_ue_dest      = payload["tex_ue_dest"]
anim_ue_dest     = payload["anim_ue_dest"]
texture_files    = payload["texture_files"]
anim_fbxs        = payload["anim_fbxs"]
skeleton_path    = payload["skeleton_path"]
do_import_morphs = payload["do_import_morphs"]
character_name   = payload["character_name"]

_result["character_name"]  = character_name
_result["ue5_destination"] = ue5_dest
_result["skeletal_mesh"]   = ""
_result["skeleton"]        = ""
_result["textures"]        = []
_result["animations"]      = []
_result["reused_skeleton"] = False

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

# ── Step 1: Import skeletal mesh ──────────────────────────────────────────────
for d in (ue5_dest, tex_ue_dest, anim_ue_dest):
    unreal.EditorAssetLibrary.make_directory(d)

options = unreal.FbxImportUI()
options.set_editor_property("import_mesh",        True)
options.set_editor_property("import_as_skeletal",  True)
options.set_editor_property("import_animations",   False)
options.set_editor_property("import_materials",    True)
options.skeletal_mesh_import_data.set_editor_property("import_morph_targets", do_import_morphs)

reused = False
if skeleton_path:
    skel = unreal.EditorAssetLibrary.load_asset(skeleton_path)
    if skel and isinstance(skel, unreal.Skeleton):
        options.set_editor_property("skeleton", skel)
        reused = True
    else:
        _warnings.append(f"Skeleton not found at {{skeleton_path}}, creating new")

task = unreal.AssetImportTask()
task.filename         = mesh_fbx
task.destination_path = ue5_dest
task.destination_name = mesh_name
task.automated        = True
task.save             = True
task.replace_existing = True
task.set_editor_property("options", options)
asset_tools.import_asset_tasks([task])

imported = task.get_editor_property("imported_object_paths")
if imported:
    sk_raw   = imported[0]
    sk_clean = sk_raw.split(".")[0] if "." in sk_raw else sk_raw
    _result["skeletal_mesh"]   = sk_clean
    _result["reused_skeleton"] = reused

    sk_asset = unreal.load_asset(sk_raw)
    if sk_asset and isinstance(sk_asset, unreal.SkeletalMesh):
        skel_obj = sk_asset.get_editor_property("skeleton")
        if skel_obj:
            _result["skeleton"] = skel_obj.get_path_name().split(".")[0]
else:
    raise RuntimeError("Skeletal mesh import returned no paths for: " + mesh_fbx)

# ── Step 2: Import textures ───────────────────────────────────────────────────
tcs = unreal.TextureCompressionSettings
for tex_path in texture_files:
    tex_name = os.path.splitext(os.path.basename(tex_path))[0]
    try:
        task = unreal.AssetImportTask()
        task.filename         = tex_path
        task.destination_path = tex_ue_dest
        task.destination_name = tex_name
        task.automated        = True
        task.save             = True
        task.replace_existing = True
        asset_tools.import_asset_tasks([task])
        imp = task.get_editor_property("imported_object_paths")
        if imp:
            raw   = imp[0]
            clean = raw.split(".")[0] if "." in raw else raw
            _result["textures"].append(clean)
            tex_obj = unreal.load_asset(raw)
            if tex_obj and isinstance(tex_obj, unreal.Texture2D):
                n = tex_name.lower() + "_"
                if any(s in n for s in ("_n_", "_normal_", "_nrm_")):
                    tex_obj.set_editor_property("compression_settings", tcs.TC_NORMALMAP)
                    tex_obj.set_editor_property("srgb", False)
                elif any(s in n for s in ("_r_", "_rough_", "_m_", "_metal_",
                                           "_ao_", "_occlusion_", "_mask_", "_orm_")):
                    tex_obj.set_editor_property("compression_settings", tcs.TC_MASKS)
                    tex_obj.set_editor_property("srgb", False)
                elif any(s in n for s in ("_h_", "_height_", "_disp_")):
                    tex_obj.set_editor_property("compression_settings", tcs.TC_MASKS)
                    tex_obj.set_editor_property("srgb", False)
                else:
                    tex_obj.set_editor_property("compression_settings", tcs.TC_DEFAULT)
                    tex_obj.set_editor_property("srgb", True)
                unreal.EditorAssetLibrary.save_asset(raw)
    except Exception as exc:
        _errors.append(f"Texture {{os.path.basename(tex_path)}} failed: {{exc}}")

# ── Step 3: Import animations ─────────────────────────────────────────────────
if _result["skeleton"] and anim_fbxs:
    skel_base = os.path.basename(_result["skeleton"])
    skel_full_path = _result["skeleton"] + "." + skel_base
    skel_for_anims = unreal.EditorAssetLibrary.load_asset(skel_full_path)
    for anim_fbx in anim_fbxs:
        anim_name = os.path.splitext(os.path.basename(anim_fbx))[0]
        try:
            anim_opts = unreal.FbxImportUI()
            anim_opts.set_editor_property("import_mesh",       False)
            anim_opts.set_editor_property("import_animations", True)
            if skel_for_anims and isinstance(skel_for_anims, unreal.Skeleton):
                anim_opts.set_editor_property("skeleton", skel_for_anims)
            task = unreal.AssetImportTask()
            task.filename         = anim_fbx
            task.destination_path = anim_ue_dest
            task.destination_name = anim_name
            task.automated        = True
            task.save             = True
            task.replace_existing = True
            task.set_editor_property("options", anim_opts)
            asset_tools.import_asset_tasks([task])
            imp = task.get_editor_property("imported_object_paths")
            if imp:
                _result["animations"].append(anim_name)
        except Exception as exc:
            _errors.append(f"Animation {{anim_name}} failed: {{exc}}")
"""
        exec_structured = _get_substrate()
        r = exec_structured(user_code, "import_folder_as_character")
        return json.dumps(r)
