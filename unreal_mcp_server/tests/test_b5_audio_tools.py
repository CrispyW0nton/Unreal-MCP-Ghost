"""Offline smoke coverage for Workstream B.5 MetaSound and audio tools."""

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


class TestB5AudioTools(unittest.TestCase):
    def setUp(self):
        from tools.audio_tools import register_audio_tools

        self.mcp = _MockMCP()
        register_audio_tools(self.mcp)

    def test_b5_audio_tools_register(self):
        expected = {
            "metasound_create_source",
            "metasound_create_patch",
            "metasound_add_node",
            "metasound_connect_pins",
            "metasound_compile",
            "audio_create_soundcue",
            "audio_create_attenuation",
            "audio_create_concurrency",
        }
        self.assertTrue(expected.issubset(self.mcp.tools))

    def test_audio_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {"success": True, "route": command, "asset_path": params.get("path", "/Game/Audio") + "/" + params.get("name", "Asset")}

        async def run():
            with patch("tools.audio_tools._send", side_effect=fake_send):
                source = json.loads(await self.mcp.tools["metasound_create_source"](
                    ctx=None,
                    name="MS_GeneratorHum",
                    one_shot=False,
                ))
                patch_payload = json.loads(await self.mcp.tools["metasound_create_patch"](
                    ctx=None,
                    name="MSP_DamageCrackle",
                ))
                node = json.loads(await self.mcp.tools["metasound_add_node"](
                    ctx=None,
                    metasound="/Game/Audio/MetaSounds/MS_GeneratorHum",
                    class_name="Sine",
                    class_namespace="UE",
                    node_position=[200, 80],
                ))
                connect = json.loads(await self.mcp.tools["metasound_connect_pins"](
                    ctx=None,
                    metasound="/Game/Audio/MetaSounds/MS_GeneratorHum",
                    from_node_id="11111111-1111-1111-1111-111111111111",
                    from_output_id="22222222-2222-2222-2222-222222222222",
                    to_node_id="33333333-3333-3333-3333-333333333333",
                    to_input_id="44444444-4444-4444-4444-444444444444",
                ))
                compile_result = json.loads(await self.mcp.tools["metasound_compile"](
                    ctx=None,
                    metasound="/Game/Audio/MetaSounds/MS_GeneratorHum",
                ))
                cue = json.loads(await self.mcp.tools["audio_create_soundcue"](
                    ctx=None,
                    name="SC_Footstep_Dirt",
                    sound_wave="/Game/Audio/SFX/SW_Footstep_Dirt",
                ))
                attenuation = json.loads(await self.mcp.tools["audio_create_attenuation"](
                    ctx=None,
                    name="SA_RoomTone",
                    radius=500.0,
                    falloff_distance=2500.0,
                ))
                concurrency = json.loads(await self.mcp.tools["audio_create_concurrency"](
                    ctx=None,
                    name="SCN_Impacts",
                    max_count=6,
                    resolution_rule="stop_quietest",
                ))
            return source, patch_payload, node, connect, compile_result, cue, attenuation, concurrency

        payloads = asyncio.run(run())
        stages = [
            "metasound_create_source",
            "metasound_create_patch",
            "metasound_add_node",
            "metasound_connect_pins",
            "metasound_compile",
            "audio_create_soundcue",
            "audio_create_attenuation",
            "audio_create_concurrency",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertFalse(calls[0][1]["one_shot"])
        self.assertEqual(calls[2][1]["class_namespace"], "UE")
        self.assertEqual(calls[2][1]["node_position"], [200, 80])
        self.assertEqual(calls[3][1]["to_input_id"], "44444444-4444-4444-4444-444444444444")
        self.assertEqual(calls[5][1]["sound_wave"], "/Game/Audio/SFX/SW_Footstep_Dirt")
        self.assertEqual(calls[6][1]["radius"], 500.0)
        self.assertEqual(calls[7][1]["max_count"], 6)
        self.assertEqual(calls[7][1]["resolution_rule"], "stop_quietest")


if __name__ == "__main__":
    unittest.main()
