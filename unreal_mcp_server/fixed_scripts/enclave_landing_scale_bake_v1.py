import hashlib
import json
import os
import unreal

EXPECTED_PROJECT = "EnclaveProject"
TARGET_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
OUTPUT_ROOT = "/Game/MCPStudio/Enclave/LandingScaleBake/v1"
MESH_ROOT = OUTPUT_ROOT + "/Meshes"
EVIDENCE_RELATIVE = "MCPStudio/evidence"
RECEIPT_FILENAME = "enclave_landing_scale_bake_v1_receipt.json"
PERSISTENCE_FILENAME = "enclave_landing_scale_bake_v1_persistence.json"
ROLLBACK_FILENAME = "enclave_landing_scale_bake_v1_rollback.json"
REPAIR_ROOT = "/Game/MCPStudio/Enclave/LandingScaleBake/v2"
REPAIR_MESH_ROOT = REPAIR_ROOT + "/Meshes"
REPAIR_RECEIPT_FILENAME = "enclave_landing_scale_bake_v2_repair_receipt.json"
UNIT_SCALE = (1.0, 1.0, 1.0)
MODE = globals().get("_MCPSTUDIO_FIXED_MODE", "dry_run")

SPECS = (
    {
        "label": "Floor",
        "guid": "04B40FE441C580AE34D06B94E7FAFBF2",
        "source_mesh": "/Engine/MapTemplates/SM_Template_Map_Floor.SM_Template_Map_Floor",
        "source_file": "C:/Program Files/Epic Games/UE_5.6/Engine/Content/MapTemplates/SM_Template_Map_Floor.uasset",
        "source_sha256": "6b7a14634fa3a1d18883782973f9d7a349d7bad4a5cfa122a86bc64fac1e49fb",
        "scale": (42.629469, 1000.0, 1.0),
        "output_name": "SM_LandingFloor_ScaleBaked_v1",
        "external_actor": "Content/__ExternalActors__/ThirdPerson/Lvl_ThirdPerson/D/K5/NQBPXM7AM8N39CBW4ZT57P.uasset",
        "external_sha256": "32747f42e1969c2b8d9c72d2319a8819f2a7cff8dac14fa3578a5cd1f3e3eab3",
    },
    {
        "label": "m13aa_01a2",
        "guid": "39A96FF046720C0C936788BC9A08FBF1",
        "source_mesh": "/Game/LevelPrototyping/KotorModels/m13aa_01a.m13aa_01a",
        "source_file": "Content/LevelPrototyping/KotorModels/m13aa_01a.uasset",
        "source_sha256": "11456629f09e36dc644dfc18da2ddff8c981d3994c565dbd854a9a65c305fa54",
        "scale": (2.75, 3.906263, 3.0),
        "output_name": "SM_LandingStructure_m13aa_01a_ScaleBaked_v1",
        "external_actor": "Content/__ExternalActors__/ThirdPerson/Lvl_ThirdPerson/1/KY/ED4TVT1UJKRMVUY4IPODSB.uasset",
        "external_sha256": "d78c4615c4855622456153c6a41864cef7637ee55e7c47ad6c89546fc0753198",
    },
    {
        "label": "dor_lda3",
        "guid": "FDADFE844299C99B7C68A09E080D956B",
        "source_mesh": "/Game/LevelPrototyping/KotorModels/dor_lda02.dor_lda02",
        "source_file": "Content/LevelPrototyping/KotorModels/dor_lda02.uasset",
        "source_sha256": "12e5be9f2ae3dc44691fc7569bffb201e19e45d470e1c500c71488becc784330",
        "scale": (2.0, 2.830045, 2.5),
        "output_name": "SM_LandingDoor_West_ScaleBaked_v1",
        "external_actor": "Content/__ExternalActors__/ThirdPerson/Lvl_ThirdPerson/E/G0/XFXU38UQELQVFZB2F7N135.uasset",
        "external_sha256": "f49bbc26a56f329921dc606b9f433422684b6eb75e559076c7bcb5d01a734a90",
    },
    {
        "label": "dor_lda02",
        "guid": "91339B3342056C4A1E4B8DBCCB51237B",
        "source_mesh": "/Game/LevelPrototyping/KotorModels/dor_lda02.dor_lda02",
        "source_file": "Content/LevelPrototyping/KotorModels/dor_lda02.uasset",
        "source_sha256": "12e5be9f2ae3dc44691fc7569bffb201e19e45d470e1c500c71488becc784330",
        "scale": (2.0, 2.890391, 2.5),
        "output_name": "SM_LandingDoor_East_ScaleBaked_v1",
        "external_actor": "Content/__ExternalActors__/ThirdPerson/Lvl_ThirdPerson/C/T8/WPHTMC9INHR6L0VTY1ZP2G.uasset",
        "external_sha256": "df04f1842212f5b97657190aeca74cf598fc273972e8d523a3d597f1045d41f3",
    },
    {
        "label": "dor_lda4",
        "guid": "C312879645CACBA863C2FE93E5CC514D",
        "source_mesh": "/Game/LevelPrototyping/KotorModels/dor_lda02.dor_lda02",
        "source_file": "Content/LevelPrototyping/KotorModels/dor_lda02.uasset",
        "source_sha256": "12e5be9f2ae3dc44691fc7569bffb201e19e45d470e1c500c71488becc784330",
        "scale": (2.0, 2.789983, 2.5),
        "output_name": "SM_LandingDoor_North_ScaleBaked_v1",
        "external_actor": "Content/__ExternalActors__/ThirdPerson/Lvl_ThirdPerson/B/8U/6XXF2313KKICVMHFJDH41Z.uasset",
        "external_sha256": "6948fb4b230b1ec9156b88830b9e03d2152965c1b89f87ff198f7c73554aadde",
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


def _vector_tuple(value):
    return (float(value.x), float(value.y), float(value.z))


def _close_vector(value, expected, tolerance=0.001):
    return all(abs(left - right) <= tolerance for left, right in zip(_vector_tuple(value), expected))


def _bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return {"origin": _vector_tuple(origin), "extent": _vector_tuple(extent)}


def _bounds_close(before, after):
    for key in ("origin", "extent"):
        for left, right in zip(before[key], after[key]):
            tolerance = max(1.0, abs(left) * 0.001, abs(right) * 0.001)
            if abs(left - right) > tolerance:
                return False
    return True


def _repair_bounds_close(expected, actual):
    for left, right in zip(expected["origin"], actual["origin"]):
        if abs(float(left) - float(right)) > 2.5:
            return False
    for left, right in zip(expected["extent"], actual["extent"]):
        tolerance = max(2.5, abs(float(left)) * 0.05)
        if abs(float(left) - float(right)) > tolerance:
            return False
    return True


def _asset_path(spec):
    return MESH_ROOT + "/" + spec["output_name"]


def _object_path(spec):
    path = _asset_path(spec)
    return path + "." + spec["output_name"]


def _package_path(object_path):
    return object_path.split(".", 1)[0]


def _absolute_source_file(project_root, spec):
    path = spec["source_file"]
    return os.path.realpath(path if os.path.isabs(path) else os.path.join(project_root, path))


def _find_records(project_root):
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(subsystem.get_all_level_actors() or [])
    records = []
    for spec in SPECS:
        matches = [actor for actor in actors if _guid(actor) == spec["guid"]]
        if len(matches) != 1:
            raise RuntimeError("Landing scale-bake actor identity is not unique: " + spec["label"])
        actor = matches[0]
        components = list(actor.get_components_by_class(unreal.StaticMeshComponent) or [])
        if len(components) != 1:
            raise RuntimeError("Landing scale-bake actor must have one StaticMeshComponent: " + spec["label"])
        source_file = _absolute_source_file(project_root, spec)
        if _sha256(source_file) != spec["source_sha256"]:
            raise RuntimeError("Protected landing source mesh changed: " + spec["label"])
        records.append((spec, actor, components[0], source_file))
    return records


def _source_hashes(project_root):
    hashes = {}
    for spec in SPECS:
        path = _absolute_source_file(project_root, spec)
        hashes[spec["source_mesh"]] = _sha256(path)
    return hashes


def _external_hashes(project_root):
    return {
        spec["guid"]: _sha256(os.path.realpath(os.path.join(project_root, spec["external_actor"])))
        for spec in SPECS
    }


def _save_actor_packages(records):
    packages = []
    package_names = []
    for spec, actor, _component, _source_file in records:
        package = actor.get_outermost()
        if package is None:
            raise RuntimeError("Could not resolve the external actor package: " + spec["label"])
        packages.append(package)
        package_names.append(package.get_path_name())
    if len(set(package_names)) != len(records):
        raise RuntimeError("Landing scale-bake actors do not own unique external packages")
    if not unreal.EditorLoadingAndSavingUtils.save_packages(packages, False):
        raise RuntimeError("Could not save the exact landing external actor packages")
    return package_names


if MODE not in {"dry_run", "apply", "rollback"}:
    raise RuntimeError("Invalid fixed landing scale-bake mode")
if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The landing scale-bake operation is connected to the wrong project")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not world.get_path_name().startswith(TARGET_MAP + "."):
    raise RuntimeError("The landing scale-bake operation requires the main Enclave level")

project_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
saved_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
evidence_root = os.path.realpath(os.path.join(saved_root, EVIDENCE_RELATIVE))
os.makedirs(evidence_root, exist_ok=True)
receipt_path = os.path.join(evidence_root, RECEIPT_FILENAME)
persistence_path = os.path.join(evidence_root, PERSISTENCE_FILENAME)
rollback_path = os.path.join(evidence_root, ROLLBACK_FILENAME)
repair_receipt_path = os.path.join(evidence_root, REPAIR_RECEIPT_FILENAME)
records = _find_records(project_root)

if MODE == "dry_run":
    items = []
    if os.path.isfile(receipt_path):
        repair = None
        if os.path.isfile(repair_receipt_path):
            with open(repair_receipt_path, "r", encoding="utf-8") as stream:
                repair = json.load(stream)
        repaired_by_guid = {
            item["actor_guid"]: item
            for item in (repair or {}).get("outputs", [])
        }
        for spec, actor, component, _source_file in records[1:]:
            mesh = component.get_editor_property("static_mesh")
            expected_path = repaired_by_guid.get(spec["guid"], {}).get("output_mesh", _object_path(spec))
            if mesh is None or mesh.get_path_name() != expected_path:
                raise RuntimeError("Landing repair input mesh mismatched: " + spec["label"])
            if not _close_vector(actor.get_actor_scale3d(), UNIT_SCALE):
                raise RuntimeError("Landing repair input actor is not unit scale: " + spec["label"])
            items.append({
                "label": spec["label"],
                "actor_guid": spec["guid"],
                "current_mesh": mesh.get_path_name(),
                "baked_scale": spec["scale"],
                "bounds_before": _bounds(actor),
            })
        collisions = list(unreal.EditorAssetLibrary.list_assets(REPAIR_ROOT, recursive=True, include_folder=False) or [])
        eligible = repair is None and len(collisions) == 0
    else:
        for spec, actor, component, _source_file in records:
            mesh = component.get_editor_property("static_mesh")
            if mesh is None or mesh.get_path_name() != spec["source_mesh"]:
                raise RuntimeError("Landing actor no longer references its protected source mesh: " + spec["label"])
            if not _close_vector(actor.get_actor_scale3d(), spec["scale"]):
                raise RuntimeError("Landing actor scale no longer matches the staged source: " + spec["label"])
            items.append({
                "label": spec["label"],
                "actor_guid": spec["guid"],
                "source_mesh": spec["source_mesh"],
                "staged_scale": spec["scale"],
                "output_mesh": _object_path(spec),
                "bounds_before": _bounds(actor),
            })
        collisions = list(unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False) or [])
        eligible = len(collisions) == 0
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-scale-bake/v1",
        "mode": MODE,
        "will_mutate": False,
        "target_map": TARGET_MAP,
        "item_count": len(items),
        "items": items,
        "source_hashes": _source_hashes(project_root),
        "external_actor_hashes": _external_hashes(project_root),
        "output_root": OUTPUT_ROOT,
        "output_collision_count": len(collisions),
        "output_collision_paths": collisions[:32],
        "eligible_to_apply": eligible,
    })

elif MODE == "apply":
    if os.path.isfile(receipt_path):
        with open(receipt_path, "r", encoding="utf-8") as stream:
            prior = json.load(stream)
        if prior.get("schema") != "mcpstudio.enclave-landing-scale-bake-receipt/v1":
            raise RuntimeError("The landing scale-bake receipt schema mismatched")
        if _source_hashes(project_root) != prior.get("source_hashes"):
            raise RuntimeError("Protected landing source mesh changed after scale bake")
        repair_specs = SPECS[1:]
        repair_records = [record for record in records if record[0]["guid"] != SPECS[0]["guid"]]
        if os.path.isfile(repair_receipt_path):
            with open(repair_receipt_path, "rb") as stream:
                repair_bytes = stream.read()
            repair = json.loads(repair_bytes.decode("utf-8"))
            if repair.get("schema") != "mcpstudio.enclave-landing-scale-bake-repair/v2":
                raise RuntimeError("Landing scale-bake repair receipt schema mismatched")
            repaired_by_guid = {item["actor_guid"]: item for item in repair.get("outputs", [])}
            for spec, actor, component, _source_file in repair_records:
                item = repaired_by_guid.get(spec["guid"])
                mesh = component.get_editor_property("static_mesh")
                if item is None or mesh is None or mesh.get_path_name() != item.get("output_mesh"):
                    raise RuntimeError("Landing scale-bake repair mesh drifted: " + spec["label"])
                if not _close_vector(actor.get_actor_scale3d(), UNIT_SCALE):
                    raise RuntimeError("Landing scale-bake repaired actor is not unit scale: " + spec["label"])
            _result.update({
                "schema": "unreal_mcp_ghost.enclave-landing-scale-bake/v1",
                "mode": MODE,
                "idempotent_replay": True,
                "repair_receipt_path": repair_receipt_path,
                "repair_receipt_sha256": hashlib.sha256(repair_bytes).hexdigest(),
                "outputs": repair.get("outputs", []),
            })
        else:
            if unreal.EditorAssetLibrary.list_assets(REPAIR_ROOT, recursive=True, include_folder=False):
                raise RuntimeError("The exclusive landing scale-bake repair namespace contains unreceipted assets")
            prior_by_label = {item["label"]: item for item in prior.get("outputs", [])}
            actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            changed = []
            live_merged = []
            outputs = []
            try:
                unreal.EditorAssetLibrary.make_directory(REPAIR_MESH_ROOT)
                for spec, actor, component, _source_file in repair_records:
                    current_mesh = component.get_editor_property("static_mesh")
                    if current_mesh is None or current_mesh.get_path_name() != _object_path(spec):
                        raise RuntimeError("Landing repair input mesh mismatched: " + spec["label"])
                    if not _close_vector(actor.get_actor_scale3d(), UNIT_SCALE):
                        raise RuntimeError("Landing repair input actor is not unit scale: " + spec["label"])
                    source = unreal.load_asset(spec["source_mesh"])
                    if source is None or not isinstance(source, unreal.StaticMesh):
                        raise RuntimeError("Landing repair source mesh is unavailable: " + spec["label"])
                    temp = actor_subsystem.spawn_actor_from_object(
                        source,
                        unreal.Vector(0.0, 0.0, 0.0),
                        unreal.Rotator(0.0, 0.0, 0.0),
                    )
                    if temp is None:
                        raise RuntimeError("Could not stage landing scale repair: " + spec["label"])
                    temp.set_actor_scale3d(unreal.Vector(*spec["scale"]))
                    temp_component = temp.get_component_by_class(unreal.StaticMeshComponent)
                    if temp_component is None:
                        raise RuntimeError("Landing repair staging component is unavailable")
                    for material_index in range(int(component.get_num_materials())):
                        material = component.get_material(material_index)
                        if material is not None:
                            temp_component.set_material(material_index, material)
                    options = unreal.MergeStaticMeshActorsOptions()
                    repair_base = REPAIR_MESH_ROOT + "/" + spec["output_name"].replace("_v1", "_v2")
                    options.set_editor_property("base_package_name", repair_base)
                    options.set_editor_property("destroy_source_actors", True)
                    options.set_editor_property("spawn_merged_actor", True)
                    options.set_editor_property("new_actor_label", "MCPStudioRepair_" + spec["label"])
                    merged = unreal.EditorLevelLibrary.merge_static_mesh_actors([temp], options)
                    if merged is None:
                        raise RuntimeError("Could not merge landing scale repair: " + spec["label"])
                    live_merged.append(merged)
                    merged_component = merged.get_component_by_class(unreal.StaticMeshComponent)
                    repaired_mesh = None if merged_component is None else merged_component.static_mesh
                    repaired_path = "" if repaired_mesh is None else repaired_mesh.get_path_name()
                    if not repaired_path.startswith(REPAIR_MESH_ROOT + "/"):
                        raise RuntimeError("Landing scale repair escaped its namespace: " + spec["label"])
                    changed.append((spec, actor, component, current_mesh))
                    component.set_static_mesh(repaired_mesh)
                    actor.set_actor_scale3d(unreal.Vector(*UNIT_SCALE))
                    expected = prior_by_label.get(spec["label"], {}).get("bounds_after")
                    actual = _bounds(actor)
                    if not isinstance(expected, dict) or not _repair_bounds_close(expected, actual):
                        raise RuntimeError(
                            "Landing scale repair changed placed bounds: "
                            + spec["label"]
                            + " observed="
                            + json.dumps(actual)
                            + " expected="
                            + json.dumps(expected)
                        )
                    if not unreal.EditorAssetLibrary.save_asset(_package_path(repaired_path), only_if_is_dirty=False):
                        raise RuntimeError("Could not persist landing scale repair: " + spec["label"])
                    actor_subsystem.destroy_actor(merged)
                    live_merged.remove(merged)
                    outputs.append({
                        "label": spec["label"],
                        "actor_guid": spec["guid"],
                        "source_mesh": spec["source_mesh"],
                        "prior_mesh": current_mesh.get_path_name(),
                        "output_mesh": repaired_path,
                        "baked_scale": spec["scale"],
                        "actor_scale_after": UNIT_SCALE,
                        "bounds_after": actual,
                    })
                package_names = _save_actor_packages(repair_records)
                if not unreal.EditorLevelLibrary.save_current_level():
                    raise RuntimeError("Could not save the Enclave level after landing scale repair")
                repair = {
                    "schema": "mcpstudio.enclave-landing-scale-bake-repair/v2",
                    "target_map": TARGET_MAP,
                    "output_root": REPAIR_ROOT,
                    "package_names": package_names,
                    "outputs": outputs,
                }
                repair_bytes = (json.dumps(repair, indent=2, sort_keys=True) + "\n").encode("utf-8")
                with open(repair_receipt_path, "xb") as stream:
                    stream.write(repair_bytes)
                _result.update({
                    "schema": "unreal_mcp_ghost.enclave-landing-scale-bake/v1",
                    "mode": MODE,
                    "idempotent_replay": False,
                    "repair_receipt_path": repair_receipt_path,
                    "repair_receipt_sha256": hashlib.sha256(repair_bytes).hexdigest(),
                    "outputs": outputs,
                })
            except Exception:
                for merged in reversed(live_merged):
                    actor_subsystem.destroy_actor(merged)
                for spec, actor, component, current_mesh in reversed(changed):
                    component.set_static_mesh(current_mesh)
                    actor.set_actor_scale3d(unreal.Vector(*UNIT_SCALE))
                if changed:
                    _save_actor_packages(repair_records)
                    unreal.EditorLevelLibrary.save_current_level()
                unreal.EditorAssetLibrary.delete_directory(REPAIR_ROOT)
                raise
    else:
        if unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False):
            raise RuntimeError("The exclusive landing scale-bake namespace contains unreceipted assets")
        for spec, actor, component, _source_file in records:
            mesh = component.get_editor_property("static_mesh")
            if mesh is None or mesh.get_path_name() != spec["source_mesh"]:
                raise RuntimeError("Landing actor source mesh mismatched before bake: " + spec["label"])
            if not _close_vector(actor.get_actor_scale3d(), spec["scale"]):
                raise RuntimeError("Landing actor scale mismatched before bake: " + spec["label"])
        source_hashes_before = _source_hashes(project_root)
        external_hashes_before = _external_hashes(project_root)
        before_bounds = {spec["guid"]: _bounds(actor) for spec, actor, _component, _source_file in records}
        changed = []
        try:
            unreal.EditorAssetLibrary.make_directory(MESH_ROOT)
            mesh_editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            outputs = []
            for spec, actor, component, _source_file in records:
                duplicate = unreal.EditorAssetLibrary.duplicate_asset(spec["source_mesh"], _asset_path(spec))
                if duplicate is None or not isinstance(duplicate, unreal.StaticMesh):
                    raise RuntimeError("Could not duplicate landing mesh: " + spec["label"])
                lod_count = int(mesh_editor.get_lod_count(duplicate))
                if lod_count < 1:
                    raise RuntimeError("Landing mesh has no buildable LOD: " + spec["label"])
                for lod_index in range(lod_count):
                    settings = mesh_editor.get_lod_build_settings(duplicate, lod_index)
                    current_scale = settings.get_editor_property("build_scale3d")
                    if not _close_vector(current_scale, UNIT_SCALE):
                        raise RuntimeError("Landing duplicate already has a non-unit build scale: " + spec["label"])
                    settings.set_editor_property("build_scale3d", unreal.Vector(*spec["scale"]))
                    mesh_editor.set_lod_build_settings(duplicate, lod_index, settings)
                unreal.EditorAssetLibrary.save_asset(duplicate.get_path_name(), only_if_is_dirty=False)
                component.set_static_mesh(duplicate)
                actor.set_actor_scale3d(unreal.Vector(*UNIT_SCALE))
                changed.append((spec, actor, component))
                after_bounds = _bounds(actor)
                if not _bounds_close(before_bounds[spec["guid"]], after_bounds):
                    raise RuntimeError("Landing scale bake changed placed bounds: " + spec["label"])
                outputs.append({
                    "label": spec["label"],
                    "actor_guid": spec["guid"],
                    "source_mesh": spec["source_mesh"],
                    "output_mesh": duplicate.get_path_name(),
                    "baked_scale": spec["scale"],
                    "actor_scale_after": UNIT_SCALE,
                    "lod_count": lod_count,
                    "bounds_before": before_bounds[spec["guid"]],
                    "bounds_after": after_bounds,
                })
            package_names = _save_actor_packages(records)
            if not unreal.EditorLevelLibrary.save_current_level():
                raise RuntimeError("Could not save the main Enclave level after landing scale bake")
            if _source_hashes(project_root) != source_hashes_before:
                raise RuntimeError("A protected landing source mesh changed during scale bake")
            external_hashes_after = _external_hashes(project_root)
            if any(
                external_hashes_after.get(spec["guid"]) == external_hashes_before.get(spec["guid"])
                for spec in SPECS
            ):
                raise RuntimeError("A landing external actor package did not persist its baked state")
            receipt = {
                "schema": "mcpstudio.enclave-landing-scale-bake-receipt/v1",
                "target_map": TARGET_MAP,
                "output_root": OUTPUT_ROOT,
                "source_hashes": source_hashes_before,
                "external_actor_hashes_before": external_hashes_before,
                "external_actor_hashes_after": external_hashes_after,
                "package_names": package_names,
                "outputs": outputs,
            }
            receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
            with open(receipt_path, "xb") as stream:
                stream.write(receipt_bytes)
            _result.update({
                "schema": "unreal_mcp_ghost.enclave-landing-scale-bake/v1",
                "mode": MODE,
                "idempotent_replay": False,
                "receipt_path": receipt_path,
                "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                "outputs": outputs,
            })
        except Exception:
            for spec, actor, component in reversed(changed):
                source = unreal.load_asset(spec["source_mesh"])
                if source is not None:
                    component.set_static_mesh(source)
                    actor.set_actor_scale3d(unreal.Vector(*spec["scale"]))
            if changed:
                _save_actor_packages(records)
                unreal.EditorLevelLibrary.save_current_level()
            unreal.EditorAssetLibrary.delete_directory(OUTPUT_ROOT)
            raise

else:
    if os.path.isfile(rollback_path):
        with open(rollback_path, "r", encoding="utf-8") as stream:
            prior = json.load(stream)
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-landing-scale-bake/v1",
            "mode": MODE,
            "idempotent_replay": True,
            "outputs": prior,
        })
    else:
        if not os.path.isfile(receipt_path):
            raise RuntimeError("The landing scale-bake receipt is required before rollback")
        with open(receipt_path, "r", encoding="utf-8") as stream:
            receipt = json.load(stream)
        if receipt.get("schema") != "mcpstudio.enclave-landing-scale-bake-receipt/v1":
            raise RuntimeError("The landing scale-bake receipt failed rollback validation")
        for spec, actor, component, _source_file in records:
            source = unreal.load_asset(spec["source_mesh"])
            if source is None or not isinstance(source, unreal.StaticMesh):
                raise RuntimeError("Protected landing source mesh is unavailable: " + spec["label"])
            component.set_static_mesh(source)
            actor.set_actor_scale3d(unreal.Vector(*spec["scale"]))
        _save_actor_packages(records)
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("Could not save the main Enclave level during landing scale-bake rollback")
        assets_before = list(unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False) or [])
        if assets_before and not unreal.EditorAssetLibrary.delete_directory(OUTPUT_ROOT):
            raise RuntimeError("Could not delete the landing scale-bake namespace")
        restored_external_hashes = _external_hashes(project_root)
        expected_external_hashes = receipt.get("external_actor_hashes_before")
        if restored_external_hashes != expected_external_hashes:
            raise RuntimeError("Landing scale-bake rollback did not restore the exact external actor packages")
        outputs = {
            "rolled_back": True,
            "restored_actor_count": len(records),
            "deleted_asset_count": len(assets_before),
            "deleted_assets": assets_before[:64],
            "source_hashes": _source_hashes(project_root),
            "external_actor_hashes": restored_external_hashes,
        }
        rollback_bytes = (json.dumps(outputs, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(rollback_path, "xb") as stream:
            stream.write(rollback_bytes)
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-landing-scale-bake/v1",
            "mode": MODE,
            "idempotent_replay": False,
            "rollback_path": rollback_path,
            "rollback_sha256": hashlib.sha256(rollback_bytes).hexdigest(),
            "outputs": outputs,
        })
