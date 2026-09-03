"""Offline coverage for Uthana generated-animation next-step guidance."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from chat.cockpit import (
    build_execution_review,
    build_next_safe_step_gate,
    build_queue_target_context,
    execution_review_context,
    generated_animation_lifecycle_context,
)


def _lifecycle(
    *,
    task_status: str = "not_submitted",
    motion_id: str = "",
    quality_gate_count: int = 7,
    quality_evidence_count: int = 0,
    task_type: str = "text_to_motion",
    submit_tool: str = "gen_uthana_text_to_motion",
    planned_submit_tool: str = "gen_uthana_text_to_motion",
    status_tool: str = "gen_uthana_get_motion",
    video_file: str = "",
    public_mcp_tool_available: bool = True,
    unsupported_reason: str = "",
) -> list[dict]:
    return [
        {
            "manifest_path": ".mcp_artifacts/ide_companion_sessions/ide-companion_asset_lifecycle.json",
            "preview_animation_assets": [
                {
                    "id": "animation_01",
                    "name": "A_EnemyScout_PatrolWalk",
                    "role": "patrol_walk",
                    "provider": "uthana",
                    "task_type": task_type,
                    "source_video_file": video_file,
                    "video_reference_required": task_type == "video_to_motion",
                    "video_reference_provided": bool(video_file),
                    "task_status": task_status,
                    "motion_id": motion_id,
                    "submit_tool": submit_tool,
                    "planned_submit_tool": planned_submit_tool,
                    "status_tool": status_tool,
                    "public_mcp_tool_available": public_mcp_tool_available,
                    "unsupported_reason": unsupported_reason,
                    "expected_import_path": "/Game/Generated/Animations/A_EnemyScout_PatrolWalk",
                    "target_skeleton": "UE5 Manny",
                    "format": "fbx",
                    "estimated_seconds": 4,
                    "default_character_id": "cXi2eAP19XwQ",
                    "quality_gate_count": quality_gate_count,
                    "quality_evidence_count": quality_evidence_count,
                    "quality_gate_preview": [
                        "download allowance",
                        "import result",
                        "retarget/readback proof",
                        "AnimGraph reference",
                        "PIE proof",
                        "ledger evidence",
                        "human approval",
                    ],
                }
            ],
        }
    ]


def _readiness(
    *,
    paid_allowed: bool = False,
    editor_allowed: bool = False,
) -> dict:
    return {
        "state": "ready" if paid_allowed and editor_allowed else "blocked",
        "paid_animation_generation": {
            "allowed": paid_allowed,
            "missing_gates": [] if paid_allowed else [
                "animation_provider_api_key_configured",
                "wallet_evidence_recorded",
                "spend_confirmation_recorded",
            ],
        },
        "editor_mutation": {
            "allowed": editor_allowed,
            "missing_gates": [] if editor_allowed else ["unreal_bridge_reachable"],
        },
    }


class UthanaAnimationNextSafeActionTest(unittest.TestCase):
    def test_missing_public_uthana_submit_tool_blocks_before_usage_gates(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(
                task_type="video_to_motion",
                submit_tool="",
                planned_submit_tool="gen_uthana_video_to_motion",
                public_mcp_tool_available=False,
                unsupported_reason="Uthana video_to_motion is planned provider capability but no public MCP submit tool is registered yet.",
            ),
            readiness_policy=_readiness(paid_allowed=False, editor_allowed=False),
        )

        action = context["next_safe_action"]
        self.assertEqual(context["state"], "blocked")
        self.assertEqual(context["unsupported_provider_task_count"], 1)
        self.assertEqual(context["unsupported_provider_task_preview"][0]["planned_submit_tool"], "gen_uthana_video_to_motion")
        self.assertIn("provider_submit_tool_missing", context["missing_stage_preview"])
        self.assertEqual(context["target_animation"]["planned_submit_tool"], "gen_uthana_video_to_motion")
        self.assertFalse(context["target_animation"]["public_mcp_tool_available"])
        self.assertEqual(context["submit_tool"], "")
        self.assertEqual(context["planned_submit_tool"], "gen_uthana_video_to_motion")
        self.assertFalse(context["public_mcp_tool_available"])
        self.assertEqual(action["action_id"], "implement_uthana_submit_tool_wrapper")
        self.assertEqual(action["action_type"], "provider_wrapper_gap")
        self.assertEqual(action["candidate_tool_after_unblocked"], "gen_uthana_video_to_motion")
        self.assertFalse(action["can_execute_now"])
        self.assertFalse(action["requires_provider_network"])
        self.assertFalse(action["requires_bridge"])
        self.assertTrue(action["no_provider_call"])
        self.assertIn("public_mcp_submit_tool_missing", action["blocking_gate_preview"])

    def test_paid_animation_gates_are_resolved_before_provider_submit(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(),
            readiness_policy=_readiness(paid_allowed=False, editor_allowed=False),
        )

        action = context["next_safe_action"]
        self.assertEqual(action["schema"], "unreal_mcp_chat_generated_animation_next_safe_action.v1")
        self.assertEqual(action["state"], "blocked")
        self.assertEqual(action["action_id"], "resolve_uthana_usage_gates")
        self.assertEqual(action["tool"], "gen_compile_ide_companion_readiness")
        self.assertEqual(action["candidate_tool_after_unblocked"], "gen_uthana_text_to_motion")
        self.assertFalse(action["can_execute_now"])
        self.assertFalse(action["requires_provider_network"])
        self.assertFalse(action["requires_bridge"])
        self.assertTrue(action["no_provider_call"])
        self.assertTrue(action["no_download"])
        self.assertTrue(action["no_import"])
        self.assertTrue(action["no_editor_mutation"])
        self.assertIn("animation_provider_api_key_configured", action["blocking_gate_preview"])
        usage = context["uthana_usage_contract"]
        self.assertEqual(usage["schema"], "unreal_mcp_uthana_animation_usage_contract.v1")
        self.assertEqual(usage["provider"], "uthana")
        self.assertEqual(usage["review_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
        self.assertEqual(usage["review_receipt_required_command"], "python scripts\\write_paid_generation_evidence_review.py")
        self.assertIn("gen_uthana_get_account", usage["allowance_tools"])
        self.assertIn("gen_uthana_check_download_allowed", usage["allowance_tools"])
        self.assertIn("confirm_usage=True", usage["usage_confirmation_field"])
        self.assertEqual(
            usage["operator_command_handoff_ids"],
            ["record_masked_uthana_allowance_evidence", "record_explicit_uthana_usage_approval"],
        )
        self.assertEqual(usage["operator_command_handoff"][0]["provider"], "uthana")
        self.assertEqual(usage["operator_command_handoff"][0]["command_kind"], "local_receipt")
        self.assertTrue(usage["operator_command_handoff"][0]["records_evidence_only"])
        self.assertTrue(usage["operator_command_handoff"][0]["no_provider_call"])
        self.assertTrue(usage["operator_command_handoff"][0]["no_task_submission"])
        self.assertEqual(
            context["uthana_usage_next_operator_command_handoff"]["id"],
            "record_masked_uthana_allowance_evidence",
        )
        self.assertTrue(usage["no_provider_call"])
        self.assertTrue(usage["no_task_submission"])
        self.assertTrue(usage["no_download"])
        self.assertTrue(usage["no_import"])
        self.assertTrue(usage["no_editor_mutation"])

    def test_provider_submit_is_ready_to_confirm_after_paid_gates(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(),
            readiness_policy=_readiness(paid_allowed=True, editor_allowed=False),
        )

        action = context["next_safe_action"]
        self.assertEqual(action["state"], "ready_to_confirm")
        self.assertEqual(action["action_id"], "submit_uthana_text_to_motion")
        self.assertEqual(action["tool"], "gen_uthana_text_to_motion")
        self.assertEqual(action["confirmation_field"], "confirm_usage")
        self.assertTrue(action["requires_provider_network"])
        self.assertTrue(action["requires_usage_confirmation"])
        self.assertFalse(action["can_execute_now"])
        self.assertEqual(action["argument_preview"]["prompt"], "A_EnemyScout_PatrolWalk")
        self.assertEqual(action["argument_preview"]["character_id"], "cXi2eAP19XwQ")

    def test_video_to_motion_requires_reference_before_upload(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(
                task_type="video_to_motion",
                submit_tool="gen_uthana_video_to_motion",
                planned_submit_tool="gen_uthana_video_to_motion",
                status_tool="gen_uthana_get_job",
            ),
            readiness_policy=_readiness(paid_allowed=True, editor_allowed=False),
        )

        action = context["next_safe_action"]
        self.assertEqual(action["state"], "blocked")
        self.assertEqual(action["action_id"], "attach_uthana_video_reference")
        self.assertEqual(action["action_type"], "input_evidence")
        self.assertEqual(action["candidate_tool_after_unblocked"], "gen_uthana_video_to_motion")
        self.assertFalse(action["requires_provider_network"])
        self.assertFalse(action["requires_usage_confirmation"])
        self.assertIn("uthana_video_reference_file", action["blocking_gate_preview"])
        self.assertIn("uthana_video_reference_file", context["missing_stage_preview"])
        self.assertTrue(context["target_animation"]["video_reference_required"])
        self.assertFalse(context["target_animation"]["video_reference_provided"])

    def test_video_to_motion_submit_is_ready_after_reference_and_paid_gates(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(
                task_type="video_to_motion",
                submit_tool="gen_uthana_video_to_motion",
                planned_submit_tool="gen_uthana_video_to_motion",
                status_tool="gen_uthana_get_job",
                video_file="C:/captures/patrol_walk.mp4",
            ),
            readiness_policy=_readiness(paid_allowed=True, editor_allowed=False),
        )

        action = context["next_safe_action"]
        self.assertEqual(action["state"], "ready_to_confirm")
        self.assertEqual(action["action_id"], "submit_uthana_video_to_motion")
        self.assertEqual(action["tool"], "gen_uthana_video_to_motion")
        self.assertEqual(action["status_tool"], "gen_uthana_get_job")
        self.assertEqual(action["expected_followup_tool"], "gen_uthana_get_job")
        self.assertEqual(action["confirmation_field"], "confirm_usage")
        self.assertTrue(action["requires_provider_network"])
        self.assertTrue(action["requires_usage_confirmation"])
        self.assertFalse(action["can_execute_now"])
        self.assertEqual(action["argument_preview"]["video_file"], "C:/captures/patrol_walk.mp4")
        self.assertEqual(action["argument_preview"]["motion_name"], "A_EnemyScout_PatrolWalk")
        self.assertEqual(action["argument_preview"]["model"], "video-to-motion-v2")
        self.assertTrue(context["target_animation"]["video_reference_provided"])

    def test_video_to_motion_paid_gate_candidate_uses_video_tool(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(
                task_type="video_to_motion",
                submit_tool="gen_uthana_video_to_motion",
                planned_submit_tool="gen_uthana_video_to_motion",
                status_tool="gen_uthana_get_job",
                video_file="C:/captures/patrol_walk.mp4",
            ),
            readiness_policy=_readiness(paid_allowed=False, editor_allowed=False),
        )

        action = context["next_safe_action"]
        self.assertEqual(action["action_id"], "resolve_uthana_usage_gates")
        self.assertEqual(action["candidate_tool_after_unblocked"], "gen_uthana_video_to_motion")
        self.assertIn("gen_uthana_video_to_motion", context["uthana_usage_confirmation_field"])

    def test_editor_import_gates_block_after_motion_exists(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(task_status="success", motion_id="motion_123"),
            readiness_policy=_readiness(paid_allowed=True, editor_allowed=False),
        )

        action = context["next_safe_action"]
        self.assertEqual(action["state"], "blocked")
        self.assertEqual(action["action_id"], "unblock_animation_import_gates")
        self.assertEqual(action["candidate_tool_after_unblocked"], "gen_uthana_import_animation_to_project")
        self.assertTrue(action["requires_bridge"])
        self.assertFalse(action["can_execute_now"])
        self.assertIn("unreal_bridge_reachable", action["blocking_gate_preview"])

    def test_quality_proof_is_next_after_motion_and_editor_gates(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(task_status="success", motion_id="motion_123", quality_evidence_count=3),
            readiness_policy=_readiness(paid_allowed=True, editor_allowed=True),
        )

        action = context["next_safe_action"]
        self.assertEqual(action["state"], "needs_evidence")
        self.assertEqual(action["action_id"], "compile_generated_animation_evidence")
        self.assertEqual(action["tool"], "gen_compile_generated_animation_evidence")
        self.assertFalse(action["requires_provider_network"])
        self.assertFalse(action["requires_bridge"])
        self.assertFalse(action["can_execute_now"])

    def test_record_evidence_is_next_when_all_quality_gates_are_met(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(
                task_status="success",
                motion_id="motion_123",
                quality_gate_count=7,
                quality_evidence_count=7,
            ),
            readiness_policy=_readiness(paid_allowed=True, editor_allowed=True),
        )

        action = context["next_safe_action"]
        self.assertEqual(context["state"], "ready")
        self.assertEqual(action["state"], "ready_to_record")
        self.assertEqual(action["action_id"], "record_generated_animation_evidence")
        self.assertEqual(action["tool"], "skill_record_ide_companion_evidence")
        self.assertTrue(action["can_execute_now"])
        self.assertFalse(action["requires_provider_network"])
        self.assertFalse(action["requires_bridge"])

    def test_generated_animation_gates_survive_queue_and_execution_review(self) -> None:
        context = generated_animation_lifecycle_context(
            asset_lifecycles=_lifecycle(task_status="success", motion_id="motion_123", quality_evidence_count=3),
            readiness_policy=_readiness(paid_allowed=True, editor_allowed=True),
        )
        queue_context = build_queue_target_context(
            target_phase="animation_generation",
            work_order_template={"template_name": "enemy_patrol_chase_attack"},
            ledger_path=".mcp_artifacts/ide_companion_sessions/ide-companion.json",
            generated_animation_context=context,
        )

        self.assertEqual(queue_context["generated_animation_asset_count"], 1)
        self.assertEqual(queue_context["generated_animation_target_name"], "A_EnemyScout_PatrolWalk")
        self.assertEqual(queue_context["generated_animation_target_skeleton"], "UE5 Manny")
        self.assertEqual(queue_context["generated_animation_next_safe_action_id"], "compile_generated_animation_evidence")
        self.assertEqual(
            queue_context["generated_animation_usage_contract_schema"],
            "unreal_mcp_uthana_animation_usage_contract.v1",
        )
        self.assertEqual(queue_context["generated_animation_usage_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
        self.assertIn("gen_uthana_get_account", queue_context["generated_animation_allowance_tool_preview"])
        self.assertEqual(queue_context["generated_animation_usage_operator_command_handoff_count"], 2)
        self.assertIn(
            "record_masked_uthana_allowance_evidence",
            queue_context["generated_animation_usage_operator_command_handoff_ids"],
        )
        self.assertIn("confirm_usage=True", queue_context["generated_animation_usage_confirmation_field"])
        self.assertIn("retarget/readback", " ".join(queue_context["generated_animation_gate_policy"]))

        next_safe_step = build_next_safe_step_gate(
            queues=[
                {
                    "queue_path": ".mcp_artifacts/ide_companion_sessions/ide-companion_queue.json",
                    "queue_name": "editor_queue",
                    "target_phase": "animation_generation",
                    "next_action_id": "wire_patrol_walk_animgraph",
                    "next_action_tool": "connect_anim_graph_nodes",
                    "bridge_required": True,
                    "can_execute_now": True,
                    "preview_actions": [
                        {
                            "id": "wire_patrol_walk_animgraph",
                            "tool": "connect_anim_graph_nodes",
                            "label": "Wire patrol walk AnimGraph",
                            "argument_keys": ["anim_blueprint_name", "source_node_id", "target_node_id"],
                        }
                    ],
                }
            ],
            blocking_gates=[],
            evidence_recording={"items": []},
            generated_animation_context=context,
        )
        self.assertEqual(next_safe_step["generated_animation_asset_count"], 1)
        self.assertIn("Do not execute generated animation work", " ".join(next_safe_step["execution_policy"]))

        review = execution_review_context(build_execution_review(
            next_safe_step=next_safe_step,
            evidence_recording={"items": []},
        ))
        self.assertEqual(review["generated_animation_asset_count"], 1)
        self.assertEqual(review["generated_animation_target_provider"], "uthana")
        self.assertEqual(review["generated_animation_target_skeleton"], "UE5 Manny")
        self.assertEqual(review["generated_animation_next_safe_tool"], "gen_compile_generated_animation_evidence")
        self.assertEqual(review["generated_animation_usage_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
        self.assertIn("gen_uthana_get_account", review["generated_animation_allowance_tool_preview"])
        self.assertIn("AnimGraph", " ".join(review["generated_animation_gate_policy"]))


if __name__ == "__main__":
    unittest.main()
