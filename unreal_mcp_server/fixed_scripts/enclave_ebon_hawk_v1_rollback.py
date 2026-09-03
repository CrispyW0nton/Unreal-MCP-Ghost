import hashlib
import json
import os
import unreal

EXPECTED_PROJECT = "EnclaveProject"
EBON_GUID = "B618B798424015C10441568564ACA29B"
ORIGINAL_MESH = "/Game/LevelPrototyping/KotorModels/ebon_01.ebon_01"
OUTPUT_ROOT = "/Game/MCPStudio/Enclave/EbonHawk/v2"
ORIGINAL_LOCATION = (-4620.0, 522.511671, 20.0)
ORIGINAL_ROTATION = (0.0, 90.0, 90.0)
ORIGINAL_SCALE = (19.0, 19.0, 19.0)
ORIGINAL_MESH_FILE = ("Content/LevelPrototyping/KotorModels/ebon_01.uasset", "76678c57fcc881e3c4a89cf55391cb121cdd26ed082e1b9cd7bf6f59104216f5")
ORIGINAL_EXTERNAL_ACTOR_FILE = ("Content/__ExternalActors__/ThirdPerson/Lvl_ThirdPerson/C/YR/UEIU0SB2UAJGUYCIP860S0.uasset", "7960dde3774e0d91bfa615d43cfb95ba864028834a59cb3674e1d09173db6169")


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


def _rotator(pitch_yaw_roll):
    value = unreal.Rotator()
    value.set_editor_property("pitch", pitch_yaw_roll[0])
    value.set_editor_property("yaw", pitch_yaw_roll[1])
    value.set_editor_property("roll", pitch_yaw_roll[2])
    return value


def _close_vector(value, expected, tolerance=0.01):
    observed = (float(value.x), float(value.y), float(value.z))
    return all(abs(left - right) <= tolerance for left, right in zip(observed, expected))


def _close_rotation(value, expected, tolerance=0.01):
    observed = (float(value.pitch), float(value.yaw), float(value.roll))
    return all(abs(left - right) <= tolerance for left, right in zip(observed, expected))


def _restore(actor, component, original):
    component.set_static_mesh(original)
    actor.set_actor_location(unreal.Vector(*ORIGINAL_LOCATION), False, False)
    actor.set_actor_rotation(_rotator(ORIGINAL_ROTATION), False)
    actor.set_actor_scale3d(unreal.Vector(*ORIGINAL_SCALE))
    if (
        not _close_vector(actor.get_actor_location(), ORIGINAL_LOCATION)
        or not _close_rotation(actor.get_actor_rotation(), ORIGINAL_ROTATION)
        or not _close_vector(actor.get_actor_scale3d(), ORIGINAL_SCALE)
    ):
        raise RuntimeError("The Ebon Hawk source transform could not be restored exactly")


if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The fixed Ebon Hawk rollback is connected to the wrong project")
project_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
saved_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
original_mesh_file = os.path.realpath(os.path.join(project_root, ORIGINAL_MESH_FILE[0]))
if _sha256(original_mesh_file) != ORIGINAL_MESH_FILE[1]:
    raise RuntimeError("The protected original Ebon Hawk mesh identity changed")
evidence_root = os.path.realpath(os.path.join(saved_root, "MCPStudio/evidence"))
receipt_path = os.path.join(evidence_root, "enclave_ebon_hawk_v2_receipt.json")
rollback_path = os.path.join(evidence_root, "enclave_ebon_hawk_v2_rollback.json")
failure_path = os.path.join(evidence_root, "enclave_ebon_hawk_v2_deferred_failure.json")
recovered_failure_path = os.path.join(evidence_root, "enclave_ebon_hawk_v2_recovered_failure.json")
if os.path.isfile(rollback_path):
    with open(rollback_path, "r", encoding="utf-8") as stream:
        prior = json.load(stream)
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-ebon-hawk-handoff/v2",
        "mode": "rollback",
        "idempotent_replay": True,
        "outputs": prior,
    })
else:
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    matches = [actor for actor in subsystem.get_all_level_actors() if _guid(actor) == EBON_GUID]
    if len(matches) != 1:
        raise RuntimeError("The fixed Ebon Hawk actor identity is not unique")
    components = list(matches[0].get_components_by_class(unreal.StaticMeshComponent) or [])
    if len(components) != 1:
        raise RuntimeError("The fixed Ebon Hawk actor must have one static-mesh component")
    original = unreal.load_asset(ORIGINAL_MESH)
    if original is None or not isinstance(original, unreal.StaticMesh):
        raise RuntimeError("The protected original Ebon Hawk mesh is unavailable")
    if not os.path.isfile(receipt_path):
        if not os.path.isfile(failure_path):
            raise RuntimeError("The exact Ebon Hawk handoff receipt or deferred failure is required before rollback")
        external_path = os.path.realpath(os.path.join(project_root, ORIGINAL_EXTERNAL_ACTOR_FILE[0]))
        if _sha256(external_path) != ORIGINAL_EXTERNAL_ACTOR_FILE[1]:
            raise RuntimeError("The protected Ebon Hawk external actor changed during the rejected handoff")
        _restore(matches[0], components[0], original)
        assets_before = unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False)
        if assets_before and not unreal.EditorAssetLibrary.delete_directory(OUTPUT_ROOT):
            raise RuntimeError("Could not remove the rejected Ebon Hawk candidate namespace")
        recovery_destination = recovered_failure_path
        if os.path.isfile(recovery_destination):
            recovery_destination = recovered_failure_path[:-5] + "_2.json"
        if os.path.isfile(recovery_destination):
            raise RuntimeError("The fixed Ebon Hawk rejected-apply recovery evidence namespace is exhausted")
        os.replace(failure_path, recovery_destination)
        outputs = {
            "recovered_rejected_apply": True,
            "actor_guid": EBON_GUID,
            "restored_mesh": ORIGINAL_MESH,
            "restored_transform": {
                "location": ORIGINAL_LOCATION,
                "rotation_pitch_yaw_roll": ORIGINAL_ROTATION,
                "scale": ORIGINAL_SCALE,
            },
            "deleted_asset_count": len(assets_before),
            "protected_original_mesh_sha256": _sha256(original_mesh_file),
            "protected_external_actor_sha256": _sha256(external_path),
            "recovered_failure_path": recovery_destination,
        }
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-ebon-hawk-handoff/v2",
            "mode": "rollback",
            "idempotent_replay": False,
            "outputs": outputs,
        })
    else:
        with open(receipt_path, "r", encoding="utf-8") as stream:
            receipt = json.load(stream)
        if receipt.get("schema") != "mcpstudio.enclave-ebon-hawk-receipt/v2":
            raise RuntimeError("The Ebon Hawk handoff receipt failed rollback validation")
        _restore(matches[0], components[0], original)
        package = matches[0].get_outermost()
        if package is None or not unreal.EditorLoadingAndSavingUtils.save_packages([package], False):
            raise RuntimeError("Could not save the exact Ebon Hawk external actor package during rollback")
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("Could not save the Enclave map during Ebon Hawk rollback")
        current = components[0].get_editor_property("static_mesh")
        if current is None or current.get_path_name() != ORIGINAL_MESH:
            raise RuntimeError("The Ebon Hawk actor did not return to its original mesh")
        assets_before = unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False)
        if assets_before and not unreal.EditorAssetLibrary.delete_directory(OUTPUT_ROOT):
            raise RuntimeError("Could not remove the exact Ebon Hawk candidate namespace")
        outputs = {
            "rolled_back": True,
            "actor_guid": EBON_GUID,
            "restored_mesh": ORIGINAL_MESH,
            "restored_transform": {
                "location": ORIGINAL_LOCATION,
                "rotation_pitch_yaw_roll": ORIGINAL_ROTATION,
                "scale": ORIGINAL_SCALE,
            },
            "deleted_asset_count": len(assets_before),
            "deleted_assets": list(assets_before)[:64],
            "protected_original_mesh_sha256": _sha256(original_mesh_file),
        }
        rollback_bytes = (json.dumps(outputs, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(rollback_path, "xb") as stream:
            stream.write(rollback_bytes)
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-ebon-hawk-handoff/v2",
            "mode": "rollback",
            "idempotent_replay": False,
            "rollback_path": rollback_path,
            "rollback_sha256": hashlib.sha256(rollback_bytes).hexdigest(),
            "outputs": outputs,
        })
