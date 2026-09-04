"""Offline smoke coverage for Workstream B.11 Movie Render Queue tools."""

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


class TestB11MRQTools(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        from tools.mrq_tools import register_mrq_tools

        self.mcp = _MockMCP()
        register_mrq_tools(self.mcp)

    def test_b11_mrq_tools_register(self):
        expected = {
            "mrq_create_job",
            "mrq_add_render_setting",
            "mrq_render_queue",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    async def test_mrq_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "route": command,
                "queue_job_count": 1,
                "job": {
                    "job_name": params.get("job_name", "Trailer_Master"),
                    "settings": ["MoviePipelineOutputSetting"],
                },
                "dry_run": params.get("dry_run", False),
                "executor": params.get("executor", "pie"),
            }

        with patch("tools.mrq_tools._send", side_effect=fake_send):
            payloads = [
                json.loads(await self.mcp.tools["mrq_create_job"](
                    ctx=None,
                    job_name="Trailer_Master",
                    sequence="/Game/Cinematics/LS_Trailer",
                    map="/Game/Maps/L_Cinematic",
                    output_directory="C:/Renders/Trailer",
                    resolution=[3840, 2160],
                    image_format="exr",
                    clear_queue=True,
                )),
                json.loads(await self.mcp.tools["mrq_add_render_setting"](
                    ctx=None,
                    job_name="Trailer_Master",
                    setting_type="anti_aliasing",
                    temporal_samples=8,
                    spatial_samples=2,
                    warmup_frames=16,
                    console_variables={"r.MotionBlurQuality": 4.0},
                )),
                json.loads(await self.mcp.tools["mrq_render_queue"](
                    ctx=None,
                    executor="pie",
                    dry_run=True,
                )),
            ]

        stages = [
            "mrq_create_job",
            "mrq_add_render_setting",
            "mrq_render_queue",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertEqual(calls[0][1]["sequence"], "/Game/Cinematics/LS_Trailer")
        self.assertEqual(calls[0][1]["map"], "/Game/Maps/L_Cinematic")
        self.assertEqual(calls[0][1]["resolution"], [3840, 2160])
        self.assertEqual(calls[0][1]["image_format"], "exr")
        self.assertTrue(calls[0][1]["clear_queue"])
        self.assertEqual(calls[1][1]["setting_type"], "anti_aliasing")
        self.assertEqual(calls[1][1]["temporal_samples"], 8)
        self.assertEqual(calls[1][1]["spatial_samples"], 2)
        self.assertEqual(calls[1][1]["warmup_frames"], 16)
        self.assertEqual(calls[1][1]["console_variables"], {"r.MotionBlurQuality": 4.0})
        self.assertTrue(calls[2][1]["dry_run"])
        self.assertEqual(calls[2][1]["executor"], "pie")


if __name__ == "__main__":
    unittest.main()
