import hashlib
import json
import os
import unreal


MODE = globals().get("MCPSTUDIO_MODE", "dry_run")
EXPECTED_PROJECT = "EnclaveProject"
EXPECTED_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
MATERIAL_RECEIPT_RELATIVE = "MCPStudio/evidence/enclave_landing_material_pass_v1_receipt.json"
MATERIAL_RECEIPT_SHA256 = "785536e9d9e5ba542a8a7dc6b2bc338100f41787d6188a62dd4ca918459060f4"
OUTPUT_ROOT = "/Game/MCPStudio/Enclave/LandingGround/v1"
MESH_ROOT = OUTPUT_ROOT + "/Meshes"
CURRENT_FLOOR_MESH = "/Game/MCPStudio/Enclave/LandingScaleBake/v1/Meshes/SM_LandingFloor_ScaleBaked_v1.SM_LandingFloor_ScaleBaked_v1"
BASE_FLOOR_MESH = "/Engine/MapTemplates/SM_Template_Map_Floor.SM_Template_Map_Floor"
STRUCTURE_MESH = "/Game/MCPStudio/Enclave/LandingScaleBake/v1/Meshes/SM_LandingStructure_m13aa_01a_ScaleBaked_v1.SM_LandingStructure_m13aa_01a_ScaleBaked_v1"
STONE_CLEAN = "/Game/MCPStudio/Enclave/LandingMaterials/v1/Materials/M_Enclave_Landing_StoneClean_v1.M_Enclave_Landing_StoneClean_v1"
STONE_WEATHERED = "/Game/MCPStudio/Enclave/LandingMaterials/v1/Materials/M_Enclave_Landing_StoneWeathered_v1.M_Enclave_Landing_StoneWeathered_v1"
PAVING_PRIMARY = "/Game/MCPStudio/Enclave/LandingMaterials/v1/Materials/M_Enclave_Landing_PavingPrimary_v1.M_Enclave_Landing_PavingPrimary_v1"
PAVING_SECONDARY = "/Game/MCPStudio/Enclave/LandingMaterials/v1/Materials/M_Enclave_Landing_PavingSecondary_v1.M_Enclave_Landing_PavingSecondary_v1"
GRASSLAND = "/Game/MCPStudio/Enclave/LandingMaterials/v1/Materials/M_Enclave_Landing_Grassland_v1.M_Enclave_Landing_Grassland_v1"
STRUCTURE_GUID = "39A96FF046720C0C936788BC9A08FBF1"
FLOOR_GUID = "04B40FE441C580AE34D06B94E7FAFBF2"
EBON_GUID = "B618B798424015C10441568564ACA29B"
RECEIPT_NAME = "enclave_landing_ground_refine_v1_receipt.json"
ROLLBACK_NAME = "enclave_landing_ground_refine_v1_rollback.json"

SPAWN_SPECS = (
    {
        "key": "landing-pad",
        "label": "MCP_LandingPad_Production_v1",
        "mesh_name": "SM_LandingPad_40m_v1",
        "build_multiplier": (4.0, 4.0, 1.0),
        "location": (-4989.045, 240.217, -5.0),
        "material": PAVING_PRIMARY,
        "expected_extent": (2000.0, 2000.0, 25.0),
    },
    {
        "key": "grass-support",
        "label": "MCP_LandingGrassGround_80x60m_v1",
        "mesh_name": "SM_LandingGrassGround_80x60m_v1",
        "build_multiplier": (8.0, 6.0, 1.0),
        "location": (-3000.0, 500.0, -20.0),
        "material": GRASSLAND,
        "expected_extent": (4000.0, 3000.0, 25.0),
    },
)


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


def _close(left, right, tolerance=0.01):
    return abs(float(left) - float(right)) <= tolerance


def _close_vector(value, expected, tolerance=0.01):
    return all(_close(component, target, tolerance) for component, target in zip((value.x, value.y, value.z), expected))


def _bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return {
        "origin": [float(origin.x), float(origin.y), float(origin.z)],
        "extent": [float(extent.x), float(extent.y), float(extent.z)],
    }


def _find_actor(guid, label):
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    matches = [actor for actor in actors if _guid(actor) == guid]
    if len(matches) != 1 or matches[0].get_actor_label() != label:
        raise RuntimeError("Landing ground actor identity mismatch: " + label)
    return matches[0]


def _component(actor):
    result = actor.get_component_by_class(unreal.StaticMeshComponent)
    if result is None or result.static_mesh is None:
        raise RuntimeError("Landing ground target has no static mesh: " + actor.get_actor_label())
    return result


def _load_material(path):
    material = unreal.load_asset(path)
    if material is None or not isinstance(material, unreal.MaterialInterface):
        raise RuntimeError("Landing ground material is unavailable: " + path)
    return material


def _asset_path(spec):
    return MESH_ROOT + "/" + spec["mesh_name"]


def _object_path(spec):
    return _asset_path(spec) + "." + spec["mesh_name"]


def _package_path(object_path):
    return object_path.split(".", 1)[0]


def _is_recoverable_partial(actor):
    labels = {spec["label"] for spec in SPAWN_SPECS}
    tags = {str(value) for value in actor.tags}
    return actor.get_actor_label() in labels and "MCPStudioLandingGroundV1" in tags


def _save_actor_packages(actors):
    packages = []
    names = []
    for actor in actors:
        package = actor.get_outermost()
        if package is None:
            raise RuntimeError("Could not resolve landing ground actor package")
        packages.append(package)
        names.append(package.get_path_name())
    if packages and not unreal.EditorLoadingAndSavingUtils.save_packages(packages, False):
        raise RuntimeError("Could not save landing ground external actor packages")
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("Could not save the Enclave main level")
    return names


def _receipt_path(name):
    root = os.path.realpath(os.path.join(unreal.Paths.project_saved_dir(), "MCPStudio/evidence"))
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, name)


if MODE not in {"dry_run", "apply", "rollback"}:
    raise RuntimeError("Invalid fixed landing ground mode")
if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The landing ground refinement is connected to the wrong project")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not world.get_path_name().startswith(EXPECTED_MAP + "."):
    raise RuntimeError("The landing ground refinement requires the main Enclave level")

material_receipt = os.path.realpath(os.path.join(unreal.Paths.project_saved_dir(), MATERIAL_RECEIPT_RELATIVE))
if _sha256(material_receipt) != MATERIAL_RECEIPT_SHA256:
    raise RuntimeError("The accepted landing material receipt changed")

structure_actor = _find_actor(STRUCTURE_GUID, "m13aa_01a2")
floor_actor = _find_actor(FLOOR_GUID, "Floor")
ebon_actor = _find_actor(EBON_GUID, "ebon_01")
structure_component = _component(structure_actor)
floor_component = _component(floor_actor)
ebon_component = _component(ebon_actor)
if structure_component.static_mesh.get_path_name() != STRUCTURE_MESH:
    raise RuntimeError("Landing structure mesh drifted")
if floor_component.static_mesh.get_path_name() != CURRENT_FLOOR_MESH:
    raise RuntimeError("Landing floor mesh drifted")
if not _close_vector(structure_actor.get_actor_scale3d(), (1.0, 1.0, 1.0)):
    raise RuntimeError("Landing structure is no longer unit scale")
if not _close_vector(floor_actor.get_actor_scale3d(), (1.0, 1.0, 1.0)):
    raise RuntimeError("Landing floor is no longer unit scale")
if not _close_vector(ebon_actor.get_actor_scale3d(), (1.0, 1.0, 1.0)):
    raise RuntimeError("Ebon Hawk is no longer unit scale")

stone_clean = _load_material(STONE_CLEAN)
stone_weathered = _load_material(STONE_WEATHERED)
paving_primary = _load_material(PAVING_PRIMARY)
paving_secondary = _load_material(PAVING_SECONDARY)
grassland = _load_material(GRASSLAND)
if structure_component.static_mesh.get_material(5).get_path_name() not in {STONE_CLEAN, STONE_WEATHERED}:
    raise RuntimeError("Landing wall material slot drifted")
if floor_component.static_mesh.get_material(0).get_path_name() not in {GRASSLAND, PAVING_SECONDARY}:
    raise RuntimeError("Landing floor material slot drifted")

receipt_path = _receipt_path(RECEIPT_NAME)
rollback_path = _receipt_path(ROLLBACK_NAME)

if MODE == "dry_run":
    collisions = list(unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False) or [])
    all_actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    recoverable_partial_labels = sorted(actor.get_actor_label() for actor in all_actors if _is_recoverable_partial(actor))
    labels = {actor.get_actor_label() for actor in all_actors if not _is_recoverable_partial(actor)}
    label_collisions = sorted(spec["label"] for spec in SPAWN_SPECS if spec["label"] in labels)
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-ground-refine/v1",
        "mode": MODE,
        "will_mutate": False,
        "content_root": OUTPUT_ROOT,
        "current_floor_mesh": CURRENT_FLOOR_MESH,
        "base_floor_mesh": BASE_FLOOR_MESH,
        "spawn_specs": SPAWN_SPECS,
        "asset_collisions": collisions,
        "label_collisions": label_collisions,
        "recoverable_partial_labels": recoverable_partial_labels,
        "eligible_to_apply": not collisions and not label_collisions and not os.path.exists(receipt_path),
    })

elif MODE == "apply":
    if os.path.exists(receipt_path):
        with open(receipt_path, "r", encoding="utf-8") as stream:
            receipt = json.load(stream)
        if receipt.get("schema") != "mcpstudio.enclave-landing-ground-refine-receipt/v1":
            raise RuntimeError("The landing ground receipt is not trusted")
        actors_by_guid = {
            _guid(actor): actor
            for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        }
        for output in receipt.get("outputs", {}).get("spawned", []):
            actor = actors_by_guid.get(output.get("actor_guid"))
            if actor is None or actor.get_actor_label() != output.get("label"):
                raise RuntimeError("A persisted landing ground actor is unavailable")
            if not _close_vector(actor.get_actor_scale3d(), (1.0, 1.0, 1.0)):
                raise RuntimeError("A persisted landing ground actor lost unit scale")
            if _component(actor).static_mesh.get_path_name() != output.get("mesh"):
                raise RuntimeError("A persisted landing ground actor mesh drifted")
        if structure_component.static_mesh.get_material(5).get_path_name() != STONE_CLEAN:
            raise RuntimeError("The refined landing wall material drifted")
        if floor_component.static_mesh.get_material(0).get_path_name() != PAVING_SECONDARY:
            raise RuntimeError("The refined landing detail floor material drifted")
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-landing-ground-refine/v1",
            "mode": MODE,
            "idempotent_replay": True,
            "receipt_path": receipt_path,
            "outputs": receipt.get("outputs", {}),
        })
    else:
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        for actor in list(actor_subsystem.get_all_level_actors()):
            if _is_recoverable_partial(actor):
                actor_subsystem.destroy_actor(actor)
        if unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False):
            raise RuntimeError("The exclusive landing ground namespace contains unreceipted assets")
        labels = {actor.get_actor_label() for actor in actor_subsystem.get_all_level_actors()}
        if any(spec["label"] in labels for spec in SPAWN_SPECS):
            raise RuntimeError("A landing ground actor label already exists")
        source_floor = unreal.load_asset(BASE_FLOOR_MESH)
        if source_floor is None or not isinstance(source_floor, unreal.StaticMesh):
            raise RuntimeError("The scale-baked landing floor source is unavailable")
        spawned = []
        temporary = []
        previous_wall = structure_component.static_mesh.get_material(5).get_path_name()
        previous_floor = floor_component.static_mesh.get_material(0).get_path_name()
        try:
            unreal.EditorAssetLibrary.make_directory(MESH_ROOT)
            for spec in SPAWN_SPECS:
                actor = actor_subsystem.spawn_actor_from_object(
                    source_floor,
                    unreal.Vector(*spec["location"]),
                    unreal.Rotator(0.0, 0.0, 0.0),
                )
                if actor is None:
                    raise RuntimeError("Could not spawn landing ground actor: " + spec["label"])
                temporary.append(actor)
                actor.set_actor_label(spec["label"] + "_ScaleBakeSource", mark_dirty=True)
                actor.set_actor_scale3d(unreal.Vector(*spec["build_multiplier"]))
                material = paving_primary if spec["material"] == PAVING_PRIMARY else grassland
                _component(actor).set_material(0, material)
                before_bake = _bounds(actor)["extent"]
                for observed, expected in zip(before_bake, spec["expected_extent"]):
                    if abs(observed - expected) > max(5.0, expected * 0.01):
                        raise RuntimeError(
                            "Landing ground staged bounds mismatched: "
                            + spec["label"]
                            + " observed="
                            + json.dumps(before_bake)
                            + " expected="
                            + json.dumps(list(spec["expected_extent"]))
                        )
                options = unreal.MergeStaticMeshActorsOptions()
                options.set_editor_property("base_package_name", _asset_path(spec))
                options.set_editor_property("destroy_source_actors", True)
                options.set_editor_property("spawn_merged_actor", True)
                options.set_editor_property("new_actor_label", spec["label"])
                merged = unreal.EditorLevelLibrary.merge_static_mesh_actors([actor], options)
                if merged is None:
                    raise RuntimeError("Could not merge the landing ground scale bake: " + spec["label"])
                temporary.remove(actor)
                merged.set_actor_label(spec["label"], mark_dirty=True)
                merged.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
                merged.tags = [unreal.Name("MCPStudioLandingGroundV1")]
                spawned.append((spec, merged))
                merged_mesh_path = _component(merged).static_mesh.get_path_name()
                if not merged_mesh_path.startswith(MESH_ROOT + "/"):
                    raise RuntimeError(
                        "Landing ground merge escaped its exclusive namespace: "
                        + spec["label"]
                        + " mesh="
                        + merged_mesh_path
                    )
                if not unreal.EditorAssetLibrary.save_asset(_package_path(merged_mesh_path), only_if_is_dirty=False):
                    raise RuntimeError("Could not persist landing ground mesh: " + spec["label"])
                actual = _bounds(merged)["extent"]
                for observed, expected in zip(actual, spec["expected_extent"]):
                    if abs(observed - expected) > max(5.0, expected * 0.01):
                        raise RuntimeError(
                            "Landing ground baked bounds mismatched: "
                            + spec["label"]
                            + " observed="
                            + json.dumps(actual)
                            + " expected="
                            + json.dumps(list(spec["expected_extent"]))
                        )
            structure_component.static_mesh.set_material(5, stone_clean)
            floor_component.static_mesh.set_material(0, paving_secondary)
            if not unreal.EditorAssetLibrary.save_asset(_package_path(structure_component.static_mesh.get_path_name()), only_if_is_dirty=False):
                raise RuntimeError("Could not persist the refined landing structure material")
            if not unreal.EditorAssetLibrary.save_asset(_package_path(floor_component.static_mesh.get_path_name()), only_if_is_dirty=False):
                raise RuntimeError("Could not persist the refined landing floor material")
            packages = _save_actor_packages([actor for _spec, actor in spawned] + [structure_actor, floor_actor])
            outputs = {
                "content_root": OUTPUT_ROOT,
                "previous_structure_slot_5": previous_wall,
                "after_structure_slot_5": STONE_CLEAN,
                "previous_floor_slot_0": previous_floor,
                "after_floor_slot_0": PAVING_SECONDARY,
                "actor_packages": packages,
                "spawned": [
                    {
                        "key": spec["key"],
                        "label": spec["label"],
                        "actor_guid": _guid(actor),
                        "mesh": _component(actor).static_mesh.get_path_name(),
                        "location": list(spec["location"]),
                        "scale": [1.0, 1.0, 1.0],
                        "bounds": _bounds(actor),
                        "material": spec["material"],
                    }
                    for spec, actor in spawned
                ],
            }
            receipt = {
                "schema": "mcpstudio.enclave-landing-ground-refine-receipt/v1",
                "target_map": EXPECTED_MAP,
                "material_receipt_sha256": MATERIAL_RECEIPT_SHA256,
                "outputs": outputs,
            }
            receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
            with open(receipt_path, "xb") as stream:
                stream.write(receipt_bytes)
            _result.update({
                "schema": "unreal_mcp_ghost.enclave-landing-ground-refine/v1",
                "mode": MODE,
                "idempotent_replay": False,
                "receipt_path": receipt_path,
                "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                "outputs": outputs,
            })
        except Exception:
            structure_component.static_mesh.set_material(5, stone_weathered if previous_wall == STONE_WEATHERED else stone_clean)
            floor_component.static_mesh.set_material(0, grassland if previous_floor == GRASSLAND else paving_secondary)
            for _spec, actor in reversed(spawned):
                actor_subsystem.destroy_actor(actor)
            for actor in reversed(temporary):
                actor_subsystem.destroy_actor(actor)
            unreal.EditorAssetLibrary.delete_directory(OUTPUT_ROOT)
            unreal.EditorLevelLibrary.save_current_level()
            raise

else:
    if os.path.exists(rollback_path):
        with open(rollback_path, "r", encoding="utf-8") as stream:
            prior = json.load(stream)
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-landing-ground-refine/v1",
            "mode": MODE,
            "idempotent_replay": True,
            "outputs": prior,
        })
    else:
        if not os.path.exists(receipt_path):
            raise RuntimeError("The landing ground receipt is required before rollback")
        with open(receipt_path, "r", encoding="utf-8") as stream:
            receipt = json.load(stream)
        if receipt.get("schema") != "mcpstudio.enclave-landing-ground-refine-receipt/v1":
            raise RuntimeError("The landing ground rollback receipt is not trusted")
        outputs = receipt.get("outputs", {})
        actors_by_guid = {
            _guid(actor): actor
            for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        }
        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        removed = []
        for item in outputs.get("spawned", []):
            actor = actors_by_guid.get(item.get("actor_guid"))
            if actor is None or actor.get_actor_label() != item.get("label"):
                raise RuntimeError("A landing ground rollback actor is unavailable")
            removed.append(item.get("label"))
            actor_subsystem.destroy_actor(actor)
        structure_component.static_mesh.set_material(5, stone_weathered)
        floor_component.static_mesh.set_material(0, grassland)
        if not unreal.EditorAssetLibrary.save_asset(_package_path(structure_component.static_mesh.get_path_name()), only_if_is_dirty=False):
            raise RuntimeError("Could not persist the rolled-back landing structure material")
        if not unreal.EditorAssetLibrary.save_asset(_package_path(floor_component.static_mesh.get_path_name()), only_if_is_dirty=False):
            raise RuntimeError("Could not persist the rolled-back landing floor material")
        unreal.EditorLevelLibrary.save_current_level()
        assets = list(unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False) or [])
        if assets and not unreal.EditorAssetLibrary.delete_directory(OUTPUT_ROOT):
            raise RuntimeError("Could not remove the landing ground content namespace")
        rollback = {
            "rolled_back": True,
            "removed_actor_labels": removed,
            "deleted_assets": assets,
            "restored_structure_slot_5": STONE_WEATHERED,
            "restored_floor_slot_0": GRASSLAND,
        }
        rollback_bytes = (json.dumps(rollback, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(rollback_path, "xb") as stream:
            stream.write(rollback_bytes)
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-landing-ground-refine/v1",
            "mode": MODE,
            "idempotent_replay": False,
            "outputs": rollback,
        })
