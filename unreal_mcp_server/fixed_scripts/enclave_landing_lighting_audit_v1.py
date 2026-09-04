import hashlib
import json
import os
import unreal


EXPECTED_PROJECT = "EnclaveProject"
EXPECTED_MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"
GROUND_RECEIPT = "MCPStudio/evidence/enclave_landing_ground_refine_v1_receipt.json"
GROUND_RECEIPT_SHA256 = "0a33afab2f32dab240967763bffe2058e640341e86379c3ee7902d0c7ef6c926"
SCALE_RECEIPT = "MCPStudio/evidence/enclave_landing_scale_bake_v2_repair_receipt.json"
SCALE_RECEIPT_SHA256 = "43469989da0beeae95bce2364b645e7a3fc9e57cbdb5a3da6d6b8d35f266a549"
MAX_CONTEXT_ACTORS = 128
CONTEXT_CLASSES = {
    "DirectionalLight",
    "ExponentialHeightFog",
    "PointLight",
    "PostProcessVolume",
    "RectLight",
    "SkyAtmosphere",
    "SkyLight",
    "SpotLight",
    "VolumetricCloud",
}

COMMON_LIGHT_PROPERTIES = (
    "intensity",
    "light_color",
    "affects_world",
    "cast_shadows",
    "cast_static_shadows",
    "cast_dynamic_shadows",
    "use_temperature",
    "temperature",
    "indirect_lighting_intensity",
    "volumetric_scattering_intensity",
)
DIRECTIONAL_PROPERTIES = (
    "atmosphere_sun_light",
    "atmosphere_sun_light_index",
    "light_source_angle",
    "light_source_soft_angle",
    "dynamic_shadow_distance_movable_light",
    "cloud_shadow_strength",
    "cloud_shadow_on_atmosphere_strength",
)
SKYLIGHT_PROPERTIES = (
    "intensity",
    "light_color",
    "source_type",
    "cubemap",
    "source_cubemap_angle",
    "real_time_capture",
    "lower_hemisphere_is_black",
    "lower_hemisphere_color",
    "cast_shadows",
    "affects_world",
    "indirect_lighting_intensity",
    "volumetric_scattering_intensity",
)
SKY_ATMOSPHERE_PROPERTIES = (
    "transform_mode",
    "bottom_radius",
    "ground_albedo",
    "atmosphere_height",
    "multi_scattering_factor",
    "rayleigh_scattering_scale",
    "rayleigh_scattering",
    "rayleigh_exponential_distribution",
    "mie_scattering_scale",
    "mie_scattering",
    "mie_absorption_scale",
    "mie_absorption",
    "mie_anisotropy",
    "mie_exponential_distribution",
)
FOG_PROPERTIES = (
    "fog_density",
    "fog_height_falloff",
    "fog_inscattering_color",
    "fog_max_opacity",
    "start_distance",
    "fog_cutoff_distance",
    "directional_inscattering_exponent",
    "directional_inscattering_start_distance",
    "directional_inscattering_color",
    "volumetric_fog",
    "volumetric_fog_scattering_distribution",
    "volumetric_fog_albedo",
    "volumetric_fog_emissive",
    "volumetric_fog_extinction_scale",
    "volumetric_fog_distance",
)
POST_PROCESS_PROPERTIES = (
    "override_auto_exposure_method",
    "auto_exposure_method",
    "override_auto_exposure_min_brightness",
    "auto_exposure_min_brightness",
    "override_auto_exposure_max_brightness",
    "auto_exposure_max_brightness",
    "override_auto_exposure_bias",
    "auto_exposure_bias",
    "override_auto_exposure_speed_up",
    "auto_exposure_speed_up",
    "override_auto_exposure_speed_down",
    "auto_exposure_speed_down",
    "override_local_exposure_highlight_contrast_scale",
    "local_exposure_highlight_contrast_scale",
    "override_local_exposure_shadow_contrast_scale",
    "local_exposure_shadow_contrast_scale",
    "override_color_saturation",
    "color_saturation",
    "override_color_contrast",
    "color_contrast",
    "override_color_gamma",
    "color_gamma",
    "override_color_gain",
    "color_gain",
    "override_color_offset",
    "color_offset",
)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_receipt(relative_path, expected_sha256):
    saved = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())
    path = os.path.realpath(os.path.join(saved, relative_path))
    if not os.path.isfile(path) or _sha256(path) != expected_sha256:
        raise RuntimeError("A required landing lighting-audit prerequisite is missing or drifted")
    return path


def _class_name(value):
    try:
        return value.get_class().get_name()
    except Exception:
        return type(value).__name__


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


def _value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "r") and hasattr(value, "g") and hasattr(value, "b"):
        result = {"r": float(value.r), "g": float(value.g), "b": float(value.b)}
        if hasattr(value, "a"):
            result["a"] = float(value.a)
        return result
    if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z"):
        return {"x": float(value.x), "y": float(value.y), "z": float(value.z)}
    if hasattr(value, "get_path_name"):
        try:
            return value.get_path_name()
        except Exception:
            pass
    text = str(value)
    if len(text) > 512:
        text = text[:512] + "..."
    return text


def _read_properties(target, names):
    observed = {}
    unavailable = []
    if target is None:
        return observed, list(names)
    for name in names:
        try:
            observed[name] = _value(target.get_editor_property(name))
        except Exception:
            unavailable.append(name)
    return observed, unavailable


def _transform(actor):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return {
        "location": [float(location.x), float(location.y), float(location.z)],
        "rotation": [float(rotation.pitch), float(rotation.yaw), float(rotation.roll)],
        "scale": [float(scale.x), float(scale.y), float(scale.z)],
    }


def _component_record(component, properties):
    observed, unavailable = _read_properties(component, properties)
    return {
        "class": _class_name(component) if component is not None else None,
        "properties": observed,
        "unavailable_properties": unavailable,
    }


def _dirty_map_paths():
    packages = unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    return sorted(package.get_path_name() for package in packages if package is not None)


if unreal.SystemLibrary.get_game_name() != EXPECTED_PROJECT:
    raise RuntimeError("The landing lighting audit is connected to the wrong project")
world = unreal.EditorLevelLibrary.get_editor_world()
if world is None or not world.get_path_name().startswith(EXPECTED_MAP + "."):
    raise RuntimeError("The landing lighting audit requires the Enclave main level")

ground_receipt = _require_receipt(GROUND_RECEIPT, GROUND_RECEIPT_SHA256)
scale_receipt = _require_receipt(SCALE_RECEIPT, SCALE_RECEIPT_SHA256)
world_package_path = world.get_outermost().get_path_name()
dirty_map_paths_before = _dirty_map_paths()
package_dirty_before = world_package_path in dirty_map_paths_before
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
all_actors = list(actor_subsystem.get_all_level_actors())
context_actors = [actor for actor in all_actors if _class_name(actor) in CONTEXT_CLASSES]
context_actors.sort(key=lambda actor: (_class_name(actor), actor.get_actor_label(), actor.get_path_name()))
truncated = len(context_actors) > MAX_CONTEXT_ACTORS
records = []
class_counts = {}

for actor in context_actors[:MAX_CONTEXT_ACTORS]:
    class_name = _class_name(actor)
    class_counts[class_name] = class_counts.get(class_name, 0) + 1
    try:
        root = actor.get_editor_property("root_component")
    except Exception:
        root = None
    root_properties, root_unavailable = _read_properties(root, ("mobility", "visible", "hidden_in_game"))
    record = {
        "label": actor.get_actor_label(),
        "path": actor.get_path_name(),
        "actor_guid": _guid(actor),
        "class": class_name,
        "transform": _transform(actor),
        "tags": sorted(str(tag) for tag in actor.tags),
        "root_component": {
            "class": _class_name(root) if root is not None else None,
            "properties": root_properties,
            "unavailable_properties": root_unavailable,
        },
    }
    if class_name == "DirectionalLight":
        component = actor.get_component_by_class(unreal.DirectionalLightComponent)
        record["lighting_component"] = _component_record(
            component, COMMON_LIGHT_PROPERTIES + DIRECTIONAL_PROPERTIES
        )
    elif class_name in {"PointLight", "SpotLight", "RectLight"}:
        light_class = {
            "PointLight": unreal.PointLightComponent,
            "SpotLight": unreal.SpotLightComponent,
            "RectLight": unreal.RectLightComponent,
        }[class_name]
        component = actor.get_component_by_class(light_class)
        record["lighting_component"] = _component_record(
            component,
            COMMON_LIGHT_PROPERTIES + (
                "attenuation_radius",
                "inverse_exposure_blend",
                "use_inverse_squared_falloff",
            ),
        )
    elif class_name == "SkyLight":
        component = actor.get_component_by_class(unreal.SkyLightComponent)
        record["skylight_component"] = _component_record(component, SKYLIGHT_PROPERTIES)
    elif class_name == "SkyAtmosphere":
        component = actor.get_component_by_class(unreal.SkyAtmosphereComponent)
        record["sky_atmosphere_component"] = _component_record(
            component, SKY_ATMOSPHERE_PROPERTIES
        )
    elif class_name == "ExponentialHeightFog":
        component = actor.get_component_by_class(unreal.ExponentialHeightFogComponent)
        record["fog_component"] = _component_record(component, FOG_PROPERTIES)
    elif class_name == "PostProcessVolume":
        volume_properties, volume_unavailable = _read_properties(
            actor, ("enabled", "unbound", "priority", "blend_radius", "blend_weight")
        )
        settings = None
        try:
            settings = actor.get_editor_property("settings")
        except Exception:
            pass
        record["post_process_volume"] = {
            "properties": volume_properties,
            "unavailable_properties": volume_unavailable,
            "settings": _component_record(settings, POST_PROCESS_PROPERTIES),
        }
    records.append(record)

dirty_map_paths_after = _dirty_map_paths()
package_dirty_after = world_package_path in dirty_map_paths_after
if dirty_map_paths_after != dirty_map_paths_before:
    raise RuntimeError("The read-only lighting audit changed the map package dirty state")

review_receipt = os.path.realpath(os.path.join(
    unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()),
    "MCPStudio/evidence/enclave_landing_review_capture_v1_receipt.json",
))
review_receipt_observation = {
    "path": review_receipt,
    "exists": os.path.isfile(review_receipt),
    "sha256": _sha256(review_receipt) if os.path.isfile(review_receipt) else None,
}

_result.update({
    "schema": "unreal_mcp_ghost.enclave-landing-lighting-audit/v1",
    "target_project": EXPECTED_PROJECT,
    "target_map": EXPECTED_MAP,
    "engine_version": unreal.SystemLibrary.get_engine_version(),
    "level_actor_count": len(all_actors),
    "matched_context_actor_count": len(context_actors),
    "returned_context_actor_count": len(records),
    "truncated": truncated,
    "class_histogram": [
        {"class": name, "count": class_counts[name]} for name in sorted(class_counts)
    ],
    "actors": records,
    "prerequisites": {
        "ground_receipt": {"path": ground_receipt, "sha256": GROUND_RECEIPT_SHA256},
        "scale_receipt": {"path": scale_receipt, "sha256": SCALE_RECEIPT_SHA256},
        "review_receipt": review_receipt_observation,
    },
    "map_package_dirty_before": package_dirty_before,
    "map_package_dirty_after": package_dirty_after,
    "dirty_map_paths_before": dirty_map_paths_before,
    "dirty_map_paths_after": dirty_map_paths_after,
    "epistemic_policy": (
        "Only explicit Unreal actor/component properties are reported; unavailable properties "
        "remain unavailable and no visual-quality conclusion is inferred by this operator."
    ),
})
