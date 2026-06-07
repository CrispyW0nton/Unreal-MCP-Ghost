"""Offline smoke coverage for Workstream B.13 Pixel Streaming tools."""

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


class TestB13PixelStreamingTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.pixelstream_tools import register_pixelstream_tools

        self.mcp = _MockMCP()
        register_pixelstream_tools(self.mcp)

    def test_b13_pixelstream_tools_register(self):
        expected = {
            "pixelstream_inspect_config",
            "pixelstream_configure_plugin",
            "pixelstream_configure_streamer",
            "pixelstream_create_launch_profile",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    async def test_pixelstream_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "route": command,
                "config_path": "C:/Project/Config/DefaultEngine.ini",
                "plugin_config": {
                    "pixel_streaming_enabled": params.get("enable_pixel_streaming", True),
                    "pixel_streaming_2_enabled": params.get("enable_pixel_streaming_2", False),
                    "prefer_pixel_streaming_2": params.get("prefer_pixel_streaming_2", False),
                },
                "pixel_streaming": {
                    "signalling_url": params.get("signalling_url", "ws://127.0.0.1:8888"),
                    "streamer_id": params.get("streamer_id", "DefaultStreamer"),
                    "render_offscreen": params.get("render_offscreen", True),
                },
                "launch_profile": {
                    "profile_name": params.get("profile_name", "LocalPixelStreaming"),
                    "resolution_x": params.get("resolution_x", 1280),
                    "resolution_y": params.get("resolution_y", 720),
                },
                "launch_args": [
                    f"-PixelStreamingURL={params.get('signalling_url', 'ws://127.0.0.1:8888')}",
                    f"-PixelStreamingStreamerId={params.get('streamer_id', 'DefaultStreamer')}",
                ],
            }

        with patch("tools.pixelstream_tools._send", side_effect=fake_send):
            payloads = [
                json.loads(await self.mcp.tools["pixelstream_inspect_config"](
                    ctx=None,
                    include_plugins=True,
                )),
                json.loads(await self.mcp.tools["pixelstream_configure_plugin"](
                    ctx=None,
                    enable_pixel_streaming=True,
                    enable_pixel_streaming_2=False,
                    prefer_pixel_streaming_2=False,
                )),
                json.loads(await self.mcp.tools["pixelstream_configure_streamer"](
                    ctx=None,
                    signalling_url="ws://127.0.0.1:8888",
                    streamer_id="LocalDemo",
                    web_server_port=80,
                    signalling_port=8888,
                    use_secure_websocket=False,
                    render_offscreen=True,
                    encoder_target_bitrate=12000000,
                )),
                json.loads(await self.mcp.tools["pixelstream_create_launch_profile"](
                    ctx=None,
                    profile_name="LocalPixelStreaming",
                    signalling_url="ws://127.0.0.1:8888",
                    streamer_id="LocalDemo",
                    render_offscreen=True,
                    resolution_x=1280,
                    resolution_y=720,
                )),
            ]

        stages = [
            "pixelstream_inspect_config",
            "pixelstream_configure_plugin",
            "pixelstream_configure_streamer",
            "pixelstream_create_launch_profile",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertTrue(calls[0][1]["include_plugins"])
        self.assertTrue(calls[1][1]["enable_pixel_streaming"])
        self.assertFalse(calls[1][1]["enable_pixel_streaming_2"])
        self.assertEqual(calls[2][1]["streamer_id"], "LocalDemo")
        self.assertEqual(calls[2][1]["encoder_target_bitrate"], 12000000)
        self.assertEqual(calls[3][1]["profile_name"], "LocalPixelStreaming")
        self.assertEqual(calls[3][1]["resolution_x"], 1280)
        self.assertEqual(payloads[3]["outputs"]["launch_args"][0], "-PixelStreamingURL=ws://127.0.0.1:8888")


if __name__ == "__main__":
    unittest.main()
