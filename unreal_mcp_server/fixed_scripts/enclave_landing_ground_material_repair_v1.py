import hashlib
import json
import os
import unreal


MODE = globals().get("MCPSTUDIO_MODE", "dry_run")
EXPECTED_PROJECT = "EnclaveProject"
EXPECTED_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
MATERIAL_PASS_RECEIPT_SHA256 = "785536e9d9e5ba542a8a7dc6b2bc338100f41787d6188a62dd4ca918459060f4"
GROUND_REFINE_RECEIPT_SHA256 = "0a33afab2f32dab240967763bffe2058e640341e86379c3ee7902d0c7ef6c926"
SOURCE_MATERIAL = "/Game/MCPStudio/Enclave/LandingMaterials/v1/Materials/M_Enclave_Landing_Grassland_v1.M_Enclave_Landing_Grassland_v1"
OUTPUT_ROOT = "/Game/MCPStudio/Enclave/LandingMaterials/v2"
OUTPUT_PACKAGE = OUTPUT_ROOT + "/Materials/M_Enclave_Landing_Grassland_PhysicalScale_v2"
OUTPUT_MATERIAL = OUTPUT_PACKAGE + ".M_Enclave_Landing_Grassland_PhysicalScale_v2"
TARGET_U_TILING = 40.0
TARGET_V_TILING = 30.0
RECEIPT_NAME = "enclave_landing_ground_material_repair_v1_receipt.json"
ROLLBACK_NAME = "enclave_landing_ground_material_repair_v1_rollback.json"
RECOVERABLE_FAILURE_SAVE_ASSET_NAME = "enclave_landing_ground_material_repair_v1_deferred_failure_superseded_save_asset_false.json"
RECOVERABLE_FAILURE_SAVE_ASSET_SHA256 = "fa2e1c26669b00b609887ef64e3023bfa6e6f38c94a452da4fc5e8ba3964a4db"
RECOVERABLE_FAILURE_SAVE_LOADED_ASSET_NAME = "enclave_landing_ground_material_repair_v1_deferred_failure_superseded_save_loaded_asset_false.json"
RECOVERABLE_FAILURE_SAVE_LOADED_ASSET_SHA256 = "3cd641948b132492a1c35828557732f974008e9abecfc0ffaddba3ddea93ec97"
RECOVERABLE_FAILURE_DIRTY_FLAG_NAME = "enclave_landing_ground_material_repair_v1_deferred_failure_superseded_dirty_flag_api.json"
RECOVERABLE_FAILURE_DIRTY_FLAG_SHA256 = "1431044831aa6748dc371ffd938c5c16d8e9c45a80aa0869d0f763978fd5a275"
RECOVERABLE_FAILURE_LEVEL_SAVE_NAME = "enclave_landing_ground_material_repair_v1_deferred_failure_superseded_level_save_false.json"
RECOVERABLE_FAILURE_LEVEL_SAVE_SHA256 = "13a540ca944d3585c184c7f6c2933e1d384185ff59526e9f7d19886db50e4b41"
TEXTURES = {
    "base-color": "/Game/MCPStudio/Enclave/LandingMaterials/v1/Textures/T_Enclave_Landing_Grassland_Basecolor_v1",
    "normal": "/Game/MCPStudio/Enclave/LandingMaterials/v1/Textures/T_Enclave_Landing_Grassland_Normal_v1",
    "roughness": "/Game/MCPStudio/Enclave/LandingMaterials/v1/Textures/T_Enclave_Landing_Grassland_Roughness_v1",
    "ambient-occlusion": "/Game/MCPStudio/Enclave/LandingMaterials/v1/Textures/T_Enclave_Landing_Grassland_Ambientocclusion_v1",
}
TARGETS = {
    "ground-support": {
        "actor_guid": "6E7C5DEE47582C880B7983A5A807685F",
        "mesh": "/Game/MCPStudio/Enclave/LandingGround/v1/Meshes/SM_SM_LandingGrassGround_80x60m_v1.SM_SM_LandingGrassGround_80x60m_v1",
        "slot": 0,
    },
}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _evidence_path(name):
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    root = os.path.realpath(os.path.join(saved, "MCPStudio", "evidence"))
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, name)


def _require_receipt(name, expected_sha256):
    path = _evidence_path(name)
    if not os.path.isfile(path) or _sha256(path) != expected_sha256:
        raise RuntimeError("A landing ground-material prerequisite receipt is missing or drifted")
    return path


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
        matches = [actor for actor in actors if _guid(actor) == spec["actor_guid"]]
        if len(matches) != 1:
            raise RuntimeError("An exact landing ground-material actor is missing or ambiguous")
        component = matches[0].get_component_by_class(unreal.StaticMeshComponent)
        if component is None or component.static_mesh is None:
            raise RuntimeError("An exact landing ground-material actor has no mesh")
        if component.static_mesh.get_path_name() != spec["mesh"]:
            raise RuntimeError("An exact landing ground-material mesh identity drifted")
        result[key] = (matches[0], component, component.static_mesh)
    return result


def _material_path(mesh, slot):
    materials = mesh.get_editor_property("static_materials")
    if slot < 0 or slot >= len(materials):
        raise RuntimeError("An exact landing ground-material slot is unavailable")
    material = mesh.get_material(slot)
    return material.get_path_name() if material is not None else ""


def _snapshot(targets):
    return {
        key: {
            "actor_guid": TARGETS[key]["actor_guid"],
            "mesh": mesh.get_path_name(),
            "slot": TARGETS[key]["slot"],
            "mesh_material": _material_path(mesh, TARGETS[key]["slot"]),
            "component_overrides": [
                material.get_path_name() if material is not None else ""
                for material in component.get_editor_property("override_materials")
            ],
        }
        for key, (_actor, component, mesh) in targets.items()
    }


def _is_source_state(snapshot):
    return set(snapshot) == set(TARGETS) and all(
        item["actor_guid"] == TARGETS[key]["actor_guid"]
        and item["mesh"] == TARGETS[key]["mesh"]
        and item["slot"] == TARGETS[key]["slot"]
        and item["mesh_material"] == SOURCE_MATERIAL
        and item["component_overrides"] == []
        for key, item in snapshot.items()
    )


def _is_after_state(snapshot):
    return set(snapshot) == set(TARGETS) and all(
        item["actor_guid"] == TARGETS[key]["actor_guid"]
        and item["mesh"] == TARGETS[key]["mesh"]
        and item["slot"] == TARGETS[key]["slot"]
        and item["mesh_material"] == SOURCE_MATERIAL
        and item["component_overrides"] == [OUTPUT_MATERIAL]
        for key, item in snapshot.items()
    )


def _is_partial_mesh_state(snapshot):
    return set(snapshot) == set(TARGETS) and all(
        item["actor_guid"] == TARGETS[key]["actor_guid"]
        and item["mesh"] == TARGETS[key]["mesh"]
        and item["slot"] == TARGETS[key]["slot"]
        and item["mesh_material"] == OUTPUT_MATERIAL
        and item["component_overrides"] == []
        for key, item in snapshot.items()
    )


def _connect_sample(material, texture, texcoord, x, y, prop, output="RGB"):
    sample = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionTextureSample, x, y
    )
    sample.set_editor_property("texture", texture)
    unreal.MaterialEditingLibrary.connect_material_expressions(
        texcoord, "", sample, "Coordinates"
    )
    if not unreal.MaterialEditingLibrary.connect_material_property(sample, output, prop):
        raise RuntimeError("Could not connect the physical-scale grass material")


def _create_material():
    if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_PACKAGE):
        raise RuntimeError("The physical-scale grass output exists without a trusted receipt")
    textures = {key: unreal.load_asset(path) for key, path in TEXTURES.items()}
    if any(texture is None or not isinstance(texture, unreal.Texture2D) for texture in textures.values()):
        raise RuntimeError("A fixed landing grass texture is unavailable")
    unreal.EditorAssetLibrary.make_directory(OUTPUT_ROOT + "/Materials")
    material = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_Enclave_Landing_Grassland_PhysicalScale_v2",
        OUTPUT_ROOT + "/Materials",
        unreal.Material,
        unreal.MaterialFactoryNew(),
    )
    if material is None:
        raise RuntimeError("Could not create the physical-scale grass material")
    texcoord = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionTextureCoordinate, -900, 0
    )
    texcoord.set_editor_property("u_tiling", TARGET_U_TILING)
    texcoord.set_editor_property("v_tiling", TARGET_V_TILING)
    _connect_sample(material, textures["base-color"], texcoord, -650, -260, unreal.MaterialProperty.MP_BASE_COLOR)
    _connect_sample(material, textures["normal"], texcoord, -650, -40, unreal.MaterialProperty.MP_NORMAL)
    _connect_sample(material, textures["roughness"], texcoord, -650, 180, unreal.MaterialProperty.MP_ROUGHNESS, "R")
    _connect_sample(material, textures["ambient-occlusion"], texcoord, -650, 400, unreal.MaterialProperty.MP_AMBIENT_OCCLUSION, "R")
    metallic = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionConstant, -400, 620
    )
    metallic.set_editor_property("r", 0.0)
    unreal.MaterialEditingLibrary.connect_material_property(
        metallic, "", unreal.MaterialProperty.MP_METALLIC
    )
    unreal.MaterialEditingLibrary.recompile_material(material)
    if not unreal.EditorAssetLibrary.save_asset(OUTPUT_PACKAGE, only_if_is_dirty=False):
        raise RuntimeError("Could not save the physical-scale grass material")
    return material


def _assign_overrides(targets, material):
    for key, (_actor, component, _mesh) in targets.items():
        component.set_material(TARGETS[key]["slot"], material)
    _save_actor_packages(targets)


def _save_actor_packages(targets):
    packages = []
    names = []
    for actor, _component, _mesh in targets.values():
        package = actor.get_outermost()
        if package is None:
            raise RuntimeError("Could not resolve the exact landing grass actor package")
        name = package.get_path_name()
        if name not in names:
            names.append(name)
            packages.append(package)
    if not packages or not unreal.EditorLoadingAndSavingUtils.save_packages(packages, False):
        raise RuntimeError("Could not save the exact landing grass actor override")


def _clear_overrides(targets):
    for _actor, component, _mesh in targets.values():
        component.set_editor_property("override_materials", [])
    _save_actor_packages(targets)


def _before_from_partial(snapshot):
    before = json.loads(json.dumps(snapshot))
    for item in before.values():
        item["mesh_material"] = SOURCE_MATERIAL
        item["component_overrides"] = []
    return before


if MODE not in {"dry_run", "apply", "rollback"}:
    raise RuntimeError("Invalid landing ground-material repair mode")
if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The landing ground-material repair is connected to the wrong project")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not world.get_path_name().startswith(EXPECTED_MAP + "."):
    raise RuntimeError("The landing ground-material repair requires the Enclave main level")

material_receipt = _require_receipt(
    "enclave_landing_material_pass_v1_receipt.json", MATERIAL_PASS_RECEIPT_SHA256
)
ground_receipt = _require_receipt(
    "enclave_landing_ground_refine_v1_receipt.json", GROUND_REFINE_RECEIPT_SHA256
)
targets = _find_targets()
current = _snapshot(targets)
receipt_path = _evidence_path(RECEIPT_NAME)
recoverable_failure_save_asset_path = _evidence_path(RECOVERABLE_FAILURE_SAVE_ASSET_NAME)
recoverable_failure_save_loaded_asset_path = _evidence_path(
    RECOVERABLE_FAILURE_SAVE_LOADED_ASSET_NAME
)
recoverable_failure_dirty_flag_path = _evidence_path(
    RECOVERABLE_FAILURE_DIRTY_FLAG_NAME
)
recoverable_failure_level_save_path = _evidence_path(
    RECOVERABLE_FAILURE_LEVEL_SAVE_NAME
)
recoverable_evidence = (
    os.path.isfile(recoverable_failure_save_asset_path)
    and _sha256(recoverable_failure_save_asset_path)
    == RECOVERABLE_FAILURE_SAVE_ASSET_SHA256
    and os.path.isfile(recoverable_failure_save_loaded_asset_path)
    and _sha256(recoverable_failure_save_loaded_asset_path)
    == RECOVERABLE_FAILURE_SAVE_LOADED_ASSET_SHA256
    and os.path.isfile(recoverable_failure_dirty_flag_path)
    and _sha256(recoverable_failure_dirty_flag_path)
    == RECOVERABLE_FAILURE_DIRTY_FLAG_SHA256
    and os.path.isfile(recoverable_failure_level_save_path)
    and _sha256(recoverable_failure_level_save_path)
    == RECOVERABLE_FAILURE_LEVEL_SAVE_SHA256
    and unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_PACKAGE)
)
recoverable_partial = recoverable_evidence and _is_partial_mesh_state(current)
recoverable_source = recoverable_evidence and _is_source_state(current)
recoverable_after = recoverable_evidence and _is_after_state(current)

if MODE == "dry_run":
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-ground-material-repair/v1",
        "mode": MODE,
        "will_mutate": False,
        "eligible_to_apply": (
            (
                _is_source_state(current)
                and not unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_PACKAGE)
            )
            or (
                os.path.isfile(receipt_path)
                and _is_after_state(current)
                and unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_PACKAGE)
            )
            or recoverable_partial
            or recoverable_source
            or recoverable_after
        ),
        "current": current,
        "planned": {
            "source_material": SOURCE_MATERIAL,
            "output_material": OUTPUT_MATERIAL,
            "u_tiling": TARGET_U_TILING,
            "v_tiling": TARGET_V_TILING,
            "physical_ground_meters": [80.0, 60.0],
            "nominal_texture_repeat_meters": 2.0,
            "target_count": len(TARGETS),
            "recoverable_partial": recoverable_partial,
            "recoverable_source": recoverable_source,
            "recoverable_after": recoverable_after,
        },
        "receipt_path": receipt_path,
        "prerequisites": {
            "material_pass_receipt": material_receipt,
            "ground_refine_receipt": ground_receipt,
        },
    })

elif MODE == "apply":
    if os.path.isfile(receipt_path):
        with open(receipt_path, "r", encoding="utf-8") as stream:
            receipt = json.load(stream)
        if (
            receipt.get("schema") != "mcpstudio.enclave-landing-ground-material-repair-receipt/v1"
            or receipt.get("target_map") != EXPECTED_MAP
            or not _is_after_state(current)
            or not unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_PACKAGE)
        ):
            raise RuntimeError("The ground-material repair receipt or material state drifted")
        idempotent = True
    else:
        recovered_failure = None
        if recoverable_after:
            before = json.loads(json.dumps(current))
            for item in before.values():
                item["component_overrides"] = []
            _save_actor_packages(targets)
            recovered_failure = [
                {"path": recoverable_failure_save_asset_path, "sha256": RECOVERABLE_FAILURE_SAVE_ASSET_SHA256},
                {"path": recoverable_failure_save_loaded_asset_path, "sha256": RECOVERABLE_FAILURE_SAVE_LOADED_ASSET_SHA256},
                {"path": recoverable_failure_dirty_flag_path, "sha256": RECOVERABLE_FAILURE_DIRTY_FLAG_SHA256},
                {"path": recoverable_failure_level_save_path, "sha256": RECOVERABLE_FAILURE_LEVEL_SAVE_SHA256},
            ]
        elif recoverable_partial:
            before = _before_from_partial(current)
            source_material = unreal.load_asset(SOURCE_MATERIAL)
            material = unreal.load_asset(OUTPUT_MATERIAL)
            if source_material is None or material is None:
                raise RuntimeError("A recovery material is unavailable")
            for key, (_actor, _component, mesh) in targets.items():
                mesh.set_material(TARGETS[key]["slot"], source_material)
            _assign_overrides(targets, material)
            recovered_failure = [
                {
                    "path": recoverable_failure_save_asset_path,
                    "sha256": RECOVERABLE_FAILURE_SAVE_ASSET_SHA256,
                },
                {
                    "path": recoverable_failure_save_loaded_asset_path,
                    "sha256": RECOVERABLE_FAILURE_SAVE_LOADED_ASSET_SHA256,
                },
                {
                    "path": recoverable_failure_dirty_flag_path,
                    "sha256": RECOVERABLE_FAILURE_DIRTY_FLAG_SHA256,
                },
                {
                    "path": recoverable_failure_level_save_path,
                    "sha256": RECOVERABLE_FAILURE_LEVEL_SAVE_SHA256,
                },
            ]
        elif recoverable_source:
            before = current
            material = unreal.load_asset(OUTPUT_MATERIAL)
            if material is None:
                raise RuntimeError("The recovered physical-scale material is unavailable")
            _assign_overrides(targets, material)
            recovered_failure = [
                {
                    "path": recoverable_failure_save_asset_path,
                    "sha256": RECOVERABLE_FAILURE_SAVE_ASSET_SHA256,
                },
                {
                    "path": recoverable_failure_save_loaded_asset_path,
                    "sha256": RECOVERABLE_FAILURE_SAVE_LOADED_ASSET_SHA256,
                },
                {
                    "path": recoverable_failure_dirty_flag_path,
                    "sha256": RECOVERABLE_FAILURE_DIRTY_FLAG_SHA256,
                },
                {
                    "path": recoverable_failure_level_save_path,
                    "sha256": RECOVERABLE_FAILURE_LEVEL_SAVE_SHA256,
                },
            ]
        else:
            if not _is_source_state(current):
                raise RuntimeError("The audited landing grass assignments no longer match the original")
            before = current
            material = _create_material()
            _assign_overrides(targets, material)
        after = _snapshot(targets)
        if not _is_after_state(after):
            _clear_overrides(targets)
            raise RuntimeError("The landing grass material repair did not verify")
        receipt = {
            "schema": "mcpstudio.enclave-landing-ground-material-repair-receipt/v1",
            "target_map": EXPECTED_MAP,
            "material_pass_receipt_sha256": MATERIAL_PASS_RECEIPT_SHA256,
            "ground_refine_receipt_sha256": GROUND_REFINE_RECEIPT_SHA256,
            "before": before,
            "after": after,
            "output_material": OUTPUT_MATERIAL,
            "textures": TEXTURES,
            "physical_basis": {
                "ground_meters": [80.0, 60.0],
                "u_tiling": TARGET_U_TILING,
                "v_tiling": TARGET_V_TILING,
                "nominal_texture_repeat_meters": 2.0,
            },
            "recovered_failure": recovered_failure,
        }
        receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(receipt_path, "xb") as stream:
            stream.write(receipt_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        idempotent = False
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-ground-material-repair/v1",
        "mode": MODE,
        "idempotent_replay": idempotent,
        "receipt_path": receipt_path,
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "before": receipt["before"],
        "after": receipt["after"],
        "output_material": receipt["output_material"],
    })

else:
    if not os.path.isfile(receipt_path):
        raise RuntimeError("The ground-material repair receipt is required for rollback")
    with open(receipt_path, "r", encoding="utf-8") as stream:
        receipt = json.load(stream)
    if (
        receipt.get("schema") != "mcpstudio.enclave-landing-ground-material-repair-receipt/v1"
        or receipt.get("target_map") != EXPECTED_MAP
        or not _is_after_state(current)
    ):
        raise RuntimeError("The grass material assignments are not eligible for exact rollback")
    _clear_overrides(targets)
    restored = _snapshot(targets)
    if not _is_source_state(restored):
        raise RuntimeError("The ground-material rollback did not restore the original assignments")
    rollback_path = _evidence_path(ROLLBACK_NAME)
    rollback = {
        "schema": "mcpstudio.enclave-landing-ground-material-repair-rollback/v1",
        "target_map": EXPECTED_MAP,
        "restored": restored,
        "retained_unreferenced_output_material": OUTPUT_MATERIAL,
        "source_receipt_sha256": _sha256(receipt_path),
    }
    with open(rollback_path, "x", encoding="utf-8") as stream:
        json.dump(rollback, stream, indent=2, sort_keys=True)
        stream.write("\n")
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-ground-material-repair/v1",
        "mode": MODE,
        "idempotent_replay": False,
        "rollback_path": rollback_path,
        "restored": restored,
    })
