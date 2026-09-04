import hashlib
import json
import os
import re

import unreal


EXPECTED_PROJECT = "EnclaveProject"
TARGET_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
OUTPUT_ROOT = "/Game/MCPStudio/Enclave/StagedScaleBake/v1"
EVIDENCE_RELATIVE = "MCPStudio/evidence"
UNIT_SCALE = (1.0, 1.0, 1.0)
BATCH_COUNT = 8
MODE = globals().get("_MCPSTUDIO_FIXED_MODE", "dry_run")
BATCH_INDEX = int(globals().get("_MCPSTUDIO_FIXED_BATCH", 0))

ALLOWED_SOURCE_MESHES = frozenset(
    {
        "/Game/LevelPrototyping/ModularKit/sm_enclave_arcade_columned_a.sm_enclave_arcade_columned_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_buttress_roof_transition_a.sm_enclave_buttress_roof_transition_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_buttress_twin_tall_assembly_a.sm_enclave_buttress_twin_tall_assembly_a",
        "/Game/LevelPrototyping/ModularKit/SM_Enclave_CentralPavilion_Main_A.SM_Enclave_CentralPavilion_Main_A",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_courtyard_parapet_cap_curved_a.sm_enclave_courtyard_parapet_cap_curved_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_courtyard_planter_base_ring_a.sm_enclave_courtyard_planter_base_ring_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_courtyard_planter_inset_Left.sm_enclave_courtyard_planter_inset_Left",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_courtyard_planter_inset_panel_a.sm_enclave_courtyard_planter_inset_panel_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_courtyard_planter_inset_Right.sm_enclave_courtyard_planter_inset_Right",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_courtyard_upper_buttress_tower_b.sm_enclave_courtyard_upper_buttress_tower_b",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_exit_opening_tunnel_bay_a.sm_enclave_exit_opening_tunnel_bay_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_exit_path_curb_straight_a.sm_enclave_exit_path_curb_straight_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_exit_path_curved_segment_a.sm_enclave_exit_path_curved_segment_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_exit_path_junction_node_a.sm_enclave_exit_path_junction_node_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_exit_path_straight_segment_a.sm_enclave_exit_path_straight_segment_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_exit_pavilion_main_a.sm_enclave_exit_pavilion_main_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_exit_side_retaining_wedge_a.sm_enclave_exit_side_retaining_wedge_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_exit_terrain_embankment_transition_a.sm_enclave_exit_terrain_embankment_transition_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_Jedi_Sentinel_Statue.sm_enclave_Jedi_Sentinel_Statue",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_roof_buttress_fin_hero_a.sm_enclave_roof_buttress_fin_hero_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_roof_dome_cap_a.sm_enclave_roof_dome_cap_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_rotunda_wall_wedge_a.sm_enclave_rotunda_wall_wedge_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_rotunda_window_wedge_a.sm_enclave_rotunda_window_wedge_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_service_doorway_a.sm_enclave_service_doorway_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_tree_uneti_a.sm_enclave_tree_uneti_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_wall_curved_exterior_a.sm_enclave_wall_curved_exterior_a",
        "/Game/LevelPrototyping/ModularKit/sm_enclave_wall_radial_section_a.sm_enclave_wall_radial_section_a",
    }
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
    return all(
        abs(left - right) <= tolerance
        for left, right in zip(_vector_tuple(value), expected)
    )


def _bounds(actor):
    origin, extent = actor.get_actor_bounds(False)
    return {"origin": _vector_tuple(origin), "extent": _vector_tuple(extent)}


def _bounds_close(before, after):
    for key in ("origin", "extent"):
        for left, right in zip(before[key], after[key]):
            tolerance = max(2.5, abs(float(left)) * 0.005, abs(float(right)) * 0.005)
            if abs(float(left) - float(right)) > tolerance:
                return False
    return True


def _material_paths(component):
    paths = []
    for material_index in range(int(component.get_num_materials())):
        material = component.get_material(material_index)
        paths.append("" if material is None else material.get_path_name())
    return tuple(paths)


def _group_key(source_mesh, scale, materials):
    scale_text = ",".join("{:.6f}".format(float(value)) for value in scale)
    return source_mesh + "|" + scale_text + "|" + "|".join(materials)


def _group_batch(group_key):
    return int(hashlib.sha256(group_key.encode("utf-8")).hexdigest()[:8], 16) % BATCH_COUNT


def _source_file(project_root, source_mesh):
    package_path = source_mesh.split(".", 1)[0]
    if not package_path.startswith("/Game/"):
        raise RuntimeError("Staged prop source escaped /Game")
    relative = package_path[len("/Game/") :] + ".uasset"
    path = os.path.realpath(os.path.join(project_root, "Content", relative.replace("/", os.sep)))
    content_root = os.path.realpath(os.path.join(project_root, "Content"))
    if os.path.commonpath((content_root, path)) != content_root or not os.path.isfile(path):
        raise RuntimeError("Staged prop source file is unavailable: " + source_mesh)
    return path


def _actor_records():
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    records = []
    for actor in list(subsystem.get_all_level_actors() or []):
        components = list(actor.get_components_by_class(unreal.StaticMeshComponent) or [])
        if len(components) != 1:
            continue
        component = components[0]
        mesh = component.get_editor_property("static_mesh")
        if mesh is None:
            continue
        source_mesh = mesh.get_path_name()
        if source_mesh not in ALLOWED_SOURCE_MESHES:
            continue
        scale = _vector_tuple(actor.get_actor_scale3d())
        if _close_vector(actor.get_actor_scale3d(), UNIT_SCALE):
            continue
        materials = _material_paths(component)
        key = _group_key(source_mesh, scale, materials)
        if _group_batch(key) != BATCH_INDEX:
            continue
        records.append(
            {
                "actor": actor,
                "component": component,
                "guid": _guid(actor),
                "label": actor.get_actor_label(),
                "source_mesh": source_mesh,
                "scale": scale,
                "materials": materials,
                "group_key": key,
                "group_digest": hashlib.sha256(key.encode("utf-8")).hexdigest(),
                "bounds_before": _bounds(actor),
            }
        )
    records.sort(key=lambda item: item["guid"])
    if len({item["guid"] for item in records}) != len(records):
        raise RuntimeError("Staged prop actor GUIDs are not unique")
    return records


def _find_actor_by_guid(guid):
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matches = [
        actor
        for actor in list(subsystem.get_all_level_actors() or [])
        if _guid(actor) == guid
    ]
    if len(matches) != 1:
        raise RuntimeError("Staged prop actor identity is not unique: " + guid)
    return matches[0]


def _save_actor_packages(actors):
    packages = []
    names = []
    for actor in actors:
        package = actor.get_outermost()
        if package is None:
            raise RuntimeError("Could not resolve a staged prop actor package")
        name = package.get_path_name()
        if name not in names:
            names.append(name)
            packages.append(package)
    if not unreal.EditorLoadingAndSavingUtils.save_packages(packages, False):
        raise RuntimeError("Could not save staged prop actor packages")
    return names


def _safe_asset_name(source_mesh, group_digest):
    base = source_mesh.rsplit("/", 1)[-1].split(".", 1)[0]
    base = re.sub(r"[^A-Za-z0-9_]", "_", base)
    return "SM_Baked_" + base + "_" + group_digest[:10] + "_v1"


def _batch_paths(saved_root):
    batch_name = "Batch{}".format(BATCH_INDEX)
    output_root = OUTPUT_ROOT + "/" + batch_name
    mesh_root = output_root + "/Meshes"
    evidence_root = os.path.realpath(os.path.join(saved_root, EVIDENCE_RELATIVE))
    receipt = os.path.join(
        evidence_root,
        "enclave_staged_prop_scale_bake_v1_batch_{}_receipt.json".format(BATCH_INDEX),
    )
    rollback = os.path.join(
        evidence_root,
        "enclave_staged_prop_scale_bake_v1_batch_{}_rollback.json".format(BATCH_INDEX),
    )
    return output_root, mesh_root, evidence_root, receipt, rollback


def _receipt_replay(receipt):
    outputs = list(receipt.get("outputs") or [])
    for item in outputs:
        actor = _find_actor_by_guid(item["actor_guid"])
        components = list(actor.get_components_by_class(unreal.StaticMeshComponent) or [])
        if len(components) != 1:
            raise RuntimeError("Replayed staged prop no longer has one mesh component")
        mesh = components[0].get_editor_property("static_mesh")
        if mesh is None or mesh.get_path_name() != item["output_mesh"]:
            raise RuntimeError("Replayed staged prop output mesh drifted: " + item["label"])
        if not _close_vector(actor.get_actor_scale3d(), UNIT_SCALE):
            raise RuntimeError("Replayed staged prop is not unit scale: " + item["label"])
    return outputs


if MODE not in {"dry_run", "apply", "rollback"}:
    raise RuntimeError("Invalid fixed staged prop scale-bake mode")
if BATCH_INDEX < 0 or BATCH_INDEX >= BATCH_COUNT:
    raise RuntimeError("Invalid fixed staged prop scale-bake batch")
if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The staged prop scale bake is connected to the wrong project")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not world.get_path_name().startswith(TARGET_MAP + "."):
    raise RuntimeError("The staged prop scale bake requires the main Enclave level")

project_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
saved_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
output_root, mesh_root, evidence_root, receipt_path, rollback_path = _batch_paths(saved_root)
os.makedirs(evidence_root, exist_ok=True)

if MODE == "dry_run":
    if os.path.isfile(rollback_path):
        with open(rollback_path, "r", encoding="utf-8") as stream:
            rollback = json.load(stream)
        _result.update(
            {
                "schema": "unreal_mcp_ghost.enclave-staged-prop-scale-bake/v1",
                "mode": MODE,
                "batch": BATCH_INDEX,
                "batch_count": BATCH_COUNT,
                "will_mutate": False,
                "rolled_back": True,
                "outputs": rollback,
            }
        )
    elif os.path.isfile(receipt_path):
        with open(receipt_path, "rb") as stream:
            receipt_bytes = stream.read()
        receipt = json.loads(receipt_bytes.decode("utf-8"))
        outputs = _receipt_replay(receipt)
        _result.update(
            {
                "schema": "unreal_mcp_ghost.enclave-staged-prop-scale-bake/v1",
                "mode": MODE,
                "batch": BATCH_INDEX,
                "batch_count": BATCH_COUNT,
                "will_mutate": False,
                "idempotent_replay": True,
                "receipt_path": receipt_path,
                "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                "outputs": outputs,
            }
        )
    else:
        records = _actor_records()
        collisions = list(
            unreal.EditorAssetLibrary.list_assets(
                output_root, recursive=True, include_folder=False
            )
            or []
        )
        groups = {}
        source_hashes = {}
        for item in records:
            groups.setdefault(item["group_digest"], []).append(item)
            if item["source_mesh"] not in source_hashes:
                source_hashes[item["source_mesh"]] = _sha256(
                    _source_file(project_root, item["source_mesh"])
                )
        _result.update(
            {
                "schema": "unreal_mcp_ghost.enclave-staged-prop-scale-bake/v1",
                "mode": MODE,
                "batch": BATCH_INDEX,
                "batch_count": BATCH_COUNT,
                "will_mutate": False,
                "target_map": TARGET_MAP,
                "actor_count": len(records),
                "variant_count": len(groups),
                "eligible_to_apply": len(records) > 0 and len(collisions) == 0,
                "output_root": output_root,
                "output_collision_paths": collisions[:32],
                "source_hashes": source_hashes,
                "items": [
                    {
                        "label": item["label"],
                        "actor_guid": item["guid"],
                        "source_mesh": item["source_mesh"],
                        "staged_scale": item["scale"],
                        "material_paths": item["materials"],
                        "group_digest": item["group_digest"],
                        "bounds_before": item["bounds_before"],
                    }
                    for item in records
                ],
            }
        )

elif MODE == "apply":
    if os.path.isfile(rollback_path):
        raise RuntimeError("This staged prop scale-bake batch was already rolled back")
    if os.path.isfile(receipt_path):
        with open(receipt_path, "rb") as stream:
            receipt_bytes = stream.read()
        receipt = json.loads(receipt_bytes.decode("utf-8"))
        outputs = _receipt_replay(receipt)
        _result.update(
            {
                "schema": "unreal_mcp_ghost.enclave-staged-prop-scale-bake/v1",
                "mode": MODE,
                "batch": BATCH_INDEX,
                "idempotent_replay": True,
                "receipt_path": receipt_path,
                "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                "outputs": outputs,
            }
        )
    else:
        records = _actor_records()
        if not records:
            raise RuntimeError("This staged prop scale-bake batch has no eligible actors")
        collisions = list(
            unreal.EditorAssetLibrary.list_assets(
                output_root, recursive=True, include_folder=False
            )
            or []
        )
        if collisions:
            raise RuntimeError("The staged prop scale-bake batch namespace is not empty")

        groups = {}
        source_hashes = {}
        for item in records:
            groups.setdefault(item["group_digest"], []).append(item)
            if item["source_mesh"] not in source_hashes:
                source_hashes[item["source_mesh"]] = _sha256(
                    _source_file(project_root, item["source_mesh"])
                )

        actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        changed = []
        live_merged = []
        outputs = []
        variant_outputs = []
        try:
            unreal.EditorAssetLibrary.make_directory(mesh_root)
            for group_digest in sorted(groups):
                members = groups[group_digest]
                first = members[0]
                source = unreal.load_asset(first["source_mesh"])
                if source is None or not isinstance(source, unreal.StaticMesh):
                    raise RuntimeError("Staged prop source mesh is unavailable")
                temp = actor_subsystem.spawn_actor_from_object(
                    source,
                    unreal.Vector(0.0, 0.0, 0.0),
                    unreal.Rotator(0.0, 0.0, 0.0),
                )
                if temp is None:
                    raise RuntimeError("Could not stage a modular scale-bake variant")
                temp.set_actor_scale3d(unreal.Vector(*first["scale"]))
                temp_component = temp.get_component_by_class(unreal.StaticMeshComponent)
                if temp_component is None:
                    raise RuntimeError("Staged scale-bake temporary component is unavailable")
                for material_index, material_path in enumerate(first["materials"]):
                    material = unreal.load_asset(material_path) if material_path else None
                    if material is not None:
                        temp_component.set_material(material_index, material)

                output_name = _safe_asset_name(first["source_mesh"], group_digest)
                output_asset = mesh_root + "/" + output_name
                options = unreal.MergeStaticMeshActorsOptions()
                options.set_editor_property("base_package_name", output_asset)
                options.set_editor_property("destroy_source_actors", True)
                options.set_editor_property("spawn_merged_actor", True)
                options.set_editor_property("new_actor_label", "MCPStudioStageBake_" + output_name)
                merged = unreal.EditorLevelLibrary.merge_static_mesh_actors([temp], options)
                if merged is None:
                    raise RuntimeError("Could not merge a staged modular scale variant")
                live_merged.append(merged)
                merged_component = merged.get_component_by_class(unreal.StaticMeshComponent)
                baked_mesh = None if merged_component is None else merged_component.static_mesh
                baked_path = "" if baked_mesh is None else baked_mesh.get_path_name()
                if not baked_path.startswith(mesh_root + "/"):
                    raise RuntimeError("A staged scale-bake output escaped its fixed namespace")
                if not unreal.EditorAssetLibrary.save_asset(
                    baked_path.split(".", 1)[0], only_if_is_dirty=False
                ):
                    raise RuntimeError("Could not save a staged scale-bake mesh")
                actor_subsystem.destroy_actor(merged)
                live_merged.remove(merged)

                variant_outputs.append(
                    {
                        "group_digest": group_digest,
                        "source_mesh": first["source_mesh"],
                        "baked_scale": first["scale"],
                        "material_paths": first["materials"],
                        "output_mesh": baked_path,
                        "actor_count": len(members),
                    }
                )
                for item in members:
                    actor = item["actor"]
                    component = item["component"]
                    changed.append(item)
                    component.set_static_mesh(baked_mesh)
                    actor.set_actor_scale3d(unreal.Vector(*UNIT_SCALE))
                    after = _bounds(actor)
                    if not _bounds_close(item["bounds_before"], after):
                        raise RuntimeError(
                            "Staged scale bake changed placed bounds: " + item["label"]
                        )
                    outputs.append(
                        {
                            "label": item["label"],
                            "actor_guid": item["guid"],
                            "source_mesh": item["source_mesh"],
                            "output_mesh": baked_path,
                            "baked_scale": item["scale"],
                            "actor_scale_after": UNIT_SCALE,
                            "material_paths": item["materials"],
                            "group_digest": group_digest,
                            "bounds_before": item["bounds_before"],
                            "bounds_after": after,
                        }
                    )

            package_names = _save_actor_packages([item["actor"] for item in records])
            if not unreal.EditorLevelLibrary.save_current_level():
                raise RuntimeError("Could not save the Enclave level after staged scale bake")
            observed_source_hashes = {
                path: _sha256(_source_file(project_root, path)) for path in source_hashes
            }
            if observed_source_hashes != source_hashes:
                raise RuntimeError("A protected modular source mesh changed during scale bake")
            receipt = {
                "schema": "mcpstudio.enclave-staged-prop-scale-bake-receipt/v1",
                "target_map": TARGET_MAP,
                "batch": BATCH_INDEX,
                "batch_count": BATCH_COUNT,
                "output_root": output_root,
                "source_hashes": source_hashes,
                "package_names": package_names,
                "variants": variant_outputs,
                "outputs": outputs,
            }
            receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode(
                "utf-8"
            )
            with open(receipt_path, "xb") as stream:
                stream.write(receipt_bytes)
            _result.update(
                {
                    "schema": "unreal_mcp_ghost.enclave-staged-prop-scale-bake/v1",
                    "mode": MODE,
                    "batch": BATCH_INDEX,
                    "idempotent_replay": False,
                    "receipt_path": receipt_path,
                    "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                    "variant_count": len(variant_outputs),
                    "outputs": outputs,
                }
            )
        except Exception:
            for merged in reversed(live_merged):
                actor_subsystem.destroy_actor(merged)
            for item in reversed(changed):
                source = unreal.load_asset(item["source_mesh"])
                if source is not None:
                    item["component"].set_static_mesh(source)
                    item["actor"].set_actor_scale3d(unreal.Vector(*item["scale"]))
            if changed:
                _save_actor_packages([item["actor"] for item in records])
                unreal.EditorLevelLibrary.save_current_level()
            unreal.EditorAssetLibrary.delete_directory(output_root)
            raise

else:
    if os.path.isfile(rollback_path):
        with open(rollback_path, "r", encoding="utf-8") as stream:
            prior = json.load(stream)
        _result.update(
            {
                "schema": "unreal_mcp_ghost.enclave-staged-prop-scale-bake/v1",
                "mode": MODE,
                "batch": BATCH_INDEX,
                "idempotent_replay": True,
                "outputs": prior,
            }
        )
    else:
        if not os.path.isfile(receipt_path):
            raise RuntimeError("The staged prop scale-bake receipt is required before rollback")
        with open(receipt_path, "r", encoding="utf-8") as stream:
            receipt = json.load(stream)
        if receipt.get("schema") != "mcpstudio.enclave-staged-prop-scale-bake-receipt/v1":
            raise RuntimeError("The staged prop scale-bake receipt failed validation")
        restored = []
        actors = []
        for item in receipt.get("outputs") or []:
            actor = _find_actor_by_guid(item["actor_guid"])
            components = list(actor.get_components_by_class(unreal.StaticMeshComponent) or [])
            if len(components) != 1:
                raise RuntimeError("Rollback actor no longer has one mesh component")
            source = unreal.load_asset(item["source_mesh"])
            if source is None or not isinstance(source, unreal.StaticMesh):
                raise RuntimeError("Protected staged prop source is unavailable")
            components[0].set_static_mesh(source)
            actor.set_actor_scale3d(unreal.Vector(*item["baked_scale"]))
            after = _bounds(actor)
            if not _bounds_close(item["bounds_before"], after):
                raise RuntimeError("Staged prop rollback changed placed bounds: " + item["label"])
            actors.append(actor)
            restored.append(
                {
                    "label": item["label"],
                    "actor_guid": item["actor_guid"],
                    "source_mesh": item["source_mesh"],
                    "restored_scale": item["baked_scale"],
                    "bounds_after": after,
                }
            )
        package_names = _save_actor_packages(actors)
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("Could not save the Enclave level during staged scale rollback")
        assets = list(
            unreal.EditorAssetLibrary.list_assets(
                output_root, recursive=True, include_folder=False
            )
            or []
        )
        if assets and not unreal.EditorAssetLibrary.delete_directory(output_root):
            raise RuntimeError("Could not delete the staged scale-bake batch namespace")
        rollback = {
            "rolled_back": True,
            "batch": BATCH_INDEX,
            "restored_actor_count": len(restored),
            "deleted_asset_count": len(assets),
            "package_names": package_names,
            "outputs": restored,
        }
        rollback_bytes = (json.dumps(rollback, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
        with open(rollback_path, "xb") as stream:
            stream.write(rollback_bytes)
        _result.update(
            {
                "schema": "unreal_mcp_ghost.enclave-staged-prop-scale-bake/v1",
                "mode": MODE,
                "batch": BATCH_INDEX,
                "idempotent_replay": False,
                "rollback_path": rollback_path,
                "rollback_sha256": hashlib.sha256(rollback_bytes).hexdigest(),
                "outputs": rollback,
            }
        )
