import hashlib
import json
import os
import unreal


MODE = globals().get("MCPSTUDIO_MODE", "dry_run")
REVIEW_REVISION = globals().get("MCPSTUDIO_REVIEW_REVISION", "v1")
EXPECTED_PROJECT = "EnclaveProject"
EXPECTED_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
GROUND_RECEIPT = "MCPStudio/evidence/enclave_landing_ground_refine_v1_receipt.json"
GROUND_RECEIPT_SHA256 = "0a33afab2f32dab240967763bffe2058e640341e86379c3ee7902d0c7ef6c926"
SCALE_RECEIPT = "MCPStudio/evidence/enclave_landing_scale_bake_v2_repair_receipt.json"
SCALE_RECEIPT_SHA256 = "43469989da0beeae95bce2364b645e7a3fc9e57cbdb5a3da6d6b8d35f266a549"
EXPOSURE_RECEIPT = "MCPStudio/evidence/enclave_landing_exposure_repair_v1_receipt.json"
EXPOSURE_RECEIPT_SHA256 = "cc723c0caf8d73b52bca79a3667f1cf53fb4f9f3f8e02c38bee757130d4c03f3"
DAYLIGHT_RECEIPT = "MCPStudio/evidence/enclave_landing_daylight_pass_v1_receipt.json"
DAYLIGHT_RECEIPT_SHA256 = "92b859eccd97a8040491913f15262c6f87b873dd3f89ffb7f240adde7b48b84e"
if REVIEW_REVISION not in {"v1", "v2", "v3"}:
    raise RuntimeError("Invalid landing review revision")
RECEIPT_NAME = "enclave_landing_review_capture_" + REVIEW_REVISION + "_receipt.json"
TAG = "MCPStudioLandingReview" + REVIEW_REVISION.upper()
OUTPUT_LEAF = "landing-review-" + REVIEW_REVISION
RECEIPT_SCHEMA = "mcpstudio.enclave-landing-review-capture-receipt/" + REVIEW_REVISION

CAMERAS_V1 = (
    {
        "key": "wide",
        "label": "MCP_LandingReview_Wide_v1",
        "location": (-14500.0, -12000.0, 5800.0),
        "target": (-3200.0, 500.0, 550.0),
        "fov": 56.0,
        "filename": "landing_review_wide_v1.png",
    },
    {
        "key": "mid",
        "label": "MCP_LandingReview_Mid_v1",
        "location": (-11000.0, -6500.0, 2800.0),
        "target": (-4000.0, 400.0, 500.0),
        "fov": 50.0,
        "filename": "landing_review_mid_v1.png",
    },
    {
        "key": "entry",
        "label": "MCP_LandingReview_Entry_v1",
        "location": (-9300.0, 500.0, 1500.0),
        "target": (-3800.0, 500.0, 650.0),
        "fov": 45.0,
        "filename": "landing_review_entry_v1.png",
    },
)
CAMERAS_V2 = (
    {
        "key": "wide",
        "label": "MCP_LandingReview_Wide_v2",
        "location": (-14500.0, -12000.0, 5800.0),
        "target": (-3200.0, 500.0, 550.0),
        "fov": 56.0,
        "filename": "landing_review_wide_v2.png",
    },
    {
        "key": "mid",
        "label": "MCP_LandingReview_Mid_v2",
        "location": (-12000.0, -10000.0, 3600.0),
        "target": (-2800.0, 500.0, 550.0),
        "fov": 48.0,
        "filename": "landing_review_mid_v2.png",
    },
    {
        "key": "entry",
        "label": "MCP_LandingReview_Entry_v2",
        "location": (-9300.0, 500.0, 1500.0),
        "target": (-3800.0, 500.0, 650.0),
        "fov": 45.0,
        "filename": "landing_review_entry_v2.png",
    },
)
CAMERAS_V3 = tuple(
    {
        **spec,
        "label": spec["label"].replace("_v2", "_v3"),
        "filename": spec["filename"].replace("_v2.png", "_v3.png"),
    }
    for spec in CAMERAS_V2
)
CAMERAS = (
    CAMERAS_V3
    if REVIEW_REVISION == "v3"
    else CAMERAS_V2
    if REVIEW_REVISION == "v2"
    else CAMERAS_V1
)
CAPTURE_MODE_TO_KEY = {
    "capture_wide": "wide",
    "capture_mid": "mid",
    "capture_entry": "entry",
}
POSITION_MODE_TO_KEY = {
    "position_wide": "wide",
    "position_mid": "mid",
    "position_entry": "entry",
}
RENDER_MODE_TO_KEY = {
    "render_wide": "wide",
    "render_mid": "mid",
    "render_entry": "entry",
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


def _close_vector(value, expected, tolerance=0.1):
    return all(
        abs(float(component) - float(target)) <= tolerance
        for component, target in zip((value.x, value.y, value.z), expected)
    )


def _close_rotation(value, expected, tolerance=0.1):
    return all(
        abs(float(component) - float(target)) <= tolerance
        for component, target in zip(
            (value.pitch, value.yaw, value.roll),
            (expected.pitch, expected.yaw, expected.roll),
        )
    )


def _receipt_path(name):
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    evidence = os.path.realpath(os.path.join(saved, "MCPStudio", "evidence"))
    os.makedirs(evidence, exist_ok=True)
    return os.path.join(evidence, name)


def _require_receipt(relative_path, expected_sha256):
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    path = os.path.realpath(os.path.join(saved, relative_path))
    if not os.path.isfile(path) or _sha256(path) != expected_sha256:
        raise RuntimeError("A required landing review prerequisite receipt is missing or drifted")
    return path


def _expected_rotation(spec):
    location = unreal.Vector(*spec["location"])
    target = unreal.Vector(*spec["target"])
    return unreal.MathLibrary.find_look_at_rotation(location, target)


def _camera_record(spec, actor):
    rotation = _expected_rotation(spec)
    return {
        "key": spec["key"],
        "label": spec["label"],
        "actor_guid": _guid(actor),
        "location": list(spec["location"]),
        "target": list(spec["target"]),
        "rotation": [float(rotation.pitch), float(rotation.yaw), float(rotation.roll)],
        "fov": spec["fov"],
    }


def _verified_capture(item, expected_paths):
    path = os.path.realpath(str(item.get("path", "")))
    expected = expected_paths.get(item.get("key"))
    if expected is None or os.path.normcase(path) != os.path.normcase(expected):
        return False
    if not os.path.isfile(path):
        return False
    size = os.path.getsize(path)
    return (
        size > 0
        and item.get("capture_bytes") == size
        and item.get("capture_sha256") == _sha256(path)
    )


if MODE not in {
    "dry_run",
    "apply",
    "prepare_native_capture",
    "finalize",
    "rollback",
    *CAPTURE_MODE_TO_KEY,
    *POSITION_MODE_TO_KEY,
    *RENDER_MODE_TO_KEY,
}:
    raise RuntimeError("Invalid landing review capture mode")
if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The landing review capture is connected to the wrong project")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not world.get_path_name().startswith(EXPECTED_MAP + "."):
    raise RuntimeError("The landing review capture requires the Enclave main level")

_require_receipt(GROUND_RECEIPT, GROUND_RECEIPT_SHA256)
_require_receipt(SCALE_RECEIPT, SCALE_RECEIPT_SHA256)
if REVIEW_REVISION in {"v2", "v3"}:
    _require_receipt(EXPOSURE_RECEIPT, EXPOSURE_RECEIPT_SHA256)
if REVIEW_REVISION == "v3":
    _require_receipt(DAYLIGHT_RECEIPT, DAYLIGHT_RECEIPT_SHA256)
receipt_path = _receipt_path(RECEIPT_NAME)
output_dir = os.path.realpath(os.path.join(
    unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()),
    "MCPStudio", "evidence", OUTPUT_LEAF,
))
os.makedirs(output_dir, exist_ok=True)
expected_capture_paths = {
    spec["key"]: os.path.realpath(os.path.join(output_dir, spec["filename"]))
    for spec in CAMERAS
}
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
actors = list(actor_subsystem.get_all_level_actors())
by_label = {actor.get_actor_label(): actor for actor in actors}


def _validated_camera(spec):
    actor = by_label.get(spec["label"])
    if actor is None:
        return None, "missing"
    tags = {str(value) for value in actor.tags}
    if actor.get_class().get_name() != "CameraActor" or TAG not in tags:
        return actor, "collision"
    component = actor.get_component_by_class(unreal.CameraComponent)
    if component is None:
        return actor, "missing_component"
    if not _close_vector(actor.get_actor_location(), spec["location"]):
        return actor, "location_drift"
    if not _close_rotation(actor.get_actor_rotation(), _expected_rotation(spec)):
        return actor, "rotation_drift"
    if abs(float(component.get_editor_property("field_of_view")) - spec["fov"]) > 0.01:
        return actor, "fov_drift"
    return actor, "trusted"


if MODE == "dry_run":
    reusable = []
    collisions = []
    drifted = []
    missing = []
    for spec in CAMERAS:
        actor, status = _validated_camera(spec)
        if status == "trusted":
            reusable.append(spec["label"])
        elif status == "collision":
            collisions.append(spec["label"])
        elif status == "missing":
            missing.append(spec["label"])
        else:
            drifted.append({"label": spec["label"], "reason": status})
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-review-capture/v1",
        "mode": MODE,
        "will_mutate": False,
        "camera_specs": CAMERAS,
        "reusable_camera_labels": reusable,
        "missing_camera_labels": missing,
        "drifted_cameras": drifted,
        "label_collisions": collisions,
        "eligible_to_apply": not collisions,
        "receipt_path": receipt_path,
        "output_directory": output_dir,
        "expected_capture_paths": expected_capture_paths,
    })

elif MODE == "apply":
    collisions = []
    review_cameras = []
    created = []
    try:
        for spec in CAMERAS:
            actor = by_label.get(spec["label"])
            if actor is not None:
                tags = {str(value) for value in actor.tags}
                if actor.get_class().get_name() != "CameraActor" or TAG not in tags:
                    collisions.append(spec["label"])
                    continue
            else:
                actor = actor_subsystem.spawn_actor_from_class(
                    unreal.CameraActor,
                    unreal.Vector(*spec["location"]),
                    _expected_rotation(spec),
                )
                if actor is None:
                    raise RuntimeError("Could not create landing review camera: " + spec["label"])
                actor.set_actor_label(spec["label"], mark_dirty=True)
                actor.tags = [unreal.Name(TAG)]
                actor.set_actor_hidden_in_game(True)
                created.append(actor)
            actor.set_actor_location(unreal.Vector(*spec["location"]), False, False)
            actor.set_actor_rotation(_expected_rotation(spec), False)
            component = actor.get_component_by_class(unreal.CameraComponent)
            component.set_editor_property("field_of_view", spec["fov"])
            review_cameras.append((spec, actor))
        if collisions:
            raise RuntimeError("Landing review camera label collision: " + ", ".join(collisions))
        packages = [actor.get_outermost() for _spec, actor in review_cameras]
        if not unreal.EditorLoadingAndSavingUtils.save_packages(packages, False):
            raise RuntimeError("Could not persist landing review cameras")
        if not unreal.EditorLevelLibrary.save_current_level():
            raise RuntimeError("Could not save the Enclave main level with review cameras")
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-landing-review-capture/v1",
            "mode": MODE,
            "setup_complete": True,
            "created_camera_labels": [actor.get_actor_label() for actor in created],
            "cameras": [_camera_record(spec, actor) for spec, actor in review_cameras],
            "receipt_path": receipt_path,
            "expected_capture_paths": expected_capture_paths,
        })
    except Exception:
        for actor in reversed(created):
            actor_subsystem.destroy_actor(actor)
        if created:
            unreal.EditorLevelLibrary.save_current_level()
        raise

elif MODE == "prepare_native_capture":
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if level_editor is None:
        raise RuntimeError("LevelEditorSubsystem is unavailable for landing review preparation")
    viewport_key = level_editor.get_active_viewport_config_key()
    level_editor.eject_pilot_level_actor(viewport_key)
    level_editor.editor_set_viewport_realtime(True, viewport_key)
    level_editor.editor_invalidate_viewports()
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-review-capture/v1",
        "mode": MODE,
        "prepared": True,
        "viewport_config_key": str(viewport_key),
    })

elif MODE in POSITION_MODE_TO_KEY:
    position_key = POSITION_MODE_TO_KEY[MODE]
    spec = next(item for item in CAMERAS if item["key"] == position_key)
    level_editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if level_editor is None:
        raise RuntimeError("LevelEditorSubsystem is unavailable for landing review positioning")
    unreal_editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if unreal_editor is None:
        raise RuntimeError("UnrealEditorSubsystem is unavailable for landing review positioning")
    viewport_key = level_editor.get_active_viewport_config_key()
    expected_location = unreal.Vector(*spec["location"])
    expected_rotation = _expected_rotation(spec)
    level_editor.eject_pilot_level_actor(viewport_key)
    unreal_editor.set_level_viewport_camera_info(
        expected_location,
        expected_rotation,
    )
    level_editor.editor_invalidate_viewports()
    observed = unreal_editor.get_level_viewport_camera_info()
    if observed is None or len(observed) != 2:
        raise RuntimeError("Landing review viewport position could not be observed: " + position_key)
    observed_location, observed_rotation = observed
    if not _close_vector(observed_location, spec["location"]):
        raise RuntimeError("Landing review viewport location drifted: " + position_key)
    if not _close_rotation(observed_rotation, expected_rotation):
        raise RuntimeError("Landing review viewport rotation drifted: " + position_key)
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-review-capture/v1",
        "mode": MODE,
        "positioned": True,
        "capture_key": position_key,
        "viewport_config_key": str(viewport_key),
        "observed_location": [
            float(observed_location.x),
            float(observed_location.y),
            float(observed_location.z),
        ],
        "observed_rotation": [
            float(observed_rotation.pitch),
            float(observed_rotation.yaw),
            float(observed_rotation.roll),
        ],
    })

elif MODE in RENDER_MODE_TO_KEY:
    render_key = RENDER_MODE_TO_KEY[MODE]
    spec = next(item for item in CAMERAS if item["key"] == render_key)
    actor, status = _validated_camera(spec)
    if status != "trusted":
        raise RuntimeError("Landing review camera is not exact during render: " + spec["label"])
    screenshot_path = expected_capture_paths[render_key]
    if os.path.isfile(screenshot_path):
        os.remove(screenshot_path)
    capture_actor = None
    render_target = None
    try:
        capture_actor = actor_subsystem.spawn_actor_from_class(
            unreal.SceneCapture2D,
            unreal.Vector(*spec["location"]),
            _expected_rotation(spec),
        )
        if capture_actor is None:
            raise RuntimeError("Could not create transient landing review scene capture")
        capture_component = capture_actor.get_component_by_class(
            unreal.SceneCaptureComponent2D
        )
        if capture_component is None:
            raise RuntimeError("Landing review scene capture component is unavailable")
        render_target = unreal.RenderingLibrary.create_render_target2d(
            world,
            1600,
            900,
            unreal.TextureRenderTargetFormat.RTF_RGBA8,
            unreal.LinearColor(0.0, 0.0, 0.0, 1.0),
            False,
            False,
        )
        if render_target is None:
            raise RuntimeError("Could not create landing review render target")
        capture_component.set_editor_property("capture_every_frame", False)
        capture_component.set_editor_property("capture_on_movement", False)
        capture_component.set_editor_property("fov_angle", spec["fov"])
        capture_component.set_editor_property(
            "capture_source",
            unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR,
        )
        capture_component.set_editor_property("texture_target", render_target)
        capture_component.capture_scene()
        unreal.RenderingLibrary.export_render_target(
            world,
            render_target,
            output_dir,
            spec["filename"],
        )
        if not os.path.isfile(screenshot_path) or os.path.getsize(screenshot_path) <= 0:
            raise RuntimeError("Landing review scene render was not exported: " + render_key)
        _result.update({
            "schema": "unreal_mcp_ghost.enclave-landing-review-capture/v1",
            "mode": MODE,
            "rendered": True,
            "capture_key": render_key,
            "capture_path": screenshot_path,
            "capture_bytes": os.path.getsize(screenshot_path),
            "capture_sha256": _sha256(screenshot_path),
            "fov": spec["fov"],
        })
    finally:
        if capture_actor is not None:
            component = capture_actor.get_component_by_class(unreal.SceneCaptureComponent2D)
            if component is not None:
                component.set_editor_property("texture_target", None)
        if render_target is not None:
            unreal.RenderingLibrary.release_render_target2d(render_target)
        if capture_actor is not None:
            actor_subsystem.destroy_actor(capture_actor)

elif MODE in CAPTURE_MODE_TO_KEY:
    capture_key = CAPTURE_MODE_TO_KEY[MODE]
    spec = next(item for item in CAMERAS if item["key"] == capture_key)
    actor, status = _validated_camera(spec)
    if status != "trusted":
        raise RuntimeError("Landing review camera is not exact during capture: " + spec["label"])
    screenshot_path = expected_capture_paths[capture_key]
    if os.path.isfile(screenshot_path):
        os.remove(screenshot_path)
    unreal.AutomationLibrary.finish_loading_before_screenshot()
    task = unreal.AutomationLibrary.take_high_res_screenshot(
        1600,
        900,
        screenshot_path,
        actor,
        False,
        False,
        unreal.ComparisonTolerance.LOW,
        "MCPStudio Enclave landing review " + capture_key,
        0.5,
        True,
    )
    if task is None or not task.is_valid_task():
        raise RuntimeError("Unreal did not enqueue the landing review capture: " + capture_key)
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-review-capture/v1",
        "mode": MODE,
        "capture_key": capture_key,
        "capture_path": screenshot_path,
        "submitted": True,
    })

elif MODE == "finalize":
    review_cameras = []
    for spec in CAMERAS:
        actor, status = _validated_camera(spec)
        if status != "trusted":
            raise RuntimeError("Landing review camera is not exact during finalize: " + spec["label"])
        review_cameras.append((spec, actor))
    captures = []
    for spec in CAMERAS:
        path = expected_capture_paths[spec["key"]]
        if not os.path.isfile(path):
            raise RuntimeError("Landing review capture is missing: " + spec["key"])
        capture_bytes = os.path.getsize(path)
        if capture_bytes <= 0:
            raise RuntimeError("Landing review capture is empty: " + spec["key"])
        captures.append({
            "key": spec["key"],
            "path": path,
            "capture_bytes": capture_bytes,
            "capture_sha256": _sha256(path),
        })
    outputs = {
        "output_directory": output_dir,
        "captures": captures,
        "cameras": [_camera_record(spec, actor) for spec, actor in review_cameras],
    }
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "target_map": EXPECTED_MAP,
        "outputs": outputs,
    }
    receipt_bytes = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
    idempotent = False
    superseded_receipt_path = None
    if os.path.isfile(receipt_path):
        with open(receipt_path, "rb") as stream:
            existing = stream.read()
        existing_receipt = json.loads(existing.decode("utf-8"))
        existing_captures = existing_receipt.get("outputs", {}).get("captures", [])
        if (
            existing_receipt.get("schema") == receipt["schema"]
            and len(existing_captures) == len(CAMERAS)
            and all(_verified_capture(item, expected_capture_paths) for item in existing_captures)
        ):
            receipt_bytes = existing
            outputs = existing_receipt["outputs"]
            idempotent = True
        else:
            expected_keys = {spec["key"] for spec in CAMERAS}
            existing_keys = {item.get("key") for item in existing_captures}
            existing_hashes = {
                item.get("capture_sha256") for item in existing_captures
            }
            current_hashes = {item["capture_sha256"] for item in captures}
            existing_contract = (
                existing_receipt.get("schema") == receipt["schema"]
                and existing_receipt.get("target_map") == EXPECTED_MAP
                and len(existing_captures) == len(CAMERAS)
                and existing_keys == expected_keys
                and all(
                    os.path.normcase(os.path.realpath(str(item.get("path", ""))))
                    == os.path.normcase(expected_capture_paths[item["key"]])
                    and isinstance(item.get("capture_bytes"), int)
                    and item.get("capture_bytes") > 0
                    and isinstance(item.get("capture_sha256"), str)
                    and len(item.get("capture_sha256")) == 64
                    for item in existing_captures
                )
            )
            if (
                existing_contract
                and len(existing_hashes) == 1
                and len(current_hashes) == len(CAMERAS)
            ):
                superseded_receipt_path = _receipt_path(
                    "enclave_landing_review_capture_"
                    + REVIEW_REVISION
                    + "_superseded_identical_views.json"
                )
                superseded = {
                    "schema": "mcpstudio.enclave-landing-review-capture-superseded/v1",
                    "superseded_reason": "identical-capture-hashes",
                    "original_receipt_sha256": hashlib.sha256(existing).hexdigest(),
                    "original_receipt": existing_receipt,
                }
                superseded_bytes = (
                    json.dumps(superseded, indent=2, sort_keys=True) + "\n"
                ).encode("utf-8")
                if os.path.isfile(superseded_receipt_path):
                    with open(superseded_receipt_path, "rb") as stream:
                        if stream.read() != superseded_bytes:
                            raise RuntimeError("The superseded landing review receipt drifted")
                else:
                    with open(superseded_receipt_path, "xb") as stream:
                        stream.write(superseded_bytes)
                replacement_path = receipt_path + ".replacement.pending"
                with open(replacement_path, "xb") as stream:
                    stream.write(receipt_bytes)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(replacement_path, receipt_path)
            else:
                raise RuntimeError("The existing landing review receipt is not verified")
    else:
        with open(receipt_path, "xb") as stream:
            stream.write(receipt_bytes)
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-review-capture/v1",
        "mode": MODE,
        "idempotent_replay": idempotent,
        "receipt_path": receipt_path,
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "superseded_receipt_path": superseded_receipt_path,
        "outputs": outputs,
    })

else:
    if not os.path.isfile(receipt_path):
        raise RuntimeError("The landing review capture receipt is required before rollback")
    with open(receipt_path, "r", encoding="utf-8") as stream:
        receipt = json.load(stream)
    current = {_guid(actor): actor for actor in actor_subsystem.get_all_level_actors()}
    removed = []
    for item in receipt.get("outputs", {}).get("cameras", []):
        actor = current.get(item.get("actor_guid"))
        if actor is not None:
            actor_subsystem.destroy_actor(actor)
            removed.append(item.get("label"))
    if not unreal.EditorLevelLibrary.save_current_level():
        raise RuntimeError("Could not save the Enclave level after review-camera rollback")
    rollback_path = _receipt_path(
        "enclave_landing_review_capture_" + REVIEW_REVISION + "_rollback.json"
    )
    rollback = {
        "schema": "mcpstudio.enclave-landing-review-capture-rollback/v1",
        "removed_camera_labels": removed,
    }
    with open(rollback_path, "x", encoding="utf-8") as stream:
        json.dump(rollback, stream, indent=2, sort_keys=True)
        stream.write("\n")
    _result.update({
        "schema": "unreal_mcp_ghost.enclave-landing-review-capture/v1",
        "mode": MODE,
        "idempotent_replay": False,
        "rollback_path": rollback_path,
        "outputs": rollback,
    })
