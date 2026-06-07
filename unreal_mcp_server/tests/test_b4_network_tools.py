"""Offline smoke coverage for Workstream B.4 networking tools."""

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


class TestB4NetworkTools(unittest.TestCase):
    def setUp(self):
        from tools.network_tools import register_network_tools

        self.mcp = _MockMCP()
        register_network_tools(self.mcp)

    def test_b4_network_tools_register(self):
        expected = {
            "net_set_property_replicated",
            "net_set_function_rpc",
            "net_set_replication_condition",
            "net_add_replicated_component",
            "net_set_role_override",
            "net_get_replication_graph_state",
        }
        self.assertTrue(expected.issubset(self.mcp.tools))

    def test_authoring_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "route": command}

        async def run():
            with patch("tools.network_tools._send", side_effect=fake_send):
                prop = json.loads(await self.mcp.tools["net_set_property_replicated"](
                    ctx=None,
                    blueprint_name="/Game/BP_Door",
                    variable_name="bIsOpen",
                    repnotify=True,
                    replication_condition="owner_only",
                ))
                rpc = json.loads(await self.mcp.tools["net_set_function_rpc"](
                    ctx=None,
                    blueprint_name="/Game/BP_Door",
                    function_name="Multicast_PlayOpenFX",
                    rpc_type="netmulticast",
                    reliable=False,
                    node_position=[400, 120],
                ))
                condition = json.loads(await self.mcp.tools["net_set_replication_condition"](
                    ctx=None,
                    blueprint_name="/Game/BP_Door",
                    variable_name="CurrentState",
                    replication_condition="skip_owner",
                ))
                component = json.loads(await self.mcp.tools["net_add_replicated_component"](
                    ctx=None,
                    blueprint_name="/Game/BP_Door",
                    component_name="ReplicatedMesh",
                    component_type="StaticMeshComponent",
                ))
                role = json.loads(await self.mcp.tools["net_set_role_override"](
                    ctx=None,
                    blueprint_name="/Game/BP_Door",
                    node_position=[640, 0],
                ))
                state = json.loads(await self.mcp.tools["net_get_replication_graph_state"](
                    ctx=None,
                    max_actors=7,
                ))
            return prop, rpc, condition, component, role, state

        prop, rpc, condition, component, role, state = asyncio.run(run())
        for payload, stage in [
            (prop, "net_set_property_replicated"),
            (rpc, "net_set_function_rpc"),
            (condition, "net_set_replication_condition"),
            (component, "net_add_replicated_component"),
            (role, "net_set_role_override"),
            (state, "net_get_replication_graph_state"),
        ]:
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], [
            "net_set_property_replicated",
            "net_set_function_rpc",
            "net_set_replication_condition",
            "net_add_replicated_component",
            "net_set_role_override",
            "net_get_replication_graph_state",
        ])
        self.assertEqual(calls[0][1]["replication_mode"], "repnotify")
        self.assertEqual(calls[0][1]["replication_condition"], "owner_only")
        self.assertEqual(calls[1][1]["rpc_type"], "net_multicast")
        self.assertEqual(calls[1][1]["event_name"], "Multicast_PlayOpenFX")
        self.assertFalse(calls[1][1]["reliable"])
        self.assertEqual(calls[2][1]["replication_condition"], "skip_owner")
        self.assertEqual(calls[3][1]["component_type"], "StaticMeshComponent")
        self.assertEqual(calls[4][1]["node_position"], [640, 0])
        self.assertEqual(calls[5][1]["max_actors"], 7)


if __name__ == "__main__":
    unittest.main()
