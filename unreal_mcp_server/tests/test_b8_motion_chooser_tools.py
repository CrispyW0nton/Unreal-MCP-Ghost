"""Offline smoke coverage for Workstream B.8 Motion Matching and Chooser tools."""

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


class TestB8MotionChooserTools(unittest.TestCase):
    def setUp(self):
        from tools.animation_tools import register_animation_tools

        self.mcp = _MockMCP()
        register_animation_tools(self.mcp)

    def test_b8_motion_chooser_tools_register(self):
        expected = {
            "motion_create_pose_search_schema",
            "motion_create_pose_search_database",
            "motion_add_database_sequence",
            "motion_inspect_pose_search_asset",
            "chooser_create_table",
            "chooser_add_asset_row",
            "chooser_inspect_table",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    def test_motion_chooser_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "route": command,
                "asset_path": params.get("asset") or params.get("database") or params.get("chooser") or "/Game/Animation/TestAsset",
                "object_path": "/Game/Animation/TestAsset.TestAsset",
                "row_count": 1,
                "animation_asset_count": 1,
                "channel_count": 4,
            }

        with patch("tools.animation_tools._send", side_effect=fake_send):
            payloads = [
                json.loads(self.mcp.tools["motion_create_pose_search_schema"](
                    ctx=None,
                    name="PSS_Locomotion",
                    skeleton="/Game/Characters/Hero/SK_Hero",
                    sample_rate=60,
                    overwrite=True,
                )),
                json.loads(self.mcp.tools["motion_create_pose_search_database"](
                    ctx=None,
                    name="PSD_Locomotion",
                    schema="/Game/Animation/MotionMatching/PSS_Locomotion",
                    sequences=["/Game/Characters/Hero/Animations/A_Run"],
                    search_mode="brute_force",
                    overwrite=True,
                )),
                json.loads(self.mcp.tools["motion_add_database_sequence"](
                    ctx=None,
                    database="/Game/Animation/MotionMatching/PSD_Locomotion",
                    sequence="/Game/Characters/Hero/Animations/A_Walk",
                    enabled=False,
                    disable_reselection=True,
                    mirror_option="both",
                    sampling_range=[0.1, 1.2],
                )),
                json.loads(self.mcp.tools["motion_inspect_pose_search_asset"](
                    ctx=None,
                    asset="/Game/Animation/MotionMatching/PSD_Locomotion",
                )),
                json.loads(self.mcp.tools["chooser_create_table"](
                    ctx=None,
                    name="CH_Locomotion",
                    result_class="/Script/Engine.AnimationAsset",
                    overwrite=True,
                )),
                json.loads(self.mcp.tools["chooser_add_asset_row"](
                    ctx=None,
                    chooser="/Game/Animation/Choosers/CH_Locomotion",
                    asset="/Game/Characters/Hero/Animations/A_Run",
                    enabled=False,
                )),
                json.loads(self.mcp.tools["chooser_inspect_table"](
                    ctx=None,
                    chooser="/Game/Animation/Choosers/CH_Locomotion",
                )),
            ]

        stages = [
            "motion_create_pose_search_schema",
            "motion_create_pose_search_database",
            "motion_add_database_sequence",
            "motion_inspect_pose_search_asset",
            "chooser_create_table",
            "chooser_add_asset_row",
            "chooser_inspect_table",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertEqual(calls[0][1]["sample_rate"], 60)
        self.assertTrue(calls[0][1]["overwrite"])
        self.assertEqual(calls[1][1]["sequences"], ["/Game/Characters/Hero/Animations/A_Run"])
        self.assertEqual(calls[1][1]["search_mode"], "brute_force")
        self.assertFalse(calls[2][1]["enabled"])
        self.assertTrue(calls[2][1]["disable_reselection"])
        self.assertEqual(calls[2][1]["sampling_range"], [0.1, 1.2])
        self.assertEqual(calls[3][1]["asset"], "/Game/Animation/MotionMatching/PSD_Locomotion")
        self.assertEqual(calls[4][1]["result_class"], "/Script/Engine.AnimationAsset")
        self.assertFalse(calls[5][1]["enabled"])
        self.assertEqual(calls[6][1]["chooser"], "/Game/Animation/Choosers/CH_Locomotion")


if __name__ == "__main__":
    unittest.main()
