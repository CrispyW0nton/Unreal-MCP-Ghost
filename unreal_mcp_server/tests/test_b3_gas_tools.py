"""Offline smoke coverage for Workstream B.3 Gameplay Ability System tools."""

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


class TestB3GASTools(unittest.TestCase):
    def setUp(self):
        from tools.gas_tools import register_gas_tools

        self.mcp = _MockMCP()
        register_gas_tools(self.mcp)

    def test_b3_gas_tools_register(self):
        expected = {
            "gas_create_ability",
            "gas_create_gameplay_effect",
            "gas_create_gameplay_cue",
            "gas_create_attribute_set",
            "gas_grant_ability",
            "gas_apply_effect",
            "gas_add_tag",
            "gas_create_ability_task_node",
        }
        self.assertTrue(expected.issubset(self.mcp.tools))

    def test_asset_creation_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "object_path": f"{params['path']}/{params['name']}.{params['name']}"}

        async def run():
            with patch("tools.gas_tools._send", side_effect=fake_send):
                ability = json.loads(await self.mcp.tools["gas_create_ability"](
                    ctx=None,
                    name="GA_Dash",
                    path="/Game/GAS/Abilities",
                ))
                effect = json.loads(await self.mcp.tools["gas_create_gameplay_effect"](
                    ctx=None,
                    name="GE_DashCooldown",
                ))
                cue = json.loads(await self.mcp.tools["gas_create_gameplay_cue"](
                    ctx=None,
                    name="GCN_DashTrail",
                    notify_type="static",
                ))
                attrs = json.loads(await self.mcp.tools["gas_create_attribute_set"](
                    ctx=None,
                    name="AS_HeroCombat",
                ))
            return ability, effect, cue, attrs

        ability, effect, cue, attrs = asyncio.run(run())
        for payload, stage in [
            (ability, "gas_create_ability"),
            (effect, "gas_create_gameplay_effect"),
            (cue, "gas_create_gameplay_cue"),
            (attrs, "gas_create_attribute_set"),
        ]:
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], [
            "gas_create_ability",
            "gas_create_gameplay_effect",
            "gas_create_gameplay_cue",
            "gas_create_attribute_set",
        ])
        self.assertEqual(calls[2][1]["notify_type"], "static")

    def test_mutation_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "metadata_key": "MCP.GAS", "value": "ok", "asc_component_added": False}

        async def run():
            with patch("tools.gas_tools._send", side_effect=fake_send):
                grant = json.loads(await self.mcp.tools["gas_grant_ability"](
                    ctx=None,
                    target_bp="/Game/BP_Hero",
                    ability="/Game/GAS/Abilities/GA_Dash",
                    level=3,
                    input_id=1,
                ))
                effect = json.loads(await self.mcp.tools["gas_apply_effect"](
                    ctx=None,
                    target_bp="/Game/BP_Hero",
                    effect="/Game/GAS/Effects/GE_StartupStats",
                    level=2.5,
                ))
                tag = json.loads(await self.mcp.tools["gas_add_tag"](
                    ctx=None,
                    target_bp="/Game/BP_Hero",
                    tag="Ability.Movement.Dash",
                    ensure_asc=False,
                ))
            return grant, effect, tag

        grant, effect, tag = asyncio.run(run())
        _assert_structured(self, grant, "gas_grant_ability")
        _assert_structured(self, effect, "gas_apply_effect")
        _assert_structured(self, tag, "gas_add_tag")
        self.assertEqual(calls[0][0], "gas_grant_ability")
        self.assertEqual(calls[0][1]["level"], 3)
        self.assertEqual(calls[1][0], "gas_apply_effect")
        self.assertEqual(calls[1][1]["level"], 2.5)
        self.assertEqual(calls[2][0], "gas_add_tag")
        self.assertFalse(calls[2][1]["ensure_asc"])

    def test_ability_task_node_passes_position_object(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "node_id": "NODE-1", "task_function": "WaitDelay"}

        async def run():
            with patch("tools.gas_tools._send", side_effect=fake_send):
                return json.loads(await self.mcp.tools["gas_create_ability_task_node"](
                    ctx=None,
                    blueprint_name="/Game/GAS/Abilities/GA_Dash",
                    task_class="AbilityTask_WaitDelay",
                    task_function="WaitDelay",
                    position_x=100,
                    position_y=240,
                ))

        payload = asyncio.run(run())
        _assert_structured(self, payload, "gas_create_ability_task_node")
        self.assertEqual(calls[0][0], "gas_create_ability_task_node")
        self.assertEqual(calls[0][1]["node_position"], {"x": 100, "y": 240})
        self.assertEqual(calls[0][1]["task_function"], "WaitDelay")


if __name__ == "__main__":
    unittest.main()
