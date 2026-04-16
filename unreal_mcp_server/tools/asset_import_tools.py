"""
Asset Import Tools — Category C (single-asset atomic imports).

Tools:
  import_texture        — PNG/JPG/TGA/EXR/HDR/BMP → Texture2D with auto compression settings
  import_static_mesh    — FBX/OBJ/glTF → StaticMesh with configurable import options
  import_skeletal_mesh  — FBX → SkeletalMesh with animation, morph-target, and skeleton options

All tools use exec_python_structured (safe execution substrate) to run inside UE5.
Results follow the StructuredResult schema:
  {success, stage, message, outputs, warnings, errors, log_tail}
For files on the Linux sandbox use import_sound_asset_from_sandbox pattern instead.
"""
import json
import logging
from typing import Any, Dict

from mcp.server.fastmcp import Context, FastMCP

logger = logging.getLogger("UnrealMCP")

SUPPORTED_TEXTURE_EXTS = {".png", ".jpg", ".jpeg", ".tga", ".exr", ".hdr", ".bmp"}
SUPPORTED_STATIC_MESH_EXTS = {".fbx", ".obj", ".gltf", ".glb"}
SUPPORTED_SKELETAL_MESH_EXTS = {".fbx"}


def _get_substrate():
    """Lazy import of exec_substrate helpers to avoid circular imports."""
    from tools.exec_substrate import exec_python_structured
    return exec_python_structured


def register_asset_import_tools(mcp: FastMCP):

    # ── Tool 1: import_texture ────────────────────────────────────────────────

    @mcp.tool()
    async def import_texture(
        ctx: Context,
        file_path: str,
        destination_path: str = "/Game/Textures/",
        texture_type: str = "auto",
    ) -> str:
        """Import a texture file into UE5 Content Browser as a Texture2D asset.

        Supports PNG, JPG/JPEG, TGA, EXR, HDR, and BMP formats.
        The file must already exist on the Windows machine running UE5.

        When texture_type is "auto" (default) the correct compression settings and
        sRGB flag are inferred from the filename suffix:
          *_n / *_normal / *_nrm        → TC_NORMALMAP, sRGB=False
          *_r / *_rough / *_m / *_metal
          *_ao / *_occlusion / *_orm
          *_mask                         → TC_MASKS, sRGB=False
          *_h / *_height / *_disp        → TC_MASKS, sRGB=False
          *_e / *_emissive / *_emit      → TC_DEFAULT, sRGB=True
          everything else (BaseColor…)   → TC_DEFAULT, sRGB=True

        Args:
            file_path:        Absolute OS path on the UE5 Windows machine
                              (e.g. "C:/Textures/T_Wood_BaseColor.png")
            destination_path: Content Browser folder (default "/Game/Textures/")
            texture_type:     "auto" | "diffuse" | "normal" | "roughness" |
                              "metallic" | "ao" | "emissive" | "height" | "default"
                              Overrides filename-based detection when not "auto".

        Returns:
            JSON string with StructuredResult — outputs on success:
              {
                "success": true,
                "stage": "import_texture",
                "outputs": {
                  "asset_path": "/Game/Textures/T_Wood_BaseColor",
                  "asset_type": "Texture2D",
                  "texture_type": "BaseColor",
                  "srgb": true,
                  "compression": "TC_DEFAULT"
                },
                "warnings": [], "errors": [], "log_tail": []
              }
            failure:
              {"success": false, "stage": "import_texture", "errors": ["<reason>"]}
        """
        user_code = f"""
import os

file_path        = {file_path!r}
destination_path = {destination_path!r}
texture_type_arg = {texture_type!r}

asset_name = os.path.splitext(os.path.basename(file_path))[0]
dest = destination_path.rstrip("/") or "/Game/Textures"
unreal.EditorAssetLibrary.make_directory(dest)

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
if not imported:
    raise RuntimeError(
        "Import returned no paths. Verify the file exists on the UE5 "
        "host machine at: " + file_path
    )

asset_path_full  = imported[0]
asset_path_clean = asset_path_full.split(".")[0] if "." in asset_path_full else asset_path_full

tex = unreal.load_asset(asset_path_full)
tcs = unreal.TextureCompressionSettings

# ── Determine compression from texture_type_arg or filename ──────────
name = asset_name.lower()

if texture_type_arg == "normal":
    comp_label = "Normal"
    comp       = tcs.TC_NORMALMAP
    use_srgb   = False
elif texture_type_arg in ("roughness", "metallic", "ao"):
    comp_label = "Mask"
    comp       = tcs.TC_MASKS
    use_srgb   = False
elif texture_type_arg == "height":
    comp_label = "Height"
    comp       = tcs.TC_MASKS
    use_srgb   = False
elif texture_type_arg == "emissive":
    comp_label = "Emissive"
    comp       = tcs.TC_DEFAULT
    use_srgb   = True
elif texture_type_arg in ("diffuse", "default"):
    comp_label = "BaseColor"
    comp       = tcs.TC_DEFAULT
    use_srgb   = True
else:
    # "auto" — infer from filename suffix
    n = name + "_"
    if any(s in n for s in ("_n_", "_normal_", "_nrm_")):
        comp_label = "Normal"
        comp       = tcs.TC_NORMALMAP
        use_srgb   = False
    elif any(s in n for s in ("_r_", "_rough_", "_m_", "_metal_",
                               "_ao_", "_occlusion_", "_mask_", "_orm_")):
        comp_label = "Mask"
        comp       = tcs.TC_MASKS
        use_srgb   = False
    elif any(s in n for s in ("_h_", "_height_", "_disp_")):
        comp_label = "Height"
        comp       = tcs.TC_MASKS
        use_srgb   = False
    elif any(s in n for s in ("_e_", "_emissive_", "_emit_")):
        comp_label = "Emissive"
        comp       = tcs.TC_DEFAULT
        use_srgb   = True
    else:
        comp_label = "BaseColor"
        comp       = tcs.TC_DEFAULT
        use_srgb   = True

# ── Apply compression settings ────────────────────────────────────────
if tex and isinstance(tex, unreal.Texture2D):
    with unreal.ScopedEditorTransaction("MCP import_texture: " + asset_name):
        tex.set_editor_property("compression_settings", comp)
        tex.set_editor_property("srgb", use_srgb)
    unreal.EditorAssetLibrary.save_asset(asset_path_full)
else:
    _warnings.append(f"Asset loaded but is not Texture2D; compression not applied")

_result["asset_path"]    = asset_path_clean
_result["asset_type"]    = "Texture2D"
_result["texture_type"]  = comp_label
_result["srgb"]          = use_srgb
_result["compression"]   = str(comp).split(".")[-1]
"""
        exec_structured = _get_substrate()
        r = exec_structured(user_code, "import_texture")
        return json.dumps(r)

    # ── Tool 2: import_static_mesh ────────────────────────────────────────────

    @mcp.tool()
    async def import_static_mesh(
        ctx: Context,
        file_path: str,
        destination_path: str = "/Game/Meshes/",
        combine_meshes: bool = True,
        generate_lightmap_uvs: bool = True,
        auto_generate_collision: bool = True,
        import_materials: bool = True,
        import_textures: bool = True,
    ) -> str:
        """Import a 3D model as a Static Mesh into UE5 Content Browser.

        Supports FBX, OBJ, glTF (.gltf), and GLB (.glb) formats.
        For glTF/GLB files UE5's Interchange Framework handles import automatically —
        FBX options are not applied but all other parameters still work.

        Args:
            file_path:               OS path on UE5 machine (e.g. "C:/Models/table.fbx")
            destination_path:        Content Browser destination (default "/Game/Meshes/")
            combine_meshes:          Merge all meshes into one asset (default True)
            generate_lightmap_uvs:   Auto-generate UV channel 1 for lightmaps (default True)
            auto_generate_collision: Create simple collision hull (default True)
            import_materials:        Import materials embedded in the file (default True)
            import_textures:         Import textures embedded in the file (default True)

        Returns:
            JSON string with StructuredResult — outputs on success:
              {
                "success": true,
                "stage": "import_static_mesh",
                "outputs": {
                  "asset_path": "/Game/Meshes/SM_Table",
                  "asset_type": "StaticMesh",
                  "poly_count": -1
                },
                "warnings": [], "errors": [], "log_tail": []
              }
        """
        user_code = f"""
import os

file_path               = {file_path!r}
destination_path        = {destination_path!r}
combine_meshes          = {combine_meshes!r}
generate_lightmap_uvs   = {generate_lightmap_uvs!r}
auto_generate_collision = {auto_generate_collision!r}
import_materials_flag   = {import_materials!r}
import_textures_flag    = {import_textures!r}

asset_name = os.path.splitext(os.path.basename(file_path))[0]
dest = destination_path.rstrip("/") or "/Game/Meshes"
unreal.EditorAssetLibrary.make_directory(dest)

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
task = unreal.AssetImportTask()
task.filename         = file_path
task.destination_path = dest
task.destination_name = asset_name
task.automated        = True
task.save             = True
task.replace_existing = True

# FBX/OBJ options — skip for glTF/GLB (Interchange handles those)
ext = os.path.splitext(file_path)[1].lower()
if ext in (".fbx", ".obj"):
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh",       True)
    options.set_editor_property("import_as_skeletal", False)
    options.set_editor_property("import_materials",  import_materials_flag)
    options.set_editor_property("import_textures",   import_textures_flag)
    smd = options.static_mesh_import_data
    smd.set_editor_property("combine_meshes",          combine_meshes)
    smd.set_editor_property("generate_lightmap_u_vs",  generate_lightmap_uvs)
    smd.set_editor_property("auto_generate_collision", auto_generate_collision)
    task.set_editor_property("options", options)

asset_tools.import_asset_tasks([task])

imported = task.get_editor_property("imported_object_paths")
if not imported:
    raise RuntimeError(
        "Import returned no paths. Verify the file exists on the UE5 "
        "host machine at: " + file_path
    )

asset_path_full  = imported[0]
asset_path_clean = asset_path_full.split(".")[0] if "." in asset_path_full else asset_path_full

mesh = unreal.load_asset(asset_path_full)
poly_count = -1  # not directly exposed in Python API; -1 = imported OK
if not (mesh and isinstance(mesh, unreal.StaticMesh)):
    _warnings.append("Imported asset did not load as StaticMesh; verify in Content Browser")

_result["asset_path"] = asset_path_clean
_result["asset_type"] = "StaticMesh"
_result["poly_count"] = poly_count
"""
        exec_structured = _get_substrate()
        r = exec_structured(user_code, "import_static_mesh")
        return json.dumps(r)

    # ── Tool 3: import_skeletal_mesh ─────────────────────────────────────────

    @mcp.tool()
    async def import_skeletal_mesh(
        ctx: Context,
        file_path: str,
        destination_path: str = "/Game/Characters/",
        skeleton: str = "",
        import_animations: bool = True,
        import_morph_targets: bool = True,
        import_materials: bool = True,
    ) -> str:
        """Import an FBX file as a Skeletal Mesh into UE5 Content Browser.

        Args:
            file_path:            OS path to the FBX file on the UE5 Windows machine
                                  (e.g. "C:/Characters/Bastila.fbx")
            destination_path:     Content Browser destination (default "/Game/Characters/")
            skeleton:             Content Browser path to an existing Skeleton asset to
                                  reuse, e.g. "/Game/Mannequin/SK_Mannequin_Skeleton".
                                  Leave empty ("") to create a new skeleton from the file.
            import_animations:    Import embedded animations as AnimSequence assets
                                  (default True)
            import_morph_targets: Import morph targets / blend shapes (default True)
            import_materials:     Import materials embedded in the FBX (default True)

        Returns:
            JSON string with StructuredResult — outputs on success:
              {
                "success": true,
                "stage": "import_skeletal_mesh",
                "outputs": {
                  "asset_path": "/Game/Characters/SK_Bastila",
                  "asset_type": "SkeletalMesh",
                  "skeleton_path": "/Game/Characters/SK_Bastila_Skeleton",
                  "animations_imported": ["Idle", "Walk"],
                  "reused_skeleton": false
                },
                "warnings": [], "errors": [], "log_tail": []
              }
        """
        user_code = f"""
import os

file_path             = {file_path!r}
destination_path      = {destination_path!r}
skeleton_path         = {skeleton!r}
do_import_animations  = {import_animations!r}
do_import_morphs      = {import_morph_targets!r}
do_import_materials   = {import_materials!r}

asset_name = os.path.splitext(os.path.basename(file_path))[0]
dest = destination_path.rstrip("/") or "/Game/Characters"
unreal.EditorAssetLibrary.make_directory(dest)

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

# Build FBX import options
options = unreal.FbxImportUI()
options.set_editor_property("import_mesh",        True)
options.set_editor_property("import_as_skeletal",  True)
options.set_editor_property("import_animations",   do_import_animations)
options.set_editor_property("import_materials",    do_import_materials)

# Morph targets live on the sub-data object
skd = options.skeletal_mesh_import_data
skd.set_editor_property("import_morph_targets", do_import_morphs)

# Optionally reuse an existing skeleton
reused_skeleton = False
if skeleton_path:
    skel = unreal.EditorAssetLibrary.load_asset(skeleton_path)
    if skel and isinstance(skel, unreal.Skeleton):
        options.set_editor_property("skeleton", skel)
        reused_skeleton = True
    else:
        _warnings.append(f"Skeleton not found at {{skeleton_path}}, creating new skeleton")

task = unreal.AssetImportTask()
task.filename         = file_path
task.destination_path = dest
task.destination_name = asset_name
task.automated        = True
task.save             = True
task.replace_existing = True
task.set_editor_property("options", options)

asset_tools.import_asset_tasks([task])

imported = task.get_editor_property("imported_object_paths")
if not imported:
    raise RuntimeError(
        "Import returned no paths. Verify the file exists on the UE5 "
        "host machine at: " + file_path
    )

# The first path is usually the SkeletalMesh; others may be AnimSequences
sk_path_full  = imported[0]
sk_path_clean = sk_path_full.split(".")[0] if "." in sk_path_full else sk_path_full

# Discover skeleton path from the imported mesh
skel_path_clean = ""
sk_asset = unreal.load_asset(sk_path_full)
if sk_asset and isinstance(sk_asset, unreal.SkeletalMesh):
    skel_obj = sk_asset.get_editor_property("skeleton")
    if skel_obj:
        skel_path_clean = skel_obj.get_path_name().split(".")[0]
else:
    _warnings.append("Imported asset did not load as SkeletalMesh; verify in Content Browser")

# Collect animation names from the other imported paths
anim_names = []
for p in imported[1:]:
    anim_asset = unreal.load_asset(p)
    if anim_asset and isinstance(anim_asset, unreal.AnimSequence):
        anim_names.append(anim_asset.get_name())

_result["asset_path"]          = sk_path_clean
_result["asset_type"]          = "SkeletalMesh"
_result["skeleton_path"]       = skel_path_clean
_result["animations_imported"] = anim_names
_result["reused_skeleton"]     = reused_skeleton
"""
        exec_structured = _get_substrate()
        r = exec_structured(user_code, "import_skeletal_mesh")
        return json.dumps(r)
