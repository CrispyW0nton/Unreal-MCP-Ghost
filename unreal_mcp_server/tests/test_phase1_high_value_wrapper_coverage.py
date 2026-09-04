"""Offline guard for the AI IDE roadmap's high-value bridge wrappers."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVER_ROOT.parent


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "audit_high_value_wrapper_coverage",
        REPO_ROOT / "scripts" / "audit_high_value_wrapper_coverage.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestPhase1HighValueWrapperCoverage(unittest.TestCase):
    def test_named_roadmap_capabilities_have_full_offline_evidence(self):
        audit = _load_audit_module()

        report = audit.build_report()

        self.assertEqual(report["schema"], "unreal_mcp_high_value_wrapper_coverage.v1")
        self.assertEqual(report["state"], "ok")
        self.assertEqual(report["status"], "OK")
        self.assertTrue(report["ok"], report)
        self.assertGreaterEqual(report["command_count"], 14)
        self.assertIn("set_behavior_tree_blackboard", report["command_preview"])
        self.assertIn("add_get_random_reachable_point_node", report["command_preview"])
        self.assertEqual(report["covered_capability_count"], 10)
        self.assertEqual(report["failing_capability_count"], 0)
        self.assertEqual(report["failing_capability_preview"], [])
        self.assertEqual(report["schema_command_count"], report["command_count"])
        self.assertEqual(report["schema_covered_command_count"], report["schema_command_count"])
        self.assertEqual(report["roadmap_priority_count"], 10)
        self.assertEqual(report["roadmap_priority_covered_count"], 10)
        self.assertEqual(report["roadmap_priority_missing_count"], 0)
        self.assertEqual(report["roadmap_priority_command_count"], report["command_count"])
        self.assertIn("behavior_tree_blackboard_assignment", report["roadmap_priority_preview"])
        self.assertIn("behavior_tree_task_graph_primitives", report["roadmap_priority_preview"])
        self.assertIn("niagara_component_attachment", report["roadmap_priority_preview"])
        self.assertEqual(report["roadmap_priority_missing_preview"], [])
        self.assertEqual(report["operator_command_handoff_count"], 2)
        self.assertEqual(
            report["operator_command_handoff_ids"],
            ["run_high_value_wrapper_coverage_audit", "run_high_value_wrapper_offline_tests"],
        )
        self.assertEqual(report["operator_command_handoff"][0]["command"], "python scripts\\audit_high_value_wrapper_coverage.py --json")
        self.assertFalse(report["operator_command_handoff"][0]["requires_bridge"])
        self.assertTrue(report["operator_command_handoff"][0]["no_editor_mutation"])
        self.assertTrue(report["operator_command_handoff"][0]["no_provider_call"])
        self.assertTrue(report["operator_command_handoff"][0]["no_git_mutation"])
        self.assertEqual(report["audit_tool"], "scripts/audit_high_value_wrapper_coverage.py")
        self.assertEqual(report["bridge_registry_tool"], "scripts/bridge_command_audit.py")
        self.assertFalse(report["requires_bridge"])
        self.assertTrue(report["no_editor_mutation"])
        self.assertTrue(report["no_provider_call"])
        self.assertTrue(report["no_git_mutation"])

        capabilities = {entry["name"]: entry for entry in report["capabilities"]}
        self.assertIn("behavior_tree_blackboard_assignment", capabilities)
        self.assertIn("behavior_tree_task_graph_primitives", capabilities)
        self.assertIn("blueprint_parent_class_changes", capabilities)
        self.assertIn("construction_script_native_node", capabilities)
        self.assertIn("function_with_pins_creation", capabilities)
        self.assertIn("spawnactor_class_assignment", capabilities)
        self.assertIn("math_relational_native_nodes", capabilities)
        self.assertIn("sequence_player_nodes", capabilities)
        self.assertIn("animgraph_pose_links", capabilities)
        self.assertIn("niagara_component_attachment", capabilities)

        for capability in capabilities.values():
            self.assertTrue(capability["test_files"])
            self.assertTrue(capability["doc_files"])
            self.assertEqual(capability["schema_covered_command_count"], capability["schema_command_count"])
            for command in capability["commands"]:
                self.assertGreater(command["cpp_routes"], 0, command)
                self.assertGreater(command["python_references"], 0, command)
                self.assertIn("ctx", command["parameters"], command)
                self.assertTrue(command["schema_ok"], command)
                self.assertTrue(command["expected_schema_parameters"], command)
                self.assertEqual(command["missing_schema_parameters"], [], command)

    def test_markdown_report_names_status_and_core_commands(self):
        audit = _load_audit_module()

        markdown = audit.format_markdown(audit.build_report())

        self.assertIn("# High-Value Bridge Wrapper Coverage", markdown)
        self.assertIn("Status: OK", markdown)
        self.assertIn("Schema coverage:", markdown)
        self.assertIn("Roadmap priorities: 10/10 covered", markdown)
        self.assertIn("`set_behavior_tree_blackboard`", markdown)
        self.assertIn("`add_get_random_reachable_point_node`", markdown)
        self.assertIn("`add_finish_execute_node`", markdown)
        self.assertIn("`add_clear_blackboard_value_node`", markdown)
        self.assertIn("`add_blueprint_function_with_pins`", markdown)
        self.assertIn("`connect_anim_graph_nodes`", markdown)
        self.assertIn("`add_niagara_component`", markdown)


if __name__ == "__main__":
    unittest.main()
