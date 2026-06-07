"""Offline smoke coverage for Workstream B.14 MetaHuman tools."""

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


class TestB14MetaHumanTools(unittest.TestCase):
    def setUp(self):
        from tools.animation_tools import register_animation_tools

        self.mcp = _MockMCP()
        register_animation_tools(self.mcp)

    def test_b14_metahuman_tools_register(self):
        expected = {
            "metahuman_import",
            "metahuman_inspect_package",
            "metahuman_link_to_skeleton",
            "metahuman_assign_dna",
            "metahuman_configure_wrapper",
        }
        self.assertTrue(expected.issubset(set(self.mcp.tools)))

    def test_metahuman_tools_call_native_routes(self):
        calls = []

        def fake_send(command, params):
            calls.append((command, params))
            return {
                "success": True,
                "route": command,
                "config_path": "C:/Project/Config/DefaultEngine.ini",
                "manifest_section": f"UnrealMCP.MetaHuman.{params.get('character_name', 'Ada')}",
                "asset_count": 3,
                "asset_class_counts": {"SkeletalMesh": 2, "Blueprint": 1},
                "skeleton_links": {
                    "body_skeletal_mesh": params.get("body_skeletal_mesh", ""),
                    "target_skeleton": params.get("target_skeleton", "/Game/MetaHumans/Ada/Body/SKEL_Ada"),
                    "ik_rig": params.get("ik_rig", ""),
                    "retargeter": params.get("retargeter", ""),
                },
                "dna": {
                    "dna_asset": params.get("dna_asset", ""),
                    "dna_file": params.get("dna_file", ""),
                    "face_skeletal_mesh": params.get("face_skeletal_mesh", ""),
                    "rig_logic_asset": params.get("rig_logic_asset", ""),
                },
                "wrapper": {
                    "wrapper_blueprint": params.get("wrapper_blueprint", ""),
                    "parent_class": params.get("parent_class", "/Script/Engine.Character"),
                    "gameplay_tag": params.get("gameplay_tag", "Character.MetaHuman"),
                },
            }

        with patch("tools.animation_tools._send", side_effect=fake_send):
            payloads = [
                json.loads(self.mcp.tools["metahuman_import"](
                    ctx=None,
                    character_name="Ada",
                    metahuman_root="/Game/MetaHumans/Ada",
                    expected_blueprint="/Game/MetaHumans/Ada/BP_Ada",
                    body_skeletal_mesh="/Game/MetaHumans/Ada/Body/SK_Ada_Body",
                    face_skeletal_mesh="/Game/MetaHumans/Ada/Face/SK_Ada_Face",
                    create_manifest=True,
                )),
                json.loads(self.mcp.tools["metahuman_inspect_package"](
                    ctx=None,
                    character_name="Ada",
                    metahuman_root="/Game/MetaHumans/Ada",
                )),
                json.loads(self.mcp.tools["metahuman_link_to_skeleton"](
                    ctx=None,
                    character_name="Ada",
                    body_skeletal_mesh="/Game/MetaHumans/Ada/Body/SK_Ada_Body",
                    target_skeleton="/Game/MetaHumans/Ada/Body/SKEL_Ada",
                    ik_rig="/Game/Animation/IK/IK_Ada",
                    retargeter="/Game/Animation/Retargeters/RTG_Ada",
                    anim_blueprint="/Game/MetaHumans/Ada/ABP_Ada",
                    post_process_anim_blueprint="/Game/MetaHumans/Ada/ABP_Ada_Post",
                )),
                json.loads(self.mcp.tools["metahuman_assign_dna"](
                    ctx=None,
                    character_name="Ada",
                    dna_asset="/Game/MetaHumans/Ada/Face/Ada_DNA",
                    dna_file="C:/MetaHumans/Ada/Ada.dna",
                    face_skeletal_mesh="/Game/MetaHumans/Ada/Face/SK_Ada_Face",
                    rig_logic_asset="/Game/MetaHumans/Ada/Face/CR_Ada_Face",
                )),
                json.loads(self.mcp.tools["metahuman_configure_wrapper"](
                    ctx=None,
                    character_name="Ada",
                    wrapper_blueprint="/Game/Characters/BP_AdaWrapper",
                    parent_class="/Script/Engine.Character",
                    body_component_name="Body",
                    face_component_name="Face",
                    attach_to_component="Mesh",
                    gameplay_tag="Character.MetaHuman.NPC",
                )),
            ]

        stages = [
            "metahuman_import",
            "metahuman_inspect_package",
            "metahuman_link_to_skeleton",
            "metahuman_assign_dna",
            "metahuman_configure_wrapper",
        ]
        for payload, stage in zip(payloads, stages):
            _assert_structured(self, payload, stage)
            self.assertTrue(payload["success"])

        self.assertEqual([call[0] for call in calls], stages)
        self.assertEqual(calls[0][1]["metahuman_root"], "/Game/MetaHumans/Ada")
        self.assertTrue(calls[0][1]["create_manifest"])
        self.assertEqual(calls[1][1]["metahuman_root"], "/Game/MetaHumans/Ada")
        self.assertEqual(calls[2][1]["body_skeletal_mesh"], "/Game/MetaHumans/Ada/Body/SK_Ada_Body")
        self.assertEqual(calls[2][1]["retargeter"], "/Game/Animation/Retargeters/RTG_Ada")
        self.assertEqual(calls[3][1]["dna_asset"], "/Game/MetaHumans/Ada/Face/Ada_DNA")
        self.assertEqual(calls[3][1]["rig_logic_asset"], "/Game/MetaHumans/Ada/Face/CR_Ada_Face")
        self.assertEqual(calls[4][1]["wrapper_blueprint"], "/Game/Characters/BP_AdaWrapper")
        self.assertEqual(calls[4][1]["gameplay_tag"], "Character.MetaHuman.NPC")


if __name__ == "__main__":
    unittest.main()
