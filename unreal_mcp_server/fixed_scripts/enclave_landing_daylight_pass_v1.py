import hashlib
import json
import math
import os
import unreal


MODE = globals().get("MCPSTUDIO_MODE", "dry_run")
EXPECTED_PROJECT = "EnclaveProject"
EXPECTED_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
DIRECTIONAL_GUID = "648F0DD8460F534C038DBA8FD49BBEBD"
SKYLIGHT_GUID = "7C51FF6946709420F344E583FE7EC95F"
EXPOSURE_RECEIPT_SHA256 = "cc723c0caf8d73b52bca79a3667f1cf53fb4f9f3f8e02c38bee757130d4c03f3"
REVIEW_V2_RECEIPT_SHA256 = "7ea1726eab303a115d727ab8d24bcdd5ad55e8d938c4df4401f77c597db5f322"
RECEIPT_NAME = "enclave_landing_daylight_pass_v1_receipt.json"
ROLLBACK_NAME = "enclave_landing_daylight_pass_v1_rollback.json"
TARGET_ROTATION = (-35.0, -45.0, 0.0)
ORIGINAL_ROTATION = (-82.5699466246705, -102.4965355219415, 115.0023429482696)
FAILED_POSITIONAL_RESTORE_ROTATION = (-77.50346374511726, -64.99765777587903, 97.43005371093768)
TARGET_DIRECTIONAL_INTENSITY = 10.0
TARGET_DIRECTIONAL_TEMPERATURE = 5600.0
TARGET_SKYLIGHT_INTENSITY = 2.0
TARGET_LOWER_HEMISPHERE = (0.08, 0.065, 0.05, 1.0)


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
        raise RuntimeError("A daylight-pass prerequisite receipt is missing or drifted")
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


def _find_exact(actor_subsystem, guid, class_name, label):
    matches = [actor for actor in actor_subsystem.get_all_level_actors() if _guid(actor) == guid]
    if len(matches) != 1:
        raise RuntimeError("An exact daylight actor is missing or ambiguous")
    actor = matches[0]
    if actor.get_class().get_name() != class_name or actor.get_actor_label() != label:
        raise RuntimeError("An exact daylight actor identity drifted")
    return actor


def _color_tuple(value):
    return (float(value.r), float(value.g), float(value.b), float(value.a))


def _snapshot(directional_actor, skylight_actor):
    directional = directional_actor.get_component_by_class(unreal.DirectionalLightComponent)
    skylight = skylight_actor.get_component_by_class(unreal.SkyLightComponent)
    if directional is None or skylight is None:
        raise RuntimeError("The exact daylight components are unavailable")
    rotation = directional_actor.get_actor_rotation()
    scale = directional_actor.get_actor_scale3d()
    return {
        "directional": {
            "actor_guid": DIRECTIONAL_GUID,
            "actor_path": directional_actor.get_path_name(),
            "rotation": [float(rotation.pitch), float(rotation.yaw), float(rotation.roll)],
            "scale": [float(scale.x), float(scale.y), float(scale.z)],
            "intensity": float(directional.get_editor_property("intensity")),
            "use_temperature": bool(directional.get_editor_property("use_temperature")),
            "temperature": float(directional.get_editor_property("temperature")),
            "affects_world": bool(directional.get_editor_property("affects_world")),
            "atmosphere_sun_light": bool(
                directional.get_editor_property("atmosphere_sun_light")
            ),
        },
        "skylight": {
            "actor_guid": SKYLIGHT_GUID,
            "actor_path": skylight_actor.get_path_name(),
            "intensity": float(skylight.get_editor_property("intensity")),
            "real_time_capture": bool(skylight.get_editor_property("real_time_capture")),
            "lower_hemisphere_is_black": bool(
                skylight.get_editor_property("lower_hemisphere_is_black")
            ),
            "lower_hemisphere_color": list(
                _color_tuple(skylight.get_editor_property("lower_hemisphere_color"))
            ),
            "affects_world": bool(skylight.get_editor_property("affects_world")),
        },
    }


def _close(left, right, tolerance=1e-5):
    return math.isclose(float(left), float(right), abs_tol=tolerance, rel_tol=0.0)


def _vector_close(values, expected, tolerance=1e-5):
    return len(values) == len(expected) and all(
        _close(value, target, tolerance) for value, target in zip(values, expected)
    )


def _is_original(snapshot):
    directional = snapshot["directional"]
    skylight = snapshot["skylight"]
    return (
        _vector_close(
            directional["rotation"],
            ORIGINAL_ROTATION,
            1e-3,
        )
        and _vector_close(directional["scale"], (2.5, 2.5, 2.5))
        and _close(directional["intensity"], 3.0)
        and directional["use_temperature"] is True
        and _close(directional["temperature"], 6500.0)
        and directional["affects_world"] is True
        and directional["atmosphere_sun_light"] is True
        and _close(skylight["intensity"], 1.0)
        and skylight["real_time_capture"] is True
        and skylight["lower_hemisphere_is_black"] is True
        and _vector_close(skylight["lower_hemisphere_color"], (0.0, 0.0, 0.0, 1.0))
        and skylight["affects_world"] is True
    )


def _is_failed_positional_restore(snapshot):
    recovered = json.loads(json.dumps(snapshot))
    recovered["directional"]["rotation"] = list(ORIGINAL_ROTATION)
    return (
        _vector_close(
            snapshot["directional"]["rotation"],
            FAILED_POSITIONAL_RESTORE_ROTATION,
            1e-3,
        )
        and _is_original(recovered)
    )


def _is_after(snapshot):
    directional = snapshot["directional"]
    skylight = snapshot["skylight"]
    return (
        _vector_close(directional["rotation"], TARGET_ROTATION, 1e-3)
        and _vector_close(directional["scale"], (2.5, 2.5, 2.5))
        and _close(directional["intensity"], TARGET_DIRECTIONAL_INTENSITY)
        and directional["use_temperature"] is True
        and _close(directional["temperature"], TARGET_DIRECTIONAL_TEMPERATURE)
        and directional["affects_world"] is True
        and directional["atmosphere_sun_light"] is True
        and _close(skylight["intensity"], TARGET_SKYLIGHT_INTENSITY)
        and skylight["real_time_capture"] is True
        and skylight["lower_hemisphere_is_black"] is False
        and _vector_close(
            skylight["lower_hemisphere_color"], TARGET_LOWER_HEMISPHERE, 1e-4
        )
        and skylight["affects_world"] is True
    )


def _apply_after(directional_actor, skylight_actor):
    directional = directional_actor.get_component_by_class(unreal.DirectionalLightComponent)
    skylight = skylight_actor.get_component_by_class(unreal.SkyLightComponent)
    directional_actor.set_actor_rotation(
        unreal.Rotator(
            pitch=TARGET_ROTATION[0],
            yaw=TARGET_ROTATION[1],
            roll=TARGET_ROTATION[2],
        ),
        False,
    )
    directional.set_editor_property("intensity", TARGET_DIRECTIONAL_INTENSITY)
    directional.set_editor_property("temperature", TARGET_DIRECTIONAL_TEMPERATURE)
    skylight.set_editor_property("intensity", TARGET_SKYLIGHT_INTENSITY)
    skylight.set_editor_property("lower_hemisphere_is_black", False)
    skylight.set_editor_property(
        "lower_hemisphere_color", unreal.LinearColor(*TARGET_LOWER_HEMISPHERE)
    )


def _restore(directional_actor, skylight_actor, snapshot):
    directional = directional_actor.get_component_by_class(unreal.DirectionalLightComponent)
    skylight = skylight_actor.get_component_by_class(unreal.SkyLightComponent)
    rotation = snapshot["directional"]["rotation"]
    directional_actor.set_actor_rotation(
        unreal.Rotator(pitch=rotation[0], yaw=rotation[1], roll=rotation[2]),
        False,
    )
    directional.set_editor_property("intensity", snapshot["directional"]["intensity"])
    directional.set_editor_property("temperature", snapshot["directional"]["temperature"])
    skylight.set_editor_property("intensity", snapshot["skylight"]["intensity"])
    skylight.set_editor_property(
        "lower_hemisphere_is_black",
        snapshot["skylight"]["lower_hemisphere_is_black"],
    )
    skylight.set_editor_property(
        "lower_hemisphere_color",
        unreal.LinearColor(*snapshot["skylight"]["lower_hemisphere_color"]),
    )


if MODE not in {"dry_run", "apply", "rollback"}:
    raise RuntimeError("Invalid landing daylight-pass mode")
if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The landing daylight pass is connected to the wrong project")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not world.get_path_name().startswith(EXPECTED_MAP + "."):
    raise RuntimeError("The landing daylight pass requires the Enclave main level")

exposure_receipt = _require_receipt(
    "enclave_landing_exposure_repair_v1_receipt.json", EXPOSURE_RECEIPT_SHA256
)
review_receipt = _require_receipt(
    "enclave_landing_review_capture_v2_receipt.json", REVIEW_V2_RECEIPT_SHA256
)
receipt_path = _evidence_path(RECEIPT_NAME)
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
directional_actor = _find_exact(
    actor_subsystem, DIRECTIONAL_GUID, "DirectionalLight", "DirectionalLight"
)
skylight_actor = _find_exact(actor_subsystem, SKYLIGHT_GUID, "SkyLight", "SkyLight")
current = _snapshot(directional_actor, skylight_actor)

if MODE == "dry_run":
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-daylight-pass/v1",
        "mode": MODE,
        "will_mutate": False,
        "eligible_to_apply": _is_original(current) or _is_failed_positional_restore(current) or (
            os.path.isfile(receipt_path) and _is_after(current)
        ),
        "current": current,
        "planned": {
            "directional_rotation": list(TARGET_ROTATION),
            "directional_intensity": TARGET_DIRECTIONAL_INTENSITY,
            "directional_temperature": TARGET_DIRECTIONAL_TEMPERATURE,
            "skylight_intensity": TARGET_SKYLIGHT_INTENSITY,
            "lower_hemisphere_is_black": False,
            "lower_hemisphere_color": list(TARGET_LOWER_HEMISPHERE),
        },
        "receipt_path": receipt_path,
        "prerequisites": {
            "exposure_receipt": exposure_receipt,
            "review_v2_receipt": review_receipt,
        },
    })

elif MODE == "apply":
    if os.path.isfile(receipt_path):
        with open(receipt_path, "r", encoding="utf-8") as stream:
            receipt = json.load(stream)
        if (
            receipt.get("schema") != "mcpstudio.enclave-landing-daylight-pass-receipt/v1"
            or receipt.get("target_map") != EXPECTED_MAP
            or not _is_after(current)
        ):
            raise RuntimeError("The daylight-pass receipt or scene state drifted")
        idempotent = True
    else:
        recovered_failed_positional_restore = None
        if _is_failed_positional_restore(current):
            recovered_failed_positional_restore = current
            canonical_original = json.loads(json.dumps(current))
            canonical_original["directional"]["rotation"] = list(ORIGINAL_ROTATION)
            _restore(directional_actor, skylight_actor, canonical_original)
            current = _snapshot(directional_actor, skylight_actor)
            if not _is_original(current):
                raise RuntimeError("The failed positional daylight rotation could not be recovered")
        if not _is_original(current):
            raise RuntimeError("The audited daylight state no longer matches the original")
        _apply_after(directional_actor, skylight_actor)
        after = _snapshot(directional_actor, skylight_actor)
        if not _is_after(after):
            _restore(directional_actor, skylight_actor, current)
            raise RuntimeError("The landing daylight pass did not verify")
        if not unreal.EditorLevelLibrary.save_current_level():
            _restore(directional_actor, skylight_actor, current)
            raise RuntimeError("Could not save the Enclave main level after daylight pass")
        receipt = {
            "schema": "mcpstudio.enclave-landing-daylight-pass-receipt/v1",
            "target_map": EXPECTED_MAP,
            "exposure_receipt_sha256": EXPOSURE_RECEIPT_SHA256,
            "review_v2_receipt_sha256": REVIEW_V2_RECEIPT_SHA256,
            "before": current,
            "after": after,
            "recovered_failed_positional_restore": recovered_failed_positional_restore,
        }
        receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with open(receipt_path, "xb") as stream:
            stream.write(receipt_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        idempotent = False
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-daylight-pass/v1",
        "mode": MODE,
        "idempotent_replay": idempotent,
        "receipt_path": receipt_path,
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "before": receipt["before"],
        "after": receipt["after"],
    })

else:
    if not os.path.isfile(receipt_path):
        raise RuntimeError("The daylight-pass receipt is required for rollback")
    with open(receipt_path, "r", encoding="utf-8") as stream:
        receipt = json.load(stream)
    if (
        receipt.get("schema") != "mcpstudio.enclave-landing-daylight-pass-receipt/v1"
        or receipt.get("target_map") != EXPECTED_MAP
        or not _is_after(current)
    ):
        raise RuntimeError("The daylight state is not eligible for exact rollback")
    _restore(directional_actor, skylight_actor, receipt["before"])
    restored = _snapshot(directional_actor, skylight_actor)
    if not _is_original(restored):
        raise RuntimeError("The daylight rollback did not restore the original state")
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("Could not save the Enclave main level after daylight rollback")
    rollback_path = _evidence_path(ROLLBACK_NAME)
    rollback = {
        "schema": "mcpstudio.enclave-landing-daylight-pass-rollback/v1",
        "target_map": EXPECTED_MAP,
        "restored": restored,
        "source_receipt_sha256": _sha256(receipt_path),
    }
    with open(rollback_path, "x", encoding="utf-8") as stream:
        json.dump(rollback, stream, indent=2, sort_keys=True)
        stream.write("\n")
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-daylight-pass/v1",
        "mode": MODE,
        "idempotent_replay": False,
        "rollback_path": rollback_path,
        "restored": restored,
    })
