import hashlib
import json
import math
import os
import unreal

EXPECTED_PROJECT = "EnclaveProject"
EXPECTED_MANIFEST_SHA256 = "54a90ba6cb18943c0ddaba928cdf9fa074c688f7c27f652aa9a5f54e1cae4b44"
EXPECTED_MATERIAL_ID = "unrealengine-pack-2:walls:middle-eastern-wall"
SOURCE_MESH = "/Game/LevelPrototyping/ModularKit/SM_Enclave_CentralPavilion_Main_A.SM_Enclave_CentralPavilion_Main_A"
OUTPUT_ROOT = "/Game/MCPStudio/EnclavePilot/v1"
TEXTURE_ROOT = OUTPUT_ROOT + "/Textures"
MATERIAL_ROOT = OUTPUT_ROOT + "/Materials"
MESH_ROOT = OUTPUT_ROOT + "/Meshes"
MAP_ROOT = OUTPUT_ROOT + "/Maps"
MATERIAL_PATH = MATERIAL_ROOT + "/M_Enclave_MiddleEasternWall_Pilot_v1"
PILOT_MESH_PATH = MESH_ROOT + "/SM_Enclave_CentralPavilion_Pilot_v1"
PILOT_MAP_PATH = MAP_ROOT + "/L_Enclave_CentralPavilion_Pilot_v1"
ORIGINAL_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
ORIGINAL_FILES = {
    "targetMap": ("Content/ThirdPerson/Lvl_ThirdPerson.umap", "3e668a9b3098a76f49ce307759ab00662406c7fa0870eeee6e7a2dbf7f854386"),
    "ebonHawkExternalActor": ("Content/__ExternalActors__/ThirdPerson/Lvl_ThirdPerson/C/YR/UEIU0SB2UAJGUYCIP860S0.uasset", "7960dde3774e0d91bfa615d43cfb95ba864028834a59cb3674e1d09173db6169"),
    "sourcePavilion": ("Content/LevelPrototyping/ModularKit/SM_Enclave_CentralPavilion_Main_A.uasset", "a2d152effdcd05f0d4d423a1bc68104dec0251500a512ffa6e9ae70786709504"),
}
TEXTURE_NAMES = {
    "base-color": "T_Enclave_MiddleEasternWall_BaseColor_v1",
    "normal": "T_Enclave_MiddleEasternWall_NormalDX_v1",
    "roughness": "T_Enclave_MiddleEasternWall_Roughness_v1",
    "height": "T_Enclave_MiddleEasternWall_Height_v1",
    "ambient-occlusion": "T_Enclave_MiddleEasternWall_AO_v1",
}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_originals(project_root):
    result = {}
    for label, (relative_path, expected_hash) in ORIGINAL_FILES.items():
        path = os.path.realpath(os.path.join(project_root, relative_path))
        observed_hash = _sha256(path)
        if observed_hash != expected_hash:
            raise RuntimeError(f"Protected input identity mismatch: {label}")
        result[label] = observed_hash
    return result


if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The fixed Enclave pilot is connected to the wrong project")
project_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
original_hashes_before = _verify_originals(project_root)
manifest_path = os.path.realpath(os.path.join(
    unreal.Paths.project_saved_dir(),
    "MCPStudio/material_library/b3012e9533179694/unrealengine-pack-2-walls-middle-eastern-wall/manifest.json",
))
if _sha256(manifest_path) != EXPECTED_MANIFEST_SHA256:
    raise RuntimeError("The fixed staged-material manifest identity changed")
with open(manifest_path, "r", encoding="utf-8") as stream:
    manifest = json.load(stream)
if manifest.get("schemaVersion") != "mcpstudio.enclave-material-stage/v1" or manifest.get("materialId") != EXPECTED_MATERIAL_ID:
    raise RuntimeError("The fixed staged-material manifest contract is invalid")
stage_root = os.path.realpath(os.path.dirname(manifest_path))
staged = {}
for item in manifest.get("staged", []):
    kind = item.get("kind")
    path = os.path.realpath(str(item.get("path") or ""))
    if os.path.commonpath([stage_root, path]) != stage_root or _sha256(path) != item.get("sha256"):
        raise RuntimeError(f"Staged material input failed identity validation: {kind}")
    staged[kind] = item
required = set(TEXTURE_NAMES)
if set(staged) != required:
    raise RuntimeError("The fixed staged material channel set is incomplete")

receipt_dir = os.path.realpath(os.path.join(unreal.Paths.project_saved_dir(), "MCPStudio/evidence"))
os.makedirs(receipt_dir, exist_ok=True)
receipt_path = os.path.join(receipt_dir, "enclave_sandstone_pilot_v1_receipt.json")
screenshot_path = os.path.join(receipt_dir, "enclave_sandstone_pilot_v1.png")
if os.path.exists(receipt_path):
    with open(receipt_path, "r", encoding="utf-8") as stream:
        prior_receipt = json.load(stream)
    if prior_receipt.get("schema") != "mcpstudio.enclave-sandstone-pilot-receipt/v1":
        raise RuntimeError("The existing pilot receipt is not trusted")
    original_hashes_after = _verify_originals(project_root)
    _result.update({
        "schema": "unreal_mcp_ghost.enclave_sandstone_pilot.v1",
        "mode": "apply",
        "idempotent_replay": True,
        "receipt_path": receipt_path,
        "screenshot_path": screenshot_path,
        "outputs": prior_receipt.get("outputs", {}),
        "original_hashes_before": original_hashes_before,
        "original_hashes_after": original_hashes_after,
    })
else:
    existing_outputs = unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False)
    if existing_outputs:
        raise RuntimeError("The exclusive pilot namespace already contains unreceipted assets")
    if os.path.exists(screenshot_path):
        raise RuntimeError("The exclusive pilot screenshot path already exists")

    unreal.EditorAssetLibrary.make_directory(TEXTURE_ROOT)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    imported_paths = {}
    for kind, asset_name in TEXTURE_NAMES.items():
        task = unreal.AssetImportTask()
        task.filename = staged[kind]["path"]
        task.destination_path = TEXTURE_ROOT
        task.destination_name = asset_name
        task.automated = True
        task.save = True
        task.replace_existing = False
        asset_tools.import_asset_tasks([task])
        imported = list(task.get_editor_property("imported_object_paths") or [])
        if len(imported) != 1:
            raise RuntimeError(f"Expected one imported texture for {kind}, observed {len(imported)}")
        texture = unreal.load_asset(imported[0])
        if texture is None or not isinstance(texture, unreal.Texture2D):
            raise RuntimeError(f"Imported asset is not a Texture2D: {kind}")
        if kind == "base-color":
            texture.set_editor_property("srgb", True)
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
        elif kind == "normal":
            texture.set_editor_property("srgb", False)
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
            texture.set_editor_property("flip_green_channel", False)
        else:
            texture.set_editor_property("srgb", False)
            texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
        unreal.EditorAssetLibrary.save_asset(texture.get_path_name(), only_if_is_dirty=False)
        imported_paths[kind] = texture.get_path_name()

    material = asset_tools.create_asset(
        "M_Enclave_MiddleEasternWall_Pilot_v1",
        MATERIAL_ROOT,
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if material is None:
        raise RuntimeError("Could not create the exclusive pilot material")
    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_OPAQUE)
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    material.set_editor_property("two_sided", False)
    positions = {
        "base-color": (-700, -260),
        "normal": (-700, -40),
        "roughness": (-700, 180),
        "ambient-occlusion": (-700, 400),
    }
    properties = {
        "base-color": unreal.MaterialProperty.MP_BASE_COLOR,
        "normal": unreal.MaterialProperty.MP_NORMAL,
        "roughness": unreal.MaterialProperty.MP_ROUGHNESS,
        "ambient-occlusion": unreal.MaterialProperty.MP_AMBIENT_OCCLUSION,
    }
    expression_paths = {}
    for kind, position in positions.items():
        expression = unreal.MaterialEditingLibrary.create_material_expression(
            material,
            unreal.MaterialExpressionTextureSample,
            position[0],
            position[1],
        )
        if expression is None:
            raise RuntimeError(f"Could not create material expression for {kind}")
        expression.set_editor_property("texture", unreal.load_asset(imported_paths[kind]))
        output_name = "RGB" if kind in {"base-color", "normal"} else "R"
        if not unreal.MaterialEditingLibrary.connect_material_property(expression, output_name, properties[kind]):
            raise RuntimeError(f"Could not connect material property for {kind}")
        expression_paths[kind] = expression.get_path_name()
    metallic = unreal.MaterialEditingLibrary.create_material_expression(
        material,
        unreal.MaterialExpressionConstant,
        -420,
        560,
    )
    metallic.set_editor_property("r", 0.0)
    if not unreal.MaterialEditingLibrary.connect_material_property(
        metallic, "", unreal.MaterialProperty.MP_METALLIC
    ):
        raise RuntimeError("Could not enforce the nonmetal metallic policy")
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(material.get_path_name(), only_if_is_dirty=False)

    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE_MESH, PILOT_MESH_PATH):
        raise RuntimeError("Could not duplicate the pavilion into the exclusive pilot namespace")
    pilot_mesh = unreal.load_asset(PILOT_MESH_PATH)
    if pilot_mesh is None or not isinstance(pilot_mesh, unreal.StaticMesh):
        raise RuntimeError("The duplicated pilot mesh is unavailable")
    pilot_mesh.set_material(0, material)
    unreal.EditorAssetLibrary.save_asset(pilot_mesh.get_path_name(), only_if_is_dirty=False)

    if not unreal.EditorLevelLibrary.new_level(PILOT_MAP_PATH):
        raise RuntimeError("Could not create the exclusive pilot level")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    pavilion = actor_subsystem.spawn_actor_from_object(
        pilot_mesh, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0)
    )
    if pavilion is None:
        raise RuntimeError("Could not spawn the pilot pavilion")
    pavilion.set_actor_label("MCPStudio_Enclave_Pavilion_PBR_Pilot_v1")
    origin, extent = pavilion.get_actor_bounds(False, False)
    radius = max(float(extent.x), float(extent.y), float(extent.z), 100.0)

    floor_mesh = unreal.load_asset("/Engine/BasicShapes/Plane.Plane")
    floor_actor = actor_subsystem.spawn_actor_from_object(
        floor_mesh,
        unreal.Vector(float(origin.x), float(origin.y), float(origin.z - extent.z - 8.0)),
        unreal.Rotator(0.0, 0.0, 0.0),
    )
    if floor_actor:
        floor_actor.set_actor_label("MCPStudio_Neutral_Ground_v1")
        floor_actor.set_actor_scale3d(unreal.Vector(radius / 50.0, radius / 50.0, 1.0))

    key = actor_subsystem.spawn_actor_from_class(
        unreal.DirectionalLight,
        unreal.Vector(0.0, 0.0, 0.0),
        unreal.Rotator(-38.0, -24.0, -38.0),
    )
    key.set_actor_label("MCPStudio_Warm_Key_v1")
    key_component = key.get_component_by_class(unreal.DirectionalLightComponent)
    key_component.set_editor_property("intensity", 8.0)
    key_component.set_editor_property("light_color", unreal.Color(255, 226, 190, 255))

    sky_atmosphere = actor_subsystem.spawn_actor_from_class(
        unreal.SkyAtmosphere, unreal.Vector(), unreal.Rotator()
    )
    sky_atmosphere.set_actor_label("MCPStudio_SkyAtmosphere_v1")
    skylight = actor_subsystem.spawn_actor_from_class(
        unreal.SkyLight, unreal.Vector(), unreal.Rotator()
    )
    skylight.set_actor_label("MCPStudio_Skylight_v1")
    sky_component = skylight.get_component_by_class(unreal.SkyLightComponent)
    sky_component.set_editor_property("intensity", 1.0)
    sky_component.set_editor_property("real_time_capture", True)

    camera_location = unreal.Vector(
        float(origin.x + radius * 2.4),
        float(origin.y - radius * 2.4),
        float(origin.z + radius * 0.55),
    )
    camera_rotation = unreal.MathLibrary.find_look_at_rotation(camera_location, origin)
    camera = actor_subsystem.spawn_actor_from_class(
        unreal.CameraActor, camera_location, camera_rotation
    )
    camera.set_actor_label("MCPStudio_Enclave_Pilot_Camera_v1")
    camera_component = camera.get_component_by_class(unreal.CameraComponent)
    camera_component.set_editor_property("field_of_view", 52.0)

    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("Could not save the exclusive pilot level")
    unreal.AutomationLibrary.finish_loading_before_screenshot()
    screenshot_task = unreal.AutomationLibrary.take_high_res_screenshot(
        1600,
        1200,
        screenshot_path,
        camera,
        False,
        False,
        unreal.ComparisonTolerance.LOW,
        "MCPStudio Enclave sandstone PBR pilot v1",
        0.5,
        True,
    )
    if screenshot_task is None:
        raise RuntimeError("Unreal did not enqueue the pilot screenshot")

    original_hashes_after = _verify_originals(project_root)
    outputs = {
        "content_root": OUTPUT_ROOT,
        "textures": imported_paths,
        "material": material.get_path_name(),
        "material_expressions": expression_paths,
        "height_imported_for_future_relief_policy": imported_paths["height"],
        "metallic_policy": "nonmetal-zero",
        "pilot_mesh": pilot_mesh.get_path_name(),
        "pilot_map": PILOT_MAP_PATH,
        "screenshot_path": screenshot_path,
        "screenshot_queued": True,
    }
    receipt = {
        "schema": "mcpstudio.enclave-sandstone-pilot-receipt/v1",
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "material_id": EXPECTED_MATERIAL_ID,
        "original_hashes_before": original_hashes_before,
        "original_hashes_after": original_hashes_after,
        "outputs": outputs,
    }
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with open(receipt_path, "xb") as stream:
        stream.write(receipt_bytes)
    _result.update({
        "schema": "unreal_mcp_ghost.enclave_sandstone_pilot.v1",
        "mode": "apply",
        "idempotent_replay": False,
        "receipt_path": receipt_path,
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "screenshot_path": screenshot_path,
        "outputs": outputs,
        "original_hashes_before": original_hashes_before,
        "original_hashes_after": original_hashes_after,
    })
