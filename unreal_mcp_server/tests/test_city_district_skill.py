from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from typing import Any

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from skills.city_district.skill import (  # noqa: E402
    CITY_DISTRICT_SCHEMA,
    register_city_district_skill,
    skill_generate_city_district,
)


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


def _tools_from_plan(payload: dict[str, Any]) -> set[str]:
    plan = payload["outputs"]["plan"]
    return {step["tool"] for step in plan["tool_sequence"]}


class TestCityDistrictSkill(unittest.TestCase):
    def test_plan_includes_native_unreal_workflow_steps(self) -> None:
        payload = skill_generate_city_district(
            brief="walkable sci-fi downtown district with plaza and alleys",
            mode="plan",
            district_name="Neon Core",
            size_blocks=5,
        )

        self.assertTrue(payload["success"])
        plan = payload["outputs"]["plan"]
        self.assertEqual(plan["schema"], CITY_DISTRICT_SCHEMA)
        self.assertEqual(plan["capability_level"], "native_workflow_scaffold")
        tools = _tools_from_plan(payload)
        for expected in {
            "pcg_check_support",
            "pcg_create_graph_asset",
            "pcg_create_volume",
            "wp_load_region",
            "wp_create_data_layer",
            "create_spline_placement_blueprint",
            "hlod_generate",
            "take_screenshot",
            "viewport_capture_screenshot",
        }:
            self.assertIn(expected, tools)
        self.assertGreater(len(plan["validation_gates"]), 4)
        self.assertTrue(any("PCG graph node authoring" in item for item in plan["future_native_requirements"]))

    def test_mass_traffic_option_adds_scaffold_steps_and_warning(self) -> None:
        payload = skill_generate_city_district(
            brief="dense city block with pedestrians and traffic",
            mode="plan",
            include_mass_traffic=True,
        )

        tools = _tools_from_plan(payload)
        self.assertIn("mass_create_entity_config", tools)
        self.assertIn("smartobject_create_definition", tools)
        self.assertTrue(any("ZoneGraph" in warning for warning in payload["warnings"]))
        self.assertTrue(any("Mass traffic" in item for item in payload["outputs"]["plan"]["future_native_requirements"]))

    def test_queue_mode_returns_not_executed_tool_queue(self) -> None:
        payload = skill_generate_city_district(
            brief="small coastal market district",
            mode="queue",
            use_pcg=False,
            include_hlod=False,
        )

        self.assertTrue(payload["success"])
        self.assertEqual(payload["stage"], "queue_ready")
        queue = payload["outputs"]["queue"]
        self.assertEqual(queue["status"], "not_executed")
        self.assertEqual(queue["tool_count"], len(payload["outputs"]["plan"]["tool_sequence"]))
        self.assertNotIn("pcg_check_support", _tools_from_plan(payload))

    def test_invalid_mode_and_empty_brief_fail(self) -> None:
        invalid_mode = skill_generate_city_district(brief="district", mode="execute")
        self.assertFalse(invalid_mode["success"])
        self.assertEqual(invalid_mode["stage"], "invalid_mode")

        empty_brief = skill_generate_city_district(brief="", mode="plan")
        self.assertFalse(empty_brief["success"])
        self.assertEqual(empty_brief["stage"], "invalid_brief")

    def test_registration_adds_async_mcp_tool(self) -> None:
        mcp = FakeMCP()
        register_city_district_skill(mcp)

        self.assertIn("skill_generate_city_district", mcp.tools)
        payload = json.loads(asyncio.run(mcp.tools["skill_generate_city_district"](
            ctx=None,
            brief="compact medieval city district",
            mode="plan",
        )))
        self.assertTrue(payload["success"])
        self.assertEqual(payload["outputs"]["plan"]["schema"], CITY_DISTRICT_SCHEMA)


if __name__ == "__main__":
    unittest.main()
