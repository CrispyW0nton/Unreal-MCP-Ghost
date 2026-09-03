from __future__ import annotations

import ast
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from tools import spatial_awareness_tools  # noqa: E402


class FakeMCP:
    def __init__(self) -> None:
        self.tools: dict[str, Any] = {}

    def tool(self, *args: Any, **kwargs: Any) -> Any:
        name = kwargs.get("name")

        if len(args) == 1 and callable(args[0]) and not kwargs:
            fn = args[0]
            self.tools[getattr(fn, "__name__", "")] = fn
            return fn

        def decorator(fn: Any) -> Any:
            self.tools[name or getattr(fn, "__name__", "")] = fn
            return fn

        return decorator


class TestSpatialAwarenessTools(unittest.TestCase):
    def test_registers_spatial_tools(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        self.assertEqual(
            set(mcp.tools),
            {
                "spatial_scene_overview",
                "spatial_query_actors",
                "spatial_describe_actor",
                "spatial_proximity_map",
                "spatial_view_context",
                "spatial_analyze_room",
                "spatial_plan_room_bounds_designation",
                "spatial_infer_functional_zones",
                "spatial_plan_interior_prop_program",
                "spatial_surface_probe",
                "spatial_validate_placement",
                "spatial_infer_placement_policy",
                "spatial_plan_interior_composition",
                "spatial_prepare_screenshot_decomposition_request",
                "spatial_preflight_screenshot_detections",
                "spatial_infer_screenshot_scene_graph",
                "spatial_prepare_screenshot_crop_manifest",
                "spatial_plan_screenshot_reconstruction",
                "spatial_catalog_project_assets",
                "spatial_resolve_project_assets",
                "spatial_prepare_tripo_generation_batch",
                "spatial_bind_generated_assets_to_composition",
                "spatial_plan_asset_scale_corrections",
                "spatial_plan_support_surface_anchors",
                "spatial_apply_composition_plan",
                "spatial_preflight_interior_layout",
                "spatial_plan_layout_preflight_corrections",
                "spatial_preflight_candidate_clearance",
                "spatial_plan_composition_iteration",
                "spatial_assess_environment_coherence",
                "spatial_compile_worldbuilding_readiness",
                "spatial_plan_worldbuilding_work_order",
                "spatial_content_selection_context",
                "spatial_place_selected_assets",
                "spatial_select_actors",
                "spatial_add_asset_to_scene",
            },
        )

    def test_scene_overview_returns_structured_json(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {"actor_count": 3},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_scene_overview"](ctx=None, class_filter="StaticMeshActor"))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["schema"], spatial_awareness_tools.SPATIAL_RESULT_SCHEMA)
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.SCENE_OVERVIEW_SCHEMA)
        self.assertEqual(calls[0][1], "spatial_scene_overview")
        self.assertIn("EditorActorSubsystem", calls[0][0])
        self.assertIn("get_actor_bounds", calls[0][0])
        self.assertIn("class_histogram", calls[0][0])

    def test_scene_overview_declares_content_scopes_and_local_ambiguity_refusal(self) -> None:
        code = spatial_awareness_tools._scene_overview_code(
            include_hidden=False,
            class_filter="",
            tag_filter="",
            limit=25,
            include_actor_samples=False,
        )

        self.assertEqual(
            spatial_awareness_tools.SCENE_OVERVIEW_SCHEMA,
            "unreal_mcp_ghost.spatial_scene_overview.v2",
        )
        self.assertIn("bounds_scopes", code)
        self.assertIn("physical_content", code)
        self.assertIn("selected_physical_content", code)
        self.assertIn("authored_room_candidates", code)
        self.assertIn("local_bounds_resolution", code)
        self.assertIn("needs_explicit_local_scope", code)
        self.assertIn("WorldPartitionMiniMap", code)
        self.assertIn("observed_native_component_and_class_metadata", code)
        self.assertIn("unreal_mcp_ghost.physical_content_classification.v1", code)

    def test_scene_overview_executes_physical_bounds_and_local_scope_precedence(self) -> None:
        class FakeVector:
            def __init__(self, x: float, y: float, z: float) -> None:
                self.x = x
                self.y = y
                self.z = z

        class FakeRotation:
            pitch = 0.0
            yaw = 0.0
            roll = 0.0

        class FakeClass:
            def __init__(self, name: str) -> None:
                self._name = name

            def get_name(self) -> str:
                return self._name

        class FakeComponent:
            def __init__(self, class_name: str, asset_path: str = "") -> None:
                self._class = FakeClass(class_name)
                self._asset_path = asset_path

            def get_class(self) -> FakeClass:
                return self._class

            def get_editor_property(self, property_name: str) -> object:
                if property_name != "static_mesh" or not self._asset_path:
                    raise AttributeError(property_name)
                return types.SimpleNamespace(get_path_name=lambda: self._asset_path)

        class FakeActor:
            def __init__(
                self,
                label: str,
                class_name: str,
                origin: tuple[float, float, float],
                extent: tuple[float, float, float],
                *,
                components: tuple[str | tuple[str, str], ...] = (),
                tags: tuple[str, ...] = (),
            ) -> None:
                self._label = label
                self._class = FakeClass(class_name)
                self._origin = FakeVector(*origin)
                self._extent = FakeVector(*extent)
                self._components = [
                    FakeComponent(spec[0], spec[1])
                    if isinstance(spec, tuple)
                    else FakeComponent(spec)
                    for spec in components
                ]
                self.tags = list(tags)

            def get_actor_bounds(self, *_args: object) -> tuple[FakeVector, FakeVector]:
                return self._origin, self._extent

            def get_actor_label(self) -> str:
                return self._label

            def get_name(self) -> str:
                return self._label

            def get_path_name(self) -> str:
                return f"/Game/Test.{self._label}"

            def get_class(self) -> FakeClass:
                return self._class

            def get_components_by_class(self, _component_type: object) -> list[FakeComponent]:
                return list(self._components)

            def get_actor_location(self) -> FakeVector:
                return self._origin

            def get_actor_rotation(self) -> FakeRotation:
                return FakeRotation()

            def get_actor_scale3d(self) -> FakeVector:
                return FakeVector(1.0, 1.0, 1.0)

        class FakeSubsystem:
            def __init__(self, actors: list[FakeActor], selected: list[FakeActor]) -> None:
                self.actors = actors
                self.selected = selected

            def get_all_level_actors(self) -> list[FakeActor]:
                return list(self.actors)

            def get_selected_level_actors(self) -> list[FakeActor]:
                return list(self.selected)

        mesh = FakeActor(
            "EnclaveWall",
            "StaticMeshActor",
            (100.0, 200.0, 300.0),
            (50.0, 60.0, 70.0),
            components=("StaticMeshComponent",),
        )
        partition = FakeActor(
            "WorldPartitionMiniMap",
            "WorldPartitionMiniMap",
            (0.0, 0.0, 0.0),
            (1_638_400.0, 1_638_400.0, 1_638_400.0),
        )
        light = FakeActor(
            "FillLight",
            "PointLight",
            (0.0, 0.0, 0.0),
            (100_000.0, 100_000.0, 100_000.0),
        )
        sky = FakeActor(
            "SM_SkySphere",
            "StaticMeshActor",
            (0.0, 0.0, 0.0),
            (1_638_400.0, 1_638_400.0, 1_638_400.0),
            components=(("StaticMeshComponent", "/Engine/MapTemplates/Sky/SM_SkySphere.SM_SkySphere"),),
        )
        room = FakeActor(
            "EnclaveRoom",
            "Volume",
            (100.0, 200.0, 150.0),
            (500.0, 600.0, 150.0),
            components=("BoxComponent",),
            tags=("Ghost.RoomBounds",),
        )
        subsystem = FakeSubsystem([mesh, partition, light, sky], [])
        fake_unreal = types.ModuleType("unreal")
        fake_unreal.ActorComponent = object
        fake_unreal.EditorActorSubsystem = object
        fake_unreal.get_editor_subsystem = lambda _kind: subsystem
        code = spatial_awareness_tools._scene_overview_code(
            include_hidden=False,
            class_filter="",
            tag_filter="",
            limit=25,
            include_actor_samples=False,
        )

        def execute() -> dict[str, Any]:
            namespace: dict[str, Any] = {"_result": {}, "_warnings": [], "_errors": []}
            with patch.dict(sys.modules, {"unreal": fake_unreal}):
                exec(code, namespace)
            return namespace["_result"]

        unresolved = execute()
        content = unresolved["bounds_scopes"]["physical_content"]
        self.assertEqual(content["included_actor_count"], 1)
        self.assertEqual(content["excluded_actor_count"], 3)
        self.assertIn(
            {"name": "renderable_environment_context_actor", "count": 1},
            content["exclusion_reason_histogram"],
        )
        self.assertEqual(content["bounds"]["min"], {"x": 50.0, "y": 140.0, "z": 230.0})
        self.assertEqual(content["bounds"]["max"], {"x": 150.0, "y": 260.0, "z": 370.0})
        self.assertEqual(unresolved["local_bounds_resolution"]["status"], "needs_explicit_local_scope")

        subsystem.actors.append(room)
        authored = execute()
        self.assertEqual(authored["local_bounds_resolution"]["status"], "resolved_from_single_authored_room")
        self.assertEqual(authored["local_bounds_resolution"]["bounds"]["min"]["x"], -400.0)

        subsystem.selected = [mesh]
        selected = execute()
        self.assertEqual(selected["local_bounds_resolution"]["status"], "resolved_from_selected_physical_content")
        self.assertEqual(selected["local_bounds_resolution"]["bounds"], content["bounds"])

        subsystem.selected = []
        query_code = spatial_awareness_tools._scene_overview_code(
            include_hidden=False,
            class_filter="",
            tag_filter="",
            limit=25,
            include_actor_samples=False,
            local_actor_query="EnclaveWall",
        )
        query_namespace: dict[str, Any] = {"_result": {}, "_warnings": [], "_errors": []}
        with patch.dict(sys.modules, {"unreal": fake_unreal}):
            exec(query_code, query_namespace)
        query_result = query_namespace["_result"]
        self.assertEqual(
            query_result["local_bounds_resolution"]["status"],
            "resolved_from_explicit_local_query",
        )
        self.assertEqual(
            query_result["local_bounds_resolution"]["source_scope"],
            "bounds_scopes.explicit_local_query",
        )
        self.assertEqual(
            query_result["bounds_scopes"]["explicit_local_query"]["included_actor_count"],
            1,
        )

    def test_analyze_room_generates_bounds_surface_clearance_handoffs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {
                    "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
                    "room_model": {"dimensions_cm": [700.0, 520.0, 280.0]},
                    "surface_counts": {"floors": 1, "walls": 4, "horizontal_supports": 2},
                    "clearance_summary": {"risk_count": 0},
                    "planner_handoff": {
                        "spatial_plan_interior_composition": {"room_dimensions": [700.0, 520.0, 280.0]},
                        "spatial_surface_probe": {"points": [[0.0, 0.0, 200.0]]},
                    },
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_analyze_room"](
                ctx=None,
                room_type="apartment",
                actor_query="Apartment",
                class_filter="StaticMeshActor",
                tag_filter="Interior",
                clearance_padding=110,
                min_walkway_width=95,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA)
        self.assertEqual(payload["inputs"]["clearance_padding"], 110.0)
        self.assertEqual(calls[0][1], "spatial_analyze_room")
        self.assertIn("_room_zones_live", calls[0][0])
        self.assertIn("Ghost.RoomBounds", calls[0][0])
        self.assertIn("Ghost.Zone.", calls[0][0])
        self.assertIn("authored_room_designation", calls[0][0])
        self.assertIn("designation_markers", calls[0][0])
        self.assertIn("bedroom", calls[0][0])
        self.assertNotIn('"bedroom": ["sleeping"]', calls[0][0])
        self.assertIn("classified_surfaces", calls[0][0])
        self.assertIn("clearance_risks", calls[0][0])
        self.assertIn("supports_countertop_clutter", calls[0][0])
        self.assertIn("central_circulation_overlap", calls[0][0])
        self.assertIn("spatial_plan_interior_composition", calls[0][0])
        self.assertIn("spatial_infer_functional_zones", calls[0][0])
        self.assertIn("spatial_surface_probe", calls[0][0])
        self.assertIn("spatial_validate_placement", calls[0][0])

    def test_analyze_room_validates_room_type_before_unreal_execution(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_structured") as fake_exec:
            invalid_room = json.loads(mcp.tools["spatial_analyze_room"](
                ctx=None,
                room_type="spaceship_hangar",
            ))

        self.assertFalse(invalid_room["success"])
        self.assertIn("room_type must be one of", invalid_room["errors"][0])
        fake_exec.assert_not_called()

    def test_plan_room_bounds_designation_outputs_tag_contract_and_handoffs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        payload = json.loads(mcp.tools["spatial_plan_room_bounds_designation"](
            ctx=None,
            room_id="apartment_01",
            room_type="apartment",
            room_dimensions=[720, 520, 300],
            room_origin=[10, 20, 0],
            zone_names=["genkan", "kitchenette", "living", "bedroom", "hallway"],
            include_opening_markers=True,
            include_surface_markers=True,
            include_path_markers=True,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.ROOM_BOUNDS_DESIGNATION_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_editor_authoring")
        self.assertFalse(outputs["mutation_required"])
        self.assertFalse(outputs["tripo_required"])
        self.assertIn("Ghost.RoomBounds", outputs["room_bounds_actor"]["tags"])
        self.assertIn("Ghost.RoomId.apartment_01", outputs["room_bounds_actor"]["tags"])
        self.assertEqual(outputs["analysis_handoff"]["tool"], "spatial_analyze_room")
        self.assertEqual(outputs["analysis_handoff"]["arguments"]["tag_filter"], "Ghost.RoomId.apartment_01")
        zones = {zone["authored_label"]: zone for zone in outputs["zone_specs"]}
        self.assertEqual(zones["genkan"]["name"], "entry")
        self.assertEqual(zones["kitchenette"]["name"], "kitchen")
        self.assertIn("Ghost.Zone.Genkan", zones["genkan"]["tags"])
        self.assertIn("Ghost.Zone.Kitchenette", zones["kitchenette"]["tags"])
        marker_kinds = {marker["kind"] for marker in outputs["marker_examples"]}
        self.assertIn("opening", marker_kinds)
        self.assertIn("path", marker_kinds)
        self.assertIn("surface", marker_kinds)
        self.assertEqual(outputs["functional_zone_handoff"]["tool"], "spatial_infer_functional_zones")
        self.assertIn("entry", outputs["functional_zone_handoff"]["arguments"]["requested_zones"])

    def test_query_actor_validates_vectors_before_unreal_execution(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_structured") as fake_exec:
            payload = json.loads(mcp.tools["spatial_query_actors"](ctx=None, center=[1.0, 2.0]))

        self.assertFalse(payload["success"])
        self.assertIn("center must contain exactly three numbers", payload["errors"])
        fake_exec.assert_not_called()

    def test_query_actor_generates_radius_and_box_filters(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {"matched_actor_count": 1},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(
                mcp.tools["spatial_query_actors"](
                    ctx=None,
                    query="door",
                    center=[0, 0, 0],
                    radius=500,
                    box_min=[-100, -100, 0],
                    box_max=[100, 100, 300],
                )
            )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.SPATIAL_QUERY_SCHEMA)
        self.assertEqual(calls[0][1], "spatial_query_actors")
        self.assertIn("radius = float(500.0)", calls[0][0])
        self.assertIn("box_min", calls[0][0])
        self.assertIn("_inside_box", calls[0][0])

    def test_describe_actor_requires_actor_name(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_structured") as fake_exec:
            payload = json.loads(mcp.tools["spatial_describe_actor"](ctx=None, actor=""))

        self.assertFalse(payload["success"])
        self.assertIn("actor is required", payload["errors"])
        fake_exec.assert_not_called()

    def test_proximity_map_uses_actor_selection_or_point(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {"matched_actor_count": 2},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_proximity_map"](ctx=None, actor="BP_PlayerStart", radius=2500))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.PROXIMITY_MAP_SCHEMA)
        self.assertEqual(calls[0][1], "spatial_proximity_map")
        self.assertIn("source_actor = _find_actor", calls[0][0])
        self.assertIn("selected_actors", calls[0][0])

    def test_view_context_reads_level_editor_subsystem(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {"viewport": {"available": True}},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_view_context"](ctx=None))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.VIEW_CONTEXT_SCHEMA)
        self.assertEqual(calls[0][1], "spatial_view_context")
        self.assertIn("LevelEditorSubsystem", calls[0][0])
        self.assertIn("get_level_viewport_camera_info", calls[0][0])

    def test_surface_probe_generates_downward_trace_plan(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {
                    "schema": spatial_awareness_tools.SURFACE_PROBE_SCHEMA,
                    "hit_count": 1,
                    "surface_adjusted_locations": [[0.0, 0.0, 25.0]],
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_surface_probe"](
                ctx=None,
                points=[[0, 0, 100]],
                trace_channel="visibility",
                placement_offset=25,
                ignore_actor_query="Preview",
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.SURFACE_PROBE_SCHEMA)
        self.assertEqual(calls[0][1], "spatial_surface_probe")
        self.assertIn("line_trace_single_by_channel", calls[0][0])
        self.assertIn("SystemLibrary.line_trace_single", calls[0][0])
        self.assertIn("placement_offset = float(25.0)", calls[0][0])
        self.assertIn("ignore_actor_query = 'preview'", calls[0][0])
        self.assertIn("spatial_add_asset_to_scene", calls[0][0])

    def test_surface_probe_validates_inputs_before_unreal_execution(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_structured") as fake_exec:
            invalid_point = json.loads(mcp.tools["spatial_surface_probe"](
                ctx=None,
                points=[[1, 2]],
            ))
            invalid_channel = json.loads(mcp.tools["spatial_surface_probe"](
                ctx=None,
                trace_channel="projectile",
            ))

        self.assertFalse(invalid_point["success"])
        self.assertIn("points[0] must contain exactly three numbers", invalid_point["errors"][0])
        self.assertFalse(invalid_channel["success"])
        self.assertIn("trace_channel must be one of", invalid_channel["errors"][0])
        fake_exec.assert_not_called()

    def test_validate_placement_generates_surface_and_evidence_checks(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {
                    "schema": spatial_awareness_tools.PLACEMENT_VALIDATION_SCHEMA,
                    "validated_actor_count": 1,
                    "summary": {"on_surface": 1, "potential_overlap": 0},
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_validate_placement"](
                ctx=None,
                actors=["POI_Table"],
                surface_tolerance=15,
                clearance_padding=25,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.PLACEMENT_VALIDATION_SCHEMA)
        self.assertEqual(calls[0][1], "spatial_validate_placement")
        self.assertIn("line_trace_single_by_channel", calls[0][0])
        self.assertIn("SystemLibrary.line_trace_single", calls[0][0])
        self.assertIn("axis_aligned_bounds_overlap", calls[0][0])
        self.assertIn("viewport_capture_screenshot", calls[0][0])
        self.assertIn("surface_tolerance = max(0.0, float(15.0))", calls[0][0])
        self.assertIn("clearance_padding = max(0.0, float(25.0))", calls[0][0])

    def test_validate_placement_validates_inputs_before_unreal_execution(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_structured") as fake_exec:
            invalid_center = json.loads(mcp.tools["spatial_validate_placement"](
                ctx=None,
                center=[1, 2],
            ))
            invalid_channel = json.loads(mcp.tools["spatial_validate_placement"](
                ctx=None,
                trace_channel="projectile",
            ))

        self.assertFalse(invalid_center["success"])
        self.assertIn("center must contain exactly three numbers", invalid_center["errors"][0])
        self.assertFalse(invalid_channel["success"])
        self.assertIn("trace_channel must be one of", invalid_channel["errors"][0])
        fake_exec.assert_not_called()

    def test_infer_placement_policy_returns_city_worldbuilding_handoff(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        payload = json.loads(mcp.tools["spatial_infer_placement_policy"](
            ctx=None,
            asset_paths=["/Game/City/SM_CityBlock_A.SM_CityBlock_A"],
            intent="city district blockout",
            actor_label_prefix="District",
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.PLACEMENT_POLICY_SCHEMA)
        self.assertEqual(outputs["resolved_policy"], "city_block")
        self.assertEqual(outputs["effective_layout"], "grid")
        self.assertGreaterEqual(outputs["effective_spacing"], 1600.0)
        self.assertIn("CityBlock", outputs["effective_tags"])
        self.assertIn("World_City", outputs["recommended_data_layer_names"])
        handoff = outputs["placement_arguments"]["spatial_place_selected_assets"]
        self.assertEqual(handoff["placement_layout"], "grid")
        self.assertEqual(handoff["dry_run"], True)

    def test_infer_placement_policy_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        invalid_policy = json.loads(mcp.tools["spatial_infer_placement_policy"](
            ctx=None,
            asset_paths=["/Game/Props/SM_Table.SM_Table"],
            policy="native_secret_policy",
        ))
        invalid_path = json.loads(mcp.tools["spatial_infer_placement_policy"](
            ctx=None,
            asset_paths=["SM_Table"],
        ))

        self.assertFalse(invalid_policy["success"])
        self.assertIn("policy must be one of", invalid_policy["errors"][0])
        self.assertFalse(invalid_path["success"])
        self.assertIn("Content Browser path", invalid_path["errors"][0])

    def test_infer_functional_zones_scores_room_analysis_and_detected_items(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {
                "type": "apartment",
                "dimensions_cm": [720, 520, 300],
                "origin": [0, 0, 0],
            },
            "zones": [
                {"name": "kitchen", "center": [-140, -150, 0], "size": [260, 160, 300], "wall": "negative_y"},
                {"name": "living", "center": [120, 70, 0], "size": [340, 240, 300], "wall": "open_center"},
            ],
            "classified_surfaces": {
                "horizontal_supports": [
                    {
                        "label": "Kitchen_Counter_A",
                        "roles": ["horizontal_support"],
                        "top_center": [-180, -170, 96],
                    }
                ],
                "openings": [
                    {
                        "label": "Entry_Door",
                        "roles": ["opening"],
                        "bounds": {
                            "min": {"x": -350, "y": 210, "z": 0},
                            "max": {"x": -260, "y": 250, "z": 220},
                        },
                    }
                ],
            },
        }
        detected_items = [
            {"name": "refrigerator", "zone": "kitchen", "surface": "floor", "confidence": 0.9},
            {"name": "sofa", "zone": "living", "surface": "floor", "confidence": 0.85},
            {"name": "washer dryer stack", "zone": "utility", "surface": "floor", "confidence": 0.8},
        ]

        payload = json.loads(mcp.tools["spatial_infer_functional_zones"](
            ctx=None,
            room_analysis_json=json.dumps(room_analysis),
            detected_items_json=json.dumps(detected_items),
            requested_zones=["kitchen", "living", "utility"],
            min_zone_size_cm=120,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.FUNCTIONAL_ZONE_INFERENCE_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_composition")
        self.assertEqual(outputs["zone_count"], 4)
        self.assertEqual(set(outputs["zone_names"]), {"kitchen", "living", "utility", "entry"})
        zones = {zone["name"]: zone for zone in outputs["zones"]}
        self.assertGreaterEqual(zones["kitchen"]["evidence_count"], 2)
        self.assertGreater(zones["kitchen"]["confidence"], 0.5)
        self.assertIn("refrigerator", zones["kitchen"]["recommended_props"])
        self.assertEqual(outputs["updated_room_analysis"]["zones"][0]["name"], "kitchen")
        self.assertEqual(outputs["composition_handoff"]["tool"], "spatial_plan_interior_composition")
        self.assertTrue(outputs["composition_handoff"]["enabled"])
        self.assertEqual(outputs["prop_program_handoff"]["tool"], "spatial_plan_interior_prop_program")
        self.assertTrue(outputs["prop_program_handoff"]["enabled"])
        self.assertIn("spatial_plan_interior_composition", outputs["updated_room_analysis"]["planner_handoff"])

    def test_authored_room_zones_drive_functional_zone_inference(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {
                "type": "apartment",
                "dimensions_cm": [720, 520, 300],
                "origin": [0, 0, 0],
            },
            "authored_room_designation": {
                "schema": spatial_awareness_tools.ROOM_BOUNDS_DESIGNATION_SCHEMA,
                "recognized": True,
                "room_bounds_source": "authored_room_bounds",
                "marker_counts": {"room_bounds": 1, "zones": 4, "openings": 1, "required_paths": 1},
            },
            "zones": [
                {
                    "name": "entry",
                    "authored_label": "genkan",
                    "center": [-260, 180, 0],
                    "size": [150, 130, 300],
                    "wall": "positive_y",
                    "source": "authored_actor_tag",
                    "tags": ["Ghost.Zone.Genkan", "Ghost.RoomId.apartment_01"],
                },
                {
                    "name": "kitchen",
                    "authored_label": "kitchenette",
                    "center": [-210, -155, 0],
                    "size": [240, 140, 300],
                    "wall": "negative_y",
                    "source": "authored_actor_tag",
                    "tags": ["Ghost.Zone.Kitchenette", "Ghost.RoomId.apartment_01"],
                },
                {
                    "name": "bedroom",
                    "authored_label": "sleeping alcove",
                    "center": [170, 130, 0],
                    "size": [230, 190, 300],
                    "wall": "positive_y",
                    "source": "authored_actor_tag",
                    "tags": ["Ghost.Zone.Bedroom", "Ghost.RoomId.apartment_01"],
                },
                {
                    "name": "hallway",
                    "authored_label": "hallway",
                    "center": [-60, 160, 0],
                    "size": [300, 100, 300],
                    "wall": "positive_y",
                    "source": "authored_actor_tag",
                    "tags": ["Ghost.Zone.Hallway", "Ghost.RoomId.apartment_01"],
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_infer_functional_zones"](
            ctx=None,
            room_analysis_json=json.dumps(room_analysis),
            min_zone_size_cm=90,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertTrue(payload["inputs"]["room_analysis_applied"])
        self.assertEqual(set(outputs["zone_names"]), {"entry", "kitchen", "bedroom", "hallway"})
        zones = {zone["name"]: zone for zone in outputs["zones"]}
        self.assertEqual(zones["entry"]["authored_label"], "genkan")
        self.assertEqual(zones["entry"]["center"], [-260.0, 180.0, 0.0])
        self.assertEqual(zones["entry"]["size"], [150.0, 130.0, 300.0])
        self.assertGreaterEqual(zones["entry"]["confidence"], 0.5)
        self.assertIn("bed", zones["bedroom"]["recommended_props"])
        constraint_by_kind = {constraint["kind"]: constraint for constraint in outputs["zone_constraints"]}
        self.assertTrue(constraint_by_kind["compose_bedroom_group"]["enabled"])
        self.assertTrue(constraint_by_kind["preserve_hallway_linear_circulation"]["enabled"])
        summary = outputs["updated_room_analysis"]["zones"][0]
        self.assertIn("authored_label", summary)
        self.assertEqual(outputs["updated_room_analysis"]["authored_room_designation"]["marker_counts"]["room_bounds"], 1)

    def test_hallway_zone_survives_inference_prop_program_and_composition(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {"name": "runner rug", "zone": "hallway", "surface": "floor", "confidence": 0.82},
            {"name": "wall hooks", "zone": "hallway", "surface": "wall", "confidence": 0.78},
        ]

        zone_payload = json.loads(mcp.tools["spatial_infer_functional_zones"](
            ctx=None,
            detected_items_json=json.dumps(detected_items),
            room_type="apartment",
            room_dimensions=[720, 520, 300],
            requested_zones=["hallway"],
            min_zone_size_cm=120,
        ))

        self.assertTrue(zone_payload["success"])
        zone_outputs = zone_payload["outputs"]
        self.assertIn("hallway", zone_outputs["zone_names"])
        zones = {zone["name"]: zone for zone in zone_outputs["zones"]}
        self.assertIn("hallway", zones)
        self.assertEqual(zones["hallway"]["wall"], "positive_y")
        self.assertIn("hallway runner rug", zones["hallway"]["recommended_props"])
        constraint_by_kind = {constraint["kind"]: constraint for constraint in zone_outputs["zone_constraints"]}
        self.assertTrue(constraint_by_kind["preserve_hallway_linear_circulation"]["enabled"])

        program_payload = json.loads(mcp.tools["spatial_plan_interior_prop_program"](
            ctx=None,
            functional_zone_plan_json=json.dumps(zone_outputs),
            detected_items_json=json.dumps(detected_items),
            include_architectural_fill=True,
        ))

        self.assertTrue(program_payload["success"])
        program_outputs = program_payload["outputs"]
        props_by_id = {prop["id"]: prop for prop in program_outputs["props"]}
        self.assertIn("hallway_runner_rug", props_by_id)
        self.assertIn("wall_hooks", props_by_id)
        self.assertIn("shoe_bench", props_by_id)
        self.assertIn("hallway_baseboard_trim", props_by_id)
        self.assertEqual(props_by_id["wall_hooks"]["surface"], "wall")
        hallway_program = next(zone for zone in program_outputs["zone_program"] if zone["name"] == "hallway")
        self.assertGreaterEqual(hallway_program["planned_prop_count"], 3)
        self.assertIn("center path", " ".join(hallway_program["composition_notes"]))

        composition_payload = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="apartment",
            room_dimensions=[720, 520, 300],
            functional_zone_plan_json=json.dumps(zone_outputs),
            prop_program_json=json.dumps(program_outputs),
            actor_label_prefix="AptHall",
        ))

        self.assertTrue(composition_payload["success"])
        composition_outputs = composition_payload["outputs"]
        constraint_kinds = {constraint["kind"] for constraint in composition_outputs["composition_constraints"]}
        self.assertIn("hallway_linear_clearance", constraint_kinds)
        steps_by_id = {step["id"]: step for step in composition_outputs["placement_steps"]}
        self.assertEqual(steps_by_id["hallway_runner_rug"]["arguments"]["actor_label"], "AptHall_hallway_runner_rug")
        self.assertEqual(steps_by_id["wall_hooks"]["arguments"]["location"][2], 135.0)

    def test_plan_interior_prop_program_builds_zone_requirements_and_handoffs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        zone_plan = {
            "schema": spatial_awareness_tools.FUNCTIONAL_ZONE_INFERENCE_SCHEMA,
            "status": "ready_for_composition",
            "room": {"type": "apartment", "dimensions_cm": [720, 520, 300], "origin": [0, 0, 0]},
            "zones": [
                {
                    "name": "kitchen",
                    "center": [-180, -150, 0],
                    "size": [260, 170, 300],
                    "wall": "negative_y",
                    "recommended_props": ["refrigerator", "stove and oven", "kitchen counter run", "kitchen sink"],
                },
                {
                    "name": "living",
                    "center": [120, 80, 0],
                    "size": [360, 260, 300],
                    "wall": "open_center",
                    "recommended_props": ["sofa", "coffee table", "books and table clutter"],
                },
                {
                    "name": "utility",
                    "center": [-230, 120, 0],
                    "size": [150, 160, 300],
                    "wall": "positive_x",
                    "recommended_props": ["washer dryer stack"],
                },
            ],
        }
        detected_items = [
            {"name": "bar stool", "zone": "kitchen", "surface": "floor", "confidence": 0.8},
            {"name": "books", "zone": "living", "surface": "table", "confidence": 0.75},
        ]

        payload = json.loads(mcp.tools["spatial_plan_interior_prop_program"](
            ctx=None,
            functional_zone_plan_json=json.dumps(zone_plan),
            detected_items_json=json.dumps(detected_items),
            required_props=["counter clutter"],
            existing_asset_paths=["/Game/Props/Living/SM_Sofa.SM_Sofa"],
            include_architectural_fill=True,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.INTERIOR_PROP_PROGRAM_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_composition")
        self.assertTrue(payload["inputs"]["functional_zone_plan_applied"])
        self.assertGreaterEqual(outputs["prop_count"], 8)
        self.assertGreater(outputs["architectural_fill_count"], 0)
        self.assertGreater(outputs["generation_candidate_count"], 0)
        props_by_id = {prop["id"]: prop for prop in outputs["props"]}
        self.assertIn("refrigerator", props_by_id)
        self.assertIn("backsplash_panel", props_by_id)
        self.assertIn("bar_stool", props_by_id)
        self.assertIn("screenshot_detected", props_by_id["bar_stool"]["program_source"])
        zone_program = {zone["name"]: zone for zone in outputs["zone_program"]}
        self.assertIn("kitchen", zone_program)
        self.assertIn("living", zone_program)
        self.assertGreaterEqual(zone_program["kitchen"]["planned_prop_count"], 5)
        self.assertIn("surface_counts", zone_program["kitchen"])
        self.assertEqual(outputs["composition_handoff"]["tool"], "spatial_plan_interior_composition")
        self.assertEqual(outputs["composition_handoff"]["arguments"]["prop_program_json"], "<THIS_INTERIOR_PROP_PROGRAM_RESULT_JSON>")

    def test_preflight_hallway_linear_clearance_flags_wide_floor_props(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {
                "type": "apartment",
                "dimensions_cm": [600, 400, 280],
                "origin": [0, 0, 0],
                "zones": [
                    {"name": "hallway", "center": [0, 110, 0], "size": [320, 120, 280], "wall": "positive_y"},
                ],
            },
            "props": [
                {
                    "id": "wide_console",
                    "name": "wide console",
                    "zone": "hallway",
                    "category": "furniture",
                    "surface": "floor",
                    "approx_size_cm": [170, 120, 85],
                },
            ],
            "placement_steps": [
                {
                    "id": "wide_console",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Hall_wide_console",
                        "asset_path": "/Game/Props/Hall/SM_WideConsole.SM_WideConsole",
                        "location": [0, 110, 0],
                        "rotation": [0, 180, 0],
                        "dry_run": True,
                    },
                },
            ],
            "composition_constraints": [
                {
                    "kind": "hallway_linear_clearance",
                    "sources": ["wide_console"],
                    "max_floor_prop_cross_section_cm": 90.0,
                    "min_clear_path_cm": 90.0,
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            min_walkway_width=90,
            clearance_padding=0,
            pairwise_padding=10,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "needs_review")
        issue_kinds = {issue["kind"] for issue in outputs["issues"]}
        self.assertIn("semantic_hallway_clearance_review", issue_kinds)
        hallway_issue = next(issue for issue in outputs["issues"] if issue["kind"] == "semantic_hallway_clearance_review")
        self.assertEqual(hallway_issue["actor_label"], "Hall_wide_console")
        self.assertEqual(hallway_issue["cross_section_cm"], 120.0)
        self.assertIn(
            "semantic_hallway_clearance_review",
            {issue["kind"] for issue in outputs["actor_checks"][0]["issues"]},
        )
        self.assertIn(
            "preserve linear circulation",
            " ".join(str(suggestion.get("reason", "")) for suggestion in outputs["suggestions"]),
        )

    def test_plan_interior_composition_accepts_functional_zone_plan(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        zone_plan = {
            "schema": spatial_awareness_tools.FUNCTIONAL_ZONE_INFERENCE_SCHEMA,
            "status": "ready_for_composition",
            "room": {"type": "apartment", "dimensions_cm": [700, 520, 280], "origin": [0, 0, 0]},
            "zone_names": ["kitchen", "living", "utility"],
            "evidence_count": 3,
            "zones": [
                {"name": "kitchen", "center": [-190, -160, 0], "size": [260, 170, 280], "wall": "negative_y"},
                {"name": "living", "center": [110, 90, 0], "size": [360, 250, 280], "wall": "open_center"},
                {"name": "utility", "center": [-230, 120, 0], "size": [150, 160, 280], "wall": "positive_x"},
            ],
        }

        payload = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="apartment",
            functional_zone_plan_json=json.dumps(zone_plan),
            required_props=["refrigerator", "sofa", "washer dryer stack"],
            actor_label_prefix="ZonedApt",
        ))

        self.assertTrue(payload["success"])
        self.assertTrue(payload["inputs"]["functional_zone_plan_applied"])
        outputs = payload["outputs"]
        self.assertTrue(outputs["functional_zone_inference"]["applied"])
        self.assertEqual(outputs["functional_zone_inference"]["zone_names"], ["kitchen", "living", "utility"])
        self.assertEqual([zone["name"] for zone in outputs["zones"]], ["kitchen", "living", "utility"])
        self.assertEqual(outputs["room"]["dimensions_cm"], [700.0, 520.0, 280.0])
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        self.assertFalse(workflow_by_step["infer_functional_zones"]["enabled"])

    def test_plan_interior_composition_accepts_prop_program(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        prop_program = {
            "schema": spatial_awareness_tools.INTERIOR_PROP_PROGRAM_SCHEMA,
            "status": "ready_for_composition",
            "room": {"type": "apartment", "dimensions_cm": [700, 520, 280], "origin": [0, 0, 0]},
            "zones": [
                {"name": "utility", "center": [-220, 110, 0], "size": [160, 180, 280], "wall": "positive_x"},
            ],
            "zone_program": [
                {"name": "utility", "planned_props": ["washer dryer stack", "utility wall rail"], "planned_prop_count": 2},
            ],
            "props": [
                {
                    "id": "washer_dryer_stack",
                    "name": "washer dryer stack",
                    "zone": "utility",
                    "category": "appliance",
                    "surface": "floor",
                    "approx_size_cm": [80, 75, 190],
                    "program_source": "zone_recommended",
                    "existing_asset_path": "/Game/Props/Utility/SM_WasherDryer.SM_WasherDryer",
                },
                {
                    "id": "utility_wall_rail",
                    "name": "utility wall rail",
                    "zone": "utility",
                    "category": "architectural_fill",
                    "surface": "wall",
                    "approx_size_cm": [150, 8, 12],
                    "program_source": "architectural_fill",
                },
            ],
            "generation_candidate_count": 1,
            "architectural_fill_count": 1,
        }

        payload = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="apartment",
            prop_program_json=json.dumps(prop_program),
            actor_label_prefix="ProgramApt",
        ))

        self.assertTrue(payload["success"])
        self.assertTrue(payload["inputs"]["prop_program_applied"])
        outputs = payload["outputs"]
        self.assertTrue(outputs["prop_program"]["applied"])
        self.assertEqual(outputs["prop_program"]["architectural_fill_count"], 1)
        self.assertEqual([prop["id"] for prop in outputs["props"]], ["washer_dryer_stack", "utility_wall_rail"])
        self.assertEqual(outputs["props"][0]["source"], "existing_asset")
        self.assertEqual(outputs["generation_task_count"], 1)
        self.assertEqual(outputs["placement_steps"][0]["arguments"]["asset_path"], "/Game/Props/Utility/SM_WasherDryer.SM_WasherDryer")
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        self.assertFalse(workflow_by_step["plan_prop_program"]["enabled"])

    def test_plan_interior_composition_returns_tripo_and_spatial_handoffs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        payload = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="apartment",
            room_dimensions=[700, 520, 280],
            style="lived-in modern",
            intent="small apartment kitchen and living room",
            screenshot_reference="C:/refs/apartment.png",
            screenshot_observations=["visible fridge", "books on coffee table"],
            required_props=["fridge", "stove", "counter clutter"],
            actor_label_prefix="Apt",
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA)
        self.assertEqual(outputs["room"]["type"], "apartment")
        self.assertGreaterEqual(outputs["prop_count"], 3)
        self.assertGreaterEqual(outputs["generation_task_count"], 1)
        first_task = outputs["generation_tasks"][0]
        self.assertEqual(first_task["provider"], "tripo")
        self.assertEqual(first_task["submit"]["tool"], "gen_tripo_text_to_model")
        self.assertFalse(first_task["submit"]["arguments"]["confirm_spend"])
        self.assertEqual(first_task["spatial_fit"]["surface"], "floor")
        self.assertIn("stable flat base", first_task["spatial_fit"]["contact_requirement"])
        self.assertIn("spatial fit", first_task["submit"]["arguments"]["prompt"])
        self.assertIn("surface/contact floor", first_task["submit"]["arguments"]["prompt"])
        self.assertEqual(first_task["reference_image_variant"]["tool"], "gen_tripo_image_to_model")
        self.assertTrue(first_task["reference_image_variant"]["crop_required"])
        self.assertEqual(first_task["reference_image_variant"]["spatial_fit"]["zone"], first_task["spatial_fit"]["zone"])
        self.assertEqual(first_task["import"]["tool"], "gen_tripo_import_to_project")
        self.assertEqual(outputs["placement_steps"][0]["tool"], "spatial_add_asset_to_scene")
        self.assertEqual(outputs["placement_steps"][0]["arguments"]["dry_run"], True)
        self.assertEqual(outputs["validation_handoff"]["tool"], "spatial_validate_placement")
        self.assertIn("Segment the reference", " ".join(outputs["screenshot_decomposition"]["contract"]))

    def test_plan_interior_composition_emits_semantic_constraints(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        payload = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="kitchen",
            required_props=[
                "fridge",
                "stove",
                "sink",
                "kitchen counter run",
                "bar stool",
                "counter clutter",
            ],
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        constraint_kinds = {constraint["kind"] for constraint in outputs["composition_constraints"]}
        self.assertIn("kitchen_work_triangle", constraint_kinds)
        self.assertIn("counter_adjacency", constraint_kinds)
        self.assertIn("support_contact", constraint_kinds)
        self.assertIn("circulation_clearance", constraint_kinds)
        triangle = next(
            constraint
            for constraint in outputs["composition_constraints"]
            if constraint["kind"] == "kitchen_work_triangle"
        )
        self.assertEqual(set(triangle["sources"]), {"refrigerator", "stove_and_oven", "kitchen_sink"})
        self.assertEqual(outputs["constraint_count"], len(outputs["composition_constraints"]))
        self.assertIn("review_composition_constraints", [step["step"] for step in outputs["workflow"]])

    def test_plan_interior_composition_uses_room_analysis_json(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        analysis_outputs = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {
                "type": "apartment",
                "dimensions_cm": [720, 540, 300],
                "origin": [10, 20, 0],
            },
            "zones": [
                {"name": "kitchen", "center": [-80, -180, 0], "size": [280, 160, 300], "wall": "negative_y"},
                {"name": "living", "center": [120, 80, 0], "size": [360, 260, 300], "wall": "open_center"},
            ],
            "surface_counts": {"floors": 1, "walls": 4, "horizontal_supports": 2},
            "clearance_summary": {
                "clearance_padding_cm": 45,
                "risk_count": 1,
                "risks": [
                    {
                        "actor": "Sofa_Existing",
                        "risk": "central_circulation_overlap",
                        "reason": "Obstacle footprint overlaps the inferred central walkway band.",
                    }
                ],
            },
            "planner_handoff": {
                "spatial_surface_probe": {"points": [[10, 20, 160]]},
            },
        }
        room_analysis_json = json.dumps({
            "schema": spatial_awareness_tools.SPATIAL_RESULT_SCHEMA,
            "outputs": analysis_outputs,
        })

        payload = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="apartment",
            room_dimensions=[1, 1, 1],
            room_analysis_json=room_analysis_json,
            screenshot_observations=["visible fridge"],
            required_props=["fridge"],
            actor_label_prefix="MeasuredApt",
        ))

        self.assertTrue(payload["success"])
        self.assertTrue(payload["inputs"]["room_analysis_applied"])
        outputs = payload["outputs"]
        self.assertTrue(outputs["room_analysis"]["applied"])
        self.assertEqual(outputs["room"]["dimensions_cm"], [720.0, 540.0, 300.0])
        self.assertEqual(outputs["room"]["origin"], [10.0, 20.0, 0.0])
        self.assertEqual(outputs["zones"][0]["center"], [-80.0, -180.0, 0.0])
        self.assertEqual(outputs["workflow"][0]["tool"], "spatial_analyze_room")
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        self.assertEqual(workflow_by_step["probe_surfaces"]["arguments"]["points"][0], [10.0, 20.0, 160.0])
        self.assertEqual(outputs["validation_handoff"]["arguments"]["clearance_padding"], 45.0)
        self.assertIn("Room analysis detected", " ".join(outputs["screenshot_decomposition"]["observations"]))
        self.assertIn("Clearance risk near Sofa_Existing", " ".join(outputs["screenshot_decomposition"]["observations"]))

    def test_plan_interior_composition_uses_room_analysis_support_surfaces(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis_json = json.dumps({
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {
                "type": "kitchen",
                "dimensions_cm": [420, 320, 280],
                "origin": [0, 0, 0],
            },
            "zones": [
                {"name": "kitchen", "center": [0, 0, 0], "size": [420, 320, 280], "wall": "negative_y"},
            ],
            "classified_surfaces": {
                "horizontal_supports": [
                    {
                        "label": "Counter_A",
                        "roles": ["horizontal_support"],
                        "top_center": [-60, -120, 96],
                        "bounds": {
                            "min": {"x": -180, "y": -150, "z": 0},
                            "max": {"x": 60, "y": -90, "z": 96},
                        },
                    }
                ],
                "walls": [
                    {
                        "label": "Kitchen_Wall_A",
                        "roles": ["wall"],
                        "bounds": {
                            "min": {"x": -210, "y": -165, "z": 0},
                            "max": {"x": 210, "y": -155, "z": 280},
                        },
                    }
                ],
                "floors": [
                    {
                        "label": "Kitchen_Floor",
                        "roles": ["floor"],
                        "top_center": [0, 0, 0],
                    }
                ],
            },
        })

        payload = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="kitchen",
            room_analysis_json=room_analysis_json,
            required_props=["counter clutter", "wall cabinets"],
        ))

        self.assertTrue(payload["success"])
        props_by_id = {prop["id"]: prop for prop in payload["outputs"]["props"]}
        clutter = props_by_id["counter_clutter"]
        wall_cabinets = props_by_id["wall_cabinets"]
        self.assertEqual(clutter["placement"]["source"], "room_analysis_horizontal_support")
        self.assertEqual(clutter["placement"]["support_actor"], "Counter_A")
        self.assertEqual(clutter["placement"]["location"], [-60.0, -120.0, 98.0])
        self.assertEqual(wall_cabinets["placement"]["source"], "room_analysis_wall")
        self.assertEqual(wall_cabinets["placement"]["support_actor"], "Kitchen_Wall_A")
        steps_by_id = {step["id"]: step for step in payload["outputs"]["placement_steps"]}
        self.assertEqual(steps_by_id["counter_clutter"]["arguments"]["placement_source"], "room_analysis_horizontal_support")
        self.assertEqual(steps_by_id["wall_cabinets"]["arguments"]["placement_source"], "room_analysis_wall")

    def test_plan_interior_composition_prefers_existing_assets(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        payload = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="kitchen",
            required_props=["refrigerator"],
            existing_asset_paths=["/Game/Props/SM_Refrigerator.SM_Refrigerator"],
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        [prop] = outputs["props"]
        self.assertEqual(prop["source"], "existing_asset")
        self.assertEqual(prop["matched_asset_path"], "/Game/Props/SM_Refrigerator.SM_Refrigerator")
        self.assertEqual(outputs["generation_task_count"], 0)
        self.assertEqual(outputs["placement_steps"][0]["arguments"]["asset_path"], "/Game/Props/SM_Refrigerator.SM_Refrigerator")

    def test_plan_interior_composition_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        invalid_room = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="castle_banquet_hall",
        ))
        invalid_dimensions = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_dimensions=[700, 520],
        ))
        invalid_analysis = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_analysis_json="{not-json",
        ))

        self.assertFalse(invalid_room["success"])
        self.assertIn("room_type must be one of", invalid_room["errors"][0])
        self.assertFalse(invalid_dimensions["success"])
        self.assertIn("room_dimensions must contain exactly three numbers", invalid_dimensions["errors"][0])
        self.assertFalse(invalid_analysis["success"])
        self.assertIn("room_analysis_json must be a JSON object", invalid_analysis["errors"][0])

    def test_plan_screenshot_reconstruction_returns_detection_contract_without_items(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        payload = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            room_type="apartment",
            room_dimensions=[700, 520, 280],
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.SCREENSHOT_RECONSTRUCTION_SCHEMA)
        self.assertTrue(outputs["decomposition_required"])
        self.assertIn("crop_box", outputs["segmentation_schema"]["fields"])
        self.assertEqual(outputs["crop_tasks"], [])
        self.assertIn("segment_reference_image", [step["step"] for step in outputs["workflow"]])
        self.assertEqual(outputs["workflow"][-1]["tool"], "spatial_plan_screenshot_reconstruction")

    def test_prepare_screenshot_decomposition_request_builds_vision_contract_and_handoffs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        payload = json.loads(mcp.tools["spatial_prepare_screenshot_decomposition_request"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            image_size=[1280, 720],
            room_type="apartment",
            room_dimensions=[700, 520, 280],
            style="warm modern",
            intent="rebuild a compact kitchen and living area",
            max_items=24,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.SCREENSHOT_DECOMPOSITION_REQUEST_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_vision_decomposition")
        self.assertEqual(outputs["room"]["dimensions_cm"], [700.0, 520.0, 280.0])
        self.assertEqual(outputs["output_contract"]["format"], "detected_items_json")
        self.assertIn("crop_box", outputs["detected_items_schema"]["fields"])
        self.assertIn("Return only JSON", outputs["vision_prompt"])
        self.assertIn("Maximum items: 24", outputs["vision_prompt"])
        self.assertIn("kitchen work-triangle anchors", " ".join(outputs["decomposition_targets"]))
        self.assertTrue(outputs["preflight_handoff"]["arguments"]["require_crop_boxes"])
        self.assertEqual(outputs["preflight_handoff"]["tool"], "spatial_preflight_screenshot_detections")
        self.assertEqual(outputs["scene_graph_handoff"]["tool"], "spatial_infer_screenshot_scene_graph")
        self.assertEqual(outputs["reconstruction_handoff"]["tool"], "spatial_plan_screenshot_reconstruction")
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        self.assertIn("spatial_prepare_tripo_generation_batch", workflow_by_step["crop_generate_bind_apply_validate"]["tools"])
        self.assertIn("spatial_apply_composition_plan", workflow_by_step["crop_generate_bind_apply_validate"]["tools"])

    def test_prepare_screenshot_decomposition_request_uses_room_analysis_and_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {
                "type": "kitchen",
                "dimensions_cm": [420, 320, 280],
                "origin": [10, 20, 0],
            },
        }

        payload = json.loads(mcp.tools["spatial_prepare_screenshot_decomposition_request"](
            ctx=None,
            reference_image="C:/refs/kitchen.png",
            room_analysis_json=json.dumps(room_analysis),
            room_type="apartment",
            prefer_crop_boxes=False,
        ))
        missing_reference = json.loads(mcp.tools["spatial_prepare_screenshot_decomposition_request"](
            ctx=None,
            reference_image="",
        ))
        invalid_image_size = json.loads(mcp.tools["spatial_prepare_screenshot_decomposition_request"](
            ctx=None,
            reference_image="C:/refs/kitchen.png",
            image_size=[1280],
        ))

        self.assertTrue(payload["success"])
        self.assertTrue(payload["inputs"]["room_analysis_applied"])
        self.assertEqual(payload["outputs"]["room"]["type"], "kitchen")
        self.assertEqual(payload["outputs"]["room"]["dimensions_cm"], [420.0, 320.0, 280.0])
        self.assertFalse(payload["outputs"]["preflight_handoff"]["arguments"]["require_crop_boxes"])
        self.assertFalse(missing_reference["success"])
        self.assertIn("reference_image is required", missing_reference["errors"][0])
        self.assertFalse(invalid_image_size["success"])
        self.assertIn("image_size must contain width and height numbers", invalid_image_size["errors"][0])

    def test_compile_worldbuilding_readiness_reports_missing_screenshot_gates(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        payload = json.loads(mcp.tools["spatial_compile_worldbuilding_readiness"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.WORLDBUILDING_READINESS_SCHEMA)
        self.assertEqual(outputs["status"], "blocked")
        gate_by_name = {gate["name"]: gate for gate in outputs["gates"]}
        self.assertFalse(gate_by_name["live_room_analysis"]["ready"])
        self.assertFalse(gate_by_name["screenshot_decomposition_request"]["ready"])
        self.assertFalse(gate_by_name["screenshot_scene_graph"]["ready"])
        self.assertIn("spatial_analyze_room", [action["tool"] for action in outputs["next_actions"]])
        self.assertIn("spatial_prepare_screenshot_decomposition_request", [action["tool"] for action in outputs["next_actions"]])
        self.assertTrue(outputs["screenshot_mode"])

    def test_compile_worldbuilding_readiness_requires_functional_zones_after_room_analysis(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {"type": "apartment", "dimensions_cm": [720, 520, 300], "origin": [0, 0, 0]},
        }

        payload = json.loads(mcp.tools["spatial_compile_worldbuilding_readiness"](
            ctx=None,
            room_analysis_json=json.dumps(room_analysis),
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "blocked")
        gate_by_name = {gate["name"]: gate for gate in outputs["gates"]}
        self.assertTrue(gate_by_name["live_room_analysis"]["ready"])
        self.assertFalse(gate_by_name["functional_zone_inference"]["ready"])
        self.assertTrue(gate_by_name["functional_zone_inference"]["blocking"])
        self.assertEqual(gate_by_name["functional_zone_inference"]["next_action"]["tool"], "spatial_infer_functional_zones")
        self.assertIn("spatial_infer_functional_zones", [action["tool"] for action in outputs["next_actions"]])

    def test_compile_worldbuilding_readiness_requires_prop_program_after_functional_zones(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {"type": "apartment", "dimensions_cm": [720, 520, 300], "origin": [0, 0, 0]},
        }
        functional_zone_plan = {
            "schema": spatial_awareness_tools.FUNCTIONAL_ZONE_INFERENCE_SCHEMA,
            "status": "ready_for_composition",
            "zones": [
                {
                    "name": "kitchen",
                    "center": [-180, 120, 0],
                    "size": [240, 220, 300],
                    "wall": "west",
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_compile_worldbuilding_readiness"](
            ctx=None,
            room_analysis_json=json.dumps(room_analysis),
            functional_zone_plan_json=json.dumps(functional_zone_plan),
            require_viewport_evidence=False,
        ))

        self.assertTrue(payload["success"])
        self.assertFalse(payload["inputs"]["prop_program_applied"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "blocked")
        gate_by_name = {gate["name"]: gate for gate in outputs["gates"]}
        self.assertTrue(gate_by_name["live_room_analysis"]["ready"])
        self.assertTrue(gate_by_name["functional_zone_inference"]["ready"])
        self.assertFalse(gate_by_name["interior_prop_program"]["ready"])
        self.assertTrue(gate_by_name["interior_prop_program"]["blocking"])
        self.assertEqual(
            gate_by_name["interior_prop_program"]["next_action"]["tool"],
            "spatial_plan_interior_prop_program",
        )
        self.assertIn("prop_program_json", gate_by_name["composition_plan"]["next_action"]["arguments"])
        self.assertIn("spatial_plan_interior_prop_program", [action["tool"] for action in outputs["next_actions"]])

    def test_compile_worldbuilding_readiness_accepts_complete_pipeline_evidence(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {"type": "apartment", "dimensions_cm": [700, 520, 280], "origin": [0, 0, 0]},
        }
        decomposition_request = {
            "schema": spatial_awareness_tools.SCREENSHOT_DECOMPOSITION_REQUEST_SCHEMA,
            "status": "ready_for_vision_decomposition",
        }
        detection_preflight = {
            "schema": spatial_awareness_tools.SCREENSHOT_DECOMPOSITION_PREFLIGHT_SCHEMA,
            "status": "ready_for_reconstruction",
        }
        scene_graph = {
            "schema": spatial_awareness_tools.SCREENSHOT_SCENE_GRAPH_SCHEMA,
            "status": "ready_for_reconstruction",
        }
        reconstruction = {
            "schema": spatial_awareness_tools.SCREENSHOT_RECONSTRUCTION_SCHEMA,
            "composition_plan": {
                "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
                "placement_steps": [{"id": "fridge", "arguments": {"asset_path": "/Game/Props/SM_Fridge.SM_Fridge"}}],
            },
        }
        asset_resolution = {
            "schema": spatial_awareness_tools.PROJECT_ASSET_RESOLUTION_SCHEMA,
            "status": "ready_for_binding",
        }
        tripo_batch = {
            "schema": spatial_awareness_tools.TRIPO_GENERATION_BATCH_SCHEMA,
            "status": "no_generation_needed",
            "job_count": 0,
        }
        binding = {
            "schema": spatial_awareness_tools.COMPOSITION_ASSET_BINDING_SCHEMA,
            "status": "ready_for_dry_run_placement",
        }
        layout_preflight = {
            "schema": spatial_awareness_tools.LAYOUT_PREFLIGHT_SCHEMA,
            "status": "pass",
        }
        candidate_clearance = {
            "schema": spatial_awareness_tools.CANDIDATE_CLEARANCE_SCHEMA,
            "status": "pass",
            "candidate_count": 1,
            "blocked_count": 0,
            "needs_review_count": 0,
        }
        apply_result = {
            "schema": spatial_awareness_tools.COMPOSITION_PLACEMENT_BATCH_SCHEMA,
            "status": "executed",
        }
        validation = {
            "schema": spatial_awareness_tools.PLACEMENT_VALIDATION_SCHEMA,
            "summary": {"on_surface": 1, "floating": 0, "intersecting_or_below_surface": 0, "no_surface_hit": 0, "potential_overlap": 0},
        }

        payload = json.loads(mcp.tools["spatial_compile_worldbuilding_readiness"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            room_analysis_json=json.dumps(room_analysis),
            decomposition_request_json=json.dumps(decomposition_request),
            detection_preflight_json=json.dumps(detection_preflight),
            scene_graph_json=json.dumps(scene_graph),
            reconstruction_plan_json=json.dumps(reconstruction),
            asset_resolution_json=json.dumps(asset_resolution),
            tripo_batch_json=json.dumps(tripo_batch),
            asset_binding_json=json.dumps(binding),
            layout_preflight_json=json.dumps(layout_preflight),
            candidate_clearance_json=json.dumps(candidate_clearance),
            apply_result_json=json.dumps(apply_result),
            validation_result_json=json.dumps(validation),
            viewport_evidence_json=json.dumps({"artifact_path": "C:/shots/apartment_after.png"}),
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "ready_for_human_worldbuilding_review")
        self.assertEqual(outputs["blocking_gate_count"], 0)
        self.assertEqual(outputs["remaining_gate_count"], 0)
        self.assertEqual(outputs["ready_gate_count"], outputs["gate_count"])
        gate_by_name = {gate["name"]: gate for gate in outputs["gates"]}
        self.assertTrue(gate_by_name["interior_prop_program"]["ready"])
        self.assertEqual(gate_by_name["interior_prop_program"]["status"], "satisfied_by_composition")
        self.assertTrue(gate_by_name["live_candidate_clearance"]["ready"])
        self.assertTrue(gate_by_name["placement_validation"]["ready"])
        self.assertTrue(gate_by_name["viewport_evidence"]["ready"])
        workflow_steps = [step["step"] for step in outputs["workflow"]]
        self.assertIn("validate_iterate_evidence", workflow_steps)

    def test_compile_worldbuilding_readiness_blocks_candidate_clearance_overlaps(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {"type": "apartment", "dimensions_cm": [700, 520, 280], "origin": [0, 0, 0]},
        }
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "placement_steps": [
                {
                    "id": "sofa",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_Sofa.SM_Sofa",
                        "actor_label": "Apt_sofa",
                    },
                }
            ],
        }
        candidate_clearance = {
            "schema": spatial_awareness_tools.CANDIDATE_CLEARANCE_SCHEMA,
            "status": "blocked_by_clearance",
            "candidate_count": 1,
            "blocked_count": 1,
            "needs_review_count": 0,
            "candidates": [
                {
                    "actor_label": "Apt_sofa",
                    "status": "blocked_by_existing_overlap",
                    "existing_overlap_count": 1,
                    "existing_overlaps": [{"label": "Existing_Table"}],
                }
            ],
        }

        payload = json.loads(mcp.tools["spatial_compile_worldbuilding_readiness"](
            ctx=None,
            room_analysis_json=json.dumps(room_analysis),
            composition_plan_json=json.dumps(composition_plan),
            candidate_clearance_json=json.dumps(candidate_clearance),
            require_viewport_evidence=False,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "blocked")
        gate_by_name = {gate["name"]: gate for gate in outputs["gates"]}
        clearance_gate = gate_by_name["live_candidate_clearance"]
        self.assertFalse(clearance_gate["ready"])
        self.assertTrue(clearance_gate["blocking"])
        self.assertEqual(clearance_gate["status"], "blocked_by_clearance")
        self.assertEqual(clearance_gate["next_action"]["tool"], "spatial_plan_composition_iteration")
        self.assertIn("validation_result_json", clearance_gate["next_action"]["arguments"])
        self.assertIn("spatial_plan_composition_iteration", [action["tool"] for action in outputs["next_actions"]])
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        self.assertEqual(workflow_by_step["bind_review_apply"]["candidate_clearance_status"], "blocked_by_clearance")

    def test_compile_worldbuilding_readiness_routes_tripo_crop_manifest_blockers(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {"type": "apartment", "dimensions_cm": [700, 520, 280], "origin": [0, 0, 0]},
        }
        decomposition_request = {
            "schema": spatial_awareness_tools.SCREENSHOT_DECOMPOSITION_REQUEST_SCHEMA,
            "status": "ready_for_vision_decomposition",
        }
        detection_preflight = {
            "schema": spatial_awareness_tools.SCREENSHOT_DECOMPOSITION_PREFLIGHT_SCHEMA,
            "status": "ready_for_reconstruction",
        }
        scene_graph = {
            "schema": spatial_awareness_tools.SCREENSHOT_SCENE_GRAPH_SCHEMA,
            "status": "ready_for_reconstruction",
        }
        reconstruction = {
            "schema": spatial_awareness_tools.SCREENSHOT_RECONSTRUCTION_SCHEMA,
            "composition_plan": {
                "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
                "placement_steps": [{"id": "fridge", "arguments": {"asset_path": "<IMPORTED_ASSET_PATH_FOR_fridge>"}}],
            },
        }
        tripo_batch = {
            "schema": spatial_awareness_tools.TRIPO_GENERATION_BATCH_SCHEMA,
            "status": "needs_crop_review",
            "job_count": 1,
            "blocked_by_crop_manifest_count": 1,
            "jobs": [
                {
                    "id": "fridge",
                    "prop_name": "refrigerator",
                    "mode": "image_to_model",
                    "crop_readiness": {
                        "ready": False,
                        "status": "needs_crop_manifest",
                        "next_tool": "spatial_prepare_screenshot_crop_manifest",
                    },
                    "crop": {
                        "crop_box": [40, 80, 120, 240],
                        "output_placeholder": "<CROP_FOR_fridge>",
                    },
                }
            ],
        }

        payload = json.loads(mcp.tools["spatial_compile_worldbuilding_readiness"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            room_analysis_json=json.dumps(room_analysis),
            decomposition_request_json=json.dumps(decomposition_request),
            detection_preflight_json=json.dumps(detection_preflight),
            scene_graph_json=json.dumps(scene_graph),
            reconstruction_plan_json=json.dumps(reconstruction),
            tripo_batch_json=json.dumps(tripo_batch),
            require_viewport_evidence=False,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        gate_by_name = {gate["name"]: gate for gate in outputs["gates"]}
        crop_gate = gate_by_name["screenshot_crop_manifest"]
        self.assertFalse(crop_gate["ready"])
        self.assertTrue(crop_gate["blocking"])
        self.assertEqual(crop_gate["status"], "needs_crop_manifest")
        self.assertEqual(crop_gate["next_action"]["tool"], "spatial_prepare_screenshot_crop_manifest")
        self.assertEqual(crop_gate["next_action"]["arguments"]["blocked_job_ids"], ["fridge"])
        tripo_gate = gate_by_name["guarded_tripo_generation"]
        self.assertFalse(tripo_gate["ready"])
        self.assertFalse(tripo_gate["blocking"])
        self.assertEqual(tripo_gate["next_action"]["tool"], "spatial_prepare_screenshot_crop_manifest")
        self.assertIn("spatial_prepare_screenshot_crop_manifest", [action["tool"] for action in outputs["next_actions"]])
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        self.assertTrue(workflow_by_step["prepare_screenshot_crops"]["enabled"])
        self.assertEqual(workflow_by_step["prepare_screenshot_crops"]["blocked_job_ids"], ["fridge"])

    def test_plan_worldbuilding_work_order_prepares_screenshot_first_lane(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        payload = json.loads(mcp.tools["spatial_plan_worldbuilding_work_order"](
            ctx=None,
            design_brief="Rebuild this compact apartment kitchen from the reference.",
            reference_image="C:/refs/apartment.png",
            room_dimensions=[700, 520, 280],
            requested_zones=["kitchen", "living"],
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.WORLDBUILDING_WORK_ORDER_SCHEMA)
        self.assertEqual(outputs["status"], "needs_screenshot_decomposition")
        self.assertEqual(outputs["source_mode"], "screenshot_first")
        self.assertEqual(outputs["decomposition_request"]["schema"], spatial_awareness_tools.SCREENSHOT_DECOMPOSITION_REQUEST_SCHEMA)
        self.assertTrue(outputs["workflow"][1]["enabled"])
        self.assertFalse(outputs["workflow"][1]["ready"])
        self.assertEqual(outputs["tripo_strategy"]["expected_job_count"], 0)
        self.assertFalse(outputs["tripo_strategy"]["user_confirmation_required"])
        self.assertIn("screenshot_decomposition_and_scene_graph_when_reference_image_is_used", outputs["quality_gates"])
        self.assertIn("functional_zone_plan_json", outputs["readiness_handoff"]["arguments"])
        self.assertIn("prop_program_json", outputs["readiness_handoff"]["arguments"])
        self.assertIn("candidate_clearance_json", outputs["readiness_handoff"]["arguments"])
        self.assertEqual(outputs["readiness_handoff"]["tool"], "spatial_compile_worldbuilding_readiness")

    def test_plan_worldbuilding_work_order_threads_screenshot_prop_program(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "name": "refrigerator",
                "category": "appliance",
                "zone": "kitchen",
                "surface": "floor",
                "crop_box": [40, 80, 120, 240],
                "approx_size_cm": [90, 80, 190],
            },
            {
                "name": "books",
                "zone": "living",
                "surface": "table",
                "existing_asset_path": "/Game/Props/SM_Books.SM_Books",
                "crop_box": [470, 360, 60, 40],
            },
        ]

        payload = json.loads(mcp.tools["spatial_plan_worldbuilding_work_order"](
            ctx=None,
            design_brief="Rebuild the visible apartment reference.",
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps(detected_items),
            room_dimensions=[700, 520, 280],
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["source_mode"], "screenshot_reconstruction")
        self.assertEqual(outputs["reconstruction_plan"]["prop_program"]["schema"], spatial_awareness_tools.INTERIOR_PROP_PROGRAM_SCHEMA)
        self.assertEqual(outputs["prop_program"]["detected_prop_count"], 2)
        self.assertEqual(outputs["prop_program"]["prop_count"], outputs["composition_plan"]["prop_program"]["prop_count"])
        self.assertTrue(outputs["composition_plan"]["prop_program"]["applied"])
        self.assertTrue(outputs["readiness_preview"]["blocking_gate_count"] >= 1)
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        self.assertTrue(workflow_by_step["plan_prop_program"]["ready"])
        self.assertEqual(outputs["status"], "needs_screenshot_crop_manifest")
        self.assertTrue(outputs["tripo_strategy"]["crop_manifest_required"])
        self.assertEqual(outputs["tripo_strategy"]["blocked_by_crop_manifest_count"], 1)
        self.assertEqual(outputs["tripo_strategy"]["blocked_crop_job_ids"], ["refrigerator"])
        self.assertEqual(outputs["tripo_strategy"]["crop_manifest_handoff"]["tool"], "spatial_prepare_screenshot_crop_manifest")
        self.assertTrue(workflow_by_step["prepare_screenshot_crop_manifest"]["enabled"])
        self.assertFalse(workflow_by_step["prepare_screenshot_crop_manifest"]["ready"])
        self.assertEqual(workflow_by_step["prepare_screenshot_crop_manifest"]["blocked_job_ids"], ["refrigerator"])
        self.assertIn("screenshot_crop_manifest_before_tripo_image_spend", outputs["quality_gates"])

    def test_plan_worldbuilding_work_order_resolves_project_assets_before_tripo(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        asset_catalog = {
            "assets": [
                {
                    "asset_path": "/Game/Props/Kitchen/SM_RefrigeratorFull.SM_RefrigeratorFull",
                    "asset_name": "SM_RefrigeratorFull",
                    "class_name": "StaticMesh",
                    "tags": ["fridge", "refrigerator", "kitchen", "appliance"],
                    "approx_size_cm": [92, 82, 188],
                },
                {
                    "asset_path": "/Game/Props/Kitchen/SM_StoveRange.SM_StoveRange",
                    "asset_name": "SM_StoveRange",
                    "class_name": "StaticMesh",
                    "tags": ["stove", "oven", "range", "kitchen", "appliance"],
                    "approx_size_cm": [82, 72, 94],
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_plan_worldbuilding_work_order"](
            ctx=None,
            design_brief="Build a believable apartment kitchen with clutter.",
            room_type="kitchen",
            room_dimensions=[420, 320, 280],
            required_props=["refrigerator", "stove and oven", "counter clutter"],
            project_asset_catalog_json=json.dumps(asset_catalog),
            generate_missing_with_tripo=True,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.WORLDBUILDING_WORK_ORDER_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_guarded_tripo_review")
        self.assertEqual(outputs["source_mode"], "direct_room_composition")
        self.assertEqual(outputs["prop_requirement_count"], 7)
        self.assertEqual(outputs["asset_strategy"]["resolved_count"], 2)
        self.assertEqual(outputs["asset_strategy"]["unresolved_count"], 5)
        self.assertEqual(outputs["tripo_strategy"]["expected_job_count"], 5)
        self.assertEqual(outputs["tripo_strategy"]["batch_preview"]["status"], "needs_user_spend_confirmation")
        self.assertEqual(outputs["tripo_strategy"]["batch_preview"]["job_count"], 5)
        self.assertEqual(outputs["tripo_strategy"]["batch_preview"]["text_job_count"], 5)
        self.assertEqual(outputs["tripo_strategy"]["batch_preview"]["image_job_count"], 0)
        self.assertFalse(outputs["tripo_strategy"]["batch_preview"]["jobs"][0]["submit"]["arguments"]["confirm_spend"])
        self.assertEqual(
            set(outputs["tripo_strategy"]["generation_source"]["resolved_ids"]),
            {"refrigerator", "stove_and_oven"},
        )
        self.assertEqual(
            set(outputs["tripo_strategy"]["generation_source"]["unresolved_ids"]),
            {"kitchen_counter_run", "kitchen_sink", "base_cabinets", "counter_clutter", "backsplash_panel"},
        )
        self.assertEqual(
            {job["id"] for job in outputs["tripo_strategy"]["batch_preview"]["jobs"]},
            set(outputs["tripo_strategy"]["generation_source"]["unresolved_ids"]),
        )
        self.assertNotIn("refrigerator", {job["id"] for job in outputs["tripo_strategy"]["batch_preview"]["jobs"]})
        self.assertNotIn("stove_and_oven", {job["id"] for job in outputs["tripo_strategy"]["batch_preview"]["jobs"]})
        self.assertTrue(outputs["tripo_strategy"]["user_confirmation_required"])
        self.assertEqual(outputs["functional_zone_plan"]["schema"], spatial_awareness_tools.FUNCTIONAL_ZONE_INFERENCE_SCHEMA)
        self.assertEqual(outputs["functional_zone_plan"]["status"], "ready_for_composition")
        self.assertEqual(outputs["composition_plan"]["functional_zone_inference"]["applied"], True)
        self.assertEqual(outputs["prop_program"]["schema"], spatial_awareness_tools.INTERIOR_PROP_PROGRAM_SCHEMA)
        self.assertEqual(outputs["prop_program"]["prop_count"], 7)
        self.assertEqual(outputs["prop_program"]["architectural_fill_count"], 1)
        unresolved_ids = {item["id"] for item in outputs["asset_strategy"]["resolution"]["unresolved_props"]}
        self.assertIn("kitchen_counter_run", unresolved_ids)
        self.assertIn("kitchen_sink", unresolved_ids)
        self.assertIn("backsplash_panel", unresolved_ids)
        self.assertIn("kitchen", [zone["name"] for zone in outputs["zone_program"]])
        workflow_steps = [step["step"] for step in outputs["workflow"]]
        self.assertIn("plan_prop_program", workflow_steps)
        self.assertIn("resolve_project_assets", workflow_steps)
        self.assertIn("prepare_guarded_tripo_batch", workflow_steps)
        self.assertIn("bind_existing_project_assets", workflow_steps)
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        existing_binding_handoff = outputs["asset_strategy"]["existing_asset_binding_handoff"]
        self.assertTrue(existing_binding_handoff["enabled"])
        self.assertEqual(existing_binding_handoff["tool"], "spatial_bind_generated_assets_to_composition")
        existing_overrides = json.loads(existing_binding_handoff["arguments"]["asset_overrides_json"])
        self.assertEqual(
            existing_overrides["refrigerator"]["asset_path"],
            "/Game/Props/Kitchen/SM_RefrigeratorFull.SM_RefrigeratorFull",
        )
        self.assertEqual(
            existing_overrides["stove_and_oven"]["asset_path"],
            "/Game/Props/Kitchen/SM_StoveRange.SM_StoveRange",
        )
        self.assertTrue(workflow_by_step["bind_existing_project_assets"]["prepared"])
        self.assertEqual(
            workflow_by_step["bind_existing_project_assets"]["arguments"]["asset_overrides_json"],
            existing_binding_handoff["arguments"]["asset_overrides_json"],
        )
        bound_existing = json.loads(mcp.tools[existing_binding_handoff["tool"]](
            ctx=None,
            **existing_binding_handoff["arguments"],
        ))
        self.assertTrue(bound_existing["success"])
        self.assertEqual(bound_existing["outputs"]["status"], "waiting_for_generated_assets")
        self.assertEqual(bound_existing["outputs"]["resolved_count"], 2)
        self.assertEqual(bound_existing["outputs"]["unresolved_count"], 5)
        bound_steps = {step["id"]: step for step in bound_existing["outputs"]["placement_steps"]}
        self.assertEqual(
            bound_steps["refrigerator"]["arguments"]["asset_path"],
            "/Game/Props/Kitchen/SM_RefrigeratorFull.SM_RefrigeratorFull",
        )
        post_generation_binding = outputs["tripo_strategy"]["post_generation_binding_handoff"]
        self.assertTrue(post_generation_binding["enabled"])
        self.assertEqual(post_generation_binding["tool"], "spatial_bind_generated_assets_to_composition")
        self.assertIn("project_asset_resolution", post_generation_binding["arguments"]["composition_plan_json"])
        self.assertIn("/Game/Props/Kitchen/SM_StoveRange.SM_StoveRange", post_generation_binding["arguments"]["composition_plan_json"])
        self.assertEqual(
            workflow_by_step["bind_review_apply_validate"]["binding_handoffs"]["after_tripo_imports"]["arguments"]["composition_plan_json"],
            post_generation_binding["arguments"]["composition_plan_json"],
        )
        post_binding_pipeline = outputs["placement_strategy"]["post_binding_spatial_pipeline"]
        self.assertEqual(post_binding_pipeline["schema"], "unreal_mcp_ghost.spatial_post_binding_pipeline.v1")
        self.assertEqual(post_binding_pipeline["status"], "ready_for_bound_asset_review")
        self.assertEqual(post_binding_pipeline["actor_count"], 7)
        self.assertIn("kitchen_refrigerator", post_binding_pipeline["actor_labels"])
        self.assertIn("kitchen_counter_clutter", post_binding_pipeline["actor_labels"])
        self.assertEqual(post_binding_pipeline["scale_correction_handoff"]["tool"], "spatial_plan_asset_scale_corrections")
        self.assertFalse(post_binding_pipeline["scale_correction_handoff"]["arguments"]["allow_non_uniform_scale"])
        self.assertEqual(post_binding_pipeline["support_surface_anchor_handoff"]["tool"], "spatial_plan_support_surface_anchors")
        self.assertEqual(post_binding_pipeline["layout_preflight_handoff"]["tool"], "spatial_preflight_interior_layout")
        self.assertEqual(post_binding_pipeline["candidate_clearance_handoff"]["tool"], "spatial_preflight_candidate_clearance")
        self.assertIn("kitchen_refrigerator", post_binding_pipeline["candidate_clearance_handoff"]["arguments"]["ignore_actor_labels"])
        self.assertTrue(post_binding_pipeline["apply_handoff"]["arguments"]["dry_run"])
        self.assertTrue(post_binding_pipeline["apply_handoff"]["arguments"]["block_on_preflight_errors"])
        self.assertEqual(post_binding_pipeline["validation_handoff"]["arguments"]["actors"], post_binding_pipeline["actor_labels"])
        self.assertEqual(post_binding_pipeline["iteration_handoff"]["tool"], "spatial_plan_composition_iteration")
        self.assertEqual(post_binding_pipeline["candidate_clearance_iteration_handoff"]["tool"], "spatial_plan_composition_iteration")
        evidence_tools = [step["tool"] for step in post_binding_pipeline["viewport_evidence_handoff"]]
        self.assertIn("spatial_select_actors", evidence_tools)
        self.assertIn("viewport_capture_screenshot", evidence_tools)
        pipeline_steps = [step["step"] for step in post_binding_pipeline["workflow"]]
        self.assertIn("preflight_live_candidate_clearance", pipeline_steps)
        self.assertIn("capture_viewport_evidence", pipeline_steps)
        self.assertEqual(
            workflow_by_step["bind_review_apply_validate"]["spatial_pipeline"]["actor_labels"],
            post_binding_pipeline["actor_labels"],
        )
        self.assertTrue(workflow_by_step["prepare_guarded_tripo_batch"]["prepared"])
        self.assertEqual(
            set(workflow_by_step["prepare_guarded_tripo_batch"]["unresolved_generation_ids"]),
            {"kitchen_counter_run", "kitchen_sink", "base_cabinets", "counter_clutter", "backsplash_panel"},
        )
        self.assertIn("project_asset_resolution", workflow_by_step["prepare_guarded_tripo_batch"]["arguments"]["composition_plan_json"])
        self.assertIn("prop_program_json", outputs["readiness_handoff"]["arguments"])
        self.assertIn("project_asset_resolution_before_tripo_spend", outputs["quality_gates"])
        self.assertIn("functional_zone_inference_before_composition", outputs["quality_gates"])
        self.assertIn("interior_prop_program_before_composition", outputs["quality_gates"])

    def test_preflight_screenshot_detections_normalizes_hints_and_flags_crop_quality(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "name": "refrigerator",
                "category": "appliance",
                "crop_box": [40, 80, 120, 240],
                "approx_size_cm": [90, 80, 190],
                "confidence": 0.91,
            },
            {
                "name": "books",
                "surface": "table",
                "existing_asset_path": "/Game/Props/SM_Books.SM_Books",
                "crop_box": [420, 360, 80, 50],
                "confidence": 0.88,
            },
            {
                "name": "tiny plant",
                "category": "decor",
                "crop_box": [790, 10, 40, 40],
                "confidence": 0.2,
            },
        ]

        payload = json.loads(mcp.tools["spatial_preflight_screenshot_detections"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps(detected_items),
            image_size=[800, 600],
            room_type="apartment",
            confidence_threshold=0.35,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.SCREENSHOT_DECOMPOSITION_PREFLIGHT_SCHEMA)
        self.assertEqual(outputs["status"], "blocked_by_decomposition")
        self.assertEqual(outputs["detected_item_count"], 3)
        normalized_by_name = {item["name"]: item for item in outputs["normalized_detected_items"]}
        self.assertEqual(normalized_by_name["refrigerator"]["zone"], "kitchen")
        self.assertEqual(normalized_by_name["refrigerator"]["placement_hint"], "against the left kitchen wall")
        self.assertEqual(normalized_by_name["books"]["placement_hint"], "on the coffee table")
        self.assertEqual(normalized_by_name["books"]["existing_asset_path"], "/Game/Props/SM_Books.SM_Books")
        self.assertEqual(outputs["coverage_summary"]["out_of_bounds_count"], 1)
        self.assertEqual(outputs["coverage_summary"]["low_confidence_count"], 1)
        issue_kinds = {issue["kind"] for issue in outputs["issues"]}
        self.assertIn("crop_box_out_of_bounds", issue_kinds)
        self.assertIn("low_confidence", issue_kinds)
        self.assertEqual(outputs["reconstruction_handoff"]["tool"], "spatial_plan_screenshot_reconstruction")
        handoff_items = json.loads(outputs["reconstruction_handoff"]["arguments"]["detected_items_json"])
        self.assertEqual(
            next(item for item in handoff_items if item["name"] == "books")["placement_hint"],
            "on the coffee table",
        )

    def test_preflight_screenshot_detections_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        missing_reference = json.loads(mcp.tools["spatial_preflight_screenshot_detections"](
            ctx=None,
            reference_image="",
            detected_items_json="[]",
        ))
        invalid_image_size = json.loads(mcp.tools["spatial_preflight_screenshot_detections"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json="[]",
            image_size=[800],
        ))
        invalid_json = json.loads(mcp.tools["spatial_preflight_screenshot_detections"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json="{not-json",
        ))

        self.assertFalse(missing_reference["success"])
        self.assertIn("reference_image is required", missing_reference["errors"][0])
        self.assertFalse(invalid_image_size["success"])
        self.assertIn("image_size must contain width and height numbers", invalid_image_size["errors"][0])
        self.assertFalse(invalid_json["success"])
        self.assertIn("detected_items_json must be a JSON list", invalid_json["errors"][0])

    def test_infer_screenshot_scene_graph_builds_relationships_and_handoff(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "name": "refrigerator",
                "category": "appliance",
                "zone": "kitchen",
                "surface": "floor",
                "crop_box": [40, 80, 120, 240],
                "confidence": 0.91,
            },
            {
                "name": "kitchen counter run",
                "zone": "kitchen",
                "surface": "floor",
                "crop_box": [220, 320, 220, 80],
                "confidence": 0.88,
            },
            {
                "name": "counter clutter",
                "zone": "kitchen",
                "surface": "counter",
                "crop_box": [260, 330, 50, 40],
                "confidence": 0.82,
            },
            {
                "name": "coffee table",
                "zone": "living",
                "surface": "floor",
                "crop_box": [450, 360, 120, 70],
                "confidence": 0.86,
            },
            {
                "name": "books",
                "zone": "living",
                "surface": "table",
                "existing_asset_path": "/Game/Props/SM_Books.SM_Books",
                "crop_box": [470, 360, 60, 40],
                "confidence": 0.9,
            },
        ]

        payload = json.loads(mcp.tools["spatial_infer_screenshot_scene_graph"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps(detected_items),
            image_size=[800, 600],
            room_type="apartment",
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.SCREENSHOT_SCENE_GRAPH_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_reconstruction")
        self.assertEqual(outputs["node_count"], 5)
        nodes = {node["id"]: node for node in outputs["nodes"]}
        self.assertEqual(nodes["refrigerator"]["frame_region"]["horizontal"], "left")
        self.assertEqual(nodes["counter_clutter"]["placement_hint"], "on the counter")
        self.assertEqual(nodes["books"]["placement_hint"], "on the coffee table")
        relation_pairs = {
            (relation["source"], relation["relation"], relation["target"])
            for relation in outputs["relations"]
        }
        self.assertIn(("books", "supported_by", "coffee_table"), relation_pairs)
        self.assertIn(("counter_clutter", "supported_by", "kitchen_counter_run"), relation_pairs)
        self.assertIn(("refrigerator", "left_of", "kitchen_counter_run"), relation_pairs)
        cluster_by_zone = {cluster["zone"]: cluster for cluster in outputs["zone_clusters"]}
        self.assertEqual(cluster_by_zone["kitchen"]["item_count"], 3)
        self.assertIn("refrigerator", cluster_by_zone["kitchen"]["anchor_items"])
        constraint_kinds = {constraint["kind"] for constraint in outputs["composition_constraints"]}
        self.assertIn("support_contact", constraint_kinds)
        self.assertIn("placement_hint", constraint_kinds)
        self.assertEqual(outputs["reconstruction_handoff"]["tool"], "spatial_plan_screenshot_reconstruction")
        handoff_items = json.loads(outputs["reconstruction_handoff"]["arguments"]["detected_items_json"])
        self.assertEqual(
            next(item for item in handoff_items if item["id"] == "counter_clutter")["placement_hint"],
            "on the counter",
        )

    def test_infer_screenshot_scene_graph_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        missing_items = json.loads(mcp.tools["spatial_infer_screenshot_scene_graph"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json="[]",
        ))
        invalid_image_size = json.loads(mcp.tools["spatial_infer_screenshot_scene_graph"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps([{"name": "chair", "crop_box": [1, 2, 30, 40]}]),
            image_size=[800],
        ))
        invalid_json = json.loads(mcp.tools["spatial_infer_screenshot_scene_graph"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json="{not-json",
        ))

        self.assertFalse(missing_items["success"])
        self.assertIn("detected_items_json is required", missing_items["errors"][0])
        self.assertFalse(invalid_image_size["success"])
        self.assertIn("image_size must contain width and height numbers", invalid_image_size["errors"][0])
        self.assertFalse(invalid_json["success"])
        self.assertIn("detected_items_json must be a JSON list", invalid_json["errors"][0])

    def test_prepare_screenshot_crop_manifest_writes_crops_and_updates_batch_handoff(self) -> None:
        from PIL import Image

        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "apartment.png"
            output_dir = Path(temp_dir) / "crops"
            image = Image.new("RGB", (100, 80), (20, 20, 20))
            for x in range(10, 40):
                for y in range(12, 42):
                    image.putpixel((x, y), (200, 40, 40))
            image.save(image_path)
            detected_items = [
                {
                    "name": "refrigerator",
                    "category": "appliance",
                    "zone": "kitchen",
                    "surface": "floor",
                    "crop_box": [10, 12, 30, 30],
                    "placement_hint": "against the left kitchen wall",
                    "confidence": 0.91,
                },
                {
                    "name": "books",
                    "surface": "table",
                    "existing_asset_path": "/Game/Props/SM_Books.SM_Books",
                    "crop_box": [50, 12, 20, 20],
                    "placement_hint": "on the coffee table",
                },
            ]
            reconstruction = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
                ctx=None,
                reference_image=str(image_path),
                detected_items_json=json.dumps(detected_items),
                room_type="apartment",
                actor_label_prefix="AptRef",
            ))

            payload = json.loads(mcp.tools["spatial_prepare_screenshot_crop_manifest"](
                ctx=None,
                reconstruction_plan_json=json.dumps(reconstruction),
                crop_output_dir=str(output_dir),
                padding_px=2,
            ))

            self.assertTrue(payload["success"])
            outputs = payload["outputs"]
            self.assertEqual(outputs["schema"], spatial_awareness_tools.SCREENSHOT_CROP_MANIFEST_SCHEMA)
            self.assertEqual(outputs["status"], "ready_for_tripo_image_to_model")
            self.assertEqual(outputs["crop_count"], 1)
            crop = outputs["crops"][0]
            self.assertEqual(crop["id"], "refrigerator")
            self.assertTrue(Path(crop["output_path"]).exists())
            self.assertEqual(crop["width"], 34)
            self.assertEqual(crop["height"], 34)
            self.assertEqual(outputs["tripo_image_handoffs"][0]["arguments"]["image_path"], crop["output_path"])
            self.assertFalse(outputs["tripo_image_handoffs"][0]["arguments"]["confirm_spend"])
            updated_plan = json.loads(outputs["updated_reconstruction_plan_json"])
            self.assertEqual(updated_plan["crop_tasks"][0]["arguments"]["image_path"], crop["output_path"])
            self.assertEqual(updated_plan["asset_mapping"][0]["source"], crop["output_path"])

            batch = json.loads(mcp.tools["spatial_prepare_tripo_generation_batch"](
                ctx=None,
                composition_plan_json=outputs["updated_reconstruction_plan_json"],
                session_name="apartment_reference_rebuild",
            ))
            self.assertTrue(batch["success"])
            self.assertEqual(batch["outputs"]["status"], "needs_user_spend_confirmation")
            self.assertEqual(batch["outputs"]["blocked_by_crop_manifest_count"], 0)
            self.assertEqual(batch["outputs"]["jobs"][0]["submit"]["arguments"]["image_path"], crop["output_path"])
            self.assertTrue(batch["outputs"]["jobs"][0]["ready_for_submission"])
            self.assertEqual(batch["outputs"]["jobs"][0]["crop_readiness"]["status"], "ready_with_local_crop")

    def test_prepare_screenshot_crop_manifest_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        missing_source = json.loads(mcp.tools["spatial_prepare_screenshot_crop_manifest"](
            ctx=None,
            reference_image="",
        ))
        missing_file = json.loads(mcp.tools["spatial_prepare_screenshot_crop_manifest"](
            ctx=None,
            reference_image="C:/refs/does_not_exist.png",
            detected_items_json=json.dumps([{"name": "chair", "crop_box": [1, 2, 30, 40]}]),
        ))
        url_source = json.loads(mcp.tools["spatial_prepare_screenshot_crop_manifest"](
            ctx=None,
            reference_image="https://example.com/apartment.png",
            detected_items_json=json.dumps([{"name": "chair", "crop_box": [1, 2, 30, 40]}]),
        ))

        self.assertFalse(missing_source["success"])
        self.assertIn("reference_image is required", missing_source["errors"][0])
        self.assertFalse(missing_file["success"])
        self.assertIn("reference_image must be an existing local image file", missing_file["errors"][0])
        self.assertFalse(url_source["success"])
        self.assertIn("reference_image must be a local image file path", url_source["errors"][0])

    def test_plan_screenshot_reconstruction_maps_detected_props_to_crops_assets_and_placement(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "name": "refrigerator",
                "category": "appliance",
                "zone": "kitchen",
                "surface": "floor",
                "crop_box": [10, 20, 120, 240],
                "placement_hint": "against the left kitchen wall",
                "approx_size_cm": [90, 80, 190],
                "confidence": 0.91,
            },
            {
                "name": "books",
                "category": "dressing",
                "zone": "living",
                "surface": "table",
                "existing_asset_path": "/Game/Props/SM_Books.SM_Books",
                "placement_hint": "on the coffee table",
            },
        ]

        payload = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps(detected_items),
            room_type="apartment",
            room_dimensions=[700, 520, 280],
            style="lived-in modern",
            intent="reference rebuild",
            actor_label_prefix="AptRef",
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.SCREENSHOT_RECONSTRUCTION_SCHEMA)
        self.assertFalse(outputs["decomposition_required"])
        self.assertEqual(outputs["detected_item_count"], 2)
        self.assertEqual(len(outputs["crop_tasks"]), 1)
        crop_task = outputs["crop_tasks"][0]
        self.assertEqual(crop_task["tool"], "gen_tripo_image_to_model")
        self.assertEqual(crop_task["arguments"]["image_path"], "<CROP_FOR_refrigerator>")
        self.assertFalse(crop_task["arguments"]["confirm_spend"])
        mapping_by_id = {item["id"]: item for item in outputs["asset_mapping"]}
        self.assertEqual(mapping_by_id["refrigerator"]["action"], "tripo_image_to_model")
        self.assertEqual(mapping_by_id["books"]["action"], "existing_asset")
        self.assertEqual(mapping_by_id["books"]["matched_asset_path"], "/Game/Props/SM_Books.SM_Books")
        self.assertEqual(outputs["functional_zone_plan"]["schema"], spatial_awareness_tools.FUNCTIONAL_ZONE_INFERENCE_SCHEMA)
        self.assertIn("kitchen", outputs["functional_zone_plan"]["zone_names"])
        self.assertIn("living", outputs["functional_zone_plan"]["zone_names"])
        self.assertEqual(outputs["prop_program"]["schema"], spatial_awareness_tools.INTERIOR_PROP_PROGRAM_SCHEMA)
        self.assertEqual(outputs["prop_program"]["prop_count"], 2)
        self.assertEqual(outputs["prop_program"]["detected_prop_count"], 2)
        self.assertEqual(outputs["prop_program"]["generation_candidate_count"], 1)
        self.assertEqual(outputs["prop_program"]["existing_asset_match_count"], 1)
        self.assertFalse(outputs["prop_program"]["zone_recommendations_applied"])
        composition = outputs["composition_plan"]
        self.assertEqual(composition["schema"], spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA)
        self.assertTrue(composition["functional_zone_inference"]["applied"])
        self.assertTrue(composition["prop_program"]["applied"])
        self.assertEqual(composition["prop_program"]["prop_count"], 2)
        self.assertEqual(composition["placement_steps"][0]["tool"], "spatial_add_asset_to_scene")
        self.assertTrue(composition["placement_steps"][0]["arguments"]["dry_run"])
        fridge = next(prop for prop in composition["props"] if prop["id"] == "refrigerator")
        self.assertEqual(fridge["zone"], "kitchen")
        self.assertEqual(fridge["approx_size_cm"], [90.0, 80.0, 190.0])
        self.assertTrue(fridge["placement"]["source"].startswith("placement_hint_"))
        self.assertLess(fridge["placement"]["location"][0], -250.0)
        books_prop = next(prop for prop in composition["props"] if prop["id"] == "books")
        self.assertEqual(books_prop["placement"]["source"], "placement_hint_anchor_coffee_table")
        self.assertEqual(books_prop["placement"]["location"], [-35.0, 10.4, 47.0])
        steps_by_id = {step["id"]: step for step in composition["placement_steps"]}
        self.assertEqual(steps_by_id["books"]["arguments"]["placement_source"], "placement_hint_anchor_coffee_table")
        screenshot_workflow = [step["step"] for step in outputs["workflow"]]
        self.assertIn("infer_functional_zones", screenshot_workflow)
        self.assertIn("plan_prop_program", screenshot_workflow)
        composition_workflow = {step["step"]: step for step in composition["workflow"]}
        self.assertFalse(composition_workflow["plan_prop_program"]["enabled"])
        self.assertEqual(outputs["validation_handoff"]["tool"], "spatial_validate_placement")

    def test_plan_screenshot_reconstruction_turns_detected_openings_into_preflight_constraints(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "id": "entry_door",
                "name": "entry door",
                "category": "architectural",
                "zone": "entry",
                "surface": "wall",
                "crop_box": [30, 80, 90, 260],
                "placement_hint": "on the back entry wall",
                "approx_size_cm": [100, 12, 220],
                "confidence": 0.94,
            },
            {
                "name": "sofa",
                "category": "seating",
                "zone": "living",
                "surface": "floor",
                "existing_asset_path": "/Game/Props/SM_Sofa.SM_Sofa",
                "crop_box": [380, 310, 210, 95],
                "confidence": 0.89,
            },
        ]

        payload = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment_entry.png",
            detected_items_json=json.dumps(detected_items),
            room_type="apartment",
            room_dimensions=[500, 400, 280],
            actor_label_prefix="ShotRef",
            generate_missing_with_tripo=False,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["detected_opening_count"], 1)
        opening = outputs["detected_openings"][0]
        self.assertEqual(opening["source"], "screenshot_detection")
        self.assertEqual(opening["wall"], "positive_y")
        self.assertIn("opening", opening["roles"])
        self.assertEqual(opening["detected_item_id"], "entry_door")
        composition = outputs["composition_plan"]
        self.assertEqual(composition["screenshot_opening_constraints"]["opening_count"], 1)
        self.assertEqual(composition["room"]["openings"][0]["id"], opening["id"])
        self.assertEqual(composition["openings"][0]["id"], opening["id"])
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        self.assertTrue(workflow_by_step["preflight_detected_openings"]["enabled"])

        preflight_plan = json.loads(json.dumps(composition))
        blocker_location = [opening["center"][0], opening["center"][1] - 45.0, 0.0]
        preflight_plan["props"].append({
            "id": "entry_console",
            "name": "entry console",
            "category": "table",
            "zone": "entry",
            "surface": "floor",
            "approx_size_cm": [90, 65, 85],
            "placement": {"actor_label": "ShotRef_entry_console", "source": "manual_test"},
        })
        preflight_plan["placement_steps"].append({
            "id": "entry_console",
            "tool": "spatial_add_asset_to_scene",
            "arguments": {
                "actor_label": "ShotRef_entry_console",
                "asset_path": "/Game/Props/SM_EntryConsole.SM_EntryConsole",
                "location": blocker_location,
                "placement_source": "manual_test",
            },
        })

        preflight = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(preflight_plan),
            min_walkway_width=90,
            clearance_padding=0,
            pairwise_padding=0,
        ))

        self.assertTrue(preflight["success"])
        preflight_outputs = preflight["outputs"]
        self.assertEqual(preflight_outputs["opening_clearance_count"], 1)
        self.assertEqual(preflight_outputs["blocked_opening_count"], 1)
        self.assertEqual(preflight_outputs["opening_clearance"][0]["label"], opening["label"])
        issue_kinds = {issue["kind"] for issue in preflight_outputs["issues"]}
        self.assertIn("opening_clearance_blocked", issue_kinds)
        blocker_check = next(check for check in preflight_outputs["actor_checks"] if check["id"] == "entry_console")
        self.assertFalse(blocker_check["valid"])

    def test_plan_screenshot_reconstruction_consumes_scene_graph_constraints(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "name": "refrigerator",
                "category": "appliance",
                "zone": "kitchen",
                "surface": "floor",
                "crop_box": [40, 80, 120, 240],
                "confidence": 0.91,
            },
            {
                "name": "kitchen counter run",
                "zone": "kitchen",
                "surface": "floor",
                "crop_box": [220, 320, 220, 80],
                "confidence": 0.88,
            },
            {
                "name": "counter clutter",
                "zone": "kitchen",
                "surface": "counter",
                "crop_box": [260, 330, 50, 40],
                "confidence": 0.82,
            },
            {
                "name": "coffee table",
                "zone": "living",
                "surface": "floor",
                "crop_box": [450, 360, 120, 70],
                "confidence": 0.86,
            },
            {
                "name": "books",
                "zone": "living",
                "surface": "table",
                "existing_asset_path": "/Game/Props/SM_Books.SM_Books",
                "crop_box": [470, 360, 60, 40],
                "confidence": 0.9,
            },
        ]

        scene_graph = json.loads(mcp.tools["spatial_infer_screenshot_scene_graph"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps(detected_items),
            image_size=[800, 600],
            room_type="apartment",
        ))["outputs"]
        payload = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            scene_graph_json=json.dumps(scene_graph),
            room_type="apartment",
            room_dimensions=[700, 520, 280],
            actor_label_prefix="GraphRef",
        ))

        self.assertTrue(payload["success"])
        self.assertTrue(payload["inputs"]["scene_graph_applied"])
        self.assertEqual(payload["inputs"]["detected_item_count"], 5)
        outputs = payload["outputs"]
        self.assertFalse(outputs["decomposition_required"])
        self.assertTrue(outputs["scene_graph"]["applied"])
        self.assertEqual(outputs["scene_graph_context"]["relation_count"], scene_graph["relation_count"])
        detected_by_id = {item["id"]: item for item in outputs["detected_items"]}
        self.assertEqual(detected_by_id["books"]["placement_hint"], "on the coffee table")
        self.assertIn("on the counter", detected_by_id["counter_clutter"]["placement_hint"])
        self.assertIn("kitchen counter run", detected_by_id["counter_clutter"]["placement_hint"])
        relation_pairs = {
            (relation["source"], relation["relation"], relation["target"])
            for relation in outputs["scene_graph_context"]["relations"]
        }
        self.assertIn(("books", "supported_by", "coffee_table"), relation_pairs)
        self.assertIn(("counter_clutter", "supported_by", "kitchen_counter_run"), relation_pairs)
        composition = outputs["composition_plan"]
        props_by_id = {prop["id"]: prop for prop in composition["props"]}
        self.assertEqual(props_by_id["books"]["placement"]["source"], "placement_hint_anchor_coffee_table")
        self.assertEqual(props_by_id["counter_clutter"]["placement"]["source"], "placement_hint_anchor_counter")
        self.assertEqual(props_by_id["books"]["source"], "existing_asset")
        self.assertIn("review_scene_graph_constraints", [step["step"] for step in outputs["workflow"]])

    def test_plan_screenshot_reconstruction_uses_room_analysis_json(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis_json = json.dumps({
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {
                "type": "apartment",
                "dimensions_cm": [720, 540, 300],
                "origin": [10, 20, 0],
            },
            "surface_counts": {"floors": 1, "walls": 4},
            "planner_handoff": {
                "spatial_surface_probe": {"points": [[10, 20, 160]]},
            },
        })

        payload = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps([{"name": "refrigerator", "zone": "kitchen", "crop_box": [1, 2, 3, 4]}]),
            room_analysis_json=room_analysis_json,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertTrue(outputs["room_analysis"]["applied"])
        self.assertEqual(outputs["room"]["dimensions_cm"], [720.0, 540.0, 300.0])
        self.assertTrue(outputs["composition_plan"]["room_analysis"]["applied"])
        self.assertEqual(outputs["composition_plan"]["workflow"][0]["tool"], "spatial_analyze_room")
        workflow_by_step = {step["step"]: step for step in outputs["composition_plan"]["workflow"]}
        self.assertEqual(workflow_by_step["probe_surfaces"]["arguments"]["points"][0], [10.0, 20.0, 160.0])

    def test_plan_screenshot_reconstruction_validates_items_json(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        missing_reference = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="",
        ))
        invalid_json = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json="{not-json",
        ))
        invalid_crop = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps([{"name": "chair", "crop_box": [1, 2]}]),
        ))
        invalid_scene_graph = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            scene_graph_json=json.dumps({"schema": "wrong.schema"}),
        ))

        self.assertFalse(missing_reference["success"])
        self.assertIn("reference_image is required", missing_reference["errors"][0])
        self.assertFalse(invalid_json["success"])
        self.assertIn("detected_items_json must be a JSON list", invalid_json["errors"][0])
        self.assertFalse(invalid_crop["success"])
        self.assertIn("crop_box must be a list of four numbers", invalid_crop["errors"][0])
        self.assertFalse(invalid_scene_graph["success"])
        self.assertIn("scene_graph_json must have schema", invalid_scene_graph["errors"][0])

    def test_catalog_project_assets_builds_resolver_handoff(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            compile(code, "<spatial_catalog_project_assets>", "exec")
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {
                    "schema": spatial_awareness_tools.PROJECT_ASSET_CATALOG_SCHEMA,
                    "asset_count": 2,
                    "assets": [
                        {
                            "asset_path": "/Game/Props/Kitchen/SM_Refrigerator.SM_Refrigerator",
                            "asset_name": "SM_Refrigerator",
                            "class_name": "StaticMesh",
                            "tags": ["refrigerator", "kitchen"],
                            "approx_size_cm": [90.0, 80.0, 190.0],
                        },
                        {
                            "asset_path": "/Game/Props/Kitchen/BP_CounterRun.BP_CounterRun",
                            "asset_name": "BP_CounterRun",
                            "class_name": "Blueprint",
                            "tags": ["counter"],
                        },
                    ],
                    "asset_catalog_json": json.dumps({
                        "assets": [
                            {"asset_path": "/Game/Props/Kitchen/SM_Refrigerator.SM_Refrigerator"},
                            {"asset_path": "/Game/Props/Kitchen/BP_CounterRun.BP_CounterRun"},
                        ]
                    }),
                    "resolver_handoff": {
                        "tool": "spatial_resolve_project_assets",
                        "arguments": {"composition_plan_json": "<COMPOSITION_OR_SCREENSHOT_RECONSTRUCTION_JSON>"},
                        "enabled": True,
                    },
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_catalog_project_assets"](
                ctx=None,
                folders=["/Game/Props/Kitchen"],
                query="kitchen",
                class_names=["StaticMesh", "Blueprint"],
                include_bounds=True,
                limit=25,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.PROJECT_ASSET_CATALOG_SCHEMA)
        self.assertEqual(payload["inputs"]["folders"], ["/Game/Props/Kitchen"])
        self.assertEqual(payload["inputs"]["class_names"], ["StaticMesh", "Blueprint"])
        self.assertTrue(payload["inputs"]["include_bounds"])
        self.assertEqual(calls[0][1], "spatial_catalog_project_assets")
        code = calls[0][0]
        self.assertIn("AssetRegistryHelpers.get_asset_registry", code)
        self.assertIn("EditorAssetLibrary", code)
        self.assertIn("list_assets", code)
        self.assertIn("load_asset", code)
        self.assertIn("get_bounding_box", code)
        self.assertIn("approx_size_cm", code)
        self.assertIn("get_selected_assets", code)
        self.assertIn("spatial_resolve_project_assets", code)
        self.assertIn("asset_catalog_json", code)
        self.assertEqual(payload["outputs"]["resolver_handoff"]["tool"], "spatial_resolve_project_assets")

    def test_catalog_project_assets_validates_inputs_before_unreal_execution(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_structured") as fake_exec:
            invalid_folder = json.loads(mcp.tools["spatial_catalog_project_assets"](
                ctx=None,
                folders=["/Plugin/Props"],
            ))
            invalid_class_name = json.loads(mcp.tools["spatial_catalog_project_assets"](
                ctx=None,
                class_names=["x" * 129],
            ))

        self.assertFalse(invalid_folder["success"])
        self.assertIn("content_path must be a Content Browser folder under /Game", invalid_folder["errors"][0])
        self.assertFalse(invalid_class_name["success"])
        self.assertIn("class_names entries must be 128 characters or fewer", invalid_class_name["errors"][0])
        fake_exec.assert_not_called()

    def test_resolve_project_assets_prefers_existing_assets_before_tripo(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {"name": "refrigerator", "zone": "kitchen", "surface": "floor", "crop_box": [10, 20, 120, 240]},
            {"name": "books", "zone": "living", "surface": "table", "crop_box": [410, 360, 80, 60]},
            {"name": "counter clutter", "zone": "kitchen", "surface": "counter", "crop_box": [260, 330, 50, 40]},
            {"name": "wall cabinets", "zone": "kitchen", "surface": "wall", "crop_box": [250, 120, 180, 80]},
        ]
        reconstruction = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps(detected_items),
            room_type="apartment",
            room_dimensions=[700, 520, 280],
            actor_label_prefix="AptRef",
        ))
        asset_catalog = {
            "assets": [
                {
                    "asset_path": "/Game/Props/Kitchen/SM_Refrigerator.SM_Refrigerator",
                    "class_name": "StaticMesh",
                    "tags": ["refrigerator", "appliance", "kitchen"],
                },
                {
                    "asset_path": "/Game/Props/Living/SM_Books.SM_Books",
                    "class_name": "StaticMesh",
                    "tags": ["books", "table clutter"],
                },
                {
                    "asset_path": "/Game/Props/Kitchen/SM_CounterClutter.SM_CounterClutter",
                    "class_name": "StaticMesh",
                    "tags": ["counter clutter", "small appliance", "kitchen dressing"],
                },
                {
                    "asset_path": "/Game/Props/Lighting/SM_FloorLamp.SM_FloorLamp",
                    "class_name": "StaticMesh",
                    "tags": ["lamp"],
                },
            ]
        }

        payload = json.loads(mcp.tools["spatial_resolve_project_assets"](
            ctx=None,
            composition_plan_json=json.dumps(reconstruction),
            asset_catalog_json=json.dumps(asset_catalog),
            minimum_score=45,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.PROJECT_ASSET_RESOLUTION_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_binding")
        self.assertEqual(outputs["resolved_count"], 3)
        self.assertEqual(outputs["unresolved_count"], 1)
        self.assertEqual(outputs["asset_overrides"]["refrigerator"], "/Game/Props/Kitchen/SM_Refrigerator.SM_Refrigerator")
        self.assertEqual(outputs["asset_overrides"]["books"], "/Game/Props/Living/SM_Books.SM_Books")
        self.assertEqual(outputs["asset_overrides"]["counter_clutter"], "/Game/Props/Kitchen/SM_CounterClutter.SM_CounterClutter")
        unresolved = {item["id"] for item in outputs["unresolved_props"]}
        self.assertIn("wall_cabinets", unresolved)
        matches = {match["id"]: match for match in outputs["matches"]}
        self.assertGreaterEqual(matches["refrigerator"]["selected_score"], 45)
        self.assertTrue(outputs["binding_handoff"]["enabled"])
        self.assertEqual(outputs["binding_handoff"]["tool"], "spatial_bind_generated_assets_to_composition")
        self.assertEqual(
            outputs["tripo_batch_handoff"]["arguments"]["composition_plan_json"],
            "<SPATIAL_BIND_GENERATED_ASSETS_OUTPUT_JSON>",
        )

        binding = json.loads(mcp.tools["spatial_bind_generated_assets_to_composition"](
            ctx=None,
            **outputs["binding_handoff"]["arguments"],
        ))
        self.assertTrue(binding["success"])
        binding_outputs = binding["outputs"]
        self.assertEqual(binding_outputs["resolved_count"], 3)
        self.assertEqual(binding_outputs["unresolved_count"], 1)
        steps_by_id = {step["id"]: step for step in binding_outputs["placement_steps"]}
        self.assertEqual(
            steps_by_id["books"]["arguments"]["asset_path"],
            "/Game/Props/Living/SM_Books.SM_Books",
        )
        self.assertEqual(
            steps_by_id["counter_clutter"]["arguments"]["asset_binding_source"],
            "asset_override",
        )

    def test_resolve_project_assets_prefers_size_compatible_candidates(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        reconstruction = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps([
                {
                    "name": "refrigerator",
                    "zone": "kitchen",
                    "surface": "floor",
                    "crop_box": [10, 20, 120, 240],
                    "approx_size_cm": [90, 80, 190],
                }
            ]),
            room_type="apartment",
            room_dimensions=[700, 520, 280],
            actor_label_prefix="AptRef",
        ))
        asset_catalog = {
            "assets": [
                {
                    "asset_path": "/Game/Props/Kitchen/SM_RefrigeratorMini.SM_RefrigeratorMini",
                    "class_name": "StaticMesh",
                    "tags": ["refrigerator", "kitchen"],
                    "approx_size_cm": [35, 35, 55],
                },
                {
                    "asset_path": "/Game/Props/Kitchen/SM_RefrigeratorFull.SM_RefrigeratorFull",
                    "class_name": "StaticMesh",
                    "tags": ["refrigerator", "kitchen"],
                    "approx_size_cm": [92, 82, 188],
                },
            ]
        }

        payload = json.loads(mcp.tools["spatial_resolve_project_assets"](
            ctx=None,
            composition_plan_json=json.dumps(reconstruction),
            asset_catalog_json=json.dumps(asset_catalog),
            minimum_score=45,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        [match] = outputs["matches"]
        self.assertEqual(
            match["selected_asset_path"],
            "/Game/Props/Kitchen/SM_RefrigeratorFull.SM_RefrigeratorFull",
        )
        self.assertEqual(match["candidates"][0]["approx_size_cm"], [92.0, 82.0, 188.0])
        self.assertIn("size_close_match", match["candidates"][0]["reasons"])
        mini = next(candidate for candidate in match["candidates"] if "Mini" in candidate["asset_path"])
        self.assertIn("size_loose_mismatch", mini["reasons"])
        override_records = json.loads(outputs["asset_overrides_json"])
        self.assertEqual(
            override_records["refrigerator"]["approx_size_cm"],
            [92.0, 82.0, 188.0],
        )

        binding = json.loads(mcp.tools["spatial_bind_generated_assets_to_composition"](
            ctx=None,
            **outputs["binding_handoff"]["arguments"],
        ))
        self.assertTrue(binding["success"])
        review = binding["outputs"]["spatial_fit_reviews"][0]
        self.assertEqual(review["status"], "ready_for_spatial_validation")
        self.assertEqual(review["imported_size_cm"], [92.0, 82.0, 188.0])
        self.assertEqual(review["size_match"]["reason"], "size_close_match")

    def test_resolve_project_assets_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="apartment",
            required_props=["refrigerator"],
        ))

        missing_plan = json.loads(mcp.tools["spatial_resolve_project_assets"](
            ctx=None,
            composition_plan_json="",
            candidate_asset_paths=["/Game/Props/SM_Refrigerator.SM_Refrigerator"],
        ))
        missing_catalog = json.loads(mcp.tools["spatial_resolve_project_assets"](
            ctx=None,
            composition_plan_json=json.dumps(composition),
        ))
        invalid_catalog = json.loads(mcp.tools["spatial_resolve_project_assets"](
            ctx=None,
            composition_plan_json=json.dumps(composition),
            asset_catalog_json="{not-json",
        ))
        invalid_asset = json.loads(mcp.tools["spatial_resolve_project_assets"](
            ctx=None,
            composition_plan_json=json.dumps(composition),
            candidate_asset_paths=["NotAContentPath"],
        ))

        self.assertFalse(missing_plan["success"])
        self.assertIn("composition_plan_json is required", missing_plan["errors"][0])
        self.assertFalse(missing_catalog["success"])
        self.assertIn("asset_catalog_json or candidate_asset_paths is required", missing_catalog["errors"][0])
        self.assertFalse(invalid_catalog["success"])
        self.assertIn("asset_catalog_json must be valid JSON", invalid_catalog["errors"][0])
        self.assertFalse(invalid_asset["success"])
        self.assertIn("asset_path must be a Content Browser path", invalid_asset["errors"][0])

    def test_prepare_tripo_generation_batch_prefers_screenshot_crops_and_keeps_spend_guard(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "name": "refrigerator",
                "category": "appliance",
                "zone": "kitchen",
                "surface": "floor",
                "crop_box": [40, 80, 120, 240],
                "placement_hint": "against the left kitchen wall",
                "confidence": 0.91,
            },
            {
                "name": "books",
                "surface": "table",
                "existing_asset_path": "/Game/Props/SM_Books.SM_Books",
                "crop_box": [420, 360, 80, 50],
                "placement_hint": "on the coffee table",
            },
        ]
        reconstruction = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/apartment.png",
            detected_items_json=json.dumps(detected_items),
            room_type="apartment",
            actor_label_prefix="AptRef",
        ))

        payload = json.loads(mcp.tools["spatial_prepare_tripo_generation_batch"](
            ctx=None,
            composition_plan_json=json.dumps(reconstruction),
            content_path="/Game/Generated/ApartmentProps",
            session_name="apartment_reference_rebuild",
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.TRIPO_GENERATION_BATCH_SCHEMA)
        self.assertEqual(outputs["status"], "needs_crop_review")
        self.assertEqual(outputs["job_count"], 1)
        self.assertEqual(outputs["ready_job_count"], 0)
        self.assertEqual(outputs["not_ready_job_count"], 1)
        self.assertEqual(outputs["blocked_by_crop_manifest_count"], 1)
        self.assertEqual(outputs["spatial_generation_brief_count"], 1)
        self.assertEqual(outputs["image_job_count"], 1)
        self.assertEqual(outputs["text_job_count"], 0)
        job = outputs["jobs"][0]
        self.assertEqual(job["id"], "refrigerator")
        self.assertEqual(job["mode"], "image_to_model")
        self.assertFalse(job["ready_for_submission"])
        self.assertEqual(job["crop_readiness"]["status"], "needs_crop_manifest")
        self.assertEqual(job["crop_readiness"]["next_tool"], "spatial_prepare_screenshot_crop_manifest")
        self.assertEqual(job["submit"]["tool"], "gen_tripo_image_to_model")
        self.assertFalse(job["submit"]["arguments"]["confirm_spend"])
        self.assertEqual(job["submit"]["arguments"]["session_name"], "apartment_reference_rebuild")
        self.assertEqual(job["import"]["arguments"]["content_path"], "/Game/Generated/ApartmentProps")
        self.assertEqual(job["placement_after_import"]["tool"], "spatial_add_asset_to_scene")
        self.assertEqual(job["placement_after_import"]["arguments"]["actor_label"], "AptRef_refrigerator")
        self.assertEqual(job["spatial_fit"]["surface"], "floor")
        self.assertIn("stable flat base", " ".join(job["review_requirements"]))
        self.assertEqual(job["spatial_generation_brief"]["schema"], spatial_awareness_tools.SPATIAL_GENERATION_BRIEF_SCHEMA)
        self.assertEqual(job["spatial_generation_brief"]["room"]["dimensions_cm"], [650.0, 500.0, 280.0])
        self.assertEqual(job["spatial_generation_brief"]["placement"]["actor_label"], "AptRef_refrigerator")
        self.assertEqual(job["spatial_generation_brief"]["surface"], "floor")
        self.assertIn("spatial generation brief", job["spatial_generation_brief_prompt"])
        self.assertEqual(job["text_fallback_submit"]["tool"], "gen_tripo_text_to_model")
        self.assertIn("spatial fit", job["text_fallback_submit"]["arguments"]["prompt"])
        self.assertIn("spatial generation brief", job["text_fallback_submit"]["arguments"]["prompt"])
        pipeline_by_step = {step["step"]: step for step in job["guarded_pipeline"]}
        self.assertEqual(pipeline_by_step["review_generation_prompt"]["tool"], "gen_tripo_image_to_model")
        self.assertEqual(pipeline_by_step["review_spatial_generation_brief"]["brief"]["surface"], "floor")
        self.assertEqual(pipeline_by_step["prepare_image_crop"]["status"], "required_before_image_submission")
        self.assertTrue(pipeline_by_step["prepare_image_crop"]["blocking"])
        self.assertEqual(pipeline_by_step["confirm_tripo_spend"]["status"], "requires_user_confirmation")
        self.assertTrue(pipeline_by_step["confirm_tripo_spend"]["blocking"])
        self.assertEqual(pipeline_by_step["submit_tripo_generation"]["status"], "blocked_by_crop_review")
        self.assertEqual(
            pipeline_by_step["validate_generated_asset_placement"]["arguments"]["actors"],
            ["AptRef_refrigerator"],
        )
        self.assertEqual(outputs["guarded_pipeline_summary"]["job_count"], 1)
        self.assertEqual(outputs["guarded_pipeline_summary"]["spatial_generation_brief_count"], 1)
        self.assertEqual(outputs["guarded_pipeline_summary"]["blocked_by_crop_manifest_count"], 1)
        self.assertTrue(outputs["guarded_pipeline_summary"]["spend_confirmation_required"])
        self.assertEqual(outputs["guarded_pipeline_summary"]["blocked_by_spend_confirmation_count"], 0)
        self.assertIn("review_spatial_generation_brief", outputs["guarded_pipeline_summary"]["required_sequence"])
        self.assertIn("prepare_image_crop", outputs["guarded_pipeline_summary"]["required_sequence"])
        self.assertIn("validate_generated_asset_placement", outputs["guarded_pipeline_summary"]["required_sequence"])
        self.assertTrue(outputs["spend_policy"]["user_confirmation_required"])
        self.assertEqual(outputs["post_import_binding_handoff"]["tool"], "spatial_bind_generated_assets_to_composition")
        self.assertIn("review_spatial_generation_briefs", [step["step"] for step in outputs["workflow"]])
        self.assertIn("review_spatial_fit", [step["step"] for step in outputs["workflow"]])
        self.assertIn("submit_tripo_jobs", [step["step"] for step in outputs["workflow"]])

    def test_prepare_tripo_generation_batch_uses_text_tasks_and_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition = json.loads(mcp.tools["spatial_plan_interior_composition"](
            ctx=None,
            room_type="apartment",
            required_props=["fridge"],
            actor_label_prefix="Apt",
        ))

        payload = json.loads(mcp.tools["spatial_prepare_tripo_generation_batch"](
            ctx=None,
            composition_plan_json=json.dumps(composition),
            confirm_spend=True,
            prefer_image_crops=True,
        ))
        missing_plan = json.loads(mcp.tools["spatial_prepare_tripo_generation_batch"](
            ctx=None,
            composition_plan_json="",
        ))
        wrong_schema = json.loads(mcp.tools["spatial_prepare_tripo_generation_batch"](
            ctx=None,
            composition_plan_json=json.dumps({"schema": spatial_awareness_tools.SCREENSHOT_DECOMPOSITION_PREFLIGHT_SCHEMA}),
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "ready_for_tripo_submission")
        self.assertEqual(outputs["job_count"], 1)
        self.assertEqual(outputs["jobs"][0]["mode"], "text_to_model")
        self.assertEqual(outputs["jobs"][0]["submit"]["tool"], "gen_tripo_text_to_model")
        self.assertTrue(outputs["jobs"][0]["submit"]["arguments"]["confirm_spend"])
        self.assertEqual(outputs["jobs"][0]["spatial_fit"]["zone"], "kitchen")
        self.assertIn("spatial fit", outputs["jobs"][0]["submit"]["arguments"]["prompt"])
        self.assertIn("spatial generation brief", outputs["jobs"][0]["submit"]["arguments"]["prompt"])
        self.assertEqual(outputs["jobs"][0]["spatial_generation_brief"]["mode"], "text_to_model")
        pipeline_by_step = {step["step"]: step for step in outputs["jobs"][0]["guarded_pipeline"]}
        self.assertEqual(pipeline_by_step["confirm_tripo_spend"]["status"], "approved")
        self.assertEqual(pipeline_by_step["submit_tripo_generation"]["status"], "ready")
        self.assertTrue(outputs["guarded_pipeline_summary"]["spend_confirmed"])
        self.assertEqual(outputs["guarded_pipeline_summary"]["blocked_by_spend_confirmation_count"], 0)
        self.assertFalse(outputs["spend_policy"]["user_confirmation_required"])
        self.assertEqual(outputs["import_handoffs"][0]["tool"], "gen_tripo_import_to_project")
        self.assertFalse(missing_plan["success"])
        self.assertIn("composition_plan_json is required", missing_plan["errors"][0])
        self.assertFalse(wrong_schema["success"])
        self.assertIn("composition_plan_json must have schema", wrong_schema["errors"][0])

    def test_prepare_tripo_generation_batch_briefs_wall_mount_image_jobs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "id": "wall_cabinets",
                "name": "wall cabinets",
                "category": "storage",
                "zone": "kitchen",
                "surface": "wall",
                "crop_box": [210, 80, 220, 90],
                "placement_hint": "mounted on the back kitchen wall",
                "approx_size_cm": [220, 40, 80],
                "confidence": 0.88,
            }
        ]
        reconstruction = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/kitchen_wall.png",
            detected_items_json=json.dumps(detected_items),
            room_type="apartment",
            room_dimensions=[500, 400, 280],
            actor_label_prefix="BriefWall",
            generate_missing_with_tripo=True,
        ))

        payload = json.loads(mcp.tools["spatial_prepare_tripo_generation_batch"](
            ctx=None,
            composition_plan_json=json.dumps(reconstruction),
            session_name="wall_mount_reference_rebuild",
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["job_count"], 1)
        self.assertEqual(outputs["status"], "needs_crop_review")
        self.assertEqual(outputs["blocked_by_crop_manifest_count"], 1)
        job = outputs["jobs"][0]
        self.assertEqual(job["id"], "wall_cabinets")
        self.assertEqual(job["mode"], "image_to_model")
        self.assertFalse(job["ready_for_submission"])
        self.assertEqual(job["crop_readiness"]["status"], "needs_crop_manifest")
        self.assertEqual(job["spatial_generation_brief"]["surface"], "wall")
        self.assertEqual(job["spatial_generation_brief"]["approx_size_cm"], [220.0, 40.0, 80.0])
        self.assertEqual(job["spatial_generation_brief"]["placement"]["actor_label"], "BriefWall_wall_cabinets")
        self.assertIn("mounted on the back kitchen wall", job["spatial_generation_brief"]["placement"]["placement_hint"])
        self.assertIn("flat back or mounting face", job["spatial_generation_brief"]["contact_requirement"])
        self.assertIn("surface/contact wall", job["spatial_generation_brief_prompt"])
        self.assertIn("flat back or mounting face", " ".join(job["review_requirements"]))
        pipeline_by_step = {step["step"]: step for step in job["guarded_pipeline"]}
        self.assertEqual(pipeline_by_step["review_spatial_generation_brief"]["brief"]["surface"], "wall")
        self.assertEqual(pipeline_by_step["prepare_image_crop"]["status"], "required_before_image_submission")

    def test_bind_generated_assets_to_composition_replaces_placeholders(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "props": [
                {
                    "id": "refrigerator",
                    "name": "refrigerator",
                    "source": "existing_asset",
                    "matched_asset_path": "/Game/Props/SM_Refrigerator.SM_Refrigerator",
                    "placement": {"actor_label": "Apt_refrigerator"},
                },
                {
                    "id": "counter_clutter",
                    "name": "counter clutter",
                    "source": "tripo_candidate",
                    "zone": "kitchen",
                    "surface": "counter",
                    "approx_size_cm": [45, 28, 20],
                    "asset_path_placeholder": "/Game/Generated/SpatialInteriors/counter_clutter.counter_clutter",
                    "placement": {"actor_label": "Apt_counter_clutter"},
                    "spatial_fit": {
                        "prop_id": "counter_clutter",
                        "zone": "kitchen",
                        "surface": "counter",
                        "approx_size_cm": [45, 28, 20],
                        "contact_requirement": "stable underside sized for countertop contact",
                        "generation_requirements": [
                            "single prop asset only, not a full room",
                            "stable underside sized for countertop contact",
                        ],
                    },
                },
                {
                    "id": "wall_cabinets",
                    "name": "wall cabinets",
                    "source": "tripo_candidate",
                    "placement": {"actor_label": "Apt_wall_cabinets"},
                },
            ],
            "generation_tasks": [
                {
                    "id": "wall_cabinets",
                    "prop_name": "wall cabinets",
                    "submit": {"tool": "gen_tripo_text_to_model", "arguments": {"confirm_spend": False}},
                    "wait": {"tool": "gen_tripo_wait_for_task", "arguments": {"task_id": "<TRIPO_TASK_ID_FOR_wall_cabinets>"}},
                    "import": {"tool": "gen_tripo_import_to_project", "arguments": {"asset_name": "wall_cabinets"}},
                }
            ],
            "placement_steps": [
                {
                    "id": "refrigerator",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_Refrigerator.SM_Refrigerator",
                        "actor_label": "Apt_refrigerator",
                        "location": [-120, -150, 0],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                        "dry_run": True,
                        "allow_mutation": False,
                    },
                },
                {
                    "id": "counter_clutter",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "<IMPORTED_ASSET_PATH_FOR_counter_clutter>",
                        "actor_label": "Apt_counter_clutter",
                        "location": [10, 20, 98],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                        "dry_run": True,
                        "allow_mutation": False,
                    },
                },
                {
                    "id": "wall_cabinets",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "<IMPORTED_ASSET_PATH_FOR_wall_cabinets>",
                        "actor_label": "Apt_wall_cabinets",
                        "location": [40, -150, 160],
                        "rotation": [0, 90, 0],
                        "scale": [1, 1, 1],
                        "dry_run": True,
                        "allow_mutation": False,
                    },
                },
            ],
        }
        import_result = {
            "success": True,
            "stage": "gen_tripo_import_to_project",
            "inputs": {"task_id": "task-counter-clutter", "asset_name": "counter_clutter"},
            "outputs": {
                "task_id": "task-counter-clutter",
                "asset_paths": {
                    "primary_asset": "/Game/Generated/SpatialInteriors/SM_CounterClutter.SM_CounterClutter",
                    "imported_object_paths": ["/Game/Generated/SpatialInteriors/SM_CounterClutter.SM_CounterClutter"],
                },
                "bounds": {"size": [48, 30, 18]},
            },
        }

        payload = json.loads(mcp.tools["spatial_bind_generated_assets_to_composition"](
            ctx=None,
            composition_plan_json=json.dumps({
                "schema": spatial_awareness_tools.SPATIAL_RESULT_SCHEMA,
                "outputs": composition_plan,
            }),
            import_results_json=json.dumps([import_result]),
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.COMPOSITION_ASSET_BINDING_SCHEMA)
        self.assertEqual(outputs["status"], "waiting_for_generated_assets")
        self.assertEqual(outputs["resolved_count"], 2)
        self.assertEqual(outputs["unresolved_count"], 1)
        steps_by_id = {step["id"]: step for step in outputs["placement_steps"]}
        self.assertEqual(
            steps_by_id["counter_clutter"]["arguments"]["asset_path"],
            "/Game/Generated/SpatialInteriors/SM_CounterClutter.SM_CounterClutter",
        )
        self.assertEqual(steps_by_id["counter_clutter"]["arguments"]["asset_binding_source"], "tripo_import_result")
        self.assertTrue(steps_by_id["counter_clutter"]["arguments"]["dry_run"])
        self.assertFalse(steps_by_id["counter_clutter"]["arguments"]["allow_mutation"])
        reviews = {review["id"]: review for review in outputs["spatial_fit_reviews"]}
        self.assertEqual(outputs["spatial_fit_review_count"], 2)
        self.assertEqual(outputs["spatial_fit_review_summary"]["ready_count"], 1)
        self.assertEqual(outputs["spatial_fit_review_summary"]["unresolved_count"], 1)
        self.assertEqual(reviews["counter_clutter"]["status"], "ready_for_spatial_validation")
        self.assertEqual(reviews["counter_clutter"]["planned_size_cm"], [45.0, 28.0, 20.0])
        self.assertEqual(reviews["counter_clutter"]["imported_size_cm"], [48.0, 30.0, 18.0])
        self.assertEqual(reviews["counter_clutter"]["size_match"]["reason"], "size_close_match")
        self.assertIn("stable underside sized for countertop contact", reviews["counter_clutter"]["review_requirements"])
        self.assertEqual(steps_by_id["counter_clutter"]["spatial_fit_review"]["status"], "ready_for_spatial_validation")
        self.assertEqual(reviews["wall_cabinets"]["status"], "waiting_for_import_result")
        self.assertEqual(outputs["generation_follow_up"][0]["id"], "wall_cabinets")
        self.assertEqual(outputs["generation_follow_up"][0]["submit"]["tool"], "gen_tripo_text_to_model")
        self.assertEqual(
            outputs["validation_handoff"]["arguments"]["actors"],
            ["Apt_refrigerator", "Apt_counter_clutter"],
        )
        workflow_by_step = {step["step"]: step for step in outputs["workflow"]}
        self.assertEqual(workflow_by_step["review_spatial_fit"]["reviews"][0]["id"], "counter_clutter")
        self.assertEqual(workflow_by_step["place_resolved_assets"]["tool"], "spatial_apply_composition_plan")
        bindings = {binding["id"]: binding for binding in outputs["asset_bindings"]}
        self.assertEqual(bindings["wall_cabinets"]["status"], "unresolved")

    def test_bind_generated_assets_accepts_manual_overrides_and_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "placement_steps": [
                {
                    "id": "sink",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "<IMPORTED_ASSET_PATH_FOR_sink>",
                        "actor_label": "Apt_sink",
                        "location": [0, 0, 95],
                    },
                }
            ],
        }

        payload = json.loads(mcp.tools["spatial_bind_generated_assets_to_composition"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            asset_overrides_json=json.dumps({"sink": "/Game/Props/SM_Sink.SM_Sink"}),
        ))
        missing_plan = json.loads(mcp.tools["spatial_bind_generated_assets_to_composition"](
            ctx=None,
            composition_plan_json="",
        ))
        invalid_import_json = json.loads(mcp.tools["spatial_bind_generated_assets_to_composition"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            import_results_json="{not-json",
        ))
        invalid_override = json.loads(mcp.tools["spatial_bind_generated_assets_to_composition"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            asset_overrides_json=json.dumps({"sink": "NotAContentPath"}),
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "ready_for_dry_run_placement")
        self.assertEqual(outputs["resolved_count"], 1)
        self.assertEqual(outputs["placement_steps"][0]["arguments"]["asset_path"], "/Game/Props/SM_Sink.SM_Sink")
        self.assertEqual(outputs["placement_steps"][0]["arguments"]["asset_binding_source"], "asset_override")
        self.assertFalse(missing_plan["success"])
        self.assertIn("composition_plan_json is required", missing_plan["errors"][0])
        self.assertFalse(invalid_import_json["success"])
        self.assertIn("import_results_json must be valid JSON", invalid_import_json["errors"][0])
        self.assertFalse(invalid_override["success"])
        self.assertIn("asset_path must be a Content Browser path", invalid_override["errors"][0])

    def test_plan_asset_scale_corrections_updates_binding_for_scaled_dry_run(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        binding_output = {
            "schema": spatial_awareness_tools.COMPOSITION_ASSET_BINDING_SCHEMA,
            "room": {"type": "apartment", "dimensions_cm": [420, 320, 280], "origin": [0, 0, 0]},
            "bound_props": [
                {
                    "id": "refrigerator",
                    "name": "refrigerator",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [90, 80, 190],
                    "placement": {"actor_label": "Apt_refrigerator"},
                }
            ],
            "asset_bindings": [
                {
                    "status": "resolved",
                    "id": "refrigerator",
                    "actor_label": "Apt_refrigerator",
                    "asset_path": "/Game/Generated/SpatialInteriors/SM_TripoFridge.SM_TripoFridge",
                    "source": "tripo_import_result",
                    "bounds": {"size": [180, 160, 380]},
                }
            ],
            "spatial_fit_reviews": [
                {
                    "id": "refrigerator",
                    "prop_name": "refrigerator",
                    "actor_label": "Apt_refrigerator",
                    "asset_path": "/Game/Generated/SpatialInteriors/SM_TripoFridge.SM_TripoFridge",
                    "status": "needs_size_review",
                    "planned_size_cm": [90, 80, 190],
                    "imported_size_cm": [180, 160, 380],
                    "size_match": {"reason": "size_loose_mismatch", "score": -10},
                    "review_requirements": ["rescale, regenerate, or replace the asset before final placement"],
                }
            ],
            "all_placement_steps": [
                {
                    "id": "refrigerator",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Generated/SpatialInteriors/SM_TripoFridge.SM_TripoFridge",
                        "actor_label": "Apt_refrigerator",
                        "location": [-120, -90, 0],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                    },
                }
            ],
        }

        payload = json.loads(mcp.tools["spatial_plan_asset_scale_corrections"](
            ctx=None,
            composition_plan_json=json.dumps(binding_output),
        ))
        apply_payload = json.loads(mcp.tools["spatial_apply_composition_plan"](
            ctx=None,
            composition_plan_json=json.dumps(payload["outputs"]),
            dry_run=True,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.ASSET_SCALE_CORRECTION_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_scaled_dry_run")
        self.assertEqual(outputs["correction_count"], 1)
        correction = outputs["corrections"][0]
        self.assertEqual(correction["status"], "ready_for_scaled_dry_run")
        self.assertEqual(correction["scale_mode"], "uniform")
        self.assertEqual(correction["recommended_scale"], [0.5, 0.5, 0.5])
        updated_step = outputs["updated_composition_plan"]["placement_steps"][0]
        self.assertEqual(updated_step["arguments"]["scale"], [0.5, 0.5, 0.5])
        self.assertTrue(updated_step["arguments"]["dry_run"])
        self.assertFalse(updated_step["arguments"]["allow_mutation"])
        updated_review = outputs["updated_spatial_fit_reviews"][0]
        self.assertEqual(updated_review["status"], "ready_for_scaled_spatial_validation")
        self.assertEqual(outputs["apply_handoff"]["tool"], "spatial_apply_composition_plan")
        self.assertTrue(outputs["candidate_clearance_handoff"]["enabled"])
        self.assertTrue(apply_payload["success"])
        self.assertEqual(apply_payload["outputs"]["status"], "ready_for_review")
        self.assertEqual(apply_payload["outputs"]["spatial_fit_blocker_count"], 0)

    def test_plan_asset_scale_corrections_blocks_distorted_generated_imports(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        binding_output = {
            "schema": spatial_awareness_tools.COMPOSITION_ASSET_BINDING_SCHEMA,
            "spatial_fit_reviews": [
                {
                    "id": "counter_run",
                    "actor_label": "Apt_counter",
                    "asset_path": "/Game/Generated/SpatialInteriors/SM_CounterRun.SM_CounterRun",
                    "status": "needs_size_review",
                    "planned_size_cm": [240, 65, 95],
                    "imported_size_cm": [720, 65, 190],
                    "size_match": {"reason": "size_strong_mismatch", "score": -45},
                }
            ],
            "all_placement_steps": [
                {
                    "id": "counter_run",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Generated/SpatialInteriors/SM_CounterRun.SM_CounterRun",
                        "actor_label": "Apt_counter",
                        "location": [0, -150, 0],
                        "scale": [1, 1, 1],
                    },
                }
            ],
        }

        payload = json.loads(mcp.tools["spatial_plan_asset_scale_corrections"](
            ctx=None,
            composition_plan_json=json.dumps(binding_output),
            anisotropy_tolerance=0.2,
        ))
        missing_plan = json.loads(mcp.tools["spatial_plan_asset_scale_corrections"](
            ctx=None,
            composition_plan_json="",
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "needs_regeneration_or_manual_review")
        self.assertEqual(outputs["blocker_count"], 1)
        self.assertEqual(outputs["blockers"][0]["status"], "needs_non_uniform_or_regenerate")
        self.assertFalse(outputs["apply_handoff"]["enabled"])
        self.assertTrue(outputs["tripo_regeneration_handoff"]["enabled"])
        self.assertIn("counter_run", outputs["tripo_regeneration_handoff"]["blocked_ids"])
        self.assertFalse(missing_plan["success"])
        self.assertIn("composition_plan_json is required", missing_plan["errors"][0])

    def test_plan_support_surface_anchors_retargets_binding_to_room_surfaces(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {"type": "kitchen", "dimensions_cm": [500, 380, 280], "origin": [0, 0, 0]},
            "zones": [
                {"name": "kitchen", "center": [0, 0, 0], "size": [460, 340, 280], "wall": "negative_y"},
            ],
            "classified_surfaces": {
                "floors": [
                    {
                        "label": "Kitchen_Floor",
                        "roles": ["floor"],
                        "top_center": [0, 0, 0],
                        "bounds": {"min": {"x": -250, "y": -190, "z": -5}, "max": {"x": 250, "y": 190, "z": 0}},
                    }
                ],
                "horizontal_supports": [
                    {
                        "label": "Counter_A",
                        "roles": ["horizontal_support"],
                        "top_center": [10, 20, 95],
                        "bounds": {"min": {"x": -80, "y": -20, "z": 0}, "max": {"x": 100, "y": 60, "z": 95}},
                    }
                ],
                "walls": [
                    {
                        "label": "Kitchen_Wall_A",
                        "roles": ["wall"],
                        "bounds": {"min": {"x": -220, "y": -160, "z": 0}, "max": {"x": 220, "y": -150, "z": 280}},
                    }
                ],
            },
        }
        binding_output = {
            "schema": spatial_awareness_tools.COMPOSITION_ASSET_BINDING_SCHEMA,
            "bound_props": [
                {
                    "id": "counter_clutter",
                    "name": "counter clutter",
                    "zone": "kitchen",
                    "surface": "counter",
                    "approx_size_cm": [35, 25, 25],
                    "placement": {"actor_label": "Apt_counter_clutter"},
                },
                {
                    "id": "wall_cabinets",
                    "name": "wall cabinets",
                    "zone": "kitchen",
                    "surface": "wall",
                    "approx_size_cm": [220, 40, 80],
                    "placement": {"actor_label": "Apt_wall_cabinets"},
                },
            ],
            "all_placement_steps": [
                {
                    "id": "counter_clutter",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Generated/SpatialInteriors/SM_Clutter.SM_Clutter",
                        "actor_label": "Apt_counter_clutter",
                        "location": [0, 0, 0],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                    },
                },
                {
                    "id": "wall_cabinets",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Generated/SpatialInteriors/SM_WallCabinets.SM_WallCabinets",
                        "actor_label": "Apt_wall_cabinets",
                        "location": [40, -80, 80],
                        "rotation": [0, 90, 0],
                        "scale": [1, 1, 1],
                    },
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_plan_support_surface_anchors"](
            ctx=None,
            composition_plan_json=json.dumps(binding_output),
            room_analysis_json=json.dumps(room_analysis),
        ))
        apply_payload = json.loads(mcp.tools["spatial_apply_composition_plan"](
            ctx=None,
            composition_plan_json=json.dumps(payload["outputs"]),
            dry_run=True,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.SUPPORT_SURFACE_ANCHOR_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_support_surface_review")
        self.assertEqual(outputs["anchored_count"], 2)
        self.assertEqual(outputs["blocker_count"], 0)
        anchors = {anchor["id"]: anchor for anchor in outputs["anchors"]}
        self.assertEqual(anchors["counter_clutter"]["support_actor"], "Counter_A")
        self.assertEqual(anchors["counter_clutter"]["anchored_location"], [10.0, 20.0, 97.0])
        self.assertEqual(anchors["wall_cabinets"]["support_actor"], "Kitchen_Wall_A")
        self.assertEqual(anchors["wall_cabinets"]["source"], "room_analysis_wall")
        steps_by_id = {step["id"]: step for step in outputs["updated_composition_plan"]["placement_steps"]}
        self.assertEqual(steps_by_id["counter_clutter"]["arguments"]["placement_source"], "room_analysis_horizontal_support")
        self.assertEqual(steps_by_id["counter_clutter"]["arguments"]["support_actor"], "Counter_A")
        self.assertEqual(steps_by_id["wall_cabinets"]["arguments"]["location"], [0.0, -155.0, 150.0])
        self.assertTrue(outputs["surface_probe_handoff"]["enabled"])
        self.assertTrue(outputs["layout_preflight_handoff"]["enabled"])
        self.assertTrue(outputs["candidate_clearance_handoff"]["enabled"])
        self.assertTrue(apply_payload["success"])
        self.assertEqual(apply_payload["outputs"]["status"], "ready_for_review")

    def test_plan_support_surface_anchors_uses_screenshot_composition_supports(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "id": "kitchen_counter_run",
                "name": "kitchen counter run",
                "category": "counter",
                "zone": "kitchen",
                "surface": "floor",
                "existing_asset_path": "/Game/Props/SM_Counter.SM_Counter",
                "crop_box": [180, 260, 260, 80],
                "placement_hint": "against the back kitchen wall",
                "approx_size_cm": [240, 65, 95],
                "confidence": 0.9,
            },
            {
                "id": "counter_clutter",
                "name": "counter clutter",
                "category": "dressing",
                "zone": "kitchen",
                "surface": "counter",
                "existing_asset_path": "/Game/Props/SM_CounterClutter.SM_CounterClutter",
                "crop_box": [240, 245, 70, 35],
                "placement_hint": "on the kitchen counter run",
                "approx_size_cm": [35, 25, 25],
                "confidence": 0.86,
            },
        ]
        reconstruction = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/kitchen_counter.png",
            detected_items_json=json.dumps(detected_items),
            room_type="apartment",
            room_dimensions=[500, 400, 280],
            actor_label_prefix="ShotSupport",
            generate_missing_with_tripo=False,
        ))

        payload = json.loads(mcp.tools["spatial_plan_support_surface_anchors"](
            ctx=None,
            composition_plan_json=json.dumps(reconstruction),
            room_analysis_json="",
            anchor_floor=True,
            anchor_horizontal_supports=True,
            anchor_walls=True,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "ready_for_support_surface_review")
        self.assertEqual(outputs["composition_support_surface_count"], 1)
        self.assertEqual(outputs["support_surface_source_summary"]["room_analysis_horizontal_support_count"], 0)
        self.assertEqual(outputs["support_surface_source_summary"]["merged_horizontal_support_count"], 1)
        support = outputs["composition_support_surfaces"][0]
        self.assertEqual(support["source_prop_id"], "kitchen_counter_run")
        self.assertEqual(support["support_kind"], "counter")
        self.assertIn("composition_support_surface", support["roles"])
        anchors = {anchor["id"]: anchor for anchor in outputs["anchors"]}
        self.assertEqual(anchors["counter_clutter"]["status"], "anchored")
        self.assertEqual(anchors["counter_clutter"]["source"], "composition_horizontal_support")
        self.assertEqual(anchors["counter_clutter"]["support_actor"], "ShotSupport_kitchen_counter_run")
        self.assertEqual(anchors["counter_clutter"]["anchored_location"][2], 97.0)
        steps_by_id = {step["id"]: step for step in outputs["updated_composition_plan"]["placement_steps"]}
        clutter_args = steps_by_id["counter_clutter"]["arguments"]
        self.assertEqual(clutter_args["placement_source"], "composition_horizontal_support")
        self.assertEqual(clutter_args["support_actor"], "ShotSupport_kitchen_counter_run")
        self.assertEqual(outputs["updated_composition_plan"]["support_surface_anchor_summary"]["composition_support_surface_count"], 1)

        preflight = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(outputs["updated_composition_plan"]),
            min_walkway_width=90,
        ))
        self.assertTrue(preflight["success"])
        issue_kinds = {issue["kind"] for issue in preflight["outputs"]["issues"]}
        self.assertNotIn("semantic_support_contact_unresolved", issue_kinds)

    def test_plan_support_surface_anchors_uses_composition_room_walls_for_screenshot_wall_props(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        detected_items = [
            {
                "id": "wall_cabinets",
                "name": "wall cabinets",
                "category": "storage",
                "zone": "kitchen",
                "surface": "wall",
                "existing_asset_path": "/Game/Props/SM_WallCabinets.SM_WallCabinets",
                "crop_box": [210, 80, 220, 90],
                "placement_hint": "mounted on the back kitchen wall",
                "approx_size_cm": [220, 40, 80],
                "confidence": 0.88,
            }
        ]
        reconstruction = json.loads(mcp.tools["spatial_plan_screenshot_reconstruction"](
            ctx=None,
            reference_image="C:/refs/kitchen_wall.png",
            detected_items_json=json.dumps(detected_items),
            room_type="apartment",
            room_dimensions=[500, 400, 280],
            actor_label_prefix="ShotWall",
            generate_missing_with_tripo=False,
        ))

        payload = json.loads(mcp.tools["spatial_plan_support_surface_anchors"](
            ctx=None,
            composition_plan_json=json.dumps(reconstruction),
            room_analysis_json="",
            anchor_floor=True,
            anchor_horizontal_supports=True,
            anchor_walls=True,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "ready_for_support_surface_review")
        self.assertGreaterEqual(outputs["composition_wall_surface_count"], 1)
        self.assertEqual(outputs["support_surface_source_summary"]["room_analysis_wall_count"], 0)
        self.assertGreaterEqual(outputs["support_surface_source_summary"]["merged_wall_count"], 1)
        wall = next(surface for surface in outputs["composition_wall_surfaces"] if surface["zone"] == "kitchen")
        self.assertEqual(wall["wall"], "negative_y")
        self.assertIn("composition_wall_surface", wall["roles"])
        anchors = {anchor["id"]: anchor for anchor in outputs["anchors"]}
        self.assertEqual(anchors["wall_cabinets"]["status"], "anchored")
        self.assertEqual(anchors["wall_cabinets"]["source"], "composition_room_wall")
        self.assertEqual(anchors["wall_cabinets"]["support_actor"], wall["label"])
        self.assertIn("composition_wall_surface", anchors["wall_cabinets"]["support_roles"])
        self.assertEqual(anchors["wall_cabinets"]["anchored_location"][2], 150.0)
        steps_by_id = {step["id"]: step for step in outputs["updated_composition_plan"]["placement_steps"]}
        wall_args = steps_by_id["wall_cabinets"]["arguments"]
        self.assertEqual(wall_args["placement_source"], "composition_room_wall")
        self.assertEqual(wall_args["support_actor"], wall["label"])
        self.assertEqual(outputs["updated_composition_plan"]["support_surface_anchor_summary"]["composition_wall_surface_count"], outputs["composition_wall_surface_count"])

        preflight = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(outputs["updated_composition_plan"]),
            min_walkway_width=90,
        ))
        self.assertTrue(preflight["success"])
        issue_kinds = {issue["kind"] for issue in preflight["outputs"]["issues"]}
        self.assertNotIn("wall_mount_source_missing", issue_kinds)
        self.assertNotIn("semantic_wall_anchor_unresolved", issue_kinds)

    def test_plan_support_surface_anchors_blocks_when_support_surface_missing(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {"type": "kitchen", "dimensions_cm": [500, 380, 280], "origin": [0, 0, 0]},
            "zones": [
                {"name": "kitchen", "center": [0, 0, 0], "size": [460, 340, 280], "wall": "negative_y"},
            ],
            "classified_surfaces": {
                "floors": [
                    {
                        "label": "Kitchen_Floor",
                        "roles": ["floor"],
                        "top_center": [0, 0, 0],
                        "bounds": {"min": {"x": -250, "y": -190, "z": -5}, "max": {"x": 250, "y": 190, "z": 0}},
                    }
                ],
                "horizontal_supports": [],
                "walls": [],
            },
        }
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "props": [
                {
                    "id": "counter_clutter",
                    "name": "counter clutter",
                    "zone": "kitchen",
                    "surface": "counter",
                    "approx_size_cm": [35, 25, 25],
                    "placement": {"actor_label": "Apt_counter_clutter"},
                }
            ],
            "placement_steps": [
                {
                    "id": "counter_clutter",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_Clutter.SM_Clutter",
                        "actor_label": "Apt_counter_clutter",
                        "location": [0, 0, 0],
                    },
                }
            ],
        }

        payload = json.loads(mcp.tools["spatial_plan_support_surface_anchors"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            room_analysis_json=json.dumps(room_analysis),
        ))
        missing_plan = json.loads(mcp.tools["spatial_plan_support_surface_anchors"](
            ctx=None,
            composition_plan_json="",
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "needs_surface_probe")
        self.assertEqual(outputs["blocker_count"], 1)
        self.assertEqual(outputs["blockers"][0]["status"], "needs_surface_probe")
        self.assertFalse(outputs["apply_handoff"]["enabled"])
        self.assertTrue(outputs["surface_probe_handoff"]["enabled"])
        self.assertFalse(missing_plan["success"])
        self.assertIn("composition_plan_json is required", missing_plan["errors"][0])

    def test_apply_composition_plan_dry_run_blocks_unresolved_generated_assets(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "placement_steps": [
                {
                    "id": "refrigerator",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_Refrigerator.SM_Refrigerator",
                        "actor_label": "Apt_refrigerator",
                        "location": [-120, -150, 0],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                        "tags": ["Kitchen"],
                    },
                },
                {
                    "id": "counter_clutter",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "<IMPORTED_ASSET_PATH_FOR_counter_clutter>",
                        "actor_label": "Apt_counter_clutter",
                        "location": [10, 20, 98],
                    },
                },
            ],
        }

        with patch.object(spatial_awareness_tools, "_exec_transactional") as fake_exec:
            payload = json.loads(mcp.tools["spatial_apply_composition_plan"](
                ctx=None,
                composition_plan_json=json.dumps(composition_plan),
                default_tags=["Interior"],
                default_data_layer_names=["World_Interiors"],
                dry_run=True,
            ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.COMPOSITION_PLACEMENT_BATCH_SCHEMA)
        self.assertEqual(outputs["status"], "blocked_by_unresolved_assets")
        self.assertTrue(outputs["dry_run"])
        self.assertFalse(outputs["will_execute"])
        self.assertEqual(outputs["executable_count"], 1)
        self.assertEqual(outputs["unresolved_count"], 1)
        fridge = outputs["executable_steps"][0]
        self.assertEqual(fridge["id"], "refrigerator")
        self.assertEqual(fridge["arguments"]["tags"], ["Kitchen", "Interior"])
        self.assertEqual(fridge["arguments"]["data_layer_names"], ["World_Interiors"])
        self.assertEqual(outputs["validation_handoff"]["tool"], "spatial_validate_placement")
        self.assertEqual(outputs["validation_handoff"]["arguments"]["actors"], ["Apt_refrigerator"])
        self.assertEqual(outputs["unresolved_steps"][0]["id"], "counter_clutter")
        fake_exec.assert_not_called()

    def test_apply_composition_plan_mutation_gate_and_executes_resolved_steps(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "placement_steps": [
                {
                    "id": "sink",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_Sink.SM_Sink",
                        "actor_label": "Apt_sink",
                        "location": [0, -120, 95],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                    },
                },
                {
                    "id": "bar_stool",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_BarStool.SM_BarStool",
                        "actor_label": "Apt_bar_stool",
                        "location": [90, -40, 0],
                        "rotation": [0, 180, 0],
                        "scale": [1, 1, 1],
                    },
                },
            ],
        }
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, transaction_name: str) -> dict[str, Any]:
            calls.append((code, transaction_name))
            return {
                "success": True,
                "stage": "transaction_complete",
                "message": "Transaction committed",
                "outputs": {"schema": spatial_awareness_tools.ASSET_PLACEMENT_SCHEMA, "actor": {"label": transaction_name}},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_transactional", side_effect=fake_exec):
            gated = json.loads(mcp.tools["spatial_apply_composition_plan"](
                ctx=None,
                composition_plan_json=json.dumps(composition_plan),
                dry_run=False,
            ))
            executed = json.loads(mcp.tools["spatial_apply_composition_plan"](
                ctx=None,
                composition_plan_json=json.dumps(composition_plan),
                default_tags=["Interior"],
                dry_run=False,
                allow_mutation=True,
                focus_viewport=True,
            ))

        self.assertFalse(gated["success"])
        self.assertIn("allow_mutation=True", " ".join(gated["errors"]))
        self.assertEqual(len(calls), 2)
        self.assertTrue(executed["success"])
        outputs = executed["outputs"]
        self.assertEqual(outputs["status"], "executed")
        self.assertEqual(outputs["executed_count"], 2)
        self.assertEqual(outputs["failed_count"], 0)
        self.assertEqual(calls[0][1], "MCP Spatial Apply Composition: sink")
        self.assertIn("/Game/Props/SM_Sink.SM_Sink", calls[0][0])
        self.assertIn("spawn_actor_from_object", calls[0][0])
        self.assertEqual(outputs["execution_results"][1]["id"], "bar_stool")

    def test_apply_composition_plan_blocks_spatial_fit_review_failures(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        binding_output = {
            "schema": spatial_awareness_tools.COMPOSITION_ASSET_BINDING_SCHEMA,
            "spatial_fit_reviews": [
                {
                    "id": "counter_clutter",
                    "actor_label": "Apt_counter_clutter",
                    "asset_path": "/Game/Generated/SpatialInteriors/SM_CounterClutter.SM_CounterClutter",
                    "status": "needs_size_review",
                    "size_match": {"reason": "size_strong_mismatch", "score": -45},
                    "review_requirements": ["rescale, regenerate, or replace the asset before final placement"],
                }
            ],
            "placement_steps": [
                {
                    "id": "counter_clutter",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Generated/SpatialInteriors/SM_CounterClutter.SM_CounterClutter",
                        "actor_label": "Apt_counter_clutter",
                        "location": [10, 20, 98],
                    },
                }
            ],
        }

        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, transaction_name: str) -> dict[str, Any]:
            calls.append((code, transaction_name))
            return {
                "success": True,
                "stage": "transaction_complete",
                "outputs": {"schema": spatial_awareness_tools.ASSET_PLACEMENT_SCHEMA},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_transactional", side_effect=fake_exec):
            dry_run = json.loads(mcp.tools["spatial_apply_composition_plan"](
                ctx=None,
                composition_plan_json=json.dumps(binding_output),
                dry_run=True,
            ))
            blocked = json.loads(mcp.tools["spatial_apply_composition_plan"](
                ctx=None,
                composition_plan_json=json.dumps(binding_output),
                dry_run=False,
                allow_mutation=True,
            ))
            bypassed = json.loads(mcp.tools["spatial_apply_composition_plan"](
                ctx=None,
                composition_plan_json=json.dumps(binding_output),
                dry_run=False,
                allow_mutation=True,
                block_on_spatial_fit_review=False,
            ))

        self.assertTrue(dry_run["success"])
        self.assertEqual(dry_run["outputs"]["status"], "blocked_by_spatial_fit_review")
        self.assertEqual(dry_run["outputs"]["spatial_fit_review_count"], 1)
        self.assertEqual(dry_run["outputs"]["spatial_fit_blocker_count"], 1)
        queue_item = dry_run["outputs"]["placement_queue"][0]
        self.assertTrue(queue_item["spatial_fit_review_blocking"])
        self.assertEqual(queue_item["spatial_fit_review_status"], "needs_size_review")
        workflow_by_step = {step["step"]: step for step in dry_run["outputs"]["workflow"]}
        self.assertTrue(workflow_by_step["review_spatial_fit"]["enabled"])
        self.assertFalse(blocked["success"])
        self.assertEqual(blocked["outputs"]["status"], "blocked_by_spatial_fit_review")
        self.assertIn("blocked_by_spatial_fit_review", blocked["errors"][0])
        self.assertTrue(bypassed["success"])
        self.assertEqual(bypassed["outputs"]["status"], "executed")
        self.assertEqual(len(calls), 1)

    def test_apply_composition_plan_blocks_on_layout_preflight_errors_and_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "placement_steps": [
                {
                    "id": "sofa",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_Sofa.SM_Sofa",
                        "actor_label": "Apt_sofa",
                        "location": [0, 0, 0],
                    },
                }
            ],
        }
        layout_preflight = {
            "schema": spatial_awareness_tools.LAYOUT_PREFLIGHT_SCHEMA,
            "status": "blocked_by_preflight",
            "error_count": 1,
        }

        with patch.object(spatial_awareness_tools, "_exec_transactional") as fake_exec:
            blocked = json.loads(mcp.tools["spatial_apply_composition_plan"](
                ctx=None,
                composition_plan_json=json.dumps(composition_plan),
                layout_preflight_json=json.dumps(layout_preflight),
                dry_run=False,
                allow_mutation=True,
            ))
            missing_plan = json.loads(mcp.tools["spatial_apply_composition_plan"](
                ctx=None,
                composition_plan_json="",
            ))
            wrong_preflight = json.loads(mcp.tools["spatial_apply_composition_plan"](
                ctx=None,
                composition_plan_json=json.dumps(composition_plan),
                layout_preflight_json=json.dumps({"schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA}),
            ))

        self.assertFalse(blocked["success"])
        self.assertEqual(blocked["outputs"]["status"], "blocked_by_preflight")
        self.assertIn("blocked_by_preflight", blocked["errors"][0])
        self.assertFalse(missing_plan["success"])
        self.assertIn("composition_plan_json is required", missing_plan["errors"][0])
        self.assertFalse(wrong_preflight["success"])
        self.assertIn(spatial_awareness_tools.LAYOUT_PREFLIGHT_SCHEMA, wrong_preflight["errors"][0])
        fake_exec.assert_not_called()

    def test_preflight_interior_layout_flags_bounds_overlap_and_handoffs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {"type": "apartment", "dimensions_cm": [400, 300, 280], "origin": [0, 0, 0]},
            "zones": [
                {"name": "kitchen", "center": [-80, -80, 0], "size": [180, 130, 280], "wall": "negative_y"},
                {"name": "living", "center": [80, 60, 0], "size": [220, 160, 280], "wall": "open_center"},
            ],
            "props": [
                {
                    "id": "refrigerator",
                    "name": "refrigerator",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [100, 90, 190],
                    "placement": {"actor_label": "Apt_refrigerator"},
                },
                {
                    "id": "stove",
                    "name": "stove",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [90, 80, 95],
                    "placement": {"actor_label": "Apt_stove"},
                },
                {
                    "id": "bookshelf",
                    "name": "bookshelf",
                    "zone": "living",
                    "surface": "floor",
                    "approx_size_cm": [120, 40, 190],
                    "placement": {"actor_label": "Apt_bookshelf"},
                },
            ],
            "placement_steps": [
                {
                    "id": "refrigerator",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {"actor_label": "Apt_refrigerator", "asset_path": "/Game/Props/SM_Fridge.SM_Fridge", "location": [0, 0, 0]},
                },
                {
                    "id": "stove",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {"actor_label": "Apt_stove", "asset_path": "/Game/Props/SM_Stove.SM_Stove", "location": [20, 10, 0]},
                },
                {
                    "id": "bookshelf",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {"actor_label": "Apt_bookshelf", "asset_path": "/Game/Props/SM_Bookshelf.SM_Bookshelf", "location": [250, 0, 0]},
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            min_walkway_width=90,
            clearance_padding=12,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.LAYOUT_PREFLIGHT_SCHEMA)
        self.assertEqual(outputs["status"], "blocked_by_preflight")
        self.assertGreaterEqual(outputs["error_count"], 2)
        issue_kinds = {issue["kind"] for issue in outputs["issues"]}
        self.assertIn("outside_room_bounds", issue_kinds)
        self.assertIn("footprint_overlap", issue_kinds)
        self.assertIn("central_circulation_risk", issue_kinds)
        self.assertEqual(outputs["validation_handoff"]["tool"], "spatial_validate_placement")
        self.assertEqual(outputs["surface_probe_handoff"]["tool"], "spatial_surface_probe")
        actors = outputs["validation_handoff"]["arguments"]["actors"]
        self.assertIn("Apt_refrigerator", actors)
        self.assertIn("Apt_bookshelf", actors)

    def test_preflight_interior_layout_checks_semantic_constraints(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {"type": "kitchen", "dimensions_cm": [1000, 700, 280], "origin": [0, 0, 0]},
            "zones": [
                {"name": "kitchen", "center": [0, 0, 0], "size": [920, 620, 280], "wall": "negative_y"},
            ],
            "props": [
                {
                    "id": "kitchen_counter_run",
                    "name": "kitchen counter run",
                    "category": "counter",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [240, 65, 95],
                    "placement": {"actor_label": "Apt_counter", "source": "zone_heuristic"},
                },
                {
                    "id": "bar_stool",
                    "name": "bar stool",
                    "category": "seating",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [45, 45, 110],
                    "placement": {"actor_label": "Apt_bar_stool", "source": "zone_heuristic"},
                },
            ],
            "placement_steps": [
                {
                    "id": "kitchen_counter_run",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_counter",
                        "asset_path": "/Game/Props/SM_Counter.SM_Counter",
                        "location": [-220, -230, 0],
                    },
                },
                {
                    "id": "bar_stool",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_bar_stool",
                        "asset_path": "/Game/Props/SM_BarStool.SM_BarStool",
                        "location": [260, -230, 0],
                    },
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            min_walkway_width=90,
            clearance_padding=12,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "needs_review")
        semantic_kinds = {constraint["kind"] for constraint in outputs["semantic_constraints"]}
        self.assertIn("counter_adjacency", semantic_kinds)
        issue_kinds = {issue["kind"] for issue in outputs["issues"]}
        self.assertIn("semantic_counter_adjacency_gap", issue_kinds)
        stool_check = next(check for check in outputs["actor_checks"] if check["id"] == "bar_stool")
        self.assertIn("semantic_counter_adjacency_gap", {issue["kind"] for issue in stool_check["issues"]})

    def test_preflight_interior_layout_reports_interaction_clearance(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {"type": "kitchen", "dimensions_cm": [240, 220, 280], "origin": [0, 0, 0]},
            "zones": [
                {"name": "kitchen", "center": [0, 0, 0], "size": [220, 200, 280], "wall": "negative_y"},
            ],
            "props": [
                {
                    "id": "refrigerator",
                    "name": "refrigerator",
                    "category": "appliance",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [90, 80, 190],
                    "placement": {"actor_label": "Apt_refrigerator", "source": "zone_heuristic"},
                },
            ],
            "placement_steps": [
                {
                    "id": "refrigerator",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_refrigerator",
                        "asset_path": "/Game/Props/SM_Fridge.SM_Fridge",
                        "location": [0, 0, 0],
                    },
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            min_walkway_width=40,
            clearance_padding=0,
            pairwise_padding=0,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "needs_review")
        self.assertEqual(outputs["interaction_clearance_count"], 1)
        clearance = outputs["interaction_clearance"][0]
        self.assertEqual(clearance["kind"], "appliance_door_swing")
        self.assertEqual(clearance["status"], "tight_review")
        self.assertLess(clearance["available_cm"], clearance["required_cm"])
        self.assertEqual(clearance["front_margin_key"], "back")
        self.assertEqual(clearance["facing_direction"], "positive_y")
        issue = next(issue for issue in outputs["issues"] if issue["kind"] == "interaction_clearance_tight")
        self.assertEqual(issue["clearance_kind"], "appliance_door_swing")
        fridge_check = next(check for check in outputs["actor_checks"] if check["id"] == "refrigerator")
        self.assertEqual(fridge_check["interaction_clearance"]["kind"], "appliance_door_swing")
        self.assertIn("interaction_clearance_tight", {item["kind"] for item in fridge_check["issues"]})

    def test_preflight_interior_layout_uses_front_facing_clearance(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {"type": "kitchen", "dimensions_cm": [600, 220, 280], "origin": [0, 0, 0]},
            "zones": [
                {"name": "kitchen", "center": [-200, 0, 0], "size": [360, 200, 280], "wall": "negative_y"},
            ],
            "props": [
                {
                    "id": "refrigerator",
                    "name": "refrigerator",
                    "category": "appliance",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [90, 80, 190],
                    "placement": {"actor_label": "Apt_refrigerator", "source": "zone_heuristic"},
                },
            ],
            "placement_steps": [
                {
                    "id": "refrigerator",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_refrigerator",
                        "asset_path": "/Game/Props/SM_Fridge.SM_Fridge",
                        "location": [-200, 55, 0],
                        "rotation": [0, 0, 0],
                    },
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            min_walkway_width=40,
            clearance_padding=0,
            pairwise_padding=0,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "needs_review")
        clearance = outputs["interaction_clearance"][0]
        self.assertEqual(clearance["orientation_source"], "rotation_yaw")
        self.assertEqual(clearance["front_margin_key"], "back")
        self.assertEqual(clearance["facing_direction"], "positive_y")
        self.assertEqual(clearance["front_available_cm"], 15.0)
        self.assertEqual(clearance["available_cm"], 15.0)
        self.assertGreater(clearance["max_available_cm"], clearance["required_cm"])
        self.assertEqual(clearance["status"], "tight_review")
        issue = next(issue for issue in outputs["issues"] if issue["kind"] == "interaction_clearance_tight")
        self.assertEqual(issue["available_cm"], 15.0)

    def test_preflight_interior_layout_blocks_opening_clearance(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {
                "type": "apartment",
                "dimensions_cm": [500, 400, 280],
                "origin": [0, 0, 0],
            },
            "zones": [
                {"name": "entry", "center": [-160, 150, 0], "size": [160, 100, 280], "wall": "positive_y"},
                {"name": "living", "center": [80, 0, 0], "size": [260, 220, 280], "wall": "open_center"},
            ],
            "classified_surfaces": {
                "openings": [
                    {
                        "label": "Apartment_Entry_Door",
                        "roles": ["opening"],
                        "bounds": {
                            "min": {"x": -210, "y": 185, "z": 0},
                            "max": {"x": -110, "y": 200, "z": 220},
                        },
                    }
                ],
            },
        }
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {"type": "apartment", "dimensions_cm": [500, 400, 280], "origin": [0, 0, 0]},
            "zones": room_analysis["zones"],
            "props": [
                {
                    "id": "entry_console",
                    "name": "entry console",
                    "category": "table",
                    "zone": "entry",
                    "surface": "floor",
                    "approx_size_cm": [80, 70, 90],
                    "placement": {"actor_label": "Apt_entry_console", "source": "zone_heuristic"},
                },
            ],
            "placement_steps": [
                {
                    "id": "entry_console",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_entry_console",
                        "asset_path": "/Game/Props/SM_EntryConsole.SM_EntryConsole",
                        "location": [-160, 150, 0],
                    },
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            room_analysis_json=json.dumps(room_analysis),
            min_walkway_width=90,
            clearance_padding=0,
            pairwise_padding=0,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "blocked_by_preflight")
        self.assertEqual(outputs["opening_clearance_count"], 1)
        self.assertEqual(outputs["blocked_opening_count"], 1)
        opening = outputs["opening_clearance"][0]
        self.assertEqual(opening["label"], "Apartment_Entry_Door")
        self.assertEqual(opening["blocked_by"][0]["actor_label"], "Apt_entry_console")
        issue = next(issue for issue in outputs["issues"] if issue["kind"] == "opening_clearance_blocked")
        self.assertEqual(issue["severity"], "error")
        self.assertEqual(issue["opening_label"], "Apartment_Entry_Door")
        self.assertEqual(issue["recommended_tool"], "spatial_plan_composition_iteration")
        actor_check = next(check for check in outputs["actor_checks"] if check["id"] == "entry_console")
        self.assertFalse(actor_check["valid"])
        self.assertIn("opening_clearance_blocked", {item["kind"] for item in actor_check["issues"]})

    def test_preflight_interior_layout_reports_visual_sightline_obstruction(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        room_analysis = {
            "schema": spatial_awareness_tools.ROOM_ANALYSIS_SCHEMA,
            "room_model": {
                "type": "apartment",
                "dimensions_cm": [500, 400, 280],
                "origin": [0, 0, 0],
            },
            "zones": [
                {"name": "entry", "center": [0, -160, 0], "size": [160, 80, 280], "wall": "negative_y"},
                {"name": "living", "center": [0, 80, 0], "size": [280, 220, 280], "wall": "open_center"},
            ],
            "classified_surfaces": {
                "openings": [
                    {
                        "label": "Apartment_Entry_Door",
                        "roles": ["opening"],
                        "bounds": {
                            "min": {"x": -55, "y": -200, "z": 0},
                            "max": {"x": 55, "y": -185, "z": 220},
                        },
                    }
                ],
            },
        }
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {"type": "apartment", "dimensions_cm": [500, 400, 280], "origin": [0, 0, 0]},
            "zones": room_analysis["zones"],
            "props": [
                {
                    "id": "sofa",
                    "name": "sofa",
                    "category": "seating",
                    "zone": "living",
                    "surface": "floor",
                    "approx_size_cm": [180, 85, 90],
                    "placement": {"actor_label": "Apt_sofa", "source": "zone_heuristic"},
                },
                {
                    "id": "bookshelf",
                    "name": "bookshelf",
                    "category": "storage",
                    "zone": "living",
                    "surface": "floor",
                    "approx_size_cm": [90, 35, 190],
                    "placement": {"actor_label": "Apt_bookshelf", "source": "zone_heuristic"},
                },
            ],
            "placement_steps": [
                {
                    "id": "sofa",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_sofa",
                        "asset_path": "/Game/Props/SM_Sofa.SM_Sofa",
                        "location": [0, 120, 0],
                    },
                },
                {
                    "id": "bookshelf",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_bookshelf",
                        "asset_path": "/Game/Props/SM_Bookshelf.SM_Bookshelf",
                        "location": [0, -40, 0],
                    },
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            room_analysis_json=json.dumps(room_analysis),
            min_walkway_width=90,
            clearance_padding=0,
            pairwise_padding=0,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["status"], "needs_review")
        self.assertEqual(outputs["blocked_opening_count"], 0)
        self.assertEqual(outputs["visual_sightline_count"], 1)
        self.assertEqual(outputs["obstructed_sightline_count"], 1)
        sightline = outputs["visual_sightlines"][0]
        self.assertEqual(sightline["opening_label"], "Apartment_Entry_Door")
        self.assertEqual(sightline["target_actor_label"], "Apt_sofa")
        self.assertEqual(sightline["blockers"][0]["actor_label"], "Apt_bookshelf")
        issue = next(issue for issue in outputs["issues"] if issue["kind"] == "visual_sightline_obstructed")
        self.assertEqual(issue["severity"], "warning")
        self.assertEqual(issue["actor_label"], "Apt_bookshelf")
        self.assertEqual(issue["target_actor_label"], "Apt_sofa")
        bookshelf_check = next(check for check in outputs["actor_checks"] if check["id"] == "bookshelf")
        self.assertIn("visual_sightline_obstructed", {item["kind"] for item in bookshelf_check["issues"]})

    def test_preflight_interior_layout_accepts_binding_output_and_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        binding_output = {
            "schema": spatial_awareness_tools.COMPOSITION_ASSET_BINDING_SCHEMA,
            "bound_props": [
                {
                    "id": "sofa",
                    "name": "sofa",
                    "zone": "living",
                    "surface": "floor",
                    "approx_size_cm": [180, 85, 90],
                    "placement": {"actor_label": "Apt_sofa"},
                }
            ],
            "all_placement_steps": [
                {
                    "id": "sofa",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_Sofa.SM_Sofa",
                        "actor_label": "Apt_sofa",
                        "location": [220, 120, 0],
                    },
                }
            ],
        }

        payload = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps({
                "schema": spatial_awareness_tools.SPATIAL_RESULT_SCHEMA,
                "outputs": binding_output,
            }),
        ))
        missing_plan = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json="",
        ))
        wrong_schema = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps({"schema": spatial_awareness_tools.PLACEMENT_VALIDATION_SCHEMA}),
        ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.LAYOUT_PREFLIGHT_SCHEMA)
        self.assertEqual(payload["outputs"]["status"], "pass")
        self.assertEqual(payload["outputs"]["actor_count"], 1)
        self.assertFalse(missing_plan["success"])
        self.assertIn("composition_plan_json is required", missing_plan["errors"][0])
        self.assertFalse(wrong_schema["success"])
        self.assertIn(spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA, wrong_schema["errors"][0])

    def test_plan_layout_preflight_corrections_repairs_bounds_overlap_and_round_trips(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {"type": "apartment", "dimensions_cm": [500, 400, 280], "origin": [0, 0, 0]},
            "zones": [
                {"name": "kitchen", "center": [-100, -90, 0], "size": [240, 180, 280], "wall": "negative_y"},
                {"name": "living", "center": [100, 70, 0], "size": [260, 200, 280], "wall": "open_center"},
            ],
            "props": [
                {
                    "id": "refrigerator",
                    "name": "refrigerator",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [100, 90, 190],
                    "placement": {"actor_label": "Apt_refrigerator"},
                },
                {
                    "id": "stove",
                    "name": "stove",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [90, 80, 95],
                    "placement": {"actor_label": "Apt_stove"},
                },
                {
                    "id": "counter",
                    "name": "kitchen counter run",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [100, 80, 95],
                    "placement": {"actor_label": "Apt_counter"},
                },
            ],
            "placement_steps": [
                {
                    "id": "refrigerator",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_refrigerator",
                        "asset_path": "/Game/Props/SM_Fridge.SM_Fridge",
                        "location": [245, -120, 0],
                    },
                },
                {
                    "id": "stove",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_stove",
                        "asset_path": "/Game/Props/SM_Stove.SM_Stove",
                        "location": [0, 0, 0],
                    },
                },
                {
                    "id": "counter",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_counter",
                        "asset_path": "/Game/Props/SM_Counter.SM_Counter",
                        "location": [20, 10, 0],
                    },
                },
            ],
        }

        preflight = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            min_walkway_width=90,
            clearance_padding=12,
            pairwise_padding=8,
        ))
        payload = json.loads(mcp.tools["spatial_plan_layout_preflight_corrections"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            layout_preflight_json=json.dumps(preflight),
            boundary_margin_cm=12,
            pairwise_padding=12,
            min_walkway_width=90,
        ))
        apply_payload = json.loads(mcp.tools["spatial_apply_composition_plan"](
            ctx=None,
            composition_plan_json=json.dumps(payload),
            dry_run=True,
        ))

        self.assertTrue(preflight["success"])
        self.assertEqual(preflight["outputs"]["status"], "blocked_by_preflight")
        self.assertEqual(preflight["outputs"]["layout_correction_handoff"]["tool"], "spatial_plan_layout_preflight_corrections")
        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.LAYOUT_PREFLIGHT_CORRECTION_SCHEMA)
        self.assertEqual(outputs["status"], "ready_for_corrected_preflight")
        self.assertGreaterEqual(outputs["correction_count"], 2)
        self.assertEqual(outputs["blocker_count"], 0)
        issue_kinds = {item["issue_kind"] for item in outputs["corrections"]}
        self.assertIn("outside_room_bounds", issue_kinds)
        self.assertIn("footprint_overlap", issue_kinds)
        fridge_step = next(
            step for step in outputs["updated_placement_steps"]
            if step["arguments"]["actor_label"] == "Apt_refrigerator"
        )
        self.assertLess(fridge_step["arguments"]["location"][0], 245)
        self.assertTrue(fridge_step["arguments"]["dry_run"])
        self.assertFalse(fridge_step["arguments"]["allow_mutation"])
        self.assertTrue(outputs["layout_preflight_handoff"]["enabled"])
        self.assertTrue(outputs["apply_handoff"]["enabled"])
        self.assertTrue(apply_payload["success"])
        self.assertEqual(apply_payload["outputs"]["status"], "ready_for_review")
        self.assertEqual(apply_payload["outputs"]["placement_step_count"], 3)

    def test_plan_layout_preflight_corrections_blocks_oversized_room_fit(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {"type": "studio", "dimensions_cm": [200, 200, 260], "origin": [0, 0, 0]},
            "props": [
                {
                    "id": "sofa",
                    "name": "sofa",
                    "zone": "living",
                    "surface": "floor",
                    "approx_size_cm": [320, 250, 90],
                    "placement": {"actor_label": "Tiny_sofa"},
                }
            ],
            "placement_steps": [
                {
                    "id": "sofa",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Tiny_sofa",
                        "asset_path": "/Game/Props/SM_Sofa.SM_Sofa",
                        "location": [0, 0, 0],
                    },
                }
            ],
        }

        preflight = json.loads(mcp.tools["spatial_preflight_interior_layout"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            clearance_padding=12,
        ))
        payload = json.loads(mcp.tools["spatial_plan_layout_preflight_corrections"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            layout_preflight_json=json.dumps(preflight),
            boundary_margin_cm=12,
        ))
        missing_preflight = json.loads(mcp.tools["spatial_plan_layout_preflight_corrections"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            layout_preflight_json="",
        ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.LAYOUT_PREFLIGHT_CORRECTION_SCHEMA)
        self.assertEqual(payload["outputs"]["status"], "needs_manual_layout_review")
        self.assertEqual(payload["outputs"]["blocker_count"], 1)
        self.assertFalse(payload["outputs"]["apply_handoff"]["enabled"])
        self.assertIn("spatial_plan_asset_scale_corrections", payload["outputs"]["blockers"][0]["recommended_next_tools"])
        self.assertFalse(missing_preflight["success"])
        self.assertIn("layout_preflight_json is required", missing_preflight["errors"][0])

    def test_preflight_candidate_clearance_builds_live_bounds_check(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "room": {"type": "kitchen", "dimensions_cm": [420, 320, 280], "origin": [0, 0, 0]},
            "props": [
                {
                    "id": "refrigerator",
                    "name": "refrigerator",
                    "zone": "kitchen",
                    "surface": "floor",
                    "approx_size_cm": [90, 80, 190],
                    "placement": {"actor_label": "Apt_refrigerator"},
                },
            ],
            "placement_steps": [
                {
                    "id": "refrigerator",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "actor_label": "Apt_refrigerator",
                        "asset_path": "/Game/Props/SM_Fridge.SM_Fridge",
                        "location": [-120, -90, 0],
                    },
                },
            ],
        }
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {
                    "schema": spatial_awareness_tools.CANDIDATE_CLEARANCE_SCHEMA,
                    "status": "pass",
                    "candidate_count": 1,
                    "blocked_count": 0,
                    "needs_review_count": 0,
                    "candidates": [{"actor_label": "Apt_refrigerator", "status": "clear"}],
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_preflight_candidate_clearance"](
                ctx=None,
                composition_plan_json=json.dumps(composition_plan),
                actor_query="Kitchen",
                clearance_padding=18,
                ignore_actor_labels=["ExistingPreview"],
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.CANDIDATE_CLEARANCE_SCHEMA)
        self.assertEqual(payload["outputs"]["status"], "pass")
        self.assertEqual(payload["inputs"]["candidate_count"], 1)
        self.assertEqual(payload["inputs"]["clearance_padding"], 18.0)
        self.assertEqual(calls[0][1], "spatial_preflight_candidate_clearance")
        self.assertIn("axis_aligned_candidate_bounds_vs_live_actor_bounds", calls[0][0])
        self.assertIn("Apt_refrigerator", calls[0][0])
        self.assertIn("ExistingPreview", calls[0][0])
        self.assertIn("blocked_by_existing_overlap", calls[0][0])

    def test_preflight_candidate_clearance_validates_inputs_before_bridge_call(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_structured") as fake_exec:
            missing_plan = json.loads(mcp.tools["spatial_preflight_candidate_clearance"](
                ctx=None,
                composition_plan_json="",
            ))
            wrong_schema = json.loads(mcp.tools["spatial_preflight_candidate_clearance"](
                ctx=None,
                composition_plan_json=json.dumps({"schema": spatial_awareness_tools.PLACEMENT_VALIDATION_SCHEMA}),
            ))

        self.assertFalse(missing_plan["success"])
        self.assertIn("composition_plan_json is required", missing_plan["errors"][0])
        self.assertFalse(wrong_schema["success"])
        self.assertIn(spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA, wrong_schema["errors"][0])
        fake_exec.assert_not_called()

    def test_plan_composition_iteration_generates_corrections_and_evidence_handoffs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "placement_steps": [
                {
                    "id": "counter_clutter",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_Clutter.SM_Clutter",
                        "actor_label": "Apt_counter_clutter",
                        "location": [10, 20, 130],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                        "dry_run": True,
                        "allow_mutation": False,
                    },
                },
                {
                    "id": "wall_cabinets",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_WallCabinets.SM_WallCabinets",
                        "actor_label": "Apt_wall_cabinets",
                        "location": [40, 20, 150],
                        "rotation": [0, 90, 0],
                        "scale": [1, 1, 1],
                        "dry_run": True,
                        "allow_mutation": False,
                    },
                },
            ],
            "props": [
                {"id": "counter_clutter", "placement": {"actor_label": "Apt_counter_clutter"}},
                {"id": "wall_cabinets", "placement": {"actor_label": "Apt_wall_cabinets"}},
            ],
        }
        validation_result = {
            "schema": spatial_awareness_tools.PLACEMENT_VALIDATION_SCHEMA,
            "summary": {
                "on_surface": 1,
                "floating": 1,
                "intersecting_or_below_surface": 0,
                "no_surface_hit": 0,
                "potential_overlap": 1,
            },
            "validations": [
                {
                    "actor": {"label": "Apt_counter_clutter"},
                    "status": "floating",
                    "surface_gap": 35.0,
                    "surface_tolerance": 15.0,
                    "probe_location": [10, 20, 130],
                    "clearance": {"status": "clear"},
                },
                {
                    "actor": {"label": "Apt_wall_cabinets"},
                    "status": "on_surface",
                    "surface_gap": 0.0,
                    "probe_location": [40, 20, 150],
                    "clearance": {
                        "status": "potential_overlap",
                        "overlaps": [{"label": "ExistingCabinet", "center": [30, 20, 150]}],
                    },
                },
            ],
        }

        payload = json.loads(mcp.tools["spatial_plan_composition_iteration"](
            ctx=None,
            composition_plan_json=json.dumps({
                "schema": spatial_awareness_tools.SPATIAL_RESULT_SCHEMA,
                "outputs": composition_plan,
            }),
            validation_result_json=json.dumps(validation_result),
            screenshot_notes=["cabinet row still reads too tight"],
            reference_image="C:/refs/apartment.png",
        ))

        self.assertTrue(payload["success"])
        self.assertTrue(payload["inputs"]["composition_plan_applied"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.COMPOSITION_ITERATION_SCHEMA)
        self.assertEqual(outputs["status"], "needs_correction")
        self.assertEqual(outputs["correction_count"], 2)
        corrections = {step["actor_label"]: step for step in outputs["correction_steps"]}
        clutter = corrections["Apt_counter_clutter"]
        self.assertIn("lower_z_by_surface_gap_35.0cm", clutter["reasons"])
        self.assertEqual(clutter["candidate_location"], [10.0, 20.0, 95.0])
        self.assertTrue(clutter["dry_run"])
        self.assertFalse(clutter["allow_mutation"])
        self.assertTrue(clutter["dry_run_preview_handoff"]["arguments"]["dry_run"])
        self.assertFalse(clutter["dry_run_preview_handoff"]["arguments"]["allow_mutation"])
        cabinets = corrections["Apt_wall_cabinets"]
        self.assertIn("nudge_xy_for_potential_overlap_25.0cm", cabinets["reasons"])
        self.assertEqual(cabinets["candidate_location"], [65.0, 20.0, 150.0])
        self.assertEqual(cabinets["reviewed_mutation_handoff"]["tool"], "set_actor_transform")
        self.assertTrue(cabinets["reviewed_mutation_handoff"]["requires_review"])
        updated_steps = {
            step["arguments"]["actor_label"]: step
            for step in outputs["updated_composition_plan"]["placement_steps"]
        }
        self.assertEqual(updated_steps["Apt_counter_clutter"]["arguments"]["location"], [10.0, 20.0, 95.0])
        self.assertEqual(updated_steps["Apt_wall_cabinets"]["arguments"]["location"], [65.0, 20.0, 150.0])
        self.assertIn("composition_iteration_correction", updated_steps["Apt_wall_cabinets"]["arguments"]["placement_source"])
        self.assertTrue(outputs["layout_preflight_handoff"]["enabled"])
        self.assertTrue(outputs["candidate_clearance_handoff"]["enabled"])
        self.assertTrue(outputs["apply_handoff"]["enabled"])
        rerun_step = next(step for step in outputs["iteration_loop"] if step["step"] == "rerun_iteration_planner")
        self.assertIn("composition_iteration_summary", rerun_step["arguments"]["composition_plan_json"])
        self.assertIn("[65.0, 20.0, 150.0]", rerun_step["arguments"]["composition_plan_json"])
        self.assertEqual(outputs["validation_handoff"]["tool"], "spatial_validate_placement")
        evidence_tools = [step["tool"] for step in outputs["evidence_handoff"]]
        self.assertIn("viewport_capture_screenshot", evidence_tools)
        self.assertIn("viewport_compare_screenshot", evidence_tools)
        self.assertEqual(outputs["surface_probe_handoff"]["tool"], "spatial_surface_probe")
        self.assertIn("cabinet row still reads too tight", outputs["review_notes"])

    def test_plan_composition_iteration_accepts_candidate_clearance_blockers(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        composition_plan = {
            "schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA,
            "placement_steps": [
                {
                    "id": "sofa",
                    "tool": "spatial_add_asset_to_scene",
                    "arguments": {
                        "asset_path": "/Game/Props/SM_Sofa.SM_Sofa",
                        "actor_label": "Apt_sofa",
                        "location": [0, 0, 0],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                        "dry_run": True,
                        "allow_mutation": False,
                    },
                },
            ],
            "props": [
                {"id": "sofa", "placement": {"actor_label": "Apt_sofa"}},
            ],
        }
        candidate_clearance = {
            "schema": spatial_awareness_tools.CANDIDATE_CLEARANCE_SCHEMA,
            "status": "blocked_by_clearance",
            "candidate_count": 1,
            "blocked_count": 1,
            "needs_review_count": 0,
            "candidates": [
                {
                    "id": "sofa",
                    "actor_label": "Apt_sofa",
                    "status": "blocked_by_existing_overlap",
                    "location": [0, 0, 0],
                    "existing_overlap_count": 1,
                    "existing_overlaps": [
                        {
                            "label": "Existing_Table",
                            "bounds": {"center": [0, -40, 0]},
                            "overlap_cm": [80, 50, 40],
                        }
                    ],
                }
            ],
        }

        payload = json.loads(mcp.tools["spatial_plan_composition_iteration"](
            ctx=None,
            composition_plan_json=json.dumps(composition_plan),
            validation_result_json=json.dumps(candidate_clearance),
            nudge_distance=25,
        ))

        self.assertTrue(payload["success"])
        outputs = payload["outputs"]
        self.assertEqual(outputs["schema"], spatial_awareness_tools.COMPOSITION_ITERATION_SCHEMA)
        self.assertEqual(outputs["source_validation_schema"], spatial_awareness_tools.CANDIDATE_CLEARANCE_SCHEMA)
        self.assertEqual(outputs["candidate_clearance_summary"]["status"], "blocked_by_clearance")
        self.assertEqual(outputs["candidate_clearance_summary"]["blocked_count"], 1)
        self.assertEqual(outputs["status"], "needs_correction")
        self.assertEqual(outputs["correction_count"], 1)
        correction = outputs["correction_steps"][0]
        self.assertEqual(correction["actor_label"], "Apt_sofa")
        self.assertEqual(correction["source_status"], "candidate_blocked_by_existing_overlap")
        self.assertIn("review_validation_status_candidate_blocked_by_existing_overlap", correction["reasons"])
        self.assertIn("nudge_xy_for_potential_overlap_25.0cm", correction["reasons"])
        self.assertEqual(correction["candidate_location"], [0.0, 25.0, 0.0])
        self.assertTrue(correction["dry_run_preview_handoff"]["arguments"]["dry_run"])
        self.assertFalse(correction["dry_run_preview_handoff"]["arguments"]["allow_mutation"])
        updated_step = outputs["updated_composition_plan"]["placement_steps"][0]
        self.assertEqual(updated_step["arguments"]["location"], [0.0, 25.0, 0.0])
        self.assertTrue(updated_step["arguments"]["dry_run"])
        self.assertFalse(updated_step["arguments"]["allow_mutation"])
        self.assertIn("composition_iteration_correction", updated_step["arguments"]["placement_source"])
        self.assertEqual(
            outputs["updated_composition_plan"]["props"][0]["placement"]["location"],
            [0.0, 25.0, 0.0],
        )
        self.assertTrue(outputs["layout_preflight_handoff"]["enabled"])
        self.assertTrue(outputs["candidate_clearance_handoff"]["enabled"])
        self.assertTrue(outputs["apply_handoff"]["enabled"])
        self.assertIn("composition_iteration_summary", outputs["apply_handoff"]["arguments"]["composition_plan_json"])
        rerun_step = next(step for step in outputs["iteration_loop"] if step["step"] == "rerun_iteration_planner")
        self.assertIn("composition_iteration_summary", rerun_step["arguments"]["composition_plan_json"])
        self.assertIn("[0.0, 25.0, 0.0]", rerun_step["arguments"]["composition_plan_json"])
        self.assertEqual(outputs["validation_handoff"]["arguments"]["actors"], ["Apt_sofa"])

    def test_plan_composition_iteration_validates_inputs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        missing_validation = json.loads(mcp.tools["spatial_plan_composition_iteration"](
            ctx=None,
            validation_result_json="",
        ))
        invalid_json = json.loads(mcp.tools["spatial_plan_composition_iteration"](
            ctx=None,
            validation_result_json="{not-json",
        ))
        wrong_schema = json.loads(mcp.tools["spatial_plan_composition_iteration"](
            ctx=None,
            validation_result_json=json.dumps({"schema": spatial_awareness_tools.INTERIOR_COMPOSITION_SCHEMA}),
        ))

        self.assertFalse(missing_validation["success"])
        self.assertIn("validation_result_json is required", missing_validation["errors"][0])
        self.assertFalse(invalid_json["success"])
        self.assertIn("validation_result_json must be a JSON object", invalid_json["errors"][0])
        self.assertFalse(wrong_schema["success"])
        self.assertIn(spatial_awareness_tools.PLACEMENT_VALIDATION_SCHEMA, wrong_schema["errors"][0])
        self.assertIn(spatial_awareness_tools.CANDIDATE_CLEARANCE_SCHEMA, wrong_schema["errors"][0])

    def test_content_selection_context_builds_placement_handoffs(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {
                    "schema": spatial_awareness_tools.CONTENT_SELECTION_SCHEMA,
                    "selected_asset_count": 1,
                    "placement_plan": [
                        {
                            "tool": "spatial_add_asset_to_scene",
                            "arguments": {
                                "asset_path": "/Game/Props/SM_Table.SM_Table",
                                "tags": ["Gameplay_POI"],
                                "data_layer_names": ["Gameplay_POIs"],
                                "dry_run": True,
                            },
                        }
                    ],
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_content_selection_context"](
                ctx=None,
                placement_layout="grid",
                placement_origin=[100, 200, 300],
                actor_label_prefix="POI",
                tags=["Gameplay_POI"],
                data_layer_names=["Gameplay_POIs"],
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.CONTENT_SELECTION_SCHEMA)
        self.assertEqual(payload["outputs"]["placement_plan"][0]["tool"], "spatial_add_asset_to_scene")
        self.assertEqual(calls[0][1], "spatial_content_selection_context")
        self.assertIn("EditorUtilityLibrary", calls[0][0])
        self.assertIn("get_selected_assets", calls[0][0])
        self.assertIn("get_selected_asset_data", calls[0][0])
        self.assertIn("spatial_add_asset_to_scene", calls[0][0])
        self.assertIn("viewport_capture_screenshot", calls[0][0])

    def test_content_selection_context_validates_inputs_before_unreal_execution(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_structured") as fake_exec:
            invalid_layout = json.loads(mcp.tools["spatial_content_selection_context"](
                ctx=None,
                placement_layout="spiral",
            ))
            invalid_origin = json.loads(mcp.tools["spatial_content_selection_context"](
                ctx=None,
                placement_origin=[1, 2],
            ))

        self.assertFalse(invalid_layout["success"])
        self.assertIn("placement_layout must be one of", invalid_layout["errors"][0])
        self.assertFalse(invalid_origin["success"])
        self.assertIn("placement_origin must contain exactly three numbers", invalid_origin["errors"][0])
        fake_exec.assert_not_called()

    def test_place_selected_assets_dry_run_uses_structured_resolution(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {
                    "schema": spatial_awareness_tools.SELECTED_ASSET_PLACEMENT_SCHEMA,
                    "dry_run": True,
                    "asset_count": 1,
                    "placement_plan": [{"asset": {"path": "/Game/Props/SM_Table.SM_Table"}}],
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with (
            patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec) as structured_exec,
            patch.object(spatial_awareness_tools, "_exec_transactional") as transactional_exec,
        ):
            payload = json.loads(mcp.tools["spatial_place_selected_assets"](
                ctx=None,
                asset_paths=["/Game/Props/SM_Table.SM_Table"],
                placement_layout="grid",
                tags=["Gameplay_POI"],
                data_layer_names=["Gameplay_POIs"],
                dry_run=True,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.SELECTED_ASSET_PLACEMENT_SCHEMA)
        self.assertEqual(calls[0][1], "spatial_place_selected_assets")
        self.assertIn("explicit_asset_paths", calls[0][0])
        self.assertIn("EditorUtilityLibrary", calls[0][0])
        self.assertIn("execute_batch = False", calls[0][0])
        structured_exec.assert_called_once()
        transactional_exec.assert_not_called()

    def test_place_selected_assets_requires_mutation_gate(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with (
            patch.object(spatial_awareness_tools, "_exec_structured") as structured_exec,
            patch.object(spatial_awareness_tools, "_exec_transactional") as transactional_exec,
        ):
            payload = json.loads(mcp.tools["spatial_place_selected_assets"](
                ctx=None,
                asset_paths=["/Game/Props/SM_Table.SM_Table"],
                dry_run=False,
            ))

        self.assertFalse(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.SELECTED_ASSET_PLACEMENT_SCHEMA)
        self.assertFalse(payload["outputs"]["will_execute"])
        self.assertIn("allow_mutation=True", " ".join(payload["errors"]))
        structured_exec.assert_not_called()
        transactional_exec.assert_not_called()

    def test_place_selected_assets_executes_transactional_batch_after_gate(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, transaction_name: str) -> dict[str, Any]:
            calls.append((code, transaction_name))
            return {
                "success": True,
                "stage": "transaction_complete",
                "message": "Transaction committed",
                "outputs": {
                    "schema": spatial_awareness_tools.SELECTED_ASSET_PLACEMENT_SCHEMA,
                    "placed_count": 1,
                    "placed_actors": [{"label": "POI_SM_Table"}],
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with (
            patch.object(spatial_awareness_tools, "_exec_structured") as structured_exec,
            patch.object(spatial_awareness_tools, "_exec_transactional", side_effect=fake_exec),
        ):
            payload = json.loads(mcp.tools["spatial_place_selected_assets"](
                ctx=None,
                asset_paths=["/Game/Props/SM_Table.SM_Table"],
                actor_label_prefix="POI",
                dry_run=False,
                allow_mutation=True,
                select_actors=True,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.SELECTED_ASSET_PLACEMENT_SCHEMA)
        self.assertEqual(calls[0][1], "MCP Spatial Place Selected Assets")
        self.assertIn("spawn_actor_from_object", calls[0][0])
        self.assertIn("DataLayerEditorSubsystem", calls[0][0])
        self.assertIn("set_selected_level_actors", calls[0][0])
        self.assertIn("execute_batch = True", calls[0][0])
        structured_exec.assert_not_called()

    def test_place_selected_assets_validates_inputs_before_unreal_execution(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with (
            patch.object(spatial_awareness_tools, "_exec_structured") as structured_exec,
            patch.object(spatial_awareness_tools, "_exec_transactional") as transactional_exec,
        ):
            invalid_path = json.loads(mcp.tools["spatial_place_selected_assets"](
                ctx=None,
                asset_paths=["SM_Table"],
            ))
            invalid_layout = json.loads(mcp.tools["spatial_place_selected_assets"](
                ctx=None,
                placement_layout="spiral",
            ))
            invalid_scale = json.loads(mcp.tools["spatial_place_selected_assets"](
                ctx=None,
                scale=[1, 2],
            ))

        self.assertFalse(invalid_path["success"])
        self.assertIn("Content Browser path", invalid_path["errors"][0])
        self.assertFalse(invalid_layout["success"])
        self.assertIn("placement_layout must be one of", invalid_layout["errors"][0])
        self.assertFalse(invalid_scale["success"])
        self.assertIn("scale must contain exactly three numbers", invalid_scale["errors"][0])
        structured_exec.assert_not_called()
        transactional_exec.assert_not_called()

    def test_select_actors_dry_run_resolves_without_mutation(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, stage: str) -> dict[str, Any]:
            calls.append((code, stage))
            return {
                "success": True,
                "stage": stage,
                "message": "Operation completed",
                "outputs": {
                    "schema": spatial_awareness_tools.ACTOR_SELECTION_SCHEMA,
                    "dry_run": True,
                    "matched_actor_count": 1,
                    "recommended_follow_up": [{"tool": "viewport_capture_screenshot"}],
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with (
            patch.object(spatial_awareness_tools, "_exec_structured", side_effect=fake_exec) as structured_exec,
            patch.object(spatial_awareness_tools, "_exec_transactional") as transactional_exec,
        ):
            payload = json.loads(mcp.tools["spatial_select_actors"](
                ctx=None,
                query="Market",
                tag_filter="Gameplay_POI",
                center=[0, 0, 0],
                radius=5000,
                dry_run=True,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.ACTOR_SELECTION_SCHEMA)
        self.assertTrue(payload["outputs"]["dry_run"])
        self.assertEqual(calls[0][1], "spatial_select_actors")
        self.assertIn("set_selected_level_actors", calls[0][0])
        self.assertIn("viewport_capture_screenshot", calls[0][0])
        structured_exec.assert_called_once()
        transactional_exec.assert_not_called()

    def test_select_actors_requires_mutation_gate(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with (
            patch.object(spatial_awareness_tools, "_exec_structured") as structured_exec,
            patch.object(spatial_awareness_tools, "_exec_transactional") as transactional_exec,
        ):
            payload = json.loads(mcp.tools["spatial_select_actors"](
                ctx=None,
                actors=["BP_PlayerStart"],
                dry_run=False,
            ))

        self.assertFalse(payload["success"])
        self.assertIn("allow_mutation=True", " ".join(payload["errors"]))
        self.assertFalse(payload["outputs"]["will_execute"])
        structured_exec.assert_not_called()
        transactional_exec.assert_not_called()

    def test_select_actors_executes_transactional_selection_after_gate(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, transaction_name: str) -> dict[str, Any]:
            calls.append((code, transaction_name))
            return {
                "success": True,
                "stage": "transaction_complete",
                "message": "Transaction committed",
                "outputs": {
                    "schema": spatial_awareness_tools.ACTOR_SELECTION_SCHEMA,
                    "selection_applied": True,
                    "selection_method": "EditorActorSubsystem.set_selected_level_actors",
                },
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with (
            patch.object(spatial_awareness_tools, "_exec_structured") as structured_exec,
            patch.object(spatial_awareness_tools, "_exec_transactional", side_effect=fake_exec),
        ):
            payload = json.loads(mcp.tools["spatial_select_actors"](
                ctx=None,
                actors=["BP_PlayerStart"],
                selection_mode="add",
                focus_viewport=True,
                dry_run=False,
                allow_mutation=True,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.ACTOR_SELECTION_SCHEMA)
        self.assertEqual(calls[0][1], "MCP Spatial Select Actors")
        self.assertIn("set_selected_level_actors", calls[0][0])
        self.assertIn("set_level_viewport_camera_info", calls[0][0])
        structured_exec.assert_not_called()

    def test_select_actors_validates_inputs_before_unreal_execution(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with (
            patch.object(spatial_awareness_tools, "_exec_structured") as structured_exec,
            patch.object(spatial_awareness_tools, "_exec_transactional") as transactional_exec,
        ):
            invalid_mode = json.loads(mcp.tools["spatial_select_actors"](
                ctx=None,
                query="Market",
                selection_mode="toggle",
            ))
            invalid_center = json.loads(mcp.tools["spatial_select_actors"](
                ctx=None,
                query="Market",
                center=[1, 2],
            ))

        self.assertFalse(invalid_mode["success"])
        self.assertIn("selection_mode must be one of", invalid_mode["errors"][0])
        self.assertFalse(invalid_center["success"])
        self.assertIn("center must contain exactly three numbers", invalid_center["errors"][0])
        structured_exec.assert_not_called()
        transactional_exec.assert_not_called()

    def test_add_asset_to_scene_dry_run_does_not_execute(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_transactional") as fake_exec:
            payload = json.loads(mcp.tools["spatial_add_asset_to_scene"](
                ctx=None,
                asset_path="/Game/Props/SM_Table.SM_Table",
                actor_label="Table_A",
                location=[1, 2, 3],
                tags=["Gameplay_POI", "Gameplay_POI"],
                data_layer_names=["Gameplay_POIs"],
                fail_on_missing_data_layer=True,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.ASSET_PLACEMENT_SCHEMA)
        self.assertTrue(payload["outputs"]["dry_run"])
        self.assertFalse(payload["outputs"]["will_execute"])
        self.assertEqual(payload["outputs"]["tags"], ["Gameplay_POI"])
        self.assertEqual(payload["outputs"]["data_layer_names"], ["Gameplay_POIs"])
        self.assertTrue(payload["outputs"]["fail_on_missing_data_layer"])
        self.assertTrue(payload["outputs"]["world_partition"]["data_layer_assignment_requested"])
        fake_exec.assert_not_called()

    def test_add_asset_to_scene_requires_mutation_gate(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_transactional") as fake_exec:
            payload = json.loads(mcp.tools["spatial_add_asset_to_scene"](
                ctx=None,
                asset_path="/Game/Props/SM_Table.SM_Table",
                dry_run=False,
        ))

        self.assertFalse(payload["success"])
        self.assertIn("allow_mutation=True", " ".join(payload["errors"]))
        self.assertFalse(payload["outputs"]["will_execute"])
        fake_exec.assert_not_called()

    def test_add_asset_to_scene_executes_transactional_script_after_gate(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        calls: list[tuple[str, str]] = []

        def fake_exec(code: str, transaction_name: str) -> dict[str, Any]:
            calls.append((code, transaction_name))
            return {
                "success": True,
                "stage": "transaction_complete",
                "message": "Transaction committed",
                "outputs": {"placed": True, "actor": {"label": "Table_A"}},
                "warnings": [],
                "errors": [],
                "log_tail": [],
            }

        with patch.object(spatial_awareness_tools, "_exec_transactional", side_effect=fake_exec):
            payload = json.loads(mcp.tools["spatial_add_asset_to_scene"](
                ctx=None,
                asset_path="/Game/Props/SM_Table.SM_Table",
                actor_label="Table_A",
                location=[10, 20, 30],
                rotation=[0, 90, 0],
                scale=[2, 2, 2],
                tags=["Gameplay_POI"],
                data_layer_names=["Gameplay_POIs"],
                dry_run=False,
                allow_mutation=True,
            ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["schema"], spatial_awareness_tools.ASSET_PLACEMENT_SCHEMA)
        self.assertEqual(calls[0][1], "MCP Spatial Add Asset To Scene")
        self.assertIn("EditorAssetLibrary.load_asset", calls[0][0])
        self.assertIn("spawn_actor_from_object", calls[0][0])
        self.assertIn("set_actor_label", calls[0][0])
        self.assertIn("set_editor_property(\"tags\"", calls[0][0])
        self.assertIn("DataLayerEditorSubsystem", calls[0][0])
        self.assertIn("add_actor_to_data_layer", calls[0][0])

    def test_add_asset_to_scene_validates_content_path_and_vectors(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)

        with patch.object(spatial_awareness_tools, "_exec_transactional") as fake_exec:
            invalid_path = json.loads(mcp.tools["spatial_add_asset_to_scene"](
                ctx=None,
                asset_path="SM_Table",
            ))
            invalid_vector = json.loads(mcp.tools["spatial_add_asset_to_scene"](
                ctx=None,
                asset_path="/Game/Props/SM_Table.SM_Table",
                scale=[1, 2],
            ))
            invalid_tag = json.loads(mcp.tools["spatial_add_asset_to_scene"](
                ctx=None,
                asset_path="/Game/Props/SM_Table.SM_Table",
                tags=["x" * 129],
            ))

        self.assertFalse(invalid_path["success"])
        self.assertIn("Content Browser path", invalid_path["errors"][0])
        self.assertFalse(invalid_vector["success"])
        self.assertIn("scale must contain exactly three numbers", invalid_vector["errors"][0])
        self.assertFalse(invalid_tag["success"])
        self.assertIn("tags entries must be 128 characters or fewer", invalid_tag["errors"][0])
        fake_exec.assert_not_called()

    def test_generated_unreal_python_snippets_parse(self) -> None:
        snippets = [
            spatial_awareness_tools._scene_overview_code(
                include_hidden=False,
                class_filter="",
                tag_filter="",
                limit=10,
                include_actor_samples=True,
            ),
            spatial_awareness_tools._room_analysis_code(
                room_type="apartment",
                actor_query="Apartment",
                class_filter="StaticMeshActor",
                tag_filter="Interior",
                include_hidden=False,
                prefer_selected=True,
                clearance_padding=90.0,
                min_walkway_width=90.0,
                limit=50,
            ),
            spatial_awareness_tools._query_actors_code(
                query="door",
                class_filter="StaticMeshActor",
                tag_filter="Gameplay",
                center=[0, 0, 0],
                radius=1000,
                box_min=None,
                box_max=None,
                include_hidden=False,
                include_components=True,
                limit=25,
            ),
            spatial_awareness_tools._describe_actor_code(
                actor="BP_PlayerStart",
                include_components=True,
                include_bounds=True,
                nearby_radius=1000,
                nearby_limit=25,
            ),
            spatial_awareness_tools._proximity_map_code(
                actor="BP_PlayerStart",
                center=None,
                radius=1000,
                class_filter="",
                tag_filter="",
                include_hidden=False,
                limit=25,
            ),
            spatial_awareness_tools._view_context_code(include_nearby=True, nearby_radius=3000, limit=40),
            spatial_awareness_tools._surface_probe_code(
                points=[[0.0, 0.0, 100.0]],
                center=[0.0, 0.0, 0.0],
                grid_count=1,
                grid_spacing=300.0,
                trace_up=5000.0,
                trace_down=10000.0,
                trace_channel="visibility",
                ignore_actor_query="Preview",
                placement_offset=25.0,
                include_handoff=True,
            ),
            spatial_awareness_tools._placement_validation_code(
                actors=["POI_Table"],
                query="",
                class_filter="",
                tag_filter="Gameplay_POI",
                center=[0.0, 0.0, 0.0],
                radius=3000.0,
                include_hidden=False,
                limit=25,
                trace_up=500.0,
                trace_down=5000.0,
                trace_channel="visibility",
                surface_tolerance=10.0,
                clearance_padding=25.0,
                ignore_self=True,
                include_evidence_handoff=True,
            ),
            spatial_awareness_tools._content_selection_code(
                limit=10,
                placement_origin=[0.0, 0.0, 0.0],
                placement_spacing=300.0,
                placement_layout="grid",
                actor_label_prefix="POI",
                tags=["Gameplay_POI"],
                data_layer_names=["Gameplay_POIs"],
            ),
            spatial_awareness_tools._selected_asset_placement_code(
                asset_paths=["/Game/Props/SM_Table.SM_Table"],
                limit=10,
                placement_origin=[0.0, 0.0, 0.0],
                placement_spacing=300.0,
                placement_layout="grid",
                actor_label_prefix="POI",
                rotation=[0.0, 0.0, 0.0],
                scale=[1.0, 1.0, 1.0],
                tags=["Gameplay_POI"],
                data_layer_names=["Gameplay_POIs"],
                fail_on_missing_data_layer=False,
                execute=False,
                select_actors=True,
                focus_viewport=False,
            ),
            spatial_awareness_tools._actor_selection_code(
                actors=["BP_PlayerStart"],
                query="",
                class_filter="",
                tag_filter="",
                center=None,
                radius=0,
                box_min=None,
                box_max=None,
                include_hidden=False,
                limit=25,
                apply_selection=True,
                selection_mode="replace",
                allow_empty_selection=False,
                focus_viewport=True,
                focus_distance=1200,
            ),
            spatial_awareness_tools._asset_placement_code(
                asset_path="/Game/Props/SM_Table.SM_Table",
                actor_label="Table_A",
                location=[0.0, 0.0, 0.0],
                rotation=[0.0, 0.0, 0.0],
                scale=[1.0, 1.0, 1.0],
                tags=["Gameplay_POI"],
                data_layer_names=["Gameplay_POIs"],
                fail_on_missing_data_layer=False,
                select_actor=True,
                focus_viewport=False,
            ),
        ]

        for snippet in snippets:
            ast.parse(snippet)

    def test_environment_coherence_passes_revision_bound_supported_scene(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        scene = {
            "scene_revision": "rev-001",
            "coordinate_frame": {"units": "centimeter", "handedness": "left", "up_axis": "+Z"},
            "entities": [
                {"stable_id": "floor", "semantic_role": "support", "evidence_status": "observed", "confidence": 1.0, "zone_id": "courtyard", "material_family": "sandstone", "size_m": [20, 20, 0.2]},
                {"stable_id": "landmark", "semantic_role": "landmark", "evidence_status": "observed", "confidence": 0.95, "zone_id": "courtyard", "material_family": "sandstone", "gravity_bound": True, "support_id": "floor", "size_m": [8, 8, 12]},
            ],
            "circulation_paths": [{"stable_id": "approach", "measured_clearance_m": 3.0, "required_clearance_m": 1.5, "blocked_by_ids": []}],
            "sightlines": [{"target_id": "landmark", "visible": True, "occluder_ids": []}],
            "ecological_constraints": [{"rule_id": "grass-respects-path", "status": "pass", "violation_ids": []}],
        }
        intent = {
            "primary_landmark_ids": ["landmark"],
            "functional_zones": [{"id": "courtyard", "required_roles": ["support", "landmark"], "minimum_entity_count": 2}],
            "allowed_material_families": ["sandstone"],
            "scale_references": [{"entity_id": "landmark", "minimum_height_m": 10, "maximum_height_m": 14}],
        }

        payload = json.loads(mcp.tools["spatial_assess_environment_coherence"](
            ctx=None,
            scene_context_json=json.dumps(scene),
            design_intent_json=json.dumps(intent),
        ))

        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["readiness"], "ready")
        self.assertEqual(payload["outputs"]["advisory_coherence_score"], 100.0)
        self.assertEqual(payload["outputs"]["hard_failures"], [])
        self.assertIn("grants no mutation authority", payload["outputs"]["epistemic_policy"])

    def test_environment_coherence_blocks_unsupported_and_obstructed_entities(self) -> None:
        mcp = FakeMCP()
        spatial_awareness_tools.register_spatial_awareness_tools(mcp)
        scene = {
            "scene_revision": "rev-002",
            "coordinate_frame": {"units": "centimeter", "handedness": "left", "up_axis": "+Z"},
            "entities": [{"stable_id": "floating_tree", "semantic_role": "vegetation", "evidence_status": "observed", "gravity_bound": True, "material_family": "organic"}],
            "circulation_paths": [{"stable_id": "main-path", "measured_clearance_m": 0.4, "required_clearance_m": 1.5, "blocked_by_ids": ["floating_tree"]}],
        }
        intent = {
            "functional_zones": [{"id": "grassland", "required_roles": ["vegetation"]}],
            "allowed_material_families": ["organic"],
        }

        payload = json.loads(mcp.tools["spatial_assess_environment_coherence"](
            ctx=None,
            scene_context_json=json.dumps(scene),
            design_intent_json=json.dumps(intent),
        ))

        self.assertEqual(payload["outputs"]["readiness"], "blocked")
        self.assertIn("support_and_contact", payload["outputs"]["hard_failures"])
        self.assertIn("circulation_and_clearance", payload["outputs"]["hard_failures"])
        self.assertLess(payload["outputs"]["advisory_coherence_score"], 100.0)


if __name__ == "__main__":
    unittest.main()
