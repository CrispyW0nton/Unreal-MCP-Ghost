"""Clean-room spatial awareness tools for live Unreal Editor scenes.

These tools intentionally read editor state only. They are inspired by the
capability gap exposed by the UE 5.8 native MCP SceneTools breadcrumb, but they
do not copy Epic implementation code.
"""

from __future__ import annotations

import json
import logging
import math
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from mcp.server.fastmcp import Context

from tools.tool_registration_surface import ToolRegistrationSurface

logger = logging.getLogger("UnrealMCP.tools.spatial_awareness_tools")
_REPO_ROOT = Path(__file__).resolve().parents[2]

SPATIAL_RESULT_SCHEMA = "unreal_mcp_ghost.spatial_awareness_result.v1"
SCENE_OVERVIEW_SCHEMA = "unreal_mcp_ghost.spatial_scene_overview.v2"
SPATIAL_QUERY_SCHEMA = "unreal_mcp_ghost.spatial_query_actors.v1"
ACTOR_DESCRIPTOR_SCHEMA = "unreal_mcp_ghost.spatial_actor_descriptor.v1"
PROXIMITY_MAP_SCHEMA = "unreal_mcp_ghost.spatial_proximity_map.v1"
VIEW_CONTEXT_SCHEMA = "unreal_mcp_ghost.spatial_view_context.v1"
ACTOR_SELECTION_SCHEMA = "unreal_mcp_ghost.spatial_actor_selection.v1"
CONTENT_SELECTION_SCHEMA = "unreal_mcp_ghost.spatial_content_selection.v1"
SELECTED_ASSET_PLACEMENT_SCHEMA = "unreal_mcp_ghost.spatial_selected_asset_placement.v1"
PLACEMENT_POLICY_SCHEMA = "unreal_mcp_ghost.spatial_placement_policy.v1"
SURFACE_PROBE_SCHEMA = "unreal_mcp_ghost.spatial_surface_probe.v1"
PLACEMENT_VALIDATION_SCHEMA = "unreal_mcp_ghost.spatial_placement_validation.v1"
ASSET_PLACEMENT_SCHEMA = "unreal_mcp_ghost.spatial_asset_placement.v1"
ROOM_ANALYSIS_SCHEMA = "unreal_mcp_ghost.spatial_room_analysis.v1"
ROOM_BOUNDS_DESIGNATION_SCHEMA = "unreal_mcp_ghost.spatial_room_bounds_designation.v1"
FUNCTIONAL_ZONE_INFERENCE_SCHEMA = "unreal_mcp_ghost.spatial_functional_zone_inference.v1"
INTERIOR_PROP_PROGRAM_SCHEMA = "unreal_mcp_ghost.spatial_interior_prop_program.v1"
INTERIOR_COMPOSITION_SCHEMA = "unreal_mcp_ghost.spatial_interior_composition.v1"
SCREENSHOT_RECONSTRUCTION_SCHEMA = "unreal_mcp_ghost.spatial_screenshot_reconstruction.v1"
SCREENSHOT_DECOMPOSITION_REQUEST_SCHEMA = "unreal_mcp_ghost.spatial_screenshot_decomposition_request.v1"
SCREENSHOT_DECOMPOSITION_PREFLIGHT_SCHEMA = "unreal_mcp_ghost.spatial_screenshot_decomposition_preflight.v1"
SCREENSHOT_SCENE_GRAPH_SCHEMA = "unreal_mcp_ghost.spatial_screenshot_scene_graph.v1"
SCREENSHOT_CROP_MANIFEST_SCHEMA = "unreal_mcp_ghost.spatial_screenshot_crop_manifest.v1"
COMPOSITION_ITERATION_SCHEMA = "unreal_mcp_ghost.spatial_composition_iteration.v1"
COMPOSITION_ASSET_BINDING_SCHEMA = "unreal_mcp_ghost.spatial_composition_asset_binding.v1"
PROJECT_ASSET_CATALOG_SCHEMA = "unreal_mcp_ghost.spatial_project_asset_catalog.v1"
PROJECT_ASSET_RESOLUTION_SCHEMA = "unreal_mcp_ghost.spatial_project_asset_resolution.v1"
TRIPO_GENERATION_BATCH_SCHEMA = "unreal_mcp_ghost.spatial_tripo_generation_batch.v1"
SPATIAL_GENERATION_BRIEF_SCHEMA = "unreal_mcp_ghost.spatial_generation_brief.v1"
LAYOUT_PREFLIGHT_SCHEMA = "unreal_mcp_ghost.spatial_layout_preflight.v1"
LAYOUT_PREFLIGHT_CORRECTION_SCHEMA = "unreal_mcp_ghost.spatial_layout_preflight_correction.v1"
COMPOSITION_PLACEMENT_BATCH_SCHEMA = "unreal_mcp_ghost.spatial_composition_placement_batch.v1"
WORLDBUILDING_READINESS_SCHEMA = "unreal_mcp_ghost.spatial_worldbuilding_readiness.v1"
WORLDBUILDING_WORK_ORDER_SCHEMA = "unreal_mcp_ghost.spatial_worldbuilding_work_order.v1"
ENVIRONMENT_COHERENCE_SCHEMA = "unreal_mcp_ghost.spatial_environment_coherence.v1"
CANDIDATE_CLEARANCE_SCHEMA = "unreal_mcp_ghost.spatial_candidate_clearance.v1"
ASSET_SCALE_CORRECTION_SCHEMA = "unreal_mcp_ghost.spatial_asset_scale_correction.v1"
SUPPORT_SURFACE_ANCHOR_SCHEMA = "unreal_mcp_ghost.spatial_support_surface_anchor.v1"

ROOM_BOUNDS_TAG = "Ghost.RoomBounds"
ROOM_ID_TAG_PREFIX = "Ghost.RoomId."
ROOM_TYPE_TAG_PREFIX = "Ghost.RoomType."
ZONE_TAG_PREFIX = "Ghost.Zone."
OPENING_TAG_PREFIX = "Ghost.Opening."
CLEARANCE_TAG_PREFIX = "Ghost.Clearance."
PATH_REQUIRED_TAG = "Ghost.Path.Required"
SURFACE_TAG_PREFIX = "Ghost.Surface."

SPATIAL_FIT_READY_STATUSES = frozenset({
    "ready_for_spatial_validation",
    "ready_for_scaled_spatial_validation",
})

PLACEMENT_LAYOUTS = frozenset({"line", "grid", "stack"})
SURFACE_TRACE_CHANNELS = frozenset({"visibility", "camera"})
PLACEMENT_POLICIES = frozenset({
    "auto",
    "manual",
    "set_dressing",
    "city_block",
    "gameplay_poi",
    "lighting",
    "vfx",
    "linear_showcase",
    "vertical_stack",
    "interior_composition",
})

INTERIOR_ROOM_TYPES = frozenset({
    "apartment",
    "studio",
    "kitchen",
    "living_room",
    "bedroom",
    "bathroom",
    "hallway",
    "utility",
    "generic_room",
})

INTERIOR_PROP_LIBRARY: List[Dict[str, Any]] = [
    {"name": "refrigerator", "aliases": ["fridge", "refrigerator"], "zone": "kitchen", "category": "appliance", "priority": 10, "size": [90, 80, 190], "surface": "floor"},
    {"name": "stove and oven", "aliases": ["stove", "oven", "range"], "zone": "kitchen", "category": "appliance", "priority": 9, "size": [80, 70, 95], "surface": "floor"},
    {"name": "kitchen sink", "aliases": ["sink"], "zone": "kitchen", "category": "fixture", "priority": 9, "size": [90, 65, 95], "surface": "counter"},
    {"name": "kitchen counter run", "aliases": ["counter", "countertop", "counter run"], "zone": "kitchen", "category": "counter", "priority": 8, "size": [240, 65, 95], "surface": "floor"},
    {"name": "base cabinets", "aliases": ["base cabinet", "cabinets"], "zone": "kitchen", "category": "storage", "priority": 7, "size": [220, 60, 95], "surface": "floor"},
    {"name": "wall cabinets", "aliases": ["wall cabinet", "upper cabinet"], "zone": "kitchen", "category": "storage", "priority": 6, "size": [220, 40, 80], "surface": "wall"},
    {"name": "bar stool", "aliases": ["bar stool", "stool"], "zone": "kitchen", "category": "seating", "priority": 5, "size": [45, 45, 110], "surface": "floor"},
    {"name": "counter clutter", "aliases": ["clutter", "counter clutter", "small appliance"], "zone": "kitchen", "category": "dressing", "priority": 4, "size": [35, 25, 25], "surface": "counter"},
    {"name": "sofa", "aliases": ["couch", "sofa"], "zone": "living", "category": "seating", "priority": 9, "size": [220, 95, 90], "surface": "floor"},
    {"name": "coffee table", "aliases": ["coffee table"], "zone": "living", "category": "table", "priority": 8, "size": [110, 65, 45], "surface": "floor"},
    {"name": "bookshelf", "aliases": ["bookcase", "bookshelf"], "zone": "living", "category": "storage", "priority": 6, "size": [90, 35, 190], "surface": "floor"},
    {"name": "floor lamp", "aliases": ["lamp", "floor lamp"], "zone": "living", "category": "lighting", "priority": 5, "size": [35, 35, 170], "surface": "floor"},
    {"name": "rug", "aliases": ["rug", "carpet"], "zone": "living", "category": "dressing", "priority": 5, "size": [240, 180, 3], "surface": "floor"},
    {"name": "books and table clutter", "aliases": ["books", "magazines", "table clutter"], "zone": "living", "category": "dressing", "priority": 4, "size": [45, 35, 15], "surface": "table"},
    {"name": "bed", "aliases": ["bed"], "zone": "bedroom", "category": "furniture", "priority": 9, "size": [160, 210, 80], "surface": "floor"},
    {"name": "nightstand", "aliases": ["nightstand", "bedside table"], "zone": "bedroom", "category": "table", "priority": 6, "size": [50, 45, 55], "surface": "floor"},
    {"name": "dresser", "aliases": ["dresser", "wardrobe"], "zone": "bedroom", "category": "storage", "priority": 5, "size": [130, 55, 95], "surface": "floor"},
    {"name": "entry console", "aliases": ["entry console", "console table"], "zone": "entry", "category": "table", "priority": 4, "size": [100, 35, 85], "surface": "floor"},
    {"name": "hallway runner rug", "aliases": ["runner rug", "hallway runner", "hall rug"], "zone": "hallway", "category": "dressing", "priority": 4, "size": [260, 80, 3], "surface": "floor"},
    {"name": "wall hooks", "aliases": ["coat hooks", "wall hooks", "coat rack"], "zone": "hallway", "category": "storage", "priority": 3, "size": [90, 12, 45], "surface": "wall"},
    {"name": "shoe bench", "aliases": ["shoe bench", "bench", "hall bench"], "zone": "hallway", "category": "seating", "priority": 3, "size": [120, 40, 48], "surface": "floor"},
    {"name": "utility shelf", "aliases": ["utility shelf", "laundry shelf", "storage shelf"], "zone": "utility", "category": "storage", "priority": 5, "size": [120, 40, 180], "surface": "floor"},
    {"name": "washer dryer stack", "aliases": ["washer", "dryer", "laundry"], "zone": "utility", "category": "appliance", "priority": 6, "size": [80, 75, 190], "surface": "floor"},
]


def _exec_structured(code: str, stage_name: str) -> Dict[str, Any]:
    from tools.exec_substrate import exec_python_structured

    return exec_python_structured(code, stage_name)


def _exec_transactional(code: str, transaction_name: str) -> Dict[str, Any]:
    from tools.exec_substrate import exec_python_transactional

    return exec_python_transactional(code, transaction_name)


def _clean_asset_path(value: str) -> str:
    path = str(value or "").strip().replace("\\", "/")
    if "'" in path and path.endswith("'"):
        path = path.split("'", 1)[1].rsplit("'", 1)[0]
    while "//" in path:
        path = path.replace("//", "/")
    path = path.rstrip("/")
    if not path:
        raise ValueError("asset_path is required")
    if not path.startswith("/"):
        raise ValueError("asset_path must be a Content Browser path such as /Game/Props/SM_Table.SM_Table")
    if path.count("/") < 2:
        raise ValueError("asset_path must include a folder and asset name")
    return path


def _bounded_limit(value: int, *, default: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except Exception:
        parsed = default
    return max(1, min(parsed, maximum))


def _float_value(value: float, *, default: float = 0.0, minimum: Optional[float] = None) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    if minimum is not None:
        parsed = max(minimum, parsed)
    return parsed


def _vector3(value: Optional[Sequence[float]], field_name: str) -> Optional[List[float]]:
    if value is None:
        return None
    try:
        raw = list(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must contain exactly three numbers") from exc
    if len(raw) != 3:
        raise ValueError(f"{field_name} must contain exactly three numbers")
    return [float(raw[0]), float(raw[1]), float(raw[2])]


def _vector3_list(value: Optional[Sequence[Sequence[float]]], field_name: str, *, maximum: int = 100) -> List[List[float]]:
    if value is None:
        return []
    if isinstance(value, str):
        raise ValueError(f"{field_name} must be a list of three-number vectors")
    try:
        raw = list(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be a list of three-number vectors") from exc
    if len(raw) > maximum:
        raise ValueError(f"{field_name} may contain at most {maximum} entries")

    cleaned: List[List[float]] = []
    for index, item in enumerate(raw):
        vector = _vector3(item, f"{field_name}[{index}]")
        if vector is None:
            raise ValueError(f"{field_name}[{index}] must contain exactly three numbers")
        cleaned.append(vector)
    return cleaned


def _string_list(value: Optional[Sequence[Any]], field_name: str, *, maximum: int = 32) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw = [value]
    else:
        try:
            raw = list(value)
        except TypeError as exc:
            raise ValueError(f"{field_name} must be a list of strings") from exc
    if len(raw) > maximum:
        raise ValueError(f"{field_name} may contain at most {maximum} entries")

    cleaned: List[str] = []
    seen = set()
    for item in raw:
        text = str(item or "").strip()
        if not text:
            continue
        if len(text) > 128:
            raise ValueError(f"{field_name} entries must be 128 characters or fewer")
        if text not in seen:
            cleaned.append(text)
            seen.add(text)
    return cleaned


def _clean_choice(value: str, field_name: str, allowed: Sequence[str], default: str) -> str:
    choice = str(value or default).strip().lower()
    if not choice:
        choice = default
    if choice not in allowed:
        raise ValueError(f"{field_name} must be one of: {', '.join(sorted(allowed))}")
    return choice


def _merge_unique(*groups: Sequence[str]) -> List[str]:
    merged: List[str] = []
    seen = set()
    for group in groups:
        for value in group:
            text = str(value or "").strip()
            if text and text not in seen:
                merged.append(text)
                seen.add(text)
    return merged


def _asset_name_from_path(asset_path: str) -> str:
    path = str(asset_path or "").strip()
    if "." in path:
        return path.rsplit(".", 1)[-1]
    return path.rsplit("/", 1)[-1]


def _safe_asset_stem(value: str, default: str = "GeneratedProp") -> str:
    cleaned = []
    for char in str(value or "").strip():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "_":
            cleaned.append("_")
    text = "".join(cleaned).strip("_")
    if not text:
        text = default
    if text[0].isdigit():
        text = f"{default}_{text}"
    return text[:64]


def _clean_room_type(value: str) -> str:
    room_type = str(value or "apartment").strip().lower().replace(" ", "_").replace("-", "_")
    if not room_type:
        room_type = "apartment"
    if room_type not in INTERIOR_ROOM_TYPES:
        raise ValueError(f"room_type must be one of: {', '.join(sorted(INTERIOR_ROOM_TYPES))}")
    return room_type


def _normalize_content_path(value: str) -> str:
    path = str(value or "/Game/Generated/SpatialInteriors").strip().replace("\\", "/")
    if not path:
        path = "/Game/Generated/SpatialInteriors"
    while "//" in path:
        path = path.replace("//", "/")
    path = path.rstrip("/")
    if not path.startswith("/Game"):
        raise ValueError("content_path must be a Content Browser folder under /Game")
    return path


def _clean_reference_image(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        raise ValueError("reference_image is required")
    return text


def _crop_box(value: Any, field_name: str) -> Optional[List[float]]:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        raise ValueError(f"{field_name} must be a list of four numbers")
    try:
        raw = list(value)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be a list of four numbers") from exc
    if len(raw) != 4:
        raise ValueError(f"{field_name} must be a list of four numbers")
    return [float(raw[0]), float(raw[1]), float(raw[2]), float(raw[3])]


def _image_size(value: Optional[Sequence[float]]) -> Optional[List[float]]:
    if value is None:
        return None
    if isinstance(value, str):
        raise ValueError("image_size must contain width and height numbers")
    try:
        raw = list(value)
    except TypeError as exc:
        raise ValueError("image_size must contain width and height numbers") from exc
    if len(raw) != 2:
        raise ValueError("image_size must contain width and height numbers")
    width = float(raw[0])
    height = float(raw[1])
    if width <= 0.0 or height <= 0.0:
        raise ValueError("image_size values must be positive pixels")
    return [width, height]


def _detected_items_from_json(value: str, *, maximum: int) -> List[Dict[str, Any]]:
    text = str(value or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"detected_items_json must be a JSON list: {exc.msg}") from exc
    if not isinstance(parsed, list):
        raise ValueError("detected_items_json must decode to a list")
    if len(parsed) > maximum:
        raise ValueError(f"detected_items_json may contain at most {maximum} items")

    cleaned: List[Dict[str, Any]] = []
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ValueError(f"detected_items_json[{index}] must be an object")
        name = str(item.get("name") or item.get("prop") or item.get("label") or "").strip()
        if not name:
            raise ValueError(f"detected_items_json[{index}].name is required")
        if len(name) > 128:
            raise ValueError(f"detected_items_json[{index}].name must be 128 characters or fewer")
        count = _bounded_limit(item.get("count", 1) or 1, default=1, maximum=20)
        approx_size = None
        if item.get("approx_size_cm") not in (None, ""):
            approx_size = _vector3(item.get("approx_size_cm"), f"detected_items_json[{index}].approx_size_cm")
        existing_asset_path = ""
        if item.get("existing_asset_path"):
            existing_asset_path = _clean_asset_path(str(item.get("existing_asset_path")))
        cleaned.append({
            "id": _safe_asset_stem(str(item.get("id") or name), "DetectedProp"),
            "name": name,
            "category": str(item.get("category") or "prop").strip()[:64] or "prop",
            "zone": str(item.get("zone") or "").strip()[:64],
            "surface": str(item.get("surface") or "").strip()[:64],
            "count": count,
            "crop_box": _crop_box(item.get("crop_box"), f"detected_items_json[{index}].crop_box"),
            "crop_hint": str(item.get("crop_hint") or item.get("description") or "").strip()[:512],
            "placement_hint": str(item.get("placement_hint") or "").strip()[:512],
            "approx_size_cm": approx_size,
            "existing_asset_path": existing_asset_path,
            "confidence": float(item.get("confidence", 0.0) or 0.0),
        })
    return cleaned


def _normalize_detected_zone(zone: str, *, room_type: str, fallback: str) -> str:
    text = str(zone or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "living_room": "living",
        "lounge": "living",
        "sitting": "living",
        "washitsu": "living",
        "tatami_room": "living",
        "ldk": "living",
        "dining": "living",
        "bedroom": "bedroom",
        "sleeping": "bedroom",
        "bed": "bedroom",
        "sleep": "bedroom",
        "kitchenette": "kitchen",
        "galley": "kitchen",
        "laundry": "utility",
        "laundry_room": "utility",
        "mudroom": "utility",
        "entryway": "entry",
        "foyer": "entry",
        "genkan": "entry",
        "vestibule": "entry",
        "unit_bath": "bathroom",
        "bath_unit": "bathroom",
        "toilet": "bathroom",
        "corridor": "hallway",
        "hall": "hallway",
    }
    text = aliases.get(text, text)
    available = {item["name"] for item in _room_zones(room_type, [0.0, 0.0, 0.0], [650.0, 500.0, 280.0])}
    if text in available:
        return text
    if fallback in available:
        return fallback
    if "living" in available:
        return "living"
    return sorted(available)[0]


def _detected_items_to_prop_specs(
    *,
    room_type: str,
    detected_items: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    props: List[Dict[str, Any]] = []
    for item in detected_items:
        name = str(item.get("name") or "").strip()
        match = next((prop for prop in INTERIOR_PROP_LIBRARY if _prop_matches_text(prop, name)), None)
        if match is None:
            match = {
                "name": name,
                "aliases": [name],
                "zone": "living",
                "category": str(item.get("category") or "prop").strip() or "prop",
                "priority": 1,
                "size": [75, 75, 75],
                "surface": "floor",
            }
        prop = dict(match)
        category = str(item.get("category") or "").strip()
        surface = str(item.get("surface") or "").strip()
        prop.update({
            "id": _safe_asset_stem(str(item.get("id") or name), "DetectedProp"),
            "detected_item_id": _safe_asset_stem(str(item.get("id") or name), "DetectedProp"),
            "name": name,
            "aliases": _merge_unique([name], [str(alias) for alias in prop.get("aliases", [])]),
            "zone": _normalize_detected_zone(str(item.get("zone") or ""), room_type=room_type, fallback=str(prop.get("zone", "living"))),
            "category": category if category and category != "prop" else str(prop.get("category", "prop")),
            "surface": surface if surface else str(prop.get("surface", "floor")),
            "count": int(item.get("count", 1) or 1),
            "crop_box": item.get("crop_box"),
            "crop_hint": str(item.get("crop_hint") or ""),
            "placement_hint": str(item.get("placement_hint") or ""),
            "existing_asset_path": str(item.get("existing_asset_path") or ""),
            "confidence": float(item.get("confidence", 0.0) or 0.0),
            "screenshot_evidence": _detected_item_observation(item),
        })
        if item.get("approx_size_cm"):
            prop["size"] = list(item["approx_size_cm"])
        props.append(prop)
    return props


def _detected_item_observation(item: Mapping[str, Any]) -> str:
    parts = [str(item.get("name") or "").strip()]
    if item.get("zone"):
        parts.append(f"zone: {item['zone']}")
    if item.get("surface"):
        parts.append(f"surface: {item['surface']}")
    if item.get("placement_hint"):
        parts.append(str(item["placement_hint"]))
    if item.get("crop_hint"):
        parts.append(f"visual cue: {item['crop_hint']}")
    return "; ".join(part for part in parts if part)


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(float(minimum), min(float(value), float(maximum)))


def _detected_opening_kind(item: Mapping[str, Any]) -> str:
    values = [
        item.get("id", ""),
        item.get("name", ""),
        item.get("category", ""),
        item.get("surface", ""),
        item.get("zone", ""),
        item.get("placement_hint", ""),
        item.get("crop_hint", ""),
    ]
    text = " ".join(str(value or "").lower().replace("_", " ").replace("-", " ") for value in values)
    words = {token.strip() for token in text.split() if token.strip()}
    if any(token in text for token in ("refrigerator", "fridge", "oven", "stove", "cabinet door", "drawer", "wardrobe")):
        return ""
    if any(token in text for token in ("window", "clerestory")):
        return "window"
    if any(token in text for token in ("archway", "arched opening")):
        return "archway"
    if any(token in text for token in ("doorway", "entry door", "front door", "sliding door", "patio door", "threshold", "portal")):
        return "door"
    architectural_context = any(token in text for token in ("architectural", "wall", "entry", "foyer", "hall", "opening"))
    if "door" in words and architectural_context:
        return "door"
    if "opening" in words and architectural_context:
        return "opening"
    return ""


def _wall_from_opening_hint(item: Mapping[str, Any], *, zone_wall: str) -> str:
    text = " ".join([
        str(item.get("placement_hint") or ""),
        str(item.get("crop_hint") or ""),
        str(item.get("zone") or ""),
        str(item.get("name") or ""),
    ]).lower().replace("_", " ").replace("-", " ")
    if any(token in text for token in ("left wall", "left side", "west wall")):
        return "negative_x"
    if any(token in text for token in ("right wall", "right side", "east wall")):
        return "positive_x"
    if any(token in text for token in ("front wall", "near wall", "foreground wall", "south wall")):
        return "negative_y"
    if any(token in text for token in ("back wall", "rear wall", "far wall", "entry wall", "north wall")):
        return "positive_y"
    if zone_wall in {"negative_x", "positive_x", "negative_y", "positive_y"}:
        return zone_wall
    if "entry" in text or "door" in text:
        return "positive_y"
    if "window" in text:
        return "positive_x"
    return "positive_y"


def _opening_vertical_span(kind: str, item: Mapping[str, Any], room_height: float) -> Dict[str, float]:
    size = _optional_vector3(item.get("approx_size_cm"))
    if kind == "window":
        height = float(size[2]) if size and float(size[2]) <= 190.0 else 115.0
        sill = 90.0
    else:
        height = float(size[2]) if size else 220.0
        sill = 0.0
    height = _clamp_float(height, 40.0, max(40.0, float(room_height) - sill))
    return {"sill_cm": round(sill, 3), "height_cm": round(height, 3)}


def _opening_width_cm(kind: str, item: Mapping[str, Any]) -> float:
    size = _optional_vector3(item.get("approx_size_cm"))
    if size:
        span = max(float(size[0]), float(size[1]))
        if span > 0.0:
            return round(_clamp_float(span, 45.0, 360.0), 3)
    if kind == "window":
        return 120.0
    if kind == "archway":
        return 140.0
    return 95.0


def _opening_axis_center_from_hint(
    *,
    text: str,
    axis: str,
    origin: float,
    room_span: float,
    zone_center: float,
    half_width: float,
) -> float:
    minimum = float(origin) - float(room_span) / 2.0 + float(half_width)
    maximum = float(origin) + float(room_span) / 2.0 - float(half_width)
    if minimum > maximum:
        return float(origin)
    if axis == "x" and any(token in text for token in ("left", "west")):
        return _clamp_float(float(origin) - float(room_span) * 0.32, minimum, maximum)
    if axis == "x" and any(token in text for token in ("right", "east")):
        return _clamp_float(float(origin) + float(room_span) * 0.32, minimum, maximum)
    if axis == "y" and any(token in text for token in ("front", "near", "south")):
        return _clamp_float(float(origin) - float(room_span) * 0.32, minimum, maximum)
    if axis == "y" and any(token in text for token in ("back", "rear", "far", "north")):
        return _clamp_float(float(origin) + float(room_span) * 0.32, minimum, maximum)
    if any(token in text for token in ("center", "middle")):
        return _clamp_float(float(origin), minimum, maximum)
    return _clamp_float(float(zone_center), minimum, maximum)


def _detected_opening_records(
    *,
    detected_items: Sequence[Mapping[str, Any]],
    functional_zone_plan: Mapping[str, Any],
    room_type: str,
    room_dimensions: Sequence[float],
    room_origin: Sequence[float],
    actor_label_prefix: str,
) -> List[Dict[str, Any]]:
    width, depth, height = [float(component) for component in room_dimensions]
    ox, oy, oz = [float(component) for component in room_origin]
    room_min_x = ox - width / 2.0
    room_max_x = ox + width / 2.0
    room_min_y = oy - depth / 2.0
    room_max_y = oy + depth / 2.0
    zones = functional_zone_plan.get("zones") if isinstance(functional_zone_plan.get("zones"), list) else []
    zone_lookup = {
        str(zone.get("name") or ""): zone
        for zone in zones
        if isinstance(zone, Mapping)
    }
    label_prefix = _safe_asset_stem(actor_label_prefix or "ReferenceRebuild", "ReferenceRebuild")
    records: List[Dict[str, Any]] = []
    for item in detected_items:
        kind = _detected_opening_kind(item)
        if not kind:
            continue
        zone_name = _normalize_detected_zone(
            str(item.get("zone") or ""),
            room_type=room_type,
            fallback="entry" if kind in {"door", "archway", "opening"} else "living",
        )
        zone = zone_lookup.get(zone_name, {})
        zone_center = _optional_vector3(zone.get("center")) or [ox, oy, oz]
        zone_wall = str(zone.get("wall") or "")
        wall = _wall_from_opening_hint(item, zone_wall=zone_wall)
        opening_width = _opening_width_cm(kind, item)
        vertical = _opening_vertical_span(kind, item, height)
        half_width = opening_width / 2.0
        thickness = 12.0
        hint_text = " ".join([
            str(item.get("placement_hint") or ""),
            str(item.get("crop_hint") or ""),
            str(item.get("zone") or ""),
            str(item.get("name") or ""),
        ]).lower()
        z_min = oz + float(vertical["sill_cm"])
        z_max = min(oz + height, z_min + float(vertical["height_cm"]))
        if wall in {"negative_y", "positive_y"}:
            center_x = _opening_axis_center_from_hint(
                text=hint_text,
                axis="x",
                origin=ox,
                room_span=width,
                zone_center=float(zone_center[0]),
                half_width=half_width,
            )
            if wall == "positive_y":
                mins = [center_x - half_width, room_max_y - thickness, z_min]
                maxs = [center_x + half_width, room_max_y, z_max]
            else:
                mins = [center_x - half_width, room_min_y, z_min]
                maxs = [center_x + half_width, room_min_y + thickness, z_max]
        else:
            center_y = _opening_axis_center_from_hint(
                text=hint_text,
                axis="y",
                origin=oy,
                room_span=depth,
                zone_center=float(zone_center[1]),
                half_width=half_width,
            )
            if wall == "positive_x":
                mins = [room_max_x - thickness, center_y - half_width, z_min]
                maxs = [room_max_x, center_y + half_width, z_max]
            else:
                mins = [room_min_x, center_y - half_width, z_min]
                maxs = [room_min_x + thickness, center_y + half_width, z_max]
        item_id = _safe_asset_stem(str(item.get("id") or item.get("name") or f"{kind}_{len(records)}"), "opening")
        record = {
            "id": f"screenshot_{item_id}_opening",
            "label": f"{label_prefix}_{item_id}_opening",
            "name": str(item.get("name") or item_id),
            "roles": _merge_unique(["opening", kind], [str(item.get("category") or "")]),
            "source": "screenshot_detection",
            "detected_item_id": item_id,
            "detection_name": str(item.get("name") or ""),
            "confidence": round(float(item.get("confidence", 0.0) or 0.0), 3),
            "zone": zone_name,
            "wall": wall,
            "opening_width_cm": opening_width,
            "sill_cm": vertical["sill_cm"],
            "height_cm": vertical["height_cm"],
            "bounds": {
                "min": _rounded_vector(mins),
                "max": _rounded_vector(maxs),
            },
            "center": _rounded_vector([
                (mins[0] + maxs[0]) / 2.0,
                (mins[1] + maxs[1]) / 2.0,
                (mins[2] + maxs[2]) / 2.0,
            ]),
            "placement_hint": str(item.get("placement_hint") or ""),
            "crop_box": item.get("crop_box"),
        }
        records.append(record)
    return records[:32]


def _add_detected_openings_to_composition(
    composition_plan: Mapping[str, Any],
    detected_openings: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    updated = dict(composition_plan)
    if not detected_openings:
        return updated
    openings = [dict(opening) for opening in detected_openings if isinstance(opening, Mapping)]
    room = dict(updated.get("room") or {}) if isinstance(updated.get("room"), Mapping) else {}
    room_existing = room.get("openings") if isinstance(room.get("openings"), list) else []
    top_existing = updated.get("openings") if isinstance(updated.get("openings"), list) else []
    room["openings"] = [*room_existing, *openings]
    updated["room"] = room
    updated["openings"] = [*top_existing, *openings]
    updated["screenshot_opening_constraints"] = {
        "applied": True,
        "source": "detected_items_json",
        "opening_count": len(openings),
        "preflight_tool": "spatial_preflight_interior_layout",
        "reason": "Detected doors, windows, archways, and openings protect circulation, egress, and entry sightlines during layout preflight.",
    }
    workflow = list(updated.get("workflow", [])) if isinstance(updated.get("workflow"), list) else []
    workflow.insert(4 if len(workflow) >= 4 else len(workflow), {
        "step": "preflight_detected_openings",
        "tool": "spatial_preflight_interior_layout",
        "enabled": True,
        "opening_count": len(openings),
        "reason": "Run layout preflight after screenshot reconstruction so detected doors/windows reserve clearance before placement or Tripo import.",
    })
    updated["workflow"] = workflow
    return updated


def _room_dimensions(value: Optional[Sequence[float]]) -> List[float]:
    dimensions = _vector3(value, "room_dimensions") or [650.0, 500.0, 280.0]
    if any(component <= 0 for component in dimensions):
        raise ValueError("room_dimensions values must be positive Unreal centimeters")
    return dimensions


def _outputs_from_result_json(value: str, field_name: str, expected_schema: str) -> Dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be a JSON object: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must decode to an object")
    outputs = parsed.get("outputs") if parsed.get("schema") == SPATIAL_RESULT_SCHEMA else parsed
    if not isinstance(outputs, dict):
        raise ValueError(f"{field_name}.outputs must be an object")
    if outputs.get("schema") not in (None, expected_schema):
        raise ValueError(f"{field_name} must have schema {expected_schema}")
    return outputs


def _room_analysis_from_json(value: str) -> Dict[str, Any]:
    outputs = _outputs_from_result_json(value, "room_analysis_json", ROOM_ANALYSIS_SCHEMA)
    if not outputs:
        return {}
    if outputs.get("schema") not in (None, ROOM_ANALYSIS_SCHEMA):
        raise ValueError(f"room_analysis_json must have schema {ROOM_ANALYSIS_SCHEMA}")

    room_model = outputs.get("room_model") if isinstance(outputs.get("room_model"), dict) else {}
    handoff = outputs.get("planner_handoff") if isinstance(outputs.get("planner_handoff"), dict) else {}
    composition_handoff = handoff.get("spatial_plan_interior_composition") if isinstance(handoff.get("spatial_plan_interior_composition"), dict) else {}
    room_type_value = room_model.get("type") or outputs.get("room_type") or composition_handoff.get("room_type") or "apartment"
    room_type = _clean_room_type(str(room_type_value))
    dimensions = _vector3(
        room_model.get("dimensions_cm") or composition_handoff.get("room_dimensions"),
        "room_analysis_json.room_model.dimensions_cm",
    )
    if dimensions is None or any(component <= 0 for component in dimensions):
        raise ValueError("room_analysis_json.room_model.dimensions_cm must contain positive Unreal centimeters")
    origin = _vector3(
        room_model.get("origin") or composition_handoff.get("room_origin"),
        "room_analysis_json.room_model.origin",
    )
    if origin is None:
        center = _vector3(room_model.get("center"), "room_analysis_json.room_model.center")
        floor_z = float(room_model.get("floor_z", 0.0) or 0.0)
        origin = [float(center[0]), float(center[1]), floor_z] if center is not None else [0.0, 0.0, 0.0]
    return {
        "schema": ROOM_ANALYSIS_SCHEMA,
        "room_type": room_type,
        "room_dimensions": dimensions,
        "room_origin": origin,
        "zones": _room_analysis_zones(outputs.get("zones"), room_type=room_type, room_origin=origin, room_dimensions=dimensions),
        "surface_counts": outputs.get("surface_counts") if isinstance(outputs.get("surface_counts"), dict) else {},
        "clearance_summary": outputs.get("clearance_summary") if isinstance(outputs.get("clearance_summary"), dict) else {},
        "classified_surfaces": outputs.get("classified_surfaces") if isinstance(outputs.get("classified_surfaces"), dict) else {},
        "authored_room_designation": outputs.get("authored_room_designation") if isinstance(outputs.get("authored_room_designation"), dict) else {},
        "planner_handoff": handoff,
    }


def _functional_zone_plan_from_json(value: str) -> Dict[str, Any]:
    outputs = _outputs_from_result_json(value, "functional_zone_plan_json", FUNCTIONAL_ZONE_INFERENCE_SCHEMA)
    if not outputs:
        return {}
    if outputs.get("schema") not in (None, FUNCTIONAL_ZONE_INFERENCE_SCHEMA):
        raise ValueError(f"functional_zone_plan_json must have schema {FUNCTIONAL_ZONE_INFERENCE_SCHEMA}")
    zones = outputs.get("zones") if isinstance(outputs.get("zones"), list) else []
    clean_zones: List[Dict[str, Any]] = []
    for index, zone in enumerate(zones[:16]):
        if not isinstance(zone, Mapping):
            continue
        name = str(zone.get("name") or "").strip()
        if not name:
            continue
        center = _vector3(zone.get("center"), f"functional_zone_plan_json.zones[{index}].center")
        size = _vector3(zone.get("size"), f"functional_zone_plan_json.zones[{index}].size")
        if center is None or size is None:
            raise ValueError(f"functional_zone_plan_json.zones[{index}] must include center and size vectors")
        clean = dict(zone)
        clean["name"] = name
        clean["center"] = center
        clean["size"] = size
        clean.setdefault("wall", "open_center")
        clean_zones.append(clean)
    result = dict(outputs)
    result["zones"] = clean_zones
    return result


def _prop_program_from_json(value: str) -> Dict[str, Any]:
    outputs = _outputs_from_result_json(value, "prop_program_json", INTERIOR_PROP_PROGRAM_SCHEMA)
    if not outputs:
        return {}
    if outputs.get("schema") not in (None, INTERIOR_PROP_PROGRAM_SCHEMA):
        raise ValueError(f"prop_program_json must have schema {INTERIOR_PROP_PROGRAM_SCHEMA}")
    props = outputs.get("props") if isinstance(outputs.get("props"), list) else []
    clean_props: List[Dict[str, Any]] = []
    for index, prop in enumerate(props[:128]):
        if not isinstance(prop, Mapping):
            continue
        name = str(prop.get("name") or prop.get("id") or "").strip()
        if not name:
            raise ValueError(f"prop_program_json.props[{index}].name is required")
        size = None
        if prop.get("approx_size_cm") not in (None, "", []):
            size = _vector3(prop.get("approx_size_cm"), f"prop_program_json.props[{index}].approx_size_cm")
        elif prop.get("size") not in (None, "", []):
            size = _vector3(prop.get("size"), f"prop_program_json.props[{index}].size")
        clean = dict(prop)
        clean["id"] = _safe_asset_stem(str(prop.get("id") or name), "ProgramProp")
        clean["name"] = name
        clean["zone"] = str(prop.get("zone") or "living").strip()[:64] or "living"
        clean["category"] = str(prop.get("category") or "prop").strip()[:64] or "prop"
        clean["surface"] = str(prop.get("surface") or "floor").strip()[:64] or "floor"
        if size is not None:
            clean["approx_size_cm"] = size
            clean["size"] = size
        else:
            clean.setdefault("approx_size_cm", [75.0, 75.0, 75.0])
            clean.setdefault("size", clean["approx_size_cm"])
        clean_props.append(clean)
    result = dict(outputs)
    result["props"] = clean_props
    return result


def _composition_plan_from_json(value: str) -> Dict[str, Any]:
    return _outputs_from_result_json(value, "composition_plan_json", INTERIOR_COMPOSITION_SCHEMA)


def _placement_validation_from_json(value: str) -> Dict[str, Any]:
    return _outputs_from_result_json(value, "validation_result_json", PLACEMENT_VALIDATION_SCHEMA)


def _bounds_center_from_record(record: Mapping[str, Any]) -> Optional[List[float]]:
    bounds = record.get("bounds") if isinstance(record.get("bounds"), Mapping) else {}
    return (
        _optional_vector3(record.get("center"))
        or _optional_vector3(bounds.get("center"))
        or _optional_vector3(bounds.get("origin"))
    )


def _candidate_clearance_overlap_records(candidate: Mapping[str, Any]) -> List[Dict[str, Any]]:
    overlaps = candidate.get("existing_overlaps") if isinstance(candidate.get("existing_overlaps"), list) else []
    cleaned: List[Dict[str, Any]] = []
    for overlap in overlaps[:20]:
        if not isinstance(overlap, Mapping):
            continue
        record = dict(overlap)
        center = _bounds_center_from_record(record)
        if center is not None:
            record["center"] = center
        cleaned.append(record)
    return cleaned


def _candidate_clearance_iteration_validation(candidate_clearance: Mapping[str, Any]) -> Dict[str, Any]:
    candidates = candidate_clearance.get("candidates") if isinstance(candidate_clearance.get("candidates"), list) else []
    validations: List[Dict[str, Any]] = []
    potential_overlap = 0
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        label = str(candidate.get("actor_label") or candidate.get("id") or candidate.get("name") or "Candidate").strip()[:128]
        status = str(candidate.get("status") or "unknown").strip()
        overlaps = _candidate_clearance_overlap_records(candidate)
        candidate_location = (
            _optional_vector3(candidate.get("location"))
            or _bounds_center_from_record(candidate)
            or [0.0, 0.0, 0.0]
        )
        validation_status = "on_surface" if status in {"clear", "needs_review"} else f"candidate_{status}"
        clearance_status = "potential_overlap" if overlaps or status in {"blocked_by_existing_overlap", "blocked_by_clearance"} else status
        if clearance_status == "potential_overlap":
            potential_overlap += 1
        validations.append({
            "actor": {
                "label": label or "Candidate",
                "location": _rounded_vector(candidate_location),
            },
            "status": validation_status,
            "probe_location": _rounded_vector(candidate_location),
            "surface_gap": 0.0,
            "surface_tolerance": 0.0,
            "clearance": {
                "status": clearance_status,
                "overlaps": overlaps,
                "source": "spatial_preflight_candidate_clearance",
                "candidate_status": status,
                "existing_overlap_count": int(candidate.get("existing_overlap_count") or len(overlaps)),
            },
            "source_candidate_clearance": dict(candidate),
        })
    blocked_count = int(candidate_clearance.get("blocked_count") or 0)
    needs_review_count = int(candidate_clearance.get("needs_review_count") or 0)
    return {
        "schema": PLACEMENT_VALIDATION_SCHEMA,
        "source_schema": CANDIDATE_CLEARANCE_SCHEMA,
        "source_status": str(candidate_clearance.get("status") or ""),
        "summary": {
            "on_surface": max(0, len(validations) - blocked_count - needs_review_count),
            "floating": 0,
            "intersecting_or_below_surface": 0,
            "no_surface_hit": 0,
            "potential_overlap": potential_overlap or blocked_count,
        },
        "candidate_clearance_summary": {
            "status": str(candidate_clearance.get("status") or ""),
            "candidate_count": int(candidate_clearance.get("candidate_count") or len(candidates)),
            "blocked_count": blocked_count,
            "needs_review_count": needs_review_count,
        },
        "validations": validations,
    }


def _iteration_validation_from_json(value: str) -> Dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"validation_result_json must be a JSON object: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("validation_result_json must decode to an object")
    outputs = parsed.get("outputs") if parsed.get("schema") == SPATIAL_RESULT_SCHEMA else parsed
    if not isinstance(outputs, dict):
        raise ValueError("validation_result_json.outputs must be an object")
    schema = outputs.get("schema")
    if schema in (None, PLACEMENT_VALIDATION_SCHEMA):
        return outputs
    if schema == CANDIDATE_CLEARANCE_SCHEMA:
        return _candidate_clearance_iteration_validation(outputs)
    raise ValueError(
        f"validation_result_json must have schema {PLACEMENT_VALIDATION_SCHEMA} or {CANDIDATE_CLEARANCE_SCHEMA}"
    )


def _json_value_from_text(value: str, field_name: str) -> Any:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON: {exc.msg}") from exc


def _json_object_from_text(value: str, field_name: str) -> Dict[str, Any]:
    parsed = _json_value_from_text(value, field_name)
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError(f"{field_name} must decode to a JSON object")
    return parsed


def _room_analysis_zones(
    value: Any,
    *,
    room_type: str,
    room_origin: Sequence[float],
    room_dimensions: Sequence[float],
) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return _room_zones(room_type, room_origin, room_dimensions)
    zones: List[Dict[str, Any]] = []
    for index, item in enumerate(value[:16]):
        if not isinstance(item, dict):
            raise ValueError(f"room_analysis_json.zones[{index}] must be an object")
        name = str(item.get("name") or "").strip()[:64]
        if not name:
            raise ValueError(f"room_analysis_json.zones[{index}].name is required")
        center = _vector3(item.get("center"), f"room_analysis_json.zones[{index}].center")
        size = _vector3(item.get("size"), f"room_analysis_json.zones[{index}].size")
        if center is None or size is None:
            raise ValueError(f"room_analysis_json.zones[{index}] must include center and size vectors")
        zones.append({
            "name": name,
            "center": center,
            "size": size,
            "wall": str(item.get("wall") or "open_center").strip()[:64] or "open_center",
            "authored_label": str(item.get("authored_label") or item.get("label") or "").strip()[:64],
            "source": str(item.get("source") or "").strip()[:64],
            "tags": [str(tag) for tag in item.get("tags", [])[:16]] if isinstance(item.get("tags"), list) else [],
        })
    return zones or _room_zones(room_type, room_origin, room_dimensions)


def _room_analysis_probe_points(room_analysis: Mapping[str, Any]) -> List[List[float]]:
    handoff = room_analysis.get("planner_handoff") if isinstance(room_analysis.get("planner_handoff"), dict) else {}
    probe = handoff.get("spatial_surface_probe") if isinstance(handoff.get("spatial_surface_probe"), dict) else {}
    try:
        return _vector3_list(probe.get("points"), "room_analysis_json.planner_handoff.spatial_surface_probe.points", maximum=32)
    except ValueError:
        return []


def _merge_vector_lists(*groups: Sequence[Sequence[float]], maximum: int = 32) -> List[List[float]]:
    merged: List[List[float]] = []
    seen = set()
    for group in groups:
        for item in group:
            try:
                vector = [float(item[0]), float(item[1]), float(item[2])]
            except Exception:
                continue
            key = tuple(round(component, 3) for component in vector)
            if key in seen:
                continue
            merged.append([round(component, 3) for component in vector])
            seen.add(key)
            if len(merged) >= maximum:
                return merged
    return merged


def _room_analysis_observations(room_analysis: Mapping[str, Any]) -> List[str]:
    if not room_analysis:
        return []
    observations: List[str] = []
    counts = room_analysis.get("surface_counts") if isinstance(room_analysis.get("surface_counts"), dict) else {}
    if counts:
        observations.append(
            "Room analysis detected "
            + ", ".join(f"{key}: {value}" for key, value in sorted(counts.items()) if value)
        )
    clearance = room_analysis.get("clearance_summary") if isinstance(room_analysis.get("clearance_summary"), dict) else {}
    risks = clearance.get("risks") if isinstance(clearance.get("risks"), list) else []
    for risk in risks[:8]:
        if not isinstance(risk, dict):
            continue
        label = str(risk.get("actor") or "unknown actor")
        risk_name = str(risk.get("risk") or "clearance_risk")
        reason = str(risk.get("reason") or "").strip()
        observations.append(f"Clearance risk near {label}: {risk_name}" + (f" ({reason})" if reason else ""))
    return observations


def _room_analysis_summary(room_analysis: Mapping[str, Any]) -> Dict[str, Any]:
    if not room_analysis:
        return {"applied": False}
    clearance = room_analysis.get("clearance_summary") if isinstance(room_analysis.get("clearance_summary"), dict) else {}
    designation = room_analysis.get("authored_room_designation") if isinstance(room_analysis.get("authored_room_designation"), dict) else {}
    return {
        "applied": True,
        "schema": ROOM_ANALYSIS_SCHEMA,
        "room_type": room_analysis.get("room_type"),
        "dimensions_cm": list(room_analysis.get("room_dimensions", [])),
        "origin": list(room_analysis.get("room_origin", [])),
        "zone_count": len(room_analysis.get("zones", []) or []),
        "authored_designation": {
            "recognized": bool(designation.get("recognized")),
            "room_bounds_source": designation.get("room_bounds_source", ""),
            "marker_counts": designation.get("marker_counts", {}),
        },
        "surface_counts": room_analysis.get("surface_counts", {}),
        "clearance": {
            "risk_count": clearance.get("risk_count", len(clearance.get("risks", []) if isinstance(clearance.get("risks"), list) else [])),
            "recommended_min_walkway_cm": clearance.get("recommended_min_walkway_cm"),
            "clearance_padding_cm": clearance.get("clearance_padding_cm"),
        },
    }


def _room_analysis_validation_padding(room_analysis: Mapping[str, Any], *, default: float = 12.0) -> float:
    clearance = room_analysis.get("clearance_summary") if isinstance(room_analysis.get("clearance_summary"), dict) else {}
    value = clearance.get("clearance_padding_cm", default)
    try:
        parsed = float(value)
    except Exception:
        parsed = default
    return max(default, min(parsed, 90.0))


def _room_zones(room_type: str, origin: Sequence[float], dimensions: Sequence[float]) -> List[Dict[str, Any]]:
    width, depth, height = [float(component) for component in dimensions]
    ox, oy, oz = [float(component) for component in origin]
    zone_names = {
        "apartment": ["kitchen", "living", "bedroom", "entry", "hallway"],
        "studio": ["kitchen", "living", "bedroom", "entry", "hallway"],
        "kitchen": ["kitchen"],
        "living_room": ["living"],
        "bedroom": ["bedroom"],
        "bathroom": ["bathroom"],
        "hallway": ["hallway"],
        "utility": ["utility"],
        "generic_room": ["living"],
    }.get(room_type, ["living"])

    specs = {
        "kitchen": {"center": [ox - width * 0.22, oy - depth * 0.32, oz], "size": [width * 0.48, depth * 0.28, height], "wall": "negative_y"},
        "living": {"center": [ox + width * 0.08, oy + depth * 0.08, oz], "size": [width * 0.58, depth * 0.48, height], "wall": "open_center"},
        "bedroom": {"center": [ox + width * 0.28, oy + depth * 0.30, oz], "size": [width * 0.36, depth * 0.34, height], "wall": "positive_y"},
        "sleeping": {"center": [ox + width * 0.28, oy + depth * 0.30, oz], "size": [width * 0.36, depth * 0.34, height], "wall": "positive_y"},
        "entry": {"center": [ox - width * 0.36, oy + depth * 0.30, oz], "size": [width * 0.20, depth * 0.24, height], "wall": "positive_y"},
        "hallway": {"center": [ox - width * 0.08, oy + depth * 0.26, oz], "size": [width * 0.38, depth * 0.18, height], "wall": "positive_y"},
        "bathroom": {"center": [ox, oy, oz], "size": [width * 0.75, depth * 0.75, height], "wall": "negative_y"},
        "utility": {"center": [ox - width * 0.30, oy + depth * 0.18, oz], "size": [width * 0.30, depth * 0.30, height], "wall": "positive_x"},
    }
    return [{"name": name, **specs[name]} for name in zone_names if name in specs]


def _designation_room_id(value: str) -> str:
    return _safe_asset_stem(str(value or "Room_01"), "Room_01")


def _designation_tag_suffix(value: str, default: str) -> str:
    text = _safe_asset_stem(str(value or default), default)
    parts = [part for part in text.split("_") if part]
    return "".join(part[:1].upper() + part[1:] for part in parts) or default


def _designation_zone_name(value: str) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    canonical = _normalize_functional_zone_name(text)
    return canonical or text[:64] or "living"


def _designation_zone_display(value: str) -> str:
    text = str(value or "").strip()
    if text:
        return text[:64]
    return "Living"


def _room_bounds_min_max(
    *,
    room_origin: Sequence[float],
    room_dimensions: Sequence[float],
) -> Dict[str, List[float]]:
    width, depth, height = [float(component) for component in room_dimensions]
    ox, oy, oz = [float(component) for component in room_origin]
    minimum = [ox - width / 2.0, oy - depth / 2.0, oz]
    maximum = [ox + width / 2.0, oy + depth / 2.0, oz + height]
    return {
        "min": _rounded_vector(minimum),
        "max": _rounded_vector(maximum),
        "center": _rounded_vector([ox, oy, oz + height / 2.0]),
        "size": _rounded_vector([width, depth, height]),
    }


def _plan_room_bounds_designation(
    *,
    room_id: str,
    room_type: str,
    room_dimensions: Sequence[float],
    room_origin: Sequence[float],
    zone_names: Sequence[str],
    include_opening_markers: bool,
    include_surface_markers: bool,
    include_path_markers: bool,
    limit: int,
) -> Dict[str, Any]:
    clean_room_id = _designation_room_id(room_id)
    room_id_tag = f"{ROOM_ID_TAG_PREFIX}{clean_room_id}"
    room_type_tag = f"{ROOM_TYPE_TAG_PREFIX}{_designation_tag_suffix(room_type, 'Apartment')}"
    room_bounds_tags = [ROOM_BOUNDS_TAG, room_id_tag, room_type_tag]
    default_zone_names = [zone["name"] for zone in _room_zones(room_type, room_origin, room_dimensions)]
    requested_names = [str(name or "").strip() for name in zone_names if str(name or "").strip()]
    authored_names = (requested_names or default_zone_names)[:limit]
    template_by_name = {zone["name"]: zone for zone in _room_zones(room_type, room_origin, room_dimensions)}
    zone_specs: List[Dict[str, Any]] = []
    for index, authored_name in enumerate(authored_names):
        canonical = _designation_zone_name(authored_name)
        template = template_by_name.get(canonical) or template_by_name.get("living") or {
            "center": list(room_origin),
            "size": [float(room_dimensions[0]) * 0.4, float(room_dimensions[1]) * 0.4, float(room_dimensions[2])],
            "wall": "open_center",
        }
        display_name = _designation_zone_display(authored_name)
        zone_tag = f"{ZONE_TAG_PREFIX}{_designation_tag_suffix(display_name, f'Zone{index + 1}')}"
        zone_specs.append({
            "name": canonical,
            "authored_label": display_name,
            "actor_label": f"Ghost_{clean_room_id}_{_safe_asset_stem(display_name, 'Zone')}_ZoneBounds",
            "tags": [zone_tag, room_id_tag],
            "center": _rounded_vector(template.get("center", room_origin)),
            "size": _rounded_vector(template.get("size", room_dimensions)),
            "wall": str(template.get("wall") or "open_center"),
            "usable_area_cm2": round(float(template.get("size", room_dimensions)[0]) * float(template.get("size", room_dimensions)[1]), 3),
            "canonical_role": canonical,
            "source": "planned_authoring_marker",
        })

    marker_examples: List[Dict[str, Any]] = [
        {
            "kind": "room_bounds",
            "actor_label": f"Ghost_{clean_room_id}_RoomBounds",
            "recommended_actor_type": "Box Trigger / Editor volume / simple cube marker",
            "tags": room_bounds_tags,
            "bounds": _room_bounds_min_max(room_origin=room_origin, room_dimensions=room_dimensions),
            "required": True,
        }
    ]
    marker_examples.extend({
        "kind": "zone_bounds",
        "actor_label": zone["actor_label"],
        "recommended_actor_type": "Box Trigger / Editor volume / simple cube marker",
        "tags": zone["tags"],
        "center": zone["center"],
        "size": zone["size"],
        "canonical_role": zone["canonical_role"],
        "authored_label": zone["authored_label"],
        "required": False,
    } for zone in zone_specs)
    if include_opening_markers:
        marker_examples.extend([
            {
                "kind": "opening",
                "actor_label": f"Ghost_{clean_room_id}_EntryDoor_Clearance",
                "recommended_actor_type": "thin box volume covering door swing/threshold",
                "tags": [f"{OPENING_TAG_PREFIX}Door", f"{CLEARANCE_TAG_PREFIX}KeepOpen", room_id_tag],
                "required": False,
            },
            {
                "kind": "opening",
                "actor_label": f"Ghost_{clean_room_id}_Window_Clearance",
                "recommended_actor_type": "thin box volume over window opening",
                "tags": [f"{OPENING_TAG_PREFIX}Window", f"{CLEARANCE_TAG_PREFIX}KeepOpen", room_id_tag],
                "required": False,
            },
        ])
    if include_path_markers:
        marker_examples.append({
            "kind": "path",
            "actor_label": f"Ghost_{clean_room_id}_MainWalkPath",
            "recommended_actor_type": "narrow box volume along required walking lane",
            "tags": [PATH_REQUIRED_TAG, f"{CLEARANCE_TAG_PREFIX}KeepOpen", room_id_tag],
            "required": False,
        })
    if include_surface_markers:
        marker_examples.extend([
            {
                "kind": "surface",
                "actor_label": f"Ghost_{clean_room_id}_CounterSurface",
                "recommended_actor_type": "box or mesh actor aligned to usable countertop",
                "tags": [f"{SURFACE_TAG_PREFIX}Counter", room_id_tag],
                "required": False,
            },
            {
                "kind": "surface",
                "actor_label": f"Ghost_{clean_room_id}_WallSurface",
                "recommended_actor_type": "wall mesh or thin wall marker",
                "tags": [f"{SURFACE_TAG_PREFIX}Wall", room_id_tag],
                "required": False,
            },
        ])

    return {
        "schema": ROOM_BOUNDS_DESIGNATION_SCHEMA,
        "status": "ready_for_editor_authoring",
        "room": {
            "id": clean_room_id,
            "type": room_type,
            "origin": _rounded_vector(room_origin),
            "dimensions_cm": _rounded_vector(room_dimensions),
            "bounds": _room_bounds_min_max(room_origin=room_origin, room_dimensions=room_dimensions),
        },
        "authoritative_source_order": [
            ROOM_BOUNDS_TAG,
            "selected actor bounds when selected actors include a room marker",
            "actor_query/tag_filter aggregate bounds",
            "fallback dimensions supplied to local planners",
        ],
        "tag_contract": {
            "room_bounds": ROOM_BOUNDS_TAG,
            "room_id": room_id_tag,
            "room_type": room_type_tag,
            "zone_prefix": ZONE_TAG_PREFIX,
            "opening_prefix": OPENING_TAG_PREFIX,
            "clearance_prefix": CLEARANCE_TAG_PREFIX,
            "path_required": PATH_REQUIRED_TAG,
            "surface_prefix": SURFACE_TAG_PREFIX,
        },
        "room_bounds_actor": marker_examples[0],
        "zone_specs": zone_specs,
        "zone_count": len(zone_specs),
        "marker_examples": marker_examples,
        "marker_count": len(marker_examples),
        "analysis_handoff": {
            "tool": "spatial_analyze_room",
            "arguments": {
                "room_type": room_type,
                "actor_query": "",
                "tag_filter": room_id_tag,
                "prefer_selected": True,
                "clearance_padding": 90.0,
                "min_walkway_width": 90.0,
            },
            "reason": "Analyze all actors and markers carrying the same room id tag; Ghost.RoomBounds provides the authoritative room envelope.",
        },
        "functional_zone_handoff": {
            "tool": "spatial_infer_functional_zones",
            "arguments": {
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
                "requested_zones": [zone["name"] for zone in zone_specs],
            },
            "enabled": bool(zone_specs),
        },
        "authoring_workflow": [
            "Create or place one box/volume around the usable interior envelope and tag it with the room_bounds tags.",
            "Give every related zone/opening/path/surface marker the same room id tag.",
            "Add zone markers only where the designer wants to override automatic zone inference.",
            "Mark doors, windows, balcony thresholds, and required walk paths as keep-open constraints.",
            "Run spatial_analyze_room using the analysis_handoff before prop programming or Tripo generation.",
        ],
        "mutation_required": False,
        "tripo_required": False,
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is a Ghost-owned authoring/tagging contract and clean-room planner output.",
                "Any future direct reuse of Epic native SceneTools room marker code or source should receive legal review.",
            ],
        },
    }


FUNCTIONAL_ZONE_ALIASES = {
    "living_room": "living",
    "lounge": "living",
    "sitting": "living",
    "washitsu": "living",
    "tatami_room": "living",
    "ldk": "living",
    "dining": "living",
    "sleeping": "bedroom",
    "bed": "bedroom",
    "sleep": "bedroom",
    "kitchenette": "kitchen",
    "galley": "kitchen",
    "corridor": "hallway",
    "hall": "hallway",
    "entryway": "entry",
    "foyer": "entry",
    "genkan": "entry",
    "vestibule": "entry",
    "unit_bath": "bathroom",
    "bath_unit": "bathroom",
    "toilet": "bathroom",
    "laundry": "utility",
    "laundry_room": "utility",
    "mudroom": "utility",
}

FUNCTIONAL_ZONE_DEFAULT_PROPS = {
    "kitchen": ["refrigerator", "stove and oven", "kitchen counter run", "kitchen sink", "base cabinets", "counter clutter"],
    "living": ["sofa", "coffee table", "rug", "bookshelf", "floor lamp", "books and table clutter"],
    "bedroom": ["bed", "nightstand", "dresser"],
    "sleeping": ["bed", "nightstand", "dresser"],
    "entry": ["entry console"],
    "hallway": ["hallway runner rug", "wall hooks", "shoe bench"],
    "bathroom": ["kitchen sink"],
    "utility": ["utility shelf", "washer dryer stack"],
}

INTERIOR_ARCHITECTURAL_FILL_LIBRARY: List[Dict[str, Any]] = [
    {"name": "backsplash panel", "aliases": ["backsplash", "backsplash panel"], "zone": "kitchen", "category": "architectural_fill", "priority": 3, "size": [240, 5, 55], "surface": "wall"},
    {"name": "baseboard trim run", "aliases": ["baseboard", "trim", "baseboard trim"], "zone": "living", "category": "architectural_fill", "priority": 2, "size": [280, 5, 12], "surface": "wall"},
    {"name": "door casing", "aliases": ["door trim", "door casing"], "zone": "entry", "category": "architectural_fill", "priority": 2, "size": [100, 5, 220], "surface": "wall"},
    {"name": "hallway baseboard trim", "aliases": ["hallway trim", "corridor baseboard"], "zone": "hallway", "category": "architectural_fill", "priority": 2, "size": [260, 5, 12], "surface": "wall"},
    {"name": "utility wall rail", "aliases": ["utility rail", "laundry rail"], "zone": "utility", "category": "architectural_fill", "priority": 2, "size": [150, 8, 12], "surface": "wall"},
    {"name": "bedroom wall trim", "aliases": ["bedroom trim", "wall trim"], "zone": "bedroom", "category": "architectural_fill", "priority": 2, "size": [220, 5, 12], "surface": "wall"},
]


def _normalize_functional_zone_name(value: Any, *, fallback: str = "") -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    text = FUNCTIONAL_ZONE_ALIASES.get(text, text)
    allowed = {"kitchen", "living", "bedroom", "sleeping", "entry", "hallway", "bathroom", "utility"}
    if text in allowed:
        return text
    fallback = str(fallback or "").strip().lower().replace("-", "_").replace(" ", "_")
    return FUNCTIONAL_ZONE_ALIASES.get(fallback, fallback) if fallback in allowed or fallback in FUNCTIONAL_ZONE_ALIASES else ""


def _functional_zone_names_for_room(
    *,
    room_type: str,
    requested_zones: Sequence[str],
    evidence_zones: Sequence[str],
) -> List[str]:
    names: List[str] = []

    def add(value: Any) -> None:
        name = _normalize_functional_zone_name(value)
        if name and name not in names:
            names.append(name)

    for value in requested_zones:
        add(value)
    for value in evidence_zones:
        add(value)
    if not names:
        for zone in _room_zones(room_type, [0.0, 0.0, 0.0], [650.0, 500.0, 280.0]):
            add(zone.get("name"))
    if room_type == "apartment" and "entry" not in names:
        names.append("entry")
    if not names:
        names.append("living")
    return names[:8]


def _functional_zone_prop_evidence(item: Mapping[str, Any], *, source: str) -> Dict[str, Any]:
    name = str(item.get("name") or item.get("id") or item.get("actor_label") or "").strip()
    explicit_zone = _normalize_functional_zone_name(item.get("zone"))
    match = _best_interior_prop_match(name)
    inferred_zone = _normalize_functional_zone_name((match or {}).get("zone"))
    zone = explicit_zone or inferred_zone or "living"
    category = str(item.get("category") or (match or {}).get("category") or "prop").strip().lower()
    surface = str(item.get("surface") or (match or {}).get("surface") or "").strip().lower()
    weight = 1.0
    if category in {"appliance", "fixture", "counter", "furniture"}:
        weight += 0.7
    if surface in {"counter", "table", "shelf", "wall"}:
        weight += 0.25
    if item.get("confidence") not in (None, ""):
        try:
            weight += max(0.0, min(float(item.get("confidence")), 1.0)) * 0.5
        except Exception:
            pass
    return {
        "source": source,
        "zone": zone,
        "name": name,
        "category": category,
        "surface": surface,
        "weight": round(weight, 3),
        "reason": f"{source} evidence for {zone}: {name}",
    }


def _functional_zone_surface_center(surface: Mapping[str, Any]) -> List[float]:
    center = _optional_vector3(surface.get("top_center"))
    if center:
        return center
    bounds = surface.get("bounds") if isinstance(surface.get("bounds"), Mapping) else {}
    min_v = _optional_vector3(bounds.get("min"))
    max_v = _optional_vector3(bounds.get("max"))
    if min_v and max_v:
        return [
            round((float(min_v[axis]) + float(max_v[axis])) / 2.0, 3)
            for axis in range(3)
        ]
    center = _optional_vector3(surface.get("center") or surface.get("location"))
    return center or []


def _functional_zone_surface_evidence(room_analysis: Mapping[str, Any]) -> List[Dict[str, Any]]:
    classified = room_analysis.get("classified_surfaces") if isinstance(room_analysis.get("classified_surfaces"), Mapping) else {}
    evidence: List[Dict[str, Any]] = []
    for group_name, default_zone, weight in (
        ("horizontal_supports", "kitchen", 1.4),
        ("openings", "entry", 1.2),
        ("obstacles", "living", 0.7),
        ("walls", "kitchen", 0.25),
    ):
        surfaces = classified.get(group_name) if isinstance(classified.get(group_name), list) else []
        for surface in surfaces[:32]:
            if not isinstance(surface, Mapping):
                continue
            label = str(surface.get("label") or surface.get("name") or "").strip()
            text = " ".join([
                label,
                str(surface.get("class") or ""),
                str(surface.get("path") or ""),
                " ".join(str(role) for role in surface.get("roles", []) if isinstance(surface.get("roles"), list)),
            ]).lower()
            zone = default_zone
            if any(token in text for token in ("counter", "kitchen", "island", "stove", "fridge", "sink", "cabinet")):
                zone = "kitchen"
            elif any(token in text for token in ("corridor", "hallway", "hall runner", "hall_")):
                zone = "hallway"
            elif any(token in text for token in ("door", "entry", "foyer", "opening", "archway")):
                zone = "entry"
            elif any(token in text for token in ("bed", "sleep", "nightstand", "dresser")):
                zone = "bedroom"
            elif any(token in text for token in ("washer", "dryer", "laundry", "utility")):
                zone = "utility"
            elif any(token in text for token in ("sofa", "couch", "coffee", "rug", "book")):
                zone = "living"
            center = _functional_zone_surface_center(surface)
            evidence.append({
                "source": f"room_analysis.{group_name}",
                "zone": zone,
                "name": label or group_name,
                "weight": weight,
                "center": _rounded_vector(center) if center else [],
                "reason": f"{group_name} surface suggests {zone} zone",
            })
    return evidence


def _functional_zone_authored_zone_evidence(room_analysis: Mapping[str, Any]) -> List[Dict[str, Any]]:
    zones = room_analysis.get("zones") if isinstance(room_analysis.get("zones"), list) else []
    evidence: List[Dict[str, Any]] = []
    for zone in zones[:32]:
        if not isinstance(zone, Mapping):
            continue
        name = _normalize_functional_zone_name(zone.get("name"))
        if not name:
            continue
        label = str(zone.get("authored_label") or zone.get("name") or name).strip()
        center = _optional_vector3(zone.get("center"))
        evidence.append({
            "source": "room_analysis.authored_zone",
            "zone": name,
            "name": label or name,
            "weight": 1.65 if str(zone.get("source") or "").startswith("authored") else 1.2,
            "center": _rounded_vector(center) if center else [],
            "reason": f"room analysis zone marker suggests {name} zone",
        })
    return evidence


def _functional_zone_evidence(
    *,
    room_analysis: Mapping[str, Any],
    detected_items: Sequence[Mapping[str, Any]],
    composition_plan: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    evidence: List[Dict[str, Any]] = []
    for item in detected_items:
        if isinstance(item, Mapping):
            evidence.append(_functional_zone_prop_evidence(item, source="detected_item"))
    props = composition_plan.get("props") if isinstance(composition_plan.get("props"), list) else []
    for prop in props[:128]:
        if isinstance(prop, Mapping):
            evidence.append(_functional_zone_prop_evidence(prop, source="composition_prop"))
    evidence.extend(_functional_zone_authored_zone_evidence(room_analysis))
    evidence.extend(_functional_zone_surface_evidence(room_analysis))
    return evidence[:256]


def _functional_zone_region(
    *,
    name: str,
    room_type: str,
    room_origin: Sequence[float],
    room_dimensions: Sequence[float],
    template_by_name: Mapping[str, Mapping[str, Any]],
    anchor_points: Sequence[Sequence[float]],
    min_zone_size_cm: float,
) -> Dict[str, Any]:
    width, depth, height = [float(component) for component in room_dimensions]
    ox, oy, oz = [float(component) for component in room_origin]
    template = template_by_name.get(name) or {}
    center = list(template.get("center") or [ox, oy, oz])
    size = list(template.get("size") or [width * 0.5, depth * 0.5, height])
    wall = str(template.get("wall") or "open_center")
    if anchor_points:
        center = [
            sum(float(point[axis]) for point in anchor_points) / len(anchor_points)
            for axis in range(3)
        ]
        center[2] = oz
    size = [
        max(min_zone_size_cm, min(float(size[0]), width)),
        max(min_zone_size_cm, min(float(size[1]), depth)),
        height,
    ]
    half_x = float(size[0]) / 2.0
    half_y = float(size[1]) / 2.0
    center[0] = min(max(float(center[0]), ox - width / 2.0 + half_x), ox + width / 2.0 - half_x)
    center[1] = min(max(float(center[1]), oy - depth / 2.0 + half_y), oy + depth / 2.0 - half_y)
    if name == "kitchen" and room_type in {"kitchen", "apartment", "studio"}:
        wall = "negative_y" if float(center[1]) <= oy else wall
    if name == "entry":
        wall = "positive_y" if float(center[1]) >= oy else wall
    if name == "hallway":
        wall = "positive_y" if float(center[1]) >= oy else wall
    return {
        "name": name,
        "center": _rounded_vector(center),
        "size": _rounded_vector(size),
        "wall": wall,
        "usable_area_cm2": round(float(size[0]) * float(size[1]), 3),
        "source": str(template.get("source") or "template"),
        "authored_label": str(template.get("authored_label") or ""),
    }


def _plan_functional_zones(
    *,
    room_type: str,
    room_dimensions: Sequence[float],
    room_origin: Sequence[float],
    room_analysis: Mapping[str, Any],
    detected_items: Sequence[Mapping[str, Any]],
    composition_plan: Mapping[str, Any],
    requested_zones: Sequence[str],
    min_zone_size_cm: float,
    include_updated_room_analysis: bool,
    limit: int,
) -> Dict[str, Any]:
    templates = _room_zones(room_type, room_origin, room_dimensions)
    template_by_name = {str(zone.get("name")): zone for zone in templates}
    for zone in room_analysis.get("zones", []) if isinstance(room_analysis.get("zones"), list) else []:
        if not isinstance(zone, Mapping):
            continue
        name = _normalize_functional_zone_name(zone.get("name"))
        center = _optional_vector3(zone.get("center"))
        size = _optional_vector3(zone.get("size"))
        if name and center and size:
            template_by_name[name] = {
                "name": name,
                "center": _rounded_vector(center),
                "size": _rounded_vector(size),
                "wall": str(zone.get("wall") or "open_center"),
                "source": str(zone.get("source") or "room_analysis_zone"),
                "authored_label": str(zone.get("authored_label") or ""),
            }
    evidence = _functional_zone_evidence(
        room_analysis=room_analysis,
        detected_items=detected_items,
        composition_plan=composition_plan,
    )
    evidence_zones = [str(item.get("zone") or "") for item in evidence if item.get("zone")]
    zone_names = _functional_zone_names_for_room(
        room_type=room_type,
        requested_zones=requested_zones,
        evidence_zones=evidence_zones,
    )[:limit]

    evidence_by_zone: Dict[str, List[Dict[str, Any]]] = {name: [] for name in zone_names}
    for item in evidence:
        zone = _normalize_functional_zone_name(item.get("zone"))
        if zone in evidence_by_zone:
            evidence_by_zone[zone].append(item)

    zones: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []
    for name in zone_names:
        zone_evidence = evidence_by_zone.get(name, [])
        anchors = [
            item.get("center")
            for item in zone_evidence
            if isinstance(item.get("center"), list) and len(item.get("center")) >= 3
        ][:6]
        region = _functional_zone_region(
            name=name,
            room_type=room_type,
            room_origin=room_origin,
            room_dimensions=room_dimensions,
            template_by_name=template_by_name,
            anchor_points=anchors,
            min_zone_size_cm=min_zone_size_cm,
        )
        requested = name in {_normalize_functional_zone_name(value) for value in requested_zones}
        score = sum(float(item.get("weight") or 0.0) for item in zone_evidence)
        confidence = min(0.95, 0.35 + score * 0.12 + (0.18 if requested else 0.0))
        if not zone_evidence and requested:
            confidence = max(confidence, 0.55)
        if region["usable_area_cm2"] < min_zone_size_cm * min_zone_size_cm:
            warnings.append({
                "zone": name,
                "kind": "small_zone_area",
                "message": "Functional zone is smaller than the requested minimum footprint.",
            })
        recommended_props = FUNCTIONAL_ZONE_DEFAULT_PROPS.get(name, [])[:8]
        region.update({
            "confidence": round(confidence, 3),
            "requested": requested,
            "evidence_count": len(zone_evidence),
            "evidence": zone_evidence[:12],
            "recommended_props": recommended_props,
            "surface_priorities": (
                ["floor", "counter", "wall"] if name == "kitchen"
                else ["floor", "table", "shelf"] if name == "living"
                else ["floor", "wall"]
            ),
        })
        zones.append(region)

    zone_constraints = [
        {
            "kind": "keep_central_circulation_open",
            "min_walkway_cm": 90.0,
            "applies_to": [zone["name"] for zone in zones],
        },
        {
            "kind": "anchor_kitchen_to_support_surfaces",
            "applies_to": ["kitchen"],
            "enabled": any(zone["name"] == "kitchen" for zone in zones),
        },
        {
            "kind": "compose_living_group",
            "applies_to": ["living"],
            "enabled": any(zone["name"] == "living" for zone in zones),
        },
        {
            "kind": "compose_bedroom_group",
            "applies_to": ["bedroom"],
            "enabled": any(zone["name"] in {"bedroom", "sleeping"} for zone in zones),
        },
        {
            "kind": "preserve_hallway_linear_circulation",
            "min_clear_path_cm": 90.0,
            "applies_to": ["hallway"],
            "enabled": any(zone["name"] == "hallway" for zone in zones),
        },
    ]
    updated_room_analysis = dict(room_analysis) if room_analysis else {
        "schema": ROOM_ANALYSIS_SCHEMA,
        "room_type": room_type,
        "room_dimensions": list(room_dimensions),
        "room_origin": list(room_origin),
    }
    updated_room_analysis["zones"] = [
        {key: value for key, value in zone.items() if key in {"name", "center", "size", "wall", "source", "authored_label", "tags"}}
        for zone in zones
    ]
    updated_room_analysis.setdefault("planner_handoff", {})
    if isinstance(updated_room_analysis["planner_handoff"], dict):
        updated_room_analysis["planner_handoff"]["spatial_plan_interior_composition"] = {
            "room_type": room_type,
            "room_dimensions": list(room_dimensions),
            "room_origin": list(room_origin),
            "functional_zone_plan_json": "<SPATIAL_INFER_FUNCTIONAL_ZONES_RESULT_JSON>",
        }
    status = "ready_for_composition" if zones else "needs_room_analysis"
    zone_names_output = [zone["name"] for zone in zones]
    updated_room_analysis_json = json.dumps(updated_room_analysis, sort_keys=True) if include_updated_room_analysis else "<FUNCTIONAL_ZONE_UPDATED_ROOM_ANALYSIS_JSON>"
    return {
        "schema": FUNCTIONAL_ZONE_INFERENCE_SCHEMA,
        "status": status,
        "room": {
            "type": room_type,
            "dimensions_cm": list(room_dimensions),
            "origin": list(room_origin),
        },
        "zone_count": len(zones),
        "zones": zones,
        "zone_names": zone_names_output,
        "evidence_count": len(evidence),
        "evidence": evidence[:64],
        "warnings": warnings,
        "zone_constraints": zone_constraints,
        "updated_room_analysis": updated_room_analysis if include_updated_room_analysis else {},
        "updated_room_analysis_json": updated_room_analysis_json,
        "composition_handoff": {
            "tool": "spatial_plan_interior_composition",
            "arguments": {
                "room_type": room_type,
                "room_dimensions": list(room_dimensions),
                "room_origin": list(room_origin),
                "room_analysis_json": updated_room_analysis_json,
                "functional_zone_plan_json": "<THIS_FUNCTIONAL_ZONE_INFERENCE_RESULT_JSON>",
                "required_props": sorted({prop for zone in zones for prop in zone.get("recommended_props", [])})[:32],
            },
            "enabled": bool(zones),
        },
        "prop_program_handoff": {
            "tool": "spatial_plan_interior_prop_program",
            "arguments": {
                "room_type": room_type,
                "room_dimensions": list(room_dimensions),
                "room_origin": list(room_origin),
                "functional_zone_plan_json": "<THIS_FUNCTIONAL_ZONE_INFERENCE_RESULT_JSON>",
                "requested_zones": zone_names_output,
                "required_props": sorted({prop for zone in zones for prop in zone.get("recommended_props", [])})[:32],
            },
            "enabled": bool(zones),
        },
        "work_order_handoff": {
            "tool": "spatial_plan_worldbuilding_work_order",
            "arguments": {
                "room_type": room_type,
                "room_dimensions": list(room_dimensions),
                "room_origin": list(room_origin),
                "requested_zones": zone_names_output,
            },
            "enabled": bool(zones),
        },
        "workflow": [
            {"step": "review_room_analysis", "tool": "spatial_analyze_room", "enabled": not bool(room_analysis)},
            {"step": "review_functional_zone_evidence", "reason": "Confirm each zone's evidence before generating or placing props."},
            {"step": "plan_prop_program", "tool": "spatial_plan_interior_prop_program", "enabled": bool(zones)},
            {"step": "plan_composition", "tool": "spatial_plan_interior_composition", "enabled": bool(zones)},
            {"step": "preflight_layout", "tool": "spatial_preflight_interior_layout", "enabled": bool(zones)},
            {"step": "repair_preflight_if_needed", "tool": "spatial_plan_layout_preflight_corrections", "enabled": bool(zones)},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This functional zone inference is Ghost-owned heuristic planning over Ghost room-analysis, screenshot, and composition schemas.",
                "It does not copy Epic native MCP/SceneTools source and does not mutate Unreal Editor state.",
            ],
        },
    }


def _prop_program_zone_names(zones: Sequence[Mapping[str, Any]]) -> List[str]:
    names: List[str] = []
    for zone in zones:
        if not isinstance(zone, Mapping):
            continue
        name = _normalize_functional_zone_name(zone.get("name")) or str(zone.get("name") or "").strip().lower().replace(" ", "_")
        if name and name not in names:
            names.append(name)
    return names or ["living"]


def _prop_program_base_prop(name: str, *, fallback_zone: str, program_source: str) -> Dict[str, Any]:
    match = _best_interior_prop_match(name)
    if match is None:
        match = {
            "name": str(name or "prop").strip() or "prop",
            "aliases": [str(name or "prop").strip() or "prop"],
            "zone": fallback_zone or "living",
            "category": "dressing",
            "priority": 1,
            "size": [75, 75, 75],
            "surface": "floor",
        }
    prop = dict(match)
    if fallback_zone and not str(prop.get("zone") or "").strip():
        prop["zone"] = fallback_zone
    prop["id"] = _safe_asset_stem(str(prop.get("id") or prop.get("name") or name), "ProgramProp")
    prop["program_source"] = program_source
    prop["approx_size_cm"] = list(prop.get("approx_size_cm") or prop.get("size") or [75, 75, 75])
    prop["size"] = list(prop["approx_size_cm"])
    return prop


def _prop_program_add_prop(
    selected: Dict[str, Dict[str, Any]],
    prop: Mapping[str, Any],
    *,
    zone_names: Sequence[str],
    program_source: str,
    existing_asset_paths: Sequence[str],
) -> None:
    clean = dict(prop)
    clean["id"] = _safe_asset_stem(str(clean.get("id") or clean.get("detected_item_id") or clean.get("name")), "ProgramProp")
    zone = _normalize_functional_zone_name(clean.get("zone")) or str(clean.get("zone") or "").strip().lower().replace(" ", "_")
    if zone not in zone_names:
        zone = zone_names[0] if zone_names else "living"
    clean["zone"] = zone
    clean["program_source"] = str(clean.get("program_source") or program_source)
    clean["category"] = str(clean.get("category") or "prop").strip() or "prop"
    clean["surface"] = str(clean.get("surface") or "floor").strip() or "floor"
    size = _size_vector(clean.get("approx_size_cm") or clean.get("size")) or [75.0, 75.0, 75.0]
    clean["approx_size_cm"] = _rounded_vector(size)
    clean["size"] = _rounded_vector(size)
    matched_asset = str(clean.get("existing_asset_path") or clean.get("matched_asset_path") or "").strip()
    if not matched_asset:
        matched_asset = _match_existing_asset(clean, existing_asset_paths)
    if matched_asset:
        clean["existing_asset_path"] = matched_asset
        clean["matched_asset_path"] = matched_asset
    key = clean["id"]
    if key in selected:
        merged = dict(selected[key])
        merged.update({key_name: value for key_name, value in clean.items() if value not in (None, "", [])})
        sources = _merge_unique(
            [str(selected[key].get("program_source") or "")],
            [str(clean.get("program_source") or "")],
        )
        merged["program_source"] = "+".join(sources)
        selected[key] = merged
    else:
        selected[key] = clean


def _prop_program_density_status(ratio: float) -> str:
    if ratio <= 0.10:
        return "sparse"
    if ratio <= 0.24:
        return "comfortable"
    if ratio <= 0.38:
        return "dense"
    return "crowded_review"


def _prop_program_for_zone(
    *,
    zone: Mapping[str, Any],
    props: Sequence[Mapping[str, Any]],
    requested: bool,
) -> Dict[str, Any]:
    name = str(zone.get("name") or "zone")
    zone_props = [prop for prop in props if str(prop.get("zone") or "") == name]
    area = float(zone.get("usable_area_cm2") or 0.0)
    if area <= 0.0:
        size = _size_vector(zone.get("size")) or [1.0, 1.0, 1.0]
        area = max(1.0, float(size[0]) * float(size[1]))
    footprint = 0.0
    categories: Dict[str, int] = {}
    surfaces: Dict[str, int] = {}
    for prop in zone_props:
        size = _size_vector(prop.get("approx_size_cm") or prop.get("size")) or [75.0, 75.0, 75.0]
        if str(prop.get("surface") or "floor") == "floor":
            footprint += float(size[0]) * float(size[1])
        category = str(prop.get("category") or "prop")
        surface = str(prop.get("surface") or "floor")
        categories[category] = categories.get(category, 0) + 1
        surfaces[surface] = surfaces.get(surface, 0) + 1
    density = round(footprint / max(1.0, area), 3)
    notes = [
        "Anchor kitchen appliances, sink, counters, cabinets, stools, and clutter as one readable work zone." if name == "kitchen" else "",
        "Keep living seating, coffee table, rug, books, and lighting visually grouped." if name == "living" else "",
        "Keep the bed, nightstand, dresser, and bedroom wall dressing readable as one bedroom zone." if name in {"bedroom", "sleeping"} else "",
        "Use narrow wall-hugging props and keep the center path legible through the hallway." if name == "hallway" else "",
        "Keep entry and utility props against walls and preserve circulation." if name in {"entry", "utility"} else "",
    ]
    return {
        "name": name,
        "requested": requested,
        "center": list(zone.get("center") or []),
        "size": list(zone.get("size") or []),
        "wall": str(zone.get("wall") or ""),
        "usable_area_cm2": round(area, 3),
        "planned_props": [str(prop.get("name") or prop.get("id")) for prop in zone_props],
        "planned_prop_count": len(zone_props),
        "category_counts": categories,
        "surface_counts": surfaces,
        "floor_footprint_cm2": round(footprint, 3),
        "density_ratio": density,
        "density_status": _prop_program_density_status(density),
        "missing_asset_count": len([prop for prop in zone_props if not (prop.get("matched_asset_path") or prop.get("existing_asset_path"))]),
        "composition_notes": [note for note in notes if note],
    }


def _plan_interior_prop_program(
    *,
    room_type: str,
    room_dimensions: Sequence[float],
    room_origin: Sequence[float],
    functional_zone_plan: Mapping[str, Any],
    room_analysis: Mapping[str, Any],
    detected_items: Sequence[Mapping[str, Any]],
    requested_zones: Sequence[str],
    required_props: Sequence[str],
    omit_props: Sequence[str],
    existing_asset_paths: Sequence[str],
    style: str,
    intent: str,
    include_architectural_fill: bool,
    limit: int,
    include_zone_recommendations: bool = True,
) -> Dict[str, Any]:
    zones = list(functional_zone_plan.get("zones", []) or room_analysis.get("zones", []) or _room_zones(room_type, room_origin, room_dimensions))
    zone_names = _prop_program_zone_names(zones)
    requested = {
        _normalize_functional_zone_name(value) or str(value or "").strip().lower().replace(" ", "_")
        for value in requested_zones
        if str(value or "").strip()
    }
    selected: Dict[str, Dict[str, Any]] = {}

    if include_zone_recommendations:
        for zone in zones:
            if not isinstance(zone, Mapping):
                continue
            zone_name = _normalize_functional_zone_name(zone.get("name")) or str(zone.get("name") or "").strip().lower().replace(" ", "_")
            recommendations = zone.get("recommended_props") if isinstance(zone.get("recommended_props"), list) else FUNCTIONAL_ZONE_DEFAULT_PROPS.get(zone_name, [])
            for prop_name in recommendations:
                prop = _prop_program_base_prop(str(prop_name), fallback_zone=zone_name, program_source="zone_recommended")
                _prop_program_add_prop(selected, prop, zone_names=zone_names, program_source="zone_recommended", existing_asset_paths=existing_asset_paths)

    for requested_prop in required_props:
        fallback_zone = zone_names[0] if zone_names else "living"
        prop = _prop_program_base_prop(str(requested_prop), fallback_zone=fallback_zone, program_source="user_required")
        _prop_program_add_prop(selected, prop, zone_names=zone_names, program_source="user_required", existing_asset_paths=existing_asset_paths)

    for prop in _detected_items_to_prop_specs(room_type=room_type, detected_items=detected_items):
        _prop_program_add_prop(selected, prop, zone_names=zone_names, program_source="screenshot_detected", existing_asset_paths=existing_asset_paths)

    if include_architectural_fill:
        for fill in INTERIOR_ARCHITECTURAL_FILL_LIBRARY:
            fill_zone = str(fill.get("zone") or "")
            if fill_zone in zone_names:
                _prop_program_add_prop(selected, fill, zone_names=zone_names, program_source="architectural_fill", existing_asset_paths=existing_asset_paths)

    omit_text = " ".join(omit_props).lower()
    props = [
        prop for prop in selected.values()
        if not _prop_matches_text(prop, omit_text)
    ][:limit]

    zone_program = [
        _prop_program_for_zone(
            zone=zone,
            props=props,
            requested=bool(not requested or str(zone.get("name") or "").lower() in requested),
        )
        for zone in zones
        if isinstance(zone, Mapping)
    ]
    generation_candidates = []
    existing_matches = []
    for prop in props:
        matched = str(prop.get("matched_asset_path") or prop.get("existing_asset_path") or "").strip()
        if matched:
            existing_matches.append({
                "id": prop.get("id"),
                "name": prop.get("name"),
                "asset_path": matched,
                "program_source": prop.get("program_source", ""),
            })
            continue
        generation_candidates.append({
            "id": prop.get("id"),
            "name": prop.get("name"),
            "zone": prop.get("zone"),
            "category": prop.get("category"),
            "surface": prop.get("surface"),
            "approx_size_cm": list(prop.get("approx_size_cm") or []),
            "program_source": prop.get("program_source", ""),
            "tripo_prompt_seed": _tripo_prompt_for_prop(prop, room_type=room_type, style=style, intent=intent),
        })

    warnings = []
    for zone in zone_program:
        if zone.get("density_status") == "crowded_review":
            warnings.append({
                "zone": zone.get("name"),
                "kind": "crowded_zone_density",
                "message": "Review footprint density before placement or reduce optional props.",
            })
    if "kitchen" in zone_names:
        kitchen_prop_names = " ".join(str(prop.get("name") or "").lower() for prop in props if prop.get("zone") == "kitchen")
        for required in ("counter", "sink"):
            if required not in kitchen_prop_names:
                warnings.append({
                    "zone": "kitchen",
                    "kind": f"missing_{required}_anchor",
                    "message": f"Kitchen zone has no {required} anchor in the prop program.",
                })

    prop_program_payload = {
        "schema": INTERIOR_PROP_PROGRAM_SCHEMA,
        "status": "ready_for_composition" if props else "needs_prop_requirements",
        "room": {
            "type": room_type,
            "dimensions_cm": list(room_dimensions),
            "origin": list(room_origin),
            "style": style,
            "intent": intent,
        },
        "functional_zone_plan_applied": bool(functional_zone_plan),
        "room_analysis_applied": bool(room_analysis),
        "zone_recommendations_applied": bool(include_zone_recommendations),
        "zone_count": len(zones),
        "zones": zones,
        "zone_program": zone_program,
        "props": props,
        "prop_count": len(props),
        "generation_candidates": generation_candidates,
        "generation_candidate_count": len(generation_candidates),
        "existing_asset_matches": existing_matches,
        "existing_asset_match_count": len(existing_matches),
        "architectural_fill_count": len([prop for prop in props if prop.get("program_source") == "architectural_fill"]),
        "detected_prop_count": len([prop for prop in props if "screenshot_detected" in str(prop.get("program_source") or "")]),
        "required_prop_count": len([prop for prop in props if "user_required" in str(prop.get("program_source") or "")]),
        "recommended_prop_count": len([prop for prop in props if "zone_recommended" in str(prop.get("program_source") or "")]),
        "warnings": warnings,
    }
    return {
        **prop_program_payload,
        "composition_handoff": {
            "tool": "spatial_plan_interior_composition",
            "arguments": {
                "room_type": room_type,
                "room_dimensions": list(room_dimensions),
                "room_origin": list(room_origin),
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>" if room_analysis else "",
                "functional_zone_plan_json": "<SPATIAL_INFER_FUNCTIONAL_ZONES_RESULT_JSON>" if functional_zone_plan else "",
                "prop_program_json": "<THIS_INTERIOR_PROP_PROGRAM_RESULT_JSON>",
            },
            "enabled": bool(props),
        },
        "asset_resolution_handoff": {
            "tool": "spatial_resolve_project_assets",
            "arguments": {
                "composition_plan_json": "<SPATIAL_PLAN_INTERIOR_COMPOSITION_RESULT_JSON>",
                "asset_catalog_json": "<SPATIAL_CATALOG_PROJECT_ASSETS_RESULT_JSON>",
            },
            "enabled": bool(props),
        },
        "workflow": [
            {"step": "measure_space", "tool": "spatial_analyze_room", "enabled": not bool(room_analysis)},
            {"step": "infer_functional_zones", "tool": "spatial_infer_functional_zones", "enabled": not bool(functional_zone_plan)},
            {"step": "review_prop_program", "reason": "Confirm required fixtures, furniture, clutter, architectural fill, and missing-asset candidates before composition."},
            {"step": "plan_composition", "tool": "spatial_plan_interior_composition", "enabled": bool(props)},
            {"step": "resolve_project_assets", "tool": "spatial_resolve_project_assets", "enabled": bool(props)},
            {"step": "prepare_guarded_tripo_batch", "tool": "spatial_prepare_tripo_generation_batch", "enabled": bool(generation_candidates)},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is Ghost-owned prop-program planning over Ghost room, zone, screenshot, and asset metadata.",
                "It does not mutate Unreal Editor state, run computer vision, submit Tripo jobs, or copy Epic native SceneTools source.",
            ],
        },
    }


def _prop_program_summary(prop_program: Mapping[str, Any], props: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    if not prop_program:
        return {"applied": False, "prop_count": len(props)}
    return {
        "applied": True,
        "schema": prop_program.get("schema") or INTERIOR_PROP_PROGRAM_SCHEMA,
        "status": prop_program.get("status", ""),
        "prop_count": len(props),
        "zone_program_count": len(prop_program.get("zone_program", []) if isinstance(prop_program.get("zone_program"), list) else []),
        "generation_candidate_count": int(prop_program.get("generation_candidate_count") or 0),
        "architectural_fill_count": int(prop_program.get("architectural_fill_count") or 0),
    }


def _prop_matches_text(prop: Mapping[str, Any], text: str) -> bool:
    return _prop_match_score(prop, text) > 0


def _prop_match_score(prop: Mapping[str, Any], text: str) -> int:
    needle = text.lower()
    if not needle:
        return 0
    values = [str(prop.get("name", "")), str(prop.get("category", "")), *[str(alias) for alias in prop.get("aliases", [])]]
    best = 0
    needle_tokens = {token for token in needle.replace("_", " ").replace("-", " ").split() if token}
    for value in values:
        haystack = value.lower().strip()
        if not haystack:
            continue
        haystack_tokens = {token for token in haystack.replace("_", " ").replace("-", " ").split() if token}
        if haystack == needle:
            best = max(best, 100)
        elif needle in haystack:
            best = max(best, 80)
        elif haystack in needle:
            best = max(best, 40)
        elif needle_tokens and haystack_tokens and needle_tokens.issubset(haystack_tokens):
            best = max(best, 70)
        elif needle_tokens and haystack_tokens and haystack_tokens.issubset(needle_tokens):
            best = max(best, 35)
        elif needle_tokens and haystack_tokens and needle_tokens.intersection(haystack_tokens):
            best = max(best, 15)
    return best


def _best_interior_prop_match(text: str) -> Optional[Dict[str, Any]]:
    scored = [
        (_prop_match_score(prop, text), int(prop.get("priority", 0)), -index, prop)
        for index, prop in enumerate(INTERIOR_PROP_LIBRARY)
    ]
    score, _priority, _index, prop = max(scored, key=lambda item: (item[0], item[1], item[2]))
    return dict(prop) if score > 0 else None


def _select_interior_props(
    *,
    room_type: str,
    required_props: Sequence[str],
    omit_props: Sequence[str],
    screenshot_observations: Sequence[str],
    limit: int,
    detected_items: Sequence[Mapping[str, Any]] = (),
) -> List[Dict[str, Any]]:
    zones = {zone["name"] for zone in _room_zones(room_type, [0.0, 0.0, 0.0], [650.0, 500.0, 280.0])}
    omit_text = " ".join(omit_props).lower()
    selected: Dict[str, Dict[str, Any]] = {}

    if detected_items:
        for prop in _detected_items_to_prop_specs(room_type=room_type, detected_items=detected_items):
            selected[str(prop.get("id") or prop["name"])] = prop
    elif required_props:
        for requested in required_props:
            requested_text = str(requested or "").strip()
            if not requested_text:
                continue
            match = _best_interior_prop_match(requested_text)
            if match is None:
                match = {
                    "name": requested_text,
                    "aliases": [requested_text],
                    "zone": "living" if "living" in zones else sorted(zones)[0],
                    "category": "dressing",
                    "priority": 1,
                    "size": [75, 75, 75],
                    "surface": "floor",
                }
            selected[str(match["name"])] = dict(match)
    else:
        for prop in sorted(INTERIOR_PROP_LIBRARY, key=lambda item: (-int(item["priority"]), str(item["name"]))):
            if prop["zone"] in zones:
                selected[str(prop["name"])] = dict(prop)
            if len(selected) >= limit:
                break

    for observation in ([] if detected_items else screenshot_observations):
        text = str(observation or "").strip()
        if not text:
            continue
        match = _best_interior_prop_match(text)
        if match is not None:
            entry = dict(match)
            entry["screenshot_evidence"] = text
            selected[str(entry["name"])] = entry

    filtered = []
    for prop in selected.values():
        if _prop_matches_text(prop, omit_text):
            continue
        filtered.append(prop)
    return filtered[:limit]


def _match_existing_asset(prop: Mapping[str, Any], existing_asset_paths: Sequence[str]) -> str:
    prop_terms = [str(prop.get("name", "")), str(prop.get("category", "")), *[str(alias) for alias in prop.get("aliases", [])]]
    normalized_terms = [
        term.lower().replace(" ", "").replace("_", "").replace("-", "")
        for term in prop_terms
        if term
    ]
    for path in existing_asset_paths:
        haystack = str(path).lower().replace(" ", "").replace("_", "").replace("-", "")
        if any(term and term in haystack for term in normalized_terms):
            return str(path)
    return ""


def _surface_vec(surface: Mapping[str, Any], field: str) -> Optional[List[float]]:
    value = surface.get(field)
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            return [float(value[0]), float(value[1]), float(value[2])]
        except Exception:
            return None
    return None


def _surface_bounds_values(surface: Mapping[str, Any]) -> Optional[Dict[str, List[float]]]:
    bounds = surface.get("bounds") if isinstance(surface.get("bounds"), dict) else {}
    mins = _optional_vector3(bounds.get("min"))
    maxs = _optional_vector3(bounds.get("max"))
    if mins is None or maxs is None:
        return None
    return {
        "min": mins,
        "max": maxs,
        "center": [(mins[0] + maxs[0]) / 2.0, (mins[1] + maxs[1]) / 2.0, (mins[2] + maxs[2]) / 2.0],
        "size": [maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2]],
    }


def _analysis_surfaces(room_analysis: Mapping[str, Any], role: str) -> List[Mapping[str, Any]]:
    classified = room_analysis.get("classified_surfaces") if isinstance(room_analysis.get("classified_surfaces"), dict) else {}
    surfaces = classified.get(role) if isinstance(classified.get(role), list) else []
    return [surface for surface in surfaces if isinstance(surface, dict)]


def _zone_contains_xy(zone: Mapping[str, Any], point: Sequence[float]) -> bool:
    try:
        center = [float(value) for value in zone.get("center", [0.0, 0.0, 0.0])]
        size = [float(value) for value in zone.get("size", [0.0, 0.0, 0.0])]
        x, y = float(point[0]), float(point[1])
    except Exception:
        return False
    return abs(x - center[0]) <= max(1.0, size[0] / 2.0) and abs(y - center[1]) <= max(1.0, size[1] / 2.0)


def _surface_for_zone(
    surfaces: Sequence[Mapping[str, Any]],
    *,
    zone: Mapping[str, Any],
    index: int,
) -> Optional[Mapping[str, Any]]:
    if not surfaces:
        return None
    zoned = []
    for surface in surfaces:
        point = _surface_vec(surface, "top_center")
        if point is None:
            values = _surface_bounds_values(surface)
            point = values["center"] if values else None
        if point is not None and _zone_contains_xy(zone, point):
            zoned.append(surface)
    candidates = zoned or list(surfaces)
    return candidates[index % len(candidates)]


def _room_analysis_location_for_prop(
    prop: Mapping[str, Any],
    *,
    room_analysis: Mapping[str, Any],
    zone: Mapping[str, Any],
    room_origin: Sequence[float],
    index: int,
    fallback_location: Sequence[float],
    fallback_rotation: Sequence[float],
) -> Optional[Dict[str, Any]]:
    if not room_analysis:
        return None
    name = str(prop.get("name", "")).lower()
    category = str(prop.get("category", "")).lower()
    surface = str(prop.get("surface", "")).lower()

    needs_horizontal_support = (
        surface in {"counter", "table", "shelf"}
        or "clutter" in name
        or "book" in name
        or category in {"dressing", "fixture"}
    )
    if needs_horizontal_support:
        support = _surface_for_zone(_analysis_surfaces(room_analysis, "horizontal_supports"), zone=zone, index=index)
        if support is not None:
            top_center = _surface_vec(support, "top_center")
            if top_center is None:
                bounds = _surface_bounds_values(support)
                if bounds is not None:
                    top_center = [bounds["center"][0], bounds["center"][1], bounds["max"][2]]
            if top_center is not None:
                offsets = [(0.0, 0.0), (18.0, 0.0), (-18.0, 0.0), (0.0, 18.0), (0.0, -18.0)]
                dx, dy = offsets[index % len(offsets)]
                support_roles = [str(role) for role in support.get("roles", [])] if isinstance(support.get("roles"), list) else []
                support_source = (
                    "composition_horizontal_support"
                    if str(support.get("source") or "") == "composition_prop" or "composition_support_surface" in support_roles
                    else "room_analysis_horizontal_support"
                )
                return {
                    "location": [round(top_center[0] + dx, 3), round(top_center[1] + dy, 3), round(top_center[2] + 2.0, 3)],
                    "rotation": list(fallback_rotation),
                    "source": support_source,
                    "support_actor": str(support.get("label") or ""),
                    "support_roles": support_roles,
                }

    needs_wall = surface == "wall" or "wall cabinet" in name or "upper cabinet" in name
    if needs_wall:
        wall = _surface_for_zone(_analysis_surfaces(room_analysis, "walls"), zone=zone, index=index)
        bounds = _surface_bounds_values(wall) if wall is not None else None
        if wall is not None and bounds is not None:
            size = bounds["size"]
            yaw = 90.0 if size[0] <= size[1] else 0.0
            wall_roles = [str(role) for role in wall.get("roles", [])] if isinstance(wall.get("roles"), list) else []
            wall_source = (
                "composition_room_wall"
                if str(wall.get("source") or "") == "composition_room"
                or "composition_wall_surface" in wall_roles
                else "room_analysis_wall"
            )
            return {
                "location": [
                    round(bounds["center"][0], 3),
                    round(bounds["center"][1], 3),
                    round(max(float(room_origin[2]) + 150.0, bounds["min"][2] + 150.0), 3),
                ],
                "rotation": [0.0, yaw, 0.0],
                "source": wall_source,
                "support_actor": str(wall.get("label") or ""),
                "support_roles": wall_roles,
            }

    if surface == "floor":
        floor = _surface_for_zone(_analysis_surfaces(room_analysis, "floors"), zone=zone, index=index)
        top_center = _surface_vec(floor, "top_center") if floor is not None else None
        if top_center is None and floor is not None:
            bounds = _surface_bounds_values(floor)
            if bounds is not None:
                top_center = [bounds["center"][0], bounds["center"][1], bounds["max"][2]]
        if top_center is not None:
            location = [float(fallback_location[0]), float(fallback_location[1]), round(float(top_center[2]), 3)]
            return {
                "location": [round(value, 3) for value in location],
                "rotation": list(fallback_rotation),
                "source": "room_analysis_floor_z",
                "support_actor": str(floor.get("label") or ""),
                "support_roles": list(floor.get("roles", [])) if isinstance(floor.get("roles"), list) else [],
            }

    return None


def _placement_hint_transform(
    prop: Mapping[str, Any],
    *,
    zone_name: str,
    zone: Mapping[str, Any],
    room_origin: Sequence[float],
    room_dimensions: Sequence[float],
    fallback_location: Sequence[float],
    fallback_rotation: Sequence[float],
) -> Optional[Dict[str, Any]]:
    hint = str(prop.get("placement_hint") or "").strip().lower()
    if not hint:
        return None

    width, depth, _height = [float(component) for component in room_dimensions]
    ox, oy, oz = [float(component) for component in room_origin]
    center = [float(value) for value in zone.get("center", [ox, oy, oz])]
    size = [float(value) for value in zone.get("size", [width, depth, _height])]
    zone_half_x = max(40.0, size[0] / 2.0)
    zone_half_y = max(40.0, size[1] / 2.0)
    x_min = max(ox - width * 0.46, center[0] - zone_half_x * 0.92)
    x_max = min(ox + width * 0.46, center[0] + zone_half_x * 0.92)
    y_min = max(oy - depth * 0.46, center[1] - zone_half_y * 0.92)
    y_max = min(oy + depth * 0.46, center[1] + zone_half_y * 0.92)
    location = [float(fallback_location[0]), float(fallback_location[1]), float(fallback_location[2])]
    rotation = list(fallback_rotation)
    source_parts = []

    if "coffee table" in hint:
        location = [ox - width * 0.05, oy + depth * 0.02, oz + 47.0]
        source_parts.append("anchor_coffee_table")
    elif "counter" in hint or "countertop" in hint or "island" in hint or "under cabinet" in hint or "under the cabinet" in hint:
        kitchen_y = oy - depth * 0.43 if zone_name == "kitchen" else y_min
        location = [center[0], kitchen_y, oz + 97.0]
        rotation = [0.0, 0.0, 0.0]
        source_parts.append("anchor_counter")
    elif "table" in hint or "desk" in hint:
        location = [center[0], center[1], oz + 47.0]
        source_parts.append("anchor_table")

    if "left" in hint:
        location[0] = x_min
        rotation = [0.0, 90.0, 0.0]
        source_parts.append("left_wall")
    elif "right" in hint:
        location[0] = x_max
        rotation = [0.0, -90.0, 0.0]
        source_parts.append("right_wall")

    if any(token in hint for token in ("front", "near wall", "foreground", "negative_y")):
        location[1] = y_min
        rotation = [0.0, 0.0, 0.0]
        source_parts.append("front_wall")
    elif any(token in hint for token in ("back", "rear", "far wall", "positive_y")):
        location[1] = y_max
        rotation = [0.0, 180.0, 0.0]
        source_parts.append("back_wall")
    elif "kitchen wall" in hint or "against wall" in hint or "against the wall" in hint:
        if zone_name == "kitchen":
            location[1] = y_min
            rotation = [0.0, 0.0, 0.0]
            source_parts.append("kitchen_wall")

    if "center" in hint or "middle" in hint:
        location[0] = center[0]
        location[1] = center[1]
        source_parts.append("zone_center")

    if "floor" in hint:
        location[2] = oz
        source_parts.append("floor_contact")
    elif "wall" in hint and str(prop.get("surface", "")).lower() == "wall":
        location[2] = max(location[2], oz + 150.0)
        source_parts.append("wall_height")

    if not source_parts:
        return None

    return {
        "location": [round(value, 3) for value in location],
        "rotation": rotation,
        "source": "placement_hint_" + "_".join(source_parts[:3]),
        "placement_hint": str(prop.get("placement_hint") or ""),
    }


def _prop_location(
    prop: Mapping[str, Any],
    *,
    zone_lookup: Mapping[str, Mapping[str, Any]],
    room_origin: Sequence[float],
    room_dimensions: Sequence[float],
    index: int,
    room_analysis: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    width, depth, _height = [float(component) for component in room_dimensions]
    ox, oy, oz = [float(component) for component in room_origin]
    name = str(prop.get("name", "")).lower()
    zone_name = str(prop.get("zone", "living"))
    zone = zone_lookup.get(zone_name) or {"center": [ox, oy, oz], "wall": "open_center"}
    center = [float(value) for value in zone.get("center", [ox, oy, oz])]

    location = list(center)
    rotation = [0.0, 0.0, 0.0]
    if zone_name == "kitchen":
        x_slots = [-0.36, -0.22, -0.08, 0.06, 0.20, 0.34]
        slot = x_slots[index % len(x_slots)]
        location = [ox + width * slot, oy - depth * 0.43, oz]
        rotation = [0.0, 0.0, 0.0]
        if "wall cabinet" in name:
            location[2] = oz + 150.0
        if "counter clutter" in name or "sink" in name:
            location[2] = oz + 95.0
    elif zone_name == "living":
        if "sofa" in name:
            location = [ox - width * 0.05, oy + depth * 0.18, oz]
            rotation = [0.0, 180.0, 0.0]
        elif "coffee" in name:
            location = [ox - width * 0.05, oy + depth * 0.02, oz]
        elif "rug" in name:
            location = [ox - width * 0.05, oy + depth * 0.04, oz + 1.0]
        elif "book" in name:
            location = [ox + width * 0.34, oy + depth * 0.02, oz]
            rotation = [0.0, -90.0, 0.0]
        else:
            location = [ox + width * 0.22, oy + depth * 0.12, oz]
    elif zone_name in {"bedroom", "sleeping"}:
        if "bed" in name:
            location = [ox + width * 0.26, oy + depth * 0.32, oz]
            rotation = [0.0, 180.0, 0.0]
        else:
            location = [ox + width * 0.40, oy + depth * 0.25, oz]
            rotation = [0.0, 180.0, 0.0]
    elif zone_name == "entry":
        location = [ox - width * 0.42, oy + depth * 0.34, oz]
        rotation = [0.0, 180.0, 0.0]
    elif zone_name == "hallway":
        if "runner" in name or "rug" in name:
            location = [ox - width * 0.08, oy + depth * 0.26, oz + 1.0]
            rotation = [0.0, 90.0, 0.0]
        elif "hook" in name or "coat" in name:
            location = [ox + width * 0.08, oy + depth * 0.35, oz + 135.0]
            rotation = [0.0, 180.0, 0.0]
        else:
            location = [ox - width * 0.24, oy + depth * 0.33, oz]
            rotation = [0.0, 180.0, 0.0]
    elif zone_name == "utility":
        location = [ox - width * 0.34, oy + depth * 0.18, oz]
        rotation = [0.0, 90.0, 0.0]

    hinted = _placement_hint_transform(
        prop,
        zone_name=zone_name,
        zone=zone,
        room_origin=room_origin,
        room_dimensions=room_dimensions,
        fallback_location=location,
        fallback_rotation=rotation,
    )
    if hinted is not None:
        location = hinted["location"]
        rotation = hinted["rotation"]

    adjusted = _room_analysis_location_for_prop(
        prop,
        room_analysis=room_analysis or {},
        zone=zone,
        room_origin=room_origin,
        index=index,
        fallback_location=location,
        fallback_rotation=rotation,
    )
    if adjusted is not None:
        if hinted is not None:
            adjusted["placement_hint_source"] = hinted["source"]
            adjusted["placement_hint"] = hinted.get("placement_hint", "")
        return adjusted
    if hinted is not None:
        return hinted
    return {"location": [round(value, 3) for value in location], "rotation": rotation, "source": "zone_heuristic"}


def _tripo_spatial_fit_constraints(prop_id: str, constraints: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    relevant: List[Dict[str, Any]] = []
    for constraint in constraints:
        if not isinstance(constraint, Mapping):
            continue
        sources = constraint.get("sources") if isinstance(constraint.get("sources"), list) else []
        if constraint.get("source") != prop_id and prop_id not in [str(item) for item in sources]:
            continue
        relevant.append({
            key: value
            for key, value in {
                "kind": constraint.get("kind"),
                "target": constraint.get("target"),
                "target_role": constraint.get("target_role"),
                "sources": sources,
                "description": constraint.get("description"),
            }.items()
            if value not in (None, "", [])
        })
    return relevant[:8]


def _tripo_spatial_fit_for_prop(
    prop: Mapping[str, Any],
    *,
    prop_id: str,
    room_type: str,
    style: str,
    intent: str,
    transform: Mapping[str, Any],
    constraints: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    size = _size_vector(prop.get("size") or prop.get("approx_size_cm")) or [75.0, 75.0, 75.0]
    surface = str(prop.get("surface") or "floor").lower()
    zone = str(prop.get("zone") or "living")
    category = str(prop.get("category") or "prop")
    contact = {
        "floor": "stable flat base and origin/pivot at floor contact",
        "wall": "flat back or mounting face suitable for wall alignment",
        "counter": "stable underside sized for countertop contact",
        "table": "stable underside sized for table contact",
        "shelf": "compact underside sized for shelf contact",
        "cabinet": "stable underside or back face suitable for cabinet contact",
        "ceiling": "mount point suitable for ceiling alignment",
    }.get(surface, "clear contact face suitable for the requested support surface")
    fit_constraints = _tripo_spatial_fit_constraints(prop_id, constraints)
    return {
        "prop_id": prop_id,
        "room_type": room_type,
        "zone": zone,
        "surface": surface,
        "category": category,
        "style": str(style or "").strip(),
        "intent": str(intent or "").strip(),
        "approx_size_cm": _rounded_vector(size),
        "placement_source": str(transform.get("source") or ""),
        "placement_hint": str(transform.get("placement_hint") or prop.get("placement_hint") or ""),
        "support_actor": str(transform.get("support_actor") or ""),
        "contact_requirement": contact,
        "constraints": fit_constraints,
        "generation_requirements": _merge_unique(
            [
                "single prop asset only, not a full room",
                "real-world scale in Unreal centimeters",
                contact,
                "clean silhouette and simple collision-friendly shape",
                "PBR materials with no labels, text, watermark, characters, or merged furniture set",
            ],
            [str(item.get("description")) for item in fit_constraints if item.get("description")],
        ),
    }


def _tripo_spatial_fit_prompt(spatial_fit: Mapping[str, Any]) -> str:
    if not spatial_fit:
        return ""
    size = spatial_fit.get("approx_size_cm") if isinstance(spatial_fit.get("approx_size_cm"), list) else []
    size_text = " x ".join(str(int(float(value))) for value in size[:3]) if len(size) >= 3 else ""
    pieces = [
        "spatial fit",
        f"zone {spatial_fit.get('zone')}" if spatial_fit.get("zone") else "",
        f"surface/contact {spatial_fit.get('surface')}" if spatial_fit.get("surface") else "",
        f"target size about {size_text} cm" if size_text else "",
        str(spatial_fit.get("contact_requirement") or ""),
    ]
    for constraint in spatial_fit.get("constraints", []) if isinstance(spatial_fit.get("constraints"), list) else []:
        if isinstance(constraint, Mapping) and constraint.get("description"):
            pieces.append(str(constraint.get("description")))
    return "; ".join(piece for piece in pieces if piece)


def _tripo_prompt_for_prop(
    prop: Mapping[str, Any],
    *,
    room_type: str,
    style: str,
    intent: str,
    spatial_fit: Optional[Mapping[str, Any]] = None,
) -> str:
    size = _size_vector(prop.get("size") or prop.get("approx_size_cm")) or [100.0, 100.0, 100.0]
    size_text = " x ".join(str(int(float(value))) for value in size[:3])
    style_text = f"{style.strip()} " if str(style or "").strip() else ""
    intent_text = f" for {intent.strip()}" if str(intent or "").strip() else ""
    prompt = (
        f"{style_text}{prop['name']} game-ready static mesh for an Unreal Engine {room_type.replace('_', ' ')} interior"
        f"{intent_text}; real-world scale around {size_text} cm; PBR textured; clean topology; single prop asset; "
        "sensible origin at floor contact or mounting surface; no people, no text, no full room background"
    )
    fit_prompt = _tripo_spatial_fit_prompt(spatial_fit or {})
    return f"{prompt}; {fit_prompt}" if fit_prompt else prompt


def _tripo_spatial_generation_brief(
    *,
    prop_id: str,
    prop: Mapping[str, Any],
    prop_name: str,
    mode: str,
    room: Mapping[str, Any],
    spatial_fit: Mapping[str, Any],
    placement_after_import: Mapping[str, Any],
) -> Dict[str, Any]:
    placement_arguments = _placement_step_arguments(placement_after_import) if placement_after_import else {}
    size = (
        _size_vector(spatial_fit.get("approx_size_cm"))
        or _size_vector(prop.get("approx_size_cm") or prop.get("size"))
        or []
    )
    room_size = _size_vector(room.get("dimensions_cm"))
    placement: Dict[str, Any] = {
        "actor_label": str(placement_arguments.get("actor_label") or "").strip(),
        "location": _rounded_vector(_optional_vector3(placement_arguments.get("location")) or []),
        "rotation": _rounded_vector(_optional_vector3(placement_arguments.get("rotation")) or []),
        "scale": _rounded_vector(_optional_vector3(placement_arguments.get("scale")) or []),
        "placement_source": str(
            placement_arguments.get("placement_source")
            or placement_arguments.get("source")
            or spatial_fit.get("placement_source")
            or ""
        ).strip(),
        "support_actor": str(
            placement_arguments.get("support_actor")
            or spatial_fit.get("support_actor")
            or ""
        ).strip(),
        "support_roles": (
            [str(role) for role in placement_arguments.get("support_roles", [])]
            if isinstance(placement_arguments.get("support_roles"), list)
            else []
        ),
        "placement_hint": str(
            placement_arguments.get("placement_hint")
            or spatial_fit.get("placement_hint")
            or prop.get("placement_hint")
            or ""
        ).strip(),
    }
    placement = {key: value for key, value in placement.items() if value not in ("", [], None)}
    requirements = _merge_unique(
        spatial_fit.get("generation_requirements", []) if isinstance(spatial_fit.get("generation_requirements"), list) else [],
        [str(spatial_fit.get("contact_requirement") or "").strip()],
    )
    return {
        "schema": SPATIAL_GENERATION_BRIEF_SCHEMA,
        "id": prop_id,
        "prop_name": prop_name,
        "provider": "tripo",
        "mode": mode,
        "room": {
            "type": str(room.get("type") or spatial_fit.get("room_type") or "interior"),
            "dimensions_cm": _rounded_vector(room_size) if room_size else [],
            "style": str(room.get("style") or spatial_fit.get("style") or "").strip(),
            "intent": str(room.get("intent") or spatial_fit.get("intent") or "").strip(),
        },
        "zone": str(spatial_fit.get("zone") or prop.get("zone") or "").strip(),
        "surface": str(spatial_fit.get("surface") or prop.get("surface") or "").strip(),
        "category": str(spatial_fit.get("category") or prop.get("category") or "").strip(),
        "approx_size_cm": _rounded_vector(size) if size else [],
        "contact_requirement": str(spatial_fit.get("contact_requirement") or "").strip(),
        "placement": placement,
        "constraints": list(spatial_fit.get("constraints", [])) if isinstance(spatial_fit.get("constraints"), list) else [],
        "generation_requirements": requirements,
        "post_import_validation": {
            "fit_review_tool": "spatial_bind_generated_assets_to_composition",
            "scale_tool": "spatial_plan_asset_scale_corrections",
            "support_anchor_tool": "spatial_plan_support_surface_anchors",
            "layout_preflight_tool": "spatial_preflight_interior_layout",
            "placement_validation_tool": "spatial_validate_placement",
        },
    }


def _tripo_spatial_generation_brief_prompt(brief: Mapping[str, Any]) -> str:
    if not brief:
        return ""
    room = brief.get("room") if isinstance(brief.get("room"), Mapping) else {}
    placement = brief.get("placement") if isinstance(brief.get("placement"), Mapping) else {}
    dims = room.get("dimensions_cm") if isinstance(room.get("dimensions_cm"), list) else []
    dims_text = " x ".join(str(int(float(value))) for value in dims[:3]) if len(dims) >= 3 else ""
    size = brief.get("approx_size_cm") if isinstance(brief.get("approx_size_cm"), list) else []
    size_text = " x ".join(str(int(float(value))) for value in size[:3]) if len(size) >= 3 else ""
    pieces = [
        "spatial generation brief",
        f"room {room.get('type')} {dims_text} cm" if room.get("type") and dims_text else f"room {room.get('type')}" if room.get("type") else "",
        f"zone {brief.get('zone')}" if brief.get("zone") else "",
        f"surface/contact {brief.get('surface')}" if brief.get("surface") else "",
        f"target prop size {size_text} cm" if size_text else "",
        str(brief.get("contact_requirement") or ""),
        f"placement source {placement.get('placement_source')}" if placement.get("placement_source") else "",
        f"support {placement.get('support_actor')}" if placement.get("support_actor") else "",
        f"placement hint {placement.get('placement_hint')}" if placement.get("placement_hint") else "",
        "must remain a single standalone prop, not a merged room or furniture set",
    ]
    for constraint in brief.get("constraints", []) if isinstance(brief.get("constraints"), list) else []:
        if isinstance(constraint, Mapping) and constraint.get("description"):
            pieces.append(str(constraint.get("description")))
    return "; ".join(piece for piece in pieces if piece)[:1200]


def _handoff_with_spatial_generation_prompt(
    handoff: Mapping[str, Any],
    *,
    brief_prompt: str,
) -> Dict[str, Any]:
    updated = dict(handoff)
    arguments = dict(updated.get("arguments") or {}) if isinstance(updated.get("arguments"), Mapping) else {}
    prompt = str(arguments.get("prompt") or "").strip()
    if prompt and brief_prompt and brief_prompt not in prompt:
        arguments["prompt"] = f"{prompt.rstrip('; ')}; {brief_prompt}"[:2400]
    updated["arguments"] = arguments
    return updated


def _is_unresolved_handoff_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    return not text or (text.startswith("<") and text.endswith(">"))


def _image_to_model_crop_readiness(
    *,
    crop_task: Mapping[str, Any],
    submit: Mapping[str, Any],
) -> Dict[str, Any]:
    arguments = submit.get("arguments") if isinstance(submit.get("arguments"), Mapping) else {}
    image_path = str(arguments.get("image_path") or "").strip()
    image_url = str(arguments.get("image_url") or "").strip()
    file_token = str(arguments.get("file_token") or "").strip()
    output_placeholder = str(crop_task.get("output_placeholder") or "").strip()
    has_crop_guidance = bool(crop_task.get("crop_box") or crop_task.get("crop_hint"))

    if file_token and not _is_unresolved_handoff_placeholder(file_token):
        return {
            "ready": True,
            "status": "ready_with_file_token",
            "input_kind": "file_token",
            "input": file_token,
            "has_crop_guidance": has_crop_guidance,
            "reason": "Image-to-model job has a concrete Tripo file token.",
        }
    if image_url and not _is_unresolved_handoff_placeholder(image_url):
        return {
            "ready": image_url.lower().startswith(("http://", "https://")),
            "status": "ready_with_image_url" if image_url.lower().startswith(("http://", "https://")) else "invalid_image_url",
            "input_kind": "image_url",
            "input": image_url,
            "has_crop_guidance": has_crop_guidance,
            "reason": "Image-to-model job has a concrete image URL." if image_url.lower().startswith(("http://", "https://")) else "image_url must be an http(s) URL.",
        }
    if image_path and not _is_unresolved_handoff_placeholder(image_path):
        path = Path(image_path)
        if not path.is_absolute():
            path = (_REPO_ROOT / path).resolve()
        exists = path.exists()
        return {
            "ready": exists,
            "status": "ready_with_local_crop" if exists else "local_crop_missing",
            "input_kind": "image_path",
            "input": str(path),
            "has_crop_guidance": has_crop_guidance,
            "reason": "Local crop exists and can be submitted to image-to-model." if exists else "Run spatial_prepare_screenshot_crop_manifest or provide an existing local crop image before Tripo spend.",
        }
    return {
        "ready": False,
        "status": "needs_crop_manifest",
        "input_kind": "placeholder",
        "input": output_placeholder,
        "has_crop_guidance": has_crop_guidance,
        "reason": "Crop box or hint is available, but image-to-model still needs a real local crop path, image URL, or file token.",
        "next_tool": "spatial_prepare_screenshot_crop_manifest",
    }


def _semantic_prop_id(prop: Mapping[str, Any]) -> str:
    return _safe_asset_stem(str(prop.get("id") or prop.get("detected_item_id") or prop.get("name")), "Prop")


def _semantic_prop_text(prop: Mapping[str, Any]) -> str:
    aliases = prop.get("aliases") if isinstance(prop.get("aliases"), list) else []
    values = [
        prop.get("id", ""),
        prop.get("name", ""),
        prop.get("category", ""),
        prop.get("surface", ""),
        prop.get("zone", ""),
        *aliases,
    ]
    return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ") for value in values)


def _semantic_has_any(prop: Mapping[str, Any], tokens: Sequence[str]) -> bool:
    text = _semantic_prop_text(prop)
    return any(str(token).lower() in text for token in tokens)


def _semantic_counter_anchor(prop: Mapping[str, Any]) -> bool:
    text = _semantic_prop_text(prop)
    category = str(prop.get("category") or "").lower()
    if category == "counter":
        return True
    if "counter clutter" in text:
        return False
    return any(token in text for token in ("counter run", "countertop", "kitchen counter", "island"))


def _semantic_find_prop(props: Sequence[Mapping[str, Any]], tokens: Sequence[str]) -> Optional[Mapping[str, Any]]:
    for prop in props:
        if _semantic_has_any(prop, tokens):
            return prop
    return None


def _semantic_location(item: Mapping[str, Any]) -> List[float]:
    value = item.get("location")
    if value in (None, "", []):
        placement = item.get("placement") if isinstance(item.get("placement"), Mapping) else {}
        value = placement.get("location")
    try:
        raw = [float(component) for component in list(value)[:3]]
    except Exception:
        return []
    return raw if len(raw) == 3 else []


def _composition_semantic_constraints(props: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    constraints: List[Dict[str, Any]] = []
    props = [prop for prop in props if isinstance(prop, Mapping)]
    if not props:
        return constraints

    def add(record: Dict[str, Any]) -> None:
        record = {key: value for key, value in record.items() if value not in (None, "", [])}
        key = (
            record.get("kind"),
            record.get("source"),
            record.get("target"),
            tuple(record.get("sources", []) if isinstance(record.get("sources"), list) else []),
        )
        existing = {
            (
                item.get("kind"),
                item.get("source"),
                item.get("target"),
                tuple(item.get("sources", []) if isinstance(item.get("sources"), list) else []),
            )
            for item in constraints
        }
        if key not in existing:
            constraints.append(record)

    counter = next((prop for prop in props if _semantic_counter_anchor(prop)), None)
    refrigerator = _semantic_find_prop(props, ("refrigerator", "fridge"))
    stove = _semantic_find_prop(props, ("stove", "oven", "range"))
    sink = _semantic_find_prop(props, ("sink",))
    sofa = _semantic_find_prop(props, ("sofa", "couch"))
    coffee_table = _semantic_find_prop(props, ("coffee table",))
    rug = _semantic_find_prop(props, ("rug", "carpet"))
    bed = _semantic_find_prop(props, ("bed",))
    nightstand = _semantic_find_prop(props, ("nightstand", "bedside table"))
    dresser = _semantic_find_prop(props, ("dresser", "wardrobe"))
    hallway_props = [
        prop for prop in props
        if str(prop.get("zone") or "").lower() == "hallway"
        or _semantic_has_any(prop, ("hallway", "hall runner", "runner rug", "wall hooks", "shoe bench", "corridor"))
    ]

    for prop in props:
        prop_id = _semantic_prop_id(prop)
        name = str(prop.get("name") or prop_id)
        surface = str(prop.get("surface") or "").lower()
        category = str(prop.get("category") or "").lower()
        if surface in {"counter", "table", "shelf", "cabinet"} or (
            category in {"fixture", "dressing"} and surface not in {"", "floor", "wall", "ceiling"}
        ):
            add({
                "kind": "support_contact",
                "source": prop_id,
                "target_role": _support_surface_kind(surface) or surface or "horizontal_support",
                "description": f"Place {name} on a valid {surface or 'support'} surface with visible contact.",
            })
        if surface == "wall" or _semantic_has_any(prop, ("wall cabinet", "upper cabinet")):
            add({
                "kind": "wall_anchor",
                "source": prop_id,
                "description": f"Keep {name} aligned to a wall surface and validate mounting height.",
            })
        if counter is not None and prop is not counter and (
            surface == "counter"
            or category in {"fixture", "dressing", "appliance", "seating"}
            or _semantic_has_any(prop, ("sink", "stove", "oven", "fridge", "refrigerator", "bar stool", "small appliance"))
        ):
            max_distance = 150.0 if _semantic_has_any(prop, ("bar stool", "stool", "counter clutter", "small appliance")) else 240.0
            add({
                "kind": "counter_adjacency",
                "source": prop_id,
                "target": _semantic_prop_id(counter),
                "max_distance_cm": max_distance,
                "description": f"Keep {name} spatially tied to the counter run or island.",
            })

    if refrigerator is not None and stove is not None and sink is not None:
        add({
            "kind": "kitchen_work_triangle",
            "sources": [_semantic_prop_id(refrigerator), _semantic_prop_id(stove), _semantic_prop_id(sink)],
            "min_edge_cm": 90.0,
            "max_edge_cm": 360.0,
            "max_total_cm": 820.0,
            "description": "Keep refrigerator, stove or oven, and sink in a compact kitchen work triangle with clear access.",
        })

    if sofa is not None and coffee_table is not None:
        sources = [_semantic_prop_id(sofa), _semantic_prop_id(coffee_table)]
        if rug is not None:
            sources.append(_semantic_prop_id(rug))
        add({
            "kind": "living_visual_group",
            "sources": sources,
            "min_distance_cm": 45.0,
            "max_distance_cm": 280.0,
            "description": "Keep sofa, coffee table, and optional rug composed as one readable living-area group.",
        })

    if bed is not None:
        sources = [_semantic_prop_id(bed)]
        if nightstand is not None:
            sources.append(_semantic_prop_id(nightstand))
        if dresser is not None:
            sources.append(_semantic_prop_id(dresser))
        if len(sources) > 1:
            add({
                "kind": "bedroom_anchor_group",
                "sources": sources,
                "bedside_min_distance_cm": 35.0,
                "bedside_max_distance_cm": 170.0,
                "dresser_max_distance_cm": 320.0,
                "description": "Keep bedroom furniture readable around the bed, with nightstand access and dresser spacing.",
            })

    if any(str(prop.get("surface") or "").lower() == "floor" for prop in props):
        add({
            "kind": "circulation_clearance",
            "min_walkway_cm": 90.0,
            "description": "Keep a conservative central circulation path open for apartment navigation and viewport readability.",
        })

    if hallway_props:
        add({
            "kind": "hallway_linear_clearance",
            "sources": [_semantic_prop_id(prop) for prop in hallway_props],
            "max_floor_prop_cross_section_cm": 90.0,
            "min_clear_path_cm": 90.0,
            "description": "Keep hallway props narrow or wall-hugging so the corridor remains readable and traversable.",
        })

    return constraints[:128]


def _plan_interior_composition(
    *,
    room_type: str,
    room_dimensions: Sequence[float],
    room_origin: Sequence[float],
    functional_zone_plan: Optional[Mapping[str, Any]],
    prop_program: Optional[Mapping[str, Any]],
    style: str,
    intent: str,
    screenshot_reference: str,
    screenshot_observations: Sequence[str],
    existing_asset_paths: Sequence[str],
    required_props: Sequence[str],
    omit_props: Sequence[str],
    content_path: str,
    actor_label_prefix: str,
    generate_missing_with_tripo: bool,
    include_image_to_model_handoffs: bool,
    limit: int,
    detected_items: Sequence[Mapping[str, Any]] = (),
    room_analysis: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    analysis = room_analysis or {}
    zone_plan = functional_zone_plan or {}
    program_plan = prop_program or {}
    zones = (
        list(zone_plan.get("zones", []) or [])
        if zone_plan
        else list(analysis.get("zones", []) or []) if analysis else _room_zones(room_type, room_origin, room_dimensions)
    )
    zone_lookup = {zone["name"]: zone for zone in zones}
    props = (
        [dict(prop) for prop in program_plan.get("props", []) if isinstance(prop, Mapping)][:limit]
        if program_plan
        else _select_interior_props(
            room_type=room_type,
            required_props=required_props,
            omit_props=omit_props,
            screenshot_observations=screenshot_observations,
            detected_items=detected_items,
            limit=limit,
        )
    )
    semantic_constraints = _composition_semantic_constraints(props)

    planned_props = []
    generation_tasks = []
    placement_steps = []
    data_layers = ["World_Interiors", f"Interior_{_safe_asset_stem(room_type, 'Room')}"]
    label_prefix = _safe_asset_stem(actor_label_prefix or room_type, "Interior")

    for index, prop in enumerate(props):
        prop_id = _safe_asset_stem(str(prop.get("id") or prop["name"]), "Prop")
        matched_asset = str(prop.get("existing_asset_path") or "").strip() or _match_existing_asset(prop, existing_asset_paths)
        transform = _prop_location(
            prop,
            zone_lookup=zone_lookup,
            room_origin=room_origin,
            room_dimensions=room_dimensions,
            index=index,
            room_analysis=analysis,
        )
        spatial_fit = _tripo_spatial_fit_for_prop(
            prop,
            prop_id=prop_id,
            room_type=room_type,
            style=style,
            intent=intent,
            transform=transform,
            constraints=semantic_constraints,
        )
        actor_label = f"{label_prefix}_{prop_id}"
        tags = _merge_unique(["Interior", f"Zone_{prop.get('zone', 'living')}", str(prop.get("category", "prop"))])
        asset_placeholder = matched_asset or f"{content_path}/{prop_id}.{prop_id}"
        source = "existing_asset" if matched_asset else ("tripo_candidate" if generate_missing_with_tripo else "missing_asset")

        prop_plan = {
            "id": prop_id,
            "name": prop["name"],
            "category": prop.get("category", "prop"),
            "zone": prop.get("zone", "living"),
            "source": source,
            "matched_asset_path": matched_asset,
            "asset_path_placeholder": asset_placeholder,
            "surface": prop.get("surface", "floor"),
            "approx_size_cm": prop.get("size", [75, 75, 75]),
            "spatial_fit": spatial_fit,
            "placement": {
                "actor_label": actor_label,
                "location": transform["location"],
                "rotation": transform["rotation"],
                "scale": [1.0, 1.0, 1.0],
                "clearance_padding": 12.0 if prop.get("surface") == "floor" else 4.0,
                "source": transform.get("source", "zone_heuristic"),
            },
        }
        if transform.get("support_actor"):
            prop_plan["placement"]["support_actor"] = transform["support_actor"]
        if transform.get("support_roles"):
            prop_plan["placement"]["support_roles"] = transform["support_roles"]
        if transform.get("placement_hint_source"):
            prop_plan["placement"]["placement_hint_source"] = transform["placement_hint_source"]
        if transform.get("placement_hint"):
            prop_plan["placement"]["placement_hint"] = transform["placement_hint"]
        if prop.get("screenshot_evidence"):
            prop_plan["screenshot_evidence"] = prop["screenshot_evidence"]
        if prop.get("detected_item_id"):
            prop_plan["detected_item_id"] = prop["detected_item_id"]
        if prop.get("count") not in (None, 1):
            prop_plan["count"] = int(prop.get("count", 1) or 1)
        if prop.get("crop_box"):
            prop_plan["crop_box"] = prop["crop_box"]
        if prop.get("crop_hint"):
            prop_plan["crop_hint"] = prop["crop_hint"]
        if prop.get("placement_hint"):
            prop_plan["placement_hint"] = prop["placement_hint"]
        if prop.get("confidence"):
            prop_plan["confidence"] = prop["confidence"]
        planned_props.append(prop_plan)

        if not matched_asset and generate_missing_with_tripo:
            text_prompt = _tripo_prompt_for_prop(prop, room_type=room_type, style=style, intent=intent, spatial_fit=spatial_fit)
            generation_task = {
                "id": prop_id,
                "provider": "tripo",
                "prop_name": prop["name"],
                "spatial_fit": spatial_fit,
                "submit": {
                    "tool": "gen_tripo_text_to_model",
                    "arguments": {
                        "prompt": text_prompt,
                        "texture": True,
                        "pbr": True,
                        "smart_low_poly": True,
                        "auto_size": True,
                        "session_name": f"spatial_{_safe_asset_stem(room_type, 'room').lower()}",
                        "confirm_spend": False,
                    },
                },
                "wait": {"tool": "gen_tripo_wait_for_task", "arguments": {"task_id": f"<TRIPO_TASK_ID_FOR_{prop_id}>"}},
                "import": {
                    "tool": "gen_tripo_import_to_project",
                    "arguments": {
                        "task_id": f"<TRIPO_TASK_ID_FOR_{prop_id}>",
                        "content_path": content_path,
                        "asset_name": prop_id,
                        "create_material_instance": True,
                        "capture_thumbnail": True,
                    },
                },
                "negative_prompt": "people, characters, labels, watermark, entire room, merged furniture set, distorted scale",
            }
            if screenshot_reference and include_image_to_model_handoffs:
                reference_key = "image_url" if screenshot_reference.lower().startswith(("http://", "https://")) else "image_path"
                generation_task["reference_image_variant"] = {
                    "tool": "gen_tripo_image_to_model",
                    "crop_required": True,
                    "crop_instruction": f"Crop only the {prop['name']} from the reference image before submitting.",
                    "spatial_fit": spatial_fit,
                    "arguments": {
                        reference_key: f"<CROP_FOR_{prop_id}>",
                        "texture": True,
                        "pbr": True,
                        "smart_low_poly": True,
                        "auto_size": True,
                        "session_name": f"spatial_{_safe_asset_stem(room_type, 'room').lower()}",
                        "confirm_spend": False,
                    },
                    "source_reference": screenshot_reference,
                }
            generation_tasks.append(generation_task)

        placement_steps.append({
            "id": prop_id,
            "tool": "spatial_add_asset_to_scene",
            "arguments": {
                "asset_path": asset_placeholder if matched_asset else f"<IMPORTED_ASSET_PATH_FOR_{prop_id}>",
                "actor_label": actor_label,
                "location": transform["location"],
                "rotation": transform["rotation"],
                "scale": [1.0, 1.0, 1.0],
                "placement_source": transform.get("source", "zone_heuristic"),
                "placement_hint_source": transform.get("placement_hint_source", ""),
                "tags": tags,
                "data_layer_names": data_layers,
                "dry_run": True,
                "allow_mutation": False,
                "select_actor": True,
                "focus_viewport": False,
            },
        })

    composition_constraints = _composition_semantic_constraints(planned_props)
    analysis_probe_points = _room_analysis_probe_points(analysis) if analysis else []
    probe_points = _merge_vector_lists(
        analysis_probe_points,
        [step["arguments"]["location"] for step in placement_steps[: min(12, len(placement_steps))]],
        maximum=32,
    )
    validation_padding = _room_analysis_validation_padding(analysis, default=12.0) if analysis else 12.0
    measure_step = (
        {"step": "measure_space", "tool": "spatial_analyze_room", "reason": "Use live actor bounds, surfaces, zones, and clearance risks as planner context."}
        if analysis
        else {"step": "measure_space", "tool": "spatial_scene_overview", "reason": "Confirm actor bounds and current room extents."}
    )
    return {
        "schema": INTERIOR_COMPOSITION_SCHEMA,
        "goal": "Understand an interior space, generate missing props through Tripo, and place a coherent environment composition in Unreal.",
        "room": {
            "type": room_type,
            "dimensions_cm": list(room_dimensions),
            "origin": list(room_origin),
            "style": style,
            "intent": intent,
        },
        "room_analysis": _room_analysis_summary(analysis),
        "functional_zone_inference": {
            "applied": bool(zone_plan),
            "schema": zone_plan.get("schema") if zone_plan else "",
            "status": zone_plan.get("status") if zone_plan else "",
            "zone_names": list(zone_plan.get("zone_names", [])) if isinstance(zone_plan.get("zone_names"), list) else [zone.get("name") for zone in zones],
            "evidence_count": int(zone_plan.get("evidence_count") or 0) if zone_plan else 0,
        },
        "prop_program": _prop_program_summary(program_plan, planned_props),
        "zones": zones,
        "props": planned_props,
        "prop_count": len(planned_props),
        "composition_constraints": composition_constraints,
        "constraint_count": len(composition_constraints),
        "missing_prop_count": sum(1 for prop in planned_props if prop["source"] != "existing_asset"),
        "generation_tasks": generation_tasks,
        "generation_task_count": len(generation_tasks),
        "screenshot_decomposition": {
            "reference": screenshot_reference,
            "observations": list(screenshot_observations),
            "contract": [
                "Segment the reference into individual props, fixtures, architectural pieces, and clutter groups.",
                "Prefer one crop per prop before using gen_tripo_image_to_model.",
                "Record approximate scale, wall/floor contact, occlusion, and zone for each prop.",
                "Map each item to either an existing Content Browser asset or a Tripo generation task.",
            ],
            "ready": bool(screenshot_observations),
        },
        "workflow": [
            measure_step,
            {"step": "infer_functional_zones", "tool": "spatial_infer_functional_zones", "enabled": not bool(zone_plan), "reason": "Convert room analysis and screenshot/composition hints into functional kitchen/living/bedroom/entry/hallway/utility zones."},
            {"step": "plan_prop_program", "tool": "spatial_plan_interior_prop_program", "enabled": not bool(program_plan), "reason": "Confirm fixtures, furniture, clutter, architectural fill, and missing-asset candidates before composition."},
            {"step": "probe_surfaces", "tool": "spatial_surface_probe", "arguments": {"points": probe_points, "placement_offset": 0.0}, "reason": "Confirm floor/counter/wall surface contact before placement."},
            {"step": "review_composition_constraints", "constraints": composition_constraints, "reason": "Review support contact, adjacency, work-triangle, grouping, and circulation intent before placement."},
            {"step": "generate_missing_assets", "tools": ["gen_tripo_text_to_model", "gen_tripo_image_to_model"], "reason": "Submit only after user approval and Tripo spend confirmation."},
            {"step": "import_generated_assets", "tool": "gen_tripo_import_to_project", "reason": "Import successful Tripo model outputs into the project."},
            {"step": "place_assets", "tool": "spatial_add_asset_to_scene", "placement_steps": placement_steps},
            {"step": "validate_composition", "tool": "spatial_validate_placement", "arguments": {"actors": [step["arguments"]["actor_label"] for step in placement_steps], "surface_tolerance": 15.0, "clearance_padding": validation_padding}, "reason": "Check surface contact and conservative bounds overlap."},
            {"step": "capture_evidence", "tools": ["spatial_select_actors", "focus_viewport", "viewport_capture_screenshot"], "reason": "Frame the final composition for review and iteration."},
        ],
        "placement_steps": placement_steps,
        "validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": [step["arguments"]["actor_label"] for step in placement_steps],
                "surface_tolerance": 15.0,
                "clearance_padding": validation_padding,
                "include_evidence_handoff": True,
            },
        },
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is Ghost-owned planning data and does not copy Epic SceneTools source.",
                "Any future close reuse of Epic native SceneTools behavior or source should receive legal review.",
            ],
        },
    }


def _screenshot_detection_schema() -> Dict[str, Any]:
    return {
        "type": "json_list",
        "description": "One object per visible prop, fixture, clutter group, or architectural fill piece from the reference image.",
        "fields": {
            "name": "Required short prop label, for example refrigerator, bar stool, books, or wall cabinets.",
            "category": "Optional role such as appliance, counter, storage, seating, dressing, lighting, decor, or fixture.",
            "zone": "Optional room zone such as kitchen, living, bedroom, entry, bathroom, or hallway.",
            "surface": "Optional contact target such as floor, wall, counter, table, shelf, ceiling, or cabinet.",
            "count": "Optional count for repeated props. Keep repeated identical objects grouped unless their placements differ.",
            "crop_box": "Optional [x, y, width, height] crop in source-image pixels for image-to-model generation.",
            "crop_hint": "Optional visual description when exact pixel crop is unavailable.",
            "placement_hint": "Optional spatial relationship, for example against left wall, on coffee table, under cabinets.",
            "approx_size_cm": "Optional [width, depth, height] in Unreal centimeters.",
            "existing_asset_path": "Optional /Game path when a matching project asset is already known.",
            "confidence": "Optional detection confidence from 0.0 to 1.0.",
        },
        "example": [
            {
                "name": "refrigerator",
                "category": "appliance",
                "zone": "kitchen",
                "surface": "floor",
                "crop_box": [42, 80, 210, 460],
                "placement_hint": "against the left kitchen wall",
                "approx_size_cm": [90, 80, 190],
                "confidence": 0.82,
            }
        ],
    }


def _screenshot_decomposition_targets(room_type: str, include_architectural_fill: bool) -> List[str]:
    targets = [
        "major furniture and appliances",
        "fixtures such as sinks, lighting, cabinets, doors, windows, and built-ins",
        "surface props such as books, dishes, appliances, plants, pillows, and counter clutter",
        "support surfaces including floors, walls, counters, tables, shelves, cabinet tops, and ceilings",
        "room zones such as kitchen, living, bedroom, hallway, bathroom, entry, or utility",
        "clearances and circulation paths implied by doors, seating, counters, and walkways",
    ]
    if room_type in {"apartment", "studio", "kitchen"}:
        targets.extend([
            "kitchen work-triangle anchors: refrigerator, stove or oven, and sink",
            "counter adjacency: stools, small appliances, sink, stove, and clutter near the counter run",
        ])
    if room_type in {"apartment", "studio", "living_room"}:
        targets.append("living-area visual groups such as sofa, coffee table, rug, bookshelf, lamps, and decor")
    if include_architectural_fill:
        targets.append("architectural fill pieces such as wall panels, trim, backsplash, rails, columns, alcoves, and utility runs")
    return targets


def _plan_screenshot_decomposition_request(
    *,
    reference_image: str,
    image_size: Optional[Sequence[float]],
    room_type: str,
    room_dimensions: Sequence[float],
    room_origin: Sequence[float],
    room_analysis: Mapping[str, Any],
    style: str,
    intent: str,
    include_architectural_fill: bool,
    prefer_crop_boxes: bool,
    max_items: int,
) -> Dict[str, Any]:
    schema = _screenshot_detection_schema()
    targets = _screenshot_decomposition_targets(room_type, include_architectural_fill)
    room_analysis_summary = _room_analysis_summary(room_analysis)
    room_text = f"{room_type.replace('_', ' ')} interior, Unreal room dimensions {int(room_dimensions[0])} x {int(room_dimensions[1])} x {int(room_dimensions[2])} cm"
    style_text = f" Style: {style.strip()}." if str(style or "").strip() else ""
    intent_text = f" Build intent: {intent.strip()}." if str(intent or "").strip() else ""
    image_size_text = f" Image size: {int(image_size[0])} x {int(image_size[1])} px." if image_size else ""
    prompt_lines = [
        f"Analyze the reference image for spatial Unreal Engine interior reconstruction: {reference_image}.",
        room_text + "." + style_text + intent_text + image_size_text,
        "Return only JSON: a list of detected item objects matching the supplied detected_items_schema.",
        "Create one item for every prop, fixture, furniture item, clutter group, support surface, or architectural fill piece that should become a separately placeable Unreal asset or placement constraint.",
        "Infer zone, surface/contact target, approximate real-world size in Unreal centimeters, and placement_hint for each item.",
        "Use existing_asset_path only when the project asset is already known; otherwise leave it empty so Ghost can resolve project assets or prepare guarded Tripo generation.",
    ]
    if prefer_crop_boxes:
        prompt_lines.append("Provide crop_box [x, y, width, height] in source-image pixels for every object that may need Tripo image-to-model generation.")
    else:
        prompt_lines.append("Provide crop_hint when exact pixel crop boxes are not available; crop_box is preferred when possible.")
    prompt_lines.extend([
        "Group repeated identical objects only when their spatial placement is the same; split them when placement, zone, or support surface differs.",
        "Do not include people, animals, logos, watermarks, full-room backgrounds, or text signs as generation targets.",
        f"Maximum items: {max_items}. Prioritize: " + "; ".join(targets),
    ])

    output_contract = {
        "format": "detected_items_json",
        "schema": schema,
        "max_items": max_items,
        "quality_rules": [
            "Every item must have name.",
            "Prefer zone, surface, placement_hint, approx_size_cm, and confidence for every item.",
            "Use crop_box for Tripo candidates when image pixels are known.",
            "Keep generated-model targets as single props, not merged room sets.",
            "Use conservative sizes in Unreal centimeters and note uncertainty through confidence.",
        ],
    }
    workflow = [
        {
            "step": "vision_decompose_reference",
            "actor": "agent_vision",
            "prompt": "\n".join(prompt_lines),
            "output": "detected_items_json",
        },
        {
            "step": "preflight_detections",
            "tool": "spatial_preflight_screenshot_detections",
            "arguments": {
                "reference_image": reference_image,
                "detected_items_json": "<DETECTED_ITEMS_JSON_FROM_VISION>",
                "image_size": list(image_size) if image_size else [],
                "room_type": room_type,
                "require_crop_boxes": prefer_crop_boxes,
                "limit": max_items,
            },
        },
        {
            "step": "infer_scene_graph",
            "tool": "spatial_infer_screenshot_scene_graph",
            "arguments": {
                "reference_image": reference_image,
                "detected_items_json": "<NORMALIZED_DETECTED_ITEMS_JSON>",
                "image_size": list(image_size) if image_size else [],
                "room_type": room_type,
            },
        },
        {
            "step": "plan_reconstruction",
            "tool": "spatial_plan_screenshot_reconstruction",
            "arguments": {
                "reference_image": reference_image,
                "detected_items_json": "<NORMALIZED_DETECTED_ITEMS_JSON>",
                "scene_graph_json": "<SCREENSHOT_SCENE_GRAPH_JSON>",
                "room_type": room_type,
                "room_dimensions": list(room_dimensions),
                "room_origin": list(room_origin),
                "style": style,
                "intent": intent,
            },
        },
        {
            "step": "crop_generate_bind_apply_validate",
            "tools": [
                "spatial_prepare_screenshot_crop_manifest",
                "spatial_prepare_tripo_generation_batch",
                "spatial_bind_generated_assets_to_composition",
                "spatial_apply_composition_plan",
                "spatial_validate_placement",
            ],
            "reason": "Use cropped prop images and guarded spend confirmation before importing, binding, spatial-fit review, dry-run placement, and validation.",
        },
    ]
    return {
        "schema": SCREENSHOT_DECOMPOSITION_REQUEST_SCHEMA,
        "status": "ready_for_vision_decomposition",
        "reference_image": reference_image,
        "image_size": list(image_size) if image_size else [],
        "room": {
            "type": room_type,
            "dimensions_cm": list(room_dimensions),
            "origin": list(room_origin),
            "style": style,
            "intent": intent,
        },
        "room_analysis": room_analysis_summary,
        "decomposition_targets": targets,
        "detected_items_schema": schema,
        "output_contract": output_contract,
        "vision_prompt": "\n".join(prompt_lines),
        "preflight_handoff": workflow[1],
        "scene_graph_handoff": workflow[2],
        "reconstruction_handoff": workflow[3],
        "workflow": workflow,
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is a Ghost-owned decomposition request and tool handoff schema; it does not perform or copy Epic vision/SceneTools code.",
                "Vision model outputs and generated assets still require human review, Tripo spend confirmation, spatial-fit review, dry-run placement, and validation.",
            ],
        },
    }


def _reference_image_argument_key(reference_image: str) -> str:
    return "image_url" if reference_image.lower().startswith(("http://", "https://")) else "image_path"


def _crop_task_for_detected_item(
    item: Mapping[str, Any],
    *,
    reference_image: str,
    room_type: str,
) -> Dict[str, Any]:
    item_id = _safe_asset_stem(str(item.get("id") or item.get("name")), "DetectedProp")
    placeholder = f"<CROP_FOR_{item_id}>"
    ready = bool(item.get("crop_box") or item.get("crop_hint"))
    return {
        "id": item_id,
        "name": item.get("name", item_id),
        "source_reference": reference_image,
        "crop_box": item.get("crop_box"),
        "crop_hint": item.get("crop_hint") or f"Crop only the {item.get('name', 'prop')} from the reference image.",
        "output_placeholder": placeholder,
        "ready_for_image_to_model": ready,
        "tool": "gen_tripo_image_to_model",
        "arguments": {
            _reference_image_argument_key(reference_image): placeholder,
            "texture": True,
            "pbr": True,
            "smart_low_poly": True,
            "auto_size": True,
            "session_name": f"spatial_{_safe_asset_stem(room_type, 'room').lower()}",
            "confirm_spend": False,
        },
        "notes": [
            "Submit a cropped image file, not the full room screenshot.",
            "Keep confirm_spend=false until the user explicitly approves Tripo cost.",
        ],
    }


def _local_filesystem_path(value: str, field_name: str) -> Path:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        raise ValueError(f"{field_name} is required")
    if text.lower().startswith(("http://", "https://")):
        raise ValueError(f"{field_name} must be a local image file path for crop extraction")
    path = Path(text)
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    return path


def _crop_output_dir(value: str) -> Path:
    text = str(value or "Saved/MCPChat/spatial_crops").strip().replace("\\", "/")
    if not text:
        text = "Saved/MCPChat/spatial_crops"
    if text.lower().startswith(("http://", "https://")):
        raise ValueError("crop_output_dir must be a local folder path")
    path = Path(text)
    if not path.is_absolute():
        path = (_REPO_ROOT / path).resolve()
    return path


def _screenshot_crop_source(
    *,
    reference_image: str,
    detected_items_json: str,
    reconstruction_plan_json: str,
    limit: int,
) -> tuple[Dict[str, Any], str, List[Dict[str, Any]]]:
    text = str(reconstruction_plan_json or "").strip()
    if text:
        parsed = _json_object_from_text(text, "reconstruction_plan_json")
        outputs = parsed.get("outputs") if parsed.get("schema") == SPATIAL_RESULT_SCHEMA else parsed
        if not isinstance(outputs, Mapping):
            raise ValueError("reconstruction_plan_json.outputs must be an object")
        source_outputs = dict(outputs)
        if source_outputs.get("schema") != SCREENSHOT_RECONSTRUCTION_SCHEMA:
            raise ValueError(f"reconstruction_plan_json must have schema {SCREENSHOT_RECONSTRUCTION_SCHEMA}")
        source_reference = _clean_reference_image(reference_image or str(source_outputs.get("reference_image") or ""))
        crop_tasks = source_outputs.get("crop_tasks") if isinstance(source_outputs.get("crop_tasks"), list) else []
        tasks: List[Dict[str, Any]] = []
        for index, task in enumerate(crop_tasks[:limit]):
            if not isinstance(task, Mapping):
                continue
            task_dict = dict(task)
            task_dict["id"] = _safe_asset_stem(str(task_dict.get("id") or task_dict.get("name") or f"Crop{index}"), "Crop")
            task_dict["name"] = str(task_dict.get("name") or task_dict["id"])
            task_dict["crop_box"] = _crop_box(task_dict.get("crop_box"), f"reconstruction_plan_json.crop_tasks[{index}].crop_box")
            task_dict["source_reference"] = str(task_dict.get("source_reference") or source_reference)
            tasks.append(task_dict)
        return source_outputs, source_reference, tasks

    clean_reference = _clean_reference_image(reference_image)
    detected_items = _detected_items_from_json(detected_items_json, maximum=limit)
    if not detected_items:
        raise ValueError("detected_items_json or reconstruction_plan_json is required")
    tasks = [
        _crop_task_for_detected_item(item, reference_image=clean_reference, room_type=str(item.get("zone") or "apartment"))
        for item in detected_items[:limit]
    ]
    return {
        "schema": "unreal_mcp_ghost.spatial_detected_items_for_cropping.v1",
        "reference_image": clean_reference,
        "crop_tasks": tasks,
    }, clean_reference, tasks


def _padded_pixel_crop_box(
    *,
    crop_box: Sequence[float],
    image_width: int,
    image_height: int,
    padding_px: float,
) -> Dict[str, Any]:
    x, y, width, height = [float(value) for value in crop_box]
    left = int(math.floor(x - padding_px))
    top = int(math.floor(y - padding_px))
    right = int(math.ceil(x + width + padding_px))
    bottom = int(math.ceil(y + height + padding_px))
    clipped_left = max(0, min(image_width, left))
    clipped_top = max(0, min(image_height, top))
    clipped_right = max(0, min(image_width, right))
    clipped_bottom = max(0, min(image_height, bottom))
    return {
        "requested": [left, top, right, bottom],
        "clipped": [clipped_left, clipped_top, clipped_right, clipped_bottom],
        "width": max(0, clipped_right - clipped_left),
        "height": max(0, clipped_bottom - clipped_top),
        "was_clipped": [left, top, right, bottom] != [clipped_left, clipped_top, clipped_right, clipped_bottom],
    }


def _updated_reconstruction_with_crop_paths(
    *,
    source_outputs: Mapping[str, Any],
    crop_records: Sequence[Mapping[str, Any]],
) -> str:
    if source_outputs.get("schema") != SCREENSHOT_RECONSTRUCTION_SCHEMA:
        return ""
    crop_by_id = {
        str(record.get("id") or ""): record
        for record in crop_records
        if record.get("status") in {"written", "exists"} and record.get("output_path")
    }
    if not crop_by_id:
        return json.dumps(dict(source_outputs), sort_keys=True)
    updated = json.loads(json.dumps(source_outputs))
    for task in updated.get("crop_tasks", []) if isinstance(updated.get("crop_tasks"), list) else []:
        task_id = str(task.get("id") or "")
        record = crop_by_id.get(task_id)
        if not record:
            continue
        output_path = str(record.get("output_path") or "")
        task["output_placeholder"] = output_path
        task["ready_for_image_to_model"] = True
        arguments = task.get("arguments") if isinstance(task.get("arguments"), dict) else {}
        arguments.pop("image_url", None)
        arguments["image_path"] = output_path
        arguments["confirm_spend"] = False
        task["arguments"] = arguments
    for mapping in updated.get("asset_mapping", []) if isinstance(updated.get("asset_mapping"), list) else []:
        handoff = mapping.get("handoff") if isinstance(mapping.get("handoff"), dict) else {}
        record = crop_by_id.get(str(handoff.get("crop_task_id") or mapping.get("id") or ""))
        if record:
            mapping["source"] = str(record.get("output_path") or "")
    return json.dumps(updated, sort_keys=True)


def _plan_screenshot_crop_manifest(
    *,
    reference_image: str,
    detected_items_json: str,
    reconstruction_plan_json: str,
    crop_output_dir: str,
    image_size: Optional[Sequence[float]],
    padding_px: float,
    min_crop_px: int,
    overwrite: bool,
    limit: int,
) -> Dict[str, Any]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow/PIL is required to crop screenshot reference images") from exc

    source_outputs, source_reference, crop_tasks = _screenshot_crop_source(
        reference_image=reference_image,
        detected_items_json=detected_items_json,
        reconstruction_plan_json=reconstruction_plan_json,
        limit=limit,
    )
    source_path = _local_filesystem_path(source_reference, "reference_image")
    if not source_path.exists() or not source_path.is_file():
        raise ValueError("reference_image must be an existing local image file")
    output_dir = _crop_output_dir(crop_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    issues: List[Dict[str, Any]] = []
    crop_records: List[Dict[str, Any]] = []
    handoffs: List[Dict[str, Any]] = []
    with Image.open(source_path) as image:
        image_width, image_height = image.size
        declared_size = list(image_size) if image_size else []
        if declared_size and [float(image_width), float(image_height)] != [float(declared_size[0]), float(declared_size[1])]:
            issues.append({
                "severity": "warning",
                "kind": "image_size_mismatch",
                "message": "Supplied image_size does not match the opened reference image dimensions.",
                "actual_size": [image_width, image_height],
                "declared_size": declared_size,
            })
        for index, task in enumerate(crop_tasks):
            task_id = _safe_asset_stem(str(task.get("id") or f"Crop{index}"), "Crop")
            name = str(task.get("name") or task_id)
            crop_box = task.get("crop_box")
            if not crop_box:
                issues.append({"severity": "warning", "kind": "missing_crop_box", "id": task_id, "item": name, "message": "Crop task has no crop_box."})
                crop_records.append({"id": task_id, "name": name, "status": "missing_crop_box", "output_path": ""})
                continue
            pixel_box = _padded_pixel_crop_box(
                crop_box=crop_box,
                image_width=image_width,
                image_height=image_height,
                padding_px=padding_px,
            )
            if pixel_box["was_clipped"]:
                issues.append({"severity": "warning", "kind": "crop_box_clipped_to_image", "id": task_id, "item": name, "message": "Crop box was clipped to image bounds."})
            if pixel_box["width"] < min_crop_px or pixel_box["height"] < min_crop_px:
                issues.append({"severity": "warning", "kind": "crop_too_small", "id": task_id, "item": name, "message": "Crop is too small for reliable image-to-model generation."})
                crop_records.append({"id": task_id, "name": name, "status": "too_small", "output_path": "", "padded_crop_box": pixel_box["clipped"]})
                continue
            output_name = f"{index + 1:02d}_{task_id}.png"
            output_path = output_dir / output_name
            status = "exists"
            if overwrite or not output_path.exists():
                left, top, right, bottom = pixel_box["clipped"]
                image.crop((left, top, right, bottom)).save(output_path, format="PNG")
                status = "written"
            output_text = str(output_path).replace("\\", "/")
            record = {
                "id": task_id,
                "name": name,
                "status": status,
                "source_reference": str(source_path).replace("\\", "/"),
                "crop_box": [float(value) for value in crop_box],
                "padded_crop_box": pixel_box["clipped"],
                "output_path": output_text,
                "width": pixel_box["width"],
                "height": pixel_box["height"],
            }
            crop_records.append(record)
            handoff_args = dict(task.get("arguments") or {}) if isinstance(task.get("arguments"), Mapping) else {}
            handoff_args.pop("image_url", None)
            handoff_args.update({
                "image_path": output_text,
                "texture": bool(handoff_args.get("texture", True)),
                "pbr": bool(handoff_args.get("pbr", True)),
                "smart_low_poly": bool(handoff_args.get("smart_low_poly", True)),
                "auto_size": bool(handoff_args.get("auto_size", True)),
                "confirm_spend": False,
            })
            handoffs.append({"id": task_id, "tool": "gen_tripo_image_to_model", "arguments": handoff_args})

    updated_reconstruction_json = _updated_reconstruction_with_crop_paths(
        source_outputs=source_outputs,
        crop_records=crop_records,
    )
    crop_count = sum(1 for record in crop_records if record.get("status") in {"written", "exists"})
    missing_count = sum(1 for record in crop_records if record.get("status") == "missing_crop_box")
    too_small_count = sum(1 for record in crop_records if record.get("status") == "too_small")
    status = (
        "ready_for_tripo_image_to_model"
        if crop_count and not missing_count and not too_small_count
        else ("needs_crop_boxes" if missing_count else ("needs_crop_review" if too_small_count else "no_crops_needed"))
    )
    return {
        "schema": SCREENSHOT_CROP_MANIFEST_SCHEMA,
        "status": status,
        "reference_image": str(source_path).replace("\\", "/"),
        "image_size": [image_width, image_height],
        "crop_output_dir": str(output_dir).replace("\\", "/"),
        "source_schema": source_outputs.get("schema", ""),
        "source_crop_task_count": len(crop_tasks),
        "crop_count": crop_count,
        "missing_crop_count": missing_count,
        "too_small_crop_count": too_small_count,
        "issues": issues,
        "crops": crop_records,
        "tripo_image_handoffs": handoffs,
        "updated_reconstruction_plan_json": updated_reconstruction_json,
        "tripo_batch_handoff": {
            "tool": "spatial_prepare_tripo_generation_batch",
            "arguments": {
                "composition_plan_json": updated_reconstruction_json or "<SCREENSHOT_RECONSTRUCTION_JSON_WITH_CROP_PATHS>",
                "prefer_image_crops": True,
                "include_text_fallbacks": True,
                "confirm_spend": False,
            },
            "enabled": bool(updated_reconstruction_json and crop_count),
        },
        "workflow": [
            {"step": "review_written_crops", "reason": "Confirm every crop contains one isolated prop before paid Tripo generation."},
            {"step": "prepare_tripo_batch", "tool": "spatial_prepare_tripo_generation_batch"},
            {"step": "approve_tripo_spend", "reason": "Only submit image-to-model jobs after explicit user approval."},
            {"step": "import_bind_place_validate", "tools": ["gen_tripo_import_to_project", "spatial_bind_generated_assets_to_composition", "spatial_plan_asset_scale_corrections", "spatial_plan_support_surface_anchors", "spatial_preflight_interior_layout", "spatial_plan_layout_preflight_corrections", "spatial_apply_composition_plan", "spatial_validate_placement"]},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is Ghost-owned local image crop extraction over agent-supplied crop boxes.",
                "It does not perform proprietary vision segmentation or copy Epic native MCP/SceneTools source.",
            ],
        },
    }


def _detected_item_asset_mappings(
    *,
    detected_items: Sequence[Mapping[str, Any]],
    composition_plan: Mapping[str, Any],
    crop_tasks: Sequence[Mapping[str, Any]],
    generate_missing_with_tripo: bool,
    include_text_fallbacks: bool,
) -> List[Dict[str, Any]]:
    props_by_id = {
        str(prop.get("detected_item_id") or prop.get("id")): prop
        for prop in composition_plan.get("props", [])
    }
    crop_by_id = {str(task.get("id")): task for task in crop_tasks}
    generation_by_id = {
        str(task.get("id")): task
        for task in composition_plan.get("generation_tasks", [])
    }
    mappings: List[Dict[str, Any]] = []
    for item in detected_items:
        item_id = _safe_asset_stem(str(item.get("id") or item.get("name")), "DetectedProp")
        prop = props_by_id.get(item_id, {})
        crop = crop_by_id.get(item_id, {})
        matched_asset = str(item.get("existing_asset_path") or prop.get("matched_asset_path") or "").strip()
        if matched_asset:
            action = "existing_asset"
            source = matched_asset
            handoff = {}
        elif generate_missing_with_tripo and crop.get("ready_for_image_to_model"):
            action = "tripo_image_to_model"
            source = str(crop.get("output_placeholder") or f"<CROP_FOR_{item_id}>")
            handoff = {"crop_task_id": item_id, "tool": "gen_tripo_image_to_model"}
        elif generate_missing_with_tripo and include_text_fallbacks and item_id in generation_by_id:
            action = "tripo_text_to_model"
            source = str(prop.get("asset_path_placeholder") or "")
            handoff = {"generation_task_id": item_id, "tool": "gen_tripo_text_to_model"}
        else:
            action = "missing_asset"
            source = ""
            handoff = {}
        mappings.append({
            "id": item_id,
            "name": item.get("name", item_id),
            "zone": item.get("zone") or prop.get("zone", ""),
            "surface": item.get("surface") or prop.get("surface", ""),
            "action": action,
            "source": source,
            "matched_asset_path": matched_asset,
            "composition_prop_id": prop.get("id", item_id),
            "placement_actor_label": (prop.get("placement") or {}).get("actor_label", ""),
            "handoff": handoff,
        })
    return mappings


def _crop_metrics(crop_box: Optional[Sequence[float]], image_size: Optional[Sequence[float]]) -> Dict[str, Any]:
    if not crop_box:
        return {"available": False}
    x, y, width, height = [float(value) for value in crop_box]
    metrics: Dict[str, Any] = {
        "available": True,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "area_px": max(0.0, width) * max(0.0, height),
    }
    if image_size:
        image_w, image_h = [float(value) for value in image_size]
        center_x = x + width / 2.0
        center_y = y + height / 2.0
        metrics.update({
            "center_px": [round(center_x, 3), round(center_y, 3)],
            "center_norm": [round(center_x / image_w, 4), round(center_y / image_h, 4)],
            "area_ratio": round(metrics["area_px"] / max(1.0, image_w * image_h), 6),
            "out_of_bounds": x < 0.0 or y < 0.0 or width <= 0.0 or height <= 0.0 or x + width > image_w or y + height > image_h,
        })
    return metrics


def _frame_region(metrics: Mapping[str, Any]) -> Dict[str, str]:
    center = metrics.get("center_norm") if isinstance(metrics.get("center_norm"), list) else None
    if not center:
        return {"horizontal": "unknown", "depth": "unknown"}
    x, y = float(center[0]), float(center[1])
    horizontal = "left" if x < 0.34 else ("right" if x > 0.66 else "center")
    depth = "background" if y < 0.34 else ("foreground" if y > 0.66 else "midground")
    return {"horizontal": horizontal, "depth": depth}


def _detected_item_defaults(item: Mapping[str, Any], room_type: str) -> Dict[str, str]:
    name = str(item.get("name") or "").strip()
    match = _best_interior_prop_match(name) or {}
    category = str(item.get("category") or match.get("category") or "prop").strip() or "prop"
    surface = str(item.get("surface") or match.get("surface") or "floor").strip() or "floor"
    zone = _normalize_detected_zone(
        str(item.get("zone") or ""),
        room_type=room_type,
        fallback=str(match.get("zone") or "living"),
    )
    return {"category": category, "surface": surface, "zone": zone}


def _inferred_placement_hint(
    *,
    item: Mapping[str, Any],
    defaults: Mapping[str, str],
    region: Mapping[str, str],
) -> str:
    existing = str(item.get("placement_hint") or "").strip()
    if existing:
        return existing
    name = str(item.get("name") or "").lower()
    zone = str(defaults.get("zone") or "room").replace("_", " ")
    surface = str(defaults.get("surface") or "floor").lower()
    horizontal = region.get("horizontal", "unknown")
    depth = region.get("depth", "unknown")

    if surface in {"table", "counter", "shelf"}:
        if "book" in name or "magazine" in name:
            return "on the coffee table" if zone == "living" else f"on the {surface}"
        if "clutter" in name or "small appliance" in name:
            return "on the counter" if zone == "kitchen" else f"on the {surface}"
        return f"on the {surface}"
    if surface == "wall":
        if horizontal in {"left", "right"}:
            return f"mounted on the {horizontal} {zone} wall"
        if depth == "background":
            return f"mounted on the back {zone} wall"
        return f"mounted on the {zone} wall"
    if horizontal in {"left", "right"} and depth in {"background", "midground"}:
        return f"against the {horizontal} {zone} wall"
    if depth == "background":
        return f"against the back {zone} wall"
    if depth == "foreground":
        return f"near the front of the {zone}"
    if horizontal == "center":
        return f"near the center of the {zone}"
    return ""


def _crop_iou(first: Sequence[float], second: Sequence[float]) -> float:
    ax, ay, aw, ah = [float(value) for value in first]
    bx, by, bw, bh = [float(value) for value in second]
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    overlap_w = max(0.0, min(ax2, bx2) - max(ax, bx))
    overlap_h = max(0.0, min(ay2, by2) - max(ay, by))
    intersection = overlap_w * overlap_h
    union = max(1.0, aw * ah + bw * bh - intersection)
    return round(intersection / union, 6)


def _plan_screenshot_decomposition_preflight(
    *,
    reference_image: str,
    detected_items: Sequence[Mapping[str, Any]],
    image_size: Optional[Sequence[float]],
    room_type: str,
    require_crop_boxes: bool,
    confidence_threshold: float,
    min_crop_area_ratio: float,
) -> Dict[str, Any]:
    normalized_items: List[Dict[str, Any]] = []
    item_reports: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []
    crop_box_count = 0
    low_confidence_count = 0
    out_of_bounds_count = 0
    missing_crop_count = 0
    small_crop_count = 0

    for index, item in enumerate(detected_items):
        defaults = _detected_item_defaults(item, room_type)
        crop_box = item.get("crop_box")
        metrics = _crop_metrics(crop_box, image_size)
        region = _frame_region(metrics)
        placement_hint = _inferred_placement_hint(item=item, defaults=defaults, region=region)
        item_issues: List[Dict[str, Any]] = []
        if crop_box:
            crop_box_count += 1
        elif require_crop_boxes:
            missing_crop_count += 1
            item_issues.append({"severity": "warning", "kind": "missing_crop_box", "message": "Detected item has no crop_box for image-to-model generation."})
        if metrics.get("out_of_bounds"):
            out_of_bounds_count += 1
            item_issues.append({"severity": "error", "kind": "crop_box_out_of_bounds", "message": "crop_box extends outside the supplied image_size."})
        if image_size and metrics.get("available") and float(metrics.get("area_ratio", 0.0)) < min_crop_area_ratio:
            small_crop_count += 1
            item_issues.append({"severity": "warning", "kind": "tiny_crop_box", "message": "crop_box covers very little of the reference image; review before Tripo submission."})
        confidence = float(item.get("confidence", 0.0) or 0.0)
        if confidence and confidence < confidence_threshold:
            low_confidence_count += 1
            item_issues.append({"severity": "warning", "kind": "low_confidence", "message": "Detection confidence is below the requested threshold."})

        normalized = {
            "id": item.get("id"),
            "name": item.get("name"),
            "category": defaults["category"],
            "zone": defaults["zone"],
            "surface": defaults["surface"],
            "count": item.get("count", 1),
            "crop_box": crop_box,
            "crop_hint": item.get("crop_hint", ""),
            "placement_hint": placement_hint,
            "approx_size_cm": item.get("approx_size_cm"),
            "existing_asset_path": item.get("existing_asset_path", ""),
            "confidence": confidence,
        }
        normalized_items.append({key: value for key, value in normalized.items() if value not in (None, "", [])})
        report = {
            "index": index,
            "id": item.get("id"),
            "name": item.get("name"),
            "zone": defaults["zone"],
            "surface": defaults["surface"],
            "frame_region": region,
            "crop_metrics": metrics,
            "placement_hint": placement_hint,
            "placement_hint_inferred": not bool(str(item.get("placement_hint") or "").strip()) and bool(placement_hint),
            "issues": item_issues,
        }
        item_reports.append(report)
        for issue in item_issues:
            issues.append({**issue, "item": item.get("name"), "index": index})

    for first_index, first in enumerate(detected_items):
        first_box = first.get("crop_box")
        if not first_box:
            continue
        for second_index, second in enumerate(detected_items[first_index + 1:], start=first_index + 1):
            second_box = second.get("crop_box")
            if not second_box:
                continue
            iou = _crop_iou(first_box, second_box)
            if iou >= 0.72:
                issues.append({
                    "severity": "warning",
                    "kind": "duplicate_or_overlapping_crop",
                    "items": [first.get("name"), second.get("name")],
                    "indices": [first_index, second_index],
                    "iou": iou,
                    "message": "Two detected item crops overlap heavily; review whether they are duplicate detections or should be grouped.",
                })

    error_count = sum(1 for issue in issues if issue.get("severity") == "error")
    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    status = "blocked_by_decomposition" if error_count else ("needs_review" if warning_count else "ready_for_reconstruction")
    normalized_json = json.dumps(normalized_items, sort_keys=True)
    return {
        "schema": SCREENSHOT_DECOMPOSITION_PREFLIGHT_SCHEMA,
        "status": status,
        "reference_image": reference_image,
        "image_size": list(image_size) if image_size else [],
        "detected_item_count": len(detected_items),
        "normalized_detected_items": normalized_items,
        "normalized_detected_items_json": normalized_json,
        "item_reports": item_reports,
        "issue_count": len(issues),
        "error_count": error_count,
        "warning_count": warning_count,
        "issues": issues,
        "coverage_summary": {
            "crop_box_count": crop_box_count,
            "missing_crop_count": missing_crop_count,
            "out_of_bounds_count": out_of_bounds_count,
            "low_confidence_count": low_confidence_count,
            "tiny_crop_count": small_crop_count,
        },
        "reconstruction_handoff": {
            "tool": "spatial_plan_screenshot_reconstruction",
            "arguments": {
                "reference_image": reference_image,
                "detected_items_json": normalized_json,
                "room_type": room_type,
            },
            "enabled": bool(normalized_items),
        },
        "workflow": [
            {"step": "review_detection_issues", "reason": "Fix out-of-bounds, duplicate, tiny, or low-confidence crops before paid generation."},
            {"step": "rerun_screenshot_reconstruction", "tool": "spatial_plan_screenshot_reconstruction", "arguments": {"reference_image": reference_image, "detected_items_json": "<NORMALIZED_DETECTED_ITEMS_JSON>"}},
            {"step": "preflight_layout", "tool": "spatial_preflight_interior_layout"},
            {"step": "plan_layout_preflight_corrections", "tool": "spatial_plan_layout_preflight_corrections"},
            {"step": "generate_import_place_validate", "tools": ["gen_tripo_image_to_model", "gen_tripo_import_to_project", "spatial_add_asset_to_scene", "spatial_validate_placement"]},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is Ghost-owned detection QA over agent-supplied item metadata and does not perform or copy proprietary vision segmentation.",
                "Human/agent vision review remains required before submitting crops to paid generation providers.",
            ],
        },
    }


def _scene_graph_defaults(item: Mapping[str, Any], room_type: str) -> Dict[str, str]:
    defaults = _detected_item_defaults(item, room_type)
    match = _best_interior_prop_match(str(item.get("name") or "")) or {}
    if defaults["category"] == "prop" and match.get("category"):
        defaults["category"] = str(match["category"])
    if defaults["surface"] == "floor" and match.get("surface") and not str(item.get("surface") or "").strip():
        defaults["surface"] = str(match["surface"])
    return defaults


def _scene_graph_nodes(
    *,
    detected_items: Sequence[Mapping[str, Any]],
    image_size: Optional[Sequence[float]],
    room_type: str,
) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    for index, item in enumerate(detected_items):
        defaults = _scene_graph_defaults(item, room_type)
        metrics = _crop_metrics(item.get("crop_box"), image_size)
        region = _frame_region(metrics)
        placement_hint = _inferred_placement_hint(item=item, defaults=defaults, region=region)
        node = {
            "id": _safe_asset_stem(str(item.get("id") or item.get("name") or f"DetectedProp{index}"), "DetectedProp"),
            "index": index,
            "name": item.get("name"),
            "category": defaults["category"],
            "zone": defaults["zone"],
            "surface": defaults["surface"],
            "count": item.get("count", 1),
            "crop_box": item.get("crop_box"),
            "crop_metrics": metrics,
            "frame_region": region,
            "placement_hint": placement_hint,
            "placement_hint_inferred": not bool(str(item.get("placement_hint") or "").strip()) and bool(placement_hint),
            "approx_size_cm": item.get("approx_size_cm"),
            "existing_asset_path": item.get("existing_asset_path", ""),
            "confidence": float(item.get("confidence", 0.0) or 0.0),
            "generation_need": "existing_asset" if item.get("existing_asset_path") else "tripo_or_project_asset",
        }
        nodes.append({key: value for key, value in node.items() if value not in (None, "", [])})
    return nodes


def _node_center_norm(node: Mapping[str, Any]) -> Optional[List[float]]:
    metrics = node.get("crop_metrics") if isinstance(node.get("crop_metrics"), Mapping) else {}
    center = metrics.get("center_norm") if isinstance(metrics.get("center_norm"), list) else None
    if not center or len(center) != 2:
        return None
    return [float(center[0]), float(center[1])]


def _node_area_ratio(node: Mapping[str, Any]) -> float:
    metrics = node.get("crop_metrics") if isinstance(node.get("crop_metrics"), Mapping) else {}
    try:
        return float(metrics.get("area_ratio") or 0.0)
    except Exception:
        return 0.0


def _support_surface_kind(surface: str) -> str:
    text = str(surface or "").strip().lower()
    if text in {"table", "counter", "shelf", "cabinet"}:
        return text
    return ""


def _node_supports_surface(node: Mapping[str, Any], surface: str) -> bool:
    target = _support_surface_kind(surface)
    if not target:
        return False
    text = f"{node.get('name', '')} {node.get('category', '')} {node.get('surface', '')}".lower()
    if target == "counter":
        return any(token in text for token in ("counter", "island"))
    if target == "table":
        return "table" in text
    if target == "shelf":
        return any(token in text for token in ("shelf", "bookshelf", "bookcase"))
    if target == "cabinet":
        return "cabinet" in text
    return False


def _nearest_support_node(node: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    center = _node_center_norm(node)
    same_zone = [candidate for candidate in candidates if candidate.get("zone") == node.get("zone")]
    search = same_zone or list(candidates)
    best: Optional[Mapping[str, Any]] = None
    best_distance = 999.0
    for candidate in search:
        if candidate.get("id") == node.get("id"):
            continue
        if not _node_supports_surface(candidate, str(node.get("surface") or "")):
            continue
        candidate_center = _node_center_norm(candidate)
        if center and candidate_center:
            distance = ((center[0] - candidate_center[0]) ** 2 + (center[1] - candidate_center[1]) ** 2) ** 0.5
        else:
            distance = 0.5
        if distance < best_distance:
            best = candidate
            best_distance = distance
    return best


def _scene_graph_relations(nodes: Sequence[Mapping[str, Any]], *, maximum: int = 256) -> List[Dict[str, Any]]:
    relations: List[Dict[str, Any]] = []

    def add_relation(source: Mapping[str, Any], relation: str, target: str, **extra: Any) -> None:
        if len(relations) >= maximum:
            return
        relations.append({
            "source": source.get("id"),
            "source_name": source.get("name"),
            "relation": relation,
            "target": target,
            **{key: value for key, value in extra.items() if value not in (None, "", [])},
        })

    for node in nodes:
        surface = str(node.get("surface") or "").lower()
        support = _nearest_support_node(node, nodes)
        if support:
            add_relation(
                node,
                "supported_by",
                str(support.get("id")),
                target_name=support.get("name"),
                surface=surface,
                reason=f"{node.get('name')} is marked for placement on a {surface}.",
            )
        elif surface in {"wall", "ceiling"}:
            region = node.get("frame_region") if isinstance(node.get("frame_region"), Mapping) else {}
            wall = "back" if region.get("depth") == "background" else str(region.get("horizontal") or "room")
            add_relation(node, "anchored_to_wall", f"{wall}_{node.get('zone', 'room')}_wall", surface=surface)

    for first_index, first in enumerate(nodes):
        first_center = _node_center_norm(first)
        if not first_center:
            continue
        for second in nodes[first_index + 1:]:
            second_center = _node_center_norm(second)
            if not second_center:
                continue
            dx = second_center[0] - first_center[0]
            dy = second_center[1] - first_center[1]
            distance = (dx * dx + dy * dy) ** 0.5
            same_zone = first.get("zone") == second.get("zone")
            if abs(dx) >= 0.14 and abs(dy) <= 0.42:
                left, right = (first, second) if dx > 0 else (second, first)
                add_relation(left, "left_of", str(right.get("id")), target_name=right.get("name"), same_zone=same_zone, strength=round(abs(dx), 3))
                add_relation(right, "right_of", str(left.get("id")), target_name=left.get("name"), same_zone=same_zone, strength=round(abs(dx), 3))
            if abs(dy) >= 0.18 and abs(dx) <= 0.45:
                back, front = (first, second) if dy > 0 else (second, first)
                add_relation(front, "in_front_of", str(back.get("id")), target_name=back.get("name"), same_zone=same_zone, strength=round(abs(dy), 3))
                add_relation(back, "behind", str(front.get("id")), target_name=front.get("name"), same_zone=same_zone, strength=round(abs(dy), 3))
            if same_zone and distance <= 0.30:
                add_relation(first, "clustered_with", str(second.get("id")), target_name=second.get("name"), distance=round(distance, 3))
                add_relation(second, "clustered_with", str(first.get("id")), target_name=first.get("name"), distance=round(distance, 3))
    return relations


def _scene_graph_zone_clusters(nodes: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    clusters: Dict[str, List[Mapping[str, Any]]] = {}
    for node in nodes:
        clusters.setdefault(str(node.get("zone") or "room"), []).append(node)
    result: List[Dict[str, Any]] = []
    for zone, zone_nodes in sorted(clusters.items()):
        anchors = [
            node for node in zone_nodes
            if str(node.get("surface") or "") == "floor" or _node_area_ratio(node) >= 0.04
        ]
        result.append({
            "zone": zone,
            "item_count": len(zone_nodes),
            "items": [node.get("id") for node in zone_nodes],
            "anchor_items": [node.get("id") for node in anchors[:6]],
            "support_items": [
                node.get("id") for node in zone_nodes
                if str(node.get("category") or "").lower() in {"table", "counter", "storage"} or _support_surface_kind(str(node.get("surface") or ""))
            ],
        })
    return result


def _scene_graph_constraints(
    *,
    nodes: Sequence[Mapping[str, Any]],
    relations: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    constraints: List[Dict[str, Any]] = []
    for relation in relations:
        if relation.get("relation") == "supported_by":
            constraints.append({
                "kind": "support_contact",
                "source": relation.get("source"),
                "target": relation.get("target"),
                "description": f"Place {relation.get('source_name')} on {relation.get('target_name')}.",
            })
        elif relation.get("relation") == "anchored_to_wall":
            constraints.append({
                "kind": "wall_anchor",
                "source": relation.get("source"),
                "target": relation.get("target"),
                "description": f"Keep {relation.get('source_name')} anchored to the inferred wall region.",
            })
    for node in nodes:
        hint = str(node.get("placement_hint") or "")
        if hint:
            constraints.append({
                "kind": "placement_hint",
                "source": node.get("id"),
                "description": hint,
            })
    return constraints[:128]


def _plan_screenshot_scene_graph(
    *,
    reference_image: str,
    detected_items: Sequence[Mapping[str, Any]],
    image_size: Optional[Sequence[float]],
    room_type: str,
    include_reconstruction_handoff: bool,
) -> Dict[str, Any]:
    nodes = _scene_graph_nodes(detected_items=detected_items, image_size=image_size, room_type=room_type)
    relations = _scene_graph_relations(nodes)
    clusters = _scene_graph_zone_clusters(nodes)
    constraints = _scene_graph_constraints(nodes=nodes, relations=relations)
    normalized_items = []
    for node in nodes:
        item = {
            "id": node.get("id"),
            "name": node.get("name"),
            "category": node.get("category"),
            "zone": node.get("zone"),
            "surface": node.get("surface"),
            "count": node.get("count", 1),
            "crop_box": node.get("crop_box"),
            "placement_hint": node.get("placement_hint", ""),
            "approx_size_cm": node.get("approx_size_cm"),
            "existing_asset_path": node.get("existing_asset_path", ""),
            "confidence": node.get("confidence", 0.0),
        }
        normalized_items.append({key: value for key, value in item.items() if value not in (None, "", [])})
    normalized_json = json.dumps(normalized_items, sort_keys=True)
    return {
        "schema": SCREENSHOT_SCENE_GRAPH_SCHEMA,
        "status": "ready_for_reconstruction" if nodes else "no_detected_items",
        "reference_image": reference_image,
        "image_size": list(image_size) if image_size else [],
        "room_type": room_type,
        "node_count": len(nodes),
        "relation_count": len(relations),
        "constraint_count": len(constraints),
        "nodes": nodes,
        "relations": relations,
        "zone_clusters": clusters,
        "composition_constraints": constraints,
        "normalized_detected_items": normalized_items,
        "normalized_detected_items_json": normalized_json,
        "reconstruction_handoff": {
            "tool": "spatial_plan_screenshot_reconstruction",
            "arguments": {
                "reference_image": reference_image,
                "detected_items_json": normalized_json,
                "scene_graph_json": "<THIS_SCENE_GRAPH_RESULT_JSON>",
                "room_type": room_type,
            },
            "enabled": bool(include_reconstruction_handoff and normalized_items),
        },
        "workflow": [
            {"step": "review_scene_graph", "reason": "Confirm object relationships before using them as placement constraints."},
            {"step": "prepare_crops", "tool": "spatial_prepare_screenshot_crop_manifest"},
            {"step": "plan_reconstruction", "tool": "spatial_plan_screenshot_reconstruction"},
            {"step": "preflight_layout", "tool": "spatial_preflight_interior_layout"},
            {"step": "plan_layout_preflight_corrections", "tool": "spatial_plan_layout_preflight_corrections"},
            {"step": "generate_bind_apply_validate", "tools": ["spatial_prepare_tripo_generation_batch", "spatial_bind_generated_assets_to_composition", "spatial_plan_asset_scale_corrections", "spatial_plan_support_surface_anchors", "spatial_preflight_interior_layout", "spatial_plan_layout_preflight_corrections", "spatial_apply_composition_plan", "spatial_validate_placement"]},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is Ghost-owned relationship inference over agent/vision-supplied detection metadata.",
                "It does not perform proprietary vision segmentation and does not copy Epic native MCP or SceneTools source.",
            ],
        },
    }


def _scene_graph_from_json(value: str) -> Dict[str, Any]:
    outputs = _outputs_from_result_json(value, "scene_graph_json", SCREENSHOT_SCENE_GRAPH_SCHEMA)
    if not outputs:
        return {}
    if outputs.get("schema") not in (None, SCREENSHOT_SCENE_GRAPH_SCHEMA):
        raise ValueError(f"scene_graph_json must have schema {SCREENSHOT_SCENE_GRAPH_SCHEMA}")
    for field_name in ("nodes", "relations", "zone_clusters", "composition_constraints", "normalized_detected_items"):
        if outputs.get(field_name) not in (None, "") and not isinstance(outputs.get(field_name), list):
            raise ValueError(f"scene_graph_json.{field_name} must be a list")
    return outputs


def _scene_item_key(value: Any) -> str:
    text = str(value or "").strip()
    return _safe_asset_stem(text, "DetectedProp").lower() if text else ""


def _scene_graph_detected_items(scene_graph: Mapping[str, Any], *, maximum: int) -> List[Dict[str, Any]]:
    if not scene_graph:
        return []
    raw_items = scene_graph.get("normalized_detected_items")
    if not isinstance(raw_items, list) or not raw_items:
        raw_items = []
        nodes = scene_graph.get("nodes") if isinstance(scene_graph.get("nodes"), list) else []
        for node in nodes:
            if not isinstance(node, Mapping):
                continue
            raw_items.append({
                "id": node.get("id"),
                "name": node.get("name"),
                "category": node.get("category"),
                "zone": node.get("zone"),
                "surface": node.get("surface"),
                "count": node.get("count", 1),
                "crop_box": node.get("crop_box"),
                "crop_hint": node.get("crop_hint", ""),
                "placement_hint": node.get("placement_hint", ""),
                "approx_size_cm": node.get("approx_size_cm"),
                "existing_asset_path": node.get("existing_asset_path", ""),
                "confidence": node.get("confidence", 0.0),
            })
    return _detected_items_from_json(json.dumps(raw_items[:maximum]), maximum=maximum)


def _scene_graph_label_lookup(scene_graph: Mapping[str, Any]) -> Dict[str, Dict[str, str]]:
    lookup: Dict[str, Dict[str, str]] = {}
    raw_groups = [
        scene_graph.get("nodes") if isinstance(scene_graph.get("nodes"), list) else [],
        scene_graph.get("normalized_detected_items") if isinstance(scene_graph.get("normalized_detected_items"), list) else [],
    ]
    for group in raw_groups:
        for item in group:
            if not isinstance(item, Mapping):
                continue
            item_id = _scene_item_key(item.get("id") or item.get("name"))
            if not item_id:
                continue
            lookup[item_id] = {
                "id": item_id,
                "name": str(item.get("name") or item_id).strip(),
                "surface": str(item.get("surface") or "").strip().lower(),
                "zone": str(item.get("zone") or "").strip().lower(),
            }
    return lookup


def _scene_graph_relation_hints(scene_graph: Mapping[str, Any]) -> Dict[str, str]:
    hints: Dict[str, str] = {}
    labels = _scene_graph_label_lookup(scene_graph)
    relations = scene_graph.get("relations") if isinstance(scene_graph.get("relations"), list) else []
    for relation in relations:
        if not isinstance(relation, Mapping):
            continue
        source = _scene_item_key(relation.get("source"))
        if not source:
            continue
        relation_type = str(relation.get("relation") or "").strip()
        if relation_type == "supported_by":
            target = _scene_item_key(relation.get("target"))
            target_name = str(relation.get("target_name") or labels.get(target, {}).get("name") or relation.get("target") or "").strip()
            if target_name:
                hints.setdefault(source, f"on the {target_name}")
        elif relation_type == "anchored_to_wall":
            source_surface = labels.get(source, {}).get("surface", "")
            target_text = str(relation.get("target") or "room wall").replace("_", " ").strip()
            if target_text:
                verb = "mounted on" if source_surface == "wall" else "against"
                hints.setdefault(source, f"{verb} the {target_text}")
    return hints


def _scene_graph_observations(scene_graph: Mapping[str, Any], *, maximum: int = 64) -> List[str]:
    if not scene_graph:
        return []
    labels = _scene_graph_label_lookup(scene_graph)
    observations: List[str] = []
    relations = scene_graph.get("relations") if isinstance(scene_graph.get("relations"), list) else []
    for relation in relations:
        if not isinstance(relation, Mapping):
            continue
        source_id = _scene_item_key(relation.get("source"))
        target_id = _scene_item_key(relation.get("target"))
        source_name = str(relation.get("source_name") or labels.get(source_id, {}).get("name") or relation.get("source") or "").strip()
        target_name = str(relation.get("target_name") or labels.get(target_id, {}).get("name") or relation.get("target") or "").replace("_", " ").strip()
        relation_type = str(relation.get("relation") or "").replace("_", " ").strip()
        if source_name and target_name and relation_type:
            observations.append(f"{source_name} is {relation_type} {target_name}.")
        if len(observations) >= maximum:
            break
    constraints = scene_graph.get("composition_constraints") if isinstance(scene_graph.get("composition_constraints"), list) else []
    for constraint in constraints:
        if not isinstance(constraint, Mapping):
            continue
        description = str(constraint.get("description") or "").strip()
        if description:
            observations.append(description)
        if len(observations) >= maximum:
            break
    return _merge_unique(observations)


def _scene_graph_count(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _scene_graph_context(scene_graph: Mapping[str, Any]) -> Dict[str, Any]:
    if not scene_graph:
        return {"applied": False}
    relations = scene_graph.get("relations") if isinstance(scene_graph.get("relations"), list) else []
    constraints = scene_graph.get("composition_constraints") if isinstance(scene_graph.get("composition_constraints"), list) else []
    clusters = scene_graph.get("zone_clusters") if isinstance(scene_graph.get("zone_clusters"), list) else []
    nodes = scene_graph.get("nodes") if isinstance(scene_graph.get("nodes"), list) else []
    return {
        "applied": True,
        "schema": scene_graph.get("schema") or SCREENSHOT_SCENE_GRAPH_SCHEMA,
        "status": scene_graph.get("status", ""),
        "node_count": _scene_graph_count(scene_graph.get("node_count"), len(nodes)),
        "relation_count": _scene_graph_count(scene_graph.get("relation_count"), len(relations)),
        "constraint_count": _scene_graph_count(scene_graph.get("constraint_count"), len(constraints)),
        "zone_clusters": clusters[:16],
        "relations": relations[:128],
        "composition_constraints": constraints[:128],
    }


def _merge_scene_graph_detected_items(
    detected_items: Sequence[Mapping[str, Any]],
    scene_graph: Mapping[str, Any],
    *,
    maximum: int,
) -> List[Dict[str, Any]]:
    graph_items = _scene_graph_detected_items(scene_graph, maximum=maximum)
    if not graph_items:
        return [dict(item) for item in detected_items]

    graph_by_key: Dict[str, Dict[str, Any]] = {}
    for item in graph_items:
        for key in (_scene_item_key(item.get("id")), _scene_item_key(item.get("name"))):
            if key and key not in graph_by_key:
                graph_by_key[key] = item

    merged = [dict(item) for item in detected_items] if detected_items else [dict(item) for item in graph_items]
    relation_hints = _scene_graph_relation_hints(scene_graph)
    fill_fields = ("category", "zone", "surface", "crop_box", "crop_hint", "approx_size_cm", "existing_asset_path")

    for item in merged:
        candidates = [_scene_item_key(item.get("id")), _scene_item_key(item.get("name"))]
        graph_item = next((graph_by_key[key] for key in candidates if key in graph_by_key), None)
        if graph_item:
            for field_name in fill_fields:
                if item.get(field_name) in (None, "", []):
                    item[field_name] = graph_item.get(field_name)
            if not item.get("confidence") and graph_item.get("confidence"):
                item["confidence"] = graph_item.get("confidence")
            if not item.get("placement_hint") and graph_item.get("placement_hint"):
                item["placement_hint"] = graph_item.get("placement_hint")
        relation_hint = next((relation_hints[key] for key in candidates if key in relation_hints), "")
        if relation_hint:
            current_hint = str(item.get("placement_hint") or "").strip()
            if not current_hint:
                item["placement_hint"] = relation_hint
            elif relation_hint.lower() not in current_hint.lower():
                item["placement_hint"] = f"{current_hint}; {relation_hint}"

    return _detected_items_from_json(json.dumps(merged[:maximum]), maximum=maximum)


def _plan_screenshot_reconstruction(
    *,
    reference_image: str,
    detected_items: Sequence[Mapping[str, Any]],
    room_type: str,
    room_dimensions: Sequence[float],
    room_origin: Sequence[float],
    style: str,
    intent: str,
    existing_asset_paths: Sequence[str],
    content_path: str,
    actor_label_prefix: str,
    generate_missing_with_tripo: bool,
    include_text_fallbacks: bool,
    limit: int,
    required_props: Sequence[str] = (),
    include_architectural_fill: bool = False,
    include_zone_recommendations: bool = False,
    room_analysis: Optional[Mapping[str, Any]] = None,
    scene_graph: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    analysis = room_analysis or {}
    graph = scene_graph or {}
    base = {
        "schema": SCREENSHOT_RECONSTRUCTION_SCHEMA,
        "goal": "Decompose a reference image into props, map each item to assets or guarded Tripo tasks, then rebuild the composition spatially in Unreal.",
        "reference_image": reference_image,
        "room": {
            "type": room_type,
            "dimensions_cm": list(room_dimensions),
            "origin": list(room_origin),
            "style": style,
            "intent": intent,
        },
        "room_analysis": _room_analysis_summary(analysis),
        "scene_graph": _scene_graph_context(graph),
        "detected_items": list(detected_items),
        "segmentation_schema": _screenshot_detection_schema(),
    }
    if not detected_items:
        return {
            **base,
            "decomposition_required": True,
            "crop_tasks": [],
            "asset_mapping": [],
            "composition_plan": None,
            "workflow": [
                {
                    "step": "segment_reference_image",
                    "actor": "agent_vision",
                    "instructions": [
                        "Identify room layout, major zones, visible surfaces, and individual props.",
                        "Return detected_items_json using the segmentation_schema fields.",
                        "Prefer separate entries for props that will need individual placement or Tripo generation.",
                    ],
                },
                {
                    "step": "infer_scene_graph",
                    "tool": "spatial_infer_screenshot_scene_graph",
                    "reason": "Convert detections into support, wall-anchor, zone-cluster, and relative-position constraints before reconstruction.",
                },
                {
                    "step": "crop_missing_props",
                    "actor": "agent_vision",
                    "instructions": [
                        "Crop each missing prop before using gen_tripo_image_to_model.",
                        "Use crop_box when pixel coordinates are known; otherwise provide crop_hint and placement_hint.",
                    ],
                },
                {
                    "step": "rerun_planner",
                    "tool": "spatial_plan_screenshot_reconstruction",
                    "arguments": {
                        "reference_image": reference_image,
                        "room_type": room_type,
                        "room_dimensions": list(room_dimensions),
                        "room_origin": list(room_origin),
                        "room_analysis_json": "<OPTIONAL_SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
                        "detected_items_json": "<JSON_LIST_FROM_SEGMENTATION>",
                        "scene_graph_json": "<OPTIONAL_SPATIAL_INFER_SCREENSHOT_SCENE_GRAPH_RESULT_JSON>",
                    },
                },
            ],
            "legal_review": {
                "requires_review": False,
                "notes": [
                    "This is a Ghost-owned image decomposition contract, not Epic source-derived code.",
                    "Any future direct reuse of Epic native spatial or SceneTools implementation details needs legal review.",
                ],
            },
        }

    item_asset_paths = [
        str(item.get("existing_asset_path"))
        for item in detected_items
        if item.get("existing_asset_path")
    ]
    combined_asset_paths = _merge_unique(existing_asset_paths, item_asset_paths)
    observations = [_detected_item_observation(item) for item in detected_items]
    observations = _merge_unique(observations, _scene_graph_observations(graph), _room_analysis_observations(analysis))
    functional_zone_plan = _plan_functional_zones(
        room_type=room_type,
        room_dimensions=room_dimensions,
        room_origin=room_origin,
        room_analysis=analysis,
        detected_items=detected_items,
        composition_plan={},
        requested_zones=[],
        min_zone_size_cm=120.0,
        include_updated_room_analysis=True,
        limit=16,
    )
    analysis_for_planning = (
        dict(functional_zone_plan["updated_room_analysis"])
        if isinstance(functional_zone_plan.get("updated_room_analysis"), Mapping)
        else analysis
    )
    prop_program = _plan_interior_prop_program(
        room_type=room_type,
        room_dimensions=room_dimensions,
        room_origin=room_origin,
        functional_zone_plan=functional_zone_plan,
        room_analysis=analysis_for_planning,
        detected_items=detected_items,
        requested_zones=[],
        required_props=required_props,
        omit_props=[],
        existing_asset_paths=combined_asset_paths,
        style=style,
        intent=intent,
        include_architectural_fill=include_architectural_fill,
        limit=limit,
        include_zone_recommendations=include_zone_recommendations,
    )
    composition_plan = _plan_interior_composition(
        room_type=room_type,
        room_dimensions=room_dimensions,
        room_origin=room_origin,
        functional_zone_plan=functional_zone_plan,
        prop_program=prop_program,
        style=style,
        intent=intent,
        screenshot_reference=reference_image,
        screenshot_observations=observations,
        existing_asset_paths=combined_asset_paths,
        required_props=[],
        omit_props=[],
        content_path=content_path,
        actor_label_prefix=actor_label_prefix or "ReferenceRebuild",
        generate_missing_with_tripo=bool(generate_missing_with_tripo and include_text_fallbacks),
        include_image_to_model_handoffs=False,
        limit=limit,
        detected_items=detected_items,
        room_analysis=analysis_for_planning,
    )
    detected_openings = _detected_opening_records(
        detected_items=detected_items,
        functional_zone_plan=functional_zone_plan,
        room_type=room_type,
        room_dimensions=room_dimensions,
        room_origin=room_origin,
        actor_label_prefix=actor_label_prefix or "ReferenceRebuild",
    )
    composition_plan = _add_detected_openings_to_composition(composition_plan, detected_openings)
    crop_tasks = [
        _crop_task_for_detected_item(item, reference_image=reference_image, room_type=room_type)
        for item in detected_items
        if generate_missing_with_tripo and not item.get("existing_asset_path")
    ]
    asset_mapping = _detected_item_asset_mappings(
        detected_items=detected_items,
        composition_plan=composition_plan,
        crop_tasks=crop_tasks,
        generate_missing_with_tripo=generate_missing_with_tripo,
        include_text_fallbacks=include_text_fallbacks,
    )
    return {
        **base,
        "decomposition_required": False,
        "detected_item_count": len(detected_items),
        "detected_openings": detected_openings,
        "detected_opening_count": len(detected_openings),
        "functional_zone_plan": functional_zone_plan,
        "prop_program": prop_program,
        "crop_tasks": crop_tasks,
        "asset_mapping": asset_mapping,
        "composition_plan": composition_plan,
        "scene_graph_context": _scene_graph_context(graph),
        "validation_handoff": composition_plan.get("validation_handoff", {}),
        "workflow": [
            {"step": "review_detected_items", "reason": "Confirm each visible prop, zone, surface, scale hint, and crop before generation."},
            {"step": "review_scene_graph_constraints", "enabled": bool(graph), "reason": "Confirm support contacts, wall anchors, and relative prop relationships before placement."},
            {"step": "infer_functional_zones", "tool": "spatial_infer_functional_zones", "reason": "Cluster screenshot detections into usable room zones before prop programming."},
            {"step": "plan_prop_program", "tool": "spatial_plan_interior_prop_program", "reason": "Preserve detected reference props as a composition-ready prop program before Tripo planning."},
            {"step": "preflight_detected_openings", "tool": "spatial_preflight_interior_layout", "enabled": bool(detected_openings), "opening_count": len(detected_openings), "reason": "Use detected doors, windows, archways, and openings as clearance/sightline constraints before placement."},
            {"step": "map_existing_assets", "reason": "Prefer supplied /Game assets and project content over generation."},
            {"step": "crop_missing_props", "tools": ["agent_vision", "gen_tripo_image_to_model"], "crop_tasks": crop_tasks},
            {"step": "generate_text_fallbacks", "tools": ["gen_tripo_text_to_model"], "enabled": bool(generate_missing_with_tripo and include_text_fallbacks)},
            {"step": "import_generated_assets", "tool": "gen_tripo_import_to_project"},
            {"step": "place_spatially", "tool": "spatial_add_asset_to_scene", "placement_steps": composition_plan.get("placement_steps", [])},
            {"step": "probe_and_validate", "tools": ["spatial_surface_probe", "spatial_validate_placement"]},
            {"step": "capture_and_iterate", "tools": ["spatial_select_actors", "focus_viewport", "viewport_capture_screenshot"]},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This clean-room workflow coordinates Ghost spatial probes, Tripo handoffs, and placement plans without copying Epic source.",
                "Legal review is required before transplanting native UE MCP SceneTools, ToolsetRegistry, or asset-placement source.",
            ],
        },
    }


def _binding_key(value: Any) -> str:
    text = str(value or "").strip().lower().replace("\\", "/")
    if not text:
        return ""
    if text.startswith("/game"):
        text = _asset_name_from_path(text).lower()
    return _safe_asset_stem(text, "key").lower()


def _binding_keys(*values: Any) -> List[str]:
    keys: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        candidates = {
            text.lower().replace("\\", "/"),
            _binding_key(text),
        }
        if text.startswith("<") and text.endswith(">"):
            candidates.add(_binding_key(text.strip("<>")))
        for candidate in candidates:
            if candidate and candidate not in seen:
                keys.append(candidate)
                seen.add(candidate)
    return keys


def _first_clean_asset_path(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        try:
            return _clean_asset_path(text)
        except ValueError:
            continue
    return ""


def _dict_value(value: Any, key: str) -> Dict[str, Any]:
    if isinstance(value, Mapping) and isinstance(value.get(key), Mapping):
        return dict(value[key])
    return {}


def _list_value(value: Any, key: str) -> List[Any]:
    if isinstance(value, Mapping) and isinstance(value.get(key), list):
        return list(value[key])
    return []


def _import_result_items_from_json(value: str) -> List[Dict[str, Any]]:
    parsed = _json_value_from_text(value, "import_results_json")
    if parsed is None:
        return []
    if isinstance(parsed, list):
        return [dict(item) for item in parsed if isinstance(item, Mapping)]
    if not isinstance(parsed, Mapping):
        raise ValueError("import_results_json must decode to an object or list")

    parsed_dict = dict(parsed)
    outputs = _dict_value(parsed_dict, "outputs")
    for key in ("import_results", "imports", "results"):
        wrapped = _list_value(parsed_dict, key) or _list_value(outputs, key)
        if wrapped:
            return [dict(item) for item in wrapped if isinstance(item, Mapping)]

    known_single = bool(
        outputs
        or parsed_dict.get("asset_paths")
        or parsed_dict.get("primary_asset")
        or parsed_dict.get("preview_asset_path")
        or parsed_dict.get("import_result")
        or parsed_dict.get("task_id")
    )
    if known_single:
        return [parsed_dict]

    items: List[Dict[str, Any]] = []
    for key, item in parsed_dict.items():
        if isinstance(item, str):
            items.append({"id": key, "asset_path": item})
        elif isinstance(item, Mapping):
            merged = dict(item)
            merged.setdefault("id", key)
            items.append(merged)
    return items


def _size_vector_from_any(value: Any) -> List[float]:
    size = _size_vector(value)
    if size:
        return size
    if not isinstance(value, Mapping):
        return []
    vector = _optional_vector3(value)
    if vector and all(component > 0.0 for component in vector):
        return vector
    keyed = []
    for key in ("width", "depth", "height"):
        parsed = _numeric_value(value.get(key))
        if parsed is None or parsed <= 0.0:
            keyed = []
            break
        keyed.append(parsed)
    return keyed if len(keyed) == 3 else []


def _bounds_size_vector(value: Any) -> List[float]:
    if not isinstance(value, Mapping):
        return []
    for key in ("size", "approx_size_cm", "dimensions_cm"):
        size = _size_vector_from_any(value.get(key))
        if size:
            return size
    extent = _size_vector_from_any(value.get("extent") or value.get("box_extent"))
    if extent:
        return [component * 2.0 for component in extent]
    min_v = _optional_vector3(value.get("min"))
    max_v = _optional_vector3(value.get("max"))
    if min_v and max_v:
        size = [abs(float(max_v[index]) - float(min_v[index])) for index in range(3)]
        if all(component > 0.0 for component in size):
            return size
    return []


def _import_result_bounds_mapping(*sources: Mapping[str, Any]) -> Dict[str, Any]:
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for key in ("bounds", "asset_bounds", "static_mesh_bounds", "bounding_box"):
            bounds = source.get(key)
            if not isinstance(bounds, Mapping):
                continue
            size = _bounds_size_vector(bounds)
            if size:
                cleaned = dict(bounds)
                cleaned["size"] = _rounded_vector(size)
                return cleaned
    return {}


def _import_result_size_vector(*sources: Mapping[str, Any]) -> List[float]:
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for key in ("approx_size_cm", "size", "dimensions_cm"):
            size = _size_vector_from_any(source.get(key))
            if size:
                return size
        bounds = _import_result_bounds_mapping(source)
        size = _bounds_size_vector(bounds)
        if size:
            return size
    return []


def _normalize_import_result_records(value: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for item in _import_result_items_from_json(value):
        outputs = _dict_value(item, "outputs") or item
        inputs = _dict_value(item, "inputs")
        asset_paths = _dict_value(outputs, "asset_paths")
        manifest = _dict_value(outputs, "manifest")
        import_result = _dict_value(outputs, "import_result")
        import_outputs = _dict_value(import_result, "outputs")
        imported_paths = asset_paths.get("imported_object_paths")
        if not isinstance(imported_paths, list):
            imported_paths = outputs.get("imported_object_paths") if isinstance(outputs.get("imported_object_paths"), list) else []
        primary_asset = _first_clean_asset_path(
            asset_paths.get("primary_asset"),
            outputs.get("preview_asset_path"),
            outputs.get("primary_asset"),
            outputs.get("asset_path"),
            import_outputs.get("asset_path"),
            *(imported_paths or []),
        )
        if not primary_asset:
            continue
        task = _dict_value(outputs, "task")
        task_id = str(outputs.get("task_id") or inputs.get("task_id") or task.get("id") or task.get("task_id") or "").strip()
        asset_name = str(inputs.get("asset_name") or manifest.get("asset_name") or outputs.get("asset_name") or "").strip()
        explicit_id = str(item.get("id") or outputs.get("id") or "").strip()
        size_sources = (item, outputs, manifest, import_result, import_outputs, asset_paths)
        imported_size = _import_result_size_vector(*size_sources)
        imported_bounds = _import_result_bounds_mapping(*size_sources)
        record = {
            "id": explicit_id or asset_name or task_id or _safe_asset_stem(_asset_name_from_path(primary_asset), "ImportedAsset"),
            "asset_path": primary_asset,
            "task_id": task_id,
            "asset_name": asset_name,
            "source": "tripo_import_result",
            "match_keys": _binding_keys(explicit_id, asset_name, task_id, primary_asset),
            "raw_stage": item.get("stage", ""),
        }
        if imported_size:
            record["approx_size_cm"] = _rounded_vector(imported_size)
        if imported_bounds:
            record["bounds"] = imported_bounds
        records.append(record)
    return records


def _asset_override_records_from_json(value: str) -> List[Dict[str, Any]]:
    parsed = _json_value_from_text(value, "asset_overrides_json")
    if parsed is None:
        return []
    raw_items: List[Dict[str, Any]] = []
    if isinstance(parsed, Mapping):
        for key, item in parsed.items():
            if isinstance(item, str):
                raw_items.append({"id": key, "asset_path": item})
            elif isinstance(item, Mapping):
                merged = dict(item)
                merged.setdefault("id", key)
                raw_items.append(merged)
            else:
                raise ValueError("asset_overrides_json object values must be strings or objects")
    elif isinstance(parsed, list):
        raw_items = [dict(item) for item in parsed if isinstance(item, Mapping)]
    else:
        raise ValueError("asset_overrides_json must decode to an object or list")

    records: List[Dict[str, Any]] = []
    for index, item in enumerate(raw_items):
        asset_path = _clean_asset_path(str(item.get("asset_path") or item.get("primary_asset") or ""))
        identifier = str(item.get("id") or item.get("prop_id") or item.get("actor_label") or _asset_name_from_path(asset_path)).strip()
        actor_label = str(item.get("actor_label") or "").strip()
        imported_size = _import_result_size_vector(item)
        imported_bounds = _import_result_bounds_mapping(item)
        record = {
            "id": identifier,
            "actor_label": actor_label,
            "asset_path": asset_path,
            "source": "asset_override",
            "match_keys": _binding_keys(identifier, actor_label, asset_path),
            "override_index": index,
        }
        if imported_size:
            record["approx_size_cm"] = _rounded_vector(imported_size)
        if imported_bounds:
            record["bounds"] = imported_bounds
        records.append(record)
    return records


def _records_by_binding_key(records: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for record in records:
        for key in record.get("match_keys", []) if isinstance(record.get("match_keys"), list) else []:
            if key and key not in lookup:
                lookup[key] = dict(record)
    return lookup


def _generation_tasks_by_id(composition_plan: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    tasks: Dict[str, Dict[str, Any]] = {}
    for task in composition_plan.get("generation_tasks", []) if isinstance(composition_plan.get("generation_tasks"), list) else []:
        if not isinstance(task, Mapping):
            continue
        task_id = str(task.get("id") or "").strip()
        if task_id:
            tasks[task_id] = dict(task)
    return tasks


def _props_by_id(composition_plan: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    props: Dict[str, Dict[str, Any]] = {}
    for prop in composition_plan.get("props", []) if isinstance(composition_plan.get("props"), list) else []:
        if not isinstance(prop, Mapping):
            continue
        prop_id = str(prop.get("id") or prop.get("detected_item_id") or "").strip()
        if prop_id:
            props[prop_id] = dict(prop)
    return props


def _asset_binding_for_step(
    *,
    step: Mapping[str, Any],
    prop: Mapping[str, Any],
    record_lookup: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    arguments = _placement_step_arguments(step)
    step_id = str(step.get("id") or prop.get("id") or "").strip()
    actor_label = str(arguments.get("actor_label") or (prop.get("placement") or {}).get("actor_label") or "").strip()
    original_asset_path = str(arguments.get("asset_path") or prop.get("matched_asset_path") or prop.get("asset_path_placeholder") or "").strip()
    existing_asset = _first_clean_asset_path(original_asset_path) if original_asset_path.startswith("/Game") else ""
    if existing_asset:
        return {
            "status": "resolved",
            "id": step_id,
            "actor_label": actor_label,
            "asset_path": existing_asset,
            "source": "existing_or_planned_asset",
            "matched_by": "placement_step.asset_path",
            "original_asset_path": original_asset_path,
        }

    candidate_keys = _binding_keys(
        step_id,
        actor_label,
        prop.get("name"),
        prop.get("detected_item_id"),
        prop.get("asset_path_placeholder"),
        original_asset_path,
    )
    for key in candidate_keys:
        record = record_lookup.get(key)
        if record:
            binding = {
                "status": "resolved",
                "id": step_id,
                "actor_label": actor_label,
                "asset_path": str(record.get("asset_path") or ""),
                "source": str(record.get("source") or "asset_binding"),
                "matched_by": key,
                "original_asset_path": original_asset_path,
                "task_id": record.get("task_id", ""),
            }
            if record.get("approx_size_cm"):
                binding["approx_size_cm"] = record.get("approx_size_cm")
            if isinstance(record.get("bounds"), Mapping):
                binding["bounds"] = dict(record["bounds"])
            return binding
    return {
        "status": "unresolved",
        "id": step_id,
        "actor_label": actor_label,
        "asset_path": "",
        "source": "missing_import_result",
        "matched_by": "",
        "original_asset_path": original_asset_path,
    }


def _spatial_fit_from_sources(prop: Mapping[str, Any], generation_task: Mapping[str, Any]) -> Dict[str, Any]:
    if isinstance(prop.get("spatial_fit"), Mapping):
        return dict(prop["spatial_fit"])
    if isinstance(generation_task.get("spatial_fit"), Mapping):
        return dict(generation_task["spatial_fit"])
    return {}


def _spatial_fit_review_for_binding(
    *,
    step: Mapping[str, Any],
    prop: Mapping[str, Any],
    binding: Mapping[str, Any],
    generation_task: Mapping[str, Any],
    surface_tolerance: float,
    clearance_padding: float,
) -> Dict[str, Any]:
    spatial_fit = _spatial_fit_from_sources(prop, generation_task)
    generated_source = (
        bool(generation_task)
        or str(prop.get("source") or "").lower() in {"tripo_candidate", "generated_asset", "screenshot_crop", "tripo"}
        or str(binding.get("source") or "").lower() in {"tripo_import_result", "asset_override", "missing_import_result"}
    )
    planned_size = _size_vector(spatial_fit.get("approx_size_cm")) or _size_vector(prop.get("approx_size_cm") or prop.get("size"))
    imported_size = _asset_size_vector(binding)
    if not (spatial_fit or planned_size or imported_size or generated_source):
        return {}

    actor_label = str(
        binding.get("actor_label")
        or _placement_step_arguments(step).get("actor_label")
        or (prop.get("placement") or {}).get("actor_label")
        or ""
    ).strip()
    review_requirements = _merge_unique(
        spatial_fit.get("generation_requirements", []) if isinstance(spatial_fit.get("generation_requirements"), list) else [],
        generation_task.get("review_requirements", []) if isinstance(generation_task.get("review_requirements"), list) else [],
    )
    contact_requirement = str(spatial_fit.get("contact_requirement") or "").strip()
    if contact_requirement:
        review_requirements = _merge_unique(review_requirements, [contact_requirement])

    size_match = _size_match_score({"approx_size_cm": planned_size}, {"approx_size_cm": imported_size})
    if binding.get("status") != "resolved":
        status = "waiting_for_import_result"
        review_requirements = _merge_unique(review_requirements, ["complete Tripo generation/import before placement"])
    elif not imported_size:
        status = "needs_bounds_review"
        review_requirements = _merge_unique(review_requirements, ["catalog or inspect imported mesh bounds before mutation"])
    elif not planned_size:
        status = "needs_planned_size_review"
        review_requirements = _merge_unique(review_requirements, ["add planned approx_size_cm or spatial_fit before final placement"])
    elif size_match.get("reason") in {"size_loose_mismatch", "size_strong_mismatch"}:
        status = "needs_size_review"
        review_requirements = _merge_unique(review_requirements, ["rescale, regenerate, or replace the asset before final placement"])
    else:
        status = "ready_for_spatial_validation"

    review_requirements = _merge_unique(
        review_requirements,
        [
            "run dry-run placement before allow_mutation",
            "run spatial_validate_placement against surface contact and clearance",
        ],
    )
    review = {
        "id": str(binding.get("id") or step.get("id") or prop.get("id") or "").strip(),
        "prop_name": str(prop.get("name") or generation_task.get("prop_name") or binding.get("id") or "").strip(),
        "actor_label": actor_label,
        "asset_path": str(binding.get("asset_path") or ""),
        "asset_binding_source": str(binding.get("source") or ""),
        "status": status,
        "surface": str(spatial_fit.get("surface") or prop.get("surface") or "").strip(),
        "zone": str(spatial_fit.get("zone") or prop.get("zone") or "").strip(),
        "planned_size_cm": _rounded_vector(planned_size) if planned_size else [],
        "imported_size_cm": _rounded_vector(imported_size) if imported_size else [],
        "size_match": size_match,
        "contact_requirement": contact_requirement,
        "review_requirements": review_requirements,
        "validation_settings": {
            "surface_tolerance": surface_tolerance,
            "clearance_padding": clearance_padding,
        },
        "recommended_next_tools": [
            "spatial_preflight_interior_layout",
            "spatial_plan_layout_preflight_corrections",
            "spatial_add_asset_to_scene",
            "spatial_validate_placement",
        ],
    }
    if spatial_fit:
        review["spatial_fit"] = spatial_fit
    return review


def _spatial_fit_review_summary(reviews: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    ready = 0
    missing_bounds = 0
    size_review = 0
    unresolved = 0
    other_review = 0
    for review in reviews:
        status = str(review.get("status") or "")
        if status in SPATIAL_FIT_READY_STATUSES:
            ready += 1
        elif status == "needs_bounds_review":
            missing_bounds += 1
        elif status == "needs_size_review":
            size_review += 1
        elif status == "waiting_for_import_result":
            unresolved += 1
        else:
            other_review += 1
    return {
        "ready_count": ready,
        "missing_bounds_count": missing_bounds,
        "size_review_count": size_review,
        "unresolved_count": unresolved,
        "other_review_count": other_review,
    }


def _asset_scale_review_blocking_status(status: str) -> bool:
    return str(status or "").strip() not in SPATIAL_FIT_READY_STATUSES


def _median_float(values: Sequence[float]) -> float:
    cleaned = sorted(float(value) for value in values if float(value) > 0.0)
    if not cleaned:
        return 1.0
    midpoint = len(cleaned) // 2
    if len(cleaned) % 2:
        return cleaned[midpoint]
    return (cleaned[midpoint - 1] + cleaned[midpoint]) / 2.0


def _asset_bindings_by_key(composition_plan: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    for binding in composition_plan.get("asset_bindings", []) if isinstance(composition_plan.get("asset_bindings"), list) else []:
        if not isinstance(binding, Mapping):
            continue
        for key in _binding_keys(binding.get("id"), binding.get("actor_label"), binding.get("asset_path"), binding.get("prop_name")):
            lookup.setdefault(key, dict(binding))
    return lookup


def _asset_binding_for_scale_step(
    *,
    step_id: str,
    actor_label: str,
    asset_path: str,
    step: Mapping[str, Any],
    bindings_by_key: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    direct = step.get("asset_binding") if isinstance(step.get("asset_binding"), Mapping) else {}
    if direct:
        return dict(direct)
    for key in _binding_keys(step_id, actor_label, asset_path):
        binding = bindings_by_key.get(key)
        if binding:
            return dict(binding)
    return {}


def _scale_correction_review_context(
    *,
    step_id: str,
    actor_label: str,
    asset_path: str,
    step: Mapping[str, Any],
    review: Mapping[str, Any],
    prop: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> tuple[List[float], List[float], str]:
    planned_size = (
        _size_vector(review.get("planned_size_cm"))
        or _size_vector((prop.get("spatial_fit") or {}).get("approx_size_cm") if isinstance(prop.get("spatial_fit"), Mapping) else None)
        or _size_vector(prop.get("approx_size_cm") or prop.get("size"))
    )
    imported_size = (
        _size_vector(review.get("imported_size_cm"))
        or _asset_size_vector(binding)
        or _asset_size_vector(step.get("asset_binding") if isinstance(step.get("asset_binding"), Mapping) else {})
    )
    source = "spatial_fit_review" if review else ("prop_and_asset_binding" if (planned_size or imported_size) else "")
    if not prop:
        for key in _binding_keys(step_id, actor_label, asset_path):
            if key and str(review.get("id") or "").strip() == key:
                source = "spatial_fit_review"
                break
    return planned_size, imported_size, source


def _scale_correction_record_for_step(
    *,
    step: Mapping[str, Any],
    index: int,
    reviews_by_key: Mapping[str, Mapping[str, Any]],
    props_by_id: Mapping[str, Mapping[str, Any]],
    bindings_by_key: Mapping[str, Mapping[str, Any]],
    min_scale: float,
    max_scale: float,
    anisotropy_tolerance: float,
    close_scale_tolerance: float,
    allow_non_uniform_scale: bool,
) -> Dict[str, Any]:
    arguments = _placement_step_arguments(step)
    step_id = str(step.get("id") or arguments.get("actor_label") or f"step_{index + 1}").strip()
    actor_label = str(arguments.get("actor_label") or step_id).strip()
    asset_path = str(arguments.get("asset_path") or "").strip()
    current_scale = _optional_vector3(arguments.get("scale")) or [1.0, 1.0, 1.0]
    review = _spatial_fit_review_for_step(
        step_id=step_id,
        actor_label=actor_label,
        asset_path=asset_path,
        step=step,
        reviews_by_key=reviews_by_key,
    )
    prop = props_by_id.get(step_id, {})
    binding = _asset_binding_for_scale_step(
        step_id=step_id,
        actor_label=actor_label,
        asset_path=asset_path,
        step=step,
        bindings_by_key=bindings_by_key,
    )
    planned_size, imported_size, source = _scale_correction_review_context(
        step_id=step_id,
        actor_label=actor_label,
        asset_path=asset_path,
        step=step,
        review=review,
        prop=prop,
        binding=binding,
    )
    if not (review or planned_size or imported_size):
        return {}

    base = {
        "id": step_id,
        "index": index,
        "actor_label": actor_label,
        "asset_path": asset_path,
        "current_scale": _rounded_vector(current_scale),
        "planned_size_cm": _rounded_vector(planned_size) if planned_size else [],
        "imported_size_cm": _rounded_vector(imported_size) if imported_size else [],
        "source": source,
        "spatial_fit_review_status": str(review.get("status") or "").strip(),
        "review_requirements": list(review.get("review_requirements", [])) if isinstance(review.get("review_requirements"), list) else [],
        "blocking": False,
    }
    if binding.get("status") and binding.get("status") != "resolved":
        base.update({
            "status": "waiting_for_import_result",
            "reason": "Asset is not resolved yet; complete import/binding before scale correction.",
            "blocking": True,
        })
        return base
    if not planned_size or not imported_size:
        base.update({
            "status": "missing_size_evidence",
            "reason": "Scale correction needs both planned_size_cm and imported_size_cm or import bounds.",
            "blocking": True,
            "recommended_next_tools": ["spatial_bind_generated_assets_to_composition", "spatial_catalog_project_assets"],
        })
        return base

    axis_scale = [
        planned_size[index] / imported_size[index]
        for index in range(3)
        if imported_size[index] > 0.0
    ]
    if len(axis_scale) != 3:
        base.update({
            "status": "missing_size_evidence",
            "reason": "Imported dimensions must contain three positive numbers.",
            "blocking": True,
        })
        return base

    uniform_ratio = _median_float(axis_scale)
    axis_min = min(axis_scale)
    axis_max = max(axis_scale)
    anisotropy_ratio = axis_max / axis_min if axis_min > 0.0 else math.inf
    deviation = max(abs((axis / uniform_ratio) - 1.0) for axis in axis_scale) if uniform_ratio > 0.0 else math.inf
    uniform_scale = [current_scale[index] * uniform_ratio for index in range(3)]
    non_uniform_scale = [current_scale[index] * axis_scale[index] for index in range(3)]
    close_delta = max(abs(uniform_scale[index] - current_scale[index]) for index in range(3))

    base.update({
        "axis_scale": _rounded_vector(axis_scale),
        "uniform_ratio": round(uniform_ratio, 4),
        "anisotropy_ratio": round(anisotropy_ratio, 4) if math.isfinite(anisotropy_ratio) else "inf",
        "anisotropy_deviation": round(deviation, 4) if math.isfinite(deviation) else "inf",
        "uniform_scale": _rounded_vector(uniform_scale),
        "non_uniform_scale": _rounded_vector(non_uniform_scale),
        "corrected_uniform_size_cm": _rounded_vector([imported_size[index] * uniform_scale[index] for index in range(3)]),
        "corrected_non_uniform_size_cm": _rounded_vector([imported_size[index] * non_uniform_scale[index] for index in range(3)]),
    })
    if close_delta <= close_scale_tolerance:
        base.update({
            "status": "already_close",
            "reason": "Current scale is already within the requested scale tolerance.",
            "scale_mode": "unchanged",
            "recommended_scale": _rounded_vector(current_scale),
            "review_status_after_correction": "ready_for_spatial_validation",
        })
        return base
    if min(uniform_scale) < min_scale or max(uniform_scale) > max_scale:
        base.update({
            "status": "scale_out_of_policy",
            "reason": "Uniform scale needed to match the room plan is outside the allowed scale policy; regenerate or replace the asset.",
            "blocking": True,
            "recommended_next_tools": ["spatial_prepare_tripo_generation_batch", "spatial_resolve_project_assets"],
        })
        return base
    if deviation <= anisotropy_tolerance:
        base.update({
            "status": "ready_for_scaled_dry_run",
            "reason": "Uniform scale can bring imported bounds close to the planned environment dimensions.",
            "scale_mode": "uniform",
            "recommended_scale": _rounded_vector(uniform_scale),
            "review_status_after_correction": "ready_for_scaled_spatial_validation",
        })
        return base
    if allow_non_uniform_scale:
        if min(non_uniform_scale) < min_scale or max(non_uniform_scale) > max_scale:
            base.update({
                "status": "scale_out_of_policy",
                "reason": "Non-uniform scale needed to match the room plan is outside the allowed scale policy; regenerate or replace the asset.",
                "blocking": True,
                "recommended_next_tools": ["spatial_prepare_tripo_generation_batch", "spatial_resolve_project_assets"],
            })
            return base
        base.update({
            "status": "ready_for_scaled_dry_run",
            "reason": "Non-uniform scale is required; review visual distortion before mutation.",
            "scale_mode": "non_uniform",
            "recommended_scale": _rounded_vector(non_uniform_scale),
            "review_status_after_correction": "ready_for_scaled_spatial_validation",
            "warnings": ["Non-uniform scale can distort generated meshes; prefer regeneration when visual fidelity matters."],
        })
        return base
    base.update({
        "status": "needs_non_uniform_or_regenerate",
        "reason": "Imported dimensions differ too much by axis for safe uniform scale; regenerate, replace, or allow non-uniform scale explicitly.",
        "blocking": True,
        "recommended_next_tools": ["spatial_prepare_tripo_generation_batch", "spatial_resolve_project_assets"],
    })
    return base


def _review_after_scale_correction(review: Mapping[str, Any], correction: Mapping[str, Any]) -> Dict[str, Any]:
    updated = dict(review)
    if not updated:
        updated = {
            "id": correction.get("id", ""),
            "actor_label": correction.get("actor_label", ""),
            "asset_path": correction.get("asset_path", ""),
        }
    updated["asset_scale_correction"] = {
        "status": correction.get("status"),
        "scale_mode": correction.get("scale_mode", ""),
        "recommended_scale": correction.get("recommended_scale", []),
        "planned_size_cm": correction.get("planned_size_cm", []),
        "imported_size_cm": correction.get("imported_size_cm", []),
        "corrected_size_cm": (
            correction.get("corrected_non_uniform_size_cm")
            if correction.get("scale_mode") == "non_uniform"
            else correction.get("corrected_uniform_size_cm", [])
        ),
    }
    next_status = str(correction.get("review_status_after_correction") or "").strip()
    if next_status:
        updated["status"] = next_status
    requirements = list(updated.get("review_requirements", [])) if isinstance(updated.get("review_requirements"), list) else []
    updated["review_requirements"] = _merge_unique(
        requirements,
        [
            "run scaled dry-run placement before allow_mutation",
            "validate corrected bounds against surface contact and clearance",
        ],
    )
    return updated


def _step_after_scale_correction(
    *,
    step: Mapping[str, Any],
    correction: Mapping[str, Any],
    review: Mapping[str, Any],
) -> Dict[str, Any]:
    updated = dict(step)
    arguments = _placement_step_arguments(updated)
    if correction.get("recommended_scale") and not correction.get("blocking"):
        arguments["scale"] = list(correction.get("recommended_scale") or [])
        arguments["dry_run"] = True
        arguments["allow_mutation"] = False
    updated["arguments"] = arguments
    updated["asset_scale_correction"] = dict(correction)
    if review:
        updated["spatial_fit_review"] = dict(review)
        binding = updated.get("asset_binding") if isinstance(updated.get("asset_binding"), Mapping) else {}
        if binding:
            binding = dict(binding)
            binding["spatial_fit_review"] = dict(review)
            updated["asset_binding"] = binding
    return updated


def _scale_corrections_by_step(corrections: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    for correction in corrections:
        if not isinstance(correction, Mapping):
            continue
        key = str(correction.get("id") or "").strip()
        if key:
            by_id[key] = dict(correction)
    return by_id


def _step_surface_anchor_prop(
    *,
    step_id: str,
    prop: Mapping[str, Any],
    arguments: Mapping[str, Any],
) -> Dict[str, Any]:
    if prop:
        candidate = dict(prop)
    else:
        candidate = {"id": step_id, "name": step_id}
    if not candidate.get("surface") and arguments.get("surface"):
        candidate["surface"] = arguments.get("surface")
    if not candidate.get("zone") and arguments.get("zone"):
        candidate["zone"] = arguments.get("zone")
    if not candidate.get("category") and arguments.get("category"):
        candidate["category"] = arguments.get("category")
    return candidate


def _zone_for_anchor_step(
    *,
    room: Mapping[str, Any],
    prop_details: Mapping[str, Any],
    location: Sequence[float],
) -> Dict[str, Any]:
    zones = room.get("zones") if isinstance(room.get("zones"), list) else []
    zone_name = str(prop_details.get("zone") or "").strip()
    for zone in zones:
        if isinstance(zone, Mapping) and str(zone.get("name") or "") == zone_name:
            return dict(zone)
    for zone in zones:
        if isinstance(zone, Mapping) and _zone_contains_xy(zone, location):
            return dict(zone)
    if zones and isinstance(zones[0], Mapping):
        return dict(zones[0])
    return {
        "name": zone_name or "room",
        "center": room.get("origin", [0.0, 0.0, 0.0]),
        "size": room.get("dimensions_cm", [650.0, 500.0, 280.0]),
        "wall": "open_center",
    }


def _surface_anchor_required(prop_details: Mapping[str, Any]) -> bool:
    surface = str(prop_details.get("surface") or "").strip().lower()
    category = str(prop_details.get("category") or "").strip().lower()
    name = str(prop_details.get("name") or "").strip().lower()
    if surface in {"counter", "table", "shelf", "cabinet", "wall"}:
        return True
    if "wall cabinet" in name or "upper cabinet" in name:
        return True
    if category in {"fixture", "dressing"} and surface not in {"", "floor"}:
        return True
    return False


def _composition_support_surface_kind(prop: Mapping[str, Any]) -> str:
    surface = str(prop.get("surface") or "").strip().lower()
    category = str(prop.get("category") or "").strip().lower()
    text = " ".join([
        str(prop.get("id") or ""),
        str(prop.get("name") or ""),
        category,
        surface,
    ]).lower().replace("_", " ").replace("-", " ")
    if surface not in {"", "floor"}:
        return ""
    if category == "counter" or any(token in text for token in ("counter run", "countertop", "kitchen counter", "island")):
        return "counter"
    if category == "table" or any(token in text for token in ("coffee table", "console table", "nightstand", "desk")):
        return "table"
    if any(token in text for token in ("shelf", "bookshelf", "bookcase", "storage shelf")):
        return "shelf"
    if any(token in text for token in ("base cabinet", "lower cabinet", "dresser")):
        return "cabinet"
    return ""


def _composition_support_surface_default_size(kind: str) -> List[float]:
    return {
        "counter": [240.0, 65.0, 95.0],
        "table": [110.0, 65.0, 45.0],
        "shelf": [100.0, 40.0, 160.0],
        "cabinet": [160.0, 55.0, 95.0],
    }.get(kind, [100.0, 60.0, 80.0])


def _composition_support_surface_top_z(kind: str, location_z: float, height: float) -> float:
    if kind == "shelf":
        usable_height = min(float(height) - 8.0, max(90.0, float(height) * 0.55))
        return float(location_z) + max(40.0, usable_height)
    return float(location_z) + float(height)


def _composition_support_surfaces(composition_plan: Mapping[str, Any]) -> List[Dict[str, Any]]:
    props = composition_plan.get("props") if isinstance(composition_plan.get("props"), list) else []
    steps_by_id = _placement_steps_by_id(composition_plan)
    surfaces: List[Dict[str, Any]] = []
    for index, prop in enumerate(props):
        if not isinstance(prop, Mapping):
            continue
        kind = _composition_support_surface_kind(prop)
        if not kind:
            continue
        prop_id = _safe_asset_stem(str(prop.get("id") or prop.get("detected_item_id") or prop.get("name") or f"support_{index}"), "support")
        step = steps_by_id.get(prop_id, {})
        arguments = _placement_step_arguments(step) if step else {}
        placement = prop.get("placement") if isinstance(prop.get("placement"), Mapping) else {}
        location = _optional_vector3(arguments.get("location")) or _optional_vector3(placement.get("location"))
        if location is None:
            continue
        size = (
            _size_vector_from_any(prop.get("approx_size_cm"))
            or _size_vector_from_any(prop.get("size"))
            or _size_vector_from_any((prop.get("spatial_fit") or {}).get("approx_size_cm") if isinstance(prop.get("spatial_fit"), Mapping) else None)
            or _composition_support_surface_default_size(kind)
        )
        width, depth, height = [max(1.0, float(component)) for component in size[:3]]
        top_z = _composition_support_surface_top_z(kind, float(location[2]), height)
        actor_label = str(arguments.get("actor_label") or placement.get("actor_label") or prop_id)
        min_v = [float(location[0]) - width / 2.0, float(location[1]) - depth / 2.0, float(location[2])]
        max_v = [float(location[0]) + width / 2.0, float(location[1]) + depth / 2.0, float(location[2]) + height]
        surfaces.append({
            "id": f"composition_support_{prop_id}",
            "label": actor_label,
            "name": str(prop.get("name") or prop_id),
            "source": "composition_prop",
            "source_prop_id": prop_id,
            "support_kind": kind,
            "zone": str(prop.get("zone") or ""),
            "roles": ["horizontal_support", "composition_support_surface", kind],
            "top_center": _rounded_vector([float(location[0]), float(location[1]), top_z]),
            "bounds": {
                "min": _rounded_vector(min_v),
                "max": _rounded_vector(max_v),
            },
        })
    return surfaces[:64]


def _composition_wall_surface(
    *,
    zone: Mapping[str, Any],
    side: str,
    room: Mapping[str, Any],
    index: int,
) -> Optional[Dict[str, Any]]:
    if side not in {"negative_x", "positive_x", "negative_y", "positive_y"}:
        return None
    center = _optional_vector3(zone.get("center")) or _optional_vector3(room.get("origin")) or [0.0, 0.0, 0.0]
    size = _optional_vector3(zone.get("size")) or _optional_vector3(room.get("dimensions_cm")) or [650.0, 500.0, 280.0]
    room_bounds = room.get("bounds") if isinstance(room.get("bounds"), Mapping) else {}
    room_min = _optional_vector3(room_bounds.get("min")) or [
        float(center[0]) - float(size[0]) / 2.0,
        float(center[1]) - float(size[1]) / 2.0,
        float(center[2]),
    ]
    room_max = _optional_vector3(room_bounds.get("max")) or [
        float(center[0]) + float(size[0]) / 2.0,
        float(center[1]) + float(size[1]) / 2.0,
        float(center[2]) + float(size[2]),
    ]
    thickness = 10.0
    zone_min_x = max(float(room_min[0]), float(center[0]) - float(size[0]) / 2.0)
    zone_max_x = min(float(room_max[0]), float(center[0]) + float(size[0]) / 2.0)
    zone_min_y = max(float(room_min[1]), float(center[1]) - float(size[1]) / 2.0)
    zone_max_y = min(float(room_max[1]), float(center[1]) + float(size[1]) / 2.0)
    if side == "negative_y":
        min_v = [zone_min_x, zone_min_y, float(room_min[2])]
        max_v = [zone_max_x, min(zone_min_y + thickness, zone_max_y), float(room_max[2])]
    elif side == "positive_y":
        min_v = [zone_min_x, max(zone_min_y, zone_max_y - thickness), float(room_min[2])]
        max_v = [zone_max_x, zone_max_y, float(room_max[2])]
    elif side == "negative_x":
        min_v = [zone_min_x, zone_min_y, float(room_min[2])]
        max_v = [min(zone_min_x + thickness, zone_max_x), zone_max_y, float(room_max[2])]
    else:
        min_v = [max(zone_min_x, zone_max_x - thickness), zone_min_y, float(room_min[2])]
        max_v = [zone_max_x, zone_max_y, float(room_max[2])]
    if min_v[0] >= max_v[0] or min_v[1] >= max_v[1] or min_v[2] >= max_v[2]:
        return None
    zone_name = _safe_asset_stem(str(zone.get("name") or f"zone_{index}"), "zone")
    label = f"composition_wall_{zone_name}_{side}"
    return {
        "id": label,
        "label": label,
        "name": f"{zone.get('name') or 'zone'} {side} wall",
        "source": "composition_room",
        "zone": str(zone.get("name") or ""),
        "wall": side,
        "roles": ["wall", "composition_wall_surface", side],
        "top_center": _rounded_vector([
            (min_v[0] + max_v[0]) / 2.0,
            (min_v[1] + max_v[1]) / 2.0,
            max_v[2],
        ]),
        "bounds": {
            "min": _rounded_vector(min_v),
            "max": _rounded_vector(max_v),
        },
    }


def _composition_wall_surfaces(room: Mapping[str, Any]) -> List[Dict[str, Any]]:
    zones = room.get("zones") if isinstance(room.get("zones"), list) else []
    surfaces: List[Dict[str, Any]] = []
    seen = set()
    for index, zone in enumerate(zones):
        if not isinstance(zone, Mapping):
            continue
        side = str(zone.get("wall") or "").strip().lower()
        surface = _composition_wall_surface(zone=zone, side=side, room=room, index=index)
        if surface is None:
            continue
        key = str(surface.get("id") or "")
        if key in seen:
            continue
        surfaces.append(surface)
        seen.add(key)
    return surfaces[:32]


def _room_analysis_with_composition_surfaces(
    *,
    composition_plan: Mapping[str, Any],
    room_analysis: Mapping[str, Any],
    room: Mapping[str, Any],
) -> tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    composition_surfaces = _composition_support_surfaces(composition_plan)
    composition_walls = _composition_wall_surfaces(room)
    if not composition_surfaces and not composition_walls:
        return dict(room_analysis), [], []
    enriched = dict(room_analysis)
    classified = dict(enriched.get("classified_surfaces") or {}) if isinstance(enriched.get("classified_surfaces"), Mapping) else {}
    existing = [
        dict(surface)
        for surface in classified.get("horizontal_supports", [])
        if isinstance(surface, Mapping)
    ] if isinstance(classified.get("horizontal_supports"), list) else []
    seen = {
        str(surface.get("label") or surface.get("id") or surface.get("source_prop_id") or "").lower()
        for surface in existing
    }
    merged = list(existing)
    for surface in composition_surfaces:
        key = str(surface.get("label") or surface.get("id") or surface.get("source_prop_id") or "").lower()
        if key in seen:
            continue
        merged.append(surface)
        seen.add(key)
    classified["horizontal_supports"] = merged
    existing_walls = [
        dict(surface)
        for surface in classified.get("walls", [])
        if isinstance(surface, Mapping)
    ] if isinstance(classified.get("walls"), list) else []
    wall_seen = {
        str(surface.get("label") or surface.get("id") or "").lower()
        for surface in existing_walls
    }
    merged_walls = list(existing_walls)
    if not existing_walls:
        for wall in composition_walls:
            key = str(wall.get("label") or wall.get("id") or "").lower()
            if key in wall_seen:
                continue
            merged_walls.append(wall)
            wall_seen.add(key)
    classified["walls"] = merged_walls
    enriched["classified_surfaces"] = classified
    enriched.setdefault("schema", ROOM_ANALYSIS_SCHEMA)
    enriched.setdefault("source", "composition_surface_enriched")
    return enriched, composition_surfaces, composition_walls


def _support_anchor_record_for_step(
    *,
    step: Mapping[str, Any],
    index: int,
    composition_plan: Mapping[str, Any],
    room_analysis: Mapping[str, Any],
    room: Mapping[str, Any],
    anchor_floor: bool,
    anchor_horizontal_supports: bool,
    anchor_walls: bool,
) -> Dict[str, Any]:
    arguments = _placement_step_arguments(step)
    step_id = str(step.get("id") or arguments.get("actor_label") or f"step_{index + 1}").strip()
    actor_label = str(arguments.get("actor_label") or step_id).strip()
    current_location = _optional_vector3(arguments.get("location")) or [0.0, 0.0, float(room.get("origin", [0.0, 0.0, 0.0])[2])]
    current_rotation = _optional_vector3(arguments.get("rotation")) or [0.0, 0.0, 0.0]
    props_by_id = _props_by_id(composition_plan)
    prop = _step_surface_anchor_prop(
        step_id=step_id,
        prop=props_by_id.get(step_id, {}),
        arguments=arguments,
    )
    details = _prop_size_surface_zone(prop, step_id)
    surface = str(details.get("surface") or "").strip().lower()
    zone = _zone_for_anchor_step(room=room, prop_details=details, location=current_location)
    enabled_for_surface = (
        (surface == "floor" and anchor_floor)
        or (surface in {"counter", "table", "shelf", "cabinet"} and anchor_horizontal_supports)
        or (surface == "wall" and anchor_walls)
        or ("wall cabinet" in str(details.get("name") or "").lower() and anchor_walls)
    )
    record = {
        "id": step_id,
        "index": index,
        "actor_label": actor_label,
        "asset_path": str(arguments.get("asset_path") or ""),
        "name": str(details.get("name") or step_id),
        "surface": surface,
        "zone": str(zone.get("name") or details.get("zone") or ""),
        "current_location": _rounded_vector(current_location),
        "current_rotation": _rounded_vector(current_rotation),
        "required": _surface_anchor_required(details),
        "blocking": False,
    }
    if not enabled_for_surface:
        record.update({
            "status": "not_applicable",
            "reason": "This placement step does not require a supported floor/counter/table/shelf/wall anchor for the enabled anchor modes.",
        })
        return record
    if not room_analysis:
        record.update({
            "status": "missing_room_analysis",
            "reason": "Support-surface anchoring needs spatial_analyze_room output with classified surfaces.",
            "blocking": bool(record["required"]),
            "recommended_next_tools": ["spatial_analyze_room", "spatial_surface_probe"],
        })
        return record
    transform = _room_analysis_location_for_prop(
        prop,
        room_analysis=room_analysis,
        zone=zone,
        room_origin=room.get("origin", [0.0, 0.0, 0.0]),
        index=index,
        fallback_location=current_location,
        fallback_rotation=current_rotation,
    )
    if not transform:
        record.update({
            "status": "needs_surface_probe",
            "reason": "Room analysis did not include a matching support surface; probe or add support geometry before mutation.",
            "blocking": bool(record["required"]),
            "recommended_next_tools": ["spatial_surface_probe", "spatial_analyze_room"],
        })
        return record
    anchored_location = _rounded_vector(transform.get("location", current_location))
    anchored_rotation = _rounded_vector(transform.get("rotation", current_rotation))
    delta = [
        round(anchored_location[axis] - float(current_location[axis]), 3)
        for axis in range(3)
    ]
    record.update({
        "status": "anchored",
        "reason": "Placement was aligned to a classified room support surface.",
        "source": str(transform.get("source") or ""),
        "support_actor": str(transform.get("support_actor") or ""),
        "support_roles": list(transform.get("support_roles", [])) if isinstance(transform.get("support_roles"), list) else [],
        "anchored_location": anchored_location,
        "anchored_rotation": anchored_rotation,
        "location_delta_cm": delta,
        "surface_probe_point": anchored_location,
    })
    return record


def _step_after_support_anchor(step: Mapping[str, Any], anchor: Mapping[str, Any]) -> Dict[str, Any]:
    updated = dict(step)
    arguments = _placement_step_arguments(updated)
    if anchor.get("status") == "anchored":
        arguments["location"] = list(anchor.get("anchored_location") or arguments.get("location") or [0.0, 0.0, 0.0])
        arguments["rotation"] = list(anchor.get("anchored_rotation") or arguments.get("rotation") or [0.0, 0.0, 0.0])
        arguments["placement_source"] = str(anchor.get("source") or arguments.get("placement_source") or "")
        arguments["support_actor"] = str(anchor.get("support_actor") or arguments.get("support_actor") or "")
        arguments["support_roles"] = list(anchor.get("support_roles", [])) if isinstance(anchor.get("support_roles"), list) else list(arguments.get("support_roles", [])) if isinstance(arguments.get("support_roles"), list) else []
        arguments["dry_run"] = True
        arguments["allow_mutation"] = False
    updated["arguments"] = arguments
    updated["support_surface_anchor"] = dict(anchor)
    return updated


def _props_after_support_anchors(
    *,
    composition_plan: Mapping[str, Any],
    anchors_by_id: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    updated_props: List[Dict[str, Any]] = []
    for prop in composition_plan.get("props", []) if isinstance(composition_plan.get("props"), list) else []:
        if not isinstance(prop, Mapping):
            continue
        updated = dict(prop)
        prop_id = str(updated.get("id") or updated.get("detected_item_id") or "").strip()
        anchor = anchors_by_id.get(prop_id)
        if anchor and anchor.get("status") == "anchored":
            placement = dict(updated.get("placement") or {}) if isinstance(updated.get("placement"), Mapping) else {}
            placement.update({
                "location": list(anchor.get("anchored_location") or placement.get("location") or []),
                "rotation": list(anchor.get("anchored_rotation") or placement.get("rotation") or []),
                "source": str(anchor.get("source") or placement.get("source") or ""),
                "support_actor": str(anchor.get("support_actor") or placement.get("support_actor") or ""),
                "support_roles": list(anchor.get("support_roles", [])) if isinstance(anchor.get("support_roles"), list) else placement.get("support_roles", []),
            })
            updated["placement"] = placement
            updated["support_surface_anchor"] = dict(anchor)
        updated_props.append(updated)
    return updated_props


def _plan_support_surface_anchors(
    *,
    composition_plan: Mapping[str, Any],
    room_analysis: Mapping[str, Any],
    anchor_floor: bool,
    anchor_horizontal_supports: bool,
    anchor_walls: bool,
    include_updated_plan: bool,
    limit: int,
) -> Dict[str, Any]:
    room = _room_context_for_preflight(composition_plan=composition_plan, room_analysis=room_analysis)
    anchor_room_analysis, composition_support_surfaces, composition_wall_surfaces = _room_analysis_with_composition_surfaces(
        composition_plan=composition_plan,
        room_analysis=room_analysis,
        room=room,
    )
    steps = composition_plan.get("placement_steps") if isinstance(composition_plan.get("placement_steps"), list) else []
    anchors: List[Dict[str, Any]] = []
    updated_steps: List[Dict[str, Any]] = []
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            continue
        anchor = {}
        if index < limit:
            anchor = _support_anchor_record_for_step(
                step=step,
                index=index,
                composition_plan=composition_plan,
                room_analysis=anchor_room_analysis,
                room=room,
                anchor_floor=anchor_floor,
                anchor_horizontal_supports=anchor_horizontal_supports,
                anchor_walls=anchor_walls,
            )
            anchors.append(anchor)
        updated_steps.append(_step_after_support_anchor(step, anchor) if anchor else dict(step))

    anchored = [item for item in anchors if item.get("status") == "anchored"]
    blockers = [item for item in anchors if item.get("blocking")]
    required = [item for item in anchors if item.get("required")]
    if blockers and anchored:
        status = "partial_support_surface_anchors_need_probe"
    elif blockers:
        status = "needs_surface_probe"
    elif anchored:
        status = "ready_for_support_surface_review"
    elif required:
        status = "support_anchors_not_applicable"
    else:
        status = "no_support_anchors_needed"

    anchors_by_id = {
        str(anchor.get("id") or ""): dict(anchor)
        for anchor in anchors
        if str(anchor.get("id") or "").strip()
    }
    updated_plan = dict(composition_plan)
    updated_plan["placement_steps"] = updated_steps
    updated_plan["all_placement_steps"] = updated_steps
    if isinstance(composition_plan.get("props"), list):
        updated_plan["props"] = _props_after_support_anchors(composition_plan=composition_plan, anchors_by_id=anchors_by_id)
    updated_plan["support_surface_anchors"] = anchors
    updated_plan["support_surface_anchor_summary"] = {
        "status": status,
        "anchored_count": len(anchored),
        "required_count": len(required),
        "blocker_count": len(blockers),
        "composition_support_surface_count": len(composition_support_surfaces),
        "composition_wall_surface_count": len(composition_wall_surfaces),
    }
    updated_plan_json = json.dumps(updated_plan, sort_keys=True) if include_updated_plan else "<SUPPORT_ANCHORED_COMPOSITION_PLAN_JSON>"
    probe_points = _merge_vector_lists(
        [anchor.get("surface_probe_point", []) for anchor in anchored if anchor.get("surface_probe_point")],
        [anchor.get("current_location", []) for anchor in blockers if anchor.get("current_location")],
        maximum=32,
    )
    actor_labels = [
        str((_placement_step_arguments(step).get("actor_label") or step.get("id") or "")).strip()
        for step in updated_steps
        if isinstance(step, Mapping) and (_placement_step_arguments(step).get("actor_label") or step.get("id"))
    ]
    return {
        "schema": SUPPORT_SURFACE_ANCHOR_SCHEMA,
        "status": status,
        "source_schema": composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
        "room": room,
        "placement_step_count": len(steps),
        "anchor_count": len(anchors),
        "required_count": len(required),
        "anchored_count": len(anchored),
        "blocker_count": len(blockers),
        "composition_support_surface_count": len(composition_support_surfaces),
        "composition_wall_surface_count": len(composition_wall_surfaces),
        "composition_support_surfaces": composition_support_surfaces,
        "composition_wall_surfaces": composition_wall_surfaces,
        "support_surface_source_summary": {
            "room_analysis_horizontal_support_count": len(_analysis_surfaces(room_analysis, "horizontal_supports")),
            "composition_support_surface_count": len(composition_support_surfaces),
            "merged_horizontal_support_count": len(_analysis_surfaces(anchor_room_analysis, "horizontal_supports")),
            "room_analysis_wall_count": len(_analysis_surfaces(room_analysis, "walls")),
            "composition_wall_surface_count": len(composition_wall_surfaces),
            "merged_wall_count": len(_analysis_surfaces(anchor_room_analysis, "walls")),
        },
        "blockers": blockers,
        "anchors": anchors,
        "updated_placement_steps": updated_steps,
        "updated_composition_plan": updated_plan if include_updated_plan else {},
        "updated_composition_plan_json": updated_plan_json,
        "surface_probe_handoff": {
            "tool": "spatial_surface_probe",
            "arguments": {"points": probe_points, "placement_offset": 0.0, "include_handoff": True},
            "enabled": bool(probe_points),
        },
        "layout_preflight_handoff": {
            "tool": "spatial_preflight_interior_layout",
            "arguments": {"composition_plan_json": updated_plan_json, "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>"},
            "enabled": bool(updated_steps and not blockers),
        },
        "candidate_clearance_handoff": {
            "tool": "spatial_preflight_candidate_clearance",
            "arguments": {"composition_plan_json": updated_plan_json, "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>"},
            "enabled": bool(updated_steps and not blockers),
        },
        "apply_handoff": {
            "tool": "spatial_apply_composition_plan",
            "arguments": {"composition_plan_json": updated_plan_json, "dry_run": True},
            "enabled": bool(updated_steps and not blockers),
        },
        "validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": actor_labels,
                "surface_tolerance": 15.0,
                "clearance_padding": 12.0,
                "include_evidence_handoff": True,
            },
            "enabled": bool(actor_labels and not blockers),
        },
        "workflow": [
            {"step": "review_room_surfaces", "tool": "spatial_analyze_room", "reason": "Confirm classified floor, wall, and horizontal support surfaces are current."},
            {"step": "derive_composition_support_surfaces", "enabled": bool(composition_support_surfaces), "support_surface_count": len(composition_support_surfaces), "reason": "Use planned counters, tables, shelves, and cabinets as temporary support surfaces for screenshot/generated compositions before live assets exist."},
            {"step": "derive_composition_wall_surfaces", "enabled": bool(composition_wall_surfaces), "wall_surface_count": len(composition_wall_surfaces), "reason": "Use inferred room and zone walls as temporary wall anchors for screenshot/generated wall props before live wall actors are classified."},
            {"step": "anchor_support_surfaces", "reason": "Update dry-run transforms so props touch the intended floor/counter/table/shelf/wall support."},
            {"step": "probe_anchored_points", "tool": "spatial_surface_probe", "enabled": bool(probe_points)},
            {"step": "preflight_layout", "tool": "spatial_preflight_interior_layout", "enabled": bool(updated_steps and not blockers)},
            {"step": "plan_layout_preflight_corrections", "tool": "spatial_plan_layout_preflight_corrections", "enabled": bool(updated_steps and not blockers)},
            {"step": "preflight_candidate_clearance", "tool": "spatial_preflight_candidate_clearance", "enabled": bool(updated_steps and not blockers)},
            {"step": "dry_run_apply", "tool": "spatial_apply_composition_plan", "enabled": bool(updated_steps and not blockers)},
            {"step": "validate_surface_contact", "tool": "spatial_validate_placement", "enabled": bool(actor_labels and not blockers)},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This support anchoring planner reuses Ghost room-analysis surface classifications, composition-derived support props, inferred room/zone wall planes, and Ghost placement schemas.",
                "It does not copy Epic native MCP/SceneTools source and does not mutate Unreal Editor state.",
            ],
        },
    }


def _plan_asset_scale_corrections(
    *,
    composition_plan: Mapping[str, Any],
    min_scale: float,
    max_scale: float,
    anisotropy_tolerance: float,
    close_scale_tolerance: float,
    allow_non_uniform_scale: bool,
    include_updated_plan: bool,
    limit: int,
) -> Dict[str, Any]:
    steps = composition_plan.get("placement_steps") if isinstance(composition_plan.get("placement_steps"), list) else []
    reviews_by_key = _spatial_fit_reviews_by_key(composition_plan)
    props_by_id = _props_by_id(composition_plan)
    bindings_by_key = _asset_bindings_by_key(composition_plan)
    corrections: List[Dict[str, Any]] = []
    updated_reviews_by_id: Dict[str, Dict[str, Any]] = {}
    updated_steps: List[Dict[str, Any]] = []

    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            continue
        correction: Dict[str, Any] = {}
        updated_review: Dict[str, Any] = {}
        if index < limit:
            correction = _scale_correction_record_for_step(
                step=step,
                index=index,
                reviews_by_key=reviews_by_key,
                props_by_id=props_by_id,
                bindings_by_key=bindings_by_key,
                min_scale=min_scale,
                max_scale=max_scale,
                anisotropy_tolerance=anisotropy_tolerance,
                close_scale_tolerance=close_scale_tolerance,
                allow_non_uniform_scale=allow_non_uniform_scale,
            )
            if correction:
                review = _spatial_fit_review_for_step(
                    step_id=str(correction.get("id") or ""),
                    actor_label=str(correction.get("actor_label") or ""),
                    asset_path=str(correction.get("asset_path") or ""),
                    step=step,
                    reviews_by_key=reviews_by_key,
                )
                if not correction.get("blocking") and correction.get("status") in {"ready_for_scaled_dry_run", "already_close"}:
                    updated_review = _review_after_scale_correction(review, correction)
                    updated_reviews_by_id[str(correction.get("id") or "")] = updated_review
                    correction["updated_spatial_fit_review"] = updated_review
                corrections.append(correction)
        if correction:
            updated_steps.append(_step_after_scale_correction(step=step, correction=correction, review=updated_review))
        else:
            updated_steps.append(dict(step))

    correction_by_id = _scale_corrections_by_step(corrections)
    updated_reviews: List[Dict[str, Any]] = []
    existing_review_ids = set()
    for review in composition_plan.get("spatial_fit_reviews", []) if isinstance(composition_plan.get("spatial_fit_reviews"), list) else []:
        if not isinstance(review, Mapping):
            continue
        review_id = str(review.get("id") or "").strip()
        existing_review_ids.add(review_id)
        updated_reviews.append(updated_reviews_by_id.get(review_id, dict(review)))
    for review_id, review in updated_reviews_by_id.items():
        if review_id not in existing_review_ids:
            updated_reviews.append(dict(review))

    corrected = [item for item in corrections if item.get("status") == "ready_for_scaled_dry_run"]
    already_close = [item for item in corrections if item.get("status") == "already_close"]
    blockers = [item for item in corrections if item.get("blocking")]
    if blockers and corrected:
        status = "partial_scale_corrections_need_review"
    elif blockers:
        status = "needs_regeneration_or_manual_review"
    elif corrected:
        status = "ready_for_scaled_dry_run"
    elif corrections:
        status = "no_scale_corrections_needed"
    else:
        status = "no_scale_evidence"

    updated_plan = dict(composition_plan)
    updated_plan["placement_steps"] = updated_steps
    updated_plan["all_placement_steps"] = updated_steps
    updated_plan["spatial_fit_reviews"] = updated_reviews
    updated_plan["spatial_fit_review_summary"] = _spatial_fit_review_summary(updated_reviews)
    updated_plan["asset_scale_corrections"] = corrections
    updated_plan["asset_scale_correction_summary"] = {
        "status": status,
        "correction_count": len(corrected),
        "already_close_count": len(already_close),
        "blocker_count": len(blockers),
    }
    updated_plan_json = json.dumps(updated_plan, sort_keys=True) if include_updated_plan else "<SCALE_CORRECTED_COMPOSITION_PLAN_JSON>"
    actor_labels = [
        str((_placement_step_arguments(step).get("actor_label") or step.get("id") or "")).strip()
        for step in updated_steps
        if isinstance(step, Mapping) and (_placement_step_arguments(step).get("actor_label") or step.get("id"))
    ]
    return {
        "schema": ASSET_SCALE_CORRECTION_SCHEMA,
        "status": status,
        "source_schema": composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
        "placement_step_count": len(steps),
        "reviewed_count": len(corrections),
        "correction_count": len(corrected),
        "already_close_count": len(already_close),
        "blocker_count": len(blockers),
        "blockers": blockers,
        "allow_non_uniform_scale": bool(allow_non_uniform_scale),
        "scale_policy": {
            "min_scale": min_scale,
            "max_scale": max_scale,
            "anisotropy_tolerance": anisotropy_tolerance,
            "close_scale_tolerance": close_scale_tolerance,
        },
        "corrections": corrections,
        "corrections_by_id": correction_by_id,
        "updated_placement_steps": updated_steps,
        "updated_spatial_fit_reviews": updated_reviews,
        "updated_composition_plan": updated_plan if include_updated_plan else {},
        "updated_composition_plan_json": updated_plan_json,
        "layout_preflight_handoff": {
            "tool": "spatial_preflight_interior_layout",
            "arguments": {"composition_plan_json": updated_plan_json},
            "enabled": bool(updated_steps and not blockers),
        },
        "support_surface_anchor_handoff": {
            "tool": "spatial_plan_support_surface_anchors",
            "arguments": {
                "composition_plan_json": updated_plan_json,
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
            },
            "enabled": bool(updated_steps and not blockers),
        },
        "candidate_clearance_handoff": {
            "tool": "spatial_preflight_candidate_clearance",
            "arguments": {"composition_plan_json": updated_plan_json},
            "enabled": bool(updated_steps and not blockers),
        },
        "apply_handoff": {
            "tool": "spatial_apply_composition_plan",
            "arguments": {
                "composition_plan_json": updated_plan_json,
                "dry_run": True,
                "block_on_spatial_fit_review": True,
            },
            "enabled": bool(updated_steps and not blockers),
        },
        "validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": actor_labels,
                "surface_tolerance": 15.0,
                "clearance_padding": 12.0,
                "include_evidence_handoff": True,
            },
            "enabled": bool(actor_labels and not blockers),
        },
        "tripo_regeneration_handoff": {
            "tool": "spatial_prepare_tripo_generation_batch",
            "arguments": {"composition_plan_json": "<ORIGINAL_COMPOSITION_OR_SCREENSHOT_RECONSTRUCTION_JSON>", "confirm_spend": False},
            "enabled": bool(blockers),
            "blocked_ids": [item.get("id") for item in blockers],
        },
        "workflow": [
            {"step": "review_spatial_fit_records", "reason": "Confirm planned size and imported/generated bounds are available."},
            {"step": "plan_scale_corrections", "reason": "Prefer uniform scale for generated props; require explicit opt-in for non-uniform scale."},
            {"step": "plan_support_surface_anchors", "tool": "spatial_plan_support_surface_anchors", "enabled": bool(updated_steps and not blockers)},
            {"step": "preflight_layout", "tool": "spatial_preflight_interior_layout", "enabled": bool(updated_steps and not blockers)},
            {"step": "plan_layout_preflight_corrections", "tool": "spatial_plan_layout_preflight_corrections", "enabled": bool(updated_steps and not blockers)},
            {"step": "preflight_candidate_clearance", "tool": "spatial_preflight_candidate_clearance", "enabled": bool(updated_steps and not blockers)},
            {"step": "dry_run_scaled_apply", "tool": "spatial_apply_composition_plan", "enabled": bool(updated_steps and not blockers)},
            {"step": "validate_scaled_placement", "tool": "spatial_validate_placement", "enabled": bool(actor_labels and not blockers)},
            {"step": "regenerate_or_replace_blocked_assets", "tools": ["spatial_prepare_tripo_generation_batch", "spatial_resolve_project_assets"], "enabled": bool(blockers)},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This scale planner is Ghost-owned dimensional arithmetic over Ghost spatial-fit review records.",
                "It does not copy Epic native MCP or SceneTools source and does not mutate Unreal or submit paid Tripo jobs.",
            ],
        },
    }


def _plan_composition_asset_binding(
    *,
    composition_plan: Mapping[str, Any],
    import_results_json: str,
    asset_overrides_json: str,
    include_unresolved_steps: bool,
    surface_tolerance: float,
    clearance_padding: float,
) -> Dict[str, Any]:
    import_records = _normalize_import_result_records(import_results_json)
    override_records = _asset_override_records_from_json(asset_overrides_json)
    record_lookup = _records_by_binding_key([*override_records, *import_records])
    props_by_id = _props_by_id(composition_plan)
    generation_by_id = _generation_tasks_by_id(composition_plan)
    placement_steps = composition_plan.get("placement_steps") if isinstance(composition_plan.get("placement_steps"), list) else []

    asset_bindings: List[Dict[str, Any]] = []
    bound_steps: List[Dict[str, Any]] = []
    unresolved_steps: List[Dict[str, Any]] = []
    generation_follow_up: List[Dict[str, Any]] = []
    bound_props: List[Dict[str, Any]] = []
    spatial_fit_reviews: List[Dict[str, Any]] = []

    for step in placement_steps:
        if not isinstance(step, Mapping):
            continue
        step_id = str(step.get("id") or "").strip()
        prop = props_by_id.get(step_id, {})
        binding = _asset_binding_for_step(step=step, prop=prop, record_lookup=record_lookup)
        generation_task = generation_by_id.get(step_id, {})
        review = _spatial_fit_review_for_binding(
            step=step,
            prop=prop,
            binding=binding,
            generation_task=generation_task,
            surface_tolerance=surface_tolerance,
            clearance_padding=clearance_padding,
        )
        if review:
            binding["spatial_fit_review"] = review
            spatial_fit_reviews.append(review)
        asset_bindings.append(binding)
        if prop:
            bound_prop = dict(prop)
            bound_prop["asset_binding"] = {
                "status": binding["status"],
                "asset_path": binding.get("asset_path", ""),
                "source": binding.get("source", ""),
            }
            if review:
                bound_prop["spatial_fit_review"] = review
            bound_props.append(bound_prop)

        arguments = _placement_step_arguments(step)
        if binding["status"] == "resolved":
            bound_arguments = dict(arguments)
            bound_arguments.update({
                "asset_path": binding["asset_path"],
                "dry_run": True,
                "allow_mutation": False,
                "asset_binding_source": binding.get("source", ""),
                "asset_binding_matched_by": binding.get("matched_by", ""),
            })
            bound_step = dict(step)
            bound_step["tool"] = "spatial_add_asset_to_scene"
            bound_step["arguments"] = bound_arguments
            bound_step["asset_binding"] = binding
            if review:
                bound_step["spatial_fit_review"] = review
            bound_steps.append(bound_step)
        else:
            unresolved_step = dict(step)
            unresolved_step["asset_binding"] = binding
            if review:
                unresolved_step["spatial_fit_review"] = review
            unresolved_steps.append(unresolved_step)
            if generation_task:
                generation_follow_up.append({
                    "id": step_id,
                    "prop_name": generation_task.get("prop_name", step_id),
                    "submit": generation_task.get("submit", {}),
                    "wait": generation_task.get("wait", {}),
                    "import": generation_task.get("import", {}),
                    "reference_image_variant": generation_task.get("reference_image_variant", {}),
                    "reason": "Asset is still unresolved; complete the guarded Tripo generation/import flow before placement.",
                })

    resolved_actor_labels = [
        str(step.get("arguments", {}).get("actor_label") or "")
        for step in bound_steps
        if isinstance(step.get("arguments"), Mapping) and step.get("arguments", {}).get("actor_label")
    ]
    all_steps = [*bound_steps, *unresolved_steps] if include_unresolved_steps else list(bound_steps)
    return {
        "schema": COMPOSITION_ASSET_BINDING_SCHEMA,
        "status": "ready_for_dry_run_placement" if not unresolved_steps else "waiting_for_generated_assets",
        "resolved_count": len(bound_steps),
        "unresolved_count": len(unresolved_steps),
        "import_result_count": len(import_records),
        "override_count": len(override_records),
        "asset_bindings": asset_bindings,
        "bound_props": bound_props,
        "spatial_fit_reviews": spatial_fit_reviews,
        "spatial_fit_review_count": len(spatial_fit_reviews),
        "spatial_fit_review_summary": _spatial_fit_review_summary(spatial_fit_reviews),
        "placement_steps": bound_steps,
        "all_placement_steps": all_steps,
        "unresolved_steps": unresolved_steps,
        "generation_follow_up": generation_follow_up,
        "workflow": [
            {"step": "review_import_results", "reason": "Confirm each imported asset path is a real /Game asset and represents the intended prop."},
            {"step": "review_spatial_fit", "reviews": spatial_fit_reviews, "reason": "Compare imported/generated asset bounds against planned spatial-fit size, surface contact, and clearance expectations before mutation."},
            {"step": "plan_asset_scale_corrections", "tool": "spatial_plan_asset_scale_corrections", "enabled": bool(spatial_fit_reviews), "reason": "Scale generated imports to planned room dimensions before layout preflight or mutation."},
            {"step": "plan_support_surface_anchors", "tool": "spatial_plan_support_surface_anchors", "enabled": bool(all_steps), "reason": "Snap floor/counter/table/shelf/wall props to classified room surfaces before layout preflight."},
            {"step": "preflight_layout", "tool": "spatial_preflight_interior_layout", "enabled": bool(all_steps), "reason": "Check approximate room bounds, footprint overlaps, and circulation before placement."},
            {"step": "plan_layout_preflight_corrections", "tool": "spatial_plan_layout_preflight_corrections", "enabled": bool(all_steps), "reason": "Repair fixable preflight issues in a dry-run composition before mutation."},
            {"step": "finish_unresolved_generation", "tools": ["gen_tripo_text_to_model", "gen_tripo_image_to_model", "gen_tripo_wait_for_task", "gen_tripo_import_to_project"], "enabled": bool(unresolved_steps), "generation_follow_up": generation_follow_up},
            {"step": "place_resolved_assets", "tool": "spatial_apply_composition_plan", "placement_steps": bound_steps, "reason": "Run dry-run composition placement first; mutation requires explicit allow_mutation."},
            {"step": "validate_bound_composition", "tool": "spatial_validate_placement", "arguments": {"actors": resolved_actor_labels, "surface_tolerance": surface_tolerance, "clearance_padding": clearance_padding, "include_evidence_handoff": True}},
            {"step": "iterate_after_validation", "tool": "spatial_plan_composition_iteration", "arguments": {"composition_plan_json": "<THIS_ASSET_BINDING_OUTPUT_OR_ORIGINAL_COMPOSITION_PLAN>", "validation_result_json": "<SPATIAL_VALIDATE_PLACEMENT_RESULT_JSON>"}},
        ],
        "scale_correction_handoff": {
            "tool": "spatial_plan_asset_scale_corrections",
            "arguments": {
                "composition_plan_json": "<THIS_ASSET_BINDING_OUTPUT_JSON>",
                "allow_non_uniform_scale": False,
            },
            "enabled": bool(spatial_fit_reviews),
        },
        "support_surface_anchor_handoff": {
            "tool": "spatial_plan_support_surface_anchors",
            "arguments": {
                "composition_plan_json": "<THIS_ASSET_BINDING_OR_SCALE_CORRECTED_OUTPUT_JSON>",
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
            },
            "enabled": bool(all_steps),
        },
        "validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": resolved_actor_labels,
                "surface_tolerance": surface_tolerance,
                "clearance_padding": clearance_padding,
                "include_evidence_handoff": True,
            },
            "enabled": bool(resolved_actor_labels),
        },
        "iteration_handoff": {
            "tool": "spatial_plan_composition_iteration",
            "arguments": {
                "composition_plan_json": "<ORIGINAL_OR_BOUND_COMPOSITION_PLAN_JSON>",
                "validation_result_json": "<NEW_SPATIAL_VALIDATE_PLACEMENT_RESULT_JSON>",
            },
        },
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This binding plan uses Ghost composition/import result schemas and does not copy Epic SceneTools source.",
                "Generated assets still require user spend approval and review before paid Tripo submission.",
            ],
        },
    }


def _spatial_generation_source_from_json(value: str) -> tuple[Dict[str, Any], Dict[str, Any]]:
    parsed = _json_object_from_text(value, "composition_plan_json")
    if not parsed:
        return {}, {}
    outputs = parsed.get("outputs") if parsed.get("schema") == SPATIAL_RESULT_SCHEMA else parsed
    if not isinstance(outputs, Mapping):
        raise ValueError("composition_plan_json.outputs must be an object")
    outputs_dict = dict(outputs)
    schema = outputs_dict.get("schema")
    if schema == SCREENSHOT_RECONSTRUCTION_SCHEMA:
        plan = outputs_dict.get("composition_plan")
        if not isinstance(plan, Mapping):
            raise ValueError("composition_plan_json screenshot reconstruction output must include composition_plan")
        return outputs_dict, dict(plan)
    if schema == COMPOSITION_ASSET_BINDING_SCHEMA:
        return outputs_dict, {
            "schema": COMPOSITION_ASSET_BINDING_SCHEMA,
            "room": outputs_dict.get("room", {}),
            "zones": outputs_dict.get("zones", []),
            "props": outputs_dict.get("bound_props", []),
            "generation_tasks": outputs_dict.get("generation_follow_up", []),
            "placement_steps": outputs_dict.get("all_placement_steps") or outputs_dict.get("placement_steps", []),
            "asset_bindings": outputs_dict.get("asset_bindings", []),
            "spatial_fit_reviews": outputs_dict.get("spatial_fit_reviews", []),
            "spatial_fit_review_summary": outputs_dict.get("spatial_fit_review_summary", {}),
        }
    if schema not in (None, INTERIOR_COMPOSITION_SCHEMA):
        raise ValueError(
            "composition_plan_json must have schema "
            f"{INTERIOR_COMPOSITION_SCHEMA}, {SCREENSHOT_RECONSTRUCTION_SCHEMA}, or {COMPOSITION_ASSET_BINDING_SCHEMA}"
        )
    return outputs_dict, outputs_dict


def _asset_text_tokens(*values: Any) -> List[str]:
    tokens: List[str] = []
    seen = set()

    def collect(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, Mapping):
            for nested in value.values():
                collect(nested)
            return
        if isinstance(value, (list, tuple, set)):
            for nested in value:
                collect(nested)
            return
        text = str(value).replace("\\", "/").lower()
        normalized = "".join(ch if ch.isalnum() else " " for ch in text)
        for raw in normalized.split():
            token = raw.strip()
            if len(token) <= 1 or token in {"sm", "bp", "mi", "t", "sk", "static", "mesh", "asset", "game", "props", "prop"}:
                continue
            if token.endswith("s") and len(token) > 3:
                singular = token[:-1]
                if singular not in seen:
                    tokens.append(singular)
                    seen.add(singular)
            if token not in seen:
                tokens.append(token)
                seen.add(token)

    for value in values:
        collect(value)
    return tokens


def _asset_catalog_item_from_value(value: Any, index: int) -> Dict[str, Any]:
    if isinstance(value, str):
        asset_path = _clean_asset_path(value)
        return {
            "asset_path": asset_path,
            "asset_name": _asset_name_from_path(asset_path),
            "class_name": "",
            "folder": asset_path.rsplit("/", 1)[0],
            "tags": [],
            "description": "",
            "approx_size_cm": [],
            "source_index": index,
        }
    if not isinstance(value, Mapping):
        raise ValueError(f"asset_catalog_json[{index}] must be a /Game path string or object")
    item = dict(value)
    raw_path = str(
        item.get("asset_path")
        or item.get("path")
        or item.get("object_path")
        or item.get("package_name")
        or item.get("package_path")
        or ""
    ).strip()
    if item.get("package_name") and item.get("asset_name") and "." not in raw_path:
        raw_path = f"{raw_path}.{item.get('asset_name')}"
    asset_path = _clean_asset_path(raw_path)
    asset_name = str(item.get("asset_name") or item.get("name") or _asset_name_from_path(asset_path)).strip()
    tags_value = item.get("tags") or item.get("keywords") or item.get("metadata") or []
    if isinstance(tags_value, Mapping):
        tags = [str(key) for key in tags_value.keys()]
        tags.extend(str(value) for value in tags_value.values())
    elif isinstance(tags_value, str):
        tags = [tags_value]
    else:
        try:
            tags = [str(tag) for tag in tags_value]
        except TypeError:
            tags = []
    class_name = str(item.get("class_name") or item.get("asset_class") or item.get("class") or "").strip()
    folder = str(item.get("folder") or asset_path.rsplit("/", 1)[0]).strip()
    description = str(item.get("description") or item.get("display_name") or "").strip()
    approx_size = []
    if item.get("approx_size_cm") not in (None, "", []):
        approx_size = _vector3(item.get("approx_size_cm"), f"asset_catalog_json[{index}].approx_size_cm") or []
    elif isinstance(item.get("bounds"), Mapping):
        bounds = item.get("bounds") or {}
        if bounds.get("size") not in (None, "", []):
            approx_size = _vector3(bounds.get("size"), f"asset_catalog_json[{index}].bounds.size") or []
    return {
        "asset_path": asset_path,
        "asset_name": asset_name or _asset_name_from_path(asset_path),
        "class_name": class_name,
        "folder": folder,
        "tags": tags,
        "description": description,
        "approx_size_cm": approx_size,
        "source_index": index,
    }


def _asset_catalog_from_json(
    value: str,
    *,
    candidate_asset_paths: Sequence[str],
    maximum: int,
) -> List[Dict[str, Any]]:
    raw_items: List[Any] = []
    raw_items.extend(_string_list(candidate_asset_paths, "candidate_asset_paths", maximum=maximum))
    parsed = _json_value_from_text(value, "asset_catalog_json")
    if parsed is not None:
        if isinstance(parsed, Mapping) and parsed.get("schema") == SPATIAL_RESULT_SCHEMA:
            parsed = parsed.get("outputs", {})
        if isinstance(parsed, Mapping):
            for key in ("assets", "asset_catalog", "candidates", "selected_assets", "paths"):
                if isinstance(parsed.get(key), list):
                    raw_items.extend(parsed[key])
                    break
            else:
                if all(isinstance(item, str) for item in parsed.values()):
                    raw_items.extend(parsed.values())
                else:
                    raise ValueError("asset_catalog_json object must include an assets, asset_catalog, candidates, selected_assets, or paths list")
        elif isinstance(parsed, list):
            raw_items.extend(parsed)
        else:
            raise ValueError("asset_catalog_json must decode to a list or object")
    if not raw_items:
        raise ValueError("asset_catalog_json or candidate_asset_paths is required")

    records: List[Dict[str, Any]] = []
    seen = set()
    for index, item in enumerate(raw_items[:maximum]):
        record = _asset_catalog_item_from_value(item, index)
        key = record["asset_path"].lower()
        if key in seen:
            continue
        record["tokens"] = _asset_text_tokens(
            record.get("asset_path"),
            record.get("asset_name"),
            record.get("class_name"),
            record.get("folder"),
            record.get("tags"),
            record.get("description"),
        )
        records.append(record)
        seen.add(key)
    return records


GENERIC_ASSET_MATCH_TOKENS = frozenset({
    "apartment",
    "bathroom",
    "bedroom",
    "entry",
    "floor",
    "generic",
    "hall",
    "hallway",
    "interior",
    "kitchen",
    "living",
    "room",
    "sleeping",
    "studio",
    "utility",
    "wall",
})


def _meaningful_asset_tokens(tokens: Sequence[str]) -> List[str]:
    return [token for token in tokens if token not in GENERIC_ASSET_MATCH_TOKENS]


def _prop_asset_match_terms(prop: Mapping[str, Any]) -> Dict[str, Any]:
    aliases = [str(alias) for alias in prop.get("aliases", []) if str(alias or "").strip()]
    name = str(prop.get("name") or prop.get("id") or "").strip()
    identity_terms = _merge_unique(
        [name, str(prop.get("id") or ""), str(prop.get("detected_item_id") or "")],
        aliases,
    )
    name_tokens = _meaningful_asset_tokens(_asset_text_tokens(name, aliases))
    return {
        "name": name,
        "aliases": aliases,
        "terms": identity_terms,
        "name_tokens": name_tokens,
        "context_tokens": _asset_text_tokens(prop.get("category"), prop.get("zone"), prop.get("surface")),
    }


def _size_vector(value: Any) -> List[float]:
    if value in (None, "", []):
        return []
    try:
        raw = [float(component) for component in list(value)[:3]]
    except Exception:
        return []
    if len(raw) != 3 or any(component <= 0.0 for component in raw):
        return []
    return raw


def _asset_size_vector(asset: Mapping[str, Any]) -> List[float]:
    size = _size_vector(asset.get("approx_size_cm"))
    if size:
        return size
    bounds = asset.get("bounds") if isinstance(asset.get("bounds"), Mapping) else {}
    return _size_vector(bounds.get("size"))


def _size_match_score(prop: Mapping[str, Any], asset: Mapping[str, Any]) -> Dict[str, Any]:
    prop_size = _size_vector(prop.get("approx_size_cm") or prop.get("size"))
    asset_size = _asset_size_vector(asset)
    if not prop_size or not asset_size:
        return {"score": 0, "reason": ""}
    prop_dims = sorted(prop_size)
    asset_dims = sorted(asset_size)
    ratios = [
        max(asset_dim / prop_dim, prop_dim / asset_dim)
        for prop_dim, asset_dim in zip(prop_dims, asset_dims)
        if prop_dim > 0.0 and asset_dim > 0.0
    ]
    if len(ratios) != 3:
        return {"score": 0, "reason": ""}
    worst_ratio = max(ratios)
    if worst_ratio <= 1.35:
        return {"score": 35, "reason": "size_close_match"}
    if worst_ratio <= 2.0:
        return {"score": 18, "reason": "size_plausible_match"}
    if worst_ratio <= 3.5:
        return {"score": -10, "reason": "size_loose_mismatch"}
    return {"score": -45, "reason": "size_strong_mismatch"}


def _asset_match_score(prop: Mapping[str, Any], asset: Mapping[str, Any]) -> Dict[str, Any]:
    terms = _prop_asset_match_terms(prop)
    asset_tokens = set(asset.get("tokens", []))
    asset_name_tokens = set(_asset_text_tokens(asset.get("asset_name")))
    asset_path = str(asset.get("asset_path") or "")
    asset_name_normalized = "".join(_asset_text_tokens(asset.get("asset_name"), asset_path))
    score = 0
    reasons: List[str] = []

    existing = str(prop.get("matched_asset_path") or prop.get("existing_asset_path") or "").strip()
    if existing and existing.lower() == asset_path.lower():
        score += 140
        reasons.append("already_planned_asset_path")

    for term in terms["terms"]:
        term_tokens = set(_asset_text_tokens(term))
        if not term_tokens:
            continue
        term_normalized = "".join(term_tokens)
        if term_normalized and term_normalized == asset_name_normalized:
            score += 110
            reasons.append(f"asset_name_exact:{term}")
        elif term_normalized and term_normalized in asset_name_normalized:
            score += 80
            reasons.append(f"asset_name_contains:{term}")
        elif term_tokens and term_tokens.issubset(asset_tokens):
            score += 65
            reasons.append(f"token_subset:{term}")

    name_overlap = set(terms["name_tokens"]).intersection(asset_tokens)
    if name_overlap:
        score += 18 * len(name_overlap)
        reasons.append("name_token_overlap:" + ",".join(sorted(name_overlap)))
    context_overlap = set(terms["context_tokens"]).intersection(asset_tokens)
    if context_overlap:
        score += 6 * len(context_overlap)
        reasons.append("context_overlap:" + ",".join(sorted(context_overlap)))

    class_text = f"{asset.get('class_name', '')} {asset_path}".lower()
    if any(token in class_text for token in ("staticmesh", "static_mesh", "/sm_", ".sm_", " sm_")):
        score += 12
        reasons.append("static_mesh_candidate")
    if "blueprint" in class_text or "/bp_" in class_text or ".bp_" in class_text:
        score += 6
        reasons.append("blueprint_candidate")
    if any(token in class_text for token in ("material", "texture", "sound", "animation")):
        score -= 35
        reasons.append("non_prop_asset_penalty")

    size_score = _size_match_score(prop, asset)
    if size_score["score"]:
        score += int(size_score["score"])
        reasons.append(str(size_score["reason"]))

    identity_match = any(
        reason == "already_planned_asset_path"
        or reason.startswith("asset_name_exact:")
        or reason.startswith("asset_name_contains:")
        or reason.startswith("token_subset:")
        or reason.startswith("name_token_overlap:")
        for reason in reasons
    )
    if not identity_match:
        score = min(score, 30)
        if score > 0:
            reasons.append("no_identity_match_cap")

    return {
        "score": max(0, score),
        "reasons": _merge_unique(reasons),
    }


def _resolve_assets_for_composition(
    *,
    composition_plan: Mapping[str, Any],
    asset_catalog: Sequence[Mapping[str, Any]],
    minimum_score: float,
    max_candidates_per_prop: int,
    include_resolved_existing: bool,
    tripo_source_json: str,
) -> Dict[str, Any]:
    props = list(composition_plan.get("props", [])) if isinstance(composition_plan.get("props"), list) else []
    if not props:
        props = [
            {"id": step.get("id"), "name": step.get("id"), "source": "placement_step"}
            for step in composition_plan.get("placement_steps", [])
            if isinstance(step, Mapping) and step.get("id")
        ]

    matches: List[Dict[str, Any]] = []
    overrides: Dict[str, str] = {}
    override_records: Dict[str, Dict[str, Any]] = {}
    resolved_count = 0
    skipped_count = 0

    for prop in props:
        if not isinstance(prop, Mapping):
            continue
        prop_id = _safe_asset_stem(str(prop.get("id") or prop.get("detected_item_id") or prop.get("name")), "Prop")
        existing = str(prop.get("matched_asset_path") or prop.get("existing_asset_path") or "").strip()
        if existing and not include_resolved_existing:
            skipped_count += 1
            matches.append({
                "id": prop_id,
                "prop_name": prop.get("name") or prop_id,
                "resolved": True,
                "selected_asset_path": existing,
                "selected_score": 999,
                "source": "already_resolved",
                "candidates": [],
            })
            continue
        scored: List[Dict[str, Any]] = []
        for asset in asset_catalog:
            score_info = _asset_match_score(prop, asset)
            score = float(score_info["score"])
            if score <= 0:
                continue
            scored.append({
                "asset_path": asset.get("asset_path"),
                "asset_name": asset.get("asset_name"),
                "class_name": asset.get("class_name", ""),
                "approx_size_cm": _asset_size_vector(asset),
                "score": score,
                "reasons": score_info["reasons"],
            })
        scored.sort(key=lambda item: (-float(item["score"]), str(item["asset_path"])))
        top = scored[:max_candidates_per_prop]
        selected = top[0] if top and float(top[0]["score"]) >= minimum_score else {}
        if selected:
            overrides[prop_id] = str(selected["asset_path"])
            override_record = {"asset_path": str(selected["asset_path"])}
            if selected.get("approx_size_cm"):
                override_record["approx_size_cm"] = selected.get("approx_size_cm")
            override_records[prop_id] = override_record
            resolved_count += 1
        matches.append({
            "id": prop_id,
            "prop_name": prop.get("name") or prop_id,
            "source_before": prop.get("source", ""),
            "resolved": bool(selected),
            "selected_asset_path": selected.get("asset_path", ""),
            "selected_score": selected.get("score", 0),
            "candidates": top,
            "unresolved_reason": "" if selected else "no_candidate_above_minimum_score",
        })

    unresolved = [match for match in matches if not match.get("resolved")]
    overrides_json = json.dumps(override_records or overrides, sort_keys=True)
    composition_json = json.dumps(dict(composition_plan), sort_keys=True)
    generation_source_json = (
        "<SPATIAL_BIND_GENERATED_ASSETS_OUTPUT_JSON>"
        if overrides
        else (str(tripo_source_json or "").strip() or composition_json)
    )
    status = "ready_for_binding" if overrides else ("already_resolved" if not unresolved else "needs_generation_for_unresolved")
    return {
        "schema": PROJECT_ASSET_RESOLUTION_SCHEMA,
        "status": status,
        "prop_count": len(matches),
        "resolved_count": resolved_count,
        "unresolved_count": len(unresolved),
        "skipped_existing_count": skipped_count,
        "asset_catalog_count": len(asset_catalog),
        "minimum_score": minimum_score,
        "max_candidates_per_prop": max_candidates_per_prop,
        "matches": matches,
        "unresolved_props": [
            {"id": match["id"], "prop_name": match["prop_name"], "reason": match.get("unresolved_reason", "")}
            for match in unresolved
        ],
        "asset_overrides": overrides,
        "asset_overrides_json": overrides_json,
        "binding_handoff": {
            "tool": "spatial_bind_generated_assets_to_composition",
            "arguments": {
                "composition_plan_json": composition_json,
                "asset_overrides_json": overrides_json,
                "include_unresolved_steps": True,
            },
            "enabled": bool(overrides),
        },
        "tripo_batch_handoff": {
            "tool": "spatial_prepare_tripo_generation_batch",
            "arguments": {
                "composition_plan_json": generation_source_json,
                "prefer_image_crops": True,
                "confirm_spend": False,
            },
            "enabled": bool(unresolved),
        },
        "workflow": [
            {"step": "review_project_asset_matches", "reason": "Confirm the selected project assets visually match the intended props before binding."},
            {"step": "bind_existing_project_assets", "tool": "spatial_bind_generated_assets_to_composition", "enabled": bool(overrides)},
            {"step": "prepare_tripo_for_unresolved", "tool": "spatial_prepare_tripo_generation_batch", "enabled": bool(unresolved), "reason": "Only unresolved props should proceed to guarded Tripo generation."},
            {"step": "place_validate_iterate", "tools": ["spatial_preflight_interior_layout", "spatial_plan_layout_preflight_corrections", "spatial_apply_composition_plan", "spatial_validate_placement", "spatial_plan_composition_iteration"]},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is Ghost-owned lexical asset matching over provided project catalog metadata.",
                "It does not inspect or copy Epic native MCP SceneTools source and does not submit paid generation jobs.",
            ],
        },
    }


def _asset_resolution_selected_assets(asset_resolution: Mapping[str, Any]) -> Dict[str, str]:
    selected: Dict[str, str] = {}
    overrides = asset_resolution.get("asset_overrides") if isinstance(asset_resolution.get("asset_overrides"), Mapping) else {}
    for prop_id, asset_path in overrides.items():
        clean_id = str(prop_id or "").strip()
        clean_path = str(asset_path or "").strip()
        if clean_id and clean_path:
            selected[clean_id] = clean_path
    for match in asset_resolution.get("matches", []) if isinstance(asset_resolution.get("matches"), list) else []:
        if not isinstance(match, Mapping) or not match.get("resolved"):
            continue
        clean_id = str(match.get("id") or "").strip()
        clean_path = str(match.get("selected_asset_path") or "").strip()
        if clean_id and clean_path and clean_id not in selected:
            selected[clean_id] = clean_path
    return selected


def _asset_resolution_unresolved_ids(asset_resolution: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    seen = set()
    for item in asset_resolution.get("unresolved_props", []) if isinstance(asset_resolution.get("unresolved_props"), list) else []:
        if not isinstance(item, Mapping):
            continue
        prop_id = str(item.get("id") or "").strip()
        if prop_id and prop_id not in seen:
            ids.append(prop_id)
            seen.add(prop_id)
    if ids:
        return ids
    for match in asset_resolution.get("matches", []) if isinstance(asset_resolution.get("matches"), list) else []:
        if not isinstance(match, Mapping) or match.get("resolved"):
            continue
        prop_id = str(match.get("id") or "").strip()
        if prop_id and prop_id not in seen:
            ids.append(prop_id)
            seen.add(prop_id)
    return ids


def _composition_after_project_asset_resolution(
    *,
    composition_plan: Mapping[str, Any],
    source_outputs: Mapping[str, Any],
    asset_resolution: Mapping[str, Any],
) -> Dict[str, Any]:
    selected_assets = _asset_resolution_selected_assets(asset_resolution)
    unresolved_ids = _asset_resolution_unresolved_ids(asset_resolution)
    unresolved = set(unresolved_ids)
    resolved = set(selected_assets)

    updated_composition = dict(composition_plan)
    updated_props: List[Dict[str, Any]] = []
    for prop in composition_plan.get("props", []) if isinstance(composition_plan.get("props"), list) else []:
        if not isinstance(prop, Mapping):
            continue
        prop_id = _safe_asset_stem(str(prop.get("id") or prop.get("detected_item_id") or prop.get("name")), "Prop")
        updated = dict(prop)
        if prop_id in selected_assets:
            updated["source"] = "existing_asset"
            updated["matched_asset_path"] = selected_assets[prop_id]
            updated["asset_resolution_source"] = "project_asset_catalog"
        elif unresolved and prop_id in unresolved:
            updated["source"] = str(updated.get("source") or "tripo_candidate")
        updated_props.append(updated)
    if updated_props:
        updated_composition["props"] = updated_props

    updated_steps: List[Dict[str, Any]] = []
    for step in composition_plan.get("placement_steps", []) if isinstance(composition_plan.get("placement_steps"), list) else []:
        if not isinstance(step, Mapping):
            continue
        step_id = str(step.get("id") or "").strip()
        updated = dict(step)
        arguments = _placement_step_arguments(updated)
        if step_id in selected_assets:
            arguments["asset_path"] = selected_assets[step_id]
            arguments["asset_binding_source"] = "project_asset_resolution"
            arguments["dry_run"] = True
            arguments["allow_mutation"] = False
            arguments["placement_source"] = _append_placement_source(arguments.get("placement_source", ""), "project_asset_resolution")
            updated["tool"] = "spatial_add_asset_to_scene"
            updated["arguments"] = arguments
        updated_steps.append(updated)
    if updated_steps:
        updated_composition["placement_steps"] = updated_steps
        if isinstance(composition_plan.get("all_placement_steps"), list):
            updated_composition["all_placement_steps"] = updated_steps

    filtered_generation_tasks: List[Dict[str, Any]] = []
    for task in composition_plan.get("generation_tasks", []) if isinstance(composition_plan.get("generation_tasks"), list) else []:
        if not isinstance(task, Mapping):
            continue
        task_id = str(task.get("id") or "").strip()
        if task_id in unresolved:
            filtered_generation_tasks.append(dict(task))
    updated_composition["generation_tasks"] = filtered_generation_tasks
    updated_composition["project_asset_resolution"] = {
        "applied": True,
        "resolved_ids": sorted(resolved),
        "unresolved_ids": list(unresolved_ids),
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved_ids),
    }

    updated_source = dict(source_outputs or updated_composition)
    if updated_source.get("schema") == SCREENSHOT_RECONSTRUCTION_SCHEMA:
        updated_source["composition_plan"] = updated_composition
        if isinstance(updated_source.get("crop_tasks"), list):
            updated_source["crop_tasks"] = [
                dict(task)
                for task in updated_source.get("crop_tasks", [])
                if isinstance(task, Mapping) and str(task.get("id") or "").strip() in unresolved
            ]
        if isinstance(updated_source.get("asset_mapping"), list):
            mapping: List[Dict[str, Any]] = []
            for item in updated_source.get("asset_mapping", []):
                if not isinstance(item, Mapping):
                    continue
                item_id = str(item.get("id") or "").strip()
                updated = dict(item)
                if item_id in selected_assets:
                    updated["action"] = "existing_asset"
                    updated["source"] = selected_assets[item_id]
                    updated["matched_asset_path"] = selected_assets[item_id]
                    updated["handoff"] = {}
                    updated["asset_resolution_source"] = "project_asset_catalog"
                elif item_id in unresolved:
                    updated["asset_resolution_source"] = "unresolved_after_project_asset_catalog"
                mapping.append(updated)
            updated_source["asset_mapping"] = mapping
    else:
        updated_source = dict(updated_composition)
    updated_source["project_asset_resolution"] = updated_composition["project_asset_resolution"]

    return {
        "schema": "unreal_mcp_ghost.spatial_post_asset_resolution_generation_source.v1",
        "resolved_ids": sorted(resolved),
        "unresolved_ids": list(unresolved_ids),
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved_ids),
        "composition_plan": updated_composition,
        "source_outputs": updated_source,
        "composition_plan_json": json.dumps(updated_composition, sort_keys=True),
        "source_outputs_json": json.dumps(updated_source, sort_keys=True),
        "tripo_batch_handoff": {
            "tool": "spatial_prepare_tripo_generation_batch",
            "arguments": {
                "composition_plan_json": json.dumps(updated_source, sort_keys=True),
                "prefer_image_crops": bool(updated_source.get("schema") == SCREENSHOT_RECONSTRUCTION_SCHEMA),
                "confirm_spend": False,
            },
            "enabled": bool(unresolved_ids),
        },
    }


def _generation_content_path(
    *,
    composition_plan: Mapping[str, Any],
    content_path: str,
) -> str:
    if str(content_path or "").strip():
        return _normalize_content_path(content_path)
    for task in composition_plan.get("generation_tasks", []) if isinstance(composition_plan.get("generation_tasks"), list) else []:
        if not isinstance(task, Mapping):
            continue
        import_handoff = task.get("import") if isinstance(task.get("import"), Mapping) else {}
        arguments = import_handoff.get("arguments") if isinstance(import_handoff.get("arguments"), Mapping) else {}
        candidate = str(arguments.get("content_path") or "").strip()
        if candidate:
            return _normalize_content_path(candidate)
    return "/Game/Generated/SpatialInteriors"


def _handoff_with_arguments(handoff: Mapping[str, Any], *, confirm_spend: Optional[bool] = None) -> Dict[str, Any]:
    tool = str(handoff.get("tool") or "").strip()
    arguments = dict(handoff.get("arguments") or {}) if isinstance(handoff.get("arguments"), Mapping) else {}
    if confirm_spend is not None:
        arguments["confirm_spend"] = bool(confirm_spend)
    return {"tool": tool, "arguments": arguments}


def _import_handoff_for_generation(
    *,
    prop_id: str,
    generation_task: Mapping[str, Any],
    content_path: str,
) -> Dict[str, Any]:
    handoff = generation_task.get("import") if isinstance(generation_task.get("import"), Mapping) else {}
    arguments = dict(handoff.get("arguments") or {}) if isinstance(handoff.get("arguments"), Mapping) else {}
    arguments["task_id"] = str(arguments.get("task_id") or f"<TRIPO_TASK_ID_FOR_{prop_id}>")
    arguments["content_path"] = _normalize_content_path(content_path)
    arguments["asset_name"] = str(arguments.get("asset_name") or prop_id)
    arguments.setdefault("create_material_instance", True)
    arguments.setdefault("capture_thumbnail", True)
    return {"tool": str(handoff.get("tool") or "gen_tripo_import_to_project"), "arguments": arguments}


def _wait_handoff_for_generation(prop_id: str, generation_task: Mapping[str, Any]) -> Dict[str, Any]:
    handoff = generation_task.get("wait") if isinstance(generation_task.get("wait"), Mapping) else {}
    arguments = dict(handoff.get("arguments") or {}) if isinstance(handoff.get("arguments"), Mapping) else {}
    arguments["task_id"] = str(arguments.get("task_id") or f"<TRIPO_TASK_ID_FOR_{prop_id}>")
    return {"tool": str(handoff.get("tool") or "gen_tripo_wait_for_task"), "arguments": arguments}


def _placement_steps_by_id(composition_plan: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    steps: Dict[str, Dict[str, Any]] = {}
    for step in composition_plan.get("placement_steps", []) if isinstance(composition_plan.get("placement_steps"), list) else []:
        if not isinstance(step, Mapping):
            continue
        step_id = str(step.get("id") or "").strip()
        if step_id:
            steps[step_id] = dict(step)
    return steps


def _crop_tasks_by_id(source_outputs: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    tasks: Dict[str, Dict[str, Any]] = {}
    for task in source_outputs.get("crop_tasks", []) if isinstance(source_outputs.get("crop_tasks"), list) else []:
        if not isinstance(task, Mapping):
            continue
        task_id = str(task.get("id") or "").strip()
        if task_id:
            tasks[task_id] = dict(task)
    return tasks


def _ordered_generation_ids(
    *,
    composition_plan: Mapping[str, Any],
    generation_by_id: Mapping[str, Mapping[str, Any]],
    crop_by_id: Mapping[str, Mapping[str, Any]],
    limit: int,
) -> List[str]:
    ids: List[str] = []
    seen = set()
    for step in composition_plan.get("placement_steps", []) if isinstance(composition_plan.get("placement_steps"), list) else []:
        step_id = str(step.get("id") or "").strip() if isinstance(step, Mapping) else ""
        if step_id and step_id not in seen and (step_id in generation_by_id or step_id in crop_by_id):
            ids.append(step_id)
            seen.add(step_id)
    for source in (crop_by_id, generation_by_id):
        for item_id in source:
            if item_id and item_id not in seen:
                ids.append(item_id)
                seen.add(item_id)
            if len(ids) >= limit:
                return ids
    return ids[:limit]


def _planned_step_after_import(step: Mapping[str, Any], *, prop_id: str) -> Dict[str, Any]:
    if not step:
        return {}
    planned = dict(step)
    arguments = _placement_step_arguments(planned)
    arguments["asset_path"] = str(arguments.get("asset_path") or f"<IMPORTED_ASSET_PATH_FOR_{prop_id}>")
    arguments["dry_run"] = True
    arguments["allow_mutation"] = False
    planned["tool"] = "spatial_add_asset_to_scene"
    planned["arguments"] = arguments
    return planned


def _tripo_job_guarded_pipeline(job: Mapping[str, Any], *, confirm_spend: bool) -> List[Dict[str, Any]]:
    submit = job.get("submit") if isinstance(job.get("submit"), Mapping) else {}
    submit_args = submit.get("arguments") if isinstance(submit.get("arguments"), Mapping) else {}
    prompt_preview = str(submit_args.get("prompt") or submit_args.get("image_path") or submit_args.get("image_url") or "").strip()
    ready_for_submission = bool(job.get("ready_for_submission"))
    spend_confirmed = bool(confirm_spend)
    actor_label = str(job.get("actor_label") or "")
    prop_id = str(job.get("id") or "generated_prop")
    crop_readiness = job.get("crop_readiness") if isinstance(job.get("crop_readiness"), Mapping) else {}
    return [
        {
            "step": "review_generation_prompt",
            "tool": submit.get("tool", ""),
            "status": "ready_for_review" if submit else "missing_submit_handoff",
            "prompt_preview": prompt_preview[:500],
            "reason": "Confirm the generated asset is a single environment prop with the planned size, surface contact, and visual role.",
        },
        {
            "step": "review_spatial_generation_brief",
            "status": "ready_for_review" if job.get("spatial_generation_brief") else "missing_spatial_generation_brief",
            "brief": job.get("spatial_generation_brief", {}),
            "brief_prompt": str(job.get("spatial_generation_brief_prompt") or "")[:800],
            "reason": "Confirm the Tripo job is grounded in the target room, zone, support surface, clearance, and post-import validation plan.",
        },
        {
            "step": "prepare_image_crop",
            "tool": "spatial_prepare_screenshot_crop_manifest",
            "status": (
                "prepared"
                if crop_readiness.get("ready")
                else "required_before_image_submission"
                if job.get("mode") == "image_to_model"
                else "not_applicable"
            ),
            "blocking": bool(job.get("mode") == "image_to_model" and not crop_readiness.get("ready")),
            "crop_readiness": crop_readiness,
            "reason": "Image-to-model jobs need a concrete crop file, image URL, or file token before paid Tripo submission.",
        },
        {
            "step": "confirm_tripo_spend",
            "status": "approved" if spend_confirmed else "requires_user_confirmation",
            "blocking": bool(not spend_confirmed),
            "reason": "Paid Tripo generation must remain blocked until the user explicitly approves spend.",
        },
        {
            "step": "submit_tripo_generation",
            "tool": submit.get("tool", ""),
            "status": (
                "ready"
                if ready_for_submission and spend_confirmed
                else "blocked_by_spend_confirmation"
                if ready_for_submission
                else "blocked_by_crop_review"
            ),
            "arguments": submit_args,
        },
        {
            "step": "wait_for_tripo_result",
            "tool": "gen_tripo_wait_for_task",
            "status": "pending_submission",
            "arguments": (job.get("wait") or {}).get("arguments", {}) if isinstance(job.get("wait"), Mapping) else {},
        },
        {
            "step": "import_to_unreal",
            "tool": "gen_tripo_import_to_project",
            "status": "pending_generation_result",
            "arguments": (job.get("import") or {}).get("arguments", {}) if isinstance(job.get("import"), Mapping) else {},
        },
        {
            "step": "bind_import_to_composition",
            "tool": "spatial_bind_generated_assets_to_composition",
            "status": "pending_import_result",
            "arguments": {
                "composition_plan_json": "<ORIGINAL_COMPOSITION_OR_SCREENSHOT_RECONSTRUCTION_JSON>",
                "import_results_json": f"<IMPORT_RESULT_FOR_{prop_id}>",
            },
        },
        {
            "step": "review_spatial_fit",
            "tool": "spatial_plan_asset_scale_corrections",
            "status": "pending_binding",
            "spatial_fit": job.get("spatial_fit", {}),
        },
        {
            "step": "anchor_support_surfaces",
            "tool": "spatial_plan_support_surface_anchors",
            "status": "pending_fit_review",
        },
        {
            "step": "preflight_layout",
            "tool": "spatial_preflight_interior_layout",
            "status": "pending_support_anchors",
        },
        {
            "step": "dry_run_place_generated_asset",
            "tool": "spatial_apply_composition_plan",
            "status": "pending_layout_preflight",
            "placement_after_import": job.get("placement_after_import", {}),
        },
        {
            "step": "validate_generated_asset_placement",
            "tool": "spatial_validate_placement",
            "status": "pending_dry_run_apply",
            "arguments": {
                "actors": [actor_label] if actor_label else [],
                "include_evidence_handoff": True,
            },
        },
        {
            "step": "capture_viewport_evidence",
            "tool": "viewport_capture_screenshot",
            "status": "pending_validation",
            "arguments": {"artifact_name": f"generated_asset_{prop_id}_review", "show_ui": False},
        },
    ]


def _tripo_batch_guarded_pipeline_summary(
    jobs: Sequence[Mapping[str, Any]],
    *,
    confirm_spend: bool,
    not_ready_count: int,
) -> Dict[str, Any]:
    return {
        "job_count": len(jobs),
        "spend_confirmed": bool(confirm_spend),
        "spend_confirmation_required": bool(jobs and not confirm_spend),
        "ready_for_submission_count": len([job for job in jobs if job.get("ready_for_submission")]),
        "blocked_by_crop_review_count": int(not_ready_count),
        "blocked_by_crop_manifest_count": len([
            job for job in jobs
            if job.get("mode") == "image_to_model"
            and isinstance(job.get("crop_readiness"), Mapping)
            and not job.get("crop_readiness", {}).get("ready")
        ]),
        "blocked_by_spend_confirmation_count": len([job for job in jobs if job.get("ready_for_submission")]) if jobs and not confirm_spend else 0,
        "spatial_generation_brief_count": len([job for job in jobs if job.get("spatial_generation_brief")]),
        "required_sequence": [
            "review_generation_prompt",
            "review_spatial_generation_brief",
            "prepare_image_crop",
            "confirm_tripo_spend",
            "submit_tripo_generation",
            "wait_for_tripo_result",
            "import_to_unreal",
            "bind_import_to_composition",
            "review_spatial_fit",
            "anchor_support_surfaces",
            "preflight_layout",
            "dry_run_place_generated_asset",
            "validate_generated_asset_placement",
            "capture_viewport_evidence",
        ],
    }


def _plan_spatial_tripo_generation_batch(
    *,
    source_outputs: Mapping[str, Any],
    composition_plan: Mapping[str, Any],
    content_path: str,
    session_name: str,
    prefer_image_crops: bool,
    include_text_fallbacks: bool,
    confirm_spend: bool,
    limit: int,
) -> Dict[str, Any]:
    generation_by_id = _generation_tasks_by_id(composition_plan)
    crop_by_id = _crop_tasks_by_id(source_outputs)
    props_by_id = _props_by_id(composition_plan)
    steps_by_id = _placement_steps_by_id(composition_plan)
    resolved_content_path = _generation_content_path(composition_plan=composition_plan, content_path=content_path)
    room = composition_plan.get("room") if isinstance(composition_plan.get("room"), Mapping) else {}
    room_type = str(room.get("type") or "interior")
    safe_session = str(session_name or "").strip() or f"spatial_{_safe_asset_stem(room_type, 'room').lower()}"
    jobs: List[Dict[str, Any]] = []

    for prop_id in _ordered_generation_ids(
        composition_plan=composition_plan,
        generation_by_id=generation_by_id,
        crop_by_id=crop_by_id,
        limit=limit,
    ):
        generation_task = generation_by_id.get(prop_id, {})
        crop_task = crop_by_id.get(prop_id, {})
        prop = props_by_id.get(prop_id, {})
        step = steps_by_id.get(prop_id, {})
        spatial_fit = (
            generation_task.get("spatial_fit")
            if isinstance(generation_task.get("spatial_fit"), Mapping)
            else (prop.get("spatial_fit") if isinstance(prop.get("spatial_fit"), Mapping) else {})
        )
        use_image = bool(prefer_image_crops and crop_task)
        if use_image:
            submit = _handoff_with_arguments(
                {"tool": crop_task.get("tool") or "gen_tripo_image_to_model", "arguments": crop_task.get("arguments", {})},
                confirm_spend=confirm_spend,
            )
            submit["arguments"]["session_name"] = safe_session
            mode = "image_to_model"
            source = "screenshot_crop_task"
            crop_readiness = _image_to_model_crop_readiness(crop_task=crop_task, submit=submit)
            ready = bool(crop_readiness.get("ready"))
        elif generation_task.get("submit"):
            submit = _handoff_with_arguments(generation_task.get("submit", {}), confirm_spend=confirm_spend)
            submit["arguments"]["session_name"] = safe_session
            mode = "text_to_model"
            source = "composition_generation_task"
            ready = True
            crop_readiness = {}
        else:
            continue

        fallback_submit: Dict[str, Any] = {}
        if use_image and include_text_fallbacks and generation_task.get("submit"):
            fallback_submit = _handoff_with_arguments(generation_task.get("submit", {}), confirm_spend=confirm_spend)
            fallback_submit["arguments"]["session_name"] = safe_session

        import_handoff = _import_handoff_for_generation(
            prop_id=prop_id,
            generation_task=generation_task,
            content_path=resolved_content_path,
        )
        wait_handoff = _wait_handoff_for_generation(prop_id, generation_task)
        placement_after_import = _planned_step_after_import(step, prop_id=prop_id)
        placement_arguments = _placement_step_arguments(placement_after_import) if placement_after_import else {}
        prop_name = str(generation_task.get("prop_name") or crop_task.get("name") or prop.get("name") or prop_id)
        spatial_generation_brief = _tripo_spatial_generation_brief(
            prop_id=prop_id,
            prop=prop,
            prop_name=prop_name,
            mode=mode,
            room=room,
            spatial_fit=spatial_fit,
            placement_after_import=placement_after_import,
        )
        spatial_generation_brief_prompt = _tripo_spatial_generation_brief_prompt(spatial_generation_brief)
        if mode == "text_to_model":
            submit = _handoff_with_spatial_generation_prompt(submit, brief_prompt=spatial_generation_brief_prompt)
        if fallback_submit:
            fallback_submit = _handoff_with_spatial_generation_prompt(fallback_submit, brief_prompt=spatial_generation_brief_prompt)
        job = {
            "id": prop_id,
            "prop_name": prop_name,
            "mode": mode,
            "provider": "tripo",
            "source": source,
            "ready_for_submission": ready,
            "zone": prop.get("zone", ""),
            "surface": prop.get("surface", ""),
            "spatial_fit": spatial_fit,
            "crop_readiness": crop_readiness,
            "spatial_generation_brief": spatial_generation_brief,
            "spatial_generation_brief_prompt": spatial_generation_brief_prompt,
            "submit": submit,
            "wait": wait_handoff,
            "import": import_handoff,
            "placement_after_import": placement_after_import,
            "actor_label": placement_arguments.get("actor_label", ""),
            "asset_placeholder": placement_arguments.get("asset_path", f"<IMPORTED_ASSET_PATH_FOR_{prop_id}>"),
        }
        if crop_task:
            job["crop"] = {
                "source_reference": crop_task.get("source_reference", ""),
                "crop_box": crop_task.get("crop_box"),
                "crop_hint": crop_task.get("crop_hint", ""),
                "output_placeholder": crop_task.get("output_placeholder", f"<CROP_FOR_{prop_id}>"),
                "readiness": crop_readiness,
            }
        if fallback_submit:
            job["text_fallback_submit"] = fallback_submit
        if generation_task.get("negative_prompt"):
            job["negative_prompt"] = generation_task["negative_prompt"]
        if spatial_fit:
            job["review_requirements"] = list(spatial_fit.get("generation_requirements", [])) if isinstance(spatial_fit.get("generation_requirements"), list) else []
        job["guarded_pipeline"] = _tripo_job_guarded_pipeline(job, confirm_spend=confirm_spend)
        jobs.append(job)

    not_ready_jobs = [job for job in jobs if not job.get("ready_for_submission")]
    if not jobs:
        status = "no_generation_needed"
    elif not_ready_jobs:
        status = "needs_crop_review"
    elif not confirm_spend:
        status = "needs_user_spend_confirmation"
    else:
        status = "ready_for_tripo_submission"

    actor_labels = [str(job.get("actor_label") or "") for job in jobs if job.get("actor_label")]
    blocked_by_crop_manifest = [
        job for job in jobs
        if job.get("mode") == "image_to_model"
        and isinstance(job.get("crop_readiness"), Mapping)
        and not job.get("crop_readiness", {}).get("ready")
    ]
    return {
        "schema": TRIPO_GENERATION_BATCH_SCHEMA,
        "status": status,
        "source_schema": source_outputs.get("schema") or composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
        "job_count": len(jobs),
        "ready_job_count": len(jobs) - len(not_ready_jobs),
        "not_ready_job_count": len(not_ready_jobs),
        "blocked_by_crop_manifest_count": len(blocked_by_crop_manifest),
        "image_job_count": sum(1 for job in jobs if job.get("mode") == "image_to_model"),
        "text_job_count": sum(1 for job in jobs if job.get("mode") == "text_to_model"),
        "content_path": resolved_content_path,
        "session_name": safe_session,
        "spend_policy": {
            "confirm_spend": bool(confirm_spend),
            "user_confirmation_required": bool(jobs and not confirm_spend),
            "notes": [
                "This batch manifest does not submit paid Tripo tasks by itself.",
                "Set confirm_spend=true on the actual gen_tripo_* call only after explicit user approval.",
            ],
        },
        "jobs": jobs,
        "spatial_generation_briefs": [job["spatial_generation_brief"] for job in jobs if job.get("spatial_generation_brief")],
        "spatial_generation_brief_count": len([job for job in jobs if job.get("spatial_generation_brief")]),
        "guarded_pipeline_summary": _tripo_batch_guarded_pipeline_summary(
            jobs,
            confirm_spend=confirm_spend,
            not_ready_count=len(not_ready_jobs),
        ),
        "submit_handoffs": [job["submit"] for job in jobs],
        "wait_handoffs": [job["wait"] for job in jobs],
        "import_handoffs": [job["import"] for job in jobs],
        "post_import_binding_handoff": {
            "tool": "spatial_bind_generated_assets_to_composition",
            "arguments": {
                "composition_plan_json": "<ORIGINAL_COMPOSITION_OR_SCREENSHOT_RECONSTRUCTION_JSON>",
                "import_results_json": "<GEN_TRIPO_IMPORT_TO_PROJECT_RESULTS_JSON>",
            },
            "enabled": bool(jobs),
        },
        "post_binding_scale_correction_handoff": {
            "tool": "spatial_plan_asset_scale_corrections",
            "arguments": {
                "composition_plan_json": "<SPATIAL_BIND_GENERATED_ASSETS_TO_COMPOSITION_RESULT_JSON>",
                "allow_non_uniform_scale": False,
            },
            "enabled": bool(jobs),
        },
        "post_scale_support_anchor_handoff": {
            "tool": "spatial_plan_support_surface_anchors",
            "arguments": {
                "composition_plan_json": "<SPATIAL_PLAN_ASSET_SCALE_CORRECTIONS_RESULT_JSON_OR_BINDING_RESULT_JSON>",
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
            },
            "enabled": bool(jobs),
        },
        "placement_validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": actor_labels,
                "surface_tolerance": 15.0,
                "clearance_padding": 12.0,
                "include_evidence_handoff": True,
            },
            "enabled": bool(actor_labels),
        },
        "workflow": [
            {"step": "review_generation_batch", "reason": "Confirm every generated prop is missing, correctly scoped, and worth Tripo spend."},
            {"step": "review_spatial_generation_briefs", "enabled": bool(jobs), "brief_count": len([job for job in jobs if job.get("spatial_generation_brief")]), "reason": "Confirm each Tripo job is grounded in the intended room dimensions, zone, support surface, placement, and validation gates."},
            {"step": "review_spatial_fit", "enabled": bool(jobs), "job_ids": [job["id"] for job in jobs], "reason": "Check each generated asset against intended size, support contact, adjacency, and placement constraints before import/placement."},
            {"step": "prepare_missing_crops", "tool": "spatial_prepare_screenshot_crop_manifest", "enabled": bool(blocked_by_crop_manifest), "job_ids": [job["id"] for job in blocked_by_crop_manifest], "reason": "Write concrete local crop files before image-to-model spend."},
            {"step": "approve_tripo_spend", "enabled": bool(jobs and not confirm_spend), "reason": "Paid generation remains blocked until the user approves spend."},
            {"step": "submit_tripo_jobs", "handoffs": [job["submit"] for job in jobs], "enabled": bool(jobs and not not_ready_jobs)},
            {"step": "wait_for_tripo_jobs", "handoffs": [job["wait"] for job in jobs], "enabled": bool(jobs)},
            {"step": "import_generated_assets", "handoffs": [job["import"] for job in jobs], "enabled": bool(jobs)},
            {"step": "bind_imports_to_composition", "tool": "spatial_bind_generated_assets_to_composition"},
            {"step": "plan_asset_scale_corrections", "tool": "spatial_plan_asset_scale_corrections", "enabled": bool(jobs)},
            {"step": "plan_support_surface_anchors", "tool": "spatial_plan_support_surface_anchors", "enabled": bool(jobs)},
            {"step": "preflight_and_repair_layout", "tools": ["spatial_preflight_interior_layout", "spatial_plan_layout_preflight_corrections"], "enabled": bool(jobs)},
            {"step": "place_validate_iterate", "tools": ["spatial_apply_composition_plan", "spatial_validate_placement", "spatial_plan_composition_iteration"]},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is a Ghost-owned Tripo batch manifest over Ghost composition and screenshot reconstruction schemas.",
                "It does not copy Epic native MCP, SceneTools, or proprietary generation-provider implementation code.",
            ],
        },
    }


def _composition_like_from_json(value: str) -> Dict[str, Any]:
    parsed = _json_object_from_text(value, "composition_plan_json")
    if not parsed:
        return {}
    outputs = parsed.get("outputs") if parsed.get("schema") == SPATIAL_RESULT_SCHEMA else parsed
    if not isinstance(outputs, dict):
        raise ValueError("composition_plan_json.outputs must be an object")
    schema = outputs.get("schema")
    if schema == SCREENSHOT_RECONSTRUCTION_SCHEMA:
        plan = outputs.get("composition_plan")
        if isinstance(plan, dict):
            return dict(plan)
        raise ValueError("composition_plan_json screenshot reconstruction output must include composition_plan")
    if schema == COMPOSITION_ASSET_BINDING_SCHEMA:
        return {
            "schema": COMPOSITION_ASSET_BINDING_SCHEMA,
            "room": outputs.get("room", {}),
            "zones": outputs.get("zones", []),
            "props": outputs.get("bound_props", []),
            "placement_steps": outputs.get("all_placement_steps") or outputs.get("placement_steps", []),
            "asset_bindings": outputs.get("asset_bindings", []),
            "spatial_fit_reviews": outputs.get("spatial_fit_reviews", []),
            "spatial_fit_review_summary": outputs.get("spatial_fit_review_summary", {}),
        }
    if schema == ASSET_SCALE_CORRECTION_SCHEMA:
        plan = outputs.get("updated_composition_plan")
        if isinstance(plan, dict):
            return dict(plan)
        raise ValueError("composition_plan_json asset scale correction output must include updated_composition_plan")
    if schema == SUPPORT_SURFACE_ANCHOR_SCHEMA:
        plan = outputs.get("updated_composition_plan")
        if isinstance(plan, dict):
            return dict(plan)
        raise ValueError("composition_plan_json support surface anchor output must include updated_composition_plan")
    if schema == LAYOUT_PREFLIGHT_CORRECTION_SCHEMA:
        plan = outputs.get("updated_composition_plan")
        if isinstance(plan, dict):
            return dict(plan)
        raise ValueError("composition_plan_json layout preflight correction output must include updated_composition_plan")
    if schema not in (None, INTERIOR_COMPOSITION_SCHEMA):
        raise ValueError(
            "composition_plan_json must have schema "
            f"{INTERIOR_COMPOSITION_SCHEMA}, {SCREENSHOT_RECONSTRUCTION_SCHEMA}, {COMPOSITION_ASSET_BINDING_SCHEMA}, {ASSET_SCALE_CORRECTION_SCHEMA}, {SUPPORT_SURFACE_ANCHOR_SCHEMA}, or {LAYOUT_PREFLIGHT_CORRECTION_SCHEMA}"
        )
    return dict(outputs)


def _room_context_for_preflight(
    *,
    composition_plan: Mapping[str, Any],
    room_analysis: Mapping[str, Any],
) -> Dict[str, Any]:
    room = composition_plan.get("room") if isinstance(composition_plan.get("room"), Mapping) else {}
    room_type = _clean_room_type(str(room_analysis.get("room_type") or room.get("type") or "apartment"))
    dimensions = (
        list(room_analysis.get("room_dimensions"))
        if room_analysis.get("room_dimensions")
        else _room_dimensions(room.get("dimensions_cm") if isinstance(room.get("dimensions_cm"), Sequence) else None)
    )
    origin = (
        list(room_analysis.get("room_origin"))
        if room_analysis.get("room_origin")
        else (_vector3(room.get("origin"), "composition_plan_json.room.origin") or [0.0, 0.0, 0.0])
    )
    zones = room_analysis.get("zones") if isinstance(room_analysis.get("zones"), list) else composition_plan.get("zones")
    if not isinstance(zones, list) or not zones:
        zones = _room_zones(room_type, origin, dimensions)
    clean_zones = []
    for index, zone in enumerate(zones[:16]):
        if not isinstance(zone, Mapping):
            continue
        center = _optional_vector3(zone.get("center"))
        size = _optional_vector3(zone.get("size"))
        if center is None or size is None:
            continue
        clean_zones.append({
            "name": str(zone.get("name") or f"zone_{index}").strip(),
            "center": center,
            "size": size,
            "wall": str(zone.get("wall") or "open_center"),
        })
    if not clean_zones:
        clean_zones = _room_zones(room_type, origin, dimensions)
    width, depth, height = [float(component) for component in dimensions]
    ox, oy, oz = [float(component) for component in origin]
    return {
        "type": room_type,
        "dimensions_cm": [width, depth, height],
        "origin": [ox, oy, oz],
        "zones": clean_zones,
        "bounds": {
            "min": [ox - width / 2.0, oy - depth / 2.0, oz],
            "max": [ox + width / 2.0, oy + depth / 2.0, oz + height],
        },
    }


def _opening_sources_for_preflight(
    *,
    composition_plan: Mapping[str, Any],
    room_analysis: Mapping[str, Any],
) -> List[Mapping[str, Any]]:
    sources: List[Mapping[str, Any]] = []
    sources.extend(_analysis_surfaces(room_analysis, "openings"))
    room = composition_plan.get("room") if isinstance(composition_plan.get("room"), Mapping) else {}
    for candidate_source in (room.get("openings"), composition_plan.get("openings")):
        if not isinstance(candidate_source, list):
            continue
        sources.extend(item for item in candidate_source if isinstance(item, Mapping))
    deduped: List[Mapping[str, Any]] = []
    seen = set()
    for source in sources:
        bounds = source.get("bounds") if isinstance(source.get("bounds"), Mapping) else {}
        key = (
            str(source.get("id") or source.get("label") or source.get("name") or "").lower(),
            json.dumps(bounds, sort_keys=True, default=str) if bounds else "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped[:32]


def _opening_bounds_values(source: Mapping[str, Any]) -> Optional[Dict[str, List[float]]]:
    bounds = source.get("bounds") if isinstance(source.get("bounds"), Mapping) else {}
    mins = _optional_vector3(bounds.get("min"))
    maxs = _optional_vector3(bounds.get("max"))
    if mins is not None and maxs is not None:
        return {
            "min": [min(float(mins[axis]), float(maxs[axis])) for axis in range(3)],
            "max": [max(float(mins[axis]), float(maxs[axis])) for axis in range(3)],
        }
    center = _optional_vector3(source.get("center") or source.get("location") or source.get("top_center"))
    size = _optional_vector3(
        source.get("size")
        or source.get("dimensions_cm")
        or source.get("approx_size_cm")
    )
    if center is None or size is None:
        return None
    half = [max(1.0, float(value)) / 2.0 for value in size]
    return {
        "min": [float(center[axis]) - half[axis] for axis in range(3)],
        "max": [float(center[axis]) + half[axis] for axis in range(3)],
    }


def _clamped_footprint(
    *,
    min_xy: Sequence[float],
    max_xy: Sequence[float],
    room: Mapping[str, Any],
) -> Dict[str, List[float]]:
    room_min = room.get("bounds", {}).get("min", [0.0, 0.0, 0.0])
    room_max = room.get("bounds", {}).get("max", [0.0, 0.0, 0.0])
    return {
        "min": [
            round(max(float(room_min[0]), min(float(min_xy[0]), float(max_xy[0]))), 3),
            round(max(float(room_min[1]), min(float(min_xy[1]), float(max_xy[1]))), 3),
        ],
        "max": [
            round(min(float(room_max[0]), max(float(min_xy[0]), float(max_xy[0]))), 3),
            round(min(float(room_max[1]), max(float(min_xy[1]), float(max_xy[1]))), 3),
        ],
    }


def _opening_clearance_records(
    *,
    composition_plan: Mapping[str, Any],
    room_analysis: Mapping[str, Any],
    room: Mapping[str, Any],
    min_walkway_width: float,
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    approach_depth = max(60.0, float(min_walkway_width))
    side_buffer = max(15.0, min(35.0, float(min_walkway_width) * 0.25))
    for index, source in enumerate(_opening_sources_for_preflight(composition_plan=composition_plan, room_analysis=room_analysis)):
        bounds = _opening_bounds_values(source)
        if bounds is None:
            continue
        mins = bounds["min"]
        maxs = bounds["max"]
        size_x = max(1.0, float(maxs[0]) - float(mins[0]))
        size_y = max(1.0, float(maxs[1]) - float(mins[1]))
        if size_x >= size_y:
            protected = _clamped_footprint(
                min_xy=[float(mins[0]) - side_buffer, float(mins[1]) - approach_depth],
                max_xy=[float(maxs[0]) + side_buffer, float(maxs[1]) + approach_depth],
                room=room,
            )
            opening_axis = "x"
            approach_axis = "y"
            width = size_x
        else:
            protected = _clamped_footprint(
                min_xy=[float(mins[0]) - approach_depth, float(mins[1]) - side_buffer],
                max_xy=[float(maxs[0]) + approach_depth, float(maxs[1]) + side_buffer],
                room=room,
            )
            opening_axis = "y"
            approach_axis = "x"
            width = size_y
        if protected["min"][0] >= protected["max"][0] or protected["min"][1] >= protected["max"][1]:
            continue
        records.append({
            "id": str(source.get("id") or source.get("label") or source.get("name") or f"opening_{index}"),
            "label": str(source.get("label") or source.get("name") or source.get("id") or f"opening_{index}"),
            "roles": list(source.get("roles", [])) if isinstance(source.get("roles"), list) else ["opening"],
            "opening_axis": opening_axis,
            "approach_axis": approach_axis,
            "opening_width_cm": round(width, 3),
            "approach_depth_cm": round(approach_depth, 3),
            "side_buffer_cm": round(side_buffer, 3),
            "bounds": {
                "min": _rounded_vector(mins),
                "max": _rounded_vector(maxs),
            },
            "protected_footprint": protected,
            "blocked_by": [],
        })
    return records


def _actor_exempt_from_opening_clearance(check: Mapping[str, Any]) -> bool:
    text = " ".join([
        str(check.get("name") or ""),
        str(check.get("category") or ""),
        str(check.get("surface") or ""),
        str(check.get("placement_source") or ""),
    ]).lower()
    if "door casing" in text or "door trim" in text or "threshold" in text:
        return True
    if any(token in text for token in ("entry door", "front door", "doorway", "window", "archway", "opening")):
        return "wall" in text or "architectural" in text
    return False


def _visual_anchor_score(check: Mapping[str, Any]) -> float:
    text = " ".join([
        str(check.get("name") or ""),
        str(check.get("category") or ""),
        str(check.get("zone") or ""),
    ]).lower()
    scores = [
        (10.0, ("sofa", "couch", "bed", "kitchen counter", "counter run", "island")),
        (8.0, ("stove", "oven", "range", "sink", "refrigerator", "fridge")),
        (7.0, ("coffee table", "rug", "bookshelf", "bookcase", "dresser")),
        (5.0, ("entry console", "floor lamp", "nightstand", "cabinet")),
    ]
    for score, tokens in scores:
        if any(token in text for token in tokens):
            return score
    return 0.0


def _visual_anchor_checks(actor_checks: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    best_by_zone: Dict[str, Mapping[str, Any]] = {}
    for check in actor_checks:
        if not check.get("valid", True):
            continue
        zone = str(check.get("zone") or check.get("inferred_zone") or "").strip() or "room"
        if zone == "entry":
            continue
        score = _visual_anchor_score(check)
        if score <= 0.0:
            continue
        current = best_by_zone.get(zone)
        if current is None or score > _visual_anchor_score(current):
            best_by_zone[zone] = check
    return [best_by_zone[key] for key in sorted(best_by_zone)]


def _opening_focus_point(opening: Mapping[str, Any]) -> List[float]:
    bounds = opening.get("bounds") if isinstance(opening.get("bounds"), Mapping) else {}
    min_v = _optional_vector3(bounds.get("min"))
    max_v = _optional_vector3(bounds.get("max"))
    if min_v is not None and max_v is not None:
        return [
            round((float(min_v[0]) + float(max_v[0])) / 2.0, 3),
            round((float(min_v[1]) + float(max_v[1])) / 2.0, 3),
            round((float(min_v[2]) + float(max_v[2])) / 2.0, 3),
        ]
    protected = opening.get("protected_footprint") if isinstance(opening.get("protected_footprint"), Mapping) else {}
    min_xy = protected.get("min") if isinstance(protected.get("min"), list) else [0.0, 0.0]
    max_xy = protected.get("max") if isinstance(protected.get("max"), list) else [0.0, 0.0]
    return [
        round((float(min_xy[0]) + float(max_xy[0])) / 2.0, 3),
        round((float(min_xy[1]) + float(max_xy[1])) / 2.0, 3),
        0.0,
    ]


def _segment_distance_xy(point: Sequence[float], start: Sequence[float], end: Sequence[float]) -> Dict[str, float]:
    sx, sy = float(start[0]), float(start[1])
    ex, ey = float(end[0]), float(end[1])
    px, py = float(point[0]), float(point[1])
    dx = ex - sx
    dy = ey - sy
    length_sq = dx * dx + dy * dy
    if length_sq <= 0.0001:
        return {"distance_cm": round(((px - sx) ** 2 + (py - sy) ** 2) ** 0.5, 3), "t": 0.0}
    t = max(0.0, min(1.0, ((px - sx) * dx + (py - sy) * dy) / length_sq))
    nearest_x = sx + t * dx
    nearest_y = sy + t * dy
    distance = ((px - nearest_x) ** 2 + (py - nearest_y) ** 2) ** 0.5
    return {"distance_cm": round(distance, 3), "t": round(t, 3)}


def _actor_blocks_visual_sightline(check: Mapping[str, Any]) -> bool:
    if str(check.get("surface") or "").lower() != "floor":
        return False
    text = " ".join([str(check.get("name") or ""), str(check.get("category") or "")]).lower()
    if any(token in text for token in ("rug", "carpet", "coffee table", "floor lamp", "table clutter", "books and")):
        return False
    size = _optional_vector3(check.get("approx_size_cm")) or [0.0, 0.0, 0.0]
    if float(size[2]) < 70.0:
        return False
    return max(float(size[0]), float(size[1])) >= 35.0


def _visual_sightline_records(
    *,
    opening_clearance: Sequence[Mapping[str, Any]],
    actor_checks: Sequence[Mapping[str, Any]],
    min_walkway_width: float,
) -> List[Dict[str, Any]]:
    anchors = _visual_anchor_checks(actor_checks)
    records: List[Dict[str, Any]] = []
    if not opening_clearance or not anchors:
        return records
    corridor_width = max(45.0, min(110.0, float(min_walkway_width) * 0.65))
    corridor_half = corridor_width / 2.0
    for opening in opening_clearance[:8]:
        start = _opening_focus_point(opening)
        for anchor in anchors[:12]:
            target = _optional_vector3(anchor.get("location"))
            if target is None:
                continue
            blockers: List[Dict[str, Any]] = []
            for check in actor_checks:
                if check.get("id") == anchor.get("id") or check.get("actor_label") == anchor.get("actor_label"):
                    continue
                if not _actor_blocks_visual_sightline(check):
                    continue
                blocker_location = _optional_vector3(check.get("location"))
                blocker_size = _optional_vector3(check.get("approx_size_cm")) or [0.0, 0.0, 0.0]
                if blocker_location is None:
                    continue
                distance = _segment_distance_xy(blocker_location, start, target)
                if float(distance["t"]) <= 0.08 or float(distance["t"]) >= 0.92:
                    continue
                blocker_radius = min(max(float(blocker_size[0]), float(blocker_size[1])) / 2.0, 85.0)
                if float(distance["distance_cm"]) > corridor_half + blocker_radius:
                    continue
                blockers.append({
                    "actor_label": check.get("actor_label"),
                    "id": check.get("id"),
                    "distance_to_sightline_cm": distance["distance_cm"],
                    "segment_t": distance["t"],
                    "approx_size_cm": _rounded_vector(blocker_size),
                })
            records.append({
                "opening_label": opening.get("label"),
                "target_actor_label": anchor.get("actor_label"),
                "target_id": anchor.get("id"),
                "target_zone": anchor.get("zone") or anchor.get("inferred_zone") or "",
                "target_name": anchor.get("name"),
                "start": _rounded_vector(start),
                "target": _rounded_vector(target),
                "corridor_width_cm": round(corridor_width, 3),
                "status": "obstructed_review" if blockers else "clear",
                "blocker_count": len(blockers),
                "blockers": blockers,
            })
    return records[:64]


def _prop_size_surface_zone(prop: Mapping[str, Any], step_id: str) -> Dict[str, Any]:
    match = _best_interior_prop_match(str(prop.get("name") or step_id or ""))
    size = prop.get("approx_size_cm") or prop.get("size") or (match or {}).get("size") or [75.0, 75.0, 75.0]
    try:
        clean_size = [max(1.0, float(size[0])), max(1.0, float(size[1])), max(1.0, float(size[2]))]
    except Exception:
        clean_size = [75.0, 75.0, 75.0]
    return {
        "size": clean_size,
        "surface": str(prop.get("surface") or (match or {}).get("surface") or "floor").strip().lower() or "floor",
        "zone": str(prop.get("zone") or (match or {}).get("zone") or "").strip(),
        "category": str(prop.get("category") or (match or {}).get("category") or "prop").strip().lower(),
        "name": str(prop.get("name") or (match or {}).get("name") or step_id).strip(),
    }


def _interaction_clearance_profile(details: Mapping[str, Any]) -> Dict[str, Any]:
    text = " ".join([
        str(details.get("name") or ""),
        str(details.get("category") or ""),
        str(details.get("surface") or ""),
    ]).lower()
    if any(token in text for token in ("refrigerator", "fridge")):
        return {
            "kind": "appliance_door_swing",
            "required_cm": 95.0,
            "severity": "warning",
            "reason": "Reserve door-swing and standing space in front of the refrigerator.",
        }
    if any(token in text for token in ("stove", "oven", "range")):
        return {
            "kind": "appliance_work_zone",
            "required_cm": 90.0,
            "severity": "warning",
            "reason": "Reserve a safe cooking work zone and access space in front of the range.",
        }
    if any(token in text for token in ("sink", "counter run", "countertop", "kitchen counter")):
        return {
            "kind": "counter_work_clearance",
            "required_cm": 75.0,
            "severity": "warning",
            "reason": "Reserve standing work clearance for counters, sinks, and prep zones.",
        }
    if any(token in text for token in ("bar stool", "stool", "chair", "sofa", "couch")):
        return {
            "kind": "seating_pullback_clearance",
            "required_cm": 60.0,
            "severity": "warning",
            "reason": "Reserve pullback and approach clearance for seating.",
        }
    if any(token in text for token in ("cabinet", "dresser", "wardrobe", "bookshelf", "bookcase")):
        return {
            "kind": "storage_access_clearance",
            "required_cm": 55.0,
            "severity": "suggestion",
            "reason": "Reserve access space for doors, drawers, shelves, and reachable storage.",
        }
    return {}


def _clearance_margin_for_yaw(yaw: float) -> Dict[str, Any]:
    normalized = yaw % 360.0
    if normalized >= 315.0 or normalized < 45.0:
        return {"margin_key": "back", "facing_direction": "positive_y"}
    if normalized < 135.0:
        return {"margin_key": "right", "facing_direction": "positive_x"}
    if normalized < 225.0:
        return {"margin_key": "front", "facing_direction": "negative_y"}
    return {"margin_key": "left", "facing_direction": "negative_x"}


def _clearance_margin_from_wall(wall: str) -> Dict[str, Any]:
    normalized = wall.strip().lower()
    if normalized == "negative_y":
        return {"margin_key": "back", "facing_direction": "positive_y"}
    if normalized == "positive_y":
        return {"margin_key": "front", "facing_direction": "negative_y"}
    if normalized == "negative_x":
        return {"margin_key": "right", "facing_direction": "positive_x"}
    if normalized == "positive_x":
        return {"margin_key": "left", "facing_direction": "negative_x"}
    return {}


def _interaction_clearance_orientation(
    *,
    args: Mapping[str, Any],
    placement: Mapping[str, Any],
    zone: Optional[Mapping[str, Any]],
    inferred_zone: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    rotation = _optional_vector3(args.get("rotation")) or _optional_vector3(placement.get("rotation"))
    if rotation is not None:
        oriented = _clearance_margin_for_yaw(float(rotation[1]))
        return {
            **oriented,
            "source": "rotation_yaw",
            "yaw_degrees": round(float(rotation[1]) % 360.0, 3),
        }
    for source_name, candidate in (("zone_wall", zone), ("inferred_zone_wall", inferred_zone)):
        if not isinstance(candidate, Mapping):
            continue
        oriented = _clearance_margin_from_wall(str(candidate.get("wall") or ""))
        if oriented:
            return {
                **oriented,
                "source": source_name,
                "wall": str(candidate.get("wall") or ""),
            }
    return {
        "margin_key": "max_room_margin",
        "facing_direction": "unknown",
        "source": "fallback_largest_margin",
    }


def _preflight_actor_checks(
    *,
    composition_plan: Mapping[str, Any],
    room: Mapping[str, Any],
    clearance_padding: float,
) -> List[Dict[str, Any]]:
    props_by_id = _props_by_id(composition_plan)
    steps = composition_plan.get("placement_steps") if isinstance(composition_plan.get("placement_steps"), list) else []
    if not steps and isinstance(composition_plan.get("all_placement_steps"), list):
        steps = composition_plan.get("all_placement_steps")
    checks: List[Dict[str, Any]] = []
    zones = room.get("zones") if isinstance(room.get("zones"), list) else []
    room_min = room.get("bounds", {}).get("min", [0.0, 0.0, 0.0])
    room_max = room.get("bounds", {}).get("max", [0.0, 0.0, 0.0])
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            continue
        step_id = str(step.get("id") or f"step_{index}").strip()
        args = _placement_step_arguments(step)
        location = _optional_vector3(args.get("location"))
        prop = props_by_id.get(step_id, {})
        placement = prop.get("placement") if isinstance(prop.get("placement"), Mapping) else {}
        details = _prop_size_surface_zone(prop, step_id)
        actor_label = str(args.get("actor_label") or placement.get("actor_label") or step_id)
        if location is None:
            checks.append({
                "id": step_id,
                "actor_label": actor_label,
                "valid": False,
                "issues": [{"severity": "error", "kind": "missing_location", "message": "Placement step has no three-number location."}],
            })
            continue
        size = details["size"]
        padding = float(clearance_padding if details["surface"] == "floor" else min(clearance_padding, 6.0))
        footprint = {
            "min": [location[0] - size[0] / 2.0 - padding, location[1] - size[1] / 2.0 - padding],
            "max": [location[0] + size[0] / 2.0 + padding, location[1] + size[1] / 2.0 + padding],
        }
        room_margins = {
            "left": round(footprint["min"][0] - float(room_min[0]), 3),
            "right": round(float(room_max[0]) - footprint["max"][0], 3),
            "front": round(footprint["min"][1] - float(room_min[1]), 3),
            "back": round(float(room_max[1]) - footprint["max"][1], 3),
            "ceiling": round(float(room_max[2]) - (location[2] + size[2]), 3),
        }
        interaction_profile = _interaction_clearance_profile(details)
        zone = next((candidate for candidate in zones if str(candidate.get("name")) == details["zone"]), None)
        inferred_zone = next((candidate for candidate in zones if _zone_contains_xy(candidate, location)), None)
        if interaction_profile:
            margins = {
                "left": float(room_margins.get("left", 0.0)),
                "right": float(room_margins.get("right", 0.0)),
                "front": float(room_margins.get("front", 0.0)),
                "back": float(room_margins.get("back", 0.0)),
            }
            orientation = _interaction_clearance_orientation(
                args=args,
                placement=placement,
                zone=zone,
                inferred_zone=inferred_zone,
            )
            margin_key = str(orientation.get("margin_key") or "max_room_margin")
            max_available = max(margins.values())
            front_available = margins.get(margin_key, max_available)
            required = float(interaction_profile.get("required_cm") or 0.0)
            interaction_profile = {
                **interaction_profile,
                "available_cm": round(front_available, 3),
                "max_available_cm": round(max_available, 3),
                "front_available_cm": round(front_available, 3),
                "front_margin_key": margin_key,
                "facing_direction": str(orientation.get("facing_direction") or "unknown"),
                "orientation_source": str(orientation.get("source") or "unknown"),
                "room_margin_cm": {key: round(value, 3) for key, value in margins.items()},
                "status": "clear" if front_available >= required else "tight_review",
            }
            if "yaw_degrees" in orientation:
                interaction_profile["yaw_degrees"] = orientation["yaw_degrees"]
            if "wall" in orientation:
                interaction_profile["wall"] = orientation["wall"]
        checks.append({
            "id": step_id,
            "actor_label": actor_label,
            "name": details["name"],
            "category": details["category"],
            "surface": details["surface"],
            "zone": details["zone"],
            "inferred_zone": str((inferred_zone or {}).get("name") or ""),
            "location": _rounded_vector(location),
            "approx_size_cm": _rounded_vector(size),
            "footprint": footprint,
            "room_bounds_margin_cm": room_margins,
            "interaction_clearance": interaction_profile,
            "zone_expected": zone is not None,
            "placement_source": str(args.get("placement_source") or placement.get("source") or ""),
            "support_actor": str(args.get("support_actor") or placement.get("support_actor") or ""),
            "support_roles": list(placement.get("support_roles", [])) if isinstance(placement.get("support_roles"), list) else [],
            "valid": True,
            "issues": [],
        })
    return checks


def _add_preflight_issue(issues: List[Dict[str, Any]], actor_check: Optional[Dict[str, Any]], issue: Dict[str, Any]) -> None:
    issues.append(issue)
    if actor_check is not None:
        actor_check.setdefault("issues", []).append(issue)
        if issue.get("severity") == "error":
            actor_check["valid"] = False


def _aabb_gap(a: Mapping[str, Any], b: Mapping[str, Any]) -> Dict[str, float]:
    ax0, ay0 = a["footprint"]["min"]
    ax1, ay1 = a["footprint"]["max"]
    bx0, by0 = b["footprint"]["min"]
    bx1, by1 = b["footprint"]["max"]
    overlap_x = min(ax1, bx1) - max(ax0, bx0)
    overlap_y = min(ay1, by1) - max(ay0, by0)
    gap_x = max(bx0 - ax1, ax0 - bx1, 0.0)
    gap_y = max(by0 - ay1, ay0 - by1, 0.0)
    return {
        "overlap_x": round(overlap_x, 3),
        "overlap_y": round(overlap_y, 3),
        "gap_cm": round((gap_x * gap_x + gap_y * gap_y) ** 0.5, 3),
    }


def _composition_constraints_for_preflight(
    composition_plan: Mapping[str, Any],
    actor_checks: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    raw_constraints = composition_plan.get("composition_constraints") if isinstance(composition_plan.get("composition_constraints"), list) else []
    constraints = [dict(item) for item in raw_constraints if isinstance(item, Mapping)]
    generated = _composition_semantic_constraints(actor_checks)
    seen = {
        (
            item.get("kind"),
            item.get("source"),
            item.get("target"),
            tuple(item.get("sources", []) if isinstance(item.get("sources"), list) else []),
        )
        for item in constraints
    }
    for item in generated:
        key = (
            item.get("kind"),
            item.get("source"),
            item.get("target"),
            tuple(item.get("sources", []) if isinstance(item.get("sources"), list) else []),
        )
        if key not in seen:
            constraints.append(dict(item))
            seen.add(key)
    return constraints[:128]


def _actor_check_lookup(actor_checks: Sequence[Mapping[str, Any]]) -> Dict[str, Mapping[str, Any]]:
    lookup: Dict[str, Mapping[str, Any]] = {}
    for check in actor_checks:
        for value in (
            check.get("id"),
            check.get("name"),
            check.get("actor_label"),
            _safe_asset_stem(str(check.get("id") or ""), "Prop"),
            _safe_asset_stem(str(check.get("name") or ""), "Prop"),
        ):
            key = _safe_asset_stem(str(value or ""), "Prop").lower()
            if key and key not in lookup:
                lookup[key] = check
    return lookup


def _check_for_constraint_ref(lookup: Mapping[str, Mapping[str, Any]], value: Any) -> Optional[Mapping[str, Any]]:
    key = _safe_asset_stem(str(value or ""), "Prop").lower()
    return lookup.get(key) if key else None


def _xy_distance_for_checks(first: Mapping[str, Any], second: Mapping[str, Any]) -> Optional[float]:
    first_location = _semantic_location(first)
    second_location = _semantic_location(second)
    if not first_location or not second_location:
        return None
    dx = first_location[0] - second_location[0]
    dy = first_location[1] - second_location[1]
    return round((dx * dx + dy * dy) ** 0.5, 3)


def _add_semantic_preflight_issues(
    issues: List[Dict[str, Any]],
    actor_checks: Sequence[Dict[str, Any]],
    semantic_constraints: Sequence[Mapping[str, Any]],
) -> None:
    lookup = _actor_check_lookup(actor_checks)
    for constraint in semantic_constraints:
        kind = str(constraint.get("kind") or "")
        if kind == "counter_adjacency":
            source = _check_for_constraint_ref(lookup, constraint.get("source"))
            target = _check_for_constraint_ref(lookup, constraint.get("target"))
            if source is None or target is None:
                continue
            distance = _xy_distance_for_checks(source, target)
            max_distance = _float_value(constraint.get("max_distance_cm", 180.0), default=180.0, minimum=0.0)
            if distance is not None and distance > max_distance:
                _add_preflight_issue(issues, source, {
                    "severity": "warning",
                    "kind": "semantic_counter_adjacency_gap",
                    "actor_labels": [source.get("actor_label"), target.get("actor_label")],
                    "message": "Semantic composition expects this prop to stay tied to the counter run or island.",
                    "distance_cm": distance,
                    "max_distance_cm": max_distance,
                })
        elif kind == "support_contact":
            source = _check_for_constraint_ref(lookup, constraint.get("source"))
            if source is None:
                continue
            placement_source = str(source.get("placement_source") or "").lower()
            support_actor = str(source.get("support_actor") or "").strip()
            support_ready = bool(support_actor) or any(
                token in placement_source
                for token in ("support", "anchor_counter", "anchor_table", "anchor_coffee_table", "room_analysis_horizontal")
            )
            if not support_ready:
                _add_preflight_issue(issues, source, {
                    "severity": "warning",
                    "kind": "semantic_support_contact_unresolved",
                    "actor_label": source.get("actor_label"),
                    "message": "Semantic composition expects this prop to be visibly supported by a counter, table, shelf, or cabinet.",
                })
        elif kind == "wall_anchor":
            source = _check_for_constraint_ref(lookup, constraint.get("source"))
            if source is None:
                continue
            if "wall" not in str(source.get("placement_source") or "").lower():
                _add_preflight_issue(issues, source, {
                    "severity": "warning",
                    "kind": "semantic_wall_anchor_unresolved",
                    "actor_label": source.get("actor_label"),
                    "message": "Semantic composition expects this prop to be wall-aligned before final placement.",
                })
        elif kind == "kitchen_work_triangle":
            refs = constraint.get("sources") if isinstance(constraint.get("sources"), list) else []
            checks = [_check_for_constraint_ref(lookup, ref) for ref in refs]
            if len([check for check in checks if check is not None]) < 3:
                continue
            distances = []
            for first_index, first in enumerate(checks):
                for second in checks[first_index + 1:]:
                    if first is None or second is None:
                        continue
                    distance = _xy_distance_for_checks(first, second)
                    if distance is not None:
                        distances.append(distance)
            if len(distances) != 3:
                continue
            min_edge = _float_value(constraint.get("min_edge_cm", 90.0), default=90.0, minimum=0.0)
            max_edge = _float_value(constraint.get("max_edge_cm", 360.0), default=360.0, minimum=0.0)
            max_total = _float_value(constraint.get("max_total_cm", 820.0), default=820.0, minimum=0.0)
            if min(distances) < min_edge or max(distances) > max_edge or sum(distances) > max_total:
                issue = {
                    "severity": "warning",
                    "kind": "semantic_kitchen_work_triangle_review",
                    "actor_labels": [check.get("actor_label") for check in checks if check is not None],
                    "message": "Kitchen work-triangle distances are outside the recommended compact range.",
                    "edge_distances_cm": distances,
                    "total_distance_cm": round(sum(distances), 3),
                }
                issues.append(issue)
                for check in checks:
                    if check is not None:
                        check.setdefault("issues", []).append(issue)
        elif kind == "living_visual_group":
            refs = constraint.get("sources") if isinstance(constraint.get("sources"), list) else []
            checks = [_check_for_constraint_ref(lookup, ref) for ref in refs]
            sofa = next((check for check in checks if check is not None and "sofa" in str(check.get("name") or "").lower()), None)
            table = next((check for check in checks if check is not None and "coffee" in str(check.get("name") or "").lower()), None)
            if sofa is None or table is None:
                continue
            distance = _xy_distance_for_checks(sofa, table)
            min_distance = _float_value(constraint.get("min_distance_cm", 45.0), default=45.0, minimum=0.0)
            max_distance = _float_value(constraint.get("max_distance_cm", 280.0), default=280.0, minimum=0.0)
            if distance is not None and (distance < min_distance or distance > max_distance):
                _add_preflight_issue(issues, table, {
                    "severity": "warning",
                    "kind": "semantic_living_group_spacing",
                    "actor_labels": [sofa.get("actor_label"), table.get("actor_label")],
                    "message": "Living-area grouping expects the coffee table to read near the sofa.",
                    "distance_cm": distance,
                    "recommended_range_cm": [min_distance, max_distance],
                })
        elif kind == "bedroom_anchor_group":
            refs = constraint.get("sources") if isinstance(constraint.get("sources"), list) else []
            checks = [_check_for_constraint_ref(lookup, ref) for ref in refs]
            bed = next((
                check for check in checks
                if check is not None and str(check.get("name") or "").lower() == "bed"
            ), None)
            if bed is None:
                continue
            bedside_min = _float_value(constraint.get("bedside_min_distance_cm", 35.0), default=35.0, minimum=0.0)
            bedside_max = _float_value(constraint.get("bedside_max_distance_cm", 170.0), default=170.0, minimum=0.0)
            dresser_max = _float_value(constraint.get("dresser_max_distance_cm", 320.0), default=320.0, minimum=0.0)
            for check in checks:
                if check is None or check is bed:
                    continue
                name = str(check.get("name") or "").lower()
                distance = _xy_distance_for_checks(bed, check)
                if distance is None:
                    continue
                if "nightstand" in name and (distance < bedside_min or distance > bedside_max):
                    _add_preflight_issue(issues, check, {
                        "severity": "warning",
                        "kind": "semantic_bedroom_bedside_spacing",
                        "actor_labels": [bed.get("actor_label"), check.get("actor_label")],
                        "message": "Bedroom grouping expects the nightstand to read beside the bed with reachable clearance.",
                        "distance_cm": distance,
                        "recommended_range_cm": [bedside_min, bedside_max],
                    })
                elif any(token in name for token in ("dresser", "wardrobe")) and distance > dresser_max:
                    _add_preflight_issue(issues, check, {
                        "severity": "warning",
                        "kind": "semantic_bedroom_storage_spacing",
                        "actor_labels": [bed.get("actor_label"), check.get("actor_label")],
                        "message": "Bedroom grouping expects dresser or wardrobe storage to stay readable within the sleep zone.",
                        "distance_cm": distance,
                        "max_distance_cm": dresser_max,
                    })
        elif kind == "hallway_linear_clearance":
            refs = constraint.get("sources") if isinstance(constraint.get("sources"), list) else []
            max_cross_section = _float_value(
                constraint.get("max_floor_prop_cross_section_cm", 90.0),
                default=90.0,
                minimum=1.0,
            )
            for ref in refs:
                check = _check_for_constraint_ref(lookup, ref)
                if check is None:
                    continue
                zone = str(check.get("zone") or check.get("inferred_zone") or "").lower()
                surface = str(check.get("surface") or "").lower()
                if zone != "hallway" or surface != "floor":
                    continue
                size = _size_vector(check.get("approx_size_cm")) or []
                if len(size) < 2:
                    continue
                cross_section = min(float(size[0]), float(size[1]))
                if cross_section > max_cross_section:
                    _add_preflight_issue(issues, check, {
                        "severity": "warning",
                        "kind": "semantic_hallway_clearance_review",
                        "actor_label": check.get("actor_label"),
                        "message": "Hallway floor prop is wide for a corridor; keep it wall-hugging or replace it with narrower dressing.",
                        "cross_section_cm": round(cross_section, 3),
                        "max_floor_prop_cross_section_cm": max_cross_section,
                    })


def _plan_layout_preflight(
    *,
    composition_plan: Mapping[str, Any],
    room_analysis: Mapping[str, Any],
    min_walkway_width: float,
    clearance_padding: float,
    pairwise_padding: float,
    include_suggestions: bool,
) -> Dict[str, Any]:
    room = _room_context_for_preflight(composition_plan=composition_plan, room_analysis=room_analysis)
    actor_checks = _preflight_actor_checks(composition_plan=composition_plan, room=room, clearance_padding=clearance_padding)
    semantic_constraints = _composition_constraints_for_preflight(composition_plan, actor_checks)
    opening_clearance = _opening_clearance_records(
        composition_plan=composition_plan,
        room_analysis=room_analysis,
        room=room,
        min_walkway_width=min_walkway_width,
    )
    visual_sightlines = _visual_sightline_records(
        opening_clearance=opening_clearance,
        actor_checks=actor_checks,
        min_walkway_width=min_walkway_width,
    )
    issues: List[Dict[str, Any]] = []
    pairwise_clearance: List[Dict[str, Any]] = []
    suggestions: List[Dict[str, Any]] = []
    room_min = room["bounds"]["min"]
    room_max = room["bounds"]["max"]
    floor_z = float(room["origin"][2])

    for check in actor_checks:
        for issue in list(check.get("issues", [])):
            issues.append(issue)
        margin = check.get("room_bounds_margin_cm", {})
        if any(float(margin.get(key, 0.0)) < 0.0 for key in ("left", "right", "front", "back")):
            _add_preflight_issue(issues, check, {
                "severity": "error",
                "kind": "outside_room_bounds",
                "actor_label": check["actor_label"],
                "message": "Approximate footprint extends outside the inferred room bounds.",
            })
        if float(margin.get("ceiling", 0.0)) < 0.0:
            _add_preflight_issue(issues, check, {
                "severity": "warning",
                "kind": "exceeds_room_height",
                "actor_label": check["actor_label"],
                "message": "Approximate prop height exceeds the inferred room height.",
            })
        if check.get("zone") and check.get("inferred_zone") and check.get("zone") != check.get("inferred_zone"):
            _add_preflight_issue(issues, check, {
                "severity": "warning",
                "kind": "outside_declared_zone",
                "actor_label": check["actor_label"],
                "message": f"Placement is in {check.get('inferred_zone')} but prop is planned for {check.get('zone')}.",
            })
        if check.get("surface") == "floor" and abs(float(check["location"][2]) - floor_z) > 25.0:
            _add_preflight_issue(issues, check, {
                "severity": "warning",
                "kind": "floor_contact_suspicious",
                "actor_label": check["actor_label"],
                "message": "Floor prop Z is far from the inferred floor height; run spatial_surface_probe.",
            })
        if check.get("surface") in {"counter", "table", "shelf"} and float(check["location"][2]) < floor_z + 45.0:
            _add_preflight_issue(issues, check, {
                "severity": "warning",
                "kind": "support_surface_suspicious",
                "actor_label": check["actor_label"],
                "message": "Counter/table/shelf prop is not clearly on an elevated support surface.",
            })
        if check.get("surface") == "wall" and "wall" not in str(check.get("placement_source", "")):
            _add_preflight_issue(issues, check, {
                "severity": "warning",
                "kind": "wall_mount_source_missing",
                "actor_label": check["actor_label"],
                "message": "Wall-mounted prop was not placed from a wall-aware source.",
            })
        interaction_clearance = check.get("interaction_clearance") if isinstance(check.get("interaction_clearance"), Mapping) else {}
        if interaction_clearance and interaction_clearance.get("status") == "tight_review":
            _add_preflight_issue(issues, check, {
                "severity": str(interaction_clearance.get("severity") or "warning"),
                "kind": "interaction_clearance_tight",
                "actor_label": check["actor_label"],
                "clearance_kind": interaction_clearance.get("kind"),
                "message": str(interaction_clearance.get("reason") or "Review interaction clearance before placement."),
                "available_cm": interaction_clearance.get("available_cm"),
                "required_cm": interaction_clearance.get("required_cm"),
                "room_margin_cm": interaction_clearance.get("room_margin_cm", {}),
            })

    for index, first in enumerate(actor_checks):
        for second in actor_checks[index + 1:]:
            gap = _aabb_gap(first, second)
            record = {
                "a": first["actor_label"],
                "b": second["actor_label"],
                **gap,
            }
            pairwise_clearance.append(record)
            if gap["overlap_x"] > 0.0 and gap["overlap_y"] > 0.0:
                severity = "error" if first.get("surface") == "floor" or second.get("surface") == "floor" else "warning"
                issue = {
                    "severity": severity,
                    "kind": "footprint_overlap",
                    "actor_labels": [first["actor_label"], second["actor_label"]],
                    "message": "Approximate prop footprints overlap before live collision validation.",
                    "overlap_cm": [gap["overlap_x"], gap["overlap_y"]],
                }
                issues.append(issue)
                first.setdefault("issues", []).append(issue)
                second.setdefault("issues", []).append(issue)
                if severity == "error":
                    first["valid"] = False
                    second["valid"] = False
            elif gap["gap_cm"] < pairwise_padding and first.get("surface") == "floor" and second.get("surface") == "floor":
                issues.append({
                    "severity": "warning",
                    "kind": "tight_pairwise_spacing",
                    "actor_labels": [first["actor_label"], second["actor_label"]],
                    "message": "Floor prop spacing is tighter than requested pairwise padding.",
                    "gap_cm": gap["gap_cm"],
                })

    for opening in opening_clearance:
        protected_check = {"footprint": opening.get("protected_footprint", {})}
        for check in actor_checks:
            if _actor_exempt_from_opening_clearance(check):
                continue
            gap = _aabb_gap(check, protected_check)
            if gap["overlap_x"] <= 0.0 or gap["overlap_y"] <= 0.0:
                continue
            severity = "error" if check.get("surface") == "floor" else "warning"
            blocker = {
                "actor_label": check.get("actor_label"),
                "surface": check.get("surface"),
                "overlap_cm": [gap["overlap_x"], gap["overlap_y"]],
                "severity": severity,
            }
            opening.setdefault("blocked_by", []).append(blocker)
            _add_preflight_issue(issues, check, {
                "severity": severity,
                "kind": "opening_clearance_blocked",
                "actor_label": check.get("actor_label"),
                "opening_label": opening.get("label"),
                "message": "Planned footprint overlaps the protected door/opening clearance zone.",
                "overlap_cm": blocker["overlap_cm"],
                "opening_protected_footprint": opening.get("protected_footprint", {}),
                "recommended_tool": "spatial_plan_composition_iteration",
            })

    actor_by_label = {
        str(check.get("actor_label") or ""): check
        for check in actor_checks
        if check.get("actor_label")
    }
    actor_by_id = {
        str(check.get("id") or ""): check
        for check in actor_checks
        if check.get("id")
    }
    for sightline in visual_sightlines:
        if sightline.get("status") != "obstructed_review":
            continue
        for blocker in sightline.get("blockers", []) if isinstance(sightline.get("blockers"), list) else []:
            if not isinstance(blocker, Mapping):
                continue
            blocker_check = actor_by_label.get(str(blocker.get("actor_label") or "")) or actor_by_id.get(str(blocker.get("id") or ""))
            _add_preflight_issue(issues, blocker_check, {
                "severity": "warning",
                "kind": "visual_sightline_obstructed",
                "actor_label": blocker.get("actor_label"),
                "opening_label": sightline.get("opening_label"),
                "target_actor_label": sightline.get("target_actor_label"),
                "target_zone": sightline.get("target_zone"),
                "message": "Planned tall floor prop intersects the entry-to-anchor visual sightline; review composition readability.",
                "distance_to_sightline_cm": blocker.get("distance_to_sightline_cm"),
                "corridor_width_cm": sightline.get("corridor_width_cm"),
                "recommended_tool": "spatial_plan_composition_iteration",
            })

    central_min_x = float(room["origin"][0]) - min_walkway_width / 2.0
    central_max_x = float(room["origin"][0]) + min_walkway_width / 2.0
    for check in actor_checks:
        if check.get("surface") != "floor":
            continue
        fp = check["footprint"]
        if fp["min"][0] < central_max_x and fp["max"][0] > central_min_x and fp["min"][1] < room_max[1] - 30.0 and fp["max"][1] > room_min[1] + 30.0:
            issues.append({
                "severity": "warning",
                "kind": "central_circulation_risk",
                "actor_label": check["actor_label"],
                "message": "Floor prop intersects the conservative central walkway band; review circulation in viewport.",
            })

    labels_by_name = {str(check.get("name", "")).lower(): check for check in actor_checks}
    kitchen_checks = [check for check in actor_checks if check.get("zone") == "kitchen" or check.get("inferred_zone") == "kitchen"]
    kitchen_names = " ".join(str(check.get("name", "")).lower() for check in kitchen_checks)
    if "sink" in kitchen_names and "counter" not in kitchen_names and "cabinet" not in kitchen_names:
        issues.append({
            "severity": "warning",
            "kind": "kitchen_sink_without_counter_context",
            "message": "Sink is planned without nearby counter/cabinet context.",
        })
    if "bar stool" in kitchen_names and "counter" not in kitchen_names:
        issues.append({
            "severity": "suggestion",
            "kind": "bar_stool_needs_counter_anchor",
            "message": "Bar stool reads better when anchored near a counter or island.",
        })
    _add_semantic_preflight_issues(issues, actor_checks, semantic_constraints)
    if include_suggestions:
        suggestions.extend([
            {"tool": "spatial_surface_probe", "reason": "Probe candidate support/floor points before final placement."},
            {"tool": "spatial_plan_layout_preflight_corrections", "reason": "Plan dry-run corrections for bounds, footprint overlap, and circulation issues before mutation."},
            {"tool": "spatial_preflight_candidate_clearance", "reason": "Compare planned candidate bounds against existing live actor bounds before mutation."},
            {"tool": "spatial_validate_placement", "reason": "Validate live surface contact and overlap after dry-run review."},
            {"tool": "spatial_plan_composition_iteration", "reason": "Use validation results to generate correction candidates."},
        ])
        if any(issue.get("kind") == "footprint_overlap" for issue in issues):
            suggestions.append({"action": "increase_spacing_or_move_to_adjacent_zone", "reason": "Approximate footprints overlap in preflight."})
        if any(issue.get("kind") == "opening_clearance_blocked" for issue in issues):
            suggestions.append({"tool": "spatial_plan_composition_iteration", "reason": "Move planned props out of protected door/opening clearance before mutation."})
        if any(issue.get("kind") == "visual_sightline_obstructed" for issue in issues):
            suggestions.append({"tool": "spatial_plan_composition_iteration", "reason": "Move or rotate tall blockers so entry-to-anchor sightlines read clearly."})
        if any(issue.get("kind") in {"semantic_bedroom_bedside_spacing", "semantic_bedroom_storage_spacing"} for issue in issues):
            suggestions.append({"tool": "spatial_plan_composition_iteration", "reason": "Recompose bedroom furniture around the bed while preserving access clearance."})
        if any(issue.get("kind") == "semantic_hallway_clearance_review" for issue in issues):
            suggestions.append({"tool": "spatial_plan_composition_iteration", "reason": "Replace wide hallway floor props or move them against a wall to preserve linear circulation."})
        if labels_by_name and not any("rug" in name for name in labels_by_name):
            suggestions.append({"action": "consider_rug_or_visual_anchor", "reason": "A living-area rug can help compose seating/coffee-table groupings when appropriate."})

    error_count = sum(1 for issue in issues if issue.get("severity") == "error")
    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    suggestion_count = sum(1 for issue in issues if issue.get("severity") == "suggestion")
    status = "blocked_by_preflight" if error_count else ("needs_review" if warning_count else "pass")
    probe_points = _merge_vector_lists([check["location"] for check in actor_checks if check.get("location")], maximum=32)
    actors = [str(check.get("actor_label") or "") for check in actor_checks if check.get("actor_label")]
    interaction_clearance = [
        {
            "id": check.get("id"),
            "actor_label": check.get("actor_label"),
            **dict(check.get("interaction_clearance") or {}),
        }
        for check in actor_checks
        if isinstance(check.get("interaction_clearance"), Mapping) and check.get("interaction_clearance")
    ]
    return {
        "schema": LAYOUT_PREFLIGHT_SCHEMA,
        "status": status,
        "issue_count": len(issues),
        "error_count": error_count,
        "warning_count": warning_count,
        "suggestion_count": suggestion_count,
        "room": room,
        "actor_count": len(actor_checks),
        "actor_checks": actor_checks,
        "semantic_constraints": semantic_constraints,
        "interaction_clearance": interaction_clearance,
        "interaction_clearance_count": len(interaction_clearance),
        "opening_clearance": opening_clearance,
        "opening_clearance_count": len(opening_clearance),
        "blocked_opening_count": sum(1 for opening in opening_clearance if opening.get("blocked_by")),
        "visual_sightlines": visual_sightlines,
        "visual_sightline_count": len(visual_sightlines),
        "obstructed_sightline_count": sum(1 for sightline in visual_sightlines if sightline.get("status") == "obstructed_review"),
        "issues": issues,
        "pairwise_clearance": pairwise_clearance,
        "suggestions": suggestions,
        "surface_probe_handoff": {
            "tool": "spatial_surface_probe",
            "arguments": {"points": probe_points, "placement_offset": 0.0, "include_handoff": True},
            "enabled": bool(probe_points),
        },
        "validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": actors,
                "surface_tolerance": 15.0,
                "clearance_padding": clearance_padding,
                "include_evidence_handoff": True,
            },
            "enabled": bool(actors),
        },
        "candidate_clearance_handoff": {
            "tool": "spatial_preflight_candidate_clearance",
            "arguments": {
                "composition_plan_json": "<COMPOSITION_PLAN_JSON>",
                "room_analysis_json": "<OPTIONAL_SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
                "clearance_padding": clearance_padding,
            },
            "enabled": bool(actor_checks),
        },
        "layout_correction_handoff": {
            "tool": "spatial_plan_layout_preflight_corrections",
            "arguments": {
                "composition_plan_json": "<COMPOSITION_PLAN_JSON>",
                "layout_preflight_json": "<SPATIAL_PREFLIGHT_INTERIOR_LAYOUT_RESULT_JSON>",
                "correction_step_cm": max(25.0, pairwise_padding + 12.0),
                "boundary_margin_cm": clearance_padding,
                "pairwise_padding": pairwise_padding,
                "min_walkway_width": min_walkway_width,
            },
            "enabled": bool(error_count or warning_count),
        },
        "iteration_handoff": {
            "tool": "spatial_plan_composition_iteration",
            "arguments": {
                "composition_plan_json": "<COMPOSITION_PLAN_JSON>",
                "validation_result_json": "<SPATIAL_VALIDATE_PLACEMENT_RESULT_JSON>",
            },
        },
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is Ghost-owned approximate geometry preflight and does not copy Epic SceneTools source.",
                "Live Unreal traces, collisions, and viewport review remain authoritative for final placement.",
            ],
        },
    }


def _candidate_clearance_records(
    *,
    composition_plan: Mapping[str, Any],
    room_analysis: Mapping[str, Any],
    clearance_padding: float,
) -> Dict[str, Any]:
    room = _room_context_for_preflight(composition_plan=composition_plan, room_analysis=room_analysis)
    actor_checks = _preflight_actor_checks(
        composition_plan=composition_plan,
        room=room,
        clearance_padding=clearance_padding,
    )
    steps_by_id = _placement_steps_by_id(composition_plan)
    candidates: List[Dict[str, Any]] = []
    for check in actor_checks:
        if not isinstance(check, Mapping):
            continue
        location = _optional_vector3(check.get("location"))
        size = _size_vector(check.get("approx_size_cm"))
        footprint = check.get("footprint") if isinstance(check.get("footprint"), Mapping) else {}
        if location is None or not size or not footprint:
            candidates.append({
                "id": str(check.get("id") or ""),
                "actor_label": str(check.get("actor_label") or ""),
                "valid": False,
                "issues": list(check.get("issues", [])) if isinstance(check.get("issues"), list) else [],
                "status": "missing_candidate_bounds",
            })
            continue
        step = steps_by_id.get(str(check.get("id") or ""), {})
        arguments = _placement_step_arguments(step)
        vertical_padding = clearance_padding if str(check.get("surface") or "") == "floor" else min(clearance_padding, 6.0)
        min_xy = list(footprint.get("min") or [location[0], location[1]])
        max_xy = list(footprint.get("max") or [location[0], location[1]])
        candidate = {
            "id": str(check.get("id") or ""),
            "actor_label": str(check.get("actor_label") or ""),
            "asset_path": str(arguments.get("asset_path") or ""),
            "name": str(check.get("name") or check.get("id") or ""),
            "zone": str(check.get("zone") or ""),
            "surface": str(check.get("surface") or ""),
            "location": _rounded_vector(location),
            "approx_size_cm": _rounded_vector(size),
            "bounds": {
                "min": [round(float(min_xy[0]), 3), round(float(min_xy[1]), 3), round(float(location[2]) - vertical_padding, 3)],
                "max": [round(float(max_xy[0]), 3), round(float(max_xy[1]), 3), round(float(location[2]) + float(size[2]) + vertical_padding, 3)],
            },
            "footprint": dict(footprint),
            "room_bounds_margin_cm": dict(check.get("room_bounds_margin_cm") or {}),
            "placement_source": str(check.get("placement_source") or ""),
            "valid": bool(check.get("valid", True)),
            "issues": list(check.get("issues", [])) if isinstance(check.get("issues"), list) else [],
        }
        candidates.append(candidate)
    return {"room": room, "candidates": candidates}


def _candidate_clearance_code(
    *,
    candidates: Sequence[Mapping[str, Any]],
    room: Mapping[str, Any],
    actor_query: str,
    class_filter: str,
    tag_filter: str,
    include_hidden: bool,
    ignore_actor_labels: Sequence[str],
    clearance_padding: float,
    limit: int,
) -> str:
    candidate_json = json.dumps(list(candidates), sort_keys=True)
    room_json = json.dumps(dict(room), sort_keys=True)
    ignored_json = json.dumps(list(ignore_actor_labels), sort_keys=True)
    return textwrap.dedent(
        f"""\
        import json
        import unreal

        candidates = json.loads({candidate_json!r})
        room = json.loads({room_json!r})
        ignore_actor_labels = set(str(value).lower() for value in json.loads({ignored_json!r}))
        actor_query = {str(actor_query or '').strip().lower()!r}
        class_filter = {str(class_filter or '').strip().lower()!r}
        tag_filter = {str(tag_filter or '').strip().lower()!r}
        include_hidden = {bool(include_hidden)!r}
        clearance_padding = max(0.0, float({float(clearance_padding)!r}))
        limit = max(1, int({int(limit)!r}))

        _result["schema"] = {CANDIDATE_CLEARANCE_SCHEMA!r}
        _result["method"] = "axis_aligned_candidate_bounds_vs_live_actor_bounds"
        _result["clearance_padding"] = clearance_padding
        _result["room"] = room
        _result["candidate_count"] = len(candidates)
        _result["candidates"] = []
        _result["existing_actor_count"] = 0
        _result["pairwise_candidate_overlaps"] = []

        def _safe_text(value):
            try:
                return str(value)
            except Exception:
                return ""

        def _vec_dict(value):
            if value is None:
                return None
            return {{
                "x": float(getattr(value, "x", 0.0)),
                "y": float(getattr(value, "y", 0.0)),
                "z": float(getattr(value, "z", 0.0)),
            }}

        def _actor_label(actor):
            try:
                label = actor.get_actor_label()
                if label:
                    return _safe_text(label)
            except Exception:
                pass
            try:
                return _safe_text(actor.get_name())
            except Exception:
                return _safe_text(actor)

        def _class_name(actor):
            try:
                return actor.get_class().get_name()
            except Exception:
                return actor.__class__.__name__

        def _object_path(obj):
            try:
                return obj.get_path_name()
            except Exception:
                return _safe_text(obj)

        def _hidden(actor):
            for method_name in ("is_hidden_ed", "is_actor_hidden_in_game", "is_hidden"):
                method = getattr(actor, method_name, None)
                if callable(method):
                    try:
                        return bool(method())
                    except Exception:
                        pass
            return False

        def _tags(actor):
            values = []
            for tag in getattr(actor, "tags", []) or []:
                values.append(_safe_text(tag))
            return values

        def _actor_matches(actor):
            label = _actor_label(actor)
            lowered_label = label.lower()
            if lowered_label in ignore_actor_labels:
                return False
            if not include_hidden and _hidden(actor):
                return False
            class_name = _class_name(actor)
            path = _object_path(actor)
            text = " ".join([label, class_name, path, " ".join(_tags(actor))]).lower()
            if actor_query and actor_query not in text:
                return False
            if class_filter and class_filter not in class_name.lower():
                return False
            if tag_filter and tag_filter not in " ".join(_tags(actor)).lower():
                return False
            return True

        def _actor_bounds(actor):
            try:
                origin, extent = actor.get_actor_bounds(False, False)
            except TypeError:
                try:
                    origin, extent = actor.get_actor_bounds(False)
                except Exception:
                    return None
            except Exception:
                return None
            origin_data = _vec_dict(origin)
            extent_data = _vec_dict(extent)
            if origin_data is None or extent_data is None:
                return None
            return {{
                "min": [
                    origin_data["x"] - abs(extent_data["x"]),
                    origin_data["y"] - abs(extent_data["y"]),
                    origin_data["z"] - abs(extent_data["z"]),
                ],
                "max": [
                    origin_data["x"] + abs(extent_data["x"]),
                    origin_data["y"] + abs(extent_data["y"]),
                    origin_data["z"] + abs(extent_data["z"]),
                ],
                "center": [origin_data["x"], origin_data["y"], origin_data["z"]],
                "extent": [abs(extent_data["x"]), abs(extent_data["y"]), abs(extent_data["z"])],
            }}

        def _actor_descriptor(actor, bounds):
            return {{
                "label": _actor_label(actor),
                "class": _class_name(actor),
                "path": _object_path(actor),
                "tags": _tags(actor),
                "bounds": {{
                    "min": [round(float(value), 3) for value in bounds["min"]],
                    "max": [round(float(value), 3) for value in bounds["max"]],
                    "center": [round(float(value), 3) for value in bounds["center"]],
                    "extent": [round(float(value), 3) for value in bounds["extent"]],
                }},
            }}

        def _bounds_values(raw):
            if not isinstance(raw, dict):
                return None
            min_v = raw.get("min")
            max_v = raw.get("max")
            if not isinstance(min_v, list) or not isinstance(max_v, list) or len(min_v) < 3 or len(max_v) < 3:
                return None
            try:
                return ([float(min_v[0]), float(min_v[1]), float(min_v[2])], [float(max_v[0]), float(max_v[1]), float(max_v[2])])
            except Exception:
                return None

        def _aabb_overlap(a_raw, b_raw):
            a = _bounds_values(a_raw)
            b = _bounds_values(b_raw)
            if a is None or b is None:
                return None
            a_min, a_max = a
            b_min, b_max = b
            overlaps = [
                min(a_max[axis], b_max[axis]) - max(a_min[axis], b_min[axis])
                for axis in range(3)
            ]
            if all(value > 0.0 for value in overlaps):
                return {{
                    "overlap_cm": [round(float(value), 3) for value in overlaps],
                    "volume_cm3": round(float(overlaps[0] * overlaps[1] * overlaps[2]), 3),
                }}
            return None

        def _get_actors():
            actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            if actor_subsystem is not None:
                return list(actor_subsystem.get_all_level_actors() or [])
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "get_all_level_actors"):
                return list(editor_level_library.get_all_level_actors() or [])
            return []

        candidate_labels = set(str(item.get("actor_label", "")).lower() for item in candidates)
        ignore_actor_labels.update(candidate_labels)
        existing = []
        for actor in _get_actors():
            if not _actor_matches(actor):
                continue
            bounds = _actor_bounds(actor)
            if bounds is None:
                continue
            existing.append((actor, bounds))
            if len(existing) >= limit:
                break
        _result["existing_actor_count"] = len(existing)

        blocked_count = 0
        needs_review_count = 0
        for candidate in candidates:
            candidate_bounds = candidate.get("bounds") if isinstance(candidate.get("bounds"), dict) else {{}}
            overlaps = []
            for actor, actor_bounds in existing:
                overlap = _aabb_overlap(candidate_bounds, actor_bounds)
                if overlap is None:
                    continue
                record = _actor_descriptor(actor, actor_bounds)
                record.update(overlap)
                overlaps.append(record)
                if len(overlaps) >= 20:
                    break
            local_issues = list(candidate.get("issues") or []) if isinstance(candidate.get("issues"), list) else []
            if overlaps:
                status = "blocked_by_existing_overlap"
                blocked_count += 1
            elif any((issue.get("severity") == "error") for issue in local_issues if isinstance(issue, dict)):
                status = "blocked_by_candidate_preflight"
                blocked_count += 1
            elif local_issues:
                status = "needs_review"
                needs_review_count += 1
            else:
                status = "clear"
            item = dict(candidate)
            item["status"] = status
            item["existing_overlap_count"] = len(overlaps)
            item["existing_overlaps"] = overlaps
            _result["candidates"].append(item)

        for first_index, first in enumerate(candidates):
            for second in candidates[first_index + 1:]:
                overlap = _aabb_overlap(first.get("bounds", {{}}), second.get("bounds", {{}}))
                if overlap is None:
                    continue
                _result["pairwise_candidate_overlaps"].append({{
                    "a": first.get("actor_label") or first.get("id"),
                    "b": second.get("actor_label") or second.get("id"),
                    **overlap,
                }})

        if _result["pairwise_candidate_overlaps"]:
            needs_review_count += len(_result["pairwise_candidate_overlaps"])

        _result["blocked_count"] = blocked_count
        _result["needs_review_count"] = needs_review_count
        if blocked_count:
            _result["status"] = "blocked_by_clearance"
        elif needs_review_count:
            _result["status"] = "needs_review"
        else:
            _result["status"] = "pass"
        _result["iteration_handoff"] = {{
            "tool": "spatial_plan_composition_iteration",
            "arguments": {{
                "composition_plan_json": "<COMPOSITION_PLAN_JSON>",
                "validation_result_json": "<SPATIAL_VALIDATE_PLACEMENT_OR_CANDIDATE_CLEARANCE_RESULT_JSON>",
            }},
            "enabled": bool(blocked_count or needs_review_count),
        }}
        _result["layout_preflight_handoff"] = {{
            "tool": "spatial_preflight_interior_layout",
            "arguments": {{
                "composition_plan_json": "<COMPOSITION_PLAN_JSON>",
                "clearance_padding": clearance_padding,
            }},
        }}
        _result["apply_handoff"] = {{
            "tool": "spatial_apply_composition_plan",
            "arguments": {{
                "composition_plan_json": "<COMPOSITION_PLAN_JSON>",
                "dry_run": True,
                "allow_mutation": False,
            }},
            "enabled": _result["status"] == "pass",
        }}
        _result["legal_review"] = {{
            "requires_review": False,
            "notes": [
                "This is a Ghost-owned read-only clearance preflight over planned candidate bounds and live actor bounds.",
                "It does not perform physics simulation or copy Epic native SceneTools implementation code.",
            ],
        }}
        """
    )


def _optional_vector3(value: Any) -> Optional[List[float]]:
    if value is None:
        return None
    if isinstance(value, Mapping):
        keys = {str(key).lower(): key for key in value.keys()}
        if {"x", "y", "z"}.issubset(keys):
            try:
                return [
                    float(value[keys["x"]]),
                    float(value[keys["y"]]),
                    float(value[keys["z"]]),
                ]
            except Exception:
                return None
        if isinstance(value.get("origin"), Mapping):
            return _optional_vector3(value.get("origin"))
    try:
        return _vector3(value, "vector")
    except Exception:
        return None


def _rounded_vector(value: Sequence[float]) -> List[float]:
    return [round(float(component), 3) for component in value[:3]]


def _numeric_value(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def _actor_label_from_validation(validation: Mapping[str, Any]) -> str:
    actor = validation.get("actor") if isinstance(validation.get("actor"), Mapping) else {}
    for key in ("label", "name", "path"):
        text = str(actor.get(key) or validation.get(key) or "").strip()
        if text:
            return text[:128]
    return "UnknownActor"


def _validation_actor_location(validation: Mapping[str, Any]) -> Optional[List[float]]:
    actor = validation.get("actor") if isinstance(validation.get("actor"), Mapping) else {}
    return (
        _optional_vector3(actor.get("location"))
        or _optional_vector3((actor.get("bounds") or {}).get("origin") if isinstance(actor.get("bounds"), Mapping) else None)
        or _optional_vector3(validation.get("probe_location"))
    )


def _composition_context_by_actor(composition_plan: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    context: Dict[str, Dict[str, Any]] = {}
    for prop in composition_plan.get("props", []) if isinstance(composition_plan.get("props"), list) else []:
        if not isinstance(prop, Mapping):
            continue
        placement = prop.get("placement") if isinstance(prop.get("placement"), Mapping) else {}
        label = str(placement.get("actor_label") or "").strip()
        if label:
            context.setdefault(label, {})["prop"] = dict(prop)
    for step in composition_plan.get("placement_steps", []) if isinstance(composition_plan.get("placement_steps"), list) else []:
        if not isinstance(step, Mapping):
            continue
        arguments = step.get("arguments") if isinstance(step.get("arguments"), Mapping) else {}
        label = str(arguments.get("actor_label") or step.get("actor_label") or "").strip()
        if label:
            context.setdefault(label, {})["placement_step"] = dict(step)
    return context


def _placement_step_arguments(step: Mapping[str, Any]) -> Dict[str, Any]:
    arguments = step.get("arguments") if isinstance(step.get("arguments"), Mapping) else {}
    return dict(arguments)


def _spatial_fit_reviews_by_key(composition_plan: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    reviews: List[Dict[str, Any]] = []
    source = composition_plan.get("spatial_fit_reviews")
    for review in source if isinstance(source, list) else []:
        if isinstance(review, Mapping):
            reviews.append(dict(review))

    for prop in composition_plan.get("props", []) if isinstance(composition_plan.get("props"), list) else []:
        if isinstance(prop, Mapping) and isinstance(prop.get("spatial_fit_review"), Mapping):
            reviews.append(dict(prop["spatial_fit_review"]))

    for step_key in ("placement_steps", "all_placement_steps"):
        for step in composition_plan.get(step_key, []) if isinstance(composition_plan.get(step_key), list) else []:
            if not isinstance(step, Mapping):
                continue
            if isinstance(step.get("spatial_fit_review"), Mapping):
                reviews.append(dict(step["spatial_fit_review"]))
            binding = step.get("asset_binding") if isinstance(step.get("asset_binding"), Mapping) else {}
            if isinstance(binding.get("spatial_fit_review"), Mapping):
                reviews.append(dict(binding["spatial_fit_review"]))

    lookup: Dict[str, Dict[str, Any]] = {}
    for review in reviews:
        keys = _binding_keys(review.get("id"), review.get("actor_label"), review.get("asset_path"), review.get("prop_name"))
        for key in keys:
            lookup.setdefault(key, review)
    return lookup


def _spatial_fit_review_for_step(
    *,
    step_id: str,
    actor_label: str,
    asset_path: str,
    step: Mapping[str, Any],
    reviews_by_key: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    direct = step.get("spatial_fit_review")
    if isinstance(direct, Mapping):
        return dict(direct)
    binding = step.get("asset_binding") if isinstance(step.get("asset_binding"), Mapping) else {}
    if isinstance(binding.get("spatial_fit_review"), Mapping):
        return dict(binding["spatial_fit_review"])
    for key in _binding_keys(step_id, actor_label, asset_path):
        review = reviews_by_key.get(key)
        if review:
            return dict(review)
    return {}


def _spatial_fit_review_blocks_placement(review: Mapping[str, Any]) -> bool:
    if not review:
        return False
    return _asset_scale_review_blocking_status(str(review.get("status") or "").strip())


def _layout_preflight_from_json(value: str) -> Dict[str, Any]:
    parsed = _json_object_from_text(value, "layout_preflight_json")
    if not parsed:
        return {}
    outputs = parsed.get("outputs") if parsed.get("schema") == SPATIAL_RESULT_SCHEMA else parsed
    if not isinstance(outputs, Mapping):
        raise ValueError("layout_preflight_json.outputs must be an object")
    if outputs.get("schema") != LAYOUT_PREFLIGHT_SCHEMA:
        raise ValueError(f"layout_preflight_json must have schema {LAYOUT_PREFLIGHT_SCHEMA}")
    return dict(outputs)


def _layout_preflight_correction_ready_status(status: str) -> bool:
    return str(status or "").strip() in {
        "ready_for_corrected_preflight",
        "no_layout_corrections_needed",
        "layout_issues_need_review",
    }


def _layout_identity_keys(*values: Any) -> List[str]:
    keys: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        candidates = [text, text.lower(), _safe_asset_stem(text, "Prop").lower()]
        for candidate in candidates:
            if candidate and candidate not in keys:
                keys.append(candidate)
    return keys


def _layout_actor_check_lookup(layout_preflight: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    lookup: Dict[str, Dict[str, Any]] = {}
    checks = layout_preflight.get("actor_checks") if isinstance(layout_preflight.get("actor_checks"), list) else []
    for check in checks:
        if not isinstance(check, Mapping):
            continue
        clean = dict(check)
        for key in _layout_identity_keys(check.get("id"), check.get("actor_label"), check.get("name")):
            lookup.setdefault(key, clean)
    return lookup


def _layout_step_index_lookup(composition_plan: Mapping[str, Any]) -> Dict[str, int]:
    lookup: Dict[str, int] = {}
    steps = composition_plan.get("placement_steps") if isinstance(composition_plan.get("placement_steps"), list) else []
    if not steps and isinstance(composition_plan.get("all_placement_steps"), list):
        steps = composition_plan.get("all_placement_steps")
    for index, step in enumerate(steps):
        if not isinstance(step, Mapping):
            continue
        args = _placement_step_arguments(step)
        for key in _layout_identity_keys(step.get("id"), args.get("actor_label"), step.get("actor_label")):
            lookup.setdefault(key, index)
    return lookup


def _layout_check_for_issue(
    issue: Mapping[str, Any],
    actor_lookup: Mapping[str, Dict[str, Any]],
    *,
    index: int = 0,
) -> Dict[str, Any]:
    labels = issue.get("actor_labels") if isinstance(issue.get("actor_labels"), list) else []
    value = issue.get("actor_label") or (labels[index] if index < len(labels) else "")
    for key in _layout_identity_keys(value):
        if key in actor_lookup:
            return dict(actor_lookup[key])
    return {}


def _layout_step_index_for_check(
    check: Mapping[str, Any],
    step_lookup: Mapping[str, int],
) -> Optional[int]:
    for key in _layout_identity_keys(check.get("id"), check.get("actor_label"), check.get("name")):
        if key in step_lookup:
            return int(step_lookup[key])
    return None


def _layout_step_id_and_label(step: Mapping[str, Any], index: int) -> tuple[str, str]:
    args = _placement_step_arguments(step)
    step_id = str(step.get("id") or args.get("actor_label") or f"step_{index}").strip()
    label = str(args.get("actor_label") or step.get("actor_label") or step_id).strip()
    return step_id, label


def _layout_current_location(
    *,
    index: int,
    step: Mapping[str, Any],
    check: Mapping[str, Any],
    proposed_locations: Mapping[int, List[float]],
) -> Optional[List[float]]:
    if index in proposed_locations:
        return list(proposed_locations[index])
    args = _placement_step_arguments(step)
    return _optional_vector3(args.get("location")) or _optional_vector3(check.get("location"))


def _layout_room_bounds(room: Mapping[str, Any]) -> tuple[Optional[List[float]], Optional[List[float]]]:
    bounds = room.get("bounds") if isinstance(room.get("bounds"), Mapping) else {}
    room_min = _optional_vector3(bounds.get("min"))
    room_max = _optional_vector3(bounds.get("max"))
    return room_min, room_max


def _layout_clamped_location_for_actor(
    *,
    location: Sequence[float],
    size: Sequence[float],
    surface: str,
    room: Mapping[str, Any],
    boundary_margin_cm: float,
) -> tuple[Optional[List[float]], str]:
    room_min, room_max = _layout_room_bounds(room)
    if room_min is None or room_max is None:
        return None, "room bounds are missing from layout_preflight_json"
    half_x = max(0.5, float(size[0]) / 2.0)
    half_y = max(0.5, float(size[1]) / 2.0)
    min_x = float(room_min[0]) + half_x + boundary_margin_cm
    max_x = float(room_max[0]) - half_x - boundary_margin_cm
    min_y = float(room_min[1]) + half_y + boundary_margin_cm
    max_y = float(room_max[1]) - half_y - boundary_margin_cm
    if min_x > max_x or min_y > max_y:
        return None, "approximate footprint cannot fit inside room bounds with the requested boundary margin"
    corrected = [
        round(min(max(float(location[0]), min_x), max_x), 3),
        round(min(max(float(location[1]), min_y), max_y), 3),
        round(float(location[2]), 3),
    ]
    if str(surface or "").lower() == "floor":
        corrected[2] = round(float(room_min[2]), 3)
    return corrected, ""


def _layout_overlap_delta(
    *,
    first_location: Sequence[float],
    second_location: Sequence[float],
    overlap_cm: Sequence[float],
    pairwise_padding: float,
    correction_step_cm: float,
    first_label: str,
    second_label: str,
) -> List[float]:
    overlap_x = float(overlap_cm[0]) if len(overlap_cm) > 0 else 0.0
    overlap_y = float(overlap_cm[1]) if len(overlap_cm) > 1 else 0.0
    dx = float(second_location[0]) - float(first_location[0])
    dy = float(second_location[1]) - float(first_location[1])
    if abs(dx) < 0.001 and abs(dy) < 0.001:
        dx = 1.0 if str(second_label) >= str(first_label) else -1.0
        dy = 0.0
    if overlap_x <= overlap_y:
        direction = 1.0 if dx >= 0.0 else -1.0
        return [round(direction * max(correction_step_cm, overlap_x + pairwise_padding), 3), 0.0, 0.0]
    direction = 1.0 if dy >= 0.0 else -1.0
    return [0.0, round(direction * max(correction_step_cm, overlap_y + pairwise_padding), 3), 0.0]


def _layout_circulation_location(
    *,
    location: Sequence[float],
    size: Sequence[float],
    surface: str,
    room: Mapping[str, Any],
    min_walkway_width: float,
    boundary_margin_cm: float,
) -> Optional[List[float]]:
    if str(surface or "").lower() != "floor":
        return None
    room_min, room_max = _layout_room_bounds(room)
    if room_min is None or room_max is None:
        return None
    origin = _optional_vector3(room.get("origin")) or [
        (float(room_min[0]) + float(room_max[0])) / 2.0,
        (float(room_min[1]) + float(room_max[1])) / 2.0,
        float(room_min[2]),
    ]
    half_width = max(0.0, min_walkway_width) / 2.0
    current_x = float(location[0])
    desired_x = (
        float(origin[0]) + half_width + float(size[0]) / 2.0 + boundary_margin_cm
        if current_x >= float(origin[0])
        else float(origin[0]) - half_width - float(size[0]) / 2.0 - boundary_margin_cm
    )
    candidate = [desired_x, float(location[1]), float(location[2])]
    corrected, _reason = _layout_clamped_location_for_actor(
        location=candidate,
        size=size,
        surface=surface,
        room=room,
        boundary_margin_cm=boundary_margin_cm,
    )
    if corrected is None:
        return None
    if corrected[:2] == _rounded_vector(location)[:2]:
        return None
    return corrected


def _layout_correction_record(
    *,
    correction_id: str,
    step_id: str,
    actor_label: str,
    issue: Mapping[str, Any],
    original_location: Sequence[float],
    corrected_location: Sequence[float],
    action: str,
    reason: str,
) -> Dict[str, Any]:
    return {
        "correction_id": correction_id,
        "id": step_id,
        "actor_label": actor_label,
        "issue_kind": str(issue.get("kind") or ""),
        "issue_severity": str(issue.get("severity") or ""),
        "action": action,
        "reason": reason,
        "original_location": _rounded_vector(original_location),
        "corrected_location": _rounded_vector(corrected_location),
        "location_delta_cm": _rounded_vector([
            float(corrected_location[axis]) - float(original_location[axis])
            for axis in range(3)
        ]),
        "dry_run_only": True,
    }


def _layout_review_action_for_issue(issue: Mapping[str, Any]) -> Dict[str, Any]:
    kind = str(issue.get("kind") or "")
    if kind in {"support_surface_suspicious", "semantic_support_contact_unresolved", "wall_mount_source_missing", "semantic_wall_anchor_unresolved"}:
        return {
            "issue_kind": kind,
            "actor_label": issue.get("actor_label"),
            "tool": "spatial_plan_support_surface_anchors",
            "reason": "Support or wall contact needs room-analysis surface anchoring before mutation.",
        }
    if kind in {"semantic_counter_adjacency_gap", "semantic_kitchen_work_triangle_review", "semantic_living_group_spacing", "visual_sightline_obstructed"}:
        return {
            "issue_kind": kind,
            "actor_labels": issue.get("actor_labels", []),
            "actor_label": issue.get("actor_label"),
            "tool": "spatial_plan_composition_iteration",
            "reason": "Semantic composition intent needs a human-reviewed layout iteration rather than an automatic local nudge.",
        }
    if kind == "opening_clearance_blocked":
        return {
            "issue_kind": kind,
            "actor_label": issue.get("actor_label"),
            "tool": "spatial_plan_composition_iteration",
            "reason": "Protected door/opening clearance should be preserved by choosing a new layout position.",
        }
    if kind in {"floor_contact_suspicious"}:
        return {
            "issue_kind": kind,
            "actor_label": issue.get("actor_label"),
            "tool": "spatial_surface_probe",
            "reason": "Floor contact should be re-grounded from live trace evidence.",
        }
    return {
        "issue_kind": kind,
        "actor_label": issue.get("actor_label"),
        "actor_labels": issue.get("actor_labels", []),
        "tool": "spatial_preflight_interior_layout",
        "reason": "Review-only issue has no deterministic local transform correction.",
    }


def _step_after_layout_preflight_corrections(
    step: Mapping[str, Any],
    corrections: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    updated = dict(step)
    if not corrections:
        return updated
    final = corrections[-1]
    arguments = _placement_step_arguments(updated)
    arguments["location"] = list(final.get("corrected_location") or arguments.get("location") or [0.0, 0.0, 0.0])
    arguments["dry_run"] = True
    arguments["allow_mutation"] = False
    source = str(arguments.get("placement_source") or "").strip()
    if "layout_preflight_correction" not in source:
        arguments["placement_source"] = "layout_preflight_correction" if not source else f"{source}+layout_preflight_correction"
    arguments["layout_preflight_correction"] = {
        "schema": LAYOUT_PREFLIGHT_CORRECTION_SCHEMA,
        "correction_ids": [item.get("correction_id") for item in corrections],
        "issue_kinds": _merge_unique([str(item.get("issue_kind") or "") for item in corrections]),
    }
    updated["arguments"] = arguments
    updated["layout_preflight_corrections"] = [dict(item) for item in corrections]
    return updated


def _props_after_layout_preflight_corrections(
    *,
    composition_plan: Mapping[str, Any],
    corrections_by_id: Mapping[str, Sequence[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    updated_props: List[Dict[str, Any]] = []
    for prop in composition_plan.get("props", []) if isinstance(composition_plan.get("props"), list) else []:
        if not isinstance(prop, Mapping):
            continue
        updated = dict(prop)
        prop_id = str(updated.get("id") or updated.get("detected_item_id") or "").strip()
        corrections = list(corrections_by_id.get(prop_id, []))
        if corrections:
            final = corrections[-1]
            placement = dict(updated.get("placement") or {}) if isinstance(updated.get("placement"), Mapping) else {}
            placement.update({
                "location": list(final.get("corrected_location") or placement.get("location") or []),
                "source": "layout_preflight_correction",
            })
            updated["placement"] = placement
            updated["layout_preflight_corrections"] = [dict(item) for item in corrections]
        updated_props.append(updated)
    return updated_props


def _plan_layout_preflight_corrections(
    *,
    composition_plan: Mapping[str, Any],
    layout_preflight: Mapping[str, Any],
    correction_step_cm: float,
    boundary_margin_cm: float,
    pairwise_padding: float,
    min_walkway_width: float,
    include_updated_plan: bool,
    limit: int,
) -> Dict[str, Any]:
    steps = composition_plan.get("placement_steps") if isinstance(composition_plan.get("placement_steps"), list) else []
    if not steps and isinstance(composition_plan.get("all_placement_steps"), list):
        steps = composition_plan.get("all_placement_steps")
    room = layout_preflight.get("room") if isinstance(layout_preflight.get("room"), Mapping) else _room_context_for_preflight(composition_plan=composition_plan, room_analysis={})
    issues = [dict(issue) for issue in layout_preflight.get("issues", []) if isinstance(issue, Mapping)]
    actor_lookup = _layout_actor_check_lookup(layout_preflight)
    step_lookup = _layout_step_index_lookup({"placement_steps": steps})
    proposed_locations: Dict[int, List[float]] = {}
    corrections_by_index: Dict[int, List[Dict[str, Any]]] = {}
    corrections: List[Dict[str, Any]] = []
    blockers: List[Dict[str, Any]] = []
    review_actions: List[Dict[str, Any]] = []
    uncorrected_issues: List[Dict[str, Any]] = []

    def add_correction(index: int, record: Dict[str, Any]) -> None:
        proposed_locations[index] = list(record.get("corrected_location") or proposed_locations.get(index) or [])
        corrections_by_index.setdefault(index, []).append(record)
        corrections.append(record)

    for issue_index, issue in enumerate(issues[:limit]):
        kind = str(issue.get("kind") or "")
        if kind == "outside_room_bounds":
            check = _layout_check_for_issue(issue, actor_lookup)
            step_index = _layout_step_index_for_check(check, step_lookup) if check else None
            if step_index is None or step_index >= len(steps):
                blockers.append({"issue_kind": kind, "actor_label": issue.get("actor_label"), "reason": "No placement step matched the out-of-bounds actor."})
                continue
            step = steps[step_index]
            step_id, actor_label = _layout_step_id_and_label(step, step_index)
            location = _layout_current_location(index=step_index, step=step, check=check, proposed_locations=proposed_locations)
            size = _optional_vector3(check.get("approx_size_cm"))
            if location is None or size is None:
                blockers.append({"issue_kind": kind, "actor_label": actor_label, "reason": "Out-of-bounds actor is missing usable location or approximate size."})
                continue
            corrected, reason = _layout_clamped_location_for_actor(
                location=location,
                size=size,
                surface=str(check.get("surface") or "floor"),
                room=room,
                boundary_margin_cm=boundary_margin_cm,
            )
            if corrected is None:
                blockers.append({"issue_kind": kind, "id": step_id, "actor_label": actor_label, "reason": reason, "recommended_next_tools": ["spatial_plan_asset_scale_corrections", "spatial_plan_interior_composition"]})
                continue
            if _rounded_vector(corrected) != _rounded_vector(location):
                add_correction(step_index, _layout_correction_record(
                    correction_id=f"{step_id}_bounds_{issue_index}",
                    step_id=step_id,
                    actor_label=actor_label,
                    issue=issue,
                    original_location=location,
                    corrected_location=corrected,
                    action="clamp_inside_room_bounds",
                    reason="Actor footprint was clamped inside inferred room bounds before live mutation.",
                ))
            continue

        if kind == "footprint_overlap":
            first_check = _layout_check_for_issue(issue, actor_lookup, index=0)
            second_check = _layout_check_for_issue(issue, actor_lookup, index=1)
            first_index = _layout_step_index_for_check(first_check, step_lookup) if first_check else None
            second_index = _layout_step_index_for_check(second_check, step_lookup) if second_check else None
            if first_index is None or second_index is None or first_index >= len(steps) or second_index >= len(steps):
                blockers.append({"issue_kind": kind, "actor_labels": issue.get("actor_labels", []), "reason": "No placement steps matched both overlapping actors."})
                continue
            first_step = steps[first_index]
            second_step = steps[second_index]
            first_id, first_label = _layout_step_id_and_label(first_step, first_index)
            second_id, second_label = _layout_step_id_and_label(second_step, second_index)
            first_location = _layout_current_location(index=first_index, step=first_step, check=first_check, proposed_locations=proposed_locations)
            second_location = _layout_current_location(index=second_index, step=second_step, check=second_check, proposed_locations=proposed_locations)
            second_size = _optional_vector3(second_check.get("approx_size_cm"))
            if first_location is None or second_location is None or second_size is None:
                blockers.append({"issue_kind": kind, "actor_labels": [first_label, second_label], "reason": "Overlap correction is missing usable locations or target size."})
                continue
            overlap = issue.get("overlap_cm") if isinstance(issue.get("overlap_cm"), list) else [correction_step_cm, correction_step_cm]
            delta = _layout_overlap_delta(
                first_location=first_location,
                second_location=second_location,
                overlap_cm=overlap,
                pairwise_padding=pairwise_padding,
                correction_step_cm=correction_step_cm,
                first_label=first_label,
                second_label=second_label,
            )
            candidate = [second_location[axis] + delta[axis] for axis in range(3)]
            corrected, reason = _layout_clamped_location_for_actor(
                location=candidate,
                size=second_size,
                surface=str(second_check.get("surface") or "floor"),
                room=room,
                boundary_margin_cm=boundary_margin_cm,
            )
            if corrected is None or _rounded_vector(corrected) == _rounded_vector(second_location):
                reverse_candidate = [second_location[axis] - delta[axis] for axis in range(3)]
                corrected, reason = _layout_clamped_location_for_actor(
                    location=reverse_candidate,
                    size=second_size,
                    surface=str(second_check.get("surface") or "floor"),
                    room=room,
                    boundary_margin_cm=boundary_margin_cm,
                )
            if corrected is None or _rounded_vector(corrected) == _rounded_vector(second_location):
                blockers.append({"issue_kind": kind, "actor_labels": [first_label, second_label], "reason": reason or "No bounded nudge could separate the overlapping actor footprints.", "recommended_next_tools": ["spatial_plan_interior_composition", "spatial_plan_composition_iteration"]})
                continue
            add_correction(second_index, _layout_correction_record(
                correction_id=f"{second_id}_overlap_{issue_index}",
                step_id=second_id,
                actor_label=second_label,
                issue=issue,
                original_location=second_location,
                corrected_location=corrected,
                action="nudge_to_reduce_footprint_overlap",
                reason=f"Moved this actor away from {first_label} using preflight footprint overlap evidence.",
            ))
            continue

        if kind == "central_circulation_risk":
            check = _layout_check_for_issue(issue, actor_lookup)
            step_index = _layout_step_index_for_check(check, step_lookup) if check else None
            if step_index is None or step_index >= len(steps):
                review_actions.append(_layout_review_action_for_issue(issue))
                uncorrected_issues.append(dict(issue))
                continue
            step = steps[step_index]
            step_id, actor_label = _layout_step_id_and_label(step, step_index)
            location = _layout_current_location(index=step_index, step=step, check=check, proposed_locations=proposed_locations)
            size = _optional_vector3(check.get("approx_size_cm"))
            corrected = None
            if location is not None and size is not None:
                corrected = _layout_circulation_location(
                    location=location,
                    size=size,
                    surface=str(check.get("surface") or "floor"),
                    room=room,
                    min_walkway_width=min_walkway_width,
                    boundary_margin_cm=boundary_margin_cm,
                )
            if corrected is None:
                review_actions.append(_layout_review_action_for_issue(issue))
                uncorrected_issues.append(dict(issue))
                continue
            add_correction(step_index, _layout_correction_record(
                correction_id=f"{step_id}_circulation_{issue_index}",
                step_id=step_id,
                actor_label=actor_label,
                issue=issue,
                original_location=location,
                corrected_location=corrected,
                action="move_outside_central_walkway_band",
                reason="Moved floor prop toward the room edge to preserve a conservative central circulation band.",
            ))
            continue

        review_actions.append(_layout_review_action_for_issue(issue))
        uncorrected_issues.append(dict(issue))

    updated_steps: List[Dict[str, Any]] = []
    corrections_by_id: Dict[str, List[Dict[str, Any]]] = {}
    for index, step in enumerate(steps):
        step_corrections = corrections_by_index.get(index, [])
        step_id, _actor_label = _layout_step_id_and_label(step, index)
        if step_corrections:
            corrections_by_id[step_id] = [dict(item) for item in step_corrections]
        updated_steps.append(_step_after_layout_preflight_corrections(step, step_corrections))

    if blockers and corrections:
        status = "partial_layout_corrections_need_review"
    elif blockers:
        status = "needs_manual_layout_review"
    elif corrections:
        status = "ready_for_corrected_preflight"
    elif issues:
        status = "layout_issues_need_review"
    else:
        status = "no_layout_corrections_needed"

    updated_plan = dict(composition_plan)
    updated_plan["placement_steps"] = updated_steps
    updated_plan["all_placement_steps"] = updated_steps
    if isinstance(composition_plan.get("props"), list):
        updated_plan["props"] = _props_after_layout_preflight_corrections(
            composition_plan=composition_plan,
            corrections_by_id=corrections_by_id,
        )
    updated_plan["layout_preflight_corrections"] = corrections
    updated_plan["layout_preflight_correction_summary"] = {
        "status": status,
        "correction_count": len(corrections),
        "blocker_count": len(blockers),
        "review_action_count": len(review_actions),
        "source_issue_count": len(issues),
    }
    updated_plan_json = json.dumps(updated_plan, sort_keys=True) if include_updated_plan else "<LAYOUT_PREFLIGHT_CORRECTED_COMPOSITION_PLAN_JSON>"
    actor_labels = [
        str((_placement_step_arguments(step).get("actor_label") or step.get("id") or "")).strip()
        for step in updated_steps
        if isinstance(step, Mapping) and (_placement_step_arguments(step).get("actor_label") or step.get("id"))
    ]
    support_review_needed = any(str(action.get("tool") or "") == "spatial_plan_support_surface_anchors" for action in review_actions)
    return {
        "schema": LAYOUT_PREFLIGHT_CORRECTION_SCHEMA,
        "status": status,
        "source_schema": composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
        "source_preflight_status": str(layout_preflight.get("status") or ""),
        "source_issue_count": len(issues),
        "placement_step_count": len(steps),
        "correction_count": len(corrections),
        "blocker_count": len(blockers),
        "review_action_count": len(review_actions),
        "room": dict(room),
        "correction_policy": {
            "correction_step_cm": correction_step_cm,
            "boundary_margin_cm": boundary_margin_cm,
            "pairwise_padding": pairwise_padding,
            "min_walkway_width": min_walkway_width,
        },
        "corrections": corrections,
        "corrections_by_id": corrections_by_id,
        "blockers": blockers,
        "review_actions": review_actions,
        "uncorrected_issues": uncorrected_issues,
        "updated_placement_steps": updated_steps,
        "updated_composition_plan": updated_plan if include_updated_plan else {},
        "updated_composition_plan_json": updated_plan_json,
        "support_surface_anchor_handoff": {
            "tool": "spatial_plan_support_surface_anchors",
            "arguments": {
                "composition_plan_json": updated_plan_json,
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
            },
            "enabled": bool(support_review_needed),
        },
        "layout_preflight_handoff": {
            "tool": "spatial_preflight_interior_layout",
            "arguments": {"composition_plan_json": updated_plan_json, "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>"},
            "enabled": bool(corrections and not blockers),
        },
        "candidate_clearance_handoff": {
            "tool": "spatial_preflight_candidate_clearance",
            "arguments": {"composition_plan_json": updated_plan_json, "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>"},
            "enabled": bool(updated_steps and not blockers),
        },
        "apply_handoff": {
            "tool": "spatial_apply_composition_plan",
            "arguments": {
                "composition_plan_json": updated_plan_json,
                "dry_run": True,
                "block_on_preflight_errors": True,
                "block_on_spatial_fit_review": True,
            },
            "enabled": bool(updated_steps and not blockers),
        },
        "validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": actor_labels,
                "surface_tolerance": 15.0,
                "clearance_padding": pairwise_padding,
                "include_evidence_handoff": True,
            },
            "enabled": bool(actor_labels and not blockers),
        },
        "workflow": [
            {"step": "review_layout_preflight", "tool": "spatial_preflight_interior_layout", "reason": "Use existing approximate room/footprint findings as correction evidence."},
            {"step": "repair_bounds_overlap_circulation", "reason": "Clamp room-bound violations, separate overlapping footprints, and move floor props out of central walkway bands where deterministic."},
            {"step": "anchor_support_surfaces", "tool": "spatial_plan_support_surface_anchors", "enabled": bool(support_review_needed)},
            {"step": "rerun_layout_preflight", "tool": "spatial_preflight_interior_layout", "enabled": bool(corrections and not blockers)},
            {"step": "preflight_candidate_clearance", "tool": "spatial_preflight_candidate_clearance", "enabled": bool(updated_steps and not blockers)},
            {"step": "dry_run_apply", "tool": "spatial_apply_composition_plan", "enabled": bool(updated_steps and not blockers)},
            {"step": "validate_placement", "tool": "spatial_validate_placement", "enabled": bool(actor_labels and not blockers)},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This local correction planner is Ghost-owned arithmetic over Ghost layout preflight records.",
                "It does not copy Epic native MCP/SceneTools source and does not mutate Unreal Editor state.",
                "Any future direct reuse of UE native spatial-awareness implementation details still requires legal review.",
            ],
        },
    }


def _placement_step_clean_record(
    *,
    step: Mapping[str, Any],
    index: int,
    default_tags: Sequence[str],
    default_data_layer_names: Sequence[str],
    fail_on_missing_data_layer: bool,
    select_actor: bool,
    focus_viewport: bool,
    dry_run: bool,
    spatial_fit_reviews_by_key: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    arguments = _placement_step_arguments(step)
    step_id = _safe_asset_stem(str(step.get("id") or arguments.get("actor_label") or f"Placement{index + 1}"), "Placement")
    asset_path = str(arguments.get("asset_path") or "").strip()
    actor_label = str(arguments.get("actor_label") or step_id).strip()
    unresolved = not asset_path or asset_path.startswith("<") or not asset_path.startswith("/Game")
    record = {
        "id": step_id,
        "index": index,
        "tool": "spatial_add_asset_to_scene",
        "asset_path": asset_path,
        "actor_label": actor_label,
        "unresolved": unresolved,
        "unresolved_reason": "" if not unresolved else "asset_path is missing, placeholder, or not a /Game Content Browser path",
        "location": _optional_vector3(arguments.get("location")) or [0.0, 0.0, 0.0],
        "rotation": _optional_vector3(arguments.get("rotation")) or [0.0, 0.0, 0.0],
        "scale": _optional_vector3(arguments.get("scale")) or [1.0, 1.0, 1.0],
        "tags": _merge_unique(
            _string_list(arguments.get("tags"), f"placement_steps[{index}].arguments.tags", maximum=64),
            list(default_tags),
        ),
        "data_layer_names": _merge_unique(
            _string_list(arguments.get("data_layer_names"), f"placement_steps[{index}].arguments.data_layer_names", maximum=32),
            list(default_data_layer_names),
        ),
        "fail_on_missing_data_layer": bool(arguments.get("fail_on_missing_data_layer", fail_on_missing_data_layer)),
        "select_actor": bool(arguments.get("select_actor", select_actor)),
        "focus_viewport": bool(arguments.get("focus_viewport", focus_viewport)),
        "dry_run": bool(dry_run),
        "allow_mutation": False,
        "placement_source": arguments.get("placement_source", ""),
        "placement_hint_source": arguments.get("placement_hint_source", ""),
        "source_step": dict(step),
    }
    spatial_fit_review = _spatial_fit_review_for_step(
        step_id=step_id,
        actor_label=actor_label,
        asset_path=asset_path,
        step=step,
        reviews_by_key=spatial_fit_reviews_by_key,
    )
    if spatial_fit_review:
        review_status = str(spatial_fit_review.get("status") or "").strip()
        review_blocking = _spatial_fit_review_blocks_placement(spatial_fit_review)
        record["spatial_fit_review"] = spatial_fit_review
        record["spatial_fit_review_status"] = review_status
        record["spatial_fit_review_blocking"] = review_blocking
        record["spatial_fit_review_block_reason"] = (
            ""
            if not review_blocking
            else f"spatial_fit_review status is {review_status or 'missing'}; review or fix generated asset fit before mutation"
        )
    record["arguments"] = {
        "asset_path": record["asset_path"],
        "actor_label": record["actor_label"],
        "location": record["location"],
        "rotation": record["rotation"],
        "scale": record["scale"],
        "tags": record["tags"],
        "data_layer_names": record["data_layer_names"],
        "fail_on_missing_data_layer": record["fail_on_missing_data_layer"],
        "dry_run": bool(dry_run),
        "allow_mutation": False,
        "select_actor": record["select_actor"],
        "focus_viewport": record["focus_viewport"],
    }
    return record


def _composition_placement_records(
    *,
    composition_plan: Mapping[str, Any],
    default_tags: Sequence[str],
    default_data_layer_names: Sequence[str],
    fail_on_missing_data_layer: bool,
    select_actor: bool,
    focus_viewport: bool,
    dry_run: bool,
    limit: int,
) -> List[Dict[str, Any]]:
    steps = composition_plan.get("placement_steps") if isinstance(composition_plan.get("placement_steps"), list) else []
    if not steps and isinstance(composition_plan.get("all_placement_steps"), list):
        steps = composition_plan.get("all_placement_steps")
    spatial_fit_reviews_by_key = _spatial_fit_reviews_by_key(composition_plan)
    records: List[Dict[str, Any]] = []
    for index, step in enumerate(steps[:limit]):
        if not isinstance(step, Mapping):
            continue
        records.append(_placement_step_clean_record(
            step=step,
            index=index,
            default_tags=default_tags,
            default_data_layer_names=default_data_layer_names,
            fail_on_missing_data_layer=fail_on_missing_data_layer,
            select_actor=select_actor,
            focus_viewport=focus_viewport,
            dry_run=dry_run,
            spatial_fit_reviews_by_key=spatial_fit_reviews_by_key,
        ))
    return records


def _plan_composition_placement_batch(
    *,
    composition_plan: Mapping[str, Any],
    layout_preflight: Mapping[str, Any],
    default_tags: Sequence[str],
    default_data_layer_names: Sequence[str],
    fail_on_missing_data_layer: bool,
    select_actors: bool,
    focus_viewport: bool,
    dry_run: bool,
    allow_mutation: bool,
    stop_on_unresolved: bool,
    block_on_preflight_errors: bool,
    block_on_spatial_fit_review: bool,
    limit: int,
) -> Dict[str, Any]:
    records = _composition_placement_records(
        composition_plan=composition_plan,
        default_tags=default_tags,
        default_data_layer_names=default_data_layer_names,
        fail_on_missing_data_layer=fail_on_missing_data_layer,
        select_actor=select_actors,
        focus_viewport=focus_viewport,
        dry_run=dry_run,
        limit=limit,
    )
    unresolved = [record for record in records if record.get("unresolved")]
    executable = [record for record in records if not record.get("unresolved")]
    spatial_fit_reviewed = [record for record in executable if record.get("spatial_fit_review")]
    spatial_fit_blockers = [record for record in executable if record.get("spatial_fit_review_blocking")]
    preflight_error_count = int(layout_preflight.get("error_count") or 0) if layout_preflight else 0
    blocked_by_unresolved = bool(stop_on_unresolved and unresolved)
    blocked_by_preflight = bool(block_on_preflight_errors and preflight_error_count)
    blocked_by_spatial_fit_review = bool(block_on_spatial_fit_review and spatial_fit_blockers)
    will_execute = bool(
        not dry_run
        and allow_mutation
        and executable
        and not blocked_by_unresolved
        and not blocked_by_preflight
        and not blocked_by_spatial_fit_review
    )
    if not records:
        status = "no_placement_steps"
    elif blocked_by_preflight:
        status = "blocked_by_preflight"
    elif blocked_by_unresolved:
        status = "blocked_by_unresolved_assets"
    elif blocked_by_spatial_fit_review:
        status = "blocked_by_spatial_fit_review"
    elif dry_run:
        status = "ready_for_review"
    elif not allow_mutation:
        status = "mutation_requires_allow_mutation"
    elif will_execute:
        status = "ready_to_execute"
    else:
        status = "no_executable_steps"
    actor_labels = [str(record.get("actor_label") or "") for record in executable if record.get("actor_label")]
    return {
        "schema": COMPOSITION_PLACEMENT_BATCH_SCHEMA,
        "status": status,
        "will_execute": will_execute,
        "dry_run": bool(dry_run),
        "mutation_required": True,
        "placement_step_count": len(records),
        "executable_count": len(executable),
        "unresolved_count": len(unresolved),
        "preflight_error_count": preflight_error_count,
        "preflight_status": layout_preflight.get("status", "") if layout_preflight else "",
        "spatial_fit_review_count": len(spatial_fit_reviewed),
        "spatial_fit_blocker_count": len(spatial_fit_blockers),
        "spatial_fit_blockers": spatial_fit_blockers,
        "placement_queue": records,
        "executable_steps": executable,
        "unresolved_steps": unresolved,
        "validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": actor_labels,
                "surface_tolerance": 15.0,
                "clearance_padding": 12.0,
                "include_evidence_handoff": True,
            },
            "enabled": bool(actor_labels),
        },
        "evidence_handoff": {
            "tool": "spatial_select_actors",
            "arguments": {
                "actors": actor_labels,
                "dry_run": True,
                "focus_viewport": True,
            },
            "enabled": bool(actor_labels),
        },
        "iteration_handoff": {
            "tool": "spatial_plan_composition_iteration",
            "arguments": {
                "composition_plan_json": "<COMPOSITION_PLAN_JSON>",
                "validation_result_json": "<SPATIAL_VALIDATE_PLACEMENT_RESULT_JSON>",
            },
            "enabled": bool(actor_labels),
        },
        "workflow": [
            {"step": "review_batch_queue", "reason": "Confirm every asset path, transform, tag, and Data Layer before mutation."},
            {"step": "resolve_missing_assets", "enabled": bool(unresolved), "unresolved_steps": unresolved},
            {"step": "review_spatial_fit", "enabled": bool(spatial_fit_reviewed), "blockers": spatial_fit_blockers, "reason": "Generated or project-resolved assets with fit-review warnings must be fixed before mutation."},
            {"step": "plan_asset_scale_corrections", "tool": "spatial_plan_asset_scale_corrections", "enabled": bool(spatial_fit_blockers), "reason": "When blockers are size mismatches, plan scale-corrected dry-run placement before mutation."},
            {"step": "plan_support_surface_anchors", "tool": "spatial_plan_support_surface_anchors", "enabled": bool(executable), "reason": "Align planned floor, counter, table, shelf, and wall props to room-analysis support surfaces before mutation."},
            {"step": "preflight_layout", "tool": "spatial_preflight_interior_layout", "enabled": not bool(layout_preflight)},
            {"step": "plan_layout_preflight_corrections", "tool": "spatial_plan_layout_preflight_corrections", "enabled": bool(blocked_by_preflight), "reason": "Repair fixable room-bound, footprint-overlap, and circulation findings before live placement."},
            {"step": "preflight_candidate_clearance", "tool": "spatial_preflight_candidate_clearance", "enabled": bool(executable), "reason": "Compare planned candidate bounds against existing live actor bounds before mutation."},
            {"step": "apply_composition", "tool": "spatial_apply_composition_plan", "enabled": will_execute},
            {"step": "validate_placement", "tool": "spatial_validate_placement"},
            {"step": "capture_evidence", "tools": ["spatial_select_actors", "focus_viewport", "viewport_capture_screenshot"]},
            {"step": "iterate_if_needed", "tool": "spatial_plan_composition_iteration"},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This batch bridge reuses Ghost placement schemas and public Unreal Python editor APIs through Ghost's existing execution substrate.",
                "It does not copy Epic native MCP SceneTools implementation code.",
            ],
        },
    }


def _correction_base_location(
    *,
    context: Mapping[str, Any],
    validation: Mapping[str, Any],
) -> List[float]:
    step = context.get("placement_step") if isinstance(context.get("placement_step"), Mapping) else {}
    arguments = _placement_step_arguments(step)
    return _rounded_vector(
        _optional_vector3(arguments.get("location"))
        or _validation_actor_location(validation)
        or [0.0, 0.0, 0.0]
    )


def _overlap_nudge(
    *,
    location: Sequence[float],
    clearance: Mapping[str, Any],
    index: int,
    nudge_distance: float,
) -> List[float]:
    target = None
    overlaps = clearance.get("overlaps") if isinstance(clearance.get("overlaps"), list) else []
    for overlap in overlaps:
        if not isinstance(overlap, Mapping):
            continue
        target = (
            _optional_vector3(overlap.get("center"))
            or _optional_vector3(overlap.get("location"))
            or _optional_vector3((overlap.get("bounds") or {}).get("origin") if isinstance(overlap.get("bounds"), Mapping) else None)
        )
        if target is not None:
            break

    if target is not None:
        dx = float(location[0]) - float(target[0])
        dy = float(location[1]) - float(target[1])
    else:
        fallback = ((1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0), (0.707, 0.707), (-0.707, 0.707))
        dx, dy = fallback[index % len(fallback)]

    magnitude = (dx * dx + dy * dy) ** 0.5
    if magnitude <= 0.001:
        dx, dy = (1.0, 0.0)
        magnitude = 1.0
    return [round(dx / magnitude * nudge_distance, 3), round(dy / magnitude * nudge_distance, 3), 0.0]


def _correction_preview_handoff(
    *,
    label: str,
    candidate_location: Sequence[float],
    context: Mapping[str, Any],
) -> Optional[Dict[str, Any]]:
    step = context.get("placement_step") if isinstance(context.get("placement_step"), Mapping) else {}
    arguments = _placement_step_arguments(step)
    asset_path = str(arguments.get("asset_path") or "").strip()
    if not asset_path:
        return None
    preview_label = f"{_safe_asset_stem(label, 'Actor')}_CorrectionPreview"
    return {
        "tool": "spatial_add_asset_to_scene",
        "arguments": {
            "asset_path": asset_path,
            "actor_label": preview_label,
            "location": _rounded_vector(candidate_location),
            "rotation": arguments.get("rotation", [0.0, 0.0, 0.0]),
            "scale": arguments.get("scale", [1.0, 1.0, 1.0]),
            "dry_run": True,
            "allow_mutation": False,
            "select_actor": False,
            "focus_viewport": False,
        },
        "reason": "Preview the corrected placement through Ghost's dry-run asset placement path before mutating an existing actor.",
    }


def _append_placement_source(source: str, marker: str) -> str:
    current = str(source or "").strip()
    if not current:
        return marker
    if marker in current:
        return current
    return f"{current}+{marker}"


def _steps_after_composition_iteration_corrections(
    *,
    composition_plan: Mapping[str, Any],
    corrections_by_actor: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    steps = composition_plan.get("placement_steps") if isinstance(composition_plan.get("placement_steps"), list) else []
    if not steps and isinstance(composition_plan.get("all_placement_steps"), list):
        steps = composition_plan.get("all_placement_steps")
    updated_steps: List[Dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        updated = dict(step)
        arguments = _placement_step_arguments(updated)
        label = str(arguments.get("actor_label") or updated.get("actor_label") or updated.get("id") or "").strip()
        correction = corrections_by_actor.get(label)
        if correction:
            arguments["location"] = list(correction.get("candidate_location") or arguments.get("location") or [0.0, 0.0, 0.0])
            arguments["dry_run"] = True
            arguments["allow_mutation"] = False
            arguments["placement_source"] = _append_placement_source(arguments.get("placement_source", ""), "composition_iteration_correction")
            arguments["composition_iteration_correction"] = {
                "schema": COMPOSITION_ITERATION_SCHEMA,
                "correction_id": correction.get("id"),
                "source_status": correction.get("source_status"),
                "reasons": list(correction.get("reasons", [])) if isinstance(correction.get("reasons"), list) else [],
            }
            updated["arguments"] = arguments
            updated["composition_iteration_corrections"] = [dict(correction)]
        updated_steps.append(updated)
    return updated_steps


def _props_after_composition_iteration_corrections(
    *,
    composition_plan: Mapping[str, Any],
    corrections_by_actor: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    updated_props: List[Dict[str, Any]] = []
    for prop in composition_plan.get("props", []) if isinstance(composition_plan.get("props"), list) else []:
        if not isinstance(prop, Mapping):
            continue
        updated = dict(prop)
        placement = dict(updated.get("placement") or {}) if isinstance(updated.get("placement"), Mapping) else {}
        label = str(placement.get("actor_label") or updated.get("actor_label") or "").strip()
        correction = corrections_by_actor.get(label)
        if correction:
            placement.update({
                "location": list(correction.get("candidate_location") or placement.get("location") or []),
                "source": _append_placement_source(placement.get("source", ""), "composition_iteration_correction"),
            })
            updated["placement"] = placement
            updated["composition_iteration_corrections"] = [dict(correction)]
        updated_props.append(updated)
    return updated_props


def _plan_composition_iteration(
    *,
    composition_plan: Mapping[str, Any],
    validation_result: Mapping[str, Any],
    screenshot_notes: Sequence[str],
    reference_image: str,
    nudge_distance: float,
    surface_tolerance: float,
    clearance_padding: float,
    max_iterations: int,
) -> Dict[str, Any]:
    validations = validation_result.get("validations") if isinstance(validation_result.get("validations"), list) else []
    context_by_actor = _composition_context_by_actor(composition_plan)
    correction_steps: List[Dict[str, Any]] = []
    accepted_actors: List[str] = []
    probe_points: List[List[float]] = []

    for index, validation in enumerate(validations):
        if not isinstance(validation, Mapping):
            continue
        label = _actor_label_from_validation(validation)
        context = context_by_actor.get(label, {})
        base_location = _correction_base_location(context=context, validation=validation)
        candidate_location = list(base_location)
        reasons: List[str] = []
        status = str(validation.get("status") or "unknown")
        gap = _numeric_value(validation.get("surface_gap"))
        tolerance = _numeric_value(validation.get("surface_tolerance")) or surface_tolerance
        needs_surface_probe = False

        if status == "floating":
            if gap is not None:
                candidate_location[2] -= max(0.0, gap)
                reasons.append(f"lower_z_by_surface_gap_{round(max(0.0, gap), 3)}cm")
            else:
                needs_surface_probe = True
                reasons.append("floating_without_numeric_gap_probe_surface")
        elif status == "intersecting_or_below_surface":
            if gap is not None:
                lift = abs(gap) + tolerance
                candidate_location[2] += lift
                reasons.append(f"raise_z_by_gap_plus_tolerance_{round(lift, 3)}cm")
            else:
                candidate_location[2] += tolerance
                reasons.append(f"raise_z_by_surface_tolerance_{round(tolerance, 3)}cm")
        elif status == "no_surface_hit":
            needs_surface_probe = True
            candidate_location[2] += tolerance
            reasons.append("no_surface_hit_probe_before_final_move")
        elif status not in {"on_surface", "unknown"}:
            reasons.append(f"review_validation_status_{status}")

        clearance = validation.get("clearance") if isinstance(validation.get("clearance"), Mapping) else {}
        if clearance.get("status") == "potential_overlap":
            nudge = _overlap_nudge(
                location=candidate_location,
                clearance=clearance,
                index=index,
                nudge_distance=nudge_distance,
            )
            candidate_location[0] += nudge[0]
            candidate_location[1] += nudge[1]
            reasons.append(f"nudge_xy_for_potential_overlap_{round(nudge_distance, 3)}cm")

        candidate_location = _rounded_vector(candidate_location)
        if needs_surface_probe or reasons:
            probe_points.append(candidate_location)

        if not reasons:
            accepted_actors.append(label)
            continue

        step = context.get("placement_step") if isinstance(context.get("placement_step"), Mapping) else {}
        arguments = _placement_step_arguments(step)
        mutation_arguments = {
            "name": label,
            "location": candidate_location,
        }
        if arguments.get("rotation") is not None:
            mutation_arguments["rotation"] = arguments.get("rotation")
        if arguments.get("scale") is not None:
            mutation_arguments["scale"] = arguments.get("scale")

        correction: Dict[str, Any] = {
            "id": f"correct_{_safe_asset_stem(label, 'Actor')}",
            "actor_label": label,
            "source_status": status,
            "reasons": reasons,
            "original_location": base_location,
            "candidate_location": candidate_location,
            "candidate_transform": {
                "location": candidate_location,
                "rotation": arguments.get("rotation", [0.0, 0.0, 0.0]),
                "scale": arguments.get("scale", [1.0, 1.0, 1.0]),
            },
            "dry_run": True,
            "allow_mutation": False,
            "requires_surface_probe": needs_surface_probe,
            "source_validation": {
                "status": status,
                "surface_gap": gap,
                "clearance_status": clearance.get("status", "unknown"),
            },
            "reviewed_mutation_handoff": {
                "tool": "set_actor_transform",
                "arguments": mutation_arguments,
                "requires_review": True,
                "requires_allow_mutation": True,
                "reason": "Only apply after reviewing the dry-run candidate and confirming it still matches the room composition intent.",
            },
        }
        preview = _correction_preview_handoff(label=label, candidate_location=candidate_location, context=context)
        if preview is not None:
            correction["dry_run_preview_handoff"] = preview
        correction_steps.append(correction)

    actor_labels = _merge_unique(
        [step["actor_label"] for step in correction_steps],
        accepted_actors,
        [str(item) for item in (validation_result.get("missing_requested_actors") or []) if item],
    )
    probe_points = _merge_vector_lists(probe_points, maximum=32)
    reference = str(reference_image or "").strip().replace("\\", "/")
    summary = validation_result.get("summary") if isinstance(validation_result.get("summary"), Mapping) else {}
    candidate_clearance_summary = (
        validation_result.get("candidate_clearance_summary")
        if isinstance(validation_result.get("candidate_clearance_summary"), Mapping)
        else {}
    )
    corrections_by_actor = {
        str(correction.get("actor_label") or ""): correction
        for correction in correction_steps
        if str(correction.get("actor_label") or "").strip()
    }
    updated_steps = _steps_after_composition_iteration_corrections(
        composition_plan=composition_plan,
        corrections_by_actor=corrections_by_actor,
    )
    updated_plan = dict(composition_plan)
    if correction_steps:
        updated_plan["placement_steps"] = updated_steps
        updated_plan["all_placement_steps"] = updated_steps
        if isinstance(composition_plan.get("props"), list):
            updated_plan["props"] = _props_after_composition_iteration_corrections(
                composition_plan=composition_plan,
                corrections_by_actor=corrections_by_actor,
            )
        updated_plan["composition_iteration_corrections"] = correction_steps
        updated_plan["composition_iteration_summary"] = {
            "status": "needs_correction",
            "correction_count": len(correction_steps),
            "source_validation_schema": str(validation_result.get("source_schema") or validation_result.get("schema") or PLACEMENT_VALIDATION_SCHEMA),
        }
    updated_plan_json = json.dumps(updated_plan, sort_keys=True) if correction_steps else "<COMPOSITION_ITERATION_UPDATED_PLAN_JSON>"
    status = "needs_correction" if correction_steps else "ready_for_visual_review"
    evidence_handoff: List[Dict[str, Any]] = [
        {
            "tool": "spatial_select_actors",
            "arguments": {
                "actors": actor_labels,
                "dry_run": True,
                "allow_mutation": False,
                "focus_viewport": False,
            },
            "reason": "Resolve the composition actors before viewport review; selection/focus mutation should be explicitly approved later.",
        },
        {
            "tool": "focus_viewport",
            "arguments": {
                "location": "<COMPOSITION_CENTER_OR_SELECTED_ACTORS>",
                "distance": 1600.0,
            },
            "reason": "Frame the reviewed composition after corrections are applied.",
        },
        {
            "tool": "viewport_capture_screenshot",
            "arguments": {
                "artifact_name": "spatial_composition_iteration",
                "show_ui": False,
            },
            "reason": "Capture visible evidence for the next iteration pass.",
        },
    ]
    if reference:
        evidence_handoff.append({
            "tool": "viewport_compare_screenshot",
            "arguments": {
                "baseline_path": reference,
                "candidate_path": "<CAPTURED_SPATIAL_COMPOSITION_SCREENSHOT>",
                "pass_threshold": 0.82,
            },
            "reason": "Compare the new viewport evidence against the reference image after human review of segmentation and camera framing.",
        })

    return {
        "schema": COMPOSITION_ITERATION_SCHEMA,
        "status": status,
        "correction_count": len(correction_steps),
        "accepted_actor_count": len(accepted_actors),
        "validation_summary": {
            "on_surface": int(summary.get("on_surface", 0) or 0),
            "floating": int(summary.get("floating", 0) or 0),
            "intersecting_or_below_surface": int(summary.get("intersecting_or_below_surface", 0) or 0),
            "no_surface_hit": int(summary.get("no_surface_hit", 0) or 0),
            "potential_overlap": int(summary.get("potential_overlap", 0) or 0),
        },
        "source_validation_schema": str(validation_result.get("source_schema") or validation_result.get("schema") or PLACEMENT_VALIDATION_SCHEMA),
        "candidate_clearance_summary": dict(candidate_clearance_summary),
        "screenshot_notes": list(screenshot_notes),
        "correction_steps": correction_steps,
        "updated_placement_steps": updated_steps if correction_steps else [],
        "updated_composition_plan": updated_plan if correction_steps else {},
        "updated_composition_plan_json": updated_plan_json,
        "surface_probe_handoff": {
            "tool": "spatial_surface_probe",
            "arguments": {
                "points": probe_points,
                "placement_offset": 0.0,
                "include_handoff": True,
            },
            "enabled": bool(probe_points),
            "reason": "Confirm candidate corrected points against live surfaces before any reviewed transform mutation.",
        },
        "validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": actor_labels,
                "surface_tolerance": surface_tolerance,
                "clearance_padding": clearance_padding,
                "include_evidence_handoff": True,
            },
            "reason": "Re-run placement validation after applying reviewed correction transforms.",
        },
        "layout_preflight_handoff": {
            "tool": "spatial_preflight_interior_layout",
            "arguments": {
                "composition_plan_json": updated_plan_json,
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
            },
            "enabled": bool(correction_steps),
            "reason": "Recheck room bounds, support/contact, circulation, and visual sightlines after updating the dry-run composition plan.",
        },
        "candidate_clearance_handoff": {
            "tool": "spatial_preflight_candidate_clearance",
            "arguments": {
                "composition_plan_json": updated_plan_json,
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
            },
            "enabled": bool(correction_steps),
            "reason": "Compare the corrected candidate bounds against live Unreal actors before any spawn/mutation.",
        },
        "apply_handoff": {
            "tool": "spatial_apply_composition_plan",
            "arguments": {
                "composition_plan_json": updated_plan_json,
                "dry_run": True,
                "block_on_preflight_errors": True,
                "block_on_spatial_fit_review": True,
            },
            "enabled": bool(correction_steps),
            "reason": "Dry-run the corrected composition plan before any reviewed live mutation.",
        },
        "evidence_handoff": evidence_handoff,
        "iteration_loop": [
            {"step": "review_correction_candidates", "reason": "Check generated corrections against design intent, screenshots, and live room context."},
            {"step": "update_composition_plan", "reason": "Use updated_composition_plan_json for the next dry-run layout/candidate-clearance pass.", "enabled": bool(correction_steps)},
            {"step": "rerun_layout_preflight", "tool": "spatial_preflight_interior_layout", "enabled": bool(correction_steps)},
            {"step": "preflight_candidate_clearance", "tool": "spatial_preflight_candidate_clearance", "enabled": bool(correction_steps)},
            {"step": "dry_run_corrected_composition", "tool": "spatial_apply_composition_plan", "enabled": bool(correction_steps)},
            {"step": "apply_reviewed_transforms", "tools": ["set_actor_transform"], "requires_review": True, "max_batch_size": len(correction_steps)},
            {"step": "probe_candidates", "tool": "spatial_surface_probe", "enabled": bool(probe_points)},
            {"step": "revalidate", "tool": "spatial_validate_placement", "max_iterations": max_iterations},
            {"step": "capture_viewport_evidence", "tools": ["focus_viewport", "viewport_capture_screenshot", "viewport_compare_screenshot"] if reference else ["focus_viewport", "viewport_capture_screenshot"]},
            {
                "step": "rerun_iteration_planner",
                "tool": "spatial_plan_composition_iteration",
                "arguments": {
                    "composition_plan_json": updated_plan_json if correction_steps else "<UPDATED_ORIGINAL_COMPOSITION_PLAN_JSON>",
                    "validation_result_json": "<NEW_SPATIAL_VALIDATE_PLACEMENT_RESULT_JSON>",
                    "reference_image": reference,
                    "max_iterations": max(1, max_iterations - 1),
                },
            },
        ],
        "review_notes": _merge_unique(
            screenshot_notes,
            [
                "This planner does not mutate the Unreal level; transform handoffs require explicit review.",
                "Screenshot comparison depends on the viewport camera and does not replace human visual judgment.",
                "Re-run spatial_analyze_room if walls, counters, or large furniture have changed since the original plan.",
            ],
        ),
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is Ghost-owned iterative planning over Ghost validation output, not copied Epic SceneTools logic.",
                "Legal review is required before reusing native UE MCP implementation details beyond public protocol concepts.",
            ],
        },
    }


def _worldbuilding_outputs_from_json(value: str, field_name: str, expected_schema: str) -> Dict[str, Any]:
    return _outputs_from_result_json(value, field_name, expected_schema)


def _worldbuilding_gate(
    name: str,
    ready: bool,
    *,
    status: str,
    detail: str,
    tool: str = "",
    arguments: Optional[Mapping[str, Any]] = None,
    blocking: bool = True,
) -> Dict[str, Any]:
    gate = {
        "name": name,
        "ready": bool(ready),
        "status": status,
        "detail": detail,
        "blocking": bool(blocking),
    }
    if tool:
        gate["next_action"] = {"tool": tool, "arguments": dict(arguments or {})}
    return gate


def _tripo_crop_manifest_requirements(tripo_batch: Mapping[str, Any]) -> Dict[str, Any]:
    jobs = tripo_batch.get("jobs") if isinstance(tripo_batch.get("jobs"), list) else []
    blockers: List[Dict[str, Any]] = []
    for job in jobs:
        if not isinstance(job, Mapping):
            continue
        readiness = job.get("crop_readiness") if isinstance(job.get("crop_readiness"), Mapping) else {}
        if str(job.get("mode") or "") != "image_to_model" or readiness.get("ready"):
            continue
        crop = job.get("crop") if isinstance(job.get("crop"), Mapping) else {}
        blockers.append({
            "id": str(job.get("id") or ""),
            "prop_name": str(job.get("prop_name") or job.get("id") or "prop"),
            "crop_readiness_status": str(readiness.get("status") or "needs_crop_manifest"),
            "next_tool": str(readiness.get("next_tool") or "spatial_prepare_screenshot_crop_manifest"),
            "crop_box": crop.get("crop_box"),
            "output_placeholder": str(crop.get("output_placeholder") or ""),
        })

    summary = tripo_batch.get("guarded_pipeline_summary") if isinstance(tripo_batch.get("guarded_pipeline_summary"), Mapping) else {}
    count = max(
        _scene_graph_count(tripo_batch.get("blocked_by_crop_manifest_count"), 0),
        _scene_graph_count(summary.get("blocked_by_crop_manifest_count"), 0),
        len(blockers),
    )
    job_ids = [item["id"] for item in blockers if item.get("id")]
    if count and not job_ids:
        job_ids = [f"<IMAGE_CROP_JOB_{index + 1}>" for index in range(count)]
    return {
        "required": bool(count),
        "count": count,
        "job_ids": job_ids,
        "jobs": blockers,
        "status": "needs_crop_manifest" if count else "not_required",
        "handoff": {
            "tool": "spatial_prepare_screenshot_crop_manifest",
            "arguments": {
                "reconstruction_plan_json": "<SPATIAL_PLAN_SCREENSHOT_RECONSTRUCTION_RESULT_JSON>",
                "crop_output_dir": "Saved/MCPChat/spatial_crops",
            },
            "enabled": bool(count),
        },
    }


def _worldbuilding_validation_issue_count(validation: Mapping[str, Any]) -> int:
    summary = validation.get("summary") if isinstance(validation.get("summary"), Mapping) else {}
    return sum(
        int(summary.get(key, 0) or 0)
        for key in ("floating", "intersecting_or_below_surface", "no_surface_hit", "potential_overlap")
    )


def _asset_binding_needs_scale_correction(asset_binding: Mapping[str, Any]) -> bool:
    reviews = asset_binding.get("spatial_fit_reviews") if isinstance(asset_binding.get("spatial_fit_reviews"), list) else []
    for review in reviews:
        if not isinstance(review, Mapping):
            continue
        status = str(review.get("status") or "").strip()
        reason = ""
        size_match = review.get("size_match") if isinstance(review.get("size_match"), Mapping) else {}
        reason = str(size_match.get("reason") or "").strip()
        if status == "needs_size_review" or reason in {"size_loose_mismatch", "size_strong_mismatch"}:
            return True
    summary = asset_binding.get("spatial_fit_review_summary") if isinstance(asset_binding.get("spatial_fit_review_summary"), Mapping) else {}
    return int(summary.get("size_review_count") or 0) > 0


def _composition_needs_support_surface_anchoring(composition_plan: Mapping[str, Any]) -> bool:
    props = composition_plan.get("props") if isinstance(composition_plan.get("props"), list) else []
    for prop in props:
        if not isinstance(prop, Mapping):
            continue
        details = _prop_size_surface_zone(prop, str(prop.get("id") or prop.get("name") or "prop"))
        if _surface_anchor_required(details):
            placement = prop.get("placement") if isinstance(prop.get("placement"), Mapping) else {}
            if not placement.get("support_actor") and "room_analysis" not in str(placement.get("source") or ""):
                return True

    steps = composition_plan.get("placement_steps") if isinstance(composition_plan.get("placement_steps"), list) else []
    for step in steps:
        if not isinstance(step, Mapping):
            continue
        arguments = _placement_step_arguments(step)
        step_id = str(step.get("id") or arguments.get("actor_label") or "prop")
        details = _prop_size_surface_zone({"id": step_id, "name": step_id}, step_id)
        if _surface_anchor_required(details) and not arguments.get("support_actor"):
            return True
    return False


def _support_anchor_ready_status(status: str) -> bool:
    return str(status or "").strip() in {
        "ready_for_support_surface_review",
        "no_support_anchors_needed",
        "support_anchors_not_applicable",
    }


def _plan_worldbuilding_readiness(
    *,
    reference_image: str,
    room_analysis: Mapping[str, Any],
    functional_zone_plan: Mapping[str, Any],
    prop_program: Mapping[str, Any],
    decomposition_request: Mapping[str, Any],
    detection_preflight: Mapping[str, Any],
    scene_graph: Mapping[str, Any],
    reconstruction_plan: Mapping[str, Any],
    composition_plan: Mapping[str, Any],
    asset_resolution: Mapping[str, Any],
    tripo_batch: Mapping[str, Any],
    asset_binding: Mapping[str, Any],
    asset_scale_correction: Mapping[str, Any],
    support_surface_anchors: Mapping[str, Any],
    layout_preflight: Mapping[str, Any],
    layout_preflight_correction: Mapping[str, Any],
    candidate_clearance: Mapping[str, Any],
    apply_result: Mapping[str, Any],
    validation_result: Mapping[str, Any],
    iteration_plan: Mapping[str, Any],
    viewport_evidence: Mapping[str, Any],
    require_room_analysis: bool,
    require_scene_graph: bool,
    require_viewport_evidence: bool,
) -> Dict[str, Any]:
    screenshot_mode = bool(reference_image or decomposition_request or detection_preflight or scene_graph or reconstruction_plan)
    reconstruction_composition = reconstruction_plan.get("composition_plan") if isinstance(reconstruction_plan.get("composition_plan"), Mapping) else {}
    scale_corrected_composition = asset_scale_correction.get("updated_composition_plan") if isinstance(asset_scale_correction.get("updated_composition_plan"), Mapping) else {}
    support_anchored_composition = support_surface_anchors.get("updated_composition_plan") if isinstance(support_surface_anchors.get("updated_composition_plan"), Mapping) else {}
    layout_corrected_composition = layout_preflight_correction.get("updated_composition_plan") if isinstance(layout_preflight_correction.get("updated_composition_plan"), Mapping) else {}
    binding_composition = (
        {
            "schema": COMPOSITION_ASSET_BINDING_SCHEMA,
            "props": asset_binding.get("bound_props", []),
            "placement_steps": asset_binding.get("all_placement_steps") or asset_binding.get("placement_steps", []),
        }
        if asset_binding
        else {}
    )
    active_composition = (
        layout_corrected_composition
        or support_anchored_composition
        or scale_corrected_composition
        or composition_plan
        or reconstruction_composition
        or binding_composition
    )
    composition_available = bool(composition_plan.get("placement_steps") or reconstruction_composition.get("placement_steps"))
    gates: List[Dict[str, Any]] = []

    gates.append(_worldbuilding_gate(
        "live_room_analysis",
        bool(room_analysis) or not require_room_analysis,
        status="ready" if room_analysis else ("optional" if not require_room_analysis else "missing"),
        detail="room dimensions/zones/surfaces available" if room_analysis else "run spatial_analyze_room to ground the workflow in live Unreal dimensions",
        tool="spatial_analyze_room",
        arguments={"room_type": "apartment", "include_planner_handoff": True},
        blocking=require_room_analysis,
    ))

    functional_zone_status = str(functional_zone_plan.get("status") or "")
    functional_zone_ready = bool(
        functional_zone_status == "ready_for_composition"
        or functional_zone_plan
        or composition_plan
        or reconstruction_plan
    )
    gates.append(_worldbuilding_gate(
        "functional_zone_inference",
        functional_zone_ready,
        status=functional_zone_status or ("satisfied_by_composition" if (composition_plan or reconstruction_plan) else "missing"),
        detail=(
        "functional kitchen/living/bedroom/entry/hallway/utility zones are available or already baked into composition"
            if functional_zone_ready
            else "infer usable room zones from room analysis and screenshot/composition evidence before selecting props"
        ),
        tool="spatial_infer_functional_zones",
        arguments={
            "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
            "detected_items_json": "<OPTIONAL_NORMALIZED_DETECTED_ITEMS_JSON>",
            "requested_zones": ["kitchen", "living"],
        },
        blocking=bool(require_room_analysis and room_analysis and not functional_zone_ready),
    ))

    prop_program_status = str(prop_program.get("status") or "")
    prop_program_ready = bool(
        prop_program_status == "ready_for_composition"
        or prop_program
        or composition_plan
        or reconstruction_plan
    )
    gates.append(_worldbuilding_gate(
        "interior_prop_program",
        prop_program_ready,
        status=prop_program_status or (
            "satisfied_by_composition"
            if (composition_plan or reconstruction_plan)
            else ("waiting_on_functional_zones" if not functional_zone_ready else "missing")
        ),
        detail=(
            "fixtures, furniture, clutter, and architectural fill are planned or already baked into composition"
            if prop_program_ready
            else "plan the per-zone prop program before composition, asset resolution, or Tripo generation"
        ),
        tool="spatial_plan_interior_prop_program",
        arguments={
            "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
            "functional_zone_plan_json": "<SPATIAL_INFER_FUNCTIONAL_ZONES_RESULT_JSON>",
            "required_props": ["refrigerator", "stove and oven", "kitchen counter run", "kitchen sink"],
            "include_architectural_fill": True,
        },
        blocking=bool(functional_zone_ready and not prop_program_ready),
    ))

    if screenshot_mode:
        gates.append(_worldbuilding_gate(
            "screenshot_decomposition_request",
            bool(decomposition_request or detection_preflight or reconstruction_plan),
            status=str(decomposition_request.get("status") or ("satisfied_by_downstream_artifact" if (detection_preflight or reconstruction_plan) else "missing")),
            detail="vision decomposition contract prepared" if decomposition_request else ("detections/reconstruction already supplied" if (detection_preflight or reconstruction_plan) else "prepare the vision-agent screenshot decomposition request"),
            tool="spatial_prepare_screenshot_decomposition_request",
            arguments={"reference_image": reference_image or "<REFERENCE_IMAGE>"},
        ))

        preflight_status = str(detection_preflight.get("status") or "")
        preflight_ready = bool(preflight_status == "ready_for_reconstruction" or reconstruction_plan)
        gates.append(_worldbuilding_gate(
            "screenshot_detection_preflight",
            preflight_ready,
            status=preflight_status or ("satisfied_by_reconstruction" if reconstruction_plan else "missing"),
            detail="detections are normalized and ready" if preflight_ready else "preflight detected_items_json before reconstruction or Tripo crop spend",
            tool="spatial_preflight_screenshot_detections",
            arguments={"reference_image": reference_image or "<REFERENCE_IMAGE>", "detected_items_json": "<DETECTED_ITEMS_JSON>"},
        ))

        scene_status = str(scene_graph.get("status") or "")
        scene_ready = bool(scene_status == "ready_for_reconstruction" or (not require_scene_graph and reconstruction_plan))
        gates.append(_worldbuilding_gate(
            "screenshot_scene_graph",
            scene_ready,
            status=scene_status or ("optional" if not require_scene_graph else "missing"),
            detail="support/contact and relative-position graph is available" if scene_ready else "infer scene graph relationships before reconstruction placement",
            tool="spatial_infer_screenshot_scene_graph",
            arguments={"reference_image": reference_image or "<REFERENCE_IMAGE>", "detected_items_json": "<NORMALIZED_DETECTED_ITEMS_JSON>"},
            blocking=require_scene_graph,
        ))

    gates.append(_worldbuilding_gate(
        "composition_plan",
        composition_available,
        status="ready" if composition_available else "missing",
        detail="composition placement plan is available" if composition_available else "plan interior composition or screenshot reconstruction before asset resolution",
        tool="spatial_plan_screenshot_reconstruction" if screenshot_mode else "spatial_plan_interior_composition",
        arguments={"reference_image": reference_image or "<REFERENCE_IMAGE>"} if screenshot_mode else {
            "room_type": "apartment",
            "prop_program_json": "<SPATIAL_PLAN_INTERIOR_PROP_PROGRAM_RESULT_JSON>",
        },
    ))

    asset_status = str(asset_resolution.get("status") or "")
    asset_ready = bool(asset_status in {"ready_for_binding", "already_resolved"} or asset_binding)
    gates.append(_worldbuilding_gate(
        "project_asset_resolution",
        asset_ready,
        status=asset_status or ("satisfied_by_binding" if asset_binding else "missing"),
        detail="project assets resolved or binding already supplied" if asset_ready else "resolve existing project assets before preparing Tripo jobs",
        tool="spatial_resolve_project_assets",
        arguments={"composition_plan_json": "<COMPOSITION_OR_RECONSTRUCTION_JSON>", "asset_catalog_json": "<PROJECT_ASSET_CATALOG_JSON>"},
        blocking=False,
    ))

    tripo_crop_requirements = _tripo_crop_manifest_requirements(tripo_batch) if tripo_batch else {
        "required": False,
        "count": 0,
        "job_ids": [],
        "jobs": [],
        "status": "not_required",
        "handoff": {"tool": "spatial_prepare_screenshot_crop_manifest", "arguments": {}, "enabled": False},
    }
    crop_manifest_required = bool(tripo_crop_requirements.get("required") and not asset_binding)
    crop_manifest_handoff = tripo_crop_requirements.get("handoff") if isinstance(tripo_crop_requirements.get("handoff"), Mapping) else {}
    crop_manifest_arguments = crop_manifest_handoff.get("arguments") if isinstance(crop_manifest_handoff.get("arguments"), Mapping) else {}
    gates.append(_worldbuilding_gate(
        "screenshot_crop_manifest",
        not crop_manifest_required,
        status="satisfied_by_binding" if asset_binding else str(tripo_crop_requirements.get("status") or "not_required"),
        detail=(
            "screenshot crop files are prepared or not needed for Tripo image-to-model"
            if not crop_manifest_required
            else "write concrete local screenshot crop files before Tripo image-to-model spend"
        ),
        tool="spatial_prepare_screenshot_crop_manifest",
        arguments={
            **dict(crop_manifest_arguments),
            "blocked_job_ids": list(tripo_crop_requirements.get("job_ids") or []),
        },
        blocking=crop_manifest_required,
    ))

    tripo_status = str(tripo_batch.get("status") or "")
    tripo_job_count = int(tripo_batch.get("job_count") or 0) if tripo_batch else 0
    tripo_ready = bool(not tripo_batch or tripo_status in {"no_generation_needed", "ready_for_tripo_submission"} or asset_binding)
    tripo_blocking = bool(
        tripo_batch
        and tripo_job_count
        and tripo_status not in {"ready_for_tripo_submission", "no_generation_needed"}
        and not asset_binding
        and not crop_manifest_required
    )
    gates.append(_worldbuilding_gate(
        "guarded_tripo_generation",
        tripo_ready,
        status=tripo_status or ("satisfied_by_binding" if asset_binding else "not_started"),
        detail=(
            "Tripo generation is not needed, ready, or already imported/bound"
            if tripo_ready
            else (
                "prepare the screenshot crop manifest before spend confirmation or generated asset placement"
                if crop_manifest_required
                else "finish explicit spend confirmation before generated asset placement"
            )
        ),
        tool="spatial_prepare_screenshot_crop_manifest" if crop_manifest_required else "spatial_prepare_tripo_generation_batch",
        arguments={
            **(
                {
                    **dict(crop_manifest_arguments),
                    "blocked_job_ids": list(tripo_crop_requirements.get("job_ids") or []),
                }
                if crop_manifest_required
                else {"composition_plan_json": "<COMPOSITION_OR_RECONSTRUCTION_JSON>", "confirm_spend": False}
            )
        },
        blocking=tripo_blocking,
    ))

    binding_status = str(asset_binding.get("status") or "")
    binding_ready = bool(binding_status == "ready_for_dry_run_placement")
    gates.append(_worldbuilding_gate(
        "asset_binding_and_spatial_fit",
        binding_ready,
        status=binding_status or "missing",
        detail="assets are bound and ready for dry-run placement" if binding_ready else "bind imports/project overrides and review generated asset spatial fit",
        tool="spatial_bind_generated_assets_to_composition",
        arguments={"composition_plan_json": "<COMPOSITION_JSON>", "import_results_json": "<IMPORT_RESULTS_JSON>"},
    ))

    scale_required = _asset_binding_needs_scale_correction(asset_binding)
    scale_status = str(asset_scale_correction.get("status") or "")
    scale_ready_statuses = {"ready_for_scaled_dry_run", "no_scale_corrections_needed"}
    scale_ready = bool(not scale_required or scale_status in scale_ready_statuses)
    gates.append(_worldbuilding_gate(
        "generated_asset_scale_correction",
        scale_ready,
        status=scale_status or ("not_required" if not scale_required else "missing"),
        detail=(
            "no generated-asset scale correction is currently required"
            if not scale_required
            else (
                "generated/imported asset scale correction is ready for dry-run placement"
                if scale_ready
                else "plan scale correction or regenerate assets before layout preflight and mutation"
            )
        ),
        tool="spatial_plan_asset_scale_corrections",
        arguments={"composition_plan_json": "<SPATIAL_BIND_GENERATED_ASSETS_TO_COMPOSITION_RESULT_JSON>"},
        blocking=scale_required,
    ))

    support_required = bool(room_analysis and active_composition and _composition_needs_support_surface_anchoring(active_composition))
    support_status = str(support_surface_anchors.get("status") or "")
    support_ready = bool(not support_required or _support_anchor_ready_status(support_status))
    gates.append(_worldbuilding_gate(
        "support_surface_anchoring",
        support_ready,
        status=support_status or ("not_required" if not support_required else "missing"),
        detail=(
            "no counter/table/shelf/wall anchoring is currently required"
            if not support_required
            else (
                "support-surface anchors are ready for layout preflight"
                if support_ready
                else "anchor counter, table, shelf, wall, and floor contact props to room-analysis surfaces before layout preflight"
            )
        ),
        tool="spatial_plan_support_surface_anchors",
        arguments={
            "composition_plan_json": "<BOUND_OR_SCALE_CORRECTED_COMPOSITION_JSON>",
            "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
        },
        blocking=support_required,
    ))

    layout_status = str(layout_preflight.get("status") or "")
    layout_correction_status = str(layout_preflight_correction.get("status") or "")
    layout_preflight_blocked = bool(layout_preflight and layout_status not in {"pass", "needs_review"})
    layout_correction_ready = _layout_preflight_correction_ready_status(layout_correction_status)
    layout_ready = bool(layout_status in {"pass", "needs_review"} or not layout_preflight or (layout_preflight_blocked and layout_correction_ready))
    gates.append(_worldbuilding_gate(
        "layout_preflight",
        layout_ready,
        status=layout_status or ("satisfied_by_correction" if layout_correction_ready else "missing"),
        detail=(
            "layout preflight passed, has review-only warnings, or has a local correction plan ready for another preflight"
            if layout_ready and layout_preflight
            else ("run layout preflight before mutating a full composition" if not layout_preflight else "layout preflight has blocking issues")
        ),
        tool="spatial_preflight_interior_layout",
        arguments={"composition_plan_json": "<BOUND_OR_ORIGINAL_COMPOSITION_JSON>"},
        blocking=bool(layout_preflight_blocked and not layout_correction_ready),
    ))

    correction_required = bool(layout_preflight_blocked)
    correction_ready = bool(not correction_required or layout_correction_ready)
    gates.append(_worldbuilding_gate(
        "layout_preflight_correction",
        correction_ready,
        status=layout_correction_status or ("not_required" if not correction_required else "missing"),
        detail=(
            "no blocking layout correction is currently required"
            if not correction_required
            else (
                "fixable layout preflight issues have a dry-run correction plan"
                if correction_ready
                else "plan dry-run corrections for room-bound, overlap, and circulation findings before mutation"
            )
        ),
        tool="spatial_plan_layout_preflight_corrections",
        arguments={
            "composition_plan_json": "<BOUND_OR_SUPPORT_ANCHORED_COMPOSITION_JSON>",
            "layout_preflight_json": "<SPATIAL_PREFLIGHT_INTERIOR_LAYOUT_RESULT_JSON>",
        },
        blocking=correction_required,
    ))

    candidate_clearance_status = str(candidate_clearance.get("status") or "")
    candidate_clearance_blocked = bool(candidate_clearance and candidate_clearance_status not in {"pass", "needs_review"})
    candidate_clearance_ready = bool(candidate_clearance_status in {"pass", "needs_review"})
    gates.append(_worldbuilding_gate(
        "live_candidate_clearance",
        candidate_clearance_ready,
        status=candidate_clearance_status or "missing",
        detail=(
            "planned candidate bounds have been checked against live Unreal actors"
            if candidate_clearance_ready
            else (
                "live actor clearance preflight found blocking overlaps"
                if candidate_clearance_blocked
                else "compare planned candidate bounds against live Unreal actors before mutation"
            )
        ),
        tool="spatial_plan_composition_iteration" if candidate_clearance_blocked else "spatial_preflight_candidate_clearance",
        arguments=(
            {
                "composition_plan_json": "<BOUND_OR_LAYOUT_CORRECTED_COMPOSITION_JSON>",
                "validation_result_json": "<SPATIAL_PREFLIGHT_CANDIDATE_CLEARANCE_RESULT_JSON>",
            }
            if candidate_clearance_blocked
            else {
                "composition_plan_json": "<BOUND_OR_LAYOUT_CORRECTED_COMPOSITION_JSON>",
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
                "clearance_padding": 12.0,
            }
        ),
        blocking=candidate_clearance_blocked,
    ))

    apply_status = str(apply_result.get("status") or "")
    apply_ready = bool(apply_status == "executed")
    gates.append(_worldbuilding_gate(
        "fit_gated_composition_apply",
        apply_ready,
        status=apply_status or "missing",
        detail="composition was applied to the Unreal scene" if apply_ready else "run dry-run-first, spatial-fit-gated composition application",
        tool="spatial_apply_composition_plan",
        arguments={"composition_plan_json": "<BOUND_COMPOSITION_JSON>", "dry_run": True},
    ))

    validation_issue_count = _worldbuilding_validation_issue_count(validation_result)
    validation_ready = bool(validation_result and validation_issue_count == 0)
    gates.append(_worldbuilding_gate(
        "placement_validation",
        validation_ready,
        status="pass" if validation_ready else ("needs_iteration" if validation_result else "missing"),
        detail="placement validation has no surface/contact/clearance issues" if validation_ready else ("validation found issues; plan corrections" if validation_result else "validate placed actors against surfaces and clearance"),
        tool="spatial_validate_placement" if not validation_result else "spatial_plan_composition_iteration",
        arguments={"actors": "<PLACED_ACTOR_LABELS>", "include_evidence_handoff": True} if not validation_result else {"validation_result_json": "<SPATIAL_VALIDATE_PLACEMENT_RESULT_JSON>"},
    ))

    iteration_status = str(iteration_plan.get("status") or "")
    iteration_ready = bool(not validation_result or validation_ready or iteration_status == "ready_for_visual_review")
    gates.append(_worldbuilding_gate(
        "iteration_plan",
        iteration_ready,
        status=iteration_status or ("not_needed" if validation_ready else "missing"),
        detail="no correction iteration is currently needed" if iteration_ready else "compile correction candidates from validation results",
        tool="spatial_plan_composition_iteration",
        arguments={"composition_plan_json": "<COMPOSITION_JSON>", "validation_result_json": "<SPATIAL_VALIDATE_PLACEMENT_RESULT_JSON>"},
        blocking=bool(validation_result and not validation_ready),
    ))

    viewport_ready = bool(viewport_evidence) or not require_viewport_evidence
    gates.append(_worldbuilding_gate(
        "viewport_evidence",
        viewport_ready,
        status="ready" if viewport_evidence else ("optional" if not require_viewport_evidence else "missing"),
        detail="viewport evidence supplied" if viewport_evidence else "capture viewport evidence after placement/iteration",
        tool="viewport_capture_screenshot",
        arguments={"artifact_name": "spatial_worldbuilding_review", "show_ui": False},
        blocking=require_viewport_evidence,
    ))

    blocking_gates = [gate for gate in gates if not gate["ready"] and gate.get("blocking")]
    remaining_gates = [gate for gate in gates if not gate["ready"]]
    status = "blocked" if blocking_gates else ("needs_next_action" if remaining_gates else "ready_for_human_worldbuilding_review")
    next_actions = [
        {**gate.get("next_action", {}), "gate": gate["name"], "reason": gate["detail"]}
        for gate in remaining_gates
        if isinstance(gate.get("next_action"), Mapping)
    ]
    return {
        "schema": WORLDBUILDING_READINESS_SCHEMA,
        "status": status,
        "screenshot_mode": screenshot_mode,
        "reference_image": reference_image,
        "gate_count": len(gates),
        "ready_gate_count": len([gate for gate in gates if gate["ready"]]),
        "blocking_gate_count": len(blocking_gates),
        "remaining_gate_count": len(remaining_gates),
        "gates": gates,
        "blocking_gates": blocking_gates,
        "next_actions": next_actions,
        "evidence_handoffs": [
            {"tool": "spatial_select_actors", "arguments": {"actors": "<PLACED_ACTOR_LABELS>", "dry_run": True, "focus_viewport": True}},
            {"tool": "viewport_capture_screenshot", "arguments": {"artifact_name": "spatial_worldbuilding_review", "show_ui": False}},
        ],
        "workflow": [
            {"step": "measure_space", "tool": "spatial_analyze_room"},
            {"step": "infer_functional_zones", "tool": "spatial_infer_functional_zones"},
            {"step": "plan_prop_program", "tool": "spatial_plan_interior_prop_program"},
            {"step": "decompose_reference", "tool": "spatial_prepare_screenshot_decomposition_request", "enabled": screenshot_mode},
            {"step": "preflight_and_graph", "tools": ["spatial_preflight_screenshot_detections", "spatial_infer_screenshot_scene_graph"], "enabled": screenshot_mode},
            {"step": "plan_composition", "tools": ["spatial_plan_screenshot_reconstruction" if screenshot_mode else "spatial_plan_interior_composition"]},
            {"step": "resolve_or_generate_assets", "tools": ["spatial_resolve_project_assets", "spatial_prepare_tripo_generation_batch"]},
            {"step": "prepare_screenshot_crops", "tool": "spatial_prepare_screenshot_crop_manifest", "enabled": bool(crop_manifest_required), "blocked_job_ids": list(tripo_crop_requirements.get("job_ids") or [])},
            {"step": "bind_review_apply", "tools": ["spatial_bind_generated_assets_to_composition", "spatial_plan_asset_scale_corrections", "spatial_plan_support_surface_anchors", "spatial_preflight_interior_layout", "spatial_plan_layout_preflight_corrections", "spatial_preflight_candidate_clearance", "spatial_apply_composition_plan"], "candidate_clearance_status": candidate_clearance_status or "missing"},
            {"step": "validate_iterate_evidence", "tools": ["spatial_validate_placement", "spatial_plan_composition_iteration", "viewport_capture_screenshot"]},
        ],
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This readiness compiler only summarizes Ghost-owned workflow schemas and handoffs.",
                "It does not execute Unreal mutation, paid Tripo calls, computer vision, or Epic native SceneTools code.",
            ],
        },
    }


def _work_order_prop_requirements(composition_plan: Mapping[str, Any]) -> List[Dict[str, Any]]:
    props = list(composition_plan.get("props", [])) if isinstance(composition_plan.get("props"), list) else []
    generation_by_id = _generation_tasks_by_id(composition_plan)
    steps_by_id = _placement_steps_by_id(composition_plan)
    requirements: List[Dict[str, Any]] = []
    for prop in props[:128]:
        if not isinstance(prop, Mapping):
            continue
        prop_id = _safe_asset_stem(str(prop.get("id") or prop.get("detected_item_id") or prop.get("name")), "Prop")
        generation = generation_by_id.get(prop_id, {})
        placement = steps_by_id.get(prop_id, {})
        arguments = placement.get("arguments") if isinstance(placement.get("arguments"), Mapping) else {}
        requirements.append({
            "id": prop_id,
            "name": str(prop.get("name") or prop_id),
            "zone": str(prop.get("zone") or ""),
            "category": str(prop.get("category") or ""),
            "surface": str(prop.get("surface") or ""),
            "source": str(prop.get("source") or ""),
            "matched_asset_path": str(prop.get("matched_asset_path") or prop.get("existing_asset_path") or ""),
            "asset_path_placeholder": str(prop.get("asset_path_placeholder") or arguments.get("asset_path") or ""),
            "approx_size_cm": list(prop.get("approx_size_cm") or prop.get("size") or []),
            "needs_generation": bool(generation and not (prop.get("matched_asset_path") or prop.get("existing_asset_path"))),
            "tripo_mode": "image_or_text" if generation.get("reference_image_variant") else ("text_to_model" if generation else ""),
            "actor_label": str((prop.get("placement") if isinstance(prop.get("placement"), Mapping) else {}).get("actor_label") or arguments.get("actor_label") or ""),
        })
    return requirements


def _zone_program_from_composition(
    *,
    zones: Sequence[Mapping[str, Any]],
    requested_zones: Sequence[str],
    composition_plan: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    requested = {str(zone or "").strip().lower().replace(" ", "_") for zone in requested_zones if str(zone or "").strip()}
    props = list(composition_plan.get("props", [])) if isinstance(composition_plan.get("props"), list) else []
    props_by_zone: Dict[str, List[str]] = {}
    for prop in props:
        if not isinstance(prop, Mapping):
            continue
        zone_name = str(prop.get("zone") or "").strip() or "unassigned"
        props_by_zone.setdefault(zone_name, []).append(str(prop.get("name") or prop.get("id") or "prop"))

    program: List[Dict[str, Any]] = []
    for zone in zones:
        if not isinstance(zone, Mapping):
            continue
        name = str(zone.get("name") or "").strip()
        if not name:
            continue
        program.append({
            "name": name,
            "requested": bool(not requested or name.lower() in requested),
            "center": list(zone.get("center") or []),
            "size": list(zone.get("size") or []),
            "wall": str(zone.get("wall") or ""),
            "planned_props": props_by_zone.get(name, []),
            "planned_prop_count": len(props_by_zone.get(name, [])),
        })
    return program


def _worldbuilding_work_order_status(
    *,
    reference_image: str,
    detected_items: Sequence[Mapping[str, Any]],
    composition_plan: Mapping[str, Any],
    asset_resolution: Mapping[str, Any],
    tripo_expected_count: int,
    tripo_crop_blocker_count: int,
) -> str:
    if reference_image and not detected_items:
        return "needs_screenshot_decomposition"
    if not composition_plan:
        return "needs_composition_plan"
    if tripo_crop_blocker_count:
        return "needs_screenshot_crop_manifest"
    if not asset_resolution:
        return "ready_for_project_asset_catalog"
    unresolved_count = int(asset_resolution.get("unresolved_count") or 0)
    if unresolved_count or tripo_expected_count:
        return "ready_for_guarded_tripo_review"
    if int(asset_resolution.get("resolved_count") or 0):
        return "ready_for_asset_binding"
    return "ready_for_layout_preflight"


def _work_order_actor_labels(composition_plan: Mapping[str, Any]) -> List[str]:
    labels: List[str] = []
    for step in composition_plan.get("placement_steps", []) if isinstance(composition_plan.get("placement_steps"), list) else []:
        if not isinstance(step, Mapping):
            continue
        arguments = _placement_step_arguments(step)
        label = str(arguments.get("actor_label") or step.get("id") or "").strip()
        if label:
            labels.append(label)
    return _merge_unique(labels)


def _work_order_post_binding_spatial_pipeline(
    *,
    composition_plan: Mapping[str, Any],
    room_analysis_available: bool,
    reference_image: str,
    actor_label_prefix: str,
) -> Dict[str, Any]:
    bound_json = "<SPATIAL_BIND_GENERATED_ASSETS_TO_COMPOSITION_RESULT_JSON>"
    scale_json = "<SPATIAL_PLAN_ASSET_SCALE_CORRECTIONS_RESULT_JSON_OR_BINDING_RESULT_JSON>"
    anchored_json = "<SPATIAL_PLAN_SUPPORT_SURFACE_ANCHORS_RESULT_JSON_OR_SCALE_CORRECTED_BINDING_JSON>"
    layout_json = "<SPATIAL_PREFLIGHT_INTERIOR_LAYOUT_RESULT_JSON>"
    layout_corrected_json = "<SPATIAL_PLAN_LAYOUT_PREFLIGHT_CORRECTIONS_RESULT_JSON_OR_SUPPORT_ANCHORED_BINDING_JSON>"
    validation_json = "<SPATIAL_VALIDATE_PLACEMENT_RESULT_JSON>"
    candidate_clearance_json = "<SPATIAL_PREFLIGHT_CANDIDATE_CLEARANCE_RESULT_JSON>"
    room_analysis_json = "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>" if room_analysis_available else "<OPTIONAL_SPATIAL_ANALYZE_ROOM_RESULT_JSON>"
    actor_labels = _work_order_actor_labels(composition_plan)
    artifact_name = f"spatial_worldbuilding_{_safe_asset_stem(actor_label_prefix or 'interior', 'interior').lower()}_review"
    pipeline = {
        "schema": "unreal_mcp_ghost.spatial_post_binding_pipeline.v1",
        "status": "ready_for_bound_asset_review" if composition_plan else "needs_composition_plan",
        "actor_labels": actor_labels,
        "actor_count": len(actor_labels),
        "source_composition_json": bound_json,
        "scale_correction_handoff": {
            "tool": "spatial_plan_asset_scale_corrections",
            "arguments": {
                "composition_plan_json": bound_json,
                "allow_non_uniform_scale": False,
                "include_updated_plan": True,
            },
            "enabled": bool(composition_plan),
        },
        "support_surface_anchor_handoff": {
            "tool": "spatial_plan_support_surface_anchors",
            "arguments": {
                "composition_plan_json": scale_json,
                "room_analysis_json": room_analysis_json,
                "include_updated_plan": True,
            },
            "enabled": bool(composition_plan),
        },
        "layout_preflight_handoff": {
            "tool": "spatial_preflight_interior_layout",
            "arguments": {
                "composition_plan_json": anchored_json,
                "room_analysis_json": room_analysis_json,
            },
            "enabled": bool(composition_plan),
        },
        "layout_preflight_correction_handoff": {
            "tool": "spatial_plan_layout_preflight_corrections",
            "arguments": {
                "composition_plan_json": anchored_json,
                "layout_preflight_json": layout_json,
            },
            "enabled": bool(composition_plan),
        },
        "candidate_clearance_handoff": {
            "tool": "spatial_preflight_candidate_clearance",
            "arguments": {
                "composition_plan_json": layout_corrected_json,
                "room_analysis_json": room_analysis_json,
                "actor_query": actor_label_prefix or "",
                "ignore_actor_labels": actor_labels,
            },
            "enabled": bool(composition_plan),
        },
        "apply_handoff": {
            "tool": "spatial_apply_composition_plan",
            "arguments": {
                "composition_plan_json": layout_corrected_json,
                "dry_run": True,
                "block_on_preflight_errors": True,
                "block_on_spatial_fit_review": True,
            },
            "enabled": bool(composition_plan),
        },
        "validation_handoff": {
            "tool": "spatial_validate_placement",
            "arguments": {
                "actors": actor_labels,
                "surface_tolerance": 15.0,
                "clearance_padding": 12.0,
                "include_evidence_handoff": True,
            },
            "enabled": bool(actor_labels),
        },
        "iteration_handoff": {
            "tool": "spatial_plan_composition_iteration",
            "arguments": {
                "composition_plan_json": layout_corrected_json,
                "validation_result_json": validation_json,
                "reference_image": reference_image,
            },
            "enabled": bool(composition_plan),
        },
        "candidate_clearance_iteration_handoff": {
            "tool": "spatial_plan_composition_iteration",
            "arguments": {
                "composition_plan_json": layout_corrected_json,
                "validation_result_json": candidate_clearance_json,
                "reference_image": reference_image,
            },
            "enabled": bool(composition_plan),
        },
        "viewport_evidence_handoff": [
            {
                "tool": "spatial_select_actors",
                "arguments": {
                    "actors": actor_labels,
                    "dry_run": True,
                    "allow_mutation": False,
                    "focus_viewport": False,
                },
                "enabled": bool(actor_labels),
            },
            {
                "tool": "focus_viewport",
                "arguments": {
                    "location": "<BOUND_COMPOSITION_CENTER_OR_SELECTED_ACTORS>",
                    "distance": 1600.0,
                },
                "enabled": bool(actor_labels),
            },
            {
                "tool": "viewport_capture_screenshot",
                "arguments": {
                    "artifact_name": artifact_name,
                    "show_ui": False,
                },
                "enabled": bool(actor_labels),
            },
        ],
        "workflow": [
            {"step": "bind_assets", "tool": "spatial_bind_generated_assets_to_composition", "reason": "Use existing project-asset and post-generation binding handoffs first."},
            {"step": "review_scale", "tool": "spatial_plan_asset_scale_corrections", "handoff_key": "scale_correction_handoff"},
            {"step": "anchor_support_surfaces", "tool": "spatial_plan_support_surface_anchors", "handoff_key": "support_surface_anchor_handoff"},
            {"step": "preflight_layout", "tool": "spatial_preflight_interior_layout", "handoff_key": "layout_preflight_handoff"},
            {"step": "repair_layout_if_needed", "tool": "spatial_plan_layout_preflight_corrections", "handoff_key": "layout_preflight_correction_handoff"},
            {"step": "preflight_live_candidate_clearance", "tool": "spatial_preflight_candidate_clearance", "handoff_key": "candidate_clearance_handoff"},
            {"step": "dry_run_apply", "tool": "spatial_apply_composition_plan", "handoff_key": "apply_handoff"},
            {"step": "validate_placement", "tool": "spatial_validate_placement", "handoff_key": "validation_handoff"},
            {"step": "iterate_from_validation_or_clearance", "tool": "spatial_plan_composition_iteration", "handoff_keys": ["iteration_handoff", "candidate_clearance_iteration_handoff"]},
            {"step": "capture_viewport_evidence", "tools": ["spatial_select_actors", "focus_viewport", "viewport_capture_screenshot"], "handoff_key": "viewport_evidence_handoff"},
        ],
        "review_notes": [
            "All placement remains dry-run-first until the user explicitly approves mutation.",
            "Use candidate-clearance blockers or placement validation output as the next iteration planner input.",
            "Viewport evidence is required for human review before accepting a generated interior composition.",
        ],
    }
    return pipeline


def _plan_worldbuilding_work_order(
    *,
    design_brief: str,
    reference_image: str,
    room_analysis: Mapping[str, Any],
    detected_items: Sequence[Mapping[str, Any]],
    scene_graph: Mapping[str, Any],
    asset_catalog: Sequence[Mapping[str, Any]],
    room_type: str,
    room_dimensions: Sequence[float],
    room_origin: Sequence[float],
    style: str,
    requested_zones: Sequence[str],
    required_props: Sequence[str],
    content_path: str,
    actor_label_prefix: str,
    generate_missing_with_tripo: bool,
    include_architectural_fill: bool,
    max_items: int,
    minimum_asset_score: float,
    max_candidates_per_prop: int,
) -> Dict[str, Any]:
    safe_content_path = _normalize_content_path(content_path)
    safe_prefix = actor_label_prefix or _safe_asset_stem(room_type, "Interior")
    analysis = dict(room_analysis or {})
    functional_zone_plan = _plan_functional_zones(
        room_type=room_type,
        room_dimensions=room_dimensions,
        room_origin=room_origin,
        room_analysis=analysis,
        detected_items=detected_items,
        composition_plan={},
        requested_zones=requested_zones,
        min_zone_size_cm=120.0,
        include_updated_room_analysis=True,
        limit=16,
    )
    if functional_zone_plan.get("updated_room_analysis"):
        analysis = dict(functional_zone_plan["updated_room_analysis"])
    zones = list(functional_zone_plan.get("zones", []) or analysis.get("zones", []) or _room_zones(room_type, room_origin, room_dimensions))
    prop_program = _plan_interior_prop_program(
        room_type=room_type,
        room_dimensions=room_dimensions,
        room_origin=room_origin,
        functional_zone_plan=functional_zone_plan,
        room_analysis=analysis,
        detected_items=detected_items,
        requested_zones=requested_zones,
        required_props=required_props,
        omit_props=[],
        existing_asset_paths=[],
        style=style,
        intent=design_brief,
        include_architectural_fill=include_architectural_fill,
        limit=max_items,
    )
    decomposition_request: Dict[str, Any] = {}
    reconstruction_plan: Dict[str, Any] = {}
    composition_plan: Dict[str, Any] = {}
    source_outputs: Dict[str, Any] = {}
    source_mode = "direct_room_composition"

    if reference_image:
        source_mode = "screenshot_reconstruction" if detected_items else "screenshot_first"
        decomposition_request = _plan_screenshot_decomposition_request(
            reference_image=reference_image,
            image_size=None,
            room_type=room_type,
            room_dimensions=room_dimensions,
            room_origin=room_origin,
            room_analysis=analysis,
            style=style,
            intent=design_brief,
            include_architectural_fill=include_architectural_fill,
            prefer_crop_boxes=True,
            max_items=max_items,
        )
        if detected_items:
            reconstruction_plan = _plan_screenshot_reconstruction(
                reference_image=reference_image,
                detected_items=detected_items,
                room_type=room_type,
                room_dimensions=room_dimensions,
                room_origin=room_origin,
                style=style,
                intent=design_brief,
                existing_asset_paths=[],
                content_path=safe_content_path,
                actor_label_prefix=safe_prefix or "ReferenceRebuild",
                generate_missing_with_tripo=generate_missing_with_tripo,
                include_text_fallbacks=True,
                limit=max_items,
                required_props=required_props,
                include_architectural_fill=include_architectural_fill,
                include_zone_recommendations=False,
                room_analysis=analysis,
                scene_graph=scene_graph,
            )
            reconstructed_zone_plan = reconstruction_plan.get("functional_zone_plan")
            if isinstance(reconstructed_zone_plan, Mapping):
                functional_zone_plan = dict(reconstructed_zone_plan)
            reconstructed_prop_program = reconstruction_plan.get("prop_program")
            if isinstance(reconstructed_prop_program, Mapping):
                prop_program = dict(reconstructed_prop_program)
            raw_composition = reconstruction_plan.get("composition_plan")
            composition_plan = dict(raw_composition) if isinstance(raw_composition, Mapping) else {}
            source_outputs = reconstruction_plan
    else:
        composition_plan = _plan_interior_composition(
            room_type=room_type,
            room_dimensions=room_dimensions,
            room_origin=room_origin,
            functional_zone_plan=functional_zone_plan,
            prop_program=prop_program,
            style=style,
            intent=design_brief,
            screenshot_reference="",
            screenshot_observations=[],
            existing_asset_paths=[],
            required_props=required_props,
            omit_props=[],
            content_path=safe_content_path,
            actor_label_prefix=safe_prefix,
            generate_missing_with_tripo=generate_missing_with_tripo,
            include_image_to_model_handoffs=False,
            limit=max_items,
            detected_items=[],
            room_analysis=analysis,
        )
        source_outputs = composition_plan

    asset_resolution: Dict[str, Any] = {}
    if asset_catalog and composition_plan:
        asset_resolution = _resolve_assets_for_composition(
            composition_plan=composition_plan,
            asset_catalog=asset_catalog,
            minimum_score=minimum_asset_score,
            max_candidates_per_prop=max_candidates_per_prop,
            include_resolved_existing=False,
            tripo_source_json=json.dumps(source_outputs or composition_plan, sort_keys=True),
        )

    post_asset_resolution_generation_source: Dict[str, Any] = {}
    tripo_source_outputs: Mapping[str, Any] = source_outputs or composition_plan
    tripo_composition_plan: Mapping[str, Any] = composition_plan
    if asset_resolution:
        post_asset_resolution_generation_source = _composition_after_project_asset_resolution(
            composition_plan=composition_plan,
            source_outputs=source_outputs or composition_plan,
            asset_resolution=asset_resolution,
        )
        tripo_source_outputs = post_asset_resolution_generation_source.get("source_outputs", {}) or tripo_source_outputs
        tripo_composition_plan = post_asset_resolution_generation_source.get("composition_plan", {}) or tripo_composition_plan

    tripo_batch: Dict[str, Any] = {}
    tripo_expected_count = 0
    if composition_plan and generate_missing_with_tripo:
        if asset_resolution:
            tripo_batch = _plan_spatial_tripo_generation_batch(
                source_outputs=tripo_source_outputs,
                composition_plan=tripo_composition_plan,
                content_path=safe_content_path,
                session_name=f"spatial_{_safe_asset_stem(room_type, 'room').lower()}",
                prefer_image_crops=bool(reference_image),
                include_text_fallbacks=True,
                confirm_spend=False,
                limit=max_items,
            )
            tripo_expected_count = int(tripo_batch.get("job_count") or 0)
        else:
            tripo_batch = _plan_spatial_tripo_generation_batch(
                source_outputs=source_outputs or composition_plan,
                composition_plan=composition_plan,
                content_path=safe_content_path,
                session_name=f"spatial_{_safe_asset_stem(room_type, 'room').lower()}",
                prefer_image_crops=bool(reference_image),
                include_text_fallbacks=True,
                confirm_spend=False,
                limit=max_items,
            )
            tripo_expected_count = int(tripo_batch.get("job_count") or 0)
    tripo_crop_requirements = _tripo_crop_manifest_requirements(tripo_batch) if tripo_batch else {
        "required": False,
        "count": 0,
        "job_ids": [],
        "jobs": [],
        "status": "not_required",
        "handoff": {"tool": "spatial_prepare_screenshot_crop_manifest", "arguments": {}, "enabled": False},
    }
    tripo_crop_blocker_count = int(tripo_crop_requirements.get("count") or 0)
    crop_manifest_handoff = tripo_crop_requirements.get("handoff") if isinstance(tripo_crop_requirements.get("handoff"), Mapping) else {}
    crop_manifest_arguments = crop_manifest_handoff.get("arguments") if isinstance(crop_manifest_handoff.get("arguments"), Mapping) else {}

    requirements = _work_order_prop_requirements(composition_plan)
    zone_program = _zone_program_from_composition(
        zones=zones,
        requested_zones=requested_zones,
        composition_plan=composition_plan,
    )
    readiness_preview = _plan_worldbuilding_readiness(
        reference_image=reference_image,
        room_analysis=analysis,
        functional_zone_plan=functional_zone_plan,
        prop_program=prop_program,
        decomposition_request=decomposition_request,
        detection_preflight={},
        scene_graph=scene_graph,
        reconstruction_plan=reconstruction_plan,
        composition_plan=composition_plan,
        asset_resolution=asset_resolution,
        tripo_batch=tripo_batch,
        asset_binding={},
        asset_scale_correction={},
        support_surface_anchors={},
        layout_preflight={},
        layout_preflight_correction={},
        candidate_clearance={},
        apply_result={},
        validation_result={},
        iteration_plan={},
        viewport_evidence={},
        require_room_analysis=True,
        require_scene_graph=bool(reference_image),
        require_viewport_evidence=True,
    )
    status = _worldbuilding_work_order_status(
        reference_image=reference_image,
        detected_items=detected_items,
        composition_plan=composition_plan,
        asset_resolution=asset_resolution,
        tripo_expected_count=tripo_expected_count,
        tripo_crop_blocker_count=tripo_crop_blocker_count,
    )
    composition_json_placeholder = "<COMPOSITION_PLAN_JSON>"
    if composition_plan:
        composition_json_placeholder = json.dumps(composition_plan, sort_keys=True)
    existing_asset_binding_handoff = (
        dict(asset_resolution.get("binding_handoff"))
        if isinstance(asset_resolution.get("binding_handoff"), Mapping)
        else {
            "tool": "spatial_bind_generated_assets_to_composition",
            "arguments": {},
            "enabled": False,
        }
    )
    post_generation_binding_source_json = (
        str(post_asset_resolution_generation_source.get("source_outputs_json") or "")
        if post_asset_resolution_generation_source
        else composition_json_placeholder
    )
    post_generation_binding_handoff = {
        "tool": "spatial_bind_generated_assets_to_composition",
        "arguments": {
            "composition_plan_json": post_generation_binding_source_json,
            "import_results_json": "<GEN_TRIPO_IMPORT_TO_PROJECT_RESULTS_JSON>",
            "include_unresolved_steps": True,
        },
        "enabled": bool(composition_plan and (tripo_expected_count or asset_resolution)),
        "reason": "Bind generated Tripo imports back into the same post-project-asset-resolution composition so reused project assets and generated props place together.",
    }
    post_binding_spatial_pipeline = _work_order_post_binding_spatial_pipeline(
        composition_plan=(
            post_asset_resolution_generation_source.get("composition_plan")
            if post_asset_resolution_generation_source
            else composition_plan
        ) or composition_plan,
        room_analysis_available=bool(analysis),
        reference_image=reference_image,
        actor_label_prefix=safe_prefix,
    )

    workflow = [
        {
            "step": "measure_space",
            "tool": "spatial_analyze_room",
            "ready": bool(analysis),
            "arguments": {"room_type": room_type, "include_planner_handoff": True},
        },
        {
            "step": "decompose_reference",
            "tool": "spatial_prepare_screenshot_decomposition_request",
            "enabled": bool(reference_image),
            "ready": bool(not reference_image or detected_items),
            "arguments": {
                "reference_image": reference_image or "<REFERENCE_IMAGE>",
                "room_type": room_type,
                "room_dimensions": list(room_dimensions),
                "room_origin": list(room_origin),
                "include_architectural_fill": include_architectural_fill,
            },
        },
        {
            "step": "preflight_and_graph_reference",
            "tools": ["spatial_preflight_screenshot_detections", "spatial_infer_screenshot_scene_graph"],
            "enabled": bool(reference_image and detected_items),
            "ready": bool(scene_graph),
        },
        {
            "step": "plan_prop_program",
            "tool": "spatial_plan_interior_prop_program",
            "ready": bool(prop_program.get("prop_count")),
            "arguments": {
                "functional_zone_plan_json": "<SPATIAL_INFER_FUNCTIONAL_ZONES_RESULT_JSON>",
                "required_props": list(required_props),
                "include_architectural_fill": include_architectural_fill,
            },
        },
        {
            "step": "plan_composition",
            "tool": "spatial_plan_screenshot_reconstruction" if reference_image else "spatial_plan_interior_composition",
            "ready": bool(composition_plan),
        },
        {
            "step": "catalog_project_assets",
            "tool": "spatial_catalog_project_assets",
            "ready": bool(asset_catalog),
            "reason": "Reuse project assets before preparing Tripo generation.",
        },
        {
            "step": "resolve_project_assets",
            "tool": "spatial_resolve_project_assets",
            "ready": bool(asset_resolution),
            "arguments": {
                "composition_plan_json": composition_json_placeholder,
                "asset_catalog_json": "<PROJECT_ASSET_CATALOG_JSON>",
                "minimum_score": minimum_asset_score,
            },
        },
        {
            "step": "bind_existing_project_assets",
            "tool": "spatial_bind_generated_assets_to_composition",
            "enabled": bool(existing_asset_binding_handoff.get("enabled")),
            "prepared": bool(existing_asset_binding_handoff.get("enabled")),
            "arguments": dict(existing_asset_binding_handoff.get("arguments") or {}),
            "reason": "Bind catalog-resolved /Game assets into a dry-run composition before generating missing props.",
        },
        {
            "step": "prepare_guarded_tripo_batch",
            "tool": "spatial_prepare_tripo_generation_batch",
            "enabled": bool(generate_missing_with_tripo),
            "ready": bool(tripo_batch and tripo_batch.get("status") in {"no_generation_needed", "ready_for_tripo_submission"}),
            "expected_job_count": tripo_expected_count,
            "arguments": {
                "composition_plan_json": (
                    post_asset_resolution_generation_source.get("source_outputs_json")
                    if asset_resolution and post_asset_resolution_generation_source
                    else composition_json_placeholder
                ),
                "prefer_image_crops": bool(reference_image),
                "confirm_spend": False,
            },
            "prepared": bool(tripo_batch),
            "resolved_asset_count": len(post_asset_resolution_generation_source.get("resolved_ids", []) or []) if asset_resolution else 0,
            "unresolved_generation_ids": list(post_asset_resolution_generation_source.get("unresolved_ids", []) or []) if asset_resolution else [],
        },
        {
            "step": "prepare_screenshot_crop_manifest",
            "tool": "spatial_prepare_screenshot_crop_manifest",
            "enabled": bool(tripo_crop_blocker_count),
            "ready": bool(not tripo_crop_blocker_count),
            "blocked_job_count": tripo_crop_blocker_count,
            "blocked_job_ids": list(tripo_crop_requirements.get("job_ids") or []),
            "arguments": {
                **dict(crop_manifest_arguments),
                "blocked_job_ids": list(tripo_crop_requirements.get("job_ids") or []),
            },
            "reason": "Write concrete local screenshot prop crops before Tripo image-to-model spend.",
        },
        {
            "step": "bind_review_apply_validate",
            "tools": [
                "spatial_bind_generated_assets_to_composition",
                "spatial_plan_asset_scale_corrections",
                "spatial_plan_support_surface_anchors",
                "spatial_preflight_interior_layout",
                "spatial_plan_layout_preflight_corrections",
                "spatial_preflight_candidate_clearance",
                "spatial_apply_composition_plan",
                "spatial_validate_placement",
                "spatial_plan_composition_iteration",
            ],
            "ready": False,
            "binding_handoffs": {
                "existing_project_assets": existing_asset_binding_handoff,
                "after_tripo_imports": post_generation_binding_handoff,
            },
            "spatial_pipeline": post_binding_spatial_pipeline,
            "reason": "Mutation remains gated until assets are bound, spatial fit is reviewed, dry-run placement passes, and validation/evidence are captured.",
        },
        {
            "step": "compile_readiness",
            "tool": "spatial_compile_worldbuilding_readiness",
            "ready": False,
        },
    ]

    return {
        "schema": WORLDBUILDING_WORK_ORDER_SCHEMA,
        "status": status,
        "source_mode": source_mode,
        "design_brief": design_brief,
        "reference_image": reference_image,
        "room": {
            "type": room_type,
            "dimensions_cm": list(room_dimensions),
            "origin": list(room_origin),
            "style": style,
        },
        "zone_program": zone_program,
        "zone_count": len(zone_program),
        "requested_zones": list(requested_zones),
        "functional_zone_plan": functional_zone_plan,
        "prop_program": prop_program,
        "prop_requirements": requirements,
        "prop_requirement_count": len(requirements),
        "composition_plan": composition_plan,
        "decomposition_request": decomposition_request,
        "reconstruction_plan": reconstruction_plan,
        "asset_strategy": {
            "catalog_applied": bool(asset_catalog),
            "catalog_count": len(asset_catalog),
            "resolution": asset_resolution,
            "post_resolution_generation_source": post_asset_resolution_generation_source,
            "existing_asset_binding_handoff": existing_asset_binding_handoff,
            "resolved_count": int(asset_resolution.get("resolved_count") or 0) if asset_resolution else 0,
            "unresolved_count": int(asset_resolution.get("unresolved_count") or 0) if asset_resolution else len([item for item in requirements if item.get("needs_generation")]),
        },
        "tripo_strategy": {
            "enabled": bool(generate_missing_with_tripo),
            "expected_job_count": tripo_expected_count,
            "batch_preview": tripo_batch,
            "generation_source": post_asset_resolution_generation_source,
            "post_generation_binding_handoff": post_generation_binding_handoff,
            "crop_manifest_required": bool(tripo_crop_blocker_count),
            "blocked_by_crop_manifest_count": tripo_crop_blocker_count,
            "blocked_crop_job_ids": list(tripo_crop_requirements.get("job_ids") or []),
            "crop_manifest_handoff": {
                **dict(crop_manifest_handoff),
                "arguments": {
                    **dict(crop_manifest_arguments),
                    "blocked_job_ids": list(tripo_crop_requirements.get("job_ids") or []),
                },
            },
            "confirm_spend": False,
            "user_confirmation_required": bool(generate_missing_with_tripo and tripo_expected_count),
            "policy": [
                "Do not submit paid Tripo jobs from this work order.",
                "Prefer project asset resolution before generating.",
                "Prepare screenshot crop manifests before Tripo image-to-model spend when crop blockers are present.",
                "Use cropped screenshot props for image-to-model when crop evidence exists; otherwise use text fallback prompts.",
                "Review generated bounds and spatial fit before dry-run placement.",
            ],
        },
        "placement_strategy": {
            "post_binding_spatial_pipeline": post_binding_spatial_pipeline,
            "dry_run_required": True,
            "mutation_requires_user_approval": True,
        },
        "quality_gates": [
            "live_room_dimensions_or_explicit_room_dimensions",
            "screenshot_decomposition_and_scene_graph_when_reference_image_is_used",
            "project_asset_resolution_before_tripo_spend",
            "screenshot_crop_manifest_before_tripo_image_spend",
            "explicit_user_spend_confirmation_for_tripo",
            "generated_asset_spatial_fit_review",
            "generated_asset_scale_correction_before_mutation",
            "support_surface_anchoring_before_layout_preflight",
            "functional_zone_inference_before_composition",
            "interior_prop_program_before_composition",
            "layout_preflight_before_mutation",
            "layout_preflight_correction_before_mutation_when_preflight_blocks",
            "live_candidate_clearance_before_mutation",
            "dry_run_first_fit_gated_apply",
            "placement_validation_and_iteration",
            "viewport_evidence_for_human_review",
        ],
        "workflow": workflow,
        "readiness_preview": {
            "schema": readiness_preview.get("schema"),
            "status": readiness_preview.get("status"),
            "blocking_gate_count": readiness_preview.get("blocking_gate_count"),
            "remaining_gate_count": readiness_preview.get("remaining_gate_count"),
            "next_actions": readiness_preview.get("next_actions", [])[:8],
        },
        "readiness_handoff": {
            "tool": "spatial_compile_worldbuilding_readiness",
            "arguments": {
                "reference_image": reference_image,
                "room_analysis_json": "<SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
                "decomposition_request_json": "<SPATIAL_PREPARE_SCREENSHOT_DECOMPOSITION_REQUEST_RESULT_JSON>",
                "scene_graph_json": "<SPATIAL_INFER_SCREENSHOT_SCENE_GRAPH_RESULT_JSON>",
                "composition_plan_json": "<COMPOSITION_OR_RECONSTRUCTION_RESULT_JSON>",
                "asset_resolution_json": "<SPATIAL_RESOLVE_PROJECT_ASSETS_RESULT_JSON>",
                "tripo_batch_json": "<SPATIAL_PREPARE_TRIPO_GENERATION_BATCH_RESULT_JSON>",
                "asset_binding_json": "<SPATIAL_BIND_GENERATED_ASSETS_TO_COMPOSITION_RESULT_JSON>",
                "asset_scale_correction_json": "<SPATIAL_PLAN_ASSET_SCALE_CORRECTIONS_RESULT_JSON>",
                "support_surface_anchors_json": "<SPATIAL_PLAN_SUPPORT_SURFACE_ANCHORS_RESULT_JSON>",
                "functional_zone_plan_json": "<SPATIAL_INFER_FUNCTIONAL_ZONES_RESULT_JSON>",
                "prop_program_json": "<SPATIAL_PLAN_INTERIOR_PROP_PROGRAM_RESULT_JSON>",
                "layout_preflight_json": "<SPATIAL_PREFLIGHT_INTERIOR_LAYOUT_RESULT_JSON>",
                "layout_preflight_correction_json": "<SPATIAL_PLAN_LAYOUT_PREFLIGHT_CORRECTIONS_RESULT_JSON>",
                "candidate_clearance_json": "<SPATIAL_PREFLIGHT_CANDIDATE_CLEARANCE_RESULT_JSON>",
                "apply_result_json": "<SPATIAL_APPLY_COMPOSITION_PLAN_RESULT_JSON>",
                "validation_result_json": "<SPATIAL_VALIDATE_PLACEMENT_RESULT_JSON>",
                "viewport_evidence_json": "<VIEWPORT_CAPTURE_EVIDENCE_JSON>",
            },
        },
        "legal_review": {
            "requires_review": False,
            "notes": [
                "This is a Ghost-owned work-order planner over Ghost spatial schemas and handoffs.",
                "It does not execute Unreal mutation, paid Tripo calls, computer vision, or Epic native SceneTools code.",
                "Future direct reuse of Epic native MCP/SceneTools implementation details requires legal review.",
            ],
        },
    }


def _classify_policy(asset_paths: Sequence[str], intent: str, requested_policy: str) -> Dict[str, Any]:
    text = " ".join([intent or "", *asset_paths]).lower()
    scores = {
        "city_block": sum(token in text for token in ("city", "building", "block", "road", "street", "district", "urban")),
        "gameplay_poi": sum(token in text for token in ("poi", "pickup", "quest", "objective", "marker", "interaction")),
        "lighting": sum(token in text for token in ("light", "lamp", "lantern", "emissive", "neon")),
        "vfx": sum(token in text for token in ("vfx", "fx", "niagara", "particle", "smoke", "spark")),
        "set_dressing": sum(token in text for token in ("prop", "chair", "table", "crate", "barrel", "decal", "clutter", "dressing")),
        "interior_composition": sum(token in text for token in ("apartment", "interior", "kitchen", "bedroom", "living", "cabinet", "fridge", "stove", "sink")),
    }
    if requested_policy != "auto":
        resolved = requested_policy
        confidence = 1.0
    else:
        resolved = max(scores, key=lambda key: scores[key])
        if scores[resolved] <= 0:
            resolved = "set_dressing"
            confidence = 0.35
        else:
            confidence = min(0.95, 0.45 + scores[resolved] * 0.15)
    return {"resolved_policy": resolved, "scores": scores, "confidence": confidence}


def _placement_policy_defaults(policy: str, base_spacing: float) -> Dict[str, Any]:
    defaults = {
        "manual": {"layout": "line", "spacing": base_spacing, "tags": [], "data_layers": []},
        "set_dressing": {"layout": "grid", "spacing": max(base_spacing, 350.0), "tags": ["SetDressing"], "data_layers": ["World_SetDressing"]},
        "city_block": {"layout": "grid", "spacing": max(base_spacing, 1600.0), "tags": ["Worldbuilding", "CityBlock"], "data_layers": ["World_City"]},
        "gameplay_poi": {"layout": "grid", "spacing": max(base_spacing, 600.0), "tags": ["Gameplay_POI"], "data_layers": ["Gameplay_POIs"]},
        "lighting": {"layout": "line", "spacing": max(base_spacing, 800.0), "tags": ["Lighting"], "data_layers": ["Lighting"]},
        "vfx": {"layout": "line", "spacing": max(base_spacing, 700.0), "tags": ["VFX"], "data_layers": ["VFX"]},
        "linear_showcase": {"layout": "line", "spacing": max(base_spacing, 450.0), "tags": ["Showcase"], "data_layers": []},
        "vertical_stack": {"layout": "stack", "spacing": max(base_spacing, 250.0), "tags": ["StackedPlacement"], "data_layers": []},
        "interior_composition": {"layout": "grid", "spacing": max(base_spacing, 300.0), "tags": ["Interior", "SetDressing"], "data_layers": ["World_Interiors"]},
    }
    return defaults.get(policy, defaults["set_dressing"])


def _infer_placement_policy(
    *,
    asset_paths: Sequence[str],
    intent: str,
    policy: str,
    layout_hint: str,
    base_spacing: float,
    actor_label_prefix: str,
    tags: Sequence[str],
    data_layer_names: Sequence[str],
) -> Dict[str, Any]:
    classification = _classify_policy(asset_paths, intent, policy)
    resolved_policy = classification["resolved_policy"]
    defaults = _placement_policy_defaults(resolved_policy, base_spacing)
    effective_layout = layout_hint if policy == "manual" else str(defaults["layout"])
    effective_spacing = float(base_spacing if policy == "manual" else defaults["spacing"])
    effective_tags = _merge_unique(tags, defaults["tags"] if policy != "manual" else [])
    recommended_data_layers = _merge_unique(defaults["data_layers"] if policy != "manual" else [])
    asset_names = [_asset_name_from_path(path) for path in asset_paths]

    return {
        "schema": PLACEMENT_POLICY_SCHEMA,
        "policy": policy,
        "resolved_policy": resolved_policy,
        "confidence": classification["confidence"],
        "scores": classification["scores"],
        "intent": intent,
        "asset_count": len(asset_paths),
        "asset_names": asset_names,
        "effective_layout": effective_layout,
        "effective_spacing": effective_spacing,
        "effective_tags": effective_tags,
        "data_layer_names": list(data_layer_names),
        "recommended_data_layer_names": recommended_data_layers,
        "actor_label_prefix": actor_label_prefix,
        "placement_arguments": {
            "spatial_place_selected_assets": {
                "asset_paths": list(asset_paths),
                "placement_layout": effective_layout,
                "placement_spacing": effective_spacing,
                "actor_label_prefix": actor_label_prefix,
                "tags": effective_tags,
                "data_layer_names": list(data_layer_names),
                "dry_run": True,
            },
            "spatial_content_selection_context": {
                "placement_layout": effective_layout,
                "placement_spacing": effective_spacing,
                "actor_label_prefix": actor_label_prefix,
                "tags": effective_tags,
                "data_layer_names": list(data_layer_names),
            },
        },
        "notes": [
            "Recommended Data Layer names are advisory unless explicitly copied into data_layer_names.",
            "Run placement tools in dry_run mode before allowing editor mutation.",
            "Use viewport evidence tools after placement for human-visible validation.",
        ],
    }


def _local_result(
    *,
    success: bool,
    stage: str,
    tool: str,
    message: str,
    inputs: Dict[str, Any],
    t0: float,
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
) -> str:
    payload = {
        "success": success,
        "schema": SPATIAL_RESULT_SCHEMA,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": tool, "duration_ms": int((time.monotonic() - t0) * 1000)},
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _json_result(
    stage: str,
    tool: str,
    inputs: Dict[str, Any],
    result: Dict[str, Any],
    t0: float,
    output_schema: str,
) -> str:
    if not isinstance(result, dict):
        result = {
            "success": False,
            "stage": stage,
            "message": "Unreal execution returned a non-object payload",
            "outputs": {"raw": str(result)},
            "warnings": [],
            "errors": ["Unreal execution returned a non-object payload"],
            "log_tail": [],
        }

    payload = dict(result)
    payload["schema"] = SPATIAL_RESULT_SCHEMA
    payload["stage"] = payload.get("stage") or stage
    payload["inputs"] = inputs
    payload.setdefault("outputs", {})
    if isinstance(payload["outputs"], dict):
        payload["outputs"].setdefault("schema", output_schema)
    payload.setdefault("warnings", [])
    payload.setdefault("errors", [])
    payload.setdefault("log_tail", [])
    payload.setdefault("message", "Operation completed")
    if payload.get("errors") and payload.get("success") is not False:
        payload["success"] = False
        if payload.get("message") == "Operation completed":
            payload["message"] = "Operation completed with spatial awareness errors"
    payload.setdefault("success", not bool(payload.get("errors")))

    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    meta.update({"tool": tool, "duration_ms": int((time.monotonic() - t0) * 1000)})
    payload["meta"] = meta
    return json.dumps(payload, indent=2, sort_keys=True)


def _common_scene_code(
    *,
    include_hidden: bool,
    class_filter: str,
    tag_filter: str,
    limit: int,
    include_components: bool = False,
) -> str:
    return textwrap.dedent(
        f"""\
        import math
        import unreal

        include_hidden = {bool(include_hidden)!r}
        class_filter = {str(class_filter or '').strip().lower()!r}
        tag_filter = {str(tag_filter or '').strip().lower()!r}
        limit = max(1, int({int(limit)!r}))
        include_components = {bool(include_components)!r}

        def _vec_dict(value):
            if value is None:
                return None
            return {{"x": float(value.x), "y": float(value.y), "z": float(value.z)}}

        def _vec_tuple(value):
            if value is None:
                return None
            return (float(value.x), float(value.y), float(value.z))

        def _rot_dict(value):
            if value is None:
                return None
            return {{
                "pitch": float(getattr(value, "pitch", 0.0)),
                "yaw": float(getattr(value, "yaw", 0.0)),
                "roll": float(getattr(value, "roll", 0.0)),
            }}

        def _distance(a, b):
            if a is None or b is None:
                return None
            return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)))

        def _object_path(obj):
            if obj is None:
                return ""
            try:
                return obj.get_path_name()
            except Exception:
                return str(obj)

        def _class_name(obj):
            if obj is None:
                return ""
            try:
                return obj.get_class().get_name()
            except Exception:
                return obj.__class__.__name__

        def _actor_label(actor):
            try:
                label = actor.get_actor_label()
                if label:
                    return str(label)
            except Exception:
                pass
            try:
                return str(actor.get_name())
            except Exception:
                return str(actor)

        def _actor_tags(actor):
            tags = []
            for tag in list(getattr(actor, "tags", []) or []):
                text = str(tag)
                if text:
                    tags.append(text)
            return tags

        def _actor_hidden(actor):
            for attr_name in ("is_temporarily_hidden_in_editor", "is_hidden_ed", "is_hidden"):
                attr = getattr(actor, attr_name, None)
                if callable(attr):
                    try:
                        return bool(attr())
                    except TypeError:
                        continue
                    except Exception:
                        continue
            return False

        def _actor_bounds(actor):
            try:
                try:
                    origin, extent = actor.get_actor_bounds(False, False)
                except TypeError:
                    origin, extent = actor.get_actor_bounds(False)
                return {{
                    "origin": _vec_dict(origin),
                    "extent": _vec_dict(extent),
                    "min": {{
                        "x": float(origin.x) - float(extent.x),
                        "y": float(origin.y) - float(extent.y),
                        "z": float(origin.z) - float(extent.z),
                    }},
                    "max": {{
                        "x": float(origin.x) + float(extent.x),
                        "y": float(origin.y) + float(extent.y),
                        "z": float(origin.z) + float(extent.z),
                    }},
                }}
            except Exception as exc:
                return {{"error": str(exc)}}

        def _component_data(actor):
            if not include_components:
                return []
            components = []
            try:
                raw_components = list(actor.get_components_by_class(unreal.ActorComponent))
            except Exception as exc:
                _warnings.append("Could not enumerate actor components for " + _actor_label(actor) + ": " + str(exc))
                raw_components = []
            for component in raw_components[:64]:
                components.append({{
                    "name": str(component.get_name()) if hasattr(component, "get_name") else str(component),
                    "class": _class_name(component),
                    "path": _object_path(component),
                }})
            return components

        def _actor_data(actor, include_bounds=True, center=None):
            try:
                location = actor.get_actor_location()
            except Exception:
                location = None
            data = {{
                "label": _actor_label(actor),
                "name": str(actor.get_name()) if hasattr(actor, "get_name") else str(actor),
                "class": _class_name(actor),
                "path": _object_path(actor),
                "location": _vec_dict(location),
                "rotation": _rot_dict(actor.get_actor_rotation()) if hasattr(actor, "get_actor_rotation") else None,
                "scale": _vec_dict(actor.get_actor_scale3d()) if hasattr(actor, "get_actor_scale3d") else None,
                "tags": _actor_tags(actor),
                "hidden": _actor_hidden(actor),
            }}
            if include_bounds:
                data["bounds"] = _actor_bounds(actor)
            if include_components:
                data["components"] = _component_data(actor)
            if center is not None and location is not None:
                data["distance"] = _distance(_vec_tuple(location), center)
            return data

        def _actor_location_tuple(actor):
            try:
                return _vec_tuple(actor.get_actor_location())
            except Exception as exc:
                _warnings.append("Could not read actor location for " + _actor_label(actor) + ": " + str(exc))
                return None

        def _get_actor_subsystem():
            subsystem_class = getattr(unreal, "EditorActorSubsystem", None)
            if subsystem_class is None:
                return None
            try:
                return unreal.get_editor_subsystem(subsystem_class)
            except Exception as exc:
                _warnings.append("EditorActorSubsystem is unavailable: " + str(exc))
                return None

        _actor_subsystem = _get_actor_subsystem()

        def _all_level_actors():
            if _actor_subsystem is not None and hasattr(_actor_subsystem, "get_all_level_actors"):
                try:
                    return list(_actor_subsystem.get_all_level_actors())
                except Exception as exc:
                    _warnings.append("EditorActorSubsystem.get_all_level_actors failed: " + str(exc))
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "get_all_level_actors"):
                try:
                    return list(editor_level_library.get_all_level_actors())
                except Exception as exc:
                    _warnings.append("EditorLevelLibrary.get_all_level_actors failed: " + str(exc))
            _errors.append("No Unreal Python API for enumerating level actors is available.")
            return []

        def _selected_actors():
            if _actor_subsystem is not None and hasattr(_actor_subsystem, "get_selected_level_actors"):
                try:
                    return list(_actor_subsystem.get_selected_level_actors())
                except Exception as exc:
                    _warnings.append("EditorActorSubsystem.get_selected_level_actors failed: " + str(exc))
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "get_selected_level_actors"):
                try:
                    return list(editor_level_library.get_selected_level_actors())
                except Exception as exc:
                    _warnings.append("EditorLevelLibrary.get_selected_level_actors failed: " + str(exc))
            return []

        def _actor_matches_filters(actor):
            if not include_hidden and _actor_hidden(actor):
                return False
            class_name = _class_name(actor).lower()
            if class_filter and class_filter not in class_name:
                return False
            if tag_filter:
                tag_text = " ".join(tag.lower() for tag in _actor_tags(actor))
                if tag_filter not in tag_text:
                    return False
            return True

        def _text_matches(actor, query_text):
            if not query_text:
                return True
            haystack = " ".join([
                _actor_label(actor),
                str(actor.get_name()) if hasattr(actor, "get_name") else "",
                _class_name(actor),
                _object_path(actor),
                " ".join(_actor_tags(actor)),
            ]).lower()
            return query_text.lower() in haystack

        def _find_actor(query_text):
            query_text = str(query_text or "").strip()
            if not query_text:
                return None
            query_lower = query_text.lower()
            candidates = _all_level_actors()
            for actor in candidates:
                values = [
                    _actor_label(actor),
                    str(actor.get_name()) if hasattr(actor, "get_name") else "",
                    _object_path(actor),
                ]
                if any(str(value).lower() == query_lower for value in values):
                    return actor
            for actor in candidates:
                if _text_matches(actor, query_lower):
                    return actor
            return None

        def _top_counts(counts, max_items=20):
            return [
                {{"name": key, "count": count}}
                for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:max_items]
            ]

        def _histograms(actors):
            class_counts = {{}}
            tag_counts = {{}}
            for actor in actors:
                class_name = _class_name(actor)
                class_counts[class_name] = class_counts.get(class_name, 0) + 1
                for tag in _actor_tags(actor):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            return _top_counts(class_counts), _top_counts(tag_counts)

        def _aggregate_bounds(actors):
            mins = [float("inf"), float("inf"), float("inf")]
            maxs = [float("-inf"), float("-inf"), float("-inf")]
            usable = 0
            for actor in actors:
                bounds = _actor_bounds(actor)
                if "min" not in bounds or "max" not in bounds:
                    continue
                min_v = bounds["min"]
                max_v = bounds["max"]
                mins[0] = min(mins[0], float(min_v["x"]))
                mins[1] = min(mins[1], float(min_v["y"]))
                mins[2] = min(mins[2], float(min_v["z"]))
                maxs[0] = max(maxs[0], float(max_v["x"]))
                maxs[1] = max(maxs[1], float(max_v["y"]))
                maxs[2] = max(maxs[2], float(max_v["z"]))
                usable += 1
            if usable == 0:
                return {{"available": False, "actor_count": 0}}
            return {{
                "available": True,
                "actor_count": usable,
                "min": {{"x": mins[0], "y": mins[1], "z": mins[2]}},
                "max": {{"x": maxs[0], "y": maxs[1], "z": maxs[2]}},
                "size": {{"x": maxs[0] - mins[0], "y": maxs[1] - mins[1], "z": maxs[2] - mins[2]}},
                "center": {{
                    "x": (maxs[0] + mins[0]) / 2.0,
                    "y": (maxs[1] + mins[1]) / 2.0,
                    "z": (maxs[2] + mins[2]) / 2.0,
                }},
            }}

        def _literal_vec(value):
            if value is None:
                return None
            return (float(value[0]), float(value[1]), float(value[2]))

        all_actors = _all_level_actors()
        filtered_actors = [actor for actor in all_actors if _actor_matches_filters(actor)]
        selected_actors = _selected_actors()
        """
    )


def _scene_overview_code(
    *,
    include_hidden: bool,
    class_filter: str,
    tag_filter: str,
    limit: int,
    include_actor_samples: bool,
    local_actor_query: str = "",
) -> str:
    return (
        _common_scene_code(
            include_hidden=include_hidden,
            class_filter=class_filter,
            tag_filter=tag_filter,
            limit=limit,
            include_components=False,
        )
        + textwrap.dedent(
            f"""\

            import hashlib
            import json

            _physical_content_classification_version = "unreal_mcp_ghost.physical_content_classification.v1"
            _physical_component_classes = {{
                "BrushComponent",
                "DynamicMeshComponent",
                "GeometryCacheComponent",
                "GeometryCollectionComponent",
                "GroomComponent",
                "HierarchicalInstancedStaticMeshComponent",
                "InstancedStaticMeshComponent",
                "LandscapeComponent",
                "NaniteDisplacedMeshComponent",
                "PoseableMeshComponent",
                "ProceduralMeshComponent",
                "SkeletalMeshComponent",
                "SplineMeshComponent",
                "StaticMeshComponent",
                "WaterBodyComponent",
            }}
            _physical_actor_classes = {{
                "Brush",
                "GeometryCollectionActor",
                "Landscape",
                "SkeletalMeshActor",
                "StaticMeshActor",
                "WaterBody",
                "WaterBodyCustom",
                "WaterBodyLake",
                "WaterBodyOcean",
                "WaterBodyRiver",
            }}
            _infrastructure_actor_classes = {{
                "HLODActor",
                "LevelBounds",
                "LevelInstanceEditorInstanceActor",
                "NavMeshBoundsVolume",
                "RecastNavMesh",
                "WorldDataLayers",
                "WorldPartitionMiniMap",
            }}
            _context_actor_classes = {{
                "AudioVolume",
                "CameraActor",
                "CullDistanceVolume",
                "DirectionalLight",
                "ExponentialHeightFog",
                "KillZVolume",
                "LightmassImportanceVolume",
                "PhysicsVolume",
                "PlayerStart",
                "PointLight",
                "PostProcessVolume",
                "PrecomputedVisibilityVolume",
                "RectLight",
                "SkyAtmosphere",
                "SkyLight",
                "SpotLight",
                "TargetPoint",
                "VolumetricCloud",
            }}
            _renderable_context_asset_tokens = (
                "/engine/maptemplates/sky/",
                "sm_skysphere",
            )
            _room_bounds_tag = {ROOM_BOUNDS_TAG.lower()!r}
            local_actor_query = {str(local_actor_query or '').strip()!r}

            def _component_observation(actor):
                try:
                    components = list(actor.get_components_by_class(unreal.ActorComponent))
                except Exception as exc:
                    return [], [], False, str(exc)
                truncated = len(components) > 256
                scanned = [component for component in components[:256] if component is not None]
                names = sorted({{_class_name(component) for component in scanned}})
                asset_paths = set()
                for component in scanned:
                    get_property = getattr(component, "get_editor_property", None)
                    if not callable(get_property):
                        continue
                    for property_name in (
                        "static_mesh",
                        "skeletal_mesh_asset",
                        "skeletal_mesh",
                        "geometry_cache",
                        "groom_asset",
                    ):
                        try:
                            asset = get_property(property_name)
                        except Exception:
                            continue
                        asset_path = _object_path(asset)
                        if asset_path:
                            asset_paths.add(asset_path)
                return names, sorted(asset_paths), truncated, ""

            def _physical_content_classification(actor):
                class_name = _class_name(actor)
                if class_name in _infrastructure_actor_classes:
                    return {{
                        "outcome": "excluded",
                        "reason": "world_or_editor_infrastructure_actor",
                        "class_name": class_name,
                        "component_classes": [],
                        "asset_paths": [],
                        "matched_component_classes": [],
                        "component_scan_truncated": False,
                        "component_scan_error": "",
                        "evidence": "observed_native_class_metadata",
                    }}
                if class_name in _context_actor_classes:
                    return {{
                        "outcome": "excluded",
                        "reason": "non_physical_context_actor",
                        "class_name": class_name,
                        "component_classes": [],
                        "asset_paths": [],
                        "matched_component_classes": [],
                        "component_scan_truncated": False,
                        "component_scan_error": "",
                        "evidence": "observed_native_class_metadata",
                    }}
                component_classes, asset_paths, scan_truncated, scan_error = _component_observation(actor)
                matches = sorted(set(component_classes) & _physical_component_classes)
                renderable_context_paths = sorted(
                    path for path in asset_paths
                    if any(token in path.lower() for token in _renderable_context_asset_tokens)
                )
                if matches and renderable_context_paths:
                    return {{
                        "outcome": "excluded",
                        "reason": "renderable_environment_context_actor",
                        "class_name": class_name,
                        "component_classes": component_classes,
                        "asset_paths": asset_paths,
                        "matched_component_classes": matches,
                        "matched_context_asset_paths": renderable_context_paths,
                        "component_scan_truncated": scan_truncated,
                        "component_scan_error": scan_error,
                        "evidence": "calculated_from_observed_asset_metadata",
                    }}
                if matches or class_name in _physical_actor_classes:
                    return {{
                        "outcome": "included",
                        "reason": "physical_content_component_or_actor_class",
                        "class_name": class_name,
                        "component_classes": component_classes,
                        "asset_paths": asset_paths,
                        "matched_component_classes": matches,
                        "component_scan_truncated": scan_truncated,
                        "component_scan_error": scan_error,
                        "evidence": "observed_native_component_and_class_metadata",
                    }}
                if scan_error:
                    outcome = "unresolved"
                    reason = "component_scan_failed_without_physical_class_match"
                elif scan_truncated:
                    outcome = "unresolved"
                    reason = "component_scan_truncated_without_physical_match"
                else:
                    outcome = "excluded"
                    reason = "no_physical_content_component"
                return {{
                    "outcome": outcome,
                    "reason": reason,
                    "class_name": class_name,
                    "component_classes": component_classes,
                    "asset_paths": asset_paths,
                    "matched_component_classes": [],
                    "component_scan_truncated": scan_truncated,
                    "component_scan_error": scan_error,
                    "evidence": "observed_native_component_and_class_metadata",
                }}

            def _actor_matches_local_query(actor, query_text):
                if _text_matches(actor, query_text):
                    return True
                query_lower = str(query_text or "").lower()
                if not query_lower:
                    return False
                classification = _physical_content_classification(actor)
                return any(query_lower in path.lower() for path in classification.get("asset_paths", []))

            def _classified_content_scope(actors):
                included = []
                included_classes = {{}}
                excluded_classes = {{}}
                exclusion_reasons = {{}}
                unresolved_classes = {{}}
                unresolved_reasons = {{}}
                component_matches = {{}}
                excluded_assets = {{}}
                largest_bounds = []
                for actor in actors:
                    classification = _physical_content_classification(actor)
                    class_name = classification["class_name"]
                    outcome = classification["outcome"]
                    reason = classification["reason"]
                    if outcome == "included":
                        included.append(actor)
                        included_classes[class_name] = included_classes.get(class_name, 0) + 1
                        for component_name in classification["matched_component_classes"]:
                            component_matches[component_name] = component_matches.get(component_name, 0) + 1
                        actor_bounds = _actor_bounds(actor)
                        if "min" in actor_bounds and "max" in actor_bounds:
                            min_v = actor_bounds["min"]
                            max_v = actor_bounds["max"]
                            size = {{
                                "x": float(max_v["x"]) - float(min_v["x"]),
                                "y": float(max_v["y"]) - float(min_v["y"]),
                                "z": float(max_v["z"]) - float(min_v["z"]),
                            }}
                            largest_bounds.append({{
                                "label": _actor_label(actor),
                                "class_name": class_name,
                                "path": _object_path(actor),
                                "bounds": actor_bounds,
                                "size": size,
                                "largest_dimension_cm": max(size.values()),
                                "component_classes": classification["component_classes"],
                                "asset_paths": classification["asset_paths"],
                                "evidence": classification["evidence"],
                            }})
                    elif outcome == "unresolved":
                        unresolved_classes[class_name] = unresolved_classes.get(class_name, 0) + 1
                        unresolved_reasons[reason] = unresolved_reasons.get(reason, 0) + 1
                    else:
                        excluded_classes[class_name] = excluded_classes.get(class_name, 0) + 1
                        exclusion_reasons[reason] = exclusion_reasons.get(reason, 0) + 1
                        for asset_path in classification.get("matched_context_asset_paths", []):
                            excluded_assets[asset_path] = excluded_assets.get(asset_path, 0) + 1
                largest_bounds.sort(key=lambda item: (-item["largest_dimension_cm"], item["path"]))
                included_paths = sorted(_object_path(actor) for actor in included)
                aggregate = _aggregate_bounds(included)
                return {{
                    "kind": "physical_content_actor_aggregate",
                    "classification_version": _physical_content_classification_version,
                    "evidence": "observed_native_component_and_class_metadata",
                    "bounds": aggregate,
                    "input_actor_count": len(actors),
                    "included_actor_count": len(included),
                    "excluded_actor_count": sum(excluded_classes.values()),
                    "unresolved_actor_count": sum(unresolved_classes.values()),
                    "included_class_histogram": _top_counts(included_classes),
                    "matched_component_histogram": _top_counts(component_matches),
                    "excluded_class_histogram": _top_counts(excluded_classes),
                    "exclusion_reason_histogram": _top_counts(exclusion_reasons),
                    "excluded_context_asset_histogram": _top_counts(excluded_assets),
                    "unresolved_class_histogram": _top_counts(unresolved_classes),
                    "unresolved_reason_histogram": _top_counts(unresolved_reasons),
                    "histogram_limit": 20,
                    "histograms_truncated": any(len(values) > 20 for values in (
                        included_classes,
                        component_matches,
                        excluded_classes,
                        exclusion_reasons,
                        unresolved_classes,
                        unresolved_reasons,
                        excluded_assets,
                    )),
                    "largest_bounds_contributors": largest_bounds[:20],
                    "largest_bounds_contributor_limit": 20,
                    "largest_bounds_contributors_truncated": len(largest_bounds) > 20,
                    "included_actor_path_set_sha256": hashlib.sha256(
                        json.dumps(included_paths, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    ).hexdigest(),
                    "limitations": [
                        "Only observed renderable/physical component or actor classes enter this scope.",
                        "Known sky/background mesh assets are separated as renderable environment context using observed asset metadata.",
                        "Large observed landscapes remain large; no percentile or size-based clipping is applied.",
                        "Actors with failed or truncated component scans remain unresolved rather than inferred as content.",
                    ],
                    "_included_actors": included,
                }}

            def _authored_room_candidate(actor):
                tags = _actor_tags(actor)
                if _room_bounds_tag not in [str(tag).strip().lower() for tag in tags]:
                    return None
                return {{
                    "label": _actor_label(actor),
                    "class_name": _class_name(actor),
                    "path": _object_path(actor),
                    "tags": tags,
                    "bounds": _actor_bounds(actor),
                    "evidence": "observed_authored_actor_tag_and_bounds",
                }}

            class_histogram, tag_histogram = _histograms(filtered_actors)
            matched_bounds = _aggregate_bounds(filtered_actors)
            physical_content = _classified_content_scope(filtered_actors)
            selected_filtered = [actor for actor in selected_actors if _actor_matches_filters(actor)]
            selected_physical_content = _classified_content_scope(selected_filtered)
            explicit_local_actors = (
                [
                    actor for actor in physical_content["_included_actors"]
                    if _actor_matches_local_query(actor, local_actor_query)
                ]
                if local_actor_query
                else []
            )
            explicit_local_query = _classified_content_scope(explicit_local_actors)
            explicit_local_query["query"] = local_actor_query
            explicit_local_query["query_authority"] = (
                "explicit_read_only_request" if local_actor_query else "not_requested"
            )
            authored_room_candidates_all = [
                candidate for candidate in (_authored_room_candidate(actor) for actor in filtered_actors)
                if candidate is not None
            ]
            authored_room_paths = sorted(candidate["path"] for candidate in authored_room_candidates_all)
            authored_room_candidates = authored_room_candidates_all[:20]

            selected_bounds = selected_physical_content["bounds"]
            single_room_bounds = (
                authored_room_candidates_all[0]["bounds"]
                if len(authored_room_candidates_all) == 1
                else None
            )
            if selected_physical_content["included_actor_count"] > 0 and selected_bounds.get("available"):
                local_bounds_resolution = {{
                    "status": "resolved_from_selected_physical_content",
                    "source_scope": "bounds_scopes.selected_physical_content",
                    "evidence": "observed_native_selection_and_physical_content",
                    "bounds": selected_bounds,
                    "reason": "The current editor selection explicitly identifies one local content scope.",
                    "mutation_authority": False,
                }}
            elif local_actor_query:
                explicit_bounds = explicit_local_query["bounds"]
                if explicit_local_query["included_actor_count"] > 0 and explicit_bounds.get("available"):
                    local_bounds_resolution = {{
                        "status": "resolved_from_explicit_local_query",
                        "source_scope": "bounds_scopes.explicit_local_query",
                        "evidence": "observed_native_physical_content_matching_explicit_query",
                        "bounds": explicit_bounds,
                        "query": local_actor_query,
                        "matched_actor_count": explicit_local_query["included_actor_count"],
                        "reason": "The caller explicitly requested this bounded physical-content actor set.",
                        "mutation_authority": False,
                    }}
                else:
                    local_bounds_resolution = {{
                        "status": "needs_explicit_local_scope",
                        "source_scope": "bounds_scopes.explicit_local_query",
                        "evidence": "ambiguity_refusal",
                        "bounds": None,
                        "query": local_actor_query,
                        "matched_actor_count": 0,
                        "reason": "The explicit local actor query matched no observed physical-content actors.",
                        "ambiguity_reasons": ["explicit_local_query_no_physical_matches"],
                        "candidate_room_count": len(authored_room_candidates_all),
                        "mutation_authority": False,
                    }}
            elif (
                len(authored_room_candidates_all) == 1
                and isinstance(single_room_bounds, dict)
                and "min" in single_room_bounds
                and "max" in single_room_bounds
            ):
                local_bounds_resolution = {{
                    "status": "resolved_from_single_authored_room",
                    "source_scope": "bounds_scopes.authored_room_candidates.items[0]",
                    "evidence": "observed_authored_actor_tag_and_bounds",
                    "bounds": single_room_bounds,
                    "reason": "Exactly one actor explicitly carries the authored room-bounds tag.",
                    "mutation_authority": False,
                }}
            else:
                ambiguity_reasons = []
                if selected_physical_content["included_actor_count"] == 0:
                    ambiguity_reasons.append("no_selected_physical_content")
                if len(authored_room_candidates_all) == 0:
                    ambiguity_reasons.append("no_authored_room_bounds")
                elif len(authored_room_candidates_all) > 1:
                    ambiguity_reasons.append("multiple_authored_room_bounds")
                local_bounds_resolution = {{
                    "status": "needs_explicit_local_scope",
                    "source_scope": None,
                    "evidence": "ambiguity_refusal",
                    "bounds": None,
                    "reason": "Local composition bounds require an explicit physical-content selection or exactly one authored room-bounds actor.",
                    "ambiguity_reasons": ambiguity_reasons,
                    "candidate_room_count": len(authored_room_candidates_all),
                    "mutation_authority": False,
                }}

            del physical_content["_included_actors"]
            del selected_physical_content["_included_actors"]
            del explicit_local_query["_included_actors"]
            _result["schema"] = {SCENE_OVERVIEW_SCHEMA!r}
            _result["actor_count"] = len(all_actors)
            _result["matched_actor_count"] = len(filtered_actors)
            _result["filters"] = {{
                "include_hidden": include_hidden,
                "class_filter": class_filter,
                "tag_filter": tag_filter,
            }}
            _result["class_histogram"] = class_histogram
            _result["tag_histogram"] = tag_histogram
            _result["world_bounds"] = matched_bounds
            _result["bounds_scopes"] = {{
                "coordinate_system": {{
                    "units": "centimeters",
                    "handedness": "left-handed",
                    "axes": {{"x": "forward", "y": "right", "z": "up"}},
                    "provenance": "unreal_adapter_contract",
                }},
                "matched": {{
                    "kind": "matched_actor_aggregate",
                    "evidence": "observed_native_actor_bounds",
                    "bounds": matched_bounds,
                    "compatibility_alias": "world_bounds",
                }},
                "physical_content": physical_content,
                "selected_physical_content": selected_physical_content,
                "explicit_local_query": explicit_local_query,
                "authored_room_candidates": {{
                    "kind": "explicit_authored_room_bounds",
                    "evidence": "observed_authored_actor_tag_and_bounds",
                    "tag": {ROOM_BOUNDS_TAG!r},
                    "total_count": len(authored_room_candidates_all),
                    "items": authored_room_candidates,
                    "limit": 20,
                    "truncated": len(authored_room_candidates_all) > 20,
                    "path_set_sha256": hashlib.sha256(
                        json.dumps(authored_room_paths, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    ).hexdigest(),
                }},
            }}
            _result["local_bounds_resolution"] = local_bounds_resolution
            _result["selected_actor_count"] = len(selected_actors)
            _result["selected_actors"] = [_actor_data(actor, include_bounds=True) for actor in selected_actors[:20]]
            _result["actor_samples"] = (
                [_actor_data(actor, include_bounds=True) for actor in filtered_actors[:limit]]
                if {bool(include_actor_samples)!r}
                else []
            )
            _result["truncated"] = len(filtered_actors) > limit
            """
        )
    )


def _room_analysis_code(
    *,
    room_type: str,
    actor_query: str,
    class_filter: str,
    tag_filter: str,
    include_hidden: bool,
    prefer_selected: bool,
    clearance_padding: float,
    min_walkway_width: float,
    limit: int,
) -> str:
    return (
        _common_scene_code(
            include_hidden=include_hidden,
            class_filter=class_filter,
            tag_filter=tag_filter,
            limit=limit,
            include_components=False,
        )
        + textwrap.dedent(
            f"""\

            room_type = {room_type!r}
            actor_query = {str(actor_query or '').strip().lower()!r}
            prefer_selected = {bool(prefer_selected)!r}
            clearance_padding = max(0.0, float({float(clearance_padding)!r}))
            min_walkway_width = max(0.0, float({float(min_walkway_width)!r}))

            def _bounds_values(bounds):
                if not isinstance(bounds, dict) or "min" not in bounds or "max" not in bounds:
                    return None
                min_v = bounds["min"]
                max_v = bounds["max"]
                return {{
                    "min": [float(min_v["x"]), float(min_v["y"]), float(min_v["z"])],
                    "max": [float(max_v["x"]), float(max_v["y"]), float(max_v["z"])],
                    "size": [
                        float(max_v["x"]) - float(min_v["x"]),
                        float(max_v["y"]) - float(min_v["y"]),
                        float(max_v["z"]) - float(min_v["z"]),
                    ],
                    "center": [
                        (float(max_v["x"]) + float(min_v["x"])) / 2.0,
                        (float(max_v["y"]) + float(min_v["y"])) / 2.0,
                        (float(max_v["z"]) + float(min_v["z"])) / 2.0,
                    ],
                }}

            def _round_list(values):
                return [round(float(value), 3) for value in values]

            def _room_zones_live(room_type_value, origin, dimensions):
                width, depth, height = [float(component) for component in dimensions]
                ox, oy, oz = [float(component) for component in origin]
                zone_names = {{
                    "apartment": ["kitchen", "living", "bedroom", "entry", "hallway"],
                    "studio": ["kitchen", "living", "bedroom", "entry", "hallway"],
                    "kitchen": ["kitchen"],
                    "living_room": ["living"],
                    "bedroom": ["bedroom"],
                    "bathroom": ["bathroom"],
                    "hallway": ["hallway"],
                    "utility": ["utility"],
                    "generic_room": ["living"],
                }}.get(room_type_value, ["living"])
                specs = {{
                    "kitchen": {{"center": [ox - width * 0.22, oy - depth * 0.32, oz], "size": [width * 0.48, depth * 0.28, height], "wall": "negative_y"}},
                    "living": {{"center": [ox + width * 0.08, oy + depth * 0.08, oz], "size": [width * 0.58, depth * 0.48, height], "wall": "open_center"}},
                    "bedroom": {{"center": [ox + width * 0.28, oy + depth * 0.30, oz], "size": [width * 0.36, depth * 0.34, height], "wall": "positive_y"}},
                    "sleeping": {{"center": [ox + width * 0.28, oy + depth * 0.30, oz], "size": [width * 0.36, depth * 0.34, height], "wall": "positive_y"}},
                    "entry": {{"center": [ox - width * 0.36, oy + depth * 0.30, oz], "size": [width * 0.20, depth * 0.24, height], "wall": "positive_y"}},
                    "hallway": {{"center": [ox - width * 0.08, oy + depth * 0.26, oz], "size": [width * 0.38, depth * 0.18, height], "wall": "positive_y"}},
                    "bathroom": {{"center": [ox, oy, oz], "size": [width * 0.75, depth * 0.75, height], "wall": "negative_y"}},
                    "utility": {{"center": [ox - width * 0.30, oy + depth * 0.18, oz], "size": [width * 0.30, depth * 0.30, height], "wall": "positive_x"}},
                }}
                zones = []
                for name in zone_names:
                    if name not in specs:
                        continue
                    spec = dict(specs[name])
                    spec["name"] = name
                    spec["center"] = _round_list(spec["center"])
                    spec["size"] = _round_list(spec["size"])
                    zones.append(spec)
                return zones

            _room_bounds_tag = {ROOM_BOUNDS_TAG.lower()!r}
            _room_id_prefix = {ROOM_ID_TAG_PREFIX.lower()!r}
            _room_type_prefix = {ROOM_TYPE_TAG_PREFIX.lower()!r}
            _zone_prefix = {ZONE_TAG_PREFIX.lower()!r}
            _opening_prefix = {OPENING_TAG_PREFIX.lower()!r}
            _clearance_prefix = {CLEARANCE_TAG_PREFIX.lower()!r}
            _path_required_tag = {PATH_REQUIRED_TAG.lower()!r}
            _surface_prefix = {SURFACE_TAG_PREFIX.lower()!r}

            def _actor_tag_values(actor):
                values = []
                for tag in _actor_tags(actor):
                    text = str(tag).strip()
                    if text:
                        values.append(text)
                return values

            def _actor_tag_lowers(actor):
                return [tag.lower() for tag in _actor_tag_values(actor)]

            def _tag_suffix(actor, prefix_lower):
                for tag in _actor_tag_values(actor):
                    lower = tag.lower()
                    if lower.startswith(prefix_lower):
                        return tag[len(prefix_lower):].strip()
                return ""

            def _has_tag(actor, tag_lower):
                return tag_lower in _actor_tag_lowers(actor)

            def _has_prefix_tag(actor, prefix_lower):
                return any(tag.startswith(prefix_lower) for tag in _actor_tag_lowers(actor))

            def _designation_roles(actor):
                roles = []
                if _has_tag(actor, _room_bounds_tag):
                    roles.append("room_bounds")
                if _has_prefix_tag(actor, _zone_prefix):
                    roles.append("zone")
                if _has_prefix_tag(actor, _opening_prefix):
                    roles.append("opening")
                if _has_prefix_tag(actor, _clearance_prefix):
                    roles.append("clearance")
                if _has_tag(actor, _path_required_tag):
                    roles.append("required_path")
                if _has_prefix_tag(actor, _surface_prefix):
                    roles.append("surface")
                return roles

            def _canonical_zone_from_label(value):
                text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
                aliases = {{
                    "living_room": "living",
                    "lounge": "living",
                    "sitting": "living",
                    "washitsu": "living",
                    "tatami_room": "living",
                    "ldk": "living",
                    "dining": "living",
                    "bed": "bedroom",
                    "sleep": "bedroom",
                    "sleeping": "bedroom",
                    "kitchenette": "kitchen",
                    "galley": "kitchen",
                    "entryway": "entry",
                    "foyer": "entry",
                    "genkan": "entry",
                    "vestibule": "entry",
                    "corridor": "hallway",
                    "hall": "hallway",
                    "laundry": "utility",
                    "laundry_room": "utility",
                    "mudroom": "utility",
                    "unit_bath": "bathroom",
                    "bath_unit": "bathroom",
                    "toilet": "bathroom",
                }}
                text = aliases.get(text, text)
                allowed = ("kitchen", "living", "bedroom", "entry", "hallway", "bathroom", "utility")
                return text if text in allowed else text[:64]

            def _wall_from_bounds(values, room_values):
                if values is None or room_values is None:
                    return "open_center"
                distances = [
                    ("negative_x", abs(values["center"][0] - room_values["min"][0])),
                    ("positive_x", abs(values["center"][0] - room_values["max"][0])),
                    ("negative_y", abs(values["center"][1] - room_values["min"][1])),
                    ("positive_y", abs(values["center"][1] - room_values["max"][1])),
                ]
                distances.sort(key=lambda item: item[1])
                return distances[0][0] if distances and distances[0][1] <= 90.0 else "open_center"

            def _marker_record(actor, *, kind, room_values=None):
                data = _actor_data(actor, include_bounds=True)
                values = _bounds_values(data.get("bounds", {{}}))
                record = dict(
                    kind=kind,
                    label=data.get("label", ""),
                    class_name=data.get("class", ""),
                    path=data.get("path", ""),
                    tags=data.get("tags", []),
                    bounds=data.get("bounds", {{}}),
                    designation_roles=_designation_roles(actor),
                    room_id=_tag_suffix(actor, _room_id_prefix),
                    room_type=_tag_suffix(actor, _room_type_prefix),
                    source="authored_actor_tag",
                )
                if values is not None:
                    record["center"] = _round_list(values["center"])
                    record["size"] = _round_list(values["size"])
                    record["wall"] = _wall_from_bounds(values, room_values) if room_values is not None else "open_center"
                return record

            def _authored_room_bounds_actors():
                candidates = [
                    actor for actor in filtered_actors
                    if _has_tag(actor, _room_bounds_tag) and _text_matches(actor, actor_query)
                ]
                if prefer_selected:
                    selected_candidates = [
                        actor for actor in selected_actors
                        if _actor_matches_filters(actor) and _has_tag(actor, _room_bounds_tag) and _text_matches(actor, actor_query)
                    ]
                    if selected_candidates:
                        return selected_candidates[:limit], "selected_authored_room_bounds"
                return candidates[:limit], "authored_room_bounds"

            def _authored_zone_records(room_values):
                records = []
                for actor in filtered_actors:
                    if not _has_prefix_tag(actor, _zone_prefix):
                        continue
                    if not _bounds_intersects_room(_actor_bounds(actor), room_bounds, padding=clearance_padding):
                        continue
                    raw_label = _tag_suffix(actor, _zone_prefix) or _actor_label(actor)
                    canonical = _canonical_zone_from_label(raw_label)
                    marker = _marker_record(actor, kind="zone", room_values=room_values)
                    if not marker.get("center") or not marker.get("size"):
                        continue
                    marker.update(dict(
                        name=canonical,
                        authored_label=raw_label[:64],
                        wall=marker.get("wall") or "open_center",
                    ))
                    records.append(marker)
                return records[:32]

            def _authored_marker_records(kind, prefix_lower="", exact_lower=""):
                records = []
                for actor in filtered_actors:
                    matched = False
                    if prefix_lower and _has_prefix_tag(actor, prefix_lower):
                        matched = True
                    if exact_lower and _has_tag(actor, exact_lower):
                        matched = True
                    if not matched:
                        continue
                    if not _bounds_intersects_room(_actor_bounds(actor), room_bounds, padding=clearance_padding):
                        continue
                    records.append(_marker_record(actor, kind=kind, room_values=room_values))
                return records[:32]

            def _bounds_intersects_room(bounds, room_bounds, padding=0.0):
                values = _bounds_values(bounds)
                room_values = _bounds_values(room_bounds)
                if values is None or room_values is None:
                    return False
                return not (
                    values["max"][0] < room_values["min"][0] - padding
                    or values["min"][0] > room_values["max"][0] + padding
                    or values["max"][1] < room_values["min"][1] - padding
                    or values["min"][1] > room_values["max"][1] + padding
                    or values["max"][2] < room_values["min"][2] - padding
                    or values["min"][2] > room_values["max"][2] + padding
                )

            def _actor_text(actor):
                return " ".join([
                    _actor_label(actor),
                    str(actor.get_name()) if hasattr(actor, "get_name") else "",
                    _class_name(actor),
                    _object_path(actor),
                    " ".join(_actor_tags(actor)),
                ]).lower()

            def _has_any(text, keywords):
                return any(keyword in text for keyword in keywords)

            def _classify_surface(actor, room_values):
                data = _actor_data(actor, include_bounds=True)
                bounds = data.get("bounds", {{}})
                values = _bounds_values(bounds)
                if values is None:
                    return None
                text = _actor_text(actor)
                size_x, size_y, size_z = values["size"]
                center_x, center_y, center_z = values["center"]
                floor_z = room_values["min"][2]
                height = max(1.0, room_values["size"][2])
                top_z = values["max"][2]
                horizontal_area = abs(size_x * size_y)
                designation_roles = _designation_roles(actor)
                surface_marker = _tag_suffix(actor, _surface_prefix).lower()
                roles = []
                if any(role in designation_roles for role in ("room_bounds", "zone", "clearance", "required_path")):
                    roles.append("designation_marker")
                if "opening" in designation_roles:
                    roles.append("opening")
                if surface_marker in ("floor", "ground"):
                    roles.append("floor")
                if surface_marker in ("wall", "partition"):
                    roles.append("wall")
                if surface_marker in ("ceiling", "roof"):
                    roles.append("ceiling")
                if surface_marker in ("counter", "countertop", "table", "desk", "shelf", "island", "cabinet", "vanity"):
                    roles.append("horizontal_support")
                if _has_any(text, ("floor", "ground", "slab")) or (horizontal_area >= 20000.0 and size_z <= 45.0 and center_z <= floor_z + 80.0):
                    roles.append("floor")
                if _has_any(text, ("ceiling", "roof")) or (horizontal_area >= 20000.0 and size_z <= 45.0 and center_z >= floor_z + height * 0.65):
                    roles.append("ceiling")
                if _has_any(text, ("wall", "partition")) or ((size_x <= 45.0 or size_y <= 45.0) and size_z >= 120.0 and max(size_x, size_y) >= 120.0):
                    roles.append("wall")
                if _has_any(text, ("door", "window", "opening", "archway", "portal")):
                    roles.append("opening")
                if _has_any(text, ("counter", "countertop", "table", "desk", "shelf", "island", "cabinet", "vanity")) or (
                    horizontal_area >= 1200.0 and floor_z + 55.0 <= top_z <= floor_z + 135.0 and size_z <= 140.0
                ):
                    roles.append("horizontal_support")
                if _has_any(text, ("sofa", "chair", "stool", "bed", "fridge", "refrigerator", "stove", "oven", "washer", "dryer", "dresser", "bookshelf", "prop", "clutter")):
                    roles.append("obstacle")
                if not roles:
                    roles.append("designation_marker" if designation_roles else "obstacle")
                roles = list(dict.fromkeys(roles))
                top_center = [center_x, center_y, top_z]
                side_clearance = min(
                    abs(values["min"][0] - room_values["min"][0]),
                    abs(room_values["max"][0] - values["max"][0]),
                    abs(values["min"][1] - room_values["min"][1]),
                    abs(room_values["max"][1] - values["max"][1]),
                )
                return {{
                    "label": data.get("label", ""),
                    "class": data.get("class", ""),
                    "path": data.get("path", ""),
                    "roles": roles,
                    "designation_roles": designation_roles,
                    "bounds": bounds,
                    "top_center": _round_list(top_center),
                    "approx_size_cm": _round_list(values["size"]),
                    "side_clearance_to_room_edge_cm": round(float(side_clearance), 3),
                    "placement_roles": [
                        role for role in (
                            "supports_floor_placement" if "floor" in roles else "",
                            "supports_wall_mounting" if "wall" in roles else "",
                            "supports_countertop_clutter" if "horizontal_support" in roles else "",
                            "avoid_as_blocking_obstacle" if "obstacle" in roles and "floor" not in roles and "wall" not in roles and "ceiling" not in roles else "",
                        )
                        if role
                    ],
                }}

            def _central_clearance_risk(surface, room_values):
                roles = surface.get("roles", [])
                if "obstacle" not in roles or "floor" in roles or "wall" in roles or "ceiling" in roles:
                    return None
                values = _bounds_values(surface.get("bounds", {{}}))
                if values is None:
                    return None
                room_center = room_values["center"]
                room_size = room_values["size"]
                center = values["center"]
                size = values["size"]
                in_central_band = (
                    abs(center[0] - room_center[0]) <= max(min_walkway_width, room_size[0] * 0.18)
                    and abs(center[1] - room_center[1]) <= max(min_walkway_width, room_size[1] * 0.18)
                )
                oversized = size[0] >= room_size[0] * 0.45 or size[1] >= room_size[1] * 0.45
                if in_central_band and max(size[0], size[1]) >= min_walkway_width:
                    return {{
                        "actor": surface.get("label", ""),
                        "risk": "central_circulation_overlap",
                        "reason": "Obstacle footprint overlaps the inferred central walkway band.",
                        "approx_size_cm": surface.get("approx_size_cm", []),
                    }}
                if oversized:
                    return {{
                        "actor": surface.get("label", ""),
                        "risk": "oversized_obstacle",
                        "reason": "Obstacle consumes a large share of inferred room bounds.",
                        "approx_size_cm": surface.get("approx_size_cm", []),
                    }}
                return None

            def _select_room_seed_actors():
                matched = [actor for actor in filtered_actors if _text_matches(actor, actor_query)]
                if not matched:
                    matched = list(filtered_actors)
                selected_matching = [
                    actor for actor in selected_actors
                    if _actor_matches_filters(actor) and _text_matches(actor, actor_query)
                ]
                if prefer_selected and selected_matching:
                    return selected_matching[:limit], "selected_actors"
                return matched[:limit], "filtered_actors"

            authored_bounds_actors, authored_selection_strategy = _authored_room_bounds_actors()
            if authored_bounds_actors:
                seed_actors, selection_strategy = authored_bounds_actors, authored_selection_strategy
                room_bounds_source = "authored_room_bounds"
            else:
                seed_actors, selection_strategy = _select_room_seed_actors()
                room_bounds_source = "aggregate_actor_bounds"
            room_bounds = _aggregate_bounds(seed_actors)
            _result["schema"] = {ROOM_ANALYSIS_SCHEMA!r}
            _result["room_type"] = room_type
            _result["selection_strategy"] = selection_strategy
            _result["room_bounds_source"] = room_bounds_source
            _result["seed_actor_count"] = len(seed_actors)
            _result["filters"] = {{
                "actor_query": actor_query,
                "class_filter": class_filter,
                "tag_filter": tag_filter,
                "include_hidden": include_hidden,
                "prefer_selected": prefer_selected,
                "limit": limit,
            }}

            if not room_bounds.get("available"):
                _errors.append("No actors were available to infer room bounds.")
            else:
                room_values = _bounds_values(room_bounds)
                room_origin = [room_values["center"][0], room_values["center"][1], room_values["min"][2]]
                room_dimensions = [
                    max(1.0, room_values["size"][0]),
                    max(1.0, room_values["size"][1]),
                    max(1.0, room_values["size"][2]),
                ]
                analysis_actors = [
                    actor for actor in filtered_actors
                    if _bounds_intersects_room(_actor_bounds(actor), room_bounds, padding=clearance_padding)
                ][:limit]
                surfaces = []
                for actor in analysis_actors:
                    surface = _classify_surface(actor, room_values)
                    if surface is not None:
                        surfaces.append(surface)
                classified = {{
                    "floors": [surface for surface in surfaces if "floor" in surface["roles"]],
                    "walls": [surface for surface in surfaces if "wall" in surface["roles"]],
                    "ceilings": [surface for surface in surfaces if "ceiling" in surface["roles"]],
                    "openings": [surface for surface in surfaces if "opening" in surface["roles"]],
                    "horizontal_supports": [surface for surface in surfaces if "horizontal_support" in surface["roles"]],
                    "designation_markers": [surface for surface in surfaces if "designation_marker" in surface["roles"]],
                    "obstacles": [
                        surface for surface in surfaces
                        if "obstacle" in surface["roles"]
                        and "floor" not in surface["roles"]
                        and "wall" not in surface["roles"]
                        and "ceiling" not in surface["roles"]
                        and "designation_marker" not in surface["roles"]
                    ],
                }}
                clearance_risks = []
                for surface in classified["obstacles"]:
                    risk = _central_clearance_risk(surface, room_values)
                    if risk is not None:
                        clearance_risks.append(risk)

                authored_room_markers = [
                    _marker_record(actor, kind="room_bounds", room_values=room_values)
                    for actor in authored_bounds_actors
                ]
                authored_zones = _authored_zone_records(room_values)
                authored_openings = _authored_marker_records("opening", prefix_lower=_opening_prefix)
                authored_clearances = _authored_marker_records("clearance", prefix_lower=_clearance_prefix)
                authored_paths = _authored_marker_records("required_path", exact_lower=_path_required_tag)
                authored_surfaces = _authored_marker_records("surface", prefix_lower=_surface_prefix)
                authored_room_designation = {{
                    "schema": {ROOM_BOUNDS_DESIGNATION_SCHEMA!r},
                    "recognized": bool(authored_room_markers or authored_zones or authored_openings or authored_clearances or authored_paths or authored_surfaces),
                    "room_bounds_source": room_bounds_source,
                    "room_bounds": authored_room_markers,
                    "zones": authored_zones,
                    "openings": authored_openings,
                    "clearances": authored_clearances,
                    "required_paths": authored_paths,
                    "surfaces": authored_surfaces,
                    "marker_counts": {{
                        "room_bounds": len(authored_room_markers),
                        "zones": len(authored_zones),
                        "openings": len(authored_openings),
                        "clearances": len(authored_clearances),
                        "required_paths": len(authored_paths),
                        "surfaces": len(authored_surfaces),
                    }},
                    "tag_contract": {{
                        "room_bounds": {ROOM_BOUNDS_TAG!r},
                        "room_id_prefix": {ROOM_ID_TAG_PREFIX!r},
                        "room_type_prefix": {ROOM_TYPE_TAG_PREFIX!r},
                        "zone_prefix": {ZONE_TAG_PREFIX!r},
                        "opening_prefix": {OPENING_TAG_PREFIX!r},
                        "clearance_prefix": {CLEARANCE_TAG_PREFIX!r},
                        "path_required": {PATH_REQUIRED_TAG!r},
                        "surface_prefix": {SURFACE_TAG_PREFIX!r},
                    }},
                }}

                zones = authored_zones if authored_zones else _room_zones_live(room_type, room_origin, room_dimensions)
                zone_probe_points = [
                    [zone["center"][0], zone["center"][1], room_origin[2] + min(200.0, max(120.0, room_dimensions[2] * 0.5))]
                    for zone in zones
                ]
                counter_probe_points = [
                    [surface["top_center"][0], surface["top_center"][1], surface["top_center"][2] + 60.0]
                    for surface in classified["horizontal_supports"][:8]
                ]
                probe_points = zone_probe_points + counter_probe_points
                if not probe_points:
                    probe_points = [[room_origin[0], room_origin[1], room_origin[2] + 200.0]]

                _result["room_bounds"] = room_bounds
                _result["authored_room_designation"] = authored_room_designation
                _result["room_model"] = {{
                    "type": room_type,
                    "origin": _round_list(room_origin),
                    "dimensions_cm": _round_list(room_dimensions),
                    "floor_z": round(float(room_values["min"][2]), 3),
                    "ceiling_z": round(float(room_values["max"][2]), 3),
                    "center": _round_list(room_values["center"]),
                    "bounds_source": room_bounds_source,
                    "authored_room_id": authored_room_markers[0].get("room_id", "") if authored_room_markers else "",
                    "authored_room_type": authored_room_markers[0].get("room_type", "") if authored_room_markers else "",
                }}
                _result["zones"] = zones
                _result["classified_surfaces"] = classified
                _result["surface_counts"] = {{key: len(value) for key, value in classified.items()}}
                _result["clearance_summary"] = {{
                    "method": "bounds_preflight",
                    "recommended_min_walkway_cm": min_walkway_width,
                    "clearance_padding_cm": clearance_padding,
                    "analysis_actor_count": len(analysis_actors),
                    "obstacle_count": len(classified["obstacles"]),
                    "risk_count": len(clearance_risks),
                    "risks": clearance_risks,
                    "notes": [
                        "Bounds analysis is a planning preflight; run spatial_surface_probe and spatial_validate_placement before accepting final placement.",
                        "Wall and counter support roles are inferred from actor names/tags/classes and bounding-box proportions.",
                    ],
                }}
                _result["planner_handoff"] = {{
                    "spatial_plan_interior_composition": {{
                        "room_type": room_type,
                        "room_dimensions": _round_list(room_dimensions),
                        "room_origin": _round_list(room_origin),
                        "room_designation_json": "<THIS_SPATIAL_ANALYZE_ROOM_RESULT_JSON.authored_room_designation>",
                        "screenshot_observations": [
                            "Detected " + str(len(classified["floors"])) + " floor candidates",
                            "Detected " + str(len(classified["walls"])) + " wall candidates",
                            "Detected " + str(len(classified["horizontal_supports"])) + " counter/table/shelf support candidates",
                            "Detected " + str(len(classified["obstacles"])) + " existing obstacle/prop candidates",
                        ],
                    }},
                    "spatial_infer_functional_zones": {{
                        "room_analysis_json": "<THIS_SPATIAL_ANALYZE_ROOM_RESULT_JSON>",
                        "room_type": room_type,
                        "room_dimensions": _round_list(room_dimensions),
                        "room_origin": _round_list(room_origin),
                        "requested_zones": [zone["name"] for zone in zones],
                        "authored_zone_count": len(authored_zones),
                    }},
                    "spatial_surface_probe": {{
                        "points": [_round_list(point) for point in probe_points[:32]],
                        "trace_up": max(300.0, room_dimensions[2] + 100.0),
                        "trace_down": max(1000.0, room_dimensions[2] + 500.0),
                        "placement_offset": 0.0,
                    }},
                    "spatial_infer_placement_policy": {{
                        "policy": "interior_composition",
                        "intent": "compose interior props using inferred room bounds, zones, support surfaces, and clearance risks",
                        "base_spacing": max(150.0, min(room_dimensions[0], room_dimensions[1]) * 0.12),
                    }},
                    "spatial_validate_placement": {{
                        "surface_tolerance": 15.0,
                        "clearance_padding": clearance_padding,
                        "include_evidence_handoff": True,
                    }},
                }}
                _result["recommended_workflow"] = [
                    {{"step": "review_room_bounds_designation", "reason": "Confirm Ghost.RoomBounds, Ghost.Zone.*, Ghost.Opening.*, Ghost.Path.Required, and Ghost.Surface.* markers when present."}},
                    {{"step": "review_room_model", "reason": "Confirm inferred dimensions and zone split before generation."}},
                    {{"step": "infer_functional_zones", "tool": "spatial_infer_functional_zones", "arguments": _result["planner_handoff"]["spatial_infer_functional_zones"]}},
                    {{"step": "probe_surfaces", "tool": "spatial_surface_probe", "arguments": _result["planner_handoff"]["spatial_surface_probe"]}},
                    {{"step": "plan_composition", "tool": "spatial_plan_interior_composition", "arguments": _result["planner_handoff"]["spatial_plan_interior_composition"]}},
                    {{"step": "place_dry_run", "tool": "spatial_add_asset_to_scene", "reason": "Keep dry_run=true until the composition is reviewed."}},
                    {{"step": "validate_and_capture", "tools": ["spatial_validate_placement", "spatial_select_actors", "focus_viewport", "viewport_capture_screenshot"]}},
                ]
                _result["legal_review"] = {{
                    "requires_review": False,
                    "notes": [
                        "This is a clean-room Ghost room analysis over Unreal Python actor bounds.",
                        "Any future close reuse of Epic SceneTools room/surface internals should receive legal review.",
                    ],
                }}
            """
        )
    )


def _query_actors_code(
    *,
    query: str,
    class_filter: str,
    tag_filter: str,
    center: Optional[List[float]],
    radius: float,
    box_min: Optional[List[float]],
    box_max: Optional[List[float]],
    include_hidden: bool,
    include_components: bool,
    limit: int,
) -> str:
    return (
        _common_scene_code(
            include_hidden=include_hidden,
            class_filter=class_filter,
            tag_filter=tag_filter,
            limit=limit,
            include_components=include_components,
        )
        + textwrap.dedent(
            f"""\

            query_text = {str(query or '').strip().lower()!r}
            center = _literal_vec({center!r})
            radius = float({float(radius)!r})
            box_min = _literal_vec({box_min!r})
            box_max = _literal_vec({box_max!r})

            def _inside_box(actor):
                if box_min is None and box_max is None:
                    return True
                try:
                    loc = _vec_tuple(actor.get_actor_location())
                except Exception:
                    return False
                if box_min is not None:
                    if loc[0] < box_min[0] or loc[1] < box_min[1] or loc[2] < box_min[2]:
                        return False
                if box_max is not None:
                    if loc[0] > box_max[0] or loc[1] > box_max[1] or loc[2] > box_max[2]:
                        return False
                return True

            matches = []
            for actor in filtered_actors:
                if not _text_matches(actor, query_text):
                    continue
                if not _inside_box(actor):
                    continue
                try:
                    loc = _vec_tuple(actor.get_actor_location())
                except Exception:
                    loc = None
                if center is not None and radius > 0.0:
                    distance = _distance(loc, center)
                    if distance is None or distance > radius:
                        continue
                matches.append(_actor_data(actor, include_bounds=True, center=center))

            if center is not None:
                matches.sort(key=lambda item: (item.get("distance") is None, item.get("distance") or 0.0, item.get("label", "")))
            else:
                matches.sort(key=lambda item: item.get("label", ""))

            _result["schema"] = {SPATIAL_QUERY_SCHEMA!r}
            _result["matched_actor_count"] = len(matches)
            _result["actors"] = matches[:limit]
            _result["truncated"] = len(matches) > limit
            _result["filters"] = {{
                "query": query_text,
                "class_filter": class_filter,
                "tag_filter": tag_filter,
                "include_hidden": include_hidden,
                "center": center,
                "radius": radius,
                "box_min": box_min,
                "box_max": box_max,
            }}
            """
        )
    )


def _describe_actor_code(
    *,
    actor: str,
    include_components: bool,
    include_bounds: bool,
    nearby_radius: float,
    nearby_limit: int,
) -> str:
    return (
        _common_scene_code(
            include_hidden=True,
            class_filter="",
            tag_filter="",
            limit=nearby_limit,
            include_components=include_components,
        )
        + textwrap.dedent(
            f"""\

            target_query = {str(actor or '').strip()!r}
            target_actor = _find_actor(target_query)
            if target_actor is None:
                _errors.append("Actor not found: " + target_query)
            else:
                center = _actor_location_tuple(target_actor) if hasattr(target_actor, "get_actor_location") else None
                nearby = []
                for candidate in all_actors:
                    if candidate == target_actor or not _actor_matches_filters(candidate):
                        continue
                    try:
                        candidate_location = _vec_tuple(candidate.get_actor_location())
                    except Exception:
                        candidate_location = None
                    distance = _distance(candidate_location, center)
                    if distance is None:
                        continue
                    if distance <= float({float(nearby_radius)!r}):
                        nearby.append(_actor_data(candidate, include_bounds=True, center=center))
                nearby.sort(key=lambda item: (item.get("distance") is None, item.get("distance") or 0.0, item.get("label", "")))

                _result["schema"] = {ACTOR_DESCRIPTOR_SCHEMA!r}
                _result["actor"] = _actor_data(target_actor, include_bounds={bool(include_bounds)!r}, center=None)
                _result["nearby_radius"] = float({float(nearby_radius)!r})
                _result["nearby_actors"] = nearby[:max(1, int({int(nearby_limit)!r}))]
                _result["nearby_truncated"] = len(nearby) > max(1, int({int(nearby_limit)!r}))
                _result["is_selected"] = any(actor == target_actor for actor in selected_actors)
            """
        )
    )


def _proximity_map_code(
    *,
    actor: str,
    center: Optional[List[float]],
    radius: float,
    class_filter: str,
    tag_filter: str,
    include_hidden: bool,
    limit: int,
) -> str:
    return (
        _common_scene_code(
            include_hidden=include_hidden,
            class_filter=class_filter,
            tag_filter=tag_filter,
            limit=limit,
            include_components=False,
        )
        + textwrap.dedent(
            f"""\

            source_query = {str(actor or '').strip()!r}
            requested_center = _literal_vec({center!r})
            search_radius = float({float(radius)!r})
            source_actor = _find_actor(source_query) if source_query else None
            source_kind = "actor" if source_actor is not None else "point"
            source_label = _actor_label(source_actor) if source_actor is not None else ""
            source_center = None

            if source_actor is not None:
                source_center = _actor_location_tuple(source_actor)
            elif requested_center is not None:
                source_center = requested_center
            elif selected_actors:
                source_actor = selected_actors[0]
                source_kind = "selected_actor"
                source_label = _actor_label(source_actor)
                source_center = _actor_location_tuple(source_actor)
            if source_center is None:
                source_center = (0.0, 0.0, 0.0)
                _warnings.append("No usable actor, center, or selected actor location was available; using world origin.")

            neighbors = []
            for candidate in filtered_actors:
                if source_actor is not None and candidate == source_actor:
                    continue
                try:
                    candidate_location = _vec_tuple(candidate.get_actor_location())
                except Exception:
                    candidate_location = None
                distance = _distance(candidate_location, source_center)
                if distance is None:
                    continue
                if search_radius > 0.0 and distance > search_radius:
                    continue
                neighbors.append(_actor_data(candidate, include_bounds=True, center=source_center))

            neighbors.sort(key=lambda item: (item.get("distance") is None, item.get("distance") or 0.0, item.get("label", "")))
            _result["schema"] = {PROXIMITY_MAP_SCHEMA!r}
            _result["source"] = {{
                "kind": source_kind,
                "actor": source_label,
                "center": {{"x": source_center[0], "y": source_center[1], "z": source_center[2]}},
            }}
            _result["radius"] = search_radius
            _result["matched_actor_count"] = len(neighbors)
            _result["actors"] = neighbors[:limit]
            _result["truncated"] = len(neighbors) > limit
            """
        )
    )


def _view_context_code(*, include_nearby: bool, nearby_radius: float, limit: int) -> str:
    return (
        _common_scene_code(
            include_hidden=False,
            class_filter="",
            tag_filter="",
            limit=limit,
            include_components=False,
        )
        + textwrap.dedent(
            f"""\

            viewport_location = None
            viewport_rotation = None
            viewport_available = False
            level_editor_subsystem_class = getattr(unreal, "LevelEditorSubsystem", None)
            if level_editor_subsystem_class is not None:
                try:
                    level_editor_subsystem = unreal.get_editor_subsystem(level_editor_subsystem_class)
                    if hasattr(level_editor_subsystem, "get_level_viewport_camera_info"):
                        camera_info = level_editor_subsystem.get_level_viewport_camera_info()
                        if isinstance(camera_info, tuple) and len(camera_info) >= 2:
                            viewport_location = camera_info[0]
                            viewport_rotation = camera_info[1]
                            viewport_available = True
                except Exception as exc:
                    _warnings.append("Could not read LevelEditorSubsystem viewport camera info: " + str(exc))
            else:
                _warnings.append("LevelEditorSubsystem is unavailable; viewport camera context cannot be read.")

            center = _vec_tuple(viewport_location)
            if center is None and selected_actors:
                center = _actor_location_tuple(selected_actors[0])
            if center is None:
                center = (0.0, 0.0, 0.0)

            nearby = []
            if {bool(include_nearby)!r}:
                for actor in filtered_actors:
                    try:
                        actor_location = _vec_tuple(actor.get_actor_location())
                    except Exception:
                        actor_location = None
                    distance = _distance(actor_location, center)
                    if distance is None:
                        continue
                    if float({float(nearby_radius)!r}) > 0.0 and distance > float({float(nearby_radius)!r}):
                        continue
                    nearby.append(_actor_data(actor, include_bounds=True, center=center))
                nearby.sort(key=lambda item: (item.get("distance") is None, item.get("distance") or 0.0, item.get("label", "")))

            _result["schema"] = {VIEW_CONTEXT_SCHEMA!r}
            _result["viewport"] = {{
                "available": viewport_available,
                "location": _vec_dict(viewport_location),
                "rotation": _rot_dict(viewport_rotation),
            }}
            _result["selected_actor_count"] = len(selected_actors)
            _result["selected_actors"] = [_actor_data(actor, include_bounds=True) for actor in selected_actors[:limit]]
            _result["nearby_radius"] = float({float(nearby_radius)!r})
            _result["nearby_actors"] = nearby[:limit]
            _result["nearby_truncated"] = len(nearby) > limit
            """
        )
    )


def _content_selection_code(
    *,
    limit: int,
    placement_origin: List[float],
    placement_spacing: float,
    placement_layout: str,
    actor_label_prefix: str,
    tags: List[str],
    data_layer_names: List[str],
) -> str:
    return textwrap.dedent(
        f"""\
        import math
        import unreal

        limit = max(1, int({int(limit)!r}))
        placement_origin = {placement_origin!r}
        placement_spacing = max(0.0, float({float(placement_spacing)!r}))
        placement_layout = {placement_layout!r}
        actor_label_prefix = {str(actor_label_prefix or '').strip()!r}
        tag_values = {tags!r}
        data_layer_names = {data_layer_names!r}

        _result["schema"] = {CONTENT_SELECTION_SCHEMA!r}
        _result["limit"] = limit
        _result["placement_origin"] = placement_origin
        _result["placement_spacing"] = placement_spacing
        _result["placement_layout"] = placement_layout
        _result["tags"] = tag_values
        _result["data_layer_names"] = data_layer_names

        def _safe_text(value):
            try:
                return str(value)
            except Exception:
                return ""

        def _object_path(obj):
            if obj is None:
                return ""
            try:
                return obj.get_path_name()
            except Exception:
                return _safe_text(obj)

        def _class_name(obj):
            if obj is None:
                return ""
            try:
                return obj.get_class().get_name()
            except Exception:
                return obj.__class__.__name__

        def _object_name(obj):
            if obj is None:
                return ""
            try:
                return _safe_text(obj.get_name())
            except Exception:
                path = _object_path(obj)
                if "." in path:
                    return path.rsplit(".", 1)[-1]
                return path.rsplit("/", 1)[-1] if path else _safe_text(obj)

        def _package_name(obj):
            try:
                package = obj.get_outermost()
                if package is not None and hasattr(package, "get_name"):
                    return _safe_text(package.get_name())
            except Exception:
                pass
            path = _object_path(obj)
            if "." in path:
                return path.split(".", 1)[0]
            return path.rsplit("/", 1)[0] if "/" in path else ""

        def _asset_path(obj):
            path = _object_path(obj)
            if path.startswith("/") and "." in path:
                return path
            package_name = _package_name(obj)
            asset_name = _object_name(obj)
            if package_name and asset_name:
                return package_name + "." + asset_name
            return path

        def _data_value(asset_data, field_name):
            try:
                value = getattr(asset_data, field_name)
                if value:
                    return _safe_text(value)
            except Exception:
                pass
            try:
                value = asset_data.get_editor_property(field_name)
                if value:
                    return _safe_text(value)
            except Exception:
                pass
            return ""

        def _asset_data_path(asset_data):
            for field_name in ("object_path", "soft_object_path"):
                value = _data_value(asset_data, field_name)
                if value:
                    return value
            package_name = _data_value(asset_data, "package_name")
            asset_name = _data_value(asset_data, "asset_name")
            if package_name and asset_name:
                return package_name + "." + asset_name
            return package_name

        def _asset_data_descriptor(asset_data):
            asset_path = _asset_data_path(asset_data)
            asset_name = _data_value(asset_data, "asset_name")
            if not asset_name and "." in asset_path:
                asset_name = asset_path.rsplit(".", 1)[-1]
            class_name = _data_value(asset_data, "asset_class_path") or _data_value(asset_data, "asset_class")
            return _asset_descriptor_common(
                name=asset_name,
                path=asset_path,
                class_name=class_name,
                package_name=_data_value(asset_data, "package_name"),
                source="EditorUtilityLibrary.get_selected_asset_data",
            )

        def _placeable_hint(class_name, asset_path):
            text = (class_name + " " + asset_path).lower()
            checks = (
                ("Blueprint", "blueprint" in text),
                ("StaticMesh", "staticmesh" in text),
                ("SkeletalMesh", "skeletalmesh" in text),
                ("NiagaraSystem", "niagarasystem" in text),
                ("ParticleSystem", "particlesystem" in text),
            )
            for label, matched in checks:
                if matched:
                    return True, "Likely placeable through public editor spawn helpers: " + label
            return False, "No placeable asset hint detected; review before passing to spatial_add_asset_to_scene."

        def _asset_descriptor_common(name, path, class_name, package_name, source):
            placeable, reason = _placeable_hint(class_name, path)
            return {{
                "name": name or (path.rsplit(".", 1)[-1] if "." in path else path.rsplit("/", 1)[-1]),
                "path": path,
                "class": class_name,
                "package": package_name,
                "source": source,
                "placeable_hint": placeable,
                "placeable_reason": reason,
            }}

        def _asset_descriptor(asset):
            asset_path = _asset_path(asset)
            return _asset_descriptor_common(
                name=_object_name(asset),
                path=asset_path,
                class_name=_class_name(asset),
                package_name=_package_name(asset),
                source="EditorUtilityLibrary.get_selected_assets",
            )

        def _editor_utility_library():
            library = getattr(unreal, "EditorUtilityLibrary", None)
            if library is None:
                _warnings.append("EditorUtilityLibrary is unavailable; Content Browser selection cannot be read.")
            return library

        def _selected_assets():
            library = _editor_utility_library()
            if library is None:
                return [], []
            assets = []
            asset_data = []
            get_selected_assets = getattr(library, "get_selected_assets", None)
            if callable(get_selected_assets):
                try:
                    assets = list(get_selected_assets() or [])
                except Exception as exc:
                    _warnings.append("EditorUtilityLibrary.get_selected_assets failed: " + str(exc))
            get_selected_asset_data = getattr(library, "get_selected_asset_data", None)
            if callable(get_selected_asset_data):
                try:
                    asset_data = list(get_selected_asset_data() or [])
                except Exception as exc:
                    _warnings.append("EditorUtilityLibrary.get_selected_asset_data failed: " + str(exc))
            if not assets and not asset_data:
                _warnings.append("No selected Content Browser assets were reported by EditorUtilityLibrary.")
            return assets, asset_data

        def _layout_location(index):
            origin_x = float(placement_origin[0])
            origin_y = float(placement_origin[1])
            origin_z = float(placement_origin[2])
            if placement_layout == "grid":
                columns = max(1, int(math.ceil(math.sqrt(max(1, min(limit, selected_asset_count))))))
                row = index // columns
                column = index % columns
                return [origin_x + column * placement_spacing, origin_y + row * placement_spacing, origin_z]
            if placement_layout == "stack":
                return [origin_x, origin_y, origin_z + index * placement_spacing]
            return [origin_x + index * placement_spacing, origin_y, origin_z]

        def _actor_label(asset_descriptor, index):
            base_name = asset_descriptor.get("name") or ("SelectedAsset_" + str(index + 1))
            if actor_label_prefix:
                return actor_label_prefix + "_" + base_name
            return base_name

        selected_asset_objects, selected_asset_data = _selected_assets()
        object_descriptors = [_asset_descriptor(asset) for asset in selected_asset_objects]
        data_descriptors = []
        object_paths = set(item.get("path", "") for item in object_descriptors)
        for asset_data in selected_asset_data:
            descriptor = _asset_data_descriptor(asset_data)
            if descriptor.get("path") and descriptor.get("path") in object_paths:
                continue
            data_descriptors.append(descriptor)

        asset_descriptors = object_descriptors + data_descriptors
        selected_asset_count = len(asset_descriptors)
        visible_assets = asset_descriptors[:limit]
        placement_plan = []
        for index, asset_descriptor in enumerate(visible_assets):
            asset_path = asset_descriptor.get("path", "")
            if not asset_path:
                continue
            placement_plan.append({{
                "tool": "spatial_add_asset_to_scene",
                "arguments": {{
                    "asset_path": asset_path,
                    "actor_label": _actor_label(asset_descriptor, index),
                    "location": _layout_location(index),
                    "rotation": [0.0, 0.0, 0.0],
                    "scale": [1.0, 1.0, 1.0],
                    "tags": tag_values,
                    "data_layer_names": data_layer_names,
                    "dry_run": True,
                }},
                "placeable_hint": bool(asset_descriptor.get("placeable_hint")),
                "reason": asset_descriptor.get("placeable_reason", ""),
            }})

        _result["selected_asset_count"] = selected_asset_count
        _result["asset_object_count"] = len(object_descriptors)
        _result["asset_data_count"] = len(data_descriptors)
        _result["assets"] = visible_assets
        _result["truncated"] = selected_asset_count > limit
        _result["placement_plan"] = placement_plan
        _result["recommended_workflow"] = [
            "Review placeable_hint entries.",
            "Call spatial_add_asset_to_scene with dry_run=true for each placement_plan item.",
            "Execute individual placements with dry_run=false and allow_mutation=true only after reviewing transforms, tags, and Data Layers.",
            "Use spatial_select_actors and viewport_capture_screenshot for post-placement evidence.",
        ]
        """
    )


def _project_asset_catalog_code(
    *,
    folders: List[str],
    query: str,
    class_names: List[str],
    include_selected: bool,
    include_bounds: bool,
    include_resolver_handoff: bool,
    limit: int,
) -> str:
    return textwrap.dedent(
        f"""\
        import json
        import unreal

        folders = {folders!r}
        query = {str(query or '').strip()!r}
        class_names = {class_names!r}
        include_selected = {bool(include_selected)!r}
        include_bounds = {bool(include_bounds)!r}
        include_resolver_handoff = {bool(include_resolver_handoff)!r}
        limit = max(1, int({int(limit)!r}))

        _result["schema"] = {PROJECT_ASSET_CATALOG_SCHEMA!r}
        _result["folders"] = folders
        _result["query"] = query
        _result["class_names"] = class_names
        _result["include_selected"] = include_selected
        _result["include_bounds"] = include_bounds

        def _safe_text(value):
            try:
                return str(value)
            except Exception:
                return ""

        def _object_path(obj):
            if obj is None:
                return ""
            try:
                return _safe_text(obj.get_path_name())
            except Exception:
                return _safe_text(obj)

        def _object_name(obj):
            if obj is None:
                return ""
            try:
                return _safe_text(obj.get_name())
            except Exception:
                path = _object_path(obj)
                if "." in path:
                    return path.rsplit(".", 1)[-1]
                return path.rsplit("/", 1)[-1] if path else _safe_text(obj)

        def _class_name(obj):
            if obj is None:
                return ""
            try:
                return _safe_text(obj.get_class().get_name())
            except Exception:
                return obj.__class__.__name__

        def _package_name_from_path(path):
            text = _safe_text(path)
            if "." in text:
                return text.split(".", 1)[0]
            return text

        def _folder_from_path(path):
            package_name = _package_name_from_path(path)
            return package_name.rsplit("/", 1)[0] if "/" in package_name else ""

        def _data_value(asset_data, field_name):
            try:
                value = getattr(asset_data, field_name)
                if value:
                    return _safe_text(value)
            except Exception:
                pass
            try:
                value = asset_data.get_editor_property(field_name)
                if value:
                    return _safe_text(value)
            except Exception:
                pass
            return ""

        def _tags_from_asset_data(asset_data):
            values = []
            for field_name in ("tags_and_values", "tag_values"):
                try:
                    raw = getattr(asset_data, field_name)
                except Exception:
                    raw = None
                if raw is None:
                    try:
                        raw = asset_data.get_editor_property(field_name)
                    except Exception:
                        raw = None
                if not raw:
                    continue
                try:
                    items = raw.items()
                except Exception:
                    items = []
                for key, value in items:
                    key_text = _safe_text(key)
                    value_text = _safe_text(value)
                    if key_text:
                        values.append(key_text)
                    if value_text:
                        values.append(value_text)
            return values

        def _asset_data_path(asset_data):
            for field_name in ("object_path", "soft_object_path"):
                value = _data_value(asset_data, field_name)
                if value:
                    return value
            package_name = _data_value(asset_data, "package_name")
            asset_name = _data_value(asset_data, "asset_name")
            if package_name and asset_name:
                return package_name + "." + asset_name
            return package_name

        def _asset_data_descriptor(asset_data, source):
            asset_path = _asset_data_path(asset_data)
            asset_name = _data_value(asset_data, "asset_name")
            if not asset_name and "." in asset_path:
                asset_name = asset_path.rsplit(".", 1)[-1]
            class_name = _data_value(asset_data, "asset_class_path") or _data_value(asset_data, "asset_class")
            package_name = _data_value(asset_data, "package_name") or _package_name_from_path(asset_path)
            return {{
                "asset_path": asset_path,
                "asset_name": asset_name,
                "class_name": class_name,
                "package_name": package_name,
                "folder": _folder_from_path(asset_path),
                "tags": _tags_from_asset_data(asset_data),
                "description": "",
                "approx_size_cm": [],
                "source": source,
            }}

        def _selected_asset_descriptor(obj, source):
            asset_path = _object_path(obj)
            asset_name = _object_name(obj)
            if asset_path and "." not in asset_path and asset_name:
                asset_path = asset_path + "." + asset_name
            return {{
                "asset_path": asset_path,
                "asset_name": asset_name,
                "class_name": _class_name(obj),
                "package_name": _package_name_from_path(asset_path),
                "folder": _folder_from_path(asset_path),
                "tags": [],
                "description": "",
                "approx_size_cm": [],
                "source": source,
            }}

        def _vec_components(value):
            if value is None:
                return None
            try:
                return [float(value.x), float(value.y), float(value.z)]
            except Exception:
                pass
            try:
                raw = list(value)
                if len(raw) >= 3:
                    return [float(raw[0]), float(raw[1]), float(raw[2])]
            except Exception:
                pass
            return None

        def _bounds_size_from_asset_path(asset_path):
            if not include_bounds:
                return []
            library = getattr(unreal, "EditorAssetLibrary", None)
            if library is None or not hasattr(library, "load_asset"):
                return []
            try:
                asset = library.load_asset(asset_path)
            except Exception as exc:
                _warnings.append("Could not load asset for bounds " + asset_path + ": " + str(exc))
                return []
            if asset is None:
                return []
            for method_name in ("get_bounding_box", "get_bounds"):
                method = getattr(asset, method_name, None)
                if not callable(method):
                    continue
                try:
                    bounds = method()
                except Exception:
                    continue
                extent = getattr(bounds, "box_extent", None) or getattr(bounds, "extent", None)
                extent_values = _vec_components(extent)
                if extent_values is not None:
                    return [round(max(0.0, value * 2.0), 3) for value in extent_values]
                min_value = getattr(bounds, "min", None)
                max_value = getattr(bounds, "max", None)
                min_components = _vec_components(min_value)
                max_components = _vec_components(max_value)
                if min_components is not None and max_components is not None:
                    return [round(max(0.0, max_components[index] - min_components[index]), 3) for index in range(3)]
            return []

        def _normalized_class(value):
            return _safe_text(value).lower().replace("_", "").replace(".", "").replace("/", "")

        class_filters = [_normalized_class(value) for value in class_names if _safe_text(value).strip()]
        query_terms = [
            term
            for term in "".join(ch.lower() if ch.isalnum() else " " for ch in query).split()
            if term
        ]

        def _class_allowed(class_name):
            if not class_filters:
                return True
            text = _normalized_class(class_name)
            return any(item in text or text in item for item in class_filters)

        def _matches_query(asset):
            if not query_terms:
                return True
            haystack = " ".join([
                _safe_text(asset.get("asset_path")),
                _safe_text(asset.get("asset_name")),
                _safe_text(asset.get("class_name")),
                _safe_text(asset.get("folder")),
                " ".join(_safe_text(tag) for tag in asset.get("tags", []) or []),
                _safe_text(asset.get("description")),
            ]).lower()
            return all(term in haystack for term in query_terms)

        def _is_valid_game_asset(asset):
            asset_path = _safe_text(asset.get("asset_path"))
            return asset_path.startswith("/Game/") and "." in asset_path

        def _priority(asset):
            class_text = _normalized_class(asset.get("class_name"))
            if "staticmesh" in class_text:
                return 0
            if "blueprint" in class_text:
                return 1
            return 2

        discovered = []
        seen_paths = set()

        def _add_asset(asset):
            if not isinstance(asset, dict):
                return
            if not _is_valid_game_asset(asset):
                return
            if not _class_allowed(asset.get("class_name", "")):
                return
            if not _matches_query(asset):
                return
            asset_path = _safe_text(asset.get("asset_path"))
            key = asset_path.lower()
            if key in seen_paths:
                return
            if include_bounds and not asset.get("approx_size_cm"):
                asset["approx_size_cm"] = _bounds_size_from_asset_path(asset_path)
            discovered.append(asset)
            seen_paths.add(key)

        asset_registry = None
        try:
            asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()
        except Exception as exc:
            _warnings.append("AssetRegistryHelpers.get_asset_registry failed: " + str(exc))

        if asset_registry is not None:
            for folder in folders:
                try:
                    folder_name = unreal.Name(folder) if hasattr(unreal, "Name") else folder
                    try:
                        asset_data_list = asset_registry.get_assets_by_path(folder_name, True, False)
                    except TypeError:
                        asset_data_list = asset_registry.get_assets_by_path(folder_name, True)
                    for asset_data in list(asset_data_list or []):
                        _add_asset(_asset_data_descriptor(asset_data, "asset_registry"))
                except Exception as exc:
                    _warnings.append("AssetRegistry query failed for " + folder + ": " + str(exc))

        editor_asset_library = getattr(unreal, "EditorAssetLibrary", None)
        if editor_asset_library is not None and hasattr(editor_asset_library, "list_assets"):
            for folder in folders:
                try:
                    for asset_path in list(editor_asset_library.list_assets(folder, recursive=True, include_folder=False) or []):
                        asset_path_text = _safe_text(asset_path)
                        asset_name = asset_path_text.rsplit(".", 1)[-1] if "." in asset_path_text else asset_path_text.rsplit("/", 1)[-1]
                        descriptor = {{
                            "asset_path": asset_path_text,
                            "asset_name": asset_name,
                            "class_name": "",
                            "package_name": _package_name_from_path(asset_path_text),
                            "folder": _folder_from_path(asset_path_text),
                            "tags": [],
                            "description": "",
                            "approx_size_cm": [],
                            "source": "editor_asset_library",
                        }}
                        if asset_registry is not None and hasattr(asset_registry, "get_asset_by_object_path"):
                            try:
                                object_path = unreal.Name(asset_path_text) if hasattr(unreal, "Name") else asset_path_text
                                asset_data = asset_registry.get_asset_by_object_path(object_path)
                                enriched = _asset_data_descriptor(asset_data, "editor_asset_library_asset_registry")
                                if _is_valid_game_asset(enriched):
                                    descriptor.update(enriched)
                            except Exception:
                                pass
                        _add_asset(descriptor)
                except Exception as exc:
                    _warnings.append("EditorAssetLibrary.list_assets failed for " + folder + ": " + str(exc))
        else:
            _warnings.append("EditorAssetLibrary.list_assets unavailable; catalog relies on AssetRegistry only.")

        selected_count = 0
        if include_selected:
            editor_utility = getattr(unreal, "EditorUtilityLibrary", None)
            if editor_utility is not None:
                try:
                    for obj in list(editor_utility.get_selected_assets() or []):
                        selected_count += 1
                        _add_asset(_selected_asset_descriptor(obj, "selected_asset"))
                except Exception as exc:
                    _warnings.append("EditorUtilityLibrary.get_selected_assets failed: " + str(exc))
                if hasattr(editor_utility, "get_selected_asset_data"):
                    try:
                        for asset_data in list(editor_utility.get_selected_asset_data() or []):
                            selected_count += 1
                            _add_asset(_asset_data_descriptor(asset_data, "selected_asset_data"))
                    except Exception as exc:
                        _warnings.append("EditorUtilityLibrary.get_selected_asset_data failed: " + str(exc))
            else:
                _warnings.append("EditorUtilityLibrary unavailable; selected assets were not included.")

        discovered.sort(key=lambda asset: (_priority(asset), _safe_text(asset.get("folder")), _safe_text(asset.get("asset_name")), _safe_text(asset.get("asset_path"))))
        assets = discovered[:limit]
        asset_catalog_json = json.dumps({{"assets": assets}}, sort_keys=True)

        _result["asset_count"] = len(assets)
        _result["total_candidate_count"] = len(discovered)
        _result["selected_asset_count"] = selected_count
        _result["truncated"] = len(discovered) > limit
        _result["assets"] = assets
        _result["asset_catalog_json"] = asset_catalog_json
        _result["resolver_handoff"] = {{
            "tool": "spatial_resolve_project_assets",
            "arguments": {{
                "composition_plan_json": "<COMPOSITION_OR_SCREENSHOT_RECONSTRUCTION_JSON>",
                "asset_catalog_json": asset_catalog_json,
            }},
            "enabled": bool(include_resolver_handoff and assets),
        }}
        _result["workflow"] = [
            {{"step": "review_asset_catalog", "reason": "Confirm the candidate list is relevant before matching props."}},
            {{"step": "resolve_project_assets", "tool": "spatial_resolve_project_assets", "enabled": bool(include_resolver_handoff and assets)}},
            {{"step": "bind_then_generate_missing", "tools": ["spatial_bind_generated_assets_to_composition", "spatial_prepare_tripo_generation_batch"]}},
        ]
        _result["legal_review"] = {{
            "requires_review": False,
            "notes": [
                "This tool reads project asset metadata through public Unreal Python editor APIs.",
                "It does not copy Epic native MCP SceneTools or submit paid generation jobs.",
            ],
        }}
        """
    )


def _selected_asset_placement_code(
    *,
    asset_paths: List[str],
    limit: int,
    placement_origin: List[float],
    placement_spacing: float,
    placement_layout: str,
    actor_label_prefix: str,
    rotation: List[float],
    scale: List[float],
    tags: List[str],
    data_layer_names: List[str],
    fail_on_missing_data_layer: bool,
    execute: bool,
    select_actors: bool,
    focus_viewport: bool,
) -> str:
    return textwrap.dedent(
        f"""\
        import math
        import unreal

        explicit_asset_paths = {asset_paths!r}
        limit = max(1, int({int(limit)!r}))
        placement_origin = {placement_origin!r}
        placement_spacing = max(0.0, float({float(placement_spacing)!r}))
        placement_layout = {placement_layout!r}
        actor_label_prefix = {str(actor_label_prefix or '').strip()!r}
        rotation_values = {rotation!r}
        scale_values = {scale!r}
        tag_values = {tags!r}
        data_layer_names = {data_layer_names!r}
        fail_on_missing_data_layer = {bool(fail_on_missing_data_layer)!r}
        execute_batch = {bool(execute)!r}
        select_actors = {bool(select_actors)!r}
        focus_viewport = {bool(focus_viewport)!r}

        _result["schema"] = {SELECTED_ASSET_PLACEMENT_SCHEMA!r}
        _result["dry_run"] = not execute_batch
        _result["will_execute"] = execute_batch
        _result["placement_layout"] = placement_layout
        _result["placement_origin"] = placement_origin
        _result["placement_spacing"] = placement_spacing
        _result["requested_tags"] = tag_values
        _result["requested_data_layers"] = data_layer_names
        _result["fail_on_missing_data_layer"] = fail_on_missing_data_layer
        _result["spawn_attempts"] = []
        _result["placement_plan"] = []
        _result["placed_actors"] = []
        _result["data_layer_results"] = []

        def _safe_text(value):
            try:
                return str(value)
            except Exception:
                return ""

        def _object_path(obj):
            if obj is None:
                return ""
            try:
                return obj.get_path_name()
            except Exception:
                return _safe_text(obj)

        def _class_name(obj):
            if obj is None:
                return ""
            try:
                return obj.get_class().get_name()
            except Exception:
                return obj.__class__.__name__

        def _object_name(obj):
            if obj is None:
                return ""
            try:
                return _safe_text(obj.get_name())
            except Exception:
                path = _object_path(obj)
                if "." in path:
                    return path.rsplit(".", 1)[-1]
                return path.rsplit("/", 1)[-1] if path else _safe_text(obj)

        def _package_name(obj):
            try:
                package = obj.get_outermost()
                if package is not None and hasattr(package, "get_name"):
                    return _safe_text(package.get_name())
            except Exception:
                pass
            path = _object_path(obj)
            if "." in path:
                return path.split(".", 1)[0]
            return path.rsplit("/", 1)[0] if "/" in path else ""

        def _asset_path(obj):
            path = _object_path(obj)
            if path.startswith("/") and "." in path:
                return path
            package_name = _package_name(obj)
            asset_name = _object_name(obj)
            if package_name and asset_name:
                return package_name + "." + asset_name
            return path

        def _asset_name_from_path(asset_path):
            path = _safe_text(asset_path)
            if "." in path:
                return path.rsplit(".", 1)[-1]
            return path.rsplit("/", 1)[-1]

        def _placeable_hint(class_name, asset_path):
            text = (_safe_text(class_name) + " " + _safe_text(asset_path)).lower()
            checks = (
                ("Blueprint", "blueprint" in text),
                ("StaticMesh", "staticmesh" in text),
                ("SkeletalMesh", "skeletalmesh" in text),
                ("NiagaraSystem", "niagarasystem" in text),
                ("ParticleSystem", "particlesystem" in text),
            )
            for label, matched in checks:
                if matched:
                    return True, "Likely placeable through public editor spawn helpers: " + label
            return False, "No placeable asset hint detected; spawn may fail and should be reviewed."

        def _asset_descriptor_common(name, path, class_name, package_name, source, asset_obj=None):
            placeable, reason = _placeable_hint(class_name, path)
            return {{
                "name": name or _asset_name_from_path(path),
                "path": path,
                "class": class_name,
                "package": package_name,
                "source": source,
                "placeable_hint": placeable,
                "placeable_reason": reason,
                "asset": asset_obj,
            }}

        def _asset_descriptor(asset):
            asset_path = _asset_path(asset)
            return _asset_descriptor_common(
                name=_object_name(asset),
                path=asset_path,
                class_name=_class_name(asset),
                package_name=_package_name(asset),
                source="EditorUtilityLibrary.get_selected_assets",
                asset_obj=asset,
            )

        def _explicit_asset_descriptors(paths):
            descriptors = []
            for asset_path in paths:
                asset_path = _safe_text(asset_path).strip()
                if not asset_path:
                    continue
                descriptors.append(_asset_descriptor_common(
                    name=_asset_name_from_path(asset_path),
                    path=asset_path,
                    class_name="",
                    package_name=asset_path.split(".", 1)[0] if "." in asset_path else asset_path.rsplit("/", 1)[0],
                    source="explicit_asset_paths",
                    asset_obj=None,
                ))
            return descriptors

        def _selected_asset_descriptors():
            library = getattr(unreal, "EditorUtilityLibrary", None)
            if library is None:
                _warnings.append("EditorUtilityLibrary is unavailable; selected assets cannot be read.")
                return []
            get_selected_assets = getattr(library, "get_selected_assets", None)
            if not callable(get_selected_assets):
                _warnings.append("EditorUtilityLibrary.get_selected_assets is unavailable; selected assets cannot be read.")
                return []
            try:
                selected_assets = list(get_selected_assets() or [])
            except Exception as exc:
                _warnings.append("EditorUtilityLibrary.get_selected_assets failed: " + str(exc))
                selected_assets = []
            if not selected_assets:
                _warnings.append("No selected Content Browser assets were reported by EditorUtilityLibrary.")
            return [_asset_descriptor(asset) for asset in selected_assets]

        def _unique_descriptors(descriptors):
            seen = set()
            unique = []
            for descriptor in descriptors:
                path = descriptor.get("path", "")
                if not path or path in seen:
                    continue
                seen.add(path)
                unique.append(descriptor)
            return unique

        def _layout_location(index, total_count):
            origin_x = float(placement_origin[0])
            origin_y = float(placement_origin[1])
            origin_z = float(placement_origin[2])
            if placement_layout == "grid":
                columns = max(1, int(math.ceil(math.sqrt(max(1, total_count)))))
                row = index // columns
                column = index % columns
                return [origin_x + column * placement_spacing, origin_y + row * placement_spacing, origin_z]
            if placement_layout == "stack":
                return [origin_x, origin_y, origin_z + index * placement_spacing]
            return [origin_x + index * placement_spacing, origin_y, origin_z]

        def _actor_label(asset_descriptor, index):
            base_name = asset_descriptor.get("name") or ("SelectedAsset_" + str(index + 1))
            if actor_label_prefix:
                return actor_label_prefix + "_" + base_name
            return base_name

        def _vec_dict(value):
            if value is None:
                return None
            return {{"x": float(value.x), "y": float(value.y), "z": float(value.z)}}

        def _rot_dict(value):
            if value is None:
                return None
            return {{
                "pitch": float(getattr(value, "pitch", 0.0)),
                "yaw": float(getattr(value, "yaw", 0.0)),
                "roll": float(getattr(value, "roll", 0.0)),
            }}

        def _actor_tags(actor):
            try:
                raw_tags = list(actor.get_editor_property("tags") or [])
            except Exception:
                raw_tags = list(getattr(actor, "tags", []) or [])
            return [_safe_text(tag) for tag in raw_tags if _safe_text(tag)]

        def _actor_bounds(actor):
            try:
                try:
                    origin, extent = actor.get_actor_bounds(False, False)
                except TypeError:
                    origin, extent = actor.get_actor_bounds(False)
                return {{"origin": _vec_dict(origin), "extent": _vec_dict(extent)}}
            except Exception as exc:
                return {{"error": str(exc)}}

        def _actor_data(actor):
            try:
                location = actor.get_actor_location()
            except Exception:
                location = None
            try:
                rotation = actor.get_actor_rotation()
            except Exception:
                rotation = None
            try:
                scale = actor.get_actor_scale3d()
            except Exception:
                scale = None
            return {{
                "label": _safe_text(actor.get_actor_label()) if hasattr(actor, "get_actor_label") else _safe_text(actor),
                "name": _safe_text(actor.get_name()) if hasattr(actor, "get_name") else _safe_text(actor),
                "class": _class_name(actor),
                "path": _object_path(actor),
                "location": _vec_dict(location),
                "rotation": _rot_dict(rotation),
                "scale": _vec_dict(scale),
                "tags": _actor_tags(actor),
                "bounds": _actor_bounds(actor),
            }}

        def _get_actor_subsystem():
            subsystem_class = getattr(unreal, "EditorActorSubsystem", None)
            if subsystem_class is None:
                return None
            try:
                return unreal.get_editor_subsystem(subsystem_class)
            except Exception as exc:
                _warnings.append("EditorActorSubsystem is unavailable: " + str(exc))
                return None

        def _load_asset(asset_descriptor):
            asset = asset_descriptor.get("asset")
            if asset is not None:
                return asset
            path = asset_descriptor.get("path", "")
            try:
                return unreal.EditorAssetLibrary.load_asset(path)
            except Exception as exc:
                _warnings.append("EditorAssetLibrary.load_asset failed for " + path + ": " + str(exc))
                return None

        def _try_spawn_from_object(asset, location, rotation):
            actor_subsystem = _get_actor_subsystem()
            if actor_subsystem is not None and hasattr(actor_subsystem, "spawn_actor_from_object"):
                try:
                    actor = actor_subsystem.spawn_actor_from_object(asset, location, rotation)
                    _result["spawn_attempts"].append("EditorActorSubsystem.spawn_actor_from_object")
                    if actor is not None:
                        return actor
                except Exception as exc:
                    _warnings.append("EditorActorSubsystem.spawn_actor_from_object failed: " + str(exc))
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "spawn_actor_from_object"):
                try:
                    actor = editor_level_library.spawn_actor_from_object(asset, location, rotation)
                    _result["spawn_attempts"].append("EditorLevelLibrary.spawn_actor_from_object")
                    if actor is not None:
                        return actor
                except Exception as exc:
                    _warnings.append("EditorLevelLibrary.spawn_actor_from_object failed: " + str(exc))
            return None

        def _try_spawn_from_blueprint_class(asset, location, rotation):
            generated_class = None
            for attr_name in ("generated_class", "GeneratedClass"):
                generated_class = getattr(asset, attr_name, None)
                if generated_class is not None:
                    break
            if generated_class is None:
                try:
                    generated_class = asset.get_editor_property("generated_class")
                except Exception:
                    generated_class = None
            if generated_class is None:
                return None
            actor_subsystem = _get_actor_subsystem()
            if actor_subsystem is not None and hasattr(actor_subsystem, "spawn_actor_from_class"):
                try:
                    actor = actor_subsystem.spawn_actor_from_class(generated_class, location, rotation)
                    _result["spawn_attempts"].append("EditorActorSubsystem.spawn_actor_from_class")
                    if actor is not None:
                        return actor
                except Exception as exc:
                    _warnings.append("EditorActorSubsystem.spawn_actor_from_class failed: " + str(exc))
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "spawn_actor_from_class"):
                try:
                    actor = editor_level_library.spawn_actor_from_class(generated_class, location, rotation)
                    _result["spawn_attempts"].append("EditorLevelLibrary.spawn_actor_from_class")
                    if actor is not None:
                        return actor
                except Exception as exc:
                    _warnings.append("EditorLevelLibrary.spawn_actor_from_class failed: " + str(exc))
            return None

        def _apply_actor_tags(actor):
            if not tag_values:
                return []
            try:
                current_tags = list(actor.get_editor_property("tags") or [])
            except Exception:
                current_tags = list(getattr(actor, "tags", []) or [])
            current_text = set(_safe_text(tag) for tag in current_tags)
            name_class = getattr(unreal, "Name", None)
            applied = []
            for tag in tag_values:
                if tag in current_text:
                    applied.append(tag)
                    continue
                current_tags.append(name_class(tag) if name_class is not None else tag)
                current_text.add(tag)
                applied.append(tag)
            try:
                actor.set_editor_property("tags", current_tags)
            except Exception as exc:
                try:
                    actor.tags = current_tags
                except Exception:
                    _warnings.append("Could not apply actor tags: " + str(exc))
                    return []
            return applied

        def _get_data_layer_subsystem():
            subsystem_class = getattr(unreal, "DataLayerEditorSubsystem", None)
            if subsystem_class is None:
                _warnings.append("DataLayerEditorSubsystem is unavailable; Data Layer assignment was skipped.")
                return None
            try:
                return unreal.get_editor_subsystem(subsystem_class)
            except Exception as exc:
                _warnings.append("DataLayerEditorSubsystem is unavailable: " + str(exc))
                return None

        def _data_layer_names(layer):
            names = []
            for method_name in ("get_data_layer_short_name", "get_data_layer_full_name", "get_name", "get_path_name"):
                method = getattr(layer, method_name, None)
                if callable(method):
                    try:
                        value = method()
                        if value:
                            names.append(_safe_text(value))
                    except Exception:
                        pass
            return names

        def _resolve_data_layer(data_layer_subsystem, requested_name):
            name_class = getattr(unreal, "Name", None)
            possible_args = [requested_name]
            if name_class is not None:
                try:
                    possible_args.append(name_class(requested_name))
                except Exception:
                    pass
            for method_name in ("get_data_layer_instance", "get_data_layer_instance_from_name", "get_data_layer_from_name", "get_data_layer_from_label"):
                method = getattr(data_layer_subsystem, method_name, None)
                if not callable(method):
                    continue
                for arg in possible_args:
                    try:
                        layer = method(arg)
                        if layer is not None:
                            return layer, "DataLayerEditorSubsystem." + method_name
                    except Exception:
                        pass
            for method_name in ("get_all_data_layer_instances", "get_all_data_layers"):
                method = getattr(data_layer_subsystem, method_name, None)
                if not callable(method):
                    continue
                try:
                    for layer in list(method() or []):
                        values = [value.lower() for value in _data_layer_names(layer)]
                        wanted = _safe_text(requested_name).lower()
                        if wanted in values or any(value.rsplit("/", 1)[-1].rsplit(".", 1)[-1] == wanted for value in values):
                            return layer, "DataLayerEditorSubsystem." + method_name
                except Exception as exc:
                    _warnings.append("DataLayerEditorSubsystem." + method_name + " failed: " + str(exc))
            return None, ""

        def _assign_actor_to_data_layer(data_layer_subsystem, actor, layer):
            call_specs = [
                ("add_actor_to_data_layer", (actor, layer)),
                ("add_actor_to_data_layer_instance", (actor, layer)),
                ("add_actors_to_data_layer", ([actor], layer)),
                ("add_actors_to_data_layer_instance", ([actor], layer)),
                ("add_actor_to_data_layers", (actor, [layer])),
                ("add_actors_to_data_layers", ([actor], [layer])),
            ]
            for method_name, args in call_specs:
                method = getattr(data_layer_subsystem, method_name, None)
                if not callable(method):
                    continue
                try:
                    outcome = method(*args)
                    if outcome is not False:
                        return True, "DataLayerEditorSubsystem." + method_name
                except Exception as exc:
                    _warnings.append("DataLayerEditorSubsystem." + method_name + " failed: " + str(exc))
            return False, ""

        def _assign_data_layers(actor, asset_path):
            if not data_layer_names:
                return []
            data_layer_subsystem = _get_data_layer_subsystem()
            results = []
            if data_layer_subsystem is None:
                for requested_name in data_layer_names:
                    results.append({{"asset_path": asset_path, "requested": requested_name, "status": "subsystem_unavailable"}})
                    if fail_on_missing_data_layer:
                        _errors.append("DataLayerEditorSubsystem unavailable; could not assign Data Layer: " + requested_name)
                return results
            for requested_name in data_layer_names:
                layer, resolve_method = _resolve_data_layer(data_layer_subsystem, requested_name)
                if layer is None:
                    results.append({{"asset_path": asset_path, "requested": requested_name, "status": "not_found"}})
                    message = "Data Layer not found: " + requested_name
                    if fail_on_missing_data_layer:
                        _errors.append(message)
                    else:
                        _warnings.append(message)
                    continue
                assigned, assign_method = _assign_actor_to_data_layer(data_layer_subsystem, actor, layer)
                results.append({{
                    "asset_path": asset_path,
                    "requested": requested_name,
                    "status": "assigned" if assigned else "assign_failed",
                    "resolve_method": resolve_method,
                    "assign_method": assign_method,
                }})
                if not assigned:
                    message = "Could not assign actor to Data Layer: " + requested_name
                    if fail_on_missing_data_layer:
                        _errors.append(message)
                    else:
                        _warnings.append(message)
            return results

        def _set_selected_level_actors(actors_to_select):
            if not select_actors:
                return False, ""
            actor_subsystem = _get_actor_subsystem()
            if actor_subsystem is not None and hasattr(actor_subsystem, "set_selected_level_actors"):
                try:
                    actor_subsystem.set_selected_level_actors(list(actors_to_select))
                    return True, "EditorActorSubsystem.set_selected_level_actors"
                except Exception as exc:
                    _warnings.append("EditorActorSubsystem.set_selected_level_actors failed: " + str(exc))
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "set_selected_level_actors"):
                try:
                    editor_level_library.set_selected_level_actors(list(actors_to_select))
                    return True, "EditorLevelLibrary.set_selected_level_actors"
                except Exception as exc:
                    _warnings.append("EditorLevelLibrary.set_selected_level_actors failed: " + str(exc))
            return False, ""

        asset_descriptors = _explicit_asset_descriptors(explicit_asset_paths) if explicit_asset_paths else _selected_asset_descriptors()
        asset_descriptors = _unique_descriptors(asset_descriptors)[:limit]
        total_count = len(asset_descriptors)
        if total_count == 0:
            _errors.append("No assets were supplied or selected for batch placement.")

        plans = []
        for index, descriptor in enumerate(asset_descriptors):
            location_values = _layout_location(index, total_count)
            plan = {{
                "asset": {{key: value for key, value in descriptor.items() if key != "asset"}},
                "actor_label": _actor_label(descriptor, index),
                "location": location_values,
                "rotation": rotation_values,
                "scale": scale_values,
                "tags": tag_values,
                "data_layer_names": data_layer_names,
                "placeable_hint": bool(descriptor.get("placeable_hint")),
                "placeable_reason": descriptor.get("placeable_reason", ""),
            }}
            plans.append(plan)

        _result["asset_count"] = total_count
        _result["placement_plan"] = plans
        _result["recommended_follow_up"] = [
            {{"tool": "spatial_select_actors", "reason": "Select placed actors for inspection after execution."}},
            {{"tool": "viewport_capture_screenshot", "reason": "Capture viewport evidence after placement."}},
        ]

        if execute_batch and total_count > 0:
            rotation = unreal.Rotator(float(rotation_values[0]), float(rotation_values[1]), float(rotation_values[2]))
            scale = unreal.Vector(float(scale_values[0]), float(scale_values[1]), float(scale_values[2]))
            placed_actors = []
            for index, descriptor in enumerate(asset_descriptors):
                asset_path = descriptor.get("path", "")
                location_values = plans[index]["location"]
                location = unreal.Vector(float(location_values[0]), float(location_values[1]), float(location_values[2]))
                asset = _load_asset(descriptor)
                if asset is None:
                    _errors.append("Asset could not be loaded: " + asset_path)
                    continue
                actor = _try_spawn_from_object(asset, location, rotation)
                if actor is None:
                    actor = _try_spawn_from_blueprint_class(asset, location, rotation)
                if actor is None:
                    _errors.append("Could not spawn an actor from asset: " + asset_path)
                    continue
                try:
                    actor.set_actor_scale3d(scale)
                except Exception as exc:
                    _warnings.append("Could not apply actor scale for " + asset_path + ": " + str(exc))
                actor_label = plans[index]["actor_label"]
                if actor_label:
                    try:
                        actor.set_actor_label(actor_label)
                    except Exception as exc:
                        _warnings.append("Could not apply actor label for " + asset_path + ": " + str(exc))
                applied_tags = _apply_actor_tags(actor)
                layer_results = _assign_data_layers(actor, asset_path)
                _result["data_layer_results"].extend(layer_results)
                actor_data = _actor_data(actor)
                actor_data["asset_path"] = asset_path
                actor_data["applied_tags"] = applied_tags
                placed_actors.append(actor)
                _result["placed_actors"].append(actor_data)
            selected, selection_method = _set_selected_level_actors(placed_actors)
            _result["selected"] = selected
            _result["selection_method"] = selection_method
            if focus_viewport:
                _warnings.append("focus_viewport requested; use spatial_select_actors or focus_viewport plus viewport_capture_screenshot after batch placement for explicit evidence.")
            _result["placed_count"] = len(placed_actors)
        else:
            _result["placed_count"] = 0
            _result["selected"] = False
            _result["selection_method"] = ""
        """
    )


def _actor_selection_code(
    *,
    actors: List[str],
    query: str,
    class_filter: str,
    tag_filter: str,
    center: Optional[List[float]],
    radius: float,
    box_min: Optional[List[float]],
    box_max: Optional[List[float]],
    include_hidden: bool,
    limit: int,
    apply_selection: bool,
    selection_mode: str,
    allow_empty_selection: bool,
    focus_viewport: bool,
    focus_distance: float,
) -> str:
    return (
        _common_scene_code(
            include_hidden=include_hidden,
            class_filter=class_filter,
            tag_filter=tag_filter,
            limit=limit,
            include_components=False,
        )
        + textwrap.dedent(
            f"""\

            requested_actor_names = {actors!r}
            query_text = {str(query or '').strip().lower()!r}
            center = _literal_vec({center!r})
            radius = float({float(radius)!r})
            box_min = _literal_vec({box_min!r})
            box_max = _literal_vec({box_max!r})
            apply_selection = {bool(apply_selection)!r}
            selection_mode = {selection_mode!r}
            allow_empty_selection = {bool(allow_empty_selection)!r}
            focus_viewport = {bool(focus_viewport)!r}
            focus_distance = max(1.0, float({float(focus_distance)!r}))

            def _inside_box(actor):
                if box_min is None and box_max is None:
                    return True
                try:
                    loc = _vec_tuple(actor.get_actor_location())
                except Exception:
                    return False
                if box_min is not None:
                    if loc[0] < box_min[0] or loc[1] < box_min[1] or loc[2] < box_min[2]:
                        return False
                if box_max is not None:
                    if loc[0] > box_max[0] or loc[1] > box_max[1] or loc[2] > box_max[2]:
                        return False
                return True

            def _inside_radius(actor):
                if center is None or radius <= 0.0:
                    return True
                actor_location = _actor_location_tuple(actor)
                distance = _distance(actor_location, center)
                return distance is not None and distance <= radius

            def _matches_selection_constraints(actor):
                return _actor_matches_filters(actor) and _inside_box(actor) and _inside_radius(actor)

            def _actor_identity(actor):
                path = _object_path(actor)
                if path:
                    return path
                return _actor_label(actor)

            def _unique_actors(actors_to_unique):
                seen = set()
                unique = []
                for actor in actors_to_unique:
                    key = _actor_identity(actor)
                    if key in seen:
                        continue
                    seen.add(key)
                    unique.append(actor)
                return unique

            def _resolve_requested_actors(names):
                resolved = []
                missing = []
                for requested_name in names:
                    actor = _find_actor(requested_name)
                    if actor is None:
                        missing.append(requested_name)
                        continue
                    if not _matches_selection_constraints(actor):
                        missing.append(requested_name)
                        continue
                    resolved.append(actor)
                return _unique_actors(resolved), missing

            def _query_matching_actors():
                matches = []
                for actor in filtered_actors:
                    if query_text and not _text_matches(actor, query_text):
                        continue
                    if not _inside_box(actor):
                        continue
                    if not _inside_radius(actor):
                        continue
                    matches.append(actor)
                if center is not None:
                    matches.sort(key=lambda item: (_distance(_actor_location_tuple(item), center) is None, _distance(_actor_location_tuple(item), center) or 0.0, _actor_label(item)))
                else:
                    matches.sort(key=lambda item: _actor_label(item))
                return matches

            def _selection_union(current, matches):
                return _unique_actors(list(current) + list(matches))

            def _selection_remove(current, matches):
                remove_keys = set(_actor_identity(actor) for actor in matches)
                return [actor for actor in current if _actor_identity(actor) not in remove_keys]

            def _set_selected_level_actors(actors_to_select):
                if _actor_subsystem is not None and hasattr(_actor_subsystem, "set_selected_level_actors"):
                    try:
                        _actor_subsystem.set_selected_level_actors(list(actors_to_select))
                        return True, "EditorActorSubsystem.set_selected_level_actors"
                    except Exception as exc:
                        _warnings.append("EditorActorSubsystem.set_selected_level_actors failed: " + str(exc))
                editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
                if editor_level_library is not None and hasattr(editor_level_library, "set_selected_level_actors"):
                    try:
                        editor_level_library.set_selected_level_actors(list(actors_to_select))
                        return True, "EditorLevelLibrary.set_selected_level_actors"
                    except Exception as exc:
                        _warnings.append("EditorLevelLibrary.set_selected_level_actors failed: " + str(exc))
                return False, ""

            def _bounds_center(bounds):
                if not isinstance(bounds, dict) or not bounds.get("available"):
                    return None
                center_data = bounds.get("center") or {{}}
                return (
                    float(center_data.get("x", 0.0)),
                    float(center_data.get("y", 0.0)),
                    float(center_data.get("z", 0.0)),
                )

            def _focus_viewport_on(center_tuple):
                level_editor_subsystem_class = getattr(unreal, "LevelEditorSubsystem", None)
                if level_editor_subsystem_class is None:
                    return False, "LevelEditorSubsystem unavailable"
                try:
                    level_editor_subsystem = unreal.get_editor_subsystem(level_editor_subsystem_class)
                except Exception as exc:
                    return False, "LevelEditorSubsystem unavailable: " + str(exc)
                set_camera = getattr(level_editor_subsystem, "set_level_viewport_camera_info", None)
                if not callable(set_camera):
                    return False, "LevelEditorSubsystem.set_level_viewport_camera_info unavailable"
                target_x, target_y, target_z = center_tuple
                camera_location = unreal.Vector(target_x - focus_distance, target_y, target_z + focus_distance * 0.35)
                delta_x = target_x - float(camera_location.x)
                delta_y = target_y - float(camera_location.y)
                delta_z = target_z - float(camera_location.z)
                horizontal = max(1.0, math.sqrt(delta_x * delta_x + delta_y * delta_y))
                yaw = math.degrees(math.atan2(delta_y, delta_x))
                pitch = math.degrees(math.atan2(delta_z, horizontal))
                camera_rotation = unreal.Rotator(float(pitch), float(yaw), 0.0)
                try:
                    set_camera(camera_location, camera_rotation)
                    return True, "LevelEditorSubsystem.set_level_viewport_camera_info"
                except Exception as exc:
                    return False, "LevelEditorSubsystem.set_level_viewport_camera_info failed: " + str(exc)

            if requested_actor_names:
                matched_actor_objects, missing_requested = _resolve_requested_actors(requested_actor_names)
            else:
                matched_actor_objects = _query_matching_actors()
                missing_requested = []

            total_match_count = len(matched_actor_objects)
            matched_actor_objects = matched_actor_objects[:limit]
            matched_actor_data = [_actor_data(actor, include_bounds=True, center=center) for actor in matched_actor_objects]
            aggregate_bounds = _aggregate_bounds(matched_actor_objects)
            focus_center = _bounds_center(aggregate_bounds)
            if focus_center is None and matched_actor_objects:
                focus_center = _actor_location_tuple(matched_actor_objects[0])

            if missing_requested:
                _warnings.append("Some requested actors were not found or did not pass filters: " + ", ".join(missing_requested))

            recommended_follow_up = []
            if focus_center is not None:
                focus_location = [float(focus_center[0]), float(focus_center[1]), float(focus_center[2])]
                recommended_follow_up.append({{
                    "tool": "focus_viewport",
                    "arguments": {{"location": focus_location, "distance": focus_distance}},
                    "reason": "Frame the selected spatial target through Ghost's existing bridge command.",
                }})
                recommended_follow_up.append({{
                    "tool": "viewport_capture_screenshot",
                    "arguments": {{"artifact_name": "spatial_selection", "show_ui": False}},
                    "reason": "Capture viewport evidence after selection/focus.",
                }})

            selected_before = [_actor_data(actor, include_bounds=False) for actor in selected_actors[:limit]]
            selected_after = selected_before
            selection_applied = False
            selection_method = ""
            focus_result = {{"requested": focus_viewport, "applied": False, "method": "", "message": ""}}

            if apply_selection:
                if not matched_actor_objects and selection_mode != "remove" and not allow_empty_selection:
                    _errors.append("No actors matched; pass allow_empty_selection=True to intentionally clear selection.")
                else:
                    if selection_mode == "replace":
                        target_selection = matched_actor_objects
                    elif selection_mode == "add":
                        target_selection = _selection_union(selected_actors, matched_actor_objects)
                    elif selection_mode == "remove":
                        target_selection = _selection_remove(selected_actors, matched_actor_objects)
                    else:
                        target_selection = matched_actor_objects

                    selection_applied, selection_method = _set_selected_level_actors(target_selection)
                    if not selection_applied:
                        _errors.append("Could not apply actor selection; no compatible editor selection API was available.")
                    else:
                        selected_after = [_actor_data(actor, include_bounds=False) for actor in target_selection[:limit]]
                        if focus_viewport:
                            if focus_center is None:
                                focus_result["message"] = "No focus center was available."
                                _warnings.append(focus_result["message"])
                            else:
                                focused, focus_message = _focus_viewport_on(focus_center)
                                focus_result = {{
                                    "requested": True,
                                    "applied": focused,
                                    "method": focus_message if focused else "",
                                    "message": "" if focused else focus_message,
                                }}
                                if not focused:
                                    _warnings.append(focus_message)

            _result["schema"] = {ACTOR_SELECTION_SCHEMA!r}
            _result["dry_run"] = not apply_selection
            _result["will_execute"] = apply_selection
            _result["selection_mode"] = selection_mode
            _result["filters"] = {{
                "actors": requested_actor_names,
                "query": query_text,
                "class_filter": class_filter,
                "tag_filter": tag_filter,
                "include_hidden": include_hidden,
                "center": center,
                "radius": radius,
                "box_min": box_min,
                "box_max": box_max,
                "limit": limit,
            }}
            _result["matched_actor_count"] = total_match_count
            _result["actors"] = matched_actor_data
            _result["truncated"] = total_match_count > limit
            _result["aggregate_bounds"] = aggregate_bounds
            _result["focus_center"] = (
                {{"x": float(focus_center[0]), "y": float(focus_center[1]), "z": float(focus_center[2])}}
                if focus_center is not None
                else None
            )
            _result["selected_before"] = selected_before
            _result["selected_after"] = selected_after
            _result["selection_applied"] = selection_applied
            _result["selection_method"] = selection_method
            _result["focus_result"] = focus_result
            _result["recommended_follow_up"] = recommended_follow_up
            """
        )
    )


def _surface_probe_code(
    *,
    points: List[List[float]],
    center: List[float],
    grid_count: int,
    grid_spacing: float,
    trace_up: float,
    trace_down: float,
    trace_channel: str,
    ignore_actor_query: str,
    placement_offset: float,
    include_handoff: bool,
) -> str:
    return textwrap.dedent(
        f"""\
        import math
        import unreal

        point_values = {points!r}
        center_values = {center!r}
        grid_count = max(1, int({int(grid_count)!r}))
        grid_spacing = max(0.0, float({float(grid_spacing)!r}))
        trace_up = max(1.0, float({float(trace_up)!r}))
        trace_down = max(1.0, float({float(trace_down)!r}))
        trace_channel_name = {trace_channel!r}
        ignore_actor_query = {str(ignore_actor_query or '').strip().lower()!r}
        placement_offset = float({float(placement_offset)!r})
        include_handoff = {bool(include_handoff)!r}

        _result["schema"] = {SURFACE_PROBE_SCHEMA!r}
        _result["trace_channel"] = trace_channel_name
        _result["trace_up"] = trace_up
        _result["trace_down"] = trace_down
        _result["placement_offset"] = placement_offset
        _result["probes"] = []
        _result["surface_adjusted_locations"] = []
        _result["placement_handoffs"] = []

        def _safe_text(value):
            try:
                return str(value)
            except Exception:
                return ""

        def _vec_dict(value):
            if value is None:
                return None
            return {{
                "x": float(getattr(value, "x", 0.0)),
                "y": float(getattr(value, "y", 0.0)),
                "z": float(getattr(value, "z", 0.0)),
            }}

        def _vec_list(value):
            data = _vec_dict(value)
            if data is None:
                return None
            return [round(float(data["x"]), 3), round(float(data["y"]), 3), round(float(data["z"]), 3)]

        def _list_to_vector(values):
            return unreal.Vector(float(values[0]), float(values[1]), float(values[2]))

        def _object_path(obj):
            if obj is None:
                return ""
            try:
                return obj.get_path_name()
            except Exception:
                return _safe_text(obj)

        def _class_name(obj):
            if obj is None:
                return ""
            try:
                return obj.get_class().get_name()
            except Exception:
                return obj.__class__.__name__

        def _actor_label(actor):
            if actor is None:
                return ""
            try:
                label = actor.get_actor_label()
                if label:
                    return _safe_text(label)
            except Exception:
                pass
            try:
                return _safe_text(actor.get_name())
            except Exception:
                return _safe_text(actor)

        def _actor_descriptor(actor):
            if actor is None:
                return None
            return {{
                "label": _actor_label(actor),
                "class": _class_name(actor),
                "path": _object_path(actor),
            }}

        def _get_world():
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None:
                for method_name in ("get_editor_world", "get_game_world"):
                    method = getattr(editor_level_library, method_name, None)
                    if callable(method):
                        try:
                            world = method()
                            if world is not None:
                                return world
                        except Exception as exc:
                            _warnings.append("EditorLevelLibrary." + method_name + " failed: " + str(exc))
                get_pie_worlds = getattr(editor_level_library, "get_pie_worlds", None)
                if callable(get_pie_worlds):
                    try:
                        worlds = list(get_pie_worlds(False) or [])
                        if worlds:
                            return worlds[0]
                    except Exception as exc:
                        _warnings.append("EditorLevelLibrary.get_pie_worlds failed: " + str(exc))
            return None

        def _get_all_actors():
            subsystem_class = getattr(unreal, "EditorActorSubsystem", None)
            if subsystem_class is not None:
                try:
                    subsystem = unreal.get_editor_subsystem(subsystem_class)
                    method = getattr(subsystem, "get_all_level_actors", None)
                    if callable(method):
                        return list(method() or [])
                except Exception as exc:
                    _warnings.append("EditorActorSubsystem actor read failed: " + str(exc))
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "get_all_level_actors"):
                try:
                    return list(editor_level_library.get_all_level_actors() or [])
                except Exception as exc:
                    _warnings.append("EditorLevelLibrary.get_all_level_actors failed: " + str(exc))
            return []

        def _matches_ignore_query(actor):
            if not ignore_actor_query:
                return False
            values = (_actor_label(actor), _class_name(actor), _object_path(actor))
            return any(ignore_actor_query in _safe_text(value).lower() for value in values)

        def _ignored_actors():
            if not ignore_actor_query:
                return []
            return [actor for actor in _get_all_actors() if _matches_ignore_query(actor)]

        def _collision_channel():
            collision_channel = getattr(unreal, "CollisionChannel", None)
            if collision_channel is None:
                return None
            if trace_channel_name == "camera":
                return getattr(collision_channel, "ECC_CAMERA", None)
            return getattr(collision_channel, "ECC_VISIBILITY", None)

        def _trace_type_query():
            trace_type_query = getattr(unreal, "TraceTypeQuery", None)
            if trace_type_query is None:
                return None
            if trace_channel_name == "camera":
                return getattr(trace_type_query, "TRACE_TYPE_QUERY2", None)
            return getattr(trace_type_query, "TRACE_TYPE_QUERY1", None)

        def _hit_payload(hit):
            if isinstance(hit, (tuple, list)):
                if len(hit) >= 2:
                    return hit[1]
                if len(hit) == 1:
                    return hit[0]
                return None
            return hit

        def _hit_has_blocking(hit):
            if hit is None:
                return False
            if isinstance(hit, (tuple, list)):
                if len(hit) >= 1 and isinstance(hit[0], bool):
                    return bool(hit[0])
                return bool(hit)
            for attr_name in ("blocking_hit", "bBlockingHit"):
                try:
                    value = getattr(hit, attr_name)
                    if isinstance(value, bool):
                        return value
                except Exception:
                    pass
            return bool(hit)

        def _line_trace(world, start, end, actors_to_ignore):
            try:
                channel = _collision_channel()
                if channel is not None and hasattr(world, "line_trace_single_by_channel"):
                    hit = world.line_trace_single_by_channel(start, end, channel)
                    if _hit_has_blocking(hit):
                        return hit
            except Exception as exc:
                _warnings.append("world.line_trace_single_by_channel failed: " + str(exc))
            try:
                trace_query = _trace_type_query()
                if trace_query is None:
                    trace_query = getattr(unreal.TraceTypeQuery, "TRACE_TYPE_QUERY1")
                hit_tuple = unreal.SystemLibrary.line_trace_single(
                    world,
                    start,
                    end,
                    trace_query,
                    False,
                    actors_to_ignore,
                    unreal.DrawDebugTrace.NONE,
                    True,
                    unreal.LinearColor(1.0, 0.0, 0.0, 1.0),
                    unreal.LinearColor(0.0, 1.0, 0.0, 1.0),
                    0.05,
                )
                if _hit_has_blocking(hit_tuple):
                    return hit_tuple
            except Exception as exc:
                _warnings.append("SystemLibrary.line_trace_single failed: " + str(exc))
            return None

        def _hit_vector(hit_result, attr_names):
            if hit_result is None:
                return None
            for attr_name in attr_names:
                try:
                    value = getattr(hit_result, attr_name)
                    if callable(value):
                        value = value()
                    if value is not None:
                        return value
                except Exception:
                    pass
            return None

        def _hit_actor(hit_result):
            if hit_result is None:
                return None
            for method_name in ("get_actor",):
                method = getattr(hit_result, method_name, None)
                if callable(method):
                    try:
                        actor = method()
                        if actor is not None:
                            return actor
                    except Exception:
                        pass
            try:
                return getattr(hit_result, "actor")
            except Exception:
                return None

        def _probe_points():
            if point_values:
                return [list(point) for point in point_values]
            count = max(1, grid_count)
            columns = max(1, int(math.ceil(math.sqrt(count))))
            rows = max(1, int(math.ceil(float(count) / float(columns))))
            start_x = -((columns - 1) * grid_spacing) / 2.0
            start_y = -((rows - 1) * grid_spacing) / 2.0
            generated = []
            for index in range(count):
                column = index % columns
                row = index // columns
                generated.append([
                    float(center_values[0]) + start_x + column * grid_spacing,
                    float(center_values[1]) + start_y + row * grid_spacing,
                    float(center_values[2]),
                ])
            return generated

        world = _get_world()
        ignored = _ignored_actors()
        probe_points = _probe_points()
        if world is None:
            _errors.append("Could not resolve an Unreal editor world for surface probing.")

        hit_count = 0
        for index, point in enumerate(probe_points):
            input_location = [float(point[0]), float(point[1]), float(point[2])]
            start_location = [input_location[0], input_location[1], input_location[2] + trace_up]
            end_location = [input_location[0], input_location[1], input_location[2] - trace_down]
            start = _list_to_vector(start_location)
            end = _list_to_vector(end_location)
            hit = _line_trace(world, start, end, ignored) if world is not None else None
            hit_result = _hit_payload(hit)
            has_hit = _hit_has_blocking(hit)
            hit_location_vec = _hit_vector(hit_result, ("impact_point", "location"))
            hit_normal_vec = _hit_vector(hit_result, ("impact_normal", "normal"))
            hit_location = _vec_list(hit_location_vec)
            hit_normal = _vec_list(hit_normal_vec) or [0.0, 0.0, 1.0]
            hit_actor = _hit_actor(hit_result)
            if has_hit and hit_location is not None:
                hit_count += 1
                placement_location = [
                    round(hit_location[0] + hit_normal[0] * placement_offset, 3),
                    round(hit_location[1] + hit_normal[1] * placement_offset, 3),
                    round(hit_location[2] + hit_normal[2] * placement_offset, 3),
                ]
            else:
                placement_location = [round(input_location[0], 3), round(input_location[1], 3), round(input_location[2], 3)]

            distance = None
            if hit_location is not None:
                dx = float(start_location[0]) - float(hit_location[0])
                dy = float(start_location[1]) - float(hit_location[1])
                dz = float(start_location[2]) - float(hit_location[2])
                distance = round(math.sqrt(dx * dx + dy * dy + dz * dz), 3)

            probe = {{
                "index": index,
                "input_location": [round(value, 3) for value in input_location],
                "trace_start": [round(value, 3) for value in start_location],
                "trace_end": [round(value, 3) for value in end_location],
                "hit": bool(has_hit and hit_location is not None),
                "hit_location": hit_location,
                "hit_normal": hit_normal if has_hit else None,
                "hit_actor": _actor_descriptor(hit_actor),
                "distance_from_trace_start": distance,
                "placement_location": placement_location,
            }}
            _result["probes"].append(probe)
            _result["surface_adjusted_locations"].append(placement_location)
            if include_handoff:
                _result["placement_handoffs"].append({{
                    "tool": "spatial_add_asset_to_scene",
                    "arguments_template": {{
                        "asset_path": "<fill Content Browser asset path>",
                        "location": placement_location,
                        "dry_run": True,
                    }},
                    "reason": "Use the surface-adjusted location after selecting an asset path.",
                }})

        _result["point_count"] = len(probe_points)
        _result["hit_count"] = hit_count
        _result["miss_count"] = len(probe_points) - hit_count
        _result["ignored_actor_count"] = len(ignored)
        _result["recommended_workflow"] = [
            "Review hit actors and surface normals before placement.",
            "Copy a placement_location into spatial_add_asset_to_scene or use placement_handoffs as dry-run templates.",
            "Execute placement only through dry_run=false and allow_mutation=true after transform review.",
            "Use spatial_select_actors plus viewport_capture_screenshot for post-placement evidence.",
        ]
        """
    )


def _placement_validation_code(
    *,
    actors: List[str],
    query: str,
    class_filter: str,
    tag_filter: str,
    center: Optional[List[float]],
    radius: float,
    include_hidden: bool,
    limit: int,
    trace_up: float,
    trace_down: float,
    trace_channel: str,
    surface_tolerance: float,
    clearance_padding: float,
    ignore_self: bool,
    include_evidence_handoff: bool,
) -> str:
    return (
        _common_scene_code(
            include_hidden=include_hidden,
            class_filter=class_filter,
            tag_filter=tag_filter,
            limit=limit,
            include_components=False,
        )
        + textwrap.dedent(
            f"""\

            requested_actor_names = {actors!r}
            query_text = {str(query or '').strip().lower()!r}
            center = _literal_vec({center!r})
            radius = float({float(radius)!r})
            trace_up = max(1.0, float({float(trace_up)!r}))
            trace_down = max(1.0, float({float(trace_down)!r}))
            trace_channel_name = {trace_channel!r}
            surface_tolerance = max(0.0, float({float(surface_tolerance)!r}))
            clearance_padding = max(0.0, float({float(clearance_padding)!r}))
            ignore_self = {bool(ignore_self)!r}
            include_evidence_handoff = {bool(include_evidence_handoff)!r}

            def _vec_list(value):
                if value is None:
                    return None
                return [
                    round(float(getattr(value, "x", 0.0)), 3),
                    round(float(getattr(value, "y", 0.0)), 3),
                    round(float(getattr(value, "z", 0.0)), 3),
                ]

            def _list_to_vector(values):
                return unreal.Vector(float(values[0]), float(values[1]), float(values[2]))

            def _get_world():
                editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
                if editor_level_library is not None:
                    for method_name in ("get_editor_world", "get_game_world"):
                        method = getattr(editor_level_library, method_name, None)
                        if callable(method):
                            try:
                                world = method()
                                if world is not None:
                                    return world
                            except Exception as exc:
                                _warnings.append("EditorLevelLibrary." + method_name + " failed: " + str(exc))
                    get_pie_worlds = getattr(editor_level_library, "get_pie_worlds", None)
                    if callable(get_pie_worlds):
                        try:
                            worlds = list(get_pie_worlds(False) or [])
                            if worlds:
                                return worlds[0]
                        except Exception as exc:
                            _warnings.append("EditorLevelLibrary.get_pie_worlds failed: " + str(exc))
                return None

            def _collision_channel():
                collision_channel = getattr(unreal, "CollisionChannel", None)
                if collision_channel is None:
                    return None
                if trace_channel_name == "camera":
                    return getattr(collision_channel, "ECC_CAMERA", None)
                return getattr(collision_channel, "ECC_VISIBILITY", None)

            def _trace_type_query():
                trace_type_query = getattr(unreal, "TraceTypeQuery", None)
                if trace_type_query is None:
                    return None
                if trace_channel_name == "camera":
                    return getattr(trace_type_query, "TRACE_TYPE_QUERY2", None)
                return getattr(trace_type_query, "TRACE_TYPE_QUERY1", None)

            def _hit_payload(hit):
                if isinstance(hit, (tuple, list)):
                    if len(hit) >= 2:
                        return hit[1]
                    if len(hit) == 1:
                        return hit[0]
                    return None
                return hit

            def _hit_has_blocking(hit):
                if hit is None:
                    return False
                if isinstance(hit, (tuple, list)):
                    if len(hit) >= 1 and isinstance(hit[0], bool):
                        return bool(hit[0])
                    return bool(hit)
                for attr_name in ("blocking_hit", "bBlockingHit"):
                    try:
                        value = getattr(hit, attr_name)
                        if isinstance(value, bool):
                            return value
                    except Exception:
                        pass
                return bool(hit)

            def _line_trace(world, start, end, actors_to_ignore):
                try:
                    channel = _collision_channel()
                    if channel is not None and hasattr(world, "line_trace_single_by_channel"):
                        hit = world.line_trace_single_by_channel(start, end, channel)
                        if _hit_has_blocking(hit):
                            return hit
                except Exception as exc:
                    _warnings.append("world.line_trace_single_by_channel failed: " + str(exc))
                try:
                    trace_query = _trace_type_query()
                    if trace_query is None:
                        trace_query = getattr(unreal.TraceTypeQuery, "TRACE_TYPE_QUERY1")
                    hit_tuple = unreal.SystemLibrary.line_trace_single(
                        world,
                        start,
                        end,
                        trace_query,
                        False,
                        actors_to_ignore,
                        unreal.DrawDebugTrace.NONE,
                        True,
                        unreal.LinearColor(1.0, 0.0, 0.0, 1.0),
                        unreal.LinearColor(0.0, 1.0, 0.0, 1.0),
                        0.05,
                    )
                    if _hit_has_blocking(hit_tuple):
                        return hit_tuple
                except Exception as exc:
                    _warnings.append("SystemLibrary.line_trace_single failed: " + str(exc))
                return None

            def _hit_vector(hit_result, attr_names):
                if hit_result is None:
                    return None
                for attr_name in attr_names:
                    try:
                        value = getattr(hit_result, attr_name)
                        if callable(value):
                            value = value()
                        if value is not None:
                            return value
                    except Exception:
                        pass
                return None

            def _hit_actor(hit_result):
                if hit_result is None:
                    return None
                method = getattr(hit_result, "get_actor", None)
                if callable(method):
                    try:
                        actor = method()
                        if actor is not None:
                            return actor
                    except Exception:
                        pass
                try:
                    return getattr(hit_result, "actor")
                except Exception:
                    return None

            def _actor_descriptor(actor):
                if actor is None:
                    return None
                return {{
                    "label": _actor_label(actor),
                    "class": _class_name(actor),
                    "path": _object_path(actor),
                }}

            def _bounds_min_max(actor):
                bounds = _actor_bounds(actor)
                if not isinstance(bounds, dict) or "min" not in bounds or "max" not in bounds:
                    return None
                try:
                    return (
                        [float(bounds["min"]["x"]), float(bounds["min"]["y"]), float(bounds["min"]["z"])],
                        [float(bounds["max"]["x"]), float(bounds["max"]["y"]), float(bounds["max"]["z"])],
                    )
                except Exception:
                    return None

            def _bounds_probe_point(actor):
                bounds = _actor_bounds(actor)
                if isinstance(bounds, dict) and "origin" in bounds and "extent" in bounds:
                    origin = bounds.get("origin") or {{}}
                    extent = bounds.get("extent") or {{}}
                    try:
                        return [
                            float(origin.get("x", 0.0)),
                            float(origin.get("y", 0.0)),
                            float(origin.get("z", 0.0)) - float(extent.get("z", 0.0)),
                        ]
                    except Exception:
                        pass
                location = _actor_location_tuple(actor)
                if location is None:
                    return [0.0, 0.0, 0.0]
                return [float(location[0]), float(location[1]), float(location[2])]

            def _expanded_bounds(actor):
                bounds = _bounds_min_max(actor)
                if bounds is None:
                    return None
                min_v, max_v = bounds
                return (
                    [min_v[0] - clearance_padding, min_v[1] - clearance_padding, min_v[2] - clearance_padding],
                    [max_v[0] + clearance_padding, max_v[1] + clearance_padding, max_v[2] + clearance_padding],
                )

            def _aabb_overlaps(a_bounds, b_bounds):
                if a_bounds is None or b_bounds is None:
                    return False
                a_min, a_max = a_bounds
                b_min, b_max = b_bounds
                return (
                    a_min[0] <= b_max[0] and a_max[0] >= b_min[0] and
                    a_min[1] <= b_max[1] and a_max[1] >= b_min[1] and
                    a_min[2] <= b_max[2] and a_max[2] >= b_min[2]
                )

            def _clearance_overlaps(actor):
                actor_bounds = _expanded_bounds(actor)
                if actor_bounds is None:
                    return {{"status": "unknown", "overlap_count": 0, "overlaps": [], "padding": clearance_padding}}
                overlaps = []
                for candidate in all_actors:
                    if candidate == actor:
                        continue
                    if not _actor_matches_filters(candidate):
                        continue
                    candidate_bounds = _bounds_min_max(candidate)
                    if _aabb_overlaps(actor_bounds, candidate_bounds):
                        overlaps.append(_actor_descriptor(candidate))
                    if len(overlaps) >= 20:
                        break
                return {{
                    "status": "potential_overlap" if overlaps else "clear",
                    "overlap_count": len(overlaps),
                    "overlaps": overlaps,
                    "padding": clearance_padding,
                    "method": "axis_aligned_bounds_overlap",
                }}

            def _inside_radius(actor):
                if center is None or radius <= 0.0:
                    return True
                actor_location = _actor_location_tuple(actor)
                distance = _distance(actor_location, center)
                return distance is not None and distance <= radius

            def _resolve_targets():
                missing = []
                if requested_actor_names:
                    resolved = []
                    for requested_name in requested_actor_names:
                        actor = _find_actor(requested_name)
                        if actor is None or not _actor_matches_filters(actor) or not _inside_radius(actor):
                            missing.append(requested_name)
                            continue
                        resolved.append(actor)
                    return resolved, missing
                matches = []
                for actor in filtered_actors:
                    if query_text and not _text_matches(actor, query_text):
                        continue
                    if not _inside_radius(actor):
                        continue
                    matches.append(actor)
                if center is not None:
                    matches.sort(key=lambda item: (_distance(_actor_location_tuple(item), center) is None, _distance(_actor_location_tuple(item), center) or 0.0, _actor_label(item)))
                else:
                    matches.sort(key=lambda item: _actor_label(item))
                return matches, missing

            world = _get_world()
            if world is None:
                _warnings.append("Could not resolve an Unreal editor world; surface traces will report no hit.")

            target_actors, missing_requested = _resolve_targets()
            total_target_count = len(target_actors)
            target_actors = target_actors[:limit]
            if missing_requested:
                _warnings.append("Some requested actors were not found or did not pass filters: " + ", ".join(missing_requested))

            validations = []
            on_surface_count = 0
            floating_count = 0
            intersecting_count = 0
            no_surface_hit_count = 0
            potential_overlap_count = 0

            for actor in target_actors:
                probe_point = _bounds_probe_point(actor)
                start_location = [probe_point[0], probe_point[1], probe_point[2] + trace_up]
                end_location = [probe_point[0], probe_point[1], probe_point[2] - trace_down]
                ignored = [actor] if ignore_self else []
                hit = _line_trace(world, _list_to_vector(start_location), _list_to_vector(end_location), ignored) if world is not None else None
                hit_result = _hit_payload(hit)
                hit_location_vec = _hit_vector(hit_result, ("impact_point", "location"))
                hit_normal_vec = _hit_vector(hit_result, ("impact_normal", "normal"))
                hit_location = _vec_list(hit_location_vec)
                hit_normal = _vec_list(hit_normal_vec)
                surface_gap = None
                status = "no_surface_hit"
                if _hit_has_blocking(hit) and hit_location is not None:
                    surface_gap = round(float(probe_point[2]) - float(hit_location[2]), 3)
                    if abs(surface_gap) <= surface_tolerance:
                        status = "on_surface"
                        on_surface_count += 1
                    elif surface_gap > surface_tolerance:
                        status = "floating"
                        floating_count += 1
                    else:
                        status = "intersecting_or_below_surface"
                        intersecting_count += 1
                else:
                    no_surface_hit_count += 1

                clearance = _clearance_overlaps(actor)
                if clearance.get("status") == "potential_overlap":
                    potential_overlap_count += 1
                validation = {{
                    "actor": _actor_data(actor, include_bounds=True, center=center),
                    "status": status,
                    "surface_gap": surface_gap,
                    "surface_tolerance": surface_tolerance,
                    "probe_location": [round(float(value), 3) for value in probe_point],
                    "trace_start": [round(float(value), 3) for value in start_location],
                    "trace_end": [round(float(value), 3) for value in end_location],
                    "hit_location": hit_location,
                    "hit_normal": hit_normal,
                    "hit_actor": _actor_descriptor(_hit_actor(hit_result)),
                    "clearance": clearance,
                }}
                validations.append(validation)

            aggregate_bounds = _aggregate_bounds(target_actors)
            evidence_follow_up = []
            if include_evidence_handoff:
                focus_center = None
                if isinstance(aggregate_bounds, dict) and aggregate_bounds.get("available"):
                    center_data = aggregate_bounds.get("center") or {{}}
                    focus_center = [
                        float(center_data.get("x", 0.0)),
                        float(center_data.get("y", 0.0)),
                        float(center_data.get("z", 0.0)),
                    ]
                elif target_actors:
                    loc = _actor_location_tuple(target_actors[0])
                    if loc is not None:
                        focus_center = [float(loc[0]), float(loc[1]), float(loc[2])]
                if focus_center is not None:
                    evidence_follow_up.append({{
                        "tool": "focus_viewport",
                        "arguments": {{"location": focus_center, "distance": 1800.0}},
                        "reason": "Frame validated placement actors before screenshot evidence.",
                    }})
                evidence_follow_up.append({{
                    "tool": "viewport_capture_screenshot",
                    "arguments": {{"artifact_name": "spatial_placement_validation", "show_ui": False}},
                    "reason": "Capture post-placement evidence for the validation result.",
                }})

            _result["schema"] = {PLACEMENT_VALIDATION_SCHEMA!r}
            _result["trace_channel"] = trace_channel_name
            _result["surface_tolerance"] = surface_tolerance
            _result["clearance_padding"] = clearance_padding
            _result["matched_actor_count"] = total_target_count
            _result["validated_actor_count"] = len(validations)
            _result["truncated"] = total_target_count > limit
            _result["aggregate_bounds"] = aggregate_bounds
            _result["summary"] = {{
                "on_surface": on_surface_count,
                "floating": floating_count,
                "intersecting_or_below_surface": intersecting_count,
                "no_surface_hit": no_surface_hit_count,
                "potential_overlap": potential_overlap_count,
            }}
            _result["validations"] = validations
            _result["missing_requested_actors"] = missing_requested
            _result["evidence_follow_up"] = evidence_follow_up
            _result["recommended_workflow"] = [
                "Review floating, intersecting_or_below_surface, no_surface_hit, and potential_overlap entries.",
                "Use spatial_surface_probe for candidate corrected locations when surface gaps are unacceptable.",
                "Use viewport evidence follow-ups after human review.",
                "Do not claim native SceneTools placement parity without live UE 5.8 validation.",
            ]
            """
        )
    )


def _asset_placement_code(
    *,
    asset_path: str,
    actor_label: str,
    location: List[float],
    rotation: List[float],
    scale: List[float],
    tags: List[str],
    data_layer_names: List[str],
    fail_on_missing_data_layer: bool,
    select_actor: bool,
    focus_viewport: bool,
) -> str:
    return textwrap.dedent(
        f"""\
        import unreal

        asset_path = {asset_path!r}
        actor_label = {str(actor_label or '').strip()!r}
        location_values = {location!r}
        rotation_values = {rotation!r}
        scale_values = {scale!r}
        tag_values = {tags!r}
        data_layer_names = {data_layer_names!r}
        fail_on_missing_data_layer = {bool(fail_on_missing_data_layer)!r}
        select_actor = {bool(select_actor)!r}
        focus_viewport = {bool(focus_viewport)!r}

        _result["schema"] = {ASSET_PLACEMENT_SCHEMA!r}
        _result["asset_path"] = asset_path
        _result["requested_actor_label"] = actor_label
        _result["requested_tags"] = tag_values
        _result["requested_data_layers"] = data_layer_names
        _result["fail_on_missing_data_layer"] = fail_on_missing_data_layer
        _result["requested_transform"] = {{
            "location": location_values,
            "rotation": rotation_values,
            "scale": scale_values,
        }}
        _result["spawn_attempts"] = []
        _result["applied_tags"] = []
        _result["data_layer_results"] = []

        def _vec_dict(value):
            if value is None:
                return None
            return {{"x": float(value.x), "y": float(value.y), "z": float(value.z)}}

        def _rot_dict(value):
            if value is None:
                return None
            return {{
                "pitch": float(getattr(value, "pitch", 0.0)),
                "yaw": float(getattr(value, "yaw", 0.0)),
                "roll": float(getattr(value, "roll", 0.0)),
            }}

        def _object_path(obj):
            if obj is None:
                return ""
            try:
                return obj.get_path_name()
            except Exception:
                return str(obj)

        def _class_name(obj):
            if obj is None:
                return ""
            try:
                return obj.get_class().get_name()
            except Exception:
                return obj.__class__.__name__

        def _actor_label(actor):
            try:
                label = actor.get_actor_label()
                if label:
                    return str(label)
            except Exception:
                pass
            try:
                return str(actor.get_name())
            except Exception:
                return str(actor)

        def _actor_bounds(actor):
            try:
                try:
                    origin, extent = actor.get_actor_bounds(False, False)
                except TypeError:
                    origin, extent = actor.get_actor_bounds(False)
                return {{
                    "origin": _vec_dict(origin),
                    "extent": _vec_dict(extent),
                    "min": {{
                        "x": float(origin.x) - float(extent.x),
                        "y": float(origin.y) - float(extent.y),
                        "z": float(origin.z) - float(extent.z),
                    }},
                    "max": {{
                        "x": float(origin.x) + float(extent.x),
                        "y": float(origin.y) + float(extent.y),
                        "z": float(origin.z) + float(extent.z),
                    }},
                }}
            except Exception as exc:
                return {{"error": str(exc)}}

        def _actor_tags(actor):
            try:
                raw_tags = list(actor.get_editor_property("tags") or [])
            except Exception:
                raw_tags = list(getattr(actor, "tags", []) or [])
            tags = []
            for tag in raw_tags:
                text = str(tag)
                if text:
                    tags.append(text)
            return tags

        def _actor_data(actor):
            try:
                location = actor.get_actor_location()
            except Exception:
                location = None
            try:
                rotation = actor.get_actor_rotation()
            except Exception:
                rotation = None
            try:
                scale = actor.get_actor_scale3d()
            except Exception:
                scale = None
            return {{
                "label": _actor_label(actor),
                "name": str(actor.get_name()) if hasattr(actor, "get_name") else str(actor),
                "class": _class_name(actor),
                "path": _object_path(actor),
                "location": _vec_dict(location),
                "rotation": _rot_dict(rotation),
                "scale": _vec_dict(scale),
                "tags": _actor_tags(actor),
                "bounds": _actor_bounds(actor),
            }}

        def _get_actor_subsystem():
            subsystem_class = getattr(unreal, "EditorActorSubsystem", None)
            if subsystem_class is None:
                return None
            try:
                return unreal.get_editor_subsystem(subsystem_class)
            except Exception as exc:
                _warnings.append("EditorActorSubsystem is unavailable: " + str(exc))
                return None

        def _try_spawn_from_object(asset, location, rotation):
            actor_subsystem = _get_actor_subsystem()
            if actor_subsystem is not None and hasattr(actor_subsystem, "spawn_actor_from_object"):
                try:
                    actor = actor_subsystem.spawn_actor_from_object(asset, location, rotation)
                    _result["spawn_attempts"].append("EditorActorSubsystem.spawn_actor_from_object")
                    if actor is not None:
                        return actor
                except Exception as exc:
                    _warnings.append("EditorActorSubsystem.spawn_actor_from_object failed: " + str(exc))
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "spawn_actor_from_object"):
                try:
                    actor = editor_level_library.spawn_actor_from_object(asset, location, rotation)
                    _result["spawn_attempts"].append("EditorLevelLibrary.spawn_actor_from_object")
                    if actor is not None:
                        return actor
                except Exception as exc:
                    _warnings.append("EditorLevelLibrary.spawn_actor_from_object failed: " + str(exc))
            return None

        def _try_spawn_from_blueprint_class(asset, location, rotation):
            generated_class = None
            for attr_name in ("generated_class", "GeneratedClass"):
                generated_class = getattr(asset, attr_name, None)
                if generated_class is not None:
                    break
            if generated_class is None:
                try:
                    generated_class = asset.get_editor_property("generated_class")
                except Exception:
                    generated_class = None
            if generated_class is None:
                return None
            actor_subsystem = _get_actor_subsystem()
            if actor_subsystem is not None and hasattr(actor_subsystem, "spawn_actor_from_class"):
                try:
                    actor = actor_subsystem.spawn_actor_from_class(generated_class, location, rotation)
                    _result["spawn_attempts"].append("EditorActorSubsystem.spawn_actor_from_class")
                    if actor is not None:
                        return actor
                except Exception as exc:
                    _warnings.append("EditorActorSubsystem.spawn_actor_from_class failed: " + str(exc))
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "spawn_actor_from_class"):
                try:
                    actor = editor_level_library.spawn_actor_from_class(generated_class, location, rotation)
                    _result["spawn_attempts"].append("EditorLevelLibrary.spawn_actor_from_class")
                    if actor is not None:
                        return actor
                except Exception as exc:
                    _warnings.append("EditorLevelLibrary.spawn_actor_from_class failed: " + str(exc))
            return None

        def _select_actor(actor):
            if not select_actor:
                return False
            actor_subsystem = _get_actor_subsystem()
            if actor_subsystem is not None and hasattr(actor_subsystem, "set_selected_level_actors"):
                try:
                    actor_subsystem.set_selected_level_actors([actor])
                    return True
                except Exception as exc:
                    _warnings.append("EditorActorSubsystem.set_selected_level_actors failed: " + str(exc))
            editor_level_library = getattr(unreal, "EditorLevelLibrary", None)
            if editor_level_library is not None and hasattr(editor_level_library, "set_selected_level_actors"):
                try:
                    editor_level_library.set_selected_level_actors([actor])
                    return True
                except Exception as exc:
                    _warnings.append("EditorLevelLibrary.set_selected_level_actors failed: " + str(exc))
            return False

        def _apply_actor_tags(actor, tags_to_apply):
            if not tags_to_apply:
                return []
            try:
                current_tags = list(actor.get_editor_property("tags") or [])
            except Exception:
                current_tags = list(getattr(actor, "tags", []) or [])

            current_text = set(str(tag) for tag in current_tags)
            name_class = getattr(unreal, "Name", None)
            applied = []
            for tag in tags_to_apply:
                if tag in current_text:
                    applied.append(tag)
                    continue
                try:
                    current_tags.append(name_class(tag) if name_class is not None else tag)
                    current_text.add(tag)
                    applied.append(tag)
                except Exception as exc:
                    _warnings.append("Could not prepare actor tag '" + str(tag) + "': " + str(exc))
            try:
                actor.set_editor_property("tags", current_tags)
            except Exception as exc:
                try:
                    actor.tags = current_tags
                except Exception:
                    _warnings.append("Could not apply actor tags: " + str(exc))
                    return []
            return applied

        def _data_layer_label(layer):
            for method_name in ("get_data_layer_short_name", "get_data_layer_full_name", "get_name", "get_path_name"):
                method = getattr(layer, method_name, None)
                if callable(method):
                    try:
                        value = method()
                        if value:
                            return str(value)
                    except Exception:
                        pass
            for property_name in ("data_layer_short_name", "data_layer_label", "label"):
                try:
                    value = layer.get_editor_property(property_name)
                    if value:
                        return str(value)
                except Exception:
                    pass
            return str(layer)

        def _data_layer_names(layer):
            names = []
            for method_name in ("get_data_layer_short_name", "get_data_layer_full_name", "get_name", "get_path_name"):
                method = getattr(layer, method_name, None)
                if callable(method):
                    try:
                        value = method()
                        if value:
                            names.append(str(value))
                    except Exception:
                        pass
            for property_name in ("data_layer_short_name", "data_layer_label", "label"):
                try:
                    value = layer.get_editor_property(property_name)
                    if value:
                        names.append(str(value))
                except Exception:
                    pass
            return names

        def _data_layer_descriptor(layer):
            if layer is None:
                return None
            return {{
                "label": _data_layer_label(layer),
                "class": _class_name(layer),
                "path": _object_path(layer),
            }}

        def _get_data_layer_subsystem():
            subsystem_class = getattr(unreal, "DataLayerEditorSubsystem", None)
            if subsystem_class is None:
                _warnings.append("DataLayerEditorSubsystem is unavailable; Data Layer assignment was skipped.")
                return None
            try:
                return unreal.get_editor_subsystem(subsystem_class)
            except Exception as exc:
                _warnings.append("DataLayerEditorSubsystem is unavailable: " + str(exc))
                return None

        def _matches_data_layer(layer, requested_name):
            wanted = str(requested_name or "").strip().lower()
            if not wanted:
                return False
            for value in _data_layer_names(layer):
                text = str(value or "").strip()
                if not text:
                    continue
                lowered = text.lower()
                tail = lowered.rsplit("/", 1)[-1].rsplit(".", 1)[-1]
                if lowered == wanted or tail == wanted:
                    return True
            return False

        def _all_data_layers(data_layer_subsystem):
            for method_name in ("get_all_data_layer_instances", "get_all_data_layers"):
                method = getattr(data_layer_subsystem, method_name, None)
                if callable(method):
                    try:
                        return list(method() or [])
                    except Exception as exc:
                        _warnings.append("DataLayerEditorSubsystem." + method_name + " failed: " + str(exc))
            return []

        def _resolve_data_layer(data_layer_subsystem, requested_name):
            name_class = getattr(unreal, "Name", None)
            possible_args = [requested_name]
            if name_class is not None:
                try:
                    possible_args.append(name_class(requested_name))
                except Exception:
                    pass
            for method_name in (
                "get_data_layer_instance",
                "get_data_layer_instance_from_name",
                "get_data_layer_from_name",
                "get_data_layer_from_label",
            ):
                method = getattr(data_layer_subsystem, method_name, None)
                if not callable(method):
                    continue
                for arg in possible_args:
                    try:
                        layer = method(arg)
                        if layer is not None:
                            return layer, "DataLayerEditorSubsystem." + method_name
                    except Exception:
                        pass
            for layer in _all_data_layers(data_layer_subsystem):
                if _matches_data_layer(layer, requested_name):
                    return layer, "DataLayerEditorSubsystem.enumerate"
            return None, ""

        def _assign_actor_to_data_layer(data_layer_subsystem, actor, layer):
            call_specs = [
                ("add_actor_to_data_layer", (actor, layer)),
                ("add_actor_to_data_layer_instance", (actor, layer)),
                ("add_actors_to_data_layer", ([actor], layer)),
                ("add_actors_to_data_layer_instance", ([actor], layer)),
                ("add_actor_to_data_layers", (actor, [layer])),
                ("add_actors_to_data_layers", ([actor], [layer])),
            ]
            for method_name, args in call_specs:
                method = getattr(data_layer_subsystem, method_name, None)
                if not callable(method):
                    continue
                try:
                    outcome = method(*args)
                    if outcome is not False:
                        return True, "DataLayerEditorSubsystem." + method_name
                except Exception as exc:
                    _warnings.append("DataLayerEditorSubsystem." + method_name + " failed: " + str(exc))
            return False, ""

        def _assign_data_layers(actor, requested_layers):
            if not requested_layers:
                return []
            data_layer_subsystem = _get_data_layer_subsystem()
            results = []
            if data_layer_subsystem is None:
                for requested_name in requested_layers:
                    results.append({{"requested": requested_name, "status": "subsystem_unavailable"}})
                    if fail_on_missing_data_layer:
                        _errors.append("DataLayerEditorSubsystem unavailable; could not assign Data Layer: " + requested_name)
                return results

            for requested_name in requested_layers:
                layer, resolve_method = _resolve_data_layer(data_layer_subsystem, requested_name)
                if layer is None:
                    results.append({{"requested": requested_name, "status": "not_found"}})
                    message = "Data Layer not found: " + requested_name
                    if fail_on_missing_data_layer:
                        _errors.append(message)
                    else:
                        _warnings.append(message)
                    continue
                assigned, assign_method = _assign_actor_to_data_layer(data_layer_subsystem, actor, layer)
                result = {{
                    "requested": requested_name,
                    "status": "assigned" if assigned else "assign_failed",
                    "resolve_method": resolve_method,
                    "assign_method": assign_method,
                    "layer": _data_layer_descriptor(layer),
                }}
                results.append(result)
                if not assigned:
                    message = "Could not assign actor to Data Layer: " + requested_name
                    if fail_on_missing_data_layer:
                        _errors.append(message)
                    else:
                        _warnings.append(message)
            return results

        asset = unreal.EditorAssetLibrary.load_asset(asset_path)
        if asset is None:
            _errors.append("Asset could not be loaded: " + asset_path)
        else:
            location = unreal.Vector(float(location_values[0]), float(location_values[1]), float(location_values[2]))
            rotation = unreal.Rotator(float(rotation_values[0]), float(rotation_values[1]), float(rotation_values[2]))
            scale = unreal.Vector(float(scale_values[0]), float(scale_values[1]), float(scale_values[2]))
            actor = _try_spawn_from_object(asset, location, rotation)
            if actor is None:
                actor = _try_spawn_from_blueprint_class(asset, location, rotation)
            if actor is None:
                _errors.append("Could not spawn an actor from asset: " + asset_path)
            else:
                try:
                    actor.set_actor_scale3d(scale)
                except Exception as exc:
                    _warnings.append("Could not apply actor scale: " + str(exc))
                if actor_label:
                    try:
                        actor.set_actor_label(actor_label)
                    except Exception as exc:
                        _warnings.append("Could not apply actor label: " + str(exc))
                applied_tags = _apply_actor_tags(actor, tag_values)
                data_layer_results = _assign_data_layers(actor, data_layer_names)
                selected = _select_actor(actor)
                if focus_viewport:
                    _warnings.append("focus_viewport requested; use spatial_view_context or focus_viewport after placement for explicit camera control.")
                _result["actor"] = _actor_data(actor)
                _result["asset_class"] = _class_name(asset)
                _result["applied_tags"] = applied_tags
                _result["data_layer_results"] = data_layer_results
                _result["selected"] = selected
                _result["placed"] = True
        """
    )


def _environment_coherence_assessment(
    scene_context: Mapping[str, Any],
    design_intent: Mapping[str, Any],
) -> Dict[str, Any]:
    """Evaluate composition constraints without promoting inference to fact."""

    revision = str(scene_context.get("scene_revision") or "").strip()[:128]
    frame = scene_context.get("coordinate_frame")
    if frame is None:
        frame = {}
    if not isinstance(frame, dict):
        raise ValueError("scene_context_json.coordinate_frame must be an object")

    def object_list(owner: Mapping[str, Any], key: str, maximum: int) -> List[Dict[str, Any]]:
        value = owner.get(key, [])
        if value is None:
            return []
        if not isinstance(value, list) or len(value) > maximum:
            raise ValueError(f"{key} must be an array with at most {maximum} items")
        output: List[Dict[str, Any]] = []
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise ValueError(f"{key}[{index}] must be an object")
            output.append(dict(item))
        return output

    entities = object_list(scene_context, "entities", 1000)
    circulation = object_list(scene_context, "circulation_paths", 256)
    sightlines = object_list(scene_context, "sightlines", 256)
    ecology = object_list(scene_context, "ecological_constraints", 256)
    intended_zones = object_list(design_intent, "functional_zones", 128)
    scale_references = object_list(design_intent, "scale_references", 128)

    entities_by_id: Dict[str, Dict[str, Any]] = {}
    duplicate_ids: List[str] = []
    evidence_issues: List[str] = []
    allowed_evidence = {"observed", "calculated", "inferred"}
    for index, entity in enumerate(entities):
        stable_id = str(entity.get("stable_id") or entity.get("id") or "").strip()[:256]
        if not stable_id:
            evidence_issues.append(f"entities[{index}] has no stable ID")
            continue
        if stable_id in entities_by_id:
            duplicate_ids.append(stable_id)
            continue
        entities_by_id[stable_id] = entity
        evidence_status = str(entity.get("evidence_status") or "").strip().lower()
        if evidence_status not in allowed_evidence:
            evidence_issues.append(f"{stable_id} has no valid evidence_status")
        confidence = entity.get("confidence")
        if confidence is not None and (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(float(confidence))
            or float(confidence) < 0.0
            or float(confidence) > 1.0
        ):
            evidence_issues.append(f"{stable_id} has invalid confidence")

    gates: List[Dict[str, Any]] = []

    def gate(
        gate_id: str,
        status: str,
        *,
        hard: bool,
        blockers: Sequence[str],
        measurement: Any,
        target: Any,
        evidence_class: str,
    ) -> None:
        gates.append({
            "gate_id": gate_id,
            "status": status,
            "hard_constraint": hard,
            "blockers": list(blockers),
            "measurement": measurement,
            "target": target,
            "evidence_class": evidence_class,
        })

    frame_missing = [
        key for key in ("units", "handedness", "up_axis")
        if not str(frame.get(key) or "").strip()
    ]
    gate(
        "revision_and_coordinate_frame",
        "pass" if revision and not frame_missing else "unresolved",
        hard=True,
        blockers=([] if revision else ["scene_revision missing"]) + [
            f"coordinate_frame.{key} missing" for key in frame_missing
        ],
        measurement={"scene_revision": revision, "coordinate_frame": frame},
        target="one revision-bound explicit coordinate frame",
        evidence_class="observed-semantic-state",
    )

    identity_blockers = [f"duplicate stable ID: {value}" for value in sorted(set(duplicate_ids))]
    identity_blockers.extend(evidence_issues)
    gate(
        "stable_identity_and_epistemic_status",
        "pass" if entities and not identity_blockers else ("fail" if identity_blockers else "unresolved"),
        hard=True,
        blockers=identity_blockers or (["no entities supplied"] if not entities else []),
        measurement={"entity_count": len(entities), "stable_entity_count": len(entities_by_id)},
        target="every entity has a unique stable ID and observed/calculated/inferred status",
        evidence_class="observed-semantic-state",
    )

    unsupported: List[str] = []
    gravity_count = 0
    for stable_id, entity in entities_by_id.items():
        if not bool(entity.get("gravity_bound", False)):
            continue
        gravity_count += 1
        support_id = str(entity.get("support_id") or "").strip()
        suspended = bool(entity.get("intentionally_suspended", False))
        if not suspended and (not support_id or support_id not in entities_by_id):
            unsupported.append(stable_id)
    gate(
        "support_and_contact",
        "pass" if gravity_count and not unsupported else ("fail" if unsupported else "unresolved"),
        hard=True,
        blockers=[f"unsupported gravity-bound entity: {value}" for value in unsupported],
        measurement={"gravity_bound_count": gravity_count, "unsupported_ids": unsupported},
        target="every gravity-bound entity has observed support or intentional suspension",
        evidence_class="calculated-from-observed-geometry",
    )

    circulation_blockers: List[str] = []
    circulation_unresolved: List[str] = []
    for index, path in enumerate(circulation):
        path_id = str(path.get("stable_id") or path.get("id") or f"path-{index}")[:128]
        blocked_by = [str(item) for item in path.get("blocked_by_ids", [])] if isinstance(path.get("blocked_by_ids", []), list) else []
        measured = path.get("measured_clearance_m")
        required = path.get("required_clearance_m")
        if blocked_by:
            circulation_blockers.append(f"{path_id} blocked by {', '.join(blocked_by[:16])}")
        if not isinstance(measured, (int, float)) or not isinstance(required, (int, float)):
            circulation_unresolved.append(f"{path_id} lacks measured/required clearance")
        elif float(measured) < float(required):
            circulation_blockers.append(f"{path_id} clearance {float(measured):.3f}m < {float(required):.3f}m")
    gate(
        "circulation_and_clearance",
        "fail" if circulation_blockers else ("unresolved" if not circulation or circulation_unresolved else "pass"),
        hard=True,
        blockers=circulation_blockers + circulation_unresolved,
        measurement={"path_count": len(circulation)},
        target="all required paths are connected, unblocked, and meet measured clearance",
        evidence_class="calculated-from-observed-geometry",
    )

    required_landmarks = [
        str(value).strip() for value in design_intent.get("primary_landmark_ids", [])
        if str(value).strip()
    ] if isinstance(design_intent.get("primary_landmark_ids", []), list) else []
    missing_landmarks = [value for value in required_landmarks if value not in entities_by_id]
    required_sightline_targets = set(required_landmarks)
    visible_targets = {
        str(line.get("target_id") or "").strip()
        for line in sightlines
        if bool(line.get("visible", False)) and not line.get("occluder_ids")
    }
    hidden_targets = sorted(required_sightline_targets - visible_targets)
    gate(
        "landmark_and_sightline_hierarchy",
        "fail" if missing_landmarks or hidden_targets else ("pass" if required_landmarks else "unresolved"),
        hard=False,
        blockers=[f"missing landmark: {value}" for value in missing_landmarks]
        + [f"required landmark lacks a clear sightline: {value}" for value in hidden_targets],
        measurement={"required_landmarks": required_landmarks, "clear_targets": sorted(visible_targets)},
        target="primary landmarks exist and required approach/review sightlines remain readable",
        evidence_class="calculated-plus-design-intent",
    )

    zone_blockers: List[str] = []
    for index, zone in enumerate(intended_zones):
        zone_id = str(zone.get("id") or zone.get("zone_id") or f"zone-{index}").strip()[:128]
        members = [
            entity for entity in entities_by_id.values()
            if str(entity.get("zone_id") or "").strip() == zone_id
        ]
        required_roles = {
            str(value).strip().lower() for value in zone.get("required_roles", [])
            if str(value).strip()
        } if isinstance(zone.get("required_roles", []), list) else set()
        present_roles = {str(entity.get("semantic_role") or "").strip().lower() for entity in members}
        for role in sorted(required_roles - present_roles):
            zone_blockers.append(f"{zone_id} missing required role: {role}")
        minimum = zone.get("minimum_entity_count", 0)
        if isinstance(minimum, int) and len(members) < minimum:
            zone_blockers.append(f"{zone_id} has {len(members)} entities; minimum is {minimum}")
    gate(
        "functional_zones_and_density",
        "fail" if zone_blockers else ("pass" if intended_zones else "unresolved"),
        hard=False,
        blockers=zone_blockers,
        measurement={"intended_zone_count": len(intended_zones)},
        target="each authored zone contains its required roles without accidental over/under-population",
        evidence_class="observed-state-plus-design-intent",
    )

    allowed_families = {
        str(value).strip().lower() for value in design_intent.get("allowed_material_families", [])
        if str(value).strip()
    } if isinstance(design_intent.get("allowed_material_families", []), list) else set()
    style_outliers = sorted(
        stable_id for stable_id, entity in entities_by_id.items()
        if allowed_families
        and str(entity.get("material_family") or "").strip().lower() not in allowed_families
        and not bool(entity.get("intentional_style_exception", False))
    )
    gate(
        "style_and_material_family",
        "fail" if style_outliers else ("pass" if allowed_families else "unresolved"),
        hard=False,
        blockers=[f"unexplained material-family outlier: {value}" for value in style_outliers],
        measurement={"allowed_material_families": sorted(allowed_families)},
        target="coherent material/style families with explicit authored exceptions",
        evidence_class="observed-state-plus-design-intent",
    )

    ecological_blockers: List[str] = []
    ecological_unresolved: List[str] = []
    for index, rule in enumerate(ecology):
        rule_id = str(rule.get("rule_id") or rule.get("id") or f"ecology-{index}")[:128]
        status = str(rule.get("status") or "unresolved").strip().lower()
        violations = rule.get("violation_ids", [])
        violation_ids = [str(value) for value in violations[:64]] if isinstance(violations, list) else []
        if status == "fail" or violation_ids:
            ecological_blockers.append(f"{rule_id}: {', '.join(violation_ids) or 'failed'}")
        elif status != "pass":
            ecological_unresolved.append(f"{rule_id} unresolved")
    gate(
        "ecological_and_contextual_coherence",
        "fail" if ecological_blockers else ("pass" if ecology and not ecological_unresolved else "unresolved"),
        hard=False,
        blockers=ecological_blockers + ecological_unresolved,
        measurement={"rule_count": len(ecology)},
        target="terrain, vegetation, wear, exposure, and prop context follow declared causal rules",
        evidence_class="calculated-plus-design-intent",
    )

    scale_blockers: List[str] = []
    for index, reference in enumerate(scale_references):
        entity_id = str(reference.get("entity_id") or "").strip()
        entity = entities_by_id.get(entity_id)
        if not entity:
            scale_blockers.append(f"scale reference {index} missing entity: {entity_id or '<empty>'}")
            continue
        size = entity.get("size_m")
        if not isinstance(size, list) or len(size) != 3 or not all(isinstance(value, (int, float)) for value in size):
            scale_blockers.append(f"{entity_id} lacks measured size_m")
            continue
        measured_height = float(size[2])
        minimum = reference.get("minimum_height_m")
        maximum = reference.get("maximum_height_m")
        if isinstance(minimum, (int, float)) and measured_height < float(minimum):
            scale_blockers.append(f"{entity_id} height {measured_height:.3f}m below {float(minimum):.3f}m")
        if isinstance(maximum, (int, float)) and measured_height > float(maximum):
            scale_blockers.append(f"{entity_id} height {measured_height:.3f}m above {float(maximum):.3f}m")
    gate(
        "physical_scale_cues",
        "fail" if scale_blockers else ("pass" if scale_references else "unresolved"),
        hard=False,
        blockers=scale_blockers,
        measurement={"scale_reference_count": len(scale_references)},
        target="declared human/vehicle/architectural scale references stay inside measured ranges",
        evidence_class="calculated-from-observed-geometry",
    )

    hard_failures = [item["gate_id"] for item in gates if item["hard_constraint"] and item["status"] == "fail"]
    hard_unresolved = [item["gate_id"] for item in gates if item["hard_constraint"] and item["status"] == "unresolved"]
    soft_failures = [item["gate_id"] for item in gates if not item["hard_constraint"] and item["status"] == "fail"]
    unresolved = [item["gate_id"] for item in gates if item["status"] == "unresolved"]
    passing = sum(1 for item in gates if item["status"] == "pass")
    advisory_score = round(100.0 * passing / len(gates), 3) if gates else 0.0
    readiness = "blocked" if hard_failures else ("needs-review" if hard_unresolved or soft_failures or unresolved else "ready")

    return {
        "schema": ENVIRONMENT_COHERENCE_SCHEMA,
        "scene_revision": revision,
        "readiness": readiness,
        "advisory_coherence_score": advisory_score,
        "score_warning": "Advisory only; hard failures and unresolved evidence cannot be averaged away.",
        "gates": gates,
        "hard_failures": hard_failures,
        "hard_unresolved": hard_unresolved,
        "soft_failures": soft_failures,
        "unresolved": unresolved,
        "next_actions": [
            f"Resolve {gate_id}: " + "; ".join(next(item["blockers"] for item in gates if item["gate_id"] == gate_id)[:4])
            for gate_id in hard_failures + hard_unresolved + soft_failures + unresolved
        ],
        "knowledge_basis": [
            {"principle": "typed entity-relation graph", "source": "Handbook of Geospatial Artificial Intelligence, PDF p. 84"},
            {"principle": "support, interposition, scale, viewpoint, and scene relations", "source": "Representations and Techniques for 3D Object Recognition and Scene Interpretation, PDF pp. 29, 87, 123, 138-139"},
            {"principle": "partitioned world, foliage, collision, and regional budgets", "source": "Building Open World Landscapes with Unreal Engine 5, EPUB units 4, 11, 13"},
            {"principle": "exact editor, viewport, asset, and sequence context", "source": "Virtual Filmmaking with Unreal Engine 5, PDF pp. 298, 358"},
        ],
        "epistemic_policy": "Observed, calculated, and inferred facts remain distinct; this assessment grants no mutation authority.",
    }


def register_spatial_awareness_tools(mcp: ToolRegistrationSurface) -> None:
    @mcp.tool()
    def spatial_scene_overview(
        ctx: Context,
        include_hidden: bool = False,
        class_filter: str = "",
        tag_filter: str = "",
        limit: int = 200,
        include_actor_samples: bool = True,
        local_actor_query: str = "",
    ) -> str:
        """Summarize live level actors and resolve explicit local content bounds.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        The optional local_actor_query establishes a read-only local scope over
        observed physical-content actor labels, names, classes, paths, tags, or
        asset paths. Selection takes precedence. Without selection, a matching
        explicit query, or exactly one authored Ghost.RoomBounds actor, local
        bounds fail closed as ambiguous.

        Example:
            spatial_scene_overview(local_actor_query="Enclave", limit=50)"""
        t0 = time.monotonic()
        safe_limit = _bounded_limit(limit, default=200, maximum=1000)
        clean_local_actor_query = str(local_actor_query or "").strip()
        inputs = {
            "include_hidden": include_hidden,
            "class_filter": class_filter,
            "tag_filter": tag_filter,
            "limit": safe_limit,
            "include_actor_samples": include_actor_samples,
            "local_actor_query": clean_local_actor_query,
        }
        if len(clean_local_actor_query) > 256:
            message = "local_actor_query must be 256 characters or fewer"
            return _local_result(
                success=False,
                stage="spatial_scene_overview",
                tool="spatial_scene_overview",
                message=message,
                inputs=inputs,
                errors=[message],
                t0=t0,
            )
        code = _scene_overview_code(
            include_hidden=include_hidden,
            class_filter=class_filter,
            tag_filter=tag_filter,
            limit=safe_limit,
            include_actor_samples=include_actor_samples,
            local_actor_query=clean_local_actor_query,
        )
        result = _exec_structured(code, "spatial_scene_overview")
        return _json_result("spatial_scene_overview", "spatial_scene_overview", inputs, result, t0, SCENE_OVERVIEW_SCHEMA)

    @mcp.tool()
    def spatial_analyze_room(
        ctx: Context,
        room_type: str = "apartment",
        actor_query: str = "",
        class_filter: str = "",
        tag_filter: str = "",
        include_hidden: bool = False,
        prefer_selected: bool = True,
        clearance_padding: float = 90.0,
        min_walkway_width: float = 90.0,
        limit: int = 200,
    ) -> str:
        """Infer room dimensions, surfaces, zones, and clearance risks from live actors.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This read-only analysis turns selected or filtered level actors into a
        planner-ready room model for interior composition, surface probing, and
        validation. It uses bounds/name/tag heuristics and does not mutate the
        Unreal Editor scene.

        Example:
            spatial_analyze_room(room_type="apartment", actor_query="Apartment")"""
        t0 = time.monotonic()
        safe_limit = _bounded_limit(limit, default=200, maximum=1000)
        inputs = {
            "room_type": room_type,
            "actor_query": actor_query,
            "class_filter": class_filter,
            "tag_filter": tag_filter,
            "include_hidden": include_hidden,
            "prefer_selected": prefer_selected,
            "clearance_padding": clearance_padding,
            "min_walkway_width": min_walkway_width,
            "limit": safe_limit,
        }
        try:
            clean_room_type = _clean_room_type(room_type)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_analyze_room",
                tool="spatial_analyze_room",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        safe_clearance_padding = _float_value(clearance_padding, default=90.0, minimum=0.0)
        safe_min_walkway_width = _float_value(min_walkway_width, default=90.0, minimum=0.0)
        inputs.update({
            "room_type": clean_room_type,
            "clearance_padding": safe_clearance_padding,
            "min_walkway_width": safe_min_walkway_width,
        })
        code = _room_analysis_code(
            room_type=clean_room_type,
            actor_query=actor_query,
            class_filter=class_filter,
            tag_filter=tag_filter,
            include_hidden=include_hidden,
            prefer_selected=prefer_selected,
            clearance_padding=safe_clearance_padding,
            min_walkway_width=safe_min_walkway_width,
            limit=safe_limit,
        )
        result = _exec_structured(code, "spatial_analyze_room")
        return _json_result("spatial_analyze_room", "spatial_analyze_room", inputs, result, t0, ROOM_ANALYSIS_SCHEMA)

    @mcp.tool()
    def spatial_plan_room_bounds_designation(
        ctx: Context,
        room_id: str = "room_01",
        room_type: str = "apartment",
        room_dimensions: Optional[List[float]] = None,
        room_origin: Optional[List[float]] = None,
        zone_names: Optional[List[str]] = None,
        include_opening_markers: bool = True,
        include_surface_markers: bool = True,
        include_path_markers: bool = True,
        limit: int = 16,
    ) -> str:
        """Plan the editor tags/volumes that make room bounds authoritative.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local/read-only planner returns the Ghost room-bounds designation
        contract: a RoomBounds volume, optional Zone/Openings/Path/Surface
        markers, shared room id tags, and handoffs back into live room analysis.
        It does not mutate Unreal Editor state.

        Example:
            spatial_plan_room_bounds_designation(room_id="apartment_01", zone_names=["entry", "kitchen", "living", "bedroom"])"""
        t0 = time.monotonic()
        inputs = {
            "room_id": room_id,
            "room_type": room_type,
            "room_dimensions": room_dimensions or [650.0, 500.0, 280.0],
            "room_origin": room_origin or [0.0, 0.0, 0.0],
            "zone_names": zone_names or [],
            "include_opening_markers": include_opening_markers,
            "include_surface_markers": include_surface_markers,
            "include_path_markers": include_path_markers,
            "limit": limit,
        }
        try:
            clean_room_type = _clean_room_type(room_type)
            clean_dimensions = _room_dimensions(room_dimensions)
            clean_origin = _vector3(room_origin, "room_origin") or [0.0, 0.0, 0.0]
            clean_zone_names = _string_list(zone_names, "zone_names", maximum=64)
            safe_limit = _bounded_limit(limit, default=16, maximum=64)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_plan_room_bounds_designation",
                tool="spatial_plan_room_bounds_designation",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "room_type": clean_room_type,
            "room_dimensions": clean_dimensions,
            "room_origin": clean_origin,
            "zone_names": clean_zone_names,
            "limit": safe_limit,
        })
        plan = _plan_room_bounds_designation(
            room_id=room_id,
            room_type=clean_room_type,
            room_dimensions=clean_dimensions,
            room_origin=clean_origin,
            zone_names=clean_zone_names,
            include_opening_markers=bool(include_opening_markers),
            include_surface_markers=bool(include_surface_markers),
            include_path_markers=bool(include_path_markers),
            limit=safe_limit,
        )
        return _local_result(
            success=True,
            stage="spatial_plan_room_bounds_designation",
            tool="spatial_plan_room_bounds_designation",
            message="Planned Ghost room-bounds designation tags, volumes, and analysis handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_infer_functional_zones(
        ctx: Context,
        room_analysis_json: str = "",
        detected_items_json: str = "",
        composition_plan_json: str = "",
        room_type: str = "apartment",
        room_dimensions: Optional[List[float]] = None,
        room_origin: Optional[List[float]] = None,
        requested_zones: Optional[List[str]] = None,
        min_zone_size_cm: float = 140.0,
        include_updated_room_analysis: bool = True,
        limit: int = 16,
    ) -> str:
        """Infer usable functional zones for an interior worldbuilding plan.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local/read-only planner consumes room analysis, screenshot
        detections, and/or an existing composition to infer kitchen, living,
        bedroom, entry, hallway, bathroom, and utility regions before prop
        generation or placement. It does not mutate Unreal Editor state.

        Example:
            spatial_infer_functional_zones(room_analysis_json="<room analysis>", requested_zones=["kitchen", "living"])"""
        t0 = time.monotonic()
        inputs = {
            "room_analysis_json": room_analysis_json,
            "detected_items_json": detected_items_json,
            "composition_plan_json": composition_plan_json,
            "room_type": room_type,
            "room_dimensions": room_dimensions or [650.0, 500.0, 280.0],
            "room_origin": room_origin or [0.0, 0.0, 0.0],
            "requested_zones": requested_zones or [],
            "min_zone_size_cm": min_zone_size_cm,
            "include_updated_room_analysis": include_updated_room_analysis,
            "limit": limit,
        }
        try:
            safe_limit = _bounded_limit(limit, default=16, maximum=64)
            clean_room_analysis = _room_analysis_from_json(room_analysis_json)
            clean_detected_items = _detected_items_from_json(detected_items_json, maximum=128)
            clean_composition_plan = _composition_like_from_json(composition_plan_json) if str(composition_plan_json or "").strip() else {}
            composition_room = clean_composition_plan.get("room") if isinstance(clean_composition_plan.get("room"), Mapping) else {}
            room_type_source = (
                clean_room_analysis.get("room_type")
                or composition_room.get("type")
                or room_type
            )
            clean_room_type = _clean_room_type(str(room_type_source or "apartment"))
            clean_dimensions = (
                list(clean_room_analysis.get("room_dimensions") or [])
                if clean_room_analysis
                else _vector3(composition_room.get("dimensions_cm"), "composition_plan_json.room.dimensions_cm") if composition_room.get("dimensions_cm") is not None
                else _room_dimensions(room_dimensions)
            )
            clean_origin = (
                list(clean_room_analysis.get("room_origin") or [])
                if clean_room_analysis
                else _vector3(composition_room.get("origin"), "composition_plan_json.room.origin") if composition_room.get("origin") is not None
                else (_vector3(room_origin, "room_origin") or [0.0, 0.0, 0.0])
            )
            clean_requested_zones = _string_list(requested_zones, "requested_zones", maximum=16)
            safe_min_zone_size = _float_value(min_zone_size_cm, default=140.0, minimum=60.0)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_infer_functional_zones",
                tool="spatial_infer_functional_zones",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "room_type": clean_room_type,
            "room_dimensions": clean_dimensions,
            "room_origin": clean_origin,
            "room_analysis_applied": bool(clean_room_analysis),
            "detected_item_count": len(clean_detected_items),
            "composition_plan_applied": bool(clean_composition_plan),
            "requested_zones": clean_requested_zones,
            "min_zone_size_cm": safe_min_zone_size,
            "limit": safe_limit,
        })
        plan = _plan_functional_zones(
            room_type=clean_room_type,
            room_dimensions=clean_dimensions,
            room_origin=clean_origin,
            room_analysis=clean_room_analysis,
            detected_items=clean_detected_items,
            composition_plan=clean_composition_plan,
            requested_zones=clean_requested_zones,
            min_zone_size_cm=safe_min_zone_size,
            include_updated_room_analysis=bool(include_updated_room_analysis),
            limit=safe_limit,
        )
        return _local_result(
            success=True,
            stage="spatial_infer_functional_zones",
            tool="spatial_infer_functional_zones",
            message="Inferred functional interior zones for composition planning.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_plan_interior_prop_program(
        ctx: Context,
        room_analysis_json: str = "",
        functional_zone_plan_json: str = "",
        detected_items_json: str = "",
        room_type: str = "apartment",
        room_dimensions: Optional[List[float]] = None,
        room_origin: Optional[List[float]] = None,
        style: str = "lived-in realistic",
        intent: str = "",
        requested_zones: Optional[List[str]] = None,
        required_props: Optional[List[str]] = None,
        omit_props: Optional[List[str]] = None,
        existing_asset_paths: Optional[List[str]] = None,
        include_architectural_fill: bool = True,
        include_zone_recommendations: bool = True,
        limit: int = 48,
    ) -> str:
        """Plan a zone-aware interior prop program before composition.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local/read-only planner turns room analysis, functional zones,
        screenshot detections, user-required props, and known assets into a
        per-zone fixture/furniture/clutter/fill program. It does not mutate
        Unreal or submit Tripo jobs.

        Example:
            spatial_plan_interior_prop_program(functional_zone_plan_json="<zones>", required_props=["fridge", "stove"])"""
        t0 = time.monotonic()
        inputs = {
            "room_analysis_json": room_analysis_json,
            "functional_zone_plan_json": functional_zone_plan_json,
            "detected_items_json": detected_items_json,
            "room_type": room_type,
            "room_dimensions": room_dimensions or [650.0, 500.0, 280.0],
            "room_origin": room_origin or [0.0, 0.0, 0.0],
            "style": style,
            "intent": intent,
            "requested_zones": requested_zones or [],
            "required_props": required_props or [],
            "omit_props": omit_props or [],
            "existing_asset_paths": existing_asset_paths or [],
            "include_architectural_fill": include_architectural_fill,
            "include_zone_recommendations": include_zone_recommendations,
            "limit": limit,
        }
        safe_limit = _bounded_limit(limit, default=48, maximum=128)
        try:
            clean_room_analysis = _room_analysis_from_json(room_analysis_json)
            clean_functional_zone_plan = _functional_zone_plan_from_json(functional_zone_plan_json)
            room_type_source = (
                clean_functional_zone_plan.get("room", {}).get("type")
                if clean_functional_zone_plan and isinstance(clean_functional_zone_plan.get("room"), Mapping)
                else clean_room_analysis.get("room_type")
                if clean_room_analysis and str(room_type or "apartment").strip().lower().replace(" ", "_").replace("-", "_") == "apartment"
                else room_type
            )
            clean_room_type = _clean_room_type(str(room_type_source or "apartment"))
            zone_room = clean_functional_zone_plan.get("room") if isinstance(clean_functional_zone_plan.get("room"), Mapping) else {}
            clean_dimensions = (
                _vector3(zone_room.get("dimensions_cm"), "functional_zone_plan_json.room.dimensions_cm")
                if zone_room.get("dimensions_cm") is not None
                else None
            ) or (list(clean_room_analysis["room_dimensions"]) if clean_room_analysis else _room_dimensions(room_dimensions))
            clean_origin = (
                _vector3(zone_room.get("origin"), "functional_zone_plan_json.room.origin")
                if zone_room.get("origin") is not None
                else None
            ) or (list(clean_room_analysis["room_origin"]) if clean_room_analysis else (_vector3(room_origin, "room_origin") or [0.0, 0.0, 0.0]))
            clean_detected_items = _detected_items_from_json(detected_items_json, maximum=safe_limit)
            clean_requested_zones = _string_list(requested_zones, "requested_zones", maximum=16)
            clean_required_props = _string_list(required_props, "required_props", maximum=safe_limit)
            clean_omit_props = _string_list(omit_props, "omit_props", maximum=safe_limit)
            clean_existing_asset_paths = [
                _clean_asset_path(path)
                for path in _string_list(existing_asset_paths, "existing_asset_paths", maximum=256)
            ]
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_plan_interior_prop_program",
                tool="spatial_plan_interior_prop_program",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        generated_zone_plan = False
        if not clean_functional_zone_plan:
            clean_functional_zone_plan = _plan_functional_zones(
                room_type=clean_room_type,
                room_dimensions=clean_dimensions,
                room_origin=clean_origin,
                room_analysis=clean_room_analysis,
                detected_items=clean_detected_items,
                composition_plan={},
                requested_zones=clean_requested_zones,
                min_zone_size_cm=120.0,
                include_updated_room_analysis=True,
                limit=16,
            )
            generated_zone_plan = True

        inputs.update({
            "room_type": clean_room_type,
            "room_dimensions": clean_dimensions,
            "room_origin": clean_origin,
            "room_analysis_applied": bool(clean_room_analysis),
            "functional_zone_plan_applied": bool(functional_zone_plan_json),
            "functional_zone_plan_generated": generated_zone_plan,
            "detected_item_count": len(clean_detected_items),
            "requested_zones": clean_requested_zones,
            "required_props": clean_required_props,
            "omit_props": clean_omit_props,
            "existing_asset_paths": clean_existing_asset_paths,
            "include_architectural_fill": bool(include_architectural_fill),
            "include_zone_recommendations": bool(include_zone_recommendations),
            "limit": safe_limit,
        })
        plan = _plan_interior_prop_program(
            room_type=clean_room_type,
            room_dimensions=clean_dimensions,
            room_origin=clean_origin,
            functional_zone_plan=clean_functional_zone_plan,
            room_analysis=clean_room_analysis,
            detected_items=clean_detected_items,
            requested_zones=clean_requested_zones,
            required_props=clean_required_props,
            omit_props=clean_omit_props,
            existing_asset_paths=clean_existing_asset_paths,
            style=str(style or "").strip(),
            intent=str(intent or "").strip(),
            include_architectural_fill=bool(include_architectural_fill),
            limit=safe_limit,
            include_zone_recommendations=bool(include_zone_recommendations),
        )
        return _local_result(
            success=True,
            stage="spatial_plan_interior_prop_program",
            tool="spatial_plan_interior_prop_program",
            message="Planned zone-aware interior prop program for composition, asset resolution, and guarded Tripo review.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_query_actors(
        ctx: Context,
        query: str = "",
        class_filter: str = "",
        tag_filter: str = "",
        center: Optional[List[float]] = None,
        radius: float = 0.0,
        box_min: Optional[List[float]] = None,
        box_max: Optional[List[float]] = None,
        include_hidden: bool = False,
        include_components: bool = False,
        limit: int = 100,
    ) -> str:
        """Find actors by name, class, tag, radius, and/or bounding box.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        Example:
            spatial_query_actors(query="door", center=[0, 0, 0], radius=2000)"""
        t0 = time.monotonic()
        inputs = {
            "query": query,
            "class_filter": class_filter,
            "tag_filter": tag_filter,
            "center": center,
            "radius": radius,
            "box_min": box_min,
            "box_max": box_max,
            "include_hidden": include_hidden,
            "include_components": include_components,
            "limit": limit,
        }
        try:
            clean_center = _vector3(center, "center")
            clean_box_min = _vector3(box_min, "box_min")
            clean_box_max = _vector3(box_max, "box_max")
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_query_actors",
                tool="spatial_query_actors",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        safe_limit = _bounded_limit(limit, default=100, maximum=1000)
        safe_radius = _float_value(radius, default=0.0, minimum=0.0)
        inputs.update({"center": clean_center, "box_min": clean_box_min, "box_max": clean_box_max, "limit": safe_limit, "radius": safe_radius})
        code = _query_actors_code(
            query=query,
            class_filter=class_filter,
            tag_filter=tag_filter,
            center=clean_center,
            radius=safe_radius,
            box_min=clean_box_min,
            box_max=clean_box_max,
            include_hidden=include_hidden,
            include_components=include_components,
            limit=safe_limit,
        )
        result = _exec_structured(code, "spatial_query_actors")
        return _json_result("spatial_query_actors", "spatial_query_actors", inputs, result, t0, SPATIAL_QUERY_SCHEMA)

    @mcp.tool()
    def spatial_describe_actor(
        ctx: Context,
        actor: str,
        include_components: bool = True,
        include_bounds: bool = True,
        nearby_radius: float = 1000.0,
        nearby_limit: int = 25,
    ) -> str:
        """Describe one actor's transform, bounds, tags, components, and neighbors.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        Example:
            spatial_describe_actor(actor="BP_PlayerStart")"""
        t0 = time.monotonic()
        safe_actor = str(actor or "").strip()
        safe_radius = _float_value(nearby_radius, default=1000.0, minimum=0.0)
        safe_limit = _bounded_limit(nearby_limit, default=25, maximum=250)
        inputs = {
            "actor": actor,
            "include_components": include_components,
            "include_bounds": include_bounds,
            "nearby_radius": safe_radius,
            "nearby_limit": safe_limit,
        }
        if not safe_actor:
            return _local_result(
                success=False,
                stage="spatial_describe_actor",
                tool="spatial_describe_actor",
                message="actor is required",
                inputs=inputs,
                errors=["actor is required"],
                t0=t0,
            )
        code = _describe_actor_code(
            actor=safe_actor,
            include_components=include_components,
            include_bounds=include_bounds,
            nearby_radius=safe_radius,
            nearby_limit=safe_limit,
        )
        result = _exec_structured(code, "spatial_describe_actor")
        return _json_result("spatial_describe_actor", "spatial_describe_actor", inputs, result, t0, ACTOR_DESCRIPTOR_SCHEMA)

    @mcp.tool()
    def spatial_proximity_map(
        ctx: Context,
        actor: str = "",
        center: Optional[List[float]] = None,
        radius: float = 1000.0,
        class_filter: str = "",
        tag_filter: str = "",
        include_hidden: bool = False,
        limit: int = 50,
    ) -> str:
        """Map actors near an actor, the selected actor, or a world-space point.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        Example:
            spatial_proximity_map(actor="SM_CityBlock_A", radius=3000)"""
        t0 = time.monotonic()
        inputs = {
            "actor": actor,
            "center": center,
            "radius": radius,
            "class_filter": class_filter,
            "tag_filter": tag_filter,
            "include_hidden": include_hidden,
            "limit": limit,
        }
        try:
            clean_center = _vector3(center, "center")
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_proximity_map",
                tool="spatial_proximity_map",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        safe_limit = _bounded_limit(limit, default=50, maximum=500)
        safe_radius = _float_value(radius, default=1000.0, minimum=0.0)
        inputs.update({"center": clean_center, "radius": safe_radius, "limit": safe_limit})
        code = _proximity_map_code(
            actor=actor,
            center=clean_center,
            radius=safe_radius,
            class_filter=class_filter,
            tag_filter=tag_filter,
            include_hidden=include_hidden,
            limit=safe_limit,
        )
        result = _exec_structured(code, "spatial_proximity_map")
        return _json_result("spatial_proximity_map", "spatial_proximity_map", inputs, result, t0, PROXIMITY_MAP_SCHEMA)

    @mcp.tool()
    def spatial_view_context(
        ctx: Context,
        include_nearby: bool = True,
        nearby_radius: float = 3000.0,
        limit: int = 40,
    ) -> str:
        """Read viewport camera context, selected actors, and nearby actors.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        Example:
            spatial_view_context(nearby_radius=5000)"""
        t0 = time.monotonic()
        safe_limit = _bounded_limit(limit, default=40, maximum=250)
        safe_radius = _float_value(nearby_radius, default=3000.0, minimum=0.0)
        inputs = {"include_nearby": include_nearby, "nearby_radius": safe_radius, "limit": safe_limit}
        code = _view_context_code(include_nearby=include_nearby, nearby_radius=safe_radius, limit=safe_limit)
        result = _exec_structured(code, "spatial_view_context")
        return _json_result("spatial_view_context", "spatial_view_context", inputs, result, t0, VIEW_CONTEXT_SCHEMA)

    @mcp.tool()
    def spatial_surface_probe(
        ctx: Context,
        points: Optional[List[List[float]]] = None,
        center: Optional[List[float]] = None,
        grid_count: int = 1,
        grid_spacing: float = 300.0,
        trace_up: float = 5000.0,
        trace_down: float = 10000.0,
        trace_channel: str = "visibility",
        ignore_actor_query: str = "",
        placement_offset: float = 0.0,
        include_handoff: bool = True,
        limit: int = 100,
    ) -> str:
        """Probe surfaces with downward traces and return placement locations.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This read-only tool adds surface awareness to Ghost's dry-run-first
        placement workflow. It uses public Unreal Python trace APIs and returns
        surface normals, hit actors, and placement handoff templates.

        Example:
            spatial_surface_probe(center=[0, 0, 0], grid_count=9, grid_spacing=500)"""
        t0 = time.monotonic()
        inputs = {
            "points": points or [],
            "center": center or [0.0, 0.0, 0.0],
            "grid_count": grid_count,
            "grid_spacing": grid_spacing,
            "trace_up": trace_up,
            "trace_down": trace_down,
            "trace_channel": trace_channel,
            "ignore_actor_query": ignore_actor_query,
            "placement_offset": placement_offset,
            "include_handoff": include_handoff,
            "limit": limit,
        }
        safe_limit = _bounded_limit(limit, default=100, maximum=500)
        try:
            clean_points = _vector3_list(points, "points", maximum=safe_limit)
            clean_center = _vector3(center, "center") or [0.0, 0.0, 0.0]
            safe_trace_channel = _clean_choice(trace_channel, "trace_channel", SURFACE_TRACE_CHANNELS, "visibility")
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_surface_probe",
                tool="spatial_surface_probe",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        safe_grid_count = _bounded_limit(grid_count, default=1, maximum=safe_limit)
        if clean_points:
            clean_points = clean_points[:safe_limit]
            safe_grid_count = len(clean_points)
        safe_grid_spacing = _float_value(grid_spacing, default=300.0, minimum=0.0)
        safe_trace_up = _float_value(trace_up, default=5000.0, minimum=1.0)
        safe_trace_down = _float_value(trace_down, default=10000.0, minimum=1.0)
        safe_placement_offset = _float_value(placement_offset, default=0.0)
        inputs.update({
            "points": clean_points,
            "center": clean_center,
            "grid_count": safe_grid_count,
            "grid_spacing": safe_grid_spacing,
            "trace_up": safe_trace_up,
            "trace_down": safe_trace_down,
            "trace_channel": safe_trace_channel,
            "placement_offset": safe_placement_offset,
            "limit": safe_limit,
        })
        code = _surface_probe_code(
            points=clean_points,
            center=clean_center,
            grid_count=safe_grid_count,
            grid_spacing=safe_grid_spacing,
            trace_up=safe_trace_up,
            trace_down=safe_trace_down,
            trace_channel=safe_trace_channel,
            ignore_actor_query=ignore_actor_query,
            placement_offset=safe_placement_offset,
            include_handoff=include_handoff,
        )
        result = _exec_structured(code, "spatial_surface_probe")
        return _json_result("spatial_surface_probe", "spatial_surface_probe", inputs, result, t0, SURFACE_PROBE_SCHEMA)

    @mcp.tool()
    def spatial_validate_placement(
        ctx: Context,
        actors: Optional[List[str]] = None,
        query: str = "",
        class_filter: str = "",
        tag_filter: str = "",
        center: Optional[List[float]] = None,
        radius: float = 0.0,
        include_hidden: bool = False,
        limit: int = 50,
        trace_up: float = 500.0,
        trace_down: float = 5000.0,
        trace_channel: str = "visibility",
        surface_tolerance: float = 10.0,
        clearance_padding: float = 0.0,
        ignore_self: bool = True,
        include_evidence_handoff: bool = True,
    ) -> str:
        """Validate placed actors against nearby surfaces and bounds overlap.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This is a read-only post-placement bridge. It reports whether actor
        bounds appear on-surface, floating, below/intersecting, missing a trace
        hit, or potentially overlapping nearby actor bounds.

        Example:
            spatial_validate_placement(tag_filter="Gameplay_POI", surface_tolerance=15)"""
        t0 = time.monotonic()
        inputs = {
            "actors": actors or [],
            "query": query,
            "class_filter": class_filter,
            "tag_filter": tag_filter,
            "center": center,
            "radius": radius,
            "include_hidden": include_hidden,
            "limit": limit,
            "trace_up": trace_up,
            "trace_down": trace_down,
            "trace_channel": trace_channel,
            "surface_tolerance": surface_tolerance,
            "clearance_padding": clearance_padding,
            "ignore_self": ignore_self,
            "include_evidence_handoff": include_evidence_handoff,
        }
        try:
            clean_actors = _string_list(actors, "actors", maximum=128)
            clean_center = _vector3(center, "center")
            safe_trace_channel = _clean_choice(trace_channel, "trace_channel", SURFACE_TRACE_CHANNELS, "visibility")
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_validate_placement",
                tool="spatial_validate_placement",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        safe_limit = _bounded_limit(limit, default=50, maximum=500)
        safe_radius = _float_value(radius, default=0.0, minimum=0.0)
        safe_trace_up = _float_value(trace_up, default=500.0, minimum=1.0)
        safe_trace_down = _float_value(trace_down, default=5000.0, minimum=1.0)
        safe_surface_tolerance = _float_value(surface_tolerance, default=10.0, minimum=0.0)
        safe_clearance_padding = _float_value(clearance_padding, default=0.0, minimum=0.0)
        inputs.update({
            "actors": clean_actors,
            "center": clean_center,
            "radius": safe_radius,
            "limit": safe_limit,
            "trace_up": safe_trace_up,
            "trace_down": safe_trace_down,
            "trace_channel": safe_trace_channel,
            "surface_tolerance": safe_surface_tolerance,
            "clearance_padding": safe_clearance_padding,
        })
        code = _placement_validation_code(
            actors=clean_actors,
            query=query,
            class_filter=class_filter,
            tag_filter=tag_filter,
            center=clean_center,
            radius=safe_radius,
            include_hidden=include_hidden,
            limit=safe_limit,
            trace_up=safe_trace_up,
            trace_down=safe_trace_down,
            trace_channel=safe_trace_channel,
            surface_tolerance=safe_surface_tolerance,
            clearance_padding=safe_clearance_padding,
            ignore_self=ignore_self,
            include_evidence_handoff=include_evidence_handoff,
        )
        result = _exec_structured(code, "spatial_validate_placement")
        return _json_result("spatial_validate_placement", "spatial_validate_placement", inputs, result, t0, PLACEMENT_VALIDATION_SCHEMA)

    @mcp.tool()
    def spatial_infer_placement_policy(
        ctx: Context,
        asset_paths: Optional[List[str]] = None,
        intent: str = "",
        policy: str = "auto",
        layout_hint: str = "line",
        base_spacing: float = 300.0,
        actor_label_prefix: str = "",
        tags: Optional[List[str]] = None,
        data_layer_names: Optional[List[str]] = None,
    ) -> str:
        """Infer a clean-room placement policy and dry-run handoff arguments.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This planner is intentionally local and read-only. It prepares arguments
        for Ghost's spatial placement tools without mutating Unreal Editor.

        Example:
            spatial_infer_placement_policy(asset_paths=["/Game/City/SM_Block.SM_Block"], intent="city blockout")"""
        t0 = time.monotonic()
        inputs = {
            "asset_paths": asset_paths or [],
            "intent": intent,
            "policy": policy,
            "layout_hint": layout_hint,
            "base_spacing": base_spacing,
            "actor_label_prefix": actor_label_prefix,
            "tags": tags or [],
            "data_layer_names": data_layer_names or [],
        }
        try:
            clean_policy = _clean_choice(policy, "policy", PLACEMENT_POLICIES, "auto")
            clean_layout = _clean_choice(layout_hint, "layout_hint", PLACEMENT_LAYOUTS, "line")
            clean_asset_paths = [
                _clean_asset_path(path)
                for path in _string_list(asset_paths, "asset_paths", maximum=128)
            ]
            clean_tags = _string_list(tags, "tags", maximum=64)
            clean_data_layer_names = _string_list(data_layer_names, "data_layer_names", maximum=32)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_infer_placement_policy",
                tool="spatial_infer_placement_policy",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        safe_spacing = _float_value(base_spacing, default=300.0, minimum=0.0)
        inputs.update({
            "asset_paths": clean_asset_paths,
            "policy": clean_policy,
            "layout_hint": clean_layout,
            "base_spacing": safe_spacing,
            "tags": clean_tags,
            "data_layer_names": clean_data_layer_names,
        })
        policy_plan = _infer_placement_policy(
            asset_paths=clean_asset_paths,
            intent=str(intent or "").strip(),
            policy=clean_policy,
            layout_hint=clean_layout,
            base_spacing=safe_spacing,
            actor_label_prefix=str(actor_label_prefix or "").strip(),
            tags=clean_tags,
            data_layer_names=clean_data_layer_names,
        )
        return _local_result(
            success=True,
            stage="spatial_infer_placement_policy",
            tool="spatial_infer_placement_policy",
            message="Inferred clean-room spatial placement policy.",
            inputs=inputs,
            outputs=policy_plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_plan_interior_composition(
        ctx: Context,
        room_type: str = "apartment",
        room_dimensions: Optional[List[float]] = None,
        room_origin: Optional[List[float]] = None,
        room_analysis_json: str = "",
        functional_zone_plan_json: str = "",
        prop_program_json: str = "",
        style: str = "",
        intent: str = "",
        screenshot_reference: str = "",
        screenshot_observations: Optional[List[str]] = None,
        existing_asset_paths: Optional[List[str]] = None,
        required_props: Optional[List[str]] = None,
        omit_props: Optional[List[str]] = None,
        content_path: str = "/Game/Generated/SpatialInteriors",
        actor_label_prefix: str = "",
        generate_missing_with_tripo: bool = True,
        include_image_to_model_handoffs: bool = True,
        limit: int = 32,
    ) -> str:
        """Plan a spatially coherent interior composition with Tripo handoffs.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner turns room dimensions, optional screenshot-derived
        prop observations, existing assets, and style intent into zone-aware
        placements plus guarded Tripo text/image generation and import steps.

        Example:
            spatial_plan_interior_composition(room_type="apartment", style="lived-in modern")"""
        t0 = time.monotonic()
        inputs = {
            "room_type": room_type,
            "room_dimensions": room_dimensions or [650.0, 500.0, 280.0],
            "room_origin": room_origin or [0.0, 0.0, 0.0],
            "room_analysis_json": room_analysis_json,
            "functional_zone_plan_json": functional_zone_plan_json,
            "prop_program_json": prop_program_json,
            "style": style,
            "intent": intent,
            "screenshot_reference": screenshot_reference,
            "screenshot_observations": screenshot_observations or [],
            "existing_asset_paths": existing_asset_paths or [],
            "required_props": required_props or [],
            "omit_props": omit_props or [],
            "content_path": content_path,
            "actor_label_prefix": actor_label_prefix,
            "generate_missing_with_tripo": generate_missing_with_tripo,
            "include_image_to_model_handoffs": include_image_to_model_handoffs,
            "limit": limit,
        }
        try:
            clean_room_analysis = _room_analysis_from_json(room_analysis_json)
            clean_functional_zone_plan = _functional_zone_plan_from_json(functional_zone_plan_json)
            clean_prop_program = _prop_program_from_json(prop_program_json)
            room_type_source = (
                clean_functional_zone_plan.get("room", {}).get("type")
                if clean_functional_zone_plan and isinstance(clean_functional_zone_plan.get("room"), Mapping)
                else clean_prop_program.get("room", {}).get("type")
                if clean_prop_program and isinstance(clean_prop_program.get("room"), Mapping)
                else clean_room_analysis.get("room_type")
                if clean_room_analysis and str(room_type or "apartment").strip().lower().replace(" ", "_").replace("-", "_") == "apartment"
                else room_type
            )
            clean_room_type = _clean_room_type(str(room_type_source or "apartment"))
            zone_room = clean_functional_zone_plan.get("room") if isinstance(clean_functional_zone_plan.get("room"), Mapping) else {}
            program_room = clean_prop_program.get("room") if isinstance(clean_prop_program.get("room"), Mapping) else {}
            clean_dimensions = (
                _vector3(zone_room.get("dimensions_cm"), "functional_zone_plan_json.room.dimensions_cm")
                if zone_room.get("dimensions_cm") is not None
                else None
            ) or (
                _vector3(program_room.get("dimensions_cm"), "prop_program_json.room.dimensions_cm")
                if program_room.get("dimensions_cm") is not None
                else None
            ) or (list(clean_room_analysis["room_dimensions"]) if clean_room_analysis else _room_dimensions(room_dimensions))
            clean_origin = (
                _vector3(zone_room.get("origin"), "functional_zone_plan_json.room.origin")
                if zone_room.get("origin") is not None
                else None
            ) or (
                _vector3(program_room.get("origin"), "prop_program_json.room.origin")
                if program_room.get("origin") is not None
                else None
            ) or (list(clean_room_analysis["room_origin"]) if clean_room_analysis else (_vector3(room_origin, "room_origin") or [0.0, 0.0, 0.0]))
            clean_screenshot_observations = _merge_unique(
                _string_list(screenshot_observations, "screenshot_observations", maximum=128),
                _room_analysis_observations(clean_room_analysis),
            )
            clean_existing_asset_paths = [
                _clean_asset_path(path)
                for path in _string_list(existing_asset_paths, "existing_asset_paths", maximum=256)
            ]
            clean_required_props = _string_list(required_props, "required_props", maximum=128)
            clean_omit_props = _string_list(omit_props, "omit_props", maximum=128)
            clean_content_path = _normalize_content_path(content_path)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_plan_interior_composition",
                tool="spatial_plan_interior_composition",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        safe_limit = _bounded_limit(limit, default=32, maximum=128)
        inputs.update({
            "room_type": clean_room_type,
            "room_dimensions": clean_dimensions,
            "room_origin": clean_origin,
            "room_analysis_applied": bool(clean_room_analysis),
            "functional_zone_plan_applied": bool(clean_functional_zone_plan),
            "prop_program_applied": bool(clean_prop_program),
            "screenshot_observations": clean_screenshot_observations,
            "existing_asset_paths": clean_existing_asset_paths,
            "required_props": clean_required_props,
            "omit_props": clean_omit_props,
            "content_path": clean_content_path,
            "limit": safe_limit,
        })
        plan = _plan_interior_composition(
            room_type=clean_room_type,
            room_dimensions=clean_dimensions,
            room_origin=clean_origin,
            functional_zone_plan=clean_functional_zone_plan,
            prop_program=clean_prop_program,
            style=str(style or "").strip(),
            intent=str(intent or "").strip(),
            screenshot_reference=str(screenshot_reference or "").strip(),
            screenshot_observations=clean_screenshot_observations,
            existing_asset_paths=clean_existing_asset_paths,
            required_props=clean_required_props,
            omit_props=clean_omit_props,
            content_path=clean_content_path,
            actor_label_prefix=str(actor_label_prefix or "").strip(),
            generate_missing_with_tripo=bool(generate_missing_with_tripo),
            include_image_to_model_handoffs=bool(include_image_to_model_handoffs),
            limit=safe_limit,
            room_analysis=clean_room_analysis,
        )
        return _local_result(
            success=True,
            stage="spatial_plan_interior_composition",
            tool="spatial_plan_interior_composition",
            message="Planned spatial interior composition with Tripo generation/import handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_prepare_screenshot_decomposition_request(
        ctx: Context,
        reference_image: str,
        image_size: Optional[List[float]] = None,
        room_type: str = "apartment",
        room_dimensions: Optional[List[float]] = None,
        room_origin: Optional[List[float]] = None,
        room_analysis_json: str = "",
        style: str = "",
        intent: str = "",
        include_architectural_fill: bool = True,
        prefer_crop_boxes: bool = True,
        max_items: int = 48,
    ) -> str:
        """Prepare a vision-agent request for screenshot decomposition.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner does not run computer vision. It turns a reference
        screenshot, optional room bounds, and optional live room analysis into a
        strict detected_items_json contract, vision prompt, and handoffs into
        Ghost's screenshot preflight, scene graph, crop, Tripo, binding,
        placement, and validation workflow.

        Example:
            spatial_prepare_screenshot_decomposition_request(reference_image="C:/refs/apartment.png", image_size=[1280, 720])"""
        t0 = time.monotonic()
        inputs = {
            "reference_image": reference_image,
            "image_size": image_size or [],
            "room_type": room_type,
            "room_dimensions": room_dimensions or [650.0, 500.0, 280.0],
            "room_origin": room_origin or [0.0, 0.0, 0.0],
            "room_analysis_json": room_analysis_json,
            "style": style,
            "intent": intent,
            "include_architectural_fill": include_architectural_fill,
            "prefer_crop_boxes": prefer_crop_boxes,
            "max_items": max_items,
        }
        safe_limit = _bounded_limit(max_items, default=48, maximum=128)
        try:
            clean_reference_image = _clean_reference_image(reference_image)
            clean_image_size = _image_size(image_size)
            clean_room_analysis = _room_analysis_from_json(room_analysis_json)
            room_type_source = (
                clean_room_analysis.get("room_type")
                if clean_room_analysis and str(room_type or "apartment").strip().lower().replace(" ", "_").replace("-", "_") == "apartment"
                else room_type
            )
            clean_room_type = _clean_room_type(str(room_type_source or "apartment"))
            clean_dimensions = list(clean_room_analysis["room_dimensions"]) if clean_room_analysis else _room_dimensions(room_dimensions)
            clean_origin = list(clean_room_analysis["room_origin"]) if clean_room_analysis else (_vector3(room_origin, "room_origin") or [0.0, 0.0, 0.0])
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_prepare_screenshot_decomposition_request",
                tool="spatial_prepare_screenshot_decomposition_request",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        inputs.update({
            "reference_image": clean_reference_image,
            "image_size": clean_image_size or [],
            "room_type": clean_room_type,
            "room_dimensions": clean_dimensions,
            "room_origin": clean_origin,
            "room_analysis_applied": bool(clean_room_analysis),
            "max_items": safe_limit,
        })
        plan = _plan_screenshot_decomposition_request(
            reference_image=clean_reference_image,
            image_size=clean_image_size,
            room_type=clean_room_type,
            room_dimensions=clean_dimensions,
            room_origin=clean_origin,
            room_analysis=clean_room_analysis,
            style=str(style or "").strip(),
            intent=str(intent or "").strip(),
            include_architectural_fill=bool(include_architectural_fill),
            prefer_crop_boxes=bool(prefer_crop_boxes),
            max_items=safe_limit,
        )
        return _local_result(
            success=True,
            stage="spatial_prepare_screenshot_decomposition_request",
            tool="spatial_prepare_screenshot_decomposition_request",
            message="Prepared screenshot decomposition request and reconstruction handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_preflight_screenshot_detections(
        ctx: Context,
        reference_image: str,
        detected_items_json: str,
        image_size: Optional[List[float]] = None,
        room_type: str = "apartment",
        require_crop_boxes: bool = True,
        confidence_threshold: float = 0.35,
        min_crop_area_ratio: float = 0.0005,
        limit: int = 64,
    ) -> str:
        """QA screenshot detections before reconstruction and Tripo generation.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner does not perform computer vision. It validates and
        normalizes agent/vision-supplied detected_items_json, checks crop box
        coverage, confidence, and overlap quality, then emits a normalized
        handoff for screenshot reconstruction.

        Example:
            spatial_preflight_screenshot_detections(reference_image="C:/refs/apartment.png", detected_items_json="<items>")"""
        t0 = time.monotonic()
        inputs = {
            "reference_image": reference_image,
            "detected_items_json": detected_items_json,
            "image_size": image_size or [],
            "room_type": room_type,
            "require_crop_boxes": require_crop_boxes,
            "confidence_threshold": confidence_threshold,
            "min_crop_area_ratio": min_crop_area_ratio,
            "limit": limit,
        }
        safe_limit = _bounded_limit(limit, default=64, maximum=256)
        try:
            clean_reference_image = _clean_reference_image(reference_image)
            clean_detected_items = _detected_items_from_json(detected_items_json, maximum=safe_limit)
            clean_image_size = _image_size(image_size)
            clean_room_type = _clean_room_type(str(room_type or "apartment"))
            safe_confidence_threshold = _float_value(confidence_threshold, default=0.35, minimum=0.0)
            safe_min_crop_area_ratio = _float_value(min_crop_area_ratio, default=0.0005, minimum=0.0)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_preflight_screenshot_detections",
                tool="spatial_preflight_screenshot_detections",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        inputs.update({
            "reference_image": clean_reference_image,
            "detected_item_count": len(clean_detected_items),
            "image_size": clean_image_size or [],
            "room_type": clean_room_type,
            "confidence_threshold": safe_confidence_threshold,
            "min_crop_area_ratio": safe_min_crop_area_ratio,
            "limit": safe_limit,
        })
        plan = _plan_screenshot_decomposition_preflight(
            reference_image=clean_reference_image,
            detected_items=clean_detected_items,
            image_size=clean_image_size,
            room_type=clean_room_type,
            require_crop_boxes=bool(require_crop_boxes),
            confidence_threshold=safe_confidence_threshold,
            min_crop_area_ratio=safe_min_crop_area_ratio,
        )
        return _local_result(
            success=True,
            stage="spatial_preflight_screenshot_detections",
            tool="spatial_preflight_screenshot_detections",
            message="Preflighted screenshot detections and prepared normalized reconstruction handoff.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_infer_screenshot_scene_graph(
        ctx: Context,
        reference_image: str,
        detected_items_json: str,
        image_size: Optional[List[float]] = None,
        room_type: str = "apartment",
        include_reconstruction_handoff: bool = True,
        limit: int = 64,
    ) -> str:
        """Infer a clean-room spatial scene graph from screenshot detections.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner does not perform image segmentation. It consumes
        agent/vision-supplied detected_items_json, uses crop positions and
        prop metadata to infer relationships such as left/right, foreground,
        support contact, wall anchors, and zone clusters, then emits richer
        reconstruction handoffs.

        Example:
            spatial_infer_screenshot_scene_graph(reference_image="C:/refs/apartment.png", detected_items_json="<items>", image_size=[1280, 720])"""
        t0 = time.monotonic()
        inputs = {
            "reference_image": reference_image,
            "detected_items_json": detected_items_json,
            "image_size": image_size or [],
            "room_type": room_type,
            "include_reconstruction_handoff": include_reconstruction_handoff,
            "limit": limit,
        }
        safe_limit = _bounded_limit(limit, default=64, maximum=256)
        try:
            clean_reference_image = _clean_reference_image(reference_image)
            clean_detected_items = _detected_items_from_json(detected_items_json, maximum=safe_limit)
            if not clean_detected_items:
                raise ValueError("detected_items_json is required")
            clean_image_size = _image_size(image_size)
            clean_room_type = _clean_room_type(str(room_type or "apartment"))
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_infer_screenshot_scene_graph",
                tool="spatial_infer_screenshot_scene_graph",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        inputs.update({
            "reference_image": clean_reference_image,
            "detected_item_count": len(clean_detected_items),
            "image_size": clean_image_size or [],
            "room_type": clean_room_type,
            "limit": safe_limit,
        })
        plan = _plan_screenshot_scene_graph(
            reference_image=clean_reference_image,
            detected_items=clean_detected_items,
            image_size=clean_image_size,
            room_type=clean_room_type,
            include_reconstruction_handoff=bool(include_reconstruction_handoff),
        )
        return _local_result(
            success=True,
            stage="spatial_infer_screenshot_scene_graph",
            tool="spatial_infer_screenshot_scene_graph",
            message="Inferred screenshot scene graph relationships and reconstruction handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_prepare_screenshot_crop_manifest(
        ctx: Context,
        reference_image: str = "",
        detected_items_json: str = "",
        reconstruction_plan_json: str = "",
        crop_output_dir: str = "Saved/MCPChat/spatial_crops",
        image_size: Optional[List[float]] = None,
        padding_px: float = 8.0,
        min_crop_px: int = 16,
        overwrite: bool = True,
        limit: int = 64,
    ) -> str:
        """Write local prop crops for screenshot-driven Tripo image generation.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local tool accepts either detected_items_json plus a local
        reference image, or a screenshot reconstruction result with crop_tasks.
        It writes one PNG per crop box, updates image-to-model handoffs to real
        file paths, and returns an updated reconstruction JSON payload for the
        Tripo generation batch planner.

        Example:
            spatial_prepare_screenshot_crop_manifest(reconstruction_plan_json="<screenshot reconstruction output>")"""
        t0 = time.monotonic()
        inputs = {
            "reference_image": reference_image,
            "detected_items_json": detected_items_json,
            "reconstruction_plan_json": reconstruction_plan_json,
            "crop_output_dir": crop_output_dir,
            "image_size": image_size or [],
            "padding_px": padding_px,
            "min_crop_px": min_crop_px,
            "overwrite": overwrite,
            "limit": limit,
        }
        safe_limit = _bounded_limit(limit, default=64, maximum=256)
        try:
            clean_image_size = _image_size(image_size)
            safe_padding = _float_value(padding_px, default=8.0, minimum=0.0)
            safe_min_crop_px = _bounded_limit(min_crop_px, default=16, maximum=4096)
            plan = _plan_screenshot_crop_manifest(
                reference_image=reference_image,
                detected_items_json=detected_items_json,
                reconstruction_plan_json=reconstruction_plan_json,
                crop_output_dir=crop_output_dir,
                image_size=clean_image_size,
                padding_px=safe_padding,
                min_crop_px=safe_min_crop_px,
                overwrite=bool(overwrite),
                limit=safe_limit,
            )
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_prepare_screenshot_crop_manifest",
                tool="spatial_prepare_screenshot_crop_manifest",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        inputs.update({
            "image_size": clean_image_size or [],
            "padding_px": safe_padding,
            "min_crop_px": safe_min_crop_px,
            "limit": safe_limit,
        })
        return _local_result(
            success=True,
            stage="spatial_prepare_screenshot_crop_manifest",
            tool="spatial_prepare_screenshot_crop_manifest",
            message="Prepared local screenshot crop manifest for Tripo image-to-model handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_plan_screenshot_reconstruction(
        ctx: Context,
        reference_image: str,
        detected_items_json: str = "",
        scene_graph_json: str = "",
        room_type: str = "apartment",
        room_dimensions: Optional[List[float]] = None,
        room_origin: Optional[List[float]] = None,
        room_analysis_json: str = "",
        style: str = "",
        intent: str = "",
        existing_asset_paths: Optional[List[str]] = None,
        required_props: Optional[List[str]] = None,
        content_path: str = "/Game/Generated/SpatialInteriors",
        actor_label_prefix: str = "",
        generate_missing_with_tripo: bool = True,
        include_text_fallbacks: bool = True,
        include_architectural_fill: bool = False,
        include_zone_recommendations: bool = False,
        limit: int = 32,
    ) -> str:
        """Plan screenshot-driven interior reconstruction with Tripo crop handoffs.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner does not perform computer vision by itself. When no
        detections are supplied, it returns the expected detected_items_json
        schema for the agent's vision step. When detections are supplied, it
        maps each prop to an existing asset or guarded Tripo image/text handoff
        and reuses the spatial interior planner for dry-run placement. If a
        screenshot scene graph is supplied, support and wall-anchor relations
        are folded into the placement hints before planning.

        Example:
            spatial_plan_screenshot_reconstruction(reference_image="C:/refs/apartment.png")"""
        t0 = time.monotonic()
        inputs = {
            "reference_image": reference_image,
            "detected_items_json": detected_items_json,
            "scene_graph_json": scene_graph_json,
            "room_type": room_type,
            "room_dimensions": room_dimensions or [650.0, 500.0, 280.0],
            "room_origin": room_origin or [0.0, 0.0, 0.0],
            "room_analysis_json": room_analysis_json,
            "style": style,
            "intent": intent,
            "existing_asset_paths": existing_asset_paths or [],
            "required_props": required_props or [],
            "content_path": content_path,
            "actor_label_prefix": actor_label_prefix,
            "generate_missing_with_tripo": generate_missing_with_tripo,
            "include_text_fallbacks": include_text_fallbacks,
            "include_architectural_fill": include_architectural_fill,
            "include_zone_recommendations": include_zone_recommendations,
            "limit": limit,
        }
        safe_limit = _bounded_limit(limit, default=32, maximum=128)
        try:
            clean_reference_image = _clean_reference_image(reference_image)
            clean_room_analysis = _room_analysis_from_json(room_analysis_json)
            room_type_source = (
                clean_room_analysis.get("room_type")
                if clean_room_analysis and str(room_type or "apartment").strip().lower().replace(" ", "_").replace("-", "_") == "apartment"
                else room_type
            )
            clean_room_type = _clean_room_type(str(room_type_source or "apartment"))
            clean_dimensions = list(clean_room_analysis["room_dimensions"]) if clean_room_analysis else _room_dimensions(room_dimensions)
            clean_origin = list(clean_room_analysis["room_origin"]) if clean_room_analysis else (_vector3(room_origin, "room_origin") or [0.0, 0.0, 0.0])
            clean_existing_asset_paths = [
                _clean_asset_path(path)
                for path in _string_list(existing_asset_paths, "existing_asset_paths", maximum=256)
            ]
            clean_required_props = _string_list(required_props, "required_props", maximum=safe_limit)
            clean_content_path = _normalize_content_path(content_path)
            clean_detected_items = _detected_items_from_json(detected_items_json, maximum=safe_limit)
            clean_scene_graph = _scene_graph_from_json(scene_graph_json)
            clean_detected_items = _merge_scene_graph_detected_items(
                clean_detected_items,
                clean_scene_graph,
                maximum=safe_limit,
            )
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_plan_screenshot_reconstruction",
                tool="spatial_plan_screenshot_reconstruction",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        inputs.update({
            "reference_image": clean_reference_image,
            "room_type": clean_room_type,
            "room_dimensions": clean_dimensions,
            "room_origin": clean_origin,
            "room_analysis_applied": bool(clean_room_analysis),
            "existing_asset_paths": clean_existing_asset_paths,
            "required_props": clean_required_props,
            "content_path": clean_content_path,
            "detected_item_count": len(clean_detected_items),
            "scene_graph_applied": bool(clean_scene_graph),
            "scene_graph_node_count": _scene_graph_context(clean_scene_graph)["node_count"] if clean_scene_graph else 0,
            "include_architectural_fill": bool(include_architectural_fill),
            "include_zone_recommendations": bool(include_zone_recommendations),
            "limit": safe_limit,
        })
        plan = _plan_screenshot_reconstruction(
            reference_image=clean_reference_image,
            detected_items=clean_detected_items,
            room_type=clean_room_type,
            room_dimensions=clean_dimensions,
            room_origin=clean_origin,
            style=str(style or "").strip(),
            intent=str(intent or "").strip(),
            existing_asset_paths=clean_existing_asset_paths,
            content_path=clean_content_path,
            actor_label_prefix=str(actor_label_prefix or "").strip(),
            generate_missing_with_tripo=bool(generate_missing_with_tripo),
            include_text_fallbacks=bool(include_text_fallbacks),
            limit=safe_limit,
            required_props=clean_required_props,
            include_architectural_fill=bool(include_architectural_fill),
            include_zone_recommendations=bool(include_zone_recommendations),
            room_analysis=clean_room_analysis,
            scene_graph=clean_scene_graph,
        )
        message = (
            "Returned screenshot decomposition contract for agent vision."
            if plan.get("decomposition_required")
            else "Planned screenshot reconstruction with asset mapping, Tripo crop handoffs, and spatial placement."
        )
        return _local_result(
            success=True,
            stage="spatial_plan_screenshot_reconstruction",
            tool="spatial_plan_screenshot_reconstruction",
            message=message,
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_catalog_project_assets(
        ctx: Context,
        folders: Optional[List[str]] = None,
        query: str = "",
        class_names: Optional[List[str]] = None,
        include_selected: bool = True,
        include_bounds: bool = False,
        include_resolver_handoff: bool = True,
        limit: int = 200,
    ) -> str:
        """Catalog existing project assets for spatial composition matching.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This read-only bridge queries project asset metadata from /Game folders
        and returns resolver-ready asset_catalog_json for
        spatial_resolve_project_assets. StaticMesh and Blueprint candidates are
        included by default so Ghost can prefer existing project content before
        guarded Tripo generation.

        Example:
            spatial_catalog_project_assets(folders=["/Game/Props"], query="kitchen", class_names=["StaticMesh", "Blueprint"])"""
        t0 = time.monotonic()
        inputs = {
            "folders": folders or ["/Game"],
            "query": query,
            "class_names": class_names or ["StaticMesh", "Blueprint"],
            "include_selected": include_selected,
            "include_bounds": include_bounds,
            "include_resolver_handoff": include_resolver_handoff,
            "limit": limit,
        }
        safe_limit = _bounded_limit(limit, default=200, maximum=1000)
        try:
            clean_folders = [
                _normalize_content_path(folder)
                for folder in (_string_list(folders, "folders", maximum=32) if folders is not None else ["/Game"])
            ]
            if not clean_folders:
                clean_folders = ["/Game"]
            clean_class_names = _string_list(class_names, "class_names", maximum=32) if class_names is not None else ["StaticMesh", "Blueprint"]
            if any(str(name).strip().lower() == "all" for name in clean_class_names):
                clean_class_names = []
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_catalog_project_assets",
                tool="spatial_catalog_project_assets",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        inputs.update({
            "folders": clean_folders,
            "class_names": clean_class_names,
            "include_bounds": bool(include_bounds),
            "limit": safe_limit,
        })
        code = _project_asset_catalog_code(
            folders=clean_folders,
            query=str(query or "").strip(),
            class_names=clean_class_names,
            include_selected=bool(include_selected),
            include_bounds=bool(include_bounds),
            include_resolver_handoff=bool(include_resolver_handoff),
            limit=safe_limit,
        )
        result = _exec_structured(code, "spatial_catalog_project_assets")
        return _json_result(
            "spatial_catalog_project_assets",
            "spatial_catalog_project_assets",
            inputs,
            result,
            t0,
            PROJECT_ASSET_CATALOG_SCHEMA,
        )

    @mcp.tool()
    def spatial_resolve_project_assets(
        ctx: Context,
        composition_plan_json: str,
        asset_catalog_json: str = "",
        candidate_asset_paths: Optional[List[str]] = None,
        minimum_score: float = 45.0,
        max_candidates_per_prop: int = 3,
        include_resolved_existing: bool = False,
        limit: int = 256,
    ) -> str:
        """Resolve planned spatial props against existing project assets first.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner accepts an interior composition or screenshot
        reconstruction plus a project asset catalog. It scores candidate /Game
        assets against planned props, emits asset_overrides_json for resolved
        matches, and hands unresolved props to the guarded Tripo batch planner.

        Example:
            spatial_resolve_project_assets(composition_plan_json="<plan>", candidate_asset_paths=["/Game/Props/SM_Books.SM_Books"])"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "asset_catalog_json": asset_catalog_json,
            "candidate_asset_paths": candidate_asset_paths or [],
            "minimum_score": minimum_score,
            "max_candidates_per_prop": max_candidates_per_prop,
            "include_resolved_existing": include_resolved_existing,
            "limit": limit,
        }
        safe_limit = _bounded_limit(limit, default=256, maximum=1000)
        try:
            source_outputs, clean_composition_plan = _spatial_generation_source_from_json(composition_plan_json)
            if not clean_composition_plan:
                raise ValueError("composition_plan_json is required")
            if not isinstance(clean_composition_plan.get("placement_steps"), list):
                raise ValueError("composition_plan_json.placement_steps must be a list")
            safe_minimum_score = _float_value(minimum_score, default=45.0, minimum=0.0)
            safe_max_candidates = _bounded_limit(max_candidates_per_prop, default=3, maximum=12)
            asset_catalog = _asset_catalog_from_json(
                asset_catalog_json,
                candidate_asset_paths=candidate_asset_paths or [],
                maximum=safe_limit,
            )
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_resolve_project_assets",
                tool="spatial_resolve_project_assets",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "source_schema": source_outputs.get("schema") or clean_composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
            "placement_step_count": len(clean_composition_plan.get("placement_steps", [])),
            "asset_catalog_count": len(asset_catalog),
            "minimum_score": safe_minimum_score,
            "max_candidates_per_prop": safe_max_candidates,
            "limit": safe_limit,
        })
        plan = _resolve_assets_for_composition(
            composition_plan=clean_composition_plan,
            asset_catalog=asset_catalog,
            minimum_score=safe_minimum_score,
            max_candidates_per_prop=safe_max_candidates,
            include_resolved_existing=bool(include_resolved_existing),
            tripo_source_json=composition_plan_json,
        )
        return _local_result(
            success=True,
            stage="spatial_resolve_project_assets",
            tool="spatial_resolve_project_assets",
            message="Resolved spatial composition props against existing project asset candidates.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_prepare_tripo_generation_batch(
        ctx: Context,
        composition_plan_json: str,
        content_path: str = "",
        session_name: str = "",
        prefer_image_crops: bool = True,
        include_text_fallbacks: bool = True,
        confirm_spend: bool = False,
        limit: int = 64,
    ) -> str:
        """Prepare a guarded Tripo generation batch for spatial compositions.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner accepts an interior composition, screenshot
        reconstruction output, or generated-asset binding output. It reconciles
        text and crop-based Tripo handoffs, keeps spend confirmation explicit,
        and returns the import, binding, placement, validation, and iteration
        follow-ups needed to finish the worldbuilding loop.

        Example:
            spatial_prepare_tripo_generation_batch(composition_plan_json="<screenshot reconstruction output>")"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "content_path": content_path,
            "session_name": session_name,
            "prefer_image_crops": prefer_image_crops,
            "include_text_fallbacks": include_text_fallbacks,
            "confirm_spend": confirm_spend,
            "limit": limit,
        }
        safe_limit = _bounded_limit(limit, default=64, maximum=256)
        try:
            source_outputs, clean_composition_plan = _spatial_generation_source_from_json(composition_plan_json)
            if not clean_composition_plan:
                raise ValueError("composition_plan_json is required")
            if not isinstance(clean_composition_plan.get("placement_steps"), list):
                raise ValueError("composition_plan_json.placement_steps must be a list")
            resolved_content_path = _generation_content_path(
                composition_plan=clean_composition_plan,
                content_path=content_path,
            )
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_prepare_tripo_generation_batch",
                tool="spatial_prepare_tripo_generation_batch",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "source_schema": source_outputs.get("schema") or clean_composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
            "placement_step_count": len(clean_composition_plan.get("placement_steps", [])),
            "content_path": resolved_content_path,
            "session_name": str(session_name or "").strip(),
            "limit": safe_limit,
        })
        plan = _plan_spatial_tripo_generation_batch(
            source_outputs=source_outputs,
            composition_plan=clean_composition_plan,
            content_path=resolved_content_path,
            session_name=session_name,
            prefer_image_crops=bool(prefer_image_crops),
            include_text_fallbacks=bool(include_text_fallbacks),
            confirm_spend=bool(confirm_spend),
            limit=safe_limit,
        )
        return _local_result(
            success=True,
            stage="spatial_prepare_tripo_generation_batch",
            tool="spatial_prepare_tripo_generation_batch",
            message="Prepared guarded Tripo generation batch for spatial worldbuilding.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_bind_generated_assets_to_composition(
        ctx: Context,
        composition_plan_json: str,
        import_results_json: str = "",
        asset_overrides_json: str = "",
        include_unresolved_steps: bool = True,
        surface_tolerance: float = 15.0,
        clearance_padding: float = 12.0,
    ) -> str:
        """Bind imported/generated assets back into a spatial composition plan.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner consumes a spatial interior composition plan plus
        completed Tripo import results or manual asset overrides. It replaces
        placeholder asset paths with real /Game assets and returns dry-run
        placement, validation, and iteration handoffs without mutating the
        Unreal Editor scene.

        Example:
            spatial_bind_generated_assets_to_composition(composition_plan_json="<plan>", import_results_json="<imports>")"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "import_results_json": import_results_json,
            "asset_overrides_json": asset_overrides_json,
            "include_unresolved_steps": include_unresolved_steps,
            "surface_tolerance": surface_tolerance,
            "clearance_padding": clearance_padding,
        }
        try:
            clean_composition_plan = _composition_plan_from_json(composition_plan_json)
            if not clean_composition_plan:
                raise ValueError("composition_plan_json is required")
            if not isinstance(clean_composition_plan.get("placement_steps"), list):
                raise ValueError("composition_plan_json.placement_steps must be a list")
            # Parse early so malformed asset/import JSON reports before planning.
            _normalize_import_result_records(import_results_json)
            _asset_override_records_from_json(asset_overrides_json)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_bind_generated_assets_to_composition",
                tool="spatial_bind_generated_assets_to_composition",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        safe_surface_tolerance = _float_value(surface_tolerance, default=15.0, minimum=0.0)
        safe_clearance_padding = _float_value(clearance_padding, default=12.0, minimum=0.0)
        inputs.update({
            "placement_step_count": len(clean_composition_plan.get("placement_steps", [])),
            "surface_tolerance": safe_surface_tolerance,
            "clearance_padding": safe_clearance_padding,
        })
        plan = _plan_composition_asset_binding(
            composition_plan=clean_composition_plan,
            import_results_json=import_results_json,
            asset_overrides_json=asset_overrides_json,
            include_unresolved_steps=bool(include_unresolved_steps),
            surface_tolerance=safe_surface_tolerance,
            clearance_padding=safe_clearance_padding,
        )
        return _local_result(
            success=True,
            stage="spatial_bind_generated_assets_to_composition",
            tool="spatial_bind_generated_assets_to_composition",
            message="Bound generated/imported assets into dry-run spatial placement handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_plan_asset_scale_corrections(
        ctx: Context,
        composition_plan_json: str,
        min_scale: float = 0.05,
        max_scale: float = 20.0,
        anisotropy_tolerance: float = 0.35,
        close_scale_tolerance: float = 0.05,
        allow_non_uniform_scale: bool = False,
        include_updated_plan: bool = True,
        limit: int = 128,
    ) -> str:
        """Plan scale corrections for generated or bound spatial assets.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local/read-only planner consumes a generated-asset binding output,
        interior composition, or screenshot reconstruction. It compares planned
        prop dimensions to imported mesh bounds, recommends reviewed scale
        updates, and returns a scale-corrected dry-run composition plan without
        mutating the Unreal Editor scene.

        Example:
            spatial_plan_asset_scale_corrections(composition_plan_json="<binding output>")"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "min_scale": min_scale,
            "max_scale": max_scale,
            "anisotropy_tolerance": anisotropy_tolerance,
            "close_scale_tolerance": close_scale_tolerance,
            "allow_non_uniform_scale": allow_non_uniform_scale,
            "include_updated_plan": include_updated_plan,
            "limit": limit,
        }
        try:
            clean_composition_plan = _composition_like_from_json(composition_plan_json)
            if not clean_composition_plan:
                raise ValueError("composition_plan_json is required")
            if not isinstance(clean_composition_plan.get("placement_steps"), list):
                raise ValueError("composition_plan_json.placement_steps must be a list")
            safe_min_scale = _float_value(min_scale, default=0.05, minimum=0.001)
            safe_max_scale = _float_value(max_scale, default=20.0, minimum=0.001)
            if safe_min_scale > safe_max_scale:
                raise ValueError("min_scale must be less than or equal to max_scale")
            safe_anisotropy_tolerance = _float_value(anisotropy_tolerance, default=0.35, minimum=0.0)
            safe_close_scale_tolerance = _float_value(close_scale_tolerance, default=0.05, minimum=0.0)
            safe_limit = _bounded_limit(limit, default=128, maximum=512)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_plan_asset_scale_corrections",
                tool="spatial_plan_asset_scale_corrections",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "source_schema": clean_composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
            "placement_step_count": len(clean_composition_plan.get("placement_steps", [])),
            "min_scale": safe_min_scale,
            "max_scale": safe_max_scale,
            "anisotropy_tolerance": safe_anisotropy_tolerance,
            "close_scale_tolerance": safe_close_scale_tolerance,
            "limit": safe_limit,
        })
        plan = _plan_asset_scale_corrections(
            composition_plan=clean_composition_plan,
            min_scale=safe_min_scale,
            max_scale=safe_max_scale,
            anisotropy_tolerance=safe_anisotropy_tolerance,
            close_scale_tolerance=safe_close_scale_tolerance,
            allow_non_uniform_scale=bool(allow_non_uniform_scale),
            include_updated_plan=bool(include_updated_plan),
            limit=safe_limit,
        )
        return _local_result(
            success=True,
            stage="spatial_plan_asset_scale_corrections",
            tool="spatial_plan_asset_scale_corrections",
            message="Planned generated-asset scale corrections and dry-run handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_plan_support_surface_anchors(
        ctx: Context,
        composition_plan_json: str,
        room_analysis_json: str = "",
        anchor_floor: bool = True,
        anchor_horizontal_supports: bool = True,
        anchor_walls: bool = True,
        include_updated_plan: bool = True,
        limit: int = 128,
    ) -> str:
        """Plan floor, support-surface, and wall anchors for a composition.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local/read-only planner consumes an interior composition,
        screenshot reconstruction, generated-asset binding, or scale-corrected
        plan plus optional spatial_analyze_room output. It updates dry-run
        placement steps so props intended for counters, tables, shelves, walls,
        or floors align to classified room surfaces before mutation.

        Example:
            spatial_plan_support_surface_anchors(composition_plan_json="<composition>", room_analysis_json="<room analysis>")"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "room_analysis_json": room_analysis_json,
            "anchor_floor": anchor_floor,
            "anchor_horizontal_supports": anchor_horizontal_supports,
            "anchor_walls": anchor_walls,
            "include_updated_plan": include_updated_plan,
            "limit": limit,
        }
        try:
            clean_composition_plan = _composition_like_from_json(composition_plan_json)
            if not clean_composition_plan:
                raise ValueError("composition_plan_json is required")
            if not isinstance(clean_composition_plan.get("placement_steps"), list):
                raise ValueError("composition_plan_json.placement_steps must be a list")
            clean_room_analysis = _room_analysis_from_json(room_analysis_json)
            safe_limit = _bounded_limit(limit, default=128, maximum=512)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_plan_support_surface_anchors",
                tool="spatial_plan_support_surface_anchors",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "source_schema": clean_composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
            "placement_step_count": len(clean_composition_plan.get("placement_steps", [])),
            "room_analysis_applied": bool(clean_room_analysis),
            "limit": safe_limit,
        })
        plan = _plan_support_surface_anchors(
            composition_plan=clean_composition_plan,
            room_analysis=clean_room_analysis,
            anchor_floor=bool(anchor_floor),
            anchor_horizontal_supports=bool(anchor_horizontal_supports),
            anchor_walls=bool(anchor_walls),
            include_updated_plan=bool(include_updated_plan),
            limit=safe_limit,
        )
        return _local_result(
            success=True,
            stage="spatial_plan_support_surface_anchors",
            tool="spatial_plan_support_surface_anchors",
            message="Planned support-surface anchors and dry-run handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_apply_composition_plan(
        ctx: Context,
        composition_plan_json: str,
        layout_preflight_json: str = "",
        default_tags: Optional[List[str]] = None,
        default_data_layer_names: Optional[List[str]] = None,
        fail_on_missing_data_layer: bool = False,
        dry_run: bool = True,
        allow_mutation: bool = False,
        stop_on_unresolved: bool = True,
        block_on_preflight_errors: bool = True,
        block_on_spatial_fit_review: bool = True,
        stop_on_error: bool = True,
        limit: int = 64,
        select_actors: bool = True,
        focus_viewport: bool = False,
    ) -> str:
        """Apply or review a whole spatial composition placement queue.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This bridge accepts an interior composition, screenshot reconstruction,
        or generated-asset binding output. It normalizes placement steps into a
        batch queue, blocks unresolved generated assets by default, and executes
        editor placement only when dry_run=false and allow_mutation=true.

        Example:
            spatial_apply_composition_plan(composition_plan_json="<binding output>", dry_run=True)"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "layout_preflight_json": layout_preflight_json,
            "default_tags": default_tags or [],
            "default_data_layer_names": default_data_layer_names or [],
            "fail_on_missing_data_layer": fail_on_missing_data_layer,
            "dry_run": dry_run,
            "allow_mutation": allow_mutation,
            "stop_on_unresolved": stop_on_unresolved,
            "block_on_preflight_errors": block_on_preflight_errors,
            "block_on_spatial_fit_review": block_on_spatial_fit_review,
            "stop_on_error": stop_on_error,
            "limit": limit,
            "select_actors": select_actors,
            "focus_viewport": focus_viewport,
        }
        try:
            clean_composition_plan = _composition_like_from_json(composition_plan_json)
            if not clean_composition_plan:
                raise ValueError("composition_plan_json is required")
            if not isinstance(clean_composition_plan.get("placement_steps"), list):
                raise ValueError("composition_plan_json.placement_steps must be a list")
            clean_layout_preflight = _layout_preflight_from_json(layout_preflight_json)
            clean_default_tags = _string_list(default_tags, "default_tags", maximum=64)
            clean_default_data_layer_names = _string_list(default_data_layer_names, "default_data_layer_names", maximum=32)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_apply_composition_plan",
                tool="spatial_apply_composition_plan",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        safe_limit = _bounded_limit(limit, default=64, maximum=256)
        inputs.update({
            "source_schema": clean_composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
            "placement_step_count": len(clean_composition_plan.get("placement_steps", [])),
            "layout_preflight_applied": bool(clean_layout_preflight),
            "default_tags": clean_default_tags,
            "default_data_layer_names": clean_default_data_layer_names,
            "limit": safe_limit,
        })
        plan = _plan_composition_placement_batch(
            composition_plan=clean_composition_plan,
            layout_preflight=clean_layout_preflight,
            default_tags=clean_default_tags,
            default_data_layer_names=clean_default_data_layer_names,
            fail_on_missing_data_layer=bool(fail_on_missing_data_layer),
            select_actors=bool(select_actors),
            focus_viewport=bool(focus_viewport),
            dry_run=bool(dry_run),
            allow_mutation=bool(allow_mutation),
            stop_on_unresolved=bool(stop_on_unresolved),
            block_on_preflight_errors=bool(block_on_preflight_errors),
            block_on_spatial_fit_review=bool(block_on_spatial_fit_review),
            limit=safe_limit,
        )
        if dry_run:
            return _local_result(
                success=True,
                stage="spatial_apply_composition_plan",
                tool="spatial_apply_composition_plan",
                message="Prepared dry-run spatial composition placement batch.",
                inputs=inputs,
                outputs=plan,
                t0=t0,
            )
        if not allow_mutation:
            return _local_result(
                success=False,
                stage="spatial_apply_composition_plan",
                tool="spatial_apply_composition_plan",
                message="spatial_apply_composition_plan mutates the editor; pass allow_mutation=True to execute it.",
                inputs=inputs,
                outputs=plan,
                errors=["allow_mutation=True is required when dry_run=False"],
                t0=t0,
            )
        if plan.get("status") in {"blocked_by_preflight", "blocked_by_unresolved_assets", "blocked_by_spatial_fit_review", "no_placement_steps", "no_executable_steps"}:
            return _local_result(
                success=False,
                stage="spatial_apply_composition_plan",
                tool="spatial_apply_composition_plan",
                message=f"Composition placement batch cannot execute: {plan.get('status')}",
                inputs=inputs,
                outputs=plan,
                errors=[f"Composition placement batch cannot execute: {plan.get('status')}"],
                t0=t0,
            )

        execution_results = []
        for record in plan.get("executable_steps", []):
            if not isinstance(record, Mapping):
                continue
            code = _asset_placement_code(
                asset_path=str(record.get("asset_path") or ""),
                actor_label=str(record.get("actor_label") or ""),
                location=list(record.get("location") or [0.0, 0.0, 0.0]),
                rotation=list(record.get("rotation") or [0.0, 0.0, 0.0]),
                scale=list(record.get("scale") or [1.0, 1.0, 1.0]),
                tags=list(record.get("tags") or []),
                data_layer_names=list(record.get("data_layer_names") or []),
                fail_on_missing_data_layer=bool(record.get("fail_on_missing_data_layer")),
                select_actor=bool(record.get("select_actor")),
                focus_viewport=bool(record.get("focus_viewport")),
            )
            result = _exec_transactional(code, f"MCP Spatial Apply Composition: {record.get('id')}")
            execution_results.append({
                "id": record.get("id"),
                "actor_label": record.get("actor_label"),
                "asset_path": record.get("asset_path"),
                "success": bool(result.get("success")) if isinstance(result, Mapping) else False,
                "result": result,
            })
            if stop_on_error and (not isinstance(result, Mapping) or not result.get("success")):
                break

        failed_count = sum(1 for item in execution_results if not item.get("success"))
        executed_count = sum(1 for item in execution_results if item.get("success"))
        plan = dict(plan)
        plan.update({
            "status": "executed" if execution_results and failed_count == 0 else ("partial_failure" if execution_results else "no_execution_results"),
            "execution_results": execution_results,
            "executed_count": executed_count,
            "failed_count": failed_count,
        })
        return _local_result(
            success=failed_count == 0 and bool(execution_results),
            stage="spatial_apply_composition_plan",
            tool="spatial_apply_composition_plan",
            message="Applied spatial composition placement batch." if failed_count == 0 else "Spatial composition placement batch had failures.",
            inputs=inputs,
            outputs=plan,
            errors=[] if failed_count == 0 else ["One or more composition placement steps failed"],
            t0=t0,
        )

    @mcp.tool()
    def spatial_preflight_interior_layout(
        ctx: Context,
        composition_plan_json: str,
        room_analysis_json: str = "",
        min_walkway_width: float = 90.0,
        clearance_padding: float = 12.0,
        pairwise_padding: float = 8.0,
        include_suggestions: bool = True,
    ) -> str:
        """Preflight an interior composition before editor placement.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner checks approximate room bounds, prop footprints,
        pairwise spacing, zone fit, support-surface hints, and circulation
        risks before the composition is placed or validated in live Unreal.

        Example:
            spatial_preflight_interior_layout(composition_plan_json="<plan>")"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "room_analysis_json": room_analysis_json,
            "min_walkway_width": min_walkway_width,
            "clearance_padding": clearance_padding,
            "pairwise_padding": pairwise_padding,
            "include_suggestions": include_suggestions,
        }
        try:
            clean_composition_plan = _composition_like_from_json(composition_plan_json)
            if not clean_composition_plan:
                raise ValueError("composition_plan_json is required")
            if not isinstance(clean_composition_plan.get("placement_steps"), list):
                raise ValueError("composition_plan_json.placement_steps must be a list")
            clean_room_analysis = _room_analysis_from_json(room_analysis_json)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_preflight_interior_layout",
                tool="spatial_preflight_interior_layout",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        safe_min_walkway_width = _float_value(min_walkway_width, default=90.0, minimum=0.0)
        safe_clearance_padding = _float_value(clearance_padding, default=12.0, minimum=0.0)
        safe_pairwise_padding = _float_value(pairwise_padding, default=8.0, minimum=0.0)
        inputs.update({
            "placement_step_count": len(clean_composition_plan.get("placement_steps", [])),
            "room_analysis_applied": bool(clean_room_analysis),
            "min_walkway_width": safe_min_walkway_width,
            "clearance_padding": safe_clearance_padding,
            "pairwise_padding": safe_pairwise_padding,
        })
        plan = _plan_layout_preflight(
            composition_plan=clean_composition_plan,
            room_analysis=clean_room_analysis,
            min_walkway_width=safe_min_walkway_width,
            clearance_padding=safe_clearance_padding,
            pairwise_padding=safe_pairwise_padding,
            include_suggestions=bool(include_suggestions),
        )
        return _local_result(
            success=True,
            stage="spatial_preflight_interior_layout",
            tool="spatial_preflight_interior_layout",
            message="Preflighted approximate interior layout bounds, spacing, and validation handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_plan_layout_preflight_corrections(
        ctx: Context,
        composition_plan_json: str,
        layout_preflight_json: str,
        correction_step_cm: float = 35.0,
        boundary_margin_cm: float = 8.0,
        pairwise_padding: float = 12.0,
        min_walkway_width: float = 90.0,
        include_updated_plan: bool = True,
        limit: int = 128,
    ) -> str:
        """Plan dry-run corrections from an interior layout preflight.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local/read-only planner consumes a composition plus
        spatial_preflight_interior_layout output. It deterministically repairs
        fixable bounds, overlap, and circulation findings in the dry-run plan,
        and routes support/semantic issues to the right follow-up tools.

        Example:
            spatial_plan_layout_preflight_corrections(composition_plan_json="<composition>", layout_preflight_json="<layout preflight>")"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "layout_preflight_json": layout_preflight_json,
            "correction_step_cm": correction_step_cm,
            "boundary_margin_cm": boundary_margin_cm,
            "pairwise_padding": pairwise_padding,
            "min_walkway_width": min_walkway_width,
            "include_updated_plan": include_updated_plan,
            "limit": limit,
        }
        try:
            clean_composition_plan = _composition_like_from_json(composition_plan_json)
            if not clean_composition_plan:
                raise ValueError("composition_plan_json is required")
            if not isinstance(clean_composition_plan.get("placement_steps"), list):
                raise ValueError("composition_plan_json.placement_steps must be a list")
            clean_layout_preflight = _layout_preflight_from_json(layout_preflight_json)
            if not clean_layout_preflight:
                raise ValueError("layout_preflight_json is required")
            safe_correction_step = _float_value(correction_step_cm, default=35.0, minimum=0.0)
            safe_boundary_margin = _float_value(boundary_margin_cm, default=8.0, minimum=0.0)
            safe_pairwise_padding = _float_value(pairwise_padding, default=12.0, minimum=0.0)
            safe_min_walkway_width = _float_value(min_walkway_width, default=90.0, minimum=0.0)
            safe_limit = _bounded_limit(limit, default=128, maximum=512)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_plan_layout_preflight_corrections",
                tool="spatial_plan_layout_preflight_corrections",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "source_schema": clean_composition_plan.get("schema") or INTERIOR_COMPOSITION_SCHEMA,
            "placement_step_count": len(clean_composition_plan.get("placement_steps", [])),
            "layout_preflight_status": clean_layout_preflight.get("status", ""),
            "layout_preflight_issue_count": int(clean_layout_preflight.get("issue_count") or 0),
            "correction_step_cm": safe_correction_step,
            "boundary_margin_cm": safe_boundary_margin,
            "pairwise_padding": safe_pairwise_padding,
            "min_walkway_width": safe_min_walkway_width,
            "limit": safe_limit,
        })
        plan = _plan_layout_preflight_corrections(
            composition_plan=clean_composition_plan,
            layout_preflight=clean_layout_preflight,
            correction_step_cm=safe_correction_step,
            boundary_margin_cm=safe_boundary_margin,
            pairwise_padding=safe_pairwise_padding,
            min_walkway_width=safe_min_walkway_width,
            include_updated_plan=bool(include_updated_plan),
            limit=safe_limit,
        )
        return _local_result(
            success=True,
            stage="spatial_plan_layout_preflight_corrections",
            tool="spatial_plan_layout_preflight_corrections",
            message="Planned dry-run layout preflight corrections and follow-up handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_preflight_candidate_clearance(
        ctx: Context,
        composition_plan_json: str,
        room_analysis_json: str = "",
        actor_query: str = "",
        class_filter: str = "",
        tag_filter: str = "",
        include_hidden: bool = False,
        ignore_actor_labels: Optional[List[str]] = None,
        clearance_padding: float = 12.0,
        limit: int = 200,
    ) -> str:
        """Check planned placement candidates against live actor bounds.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This read-only preflight builds conservative candidate bounds from a
        composition plan, then compares them to existing live Unreal actor
        bounds before any spawn/mutation step. It is a planning gate, not a
        physics simulation.

        Example:
            spatial_preflight_candidate_clearance(composition_plan_json="<composition>", actor_query="Apartment")"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "room_analysis_json": room_analysis_json,
            "actor_query": actor_query,
            "class_filter": class_filter,
            "tag_filter": tag_filter,
            "include_hidden": include_hidden,
            "ignore_actor_labels": ignore_actor_labels or [],
            "clearance_padding": clearance_padding,
            "limit": limit,
        }
        try:
            clean_composition_plan = _composition_like_from_json(composition_plan_json)
            if not clean_composition_plan:
                raise ValueError("composition_plan_json is required")
            if not isinstance(clean_composition_plan.get("placement_steps"), list):
                raise ValueError("composition_plan_json.placement_steps must be a list")
            clean_room_analysis = _room_analysis_from_json(room_analysis_json)
            clean_ignore_actor_labels = _string_list(ignore_actor_labels, "ignore_actor_labels", maximum=128)
            safe_clearance_padding = _float_value(clearance_padding, default=12.0, minimum=0.0)
            safe_limit = _bounded_limit(limit, default=200, maximum=2000)
            candidate_packet = _candidate_clearance_records(
                composition_plan=clean_composition_plan,
                room_analysis=clean_room_analysis,
                clearance_padding=safe_clearance_padding,
            )
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_preflight_candidate_clearance",
                tool="spatial_preflight_candidate_clearance",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        candidates = list(candidate_packet.get("candidates", []))
        inputs.update({
            "composition_plan_applied": bool(clean_composition_plan),
            "room_analysis_applied": bool(clean_room_analysis),
            "candidate_count": len(candidates),
            "clearance_padding": safe_clearance_padding,
            "limit": safe_limit,
            "ignore_actor_labels": clean_ignore_actor_labels,
        })
        code = _candidate_clearance_code(
            candidates=candidates,
            room=candidate_packet.get("room", {}),
            actor_query=actor_query,
            class_filter=class_filter,
            tag_filter=tag_filter,
            include_hidden=include_hidden,
            ignore_actor_labels=clean_ignore_actor_labels,
            clearance_padding=safe_clearance_padding,
            limit=safe_limit,
        )
        result = _exec_structured(code, "spatial_preflight_candidate_clearance")
        return _json_result(
            "spatial_preflight_candidate_clearance",
            "spatial_preflight_candidate_clearance",
            inputs,
            result,
            t0,
            CANDIDATE_CLEARANCE_SCHEMA,
        )

    @mcp.tool()
    def spatial_plan_composition_iteration(
        ctx: Context,
        composition_plan_json: str = "",
        validation_result_json: str = "",
        screenshot_notes: Optional[List[str]] = None,
        reference_image: str = "",
        nudge_distance: float = 25.0,
        surface_tolerance: float = 15.0,
        clearance_padding: float = 12.0,
        max_iterations: int = 3,
    ) -> str:
        """Plan dry-run corrections from placement validation and viewport notes.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local planner consumes a spatial interior composition plan plus a
        spatial_validate_placement result, then returns reviewed transform
        candidates, surface-probe handoffs, revalidation, and screenshot
        evidence steps. It does not mutate the Unreal Editor scene.

        Example:
            spatial_plan_composition_iteration(validation_result_json="<validate result>")"""
        t0 = time.monotonic()
        inputs = {
            "composition_plan_json": composition_plan_json,
            "validation_result_json": validation_result_json,
            "screenshot_notes": screenshot_notes or [],
            "reference_image": reference_image,
            "nudge_distance": nudge_distance,
            "surface_tolerance": surface_tolerance,
            "clearance_padding": clearance_padding,
            "max_iterations": max_iterations,
        }
        try:
            clean_composition_plan = _composition_plan_from_json(composition_plan_json)
            clean_validation_result = _iteration_validation_from_json(validation_result_json)
            if not clean_validation_result:
                raise ValueError("validation_result_json is required")
            if not isinstance(clean_validation_result.get("validations"), list):
                raise ValueError("validation_result_json.validations or candidate_clearance candidates must be a list")
            clean_screenshot_notes = _string_list(screenshot_notes, "screenshot_notes", maximum=128)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_plan_composition_iteration",
                tool="spatial_plan_composition_iteration",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        safe_nudge_distance = _float_value(nudge_distance, default=25.0, minimum=0.0)
        safe_surface_tolerance = _float_value(surface_tolerance, default=15.0, minimum=0.0)
        safe_clearance_padding = _float_value(clearance_padding, default=12.0, minimum=0.0)
        safe_max_iterations = _bounded_limit(max_iterations, default=3, maximum=10)
        clean_reference_image = str(reference_image or "").strip().replace("\\", "/")
        inputs.update({
            "composition_plan_applied": bool(clean_composition_plan),
            "validation_count": len(clean_validation_result.get("validations", [])),
            "screenshot_notes": clean_screenshot_notes,
            "reference_image": clean_reference_image,
            "nudge_distance": safe_nudge_distance,
            "surface_tolerance": safe_surface_tolerance,
            "clearance_padding": safe_clearance_padding,
            "max_iterations": safe_max_iterations,
        })
        plan = _plan_composition_iteration(
            composition_plan=clean_composition_plan,
            validation_result=clean_validation_result,
            screenshot_notes=clean_screenshot_notes,
            reference_image=clean_reference_image,
            nudge_distance=safe_nudge_distance,
            surface_tolerance=safe_surface_tolerance,
            clearance_padding=safe_clearance_padding,
            max_iterations=safe_max_iterations,
        )
        return _local_result(
            success=True,
            stage="spatial_plan_composition_iteration",
            tool="spatial_plan_composition_iteration",
            message="Planned dry-run composition corrections, revalidation, and viewport evidence steps.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_assess_environment_coherence(
        ctx: Context,
        scene_context_json: str,
        design_intent_json: str,
    ) -> str:
        """Assess whether an environment is spatially and compositionally coherent.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        Example:
            spatial_assess_environment_coherence(composition_plan_json="<plan>", validation_result_json="<validation>")

        The read-only assessment combines revision-bound scene facts with an
        explicit design intent. It checks stable identity/evidence status,
        support, circulation, clearances, landmarks/sightlines, functional
        zones, material families, ecological rules, and physical scale cues.
        Hard failures are never averaged away and inferred facts never become
        observed scene truth.
        """
        t0 = time.monotonic()
        inputs = {
            "scene_context_json_bytes": len(str(scene_context_json or "").encode("utf-8")),
            "design_intent_json_bytes": len(str(design_intent_json or "").encode("utf-8")),
        }
        try:
            if inputs["scene_context_json_bytes"] > 1024 * 1024:
                raise ValueError("scene_context_json exceeds the 1 MiB limit")
            if inputs["design_intent_json_bytes"] > 256 * 1024:
                raise ValueError("design_intent_json exceeds the 256 KiB limit")
            scene_context = _json_object_from_text(scene_context_json, "scene_context_json")
            design_intent = _json_object_from_text(design_intent_json, "design_intent_json")
            if not scene_context:
                raise ValueError("scene_context_json is required")
            if not design_intent:
                raise ValueError("design_intent_json is required")
            assessment = _environment_coherence_assessment(scene_context, design_intent)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_assess_environment_coherence",
                tool="spatial_assess_environment_coherence",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )
        inputs.update({
            "scene_revision": assessment["scene_revision"],
            "gate_count": len(assessment["gates"]),
        })
        return _local_result(
            success=True,
            stage="spatial_assess_environment_coherence",
            tool="spatial_assess_environment_coherence",
            message="Assessed revision-bound environment coherence without granting mutation authority.",
            inputs=inputs,
            outputs=assessment,
            t0=t0,
        )

    @mcp.tool()
    def spatial_compile_worldbuilding_readiness(
        ctx: Context,
        reference_image: str = "",
        room_analysis_json: str = "",
        functional_zone_plan_json: str = "",
        prop_program_json: str = "",
        decomposition_request_json: str = "",
        detection_preflight_json: str = "",
        scene_graph_json: str = "",
        reconstruction_plan_json: str = "",
        composition_plan_json: str = "",
        asset_resolution_json: str = "",
        tripo_batch_json: str = "",
        asset_binding_json: str = "",
        asset_scale_correction_json: str = "",
        support_surface_anchors_json: str = "",
        layout_preflight_json: str = "",
        layout_preflight_correction_json: str = "",
        candidate_clearance_json: str = "",
        apply_result_json: str = "",
        validation_result_json: str = "",
        iteration_plan_json: str = "",
        viewport_evidence_json: str = "",
        require_room_analysis: bool = True,
        require_scene_graph: bool = True,
        require_viewport_evidence: bool = True,
    ) -> str:
        """Compile end-to-end readiness for spatial worldbuilding.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local/read-only compiler consumes any subset of Ghost spatial
        workflow outputs and reports gates, blockers, next actions, and
        viewport evidence handoffs for the room/screenshot reconstruction
        pipeline. It does not mutate Unreal, run vision, or submit paid Tripo
        jobs.

        Example:
            spatial_compile_worldbuilding_readiness(reference_image="C:/refs/apartment.png")"""
        t0 = time.monotonic()
        inputs = {
            "reference_image": reference_image,
            "room_analysis_json": room_analysis_json,
            "functional_zone_plan_json": functional_zone_plan_json,
            "prop_program_json": prop_program_json,
            "decomposition_request_json": decomposition_request_json,
            "detection_preflight_json": detection_preflight_json,
            "scene_graph_json": scene_graph_json,
            "reconstruction_plan_json": reconstruction_plan_json,
            "composition_plan_json": composition_plan_json,
            "asset_resolution_json": asset_resolution_json,
            "tripo_batch_json": tripo_batch_json,
            "asset_binding_json": asset_binding_json,
            "asset_scale_correction_json": asset_scale_correction_json,
            "support_surface_anchors_json": support_surface_anchors_json,
            "layout_preflight_json": layout_preflight_json,
            "layout_preflight_correction_json": layout_preflight_correction_json,
            "candidate_clearance_json": candidate_clearance_json,
            "apply_result_json": apply_result_json,
            "validation_result_json": validation_result_json,
            "iteration_plan_json": iteration_plan_json,
            "viewport_evidence_json": viewport_evidence_json,
            "require_room_analysis": require_room_analysis,
            "require_scene_graph": require_scene_graph,
            "require_viewport_evidence": require_viewport_evidence,
        }
        try:
            clean_reference_image = str(reference_image or "").strip().replace("\\", "/")
            clean_room_analysis = _worldbuilding_outputs_from_json(room_analysis_json, "room_analysis_json", ROOM_ANALYSIS_SCHEMA)
            clean_functional_zone_plan = _worldbuilding_outputs_from_json(functional_zone_plan_json, "functional_zone_plan_json", FUNCTIONAL_ZONE_INFERENCE_SCHEMA)
            clean_prop_program = _prop_program_from_json(prop_program_json)
            clean_decomposition_request = _worldbuilding_outputs_from_json(decomposition_request_json, "decomposition_request_json", SCREENSHOT_DECOMPOSITION_REQUEST_SCHEMA)
            clean_detection_preflight = _worldbuilding_outputs_from_json(detection_preflight_json, "detection_preflight_json", SCREENSHOT_DECOMPOSITION_PREFLIGHT_SCHEMA)
            clean_scene_graph = _worldbuilding_outputs_from_json(scene_graph_json, "scene_graph_json", SCREENSHOT_SCENE_GRAPH_SCHEMA)
            clean_reconstruction_plan = _worldbuilding_outputs_from_json(reconstruction_plan_json, "reconstruction_plan_json", SCREENSHOT_RECONSTRUCTION_SCHEMA)
            clean_composition_plan = _composition_like_from_json(composition_plan_json)
            clean_asset_resolution = _worldbuilding_outputs_from_json(asset_resolution_json, "asset_resolution_json", PROJECT_ASSET_RESOLUTION_SCHEMA)
            clean_tripo_batch = _worldbuilding_outputs_from_json(tripo_batch_json, "tripo_batch_json", TRIPO_GENERATION_BATCH_SCHEMA)
            clean_asset_binding = _worldbuilding_outputs_from_json(asset_binding_json, "asset_binding_json", COMPOSITION_ASSET_BINDING_SCHEMA)
            clean_asset_scale_correction = _worldbuilding_outputs_from_json(asset_scale_correction_json, "asset_scale_correction_json", ASSET_SCALE_CORRECTION_SCHEMA)
            clean_support_surface_anchors = _worldbuilding_outputs_from_json(support_surface_anchors_json, "support_surface_anchors_json", SUPPORT_SURFACE_ANCHOR_SCHEMA)
            clean_layout_preflight = _worldbuilding_outputs_from_json(layout_preflight_json, "layout_preflight_json", LAYOUT_PREFLIGHT_SCHEMA)
            clean_layout_preflight_correction = _worldbuilding_outputs_from_json(layout_preflight_correction_json, "layout_preflight_correction_json", LAYOUT_PREFLIGHT_CORRECTION_SCHEMA)
            clean_candidate_clearance = _worldbuilding_outputs_from_json(candidate_clearance_json, "candidate_clearance_json", CANDIDATE_CLEARANCE_SCHEMA)
            clean_apply_result = _worldbuilding_outputs_from_json(apply_result_json, "apply_result_json", COMPOSITION_PLACEMENT_BATCH_SCHEMA)
            clean_validation_result = _worldbuilding_outputs_from_json(validation_result_json, "validation_result_json", PLACEMENT_VALIDATION_SCHEMA)
            clean_iteration_plan = _worldbuilding_outputs_from_json(iteration_plan_json, "iteration_plan_json", COMPOSITION_ITERATION_SCHEMA)
            clean_viewport_evidence = _json_object_from_text(viewport_evidence_json, "viewport_evidence_json")
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_compile_worldbuilding_readiness",
                tool="spatial_compile_worldbuilding_readiness",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "reference_image": clean_reference_image,
            "room_analysis_applied": bool(clean_room_analysis),
            "functional_zone_plan_applied": bool(clean_functional_zone_plan),
            "prop_program_applied": bool(clean_prop_program),
            "decomposition_request_applied": bool(clean_decomposition_request),
            "detection_preflight_applied": bool(clean_detection_preflight),
            "scene_graph_applied": bool(clean_scene_graph),
            "reconstruction_plan_applied": bool(clean_reconstruction_plan),
            "composition_plan_applied": bool(clean_composition_plan),
            "asset_resolution_applied": bool(clean_asset_resolution),
            "tripo_batch_applied": bool(clean_tripo_batch),
            "asset_binding_applied": bool(clean_asset_binding),
            "asset_scale_correction_applied": bool(clean_asset_scale_correction),
            "support_surface_anchors_applied": bool(clean_support_surface_anchors),
            "layout_preflight_applied": bool(clean_layout_preflight),
            "layout_preflight_correction_applied": bool(clean_layout_preflight_correction),
            "apply_result_applied": bool(clean_apply_result),
            "validation_result_applied": bool(clean_validation_result),
            "iteration_plan_applied": bool(clean_iteration_plan),
            "viewport_evidence_applied": bool(clean_viewport_evidence),
        })
        plan = _plan_worldbuilding_readiness(
            reference_image=clean_reference_image,
            room_analysis=clean_room_analysis,
            functional_zone_plan=clean_functional_zone_plan,
            prop_program=clean_prop_program,
            decomposition_request=clean_decomposition_request,
            detection_preflight=clean_detection_preflight,
            scene_graph=clean_scene_graph,
            reconstruction_plan=clean_reconstruction_plan,
            composition_plan=clean_composition_plan,
            asset_resolution=clean_asset_resolution,
            tripo_batch=clean_tripo_batch,
            asset_binding=clean_asset_binding,
            asset_scale_correction=clean_asset_scale_correction,
            support_surface_anchors=clean_support_surface_anchors,
            layout_preflight=clean_layout_preflight,
            layout_preflight_correction=clean_layout_preflight_correction,
            candidate_clearance=clean_candidate_clearance,
            apply_result=clean_apply_result,
            validation_result=clean_validation_result,
            iteration_plan=clean_iteration_plan,
            viewport_evidence=clean_viewport_evidence,
            require_room_analysis=bool(require_room_analysis),
            require_scene_graph=bool(require_scene_graph),
            require_viewport_evidence=bool(require_viewport_evidence),
        )
        return _local_result(
            success=True,
            stage="spatial_compile_worldbuilding_readiness",
            tool="spatial_compile_worldbuilding_readiness",
            message="Compiled spatial worldbuilding readiness gates and next actions.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_plan_worldbuilding_work_order(
        ctx: Context,
        design_brief: str = "",
        reference_image: str = "",
        room_analysis_json: str = "",
        detected_items_json: str = "",
        scene_graph_json: str = "",
        project_asset_catalog_json: str = "",
        candidate_asset_paths: Optional[List[str]] = None,
        room_type: str = "apartment",
        room_dimensions: Optional[List[float]] = None,
        room_origin: Optional[List[float]] = None,
        style: str = "lived-in realistic",
        requested_zones: Optional[List[str]] = None,
        required_props: Optional[List[str]] = None,
        content_path: str = "/Game/Generated/SpatialInteriors",
        actor_label_prefix: str = "",
        generate_missing_with_tripo: bool = True,
        include_architectural_fill: bool = True,
        max_items: int = 40,
        minimum_asset_score: float = 45.0,
        max_candidates_per_prop: int = 5,
    ) -> str:
        """Plan an executable interior worldbuilding work order.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This local/read-only planner turns a design brief, optional screenshot
        evidence, optional room analysis, and optional project asset catalog
        into a staged Ghost workflow: measure, decompose, plan, resolve assets,
        prepare guarded Tripo generation, bind/apply, validate, and capture
        evidence. It does not run vision, mutate Unreal, or submit paid Tripo
        jobs.

        Example:
            spatial_plan_worldbuilding_work_order(reference_image="C:/refs/apartment.png", design_brief="Rebuild this compact apartment kitchen")"""
        t0 = time.monotonic()
        inputs = {
            "design_brief": design_brief,
            "reference_image": reference_image,
            "room_analysis_json": room_analysis_json,
            "detected_items_json": detected_items_json,
            "scene_graph_json": scene_graph_json,
            "project_asset_catalog_json": project_asset_catalog_json,
            "candidate_asset_paths": candidate_asset_paths or [],
            "room_type": room_type,
            "room_dimensions": room_dimensions or [],
            "room_origin": room_origin or [],
            "style": style,
            "requested_zones": requested_zones or [],
            "required_props": required_props or [],
            "content_path": content_path,
            "actor_label_prefix": actor_label_prefix,
            "generate_missing_with_tripo": generate_missing_with_tripo,
            "include_architectural_fill": include_architectural_fill,
            "max_items": max_items,
            "minimum_asset_score": minimum_asset_score,
            "max_candidates_per_prop": max_candidates_per_prop,
        }
        try:
            safe_max_items = _bounded_limit(max_items, default=40, maximum=100)
            clean_room_analysis = _room_analysis_from_json(room_analysis_json)
            clean_room_type = str(clean_room_analysis.get("room_type") or _clean_room_type(room_type))
            clean_room_dimensions = list(clean_room_analysis.get("room_dimensions") or _room_dimensions(room_dimensions))
            clean_room_origin = list(
                clean_room_analysis.get("room_origin")
                or _vector3(room_origin, "room_origin")
                or [0.0, 0.0, 0.0]
            )
            clean_reference_image = str(reference_image or "").strip().replace("\\", "/")
            clean_detected_items = _detected_items_from_json(detected_items_json, maximum=safe_max_items)
            clean_scene_graph = _worldbuilding_outputs_from_json(scene_graph_json, "scene_graph_json", SCREENSHOT_SCENE_GRAPH_SCHEMA)
            clean_candidate_paths = _string_list(candidate_asset_paths, "candidate_asset_paths", maximum=500)
            clean_asset_catalog: List[Dict[str, Any]] = []
            if str(project_asset_catalog_json or "").strip() or clean_candidate_paths:
                clean_asset_catalog = _asset_catalog_from_json(
                    project_asset_catalog_json,
                    candidate_asset_paths=clean_candidate_paths,
                    maximum=500,
                )
            clean_requested_zones = _string_list(requested_zones, "requested_zones", maximum=16)
            clean_required_props = _string_list(required_props, "required_props", maximum=safe_max_items)
            clean_content_path = _normalize_content_path(content_path)
            clean_design_brief = str(design_brief or "").strip()[:1000]
            clean_style = str(style or "").strip()[:128] or "lived-in realistic"
            safe_minimum_asset_score = _float_value(minimum_asset_score, default=45.0, minimum=0.0)
            safe_max_candidates = _bounded_limit(max_candidates_per_prop, default=5, maximum=20)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_plan_worldbuilding_work_order",
                tool="spatial_plan_worldbuilding_work_order",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "room_analysis_applied": bool(clean_room_analysis),
            "detected_item_count": len(clean_detected_items),
            "scene_graph_applied": bool(clean_scene_graph),
            "asset_catalog_count": len(clean_asset_catalog),
            "room_type": clean_room_type,
            "room_dimensions": clean_room_dimensions,
            "room_origin": clean_room_origin,
            "reference_image": clean_reference_image,
            "requested_zones": clean_requested_zones,
            "required_props": clean_required_props,
            "content_path": clean_content_path,
            "max_items": safe_max_items,
            "minimum_asset_score": safe_minimum_asset_score,
            "max_candidates_per_prop": safe_max_candidates,
        })
        plan = _plan_worldbuilding_work_order(
            design_brief=clean_design_brief,
            reference_image=clean_reference_image,
            room_analysis=clean_room_analysis,
            detected_items=clean_detected_items,
            scene_graph=clean_scene_graph,
            asset_catalog=clean_asset_catalog,
            room_type=clean_room_type,
            room_dimensions=clean_room_dimensions,
            room_origin=clean_room_origin,
            style=clean_style,
            requested_zones=clean_requested_zones,
            required_props=clean_required_props,
            content_path=clean_content_path,
            actor_label_prefix=str(actor_label_prefix or "").strip()[:64],
            generate_missing_with_tripo=bool(generate_missing_with_tripo),
            include_architectural_fill=bool(include_architectural_fill),
            max_items=safe_max_items,
            minimum_asset_score=safe_minimum_asset_score,
            max_candidates_per_prop=safe_max_candidates,
        )
        return _local_result(
            success=True,
            stage="spatial_plan_worldbuilding_work_order",
            tool="spatial_plan_worldbuilding_work_order",
            message="Planned a spatial interior worldbuilding work order with asset, Tripo, placement, validation, and readiness handoffs.",
            inputs=inputs,
            outputs=plan,
            t0=t0,
        )

    @mcp.tool()
    def spatial_content_selection_context(
        ctx: Context,
        limit: int = 50,
        placement_origin: Optional[List[float]] = None,
        placement_spacing: float = 300.0,
        placement_layout: str = "line",
        actor_label_prefix: str = "",
        tags: Optional[List[str]] = None,
        data_layer_names: Optional[List[str]] = None,
    ) -> str:
        """Read selected Content Browser assets and prepare placement handoffs.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This is a read-only bridge from editor asset selection to Ghost's
        dry-run-first spatial placement workflow.

        Example:
            spatial_content_selection_context(placement_layout="grid", tags=["Gameplay_POI"])"""
        t0 = time.monotonic()
        inputs = {
            "limit": limit,
            "placement_origin": placement_origin or [0.0, 0.0, 0.0],
            "placement_spacing": placement_spacing,
            "placement_layout": placement_layout,
            "actor_label_prefix": actor_label_prefix,
            "tags": tags or [],
            "data_layer_names": data_layer_names or [],
        }
        try:
            clean_origin = _vector3(placement_origin, "placement_origin") or [0.0, 0.0, 0.0]
            clean_tags = _string_list(tags, "tags", maximum=64)
            clean_data_layer_names = _string_list(data_layer_names, "data_layer_names", maximum=32)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_content_selection_context",
                tool="spatial_content_selection_context",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        safe_layout = str(placement_layout or "line").strip().lower()
        if safe_layout not in {"line", "grid", "stack"}:
            return _local_result(
                success=False,
                stage="spatial_content_selection_context",
                tool="spatial_content_selection_context",
                message="placement_layout must be one of: line, grid, stack",
                inputs=inputs,
                errors=["placement_layout must be one of: line, grid, stack"],
                t0=t0,
            )
        safe_limit = _bounded_limit(limit, default=50, maximum=500)
        safe_spacing = _float_value(placement_spacing, default=300.0, minimum=0.0)
        inputs.update({
            "limit": safe_limit,
            "placement_origin": clean_origin,
            "placement_spacing": safe_spacing,
            "placement_layout": safe_layout,
            "tags": clean_tags,
            "data_layer_names": clean_data_layer_names,
        })
        code = _content_selection_code(
            limit=safe_limit,
            placement_origin=clean_origin,
            placement_spacing=safe_spacing,
            placement_layout=safe_layout,
            actor_label_prefix=actor_label_prefix,
            tags=clean_tags,
            data_layer_names=clean_data_layer_names,
        )
        result = _exec_structured(code, "spatial_content_selection_context")
        return _json_result(
            "spatial_content_selection_context",
            "spatial_content_selection_context",
            inputs,
            result,
            t0,
            CONTENT_SELECTION_SCHEMA,
        )

    @mcp.tool()
    def spatial_place_selected_assets(
        ctx: Context,
        asset_paths: Optional[List[str]] = None,
        limit: int = 50,
        placement_origin: Optional[List[float]] = None,
        placement_spacing: float = 300.0,
        placement_layout: str = "line",
        actor_label_prefix: str = "",
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
        tags: Optional[List[str]] = None,
        data_layer_names: Optional[List[str]] = None,
        fail_on_missing_data_layer: bool = False,
        dry_run: bool = True,
        allow_mutation: bool = False,
        select_actors: bool = True,
        focus_viewport: bool = False,
    ) -> str:
        """Plan or place selected Content Browser assets as a batch.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        If asset_paths is empty, the tool reads the current Content Browser
        selection. Real placement is transactional and requires allow_mutation.

        Example:
            spatial_place_selected_assets(placement_layout="grid", dry_run=True)"""
        t0 = time.monotonic()
        inputs = {
            "asset_paths": asset_paths or [],
            "limit": limit,
            "placement_origin": placement_origin or [0.0, 0.0, 0.0],
            "placement_spacing": placement_spacing,
            "placement_layout": placement_layout,
            "actor_label_prefix": actor_label_prefix,
            "rotation": rotation or [0.0, 0.0, 0.0],
            "scale": scale or [1.0, 1.0, 1.0],
            "tags": tags or [],
            "data_layer_names": data_layer_names or [],
            "fail_on_missing_data_layer": fail_on_missing_data_layer,
            "dry_run": dry_run,
            "allow_mutation": allow_mutation,
            "select_actors": select_actors,
            "focus_viewport": focus_viewport,
        }
        try:
            clean_origin = _vector3(placement_origin, "placement_origin") or [0.0, 0.0, 0.0]
            clean_rotation = _vector3(rotation, "rotation") or [0.0, 0.0, 0.0]
            clean_scale = _vector3(scale, "scale") or [1.0, 1.0, 1.0]
            clean_tags = _string_list(tags, "tags", maximum=64)
            clean_data_layer_names = _string_list(data_layer_names, "data_layer_names", maximum=32)
            clean_asset_paths = [
                _clean_asset_path(path)
                for path in _string_list(asset_paths, "asset_paths", maximum=128)
            ]
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_place_selected_assets",
                tool="spatial_place_selected_assets",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        safe_layout = str(placement_layout or "line").strip().lower()
        if safe_layout not in {"line", "grid", "stack"}:
            return _local_result(
                success=False,
                stage="spatial_place_selected_assets",
                tool="spatial_place_selected_assets",
                message="placement_layout must be one of: line, grid, stack",
                inputs=inputs,
                errors=["placement_layout must be one of: line, grid, stack"],
                t0=t0,
            )
        safe_limit = _bounded_limit(limit, default=50, maximum=500)
        safe_spacing = _float_value(placement_spacing, default=300.0, minimum=0.0)
        inputs.update({
            "asset_paths": clean_asset_paths,
            "limit": safe_limit,
            "placement_origin": clean_origin,
            "placement_spacing": safe_spacing,
            "placement_layout": safe_layout,
            "rotation": clean_rotation,
            "scale": clean_scale,
            "tags": clean_tags,
            "data_layer_names": clean_data_layer_names,
        })
        plan = {
            "schema": SELECTED_ASSET_PLACEMENT_SCHEMA,
            "will_execute": bool(not dry_run and allow_mutation),
            "dry_run": bool(dry_run),
            "mutation_required": True,
            "transactional": bool(not dry_run and allow_mutation),
            "asset_source": "explicit_asset_paths" if clean_asset_paths else "content_browser_selection",
            "asset_paths": clean_asset_paths,
            "placement_layout": safe_layout,
            "placement_origin": clean_origin,
            "placement_spacing": safe_spacing,
            "rotation": clean_rotation,
            "scale": clean_scale,
            "tags": clean_tags,
            "data_layer_names": clean_data_layer_names,
            "fail_on_missing_data_layer": bool(fail_on_missing_data_layer),
            "select_actors": bool(select_actors),
            "focus_viewport": bool(focus_viewport),
        }
        if not dry_run and not allow_mutation:
            return _local_result(
                success=False,
                stage="spatial_place_selected_assets",
                tool="spatial_place_selected_assets",
                message="spatial_place_selected_assets is an editor mutation; pass allow_mutation=True to execute it.",
                inputs=inputs,
                outputs=plan,
                errors=["allow_mutation=True is required when dry_run=False"],
                t0=t0,
            )

        code = _selected_asset_placement_code(
            asset_paths=clean_asset_paths,
            limit=safe_limit,
            placement_origin=clean_origin,
            placement_spacing=safe_spacing,
            placement_layout=safe_layout,
            actor_label_prefix=actor_label_prefix,
            rotation=clean_rotation,
            scale=clean_scale,
            tags=clean_tags,
            data_layer_names=clean_data_layer_names,
            fail_on_missing_data_layer=fail_on_missing_data_layer,
            execute=bool(not dry_run and allow_mutation),
            select_actors=select_actors,
            focus_viewport=focus_viewport,
        )
        if dry_run:
            result = _exec_structured(code, "spatial_place_selected_assets")
        else:
            result = _exec_transactional(code, "MCP Spatial Place Selected Assets")
        return _json_result(
            "spatial_place_selected_assets",
            "spatial_place_selected_assets",
            inputs,
            result,
            t0,
            SELECTED_ASSET_PLACEMENT_SCHEMA,
        )

    @mcp.tool()
    def spatial_select_actors(
        ctx: Context,
        actors: Optional[List[str]] = None,
        query: str = "",
        class_filter: str = "",
        tag_filter: str = "",
        center: Optional[List[float]] = None,
        radius: float = 0.0,
        box_min: Optional[List[float]] = None,
        box_max: Optional[List[float]] = None,
        include_hidden: bool = False,
        limit: int = 100,
        selection_mode: str = "replace",
        allow_empty_selection: bool = False,
        focus_viewport: bool = False,
        focus_distance: float = 1200.0,
        dry_run: bool = True,
        allow_mutation: bool = False,
    ) -> str:
        """Resolve actors by spatial filters and optionally select/focus them.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        Dry-run mode executes a read-only actor resolution pass. Editor selection
        and viewport focus require dry_run=false and allow_mutation=true.

        Example:
            spatial_select_actors(query="Market", tag_filter="Gameplay_POI", dry_run=True)"""
        t0 = time.monotonic()
        inputs = {
            "actors": actors or [],
            "query": query,
            "class_filter": class_filter,
            "tag_filter": tag_filter,
            "center": center,
            "radius": radius,
            "box_min": box_min,
            "box_max": box_max,
            "include_hidden": include_hidden,
            "limit": limit,
            "selection_mode": selection_mode,
            "allow_empty_selection": allow_empty_selection,
            "focus_viewport": focus_viewport,
            "focus_distance": focus_distance,
            "dry_run": dry_run,
            "allow_mutation": allow_mutation,
        }
        try:
            clean_actors = _string_list(actors, "actors", maximum=128)
            clean_center = _vector3(center, "center")
            clean_box_min = _vector3(box_min, "box_min")
            clean_box_max = _vector3(box_max, "box_max")
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_select_actors",
                tool="spatial_select_actors",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        safe_limit = _bounded_limit(limit, default=100, maximum=1000)
        safe_radius = _float_value(radius, default=0.0, minimum=0.0)
        safe_focus_distance = _float_value(focus_distance, default=1200.0, minimum=1.0)
        safe_selection_mode = str(selection_mode or "replace").strip().lower()
        if safe_selection_mode not in {"replace", "add", "remove"}:
            return _local_result(
                success=False,
                stage="spatial_select_actors",
                tool="spatial_select_actors",
                message="selection_mode must be one of: replace, add, remove",
                inputs=inputs,
                errors=["selection_mode must be one of: replace, add, remove"],
                t0=t0,
            )

        inputs.update({
            "actors": clean_actors,
            "center": clean_center,
            "radius": safe_radius,
            "box_min": clean_box_min,
            "box_max": clean_box_max,
            "limit": safe_limit,
            "selection_mode": safe_selection_mode,
            "focus_distance": safe_focus_distance,
        })
        plan = {
            "schema": ACTOR_SELECTION_SCHEMA,
            "will_execute": bool(not dry_run and allow_mutation),
            "dry_run": bool(dry_run),
            "mutation_required": True,
            "transactional": bool(not dry_run and allow_mutation),
            "selection_mode": safe_selection_mode,
            "actors": clean_actors,
            "filters": {
                "query": str(query or "").strip(),
                "class_filter": str(class_filter or "").strip(),
                "tag_filter": str(tag_filter or "").strip(),
                "include_hidden": bool(include_hidden),
                "center": clean_center,
                "radius": safe_radius,
                "box_min": clean_box_min,
                "box_max": clean_box_max,
                "limit": safe_limit,
            },
            "focus_viewport": bool(focus_viewport),
            "focus_distance": safe_focus_distance,
            "evidence_follow_up": ["focus_viewport", "viewport_capture_screenshot"],
        }

        if not dry_run and not allow_mutation:
            return _local_result(
                success=False,
                stage="spatial_select_actors",
                tool="spatial_select_actors",
                message="spatial_select_actors changes editor selection; pass allow_mutation=True to execute it.",
                inputs=inputs,
                outputs=plan,
                errors=["allow_mutation=True is required when dry_run=False"],
                t0=t0,
            )

        code = _actor_selection_code(
            actors=clean_actors,
            query=query,
            class_filter=class_filter,
            tag_filter=tag_filter,
            center=clean_center,
            radius=safe_radius,
            box_min=clean_box_min,
            box_max=clean_box_max,
            include_hidden=include_hidden,
            limit=safe_limit,
            apply_selection=bool(not dry_run and allow_mutation),
            selection_mode=safe_selection_mode,
            allow_empty_selection=allow_empty_selection,
            focus_viewport=focus_viewport,
            focus_distance=safe_focus_distance,
        )
        if dry_run:
            result = _exec_structured(code, "spatial_select_actors")
        else:
            result = _exec_transactional(code, "MCP Spatial Select Actors")
        return _json_result("spatial_select_actors", "spatial_select_actors", inputs, result, t0, ACTOR_SELECTION_SCHEMA)

    @mcp.tool()
    def spatial_add_asset_to_scene(
        ctx: Context,
        asset_path: str,
        actor_label: str = "",
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
        tags: Optional[List[str]] = None,
        data_layer_names: Optional[List[str]] = None,
        fail_on_missing_data_layer: bool = False,
        dry_run: bool = True,
        allow_mutation: bool = False,
        select_actor: bool = True,
        focus_viewport: bool = False,
    ) -> str:
        """Plan or place one asset into the current level using Unreal Python.

        KB: see knowledge_base/10_WORLD_BUILDING.md#9-world-building-best-practices

        This is a clean-room scene-placement bridge inspired by Ghost's spatial
        awareness gap. It is dry-run by default and requires allow_mutation=true
        before changing the editor scene.

        Example:
            spatial_add_asset_to_scene(
                asset_path="/Game/Props/SM_Table.SM_Table",
                tags=["Gameplay_POI"],
                data_layer_names=["Gameplay_POIs"],
                dry_run=True,
            )"""
        t0 = time.monotonic()
        inputs = {
            "asset_path": asset_path,
            "actor_label": actor_label,
            "location": location or [0.0, 0.0, 0.0],
            "rotation": rotation or [0.0, 0.0, 0.0],
            "scale": scale or [1.0, 1.0, 1.0],
            "tags": tags or [],
            "data_layer_names": data_layer_names or [],
            "fail_on_missing_data_layer": fail_on_missing_data_layer,
            "dry_run": dry_run,
            "allow_mutation": allow_mutation,
            "select_actor": select_actor,
            "focus_viewport": focus_viewport,
        }
        try:
            clean_asset_path = _clean_asset_path(asset_path)
            clean_location = _vector3(location, "location") or [0.0, 0.0, 0.0]
            clean_rotation = _vector3(rotation, "rotation") or [0.0, 0.0, 0.0]
            clean_scale = _vector3(scale, "scale") or [1.0, 1.0, 1.0]
            clean_tags = _string_list(tags, "tags", maximum=64)
            clean_data_layer_names = _string_list(data_layer_names, "data_layer_names", maximum=32)
        except ValueError as exc:
            return _local_result(
                success=False,
                stage="spatial_add_asset_to_scene",
                tool="spatial_add_asset_to_scene",
                message=str(exc),
                inputs=inputs,
                errors=[str(exc)],
                t0=t0,
            )

        inputs.update({
            "asset_path": clean_asset_path,
            "location": clean_location,
            "rotation": clean_rotation,
            "scale": clean_scale,
            "tags": clean_tags,
            "data_layer_names": clean_data_layer_names,
        })
        plan = {
            "schema": ASSET_PLACEMENT_SCHEMA,
            "will_execute": bool(not dry_run and allow_mutation),
            "dry_run": bool(dry_run),
            "mutation_required": True,
            "transactional": True,
            "asset_path": clean_asset_path,
            "actor_label": str(actor_label or "").strip(),
            "tags": clean_tags,
            "data_layer_names": clean_data_layer_names,
            "fail_on_missing_data_layer": bool(fail_on_missing_data_layer),
            "transform": {
                "location": clean_location,
                "rotation": clean_rotation,
                "scale": clean_scale,
            },
            "world_partition": {
                "data_layer_assignment_requested": bool(clean_data_layer_names),
                "best_effort_unless_fail_on_missing_data_layer": not bool(fail_on_missing_data_layer),
            },
            "execution_path": "Ghost exec_python transactional substrate using public Unreal Python editor APIs",
        }
        if dry_run:
            return _local_result(
                success=True,
                stage="spatial_add_asset_to_scene",
                tool="spatial_add_asset_to_scene",
                message="Dry run only; pass dry_run=False and allow_mutation=True to place the asset.",
                inputs=inputs,
                outputs=plan,
                t0=t0,
            )
        if not allow_mutation:
            return _local_result(
                success=False,
                stage="spatial_add_asset_to_scene",
                tool="spatial_add_asset_to_scene",
                message="spatial_add_asset_to_scene is an editor mutation; pass allow_mutation=True to execute it.",
                inputs=inputs,
                outputs=plan,
                errors=["allow_mutation=True is required when dry_run=False"],
                t0=t0,
            )

        code = _asset_placement_code(
            asset_path=clean_asset_path,
            actor_label=actor_label,
            location=clean_location,
            rotation=clean_rotation,
            scale=clean_scale,
            tags=clean_tags,
            data_layer_names=clean_data_layer_names,
            fail_on_missing_data_layer=fail_on_missing_data_layer,
            select_actor=select_actor,
            focus_viewport=focus_viewport,
        )
        result = _exec_transactional(code, "MCP Spatial Add Asset To Scene")
        return _json_result("spatial_add_asset_to_scene", "spatial_add_asset_to_scene", inputs, result, t0, ASSET_PLACEMENT_SCHEMA)

    logger.info("Spatial awareness tools registered successfully")
