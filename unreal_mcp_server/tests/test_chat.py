"""Offline tests for the UE editor chat bridge."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.testclient import TestClient

_HERE = os.path.dirname(__file__)
_SERVER_ROOT = os.path.dirname(_HERE)
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)

from chat import cockpit, routes, storage  # noqa: E402


class _MockMCP:
    def __init__(self):
        self._tools: Dict[str, Any] = {}

    def tool(self):
        def dec(fn):
            self._tools[fn.__name__] = fn
            return fn
        return dec

    def get_tool(self, name):
        return self._tools.get(name)

    def list_tool_names(self):
        return list(self._tools.keys())


class _FakeTool:
    def __init__(self, name: str, module: str):
        def _fn():
            return None

        _fn.__module__ = module
        self.name = name
        self.description = "Fake tool for route tests."
        self.parameters = {"properties": {"blueprint_name": {"type": "string"}}}
        self.fn = _fn


class _MockRouteMCP:
    def __init__(self):
        self._routes = []
        self._tool_manager = self
        self._tools = [_FakeTool("get_server_info", "tools.knowledge_tools")]

    def custom_route(self, path, methods, name):
        def dec(fn):
            self._routes.append(Route(path, fn, methods=methods))
            return fn
        return dec

    def list_tools(self):
        return self._tools


def _parse(result: str) -> dict:
    return json.loads(result)


class TestCockpitEvidenceSelection(unittest.TestCase):
    def test_recordable_evidence_prefers_dirty_promotion_before_paid_generation(self):
        evidence_recording = {
            "items": [
                {
                    "id": "record_paid_generation_evidence",
                    "phase_name": "session_preflight",
                    "evidence_type": "paid_generation_evidence",
                    "label": "Record paid generation evidence",
                    "state": "pending",
                    "required_artifacts": ["wallet_evidence_recorded"],
                },
                {
                    "id": "record_dirty_promotion_review",
                    "phase_name": "session_preflight",
                    "evidence_type": "dirty_promotion_review",
                    "label": "Record dirty promotion review",
                    "state": "pending",
                    "required_artifacts": ["dirty_promotion_review_receipt"],
                },
            ],
        }

        selected = cockpit.select_recordable_evidence_item(evidence_recording)

        self.assertEqual(selected["id"], "record_dirty_promotion_review")
        self.assertEqual(selected["evidence_type"], "dirty_promotion_review")
        self.assertIn("dirty_promotion_review_receipt", selected["required_artifacts"])

    def test_recordable_evidence_still_prefers_readiness_repair_queue(self):
        evidence_recording = {
            "items": [
                {
                    "id": "record_dirty_promotion_review",
                    "phase_name": "session_preflight",
                    "evidence_type": "dirty_promotion_review",
                    "label": "Record dirty promotion review",
                    "state": "pending",
                    "required_artifacts": ["dirty_promotion_review_receipt"],
                },
                {
                    "id": "record_readiness_repair_queue",
                    "phase_name": "session_preflight",
                    "evidence_type": "readiness_repair_queue",
                    "label": "Record repair queue",
                    "state": "pending",
                    "required_artifacts": ["review_dirty_groups_for_promotion"],
                },
            ],
        }

        selected = cockpit.select_recordable_evidence_item(evidence_recording)

        self.assertEqual(selected["id"], "record_readiness_repair_queue")
        self.assertEqual(selected["evidence_type"], "readiness_repair_queue")

    def test_evidence_target_context_includes_readiness_policy_domain(self):
        context = cockpit.evidence_target_context({
            "id": "record_readiness_policy",
            "source": "readiness_policy",
            "phase_name": "session_preflight",
            "evidence_type": "readiness_policy",
            "label": "Record readiness policy gate evidence",
            "state": "pending",
            "required_artifacts": ["unreal_bridge_reachable", "wallet_evidence_recorded"],
            "metadata": {
                "schema": "unreal_mcp_chat_readiness_policy_summary.v1",
                "state": "blocked",
                "blocked_policy_count": 5,
                "blocked_policy_preview": [
                    "editor_mutation",
                    "paid_generation",
                    "paid_animation_generation",
                    "blueprint_mutation",
                    "wip_promotion",
                ],
                "editor_mutation_allowed": False,
                "editor_mutation_missing_gate_count": 1,
                "editor_mutation_missing_gate_preview": ["unreal_bridge_reachable"],
                "editor_mutation_evidence_required_count": 1,
                "editor_mutation_evidence_required_preview": ["successful_bridge_ping"],
                "paid_generation_allowed": False,
                "paid_generation_missing_gate_count": 2,
                "paid_generation_missing_gate_preview": ["wallet_evidence_recorded", "spend_confirmation_recorded"],
                "paid_generation_evidence_required_count": 2,
                "paid_generation_evidence_required_preview": ["masked_wallet_balance", "explicit_spend_approval"],
                "paid_animation_generation_allowed": False,
                "paid_animation_generation_missing_gate_count": 2,
                "paid_animation_generation_missing_gate_preview": ["wallet_evidence_recorded", "spend_confirmation_recorded"],
                "paid_animation_generation_evidence_required_count": 2,
                "paid_animation_generation_evidence_required_preview": [
                    "masked_uthana_allowance_evidence",
                    "explicit_uthana_usage_approval",
                ],
                "blueprint_mutation_allowed": False,
                "blueprint_mutation_missing_gate_count": 3,
                "blueprint_mutation_missing_gate_preview": [
                    "unreal_bridge_reachable",
                    "blueprint_pre_read_evidence",
                    "blueprint_compile_plan",
                ],
                "blueprint_mutation_evidence_required_count": 2,
                "blueprint_mutation_evidence_required_preview": [
                    "compile_check_after_mutation",
                    "blueprint_readback_after_mutation",
                ],
                "wip_promotion_allowed": False,
                "wip_promotion_missing_gate_count": 1,
                "wip_promotion_missing_gate_preview": ["dirty_state_grouped_for_promotion"],
                "wip_promotion_evidence_required_count": 2,
                "wip_promotion_evidence_required_preview": [
                    "last_no_mutation_unittest_receipt",
                    "dirty_promotion_review_receipt",
                ],
                "no_editor_mutation": True,
                "no_provider_call": True,
                "no_git_mutation": True,
            },
        })

        self.assertEqual(context["evidence_type"], "readiness_policy")
        for absent in (
            "readiness_repair_queue",
            "dirty_promotion_review",
            "generated_asset",
            "generated_animation",
            "paid_generation_evidence",
            "bridge_ping_receipt",
            "provider_config_review",
            "chat_cockpit_start_receipt",
            "platform_stability_review",
            "runtime_verification",
            "queued_action",
            "feature_completion_contract",
        ):
            self.assertNotIn(absent, context)
        readiness_context = context["readiness_policy"]
        self.assertEqual(readiness_context["schema"], "unreal_mcp_chat_readiness_policy_summary.v1")
        self.assertEqual(readiness_context["state"], "blocked")
        self.assertEqual(readiness_context["blocked_policy_count"], 5)
        self.assertIn("paid_animation_generation", readiness_context["blocked_policy_preview"])
        self.assertFalse(readiness_context["editor_mutation_allowed"])
        self.assertEqual(readiness_context["editor_mutation_missing_gate_count"], 1)
        self.assertIn("successful_bridge_ping", readiness_context["editor_mutation_evidence_required_preview"])
        self.assertFalse(readiness_context["paid_generation_allowed"])
        self.assertIn("wallet_evidence_recorded", readiness_context["paid_generation_missing_gate_preview"])
        self.assertFalse(readiness_context["paid_animation_generation_allowed"])
        self.assertIn(
            "masked_uthana_allowance_evidence",
            readiness_context["paid_animation_generation_evidence_required_preview"],
        )
        self.assertFalse(readiness_context["blueprint_mutation_allowed"])
        self.assertIn("blueprint_compile_plan", readiness_context["blueprint_mutation_missing_gate_preview"])
        self.assertFalse(readiness_context["wip_promotion_allowed"])
        self.assertIn("dirty_promotion_review_receipt", readiness_context["wip_promotion_evidence_required_preview"])
        self.assertTrue(readiness_context["no_editor_mutation"])
        self.assertTrue(readiness_context["no_provider_call"])
        self.assertTrue(readiness_context["no_git_mutation"])


class TestChatStorage(unittest.TestCase):
    def test_append_poll_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Saved" / "MCP" / "chat_history.json"

            first = storage.append_message({
                "sender": "human",
                "message": "Can you check this laser?",
                "timestamp": "2026-04-30T14:23:00Z",
                "context": {"selected_actor": "BP_DefenseLaser3"},
            }, path=path)
            storage.append_message({
                "sender": "agent",
                "message": "I can check BP_DefenseLaser3.",
                "timestamp": "2026-04-30T14:24:00Z",
            }, path=path)

            self.assertTrue(first["message_id"])
            human_messages = storage.poll_messages(
                sender="human",
                since="2026-04-30T14:22:00Z",
                path=path,
            )
            self.assertEqual(len(human_messages), 1)
            self.assertEqual(human_messages[0]["context"]["selected_actor"], "BP_DefenseLaser3")
            self.assertEqual(len(storage.get_recent_messages(limit=1, path=path)), 1)

    def test_rejects_invalid_sender(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat_history.json"
            with self.assertRaises(ValueError):
                storage.append_message({
                    "sender": "bot",
                    "message": "bad",
                    "timestamp": "2026-04-30T14:23:00Z",
                }, path=path)

    def test_named_sessions_are_isolated_and_exportable(self):
        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "Saved" / "MCPChat"
            storage.append_message({
                "sender": "human",
                "message": "Dungeon run",
                "timestamp": "2026-04-30T14:23:00Z",
            }, session="Dungeon", session_dir=session_dir)
            storage.append_message({
                "sender": "human",
                "message": "Slime run",
                "timestamp": "2026-04-30T14:24:00Z",
            }, session="Slime", session_dir=session_dir)

            self.assertEqual(
                [item["message"] for item in storage.get_recent_messages(session="Dungeon", session_dir=session_dir)],
                ["Dungeon run"],
            )
            sessions = storage.list_sessions(session_dir=session_dir)
            self.assertEqual({item["name"] for item in sessions["sessions"]}, {"Dungeon", "Slime"})
            storage.pin_session("Dungeon", session_dir=session_dir)
            storage.rename_session("Slime", "Boss Room", session_dir=session_dir)
            markdown = storage.export_session_markdown("Boss Room", session_dir=session_dir)
            self.assertIn("# MCP Chat Session: Boss Room", markdown)
            self.assertIn("Slime run", markdown)
            storage.delete_session("Dungeon", session_dir=session_dir)
            self.assertFalse((session_dir / "Dungeon.json").exists())


class TestChatRoutes(unittest.TestCase):
    def test_send_poll_history_and_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat_history.json"
            app = Starlette(routes=[
                Route("/chat/send", routes.chat_send, methods=["POST"]),
                Route("/chat/poll", routes.chat_poll, methods=["GET"]),
                Route("/chat/history", routes.chat_history, methods=["GET"]),
                Route("/chat/clear", routes.chat_clear, methods=["POST"]),
                Route("/chat/sessions", routes.chat_sessions, methods=["GET"]),
                Route("/chat/session/new", routes.chat_session_new, methods=["POST"]),
                Route("/chat/session/rename", routes.chat_session_rename, methods=["POST"]),
                Route("/chat/session/pin", routes.chat_session_pin, methods=["POST"]),
                Route("/chat/session/delete", routes.chat_session_delete, methods=["POST"]),
                Route("/chat/session/export", routes.chat_session_export, methods=["GET"]),
                Route("/chat/session/resume-context", routes.chat_session_resume_context, methods=["GET"]),
            ])

            with patch.object(storage, "DEFAULT_CHAT_HISTORY_PATH", path), patch.object(storage, "DEFAULT_CHAT_SESSION_DIR", Path(tmp) / "MCPChat"):
                client = TestClient(app)
                send_resp = client.post("/chat/send", json={
                    "sender": "human",
                    "message": "Hello from UE",
                    "timestamp": "2026-04-30T14:23:00Z",
                })
                self.assertEqual(send_resp.status_code, 200)
                self.assertEqual(send_resp.json()["status"], "ok")

                poll_resp = client.get("/chat/poll?sender=human&since=2026-04-30T14:22:00Z")
                self.assertEqual(poll_resp.status_code, 200)
                self.assertEqual(len(poll_resp.json()["messages"]), 1)

                history_resp = client.get("/chat/history?limit=50")
                self.assertEqual(history_resp.status_code, 200)
                self.assertEqual(len(history_resp.json()["messages"]), 1)

                clear_resp = client.post("/chat/clear")
                self.assertEqual(clear_resp.status_code, 200)
                self.assertEqual(client.get("/chat/history").json()["messages"], [])

                new_resp = client.post("/chat/session/new", json={"name": "Dungeon"})
                self.assertEqual(new_resp.status_code, 200)
                self.assertEqual(new_resp.json()["session"]["name"], "Dungeon")
                session_send = client.post("/chat/send?session=Dungeon", json={
                    "sender": "human",
                    "message": "Session scoped",
                    "timestamp": "2026-04-30T14:25:00Z",
                })
                self.assertEqual(session_send.status_code, 200)
                self.assertEqual(len(client.get("/chat/history?session=Dungeon").json()["messages"]), 1)
                self.assertEqual(client.get("/chat/history").json()["messages"], [])
                self.assertEqual(client.post("/chat/session/pin", json={"name": "Dungeon", "pinned": True}).status_code, 200)
                self.assertEqual(client.post("/chat/session/rename", json={"old_name": "Dungeon", "new_name": "Boss"}).status_code, 200)
                export_resp = client.get("/chat/session/export?name=Boss")
                self.assertEqual(export_resp.status_code, 200)
                self.assertIn("Session scoped", export_resp.text)
                self.assertIn("Boss", {item["name"] for item in client.get("/chat/sessions").json()["sessions"]})
                self.assertEqual(client.post("/chat/session/delete", json={"name": "Boss"}).status_code, 200)

    def test_session_resume_context_route_reads_chat_and_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            chat_dir = Path(tmp) / "MCPChat"
            ledger_dir = Path(tmp) / ".mcp_artifacts" / "ide_companion_sessions"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "ide-companion.json").write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_ledger.v1",
                "session_name": "ide-companion",
                "events": [{"phase_name": "session_preflight", "summary": "Preflight blocked by bridge."}],
                "evidence": {"session_preflight": []},
                "latest_status": {
                    "completed_phase_count": 1,
                    "blocking_gates": ["unreal_bridge_reachable"],
                    "next_phase": "mechanic_design",
                    "next_action": {"tool": "skill_plan_gameplay_mechanic"},
                },
                "latest_work_order": {"target_phase": "mechanic_design"},
                "latest_readiness": {},
            }), encoding="utf-8")

            app = Starlette(routes=[
                Route("/chat/session/resume-context", routes.chat_session_resume_context, methods=["GET"]),
                Route("/chat/cockpit/overview", routes.chat_cockpit_overview, methods=["GET"]),
            ])
            with (
                patch.object(storage, "DEFAULT_CHAT_SESSION_DIR", chat_dir),
                patch.object(cockpit, "DEFAULT_IDE_COMPANION_SESSION_DIR", ledger_dir),
            ):
                storage.append_message({
                    "sender": "human",
                    "message": "Resume the cockpit.",
                    "timestamp": "2026-04-30T14:26:00Z",
                }, session="ide-companion")
                client = TestClient(app)
                response = client.get("/chat/session/resume-context?session=ide-companion&limit=5")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["session"], "ide-companion")
            self.assertEqual(len(payload["recent_messages"]), 1)
            self.assertEqual(payload["matching_ide_companion_ledger"]["next_tool"], "skill_plan_gameplay_mechanic")
            self.assertTrue(payload["suggested_actions"][0]["enabled"])
            self.assertEqual(payload["warnings"], [])

    def test_cockpit_overview_route_reads_ledger_and_editor_queue(self):
        with tempfile.TemporaryDirectory() as tmp:
            chat_dir = Path(tmp) / "MCPChat"
            ledger_dir = Path(tmp) / ".mcp_artifacts" / "ide_companion_sessions"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "ide-companion.json").write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_ledger.v1",
                "session_name": "ide-companion",
                "events": [
                    {
                        "phase_name": "orient_to_project",
                        "evidence_type": "context",
                        "summary": "Project context loaded.",
                        "artifacts": ["kb://32_AGENT_PLAYABLE_SLICE_RECIPE.md"],
                        "timestamp_unix": 1770000000,
                    },
                    {
                        "phase_name": "session_preflight",
                        "evidence_type": "readiness",
                        "summary": "Bridge is offline.",
                        "artifacts": ["preflight report", "bridge_ping: offline"],
                        "timestamp_unix": 1770000100,
                    },
                    {
                        "phase_name": "editor_implementation",
                        "evidence_type": "failure",
                        "summary": "Blueprint compile failed: TargetActor pin is missing.",
                        "artifacts": ["compile report", "BP_EnemyScout"],
                        "timestamp_unix": 1770000150,
                    },
                ],
                "evidence": {"session_preflight": []},
                "latest_status": {
                    "completed_phase_count": 1,
                    "blocking_gates": ["unreal_bridge_reachable"],
                    "next_phase": "editor_implementation",
                    "next_action": {"tool": "skill_compile_ide_companion_editor_queue"},
                },
                "latest_work_order": {
                    "target_phase": "editor_implementation",
                    "feature_template_work": {
                        "schema": "unreal_mcp_gameplay_feature_template.v1",
                        "template_name": "enemy_patrol_chase_attack",
                        "display_name": "Enemy Patrol/Chase/Attack",
                        "asset_list": [
                            "BP_EnemyScout",
                            "BB_EnemyScout",
                            "BT_EnemyScout",
                        ],
                        "generated_animation_prompts": [
                            {
                                "role": "enemy_patrol_locomotion",
                                "name": "A_EnemyScout_PatrolWalk",
                                "provider": "uthana",
                                "task_type": "text_to_motion",
                                "target_skeleton": "UE5 Manny",
                                "estimated_seconds": 4,
                            },
                            {
                                "role": "enemy_chase_locomotion",
                                "name": "A_EnemyScout_ChaseRun",
                                "provider": "uthana",
                                "task_type": "text_to_motion",
                                "target_skeleton": "UE5 Manny",
                                "estimated_seconds": 4,
                            },
                        ],
                        "estimated_uthana_motion_seconds": 8,
                        "animation_system_hook": {
                            "needed": True,
                            "provider": "uthana",
                            "tools": [
                                "gen_uthana_text_to_motion",
                                "gen_uthana_import_animation_to_project",
                                "gen_compile_generated_animation_evidence",
                            ],
                            "proof_required": [
                                "uthana_api_key_configured",
                                "animgraph_or_state_machine_reference",
                                "pie_motion_playback_or_viewport_proof",
                                "ide_companion_ledger_event",
                            ],
                        },
                        "ownership_split": {
                            "Blueprint": ["BP_EnemyScout patrol/chase hooks"],
                            "AI": ["Blackboard keys and Behavior Tree branches"],
                        },
                        "graph_component_operations": [
                            "Create Blackboard keys TargetActor, PatrolPoint, and CombatState",
                            "Create Behavior Tree selector branches for patrol, chase, and attack",
                        ],
                        "editor_operation_checklist": [
                            {
                                "id": "enemy_patrol_chase_attack_01",
                                "phase": "editor_implementation",
                                "operation_type": "ai_blackboard_behavior_tree",
                                "summary": "Create Blackboard keys TargetActor, PatrolPoint, and CombatState",
                                "tool_candidates": ["bt_get_info", "set_behavior_tree_blackboard"],
                                "requires_bridge": True,
                                "requires_compile_after": True,
                                "requires_readback_after": True,
                                "readback_evidence": "Blueprint graph/component summary confirms the operation before PIE.",
                                "ledger_evidence_type": "feature_template_operation",
                                "operation_proof_contract": {
                                    "schema": "unreal_mcp_gameplay_feature_operation_proof.v1",
                                    "operation_id": "enemy_patrol_chase_attack_01",
                                    "required_before": ["unreal_bridge_reachable", "blueprint_pre_read_evidence"],
                                    "required_after": ["blueprint_compile_report", "graph_or_component_readback", "ide_companion_ledger_event"],
                                    "stop_if_missing": ["compile report missing or failed"],
                                },
                            },
                            {
                                "id": "enemy_patrol_chase_attack_02",
                                "phase": "editor_implementation",
                                "operation_type": "blueprint_graph_wiring",
                                "summary": "Create Behavior Tree selector branches for patrol, chase, and attack",
                                "tool_candidates": ["bp_get_graph_summary", "bp_add_node", "bp_connect_pins"],
                                "requires_bridge": True,
                                "requires_compile_after": True,
                                "requires_readback_after": True,
                                "readback_evidence": "Blueprint graph/component summary confirms the operation before PIE.",
                                "ledger_evidence_type": "feature_template_operation",
                                "operation_proof_contract": {
                                    "schema": "unreal_mcp_gameplay_feature_operation_proof.v1",
                                    "operation_id": "enemy_patrol_chase_attack_02",
                                    "required_before": ["unreal_bridge_reachable", "blueprint_pre_read_evidence"],
                                    "required_after": ["blueprint_compile_report", "graph_or_component_readback", "ide_companion_ledger_event"],
                                    "stop_if_missing": ["compile report missing or failed"],
                                },
                            },
                        ],
                        "completion_contract": {
                            "schema": "unreal_mcp_gameplay_feature_completion_contract.v1",
                            "required_evidence": [
                                "feature_template_packet",
                                "blueprint_compile_report",
                                "graph_or_component_readback",
                                "pie_log",
                                "viewport_or_hud_screenshot",
                                "ide_companion_ledger_event",
                            ],
                            "proof_gates": [
                                {"name": "editor_operations_read_back", "required_count": 2},
                                {"name": "pie_validation_passed", "required_count": 1},
                                {"name": "ledger_evidence_recorded", "required_count": 1},
                            ],
                            "stop_before_complete": [
                                "any editor operation lacks compile/readback evidence",
                                "IDE companion ledger evidence is missing",
                            ],
                        },
                        "compile_readback_checks": [
                            "compile_blueprint_and_report succeeds for BP_EnemyScout",
                        ],
                        "pie_validation": [
                            "Enemy patrols when no target is known",
                        ],
                        "repair_instructions": [
                            "If a Blueprint compile fails, stop and create a repair work order",
                        ],
                        "evidence_requirements": [
                            "Blueprint compile report",
                            "PIE log and viewport screenshot",
                        ],
                        "stop_conditions": [
                            "Stop if the AI pawn cannot reach the navmesh",
                        ],
                    },
                },
                "session_plan": {
                    "schema": "unreal_mcp_ide_companion_session_plan.v1",
                    "phases": [
                        {"name": "orient_to_project"},
                        {"name": "session_preflight"},
                        {"name": "editor_implementation"},
                    ],
                },
                "latest_readiness": {},
            }), encoding="utf-8")
            (ledger_dir / "ide-companion_editor_queue.json").write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_editor_queue.v1",
                "session_name": "ide-companion",
                "queue_name": "editor_queue",
                "queue_path": ".mcp_artifacts/ide_companion_sessions/ide-companion_editor_queue.json",
                "target_phase": "editor_implementation",
                "source": "placeholder_manifest",
                "actions": [
                    {"id": "create_placeholder_folder", "tool": "create_folder", "arguments": {"path": "/Game/Generated"}},
                    {"id": "create_placeholder_material", "tool": "create_material", "arguments": {"asset_path": "/Game/Generated/M_Placeholder"}},
                ],
                "blocking_gates": ["unreal_bridge_reachable"],
                "bridge_required": True,
                "bridge_blocked": True,
                "can_execute_now": False,
                "feature_template": {
                    "schema": "unreal_mcp_gameplay_feature_template.v1",
                    "template_name": "enemy_patrol_chase_attack",
                    "display_name": "Enemy Patrol/Chase/Attack",
                    "editor_operation_count": 2,
                    "next_operation_id": "enemy_patrol_chase_attack_01",
                    "next_operation_type": "ai_blackboard_behavior_tree",
                    "next_operation_summary": "Create or assign Blackboard keys TargetActor, PatrolLocation, AggroRange, and AttackRange.",
                    "next_operation_tool_candidates": [
                        "create_blackboard",
                        "set_behavior_tree_blackboard",
                        "build_behavior_tree",
                        "bt_get_info",
                    ],
                    "next_operation_required_before": ["unreal_bridge_reachable", "blueprint_pre_read_evidence"],
                    "next_operation_required_after": [
                        "blueprint_compile_report",
                        "graph_or_component_readback",
                        "ide_companion_ledger_event",
                    ],
                    "next_operation_stop_if_missing": [
                        "bridge ping failed",
                        "compile report missing or failed",
                        "readback does not show the expected operation",
                    ],
                },
                "evidence_to_collect": ["compile report"],
                "network_required": False,
                "unreal_editor_required": True,
                "spend_required": False,
            }), encoding="utf-8")
            (ledger_dir / "ide-companion_asset_lifecycle.json").write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_generated_asset_lifecycle.v1",
                "session_name": "ide-companion",
                "preferred_provider": "tripo",
                "asset_count": 2,
                "animation_asset_count": 1,
                "assets": [
                    {
                        "id": "asset_01",
                        "name": "SM_ObjectiveBeacon",
                        "role": "objective_marker",
                        "provider": "tripo",
                        "expected_import_path": "/Game/Generated/Assets/SM_ObjectiveBeacon",
                        "provider_task": {"status": "not_submitted"},
                        "placeholder_replacement": {
                            "has_placeholder": True,
                            "placeholder_asset_path": "/Game/Generated/Placeholders/PH_ObjectiveBeacon",
                        },
                        "quality_proof_contract": {
                            "schema": "unreal_mcp_generated_asset_quality_proof_contract.v1",
                            "asset_id": "asset_01",
                            "required_after_import": [
                                "static_mesh_load_readback",
                                "material_slot_count",
                                "collision_readability_check",
                                "viewport_thumbnail_or_screenshot",
                                "ide_companion_ledger_event",
                            ],
                            "stop_if_missing": ["viewport or thumbnail proof is missing"],
                        },
                    },
                    {
                        "id": "asset_02",
                        "name": "SM_EnemyScout",
                        "role": "enemy",
                        "provider": "tripo",
                        "expected_import_path": "/Game/Generated/Assets/SM_EnemyScout",
                        "provider_task": {
                            "status": "success",
                            "task_id": "tsk_enemy_scout",
                            "submit_tool": "gen_tripo_create_task",
                            "status_tool": "gen_tripo_get_task",
                            "download_tool": "gen_tripo_download_result",
                            "import_tool": "import_asset",
                        },
                        "placeholder_replacement": {"has_placeholder": False},
                        "quality_proof_contract": {
                            "schema": "unreal_mcp_generated_asset_quality_proof_contract.v1",
                            "asset_id": "asset_02",
                            "required_after_import": [
                                "static_mesh_load_readback",
                                "material_slot_count",
                                "collision_readability_check",
                                "viewport_thumbnail_or_screenshot",
                                "ide_companion_ledger_event",
                            ],
                            "stop_if_missing": ["viewport or thumbnail proof is missing"],
                        },
                    },
                ],
                "animation_assets": [
                    {
                        "id": "animation_01",
                        "name": "A_EnemyScout_PatrolWalk",
                        "role": "enemy_patrol_locomotion",
                        "provider": "uthana",
                        "task_type": "text_to_motion",
                        "expected_import_path": "/Game/Generated/Animations/A_EnemyScout_PatrolWalk",
                        "target_skeleton": "UE5 Manny",
                        "format": "fbx",
                        "estimated_seconds": 4,
                        "default_character_id": "cXi2eAP19XwQ",
                        "provider_task": {
                            "status": "not_submitted",
                            "motion_id": "",
                            "submit_tool": "gen_uthana_text_to_motion",
                            "status_tool": "gen_uthana_get_motion",
                            "download_tool": "gen_uthana_download_motion",
                            "import_tool": "gen_uthana_import_animation_to_project",
                        },
                        "quality_gates": [
                            "Uthana motion request has explicit prompt and usage approval",
                            "downloaded FBX/GLB/BVH motion file exists",
                            "Animation Sequence imports under /Game",
                            "target skeleton or retarget asset is recorded",
                            "AnimGraph or state machine references the generated motion",
                            "PIE log and viewport proof show the motion in gameplay context",
                            "IDE companion ledger records animation import, retarget, and runtime evidence",
                        ],
                        "quality_proof_contract": {
                            "schema": "unreal_mcp_generated_animation_quality_proof_contract.v1",
                            "animation_id": "animation_01",
                            "required_after_import": [
                                "animation_sequence_load_readback",
                                "target_skeleton_or_retarget_asset",
                                "animgraph_or_state_machine_reference",
                                "pie_motion_playback_or_viewport_proof",
                                "ide_companion_ledger_event",
                            ],
                            "stop_if_missing": ["PIE playback or viewport proof is missing"],
                        },
                    },
                ],
                "future_provider_network_required": True,
                "future_spend_required": True,
                "stop_conditions": ["confirm_spend is not explicitly true for paid submission"],
            }), encoding="utf-8")
            (ledger_dir / "other-companion.json").write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_ledger.v1",
                "session_name": "other-companion",
                "events": [
                    {
                        "phase_name": "mechanic_design",
                        "evidence_type": "plan",
                        "summary": "Other companion has a playable slice plan.",
                        "artifacts": ["other plan"],
                        "timestamp_unix": 1770000200,
                    },
                ],
                "latest_status": {
                    "completed_phase_count": 2,
                    "blocking_gates": [],
                    "next_phase": "runtime_verification",
                    "next_action": {"tool": "skill_compile_ide_companion_work_order"},
                },
                "latest_work_order": {"target_phase": "runtime_verification"},
            }), encoding="utf-8")
            (ledger_dir / "other-companion_editor_queue.json").write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_editor_queue.v1",
                "session_name": "other-companion",
                "queue_name": "editor_queue",
                "target_phase": "runtime_verification",
                "actions": [
                    {"id": "run_pie_probe", "tool": "editor_run_pie", "arguments": {"duration_seconds": 15}},
                ],
                "blocking_gates": [],
                "bridge_required": True,
                "bridge_blocked": False,
                "can_execute_now": True,
                "evidence_to_collect": ["PIE log"],
            }), encoding="utf-8")
            (ledger_dir / "other-companion_asset_lifecycle.json").write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_generated_asset_lifecycle.v1",
                "session_name": "other-companion",
                "preferred_provider": "tripo",
                "asset_count": 1,
                "assets": [
                    {
                        "id": "asset_other_01",
                        "name": "SM_OtherPickup",
                        "role": "pickup",
                        "provider": "tripo",
                        "expected_import_path": "/Game/Generated/Assets/SM_OtherPickup",
                        "provider_task": {"status": "success"},
                        "placeholder_replacement": {"has_placeholder": False},
                    },
                ],
            }), encoding="utf-8")

            app = Starlette(routes=[
                Route("/chat/cockpit/overview", routes.chat_cockpit_overview, methods=["GET"]),
            ])
            test_lane = cockpit.test_lane_context()
            test_lane.update({
                "no_mutation_receipt_exists": True,
                "no_mutation_state": "ok",
                "no_mutation_status": "success",
                "no_mutation_ok": True,
                "no_mutation_exit_code": 0,
                "no_mutation_mutation_count": 0,
                "no_mutation_tracked_file_count": max(1, int(test_lane.get("no_mutation_tracked_file_count", 0) or 1)),
                "no_mutation_snapshot_digest_match": True,
                "no_mutation_snapshot_scope": "git_tracked_worktree",
                "no_mutation_snapshot_hash_algorithm": "sha256(path\\0content_sha256_or_missing\\0)",
            })
            platform_preflight = json.loads(json.dumps(cockpit.platform_preflight_context()))
            platform_preflight.update({
                "ready_for_platform_stability": True,
                "successful_bridge_ping": False,
                "bridge_ready": False,
                "bridge_tcp_ready": False,
                "bridge_ping_receipt_state": "missing",
                "chat_ready": True,
                "chat_tcp_ready": True,
                "provider": "tripo",
                "animation_provider": "uthana",
                "provider_api_key_configured": True,
                "provider_api_key_source": "env",
                "animation_provider_api_key_configured": True,
                "animation_provider_api_key_source": "env",
                "provider_secrets_gitignored": True,
                "provider_settings_gitignored": True,
                "no_mutation_test_state": "ok",
                "no_mutation_test_ok": True,
                "no_mutation_test_status": "success",
                "no_mutation_test_exit_code": 0,
                "no_mutation_test_mutation_count": 0,
                "no_mutation_test_receipt_exists": True,
                "no_mutation_test_tracked_file_count": max(
                    1,
                    int(platform_preflight.get("no_mutation_test_tracked_file_count", 0) or 1),
                ),
                "no_mutation_test_snapshot_digest_match": True,
                "no_mutation_test_snapshot_scope": "git_tracked_worktree",
                "no_mutation_test_snapshot_hash_algorithm": "sha256(path\\0content_sha256_or_missing\\0)",
            })
            with (
                patch.object(storage, "DEFAULT_CHAT_SESSION_DIR", chat_dir),
                patch.object(cockpit, "DEFAULT_IDE_COMPANION_SESSION_DIR", ledger_dir),
                patch.object(cockpit, "test_lane_context", return_value=test_lane),
                patch.object(cockpit, "platform_preflight_context", return_value=platform_preflight),
            ):
                storage.append_message({
                    "sender": "human",
                    "message": "Show the cockpit.",
                    "timestamp": "2026-04-30T14:27:00Z",
                }, session="ide-companion")
                client = TestClient(app)
                response = client.get("/chat/cockpit/overview?session=ide-companion&limit=5")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["schema"], "unreal_mcp_chat_cockpit_overview.v1")
            self.assertEqual(payload["session"], "ide-companion")
            self.assertEqual(payload["session_picker"]["schema"], "unreal_mcp_chat_ide_companion_session_picker.v1")
            self.assertEqual(payload["session_picker"]["session_count"], 2)
            self.assertEqual(payload["session_picker"]["sessions"][0]["session_name"], "ide-companion")
            self.assertTrue(payload["session_picker"]["sessions"][0]["selected"])
            self.assertEqual(payload["session_picker"]["sessions"][0]["queued_action_count"], 2)
            self.assertEqual(payload["session_picker"]["sessions"][0]["generated_asset_count"], 2)
            self.assertEqual(payload["session_picker"]["sessions"][0]["generated_pending_count"], 1)
            self.assertIn("unreal_bridge_reachable", payload["session_picker"]["sessions"][0]["blocking_gates"])
            other_picker = payload["session_picker"]["sessions"][1]
            self.assertEqual(other_picker["session_name"], "other-companion")
            self.assertFalse(other_picker["selected"])
            self.assertEqual(other_picker["queued_action_count"], 1)
            self.assertEqual(other_picker["generated_asset_count"], 1)
            self.assertTrue(other_picker["can_execute_now"])
            self.assertEqual(payload["blocker_resolutions"]["schema"], "unreal_mcp_chat_blocker_resolution_summary.v1")
            self.assertEqual(payload["blocker_resolutions"]["blocking_gate_count"], 1)
            self.assertEqual(payload["blocker_resolutions"]["hard_blocker_count"], 1)
            self.assertEqual(payload["blocker_resolutions"]["resolutions"][0]["blocker"], "unreal_bridge_reachable")
            self.assertEqual(payload["blocker_resolutions"]["resolutions"][0]["recommended_strategy"], "unblock_first")
            self.assertTrue(payload["blocker_resolutions"]["resolutions"][0]["can_continue_offline"])
            blockers_card = next(card for card in payload["cards"] if card["id"] == "blockers")
            self.assertEqual(blockers_card["details"]["hard_blocker_count"], 1)
            self.assertEqual(blockers_card["details"]["resolution_preview"][0]["blocker"], "unreal_bridge_reachable")
            self.assertEqual(payload["readiness_policy"]["schema"], "unreal_mcp_chat_readiness_policy_summary.v1")
            self.assertEqual(payload["readiness_policy"]["state"], "blocked")
            self.assertIn("unreal_bridge_reachable", payload["readiness_policy"]["editor_mutation"]["missing_gates"])
            self.assertFalse(payload["readiness_policy"]["paid_generation"]["allowed"])
            self.assertIn("wallet_evidence_recorded", payload["readiness_policy"]["paid_generation"]["missing_gates"])
            self.assertIn("spend_confirmation_recorded", payload["readiness_policy"]["paid_generation"]["missing_gates"])
            self.assertFalse(payload["readiness_policy"]["paid_animation_generation"]["allowed"])
            self.assertIn("wallet_evidence_recorded", payload["readiness_policy"]["paid_animation_generation"]["missing_gates"])
            self.assertIn("spend_confirmation_recorded", payload["readiness_policy"]["paid_animation_generation"]["missing_gates"])
            self.assertFalse(payload["readiness_policy"]["blueprint_mutation"]["allowed"])
            self.assertIn("blueprint_pre_read_evidence", payload["readiness_policy"]["blueprint_mutation"]["missing_gates"])
            self.assertIn("blueprint_readback_plan", payload["readiness_policy"]["blueprint_mutation"]["missing_gates"])
            self.assertTrue(payload["readiness_policy"]["wip_promotion"]["allowed"])
            readiness_card = next(card for card in payload["cards"] if card["id"] == "readiness_policy")
            self.assertIn("unreal_bridge_reachable", readiness_card["details"]["editor_mutation_missing_gates"])
            self.assertIn("wallet_evidence_recorded", readiness_card["details"]["paid_generation_missing_gates"])
            self.assertIn("wallet_evidence_recorded", readiness_card["details"]["paid_animation_generation_missing_gates"])
            self.assertEqual(readiness_card["details"]["blueprint_mutation_state"], "blocked")
            self.assertEqual(readiness_card["details"]["blueprint_template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(readiness_card["details"]["blueprint_target_phase"], "editor_implementation")
            self.assertEqual(readiness_card["details"]["blueprint_editor_operation_count"], 2)
            self.assertEqual(readiness_card["details"]["blueprint_bridge_required_operation_count"], 2)
            self.assertEqual(readiness_card["details"]["blueprint_compile_after_operation_count"], 2)
            self.assertEqual(readiness_card["details"]["blueprint_readback_after_operation_count"], 2)
            self.assertEqual(readiness_card["details"]["blueprint_queued_action_count"], 2)
            self.assertTrue(readiness_card["details"]["blueprint_pre_read_required"])
            self.assertTrue(readiness_card["details"]["blueprint_compile_plan_required"])
            self.assertTrue(readiness_card["details"]["blueprint_readback_plan_required"])
            self.assertIn("blueprint_pre_read", readiness_card["details"]["blueprint_evidence_required_preview"])
            self.assertIn("set_behavior_tree_blackboard", readiness_card["details"]["blueprint_editor_operation_tool_preview"])
            self.assertIn(
                "graph_or_component_readback",
                readiness_card["details"]["blueprint_operation_proof_required_after_preview"],
            )
            self.assertEqual(payload["readiness_repair_queue"]["schema"], "unreal_mcp_readiness_repair_queue.v1")
            self.assertEqual(payload["readiness_repair_queue"]["state"], "blocked")
            self.assertEqual(payload["readiness_repair_queue"]["recommended_next"], "verify_unreal_bridge_reachability")
            self.assertEqual(payload["readiness_repair_queue"]["next_action"]["gate"], "unreal_bridge_reachable")
            self.assertTrue(payload["readiness_repair_queue"]["no_auto_execute"])
            self.assertTrue(payload["readiness_repair_queue"]["no_secret_echo"])
            self.assertEqual(payload["editor_queues"][0]["action_count"], 2)
            self.assertEqual(payload["editor_queues"][0]["evidence_preview"], ["compile report"])
            self.assertEqual(payload["editor_queues"][0]["next_action_tool"], "create_folder")
            self.assertEqual(payload["editor_queues"][0]["feature_template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(payload["editor_queues"][0]["feature_template_next_operation_id"], "enemy_patrol_chase_attack_01")
            self.assertIn("set_behavior_tree_blackboard", payload["editor_queues"][0]["feature_template_next_operation_tool_preview"])
            self.assertIn("graph_or_component_readback", payload["editor_queues"][0]["feature_template_next_operation_required_after_preview"])
            self.assertEqual(payload["editor_queues"][0]["preview_actions"][0]["id"], "create_placeholder_folder")
            self.assertEqual(payload["editor_queues"][0]["preview_actions"][1]["tool"], "create_material")
            self.assertIn("asset_path", payload["editor_queues"][0]["preview_actions"][1]["argument_keys"])
            self.assertEqual(payload["generated_asset_lifecycles"][0]["asset_count"], 2)
            self.assertEqual(payload["generated_asset_lifecycles"][0]["animation_asset_count"], 1)
            self.assertEqual(payload["generated_asset_lifecycles"][0]["animation_pending_count"], 1)
            self.assertEqual(payload["generated_asset_lifecycles"][0]["preview_assets"][0]["name"], "SM_ObjectiveBeacon")
            self.assertTrue(payload["generated_asset_lifecycles"][0]["preview_assets"][0]["has_placeholder"])
            self.assertEqual(
                payload["generated_asset_lifecycles"][0]["preview_assets"][0]["placeholder_asset_path"],
                "/Game/Generated/Placeholders/PH_ObjectiveBeacon",
            )
            self.assertEqual(payload["generated_asset_lifecycles"][0]["preview_assets"][1]["task_id"], "tsk_enemy_scout")
            self.assertEqual(payload["generated_asset_lifecycles"][0]["preview_assets"][1]["download_tool"], "gen_tripo_download_result")
            self.assertEqual(payload["generated_asset_lifecycles"][0]["preview_animation_assets"][0]["provider"], "uthana")
            self.assertEqual(payload["generated_asset_lifecycles"][0]["preview_animation_assets"][0]["submit_tool"], "gen_uthana_text_to_motion")
            self.assertEqual(payload["generated_asset_lifecycles"][0]["preview_animation_assets"][0]["target_skeleton"], "UE5 Manny")
            self.assertEqual(
                payload["generated_asset_lifecycles"][0]["preview_animation_assets"][0]["quality_proof_contract_schema"],
                "unreal_mcp_generated_animation_quality_proof_contract.v1",
            )
            self.assertIn(
                "animgraph_or_state_machine_reference",
                payload["generated_asset_lifecycles"][0]["preview_animation_assets"][0]["quality_proof_required_preview"],
            )
            self.assertEqual(payload["generated_asset_lifecycles"][0]["blocked_or_pending_count"], 1)
            self.assertIn("generated_assets", {card["id"] for card in payload["cards"]})
            generated_assets_card = next(card for card in payload["cards"] if card["id"] == "generated_assets")
            self.assertEqual(generated_assets_card["details"]["asset_count"], 2)
            self.assertEqual(generated_assets_card["details"]["animation_asset_count"], 1)
            self.assertEqual(generated_assets_card["details"]["animation_pending_count"], 1)
            self.assertEqual(generated_assets_card["details"]["unsupported_provider_task_count"], 0)
            self.assertEqual(payload["generated_asset_quality_gate"]["schema"], "unreal_mcp_chat_generated_asset_quality_gate.v1")
            self.assertEqual(payload["generated_asset_quality_gate"]["state"], "blocked")
            self.assertEqual(payload["generated_asset_quality_gate"]["asset_count"], 2)
            self.assertEqual(payload["generated_asset_quality_gate"]["provider_pending_count"], 1)
            self.assertEqual(payload["generated_asset_quality_gate"]["import_pending_count"], 1)
            self.assertEqual(payload["generated_asset_quality_gate"]["placeholder_count"], 1)
            self.assertEqual(payload["generated_asset_quality_gate"]["items"][0]["state"], "provider_pending")
            self.assertIn("viewport", " ".join(payload["generated_asset_quality_gate"]["items"][0]["quality_gate_preview"]).lower())
            self.assertEqual(
                payload["generated_asset_quality_gate"]["items"][0]["quality_proof_contract_schema"],
                "unreal_mcp_generated_asset_quality_proof_contract.v1",
            )
            self.assertIn("material_slot_count", payload["generated_asset_quality_gate"]["items"][0]["quality_proof_required_preview"])
            self.assertEqual(payload["generated_asset_quality_gate"]["items"][1]["state"], "import_pending")
            self.assertIn("generated_asset_quality_gate", {card["id"] for card in payload["cards"]})
            self.assertEqual(payload["work_order_template"]["template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(payload["work_order_template"]["operation_count"], 2)
            self.assertEqual(payload["hud_summary"]["schema"], "unreal_mcp_chat_cockpit_hud_summary.v1")
            self.assertEqual(payload["hud_summary"]["visible_card_count"], 6)
            self.assertEqual(payload["hud_summary"]["max_visible_cards"], 6)
            self.assertLessEqual(
                len(payload["hud_summary"]["compact_cards"]),
                payload["hud_summary"]["max_visible_cards"],
            )
            self.assertEqual(payload["hud_summary"]["state"], "blocked")
            self.assertEqual(payload["hud_summary"]["selected_session"], "ide-companion")
            self.assertIn("unreal_bridge_reachable", payload["hud_summary"]["primary_blocker_preview"])
            self.assertGreaterEqual(payload["hud_summary"]["primary_blocker_overflow_count"], 0)
            self.assertEqual(payload["hud_summary"]["feature_template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(payload["hud_summary"]["next_editor_operation_id"], "enemy_patrol_chase_attack_01")
            self.assertIn("Blackboard keys TargetActor", payload["hud_summary"]["next_editor_operation_summary"])
            self.assertEqual(payload["hud_summary"]["generated_animation_provider"], "uthana")
            self.assertEqual(payload["hud_summary"]["generated_animation_target_name"], "A_EnemyScout_PatrolWalk")
            self.assertEqual(payload["hud_summary"]["generated_animation_next_safe_action_id"], "resolve_uthana_usage_gates")
            self.assertEqual(payload["hud_summary"]["generated_animation_next_safe_tool"], "gen_compile_ide_companion_readiness")
            self.assertEqual(
                payload["hud_summary"]["generated_animation_usage_next_operator_handoff_id"],
                "record_masked_uthana_allowance_evidence",
            )
            self.assertEqual(
                payload["hud_summary"]["generated_animation_usage_receipt_path"],
                "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
            )
            self.assertEqual(payload["hud_summary"]["next_operator_handoff_id"], "record_dirty_target_evidence")
            self.assertEqual(payload["hud_summary"]["next_operator_handoff_command_kind"], "local_receipt")
            self.assertIn("write_dirty_promotion_review.py", payload["hud_summary"]["next_operator_handoff_command"])
            self.assertEqual(payload["hud_summary"]["next_operator_handoff_safety_label"], "local evidence only")
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_records_evidence_only"])
            self.assertFalse(payload["hud_summary"]["next_operator_handoff_requires_bridge"])
            self.assertFalse(payload["hud_summary"]["next_operator_handoff_requires_spend"])
            self.assertFalse(payload["hud_summary"]["next_operator_handoff_requires_human_approval"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_provider_call"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_spend"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_task_submission"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_download"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_import"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_stage"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_commit"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_branch_or_merge"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_editor_mutation"])
            self.assertTrue(payload["hud_summary"]["next_operator_handoff_no_git_mutation"])
            next_step_card = next(card for card in payload["hud_summary"]["compact_cards"] if card["id"] == "next_safe_step")
            self.assertEqual(next_step_card["next_operator_handoff_id"], "record_dirty_target_evidence")
            self.assertIn("Record evidence", next_step_card["primary"])
            self.assertEqual(next_step_card["secondary"], "local evidence only")
            generation_card = next(card for card in payload["hud_summary"]["compact_cards"] if card["id"] == "generation")
            self.assertEqual(generation_card["animation_provider"], "uthana")
            self.assertEqual(generation_card["animation_target_name"], "A_EnemyScout_PatrolWalk")
            self.assertEqual(generation_card["animation_next_safe_action_id"], "resolve_uthana_usage_gates")
            self.assertEqual(
                generation_card["animation_usage_next_operator_handoff_id"],
                "record_masked_uthana_allowance_evidence",
            )
            self.assertEqual(generation_card["primary"], "2 asset(s), 1 animation(s)")
            self.assertEqual(generation_card["secondary"], "uthana: A_EnemyScout_PatrolWalk -> resolve_uthana_usage_gates")
            self.assertEqual(payload["hud_summary"]["blueprint_mutation_evidence_state"], "missing_evidence")
            self.assertEqual(payload["hud_summary"]["blueprint_mutation_evidence_summary"], "0/3 recorded")
            self.assertEqual(payload["hud_summary"]["blueprint_mutation_evidence_recorded_count"], 0)
            self.assertEqual(payload["hud_summary"]["blueprint_mutation_evidence_missing_count"], 3)
            self.assertEqual(
                payload["hud_summary"]["blueprint_mutation_missing_gate_preview"],
                ["blueprint_pre_read_evidence", "blueprint_compile_plan", "blueprint_readback_plan"],
            )
            self.assertEqual(payload["hud_summary"]["blueprint_mutation_next_gate"], "blueprint_pre_read_evidence")
            self.assertEqual(
                payload["hud_summary"]["blueprint_mutation_next_operator_handoff_id"],
                "record_blueprint_pre_read_evidence",
            )
            self.assertEqual(
                payload["hud_summary"]["blueprint_mutation_next_operator_handoff_label"],
                "Record Blueprint pre-read evidence",
            )
            self.assertEqual(
                payload["hud_summary"]["blueprint_mutation_evidence_receipt_path"],
                "Saved\\BlueprintMutationEvidence\\last_review_receipt.json",
            )
            self.assertEqual(payload["hud_summary"]["blueprint_mutation_safety_label"], "blueprint evidence only")
            self.assertFalse(payload["hud_summary"]["blueprint_mutation_pre_read_evidence_recorded"])
            self.assertFalse(payload["hud_summary"]["blueprint_mutation_compile_plan_recorded"])
            self.assertFalse(payload["hud_summary"]["blueprint_mutation_readback_plan_recorded"])
            self.assertTrue(payload["hud_summary"]["blueprint_mutation_no_blueprint_mutation"])
            self.assertTrue(payload["hud_summary"]["blueprint_mutation_no_editor_mutation"])
            self.assertTrue(payload["hud_summary"]["blueprint_mutation_no_compile"])
            self.assertTrue(payload["hud_summary"]["blueprint_mutation_no_save"])
            self.assertTrue(payload["hud_summary"]["blueprint_mutation_no_pie"])
            self.assertFalse(payload["hud_summary"]["network_required"])
            self.assertFalse(payload["hud_summary"]["unreal_editor_required"])
            self.assertFalse(payload["hud_summary"]["spend_required"])
            self.assertIn("drill-down", " ".join(payload["hud_summary"]["layout_policy"]))
            self.assertIn("safety_label", " ".join(payload["hud_summary"]["layout_policy"]))
            self.assertIn("Blueprint mutation evidence", " ".join(payload["hud_summary"]["layout_policy"]))

            self.assertEqual(payload["work_order_template"]["editor_operation_count"], 2)
            self.assertEqual(payload["work_order_template"]["bridge_required_operation_count"], 2)
            self.assertEqual(payload["work_order_template"]["compile_after_operation_count"], 2)
            self.assertEqual(payload["work_order_template"]["readback_after_operation_count"], 2)
            self.assertEqual(payload["work_order_template"]["operation_proof_contract_count"], 2)
            self.assertIn("blueprint_compile_report", payload["work_order_template"]["operation_proof_required_after_preview"])
            self.assertIn("ide_companion_ledger_event", payload["work_order_template"]["operation_proof_required_after_preview"])
            self.assertEqual(payload["work_order_template"]["completion_proof_gate_count"], 3)
            self.assertEqual(payload["work_order_template"]["completion_required_evidence_count"], 6)
            self.assertIn("ai_blackboard_behavior_tree", payload["work_order_template"]["editor_operation_type_preview"])
            self.assertIn("bt_get_info", payload["work_order_template"]["editor_operation_tool_preview"])
            self.assertIn("enemy_patrol_chase_attack_01", " ".join(payload["work_order_template"]["editor_operation_preview"]))
            self.assertEqual(payload["work_order_template"]["next_editor_operation_id"], "enemy_patrol_chase_attack_01")
            self.assertEqual(payload["work_order_template"]["next_editor_operation_type"], "ai_blackboard_behavior_tree")
            self.assertIn("Blackboard keys TargetActor", payload["work_order_template"]["next_editor_operation_summary"])
            self.assertIn("set_behavior_tree_blackboard", payload["work_order_template"]["next_editor_operation_tool_preview"])
            self.assertTrue(payload["work_order_template"]["next_editor_operation_requires_bridge"])
            self.assertTrue(payload["work_order_template"]["next_editor_operation_requires_compile_after"])
            self.assertTrue(payload["work_order_template"]["next_editor_operation_requires_readback_after"])
            self.assertIn("unreal_bridge_reachable", payload["work_order_template"]["next_editor_operation_required_before_preview"])
            self.assertIn("graph_or_component_readback", payload["work_order_template"]["next_editor_operation_required_after_preview"])
            self.assertIn("compile report missing or failed", payload["work_order_template"]["next_editor_operation_stop_if_missing_preview"])
            self.assertIn("pie_validation_passed", json.dumps(payload["work_order_template"]["completion_proof_gate_preview"]))
            self.assertEqual(payload["work_order_template"]["repair_instruction_count"], 1)
            self.assertEqual(
                payload["resume_context"]["matching_ide_companion_ledger"]["work_order_template"]["display_name"],
                "Enemy Patrol/Chase/Attack",
            )
            self.assertIn("feature_work_order", {card["id"] for card in payload["cards"]})
            feature_card = next(card for card in payload["cards"] if card["id"] == "feature_work_order")
            self.assertEqual(feature_card["details"]["editor_operation_count"], 2)
            self.assertIn("bp_add_node", feature_card["details"]["editor_operation_tool_preview"])
            self.assertEqual(feature_card["details"]["next_editor_operation_id"], "enemy_patrol_chase_attack_01")
            self.assertIn("set_behavior_tree_blackboard", feature_card["details"]["next_editor_operation_tool_preview"])
            self.assertTrue(feature_card["details"]["next_editor_operation_requires_bridge"])
            self.assertTrue(feature_card["details"]["next_editor_operation_requires_compile_after"])
            self.assertTrue(feature_card["details"]["next_editor_operation_requires_readback_after"])
            self.assertEqual(feature_card["details"]["completion_proof_gate_count"], 3)
            self.assertIn("ledger_evidence_recorded", json.dumps(feature_card["details"]["completion_proof_gate_preview"]))
            self.assertEqual(payload["runtime_verification"]["schema"], "unreal_mcp_chat_runtime_verification_checklist.v1")
            self.assertTrue(payload["runtime_verification"]["available"])
            self.assertEqual(payload["runtime_verification"]["state"], "blocked")
            self.assertTrue(payload["runtime_verification"]["bridge_blocked"])
            self.assertEqual(payload["runtime_verification"]["pie_validation_count"], 1)
            self.assertEqual(payload["runtime_verification"]["evidence_requirement_count"], 2)
            self.assertEqual(payload["runtime_verification"]["items"][0]["kind"], "pie_validation")
            self.assertEqual(payload["runtime_verification"]["items"][0]["state"], "blocked")
            self.assertEqual(payload["runtime_verification"]["items"][0]["label"], "Enemy patrols when no target is known")
            self.assertIn("runtime_verification", {card["id"] for card in payload["cards"]})
            self.assertEqual(payload["runtime_review"]["schema"], "unreal_mcp_chat_runtime_review.v1")
            self.assertEqual(payload["runtime_review"]["state"], "blocked")
            self.assertFalse(payload["runtime_review"]["can_verify_now"])
            self.assertTrue(payload["runtime_review"]["bridge_blocked"])
            self.assertEqual(payload["runtime_review"]["target_phase"], "editor_implementation")
            self.assertEqual(payload["runtime_review"]["pie_validation_count"], 1)
            self.assertEqual(payload["runtime_review"]["compile_check_count"], 1)
            self.assertEqual(payload["runtime_review"]["evidence_requirement_count"], 2)
            self.assertEqual(payload["runtime_review"]["blocked_item_count"], 1)
            self.assertEqual(payload["runtime_review"]["pending_item_count"], 2)
            self.assertEqual(payload["runtime_review"]["recorded_item_count"], 0)
            self.assertIn("Confirm compile and graph/component readback evidence", payload["runtime_review"]["policy_preview"][0])
            self.assertTrue(payload["runtime_review"]["stop_after_runtime_probe"])
            self.assertIn("runtime_review", {card["id"] for card in payload["cards"]})
            self.assertEqual(payload["repair_loop"]["schema"], "unreal_mcp_chat_repair_loop_summary.v1")
            self.assertTrue(payload["repair_loop"]["available"])
            self.assertEqual(payload["repair_loop"]["state"], "blocked")
            self.assertTrue(payload["repair_loop"]["bridge_blocked"])
            self.assertEqual(payload["repair_loop"]["repair_instruction_count"], 1)
            self.assertEqual(payload["repair_loop"]["recommended_tool"], "skill_compile_ide_companion_work_order")
            self.assertIn("Blueprint compile fails", payload["repair_loop"]["items"][0]["label"])
            self.assertIn("repair_loop", {card["id"] for card in payload["cards"]})
            self.assertEqual(payload["repair_review"]["schema"], "unreal_mcp_chat_repair_review.v1")
            self.assertEqual(payload["repair_review"]["state"], "blocked")
            self.assertTrue(payload["repair_review"]["bridge_blocked"])
            self.assertEqual(payload["repair_review"]["target_repair"]["id"], "repair_hint_1")
            self.assertIn("Blueprint compile fails", payload["repair_review"]["target_repair"]["label"])
            self.assertEqual(payload["repair_review"]["failure_signal_count"], 4)
            self.assertEqual(payload["repair_review"]["blocked_count"], 3)
            self.assertEqual(payload["repair_review"]["needs_repair_count"], 1)
            self.assertEqual(payload["repair_review"]["repair_instruction_count"], 1)
            self.assertIn("Compile a scoped repair work order", payload["repair_review"]["policy_preview"][0])
            self.assertTrue(payload["repair_review"]["stop_after_repair_attempt"])
            self.assertIn("repair_review", {card["id"] for card in payload["cards"]})
            self.assertEqual(payload["evidence_recording"]["schema"], "unreal_mcp_chat_evidence_recording_checklist.v1")
            self.assertEqual(payload["evidence_recording"]["record_tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(payload["evidence_recording"]["item_count"], 17)
            self.assertEqual(payload["evidence_recording"]["pending_count"], 14)
            self.assertEqual(payload["evidence_recording"]["blocked_count"], 3)
            evidence_items = {item["id"]: item for item in payload["evidence_recording"]["items"]}
            self.assertEqual(evidence_items["record_readiness_repair_queue"]["source"], "readiness_repair_queue")
            self.assertEqual(evidence_items["record_readiness_repair_queue"]["evidence_type"], "readiness_repair_queue")
            self.assertEqual(evidence_items["record_readiness_repair_queue"]["state"], "pending")
            self.assertFalse(evidence_items["record_readiness_repair_queue"]["requires_bridge"])
            self.assertIn("verify_unreal_bridge_reachability", evidence_items["record_readiness_repair_queue"]["required_artifacts"])
            self.assertIn("unreal_bridge_reachable", evidence_items["record_readiness_repair_queue"]["required_artifacts"])
            repair_queue_metadata = evidence_items["record_readiness_repair_queue"]["metadata"]
            self.assertEqual(repair_queue_metadata["blocking_gate_count"], 1)
            self.assertIn("unreal_bridge_reachable", repair_queue_metadata["blocking_gate_preview"])
            self.assertEqual(repair_queue_metadata["next_gate"], "unreal_bridge_reachable")
            self.assertEqual(repair_queue_metadata["next_policy_area"], "editor_mutation")
            self.assertEqual(repair_queue_metadata["next_recommended_tool"], "scripts/bridge_ping.py")
            self.assertIn("successful_bridge_ping", repair_queue_metadata["next_evidence_required_preview"])
            self.assertTrue(repair_queue_metadata["next_requires_manual_operator"])
            self.assertTrue(repair_queue_metadata["next_requires_bridge"])
            self.assertFalse(repair_queue_metadata["next_requires_network"])
            self.assertFalse(repair_queue_metadata["next_requires_spend"])
            self.assertTrue(repair_queue_metadata["next_requires_unreal_editor"])
            self.assertTrue(repair_queue_metadata["no_auto_execute"])
            self.assertTrue(repair_queue_metadata["no_secret_echo"])
            self.assertEqual(evidence_items["record_readiness_policy"]["source"], "readiness_policy")
            self.assertEqual(evidence_items["record_readiness_policy"]["evidence_type"], "readiness_policy")
            self.assertEqual(evidence_items["record_readiness_policy"]["state"], "pending")
            self.assertFalse(evidence_items["record_readiness_policy"]["requires_bridge"])
            self.assertIn("wallet_evidence_recorded", evidence_items["record_readiness_policy"]["required_artifacts"])
            self.assertIn("spend_confirmation_recorded", evidence_items["record_readiness_policy"]["required_artifacts"])
            self.assertIn("blueprint_pre_read_evidence", evidence_items["record_readiness_policy"]["required_artifacts"])
            self.assertIn(
                "evidence_required:no_mutation_receipt_snapshot_digest_match",
                evidence_items["record_readiness_policy"]["required_artifacts"],
            )
            self.assertIn(
                "evidence_required:no_mutation_receipt_scope_git_tracked_worktree",
                evidence_items["record_readiness_policy"]["required_artifacts"],
            )
            readiness_policy_metadata = evidence_items["record_readiness_policy"]["metadata"]
            self.assertEqual(readiness_policy_metadata["schema"], "unreal_mcp_chat_readiness_policy_summary.v1")
            self.assertGreaterEqual(readiness_policy_metadata["blocked_policy_count"], 1)
            self.assertIn("editor_mutation", readiness_policy_metadata["blocked_policy_preview"])
            self.assertFalse(readiness_policy_metadata["editor_mutation_allowed"])
            self.assertGreaterEqual(readiness_policy_metadata["editor_mutation_missing_gate_count"], 1)
            self.assertIn("unreal_bridge_reachable", readiness_policy_metadata["editor_mutation_missing_gate_preview"])
            self.assertGreaterEqual(readiness_policy_metadata["editor_mutation_evidence_required_count"], 1)
            self.assertIn("successful_bridge_ping", readiness_policy_metadata["editor_mutation_evidence_required_preview"])
            self.assertFalse(readiness_policy_metadata["paid_generation_allowed"])
            self.assertGreaterEqual(readiness_policy_metadata["paid_generation_missing_gate_count"], 2)
            self.assertIn("wallet_evidence_recorded", readiness_policy_metadata["paid_generation_missing_gate_preview"])
            self.assertIn("spend_confirmation_recorded", readiness_policy_metadata["paid_generation_missing_gate_preview"])
            self.assertGreaterEqual(readiness_policy_metadata["paid_generation_evidence_required_count"], 3)
            self.assertIn("provider_key_presence", readiness_policy_metadata["paid_generation_evidence_required_preview"])
            self.assertIn("wallet_or_credit_evidence", readiness_policy_metadata["paid_generation_evidence_required_preview"])
            self.assertIn("explicit_spend_confirmation", readiness_policy_metadata["paid_generation_evidence_required_preview"])
            self.assertFalse(readiness_policy_metadata["paid_animation_generation_allowed"])
            self.assertGreaterEqual(readiness_policy_metadata["paid_animation_generation_missing_gate_count"], 2)
            self.assertIn("wallet_evidence_recorded", readiness_policy_metadata["paid_animation_generation_missing_gate_preview"])
            self.assertIn("spend_confirmation_recorded", readiness_policy_metadata["paid_animation_generation_missing_gate_preview"])
            self.assertGreaterEqual(readiness_policy_metadata["paid_animation_generation_evidence_required_count"], 3)
            self.assertIn(
                "animation_provider_key_presence",
                readiness_policy_metadata["paid_animation_generation_evidence_required_preview"],
            )
            self.assertIn(
                "wallet_or_credit_evidence",
                readiness_policy_metadata["paid_animation_generation_evidence_required_preview"],
            )
            self.assertIn(
                "explicit_spend_confirmation",
                readiness_policy_metadata["paid_animation_generation_evidence_required_preview"],
            )
            self.assertFalse(readiness_policy_metadata["blueprint_mutation_allowed"])
            self.assertGreaterEqual(readiness_policy_metadata["blueprint_mutation_missing_gate_count"], 1)
            self.assertIn("blueprint_pre_read_evidence", readiness_policy_metadata["blueprint_mutation_missing_gate_preview"])
            self.assertIn("blueprint_readback_plan", readiness_policy_metadata["blueprint_mutation_missing_gate_preview"])
            self.assertGreaterEqual(readiness_policy_metadata["blueprint_mutation_evidence_required_count"], 3)
            self.assertIn("blueprint_pre_read", readiness_policy_metadata["blueprint_mutation_evidence_required_preview"])
            self.assertIn("compile_check_after_mutation", readiness_policy_metadata["blueprint_mutation_evidence_required_preview"])
            self.assertIn("graph_or_component_readback_after_mutation", readiness_policy_metadata["blueprint_mutation_evidence_required_preview"])
            self.assertIsInstance(readiness_policy_metadata["wip_promotion_allowed"], bool)
            self.assertGreaterEqual(readiness_policy_metadata["wip_promotion_missing_gate_count"], 0)
            self.assertIn(
                "no_mutation_receipt_snapshot_digest_match",
                readiness_policy_metadata["wip_promotion_evidence_required_preview"],
            )
            self.assertIn(
                "no_mutation_receipt_scope_git_tracked_worktree",
                readiness_policy_metadata["wip_promotion_evidence_required_preview"],
            )
            self.assertTrue(readiness_policy_metadata["no_editor_mutation"])
            self.assertTrue(readiness_policy_metadata["no_provider_call"])
            self.assertTrue(readiness_policy_metadata["no_git_mutation"])
            self.assertEqual(evidence_items["record_platform_stability_review"]["source"], "platform_preflight")
            self.assertEqual(evidence_items["record_platform_stability_review"]["evidence_type"], "platform_stability_review")
            self.assertEqual(evidence_items["record_platform_stability_review"]["state"], "pending")
            self.assertFalse(evidence_items["record_platform_stability_review"]["requires_bridge"])
            self.assertIn(
                "receipt:Saved\\PlatformStabilityReview\\last_review_receipt.json",
                evidence_items["record_platform_stability_review"]["required_artifacts"],
            )
            self.assertIn("ready_for_platform_stability:True", evidence_items["record_platform_stability_review"]["required_artifacts"])
            self.assertIn("paid_provider_smoke_contract:True", evidence_items["record_platform_stability_review"]["required_artifacts"])
            self.assertIn(
                "blueprint_operator_command_handoff:record_blueprint_pre_read_evidence",
                evidence_items["record_platform_stability_review"]["required_artifacts"],
            )
            self.assertIn(
                "blueprint_operator_command_handoff:record_blueprint_compile_plan",
                evidence_items["record_platform_stability_review"]["required_artifacts"],
            )
            self.assertTrue(any(
                artifact in {"blueprint_evidence_receipt:missing", "blueprint_evidence_receipt:missing_evidence"}
                for artifact in evidence_items["record_platform_stability_review"]["required_artifacts"]
            ))
            self.assertIn("blueprint_pre_read_recorded:False", evidence_items["record_platform_stability_review"]["required_artifacts"])
            self.assertIn("blueprint_compile_plan_recorded:False", evidence_items["record_platform_stability_review"]["required_artifacts"])
            self.assertIn("blueprint_readback_plan_recorded:False", evidence_items["record_platform_stability_review"]["required_artifacts"])
            self.assertIn("paid_provider_smoke_manual_spend:False", evidence_items["record_platform_stability_review"]["required_artifacts"])
            self.assertIn("no_mutation_snapshot_match:True", evidence_items["record_platform_stability_review"]["required_artifacts"])
            self.assertIn("no_mutation_snapshot_scope:git_tracked_worktree", evidence_items["record_platform_stability_review"]["required_artifacts"])
            self.assertTrue(any(
                artifact.startswith("no_mutation_tracked:")
                for artifact in evidence_items["record_platform_stability_review"]["required_artifacts"]
            ))
            self.assertTrue(any(
                artifact.startswith("no_mutation_snapshot_hash:sha256(")
                for artifact in evidence_items["record_platform_stability_review"]["required_artifacts"]
            ))
            platform_metadata = evidence_items["record_platform_stability_review"]["metadata"]
            self.assertEqual(platform_metadata["schema"], "unreal_mcp_platform_stability_review_receipt.v1")
            self.assertEqual(platform_metadata["required_command"], "python scripts\\write_platform_stability_review.py")
            self.assertTrue(platform_metadata["ready_for_platform_stability"])
            self.assertTrue(platform_metadata["paid_provider_smoke_contract_ok"])
            self.assertFalse(platform_metadata["paid_provider_smoke_manual_spend_required"])
            self.assertTrue(platform_metadata["paid_provider_smoke_no_task_submission"])
            self.assertTrue(platform_metadata["paid_provider_smoke_no_download"])
            self.assertTrue(platform_metadata["paid_provider_smoke_no_import"])
            self.assertIn("RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE", platform_metadata["paid_provider_smoke_required_env_vars"])
            self.assertIn("gen_uthana_get_account", platform_metadata["paid_provider_smoke_no_spend_tools"])
            self.assertIn("dirty_promotion_review_receipt_current", platform_metadata)
            self.assertIn("dirty_promotion_review_receipt_stale", platform_metadata)
            self.assertIn("dirty_promotion_review_receipt_signature_match", platform_metadata)
            self.assertEqual(platform_metadata["blueprint_mutation_evidence_receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
            self.assertEqual(platform_metadata["blueprint_mutation_evidence_required_command"], "python scripts\\write_blueprint_mutation_evidence_review.py")
            self.assertFalse(platform_metadata["blueprint_mutation_pre_read_evidence_recorded"])
            self.assertFalse(platform_metadata["blueprint_mutation_compile_plan_recorded"])
            self.assertFalse(platform_metadata["blueprint_mutation_readback_plan_recorded"])
            self.assertTrue(platform_metadata["blueprint_mutation_evidence_no_blueprint_mutation"])
            self.assertGreaterEqual(platform_metadata["tool_count"], 1)
            self.assertEqual(platform_metadata["tool_count"], platform_metadata["recorded_tool_count"])
            self.assertGreaterEqual(platform_metadata["partial_tool_count"], 0)
            self.assertGreaterEqual(platform_metadata["blocking_gate_count"], 1)
            self.assertIn("blueprint_pre_read_evidence", platform_metadata["blocking_gate_preview"])
            self.assertIn("blueprint_compile_plan", platform_metadata["blocking_gate_preview"])
            self.assertGreaterEqual(platform_metadata["readiness_repair_action_count"], 0)
            self.assertIsInstance(platform_metadata["readiness_repair_next_requires_bridge"], bool)
            self.assertIsInstance(platform_metadata["readiness_repair_next_requires_network"], bool)
            self.assertIsInstance(platform_metadata["readiness_repair_next_requires_spend"], bool)
            if platform_metadata["readiness_repair_action_count"]:
                self.assertIn("readiness_repair_recommended_next", platform_metadata)
                self.assertIn("readiness_repair_next_gate", platform_metadata)
                self.assertIn("readiness_repair_next_tool", platform_metadata)
                self.assertTrue(platform_metadata["readiness_repair_action_preview"])
                self.assertIn("gate", platform_metadata["readiness_repair_action_preview"][0])
            self.assertIn("dirty_target_review_group", platform_metadata)
            self.assertIn("dirty_target_review_status", platform_metadata)
            self.assertIn("dirty_target_review_recorded_evidence_count", platform_metadata)
            self.assertIn("dirty_target_review_human_approval_recorded", platform_metadata)
            self.assertIn("dirty_target_review_merge_policy", platform_metadata)
            self.assertIn("dirty_target_review_previous_evidence_merged", platform_metadata)
            self.assertIn("dirty_target_review_reset_evidence", platform_metadata)
            self.assertIn("dirty_target_review_missing_evidence_preview", platform_metadata)
            self.assertIn("dirty_target_review_focused_test_command_preview", platform_metadata)
            if platform_metadata["dirty_target_review_group"]:
                self.assertGreaterEqual(platform_metadata["dirty_target_review_missing_evidence_count"], 1)
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    platform_metadata["dirty_target_review_missing_evidence_preview"],
                )
                self.assertFalse(platform_metadata["dirty_target_review_promotion_allowed_after_receipt"])
            self.assertTrue(platform_metadata["no_mutation_test_ok"])
            self.assertEqual(platform_metadata["no_mutation_test_status"], "success")
            self.assertEqual(platform_metadata["no_mutation_test_mutation_count"], 0)
            self.assertEqual(platform_metadata["no_mutation_test_exit_code"], 0)
            self.assertGreater(platform_metadata["no_mutation_test_tracked_file_count"], 0)
            self.assertTrue(platform_metadata["no_mutation_test_snapshot_digest_match"])
            self.assertEqual(platform_metadata["no_mutation_test_snapshot_scope"], "git_tracked_worktree")
            self.assertTrue(platform_metadata["no_mutation_test_snapshot_hash_algorithm"].startswith("sha256("))
            self.assertTrue(platform_metadata["no_provider_call"])
            self.assertTrue(platform_metadata["no_editor_mutation"])
            self.assertTrue(platform_metadata["no_git_mutation"])
            self.assertEqual(evidence_items["record_dirty_promotion_review"]["source"], "dirty_promotion_contract")
            self.assertEqual(evidence_items["record_dirty_promotion_review"]["evidence_type"], "dirty_promotion_review")
            self.assertEqual(evidence_items["record_dirty_promotion_review"]["state"], "pending")
            self.assertFalse(evidence_items["record_dirty_promotion_review"]["requires_bridge"])
            self.assertIn(
                "receipt:Saved\\DirtyPromotionReview\\last_review_receipt.json",
                evidence_items["record_dirty_promotion_review"]["required_artifacts"],
            )
            self.assertIn("wip_missing:dirty_state_grouped_for_promotion", evidence_items["record_dirty_promotion_review"]["required_artifacts"])
            dirty_metadata = evidence_items["record_dirty_promotion_review"]["metadata"]
            self.assertEqual(dirty_metadata["schema"], "unreal_mcp_dirty_promotion_contract.v1")
            self.assertEqual(dirty_metadata["required_command"], "python scripts\\write_dirty_promotion_review.py")
            self.assertIn("receipt_current", dirty_metadata)
            self.assertIn("receipt_stale", dirty_metadata)
            self.assertIn("receipt_dirty_signature_match", dirty_metadata)
            self.assertEqual(
                dirty_metadata["dirty_signature_algorithm"],
                "sha256(git_status_porcelain_v1_sorted_lines)",
            )
            self.assertGreaterEqual(dirty_metadata["dirty_signature_entry_count"], 0)
            self.assertTrue(dirty_metadata["no_git_mutation"])
            self.assertTrue(dirty_metadata["no_stage"])
            self.assertTrue(dirty_metadata["no_commit"])
            self.assertTrue(dirty_metadata["no_clean"])
            self.assertTrue(dirty_metadata["no_branch_or_merge"])
            self.assertTrue(dirty_metadata["no_provider_call"])
            self.assertTrue(dirty_metadata["no_editor_mutation"])
            self.assertIn("evidence_review_matrix_count", dirty_metadata)
            self.assertIn("evidence_unresolved_count", dirty_metadata)
            self.assertIn("receipt records the review target only", dirty_metadata["evidence_review_policy"])
            self.assertIn("target_review_group", dirty_metadata)
            self.assertIn("target_review_status", dirty_metadata)
            self.assertIn("target_review_recorded_evidence_count", dirty_metadata)
            self.assertIn("target_review_human_approval_recorded", dirty_metadata)
            self.assertIn("target_review_merge_policy", dirty_metadata)
            self.assertIn("target_review_previous_evidence_merged", dirty_metadata)
            self.assertIn("target_review_reset_evidence", dirty_metadata)
            self.assertEqual(
                dirty_metadata["target_review_merge_policy"],
                "preserve_existing_evidence_when_dirty_signature_and_target_match",
            )
            self.assertIn("target_review_missing_evidence_preview", dirty_metadata)
            self.assertIn("target_review_required_evidence_preview", dirty_metadata)
            self.assertIn("target_review_decision_prompt_preview", dirty_metadata)
            self.assertIn("target_review_receipt_command_template", dirty_metadata)
            self.assertIn("target_review_approval_receipt_command_template", dirty_metadata)
            self.assertIn("target_review_receipt_command_policy", dirty_metadata)
            self.assertIn("target_review_operator_command_handoff", dirty_metadata)
            self.assertEqual(len(dirty_metadata["target_review_operator_command_handoff"]), 2)
            self.assertEqual(dirty_metadata["target_review_operator_command_handoff"][0]["id"], "record_dirty_target_evidence")
            self.assertFalse(dirty_metadata["target_review_operator_command_handoff"][0]["approval_flag_included"])
            self.assertTrue(dirty_metadata["target_review_operator_command_handoff"][0]["no_git_mutation"])
            self.assertTrue(dirty_metadata["target_review_operator_command_handoff"][1]["approval_flag_included"])
            self.assertIn("target_review_focused_test_command_handoff", dirty_metadata)
            self.assertGreaterEqual(len(dirty_metadata["target_review_focused_test_command_handoff"]), 1)
            self.assertEqual(dirty_metadata["target_review_focused_test_command_handoff"][0]["command_kind"], "local_validation")
            self.assertTrue(dirty_metadata["target_review_focused_test_command_handoff"][0]["no_git_mutation"])
            self.assertIn("target_review_pending_human_approval_only", dirty_metadata)
            self.assertIn("target_review_human_approval_gate", dirty_metadata)
            self.assertIn("target_review_human_approval_command_handoff", dirty_metadata)
            self.assertIn("--target-owner-or-source", dirty_metadata["target_review_receipt_command_template"])
            self.assertNotIn("--target-human-approval-recorded", dirty_metadata["target_review_receipt_command_template"])
            self.assertIn("--target-human-approval-recorded", dirty_metadata["target_review_approval_receipt_command_template"])
            self.assertIn("explicit human approval", dirty_metadata["target_review_receipt_command_policy"])
            self.assertIn("target_review_focused_test_command_preview", dirty_metadata)
            if platform_metadata["dirty_target_review_group"]:
                self.assertEqual(
                    dirty_metadata["target_review_group"],
                    platform_metadata["dirty_target_review_group"],
                )
            self.assertIn("target_review_source", dirty_metadata)
            self.assertIn(dirty_metadata["target_review_source"], {"current_review_receipt", "current_dirty_worktree", ""})
            if dirty_metadata["evidence_review_matrix_preview"]:
                self.assertIn("missing_evidence_count", dirty_metadata["evidence_review_matrix_preview"][0])
                self.assertFalse(dirty_metadata["evidence_review_matrix_preview"][0]["promotion_allowed"])
                self.assertEqual(
                    dirty_metadata["target_review_group"],
                    dirty_metadata["evidence_review_matrix_preview"][0]["group"],
                )
                self.assertGreaterEqual(dirty_metadata["target_review_missing_evidence_count"], 1)
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    dirty_metadata["target_review_missing_evidence_preview"],
                )
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    dirty_metadata["target_review_required_evidence_preview"],
                )
                self.assertTrue(any("owner_or_source" in prompt for prompt in dirty_metadata["target_review_decision_prompt_preview"]))
                self.assertFalse(dirty_metadata["target_review_promotion_allowed_after_receipt"])
            if dirty_metadata["target_review_focused_test_command_count"]:
                self.assertIn("python", " ".join(dirty_metadata["target_review_focused_test_command_preview"]).lower())
            self.assertFalse(dirty_metadata["target_review_promotion_allowed_after_receipt"])
            self.assertIn("one coherent dirty group", dirty_metadata["promotion_batch_policy"])
            self.assertIn("generated/local artifacts", dirty_metadata["artifact_policy"])
            self.assertIn("run_focused_tests_for_each_candidate_batch", dirty_metadata["safe_promotion_next_steps"])
            self.assertEqual(evidence_items["record_provider_config_review"]["source"], "provider_config")
            self.assertEqual(evidence_items["record_provider_config_review"]["evidence_type"], "provider_config_review")
            self.assertEqual(evidence_items["record_provider_config_review"]["state"], "pending")
            self.assertFalse(evidence_items["record_provider_config_review"]["requires_bridge"])
            self.assertIn(
                "receipt:Saved\\ProviderConfigReview\\last_review_receipt.json",
                evidence_items["record_provider_config_review"]["required_artifacts"],
            )
            self.assertIn("provider:tripo", evidence_items["record_provider_config_review"]["required_artifacts"])
            self.assertIn("animation_provider:uthana", evidence_items["record_provider_config_review"]["required_artifacts"])
            provider_config_metadata = evidence_items["record_provider_config_review"]["metadata"]
            self.assertEqual(provider_config_metadata["schema"], "unreal_mcp_provider_config_review_receipt.v1")
            self.assertEqual(provider_config_metadata["required_command"], "python scripts\\write_provider_config_review.py")
            self.assertEqual(
                provider_config_metadata["operator_command_handoff"][0]["id"],
                "write_provider_config_review_receipt",
            )
            self.assertTrue(provider_config_metadata["operator_command_handoff"][0]["no_provider_call"])
            self.assertTrue(provider_config_metadata["operator_command_handoff"][0]["no_editor_mutation"])
            self.assertEqual(provider_config_metadata["save_tool"], "gen_save_provider_config")
            self.assertTrue(provider_config_metadata["masked_status_only"])
            self.assertFalse(provider_config_metadata["raw_key_returned"])
            self.assertTrue(provider_config_metadata["no_raw_key"])
            self.assertTrue(provider_config_metadata["no_provider_call"])
            self.assertTrue(provider_config_metadata["no_wallet_check"])
            self.assertTrue(provider_config_metadata["no_credit_reservation"])
            self.assertTrue(provider_config_metadata["no_spend_confirmation"])
            self.assertNotIn("api_key_masked", json.dumps(evidence_items["record_provider_config_review"]))
            self.assertEqual(evidence_items["record_bridge_ping_receipt"]["source"], "bridge_ping")
            self.assertEqual(evidence_items["record_bridge_ping_receipt"]["evidence_type"], "bridge_ping_receipt")
            self.assertEqual(evidence_items["record_bridge_ping_receipt"]["state"], "pending")
            self.assertFalse(evidence_items["record_bridge_ping_receipt"]["requires_bridge"])
            self.assertIn(
                "receipt:Saved\\BridgePing\\last_ping_receipt.json",
                evidence_items["record_bridge_ping_receipt"]["required_artifacts"],
            )
            self.assertIn("blocking_gate:unreal_bridge_reachable", evidence_items["record_bridge_ping_receipt"]["required_artifacts"])
            bridge_metadata = evidence_items["record_bridge_ping_receipt"]["metadata"]
            self.assertEqual(bridge_metadata["schema"], "unreal_mcp_bridge_ping_receipt.v1")
            self.assertEqual(bridge_metadata["required_command"], "python scripts\\bridge_ping.py")
            self.assertFalse(bridge_metadata["successful_bridge_ping"])
            self.assertFalse(bridge_metadata["editor_mutation_allowed"])
            self.assertTrue(bridge_metadata["no_editor_mutation"])
            self.assertTrue(bridge_metadata["no_pie_run"])
            self.assertTrue(bridge_metadata["stop_before_editor_or_pie"])
            self.assertEqual(evidence_items["record_chat_cockpit_start_receipt"]["source"], "chat_cockpit_repair_contract")
            self.assertEqual(evidence_items["record_chat_cockpit_start_receipt"]["evidence_type"], "chat_cockpit_start_receipt")
            self.assertEqual(evidence_items["record_chat_cockpit_start_receipt"]["state"], "pending")
            self.assertFalse(evidence_items["record_chat_cockpit_start_receipt"]["requires_bridge"])
            self.assertIn(
                "receipt:Saved\\ChatCockpit\\last_start_receipt.json",
                evidence_items["record_chat_cockpit_start_receipt"]["required_artifacts"],
            )
            self.assertIn("chat_history_endpoint_ready", evidence_items["record_chat_cockpit_start_receipt"]["required_artifacts"])
            chat_metadata = evidence_items["record_chat_cockpit_start_receipt"]["metadata"]
            self.assertEqual(chat_metadata["schema"], "unreal_mcp_chat_cockpit_start_receipt.v1")
            self.assertTrue(chat_metadata["chat_ready"])
            self.assertTrue(chat_metadata["no_process_start"])
            self.assertTrue(chat_metadata["no_port_kill"])
            self.assertTrue(chat_metadata["no_editor_mutation"])
            self.assertTrue(chat_metadata["no_provider_call"])
            self.assertTrue(chat_metadata["no_git_mutation"])
            self.assertEqual(evidence_items["record_paid_generation_evidence"]["source"], "provider_spend_context")
            self.assertEqual(evidence_items["record_paid_generation_evidence"]["evidence_type"], "paid_generation_evidence")
            self.assertEqual(evidence_items["record_paid_generation_evidence"]["state"], "pending")
            self.assertFalse(evidence_items["record_paid_generation_evidence"]["requires_bridge"])
            self.assertIn(
                "receipt:Saved\\PaidGenerationEvidence\\last_review_receipt.json",
                evidence_items["record_paid_generation_evidence"]["required_artifacts"],
            )
            self.assertTrue(any(
                artifact in {"receipt_state:missing", "receipt_state:missing_evidence"}
                for artifact in evidence_items["record_paid_generation_evidence"]["required_artifacts"]
            ))
            self.assertIn("wallet_evidence_recorded", evidence_items["record_paid_generation_evidence"]["required_artifacts"])
            self.assertIn("spend_confirmation_recorded", evidence_items["record_paid_generation_evidence"]["required_artifacts"])
            self.assertIn("mesh_wallet_tool:gen_tripo_get_credit_balance", evidence_items["record_paid_generation_evidence"]["required_artifacts"])
            self.assertIn("animation_allowance_tool:gen_uthana_get_account", evidence_items["record_paid_generation_evidence"]["required_artifacts"])
            self.assertTrue(any(
                artifact.startswith("wallet_evidence_step:")
                for artifact in evidence_items["record_paid_generation_evidence"]["required_artifacts"]
            ))
            self.assertTrue(any(
                artifact.startswith("mesh_wallet_evidence_receipt_command_template:")
                for artifact in evidence_items["record_paid_generation_evidence"]["required_artifacts"]
            ))
            self.assertTrue(any(
                artifact.startswith("animation_allowance_receipt_command_template:")
                for artifact in evidence_items["record_paid_generation_evidence"]["required_artifacts"]
            ))
            self.assertIn(
                "operator_command_handoff:record_masked_tripo_wallet_evidence",
                evidence_items["record_paid_generation_evidence"]["required_artifacts"],
            )
            self.assertIn(
                "operator_command_handoff:record_masked_uthana_allowance_evidence",
                evidence_items["record_paid_generation_evidence"]["required_artifacts"],
            )
            paid_metadata = evidence_items["record_paid_generation_evidence"]["metadata"]
            self.assertEqual(paid_metadata["schema"], "unreal_mcp_paid_generation_evidence_contract.v1")
            self.assertEqual(paid_metadata["mesh_provider"], "tripo")
            self.assertEqual(paid_metadata["animation_provider"], "uthana")
            self.assertEqual(paid_metadata["review_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
            self.assertIn(paid_metadata["review_receipt_state"], {"missing", "missing_evidence"})
            self.assertEqual(paid_metadata["review_receipt_required_command"], "python scripts\\write_paid_generation_evidence_review.py")
            self.assertFalse(paid_metadata["network_required_now"])
            self.assertFalse(paid_metadata["spend_required_now"])
            self.assertTrue(paid_metadata["future_network_required"])
            self.assertTrue(paid_metadata["future_spend_required"])
            self.assertTrue(paid_metadata["no_provider_call"])
            self.assertTrue(paid_metadata["no_credit_reservation"])
            self.assertTrue(paid_metadata["no_task_submission"])
            self.assertTrue(paid_metadata["no_ledger_write"])
            self.assertFalse(paid_metadata["unreal_editor_required_now"])
            self.assertIn("explicit_uthana_usage_approval", paid_metadata["evidence_required_preview"])
            self.assertIn(
                "gen_uthana_get_account / gen_uthana_get_job / gen_uthana_check_download_allowed",
                " ".join(paid_metadata["no_spend_checks"]),
            )
            self.assertEqual(paid_metadata["fallback_tool"], "skill_compile_ide_companion_placeholder_manifest")
            self.assertIn("gen_uthana_get_account(include_user=False)", " ".join(paid_metadata["wallet_evidence_review_steps"]))
            self.assertIn("--mesh-wallet-evidence-recorded", paid_metadata["wallet_evidence_receipt_command_template"])
            self.assertIn("--record-masked-tripo-wallet-evidence", paid_metadata["mesh_wallet_evidence_receipt_command_template"])
            self.assertIn("--record-masked-uthana-allowance-evidence", paid_metadata["animation_allowance_receipt_command_template"])
            self.assertIn("--record-explicit-spend-and-usage-approval", paid_metadata["spend_confirmation_receipt_command_template"])
            self.assertIn("operator_command_handoff", paid_metadata)
            self.assertEqual(len(paid_metadata["operator_command_handoff"]), 3)
            self.assertEqual(paid_metadata["operator_command_handoff"][0]["id"], "record_masked_tripo_wallet_evidence")
            self.assertEqual(paid_metadata["operator_command_handoff"][1]["id"], "record_masked_uthana_allowance_evidence")
            self.assertEqual(paid_metadata["operator_command_handoff"][2]["id"], "record_explicit_spend_and_usage_approval")
            self.assertFalse(paid_metadata["operator_command_handoff"][0]["approval_flags_included"])
            self.assertFalse(paid_metadata["operator_command_handoff"][1]["approval_flags_included"])
            self.assertTrue(paid_metadata["operator_command_handoff"][0]["no_provider_call"])
            self.assertTrue(paid_metadata["operator_command_handoff"][1]["no_provider_call"])
            self.assertTrue(paid_metadata["operator_command_handoff"][2]["approval_flags_included"])
            self.assertEqual(evidence_items["record_editor_queue_1"]["required_artifacts"], ["compile report"])
            self.assertEqual(evidence_items["record_editor_queue_1"]["state"], "blocked")
            queue_metadata = evidence_items["record_editor_queue_1"]["metadata"]
            self.assertEqual(queue_metadata["queue_name"], "editor_queue")
            self.assertEqual(queue_metadata["target_phase"], "editor_implementation")
            self.assertEqual(queue_metadata["next_action_id"], "create_placeholder_folder")
            self.assertEqual(queue_metadata["next_action_tool"], "create_folder")
            self.assertEqual(queue_metadata["action_count"], 2)
            self.assertEqual(queue_metadata["preview_action_count"], 2)
            self.assertTrue(queue_metadata["bridge_blocked"])
            self.assertFalse(queue_metadata["can_execute_now"])
            self.assertEqual(queue_metadata["argument_keys"], ["path"])
            self.assertTrue(queue_metadata["requires_successful_bridge_ping_before_execution"])
            self.assertTrue(queue_metadata["no_auto_execute"])
            self.assertTrue(queue_metadata["no_editor_mutation"])
            self.assertTrue(queue_metadata["no_pie_run"])
            self.assertTrue(queue_metadata["no_provider_call"])
            self.assertTrue(queue_metadata["no_git_mutation"])
            self.assertEqual(evidence_items["record_runtime_verification"]["state"], "blocked")
            self.assertEqual(evidence_items["record_runtime_verification"]["metadata"]["target_phase"], "editor_implementation")
            self.assertTrue(evidence_items["record_runtime_verification"]["metadata"]["bridge_blocked"])
            self.assertEqual(evidence_items["record_runtime_verification"]["metadata"]["pie_validation_count"], 1)
            self.assertEqual(evidence_items["record_runtime_verification"]["metadata"]["compile_check_count"], 1)
            self.assertEqual(evidence_items["record_runtime_verification"]["metadata"]["evidence_requirement_count"], 2)
            self.assertEqual(evidence_items["record_runtime_verification"]["metadata"]["blocked_item_count"], 1)
            self.assertEqual(evidence_items["record_runtime_verification"]["metadata"]["pending_item_count"], 2)
            self.assertIn("PIE log, viewport screenshot, and observed runtime state", evidence_items["record_runtime_verification"]["metadata"]["runtime_proof_preview"])
            self.assertFalse(evidence_items["record_runtime_verification"]["metadata"]["runtime_probe_allowed"])
            self.assertTrue(evidence_items["record_runtime_verification"]["metadata"]["requires_successful_bridge_ping_before_runtime_probe"])
            self.assertTrue(evidence_items["record_runtime_verification"]["metadata"]["no_pie_run"])
            self.assertTrue(evidence_items["record_runtime_verification"]["metadata"]["no_editor_mutation"])
            self.assertTrue(evidence_items["record_runtime_verification"]["metadata"]["no_provider_call"])
            self.assertTrue(evidence_items["record_runtime_verification"]["metadata"]["no_git_mutation"])
            self.assertEqual(evidence_items["record_repair_loop"]["evidence_type"], "repair")
            self.assertEqual(evidence_items["record_generated_asset_quality_gate"]["source"], "generated_asset_quality_gate")
            self.assertEqual(evidence_items["record_generated_asset_quality_gate"]["evidence_type"], "generated_asset_quality_gate")
            self.assertEqual(evidence_items["record_generated_asset_quality_gate"]["state"], "pending")
            self.assertFalse(evidence_items["record_generated_asset_quality_gate"]["requires_bridge"])
            self.assertIn("asset:SM_ObjectiveBeacon", evidence_items["record_generated_asset_quality_gate"]["required_artifacts"])
            self.assertIn("state:provider_pending", evidence_items["record_generated_asset_quality_gate"]["required_artifacts"])
            self.assertTrue(any("viewport" in item.lower() for item in evidence_items["record_generated_asset_quality_gate"]["required_artifacts"]))
            asset_metadata = evidence_items["record_generated_asset_quality_gate"]["metadata"]
            self.assertEqual(asset_metadata["asset_id"], "asset_01")
            self.assertEqual(asset_metadata["asset_name"], "SM_ObjectiveBeacon")
            self.assertEqual(asset_metadata["asset_role"], "objective_marker")
            self.assertEqual(asset_metadata["provider"], "tripo")
            self.assertEqual(asset_metadata["state"], "provider_pending")
            self.assertEqual(asset_metadata["task_status"], "not_submitted")
            self.assertIn("provider task", asset_metadata["next_gate"])
            self.assertTrue(asset_metadata["manifest_path"].replace("\\", "/").endswith(".mcp_artifacts/ide_companion_sessions/ide-companion_asset_lifecycle.json"))
            self.assertEqual(asset_metadata["expected_import_path"], "/Game/Generated/Assets/SM_ObjectiveBeacon")
            self.assertTrue(asset_metadata["has_placeholder"])
            self.assertTrue(any("viewport" in item.lower() for item in asset_metadata["quality_gate_preview"]))
            self.assertFalse(asset_metadata["import_or_quality_pass_allowed"])
            self.assertTrue(asset_metadata["requires_successful_bridge_ping_before_import_or_quality"])
            self.assertTrue(asset_metadata["requires_quality_evidence_before_replacement"])
            self.assertTrue(asset_metadata["no_provider_call"])
            self.assertTrue(asset_metadata["no_task_submission"])
            self.assertTrue(asset_metadata["no_download"])
            self.assertTrue(asset_metadata["no_import"])
            self.assertTrue(asset_metadata["no_editor_mutation"])
            self.assertTrue(asset_metadata["no_git_mutation"])
            self.assertEqual(evidence_items["record_generated_animation_evidence"]["source"], "generated_animation_lifecycle")
            self.assertEqual(evidence_items["record_generated_animation_evidence"]["evidence_type"], "generated_animation_evidence")
            self.assertEqual(evidence_items["record_generated_animation_evidence"]["state"], "pending")
            self.assertFalse(evidence_items["record_generated_animation_evidence"]["requires_bridge"])
            self.assertIn("animation:A_EnemyScout_PatrolWalk", evidence_items["record_generated_animation_evidence"]["required_artifacts"])
            self.assertIn("provider:uthana", evidence_items["record_generated_animation_evidence"]["required_artifacts"])
            self.assertIn("compiler:gen_compile_generated_animation_evidence", evidence_items["record_generated_animation_evidence"]["required_artifacts"])
            animation_metadata = evidence_items["record_generated_animation_evidence"]["metadata"]
            self.assertEqual(animation_metadata["animation_id"], "animation_01")
            self.assertEqual(animation_metadata["animation_name"], "A_EnemyScout_PatrolWalk")
            self.assertEqual(animation_metadata["provider"], "uthana")
            self.assertEqual(animation_metadata["task_status"], "not_submitted")
            self.assertEqual(animation_metadata["expected_import_path"], "/Game/Generated/Animations/A_EnemyScout_PatrolWalk")
            self.assertEqual(animation_metadata["target_skeleton"], "UE5 Manny")
            self.assertEqual(animation_metadata["quality_gate_count"], 7)
            self.assertEqual(animation_metadata["quality_evidence_count"], 0)
            self.assertEqual(
                animation_metadata["quality_proof_contract_schema"],
                "unreal_mcp_generated_animation_quality_proof_contract.v1",
            )
            self.assertEqual(animation_metadata["quality_proof_required_count"], 5)
            self.assertIn("animgraph_or_state_machine_reference", animation_metadata["quality_proof_required_preview"])
            self.assertIn("animation_retarget_animgraph_pie_ledger_proof", animation_metadata["missing_stage_preview"])
            self.assertEqual(
                animation_metadata["uthana_usage_contract_schema"],
                "unreal_mcp_uthana_animation_usage_contract.v1",
            )
            self.assertEqual(animation_metadata["uthana_usage_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
            self.assertIn("gen_uthana_get_account", animation_metadata["uthana_allowance_tools"])
            self.assertIn("confirm_usage=True", animation_metadata["uthana_usage_confirmation_field"])
            self.assertEqual(len(animation_metadata["uthana_usage_operator_command_handoff"]), 2)
            self.assertEqual(
                animation_metadata["uthana_usage_operator_command_handoff"][0]["id"],
                "record_masked_uthana_allowance_evidence",
            )
            self.assertTrue(animation_metadata["uthana_usage_operator_command_handoff"][0]["no_provider_call"])
            self.assertEqual(
                animation_metadata["uthana_usage_next_operator_command_handoff"]["id"],
                "record_masked_uthana_allowance_evidence",
            )
            self.assertTrue(animation_metadata["no_provider_call"])
            self.assertTrue(animation_metadata["no_task_submission"])
            self.assertTrue(animation_metadata["no_download"])
            self.assertTrue(animation_metadata["no_import"])
            self.assertTrue(animation_metadata["no_editor_mutation"])
            self.assertEqual(evidence_items["record_feature_completion_contract"]["source"], "feature_completion_contract")
            self.assertEqual(evidence_items["record_feature_completion_contract"]["evidence_type"], "feature_completion_contract")
            self.assertEqual(evidence_items["record_feature_completion_contract"]["state"], "pending")
            self.assertFalse(evidence_items["record_feature_completion_contract"]["requires_bridge"])
            self.assertEqual(evidence_items["record_feature_completion_contract"]["required_artifact_count"], 10)
            self.assertIn("feature_template_packet", evidence_items["record_feature_completion_contract"]["required_artifacts"])
            self.assertTrue(any("pie_validation_passed" in item for item in evidence_items["record_feature_completion_contract"]["required_artifacts"]))
            completion_metadata = evidence_items["record_feature_completion_contract"]["metadata"]
            self.assertEqual(completion_metadata["completion_contract_schema"], "unreal_mcp_gameplay_feature_completion_contract.v1")
            self.assertEqual(completion_metadata["completion_proof_gate_count"], 3)
            self.assertEqual(completion_metadata["completion_required_evidence_count"], 6)
            self.assertIn("ide_companion_ledger_event", completion_metadata["completion_required_evidence_preview"])
            self.assertIn("ledger_evidence_recorded", json.dumps(completion_metadata["completion_proof_gate_preview"]))
            self.assertIn("evidence_recording", {card["id"] for card in payload["cards"]})
            self.assertEqual(payload["next_safe_step"]["schema"], "unreal_mcp_chat_next_safe_step_gate.v1")
            self.assertEqual(payload["next_safe_step"]["state"], "blocked")
            self.assertFalse(payload["next_safe_step"]["can_execute_now"])
            self.assertEqual(payload["next_safe_step"]["next_action_id"], "create_placeholder_folder")
            self.assertEqual(payload["next_safe_step"]["next_action_tool"], "create_folder")
            self.assertEqual(payload["next_safe_step"]["next_action_label"], "create_placeholder_folder")
            self.assertEqual(payload["next_safe_step"]["argument_keys"], ["path"])
            self.assertTrue(payload["next_safe_step"]["bridge_blocked"])
            self.assertIn("unreal_bridge_reachable", payload["next_safe_step"]["blocking_gates"])
            self.assertIn("Confirm can_execute_now", " ".join(payload["next_safe_step"]["pre_execution_checklist"]))
            self.assertGreaterEqual(payload["next_safe_step"]["after_execution_evidence_count"], 1)
            self.assertEqual(payload["next_safe_step"]["after_execution_evidence"][0]["source"], "editor_queue")
            self.assertIn("next_safe_step", {card["id"] for card in payload["cards"]})
            self.assertEqual(payload["execution_review"]["schema"], "unreal_mcp_chat_execution_review.v1")
            self.assertEqual(payload["execution_review"]["state"], "blocked")
            self.assertFalse(payload["execution_review"]["can_execute_now"])
            self.assertEqual(payload["execution_review"]["target_action"]["tool"], "create_folder")
            self.assertEqual(payload["execution_review"]["target_action"]["action_id"], "create_placeholder_folder")
            self.assertIn("unreal_bridge_reachable", payload["execution_review"]["missing_gates"])
            self.assertGreaterEqual(payload["execution_review"]["after_execution_evidence_count"], 1)
            self.assertIn("Run only the next queued editor action.", payload["execution_review"]["policy_preview"])
            self.assertIn("Execute exactly one queued editor action.", payload["execution_review"]["executor_contract"])
            self.assertIn("Refresh cockpit overview", " ".join(payload["execution_review"]["pre_execution_checklist"]))
            self.assertIn("Record queued editor action evidence", " ".join(payload["execution_review"]["post_execution_evidence_required"]))
            self.assertTrue(payload["execution_review"]["stop_after_action"])
            self.assertIn("execution_review", {card["id"] for card in payload["cards"]})
            self.assertEqual(payload["failure_triage"]["schema"], "unreal_mcp_chat_failure_triage_summary.v1")
            self.assertEqual(payload["failure_triage"]["state"], "needs_repair")
            self.assertEqual(payload["failure_triage"]["item_count"], 4)
            self.assertEqual(payload["failure_triage"]["needs_repair_count"], 1)
            self.assertEqual(payload["failure_triage"]["blocked_count"], 3)
            self.assertEqual(payload["failure_triage"]["items"][0]["source"], "evidence_timeline")
            self.assertIn("TargetActor pin", payload["failure_triage"]["items"][0]["label"])
            self.assertIn("skill_compile_ide_companion_work_order", payload["failure_triage"]["recommended_tools"])
            self.assertIn("failure_triage", {card["id"] for card in payload["cards"]})
            workflow_actions = {action["id"]: action for action in payload["workflow_actions"]}
            self.assertEqual(
                set(workflow_actions),
                {
                    "start_companion_session",
                    "check_readiness",
                    "review_readiness_repair_queue",
                    "review_platform_preflight_gate",
                    "review_live_editor_bridge_gate",
                    "review_wip_promotion_gate",
                    "review_blueprint_mutation_gate",
                    "review_bridge_wrapper_coverage",
                    "review_test_lane_gates",
                    "review_provider_config_gate",
                    "refresh_companion_status",
                    "generate_work_order",
                    "review_gameplay_template_plan",
                    "queue_gameplay_template_next_operation",
                    "resume_companion_session",
                    "show_companion_dashboard",
                    "show_evidence_ledger",
                    "resolve_blockers",
                    "review_generated_asset_gate",
                    "review_generated_asset_lifecycle_gate",
                    "compile_asset_lifecycle_manifest",
                    "review_generated_animation_lifecycle_gate",
                    "compile_generated_animation_evidence",
                    "review_generated_asset_import_gate",
                    "review_generated_asset_quality_proof_gate",
                    "review_generated_asset_replacement_gate",
                    "review_provider_spend_gate",
                    "continue_with_placeholder_fallback",
                    "review_generated_asset_provider_task_gate",
                    "resolve_generated_asset",
                    "compile_placeholder_manifest",
                    "review_editor_queue",
                    "queue_editor_actions",
                    "execute_next_safe_step",
                    "review_evidence_requirements",
                    "record_evidence",
                    "record_platform_stability_review",
                    "record_dirty_promotion_review",
                    "record_provider_config_review",
                    "record_bridge_ping_receipt",
                    "record_chat_cockpit_start_receipt",
                    "record_queued_action_evidence",
                    "record_generated_asset_evidence",
                    "record_paid_generation_evidence",
                    "record_generated_animation_evidence",
                    "record_feature_completion_contract",
                    "review_runtime_verification",
                    "record_runtime_evidence",
                    "repair_failed_step",
                },
            )
            self.assertTrue(workflow_actions["start_companion_session"]["enabled"])
            self.assertEqual(
                workflow_actions["start_companion_session"]["input_source"],
                "session_name plus cockpit readiness, ledger, queue, and generated-asset state",
            )
            start_context = workflow_actions["start_companion_session"]["target_start_context"]
            self.assertEqual(start_context["session_name"], "ide-companion")
            self.assertTrue(start_context["has_existing_ledger"])
            self.assertEqual(start_context["event_count"], 3)
            self.assertEqual(start_context["completed_phase_count"], 1)
            self.assertEqual(start_context["readiness_state"], "blocked")
            self.assertEqual(start_context["blocked_policy_count"], 4)
            self.assertEqual(start_context["queue_count"], 1)
            self.assertEqual(start_context["generated_asset_count"], 2)
            self.assertEqual(start_context["recommended_next"], "resume_existing_session")
            self.assertTrue(start_context["stop_before_editor_or_provider"])
            self.assertTrue(workflow_actions["check_readiness"]["enabled"])
            self.assertEqual(workflow_actions["check_readiness"]["input_source"], "outputs.readiness_policy plus local preflight gates")
            readiness_context = workflow_actions["check_readiness"]["target_readiness_policy_context"]
            self.assertEqual(readiness_context["state"], "blocked")
            self.assertEqual(readiness_context["blocked_policy_count"], 4)
            self.assertEqual(readiness_context["blocked_policies"], ["editor_mutation", "paid_generation", "paid_animation_generation", "blueprint_mutation"])
            self.assertEqual(readiness_context["missing_gate_count"], 5)
            self.assertIn("unreal_bridge_reachable", readiness_context["missing_gate_preview"])
            self.assertIn("wallet_evidence_recorded", readiness_context["missing_gate_preview"])
            self.assertIn("gen_compile_ide_companion_readiness", readiness_context["recommended_tools"])
            self.assertTrue(readiness_context["stop_before_editor_or_provider"])
            self.assertTrue(workflow_actions["review_readiness_repair_queue"]["enabled"])
            self.assertFalse(workflow_actions["review_readiness_repair_queue"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_readiness_repair_queue"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_readiness_repair_queue"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_readiness_repair_queue"]["input_source"],
                "outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context.readiness_repair_queue",
            )
            self.assertTrue(workflow_actions["review_platform_preflight_gate"]["enabled"])
            self.assertFalse(workflow_actions["review_platform_preflight_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_platform_preflight_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_platform_preflight_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_platform_preflight_gate"]["input_source"],
                "scripts/audit_ide_companion_readiness.py plus outputs.readiness_policy",
            )
            platform_context = workflow_actions["review_platform_preflight_gate"]["target_platform_preflight_context"]
            self.assertEqual(platform_context["schema"], "unreal_mcp_ide_companion_preflight.v1")
            self.assertIn(platform_context["state"], {"ready", "blocked"})
            self.assertEqual(platform_context["audit_tool"], "scripts/audit_ide_companion_readiness.py")
            self.assertEqual(platform_context["readiness_tool"], "gen_compile_ide_companion_readiness")
            self.assertGreaterEqual(platform_context["tool_count"], 1)
            self.assertGreaterEqual(platform_context["recorded_count"], 1)
            self.assertIn("readiness_repair_queue", platform_context)
            repair_queue = platform_context["readiness_repair_queue"]
            self.assertEqual(repair_queue["schema"], "unreal_mcp_readiness_repair_queue.v1")
            self.assertEqual(repair_queue["state"], "blocked")
            self.assertGreaterEqual(repair_queue["action_count"], 1)
            self.assertIn(
                repair_queue["recommended_next"],
                {
                    "repair_chat_server_reachability",
                    "refresh_chat_cockpit_after_server_ready",
                    "review_dirty_groups_for_promotion",
                    "verify_unreal_bridge_reachability",
                    "configure_tripo_provider_secret",
                    "configure_uthana_provider_secret",
                    "record_wallet_or_allowance_evidence",
                },
            )
            self.assertEqual(
                repair_queue["priority_policy"],
                "chat_health_then_wip_promotion_safety_then_bridge_proof_then_paid_provider_gates",
            )
            self.assertTrue(repair_queue["no_auto_execute"])
            self.assertTrue(repair_queue["no_secret_echo"])
            self.assertTrue(repair_queue["no_git_mutation"])
            self.assertTrue(repair_queue["no_editor_mutation"])
            if repair_queue["recommended_next"] == "record_wallet_or_allowance_evidence":
                self.assertTrue(repair_queue["network_required_for_next_action"])
            else:
                self.assertFalse(repair_queue["network_required_for_next_action"])
            self.assertFalse(repair_queue["spend_required_for_next_action"])
            self.assertIn(
                repair_queue["next_action"]["gate"],
                {
                    "chat_server_reachable",
                    "chat_cockpit_reachable",
                    "dirty_state_grouped_for_promotion",
                    "unreal_bridge_reachable",
                    "provider_api_key_configured",
                    "animation_provider_api_key_configured",
                    "wallet_evidence_recorded",
                },
            )
            if repair_queue["next_action"]["gate"] == "chat_server_reachable":
                self.assertIn("chat_history_http_200", repair_queue["next_action"]["evidence_required_preview"])
            if repair_queue["next_action"]["gate"] == "dirty_state_grouped_for_promotion":
                self.assertFalse(repair_queue["network_required_for_next_action"])
                self.assertEqual(repair_queue["next_action"]["recommended_tool"], "scripts/write_dirty_promotion_review.py")
                self.assertIn("evidence_review_matrix_count", repair_queue["next_action"])
                self.assertIn("evidence_unresolved_count", repair_queue["next_action"])
                self.assertIn("evidence_review_matrix_preview", repair_queue["next_action"])
                self.assertIn("target_review_group", repair_queue["next_action"])
                self.assertIn("target_review_focused_test_command_preview", repair_queue["next_action"])
                self.assertIn("target_review_sample_preview", repair_queue["next_action"])
                self.assertIn("target_review_required_evidence_preview", repair_queue["next_action"])
                self.assertIn("target_review_decision_prompt_preview", repair_queue["next_action"])
                self.assertIn("target_review_receipt_command_template", repair_queue["next_action"])
                self.assertIn("target_review_approval_receipt_command_template", repair_queue["next_action"])
                self.assertIn("target_review_receipt_command_policy", repair_queue["next_action"])
                self.assertIn("target_review_operator_command_handoff", repair_queue["next_action"])
                self.assertEqual(len(repair_queue["next_action"]["target_review_operator_command_handoff"]), 2)
                self.assertFalse(repair_queue["next_action"]["target_review_operator_command_handoff"][0]["approval_flag_included"])
                self.assertTrue(repair_queue["next_action"]["target_review_operator_command_handoff"][1]["approval_flag_included"])
                self.assertIn("target_review_pending_human_approval_only", repair_queue["next_action"])
                self.assertIn("target_review_human_approval_command_handoff", repair_queue["next_action"])
                if repair_queue["next_action"]["target_review_pending_human_approval_only"]:
                    self.assertEqual(
                        repair_queue["next_operator_command_handoff"],
                        repair_queue["next_action"]["target_review_human_approval_command_handoff"],
                    )
                else:
                    self.assertEqual(
                        repair_queue["next_operator_command_handoff"],
                        repair_queue["next_action"]["target_review_operator_command_handoff"],
                    )
                self.assertIn("--target-owner-or-source", repair_queue["next_action"]["target_review_receipt_command_template"])
                self.assertNotIn("--target-human-approval-recorded", repair_queue["next_action"]["target_review_receipt_command_template"])
                self.assertIn(
                    "--target-human-approval-recorded",
                    repair_queue["next_action"]["target_review_approval_receipt_command_template"],
                )
                self.assertIn("target_review_status", repair_queue["next_action"])
                self.assertIn("target_review_recorded_evidence_preview", repair_queue["next_action"])
                self.assertIn("target_review_human_approval_recorded", repair_queue["next_action"])
                self.assertIn("target_review_merge_policy", repair_queue["next_action"])
                self.assertIn("target_review_previous_evidence_merged", repair_queue["next_action"])
                self.assertIn("target_review_reset_evidence", repair_queue["next_action"])
                if repair_queue["next_action"]["evidence_review_matrix_preview"]:
                    self.assertFalse(repair_queue["next_action"]["evidence_review_matrix_preview"][0]["promotion_allowed"])
                    self.assertEqual(
                        repair_queue["next_action"]["target_review_group"],
                        repair_queue["next_action"]["evidence_review_matrix_preview"][0]["group"],
                    )
                    self.assertIn(
                        "human_approval_before_stage_commit_merge",
                        repair_queue["next_action"]["target_review_missing_evidence_preview"],
                    )
                    self.assertIn(
                        "human_approval_before_stage_commit_merge",
                        repair_queue["next_action"]["target_review_required_evidence_preview"],
                    )
                    self.assertTrue(any(
                        "promotion_intent" in prompt
                        for prompt in repair_queue["next_action"]["target_review_decision_prompt_preview"]
                    ))
                    self.assertFalse(repair_queue["next_action"]["target_review_promotion_allowed_after_receipt"])
                if repair_queue["next_action"]["target_review_focused_test_command_count"]:
                    self.assertIn("python", " ".join(repair_queue["next_action"]["target_review_focused_test_command_preview"]).lower())
            if repair_queue["next_action"]["gate"] == "unreal_bridge_reachable":
                self.assertFalse(repair_queue["network_required_for_next_action"])
                self.assertEqual(repair_queue["next_action"]["recommended_tool"], "scripts/bridge_ping.py")
            if repair_queue["next_action"]["gate"] == "wallet_evidence_recorded":
                self.assertTrue(repair_queue["next_action"]["no_credit_reservation"])
                self.assertTrue(repair_queue["next_action"]["no_task_submission"])
                self.assertIn("gen_uthana_get_account(include_user=False)", " ".join(repair_queue["next_action"]["review_steps"]))
                self.assertIn("--mesh-wallet-evidence-recorded", repair_queue["next_action"]["receipt_command_template"])
            self.assertNotIn("api_key_masked", json.dumps(repair_queue))
            repair_queue_context = workflow_actions["review_readiness_repair_queue"]["target_readiness_repair_queue_context"]
            self.assertEqual(repair_queue_context["schema"], "unreal_mcp_readiness_repair_queue.v1")
            self.assertEqual(repair_queue_context["recommended_next"], repair_queue["recommended_next"])
            self.assertEqual(repair_queue_context["next_gate"], repair_queue["next_action"]["gate"])
            self.assertEqual(repair_queue_context["priority_policy"], repair_queue["priority_policy"])
            self.assertEqual(repair_queue_context["next_action_id"], repair_queue["next_action"]["action_id"])
            self.assertEqual(repair_queue_context["next_tool"], repair_queue["next_action"]["recommended_tool"])
            if repair_queue_context["next_gate"] == "dirty_state_grouped_for_promotion":
                self.assertEqual(
                    repair_queue_context["next_evidence_review_matrix_count"],
                    repair_queue["next_action"]["evidence_review_matrix_count"],
                )
                self.assertEqual(
                    repair_queue_context["next_evidence_unresolved_count"],
                    repair_queue["next_action"]["evidence_unresolved_count"],
                )
                self.assertEqual(
                    repair_queue_context["next_evidence_review_matrix_preview"],
                    repair_queue["next_action"]["evidence_review_matrix_preview"][:3],
                )
                self.assertEqual(
                    repair_queue_context["next_target_review_group"],
                    repair_queue["next_action"]["target_review_group"],
                )
                self.assertEqual(
                    repair_queue_context["next_target_review_focused_test_command_preview"],
                    repair_queue["next_action"]["target_review_focused_test_command_preview"][:5],
                )
                self.assertEqual(
                    repair_queue_context["next_target_review_sample_preview"],
                    repair_queue["next_action"]["target_review_sample_preview"][:5],
                )
                self.assertEqual(
                    repair_queue_context["next_target_review_required_evidence_preview"],
                    repair_queue["next_action"]["target_review_required_evidence_preview"][:8],
                )
                self.assertEqual(
                    repair_queue_context["next_target_review_decision_prompt_preview"],
                    repair_queue["next_action"]["target_review_decision_prompt_preview"][:8],
                )
                self.assertEqual(
                    repair_queue_context["next_target_review_receipt_command_template"],
                    repair_queue["next_action"]["target_review_receipt_command_template"],
                )
                self.assertEqual(
                    repair_queue_context["next_target_review_approval_receipt_command_template"],
                    repair_queue["next_action"]["target_review_approval_receipt_command_template"],
                )
                self.assertIn("explicit human approval", repair_queue_context["next_target_review_receipt_command_policy"])
                self.assertEqual(
                    repair_queue_context["next_target_review_operator_command_handoff"],
                    repair_queue["next_action"]["target_review_operator_command_handoff"],
                )
                self.assertEqual(
                    repair_queue_context["next_target_review_focused_test_command_handoff"],
                    repair_queue["next_action"]["target_review_focused_test_command_handoff"],
                )
                self.assertIn("next_target_review_pending_human_approval_only", repair_queue_context)
                self.assertIn("next_target_review_human_approval_command_handoff", repair_queue_context)
                if repair_queue_context["next_target_review_pending_human_approval_only"]:
                    self.assertEqual(repair_queue_context["next_target_review_human_approval_gate"], "human_approval_before_stage_commit_merge")
                    self.assertEqual(len(repair_queue_context["next_target_review_human_approval_command_handoff"]), 1)
                    self.assertEqual(
                        repair_queue_context["next_operator_command_handoff"],
                        repair_queue_context["next_target_review_human_approval_command_handoff"],
                    )
                else:
                    self.assertEqual(
                        repair_queue_context["next_operator_command_handoff"],
                        repair_queue["next_action"]["target_review_operator_command_handoff"],
                    )
                self.assertEqual(
                    repair_queue_context["next_target_review_recorded_evidence_preview"],
                    repair_queue["next_action"]["target_review_recorded_evidence_preview"][:8],
                )
                self.assertFalse(repair_queue_context["next_target_review_human_approval_recorded"])
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    repair_queue_context["next_target_review_required_evidence_preview"],
                )
                self.assertTrue(any(
                    "owner_or_source" in prompt
                    for prompt in repair_queue_context["next_target_review_decision_prompt_preview"]
                ))
                self.assertFalse(repair_queue_context["next_target_review_promotion_allowed_after_receipt"])
                self.assertEqual(
                    repair_queue_context["next_target_review_merge_policy"],
                    repair_queue["next_action"]["target_review_merge_policy"],
                )
                self.assertFalse(repair_queue_context["next_target_review_reset_evidence"])
            self.assertTrue(repair_queue_context["stop_before_running_repair"])
            self.assertTrue(repair_queue_context["no_auto_execute"])
            self.assertTrue(repair_queue_context["no_git_mutation"])
            self.assertTrue(repair_queue_context["no_editor_mutation"])
            self.assertIn("dirty_risk", platform_context)
            self.assertIn("dirty_group_count", platform_context)
            self.assertIn("dirty_group_preview", platform_context)
            self.assertIn("dirty_grouping_required", platform_context)
            self.assertIn("dirty_promotion_contract", platform_context)
            dirty_contract = platform_context["dirty_promotion_contract"]
            self.assertEqual(dirty_contract["schema"], "unreal_mcp_dirty_promotion_contract.v1")
            self.assertEqual(dirty_contract["dirty_group_count"], platform_context["dirty_group_count"])
            self.assertEqual(dirty_contract["tracked_change_count"], platform_context["tracked_change_count"])
            self.assertEqual(dirty_contract["untracked_count"], platform_context["untracked_count"])
            self.assertIn(dirty_contract["state"], {"ready", "needs_grouping"})
            self.assertTrue(dirty_contract["no_git_mutation"])
            self.assertTrue(dirty_contract["no_stage"])
            self.assertTrue(dirty_contract["no_commit"])
            self.assertTrue(dirty_contract["no_clean"])
            self.assertTrue(dirty_contract["no_delete"])
            self.assertTrue(dirty_contract["no_branch_or_merge"])
            self.assertTrue(dirty_contract["no_provider_call"])
            self.assertTrue(dirty_contract["no_editor_mutation"])
            self.assertIn("one coherent dirty group", dirty_contract["promotion_batch_policy"])
            self.assertIn("generated/local artifacts", dirty_contract["artifact_policy"])
            self.assertIn("run_focused_tests_for_each_candidate_batch", dirty_contract["safe_promotion_next_steps"])
            self.assertIn("evidence_review_matrix_count", dirty_contract)
            self.assertIn("evidence_review_matrix_preview", dirty_contract)
            self.assertIn("evidence_unresolved_count", dirty_contract)
            self.assertIn("receipt records the review target only", dirty_contract["evidence_review_policy"])
            if dirty_contract["evidence_review_matrix_preview"]:
                self.assertIn("missing_evidence", dirty_contract["evidence_review_matrix_preview"][0])
                self.assertFalse(dirty_contract["evidence_review_matrix_preview"][0]["promotion_allowed"])
            self.assertIn(dirty_contract["review_receipt_state"], {"missing", "review_required", "ready", "blocked", "stale"})
            self.assertEqual(dirty_contract["review_receipt_path"], "Saved\\DirtyPromotionReview\\last_review_receipt.json")
            self.assertEqual(dirty_contract["review_receipt_required_command"], "python scripts\\write_dirty_promotion_review.py")
            self.assertIn("human_review_before_stage_commit_or_merge", dirty_contract["required_evidence_preview"])
            self.assertIn("current_branch", platform_context)
            self.assertIn("branch_role", platform_context)
            self.assertIn("working_branch_ok", platform_context)
            self.assertEqual(platform_context["source_branch_policy"], "wip")
            self.assertEqual(platform_context["stable_branch_policy"], "main")
            self.assertIn("bridge_ready", platform_context)
            self.assertIn("bridge_tcp_ready", platform_context)
            self.assertIn(platform_context["bridge_ping_receipt_state"], {"missing", "ok", "blocked"})
            self.assertEqual(platform_context["bridge_ping_receipt_path"], "Saved\\BridgePing\\last_ping_receipt.json")
            self.assertEqual(platform_context["bridge_ping_required_command"], "python scripts\\bridge_ping.py")
            self.assertEqual(platform_context["bridge_ping_operator_command_handoff_count"], 1)
            self.assertEqual(platform_context["bridge_ping_operator_command_handoff_ids"], ["verify_unreal_bridge_ping"])
            self.assertEqual(
                platform_context["bridge_ping_operator_command_handoff"][0]["command"],
                "python scripts\\bridge_ping.py",
            )
            self.assertTrue(platform_context["bridge_ping_operator_command_handoff"][0]["requires_bridge"])
            self.assertTrue(platform_context["bridge_ping_operator_command_handoff"][0]["no_editor_mutation"])
            self.assertIn("successful_bridge_ping", platform_context)
            self.assertIn("chat_ready", platform_context)
            self.assertIn("chat_base_url", platform_context)
            self.assertIn("chat_health_endpoint", platform_context)
            self.assertIn("chat_tcp_ready", platform_context)
            self.assertIn("chat_startup_script", platform_context)
            self.assertEqual(platform_context["chat_startup_script"], "scripts\\start_chat_cockpit_server.ps1")
            self.assertEqual(platform_context["chat_startup_receipt_path"], "Saved\\ChatCockpit\\last_start_receipt.json")
            self.assertIn("chat_startup_command", platform_context)
            self.assertIn("scripts\\start_chat_cockpit_server.ps1", platform_context["chat_startup_command"])
            self.assertIn("--transport sse", platform_context["chat_manual_startup_command"])
            self.assertIn("chat_agent_command", platform_context)
            self.assertIn("chat_cockpit_repair_contract", platform_context)
            chat_repair = platform_context["chat_cockpit_repair_contract"]
            self.assertEqual(chat_repair["schema"], "unreal_mcp_chat_cockpit_repair_contract.v1")
            self.assertEqual(chat_repair["health_endpoint"], "/chat/history?limit=1")
            self.assertEqual(chat_repair["startup_script"], "scripts\\start_chat_cockpit_server.ps1")
            self.assertEqual(chat_repair["startup_receipt_path"], "Saved\\ChatCockpit\\last_start_receipt.json")
            self.assertIn("scripts\\start_chat_cockpit_server.ps1", chat_repair["startup_command"])
            self.assertIn("--transport sse", chat_repair["manual_startup_command"])
            self.assertIn("Invoke-WebRequest", chat_repair["proof_command"])
            self.assertIn("messages list", chat_repair["proof_expected"])
            self.assertIn("chat_cockpit_start_receipt_success", chat_repair["required_evidence_preview"])
            self.assertIn("chat_history_http_200", chat_repair["required_evidence_preview"])
            self.assertTrue(chat_repair["no_process_start"])
            self.assertTrue(chat_repair["no_port_kill"])
            self.assertFalse(chat_repair["network_required"])
            self.assertFalse(chat_repair["spend_required"])
            self.assertFalse(chat_repair["unreal_editor_required"])
            self.assertIn("provider_api_key_configured", platform_context)
            self.assertIn("animation_provider_api_key_configured", platform_context)
            self.assertIn("provider_secrets_gitignored", platform_context)
            self.assertIn("provider_settings_gitignored", platform_context)
            self.assertIn(platform_context["provider_config_review_receipt_state"], {"missing", "ready", "missing_keys", "blocked"})
            self.assertEqual(platform_context["provider_config_review_receipt_path"], "Saved\\ProviderConfigReview\\last_review_receipt.json")
            self.assertEqual(platform_context["provider_config_review_receipt_required_command"], "python scripts\\write_provider_config_review.py")
            self.assertEqual(platform_context["provider_config_operator_command_handoff_count"], 1)
            self.assertEqual(platform_context["provider_config_operator_command_handoff_ids"], ["write_provider_config_review_receipt"])
            self.assertEqual(
                platform_context["provider_config_operator_command_handoff"][0]["command"],
                "python scripts\\write_provider_config_review.py",
            )
            self.assertTrue(platform_context["provider_config_operator_command_handoff"][0]["no_provider_call"])
            self.assertIn("platform_stability_review", platform_context)
            self.assertIn(platform_context["platform_stability_review_receipt_state"], {"missing", "ready", "review_required", "blocked"})
            self.assertEqual(platform_context["platform_stability_review_receipt_path"], "Saved\\PlatformStabilityReview\\last_review_receipt.json")
            self.assertEqual(platform_context["platform_stability_review_receipt_required_command"], "python scripts\\write_platform_stability_review.py")
            self.assertTrue(platform_context["platform_stability_review"]["no_provider_call"])
            self.assertTrue(platform_context["platform_stability_review"]["no_editor_mutation"])
            self.assertTrue(platform_context["platform_stability_review"]["no_git_mutation"])
            self.assertIn("dirty_promotion_review_receipt_current", platform_context["platform_stability_review"])
            self.assertIn("dirty_promotion_review_receipt_stale", platform_context["platform_stability_review"])
            self.assertIn("dirty_promotion_review_receipt_signature_match", platform_context["platform_stability_review"])
            self.assertEqual(platform_context["platform_stability_review"]["tool_count"], platform_context["tool_count"])
            self.assertEqual(platform_context["platform_stability_review"]["recorded_tool_count"], platform_context["recorded_count"])
            self.assertEqual(platform_context["platform_stability_review"]["partial_tool_count"], platform_context["partial_tool_count"])
            self.assertEqual(platform_context["platform_stability_review"]["blocking_gate_count"], platform_context["blocking_gate_count"])
            self.assertIn("blueprint_pre_read_evidence", platform_context["platform_stability_review"]["blocking_gate_preview"])
            self.assertIn("blueprint_compile_plan", platform_context["platform_stability_review"]["blocking_gate_preview"])
            self.assertEqual(
                platform_context["platform_stability_review"]["readiness_repair_action_count"],
                platform_context["readiness_repair_queue"]["action_count"],
            )
            self.assertEqual(
                platform_context["platform_stability_review"]["readiness_repair_recommended_next"],
                platform_context["readiness_repair_queue"]["recommended_next"],
            )
            self.assertEqual(
                platform_context["platform_stability_review"]["readiness_repair_next_gate"],
                platform_context["readiness_repair_queue"]["next_action"]["gate"],
            )
            self.assertTrue(platform_context["platform_stability_review"]["readiness_repair_action_preview"])
            self.assertIn(
                platform_context["readiness_repair_queue"]["next_action"]["gate"],
                {item["gate"] for item in platform_context["platform_stability_review"]["readiness_repair_action_preview"]},
            )
            self.assertIn("dirty_target_review_group", platform_context["platform_stability_review"])
            self.assertIn("dirty_target_review_status", platform_context["platform_stability_review"])
            self.assertIn("dirty_target_review_recorded_evidence_count", platform_context["platform_stability_review"])
            self.assertIn("dirty_target_review_human_approval_recorded", platform_context["platform_stability_review"])
            self.assertIn("dirty_target_review_missing_evidence_preview", platform_context["platform_stability_review"])
            self.assertIn("dirty_target_review_pending_human_approval_only", platform_context["platform_stability_review"])
            self.assertIn("dirty_target_review_human_approval_command_handoff", platform_context["platform_stability_review"])
            self.assertIn("dirty_target_review_focused_test_command_handoff", platform_context["platform_stability_review"])
            self.assertIn("dirty_target_review_focused_test_command_preview", platform_context["platform_stability_review"])
            if platform_context["platform_stability_review"]["dirty_target_review_focused_test_command_handoff"]:
                self.assertEqual(
                    platform_context["platform_stability_review"]["dirty_target_review_focused_test_command_handoff"][0]["command_kind"],
                    "local_validation",
                )
            if platform_context["platform_stability_review"]["dirty_target_review_group"]:
                self.assertGreaterEqual(
                    platform_context["platform_stability_review"]["dirty_target_review_missing_evidence_count"],
                    1,
                )
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    platform_context["platform_stability_review"]["dirty_target_review_missing_evidence_preview"],
                )
                self.assertFalse(platform_context["platform_stability_review"]["dirty_target_review_promotion_allowed_after_receipt"])
            self.assertIn("provider_secret_contract", platform_context)
            self.assertIn("provider_repair_contract", platform_context)
            self.assertFalse(platform_context["provider_secret_contract"]["raw_key_returned"])
            self.assertIn("<TRIPO_API_KEY>", platform_context["provider_repair_contract"]["tripo_store_command_template"])
            self.assertIn("<UTHANA_API_KEY>", platform_context["provider_repair_contract"]["uthana_store_command_template"])
            self.assertIn("paid_generation_evidence_contract", platform_context)
            paid_evidence_contract = platform_context["paid_generation_evidence_contract"]
            self.assertEqual(paid_evidence_contract["schema"], "unreal_mcp_paid_generation_evidence_contract.v1")
            self.assertFalse(paid_evidence_contract["wallet_evidence_recorded"])
            self.assertFalse(paid_evidence_contract["mesh_wallet_evidence_recorded"])
            self.assertFalse(paid_evidence_contract["animation_allowance_evidence_recorded"])
            self.assertFalse(paid_evidence_contract["spend_confirmation_recorded"])
            self.assertFalse(paid_evidence_contract["explicit_spend_approval_recorded"])
            self.assertFalse(paid_evidence_contract["explicit_usage_approval_recorded"])
            self.assertEqual(paid_evidence_contract["review_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
            self.assertEqual(paid_evidence_contract["review_receipt_required_command"], "python scripts\\write_paid_generation_evidence_review.py")
            self.assertIn(paid_evidence_contract["review_receipt_state"], {"missing", "missing_evidence", "ready"})
            self.assertFalse(paid_evidence_contract["network_required_now"])
            self.assertFalse(paid_evidence_contract["spend_required_now"])
            self.assertTrue(paid_evidence_contract["future_spend_required"])
            self.assertFalse(paid_evidence_contract["unreal_editor_required_now"])
            self.assertTrue(paid_evidence_contract["no_provider_call"])
            self.assertTrue(paid_evidence_contract["no_task_submission"])
            self.assertTrue(paid_evidence_contract["no_credit_reservation"])
            self.assertTrue(paid_evidence_contract["no_ledger_write"])
            self.assertIn("gen_uthana_get_account", paid_evidence_contract["animation_allowance_tools"])
            self.assertIn(
                "gen_uthana_get_account / gen_uthana_get_job / gen_uthana_check_download_allowed",
                " ".join(paid_evidence_contract["no_spend_checks"]),
            )
            self.assertIn("masked_tripo_wallet_evidence", paid_evidence_contract["evidence_required_preview"])
            self.assertIn("explicit_uthana_usage_approval", paid_evidence_contract["evidence_required_preview"])
            self.assertEqual(paid_evidence_contract["fallback_tool"], "skill_compile_ide_companion_placeholder_manifest")
            self.assertIn("placeholders and lifecycle manifests", paid_evidence_contract["fallback_reason"])
            self.assertIn("gen_tripo_get_credit_balance(include_raw=False)", " ".join(paid_evidence_contract["wallet_evidence_review_steps"]))
            self.assertIn("--mesh-wallet-evidence-recorded", paid_evidence_contract["wallet_evidence_receipt_command_template"])
            self.assertIn("--record-masked-tripo-wallet-evidence", paid_evidence_contract["mesh_wallet_evidence_receipt_command_template"])
            self.assertIn("--record-masked-uthana-allowance-evidence", paid_evidence_contract["animation_allowance_receipt_command_template"])
            self.assertIn("--record-explicit-spend-and-usage-approval", paid_evidence_contract["spend_confirmation_receipt_command_template"])
            self.assertEqual(len(paid_evidence_contract["operator_command_handoff"]), 3)
            self.assertEqual(paid_evidence_contract["operator_command_handoff"][0]["id"], "record_masked_tripo_wallet_evidence")
            self.assertEqual(paid_evidence_contract["operator_command_handoff"][1]["id"], "record_masked_uthana_allowance_evidence")
            self.assertEqual(paid_evidence_contract["operator_command_handoff"][2]["id"], "record_explicit_spend_and_usage_approval")
            self.assertFalse(paid_evidence_contract["operator_command_handoff"][0]["approval_flags_included"])
            self.assertFalse(paid_evidence_contract["operator_command_handoff"][1]["approval_flags_included"])
            self.assertTrue(paid_evidence_contract["operator_command_handoff"][2]["approval_flags_included"])
            self.assertIn("blueprint_mutation_evidence_contract", platform_context)
            blueprint_evidence_contract = platform_context["blueprint_mutation_evidence_contract"]
            self.assertEqual(blueprint_evidence_contract["schema"], "unreal_mcp_blueprint_mutation_evidence_review_receipt.v1")
            self.assertIn(blueprint_evidence_contract["state"], {"missing", "missing_evidence", "ready", "blocked"})
            self.assertEqual(blueprint_evidence_contract["receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
            self.assertEqual(
                blueprint_evidence_contract["receipt_required_command"],
                "python scripts\\write_blueprint_mutation_evidence_review.py",
            )
            self.assertEqual(len(blueprint_evidence_contract["operator_command_handoff"]), 3)
            self.assertEqual(blueprint_evidence_contract["operator_command_handoff"][0]["id"], "record_blueprint_pre_read_evidence")
            self.assertEqual(blueprint_evidence_contract["operator_command_handoff"][1]["id"], "record_blueprint_compile_plan")
            self.assertEqual(blueprint_evidence_contract["operator_command_handoff"][2]["id"], "record_blueprint_readback_plan")
            self.assertTrue(blueprint_evidence_contract["operator_command_handoff"][0]["no_blueprint_mutation"])
            self.assertFalse(blueprint_evidence_contract["pre_read_evidence_recorded"])
            self.assertFalse(blueprint_evidence_contract["compile_plan_recorded"])
            self.assertFalse(blueprint_evidence_contract["readback_plan_recorded"])
            self.assertTrue(blueprint_evidence_contract["no_editor_mutation"])
            self.assertTrue(blueprint_evidence_contract["no_blueprint_mutation"])
            self.assertTrue(blueprint_evidence_contract["no_compile"])
            self.assertTrue(blueprint_evidence_contract["no_save"])
            self.assertTrue(blueprint_evidence_contract["no_pie"])
            self.assertTrue(blueprint_evidence_contract["no_provider_call"])
            self.assertEqual(platform_context["blueprint_mutation_evidence_receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
            self.assertEqual(
                platform_context["blueprint_mutation_evidence_receipt_required_command"],
                "python scripts\\write_blueprint_mutation_evidence_review.py",
            )
            self.assertEqual(len(platform_context["blueprint_mutation_operator_command_handoff"]), 3)
            self.assertEqual(platform_context["blueprint_mutation_operator_command_handoff"][0]["id"], "record_blueprint_pre_read_evidence")
            self.assertFalse(platform_context["blueprint_pre_read_evidence_recorded"])
            self.assertFalse(platform_context["blueprint_compile_plan_recorded"])
            self.assertFalse(platform_context["blueprint_readback_plan_recorded"])
            self.assertIn("blueprint_mutation_evidence_receipt_state", platform_context["platform_stability_review"])
            self.assertEqual(
                platform_context["platform_stability_review"]["blueprint_mutation_evidence_receipt_path"],
                "Saved\\BlueprintMutationEvidence\\last_review_receipt.json",
            )
            self.assertEqual(
                platform_context["platform_stability_review"]["blueprint_mutation_evidence_required_command"],
                "python scripts\\write_blueprint_mutation_evidence_review.py",
            )
            self.assertEqual(len(platform_context["platform_stability_review"]["blueprint_mutation_operator_command_handoff"]), 3)
            self.assertEqual(
                platform_context["platform_stability_review"]["blueprint_mutation_operator_command_handoff"][0]["id"],
                "record_blueprint_pre_read_evidence",
            )
            self.assertFalse(platform_context["platform_stability_review"]["blueprint_mutation_pre_read_evidence_recorded"])
            self.assertFalse(platform_context["platform_stability_review"]["blueprint_mutation_compile_plan_recorded"])
            self.assertFalse(platform_context["platform_stability_review"]["blueprint_mutation_readback_plan_recorded"])
            self.assertTrue(platform_context["platform_stability_review"]["blueprint_mutation_evidence_no_blueprint_mutation"])
            self.assertTrue(platform_context["platform_stability_review"]["blueprint_mutation_evidence_no_compile"])
            self.assertIn("paid_animation_missing_gate_count", platform_context)
            self.assertIn("last_plugin_build_status", platform_context)
            self.assertIn("last_plugin_build_warning_count", platform_context)
            self.assertIn("last_plugin_build_warning_categories", platform_context)
            self.assertIn("last_plugin_build_warning_severity", platform_context)
            self.assertTrue(platform_context["paid_provider_smoke_contract_ok"])
            self.assertFalse(platform_context["paid_provider_smoke_default_ci_network_required"])
            self.assertTrue(platform_context["paid_provider_smoke_manual_network_required"])
            self.assertFalse(platform_context["paid_provider_smoke_manual_spend_required"])
            self.assertIn("RUN_UNREAL_MCP_PAID_PROVIDER_SMOKE", platform_context["paid_provider_smoke_required_env_vars"])
            self.assertIn("gen_uthana_get_account", platform_context["paid_provider_smoke_no_spend_tools"])
            self.assertIn("paid_provider_generative_smoke", platform_context["paid_provider_smoke_manual_command"])
            self.assertIn("ready_for_platform_stability", platform_context)
            self.assertIn("ready_for_wip_promotion", platform_context)
            self.assertIn("ready_for_blueprint_mutation", platform_context)
            self.assertFalse(platform_context["ready_for_blueprint_mutation"])
            self.assertIn("platform_missing_gate_count", platform_context)
            self.assertIn("wip_promotion_missing_gate_count", platform_context)
            self.assertIn("dirty_state_grouped_for_promotion", platform_context["wip_promotion_missing_gate_preview"])
            self.assertEqual(platform_context["test_lane_state"], "ok")
            self.assertTrue(platform_context["test_lane_default_ci_safe"])
            self.assertGreaterEqual(platform_context["test_lane_offline_count"], 80)
            self.assertGreaterEqual(platform_context["test_lane_live_bridge_manual_count"], 4)
            self.assertGreaterEqual(platform_context["test_lane_paid_provider_count"], 1)
            self.assertEqual(platform_context["test_lane_violation_count"], 0)
            self.assertIn("no_mutation_test_state", platform_context)
            self.assertIn(platform_context["no_mutation_test_state"], {"ok", "missing", "blocked"})
            self.assertIn("no_mutation_test_ok", platform_context)
            self.assertIn("no_mutation_test_mutation_count", platform_context)
            self.assertIn("no_mutation_test_exit_code", platform_context)
            self.assertIn("no_mutation_test_tracked_file_count", platform_context)
            self.assertIn("no_mutation_test_snapshot_digest_match", platform_context)
            self.assertIn("no_mutation_test_snapshot_scope", platform_context)
            self.assertIn("no_mutation_test_snapshot_hash_algorithm", platform_context)
            self.assertEqual(platform_context["no_mutation_test_required_command"], "python scripts\\run_no_mutation_unittest.py")
            self.assertEqual(platform_context["no_mutation_test_operator_command_handoff_count"], 1)
            self.assertEqual(platform_context["no_mutation_test_operator_command_handoff_ids"], ["run_no_mutation_unittest"])
            self.assertEqual(
                platform_context["no_mutation_test_operator_command_handoff"][0]["command"],
                "python scripts\\run_no_mutation_unittest.py",
            )
            self.assertTrue(platform_context["no_mutation_test_operator_command_handoff"][0]["no_editor_mutation"])
            self.assertEqual(platform_context["high_value_wrapper_state"], "ok")
            self.assertTrue(platform_context["high_value_wrapper_ok"])
            self.assertEqual(platform_context["high_value_wrapper_capability_count"], 10)
            self.assertEqual(platform_context["high_value_wrapper_covered_capability_count"], 10)
            self.assertEqual(platform_context["high_value_wrapper_failing_capability_count"], 0)
            self.assertGreaterEqual(platform_context["high_value_wrapper_command_count"], 14)
            self.assertEqual(
                platform_context["high_value_wrapper_schema_command_count"],
                platform_context["high_value_wrapper_schema_covered_command_count"],
            )
            self.assertIn("set_behavior_tree_blackboard", platform_context["high_value_wrapper_command_preview"])
            self.assertIn("add_get_random_reachable_point_node", platform_context["high_value_wrapper_command_preview"])
            self.assertEqual(platform_context["high_value_wrapper_roadmap_priority_count"], 10)
            self.assertEqual(platform_context["high_value_wrapper_roadmap_priority_covered_count"], 10)
            self.assertEqual(platform_context["high_value_wrapper_roadmap_priority_missing_count"], 0)
            self.assertIn(
                "behavior_tree_blackboard_assignment",
                platform_context["high_value_wrapper_roadmap_priority_preview"],
            )
            self.assertIn(
                "behavior_tree_task_graph_primitives",
                platform_context["high_value_wrapper_roadmap_priority_preview"],
            )
            self.assertEqual(platform_context["high_value_wrapper_roadmap_priority_missing_preview"], [])
            self.assertEqual(platform_context["high_value_wrapper_operator_command_handoff_count"], 2)
            self.assertEqual(
                platform_context["high_value_wrapper_operator_command_handoff_ids"],
                ["run_high_value_wrapper_coverage_audit", "run_high_value_wrapper_offline_tests"],
            )
            self.assertEqual(
                platform_context["high_value_wrapper_operator_command_handoff"][0]["id"],
                "run_high_value_wrapper_coverage_audit",
            )
            self.assertTrue(platform_context["high_value_wrapper_operator_command_handoff"][0]["no_editor_mutation"])
            self.assertEqual(platform_context["high_value_wrapper_audit_tool"], "scripts/audit_high_value_wrapper_coverage.py")
            self.assertIn("build_wrapper_status", platform_context)
            self.assertIn("build_health", platform_context)
            self.assertIn("build_wrapper_missing_reference_count", platform_context)
            self.assertNotIn("api_key_masked", platform_context)
            self.assertTrue(platform_context["no_editor_mutation"])
            self.assertTrue(platform_context["no_provider_spend"])
            self.assertTrue(platform_context["stop_before_editor_provider_or_blueprint"])
            self.assertTrue(workflow_actions["review_live_editor_bridge_gate"]["enabled"])
            self.assertFalse(workflow_actions["review_live_editor_bridge_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_live_editor_bridge_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_live_editor_bridge_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_live_editor_bridge_gate"]["input_source"],
                "outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context plus outputs.next_safe_step, execution_review, and runtime_review",
            )
            live_editor_context = workflow_actions["review_live_editor_bridge_gate"]["target_live_editor_context"]
            self.assertEqual(live_editor_context["state"], "blocked")
            self.assertIsInstance(live_editor_context["bridge_ready"], bool)
            self.assertIn(live_editor_context["bridge_ping_receipt_state"], {"missing", "ok", "blocked"})
            self.assertEqual(live_editor_context["bridge_ping_receipt_path"], "Saved\\BridgePing\\last_ping_receipt.json")
            self.assertEqual(live_editor_context["bridge_ping_required_command"], "python scripts\\bridge_ping.py")
            self.assertEqual(live_editor_context["bridge_ping_operator_command_handoff_count"], 1)
            self.assertEqual(live_editor_context["bridge_ping_operator_command_handoff_ids"], ["verify_unreal_bridge_ping"])
            self.assertTrue(live_editor_context["bridge_ping_operator_command_handoff"][0]["requires_unreal_editor"])
            self.assertIn("successful_bridge_ping", live_editor_context)
            self.assertFalse(live_editor_context["editor_mutation_allowed"])
            self.assertEqual(live_editor_context["queue_count"], 1)
            self.assertEqual(live_editor_context["queued_action_count"], 2)
            self.assertEqual(live_editor_context["bridge_blocked_count"], 1)
            self.assertEqual(live_editor_context["next_action_id"], "create_placeholder_folder")
            self.assertEqual(live_editor_context["next_action_tool"], "create_folder")
            self.assertFalse(live_editor_context["can_execute_now"])
            self.assertFalse(live_editor_context["can_verify_now"])
            self.assertIn("unreal_bridge_reachable", live_editor_context["missing_gate_preview"])
            self.assertEqual(live_editor_context["preflight_tool"], "scripts/audit_ide_companion_readiness.py")
            self.assertEqual(live_editor_context["queue_tool"], "skill_compile_ide_companion_editor_queue")
            self.assertEqual(live_editor_context["evidence_tool"], "skill_record_ide_companion_evidence")
            self.assertTrue(live_editor_context["future_editor_mutation_requires_bridge"])
            self.assertTrue(live_editor_context["no_editor_mutation"])
            self.assertTrue(live_editor_context["no_pie_run"])
            self.assertTrue(live_editor_context["stop_before_editor_or_pie"])
            self.assertTrue(workflow_actions["review_wip_promotion_gate"]["enabled"])
            self.assertFalse(workflow_actions["review_wip_promotion_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_wip_promotion_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_wip_promotion_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_wip_promotion_gate"]["input_source"],
                "outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context plus wrapper and test-lane audits",
            )
            promotion_context = workflow_actions["review_wip_promotion_gate"]["target_wip_promotion_context"]
            self.assertEqual(promotion_context["state"], "blocked")
            self.assertEqual(promotion_context["current_branch"], platform_context["current_branch"])
            self.assertEqual(promotion_context["branch_role"], platform_context["branch_role"])
            self.assertEqual(promotion_context["working_branch_ok"], platform_context["working_branch_ok"])
            self.assertEqual(promotion_context["source_branch_policy"], "wip")
            self.assertEqual(promotion_context["stable_branch_policy"], "main")
            self.assertIn("working_branch_is_wip", [row["gate"] for row in promotion_context["gate_preview"]])
            self.assertGreaterEqual(promotion_context["gate_count"], 5)
            self.assertGreaterEqual(promotion_context["missing_gate_count"], 1)
            self.assertIn("dirty_state_grouped_for_promotion", promotion_context["missing_gate_preview"])
            self.assertIn("promotion_resolution_preview", promotion_context)
            self.assertEqual(promotion_context["readiness_repair_queue"], platform_context["readiness_repair_queue"])
            self.assertEqual(promotion_context["readiness_repair_recommended_next"], repair_queue["recommended_next"])
            self.assertEqual(
                promotion_context["readiness_repair_action_count"],
                platform_context["readiness_repair_queue"]["action_count"],
            )
            self.assertIn(repair_queue["next_action"]["gate"], {item["gate"] for item in promotion_context["readiness_repair_action_preview"]})
            self.assertIn(
                "dirty_state_grouped_for_promotion",
                {item["blocker"] for item in promotion_context["promotion_resolution_preview"]},
            )
            self.assertEqual(
                promotion_context["target_promotion_blocker_resolution"]["blocker"],
                "dirty_state_grouped_for_promotion",
            )
            self.assertEqual(
                promotion_context["target_promotion_blocker_resolution"]["recommended_strategy"],
                "group_dirty_state_for_promotion",
            )
            self.assertEqual(promotion_context["tool_count"], platform_context["tool_count"])
            self.assertEqual(promotion_context["recorded_count"], platform_context["recorded_count"])
            self.assertEqual(promotion_context["dirty_risk"], platform_context["dirty_risk"])
            self.assertEqual(promotion_context["dirty_group_count"], platform_context["dirty_group_count"])
            self.assertEqual(promotion_context["dirty_group_preview"], platform_context["dirty_group_preview"])
            self.assertEqual(promotion_context["dirty_grouping_required"], platform_context["dirty_grouping_required"])
            self.assertEqual(promotion_context["dirty_promotion_contract"], platform_context["dirty_promotion_contract"])
            self.assertEqual(
                promotion_context["dirty_promotion_review_batch_count"],
                platform_context["dirty_promotion_contract"]["review_batch_count"],
            )
            self.assertEqual(
                promotion_context["dirty_promotion_review_receipt_state"],
                platform_context["dirty_promotion_contract"]["review_receipt_state"],
            )
            self.assertEqual(
                promotion_context["dirty_promotion_review_receipt_path"],
                "Saved\\DirtyPromotionReview\\last_review_receipt.json",
            )
            self.assertEqual(
                promotion_context["dirty_promotion_review_receipt_required_command"],
                "python scripts\\write_dirty_promotion_review.py",
            )
            self.assertIn("one coherent dirty group", promotion_context["dirty_promotion_batch_policy"])
            self.assertIn("generated/local artifacts", promotion_context["dirty_promotion_artifact_policy"])
            self.assertIn("run_focused_tests_for_each_candidate_batch", promotion_context["dirty_promotion_safe_next_steps"])
            self.assertEqual(
                promotion_context["dirty_promotion_evidence_review_matrix_count"],
                platform_context["dirty_promotion_contract"]["evidence_review_matrix_count"],
            )
            self.assertEqual(
                promotion_context["dirty_promotion_evidence_unresolved_count"],
                platform_context["dirty_promotion_contract"]["evidence_unresolved_count"],
            )
            self.assertIn("receipt records the review target only", promotion_context["dirty_promotion_evidence_review_policy"])
            self.assertIn("target_review_group", promotion_context)
            self.assertIn("target_review_status", promotion_context)
            self.assertIn("target_review_recorded_evidence_count", promotion_context)
            self.assertIn("target_review_human_approval_recorded", promotion_context)
            self.assertIn("target_review_missing_evidence_preview", promotion_context)
            self.assertIn("target_review_required_evidence_preview", promotion_context)
            self.assertIn("target_review_decision_prompt_preview", promotion_context)
            self.assertIn("target_review_receipt_command_template", promotion_context)
            self.assertIn("target_review_approval_receipt_command_template", promotion_context)
            self.assertIn("target_review_receipt_command_policy", promotion_context)
            self.assertIn("target_review_operator_command_handoff", promotion_context)
            self.assertEqual(len(promotion_context["target_review_operator_command_handoff"]), 2)
            self.assertFalse(promotion_context["target_review_operator_command_handoff"][0]["approval_flag_included"])
            self.assertTrue(promotion_context["target_review_operator_command_handoff"][1]["approval_flag_included"])
            self.assertIn("target_review_focused_test_command_handoff", promotion_context)
            self.assertGreaterEqual(len(promotion_context["target_review_focused_test_command_handoff"]), 1)
            self.assertEqual(promotion_context["target_review_focused_test_command_handoff"][0]["command_kind"], "local_validation")
            self.assertTrue(promotion_context["target_review_focused_test_command_handoff"][0]["no_git_mutation"])
            self.assertIn("target_review_pending_human_approval_only", promotion_context)
            self.assertIn("target_review_human_approval_command_handoff", promotion_context)
            self.assertIn("--target-owner-or-source", promotion_context["target_review_receipt_command_template"])
            self.assertNotIn("--target-human-approval-recorded", promotion_context["target_review_receipt_command_template"])
            self.assertIn("--target-human-approval-recorded", promotion_context["target_review_approval_receipt_command_template"])
            self.assertIn("target_review_focused_test_command_preview", promotion_context)
            self.assertEqual(
                promotion_context["target_review_group"],
                platform_context["dirty_promotion_contract"]["target_review_group"],
            )
            self.assertEqual(
                promotion_context["target_review_source"],
                platform_context["dirty_promotion_contract"]["target_review_source"],
            )
            if promotion_context["target_review_group"]:
                self.assertGreaterEqual(promotion_context["target_review_missing_evidence_count"], 1)
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    promotion_context["target_review_missing_evidence_preview"],
                )
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    promotion_context["target_review_required_evidence_preview"],
                )
                self.assertTrue(any("promotion_intent" in prompt for prompt in promotion_context["target_review_decision_prompt_preview"]))
                self.assertFalse(promotion_context["target_review_promotion_allowed_after_receipt"])
            if promotion_context["dirty_promotion_evidence_review_matrix_preview"]:
                self.assertIn("missing_evidence", promotion_context["dirty_promotion_evidence_review_matrix_preview"][0])
                self.assertFalse(promotion_context["dirty_promotion_evidence_review_matrix_preview"][0]["promotion_allowed"])
            self.assertGreaterEqual(promotion_context["dirty_promotion_focused_test_command_count"], 1)
            self.assertIn("dirty_promotion_focused_test_command_preview", promotion_context)
            self.assertIn("explicit human approval", promotion_context["dirty_promotion_candidate_batch_review_policy"])
            self.assertIn("focused_test_commands", promotion_context["dirty_promotion_review_batch_preview"][0])
            self.assertFalse(promotion_context["dirty_promotion_review_batch_preview"][0]["promotion_allowed_after_receipt"])
            self.assertEqual(
                promotion_context["platform_stability_review_receipt_state"],
                platform_context["platform_stability_review"]["state"],
            )
            self.assertEqual(
                promotion_context["platform_stability_review_receipt_path"],
                "Saved\\PlatformStabilityReview\\last_review_receipt.json",
            )
            self.assertEqual(
                promotion_context["platform_stability_review_receipt_required_command"],
                "python scripts\\write_platform_stability_review.py",
            )
            self.assertEqual(
                promotion_context["dirty_promotion_recommended_next"],
                platform_context["dirty_promotion_contract"]["recommended_next"],
            )
            self.assertIn(
                "human_review_before_stage_commit_or_merge",
                promotion_context["dirty_promotion_required_evidence_preview"],
            )
            self.assertEqual(promotion_context["last_plugin_build_status"], platform_context["last_plugin_build_status"])
            self.assertEqual(promotion_context["last_plugin_build_warning_count"], platform_context["last_plugin_build_warning_count"])
            self.assertEqual(promotion_context["last_plugin_build_warning_severity"], platform_context["last_plugin_build_warning_severity"])
            self.assertEqual(promotion_context["build_wrapper_status"], platform_context["build_wrapper_status"])
            self.assertEqual(promotion_context["build_health"], platform_context["build_health"])
            self.assertEqual(promotion_context["build_wrapper_missing_reference_count"], platform_context["build_wrapper_missing_reference_count"])
            self.assertEqual(promotion_context["test_lane_violation_count"], 0)
            self.assertEqual(promotion_context["no_mutation_test_state"], platform_context["no_mutation_test_state"])
            self.assertEqual(promotion_context["no_mutation_test_ok"], platform_context["no_mutation_test_ok"])
            self.assertEqual(promotion_context["no_mutation_test_mutation_count"], platform_context["no_mutation_test_mutation_count"])
            self.assertEqual(promotion_context["no_mutation_test_exit_code"], platform_context["no_mutation_test_exit_code"])
            self.assertEqual(promotion_context["no_mutation_test_tracked_file_count"], platform_context["no_mutation_test_tracked_file_count"])
            self.assertEqual(
                promotion_context["no_mutation_test_snapshot_digest_match"],
                platform_context["no_mutation_test_snapshot_digest_match"],
            )
            self.assertEqual(promotion_context["no_mutation_test_snapshot_scope"], platform_context["no_mutation_test_snapshot_scope"])
            self.assertEqual(
                promotion_context["no_mutation_test_snapshot_hash_algorithm"],
                platform_context["no_mutation_test_snapshot_hash_algorithm"],
            )
            self.assertEqual(promotion_context["no_mutation_test_required_command"], "python scripts\\run_no_mutation_unittest.py")
            self.assertEqual(promotion_context["chat_base_url"], platform_context["chat_base_url"])
            self.assertEqual(promotion_context["chat_health_endpoint"], platform_context["chat_health_endpoint"])
            self.assertEqual(promotion_context["chat_tcp_ready"], platform_context["chat_tcp_ready"])
            self.assertEqual(promotion_context["chat_startup_command"], platform_context["chat_startup_command"])
            self.assertEqual(promotion_context["chat_cockpit_repair_contract"], platform_context["chat_cockpit_repair_contract"])
            self.assertEqual(promotion_context["chat_cockpit_repair_state"], platform_context["chat_cockpit_repair_contract"]["state"])
            self.assertIn("chat_history_http_200", promotion_context["chat_cockpit_required_evidence_preview"])
            self.assertIn("Start MCP server", promotion_context["chat_cockpit_startup_step_preview"][0])
            self.assertEqual(
                promotion_context["chat_cockpit_proof_command"],
                platform_context["chat_cockpit_repair_contract"]["proof_command"],
            )
            self.assertEqual(promotion_context["failing_wrapper_count"], 0)
            self.assertEqual(promotion_context["preflight_tool"], "scripts/audit_ide_companion_readiness.py")
            self.assertEqual(promotion_context["test_lane_tool"], "scripts/audit_test_lanes.py")
            self.assertEqual(promotion_context["wrapper_audit_tool"], "scripts/audit_high_value_wrapper_coverage.py")
            self.assertTrue(promotion_context["no_git_mutation"])
            self.assertTrue(promotion_context["stop_before_branch_stage_commit_or_merge"])
            self.assertTrue(workflow_actions["review_blueprint_mutation_gate"]["enabled"])
            self.assertFalse(workflow_actions["review_blueprint_mutation_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_blueprint_mutation_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_blueprint_mutation_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_blueprint_mutation_gate"]["input_source"],
                "outputs.readiness_policy.blueprint_mutation plus outputs.work_order_template and outputs.editor_queues",
            )
            blueprint_context = workflow_actions["review_blueprint_mutation_gate"]["target_blueprint_mutation_context"]
            self.assertEqual(blueprint_context["state"], "blocked")
            self.assertEqual(blueprint_context["readiness_state"], "blocked")
            self.assertFalse(blueprint_context["blueprint_mutation_allowed"])
            self.assertEqual(blueprint_context["target_phase"], "editor_implementation")
            self.assertEqual(blueprint_context["template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(blueprint_context["operation_count"], 2)
            self.assertEqual(blueprint_context["editor_operation_count"], 2)
            self.assertEqual(blueprint_context["bridge_required_operation_count"], 2)
            self.assertEqual(blueprint_context["compile_after_operation_count"], 2)
            self.assertEqual(blueprint_context["readback_after_operation_count"], 2)
            self.assertIn("set_behavior_tree_blackboard", blueprint_context["editor_operation_tool_preview"])
            self.assertEqual(blueprint_context["compile_check_count"], 1)
            self.assertEqual(blueprint_context["pie_validation_count"], 1)
            self.assertEqual(blueprint_context["evidence_requirement_count"], 2)
            self.assertEqual(blueprint_context["queue_count"], 1)
            self.assertEqual(blueprint_context["queued_action_count"], 2)
            self.assertEqual(blueprint_context["bridge_blocked_count"], 1)
            self.assertEqual(blueprint_context["missing_gate_count"], 3)
            self.assertIn("unreal_bridge_reachable", blueprint_context["missing_gate_preview"])
            self.assertIn("blueprint_pre_read_evidence", blueprint_context["missing_gate_preview"])
            self.assertIn("blueprint_readback_plan", blueprint_context["missing_gate_preview"])
            self.assertEqual(blueprint_context["evidence_required_count"], 3)
            self.assertIn("blueprint_pre_read", blueprint_context["evidence_required_preview"])
            self.assertEqual(blueprint_context["repair_queue_state"], platform_context["readiness_repair_queue"]["state"])
            self.assertEqual(
                blueprint_context["repair_queue_recommended_next"],
                platform_context["readiness_repair_queue"]["recommended_next"],
            )
            self.assertEqual(blueprint_context["evidence_receipt_path"], "Saved\\BlueprintMutationEvidence\\last_review_receipt.json")
            self.assertEqual(
                blueprint_context["evidence_receipt_required_command"],
                "python scripts\\write_blueprint_mutation_evidence_review.py",
            )
            self.assertEqual(len(blueprint_context["operator_command_handoff"]), 3)
            self.assertEqual(blueprint_context["operator_command_handoff"][0]["id"], "record_blueprint_pre_read_evidence")
            self.assertIn("--pre-read-evidence-recorded", blueprint_context["operator_command_handoff"][0]["command"])
            self.assertFalse(blueprint_context["pre_read_evidence_recorded"])
            self.assertFalse(blueprint_context["compile_plan_recorded"])
            self.assertFalse(blueprint_context["readback_plan_recorded"])
            self.assertEqual(blueprint_context["evidence_merge_policy"], "preserve_existing_evidence_unless_reset")
            self.assertTrue(blueprint_context["human_approval_required_before_blueprint_mutation"])
            self.assertTrue(blueprint_context["receipt_no_editor_mutation"])
            self.assertTrue(blueprint_context["receipt_no_blueprint_mutation"])
            self.assertTrue(blueprint_context["receipt_no_compile"])
            self.assertTrue(blueprint_context["receipt_no_save"])
            self.assertTrue(blueprint_context["receipt_no_provider_call"])
            self.assertEqual(blueprint_context["blueprint_repair_action_count"], 3)
            self.assertEqual(
                blueprint_context["blueprint_repair_gate_preview"],
                ["blueprint_pre_read_evidence", "blueprint_compile_plan", "blueprint_readback_plan"],
            )
            self.assertEqual(blueprint_context["blueprint_next_repair_action_id"], "record_blueprint_pre_read_evidence")
            self.assertEqual(blueprint_context["blueprint_next_repair_gate"], "blueprint_pre_read_evidence")
            self.assertEqual(blueprint_context["blueprint_next_repair_tool"], "chat_get_cockpit_overview")
            self.assertTrue(blueprint_context["blueprint_repair_action_preview"][0]["requires_bridge"])
            self.assertTrue(blueprint_context["blueprint_repair_action_preview"][0]["no_blueprint_mutation"])
            self.assertEqual(
                blueprint_context["blueprint_repair_action_preview"][0]["receipt_path"],
                "Saved\\BlueprintMutationEvidence\\last_review_receipt.json",
            )
            self.assertIn(
                "--pre-read-evidence-recorded",
                blueprint_context["blueprint_repair_action_preview"][0]["receipt_command_template"],
            )
            self.assertEqual(
                blueprint_context["blueprint_repair_action_preview"][0]["operator_command_handoff"][0]["id"],
                "record_blueprint_pre_read_evidence",
            )
            self.assertIn("review_steps_preview", blueprint_context["blueprint_repair_action_preview"][0])
            self.assertIn(
                "Use the Blueprint mutation gate",
                blueprint_context["blueprint_repair_action_preview"][0]["review_steps_preview"][0],
            )
            self.assertIn(
                "Use the Blueprint mutation gate",
                blueprint_context["blueprint_next_repair_review_steps_preview"][0],
            )
            self.assertIn(
                "blueprint_pre_read",
                blueprint_context["blueprint_repair_action_preview"][0]["evidence_required_preview"],
            )
            self.assertTrue(blueprint_context["pre_read_required"])
            self.assertTrue(blueprint_context["compile_plan_required"])
            self.assertTrue(blueprint_context["readback_plan_required"])
            self.assertTrue(blueprint_context["bridge_required"])
            self.assertEqual(blueprint_context["readiness_tool"], "gen_compile_ide_companion_readiness")
            self.assertEqual(blueprint_context["work_order_tool"], "skill_compile_ide_companion_work_order")
            self.assertEqual(blueprint_context["queue_tool"], "skill_compile_ide_companion_editor_queue")
            self.assertTrue(blueprint_context["requires_bridge"])
            self.assertTrue(blueprint_context["requires_compile_readback"])
            self.assertTrue(blueprint_context["stop_before_blueprint_mutation"])
            self.assertTrue(workflow_actions["review_bridge_wrapper_coverage"]["enabled"])
            self.assertFalse(workflow_actions["review_bridge_wrapper_coverage"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_bridge_wrapper_coverage"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_bridge_wrapper_coverage"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_bridge_wrapper_coverage"]["input_source"],
                "scripts/audit_high_value_wrapper_coverage.py plus scripts/bridge_command_audit.py",
            )
            bridge_wrapper_context = workflow_actions["review_bridge_wrapper_coverage"]["target_bridge_wrapper_context"]
            self.assertEqual(bridge_wrapper_context["schema"], "unreal_mcp_high_value_wrapper_coverage.v1")
            self.assertEqual(bridge_wrapper_context["state"], "ok")
            self.assertEqual(bridge_wrapper_context["status"], "OK")
            self.assertEqual(bridge_wrapper_context["capability_count"], 10)
            self.assertEqual(bridge_wrapper_context["covered_capability_count"], 10)
            self.assertEqual(bridge_wrapper_context["failing_capability_count"], 0)
            self.assertGreaterEqual(bridge_wrapper_context["command_count"], 14)
            self.assertEqual(bridge_wrapper_context["schema_command_count"], bridge_wrapper_context["command_count"])
            self.assertEqual(bridge_wrapper_context["schema_covered_command_count"], bridge_wrapper_context["schema_command_count"])
            self.assertIn("set_behavior_tree_blackboard", bridge_wrapper_context["command_preview"])
            self.assertIn("add_get_random_reachable_point_node", bridge_wrapper_context["command_preview"])
            self.assertEqual(bridge_wrapper_context["roadmap_priority_count"], 10)
            self.assertEqual(bridge_wrapper_context["roadmap_priority_covered_count"], 10)
            self.assertEqual(bridge_wrapper_context["roadmap_priority_missing_count"], 0)
            self.assertIn("behavior_tree_blackboard_assignment", bridge_wrapper_context["roadmap_priority_preview"])
            self.assertIn("behavior_tree_task_graph_primitives", bridge_wrapper_context["roadmap_priority_preview"])
            self.assertEqual(bridge_wrapper_context["roadmap_priority_missing_preview"], [])
            self.assertEqual(bridge_wrapper_context["operator_command_handoff_count"], 2)
            self.assertEqual(
                bridge_wrapper_context["operator_command_handoff_ids"],
                ["run_high_value_wrapper_coverage_audit", "run_high_value_wrapper_offline_tests"],
            )
            self.assertEqual(
                bridge_wrapper_context["operator_command_handoff"][1]["command"],
                "python -m unittest unreal_mcp_server.tests.test_phase7_bridge_command_audit unreal_mcp_server.tests.test_phase1_high_value_wrapper_coverage",
            )
            self.assertFalse(bridge_wrapper_context["operator_command_handoff"][1]["requires_bridge"])
            self.assertTrue(bridge_wrapper_context["operator_command_handoff"][1]["no_git_mutation"])
            self.assertEqual(bridge_wrapper_context["audit_tool"], "scripts/audit_high_value_wrapper_coverage.py")
            self.assertEqual(bridge_wrapper_context["bridge_registry_tool"], "scripts/bridge_command_audit.py")
            self.assertFalse(bridge_wrapper_context["requires_bridge"])
            self.assertTrue(bridge_wrapper_context["no_editor_mutation"])
            self.assertTrue(workflow_actions["review_test_lane_gates"]["enabled"])
            self.assertFalse(workflow_actions["review_test_lane_gates"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_test_lane_gates"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_test_lane_gates"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_test_lane_gates"]["input_source"],
                "scripts/audit_test_lanes.py plus docs/ci-smoke.md",
            )
            test_lane_context = workflow_actions["review_test_lane_gates"]["target_test_lane_context"]
            self.assertEqual(test_lane_context["schema"], "unreal_mcp_test_lane_audit.v1")
            self.assertEqual(test_lane_context["state"], "ok")
            self.assertEqual(test_lane_context["status"], "OK")
            self.assertEqual(test_lane_context["default_discovery_pattern"], "test_*.py")
            self.assertGreaterEqual(test_lane_context["offline_count"], 80)
            self.assertGreaterEqual(test_lane_context["live_bridge_manual_count"], 4)
            self.assertGreaterEqual(test_lane_context["paid_provider_count"], 1)
            self.assertEqual(test_lane_context["violation_count"], 0)
            self.assertEqual(test_lane_context["audit_tool"], "scripts/audit_test_lanes.py")
            self.assertEqual(test_lane_context["ci_doc"], "docs/ci-smoke.md")
            self.assertTrue(test_lane_context["default_ci_safe"])
            self.assertEqual(test_lane_context["no_mutation_receipt_schema"], "unreal_mcp_no_mutation_unittest_receipt.v1")
            self.assertIn(test_lane_context["no_mutation_state"], {"ok", "missing", "blocked"})
            self.assertIn("no_mutation_status", test_lane_context)
            self.assertIn("no_mutation_mutation_count", test_lane_context)
            self.assertIn("no_mutation_tracked_file_count", test_lane_context)
            self.assertIn("no_mutation_snapshot_digest_match", test_lane_context)
            self.assertIn("no_mutation_snapshot_scope", test_lane_context)
            self.assertIn("no_mutation_snapshot_hash_algorithm", test_lane_context)
            self.assertEqual(test_lane_context["no_mutation_required_command"], "python scripts\\run_no_mutation_unittest.py")
            self.assertEqual(test_lane_context["no_mutation_operator_command_handoff_count"], 1)
            self.assertEqual(test_lane_context["no_mutation_operator_command_handoff_ids"], ["run_no_mutation_unittest"])
            self.assertEqual(
                test_lane_context["no_mutation_operator_command_handoff"][0]["receipt_path"],
                "Saved\\NoMutationTest\\last_run_receipt.json",
            )
            self.assertFalse(test_lane_context["no_mutation_operator_command_handoff"][0]["requires_bridge"])
            self.assertFalse(test_lane_context["requires_bridge"])
            self.assertTrue(test_lane_context["future_bridge_required"])
            self.assertTrue(test_lane_context["future_spend_required"])
            self.assertTrue(test_lane_context["no_editor_mutation"])
            self.assertTrue(workflow_actions["review_provider_config_gate"]["enabled"])
            self.assertFalse(workflow_actions["review_provider_config_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_provider_config_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_provider_config_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_provider_config_gate"]["input_source"],
                "outputs.workflow_actions.review_platform_preflight_gate.target_platform_preflight_context plus provider repair and secret contracts",
            )
            provider_config_context = workflow_actions["review_provider_config_gate"]["target_provider_config_context"]
            self.assertEqual(provider_config_context["schema"], "unreal_mcp_provider_config_gate_context.v1")
            self.assertIn(provider_config_context["state"], {"ready", "blocked"})
            self.assertEqual(provider_config_context["provider"], "tripo")
            self.assertEqual(provider_config_context["animation_provider"], "uthana")
            self.assertIn(provider_config_context["provider_config_review_receipt_state"], {"missing", "ready", "missing_keys", "blocked"})
            self.assertEqual(provider_config_context["provider_config_review_receipt_path"], "Saved\\ProviderConfigReview\\last_review_receipt.json")
            self.assertEqual(provider_config_context["provider_config_review_receipt_required_command"], "python scripts\\write_provider_config_review.py")
            self.assertEqual(provider_config_context["provider_config_operator_command_handoff_count"], 1)
            self.assertEqual(provider_config_context["provider_config_operator_command_handoff_ids"], ["write_provider_config_review_receipt"])
            self.assertFalse(provider_config_context["provider_config_operator_command_handoff"][0]["requires_bridge"])
            self.assertFalse(provider_config_context["provider_config_operator_command_handoff"][0]["requires_spend"])
            self.assertTrue(provider_config_context["provider_config_operator_command_handoff"][0]["no_task_submission"])
            self.assertIn(provider_config_context["recommended_next"], {
                "configure_tripo_provider_secret",
                "configure_uthana_provider_secret",
                "write_provider_config_review_receipt",
                "record_wallet_or_allowance_evidence",
            })
            self.assertEqual(provider_config_context["config_tool"], "gen_get_provider_config")
            self.assertEqual(provider_config_context["save_tool"], "gen_save_provider_config")
            self.assertIn("<TRIPO_API_KEY>", provider_config_context["tripo_store_command_template"])
            self.assertIn("<UTHANA_API_KEY>", provider_config_context["uthana_store_command_template"])
            self.assertIn("gen_uthana_get_account", provider_config_context["animation_allowance_tools"])
            self.assertFalse(provider_config_context["raw_key_returned"])
            self.assertTrue(provider_config_context["masked_status_only"])
            self.assertTrue(provider_config_context["no_raw_key"])
            self.assertTrue(provider_config_context["no_provider_call"])
            self.assertTrue(provider_config_context["no_wallet_check"])
            self.assertTrue(provider_config_context["no_credit_reservation"])
            self.assertTrue(provider_config_context["no_spend_confirmation"])
            self.assertTrue(provider_config_context["no_editor_mutation"])
            self.assertTrue(provider_config_context["stop_before_provider_call"])
            self.assertNotIn("api_key_masked", json.dumps(provider_config_context))
            self.assertTrue(workflow_actions["refresh_companion_status"]["enabled"])
            self.assertTrue(workflow_actions["refresh_companion_status"]["requires_ledger"])
            self.assertEqual(workflow_actions["refresh_companion_status"]["tool"], "skill_compile_ide_companion_status")
            self.assertEqual(
                workflow_actions["refresh_companion_status"]["input_source"],
                "matching_ide_companion_ledger plus outputs.readiness_policy and outputs.evidence_recording",
            )
            self.assertIn("current_blockers", workflow_actions["refresh_companion_status"]["arguments"])
            status_context = workflow_actions["refresh_companion_status"]["target_status_context"]
            self.assertEqual(status_context["session_name"], "ide-companion")
            self.assertTrue(status_context["has_session_plan"])
            self.assertEqual(status_context["session_plan_phase_count"], 3)
            self.assertEqual(status_context["event_count"], 3)
            self.assertEqual(status_context["completed_phase_count"], 1)
            self.assertEqual(status_context["next_phase"], "editor_implementation")
            self.assertEqual(status_context["next_tool"], "skill_compile_ide_companion_editor_queue")
            self.assertEqual(status_context["readiness_state"], "blocked")
            self.assertEqual(status_context["blocking_gate_count"], 1)
            self.assertEqual(status_context["queue_count"], 1)
            self.assertEqual(status_context["evidence_item_count"], 17)
            self.assertEqual(status_context["generated_asset_count"], 2)
            self.assertEqual(status_context["runtime_review_state"], "blocked")
            self.assertTrue(status_context["requires_session_plan"])
            self.assertTrue(status_context["stop_before_editor_or_provider"])
            self.assertTrue(workflow_actions["generate_work_order"]["enabled"])
            self.assertTrue(workflow_actions["generate_work_order"]["requires_ledger"])
            self.assertEqual(workflow_actions["generate_work_order"]["tool"], "skill_compile_ide_companion_work_order")
            self.assertEqual(
                workflow_actions["generate_work_order"]["input_source"],
                "matching_ide_companion_ledger plus outputs.workflow_actions.refresh_companion_status.target_status_context",
            )
            self.assertEqual(workflow_actions["generate_work_order"]["arguments"]["target_phase"], "editor_implementation")
            work_order_context = workflow_actions["generate_work_order"]["target_work_order_context"]
            self.assertEqual(work_order_context["session_name"], "ide-companion")
            self.assertTrue(work_order_context["has_session_plan"])
            self.assertTrue(work_order_context["has_status_receipt"])
            self.assertEqual(work_order_context["target_phase"], "editor_implementation")
            self.assertEqual(work_order_context["next_phase"], "editor_implementation")
            self.assertEqual(work_order_context["readiness_state"], "blocked")
            self.assertEqual(work_order_context["blocking_gate_count"], 1)
            self.assertEqual(work_order_context["status_completed_phase_count"], 1)
            self.assertEqual(work_order_context["template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(work_order_context["operation_count"], 2)
            self.assertEqual(work_order_context["editor_operation_count"], 2)
            self.assertEqual(work_order_context["bridge_required_operation_count"], 2)
            self.assertEqual(work_order_context["compile_after_operation_count"], 2)
            self.assertEqual(work_order_context["readback_after_operation_count"], 2)
            self.assertIn("blueprint_graph_wiring", work_order_context["editor_operation_type_preview"])
            self.assertEqual(work_order_context["compile_check_count"], 1)
            self.assertEqual(work_order_context["pie_validation_count"], 1)
            self.assertEqual(work_order_context["evidence_requirement_count"], 2)
            self.assertEqual(work_order_context["generated_animation_prompt_count"], 2)
            self.assertIn("A_EnemyScout_PatrolWalk", " ".join(work_order_context["generated_animation_prompt_preview"]))
            self.assertIn("uthana", work_order_context["generated_animation_provider_preview"])
            self.assertIn("gen_uthana_text_to_motion", work_order_context["generated_animation_tool_preview"])
            self.assertIn("animgraph_or_state_machine_reference", work_order_context["generated_animation_proof_required_preview"])
            self.assertEqual(work_order_context["estimated_uthana_motion_seconds"], 8)
            self.assertTrue(work_order_context["requires_session_plan"])
            self.assertTrue(work_order_context["prefers_status_receipt"])
            self.assertTrue(work_order_context["stop_before_editor_mutation"])
            self.assertTrue(workflow_actions["review_gameplay_template_plan"]["enabled"])
            self.assertTrue(workflow_actions["review_gameplay_template_plan"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_gameplay_template_plan"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_gameplay_template_plan"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_gameplay_template_plan"]["input_source"],
                "matching_ide_companion_ledger.latest_work_order.feature_template_work plus outputs.work_order_template",
            )
            self.assertTrue(workflow_actions["queue_gameplay_template_next_operation"]["enabled"])
            self.assertTrue(workflow_actions["queue_gameplay_template_next_operation"]["requires_ledger"])
            self.assertFalse(workflow_actions["queue_gameplay_template_next_operation"]["requires_bridge"])
            self.assertEqual(
                workflow_actions["queue_gameplay_template_next_operation"]["tool"],
                "skill_compile_ide_companion_editor_queue",
            )
            self.assertEqual(
                workflow_actions["queue_gameplay_template_next_operation"]["arguments"]["queue_name"],
                "gameplay_template_queue",
            )
            self.assertEqual(
                workflow_actions["queue_gameplay_template_next_operation"]["input_source"],
                "outputs.workflow_actions.review_gameplay_template_plan.target_gameplay_template_context plus matching_ide_companion_ledger.latest_work_order",
            )
            queue_template_context = workflow_actions["queue_gameplay_template_next_operation"]["target_gameplay_template_context"]
            self.assertEqual(queue_template_context["next_editor_operation_id"], "enemy_patrol_chase_attack_01")
            self.assertFalse(queue_template_context["can_queue_editor_work"])
            queue_compile_context = workflow_actions["queue_gameplay_template_next_operation"]["target_queue_context"]
            self.assertEqual(queue_compile_context["next_editor_operation_id"], "enemy_patrol_chase_attack_01")
            self.assertIn("set_behavior_tree_blackboard", queue_compile_context["next_editor_operation_tool_preview"])
            self.assertIn("graph_or_component_readback", queue_compile_context["next_editor_operation_required_after_preview"])
            gameplay_template_context = workflow_actions["review_gameplay_template_plan"]["target_gameplay_template_context"]
            self.assertEqual(gameplay_template_context["state"], "ready_to_review")
            self.assertEqual(gameplay_template_context["session_name"], "ide-companion")
            self.assertEqual(gameplay_template_context["target_phase"], "editor_implementation")
            self.assertEqual(gameplay_template_context["template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(gameplay_template_context["display_name"], "Enemy Patrol/Chase/Attack")
            self.assertEqual(gameplay_template_context["asset_count"], 3)
            self.assertEqual(gameplay_template_context["operation_count"], 2)
            self.assertEqual(gameplay_template_context["editor_operation_count"], 2)
            self.assertEqual(gameplay_template_context["bridge_required_operation_count"], 2)
            self.assertEqual(gameplay_template_context["compile_after_operation_count"], 2)
            self.assertEqual(gameplay_template_context["readback_after_operation_count"], 2)
            self.assertEqual(gameplay_template_context["compile_check_count"], 1)
            self.assertEqual(gameplay_template_context["pie_validation_count"], 1)
            self.assertEqual(gameplay_template_context["repair_instruction_count"], 1)
            self.assertEqual(gameplay_template_context["evidence_requirement_count"], 2)
            self.assertEqual(gameplay_template_context["completion_proof_gate_count"], 3)
            self.assertEqual(gameplay_template_context["completion_required_evidence_count"], 6)
            self.assertEqual(gameplay_template_context["operation_proof_contract_count"], 2)
            self.assertEqual(gameplay_template_context["generated_animation_prompt_count"], 2)
            self.assertIn("A_EnemyScout_ChaseRun", " ".join(gameplay_template_context["generated_animation_prompt_preview"]))
            self.assertIn("UE5 Manny", gameplay_template_context["generated_animation_target_skeleton_preview"])
            self.assertIn("gen_compile_generated_animation_evidence", gameplay_template_context["generated_animation_tool_preview"])
            self.assertIn("pie_motion_playback_or_viewport_proof", gameplay_template_context["generated_animation_proof_required_preview"])
            self.assertIn("Do not call Uthana", " ".join(gameplay_template_context["generated_animation_prompt_gate_policy"]))
            self.assertFalse(gameplay_template_context["generated_animation_paid_generation_allowed"])
            self.assertEqual(gameplay_template_context["generated_animation_paid_missing_gate_count"], 2)
            self.assertIn("wallet_evidence_recorded", gameplay_template_context["generated_animation_paid_missing_gate_preview"])
            self.assertIn("spend_confirmation_recorded", gameplay_template_context["generated_animation_paid_missing_gate_preview"])
            self.assertIn(
                "animation_provider_key_presence",
                gameplay_template_context["generated_animation_paid_evidence_required_preview"],
            )
            self.assertIn("gen_uthana_get_account", gameplay_template_context["generated_animation_safe_unblock_tool_preview"])
            self.assertTrue(gameplay_template_context["generated_animation_stop_before_provider"])
            execution_readiness = gameplay_template_context["execution_readiness"]
            self.assertEqual(
                execution_readiness["schema"],
                "unreal_mcp_gameplay_template_execution_readiness.v1",
            )
            self.assertEqual(execution_readiness["state"], "blocked")
            self.assertFalse(execution_readiness["can_queue_editor_work"])
            self.assertFalse(gameplay_template_context["can_queue_editor_work"])
            self.assertFalse(execution_readiness["can_mark_feature_complete"])
            self.assertFalse(gameplay_template_context["can_mark_feature_complete"])
            self.assertEqual(gameplay_template_context["execution_readiness_state"], "blocked")
            self.assertEqual(gameplay_template_context["execution_recommended_next"], "resolve_blueprint_mutation_gates")
            self.assertFalse(execution_readiness["editor_mutation_allowed"])
            self.assertEqual(execution_readiness["bridge_required_operation_count"], 2)
            self.assertEqual(execution_readiness["compile_after_operation_count"], 2)
            self.assertEqual(execution_readiness["readback_after_operation_count"], 2)
            self.assertEqual(execution_readiness["operation_proof_contract_count"], 2)
            self.assertEqual(execution_readiness["completion_required_evidence_count"], 6)
            self.assertIn("unreal_bridge_reachable", execution_readiness["missing_gate_preview"])
            self.assertIn("blueprint_pre_read_evidence", execution_readiness["required_before_preview"])
            self.assertIn("blueprint_compile_report", execution_readiness["required_after_preview"])
            self.assertIn("runtime proof contract evidence is incomplete", execution_readiness["stop_if_missing_preview"])
            self.assertEqual(execution_readiness["queue_tool"], "skill_compile_ide_companion_editor_queue")
            self.assertEqual(execution_readiness["evidence_tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(execution_readiness["next_editor_operation_id"], "enemy_patrol_chase_attack_01")
            self.assertEqual(execution_readiness["next_editor_operation_type"], "ai_blackboard_behavior_tree")
            self.assertIn("Blackboard keys TargetActor", execution_readiness["next_editor_operation_summary"])
            self.assertIn("set_behavior_tree_blackboard", execution_readiness["next_editor_operation_tool_preview"])
            self.assertFalse(execution_readiness["next_editor_operation_ready"])
            self.assertIn("unreal_bridge_reachable", execution_readiness["next_editor_operation_blocking_gate_preview"])
            self.assertIn("blueprint_pre_read_evidence", execution_readiness["next_editor_operation_required_before_preview"])
            self.assertIn("graph_or_component_readback", execution_readiness["next_editor_operation_required_after_preview"])
            self.assertIn("compile report missing or failed", execution_readiness["next_editor_operation_stop_if_missing_preview"])
            self.assertTrue(execution_readiness["requires_bridge_before_execution"])
            self.assertTrue(execution_readiness["requires_compile_readback"])
            self.assertTrue(execution_readiness["requires_runtime_proof"])
            self.assertTrue(execution_readiness["requires_ledger_evidence"])
            self.assertTrue(execution_readiness["no_editor_mutation"])
            self.assertTrue(execution_readiness["stop_before_feature_complete"])
            self.assertIn("graph_or_component_readback", gameplay_template_context["operation_proof_required_after_preview"])
            self.assertIn("AI", gameplay_template_context["ownership_domains"])
            self.assertIn("BP_EnemyScout", " ".join(gameplay_template_context["asset_preview"]))
            self.assertIn("Blackboard keys TargetActor", " ".join(gameplay_template_context["operation_preview"]))
            self.assertIn("ai_blackboard_behavior_tree", gameplay_template_context["editor_operation_type_preview"])
            self.assertIn("bp_connect_pins", gameplay_template_context["editor_operation_tool_preview"])
            self.assertIn("enemy_patrol_chase_attack_02", " ".join(gameplay_template_context["editor_operation_preview"]))
            self.assertEqual(gameplay_template_context["next_editor_operation_id"], "enemy_patrol_chase_attack_01")
            self.assertEqual(gameplay_template_context["next_editor_operation_type"], "ai_blackboard_behavior_tree")
            self.assertIn("set_behavior_tree_blackboard", gameplay_template_context["next_editor_operation_tool_preview"])
            self.assertTrue(gameplay_template_context["next_editor_operation_requires_bridge"])
            self.assertTrue(gameplay_template_context["next_editor_operation_requires_compile_after"])
            self.assertTrue(gameplay_template_context["next_editor_operation_requires_readback_after"])
            self.assertIn("unreal_bridge_reachable", gameplay_template_context["next_editor_operation_required_before_preview"])
            self.assertIn("graph_or_component_readback", gameplay_template_context["next_editor_operation_required_after_preview"])
            self.assertIn("Blueprint compile report", gameplay_template_context["evidence_preview"])
            self.assertIn("editor_operations_read_back", json.dumps(gameplay_template_context["completion_proof_gate_preview"]))
            self.assertFalse(gameplay_template_context["editor_mutation_allowed"])
            self.assertIn("unreal_bridge_reachable", gameplay_template_context["missing_gate_preview"])
            self.assertEqual(gameplay_template_context["plan_tool"], "skill_plan_gameplay_mechanic")
            self.assertEqual(gameplay_template_context["queue_tool"], "skill_compile_ide_companion_editor_queue")
            self.assertTrue(gameplay_template_context["requires_ledger"])
            self.assertTrue(gameplay_template_context["stop_before_editor_mutation"])
            self.assertTrue(workflow_actions["resume_companion_session"]["enabled"])
            self.assertTrue(workflow_actions["resume_companion_session"]["requires_ledger"])
            self.assertEqual(workflow_actions["resume_companion_session"]["tool"], "skill_resume_ide_companion_session")
            self.assertIn("ledger_path", workflow_actions["resume_companion_session"]["arguments"])
            resume_context = workflow_actions["resume_companion_session"]["target_resume_context"]
            self.assertEqual(resume_context["session_name"], "ide-companion")
            self.assertEqual(resume_context["event_count"], 3)
            self.assertEqual(resume_context["completed_phase_count"], 1)
            self.assertEqual(resume_context["latest_phase"], "editor_implementation")
            self.assertEqual(resume_context["next_phase"], "editor_implementation")
            self.assertEqual(resume_context["next_tool"], "skill_compile_ide_companion_editor_queue")
            self.assertEqual(resume_context["blocking_gate_count"], 1)
            self.assertIn("unreal_bridge_reachable", resume_context["blocking_gate_preview"])
            self.assertTrue(resume_context["stop_before_editor_mutation"])
            self.assertTrue(workflow_actions["show_companion_dashboard"]["enabled"])
            self.assertTrue(workflow_actions["show_companion_dashboard"]["requires_ledger"])
            self.assertEqual(workflow_actions["show_companion_dashboard"]["tool"], "skill_compile_ide_companion_dashboard")
            self.assertIn("ledger_path", workflow_actions["show_companion_dashboard"]["arguments"])
            dashboard_context = workflow_actions["show_companion_dashboard"]["target_dashboard_context"]
            self.assertEqual(dashboard_context["session_name"], "ide-companion")
            self.assertEqual(dashboard_context["event_count"], 3)
            self.assertEqual(dashboard_context["completed_phase_count"], 1)
            self.assertEqual(dashboard_context["readiness_state"], "blocked")
            self.assertEqual(dashboard_context["blocking_gate_count"], 1)
            self.assertEqual(dashboard_context["queued_action_count"], 2)
            self.assertEqual(dashboard_context["evidence_item_count"], 17)
            self.assertEqual(dashboard_context["generated_asset_state"], "blocked")
            self.assertEqual(dashboard_context["generated_asset_count"], 2)
            self.assertEqual(dashboard_context["runtime_review_state"], "blocked")
            self.assertEqual(dashboard_context["repair_loop_state"], "blocked")
            self.assertTrue(dashboard_context["stop_before_editor_mutation"])
            self.assertTrue(workflow_actions["show_evidence_ledger"]["enabled"])
            self.assertTrue(workflow_actions["show_evidence_ledger"]["requires_ledger"])
            self.assertEqual(workflow_actions["show_evidence_ledger"]["tool"], "chat_get_cockpit_ledger_detail")
            self.assertEqual(workflow_actions["show_evidence_ledger"]["arguments"]["limit"], 50)
            self.assertIn("ledger_path", workflow_actions["show_evidence_ledger"]["arguments"])
            self.assertEqual(workflow_actions["show_evidence_ledger"]["input_source"], "matching_ide_companion_ledger.ledger_path plus outputs.evidence_timeline")
            self.assertGreaterEqual(workflow_actions["show_evidence_ledger"]["target_evidence_event_count"], 2)
            ledger_context = workflow_actions["show_evidence_ledger"]["target_evidence_ledger_context"]
            self.assertEqual(ledger_context["latest_phase"], "editor_implementation")
            self.assertEqual(ledger_context["latest_evidence_type"], "failure")
            self.assertIn("TargetActor pin", ledger_context["latest_summary"])
            self.assertEqual(ledger_context["timeline_preview"][0]["phase_name"], "orient_to_project")
            self.assertTrue(workflow_actions["resolve_blockers"]["enabled"])
            self.assertTrue(workflow_actions["resolve_blockers"]["requires_ledger"])
            self.assertEqual(workflow_actions["resolve_blockers"]["tool"], "skill_compile_ide_companion_blocker_resolution")
            self.assertEqual(workflow_actions["resolve_blockers"]["input_source"], "outputs.blocker_resolutions")
            self.assertIn("unreal_bridge_reachable", workflow_actions["resolve_blockers"]["arguments"]["current_blockers"])
            self.assertEqual(workflow_actions["resolve_blockers"]["arguments"]["target_blocker"], "unreal_bridge_reachable")
            self.assertEqual(workflow_actions["resolve_blockers"]["arguments"]["preferred_strategy"], "unblock_first")
            self.assertEqual(workflow_actions["resolve_blockers"]["target_blocker_id"], "unreal_bridge_reachable")
            self.assertEqual(workflow_actions["resolve_blockers"]["target_blocker_resolution"]["recommended_tool"], "scripts/bridge_ping.py")
            self.assertTrue(workflow_actions["resolve_blockers"]["target_blocker_resolution"]["can_continue_offline"])
            self.assertTrue(workflow_actions["review_generated_asset_gate"]["enabled"])
            self.assertTrue(workflow_actions["review_generated_asset_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_generated_asset_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_generated_asset_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(workflow_actions["review_generated_asset_gate"]["input_source"], "outputs.generated_asset_quality_gate")
            self.assertEqual(workflow_actions["review_generated_asset_gate"]["arguments"]["session_name"], "ide-companion")
            self.assertEqual(workflow_actions["review_generated_asset_gate"]["arguments"]["limit"], 50)
            asset_review_context = workflow_actions["review_generated_asset_gate"]["target_generated_asset_review_context"]
            self.assertEqual(asset_review_context["state"], "blocked")
            self.assertEqual(asset_review_context["asset_count"], 2)
            self.assertEqual(asset_review_context["provider_pending_count"], 1)
            self.assertEqual(asset_review_context["import_pending_count"], 1)
            self.assertEqual(asset_review_context["quality_pending_count"], 0)
            self.assertEqual(asset_review_context["placeholder_count"], 1)
            self.assertEqual(asset_review_context["target_asset"]["id"], "asset_01")
            self.assertEqual(asset_review_context["target_asset"]["name"], "SM_ObjectiveBeacon")
            self.assertEqual(asset_review_context["target_asset"]["state"], "provider_pending")
            self.assertTrue(asset_review_context["stop_before_provider_or_import"])
            self.assertTrue(workflow_actions["review_generated_asset_lifecycle_gate"]["enabled"])
            self.assertTrue(workflow_actions["review_generated_asset_lifecycle_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_generated_asset_lifecycle_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_generated_asset_lifecycle_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_generated_asset_lifecycle_gate"]["input_source"],
                "outputs.generated_asset_lifecycles plus outputs.generated_asset_quality_gate",
            )
            lifecycle_context = workflow_actions["review_generated_asset_lifecycle_gate"]["target_generated_asset_lifecycle_context"]
            self.assertEqual(lifecycle_context["schema"], "unreal_mcp_chat_generated_asset_lifecycle_gate.v1")
            self.assertEqual(lifecycle_context["state"], "blocked")
            self.assertEqual(lifecycle_context["manifest_count"], 1)
            self.assertEqual(lifecycle_context["asset_count"], 2)
            self.assertEqual(lifecycle_context["animation_asset_count"], 1)
            self.assertEqual(lifecycle_context["animation_pending_count"], 1)
            self.assertEqual(lifecycle_context["provider_pending_count"], 1)
            self.assertEqual(lifecycle_context["import_pending_count"], 1)
            self.assertEqual(lifecycle_context["quality_pending_count"], 0)
            self.assertEqual(lifecycle_context["ready_count"], 0)
            self.assertEqual(lifecycle_context["placeholder_count"], 1)
            self.assertEqual(lifecycle_context["stop_condition_count"], 1)
            self.assertIn("tripo", lifecycle_context["preferred_provider_preview"])
            self.assertIn("provider_task_completion", lifecycle_context["missing_stage_preview"])
            self.assertIn("download_or_import_result", lifecycle_context["missing_stage_preview"])
            self.assertIn("animation_motion_generation_or_retarget", lifecycle_context["missing_stage_preview"])
            self.assertIn("placeholder_mapping", lifecycle_context["missing_stage_preview"])
            self.assertEqual(lifecycle_context["target_asset"]["id"], "asset_01")
            self.assertFalse(lifecycle_context["lifecycle_complete"])
            self.assertTrue(lifecycle_context["future_network_required"])
            self.assertTrue(lifecycle_context["future_spend_required"])
            self.assertTrue(lifecycle_context["no_provider_call"])
            self.assertTrue(lifecycle_context["no_editor_mutation"])
            self.assertTrue(lifecycle_context["no_import"])
            self.assertTrue(lifecycle_context["no_ledger_write"])
            self.assertTrue(lifecycle_context["stop_before_lifecycle_mutation"])
            self.assertTrue(workflow_actions["compile_asset_lifecycle_manifest"]["enabled"])
            self.assertTrue(workflow_actions["compile_asset_lifecycle_manifest"]["requires_ledger"])
            self.assertFalse(workflow_actions["compile_asset_lifecycle_manifest"]["requires_bridge"])
            self.assertEqual(
                workflow_actions["compile_asset_lifecycle_manifest"]["tool"],
                "skill_compile_ide_companion_asset_lifecycle_manifest",
            )
            self.assertEqual(
                workflow_actions["compile_asset_lifecycle_manifest"]["input_source"],
                "matching_ide_companion_ledger.session_plan plus outputs.work_order_template generated prompt counts",
            )
            self.assertTrue(workflow_actions["compile_asset_lifecycle_manifest"]["arguments"]["write_manifest"])
            self.assertEqual(workflow_actions["compile_asset_lifecycle_manifest"]["arguments"]["preferred_provider"], "tripo")
            lifecycle_compile_context = workflow_actions["compile_asset_lifecycle_manifest"]["target_asset_lifecycle_compile_context"]
            self.assertEqual(
                lifecycle_compile_context["schema"],
                "unreal_mcp_chat_asset_lifecycle_manifest_compile_context.v1",
            )
            self.assertEqual(lifecycle_compile_context["state"], "refresh_recommended")
            self.assertEqual(lifecycle_compile_context["session_name"], "ide-companion")
            self.assertTrue(lifecycle_compile_context["has_session_plan"])
            self.assertEqual(lifecycle_compile_context["session_plan_phase_count"], 3)
            self.assertEqual(lifecycle_compile_context["planned_asset_prompt_count"], 3)
            self.assertEqual(lifecycle_compile_context["planned_animation_prompt_count"], 2)
            self.assertEqual(lifecycle_compile_context["estimated_uthana_motion_seconds"], 8)
            self.assertEqual(lifecycle_compile_context["manifest_count"], 1)
            self.assertEqual(lifecycle_compile_context["manifest_asset_count"], 2)
            self.assertEqual(lifecycle_compile_context["manifest_animation_asset_count"], 1)
            self.assertEqual(lifecycle_compile_context["manifest_pending_count"], 2)
            self.assertIn("A_EnemyScout_PatrolWalk", " ".join(lifecycle_compile_context["generated_animation_prompt_preview"]))
            self.assertIn("gen_compile_generated_animation_evidence", lifecycle_compile_context["generated_animation_tool_preview"])
            self.assertIn("pie_motion_playback_or_viewport_proof", lifecycle_compile_context["generated_animation_proof_required_preview"])
            self.assertIn("wallet_evidence_recorded", lifecycle_compile_context["missing_future_gate_preview"])
            self.assertEqual(lifecycle_compile_context["compile_tool"], "skill_compile_ide_companion_asset_lifecycle_manifest")
            self.assertEqual(lifecycle_compile_context["placeholder_tool"], "skill_compile_ide_companion_placeholder_manifest")
            self.assertTrue(lifecycle_compile_context["requires_session_plan"])
            self.assertTrue(lifecycle_compile_context["write_manifest_recommended"])
            self.assertTrue(lifecycle_compile_context["future_network_required"])
            self.assertTrue(lifecycle_compile_context["future_spend_required"])
            self.assertFalse(lifecycle_compile_context["network_required_now"])
            self.assertFalse(lifecycle_compile_context["spend_required_now"])
            self.assertFalse(lifecycle_compile_context["unreal_editor_required_now"])
            self.assertTrue(lifecycle_compile_context["stop_before_provider_or_editor"])
            self.assertTrue(lifecycle_compile_context["no_provider_call"])
            self.assertTrue(workflow_actions["review_generated_animation_lifecycle_gate"]["enabled"])
            self.assertTrue(workflow_actions["review_generated_animation_lifecycle_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_generated_animation_lifecycle_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_generated_animation_lifecycle_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_generated_animation_lifecycle_gate"]["input_source"],
                "outputs.generated_asset_lifecycles.preview_animation_assets plus outputs.readiness_policy",
            )
            animation_context = workflow_actions["review_generated_animation_lifecycle_gate"]["target_generated_animation_lifecycle_context"]
            self.assertEqual(animation_context["schema"], "unreal_mcp_chat_generated_animation_lifecycle_gate.v1")
            self.assertEqual(animation_context["state"], "blocked")
            self.assertEqual(animation_context["animation_provider"], "uthana")
            self.assertEqual(animation_context["animation_asset_count"], 1)
            self.assertEqual(animation_context["animation_pending_count"], 1)
            self.assertEqual(animation_context["target_animation"]["id"], "animation_01")
            self.assertEqual(animation_context["target_animation"]["name"], "A_EnemyScout_PatrolWalk")
            self.assertEqual(animation_context["target_animation"]["provider"], "uthana")
            self.assertEqual(animation_context["target_animation"]["target_skeleton"], "UE5 Manny")
            self.assertEqual(
                animation_context["quality_proof_contract_schema"],
                "unreal_mcp_generated_animation_quality_proof_contract.v1",
            )
            self.assertEqual(animation_context["quality_proof_required_count"], 5)
            self.assertIn("pie_motion_playback_or_viewport_proof", animation_context["quality_proof_required_preview"])
            self.assertIn("target_skeleton_or_retarget_asset", animation_context["target_animation"]["quality_proof_required_preview"])
            self.assertEqual(animation_context["quality_gate_count"], 7)
            self.assertEqual(animation_context["quality_evidence_count"], 0)
            self.assertEqual(animation_context["quality_evidence_missing_count"], 7)
            self.assertIn("uthana_motion_generation", animation_context["missing_stage_preview"])
            self.assertIn("provider_usage_readiness", animation_context["missing_stage_preview"])
            self.assertIn("editor_import_readiness", animation_context["missing_stage_preview"])
            self.assertIn("animation_retarget_animgraph_pie_ledger_proof", animation_context["missing_stage_preview"])
            self.assertEqual(animation_context["next_safe_action"]["schema"], "unreal_mcp_chat_generated_animation_next_safe_action.v1")
            self.assertEqual(animation_context["next_safe_action"]["action_id"], "resolve_uthana_usage_gates")
            self.assertEqual(animation_context["next_safe_action"]["tool"], "gen_compile_ide_companion_readiness")
            self.assertEqual(animation_context["next_safe_action"]["candidate_tool_after_unblocked"], "gen_uthana_text_to_motion")
            self.assertFalse(animation_context["next_safe_action"]["can_execute_now"])
            self.assertTrue(animation_context["next_safe_action"]["no_provider_call"])
            self.assertTrue(animation_context["next_safe_action"]["no_editor_mutation"])
            self.assertEqual(
                animation_context["uthana_usage_contract"]["schema"],
                "unreal_mcp_uthana_animation_usage_contract.v1",
            )
            self.assertEqual(animation_context["uthana_usage_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
            self.assertEqual(animation_context["uthana_usage_receipt_required_command"], "python scripts\\write_paid_generation_evidence_review.py")
            self.assertIn("gen_uthana_get_account", animation_context["uthana_allowance_tool_preview"])
            self.assertIn("confirm_usage=True", animation_context["uthana_usage_confirmation_field"])
            self.assertEqual(
                animation_context["uthana_usage_contract"]["operator_command_handoff_ids"],
                ["record_masked_uthana_allowance_evidence", "record_explicit_uthana_usage_approval"],
            )
            self.assertEqual(
                animation_context["uthana_usage_next_operator_command_handoff"]["id"],
                "record_masked_uthana_allowance_evidence",
            )
            self.assertTrue(animation_context["uthana_usage_contract"]["no_task_submission"])
            self.assertEqual(animation_context["submit_tool"], "gen_uthana_text_to_motion")
            self.assertEqual(animation_context["download_tool"], "gen_uthana_download_motion")
            self.assertEqual(animation_context["import_tool"], "gen_uthana_import_animation_to_project")
            self.assertTrue(animation_context["requires_provider_key"])
            self.assertTrue(animation_context["requires_usage_confirmation"])
            self.assertTrue(animation_context["requires_bridge"])
            self.assertTrue(animation_context["no_provider_call"])
            self.assertTrue(animation_context["no_download"])
            self.assertTrue(animation_context["no_import"])
            self.assertTrue(animation_context["no_editor_mutation"])
            self.assertTrue(animation_context["no_ledger_write"])
            self.assertTrue(animation_context["stop_before_animation_generation_or_import"])
            self.assertTrue(workflow_actions["compile_generated_animation_evidence"]["enabled"])
            self.assertTrue(workflow_actions["compile_generated_animation_evidence"]["requires_ledger"])
            self.assertFalse(workflow_actions["compile_generated_animation_evidence"]["requires_bridge"])
            self.assertEqual(workflow_actions["compile_generated_animation_evidence"]["tool"], "gen_compile_generated_animation_evidence")
            self.assertEqual(
                workflow_actions["compile_generated_animation_evidence"]["input_source"],
                "outputs.workflow_actions.review_generated_animation_lifecycle_gate.target_generated_animation_lifecycle_context plus captured provider/editor/runtime/ledger proof JSON",
            )
            self.assertEqual(workflow_actions["compile_generated_animation_evidence"]["arguments"]["motion_prompt"], "A_EnemyScout_PatrolWalk")
            self.assertEqual(workflow_actions["compile_generated_animation_evidence"]["arguments"]["motion_id"], "")
            self.assertIn("job_result_json", workflow_actions["compile_generated_animation_evidence"]["arguments"])
            self.assertIn("text_motion_result_json", workflow_actions["compile_generated_animation_evidence"]["arguments"])
            self.assertIn("download_result_json", workflow_actions["compile_generated_animation_evidence"]["arguments"])
            self.assertIn("pie_evidence_json", workflow_actions["compile_generated_animation_evidence"]["arguments"])
            self.assertEqual(workflow_actions["compile_generated_animation_evidence"]["target_generated_animation_lifecycle_context"]["target_animation"]["id"], "animation_01")
            self.assertTrue(workflow_actions["review_generated_asset_import_gate"]["enabled"])
            self.assertTrue(workflow_actions["review_generated_asset_import_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_generated_asset_import_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_generated_asset_import_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_generated_asset_import_gate"]["input_source"],
                "outputs.generated_asset_quality_gate.items plus outputs.readiness_policy.editor_mutation",
            )
            asset_import_context = workflow_actions["review_generated_asset_import_gate"]["target_generated_asset_import_context"]
            self.assertEqual(asset_import_context["state"], "blocked")
            self.assertEqual(asset_import_context["readiness_state"], "blocked")
            self.assertFalse(asset_import_context["editor_mutation_allowed"])
            self.assertEqual(asset_import_context["asset_count"], 2)
            self.assertEqual(asset_import_context["import_pending_count"], 1)
            self.assertEqual(asset_import_context["quality_pending_count"], 0)
            self.assertEqual(asset_import_context["target_asset"]["id"], "asset_02")
            self.assertEqual(asset_import_context["target_asset"]["name"], "SM_EnemyScout")
            self.assertEqual(asset_import_context["target_asset"]["state"], "import_pending")
            self.assertEqual(asset_import_context["target_asset"]["expected_import_path"], "/Game/Generated/Assets/SM_EnemyScout")
            self.assertFalse(asset_import_context["target_asset"]["has_placeholder"])
            self.assertIn("unreal_bridge_reachable", asset_import_context["missing_gate_preview"])
            self.assertTrue(asset_import_context["import_readback_required"])
            self.assertTrue(asset_import_context["quality_proof_required"])
            self.assertFalse(asset_import_context["placeholder_replacement_required"])
            self.assertEqual(asset_import_context["lifecycle_tool"], "skill_compile_ide_companion_asset_lifecycle_manifest")
            self.assertEqual(asset_import_context["queue_tool"], "skill_compile_ide_companion_editor_queue")
            self.assertEqual(asset_import_context["evidence_tool"], "skill_record_ide_companion_evidence")
            self.assertTrue(asset_import_context["requires_bridge"])
            self.assertTrue(asset_import_context["stop_before_import_or_quality_work"])
            self.assertTrue(workflow_actions["review_generated_asset_quality_proof_gate"]["enabled"])
            self.assertTrue(workflow_actions["review_generated_asset_quality_proof_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_generated_asset_quality_proof_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_generated_asset_quality_proof_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_generated_asset_quality_proof_gate"]["input_source"],
                "outputs.generated_asset_quality_gate.items plus outputs.readiness_policy.editor_mutation",
            )
            quality_proof_context = workflow_actions["review_generated_asset_quality_proof_gate"]["target_generated_asset_quality_proof_context"]
            self.assertEqual(quality_proof_context["schema"], "unreal_mcp_chat_generated_asset_quality_proof_gate.v1")
            self.assertEqual(quality_proof_context["state"], "blocked")
            self.assertEqual(quality_proof_context["readiness_state"], "blocked")
            self.assertFalse(quality_proof_context["editor_mutation_allowed"])
            self.assertEqual(quality_proof_context["asset_count"], 2)
            self.assertEqual(quality_proof_context["quality_candidate_count"], 2)
            self.assertEqual(quality_proof_context["target_asset"]["id"], "asset_02")
            self.assertEqual(quality_proof_context["target_asset"]["name"], "SM_EnemyScout")
            self.assertEqual(quality_proof_context["target_asset"]["state"], "import_pending")
            self.assertEqual(quality_proof_context["quality_gate_count"], 5)
            self.assertEqual(quality_proof_context["quality_evidence_count"], 0)
            self.assertEqual(quality_proof_context["quality_evidence_missing_count"], 5)
            self.assertEqual(
                quality_proof_context["quality_proof_contract_schema"],
                "unreal_mcp_generated_asset_quality_proof_contract.v1",
            )
            self.assertEqual(quality_proof_context["quality_proof_required_count"], 5)
            self.assertIn("collision_readability_check", quality_proof_context["quality_proof_required_preview"])
            self.assertIn("viewport_thumbnail_or_screenshot", quality_proof_context["target_asset"]["quality_proof_required_preview"])
            self.assertTrue(quality_proof_context["requires_imported_asset"])
            self.assertTrue(quality_proof_context["requires_material_proof"])
            self.assertTrue(quality_proof_context["requires_collision_proof"])
            self.assertTrue(quality_proof_context["requires_viewport_proof"])
            self.assertTrue(quality_proof_context["requires_ledger_proof"])
            self.assertIn("import_result", quality_proof_context["missing_stage_preview"])
            self.assertIn("editor_mutation_readiness", quality_proof_context["missing_stage_preview"])
            self.assertIn("material_collision_viewport_ledger_proof", quality_proof_context["missing_stage_preview"])
            self.assertIn("unreal_bridge_reachable", quality_proof_context["missing_gate_preview"])
            self.assertFalse(quality_proof_context["quality_proof_ready"])
            self.assertEqual(quality_proof_context["import_review_tool"], "review_generated_asset_import_gate")
            self.assertEqual(quality_proof_context["replacement_review_tool"], "review_generated_asset_replacement_gate")
            self.assertTrue(quality_proof_context["requires_bridge"])
            self.assertTrue(quality_proof_context["no_provider_call"])
            self.assertTrue(quality_proof_context["no_import"])
            self.assertTrue(quality_proof_context["no_editor_mutation"])
            self.assertTrue(quality_proof_context["no_viewport_capture"])
            self.assertTrue(quality_proof_context["no_ledger_write"])
            self.assertTrue(quality_proof_context["stop_before_quality_proof_work"])
            self.assertTrue(workflow_actions["review_generated_asset_replacement_gate"]["enabled"])
            self.assertTrue(workflow_actions["review_generated_asset_replacement_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_generated_asset_replacement_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_generated_asset_replacement_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_generated_asset_replacement_gate"]["input_source"],
                "outputs.generated_asset_lifecycles.preview_assets plus outputs.readiness_policy.editor_mutation",
            )
            replacement_context = workflow_actions["review_generated_asset_replacement_gate"]["target_generated_asset_replacement_context"]
            self.assertEqual(replacement_context["schema"], "unreal_mcp_chat_generated_asset_replacement_gate.v1")
            self.assertEqual(replacement_context["state"], "blocked")
            self.assertEqual(replacement_context["readiness_state"], "blocked")
            self.assertFalse(replacement_context["editor_mutation_allowed"])
            self.assertEqual(replacement_context["asset_count"], 2)
            self.assertEqual(replacement_context["placeholder_count"], 1)
            self.assertEqual(replacement_context["replacement_pending_count"], 1)
            self.assertEqual(replacement_context["target_asset"]["id"], "asset_01")
            self.assertEqual(replacement_context["target_asset"]["name"], "SM_ObjectiveBeacon")
            self.assertEqual(
                replacement_context["target_asset"]["placeholder_asset_path"],
                "/Game/Generated/Placeholders/PH_ObjectiveBeacon",
            )
            self.assertEqual(
                replacement_context["target_asset"]["expected_import_path"],
                "/Game/Generated/Assets/SM_ObjectiveBeacon",
            )
            self.assertIn("provider_task_completion", replacement_context["missing_stage_preview"])
            self.assertIn("generated_asset_import", replacement_context["missing_stage_preview"])
            self.assertIn("editor_mutation_readiness", replacement_context["missing_stage_preview"])
            self.assertIn("ledger_replacement_evidence", replacement_context["missing_stage_preview"])
            self.assertIn("unreal_bridge_reachable", replacement_context["missing_gate_preview"])
            self.assertFalse(replacement_context["replacement_ready"])
            self.assertTrue(replacement_context["import_required_before_replacement"])
            self.assertTrue(replacement_context["ledger_evidence_required"])
            self.assertEqual(replacement_context["queue_tool"], "skill_compile_ide_companion_editor_queue")
            self.assertEqual(replacement_context["evidence_tool"], "skill_record_ide_companion_evidence")
            self.assertTrue(replacement_context["requires_bridge"])
            self.assertTrue(replacement_context["no_provider_call"])
            self.assertTrue(replacement_context["no_import"])
            self.assertTrue(replacement_context["no_editor_mutation"])
            self.assertTrue(replacement_context["no_ledger_write"])
            self.assertTrue(replacement_context["stop_before_placeholder_replacement"])
            self.assertTrue(workflow_actions["review_provider_spend_gate"]["enabled"])
            self.assertTrue(workflow_actions["review_provider_spend_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_provider_spend_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_provider_spend_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_provider_spend_gate"]["input_source"],
                "outputs.readiness_policy.paid_generation plus outputs.generated_asset_quality_gate",
            )
            provider_spend_context = workflow_actions["review_provider_spend_gate"]["target_provider_spend_context"]
            self.assertEqual(provider_spend_context["state"], "blocked")
            self.assertEqual(provider_spend_context["readiness_state"], "blocked")
            self.assertFalse(provider_spend_context["paid_generation_allowed"])
            self.assertEqual(provider_spend_context["provider_pending_count"], 1)
            self.assertEqual(provider_spend_context["asset_count"], 2)
            self.assertEqual(provider_spend_context["placeholder_count"], 1)
            self.assertEqual(provider_spend_context["missing_gate_count"], 2)
            self.assertIn("wallet_evidence_recorded", provider_spend_context["missing_gate_preview"])
            self.assertIn("spend_confirmation_recorded", provider_spend_context["missing_gate_preview"])
            self.assertEqual(provider_spend_context["evidence_required_count"], 3)
            self.assertIn("paid_generation_evidence_contract", provider_spend_context)
            spend_contract = provider_spend_context["paid_generation_evidence_contract"]
            self.assertEqual(spend_contract["schema"], "unreal_mcp_paid_generation_evidence_contract.v1")
            self.assertFalse(spend_contract["mesh_wallet_evidence_recorded"])
            self.assertFalse(spend_contract["animation_allowance_evidence_recorded"])
            self.assertFalse(spend_contract["explicit_usage_approval_recorded"])
            self.assertFalse(spend_contract["network_required_now"])
            self.assertFalse(spend_contract["spend_required_now"])
            self.assertTrue(spend_contract["future_network_required"])
            self.assertTrue(spend_contract["future_spend_required"])
            self.assertTrue(spend_contract["no_provider_call"])
            self.assertTrue(spend_contract["no_credit_reservation"])
            self.assertTrue(spend_contract["no_task_submission"])
            self.assertTrue(spend_contract["no_ledger_write"])
            self.assertEqual(spend_contract["ledger_tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(spend_contract["review_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
            self.assertEqual(spend_contract["review_receipt_required_command"], "python scripts\\write_paid_generation_evidence_review.py")
            self.assertIn(spend_contract["review_receipt_state"], {"missing", "missing_evidence", "ready"})
            self.assertIn("gen_uthana_get_account", spend_contract["animation_allowance_tools"])
            self.assertIn(
                "gen_uthana_get_account / gen_uthana_get_job / gen_uthana_check_download_allowed",
                " ".join(spend_contract["no_spend_checks"]),
            )
            self.assertIn("explicit_uthana_usage_approval", spend_contract["evidence_required_preview"])
            self.assertIn("placeholders and lifecycle manifests", spend_contract["fallback_reason"])
            self.assertEqual(len(spend_contract["operator_command_handoff"]), 3)
            self.assertEqual(spend_contract["operator_command_handoff"][0]["id"], "record_masked_tripo_wallet_evidence")
            self.assertEqual(spend_contract["operator_command_handoff"][1]["id"], "record_masked_uthana_allowance_evidence")
            self.assertEqual(spend_contract["operator_command_handoff"][2]["id"], "record_explicit_spend_and_usage_approval")
            self.assertFalse(spend_contract["operator_command_handoff"][0]["approval_flags_included"])
            self.assertFalse(spend_contract["operator_command_handoff"][1]["approval_flags_included"])
            self.assertTrue(spend_contract["operator_command_handoff"][0]["no_task_submission"])
            self.assertTrue(spend_contract["operator_command_handoff"][1]["no_task_submission"])
            self.assertTrue(spend_contract["operator_command_handoff"][2]["approval_flags_included"])
            self.assertEqual(provider_spend_context["target_asset"]["id"], "asset_01")
            self.assertEqual(provider_spend_context["target_asset"]["name"], "SM_ObjectiveBeacon")
            self.assertEqual(provider_spend_context["provider"], "tripo")
            self.assertIn(provider_spend_context["provider_config_review_receipt_state"], {"missing", "ready", "missing_keys", "blocked"})
            self.assertEqual(provider_spend_context["provider_config_review_receipt_path"], "Saved\\ProviderConfigReview\\last_review_receipt.json")
            self.assertEqual(provider_spend_context["provider_config_review_receipt_required_command"], "python scripts\\write_provider_config_review.py")
            self.assertIn("provider task", provider_spend_context["next_gate"])
            self.assertTrue(provider_spend_context["fallback_placeholder_available"])
            self.assertEqual(provider_spend_context["fallback_action_id"], "compile_placeholder_manifest")
            self.assertEqual(provider_spend_context["fallback_action_label"], "Compile Placeholder Manifest")
            self.assertEqual(provider_spend_context["fallback_tool"], "skill_compile_ide_companion_placeholder_manifest")
            self.assertEqual(provider_spend_context["fallback_queue_tool"], "skill_compile_ide_companion_editor_queue")
            self.assertIn("no-spend placeholders", provider_spend_context["fallback_reason"])
            self.assertTrue(provider_spend_context["future_network_required"])
            self.assertTrue(provider_spend_context["future_spend_required"])
            self.assertFalse(provider_spend_context["network_required_now"])
            self.assertFalse(provider_spend_context["spend_required_now"])
            self.assertFalse(provider_spend_context["unreal_editor_required_now"])
            self.assertTrue(provider_spend_context["no_provider_call"])
            self.assertTrue(provider_spend_context["stop_before_provider_call"])
            self.assertTrue(workflow_actions["continue_with_placeholder_fallback"]["enabled"])
            self.assertTrue(workflow_actions["continue_with_placeholder_fallback"]["requires_ledger"])
            self.assertFalse(workflow_actions["continue_with_placeholder_fallback"]["requires_bridge"])
            self.assertEqual(
                workflow_actions["continue_with_placeholder_fallback"]["tool"],
                "skill_compile_ide_companion_placeholder_manifest",
            )
            self.assertEqual(
                workflow_actions["continue_with_placeholder_fallback"]["input_source"],
                "outputs.workflow_actions.review_provider_spend_gate.target_provider_spend_context plus outputs.workflow_actions.compile_placeholder_manifest.target_placeholder_context",
            )
            self.assertEqual(
                workflow_actions["continue_with_placeholder_fallback"]["target_provider_spend_context"]["fallback_action_id"],
                "compile_placeholder_manifest",
            )
            self.assertEqual(
                workflow_actions["continue_with_placeholder_fallback"]["target_placeholder_context"]["target_asset"]["id"],
                "asset_01",
            )
            self.assertEqual(
                workflow_actions["continue_with_placeholder_fallback"]["arguments"]["placeholder_root"],
                "/Game/Generated/Placeholders",
            )
            self.assertTrue(workflow_actions["review_generated_asset_provider_task_gate"]["enabled"])
            self.assertTrue(workflow_actions["review_generated_asset_provider_task_gate"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_generated_asset_provider_task_gate"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_generated_asset_provider_task_gate"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_generated_asset_provider_task_gate"]["input_source"],
                "outputs.generated_asset_lifecycles.preview_assets plus outputs.readiness_policy.paid_generation",
            )
            provider_task_context = workflow_actions["review_generated_asset_provider_task_gate"]["target_generated_asset_provider_task_context"]
            self.assertEqual(provider_task_context["schema"], "unreal_mcp_chat_generated_asset_provider_task_gate.v1")
            self.assertEqual(provider_task_context["state"], "blocked")
            self.assertEqual(provider_task_context["asset_count"], 2)
            self.assertEqual(provider_task_context["provider_pending_count"], 1)
            self.assertEqual(provider_task_context["provider_success_count"], 1)
            self.assertEqual(provider_task_context["task_id_missing_count"], 0)
            self.assertEqual(provider_task_context["download_pending_count"], 1)
            self.assertEqual(provider_task_context["import_pending_count"], 1)
            self.assertEqual(provider_task_context["target_asset"]["id"], "asset_02")
            self.assertEqual(provider_task_context["target_asset"]["name"], "SM_EnemyScout")
            self.assertEqual(provider_task_context["target_asset"]["task_status"], "success")
            self.assertEqual(provider_task_context["target_asset"]["task_id"], "tsk_enemy_scout")
            self.assertEqual(provider_task_context["target_asset"]["status_tool"], "gen_tripo_get_task")
            self.assertEqual(provider_task_context["target_asset"]["download_tool"], "gen_tripo_download_result")
            self.assertEqual(provider_task_context["target_asset"]["expected_import_path"], "/Game/Generated/Assets/SM_EnemyScout")
            self.assertIn("download_result", provider_task_context["missing_stage_preview"])
            self.assertIn("import_result", provider_task_context["missing_stage_preview"])
            self.assertIn("ledger_provider_task_evidence", provider_task_context["missing_stage_preview"])
            self.assertFalse(provider_task_context["provider_task_ready"])
            self.assertFalse(provider_task_context["status_poll_required"])
            self.assertTrue(provider_task_context["download_required"])
            self.assertTrue(provider_task_context["import_required_after_download"])
            self.assertTrue(provider_task_context["ledger_evidence_required"])
            self.assertEqual(provider_task_context["spend_review_tool"], "review_provider_spend_gate")
            self.assertEqual(provider_task_context["import_review_tool"], "review_generated_asset_import_gate")
            self.assertTrue(provider_task_context["requires_network"])
            self.assertTrue(provider_task_context["requires_bridge_for_import"])
            self.assertTrue(provider_task_context["no_provider_call"])
            self.assertTrue(provider_task_context["no_status_poll"])
            self.assertTrue(provider_task_context["no_download"])
            self.assertTrue(provider_task_context["no_import"])
            self.assertTrue(provider_task_context["no_editor_mutation"])
            self.assertTrue(provider_task_context["no_ledger_write"])
            self.assertTrue(provider_task_context["stop_before_provider_task_or_download"])
            self.assertTrue(workflow_actions["resolve_generated_asset"]["enabled"])
            self.assertTrue(workflow_actions["resolve_generated_asset"]["requires_ledger"])
            self.assertEqual(workflow_actions["resolve_generated_asset"]["tool"], "skill_compile_ide_companion_asset_lifecycle_manifest")
            self.assertEqual(workflow_actions["resolve_generated_asset"]["input_source"], "outputs.generated_asset_quality_gate.items")
            self.assertEqual(workflow_actions["resolve_generated_asset"]["target_generated_asset_id"], "asset_01")
            self.assertEqual(workflow_actions["resolve_generated_asset"]["arguments"]["target_asset_id"], "asset_01")
            self.assertEqual(workflow_actions["resolve_generated_asset"]["arguments"]["target_asset_state"], "provider_pending")
            self.assertIn("provider task", workflow_actions["resolve_generated_asset"]["arguments"]["next_gate"])
            self.assertEqual(workflow_actions["resolve_generated_asset"]["target_generated_asset_context"]["name"], "SM_ObjectiveBeacon")
            self.assertEqual(workflow_actions["resolve_generated_asset"]["target_generated_asset_context"]["state"], "provider_pending")
            self.assertTrue(workflow_actions["resolve_generated_asset"]["target_generated_asset_context"]["has_placeholder"])
            self.assertIn("viewport", " ".join(workflow_actions["resolve_generated_asset"]["target_generated_asset_context"]["quality_gate_preview"]).lower())
            self.assertTrue(workflow_actions["compile_placeholder_manifest"]["enabled"])
            self.assertTrue(workflow_actions["compile_placeholder_manifest"]["requires_ledger"])
            self.assertFalse(workflow_actions["compile_placeholder_manifest"]["requires_bridge"])
            self.assertEqual(workflow_actions["compile_placeholder_manifest"]["tool"], "skill_compile_ide_companion_placeholder_manifest")
            self.assertEqual(
                workflow_actions["compile_placeholder_manifest"]["input_source"],
                "outputs.generated_asset_quality_gate plus outputs.workflow_actions.resolve_blockers",
            )
            placeholder_context = workflow_actions["compile_placeholder_manifest"]["target_placeholder_context"]
            self.assertEqual(placeholder_context["session_name"], "ide-companion")
            self.assertTrue(placeholder_context["has_session_plan"])
            self.assertEqual(placeholder_context["generated_asset_state"], "blocked")
            self.assertEqual(placeholder_context["asset_count"], 2)
            self.assertEqual(placeholder_context["provider_pending_count"], 1)
            self.assertEqual(placeholder_context["import_pending_count"], 1)
            self.assertEqual(placeholder_context["placeholder_count"], 1)
            self.assertEqual(placeholder_context["blocking_gate_count"], 1)
            self.assertEqual(placeholder_context["target_asset"]["id"], "asset_01")
            self.assertEqual(placeholder_context["target_asset"]["name"], "SM_ObjectiveBeacon")
            self.assertEqual(placeholder_context["placeholder_root"], "/Game/Generated/Placeholders")
            self.assertTrue(placeholder_context["requires_session_plan"])
            self.assertTrue(placeholder_context["stop_before_editor_or_provider"])
            self.assertEqual(
                workflow_actions["compile_placeholder_manifest"]["arguments"]["placeholder_root"],
                "/Game/Generated/Placeholders",
            )
            self.assertTrue(workflow_actions["review_editor_queue"]["enabled"])
            self.assertFalse(workflow_actions["review_editor_queue"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_editor_queue"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_editor_queue"]["input_source"],
                "outputs.editor_queues plus outputs.next_safe_step",
            )
            queue_review_context = workflow_actions["review_editor_queue"]["target_queue_review_context"]
            self.assertEqual(queue_review_context["state"], "blocked")
            self.assertEqual(queue_review_context["queue_count"], 1)
            self.assertEqual(queue_review_context["queued_action_count"], 2)
            self.assertEqual(queue_review_context["executable_queue_count"], 0)
            self.assertEqual(queue_review_context["blocked_queue_count"], 1)
            self.assertEqual(queue_review_context["bridge_blocked_count"], 1)
            self.assertEqual(queue_review_context["queue_name"], "editor_queue")
            self.assertEqual(queue_review_context["target_phase"], "editor_implementation")
            self.assertEqual(queue_review_context["action_count"], 2)
            self.assertEqual(queue_review_context["preview_action_count"], 2)
            self.assertEqual(queue_review_context["evidence_count"], 1)
            self.assertEqual(queue_review_context["next_action_id"], "create_placeholder_folder")
            self.assertEqual(queue_review_context["next_action_tool"], "create_folder")
            self.assertEqual(queue_review_context["blocking_gate_count"], 1)
            self.assertIn("unreal_bridge_reachable", queue_review_context["blocking_gate_preview"])
            self.assertTrue(queue_review_context["requires_bridge"])
            self.assertTrue(queue_review_context["bridge_blocked"])
            self.assertFalse(queue_review_context["can_execute_now"])
            self.assertEqual(queue_review_context["generated_animation_asset_count"], 1)
            self.assertEqual(queue_review_context["generated_animation_target_name"], "A_EnemyScout_PatrolWalk")
            self.assertEqual(queue_review_context["generated_animation_target_provider"], "uthana")
            self.assertEqual(queue_review_context["generated_animation_target_skeleton"], "UE5 Manny")
            self.assertEqual(queue_review_context["generated_animation_next_safe_action_id"], "resolve_uthana_usage_gates")
            self.assertIn("retarget/readback", " ".join(queue_review_context["generated_animation_gate_policy"]))
            self.assertTrue(queue_review_context["stop_before_editor_mutation"])
            self.assertTrue(workflow_actions["queue_editor_actions"]["enabled"])
            self.assertIn("chat_get_cockpit_ledger_detail", workflow_actions["queue_editor_actions"]["input_source"])
            self.assertEqual(workflow_actions["queue_editor_actions"]["arguments"]["target_phase"], "editor_implementation")
            self.assertIn("ledger_path", workflow_actions["queue_editor_actions"]["arguments"])
            self.assertEqual(workflow_actions["queue_editor_actions"]["target_queue_phase"], "editor_implementation")
            self.assertEqual(workflow_actions["queue_editor_actions"]["target_queue_context"]["template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(workflow_actions["queue_editor_actions"]["target_queue_context"]["operation_count"], 2)
            self.assertEqual(workflow_actions["queue_editor_actions"]["target_queue_context"]["editor_operation_count"], 2)
            self.assertEqual(workflow_actions["queue_editor_actions"]["target_queue_context"]["bridge_required_operation_count"], 2)
            self.assertEqual(workflow_actions["queue_editor_actions"]["target_queue_context"]["compile_check_count"], 1)
            self.assertFalse(workflow_actions["execute_next_safe_step"]["enabled"])
            self.assertTrue(workflow_actions["execute_next_safe_step"]["requires_bridge"])
            self.assertEqual(workflow_actions["execute_next_safe_step"]["input_source"], "outputs.next_safe_step")
            self.assertEqual(workflow_actions["execute_next_safe_step"]["target_execute_id"], "create_placeholder_folder")
            self.assertEqual(workflow_actions["execute_next_safe_step"]["target_execute_context"]["tool"], "create_folder")
            self.assertEqual(workflow_actions["execute_next_safe_step"]["target_execute_context"]["target_phase"], "editor_implementation")
            self.assertEqual(workflow_actions["execute_next_safe_step"]["target_execute_context"]["argument_keys"], ["path"])
            self.assertFalse(workflow_actions["execute_next_safe_step"]["target_execute_context"]["can_execute_now"])
            self.assertEqual(workflow_actions["execute_next_safe_step"]["target_execution_review_context"]["tool"], "create_folder")
            self.assertEqual(workflow_actions["execute_next_safe_step"]["target_execution_review_context"]["state"], "blocked")
            self.assertEqual(workflow_actions["execute_next_safe_step"]["target_execution_review_context"]["missing_gate_count"], 1)
            self.assertIn("unreal_bridge_reachable", workflow_actions["execute_next_safe_step"]["target_execution_review_context"]["missing_gates"])
            self.assertIn("Execute exactly one queued editor action.", workflow_actions["execute_next_safe_step"]["target_execution_review_context"]["executor_contract"])
            self.assertIn("Refresh cockpit overview", " ".join(workflow_actions["execute_next_safe_step"]["target_execution_review_context"]["pre_execution_checklist"]))
            self.assertIn("Record queued editor action evidence", " ".join(workflow_actions["execute_next_safe_step"]["target_execution_review_context"]["post_execution_evidence_required"]))
            self.assertTrue(workflow_actions["execute_next_safe_step"]["target_execution_review_context"]["stop_after_action"])
            self.assertTrue(workflow_actions["review_evidence_requirements"]["enabled"])
            self.assertTrue(workflow_actions["review_evidence_requirements"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_evidence_requirements"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_evidence_requirements"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(
                workflow_actions["review_evidence_requirements"]["input_source"],
                "outputs.evidence_recording plus outputs.workflow_actions.record_evidence.target_evidence_context",
            )
            evidence_review_context = workflow_actions["review_evidence_requirements"]["target_evidence_review_context"]
            self.assertEqual(evidence_review_context["state"], "blocked")
            self.assertEqual(evidence_review_context["session_name"], "ide-companion")
            self.assertEqual(evidence_review_context["target_phase"], "editor_implementation")
            self.assertEqual(evidence_review_context["item_count"], 17)
            self.assertEqual(evidence_review_context["pending_count"], 14)
            self.assertEqual(evidence_review_context["blocked_count"], 3)
            self.assertEqual(evidence_review_context["recorded_count"], 0)
            self.assertEqual(evidence_review_context["record_tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(evidence_review_context["target_evidence_id"], "record_readiness_repair_queue")
            self.assertEqual(evidence_review_context["target_evidence_type"], "readiness_repair_queue")
            self.assertEqual(evidence_review_context["target_artifact_count"], 7)
            self.assertIn("verify_unreal_bridge_reachability", evidence_review_context["target_artifact_preview"])
            self.assertEqual(evidence_review_context["target_evidence"]["evidence_type"], "readiness_repair_queue")
            self.assertTrue(evidence_review_context["requires_bridge"])
            self.assertFalse(evidence_review_context["spend_required"])
            self.assertTrue(evidence_review_context["stop_before_ledger_write"])
            self.assertTrue(workflow_actions["record_evidence"]["records_evidence"])
            self.assertEqual(workflow_actions["record_evidence"]["input_source"], "outputs.evidence_recording.items")
            self.assertEqual(workflow_actions["record_evidence"]["target_evidence_item_id"], "record_readiness_repair_queue")
            self.assertEqual(workflow_actions["record_evidence"]["target_evidence_item"]["evidence_type"], "readiness_repair_queue")
            self.assertEqual(workflow_actions["record_evidence"]["target_evidence_item"]["state"], "pending")
            self.assertEqual(workflow_actions["record_evidence"]["target_evidence_context"]["evidence_type"], "readiness_repair_queue")
            self.assertEqual(workflow_actions["record_evidence"]["target_evidence_context"]["state"], "pending")
            self.assertEqual(workflow_actions["record_evidence"]["target_evidence_context"]["artifact_count"], 7)
            self.assertIn("verify_unreal_bridge_reachability", workflow_actions["record_evidence"]["target_evidence_context"]["artifact_preview"])
            self.assertNotIn("dirty_promotion_review", workflow_actions["record_evidence"]["target_evidence_context"])
            self.assertNotIn("generated_asset", workflow_actions["record_evidence"]["target_evidence_context"])
            self.assertNotIn("generated_animation", workflow_actions["record_evidence"]["target_evidence_context"])
            self.assertNotIn("paid_generation_evidence", workflow_actions["record_evidence"]["target_evidence_context"])
            self.assertNotIn("runtime_verification", workflow_actions["record_evidence"]["target_evidence_context"])
            self.assertNotIn("queued_action", workflow_actions["record_evidence"]["target_evidence_context"])
            self.assertNotIn("feature_completion_contract", workflow_actions["record_evidence"]["target_evidence_context"])
            repair_queue_target = workflow_actions["record_evidence"]["target_evidence_context"]["readiness_repair_queue"]
            self.assertEqual(repair_queue_target["schema"], "unreal_mcp_readiness_repair_queue.v1")
            self.assertEqual(repair_queue_target["state"], "blocked")
            self.assertEqual(repair_queue_target["recommended_next"], "verify_unreal_bridge_reachability")
            self.assertEqual(repair_queue_target["next_gate"], "unreal_bridge_reachable")
            self.assertEqual(repair_queue_target["next_policy_area"], "editor_mutation")
            self.assertEqual(repair_queue_target["next_recommended_tool"], "scripts/bridge_ping.py")
            self.assertIn("successful_bridge_ping", repair_queue_target["next_evidence_required_preview"])
            self.assertTrue(repair_queue_target["next_requires_manual_operator"])
            self.assertTrue(repair_queue_target["next_requires_bridge"])
            self.assertFalse(repair_queue_target["next_requires_network"])
            self.assertFalse(repair_queue_target["next_requires_spend"])
            self.assertTrue(repair_queue_target["next_requires_unreal_editor"])
            self.assertTrue(repair_queue_target["no_auto_execute"])
            self.assertTrue(repair_queue_target["no_secret_echo"])
            self.assertTrue(repair_queue_target["no_git_mutation"])
            self.assertTrue(repair_queue_target["no_editor_mutation"])
            self.assertEqual(workflow_actions["record_evidence"]["arguments"]["evidence_type"], "readiness_repair_queue")
            self.assertIn("verify_unreal_bridge_reachability", workflow_actions["record_evidence"]["arguments"]["artifacts"])
            self.assertIn("ordered blocker repair queue", workflow_actions["record_evidence"]["arguments"]["summary"])
            self.assertTrue(workflow_actions["record_platform_stability_review"]["enabled"])
            self.assertTrue(workflow_actions["record_platform_stability_review"]["records_evidence"])
            self.assertTrue(workflow_actions["record_platform_stability_review"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_platform_stability_review"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_platform_stability_review"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(
                workflow_actions["record_platform_stability_review"]["input_source"],
                "outputs.evidence_recording.items.record_platform_stability_review plus outputs.workflow_actions.review_platform_preflight_gate",
            )
            self.assertEqual(
                workflow_actions["record_platform_stability_review"]["target_evidence_item_id"],
                "record_platform_stability_review",
            )
            self.assertEqual(
                workflow_actions["record_platform_stability_review"]["target_evidence_context"]["evidence_type"],
                "platform_stability_review",
            )
            self.assertNotIn("readiness_repair_queue", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("dirty_promotion_review", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("generated_asset", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("generated_animation", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("paid_generation_evidence", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("bridge_ping_receipt", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("provider_config_review", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("chat_cockpit_start_receipt", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("runtime_verification", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("queued_action", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            self.assertNotIn("feature_completion_contract", workflow_actions["record_platform_stability_review"]["target_evidence_context"])
            platform_stability_context = workflow_actions["record_platform_stability_review"]["target_evidence_context"]["platform_stability_review"]
            self.assertEqual(platform_stability_context["schema"], "unreal_mcp_platform_stability_review_receipt.v1")
            self.assertEqual(platform_stability_context["receipt_path"], "Saved\\PlatformStabilityReview\\last_review_receipt.json")
            self.assertEqual(platform_stability_context["required_command"], "python scripts\\write_platform_stability_review.py")
            self.assertTrue(platform_stability_context["ready_for_platform_stability"])
            self.assertFalse(platform_stability_context["ready_for_wip_promotion"])
            self.assertEqual(platform_stability_context["platform_missing_gate_count"], 0)
            self.assertGreaterEqual(platform_stability_context["wip_promotion_missing_gate_count"], 1)
            self.assertIn("dirty_promotion_review_receipt_current", platform_stability_context)
            self.assertIn("dirty_promotion_review_receipt_stale", platform_stability_context)
            self.assertIn("dirty_promotion_review_receipt_signature_match", platform_stability_context)
            self.assertIn("dirty_target_review_group", platform_stability_context)
            self.assertIn("dirty_target_review_status", platform_stability_context)
            self.assertIn("dirty_target_review_recorded_evidence_count", platform_stability_context)
            self.assertIn("dirty_target_review_human_approval_recorded", platform_stability_context)
            self.assertIn("dirty_target_review_merge_policy", platform_stability_context)
            self.assertIn("dirty_target_review_previous_evidence_merged", platform_stability_context)
            self.assertIn("dirty_target_review_reset_evidence", platform_stability_context)
            self.assertIn("dirty_target_review_missing_evidence_preview", platform_stability_context)
            self.assertIn("dirty_target_review_focused_test_command_preview", platform_stability_context)
            if platform_stability_context["dirty_target_review_group"]:
                self.assertGreaterEqual(platform_stability_context["dirty_target_review_missing_evidence_count"], 1)
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    platform_stability_context["dirty_target_review_missing_evidence_preview"],
                )
                self.assertFalse(platform_stability_context["dirty_target_review_promotion_allowed_after_receipt"])
            self.assertTrue(platform_stability_context["tool_registry_reproducible"])
            self.assertGreaterEqual(platform_stability_context["tool_count"], 1)
            self.assertEqual(platform_stability_context["tool_count"], platform_stability_context["recorded_tool_count"])
            self.assertGreaterEqual(platform_stability_context["partial_tool_count"], 0)
            self.assertGreaterEqual(platform_stability_context["blocking_gate_count"], 1)
            self.assertIn("blueprint_pre_read_evidence", platform_stability_context["blocking_gate_preview"])
            self.assertIn("blueprint_compile_plan", platform_stability_context["blocking_gate_preview"])
            self.assertGreaterEqual(platform_stability_context["readiness_repair_action_count"], 1)
            self.assertIn("readiness_repair_recommended_next", platform_stability_context)
            self.assertIn("readiness_repair_next_gate", platform_stability_context)
            self.assertIn("readiness_repair_next_tool", platform_stability_context)
            self.assertIsInstance(platform_stability_context["readiness_repair_next_requires_bridge"], bool)
            self.assertIsInstance(platform_stability_context["readiness_repair_next_requires_network"], bool)
            self.assertIsInstance(platform_stability_context["readiness_repair_next_requires_spend"], bool)
            self.assertTrue(platform_stability_context["readiness_repair_action_preview"])
            self.assertIn("gate", platform_stability_context["readiness_repair_action_preview"][0])
            self.assertIn(platform_stability_context["test_lane_state"], {"ok", "safe"})
            self.assertTrue(platform_stability_context["paid_provider_smoke_contract_ok"])
            self.assertFalse(platform_stability_context["paid_provider_smoke_manual_spend_required"])
            self.assertTrue(platform_stability_context["paid_provider_smoke_no_task_submission"])
            self.assertTrue(platform_stability_context["paid_provider_smoke_no_download"])
            self.assertTrue(platform_stability_context["paid_provider_smoke_no_import"])
            self.assertIn(platform_stability_context["paid_generation_evidence_receipt_state"], {"missing", "missing_evidence", "ready"})
            self.assertEqual(platform_stability_context["paid_generation_evidence_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
            self.assertEqual(platform_stability_context["paid_generation_evidence_required_command"], "python scripts\\write_paid_generation_evidence_review.py")
            self.assertFalse(platform_stability_context["paid_generation_mesh_wallet_evidence_recorded"])
            self.assertFalse(platform_stability_context["paid_generation_animation_allowance_evidence_recorded"])
            self.assertFalse(platform_stability_context["paid_generation_spend_confirmation_recorded"])
            self.assertEqual(platform_stability_context["paid_generation_mesh_provider"], "tripo")
            self.assertEqual(platform_stability_context["paid_generation_animation_provider"], "uthana")
            self.assertEqual(len(platform_stability_context["paid_generation_operator_command_handoff"]), 3)
            self.assertEqual(
                platform_stability_context["paid_generation_operator_command_handoff"][0]["id"],
                "record_masked_tripo_wallet_evidence",
            )
            self.assertEqual(
                platform_stability_context["paid_generation_operator_command_handoff"][1]["id"],
                "record_masked_uthana_allowance_evidence",
            )
            self.assertIn(platform_stability_context["blueprint_mutation_evidence_receipt_state"], {"missing", "missing_evidence", "ready"})
            self.assertEqual(
                platform_stability_context["blueprint_mutation_evidence_receipt_path"],
                "Saved\\BlueprintMutationEvidence\\last_review_receipt.json",
            )
            self.assertEqual(
                platform_stability_context["blueprint_mutation_evidence_required_command"],
                "python scripts\\write_blueprint_mutation_evidence_review.py",
            )
            self.assertEqual(len(platform_stability_context["blueprint_mutation_operator_command_handoff"]), 3)
            self.assertEqual(
                platform_stability_context["blueprint_mutation_operator_command_handoff"][0]["id"],
                "record_blueprint_pre_read_evidence",
            )
            self.assertTrue(platform_stability_context["blueprint_mutation_operator_command_handoff"][0]["no_blueprint_mutation"])
            self.assertFalse(platform_stability_context["blueprint_mutation_pre_read_evidence_recorded"])
            self.assertFalse(platform_stability_context["blueprint_mutation_compile_plan_recorded"])
            self.assertFalse(platform_stability_context["blueprint_mutation_readback_plan_recorded"])
            self.assertTrue(platform_stability_context["blueprint_mutation_evidence_no_editor_mutation"])
            self.assertTrue(platform_stability_context["blueprint_mutation_evidence_no_blueprint_mutation"])
            self.assertTrue(platform_stability_context["blueprint_mutation_evidence_no_compile"])
            self.assertTrue(platform_stability_context["no_mutation_test_ok"])
            self.assertEqual(platform_stability_context["no_mutation_test_status"], "success")
            self.assertEqual(platform_stability_context["no_mutation_test_mutation_count"], 0)
            self.assertEqual(platform_stability_context["no_mutation_test_exit_code"], 0)
            self.assertGreater(platform_stability_context["no_mutation_test_tracked_file_count"], 0)
            self.assertTrue(platform_stability_context["no_mutation_test_snapshot_digest_match"])
            self.assertEqual(platform_stability_context["no_mutation_test_snapshot_scope"], "git_tracked_worktree")
            self.assertTrue(platform_stability_context["no_mutation_test_snapshot_hash_algorithm"].startswith("sha256("))
            self.assertTrue(platform_stability_context["high_value_wrapper_ok"])
            self.assertIn(platform_stability_context["build_wrapper_status"], {"present", "ready"})
            self.assertEqual(platform_stability_context["last_plugin_build_status"], "success")
            self.assertTrue(platform_stability_context["no_provider_call"])
            self.assertTrue(platform_stability_context["no_editor_mutation"])
            self.assertTrue(platform_stability_context["no_git_mutation"])
            self.assertIn(
                "receipt:Saved\\PlatformStabilityReview\\last_review_receipt.json",
                workflow_actions["record_platform_stability_review"]["arguments"]["artifacts"],
            )
            self.assertIn("paid_evidence_receipt:missing_evidence", workflow_actions["record_platform_stability_review"]["arguments"]["artifacts"])
            self.assertIn(
                "paid_operator_command_handoff:record_masked_tripo_wallet_evidence",
                workflow_actions["record_platform_stability_review"]["arguments"]["artifacts"],
            )
            self.assertIn(
                "paid_operator_command_handoff:record_masked_uthana_allowance_evidence",
                workflow_actions["record_platform_stability_review"]["arguments"]["artifacts"],
            )
            self.assertTrue(workflow_actions["record_dirty_promotion_review"]["enabled"])
            self.assertTrue(workflow_actions["record_dirty_promotion_review"]["records_evidence"])
            self.assertTrue(workflow_actions["record_dirty_promotion_review"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_dirty_promotion_review"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_dirty_promotion_review"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(
                workflow_actions["record_dirty_promotion_review"]["input_source"],
                "outputs.evidence_recording.items.record_dirty_promotion_review plus outputs.workflow_actions.review_wip_promotion_gate",
            )
            self.assertEqual(
                workflow_actions["record_dirty_promotion_review"]["target_evidence_item_id"],
                "record_dirty_promotion_review",
            )
            self.assertEqual(
                workflow_actions["record_dirty_promotion_review"]["target_evidence_context"]["evidence_type"],
                "dirty_promotion_review",
            )
            self.assertNotIn("generated_asset", workflow_actions["record_dirty_promotion_review"]["target_evidence_context"])
            self.assertNotIn("generated_animation", workflow_actions["record_dirty_promotion_review"]["target_evidence_context"])
            self.assertNotIn("paid_generation_evidence", workflow_actions["record_dirty_promotion_review"]["target_evidence_context"])
            self.assertNotIn("runtime_verification", workflow_actions["record_dirty_promotion_review"]["target_evidence_context"])
            self.assertNotIn("queued_action", workflow_actions["record_dirty_promotion_review"]["target_evidence_context"])
            self.assertNotIn("feature_completion_contract", workflow_actions["record_dirty_promotion_review"]["target_evidence_context"])
            dirty_action_context = workflow_actions["record_dirty_promotion_review"]["target_evidence_context"]["dirty_promotion_review"]
            self.assertEqual(dirty_action_context["receipt_path"], "Saved\\DirtyPromotionReview\\last_review_receipt.json")
            self.assertEqual(dirty_action_context["required_command"], "python scripts\\write_dirty_promotion_review.py")
            self.assertIn("target_review_group", dirty_action_context)
            self.assertIn("target_review_status", dirty_action_context)
            self.assertIn("target_review_recorded_evidence_count", dirty_action_context)
            self.assertIn("target_review_human_approval_recorded", dirty_action_context)
            self.assertIn("target_review_missing_evidence_preview", dirty_action_context)
            self.assertIn("target_review_required_evidence_preview", dirty_action_context)
            self.assertIn("target_review_decision_prompt_preview", dirty_action_context)
            self.assertIn("target_review_receipt_command_template", dirty_action_context)
            self.assertIn("target_review_approval_receipt_command_template", dirty_action_context)
            self.assertIn("target_review_receipt_command_policy", dirty_action_context)
            self.assertIn("target_review_operator_command_handoff", dirty_action_context)
            self.assertEqual(len(dirty_action_context["target_review_operator_command_handoff"]), 2)
            self.assertFalse(dirty_action_context["target_review_operator_command_handoff"][0]["approval_flag_included"])
            self.assertTrue(dirty_action_context["target_review_operator_command_handoff"][1]["approval_flag_included"])
            self.assertIn("target_review_focused_test_command_handoff", dirty_action_context)
            self.assertGreaterEqual(len(dirty_action_context["target_review_focused_test_command_handoff"]), 1)
            self.assertEqual(dirty_action_context["target_review_focused_test_command_handoff"][0]["command_kind"], "local_validation")
            self.assertTrue(dirty_action_context["target_review_focused_test_command_handoff"][0]["no_git_mutation"])
            self.assertIn("target_review_pending_human_approval_only", dirty_action_context)
            self.assertIn("target_review_human_approval_gate", dirty_action_context)
            self.assertIn("target_review_human_approval_command_handoff", dirty_action_context)
            self.assertIn("--target-owner-or-source", dirty_action_context["target_review_receipt_command_template"])
            self.assertNotIn("--target-human-approval-recorded", dirty_action_context["target_review_receipt_command_template"])
            self.assertIn("--target-human-approval-recorded", dirty_action_context["target_review_approval_receipt_command_template"])
            self.assertIn("target_review_focused_test_command_preview", dirty_action_context)
            if dirty_action_context["target_review_group"]:
                self.assertGreaterEqual(dirty_action_context["target_review_missing_evidence_count"], 1)
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    dirty_action_context["target_review_missing_evidence_preview"],
                )
                self.assertIn(
                    "human_approval_before_stage_commit_merge",
                    dirty_action_context["target_review_required_evidence_preview"],
                )
                self.assertTrue(any("owner_or_source" in prompt for prompt in dirty_action_context["target_review_decision_prompt_preview"]))
                self.assertFalse(dirty_action_context["target_review_promotion_allowed_after_receipt"])
            if dirty_action_context["target_review_focused_test_command_count"]:
                self.assertIn("python", " ".join(dirty_action_context["target_review_focused_test_command_preview"]).lower())
            self.assertTrue(dirty_action_context["no_git_mutation"])
            self.assertTrue(dirty_action_context["no_stage"])
            self.assertTrue(dirty_action_context["no_commit"])
            self.assertTrue(dirty_action_context["no_branch_or_merge"])
            self.assertTrue(dirty_action_context["no_editor_mutation"])
            self.assertTrue(dirty_action_context["no_provider_call"])
            self.assertIn(
                "receipt:Saved\\DirtyPromotionReview\\last_review_receipt.json",
                workflow_actions["record_dirty_promotion_review"]["arguments"]["artifacts"],
            )
            self.assertTrue(workflow_actions["record_provider_config_review"]["enabled"])
            self.assertTrue(workflow_actions["record_provider_config_review"]["records_evidence"])
            self.assertTrue(workflow_actions["record_provider_config_review"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_provider_config_review"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_provider_config_review"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(
                workflow_actions["record_provider_config_review"]["input_source"],
                "outputs.evidence_recording.items.record_provider_config_review plus outputs.workflow_actions.review_provider_config_gate",
            )
            self.assertEqual(
                workflow_actions["record_provider_config_review"]["target_evidence_item_id"],
                "record_provider_config_review",
            )
            self.assertEqual(
                workflow_actions["record_provider_config_review"]["target_evidence_context"]["evidence_type"],
                "provider_config_review",
            )
            self.assertNotIn("readiness_repair_queue", workflow_actions["record_provider_config_review"]["target_evidence_context"])
            self.assertNotIn("dirty_promotion_review", workflow_actions["record_provider_config_review"]["target_evidence_context"])
            self.assertNotIn("generated_asset", workflow_actions["record_provider_config_review"]["target_evidence_context"])
            self.assertNotIn("generated_animation", workflow_actions["record_provider_config_review"]["target_evidence_context"])
            self.assertNotIn("paid_generation_evidence", workflow_actions["record_provider_config_review"]["target_evidence_context"])
            self.assertNotIn("bridge_ping_receipt", workflow_actions["record_provider_config_review"]["target_evidence_context"])
            self.assertNotIn("runtime_verification", workflow_actions["record_provider_config_review"]["target_evidence_context"])
            self.assertNotIn("queued_action", workflow_actions["record_provider_config_review"]["target_evidence_context"])
            self.assertNotIn("feature_completion_contract", workflow_actions["record_provider_config_review"]["target_evidence_context"])
            provider_config_review = workflow_actions["record_provider_config_review"]["target_evidence_context"]["provider_config_review"]
            self.assertEqual(provider_config_review["schema"], "unreal_mcp_provider_config_review_receipt.v1")
            self.assertEqual(provider_config_review["receipt_path"], "Saved\\ProviderConfigReview\\last_review_receipt.json")
            self.assertEqual(provider_config_review["required_command"], "python scripts\\write_provider_config_review.py")
            self.assertEqual(
                provider_config_review["operator_command_handoff"][0]["id"],
                "write_provider_config_review_receipt",
            )
            self.assertFalse(provider_config_review["operator_command_handoff"][0]["requires_provider_network"])
            self.assertTrue(provider_config_review["operator_command_handoff"][0]["no_provider_call"])
            self.assertEqual(provider_config_review["provider"], "tripo")
            self.assertEqual(provider_config_review["animation_provider"], "uthana")
            self.assertTrue(provider_config_review["provider_api_key_configured"])
            self.assertTrue(provider_config_review["animation_provider_api_key_configured"])
            self.assertIn(provider_config_review["provider_api_key_source"], {"env", "secrets"})
            self.assertIn(provider_config_review["animation_provider_api_key_source"], {"env", "secrets"})
            self.assertTrue(provider_config_review["provider_secrets_gitignored"])
            self.assertTrue(provider_config_review["provider_settings_gitignored"])
            self.assertTrue(provider_config_review["masked_status_only"])
            self.assertFalse(provider_config_review["raw_key_returned"])
            self.assertEqual(provider_config_review["save_tool"], "gen_save_provider_config")
            self.assertIn("gen_get_provider_config", provider_config_review["proof_tool"])
            self.assertTrue(provider_config_review["no_raw_key"])
            self.assertTrue(provider_config_review["no_provider_call"])
            self.assertTrue(provider_config_review["no_wallet_check"])
            self.assertTrue(provider_config_review["no_credit_reservation"])
            self.assertTrue(provider_config_review["no_spend_confirmation"])
            self.assertTrue(provider_config_review["no_editor_mutation"])
            self.assertIn(
                "receipt:Saved\\ProviderConfigReview\\last_review_receipt.json",
                workflow_actions["record_provider_config_review"]["arguments"]["artifacts"],
            )
            self.assertNotIn("api_key_masked", json.dumps(workflow_actions["record_provider_config_review"]))
            self.assertTrue(workflow_actions["record_bridge_ping_receipt"]["enabled"])
            self.assertTrue(workflow_actions["record_bridge_ping_receipt"]["records_evidence"])
            self.assertTrue(workflow_actions["record_bridge_ping_receipt"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_bridge_ping_receipt"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_bridge_ping_receipt"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(
                workflow_actions["record_bridge_ping_receipt"]["input_source"],
                "outputs.evidence_recording.items.record_bridge_ping_receipt plus outputs.workflow_actions.review_live_editor_bridge_gate",
            )
            self.assertEqual(
                workflow_actions["record_bridge_ping_receipt"]["target_evidence_item_id"],
                "record_bridge_ping_receipt",
            )
            self.assertEqual(
                workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"]["evidence_type"],
                "bridge_ping_receipt",
            )
            self.assertNotIn("readiness_repair_queue", workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"])
            self.assertNotIn("dirty_promotion_review", workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"])
            self.assertNotIn("generated_asset", workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"])
            self.assertNotIn("generated_animation", workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"])
            self.assertNotIn("paid_generation_evidence", workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"])
            self.assertNotIn("runtime_verification", workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"])
            self.assertNotIn("queued_action", workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"])
            self.assertNotIn("feature_completion_contract", workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"])
            bridge_context = workflow_actions["record_bridge_ping_receipt"]["target_evidence_context"]["bridge_ping_receipt"]
            self.assertEqual(bridge_context["schema"], "unreal_mcp_bridge_ping_receipt.v1")
            self.assertEqual(bridge_context["receipt_path"], "Saved\\BridgePing\\last_ping_receipt.json")
            self.assertEqual(bridge_context["required_command"], "python scripts\\bridge_ping.py")
            self.assertFalse(bridge_context["successful_bridge_ping"])
            self.assertFalse(bridge_context["bridge_ready"])
            self.assertFalse(bridge_context["bridge_tcp_ready"])
            self.assertEqual(bridge_context["bridge_host"], "127.0.0.1")
            self.assertEqual(bridge_context["bridge_port"], 55655)
            self.assertFalse(bridge_context["editor_mutation_allowed"])
            self.assertGreaterEqual(bridge_context["blueprint_missing_gate_count"], 1)
            self.assertEqual(bridge_context["operator_command_handoff"][0]["id"], "verify_unreal_bridge_ping")
            self.assertTrue(bridge_context["operator_command_handoff"][0]["requires_bridge"])
            self.assertTrue(bridge_context["operator_command_handoff"][0]["no_editor_mutation"])
            self.assertTrue(bridge_context["no_editor_mutation"])
            self.assertTrue(bridge_context["no_pie_run"])
            self.assertTrue(bridge_context["no_provider_call"])
            self.assertTrue(bridge_context["no_git_mutation"])
            self.assertTrue(bridge_context["stop_before_editor_or_pie"])
            self.assertIn(
                "receipt:Saved\\BridgePing\\last_ping_receipt.json",
                workflow_actions["record_bridge_ping_receipt"]["arguments"]["artifacts"],
            )
            self.assertTrue(workflow_actions["record_chat_cockpit_start_receipt"]["enabled"])
            self.assertTrue(workflow_actions["record_chat_cockpit_start_receipt"]["records_evidence"])
            self.assertTrue(workflow_actions["record_chat_cockpit_start_receipt"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_chat_cockpit_start_receipt"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_chat_cockpit_start_receipt"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(
                workflow_actions["record_chat_cockpit_start_receipt"]["input_source"],
                "outputs.evidence_recording.items.record_chat_cockpit_start_receipt plus outputs.workflow_actions.review_platform_preflight_gate",
            )
            self.assertEqual(
                workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_item_id"],
                "record_chat_cockpit_start_receipt",
            )
            self.assertEqual(
                workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"]["evidence_type"],
                "chat_cockpit_start_receipt",
            )
            self.assertNotIn("readiness_repair_queue", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            self.assertNotIn("dirty_promotion_review", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            self.assertNotIn("generated_asset", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            self.assertNotIn("generated_animation", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            self.assertNotIn("paid_generation_evidence", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            self.assertNotIn("bridge_ping_receipt", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            self.assertNotIn("provider_config_review", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            self.assertNotIn("runtime_verification", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            self.assertNotIn("queued_action", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            self.assertNotIn("feature_completion_contract", workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"])
            chat_start_context = workflow_actions["record_chat_cockpit_start_receipt"]["target_evidence_context"]["chat_cockpit_start_receipt"]
            self.assertEqual(chat_start_context["schema"], "unreal_mcp_chat_cockpit_start_receipt.v1")
            self.assertTrue(chat_start_context["chat_ready"])
            self.assertTrue(chat_start_context["chat_tcp_ready"])
            self.assertIn("http://127.0.0.1:8000", chat_start_context["chat_base_url"])
            self.assertIn("/chat/history", chat_start_context["chat_health_endpoint"])
            self.assertEqual(chat_start_context["startup_script"], "scripts\\start_chat_cockpit_server.ps1")
            self.assertEqual(chat_start_context["startup_receipt_path"], "Saved\\ChatCockpit\\last_start_receipt.json")
            self.assertIn("chat", chat_start_context["proof_command"].lower())
            self.assertTrue(chat_start_context["no_process_start"])
            self.assertTrue(chat_start_context["no_port_kill"])
            self.assertTrue(chat_start_context["no_editor_mutation"])
            self.assertTrue(chat_start_context["no_provider_call"])
            self.assertTrue(chat_start_context["no_git_mutation"])
            self.assertIn(
                "receipt:Saved\\ChatCockpit\\last_start_receipt.json",
                workflow_actions["record_chat_cockpit_start_receipt"]["arguments"]["artifacts"],
            )
            self.assertTrue(workflow_actions["record_queued_action_evidence"]["enabled"])
            self.assertTrue(workflow_actions["record_queued_action_evidence"]["records_evidence"])
            self.assertTrue(workflow_actions["record_queued_action_evidence"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_queued_action_evidence"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_queued_action_evidence"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(workflow_actions["record_queued_action_evidence"]["input_source"], "outputs.evidence_recording.items.record_editor_queue_1 plus outputs.next_safe_step")
            self.assertEqual(workflow_actions["record_queued_action_evidence"]["target_evidence_item_id"], "record_editor_queue_1")
            self.assertEqual(workflow_actions["record_queued_action_evidence"]["target_evidence_context"]["evidence_type"], "editor_queue")
            self.assertEqual(workflow_actions["record_queued_action_evidence"]["target_evidence_context"]["state"], "blocked")
            self.assertEqual(workflow_actions["record_queued_action_evidence"]["target_evidence_context"]["artifact_count"], 1)
            queued_context = workflow_actions["record_queued_action_evidence"]["target_evidence_context"]["queued_action"]
            self.assertEqual(queued_context["queue_name"], "editor_queue")
            self.assertEqual(queued_context["next_action_id"], "create_placeholder_folder")
            self.assertEqual(queued_context["next_action_tool"], "create_folder")
            self.assertEqual(queued_context["feature_template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(queued_context["feature_template_next_operation_id"], "enemy_patrol_chase_attack_01")
            self.assertEqual(queued_context["feature_template_next_operation_type"], "ai_blackboard_behavior_tree")
            self.assertIn("set_behavior_tree_blackboard", queued_context["feature_template_next_operation_tool_preview"])
            self.assertIn("unreal_bridge_reachable", queued_context["feature_template_next_operation_required_before_preview"])
            self.assertIn("graph_or_component_readback", queued_context["feature_template_next_operation_required_after_preview"])
            self.assertIn("compile report missing or failed", queued_context["feature_template_next_operation_stop_if_missing_preview"])
            self.assertEqual(queued_context["action_count"], 2)
            self.assertEqual(queued_context["preview_action_count"], 2)
            self.assertTrue(queued_context["bridge_blocked"])
            self.assertFalse(queued_context["can_execute_now"])
            self.assertEqual(queued_context["argument_keys"], ["path"])
            self.assertTrue(queued_context["requires_successful_bridge_ping_before_execution"])
            self.assertTrue(queued_context["no_auto_execute"])
            self.assertTrue(queued_context["no_editor_mutation"])
            self.assertTrue(queued_context["no_pie_run"])
            self.assertTrue(queued_context["no_provider_call"])
            self.assertTrue(queued_context["no_git_mutation"])
            self.assertEqual(workflow_actions["record_queued_action_evidence"]["arguments"]["evidence_type"], "editor_queue")
            self.assertEqual(workflow_actions["record_queued_action_evidence"]["arguments"]["artifacts"], ["compile report"])
            self.assertTrue(workflow_actions["record_generated_asset_evidence"]["enabled"])
            self.assertTrue(workflow_actions["record_generated_asset_evidence"]["records_evidence"])
            self.assertTrue(workflow_actions["record_generated_asset_evidence"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_generated_asset_evidence"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_generated_asset_evidence"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(workflow_actions["record_generated_asset_evidence"]["input_source"], "outputs.evidence_recording.items.record_generated_asset_quality_gate")
            self.assertEqual(workflow_actions["record_generated_asset_evidence"]["target_evidence_item_id"], "record_generated_asset_quality_gate")
            self.assertEqual(workflow_actions["record_generated_asset_evidence"]["target_evidence_context"]["evidence_type"], "generated_asset_quality_gate")
            self.assertEqual(workflow_actions["record_generated_asset_evidence"]["target_evidence_context"]["state"], "pending")
            self.assertEqual(workflow_actions["record_generated_asset_evidence"]["target_evidence_context"]["artifact_count"], 8)
            generated_asset_context = workflow_actions["record_generated_asset_evidence"]["target_evidence_context"]["generated_asset"]
            self.assertEqual(generated_asset_context["asset_id"], "asset_01")
            self.assertEqual(generated_asset_context["asset_name"], "SM_ObjectiveBeacon")
            self.assertEqual(generated_asset_context["asset_role"], "objective_marker")
            self.assertEqual(generated_asset_context["provider"], "tripo")
            self.assertEqual(generated_asset_context["state"], "provider_pending")
            self.assertIn("provider task", generated_asset_context["next_gate"])
            self.assertEqual(generated_asset_context["expected_import_path"], "/Game/Generated/Assets/SM_ObjectiveBeacon")
            self.assertTrue(generated_asset_context["has_placeholder"])
            self.assertFalse(generated_asset_context["import_or_quality_pass_allowed"])
            self.assertTrue(generated_asset_context["requires_successful_bridge_ping_before_import_or_quality"])
            self.assertTrue(generated_asset_context["requires_quality_evidence_before_replacement"])
            self.assertTrue(generated_asset_context["no_provider_call"])
            self.assertTrue(generated_asset_context["no_task_submission"])
            self.assertTrue(generated_asset_context["no_download"])
            self.assertTrue(generated_asset_context["no_import"])
            self.assertTrue(generated_asset_context["no_editor_mutation"])
            self.assertTrue(generated_asset_context["no_git_mutation"])
            self.assertEqual(workflow_actions["record_generated_asset_evidence"]["arguments"]["evidence_type"], "generated_asset_quality_gate")
            self.assertIn("asset:SM_ObjectiveBeacon", workflow_actions["record_generated_asset_evidence"]["arguments"]["artifacts"])
            self.assertIn("state:provider_pending", workflow_actions["record_generated_asset_evidence"]["arguments"]["artifacts"])
            self.assertTrue(workflow_actions["record_paid_generation_evidence"]["enabled"])
            self.assertTrue(workflow_actions["record_paid_generation_evidence"]["records_evidence"])
            self.assertTrue(workflow_actions["record_paid_generation_evidence"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_paid_generation_evidence"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_paid_generation_evidence"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(
                workflow_actions["record_paid_generation_evidence"]["input_source"],
                "outputs.evidence_recording.items.record_paid_generation_evidence plus outputs.workflow_actions.review_provider_spend_gate",
            )
            self.assertEqual(workflow_actions["record_paid_generation_evidence"]["target_evidence_item_id"], "record_paid_generation_evidence")
            self.assertEqual(workflow_actions["record_paid_generation_evidence"]["target_evidence_context"]["evidence_type"], "paid_generation_evidence")
            self.assertEqual(workflow_actions["record_paid_generation_evidence"]["target_evidence_context"]["state"], "pending")
            self.assertGreaterEqual(workflow_actions["record_paid_generation_evidence"]["target_evidence_context"]["artifact_count"], 20)
            self.assertNotIn("dirty_promotion_review", workflow_actions["record_paid_generation_evidence"]["target_evidence_context"])
            self.assertNotIn("generated_asset", workflow_actions["record_paid_generation_evidence"]["target_evidence_context"])
            self.assertNotIn("generated_animation", workflow_actions["record_paid_generation_evidence"]["target_evidence_context"])
            self.assertNotIn("runtime_verification", workflow_actions["record_paid_generation_evidence"]["target_evidence_context"])
            self.assertNotIn("queued_action", workflow_actions["record_paid_generation_evidence"]["target_evidence_context"])
            self.assertNotIn("feature_completion_contract", workflow_actions["record_paid_generation_evidence"]["target_evidence_context"])
            paid_context = workflow_actions["record_paid_generation_evidence"]["target_evidence_context"]["paid_generation_evidence"]
            self.assertEqual(paid_context["review_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
            self.assertFalse(paid_context["mesh_wallet_evidence_recorded"])
            self.assertFalse(paid_context["animation_allowance_evidence_recorded"])
            self.assertFalse(paid_context["explicit_usage_approval_recorded"])
            self.assertIn(paid_context["review_receipt_state"], {"missing", "missing_evidence"})
            self.assertEqual(paid_context["mesh_wallet_tool"], "gen_tripo_get_credit_balance")
            self.assertIn("gen_uthana_get_account", paid_context["animation_allowance_tools"])
            self.assertIn("gen_uthana_get_account(include_user=False)", " ".join(paid_context["wallet_evidence_review_steps"]))
            self.assertIn("--mesh-wallet-evidence-recorded", paid_context["wallet_evidence_receipt_command_template"])
            self.assertIn("--record-masked-tripo-wallet-evidence", paid_context["mesh_wallet_evidence_receipt_command_template"])
            self.assertIn("--record-masked-uthana-allowance-evidence", paid_context["animation_allowance_receipt_command_template"])
            self.assertEqual(len(paid_context["operator_command_handoff"]), 3)
            self.assertEqual(paid_context["operator_command_handoff"][0]["id"], "record_masked_tripo_wallet_evidence")
            self.assertEqual(paid_context["operator_command_handoff"][1]["id"], "record_masked_uthana_allowance_evidence")
            self.assertEqual(paid_context["operator_command_handoff"][2]["id"], "record_explicit_spend_and_usage_approval")
            self.assertFalse(paid_context["operator_command_handoff"][0]["approval_flags_included"])
            self.assertFalse(paid_context["operator_command_handoff"][1]["approval_flags_included"])
            self.assertTrue(paid_context["operator_command_handoff"][0]["no_provider_call"])
            self.assertTrue(paid_context["operator_command_handoff"][1]["no_provider_call"])
            self.assertTrue(paid_context["operator_command_handoff"][2]["approval_flags_included"])
            self.assertIn("explicit_uthana_usage_approval", paid_context["evidence_required_preview"])
            self.assertIn(
                "gen_uthana_get_account / gen_uthana_get_job / gen_uthana_check_download_allowed",
                " ".join(paid_context["no_spend_checks"]),
            )
            self.assertEqual(paid_context["fallback_tool"], "skill_compile_ide_companion_placeholder_manifest")
            self.assertTrue(paid_context["no_provider_call"])
            self.assertTrue(paid_context["no_credit_reservation"])
            self.assertTrue(paid_context["no_ledger_write"])
            self.assertEqual(workflow_actions["record_paid_generation_evidence"]["arguments"]["evidence_type"], "paid_generation_evidence")
            self.assertIn("receipt:Saved\\PaidGenerationEvidence\\last_review_receipt.json", workflow_actions["record_paid_generation_evidence"]["arguments"]["artifacts"])
            self.assertIn("mesh_wallet_tool:gen_tripo_get_credit_balance", workflow_actions["record_paid_generation_evidence"]["arguments"]["artifacts"])
            self.assertIn("animation_allowance_tool:gen_uthana_get_account", workflow_actions["record_paid_generation_evidence"]["arguments"]["artifacts"])
            self.assertIn(
                "operator_command_handoff:record_masked_tripo_wallet_evidence",
                workflow_actions["record_paid_generation_evidence"]["arguments"]["artifacts"],
            )
            self.assertIn(
                "operator_command_handoff:record_masked_uthana_allowance_evidence",
                workflow_actions["record_paid_generation_evidence"]["arguments"]["artifacts"],
            )
            self.assertIn("spend/usage approval", workflow_actions["record_paid_generation_evidence"]["arguments"]["summary"])
            self.assertTrue(workflow_actions["record_generated_animation_evidence"]["enabled"])
            self.assertTrue(workflow_actions["record_generated_animation_evidence"]["records_evidence"])
            self.assertTrue(workflow_actions["record_generated_animation_evidence"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_generated_animation_evidence"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_generated_animation_evidence"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(
                workflow_actions["record_generated_animation_evidence"]["input_source"],
                "outputs.evidence_recording.items.record_generated_animation_evidence plus outputs.workflow_actions.compile_generated_animation_evidence",
            )
            self.assertEqual(workflow_actions["record_generated_animation_evidence"]["target_evidence_item_id"], "record_generated_animation_evidence")
            self.assertEqual(workflow_actions["record_generated_animation_evidence"]["target_evidence_context"]["evidence_type"], "generated_animation_evidence")
            self.assertEqual(workflow_actions["record_generated_animation_evidence"]["target_evidence_context"]["state"], "pending")
            self.assertEqual(workflow_actions["record_generated_animation_evidence"]["target_evidence_context"]["artifact_count"], 10)
            generated_animation_context = workflow_actions["record_generated_animation_evidence"]["target_evidence_context"]["generated_animation"]
            self.assertEqual(generated_animation_context["animation_id"], "animation_01")
            self.assertEqual(generated_animation_context["animation_name"], "A_EnemyScout_PatrolWalk")
            self.assertEqual(generated_animation_context["provider"], "uthana")
            self.assertEqual(generated_animation_context["task_status"], "not_submitted")
            self.assertEqual(generated_animation_context["expected_import_path"], "/Game/Generated/Animations/A_EnemyScout_PatrolWalk")
            self.assertEqual(generated_animation_context["target_skeleton"], "UE5 Manny")
            self.assertEqual(
                generated_animation_context["quality_proof_contract_schema"],
                "unreal_mcp_generated_animation_quality_proof_contract.v1",
            )
            self.assertEqual(generated_animation_context["compile_tool"], "gen_compile_generated_animation_evidence")
            self.assertEqual(
                generated_animation_context["uthana_usage_contract_schema"],
                "unreal_mcp_uthana_animation_usage_contract.v1",
            )
            self.assertEqual(generated_animation_context["uthana_usage_receipt_path"], "Saved\\PaidGenerationEvidence\\last_review_receipt.json")
            self.assertIn("gen_uthana_get_account", generated_animation_context["uthana_allowance_tools"])
            self.assertEqual(
                generated_animation_context["uthana_usage_operator_command_handoff"][0]["id"],
                "record_masked_uthana_allowance_evidence",
            )
            self.assertEqual(
                generated_animation_context["uthana_usage_next_operator_command_handoff"]["id"],
                "record_masked_uthana_allowance_evidence",
            )
            self.assertTrue(generated_animation_context["no_provider_call"])
            self.assertTrue(generated_animation_context["no_task_submission"])
            self.assertIn("animation:A_EnemyScout_PatrolWalk", workflow_actions["record_generated_animation_evidence"]["arguments"]["artifacts"])
            self.assertIn("usage_receipt:Saved\\PaidGenerationEvidence\\last_review_receipt.json", workflow_actions["record_generated_animation_evidence"]["arguments"]["artifacts"])
            self.assertTrue(workflow_actions["record_feature_completion_contract"]["enabled"])
            self.assertTrue(workflow_actions["record_feature_completion_contract"]["records_evidence"])
            self.assertTrue(workflow_actions["record_feature_completion_contract"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_feature_completion_contract"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_feature_completion_contract"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(
                workflow_actions["record_feature_completion_contract"]["input_source"],
                "outputs.evidence_recording.items.record_feature_completion_contract plus outputs.work_order_template",
            )
            self.assertEqual(workflow_actions["record_feature_completion_contract"]["target_evidence_item_id"], "record_feature_completion_contract")
            self.assertEqual(workflow_actions["record_feature_completion_contract"]["target_evidence_context"]["evidence_type"], "feature_completion_contract")
            self.assertEqual(workflow_actions["record_feature_completion_contract"]["target_evidence_context"]["state"], "pending")
            self.assertEqual(workflow_actions["record_feature_completion_contract"]["target_evidence_context"]["artifact_count"], 10)
            completion_context = workflow_actions["record_feature_completion_contract"]["target_evidence_context"]["feature_completion_contract"]
            self.assertEqual(completion_context["schema"], "unreal_mcp_gameplay_feature_completion_contract.v1")
            self.assertEqual(completion_context["template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(completion_context["proof_gate_count"], 3)
            self.assertEqual(completion_context["required_evidence_count"], 6)
            self.assertIn("ide_companion_ledger_event", completion_context["required_evidence_preview"])
            self.assertIn("ledger_evidence_recorded", json.dumps(completion_context["proof_gate_preview"]))
            self.assertFalse(completion_context["completion_allowed"])
            self.assertTrue(completion_context["requires_all_proof_gates_before_complete"])
            self.assertTrue(completion_context["requires_all_required_evidence_before_complete"])
            self.assertTrue(completion_context["stop_before_complete_required"])
            self.assertTrue(completion_context["no_auto_complete"])
            self.assertTrue(completion_context["no_editor_mutation"])
            self.assertTrue(completion_context["no_pie_run"])
            self.assertTrue(completion_context["no_provider_call"])
            self.assertTrue(completion_context["no_git_mutation"])
            self.assertEqual(workflow_actions["record_feature_completion_contract"]["arguments"]["evidence_type"], "feature_completion_contract")
            self.assertIn("feature_template_packet", workflow_actions["record_feature_completion_contract"]["arguments"]["artifacts"])
            self.assertTrue(any("pie_validation_passed" in item for item in workflow_actions["record_feature_completion_contract"]["arguments"]["artifacts"]))
            self.assertTrue(workflow_actions["record_runtime_evidence"]["enabled"])
            self.assertTrue(workflow_actions["record_runtime_evidence"]["records_evidence"])
            self.assertTrue(workflow_actions["record_runtime_evidence"]["requires_ledger"])
            self.assertFalse(workflow_actions["record_runtime_evidence"]["requires_bridge"])
            self.assertEqual(workflow_actions["record_runtime_evidence"]["tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(workflow_actions["record_runtime_evidence"]["input_source"], "outputs.evidence_recording.items.record_runtime_verification")
            self.assertEqual(workflow_actions["record_runtime_evidence"]["target_evidence_item_id"], "record_runtime_verification")
            self.assertEqual(workflow_actions["record_runtime_evidence"]["target_evidence_context"]["evidence_type"], "runtime_verification")
            self.assertEqual(workflow_actions["record_runtime_evidence"]["target_evidence_context"]["state"], "blocked")
            self.assertEqual(workflow_actions["record_runtime_evidence"]["target_evidence_context"]["artifact_count"], 3)
            runtime_evidence_context = workflow_actions["record_runtime_evidence"]["target_evidence_context"]["runtime_verification"]
            self.assertEqual(runtime_evidence_context["target_phase"], "editor_implementation")
            self.assertTrue(runtime_evidence_context["bridge_blocked"])
            self.assertEqual(runtime_evidence_context["pie_validation_count"], 1)
            self.assertEqual(runtime_evidence_context["evidence_requirement_count"], 2)
            self.assertEqual(runtime_evidence_context["blocked_item_count"], 1)
            self.assertEqual(runtime_evidence_context["pending_item_count"], 2)
            self.assertIn("PIE log, viewport screenshot, and observed runtime state", runtime_evidence_context["runtime_proof_preview"])
            self.assertFalse(runtime_evidence_context["runtime_probe_allowed"])
            self.assertTrue(runtime_evidence_context["requires_successful_bridge_ping_before_runtime_probe"])
            self.assertTrue(runtime_evidence_context["no_pie_run"])
            self.assertTrue(runtime_evidence_context["no_editor_mutation"])
            self.assertTrue(runtime_evidence_context["no_provider_call"])
            self.assertTrue(runtime_evidence_context["no_git_mutation"])
            self.assertEqual(workflow_actions["record_runtime_evidence"]["arguments"]["evidence_type"], "runtime_verification")
            self.assertIn("PIE log", workflow_actions["record_runtime_evidence"]["arguments"]["artifacts"][0])
            self.assertTrue(workflow_actions["review_runtime_verification"]["enabled"])
            self.assertTrue(workflow_actions["review_runtime_verification"]["requires_ledger"])
            self.assertFalse(workflow_actions["review_runtime_verification"]["requires_bridge"])
            self.assertEqual(workflow_actions["review_runtime_verification"]["tool"], "chat_get_cockpit_overview")
            self.assertEqual(workflow_actions["review_runtime_verification"]["input_source"], "outputs.runtime_review plus outputs.runtime_verification")
            self.assertEqual(workflow_actions["review_runtime_verification"]["arguments"]["session_name"], "ide-companion")
            self.assertEqual(workflow_actions["review_runtime_verification"]["arguments"]["limit"], 50)
            runtime_context = workflow_actions["review_runtime_verification"]["target_runtime_review_context"]
            self.assertEqual(runtime_context["state"], "blocked")
            self.assertEqual(runtime_context["target_phase"], "editor_implementation")
            self.assertFalse(runtime_context["can_verify_now"])
            self.assertTrue(runtime_context["bridge_blocked"])
            self.assertEqual(runtime_context["pie_validation_count"], 1)
            self.assertEqual(runtime_context["evidence_requirement_count"], 2)
            self.assertEqual(runtime_context["blocked_item_count"], 1)
            self.assertEqual(runtime_context["pending_item_count"], 2)
            self.assertTrue(runtime_context["stop_after_runtime_probe"])
            self.assertTrue(workflow_actions["repair_failed_step"]["enabled"])
            self.assertEqual(workflow_actions["repair_failed_step"]["input_source"], "outputs.repair_loop.items")
            self.assertEqual(workflow_actions["repair_failed_step"]["arguments"]["target_phase"], "editor_implementation")
            self.assertEqual(workflow_actions["repair_failed_step"]["arguments"]["target_repair_id"], "repair_hint_1")
            self.assertEqual(workflow_actions["repair_failed_step"]["target_repair_id"], "repair_hint_1")
            self.assertIn("Blueprint compile fails", workflow_actions["repair_failed_step"]["target_repair_context"]["label"])
            self.assertEqual(workflow_actions["repair_failed_step"]["target_repair_context"]["recommended_tool"], "skill_compile_ide_companion_work_order")
            self.assertEqual(workflow_actions["repair_failed_step"]["target_repair_context"]["evidence_tool"], "skill_record_ide_companion_evidence")
            self.assertEqual(workflow_actions["repair_failed_step"]["target_repair_review_context"]["target_repair_id"], "repair_hint_1")
            self.assertEqual(workflow_actions["repair_failed_step"]["target_repair_review_context"]["state"], "blocked")
            self.assertEqual(workflow_actions["repair_failed_step"]["target_repair_review_context"]["failure_signal_count"], 4)
            self.assertEqual(workflow_actions["repair_failed_step"]["target_repair_review_context"]["blocked_count"], 3)
            self.assertEqual(workflow_actions["repair_failed_step"]["target_repair_review_context"]["needs_repair_count"], 1)
            self.assertEqual(workflow_actions["repair_failed_step"]["target_repair_review_context"]["recommended_tool"], "skill_compile_ide_companion_work_order")
            self.assertTrue(workflow_actions["repair_failed_step"]["target_repair_review_context"]["stop_after_repair_attempt"])
            repair_readiness = workflow_actions["repair_failed_step"]["target_repair_review_context"]["repair_execution_readiness"]
            self.assertEqual(repair_readiness["schema"], "unreal_mcp_chat_repair_execution_readiness.v1")
            self.assertEqual(repair_readiness["state"], "ready_to_plan")
            self.assertTrue(repair_readiness["can_compile_repair_work_order"])
            self.assertFalse(repair_readiness["can_apply_repair_now"])
            self.assertFalse(repair_readiness["can_record_repair_evidence"])
            self.assertEqual(repair_readiness["target_repair_id"], "repair_hint_1")
            self.assertEqual(repair_readiness["target_phase"], "editor_implementation")
            self.assertTrue(repair_readiness["requires_bridge_before_apply"])
            self.assertTrue(repair_readiness["bridge_blocked"])
            self.assertIn("unreal_bridge_reachable", repair_readiness["missing_gate_preview"])
            self.assertIn("failure_signal_reviewed", repair_readiness["required_before_plan_preview"])
            self.assertIn("blueprint_pre_read_evidence", repair_readiness["required_before_apply_preview"])
            self.assertIn("blueprint_compile_report", repair_readiness["required_after_apply_preview"])
            self.assertIn("readback still shows the failure", repair_readiness["stop_if_missing_preview"])
            self.assertEqual(repair_readiness["recommended_next"], "resolve_bridge_before_apply")
            self.assertEqual(repair_readiness["planning_tool"], "skill_compile_ide_companion_work_order")
            self.assertEqual(repair_readiness["evidence_tool"], "skill_record_ide_companion_evidence")
            self.assertTrue(repair_readiness["no_editor_mutation"])
            self.assertTrue(repair_readiness["stop_before_editor_mutation"])
            self.assertEqual(
                workflow_actions["repair_failed_step"]["target_repair_review_context"]["repair_execution_readiness_state"],
                "ready_to_plan",
            )
            self.assertTrue(workflow_actions["repair_failed_step"]["target_repair_review_context"]["can_compile_repair_work_order"])
            self.assertFalse(workflow_actions["repair_failed_step"]["target_repair_review_context"]["can_apply_repair_now"])
            self.assertEqual(
                workflow_actions["repair_failed_step"]["target_repair_review_context"]["repair_recommended_next"],
                "resolve_bridge_before_apply",
            )
            self.assertEqual(payload["evidence_timeline"][0]["phase_name"], "orient_to_project")
            self.assertEqual(payload["evidence_timeline"][1]["evidence_type"], "readiness")
            self.assertEqual(payload["evidence_timeline"][1]["artifact_count"], 2)
            self.assertEqual(payload["evidence_timeline"][1]["artifact_preview"][0], "preflight report")
            self.assertEqual(payload["evidence_timeline"][1]["artifact_preview"][1], "bridge_ping: offline")
            self.assertIn("unreal_bridge_reachable", payload["blocking_gates"])
            self.assertIn("editor_queue", {card["id"] for card in payload["cards"]})
            editor_queue_card = next(card for card in payload["cards"] if card["id"] == "editor_queue")
            self.assertEqual(editor_queue_card["details"]["feature_template_name"], "enemy_patrol_chase_attack")
            self.assertEqual(
                editor_queue_card["details"]["feature_template_next_operation_id"],
                "enemy_patrol_chase_attack_01",
            )
            self.assertIn(
                "set_behavior_tree_blackboard",
                editor_queue_card["details"]["feature_template_next_operation_tool_preview"],
            )
            self.assertIn(
                "graph_or_component_readback",
                editor_queue_card["details"]["feature_template_next_operation_required_after_preview"],
            )
            self.assertFalse(payload["suggested_actions"][-1]["enabled"])
            self.assertIn("Queued editor actions are present", payload["warnings"][-1])

    def test_asset_lifecycle_summary_surfaces_unsupported_provider_task_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            lifecycle_path = Path(tmp) / "ide-companion_asset_lifecycle.json"
            lifecycle_path.write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_generated_asset_lifecycle.v1",
                "session_name": "ide-companion",
                "preferred_provider": "tripo",
                "asset_count": 0,
                "animation_asset_count": 1,
                "assets": [],
                "animation_assets": [
                    {
                        "id": "animation_01",
                        "name": "A_EnemyScout_VideoReference",
                        "role": "enemy_patrol_locomotion",
                        "provider": "uthana",
                        "task_type": "video_to_motion",
                        "expected_import_path": "/Game/Generated/Animations/A_EnemyScout_VideoReference",
                        "provider_task": {
                            "status": "unsupported_task_type",
                            "motion_id": "",
                            "submit_tool": "",
                            "planned_submit_tool": "gen_uthana_video_to_motion",
                            "status_tool": "gen_uthana_get_motion",
                            "download_tool": "gen_uthana_download_motion",
                            "import_tool": "gen_uthana_import_animation_to_project",
                            "public_mcp_tool_available": False,
                            "unsupported_reason": "Uthana video_to_motion is planned provider capability but no public MCP submit tool is registered yet.",
                        },
                    },
                ],
                "unsupported_provider_task_count": 1,
                "unsupported_provider_task_preview": [
                    {
                        "id": "animation_01",
                        "name": "A_EnemyScout_VideoReference",
                        "provider": "uthana",
                        "task_type": "video_to_motion",
                        "planned_submit_tool": "gen_uthana_video_to_motion",
                        "unsupported_reason": "Uthana video_to_motion is planned provider capability but no public MCP submit tool is registered yet.",
                    },
                ],
            }), encoding="utf-8")

            summary = cockpit.asset_lifecycle_summary(lifecycle_path)
            overview = cockpit.build_cockpit_overview(
                session="ide-companion",
                message_limit=5,
                limit=5,
                chat_session_dir=Path(tmp) / "MCPChat",
                ledger_session_dir=Path(tmp),
            )

        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary["unsupported_provider_task_count"], 1)
        self.assertEqual(summary["unsupported_provider_task_preview"][0]["planned_submit_tool"], "gen_uthana_video_to_motion")
        animation = summary["preview_animation_assets"][0]
        self.assertEqual(animation["submit_tool"], "")
        self.assertEqual(animation["planned_submit_tool"], "gen_uthana_video_to_motion")
        self.assertFalse(animation["public_mcp_tool_available"])
        self.assertIn("no public MCP submit tool", animation["unsupported_reason"])
        generated_assets_card = next(card for card in overview["cards"] if card["id"] == "generated_assets")
        self.assertEqual(generated_assets_card["state"], "blocked")
        self.assertEqual(generated_assets_card["details"]["animation_asset_count"], 1)
        self.assertEqual(generated_assets_card["details"]["animation_pending_count"], 1)
        self.assertEqual(generated_assets_card["details"]["unsupported_provider_task_count"], 1)
        self.assertEqual(
            generated_assets_card["details"]["unsupported_provider_task_preview"][0]["planned_submit_tool"],
            "gen_uthana_video_to_motion",
        )
        self.assertEqual(generated_assets_card["details"]["animation_gate_state"], "blocked")
        self.assertEqual(generated_assets_card["details"]["animation_provider"], "uthana")
        self.assertEqual(generated_assets_card["details"]["animation_target_name"], "A_EnemyScout_VideoReference")
        self.assertEqual(generated_assets_card["details"]["animation_target_task_type"], "video_to_motion")
        self.assertEqual(generated_assets_card["details"]["animation_next_safe_action_id"], "implement_uthana_submit_tool_wrapper")
        self.assertEqual(generated_assets_card["details"]["animation_next_safe_action_tool"], "chat_get_cockpit_overview")
        self.assertEqual(
            generated_assets_card["details"]["animation_candidate_tool_after_unblocked"],
            "gen_uthana_video_to_motion",
        )
        self.assertIn("provider_submit_tool_missing", generated_assets_card["details"]["animation_missing_stage_preview"])
        self.assertIsInstance(generated_assets_card["details"]["animation_missing_editor_gate_preview"], list)
        self.assertEqual(
            generated_assets_card["details"]["animation_usage_receipt_path"],
            "Saved\\PaidGenerationEvidence\\last_review_receipt.json",
        )
        self.assertIn("confirm_usage=True", generated_assets_card["details"]["animation_usage_confirmation_field"])
        self.assertIn("registered public MCP submit tools", " ".join(overview["warnings"]))
        lifecycle_context = cockpit.generated_animation_lifecycle_context(
            asset_lifecycles=[summary],
            readiness_policy={
                "state": "blocked",
                "paid_animation_generation": {
                    "allowed": False,
                    "missing_gates": ["wallet_evidence_recorded", "spend_confirmation_recorded"],
                },
                "editor_mutation": {
                    "allowed": False,
                    "missing_gates": ["unreal_bridge_reachable"],
                },
            },
        )
        self.assertEqual(lifecycle_context["unsupported_provider_task_count"], 1)
        self.assertIn("provider_submit_tool_missing", lifecycle_context["missing_stage_preview"])
        self.assertEqual(lifecycle_context["target_animation"]["planned_submit_tool"], "gen_uthana_video_to_motion")
        self.assertFalse(lifecycle_context["target_animation"]["public_mcp_tool_available"])
        self.assertEqual(lifecycle_context["submit_tool"], "")
        self.assertEqual(lifecycle_context["planned_submit_tool"], "gen_uthana_video_to_motion")
        self.assertFalse(lifecycle_context["public_mcp_tool_available"])
        self.assertEqual(lifecycle_context["next_safe_action"]["action_id"], "implement_uthana_submit_tool_wrapper")
        self.assertEqual(lifecycle_context["next_safe_action"]["action_type"], "provider_wrapper_gap")
        self.assertFalse(lifecycle_context["next_safe_action"]["requires_provider_network"])

    def test_evidence_target_context_promotes_generated_asset_metadata(self):
        context = cockpit.evidence_target_context({
            "id": "record_generated_asset_quality_gate",
            "source": "generated_asset_quality_gate",
            "phase_name": "editor_implementation",
            "evidence_type": "generated_asset_quality_gate",
            "label": "Record generated asset proof for SM_ObjectiveBeacon",
            "state": "pending",
            "requires_bridge": False,
            "required_artifact_count": 6,
            "required_artifacts": [
                "asset:SM_ObjectiveBeacon",
                "state:provider_pending",
                "manifest:.mcp_artifacts/ide_companion_sessions/ide-companion_asset_lifecycle.json",
            ],
            "suggested_summary": "Record generated asset state.",
            "metadata": {
                "asset_id": "asset_01",
                "asset_name": "SM_ObjectiveBeacon",
                "asset_role": "objective_marker",
                "provider": "tripo",
                "state": "provider_pending",
                "task_status": "not_submitted",
                "next_gate": "Submit provider task after spend confirmation.",
                "manifest_path": ".mcp_artifacts/ide_companion_sessions/ide-companion_asset_lifecycle.json",
                "expected_import_path": "/Game/Generated/Assets/SM_ObjectiveBeacon",
                "has_placeholder": True,
                "quality_gate_count": 4,
                "quality_evidence_count": 1,
                "quality_gate_preview": ["viewport screenshot required"],
            },
        })
        self.assertEqual(context["artifact_preview"][0], "asset:SM_ObjectiveBeacon")
        self.assertIn("asset_name", context["metadata_keys"])
        self.assertEqual(context["generated_asset"]["asset_id"], "asset_01")
        self.assertEqual(context["generated_asset"]["asset_name"], "SM_ObjectiveBeacon")
        self.assertEqual(context["generated_asset"]["provider"], "tripo")
        self.assertEqual(context["generated_asset"]["expected_import_path"], "/Game/Generated/Assets/SM_ObjectiveBeacon")
        self.assertTrue(context["generated_asset"]["has_placeholder"])
        self.assertIn("viewport", " ".join(context["generated_asset"]["quality_gate_preview"]).lower())

    def test_gameplay_template_context_surfaces_generated_asset_replacement_operations(self):
        work_order = {
            "target_phase": "editor_implementation",
            "feature_template_work": {
                "schema": "unreal_mcp_gameplay_feature_template.v1",
                "template_name": "ai_patrol_objective_asset_swap_slice",
                "display_name": "AI Patrol Objective Asset-Swap Slice",
                "asset_list": ["BP_EnemyScout", "BP_ObjectiveDirector", "PH_EnemyScout"],
                "ownership_split": {"Blueprint": ["Enemy visual slot"], "AI": ["Behavior Tree"], "HUD": ["Objective widget"]},
                "graph_component_operations": [
                    "Create Behavior Tree selector branches for patrol, chase, attack, and objective-area arrival.",
                    "Wire placeholder-to-generated replacement only after lifecycle import, quality proof, and ledger evidence are present.",
                ],
                "editor_operation_checklist": [
                    {
                        "id": "ai_patrol_objective_asset_swap_slice_01",
                        "operation_type": "ai_blackboard_behavior_tree",
                        "summary": "Create Behavior Tree selector branches for patrol, chase, attack, and objective-area arrival.",
                        "tool_candidates": ["build_behavior_tree", "bt_get_info"],
                        "requires_bridge": True,
                        "requires_compile_after": True,
                        "requires_readback_after": True,
                        "operation_proof_contract": {
                            "schema": "unreal_mcp_gameplay_feature_operation_proof.v1",
                            "operation_id": "ai_patrol_objective_asset_swap_slice_01",
                            "required_after": ["blueprint_compile_report", "graph_or_component_readback", "ide_companion_ledger_event"],
                        },
                    },
                    {
                        "id": "ai_patrol_objective_asset_swap_slice_02",
                        "operation_type": "generated_asset_replacement",
                        "summary": "Wire placeholder-to-generated replacement only after lifecycle import, quality proof, and ledger evidence are present.",
                        "tool_candidates": [
                            "skill_compile_ide_companion_asset_lifecycle_manifest",
                            "skill_compile_ide_companion_placeholder_manifest",
                            "chat_get_cockpit_overview",
                        ],
                        "requires_bridge": True,
                        "requires_compile_after": True,
                        "requires_readback_after": True,
                        "operation_proof_contract": {
                            "schema": "unreal_mcp_gameplay_feature_operation_proof.v1",
                            "operation_id": "ai_patrol_objective_asset_swap_slice_02",
                            "required_after": ["blueprint_compile_report", "graph_or_component_readback", "ide_companion_ledger_event"],
                        },
                    },
                ],
                "compile_readback_checks": ["compile_blueprint_and_report succeeds for every created Blueprint"],
                "pie_validation": ["Placeholder visual remains active until generated asset quality proof passes."],
                "runtime_proof_contract": {
                    "schema": "unreal_mcp_gameplay_feature_runtime_proof.v1",
                    "template_name": "ai_patrol_objective_asset_swap_slice",
                    "mode": "ai_behavior_tree_navigation_smoke",
                    "required_before": ["unreal_bridge_reachable", "editor_operations_read_back"],
                    "required_evidence": [
                        "bt_get_info_blackboard_assigned",
                        "blackboard_key_readback",
                        "nav_describe_agent_settings_or_setup_navmesh_result",
                        "enemy_capsule_and_movement_component_readback",
                        "pie_ai_state_or_log",
                        "viewport_or_hud_screenshot",
                        "ide_companion_ledger_event",
                    ],
                    "tool_candidates": ["bt_get_info", "nav_describe_agent_settings", "pie_capture_log"],
                    "stop_if_missing": ["Behavior Tree has no Blackboard assigned"],
                },
                "repair_instructions": ["If runtime proof is missing, keep the feature marked unproven."],
                "evidence_requirements": ["created asset paths or placeholder/generated asset lifecycle manifest"],
                "stop_conditions": ["Unreal bridge is offline for editor mutation"],
                "completion_contract": {
                    "schema": "unreal_mcp_gameplay_feature_completion_contract.v1",
                    "required_evidence": ["asset_or_placeholder_manifest", "ide_companion_ledger_event"],
                    "proof_gates": [{"name": "editor_operations_read_back", "required_count": 2}],
                    "stop_before_complete": ["any required asset, placeholder, or generated replacement is missing"],
                },
            },
        }
        summary = cockpit.work_order_template_summary(work_order)
        context = cockpit.gameplay_template_context(
            ledger={"session_name": "ide-companion", "work_order_phase": "editor_implementation"},
            readiness_policy={"editor_mutation": {"allowed": False, "missing_gates": ["unreal_bridge_reachable"]}},
            work_order_template=summary,
        )

        self.assertEqual(summary["template_name"], "ai_patrol_objective_asset_swap_slice")
        self.assertEqual(summary["generated_asset_replacement_operation_count"], 1)
        self.assertEqual(summary["generated_asset_replacement_proof_contract_count"], 1)
        self.assertIn("skill_compile_ide_companion_asset_lifecycle_manifest", summary["generated_asset_replacement_tool_preview"])
        self.assertIn("generated_asset_replacement", summary["editor_operation_type_preview"])
        self.assertEqual(summary["runtime_proof_contract_schema"], "unreal_mcp_gameplay_feature_runtime_proof.v1")
        self.assertEqual(summary["runtime_proof_mode"], "ai_behavior_tree_navigation_smoke")
        self.assertEqual(summary["runtime_proof_required_count"], 7)
        self.assertEqual(summary["runtime_proof_required_before_count"], 2)
        self.assertIn("unreal_bridge_reachable", summary["runtime_proof_required_before_preview"])
        self.assertIn("editor_operations_read_back", summary["runtime_proof_required_before_preview"])
        self.assertIn("bt_get_info_blackboard_assigned", summary["runtime_proof_required_preview"])
        self.assertIn("nav_describe_agent_settings", summary["runtime_proof_tool_preview"])
        self.assertEqual(context["generated_asset_replacement_operation_count"], 1)
        self.assertEqual(context["generated_asset_replacement_proof_contract_count"], 1)
        self.assertEqual(context["runtime_proof_mode"], "ai_behavior_tree_navigation_smoke")
        self.assertEqual(context["runtime_proof_required_count"], 7)
        self.assertIn("enemy_capsule_and_movement_component_readback", context["runtime_proof_required_preview"])
        self.assertIn("placeholder-to-generated replacement", " ".join(context["generated_asset_replacement_operation_preview"]))
        self.assertIn("skill_compile_ide_companion_placeholder_manifest", context["generated_asset_replacement_tool_preview"])
        self.assertIn("unreal_bridge_reachable", context["missing_gate_preview"])
        queue_context = cockpit.build_queue_target_context(
            target_phase="editor_implementation",
            work_order_template=summary,
            ledger_path=".mcp_artifacts/ide_companion_sessions/ide-companion.json",
        )
        self.assertEqual(queue_context["generated_asset_replacement_operation_count"], 1)
        self.assertEqual(queue_context["generated_asset_replacement_proof_contract_count"], 1)
        self.assertIn("placeholder-to-generated replacement", " ".join(queue_context["generated_asset_replacement_operation_preview"]))
        self.assertIn("lifecycle and quality proof", " ".join(queue_context["generated_asset_replacement_gate_policy"]))
        queue_review = cockpit.queue_review_context(
            queues=[
                {
                    "queue_path": ".mcp_artifacts/ide_companion_sessions/ide-companion_queue.json",
                    "queue_name": "editor_queue",
                    "target_phase": "editor_implementation",
                    "action_count": 1,
                    "next_action_id": "swap_placeholder_mesh",
                    "next_action_tool": "set_static_mesh_component",
                    "bridge_required": True,
                    "can_execute_now": False,
                    "bridge_blocked": True,
                    "blocking_gates": ["unreal_bridge_reachable"],
                    "preview_actions": [
                        {
                            "id": "swap_placeholder_mesh",
                            "tool": "set_static_mesh_component",
                            "label": "Swap placeholder mesh",
                            "argument_keys": ["blueprint_path", "component_name", "static_mesh_path"],
                        }
                    ],
                }
            ],
            next_queue={},
            work_order_template=summary,
        )
        self.assertEqual(queue_review["generated_asset_replacement_operation_count"], 1)
        self.assertEqual(queue_review["generated_asset_replacement_proof_contract_count"], 1)
        self.assertIn("placeholder-to-generated replacement", " ".join(queue_review["generated_asset_replacement_operation_preview"]))
        self.assertIn("quality proof", " ".join(queue_review["generated_asset_replacement_gate_policy"]))
        next_safe_step = cockpit.build_next_safe_step_gate(
            queues=[
                {
                    "queue_path": ".mcp_artifacts/ide_companion_sessions/ide-companion_queue.json",
                    "queue_name": "editor_queue",
                    "target_phase": "editor_implementation",
                    "next_action_id": "swap_placeholder_mesh",
                    "next_action_tool": "set_static_mesh_component",
                    "bridge_required": True,
                    "can_execute_now": True,
                    "preview_actions": [
                        {
                            "id": "swap_placeholder_mesh",
                            "tool": "set_static_mesh_component",
                            "label": "Swap placeholder mesh",
                            "argument_keys": ["blueprint_path", "component_name", "static_mesh_path"],
                        }
                    ],
                }
            ],
            blocking_gates=[],
            evidence_recording={"items": []},
            work_order_template=summary,
        )
        self.assertEqual(next_safe_step["generated_asset_replacement_operation_count"], 1)
        self.assertIn("Do not execute replacement operations", " ".join(next_safe_step["execution_policy"]))
        execution_review = cockpit.build_execution_review(
            next_safe_step=next_safe_step,
            evidence_recording={"items": []},
        )
        execution_context = cockpit.execution_review_context(execution_review)
        self.assertEqual(execution_context["generated_asset_replacement_operation_count"], 1)
        self.assertEqual(execution_context["generated_asset_replacement_proof_contract_count"], 1)
        self.assertIn("placeholder assets active", " ".join(execution_context["generated_asset_replacement_gate_policy"]))

        runtime_verification = cockpit.build_runtime_verification_checklist(
            work_order_template=summary,
            ledger={"work_order_phase": "runtime_verification", "preview_events": []},
            queues=[{"bridge_blocked": True}],
            blocking_gates=["unreal_bridge_reachable"],
        )
        runtime_review = cockpit.build_runtime_review(runtime_verification)
        self.assertEqual(runtime_verification["runtime_proof_mode"], "ai_behavior_tree_navigation_smoke")
        self.assertEqual(runtime_verification["runtime_proof_required_count"], 7)
        self.assertEqual(runtime_verification["runtime_proof_required_before_count"], 2)
        self.assertIn("editor_operations_read_back", runtime_verification["runtime_proof_required_before_preview"])
        self.assertIn("bt_get_info_blackboard_assigned", runtime_verification["runtime_proof_required_preview"])
        self.assertIn("runtime_proof_contract", {item["kind"] for item in runtime_verification["items"]})
        self.assertEqual(runtime_review["runtime_proof_mode"], "ai_behavior_tree_navigation_smoke")
        self.assertEqual(runtime_review["runtime_proof_required_before_count"], 2)
        self.assertIn("unreal_bridge_reachable", runtime_review["runtime_proof_required_before_preview"])
        self.assertIn("Behavior Tree has no Blackboard assigned", runtime_review["runtime_proof_stop_preview"])
        evidence_recording = cockpit.build_evidence_recording_checklist(
            session_name="ide-companion",
            ledger={"work_order_phase": "runtime_verification", "preview_events": []},
            queues=[],
            asset_lifecycles=[],
            generated_asset_quality_gate={},
            work_order_template=summary,
            runtime_verification=runtime_verification,
            repair_loop={},
            blocker_resolutions={},
            readiness_policy={},
        )
        runtime_item = next(item for item in evidence_recording["items"] if item["id"] == "record_runtime_verification")
        self.assertEqual(runtime_item["metadata"]["runtime_proof_mode"], "ai_behavior_tree_navigation_smoke")
        self.assertEqual(runtime_item["metadata"]["runtime_proof_required_count"], 7)
        self.assertEqual(runtime_item["metadata"]["runtime_proof_required_before_count"], 2)
        self.assertIn("editor_operations_read_back", runtime_item["metadata"]["runtime_proof_required_before_preview"])
        self.assertIn("blackboard_key_readback", runtime_item["metadata"]["runtime_proof_required_preview"])

    def test_gameplay_template_context_surfaces_generated_animation_prompts(self):
        work_order = {
            "target_phase": "editor_implementation",
            "feature_template_work": {
                "schema": "unreal_mcp_gameplay_feature_template.v1",
                "template_name": "replicated_combat_sample",
                "display_name": "Replicated Combat Sample",
                "asset_list": [
                    {"kind": "blueprint", "name": "BP_CombatProbe", "role": "combat actor", "path": "/Game/Combat"},
                    {"kind": "generated_animation_or_placeholder", "name": "A_Combat_Attack", "role": "combat_attack_motion", "path": "/Game/Generated/Animations"},
                ],
                "generated_animation_prompts": [
                    {
                        "role": "combat_attack_motion",
                        "name": "A_Combat_Attack",
                        "provider": "uthana",
                        "task_type": "text_to_motion",
                        "target_skeleton": "UE5 Manny",
                        "estimated_seconds": 4,
                    },
                ],
                "estimated_uthana_motion_seconds": 4,
                "animation_system_hook": {
                    "needed": True,
                    "provider": "uthana",
                    "tools": ["gen_uthana_text_to_motion", "gen_uthana_import_animation_to_project", "gen_compile_generated_animation_evidence"],
                    "proof_required": ["uthana_api_key_configured", "animgraph_or_state_machine_reference", "pie_motion_playback_or_viewport_proof"],
                },
                "ownership_split": {"Blueprint": ["Damageable Component"]},
                "graph_component_operations": ["Route attack input into damage and animation feedback."],
                "editor_operation_checklist": [],
                "compile_readback_checks": ["compile_blueprint_and_report succeeds"],
                "pie_validation": ["Attack feedback triggers in PIE."],
                "repair_instructions": ["Stop on animation proof failure."],
                "evidence_requirements": ["generated animation lifecycle manifest"],
                "stop_conditions": ["Uthana proof is missing"],
                "completion_contract": {
                    "schema": "unreal_mcp_gameplay_feature_completion_contract.v1",
                    "required_evidence": ["ide_companion_ledger_event"],
                    "proof_gates": [{"name": "pie_validation_passed", "required_count": 1}],
                    "stop_before_complete": ["animation proof missing"],
                },
            },
        }
        summary = cockpit.work_order_template_summary(work_order)
        context = cockpit.gameplay_template_context(
            ledger={"session_name": "ide-companion", "work_order_phase": "editor_implementation"},
            readiness_policy={"editor_mutation": {"allowed": False, "missing_gates": ["unreal_bridge_reachable"]}},
            work_order_template=summary,
        )

        self.assertEqual(summary["generated_animation_prompt_count"], 1)
        self.assertIn("A_Combat_Attack", " ".join(summary["generated_animation_prompt_preview"]))
        self.assertEqual(summary["generated_animation_provider_preview"], ["uthana"])
        self.assertEqual(summary["generated_animation_target_skeleton_preview"], ["UE5 Manny"])
        self.assertIn("gen_uthana_text_to_motion", summary["generated_animation_tool_preview"])
        self.assertIn("animgraph_or_state_machine_reference", summary["generated_animation_proof_required_preview"])
        self.assertEqual(summary["estimated_uthana_motion_seconds"], 4)
        self.assertEqual(context["generated_animation_prompt_count"], 1)
        self.assertIn("lifecycle manifest", " ".join(context["generated_animation_prompt_gate_policy"]))
        self.assertIn("Do not call Uthana", " ".join(context["generated_animation_prompt_gate_policy"]))

        queue_context = cockpit.build_queue_target_context(
            target_phase="editor_implementation",
            work_order_template=summary,
            ledger_path=".mcp_artifacts/ide_companion_sessions/ide-companion.json",
        )
        self.assertEqual(queue_context["generated_animation_prompt_count"], 1)
        self.assertIn("A_Combat_Attack", " ".join(queue_context["generated_animation_prompt_preview"]))

        next_safe_step = cockpit.build_next_safe_step_gate(
            queues=[
                {
                    "queue_path": ".mcp_artifacts/ide_companion_sessions/ide-companion_queue.json",
                    "queue_name": "editor_queue",
                    "target_phase": "editor_implementation",
                    "next_action_id": "wire_combat_animation",
                    "next_action_tool": "add_sequence_player_node",
                    "bridge_required": True,
                    "can_execute_now": True,
                    "preview_actions": [{"id": "wire_combat_animation", "tool": "add_sequence_player_node", "label": "Wire combat animation"}],
                }
            ],
            blocking_gates=[],
            evidence_recording={"items": []},
            work_order_template=summary,
        )
        self.assertEqual(next_safe_step["generated_animation_prompt_count"], 1)
        self.assertIn("fallback animation active", " ".join(next_safe_step["execution_policy"]))
        execution_context = cockpit.execution_review_context(cockpit.build_execution_review(
            next_safe_step=next_safe_step,
            evidence_recording={"items": []},
        ))
        self.assertEqual(execution_context["generated_animation_prompt_count"], 1)
        self.assertIn("pie_motion_playback_or_viewport_proof", execution_context["generated_animation_proof_required_preview"])

    def test_evidence_ledger_context_summarizes_bounded_timeline(self):
        context = cockpit.evidence_ledger_context({
            "ledger_path": ".mcp_artifacts/ide_companion_sessions/ide-companion.json",
            "session_name": "ide-companion",
            "event_count": 3,
            "preview_events": [
                {
                    "phase_name": "orient_to_project",
                    "evidence_type": "context",
                    "summary": "Project context loaded.",
                    "artifact_count": 1,
                    "artifact_preview": ["kb://INDEX.md"],
                },
                {
                    "phase_name": "editor_implementation",
                    "evidence_type": "readiness",
                    "summary": "Bridge blocked, continue offline.",
                    "artifact_count": 2,
                    "artifact_preview": ["preflight report", "bridge_ping: offline"],
                },
            ],
        })
        self.assertEqual(context["event_count"], 3)
        self.assertEqual(context["preview_event_count"], 2)
        self.assertEqual(context["artifact_count"], 3)
        self.assertEqual(context["latest_phase"], "editor_implementation")
        self.assertEqual(context["latest_evidence_type"], "readiness")
        self.assertIn("bridge", context["latest_summary"].lower())
        self.assertEqual(context["latest_artifact_preview"], ["preflight report", "bridge_ping: offline"])
        self.assertEqual(context["timeline_preview"][0]["phase_name"], "orient_to_project")

    def test_cockpit_ledger_detail_route_reads_bounded_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            chat_dir = Path(tmp) / "MCPChat"
            ledger_dir = Path(tmp) / ".mcp_artifacts" / "ide_companion_sessions"
            ledger_dir.mkdir(parents=True)
            (ledger_dir / "ide-companion.json").write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_ledger.v1",
                "session_name": "ide-companion",
                "events": [
                    {
                        "phase_name": "orient_to_project",
                        "evidence_type": "context",
                        "summary": "Project context loaded.",
                        "artifacts": ["kb://INDEX.md"],
                        "timestamp_unix": 1770000000,
                    },
                    {
                        "phase_name": "editor_implementation",
                        "evidence_type": "readback",
                        "summary": "Placeholder actor queued for review.",
                        "artifacts": [
                            "/Game/Generated/BP_Placeholder",
                            "https://example.invalid/proof.png",
                            "compile report",
                            "C:/Project/Saved/Screenshots/proof.png",
                        ],
                        "timestamp_unix": 1770000200,
                    },
                ],
                "evidence": {"editor_implementation": []},
                "latest_status": {
                    "completed_phase_count": 2,
                    "blocking_gates": [],
                    "next_phase": "runtime_verification",
                    "next_action": {"tool": "pie_launch_session"},
                },
                "latest_work_order": {"target_phase": "runtime_verification"},
            }), encoding="utf-8")

            app = Starlette(routes=[
                Route("/chat/cockpit/ledger", routes.chat_cockpit_ledger_detail, methods=["GET"]),
            ])
            with (
                patch.object(storage, "DEFAULT_CHAT_SESSION_DIR", chat_dir),
                patch.object(cockpit, "DEFAULT_IDE_COMPANION_SESSION_DIR", ledger_dir),
            ):
                storage.append_message({
                    "sender": "human",
                    "message": "Open ledger detail.",
                    "timestamp": "2026-04-30T14:28:00Z",
                }, session="ide-companion")
                client = TestClient(app)
                response = client.get("/chat/cockpit/ledger?session=ide-companion&event_index=2&artifact_limit=3")

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["schema"], "unreal_mcp_chat_ledger_detail.v1")
            self.assertTrue(payload["ledger_found"])
            self.assertEqual(payload["event_count"], 2)
            self.assertEqual(payload["returned_event_count"], 1)
            event = payload["events"][0]
            self.assertEqual(event["index"], 2)
            self.assertEqual(event["artifact_count"], 4)
            self.assertEqual(event["artifact_overflow_count"], 1)
            self.assertEqual([item["kind"] for item in event["artifact_items"]], ["unreal_asset", "uri", "note"])
            self.assertEqual(payload["phase_index"][1]["phase_name"], "editor_implementation")
            self.assertEqual(payload["latest_work_order"]["target_phase"], "runtime_verification")
            self.assertEqual(payload["warnings"], [])

    def test_tools_list_route_uses_tool_inventory_categories(self):
        mcp = _MockRouteMCP()
        routes.register_chat_routes(mcp)
        app = Starlette(routes=mcp._routes)
        client = TestClient(app)

        response = client.get("/tools/list?domain=knowledge_base")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("knowledge_base", payload["tools_by_category"])
        self.assertEqual(payload["tools"][0]["name"], "get_server_info")
        self.assertEqual(payload["tools"][0]["parameters"], ["blueprint_name"])


class TestChatTools(unittest.TestCase):
    def setUp(self):
        from tools import chat_tools

        self.chat_tools = chat_tools
        self.mcp = _MockMCP()
        self.chat_tools.register_chat_tools(self.mcp)
        self.chat_tools._LAST_HUMAN_POLL_SINCE = {}

    def test_tools_registered(self):
        self.assertEqual({
            "chat_poll_messages",
            "chat_send_response",
            "chat_get_context",
            "chat_list_sessions",
            "chat_get_session_resume_context",
            "chat_get_cockpit_overview",
            "chat_get_cockpit_ledger_detail",
        }, set(self.mcp.list_tool_names()))

    def test_send_and_poll_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "chat_history.json"
            with patch.object(storage, "DEFAULT_CHAT_HISTORY_PATH", path):
                storage.append_message({
                    "sender": "human",
                    "message": "What phase are we in?",
                    "timestamp": "2026-04-30T14:23:00Z",
                })

                poll = _parse(self.mcp.get_tool("chat_poll_messages")(
                    since="2026-04-30T14:22:00Z",
                    limit=10,
                ))
                self.assertTrue(poll["success"])
                self.assertEqual(len(poll["outputs"]["messages"]), 1)

                send = _parse(self.mcp.get_tool("chat_send_response")(
                    message="We are still in audit.",
                    context={"phase": "0"},
                ))
                self.assertTrue(send["success"])
                self.assertEqual(send["outputs"]["message"]["sender"], "agent")

                context = _parse(self.mcp.get_tool("chat_get_context")(message_limit=10))
                self.assertTrue(context["success"])
                self.assertIn("knowledge_base", context["outputs"])

    def test_agent_tools_keep_named_sessions_isolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "sessions"
            with patch.object(storage, "DEFAULT_CHAT_SESSION_DIR", session_dir):
                storage.append_message(
                    {"sender": "human", "message": "Alpha question", "timestamp": "2026-04-30T14:23:00Z"},
                    session="Alpha",
                )
                storage.append_message(
                    {"sender": "human", "message": "Beta question", "timestamp": "2026-04-30T14:23:01Z"},
                    session="Beta",
                )

                alpha = _parse(self.mcp.get_tool("chat_poll_messages")(
                    since="2026-04-30T14:22:00Z",
                    limit=10,
                    session="Alpha",
                ))
                beta = _parse(self.mcp.get_tool("chat_poll_messages")(
                    since="2026-04-30T14:22:00Z",
                    limit=10,
                    session="Beta",
                ))
                self.assertEqual([item["message"] for item in alpha["outputs"]["messages"]], ["Alpha question"])
                self.assertEqual([item["message"] for item in beta["outputs"]["messages"]], ["Beta question"])

                sent = _parse(self.mcp.get_tool("chat_send_response")(
                    message="Alpha answer",
                    session="Alpha",
                ))
                self.assertTrue(sent["success"])
                alpha_context = _parse(self.mcp.get_tool("chat_get_context")(
                    message_limit=10,
                    session="Alpha",
                ))
                beta_context = _parse(self.mcp.get_tool("chat_get_context")(
                    message_limit=10,
                    session="Beta",
                ))
                self.assertEqual(alpha_context["outputs"]["session"], "Alpha")
                self.assertEqual(len(alpha_context["outputs"]["recent_messages"]), 2)
                self.assertEqual(len(beta_context["outputs"]["recent_messages"]), 1)

    def test_session_picker_tools_include_matching_companion_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "Saved" / "MCPChat"
            ledger_dir = Path(tmp) / ".mcp_artifacts" / "ide_companion_sessions"
            ledger_dir.mkdir(parents=True)
            ledger_path = ledger_dir / "ide-companion.json"
            ledger_path.write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_ledger.v1",
                "session_name": "ide-companion",
                "events": [
                    {
                        "phase_name": "orient_to_project",
                        "evidence_type": "context",
                        "summary": "Context loaded for resume.",
                        "artifacts": ["kb://INDEX.md"],
                        "timestamp_unix": 1770000000,
                    },
                    {
                        "phase_name": "session_preflight",
                        "evidence_type": "readiness",
                        "summary": "Bridge gate recorded.",
                        "artifacts": ["preflight report", "bridge_ping: offline"],
                        "timestamp_unix": 1770000100,
                    },
                ],
                "evidence": {"orient_to_project": []},
                "latest_status": {
                    "completed_phase_count": 1,
                    "blocking_gates": ["unreal_bridge_reachable"],
                    "next_phase": "session_preflight",
                    "next_action": {"tool": "gen_compile_ide_companion_readiness"},
                },
                "latest_work_order": {"target_phase": "session_preflight"},
                "latest_readiness": {},
            }), encoding="utf-8")
            (ledger_dir / "ide-companion_editor_queue.json").write_text(json.dumps({
                "schema": "unreal_mcp_ide_companion_editor_queue.v1",
                "session_name": "ide-companion",
                "queue_name": "editor_queue",
                "queue_path": ".mcp_artifacts/ide_companion_sessions/ide-companion_editor_queue.json",
                "target_phase": "editor_implementation",
                "source": "placeholder_manifest",
                "actions": [
                    {"id": "create_placeholder_folder", "tool": "create_folder", "arguments": {"path": "/Game/Generated"}},
                    {"id": "create_placeholder_material", "tool": "create_material", "arguments": {"asset_path": "/Game/Generated/M_Placeholder"}},
                ],
                "blocking_gates": ["unreal_bridge_reachable"],
                "bridge_required": True,
                "bridge_blocked": True,
                "can_execute_now": False,
                "evidence_to_collect": ["compile report"],
            }), encoding="utf-8")

            with (
                patch.object(storage, "DEFAULT_CHAT_SESSION_DIR", session_dir),
                patch.object(cockpit, "DEFAULT_IDE_COMPANION_SESSION_DIR", ledger_dir),
            ):
                storage.append_message({
                    "sender": "human",
                    "message": "Resume the IDE companion.",
                    "timestamp": "2026-04-30T14:23:00Z",
                }, session="ide-companion")

                sessions = _parse(self.mcp.get_tool("chat_list_sessions")())
                self.assertTrue(sessions["success"])
                self.assertEqual(sessions["stage"], "chat_sessions_listed")
                self.assertIn("ide-companion", {item["name"] for item in sessions["outputs"]["sessions"]})
                self.assertEqual(sessions["outputs"]["ide_companion_ledgers"][0]["session_name"], "ide-companion")
                self.assertEqual(sessions["outputs"]["ide_companion_ledgers"][0]["next_tool"], "gen_compile_ide_companion_readiness")

                context = _parse(self.mcp.get_tool("chat_get_session_resume_context")(
                    session="ide-companion",
                    message_limit=5,
                ))
                self.assertTrue(context["success"])
                self.assertEqual(context["stage"], "chat_session_resume_context")
                self.assertEqual(context["outputs"]["session"], "ide-companion")
                self.assertEqual(len(context["outputs"]["recent_messages"]), 1)
                ledger = context["outputs"]["matching_ide_companion_ledger"]
                self.assertEqual(ledger["latest_phase"], "session_preflight")
                self.assertEqual(ledger["blocking_gates"], ["unreal_bridge_reachable"])
                self.assertTrue(context["outputs"]["suggested_actions"][0]["enabled"])

                overview = _parse(self.mcp.get_tool("chat_get_cockpit_overview")(
                    session="ide-companion",
                    message_limit=5,
                    limit=5,
                ))
                self.assertTrue(overview["success"])
                self.assertEqual(overview["stage"], "chat_cockpit_overview")
                self.assertEqual(overview["outputs"]["schema"], "unreal_mcp_chat_cockpit_overview.v1")
                self.assertEqual(overview["outputs"]["editor_queues"][0]["next_action_tool"], "create_folder")
                self.assertEqual(overview["outputs"]["editor_queues"][0]["preview_actions"][1]["tool"], "create_material")
                self.assertEqual(overview["outputs"]["evidence_timeline"][0]["phase_name"], "orient_to_project")
                self.assertEqual(overview["outputs"]["evidence_timeline"][1]["evidence_type"], "readiness")
                self.assertEqual(overview["outputs"]["evidence_timeline"][1]["artifact_preview"][0], "preflight report")
                self.assertIn("editor_queue", {card["id"] for card in overview["outputs"]["cards"]})
                self.assertFalse(overview["outputs"]["suggested_actions"][-1]["enabled"])
                self.assertIn("Queued editor actions are present", overview["warnings"][-1])

                detail = _parse(self.mcp.get_tool("chat_get_cockpit_ledger_detail")(
                    session="ide-companion",
                    event_index=2,
                    artifact_limit=1,
                ))
                self.assertTrue(detail["success"])
                self.assertEqual(detail["stage"], "chat_cockpit_ledger_detail")
            self.assertEqual(detail["outputs"]["schema"], "unreal_mcp_chat_ledger_detail.v1")
            self.assertEqual(detail["outputs"]["events"][0]["phase_name"], "session_preflight")
            self.assertEqual(detail["outputs"]["events"][0]["artifacts"], ["preflight report"])
            self.assertEqual(detail["outputs"]["events"][0]["artifact_overflow_count"], 1)

    def test_readiness_policy_context_includes_wip_promotion_blockers(self):
        policy = cockpit.build_readiness_policy_summary(
            blocking_gates=[
                "dirty_state_grouped_for_promotion",
                "plugin_build_successful",
                "test_lane_separation",
                "chat_server_reachable",
            ],
            queues=[],
            work_order_template={"compile_check_count": 1},
        )

        self.assertFalse(policy["wip_promotion"]["allowed"])
        self.assertEqual(
            policy["wip_promotion"]["missing_gates"],
            [
                "no_mutation_test_lane_safe",
                "plugin_build_successful",
                "dirty_state_grouped_for_promotion",
                "chat_cockpit_reachable",
            ],
        )
        self.assertNotIn("test_lane_separation", policy["wip_promotion"]["missing_gates"])
        self.assertNotIn("chat_server_reachable", policy["wip_promotion"]["missing_gates"])
        self.assertIn("no_mutation_receipt_tracked_file_count", policy["wip_promotion"]["evidence_required"])
        self.assertIn("no_mutation_receipt_snapshot_digest_match", policy["wip_promotion"]["evidence_required"])
        self.assertIn("no_mutation_receipt_scope_git_tracked_worktree", policy["wip_promotion"]["evidence_required"])

        context = cockpit.readiness_policy_context(policy)
        self.assertIn("wip_promotion", context["blocked_policies"])
        self.assertIn("dirty_state_grouped_for_promotion", context["missing_gate_preview"])
        self.assertIn("chat_cockpit_reachable", context["missing_gate_preview"])
        self.assertGreater(context["evidence_required_count"], 0)
        self.assertIn("no_mutation_receipt_snapshot_digest_match", context["wip_promotion_evidence_required_preview"])
        self.assertIn("no_mutation_receipt_scope_git_tracked_worktree", context["wip_promotion_evidence_required_preview"])

    def test_no_mutation_blocker_requires_snapshot_receipt_proof(self):
        summary = cockpit.build_blocker_resolution_summary(["no_mutation_test_lane_safe"])
        self.assertEqual(summary["blocking_gate_count"], 1)
        resolution = summary["resolutions"][0]

        self.assertEqual(resolution["blocker"], "no_mutation_test_lane_safe")
        self.assertEqual(resolution["recommended_strategy"], "prove_no_mutation_lane_safe")
        self.assertIn("TRACKED_FILE_MUTATIONS=0", resolution["evidence_required"])
        self.assertIn("tracked_file_count>0", resolution["evidence_required"])
        self.assertIn("snapshot_digest_match=true", resolution["evidence_required"])
        self.assertIn("snapshot_scope=git_tracked_worktree", resolution["evidence_required"])


if __name__ == "__main__":
    unittest.main()
