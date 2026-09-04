import hashlib
import json
import os
import unreal

EXPECTED_PROJECT = "EnclaveProject"
OUTPUT_ROOT = "/Game/MCPStudio/EnclavePilot/v1"
ORIGINAL_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
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
receipt_dir = os.path.realpath(os.path.join(unreal.Paths.project_saved_dir(), "MCPStudio/evidence"))
receipt_path = os.path.join(receipt_dir, "enclave_sandstone_pilot_v1_receipt.json")
screenshot_path = os.path.join(receipt_dir, "enclave_sandstone_pilot_v1.png")
if not os.path.isfile(receipt_path):
    raise RuntimeError("The exact pilot receipt is required before rollback")
with open(receipt_path, "r", encoding="utf-8") as stream:
    receipt = json.load(stream)
if receipt.get("schema") != "mcpstudio.enclave-sandstone-pilot-receipt/v1" or receipt.get("outputs", {}).get("content_root") != OUTPUT_ROOT:
    raise RuntimeError("The exact pilot receipt failed rollback validation")
if not unreal.EditorLoadingAndSavingUtils.load_map(ORIGINAL_MAP):
    raise RuntimeError("Could not restore the original Enclave map before rollback")
assets_before = unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False)
if assets_before and not unreal.EditorAssetLibrary.delete_directory(OUTPUT_ROOT):
    raise RuntimeError("Could not delete the exact namespaced pilot directory")
assets_after = unreal.EditorAssetLibrary.list_assets(OUTPUT_ROOT, recursive=True, include_folder=False)
if assets_after:
    raise RuntimeError("Namespaced pilot assets remain after rollback")
if os.path.isfile(screenshot_path):
    os.remove(screenshot_path)
os.remove(receipt_path)
original_hashes_after = _verify_originals(project_root)
_result.update({
    "schema": "unreal_mcp_ghost.enclave_sandstone_pilot.v1",
    "mode": "rollback",
    "rolled_back": True,
    "deleted_asset_count": len(assets_before),
    "deleted_assets": list(assets_before)[:64],
    "original_hashes_before": original_hashes_before,
    "original_hashes_after": original_hashes_after,
})
