"""Offline smoke coverage for provider-neutral generated asset lifecycles."""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent
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
    testcase.assertEqual(payload["meta"]["tool"], "skill_compile_ide_companion_asset_lifecycle_manifest")


def _session_plan() -> dict:
    from skills.playable_slice.skill import skill_compile_ide_companion_session

    result = skill_compile_ide_companion_session(
        project_brief="solo developer generated asset lifecycle slice",
        mechanic_brief="enemy AI patrol that updates the objective HUD",
        session_name="asset-lifecycle-test",
        include_generated_assets=True,
    )
    return result["outputs"]["plan"]


class TestD34IdeCompanionAssetLifecycleManifest(unittest.TestCase):
    def test_lifecycle_manifest_maps_prompts_to_provider_tasks_and_quality_gates(self):
        from skills.playable_slice.skill import (
            skill_compile_ide_companion_asset_lifecycle_manifest,
            skill_compile_ide_companion_placeholder_manifest,
        )

        plan = _session_plan()
        placeholder = skill_compile_ide_companion_placeholder_manifest(plan)["outputs"]["manifest"]
        result = skill_compile_ide_companion_asset_lifecycle_manifest(plan, placeholder_manifest=placeholder)

        _assert_structured(self, result, "asset_lifecycle_manifest_ready")
        manifest = result["outputs"]["manifest"]
        self.assertEqual(manifest["schema"], "unreal_mcp_ide_companion_generated_asset_lifecycle.v1")
        self.assertTrue(manifest["provider_neutral"])
        self.assertEqual(manifest["preferred_provider"], "tripo")
        self.assertEqual(manifest["asset_count"], len(plan["generated_asset_prompts"]))
        self.assertEqual(manifest["animation_asset_count"], len(plan["generated_animation_prompts"]))
        self.assertIn("uthana", manifest["supported_provider_slots"])
        self.assertFalse(manifest["network_required"])
        self.assertFalse(manifest["spend_required"])
        self.assertTrue(manifest["future_provider_network_required"])
        self.assertTrue(manifest["future_spend_required"])

        first_asset = manifest["assets"][0]
        self.assertEqual(first_asset["provider_task"]["submit_tool"], "gen_tripo_text_to_model")
        self.assertEqual(first_asset["provider_task"]["import_tool"], "gen_tripo_import_to_project")
        self.assertTrue(first_asset["provider_task"]["requires_confirm_spend"])
        self.assertTrue(first_asset["placeholder_replacement"]["has_placeholder"])
        self.assertIn("mesh loads in Unreal", first_asset["quality_gates"])
        self.assertIn("viewport thumbnail or screenshot proof exists", first_asset["quality_gates"])
        self.assertIn("IDE companion ledger records import and replacement evidence", first_asset["quality_gates"])
        quality_contract = first_asset["quality_proof_contract"]
        self.assertEqual(quality_contract["schema"], "unreal_mcp_generated_asset_quality_proof_contract.v1")
        self.assertEqual(quality_contract["asset_id"], first_asset["id"])
        self.assertIn("material_slot_count", quality_contract["required_after_import"])
        self.assertIn("collision_readability_check", quality_contract["required_after_import"])
        self.assertIn("viewport_thumbnail_or_screenshot", quality_contract["required_after_import"])
        self.assertIn("ide_companion_ledger_event", quality_contract["required_after_import"])
        self.assertIn("viewport or thumbnail proof is missing", quality_contract["stop_if_missing"])

        first_animation = manifest["animation_assets"][0]
        self.assertEqual(first_animation["provider"], "uthana")
        self.assertEqual(first_animation["provider_task"]["submit_tool"], "gen_uthana_text_to_motion")
        self.assertEqual(first_animation["provider_task"]["download_tool"], "gen_uthana_download_motion")
        self.assertEqual(first_animation["provider_task"]["import_tool"], "gen_uthana_import_animation_to_project")
        self.assertIn("retarget/readback", first_animation["animation_usage"])
        self.assertIn("AnimGraph or state machine references the generated motion", first_animation["quality_gates"])
        animation_quality_contract = first_animation["quality_proof_contract"]
        self.assertEqual(animation_quality_contract["schema"], "unreal_mcp_generated_animation_quality_proof_contract.v1")
        self.assertEqual(animation_quality_contract["animation_id"], first_animation["id"])
        self.assertIn("animation_sequence_load_readback", animation_quality_contract["required_after_import"])
        self.assertIn("target_skeleton_or_retarget_asset", animation_quality_contract["required_after_import"])
        self.assertIn("animgraph_or_state_machine_reference", animation_quality_contract["required_after_import"])
        self.assertIn("pie_motion_playback_or_viewport_proof", animation_quality_contract["required_after_import"])
        self.assertIn("PIE playback or viewport proof is missing", animation_quality_contract["stop_if_missing"])

        stage_names = {stage["name"] for stage in manifest["lifecycle_stages"]}
        for expected in (
            "prompt_manifest",
            "credit_gate",
            "task_submission",
            "status_wait",
            "download_import",
            "animation_motion_generation",
            "animation_retarget_import",
            "placeholder_fallback",
            "replacement_mapping",
            "material_collision_pass",
            "viewport_proof",
            "ledger_evidence",
        ):
            self.assertIn(expected, stage_names)

    def test_lifecycle_manifest_supports_uthana_video_to_motion_with_job_polling(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_asset_lifecycle_manifest

        plan = _session_plan()
        plan["generated_animation_prompts"][0]["task_type"] = "video_to_motion"
        plan["generated_animation_prompts"][0]["video_file"] = "C:/captures/patrol_walk.mp4"

        result = skill_compile_ide_companion_asset_lifecycle_manifest(plan)
        manifest = result["outputs"]["manifest"]
        animation = manifest["animation_assets"][0]
        provider_task = animation["provider_task"]

        _assert_structured(self, result, "asset_lifecycle_manifest_ready")
        self.assertEqual(animation["task_type"], "video_to_motion")
        self.assertEqual(animation["video_file"], "C:/captures/patrol_walk.mp4")
        self.assertEqual(animation["reference_video_file"], "C:/captures/patrol_walk.mp4")
        self.assertEqual(provider_task["status"], "not_submitted")
        self.assertEqual(provider_task["submit_tool"], "gen_uthana_video_to_motion")
        self.assertEqual(provider_task["planned_submit_tool"], "gen_uthana_video_to_motion")
        self.assertEqual(provider_task["status_tool"], "gen_uthana_get_job")
        self.assertTrue(provider_task["public_mcp_tool_available"])
        self.assertEqual(provider_task["unsupported_reason"], "")
        self.assertEqual(manifest["unsupported_provider_task_count"], 0)

    def test_lifecycle_manifest_handles_no_generated_assets_without_future_spend(self):
        from skills.playable_slice.skill import (
            skill_compile_ide_companion_asset_lifecycle_manifest,
            skill_compile_ide_companion_session,
        )

        plan = skill_compile_ide_companion_session(
            project_brief="solo developer no generated assets slice",
            mechanic_brief="objective HUD update",
            session_name="no-assets",
            include_generated_assets=False,
        )["outputs"]["plan"]
        result = skill_compile_ide_companion_asset_lifecycle_manifest(plan)
        manifest = result["outputs"]["manifest"]

        _assert_structured(self, result, "asset_lifecycle_manifest_ready")
        self.assertEqual(manifest["asset_count"], 0)
        self.assertEqual(manifest["assets"], [])
        self.assertEqual(manifest["animation_asset_count"], 0)
        self.assertEqual(manifest["animation_assets"], [])
        self.assertFalse(manifest["future_provider_network_required"])
        self.assertFalse(manifest["future_spend_required"])

    def test_lifecycle_manifest_can_write_local_session_artifact(self):
        import skills.playable_slice.skill as skill_module

        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(skill_module, "_REPO_ROOT", Path(tmp)):
                plan = _session_plan()
                result = skill_module.skill_compile_ide_companion_asset_lifecycle_manifest(
                    plan,
                    write_manifest=True,
                    manifest_name="asset_lifecycle",
                )

                _assert_structured(self, result, "asset_lifecycle_manifest_ready")
                self.assertTrue(result["outputs"]["manifest_written"])
                manifest_path = Path(result["outputs"]["manifest_path"])
                self.assertTrue(manifest_path.exists())
                self.assertIn(".mcp_artifacts", manifest_path.as_posix())
                saved = json.loads(manifest_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["schema"], "unreal_mcp_ide_companion_generated_asset_lifecycle.v1")
                self.assertEqual(saved["session_name"], "asset_lifecycle_test")

    def test_registered_tool_returns_json(self):
        from skills.playable_slice.skill import register_playable_slice_skill

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_compile_ide_companion_asset_lifecycle_manifest", mcp.tools)
        payload = json.loads(asyncio.run(mcp.tools["skill_compile_ide_companion_asset_lifecycle_manifest"](
            None,
            _session_plan(),
        )))

        _assert_structured(self, payload, "asset_lifecycle_manifest_ready")
        self.assertEqual(payload["outputs"]["manifest"]["schema"], "unreal_mcp_ide_companion_generated_asset_lifecycle.v1")

    def test_invalid_session_plan_is_structured(self):
        from skills.playable_slice.skill import skill_compile_ide_companion_asset_lifecycle_manifest

        payload = skill_compile_ide_companion_asset_lifecycle_manifest({"schema": "wrong"})

        _assert_structured(self, payload, "invalid_session_plan")
        self.assertFalse(payload["success"])
        self.assertIn("session_plan must use unreal_mcp_ide_companion_session_plan.v1", payload["errors"])

    def test_static_registration_kb_and_command_palette(self):
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        gen_kb_text = (REPO_ROOT / "knowledge_base" / "31_GENERATIVE_CONTENT_PIPELINE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("skill_compile_ide_companion_asset_lifecycle_manifest", skill_text)
        self.assertIn("unreal_mcp_ide_companion_generated_asset_lifecycle.v1", skill_text)
        self.assertIn("write_manifest", skill_text)
        self.assertIn("D34 IDE Companion Generated Asset Lifecycle Manifest", kb_text)
        self.assertIn("skill_compile_ide_companion_asset_lifecycle_manifest", kb_text)
        self.assertIn("unreal_mcp_ide_companion_generated_asset_lifecycle.v1", gen_kb_text)
        self.assertIn("D.151 threads Uthana motion prompts", gen_kb_text)
        self.assertIn("D.152 exposes those prompt requirements", gen_kb_text)
        self.assertIn("D.152 - Gameplay-template generated-animation cockpit review", changelog_text)
        self.assertIn("D.151 - Gameplay mechanic Uthana animation prompts", changelog_text)
        self.assertIn("D.34 - IDE companion generated asset lifecycle manifest", changelog_text)
        self.assertIn("Compile Generated Asset Lifecycle", panel_text)
        self.assertIn("unreal_mcp_ide_companion_generated_asset_lifecycle.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
