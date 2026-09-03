import hashlib
import json
import os
import unreal

EXPECTED_PROJECT = "EnclaveProject"
EXPECTED_MANIFEST_SHA256 = "54a90ba6cb18943c0ddaba928cdf9fa074c688f7c27f652aa9a5f54e1cae4b44"
EXPECTED_MATERIAL_ID = "unrealengine-pack-2:walls:middle-eastern-wall"
SOURCE_MESH = "/Game/LevelPrototyping/ModularKit/SM_Enclave_CentralPavilion_Main_A.SM_Enclave_CentralPavilion_Main_A"
OUTPUT_ROOT = "/Game/MCPStudio/EnclavePilot/v1"
ORIGINAL_FILES = {
    "targetMap": ("Content/ThirdPerson/Lvl_ThirdPerson.umap", "3e668a9b3098a76f49ce307759ab00662406c7fa0870eeee6e7a2dbf7f854386"),
    "ebonHawkExternalActor": ("Content/__ExternalActors__/ThirdPerson/Lvl_ThirdPerson/C/YR/UEIU0SB2UAJGUYCIP860S0.uasset", "7960dde3774e0d91bfa615d43cfb95ba864028834a59cb3674e1d09173db6169"),
    "sourcePavilion": ("Content/LevelPrototyping/ModularKit/SM_Enclave_CentralPavilion_Main_A.uasset", "a2d152effdcd05f0d4d423a1bc68104dec0251500a512ffa6e9ae70786709504"),
}


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The fixed Enclave pilot is connected to the wrong project")
project_root = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
original_hashes = {}
for label, (relative_path, expected_hash) in ORIGINAL_FILES.items():
    path = os.path.realpath(os.path.join(project_root, relative_path))
    observed_hash = _sha256(path)
    if observed_hash != expected_hash:
        raise RuntimeError(f"Protected input identity mismatch: {label}")
    original_hashes[label] = observed_hash

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
    staged[kind] = item.get("sha256")
required = {"base-color", "normal", "roughness", "height", "ambient-occlusion"}
if set(staged) != required:
    raise RuntimeError("The fixed staged material channel set is incomplete")
source_mesh = unreal.load_asset(SOURCE_MESH)
if source_mesh is None or not isinstance(source_mesh, unreal.StaticMesh):
    raise RuntimeError("The fixed source pavilion mesh is unavailable")
existing_outputs = unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False)
_result.update({
    "schema": "unreal_mcp_ghost.enclave_sandstone_pilot.v1",
    "mode": "dry_run",
    "will_mutate": False,
    "project": EXPECTED_PROJECT,
    "source_mesh": SOURCE_MESH,
    "output_root": OUTPUT_ROOT,
    "output_collision_count": len(existing_outputs),
    "output_collision_paths": list(existing_outputs)[:32],
    "manifest_sha256": EXPECTED_MANIFEST_SHA256,
    "staged_channels": sorted(staged),
    "metallic_policy": "nonmetal-zero",
    "original_hashes": original_hashes,
    "eligible_to_apply": len(existing_outputs) == 0,
})
