import hashlib
import json
import os
import unreal


MODE = globals().get("MCPSTUDIO_MODE", "dry_run")
EXPECTED_PROJECT = "EnclaveProject"
EXPECTED_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
POST_PROCESS_GUID = "61AEAD1E4CCA665CDAB8ACB3E4D9F68C"
POST_PROCESS_LABEL = "PostProcessVolume"
REVIEW_RECEIPT = "MCPStudio/evidence/enclave_landing_review_capture_v1_receipt.json"
REVIEW_RECEIPT_SHA256 = "435981a0eb1e3f8af5d1753b1d7e8eaebce19db33f709fe256f567f5d6049a12"
RECEIPT_NAME = "enclave_landing_exposure_repair_v1_receipt.json"
ROLLBACK_NAME = "enclave_landing_exposure_repair_v1_rollback.json"


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _receipt_path(name):
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    evidence = os.path.realpath(os.path.join(saved, "MCPStudio", "evidence"))
    os.makedirs(evidence, exist_ok=True)
    return os.path.join(evidence, name)


def _require_review_receipt():
    path = _receipt_path(os.path.basename(REVIEW_RECEIPT))
    if not os.path.isfile(path) or _sha256(path) != REVIEW_RECEIPT_SHA256:
        raise RuntimeError("The exact landing review receipt is missing or drifted")
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


def _find_post_process(actor_subsystem):
    matches = [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if _guid(actor) == POST_PROCESS_GUID
    ]
    if len(matches) != 1:
        raise RuntimeError("The exact landing post-process volume is missing or ambiguous")
    actor = matches[0]
    if (
        actor.get_class().get_name() != "PostProcessVolume"
        or actor.get_actor_label() != POST_PROCESS_LABEL
    ):
        raise RuntimeError("The landing post-process identity drifted")
    if not bool(actor.get_editor_property("enabled")):
        raise RuntimeError("The landing post-process volume is disabled")
    if not bool(actor.get_editor_property("unbound")):
        raise RuntimeError("The landing post-process volume is not unbound")
    return actor


def _snapshot(actor):
    settings = actor.get_editor_property("settings")
    return {
        "actor_guid": POST_PROCESS_GUID,
        "actor_label": POST_PROCESS_LABEL,
        "actor_path": actor.get_path_name(),
        "enabled": bool(actor.get_editor_property("enabled")),
        "unbound": bool(actor.get_editor_property("unbound")),
        "blend_weight": float(actor.get_editor_property("blend_weight")),
        "override_auto_exposure_min_brightness": bool(
            settings.get_editor_property("override_auto_exposure_min_brightness")
        ),
        "auto_exposure_min_brightness": float(
            settings.get_editor_property("auto_exposure_min_brightness")
        ),
        "override_auto_exposure_max_brightness": bool(
            settings.get_editor_property("override_auto_exposure_max_brightness")
        ),
        "auto_exposure_max_brightness": float(
            settings.get_editor_property("auto_exposure_max_brightness")
        ),
        "override_auto_exposure_bias": bool(
            settings.get_editor_property("override_auto_exposure_bias")
        ),
        "auto_exposure_bias": float(
            settings.get_editor_property("auto_exposure_bias")
        ),
    }


def _close(value, expected, tolerance=1e-6):
    return abs(float(value) - float(expected)) <= tolerance


def _is_original(snapshot):
    return (
        snapshot["enabled"] is True
        and snapshot["unbound"] is True
        and _close(snapshot["blend_weight"], 1.0)
        and snapshot["override_auto_exposure_min_brightness"] is True
        and _close(snapshot["auto_exposure_min_brightness"], 0.0)
        and snapshot["override_auto_exposure_max_brightness"] is True
        and _close(snapshot["auto_exposure_max_brightness"], 0.0)
        and snapshot["override_auto_exposure_bias"] is False
        and _close(snapshot["auto_exposure_bias"], 1.0)
    )


def _is_repaired(snapshot):
    return (
        snapshot["enabled"] is True
        and snapshot["unbound"] is True
        and _close(snapshot["blend_weight"], 1.0)
        and snapshot["override_auto_exposure_min_brightness"] is False
        and _close(snapshot["auto_exposure_min_brightness"], 0.0)
        and snapshot["override_auto_exposure_max_brightness"] is False
        and _close(snapshot["auto_exposure_max_brightness"], 0.0)
        and snapshot["override_auto_exposure_bias"] is False
        and _close(snapshot["auto_exposure_bias"], 1.0)
    )


def _set_repaired(actor):
    settings = actor.get_editor_property("settings")
    settings.set_editor_property("override_auto_exposure_min_brightness", False)
    settings.set_editor_property("override_auto_exposure_max_brightness", False)
    actor.set_editor_property("settings", settings)


def _restore(actor, snapshot):
    settings = actor.get_editor_property("settings")
    for name in (
        "override_auto_exposure_min_brightness",
        "auto_exposure_min_brightness",
        "override_auto_exposure_max_brightness",
        "auto_exposure_max_brightness",
        "override_auto_exposure_bias",
        "auto_exposure_bias",
    ):
        settings.set_editor_property(name, snapshot[name])
    actor.set_editor_property("settings", settings)


if MODE not in {"dry_run", "apply", "rollback"}:
    raise RuntimeError("Invalid landing exposure-repair mode")
if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The landing exposure repair is connected to the wrong project")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not world.get_path_name().startswith(EXPECTED_MAP + "."):
    raise RuntimeError("The landing exposure repair requires the Enclave main level")

review_receipt_path = _require_review_receipt()
receipt_path = _receipt_path(RECEIPT_NAME)
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
post_process = _find_post_process(actor_subsystem)
current = _snapshot(post_process)

if MODE == "dry_run":
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-exposure-repair/v1",
        "mode": MODE,
        "will_mutate": False,
        "eligible_to_apply": _is_original(current) or (
            os.path.isfile(receipt_path) and _is_repaired(current)
        ),
        "current": current,
        "planned_changes": {
            "override_auto_exposure_min_brightness": False,
            "override_auto_exposure_max_brightness": False,
        },
        "receipt_path": receipt_path,
        "review_receipt_path": review_receipt_path,
        "review_receipt_sha256": REVIEW_RECEIPT_SHA256,
    })

elif MODE == "apply":
    if os.path.isfile(receipt_path):
        with open(receipt_path, "r", encoding="utf-8") as stream:
            receipt = json.load(stream)
        if (
            receipt.get("schema")
            != "mcpstudio.enclave-landing-exposure-repair-receipt/v1"
            or receipt.get("target_map") != EXPECTED_MAP
            or receipt.get("target_actor_guid") != POST_PROCESS_GUID
            or not _is_repaired(current)
        ):
            raise RuntimeError("The landing exposure-repair receipt or scene state drifted")
        idempotent = True
    else:
        if not _is_original(current):
            raise RuntimeError("The landing exposure state no longer matches the audited original")
        _set_repaired(post_process)
        after = _snapshot(post_process)
        if not _is_repaired(after):
            _restore(post_process, current)
            raise RuntimeError("The landing exposure repair did not verify")
        if not unreal.EditorLevelLibrary.save_current_level():
            _restore(post_process, current)
            raise RuntimeError("Could not save the Enclave main level after exposure repair")
        receipt = {
            "schema": "mcpstudio.enclave-landing-exposure-repair-receipt/v1",
            "target_map": EXPECTED_MAP,
            "target_actor_guid": POST_PROCESS_GUID,
            "review_receipt_sha256": REVIEW_RECEIPT_SHA256,
            "before": current,
            "after": after,
        }
        receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(receipt_path, "xb") as stream:
            stream.write(receipt_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        idempotent = False
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-exposure-repair/v1",
        "mode": MODE,
        "idempotent_replay": idempotent,
        "receipt_path": receipt_path,
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "before": receipt["before"],
        "after": receipt["after"],
    })

else:
    if not os.path.isfile(receipt_path):
        raise RuntimeError("The landing exposure-repair receipt is required for rollback")
    with open(receipt_path, "r", encoding="utf-8") as stream:
        receipt = json.load(stream)
    if (
        receipt.get("schema")
        != "mcpstudio.enclave-landing-exposure-repair-receipt/v1"
        or receipt.get("target_map") != EXPECTED_MAP
        or receipt.get("target_actor_guid") != POST_PROCESS_GUID
        or not _is_repaired(current)
    ):
        raise RuntimeError("The landing exposure state is not eligible for exact rollback")
    _restore(post_process, receipt["before"])
    restored = _snapshot(post_process)
    if not _is_original(restored):
        raise RuntimeError("The landing exposure rollback did not restore the original state")
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("Could not save the Enclave main level after exposure rollback")
    rollback_path = _receipt_path(ROLLBACK_NAME)
    rollback = {
        "schema": "mcpstudio.enclave-landing-exposure-repair-rollback/v1",
        "target_map": EXPECTED_MAP,
        "target_actor_guid": POST_PROCESS_GUID,
        "restored": restored,
        "source_receipt_sha256": _sha256(receipt_path),
    }
    with open(rollback_path, "x", encoding="utf-8") as stream:
        json.dump(rollback, stream, indent=2, sort_keys=True)
        stream.write("\n")
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-exposure-repair/v1",
        "mode": MODE,
        "idempotent_replay": False,
        "rollback_path": rollback_path,
        "restored": restored,
    })
