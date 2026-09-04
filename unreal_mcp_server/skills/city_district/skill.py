"""City/district generation planning skill for native Unreal workflow alignment."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

CITY_DISTRICT_SCHEMA = "unreal_mcp_ghost.city_district_plan.v1"
VALID_MODES = {"plan", "queue"}


def _safe_name(value: str, default: str = "CityDistrict") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", (value or "").strip()).strip("_")
    if not cleaned:
        cleaned = default
    if cleaned[0].isdigit():
        cleaned = f"{default}_{cleaned}"
    return cleaned[:64]


def _content_root(value: str) -> str:
    root = (value or "/Game/Generated/CityDistrict").strip().replace("\\", "/").rstrip("/")
    while "//" in root:
        root = root.replace("//", "/")
    if not root.startswith("/Game"):
        root = "/Game/Generated/CityDistrict"
    return root


def _density_profile(density: str) -> Dict[str, Any]:
    profiles = {
        "low": {"lots_per_block": 2, "pcg_density_scalar": 0.45, "floor_range": [1, 4], "traffic_density": "light"},
        "medium": {"lots_per_block": 4, "pcg_density_scalar": 0.75, "floor_range": [2, 8], "traffic_density": "moderate"},
        "high": {"lots_per_block": 6, "pcg_density_scalar": 1.0, "floor_range": [4, 18], "traffic_density": "busy"},
        "vertical": {"lots_per_block": 5, "pcg_density_scalar": 1.2, "floor_range": [10, 42], "traffic_density": "busy"},
    }
    return dict(profiles.get((density or "medium").strip().lower(), profiles["medium"]))


def _tool_step(
    *,
    phase: str,
    tool: str,
    purpose: str,
    arguments: Optional[Dict[str, Any]] = None,
    mutates_editor: bool = False,
    evidence: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "phase": phase,
        "tool": tool,
        "purpose": purpose,
        "arguments": arguments or {},
        "mutates_editor": mutates_editor,
        "evidence": evidence or [],
    }


def build_city_district_plan(
    *,
    brief: str,
    district_name: str = "MCP_CityDistrict",
    content_path: str = "/Game/Generated/CityDistrict",
    size_blocks: int = 4,
    block_size: float = 1000.0,
    density: str = "medium",
    style: str = "modern",
    use_pcg: bool = True,
    include_world_partition: bool = True,
    include_hlod: bool = True,
    include_mass_traffic: bool = False,
) -> Dict[str, Any]:
    safe_name = _safe_name(district_name)
    root = _content_root(content_path)
    blocks = max(1, min(int(size_blocks or 1), 24))
    spacing = max(100.0, float(block_size or 1000.0))
    half_extent = (blocks * spacing) / 2.0
    profile = _density_profile(density)
    graph_path = f"{root}/PCG/PCG_{safe_name}"
    data_layer_name = f"DL_{safe_name}"
    pcg_volume_label = f"PCG_{safe_name}_Volume"
    hlod_layer_path = f"{root}/HLOD/HLODLayer_{safe_name}"

    district_descriptor = {
        "name": safe_name,
        "brief": brief,
        "style": style,
        "density": density,
        "blocks_per_side": blocks,
        "block_size_cm": spacing,
        "extent_cm": [blocks * spacing, blocks * spacing, 4000.0],
        "road_grid": {
            "avenue_count": blocks + 1,
            "street_count": blocks + 1,
            "primary_road_width_cm": max(800.0, spacing * 0.12),
            "secondary_road_width_cm": max(500.0, spacing * 0.08),
        },
        "lots": {
            "estimated_lot_count": blocks * blocks * int(profile["lots_per_block"]),
            "lots_per_block": profile["lots_per_block"],
            "floor_range": profile["floor_range"],
            "pcg_density_scalar": profile["pcg_density_scalar"],
        },
        "zones": [
            {"name": "commercial_core", "weight": 0.25},
            {"name": "residential_blocks", "weight": 0.45},
            {"name": "civic_or_landmark", "weight": 0.10},
            {"name": "industrial_or_service", "weight": 0.10},
            {"name": "parks_and_plazas", "weight": 0.10},
        ],
        "assets": {
            "pcg_graph": graph_path,
            "pcg_volume_label": pcg_volume_label,
            "data_layer": data_layer_name,
            "hlod_layer": hlod_layer_path,
            "road_spline_blueprint": f"{root}/Blueprints/BP_{safe_name}_RoadSpline",
            "building_ism_blueprint": f"{root}/Blueprints/BP_{safe_name}_BuildingBlockout",
        },
    }

    tool_sequence: List[Dict[str, Any]] = [
        _tool_step(
            phase="orient",
            tool="get_project_context",
            purpose="Confirm project/map context before mutating world assets.",
            evidence=["project name", "current map"],
        )
    ]
    if use_pcg:
        tool_sequence.append(_tool_step(
            phase="pcg_preflight",
            tool="pcg_check_support",
            purpose="Verify that Unreal Python exposes PCG classes in this editor session.",
            evidence=["available_classes.PCGGraph", "available_classes.PCGVolume"],
        ))
    if include_world_partition:
        tool_sequence.extend([
            _tool_step(
                phase="streaming_setup",
                tool="wp_load_region",
                purpose="Load the edit window that will contain the generated district.",
                arguments={"center": [0.0, 0.0, 0.0], "extent": [half_extent, half_extent, 50000.0], "label": f"{safe_name} Edit Region"},
                mutates_editor=True,
                evidence=["region loader actor", "loaded editor cells"],
            ),
            _tool_step(
                phase="streaming_setup",
                tool="wp_create_data_layer",
                purpose="Create or reuse a Data Layer for district actors.",
                arguments={"name": data_layer_name, "type": "runtime", "asset_path": f"{root}/DataLayers/{data_layer_name}", "initial_runtime_state": "loaded"},
                mutates_editor=True,
                evidence=["data layer asset path", "data layer instance"],
            ),
        ])
    if use_pcg:
        tool_sequence.extend([
            _tool_step(
                phase="pcg_assets",
                tool="pcg_create_graph_asset",
                purpose="Create the district PCG graph asset shell for later node authoring.",
                arguments={"graph_path": graph_path, "overwrite": False, "save": True},
                mutates_editor=True,
                evidence=["pcg graph asset path"],
            ),
            _tool_step(
                phase="pcg_assets",
                tool="pcg_create_volume",
                purpose="Place a PCG volume sized for the district and assign the graph when possible.",
                arguments={
                    "actor_label": pcg_volume_label,
                    "graph_path": graph_path,
                    "location": [0.0, 0.0, 0.0],
                    "scale": [max(1.0, half_extent / 100.0), max(1.0, half_extent / 100.0), 8.0],
                    "generate": False,
                },
                mutates_editor=True,
                evidence=["pcg volume actor", "graph assignment attempts"],
            ),
        ])

    tool_sequence.extend([
        _tool_step(
            phase="blueprint_blockout",
            tool="create_spline_placement_blueprint",
            purpose="Create a Blueprint spline primitive for roads and path-guided props.",
            arguments={
                "name": f"BP_{safe_name}_RoadSpline",
                "static_mesh_path": "/Engine/BasicShapes/Cube",
                "default_space_between_instances": spacing,
                "folder_path": f"{root}/Blueprints",
            },
            mutates_editor=True,
            evidence=["road spline Blueprint"],
        ),
        _tool_step(
            phase="blueprint_blockout",
            tool="create_procedural_mesh_blueprint",
            purpose="Create an ISM blockout Blueprint for repeated building lots while PCG graph authoring matures.",
            arguments={
                "name": f"BP_{safe_name}_BuildingBlockout",
                "static_mesh_path": "/Engine/BasicShapes/Cube",
                "default_instances_per_row": blocks,
                "default_number_of_rows": blocks,
                "default_space_between_instances": spacing,
                "default_space_between_rows": spacing,
                "folder_path": f"{root}/Blueprints",
            },
            mutates_editor=True,
            evidence=["building blockout Blueprint"],
        ),
    ])

    if include_mass_traffic:
        tool_sequence.extend([
            _tool_step(
                phase="agents_and_traffic",
                tool="mass_create_entity_config",
                purpose="Create an initial MassEntity config for crowd/traffic agents.",
                arguments={"name": f"EC_{safe_name}_CrowdAgent", "path": f"{root}/Mass/EntityConfigs"},
                mutates_editor=True,
                evidence=["MassEntity config asset"],
            ),
            _tool_step(
                phase="agents_and_traffic",
                tool="smartobject_create_definition",
                purpose="Seed SmartObject definitions for intersections, benches, doors, and service points.",
                arguments={"name": f"SO_{safe_name}_DistrictSlot", "path": f"{root}/AI/SmartObjects"},
                mutates_editor=True,
                evidence=["SmartObject definition asset"],
            ),
        ])

    if include_hlod:
        tool_sequence.extend([
            _tool_step(
                phase="streaming_optimization",
                tool="hlod_assign_layer",
                purpose="Assign generated actors to an HLOD layer once actors exist.",
                arguments={"hlod_layer": hlod_layer_path, "actors": []},
                mutates_editor=True,
                evidence=["HLOD layer assignment report"],
            ),
            _tool_step(
                phase="streaming_optimization",
                tool="hlod_generate",
                purpose="Run or dry-run World Partition HLOD generation after layout is stable.",
                arguments={"setup": True, "build": True, "report_only": True, "layer": hlod_layer_path},
                mutates_editor=False,
                evidence=["HLOD commandlet report"],
            ),
        ])

    tool_sequence.extend([
        _tool_step(
            phase="visual_validation",
            tool="take_screenshot",
            purpose="Capture a viewport screenshot for city layout evidence.",
            arguments={"filename": f"{safe_name}_district_layout.png", "show_ui": False, "resolution": [1920, 1080]},
            evidence=["viewport screenshot"],
        ),
        _tool_step(
            phase="visual_validation",
            tool="viewport_capture_screenshot",
            purpose="Capture a workspace-local screenshot artifact when the execution substrate is available.",
            arguments={"artifact_name": f"{safe_name}_district_layout"},
            evidence=["workspace screenshot artifact", "image dimensions", "sha256"],
        ),
    ])

    validation_gates = [
        "PCG support check proves PCGGraph and PCGVolume are exposed before PCG mutation.",
        "World Partition edit region is loaded before placing district actors.",
        "Data Layer exists and generated actors are assigned or queued for assignment.",
        "PCG graph asset exists and the PCG volume reports graph assignment attempts.",
        "Blueprint blockout compiles and provides fallback city geometry before deeper PCG graph node authoring.",
        "HLOD report is captured before committing to full build output.",
        "Viewport screenshot evidence shows non-empty district layout.",
        "PIE or simulate pass validates collision, navigation, and frame-time budget before city scale is increased.",
    ]

    future_native_requirements = [
        "Native or bridge-backed PCG graph node authoring for samplers, filters, static mesh spawners, actor spawners, and exclusion volumes.",
        "MassTraffic-specific lane, zone graph, signal, and vehicle/pedestrian spawning wrappers.",
        "Actor/Data Layer assignment automation after PCG or Blueprint generation creates concrete actors.",
        "Streaming proof across multiple World Partition cells with HLOD and memory/performance evidence.",
        "A city grammar asset format that maps neighborhoods, roads, parcels, landmarks, and rules to reproducible PCG graphs.",
    ]
    if include_mass_traffic:
        future_native_requirements.append("Mass traffic is only scaffolded here; production traffic needs ZoneGraph/MassTraffic wrappers and runtime validation.")

    return {
        "schema": CITY_DISTRICT_SCHEMA,
        "capability_level": "native_workflow_scaffold",
        "district_descriptor": district_descriptor,
        "tool_sequence": tool_sequence,
        "validation_gates": validation_gates,
        "future_native_requirements": future_native_requirements,
        "limits": [
            "This plan does not equal Unreal's full native city/sample generation stack by itself.",
            "PCG graph shells and volumes are available now; rich PCG node graph authoring still needs deeper native integration.",
            "World Partition/Data Layer/HLOD wrappers exist, but actor assignment and streaming validation must be executed and evidenced per project.",
        ],
    }


def _structured(
    *,
    success: bool,
    stage: str,
    message: str,
    inputs: Dict[str, Any],
    t0: float,
    outputs: Optional[Dict[str, Any]] = None,
    warnings: Optional[List[str]] = None,
    errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "success": success,
        "stage": stage,
        "message": message,
        "inputs": inputs,
        "outputs": outputs or {},
        "warnings": warnings or [],
        "errors": errors or [],
        "log_tail": [],
        "meta": {"tool": "skill_generate_city_district", "duration_ms": int((time.monotonic() - t0) * 1000)},
    }


def skill_generate_city_district(
    brief: str,
    mode: str = "plan",
    district_name: str = "MCP_CityDistrict",
    content_path: str = "/Game/Generated/CityDistrict",
    size_blocks: int = 4,
    block_size: float = 1000.0,
    density: str = "medium",
    style: str = "modern",
    use_pcg: bool = True,
    include_world_partition: bool = True,
    include_hlod: bool = True,
    include_mass_traffic: bool = False,
) -> Dict[str, Any]:
    """Plan a native-aligned city/district generation workflow without executing it."""

    t0 = time.monotonic()
    safe_mode = (mode or "plan").strip().lower()
    inputs = {
        "brief": brief,
        "mode": safe_mode,
        "district_name": district_name,
        "content_path": content_path,
        "size_blocks": size_blocks,
        "block_size": block_size,
        "density": density,
        "style": style,
        "use_pcg": use_pcg,
        "include_world_partition": include_world_partition,
        "include_hlod": include_hlod,
        "include_mass_traffic": include_mass_traffic,
    }
    if safe_mode not in VALID_MODES:
        return _structured(
            success=False,
            stage="invalid_mode",
            message="mode must be one of: plan, queue",
            inputs=inputs,
            errors=["mode must be one of: plan, queue"],
            t0=t0,
        )
    if not str(brief or "").strip():
        return _structured(
            success=False,
            stage="invalid_brief",
            message="brief is required",
            inputs=inputs,
            errors=["brief is required"],
            t0=t0,
        )

    plan = build_city_district_plan(
        brief=brief,
        district_name=district_name,
        content_path=content_path,
        size_blocks=size_blocks,
        block_size=block_size,
        density=density,
        style=style,
        use_pcg=use_pcg,
        include_world_partition=include_world_partition,
        include_hlod=include_hlod,
        include_mass_traffic=include_mass_traffic,
    )
    warnings = [
        "This is a native-aligned city/district workflow scaffold, not a full production city generator yet.",
        "Execute the tool sequence only after project/map context and backup policy are clear.",
    ]
    if include_mass_traffic:
        warnings.append("Mass/traffic support is scaffolded through existing Mass and SmartObject tools; ZoneGraph and MassTraffic wrappers still need deeper integration.")
    if not use_pcg:
        warnings.append("PCG was disabled, so the plan falls back to Blueprint/ISM blockout workflows.")

    outputs: Dict[str, Any] = {"plan": plan}
    if safe_mode == "queue":
        outputs["queue"] = {
            "schema": "unreal_mcp_ghost.city_district_tool_queue.v1",
            "status": "not_executed",
            "tool_count": len(plan["tool_sequence"]),
            "steps": plan["tool_sequence"],
        }

    return _structured(
        success=True,
        stage="plan_ready" if safe_mode == "plan" else "queue_ready",
        message="City/district workflow compiled; no Unreal mutation was executed.",
        inputs=inputs,
        outputs=outputs,
        warnings=warnings,
        t0=t0,
    )


def register_city_district_skill(mcp: FastMCP) -> None:
    impl = globals()["skill_generate_city_district"]

    @mcp.tool()
    async def skill_generate_city_district(
        ctx: Context,
        brief: str,
        mode: str = "plan",
        district_name: str = "MCP_CityDistrict",
        content_path: str = "/Game/Generated/CityDistrict",
        size_blocks: int = 4,
        block_size: float = 1000.0,
        density: str = "medium",
        style: str = "modern",
        use_pcg: bool = True,
        include_world_partition: bool = True,
        include_hlod: bool = True,
        include_mass_traffic: bool = False,
    ) -> str:
        """Plan a native-aligned city/district generation workflow.

        Mode `plan` returns a no-mutation plan. Mode `queue` also returns a
        structured, not-yet-executed tool queue. The skill composes PCG,
        World Partition, Data Layer, HLOD, Blueprint blockout, screenshot, and
        optional Mass/SmartObject steps while calling out deeper native gaps.

        KB: see knowledge_base/10_WORLD_BUILDING.md#4-procedural-content-generation-pcg
        Example:
            skill_generate_city_district(brief="walkable sci-fi downtown district", mode="plan")"""
        result = impl(
            brief=brief,
            mode=mode,
            district_name=district_name,
            content_path=content_path,
            size_blocks=size_blocks,
            block_size=block_size,
            density=density,
            style=style,
            use_pcg=use_pcg,
            include_world_partition=include_world_partition,
            include_hlod=include_hlod,
            include_mass_traffic=include_mass_traffic,
        )
        return json.dumps(result, indent=2, sort_keys=True)
