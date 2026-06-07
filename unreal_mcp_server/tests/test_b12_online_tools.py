"""Offline smoke coverage for Workstream B.12 Online Subsystem and EOS tools."""

from __future__ import annotations

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


class TestB12OnlineTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.online_tools import register_online_tools

        self.mcp = _MockMCP()
        register_online_tools(self.mcp)

    def test_b12_online_tools_register(self):
        expected = {
            "online_inspect_config",
            "online_configure_default_subsystem",
            "online_create_eos_artifact_config",
            "online_configure_eos_sessions",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    async def test_online_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "route": command,
                "config_path": "C:/Project/Config/DefaultEngine.ini",
                "online_subsystem": {
                    "default_platform_service": params.get("default_service", "EOS"),
                    "native_platform_service": params.get("native_service", "EOS"),
                },
                "eos": {
                    "default_artifact_name": params.get("artifact_name", "Dev"),
                    "use_eos_sessions": params.get("use_eos_sessions", True),
                    "use_eos_lobbies": params.get("use_eos_lobbies", True),
                },
            }

        with patch("tools.online_tools._send", side_effect=fake_send):
            payloads = [
                json.loads(await self.mcp.tools["online_inspect_config"](
                    ctx=None,
                    include_plugins=True,
                )),
                json.loads(await self.mcp.tools["online_configure_default_subsystem"](
                    ctx=None,
                    default_service="EOS",
                    native_service="EOS",
                    enable_online_subsystem=True,
                )),
                json.loads(await self.mcp.tools["online_create_eos_artifact_config"](
                    ctx=None,
                    artifact_name="Dev",
                    product_id="product",
                    sandbox_id="sandbox",
                    deployment_id="deployment",
                    client_id="client",
                    client_secret="secret",
                    encryption_key="encryption",
                    store_secrets=False,
                )),
                json.loads(await self.mcp.tools["online_configure_eos_sessions"](
                    ctx=None,
                    use_eos_sessions=True,
                    use_eos_lobbies=True,
                    use_eos_presence=True,
                    use_eos_connect=True,
                    mirror_stats_to_eos=True,
                )),
            ]

        stages = [
            "online_inspect_config",
            "online_configure_default_subsystem",
            "online_create_eos_artifact_config",
            "online_configure_eos_sessions",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertTrue(calls[0][1]["include_plugins"])
        self.assertEqual(calls[1][1]["default_service"], "EOS")
        self.assertTrue(calls[1][1]["enable_online_subsystem"])
        self.assertEqual(calls[2][1]["artifact_name"], "Dev")
        self.assertEqual(calls[2][1]["product_id"], "product")
        self.assertEqual(calls[2][1]["client_secret"], "")
        self.assertEqual(calls[2][1]["encryption_key"], "")
        self.assertFalse(calls[2][1]["store_secrets"])
        self.assertIn("store_secrets=False", payloads[2]["warnings"][0])
        self.assertTrue(calls[3][1]["use_eos_connect"])
        self.assertTrue(calls[3][1]["mirror_stats_to_eos"])


if __name__ == "__main__":
    unittest.main()
