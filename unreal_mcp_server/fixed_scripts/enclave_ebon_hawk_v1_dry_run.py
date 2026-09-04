import hashlib
import json
import os
import unreal

EXPECTED_PROJECT = "EnclaveProject"
TARGET_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
EBON_GUID = "B618B798424015C10441568564ACA29B"
ORIGINAL_MESH = "/Game/LevelPrototyping/KotorModels/ebon_01.ebon_01"
OUTPUT_ROOT = "/Game/MCPStudio/Enclave/EbonHawk/v2"
ORIGINAL_LOCATION = (-4620.0, 522.511671, 20.0)
ORIGINAL_ROTATION = (0.0, 90.0, 90.0)
ORIGINAL_SCALE = (19.0, 19.0, 19.0)
STAGE_RELATIVE = "MCPStudio/staging/ebon_hawk_ghoststudio_v2"
GHOST_STUDIO_VERTEX_SCALE = 0.705
STAGED_FILES = {
    "fbx": ("SM_EbonHawk_GhostStudio_v2.fbx", "1b65e86e1191b6b283ac16a9da668c70235e303c1d94d092c7ae70f964759f94"),
    "manifest": ("SM_EbonHawk_GhostStudio_v2.ghostrigger.json", "456a5725fbcdaa7609fa66d6e09b077cbffdec08f86736fd582de6e3c7d89d66"),
    "base_color": ("textures/v_ehawk01.png", "46fe4f73d0d7543f0dc2bed8c15c542f104cd4431a14b8140f3b06eb88932772"),
    "detail_color": ("textures/v_ehawk01a.png", "a057c668d1b67e97046ee220e04bfbbdfe66663310e016bab4e28af022dc3ea9"),
}
PROTECTED_FILES = {
    "originalMesh": ("Content/LevelPrototyping/KotorModels/ebon_01.uasset", "76678c57fcc881e3c4a89cf55391cb121cdd26ed082e1b9cd7bf6f59104216f5"),
    "originalExternalActor": ("Content/__ExternalActors__/ThirdPerson/Lvl_ThirdPerson/C/YR/UEIU0SB2UAJGUYCIP860S0.uasset", "7960dde3774e0d91bfa615d43cfb95ba864028834a59cb3674e1d09173db6169"),
}


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


def _close_vector(value, expected, tolerance=0.01):
    observed = (float(value.x), float(value.y), float(value.z))
    return all(abs(left - right) <= tolerance for left, right in zip(observed, expected))


def _close_rotation(value, expected, tolerance=0.01):
    observed = (float(value.pitch), float(value.yaw), float(value.roll))
    return all(abs(left - right) <= tolerance for left, right in zip(observed, expected))


if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The fixed Ebon Hawk handoff is connected to the wrong project")
project_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
saved_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
stage_root = os.path.realpath(os.path.join(saved_root, STAGE_RELATIVE))
staged_hashes = {}
for label, (relative_path, expected_hash) in STAGED_FILES.items():
    path = os.path.realpath(os.path.join(stage_root, relative_path))
    if os.path.commonpath([stage_root, path]) != stage_root or _sha256(path) != expected_hash:
        raise RuntimeError(f"Pinned Ghost Studio Ebon Hawk input mismatched: {label}")
    staged_hashes[label] = expected_hash

with open(os.path.join(stage_root, STAGED_FILES["manifest"][0]), "r", encoding="utf-8") as stream:
    manifest = json.load(stream)
if (
    manifest.get("schema") != "ghostrigger.kotor_fbx_manifest.v1"
    or str(manifest.get("source", {}).get("resref", "")).lower() != "v_ehawk"
    or manifest.get("fbx", {}).get("compatibility_profile") != "unreal"
    or manifest.get("fbx", {}).get("ok") is not True
    or manifest.get("fbx", {}).get("textures") != 2
    or manifest.get("mcpstudio", {}).get("schema") != "mcpstudio.ghoststudio-geometry-scale/v1"
    or abs(float(manifest.get("mcpstudio", {}).get("vertex_scale", 0.0)) - GHOST_STUDIO_VERTEX_SCALE) > 0.000001
):
    raise RuntimeError("The pinned Ghost Studio Ebon Hawk manifest is not Unreal-ready")

protected_hashes = {}
for label, (relative_path, expected_hash) in PROTECTED_FILES.items():
    path = os.path.realpath(os.path.join(project_root, relative_path))
    observed = _sha256(path)
    if observed != expected_hash:
        raise RuntimeError(f"Protected Enclave Ebon Hawk identity mismatched: {label}")
    protected_hashes[label] = observed

actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
matches = [actor for actor in actor_subsystem.get_all_level_actors() if _guid(actor) == EBON_GUID]
if len(matches) != 1:
    raise RuntimeError("The fixed Ebon Hawk actor identity is not unique in the loaded map")
components = list(matches[0].get_components_by_class(unreal.StaticMeshComponent) or [])
if len(components) != 1:
    raise RuntimeError("The fixed Ebon Hawk actor does not have exactly one static-mesh component")
mesh = components[0].get_editor_property("static_mesh")
if mesh is None or mesh.get_path_name() != ORIGINAL_MESH:
    raise RuntimeError("The fixed Ebon Hawk actor no longer references its protected source mesh")
if (
    not _close_vector(matches[0].get_actor_location(), ORIGINAL_LOCATION)
    or not _close_rotation(matches[0].get_actor_rotation(), ORIGINAL_ROTATION)
    or not _close_vector(matches[0].get_actor_scale3d(), ORIGINAL_SCALE)
):
    raise RuntimeError("The protected Ebon Hawk actor transform no longer matches its source state")

existing_outputs = unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False)
_result.update({
    "schema": "unreal_mcp_ghost.enclave-ebon-hawk-handoff/v2",
    "mode": "dry_run",
    "will_mutate": False,
    "project": EXPECTED_PROJECT,
    "target_map": TARGET_MAP,
    "actor_guid": EBON_GUID,
    "original_mesh": ORIGINAL_MESH,
    "original_transform": {
        "location": ORIGINAL_LOCATION,
        "rotation_pitch_yaw_roll": ORIGINAL_ROTATION,
        "scale": ORIGINAL_SCALE,
    },
    "output_root": OUTPUT_ROOT,
    "staged_hashes": staged_hashes,
    "protected_hashes": protected_hashes,
    "source_contract": {"game": "K2", "resref": "v_ehawk", "textures": 2},
    "output_collision_count": len(existing_outputs),
    "output_collision_paths": list(existing_outputs)[:32],
    "eligible_to_apply": len(existing_outputs) == 0,
})
