"""Offline smoke coverage for gameplay mechanic planning skill."""

from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path


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
    testcase.assertEqual(payload["meta"]["tool"], "skill_plan_gameplay_mechanic")


class TestD11GameplayMechanicPlanner(unittest.TestCase):
    def test_plan_ability_cooldown_mechanic_offline(self):
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        result = skill_plan_gameplay_mechanic(
            "player dash ability with cooldown and HUD feedback",
            include_generated_assets=True,
        )

        _assert_structured(self, result, "plan_ready")
        self.assertTrue(result["success"])
        self.assertFalse(result["outputs"]["network_required"])
        self.assertFalse(result["outputs"]["unreal_editor_required"])
        self.assertFalse(result["outputs"]["spend_required"])
        plan = result["outputs"]["plan"]
        self.assertEqual(plan["schema"], "unreal_mcp_gameplay_mechanic_plan.v1")
        self.assertEqual(plan["mechanic_kind"], "ability_cooldown")
        self.assertEqual(plan["feature_template"]["schema"], "unreal_mcp_gameplay_feature_template.v1")
        self.assertEqual(plan["feature_template"]["template_name"], "input_cooldown_ability")
        self.assertIn("Input Cooldown Ability", plan["feature_template"]["display_name"])
        completion = plan["feature_template"]["completion_contract"]
        self.assertEqual(completion["schema"], "unreal_mcp_gameplay_feature_completion_contract.v1")
        self.assertIn("pie_validation_passed", {gate["name"] for gate in completion["proof_gates"]})
        self.assertIn("viewport_or_hud_screenshot", completion["required_evidence"])
        self.assertIn("IDE companion ledger evidence is missing", completion["stop_before_complete"])
        self.assertIn("Enhanced Input Action", json.dumps(plan["feature_template"]["ownership_split"]))
        self.assertIn("Repeated input during cooldown is ignored", json.dumps(plan["feature_template"]["pie_validation"]))
        self.assertIn("Blueprint compile report", plan["feature_template"]["evidence_requirements"])
        operations = plan["feature_template"]["editor_operation_checklist"]
        self.assertGreaterEqual(len(operations), 4)
        self.assertTrue(all(row["requires_bridge"] for row in operations))
        self.assertTrue(all(row["requires_compile_after"] for row in operations))
        self.assertTrue(all(row["requires_readback_after"] for row in operations))
        self.assertIn("input_and_cooldown", {row["operation_type"] for row in operations})
        self.assertIn("add_enhanced_input_action_event", json.dumps(operations))
        runtime_contract = plan["feature_template"]["runtime_proof_contract"]
        self.assertEqual(runtime_contract["mode"], "input_cooldown_ability_smoke")
        self.assertIn("enhanced_input_action_mapping_readback", runtime_contract["required_evidence"])
        self.assertIn("can_activate_false_while_cooldown_active", runtime_contract["required_evidence"])
        self.assertIn("hud_cooldown_state_or_widget_readback", runtime_contract["required_evidence"])
        self.assertIn("add_enhanced_input_action_event", runtime_contract["tool_candidates"])
        self.assertIn("blocked repeat input", " ".join(runtime_contract["stop_if_missing"]))
        self.assertTrue(plan["system_hooks"]["input"]["needed"])
        self.assertTrue(plan["system_hooks"]["hud"]["needed"])
        self.assertTrue(plan["system_hooks"]["replication"]["needed"])
        self.assertGreaterEqual(len(plan["generated_assets"]), 2)
        self.assertIn("gen_compile_ide_companion_readiness", json.dumps(plan["next_actions"]))

    def test_ai_brief_includes_blackboard_behavior_tree_hooks(self):
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        result = skill_plan_gameplay_mechanic(
            "enemy AI patrol that chases the player when seen",
            include_generated_assets=False,
        )

        _assert_structured(self, result, "plan_ready")
        plan = result["outputs"]["plan"]
        self.assertEqual(plan["mechanic_kind"], "ai_encounter")
        self.assertEqual(plan["feature_template"]["template_name"], "enemy_patrol_chase_attack")
        self.assertEqual(plan["generated_assets"], [])
        self.assertTrue(plan["system_hooks"]["ai"]["needed"])
        self.assertIn("TargetActor", plan["system_hooks"]["ai"]["blackboard_keys"])
        self.assertIn("Blackboard keys TargetActor", json.dumps(plan["feature_template"]["graph_component_operations"]))
        self.assertIn("ai_blackboard_behavior_tree", {row["operation_type"] for row in plan["feature_template"]["editor_operation_checklist"]})
        self.assertIn("set_behavior_tree_blackboard", json.dumps(plan["feature_template"]["editor_operation_checklist"]))
        runtime_contract = plan["feature_template"]["runtime_proof_contract"]
        self.assertEqual(runtime_contract["schema"], "unreal_mcp_gameplay_feature_runtime_proof.v1")
        self.assertEqual(runtime_contract["mode"], "ai_behavior_tree_navigation_smoke")
        self.assertIn("bt_get_info_blackboard_assigned", runtime_contract["required_evidence"])
        self.assertIn("nav_describe_agent_settings_or_setup_navmesh_result", runtime_contract["required_evidence"])
        self.assertIn("enemy_capsule_and_movement_component_readback", runtime_contract["required_evidence"])
        self.assertIn("Behavior Tree has no Blackboard assigned", runtime_contract["stop_if_missing"])
        self.assertIn("Enemy patrols when no target is known", json.dumps(plan["feature_template"]["pie_validation"]))
        self.assertIn("repair work order", json.dumps(plan["feature_template"]["repair_instructions"]))
        self.assertIn("build_behavior_tree", json.dumps(plan["tool_sequence"]))

    def test_common_feature_template_names_are_advertised(self):
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        result = skill_plan_gameplay_mechanic("interactable pickup objective that saves progress")
        plan = result["outputs"]["plan"]

        self.assertIn("interactable_objective", plan["supported_feature_templates"])
        self.assertIn("pickup_resource_loop", plan["supported_feature_templates"])
        self.assertIn("enemy_patrol_chase_attack", plan["supported_feature_templates"])
        self.assertIn("objective_hud_update", plan["supported_feature_templates"])
        self.assertIn("save_load_state", plan["supported_feature_templates"])
        self.assertIn("input_cooldown_ability", plan["supported_feature_templates"])
        self.assertIn("replicated_combat_sample", plan["supported_feature_templates"])
        self.assertIn("ai_patrol_objective_asset_swap_slice", plan["supported_feature_templates"])
        self.assertIn("performance_optimization_pass", plan["supported_feature_templates"])
        self.assertIn("bug_fix_repair_pass", plan["supported_feature_templates"])
        self.assertEqual(plan["feature_template"]["schema"], "unreal_mcp_gameplay_feature_template.v1")
        self.assertEqual(plan["feature_template"]["template_name"], "save_load_state")
        self.assertGreaterEqual(len(plan["feature_template"]["asset_list"]), len(plan["blueprint_assets"]))

    def test_all_common_feature_templates_have_completion_contracts(self):
        from skills.playable_slice.skill import _feature_template_for_kind

        sample_assets = [
            {"name": "BP_Feature", "role": "mechanic", "path": "/Game/Generated/Mechanics/BP_Feature"},
        ]
        kinds = {
            "interaction_objective": "interactable_objective",
            "inventory_resource": "pickup_resource_loop",
            "save_load_state": "save_load_state",
            "ai_encounter": "enemy_patrol_chase_attack",
            "ai_objective_asset_swap_slice": "ai_patrol_objective_asset_swap_slice",
            "ability_cooldown": "input_cooldown_ability",
            "combat_loop": "replicated_combat_sample",
            "core_gameplay_loop": "objective_hud_update",
            "performance_optimization": "performance_optimization_pass",
            "bug_fix_repair": "bug_fix_repair_pass",
        }

        for kind, template_name in kinds.items():
            with self.subTest(kind=kind):
                template = _feature_template_for_kind(kind, "sample_feature", sample_assets, [])
                contract = template["completion_contract"]
                gate_by_name = {gate["name"]: gate for gate in contract["proof_gates"]}

                self.assertEqual(template["template_name"], template_name)
                self.assertEqual(contract["schema"], "unreal_mcp_gameplay_feature_completion_contract.v1")
                self.assertIn("editor_operations_read_back", gate_by_name)
                self.assertEqual(
                    gate_by_name["editor_operations_read_back"]["required_count"],
                    len(template["editor_operation_checklist"]),
                )
                for operation in template["editor_operation_checklist"]:
                    operation_contract = operation["operation_proof_contract"]
                    self.assertEqual(operation_contract["schema"], "unreal_mcp_gameplay_feature_operation_proof.v1")
                    self.assertEqual(operation_contract["operation_id"], operation["id"])
                    self.assertIn("unreal_bridge_reachable", operation_contract["required_before"])
                    self.assertIn("blueprint_compile_report", operation_contract["required_after"])
                    self.assertIn("graph_or_component_readback", operation_contract["required_after"])
                    self.assertIn("ide_companion_ledger_event", operation_contract["required_after"])
                    self.assertIn("compile report missing or failed", operation_contract["stop_if_missing"])
                self.assertIn("pie_validation_passed", gate_by_name)
                self.assertEqual(gate_by_name["pie_validation_passed"]["required_count"], len(template["pie_validation"]))
                self.assertIn("runtime_proof_contract_satisfied", gate_by_name)
                self.assertEqual(
                    gate_by_name["runtime_proof_contract_satisfied"]["required_count"],
                    len(template["runtime_proof_contract"]["required_evidence"]),
                )
                self.assertIn("ide_companion_ledger_event", contract["required_evidence"])
                self.assertIn("runtime_proof_contract_evidence", contract["required_evidence"])
                self.assertIn("any editor operation lacks compile/readback evidence", contract["stop_before_complete"])
                self.assertIn("runtime proof contract evidence is incomplete", contract["stop_before_complete"])

    def test_ai_objective_asset_swap_vertical_slice_template(self):
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        result = skill_plan_gameplay_mechanic(
            "AI patrol enemy with objective HUD and placeholder/generated asset swap vertical slice",
            include_generated_assets=True,
        )

        _assert_structured(self, result, "plan_ready")
        plan = result["outputs"]["plan"]
        template = plan["feature_template"]
        operations = template["editor_operation_checklist"]

        self.assertEqual(plan["mechanic_kind"], "ai_objective_asset_swap_slice")
        self.assertEqual(template["template_name"], "ai_patrol_objective_asset_swap_slice")
        self.assertIn("AI Patrol Objective Asset-Swap Slice", template["display_name"])
        self.assertTrue(plan["system_hooks"]["ai"]["needed"])
        self.assertTrue(plan["system_hooks"]["hud"]["needed"])
        self.assertTrue(plan["system_hooks"]["damage"]["needed"])
        self.assertTrue(plan["system_hooks"]["animation"]["needed"])
        self.assertGreaterEqual(len(plan["generated_assets"]), 2)
        self.assertGreaterEqual(len(plan["generated_animation_prompts"]), 2)
        self.assertEqual(plan["generated_animation_prompts"][0]["provider"], "uthana")
        self.assertEqual(plan["generated_animation_prompts"][0]["task_type"], "text_to_motion")
        self.assertGreater(plan["estimated_uthana_motion_seconds"], 0)
        self.assertIn("generated_animation_or_placeholder", {row["kind"] for row in template["asset_list"]})
        self.assertIn("placeholder mesh actor/component", json.dumps(template["ownership_split"]))
        self.assertIn("Objective HUD", json.dumps(template["graph_component_operations"]))
        self.assertIn("quality proof", json.dumps(template["graph_component_operations"]))
        self.assertIn("Placeholder visual remains active", json.dumps(template["pie_validation"]))
        self.assertIn("generated_asset_replacement", {row["operation_type"] for row in operations})
        self.assertIn("ai_blackboard_behavior_tree", {row["operation_type"] for row in operations})
        self.assertIn("hud_feedback", {row["operation_type"] for row in operations})
        self.assertIn("skill_compile_ide_companion_asset_lifecycle_manifest", json.dumps(operations))
        self.assertIn("skill_compile_ide_companion_placeholder_manifest", json.dumps(operations))
        self.assertIn("asset_or_placeholder_manifest", template["completion_contract"]["required_evidence"])
        self.assertIn("pie_validation_passed", json.dumps(template["completion_contract"]["proof_gates"]))
        self.assertIn("gen_uthana_text_to_motion", json.dumps(plan["tool_sequence"]))
        self.assertIn("gen_compile_generated_animation_evidence", json.dumps(plan["system_hooks"]["animation"]))

    def test_registered_tool_returns_json(self):
        from skills.playable_slice.skill import register_playable_slice_skill

        mcp = _MockMCP()
        register_playable_slice_skill(mcp)
        self.assertIn("skill_plan_gameplay_mechanic", mcp.tools)

        payload = json.loads(asyncio.run(mcp.tools["skill_plan_gameplay_mechanic"](
            None,
            "collectible resource pickup with capacity",
        )))

        _assert_structured(self, payload, "plan_ready")
        self.assertEqual(payload["outputs"]["plan"]["mechanic_kind"], "inventory_resource")

    def test_save_load_brief_gets_dedicated_template(self):
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        result = skill_plan_gameplay_mechanic("checkpoint save and load state for objective progress")
        plan = result["outputs"]["plan"]

        _assert_structured(self, result, "plan_ready")
        self.assertEqual(plan["mechanic_kind"], "save_load_state")
        self.assertEqual(plan["feature_template"]["template_name"], "save_load_state")
        self.assertTrue(plan["system_hooks"]["savegame"]["needed"])
        self.assertIn("SaveGame Blueprint", json.dumps(plan["feature_template"]["ownership_split"]))
        self.assertIn("Reloading or invoking load restores", json.dumps(plan["feature_template"]["pie_validation"]))
        self.assertIn("save_load_state", {row["operation_type"] for row in plan["feature_template"]["editor_operation_checklist"]})
        self.assertIn("create_save_game_blueprint", json.dumps(plan["feature_template"]["editor_operation_checklist"]))
        runtime_contract = plan["feature_template"]["runtime_proof_contract"]
        self.assertEqual(runtime_contract["mode"], "save_load_state_restore_smoke")
        self.assertIn("savegame_blueprint_or_slot_helper_readback", runtime_contract["required_evidence"])
        self.assertIn("loaded_feature_state_matches_saved_state", runtime_contract["required_evidence"])
        self.assertIn("hud_or_objective_state_restored_after_load", runtime_contract["required_evidence"])
        self.assertIn("savegame_add_slot_helpers", runtime_contract["tool_candidates"])
        self.assertIn("saved feature state and loaded feature state", " ".join(runtime_contract["stop_if_missing"]))

    def test_performance_brief_gets_optimization_template(self):
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        result = skill_plan_gameplay_mechanic("optimize frame hitches in the objective encounter and capture before after proof")
        plan = result["outputs"]["plan"]
        template = plan["feature_template"]

        _assert_structured(self, result, "plan_ready")
        self.assertEqual(plan["mechanic_kind"], "performance_optimization")
        self.assertEqual(template["template_name"], "performance_optimization_pass")
        self.assertTrue(plan["system_hooks"]["performance"]["needed"])
        self.assertIn("Performance Probe", json.dumps(template["ownership_split"]))
        self.assertIn("Capture baseline", json.dumps(template["graph_component_operations"]))
        self.assertIn("before/after timing evidence", json.dumps(template["graph_component_operations"]))
        self.assertIn("Gameplay behavior remains equivalent", json.dumps(template["pie_validation"]))
        self.assertIn("performance_optimization", {row["operation_type"] for row in template["editor_operation_checklist"]})
        self.assertIn("pie_capture_log", json.dumps(template["editor_operation_checklist"]))
        self.assertIn("baseline_profile", json.dumps(plan["tool_sequence"]))
        self.assertIn("viewport_or_hud_screenshot", template["completion_contract"]["required_evidence"])

    def test_combat_brief_gets_uthana_animation_prompts(self):
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        result = skill_plan_gameplay_mechanic("combat attack combo with hit reaction animations")
        plan = result["outputs"]["plan"]
        prompts = plan["generated_animation_prompts"]

        _assert_structured(self, result, "plan_ready")
        self.assertEqual(plan["mechanic_kind"], "combat_loop")
        self.assertTrue(plan["system_hooks"]["animation"]["needed"])
        self.assertGreaterEqual(len(prompts), 2)
        self.assertEqual({prompt["provider"] for prompt in prompts}, {"uthana"})
        self.assertIn("combat_attack_motion", {prompt["role"] for prompt in prompts})
        self.assertIn("retarget-friendly", prompts[0]["prompt"])
        self.assertIn("animgraph_or_state_machine_reference", plan["system_hooks"]["animation"]["proof_required"])
        self.assertIn("gen_uthana_import_animation_to_project", json.dumps(plan["tool_sequence"]))
        self.assertIn("generated_animation_or_placeholder", {row["kind"] for row in plan["feature_template"]["asset_list"]})
        runtime_contract = plan["feature_template"]["runtime_proof_contract"]
        self.assertEqual(runtime_contract["mode"], "replicated_authority_combat_smoke")
        self.assertIn("net_describe_blueprint_replication", runtime_contract["required_evidence"])
        self.assertIn("server_authority_damage_policy_readback", runtime_contract["required_evidence"])
        self.assertIn("two_player_pie_or_deferred_rationale", runtime_contract["required_evidence"])
        self.assertIn("net_validate_common_mistakes", runtime_contract["tool_candidates"])
        self.assertIn("two-player PIE proof", " ".join(runtime_contract["stop_if_missing"]))

    def test_bug_fix_brief_gets_repair_template(self):
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        result = skill_plan_gameplay_mechanic("fix broken objective blueprint compile error and verify runtime regression")
        plan = result["outputs"]["plan"]
        template = plan["feature_template"]
        operation_types = {row["operation_type"] for row in template["editor_operation_checklist"]}

        _assert_structured(self, result, "plan_ready")
        self.assertEqual(plan["mechanic_kind"], "bug_fix_repair")
        self.assertEqual(template["template_name"], "bug_fix_repair_pass")
        self.assertEqual(plan["generated_assets"], [])
        self.assertTrue(plan["system_hooks"]["repair"]["needed"])
        self.assertFalse(plan["system_hooks"]["hud"]["needed"])
        self.assertIn("Repair Probe", json.dumps(template["ownership_split"]))
        self.assertIn("Capture failure context", json.dumps(template["graph_component_operations"]))
        self.assertIn("Original failure is reproduced", json.dumps(template["pie_validation"]))
        self.assertIn("bug_fix_repair", operation_types)
        self.assertIn("bp_get_graph_summary", json.dumps(template["editor_operation_checklist"]))
        self.assertIn("compile_blueprint_and_report", json.dumps(template["editor_operation_checklist"]))
        self.assertIn("pie_capture_log", json.dumps(template["editor_operation_checklist"]))
        self.assertIn("failure_reproduction", json.dumps(plan["tool_sequence"]))
        self.assertNotIn("gen_tripo_text_to_model", json.dumps(plan["tool_sequence"]))
        self.assertIn("blueprint_compile_report", template["completion_contract"]["required_evidence"])
        self.assertIn("graph_or_component_readback", template["completion_contract"]["required_evidence"])
        self.assertIn("pie_log", template["completion_contract"]["required_evidence"])
        self.assertIn("ide_companion_ledger_event", template["completion_contract"]["required_evidence"])

    def test_invalid_brief_is_structured(self):
        from skills.playable_slice.skill import skill_plan_gameplay_mechanic

        payload = skill_plan_gameplay_mechanic("")

        _assert_structured(self, payload, "invalid_brief")
        self.assertFalse(payload["success"])
        self.assertIn("brief is required", payload["errors"])

    def test_static_registration_and_kb(self):
        server_text = (SERVER_ROOT / "unreal_mcp_server.py").read_text(encoding="utf-8")
        inventory_text = (SERVER_ROOT / "tool_inventory_categories.json").read_text(encoding="utf-8")
        skill_text = (SERVER_ROOT / "skills" / "playable_slice" / "skill.py").read_text(encoding="utf-8")
        kb_text = (REPO_ROOT / "knowledge_base" / "32_AGENT_PLAYABLE_SLICE_RECIPE.md").read_text(encoding="utf-8")
        changelog_text = (REPO_ROOT / "knowledge_base" / "v5" / "CHANGELOG.md").read_text(encoding="utf-8")
        panel_text = (REPO_ROOT / "unreal_plugin" / "Source" / "UnrealMCPEditor" / "Private" / "MCPChatPanel.cpp").read_text(encoding="utf-8")

        self.assertIn("register_playable_slice_skill", server_text)
        self.assertIn('"skills.playable_slice.skill"', inventory_text)
        self.assertIn("skill_plan_gameplay_mechanic", skill_text)
        self.assertIn("unreal_mcp_gameplay_mechanic_plan.v1", skill_text)
        self.assertIn("unreal_mcp_gameplay_feature_template.v1", skill_text)
        self.assertIn("editor_operation_checklist", skill_text)
        self.assertIn("unreal_mcp_gameplay_feature_completion_contract.v1", skill_text)
        self.assertIn("unreal_mcp_gameplay_feature_runtime_proof.v1", skill_text)
        self.assertIn("D11 Gameplay Mechanic Planner", kb_text)
        self.assertIn("D36 Gameplay Feature Template Packets", kb_text)
        self.assertIn("D163 Runtime proof contracts", kb_text)
        self.assertIn("performance_optimization_pass", kb_text)
        self.assertIn("bug_fix_repair_pass", kb_text)
        self.assertIn("unreal_mcp_gameplay_feature_completion_contract.v1", kb_text)
        self.assertIn("unreal_mcp_gameplay_feature_runtime_proof.v1", kb_text)
        self.assertIn("D.163 - Gameplay template runtime proof contracts", changelog_text)
        self.assertIn("skill_plan_gameplay_mechanic", kb_text)
        self.assertIn("D.152 - Gameplay-template generated-animation cockpit review", changelog_text)
        self.assertIn("D.151 - Gameplay mechanic Uthana animation prompts", changelog_text)
        self.assertIn("D.150 - Bug-fix repair feature template", changelog_text)
        self.assertIn("D.149 - Performance optimization feature template", changelog_text)
        self.assertIn("D.135 - Gameplay feature completion contracts", changelog_text)
        self.assertIn("D.144 - AI patrol objective asset-swap vertical-slice template", changelog_text)
        self.assertIn("D.36 - Gameplay feature template packets", changelog_text)
        self.assertIn("D.11 - Gameplay mechanic planner", changelog_text)
        self.assertIn("Plan Gameplay Mechanic", panel_text)
        self.assertIn("placeholder/generated asset swap requirements", panel_text)
        self.assertIn("unreal_mcp_gameplay_mechanic_plan.v1", panel_text)


if __name__ == "__main__":
    unittest.main()
