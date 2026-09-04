"""Offline smoke coverage for Workstream B.7 Mass/StateTree/SmartObject tools."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))


class _MockMCP:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _assert_structured(testcase: unittest.TestCase, payload: dict, stage: str):
    for key in ("success", "stage", "message", "inputs", "outputs", "warnings", "errors", "log_tail", "meta"):
        testcase.assertIn(key, payload)
    testcase.assertEqual(payload["stage"], stage)
    testcase.assertEqual(payload["meta"]["tool"], stage)


class TestB7MassTools(unittest.TestCase):
    def setUp(self):
        from tools.mass_tools import register_mass_tools

        self.mcp = _MockMCP()
        register_mass_tools(self.mcp)

    def test_b7_mass_tools_register(self):
        expected = {
            "mass_create_entity_config",
            "mass_add_trait",
            "mass_inspect_entity_config",
            "statetree_create",
            "statetree_add_state",
            "statetree_inspect",
            "smartobject_create_definition",
            "smartobject_add_slot",
            "smartobject_inspect_definition",
        }
        self.assertEqual(expected, set(self.mcp.tools))

    def test_mass_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "route": command,
                "asset_path": params.get("config_asset") or params.get("state_tree") or params.get("definition") or "/Game/Test/Asset",
                "trait_count": 2,
                "slot_count": 1,
                "state_count": 3,
            }

        async def run():
            with patch("tools.mass_tools._send", side_effect=fake_send):
                mass_create = json.loads(await self.mcp.tools["mass_create_entity_config"](
                    ctx=None,
                    name="EC_CrowdAgent",
                    traits=["MassAssortedFragmentsTrait"],
                    overwrite=True,
                ))
                mass_trait = json.loads(await self.mcp.tools["mass_add_trait"](
                    ctx=None,
                    config_asset="/Game/Mass/EntityConfigs/EC_CrowdAgent",
                    trait_class="MassLODTrait",
                ))
                mass_inspect = json.loads(await self.mcp.tools["mass_inspect_entity_config"](
                    ctx=None,
                    config_asset="/Game/Mass/EntityConfigs/EC_CrowdAgent",
                    validate=True,
                ))
                st_create = json.loads(await self.mcp.tools["statetree_create"](
                    ctx=None,
                    name="ST_CombatBrain",
                    schema_class="StateTreeComponentSchema",
                    overwrite=True,
                ))
                st_add = json.loads(await self.mcp.tools["statetree_add_state"](
                    ctx=None,
                    state_tree="/Game/AI/StateTrees/ST_CombatBrain",
                    name="Patrol",
                    parent_state="Root",
                    description="Patrol loop",
                ))
                st_inspect = json.loads(await self.mcp.tools["statetree_inspect"](
                    ctx=None,
                    state_tree="/Game/AI/StateTrees/ST_CombatBrain",
                ))
                so_create = json.loads(await self.mcp.tools["smartobject_create_definition"](
                    ctx=None,
                    name="SO_CoverPoint",
                    slot_name="UseCover",
                    overwrite=True,
                ))
                so_add = json.loads(await self.mcp.tools["smartobject_add_slot"](
                    ctx=None,
                    definition="/Game/AI/SmartObjects/SO_CoverPoint",
                    slot_name="LeftPeek",
                    offset=[0, -60, 0],
                    activity_tags=["AI.Cover"],
                ))
                so_inspect = json.loads(await self.mcp.tools["smartobject_inspect_definition"](
                    ctx=None,
                    definition="/Game/AI/SmartObjects/SO_CoverPoint",
                ))
            return mass_create, mass_trait, mass_inspect, st_create, st_add, st_inspect, so_create, so_add, so_inspect

        payloads = asyncio.run(run())
        stages = [
            "mass_create_entity_config",
            "mass_add_trait",
            "mass_inspect_entity_config",
            "statetree_create",
            "statetree_add_state",
            "statetree_inspect",
            "smartobject_create_definition",
            "smartobject_add_slot",
            "smartobject_inspect_definition",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertEqual(calls[0][1]["traits"], ["MassAssortedFragmentsTrait"])
        self.assertTrue(calls[0][1]["overwrite"])
        self.assertEqual(calls[1][1]["trait_class"], "MassLODTrait")
        self.assertTrue(calls[2][1]["validate"])
        self.assertEqual(calls[3][1]["schema_class"], "StateTreeComponentSchema")
        self.assertEqual(calls[4][1]["parent_state"], "Root")
        self.assertEqual(calls[7][1]["offset"], [0, -60, 0])
        self.assertEqual(calls[7][1]["activity_tags"], ["AI.Cover"])


if __name__ == "__main__":
    unittest.main()
