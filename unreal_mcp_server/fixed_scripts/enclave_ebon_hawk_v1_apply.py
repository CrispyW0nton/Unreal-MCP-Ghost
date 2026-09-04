import hashlib
import json
import os
import unreal

EXPECTED_PROJECT = "EnclaveProject"
EBON_GUID = "B618B798424015C10441568564ACA29B"
ORIGINAL_MESH = "/Game/LevelPrototyping/KotorModels/ebon_01.ebon_01"
OUTPUT_ROOT = "/Game/MCPStudio/Enclave/EbonHawk/v2"
TEXTURE_ROOT = OUTPUT_ROOT + "/Textures"
MATERIAL_ROOT = OUTPUT_ROOT + "/Materials"
MESH_ROOT = OUTPUT_ROOT + "/Meshes"
CANDIDATE_MESH = MESH_ROOT + "/SM_EbonHawk_GhostStudio_v2.SM_EbonHawk_GhostStudio_v2"
ORIGINAL_LOCATION = (-4620.0, 522.511671, 20.0)
ORIGINAL_ROTATION = (0.0, 90.0, 90.0)
ORIGINAL_SCALE = (19.0, 19.0, 19.0)
CANDIDATE_ROTATION = (0.0, 90.0, 0.0)
IMPORT_UNIFORM_SCALE = 1.0
BAKED_BUILD_SCALE = 1.0
GHOST_STUDIO_VERTEX_SCALE = 0.705
CANDIDATE_SCALE = (1.0, 1.0, 1.0)
STAGE_RELATIVE = "MCPStudio/staging/ebon_hawk_ghoststudio_v2"
STAGED_FILES = {
    "fbx": ("SM_EbonHawk_GhostStudio_v2.fbx", "1b65e86e1191b6b283ac16a9da668c70235e303c1d94d092c7ae70f964759f94"),
    "manifest": ("SM_EbonHawk_GhostStudio_v2.ghostrigger.json", "456a5725fbcdaa7609fa66d6e09b077cbffdec08f86736fd582de6e3c7d89d66"),
    "base_color": ("textures/v_ehawk01.png", "46fe4f73d0d7543f0dc2bed8c15c542f104cd4431a14b8140f3b06eb88932772"),
    "detail_color": ("textures/v_ehawk01a.png", "a057c668d1b67e97046ee220e04bfbbdfe66663310e016bab4e28af022dc3ea9"),
}
ORIGINAL_MESH_FILE = ("Content/LevelPrototyping/KotorModels/ebon_01.uasset", "76678c57fcc881e3c4a89cf55391cb121cdd26ed082e1b9cd7bf6f59104216f5")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _guid(actor):
    try:
        value = actor.get_actor_guid()
    except Exception:
        value = actor.get_editor_property("actor_guid")
    try:
        text = value.to_string()
    except Exception:
        text = str(value)
    return text.replace("-", "").replace(" ", "").upper()


def _find_actor_and_component():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matches = [actor for actor in subsystem.get_all_level_actors() if _guid(actor) == EBON_GUID]
    if len(matches) != 1:
        raise RuntimeError("The fixed Ebon Hawk actor identity is not unique")
    components = list(matches[0].get_components_by_class(unreal.StaticMeshComponent) or [])
    if len(components) != 1:
        raise RuntimeError("The fixed Ebon Hawk actor must have one static-mesh component")
    return matches[0], components[0]


def _close_vector(value, expected, tolerance=0.01):
    observed = (float(value.x), float(value.y), float(value.z))
    return all(abs(left - right) <= tolerance for left, right in zip(observed, expected))


def _close_rotation(value, expected, tolerance=0.01):
    observed = (float(value.pitch), float(value.yaw), float(value.roll))
    return all(abs(left - right) <= tolerance for left, right in zip(observed, expected))


def _rotator(pitch_yaw_roll):
    value = unreal.Rotator()
    value.set_editor_property("pitch", pitch_yaw_roll[0])
    value.set_editor_property("yaw", pitch_yaw_roll[1])
    value.set_editor_property("roll", pitch_yaw_roll[2])
    return value


def _save_actor_package(actor):
    package = actor.get_outermost()
    if package is None or not unreal.EditorLoadingAndSavingUtils.save_packages([package], False):
        raise RuntimeError("Could not save the exact Ebon Hawk external actor package")
    return package.get_path_name()


def _restore_source_transform(actor):
    actor.set_actor_location(unreal.Vector(*ORIGINAL_LOCATION), False, False)
    actor.set_actor_rotation(_rotator(ORIGINAL_ROTATION), False)
    actor.set_actor_scale3d(unreal.Vector(*ORIGINAL_SCALE))


def _apply_candidate_transform(actor):
    actor.set_actor_location(unreal.Vector(*ORIGINAL_LOCATION), False, False)
    actor.set_actor_rotation(_rotator(CANDIDATE_ROTATION), False)
    actor.set_actor_scale3d(unreal.Vector(*CANDIDATE_SCALE))


def _import_texture(asset_tools, filename, name):
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = TEXTURE_ROOT
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = False
    asset_tools.import_asset_tasks([task])
    paths = list(task.get_editor_property("imported_object_paths") or [])
    if len(paths) != 1:
        raise RuntimeError(f"Expected one imported Ebon Hawk texture for {name}")
    texture = unreal.load_asset(paths[0])
    if texture is None or not isinstance(texture, unreal.Texture2D):
        raise RuntimeError(f"Imported Ebon Hawk texture is invalid: {name}")
    texture.set_editor_property("srgb", True)
    texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
    unreal.EditorAssetLibrary.save_asset(texture.get_path_name(), only_if_is_dirty=False)
    return texture


def _make_legacy_material(asset_tools, name, texture):
    material = asset_tools.create_asset(name, MATERIAL_ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if material is None:
        raise RuntimeError(f"Could not create Ebon Hawk staging material {name}")
    sample = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionTextureSample, -500, -100
    )
    sample.set_editor_property("texture", texture)
    if not unreal.MaterialEditingLibrary.connect_material_property(
        sample, "RGB", unreal.MaterialProperty.MP_BASE_COLOR
    ):
        raise RuntimeError("Could not connect the Ebon Hawk base-color atlas")
    for property_name, value, y in (
        (unreal.MaterialProperty.MP_METALLIC, 0.0, 100),
        (unreal.MaterialProperty.MP_ROUGHNESS, 0.42, 220),
        (unreal.MaterialProperty.MP_SPECULAR, 0.5, 340),
    ):
        constant = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant, -260, y
        )
        constant.set_editor_property("r", value)
        if not unreal.MaterialEditingLibrary.connect_material_property(constant, "", property_name):
            raise RuntimeError("Could not connect an Ebon Hawk staging material constant")
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(material.get_path_name(), only_if_is_dirty=False)
    return material


if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The fixed Ebon Hawk handoff is connected to the wrong project")
project_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
saved_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
stage_root = os.path.realpath(os.path.join(saved_root, STAGE_RELATIVE))
staged = {}
for label, (relative_path, expected_hash) in STAGED_FILES.items():
    path = os.path.realpath(os.path.join(stage_root, relative_path))
    if os.path.commonpath([stage_root, path]) != stage_root or _sha256(path) != expected_hash:
        raise RuntimeError(f"Pinned Ghost Studio Ebon Hawk input mismatched: {label}")
    staged[label] = path
with open(staged["manifest"], "r", encoding="utf-8") as stream:
    manifest = json.load(stream)
if (
    manifest.get("schema") != "ghostrigger.kotor_fbx_manifest.v1"
    or str(manifest.get("source", {}).get("resref", "")).lower() != "v_ehawk"
    or manifest.get("fbx", {}).get("compatibility_profile") != "unreal"
    or manifest.get("fbx", {}).get("ok") is not True
    or manifest.get("mcpstudio", {}).get("schema") != "mcpstudio.ghoststudio-geometry-scale/v1"
    or abs(float(manifest.get("mcpstudio", {}).get("vertex_scale", 0.0)) - GHOST_STUDIO_VERTEX_SCALE) > 0.000001
):
    raise RuntimeError("The pinned scaled Ghost Studio Ebon Hawk manifest is invalid")
original_mesh_file = os.path.realpath(os.path.join(project_root, ORIGINAL_MESH_FILE[0]))
if _sha256(original_mesh_file) != ORIGINAL_MESH_FILE[1]:
    raise RuntimeError("The protected original Ebon Hawk mesh identity changed")

evidence_root = os.path.realpath(os.path.join(saved_root, "MCPStudio/evidence"))
os.makedirs(evidence_root, exist_ok=True)
receipt_path = os.path.join(evidence_root, "enclave_ebon_hawk_v2_receipt.json")
actor, component = _find_actor_and_component()
if os.path.isfile(receipt_path):
    with open(receipt_path, "r", encoding="utf-8") as stream:
        prior = json.load(stream)
    current = component.get_editor_property("static_mesh")
    if (
        prior.get("schema") != "mcpstudio.enclave-ebon-hawk-receipt/v2"
        or current is None
        or current.get_path_name() != CANDIDATE_MESH
        or not _close_vector(actor.get_actor_location(), ORIGINAL_LOCATION)
        or not _close_rotation(actor.get_actor_rotation(), CANDIDATE_ROTATION)
        or not _close_vector(actor.get_actor_scale3d(), CANDIDATE_SCALE)
        or _sha256(original_mesh_file) != ORIGINAL_MESH_FILE[1]
    ):
        raise RuntimeError("The existing Ebon Hawk handoff receipt failed replay validation")
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-ebon-hawk-handoff/v2",
        "mode": "apply",
        "idempotent_replay": True,
        "receipt_path": receipt_path,
        "outputs": prior.get("outputs", {}),
    })
else:
    if unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False):
        raise RuntimeError("The exclusive Ebon Hawk namespace contains unreceipted assets")
    current = component.get_editor_property("static_mesh")
    if current is None or current.get_path_name() != ORIGINAL_MESH:
        raise RuntimeError("The Ebon Hawk actor is not in its protected pre-handoff state")
    if (
        not _close_vector(actor.get_actor_location(), ORIGINAL_LOCATION)
        or not _close_rotation(actor.get_actor_rotation(), ORIGINAL_ROTATION)
        or not _close_vector(actor.get_actor_scale3d(), ORIGINAL_SCALE)
    ):
        raise RuntimeError("The Ebon Hawk actor transform is not in its protected pre-handoff state")
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    actor_changed = False
    try:
        unreal.EditorAssetLibrary.make_directory(TEXTURE_ROOT)
        main_texture = _import_texture(asset_tools, staged["base_color"], "T_EbonHawk_BaseColor_v1")
        detail_texture = _import_texture(asset_tools, staged["detail_color"], "T_EbonHawk_Detail_BaseColor_v1")

        task = unreal.AssetImportTask()
        task.filename = staged["fbx"]
        task.destination_path = MESH_ROOT
        task.destination_name = "SM_EbonHawk_GhostStudio_v2"
        task.automated = True
        task.save = True
        task.replace_existing = False
        options = unreal.FbxImportUI()
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("import_as_skeletal", False)
        options.set_editor_property("import_materials", False)
        options.set_editor_property("import_textures", False)
        options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        static_data = options.get_editor_property("static_mesh_import_data")
        static_data.set_editor_property("combine_meshes", True)
        static_data.set_editor_property("import_uniform_scale", IMPORT_UNIFORM_SCALE)
        static_data.set_editor_property("generate_lightmap_u_vs", True)
        static_data.set_editor_property("auto_generate_collision", True)
        task.options = options
        asset_tools.import_asset_tasks([task])
        imported = list(task.get_editor_property("imported_object_paths") or [])
        meshes = [unreal.load_asset(path) for path in imported]
        meshes = [asset for asset in meshes if isinstance(asset, unreal.StaticMesh)]
        if len(meshes) != 1:
            raise RuntimeError(f"Expected one imported Ebon Hawk StaticMesh, observed {len(meshes)}")
        candidate = meshes[0]
        if candidate.get_path_name() != CANDIDATE_MESH:
            raise RuntimeError("The imported Ebon Hawk mesh did not use its fixed identity")

        mesh_editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        lod_count = int(mesh_editor.get_lod_count(candidate))
        if lod_count < 1:
            raise RuntimeError("The imported Ebon Hawk mesh has no buildable LOD")
        for lod_index in range(lod_count):
            settings = mesh_editor.get_lod_build_settings(candidate, lod_index)
            current_scale = settings.get_editor_property("build_scale3d")
            if not _close_vector(current_scale, (1.0, 1.0, 1.0)):
                raise RuntimeError("The imported Ebon Hawk mesh already has a non-unit build scale")
            settings.set_editor_property(
                "build_scale3d",
                unreal.Vector(BAKED_BUILD_SCALE, BAKED_BUILD_SCALE, BAKED_BUILD_SCALE),
            )
            mesh_editor.set_lod_build_settings(candidate, lod_index, settings)
        unreal.EditorAssetLibrary.save_asset(candidate.get_path_name(), only_if_is_dirty=False)

        main_material = _make_legacy_material(asset_tools, "M_EbonHawk_LegacyPaint_v2", main_texture)
        detail_material = _make_legacy_material(asset_tools, "M_EbonHawk_LegacyDetail_v2", detail_texture)
        candidate.set_material(0, main_material)
        if len(list(candidate.get_editor_property("static_materials") or [])) > 1:
            candidate.set_material(1, detail_material)
        unreal.EditorAssetLibrary.save_asset(candidate.get_path_name(), only_if_is_dirty=False)

        component.set_static_mesh(candidate)
        actor_changed = True
        _apply_candidate_transform(actor)
        bounds_origin, bounds_extent = actor.get_actor_bounds(False)
        footprint_valid = (
            1400.0 <= float(bounds_extent.x) <= 1600.0
            and 1400.0 <= float(bounds_extent.y) <= 1600.0
            and 340.0 <= float(bounds_extent.z) <= 400.0
        )
        if not footprint_valid:
            raise RuntimeError(
                "The corrected Ebon Hawk candidate bounds are outside the landing-area scale contract: "
                f"origin=({float(bounds_origin.x):.6f},{float(bounds_origin.y):.6f},{float(bounds_origin.z):.6f}), "
                f"extent=({float(bounds_extent.x):.6f},{float(bounds_extent.y):.6f},{float(bounds_extent.z):.6f})"
            )
        actor_package = _save_actor_package(actor)
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("Could not save the Enclave map after the Ebon Hawk handoff")
        if _sha256(original_mesh_file) != ORIGINAL_MESH_FILE[1]:
            raise RuntimeError("The protected original Ebon Hawk mesh changed during handoff")
        outputs = {
            "content_root": OUTPUT_ROOT,
            "candidate_mesh": candidate.get_path_name(),
            "textures": [main_texture.get_path_name(), detail_texture.get_path_name()],
            "materials": [main_material.get_path_name(), detail_material.get_path_name()],
            "actor_guid": EBON_GUID,
            "actor_label": actor.get_actor_label(),
            "previous_mesh": ORIGINAL_MESH,
            "source_transform": {
                "location": ORIGINAL_LOCATION,
                "rotation_pitch_yaw_roll": ORIGINAL_ROTATION,
                "scale": ORIGINAL_SCALE,
            },
            "candidate_transform": {
                "location": ORIGINAL_LOCATION,
                "rotation_pitch_yaw_roll": CANDIDATE_ROTATION,
                "scale": CANDIDATE_SCALE,
            },
            "import_uniform_scale": IMPORT_UNIFORM_SCALE,
            "baked_build_scale": BAKED_BUILD_SCALE,
            "ghost_studio_vertex_scale": GHOST_STUDIO_VERTEX_SCALE,
            "actor_package": actor_package,
            "candidate_world_bounds": {
                "origin": [float(bounds_origin.x), float(bounds_origin.y), float(bounds_origin.z)],
                "extent": [float(bounds_extent.x), float(bounds_extent.y), float(bounds_extent.z)],
            },
            "pbr_status": "legacy-albedo-staging-only",
            "substance_upgrade_required": True,
        }
        receipt = {
            "schema": "mcpstudio.enclave-ebon-hawk-receipt/v2",
            "source": {"game": "K2", "resref": "v_ehawk", "fbx_sha256": STAGED_FILES["fbx"][1]},
            "protected_original_mesh_sha256": ORIGINAL_MESH_FILE[1],
            "outputs": outputs,
        }
        receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(receipt_path, "xb") as stream:
            stream.write(receipt_bytes)
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-ebon-hawk-handoff/v2",
            "mode": "apply",
            "idempotent_replay": False,
            "receipt_path": receipt_path,
            "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
            "outputs": outputs,
        })
    except Exception:
        if actor_changed:
            original = unreal.load_asset(ORIGINAL_MESH)
            if original is not None:
                component.set_static_mesh(original)
                _restore_source_transform(actor)
                if not _close_rotation(actor.get_actor_rotation(), ORIGINAL_ROTATION):
                    raise RuntimeError("Could not restore the exact Ebon Hawk source rotation")
        unreal.EditorAssetLibrary.delete_directory(OUTPUT_ROOT)
        raise
