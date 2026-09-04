import hashlib
import json
import os
import unreal


MODE = globals().get("MCPSTUDIO_MODE", "dry_run")
EXPECTED_PROJECT = "EnclaveProject"
EXPECTED_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
EXPECTED_MANIFEST_SHA256 = "cfae47bdd70738b834d24d1022f133a12f13721c396157bb72afc8b43e68c19d"
MANIFEST_RELATIVE_PATH = "MCPStudio/material_library/landing-v1/manifest.json"
OUTPUT_ROOT = "/Game/MCPStudio/Enclave/LandingMaterials/v1"
TEXTURE_ROOT = OUTPUT_ROOT + "/Textures"
MATERIAL_ROOT = OUTPUT_ROOT + "/Materials"
RECEIPT_NAME = "enclave_landing_material_pass_v1_receipt.json"
ROLLBACK_NAME = "enclave_landing_material_pass_v1_rollback.json"

TARGETS = {
    "structure": {
        "label": "m13aa_01a2",
        "guid": "39A96FF046720C0C936788BC9A08FBF1",
        "mesh": "/Game/MCPStudio/Enclave/LandingScaleBake/v1/Meshes/SM_LandingStructure_m13aa_01a_ScaleBaked_v1.SM_LandingStructure_m13aa_01a_ScaleBaked_v1",
    },
    "floor": {
        "label": "Floor",
        "guid": "04B40FE441C580AE34D06B94E7FAFBF2",
        "mesh": "/Game/MCPStudio/Enclave/LandingScaleBake/v1/Meshes/SM_LandingFloor_ScaleBaked_v1.SM_LandingFloor_ScaleBaked_v1",
    },
    "door-west": {
        "label": "dor_lda3",
        "guid": "FDADFE844299C99B7C68A09E080D956B",
        "mesh": "/Game/MCPStudio/Enclave/LandingScaleBake/v1/Meshes/SM_LandingDoor_West_ScaleBaked_v1.SM_LandingDoor_West_ScaleBaked_v1",
    },
    "door-east": {
        "label": "dor_lda02",
        "guid": "91339B3342056C4A1E4B8DBCCB51237B",
        "mesh": "/Game/MCPStudio/Enclave/LandingScaleBake/v1/Meshes/SM_LandingDoor_East_ScaleBaked_v1.SM_LandingDoor_East_ScaleBaked_v1",
    },
    "door-north": {
        "label": "dor_lda4",
        "guid": "C312879645CACBA863C2FE93E5CC514D",
        "mesh": "/Game/MCPStudio/Enclave/LandingScaleBake/v1/Meshes/SM_LandingDoor_North_ScaleBaked_v1.SM_LandingDoor_North_ScaleBaked_v1",
    },
}

FAMILY_CONFIG = {
    "stone-clean": ("M_Enclave_Landing_StoneClean_v1", 8.0),
    "stone-weathered": ("M_Enclave_Landing_StoneWeathered_v1", 8.0),
    "metal-grate": ("M_Enclave_Landing_MetalGrate_v1", 6.0),
    "metal-trim": ("M_Enclave_Landing_MetalTrim_v1", 10.0),
    "metal-door": ("M_Enclave_Landing_MetalDoor_v1", 3.0),
    "paving-primary": ("M_Enclave_Landing_PavingPrimary_v1", 10.0),
    "paving-secondary": ("M_Enclave_Landing_PavingSecondary_v1", 10.0),
    "grassland": ("M_Enclave_Landing_Grassland_v1", 1800.0),
    "bark": ("M_Enclave_Landing_Bark_v1", 5.0),
    "foliage": ("M_Enclave_Landing_Foliage_v1", 1.0),
    "rock": ("M_Enclave_Landing_Rock_v1", 5.0),
}

STRUCTURE_FAMILIES = [
    "metal-trim",
    "glass",
    "metal-grate",
    "metal-trim",
    "stone-clean",
    "stone-weathered",
    "metal-trim",
    "paving-primary",
    "paving-secondary",
    "foliage",
    "rock",
    "grassland",
    "bark",
    "emissive",
]


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset_path(value):
    return value.split(".", 1)[0]


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


def _find_targets():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    result = {}
    for key, spec in TARGETS.items():
        matches = [actor for actor in actors if actor.get_actor_label() == spec["label"]]
        if len(matches) != 1 or _guid(matches[0]) != spec["guid"]:
            raise RuntimeError("Landing actor identity mismatch: " + spec["label"])
        component = matches[0].get_component_by_class(unreal.StaticMeshComponent)
        if component is None or component.static_mesh is None:
            raise RuntimeError("Landing actor has no static mesh: " + spec["label"])
        if component.static_mesh.get_path_name() != spec["mesh"]:
            raise RuntimeError("Landing actor mesh drifted: " + spec["label"])
        result[key] = (matches[0], component, component.static_mesh)
    return result


def _material_paths(mesh):
    return [
        mesh.get_material(index).get_path_name() if mesh.get_material(index) else ""
        for index in range(len(mesh.get_editor_property("static_materials")))
    ]


def _override_paths(component):
    return [item.get_path_name() if item else "" for item in component.get_editor_property("override_materials")]


def _load_manifest():
    path = os.path.realpath(os.path.join(unreal.Paths.project_saved_dir(), MANIFEST_RELATIVE_PATH))
    if _sha256(path) != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("The fixed landing material manifest identity changed")
    with open(path, "r", encoding="utf-8") as stream:
        manifest = json.load(stream)
    if manifest.get("schemaVersion") != "mcpstudio.enclave-landing-material-stage/v1":
        raise RuntimeError("The fixed landing material manifest schema changed")
    families = {item["family"]: item for item in manifest.get("families", [])}
    if set(families) != set(FAMILY_CONFIG):
        raise RuntimeError("The fixed landing material family set changed")
    root = os.path.realpath(os.path.dirname(path))
    for family, item in families.items():
        for channel in item.get("channels", []):
            channel_path = os.path.realpath(channel.get("path", ""))
            if os.path.commonpath([root, channel_path]) != root:
                raise RuntimeError("A landing material channel escaped the fixed stage")
            if _sha256(channel_path) != channel.get("sha256"):
                raise RuntimeError("Landing material channel identity changed: " + family)
    return path, families


def _import_texture(asset_tools, family, kind, record):
    name = "T_Enclave_Landing_%s_%s_v1" % (
        family.replace("-", "").title(),
        kind.replace("-", "").title(),
    )
    path = TEXTURE_ROOT + "/" + name
    existing = unreal.load_asset(path)
    if existing is not None:
        return existing
    task = unreal.AssetImportTask()
    task.filename = record["path"]
    task.destination_path = TEXTURE_ROOT
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = False
    asset_tools.import_asset_tasks([task])
    imported = list(task.get_editor_property("imported_object_paths") or [])
    if len(imported) != 1:
        raise RuntimeError("Expected one imported texture for %s/%s" % (family, kind))
    texture = unreal.load_asset(imported[0])
    if not isinstance(texture, unreal.Texture2D):
        raise RuntimeError("Landing material import is not Texture2D")
    texture.set_editor_property("srgb", kind == "base-color")
    if kind == "normal":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_NORMALMAP)
        texture.set_editor_property("flip_green_channel", False)
    elif kind != "base-color":
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    unreal.EditorAssetLibrary.save_asset(texture.get_path_name(), only_if_is_dirty=False)
    return texture


def _connect_sample(material, texture, texcoord, x, y, prop, output="RGB"):
    sample = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionTextureSample, x, y
    )
    sample.set_editor_property("texture", texture)
    if texcoord is not None:
        unreal.MaterialEditingLibrary.connect_material_expressions(
            texcoord, "", sample, "Coordinates"
        )
    if not unreal.MaterialEditingLibrary.connect_material_property(sample, output, prop):
        raise RuntimeError("Could not connect landing material property")


def _create_pbr_material(asset_tools, family, config, textures):
    asset_name, tiling = config
    path = MATERIAL_ROOT + "/" + asset_name
    existing = unreal.load_asset(path)
    if existing is not None:
        return existing
    material = asset_tools.create_asset(asset_name, MATERIAL_ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if material is None:
        raise RuntimeError("Could not create landing material: " + family)
    material.set_editor_property("two_sided", family == "foliage")
    if family == "foliage":
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        material.set_editor_property("opacity_mask_clip_value", 0.28)
    texcoord = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionTextureCoordinate, -900, 0
    )
    texcoord.set_editor_property("u_tiling", tiling)
    texcoord.set_editor_property("v_tiling", tiling)
    _connect_sample(material, textures["base-color"], texcoord, -650, -300, unreal.MaterialProperty.MP_BASE_COLOR)
    _connect_sample(material, textures["normal"], texcoord, -650, -80, unreal.MaterialProperty.MP_NORMAL)
    _connect_sample(material, textures["roughness"], texcoord, -650, 140, unreal.MaterialProperty.MP_ROUGHNESS, "R")
    _connect_sample(material, textures["ambient-occlusion"], texcoord, -650, 360, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, "R")
    if family.startswith("metal-"):
        _connect_sample(material, textures["metallic"], texcoord, -650, 580, unreal.MaterialProperty.MP_METALLIC, "R")
    else:
        constant = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant, -400, 580
        )
        constant.set_editor_property("r", 0.0)
        unreal.MaterialEditingLibrary.connect_material_property(constant, "", unreal.MaterialProperty.MP_METALLIC)
    if family == "foliage":
        _connect_sample(material, textures["opacity"], texcoord, -650, 800, unreal.MaterialProperty.MP_OPACITY_MASK, "R")
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(material.get_path_name(), only_if_is_dirty=False)
    return material


def _create_constant_material(asset_tools, key):
    name = "M_Enclave_Landing_Glass_v1" if key == "glass" else "M_Enclave_Landing_Emissive_v1"
    path = MATERIAL_ROOT + "/" + name
    existing = unreal.load_asset(path)
    if existing is not None:
        return existing
    material = asset_tools.create_asset(name, MATERIAL_ROOT, unreal.Material, unreal.MaterialFactoryNew())
    if key == "glass":
        material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        material.set_editor_property("two_sided", True)
        material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
        values = [
            (unreal.MaterialProperty.MP_BASE_COLOR, (0.025, 0.055, 0.075, 1.0)),
            (unreal.MaterialProperty.MP_OPACITY, 0.34),
            (unreal.MaterialProperty.MP_ROUGHNESS, 0.14),
            (unreal.MaterialProperty.MP_METALLIC, 0.0),
        ]
    else:
        values = [
            (unreal.MaterialProperty.MP_BASE_COLOR, (0.01, 0.025, 0.03, 1.0)),
            (unreal.MaterialProperty.MP_EMISSIVE_COLOR, (2.5, 5.5, 6.5, 1.0)),
            (unreal.MaterialProperty.MP_ROUGHNESS, 0.22),
            (unreal.MaterialProperty.MP_METALLIC, 0.0),
        ]
    for index, (prop, value) in enumerate(values):
        cls = unreal.MaterialExpressionConstant4Vector if isinstance(value, tuple) else unreal.MaterialExpressionConstant
        expr = unreal.MaterialEditingLibrary.create_material_expression(material, cls, -500, index * 180)
        if isinstance(value, tuple):
            expr.set_editor_property("constant", unreal.LinearColor(*value))
        else:
            expr.set_editor_property("r", value)
        unreal.MaterialEditingLibrary.connect_material_property(expr, "", prop)
    unreal.MaterialEditingLibrary.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(material.get_path_name(), only_if_is_dirty=False)
    return material


def _save_targets(targets):
    for _actor, _component, mesh in targets.values():
        unreal.EditorAssetLibrary.save_asset(mesh.get_path_name(), only_if_is_dirty=False)
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("Could not save the main Enclave level")


if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The landing material pass is connected to the wrong project")
if unreal.EditorLevelLibrary.get_editor_world().get_path_name().split(".", 1)[0] != EXPECTED_MAP:
    raise RuntimeError("The landing material pass requires the main Enclave level")
if MODE not in {"dry_run", "apply", "rollback"}:
    raise RuntimeError("Invalid fixed landing material mode")

manifest_path, families = _load_manifest()
targets = _find_targets()
receipt_dir = os.path.realpath(os.path.join(unreal.Paths.project_saved_dir(), "MCPStudio/evidence"))
os.makedirs(receipt_dir, exist_ok=True)
receipt_path = os.path.join(receipt_dir, RECEIPT_NAME)
rollback_path = os.path.join(receipt_dir, ROLLBACK_NAME)

if MODE == "dry_run":
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-material-pass/v1",
        "mode": MODE,
        "manifest_path": manifest_path,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "target_actor_guids": [spec["guid"] for spec in TARGETS.values()],
        "structure_families": STRUCTURE_FAMILIES,
        "content_root": OUTPUT_ROOT,
        "receipt_exists": os.path.exists(receipt_path),
    })
elif MODE == "apply":
    if os.path.exists(receipt_path):
        with open(receipt_path, "r", encoding="utf-8") as stream:
            prior = json.load(stream)
        if prior.get("schema") != "mcpstudio.enclave-landing-material-pass-receipt/v1":
            raise RuntimeError("The existing landing material receipt is not trusted")
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-landing-material-pass/v1",
            "mode": MODE,
            "idempotent_replay": True,
            "receipt_path": receipt_path,
            "outputs": prior.get("outputs", {}),
        })
    else:
        if unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False):
            raise RuntimeError("The landing material namespace contains unreceipted assets")
        before = {
            key: {
                "mesh_materials": _material_paths(mesh),
                "component_overrides": _override_paths(component),
            }
            for key, (_actor, component, mesh) in targets.items()
        }
        unreal.EditorAssetLibrary.make_directory(TEXTURE_ROOT)
        unreal.EditorAssetLibrary.make_directory(MATERIAL_ROOT)
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        materials = {}
        texture_paths = {}
        for family, config in FAMILY_CONFIG.items():
            by_kind = {item["kind"]: item for item in families[family]["channels"]}
            textures = {kind: _import_texture(asset_tools, family, kind, item) for kind, item in by_kind.items()}
            materials[family] = _create_pbr_material(asset_tools, family, config, textures)
            texture_paths[family] = {kind: texture.get_path_name() for kind, texture in textures.items()}
        materials["glass"] = _create_constant_material(asset_tools, "glass")
        materials["emissive"] = _create_constant_material(asset_tools, "emissive")

        structure_mesh = targets["structure"][2]
        if len(structure_mesh.get_editor_property("static_materials")) != len(STRUCTURE_FAMILIES):
            raise RuntimeError("Landing structure material slot count changed")
        for index, family in enumerate(STRUCTURE_FAMILIES):
            structure_mesh.set_material(index, materials[family])
        targets["floor"][2].set_material(0, materials["grassland"])
        for key in ("door-west", "door-east", "door-north"):
            targets[key][2].set_material(0, materials["metal-door"])
        for _actor, component, _mesh in targets.values():
            component.set_editor_property("override_materials", [])
        _save_targets(targets)

        after = {
            key: {
                "mesh_materials": _material_paths(mesh),
                "component_overrides": _override_paths(component),
            }
            for key, (_actor, component, mesh) in targets.items()
        }
        outputs = {
            "content_root": OUTPUT_ROOT,
            "materials": {key: value.get_path_name() for key, value in materials.items()},
            "textures": texture_paths,
            "actor_guids": {key: spec["guid"] for key, spec in TARGETS.items()},
            "structure_slot_families": STRUCTURE_FAMILIES,
            "before": before,
            "after": after,
        }
        receipt = {
            "schema": "mcpstudio.enclave-landing-material-pass-receipt/v1",
            "manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "target_map": EXPECTED_MAP,
            "outputs": outputs,
        }
        data = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(receipt_path, "xb") as stream:
            stream.write(data)
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-landing-material-pass/v1",
            "mode": MODE,
            "idempotent_replay": False,
            "receipt_path": receipt_path,
            "receipt_sha256": hashlib.sha256(data).hexdigest(),
            "outputs": outputs,
        })
else:
    if not os.path.exists(receipt_path):
        raise RuntimeError("Landing material receipt is required before rollback")
    with open(receipt_path, "r", encoding="utf-8") as stream:
        receipt = json.load(stream)
    if receipt.get("schema") != "mcpstudio.enclave-landing-material-pass-receipt/v1":
        raise RuntimeError("Landing material receipt failed rollback validation")
    before = receipt["outputs"]["before"]
    for key, (_actor, component, mesh) in targets.items():
        for index, material_path in enumerate(before[key]["mesh_materials"]):
            mesh.set_material(index, unreal.load_asset(material_path) if material_path else None)
        component.set_editor_property(
            "override_materials",
            [unreal.load_asset(path) if path else None for path in before[key]["component_overrides"]],
        )
    _save_targets(targets)
    if not unreal.EditorAssetLibrary.delete_directory(OUTPUT_ROOT):
        raise RuntimeError("Could not delete the landing material namespace")
    os.replace(receipt_path, rollback_path)
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-material-pass/v1",
        "mode": MODE,
        "rollback_path": rollback_path,
        "restored": before,
    })
